---
chapter: 27
title: 資料結構設計
part: 6
---

# 第 27 章　資料結構設計

> [!abstract] 本章地圖
> **一句話**：設計題不是發明新結構，而是先替每個操作定下目標複雜度，再找出「哪個基本結構負責哪個操作」，把兩三個結構用指標或索引互相連起來，並在每次修改後維持它們之間的 invariant。
>
> **辨識訊號**：
> - 題目給一個 class 介面（`get`、`put`、`insert`、`pop`…），要求「每個操作平均 O(1)」或「O(log n)」
> - 同一份資料要同時支援「依 key 查找」和「依某種順序取出」（最近使用、最少使用、最大值、最高頻率）
> - 要從集合中間刪除任意元素，但原本的結構（stack、heap、array）只擅長處理一端
> - 要在 O(1) 內隨機取樣，或要回到過去某個時間點、某個版本的狀態
> - 操作是串流式的、彼此交錯的，無法先看完所有輸入再一次處理
>
> **核心題**：146、380、981、1472、341
>
> **難題**：460、432、716、895、1146

## 27.1 這個 Pattern 解決什麼問題

先看一個最小的例子。你要做一個快取（cache），容量 2，支援 `get(key)` 與 `put(key, value)`，容量滿了就丟掉「最久沒被使用」的那一個。最直接的做法是用一個 list 依使用時間排好所有 key：`get` 時在 list 裡找到 key、把它搬到最後；`put` 滿了就刪掉 list 的第一個。這個做法完全正確，但每次「找到 key」與「從中間刪除」都是 O(n)。如果改用 dict，查找變成 O(1)，可是 dict 不知道誰最久沒用，淘汰時又得掃一遍。兩個結構各自只擅長一半的操作。

設計題的核心就在這裡：**沒有任何單一的內建結構能讓所有操作都快，但兩個結構組合起來可以**。dict 負責「給 key，O(1) 找到它在哪裡」；雙向 linked list 負責「給節點，O(1) 把它拿下來、放到最前面、刪掉最後一個」。dict 的 value 不存資料本身，而是存 linked list 的節點，讓兩個結構互相指向。這樣 `get` 與 `put` 都只做常數次的指標操作，就是核心題 1（146. LRU Cache）。

本章十題都是同一種思考方式的練習：列出操作、定下每個操作的目標複雜度、找出瓶頸操作、挑一個能處理瓶頸的結構，再用 hash map 把「key → 它在那個結構裡的位置」連起來。差別只在瓶頸是什麼：LRU 的瓶頸是「從中間移走」（用 linked list），RandomizedSet 的瓶頸是「隨機取一個」（用 array），Max Stack 的瓶頸是「取最大值但還要保留 stack 順序」（用 heap 加 lazy deletion），Time Map 與 Snapshot Array 的瓶頸是「回到過去的版本」（用排序的版本串列加 binary search）。

設計題在面試裡還有另一層考點：它的程式比較長、狀態比較多，很容易某個操作忘了同步更新其中一個結構。所以面試官看的不只是你選對結構，還有你**能不能明說每個結構之間的 invariant（不變式）**、能不能先把介面與測試寫出來、寫完能不能自己找出不同步的 bug。L5 等級的表現是：結構選擇一次到位，複雜度說得出理由，邊界（容量 0、重複 key、空集合、同一時間點覆寫）主動處理，追問 thread safety（執行緒安全）或分散式時能具體說出鎖在哪裡、資料怎麼切。

## 27.2 辨識訊號

| 題目特徵 | 為什麼是資料結構設計 | 本章哪一題 |
|---|---|---|
| 「最近最少使用」「最久沒存取的淘汰」，所有操作 O(1) | 需要 O(1) 查找＋O(1) 調整順序：hash map 指向雙向 linked list 的節點 | 核心題 1（146） |
| 插入、刪除、隨機取一個，全部 O(1) | 隨機取樣需要連續陣列；刪除用「和最後一個交換再 pop」，hash map 記住每個值的索引 | 核心題 2（380） |
| 依時間戳記查「當時的值」，時間戳記遞增寫入 | 每個 key 一條依時間排序的版本串列，查詢用 binary search 找 floor | 核心題 3（981）、難題 5（1146） |
| 上一頁、下一頁、新開頁面清掉前進紀錄 | 一個陣列加「目前位置」與「有效結尾」兩個指標，截斷用移動指標代替刪除 | 核心題 4（1472） |
| 把巢狀結構「攤平」但要逐個取出，不能先全部展開 | iterator（迭代器）要保存「走到哪裡」的狀態，用 stack 模擬遞迴 | 核心題 5（341） |
| 「最少使用次數」淘汰，同次數再比最近使用 | 次數 → 一串依時間排序的 key（多層 hash），再記錄目前的最小次數 | 難題 1（460） |
| 次數加一減一，隨時要最大與最小次數的 key，全部 O(1) | 次數每次只變 1，把「次數桶」串成雙向 linked list，key 只在相鄰桶之間移動 | 難題 2（432） |
| Stack 但還要 popMax，刪除會發生在中間 | 兩個結構各自維持一種順序，被另一邊刪掉的元素用 lazy deletion 跳過 | 難題 3（716） |
| 依「頻率最高、同頻率取最近」彈出 | 頻率每次只變 1；每個頻率一個 stack，元素在每個頻率層各出現一次 | 難題 4（895） |
| 很多次「快照」，只有少數位置被改 | 不複製整份資料，每個位置只記錄被修改過的版本（copy-on-write 的精神） | 難題 5（1146） |

一個實用的反向檢查：如果所有操作都可以先讀完再一次處理（offline，離線），那通常不是設計題，排序或 prefix sum 就能解；如果某個操作的目標複雜度你說不出來，先問面試官，因為設計題的答案幾乎完全由「哪個操作必須快」決定。

## 27.3 設計方法：從每個操作的目標複雜度出發

面試中的設計題通常只給介面和一句「盡量快」。不要直接開始寫程式，先花兩分鐘做以下四步，並且說出口：

1. **列出操作與目標複雜度**。把每個方法寫成一列：它的輸入、輸出、要多快。若題目沒說，就提出合理目標並和面試官確認，例如「我希望 get 與 put 都是 O(1)」。有時候不同操作的頻率差很多（讀遠多於寫），可以故意讓一個操作慢一點換另一個快，這個取捨也要說出來。
2. **找出瓶頸操作**。逐一問「如果只用 dict（或只用 list），哪個操作會變慢？」。慢的那個就是瓶頸，它決定你要加入什麼結構：從中間刪除 → 雙向 linked list；隨機取樣或依索引存取 → 陣列；取最大／最小且會變動 → heap 或有序結構；查歷史版本 → 排序的版本串列＋binary search。
3. **用 hash map 把結構連起來**。第二個結構通常無法依 key 查找，所以 hash map 的 value 要存「這個 key 在第二個結構裡的位置」：節點參考、陣列索引、所屬的桶。這一步是 O(1) 的來源，也是 bug 的來源，因為位置會變（陣列交換、節點搬桶），每次變動都要同步更新 hash map。
4. **寫下 invariant，再寫程式**。例如 LRU 的 invariant 是「dict 的 key 集合等於 linked list 的節點集合，而且 list 從頭到尾依最近使用排序」。每個方法寫完，都檢查一次它是否維持了每一條 invariant。

下表是本章四種最常見的組合，幾乎所有 O(1)／O(log n) 的設計題都是它們的變形：

| 組合 | 主結構負責 | Hash map 存什麼 | 典型操作 | 本章題目 |
|---|---|---|---|---|
| hash ＋ 雙向 linked list | 維持順序，O(1) 移出任意節點、O(1) 放到頭尾 | key → 節點 | 最近使用、移到最前、淘汰最舊 | 146、460、432 |
| hash ＋ array | 連續儲存，O(1) 依索引存取與隨機取樣 | 值 → 索引（1472 只依位置存取，不需要 hash） | 刪除時和最後一個交換再 pop | 380、1472 |
| heap ＋ lazy deletion | 隨時取最大／最小 | 「已刪除」的 id 集合 | 刪除時只做記號，取頂時才清掉 | 716 |
| 多層 hash | 第一層分群（次數、key），第二層存群內的元素或版本 | key → 次數、次數 → 群、key → 版本串列 | 依次數或依時間分層 | 460、895、981、1146 |

選擇時要注意 Python 的特性。`dict` 保留插入順序，`collections.OrderedDict` 還支援 `move_to_end` 與 `popitem(last=False)`，兩者都是 O(1)，等於內建了「hash ＋ 雙向 linked list」；面試時可以先用它寫出正確版本，再依面試官要求手寫節點版本。Python 標準函式庫沒有平衡二元搜尋樹，需要「有序且可刪除任意元素」時，常見的替代是 heap 加 lazy deletion，或在值域有限時用 bucket（桶）。

## 27.4 模板與原理：四個基本零件

下面這段程式是本章所有題目會用到的四個零件。每個零件都很短，但都有一條必須維持的 invariant，寫在註解裡。

```python
import heapq
import random
from collections import defaultdict


class Node:
    __slots__ = ("key", "val", "prev", "next")

    def __init__(self, key=None, val=None):
        self.key, self.val = key, val
        self.prev = self.next = None


class DList:
    """帶兩個 sentinel 的雙向 linked list。
    invariant：head.next … tail.prev 是所有真實節點，每個節點 prev.next is self 且 next.prev is self。"""

    def __init__(self):
        self.head, self.tail = Node(), Node()
        self.head.next, self.tail.prev = self.tail, self.head
        self.size = 0

    def push_front(self, node):
        node.prev, node.next = self.head, self.head.next
        self.head.next.prev = node
        self.head.next = node
        self.size += 1

    def remove(self, node):
        node.prev.next, node.next.prev = node.next, node.prev
        node.prev = node.next = None
        self.size -= 1

    def pop_back(self):
        node = self.tail.prev
        self.remove(node)
        return node

    def keys(self):
        out, cur = [], self.head.next
        while cur is not self.tail:
            out.append(cur.key)
            cur = cur.next
        return out


class IndexedSet:
    """hash ＋ array。invariant：pos[items[i]] == i 對所有 i 成立。"""

    def __init__(self):
        self.items, self.pos = [], {}

    def add(self, x):
        if x in self.pos:
            return False
        self.pos[x] = len(self.items)
        self.items.append(x)
        return True

    def discard(self, x):
        if x not in self.pos:
            return False
        i, last = self.pos.pop(x), self.items.pop()
        if i < len(self.items):          # x 不是最後一個：把最後一個搬到洞裡
            self.items[i] = last
            self.pos[last] = i
        return True

    def choice(self, rng=random):
        return self.items[rng.randrange(len(self.items))]


class LazyMaxHeap:
    """heap ＋ lazy deletion。invariant：heap 中「沒被標記刪除」的 id 恰好是目前的元素。"""

    def __init__(self):
        self.heap, self.dead = [], set()

    def push(self, priority, ident):
        heapq.heappush(self.heap, (-priority, ident))

    def discard(self, ident):
        self.dead.add(ident)             # 只做記號，O(1)

    def _clean(self):
        while self.heap and self.heap[0][1] in self.dead:
            self.dead.remove(heapq.heappop(self.heap)[1])

    def top(self):
        self._clean()
        return (-self.heap[0][0], self.heap[0][1]) if self.heap else None


class CountBuckets:
    """多層 hash：key → 次數，次數 → key 集合。invariant：key 在 buckets[count[key]] 裡，且只在那裡。"""

    def __init__(self):
        self.count = defaultdict(int)
        self.buckets = defaultdict(set)

    def inc(self, key):
        c = self.count[key]
        if c:
            self.buckets[c].discard(key)
            if not self.buckets[c]:
                del self.buckets[c]
        self.count[key] = c + 1
        self.buckets[c + 1].add(key)


d = DList()
nodes = {k: Node(k) for k in "abc"}
for k in "abc":
    d.push_front(nodes[k])
assert d.keys() == ["c", "b", "a"]
d.remove(nodes["b"])
d.push_front(nodes["b"])
assert d.keys() == ["b", "c", "a"] and d.pop_back().key == "a" and d.size == 2

s = IndexedSet()
assert s.add(1) and s.add(2) and s.add(3) and not s.add(2)
assert s.discard(1) and not s.discard(1)
assert sorted(s.items) == [2, 3] and all(s.pos[v] == i for i, v in enumerate(s.items))
assert s.choice(random.Random(0)) in (2, 3)

h = LazyMaxHeap()
for ident, pr in enumerate([5, 9, 7]):
    h.push(pr, ident)
assert h.top() == (9, 1)
h.discard(1)
assert h.top() == (7, 2)
h.discard(2)
h.discard(0)
assert h.top() is None and not h.dead          # 每個標記都被清掉一次

b = CountBuckets()
for k in "ababa":
    b.inc(k)
assert b.count == {"a": 3, "b": 2} and b.buckets == {3: {"a"}, 2: {"b"}}
print("all tests passed")
```

**每個零件為什麼這樣寫**：

- `DList` 用兩個 sentinel（哨兵節點）`head` 與 `tail`，真實節點永遠夾在中間，所以 `remove` 不必判斷「是不是第一個」「是不是最後一個」「list 是否只剩一個」，四行指標就寫完。節點同時存 `key`，因為淘汰 `tail.prev` 時要知道該刪 dict 的哪個 key；這是 LRU 最常忘記的一點。
- `IndexedSet.discard` 先把最後一個元素 pop 出來，如果被刪的不是它，再把它放進洞裡並更新它的索引。這個順序可以自然處理「刪的就是最後一個」的情況；若先寫 `items[i] = items[-1]` 再 pop，刪最後一個時要另外小心 `pos` 不要被寫回去。
- `LazyMaxHeap` 不在 heap 中間刪除（heapq 不支援，即使支援也要 O(n) 找位置），而是把 id 放進 `dead`，取頂時才把頂端的死元素彈掉。每個元素最多被 push 一次、pop 一次，所以清理的總成本被 push 的次數攤平，`top` 是 amortized（攤還）O(log n)。id 必須唯一；若用值本身當 id，同一個值出現兩次時就分不清刪的是哪一個。
- `CountBuckets` 是多層 hash 的最小形式。兩層之間的 invariant 是「key 只出現在它目前次數的桶裡」，所以每次改次數都是「從舊桶拿出、放入新桶、舊桶空了就刪掉」三步。空桶不刪會讓「找最大／最小次數」誤判。

## 27.5 Invariant 的維護：每個方法結束時都要成立

設計題的 bug 幾乎都不是演算法錯，而是**兩個結構不同步**：dict 裡還有 key，linked list 裡已經沒有節點；陣列交換了位置，索引表卻沒改；heap 頂端是一個早就被刪掉的元素。避免這類 bug 的方法是：把 invariant 寫成程式，在測試時每次操作後都檢查一次。

```python
import random


class LRUWithCheck:
    """LRU（dict 保留插入順序：前面是最舊的）加上 invariant 檢查。"""

    def __init__(self, capacity):
        self.cap, self.data = capacity, {}

    def get(self, key):
        if key not in self.data:
            return -1
        self.data[key] = self.data.pop(key)       # 移到最後 = 最近使用
        return self.data[key]

    def put(self, key, value):
        self.data.pop(key, None)
        if len(self.data) == self.cap:
            del self.data[next(iter(self.data))]  # 刪掉最舊的
        self.data[key] = value

    def check(self, history):
        """history 是依時間排序的存取紀錄；invariant：data 恰好是最近使用的 cap 個不同 key，且由舊到新排列。"""
        assert len(self.data) <= self.cap
        seen, recent = set(), []
        for k in reversed(history):
            if k not in seen:
                seen.add(k)
                recent.append(k)
        assert list(self.data) == list(reversed(recent[: self.cap]))


rng = random.Random(1)
cache, history = LRUWithCheck(3), []
for _ in range(2000):
    k = rng.randint(0, 5)
    if rng.random() < 0.5:
        hit = cache.get(k) != -1
        if hit:
            history.append(k)
    else:
        cache.put(k, rng.randint(0, 9))
        history.append(k)
    cache.check(history)
assert cache.get(99) == -1
print("all tests passed")
```

這段程式示範三件事。第一，**invariant 要能被檢查**：「依最近使用排序」聽起來抽象，但可以從存取紀錄直接算出應有的順序，再和實際狀態比對。第二，**invariant 要涵蓋所有結構之間的關係**：例如 LFU 至少有四條（key 集合一致、每個 key 只在一個桶、`min_freq` 是最小的非空桶、桶內依最近使用排序），少檢查一條就可能漏 bug。第三，**沒命中的 `get` 不算使用**：這種語意細節最好在寫程式前就和面試官確認。

面試中不一定要寫出 `check`，但要能口頭說出 invariant，並在寫完每個方法後逐條對照：「`put` 一個已存在的 key：dict 更新了值、節點移到最前面、大小不變，三條都成立。」這比寫完再隨便跑一個例子可靠得多。

## 27.6 面試流程：先寫介面與測試，再填實作

設計題的程式通常有 40–80 行，直接從第一行寫到最後一行很容易迷路。比較穩定的流程是：

1. **先寫介面骨架**：class 名稱、每個方法的簽名、一行註解寫目標複雜度與回傳值的語意（找不到回傳什麼、空的時候怎麼辦）。這一步只要一分鐘，卻能讓你和面試官對齊需求，例如「`put` 已存在的 key 算不算使用？」「`getRandom` 在空集合時會被呼叫嗎？」。
2. **寫出題目範例的呼叫序列當作測試**：把範例寫成一串方法呼叫與預期結果。寫完實作後，先拿這串測試在腦中或白板上跑一遍。
3. **選結構、寫 invariant，再逐個方法實作**：先寫最簡單、會被其他方法共用的 helper（例如 `_remove(node)`、`_add_front(node)`），再寫公開方法。公開方法只呼叫 helper，就比較不會漏掉同步。
4. **主動測邊界**：容量 0 或 1、同一個 key 重複 put、刪除最後一個元素、所有元素都被刪光後再操作。

如果環境允許執行程式，L5 等級的加分做法是寫一個**差分測試**（differential testing）：同時跑「快但複雜」的實作和「慢但明顯正確」的模型，用亂數產生一串操作，每一步比對結果。下面用第 10 章核心題 2（155. Min Stack）示範這個套路；本章每一題的解法都用同樣的方式和暴力模型比對。

```python
import random


class MinStack:
    def __init__(self):
        self.stack = []                       # 每層存 (值, 到這層為止的最小值)

    def push(self, x):
        self.stack.append((x, min(x, self.stack[-1][1]) if self.stack else x))

    def pop(self):
        return self.stack.pop()[0]

    def top(self):
        return self.stack[-1][0]

    def get_min(self):
        return self.stack[-1][1]


class MinStackModel:                          # 暴力但顯然正確
    def __init__(self):
        self.a = []

    def push(self, x):
        self.a.append(x)

    def pop(self):
        return self.a.pop()

    def top(self):
        return self.a[-1]

    def get_min(self):
        return min(self.a)


def differential_test(fast, model, gen_op, steps=3000, seed=0):
    rng = random.Random(seed)
    for step in range(steps):
        name, args = gen_op(rng, model)
        got, want = getattr(fast, name)(*args), getattr(model, name)(*args)
        assert got == want, (step, name, args, got, want)


def gen_min_stack_op(rng, model):
    if not model.a or rng.random() < 0.5:
        return "push", (rng.randint(-5, 5),)
    return rng.choice(["pop", "top", "get_min"]), ()


differential_test(MinStack(), MinStackModel(), gen_min_stack_op)
s = MinStack()
s.push(2)
s.push(1)
s.push(1)
assert s.get_min() == 1 and s.pop() == 1 and s.get_min() == 1 and s.pop() == 1 and s.get_min() == 2
print("all tests passed")
```

`gen_op` 收到 model，是為了只產生合法的操作（例如空 stack 時不呼叫 `pop`）。小值域（`-5` 到 `5`）是刻意的：值越少，重複值、相等的最小值這類邊界越常出現。面試時就算不能執行，說出「我會用一個 O(n) 的暴力模型做差分測試」也能展現你對正確性的重視。

## 27.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 淘汰節點時只從 linked list 拿掉，忘了刪 dict | 容量似乎沒滿卻一直淘汰，或 `get` 回傳已淘汰的值 | 節點存 `key`；把「刪節點＋刪 dict」寫成同一個 helper |
| 陣列交換刪除後沒更新被搬動元素的索引 | 之後刪除那個元素時刪錯位置 | 寫成 `last = pop(); if i < len: items[i] = last; pos[last] = i` |
| 刪的是最後一個元素時，把它的索引寫回 dict | 已刪除的值仍在 dict 中，`insert` 回傳 False | 先 pop 掉 dict 中的 key，再判斷是否需要搬移 |
| `put` 已存在的 key 時當作新 key 插入 | 同一個 key 出現兩個節點，大小計算錯誤、提前淘汰 | `put` 先查 key 是否存在，存在就更新值並調整順序，不做淘汰 |
| Lazy deletion 用「值」當刪除標記 | 同一個值 push 兩次、刪一次，兩個都被跳過 | 每次 push 給一個唯一遞增的 id，標記 id 而不是值 |
| 空桶沒刪掉或 `min_freq`／`max_freq` 沒更新 | 取最小／最大次數時拿到空集合而出錯 | 每次桶變空就刪除，並在同一處更新極值；寫進 invariant |
| 容量 0、第一次操作就淘汰等邊界沒處理 | `put` 時從空 list 淘汰，指到 sentinel | 容量 0 直接忽略 `put`；淘汰前確認大小真的到達容量 |
| Iterator 在 `next` 裡做所有工作，`hasNext` 不處理空 list | 巢狀空 list `[[]]` 時 `hasNext` 回 True 但 `next` 出錯 | 在 `hasNext` 裡把 stack 推進到下一個整數；`next` 先呼叫 `hasNext` |
| 版本查詢用 `bisect_left` 而不是 `bisect_right` | 查詢時間剛好等於某個寫入時間時拿到舊版本 | floor 查詢是「最後一個 ≤ t」，即 `bisect_right(times, t) - 1` |
| 用 `copy()` 實作 snapshot | 每次 snap O(n)，snap 很多次時超時或爆記憶體 | 只記錄被改過的位置與版本號，查詢時用 binary search |

## 核心題 1｜146. LRU Cache｜Medium

### 題目

設計一個容量為 `capacity` 的 LRU（Least Recently Used，最近最少使用）快取，支援兩個操作：

- `get(key)`：如果 key 在快取中，回傳它的值，並把它標記為「最近使用」；否則回傳 `-1`。
- `put(key, value)`：如果 key 已存在，更新它的值並標記為最近使用；否則插入這組 key-value。插入後如果數量超過 `capacity`，要淘汰「最久沒被使用」的那個 key。

兩個操作都要平均 O(1)。限制：`1 <= capacity <= 3000`，key 與 value 是非負整數，總呼叫次數最多 2 × 10⁵。「使用」指成功的 `get` 與任何 `put`；查不到的 `get` 不算使用。

- 範例 1：容量 2，依序 `put(1, 1)`、`put(2, 2)`、`get(1)` → `1`、`put(3, 3)`（淘汰 2，因為 1 剛被用過）、`get(2)` → `-1`、`put(4, 4)`（淘汰 1）、`get(1)` → `-1`、`get(3)` → `3`、`get(4)` → `4`。
- 範例 2（邊界）：容量 1，`put(1, 1)`、`put(1, 5)`（更新，不淘汰）、`get(1)` → `5`、`put(2, 2)`（淘汰 1）、`get(1)` → `-1`。
- 範例 3（邊界）：容量 2，`put(1, 1)`、`put(2, 2)`、`put(1, 10)`（更新 1，使 1 變成最近使用）、`put(3, 3)` 淘汰的是 2 而不是 1。

### 思路

暴力解是用一個 list 依使用時間存 key、一個 dict 存值。`get` 命中時要在 list 中找到 key 並搬到尾端，O(n)；淘汰時刪 list 的第一個元素，在 Python 的 list 上也是 O(n)。只用 dict 加上「最後使用時間」也行，但淘汰時要掃過所有 key 找最小時間，還是 O(n)。用 heap 依時間排序可以 O(log n) 找到最舊的，但每次使用都要更新某個 key 的時間，heap 不支援就地修改，只能 lazy deletion，空間會被大量過期項目撐大。

照 27.3 節的方法列操作：「依 key 找」要 O(1)，所以一定有 dict；「把某個 key 移到最新」要 O(1) 從中間拿出來；「淘汰最舊」要 O(1) 拿到一端。能 O(1) 從中間拿出任意元素、又能 O(1) 存取兩端的結構，就是雙向 linked list：只要手上有節點，改四個指標就能把它拿下來。剩下的問題是「怎麼 O(1) 拿到節點」，答案是讓 dict 的 value 直接存節點。

所以結構是：`dict[key] = node`，節點依使用時間串成雙向 list，靠近 `head` 的是最近使用，靠近 `tail` 的是最久沒用。invariant 有三條：dict 的 key 集合等於 list 中的節點集合；list 從 head 到 tail 依最近使用排序；節點數不超過容量。每個操作都只用兩個 helper：`_remove(node)` 與 `_add_front(node)`，「移到最前面」就是先 remove 再 add_front。淘汰時取 `tail.prev`，因為節點存了 key，才能同時從 dict 刪掉它。

```text
容量 2；list 由左到右 = 最近 → 最久（H、T 是 sentinel）

操作        list 狀態              dict keys   說明
put(1,1)    H ⇄ 1 ⇄ T              {1}         新節點放最前
put(2,2)    H ⇄ 2 ⇄ 1 ⇄ T          {1,2}
get(1)=1    H ⇄ 1 ⇄ 2 ⇄ T          {1,2}       1 被拿下來、放到最前
put(3,3)    H ⇄ 3 ⇄ 1 ⇄ T          {1,3}       已滿：淘汰 T.prev = 2，dict 刪 2
get(2)=-1   不變                    {1,3}       沒命中不算使用
put(4,4)    H ⇄ 4 ⇄ 3 ⇄ T          {3,4}       淘汰 T.prev = 1
get(3)=3    H ⇄ 3 ⇄ 4 ⇄ T          {3,4}
```

第三步的 `get(1)` 是 LRU 的關鍵：它改變的不是內容而是順序，於是第四步淘汰的是 2 而不是 1。每一步都只動到常數個節點：命中時拿下一個、放上一個；插入時放上一個、可能拿掉 `T.prev` 一個。

### 解法

```python
import random
from collections import OrderedDict


class Node:
    __slots__ = ("key", "val", "prev", "next")

    def __init__(self, key=0, val=0):
        self.key, self.val = key, val
        self.prev = self.next = None


class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.map: dict[int, Node] = {}
        self.head, self.tail = Node(), Node()      # head.next 最近使用，tail.prev 最久沒用
        self.head.next, self.tail.prev = self.tail, self.head

    def _remove(self, node: Node) -> None:
        node.prev.next, node.next.prev = node.next, node.prev

    def _add_front(self, node: Node) -> None:
        node.prev, node.next = self.head, self.head.next
        self.head.next.prev = node
        self.head.next = node

    def get(self, key: int) -> int:
        node = self.map.get(key)
        if node is None:
            return -1
        self._remove(node)
        self._add_front(node)
        return node.val

    def put(self, key: int, value: int) -> None:
        if self.cap <= 0:
            return
        node = self.map.get(key)
        if node is not None:                        # 已存在：更新值並移到最前，不淘汰
            node.val = value
            self._remove(node)
            self._add_front(node)
            return
        if len(self.map) == self.cap:               # 已滿：淘汰最久沒用的
            lru = self.tail.prev
            self._remove(lru)
            del self.map[lru.key]
        node = Node(key, value)
        self.map[key] = node
        self._add_front(node)


class LRUCacheOD:
    """用 OrderedDict 的版本：尾端是最近使用。"""

    def __init__(self, capacity: int):
        self.cap, self.od = capacity, OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.od:
            return -1
        self.od.move_to_end(key)
        return self.od[key]

    def put(self, key: int, value: int) -> None:
        if self.cap <= 0:
            return
        if key in self.od:
            self.od.move_to_end(key)
        elif len(self.od) == self.cap:
            self.od.popitem(last=False)
        self.od[key] = value


class LRUModel:                                     # O(n) 暴力模型：list 尾端是最近使用
    def __init__(self, capacity):
        self.cap, self.order, self.val = capacity, [], {}

    def get(self, key):
        if key not in self.val:
            return -1
        self.order.remove(key)
        self.order.append(key)
        return self.val[key]

    def put(self, key, value):
        if self.cap <= 0:
            return
        if key in self.val:
            self.order.remove(key)
        elif len(self.order) == self.cap:
            del self.val[self.order.pop(0)]
        self.order.append(key)
        self.val[key] = value


c = LRUCache(2)
c.put(1, 1); c.put(2, 2)
assert c.get(1) == 1
c.put(3, 3)
assert c.get(2) == -1
c.put(4, 4)
assert c.get(1) == -1 and c.get(3) == 3 and c.get(4) == 4

c = LRUCache(1)
c.put(1, 1); c.put(1, 5)
assert c.get(1) == 5
c.put(2, 2)
assert c.get(1) == -1 and c.get(2) == 2

c = LRUCache(2)
c.put(1, 1); c.put(2, 2); c.put(1, 10); c.put(3, 3)
assert c.get(2) == -1 and c.get(1) == 10

rng = random.Random(7)
for cap in (0, 1, 2, 3, 5):
    caches = [LRUCache(cap), LRUCacheOD(cap), LRUModel(cap)]
    for _ in range(3000):
        k = rng.randint(0, 7)
        if rng.random() < 0.5:
            res = [x.get(k) for x in caches]
            assert res[0] == res[1] == res[2], res
        else:
            v = rng.randint(0, 99)
            for x in caches:
                x.put(k, v)
    assert len(caches[0].map) == len(caches[2].val) <= cap
print("all tests passed")
```

### 複雜度與邊界

時間：`get` 與 `put` 都是 O(1)，因為 dict 查找平均 O(1)，每次操作只改常數個指標。空間 O(capacity)：dict 與 list 各有 capacity 個項目，加上兩個 sentinel。邊界：容量 1 時每次插入新 key 都會淘汰唯一的那個，sentinel 讓 `_remove` 不需要特判；`put` 已存在的 key 時絕對不能淘汰：容量 1 時這樣做恰好把自己淘汰掉再插回去，結果看不出錯，但容量 2 時 `put(1, 1)`、`put(2, 2)`、`get(1)`、`put(1, 10)` 會錯誤地淘汰 2（此時 2 是最久沒用的），快取只剩一個 key；沒命中的 `get` 不改變順序；容量 0（題目限制不會出現，但追問時常被問到）直接忽略 `put`。Python 的 `OrderedDict` 版本內部也是 hash ＋ 雙向 linked list，複雜度相同，面試時可以先寫它，再說明自己會手寫節點版本。

### Follow-up

> [!question]- F1. 如果要讓多個執行緒同時使用這個快取（thread safety），怎麼做？
> 關鍵在於 LRU 的 `get` 也會修改結構（把節點移到最前面），所以不能用「讀鎖共享、寫鎖互斥」的 read-write lock 讓 `get` 並行，最簡單正確的做法是整個物件一把 mutex（互斥鎖），`get` 與 `put` 都在鎖內完成，每個操作仍是 O(1)，但所有執行緒會在這把鎖上排隊。要提高並行度，常見做法是**分片**（sharding）：依 `hash(key) % S` 把 key 分到 S 個獨立的 LRU，每個有自己的鎖與 capacity / S 的容量，代價是淘汰變成「各分片內」的近似 LRU。另一種是減少 `get` 時的寫入：只記錄「這個 key 被用過」的位元或時間戳記，由背景或 `put` 時批次調整順序，這就是 CLOCK 等近似 LRU 的想法。

> [!question]- F2. 如果每個項目有 TTL（存活時間），過期就不能再被讀到呢？
> 每個節點多存 `expire_at`。`get` 時先檢查：若已過期，就當作沒命中，順便把節點從 list 與 dict 刪掉（lazy expiration，延遲過期）。只靠 lazy 的話，從不被讀的過期項目會一直占容量，所以 `put` 需要空間時要優先淘汰過期的。若所有 key 的 TTL 都相同，「最久沒用」不等於「最早過期」（被讀過的 key 會移到前面但過期時間不變），因此要另外維護一個依 `expire_at` 排序的結構：TTL 固定時可以用一條依寫入時間排列的 FIFO list，TTL 不固定時用 heap 加 lazy deletion，淘汰時先清掉堆頂已過期的，再按 LRU 淘汰。每次操作 amortized O(log n)，TTL 固定時仍是 O(1)。

> [!question]- F3. 如果容量是以位元組計，每個 value 的大小不同呢？
> 改成記錄目前總大小 `used` 與上限 `limit_bytes`。插入或更新時先加上新大小（更新要先扣掉舊大小），然後在 `used > limit_bytes` 時重複淘汰 `tail.prev`，直到總大小合法。一次 `put` 可能淘汰多個項目，但每個項目只會被淘汰一次，所以 amortized 仍是 O(1)。要處理兩個邊界：單一 value 本身就超過上限時應該直接拒絕（否則會把整個快取清空後還是放不下）；正在插入的 key 不能被自己的淘汰迴圈淘汰，所以要先淘汰再插入，或在迴圈中跳過它。

> [!question]- F4. 如果快取要分散到多台機器（distributed cache）呢？
> 全域精確的 LRU 需要所有機器共享一份使用順序，每次 `get` 都要跨機器同步，代價太高，所以實務上不做全域 LRU。做法是用 consistent hashing（一致性雜湊）把 key 分到各台機器，每台機器維護自己的本地 LRU，這和 F1 的分片是同一個想法，只是分片的邊界從鎖變成網路。新增或移除機器時，consistent hashing 只會讓大約 1/N 的 key 換主人，換主人的 key 等於快取失效，下次讀取時從資料來源重新載入。熱門 key 可能讓單台機器過載，可以在客戶端加一層小的本地 LRU，或把熱門 key 複製到多台機器。

> [!question]- F5. 如果重開機後要保留快取內容（持久化）呢？
> 快取本身可以被重建，所以通常只要保存「內容與大致的使用順序」，不需要每次 `get` 都寫磁碟。做法一是定期 snapshot：從 head 到 tail 走一遍，把 key、value 依順序寫成檔案，重開機時依相反順序 `put` 回去就能還原順序，代價是 O(n) 的寫入，而且會遺失最後一次 snapshot 之後的變更。做法二是 append-only log：每次 `put` 追加一筆紀錄，`get` 不寫（或只抽樣寫），重開機時重播 log；log 會無限變長，所以要定期用 snapshot 壓縮。若只是想避免冷啟動，也可以只存 key 清單，重開機後在背景預先載入（warm up）。

## 核心題 2｜380. Insert Delete GetRandom O(1)｜Medium

### 題目

設計一個整數集合 `RandomizedSet`，支援三個平均 O(1) 的操作：

- `insert(val)`：若 val 不在集合中就加入並回傳 `True`，否則回傳 `False`。
- `remove(val)`：若 val 在集合中就移除並回傳 `True`，否則回傳 `False`。
- `getRandom()`：從目前集合中**等機率**回傳一個元素。保證呼叫時集合非空。

限制：val 在 32 位元整數範圍內，總呼叫次數最多 2 × 10⁵。

- 範例 1：`insert(1)` → `True`、`remove(2)` → `False`、`insert(2)` → `True`、`getRandom()` → 1 或 2 各 1/2 機率、`remove(1)` → `True`、`insert(2)` → `False`、`getRandom()` → `2`。
- 範例 2（邊界）：`insert(5)`、`remove(5)`、`insert(5)` → 第三次回傳 `True`，刪掉之後可以再加入。
- 範例 3（邊界）：集合 `{3, 7, 9}` 中移除最後加入的 9，不需要搬動任何其他元素。

### 思路

只用 Python 的 `set`：插入與刪除 O(1)，但 `set` 沒有索引，`getRandom` 只能 `random.choice(list(s))`，每次 O(n)。只用 list：`getRandom` 是 `random.choice` O(1)，但 `remove(val)` 要先找到 val（O(n)），再從中間刪除（又是 O(n)）。瓶頸很清楚：等機率取樣需要元素**連續存放在陣列裡**，而陣列不擅長「找到某個值」與「從中間刪除」。

第一個問題用 hash map 解決：`pos[val] = val 在陣列中的索引`，查找 O(1)。第二個問題的關鍵觀察是：**集合沒有順序**，所以刪除時不必保持其他元素的相對位置。把要刪的元素和陣列最後一個元素交換，然後 pop 最後一個，就只花 O(1)。交換後，原本最後一個元素的索引改變了，必須同步更新 `pos`。

invariant 只有一條：對所有 i，`pos[items[i]] == i`，而且 `pos` 的 key 集合等於 `items` 的元素集合。`getRandom` 在 `items` 上均勻取一個索引，因為每個元素恰好占一格，所以每個元素的機率都是 1/n。注意刪除時的順序：先從 `pos` 拿出被刪元素的索引 i，再 pop 出最後一個元素 last；如果 i 還在陣列範圍內（也就是被刪的不是最後一個），才把 last 放到 i 並更新 `pos[last]`。

```text
items = [3, 7, 9, 4]     pos = {3:0, 7:1, 9:2, 4:3}

remove(7)：
  i = pos.pop(7) = 1                     pos = {3:0, 9:2, 4:3}
  last = items.pop() = 4                 items = [3, 7, 9]
  i=1 < len=3 → items[1] = 4、pos[4] = 1
  結果 items = [3, 4, 9]                 pos = {3:0, 9:2, 4:1}

remove(9)（刪的剛好是最後一個）：
  i = pos.pop(9) = 2                     pos = {3:0, 4:1}
  last = items.pop() = 9                 items = [3, 4]
  i=2 == len=2 → 不搬動（若照搬，會把 9 寫回 pos）
  結果 items = [3, 4]                    pos = {3:0, 4:1}

getRandom()：randrange(2) 取 0 或 1，各 1/2 機率
```

第一次刪除示範一般情況：洞被最後一個元素補上，只有它的索引需要更新。第二次刪除示範邊界：被刪的就是最後一個，如果不判斷 `i < len(items)` 就執行 `pos[last] = i`，9 會被寫回 `pos`，之後 `insert(9)` 會錯誤地回傳 `False`。

### 解法

```python
import random
from collections import Counter


class RandomizedSet:
    def __init__(self):
        self.items: list[int] = []
        self.pos: dict[int, int] = {}

    def insert(self, val: int) -> bool:
        if val in self.pos:
            return False
        self.pos[val] = len(self.items)
        self.items.append(val)
        return True

    def remove(self, val: int) -> bool:
        if val not in self.pos:
            return False
        i = self.pos.pop(val)
        last = self.items.pop()
        if i < len(self.items):            # 被刪的不是最後一個：用 last 補洞
            self.items[i] = last
            self.pos[last] = i
        return True

    def getRandom(self) -> int:
        return self.items[random.randrange(len(self.items))]


rs = RandomizedSet()
assert rs.insert(1) is True and rs.remove(2) is False and rs.insert(2) is True
assert rs.getRandom() in (1, 2)
assert rs.remove(1) is True and rs.insert(2) is False and rs.getRandom() == 2

rs = RandomizedSet()
assert rs.insert(5) and rs.remove(5) and rs.insert(5) and rs.items == [5]

rs = RandomizedSet()
for v in (3, 7, 9):
    rs.insert(v)
assert rs.remove(9) and rs.items == [3, 7] and rs.pos == {3: 0, 7: 1}
assert rs.insert(9)

random.seed(0)
rs, model = RandomizedSet(), set()
for _ in range(5000):
    v = random.randint(-10, 10)
    if random.random() < 0.5:
        assert rs.insert(v) == (v not in model)
        model.add(v)
    else:
        assert rs.remove(v) == (v in model)
        model.discard(v)
    assert set(rs.items) == model == set(rs.pos)
    assert all(rs.pos[x] == i for i, x in enumerate(rs.items))

rs = RandomizedSet()
for v in range(4):
    rs.insert(v)
freq = Counter(rs.getRandom() for _ in range(40000))
assert all(abs(freq[v] - 10000) < 600 for v in range(4))       # 大致均勻
print("all tests passed")
```

### 複雜度與邊界

時間：三個操作都是平均 O(1)；`items.append` 與 `items.pop()` 是 amortized O(1)（list 偶爾擴容），dict 操作是平均 O(1)。空間 O(n)，n 是目前集合大小。邊界：刪除最後一個元素（不搬動）、刪光後再插入、重複插入回傳 `False`、刪除不存在的值回傳 `False`、集合只有一個元素時 `getRandom` 一定回傳它。不要用 `random.choice(self.pos)` 或 `random.sample(set)`，前者是對 dict 取索引會出錯，後者在新版 Python 已不支援 set。

### Follow-up

> [!question]- F1. 如果允許重複元素（381. Insert Delete GetRandom O(1) - Duplicates allowed），getRandom 的機率要和出現次數成正比呢？
> 陣列裡每次插入都放一格，同一個值可以出現多次，於是 `getRandom` 在陣列上均勻取樣時，機率自然和出現次數成正比。`pos` 改成 `val → 索引的集合`。刪除時從 `pos[val]` 任取一個索引 i（`pos[val].pop()`），把最後一個元素 last 移到 i：要先從 `pos[last]` 移除索引 `len - 1`，再加入 i；若 i 剛好是最後一格就不搬動。容易出錯的地方是 val 和 last 是同一個值的情況，所以要嚴格依照「先移除舊索引、再加入新索引」的順序，`pos[val]` 變空時刪掉這個 key。三個操作仍是平均 O(1)。

> [!question]- F2. 如果每個元素有權重，getRandom 的機率要和權重成正比，而且會插入與刪除呢？
> 靜態權重可以用 prefix sum 加 binary search（528. Random Pick with Weight）：取 `r = random() * 總和`，找第一個 prefix ≥ r 的位置，O(log n)。加上插入刪除後 prefix sum 會變動，改用 Fenwick tree（第 26 章）存每格的權重：插入放到陣列尾端並在 Fenwick 上加權重；刪除用本題的「和最後一個交換」把權重搬到洞的位置（Fenwick 上兩次單點更新）；取樣時在 Fenwick 上做 O(log n) 的「找第一個 prefix ≥ r」下降搜尋。每個操作 O(log n)。若權重只有少數幾種，也可以把同權重的元素放進同一個 RandomizedSet，先依「權重 × 個數」選組，再在組內均勻取樣。

> [!question]- F3. 如果要一次取 k 個不重複的隨機元素呢？
> 在 `items` 上做部分 Fisher–Yates shuffle：for j in 0..k−1，從 `[j, n)` 均勻選一個索引 r，交換 `items[j]` 和 `items[r]`，前 k 個就是一組均勻的不重複樣本，時間 O(k)。因為交換會改變元素位置，若要原地做，必須同步更新 `pos`；或者複製一份陣列再做，代價 O(n)。如果 k 遠小於 n，也可以重複呼叫 `getRandom` 並用 set 去重，期望次數在 k ≤ n/2 時是 O(k)，但 k 接近 n 時會退化成 coupon collector（集券問題）的 O(n log n)，所以 Fisher–Yates 是更穩定的答案。

> [!question]- F4. 如果多個執行緒同時呼叫呢？
> 三個操作都會讀寫 `items` 與 `pos` 兩個結構，必須一起原子地更新：例如 `remove` 做到一半時（`pos` 已刪、`items` 尚未搬移），另一個執行緒的 `getRandom` 可能讀到已刪除的值。最直接是一把 mutex 包住整個方法。`getRandom` 只讀，所以可以用 read-write lock 讓多個 `getRandom` 並行，`insert` 與 `remove` 取寫鎖。若要更高的並行度，可以依 `hash(val) % S` 分成 S 個子集合各自上鎖，但 `getRandom` 要維持全域均勻，必須依各分片大小加權選分片，而讀取各分片大小的瞬間不一致會造成微小偏差；面試時能指出這個取捨就夠了。

> [!question]- F5. 如果要支援 getRandom 但排除某些「黑名單」值，而值域是 [0, n) 且黑名單固定呢？
> 這是 710 題（排除清單以外的隨機取樣）的想法，同樣是「把洞補起來」：合法值有 m = n − |B| 個，取樣只在 `[0, m)` 取。落在 `[0, m)` 裡的排除清單值，事先映射到 `[m, n)` 裡的某個合法值（從尾端找沒被排除清單占用的位置配對），存在 dict 中。取樣得到 r 時，若 r 在映射表中就回傳映射後的值，否則回傳 r。前處理 O(|B|)，每次取樣 O(1)，空間 O(|B|)，不需要建出整個值域。這和本題「刪除時用最後一個補洞」是同一個技巧，只是一次處理完所有刪除。

## 核心題 3｜981. Time Based Key-Value Store｜Medium

### 題目

設計一個帶時間戳記的 key-value 儲存 `TimeMap`：

- `set(key, value, timestamp)`：在時間 `timestamp` 把 `key` 設成 `value`。同一個 key 可以在不同時間被設定多次，舊的值不會消失。
- `get(key, timestamp)`：回傳 `key` 在時間 `timestamp` 當下的值，也就是所有 `timestamp_prev <= timestamp` 的 `set` 之中，`timestamp_prev` 最大的那一次的值；若沒有這樣的 `set`，回傳空字串 `""`。

限制：所有 `set` 呼叫的 `timestamp` **嚴格遞增**；`1 <= timestamp <= 10⁷`；key 與 value 是長度 1 到 100、由小寫英文字母與數字組成的字串；總呼叫次數最多 2 × 10⁵。

- 範例 1：`set("foo", "bar", 1)`、`get("foo", 1)` → `"bar"`、`get("foo", 3)` → `"bar"`（時間 3 時最新的是時間 1 寫入的值）、`set("foo", "bar2", 4)`、`get("foo", 4)` → `"bar2"`、`get("foo", 5)` → `"bar2"`。
- 範例 2（邊界）：`set("a", "x", 10)` 之後 `get("a", 9)` → `""`（查詢時間早於第一次寫入）；`get("b", 100)` → `""`（key 不存在）。

### 思路

暴力解是每個 key 存一個 `(timestamp, value)` 的 list，`get` 時從頭掃到尾，找最大的 `timestamp_prev <= timestamp`，O(該 key 的版本數)。也可以反過來，`set` 時把每個時間點的值都填好（時間範圍 10⁷），查詢 O(1)，但空間完全不可行。

關鍵觀察來自限制：`set` 的時間戳記嚴格遞增，所以每個 key 的版本串列在 append 的同時**天然就是排序的**，不需要額外排序。`get` 要找的是「最後一個 ≤ timestamp 的版本」，這正是第 8 章的 floor 查詢：`bisect_right(times, timestamp) - 1`。`bisect_right` 回傳第一個 > timestamp 的位置，往左一格就是最後一個 ≤ timestamp 的位置；若結果是 −1，代表所有版本都比查詢時間晚，回傳 `""`。

結構是兩層：外層 dict 依 key 分群（多層 hash 的第一層），內層每個 key 存兩條平行的 list `times` 與 `values`。把時間與值分開存，是為了讓 `bisect` 直接作用在整數 list 上，不需要建 tuple 或傳 `key=`。invariant：每個 key 的 `times` 嚴格遞增，且 `times[i]` 與 `values[i]` 屬於同一次 `set`。

```text
key = "foo"
times:   [ 1,     4,      7     ]
values:  ["bar", "bar2", "bar3" ]

get("foo", 5)：bisect_right(times, 5) = 2   （第一個 > 5 的是 7，在索引 2）
               idx = 2 - 1 = 1 → "bar2"
get("foo", 4)：bisect_right(times, 4) = 2   （4 本身要算進去，所以用 right）
               idx = 1 → "bar2"
get("foo", 0)：bisect_right(times, 0) = 0
               idx = -1 → ""                （查詢時間早於所有版本）
get("foo", 99)：bisect_right(times, 99) = 3
               idx = 2 → "bar3"
```

`get("foo", 4)` 是最容易寫錯的情況：查詢時間剛好等於某次寫入的時間，必須拿到這次寫入的值。如果誤用 `bisect_left`，它會回傳 1（第一個 ≥ 4 的位置），減一後拿到 "bar"，是舊版本。

### 解法

```python
import random
from bisect import bisect_right
from collections import defaultdict


class TimeMap:
    def __init__(self):
        self.times: dict[str, list[int]] = defaultdict(list)
        self.values: dict[str, list[str]] = defaultdict(list)

    def set(self, key: str, value: str, timestamp: int) -> None:
        self.times[key].append(timestamp)          # 題目保證 timestamp 遞增，append 後仍排序
        self.values[key].append(value)

    def get(self, key: str, timestamp: int) -> str:
        if key not in self.times:                  # 避免 defaultdict 因查詢而建立空 list
            return ""
        i = bisect_right(self.times[key], timestamp) - 1
        return self.values[key][i] if i >= 0 else ""


tm = TimeMap()
tm.set("foo", "bar", 1)
assert tm.get("foo", 1) == "bar" and tm.get("foo", 3) == "bar"
tm.set("foo", "bar2", 4)
assert tm.get("foo", 4) == "bar2" and tm.get("foo", 5) == "bar2"
assert tm.get("foo", 0) == ""

tm = TimeMap()
tm.set("a", "x", 10)
assert tm.get("a", 9) == "" and tm.get("b", 100) == "" and "b" not in tm.times

rng = random.Random(3)
tm, log, t = TimeMap(), [], 0
for _ in range(3000):
    key = rng.choice("abc")
    if rng.random() < 0.4:
        t += rng.randint(1, 3)
        val = str(rng.randint(0, 99))
        tm.set(key, val, t)
        log.append((key, val, t))
    else:
        q = rng.randint(0, t + 2)
        cands = [(ts, v) for k, v, ts in log if k == key and ts <= q]
        assert tm.get(key, q) == (max(cands)[1] if cands else "")
print("all tests passed")
```

### 複雜度與邊界

時間：`set` 是 amortized O(1)（list append）；`get` 是 O(log m)，m 是該 key 的版本數。空間 O(總 `set` 次數)，因為每次寫入都保留。邊界：查詢時間早於第一次寫入回傳 `""`；查詢時間剛好等於寫入時間要拿到該次的值（用 `bisect_right`）；key 不存在時不要讓 `defaultdict` 因為查詢而建出空 list（這不影響正確性，但會讓記憶體隨查詢增加）；值可以是空字串以外的任何字串，若允許寫入空字串，就無法區分「沒有值」與「值是空字串」，追問時可以改回傳 `None`。

### Follow-up

> [!question]- F1. 如果 set 的時間戳記不保證遞增（可能補寫過去的資料）呢？
> append 之後串列就不再排序。若寫入很少、讀取很多，可以用 `bisect.insort` 插入到正確位置，`set` 變成 O(m)（陣列搬移），`get` 維持 O(log m)。若寫入也很多，需要能 O(log m) 插入的有序結構：平衡 BST、skip list（跳躍串列，多層隨機索引的有序 linked list，期望 O(log m) 插入與查找），或第三方的 `SortedList`。另一種做法是 lazy sorting：寫入時 append 並標記「髒」，第一次 `get` 時才排序一次，適合「一批寫入後一批讀取」的工作負載。還要先和面試官確認同一個 key、同一個時間戳記被寫兩次時的語意（通常是覆寫），插入前用 `bisect_left` 檢查是否已有相同時間。

> [!question]- F2. 如果要查詢一段時間 [t1, t2] 內的所有版本呢？
> 兩次 binary search：`lo = bisect_left(times, t1)`、`hi = bisect_right(times, t2)`，回傳 `values[lo:hi]`，時間 O(log m + k)，k 是回傳的版本數。如果還要「t1 當下的值」作為起點（例如畫出這段期間的值變化圖），就再加上 `values[lo - 1]`（若 `lo > 0` 且 `times[lo] != t1`）。若只需要這段期間的版本數，答案是 `hi - lo`，O(log m)。

> [!question]- F3. 如果記憶體有限，只需要保留最近 T 秒或最近 K 個版本呢？
> 最近 K 個版本：每個 key 的串列只保留最後 K 筆，超過就從前面丟掉。用 Python list 的 `pop(0)` 是 O(K)，所以改用「起始偏移量」：保留整條 list 但記錄 `start`，邏輯上的串列是 `times[start:]`，`bisect_right(times, t, lo=start)` 直接從 `start` 開始搜，等到 `start` 超過長度一半時再一次壓縮，amortized O(1)。最近 T 秒：每次 `set(key, …, now)` 時順便把 `times[start] < now - T` 的版本跳過；但要注意語意：被丟掉的最後一個版本可能仍是「T 秒前開始生效的值」，若查詢時間落在保留窗口的開頭，應該保留窗口前的最後一個版本當作基準。

> [!question]- F4. 如果要做成分散式、可持久化的版本化儲存呢？
> 依 key 做 hash 分區，同一個 key 的所有版本落在同一台機器，`get` 只需查一台，保留本題的 binary search 結構。持久化可以用 LSM-tree 的想法：寫入先 append 到 write-ahead log（預寫日誌，崩潰後可重播還原）與記憶體中的有序表，滿了再寫成依 `(key, timestamp)` 排序的不可變檔案，查詢時找 `(key, ≤ t)` 的最大一筆，這就是多版本並行控制（MVCC）儲存的基本形狀。分散式最難的是時間戳記本身：不同機器的時鐘不同步，「嚴格遞增」不再成立，常見做法是讓每個 key 的主節點（leader）指派版本號，或使用 hybrid logical clock（混合邏輯時鐘）確保同一個 key 的寫入有全序。

> [!question]- F5. 如果有多個執行緒同時讀寫呢？
> 不同 key 之間沒有關聯，可以每個 key 一把鎖（或依 key 分片的一組鎖），讓不同 key 的操作並行。同一個 key 的讀寫之間要注意兩條平行 list 的一致性：寫入時若先 append `times` 再 append `values`，讀者可能在兩次 append 之間找到新的索引，卻讀不到對應的 value 而越界。解法一是讀寫都在該 key 的鎖內完成；解法二是只用一條 `list[(timestamp, value)]` 並在 append 時一次放入整個 tuple，讓單次 append 成為唯一的寫入點。因為寫入只 append、從不修改舊版本，讀者看到的永遠是某個一致的前綴，這是 append-only 結構適合並行讀的原因。

## 核心題 4｜1472. Design Browser History｜Medium

### 題目

設計一個只有一個分頁的瀏覽器歷史紀錄 `BrowserHistory`：

- `BrowserHistory(homepage)`：從 `homepage` 開始。
- `visit(url)`：從目前頁面前往 `url`，並**清除所有前進紀錄**（就像在網頁上按了上一頁之後點了新連結）。
- `back(steps)`：最多往回走 `steps` 步（不能超過最早的頁面），回傳走完後所在的 url。
- `forward(steps)`：最多往前走 `steps` 步（不能超過最新的頁面），回傳走完後所在的 url。

限制：`1 <= steps <= 100`，url 長度最多 20，總呼叫次數最多 5000。

- 範例 1：首頁 `a.com`；`visit("b.com")`、`visit("c.com")`、`visit("d.com")`；`back(1)` → `"c.com"`；`back(1)` → `"b.com"`；`forward(1)` → `"c.com"`；`visit("e.com")`（清除前進紀錄 `d.com`）；`forward(2)` → `"e.com"`（沒有前進紀錄可走）；`back(2)` → `"b.com"`；`back(7)` → `"a.com"`（最多退到首頁）。
- 範例 2（邊界）：首頁 `x.com`，什麼都不 visit，`back(3)` → `"x.com"`、`forward(3)` → `"x.com"`。

### 思路

最直觀的模型是兩個 stack：`back_stack` 放走過的頁面，`forward_stack` 放按上一頁時退下來的頁面。`back(steps)` 就是從 `back_stack` pop 最多 steps 次推進 `forward_stack`，`visit` 時清空 `forward_stack`。這個做法正確，但 `back` 與 `forward` 是 O(steps)，`visit` 清空前進紀錄也可能要 O(n)（Python 的 `clear` 雖然很快，本質上仍要釋放 n 個元素）。用雙向 linked list 也一樣，每一步都要沿著指標走。

關鍵觀察：歷史紀錄其實是**一條陣列加一個游標**。往回、往前只是移動游標，可以用 `min`／`max` 一次跳到位，O(1)。唯一麻煩的是 `visit` 要「刪除游標之後的所有頁面」：與其真的刪除，不如再用一個指標 `last` 記住「有效紀錄的最後一格」。`visit` 時游標前進一格並覆寫該格（如果陣列夠長就覆寫，不夠長就 append），然後令 `last = cur`；之後的舊資料雖然還在陣列裡，但 `forward` 只會走到 `last`，等於被邏輯刪除了。

invariant：`0 <= cur <= last < len(hist)`；`hist[0..last]` 是目前有效的歷史紀錄；`hist[cur]` 是目前頁面。`back(steps)` 令 `cur = max(0, cur - steps)`，`forward(steps)` 令 `cur = min(last, cur + steps)`，兩者都不改 `last`；`visit` 是唯一會改 `last` 的操作。這是 27.3 節「hash ＋ array」的簡化版：不需要 hash，因為只依位置存取。

```text
範例 1（[ ] 標示 cur，| 標示 last 之後的部分是無效資料）

初始          [a]                              cur=0 last=0
visit b,c,d   a  b  c [d]                      cur=3 last=3
back(1)       a  b [c] d                       cur=2         → c
back(1)       a [b] c  d                       cur=1         → b
forward(1)    a  b [c] d                       cur=2         → c
visit e       a  b  c [e] |                    cur=3 last=3  （覆寫 d，前進紀錄消失）
forward(2)    a  b  c [e]                      cur=min(3, 5)=3 → e
back(2)       a [b] c  e                       cur=1         → b
back(7)      [a] b  c  e                       cur=max(0, -6)=0 → a
visit f      a [f] | c  e                      cur=1 last=1  （覆寫 b；c、e 是殘留的無效資料）
forward(1)   a [f] | c  e                      cur=min(1, 2)=1 → f
```

最後兩步示範「邏輯刪除」：`visit f` 之後，陣列裡還有 `c`、`e`，但 `last = 1`，所以 `forward` 永遠走不到它們；下次 `visit` 會直接覆寫它們的位置，陣列不需要縮小。

### 解法

```python
import random


class BrowserHistory:
    def __init__(self, homepage: str):
        self.hist = [homepage]
        self.cur = 0
        self.last = 0

    def visit(self, url: str) -> None:
        self.cur += 1
        if self.cur == len(self.hist):
            self.hist.append(url)
        else:
            self.hist[self.cur] = url              # 覆寫無效資料，不必刪除
        self.last = self.cur                       # cur 之後的紀錄全部失效

    def back(self, steps: int) -> str:
        self.cur = max(0, self.cur - steps)
        return self.hist[self.cur]

    def forward(self, steps: int) -> str:
        self.cur = min(self.last, self.cur + steps)
        return self.hist[self.cur]


class BrowserHistoryStacks:
    """兩個 stack 的版本：back / forward 是 O(steps)。"""

    def __init__(self, homepage: str):
        self.back_st, self.fwd_st = [homepage], []

    def visit(self, url: str) -> None:
        self.back_st.append(url)
        self.fwd_st.clear()

    def back(self, steps: int) -> str:
        while steps and len(self.back_st) > 1:
            self.fwd_st.append(self.back_st.pop())
            steps -= 1
        return self.back_st[-1]

    def forward(self, steps: int) -> str:
        while steps and self.fwd_st:
            self.back_st.append(self.fwd_st.pop())
            steps -= 1
        return self.back_st[-1]


b = BrowserHistory("a.com")
for u in ("b.com", "c.com", "d.com"):
    b.visit(u)
assert b.back(1) == "c.com" and b.back(1) == "b.com" and b.forward(1) == "c.com"
b.visit("e.com")
assert b.forward(2) == "e.com" and b.back(2) == "b.com" and b.back(7) == "a.com"
b.visit("f.com")
assert b.forward(1) == "f.com" and b.back(1) == "a.com"

b = BrowserHistory("x.com")
assert b.back(3) == "x.com" and b.forward(3) == "x.com"

rng = random.Random(5)
fast, slow = BrowserHistory("h"), BrowserHistoryStacks("h")
for i in range(4000):
    op = rng.random()
    if op < 0.4:
        fast.visit(str(i))
        slow.visit(str(i))
    elif op < 0.7:
        s = rng.randint(1, 4)
        assert fast.back(s) == slow.back(s)
    else:
        s = rng.randint(1, 4)
        assert fast.forward(s) == slow.forward(s)
print("all tests passed")
```

### 複雜度與邊界

陣列版本：`visit`、`back`、`forward` 都是 O(1)（`visit` 的 append 是 amortized O(1)）。空間 O(歷史上最長的有效紀錄長度)，因為陣列只增不減，被邏輯刪除的格子會被之後的 `visit` 重用。兩個 stack 版本：`back`／`forward` 是 O(min(steps, 可走的步數))，在本題 `steps <= 100` 的限制下也能通過，但若 steps 可達 10⁹，只有陣列版本仍是 O(1)。邊界：只有首頁時往回與往前都停在首頁；`steps` 超過可走範圍時要夾住（clamp）而不是報錯；`visit` 剛好在陣列尾端時 append，其他時候覆寫；同一個 url 可以連續 visit 多次，每次都算一頁。

### Follow-up

> [!question]- F1. 如果 visit 時不要丟掉前進紀錄，而是保留成「分支」（像編輯器的 undo tree）呢？
> 歷史紀錄從陣列變成一棵樹：每個節點存 url、父節點、子節點串列，以及「上次從這裡往前走時選的是哪個子節點」。`visit` 在目前節點下新增一個子節點並移過去；`back(steps)` 沿父節點往上走；`forward(steps)` 沿「最近選擇的子節點」往下走。逐步走是 O(steps)；若 steps 很大，`back` 可以用 binary lifting（倍增祖先表）在 O(log n) 內跳到第 steps 個祖先，而 `forward` 的路徑會隨選擇改變，通常就接受 O(steps)。這種結構在面試中常以「undo／redo 不丟分支」的形式出現。

> [!question]- F2. 如果只能保留最近 N 頁（記憶體上限）呢？
> 把陣列改成大小 N 的 ring buffer（環狀緩衝區）：記錄邏輯上的起點 `start`、`cur` 與 `last` 都用「從 start 算起的偏移量」，實際位置是 `(start + offset) % N`。`visit` 時若有效長度已達 N，就令 `start` 前進一格（丟掉最舊的一頁），否則有效長度加一。`back` 夾在偏移量 0、`forward` 夾在 `last`，所有操作仍是 O(1)，空間固定 O(N)。Python 也可以用 `collections.deque(maxlen=N)`，但 deque 的中間索引是 O(N)，所以 `cur` 的存取不是 O(1)，這是選 ring buffer 而不是 deque 的理由。

> [!question]- F3. 如果要支援「跳回最近一次造訪的某個 url」（不只是走固定步數）呢？
> 額外維護 `url → 出現位置的遞增串列`。因為 `visit` 只會寫入 `cur` 位置，且同一位置被覆寫時該格舊 url 的紀錄就失效，所以查詢時要驗證：在 `url` 的位置串列中，用 binary search 找最後一個 ≤ `cur`（往回跳）或 ≤ `last`（往前跳）的位置 p，再確認 `hist[p] == url`，不符合就把它丟掉並繼續往前找（lazy deletion）。每個失效紀錄最多被丟一次，amortized O(log n)。若只需要往回找，也可以讓每一格記錄「上一次出現同 url 的位置」，在覆寫時一起更新。

> [!question]- F4. 如果有多個分頁，每個分頁有自己的歷史，還要一個全域的「最近關閉分頁」功能呢？
> 每個分頁一個本題的 `BrowserHistory` 物件，用 `tab_id → 物件` 的 dict 管理，分頁之間互不影響。「重新開啟最近關閉的分頁」是一個 stack：關閉分頁時把整個物件 push 進 `closed`，重新開啟時 pop 回來，連同它的歷史紀錄一起恢復，O(1)。若 `closed` 要限制數量，就用 deque(maxlen=K)。這個 follow-up 考的是你能不能把本題的結構當成元件，而不是把所有分頁的歷史混在同一條陣列裡。

> [!question]- F5. 如果要在不同裝置之間同步瀏覽紀錄呢？
> 本題的陣列加游標只描述單一裝置的導覽狀態，跨裝置同步時要分清兩種資料：「造訪紀錄」（每次 visit 的 url 與時間）可以視為 append-only 的事件流，各裝置上傳後依時間合併即可，不會衝突；「目前位置與前進紀錄」是每台裝置各自的狀態，通常不同步。若一定要同步導覽狀態，就把每個 `visit`／`back`／`forward` 當成帶裝置 id 與邏輯時鐘的操作，依全序重播；但兩台裝置同時從同一頁 visit 不同 url 會產生分支，這又回到 F1 的樹狀結構。面試時說清楚「哪些狀態需要全域一致、哪些可以各自保存」就是重點。

## 核心題 5｜341. Flatten Nested List Iterator｜Medium

### 題目

給一個巢狀串列 `nestedList`，每個元素是 `NestedInteger`：它要嘛是一個整數，要嘛是一個（可能為空的）`NestedInteger` 串列。`NestedInteger` 提供三個方法：`isInteger()`、`getInteger()`（是整數時回傳整數）、`getList()`（是串列時回傳串列）。請實作 iterator（迭代器）`NestedIterator`：

- `NestedIterator(nestedList)`：用巢狀串列初始化。
- `next()`：依深度優先、由左到右的順序回傳下一個整數。
- `hasNext()`：還有整數可以回傳時回傳 `True`。

呼叫者會反覆「`while hasNext(): next()`」，結果必須等於把巢狀結構攤平後的整數序列。限制：總整數個數最多 10⁴，整數在 `-10⁶` 到 `10⁶` 之間。

- 範例 1：`[[1, 1], 2, [1, 1]]` → 依序回傳 `1, 1, 2, 1, 1`。
- 範例 2：`[1, [4, [6]]]` → 依序回傳 `1, 4, 6`。
- 範例 3（邊界）：`[[], [[]]]` → 沒有任何整數，第一次 `hasNext()` 就回傳 `False`。
- 範例 4（邊界）：`[[], 3, [[], [4]]]` → `3, 4`，空串列要被跳過。

### 思路

最簡單的做法是在建構時就用遞迴把整個結構攤平成一個 list，之後 `next` 與 `hasNext` 只是移動索引，都是 O(1)。這個 eager（急切）做法能通過題目，但面試官通常會追問：如果巢狀串列非常大、或呼叫者只想讀前幾個整數，先攤平全部就浪費了時間與 O(N) 空間。iterator 的意義就是 lazy（延遲）：需要下一個時才往下走。

把攤平的遞迴寫出來：`for x in lst: if x 是整數: 輸出 x; else: 遞迴處理 x.getList()`。遞迴在呼叫堆疊上保存了「每一層走到第幾個元素」；iterator 每次 `next` 都要暫停並返回，所以必須把這個呼叫堆疊**顯式地存成 stack**。stack 的每一層是 `[串列, 下一個要看的索引]`，最上層是目前所在的最深那層。

真正的難點是 `hasNext`：stack 不為空不代表還有整數，因為剩下的可能全是空串列（範例 3）。所以把「往前推進到下一個整數」的工作放在 `hasNext`：看最上層的下一個元素，若該層已走完就 pop；若是串列就推進這層的索引並 push 新的一層；若是整數就停下來回傳 `True`。invariant：`hasNext` 回傳 `True` 時，stack 最上層的下一個元素一定是整數。`next` 先呼叫 `hasNext` 確保 invariant 成立，再取出那個整數並把索引加一。

```text
nestedList = [[], 3, [[], [4]]]       stack 每層寫成 (串列, 索引)

hasNext()  stack: ([[],3,[[],[4]]], 0)
           看到 []      → 推進索引、push ([], 0)
           ([], 0) 已走完 → pop
           回到外層看索引 1：3 是整數 → True
next()     回傳 3，外層索引 → 2
hasNext()  外層索引 2：[[],[4]] 是串列 → 外層索引 → 3，push ([[],[4]], 0)
           看到 []      → push ([], 0)，立刻走完 → pop
           看到 [4]     → push ([4], 0)
           4 是整數 → True
next()     回傳 4
hasNext()  ([4], 1) 走完 pop；([[],[4]], 2) 走完 pop；外層 (…, 3) 走完 pop
           stack 空 → False
```

每個串列只會被 push 一次、pop 一次，每個元素只會被看一次，所以 n 次 `next` 加上所有 `hasNext` 的總成本是 O(N + L)，N 是整數個數、L 是串列個數，攤到每次 `next` 是 amortized O(1)。

### 解法

```python
import random
from typing import Iterator


class NestedInteger:
    """LeetCode 介面的本地模擬：value 是 int 或 list[NestedInteger]。"""

    def __init__(self, value):
        self.value = value

    def isInteger(self) -> bool:
        return isinstance(self.value, int)

    def getInteger(self) -> int:
        return self.value

    def getList(self) -> list["NestedInteger"]:
        return self.value


def wrap(obj) -> list[NestedInteger]:
    """把 Python 巢狀 list 轉成 list[NestedInteger]。"""
    return [NestedInteger(x) if isinstance(x, int) else NestedInteger(wrap(x)) for x in obj]


class NestedIterator:
    def __init__(self, nestedList: list[NestedInteger]):
        self.stack = [[nestedList, 0]]

    def hasNext(self) -> bool:
        while self.stack:
            lst, i = self.stack[-1]
            if i == len(lst):                 # 這一層走完
                self.stack.pop()
                continue
            item = lst[i]
            if item.isInteger():
                return True                   # invariant：頂層的下一個元素是整數
            self.stack[-1][1] += 1            # 先跳過這個子串列，再進入它
            self.stack.append([item.getList(), 0])
        return False

    def next(self) -> int:
        if not self.hasNext():
            raise StopIteration
        top = self.stack[-1]
        val = top[0][top[1]].getInteger()
        top[1] += 1
        return val


def flatten_gen(nested: list[NestedInteger]) -> Iterator[int]:
    """generator 版本：寫法最短，但遞迴深度等於巢狀深度。"""
    for x in nested:
        if x.isInteger():
            yield x.getInteger()
        else:
            yield from flatten_gen(x.getList())


def drain(it: NestedIterator) -> list[int]:
    out = []
    while it.hasNext():
        out.append(it.next())
    return out


assert drain(NestedIterator(wrap([[1, 1], 2, [1, 1]]))) == [1, 1, 2, 1, 1]
assert drain(NestedIterator(wrap([1, [4, [6]]]))) == [1, 4, 6]
assert drain(NestedIterator(wrap([[], [[]]]))) == []
assert drain(NestedIterator(wrap([[], 3, [[], [4]]]))) == [3, 4]
assert drain(NestedIterator(wrap([]))) == []

it = NestedIterator(wrap([[[]], 7]))
assert it.hasNext() and it.hasNext() and it.next() == 7 and not it.hasNext()   # hasNext 可重複呼叫

node = NestedInteger(5)
for _ in range(5000):                         # 深度 5000 的巢狀：顯式 stack 不受遞迴深度限制
    node = NestedInteger([node])
assert drain(NestedIterator([node, NestedInteger(6)])) == [5, 6]


def rand_nested(rng, depth=0):
    out = []
    for _ in range(rng.randint(0, 3)):
        if depth < 4 and rng.random() < 0.4:
            out.append(rand_nested(rng, depth + 1))
        else:
            out.append(rng.randint(-9, 9))
    return out


def py_flatten(obj):
    return [obj] if isinstance(obj, int) else [y for x in obj for y in py_flatten(x)]


rng = random.Random(11)
for _ in range(500):
    obj = rand_nested(rng)
    want = py_flatten(obj)
    assert drain(NestedIterator(wrap(obj))) == want == list(flatten_gen(wrap(obj)))
print("all tests passed")
```

### 複雜度與邊界

時間：建構 O(1)；所有 `next` 與 `hasNext` 的總成本是 O(N + L)，因為每個串列只被 push 與 pop 一次、每個元素只被看一次，所以每次 `next` 是 amortized O(1)（單次 `hasNext` 最差可能要跳過很多空串列）。空間 O(D)，D 是巢狀深度，stack 只存「目前路徑上的每一層」；eager 攤平版本則要 O(N)。邊界：全部是空串列（`[[], [[]]]`）時第一次 `hasNext` 就要回 `False`；`hasNext` 可能被連續呼叫多次，它必須是冪等的（idempotent，重複呼叫結果相同），本解法第二次呼叫時頂層已經指向整數，會立刻回傳；`next` 在沒有元素時呼叫屬於不合法操作，這裡丟出 `StopIteration`；巢狀深度很大時 generator 版本會碰到 Python 的遞迴上限（預設約 1000），顯式 stack 版本不會。

### Follow-up

> [!question]- F1. 為什麼不在建構時直接攤平？什麼情況下 lazy 版本一定比較好？
> Eager 攤平在建構時花 O(N + L) 時間與 O(N) 空間，之後每次 O(1)，若呼叫者一定會讀完全部，總時間其實和 lazy 一樣。Lazy 版本的優勢在三種情況：呼叫者只讀前 k 個就停（例如找第一個負數），lazy 只花 O(k + 途經的串列數)；資料量大到放不進記憶體，或子串列本身是從磁碟、網路逐步載入的，lazy 只需要 O(深度) 的空間；以及建構時間需要很短（例如 API 一建立就要回應）。面試時先寫 eager 當基準沒有問題，但要主動說明 iterator 的本意是 lazy，並把推進邏輯放在 `hasNext`。

> [!question]- F2. 如果巢狀深度可能達到 10⁵，generator 寫法有什麼問題？
> `yield from` 的遞迴版本每深一層就多一個 generator frame，深度超過 Python 的遞迴上限時會丟出 `RecursionError`；就算調高上限，每次 `next` 也要把值沿著 D 層 generator 一層層傳上來，單次是 O(D)，總時間可能退化成 O(N · D)。顯式 stack 版本把每一層存成 `[串列, 索引]`，深度只影響 stack 長度，取下一個整數時只看頂層，沒有遞迴上限的問題，總時間維持 O(N + L)。這也是面試時寧可多寫幾行顯式 stack 的理由。

> [!question]- F3. 如果在迭代途中，有人修改了底層的巢狀串列呢？
> 本解法在 stack 中存的是「串列參考＋索引」，若有人在目前走到的串列中插入或刪除元素，索引就會指向錯誤的位置，可能跳過或重複回傳元素。標準做法是 fail-fast（快速失敗）：讓每個串列帶一個修改計數器，iterator 在 push 一層時記下當時的計數，每次讀取前比對，不同就丟出例外，這正是 Java 集合類別的 `ConcurrentModificationException` 機制。若一定要支援修改，就在建構時對需要的部分做快照（犧牲空間），或改用不可變（immutable）的巢狀結構。

> [!question]- F4. 如果還要支援 peek()，在不前進的情況下看下一個整數（284. Peeking Iterator）呢？
> 本解法的 invariant 已經提供了 peek：`hasNext()` 回傳 `True` 後，頂層的下一個元素就是下一個整數，所以 `peek()` 是「呼叫 `hasNext()`，然後回傳 `stack[-1][0][stack[-1][1]].getInteger()`，但不推進索引」，amortized O(1)。若底層 iterator 是黑盒子、只有 `next` 與 `hasNext`（284 題的情況），做法是多存一個「預取值」：建構時先取一個放著，`peek` 回傳它，`next` 回傳它並再預取下一個，`hasNext` 只看預取值是否存在。

> [!question]- F5. 同樣的「stack 模擬遞迴」iterator，還能用在哪些題目？
> 任何「遞迴走訪但要逐個吐出結果」的題目都適用，差別只在 stack 每層存什麼。173. Binary Search Tree Iterator 是 in-order 走訪：stack 存「還沒輸出的祖先節點」，`next` 彈出一個節點後把它右子樹的左鏈全部 push，amortized O(1)、空間 O(樹高)。251. Flatten 2D Vector 是只有兩層的特例，用兩個索引 `(row, col)` 就夠了，`hasNext` 同樣要跳過空列。281. Zigzag Iterator 則是多個 iterator 輪流輸出，改用 queue 存「還沒用完的 iterator」，每次從前面取一個、輸出一個元素、若還有剩就放回尾端。

## 難題 1｜460. LFU Cache｜Hard

### 題目

設計一個容量為 `capacity` 的 LFU（Least Frequently Used，最不常使用）快取：

- `get(key)`：key 存在時回傳值，否則回傳 `-1`。
- `put(key, value)`：key 存在時更新值；不存在時插入。若插入新 key 前快取已滿，要先淘汰**使用次數最少**的 key；如果多個 key 的使用次數一樣少，淘汰其中**最久沒被使用**的那個。

每個 key 有一個使用次數：新插入時為 1，之後每次成功的 `get` 或對它的 `put` 都加 1。兩個操作都要平均 O(1)。限制：`1 <= capacity <= 10⁴`，key 與 value 非負，總呼叫次數最多 2 × 10⁵。（舊版題目允許 `capacity = 0`，此時 `put` 什麼都不做。）

- 範例 1：容量 2；`put(1, 1)`、`put(2, 2)`、`get(1)` → `1`（1 的次數變 2）、`put(3, 3)`（淘汰次數最少的 2）、`get(2)` → `-1`、`get(3)` → `3`（3 的次數變 2）、`put(4, 4)`（1 與 3 次數都是 2，1 較久沒用，淘汰 1）、`get(1)` → `-1`、`get(3)` → `3`、`get(4)` → `4`。
- 範例 2（邊界）：容量 1；`put(1, 1)`、`get(1)`（次數 2）、`put(2, 2)` 必須淘汰 1（快取只放得下一個，新 key 的次數 1 比較少也沒關係，因為淘汰發生在插入之前）、`get(1)` → `-1`、`get(2)` → `2`。
- 範例 3（邊界）：容量 2；`put(1, 1)`、`put(1, 5)`（更新也算使用，次數 2）、`put(2, 2)`、`put(3, 3)` 淘汰的是 2。

### 提示

> [!tip]- 提示 1
> 淘汰的優先順序是 `(使用次數, 最後使用時間)` 的字典序最小者。用 heap 可以做到 O(log n)，但要 O(1) 就不能做一般的「排序」；想想使用次數每次是怎麼變化的。

> [!tip]- 提示 2
> 使用次數每次只加 1，新 key 永遠從 1 開始。把同樣次數的 key 放在同一個桶裡，桶內依最近使用排序（就是一個小的 LRU）。一個 key 被使用時，只是從桶 f 移到桶 f + 1。

> [!tip]- 提示 3
> 另外記住目前的最小次數 `min_freq`。它只有三種變化：插入新 key 時變成 1；被使用的 key 原本在 `min_freq` 的桶、而且那個桶因此變空時變成 `min_freq + 1`；其他情況不變。淘汰時直接從 `min_freq` 的桶取最舊的 key。

### 詳解

**為什麼直覺做法不夠**。把每個 key 的 `(freq, last_used)` 放進 heap，淘汰時取堆頂，O(log n)；但每次使用都會改變 key 的優先順序，heapq 不支援就地修改，只能 push 新項目並 lazy 刪除舊項目，heap 的大小會隨操作次數而不是快取大小成長。若把所有 key 串成一條依 `(freq, last_used)` 排序的雙向 linked list，使用一個 key 時要把它往後移到「次數 f + 1 的那群」的最後，若次數 f 的 key 很多，往後找位置就是 O(n)。問題的本質是：我們需要一個依兩個維度排序、又能 O(1) 調整的結構。

**突破點一：分層**。第一個維度（次數）用多層 hash 處理：`buckets[f]` 是所有次數為 f 的 key，桶內依最近使用排序，所以每個桶就是一個核心題 1 的 LRU。Python 的 `OrderedDict` 剛好提供 O(1) 的「刪除任意 key」「加到最後」「彈出最前面」，用它當桶就不必手寫節點。一個 key 被使用時，從 `buckets[f]` 刪掉、加到 `buckets[f + 1]` 的最後，因為它是此刻最近被使用的，放在最後正好維持桶內順序。

**突破點二：最小次數不需要搜尋**。淘汰要找「最小的非空桶」，若每次掃描所有桶就不是 O(1)。關鍵觀察是 `min_freq` 的變化非常受限：一個 key 被使用時，次數從 f 變成 f + 1，只有當 f 正好是 `min_freq` 而且 `buckets[f]` 因此變空時，最小次數才會改變，而且新的最小值就是 f + 1（剛被移過去的這個 key 就在那裡，比它更小的桶原本就不存在）。插入新 key 時，它的次數是 1，所以 `min_freq = 1`。淘汰本身不需要更新 `min_freq`，因為淘汰後一定緊接著插入新 key，`min_freq` 會被設成 1。

**正確性**。維持四條 invariant：`vals` 與 `freq` 的 key 集合就是快取內容；每個 key 恰好在 `buckets[freq[key]]` 中；每個桶內依最後使用時間由舊到新排列；`min_freq` 是最小的非空桶（快取非空時）。由前兩條，淘汰的候選就是 `buckets[min_freq]`；由第三條，桶的第一個就是同次數中最久沒用的。每個操作都只改常數個字典項目，所以是 O(1)。

```text
容量 2；桶的內容由左到右 = 舊 → 新

操作        freq           buckets                    min_freq   說明
put(1,1)    {1:1}          1:[1]                      1
put(2,2)    {1:1,2:1}      1:[1,2]                    1
get(1)=1    {1:2,2:1}      1:[2]  2:[1]               1          桶 1 還有 2，min 不變
put(3,3)    淘汰 buckets[1] 最舊 = 2
            {1:2,3:1}      1:[3]  2:[1]               1          新 key → min = 1
get(3)=3    {1:2,3:2}      2:[1,3]                    2          桶 1 變空且 = min → min = 2
put(4,4)    淘汰 buckets[2] 最舊 = 1（1 與 3 同次數，1 較舊）
            {3:2,4:1}      1:[4]  2:[3]               1
get(1)=-1   沒命中，不變
```

`get(3)` 那一步示範 `min_freq` 唯一需要「推進」的情況：3 原本在最小桶，移走後桶變空，所以最小值變成 3 的新次數 2。`put(4, 4)` 示範同次數時依 LRU 決定：桶 2 中 1 排在 3 前面，因為 1 是較早被移進桶 2 的。

### 解法

```python
import random
from collections import OrderedDict, defaultdict


class LFUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.vals: dict[int, int] = {}
        self.freq: dict[int, int] = {}
        self.buckets: defaultdict[int, OrderedDict] = defaultdict(OrderedDict)
        self.min_freq = 0

    def _touch(self, key: int) -> None:
        f = self.freq[key]
        del self.buckets[f][key]
        if not self.buckets[f]:
            del self.buckets[f]
            if self.min_freq == f:
                self.min_freq = f + 1
        self.freq[key] = f + 1
        self.buckets[f + 1][key] = None            # 加到最後 = 這個次數中最近使用

    def get(self, key: int) -> int:
        if key not in self.vals:
            return -1
        self._touch(key)
        return self.vals[key]

    def put(self, key: int, value: int) -> None:
        if self.cap <= 0:
            return
        if key in self.vals:
            self.vals[key] = value
            self._touch(key)
            return
        if len(self.vals) == self.cap:
            old, _ = self.buckets[self.min_freq].popitem(last=False)   # 最少次數中最舊的
            if not self.buckets[self.min_freq]:
                del self.buckets[self.min_freq]
            del self.vals[old], self.freq[old]
        self.vals[key] = value
        self.freq[key] = 1
        self.buckets[1][key] = None
        self.min_freq = 1


class LFUModel:                                     # 暴力模型：淘汰時掃描 (次數, 最後使用時間)
    def __init__(self, capacity):
        self.cap, self.data, self.clock = capacity, {}, 0   # key -> [value, freq, last_used]

    def _use(self, key):
        self.clock += 1
        self.data[key][1] += 1
        self.data[key][2] = self.clock

    def get(self, key):
        if key not in self.data:
            return -1
        self._use(key)
        return self.data[key][0]

    def put(self, key, value):
        if self.cap <= 0:
            return
        if key in self.data:
            self.data[key][0] = value
            self._use(key)
            return
        if len(self.data) == self.cap:
            victim = min(self.data, key=lambda k: (self.data[k][1], self.data[k][2]))
            del self.data[victim]
        self.clock += 1
        self.data[key] = [value, 1, self.clock]


c = LFUCache(2)
c.put(1, 1); c.put(2, 2)
assert c.get(1) == 1
c.put(3, 3)
assert c.get(2) == -1 and c.get(3) == 3
c.put(4, 4)
assert c.get(1) == -1 and c.get(3) == 3 and c.get(4) == 4

c = LFUCache(1)
c.put(1, 1); c.get(1); c.put(2, 2)
assert c.get(1) == -1 and c.get(2) == 2

c = LFUCache(2)
c.put(1, 1); c.put(1, 5); c.put(2, 2); c.put(3, 3)
assert c.get(2) == -1 and c.get(1) == 5 and c.get(3) == 3

c = LFUCache(0)
c.put(1, 1)
assert c.get(1) == -1

rng = random.Random(2)
for cap in (1, 2, 3, 4):
    fast, slow = LFUCache(cap), LFUModel(cap)
    for _ in range(4000):
        k = rng.randint(0, 6)
        if rng.random() < 0.5:
            assert fast.get(k) == slow.get(k)
        else:
            v = rng.randint(0, 99)
            fast.put(k, v)
            slow.put(k, v)
        assert all(fast.buckets.values())                       # 沒有空桶
        assert not fast.vals or fast.min_freq == min(fast.buckets)
print("all tests passed")
```

### 複雜度與邊界

時間：`get` 與 `put` 都是平均 O(1)：dict 與 `OrderedDict` 的查找、刪除、尾端插入、`popitem(last=False)` 都是 O(1)，`min_freq` 的更新不需要搜尋。空間 O(capacity)：每個 key 在 `vals`、`freq` 各一項，並恰好出現在一個桶中；空桶會被刪除，所以桶的數量也不超過 capacity。邊界：容量 0 直接忽略 `put`；`put` 已存在的 key 要算一次使用且不淘汰；容量 1 時新 key 一定淘汰舊 key，即使舊 key 次數很高；淘汰後 `buckets[min_freq]` 可能變空，要一起刪掉，否則下一次淘汰時若 `min_freq` 沒有被重設，會從空桶 `popitem` 而出錯（本解法因為插入時一定設 `min_freq = 1` 而不會發生，但刪除空桶讓 invariant 更乾淨）。

### Follow-up

> [!question]- F1. 如果要支援 delete(key)，主動移除一個 key 呢？
> 從 `vals`、`freq` 與 `buckets[f]` 刪除都是 O(1)，問題出在 `min_freq`：如果被刪的 key 剛好是最小桶中唯一的 key，新的最小次數可能是任何更大的值（例如次數 {1, 50}，刪掉次數 1 的那個，最小值跳到 50），不再是「加 1」那麼簡單。若要維持 O(1)，就要把桶本身串成依次數排序的雙向 linked list（也就是難題 2 的結構），桶空了就從 list 中拿掉，最小次數永遠是 list 的第一個桶。另一個折衷是：delete 時若最小桶變空就把 `min_freq` 標成「未知」，下次淘汰時才往上掃描，掃描成本攤到被刪的 key 上。

> [!question]- F2. LFU 有「舊的熱門 key 永遠不會被淘汰」的問題，怎麼處理？
> 一個 key 在早期被讀了上萬次，之後不再使用，它的次數仍然最高，會一直占用快取（cache pollution，快取污染）。常見解法有三：一是定期衰減（aging），例如每隔一段時間把所有次數除以 2，O(n) 一次，可以用「全域 epoch ＋ 每個 key 記錄上次更新的 epoch」讓衰減延遲到 key 被碰到時才計算；二是 LFU with Dynamic Aging，優先序改成 `freq + L`，L 是上次被淘汰項目的優先序，新進的 key 從 L 起跳，這個值不再每次只加 1，所以要改用 heap，O(log n)；三是 Window TinyLFU 這類做法，用 count-min sketch（用幾個 hash 函式對應到一個小計數表、取最小值當估計的近似計數結構，只會高估不會低估）估計近期頻率並定期減半，再搭配一個小的 LRU 窗口接住新 key。

> [!question]- F3. 如果多個執行緒同時存取呢？
> 和 LRU 一樣，`get` 會修改次數與桶，所以讀操作也要取得寫入權限，最簡單是一把 mutex 包住 `get` 與 `put`。LFU 的鎖競爭比 LRU 更嚴重，因為每次 `get` 都要動兩個桶與 `min_freq`。實務上的做法是把「記錄存取」和「調整結構」分開：`get` 只把 key 丟進一個 lock-free 的存取緩衝區（或只增加一個近似計數器），由單一執行緒批次重播這些存取來更新桶；這會讓淘汰決策稍微延遲，但讀取路徑幾乎不需要鎖，這是高效能快取函式庫常見的設計。也可以依 key 分片，每片一個獨立的 LFU 與鎖，淘汰變成「片內」的 LFU。

> [!question]- F4. 如果同次數時改成淘汰「key 最小」的，而不是最久沒用的呢？
> 桶內的順序從「時間」變成「key 的大小」，就不能再用 append 到最後來維持排序。每個桶要改成能找最小值、又能刪除任意元素的結構：可以每個桶一個 heap 加 lazy deletion（刪除時只做記號），淘汰時清掉堆頂已離開這個桶的 key，amortized O(log n)；或在有平衡 BST 的語言用 TreeSet，O(log n)。整體從 O(1) 退化成 O(log n)，原因是「依時間排序」之所以 O(1)，是因為新來的永遠排最後，而任意 key 的大小沒有這種單調性。

> [!question]- F5. 如果要做成多台機器上的分散式 LFU 快取呢？
> 精確的全域 LFU 需要每次存取都更新全域次數，跨機器同步太貴。常見做法是用 consistent hashing 把 key 分到不同機器，每台機器維護本地的 LFU，因為同一個 key 的所有存取都落在同一台，本地次數就是全域次數，淘汰也只需要在本地做。真正的問題是熱門 key 造成單台機器過載：可以在客戶端加一層小快取吸收熱門讀取，但這會讓伺服器端看到的次數偏低，LFU 的決策跟著失真。若只是想知道全域哪些 key 最熱門（而不是精確淘汰），可以讓每台機器用 count-min sketch 估計頻率，定期合併（sketch 可以直接相加），空間與 key 數無關。

### 心得

關鍵突破是「次數每次只加 1、新 key 永遠從 1 開始」，所以最小次數只會重設成 1 或推進 1，不需要任何排序結構；剩下的就是把每個次數的桶做成一個 LRU。這題是核心題 1 的直接延伸：LRU 是「一個依時間排序的 list」，LFU 是「依次數分層、每層一個 LRU」，也是難題 2 與難題 4 的共同主題：當某個值每次只變 1，就能用分桶取代排序。面試時先說出淘汰順序是 `(次數, 最後使用時間)`，提出 heap 的 O(log n) 版本當基準，再說明三種 `min_freq` 變化情況來證明 O(1)；寫程式時把「使用一次」抽成 `_touch`，`get` 與 `put` 共用，最不容易漏掉同步。

## 難題 2｜432. All O(1) Data Structure｜Hard

### 題目

設計一個計數結構 `AllOne`，每個字串 key 有一個正整數計數：

- `inc(key)`：把 key 的計數加 1；key 不存在時以計數 1 插入。
- `dec(key)`：把 key 的計數減 1；計數變成 0 時移除 key。保證呼叫時 key 存在。
- `getMaxKey()`：回傳任一個計數最大的 key；沒有任何 key 時回傳 `""`。
- `getMinKey()`：回傳任一個計數最小的 key；沒有任何 key 時回傳 `""`。

四個操作都要平均 O(1)。限制：key 長度最多 10，總呼叫次數最多 5 × 10⁴。

- 範例 1：`inc("a")`、`inc("b")`、`inc("b")` → 計數 `{a: 1, b: 2}`，`getMaxKey()` → `"b"`、`getMinKey()` → `"a"`；接著 `inc("a")`、`inc("a")` → `{a: 3, b: 2}`，max 是 `"a"`、min 是 `"b"`。
- 範例 2（邊界）：`{a: 1, b: 100}` 時 `dec("a")` → a 被移除，`getMinKey()` 直接跳到 `"b"`（最小計數從 1 跳到 100）。
- 範例 3（邊界）：空結構時 `getMaxKey()` 與 `getMinKey()` 都回傳 `""`；`inc("x")` 後 `dec("x")`，結構又變空。

### 提示

> [!tip]- 提示 1
> 計數每次只變 1。若把「計數相同的 key」放在同一個桶，一個 key 被 inc 時只會從桶 c 移到桶 c + 1。想想那個桶在哪裡。

> [!tip]- 提示 2
> 只記最大值與最小值不夠，因為 dec 會讓最小值「跳」（範例 2）。把所有非空的桶依計數排序串起來，最小與最大就是兩端。為什麼插入新桶不需要搜尋位置？

> [!tip]- 提示 3
> 桶串成雙向 linked list，dict 存 `key → 所在的桶`。inc 時新桶（計數 c + 1）只可能緊接在目前的桶後面；dec 時新桶（c − 1）只可能緊接在前面。桶變空就從 list 拿掉。用兩個 sentinel 讓頭尾不必特判。

### 詳解

**為什麼直覺做法不夠**。只用 dict 存計數，inc 與 dec 是 O(1)，但 getMax／getMin 要掃描所有 key，O(n)。用兩個 heap（max-heap 與 min-heap）加 lazy deletion 可以讓查詢 amortized O(log n)，但仍然不是 O(1)。像 LFU 那樣只記一個 `min_freq` 也不行：LFU 的次數只增不減，而這題有 dec，範例 2 中刪掉唯一的計數 1 之後，最小值從 1 跳到 100，中間的 2 到 99 都沒有 key，靠「加 1」推進要掃 98 步。

**突破點：計數每次只變 1，所以新桶的位置是已知的**。把所有非空的桶依計數排序，串成雙向 linked list。一個 key 從計數 c 變成 c + 1 時，計數 c + 1 的桶如果存在，一定就是桶 c 的下一個（因為 list 依計數排序，而且 c 和 c + 1 之間沒有其他整數）；如果不存在，就在桶 c 後面新建一個。dec 對稱：計數 c − 1 的桶只可能是前一個。新 key 的計數是 1，它的桶只可能是 list 的第一個（若第一個桶的計數不是 1 就在最前面新建）。整個過程不需要搜尋，每一步都是 O(1) 的指標操作。

**實作細節**。用 sentinel `head`（計數 0）與 `tail`（計數無限大）包住所有真實的桶，這樣「插入到最前面」就是插在 head 之後，`getMaxKey` 是 `tail.prev`，list 為空時 `tail.prev is head`。每個桶存 `count` 與 key 的 set；dict `where` 存 `key → 桶`。先把 key 加入目標桶、再從舊桶移除，最後檢查舊桶是否變空並拿掉；這個順序讓「新桶插在舊桶旁邊」時舊桶仍然在 list 裡，可以當作定位點。

**正確性**。invariant：list 中的桶依計數嚴格遞增，且每個桶非空；每個 key 恰好在 `where[key]` 指向的桶裡，而且該桶的計數等於 key 的計數。由第一條，`head.next` 是最小計數的桶、`tail.prev` 是最大計數的桶，任取其中一個 key 即可。每個操作最多新增一個桶、刪除一個桶，並維持嚴格遞增（新桶的計數與鄰居差 1，且原本鄰居的計數不等於它才會新建），所以 invariant 保持。

```text
H(0) 與 T(∞) 是 sentinel；[c: keys] 是桶

inc a          H ⇄ [1: a] ⇄ T
inc b          H ⇄ [1: a, b] ⇄ T
inc b          H ⇄ [1: a] ⇄ [2: b] ⇄ T          b 從桶 1 移到新建的桶 2（插在桶 1 後面）
inc a          H ⇄ [2: a, b] ⇄ T                a 移到既有的桶 2；桶 1 變空 → 拿掉
inc a          H ⇄ [2: b] ⇄ [3: a] ⇄ T          max = T.prev = 3:a，min = H.next = 2:b
dec b          H ⇄ [1: b] ⇄ [3: a] ⇄ T          桶 1 不存在 → 插在桶 2 前面；桶 2 變空 → 拿掉
dec b          H ⇄ [3: a] ⇄ T                   計數變 0 → 移除 b；min 直接跳到 3
```

最後一步就是範例 2 的情況：b 被移除後，最小值從 1 直接變成 3，但我們不需要搜尋，因為桶 1 被拿掉後 `head.next` 自然就是桶 3。

### 解法

```python
import random


class Bucket:
    __slots__ = ("count", "keys", "prev", "next")

    def __init__(self, count):
        self.count, self.keys = count, set()
        self.prev = self.next = None


class AllOne:
    def __init__(self):
        self.head, self.tail = Bucket(0), Bucket(float("inf"))
        self.head.next, self.tail.prev = self.tail, self.head
        self.where: dict[str, Bucket] = {}

    def _insert_after(self, node: Bucket, count: int) -> Bucket:
        b = Bucket(count)
        b.prev, b.next = node, node.next
        node.next.prev = b
        node.next = b
        return b

    def _unlink_if_empty(self, b: Bucket) -> None:
        if not b.keys:
            b.prev.next, b.next.prev = b.next, b.prev

    def inc(self, key: str) -> None:
        cur = self.where.get(key)
        anchor = cur if cur else self.head          # 新 key 的「目前桶」視為計數 0 的 head
        c = anchor.count
        nxt = anchor.next
        if nxt.count != c + 1:
            nxt = self._insert_after(anchor, c + 1)
        nxt.keys.add(key)
        self.where[key] = nxt
        if cur:
            cur.keys.remove(key)
            self._unlink_if_empty(cur)

    def dec(self, key: str) -> None:
        cur = self.where[key]
        c = cur.count
        if c == 1:
            del self.where[key]
        else:
            prv = cur.prev
            if prv.count != c - 1:
                prv = self._insert_after(prv, c - 1)
            prv.keys.add(key)
            self.where[key] = prv
        cur.keys.remove(key)
        self._unlink_if_empty(cur)

    def getMaxKey(self) -> str:
        return next(iter(self.tail.prev.keys)) if self.tail.prev is not self.head else ""

    def getMinKey(self) -> str:
        return next(iter(self.head.next.keys)) if self.head.next is not self.tail else ""

    def _check(self) -> None:
        b, last = self.head.next, 0
        seen = 0
        while b is not self.tail:
            assert b.keys and b.count > last and b.prev.next is b
            assert all(self.where[k] is b for k in b.keys)
            last, seen, b = b.count, seen + len(b.keys), b.next
        assert seen == len(self.where)


s = AllOne()
s.inc("a"); s.inc("b"); s.inc("b")
assert s.getMaxKey() == "b" and s.getMinKey() == "a"
s.inc("a"); s.inc("a")
assert s.getMaxKey() == "a" and s.getMinKey() == "b"

s = AllOne()
s.inc("a")
for _ in range(100):
    s.inc("b")
s.dec("a")
assert s.getMinKey() == "b" == s.getMaxKey()

s = AllOne()
assert s.getMaxKey() == "" == s.getMinKey()
s.inc("x"); s.dec("x")
assert s.getMaxKey() == "" == s.getMinKey() and not s.where

rng = random.Random(4)
s, cnt = AllOne(), {}
for _ in range(5000):
    k = rng.choice("abcde")
    if k in cnt and rng.random() < 0.45:
        s.dec(k)
        cnt[k] -= 1
        if cnt[k] == 0:
            del cnt[k]
    else:
        s.inc(k)
        cnt[k] = cnt.get(k, 0) + 1
    s._check()
    if cnt:
        assert cnt[s.getMaxKey()] == max(cnt.values())
        assert cnt[s.getMinKey()] == min(cnt.values())
    else:
        assert s.getMaxKey() == s.getMinKey() == ""
print("all tests passed")
```

### 複雜度與邊界

時間：四個操作都是平均 O(1)：dict 與 set 操作平均 O(1)，每次最多新增一個桶、刪除一個桶，各是常數個指標操作；`next(iter(set))` 取任一元素也是 O(1)（集合經過大量刪除後，CPython 的迭代可能要跳過空槽，這是實作細節，理論上仍視為 O(1)）。空間 O(n)，n 是 key 的個數，桶的數量不超過 n。邊界：新 key 的「前一個桶」是計數 0 的 head；dec 到 0 時只移除 key、不建立計數 0 的桶；head 的計數是 0、tail 是無限大，所以 `nxt.count != c + 1` 與 `prv.count != c - 1` 的比較在兩端也成立（c − 1 ≥ 1 時永遠不等於 head 的 0）；空結構時兩個 get 都回傳 `""`。

### Follow-up

> [!question]- F1. 如果 inc 與 dec 可以一次加減任意的 delta 呢？
> O(1) 的關鍵「新桶一定是鄰居」就消失了：計數從 3 變成 50，要在 list 中找到計數 50 該放的位置，中間可能有很多桶。這時需要一個能依計數有序插入與查找的結構：平衡 BST（例如 Java 的 `TreeMap<count, keys>`）或 Python 的 `SortedList`，每次 inc／dec 為 O(log m)，m 是不同計數的個數，getMax／getMin 為 O(1)（有序結構的兩端）或 O(log m)。只用標準函式庫的話，可以用兩個 heap 存 `(count, key)` 搭配「目前計數」的 dict 做 lazy deletion：查詢時丟掉計數已過期的項目，amortized O(log n)。

> [!question]- F2. 如果要回傳計數最大的前 k 個 key（top-k）呢？
> 從 `tail.prev` 開始往前走，依序輸出每個桶的 key，湊滿 k 個就停，時間 O(k + 走過的桶數)，而每個走過的桶至少貢獻一個 key，所以就是 O(k)。如果同一桶內也要依字典序輸出，就要對那個桶的 key 排序，或把桶的 set 換成有序結構。這比 heap 版本（第 14 章核心題 2 的 347 題，每次 O(n log k)）更適合「計數持續變動、隨時要查 top-k」的情境，因為維護成本已經攤在每次 inc／dec 的 O(1) 上。

> [!question]- F3. 如果 key 非常多、只想用固定記憶體找出最頻繁的 key（heavy hitters）呢？
> 本題的結構正好是 Space-Saving 演算法的實作方式：只保留 m 個 key（容量 m），新 key 到來而容量已滿時，取出計數最小的 key（`head.next` 的桶中任一個）替換成新 key，並讓新 key 的計數變成「被替換者的計數 + 1」，等於對被替換的 key 做了一次 inc 再換名字，仍然只是移到相鄰的桶，O(1)。Space-Saving 保證每個 key 的估計值最多高估「被替換時的最小計數」，所以真實頻率超過 N/m 的 key 一定會留在結構中。這是串流 top-k 統計常用的方法，記憶體只和 m 有關。

> [!question]- F4. 如果多個執行緒同時 inc 與 dec 呢？
> 所有 key 共用同一條桶 list，兩個不同 key 的 inc 可能同時在同一個桶旁邊新建桶，所以不能只鎖單一 key，最直接的是一把全域鎖。若 inc／dec 的頻率遠高於查詢，可以把兩件事分開：每個執行緒或每個分片用一個普通的 dict 累積計數（分片鎖或 thread-local），查詢 max／min 時再合併，或由背景執行緒定期把累積的變化套用到桶 list，查詢讀到的是稍微延遲的結果。面試時要說清楚取捨：完全精確的即時 max／min 需要序列化所有更新，而「最終一致」的版本能換來高得多的寫入吞吐量。

> [!question]- F5. 如果 getMaxKey 要回傳計數最大的 key 中「字典序最小」的那一個呢？
> 每個桶的 set 換成能 O(log b) 取最小值的結構（b 是桶內 key 數），例如 heap 加 lazy deletion 或 `SortedList`，inc／dec 時從舊桶刪除、加入新桶都變成 O(log b)，查詢 O(log b) 或 O(1)。桶之間的排序完全不受影響，因為那仍然只依計數，而計數每次只變 1。也就是說，「跨桶的順序」與「桶內的順序」是兩個獨立的維度，前者靠只變 1 做到 O(1)，後者若需要依任意鍵排序就要付 O(log) 的代價，這個分析和難題 1 的 F4 相同。

### 心得

關鍵突破是「計數每次只變 1，所以目標桶一定是目前桶的鄰居」，有了這個觀察，依計數排序的桶 list 就能在不搜尋的情況下維持。它和難題 1（LFU）是同一個想法的兩種強度：LFU 只增不減，記一個 `min_freq` 就夠；這題可增可減，最小值會跳，所以要把整個桶的順序都串起來。面試時先用範例 2 說明為什麼只記極值不夠，再畫出桶的雙向 list，強調 sentinel 讓「新 key 進入計數 1」與「計數 1 的 key 被移除」都不必特判；寫完用一個 `_check` 逐條驗證 invariant，最能展現你對結構正確性的掌握。

## 難題 3｜716. Max Stack｜Hard

### 題目

設計一個 stack `MaxStack`，除了一般的 stack 操作，還能查詢與移除最大值：

- `push(x)`：把 x 放到頂端。
- `pop()`：移除並回傳頂端元素。
- `top()`：回傳頂端元素但不移除。
- `peekMax()`：回傳目前最大的元素但不移除。
- `popMax()`：移除並回傳目前最大的元素；若有多個相同的最大值，移除**最靠近頂端**的那一個。

保證 `pop`、`top`、`peekMax`、`popMax` 被呼叫時 stack 非空。目標：`top` 為 O(1)，其他操作 O(log n)。限制：x 在 `-10⁷` 到 `10⁷` 之間，總呼叫次數最多 10⁵。

- 範例 1：`push(5)`、`push(1)`、`push(5)`、`top()` → `5`、`popMax()` → `5`（移除的是最上面的 5）、`top()` → `1`、`peekMax()` → `5`、`pop()` → `1`、`top()` → `5`。
- 範例 2（邊界）：`push(3)`、`popMax()` → `3`，stack 變空；`push(2)`、`top()` → `2`、`peekMax()` → `2`。
- 範例 3（邊界）：`push(1)`、`push(2)`、`push(2)`、`push(1)`、`popMax()` → `2`（移除第 3 個元素），之後 stack 由底到頂是 `[1, 2, 1]`，`pop()` → `1`、`popMax()` → `2`、`top()` → `1`。

### 提示

> [!tip]- 提示 1
> 第 10 章核心題 2（155. Min Stack）的「每層存到這層為止的最大值」能做 `peekMax`，但 `popMax` 會從中間刪除，上面各層存的彙總值就錯了。先想清楚：哪兩種順序需要同時維持？

> [!tip]- 提示 2
> 一個結構依「時間」排序（stack），另一個依「值」排序（heap）。每個元素同時在兩邊。從其中一邊刪除時，另一邊怎麼辦？heap 不支援刪除中間元素。

> [!tip]- 提示 3
> 給每次 push 一個唯一遞增的 id。兩邊都存 `(值, id)`，heap 用 `(-值, -id)` 讓「值大、同值時 id 大（較靠近頂端）」排最前。從一邊刪除時，把 id 放進 `removed` 集合；另一邊在查看頂端時，遇到 `removed` 中的 id 就丟掉（lazy deletion），並把 id 從集合中移除。

### 詳解

**為什麼直覺做法不夠**。只用一個 list 當 stack：`peekMax` 要掃一遍 O(n)，`popMax` 要找到最上面的最大值並從中間刪除，也是 O(n)。常見的雙 stack 解法是「主 stack ＋ 每層存目前最大值的 max stack」，`peekMax` O(1)，但 `popMax` 要把最大值上面的元素先彈到暫存區、移除最大值、再一個個 push 回來（push 時重新計算每層的最大值），最差 O(n)。問題在於，「每層的彙總值」只在刪除只發生在頂端時才正確，而 `popMax` 會刪中間。

**突破點：兩個結構各自維持一種順序，刪除只做記號**。`top`／`pop` 需要「依時間的順序」，用 stack；`peekMax`／`popMax` 需要「依值的順序」，用 heap。每個元素在兩邊各有一份。從 stack 刪掉一個元素時，它還留在 heap 裡；從 heap 刪掉時，它還留在 stack 裡。我們不去另一邊找它（heap 找中間元素要 O(n)，stack 從中間刪也要 O(n)），而是記下它的 id 已被刪除，等它浮到另一邊的頂端時才順手丟掉。這就是 27.4 節的 heap ＋ lazy deletion。

**為什麼要 id，而且 heap 要用 `(-值, -id)`**。同一個值可能出現多次（範例 1 的兩個 5），如果用值當刪除標記，刪一個 5 會讓兩個 5 都被跳過，所以每次 push 給一個唯一的遞增 id。題目要求同值時移除最靠近頂端的，也就是 id 最大的，所以 heap 的排序鍵是 `(-值, -id)`：值越大越前、同值時 id 越大越前。stack 中 id 本來就是由底到頂遞增，兩邊對「同一個元素」的認定完全一致。

**正確性與攤還分析**。invariant：目前 stack 中的元素集合，等於「stack list 中 id 不在 `removed` 的項目」，也等於「heap 中 id 不在 `removed` 的項目」；而且每個在 `removed` 中的 id，恰好還殘留在兩個結構的其中一個（另一個已經真的刪掉了）。所以每個 id 在 `removed` 中最多停留到被清理一次，清理後就把它從集合中移除，集合不會無限長大。每個元素最多被 push 進 stack 與 heap 各一次、真的彈出各一次，所以所有清理的總成本是 O(n log n)，攤到每個操作上：`top` 與 `pop` 是 amortized O(1)，`peekMax` 與 `popMax` 是 amortized O(log n)。

```text
範例 1；stack 由底到頂寫 (值,id)；heap 只列出排序鍵 (-值,-id) 的集合（最前面是堆頂）

push 5,1,5   stack [(5,0) (1,1) (5,2)]   heap {(-5,-2) (-5,0) (-1,-1)}   removed {}
top()        stack 頂 (5,2) 有效 → 5
popMax()     heap 彈出 (-5,-2) → id 2 → removed {2}，回傳 5
             stack 不動，(5,2) 變成殘留的「死」元素
top()        stack 頂 (5,2)：id 2 ∈ removed → 丟掉、removed {}
             stack 頂 (1,1) 有效 → 1
peekMax()    heap 頂 (-5,0)：id 0 有效 → 5
pop()        stack 彈出 (1,1) → removed {1}，回傳 1
top()        stack 頂 (5,0) 有效 → 5
popMax()     heap 頂 (-5,0) 有效 → 彈出，removed {1, 0}，回傳 5
             此時 heap 剩 (-1,-1)、stack 剩 (5,0)，兩個都是死元素，下次查看頂端時才清掉
```

第三步的 `top()` 示範 lazy deletion 的運作：被 `popMax` 移除的 5 仍在 stack 頂端，`top` 發現它在 `removed` 中就先丟掉，再看下一個。最後一步之後兩個結構都只剩死元素，邏輯上 stack 是空的；只要不違反「非空才呼叫」的保證，它們會在下一次相應的查看時被清掉。

### 解法

```python
import heapq
import random


class MaxStack:
    def __init__(self):
        self.stack: list[tuple[int, int]] = []          # (值, id)，由底到頂
        self.heap: list[tuple[int, int]] = []           # (-值, -id)
        self.removed: set[int] = set()
        self.next_id = 0
        self.size = 0

    def push(self, x: int) -> None:
        self.stack.append((x, self.next_id))
        heapq.heappush(self.heap, (-x, -self.next_id))
        self.next_id += 1
        self.size += 1

    def _clean_stack(self) -> None:
        while self.stack and self.stack[-1][1] in self.removed:
            self.removed.remove(self.stack.pop()[1])

    def _clean_heap(self) -> None:
        while self.heap and -self.heap[0][1] in self.removed:
            self.removed.remove(-heapq.heappop(self.heap)[1])

    def pop(self) -> int:
        self._clean_stack()
        x, ident = self.stack.pop()
        self.removed.add(ident)                          # heap 裡的那一份之後再清
        self.size -= 1
        return x

    def top(self) -> int:
        self._clean_stack()
        return self.stack[-1][0]

    def peekMax(self) -> int:
        self._clean_heap()
        return -self.heap[0][0]

    def popMax(self) -> int:
        self._clean_heap()
        neg_x, neg_id = heapq.heappop(self.heap)
        self.removed.add(-neg_id)                        # stack 裡的那一份之後再清
        self.size -= 1
        return -neg_x


class MaxStackModel:
    def __init__(self):
        self.a = []

    def push(self, x):
        self.a.append(x)

    def pop(self):
        return self.a.pop()

    def top(self):
        return self.a[-1]

    def peekMax(self):
        return max(self.a)

    def popMax(self):
        m = max(self.a)
        i = len(self.a) - 1 - self.a[::-1].index(m)      # 最靠近頂端的最大值
        return self.a.pop(i)


s = MaxStack()
s.push(5); s.push(1); s.push(5)
assert s.top() == 5 and s.popMax() == 5 and s.top() == 1
assert s.peekMax() == 5 and s.pop() == 1 and s.top() == 5

s = MaxStack()
s.push(3)
assert s.popMax() == 3 and s.size == 0
s.push(2)
assert s.top() == 2 and s.peekMax() == 2

s = MaxStack()
for v in (1, 2, 2, 1):
    s.push(v)
assert s.popMax() == 2 and s.pop() == 1 and s.popMax() == 2 and s.top() == 1

rng = random.Random(8)
fast, slow = MaxStack(), MaxStackModel()
for _ in range(6000):
    if not slow.a or rng.random() < 0.45:
        x = rng.randint(-4, 4)
        fast.push(x)
        slow.push(x)
    else:
        op = rng.choice(["pop", "top", "peekMax", "popMax"])
        assert getattr(fast, op)() == getattr(slow, op)(), op
    assert fast.size == len(slow.a)
    assert len(fast.removed) <= len(fast.stack) + len(fast.heap)
print("all tests passed")
```

### 複雜度與邊界

時間：`push` 是 O(log n)（heap 插入）；`top` 與 `pop` 是 amortized O(1)（清理 stack 的總次數不超過 push 的次數）；`peekMax` 與 `popMax` 是 amortized O(log n)。單一操作的最差情況可能較慢，例如連續多次 `popMax` 之後的一次 `top` 要清掉很多死元素，但總成本有上界。空間 O(總 push 次數)：死元素在被清掉之前仍占空間，最差會是邏輯大小的好幾倍（見 F1）。邊界：同值多份要靠 id 區分；`popMax` 的同值規則靠 `-id` 讓較新的排前面；stack 變空後再 push 要能正常運作，死元素不影響新元素，因為新 id 永遠不在 `removed` 中。

### Follow-up

> [!question]- F1. Lazy deletion 留下的死元素會不會讓記憶體爆掉？怎麼控制？
> 會。例如先 push n 個遞增的數，再做 n 次 `popMax`：heap 每次真的彈出，但 stack 裡的 n 個元素全都變成死元素，若之後不呼叫 `top`／`pop`，它們就一直留著；反過來，push 後一直 `pop`，heap 也會累積死元素。最壞情況下記憶體是 O(總 push 次數) 而不是 O(目前大小)。控制方法是定期重建：當 `len(stack) + len(heap) > 4 × size` 時，用 O(size) 時間把兩邊的死元素全部濾掉、heap 重新 `heapify`、清空 `removed`。觸發一次重建前至少已經發生了 Θ(size) 次刪除，所以重建成本被攤平，amortized 複雜度不變，空間維持 O(size)。

> [!question]- F2. 如果還要支援 popMin（或 peekMin）呢？
> 再加一個 min-heap 存 `(值, -id)`（同值時移除較靠近頂端的，或依題目規定）。困難在 `removed` 集合的語意：現在每個元素存在三個結構中，被其中一個刪除時，另外兩個都要 lazy 跳過，所以「清理一次就從集合中移除」不再正確。改用 `alive[id]` 布林陣列（或 dict）表示元素是否還活著，任何結構遇到 `alive[id] == False` 就丟掉，但不修改 `alive`；陣列大小是總 push 次數，可以搭配 F1 的定期重建回收空間。每個操作的複雜度不變：stack 端 amortized O(1)，兩個 heap 端 amortized O(log n)。

> [!question]- F3. 如果要求每個操作的「最差」複雜度都是 O(log n)（不能只是攤還）呢？
> Lazy deletion 的單次成本沒有上界，所以要改成真的刪除。標準做法是雙向 linked list ＋ 平衡 BST：linked list 依 push 順序存節點，`top`／`pop` 看尾端，O(1)；平衡 BST（Java 的 `TreeMap<值, 節點串列>` 或 C++ 的 `map`）依值排序，每個值對應一串節點（後 push 的在後）。`popMax` 從 BST 取最大值的最後一個節點，從 linked list 中 O(1) 拿掉，BST 端 O(log n)；`pop` 從 linked list 拿掉尾端節點，再到 BST 中刪除它對應的項目，O(log n)。Python 標準函式庫沒有平衡 BST，面試時可以說明用 `SortedList`（第三方）或手寫 treap，但通常 lazy deletion 版本就是預期的答案。treap 是每個節點帶一個隨機優先序、依優先序維持 heap 性質的 BST，期望高度 O(log n)。

> [!question]- F4. 如果是 Max Queue（先進先出，要能 O(1) 查最大值）呢？
> 若只需要 `push`、`popFront`、`peekMax`、不需要 `popMax`，用 monotonic deque（單調佇列）即可：另開一個 deque 存「還有可能成為最大值的元素」，值由前到後非遞增，push 時從尾端彈掉所有比新值小的，`popFront` 時若被彈出的就是 deque 的最前面，就一起彈掉，所有操作 amortized O(1)，這正是 239. Sliding Window Maximum 的技巧。若還要 `popMax`，刪除又發生在中間，就回到本題的雙結構＋lazy deletion，只是把 stack 換成 deque。

> [!question]- F5. 如果多個執行緒同時使用呢？
> 需要注意一個不直覺的地方：`top()` 與 `peekMax()` 看起來是唯讀，但 lazy deletion 讓它們會修改結構（彈出死元素、修改 `removed`），所以不能讓它們在讀鎖下並行，否則兩個執行緒可能同時彈出同一個死元素、或一個在清理時另一個在 push。最簡單是所有操作共用一把 mutex。若讀取遠多於寫入，可以讓修改操作（`pop`、`popMax`）在完成時就順便清理到兩邊的頂端都是活元素，使 `top`／`peekMax` 變成真正的唯讀，再用 read-write lock 讓讀取並行；代價是修改操作的單次成本變高，但 amortized 複雜度不變。

### 心得

關鍵突破是承認「一個結構無法同時依時間與依值排序」，於是讓 stack 與 heap 各管一種順序，刪除時只做記號、等它浮到頂端才清掉，而唯一的 id 讓兩邊能確認是同一個元素。這是本章「heap ＋ lazy deletion」的標準題，也和第 14 章難題 2（480. Sliding Window Median）的延遲刪除同一套想法；它說明了為什麼第 10 章核心題 2 的 Min Stack 技巧無法延伸到 popMax。面試時先說 O(n) 的 popMax 基準與「彙總值失效」的原因，再提出雙結構與 id，最後主動分析 amortized 成本與 F1 的記憶體問題，這是區分「會寫」與「真正理解」的地方。

## 難題 4｜895. Maximum Frequency Stack｜Hard

### 題目

設計一個類似 stack 的結構 `FreqStack`：

- `push(val)`：把整數 val 放進結構。
- `pop()`：移除並回傳**出現次數最多**的元素；若有多個元素的出現次數一樣多，移除並回傳其中**最靠近頂端**（最近一次被 push）的那一個。

保證 `pop` 被呼叫時結構非空。兩個操作都要 O(1)。限制：val 在 0 到 10⁹ 之間，總呼叫次數最多 2 × 10⁴。

- 範例 1：依序 push `5, 7, 5, 7, 4, 5`。之後四次 `pop` 分別回傳 `5`（5 出現 3 次，最多）、`7`（5 與 7 都剩 2 次，7 較靠近頂端）、`5`（5 剩 2 次，最多）、`4`（5、7、4 都是 1 次，4 最靠近頂端）。
- 範例 2（邊界）：push `1, 2, 3`（全部只出現一次），`pop` 依序回傳 `3, 2, 1`，退化成普通的 stack。
- 範例 3（邊界）：push `9, 9, 9`，`pop` 依序回傳 `9, 9, 9`；之後 push `4`、`pop` → `4`。

### 提示

> [!tip]- 提示 1
> 用 `freq[val]` 記錄目前的出現次數。最大次數 `max_freq` 每次 push 只會加 1 或不變；pop 時最多減 1。這點和難題 1 的 `min_freq` 很像。

> [!tip]- 提示 2
> 同一個次數 f 的元素之中要能找到「最近的那一個」，所以對每個次數 f 維護一個 stack。一個元素的出現次數從 f − 1 變成 f 時，把它 push 進 `group[f]`。

> [!tip]- 提示 3
> 一個出現 3 次的元素會同時在 `group[1]`、`group[2]`、`group[3]` 中各有一份，這正是你要的：pop 時從 `group[max_freq]` 彈出一個，它的次數減 1，而它在 `group[max_freq - 1]` 中那一份原本就在正確的位置，不需要搬動。`group[max_freq]` 變空時 `max_freq` 減 1。

### 詳解

**為什麼直覺做法不夠**。用 heap 存 `(-次數, -push 時間, val)`：每次 push 放一個新項目，pop 取堆頂；但 pop 之後該元素的次數減 1，它的「下一個優先順序」是 `(-(f−1), -它上一次 push 的時間)`，必須另外記錄每個元素所有的 push 時間，而且是 O(log n)。若用一般的 list 當 stack，pop 時要先找最大次數、再從頂端往下找第一個符合的元素並從中間刪除，O(n)。要做到 O(1)，必須讓「最大次數中最近的那一個」直接位於某個結構的頂端。

**突破點：依次數分層，每層一個 stack**。觀察一個元素被 push 第 f 次的瞬間：它是「出現次數達到 f 的元素」中最新的一個。所以把這個事件記錄在 `group[f]` 的頂端，`group[f]` 就是「所有次數 ≥ f 的元素，依達到第 f 次的時間排序」。pop 時，所有次數等於 `max_freq` 的元素都在 `group[max_freq]` 中，而它們「達到第 `max_freq` 次的時間」就是它們最後一次被 push 的時間，所以 `group[max_freq]` 的頂端正是「次數最多中最靠近頂端」的那一個。

**為什麼彈出之後不需要搬動**。元素 x 被彈出後次數從 f 變成 f − 1。它在 `group[f − 1]` 中原本就有一份（它第 f − 1 次被 push 時放進去的），那一份的位置代表「x 達到第 f − 1 次的時間」，而這正是 x 現在在 stack 中最上面那一份的 push 時間。也就是說，`group[1..f−1]` 中的紀錄自動描述了「x 只出現 f − 1 次」時的正確狀態。`max_freq` 的更新也只需要常數時間：push 讓某元素次數變成 `max_freq + 1` 時加 1；pop 讓 `group[max_freq]` 變空時減 1，因為被彈出的元素現在次數是 `max_freq − 1`，`group[max_freq − 1]` 一定非空。

**正確性**。invariant：對每個 f ≥ 1，`group[f]` 恰好包含每個「目前次數 ≥ f」的元素一次，依它第 f 次被 push 的時間由舊到新排列；`max_freq` 是最大的非空層。由此 pop 取 `group[max_freq]` 的頂端正確，而彈出只移除該元素在第 `max_freq` 層的紀錄，其他層不受影響，invariant 保持。

```text
push 5, 7, 5, 7, 4, 5

push   freq              group（每層由底到頂）                    max_freq
5      {5:1}             1:[5]                                   1
7      {5:1,7:1}         1:[5,7]                                 1
5      {5:2,7:1}         1:[5,7]   2:[5]                         2
7      {5:2,7:2}         1:[5,7]   2:[5,7]                       2
4      {…,4:1}           1:[5,7,4] 2:[5,7]                       2
5      {5:3,7:2,4:1}     1:[5,7,4] 2:[5,7]  3:[5]                3

pop → group[3] 彈出 5；freq[5]=2；group[3] 空 → max_freq=2     回傳 5
pop → group[2] 彈出 7；freq[7]=1                                回傳 7
pop → group[2] 彈出 5；freq[5]=1；group[2] 空 → max_freq=1     回傳 5
pop → group[1] 彈出 4；freq[4]=0                                回傳 4
```

第二次 pop 是同次數的情況：5 與 7 都剩 2 次，`group[2]` 中 7 在 5 上面，因為 7 是較晚達到第 2 次的，所以彈出 7。第四次 pop 時 `group[1]` 是 `[5, 7, 4]`，頂端是 4，這正是三個都只剩一次時最靠近頂端的元素。

### 解法

```python
import random
from collections import Counter, defaultdict


class FreqStack:
    def __init__(self):
        self.freq: Counter[int] = Counter()
        self.group: defaultdict[int, list[int]] = defaultdict(list)
        self.max_freq = 0

    def push(self, val: int) -> None:
        f = self.freq[val] + 1
        self.freq[val] = f
        if f > self.max_freq:
            self.max_freq = f
        self.group[f].append(val)

    def pop(self) -> int:
        val = self.group[self.max_freq].pop()
        self.freq[val] -= 1
        if not self.group[self.max_freq]:
            del self.group[self.max_freq]
            self.max_freq -= 1
        return val


class FreqStackModel:
    def __init__(self):
        self.a = []

    def push(self, val):
        self.a.append(val)

    def pop(self):
        cnt = Counter(self.a)
        mx = max(cnt.values())
        for i in range(len(self.a) - 1, -1, -1):        # 從頂端往下找第一個次數最多的
            if cnt[self.a[i]] == mx:
                return self.a.pop(i)


fs = FreqStack()
for v in (5, 7, 5, 7, 4, 5):
    fs.push(v)
assert [fs.pop() for _ in range(4)] == [5, 7, 5, 4]

fs = FreqStack()
for v in (1, 2, 3):
    fs.push(v)
assert [fs.pop() for _ in range(3)] == [3, 2, 1] and fs.max_freq == 0

fs = FreqStack()
for v in (9, 9, 9):
    fs.push(v)
assert [fs.pop() for _ in range(3)] == [9, 9, 9]
fs.push(4)
assert fs.pop() == 4

rng = random.Random(6)
fast, slow = FreqStack(), FreqStackModel()
for _ in range(4000):
    if not slow.a or rng.random() < 0.55:
        v = rng.randint(0, 4)
        fast.push(v)
        slow.push(v)
    else:
        assert fast.pop() == slow.pop()
    assert sum(len(g) for g in fast.group.values()) == len(slow.a)
print("all tests passed")
```

### 複雜度與邊界

時間：`push` 與 `pop` 都是 O(1)：dict 與 list 尾端操作都是常數時間，`max_freq` 每次最多變 1。空間 O(n)，n 是目前結構中的元素總數：一個出現 k 次的元素在 `group[1..k]` 各有一份，總份數剛好等於它被 push 而尚未 pop 的次數，所以所有 `group` 的長度總和等於 n，不會多存。邊界：所有元素都不同時退化成普通 stack（只有 `group[1]`）；全部相同時每層各一份，pop 從最高層往下；`max_freq` 降到 0 後再 push 要能正常從 1 開始；`freq[val]` 降到 0 時可以留著（Counter 中的 0 不影響），若在意記憶體可以刪掉。

### Follow-up

> [!question]- F1. 如果還要支援 peek()，只看不彈出呢？
> 答案就是 `group[max_freq][-1]`，O(1)，不需要修改任何狀態。這也說明了本結構的好處：「下一個要彈出的元素」永遠就在某個 list 的尾端，不需要像 lazy deletion 那樣先清理。若要 peek 第 k 個會被彈出的元素，就沒有那麼簡單了，因為彈出會改變次數與層的結構；最直接是在副本上模擬 k 次 pop（O(k)），或用 undo log 記錄 k 次 pop 的變化再還原，同樣 O(k)。

> [!question]- F2. 如果同次數時改成移除「最早被 push」的（最靠近底部）呢？
> 每層的順序從「後進先出」變成「先進先出」：把 `group[f]` 從 list 換成 `collections.deque`，push 時 `append`、pop 時 `popleft`，仍然 O(1)。正確性論證不變：`group[max_freq]` 依「達到第 `max_freq` 次的時間」排序，而對次數剛好是 `max_freq` 的元素來說，這個時間就是它最上面那一份的 push 時間，所以最前面的就是「同次數中最上面那一份最靠近底部」的元素。彈出後它在較低層的紀錄仍依時間排列，不需要搬動。動手前要先和面試官確認「最靠近底部」指的是最上面那一份的位置，還是最早那一份的位置；若是後者，就要另外記錄每個元素第一次 push 的時間，並改用 heap。

> [!question]- F3. 如果改成彈出「出現次數最少」的元素（同次數取最靠近頂端）呢？
> 對稱的做法行不通。彈出次數最少的元素 x（次數 f）之後，x 的次數變成 f − 1，比原本的最小值更小，最小值往下走而不是往上走；更麻煩的是 `group[f]` 的定義是「次數 ≥ f 的元素」，次數最少的元素不一定在 `group[min]` 的頂端（次數更高的元素也在那一層）。可行的做法是每個元素記錄自己所有 push 時間的 stack，再用 heap 存 `(次數, -最近 push 時間, val)` 加 lazy deletion，每次 O(log n)；或用難題 2 的「次數桶雙向 list」，每個桶內依最近時間排序，但桶內排序需要有序結構，所以也是 O(log n)。

> [!question]- F4. 如果要支援 remove(val)，移除 val 最靠近頂端的那一份呢？
> val 的次數是 k，它最上面那一份在 `group[k]` 中，但不一定在 `group[k]` 的頂端，從 list 中間刪除是 O(n)。改法是把每層從 list 換成雙向 linked list，並用 dict 記住 `(val, f) → 該層的節點`：一個值在每一層恰好出現一次，所以 `(val, f)` 是唯一的鍵。`remove(val)` 從 `group[k]` 中拿掉節點 `(val, k)`，O(1)；`freq[val]` 減 1；若 `group[max_freq]` 變空就讓 `max_freq` 減 1（因為只有 k == max_freq 時那層才可能變空，而 val 現在在 k − 1 層，該層一定非空）。push 與 pop 也要同步維護節點表，三個操作都是 O(1)。

> [!question]- F5. 如果多個執行緒同時 push 與 pop 呢？
> `push` 與 `pop` 都同時修改 `freq`、`group` 與 `max_freq`，而 pop 的結果依賴全域的最大次數，所以這是一個天生需要序列化的結構，最直接是一把 mutex 包住兩個方法。依 val 分片（每片一個 FreqStack）會破壞語意，因為「全域次數最多」與「全域最靠近頂端」都需要跨片比較：可以在 pop 時鎖住所有分片、比較各片的 `(max_freq, 頂端時間戳記)` 再從勝出的那片彈出，但這等於回到全域鎖。面試時說出「這個語意本身要求全序，所以並行度有限」就是好的答案。

### 心得

關鍵突破是「每次 push 第 f 次，就在第 f 層留一份紀錄」，讓每個元素在每個次數層各有一個代表，彈出時其他層的紀錄自動就是正確的，不需要任何搬動。它和難題 1（LFU）、難題 2（All O(1)）共享同一個主題：次數每次只變 1，所以極值也只變 1，可以用分層取代排序；也和第 4 章「計數的計數」的想法相通。面試時用範例 1 畫出各層的 stack，說明「`group[f]` 是次數 ≥ f 的元素依達到第 f 次的時間排序」這條 invariant，正確性就幾乎不證自明；常見的錯誤是想在 pop 後把元素「搬」到較低的層，這說明還沒看出那一份紀錄早就在那裡。

## 難題 5｜1146. Snapshot Array｜Medium

### 題目

設計一個支援快照的陣列 `SnapshotArray`：

- `SnapshotArray(length)`：建立長度為 `length` 的陣列，所有元素初始為 0。
- `set(index, val)`：把 `index` 位置設成 `val`。
- `snap()`：拍一張快照，回傳快照編號 `snap_id`，等於之前呼叫 `snap()` 的總次數（第一張是 0）。
- `get(index, snap_id)`：回傳拍第 `snap_id` 張快照時，`index` 位置的值。

限制：`1 <= length <= 5 × 10⁴`，`0 <= val <= 10⁹`，`snap_id` 一定是已經拍過的快照，總呼叫次數最多 5 × 10⁴。

- 範例 1：`SnapshotArray(3)`、`set(0, 5)`、`snap()` → `0`、`set(0, 6)`、`get(0, 0)` → `5`（快照 0 拍下時位置 0 是 5，之後的修改不影響它）。
- 範例 2（邊界）：`SnapshotArray(2)`、`snap()` → `0`、`snap()` → `1`、`get(1, 1)` → `0`（從未設定過的位置是 0）。
- 範例 3（邊界）：同一張快照之前對同一位置設定多次：`set(0, 1)`、`set(0, 2)`、`set(0, 3)`、`snap()` → `0`、`get(0, 0)` → `3`，只有最後一次有效。

### 提示

> [!tip]- 提示 1
> 每次 `snap()` 複製整個陣列是 O(length)，最多 5 × 10⁴ 次 snap 乘上 5 × 10⁴ 的長度，時間與空間都不可行。大部分位置在兩次快照之間根本沒有改變。

> [!tip]- 提示 2
> 改成「每個位置記錄自己的修改歷史」：每次 `set` 記下 `(目前的快照編號, 值)`。注意「目前的快照編號」是**下一張要拍的快照**，因為這次修改會出現在那一張以及之後的快照中。

> [!tip]- 提示 3
> `get(index, snap_id)` 要找的是該位置歷史中「最後一筆編號 ≤ snap_id 的紀錄」，這是核心題 3 的 floor 查詢，用 `bisect_right`。同一張快照內的多次 `set` 只保留最後一筆（覆寫最後一筆紀錄），讓每個位置的編號嚴格遞增。

### 詳解

**為什麼直覺做法不夠**。每次 `snap` 用 `arr.copy()` 存一份完整陣列，`get` 是 O(1)，但 `snap` 是 O(length)，最壞 5 × 10⁴ 次 snap 共 2.5 × 10⁹ 次複製，記憶體也要存 2.5 × 10⁹ 個整數。反過來，若每次 `get` 都從頭重播所有 `set` 到該快照為止，`get` 又變成 O(操作數)。我們需要讓 `snap` 便宜（不碰任何資料）、`get` 也便宜。

**突破點：反轉儲存方向，從「每張快照存整個陣列」變成「每個位置存自己的版本」**。這是 copy-on-write（寫入時才複製）的精神：沒被修改的位置不需要任何新紀錄。`snap()` 只把全域的快照計數器加 1，O(1)。`set(index, val)` 在 `index` 的歷史中記錄 `(snap_id, val)`，這裡的 `snap_id` 是「目前的計數器值」，也就是下一張快照的編號，因為這次修改會在下一次 `snap()` 時被拍進去。這個標記方式讓「哪些修改屬於哪張快照」一目了然：編號 ≤ q 的紀錄都發生在拍第 q 張快照之前。

**查詢就是 floor**。`get(index, q)` 要的是「拍第 q 張快照時的值」，就是該位置歷史中編號 ≤ q 的最後一筆，若沒有這樣的紀錄則是初始值 0。因為計數器只增不減，每個位置的歷史依編號排序，所以用 `bisect_right(snaps, q) - 1` 找到它，O(log k)，k 是該位置的紀錄數。若同一張快照之前同一位置被設定多次，只有最後一次有意義，所以當最後一筆紀錄的編號等於目前計數器時直接覆寫，這讓每個位置的編號嚴格遞增，也讓紀錄數不超過 `min(set 次數, snap 次數 + 1)`。

**正確性**。invariant：對每個位置 i，`snaps[i]` 嚴格遞增，且對任意已拍的快照 q，拍下 q 時位置 i 的值等於「`snaps[i]` 中最後一個 ≤ q 的那筆紀錄的值」（不存在則為 0）。`set` 時目前計數器 c 大於所有已拍快照，所以修改只影響編號 ≥ c 的未來快照；`snap` 讓 c 加 1，把「編號 c 的紀錄」凍結成第 c 張快照的內容，之後對同位置的修改會用 c + 1 為編號，不會覆寫它。

```text
SnapshotArray(3)；每個位置的歷史寫成 [(編號, 值), …]；c 是目前的快照計數器

操作         c   位置 0 的歷史             位置 1 的歷史   回傳
set(0, 5)    0   [(0,5)]                   []
snap()       0→1                                            0
set(0, 6)    1   [(0,5) (1,6)]
set(0, 7)    1   [(0,5) (1,7)]             （同一張快照內覆寫）
snap()       1→2                                            1
set(1, 9)    2   [(0,5) (1,7)]             [(2,9)]
get(0, 0)        snaps=[0,1]：bisect_right(…, 0)=1 → idx 0 → 5
get(0, 1)        bisect_right(…, 1)=2 → idx 1 → 7
get(1, 1)        snaps=[2]：bisect_right(…, 1)=0 → idx −1 → 初始值 0
```

`get(1, 1)` 示範「修改發生在查詢的快照之後」：位置 1 的唯一紀錄編號是 2，代表它會出現在第 2 張以後的快照，而第 1 張快照拍下時它還是 0。`set(0, 7)` 示範同一張快照內的覆寫：它與 `(1, 6)` 屬於同一張未來快照，所以直接取代，歷史不會變長。

### 解法

```python
import random
from bisect import bisect_right


class SnapshotArray:
    def __init__(self, length: int):
        self.length = length
        self.snaps: dict[int, list[int]] = {}      # 只為被設定過的位置建立歷史
        self.vals: dict[int, list[int]] = {}
        self.snap_id = 0

    def set(self, index: int, val: int) -> None:
        s = self.snaps.setdefault(index, [])
        v = self.vals.setdefault(index, [])
        if s and s[-1] == self.snap_id:            # 同一張快照內再次設定：覆寫
            v[-1] = val
        else:
            s.append(self.snap_id)
            v.append(val)

    def snap(self) -> int:
        self.snap_id += 1
        return self.snap_id - 1

    def get(self, index: int, snap_id: int) -> int:
        s = self.snaps.get(index)
        if not s:
            return 0
        i = bisect_right(s, snap_id) - 1
        return self.vals[index][i] if i >= 0 else 0


sa = SnapshotArray(3)
sa.set(0, 5)
assert sa.snap() == 0
sa.set(0, 6)
assert sa.get(0, 0) == 5

sa = SnapshotArray(2)
assert sa.snap() == 0 and sa.snap() == 1 and sa.get(1, 1) == 0

sa = SnapshotArray(1)
sa.set(0, 1); sa.set(0, 2); sa.set(0, 3)
assert sa.snap() == 0 and sa.get(0, 0) == 3 and sa.snaps[0] == [0]

sa = SnapshotArray(3)
sa.set(0, 5); sa.snap(); sa.set(0, 6); sa.set(0, 7); sa.snap(); sa.set(1, 9)
assert (sa.get(0, 0), sa.get(0, 1), sa.get(1, 1)) == (5, 7, 0)

rng = random.Random(9)
n = 6
sa, cur, frozen = SnapshotArray(n), [0] * n, []
for _ in range(4000):
    r = rng.random()
    if r < 0.45:
        i, v = rng.randrange(n), rng.randint(0, 9)
        sa.set(i, v)
        cur[i] = v
    elif r < 0.6:
        assert sa.snap() == len(frozen)
        frozen.append(cur[:])                     # 暴力模型：整份複製
    elif frozen:
        i, q = rng.randrange(n), rng.randrange(len(frozen))
        assert sa.get(i, q) == frozen[q][i]
for i in sa.snaps:
    assert all(a < b for a, b in zip(sa.snaps[i], sa.snaps[i][1:]))
print("all tests passed")
```

### 複雜度與邊界

時間：建構 O(1)（用 dict 延遲建立每個位置的歷史，而不是預先建 length 個空 list；預先建立也只是 O(length)）；`set` 與 `snap` 都是 O(1)；`get` 是 O(log k)，k 是該位置的紀錄數。空間 O(實際紀錄數)，最多是 `set` 的次數，而且因為同一張快照內會覆寫，每個位置的紀錄數也不超過 snap 次數加 1。邊界：從未設定的位置回傳 0；查詢的快照早於該位置的第一筆紀錄時也回傳 0；`snap()` 回傳的是「拍之前的計數」；把值設回 0 也要記錄（不能當成「沒有紀錄」），否則之後的快照會讀到更早的非零值。

### Follow-up

> [!question]- F1. 如果還要查詢某張快照中一段區間 [l, r] 的總和呢？
> 每個位置各自的歷史無法快速回答區間問題，要改成持久化線段樹（persistent segment tree）：每張快照對應一個根節點，`set(index, val)` 只複製從根到該葉子路徑上的 O(log n) 個節點，其他子樹與上一版本共享；`snap()` 把目前的根存起來。查詢 `sum(l, r, snap_id)` 從該快照的根出發，和普通線段樹一樣 O(log n)。空間是 O(n + set 次數 × log n)。若同一張快照之前有多次 `set`，可以讓「目前版本」的節點在下一次 snap 前允許就地修改，避免為同一張快照重複複製路徑。

> [!question]- F2. 如果要刪除舊的快照以節省記憶體呢？
> 若只會刪除「最舊的若干張」（保留最近 W 張），記錄目前保留的最舊快照 `oldest`。每個位置的歷史中，編號 < `oldest` 的紀錄只需要保留最後一筆（它是 `oldest` 那張快照的值的來源），更早的都可以丟掉。可以在 `set` 碰到該位置時順便壓縮（lazy compaction），或由背景定期掃描。若可以刪除任意中間的快照，就要對每個位置找出「沒有任何保留的快照會讀到」的紀錄：一筆編號 a 的紀錄，在下一筆編號 b 之前若沒有任何保留的快照 q 滿足 a ≤ q < b，就可以刪除，判斷時用 binary search 在保留的快照集合中找，O(log S)。

> [!question]- F3. 如果要支援 restore(snap_id)，把目前狀態整個還原成某張快照呢？
> 在本題的「每個位置一條歷史」結構下，還原要對每個位置寫入一筆「回到舊值」的紀錄，O(length log k)，太慢。持久化結構可以讓還原變成 O(1)：用 F1 的持久化線段樹（或持久化陣列），每張快照就是一個根節點，`restore(q)` 只要把「目前版本的根」設成第 q 張快照的根，之後的修改從那個根複製路徑，舊的版本仍然保留。這也讓版本歷史從一條線變成一棵樹（從舊版本分支出新的修改），概念上和 git 的 commit 相同。代價是每次 `set` 與 `get` 都變成 O(log n)。

> [!question]- F4. 如果資料不是陣列而是 key-value 儲存，而且要做成分散式呢？
> 結構幾乎一樣：dict 的每個 key 存一條 `(版本, 值)` 的歷史，`snap` 增加全域版本號，`get(key, version)` 做 floor 查詢，這就是 MVCC（多版本並行控制）與快照隔離（snapshot isolation）的核心。分散式時，資料依 key 分散到多台機器，各台都保存自己 key 的版本歷史；困難在「一張快照」必須在所有機器上代表同一個時間點，所以快照編號要由一個協調者（或全域時鐘服務）統一發放，每次寫入都帶上目前的全域版本號。讀取舊快照只需要到各台機器做 floor 查詢，不需要協調，這是 MVCC 讓讀取不阻擋寫入的原因。

> [!question]- F5. 如果多個執行緒同時 set、snap、get 呢？
> 一個有用的觀察是：`get(index, q)` 只會讀到編號 ≤ q 的紀錄，而 q 一定小於目前計數器，這些紀錄在之後不會再被修改（覆寫只會發生在編號等於目前計數器的最後一筆）。所以讀取舊快照與寫入是天然不衝突的，只要「append 一筆紀錄」本身是原子的（例如每個位置存一個 tuple 串列而不是兩條平行串列）。真正需要同步的是 `set` 與 `snap` 之間：若 `set` 讀到計數器 c、在寫入之前另一個執行緒做了 `snap()`，這次修改會被標成 c，錯誤地出現在剛拍好的快照中。解法是讓 `snap` 取得寫鎖、`set` 取得讀鎖（多個 `set` 可並行，但要配合每個位置的細粒度鎖），確保每次 `set` 的「讀計數器＋寫紀錄」不會被 snap 切開。

### 心得

關鍵突破是把「每張快照存整個陣列」反轉成「每個位置存自己被改過的版本」，讓 `snap` 變成只加一個計數器，再用核心題 3 的 floor 查詢回答 `get`；另一個容易忽略的細節是 `set` 標記的是「下一張快照」的編號，並在同一張快照內覆寫。它和核心題 3（981）是同一個結構，只是「時間戳記」換成「快照編號」，也是 MVCC 與持久化資料結構的入門版。面試時先說清楚 `copy` 的 O(length) 為什麼不可行，再畫出每個位置的版本串列，用 `get(1, 1)` 這種「修改在查詢之後」的例子驗證邊界；若被追問區間查詢或還原，就接到 F1 與 F3 的持久化線段樹。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| hash ＋ 雙向 linked list | 依 key 查找，又要 O(1) 調整順序（最近使用、移到最前） | dict 存節點；sentinel 讓刪除不必特判；節點存 key 以便淘汰時刪 dict | 核心題 1（146）、難題 1（460）、難題 2（432 的桶串列） |
| hash ＋ array | 要 O(1) 隨機取樣或依索引存取，且會刪除 | 刪除時和最後一個交換再 pop，同步更新被搬動元素的索引 | 核心題 2（380）、381、710（排除清單以外的隨機取樣） |
| 陣列 ＋ 游標 | 歷史紀錄、undo／redo、回到第 k 步 | 用 `cur` 與 `last` 兩個指標，截斷用移動指標代替刪除 | 核心題 4（1472）、622 Design Circular Queue、362 Design Hit Counter（ring buffer） |
| 版本串列 ＋ binary search | 「時間 t 的值」「第 q 張快照的值」，寫入的版本號遞增 | 每個 key／位置一條遞增的版本串列，floor 查詢用 `bisect_right − 1`，同版本覆寫 | 核心題 3（981）、難題 5（1146） |
| 顯式 stack 的 iterator | 遞迴走訪但要逐個吐出結果、要求 lazy | stack 存「每層走到哪裡」，推進邏輯放在 `hasNext`，保持冪等 | 核心題 5（341）、173 BST Iterator、284 Peeking Iterator、281 Zigzag Iterator |
| 次數分桶＋極值只變 1 | 依頻率淘汰或彈出，頻率每次加減 1 | 次數 → 桶；只增時記 `min_freq`，可增可減時把桶串成有序雙向 list | 難題 1（460）、難題 2（432）、難題 4（895）、第 4 章難題 5（1224） |
| heap ＋ lazy deletion | 要取最大／最小，但刪除會發生在 heap 中間 | 唯一 id；刪除只做記號，取頂時清理；必要時定期重建控制記憶體 | 難題 3（716）、2349 Design a Number Container System、2034 Stock Price Fluctuation、第 14 章難題 2（480） |
| 每層彙總值 | 只在頂端增刪，要 O(1) 查彙總（最小、最大、和） | 每層存「到這層為止」的彙總值 | 第 10 章核心題 2（155）；刪除若發生在中間就改用上一列 |
| 持久化結構 | 舊版本要能查詢區間、或要從舊版本分支 | 路徑複製（path copying），每個版本一個根 | 難題 5 的 F1、F3；第 26 章的線段樹是基礎 |

**下限與上限**。最簡單的設計題只需要一個內建結構加上清楚的語意，例如 705／706 Design HashSet／HashMap 或 622 Design Circular Queue，考的是邊界處理與介面設計。中間層是兩個結構的標準組合（146、380、981、1472），難點在於知道該用哪一種組合，並且每次修改都同步更新兩邊。上限的題目難在三個地方：第一，**需要一個額外的觀察才能做到 O(1)**，例如「次數每次只變 1，所以極值只變 1、目標桶一定是鄰居」（460、432、895），沒有這個觀察就只能做到 O(log n)；第二，**兩種順序衝突**，必須讓兩個結構各管一種、用 lazy deletion 協調，並分析攤還成本與記憶體（716）；第三，**語意細節很多**，例如同次數的平手規則、同一張快照內的覆寫、`hasNext` 的冪等性，任何一個寫錯都會在隱藏測資失敗。

**與其他 pattern 的關係**。設計題幾乎都是其他章節零件的組合：雙向 linked list 的指標操作來自第 11 章；版本串列的 floor 查詢就是第 8 章的 binary search；heap 與 lazy deletion 來自第 14 章；每層彙總值來自第 10 章的 Min Stack；「計數的計數」來自第 4 章；需要區間查詢或任意刪除的有序結構時，就要用第 26 章的 Fenwick tree／segment tree，或第 13 章的 BST 與 Trie（例如 208 Implement Trie、211 Design Add and Search Words 也是設計題，只是主結構換成 Trie）。所以準備設計題最好的方法，是熟悉每個零件「擅長什麼、不擅長什麼」，再練習用 hash map 把它們接起來。

**容易混淆之處**。第一，「O(1)」通常指平均或攤還，dict 是平均 O(1)，lazy deletion 是攤還，回答時要說清楚是哪一種，被要求最差情況時要能換成真正刪除的版本（716 的 F3）。第二，LRU 與 LFU 的淘汰語意不同，LFU 同次數時才比最近使用，不要把兩者混成「依最後使用時間」。第三，「Max Stack」與「Min Stack」看似一樣，但 popMax 讓刪除發生在中間，彙總值技巧就失效。第四，Python 的 `OrderedDict` 與保留插入順序的 `dict` 可以省掉手寫 linked list，但面試官可能要求手寫，兩種都要會；Python 沒有內建平衡 BST，需要有序結構時要主動說明替代方案。

## 本章重點整理

- 設計題的第一步是列出每個操作與目標複雜度，再問「只用 dict 或只用 list 時，哪個操作會變慢」，那個瓶頸決定要加入什麼結構。
- 四個基本組合：hash ＋ 雙向 linked list（O(1) 調整順序）、hash ＋ array（O(1) 隨機取樣與交換刪除）、heap ＋ lazy deletion（取極值但會從中間刪除）、多層 hash（依次數或依版本分群）。
- Hash map 的 value 存「在另一個結構中的位置」（節點、索引、桶），這是 O(1) 的來源，也是 bug 的來源，位置一改變就要同步更新。
- 把 invariant 寫下來並逐個方法對照；測試時用暴力模型做差分測試，小值域的亂數操作最容易抓到不同步的 bug。
- LRU：dict ＋ 帶 sentinel 的雙向 linked list，節點要存 key；`put` 已存在的 key 不淘汰；`OrderedDict` 是內建的同等結構。
- RandomizedSet：刪除時先 pop 最後一個，被刪的不是最後一個才補洞並更新索引；有重複值時索引改成集合。
- 版本查詢（981、1146）：每個 key／位置一條遞增的版本串列，floor 查詢用 `bisect_right − 1`；快照的 `set` 標記的是下一張快照，同一張內覆寫。
- 瀏覽紀錄：陣列 ＋ `cur` ＋ `last`，截斷用移動 `last` 代替刪除，`back`／`forward` 用 `max`／`min` 一次跳到位。
- Iterator：顯式 stack 存每層進度，推進邏輯放在 `hasNext` 並保持冪等，空串列要在 `hasNext` 中跳過；空間 O(深度)。
- 次數每次只變 1 時，極值也只變 1：LFU 記 `min_freq`，FreqStack 記 `max_freq` 並讓每個元素在每層各有一份；可增可減時（All O(1)）把桶串成雙向 list。
- Max Stack：stack 管時間順序、heap 管值的順序，唯一 id 加 lazy deletion，`top` amortized O(1)、其他 amortized O(log n)；記憶體用定期重建控制。
- Follow-up 的 thread safety 要針對結構回答：LRU／LFU 的 `get` 會修改順序所以不能用讀鎖並行；lazy deletion 讓查詢也會修改結構；append-only 的版本串列讓舊版本讀取天然不衝突。
- 分散式版本通常是「依 key 分片 ＋ 各片本地結構」，全域精確的 LRU／LFU／最大值需要全序，代價太高，要說出近似或最終一致的取捨。
