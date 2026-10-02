---
chapter: 11
title: Linked List
part: 1
---

# 第 11 章　Linked List

> [!abstract] 本章地圖
> **一句話**：linked list（鏈結串列）題考的不是聰明的演算法，而是在不能隨機存取、通常要求 O(1) 額外空間的限制下，用兩三個指標加上清楚的 invariant，把「反轉、找中點／倒數第 k 個、合併」這三個基本零件正確地拼起來。
>
> **辨識訊號**：
> - 輸入是 `ListNode`，題目要求「原地」或 O(1) 額外空間
> - 要改變節點順序：反轉、每 k 個一組反轉、重排、旋轉
> - 需要中點、倒數第 k 個、或判斷有沒有環，卻不知道長度
> - 合併、拆分、排序多條 list，或要刪除某些節點而頭節點也可能被刪
> - 節點帶有額外指標（random、child），要深複製
>
> **核心題**：206、21、141（含 142）、19、143
>
> **難題**：25、23、138、148、1171

## 11.1 這個 Pattern 解決什麼問題

先看一個最小的例子：把 `1 → 2 → 3 → 4 → 5` 反轉成 `5 → 4 → 3 → 2 → 1`。最直覺的做法是把所有值倒進 Python list，反轉後再寫回節點，或乾脆建一條新的 list。這樣時間 O(n) 沒問題，但多用了 O(n) 空間；而面試官出 linked list 題時，幾乎都會接著問「能不能 O(1) 空間」。要做到這件事，就只能在原本的節點上改 `next` 指標，而每改一次指標，都可能讓後面的節點「失聯」：`1.next` 一旦指向 `None`，如果沒有先記住 `2`，後面四個節點就再也找不回來。

這就是 linked list 題目真正困難的地方。陣列可以用索引隨時跳到任何位置，所以陣列題的難點通常在演算法；linked list 只能從頭一個一個往後走，而且改指標是不可逆的破壞性操作，所以難點在於**每一步的指標改寫順序**。一個 off-by-one 或少存一個指標，結果就是斷鏈、成環，或是回傳錯的頭節點。面試官看的不是你知不知道「反轉 linked list」，而是你能不能在白板上一次寫對、並說清楚每個指標代表什麼。

好消息是，幾乎所有 linked list 題目都由三個零件組合而成。第一是**反轉**（prev／cur／nxt 三指標），第二是**快慢指標**（slow 走一步、fast 走兩步，用來找中點、判斷環；或讓 fast 先走 k 步，找倒數第 k 個），第三是**合併／接線**（用 dummy 節點與 tail 指標，把節點一個個接到新的 list 尾端）。再加上一個技巧：**dummy node（哨兵節點）**，在頭節點前面多放一個假節點，讓「刪除頭節點」「插入到最前面」不再需要特判。

本章的題目就是這三個零件的組合練習。核心題 1、2、3、4 各自是一個零件的標準形；核心題 5（143）是「找中點 ＋ 反轉 ＋ 交錯合併」的第一個組合題；難題 1（25）把反轉做成分段；難題 2（23）把合併推廣到 k 條；難題 4（148）把找中點和合併遞迴組成 merge sort；難題 3（138）與難題 5（1171）則分別用 hash map 與 prefix sum 協助處理指標。

## 11.2 辨識訊號

| 題目特徵 | 為什麼是這個 pattern | 本章哪一題 |
|---|---|---|
| 反轉整條 list 或其中一段，要求 O(1) 空間 | prev／cur／nxt 三指標原地改 `next` | 核心題 1（206）、難題 1（25） |
| 合併兩條（或多條）已排序的 list | dummy ＋ tail 接線，每次接上較小的節點 | 核心題 2（21）、難題 2（23） |
| 判斷有沒有環、找環的入口，要求 O(1) 空間 | Floyd 快慢指標：有環必相遇，再用距離關係找入口 | 核心題 3（141／142） |
| 倒數第 k 個節點、只能掃一次 | 前後指標保持固定間距 k | 核心題 4（19） |
| 首尾交錯、回文檢查、需要「後半段倒著走」 | 找中點 → 反轉後半 → 兩條一起走 | 核心題 5（143） |
| 排序 linked list，要求 O(n log n) | 不能隨機存取，quicksort／heapsort 不自然；merge sort 只需要順序走訪 | 難題 4（148） |
| 節點有額外指標（random），要深複製 | 舊節點 → 新節點的對應關係；或把新節點交錯插入原 list | 難題 3（138） |
| 刪除「和為 0 的連續區段」 | 連續區段和 ⇔ 兩個 prefix sum 之差；用 hash map 記錄 prefix sum 對應的節點 | 難題 5（1171） |

反向檢查：如果題目允許 O(n) 額外空間、又沒有要求原地修改，很多 linked list 題可以直接轉成陣列處理，面試時可以先說這個做法當基準，再說「我想做到 O(1) 空間」。另外，題目若是「設計一個 O(1) 刪除與移到最前面的結構」（例如 LRU Cache），用的是雙向 linked list ＋ hash map，屬於第 27 章的資料結構設計。

## 11.3 模板與原理：dummy node 與三個基本零件

本章所有程式都使用同一個節點定義與兩個測試工具：`build` 把 Python list 轉成 linked list，`to_list` 把 linked list 轉回 Python list，這樣就能用 `assert to_list(f(build([...]))) == [...]` 寫測試。面試時也建議先寫好這兩個小工具，手動測試會快很多。

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    """由 Python list 建立 linked list，回傳 head；空 list 回傳 None。"""
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head, limit=10**6):
    """把 linked list 轉回 Python list；limit 防止有環時無窮迴圈。"""
    out = []
    while head is not None and len(out) < limit:
        out.append(head.val)
        head = head.next
    assert head is None, "list 太長或有環"
    return out


def reverse(head):
    """零件一：反轉。invariant：prev 是已處理前綴的反轉，cur 是尚未處理的後綴。"""
    prev, cur = None, head
    while cur:
        nxt = cur.next      # 先記住後綴，等一下才不會失聯
        cur.next = prev     # 把 cur 接到已反轉部分的最前面
        prev, cur = cur, nxt
    return prev


def first_middle(head):
    """零件二：快慢指標。偶數長度回傳前半的最後一個節點，適合「切成兩半」。"""
    slow = fast = head
    while fast and fast.next and fast.next.next:
        slow = slow.next
        fast = fast.next.next
    return slow


def second_middle(head):
    """偶數長度回傳後半的第一個節點（876. Middle of the Linked List 的定義）。"""
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow


def merge(a, b):
    """零件三：dummy ＋ tail 接線，合併兩條排序 list。"""
    dummy = tail = ListNode()
    while a and b:
        if a.val <= b.val:
            tail.next, a = a, a.next
        else:
            tail.next, b = b, b.next
        tail = tail.next
    tail.next = a or b      # 剩下的整段直接接上，不必一個個搬
    return dummy.next


def remove_all(head, x):
    """dummy node 的用途：刪除所有值為 x 的節點，頭節點被刪也不必特判。"""
    dummy = ListNode(0, head)
    prev = dummy
    while prev.next:
        if prev.next.val == x:
            prev.next = prev.next.next   # 刪除後 prev 不前進，下一個也可能要刪
        else:
            prev = prev.next
    return dummy.next


assert to_list(build([])) == [] and to_list(build([1, 2])) == [1, 2]
assert to_list(reverse(build([1, 2, 3, 4, 5]))) == [5, 4, 3, 2, 1]
assert reverse(None) is None
assert to_list(reverse(build([7]))) == [7]
assert [first_middle(build(list(range(n)))).val for n in (1, 2, 3, 4, 5)] == [0, 0, 1, 1, 2]
assert [second_middle(build(list(range(n)))).val for n in (1, 2, 3, 4, 5)] == [0, 1, 1, 2, 2]
assert to_list(merge(build([1, 4, 6]), build([2, 3, 7, 9]))) == [1, 2, 3, 4, 6, 7, 9]
assert to_list(merge(None, build([1]))) == [1] and merge(None, None) is None
assert to_list(remove_all(build([6, 6, 1, 6, 2, 6]), 6)) == [1, 2]
assert remove_all(build([3, 3]), 3) is None
print("all tests passed")
```

**反轉的 invariant**。迴圈中任何時刻，原本的 list 被切成兩條互不相交的 list：`prev` 開頭的是「已經處理過的前綴，順序已反轉」，`cur` 開頭的是「還沒碰過的後綴，順序不變」。每一步把 `cur` 從後綴拿下來、放到前綴的最前面，兩條 list 的性質都不變；當 `cur` 變成 `None`，後綴是空的，`prev` 就是整條反轉後的 list。四行裡的順序不能換：`nxt = cur.next` 必須最先，因為下一行就會覆蓋掉 `cur.next`。

**快慢指標的兩種中點**。fast 每次走兩步、slow 走一步，所以 fast 走到尾端時 slow 剛好在一半。差別在停止條件：`while fast and fast.next` 讓 fast 停在最後一個節點或 `None`，偶數長度時 slow 落在**第二個**中點；`while fast.next and fast.next.next` 讓 fast 停在最後一個或倒數第二個節點，slow 落在**第一個**中點。要把 list 切成兩半（143、148、回文檢查）時用第一個中點，因為切點 `slow.next = None` 之後前半的長度是 ⌈n/2⌉、後半是 ⌊n/2⌋，兩邊都不會是空的（n ≥ 2 時）；如果用第二個中點，n = 2 時 slow 會停在第二個節點，你得另外記住它的前一個節點才能切開。

**dummy node 的價值**。凡是「頭節點可能改變」的操作（刪除可能刪到頭、合併後的頭不知道是誰、反轉一段可能從頭開始），都在前面放一個 `dummy`，所有節點就都有「前一個節點」，同一段程式處理所有位置，最後回傳 `dummy.next`。`remove_all` 中刪除之後 `prev` 不前進，因為新的 `prev.next` 還沒檢查過；這是刪除類題目最常見的 bug 來源。

**為什麼 `tail.next = a or b` 是 O(1)**。合併到其中一條用完時，另一條剩下的部分本來就是排好序、而且已經串好的，直接把整段接在 `tail` 後面即可。這是 linked list 相對陣列的優勢：陣列合併要把剩下的元素一個個複製，linked list 只改一個指標。

## 11.4 指標改寫的畫圖方法與遞迴的代價

linked list 題目寫錯，幾乎都是因為在腦中想像指標。比較穩的做法是：**每改一個 `next` 之前，先問「這個指標原本指向的東西，之後還需要嗎？」需要就先存起來**。畫圖時把每個變數名寫在它指向的節點上方，每執行一行就重畫受影響的箭頭。下面是在 `pre` 之後插入節點 `x` 的兩種寫法，順序錯了就會斷鏈：

```text
目標：在 pre 與 B 之間插入 x
  pre → B → C

正確順序                         錯誤順序
1. x.next = pre.next             1. pre.next = x
   pre → B → C                      pre → x        B → C（B 失聯了）
          ↑                         x.next = pre.next 會讓 x 指向自己
   x ─────┘
2. pre.next = x
   pre → x → B → C
```

原則是**先接新的、再斷舊的**：新節點先指向後面，再讓前面指向新節點。刪除則相反，只需要一行 `pre.next = pre.next.next`，但前提是你手上有被刪節點的**前一個**節點，這也是為什麼刪除類題目一定要用 dummy，並且讓指標停在目標的前一格。

**遞迴寫法的代價**。很多 linked list 操作都有漂亮的遞迴寫法（反轉、合併、每 k 個反轉），但遞迴深度等於 list 長度，空間是 O(n)。在 Python 中還有一個更實際的問題：預設遞迴深度上限約 1000，而 LeetCode 這類題目的 n 常常到 5000 或 10⁴，遞迴版會直接丟出 `RecursionError`。面試時可以先寫遞迴版說明思路，但要主動提到這個限制，並能改寫成迭代版；不要用 `sys.setrecursionlimit` 硬撐，因為深度太大時可能讓整個程序因 C stack 溢位而崩潰。

```python
import sys


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def length_recursive(head):
    return 0 if head is None else 1 + length_recursive(head.next)


def length_iterative(head):
    n = 0
    while head:
        n, head = n + 1, head.next
    return n


assert length_recursive(build(range(500))) == length_iterative(build(range(500))) == 500
assert length_iterative(build(range(5000))) == 5000
try:
    length_recursive(build(range(5000)))      # 深度 5000 超過預設上限
    raise AssertionError("預期 RecursionError")
except RecursionError:
    pass
assert sys.getrecursionlimit() < 5000
print("all tests passed")
```

## 11.5 快慢指標與前後指標：兩種「距離」技巧

快慢指標有兩種用法，容易混在一起。**速度差**（slow 一步、fast 兩步）利用的是「fast 走過的距離永遠是 slow 的兩倍」：fast 到尾端時 slow 在中點；如果有環，兩者在環內的距離每一步縮小 1，所以一定會相遇。**間距固定**（兩個指標速度相同，但 fast 先出發 k 步）利用的是「兩者的距離永遠是 k」：fast 到尾端時 slow 就在倒數第 k 個附近。前者用在核心題 3（141／142）與找中點，後者用在核心題 4（19）與 61. Rotate List。

```text
速度差：找中點（n = 5）              間距固定：倒數第 2 個（n = 5，k = 2）
步  slow  fast                        fast 先走 2 步
0    1     1                          slow=1 fast=3
1    2     3                          slow=2 fast=4
2    3     5   fast.next 為 None 停    slow=3 fast=5
→ 中點 3                              slow=4 fast=None 停 → 倒數第 2 個是 4
```

兩種技巧的共同點是：**不知道長度也能一次走完**。不過面試官通常也接受「先算長度、再走第二次」的兩次掃描，時間同樣是 O(n)；一次掃描的優點只在資料是串流、或走訪本身很貴（例如每個節點在不同機器上）的時候才明顯。面試時把兩種都講出來、說明取捨，比堅持一次掃描更好。

## 11.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 改 `cur.next` 之前沒有先存 `nxt` | 後半段節點失聯，回傳的 list 只剩一兩個節點 | 改寫任何 `next` 之前，先問原本指向的節點之後還要不要用 |
| 頭節點可能被刪或改變，卻沒有用 dummy | 刪除第一個節點時回傳舊的 head，或需要一堆 `if` 特判 | 只要 head 可能變，一律 `dummy = ListNode(0, head)`，回傳 `dummy.next` |
| 刪除後指標照常前進 | 連續兩個要刪的節點只刪掉一個 | 刪除時 `prev` 不動，只有保留節點時才 `prev = prev.next` |
| 切成兩半時忘了 `mid.next = None` | 前半段仍連著後半段，合併或比較時形成環、無窮迴圈 | 找到第一個中點後立刻切開：`second = mid.next; mid.next = None` |
| 中點用錯版本 | n = 2 時切不開，或後半比前半多一個導致交錯合併出錯 | 要切開時用 `while fast.next and fast.next.next` 的第一個中點 |
| 迴圈條件少檢查一層 | `fast.next.next` 在 `fast` 為 `None` 時 AttributeError | 條件由左到右短路：`fast and fast.next`，順序不能顛倒 |
| 反轉一段後沒接回前後 | 反轉的那段正確，但整條 list 斷成兩截 | 反轉前先記住段落前一個節點與段落後一個節點，反轉後兩端都要接 |
| 遞迴寫法用在長 list | Python 在 n 約 1000 以上丟出 `RecursionError` | 說明遞迴深度 O(n)，最終答案改成迭代 |
| heap 裡放 `(val, node)` | 值相同時 Python 比較 `ListNode`，丟出 TypeError | 放 `(val, idx, node)`，用索引當平手時的比較依據 |
| 比較節點用 `==` 比值 | 環檢測或判斷相交時，值相同的不同節點被當成同一個 | 判斷「同一個節點」用 `is`；只有比較內容時才用 `.val ==` |

## 核心題 1｜206. Reverse Linked List｜Easy

### 題目

給一條單向 linked list 的頭節點 `head`，把整條 list 反轉，回傳反轉後的頭節點。必須重複使用原本的節點（改 `next` 指標），不要建立新的節點。限制：節點數在 0 到 5000 之間，節點值在 `-5000` 到 `5000` 之間。題目也要求能說出迭代與遞迴兩種寫法。

- 範例 1：`1 → 2 → 3 → 4 → 5`，回傳 `5 → 4 → 3 → 2 → 1`。
- 範例 2：`1 → 2`，回傳 `2 → 1`。
- 範例 3（邊界）：空 list，回傳 `None`；只有一個節點 `7`，回傳它自己。

### 思路

暴力解是把所有值讀進 Python list，再從頭把值倒著寫回節點，或用一個 stack 依序推入節點、再逐一彈出重新串接。兩種都是 O(n) 時間、O(n) 空間。它們的瓶頸不在時間，而在空間：我們需要額外的容器，只是因為 linked list 不能從尾巴往回走。

關鍵觀察是：反轉不需要「往回走」，只需要讓每個節點的 `next` 改指向它原本的前一個節點。從頭走到尾時，前一個節點我們剛剛經過，用一個變數 `prev` 記住就好；唯一的危險是改了 `cur.next` 之後就找不到下一個節點，所以要先用 `nxt` 存起來。於是每一步做四件事：存 `nxt`、把 `cur.next` 指向 `prev`、`prev` 前進到 `cur`、`cur` 前進到 `nxt`。

正確性用 11.3 節的 invariant 說明：`prev` 是已處理前綴的反轉，`cur` 是未處理的後綴，兩者互不相交，而且兩者合起來包含所有節點。一開始前綴是空的（`prev = None`），後綴是整條 list；每一步把後綴的第一個節點移到前綴的最前面；結束時後綴為空，前綴就是答案。注意原本的頭節點會變成尾巴，它的 `next` 在第一步就被設成 `None`，所以不需要額外處理尾端。

遞迴寫法換個角度：假設 `reverse(head.next)` 已經把後面的部分反轉好，並回傳新的頭（原本的尾巴）；此時 `head.next` 仍然指向原本的第二個節點，而它現在是反轉後部分的尾巴，所以 `head.next.next = head` 把 head 接到尾巴後面，再 `head.next = None` 讓 head 成為新的尾巴。遞迴深度是 n，空間 O(n)，n = 5000 時在 Python 會超過預設遞迴上限（見 11.4 節）。

```text
初始     prev = None          cur = 1 → 2 → 3 → None

步驟 1   nxt = 2；1.next = None
         prev = 1 → None      cur = 2 → 3 → None

步驟 2   nxt = 3；2.next = 1
         prev = 2 → 1 → None  cur = 3 → None

步驟 3   nxt = None；3.next = 2
         prev = 3 → 2 → 1 → None    cur = None

結束     回傳 prev，也就是節點 3
```

每一步結束時，上方的 `prev` 那條永遠是「已經反轉好的部分」，下方 `cur` 那條永遠是「原封不動的部分」。第 1 步把 1 的 `next` 改成 `None`，原本的頭就成了最後的尾巴；第 3 步之後 `cur` 是 `None`，迴圈結束。整個過程只用了三個變數，而且每個節點的 `next` 只被改寫一次。

### 解法

```python
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def reverse_list(head):
    prev, cur = None, head
    while cur:
        nxt = cur.next
        cur.next = prev
        prev, cur = cur, nxt
    return prev


def reverse_list_recursive(head):
    if head is None or head.next is None:
        return head
    new_head = reverse_list_recursive(head.next)
    head.next.next = head      # head.next 現在是反轉後部分的尾巴
    head.next = None
    return new_head


assert to_list(reverse_list(build([1, 2, 3, 4, 5]))) == [5, 4, 3, 2, 1]
assert to_list(reverse_list(build([1, 2]))) == [2, 1]
assert reverse_list(None) is None
assert to_list(reverse_list(build([7]))) == [7]
nodes = build([1, 2, 3])
second = nodes.next
assert reverse_list(nodes).next is second            # 重複使用原本的節點
assert to_list(reverse_list(build(range(5000)))) == list(range(4999, -1, -1))
for _ in range(300):
    arr = [random.randint(-5, 5) for _ in range(random.randint(0, 30))]
    assert to_list(reverse_list(build(arr))) == arr[::-1]
    assert to_list(reverse_list_recursive(build(arr))) == arr[::-1]
print("all tests passed")
```

### 複雜度與邊界

迭代版時間 O(n)，每個節點被訪問一次、`next` 改寫一次；空間 O(1)，只有三個指標。遞迴版時間 O(n)、空間 O(n)（呼叫堆疊），在 Python 中 n 超過約 1000 就會 `RecursionError`，所以最終答案應該給迭代版。邊界情況：空 list 時迴圈不執行，回傳 `prev = None`；單一節點時迴圈執行一次，`next` 被設為 `None`（本來就是），回傳它自己；遞迴版的終止條件必須同時檢查 `head is None`（空 list）與 `head.next is None`（走到尾巴），少了前者會在空 list 上存取 `None.next`。

### Follow-up

> [!question]- F1. 如果只反轉第 left 到第 right 個節點呢（92. Reverse Linked List II）？
> 用 dummy 接在 head 前面，讓 `pre` 走到第 left − 1 個節點（left = 1 時就是 dummy）。之後用「頭插法」：令 `cur = pre.next`，重複 right − left 次把 `cur.next` 那個節點拿出來、插到 `pre` 後面。每次插入後 `cur` 都往後退一格，但 `cur` 這個節點本身始終是反轉段的尾巴，所以最後不需要另外接回後半段。一次掃描、時間 O(right)、空間 O(1)。
> ```python
> def reverse_between(head, left, right):
>     dummy = ListNode(0, head)
>     pre = dummy
>     for _ in range(left - 1):
>         pre = pre.next
>     cur = pre.next
>     for _ in range(right - left):
>         move = cur.next
>         cur.next = move.next
>         move.next = pre.next
>         pre.next = move
>     return dummy.next
> ```

> [!question]- F2. 怎麼用 O(1) 空間判斷 linked list 是不是回文（234. Palindrome Linked List）？
> 用快慢指標找第一個中點 `mid`，把 `mid.next` 開頭的後半段反轉，然後從 head 和反轉後的後半段同時往後比對值；後半段長度是 ⌊n/2⌋，比完它就結束（奇數長度時正中間的節點不必比）。時間 O(n)、空間 O(1)。好的回答會主動補一句：比對完要把後半段再反轉一次接回 `mid.next`，因為呼叫端通常不希望輸入被修改；如果是多執行緒共用的 list，原地修改期間其他讀者會看到壞掉的結構，這時只能改用 O(n) 空間的做法。

> [!question]- F3. 如果是雙向 linked list 呢？
> 每個節點同時有 `prev` 與 `next`，反轉就是把每個節點的這兩個指標互換。走訪時要先記住原本的 `next`，因為交換後 `node.next` 已經變成原本的前一個；最後一個處理的節點就是新的頭。時間 O(n)、空間 O(1)。如果結構還維護了 `head` 與 `tail` 兩個欄位，交換這兩個欄位就完成了。若只需要「倒著走訪」而不是真的反轉，雙向 list 根本不需要修改，直接從 `tail` 沿 `prev` 走即可。

> [!question]- F4. 如果不能修改 list，要倒序印出所有值，而且希望額外空間比 O(n) 少呢？
> 最簡單的是 stack 或遞迴，O(n) 時間、O(n) 空間；完全不用額外空間的做法是每次從頭走到「上次印出位置的前一個」，O(n²) 時間、O(1) 空間。折衷做法是 √n 分塊：先走一次，每隔 √n 個節點記一個檢查點（共 √n 個）；再從最後一個檢查點開始，把該塊的 √n 個值推入 stack 後倒序印出，一塊塊往前處理。每個節點只被額外走一次，總時間 O(n)、空間 O(√n)。面試官問這題時，想看的是你能在時間與空間之間做取捨，而不是只會一種答案。

## 核心題 2｜21. Merge Two Sorted Lists｜Easy

### 題目

給兩條各自以非遞減順序排列的 linked list `list1` 和 `list2`，把它們合併成一條非遞減的 linked list 並回傳頭節點。合併後的 list 必須由原本兩條 list 的節點接起來（不要建立新的值節點）。限制：每條 list 的節點數在 0 到 50 之間，節點值在 `-100` 到 `100` 之間。

- 範例 1：`list1 = 1 → 2 → 4`、`list2 = 1 → 3 → 4`，回傳 `1 → 1 → 2 → 3 → 4 → 4`。
- 範例 2：`list1 = 5`、`list2 = 1 → 2 → 3`，回傳 `1 → 2 → 3 → 5`（一條比另一條全部小）。
- 範例 3（邊界）：兩條都是空的，回傳 `None`；`list1` 空、`list2 = 0`，回傳 `0`。

### 思路

暴力解是把兩條 list 的所有值讀出來、排序、再建一條新 list，時間 O((m + n) log(m + n))，空間 O(m + n)，而且建立了新節點，不符合題目要求。這個做法浪費在兩個地方：沒有利用「兩條都已排序」這個資訊，以及沒有利用「linked list 可以直接搬動節點」這個特性。

關鍵觀察和 merge sort 的合併步驟一樣：合併後的第一個節點，一定是兩條 list 的頭之中較小的那個；把它拿走之後，剩下的問題是「合併兩條排序 list」，規模少了 1。所以只要維護兩個指標 `a`、`b` 指向兩條 list 目前的頭，每次比較、把較小的接到結果的尾端、該指標前進即可。為了避免「結果的第一個節點是誰」需要特判，用一個 dummy 節點當結果的起點，`tail` 永遠指向結果的最後一個節點。

Invariant：`dummy.next` 到 `tail` 是目前為止合併好的部分，它已經排序，而且其中每個值都 ≤ `a` 和 `b` 剩下的所有值。每一步接上 `min(a.val, b.val)`，invariant 保持。當其中一條用完，另一條剩下的部分全都 ≥ 已合併的部分，而且本身已排序、已串好，所以一行 `tail.next = a or b` 就完成，不必逐個搬動。

值相等時取 `a`（`a.val <= b.val`），這讓合併是**穩定的**：相同值的節點保持「先 list1、後 list2」的相對順序。這在本題沒有差別，但在難題 4（148）用合併做排序時，穩定性就是 merge sort 的重要性質，習慣寫 `<=` 能避免日後踩雷。

```text
a: 1 → 2 → 4          b: 1' → 3 → 4'        （' 標記來自 list2 的節點）

步驟  a    b    比較       接上   結果（dummy 之後）
 1    1    1'   1 <= 1'    1      1
 2    2    1'   2 >  1'    1'     1 → 1'
 3    2    3    2 <= 3     2      1 → 1' → 2
 4    4    3    4 >  3     3      1 → 1' → 2 → 3
 5    4    4'   4 <= 4'    4      1 → 1' → 2 → 3 → 4
 6    None 4'   a 用完     整段接上 b：1 → 1' → 2 → 3 → 4 → 4'
```

第 1 步兩個頭都是 1，因為用 `<=` 所以先取 list1 的 1；第 6 步 `a` 已經是 `None`，迴圈結束，`tail.next = b` 一次接上剩下的 `4'`（如果 b 剩下一萬個節點，也只是一次指標賦值）。整個過程沒有建立任何新的值節點，只有一個 dummy。

### 解法

```python
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def merge_two_lists(a, b):
    dummy = tail = ListNode()
    while a and b:
        if a.val <= b.val:
            tail.next, a = a, a.next
        else:
            tail.next, b = b, b.next
        tail = tail.next
    tail.next = a or b
    return dummy.next


def merge_two_lists_recursive(a, b):
    if a is None or b is None:
        return a or b
    if a.val <= b.val:
        a.next = merge_two_lists_recursive(a.next, b)
        return a
    b.next = merge_two_lists_recursive(a, b.next)
    return b


assert to_list(merge_two_lists(build([1, 2, 4]), build([1, 3, 4]))) == [1, 1, 2, 3, 4, 4]
assert to_list(merge_two_lists(build([5]), build([1, 2, 3]))) == [1, 2, 3, 5]
assert merge_two_lists(None, None) is None
assert to_list(merge_two_lists(None, build([0]))) == [0]
x, y = build([1]), build([1])
assert merge_two_lists(x, y) is x                     # 相等時先取 list1，合併是穩定的
for _ in range(300):
    p = sorted(random.randint(-9, 9) for _ in range(random.randint(0, 8)))
    q = sorted(random.randint(-9, 9) for _ in range(random.randint(0, 8)))
    assert to_list(merge_two_lists(build(p), build(q))) == sorted(p + q)
    assert to_list(merge_two_lists_recursive(build(p), build(q))) == sorted(p + q)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m + n)：每次迴圈接上一個節點，最多 m + n 次，最後剩下的部分 O(1) 接上。空間 O(1)，只有 dummy 與幾個指標；遞迴版的空間是 O(m + n)，因為每接一個節點就多一層呼叫。邊界情況：任一條為空時迴圈不執行，直接回傳另一條；兩條都空時 `a or b` 是 `None`，回傳 `dummy.next = None`；值相等時用 `<=` 保持穩定；有負數或重複值不影響，因為只做比較。

### Follow-up

> [!question]- F1. 如果兩條 list 一條遞增、一條遞減，要合併成遞增呢？
> 先把遞減的那條用核心題 1 的方法反轉成遞增，O(n) 時間、O(1) 空間，再照原題合併，總共 O(m + n)。另一種做法是如果要的是遞減結果，可以直接合併「從大到小」：反轉遞增的那條，然後每次取較大者。重點是說出「反轉是 O(1) 空間的，所以方向不一致只是多一次線性掃描」。若兩條都是遞減而要遞增輸出，也可以照常以「取較大者」合併成遞減 list，再整條反轉一次。

> [!question]- F2. 如果合併時要去除重複值，只保留一份呢（兩個排序集合的聯集）？
> 在接上節點前檢查 `tail is not dummy and tail.val == 候選.val`，相同就跳過那個節點（只讓該指標前進，不接上）。因為兩條 list 都已排序，所有相同的值會連續出現在合併序列中，只要和結果的最後一個值比較就夠。剩下的尾段不能再用一行接上，因為裡面可能還有與 `tail` 或彼此相同的值，要用同樣的檢查逐一處理。時間仍是 O(m + n)、空間 O(1)。若要的是交集，就在兩值相等時才接上，不相等時讓較小者前進。

> [!question]- F3. 為什麼遞迴版本不適合當最終答案？
> 遞迴版每接上一個節點就多一層呼叫，深度是 m + n，空間 O(m + n)；本題 m、n ≤ 50 不會出事，但若面試官把限制改成 10⁵，Python 的預設遞迴上限（約 1000）會直接 `RecursionError`。遞迴版的優點是短，而且非常直觀地表達了「取較小的頭，剩下的遞迴合併」；面試時可以先口頭描述遞迴想法，寫程式時用迭代版，並說明這個取捨。這也是第 12 章樹的遞迴與 linked list 遞迴的差別：平衡的樹深度是 O(log n)（退化成一條鏈的樹仍是 O(n)），linked list 的深度則一定是 O(n)。

> [!question]- F4. 如果有 k 條排序 list 要合併呢？
> 逐條合併（先合併第 1、2 條，結果再和第 3 條合併……）的時間是 O(k · N)，N 是總節點數，因為前面合併好的長串會被反覆走訪。正確做法有兩種：用 min-heap 同時放 k 條 list 的頭，每次取出最小的接上並推入它的下一個，O(N log k)；或兩兩配對合併，共 log k 輪、每輪 O(N)，同樣 O(N log k)。這就是難題 2（23），也是第 14 章 k-way merge 的基本形。

## 核心題 3｜141. Linked List Cycle｜Easy

### 題目

本題包含兩個連續的問題（141 與 142）。給一條 linked list 的頭節點 `head`，其中最後一個節點的 `next` 可能指回 list 中某個節點，形成一個環（cycle）；測資用參數 `pos` 表示尾巴接回第幾個節點（0-indexed），`pos = -1` 表示沒有環，但 `pos` 不會傳給你的函式。

- **141**：判斷 list 是否有環，回傳 `True` 或 `False`。
- **142**：若有環，回傳環的**入口節點**（從 head 出發第一個進入環的節點）；沒有環則回傳 `None`。不能修改 list。

兩題的進階要求都是 O(1) 額外空間。限制：節點數在 0 到 10⁴ 之間，節點值在 `-10⁵` 到 `10⁵` 之間（值可能重複，所以不能用值判斷是不是同一個節點）。

- 範例 1：`3 → 2 → 0 → -4`，`pos = 1`（`-4` 接回 `2`），141 回傳 `True`，142 回傳值為 2 的節點。
- 範例 2：`1 → 2`，`pos = 0`，有環，入口是值為 1 的節點（也就是 head）。
- 範例 3（邊界）：`1`，`pos = -1`，回傳 `False`／`None`；空 list 也一樣。單一節點自己指向自己（`pos = 0`）時有環，入口是它自己。

### 思路

暴力解是用一個 set 記錄走過的節點（存節點本身，不是值），走到一個已經在 set 裡的節點就代表有環，而且這個節點正是環的入口，因為它是第一個被「第二次」走到的節點；走到 `None` 就代表沒有環。時間 O(n)、空間 O(n)。這個做法完全正確，面試時應該先說它；瓶頸只在空間。

要把空間降到 O(1)，關鍵觀察是 Floyd 的龜兔賽跑：slow 每次走一步、fast 每次走兩步。如果沒有環，fast 會先走到 `None`；如果有環，兩者最終都會進入環並在環上繞圈，而 fast 每一步都比 slow 多走一步，也就是在環上「追近一格」，所以 fast 一定會在某一步剛好追上 slow，不會跳過去（每次只追近 1，距離從 d 變成 d − 1，不可能從 1 直接跳到 −1）。這解決了 141。

142 需要一個距離關係。令 `a` 是 head 到入口的距離、`c` 是環長。第 t 步時 slow 走了 t 步、fast 走了 2t 步；兩者在第 t 步相遇，代表 t ≥ a（都已經進環）且多走的 t 步剛好是環長的整數倍：**t ≡ 0 (mod c)**。換句話說，相遇時 slow 從 head 走了 t 步，而 t 是 c 的倍數。現在讓一個指標從 head 出發、另一個從相遇點出發，兩者每次各走一步：走了 a 步之後，第一個指標剛好在入口；第二個指標從 head 算起總共走了 t + a 步，因為 t 是環長的倍數，它的位置等同於從 head 走 a 步，也就是入口。所以兩者第一次相遇的節點就是入口。

還可以更精確地說出相遇時間：第一次相遇的 t，是「≥ a 的最小正整數、且是 c 的倍數」（a = 0 時是 t = c），所以 t ≤ a + c（只有 a = 0 時取等號），slow 進環後最多走一圈就被追上。這保證第一階段最多走 a + c ≤ n 步，第二階段走 a 步，總時間 O(n)。

```text
節點索引：0 → 1 → 2 → 3 → 4 → 5 → 6 → 7
                    ↑                   │
                    └───────────────────┘   （7 的 next 指回 2）
a = 2（head 到入口 2），c = 6（環：2 3 4 5 6 7）

第一階段：slow 走 1 步、fast 走 2 步
 t   slow  fast
 0    0     0
 1    1     2
 2    2     4
 3    3     6
 4    4     2     （6 → 7 → 2）
 5    5     4
 6    6     6     相遇於 6；t = 6 是 c 的倍數，也是 ≥ a 的最小倍數

第二階段：p 從 head、q 從相遇點，各走 1 步
 步   p   q
 0    0   6
 1    1   7
 2    2   2     相遇於 2 → 入口
```

第一階段 fast 在 t = 2 就進環了，slow 在 t = 2 進環時兩者在環上的距離是 2 → 4，fast 落後 slow 的距離（沿環往前）是 4 格，之後每一步縮小 1，所以 4 步後（t = 6）相遇。第二階段 p 要走 a = 2 步才到入口；q 從 6 出發走 2 步經過 7 回到 2，兩者剛好在入口會合。

### 解法

```python
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build_cycle(values, pos):
    """建立 linked list；pos >= 0 時讓尾巴接回索引 pos 的節點。回傳 (head, 節點陣列)。"""
    nodes = [ListNode(v) for v in values]
    for x, y in zip(nodes, nodes[1:]):
        x.next = y
    if nodes and pos >= 0:
        nodes[-1].next = nodes[pos]
    return (nodes[0] if nodes else None), nodes


def has_cycle(head):                       # 141
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:                   # 比較的是節點本身，不是值
            return True
    return False


def detect_cycle(head):                    # 142
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            p, q = head, slow
            while p is not q:
                p, q = p.next, q.next
            return p
    return None


def detect_cycle_set(head):                # O(n) 空間的基準解
    seen = set()
    while head and head not in seen:
        seen.add(head)
        head = head.next
    return head


head, nodes = build_cycle([3, 2, 0, -4], 1)
assert has_cycle(head) and detect_cycle(head) is nodes[1]
head, nodes = build_cycle([1, 2], 0)
assert has_cycle(head) and detect_cycle(head) is nodes[0]
head, nodes = build_cycle([1], -1)
assert not has_cycle(head) and detect_cycle(head) is None
assert not has_cycle(None) and detect_cycle(None) is None
head, nodes = build_cycle([5], 0)                      # 自己指向自己
assert detect_cycle(head) is nodes[0]
head, nodes = build_cycle([1, 1, 1, 1], 2)             # 值全部相同
assert detect_cycle(head) is nodes[2]
for _ in range(500):
    n = random.randint(0, 15)
    pos = random.randint(-1, n - 1) if n else -1
    head, nodes = build_cycle([random.randint(0, 2) for _ in range(n)], pos)
    expect = nodes[pos] if pos >= 0 else None
    assert detect_cycle(head) is expect is detect_cycle_set(head)
    assert has_cycle(head) == (pos >= 0)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：第一階段 slow 最多走 a + c 步（有環時在進環後一圈內被追上；無環時 fast 走 n/2 次就到尾端），第二階段走 a 步。空間 O(1)。邊界情況：空 list 與單一節點無環時，`fast.next` 為 `None`，迴圈不執行；自己指向自己時，第一步 slow 與 fast 都回到自己，a = 0，第二階段 p 與 q 一開始就相同，直接回傳 head；判斷相遇必須用 `is` 比較節點身分，因為值可能重複（測試中的 `[1, 1, 1, 1]`）；相遇的判斷要放在移動**之後**，否則一開始 `slow is fast`（都在 head）會被誤判為有環。

### Follow-up

> [!question]- F1. 怎麼求環的長度？
> 在第一階段相遇之後，固定一個指標，讓另一個從相遇點出發每次走一步並計數，再次回到相遇點時的步數就是環長 c，額外 O(c) 時間、O(1) 空間。有了 c 也可以用另一種方式找入口：讓一個指標先從 head 走 c 步，再讓第二個指標從 head 出發，兩者同速前進，相遇處就是入口（因為兩者間距固定為 c，前面那個繞完一圈剛好回到後面那個所在的入口）。這其實是核心題 4 的「間距固定」技巧。

> [!question]- F2. 為什麼 fast 走兩步？走三步行不行？
> 只判斷有沒有環的話，走三步也可以：第 t 步時兩者的位置差是 2t，只要 t 是 c 的倍數且 t ≥ a 就會相遇，這樣的 t 一定存在。但走三步有兩個缺點：每一步要多呼叫一次 `next`（還要多檢查一次 `None`），總步數沒有變少；而且第二階段找入口的推導會壞掉，因為相遇條件變成 2t ≡ 0 (mod c)，t 只保證是 c/2 的倍數，從 head 和相遇點同速出發不一定在入口相遇。兩步是讓「相遇時 t 是 c 的倍數」成立的最小選擇，所以是標準做法。

> [!question]- F3. 怎麼找兩條 linked list 的交會節點（160. Intersection of Two Linked Lists）？
> 讓指標 p 走完 A 後接著走 B，q 走完 B 後接著走 A；設 A 獨有部分長 x、B 獨有部分長 y、共同部分長 z，p 走 x + z + y 步、q 走 y + z + x 步後都剛好站在交會點，步數相同所以會同時抵達；沒有交會時兩者都走 len(A) + len(B) 步後同時變成 `None`，迴圈 `while p is not q` 也會結束。時間 O(m + n)、空間 O(1)。另一種做法是把 A 的尾巴暫時接到 B 的頭，交會點就變成這個環的入口，用本題的 142 解出後再把尾巴改回 `None`，但這需要修改輸入，題目不允許時就不能用。

> [!question]- F4. 如果「list」是隱含的，例如 `x → f(x)` 這種函數迭代呢？
> Floyd 演算法只需要「從一個狀態算出下一個狀態」的函數，不需要真的有節點。202. Happy Number 是「數字 → 各位數平方和」的迭代，判斷會不會進入不含 1 的環；第 5 章難題 2（287. Find the Duplicate Number）把陣列看成 `i → nums[i]` 的函數，重複的數字正是環的入口，用 142 的兩階段做法得到 O(n) 時間、O(1) 空間。這類題目的辨識訊號是「狀態空間有限、每個狀態只有一個後繼、要求 O(1) 空間」。

> [!question]- F5. 有沒有比 Floyd 呼叫更少次 next 的方法？
> Brent 演算法：fast 每次走一步，並在步數到達 1、2、4、8… 時把 slow「瞬移」到 fast 的位置；在每個 2 的冪次區間內，若 fast 回到 slow 就找到環，計步數同時得到環長 c。它的 `next` 呼叫次數通常比 Floyd 少（Floyd 每輪要三次 `next`），時間仍是 O(a + c)、空間 O(1)。找入口時用 F1 的方法：先讓一個指標從 head 走 c 步，再同速前進。在函數迭代很昂貴的情境（例如 Pollard's rho 分解質因數）中，Brent 是常見的選擇。

## 核心題 4｜19. Remove Nth Node From End of List｜Medium

### 題目

給一條 linked list 的頭節點 `head` 和整數 `n`，刪除**倒數第 n 個**節點，回傳刪除後的頭節點。保證 `n` 合法：`1 <= n <= 節點數`。限制：節點數 sz 在 1 到 30 之間，節點值在 0 到 100 之間。進階要求是只掃描一次。

- 範例 1：`1 → 2 → 3 → 4 → 5`、`n = 2`，刪除 4，回傳 `1 → 2 → 3 → 5`。
- 範例 2：`1 → 2`、`n = 1`，刪除最後一個節點，回傳 `1`。
- 範例 3（邊界）：`1 → 2`、`n = 2`，刪除的是頭節點，回傳 `2`；`1`、`n = 1`，刪除後是空 list，回傳 `None`。

### 思路

直接的做法是兩次掃描：第一次算出長度 L，倒數第 n 個就是正數第 L − n 個（0-indexed），第二次走到它的前一個節點，把它跳過。時間 O(L)，空間 O(1)，其實已經是最佳複雜度；面試時應該先說這個解。它唯一的「缺點」是要走兩次，而題目的進階要求是一次掃描，背後的動機是：如果 list 是串流、或每走一步都很昂貴，就希望不要先數長度。

一次掃描的關鍵觀察是 11.5 節的「間距固定」：倒數第 n 個節點，和尾端之後的 `None` 之間恰好隔 n 步。如果讓 fast 先走 n 步，再讓 slow 和 fast 同速前進，兩者的距離永遠是 n；當 fast 走到 `None`，slow 就停在倒數第 n 個。但刪除需要的是**前一個**節點，所以讓 fast 多走一步（間距 n + 1），slow 就會停在目標的前一個。

為了處理「刪除的剛好是頭節點」（範例 3），兩個指標都從 dummy 出發。dummy 在 head 前面，這讓頭節點也有「前一個節點」：n 等於長度時，slow 根本不會前進，停在 dummy，`dummy.next = dummy.next.next` 就刪掉了頭節點。最後回傳 `dummy.next`，不必特判。

Invariant：同步前進的每一步，fast 都在 slow 前面 n + 1 步。fast 從 dummy 走 n + 1 步時，因為 n ≤ L，最遠會走到 L + 1 步也就是 `None`，不會越界。當 fast 是 `None` 時，它的位置是「第 L + 1 個」（把 dummy 當第 0 個），slow 的位置是 L + 1 − (n + 1) = L − n，也就是倒數第 n 個節點（位置 L − n + 1）的前一個。

```text
dummy → 1 → 2 → 3 → 4 → 5 → None，n = 2
位置：  0    1   2   3   4   5    6

階段一：fast 從 dummy 先走 n + 1 = 3 步
  slow = dummy(0)   fast = 3

階段二：同步前進，直到 fast 為 None
  步  slow  fast
  1    1     4
  2    2     5
  3    3     None   停止，slow 與 fast 間距仍是 3

刪除：slow.next 是 4（倒數第 2 個）→ slow.next = slow.next.next
  dummy → 1 → 2 → 3 → 5 → None

邊界：1 → 2，n = 2
  fast 從 dummy 走 3 步到 None，slow 停在 dummy
  dummy.next = dummy.next.next → 回傳 2
```

正常情況下 slow 停在 3，剛好是 4 的前一個；邊界情況 n 等於長度時，fast 在第一階段就已經走到 `None`，第二階段一步都不走，slow 停在 dummy，於是刪掉的是 head。兩種情況用同一段程式處理，這就是 dummy 的作用。

### 解法

```python
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def remove_nth_from_end(head, n):
    dummy = ListNode(0, head)
    slow = fast = dummy
    for _ in range(n + 1):          # fast 領先 slow n + 1 步
        fast = fast.next
    while fast:
        slow, fast = slow.next, fast.next
    slow.next = slow.next.next      # slow 是倒數第 n 個的前一個
    return dummy.next


def remove_nth_two_pass(head, n):
    length, cur = 0, head
    while cur:
        length, cur = length + 1, cur.next
    dummy = ListNode(0, head)
    prev = dummy
    for _ in range(length - n):
        prev = prev.next
    prev.next = prev.next.next
    return dummy.next


assert to_list(remove_nth_from_end(build([1, 2, 3, 4, 5]), 2)) == [1, 2, 3, 5]
assert to_list(remove_nth_from_end(build([1, 2]), 1)) == [1]
assert to_list(remove_nth_from_end(build([1, 2]), 2)) == [2]
assert remove_nth_from_end(build([1]), 1) is None
assert to_list(remove_nth_from_end(build([1, 2, 3]), 3)) == [2, 3]
for _ in range(300):
    arr = [random.randint(0, 100) for _ in range(random.randint(1, 30))]
    k = random.randint(1, len(arr))
    expect = arr[:len(arr) - k] + arr[len(arr) - k + 1:]
    assert to_list(remove_nth_from_end(build(arr), k)) == expect
    assert to_list(remove_nth_two_pass(build(arr), k)) == expect
print("all tests passed")
```

### 複雜度與邊界

時間 O(L)：fast 從 dummy 走到 `None` 共 L + 1 步，slow 跟著走 L − n 步。空間 O(1)。一次掃描與兩次掃描的總步數其實差不多（一次掃描版本有兩個指標在走），所以兩者的差別在「能否不知道長度就完成」，而不是速度。邊界情況：n = L 時刪除頭節點，靠 dummy 處理；L = 1 時刪除後回傳 `None`；n = 1 時刪除尾巴，`slow.next.next` 是 `None`，賦值後 slow 成為新的尾巴。題目保證 n 合法；若不保證，`fast = fast.next` 會在 n > L 時對 `None` 取 `.next` 而出錯，見 F1。

### Follow-up

> [!question]- F1. 如果 n 可能超過長度或 n ≤ 0，要怎麼處理？
> 在 fast 先走 n + 1 步的迴圈中檢查：第 i 步之前若 fast 已經是 `None`，代表 n > L，應依需求回傳原 list 不變或丟出 `ValueError`。注意 fast 在第 n + 1 步剛好走到 `None` 是合法的（n = L），所以檢查要放在「取 `.next` 之前」而不是「走完之後」。n ≤ 0 也應在開頭直接拒絕。這類輸入驗證不影響複雜度，但面試時主動問「n 保證合法嗎」是加分的溝通。

> [!question]- F2. 怎麼把 list 往右旋轉 k 次（61. Rotate List）？
> 往右旋轉 k 次等於把倒數 k 個節點搬到最前面。先走一次求長度 L 與尾節點，令 `k %= L`（k 可能遠大於 L，例如 2 × 10⁹，不能真的轉 k 次）；k = 0 時直接回傳。接著把尾巴接回 head 形成環，再從 head 走 L − k − 1 步找到新的尾巴，新頭是它的下一個，最後把新尾巴的 `next` 設為 `None`。時間 O(L)、空間 O(1)。
> ```python
> def rotate_right(head, k):
>     if head is None:
>         return None
>     length, tail = 1, head
>     while tail.next:
>         length, tail = length + 1, tail.next
>     k %= length
>     if k == 0:
>         return head
>     tail.next = head                       # 暫時成環
>     new_tail = head
>     for _ in range(length - k - 1):
>         new_tail = new_tail.next
>     new_head, new_tail.next = new_tail.next, None
>     return new_head
> ```

> [!question]- F3. 如果要刪除的是正中間的節點（2095. Delete the Middle Node，索引 ⌊n/2⌋）呢？
> 刪除需要前一個節點，所以讓 slow 停在中點的前一格：單一節點時直接回傳 `None`；否則 slow 從 head、fast 從 `head.next.next` 出發，`while fast and fast.next` 時兩者分別走一步和兩步，結束後 `slow.next = slow.next.next`。驗證幾個長度：n = 2 時 fast 一開始就是 `None`，刪除索引 1；n = 4 時 slow 走到索引 1，刪除索引 2；n = 5 時同樣刪除索引 2，都符合 ⌊n/2⌋。時間 O(n)、空間 O(1)。這是「速度差」與「停在前一格」兩個技巧的組合。

> [!question]- F4. 如果只給你要刪除的那個節點，不給 head 呢（237. Delete Node in a Linked List）？
> 拿不到前一個節點，就無法真的把這個節點從鏈上拿掉。技巧是把下一個節點的值複製過來，再刪掉下一個節點：`node.val = node.next.val; node.next = node.next.next`，O(1)。代價是這個做法改變了「節點身分」：如果外部有指標指向原本的下一個節點，它會變成懸空；而且當給的是尾節點時完全行不通，所以題目保證不是尾巴。面試時說出這兩個限制，比單純寫出兩行程式更重要。

## 核心題 5｜143. Reorder List｜Medium

### 題目

給一條 linked list `L0 → L1 → … → Ln−1 → Ln`，把它原地重排成 `L0 → Ln → L1 → Ln−1 → L2 → Ln−2 → …`，也就是從頭取一個、從尾取一個，交錯排列。只能改變節點之間的連接，不能修改節點的值；函式不需要回傳值。限制：節點數在 1 到 5 × 10⁴ 之間，節點值在 1 到 1000 之間。

- 範例 1：`1 → 2 → 3 → 4`，重排成 `1 → 4 → 2 → 3`。
- 範例 2：`1 → 2 → 3 → 4 → 5`，重排成 `1 → 5 → 2 → 4 → 3`。
- 範例 3（邊界）：`1`，不變；`1 → 2`，也不變（`L0 → L1` 本身就符合）。

### 思路

暴力解是把所有節點放進一個陣列，然後用兩個索引 i、j 從兩端往中間走，依序把 `nodes[i] → nodes[j] → nodes[i+1] → …` 串起來，最後把中間那個節點的 `next` 設為 `None`。時間 O(n)、空間 O(n)。瓶頸在於：我們需要「從尾巴往回走」，而單向 linked list 做不到，所以只好把節點存起來。

關鍵觀察是：重排後的序列，正是「前半段」和「**反轉後的**後半段」交錯合併的結果。以 `1 2 3 4 5` 為例，前半是 `1 2 3`，後半是 `4 5`，反轉後是 `5 4`，交錯合併 `1 5 2 4 3` 就是答案。而「從尾巴往回走」正是反轉之後的「從頭往後走」。於是問題拆成三個本章的基本零件：用快慢指標找第一個中點並切開（11.3 節）、反轉後半段（核心題 1）、兩條 list 交錯合併（類似核心題 2，但不比大小，輪流取）。

為什麼用**第一個中點**？切開之後前半長度是 ⌈n/2⌉、後半是 ⌊n/2⌋，前半恰好多一個或一樣多。交錯合併時從前半開始取，前半多出的那個節點（奇數長度時的正中間）自然落在最後，符合 `… → L2` 結尾的要求。如果用第二個中點，偶數長度時後半會比前半多，合併的尾端就要另外處理。

交錯合併的迴圈只需要 `while second`：每輪從前半取一個 `a`、從後半取一個 `b`，接成 `a → b → (a 原本的下一個)`。因為後半長度 ≤ 前半，後半用完時前半最多剩一個節點，而它已經接在最後一個 `b` 之後、而且它的 `next` 在切開時就是 `None`（偶數長度時前半最後一個節點的 `next` 也被設成 `None`），所以結尾自然正確。

```text
原始：1 → 2 → 3 → 4 → 5

步驟一：找第一個中點並切開
  slow=1 fast=1 → slow=2 fast=3 → slow=3 fast=5（fast.next 為 None，停止）
  first  = 1 → 2 → 3          （3.next = None）
  second = 4 → 5

步驟二：反轉後半
  second = 5 → 4

步驟三：交錯合併（每輪 a 取自 first、b 取自 second）
  輪  a  b   接線                      目前結果
  1   1  5   1 → 5 → 2                 1 → 5 → 2 → 3
  2   2  4   2 → 4 → 3                 1 → 5 → 2 → 4 → 3
  second 用完，結束；3.next 本來就是 None
```

第 1 輪先記住 `1` 原本的下一個 `2` 和 `5` 原本的下一個 `4`，再接成 `1 → 5 → 2`；第 2 輪同理接成 `2 → 4 → 3`。此時 second 已經沒有節點，而前半剩下的 `3` 正好已經接在 `4` 後面，整條 list 完成，不需要任何收尾。

### 解法

```python
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def reorder_list(head):
    if head is None or head.next is None:
        return
    # 1. 第一個中點，切開
    slow = fast = head
    while fast.next and fast.next.next:
        slow, fast = slow.next, fast.next.next
    second, slow.next = slow.next, None
    # 2. 反轉後半
    prev = None
    while second:
        second.next, prev, second = prev, second, second.next
    second = prev
    # 3. 交錯合併
    first = head
    while second:
        a_next, b_next = first.next, second.next
        first.next = second
        second.next = a_next
        first, second = a_next, b_next


def expected(arr):
    out, i, j = [], 0, len(arr) - 1
    while i <= j:
        out.append(arr[i])
        if i != j:
            out.append(arr[j])
        i, j = i + 1, j - 1
    return out


def run(arr):
    head = build(arr)
    reorder_list(head)
    return to_list(head)


assert run([1, 2, 3, 4]) == [1, 4, 2, 3]
assert run([1, 2, 3, 4, 5]) == [1, 5, 2, 4, 3]
assert run([1]) == [1]
assert run([1, 2]) == [1, 2]
assert run([1, 2, 3]) == [1, 3, 2]
for _ in range(300):
    arr = [random.randint(1, 1000) for _ in range(random.randint(1, 40))]
    assert run(arr) == expected(arr)
print("all tests passed")
```

反轉那一行 `second.next, prev, second = prev, second, second.next` 是 Python 的同時賦值：右邊三個值先全部算好（此時 `second.next` 還是原本的下一個），再依序賦值給左邊，所以等價於先存 `nxt` 的四行寫法。面試時如果不確定賦值順序，寫成四行更安全。

### 複雜度與邊界

時間 O(n)：找中點 O(n/2)、反轉 O(n/2)、合併 O(n/2)。空間 O(1)，只用固定數量的指標；陣列版是 O(n) 空間。邊界情況：長度 1 或 2 時直接回傳，因為結果與原本相同（長度 2 時切開後前半是 `1`、後半是 `2`，合併結果也一樣，提前回傳只是省事）；奇數長度時正中間的節點留在前半的最後，自然成為結果的尾巴；切開時一定要 `slow.next = None`，否則前半的尾巴仍連著後半的原本開頭，反轉後會形成環，合併時無窮迴圈。

### Follow-up

> [!question]- F1. 如果要把重排後的 list 還原成原本的順序呢？
> 重排後奇數位置（第 1、3、5… 個節點，也就是索引 0、2、4…）依序是 L0、L1、L2…，偶數位置（第 2、4、6… 個節點，索引 1、3、5…）依序是 Ln、Ln−1…。所以先把 list 拆成奇偶兩條（328 題的做法），再把第二條反轉、接在第一條後面，就回到 `L0 → L1 → … → Ln`。三個步驟都是 O(n) 時間、O(1) 空間。這個 follow-up 確認你理解重排是「切半、反轉、交錯」三個可逆操作的組合。

> [!question]- F2. 怎麼把節點依位置分成奇數位置在前、偶數位置在後（328. Odd Even Linked List）？
> 維護兩條 list：`odd` 從 head 開始、`even` 從 `head.next` 開始，記住 `even_head`。迴圈 `while even and even.next`：`odd.next = even.next; odd = odd.next; even.next = odd.next; even = even.next`，每輪各前進一個節點，最後 `odd.next = even_head` 把偶數串接在奇數串之後。時間 O(n)、空間 O(1)，而且保持各自的相對順序。迴圈條件檢查 `even` 而不是 `odd`，因為 even 永遠在 odd 前面一格，它先碰到尾端。

> [!question]- F3. 偶數長度的 list，第 i 個節點與第 n − 1 − i 個節點稱為一對，求最大的一對和（2130. Maximum Twin Sum）？
> 和本題同樣的前兩步：用第一個中點切開、反轉後半；之後兩條同步走，每一步計算 `a.val + b.val` 的最大值。反轉後的後半第 k 個，正是原本的第 n − 1 − k 個，剛好對上前半的第 k 個。時間 O(n)、空間 O(1)。如果不能修改 list，就用 stack 存前半的值，再走後半時彈出比對，空間 O(n)。這題和 234 回文檢查是同一個結構：「需要把頭尾配對」就想到「切半＋反轉」。

> [!question]- F4. 如果是雙向 linked list，或者可以用遞迴呢？
> 雙向 linked list 可以直接從 head 和 tail 往中間走，不需要反轉：每輪把 tail 拿下來插到 head 後面，head 往前兩格、tail 往前一格，直到兩者相遇或相鄰，O(n) 時間、O(1) 空間，但要同時維護 `prev` 指標。單向 list 的遞迴解法是讓遞迴走到尾端，回溯時每一層拿到「從尾巴往回數」的節點，同時用一個外部指標從頭往前走，把兩者接起來；這等於用呼叫堆疊扮演反轉後的後半，空間 O(n)，n = 5 × 10⁴ 時在 Python 會超過遞迴上限，所以不適合當最終答案。

## 難題 1｜25. Reverse Nodes in k-Group｜Hard

### 題目

給一條 linked list 的頭節點 `head` 和正整數 `k`，從頭開始每 k 個節點分成一組，把每一組內的節點順序反轉；最後如果剩下不足 k 個節點，保持原樣不動。只能改變節點之間的連接，不能修改節點的值，回傳新的頭節點。限制：節點數 n 在 1 到 5000 之間，`1 <= k <= n`，節點值在 0 到 1000 之間。進階要求是 O(1) 額外空間。

- 範例 1：`1 → 2 → 3 → 4 → 5`、`k = 2`，回傳 `2 → 1 → 4 → 3 → 5`（最後的 5 不足一組，不動）。
- 範例 2：`1 → 2 → 3 → 4 → 5`、`k = 3`，回傳 `3 → 2 → 1 → 4 → 5`。
- 範例 3（邊界）：`k = 1` 時 list 不變；`k = n` 時整條反轉；`1 → 2 → 3 → 4`、`k = 2` 剛好分完，回傳 `2 → 1 → 4 → 3`。

### 提示

> [!tip]- 提示 1
> 每一組的反轉就是核心題 1，難的是「接回去」。對每一組，你需要記住哪兩個節點才能在反轉後把它和前後接起來？

> [!tip]- 提示 2
> 用 dummy 當第 0 組的「前一個節點」`group_prev`。每一輪先從 `group_prev` 往後走 k 步找到這組的最後一個節點 `kth`；走不到就代表剩下不足 k 個，直接結束。這樣就不會反轉到最後那組不完整的節點。

> [!tip]- 提示 3
> 反轉這一組時，把 `prev` 的初值設成 `kth.next`（下一組的開頭），反轉完這組原本的頭自然就指向下一組。接著 `group_prev.next = kth`，而這組原本的頭變成新的 `group_prev`。

### 詳解

**為什麼直覺做法不夠**。轉成陣列、每 k 個反轉、再重新串接，時間 O(n) 但空間 O(n)，不符合進階要求。遞迴寫法很短：先確認有 k 個節點，反轉這 k 個，再讓這組原本的頭指向「對剩下部分遞迴的結果」；它是對的，但遞迴深度是 n/k，k = 1 時深度就是 5000，Python 會超過遞迴上限。另一個常見的錯誤直覺是「邊走邊反轉，走到尾巴發現不足 k 個再反轉回來」，這也行得通，但多了一次反轉，而且容易在「反轉回來」時接錯。真正的難點不是反轉本身，而是**每一組反轉後要和前一組、後一組正確接起來**，以及**先確認夠 k 個才動手**。

**每一組需要的四個指標**。對每一組，記 `group_prev`（這組前面那個節點，第一組是 dummy）、`kth`（這組的最後一個節點）、`group_next = kth.next`（下一組的第一個節點）。反轉前這組的第一個節點是 `group_prev.next`，反轉後它會變成這組的最後一個；`kth` 則變成這組的第一個。所以反轉後要做兩條接線：`group_prev.next = kth`（前一組接到新的組頭），以及原組頭的 `next` 接到 `group_next`（新的組尾接到下一組）。

**把第二條接線藏進反轉裡**。核心題 1 的反轉中 `prev` 初值是 `None`，意思是「反轉後的尾巴指向 `None`」。這裡把 `prev` 初值設成 `group_next`，反轉 k 個節點後，原組頭（第一個被處理的節點）的 `next` 就自動指向 `group_next`，第二條接線不必另外寫。反轉的停止條件是 `cur is group_next`，剛好處理完這組的 k 個節點。

**正確性**。Invariant：每一輪開始時，`dummy.next` 到 `group_prev` 是已經處理完、順序正確的部分，`group_prev.next` 開始是尚未處理、原封不動的部分。每一輪若找得到 `kth`，就把這 k 個節點反轉並接好，然後 `group_prev` 移到這組的新尾巴（原組頭），invariant 保持；若找不到 `kth`，剩下的不足 k 個本來就該保持原樣，而它們已經接在 `group_prev` 後面，直接回傳 `dummy.next`。每個節點被「找 kth」走過一次、被反轉處理一次，總共 O(n)。

```text
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8，k = 3

第 1 輪：group_prev = dummy，往後走 3 步 → kth = 3，group_next = 4
  反轉 [1 2 3]，prev 初值 = 4：
    cur=1：1.next = 4            prev=1
    cur=2：2.next = 1            prev=2
    cur=3：3.next = 2            prev=3      cur 走到 4，停止
  dummy.next = 3；group_prev = 1（原組頭，現在是組尾）
  dummy → 3 → 2 → 1 → 4 → 5 → 6 → 7 → 8

第 2 輪：group_prev = 1，走 3 步 → kth = 6，group_next = 7
  反轉 [4 5 6]，prev 初值 = 7 → 4.next = 7、5.next = 4、6.next = 5
  1.next = 6；group_prev = 4
  dummy → 3 → 2 → 1 → 6 → 5 → 4 → 7 → 8

第 3 輪：group_prev = 4，走 3 步：7、8、None → 不足 3 個，回傳
  結果：3 → 2 → 1 → 6 → 5 → 4 → 7 → 8
```

第 1 輪反轉時，1 是第一個被處理的節點，它的 `next` 被設成 `prev` 的初值 4，於是這組的新尾巴已經接上下一組；接著只要把 dummy 接到新的組頭 3。第 3 輪找 kth 時走到 `None`，代表 7、8 不足一組，而它們本來就接在 4 後面，所以直接結束，不需要任何「反轉回來」的動作。

### 解法

```python
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def reverse_k_group(head, k):
    dummy = ListNode(0, head)
    group_prev = dummy
    while True:
        kth = group_prev
        for _ in range(k):                  # 先確認還有 k 個節點
            kth = kth.next
            if kth is None:
                return dummy.next
        group_next = kth.next
        prev, cur = group_next, group_prev.next
        while cur is not group_next:        # 反轉這一組，尾巴直接接到下一組
            nxt = cur.next
            cur.next = prev
            prev, cur = cur, nxt
        old_head = group_prev.next          # 原組頭，現在是組尾
        group_prev.next = kth
        group_prev = old_head


def expected(arr, k):
    out = []
    for i in range(0, len(arr), k):
        chunk = arr[i:i + k]
        out += chunk[::-1] if len(chunk) == k else chunk
    return out


assert to_list(reverse_k_group(build([1, 2, 3, 4, 5]), 2)) == [2, 1, 4, 3, 5]
assert to_list(reverse_k_group(build([1, 2, 3, 4, 5]), 3)) == [3, 2, 1, 4, 5]
assert to_list(reverse_k_group(build([1, 2, 3, 4]), 2)) == [2, 1, 4, 3]
assert to_list(reverse_k_group(build([1, 2, 3]), 1)) == [1, 2, 3]
assert to_list(reverse_k_group(build([1, 2, 3]), 3)) == [3, 2, 1]
assert to_list(reverse_k_group(build([9]), 1)) == [9]
assert to_list(reverse_k_group(build(range(5000)), 1)) == list(range(5000))
for _ in range(300):
    arr = [random.randint(0, 9) for _ in range(random.randint(1, 20))]
    k = random.randint(1, len(arr))
    assert to_list(reverse_k_group(build(arr), k)) == expected(arr, k)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個節點在「找 kth」時被走過一次，在反轉時被處理一次（最後不足 k 個的節點只被走過一次），合計不超過 2n 步。空間 O(1)，只有固定數量的指標；遞迴版是 O(n/k)。邊界情況：k = 1 時每組反轉等於不動，程式仍正確地逐組前進；k = n 時只有一組，第二輪找 kth 立刻走到 `None`；n 是 k 的倍數時，最後一輪 `group_prev` 是最後一組的新尾巴，它的 `next` 已經是 `None`，找 kth 第一步就結束；`prev` 初值若誤寫成 `None`，每組反轉後都會和後面斷開，只剩第一組。

### Follow-up

> [!question]- F1. 如果最後不足 k 個的那組也要反轉呢？
> 把「走不到 kth 就結束」改成「走到 `None` 之前的最後一個節點當作 kth」：找 kth 時若提早遇到 `None`，就用最後一個非空節點當 kth、`group_next = None`，照常反轉這組後結束。另一種寫法是先算長度 n，前 ⌊n/k⌋ 組照原題處理，最後 n mod k 個再做一次反轉。時間仍是 O(n)、空間 O(1)。這個變形其實比原題簡單，因為不需要「先確認夠 k 個」，但面試官會用它確認你知道原題的檢查放在哪裡。

> [!question]- F2. 如果分組要從尾巴開始算（最前面不足 k 個的那組不動）呢？
> 先走一次求長度 n，令 r = n mod k，把 `group_prev` 從 dummy 往前推 r 步，讓最前面 r 個節點保持原樣，之後的節點剛好可以分成完整的 k 個一組，照原題的迴圈處理即可。例如 `1 2 3 4 5`、k = 2 時 r = 1，結果是 `1 3 2 5 4`。時間 O(n)、空間 O(1)。這是「先算長度」與「間距固定」之間的取捨：這裡不知道長度就無法決定第一組從哪裡開始，所以兩次掃描是必要的。

> [!question]- F3. 如果組的大小依序是 1、2、3、4…，只反轉長度為偶數的組呢（2074. Reverse Nodes in Even Length Groups）？
> 迴圈結構不變，只是每一輪的 k 不再固定：第 g 輪嘗試往後走 g 步，得到這組的實際長度 L（最後一組可能不足 g 個，此時 L 就是剩下的節點數），只有 L 為偶數時才反轉。注意判斷用的是**實際長度** L 而不是預定的 g，例如最後一組預定 5 個但只剩 4 個，就要反轉。反轉與接線的程式和原題完全相同，時間 O(n)、空間 O(1)。

> [!question]- F4. k = 2 的特例（24. Swap Nodes in Pairs）能不能寫得更簡單？
> 可以用專門的四指標交換：`prev` 從 dummy 開始，每輪令 `a = prev.next`、`b = a.next`，接成 `prev.next = b; a.next = b.next; b.next = a`，然後 `prev = a`，直到 `prev.next` 或 `prev.next.next` 為空。時間 O(n)、空間 O(1)。這三行接線的順序和原題的 `prev` 初值技巧本質相同：先讓新的尾巴 a 接上下一組（`a.next = b.next`），再讓前一組接到新的頭 b。面試時若時間緊，k = 2 用專門寫法較不易錯；若面試官接著問一般的 k，再換成本題的通用版本。

### 心得

關鍵突破是把 `prev` 的初值設成下一組的開頭，讓「反轉」和「接到下一組」在同一個迴圈裡完成，剩下只要一條 `group_prev.next = kth`。它和核心題 1 的關係是：核心題 1 是 `prev = None` 的特例（整條 list 只有一組、下一組是空的）；和 F1 的 92 題相比，這題只是把「反轉一段」重複做很多次，所以真正要練的是每一組的四個指標（`group_prev`、`kth`、`group_next`、原組頭）。面試時建議先畫出一組反轉前後的圖，標出這四個指標，口頭說明「先確認夠 k 個才反轉」，再寫程式；寫完用 k = 1、k = n、n 是 k 的倍數三個情況手動走一次，這三個邊界最容易暴露接線錯誤。

## 難題 2｜23. Merge k Sorted Lists｜Hard

### 題目

給一個陣列 `lists`，裡面有 k 條各自以遞增順序排列的 linked list（有些可能是空的），把它們合併成一條遞增的 linked list 並回傳頭節點。限制：`0 <= k <= 10⁴`，每條長度 0 到 500，節點值在 `-10⁴` 到 `10⁴` 之間，所有 list 的總節點數 N 不超過 10⁴。

- 範例 1：`lists = [1 → 4 → 5, 1 → 3 → 4, 2 → 6]`，回傳 `1 → 1 → 2 → 3 → 4 → 4 → 5 → 6`。
- 範例 2：`lists = [5 → 6, 1 → 2 → 3]`，回傳 `1 → 2 → 3 → 5 → 6`。
- 範例 3（邊界）：`lists = []`，回傳 `None`；`lists = [None, None]`，也回傳 `None`。

### 提示

> [!tip]- 提示 1
> 先想最直接的做法：把第一條和第二條合併，結果再和第三條合併……這樣每個節點會被走過幾次？最差情況是什麼？

> [!tip]- 提示 2
> 合併的每一步，都要從 k 個「目前的頭」裡找最小值。有什麼資料結構可以在 O(log k) 內取出最小值、又能放入新元素？

> [!tip]- 提示 3
> 兩種 O(N log k) 的做法：min-heap 裡放 k 個頭，每次彈出最小的接上、推入它的下一個；或像 merge sort 一樣兩兩配對合併，每一輪 list 數量減半，共 log k 輪、每輪總共走 N 個節點。

### 詳解

**為什麼直覺做法不夠**。最簡單的是把所有值收集起來排序再重建，O(N log N) 時間、O(N) 空間，而且建立了新節點。逐條合併看起來利用了「已排序」，其實更糟：假設每條長度都是 N/k，第 i 次合併時累積的結果已經有 i · N/k 個節點，總工作量是 Σ i · N/k ≈ k · N / 2，也就是 O(kN)。當 k = 10⁴、N = 10⁴ 且大部分 list 很短時還勉強可以，但若 k 與 N 都大（例如 k = 10³、每條 10³ 個），就是 10⁹ 級。浪費在於：前面合併好的長串被反覆走訪。

**突破點一：heap 一次比 k 個頭**。合併後的下一個節點，一定是 k 個目前的頭之中最小的那個。用 min-heap（第 14 章）存這 k 個頭，取最小 O(log k)，接上之後把它的 `next`（如果有）推入，O(log k)。每個節點進出 heap 各一次，總時間 O(N log k)，heap 大小最多 k，額外空間 O(k)。Python 的 `heapq` 比較 tuple 時，若值相同會接著比第二個元素，所以不能放 `(val, node)`（`ListNode` 沒有定義大小比較，會 TypeError），要放 `(val, i, node)`，i 是 list 的編號，互不相同，保證比較在 node 之前就分出勝負。

**突破點二：兩兩配對合併**。把 k 條 list 配成 k/2 對，各自用核心題 2 合併，得到 k/2 條；再配對合併……共 ⌈log₂ k⌉ 輪。每一輪中，每個節點恰好參與一次合併，所以一輪的總工作量是 O(N)，總時間 O(N log k)。這和逐條合併的差別在於：每個節點被走訪的次數從「最多 k 次」降到「log k 次」，就像 merge sort 比 insertion sort 快的原因。用迭代的間隔寫法（`step = 1, 2, 4, …`，把 `lists[i]` 與 `lists[i + step]` 合併存回 `lists[i]`），額外空間 O(1)。

**兩者的取捨**。heap 版的優點是適用於串流：每條 list 只需要「讀下一個」，不需要事先看完，也能隨時輸出目前最小的值（見 F1）。配對版的優點是不需要 heap、常數小、空間 O(1)，而且每一輪的各對合併互相獨立，可以並行（見 F4）。面試時兩種都說，寫其中一種即可；Python 中 heap 版較短，配對版較省空間。

```text
lists = [1 → 4 → 5, 1 → 3 → 4, 2 → 6]

heap 版（heap 內容寫成 (值, list 編號)）
 步  彈出      推入      heap 之後                   結果
 0   -         -         (1,0) (1,1) (2,2)           -
 1   (1,0)     (4,0)     (1,1) (2,2) (4,0)           1
 2   (1,1)     (3,1)     (2,2) (3,1) (4,0)           1 1
 3   (2,2)     (6,2)     (3,1) (4,0) (6,2)           1 1 2
 4   (3,1)     (4,1)     (4,0) (4,1) (6,2)           1 1 2 3
 5   (4,0)     (5,0)     (4,1) (5,0) (6,2)           1 1 2 3 4
 6   (4,1)     -         (5,0) (6,2)                 1 1 2 3 4 4
 7   (5,0)     -         (6,2)                       1 1 2 3 4 4 5
 8   (6,2)     -         空                           1 1 2 3 4 4 5 6

配對版（step 每輪加倍）
 step=1：lists[0] = merge(lists[0], lists[1]) = 1 1 3 4 4 5；lists[2] 沒有配對，保留
 step=2：lists[0] = merge(lists[0], lists[2]) = 1 1 2 3 4 4 5 6
```

heap 版第 1 步兩個 1 平手，`heapq` 比較第二個欄位，編號 0 較小先出；這不影響正確性，但讓結果是穩定的。每一步 heap 中最多 3 個元素，也就是 k 個。配對版只需要兩輪：k = 3 時 ⌈log₂ 3⌉ = 2。

### 解法

```python
import heapq
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def merge_k_lists_heap(lists):
    heap = [(node.val, i, node) for i, node in enumerate(lists) if node]
    heapq.heapify(heap)                         # O(k)
    dummy = tail = ListNode()
    while heap:
        _, i, node = heapq.heappop(heap)
        tail.next = tail = node
        if node.next:
            heapq.heappush(heap, (node.next.val, i, node.next))
    return dummy.next


def merge_two(a, b):
    dummy = tail = ListNode()
    while a and b:
        if a.val <= b.val:
            tail.next, a = a, a.next
        else:
            tail.next, b = b, b.next
        tail = tail.next
    tail.next = a or b
    return dummy.next


def merge_k_lists_pairwise(lists):
    lists = list(lists)                         # 不修改呼叫端的陣列
    if not lists:
        return None
    step = 1
    while step < len(lists):
        for i in range(0, len(lists) - step, 2 * step):
            lists[i] = merge_two(lists[i], lists[i + step])
        step *= 2
    return lists[0]


def make(arrs):
    return [build(a) for a in arrs]


for f in (merge_k_lists_heap, merge_k_lists_pairwise):
    assert to_list(f(make([[1, 4, 5], [1, 3, 4], [2, 6]]))) == [1, 1, 2, 3, 4, 4, 5, 6]
    assert to_list(f(make([[5, 6], [1, 2, 3]]))) == [1, 2, 3, 5, 6]
    assert f([]) is None
    assert f([None, None]) is None
    assert to_list(f(make([[], [2], []]))) == [2]
    assert to_list(f(make([[1, 1], [1], [1, 1, 1]]))) == [1] * 6     # 大量平手不會 TypeError
for _ in range(300):
    arrs = [sorted(random.randint(-9, 9) for _ in range(random.randint(0, 5)))
            for _ in range(random.randint(0, 9))]
    expect = sorted(x for a in arrs for x in a)
    assert to_list(merge_k_lists_heap(make(arrs))) == expect
    assert to_list(merge_k_lists_pairwise(make(arrs))) == expect
print("all tests passed")
```

`tail.next = tail = node` 是 Python 的鏈式賦值，會由左到右先執行 `tail.next = node`、再執行 `tail = node`；不熟悉的話寫成兩行更清楚。

### 複雜度與邊界

heap 版時間 O(k + N log k)：heapify 是 O(k)，每個節點各做一次 push 與 pop，heap 大小不超過 k；空間 O(k)。配對版時間 O(N log k)：⌈log₂ k⌉ 輪、每輪 O(N)；空間 O(1)（不計複製 `lists` 陣列的 O(k)，若允許修改輸入可省略）。邊界情況：k = 0 回傳 `None`；所有 list 都是空的時 heap 為空、配對版的結果是 `None`；某些 list 為空不影響（heap 版建堆時過濾，配對版的 `merge_two` 處理空輸入）；值相同時 heap 必須有 `i` 這個平手比較欄位；k = 1 時直接回傳那一條。

### Follow-up

> [!question]- F1. 如果每條 list 是存在磁碟上的大檔案，記憶體放不下全部資料呢？
> 這就是外部排序（external merge sort）的合併階段。為每個檔案配一個讀取緩衝區，heap 只存 k 個目前的頭（值與檔案編號），每次彈出最小值寫到輸出緩衝區，再從對應檔案讀下一個；緩衝區空了才整塊讀入，滿了才整塊寫出，讓磁碟 I/O 是循序的。記憶體需求是 O(k · B)，B 是緩衝區大小；若 k 太大以致 k 個緩衝區放不下，就分多輪合併，每輪合併 m 條，共 log_m k 輪。配對版在這裡較不適合，因為每一輪都要把全部資料讀寫一次。

> [!question]- F2. 如果只需要合併結果的前 m 個節點呢？
> heap 版天然支援：彈出 m 次就停，時間 O(k + m log k)，不必處理全部 N 個節點。配對版則做不到提早結束，因為第一輪就要把所有 list 合併過。若 m 很小而 k 很大（例如 k = 10⁴、m = 10），heap 的 O(k) 建堆反而是主要成本，仍然比 O(N log k) 好得多。這類「k 條排序序列中的前 m 小」也是 373. Find K Pairs with Smallest Sums 的結構，第 14 章的 k-way merge 模板可以直接套用。

> [!question]- F3. 如果輸入是 k 個排序陣列而不是 linked list 呢？
> heap 中改放 `(值, 陣列編號, 元素索引)`，彈出後若該陣列還有下一個元素就推入 `(arr[j + 1], i, j + 1)`，時間同樣 O(N log k)，但輸出需要一個新陣列，空間 O(N)。配對版也可行，只是陣列合併要複製元素，每輪 O(N) 額外空間。和 linked list 版的差別在於：linked list 可以重用節點、剩下的尾段一次接上，陣列則一定要複製；第 14 章難題 4（632）就是在這個結構上維護「k 個指標的最大值與最小值」。

> [!question]- F4. 如果有多台機器或多個 CPU 核心，怎麼加速？
> 配對版每一輪的 k/2 個合併互相獨立，可以並行執行，總共 ⌈log₂ k⌉ 輪；理想情況下總時間由「每輪中最長的那個合併」決定，最後一輪是兩條各約 N/2 長的 list 合併，所以下限是 O(N)，加速比受限於最後幾輪。若要突破這個限制，可以按值域切分：先抽樣決定 p − 1 個分界值，每台機器負責一個值域區間，在每條 list 上用分界值切出對應片段後各自做 k-way merge，最後依值域順序串接，這是平行 sample sort 的想法。

### 心得

關鍵突破是看出逐條合併的浪費在於「長串被反覆走訪」，而解法是讓每個節點只被處理 O(log k) 次：heap 用 O(log k) 從 k 個頭中挑最小，配對合併讓每個節點只經過 log k 輪。它把核心題 2 的兩條合併推廣到 k 條，也是難題 4（148）merge sort 的合併層：148 的 bottom-up 寫法本質上就是本題的配對版，只是從 n 條長度 1 的 list 開始。面試時先說逐條合併為什麼是 O(kN)（這一步很多人跳過，但面試官很想聽你分析），再提出 heap 版，寫程式時記得 `(val, i, node)` 的平手欄位；最後主動比較兩種做法在串流、空間與並行上的差異。

## 難題 3｜138. Copy List with Random Pointer｜Medium

### 題目

一條長度為 n 的 linked list，每個節點除了 `next` 之外還有一個 `random` 指標，可以指向 list 中任何一個節點，或是 `None`。請建立這條 list 的**深複製**（deep copy）：恰好 n 個全新的節點，新節點的 `val` 與對應的舊節點相同，新節點的 `next` 與 `random` 都指向**新 list 中**對應的節點，新 list 中的任何指標都不能指向舊 list 的節點。回傳新 list 的頭節點。測資用 `[val, random_index]` 的陣列表示一條 list，`random_index` 為 `None` 表示 random 指向空。限制：`0 <= n <= 1000`，值在 `-10⁴` 到 `10⁴` 之間。

- 範例 1：`[[7, None], [13, 0], [11, 4], [10, 2], [1, 0]]`，回傳一條結構完全相同、但節點全新的 list。
- 範例 2：`[[1, 1], [2, 1]]`，第一個節點的 random 指向第二個，第二個的 random 指向自己。
- 範例 3（邊界）：空 list，回傳 `None`；`[[3, None], [3, 0], [3, None]]` 中值全部相同，不能用值來找對應節點。

### 提示

> [!tip]- 提示 1
> 複製 `next` 很簡單，困難的是 `random`：當你建立第 i 個新節點時，它的 random 指向的那個新節點可能還沒被建立。你需要一個「舊節點 → 新節點」的對應關係。

> [!tip]- 提示 2
> 用 hash map 記錄這個對應關係：先走一次建立所有新節點，再走第二次設定 `next` 與 `random`。這是 O(n) 空間。能不能把對應關係「存在 list 本身的結構裡」？

> [!tip]- 提示 3
> 把每個新節點插在對應的舊節點後面：`A → A' → B → B' → …`。這樣 `X'` 就是 `X.next`，於是 `X.next.random = X.random.next`。設好 random 後，再把交錯的 list 拆回兩條。

### 詳解

**為什麼直覺做法不夠**。如果只複製 `next`，再試圖用值去找 random 該指向哪個新節點，遇到重複值（範例 3）就會指錯。如果對每個節點的 random，從舊 list 頭走過去算出它是第幾個節點，再在新 list 上走同樣步數，結果正確但時間 O(n²)。本質上，問題需要的是一個「舊節點 → 新節點」的函數，而且要能在 O(1) 內查詢。

**做法一：hash map**。第一次走訪為每個舊節點建立新節點，存入 `old_to_new[old] = new`；第二次走訪設定 `new.next = old_to_new.get(old.next)`、`new.random = old_to_new.get(old.random)`。用節點物件當 key，Python 依物件身分雜湊（`ListNode` 沒有自訂 `__eq__`），所以重複值不會混淆。時間 O(n)、空間 O(n)。這是面試中最穩的答案，也是本題的基準。

**做法二：交錯插入，O(1) 額外空間**。突破點是：對應關係不一定要存在外部，可以用 list 的位置來表示。第一步，把每個新節點 `X'` 插在舊節點 `X` 後面，list 變成 `A → A' → B → B' → …`；此時任何舊節點 X 的複製品就是 `X.next`。第二步，對每個舊節點 X，若 `X.random` 不為空，令 `X.next.random = X.random.next`：`X.random` 是某個舊節點 Y，而 Y 的複製品正是 `Y.next`。第三步，把交錯的 list 拆開：舊節點的 `next` 恢復成 `X.next.next`，新節點的 `next` 改成 `X'.next.next`（或 `None`）。

**正確性與順序**。第二步必須在第三步之前全部完成，因為設定 random 時要依賴「`Y.next` 是 Y 的複製品」這個結構，拆開之後這個關係就消失了；同理第二步不能和第一步合併，因為設定 X 的 random 時，Y 的複製品可能還沒插入。拆開時原 list 被完整恢復，題目要求不能改變原 list 的最終狀態，所以第三步也是必要的。除了答案本身的 n 個節點，額外空間 O(1)。

```text
原 list（括號內是 random 指向的值）：
  7(-) → 13(7) → 11(1) → 10(11) → 1(7)

第一步：交錯插入複製品（' 表示新節點）
  7 → 7' → 13 → 13' → 11 → 11' → 10 → 10' → 1 → 1'

第二步：X.next.random = X.random.next
  7 ：random 為空          → 7'.random = None
  13：random = 7           → 13'.random = 7.next  = 7'
  11：random = 1           → 11'.random = 1.next  = 1'
  10：random = 11          → 10'.random = 11.next = 11'
  1 ：random = 7           → 1'.random  = 7.next  = 7'

第三步：拆開
  舊：7 → 13 → 11 → 10 → 1          （恢復原狀）
  新：7' → 13' → 11' → 10' → 1'     （random 全部指向新節點）
```

第二步的每一行都只用到兩次 `.next`：`X.next` 找到 X 的複製品，`X.random.next` 找到 random 目標的複製品。這就是把 hash map 的 `old_to_new[Y]` 換成 `Y.next` 的效果。第三步拆開後，舊 list 與題目給的完全相同，新 list 的每個指標都只指向新節點。

### 解法

```python
import random


class Node:
    def __init__(self, val, next=None, random=None):
        self.val = val
        self.next = next
        self.random = random


def build_random(pairs):
    """[[val, random_index], ...] → linked list；random_index 為 None 表示空。"""
    nodes = [Node(v) for v, _ in pairs]
    for i, (_, r) in enumerate(pairs):
        if i + 1 < len(nodes):
            nodes[i].next = nodes[i + 1]
        nodes[i].random = nodes[r] if r is not None else None
    return nodes[0] if nodes else None


def to_pairs(head):
    """linked list → [[val, random_index], ...]，用來比較結構。"""
    nodes, cur = [], head
    while cur:
        nodes.append(cur)
        cur = cur.next
    index = {id(n): i for i, n in enumerate(nodes)}
    return [[n.val, index[id(n.random)] if n.random else None] for n in nodes]


def copy_random_list_map(head):
    old_to_new = {}
    cur = head
    while cur:
        old_to_new[cur] = Node(cur.val)
        cur = cur.next
    cur = head
    while cur:
        old_to_new[cur].next = old_to_new.get(cur.next)
        old_to_new[cur].random = old_to_new.get(cur.random)
        cur = cur.next
    return old_to_new.get(head)


def copy_random_list(head):
    if head is None:
        return None
    cur = head                                   # 第一步：交錯插入
    while cur:
        cur.next = Node(cur.val, cur.next)
        cur = cur.next.next
    cur = head                                   # 第二步：設定 random
    while cur:
        if cur.random:
            cur.next.random = cur.random.next
        cur = cur.next.next
    new_head = head.next                         # 第三步：拆開
    cur = head
    while cur:
        copy = cur.next
        cur.next = copy.next
        copy.next = copy.next.next if copy.next else None
        cur = cur.next
    return new_head


def check(f, pairs):
    head = build_random(pairs)
    old_ids = set()
    cur = head
    while cur:
        old_ids.add(id(cur))
        cur = cur.next
    new = f(head)
    assert to_pairs(new) == pairs                # 結構相同
    assert to_pairs(head) == pairs               # 原 list 未被破壞
    cur = new
    while cur:                                   # 深複製：沒有任何舊節點
        assert id(cur) not in old_ids
        assert cur.random is None or id(cur.random) not in old_ids
        cur = cur.next


for f in (copy_random_list, copy_random_list_map):
    check(f, [[7, None], [13, 0], [11, 4], [10, 2], [1, 0]])
    check(f, [[1, 1], [2, 1]])
    check(f, [])
    check(f, [[3, None], [3, 0], [3, None]])
    check(f, [[5, 0]])                           # random 指向自己
    for _ in range(200):
        n = random.randint(0, 12)
        pairs = [[random.randint(0, 2), random.choice([None] + list(range(n)))] for _ in range(n)]
        check(f, pairs)
print("all tests passed")
```

### 複雜度與邊界

兩種做法時間都是 O(n)：hash map 版走兩次，交錯版走三次。hash map 版額外空間 O(n)；交錯版除了答案的 n 個新節點外是 O(1)。邊界情況：空 list 直接回傳 `None`；random 指向自己時，交錯版的 `cur.random.next` 就是 `cur.next`，也就是自己的複製品，正確；random 為空時要跳過，否則 `None.next` 出錯；拆開時最後一個複製品的 `copy.next` 是 `None`，所以要判斷 `copy.next` 再取 `.next`；值重複時兩種做法都依節點身分處理，不受影響。

### Follow-up

> [!question]- F1. 如果原 list 是唯讀的（例如多個執行緒同時在讀它），還能用交錯法嗎？
> 不能。交錯法在第一步到第三步之間會暫時改變原 list 的結構，此時其他讀者沿著 `next` 走會看到複製品，甚至把它當成原 list 的一部分。這時應該用 hash map 版：它只讀原 list，O(n) 時間、O(n) 空間。面試官常用這題確認你知道「O(1) 空間」是以「暫時修改輸入」換來的，在真實系統中這通常不可接受；能主動說出這個取捨，比單純寫出交錯法更有說服力。

> [!question]- F2. 能不能只走一次就用 hash map 完成？
> 可以用「取得或建立」的輔助函式：`get(old)` 若 `old` 為空回傳 `None`，若已在 map 中直接回傳，否則建立新節點存入後回傳。走訪一次，對每個舊節點設定 `get(cur).next = get(cur.next)`、`get(cur).random = get(cur.random)`，因為 random 指向的節點若還沒建立，`get` 會先建立它，之後走到時直接取用。時間 O(n)、空間 O(n)。遞迴版本（`copy(node)` 先查 memo，再遞迴複製 next 與 random）也可行，但遞迴深度 O(n)，n = 1000 時接近 Python 的預設上限。

> [!question]- F3. 如果要複製的是一般的圖（133. Clone Graph）呢？
> 每個節點的鄰居從「next 與 random 兩個指標」變成「任意多個」，交錯技巧就沒辦法用了，因為圖沒有一條可以插入複製品的主幹。做法是 hash map 加上 BFS 或 DFS：遇到一個沒複製過的節點就建立複製品存入 map 並加入佇列，處理每個節點時把它所有鄰居的複製品加入它的複製品的鄰居清單。時間 O(V + E)、空間 O(V)。這是第 15 章核心題 2；本題可以看成「每個節點恰好兩條出邊的圖」的特例。

> [!question]- F4. 如果要把這種 list 序列化成字串、再在另一台機器上還原呢？
> random 指標是記憶體位址，不能直接傳送，要換成與位址無關的表示法：用一次走訪給每個節點編號（hash map：節點 → 索引），輸出 `[[val, random_index], …]`，也就是本題測資的格式；還原時先依序建立 n 個節點並串好 `next`，再用索引陣列設定 random，O(n)。這和本解法的 `build_random`／`to_pairs` 一模一樣。面試時說出「指標要換成索引」，代表你理解深複製的本質是保存「結構」而不是保存「位址」。

### 心得

關鍵突破是把「舊節點 → 新節點」的對應關係從外部 hash map 搬進 list 本身：新節點插在舊節點後面，`X.next` 就是 X 的複製品，於是 `X.next.random = X.random.next` 一行完成查詢。它和本章其他題的差別是：其他題都在「改變順序」，這題在「複製結構」，難點是 random 指向尚未建立的節點；和第 15 章 Clone Graph 是同一個問題的不同規模。面試時建議先給 hash map 版並說明為什麼必須用節點身分而不是值當 key，再提出交錯法，畫出 `A → A' → B → B'` 的圖解釋第二步那一行；最後主動說明交錯法會暫時修改輸入，在唯讀或並行的情境下不適用。

## 難題 4｜148. Sort List｜Medium

### 題目

給一條 linked list 的頭節點 `head`，把它依節點值遞增排序後回傳。限制：節點數在 0 到 5 × 10⁴ 之間，節點值在 `-10⁵` 到 `10⁵` 之間。進階要求是 O(n log n) 時間與 O(1) 額外空間（也就是不使用遞迴堆疊）。

- 範例 1：`4 → 2 → 1 → 3`，回傳 `1 → 2 → 3 → 4`。
- 範例 2：`-1 → 5 → 3 → 4 → 0`，回傳 `-1 → 0 → 3 → 4 → 5`。
- 範例 3（邊界）：空 list 回傳 `None`；單一節點回傳它自己；`2 → 2 → 1 → 1` 有重複值，回傳 `1 → 1 → 2 → 2`。

### 提示

> [!tip]- 提示 1
> 陣列常用的 quicksort 和 heapsort 都依賴隨機存取。哪一種 O(n log n) 排序只需要「從頭往後走」與「把兩段接起來」？

> [!tip]- 提示 2
> Merge sort：用快慢指標找第一個中點切開，兩半各自遞迴排序，再用核心題 2 合併。時間 O(n log n)，但遞迴堆疊是 O(log n)。

> [!tip]- 提示 3
> 要做到 O(1) 空間，改成 bottom-up：先把每 1 個節點視為一段排好的 list，兩兩合併成長度 2 的段，再合併成長度 4……需要兩個小工具：「切下前 size 個節點」與「合併後回傳尾巴」。

### 詳解

**為什麼直覺做法不夠**。把值讀進陣列、`sorted` 後寫回，O(n log n) 時間但 O(n) 空間，而且改了值（題目雖然沒禁止，但面試官通常會要求只改指標）。insertion sort 在 linked list 上很自然（147 題），但最差 O(n²)，n = 5 × 10⁴ 時太慢。quicksort 可以做在 linked list 上（把節點分到小於、等於、大於三條 list 再串起來），但 pivot 只能取頭節點或要額外走訪才能隨機選，遇到已排序的輸入會退化成 O(n²)，而且遞迴深度最差 O(n)。heapsort 需要用索引存取父子節點，linked list 做不到。

**突破點：merge sort 天然適合 linked list**。merge sort 的兩個操作「切成兩半」與「合併兩條排序序列」都只需要循序走訪：切半用快慢指標 O(n)，合併用核心題 2 的 dummy ＋ tail，O(n) 而且**不需要額外陣列**（陣列的 merge sort 需要 O(n) 的暫存空間，linked list 只是改指標）。遞迴版 T(n) = 2T(n/2) + O(n) = O(n log n)，遞迴深度 log₂ n，n = 5 × 10⁴ 時約 16 層，Python 完全沒問題；空間 O(log n)。

**做到 O(1) 空間：bottom-up**。遞迴的堆疊只是在記錄「目前在排哪一段」。改成由下往上：第一輪把 list 看成 n 段長度 1 的排序 list，相鄰兩段合併成長度 2；第二輪合併成長度 4；第 r 輪段長是 2ʳ，共 ⌈log₂ n⌉ 輪，每輪走過全部 n 個節點。每一輪從 dummy 開始，重複「切下 size 個當 left、再切下 size 個當 right、合併後接在 tail 後面、tail 移到合併結果的尾巴」，直到這一輪的節點用完。只用固定數量的指標，額外空間 O(1)。

**正確性**。Invariant：第 r 輪開始時，list 由若干段組成，每段長度為 2ʳ（最後一段可能較短），而且每段內部已排序。一輪中把相鄰兩段合併，合併結果是排序的、長度 2ʳ⁺¹（或較短），invariant 對 r + 1 成立。當 size ≥ n 時只剩一段，整條 list 已排序。合併時用 `<=` 讓相等的值保持原本順序，所以這是**穩定**排序。

```text
6 → 5 → 4 → 3 → 2 → 1 → 0（n = 7）

size = 1：切成 [6] [5] | [4] [3] | [2] [1] | [0]
          合併每一對 → [5 6] [3 4] [1 2] [0]
          list：5 → 6 → 3 → 4 → 1 → 2 → 0

size = 2：切成 [5 6] [3 4] | [1 2] [0]
          合併每一對 → [3 4 5 6] [0 1 2]
          list：3 → 4 → 5 → 6 → 0 → 1 → 2

size = 4：切成 [3 4 5 6] [0 1 2]
          合併 → [0 1 2 3 4 5 6]

size = 8 ≥ n，結束
```

每一輪中，「切下 size 個」會把那一段的最後一個節點的 `next` 設成 `None`，讓 left 與 right 成為獨立的 list 才能合併；合併完再接回 tail 後面。size = 1 那一輪最後的 `[0]` 沒有配對的 right（切出來是 `None`），合併時直接整段接上。這個流程和難題 2 的配對合併完全相同，只是一開始有 n 條長度 1 的 list。

### 解法

```python
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def merge(a, b):
    dummy = tail = ListNode()
    while a and b:
        if a.val <= b.val:
            tail.next, a = a, a.next
        else:
            tail.next, b = b, b.next
        tail = tail.next
    tail.next = a or b
    return dummy.next


def sort_list_top_down(head):
    if head is None or head.next is None:
        return head
    slow, fast = head, head.next              # 第一個中點
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
    second, slow.next = slow.next, None
    return merge(sort_list_top_down(head), sort_list_top_down(second))


def split(head, size):
    """切下從 head 開始的前 size 個節點，回傳剩下部分的頭。"""
    for _ in range(size - 1):
        if head is None:
            break
        head = head.next
    if head is None:
        return None
    rest, head.next = head.next, None
    return rest


def merge_after(tail, a, b):
    """把 a、b 合併後接在 tail 後面，回傳合併結果的最後一個節點。"""
    while a and b:
        if a.val <= b.val:
            tail.next, a = a, a.next
        else:
            tail.next, b = b, b.next
        tail = tail.next
    tail.next = a or b
    while tail.next:
        tail = tail.next
    return tail


def sort_list(head):
    n, cur = 0, head
    while cur:
        n, cur = n + 1, cur.next
    dummy = ListNode(0, head)
    size = 1
    while size < n:
        tail, cur = dummy, dummy.next
        while cur:
            left = cur
            right = split(left, size)
            cur = split(right, size)
            tail = merge_after(tail, left, right)
        size *= 2
    return dummy.next


for f in (sort_list, sort_list_top_down):
    assert to_list(f(build([4, 2, 1, 3]))) == [1, 2, 3, 4]
    assert to_list(f(build([-1, 5, 3, 4, 0]))) == [-1, 0, 3, 4, 5]
    assert f(None) is None
    assert to_list(f(build([7]))) == [7]
    assert to_list(f(build([2, 2, 1, 1]))) == [1, 1, 2, 2]
    assert to_list(f(build([6, 5, 4, 3, 2, 1, 0]))) == list(range(7))
    for _ in range(200):
        arr = [random.randint(-5, 5) for _ in range(random.randint(0, 40))]
        assert to_list(f(build(arr))) == sorted(arr)
big = [random.randint(-10**5, 10**5) for _ in range(5 * 10**4)]
assert to_list(sort_list(build(big))) == sorted(big)
a, b = ListNode(1), ListNode(1)                  # 穩定性：相等的值保持原順序
a.next = b
res = sort_list(a)
assert res is a and res.next is b
print("all tests passed")
```

### 複雜度與邊界

兩個版本時間都是 O(n log n)：共 ⌈log₂ n⌉ 層（或輪），每層的切分與合併合計 O(n)。bottom-up 版額外空間 O(1)；top-down 版是 O(log n) 的遞迴堆疊。bottom-up 的 `merge_after` 最後會走到合併結果的尾巴，這段走訪的總量每輪不超過 n，不影響複雜度。邊界情況：n = 0 或 1 時 `size < n` 不成立，直接回傳；最後一段不足 size 個時 `split` 提早遇到 `None` 並回傳 `None`，right 為空的合併等於直接接上 left；每輪結束時 tail 是最後一個節點，它的 `next` 因為最後一次 `split` 而是 `None`，不會殘留舊連結；重複值用 `<=` 保持穩定。

### Follow-up

> [!question]- F1. 為什麼不用 quicksort？在 linked list 上能做嗎？
> 能做：取頭節點當 pivot，走一次把其他節點分到 less、equal、greater 三條 list（用三組 dummy ＋ tail，依原順序接上，所以是穩定的），遞迴排序 less 和 greater，再串成 `less → equal → greater`。平均 O(n log n)，但 pivot 不能 O(1) 隨機選（要隨機選得先走到第 r 個節點，多一次 O(n)），對已排序或接近排序的輸入取頭節點會退化成 O(n²)、遞迴深度 O(n)。merge sort 則保證 O(n log n)，且 bottom-up 能做到 O(1) 空間，所以 linked list 排序的標準答案是 merge sort。三路切分在大量重複值時特別有效，因為 equal 那一段不再遞迴。

> [!question]- F2. 如果 list 已經「幾乎排好」，每個節點離正確位置最多 d 格呢？
> insertion sort（147. Insertion Sort List）在這種輸入下很快：用 dummy 維護已排序的部分，每拿到一個節點，若它不小於已排序部分的尾巴就直接接上（O(1)），否則從頭找插入位置。這種從頭找的做法最差仍是 O(n²)；要穩定得到 O(n · d)，需要能從尾巴往回找（雙向 list），或改用「大小 d + 1 的 min-heap 滑動」：依序把節點推入 heap，heap 超過 d + 1 個就彈出最小的接上，O(n log d)。這是第 14 章 heap 的典型用法，也說明排序演算法的選擇取決於輸入分佈。

> [!question]- F3. 如果節點值的範圍很小（例如 0 到 100）呢？
> 用 counting sort 的 linked list 版本：準備 V 個桶（每個桶是一組 dummy ＋ tail），走一次把每個節點接到對應值的桶尾，再依序把非空的桶串起來。時間 O(n + V)、額外空間 O(V)，而且只改指標、保持穩定。值域是 `-10⁵` 到 `10⁵` 時 V = 2 × 10⁵ 也還能接受；若值是任意整數，可以做 radix sort（每一位數一輪桶分配），O(n · 位數)。面試官問這題是想確認你知道比較排序的 Ω(n log n) 下限只適用於「只能比較」的情況。

> [!question]- F4. 如果 list 已經依「絕對值」排序，要改成依實際值排序呢（2046. Sort Linked List Already Sorted Using Absolute Values）？
> 依絕對值排序時，非負數本來就是遞增的；負數依絕對值遞增，代表它們的實際值是**遞減**的。所以只要走一次，把每個遇到的負數節點拿下來插到 list 最前面：後遇到的負數絕對值較大、實際值較小，插到最前面剛好成為更前面的元素。時間 O(n)、空間 O(1)。例如 `0 → 2 → -5 → 5 → 10 → -10` 依序把 −5、−10 移到最前面，得到 `-10 → -5 → 0 → 2 → 5 → 10`。這是「利用輸入的額外結構，打敗通用排序」的典型例子。

### 心得

關鍵突破是看出 merge sort 的「切半」與「合併」都只需要循序走訪，所以它是 linked list 上最自然的 O(n log n) 排序，而且合併不需要陣列版那 O(n) 的暫存空間；再把遞迴改成 bottom-up，就連 O(log n) 的堆疊都省掉。它是本章零件的總複習：快慢指標找中點（top-down）、切斷 `next`、核心題 2 的合併、難題 2 的配對合併。面試時建議先寫 top-down 版（短、不易錯），說明空間是 O(log n)；如果面試官要求 O(1)，再說明 bottom-up 的想法並寫出 `split` 與 `merge_after` 兩個小工具，有這兩個工具，主迴圈只有五行。

## 難題 5｜1171. Remove Zero Sum Consecutive Nodes from Linked List｜Medium

### 題目

給一條 linked list 的頭節點 `head`，反覆刪除任何「節點值總和為 0 的連續節點序列」，直到 list 中再也沒有這樣的序列，回傳最後的頭節點。刪除的順序不同可能得到不同的結果，回傳任何一個合法的最終結果都可以。限制：節點數在 1 到 1000 之間，節點值在 `-1000` 到 `1000` 之間。

- 範例 1：`1 → 2 → -3 → 3 → 1`，回傳 `3 → 1`（刪除 `1, 2, -3`）；`1 → 2 → 1`（刪除 `-3, 3`）也是合法答案。
- 範例 2：`1 → 2 → 3 → -3 → 4`，回傳 `1 → 2 → 4`。
- 範例 3：`1 → 2 → 3 → -3 → -2`，回傳 `1`（先刪 `3, -3`，剩下 `1 → 2 → -2`，再刪 `2, -2`）。
- 範例 4（邊界）：`0`，回傳 `None`；`1 → -1`，回傳 `None`（整條都被刪掉）。

### 提示

> [!tip]- 提示 1
> 「連續區段的和為 0」可以用 prefix sum（前綴和，第 7 章）改寫：第 i + 1 到第 j 個節點的和為 0，等價於前 i 個與前 j 個的 prefix sum 相等。

> [!tip]- 提示 2
> 在 head 前面放一個值為 0 的 dummy，讓每個節點都有 prefix sum。如果某個 prefix sum 值出現在兩個節點 p 和 q（p 在前），那 p 之後到 q 為止的節點和為 0，可以整段跳過：`p.next = q.next`。

> [!tip]- 提示 3
> 第一次走訪用 hash map 記錄每個 prefix sum **最後一次出現**的節點；第二次走訪重新累加 prefix sum，對每個節點令 `cur.next = last[sum].next`，直接跳到同一個 prefix sum 的最後位置之後。

### 詳解

**為什麼直覺做法不夠**。直接模擬：每次從每個起點往後累加，找到和為 0 的區段就刪掉，再從頭重來。找一個區段最差 O(n²)，最多刪 O(n) 次，總共 O(n³)；即使每次刪完不從頭開始，也很難避免重複掃描，因為刪掉一段之後，原本不相鄰的節點變相鄰，可能形成新的零和區段（範例 3 的 `2, -2` 就是刪掉 `3, -3` 之後才出現的）。真正的問題是：我們在「節點值」上找零和區段，而零和區段的結構在 prefix sum 上看得更清楚。

**轉成 prefix sum**。令 dummy 的 prefix sum 為 0，第 j 個節點的 prefix sum 為 Pⱼ = 前 j 個節點值的和。第 i + 1 到第 j 個節點的和是 Pⱼ − Pᵢ，所以「這段和為 0」⇔ Pᵢ = Pⱼ。刪除這段之後，後面節點的 prefix sum **不會改變**，因為被刪掉的部分總和為 0。這個性質非常關鍵：刪除操作不影響任何保留節點的 prefix sum，所以可以在原始的 prefix sum 上一次規劃好所有刪除。

**兩次走訪**。第一次走訪計算每個節點的 prefix sum，用 hash map `last[s]` 記錄 prefix sum 為 s 的**最後一個**節點（後出現的覆蓋先出現的）。第二次走訪從 dummy 開始重新累加 s，對每個走到的節點令 `cur.next = last[s].next`：如果這個 prefix sum 之後還會再出現，就把中間整段（和為 0）跳過；如果 cur 自己就是最後一次出現，`last[s]` 就是 cur，這行等於什麼都不做。因為跳過的區段和為 0，跳過之後下一個節點的 prefix sum 與原本相同，第二次走訪累加出的 s 與第一次一致。

**正確性**。兩件事要證明。第一，每次跳過的都是一段和為 0 的連續節點，而且各段互不重疊，所以這相當於依序做了若干次合法刪除。第二，結果中不再有零和區段：保留下來的節點，prefix sum 兩兩不同，因為走到 prefix sum 為 s 的節點時，我們直接跳到 s 最後一次出現之後，後面不可能再遇到 s；而保留節點之間沒有兩個相等的 prefix sum，就代表沒有任何連續區段的和為 0。dummy 的 prefix sum 0 也參與這個論證，所以「從開頭到某處和為 0」（例如範例 4 整條刪光）也會被處理。

```text
3 → 4 → -7 → 5 → -6 → 6

節點：    dummy   3    4   -7    5   -6    6
prefix：    0     3    7    0    5   -1    5

第一次走訪：last[s] = prefix 為 s 的最後一個節點
  last[0] = -7   last[3] = 3   last[7] = 4   last[5] = 6（後面的 6 覆蓋了 5）   last[-1] = -6

第二次走訪：
  cur = dummy，s = 0  → dummy.next = last[0].next = 5      （跳過 3, 4, -7）
  cur = 5，    s = 5  → 5.next     = last[5].next = None   （跳過 -6, 6）
  cur = None，結束

結果：5
```

第二次走訪只走了兩個節點：dummy 的 prefix sum 0 最後出現在 −7，所以 `3, 4, -7` 整段（和為 0）被跳過；接著 5 的 prefix sum 5 最後出現在最後的 6，所以 `-6, 6`（和為 0）被跳過。最終只剩 `5`。驗證：原 list 先刪 `3, 4, -7` 得 `5 → -6 → 6`，再刪 `-6, 6` 得 `5`，確實是合法的刪除序列。

### 解法

```python
import random


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(values):
    dummy = tail = ListNode()
    for v in values:
        tail.next = ListNode(v)
        tail = tail.next
    return dummy.next


def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out


def remove_zero_sum_sublists(head):
    dummy = ListNode(0, head)
    last, s, cur = {}, 0, dummy
    while cur:                          # 第一次：prefix sum → 最後出現的節點
        s += cur.val
        last[s] = cur
        cur = cur.next
    s, cur = 0, dummy
    while cur:                          # 第二次：跳到同一個 prefix sum 的最後位置之後
        s += cur.val
        cur.next = last[s].next
        cur = cur.next
    return dummy.next


def has_zero_segment(arr):
    seen, s = {0}, 0
    for x in arr:
        s += x
        if s in seen:
            return True
        seen.add(s)
    return False


def reachable_results(arr):
    """暴力列舉所有刪除順序可能得到的最終結果（只用於小測資）。"""
    stack, seen, finals = [tuple(arr)], set(), set()
    while stack:
        t = stack.pop()
        if t in seen:
            continue
        seen.add(t)
        moved = False
        for i in range(len(t)):
            s = 0
            for j in range(i, len(t)):
                s += t[j]
                if s == 0:
                    moved = True
                    stack.append(t[:i] + t[j + 1:])
        if not moved:
            finals.add(t)
    return finals


assert to_list(remove_zero_sum_sublists(build([1, 2, -3, 3, 1]))) == [3, 1]
assert to_list(remove_zero_sum_sublists(build([1, 2, 3, -3, 4]))) == [1, 2, 4]
assert to_list(remove_zero_sum_sublists(build([1, 2, 3, -3, -2]))) == [1]
assert remove_zero_sum_sublists(build([0])) is None
assert remove_zero_sum_sublists(build([1, -1])) is None
assert to_list(remove_zero_sum_sublists(build([3, 4, -7, 5, -6, 6]))) == [5]
for _ in range(500):
    arr = [random.randint(-3, 3) for _ in range(random.randint(1, 8))]
    res = to_list(remove_zero_sum_sublists(build(arr)))
    assert not has_zero_segment(res)
    assert tuple(res) in reachable_results(arr)          # 是某個合法刪除順序的結果
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：兩次走訪，每次 hash map 操作平均 O(1)。空間 O(n)：hash map 最多存 n + 1 個不同的 prefix sum。邊界情況：值為 0 的單一節點本身就是零和區段，它的 prefix sum 與前一個節點相同而被跳過；整條 list 和為 0 時 dummy 的 `last[0]` 是最後一個節點，`dummy.next` 變成 `None`；dummy 的值必須是 0，否則 prefix sum 全部偏移，「從開頭開始的零和區段」就抓不到；第二次走訪必須從 dummy 開始並重新累加，不能沿用第一次的 s。

### Follow-up

> [!question]- F1. 能不能只走一次，例如節點是以串流的方式一個個送來？
> 可以，維護 `seen[s]` = 目前保留的 list 中 prefix sum 為 s 的節點。每來一個節點，先把它接到 tail 後面並累加 s；若 s 已在 `seen` 中，令 `p = seen[s]`，則 p 之後到目前節點這一段和為 0：先從 `p.next` 走到目前節點的前一個，沿途重新累加、把這些節點的 prefix sum 從 `seen` 刪掉（它們即將被移除；目前節點的 prefix sum 等於 p 的，不能刪），再令 `p.next = None`、`tail = p`；否則記錄 `seen[s] = 新節點` 並讓 tail 前進。每個節點最多被加入與刪除各一次，均攤 O(n) 時間、O(n) 空間，而且任何時刻保留的 list 都沒有零和區段，可以隨時輸出目前的結果。

> [!question]- F2. 不同的刪除順序會得到不同長度的結果嗎？如果要讓結果最短呢？
> 會。`5 → -5 → 7 → -2 → 4` 若先刪 `5, -5` 得 `7 → -2 → 4`（長度 3，不再有零和區段）；若刪 `-5, 7, -2` 則得 `5 → 4`（長度 2）。本題的兩次走訪會得到前者，所以它不保證最短。要求最短時用 DP：把 prefix sum 位置 0 到 n 當成節點，從 i 到 i + 1 代表保留第 i + 1 個節點（成本 1），從 i 跳到任何 j > i 且 Pⱼ = Pᵢ 代表刪掉中間（成本 0），最短結果就是從 0 到 n 的最小成本。依序計算 `best[i] = min(best[i − 1] + 1, 同一 prefix sum 先前位置的最小 best)`，用 hash map 記錄每個 prefix sum 的最小 best，O(n) 時間與空間。最短的結果一定沒有零和區段，否則還能再刪。

> [!question]- F3. 如果不刪除，而是問有幾個零和的連續區段，或最長的零和區段多長呢？
> 都是同一個 prefix sum 轉換。計數：走訪時用 hash map 記錄每個 prefix sum 出現的次數，每遇到 s，答案加上 `count[s]`（之前每個相同的 prefix sum 都和現在形成一個零和區段），再把 `count[s]` 加一，這是第 7 章核心題 2（560）在 k = 0 的特例，O(n)。最長：記錄每個 prefix sum **第一次**出現的位置，遇到 s 時用 `目前位置 − first[s]` 更新答案，O(n)；與本題用「最後一次出現」剛好相反，因為本題要盡量往後跳。

> [!question]- F4. 如果要刪除的是「總和為 k」的連續區段（k ≠ 0）呢？
> 這會失去本題最重要的性質：刪除一段和為 k 的區段後，後面所有節點的 prefix sum 都減少 k，原本規劃好的跳躍位置就不再成立，所以不能一次用 hash map 決定所有刪除。若題目只要求「刪除一次」（例如找出第一個和為 k 的區段並刪除），可以用 prefix sum 與 hash map 在 O(n) 內找到：記錄每個 prefix sum 最早出現的節點，遇到 s 時查 `s − k`。若要求反覆刪除直到沒有，就需要模擬，並在每次刪除後更新後續 prefix sum，最差 O(n²)。面試時指出「和為 0 時刪除不改變 prefix sum」正是本題能 O(n) 的原因，就是最好的回答。

### 心得

關鍵突破是把「連續區段和為 0」改寫成「兩個 prefix sum 相等」，並看出刪除零和區段不會改變其他節點的 prefix sum，所以可以在原始 prefix sum 上一次規劃所有跳躍。它是本章唯一以 hash map 為主角的題目，和難題 3（138）一樣，說明 linked list 題也常需要「節點 → 資訊」的對應表；它的 prefix sum 部分則與第 7 章同源。面試時先舉一個「刪除後才出現新零和區段」的例子（範例 3）說明為什麼直接模擬很麻煩，再寫出 prefix sum 表、說明 dummy 的 0 代表空前綴，最後用「保留節點的 prefix sum 兩兩不同」證明結果正確；若面試官追問最短結果，就接到 F2 的 DP。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 反轉 | 整條、一段、每 k 個一組反轉，要求 O(1) 空間 | prev／cur／nxt；反轉一段時 `prev` 初值設為段後節點 | 核心題 1（206）、難題 1（25）、92、24、2074 |
| 快慢指標（速度差） | 找中點、判斷環、找環入口 | slow 一步、fast 兩步；入口用「head 與相遇點同速出發」 | 核心題 3（141／142）、876、202、287（第 5 章難題 2） |
| 前後指標（間距固定） | 倒數第 k 個、旋轉、兩條 list 交會 | fast 先走 k（或 k + 1）步，兩者同速前進 | 核心題 4（19）、61、160 |
| dummy ＋ tail 接線 | 合併、分割、刪除，頭節點可能改變 | dummy 統一處理頭；tail 永遠指向結果尾端；剩下的整段一次接上 | 核心題 2（21）、203、86 Partition List、328 |
| 切半 ＋ 反轉 ＋ 合併 | 首尾配對、交錯重排、回文 | 第一個中點切開、反轉後半、兩條同步走 | 核心題 5（143）、234、2130 |
| 多路合併 | k 條排序 list | min-heap 放 `(val, idx, node)`，或兩兩配對合併 | 難題 2（23）、373、第 14 章難題 4（632） |
| 分治排序 | 排序 linked list，要求 O(n log n) | merge sort；O(1) 空間用 bottom-up 的 `split` ＋ `merge_after` | 難題 4（148）、147（insertion sort）、2046 |
| hash map 輔助 | 額外指標要深複製、區段和、相交 | 節點身分當 key；或把對應關係藏進 list 結構（交錯插入） | 難題 3（138）、難題 5（1171）、133（第 15 章核心題 2） |
| 雙向 list ＋ hash map | 設計 O(1) 的移到最前面、刪除任意節點 | 雙向 list 支援 O(1) 拿下節點，hash map 支援 O(1) 找到節點 | 146 LRU Cache（第 27 章核心題 1）、460 LFU Cache（第 27 章難題 1） |

**下限與上限**。最簡單的形式是單一零件：206 反轉、21 合併、876 找中點、141 判斷環，考的是能不能一次寫對、說清楚 invariant。中間層是零件的組合或加上一個觀察：143 是三個零件串起來，19 的「間距 n + 1 ＋ dummy」、142 的入口推導都需要一個額外的論證。上限的題目難在三個方向：第一，**接線複雜度**，例如 25 每一組要同時管四個指標，任何一條接線錯都會斷鏈；第二，**空間限制逼出非直覺結構**，例如 148 的 bottom-up 與 138 的交錯插入，都是為了把 O(n) 或 O(log n) 的輔助空間壓到 O(1)；第三，**需要另一個 pattern 的觀察**，例如 23 需要 heap 或分治的複雜度分析、1171 需要 prefix sum 與「刪除不改變 prefix sum」的性質。

**與其他 pattern 的關係**。快慢指標本質上是第 5 章 two pointers 在「不能隨機存取」時的版本：陣列可以從兩端往中間走，linked list 只能同向走，所以改用速度差或間距；而 287 Find the Duplicate Number 反過來把陣列看成隱含的 linked list，借用 Floyd 演算法。k-way merge 是第 14 章 heap 的主要應用之一。1171 的 prefix sum 與 hash map 與第 7 章同源。linked list 的遞迴（反轉、合併）和第 12 章樹的遞迴寫法相似，但深度是 O(n) 而不是 O(log n)，在 Python 中要特別注意遞迴上限；樹與 list 之間的轉換（114 Flatten Binary Tree to Linked List、109 Convert Sorted List to Binary Search Tree）也常作為 follow-up 出現。

**容易混淆之處**。第一，兩種中點：`while fast and fast.next` 得到第二個中點，`while fast.next and fast.next.next` 得到第一個中點；要切開時用第一個。第二，判斷相遇或交會時用 `is` 比較節點身分，不要用值。第三，「O(1) 空間」常常是以「暫時修改輸入」換來的（234 回文、138 交錯、143 重排），在唯讀或並行的情境下不能用，要能主動說明。第四，看到 linked list 不代表一定要原地操作：如果題目允許 O(n) 空間，轉成陣列往往更簡單，面試時先說這個基準解，再說明如何做到 O(1)。

## 本章重點整理

- Linked list 題的難點在指標改寫順序，不在演算法；改任何 `next` 之前，先問「原本指向的節點之後還需要嗎」，需要就先存起來。
- 三個基本零件：反轉（prev／cur／nxt）、快慢指標（速度差找中點與環、間距固定找倒數第 k 個）、dummy ＋ tail 接線（合併與分割）；大部分題目都是它們的組合。
- 只要頭節點可能改變（刪除、合併、反轉一段），就在前面放 dummy，最後回傳 `dummy.next`。
- 反轉的 invariant 是「prev 是已處理前綴的反轉、cur 是未處理的後綴」；反轉一段時把 `prev` 初值設成段後節點，反轉後就自動接上。
- 要把 list 切成兩半時，用第一個中點（`while fast.next and fast.next.next`），並立刻 `mid.next = None`，否則會形成環。
- Floyd 判環：有環時 slow 與 fast 必在 slow 進環後一圈內相遇，相遇步數 t 是環長的倍數；從 head 與相遇點同速出發，相遇處就是入口。
- 倒數第 n 個：兩個指標都從 dummy 出發、間距 n + 1，fast 到 `None` 時 slow 是目標的前一個，刪除頭節點也不必特判。
- 合併 k 條排序 list 是 O(N log k)：heap 放 `(val, idx, node)` 避免比較節點，或兩兩配對合併；逐條合併是 O(kN)。
- Linked list 排序用 merge sort：top-down 是 O(log n) 空間，bottom-up（`split` ＋ `merge_after`）是 O(1) 空間，合併用 `<=` 保持穩定。
- 帶 random 指標的深複製：hash map 用節點身分當 key（O(n) 空間），或交錯插入 `A → A' → B → B'` 讓 `X.next` 成為複製品（O(1) 額外空間，但會暫時修改輸入）。
- 零和連續區段 ⇔ 兩個 prefix sum 相等；刪除零和區段不改變其他節點的 prefix sum，所以可以用「最後一次出現」的 hash map 一次跳完。
- 遞迴寫法的深度是 O(n)，Python 預設上限約 1000；面試時可以用遞迴說明思路，但最終答案給迭代版，並主動提出這個限制。
