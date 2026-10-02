---
chapter: 13
title: BST 與 Trie
part: 2
---

# 第 13 章　BST 與 Trie

> [!abstract] 本章地圖
> **一句話**：BST 把「大小順序」寫進樹的形狀，Trie 把「共同前綴」寫進樹的路徑；兩者的每個節點都代表一整群 key（BST 是一段數值區間，Trie 是一個前綴），所以每次操作只要沿著一條根到節點的路徑往下走，路徑以外的 key 全部不必看。
>
> **辨識訊號**：
> - 題目直接給一棵 BST，要求驗證、第 k 小、刪除、修復，或找前驅／後繼、範圍內的值
> - 需要「中序走訪就是排序序列」這個性質：比較相鄰值、找逆序、依序數到第 k 個
> - 大量字串，查詢是「有沒有以某前綴開頭的字」「自動完成」「萬用字元 `.` 搜尋」
> - 很多個單字要同時在一個 grid 或一段長字串裡搜尋，逐字搜尋會重複走同樣的前綴
> - 「最大 XOR」「XOR 小於 k 的數對」：把整數看成 0／1 字串，建 binary trie 從高位貪婪
> - 字串由字典中的其他字串串接而成，需要從某個位置出發列舉所有「是單字的前綴」
>
> **核心題**：98、230、450、208、211
>
> **難題**：212、745、1707、472、99

## 13.1 這個 Pattern 解決什麼問題

先看一個最小的例子。你要維護一個整數集合，支援三種操作：插入、刪除，以及「回傳 ≥ x 的最小值」。用 hash set，插入刪除是 O(1)，但它完全不知道大小順序，查詢「≥ x 的最小值」只能掃過全部元素，O(n)。用排序陣列，查詢可以用第 8 章的 binary search 做到 O(log n)，但插入和刪除要搬動後面的元素，O(n)。兩種結構各缺一半：一個有順序但難修改，一個好修改但沒有順序。

Binary search tree（BST，二元搜尋樹）把兩者合在一起。它的規則只有一條：**每個節點左子樹的所有值都比它小，右子樹的所有值都比它大**。於是每個節點都等於一次 binary search 的「mid」：拿 x 和它比，就能丟掉一整棵子樹。查詢、插入、刪除都只走一條根到葉的路徑，成本是 O(h)，h 是樹高；樹平衡時 h = O(log n)。更重要的是，這條規則等價於「中序走訪（左、根、右）得到嚴格遞增的序列」，本章 BST 的題目幾乎都在利用這個等價關係：驗證 BST 就是檢查中序是否遞增，第 k 小就是中序的第 k 個，修復 BST 就是在中序裡找被交換的兩個位置。

字串集合有類似的問題，而且更明顯。假設字典有 N 個單字、平均長度 L，要回答「有沒有單字以 `pre` 開頭」。把單字放進 hash set 只能做精確查詢；要支援前綴查詢，要嘛每次掃過全部單字（O(N·L)），要嘛把每個單字的所有前綴也放進 set（總共 O(N·L) 個前綴，每個前綴的 hash 又要 O(L)）。Trie（字首樹，又叫 prefix tree）的做法是：讓每個節點代表一個前綴，從根往下走一條邊就多一個字元，共同前綴只存一次。查詢 `pre` 時，沿著 `pre` 的字元往下走 |pre| 步，走得下去就代表有單字以它開頭，成本和 N 無關。

這兩個結構的共同點是：**節點的位置本身就帶有資訊**。BST 的節點位置決定了它子樹內所有值的範圍（例如「比 5 大、比 8 小」），Trie 的節點位置決定了它子樹內所有字串的前綴。所以題目只要問的是「某個範圍內」或「某個前綴下」的 key，都可以從根走一條路徑定位到那個子樹。本章難題的上限，就是把這個「同時代表一群 key」的節點和其他技巧組合：Trie 加 backtracking 同時搜尋上萬個單字（212）、Trie 加離線排序回答帶限制的最大 XOR（1707）、Trie 加 DP 判斷字串能否被切成字典單字（472）。

## 13.2 辨識訊號

| 題目特徵 | 為什麼是 BST／Trie | 本章哪一題 |
|---|---|---|
| 判斷一棵二元樹是不是 BST | 每個節點都被祖先限制在一個開區間內；等價於中序嚴格遞增 | 核心題 1（98） |
| BST 的第 k 小、中位數、依序列出 | 中序走訪就是排序序列，走到第 k 個就停 | 核心題 2（230） |
| BST 的插入、刪除、找前驅後繼，要求 O(h) | 每一步和節點比較就能丟掉一棵子樹 | 核心題 3（450） |
| 字典的前綴查詢、自動完成 | 每個 Trie 節點就是一個前綴，查詢只走 |prefix| 步 | 核心題 4（208） |
| 萬用字元搜尋（`.` 可以配任何字元） | 普通字元只走一條邊，`.` 才分岔，比對所有單字便宜得多 | 核心題 5（211） |
| 很多單字要在同一個 grid 中找 | 把單字建成 Trie，DFS 一次同時推進所有單字，不是前綴就剪枝 | 難題 1（212） |
| 同時限制前綴與後綴 | 把「後綴 + 分隔符 + 單字」插入 Trie，兩個條件變成一個前綴 | 難題 2（745） |
| 最大 XOR，或 XOR 和某個門檻比較 | 整數是 0／1 字串，從高位起選相反的位元最划算 | 難題 3（1707） |
| 字串能否由字典單字串接 | 從每個可到達的位置沿 Trie 往下走，一次列出所有是單字的前綴 | 難題 4（472） |
| BST 中有兩個值被交換 | 中序序列出現一或兩個逆序，第一個逆序的前者與最後一個逆序的後者就是兩個錯誤節點 | 難題 5（99） |

一個實用的反向檢查：如果題目只需要「精確查詢某個 key 在不在」，hash set 就夠了，不必建 Trie 或 BST；只有當查詢涉及**順序**（第 k 小、≥ x 的最小值、範圍）或**前綴**（以某字串開頭、逐字元推進、萬用字元）時，這兩個結構才真正有優勢。

## 13.3 BST 模板與原理

BST 的定義有三種等價的說法，本章每一題都會用到其中一種：

1. **局部定義**：每個節點的左子樹所有值 < 節點值 < 右子樹所有值，而且左右子樹也都是 BST。
2. **區間定義**：根的合法範圍是 (−∞, +∞)；往左走時把上界收緊成目前節點的值，往右走時把下界收緊成目前節點的值。每個節點的值都必須落在自己的開區間裡。
3. **中序定義**：中序走訪（左子樹、根、右子樹）得到的序列嚴格遞增。

區間定義最適合「由上往下」檢查（核心題 1），中序定義最適合「依大小順序」處理（核心題 2、難題 5），局部定義則是插入、刪除時判斷往哪邊走的依據（核心題 3）。下面是基本操作的模板，全部用迭代寫法，因為 Python 預設的遞迴深度上限大約是 1000，而退化成一條鏈的 BST 深度可以等於 n。

```python
import random
from bisect import bisect_left


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def bst_search(root, target):
    """回傳值為 target 的節點，不存在回傳 None。O(h)。"""
    node = root
    while node is not None and node.val != target:
        node = node.left if target < node.val else node.right
    return node


def bst_insert(root, val):
    """插入 val（假設原本不存在），回傳根。O(h)。"""
    new = TreeNode(val)
    if root is None:
        return new
    node = root
    while True:
        if val < node.val:
            if node.left is None:
                node.left = new
                return root
            node = node.left
        else:
            if node.right is None:
                node.right = new
                return root
            node = node.right


def ceiling(root, x):
    """回傳 >= x 的最小值；不存在回傳 None。O(h)。"""
    ans, node = None, root
    while node is not None:
        if node.val >= x:
            ans = node.val          # node 是候選；更小的候選只可能在左子樹
            node = node.left
        else:
            node = node.right       # node 和它整個左子樹都 < x，全部丟掉
    return ans


def inorder(root):
    """迭代中序走訪，依序產生遞增的值。總共 O(n)，額外空間 O(h)。"""
    stack, node = [], root
    while stack or node is not None:
        while node is not None:     # 先把左邊一路推進 stack
            stack.append(node)
            node = node.left
        node = stack.pop()          # 左子樹已處理完，輪到自己
        yield node.val
        node = node.right           # 接著處理右子樹


def range_sum(root, lo, hi):
    """[lo, hi] 內所有值的和，只進入可能有答案的子樹（938 題）。"""
    total, stack = 0, [root]
    while stack:
        node = stack.pop()
        if node is None:
            continue
        if lo <= node.val <= hi:
            total += node.val
        if node.val > lo:           # 左子樹的值都 < node.val，可能還有 >= lo 的
            stack.append(node.left)
        if node.val < hi:
            stack.append(node.right)
    return total


for _ in range(200):
    vals = random.sample(range(-50, 50), random.randint(0, 30))
    root = None
    for v in vals:
        root = bst_insert(root, v)
    srt = sorted(vals)
    assert list(inorder(root)) == srt
    for x in range(-52, 52):
        i = bisect_left(srt, x)
        assert ceiling(root, x) == (srt[i] if i < len(srt) else None)
        assert (bst_search(root, x) is not None) == (x in vals)
    lo, hi = sorted(random.sample(range(-55, 55), 2))
    assert range_sum(root, lo, hi) == sum(v for v in vals if lo <= v <= hi)

chain = None
for v in range(3000):               # 依序插入會退化成一條鏈，深度 3000
    chain = bst_insert(chain, v)
assert list(inorder(chain)) == list(range(3000))   # 迭代寫法不受遞迴深度限制
assert ceiling(chain, 2999) == 2999 and ceiling(chain, 3000) is None
print("all tests passed")
```

**Invariant 與每一段為什麼這樣寫**：

- `bst_search` 與 `bst_insert`：每一步都維持「如果 target 在樹裡，它一定在目前 node 的子樹內」。`target < node.val` 時，右子樹全部 > node.val > target，可以整棵丟掉，這就是 binary search 每次丟掉一半的樹狀版本。差別是 BST 不保證「一半」：樹平衡時每步丟掉約一半，退化成鏈時每步只丟掉一個節點。
- `ceiling`：這是第 8 章「第一個 True」在樹上的寫法。pred 是 `val >= x`。遇到 True 的節點，它可能就是答案，先記下來，再往左找有沒有更小的 True；遇到 False 的節點，它和整個左子樹都是 False，往右走。走到 None 時，`ans` 就是最後一次記下的候選，也就是最小的 True。`floor`（≤ x 的最大值）把方向對調即可。
- `inorder`：stack 保存「已經走過、但自己和右子樹還沒處理」的祖先。內層 while 把左鏈推到底，彈出的節點的左子樹一定已經處理完（或為空），所以此時輸出它是正確的中序位置，然後轉向右子樹。每個節點恰好被推入、彈出各一次，總時間 O(n)，stack 最深 O(h)。這個寫法的好處是可以**隨時停下**：核心題 2 走到第 k 個就停，成本是 O(h + k)。
- `range_sum`：只有 `node.val > lo` 時左子樹才可能有 ≥ lo 的值，只有 `node.val < hi` 時右子樹才可能有 ≤ hi 的值。這種剪枝讓成本變成 O(h + 範圍內的節點數)，而不是 O(n)。

**樹高才是複雜度的主角**。本章所有 BST 操作都寫成 O(h)，面試時不要直接說 O(log n)：LeetCode 給的 BST 並不保證平衡，依序插入 1、2、3、… 就會得到一條鏈，h = n。真正保證 O(log n) 的是 AVL tree、red-black tree 等自平衡樹，它們在插入刪除後用旋轉把樹高維持在 O(log n)；面試通常不要求手寫，但要知道它們存在、知道 Java 的 `TreeMap` 和 C++ 的 `std::map` 就是 red-black tree。Python 標準函式庫沒有平衡 BST，需要有序集合時，常見做法是排序 list 加 `bisect`（查詢 O(log n)、插入 O(n) 但常數很小），或第 26 章的 Fenwick tree／segment tree（值域已知時）。

## 13.4 Trie 模板與原理

Trie 的每個節點代表一個前綴：根代表空字串，從節點沿著標記為 `c` 的邊往下走一步，就得到「原前綴 + c」。所以**從根到某個節點的路徑上的字元，拼起來就是這個節點代表的前綴**，字元本身存在邊上（實作時是 children 的 key），節點裡只需要存 children 和一個 `is_end` 旗標。

兩個 invariant 要分清楚：

- **節點存在 ⇔ 至少有一個插入過的單字以這個前綴開頭**。所以 `starts_with(p)` 只要檢查走不走得完 p。
- **`is_end` 為真 ⇔ 這個前綴本身就是一個插入過的單字**。插入 `apple` 之後，`app` 的節點存在但 `is_end` 是假，`search("app")` 必須回傳 False。

```python
import random


class TrieNode:
    __slots__ = ("children", "is_end")      # 節點很多時，__slots__ 能省下不少記憶體

    def __init__(self):
        self.children = {}
        self.is_end = False


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for ch in word:
            nxt = node.children.get(ch)
            if nxt is None:
                nxt = node.children[ch] = TrieNode()
            node = nxt
        node.is_end = True

    def _walk(self, s: str):
        """沿著 s 往下走；走不下去回傳 None。查詢時絕不建立新節點。"""
        node = self.root
        for ch in s:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def search(self, word: str) -> bool:
        node = self._walk(word)
        return node is not None and node.is_end

    def starts_with(self, prefix: str) -> bool:
        return self._walk(prefix) is not None


class BinaryTrie:
    """把非負整數看成固定長度的 0／1 字串（高位在前）。"""

    def __init__(self, bits: int = 30):
        self.bits = bits
        self.child = [[0, 0]]               # 節點用索引表示；0 是根，也代表「沒有子節點」

    def insert(self, x: int) -> None:
        v = 0
        for b in range(self.bits - 1, -1, -1):
            bit = x >> b & 1
            if not self.child[v][bit]:
                self.child[v][bit] = len(self.child)
                self.child.append([0, 0])
            v = self.child[v][bit]

    def max_xor(self, x: int) -> int:
        """回傳 x 與 trie 中某個數的最大 XOR；trie 必須非空。"""
        v = res = 0
        for b in range(self.bits - 1, -1, -1):
            want = (x >> b & 1) ^ 1         # 這一位相反，XOR 才會是 1
            if self.child[v][want]:
                res |= 1 << b
                v = self.child[v][want]
            else:
                v = self.child[v][want ^ 1]
        return res


t = Trie()
for w in ["apple", "app", "apt", "bat"]:
    t.insert(w)
assert t.search("app") and t.search("apple") and not t.search("ap")
assert t.starts_with("ap") and t.starts_with("ba") and not t.starts_with("c")
assert not t.search("apx") and t._walk("apx") is None
assert t.search("") is False and t.starts_with("")     # 空字串是所有單字的前綴
for _ in range(200):
    words = {"".join(random.choice("ab") for _ in range(random.randint(1, 5))) for _ in range(8)}
    tr = Trie()
    for w in words:
        tr.insert(w)
    for _ in range(20):
        q = "".join(random.choice("ab") for _ in range(random.randint(0, 5)))
        assert tr.search(q) == (q in words)
        assert tr.starts_with(q) == any(w.startswith(q) for w in words)

bt = BinaryTrie(bits=5)
for x in [3, 10, 5, 25, 2, 8]:
    bt.insert(x)
assert max(bt.max_xor(x) for x in [3, 10, 5, 25, 2, 8]) == 28    # 5 XOR 25（421 題）
for _ in range(200):
    nums = [random.randrange(1 << 10) for _ in range(random.randint(1, 15))]
    bt = BinaryTrie(bits=10)
    for x in nums:
        bt.insert(x)
    x = random.randrange(1 << 10)
    assert bt.max_xor(x) == max(x ^ y for y in nums)
print("all tests passed")
```

**每一段為什麼這樣寫**：

- `insert` 沿著單字往下走，缺的節點才建立，最後把終點標成 `is_end`。插入的成本是 O(L)，而且只新增「目前 trie 裡還沒有的那段後綴」，共同前綴不會重複存。
- `_walk` 是查詢的唯一入口，它用 `children.get` 而不是 `setdefault`。如果查詢時順手建立了節點，「節點存在 ⇔ 有單字以此開頭」這個 invariant 就被破壞了，之後的 `starts_with` 會回傳錯的 True。
- children 用 dict 還是長度 26 的陣列？dict 只存實際出現的字元，節點稀疏時省空間，也不限定字母集；陣列版本每個節點固定 26 格，存取是 O(1) 索引，在 Java／C++ 中更快，但大部分格子是空的。Python 中 dict 通常是較好的預設；核心題 4 會比較兩種寫法。
- `BinaryTrie` 用兩個平行的整數陣列代替物件，因為 1707 這類題目要插入 10⁵ 個 30 位元的數，會建出數百萬個節點，Python 物件的額外成本太高。0 同時是根的索引和「沒有子節點」的標記，因為根永遠不會是別人的子節點。
- `max_xor` 從最高位開始貪婪：只要能讓這一位的 XOR 是 1 就一定要選，因為 2^b 比所有更低位元加起來的 2^b − 1 還大，低位怎麼選都補不回來。這是難題 3 的核心。

**複雜度**。Trie 的插入與查詢都是 O(L)，L 是字串長度，和字典大小 N 無關；空間最差是 O(總字元數 × 每個節點的大小)。和 hash set 比，Trie 在「精確查詢」上沒有漸進優勢（hash 一個長度 L 的字串也是 O(L)），它的價值在於**逐字元推進**：前綴查詢、萬用字元、在 grid 或長字串上同時推進很多單字，這些都是 hash set 做不到或要重複計算的事情。

## 13.5 BST、Trie、hash 與排序陣列怎麼選

面試時常常不是「一定要用 BST 或 Trie」，而是要能說出為什麼選它、不選別的。下表比較 n 個 key（字串時長度為 L）的常見操作：

| 操作 | hash set／dict | 排序 list + `bisect` | 平衡 BST（`TreeMap`） | Trie |
|---|---|---|---|---|
| 精確查詢 | O(1)，字串 O(L) | O(log n) 次比較 | O(log n) 次比較 | O(L) |
| 插入／刪除 | O(1) | O(n)（搬移，但常數小） | O(log n) | O(L) |
| 前驅、後繼、≥ x 的最小值 | 不支援 | O(log n) | O(log n) | 可以，O(L · 字母集) |
| 第 k 小 | 不支援 | O(1) 索引 | 需要 size 欄位，O(log n) | 需要計數欄位 |
| 以 p 開頭的字是否存在 | 要另存所有前綴 | `bisect_left(p)` 後檢查 `startswith`，O(L log n) | 同左 | O(\|p\|) |
| 萬用字元、grid 上同時找多字 | 只能逐一比對 | 只能逐一比對 | 只能逐一比對 | DFS 時共享前綴，自然剪枝 |
| Python 標準函式庫 | 內建 | 內建 `bisect` | 沒有 | 自己寫，約 20 行 |

兩個常被忽略的細節。第一，**排序 list 也能回答前綴是否存在**：所有以 p 開頭的字串在排序後是連續的一段，而且這段的起點就是 `bisect_left(words, p)`，所以只要檢查那個位置的字是否以 p 開頭。若字典是靜態的、只問前綴存在與否，這比 Trie 更省記憶體。Trie 真正不可取代的情況是查詢要**逐字元推進並分岔**（211、212、472），或要**依位元貪婪**（1707）。第二，**BST 題目通常不是要你實作平衡樹**，而是考你能不能利用 BST 的順序性質（中序遞增、區間限制）在 O(h) 或 O(n) 內完成；面試官追問「如果要保證 O(log n)」時，回答自平衡樹與 size 欄位即可。

## 13.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 驗證 BST 時只比較父子 | `[5, 4, 6, null, null, 3, 7]` 被判為合法（3 在 5 的右子樹卻比 5 小） | 每個節點帶著祖先給的開區間 `(low, high)` 往下傳，或檢查中序嚴格遞增 |
| 用 `±2³¹` 這類整數哨兵當邊界 | 節點值剛好是 `-2³¹` 或 `2³¹ − 1` 時誤判；Java 中 `Integer.MIN_VALUE` 無法表示「無下界」 | 用 `None` 表示沒有限制（Python 的 `float("inf")` 也可以，但換成 Java 就沒有對應的 int），或在 Java 用 `Long`／`Integer` 物件 |
| 忽略重複值的規則 | `[2, 2, 2]` 被判為合法，或刪除時找錯節點 | 先確認題目是否允許重複、重複放哪一邊；LeetCode 的 BST 預設嚴格不等 |
| Python 遞迴走訪退化的 BST | 一條長度 10⁴ 的鏈觸發 `RecursionError` | 用迭代 stack 寫中序；或明確說明呼叫 `sys.setrecursionlimit` 的前提 |
| 宣稱 BST 操作是 O(log n) | 面試官指出依序插入會退化成鏈 | 一律寫 O(h)，再補充「平衡時 h = O(log n)」 |
| 刪除有兩個子節點的節點後，忘記刪掉後繼 | 樹中出現兩個相同的值，或後繼的右子樹遺失 | 用後繼的值覆蓋後，在右子樹中刪除後繼；後繼最多只有右子節點 |
| Trie 忘記 `is_end` | 插入 `apple` 後 `search("app")` 回傳 True | 精確查詢必須檢查終點的 `is_end`，前綴查詢才只看節點是否存在 |
| 查詢時建立節點 | 用 `setdefault` 寫 `search`，之後 `starts_with` 回傳錯的 True、記憶體暴增 | 查詢一律用 `get`，走不下去就回傳 |
| Word Search II 找到同一個字兩次 | 結果有重複，或用 set 去重導致額外成本 | 找到後把節點上的單字移除，並剪掉空的分支 |
| Binary trie 位元數不夠 | 值到 10⁹ 卻只用 20 個位元，高位被截掉，答案錯誤 | 位元數取 `max_value.bit_length()`，10⁹ 需要 30 位 |

## 核心題 1｜98. Validate Binary Search Tree｜Medium

### 題目

給一棵二元樹的根節點 `root`，判斷它是不是合法的 BST。合法的定義是：每個節點的左子樹只包含**嚴格小於**該節點值的節點，右子樹只包含**嚴格大於**該節點值的節點，而且左右子樹本身也都是合法的 BST。限制：節點數在 1 到 10⁴ 之間，節點值在 `-2³¹` 到 `2³¹ − 1` 之間。樹的輸入用 level order 表示，`null` 代表該位置沒有節點。

- 範例 1：`root = [2, 1, 3]`，回傳 `True`。
- 範例 2：`root = [5, 1, 4, null, null, 3, 6]`，回傳 `False`；根的右子節點是 4，比 5 小。
- 範例 3：`root = [5, 4, 6, null, null, 3, 7]`，回傳 `False`。每一對父子都符合大小關係，但 3 在 5 的右子樹裡，卻比 5 小。
- 範例 4（邊界）：`root = [2, 2, 2]`，回傳 `False`，因為相等不算合法；只有一個節點 `[-2147483648]` 時回傳 `True`。

### 思路

最直接的暴力解照著局部定義寫：對每個節點，掃過它整個左子樹確認都比它小、掃過整個右子樹確認都比它大。每個節點都要掃一次自己的子樹，退化成鏈時總共是 1 + 2 + … + n = O(n²)。另一個常見的「快速」寫法是只比較每個節點和它的左右子節點，這是 O(n)，但它是**錯的**：範例 3 中每一對父子都合法，問題出在 3 和祖父 5 之間。瓶頸在於：一個節點的限制不只來自父親，而是來自整條祖先路徑。

關鍵觀察是 13.3 節的區間定義。根可以是任何值，範圍是 (−∞, +∞)；走到某個節點的左子節點時，那個子節點以下的所有值都必須小於目前節點，所以上界收緊成目前節點的值；走到右子節點時下界收緊。於是每個節點只需要和**兩個數**比較：祖先傳下來的下界與上界。這兩個數已經濃縮了整條祖先路徑的所有限制，因為往右走過的祖先中最大的那個值就是下界，往左走過的祖先中最小的那個值就是上界。每個節點檢查一次，O(n)。

另一個等價的做法是中序定義：中序走訪的序列必須嚴格遞增，所以只要在走訪時記住前一個值 `prev`，每次比較 `prev < 目前值`。兩種寫法都是 O(n)，區間寫法遇到違規能在任何走訪順序下立刻停止，中序寫法則可以直接重用 13.3 節的迭代模板。兩者都要用迭代，因為 n = 10⁴ 的鏈會超過 Python 預設的遞迴深度。

邊界值要用 `None` 表示「沒有限制」，而不是 `float("-inf")` 以外的整數哨兵。如果用 `-2³¹` 當初始下界，值剛好是 `-2³¹` 的根就會因為 `val <= low` 被誤判；Python 的 `float("inf")` 雖然可以和整數比較而不出錯，但在 Java 中沒有對應的 int，養成用 `None` 的習慣比較安全。

```text
範例 3：[5, 4, 6, null, null, 3, 7]

            5          範圍 (-∞, +∞)
          /   \
         4     6       4：(-∞, 5)     6：(5, +∞)
              / \
             3   7     3：(5, 6)      7：(6, +∞)

只看父子：4 < 5、6 > 5、3 < 6、7 > 6，全部通過 → 誤判為合法
看區間：  3 必須落在 (5, 6)，但 3 <= 5 → 不合法

迭代 stack 的過程（每個元素是 (節點, 下界, 上界)，先推左再推右，彈出右）
步驟  彈出            檢查              推入
 1   (5, -, -)       通過              (4, -, 5)、(6, 5, -)
 2   (6, 5, -)       5 < 6，通過       (3, 5, 6)、(7, 6, -)
 3   (7, 6, -)       6 < 7，通過       兩個 None
 4   (3, 5, 6)       3 <= 5，違規      回傳 False
```

第 2 步走到 6 時，它從父親 5 繼承了下界 5，因為它在 5 的右邊；推入左子節點 3 時，上界收緊成 6，下界仍然是 5。所以 3 的合法範圍是 (5, 6)，這個開區間裡根本沒有整數，任何值放在那裡都不合法。第 4 步立刻發現違規，不必走完整棵樹。

### 解法

```python
import random
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build(vals):
    """由 level order 串列（None 表示空位）建樹。"""
    if not vals or vals[0] is None:
        return None
    root = TreeNode(vals[0])
    q, i = deque([root]), 1
    while q and i < len(vals):
        node = q.popleft()
        if i < len(vals) and vals[i] is not None:
            node.left = TreeNode(vals[i])
            q.append(node.left)
        i += 1
        if i < len(vals) and vals[i] is not None:
            node.right = TreeNode(vals[i])
            q.append(node.right)
        i += 1
    return root


def is_valid_bst(root) -> bool:
    stack = [(root, None, None)]            # (節點, 下界, 上界)；None 代表沒有限制
    while stack:
        node, low, high = stack.pop()
        if node is None:
            continue
        if (low is not None and node.val <= low) or (high is not None and node.val >= high):
            return False
        stack.append((node.left, low, node.val))     # 往左：上界收緊
        stack.append((node.right, node.val, high))   # 往右：下界收緊
    return True


def is_valid_bst_inorder(root) -> bool:
    stack, node, prev = [], root, None
    while stack or node is not None:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()
        if prev is not None and node.val <= prev:    # 中序必須嚴格遞增
            return False
        prev = node.val
        node = node.right
    return True


def brute(root) -> bool:
    def values(n):
        return [] if n is None else values(n.left) + [n.val] + values(n.right)

    def ok(n):
        if n is None:
            return True
        return (all(v < n.val for v in values(n.left))
                and all(v > n.val for v in values(n.right))
                and ok(n.left) and ok(n.right))
    return ok(root)


def insert(root, v):
    if root is None:
        return TreeNode(v)
    node = root
    while True:
        side = "left" if v < node.val else "right"
        if getattr(node, side) is None:
            setattr(node, side, TreeNode(v))
            return root
        node = getattr(node, side)


cases = [([2, 1, 3], True), ([5, 1, 4, None, None, 3, 6], False),
         ([5, 4, 6, None, None, 3, 7], False), ([2, 2, 2], False),
         ([-2**31], True), ([2**31 - 1], True), ([-2**31, None, 2**31 - 1], True),
         ([1, 1], False), ([3, 1, 5, 0, 2, 4, 6], True)]
for vals, expect in cases:
    assert is_valid_bst(build(vals)) == expect == is_valid_bst_inorder(build(vals))

chain = TreeNode(0)                          # 深度 10⁴ 的右鏈
node = chain
for v in range(1, 10**4):
    node.right = TreeNode(v)
    node = node.right
assert is_valid_bst(chain) and is_valid_bst_inorder(chain)
node.right = TreeNode(5)                     # 最底端放一個違規的值
assert not is_valid_bst(chain) and not is_valid_bst_inorder(chain)

for _ in range(500):
    vals = random.sample(range(30), random.randint(1, 10))
    root = None
    for v in vals:
        root = insert(root, v)
    if random.random() < 0.6:                # 隨機改壞一個節點
        nodes, q = [], [root]
        while q:
            n = q.pop()
            if n:
                nodes.append(n)
                q += [n.left, n.right]
        random.choice(nodes).val = random.randint(-2, 32)
    assert is_valid_bst(root) == is_valid_bst_inorder(root) == brute(root)
print("all tests passed")
```

### 複雜度與邊界

兩種寫法時間都是 O(n)：每個節點被檢查一次，遇到違規就提早結束。空間 O(h)：中序版本的 stack 最多存一條左鏈；區間版本是 DFS，stack 中最多同時有 O(h) 層、每層留下一個尚未處理的兄弟，所以也是 O(h)。邊界情況：只有一個節點時一定合法；節點值是 `-2³¹` 或 `2³¹ − 1` 時，用 `None` 當邊界才不會誤判；相等的值（`[1, 1]`、`[2, 2, 2]`）必須回傳 False，所以比較用 `<=` 與 `>=`；深度 10⁴ 的鏈用迭代不會觸發 `RecursionError`。

### Follow-up

> [!question]- F1. 如果題目允許重複值，規定「重複的值一律放在左子樹」（左 ≤ 根 < 右），要怎麼改？
> 區間寫法只要把左邊的上界改成「可以等於」：左子節點的範圍是 `(low, val]`，右子節點是 `(val, high)`，檢查時對上界用 `>`、對下界用 `<=`。中序寫法在這裡**不夠**：中序只能檢查「非遞減」，但 `[1, 1]`（重複值在左，合法）和 `[1, null, 1]`（重複值在右，不合法）的中序都是 `[1, 1]`，中序序列根本分不出重複值放在哪一邊。這是面試官很喜歡用來區分「背模板」與「理解定義」的追問，正確答案是用區間寫法，仍然 O(n)。

> [!question]- F2. 如果樹不是 BST，要找出「最大的 BST 子樹」有幾個節點呢（333. Largest BST Subtree）？
> 由上往下的區間寫法不適用，因為每個子樹都要各自判斷。改成後序走訪（第 12 章的由下往上 DFS），每個節點回傳四個值：子樹是不是 BST、子樹最小值、子樹最大值、子樹大小。節點是 BST ⇔ 左右都是 BST 且 `左最大 < val < 右最小`，此時大小是左右相加再加一，最小值與最大值分別來自左子樹與右子樹（空子樹用 +∞／−∞ 讓比較自動成立）。每個節點 O(1)，總共 O(n)，比「對每個子樹呼叫一次 98」的 O(n²) 好。

> [!question]- F3. 如果給的不是樹，而是一個序列，問它是不是某棵 BST 的前序走訪結果呢（255. Verify Preorder Sequence in BST）？
> 用 monotonic stack（第 10 章）模擬：前序是「根、左子樹、右子樹」，stack 存目前還在等右子樹的祖先，`low` 是目前的下界。對每個值 x：若 `x < low` 就違規；否則當 x 比 stack 頂大時，代表已經轉進某個祖先的右子樹，不斷彈出並把 `low` 更新成彈出的值；最後把 x 推入。O(n) 時間、O(n) 空間；若可以修改輸入陣列，把它當 stack 用就是 O(1) 額外空間。這題和本題是同一個「下界由往右轉的祖先決定」的觀察。

> [!question]- F4. 如果樹非常深（例如 10⁶ 層），面試官要求不用 stack、O(1) 額外空間呢？
> 用 Morris inorder traversal：對每個有左子樹的節點，找到它在左子樹中的中序前驅（左子樹最右的節點），暫時把前驅的 `right` 指回自己，當作「走完左子樹後回來的路」；第二次經過時再把它還原。走訪過程中照樣維護 `prev` 比較遞增。每條邊最多被走兩次，時間仍是 O(n)，額外空間 O(1)。要注意的是：發現違規時不能直接 `return`，否則有些暫時的指標還沒還原，樹會被改壞；應該記下結果、繼續走完（或至少把目前節點相關的線索還原）再回傳。難題 5 會用到同一個技巧。

## 核心題 2｜230. Kth Smallest Element in a BST｜Medium

### 題目

給一棵 BST 的根節點 `root` 和整數 `k`，回傳樹中第 k 小的值（k 從 1 開始）。限制：節點數 n 滿足 `1 <= k <= n <= 10⁴`，節點值在 0 到 10⁴ 之間，且互不相同。原題的進階要求是：如果這棵 BST 經常被插入、刪除，而且第 k 小的查詢很頻繁，要怎麼優化？

- 範例 1：`root = [3, 1, 4, null, 2]`、`k = 1`，回傳 `1`。
- 範例 2：`root = [5, 3, 6, 2, 4, null, null, 1]`、`k = 3`，中序是 `1, 2, 3, 4, 5, 6`，回傳 `3`。
- 範例 3（邊界）：`root = [1]`、`k = 1`，回傳 `1`。
- 範例 4（邊界）：`k = n` 時回傳最大值，例如範例 2 中 `k = 6` 回傳 `6`。

### 思路

暴力解是把所有節點的值收集起來排序，取第 k 個，O(n log n)。稍好一點是利用中序定義：中序走訪本身就是遞增序列，收集成 list 後取 `vals[k - 1]`，O(n) 時間、O(n) 空間。這已經正確，但浪費在兩個地方：k 很小時仍然走完整棵樹，而且存下了所有值。

關鍵觀察：13.3 節的迭代中序可以**隨時停下**。每彈出一個節點就是「下一個更大的值」，所以只要數到第 k 次彈出就回傳。成本是把左鏈推進 stack 的 O(h)，加上 k 次彈出與相應的推入，總共 O(h + k)。Invariant 是：stack 中的節點由頂到底遞增，而且它們是「所有比已彈出值大的值中，最小的那一條左鏈」；所以 stack 頂永遠是下一個中序值。

這題的真正考點是進階要求。如果樹會頻繁修改、查詢也頻繁，每次 O(h + k) 在 k 接近 n 時就是 O(n)。做法是在每個節點多存一個 `size`（子樹節點數），於是可以像 binary search 一樣往下走：左子樹有 `L` 個節點，若 `k <= L` 答案在左邊；若 `k == L + 1` 答案就是目前節點；否則到右子樹找第 `k − L − 1` 小。每一步只走一層，O(h)；插入刪除時沿路更新 size，也是 O(h)。配合平衡樹，所有操作都是 O(log n)，這就是 order statistic tree（順序統計樹）。

```text
root = [5, 3, 6, 2, 4, null, null, 1]，k = 3

            5
           / \
          3   6
         / \
        2   4
       /
      1

步驟  動作                              stack（底 → 頂）   已彈出      剩下 k
 1   從 5 一路往左推入 5、3、2、1        [5, 3, 2, 1]       -           3
 2   彈出 1；1 沒有右子節點              [5, 3, 2]          1           2
 3   彈出 2；2 沒有右子節點              [5, 3]             1 2         1
 4   彈出 3；k 變成 0 → 回傳 3            [5]                1 2 3       0

用 size 欄位的 O(h) 查詢（括號內是子樹大小）：
            5(6)
           /    \
        3(4)    6(1)
        /  \
     2(2)  4(1)
     /
   1(1)
在 5：左子樹 size = 4，k = 3 <= 4 → 往左
在 3：左子樹 size = 2，k = 3 == 2 + 1 → 答案是 3
```

第 1 步推入左鏈之後，stack 頂的 1 就是全樹最小值；之後每次彈出都得到下一個更小的未處理值。到第 4 步彈出 3 時剛好數到第 3 個，4、5、6 都不必碰。size 版本則完全不看前兩小的值是什麼，只用「左邊有幾個」決定方向，兩步就到。

### 解法

```python
import random


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def kth_smallest(root, k: int) -> int:
    stack, node = [], root
    while True:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()              # 下一個中序值
        k -= 1
        if k == 0:
            return node.val
        node = node.right


class SizedNode:
    __slots__ = ("val", "left", "right", "size")

    def __init__(self, val):
        self.val, self.left, self.right, self.size = val, None, None, 1


def size(n):
    return n.size if n else 0


def sized_insert(root, val):
    """插入新值並沿路更新 size（假設 val 不存在）。"""
    if root is None:
        return SizedNode(val)
    node = root
    while True:
        node.size += 1
        if val < node.val:
            if node.left is None:
                node.left = SizedNode(val)
                return root
            node = node.left
        else:
            if node.right is None:
                node.right = SizedNode(val)
                return root
            node = node.right


def select(root, k: int) -> int:
    """O(h) 找第 k 小。"""
    node = root
    while True:
        left = size(node.left)
        if k <= left:
            node = node.left
        elif k == left + 1:
            return node.val
        else:
            k -= left + 1
            node = node.right


def build_bst(vals, cls=TreeNode):
    root = None
    for v in vals:
        if cls is SizedNode:
            root = sized_insert(root, v)
            continue
        if root is None:
            root = TreeNode(v)
            continue
        node = root
        while True:
            side = "left" if v < node.val else "right"
            if getattr(node, side) is None:
                setattr(node, side, TreeNode(v))
                break
            node = getattr(node, side)
    return root


r = build_bst([3, 1, 4, 2])
assert kth_smallest(r, 1) == 1
r = build_bst([5, 3, 6, 2, 4, 1])
assert [kth_smallest(r, k) for k in range(1, 7)] == [1, 2, 3, 4, 5, 6]
assert kth_smallest(build_bst([1]), 1) == 1
chain = TreeNode(0)                      # 深度 10⁴ 的右鏈（依序插入的結果）
tail = chain
for v in range(1, 10**4):
    tail.right = TreeNode(v)
    tail = tail.right
assert kth_smallest(chain, 10**4) == 10**4 - 1
for _ in range(300):
    vals = random.sample(range(1000), random.randint(1, 40))
    srt = sorted(vals)
    plain, sized = build_bst(vals), build_bst(vals, SizedNode)
    for k in range(1, len(vals) + 1):
        assert kth_smallest(plain, k) == srt[k - 1] == select(sized, k)
print("all tests passed")
```

### 複雜度與邊界

迭代中序時間 O(h + k)：一開始推入左鏈 O(h)，之後每彈出一個節點最多再推入一條左鏈，而被推入的節點總數不超過「被彈出的 k 個節點」加上「最後停下時 stack 中的 O(h) 個」。空間 O(h)。size 版本查詢 O(h)，每個節點多一個整數。邊界情況：k = 1 時答案是最左節點；k = n 時要走完整棵樹，O(n)；n = 1 時直接回傳根；題目保證 `1 <= k <= n`，若不保證要在走完 stack 後回報錯誤，而不是讓 `stack.pop()` 拋出例外。

### Follow-up

> [!question]- F1. BST 經常插入刪除、又頻繁查詢第 k 小，怎麼做？（原題的 follow-up）
> 在每個節點維護子樹大小 `size`，查詢時依 `size(left)` 決定往左、停下或往右（並把 k 減去 `size(left) + 1`），O(h)。插入時沿路徑每個節點 `size += 1`；刪除時先確認 key 存在，再沿路徑 `size -= 1`（兩個子節點的情況，後繼所在的那段路徑也要減）。若再用 AVL 或 red-black tree 保持平衡，旋轉時用 `size = size(left) + size(right) + 1` 重新計算受影響的兩個節點，所有操作都是 O(log n)。在 Python 面試中，若值域已知，也可以改用第 26 章的 Fenwick tree：以值為索引存 0／1，第 k 小用 Fenwick 上的二分（binary lifting），O(log V)。

> [!question]- F2. 如果要第 k 大呢？
> 把中序的方向反過來：先右、再根、再左（reverse inorder），內層 while 改成一路往右推，數到第 k 次彈出就回傳，O(h + k)。也可以先數總節點數 n，再求第 n − k + 1 小，但那需要 O(n) 先數一遍，除非節點有 size 欄位（此時直接 `select(root, size(root) - k + 1)`，O(h)）。面試時優先說反向中序，因為它不需要額外資訊，而且 k 小的時候很快。

> [!question]- F3. 能不能 O(1) 額外空間？
> 用 Morris inorder traversal：沒有左子樹的節點直接輸出並往右；有左子樹時，找它的中序前驅（左子樹的最右節點），若前驅的 `right` 是空的，就把它指向目前節點作為回程線索，再往左；若已經指向目前節點，代表左子樹走完了，把線索清掉、輸出目前節點、往右。每條邊最多走兩次，O(n) 時間、O(1) 空間。找到第 k 個時要注意：如果直接回傳，某些線索還沒還原，樹就被改壞了；比較安全的寫法是記下答案後繼續走完，或接受 O(n) 時間但保證樹結構不變。

> [!question]- F4. 同一棵樹不會修改，但要回答 q 個不同的 k 呢？例如求 BST 的中位數？
> 先做一次中序把值存進陣列，O(n) 時間與空間，之後每個查詢 O(1) 索引。中位數就是 `vals[(n - 1) // 2]`（偶數時再取 `vals[n // 2]` 平均）。若不允許 O(n) 空間，可以用兩次走訪：第一次數出 n，第二次用迭代中序停在第 ⌈n/2⌉ 個；或在每個節點加 size 欄位後每個查詢 O(h)。選哪種取決於 q 的大小與記憶體限制，面試時把這三個選項和它們的取捨講出來。

## 核心題 3｜450. Delete Node in a BST｜Medium

### 題目

給一棵 BST 的根節點 `root` 和一個值 `key`，刪除樹中值為 `key` 的節點（若不存在就什麼都不做），回傳刪除後的根節點（根本身可能被刪掉而換成別的節點）。刪除後必須仍然是合法的 BST。限制：節點數在 0 到 10⁴ 之間，節點值互不相同，值與 key 都在 `-10⁵` 到 `10⁵` 之間。進階要求是時間複雜度 O(h)。

- 範例 1：`root = [5, 3, 6, 2, 4, null, 7]`、`key = 3`，一個合法答案是 `[5, 4, 6, 2, null, null, 7]`（用後繼 4 取代 3）；`[5, 2, 6, null, 4, null, 7]`（用前驅 2 取代）也正確。
- 範例 2：`root = [5, 3, 6, 2, 4, null, 7]`、`key = 0`，0 不存在，回傳原樹。
- 範例 3（邊界）：`root = []`、`key = 0`，回傳 `[]`。
- 範例 4（邊界）：`root = [5]`、`key = 5`，刪掉唯一的節點，回傳 `[]`；`root = [5, null, 6]`、`key = 5`，根被刪掉後新的根是 6。

### 思路

暴力解是把所有值做中序走訪取出，去掉 key，再用剩下的排序值重建一棵（平衡的）BST，O(n)。結果正確，但每次刪除都重建整棵樹，完全沒有利用「只有一個節點要改」這件事。題目要求 O(h)，代表只能沿著一條路徑工作。

第一步是找到節點：用 13.3 節的 `bst_search` 往下走，同時記住父節點，O(h)。接著依照被刪節點有幾個子節點分三種情況。**沒有子節點**：直接把父節點指向它的那條邊改成 None。**只有一個子節點**：讓父節點直接接上這個子節點；子節點的整棵子樹原本就落在被刪節點的區間內，而被刪節點的區間又在父節點那一側，所以接上去仍然合法。**有兩個子節點**：不能隨便拿一個子節點頂上，否則另一棵子樹沒地方放。

兩個子節點的情況，關鍵觀察來自中序定義：刪掉 key 之後，中序序列就是原序列少一個元素，而 key 的位置應該由它在中序中的鄰居接手。中序後繼（successor）是右子樹的最左節點，它比左子樹所有值都大（因為在右子樹裡），又比右子樹其他值都小（因為是最左），所以放在被刪節點的位置完全合法。做法是把後繼的值複製到被刪節點，然後改成刪除後繼節點；後繼是最左節點，**一定沒有左子節點**，所以刪它只會落入前兩種簡單情況。整個過程只走「根到被刪節點」再「到後繼」這一條路徑，O(h)。

```text
刪除 5（兩個子節點）：後繼是右子樹最左的 6

        5                          6
      /   \                      /   \
     3     8         →          3     8
    / \   / \                  / \   / \
   2   4 6   9                2   4 7   9
          \
           7

步驟 1  從根找 key = 5：就是根，parent = None
步驟 2  兩個子節點 → 找後繼：從 8 一路往左到 6（6 沒有左子節點）
步驟 3  把 6 複製到根：根的值變成 6
步驟 4  改成刪除原本的 6（parent = 8）：它只有右子節點 7
        → 8.left = 7

中序：刪除前 2 3 4 5 6 7 8 9
      刪除後 2 3 4 6 7 8 9      （恰好少了 5，仍然遞增）
```

步驟 4 是最容易寫錯的地方：後繼 6 雖然沒有左子節點，但可能有右子節點 7，不能直接把 `8.left` 設成 None，否則 7 就從樹上消失了。用「把父節點的那條邊接到後繼的右子節點」就同時處理了後繼有沒有右子節點兩種情況。

### 解法

```python
import random


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def delete_node(root, key):
    """迭代版本：O(h) 時間、O(1) 額外空間。"""
    parent, node = None, root
    while node is not None and node.val != key:
        parent, node = node, (node.left if key < node.val else node.right)
    if node is None:                         # key 不存在
        return root
    if node.left is not None and node.right is not None:
        succ_parent, succ = node, node.right
        while succ.left is not None:         # 右子樹的最左節點
            succ_parent, succ = succ, succ.left
        node.val = succ.val                  # 用後繼的值覆蓋
        parent, node = succ_parent, succ     # 改成刪除後繼，它沒有左子節點
    child = node.left if node.left is not None else node.right
    if parent is None:                       # 刪的是根
        return child
    if parent.left is node:
        parent.left = child
    else:
        parent.right = child
    return root


def delete_node_rec(root, key):
    """遞迴版本：最好讀，但深度 O(h)，退化的樹要注意遞迴上限。"""
    if root is None:
        return None
    if key < root.val:
        root.left = delete_node_rec(root.left, key)
    elif key > root.val:
        root.right = delete_node_rec(root.right, key)
    else:
        if root.left is None:
            return root.right
        if root.right is None:
            return root.left
        succ = root.right
        while succ.left is not None:
            succ = succ.left
        root.val = succ.val
        root.right = delete_node_rec(root.right, succ.val)
    return root


def insert(root, v):
    if root is None:
        return TreeNode(v)
    node = root
    while True:
        side = "left" if v < node.val else "right"
        if getattr(node, side) is None:
            setattr(node, side, TreeNode(v))
            return root
        node = getattr(node, side)


def inorder(root):
    out, stack, node = [], [], root
    while stack or node:
        while node:
            stack.append(node)
            node = node.left
        node = stack.pop()
        out.append(node.val)
        node = node.right
    return out


def is_bst(root):
    vals = inorder(root)
    return all(a < b for a, b in zip(vals, vals[1:]))


r = None
for v in [5, 3, 6, 2, 4, 7]:
    r = insert(r, v)
r = delete_node(r, 3)
assert inorder(r) == [2, 4, 5, 6, 7] and r.val == 5 and r.left.val == 4
assert inorder(delete_node(r, 0)) == [2, 4, 5, 6, 7]
assert delete_node(None, 0) is None
assert delete_node(TreeNode(5), 5) is None
assert delete_node(TreeNode(5, None, TreeNode(6)), 5).val == 6
r = None
for v in [5, 3, 8, 2, 4, 6, 9, 7]:
    r = insert(r, v)
r = delete_node(r, 5)
assert r.val == 6 and r.right.left.val == 7 and inorder(r) == [2, 3, 4, 6, 7, 8, 9]

for fn in (delete_node, delete_node_rec):
    for _ in range(300):
        vals = random.sample(range(-30, 30), random.randint(0, 20))
        root, alive = None, set(vals)
        for v in vals:
            root = insert(root, v)
        for key in random.choices(range(-32, 32), k=25):
            root = fn(root, key)
            alive.discard(key)
            assert inorder(root) == sorted(alive) and is_bst(root)
print("all tests passed")
```

### 複雜度與邊界

時間 O(h)：找節點走一段路徑，找後繼從被刪節點繼續往下走，兩段加起來不超過樹高。迭代版本額外空間 O(1)，遞迴版本 O(h) 的呼叫深度。邊界情況：空樹直接回傳 None；key 不存在時回傳原根；刪除根節點時 `parent is None`，要回傳新的根（可能是它唯一的子節點，也可能是覆蓋值後的原根）；後繼就是被刪節點的右子節點本身時（右子節點沒有左子節點），`succ_parent` 是被刪節點，要改的是 `succ_parent.right` 而不是 `.left`，程式用 `parent.left is node` 判斷，兩種情況都正確。

### Follow-up

> [!question]- F1. 如果節點除了值還帶著很多資料，或外部有指標指向節點，不能用「複製後繼的值」怎麼辦？
> 改成搬移節點本身：先把後繼從原位置拆下（`succ_parent` 的那條邊接到 `succ.right`），再讓後繼接手被刪節點的左右子節點（`succ.left = node.left`；若後繼不是 `node.right`，則 `succ.right = node.right`），最後把被刪節點的父節點指向後繼。仍然 O(h)，只是多幾條指標要接。這在實作資料庫索引或 `TreeMap` 時是必要的，因為外部的 iterator 或 handle 指向的是節點物件，偷換值會讓它們讀到錯的資料。

> [!question]- F2. 如果要刪除所有落在 [lo, hi] 之外的節點呢（669. Trim a Binary Search Tree）？
> 用遞迴（或後序迭代）一次處理：若 `node.val < lo`，它和整個左子樹都要刪，答案是修剪後的右子樹；若 `node.val > hi`，答案是修剪後的左子樹；否則保留節點、分別修剪左右子樹。每個節點最多處理一次，O(n)；而且被整棵丟掉的子樹完全不會被走訪，實際成本是 O(h + 保留下來的節點數)。和逐一呼叫 450 的 O(k · h) 相比，這種「利用區間一次丟掉整棵子樹」的寫法才是 BST 的正確用法。

> [!question]- F3. 一直用後繼取代被刪節點，樹會不會越來越歪？
> 會。這種刪除叫 Hibbard deletion，大量隨機插入刪除交錯之後，樹會往左偏，平均樹高從 O(log n) 變成約 O(√n)。簡單的緩解方式是隨機選擇用前驅或後繼；真正的解法是自平衡樹（AVL、red-black），它們在刪除後用旋轉恢復平衡，保證 O(log n)。面試中寫出本題的 O(h) 版本即可，但被問到時能指出「O(h) 不等於 O(log n)，而且刪除方式本身會影響 h」，就展現了對 BST 的完整理解。

> [!question]- F4. 如果還要支援插入（701），而且希望 Python 中所有操作都穩定地快，該怎麼選資料結構？
> 插入只要沿著搜尋路徑走到 None 的位置接上新節點，O(h)，和 13.3 節的 `bst_insert` 相同。但 Python 沒有內建平衡 BST，手寫的 BST 遇到排序好的輸入會退化成 O(n)。實務上常見的替代方案是排序 list 加 `bisect.insort`：查詢 O(log n)，插入刪除 O(n) 但底層是 C 的記憶體搬移，n = 10⁵ 時仍然很快；若值域已知，用第 26 章的 Fenwick tree 可以讓插入、刪除、第 k 小、rank 查詢都是 O(log V)。面試時說出這些取捨，比硬寫一棵 red-black tree 更實際。

## 核心題 4｜208. Implement Trie (Prefix Tree)｜Medium

### 題目

實作一個 Trie 類別，支援三個操作：`insert(word)` 把單字加入；`search(word)` 回傳這個單字是否曾被插入；`startsWith(prefix)` 回傳是否有任何已插入的單字以 `prefix` 開頭。限制：單字與前綴長度在 1 到 2000 之間，只含小寫英文字母，三種操作總共最多呼叫 3 × 10⁴ 次。

- 範例 1：依序 `insert("apple")`、`search("apple")` → `True`、`search("app")` → `False`、`startsWith("app")` → `True`、`insert("app")`、`search("app")` → `True`。
- 範例 2：`insert("bat")` 之後，`startsWith("b")` → `True`、`startsWith("bad")` → `False`、`search("ba")` → `False`。
- 範例 3（邊界）：還沒插入任何單字時，`search("a")` 與 `startsWith("a")` 都回傳 `False`。
- 範例 4（邊界）：同一個單字插入兩次不影響結果；`insert("a")` 後 `search("a")` 與 `startsWith("a")` 都是 `True`。

### 思路

最直接的做法是把單字存進 list：`search` 與 `startsWith` 都掃過全部單字，每次 O(N · L)，N 是單字數、L 是長度，3 × 10⁴ 次呼叫、每個單字最長 2000，最差是 10¹² 等級。改用 hash set，`search` 變成 O(L)，但 `startsWith` 仍然要掃過所有單字。若想讓前綴查詢也變成 O(L)，可以把每個單字的所有前綴都放進另一個 set，但長度 L 的單字有 L 個前綴，每個前綴的雜湊要 O(L)，插入一個單字就是 O(L²)，L = 2000 時是 4 × 10⁶，太貴。

瓶頸在於：不同單字、同一個單字的不同前綴之間有大量重複，但 set 把每個字串當成獨立的整體。Trie 把共同前綴合併成同一條路徑：`apple`、`app`、`apt` 共用 `a → p` 這兩個節點。插入時沿著字元往下走，缺節點才建立；查詢時沿著字元往下走，走不下去就代表沒有這個前綴。每個操作都是 O(L)，與 N 無關。

這題要把 13.4 節的兩個 invariant 寫進程式：節點存在代表「有單字以此前綴開頭」，所以 `startsWith` 只看走不走得完；`is_end` 代表「這個前綴本身是單字」，所以 `search` 走完還要檢查它。兩個查詢共用一個 `_walk` 函式，查詢過程中不建立任何節點。

children 的表示方式有兩種常見選擇。dict 只存出現過的字元，Python 中寫起來最短；長度 26 的陣列用 `ord(ch) - ord("a")` 當索引，Java／C++ 的標準寫法，存取是純索引運算，但每個節點都佔 26 格。在 Python 中還有第三種寫法：把所有節點放進一個大陣列，用整數索引代替物件指標，記憶體最省、速度也穩定，難題 3 的 binary trie 就是這種寫法。下面附上 dict 版與陣列池版本。

```text
依序插入 apple、app、apt、bat 之後的 trie（* 表示 is_end）

root
├── a
│   └── p
│       ├── p *              ← "app"
│       │   └── l
│       │       └── e *      ← "apple"
│       └── t *              ← "apt"
└── b
    └── a
        └── t *              ← "bat"

search("ap")       走 a → p，節點存在但沒有 *            → False
startsWith("ap")   走 a → p，節點存在                    → True
search("app")      走 a → p → p，有 *                   → True
search("apx")      走 a → p，沒有 x 這條邊，停下         → False（不建立節點）
startsWith("bad")  走 b → a，沒有 d 這條邊               → False

插入 "app" 時新建的節點數：0（a、p、p 都已存在，只把第二個 p 標上 *）
```

插入 `app` 時沒有新增任何節點，只是把已存在的節點標記為單字結尾，這就是共同前綴被共享的效果：總節點數等於「所有單字的不同前綴」的個數，而不是所有單字長度的總和。

### 解法

```python
import random


class TrieNode:
    __slots__ = ("children", "is_end")

    def __init__(self):
        self.children = {}
        self.is_end = False


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for ch in word:
            nxt = node.children.get(ch)
            if nxt is None:
                nxt = node.children[ch] = TrieNode()
            node = nxt
        node.is_end = True

    def _walk(self, s: str):
        node = self.root
        for ch in s:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def search(self, word: str) -> bool:
        node = self._walk(word)
        return node is not None and node.is_end

    def startsWith(self, prefix: str) -> bool:
        return self._walk(prefix) is not None


class ArrayTrie:
    """節點池版本：nxt[v][c] 是子節點索引，0 表示沒有（根是 0，不會是子節點）。"""

    def __init__(self):
        self.nxt = [[0] * 26]
        self.end = [False]

    def insert(self, word: str) -> None:
        v = 0
        for ch in word:
            c = ord(ch) - 97
            if not self.nxt[v][c]:
                self.nxt[v][c] = len(self.nxt)
                self.nxt.append([0] * 26)
                self.end.append(False)
            v = self.nxt[v][c]
        self.end[v] = True

    def _walk(self, s: str) -> int:
        v = 0
        for ch in s:
            v = self.nxt[v][ord(ch) - 97]
            if not v:
                return -1
        return v

    def search(self, word: str) -> bool:
        v = self._walk(word)
        return v != -1 and self.end[v]

    def startsWith(self, prefix: str) -> bool:
        return self._walk(prefix) != -1


for cls in (Trie, ArrayTrie):
    t = cls()
    assert not t.search("a") and not t.startsWith("a")
    t.insert("apple")
    assert t.search("apple") and not t.search("app") and t.startsWith("app")
    t.insert("app")
    assert t.search("app")
    t.insert("bat")
    assert t.startsWith("b") and not t.startsWith("bad") and not t.search("ba")
    t.insert("bat")
    assert t.search("bat")
    long_word = "z" * 2000
    t.insert(long_word)
    assert t.search(long_word) and not t.search(long_word[:-1]) and t.startsWith(long_word[:-1])

    for _ in range(100):
        t, words = cls(), set()
        for _ in range(60):
            s = "".join(random.choice("abc") for _ in range(random.randint(1, 5)))
            op = random.randrange(3)
            if op == 0:
                t.insert(s)
                words.add(s)
            elif op == 1:
                assert t.search(s) == (s in words)
            else:
                assert t.startsWith(s) == any(w.startswith(s) for w in words)
print("all tests passed")
```

### 複雜度與邊界

每個操作時間 O(L)，L 是參數字串的長度。空間是所有已插入單字的不同前綴數 P，最差是總字元數 O(ΣL)：dict 版本每個節點的成本和子節點數成正比，陣列版本每個節點固定 26 格，總共 O(26 · P)。邊界情況：空 trie 的查詢都回傳 False；重複插入只是重設 `is_end`，不會新增節點；`search` 遇到「是前綴但不是單字」必須回傳 False；長度 2000 的單字用迭代不會有遞迴深度問題；查詢失敗時不能留下新節點。

### Follow-up

> [!question]- F1. 如果要支援 erase(word)，以及「有幾個單字等於 word」「有幾個單字以 prefix 開頭」（1804. Implement Trie II）呢？
> 每個節點存兩個計數：`pass_count`（有幾個已插入的單字經過這個節點）與 `end_count`（有幾個單字在這裡結束）。插入時沿路 `pass_count += 1`、終點 `end_count += 1`；`countWordsEqualTo` 回傳終點的 `end_count`，`countWordsStartingWith` 回傳前綴終點的 `pass_count`；`erase` 先確認 `end_count > 0`，再沿路減一，若某個子節點的 `pass_count` 變成 0 就把整個分支從父節點刪掉，避免留下沒用的節點。所有操作仍然 O(L)。
> ```python
> class CountingTrie:
>     def __init__(self):
>         self.root = {"pass": 0, "end": 0, "kids": {}}
>
>     def insert(self, w):
>         node = self.root
>         node["pass"] += 1
>         for ch in w:
>             node = node["kids"].setdefault(ch, {"pass": 0, "end": 0, "kids": {}})
>             node["pass"] += 1
>         node["end"] += 1
>
>     def erase(self, w):                       # 呼叫前確認 w 存在
>         node = self.root
>         node["pass"] -= 1
>         for ch in w:
>             child = node["kids"][ch]
>             child["pass"] -= 1
>             if child["pass"] == 0:
>                 del node["kids"][ch]          # 整個分支已無單字，直接剪掉
>                 return
>             node = child
>         node["end"] -= 1
> ```

> [!question]- F2. 字母集很大（例如 Unicode）或記憶體很緊時，trie 要怎麼省空間？
> 第一步是不用固定長度陣列，改用 dict 或排序的 (字元, 子節點) 串列，只存實際出現的邊。第二步是壓縮只有一個子節點的鏈：把連續的單一路徑合併成一條標記為字串的邊，這叫 radix tree（或 compressed trie、Patricia trie），節點數從 O(總字元數) 降到 O(單字數)，因為每個內部節點至少有兩個子節點。查詢時沿著邊比對整段字串，複雜度仍是 O(L)。若字典是靜態的，還可以用 DAWG 或 double-array trie 進一步共享後綴、壓縮成連續陣列，這是輸入法與拼字檢查器常見的做法。

> [!question]- F3. 如果要做自動完成：每輸入一個字元，就回傳以目前前綴開頭、字典序最小的三個單字呢（1268. Search Suggestions System）？
> 做法一：在 trie 的每個節點存「經過這裡的字典序最小三個單字」。先把單字排序後依序插入，每個節點只在清單不滿三個時加入，這樣清單自然就是最小的三個；查詢時沿著輸入走一步就直接回傳那個節點的清單，每個字元 O(1)。預處理 O(ΣL)，額外空間 O(3 · 節點數)。做法二：不建 trie，把單字排序後，每個前綴用 `bisect_left` 找到第一個 ≥ 前綴的位置，往後取三個並檢查是否以前綴開頭，每個字元 O(L log N)。若排序依據改成熱門度（642. Design Search Autocomplete System），就在每個節點存 top-k 的 heap 或在查詢時 DFS 子樹再取 top-k。

> [!question]- F4. 如果單字是逐字元串流進來，要在每個字元到達時回報「目前輸入的最後幾個字元是否構成某個字典單字」呢（1032. Stream of Characters）？
> 把字典中每個單字**反轉**後插入 trie，並保留最近的最多 L_max 個字元（L_max 是最長單字的長度）。每來一個字元，就從最新的字元往回讀，沿著反轉的 trie 往下走，只要途中遇到 `is_end` 就回傳 True，走不下去就回傳 False。每次查詢 O(L_max)，與字典大小無關。反轉的理由是：我們要比對的是「以目前位置結尾」的字串，從最後一個字元往回走才能共用前綴；若要做到每個字元攤銷 O(1)，就要用 Aho-Corasick automaton（在 trie 上加 failure link）。

## 核心題 5｜211. Design Add and Search Words Data Structure｜Medium

### 題目

設計一個資料結構 `WordDictionary`，支援 `addWord(word)` 加入一個單字，以及 `search(word)` 判斷是否有任何已加入的單字能與 `word` 配對。`search` 的參數可以包含 `.`，它能配對任何一個字母；其他字元必須完全相同，而且長度要相等。限制：單字長度 1 到 25，`addWord` 的單字只含小寫字母，`search` 的參數含小寫字母或 `.`，且每個查詢**最多有 2 個 `.`**；兩種操作總共最多 10⁴ 次。

- 範例 1：加入 `bad`、`dad`、`mad` 之後，`search("pad")` → `False`、`search("bad")` → `True`、`search(".ad")` → `True`、`search("b..")` → `True`。
- 範例 2：同樣的字典，`search("b.")` → `False`（長度不符）、`search("...")` → `True`、`search("....")` → `False`。
- 範例 3（邊界）：空字典時任何查詢都回傳 `False`。
- 範例 4（邊界）：加入 `a` 之後，`search(".")` → `True`、`search("a.")` → `False`。

### 思路

暴力解是把單字存進 list，每次查詢掃過全部單字，逐字元比對（`.` 永遠相符），O(N · L)。10⁴ 次操作中如果一半是加入、一半是查詢，最差約 5000 × 5000 × 25 ≈ 6 × 10⁸ 次字元比較，太慢。hash set 只能處理沒有 `.` 的查詢；有 `.` 時可以把所有 26 種替換都試一遍（最多兩個 `.`，就是 26² = 676 次 set 查詢，每次 O(L)），這其實可行，但它依賴「最多兩個點」這個限制，`.` 一多就爆炸成 26^d。

Trie 讓普通字元和 `.` 都能自然處理：普通字元只走一條邊；`.` 則要嘗試目前節點的**所有**子節點，這就是一個 DFS（或 backtracking）。關鍵在於分岔只發生在 `.` 的位置，而且只會走進「真的有單字經過」的子節點，不像 26 種替換那樣盲目嘗試不存在的字元。走到查詢字串結尾時，還要檢查這個節點是否是某個單字的結尾，因為長度也要相符。

Invariant 是：DFS 的狀態 `(node, i)` 代表「已經用查詢的前 i 個字元走到 node」，也就是 node 代表的前綴與查詢的前 i 個字元相符。從這個狀態出發，若 `word[i]` 是字母就只轉移到那個子節點；若是 `.` 就轉移到每個子節點；`i == len(word)` 時答案是 `node` 是否為單字結尾。只要有任何一條路徑成功就回傳 True，所以可以提早結束。

這裡改用 dict 套 dict 的寫法：每個節點本身就是一個 dict，key 是字元，另外用一個特殊 key `"$"` 標記單字結尾。這種寫法在 Python 面試中很常見，比定義 class 更短；代價是走訪子節點時要跳過 `"$"`。

```text
字典：bad、dad、mad

root
├── b ── a ── d $
├── d ── a ── d $
└── m ── a ── d $

search(".ad")：
(root, 0) 字元 '.' → 分岔到 b、d、m 三個子節點
  (b, 1) 字元 'a' → (ba, 2) 字元 'd' → (bad, 3) 結尾，有 $ → True，提早結束

search("b.."):
(root, 0) 'b' → (b, 1) '.' → 只有 a 一個子節點 → (ba, 2) '.' → 只有 d → (bad, 3) 有 $ → True

search("b.")：
(root, 0) 'b' → (b, 1) '.' → (ba, 2) 已到結尾，ba 沒有 $ → 這條失敗；沒有其他分支 → False

search("pad")：
(root, 0) 'p' → root 沒有 p 這條邊 → 立刻 False
```

`search(".ad")` 雖然第一個字元就分岔成三條路，但走進 `b` 之後就沒有再分岔，第一條路成功就停下。`search("b.")` 說明了為什麼結尾要檢查 `$`：`ba` 是一個存在的前綴，但不是任何單字，長度 2 的查詢不能配對長度 3 的單字。

### 解法

```python
import random


class WordDictionary:
    def __init__(self):
        self.root = {}

    def addWord(self, word: str) -> None:
        node = self.root
        for ch in word:
            node = node.setdefault(ch, {})   # 加入時建立節點是正確的
        node["$"] = True

    def search(self, word: str) -> bool:
        stack = [(self.root, 0)]             # (節點, 已比對的字元數)
        while stack:
            node, i = stack.pop()
            if i == len(word):
                if "$" in node:
                    return True
                continue
            ch = word[i]
            if ch == ".":
                for key, child in node.items():
                    if key != "$":
                        stack.append((child, i + 1))
            else:
                child = node.get(ch)         # 查詢時不建立節點
                if child is not None:
                    stack.append((child, i + 1))
        return False


def brute(words, q):
    return any(len(w) == len(q) and all(c == "." or c == d for c, d in zip(q, w)) for w in words)


d = WordDictionary()
assert not d.search("a") and not d.search(".")
for w in ["bad", "dad", "mad"]:
    d.addWord(w)
assert not d.search("pad") and d.search("bad") and d.search(".ad") and d.search("b..")
assert not d.search("b.") and d.search("...") and not d.search("....")
d2 = WordDictionary()
d2.addWord("a")
assert d2.search(".") and not d2.search("a.") and not d2.search("")
for _ in range(200):
    d, words = WordDictionary(), []
    for _ in range(40):
        if random.random() < 0.5:
            w = "".join(random.choice("abc") for _ in range(random.randint(1, 4)))
            d.addWord(w)
            words.append(w)
        else:
            q = "".join(random.choice("abc.") for _ in range(random.randint(1, 4)))
            assert d.search(q) == brute(words, q)
print("all tests passed")
```

### 複雜度與邊界

`addWord` 是 O(L)。`search` 沒有 `.` 時是 O(L)；有 d 個 `.` 時，每個 `.` 最多分岔成 26 條，最差 O(26^d · L)，但實際上只會走進存在的節點，所以也不超過 trie 的總節點數。在「最多兩個 `.`」的限制下，每次查詢最多 26² · 25 ≈ 1.7 × 10⁴ 步。空間是 trie 的節點數 O(ΣL)，DFS stack 最多 O(26 · L)。邊界情況：空字典時根是空 dict，任何查詢都失敗；查詢比所有單字都長或都短時，在結尾檢查 `$` 會失敗；`"$"` 不能被當成子節點走進去，所以展開 `.` 時要跳過它。

### Follow-up

> [!question]- F1. 如果 `.` 的數量沒有限制，最壞情況是什麼？有沒有更好的做法？
> 全部是 `.` 的查詢，例如長度 25 的 `"....."`，DFS 會走遍 trie 中深度 ≤ 25 的所有節點，O(節點數)，但它只是在問「有沒有長度 25 的單字」。一個有效的優化是另外維護 `by_len[L]` 的單字集合（或每個節點存「子樹中單字的長度集合」），查詢前先檢查長度是否存在，並在 DFS 中剪掉「剩下的長度不可能配對」的分支。若查詢中的 `.` 很多而字母很少，另一種思路是把單字依長度分桶，對每個非 `.` 的位置建立 `(位置, 字母) → 單字 id 集合` 的索引，查詢時取這些集合的交集，成本取決於最小的那個集合。

> [!question]- F2. 如果再加一個萬用字元 `*`，代表任意長度（包含 0）的任意字串呢？
> DFS 的狀態仍然是 `(node, i)`，但 `*` 有兩種轉移：吃掉 0 個字元（`(node, i + 1)`），或吃掉一個字元並留在 `*`（對每個子節點 `(child, i)`）。因為同一個狀態可能被多條路徑抵達，要用 `visited` 集合記住已經處理過的 `(id(node), i)`，否則會指數爆炸；加上記憶化後，每個狀態最多處理一次，O(節點數 × 查詢長度)。這和第 22 章難題 2（44. Wildcard Matching）是同一個 DP，只是把「另一個字串」換成了整棵 trie。

> [!question]- F3. 如果 search 要回傳「有幾個單字能配對」，而不是 True／False 呢？
> 不能在第一個成功時就停下，DFS 要走完所有分支，把每個終點的單字數加總；若同一個單字可能重複加入，就在終點存計數而不是布林值。成本是所有可行路徑的節點數，最差仍是 O(26^d · L)。一個常見優化是：當查詢剩下的部分全部是 `.` 時，答案等於「這個節點子樹中，深度剛好是剩餘長度的單字數」，若每個節點預先存好 `count_by_depth`（一個長度 ≤ 25 的陣列，插入時沿路更新），就能直接 O(1) 回答這段，不用繼續展開。

## 難題 1｜212. Word Search II｜Hard

### 題目

給一個 m × n 的字元網格 `board` 和一串單字 `words`，回傳所有能在網格中找到的單字。一個單字「能被找到」的意思是：存在一條由相鄰格子（上下左右）組成的路徑，依序讀出的字母恰好是這個單字，而且同一個單字的路徑中每個格子最多使用一次。回傳順序不限，每個單字最多出現一次。限制：`1 <= m, n <= 12`，網格與單字都只含小寫字母，`1 <= len(words) <= 3 × 10⁴`，單字長度 1 到 10，單字互不相同。

- 範例 1：`board = [["o","a","a","n"],["e","t","a","e"],["i","h","k","r"],["i","f","l","v"]]`、`words = ["oath","pea","eat","rain"]`，回傳 `["eat","oath"]`。
- 範例 2：`board = [["a","b"],["c","d"]]`、`words = ["abcb"]`，回傳 `[]`；`a → b → ?`，b 的鄰居沒有 c，而且 b 不能用兩次。
- 範例 3（邊界）：`board = [["a"]]`、`words = ["a", "aa"]`，回傳 `["a"]`；`aa` 需要同一格用兩次。
- 範例 4（邊界）：`board = [["a","b"],["d","c"]]`、`words = ["abcd", "acdb", "ab"]`，回傳 `["abcd", "ab"]`（順序不限）；`acdb` 的 a 和 c 不相鄰。

### 提示

> [!tip]- 提示 1
> 對每個單字各做一次第 19 章核心題 5（79. Word Search）的 backtracking，會在網格上重複走同樣的前綴。很多單字共用前綴時，能不能一次走就同時推進所有單字？

> [!tip]- 提示 2
> 把所有單字建成 trie。從每個格子出發做 DFS 時，同時在 trie 上往下走：目前路徑讀出的字串如果不是任何單字的前綴，trie 上就沒有對應的節點，這條路立刻剪掉。

> [!tip]- 提示 3
> 在單字的終點節點存整個單字，找到時把它取出（避免重複加入）；DFS 回溯時若某個 trie 節點已經沒有子節點也沒有單字，就把它從父節點刪掉，之後的搜尋不會再走進這個死掉的分支。

### 詳解

**為什麼直覺做法不夠**。對每個單字跑一次 79 題：從每個格子出發 DFS，每一步最多三個方向（不能走回頭），一個單字最差 O(mn · 4 · 3^(L−1))。3 × 10⁴ 個單字、mn = 144、L = 10，最差是 3 × 10⁴ × 144 × 4 × 3⁹，遠超時限。更根本的浪費是：`oath`、`oats`、`oak` 在網格上從同一個 `o` 出發，前兩步完全相同，但每個單字都各自重走一遍。

**突破點：DFS 的狀態同時是「網格位置」與「trie 節點」**。把單字建成 trie 之後，從格子 (r, c) 出發的 DFS 帶著一個 trie 節點：目前路徑讀出的字串，就是這個節點代表的前綴。走到鄰居 (nr, nc) 時，只有當 trie 節點有 `board[nr][nc]` 這個子節點才繼續，否則這條路徑不是任何單字的前綴，整棵 DFS 子樹都可以丟掉。於是一次 DFS 同時推進所有共用這個前綴的單字，而不是每個單字各走一遍。遇到節點上存著單字，就把它加入答案。

**兩個關鍵優化**。第一，**找到就移除**：把終點節點上的單字取出（`node.pop("$")`），同一個單字就不會被不同路徑重複加入，不需要額外的 set 去重。第二，**剪掉死分支**：DFS 回溯到某個節點時，若它已經沒有子節點、也沒有單字，代表這個前綴底下的所有單字都已經找到，把它從父節點的 children 中刪除。這個剪枝在「網格很大、很多單字共享前綴、而且大部分都能找到」時效果非常明顯：例如網格全是 `a`、單字是 `a`、`aa`、…、`aaaaaaaaaa`，第一次 DFS 就會把十個單字全部找到，之後整棵 trie 被剪光，其餘 143 個起點一步都不用走。

**正確性**。每條從某格出發、不重複使用格子的路徑，只要它讀出的字串是某個單字的前綴，就會被 DFS 走到（因為 trie 中有對應節點），所以每個能被找到的單字都會在它的某條路徑終點被加入答案。剪枝只刪除「子樹中已經沒有未找到單字」的節點，不會影響任何還沒找到的單字。用 `"#"` 暫時覆蓋目前路徑上的格子來標記「已使用」，回溯時還原，保證同一條路徑不重複用格子；不同路徑之間可以重用格子，因為還原後網格回到原狀。

```text
board：         words = [oath, pea, eat, rain] 建成的 trie
  o a a n       root
  e t a e       ├── o ─ a ─ t ─ h $oath
  i h k r       ├── p ─ e ─ a $pea
  i f l v       ├── e ─ a ─ t $eat
                └── r ─ a ─ i ─ n $rain

從 (0,0) 'o' 出發，trie 走到 o：
(0,0) o → 鄰居 (0,1) a：o 有子節點 a ✓ → 走到 oa
          鄰居 (1,0) e：o 沒有子節點 e ✗ 剪掉
(0,1) a → 鄰居 (1,1) t：oa 有 t ✓ → oat
          鄰居 (0,2) a：oa 沒有 a ✗
(1,1) t → 鄰居 (2,1) h：oat 有 h ✓ → oath，取出 "oath" 加入答案
          oath 節點變空 → 回溯時從 oat 刪掉 h → oat 變空 → 從 oa 刪掉 t → … → 整條 o 分支刪除

從 (1,0) 'e' 出發：e → (1,1) t？trie 的 e 只有 a ✗；(2,0) i ✗；(0,0) o ✗ → 結束
從 (1,3) 'e' 出發：e → (0,3) n ✗；(1,2) a ✓ → ea → (1,1) t ✓ → eat，取出 "eat"
起點 'p'、'r'：網格中沒有 p；(2,3) 的 r 鄰居是 e、v、k，沒有 a → rain、pea 都找不到
```

找到 `oath` 之後，`o` 分支整條被剪掉，之後任何以 `o` 開頭的起點都會在第一步就被 `board[r][c] in root` 擋下。這說明了剪枝的效果：找過的單字不會讓後面的搜尋變慢。

### 解法

```python
import random


def find_words(board: list[list[str]], words: list[str]) -> list[str]:
    root = {}
    for w in words:
        node = root
        for ch in w:
            node = node.setdefault(ch, {})
        node["$"] = w                        # 終點存整個單字

    m, n = len(board), len(board[0])
    found = []

    def dfs(r: int, c: int, parent: dict) -> None:
        ch = board[r][c]
        node = parent[ch]
        word = node.pop("$", None)           # 找到就取出，避免重複
        if word is not None:
            found.append(word)
        board[r][c] = "#"                    # 標記目前路徑已使用
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < m and 0 <= nc < n and board[nr][nc] in node:
                dfs(nr, nc, node)
        board[r][c] = ch                     # 回溯還原
        if not node:                         # 子樹已經沒有單字：剪掉
            del parent[ch]

    for r in range(m):
        for c in range(n):
            if board[r][c] in root:
                dfs(r, c, root)
    return found


def brute(board, words):
    m, n = len(board), len(board[0])

    def exist(w):
        def go(r, c, i, used):
            if board[r][c] != w[i]:
                return False
            if i == len(w) - 1:
                return True
            used.add((r, c))
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < m and 0 <= nc < n and (nr, nc) not in used and go(nr, nc, i + 1, used):
                    used.discard((r, c))
                    return True
            used.discard((r, c))
            return False
        return any(go(r, c, 0, set()) for r in range(m) for c in range(n))
    return [w for w in words if exist(w)]


b1 = [list("oaan"), list("etae"), list("ihkr"), list("iflv")]
assert sorted(find_words([row[:] for row in b1], ["oath", "pea", "eat", "rain"])) == ["eat", "oath"]
assert find_words([list("ab"), list("cd")], ["abcb"]) == []
assert find_words([["a"]], ["a", "aa"]) == ["a"]
assert sorted(find_words([list("ab"), list("dc")], ["abcd", "acdb", "ab"])) == ["ab", "abcd"]
big = [["a"] * 12 for _ in range(12)]
assert sorted(find_words(big, ["a" * k for k in range(1, 11)] + ["b"])) == sorted("a" * k for k in range(1, 11))
for _ in range(300):
    m, n = random.randint(1, 4), random.randint(1, 4)
    board = [[random.choice("abc") for _ in range(n)] for _ in range(m)]
    words = list({"".join(random.choice("abc") for _ in range(random.randint(1, 6))) for _ in range(10)})
    copy = [row[:] for row in board]
    assert sorted(find_words(copy, words)) == sorted(brute(board, words))
    assert copy == board                     # 網格必須被還原
print("all tests passed")
```

### 複雜度與邊界

建 trie 是 O(ΣL)。搜尋的最差時間是 O(mn · 4 · 3^(L_max − 1))：每個起點的 DFS 最多走到深度 L_max = 10，第一步四個方向、之後每步最多三個方向；trie 剪枝讓實際成本遠低於這個上界，而且和單字數量 W 無關，這正是它比「每個單字各跑一次」好的地方。空間是 trie 的 O(ΣL) 加上遞迴深度 O(L_max)。邊界情況：網格只有一格時，長度 ≥ 2 的單字都找不到；同一個單字可能有多條路徑，取出 `$` 保證只加入一次；DFS 期間用 `"#"` 覆蓋格子，它不是任何 trie 的 key，所以不會被誤走；函式會暫時修改 `board`，結束時已全部還原，若呼叫者不允許修改輸入，也可以改用 `visited` 集合。

### Follow-up

> [!question]- F1. 如果同一個格子在一個單字中可以重複使用呢？
> 不再需要「已使用」的標記，但 DFS 可能在兩個格子之間來回走，必須避免重複狀態。此時狀態是 `(格子, trie 節點)`，總數最多 mn × 節點數，可以用 BFS 或帶 visited 的 DFS 走遍所有可到達的狀態，遇到有單字的節點就記錄。時間 O(mn · 節點數 · 4)，是多項式而不是指數，因為「不重複使用格子」這個限制才是原題需要 backtracking 的原因。這個對比值得在面試中說出來：限制改變，演算法的本質也改變了。

> [!question]- F2. 如果改成八個方向（Boggle 遊戲），而且同一本字典要對很多個不同的網格查詢呢？
> 八方向只改鄰居清單，最差分支數從 3 變成 7，上界變成 O(mn · 8 · 7^(L−1))，trie 剪枝更加重要。字典固定、網格很多時，trie 應該只建一次；但本題的「找到就刪除節點」會破壞 trie，所以要改成不刪除的版本：用一個 `found` set 去重，或在節點上記錄「最後一次被找到的網格編號」，每個新網格開始時不需要重建 trie。若還需要剪枝，可以在節點上維護「子樹中這一輪尚未找到的單字數」，每輪開始時重設。

> [!question]- F3. 如果單字很少（例如只有一兩個）但很長，還值得建 trie 嗎？
> 單字很少時 trie 退化成一兩條鏈，和直接跑 79 題差不多，建 trie 只是多了常數成本。此時更有效的優化是 79 題的剪枝：先統計網格中每個字母的數量，若單字需要的某個字母比網格中的還多就直接跳過；若單字最後一個字母在網格中比第一個字母更稀少，就把單字反轉再搜尋，讓分岔在一開始就被限制住。trie 的價值在於「很多單字共享前綴」，面試時能說出這個適用條件，比無條件地套 trie 更好。

> [!question]- F4. 如果要回傳每個找到的單字對應的一條路徑（格子座標序列）呢？
> DFS 時維護一個 `path` 串列，進入格子時 `append((r, c))`、回溯時 `pop()`；找到單字時把 `path[:]` 存起來。因為每個單字只會被記錄一次（取出 `$` 後就不會再遇到），複製路徑的總成本是 O(ΣL)，不影響整體複雜度。若要回傳**所有**路徑，就不能取出 `$`，也不能剪枝，輸出量本身可能是指數級，這時要先和面試官確認輸出規模。

### 心得

關鍵突破是讓 DFS 同時走在網格與 trie 上，一次搜尋推進所有共用前綴的單字，「不是任何單字的前綴」立刻剪枝。它是第 19 章核心題 5（79）的 backtracking 加上本章核心題 4 的 trie：79 題決定怎麼在網格上走，trie 決定哪些路值得走。面試時先說「每個單字各跑一次 79」的成本與重複之處，再提出 trie，最後主動補上兩個優化：找到就取出單字（去重）、回溯時刪除空節點（剪枝），並說明它們為什麼不影響正確性。很多候選人寫得出 trie + DFS，但能說清楚剪枝為什麼安全，才是 L5 的水準。

## 難題 2｜745. Prefix and Suffix Search｜Hard

### 題目

設計一個類別 `WordFilter`：建構時給一串單字 `words`；之後呼叫 `f(pref, suff)`，回傳**同時**以 `pref` 開頭、以 `suff` 結尾的單字中，索引最大的那一個的索引；沒有這樣的單字就回傳 -1。限制：`1 <= len(words) <= 10⁴`，單字長度 1 到 7，`pref` 與 `suff` 長度 1 到 7，全部是小寫字母；`f` 最多被呼叫 10⁴ 次。

- 範例 1：`words = ["apple"]`，`f("a", "e")` → `0`。
- 範例 2：`words = ["apple", "apply", "ape"]`，`f("ap", "e")` → `2`（`apple` 與 `ape` 都符合，取較大的索引 2）；`f("app", "y")` → `1`；`f("b", "e")` → `-1`。
- 範例 3（邊界）：`words = ["apple"]`，`f("apple", "apple")` → `0`，前綴與後綴都可以是整個單字，而且可以重疊。
- 範例 4（邊界）：`words = ["abc", "abc"]`，`f("a", "c")` → `1`，重複的單字取最後一個。

### 提示

> [!tip]- 提示 1
> 一棵前綴 trie 能找到所有以 `pref` 開頭的單字，一棵後綴 trie（插入反轉的單字）能找到所有以 `suff` 結尾的單字。但兩個集合取交集，最差要 O(N)。能不能讓**一次** trie 查詢同時檢查前綴與後綴？

> [!tip]- 提示 2
> 把兩個條件拼成一個字串：對單字 `apple` 的每個後綴 s，插入 `s + "{" + "apple"`。查詢時走 `suff + "{" + pref`：走得完就代表某個單字以 suff 結尾、而且以 pref 開頭。

> [!tip]- 提示 3
> 單字長度只有 7，所以每個單字只插入 8 個字串、每個長度不超過 15。在每個經過的節點記錄「目前經過這裡的最大索引」，因為單字依索引遞增插入，後插入的直接覆蓋即可。查詢只需 O(|pref| + |suff|)。

### 詳解

**為什麼直覺做法不夠**。最直接的是每次查詢掃過所有單字，從後往前找第一個 `startswith(pref) and endswith(suff)` 的，O(N · L)，10⁴ 次查詢乘上 10⁴ 個單字是 10⁸ 次字串比較，太慢。兩棵 trie 的做法：前綴 trie 的節點存「以這個前綴開頭的所有索引」，後綴 trie 同理，查詢時取兩個集合的交集中的最大值；但像 `pref = "a"`、`suff = "e"` 這種很常見的條件，兩個集合都可能有幾千個元素，交集仍然是 O(N)。問題在於兩個條件被分開索引，查詢時才合併。

**突破點：把兩個條件編碼成一個前綴**。想要的是一個字串 key，使得「單字 w 同時滿足 pref 與 suff」⇔「某個為 w 插入的 key 以 `suff + "{" + pref` 開頭」。取 key = `w 的某個後綴 + "{" + w`：若 w 以 suff 結尾，就存在一個後綴恰好等於 suff，對應的 key 以 `suff + "{"` 開頭，後面接著完整的 w；而 w 以 pref 開頭 ⇔ 這個 key 在 `"{"` 之後以 pref 開頭。反過來，若 key 以 `suff + "{" + pref` 開頭，因為 `"{"` 不是小寫字母，`"{"` 前面的部分一定恰好是 w 的那個後綴（不可能有字母跨過分隔符），所以它等於 suff，而 `"{"` 之後的 w 以 pref 開頭。分隔符的作用就是讓「後綴在哪裡結束」不會有歧義。

**最大索引**。依索引由小到大處理單字，對每個插入的 key，沿路每個節點都設成目前的索引。因為後處理的索引比較大，覆蓋之後每個節點存的就是「經過這個節點的所有 key 中，最大的單字索引」。查詢走到 `suff + "{" + pref` 的終點，節點上的值就是答案。

**空間與另一種做法**。每個長度 L 的單字插入 L + 1 個 key（後綴包含空字串與整個單字），每個 key 長度不超過 2L + 1，所以每個單字最多新增約 1.5L² 個節點，L = 7 時大約 90 個，10⁴ 個單字最多約 10⁶ 個節點。另一種同樣正確的做法是直接用 hash map：對每個單字列舉所有 (前綴, 後綴) 組合當 key，共 (L + 1)² = 64 組，後寫入的索引覆蓋先前的值，查詢 O(1) 個 hash 操作。兩者的時間都是建構 O(N · L²)、查詢 O(L)；在 Python 中 hash map 版本更短、物件更少，trie 版本則是這題想考的「把多個條件串成一個前綴」的技巧，兩者都值得會。

```text
words = ["apple"]（索引 0），插入的 6 個 key：
後綴 ""      → "{apple"
後綴 "e"     → "e{apple"
後綴 "le"    → "le{apple"
後綴 "ple"   → "ple{apple"
後綴 "pple"  → "pple{apple"
後綴 "apple" → "apple{apple"

查詢 f("ap", "le") → 走 "le{ap"：
root ─ l ─ e ─ { ─ a ─ p      全部存在，節點上的索引 = 0 → 回傳 0

查詢 f("ap", "x") → 走 "x{ap"：root 沒有 x 這條邊 → 回傳 -1

words = ["apple", "apply", "ape"]，查詢 f("ap", "e") → 走 "e{ap"
"e{apple" 經過 e{ap 時把索引設成 0
"e{ape"   經過 e{ap 時把索引覆蓋成 2     → 回傳 2
（"apply" 的後綴 key 都以 y、ly、… 開頭，不會經過 e{）
```

查詢 `f("ap", "le")` 時，`le{` 這一段確認了 `apple` 以 `le` 結尾，`{` 之後的 `ap` 確認了它以 `ap` 開頭，一次 trie 走訪就同時驗證了兩個條件。第三個例子說明了「後插入的索引覆蓋」如何得到最大索引。

### 解法

```python
import random


class WordFilter:
    def __init__(self, words: list[str]):
        self.root = {}
        for idx, w in enumerate(words):
            for i in range(len(w) + 1):          # 後綴 w[i:]，包含整個單字與空字串
                node = self.root
                for ch in w[i:] + "{" + w:
                    node = node.setdefault(ch, {})
                    node["#"] = idx              # 後插入的索引較大，直接覆蓋

    def f(self, pref: str, suff: str) -> int:
        node = self.root
        for ch in suff + "{" + pref:
            node = node.get(ch)
            if node is None:
                return -1
        return node.get("#", -1)


class WordFilterHash:
    def __init__(self, words: list[str]):
        self.best = {}
        for idx, w in enumerate(words):
            for i in range(len(w) + 1):
                for j in range(len(w) + 1):
                    self.best[(w[:i], w[j:])] = idx

    def f(self, pref: str, suff: str) -> int:
        return self.best.get((pref, suff), -1)


def brute(words, pref, suff):
    for i in range(len(words) - 1, -1, -1):
        if words[i].startswith(pref) and words[i].endswith(suff):
            return i
    return -1


for cls in (WordFilter, WordFilterHash):
    assert cls(["apple"]).f("a", "e") == 0
    wf = cls(["apple", "apply", "ape"])
    assert wf.f("ap", "e") == 2 and wf.f("app", "y") == 1 and wf.f("b", "e") == -1
    assert cls(["apple"]).f("apple", "apple") == 0
    assert cls(["apple"]).f("apple", "xapple") == -1     # 後綴比單字還長
    assert cls(["abc", "abc"]).f("a", "c") == 1
    for _ in range(200):
        words = ["".join(random.choice("ab") for _ in range(random.randint(1, 5))) for _ in range(12)]
        wf = cls(words)
        for _ in range(30):
            p = "".join(random.choice("ab") for _ in range(random.randint(1, 4)))
            s = "".join(random.choice("ab") for _ in range(random.randint(1, 4)))
            assert wf.f(p, s) == brute(words, p, s)
big = ["".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(7)) for _ in range(3000)]
wf = WordFilter(big)
assert wf.f(big[-1][:3], big[-1][-3:]) == len(big) - 1
print("all tests passed")
```

### 複雜度與邊界

建構時間 O(N · L²)：每個單字插入 L + 1 個長度 O(L) 的 key；trie 節點數也是 O(N · L²)，hash 版本有 N · (L + 1)² 個 key。查詢時間 O(|pref| + |suff|)。在 L = 7、N = 10⁴ 的限制下，兩種版本都只做約 10⁶ 次基本操作。邊界情況：前綴與後綴可以重疊、也可以是整個單字，因為 key 的 `"{"` 之後放的是完整單字，不是「去掉後綴的剩餘部分」；後綴比單字長時，不會有任何 key 以它加 `"{"` 開頭，正確回傳 -1；重複的單字由後插入的覆蓋，自然得到最大索引；分隔符必須是不會出現在單字中的字元，`"{"` 剛好是 ASCII 中 `z` 的下一個字元，在 26 格陣列的實作中可以用第 27 格表示。

### Follow-up

> [!question]- F1. 如果單字很長（例如 L = 1000），但單字數與查詢數不多呢？
> 組合 key 的方法每個單字要 O(L²) = 10⁶ 個節點，不再可行。改成兩棵 trie：前綴 trie 的每個節點存「經過的單字索引」的排序串列，後綴 trie（插入反轉的單字）也一樣。查詢時取出兩個排序串列，從尾端開始用 two pointers 找最大的共同索引，O(兩串列長度)。另一種做法是只建前綴 trie，從節點的索引串列尾端往前逐一檢查 `words[i].endswith(suff)`，第一個成功的就是答案，在多數資料上很快，但最差 O(N · |suff|)。建構只需 O(ΣL)，用查詢時間換建構空間。

> [!question]- F2. 如果要回傳「符合條件的單字有幾個」，而不是最大索引呢？
> 組合 key 的方法要小心重複計數：同一個單字可能有多個 key 經過同一個查詢節點嗎？不會，因為查詢字串 `suff + "{" + pref` 中的 `"{"` 位置固定了後綴長度，每個單字只有一個 key 的 `"{"` 出現在那個位置。所以只要把 `node["#"] = idx` 改成 `node["cnt"] += 1`，查詢終點的計數就是答案，O(|pref| + |suff|)。若單字可能重複且只想算不同的單字，就先去重再建構。hash 版本則是把值改成計數，但同一個單字的 (前綴, 後綴) 組合彼此不同，也不會重複。

> [!question]- F3. 如果建構之後還會陸續加入新單字（索引持續遞增）呢？
> trie 版本天生支援：新單字照樣插入它的 L + 1 個 key，沿路把索引覆蓋成新的較大值，每次 O(L²)，不影響之前的節點。hash 版本也是一樣的 O(L²) 次寫入。若也要支援刪除單字，「最大索引」就不能只存一個值，因為刪掉最大的之後需要知道次大的；每個節點要改存一個可刪除的最大值結構（例如 heap 加 lazy deletion，或排序容器），查詢時取最大的未刪除索引，這時建構與更新都會多一個 log 因子。

> [!question]- F4. 如果條件從「以 suff 結尾」改成「包含子字串 sub」呢？
> 只看「包含 sub」這一個條件時，把每個單字的所有後綴插入同一棵 trie（suffix trie），節點存經過的最大索引：w 包含 sub ⇔ w 的某個後綴以 sub 開頭，所以查詢是走 sub，O(|sub|)，建構 O(N · L²)。但再加上「以 pref 開頭」就沒辦法串成一個前綴了，因為 sub 在單字中的位置不固定，sub 之後還接著不定長的字元，無法在固定位置接上分隔符與 pref。可行的做法有兩種：單字很短時直接列舉每個單字的所有 (前綴, 子字串) 組合放進 hash map，每個單字 O(L³) 個 key，L = 7 時約 300 個；單字較長時讓兩棵 trie 的節點各存排序的索引串列，查詢時從尾端用 two pointers 找最大的共同索引。這說明了本題技巧的適用條件：兩個條件都必須能寫成「從固定位置開始的前綴」。

### 心得

關鍵突破是用一個不會出現在單字中的分隔符，把「後綴 + 分隔符 + 單字」串成一個 key，於是兩個獨立的條件變成一次前綴查詢。它和核心題 4 的關係是：trie 只能回答前綴問題，所以題目的難點在於**把問題改寫成前綴問題**，這和第 8 章把最佳化問題改寫成判定問題是同一種思維。面試時先說兩棵 trie 取交集的做法與它的瓶頸，再提出組合 key，並用 L ≤ 7 說明 O(N · L²) 的空間可以接受；若面試官放寬 L，就自然接到 F1 的取捨。

## 難題 3｜1707. Maximum XOR With an Element From Array｜Hard

### 題目

給一個非負整數陣列 `nums` 和一串查詢 `queries`，第 i 個查詢是 `[x, m]`：在 `nums` 中所有 **≤ m** 的元素裡，找出與 x 做 XOR 後最大的值，回傳這個最大的 XOR；如果 `nums` 中沒有任何元素 ≤ m，回傳 -1。輸出一個長度與 `queries` 相同的陣列。限制：`1 <= len(nums), len(queries) <= 10⁵`，所有數值在 0 到 10⁹ 之間。

- 範例 1：`nums = [0, 1, 2, 3, 4]`、`queries = [[3, 1], [1, 3], [5, 6]]`，回傳 `[3, 3, 7]`。第一個查詢只能用 0 和 1，`3 XOR 0 = 3` 最大；第三個查詢可以用全部，`5 XOR 2 = 7`。
- 範例 2：`nums = [5, 2, 4, 6, 6, 3]`、`queries = [[12, 4], [8, 1], [6, 3]]`，回傳 `[15, -1, 5]`。第二個查詢沒有 ≤ 1 的元素。
- 範例 3（邊界）：`nums = [7]`、`queries = [[0, 7], [0, 6]]`，回傳 `[7, -1]`；x = 0 時答案就是可用元素中的最大值。
- 範例 4（邊界）：`nums = [1000000000]`、`queries = [[1000000000, 1000000000]]`，回傳 `[0]`，自己和自己 XOR 是 0。

### 提示

> [!tip]- 提示 1
> 先忽略 ≤ m 的限制：給 x，在一群數中找最大的 x XOR y。把每個數寫成 30 位元的 0／1 字串放進 trie，從最高位開始，每一位都盡量選和 x 相反的位元。為什麼這樣貪婪是對的？

> [!tip]- 提示 2
> 限制 ≤ m 讓每個查詢能用的集合不同。如果查詢可以離線處理（全部讀完再回答），把查詢依 m 由小到大排序、把 nums 也排序，依序把 ≤ m 的數插入 trie，trie 裡就剛好是這個查詢能用的數。

> [!tip]- 提示 3
> 每個查詢之前，把所有 ≤ m 的 nums 插入（指標只往前），trie 為空就回答 -1，否則做一次貪婪查詢。另一種線上做法是在 trie 每個節點存「子樹中的最小值」，查詢時只走最小值 ≤ m 的子節點。

### 詳解

**為什麼直覺做法不夠**。暴力解對每個查詢掃過所有 nums，O(n · q) = 10¹⁰，太慢。把 nums 排序後用 bisect 找出 ≤ m 的前綴，可以快速知道「哪些數可用」，但 XOR 和大小順序沒有單調關係（`5 XOR 2 = 7` 而 `5 XOR 3 = 6`、`5 XOR 4 = 1`），在可用的前綴裡仍然只能逐一嘗試。問題的兩個部分需要兩種不同的結構：XOR 最大化要按**位元**組織，≤ m 的限制要按**大小**組織。

**第一個突破：binary trie 的貪婪**。把每個數看成從第 29 位到第 0 位的 0／1 字串（10⁹ < 2³⁰，所以 30 位就夠），插入 binary trie。查詢 x 時從根往下走，第 b 位上 x 的位元是 `xb`，若 trie 中有 `1 − xb` 這個子節點就走過去，這一位的 XOR 就是 1；沒有才走 `xb`。這個貪婪是最佳的，因為 XOR 結果的第 b 位是 1 時，它至少是 2^b，而所有更低的位元加起來最多是 2^b − 1；所以「讓第 b 位為 1」比任何低位的選擇都重要，在高位能贏就必須贏。每次查詢 O(30)。

**第二個突破：離線排序讓「可用集合」只增不減**。如果 trie 裡剛好是所有 ≤ m 的數，第一個突破就直接適用。把查詢依 m 遞增排序後，後面查詢的可用集合包含前面的，所以只需要一個指標在排序後的 nums 上往前推：處理查詢 (x, m) 之前，把所有 ≤ m 但還沒插入的數插入。每個數只插入一次，總共 O(n · 30)。答案要寫回查詢原本的位置，所以排序的是查詢的索引。這和第 9 章難題 5（1851）是同一種「離線處理」技巧：查詢之間沒有依賴、可以重新排序時，常常能把「每個查詢一個不同的子集合」變成「一個只增不減的集合」。

**線上做法**。若查詢必須依序即時回答（不能排序），可以把所有 nums 一次插入，並在每個節點記錄子樹中的最小值 `low`。查詢時若根的 `low > m` 就回答 -1；否則每一步優先走相反位元的子節點，**但只在它的 `low <= m` 時才走**，不然就走另一個子節點。因為目前節點的 `low <= m`，它至少有一個子節點的 `low <= m`，所以永遠走得下去；而且走過的每個子樹都至少含一個 ≤ m 的數，最後到達的葉子就是一個合法的 y。貪婪的論證不變，只是「可選的子節點」多了一個條件。

```text
nums = [0, 1, 2, 3, 4]（用 3 位元表示），queries = [[3,1], [1,3], [5,6]]
依 m 排序：(3, m=1)、(1, m=3)、(5, m=6)

處理 (x=3=011, m=1)：插入 0=000、1=001
  位元 2：x=0，想要 1 → 沒有 → 走 0         XOR 位元 0
  位元 1：x=1，想要 0 → 有   → 走 0         XOR 位元 1
  位元 0：x=1，想要 0 → 有（000）→ 走 0      XOR 位元 1
  答案 011 = 3（配對 y = 0）

處理 (x=1=001, m=3)：再插入 2=010、3=011
  位元 2：想要 1 → 沒有 → 走 0                0
  位元 1：x=0，想要 1 → 有（2、3）→ 走 1      1
  位元 0：x=1，想要 0 → 有（010）→ 走 0       1
  答案 011 = 3（配對 y = 2）

處理 (x=5=101, m=6)：再插入 4=100
  位元 2：x=1，想要 0 → 有（0～3）→ 走 0      1
  位元 1：x=0，想要 1 → 有（2、3）→ 走 1      1
  位元 0：x=1，想要 0 → 有（010）→ 走 0       1
  答案 111 = 7（配對 y = 2）
```

第三個查詢中 4 已經可用，但貪婪在最高位就選擇了 0 那一邊（因為 x 的最高位是 1，選 0 才能讓 XOR 的最高位是 1），4 根本不會被考慮，因為 `5 XOR 4 = 1` 遠小於選 0 那邊能得到的值。這就是「高位能贏就必須贏」的效果。

### 解法

```python
import random


def maximize_xor(nums: list[int], queries: list[list[int]]) -> list[int]:
    """離線做法：查詢依 m 排序，nums 依序插入 binary trie。"""
    BITS = 30
    nums = sorted(nums)
    order = sorted(range(len(queries)), key=lambda i: queries[i][1])
    trie = [[0, 0]]                          # trie[v] = [0 子節點, 1 子節點]；0 表示沒有
    ans = [-1] * len(queries)
    p = 0
    for qi in order:
        x, m = queries[qi]
        while p < len(nums) and nums[p] <= m:
            v, y = 0, nums[p]
            for b in range(BITS - 1, -1, -1):
                bit = y >> b & 1
                if not trie[v][bit]:
                    trie[v][bit] = len(trie)
                    trie.append([0, 0])
                v = trie[v][bit]
            p += 1
        if p == 0:                           # 沒有任何 <= m 的數
            continue
        v = res = 0
        for b in range(BITS - 1, -1, -1):
            want = (x >> b & 1) ^ 1
            if trie[v][want]:
                res |= 1 << b
                v = trie[v][want]
            else:
                v = trie[v][want ^ 1]
        ans[qi] = res
    return ans


def maximize_xor_online(nums: list[int], queries: list[list[int]]) -> list[int]:
    """線上做法：每個節點存子樹最小值，只走最小值 <= m 的子節點。"""
    BITS = 30
    INF = float("inf")
    trie, low = [[0, 0]], [INF]
    for y in nums:
        v = 0
        low[0] = min(low[0], y)
        for b in range(BITS - 1, -1, -1):
            bit = y >> b & 1
            if not trie[v][bit]:
                trie[v][bit] = len(trie)
                trie.append([0, 0])
                low.append(INF)
            v = trie[v][bit]
            low[v] = min(low[v], y)
    out = []
    for x, m in queries:
        if low[0] > m:
            out.append(-1)
            continue
        v = res = 0
        for b in range(BITS - 1, -1, -1):
            want = (x >> b & 1) ^ 1
            c = trie[v][want]
            if c and low[c] <= m:
                res |= 1 << b
                v = c
            else:
                v = trie[v][want ^ 1]        # 目前節點 low <= m，另一邊必定可走
        out.append(res)
    return out


def brute(nums, queries):
    return [max((x ^ y for y in nums if y <= m), default=-1) for x, m in queries]


for fn in (maximize_xor, maximize_xor_online):
    assert fn([0, 1, 2, 3, 4], [[3, 1], [1, 3], [5, 6]]) == [3, 3, 7]
    assert fn([5, 2, 4, 6, 6, 3], [[12, 4], [8, 1], [6, 3]]) == [15, -1, 5]
    assert fn([7], [[0, 7], [0, 6]]) == [7, -1]
    assert fn([10**9], [[10**9, 10**9]]) == [0]
    for _ in range(300):
        nums = [random.choice([random.randrange(64), random.randrange(10**9 + 1)])
                for _ in range(random.randint(1, 15))]
        qs = [[random.randrange(10**9 + 1), random.choice([random.randrange(70), random.randrange(10**9 + 1)])]
              for _ in range(10)]
        assert fn(nums, qs) == brute(nums, qs)
nums = [random.randrange(10**9) for _ in range(20000)]
qs = [[random.randrange(10**9), random.randrange(10**9)] for _ in range(20000)]
assert maximize_xor(nums, qs) == maximize_xor_online(nums, qs)
print("all tests passed")
```

### 複雜度與邊界

離線做法時間 O(n log n + q log q + (n + q) · B)，B = 30 是位元數：兩次排序，之後每個數插入一次、每個查詢走一次 trie。空間 O(n · B) 個 trie 節點加 O(q) 的答案。線上做法省掉兩次排序，時間 O((n + q) · B)，多一個 `low` 陣列。邊界情況：可用集合為空時回答 -1，離線版本用「指標還在 0」判斷，線上版本用根的 `low > m`；x = 0 時貪婪每一位都想要 1，得到的就是可用元素中的最大值；重複的 nums 只是走同一條路徑，不影響結果；位元數必須涵蓋最大值，10⁹ 需要 30 位，若值可達 2³¹ − 1 就要 31 位。

### Follow-up

> [!question]- F1. 如果問的是陣列中任兩個數的最大 XOR 呢（421. Maximum XOR of Two Numbers in an Array）？
> 沒有 ≤ m 的限制，直接把所有數插入 binary trie，再對每個數查一次最大 XOR，取最大值，O(n · B)。也可以邊插入邊查詢（先查再插入），trie 中永遠是「前面的數」，每對只考慮一次。另一種不用 trie 的做法是從高位逐位確定答案：假設答案的前幾位已知，把每個數的前綴放進 set，檢查是否存在兩個前綴的 XOR 等於「目前答案 | 這一位為 1」，用的是 `a XOR b = c ⇔ a XOR c = b`，同樣 O(n · B)。

> [!question]- F2. 如果限制改成「只能用 nums 中下標在 [l, r] 範圍內的元素」呢？
> 用 persistent trie（可持久化 trie）：依序插入 nums[0], nums[1], …，每次插入只複製路徑上的 B + 1 個節點，產生一個新版本的根，並在每個節點存「經過的數的個數」。版本 r 的 trie 包含 nums[0..r]，版本 l − 1 包含 nums[0..l−1]，兩個版本同一位置的計數相減，就是 nums[l..r] 在這個子樹中的個數。查詢時同時走兩個版本，只走「計數差 > 0」的子節點，每個查詢 O(B)，總空間 O(n · B)。若查詢可以離線，也可以依 r 排序，並在節點存「最近插入的下標」，只走下標 ≥ l 的子節點，更省記憶體。

> [!question]- F3. 如果要計算有多少對 (i, j) 的 nums[i] XOR nums[j] 落在 [low, high] 之間呢（1803. Count Pairs With XOR in a Range）？
> 轉成「XOR < high + 1 的對數」減去「XOR < low 的對數」。對固定的 x 計算「trie 中有幾個 y 使 x XOR y < K」：從高位往下走，在 K 的第 b 位為 1 的地方，讓 XOR 這一位為 0 的那個子樹整個都小於 K，把它的計數加進答案，然後沿著 XOR 這一位為 1 的方向繼續；K 的位元為 0 時只能走 XOR 為 0 的方向。每個節點存子樹大小，每次查詢 O(B)。邊插入邊查詢，總共 O(n · B)。這是 binary trie 從「求最大值」推廣到「計數」的標準形。

> [!question]- F4. 如果還要支援刪除 nums 中的元素呢？
> 在每個節點存子樹中的數量 `cnt`，插入時沿路加一、刪除時沿路減一；查詢時把「子節點存在」改成「子節點的 `cnt > 0`」。若同時有 ≤ m 的限制且查詢是線上的，`low` 欄位在刪除後無法直接維護（刪掉最小值後要知道次小值），可以改成每個節點存一個 multiset，或把 m 的限制改用 F2 的思路：先依值排序，建立以值的排名為版本的 persistent trie，查詢 ≤ m 等於查詢排名前綴的版本。刪除與這種持久化結構不相容時，就要考慮離線處理整個操作序列，例如依時間做分治。

### 心得

關鍵突破有兩個：binary trie 從高位貪婪求最大 XOR，以及把查詢依 m 排序，讓「每個查詢不同的可用集合」變成「只增不減的集合」。它和 13.4 節的 `BinaryTrie` 模板是同一個結構，難度在於把 ≤ m 的限制和位元貪婪結合起來，離線排序與節點存最小值是兩種標準答案。面試時先說 O(nq) 的暴力解，再說「沒有限制時是 421 題的 binary trie」，最後點出「限制只是讓可用集合隨 m 變大」，自然推出離線排序；若面試官要求線上回答，就補上節點存最小值的版本。

## 難題 4｜472. Concatenated Words｜Hard

### 題目

給一串**互不相同**的字串 `words`，回傳其中所有的「串接字」。串接字的定義是：它可以完全由 `words` 中**至少兩個**較短的字串依序串接而成，同一個字串可以重複使用。回傳順序不限。限制：`1 <= len(words) <= 10⁴`，每個字串長度 1 到 30，只含小寫字母，所有字串的總長度不超過 10⁵。

- 範例 1：`words = ["cat","cats","catsdogcats","dog","dogcatsdog","hippopotamuses","rat","ratcatdogcat"]`，回傳 `["catsdogcats","dogcatsdog","ratcatdogcat"]`；例如 `catsdogcats = cats + dog + cats`。
- 範例 2：`words = ["cat","dog","catdog"]`，回傳 `["catdog"]`。
- 範例 3（邊界）：`words = ["a","aa","aaa"]`，回傳 `["aa","aaa"]`；`aaa` 可以是 `a + a + a` 或 `a + aa`，同一個字串可以重複使用。
- 範例 4（邊界）：`words = ["abc"]`，回傳 `[]`；只有一個字串時不可能由「至少兩個」組成。

### 提示

> [!tip]- 提示 1
> 判斷單一字串能不能被切成字典中的單字，就是第 21 章核心題 4（139. Word Break）。這題對每個字串都做一次 word break，字典是「其他字串」。怎麼處理「至少兩個」與「不能用自己」？

> [!tip]- 提示 2
> 依長度排序後依序處理：處理字串 w 時，字典裡只放比它先處理的字串。任何切法的每一段都比 w 短或等長而不等於 w，所以自然至少兩段。

> [!tip]- 提示 3
> Word break 的 DP 是 `ok[j] = 存在 i < j 使 ok[i] 且 w[i:j] 在字典中`。用 trie 代替 set：從每個 `ok[i]` 為真的位置沿著 trie 往下走，一次就列出所有以 i 開頭、是單字的子字串，走不下去就停。

### 詳解

**為什麼直覺做法不夠**。最直接的是對每個字串遞迴嘗試所有切法：第一段取長度 1、2、…，若是單字就遞迴處理剩下的部分。沒有記憶化時，像 `aaaa…ab` 這種字串會產生指數級的嘗試。加上記憶化（就是 139 題的 DP），每個字串是 O(L²) 個子字串查詢，每次用 set 查詢還要 O(L) 的切片與雜湊，所以是 O(L³)；L = 30 時一個字串 2.7 × 10⁴，在總長度 10⁵ 的限制下 Σ L³ ≤ 30² × 10⁵ = 9 × 10⁷，Python 中偏慢。另一個要處理的是規則本身：字典不能包含 w 自己，否則每個字串都能「由自己組成」；而且至少要兩段。

**第一個突破：依長度排序，字典只放更短的字串**。依長度由短到長處理，處理 w 時，字典裡只有已經處理過的字串（長度 ≤ |w|），處理完再把 w 加入字典。長度相同的其他字串不可能是 w 的真子字串，只能作為整段出現，但它們不等於 w（字串互不相同），所以任何合法切法用到的都是比 w 短的字串，**自動**至少兩段，也自動不會用到 w 自己。這個排序同時省下了「把自己從字典暫時移除」的麻煩。

**第二個突破：用 trie 一次列出所有可行的下一段**。139 題的 DP 中，對每個 `ok[i]` 為真的起點，我們要知道哪些 j 使 `w[i:j]` 是單字。用 set 要對每個 j 切片查詢；用 trie 則是從根開始沿著 `w[i], w[i+1], …` 往下走，每遇到一個 `is_end` 的節點就把對應的 `ok[j]` 設成真，遇到不存在的邊就停。走一步只要 O(1)，而且一旦目前的子字串不是任何單字的前綴就立刻停止，在字典稀疏時比列舉所有 j 快得多。每個字串最差 O(L²)。

**正確性**。`ok[j]` 為真 ⇔ `w[:j]` 能被切成字典中的單字（字典只含比 w 短的字串）。初始 `ok[0]` 為真（空前綴）。對每個 `ok[i]` 為真的位置，從 i 出發在 trie 上找到的每個單字終點 j，`w[:j] = w[:i] + w[i:j]` 都能被切分，所以 `ok[j]` 為真；反過來，任何合法切法的最後一段 `w[i:j]` 都會在處理起點 i 時被 trie 走到。最後 `ok[L]` 為真時，因為字典中沒有長度 L 等於 w 的單字，切法一定有至少兩段，w 就是串接字。

```text
w = "catsdogcats"，字典 trie 中已有 cat、cats、dog（以及其他較短的字串）
index:  0 1 2 3 4 5 6 7 8 9 10 11
char:   c a t s d o g c a t s

ok[0] = T
從 i = 0 沿 trie 走：c → a → t（cat，ok[3] = T）→ s（cats，ok[4] = T）→ d？trie 沒有，停
i = 1, 2：ok 為 F，跳過
從 i = 3 走：s？trie 根沒有 s，停
從 i = 4 走：d → o → g（dog，ok[7] = T）→ c？沒有，停
i = 5, 6：跳過
從 i = 7 走：c → a → t（cat，ok[10] = T）→ s（cats，ok[11] = T）
ok[11] = T → "catsdogcats" 是串接字（cats + dog + cats）

ok:     T F F T T F F T F F T  T
```

從 i = 3 出發的嘗試說明了 trie 的剪枝：`cat` 之後的 `s…` 不是任何單字的開頭，trie 在第一步就停下，不必檢查 `s`、`sd`、`sdo`、… 這些子字串是否在字典中。DP 本身保證每個起點只處理一次，即使 `ok[3]` 和 `ok[4]` 兩條路徑在後面可能交會。

### 解法

```python
import random
from functools import cache


def find_all_concatenated_words(words: list[str]) -> list[str]:
    root = {}
    result = []

    def can_form(w: str) -> bool:
        n = len(w)
        ok = [False] * (n + 1)
        ok[0] = True
        for i in range(n):
            if not ok[i]:
                continue
            node = root
            for j in range(i, n):
                node = node.get(w[j])
                if node is None:
                    break
                if "$" in node:
                    ok[j + 1] = True
            if ok[n]:
                return True
        return False

    for w in sorted(words, key=len):
        if not w:                            # 防禦：空字串不是單字，也不能當成一段
            continue
        if can_form(w):
            result.append(w)
        node = root                          # 處理完才加入字典
        for ch in w:
            node = node.setdefault(ch, {})
        node["$"] = True
    return result


def brute(words):
    out = []
    for w in words:
        others = set(words) - {w, ""}

        @cache
        def parts(i):                        # w[i:] 最多能切成幾段（-1 表示不行）
            if i == len(w):
                return 0
            best = -1
            for j in range(i + 1, len(w) + 1):
                if w[i:j] in others and (p := parts(j)) >= 0:
                    best = max(best, p + 1)
            return best
        if w and parts(0) >= 2:
            out.append(w)
    return out


ex = ["cat", "cats", "catsdogcats", "dog", "dogcatsdog", "hippopotamuses", "rat", "ratcatdogcat"]
assert sorted(find_all_concatenated_words(ex)) == ["catsdogcats", "dogcatsdog", "ratcatdogcat"]
assert find_all_concatenated_words(["cat", "dog", "catdog"]) == ["catdog"]
assert sorted(find_all_concatenated_words(["a", "aa", "aaa"])) == ["aa", "aaa"]
assert find_all_concatenated_words(["abc"]) == []
assert find_all_concatenated_words(["", "a", "aa"]) == ["aa"]
many = ["a" * k for k in range(1, 31)] + ["a" * 29 + "b"]
assert sorted(find_all_concatenated_words(many)) == sorted("a" * k for k in range(2, 31))
for _ in range(300):
    words = list({"".join(random.choice("ab") for _ in range(random.randint(1, 6))) for _ in range(8)})
    assert sorted(find_all_concatenated_words(words)) == sorted(brute(words))
print("all tests passed")
```

### 複雜度與邊界

排序 O(N log N)。每個長度 L 的字串，DP 最多有 L 個起點，每個起點在 trie 上最多走 L 步，所以是 O(L²)；總時間 O(Σ L²) ≤ O(30 · Σ L) = 3 × 10⁶。插入 trie 共 O(Σ L)，trie 的節點數不超過總字元數 10⁵。空間 O(Σ L) 加上每個字串 O(L) 的 `ok` 陣列。邊界情況：最短的字串一定不是串接字，因為處理它時字典是空的；同一個字串可以重複使用（`aaa = a + a + a`），DP 天生允許；空字串若出現在輸入中必須跳過，否則它會讓 trie 的根變成單字結尾，雖然在這個 DP 中不會造成錯誤答案，但「由空字串組成」不符合題意，跳過最清楚；找到 `ok[n]` 就提早回傳，避免多餘的 trie 走訪。

### Follow-up

> [!question]- F1. 如果要回傳每個串接字的一種切法，或是最少要用幾段呢？
> 把 `ok` 換成 `best[j]` = 切出 `w[:j]` 的最少段數（不可行為 ∞），轉移是 `best[j + 1] = min(best[j + 1], best[i] + 1)`，每次在 trie 上走到單字終點就更新；同時記錄 `prev[j + 1] = i`，最後從 `prev[n]` 往回追就得到切法。時間仍是 O(L²)。要注意「至少兩段」在最少段數版本中一樣自動成立，因為字典裡沒有 w 自己。若要列出**所有**切法，輸出量可能是指數級（例如 `aaaa…a`），就要改成記憶化的 backtracking，像 140. Word Break II 那樣，並先和面試官確認輸出規模。

> [!question]- F2. 如果規定只能由「恰好兩個」字典字串組成呢？
> 不需要 DP：對每個字串 w，列舉切點 k = 1 … L − 1，檢查 `w[:k]` 與 `w[k:]` 是否都在 set 中，O(L) 個切點、每次切片與雜湊 O(L)，總共 O(Σ L²)。用 trie 可以省掉前半段的重複雜湊：沿著 w 在前綴 trie 上走，每遇到一個單字終點 k，再用 set 檢查 `w[k:]`。這時不必依長度排序，因為兩段都是真子字串，比 w 短，不會用到 w 自己（除非有空字串，要排除）。

> [!question]- F3. 如果字典很小但要檢查的字串非常長（例如一篇長度 10⁶ 的文章能否被切成字典單字）呢？
> 字串很長時 O(L²) 不可行，但每個起點在 trie 上最多只走 L_max 步（L_max 是字典中最長單字的長度），所以 DP 實際上是 O(L · L_max)。若 L_max 也很大，就用 Aho-Corasick automaton：把字典建成帶 failure link 的 trie，對文章掃一遍，在每個位置 j 找出所有以 j 結尾的單字（透過 output link 列出），總時間 O(L + 字典總長 + 匹配數)，然後 `ok[j + 1] |= ok[j + 1 − len(word)]`。這是第 25 章字串演算法的延伸，面試中說出「每個位置只需要知道以它結尾的單字」就足以說明思路。

> [!question]- F4. 如果要計算每個串接字有幾種不同的切法（答案對 10⁹ + 7 取餘數）呢？
> 把布林 DP 換成計數 DP：`ways[0] = 1`，在 trie 上從 i 走到單字終點 j 時 `ways[j + 1] += ways[i]`，最後 `ways[L]` 就是切法數。但要注意「至少兩段」：因為字典不含 w 自己，所有切法都至少兩段，`ways[L]` 不需要扣除任何東西；若改成字典包含 w 本身，則要減去「整個字串一段」的那一種。時間仍是 O(L²)，取餘數只在加法時做。這是第 21 章「從可行性 DP 改成計數 DP」的標準變形。

### 心得

關鍵突破有兩個：依長度排序讓「字典只含更短的字串」，於是「至少兩段、不能用自己」這兩個規則自動成立；再用 trie 讓 word break 的每個起點一次列出所有可行的下一段，並在不是任何單字前綴時立刻停止。它是第 21 章核心題 4（139）的 DP 加上本章核心題 4 的 trie，trie 在這裡扮演「同時查詢很多個子字串」的角色，和難題 1 在網格上同時推進很多單字是同一個想法。面試時先說對每個字串做 139 題的 O(L³) 版本，再說明排序如何處理題目的兩個規則，最後用 trie 降到 O(L²)；能主動指出「排序讓規則自動成立」，比在程式裡寫一堆特判更有說服力。

## 難題 5｜99. Recover Binary Search Tree｜Medium

### 題目

一棵 BST 中**恰好有兩個節點的值被互相交換了**，其他都正確。請在不改變樹結構的前提下修復它（只交換回那兩個值），函式不需要回傳，直接修改樹。限制：節點數在 2 到 1000 之間，節點值在 `-2³¹` 到 `2³¹ − 1` 之間，且互不相同。進階要求：O(n) 時間的做法很直接，能不能只用 O(1) 額外空間？

- 範例 1：`root = [1, 3, null, null, 2]`，修復後是 `[3, 1, null, null, 2]`。原本 3 在 1 的左邊，但 3 > 1；交換 1 和 3 即可。
- 範例 2：`root = [3, 1, 4, null, null, 2]`，修復後是 `[2, 1, 4, null, null, 3]`。2 在 3 的右子樹中卻比 3 小；交換 2 和 3。
- 範例 3（邊界）：`root = [2, 3, 1]`，修復後是 `[2, 1, 3]`，只有兩個葉子被交換。
- 範例 4（邊界）：`root = [1, 2]`（2 在 1 的左邊），修復後是 `[2, 1]`；被交換的兩個節點在中序中相鄰。

### 提示

> [!tip]- 提示 1
> 用中序定義：正確的 BST 中序是嚴格遞增的。把一個遞增序列中的兩個元素交換之後，會出現什麼樣的「下降」？

> [!tip]- 提示 2
> 若交換的兩個元素在中序中不相鄰，會出現兩個下降：第一個下降的**較大者**和第二個下降的**較小者**就是被交換的兩個；若相鄰，只有一個下降，兩個元素就是這個下降的兩端。

> [!tip]- 提示 3
> 走訪時只需要記住前一個節點 `prev`：遇到 `prev.val > node.val` 時，若 `first` 還沒設定就設成 `prev`，並且每次都把 `second` 更新成 `node`。走完後交換兩者的值。要 O(1) 空間，把迭代中序換成 Morris traversal。

### 詳解

**為什麼直覺做法不夠**。最直接的做法是中序走訪把所有值取出，排序，再依中序順序把排序後的值寫回去，O(n log n) 時間、O(n) 空間。它利用了正確的觀察（中序必須遞增），但做了太多事：題目保證只有兩個值錯位，排序整個序列是多餘的；而且 O(n) 空間不符合進階要求。另一個直覺是由上往下用核心題 1 的區間檢查找出「違規」的節點，但一次交換可能讓好幾個節點看起來都違規（被換到錯誤位置的值會讓它的祖先與子孫的區間關係都出問題），很難直接判斷是哪兩個。

**突破點：交換在遞增序列中留下的痕跡**。設中序序列原本是 a₁ < a₂ < … < aₙ，交換了位置 i < j 的兩個值。若 j = i + 1（相鄰），序列在位置 i 出現唯一一個下降：`aⱼ` 放在前面、`aᵢ` 放在後面，而 aⱼ > aᵢ。若 j > i + 1，會出現兩個下降：位置 i 現在放著較大的 aⱼ，它比下一個元素 aᵢ₊₁ 大，這是第一個下降，而**較大的那個（前者）**就是錯誤節點；位置 j 現在放著較小的 aᵢ，前一個元素 aⱼ₋₁ 比它大，這是第二個下降，**較小的那個（後者）**就是另一個錯誤節點。其他位置的相鄰關係完全不受影響。所以規則統一成：`first` = 第一個下降的前者，`second` = 最後一個下降的後者；相鄰的情況中兩個下降是同一個，規則依然成立。

**為什麼只需要 prev**。下降只牽涉中序中相鄰的兩個元素，所以走訪時記住前一個節點就能偵測。程式中「每遇到下降就更新 second」而不是只在第二次才更新，正好同時處理了相鄰（只有一次下降，second 就是那次的後者）與不相鄰（second 被第二次下降覆蓋）兩種情況。

**O(1) 空間：Morris traversal**。迭代中序需要 O(h) 的 stack，是因為走完左子樹後要「回到」父節點。Morris 的做法是借用樹上空著的指標：對有左子樹的節點 cur，找到它在中序中的前驅 pred（左子樹的最右節點），pred 的 `right` 一定是空的，暫時把它指向 cur，當作走完左子樹後回來的路，然後走進左子樹。之後若從 pred 沿著這條線索回到 cur，再找一次 pred 時會發現 `pred.right is cur`，代表左子樹已經處理完：把線索清掉、處理 cur、往右走。每條邊最多走兩次（一次建立線索、一次拆掉），O(n) 時間、O(1) 空間，而且走完之後所有線索都已還原，樹結構不變。

```text
正確的中序：1 2 3 4 5 6；交換 2 和 5 之後：1 5 3 4 2 6

index:   0  1  2  3  4  5
inorder: 1  5  3  4  2  6
            ↘↗       ↘↗
         下降1：5 > 3       下降2：4 > 2
first  = 下降1 的前者 = 5
second = 下降2 的後者 = 2      → 交換 5 和 2 得到 1 2 3 4 5 6

相鄰的情況：交換 3 和 4 → 1 2 4 3 5 6
只有一個下降：4 > 3 → first = 4、second = 3

範例 2 的樹：[3, 1, 4, null, null, 2]
        3
       / \
      1   4
         /
        2
中序：1 3 2 4 → 唯一下降 3 > 2 → first = 3（根）、second = 2 → 交換值
修復後：
        2
       / \
      1   4
         /
        3
```

第一個例子中，`first` 在第一次下降時被設定為 5 之後就不再改變，`second` 先被設成 3，第二次下降時被覆蓋成 2。若程式寫成「第一次下降設 first、第二次下降設 second」，相鄰交換時 second 永遠不會被設定；「每次下降都更新 second」這一行同時解決了兩種情況。

### 解法

```python
import random


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def recover_tree(root) -> None:
    """迭代中序：O(n) 時間、O(h) 空間。"""
    first = second = prev = None
    stack, node = [], root
    while stack or node is not None:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()
        if prev is not None and prev.val > node.val:
            if first is None:
                first = prev                 # 第一個下降的前者
            second = node                    # 最後一個下降的後者
        prev = node
        node = node.right
    first.val, second.val = second.val, first.val


def recover_tree_morris(root) -> None:
    """Morris 中序：O(n) 時間、O(1) 額外空間，走完後樹結構完全還原。"""
    first = second = prev = None
    cur = root
    while cur is not None:
        if cur.left is None:
            visit = cur
            cur = cur.right
        else:
            pred = cur.left
            while pred.right is not None and pred.right is not cur:
                pred = pred.right
            if pred.right is None:
                pred.right = cur             # 建立回程線索，先處理左子樹
                cur = cur.left
                continue
            pred.right = None                # 左子樹已處理完，拆掉線索
            visit = cur
            cur = cur.right
        if prev is not None and prev.val > visit.val:
            if first is None:
                first = prev
            second = visit
        prev = visit
    first.val, second.val = second.val, first.val


def insert(root, v):
    if root is None:
        return TreeNode(v)
    node = root
    while True:
        side = "left" if v < node.val else "right"
        if getattr(node, side) is None:
            setattr(node, side, TreeNode(v))
            return root
        node = getattr(node, side)


def nodes_of(root):
    out, stack, node = [], [], root
    while stack or node:
        while node:
            stack.append(node)
            node = node.left
        node = stack.pop()
        out.append(node)
        node = node.right
    return out


def shape(root):                             # 用 id 記錄結構，確認指標沒有被改動
    if root is None:
        return None
    return (id(root), shape(root.left), shape(root.right))


for fn in (recover_tree, recover_tree_morris):
    r = TreeNode(1, TreeNode(3, None, TreeNode(2)))
    fn(r)
    assert (r.val, r.left.val, r.left.right.val) == (3, 1, 2)
    r = TreeNode(3, TreeNode(1), TreeNode(4, TreeNode(2)))
    fn(r)
    assert (r.val, r.left.val, r.right.val, r.right.left.val) == (2, 1, 4, 3)
    r = TreeNode(2, TreeNode(3), TreeNode(1))
    fn(r)
    assert (r.val, r.left.val, r.right.val) == (2, 1, 3)
    r = TreeNode(1, TreeNode(2))
    fn(r)
    assert (r.val, r.left.val) == (2, 1)
    r = TreeNode(-2**31, None, TreeNode(2**31 - 1))
    r.val, r.right.val = r.right.val, r.val
    fn(r)
    assert (r.val, r.right.val) == (-2**31, 2**31 - 1)
    for _ in range(500):
        vals = random.sample(range(-100, 100), random.randint(2, 25))
        root = None
        for v in vals:
            root = insert(root, v)
        before = shape(root)
        a, b = random.sample(nodes_of(root), 2)
        a.val, b.val = b.val, a.val
        fn(root)
        assert [n.val for n in nodes_of(root)] == sorted(vals)
        assert shape(root) == before         # Morris 的線索全部被拆掉
print("all tests passed")
```

### 複雜度與邊界

兩種寫法時間都是 O(n)。迭代中序的空間是 O(h)，Morris 是 O(1)：每個有左子樹的節點，找前驅時會走過左子樹的右鏈兩次，而所有節點的「左子樹右鏈」彼此不重疊，總長度是 O(n)。邊界情況：只有兩個節點時兩者必定在中序中相鄰，只有一個下降；被交換的可能是根，也可能是兩個葉子，因為只交換值不動指標，所以不需要處理父節點；值可以是 `-2³¹` 或 `2³¹ − 1`，程式只比較節點值、不用哨兵，所以沒有溢位問題；Morris 版本不能在找到兩個節點後提早結束，否則有些線索還沒拆掉，樹結構會被破壞。

### Follow-up

> [!question]- F1. 如果不只兩個節點，而是任意多個值被打亂了（結構正確），要怎麼修復？
> 只交換兩次不夠了。做法是中序走訪取出所有值，排序後依中序順序寫回去，O(n log n) 時間、O(n) 空間；樹的結構決定了每個中序位置該放第幾小的值，所以這樣一定正確。若題目問「最少要交換幾次才能修復」，就是把中序序列排序所需的最少交換次數：找出每個值應該去的位置，形成若干個置換 cycle，答案是 n 減去 cycle 數，O(n log n)。這和本題「恰好一次交換 ⇔ 一或兩個下降」是同一個置換觀點。

> [!question]- F2. 如果不知道是否恰好交換了一對，要先判斷「這棵樹能否只靠一次交換修復成 BST」呢？
> 走一次中序並記錄所有下降。若沒有下降，已經是 BST；若有超過兩個下降，一次交換不可能修好（一次交換最多產生兩個下降）。若有一或兩個下降，依本題規則找出 first 與 second，交換後再走一次中序確認嚴格遞增，因為兩個下降不一定來自同一次交換（例如兩組各自相鄰的交換也會產生兩個下降）。總共 O(n) 時間，兩次走訪。這種「先用必要條件篩選、再用一次驗證確認」的寫法，在面試中能展現你對演算法前提的掌握。

> [!question]- F3. 如果要求交換的是節點本身（指標），而不是節點的值呢？
> 先用本題的方法找到 first 與 second，同時記錄它們的父節點；因為值已經錯位，不能事後用 BST 搜尋去找父節點，必須在走訪時就保存（例如 stack 中存 `(節點, 父節點)`）。交換兩個節點時要更新六條指標：兩個父節點指向它們的邊、兩者各自的左右子節點。最麻煩的是兩者是父子關係的情況（例如 first 的右子節點就是 second），此時直接交換會讓節點指向自己，必須特別處理。這是很好的追問，用來確認你知道「交換值」為什麼是題目的簡化。

> [!question]- F4. 如果同樣的情況發生在一個陣列上（排序陣列中有兩個元素被交換），能不能更快？
> 陣列沒有樹的結構限制，所以邏輯完全相同：掃一遍找下降，第一個下降的前者與最後一個下降的後者交換，O(n) 時間、O(1) 空間。這已經是最佳，因為任何演算法都必須看過每個元素才能確定哪兩個錯位（錯位可能在任何位置）。若陣列可以用 binary search 加速某些查詢，前提是已知它是排序的，而這裡正是要修復排序性，所以無法低於 O(n)。這個對比說明本題真正的工具是「中序序列等於排序陣列」，樹只是把陣列藏起來了。

### 心得

關鍵突破是把 BST 的錯誤轉成中序序列的錯誤：一次交換在遞增序列中留下一或兩個下降，第一個下降的前者與最後一個下降的後者就是答案。它和核心題 1、2 一樣都是「把 BST 問題轉成中序序列問題」，差別在於這題要從序列的錯誤反推原因；Morris traversal 則是核心題 2 F3 的 O(1) 空間技巧在這裡的實際應用。面試時先畫出 `1 5 3 4 2 6` 這樣的例子說明兩個下降，再講相鄰交換的特例，寫出 O(h) 的迭代版本後，再主動提出 Morris 滿足進階要求，並說明為什麼不能提早結束。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| BST 驗證與區間限制 | 判斷是否為 BST、重建 BST、由序列驗證 | 每個節點帶祖先給的開區間 `(low, high)` 往下傳 | 核心題 1（98）、255、1008 Construct BST from Preorder |
| 中序 = 排序序列 | 第 k 小、相鄰差、逆序、轉成排序陣列 | 迭代中序隨時可停；Morris 做到 O(1) 空間 | 核心題 2（230）、難題 5（99）、530 Minimum Absolute Difference、173 BST Iterator |
| BST 的搜尋路徑 | 插入、刪除、前驅後繼、≥ x 的最小值、LCA | 每步和節點比較丟掉一棵子樹，O(h) | 核心題 3（450）、701、235 LCA of BST、285 Inorder Successor |
| BST 的範圍剪枝 | 範圍和、修剪、範圍內的節點 | 只進入可能和範圍相交的子樹 | 938 Range Sum of BST、669 Trim a BST |
| 增強 BST（順序統計） | 頻繁修改又要第 k 小、rank 查詢 | 節點存子樹大小，依左子樹大小決定方向 | 核心題 2 F1、第 26 章的 Fenwick tree 替代方案 |
| 基本 trie | 前綴查詢、自動完成、前綴計數 | 節點存在 ⇔ 有單字以此前綴開頭；`is_end` 區分單字 | 核心題 4（208）、1804、1268、720 Longest Word in Dictionary |
| trie + DFS 分岔 | 萬用字元、模糊比對 | 普通字元走一條邊，萬用字元展開所有子節點 | 核心題 5（211）、676 Implement Magic Dictionary |
| trie + 網格 backtracking | 很多單字在同一個網格找 | DFS 同時走網格與 trie，找到就取出、空節點剪掉 | 難題 1（212）、第 19 章核心題 5（79） |
| 組合 key 的 trie | 同時限制前綴與後綴（或多個條件） | 把條件用分隔符串成一個前綴 | 難題 2（745） |
| binary trie | 最大 XOR、XOR 計數、XOR 與門檻比較 | 從高位貪婪；節點存計數、最小值或下標；離線排序查詢 | 難題 3（1707）、421、1803、1938 |
| trie + DP | 字串切分、串接字 | 從每個可到達的位置沿 trie 走，一次列出所有單字結尾 | 難題 4（472）、139（第 21 章核心題 4）、140 |
| 反轉 trie／串流 | 檢查「以目前位置結尾」的單字 | 插入反轉的單字，從最新字元往回走 | 1032 Stream of Characters（核心題 4 F4） |

**下限與上限**。最簡單的形式是直接操作結構本身：BST 的搜尋與插入（700、701），trie 的插入與查詢（208），考的是迴圈寫對、`is_end` 不漏、查詢不建立節點。中間層是利用結構的性質：核心題 1 的區間限制、核心題 2 的「中序可停」、核心題 3 的後繼取代，難點在於把題目轉成「區間」或「中序序列」的語言。上限的題目難在三個地方，常常同時出現：第一，**trie 是加速器而不是主演算法**，主演算法是另一個 pattern，例如 212 的 backtracking、472 的 DP、1707 的離線排序加貪婪，trie 負責「同時處理很多個字串或很多個前綴」；第二，**要先改寫問題才能用 trie**，例如 745 把兩個條件串成一個前綴、1032 把「以這裡結尾」變成反轉後的前綴；第三，**要在節點上維護額外資訊**，例如子樹大小（順序統計）、最小值（1707 線上版本）、計數（1803、1804），讓查詢在走路徑的同時就能回答更多問題。

**與其他 pattern 的關係**。BST 題目幾乎都可以看成第 12 章 binary tree 走訪的特例：由上往下傳參數（區間）、由下往上回傳資訊（333 的最大 BST 子樹）、中序走訪，差別是 BST 讓我們能在每個節點決定只走一邊。BST 的搜尋路徑就是第 8 章 binary search 的樹狀版本，`ceiling` 正是「第一個 True」；但當資料是靜態的，排序陣列加 `bisect` 通常比 BST 更簡單。需要動態有序集合時，Python 中常改用第 26 章的 Fenwick tree 或 segment tree（值域已知），或第 14 章的 heap（只需要最小值時）。Trie 則常和第 19 章的 backtracking（212）、第 21 章的 DP（139、472）、第 28 章的位元運算（421、1707）組合；處理單一 pattern 的字串比對時，第 25 章的 KMP 或 rolling hash 通常比 trie 更合適，而多個 pattern 同時比對一段長文字時，trie 加 failure link 就是 Aho-Corasick。

**容易混淆之處**。第一，「BST 操作是 O(log n)」只在平衡時成立，題目給的 BST 不保證平衡，複雜度要寫 O(h)。第二，只需要精確查詢時，hash set 比 trie 更簡單、更省記憶體；trie 的優勢只在前綴、逐字元推進、萬用字元與位元貪婪。第三，「找第 k 小」在 BST 上用中序，在兩個排序陣列或乘法表上用第 8 章的計數二分，在資料流上用第 14 章的 heap；三者看起來相似，但前提完全不同。第四，驗證 BST 只比較父子是最常見的錯誤，任何「由上往下」的 BST 檢查都要傳遞整條祖先路徑濃縮成的區間。

## 本章重點整理

- BST 有三種等價定義：局部（左 < 根 < 右且子樹都是 BST）、區間（每個節點落在祖先給的開區間內）、中序（中序嚴格遞增）；選對定義，題目就變簡單。
- 所有 BST 操作都是 O(h)，平衡時才是 O(log n)；依序插入會退化成鏈，Python 中要用迭代避免遞迴深度限制。
- 驗證 BST 要傳遞 `(low, high)` 區間，用 `None` 表示沒有限制；只比較父子是錯的，允許重複值時中序檢查也不夠。
- 迭代中序可以隨時停下，第 k 小是 O(h + k)；頻繁修改又頻繁查詢時，節點存子樹大小讓第 k 小變成 O(h)。
- 刪除有兩個子節點的節點時，用中序後繼（右子樹最左節點）的值覆蓋，再刪除後繼；後繼沒有左子節點，只剩簡單情況。
- Trie 的兩個 invariant：節點存在 ⇔ 有單字以此前綴開頭；`is_end` ⇔ 這個前綴本身是單字。查詢絕不建立節點。
- Trie 的每個操作是 O(L)，與字典大小無關；它勝過 hash set 的地方是前綴、逐字元推進、萬用字元、同時推進很多單字。
- 萬用字元 `.` 讓 trie 查詢變成 DFS：普通字元走一條邊，`.` 展開所有子節點，結尾還要檢查是否為單字。
- Word Search II 讓 DFS 同時走網格與 trie；找到單字就取出、回溯時刪除空節點，是兩個安全且關鍵的優化。
- 需要同時滿足多個字串條件時，嘗試用分隔符把條件串成一個前綴（745 的 `後綴 + "{" + 單字`）。
- Binary trie 從最高位貪婪求最大 XOR，因為 2^b 大於所有低位之和；帶 ≤ m 限制時，離線依 m 排序讓可用集合只增不減，或在節點存子樹最小值。
- 串接字問題依長度排序，讓字典只含更短的字串，「至少兩段、不能用自己」自動成立；再用 trie 加速 word break 的 DP。
- 修復被交換的 BST：中序中的第一個下降取前者、最後一個下降取後者；Morris traversal 讓中序走訪只用 O(1) 額外空間，但必須走完才能拆掉所有線索。
