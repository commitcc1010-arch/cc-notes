---
chapter: 12
title: Binary Tree：DFS 與 BFS
part: 2
---

# 第 12 章　Binary Tree：DFS 與 BFS

> [!abstract] 本章地圖
> **一句話**：先決定遞迴函式「對一棵子樹回傳什麼」，讓每個節點只靠左右子樹的答案就能在 O(1) 內算出自己的答案；題目在乎「一層一層」或「離根多遠」時，改用 queue 做 BFS。
>
> **辨識訊號**：
> - 題目說「每一層」「由上到下、由左到右」「從某一側看過去」
> - 「任兩個節點之間最長／最大的路徑」，而且路徑不一定經過根
> - 「兩個節點最近的共同祖先」「某個節點是否在某棵子樹裡」
> - 給遍歷序列要重建樹，或要把樹轉成字串再轉回來
> - 在節點上做選擇（放置、塗色、選或不選），相鄰節點互相影響，要最少或最多
> - 「刪掉某棵子樹之後」「對每個節點回答關於樹其餘部分的問題」
>
> **核心題**：102、199、543、105、236
>
> **難題**：124、297、968、987、2458

## 12.1 這個 Pattern 解決什麼問題

先看最小的例子：給一棵二元樹，求它的高度（從根往下最長的路徑有幾個節點）。你不需要知道整棵樹長什麼樣子，只要知道左子樹多高、右子樹多高，自己的高度就是 `1 + max(左, 右)`。左右子樹的高度怎麼來？用同一個函式去問它們。空樹的高度是 0，這是遞迴的終點。整個過程每個節點只被拜訪一次，所以是 O(n)。這就是 binary tree 題目的核心：**一棵樹的答案，由根節點和兩棵子樹的答案組合而成**。

可是一旦題目變複雜，很多人會不自覺地寫出重複計算。例如要找「任兩個節點之間最長的路徑」（核心題 3），直覺做法是對每個節點都呼叫一次 `height(左) + height(右)`；每次 `height` 都要走過整棵子樹，在一條鏈狀的樹上就變成 1 + 2 + … + n = O(n²)。問題不在遞迴本身，而在同一棵子樹的高度被算了很多次。改進方法是讓一次走訪同時做兩件事：函式把「高度」回傳給父節點使用，並在經過每個節點時順手更新「以這個節點為轉折點的最長路徑」。於是又回到每個節點只看一次、總共 O(n)。

所以寫樹的題目時，真正要設計的是**遞迴函式的合約（contract）**：它收到什麼參數、回傳什麼、有沒有順手更新的全域答案。合約定好之後，程式通常只有五到十行，正確性也能用歸納法一句話說清楚：「假設左右子樹回傳的值是對的，那麼我組合出來的值也是對的。」本章的題目幾乎都在練這件事，差別只在回傳值怎麼設計：543 回傳單邊最長、236 回傳「子樹裡找到了誰」、124 回傳「往下延伸的最大收益」、968 回傳「這個節點的監控狀態」。

另一類題目關心的是「層」：每一層的節點、每一層最右邊的節點、離根最近的葉子。DFS 帶著深度參數也做得到，但 BFS（breadth-first search，廣度優先搜尋）更自然：用 queue 從根開始，一次處理一整層，處理完這一層時，queue 裡剛好就是下一層的全部節點。核心題 1、2 是這類題的標準形，第 15 章在一般的圖上用的也是同一個迴圈，只是多了 `visited`。

最後還有一類題目需要「兩個方向」的資訊：子樹裡面的資訊由下往上收集，子樹外面的資訊由上往下傳遞。難題 5（2458）問「刪掉某棵子樹後整棵樹多高」，答案取決於子樹**外面**的部分，單靠後序回傳值做不到，必須再補一次由上往下的走訪。能分辨一題需要哪個方向的資訊，是這一章最重要的能力。

## 12.2 辨識訊號

| 題目特徵 | 為什麼是這個 pattern | 本章哪一題 |
|---|---|---|
| 「每一層」「逐層」「由上到下、由左到右」 | BFS 每一輪外層迴圈恰好處理一層 | 核心題 1（102） |
| 「從右邊看」「每層第一個／最後一個」「最小深度」 | 層的概念加上每層只取一個；或 DFS 帶深度、先走右邊 | 核心題 2（199） |
| 「任兩個節點間最長／最大的路徑」 | 每條路徑有唯一的最高點；後序回傳單邊，在最高點組合兩邊 | 核心題 3（543）、難題 1（124） |
| 「由遍歷序列重建樹」「把樹轉成字串再轉回來」 | preorder 的第一個是根，根把序列切成左右兩段，分治 | 核心題 4（105）、難題 2（297） |
| 「兩個節點最近的共同祖先」「x 是否在某棵子樹裡」 | 後序回傳「子樹裡找到了什麼」 | 核心題 5（236） |
| 在節點上放東西，能覆蓋自己與鄰居，要最少 | 葉子附近的決策最確定，由下往上貪婪或樹 DP，回傳狀態 | 難題 3（968） |
| 依座標（列、行）分組輸出 | 遍歷時由上往下傳座標，最後排序或分桶 | 難題 4（987） |
| 「移除子樹後的高度」「對每個節點問樹的其餘部分」 | 先後序算子樹內的資訊，再前序由上往下傳子樹外的資訊 | 難題 5（2458） |

一個實用的判斷：如果答案只和「某個節點與它的子孫」有關，用後序（先算子樹、再算自己）；如果答案和「從根走下來這一路上發生的事」有關（深度、座標、路徑上的最大值），用參數由上往下傳；如果和「同一層」有關，用 BFS。三者可以出現在同一題裡，例如 2458 先後序、再前序；987 由上往下傳座標，最後再排序。

另一個訊號是限制條件。樹的題目 n 通常是 10⁴ 到 10⁵，代表要 O(n) 或 O(n log n)，也就是「每個節點只能處理常數次」。如果你的做法在每個節點都重新走一次子樹，最差就是 O(n²)，這時要回頭想：能不能讓子樹把需要的資訊一次回傳上來？

## 12.3 模板與原理

全章的程式都建立在三個零件上：節點類別與「從 level-order list 建樹」的工具（方便寫 assert）、DFS 後序模板、BFS 層序模板。下面這段程式把三者放在一起；之後每題的解法開頭都會重複 `TreeNode` 與 `build_tree`，讓每段程式可以單獨執行。

```python
from collections import deque
from typing import Optional


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def build_tree(values: list) -> Optional[TreeNode]:
    """從 level-order list 建樹（LeetCode 格式），None 代表該位置沒有節點。"""
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue = deque([root])
    i = 1
    while queue and i < len(values):
        node = queue.popleft()               # 每個「真實節點」依序領取兩個位置
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def to_list(root: Optional[TreeNode]) -> list:
    """build_tree 的反函式：輸出 level-order list，並去掉尾端多餘的 None。"""
    out, queue = [], deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            out.append(None)                 # 空位只佔一格，不再替它產生子節點
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out


def max_depth(root: Optional[TreeNode]) -> int:
    """DFS 後序模板：先拿到左右子樹的答案，再組合出自己的答案。"""
    if root is None:                         # base case：空樹
        return 0
    left = max_depth(root.left)
    right = max_depth(root.right)
    return 1 + max(left, right)


def level_order(root: Optional[TreeNode]) -> list[list[int]]:
    """BFS 模板：每一輪外層迴圈開始時，queue 裡恰好是同一層的全部節點。"""
    if root is None:
        return []
    res, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):          # 先固定這一層的節點數
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        res.append(level)
    return res


root = build_tree([3, 9, 20, None, None, 15, 7])
assert root.val == 3 and root.left.val == 9 and root.right.left.val == 15
assert to_list(root) == [3, 9, 20, None, None, 15, 7]
assert to_list(build_tree([1, None, 2, 3])) == [1, None, 2, 3]   # 3 是 2 的左子節點
assert to_list(build_tree([])) == [] and build_tree([None]) is None
assert max_depth(root) == 3 and max_depth(None) == 0
assert max_depth(build_tree([1, 2, None, 3, None, 4])) == 4      # 往左的鏈
assert level_order(root) == [[3], [9, 20], [15, 7]]
assert level_order(build_tree([0, -1, 1])) == [[0], [-1, 1]]    # 值為 0 也要正確處理
assert level_order(None) == []
print("all tests passed")
```

```text
values = [3, 9, 20, None, None, 15, 7]

        3            每個真實節點依序領取兩個位置：
       / \             3  領取 values[1], values[2] = 9, 20
      9   20           9  領取 values[3], values[4] = None, None
         /  \          20 領取 values[5], values[6] = 15, 7
        15   7         15、7 之後已經沒有值，結束

BFS 模板跑在這棵樹上：
輪次  開始時 queue   len  本輪輸出    結束時 queue
 1    [3]           1    [3]         [9, 20]
 2    [9, 20]       2    [9, 20]     [15, 7]
 3    [15, 7]       2    [15, 7]     []
```

**Level-order list 的規則**。LeetCode 的格式是「層序列出所有真實節點，空的子節點寫 null，尾端的 null 省略」。重點是**只有真實節點會領取兩個位置**，`None` 不會替自己的子節點佔位。所以 `[1, None, 2, 3]` 中的 3 是 2 的左子節點，而不是「索引 3 = 2 × 1 + 1」所代表的 1 的左子節點的左子節點。很多人把它和 heap 的陣列表示（索引 i 的子節點在 2i + 1、2i + 2）混淆；heap 的公式只對 complete binary tree（完全二元樹）成立，一般的樹必須用上面這種「queue 依序分配」的方式。`build_tree` 和 `to_list` 互為反函式，本章大量用 `to_list` 來比對重建出來的樹。

**DFS 的正確性：結構歸納**。`max_depth` 的正確性只需要兩句話：空樹回傳 0 是對的；如果左右子樹回傳的高度都是對的，那麼 `1 + max(left, right)` 就是這棵樹的高度。這叫 structural induction（結構歸納），是證明所有樹遞迴的標準方法，面試時說出來，比逐步追蹤遞迴更有說服力。寫遞迴時不要試圖在腦中展開整棵遞迴樹，只要相信子問題的回傳值符合合約，專心處理「目前這個節點怎麼組合」即可。

**BFS 的 invariant**。外層 `while` 每一輪開始時，queue 裡恰好是某一層的全部節點，而且由左到右排列。一開始只有根，成立；這一輪把這些節點依序彈出，並依序推入它們的左、右子節點，所以結束時 queue 裡剛好是下一層、也是由左到右。關鍵是 `for _ in range(len(queue))` **先把這一層的大小固定下來**：迴圈中 queue 會一邊彈出、一邊推入下一層的節點，如果每次都重新看 `len(queue)` 或寫成 `while queue`，兩層就會混在一起。queue 要用 `collections.deque`，因為 `list.pop(0)` 是 O(n)，整個 BFS 會退化成 O(n²)。

**前序、中序、後序怎麼選**。三者都是 DFS，差別只在「處理自己」放在走訪子樹的前、中、後。前序（preorder，根左右）適合把資訊由上往下傳，以及序列化（難題 2）；中序（inorder，左根右）在 BST 上會得到排序好的序列，是第 13 章的主角；後序（postorder，左右根）適合由下往上組合答案，本章大部分題目都是後序。時間都是 O(n)，空間是 O(h)，h 是樹高：平衡樹時 h = O(log n)，鏈狀時 h = O(n)。

## 12.4 三種資訊流：參數、回傳值、全域答案

樹上的資訊只有三種流動方式，幾乎每一題都是它們的組合。**由上往下**：把祖先的資訊當作參數傳給子節點，例如目前深度、路徑上的最大值、座標；這是前序的思維。**由下往上**：子樹把摘要當作回傳值交給父節點，例如高度、是否平衡、子樹和；這是後序的思維。**跨子樹**：答案需要同時用到左右兩棵子樹的資訊，但父節點只需要其中一部分，這時在節點上組合兩邊、更新一個全域答案，回傳值仍然只給父節點需要的那部分。

```python
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def good_nodes(root) -> int:
    """1448：從根到 x 的路徑上沒有比 x 大的值，x 就是 good node。資訊由上往下傳。"""
    def dfs(node, best_so_far):
        if node is None:
            return 0
        good = 1 if node.val >= best_so_far else 0
        best = max(best_so_far, node.val)
        return good + dfs(node.left, best) + dfs(node.right, best)
    return dfs(root, float("-inf"))


def is_balanced(root) -> bool:
    """110：每個節點左右子樹高度差 ≤ 1。資訊由下往上傳，用 -1 代表「已經不平衡」。"""
    def height(node):
        if node is None:
            return 0
        left = height(node.left)
        if left == -1:
            return -1
        right = height(node.right)
        if right == -1 or abs(left - right) > 1:
            return -1
        return 1 + max(left, right)
    return height(root) != -1


def count_unival_subtrees(root) -> int:
    """250：所有值都相同的子樹有幾棵。回傳「是否同值」給父節點，同時累加全域答案。"""
    count = 0

    def dfs(node):
        nonlocal count
        if node is None:
            return True
        left = dfs(node.left)               # 兩邊都要走完，不能用 and 短路
        right = dfs(node.right)
        if not (left and right):
            return False
        if node.left and node.left.val != node.val:
            return False
        if node.right and node.right.val != node.val:
            return False
        count += 1
        return True

    dfs(root)
    return count


assert good_nodes(build_tree([3, 1, 4, 3, None, 1, 5])) == 4
assert good_nodes(build_tree([3, 3, None, 4, 2])) == 3
assert good_nodes(build_tree([1])) == 1
assert is_balanced(build_tree([3, 9, 20, None, None, 15, 7]))
assert not is_balanced(build_tree([1, 2, 2, 3, 3, None, None, 4, 4]))
assert not is_balanced(build_tree([1, 2, 2, 3, None, None, 3, 4, None, None, 4]))  # 根平衡、子樹不平衡
assert is_balanced(None)
assert count_unival_subtrees(build_tree([5, 1, 5, 5, 5, None, 5])) == 4
assert count_unival_subtrees(build_tree([5, 5, 5, 5, 5, None, 5])) == 6
assert count_unival_subtrees(None) == 0
print("all tests passed")
```

```text
good_nodes：參數由上往下              is_balanced：回傳值由下往上
       3   (best=-inf → 3 good)              1        左高 3、右高 1 → 差 2 → -1
      / \                                   / \
     1   4 (best=3 → 4 good)               2   2      左 2：子樹高 2、1 → 3
    /   / \                               / \
   3   1   5                             3   3        3：子樹高 1、1 → 2
 (best=3 → good) (best=4 → 1 不是, 5 good)  / \
                                         4   4
good = 3、4、3、5 共 4 個              height 依序回傳 1, 1, 2, 1, 3, 1, -1 → 不平衡
```

左邊的例子中，第二個 3（在 1 的下面）是 good node，因為路徑 3 → 1 → 3 上的最大值是 3，沒有比它大；右下的 1 不是，因為路徑上的最大值已經是 4。右邊的例子中，每個節點只需要左右子樹的高度，算到根時發現 3 − 1 = 2，於是回傳 -1；而一旦有子樹回傳 -1，祖先直接把 -1 往上傳，不必再算另一邊，這是用「哨兵值」把兩個回傳值（高度、是否平衡）壓成一個整數的常見技巧。

`count_unival_subtrees` 示範第三種流動：父節點只需要知道「子樹是否同值」，但題目要的是總數，所以總數放在 `nonlocal` 變數裡。注意 `left = dfs(...)`、`right = dfs(...)` 要分開寫：如果寫成 `if not (dfs(node.left) and dfs(node.right))`，左邊回傳 False 時右子樹不會被走訪，右子樹裡的同值子樹就漏算了。全域答案一律用巢狀函式加 `nonlocal`，不要用模組層級的全域變數或類別屬性，否則多個測試案例之間會共用上一次的值。

## 12.5 遞迴深度與迭代寫法

Python 預設的遞迴上限大約是 1000 層，而 LeetCode 的樹常常有 10⁴ 到 10⁵ 個節點，而且測資一定會放一條鏈。遞迴 DFS 在鏈上會丟出 `RecursionError`。有兩種處理方式：第一，`sys.setrecursionlimit(10**6)`；在 Python 3.11 之後純 Python 函式之間的遞迴不再大量消耗 C stack，調高上限通常就夠了，但在舊版直譯器或某些平台上，太深的遞迴可能直接讓程式 crash。第二，改成用顯式的 stack 迭代。面試時通常可以寫遞迴版，但要主動說出「樹可能退化成鏈，深度 O(n)，正式環境我會改成迭代」，並且會寫下面這幾個迭代模板。

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(random.randint(-9, 9)) for _ in range(n)]
    for i in range(1, n):
        while True:                            # 隨機挑一個還有空位的節點當父節點
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0] if nodes else None


def preorder_iter(root):
    out, stack = [], [root] if root else []
    while stack:
        node = stack.pop()
        out.append(node.val)
        if node.right:                         # 先推右，才會先彈出左
            stack.append(node.right)
        if node.left:
            stack.append(node.left)
    return out


def inorder_iter(root):
    out, stack, node = [], [], root
    while stack or node:
        while node:                            # 一路往左，沿途的節點都還沒輸出
            stack.append(node)
            node = node.left
        node = stack.pop()                     # 左子樹處理完了，輸出自己
        out.append(node.val)
        node = node.right                      # 接著處理右子樹
    return out


def postorder_iter(root):
    out, stack = [], [(root, False)] if root else []
    while stack:
        node, expanded = stack.pop()
        if expanded:                           # 第二次看到：子樹都處理完了
            out.append(node.val)
            continue
        stack.append((node, True))
        if node.right:
            stack.append((node.right, False))
        if node.left:
            stack.append((node.left, False))
    return out


def height_by_bfs_order(root):
    """另一種後序：BFS 順序反過來，子節點一定比父節點先處理。"""
    if root is None:
        return 0
    order = [root]
    for node in order:                         # 一邊走訪一邊 append，list 會自然延長
        order.extend(c for c in (node.left, node.right) if c)
    height = {}
    for node in reversed(order):
        hl = height[node.left] if node.left else 0
        hr = height[node.right] if node.right else 0
        height[node] = 1 + max(hl, hr)
    return height[root]


def recursive(root, kind):
    if root is None:
        return []
    l, r = recursive(root.left, kind), recursive(root.right, kind)
    return {"pre": [root.val] + l + r, "in": l + [root.val] + r, "post": l + r + [root.val]}[kind]


t = build_tree([1, 2, 3, 4, 5, None, 6])
assert preorder_iter(t) == [1, 2, 4, 5, 3, 6]
assert inorder_iter(t) == [4, 2, 5, 1, 3, 6]
assert postorder_iter(t) == [4, 5, 2, 6, 3, 1]
assert preorder_iter(None) == inorder_iter(None) == postorder_iter(None) == []
for _ in range(300):
    t = random_tree(random.randint(0, 12))
    assert preorder_iter(t) == recursive(t, "pre")
    assert inorder_iter(t) == recursive(t, "in")
    assert postorder_iter(t) == recursive(t, "post")
chain = cur = TreeNode(0)
for v in range(1, 100_000):                    # 十萬層的鏈：遞迴版會 RecursionError
    cur.left = TreeNode(v)
    cur = cur.left
assert height_by_bfs_order(chain) == 100_000
assert len(postorder_iter(chain)) == 100_000
print("all tests passed")
```

```text
inorder_iter 在 [1, 2, 3, 4, 5, None, 6] 上：
        1
       / \
      2   3
     / \   \
    4   5   6

動作                   stack（底 → 頂）   輸出
往左推 1, 2, 4         [1, 2, 4]
彈出 4，轉向 4.right   [1, 2]            4
彈出 2，轉向 5         [1]               4 2
推 5、彈出 5           [1]               4 2 5
彈出 1，轉向 3         []                4 2 5 1
推 3、彈出 3，轉向 6   []                4 2 5 1 3
推 6、彈出 6           []                4 2 5 1 3 6
```

迭代中序的 stack 存的是「左子樹還沒處理完、自己還沒輸出」的祖先，這是 inorder 迭代的 invariant，第 13 章難題 5（99 Recover BST）和 BST iterator 都直接用它。迭代後序有兩種寫法：用 `(node, expanded)` 標記第二次拜訪，或者像 `height_by_bfs_order` 那樣先拿到 BFS 順序再反過來處理。後者特別好用：BFS 順序保證父節點在子節點之前，反過來就保證子節點在父節點之前，所有「由下往上」的計算都能照這個順序做，難題 5 就用這個方法處理十萬層的鏈。

## 12.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 忘記處理 `None` | `AttributeError: 'NoneType' object has no attribute 'val'` | 每個遞迴函式第一行先寫 base case；BFS 推入前檢查子節點是否存在 |
| BFS 沒有固定這一層的大小 | 兩層的節點混在同一個 list | 用 `for _ in range(len(queue))` 先固定層大小 |
| 用 `list.pop(0)` 當 queue | 大樹上超時，整體變 O(n²) | 用 `collections.deque` 的 `popleft()` |
| 每個節點都重新計算子樹高度 | 鏈狀的樹 O(n²) 超時 | 讓同一次後序同時回傳高度並更新答案（核心題 3） |
| 回傳值與全域答案混為一談 | 124 回傳了左右兩邊的和，父節點接上後路徑「分叉」 | 回傳給父節點的只能是單邊；兩邊組合只用來更新全域答案 |
| 邊數與節點數混用 | 直徑或高度差 1 | 開頭就寫下合約：「回傳的是節點數還是邊數」，空樹的值依此決定（0 或 -1） |
| 用模組層級的全域變數存答案 | 第二個測試案例的答案錯，因為上一次的值沒有重置 | 用巢狀函式加 `nonlocal`，或把答案當回傳值的一部分 |
| 在遞迴中切片 `preorder[1:]`、呼叫 `inorder.index` | 105 在鏈狀樹上 O(n²) | 用 hash map 存位置、用索引或 iterator 取代切片 |
| 用值比較節點，而不是用 `is` 比較物件 | 有重複值時 236 找錯節點 | 題目給的是節點就比較物件；只有值保證唯一時才能用值 |
| 遞迴太深 | 十萬層的鏈 `RecursionError` | 說明風險；改用顯式 stack 或「BFS 順序反向處理」 |
| 用 `and`／`or` 短路呼叫遞迴 | 某些子樹沒被走訪，全域計數漏算 | 需要走完整棵樹時，先把左右遞迴結果存進變數再判斷 |

## 核心題 1｜102. Binary Tree Level Order Traversal｜Medium

### 題目

給一棵二元樹的根節點 `root`，請由上到下逐層回傳節點的值，每一層由左到右排成一個 list，整體回傳 list of lists。限制：節點數在 `0` 到 `2000` 之間，節點值在 `-1000` 到 `1000` 之間。

- 範例 1：`root = [3, 9, 20, null, null, 15, 7]`，回傳 `[[3], [9, 20], [15, 7]]`。
- 範例 2：`root = [1, 2, 3, 4, null, 5, 6, null, 7]`，回傳 `[[1], [2, 3], [4, 5, 6], [7]]`；7 是 4 的右子節點，自己單獨一層。
- 範例 3（邊界）：`root = [1]`，回傳 `[[1]]`。
- 範例 4（邊界）：`root = []`，回傳 `[]`（不是 `[[]]`）。

### 思路

最笨的做法是先求樹高 H，再對每個深度 d 從根做一次 DFS，只收集深度剛好是 d 的節點；每次 DFS 都走過整棵樹，總時間 O(n · H)，鏈狀時是 O(n²)。瓶頸在於每一層都重新從根走一遍，而其實「第 d + 1 層」就是「第 d 層所有節點的子節點」，上一層已經把下一層交到我們手上了。

這正是 BFS 的想法：用 queue 保存「下一個要處理的節點」。每一輪外層迴圈開始時，queue 裡恰好是同一層的全部節點、由左到右排列（12.3 節的 invariant）。這一輪先用 `len(queue)` 記下這一層有幾個節點，再彈出剛好這麼多個，同時把它們的子節點依序推進 queue；彈完時，這一層的結果收集完成，而 queue 裡已經是完整的下一層。每個節點恰好進出 queue 一次，總時間 O(n)。

另一個同樣 O(n) 的寫法是 DFS 帶著深度：`dfs(node, depth)` 第一次到達某個深度時開一個新的 list，然後把值放進 `res[depth]`。因為前序是先左後右，同一層的節點會由左到右被拜訪，所以每層內部的順序也是對的。兩種都要會：BFS 是這題最直接的答案，DFS 版則在樹很寬、queue 會很大時可以只用 O(h) 的 stack，這個取捨正是面試官常追問的點（見 F4）。

```text
root = [1, 2, 3, 4, null, 5, 6, null, 7]

        1
       / \
      2   3
     /   / \
    4   5   6
     \
      7

輪次  len  依序彈出（並推入子節點）     本輪結果     結束時 queue
 1     1   1 → 推 2, 3                  [1]          [2, 3]
 2     2   2 → 推 4；3 → 推 5, 6        [2, 3]       [4, 5, 6]
 3     3   4 → 推 7；5；6               [4, 5, 6]    [7]
 4     1   7                            [7]          []
```

第 3 輪最能說明為什麼要先固定 `len`：彈出 4 之後立刻推入 7，queue 變成 `[5, 6, 7]`，第 4 層的節點已經混進來了。因為這一輪只彈出一開始記下的 3 個，7 會留到下一輪，層與層就不會混在一起。如果寫成 `while queue` 一直彈，7 會被算進第 3 層，輸出變成 `[[1], [2, 3], [4, 5, 6, 7]]`。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(random.randint(-9, 9)) for _ in range(n)]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0] if nodes else None


def level_order(root):
    if root is None:
        return []
    res, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):           # 固定這一層的節點數
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        res.append(level)
    return res


def level_order_dfs(root):
    res = []

    def dfs(node, depth):
        if node is None:
            return
        if depth == len(res):                 # 第一次到達這個深度，開新的一層
            res.append([])
        res[depth].append(node.val)
        dfs(node.left, depth + 1)             # 先左後右，同層由左到右
        dfs(node.right, depth + 1)

    dfs(root, 0)
    return res


def brute(root):
    def collect(node, depth, d, out):
        if node:
            if depth == d:
                out.append(node.val)
            collect(node.left, depth + 1, d, out)
            collect(node.right, depth + 1, d, out)
    res, d = [], 0
    while True:
        out = []
        collect(root, 0, d, out)
        if not out:
            return res
        res.append(out)
        d += 1


assert level_order(build_tree([3, 9, 20, None, None, 15, 7])) == [[3], [9, 20], [15, 7]]
assert level_order(build_tree([1, 2, 3, 4, None, 5, 6, None, 7])) == [[1], [2, 3], [4, 5, 6], [7]]
assert level_order(build_tree([1])) == [[1]]
assert level_order(None) == []
assert level_order(build_tree([1, None, 2, None, 3])) == [[1], [2], [3]]   # 往右的鏈
for _ in range(300):
    t = random_tree(random.randint(0, 15))
    assert level_order(t) == level_order_dfs(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個節點進 queue 一次、出 queue 一次，每次 O(1)。空間 O(w)，w 是最寬那一層的節點數；完全二元樹的最後一層約有 n / 2 個節點，所以最差是 O(n)，而鏈狀的樹 w = 1。輸出本身也是 O(n)，通常不算在額外空間裡。DFS 版的額外空間是遞迴深度 O(h)。邊界情況：空樹要回傳 `[]` 而不是 `[[]]`，所以開頭要特判；推入子節點前要檢查 `if node.left`，不要把 `None` 推進 queue（否則每一層要多一次過濾）；節點值可以是 0 或負數，判斷「有沒有子節點」要看節點物件，而不是看值。

### Follow-up

> [!question]- F1. 如果要由下往上輸出（107. Binary Tree Level Order Traversal II）呢？
> 照原本的 BFS 收集完，最後 `res.reverse()`，O(n)。不要每層都 `res.insert(0, level)`：list 的頭部插入是 O(層數)，總共 O(H²)，鏈狀樹上會變成 O(n²)。如果一定要邊做邊放在前面，可以用 `deque.appendleft`，每次 O(1)。面試官問這題通常是在看你會不會注意到頭部插入的成本。

> [!question]- F2. 如果要「之」字形輸出，第一層由左到右、第二層由右到左，交替下去（103）呢？
> 走訪順序完全不變，只改輸出：用一個布林值 `left_to_right` 記錄這一層的方向，收集完這一層後若方向是由右到左就 `level.reverse()`，再翻轉布林值。每層反轉的成本是該層的大小，總和仍是 O(n)。常見的錯誤是去改「推入子節點的順序」，那會打亂下一層的走訪順序，讓之後每一層都錯。也可以每層用一個 deque，依方向 `append` 或 `appendleft`。

> [!question]- F3. 如果要每一層的平均值或最大值（637、515）呢？
> 外層迴圈結構不變，只把 `level.append(node.val)` 換成累加器：平均值用 `total += node.val`，結束時除以這一層的大小（就是迴圈前記下的 `len(queue)`）；最大值用 `best = max(best, node.val)`。這樣不必存下整層的值，額外空間只剩 queue 本身。DFS 版也可以做，平均值要對每個深度維護 `(總和, 個數)` 兩個陣列，最後再相除。注意總和可能很大，在 Java／C++ 中要用 `long`。

> [!question]- F4. 如果樹非常寬（例如完全二元樹、n = 10⁶），queue 會佔掉太多記憶體，怎麼辦？
> 改用 DFS 帶深度，額外空間是樹高 O(h)，完全二元樹只有約 20 層，遠小於最後一層的 n / 2 個節點。若連輸出都不想一次存下來，只需要「依序印出每一層」，可以用 iterative deepening：對 d = 0, 1, 2, … 各做一次「只輸出深度 d 的節點」的 DFS，直到某一次沒有任何節點為止；空間 O(h)，時間是 O(n · H)。在平衡樹上 H = O(log n)，所以是 O(n log n)，用時間換空間。

> [!question]- F5. 如果每個節點有一個 next 指標，要指向同一層右邊的節點，而且只能用 O(1) 額外空間（117. Populating Next Right Pointers in Each Node II）呢？
> BFS 需要 O(w) 的 queue，不符合要求。關鍵是：處理第 d + 1 層時，第 d 層的 next 已經接好了，第 d 層本身就是一條 linked list，可以取代 queue。用一個 dummy 節點當作下一層的頭，`tail` 指向下一層目前的尾端；沿著第 d 層的 next 走，把每個節點的左、右子節點依序接到 `tail.next`。走完一層後，下一層的開頭就是 `dummy.next`，重複直到它為空。每個節點處理一次，O(n) 時間、O(1) 額外空間。這是第 11 章 dummy 節點技巧在樹上的應用。

## 核心題 2｜199. Binary Tree Right Side View｜Medium

### 題目

想像你站在一棵二元樹的右邊往左看，請由上到下回傳你看得到的節點值。每一層你只看得到最右邊的那個節點，即使它位於根的左子樹。限制：節點數在 `0` 到 `100` 之間，節點值在 `-100` 到 `100` 之間。

- 範例 1：`root = [1, 2, 3, null, 5, null, 4]`，回傳 `[1, 3, 4]`。
- 範例 2：`root = [1, 2, 3, 4]`，回傳 `[1, 3, 4]`；第三層只有左子樹裡的 4，右邊沒有東西擋住它，所以看得到。
- 範例 3：`root = [1, null, 3]`，回傳 `[1, 3]`。
- 範例 4（邊界）：`root = []`，回傳 `[]`。

### 思路

第一個直覺通常是「一直往右走」：從根開始，有右子節點就往右，沒有就往左。範例 2 立刻推翻它：從 1 走到 3，3 沒有子節點，路就斷了，但第三層的 4 在左子樹裡依然看得到。這個錯誤說明了題目的本質：右視圖是「每一層最右邊的節點」，和「往右的那條路」沒有直接關係。

既然是「每一層的某一個」，最直接的做法就是核心題 1 的 BFS：每層處理完時，最後一個彈出的節點就是這一層最右邊的節點，O(n)。暴力法（先求出整個層序再取每層最後一個）其實也是 O(n)，只是多存了整份層序；這題的重點不是複雜度，而是看出正確的定義，並能寫出不需要額外儲存層序的版本。

DFS 版本更精巧：改用「根、右、左」的順序走訪，並帶著深度。這個順序保證了，**在同一個深度上，越右邊的節點越早被拜訪**，因為對任兩個同深度的節點，它們分岔的那個祖先會先走右邊的子樹。所以第一次到達深度 d 時遇到的節點，一定是第 d 層最右邊的那個。實作上只要判斷 `depth == len(res)`，代表這個深度還沒有人登記，就把目前節點記下來。

```text
root = [1, 2, 3, 4, 5, null, null, 6]

          1          深度 0
         / \
        2   3        深度 1
       / \
      4   5          深度 2
     /
    6                深度 3

DFS 順序（根、右、左）   depth   len(res)   動作
1                        0       0          登記 → res = [1]
3                        1       1          登記 → res = [1, 3]
2                        1       2          已登記，略過
5                        2       2          登記 → res = [1, 3, 5]
4                        2       3          已登記，略過
6                        3       3          登記 → res = [1, 3, 5, 6]
```

深度 2 有 4 和 5 兩個節點，因為先走右子樹，5 先被拜訪並登記，4 來的時候這一層已經有人了。深度 3 只有 6，它在左子樹最深處，但這一層沒有更右邊的節點，所以第一個到達的就是它，這正是「一直往右走」會漏掉的情況。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(random.randint(-9, 9)) for _ in range(n)]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0] if nodes else None


def right_side_view(root):
    if root is None:
        return []
    res, queue = [], deque([root])
    while queue:
        size = len(queue)
        for i in range(size):
            node = queue.popleft()
            if i == size - 1:                  # 這一層最後一個彈出的節點
                res.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
    return res


def right_side_view_dfs(root):
    res = []

    def dfs(node, depth):
        if node is None:
            return
        if depth == len(res):                  # 這個深度第一次被拜訪
            res.append(node.val)
        dfs(node.right, depth + 1)             # 先右後左
        dfs(node.left, depth + 1)

    dfs(root, 0)
    return res


def brute(root):
    levels, queue = [], deque([root] if root else [])
    while queue:
        levels.append([n.val for n in queue])
        queue = deque(c for n in queue for c in (n.left, n.right) if c)
    return [lvl[-1] for lvl in levels]


assert right_side_view(build_tree([1, 2, 3, None, 5, None, 4])) == [1, 3, 4]
assert right_side_view(build_tree([1, 2, 3, 4])) == [1, 3, 4]
assert right_side_view(build_tree([1, None, 3])) == [1, 3]
assert right_side_view(None) == [] == right_side_view_dfs(None)
assert right_side_view_dfs(build_tree([1, 2, 3, 4, 5, None, None, 6])) == [1, 3, 5, 6]
assert right_side_view(build_tree([1, 2])) == [1, 2]          # 只有左子節點
for _ in range(300):
    t = random_tree(random.randint(0, 15))
    assert right_side_view(t) == right_side_view_dfs(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

兩種寫法時間都是 O(n)，每個節點處理一次。BFS 版額外空間 O(w)，DFS 版 O(h)；在這題 n ≤ 100 時兩者都沒差，但若 n 到 10⁵ 且樹是鏈狀，DFS 的遞迴會超過 Python 的上限，BFS 不會（見 F4）。邊界情況：空樹回傳 `[]`；只有左子節點的樹（範例 `[1, 2]`）右視圖就是整條左鏈；樹的右半邊比左半邊淺時，深處的節點來自左子樹。BFS 版判斷「最後一個」要用迴圈前記下的 `size`，不能用迴圈中的 `len(queue)`，因為它一直在變。

### Follow-up

> [!question]- F1. 如果要左視圖呢？
> BFS 版改成記錄每一層的第一個節點（`i == 0`）；DFS 版改回「根、左、右」的順序，第一次到達某深度的節點就是最左邊的那個。複雜度不變，O(n) 時間。這個對比可以用來檢查自己是否真的理解 DFS 版的正確性：決定「誰先到達某個深度」的是左右子樹的走訪順序，所以視角換邊時只需要交換兩行遞迴呼叫。

> [!question]- F2. 如果要「從上往下看」的上視圖（top view）呢？
> 上視圖不再以「層」分組，而是以「行」（column）分組：根在第 0 行，左子節點行號減 1、右子節點加 1，每一行看得到的是最上面（深度最小）的節點。用 BFS 帶著行號走訪，因為 BFS 依深度遞增拜訪，所以每一行第一個被拜訪的節點就是答案，用 dict 記錄 `first[col]`；同時記下最小與最大行號，最後依序輸出，不需要排序，O(n)。若用 DFS，必須同時記錄深度並比較，因為 DFS 不保證先拜訪較淺的節點。這是難題 4（987）的簡化版。

> [!question]- F3. 如果要回傳整棵樹的「邊界」，也就是左邊界、所有葉子、右邊界逆序（545. Boundary of Binary Tree）呢？
> 拆成三段分別收集：左邊界是從根的左子節點開始，有左走左、沒左走右，直到葉子之前；葉子用一次 DFS 由左到右收集；右邊界對稱地從根的右子節點開始，有右走右、沒右走左，最後逆序。三段都不包含葉子，避免葉子被重複加入，根單獨放在最前面。總時間 O(n)。注意這裡的「左邊界」是沿著樹的邊緣走的路，和左視圖不同：左視圖是每層最左的節點，可能不在同一條路上。

> [!question]- F4. 如果 n 高達 10⁵，而且樹可能是一條鏈呢？
> 遞迴 DFS 會超過 Python 預設約 1000 層的上限。BFS 版不受影響，空間 O(w)，鏈狀時 w = 1，是最好的選擇。若想保留 DFS 的「先右後左」寫法，可以用顯式 stack 存 `(node, depth)`：先推左子節點、再推右子節點，這樣右子節點會先彈出，維持「根、右、左」的順序；判斷 `depth == len(res)` 的邏輯完全不變。時間仍是 O(n)，空間 O(h)。

## 核心題 3｜543. Diameter of Binary Tree｜Easy

### 題目

給一棵二元樹，回傳它的直徑：任兩個節點之間最長路徑的長度，長度以**邊數**計算。這條路徑不一定經過根。限制：節點數在 `1` 到 `10⁴` 之間，節點值在 `-100` 到 `100` 之間。

- 範例 1：`root = [1, 2, 3, 4, 5]`，回傳 `3`，路徑是 4 → 2 → 1 → 3（或 5 → 2 → 1 → 3）。
- 範例 2：`root = [1, 2]`，回傳 `1`。
- 範例 3（邊界）：`root = [1]`，回傳 `0`；只有一個節點時沒有任何邊。
- 範例 4（不經過根）：`root = [1, 2, null, 3, 4, 5, null, null, 6]`，回傳 `4`，路徑是 5 → 3 → 2 → 4 → 6，全部在根的左子樹裡；經過根的最長路徑 1 → 2 → 3 → 5 只有 3 條邊。

### 思路

先找一個好用的分類方式：樹上的任何一條路徑，都有唯一一個「最高點」（離根最近的節點），路徑從最高點往左下延伸一段、往右下延伸一段（任一段可以是空的）。所以「以 v 為最高點的最長路徑」= v 的左子樹往下最長的長度 + 右子樹往下最長的長度，而直徑就是所有 v 中的最大值。這個分類保證了不會漏掉任何路徑，也包含了「不經過根」的情況。

暴力做法直接照這個定義算：對每個節點呼叫 `height(left) + height(right)`，每次 `height` 都要走過整棵子樹。平衡樹上每層總共 O(n)，共 O(log n) 層，是 O(n log n)；但鏈狀的樹上，第 k 個節點要走 n − k 個節點，總共 O(n²)。瓶頸很清楚：每個子樹的高度被祖先們重複計算。

改進的方法是讓一次後序走訪同時完成兩件事。定義 `depth(node)` = 從 node 往下最長的路徑有幾個**節點**（空樹是 0）。這個值剛好等於「從 node 的父節點往下、經過 node 的那一段有幾條邊」，所以在 node 這裡，`depth(left) + depth(right)` 就是以 node 為最高點的最長路徑的邊數。函式回傳 `1 + max(left, right)` 給父節點（父節點只能接上其中一邊，否則路徑會分叉），同時把 `left + right` 拿去更新全域的 `best`。每個節點只算一次，O(n)。

```text
root = [1, 2, null, 3, 4, 5, null, null, 6]

          1
         /
        2
       / \
      3   4
     /     \
    5       6

後序順序  left  right  left+right（更新 best）  回傳 1+max
5         0     0      0  → best = 0            1
3         1     0      1  → best = 1            2
6         0     0      0                        1
4         0     1      1                        2
2         2     2      4  → best = 4            3
1         3     0      3                        4
答案 best = 4（以 2 為最高點：5-3-2-4-6）
```

在節點 2，左邊回傳 2（3 → 5 兩個節點）、右邊回傳 2（4 → 6），兩段接起來是 4 條邊，這是全樹最長的路徑。可是 2 回傳給 1 的只有 3，也就是「從 1 往下經過 2 的單邊」，因為 1 如果要用這條路徑，只能從 2 往其中一邊延伸。這就是「回傳值」與「全域答案」不同的原因。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(random.randint(-9, 9)) for _ in range(n)]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0] if nodes else None


def diameter_of_binary_tree(root) -> int:
    best = 0

    def depth(node) -> int:                   # 合約：從 node 往下最長路徑的「節點數」
        nonlocal best
        if node is None:
            return 0
        left = depth(node.left)
        right = depth(node.right)
        best = max(best, left + right)        # 以 node 為最高點的最長路徑（邊數）
        return 1 + max(left, right)

    depth(root)
    return best


def brute(root):                              # O(n²)：每個節點重新算兩邊高度
    def height(node):
        return 0 if node is None else 1 + max(height(node.left), height(node.right))

    def walk(node):
        if node is None:
            return 0
        return max(height(node.left) + height(node.right), walk(node.left), walk(node.right))

    return walk(root)


assert diameter_of_binary_tree(build_tree([1, 2, 3, 4, 5])) == 3
assert diameter_of_binary_tree(build_tree([1, 2])) == 1
assert diameter_of_binary_tree(build_tree([1])) == 0
assert diameter_of_binary_tree(build_tree([1, 2, None, 3, 4, 5, None, None, 6])) == 4
assert diameter_of_binary_tree(build_tree([1, 2, None, 3, None, 4])) == 3      # 鏈：n - 1
for _ in range(300):
    t = random_tree(random.randint(1, 15))
    assert diameter_of_binary_tree(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，每個節點只做一次常數工作；空間 O(h) 是遞迴深度，鏈狀時 h = n = 10⁴，超過 Python 預設的遞迴上限，正式寫法要調高上限或改用 12.5 節的迭代後序。邊界情況：單一節點直徑為 0（left + right = 0）；鏈狀樹的直徑是 n − 1，最高點是鏈的頂端；最長路徑不經過根時，答案在某個內部節點被更新，所以絕對不能只回傳 `depth(root.left) + depth(root.right)`。要特別注意「節點數」與「邊數」：這裡讓 `depth` 回傳節點數，`left + right` 剛好是邊數；如果改讓 `depth` 回傳邊數，空樹就要是 -1，而組合式要變成 `left + right + 2`。

### Follow-up

> [!question]- F1. 如果要回傳直徑路徑上的節點，而不只是長度呢？
> 在更新 `best` 時一併記下當時的最高點 `top`。結束後，從 `top.left` 開始「每次往比較深的子節點走」直到葉子，得到左半段；右半段同理從 `top.right` 開始。要知道哪個子節點比較深，需要每個節點的 depth，所以第一遍走訪時把 depth 存進 dict。左半段反轉、接上 `top`、再接右半段，就是整條路徑。總時間 O(n)，空間 O(n) 存 depth。

> [!question]- F2. 如果是 N-ary tree，每個節點有任意多個子節點（1522. Diameter of N-Ary Tree）呢？
> 以 v 為最高點的最長路徑，是從所有子節點中挑**最深的兩個**接起來。走訪子節點時維護前兩名 `first ≥ second`，用 `first + second` 更新答案，回傳 `1 + first`。維護前兩名是 O(子節點數)，不需要排序，所以總時間仍是 O(n)。這個「前兩名」技巧在難題 5 的另一種解法裡也會出現。

> [!question]- F3. 如果樹是用邊的列表給的一般樹（沒有指定根，1245. Tree Diameter）呢？
> 兩種做法。第一，任選一個點當根，用 F2 的「前兩名」DFS，O(n)。第二，two-pass BFS：從任意點 s 做 BFS 找到最遠點 u，再從 u 做 BFS 找到最遠點 v，dist(u, v) 就是直徑。正確性的關鍵是「離任意點最遠的點，一定是某條直徑的端點」，可以用反證法證明：若 u 不是直徑端點，把直徑和 s → u 的路徑接起來會得到更長的路徑。兩種都是 O(n)。

> [!question]- F4. 如果邊有權重（可能為負）呢？
> 後序做法照用，只是 `depth` 改成「往下最大的權重和」，而且要像難題 1（124）一樣用 `max(0, 子節點的值 + 邊權)`，因為負的那一段乾脆不要接，路徑在這裡停下來更好。two-pass BFS（F3）在權重非負時改用 DFS 算距離就行，但有負權重時「最遠點是直徑端點」的性質不再成立，不能用。所以面試官追問負權重時，正確答案是回到後序做法。

> [!question]- F5. 如果只能走「節點值都相同」的路徑（687. Longest Univalue Path）呢？
> 合約改成「從 node 往下、所有節點值都等於 node.val 的最長單邊路徑的邊數」。左子節點存在且值相同時，左邊的貢獻是 `1 + arm(left)`，否則是 0；右邊同理。用左右貢獻的和更新答案，回傳較大的一邊。注意即使子節點的值不同，也一定要遞迴下去，因為子樹內部可能有更長的同值路徑。O(n) 時間、O(h) 空間。

## 核心題 4｜105. Construct Binary Tree from Preorder and Inorder Traversal｜Medium

### 題目

給一棵二元樹的前序走訪 `preorder` 與中序走訪 `inorder`，兩者都是長度 n 的整數陣列，而且**樹中的值互不相同**。請重建並回傳這棵樹。限制：`1 <= n <= 3000`，節點值在 `-3000` 到 `3000` 之間，保證輸入合法。

- 範例 1：`preorder = [3, 9, 20, 15, 7]`、`inorder = [9, 3, 15, 20, 7]`，回傳 `[3, 9, 20, null, null, 15, 7]`。
- 範例 2（邊界）：`preorder = [-1]`、`inorder = [-1]`，回傳 `[-1]`。
- 範例 3（往左的鏈）：`preorder = [1, 2, 3]`、`inorder = [3, 2, 1]`，回傳 `[1, 2, null, 3]`。
- 範例 4（往右的鏈）：`preorder = [1, 2, 3]`、`inorder = [1, 2, 3]`，回傳 `[1, null, 2, null, 3]`。

### 思路

兩種走訪各提供一半的資訊。前序是「根、左子樹、右子樹」，所以 `preorder[0]` 一定是根；中序是「左子樹、根、右子樹」，所以只要在 `inorder` 裡找到根的位置 `mid`，左邊 `inorder[:mid]` 就是左子樹的全部節點，右邊是右子樹。左子樹有 `mid` 個節點，因此前序中緊接在根後面的 `mid` 個元素就是左子樹的前序，剩下的是右子樹的前序。兩邊各自是同樣的子問題，遞迴下去即可。值互不相同是必要條件，否則根在中序裡的位置不唯一。

最直接的寫法是每層都切片並呼叫 `inorder.index(root)`：每次切片與搜尋都是 O(子樹大小)，平衡樹時是 O(n log n)，但鏈狀的樹是 O(n²)。兩個改進：第一，預先建 `pos[value] = 中序索引` 的 hash map，找根變成 O(1)；第二，不要切片，改用索引範圍 `[lo, hi)` 表示目前子樹在中序裡的區段。

前序那一邊還可以更簡單：遞迴的呼叫順序本身就是「先建根、再建左子樹、再建右子樹」，剛好和前序的順序一致。所以只要用一個 iterator（或全域索引）依序從 `preorder` 取值，每建立一個節點取一個，就會自動拿到正確的根，完全不需要計算前序的區間。這樣每個節點 O(1)，總共 O(n)。

```text
preorder = [3, 9, 20, 15, 7]     inorder = [9, 3, 15, 20, 7]
pos = {9: 0, 3: 1, 15: 2, 20: 3, 7: 4}

呼叫 build(lo, hi)    取出的 preorder 值   pos   左子樹區間   右子樹區間
build(0, 5)           3                    1     [0, 1)       [2, 5)
  build(0, 1)         9                    0     [0, 0) 空    [1, 1) 空
  build(2, 5)         20                   3     [2, 3)       [4, 5)
    build(2, 3)       15                   2     空           空
    build(4, 5)       7                    4     空           空

結果：      3
           / \
          9   20
             /  \
            15   7
```

注意空區間的呼叫（`lo >= hi`）直接回傳 `None`，**不會**從 iterator 取值，所以取值的次數恰好是 n 次，和前序的長度一致。建完 9 的左右子樹（都是空的）之後，iterator 的下一個值 20 正好是根的右子樹的根，這就是「前序順序 = 遞迴建構順序」的意思。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def to_list(root):
    out, queue = [], deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out


def random_tree(n):
    vals = random.sample(range(-50, 50), n)          # 值互不相同
    nodes = [TreeNode(v) for v in vals]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0] if nodes else None


def traversals(root):
    pre, ino = [], []
    def go(node):
        if node:
            pre.append(node.val)
            go(node.left)
            ino.append(node.val)
            go(node.right)
    go(root)
    return pre, ino


def build_from_pre_in(preorder, inorder):
    pos = {v: i for i, v in enumerate(inorder)}
    nxt = iter(preorder)

    def build(lo, hi):                    # 用 inorder[lo:hi] 這一段建子樹
        if lo >= hi:
            return None
        root = TreeNode(next(nxt))        # 前序順序 = 建構順序
        mid = pos[root.val]
        root.left = build(lo, mid)
        root.right = build(mid + 1, hi)
        return root

    return build(0, len(inorder))


def build_from_pre_in_iter(preorder, inorder):
    """迭代版：stack 存「右子樹還沒開始建」的祖先，適合很深的樹。"""
    if not preorder:
        return None
    root = TreeNode(preorder[0])
    stack, j = [root], 0                  # inorder[j] 是下一個要「完成左子樹」的節點
    for v in preorder[1:]:
        node = TreeNode(v)
        parent = stack[-1]
        if parent.val != inorder[j]:      # parent 的左子樹還沒走完，v 是它的左子節點
            parent.left = node
        else:                             # 往上找到最後一個左子樹已完成的祖先
            while stack and stack[-1].val == inorder[j]:
                parent = stack.pop()
                j += 1
            parent.right = node
        stack.append(node)
    return root


assert to_list(build_from_pre_in([3, 9, 20, 15, 7], [9, 3, 15, 20, 7])) == [3, 9, 20, None, None, 15, 7]
assert to_list(build_from_pre_in([-1], [-1])) == [-1]
assert to_list(build_from_pre_in([1, 2, 3], [3, 2, 1])) == [1, 2, None, 3]
assert to_list(build_from_pre_in([1, 2, 3], [1, 2, 3])) == [1, None, 2, None, 3]
for _ in range(300):
    t = random_tree(random.randint(1, 15))
    pre, ino = traversals(t)
    assert to_list(build_from_pre_in(pre, ino)) == to_list(t) == to_list(build_from_pre_in_iter(pre, ino))
deep = list(range(3000))                  # 3000 層的左鏈：前序遞增、中序遞減
assert to_list(build_from_pre_in_iter(deep, deep[::-1]))[:3] == [0, 1, None]
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：建 hash map O(n)，之後每個節點 O(1)，空區間的呼叫最多 n + 1 次。空間 O(n) 給 hash map，加上 O(h) 的遞迴深度。迭代版同樣 O(n)：每個節點進 stack、出 stack 各一次。邊界情況：n = 1 時直接回傳單一節點；鏈狀樹的遞迴深度是 n = 3000，超過 Python 預設上限，所以附上迭代版，或在遞迴版前 `sys.setrecursionlimit`；值必須互不相同，否則 `pos` 會被覆蓋、結果不唯一（見 F4）；若 iterator 用完卻還在呼叫 `next`，代表輸入不一致，會丟出 `StopIteration`。

### Follow-up

> [!question]- F1. 如果給的是中序與後序（106）呢？
> 後序是「左、右、根」，所以最後一個元素是根。從後序的**尾端**往前取值，取出的順序是「根、右子樹的根、……」，因此遞迴時必須**先建右子樹、再建左子樹**，才能和取值順序對上。其餘完全相同：用 `pos` 找根在中序的位置、用索引區間代替切片。O(n) 時間與空間。這個「取值順序必須等於建構順序」的觀念，是能不能寫對 105、106、889 三題的關鍵。

> [!question]- F2. 如果給的是前序與後序（889）呢？
> 前序加後序一般無法唯一決定一棵樹：只有一個子節點的節點，它的子節點是左是右分辨不出來，例如 `[1, 2]` 與 `[1, null, 2]` 的前序都是 `[1, 2]`、後序都是 `[2, 1]`。題目因此只要求回傳任一個合法的樹。做法是把 `preorder[1]` 當作左子樹的根，在後序中找到它的位置 k，左子樹的大小就是 k − 起點 + 1，再分別遞迴。用 hash map 存後序位置，O(n)。

> [!question]- F3. 如果只給 BST 的前序（1008. Construct BST from Preorder Traversal）呢？
> BST 的中序就是排序後的序列，所以可以先排序得到中序，再套本題，O(n log n)。更好的做法是帶上界遞迴：`build(bound)` 只在下一個前序值 < bound 時建立節點，左子樹的上界是目前的值，右子樹沿用原本的上界，每個值只被看一次，O(n)。這是第 13 章「BST 用上下界取代中序」的典型手法。

> [!question]- F4. 如果值可能重複呢？
> 重建不再唯一，例如前序 `[1, 1]`、中序 `[1, 1]` 可以是「1 的左子節點是 1」也可以是「右子節點是 1」。面試時應該先指出這點，然後問面試官要「任一個」還是「全部」。要任一個時，可以在中序區間內選任一個值相等、且讓左右兩邊的元素集合能和前序對上的位置；要全部時是 backtracking（第 19 章），數量可能是指數級。實務上的正確解法是改用難題 2 的序列化格式，把空節點也寫進去，就沒有歧義。

> [!question]- F5. 如果輸入可能不合法，要先驗證呢？
> 在建構過程中檢查三件事：`preorder` 與 `inorder` 長度相同且值的集合相同（O(n) 用 set 比較）、值互不相同、每次取出的根都落在目前的中序區間 `[lo, hi)` 內。第三點是關鍵：若 `pos[root.val]` 不在區間內，代表這個值應該屬於別的子樹，輸入不一致，立刻回傳錯誤。全部檢查都是 O(1) 或 O(n) 的額外工作，總時間仍是 O(n)。

## 核心題 5｜236. Lowest Common Ancestor of a Binary Tree｜Medium

### 題目

給一棵二元樹（**不是** BST）以及樹中的兩個節點 `p`、`q`，回傳它們的最低共同祖先（lowest common ancestor，LCA）：同時是 p 與 q 的祖先、而且深度最大的那個節點。一個節點也算是自己的祖先。限制：節點數在 `2` 到 `10⁵` 之間，值互不相同，`p != q`，而且 p、q 一定都在樹中。

以下範例都用這棵樹 `[3, 5, 1, 6, 2, 0, 8, null, null, 7, 4]`：

- 範例 1：`p = 5`、`q = 1`，回傳 `3`。
- 範例 2：`p = 5`、`q = 4`，回傳 `5`；5 是 4 的祖先，而節點可以是自己的祖先。
- 範例 3：`p = 6`、`q = 4`，回傳 `5`。
- 範例 4（邊界）：樹 `[1, 2]`、`p = 1`、`q = 2`，回傳 `1`。

### 思路

最直覺的做法是分別找出「根到 p」和「根到 q」的路徑，然後從頭比較兩條路徑，最後一個相同的節點就是 LCA。找路徑各要一次 O(n) 的 DFS，比較是 O(h)，總共 O(n) 時間、O(h) 空間，這已經是漸進最佳的，面試時可以先說出來。但它要走兩遍、要存路徑，程式也比較長。更笨的暴力是對每個節點檢查「它的子樹是否同時包含 p 與 q」，每次檢查 O(子樹大小)，總共 O(n²)。

一次後序就能解決。定義 `lca(node)` 的合約：**如果 node 的子樹裡有 p 或 q，回傳「找到的東西」，否則回傳 None**；「找到的東西」在兩者都在子樹裡時就是它們的 LCA，只有一個在時就是那一個。組合規則：若 node 本身是 p 或 q，直接回傳 node；否則看左右子樹的回傳值，兩邊都非空，代表 p、q 分別在兩邊，node 就是分岔點，也就是 LCA；只有一邊非空，就把那一邊的結果往上傳。

為什麼遇到 p 就可以直接回傳，不必再往下找 q？因為題目保證 p、q 都在樹中。如果 q 在 p 的子樹裡，LCA 就是 p 本身，回傳 p 是對的；如果 q 不在 p 的子樹裡，q 一定在別的地方，會在某個祖先處和 p 的回傳值相遇，那個祖先才是 LCA，p 往上傳的值也沒有錯。這個「提早回傳」依賴題目的保證，F1 會討論不保證存在時要怎麼改。

```text
          3
        /   \
       5     1
      / \   / \
     6   2 0   8
        / \
       7   4

p = 6，q = 4（後序：子樹先回傳，父節點再組合）
節點  左回傳  右回傳  本節點回傳  原因
6     —       —       6           自己是 p，直接回傳
7     None    None    None
4     —       —       4           自己是 q，直接回傳
2     None    4       4           只有右邊找到，往上傳
5     6       4       5           兩邊都非空 → 5 是分岔點
0     None    None    None
8     None    None    None
1     None    None    None
3     5       None    5           只有左邊有結果，往上傳
答案：5
```

節點 2 收到右邊回傳的 4，但不知道 p 在哪裡，所以只是把 4 往上交；節點 5 同時收到 6 和 4，這是第一個「兩邊都有」的節點，於是它把自己當成答案往上傳；3 只看到左邊有結果，原樣轉交。最後根回傳的 5 就是 LCA。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(v) for v in random.sample(range(100), n)]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0], nodes


def find(root, val):
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node.val == val:
            return node
        queue.extend(c for c in (node.left, node.right) if c)
    return None


def lowest_common_ancestor(root, p, q):
    if root is None or root is p or root is q:
        return root
    left = lowest_common_ancestor(root.left, p, q)
    right = lowest_common_ancestor(root.right, p, q)
    if left and right:                      # p、q 分別在兩邊：root 是分岔點
        return root
    return left or right                    # 只有一邊找到（或都沒有）就往上傳


def lca_by_paths(root, p, q):               # 對照：兩條根到節點的路徑取最長共同前綴
    def path(node, target, acc):
        if node is None:
            return False
        acc.append(node)
        if node is target or path(node.left, target, acc) or path(node.right, target, acc):
            return True
        acc.pop()
        return False
    a, b = [], []
    path(root, p, a)
    path(root, q, b)
    ans = None
    for x, y in zip(a, b):
        if x is not y:
            break
        ans = x
    return ans


root = build_tree([3, 5, 1, 6, 2, 0, 8, None, None, 7, 4])
for pv, qv, want in [(5, 1, 3), (5, 4, 5), (6, 4, 5), (7, 8, 3), (0, 8, 1)]:
    assert lowest_common_ancestor(root, find(root, pv), find(root, qv)).val == want
small = build_tree([1, 2])
assert lowest_common_ancestor(small, small, small.left) is small
for _ in range(300):
    r, nodes = random_tree(random.randint(2, 15))
    p, q = random.sample(nodes, 2)
    assert lowest_common_ancestor(r, p, q) is lca_by_paths(r, p, q)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：最差要走過每個節點一次（提早回傳只會更快）。空間 O(h) 的遞迴深度；n 可到 10⁵，鏈狀時會超過 Python 的遞迴上限，要調高上限或改用 F2 的 parent 指標做法（先用 BFS 建 parent map，完全不需要遞迴）。邊界情況：p 是 q 的祖先時答案是 p（範例 2），由「遇到 p 就回傳」自然處理；p、q 其中一個是根時答案是根；比較節點要用 `is`，題目給的是節點物件，雖然本題值互不相同，用物件比較仍是較穩健的習慣。`left or right` 依賴 TreeNode 物件在 Python 中永遠為真，即使它的值是 0。

### Follow-up

> [!question]- F1. 如果 p 或 q 可能不在樹中，不存在時要回傳 None（1644）呢？
> 「遇到 p 就提早回傳」不再安全：若 q 不在樹中，原本的程式仍會回傳 p。改法是走完整棵樹，並用一個計數器記錄找到了幾個目標：先遞迴左右子樹，再檢查自己是否為 p 或 q（是就計數加一），組合規則不變。最後只有計數等於 2 時才回傳結果，否則回傳 None。仍是一次後序，O(n) 時間、O(h) 空間。重點是把「檢查自己」移到遞迴之後，確保子樹一定被走訪。

> [!question]- F2. 如果每個節點有指向父節點的指標，而且沒有給根（1650）呢？
> 從 p 和 q 各自往上走就是兩條在 LCA 相交的 linked list，問題變成第 11 章的「兩條 linked list 的交點」。用兩個指標 a、b 分別從 p、q 出發往上走，走到根的上方（None）時跳到另一個起點；設 p、q 到 LCA 的距離分別是 x、y，LCA 到根（含）共 z 個節點：a 走 x + z 步到根的上方後跳到 q、再走 y 步，b 對稱地走 y + z 步後跳到 p、再走 x 步，兩者的總步數相同，所以一定同時抵達 LCA。O(h) 時間、O(1) 空間。也可以先把 p 的所有祖先放進 set，再從 q 往上找第一個在 set 裡的，O(h) 時間、O(h) 空間。

> [!question]- F3. 如果是 BST（235. Lowest Common Ancestor of a BST）呢？
> 利用大小關係，不必走訪整棵樹：從根開始，若 p、q 的值都小於目前節點，LCA 在左子樹；都大於則在右子樹；否則（一個 ≤、一個 ≥，或等於目前節點）目前節點就是分岔點。每一步往下一層，O(h) 時間、O(1) 空間的迭代寫法。這是第 13 章的內容，但面試官常在 236 之後接著問，用來確認你知道一般樹與 BST 的差異。

> [!question]- F4. 如果同一棵樹要回答 q 次 LCA 查詢呢？
> 每次 O(n) 共 O(q · n)，查詢多時太慢。標準做法是 binary lifting（倍增）：BFS 求出每個節點的深度與父節點，再建 `up[k][v]` = v 往上 2^k 步的祖先，前處理 O(n log n)。查詢時先把較深的節點往上跳到同一深度，再從大到小嘗試讓兩者同時往上跳 2^k 步，只要跳完不相同就跳，最後兩者的父節點就是 LCA，每次 O(log n)。若可以離線處理，也可以用 Tarjan 的離線 LCA 搭配 Union-Find（第 17 章），總共約 O(n + q)。
> ```python
> def build_lca(root):
>     LOG = max(1, (10**5).bit_length())
>     parent, depth, order = {root: None}, {root: 0}, [root]
>     for node in order:
>         for c in (node.left, node.right):
>             if c:
>                 parent[c], depth[c] = node, depth[node] + 1
>                 order.append(c)
>     up = [parent]
>     for _ in range(1, LOG):
>         prev = up[-1]
>         up.append({v: prev[prev[v]] if prev[v] else None for v in order})
>     def lca(a, b):
>         if depth[a] < depth[b]:
>             a, b = b, a
>         diff = depth[a] - depth[b]
>         for k in range(LOG):
>             if diff >> k & 1:
>                 a = up[k][a]
>         if a is b:
>             return a
>         for k in reversed(range(LOG)):
>             if up[k][a] is not up[k][b]:
>                 a, b = up[k][a], up[k][b]
>         return up[0][a]
>     return lca
> ```

> [!question]- F5. 如果要的是一組 k 個節點的 LCA（1676）呢？
> 把 p、q 換成一個 set：遇到在 set 裡的節點就直接回傳它，組合規則不變（兩邊都非空就回傳自己）。正確性的理由和原題相同：所有目標都保證在樹中，遇到某個目標時，它子樹裡的其他目標不影響答案，因為 LCA 一定是它或它的祖先。仍是 O(n) 時間，額外 O(k) 空間放 set。另一種做法是兩兩做 LCA 再合併，但那要 k − 1 次 O(n)，比較慢。

## 難題 1｜124. Binary Tree Maximum Path Sum｜Hard

### 題目

樹上的一條路徑是一串由邊相連的節點，每個節點最多出現一次，至少包含一個節點，不一定經過根，也不必從葉子開始或結束。路徑和是路徑上所有節點值的總和。給一棵二元樹，回傳所有路徑中最大的路徑和。限制：節點數在 `1` 到 `3 × 10⁴` 之間，節點值在 `-1000` 到 `1000` 之間。

- 範例 1：`root = [1, 2, 3]`，回傳 `6`，路徑 2 → 1 → 3。
- 範例 2：`root = [-10, 9, 20, null, null, 15, 7]`，回傳 `42`，路徑 15 → 20 → 7，不經過根。
- 範例 3（邊界）：`root = [-3]`，回傳 `-3`；路徑至少要有一個節點，不能回傳 0。
- 範例 4：`root = [2, -1]`，回傳 `2`；接上 -1 只會讓和變小，最佳路徑只有根自己。

### 提示

> [!tip]- 提示 1
> 這題和核心題 3（直徑）是同一個結構：每條路徑都有唯一的最高點。把「以 v 為最高點的最佳路徑」想清楚，答案就是所有 v 的最大值。

> [!tip]- 提示 2
> 以 v 為最高點的路徑 = v 自己 + 從左子節點往下的一段 + 從右子節點往下的一段，兩段都可以不要。所以每個子樹要回傳的是「從這個節點往下、只走一邊的最大和」。

> [!tip]- 提示 3
> 定義 `gain(v) = v.val + max(0, gain(左), gain(右))`，回傳給父節點；同時用 `v.val + max(0, gain(左)) + max(0, gain(右))` 更新全域答案。全域答案的初始值要是負無限大，不是 0。

### 詳解

**為什麼直覺做法不夠**。最暴力的做法是枚舉所有點對 (u, w)，算出它們之間唯一路徑的和，共 O(n²) 對，每對算路徑 O(n)，總共 O(n³)；改成從每個節點出發做一次 DFS、沿路累加，可以降到 O(n²)，n = 3 × 10⁴ 時是 9 × 10⁸，太慢。另一個常見的錯誤直覺是「直接套直徑的寫法，把高度換成和」：直徑中每段的長度都是非負的，所以兩邊都接一定不會變差；但這題有負數，接上一段負的路徑會讓和變小，必須允許「這一邊不接」。

**突破點：以最高點分類，並把負的分支剪掉**。和核心題 3 一樣，每條路徑都有唯一的最高點 v，路徑由「v 往左下的一段」、v、「v 往右下的一段」組成。定義 `gain(v)` = 從 v 往下走、只能走一邊的路徑的最大和，而且一定包含 v。往下的那一段，可以接左邊、接右邊、或都不接，所以 `gain(v) = v.val + max(0, gain(left), gain(right))`；`max(0, ·)` 就是「如果子樹給的收益是負的，就不要它」。以 v 為最高點的最佳路徑則是 `v.val + max(0, gain(left)) + max(0, gain(right))`，兩邊可以同時接。

**回傳值與全域答案必須分開**。回傳給父節點的 `gain(v)` 只能包含一邊，因為父節點要把 v 接到自己的路徑上，如果 v 同時往左右延伸，加上父節點後 v 會有三條邊，路徑就分叉了。兩邊同時接的情況只能「在 v 這裡結算」，用來更新全域的 `best`。這正是 12.4 節說的第三種資訊流：組合兩邊更新全域答案，回傳單邊給父節點。

**正確性與初始值**。每條路徑恰好在它的最高點被結算一次，而 v 處算出的值是所有「以 v 為最高點」路徑中的最大值（左右兩段各自獨立地取最大，或者不要），所以 `best` 是全域最大。`best` 必須初始化成負無限大：全部節點都是負數時，答案是最大的那個負數（範例 3），若初始化成 0 會錯誤地回傳 0，等於選了「空路徑」。另外 `gain(None)` 回傳 0 是安全的，因為外面一律套 `max(0, ·)`，空子樹的貢獻本來就是 0。

```text
root = [-10, 9, 20, null, null, 15, 7]

        -10
        /  \
       9    20
           /  \
          15   7

後序順序  左收益  右收益  以本節點為最高點（更新 best）   回傳 gain
9         0       0       9               → best = 9      9
15        0       0       15              → best = 15     15
7         0       0       7                               7
20        15      7       20 + 15 + 7 = 42 → best = 42    20 + 15 = 35
-10       9       35      -10 + 9 + 35 = 34               -10 + 35 = 25
答案 best = 42
```

在 20 這個節點，左右兩邊都接上得到 42，這條路徑在這裡結算；但 20 回傳給 -10 的只有 35（接較好的左邊 15），因為 -10 只能經過 20 往其中一邊走。到了根，最佳也只有 34，比 42 小，所以最大路徑不經過根。若把 -10 改成 +10，根處就是 10 + 9 + 35 = 54，最佳路徑會變成經過根的 9 → 10 → 20 → 15。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(random.randint(-9, 9)) for _ in range(n)]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0] if nodes else None


def max_path_sum(root) -> int:
    best = float("-inf")

    def gain(node) -> int:                    # 從 node 往下、只走一邊的最大和（含 node）
        nonlocal best
        if node is None:
            return 0
        left = max(gain(node.left), 0)        # 負的收益乾脆不要
        right = max(gain(node.right), 0)
        best = max(best, node.val + left + right)    # 以 node 為最高點，兩邊都可接
        return node.val + max(left, right)           # 給父節點只能一邊

    gain(root)
    return best


def brute(root):                              # O(n²)：從每個節點出發走遍所有簡單路徑
    adj, stack = {}, [root]
    while stack:
        node = stack.pop()
        adj.setdefault(node, [])
        for c in (node.left, node.right):
            if c:
                adj[node].append(c)
                adj.setdefault(c, []).append(node)
                stack.append(c)
    best = float("-inf")
    for start in adj:
        todo = [(start, None, start.val)]
        while todo:
            node, came, s = todo.pop()
            best = max(best, s)
            for nb in adj[node]:
                if nb is not came:
                    todo.append((nb, node, s + nb.val))
    return best


assert max_path_sum(build_tree([1, 2, 3])) == 6
assert max_path_sum(build_tree([-10, 9, 20, None, None, 15, 7])) == 42
assert max_path_sum(build_tree([-3])) == -3
assert max_path_sum(build_tree([2, -1])) == 2
assert max_path_sum(build_tree([-1, -2, -3])) == -1                  # 全負：取最大的單一節點
assert max_path_sum(build_tree([5, 4, 8, 11, None, 13, 4, 7, 2, None, None, None, 1])) == 48
for _ in range(500):
    t = random_tree(random.randint(1, 12))
    assert max_path_sum(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，每個節點只做常數工作；空間 O(h) 的遞迴深度，n = 3 × 10⁴ 的鏈會超過 Python 的預設上限，要調高上限，或用 12.5 節的「BFS 順序反向處理」改成迭代：反向走訪時從 dict 讀子節點的 gain，算法完全相同。邊界情況：全部是負數時答案是最大的單一節點，所以 `best` 初始為負無限大；單一節點時答案就是它的值；`gain` 本身可能是負的（節點值為負且兩邊都不接），這是正確的，只是父節點會用 `max(0, ·)` 決定不接它。值的範圍很小，總和最多 3 × 10⁷，不會有溢位問題。

### Follow-up

> [!question]- F1. 如果要回傳最佳路徑本身（節點序列）呢？
> 在更新 `best` 時記下當時的最高點 `top`，以及左右兩邊是否有接（`left > 0`、`right > 0`）。為了往下重建，第一遍要把每個節點的 gain 存進 dict。重建單邊時，從某個子節點開始，每次選 gain 較大且為正的子節點往下走，直到兩邊的收益都不是正的為止。左半段反轉、接上 top、再接右半段。總時間 O(n)，空間 O(n)。

> [!question]- F2. 如果路徑只能「由上往下」，也就是從某個節點走到它的某個子孫呢？
> 那就沒有「兩邊同時接」的情況了，答案是所有節點中 `gain(v)` 的最大值，其中 `gain(v) = v.val + max(0, gain(left), gain(right))` 和原題完全相同。更新答案時用 `gain(v)` 而不是兩邊相加。仍是 O(n)。若再限制「必須從根開始、到葉子結束」，就不能用 `max(0, ·)` 剪掉分支，因為一定要走到葉子：`f(v) = v.val + max(f(子節點))`，只對存在的子節點取最大，葉子時 `f = v.val`。

> [!question]- F3. 如果路徑的兩端都必須是葉子呢？
> 只有左右兩個子節點都存在的節點，才能當作連接兩片葉子的最高點。定義 `down(v)` = 從 v 到它子樹中某片葉子的最大和（必須走到葉子，不能用 0 剪掉）。在兩個子節點都存在的節點用 `v.val + down(left) + down(right)` 更新答案；`down(v)` 在只有一個子節點時只能接那一邊。注意根若只有一個子節點，根本身也算是葉子端點的特殊情況，題目定義要先問清楚。O(n)。

> [!question]- F4. 如果是一般的樹（N-ary）或用邊列表給的樹呢？
> 結構相同，只是每個節點有很多子節點：以 v 為最高點時，從所有子節點的 `max(0, gain(c))` 中挑最大的兩個加上 v.val 更新答案，回傳 v.val 加上最大的一個。維護前兩名是 O(子節點數)，總時間 O(n)。用邊列表時任選一點當根做 DFS，記得傳入父節點避免走回頭。如果是一般的圖（有環），「最大和的簡單路徑」是 NP-hard 的最長路徑問題，沒有多項式解，樹的結構正是讓本題能 O(n) 的關鍵。

### 心得

關鍵突破是「每條路徑在最高點結算一次」，於是一次後序就能考慮所有路徑；而負數讓我們必須用 `max(0, ·)` 允許「這一邊不接」。它和核心題 3 是同一個模板，差別只有兩個：值可以是負的，所以要剪枝；路徑至少一個節點，所以初始值是負無限大。面試時先畫出「以 v 為最高點的路徑 = 左段 + v + 右段」，然後明確說出回傳值與全域答案為什麼不同，最後用全負的例子說明初始值。能把直徑和這題放在一起講，面試官就知道你掌握的是 pattern，而不是背了一題。

## 難題 2｜297. Serialize and Deserialize Binary Tree｜Hard

### 題目

設計一個 `Codec` 類別，包含兩個方法：`serialize(root)` 把一棵二元樹轉成字串，`deserialize(data)` 把字串轉回**結構與值完全相同**的樹。字串格式由你自己決定，只要兩個方法互為反函式即可，而且不能使用類別或全域變數保存狀態。限制：節點數在 `0` 到 `10⁴` 之間，節點值在 `-1000` 到 `1000` 之間。

- 範例 1：`root = [1, 2, 3, null, null, 4, 5]`，`deserialize(serialize(root))` 要得到同一棵樹。
- 範例 2（邊界）：`root = []`，空樹也要能來回轉換。
- 範例 3：`root = [-1000, 1000, null, -7]`，值有負數與多位數，格式必須能正確切開。
- 範例 4：`[1, 2]` 和 `[1, null, 2]` 是不同的樹，序列化的結果必須不同。

### 提示

> [!tip]- 提示 1
> 只記錄一種走訪（例如前序）的值不夠：範例 4 的兩棵樹前序都是 `1, 2`。少了什麼資訊？

> [!tip]- 提示 2
> 把空節點也寫出來（例如用 `#`）。帶空節點標記的前序，能唯一決定一棵樹。值之間要用分隔符號，因為值可能是負數或多位數。

> [!tip]- 提示 3
> 反序列化時用一個 iterator 依序讀 token：讀到 `#` 回傳 None，否則建立節點，先遞迴建左子樹、再建右子樹。讀 token 的順序就是前序，和序列化的順序完全一致。

### 詳解

**為什麼直覺做法不夠**。核心題 4 說明了「前序 + 中序」可以重建樹，所以一個直覺是把兩種走訪都存下來。但這有兩個問題：值必須互不相同（本題沒有這個保證），而且字串長度是兩倍。只存一種走訪的值則一定不夠，因為不同形狀的樹可以有相同的前序（範例 4）。缺的資訊是「哪裡沒有節點」，也就是樹的形狀。

**突破點：把空節點寫進去**。前序走訪時，遇到空節點也輸出一個 `#`。這樣每個子樹在字串中都變成一段「自我界定」的連續區段：一棵有 k 個節點的子樹恰好產生 k 個值和 k + 1 個 `#`（用歸納法：空樹是 0 個值、1 個 `#`；非空樹是 1 + 左邊 + 右邊，`#` 的數量是 (a + 1) + (b + 1) = (1 + a + b) + 1）。所以讀到一個值之後，接下來那一段一定是完整的左子樹，讀完左子樹的最後一個 `#` 時，自然就知道右子樹從哪裡開始，不需要任何長度資訊。

**反序列化：讓讀取順序等於建構順序**。和核心題 4 一樣，遞迴 `build()` 的執行順序是「建自己、建左子樹、建右子樹」，正好是前序。用一個 iterator 依序讀 token，每次呼叫 `build()` 讀一個：讀到 `#` 就回傳 None，讀到值就建立節點並依序遞迴左右。因為字串本身就是前序產生的，讀取順序與產生順序一一對應，所以建出來的樹和原本相同。整個過程每個 token 處理一次，O(n)。

**另一種格式：BFS 加空節點**。也可以用層序輸出，空節點同樣寫成 `#`（但空節點不再產生子節點），這正是 LeetCode 的 `[1, 2, 3, null, null, 4, 5]` 格式，反序列化就是 12.3 節的 `build_tree`。BFS 版本完全不用遞迴，在 10⁴ 層的鏈上也不會超過遞迴上限；前序版本程式更短、更容易證明。面試時兩種都可以，但要能說出遞迴深度的取捨。

```text
樹 [1, 2, 3, null, null, 4, 5]

      1
     / \
    2   3
       / \
      4   5

serialize（前序，空節點寫 #）：1,2,#,#,3,4,#,#,5,#,#
                                 └2的子樹┘ └──── 3 的子樹 ────┘

deserialize：每次 build() 讀一個 token
token  動作                         接下來要填的位置
1      建立 1，遞迴建左子樹          1.left
2      建立 2，遞迴建左子樹          2.left
#      2.left = None                 2.right
#      2.right = None，2 完成        1.right
3      建立 3，遞迴建左子樹          3.left
4      建立 4                        4.left
#      4.left = None                 4.right
#      4.right = None，4 完成        3.right
5      建立 5                        5.left
#      5.left = None                 5.right
#      5.right = None，5、3、1 完成   （token 剛好用完）
```

5 個值、6 個 `#`，符合「k 個節點、k + 1 個空標記」。讀到第二個 `#` 時，2 的子樹結束，下一個 token 3 自然成為 1 的右子節點；整個過程不需要知道任何子樹的大小。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def to_list(root):
    out, queue = [], deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out


def random_tree(n):
    nodes = [TreeNode(random.randint(-1000, 1000)) for _ in range(n)]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0] if nodes else None


class Codec:
    """前序 + 空節點標記。"""

    def serialize(self, root) -> str:
        out = []

        def dfs(node):
            if node is None:
                out.append("#")
                return
            out.append(str(node.val))
            dfs(node.left)
            dfs(node.right)

        dfs(root)
        return ",".join(out)

    def deserialize(self, data: str):
        tokens = iter(data.split(","))

        def build():
            tok = next(tokens)
            if tok == "#":
                return None
            node = TreeNode(int(tok))
            node.left = build()               # 讀取順序 = 前序 = 建構順序
            node.right = build()
            return node

        return build()


class CodecBFS:
    """層序 + 空節點標記，完全不用遞迴。"""

    def serialize(self, root) -> str:
        out, queue = [], deque([root])
        while queue:
            node = queue.popleft()
            if node is None:
                out.append("#")
                continue
            out.append(str(node.val))
            queue.append(node.left)
            queue.append(node.right)
        return ",".join(out)

    def deserialize(self, data: str):
        tokens = data.split(",")
        if tokens[0] == "#":
            return None
        root = TreeNode(int(tokens[0]))
        queue, i = deque([root]), 1
        while queue:                          # 每個真實節點恰好對應後面兩個 token
            node = queue.popleft()
            if tokens[i] != "#":
                node.left = TreeNode(int(tokens[i]))
                queue.append(node.left)
            if tokens[i + 1] != "#":
                node.right = TreeNode(int(tokens[i + 1]))
                queue.append(node.right)
            i += 2
        return root


c, b = Codec(), CodecBFS()
t = build_tree([1, 2, 3, None, None, 4, 5])
assert c.serialize(t) == "1,2,#,#,3,4,#,#,5,#,#"
assert b.serialize(t) == "1,2,3,#,#,4,5,#,#,#,#"
for codec in (c, b):
    assert to_list(codec.deserialize(codec.serialize(t))) == [1, 2, 3, None, None, 4, 5]
    assert codec.deserialize(codec.serialize(None)) is None
    neg = build_tree([-1000, 1000, None, -7])
    assert to_list(codec.deserialize(codec.serialize(neg))) == [-1000, 1000, None, -7]
    assert codec.serialize(build_tree([1, 2])) != codec.serialize(build_tree([1, None, 2]))
for _ in range(300):
    t = random_tree(random.randint(0, 20))
    assert to_list(c.deserialize(c.serialize(t))) == to_list(t) == to_list(b.deserialize(b.serialize(t)))
chain = cur = TreeNode(0)
for v in range(1, 10_000):                    # 一萬層的鏈：用不需要遞迴的 BFS 版本
    cur.right = TreeNode(v)
    cur = cur.right
assert len(to_list(b.deserialize(b.serialize(chain)))) == 2 * 10_000 - 1
print("all tests passed")
```

### 複雜度與邊界

兩個方法都是 O(n) 時間：每個節點與每個空標記各處理一次，共 2n + 1 個 token。空間 O(n) 存字串與 token；前序版本另有 O(h) 的遞迴深度，n = 10⁴ 的鏈會超過 Python 預設上限，所以附上 BFS 版本（或在前序版本中改用顯式 stack）。邊界情況：空樹序列化成 `"#"`，反序列化要先判斷；負數與多位數靠分隔符號 `,` 切開，不能逐字元解析；BFS 版本不能省略尾端的 `#`，否則 `tokens[i + 1]` 會越界（LeetCode 的格式省略了，對應的 `build_tree` 因此要檢查 `i < len(values)`）。注意 `Codec` 沒有用任何實例變數保存狀態，符合題目要求。

### Follow-up

> [!question]- F1. 如果是 BST（449. Serialize and Deserialize BST），能不能更省空間？
> 可以完全不寫空標記。BST 的形狀由前序的值唯一決定，因為中序就是排序後的序列（核心題 4 F3）。反序列化時用帶上下界的遞迴：`build(lo, hi)` 只在下一個值落在 (lo, hi) 內時建立節點，左子樹的範圍是 (lo, val)，右子樹是 (val, hi)。字串長度從 2n + 1 個 token 降到 n 個，時間 O(n)。若要更緊湊，可以把每個值編成固定長度的二進位，連分隔符號都省掉。

> [!question]- F2. 如果要求字串盡可能短，有什麼更緊湊的編碼？
> 把結構與值分開編碼。結構用位元表示：前序中每個位置寫 1（有節點）或 0（空），共 2n + 1 個位元，這已經接近資訊理論下限（n 個節點的二元樹形狀有卡特蘭數 C(n) ≈ 4ⁿ 種，至少需要約 2n 位元）。值的範圍是 -1000 到 1000，每個用 11 位元即可。整體約 13n 位元，遠小於文字格式。面試中說出「結構約 2n 位元是下限」，代表你知道為什麼空標記是必要的成本。

> [!question]- F3. 如果是 N-ary tree（428. Serialize and Deserialize N-ary Tree）呢？
> 空標記的方法要改，因為子節點數不固定。最簡單的格式是前序中每個節點寫「值, 子節點數」，反序列化時讀到子節點數 c，就遞迴建 c 個子樹。另一種是每個節點寫值，子節點都結束後寫一個結束標記（例如 `)`），讀到結束標記就返回上一層。兩種都是 O(n)。也可以用「左孩子右兄弟」把 N-ary tree 轉成二元樹，直接套本題。

> [!question]- F4. 如果節點的值是任意字串，可能包含逗號或 `#` 呢？
> 分隔符號就不能用了。改用長度前綴（length-prefix）編碼：每個值寫成 `長度:內容`，空節點寫一個特殊的長度（例如 `-1:`）。反序列化時先讀到冒號取得長度，再往後取剛好那麼多個字元，內容裡有什麼字元都不會被誤判。這和 271. Encode and Decode Strings 是同一個技巧。時間仍是 O(總字元數)，而且不需要任何跳脫（escape）規則。

> [!question]- F5. 如果樹很大，要把序列化結果串流寫進檔案，而且反序列化時也只能一段一段讀呢？
> 前序版本天生適合串流：序列化時邊走訪邊寫出 token，不需要先把整個字串存在記憶體；反序列化時 `next(tokens)` 改成從檔案讀下一個 token 的 generator 即可，記憶體只需要 O(h) 的遞迴或 stack。BFS 版本反序列化時 queue 要保存一整層的節點，記憶體是 O(w)，寬樹時較大。所以大樹的串流場景下，帶空標記的前序加上顯式 stack 是最穩健的選擇。

### 心得

關鍵突破是「把空節點寫進去，讓每個子樹在字串中成為自我界定的一段」，於是一種走訪就足以唯一決定一棵樹，不需要值互不相同。它和核心題 4 共用同一個觀念：**讀取順序必須等於建構順序**，前序剛好是遞迴建樹的順序。面試時先說明為什麼只存值不夠（給 `[1, 2]` 與 `[1, null, 2]` 的反例），再提出空標記，用「k 個節點產生 k + 1 個空標記」說明格式的正確性，最後主動提遞迴深度的風險與 BFS 版本。這題的程式不難，評分重點是你能不能說清楚格式為什麼沒有歧義。

## 難題 3｜968. Binary Tree Cameras｜Hard

### 題目

在一棵二元樹的節點上安裝攝影機，每台攝影機能監控它所在的節點、它的父節點，以及它的直接子節點。請回傳讓**所有節點**都被監控所需的最少攝影機數量。限制：節點數在 `1` 到 `1000` 之間，所有節點值都是 0（值沒有意義）。

- 範例 1：`root = [0, 0, null, 0, 0]`，回傳 `1`；攝影機放在根的左子節點，能同時看到根和它的兩個子節點。
- 範例 2：`root = [0, 0, null, 0, null, 0, null, null, 0]`，這是一條 5 個節點的鏈，回傳 `2`。
- 範例 3（邊界）：`root = [0]`，回傳 `1`；唯一的節點必須自己裝。
- 範例 4：`root = [0, 0, 0, 0, 0, 0, 0]`（7 個節點的完全二元樹），回傳 `2`，放在第二層的兩個節點。

### 提示

> [!tip]- 提示 1
> 先想葉子。葉子要被監控，攝影機要嘛裝在葉子上，要嘛裝在它的父節點上。哪一個永遠不會比較差？

> [!tip]- 提示 2
> 裝在父節點上能監控的範圍包含了裝在葉子上的範圍。所以由下往上處理，「能晚一點裝就晚一點裝」。每個節點只需要回報三種狀態之一：沒被監控、裝了攝影機、被監控但沒裝。

> [!tip]- 提示 3
> 後序：任一個子節點「沒被監控」，自己就必須裝攝影機；否則任一個子節點「有攝影機」，自己已被監控；否則自己沒被監控，交給父節點處理。空節點視為「被監控但沒裝」。最後若根沒被監控，再加一台。

### 詳解

**為什麼直覺做法不夠**。暴力法是枚舉所有 2ⁿ 種安裝方式，檢查是否全部被監控，n = 1000 時完全不可行。由上往下的貪婪也不行：例如「從根開始，每隔一層裝一台」，在範例 1 會在根裝一台，剩下的兩個孫節點又要各裝一台，共 3 台，而最佳只要 1 台。問題在於根附近的決策缺乏資訊，根有幾個子孫、子孫的形狀如何，都會影響根要不要裝；反過來，葉子附近的決策是最確定的。

**突破點：從葉子往上貪婪**。看任何一片葉子 ℓ：它必須被自己或父節點 p 監控。把攝影機裝在 p，能監控 p、p 的父節點、p 的所有子節點（包括 ℓ）；裝在 ℓ 只能監控 ℓ 和 p。前者監控的集合**包含**後者，所以任何最佳解若在 ℓ 裝了攝影機，都可以把它移到 p 而不增加數量、也不會讓任何節點失去監控。這個交換論證告訴我們：葉子永遠不裝，讓父節點裝。推廣到一般節點：由下往上處理，一個節點只有在「它有子節點還沒被監控」時才被迫裝攝影機；否則就不裝，把決定往上延後，因為越上面的位置能覆蓋的未監控節點越多。

**三種狀態**。後序回傳每個節點的狀態：`NOT_COVERED`（沒被監控，需要父節點裝）、`HAS_CAMERA`（自己裝了）、`COVERED`（被子節點監控，自己沒裝）。組合規則依優先順序：任一子節點是 `NOT_COVERED`，自己必須裝，回傳 `HAS_CAMERA`；否則任一子節點是 `HAS_CAMERA`，自己已被監控，回傳 `COVERED`；否則兩個子節點都是 `COVERED` 但沒有攝影機照到自己，回傳 `NOT_COVERED`。空節點回傳 `COVERED`：它不需要被監控，也不能裝攝影機，這樣葉子會自然得到 `NOT_COVERED`，把責任交給父節點。最後根沒有父節點，若根是 `NOT_COVERED` 就自己裝一台。

**另一個角度：樹 DP**。若不想依賴交換論證，也可以對每個節點算三個值：`a` = 自己裝攝影機時子樹的最少數量，`b` = 自己沒裝但被某個子節點監控，`c` = 自己沒裝、也沒被子節點監控（必須由父節點負責），其餘節點都被監控。轉移：`a = 1 + min(左三態) + min(右三態)`；`b = min(左a + min(右a, 右b), 右a + min(左a, 左b))`；`c = 左b + 右b`。答案是根的 `min(a, b)`。DP 不需要證明貪婪，而且能直接推廣到每個位置成本不同的情況（F2），代價是程式較長。

```text
範例 2：5 個節點的鏈（每個都是左子節點）

  A          後序處理順序：E → D → C → B → A
  |
  B          節點  子節點狀態              本節點狀態      攝影機
  |          E     (空, 空) = 已監控        NOT_COVERED     0
  C          D     E = NOT_COVERED          HAS_CAMERA      1   ← 被迫裝
  |          C     D = HAS_CAMERA           COVERED         1
  D          B     C = COVERED              NOT_COVERED     1
  |          A     B = NOT_COVERED          HAS_CAMERA      2   ← 被迫裝
  E          根 A 的狀態不是 NOT_COVERED，不必再加
             答案 2：D 監控 C、D、E；A 監控 A、B
```

葉子 E 不裝，回報「沒被監控」；D 因此被迫裝，順便照到 C；C 被照到但沒裝，回報 `COVERED`；B 的子節點只是 `COVERED`，沒人照到 B，於是 B 回報 `NOT_COVERED`，把責任交給 A。注意 B 不急著裝，因為裝在 A 一樣能照到 B，而且若 A 還有父節點，裝在 A 還能照到更多。

### 解法

```python
import random
from collections import deque
from itertools import combinations


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(0) for _ in range(n)]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0]


NOT_COVERED, HAS_CAMERA, COVERED = 0, 1, 2


def min_camera_cover(root) -> int:
    cameras = 0

    def dfs(node) -> int:
        nonlocal cameras
        if node is None:
            return COVERED                    # 空節點不需要監控，也不會逼父節點裝
        left, right = dfs(node.left), dfs(node.right)
        if left == NOT_COVERED or right == NOT_COVERED:
            cameras += 1                      # 有子節點沒被照到：被迫裝
            return HAS_CAMERA
        if left == HAS_CAMERA or right == HAS_CAMERA:
            return COVERED
        return NOT_COVERED                    # 延後決定，交給父節點

    if dfs(root) == NOT_COVERED:              # 根沒有父節點，只能自己裝
        cameras += 1
    return cameras


def min_camera_cover_dp(root) -> int:
    INF = float("inf")

    def dfs(node):
        # a：node 裝攝影機；b：node 沒裝、被子節點監控；c：node 沒裝、也沒被子節點監控
        if node is None:
            return INF, 0, 0
        la, lb, lc = dfs(node.left)
        ra, rb, rc = dfs(node.right)
        a = 1 + min(la, lb, lc) + min(ra, rb, rc)
        b = min(la + min(ra, rb), ra + min(la, lb))
        c = lb + rb
        return a, b, c

    a, b, _ = dfs(root)
    return min(a, b)


def brute(root):
    nodes, parent, stack = [], {root: None}, [root]
    while stack:
        node = stack.pop()
        nodes.append(node)
        for ch in (node.left, node.right):
            if ch:
                parent[ch] = node
                stack.append(ch)
    for k in range(1, len(nodes) + 1):
        for chosen in combinations(nodes, k):
            seen = set()
            for v in chosen:
                seen.update(x for x in (v, parent[v], v.left, v.right) if x)
            if len(seen) == len(nodes):
                return k


assert min_camera_cover(build_tree([0, 0, None, 0, 0])) == 1
assert min_camera_cover(build_tree([0, 0, None, 0, None, 0, None, None, 0])) == 2
assert min_camera_cover(build_tree([0])) == 1
assert min_camera_cover(build_tree([0, 0, 0])) == 1
assert min_camera_cover(build_tree([0, 0, 0, 0, 0, 0, 0])) == 2
for _ in range(300):
    t = random_tree(random.randint(1, 10))
    assert min_camera_cover(t) == min_camera_cover_dp(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

貪婪與 DP 都是 O(n) 時間、O(h) 的遞迴空間。邊界情況：單一節點時根是 `NOT_COVERED`，最後補一台；空節點必須回傳 `COVERED`，若回傳 `NOT_COVERED` 會讓每片葉子都被迫裝攝影機，若回傳 `HAS_CAMERA` 會讓葉子誤以為被照到；判斷順序不能對調，必須先檢查「有子節點沒被監控」，因為那是硬性要求，若先檢查「有子節點裝了攝影機」，會在另一個子節點還沒被照到時就回報 `COVERED`；最後別忘了檢查根。DP 版中空節點的 `a = INF` 代表「不能在空位置裝攝影機」。

### Follow-up

> [!question]- F1. 如果每台攝影機能監控距離 k 以內的所有節點呢？
> 貪婪可以推廣：依深度由深到淺處理節點，遇到還沒被監控的節點 v 時，把攝影機裝在 v 往上第 k 個祖先（不足 k 層就裝在根），然後用 BFS 標記這台攝影機距離 k 以內的所有節點。交換論證相同：能監控到最深的未監控節點 v 的位置中，這個祖先覆蓋的「還沒處理的部分」最多。每台攝影機的 BFS 最多 O(n)，總時間最差 O(n²)；用樹 DP 回傳「最近的攝影機距離」與「最遠的未監控節點距離」兩個值，可以做到 O(n)。

> [!question]- F2. 如果每個節點安裝攝影機的成本不同，要最小化總成本呢？
> 貪婪失效，因為把攝影機從葉子移到父節點不再保證不變貴。改用詳解中的三態 DP，只要把 `a` 的 `1` 換成 `cost[node]`：`a = cost + min(左三態) + min(右三態)`，`b`、`c` 的轉移不變，答案是根的 `min(a, b)`。O(n) 時間。這就是樹上的 minimum weighted dominating set，第 24 章的樹 DP 會系統性地處理這類「每個節點幾個狀態」的問題。

> [!question]- F3. 如果要輸出攝影機裝在哪些節點呢？
> 貪婪版只要在 `cameras += 1` 的地方把 node 加進結果 list，根被補裝時也加入根。O(n)，不需要第二遍。DP 版則需要回溯：記錄每個狀態是由哪個子狀態組合轉移而來，從根的最佳狀態往下還原，這也是 DP 解法比貪婪麻煩的地方。

> [!question]- F4. 如果不是樹，而是一般的圖呢？
> 這就是 minimum dominating set（最小支配集）問題，在一般圖上是 NP-hard，沒有已知的多項式解；只能用指數時間的精確演算法、整數規劃，或保證 O(log n) 倍近似比的貪婪。樹之所以能 O(n)，是因為移除一個節點後子樹彼此獨立，子問題之間只透過父子邊互動，所以每個節點只需要幾個狀態就能概括子樹對外的影響。面試時指出這點，代表你知道「樹」這個條件在演算法裡扮演什麼角色。

> [!question]- F5. 這題和 337. House Robber III 有什麼關係？
> 兩者都是「每個節點做一個二元選擇，相鄰節點互相限制」的樹 DP。337 是 maximum weight independent set：選了 v 就不能選它的子節點，每個節點兩個狀態（選或不選）。968 是 dominating set：每個節點要被自己或鄰居覆蓋，需要三個狀態，因為「沒裝」還要分成「已被子節點照到」與「要靠父節點」。兩題都是 O(n)。337 在第 24 章核心題 1 詳細討論；把兩題的狀態設計放在一起比較，是準備樹 DP 最有效率的方法。

### 心得

關鍵突破是「葉子永遠不裝，讓父節點裝」這個交換論證，它把一個看似需要搜尋的問題變成由下往上的貪婪，每個節點只回報三種狀態之一。它和本章其他題的關係是：結構上仍是後序回傳摘要（和 543、236 相同），只是摘要從數值變成了狀態，而組合規則有優先順序。面試時建議先講葉子的交換論證，再定義三種狀態與空節點的處理，最後補上「根要特別檢查」；如果面試官質疑貪婪的正確性，就拿出三態 DP 作為不需證明的替代方案，並說明它也能處理成本不同的情況。

## 難題 4｜987. Vertical Order Traversal of a Binary Tree｜Hard

### 題目

替二元樹的每個節點定座標：根在 `(row, col) = (0, 0)`；位於 `(row, col)` 的節點，左子節點在 `(row + 1, col − 1)`，右子節點在 `(row + 1, col + 1)`。垂直走訪是由最左邊的行到最右邊的行，每一行輸出一個 list；同一行內依 row 由上到下排序，若有多個節點的 row 與 col 都相同，再依值由小到大排序。回傳所有行的 list。限制：節點數在 `1` 到 `1000` 之間，節點值在 `0` 到 `1000` 之間。

- 範例 1：`root = [3, 9, 20, null, null, 15, 7]`，回傳 `[[9], [3, 15], [20], [7]]`；15 在 (2, 0)，和根同一行。
- 範例 2：`root = [1, 2, 3, 4, 5, 6, 7]`，回傳 `[[4], [2], [1, 5, 6], [3], [7]]`；5 和 6 都在 (2, 0)，依值排序。
- 範例 3：`root = [1, 2, 3, 4, 6, 5, 7]`，回傳 `[[4], [2], [1, 5, 6], [3], [7]]`；這次 6 在 5 的左邊，但同一格要依值排序，所以仍是 5 在前。
- 範例 4（邊界）：`root = [1]`，回傳 `[[1]]`。

### 提示

> [!tip]- 提示 1
> 座標是由上往下決定的：只要知道父節點的 (row, col)，子節點的座標就確定了。先用一次走訪把每個節點的座標記下來。

> [!tip]- 提示 2
> 輸出順序完全由三個鍵決定：col、row、val。把每個節點記成 tuple `(col, row, val)`，排序之後就是答案的順序。

> [!tip]- 提示 3
> 排序後依 col 分組即可。也可以先依 col 分桶（col 的範圍是連續的，從最小行到最大行），每桶內再依 `(row, val)` 排序。範例 3 說明了為什麼不能只靠 BFS 的順序。

### 詳解

**為什麼直覺做法不夠**。很多人會先想到 BFS：BFS 依 row 由上到下拜訪，同一層由左到右，把節點依 col 放進桶子裡，似乎就得到了「依 row 排序」的結果。這對 314 題（同一格依左到右的順序）是正確的，但本題要求同一格**依值排序**。範例 3 中 6 和 5 都在 (2, 0)，BFS 會先遇到 6（它是 2 的右子節點，在 3 的左子節點 5 的左邊），輸出 `[1, 6, 5]`，是錯的。所以同一格內的順序與走訪順序無關，必須額外排序。

**突破點：把輸出規則寫成排序鍵**。題目的三層規則「先 col、再 row、再 val」恰好是 tuple 的字典序。用任一種走訪（DFS 或 BFS 都可以）由上往下傳座標，把每個節點記為 `(col, row, val)`，排序一次，再把相同 col 的連續元素分成一組。這是本章「由上往下傳參數」的應用：座標只依賴祖先，所以用參數傳遞最自然，而輸出順序是全域的，所以收集完再一次排序。

**正確性與複雜度的下限**。排序之後，同一 col 的元素是連續的，而且組內依 (row, val) 排序，正好是題目定義；col 由小到大，所以行由左到右。總時間 O(n log n)，瓶頸在排序。能不能更快？當一整列的節點擠在同一格時（例如很多節點都落在 (k, 0)），題目要求依值排序，這本身就是一般排序問題，比較式排序的下限是 O(n log n)。但若值域很小（本題 0 到 1000），可以用 counting sort 或 radix sort 做到 O(n + 值域)，見 F5。

```text
root = [1, 2, 3, 4, 6, 5, 7]

               1 (0, 0)
             /          \
        2 (1, -1)      3 (1, 1)
        /      \        /      \
  4 (2, -2)  6 (2, 0) 5 (2, 0)  7 (2, 2)

DFS 收集到的 (col, row, val)（前序順序）：
(0, 0, 1)  (-1, 1, 2)  (-2, 2, 4)  (0, 2, 6)  (1, 1, 3)  (0, 2, 5)  (2, 2, 7)

排序後：
(-2, 2, 4)  (-1, 1, 2)  (0, 0, 1)  (0, 2, 5)  (0, 2, 6)  (1, 1, 3)  (2, 2, 7)

依 col 分組：
col -2: [4]   col -1: [2]   col 0: [1, 5, 6]   col 1: [3]   col 2: [7]

對照 BFS 的順序：第 2 層由左到右是 4, 6, 5, 7 → col 0 會得到 [1, 6, 5]，錯誤
```

6 和 5 落在同一格 (2, 0)，收集時 6 先出現，但 tuple 的第三個鍵讓 5 排在前面。這正是本題與 314 題的差別：314 要的是走訪順序，本題要的是值的順序，所以本題必須排序，314 不需要。

### 解法

```python
import random
from collections import defaultdict, deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(random.randint(0, 5)) for _ in range(n)]   # 小值域，製造大量平手
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0]


def vertical_traversal(root):
    cells = []                                    # (col, row, val)

    def dfs(node, row, col):
        if node is None:
            return
        cells.append((col, row, node.val))
        dfs(node.left, row + 1, col - 1)
        dfs(node.right, row + 1, col + 1)

    dfs(root, 0, 0)
    cells.sort()
    res, last_col = [], None
    for col, _, val in cells:
        if col != last_col:                       # 進入新的一行
            res.append([])
            last_col = col
        res[-1].append(val)
    return res


def vertical_traversal_buckets(root):
    """BFS 帶座標分桶，每桶內依 (row, val) 排序；col 範圍連續，不必排序行號。"""
    buckets, queue = defaultdict(list), deque([(root, 0, 0)])
    lo = hi = 0
    while queue:
        node, row, col = queue.popleft()
        buckets[col].append((row, node.val))
        lo, hi = min(lo, col), max(hi, col)
        if node.left:
            queue.append((node.left, row + 1, col - 1))
        if node.right:
            queue.append((node.right, row + 1, col + 1))
    return [[v for _, v in sorted(buckets[c])] for c in range(lo, hi + 1)]


assert vertical_traversal(build_tree([3, 9, 20, None, None, 15, 7])) == [[9], [3, 15], [20], [7]]
assert vertical_traversal(build_tree([1, 2, 3, 4, 5, 6, 7])) == [[4], [2], [1, 5, 6], [3], [7]]
assert vertical_traversal(build_tree([1, 2, 3, 4, 6, 5, 7])) == [[4], [2], [1, 5, 6], [3], [7]]
assert vertical_traversal(build_tree([1])) == [[1]]
assert vertical_traversal(build_tree([1, 2, None, 3, None, 4])) == [[4], [3], [2], [1]]   # 往左的鏈
for _ in range(300):
    t = random_tree(random.randint(1, 20))
    assert vertical_traversal(t) == vertical_traversal_buckets(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n)：走訪 O(n)，排序 n 個 tuple O(n log n)，分組 O(n)。分桶版本的時間也是 O(n log n)，但每桶分別排序，在行數多、每行節點少時常數較小。空間 O(n) 存座標，加上 O(h) 的遞迴深度（n ≤ 1000 的鏈剛好接近 Python 的預設上限，BFS 版本沒有這個問題）。邊界情況：col 會是負數，若用陣列分桶要加上位移量 `-lo`；同一格多個節點要依值排序，相同的值都要保留（不能用 set）；單一節點時回傳 `[[val]]`。排序時 tuple 的順序必須是 `(col, row, val)`，寫成 `(row, col, val)` 會先依列排序，結果完全錯誤。

### Follow-up

> [!question]- F1. 如果同一格內改成依「由左到右」的順序，而不是依值（314. Binary Tree Vertical Order Traversal）呢？
> 這時 BFS 的走訪順序就是答案的順序：BFS 依 row 遞增拜訪，同一 row 內由左到右，而「同一格的節點」在 BFS 中出現的先後也就是由左到右的順序。所以只要 BFS 時把值 append 到 `buckets[col]`，並記下最小與最大的 col，最後依序輸出，完全不需要排序，O(n) 時間。注意不能用 DFS，因為 DFS 會先拜訪左子樹深處的節點，打亂 row 的順序。

> [!question]- F2. 如果只要每一行最上面的節點（top view）或最下面的節點（bottom view）呢？
> top view 是每個 col 第一個被 BFS 拜訪的節點，用 dict 記錄「這個 col 還沒有值時才寫入」；bottom view 是每個 col 最後一個被 BFS 拜訪的節點，每次都覆寫即可。兩者都是 O(n)，不需要排序，因為 BFS 已經依 row 排好了。若同一格有多個節點（例如 bottom view 中兩個節點都在最深的同一格），要先問面試官取哪一個，通常是 BFS 中較後面（較右邊）的那個。

> [!question]- F3. 如果要依「對角線」輸出（右子節點沿同一條對角線，左子節點進入下一條）呢？
> 座標換成一個值：根在對角線 0，右子節點的對角線不變，左子節點加 1。用 DFS（前序，先左後右或依題目要求）帶著對角線編號，把值 append 到 `diag[d]`，最後依 d 由小到大輸出。對角線編號從 0 開始連續，可以直接用 list 當桶。O(n) 時間。這和本題的結構完全相同：先定義座標、由上往下傳、再分組，只是座標的定義不同。

> [!question]- F4. 如果要每一行的總和（vertical sum）呢？
> 不需要任何排序：DFS 帶 col，`sums[col] += node.val`，同時記下 col 的最小與最大值，最後依序輸出 `sums[lo..hi]`。O(n) 時間、O(行數) 空間。若要 O(1) 額外空間（不計輸出），可以先用一次 DFS 找出 lo 與 hi，配置長度為 hi − lo + 1 的陣列，再用第二次 DFS 累加，避免用 dict。

> [!question]- F5. 如果 n 高達 10⁶，而且值域很小，能不能比 O(n log n) 更快？
> 可以用 radix sort（基數排序）：三個鍵 col、row、val 的範圍分別是 [−n, n]、[0, n)、[0, 1000]，都是整數且範圍有限。依最不重要的鍵開始做穩定的 counting sort：先依 val、再依 row、最後依 col，每一輪 O(n + 範圍)，總共 O(n)。實作上更簡單的做法是：BFS 依 row 遞增產生節點，把每個節點放進 `buckets[col]`，此時每桶已經依 row 排好，只需要對每桶中「row 相同的連續段」依值排序；若值域很小，就用 counting sort 處理這些段。

### 心得

關鍵突破是把三層輸出規則直接寫成排序鍵 `(col, row, val)`，讓「怎麼走訪」與「怎麼輸出」脫鉤：走訪只負責由上往下傳座標，順序全部交給排序決定。它是本章「參數由上往下傳」的典型題，與核心題 2 的 F2（top view）、314 題是一組變形，差別只在同一格的平手規則。面試時要主動指出 BFS 順序為什麼不夠（給出範例 3），說明這就是需要排序的理由，再提出 O(n log n) 的解法，並能回答 314 為什麼可以 O(n)。

## 難題 5｜2458. Height of Binary Tree After Subtree Removal Queries｜Hard

### 題目

給一棵有 n 個節點的二元樹，節點值是 `1` 到 `n` 的排列（互不相同），以及長度為 m 的查詢陣列 `queries`。對每個查詢 `queries[i]`，把以該值為根的整棵子樹從樹上移除，然後回答此時樹的高度；查詢之間**互相獨立**，每次回答完樹就恢復原狀。樹的高度是從根到最深節點的**邊數**。保證查詢的節點不是根。限制：`2 <= n <= 10⁵`，`1 <= m <= min(n, 10⁴)`。

- 範例 1：`root = [1, 3, 4, 2, null, 6, 5, null, null, null, null, null, 7]`、`queries = [4]`，回傳 `[2]`；原本最深的路徑是 1 → 4 → 5 → 7，移除 4 之後剩下 1 → 3 → 2。
- 範例 2：`root = [5, 8, 9, 2, 1, 3, 7, 4, 6]`、`queries = [3, 2, 4, 8]`，回傳 `[3, 2, 3, 2]`。
- 範例 3（邊界）：`root = [1, 2]`、`queries = [2]`，回傳 `[0]`；只剩根。
- 範例 4（邊界）：移除一片不在最深路徑上的葉子，高度不變；移除最深路徑上的節點時，高度取決於樹的其他部分。

### 提示

> [!tip]- 提示 1
> 每次查詢都重新計算高度是 O(n)，總共 O(n · m) = 10⁹，太慢。需要預先算好所有節點的答案，每次查詢 O(1)。

> [!tip]- 提示 2
> 移除 v 的子樹之後，剩下的是「v 的子樹以外」的所有節點，答案是它們之中最大的深度。這是關於子樹**外面**的資訊，後序回傳值給不了，要另外由上往下傳。

> [!tip]- 提示 3
> 令 `rest(v)` = 移除 v 的子樹後的高度。對節點 u 的左子節點 L（右子節點是 R）：`rest(L) = max(rest(u), depth(u) + 1 + height(R))`，其中空子樹的高度是 -1。先用後序算出所有 height，再用前序由上往下算出所有 rest。

### 詳解

**為什麼直覺做法不夠**。最直接的是每個查詢都做一次「跳過該子樹的 DFS」，O(n)，共 m 次，最差 10⁵ × 10⁴ = 10⁹，超時。另一個直覺是「只有移除最深路徑上的節點，高度才會改變」，這是對的，但不夠：移除最深路徑上不同的節點，剩下的高度各不相同，仍然要對每個節點算出答案。所以真正的問題是：**能不能 O(n) 預先算出所有 n 個節點的答案**？

**突破點：子樹外的資訊由上往下傳**。移除 v 的子樹後，剩下的節點分成兩類：v 的父節點 u 的子樹以外的節點，以及 u 自己與 u 的另一棵子樹（v 的兄弟 s）。第一類的最大深度正是 `rest(u)`，也就是「移除 u 的子樹後的高度」；第二類中 u 的深度是 `depth(u)`，s 子樹裡最深的節點深度是 `depth(u) + 1 + height(s)`。所以 `rest(v) = max(rest(u), depth(u) + 1 + height(s))`。若 v 沒有兄弟，令 `height(None) = -1`，式子變成 `max(rest(u), depth(u))`，正好代表「u 自己還留著」。根的子節點沒有更上面的部分，令 `rest(root) = 0` 即可（根自己的深度是 0，而 0 也已經被 `depth(root) + 1 + height(s)` 涵蓋，不會錯）。

**兩遍走訪**。式子需要兩種資訊：`height(s)` 是子樹內的資訊，必須由下往上；`rest(u)` 是子樹外的資訊，必須由上往下。所以先做一次後序算出所有節點的 height，再做一次前序，從根開始依式子算出每個子節點的 rest。兩遍都是 O(n)，之後每個查詢查表 O(1)。這種「先算子樹內、再傳子樹外」的兩遍走訪，叫做 rerooting（換根）技巧，第 24 章難題 1（834）用的是同一個想法。因為 n 可到 10⁵ 而且可能是鏈，下面的解法用 12.5 節的「BFS 順序」取代遞迴：正序處理就是由上往下，反序處理就是由下往上。

**另一個等價觀點：Euler tour**。用 DFS 的進入時間把節點排成一列，每棵子樹在這一列中恰好是一段連續區間 `[tin(v), tout(v)]`。移除 v 的子樹等於移除這段區間，答案就是「區間左邊的最大深度」與「區間右邊的最大深度」的較大者，用前綴最大值與後綴最大值陣列，每個查詢 O(1)。這個觀點把樹的問題轉成陣列的區間問題，F1、F4 的變形用它處理特別方便。

```text
範例 2：root = [5, 8, 9, 2, 1, 3, 7, 4, 6]

              5            depth：5:0  8:1 9:1  2:2 1:2 3:2 7:2  4:3 6:3
            /   \          height（空樹 = -1）：
           8     9           4:0 6:0 2:1 1:0 8:2 3:0 7:0 9:1 5:3
          / \   / \
         2   1 3   7       由上往下計算 rest（u 是父節點，s 是兄弟）：
        / \                  rest(5) = 0
       4   6                 rest(8) = max(rest(5)=0, 0 + 1 + height(9)=1) = 2
                             rest(9) = max(0, 0 + 1 + height(8)=2)        = 3
                             rest(2) = max(rest(8)=2, 1 + 1 + height(1)=0) = 2
                             rest(1) = max(2, 1 + 1 + height(2)=1)        = 3
                             rest(3) = max(rest(9)=3, 1 + 1 + height(7)=0) = 3
                             rest(7) = max(3, 1 + 1 + height(3)=0)        = 3
                             rest(4) = max(rest(2)=2, 2 + 1 + height(6)=0) = 3
                             rest(6) = max(2, 2 + 1 + height(4)=0)        = 3

queries = [3, 2, 4, 8] → [rest(3), rest(2), rest(4), rest(8)] = [3, 2, 3, 2]
```

移除 2 時，最深的兩片葉子 4、6 都消失了，剩下的最深節點是深度 2 的 1、3、7，所以答案 2；算式中 `rest(8) = 2` 代表「8 的子樹以外」最深到 2（來自 9 的子樹），兄弟 1 提供 1 + 1 + 0 = 2，兩者取大是 2。移除 4 時，兄弟 6 還在，深度 3，所以答案不變。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        if values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


def random_tree(n):
    nodes = [TreeNode(v) for v in random.sample(range(1, n + 1), n)]
    for i in range(1, n):
        while True:
            parent = random.choice(nodes[:i])
            side = random.choice(("left", "right"))
            if getattr(parent, side) is None:
                setattr(parent, side, nodes[i])
                break
    return nodes[0]


def tree_queries(root, queries):
    # 第一遍：BFS 順序（父節點一定在子節點之前）與每個節點的深度
    order, depth = [root], {root.val: 0}
    for node in order:                                  # 邊走訪邊 append
        for child in (node.left, node.right):
            if child:
                depth[child.val] = depth[node.val] + 1
                order.append(child)
    # 第二遍：反序 = 由下往上，算子樹高度（邊數，空樹為 -1）
    height = {}
    for node in reversed(order):
        hl = height[node.left.val] if node.left else -1
        hr = height[node.right.val] if node.right else -1
        height[node.val] = 1 + max(hl, hr)
    # 第三遍：正序 = 由上往下，rest[v] = 移除 v 的子樹後的高度
    rest = {root.val: 0}
    for node in order:
        d = depth[node.val]
        hl = height[node.left.val] if node.left else -1
        hr = height[node.right.val] if node.right else -1
        if node.left:
            rest[node.left.val] = max(rest[node.val], d + 1 + hr)
        if node.right:
            rest[node.right.val] = max(rest[node.val], d + 1 + hl)
    return [rest[q] for q in queries]


def tree_queries_euler(root, queries):
    """Euler tour：子樹是連續區間，答案 = 區間外的最大深度。"""
    tin, tout, depths = {}, {}, []
    stack = [(root, 0, False)]
    while stack:
        node, d, done = stack.pop()
        if done:
            tout[node.val] = len(depths) - 1            # 子樹最後一個節點的位置
            continue
        tin[node.val] = len(depths)
        depths.append(d)
        stack.append((node, d, True))
        for child in (node.right, node.left):
            if child:
                stack.append((child, d + 1, False))
    n = len(depths)
    prefix = [0] * (n + 1)                              # prefix[i] = max(depths[:i])
    for i in range(n):
        prefix[i + 1] = max(prefix[i], depths[i])
    suffix = [0] * (n + 1)                              # suffix[i] = max(depths[i:])
    for i in range(n - 1, -1, -1):
        suffix[i] = max(suffix[i + 1], depths[i])
    return [max(prefix[tin[q]], suffix[tout[q] + 1]) for q in queries]


def brute(root, queries):
    def height(node, banned):
        if node is None or node.val == banned:
            return -1
        return 1 + max(height(node.left, banned), height(node.right, banned))
    return [height(root, q) for q in queries]


r1 = build_tree([1, 3, 4, 2, None, 6, 5, None, None, None, None, None, 7])
assert tree_queries(r1, [4]) == [2]
r2 = build_tree([5, 8, 9, 2, 1, 3, 7, 4, 6])
assert tree_queries(r2, [3, 2, 4, 8]) == [3, 2, 3, 2] == tree_queries_euler(r2, [3, 2, 4, 8])
assert tree_queries(build_tree([1, 2]), [2]) == [0]
for _ in range(300):
    n = random.randint(2, 15)
    t = random_tree(n)
    qs = [v for v in range(1, n + 1) if v != t.val]
    assert tree_queries(t, qs) == tree_queries_euler(t, qs) == brute(t, qs)
chain = cur = TreeNode(1)
for v in range(2, 100_001):                             # 十萬層的鏈，節點 v 的深度是 v - 1
    cur.left = TreeNode(v)
    cur = cur.left
qs = [2, 50_000, 100_000]
assert tree_queries(chain, qs) == [0, 49_998, 99_998] == tree_queries_euler(chain, qs)
print("all tests passed")
```

### 複雜度與邊界

預處理 O(n) 時間：三遍線性走訪（Euler 版是一次 DFS 加兩個前後綴陣列）；每個查詢 O(1)，總共 O(n + m)。空間 O(n) 存 depth、height、rest。兩個版本都不使用遞迴，十萬層的鏈也能處理。邊界情況：空子樹的高度必須是 -1，這樣「沒有兄弟」時式子會退化成 `depth(u)`，代表父節點本身仍在；`rest(root) = 0` 只是讓公式在根的子節點上成立，根本身不會被查詢；移除根的唯一子節點時答案是 0（範例 3）；高度以邊數計算，若誤用節點數，所有答案都會多 1。

### Follow-up

> [!question]- F1. 如果查詢不再獨立，每次移除都會累積下去呢？
> 用 Euler tour 把樹攤平成深度陣列，每次移除 v 等於把區間 `[tin(v), tout(v)]` 全部設成「已刪除」（例如負無限大），答案是整個陣列的最大值。用支援「區間賦值、全域最大值」的 segment tree（第 26 章），每次 O(log n)。若同一個節點被重複移除或它的祖先已被移除，區間賦值仍然正確，不需要特判。總時間 O(n + m log n)。

> [!question]- F2. 有沒有不需要 rerooting 式子的做法？
> 有，依深度分組。移除深度 d 的節點 v 之後，所有深度小於 d 的節點都還在（至少高度 d − 1），而所有更深的節點都屬於某個深度 d 的節點的子樹。所以答案是 `max(d − 1, max{ d + height(w) : w 在深度 d、w ≠ v })`。對每個深度預先記錄 `d + height(w)` 的前兩名，查詢時若 v 是第一名就用第二名，否則用第一名，O(n) 預處理、O(1) 查詢。這個「前兩名」技巧和核心題 3 F2 相同，是「排除自己後的最大值」的通用做法。

> [!question]- F3. 如果還要回傳移除後最深的節點是哪一個呢？
> 把所有「高度」都換成 `(高度, 節點)` 的 pair：height 存子樹中最深的節點，rest 存子樹外最深的節點，`max` 依高度比較。rerooting 的式子完全不變，只是取最大值時一起帶上節點。若有多個最深節點，要先和面試官確認回傳哪一個（例如值最小的），並把它加進比較鍵。時間與空間仍是 O(n)。

> [!question]- F4. 如果一次查詢要同時移除兩棵子樹 u、v 呢？
> 用 Euler tour。若其中一棵包含另一棵（區間包含），就等於只移除較大的那棵，套原本的 O(1) 答案。否則兩個區間不相交，假設 `[a1, b1]` 在 `[a2, b2]` 左邊，答案是 `max(prefix[a1], rangeMax(b1 + 1, a2 − 1), suffix[b2 + 1])`，中間那段用 sparse table（O(n log n) 預處理）做到 O(1) 查詢。rerooting 式子處理不了這個變形，因為兩次移除會互相影響，所以 Euler tour 的「子樹 = 區間」觀點更有彈性。

> [!question]- F5. 如果是 N-ary tree，或樹以 parent 陣列的形式給出呢？
> Euler tour 版本完全不變，只是走訪子節點的迴圈改成走訪 children list。rerooting 版本中「兄弟的最大高度」變成「所有其他子節點的最大高度」，對每個節點 u 預先記錄子節點高度的前兩名，計算某個子節點 c 的 rest 時，若 c 是第一名就用第二名。以 parent 陣列給出時，先用 O(n) 建 children list，再用 BFS 取得由上往下的順序。整體仍是 O(n) 預處理、O(1) 查詢。

### 心得

關鍵突破是看出答案取決於子樹**外面**的部分，所以除了後序的 height，還要用前序把 `rest` 由上往下傳，式子 `rest(v) = max(rest(parent), depth(parent) + 1 + height(sibling))` 一次涵蓋所有情況。它把本章兩種資訊流（由下往上的回傳值、由上往下的參數）放進同一題，是本章的上限。面試時先說 O(n · m) 的暴力法並指出 10⁹ 太慢，再說「我要預先算出每個節點的答案」，畫出「父節點以上、父節點本身、兄弟子樹」三個部分，最後提 Euler tour 作為另一種觀點，並主動說明為什麼要寫成迭代。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 層序 BFS | 「每一層」「最小深度」「離根的距離」 | `for _ in range(len(queue))` 固定層大小；用 `deque` | 核心題 1（102）、核心題 2（199）、103、107、111、637、117 |
| 參數由上往下傳 | 答案依賴從根走下來的路徑：深度、座標、路徑最大值 | 前序，把資訊當參數；先右後左控制「第一個到達」 | 核心題 2（199 DFS 版）、難題 4（987）、1448、112、113、129 |
| 後序回傳摘要 | 答案只依賴子樹：高度、是否平衡、子樹和 | 合約寫清楚；需要多個值時回傳 tuple 或用哨兵值 | 104、110、572、核心題 5（236） |
| 後序 + 全域答案 | 任兩點之間的路徑，不一定經過根 | 路徑以最高點分類；回傳單邊、在節點組合兩邊；負數用 `max(0, ·)` | 核心題 3（543）、難題 1（124）、687、1372 |
| 後序回傳狀態 | 在節點上做選擇，相鄰節點互相影響 | 葉子的交換論證 → 貪婪；或每個節點幾個狀態的樹 DP | 難題 3（968）、337（第 24 章核心題 1） |
| 分治重建與序列化 | 由遍歷序列建樹；把樹轉成字串 | 根切開序列；hash map 找位置；讀取順序 = 建構順序；空節點標記 | 核心題 4（105）、難題 2（297）、106、889、1008、449 |
| 兩遍走訪（rerooting） | 對每個節點問「子樹外面」或「以它為根」的問題 | 先後序算子樹內資訊，再前序傳子樹外資訊 | 難題 5（2458）、834（第 24 章難題 1）、1145 |
| 樹攤平成陣列 | 子樹查詢、移除子樹、子樹區間更新 | Euler tour：子樹 = 連續區間，接前後綴或 segment tree | 難題 5（2458 Euler 版）、第 26 章的子樹查詢 |
| 收集後排序或分桶 | 依座標或多重鍵輸出 | 走訪只傳座標，順序交給排序鍵 | 難題 4（987）、314、top view／bottom view |
| LCA 與祖先查詢 | 共同祖先、兩節點距離、多次查詢 | 後序回傳「找到了誰」；多次查詢用 binary lifting | 核心題 5（236）、235、1644、1650、1676、2096 |

**下限與上限**。最簡單的形式是 104 Maximum Depth 這類「回傳值就是答案」的後序，以及 102 這類標準 BFS，考的是 base case 與迴圈寫對。中間層的題目需要設計合約：543 的回傳值與答案不同、236 的回傳值同時代表「找到 p 或 q」與「找到 LCA」、105 要看出前序的取值順序等於建構順序。上限的題目難在三個地方，常常同時出現：第一，**回傳值需要額外觀察才能定義**，例如 124 要用 `max(0, ·)` 處理負數、968 要先用交換論證證明葉子不裝，才知道三種狀態夠用；第二，**需要兩個方向的資訊**，例如 2458 的答案在子樹外面，必須補一次由上往下的走訪，或改用 Euler tour 把問題變成區間；第三，**樹只是外殼，核心是另一個 pattern**，例如 987 的核心是排序鍵的設計，297 的核心是格式的無歧義性。

**與其他 pattern 的關係**。BFS 層序和第 15 章圖的 BFS 是同一個迴圈，樹只是不需要 `visited` 的特例；把樹看成無向圖（建 parent 指標）之後，「距離 target 為 k 的所有節點」（863）這類題目就變成圖的 BFS。後序回傳狀態是第 24 章樹 DP 的入門：968 和 337 是「每個節點幾個狀態」的典型，834 則是 2458 的 rerooting 推廣成「以每個節點為根的距離和」。BST（第 13 章）是加了大小關係的二元樹，中序變成排序序列，很多本章的題目（LCA、重建、序列化）在 BST 上都有更簡單的版本。Euler tour 把子樹變成陣列區間，接上第 7 章的前綴和或第 26 章的 segment tree，就能處理子樹的更新與查詢。

**容易混淆之處**。第一，「路徑」的定義要先問清楚：可以不經過根嗎？必須從根開始或到葉子結束嗎？長度算邊數還是節點數？543、124、112、687 的差別全在這裡。第二，DFS 與 BFS 不是任意互換的：987 與 314 的差別說明了，同一格的順序若是「走訪順序」就要用 BFS，若是「值的順序」就必須排序；top view 用 DFS 必須額外比較深度。第三，二元樹的題目不一定是 BST，236 不能用值的大小判斷方向；反過來，看到 BST 就要想到能不能用大小關係把 O(n) 降到 O(h)。第四，遞迴深度在 Python 中是真實的限制，n ≥ 10⁴ 的題目要準備迭代版本。

## 本章重點整理

- 寫樹的題目，先寫下遞迴函式的合約：收到什麼參數、回傳什麼、是否更新全域答案；正確性用結構歸納法一句話說明。
- 資訊只有三種流法：參數由上往下（深度、座標、路徑最大值）、回傳值由下往上（高度、狀態、是否找到）、在節點組合兩邊並更新全域答案。
- BFS 層序的 invariant 是「每輪開始時 queue 恰好是一整層」，必須先用 `len(queue)` 固定層大小，queue 要用 `deque`。
- 「任兩點之間的路徑」一律以最高點分類：回傳單邊給父節點，在節點把兩邊接起來更新答案（543、124）；有負數時用 `max(0, ·)` 允許不接，答案初始值用負無限大。
- 右視圖是「每層最右」，不是「一直往右走」；DFS 先右後左時，第一個到達某深度的節點就是答案。
- 前序加中序重建樹：前序的取值順序等於遞迴的建構順序，用 iterator 取值、hash map 找位置、索引區間代替切片，O(n)；值必須互不相同。
- 序列化要寫出空節點，k 個節點會產生 k + 1 個空標記，讓每棵子樹在字串中自我界定；BST 可以省掉空標記。
- LCA 的後序合約是「回傳子樹裡找到的 p、q 或 LCA」，兩邊都非空時自己就是 LCA；不保證存在時要走完整棵樹並計數，多次查詢用 binary lifting。
- 節點上的選擇問題（968）先找葉子的交換論證得到由下往上的貪婪，或改用每個節點幾個狀態的樹 DP；成本不同時只有 DP 成立。
- 輸出順序由多個鍵決定時（987），讓走訪只負責傳座標，順序交給排序鍵；同格依走訪順序（314）才能只用 BFS。
- 答案取決於子樹外面時（2458），先後序算子樹內資訊、再前序傳子樹外資訊（rerooting），或用 Euler tour 把子樹變成區間。
- Python 的遞迴上限約 1000，n ≥ 10⁴ 的鏈會出錯；準備好顯式 stack 的迭代寫法，或用「BFS 順序反向處理」做由下往上的計算。
