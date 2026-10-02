---
chapter: 14
title: Heap：Top-K 與 K-way Merge
part: 2
---

# 第 14 章　Heap：Top-K 與 K-way Merge

> [!abstract] 本章地圖
> **一句話**：當你反覆只需要「目前最小（或最大）的那一個」，而資料一邊加入一邊被取走時，用 heap 把每次取極值的成本從 O(n) 降到 O(log n)；只關心前 k 名時，讓 heap 永遠只保留 k 個元素。
>
> **辨識訊號**：
> - 「第 k 大／第 k 小」「前 k 個最常出現／最近／最大」，而且 k 遠小於 n
> - 多條已排序的串列、檔案或資料流，要合併或找跨串列的最佳組合
> - 資料是串流，要隨時回報中位數、百分位數或目前前 k 名
> - 貪婪過程中每一步都要挑「目前可選的之中最好的那一個」，而可選集合會隨時間擴大
> - 「同一種東西要間隔一段時間才能再用」這類排程，每一步挑剩最多的
>
> **核心題**：215、347、973、621、767
>
> **難題**：295、480、502、632、857

## 14.1 這個 Pattern 解決什麼問題

先看一個小例子。伺服器每秒收到一筆請求延遲，你要隨時回報「到目前為止最慢的 10 筆」。最直接的做法是把所有延遲存起來，每次查詢時排序取前 10，單次查詢就要 O(n log n)；稍微聰明一點是維護一個長度 10 的排序陣列，每來一筆就插入到正確位置再丟掉最小的，單次 O(k)。當 k 是 10 時這已經夠快，但當 k 是 10⁵、資料是 10⁸ 筆時，每筆 O(k) 的插入就變成瓶頸。

heap（堆積，也叫 priority queue／優先佇列）正是為「反覆取極值」設計的資料結構。它是一棵用陣列存的完全二元樹，只保證「父節點 ≤ 子節點」，不保證整體有序；正因為要求比排序弱，它的插入與彈出都只要 O(log n)，看最小值只要 O(1)。回到延遲的例子：維護一個大小為 10 的 min-heap，堆頂就是「目前前 10 名裡最小的那個」，新資料只要比堆頂大就替換掉堆頂，每筆 O(log k)，記憶體只要 O(k)。

把這個想法推廣，本章所有題目都在回答同一個問題：**我每一步需要的極值是什麼？heap 裡應該放哪些候選？** Top-K 類題目（215、347、973）放的是「目前前 k 名」，堆頂是門檻；K-way merge 類題目（632）放的是「每條串列目前的最前面」，堆頂是全域最小；排程與貪婪類題目（621、767、502）放的是「此刻可以選的東西」，堆頂是最好的選擇；two heaps 類題目（295、480）用兩個 heap 夾住中間的分界，兩個堆頂就是中位數。

heap 的另一個價值是它和貪婪天生搭配。很多貪婪演算法的骨架是「每一步從目前可行的選項中挑最好的」，而「目前可行的選項」會隨著過程增加或減少；如果每一步都重新掃描所有選項，就是 O(n²)，用 heap 維護候選集合則是 O(n log n)。第 18 章的 Dijkstra、第 20 章難題的 630 與 871，本質上都是「heap 加貪婪」，本章的 502、857 則是這個組合最典型的面試版本。

## 14.2 辨識訊號

| 題目特徵 | 為什麼是 heap | 本章哪一題 |
|---|---|---|
| 「第 k 大／第 k 小」，n 很大或資料是串流 | 大小為 k 的 heap 的堆頂就是第 k 名，O(n log k) | 核心題 1（215） |
| 「出現次數前 k 名」「距離最近的 k 個」 | 先算出每個元素的分數，再對分數做 top-k | 核心題 2（347）、核心題 3（973） |
| 「同一種任務之間要冷卻」「相鄰不能相同」 | 每一步挑剩最多、且目前可用的那種，剩最多的最難安排 | 核心題 4（621）、核心題 5（767） |
| 串流中隨時要中位數 | 兩個 heap 分別存較小與較大的一半，堆頂夾住中位數 | 難題 1（295） |
| 視窗會移動、元素要被刪除，但仍要取極值或中位數 | heap 不支援任意刪除，用 lazy deletion（延遲刪除）在堆頂時才真正移除 | 難題 2（480） |
| 選項有「解鎖門檻」，解鎖後要挑價值最高的 | 依門檻排序逐步解鎖，解鎖的選項放進 max-heap | 難題 3（502） |
| k 條已排序串列，要合併或找「每條至少取一個」的最佳組合 | heap 放每條串列的目前元素，堆頂是全域最小 | 難題 4（632）、第 11 章難題 2（23） |
| 「選 k 個，成本 = 某個最大值 × 某個總和」 | 依其中一個維度排序後枚舉，另一個維度用 heap 保留最佳 k 個 | 難題 5（857） |

一個實用的反向檢查：如果你需要的不只是極值，而是「任意排名的元素」或「刪除任意元素後仍要有序走訪」，heap 就不夠了，要改用排序陣列加 bisect、平衡樹（Python 可用 `sortedcontainers.SortedList`，但面試平台不一定有）或第 26 章的 Fenwick tree。另一方面，如果整份資料一開始就給齊、只問一次第 k 名，quickselect 或直接排序可能更簡單，14.5 節會比較。

## 14.3 模板與原理：heapq、Top-K 與 K-way Merge

Python 的 `heapq` 模組把一般的 list 當成 min-heap 操作，只有幾個函式需要記：`heappush(h, x)` 與 `heappop(h)` 各 O(log n)；`h[0]` 是最小值，O(1)；`heapify(h)` 把任意 list 原地變成 heap，O(n)；`heapreplace(h, x)` 是「先 pop 再 push」、`heappushpop(h, x)` 是「先 push 再 pop」，各只做一次 O(log n) 的調整。本章只需要兩個模板：**大小為 k 的 heap 做 top-k**，以及 **每條串列放一個代表的 k-way merge（多路合併）**。

```python
import heapq
import random


def top_k_largest(nums, k):
    """回傳最大的 k 個數（由大到小）。維護大小為 k 的 min-heap。"""
    if k <= 0:
        return []
    heap = []
    for x in nums:
        if len(heap) < k:
            heapq.heappush(heap, x)
        elif x > heap[0]:              # 比門檻（目前第 k 大）還大，才換掉門檻
            heapq.heapreplace(heap, x)
    return sorted(heap, reverse=True)


def k_way_merge(lists):
    """合併多條已排序串列。heap 中每條串列最多只有一個代表。"""
    heap = [(lst[0], i, 0) for i, lst in enumerate(lists) if lst]
    heapq.heapify(heap)
    out = []
    while heap:
        val, i, j = heapq.heappop(heap)   # 全域最小值一定是某條串列的目前元素
        out.append(val)
        if j + 1 < len(lists[i]):
            heapq.heappush(heap, (lists[i][j + 1], i, j + 1))   # 補上同一條的下一個
    return out


assert top_k_largest([3, 1, 5, 12, 2, 11], 3) == [12, 11, 5]
assert top_k_largest([5, 5, 5], 2) == [5, 5]          # 重複值
assert top_k_largest([1, 2], 5) == [2, 1]             # k 比 n 大
assert top_k_largest([], 3) == []
assert top_k_largest([4, 1], 0) == []
assert k_way_merge([[1, 4, 7], [2, 5], [], [0, 9]]) == [0, 1, 2, 4, 5, 7, 9]
assert k_way_merge([]) == []
assert k_way_merge([[], []]) == []
for _ in range(300):
    arr = [random.randint(-20, 20) for _ in range(random.randint(0, 15))]
    k = random.randint(0, 17)
    assert top_k_largest(arr, k) == heapq.nlargest(k, arr)
    lists = [sorted(random.randint(-9, 9) for _ in range(random.randint(0, 5)))
             for _ in range(random.randint(0, 5))]
    assert k_way_merge(lists) == sorted(x for lst in lists for x in lst) == list(heapq.merge(*lists))
print("all tests passed")
```

**Heap 本身的 invariant**。陣列 `h` 滿足 `h[i] <= h[2i+1]` 且 `h[i] <= h[2i+2]`，也就是每個父節點不大於它的兩個子節點，所以 `h[0]` 一定是最小值。push 把新元素放到最後再往上「浮」，pop 把最後一個元素搬到根再往下「沉」，兩者都只走一條從根到葉的路徑，樹高 ⌊log₂ n⌋，所以是 O(log n)。`heapify` 是 O(n) 而不是 O(n log n)，因為大部分節點都在底層、往下沉的距離很短；面試時若要把整個陣列變成 heap，用 `heapify` 而不是 n 次 `heappush`。

**Top-K 模板的 invariant**。處理完前 i 個元素後，heap 裡恰好是這 i 個元素中最大的 min(i, k) 個，而堆頂 `heap[0]` 是其中最小的，也就是「目前第 k 大」，可以把它想成進入前 k 名的門檻。新元素 x 若不大於門檻，它不可能是前 k 名，直接丟掉；若大於門檻，門檻被擠出前 k 名，用 `heapreplace` 一次完成「丟掉門檻、放入 x」。這就是為什麼**找最大的 k 個要用 min-heap**：我們需要隨時知道前 k 名中最弱的那個，以便決定要不要換掉它。這個反直覺的方向是面試最常見的錯誤之一。

**K-way merge 模板的 invariant**。heap 中每條還沒用完的串列恰好有一個代表，就是它目前最前面、還沒輸出的元素。因為每條串列各自有序，所有還沒輸出的元素中最小的一定是某條串列的最前面，所以 heap 的堆頂就是全域最小值。彈出後補上同一條串列的下一個元素，invariant 繼續成立。heap 的大小始終不超過 k（串列數），所以總時間是 O(N log k)，N 是元素總數；若改成「每次掃 k 個串列頭找最小」則是 O(N·k)。

**每一行為什麼這樣寫**：

- tuple 放 `(值, 串列編號, 索引)`：`heapq` 比較 tuple 時先比第一欄，相同再比第二欄。把串列編號放在第二欄，可以保證值相同時不會去比較後面可能無法比較的東西（例如第 11 章的 `ListNode` 物件沒有定義 `<`，直接放進 tuple 會在值相同時丟出 `TypeError`）。
- max-heap 用取負數：`heapq` 只有 min-heap，要取最大值時存 `-x`，取出時再取負。字串或 tuple 不能取負，要改存 `(-分數, 字串)` 或自訂比較。Python 3.14 起 `heapq` 新增了 `heappush_max`、`heappop_max` 等函式，但面試平台不一定是新版，取負數最通用。
- `heapreplace` 而不是 `heappop` 加 `heappush`：效果相同，但只調整一次，常數約減半；它要求 heap 非空，所以前面先用 `len(heap) < k` 分流。
- 回傳前 `sorted(heap, reverse=True)`：heap 本身不是排序好的，`heap[1]` 不一定是第二小；需要有序輸出時要額外排序，O(k log k)。

**`heapq.nlargest`、`nsmallest` 與 `merge`**。標準函式庫已經提供 `heapq.nlargest(k, iterable, key=…)`、`nsmallest` 與 `merge(*iterables)`，內部就是上面兩個模板。面試時可以用，但要能說出它們的複雜度與原理；遇到要在過程中加條件（例如 632 要同時追蹤最大值）時，仍然得自己寫。

## 14.4 進階形態：Two Heaps、Lazy Deletion 與「排序 + Heap」

**Two heaps（雙堆）**。中位數把資料分成「較小的一半」和「較大的一半」。用一個 max-heap 存較小的一半、一個 min-heap 存較大的一半，並維持兩個 invariant：左邊每個元素 ≤ 右邊每個元素（等價於左堆頂 ≤ 右堆頂），以及兩邊的大小差不超過 1。這樣中位數只取決於兩個堆頂，O(1) 就能回答，每次插入 O(log n)。把「一半」換成任意比例，就能維護任意百分位數。難題 1（295）是標準形，難題 2（480）在它上面加了刪除。

**Lazy deletion（延遲刪除）**。heap 只能高效地刪除堆頂，刪除中間的元素需要先找到它，O(n)。延遲刪除的做法是：要刪除 x 時不真的去找它，只在一個 hash map 裡記下「x 欠刪一次」，並把邏輯上的大小減一；等到 x 浮到堆頂、可能影響答案時，才把它真正彈出。因為每個元素最多被真正彈出一次，總成本仍是 O(n log n)。代價是 heap 的實際長度可能比邏輯大小大，所以**大小判斷一律用自己維護的計數器，不能用 `len(heap)`**。

```text
lazy deletion：視窗中的 -3 已經離開，但它不在堆頂，先不動它
low（max-heap）實際內容： 5  3  -3      delayed = {-3: 1}
邏輯內容：               5  3          low_size = 2
-3 沉在底部，不會影響堆頂 5；等它浮到堆頂時，prune 會把它彈掉
```

**排序 + heap**。很多題目的選項有兩個維度，例如 502 的（門檻、利潤）、857 的（每單位品質要價、品質）。常見解法是：依第一個維度排序，掃描時讓選項逐步「解鎖」；解鎖的選項放進以第二個維度為鍵的 heap，每一步從 heap 取最好的，或用 heap 把不夠好的踢掉。排序負責處理「什麼時候可以選」，heap 負責處理「可以選的之中挑誰」，兩者各 O(n log n)。這個組合在第 20 章難題 3（630）與難題 4（871）會再出現。

## 14.5 Heap、排序、Quickselect、Bucket：怎麼選

Top-K 類問題至少有四種做法，面試官很常要你比較。下表的 n 是元素數、k 是要的名次、V 是值域大小：

| 做法 | 時間 | 額外空間 | 什麼時候用 |
|---|---|---|---|
| 全部排序 | O(n log n) | O(n) 或 O(1) | 最簡單；n 不大或需要完整排序結果 |
| 大小為 k 的 heap | O(n log k) | O(k) | 串流、記憶體只放得下 k 個、k 遠小於 n |
| heapify 後 pop k 次 | O(n + k log n) | O(n) | 資料一次給齊，k 也不小 |
| Quickselect（快速選擇） | 平均 O(n)，最差 O(n²) | O(1)（原地） | 資料一次給齊、要最快的期望時間、可以修改輸入 |
| Bucket／counting | O(n + V) | O(V) | 值域或「分數」範圍小，例如頻率 ≤ n、值在 ±10⁴ |

quickselect 是 quicksort 的「只遞迴一邊」版本：選一個 pivot，把陣列切成「< pivot」「= pivot」「> pivot」三段，看第 k 名落在哪一段，只往那一段繼續。每一輪期望丟掉一半，總工作量 n + n/2 + n/4 + … = O(n)。pivot 必須隨機選，否則對已排序的輸入會退化成 O(n²)；切分要用三路（three-way partition），否則全部相同的輸入也會退化。理論上 median of medians 能保證最差 O(n)，但常數很大，面試中說出名字與概念即可。

面試時的建議順序是：先說排序作為基準，再提出大小為 k 的 heap（最穩定、最容易寫對、也能處理串流），最後在面試官追問「能不能更快」時提 quickselect 或 bucket。不要一開口就寫 quickselect，它容易寫錯，而且面試官通常更在意你是否理解 heap 的 O(n log k) 和 quickselect 的 O(n) 期望時間各自的前提。

## 14.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 找最大的 k 個卻用 max-heap 存全部 | 空間 O(n)、時間 O(n log n)，失去 top-k 的意義 | 最大的 k 個用大小為 k 的 **min-heap**，堆頂是門檻 |
| max-heap 忘記取負數，或取出時忘記還原 | 回傳的是最小的 k 個，或答案變號 | 存入 `-x`，取出時立刻 `-heappop(h)`；變數名寫清楚是哪種 heap |
| tuple 第一欄相同時比較到不可比較的物件 | `TypeError: '<' not supported` | tuple 中間放一個唯一的整數（索引或計數器）當 tie-breaker |
| 以為 `heap[1]`、`heap[2]` 是第二、第三小 | 輸出順序錯，或取到錯的第二名 | heap 只保證堆頂；要第二小就 pop 一次，要有序結果就排序 |
| 用 `len(heap)` 判斷 lazy deletion 後的大小 | 兩堆失衡，中位數錯 | 自己維護有效大小計數器，刪除時立即更新 |
| 延遲刪除後沒有清理堆頂 | 堆頂是已經離開視窗的元素，答案錯 | 每次可能讓已刪元素浮到堆頂的操作（pop、平衡）之後都呼叫 prune |
| `heapreplace` 用在空 heap | `IndexError` | 先用 `len(heap) < k` 分流，滿了才 replace |
| quickselect 固定選第一個當 pivot、或只做兩路切分 | 已排序或全相同的輸入退化成 O(n²)、超時 | 隨機 pivot 加三路切分 |
| k-way merge 一開始把空串列放進 heap | `IndexError` 或放入無意義的值 | 建 heap 時跳過空串列 |
| 浮點數當鍵造成誤差（857 的比例） | 比例相同的工人排序不穩定，邊界案例答案錯一點 | 只用浮點排序與計算最終成本即可；需要精確比較時用交叉相乘 `w1 * q2 < w2 * q1` |

## 核心題 1｜215. Kth Largest Element in an Array｜Medium

### 題目

給一個整數陣列 `nums` 和整數 k，回傳陣列中第 k 大的元素。這裡的「第 k 大」是指把陣列由大到小排序後的第 k 個，**重複的值各自算一次**，不是第 k 個不同的值。題目希望你不要直接排序。限制：`1 <= k <= len(nums) <= 10⁵`，元素在 `-10⁴` 到 `10⁴` 之間。

- 範例 1：`nums = [3, 2, 1, 5, 6, 4]`、`k = 2`，由大到小是 `6, 5, 4, 3, 2, 1`，回傳 `5`。
- 範例 2：`nums = [3, 2, 3, 1, 2, 4, 5, 5, 6]`、`k = 4`，由大到小是 `6, 5, 5, 4, …`，回傳 `4`（兩個 5 各算一次）。
- 範例 3（邊界）：`nums = [1]`、`k = 1`，回傳 `1`。
- 範例 4（邊界）：`nums = [2, 2, 2]`、`k = 2`，回傳 `2`；`nums = [-1, -5, 3]`、`k = 3`，回傳最小值 `-5`。

### 思路

暴力解是排序後取 `nums[n - k]`，O(n log n)。這在面試中是合理的起點，但它做了太多事：我們只需要第 k 名，卻把所有 n 個元素的相對順序都排好了。瓶頸在於「排出完整順序」的成本，而題目真正需要的只是「前 k 名是誰」或「第 k 名在哪裡」。

第一個改進是 14.3 節的 top-k 模板：維護一個大小為 k 的 min-heap，invariant 是「heap 裡是目前看過的元素中最大的 k 個」。堆頂是這 k 個中最小的，也就是目前的第 k 大；新元素比堆頂大，就把堆頂換掉，否則直接丟棄。掃完整個陣列後，堆頂就是答案。每個元素最多一次 O(log k) 的操作，總共 O(n log k)，額外空間 O(k)。當 k 很小時這幾乎是線性的，而且它只需要從頭到尾看一次資料，對串流也成立。

第二個改進是 quickselect：隨機選一個 pivot，三路切分成「< pivot」「= pivot」「> pivot」三段。第 k 大在排序後的索引是 `n - k`，看這個索引落在哪一段：落在中段就是 pivot 本身，落在左段或右段就只往那一段繼續，另一段整個丟掉。期望每輪丟掉一半，總時間期望 O(n)。三路切分很重要：若陣列全是同一個值，兩路切分每次只能排除一個元素，退化成 O(n²)；三路切分一輪就能把所有相同值歸到中段並直接結束。

第三個做法利用這題的特殊限制：值域只有 `[-10⁴, 10⁴]`，約 2 × 10⁴ 種可能。開一個計數陣列，從最大的值往下累加次數，累加到 ≥ k 的那個值就是答案，O(n + V)。這不是一般解，但面試官常拿它來確認你會不會「從限制推做法」（第 3 章）。

```text
nums = [3, 2, 1, 5, 6, 4]，k = 2，min-heap 最多 2 個（堆頂 = 目前第 2 大 = 門檻）

讀入  heap（排序後顯示）  門檻  動作
 3    [3]                 -     未滿，push
 2    [2, 3]              2     未滿，push；滿了，門檻 = 2
 1    [2, 3]              2     1 <= 2，進不了前 2 名，丟掉
 5    [3, 5]              3     5 > 2，replace：踢掉 2
 6    [5, 6]              5     6 > 3，replace：踢掉 3
 4    [5, 6]              5     4 <= 5，丟掉
結束  堆頂 = 5 → 第 2 大是 5

quickselect 一輪（target 索引 = n - k = 4，假設隨機選到 pivot = 4）
三路切分後： [3 2 1] [4] [5 6]
             < 4     = 4  > 4
索引：        0..2    3    4..5      target 4 落在 > 4 段 → 只在 [5, 6] 中繼續
```

heap 的過程中，門檻只會往上升：一開始是 2，接著 3、5。每個被丟掉的元素（1 和 4）在被丟掉的那一刻都已經不可能是前 2 名，因為已經有 2 個比它大的元素在 heap 裡。quickselect 的那一輪則一次排除了 4 個元素，只留下 `[5, 6]` 兩個，下一輪在其中找排序後的索引 4，也就是 5。

### 解法

```python
import heapq
import random


def find_kth_largest(nums: list[int], k: int) -> int:
    heap: list[int] = []                 # min-heap，最多 k 個：目前看過的最大 k 個數
    for x in nums:
        if len(heap) < k:
            heapq.heappush(heap, x)
        elif x > heap[0]:                # 比第 k 大還大，才有資格進前 k 名
            heapq.heapreplace(heap, x)   # 先 pop 再 push，一次 O(log k)
    return heap[0]


def find_kth_largest_quickselect(nums: list[int], k: int) -> int:
    arr = list(nums)
    target = len(arr) - k                # 第 k 大 = 排序後索引 n - k
    lo, hi = 0, len(arr) - 1
    while True:
        pivot = arr[random.randint(lo, hi)]
        # 三路切分：[lo, lt) < pivot，[lt, i) == pivot，(gt, hi] > pivot
        lt, i, gt = lo, lo, hi
        while i <= gt:
            if arr[i] < pivot:
                arr[lt], arr[i] = arr[i], arr[lt]
                lt += 1
                i += 1
            elif arr[i] > pivot:
                arr[i], arr[gt] = arr[gt], arr[i]
                gt -= 1
            else:
                i += 1
        if target < lt:
            hi = lt - 1
        elif target > gt:
            lo = gt + 1
        else:
            return pivot


def find_kth_largest_counting(nums: list[int], k: int) -> int:
    lo = min(nums)
    count = [0] * (max(nums) - lo + 1)
    for x in nums:
        count[x - lo] += 1
    for v in range(len(count) - 1, -1, -1):  # 從最大值往下數
        k -= count[v]
        if k <= 0:
            return v + lo


for f in (find_kth_largest, find_kth_largest_quickselect, find_kth_largest_counting):
    assert f([3, 2, 1, 5, 6, 4], 2) == 5
    assert f([3, 2, 3, 1, 2, 4, 5, 5, 6], 4) == 4
    assert f([1], 1) == 1
    assert f([2, 2, 2], 2) == 2
    assert f([-1, -5, 3], 3) == -5
assert find_kth_largest_quickselect([7] * 100000, 50000) == 7   # 全部相同也不會退化
for _ in range(500):
    arr = [random.randint(-10, 10) for _ in range(random.randint(1, 12))]
    k = random.randint(1, len(arr))
    expect = sorted(arr, reverse=True)[k - 1]
    assert find_kth_largest(arr, k) == expect
    assert find_kth_largest_quickselect(arr, k) == expect
    assert find_kth_largest_counting(arr, k) == expect
print("all tests passed")
```

### 複雜度與邊界

heap 版時間 O(n log k)、空間 O(k)；quickselect 期望時間 O(n)、最差 O(n²)（機率極低），額外空間 O(1)，但會修改陣列，所以上面先複製一份（O(n)）；counting 版 O(n + V)，V 是值域大小，這題 V ≈ 2 × 10⁴。邊界情況：k = n 時答案是最小值，heap 版會把所有元素都留下；k = 1 時 heap 只有一個元素，等於掃描最大值；重複值要各自計算，所以 heap 版的條件是 `x > heap[0]` 而不是去重；全部相同時三路切分第一輪就結束；負數不影響 heap 與 quickselect，counting 版用 `x - lo` 平移索引。

### Follow-up

> [!question]- F1. 如果資料是串流，要隨時回答「目前第 k 大」呢（703. Kth Largest Element in a Stream）？
> 直接沿用 heap 版：類別中保存一個大小為 k 的 min-heap，每次 `add(x)` 時，未滿就 push，滿了且 x 大於堆頂就 `heapreplace`，然後回傳 `heap[0]`。每次加入 O(log k)、查詢 O(1)，空間 O(k)，與已經看過多少資料無關。quickselect 在這裡完全不適用，因為它需要整份資料、每次查詢都要重做 O(n)。這是 heap 版在面試中最強的論點：它天生是線上（online）演算法。

> [!question]- F2. 如果 k 很接近 n（例如 k = n − 3）呢？
> 第 k 大等於第 n − k + 1 小。當 k > n/2 時，改成維護大小為 n − k + 1 的 **max-heap**（存負數）找第 n − k + 1 小，heap 大小變成 min(k, n − k + 1)，時間 O(n log min(k, n − k + 1))。例如 n = 10⁵、k = n − 3 時，heap 只要 4 個元素，而不是 99997 個。quickselect 不受 k 影響，期望都是 O(n)。

> [!question]- F3. quickselect 的最差情況能不能保證 O(n)？
> 可以用 median of medians：把陣列每 5 個分一組，取每組中位數，再遞迴地取這些中位數的中位數當 pivot。可以證明這個 pivot 至少大於約 30% 的元素、也至少小於約 30%，所以每輪至少丟掉 30%，遞迴式 T(n) ≤ T(n/5) + T(7n/10) + O(n) 解出 O(n)。實務上常數很大，C++ 的 `nth_element` 用的是 introselect：先跑隨機 quickselect，遞迴太深時才切換到保證線性的方法。面試中說出這些名字與遞迴式，比真的寫出來更重要。

> [!question]- F4. 如果資料大到放不進一台機器的記憶體，分散在很多台機器上呢？
> 若 k 小：每台機器各自算出本地的前 k 大（heap，O(本地資料量 · log k)），把每台的 k 個送到協調者，協調者再對 m·k 個數取前 k 大，總傳輸量 O(m·k)。正確性來自「全域前 k 名一定是某台機器的本地前 k 名」。若 k 很大：改用第 8 章的值域二分，每輪廣播一個候選值 x，各機器回報「> x 的有幾個」，協調者加總後決定往哪邊縮，約 log₂ V 輪、每輪傳輸 O(m)，這題 V ≈ 2 × 10⁴ 只要 15 輪。

> [!question]- F5. 如果要的是第 k 大的「不同」值呢？
> 先去重再做同樣的事：`set(nums)` 是 O(n)，再對去重後的 d 個值用 heap（O(d log k)）或 quickselect（期望 O(d)）。要注意 k 可能大於不同值的個數 d，此時要回報不存在（例如 414. Third Maximum Number 規定不存在時回傳最大值）。heap 版也可以不先去重，只要在 push 前檢查 x 是否已在 heap 中，但那需要額外的 set 來 O(1) 判斷，反而更複雜。

## 核心題 2｜347. Top K Frequent Elements｜Medium

### 題目

給一個整數陣列 `nums` 和整數 k，回傳出現次數最多的 k 個元素，順序不限。題目保證答案唯一，也就是第 k 名和第 k + 1 名的次數不會相同。要求時間複雜度優於 O(n log n)。限制：`1 <= len(nums) <= 10⁵`，元素在 `-10⁴` 到 `10⁴` 之間，k 介於 1 到「不同元素的個數」之間。

- 範例 1：`nums = [1, 1, 1, 2, 2, 3]`、`k = 2`，1 出現 3 次、2 出現 2 次、3 出現 1 次，回傳 `[1, 2]`。
- 範例 2：`nums = [4, 4, -1, -1, 7]`、`k = 2`，回傳 `[4, -1]`（順序不限，`[-1, 4]` 也對）。
- 範例 3（邊界）：`nums = [1]`、`k = 1`，回傳 `[1]`。
- 範例 4（邊界）：`nums = [5, 6, 7]`、`k = 3`，每個都出現一次，k 等於不同元素個數，三個全部回傳。

### 思路

這題分成兩步：先算出每個元素的頻率，再從頻率中取前 k 名。第一步用 `Counter`（第 4 章）O(n) 完成，得到 d 個（值, 次數）。第二步的暴力解是把 d 個依次數排序取前 k，O(d log d)，最差 d = n，就是 O(n log n)，剛好是題目想要你超越的界。

改進一：對 d 個頻率做 14.3 節的 top-k。維護一個大小為 k、以次數為鍵的 min-heap，堆頂是「目前前 k 名中次數最少的」，新元素的次數比它多才換進來。時間 O(n + d log k)。當 k 遠小於 d 時明顯更快；當 k 接近 d 時，可以反過來找次數最少的 d − k 個並排除，讓 heap 大小變成 min(k, d − k)。

改進二是這題的關鍵觀察：**次數是 1 到 n 之間的整數**，值域被 n 限制住了。所以可以用 bucket sort（桶排序）：開 n + 1 個桶，第 c 個桶放「恰好出現 c 次的元素」，然後從 c = n 往下掃，依序收集，收集到 k 個就停。建桶 O(d)，掃描 O(n)，總共 O(n)。這是本題唯一真正的線性解，也是面試官期待的最佳答案；heap 版則是更通用、能延伸到串流的答案，兩者都要能說。

```text
nums = [1, 1, 1, 2, 2, 3]，k = 2
第一步 Counter：{1: 3, 2: 2, 3: 1}

做法一：大小 2 的 min-heap，元素是 (次數, 值)
讀入       heap（排序後顯示）     動作
(3, 1)     [(3, 1)]               未滿，push
(2, 2)     [(2, 2), (3, 1)]       未滿，push；門檻 = 次數 2
(1, 3)     [(2, 2), (3, 1)]       1 <= 2，丟掉
結果 [2, 1]（順序不限）

做法二：bucket，索引 = 次數（0..n = 0..6）
bucket:  0   1    2    3    4   5   6
         []  [3]  [2]  [1]  []  []  []
從 6 往下掃：6、5、4 空；3 → 收 1；2 → 收 2，已滿 k = 2，停
結果 [1, 2]
```

heap 做法中，(1, 3) 因為次數 1 不超過門檻 2 而被丟掉，這一刻已經有兩個元素次數比它多，它不可能是前 2 名。bucket 做法中，桶的索引本身就是排序鍵，從高往低掃就等於依次數由大到小走訪，完全不需要比較，所以能突破比較排序的 O(n log n) 下限。

### 解法

```python
import heapq
import random
from collections import Counter


def top_k_frequent(nums: list[int], k: int) -> list[int]:
    freq = Counter(nums)
    heap: list[tuple[int, int]] = []          # (次數, 值) 的 min-heap，最多 k 個
    for val, c in freq.items():
        if len(heap) < k:
            heapq.heappush(heap, (c, val))
        elif c > heap[0][0]:
            heapq.heapreplace(heap, (c, val))
    return [val for _, val in heap]


def top_k_frequent_bucket(nums: list[int], k: int) -> list[int]:
    freq = Counter(nums)
    buckets: list[list[int]] = [[] for _ in range(len(nums) + 1)]
    for val, c in freq.items():
        buckets[c].append(val)                # 次數最多是 n，所以 n + 1 個桶
    out: list[int] = []
    for c in range(len(nums), 0, -1):
        for val in buckets[c]:
            out.append(val)
            if len(out) == k:
                return out
    return out


for f in (top_k_frequent, top_k_frequent_bucket):
    assert sorted(f([1, 1, 1, 2, 2, 3], 2)) == [1, 2]
    assert f([1], 1) == [1]
    assert sorted(f([4, 4, -1, -1, 7], 2)) == [-1, 4]
    assert sorted(f([5, 6, 7], 3)) == [5, 6, 7]
for _ in range(500):
    arr = [random.randint(-5, 5) for _ in range(random.randint(1, 20))]
    cnt = sorted(Counter(arr).values(), reverse=True)
    k = random.randint(1, len(cnt))
    if k < len(cnt) and cnt[k - 1] == cnt[k]:
        continue                              # 答案不唯一，題目保證不會發生
    freq = Counter(arr)
    expect = sorted(sorted(freq, key=lambda v: -freq[v])[:k])
    assert sorted(top_k_frequent(arr, k)) == expect == sorted(top_k_frequent_bucket(arr, k))
print("all tests passed")
```

### 複雜度與邊界

heap 版時間 O(n + d log k)，d 是不同元素個數，空間 O(d + k)；bucket 版時間 O(n)，空間 O(n)（n + 1 個桶加上 Counter）。邊界情況：k 等於 d 時兩個版本都會回傳全部元素；所有元素都相同時 d = 1，bucket 只有第 n 個非空；負數只是 Counter 的鍵，不影響；heap 的 tuple 是 `(次數, 值)`，次數相同時會比較值，整數可以比較所以沒問題，若元素是不可比較的物件就要加 tie-breaker。題目保證答案唯一，所以門檻上的平手不必處理；若不保證，見 F1。

### Follow-up

> [!question]- F1. 如果次數相同時要依字典序決定，並且輸出要依次數由高到低排序呢（692. Top K Frequent Words）？
> 排序鍵變成 `(-次數, 字串)`，越小越優先。最簡單的是 `heapq.nsmallest(k, freq, key=lambda w: (-freq[w], w))`，O(d log k)，回傳就已經有序。若要自己維護大小為 k 的 heap，堆頂必須是「最差的」，也就是次數最少、次數相同時字典序**最大**的；字串不能取負，要包一個自訂 `__lt__` 的類別把字串比較反過來。另一個選擇是 heapify 全部 d 個 `(-次數, 字串)` 再 pop k 次，O(d + k log d)，寫起來最不容易錯。

> [!question]- F2. 如果資料是無限串流、記憶體不夠存下所有不同元素呢？
> 精確答案需要 O(d) 記憶體，無法避免，所以要改用近似演算法。Misra–Gries（heavy hitters）只保留 k 個計數器：新元素若已有計數器就加一，有空位就佔一個，否則所有計數器同時減一、歸零的釋放；任何出現次數超過 n/(k + 1) 的元素保證會留在計數器中，估計值的誤差不超過 n/(k + 1)。Count-Min Sketch 則用幾個雜湊陣列估計任意元素的次數，再配合一個大小 k 的 heap 追蹤目前估計值最高的元素。面試中說出「精確需要 O(d)，近似可以 O(k)」以及其中一種的機制即可。

> [!question]- F3. 如果資料分散在很多台機器上呢？「每台取本地前 k 再合併」對嗎？
> 不對。同一個值的出現次數可能分散在各台：某值在每台都只排第 k + 1，本地都被淘汰，但加總後可能是全域第一。正確做法是先依值做雜湊分區（shuffle），讓同一個值的所有出現都送到同一台，每台計算自己負責的值的完整次數，這時「本地前 k」才有意義，最後協調者合併 m 份大小 k 的結果取前 k，O(m·k log k)。這是 MapReduce 的標準 word count 加 top-k 流程，也是面試官很愛用來檢查你是否真的理解 top-k 正確性前提的追問。

> [!question]- F4. 如果元素會被加入也會被移除，要隨時查詢目前的前 k 名呢？
> heap 不支援「某個元素的次數改變」，因為要先找到它。做法一：用 hash map 記錄次數，另用一個有序結構存 `(次數, 值)`（例如 `SortedList`），次數改變時刪除舊 pair、插入新 pair，各 O(log d)，查詢前 k 名 O(k)。做法二：若每次只加一或減一，可以用第 27 章難題 2（432. All O(1) Data Structure）的「次數桶的雙向鏈結串列」，每次更新 O(1)，查前 k 名從最高的桶往下走 O(k)。

## 核心題 3｜973. K Closest Points to Origin｜Medium

### 題目

給平面上 n 個點 `points[i] = [x, y]` 和整數 k，回傳離原點 `(0, 0)` 最近的 k 個點，距離是歐幾里得距離 √(x² + y²)，回傳順序不限。題目保證答案唯一（第 k 近和第 k + 1 近的距離不同，除非 k = n）。限制：`1 <= k <= n <= 10⁴`，座標在 `-10⁴` 到 `10⁴` 之間。

- 範例 1：`points = [[1, 3], [-2, 2]]`、`k = 1`，兩點的距離平方是 10 和 8，回傳 `[[-2, 2]]`。
- 範例 2：`points = [[3, 3], [5, -1], [-2, 4]]`、`k = 2`，距離平方是 18、26、20，回傳 `[[3, 3], [-2, 4]]`。
- 範例 3（邊界）：`points = [[0, 1]]`、`k = 1`，回傳 `[[0, 1]]`。
- 範例 4（邊界）：`k = n` 時回傳全部點。

### 思路

暴力解是依距離排序取前 k，O(n log n)。和核心題 1 一樣，排序做了多餘的工作。這題和 215 的差別只有兩點：排序鍵不是元素本身，而是由座標算出來的距離；方向是「最近」也就是最小的 k 個。所以這是 top-k 模板換了鍵與方向的版本，重點在於把方向想清楚。

找**最小**的 k 個，要用大小為 k 的 **max-heap**：堆頂是目前選中的 k 個點裡最遠的那個，它是門檻。新點比門檻近，就把最遠的換掉；否則它不可能是前 k 近，丟掉。`heapq` 只有 min-heap，所以存 `(-距離平方, 索引)`，堆頂的 `-heap[0][0]` 就是目前最遠的距離。時間 O(n log k)，空間 O(k)。

兩個細節。第一，**比較距離平方就好**，不需要開根號：平方根是單調函數，大小關係不變，而整數平方完全沒有浮點誤差；座標到 10⁴ 時平方和最多 2 × 10⁸，Python 不會溢位，Java 用 `int` 也還夠。第二，tuple 第二欄放索引而不是座標 list，比較到第二欄時整數一定可以比較，也避免把可變的 list 放進 heap。

和核心題 1 一樣，這題也能用 quickselect 期望 O(n)：以距離為鍵三路切分，找讓「前 k 個位置」都放好的切分點，之後直接回傳陣列前 k 個（這 k 個本身不必有序）。面試中先寫 heap 版，再說 quickselect 是期望線性但會修改輸入、最差 O(n²) 的替代方案。

```text
points = [[3, 3], [5, -1], [-2, 4]]，k = 2
距離平方 d：      18       26       20
max-heap 存 (-d, 索引)，堆頂是目前最遠的（門檻）

讀入            heap（依距離顯示）   門檻   動作
[3, 3]   d=18   {18}                 -      未滿，push
[5, -1]  d=26   {18, 26}             26     未滿，push；滿了，門檻 = 最遠的 26
[-2, 4]  d=20   {18, 20}             20     20 < 26，replace：踢掉 26
結束 → 回傳索引 0、2 的點：[3, 3]、[-2, 4]
```

第三個點的距離 20 比門檻 26 小，代表它比目前選中的最遠點還近，於是把 26 踢出去，新的門檻變成 20。若再來一個距離 22 的點，22 > 20，它就進不來。整個過程中門檻只會變小，和核心題 1 門檻只會變大正好對稱。

### 解法

```python
import heapq
import random


def k_closest(points: list[list[int]], k: int) -> list[list[int]]:
    heap: list[tuple[int, int]] = []        # (-距離平方, 索引)：max-heap，堆頂是目前最遠的
    for i, (x, y) in enumerate(points):
        d = x * x + y * y
        if len(heap) < k:
            heapq.heappush(heap, (-d, i))
        elif d < -heap[0][0]:               # 比目前第 k 近的還近，才換掉堆頂
            heapq.heapreplace(heap, (-d, i))
    return [points[i] for _, i in heap]


def k_closest_quickselect(points: list[list[int]], k: int) -> list[list[int]]:
    pts = list(points)
    dist = lambda p: p[0] * p[0] + p[1] * p[1]
    lo, hi = 0, len(pts) - 1
    while lo < hi:
        pivot = dist(pts[random.randint(lo, hi)])
        lt, i, gt = lo, lo, hi
        while i <= gt:
            d = dist(pts[i])
            if d < pivot:
                pts[lt], pts[i] = pts[i], pts[lt]
                lt += 1
                i += 1
            elif d > pivot:
                pts[i], pts[gt] = pts[gt], pts[i]
                gt -= 1
            else:
                i += 1
        if k <= lt:              # 前 k 個全在 < pivot 區
            hi = lt - 1
        elif k > gt + 1:         # 前 k 個還要包含 > pivot 區的一部分
            lo = gt + 1
        else:                    # 第 k 個落在 == pivot 區，前 k 個已就位
            break
    return pts[:k]


def norm(pts):
    return sorted(map(tuple, pts))


for f in (k_closest, k_closest_quickselect):
    assert norm(f([[1, 3], [-2, 2]], 1)) == [(-2, 2)]
    assert norm(f([[3, 3], [5, -1], [-2, 4]], 2)) == [(-2, 4), (3, 3)]
    assert norm(f([[0, 1]], 1)) == [(0, 1)]
    assert norm(f([[1, 1], [2, 2], [3, 3]], 3)) == [(1, 1), (2, 2), (3, 3)]
for _ in range(500):
    pts = [[random.randint(-6, 6), random.randint(-6, 6)] for _ in range(random.randint(1, 10))]
    k = random.randint(1, len(pts))
    ds = sorted(x * x + y * y for x, y in pts)
    for f in (k_closest, k_closest_quickselect):
        got = f(pts, k)
        assert len(got) == k
        assert sorted(x * x + y * y for x, y in got) == ds[:k]   # 距離多重集合必須相同
print("all tests passed")
```

### 複雜度與邊界

heap 版時間 O(n log k)，空間 O(k)；quickselect 期望 O(n)、最差 O(n²)，額外空間 O(n)（複製輸入；若允許修改輸入則 O(1)）。邊界情況：k = n 時 heap 版保留全部點、quickselect 的迴圈條件 `lo < hi` 很快結束，兩者都回傳全部；多個點距離相同時（例如 `[1, 0]` 與 `[0, 1]`），只要它們不落在第 k 名的邊界上，答案仍唯一，隨機測試只比較距離的多重集合以容許平手時的任意選擇；原點本身 `[0, 0]` 的距離是 0，正常處理；座標為負數時平方後為正，不需要絕對值。

### Follow-up

> [!question]- F1. 如果參考點不是原點，或距離改成曼哈頓距離呢？
> 只改距離函式，模板完全不變：參考點 `(a, b)` 時用 `(x − a)² + (y − b)²`；曼哈頓距離用 `|x − a| + |y − b|`；切比雪夫距離用 `max(|x − a|, |y − b|)`。只要距離能 O(1) 算出，總時間仍是 O(n log k)。要提醒的是曼哈頓距離不能「省略開根號」這一步，因為它本來就沒有根號，直接比較即可；歐幾里得距離若要回傳真實距離，最後再對答案開根號，比較時一律用平方。

> [!question]- F2. 如果點是持續到來的串流，要隨時回報目前最近的 k 個呢？
> heap 版天生支援：維護同一個大小為 k 的 max-heap，每個新點 O(log k) 決定要不要換掉堆頂，查詢時回傳 heap 中的 k 個點，O(k)。記憶體只要 O(k)，與看過多少點無關。quickselect 必須保存所有點並在每次查詢重做 O(n)，不適合串流。若點也可能被刪除，就要換成可刪除的有序結構，或使用 14.4 節的 lazy deletion。

> [!question]- F3. 如果點的集合固定，但要回答很多次「離查詢點 q 最近的 k 個」呢？
> 每次重新掃描是 O(n log k)，q 次查詢共 O(q·n log k)。若查詢很多，可以預先建 KD-tree（k 維樹，依座標交替切分平面），建樹 O(n log n)，查詢時從包含 q 的葉子往上回溯，並用「到切分線的距離 ≥ 目前第 k 近」剪枝，隨機分佈的資料平均約 O(log n + k) 個節點，但最差仍可能 O(n)。面試中說明「預處理換查詢速度」的取捨，並指出 KD-tree 在高維度會失效（維度詛咒），實務上會改用近似最近鄰索引。

> [!question]- F4. 如果點都在一條線上，而且已經依座標排序，要找離 x 最近的 k 個呢（658. Find K Closest Elements）？
> 有序時不需要 heap。答案一定是排序陣列中一段長度 k 的連續區間，問題變成找區間的左端點 `left`，範圍 `[0, n − k]`。比較 `x − arr[left]` 與 `arr[left + k] − x`：前者較大代表左端太遠，應往右移，這個判斷對 left 單調，可以用第 8 章的 first_true 模板二分，O(log(n − k) + k)。這個對比很適合在面試中說出來：資料有序時，二分取代 heap；資料無序時，才需要 heap 或 quickselect。

> [!question]- F5. 如果要求回傳的 k 個點依距離由近到遠排序呢？
> heap 版最後對 heap 中的 k 個元素排序，O(k log k)，總時間 O(n log k + k log k) = O(n log k)。也可以把 heap 逐一 pop 出來，因為是 max-heap，pop 出的順序是由遠到近，反轉即可，同樣 O(k log k)。quickselect 版則是對前 k 個做一次排序，總時間期望 O(n + k log k)。距離相同時若要依座標決定先後，排序鍵改成 `(距離平方, x, y)`。

## 核心題 4｜621. Task Scheduler｜Medium

### 題目

CPU 要執行一串任務 `tasks`，每個任務用一個大寫字母表示，每個任務花一個單位時間。每個單位時間 CPU 可以執行一個任務，或者閒置（idle）。限制是：**同一種任務的兩次執行之間，至少要間隔 n 個單位時間**。任務可以依任意順序執行，回傳完成所有任務所需的最短總時間。限制：`1 <= len(tasks) <= 10⁴`，`0 <= n <= 100`。

- 範例 1：`tasks = [A, A, A, B, B, B]`、`n = 2`，回傳 `8`，例如 `A B idle A B idle A B`。
- 範例 2：同樣的任務、`n = 0`，沒有冷卻限制，回傳 `6`。
- 範例 3：`tasks = [A, A, A, A, A, A, B, C, D, E, F, G]`、`n = 2`，回傳 `16`：A 有 6 個，必須每 3 格放一個，其他任務填空檔還填不滿。
- 範例 4（邊界）：`tasks = [A, A, A, B, B, B, C, C, D]`、`n = 2`，回傳 `9`：任務夠多，完全不需要閒置。

### 思路

暴力解是枚舉所有執行順序再插入必要的閒置，階乘級，不可行。觀察第一點：任務的名字不重要，只有每種任務的次數重要；而且只有 26 種字母，所以狀態其實很小。觀察第二點，也是這題的貪婪核心：**剩下次數最多的任務最難安排**，因為它需要的冷卻空間最多；如果每一步都先執行「目前可以執行、且剩下最多」的任務，就能最晚才被迫閒置。

這個貪婪可以直接用 heap 模擬：max-heap 存每種任務的剩餘次數，另用一個佇列存「冷卻中」的任務與它可以再執行的時間。每個時間單位，先把冷卻結束的任務放回 heap，再從 heap 取剩最多的執行，次數減一後若還有剩，放進冷卻佇列，到 `time + n + 1` 才能再用。heap 空了但佇列不空，就代表必須閒置，直接把時間跳到佇列最前面的可執行時間。時間 O(T log 26)，T 是總任務數，因為 heap 最多 26 個元素。

更進一步可以直接算出答案。設出現最多的任務出現 `max_f` 次，有 `num_max` 種任務都出現這麼多次。把最多的任務排成 `max_f` 個「框」，每個框長 n + 1，前 `max_f − 1` 個框必須完整（裡面放一個最多的任務，後面跟 n 格冷卻），最後一個框只需放那 `num_max` 種最多的任務。所以至少需要 `(max_f − 1) × (n + 1) + num_max` 格。其他任務都去填框裡的空格；若空格不夠填，就把框加寬，此時完全不需要閒置，答案是任務總數。兩者取大：`max(len(tasks), (max_f − 1) × (n + 1) + num_max)`。

為什麼「框加寬」時一定能做到零閒置？因為次數比 `max_f` 少的任務，依次數由多到少輪流填入各框，同一種任務在相鄰框中的距離至少是一個框的寬度，而框的寬度至少是 n + 1，冷卻限制自然滿足。這個公式在面試中要能用框的圖說清楚，heap 模擬則是可以推廣到其他變形的通用版本（見 Follow-up）。

```text
範例 3：A×6，B、C、D、E、F、G 各 1，n = 2
max_f = 6，num_max = 1 → (6 - 1) × (2 + 1) + 1 = 16

框（每框寬 n + 1 = 3）：
框1     框2     框3     框4     框5     框6
A B C | A D E | A F G | A _ _ | A _ _ | A
前 5 框完整（共 15 格），最後一框只放 A（1 格）→ 16
B..G 只能填 6 個空格，還剩 4 格閒置

範例 4：A×3，B×3，C×2，D×1，n = 2
max_f = 3，num_max = 2 → (3 - 1) × 3 + 2 = 8 < 9 = 任務總數 → 答案 9
A B C | A B C | A B D        空格全部填滿，最後一框原本只要 A B，D 讓它變長
```

範例 3 中 A 的冷卻要求太強，其他任務不夠填，所以答案由公式的第二項決定；範例 4 中任務足夠多，公式的第二項 8 比任務數 9 小，代表不需要任何閒置，答案就是 9。面試時用這兩個例子畫框，比直接背公式更有說服力。

### 解法

```python
import heapq
import random
from collections import Counter, deque


def least_interval(tasks: list[str], n: int) -> int:
    freq = Counter(tasks).values()
    max_f = max(freq)
    num_max = sum(1 for c in freq if c == max_f)
    return max(len(tasks), (max_f - 1) * (n + 1) + num_max)


def least_interval_simulate(tasks: list[str], n: int) -> int:
    heap = [-c for c in Counter(tasks).values()]   # max-heap：剩餘次數
    heapq.heapify(heap)
    cooling: deque[tuple[int, int]] = deque()      # (可再執行的時間, 剩餘次數的負值)
    time = 0
    while heap or cooling:
        if not heap:                               # 全部在冷卻，直接跳到下一個可執行的時間
            time = cooling[0][0]
        while cooling and cooling[0][0] <= time:
            heapq.heappush(heap, cooling.popleft()[1])
        c = heapq.heappop(heap) + 1                # 執行剩最多的那種，次數減一
        if c < 0:
            cooling.append((time + n + 1, c))
        time += 1
    return time


assert least_interval(["A", "A", "A", "B", "B", "B"], 2) == 8
assert least_interval(["A", "A", "A", "B", "B", "B"], 0) == 6
assert least_interval(list("AAAAAABCDEFG"), 2) == 16
assert least_interval(list("ACABDB"), 1) == 6
assert least_interval(["A"], 100) == 1
assert least_interval(list("AAABBBCCD"), 2) == 9     # 任務夠多，不需要閒置
for _ in range(1000):
    t = [random.choice("ABCDE") for _ in range(random.randint(1, 15))]
    n = random.randint(0, 5)
    assert least_interval(t, n) == least_interval_simulate(t, n)
print("all tests passed")
```

### 複雜度與邊界

公式版時間 O(T)（計數一次），空間 O(1)（最多 26 種）；模擬版時間 O(T log 26) = O(T)，因為 heap 與冷卻佇列都最多 26 個元素，而且閒置時直接跳時間，不會逐格空轉。邊界情況：n = 0 時公式的第二項是 `max_f − 1 + num_max ≤ T`，答案為 T；只有一種任務時答案是 `(T − 1)(n + 1) + 1`；多種任務並列最多時 `num_max` 要全部算進最後一框（範例 1 的 A、B 都是 3 次，最後一框是 `A B`）；n 很大而任務很少時（`["A"]`、n = 100）答案就是 1，最後一個任務之後不需要閒置。

### Follow-up

> [!question]- F1. 如果要輸出實際的執行順序（含 idle）呢？
> 用模擬版，每個時間單位記錄執行了哪個任務；heap 空的時候，從目前時間到冷卻佇列最前面的時間之間，每一格輸出一個 idle。heap 的元素改成 `(-剩餘次數, 任務名)`，冷卻佇列也存任務名。時間 O(T + 閒置數)，輸出本身就是這麼長，無法更快。公式版只能給長度，不能直接給順序；若一定要用框的想法構造，就是把最多的任務放在每框開頭，其他任務依次數由多到少按「框 1、框 2、…」輪流填，空格補 idle。

> [!question]- F2. 如果任務必須依照給定的順序執行，不能重排呢（2365. Task Scheduler II）？
> 那就不需要 heap，也沒有貪婪的選擇空間，只是模擬：用 hash map 記錄每種任務上次執行的時間 `last[t]`，處理下一個任務時，若 `day − last[t] <= n`（2365 的定義是至少間隔 space 天），就把 day 直接跳到 `last[t] + n + 1`，再執行並更新 `last[t]`。時間 O(T)，空間 O(不同任務數)。這個對比說明了原題的 heap 是因為「可以重排」才需要：重排帶來選擇，選擇才需要每一步挑最好的。

> [!question]- F3. 如果每種任務的冷卻時間不同呢？
> 框的公式不再成立，因為框的寬度不再統一。heap 模擬仍然可以用：冷卻佇列改成以「可再執行時間」為鍵的 min-heap（不同任務的冷卻長度不同，先進佇列的不一定先解除），每一步把所有已解除的任務移回可執行的 heap，再取剩餘次數最多的。這是一個合理的啟發式，但在冷卻時間不同時「先做剩最多的」不保證最佳，例如冷卻長的任務應該更早開始；面試中要誠實指出這一點，並說明精確解需要搜尋或 DP。

> [!question]- F4. 如果只問最少需要幾個 idle 呢？
> 由公式直接得到：idle 數 = `max(0, (max_f − 1) × (n + 1) + num_max − T)`，T 是任務總數。直觀解釋是框的總格數減去任務數：框的格數不夠放下所有任務時，框會被撐寬而沒有空格，idle 為 0；否則剩下的格子都是 idle。O(T) 計數即可。面試官追問這題，通常是想確認你理解公式裡的 `max` 對應「空格不夠填就加寬框」這一步，而不是只背了公式。

## 核心題 5｜767. Reorganize String｜Medium

### 題目

給一個只含小寫字母的字串 `s`，重新排列它的字元，使得任意兩個相鄰的字元都不相同。可以做到就回傳任意一個合法的排列，做不到就回傳空字串。限制：`1 <= len(s) <= 500`。

- 範例 1：`s = "aab"`，回傳 `"aba"`。
- 範例 2：`s = "aaab"`，回傳 `""`：三個 a 至少需要兩個其他字元隔開，只有一個 b。
- 範例 3：`s = "vvvlo"`，回傳例如 `"vlvov"`。
- 範例 4（邊界）：`s = "a"`，回傳 `"a"`；只有一個字元時沒有相鄰的問題。

### 思路

暴力解是枚舉所有排列，檢查有沒有相鄰相同，O(n! · n)，不可行。先問「什麼時候做不到」：若某個字元出現 c 次，相鄰的兩個 c 之間至少要夾一個別的字元，所以長度 n 的字串中，它最多只能出現在 0、2、4、… 這些位置，也就是 ⌈n/2⌉ = `(n + 1) // 2` 次。因此 `max_f > (n + 1) // 2` 時一定做不到。神奇的是反過來也成立：只要 `max_f ≤ (n + 1) // 2`，就一定做得到。下面兩種構造都會證明這一點。

做法一是 heap 貪婪，和核心題 4 是同一個想法：**每一步放「剩下最多、且不等於上一個字元」的字元**。剩最多的字元最危險，越早消耗越好；而上一個用過的字元暫時不能用，就先拿在手上，下一輪再放回 heap。實作上用 max-heap 存 `(-剩餘次數, 字元)`，每輪 pop 一個、append 到結果，再把上一輪暫存的字元 push 回去。這其實就是 n = 1 的 Task Scheduler，只是不允許 idle：若某一輪 heap 空了而手上還有字元，就代表無解，但只要先檢查過 `max_f ≤ (n + 1) // 2`，這種情況就不會發生。時間 O(n log 26)。

做法二是直接構造：把字元依次數由多到少排好，依序填入索引 0、2、4、…，偶數位置填滿後接著填 1、3、5、…。出現最多的字元最先填，它佔據的是 0、2、…、2(max_f − 1)，因為 `max_f ≤ (n + 1) // 2`，這些位置都在範圍內且彼此不相鄰。其他字元的次數都不超過 max_f，同一個字元連續填入時位置差 2；唯一可能出問題的是某個字元 c 從偶數位置的尾端「跨」到奇數位置的開頭：它佔了偶數位置的最後一段與奇數位置的最前一段。若其中某個奇數位置和某個偶數位置相鄰，數一下就會發現 c 的次數至少等於偶數位置的總數 ⌈n/2⌉；又因為 c 的次數不超過 max_f ≤ ⌈n/2⌉，三者只能全部相等，於是最多的字元獨自填滿了所有偶數位置，c 根本不會出現在偶數位置，矛盾。所以填位法一定合法。時間 O(n)，不需要 heap。

```text
s = "vvvlo"，次數 v:3、l:1、o:1，n = 5，上限 (5 + 1) // 2 = 3，v 剛好可以

做法一：heap 貪婪（prev = 上一輪用掉、暫時不能用的字元）
輪  pop 出   結果     放回 heap 的 prev   heap 剩下
1   v(3)     v        -                   l(1) o(1)        prev = v(2)
2   l(1)     vl       v(2)                v(2) o(1)        prev = 無（l 用完）
3   v(2)     vlv      -                   o(1)             prev = v(1)
4   o(1)     vlvo     v(1)                v(1)             prev = 無
5   v(1)     vlvov    -                   空               prev = 無
結果 "vlvov"

做法二：先填偶數位置，再填奇數位置
索引:  0  1  2  3  4
填 v:  v  .  v  .  v       （0、2、4，填完 i = 6 >= 5，跳到 1）
填 l:  v  l  v  .  v
填 o:  v  l  v  o  v       → "vlvov"
```

heap 貪婪的第 2 輪，v 剩 2 次仍是最多，但它剛被用過、被暫存在 prev，所以只能 pop 出 l；這一輪結束後 v 回到 heap，第 3 輪又輪到它。這種「暫存一輪」正是 n = 1 的冷卻。做法二則完全不看相鄰關係，只靠「最多的先填偶數位」這個安排保證合法。

### 解法

```python
import heapq
import random
from collections import Counter
from itertools import permutations


def reorganize_string(s: str) -> str:
    freq = Counter(s)
    if max(freq.values()) > (len(s) + 1) // 2:
        return ""
    heap = [(-c, ch) for ch, c in freq.items()]
    heapq.heapify(heap)
    out: list[str] = []
    prev: tuple[int, str] | None = None        # 上一輪用掉的字母，這一輪不能用
    while heap:
        c, ch = heapq.heappop(heap)            # 剩最多、且不是上一個字母
        out.append(ch)
        if prev is not None:
            heapq.heappush(heap, prev)         # 上一個字母冷卻結束，放回 heap
        prev = (c + 1, ch) if c + 1 < 0 else None
    return "".join(out)


def reorganize_string_fill(s: str) -> str:
    n = len(s)
    freq = Counter(s)
    order = sorted(freq, key=lambda ch: -freq[ch])   # 出現最多的字母排第一
    if freq[order[0]] > (n + 1) // 2:
        return ""
    res = [""] * n
    i = 0
    for ch in order:
        for _ in range(freq[ch]):
            res[i] = ch
            i += 2
            if i >= n:                         # 偶數位置填滿，換到奇數位置
                i = 1
    return "".join(res)


def valid(s: str, out: str) -> bool:
    return Counter(out) == Counter(s) and all(a != b for a, b in zip(out, out[1:]))


for f in (reorganize_string, reorganize_string_fill):
    assert valid("aab", f("aab"))
    assert f("aaab") == ""
    assert f("a") == "a"
    assert valid("vvvlo", f("vvvlo"))
    assert valid("aaabbbcc", f("aaabbbcc"))
for _ in range(500):
    s = "".join(random.choice("abc") for _ in range(random.randint(1, 8)))
    possible = any(all(a != b for a, b in zip(p, p[1:])) for p in permutations(s))
    for f in (reorganize_string, reorganize_string_fill):
        out = f(s)
        assert (out != "") == possible
        if possible:
            assert valid(s, out)
print("all tests passed")
```

### 複雜度與邊界

heap 版時間 O(n log σ)，σ ≤ 26 是字母種類數，等同 O(n)；空間 O(σ) 加上輸出 O(n)。填位版時間 O(n + σ log σ)，空間 O(n)。邊界情況：長度 1 直接回傳本身（`max_f = 1 ≤ 1`）；`max_f` 剛好等於 `(n + 1) // 2` 時（例如 `"aab"`、`"vvvlo"`），最多的字元必須佔滿所有偶數位置，兩種做法都會這樣安排；n 為偶數時上限是 n/2，例如 `"aabb"` 可以、`"aaab"` 不行；全部字元相同且長度 ≥ 2 時無解。測試中用 `valid` 驗證合法性而不是比對固定字串，因為合法答案不唯一。

### Follow-up

> [!question]- F1. 如果要求相同字元之間至少相隔 k 個位置呢（358. Rearrange String k Distance Apart）？
> 把 heap 貪婪的「暫存一輪」推廣成「暫存 k − 1 輪」：用一個佇列存最近用過的字元，佇列長度到 k 時把最前面的放回 heap。每一步從 heap 取剩最多的；若 heap 空了但結果還沒填滿，代表無解，回傳空字串（這題不能 idle）。時間 O(n log σ)。這就是核心題 4 的模擬版去掉 idle，所以兩題最好一起記：621 是「可以 idle、問最短時間」，358 是「不能 idle、問能不能排」。

> [!question]- F2. 如果要回傳字典序最小的合法排列呢？
> 逐位貪婪：每個位置從 a 到 z 嘗試，選第一個「不等於上一個字元、且放下後剩下的字元仍能合法排完」的字元。剩下長度 r 的字串能排成「第一個字元不是 c」的合法字串，條件是每個字元的次數都 ≤ `(r + 1) // 2`，而且剛放下的字元 c 剩下的次數 ≤ `r // 2`（若它剛好是 `(r + 1) // 2` 且 r 為奇數，它必須佔第一個位置，會和自己相鄰）。每個位置最多試 26 個字元、每次檢查 O(26)，總共 O(26² · n)。heap 版和填位版都不保證字典序最小。

> [!question]- F3. 如果字元排成一個環，頭尾也算相鄰呢？
> 上限變成 `max_f ≤ n // 2`（n ≥ 2），因為環上沒有「多出來的那個位置」。在這個條件下填位法仍然正確：最多的字元佔 0、2、…、2(max_f − 1) ≤ n − 2，不會碰到最後一個位置；n 為偶數時最後一個位置是奇數位、一定不是最多的字元，n 為奇數時最多的字元也到不了 n − 1，所以頭尾不同。時間 O(n)。heap 貪婪則需要額外處理最後一步，不如填位法直接。

> [!question]- F4. 如果輸入是整數陣列，保證一定有解，要回傳任一合法排列呢（1054. Distant Barcodes）？
> 完全同一題，只是元素是整數、長度到 10⁴。填位法最直接：Counter 後依次數由多到少排序，先填偶數位再填奇數位，O(n + d log d)，d 是不同值的個數。因為保證有解，可以省略 `max_f` 的檢查，但面試時最好還是說出這個條件，表示你知道演算法為什麼成立。heap 版同樣可行，時間 O(n log d)。

## 難題 1｜295. Find Median from Data Stream｜Hard

### 題目

設計一個資料結構 `MedianFinder`，支援兩個操作：`add_num(num)` 把一個整數加入資料結構；`find_median()` 回傳目前所有已加入數字的中位數。個數為奇數時中位數是排序後正中間的數，偶數時是中間兩個數的平均。限制：數字在 `-10⁵` 到 `10⁵` 之間，呼叫 `find_median` 時至少已經有一個數，兩種操作合計最多 5 × 10⁴ 次。

- 範例 1：依序 `add(1)`、`add(2)`，`find_median()` 回傳 `1.5`；再 `add(3)`，回傳 `2.0`。
- 範例 2：依序加入 5、15、1、3，每次加入後的中位數分別是 `5.0`、`10.0`、`5.0`、`4.0`。
- 範例 3（邊界）：只加入一個數 -7，中位數是 `-7.0`。
- 範例 4（邊界）：加入很多相同的數（例如五個 2），中位數是 `2.0`。

### 提示

> [!tip]- 提示 1
> 每次查詢都排序是 O(n log n)；維護一個排序陣列，插入要 O(n)。中位數只和「中間那一兩個數」有關，你真的需要知道其他數的順序嗎？

> [!tip]- 提示 2
> 把所有數分成較小的一半和較大的一半。中位數只取決於「較小一半的最大值」和「較大一半的最小值」。哪種資料結構能 O(1) 取最大值、O(log n) 插入？

> [!tip]- 提示 3
> 用一個 max-heap 存較小的一半、一個 min-heap 存較大的一半，維持「左堆頂 ≤ 右堆頂」與「左邊個數 = 右邊個數或多一個」。新數字先放進左堆，再把左堆最大的移到右堆，最後若右堆比較多就移一個回來。

### 詳解

**為什麼直覺做法不夠**。每次查詢都排序，查詢 O(n log n)；維護排序陣列用 `bisect.insort`，查詢 O(1)，但插入要搬移元素，O(n)，5 × 10⁴ 次操作最差是 O(n²) ≈ 2.5 × 10⁹ 次搬移（Python 的 list 搬移是 C 層的 memmove，實際上常常還過得去，但面試官要的是 O(log n)）。問題在於這些做法都維護了「全部數字的完整順序」，而中位數只需要知道分界線在哪。

**突破點：用兩個 heap 夾住分界線**。中位數把資料切成左右兩半，左半每個數 ≤ 右半每個數。我們不需要知道每一半內部的順序，只需要知道左半的最大值和右半的最小值，這正是 max-heap 和 min-heap 的堆頂。所以維護兩個 heap：`low` 是 max-heap（Python 中存負數），存較小的一半；`high` 是 min-heap，存較大的一半。

**兩個 invariant**。第一是**順序**：`max(low) <= min(high)`，保證兩個堆頂確實夾住中位數。第二是**大小**：`len(low) == len(high)` 或 `len(low) == len(high) + 1`，讓總數為奇數時中位數就是 `low` 的堆頂，偶數時是兩個堆頂的平均。插入時用三步維持兩者：先把新數放進 `low`；再把 `low` 的最大值移到 `high`，這一步保證了順序 invariant，因為移過去的是左邊最大的那個（不論新數本來屬於哪邊，經過這一進一出，左邊剩下的都 ≤ 右邊）；最後若 `high` 比 `low` 多，把 `high` 的最小值移回 `low`，這一步修正大小，而移回去的是右邊最小的，不會破壞順序。每次插入最多 3 次 heap 操作，O(log n)。

**正確性**。順序 invariant 保證 `low` 中的數恰好是全部數中最小的 `len(low)` 個；大小 invariant 保證 `len(low)` 是 ⌈n/2⌉。所以 `low` 的堆頂是排序後第 ⌈n/2⌉ 個數，n 為奇數時它就是中位數；n 為偶數時，`high` 的堆頂是第 n/2 + 1 個，兩者平均就是中位數。

```text
依序加入 5、15、1、3（low 是 max-heap，high 是 min-heap，依值排序顯示）

加入  步驟                          low        high      中位數
5     push low → [5]
      low 最大 5 移到 high          []         [5]
      high 比較多，5 移回 low       [5]        []        5
15    push low → [15, 5]
      low 最大 15 移到 high         [5]        [15]      (5 + 15) / 2 = 10
1     push low → [5, 1]
      low 最大 5 移到 high          [1]        [5, 15]
      high 比較多，5 移回 low       [5, 1]     [15]      5
3     push low → [5, 3, 1]
      low 最大 5 移到 high          [3, 1]     [5, 15]   (3 + 5) / 2 = 4
```

注意加入 3 的那一步：3 本來就該在左半，但它先進 `low` 之後，`low` 的最大值是 5，於是 5 被移到右邊。這個「先進左、再把左邊最大的交出去」的固定流程，讓我們不必判斷新數應該放哪一邊，也不必處理新數等於堆頂的特殊情況，程式因此只有三行。

### 解法

```python
import heapq
import random
import statistics


class MedianFinder:
    def __init__(self) -> None:
        self.low: list[int] = []    # max-heap（存負數）：較小的一半，堆頂是左半最大值
        self.high: list[int] = []   # min-heap：較大的一半，堆頂是右半最小值

    def add_num(self, num: int) -> None:
        # 先進左半，再把左半最大值交給右半：保證 max(low) <= min(high)
        heapq.heappush(self.low, -num)
        heapq.heappush(self.high, -heapq.heappop(self.low))
        # 維持 len(low) == len(high) 或 len(low) == len(high) + 1
        if len(self.high) > len(self.low):
            heapq.heappush(self.low, -heapq.heappop(self.high))

    def find_median(self) -> float:
        if len(self.low) > len(self.high):
            return float(-self.low[0])
        return (-self.low[0] + self.high[0]) / 2


mf = MedianFinder()
mf.add_num(1)
mf.add_num(2)
assert mf.find_median() == 1.5
mf.add_num(3)
assert mf.find_median() == 2.0

mf = MedianFinder()
for x, expect in [(5, 5.0), (15, 10.0), (1, 5.0), (3, 4.0)]:
    mf.add_num(x)
    assert mf.find_median() == expect

mf = MedianFinder()
mf.add_num(-7)
assert mf.find_median() == -7.0               # 只有一個數

mf = MedianFinder()
for _ in range(5):
    mf.add_num(2)
assert mf.find_median() == 2.0                # 全部相同

for _ in range(300):
    mf, seen = MedianFinder(), []
    for _ in range(random.randint(1, 30)):
        x = random.randint(-50, 50)
        mf.add_num(x)
        seen.append(x)
        assert mf.find_median() == statistics.median(seen)
print("all tests passed")
```

### 複雜度與邊界

`add_num` 時間 O(log n)：固定 2 到 3 次 heap 操作；`find_median` 時間 O(1)，只看兩個堆頂。空間 O(n)。邊界情況：只有一個數時它在 `low`、`high` 為空，`find_median` 走奇數分支，不會讀到空的 `high`；全部相同時兩個堆頂相等，順序 invariant 用 `<=` 允許相等；負數在 `low` 中存成正數，取出時要再取負一次，這是最容易寫錯的地方；平均用 `/ 2` 得到浮點數，Python 沒有溢位問題，Java 中兩個 `int` 相加可能溢位，要先轉成 `long` 或 `double`。

### Follow-up

> [!question]- F1. 如果所有數字都在 [0, 100] 之間呢？
> 改用計數陣列 `cnt[0..100]` 與總數 total：插入 O(1)，查詢時從 0 往上累加，找到第 ⌈total/2⌉ 個（偶數時再找下一個）所在的值，O(101) = O(1)。比 heap 更快也更簡單。若查詢非常頻繁，可以維護一個指向中位數所在值的指標與「左邊有幾個」，每次插入只需要把指標往左或右移動至多一格，查詢真正的 O(1)。

> [!question]- F2. 如果 99% 的數字在 [0, 100] 之間，但偶爾有離群值呢？
> 計數陣列仍然處理 [0, 100]，另外用兩個計數器記錄「< 0 的個數」與「> 100 的個數」。只要離群值少於一半，中位數一定落在 [0, 100] 內，查詢時把「< 0 的個數」當作累加的起點即可，O(101)。為了處理中位數真的落到範圍外的極端情況，可以把離群值另存在兩個 heap 或排序陣列中，那時再去查；這種「常見情況走快路徑、罕見情況走慢路徑」的設計，是面試官問這個 follow-up 想聽到的答案。

> [!question]- F3. 如果還要支援刪除某個數字呢？
> heap 不能直接刪除中間的元素，有兩種做法。一是改用有序結構（`SortedList` 或平衡樹），插入、刪除 O(log n)，中位數用索引 O(log n) 取得。二是保留兩個 heap 並加上 lazy deletion：刪除時記錄在 hash map 裡、更新兩邊的有效大小，等該元素浮到堆頂時才真正彈出，攤銷後每次 O(log n)。第二種正是難題 2（480）的寫法，關鍵是判斷被刪的數屬於哪一邊（和 `low` 的堆頂比較），以及每次平衡後都要清理堆頂。

> [!question]- F4. 如果要的不是中位數，而是任意百分位數 p（例如 p90）呢？
> 把大小 invariant 從「各一半」改成「`low` 恰好有 ⌈p · n⌉ 個」：插入時同樣先進 `low`、把最大值交給 `high`，再依目標大小在兩堆之間搬移，直到 `len(low) == ⌈p · n⌉`。因為每次插入 n 只加一，目標大小最多變動一，所以每次插入只需要常數次搬移，O(log n)；查詢 `low` 的堆頂 O(1)。若要同時支援多個百分位數，就需要多個分界，改用有序結構會更簡單。

> [!question]- F5. 如果資料量大到單機放不下，要近似的中位數呢？
> 精確的串流中位數需要 Ω(n) 記憶體，無法避免。近似做法是使用分位數草圖（quantile sketch），例如 Greenwald–Khanna 或 t-digest，它們只保存數量遠小於 n 的摘要點，保證回傳值的排名誤差在 ε·n 以內，空間約 O((1/ε) log(ε n))。若資料已經分散在多台機器且可以多輪通訊，也可以用第 8 章的值域二分精確求中位數：每輪廣播候選值 x，各台回報 ≤ x 的個數，約 log₂(值域) 輪。

### 心得

關鍵突破是「中位數只和分界線兩側的兩個數有關」，所以用兩個 heap 各管一半，只看堆頂。它是本章 two heaps 形態的原型：難題 2 在此之上加入刪除，F4 把它推廣到任意百分位數。面試時先說排序陣列的 O(n) 插入，再畫出「max-heap | min-heap」兩個桶，明確寫下順序與大小兩個 invariant，並說明「先進左、再交出左邊最大、必要時移回來」為什麼同時維持兩者。程式短，但面試官真正評分的是你能不能把 invariant 說清楚。

## 難題 2｜480. Sliding Window Median｜Hard

### 題目

給一個整數陣列 `nums` 和視窗大小 k。一個長度 k 的視窗從最左邊開始，每次往右移一格，直到碰到最右邊，總共 n − k + 1 個視窗。回傳每個視窗中元素的中位數（k 為偶數時是中間兩數的平均），誤差在 10⁻⁵ 以內都算正確。限制：`1 <= k <= n <= 10⁵`，元素在 `-2³¹` 到 `2³¹ − 1` 之間。

- 範例 1：`nums = [1, 3, -1, -3, 5, 3, 6, 7]`、`k = 3`，六個視窗的中位數是 `[1, -1, -1, 3, 5, 6]`。
- 範例 2：`nums = [1, 2, 3, 4, 2, 3, 1, 4, 2]`、`k = 3`，回傳 `[2, 3, 3, 3, 2, 3, 2]`。
- 範例 3（邊界）：`k = n`，只有一個視窗，例如 `[1, 4, 2, 3]`、`k = 4`，回傳 `[2.5]`。
- 範例 4（邊界）：`k = 1`，每個視窗的中位數就是元素本身；元素可以到 `2³¹ − 1`，兩個相加不能溢位。

### 提示

> [!tip]- 提示 1
> 每個視窗重新排序是 O(n · k log k)。這題是難題 1 的視窗版：每移一格，加入一個新數、移除一個舊數。加入沒問題，移除才是難點。

> [!tip]- 提示 2
> heap 不能刪除中間的元素。但被刪除的元素只有在它浮到堆頂時才會影響答案。能不能先記下「這個數欠刪」，等它到堆頂時才真正彈出？

> [!tip]- 提示 3
> 用 hash map `delayed` 記錄每個值待刪的次數，並自己維護兩邊的「有效大小」。刪除時判斷該值屬於哪一邊（和 `low` 的堆頂比較），更新那一邊的有效大小，若它剛好在堆頂就立刻清理。每次搬移元素平衡兩堆之後，也要清理被彈出元素那一堆的堆頂。

### 詳解

**為什麼直覺做法不夠**。每個視窗排序取中位數，O((n − k + 1) · k log k)，k = n/2 時是 O(n² log n)。維護一個排序的視窗陣列，每次用 `bisect` 找位置、`insort` 插入、`pop` 刪除，搜尋 O(log k) 但插入刪除要搬移 O(k)，總共 O(n·k)；在 Python 中因為搬移是 C 層的 memmove，這個做法實際上常常能通過，面試時可以先提出，但要指出漸進複雜度是 O(n·k)。想要 O(n log n)，就需要一個能 O(log k) 插入、刪除、取中位數的結構。

**突破點：two heaps 加 lazy deletion**。沿用難題 1 的兩個 heap：`low` 是存負數的 max-heap，`high` 是 min-heap，維持順序 invariant（`low` 的有效元素都 ≤ `high` 的有效元素）與大小 invariant（`low` 的有效個數等於 `high` 的，或多一個）。新元素照常插入；要刪除舊元素 x 時，不去找它，而是 `delayed[x] += 1`，並把 x 所在那一邊的有效大小減一。x 在哪一邊？因為順序 invariant，`x <= -low[0]` 就在 `low`，否則在 `high`；若 x 等於某一邊的堆頂，就立刻 `prune`（清理）那一邊，把所有待刪的堆頂彈出。

**為什麼堆頂一定要乾淨**。中位數只讀堆頂，所以只要保證「兩個堆頂都是有效元素」，答案就正確；沉在 heap 內部的待刪元素不影響任何判斷。堆頂可能變髒的時機只有兩種：剛刪除的元素恰好是堆頂，或平衡時從某一堆彈出了堆頂，使下一個（可能待刪的）元素浮上來。所以 `erase` 在刪到堆頂時呼叫 `prune`，`balance` 在彈出某一堆之後也對那一堆呼叫 `prune`。這兩條規則一起保證任何時刻兩個堆頂都是乾淨的，也保證判斷 x 屬於哪一邊時用的 `-low[0]` 是有效值。

**大小一律用計數器**。heap 的實際長度包含了待刪元素，所以 `len(low)` 會比邏輯大小大，平衡時若用它判斷就會失衡。程式中的 `low_size`、`high_size` 只計有效元素，每次插入、刪除、搬移都同步更新。每個元素最多被 push 一次、真正 pop 一次，heap 的實際長度最多 O(n)，所以總時間 O(n log n)。

```text
nums = [1, 3, -1, -3, 5, 3, 6, 7]，k = 3（只顯示有效元素；* 表示待刪但仍留在 heap 內）

視窗             動作                                low（大→小）   high      中位數
[1, 3, -1]       初始插入三個數，平衡                 1  -1          3         1
[3, -1, -3]      插入 -3：low 變 3 個 → 1 移到 high
                 刪除 1：1 > low 頂 -1，屬於 high，
                 1 是 high 堆頂 → 立刻 prune          -1  -3         3         -1
[-1, -3, 5]      插入 5 進 high；刪除 3（high 堆頂）    -1  -3         5         -1
[-3, 5, 3]       插入 3 進 high；刪除 -1（low 堆頂）
                 → prune；low 變少 → high 的 3 移到 low  3  -3        5         3
[5, 3, 6]        插入 6 進 high；刪除 -3：-3 <= low 頂 3，
                 屬於 low 但不在堆頂 → 只記帳；
                 low 變少 → high 的 5 移到 low          5  3  -3*    6         5
[3, 6, 7]        插入 7 進 high；刪除 5（low 堆頂）
                 → prune；low 變少 → high 的 6 移到 low  6  3  -3*    7         6
                 delayed = {-3: 1}，-3 一直沉在 low 底部，從未影響答案
```

第五個視窗是 lazy deletion 的關鍵時刻：-3 離開了視窗，但它在 `low` 的底部，當時的堆頂是 3，所以只把 `delayed[-3]` 加一、`low_size` 減一，heap 本身不動。之後 -3 始終沒有浮到堆頂，直到結束都沒有真正被彈出，但也從未影響任何一個中位數。這正是延遲刪除的精神：只有會影響答案的東西才需要處理。

### 解法

```python
import heapq
import random
import statistics
from collections import defaultdict


def median_sliding_window(nums: list[int], k: int) -> list[float]:
    low: list[int] = []            # max-heap（負數），較小的一半
    high: list[int] = []           # min-heap，較大的一半
    delayed: defaultdict[int, int] = defaultdict(int)   # 值 -> 待刪次數
    low_size = high_size = 0       # 兩邊「有效」元素個數（不含待刪）

    def prune(heap: list[int], sign: int) -> None:
        # 把堆頂已經離開視窗的元素真正彈出；sign = -1 代表 low（存負數）
        while heap and delayed[sign * heap[0]] > 0:
            delayed[sign * heap[0]] -= 1
            heapq.heappop(heap)

    def balance() -> None:
        nonlocal low_size, high_size
        if low_size > high_size + 1:
            heapq.heappush(high, -heapq.heappop(low))
            low_size -= 1
            high_size += 1
            prune(low, -1)
        elif low_size < high_size:
            heapq.heappush(low, -heapq.heappop(high))
            high_size -= 1
            low_size += 1
            prune(high, 1)

    def insert(x: int) -> None:
        nonlocal low_size, high_size
        if not low or x <= -low[0]:
            heapq.heappush(low, -x)
            low_size += 1
        else:
            heapq.heappush(high, x)
            high_size += 1
        balance()

    def erase(x: int) -> None:
        nonlocal low_size, high_size
        delayed[x] += 1
        if x <= -low[0]:            # x 屬於左半
            low_size -= 1
            if x == -low[0]:
                prune(low, -1)
        else:                       # x 屬於右半
            high_size -= 1
            if x == high[0]:
                prune(high, 1)
        balance()

    def median() -> float:
        if k % 2 == 1:
            return float(-low[0])
        return (-low[0] + high[0]) / 2

    for x in nums[:k]:
        insert(x)
    res = [median()]
    for i in range(k, len(nums)):
        insert(nums[i])
        erase(nums[i - k])
        res.append(median())
    return res


def brute(nums, k):
    return [float(statistics.median(nums[i:i + k])) for i in range(len(nums) - k + 1)]


assert median_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 3) == [1.0, -1.0, -1.0, 3.0, 5.0, 6.0]
assert median_sliding_window([1, 2, 3, 4, 2, 3, 1, 4, 2], 3) == [2.0, 3.0, 3.0, 3.0, 2.0, 3.0, 2.0]
assert median_sliding_window([1, 4, 2, 3], 4) == [2.5]
assert median_sliding_window([5, 9], 1) == [5.0, 9.0]
assert median_sliding_window([2**31 - 1, 2**31 - 1], 2) == [2147483647.0]   # 不會溢位
for _ in range(1000):
    arr = [random.randint(-5, 5) for _ in range(random.randint(1, 15))]
    k = random.randint(1, len(arr))
    assert median_sliding_window(arr, k) == brute(arr, k)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n)：每個元素被 push 一次、真正 pop 至多一次，平衡每次常數次搬移；heap 的實際長度可能因為待刪元素而大於 k，最差 O(n)，所以每次操作是 O(log n) 而不是 O(log k)。空間 O(n)（heap 與 `delayed`）。邊界情況：k = 1 時 `high` 永遠是空的，中位數走奇數分支只讀 `low`；k = n 時只輸出一次；重複值很多時（例如範例 2），`delayed` 記的是值而不是位置，刪除任何一個等值的副本都等價，所以正確；判斷屬於哪一邊時 `x == -low[0]` 也歸到左邊，因為等值副本可能同時在兩邊，歸到左邊並立刻清理左堆頂，計數就不會錯；Python 整數不溢位，Java 要用 `long` 或 `(double) a + b`。

### Follow-up

> [!question]- F1. 能不能用排序結構寫得更簡單？
> 可以用 `SortedList`（第三方 `sortedcontainers`）維護視窗：每次 `add` 新元素、`remove` 舊元素各 O(log k)，中位數用 `sl[k // 2]` 與 `sl[(k − 1) // 2]` 取，O(log k)，總時間 O(n log k)，比 heap 版更短也更不容易錯。若平台沒有這個套件，可以用 `bisect.insort` 與 `list.pop(bisect_left(...))` 的排序 list，時間 O(n·k)，但常數很小。面試時建議先說 heap 加 lazy deletion 的 O(n log n)，再提這兩種替代方案與取捨。

> [!question]- F2. 如果要的是每個視窗中「把所有元素變成同一個值」的最小總成本（每次加一或減一算成本一）呢？
> 絕對差總和在中位數處最小，所以目標值就是視窗中位數 m。成本是 `m × low_size − low_sum + high_sum − m × high_size`，其中 `low_sum`、`high_sum` 是兩邊有效元素的總和。在本題的程式中多維護這兩個總和：插入、刪除、搬移時同步加減（延遲刪除時在記帳那一刻就扣掉，不必等真正 pop）。每個視窗仍是 O(log n)，總時間 O(n log n)。這是 2448、462 類題目的視窗版。

> [!question]- F3. 如果值域很小（例如 0 到 10⁵）而 n 很大呢？
> 用第 26 章的 Fenwick tree 對值域計數：加入 x 時 `add(x, 1)`、移除時 `add(x, −1)`，第 t 小用 Fenwick tree 上的二進位倍增在 O(log V) 內找到第一個前綴和 ≥ t 的值。每個視窗 O(log V)，總時間 O(n log V)，而且完全不需要 lazy deletion。若值域很大但可以離線處理，先對所有值做座標壓縮，再用同樣的方法，O(n log n)。

> [!question]- F4. 如果要的是滑動視窗的最大值或平均值呢？
> 平均值最簡單：維護視窗總和，進一加、出一減，O(n)。最大值是第 6 章難題 2（239. Sliding Window Maximum），用 monotonic deque（單調佇列）做到 O(n)：佇列中保持遞減，新元素從尾端踢掉比它小的，舊元素過期時從頭端移除。也可以用一個 max-heap 加上「堆頂過期就 pop」的 lazy deletion，O(n log n)。中位數之所以需要兩個 heap，是因為它不是單調可維護的量，單調佇列無法處理。

### 心得

關鍵突破是「只有堆頂會影響答案，所以刪除可以延遲到它浮上堆頂時才做」，再用自己維護的有效大小取代 `len(heap)`。它是難題 1 的直接延伸，也是本章最容易寫錯的一題：錯誤幾乎都來自三個地方，判斷被刪元素屬於哪一邊、平衡後忘記清理堆頂、用 `len` 判斷大小。面試時先說 `SortedList` 或排序 list 的解法讓面試官知道你有底，再提出 two heaps 加 lazy deletion，並主動列出這三個陷阱；寫完後拿範例 1 的第五個視窗（-3 沉在底部）手動走一次，最能展現你理解延遲刪除為什麼正確。

## 難題 3｜502. IPO｜Hard

### 題目

你有初始資本 w，最多可以完成 k 個專案。共有 n 個專案，第 i 個專案需要資本至少 `capital[i]` 才能啟動，完成後淨利 `profits[i]` 會加到你的資本上（啟動所需的資本不會被花掉，只是門檻）。每個專案最多做一次，專案之間依序進行。回傳最多 k 個專案之後能得到的最大資本。限制：`1 <= k <= 10⁵`，`0 <= w <= 10⁹`，`1 <= n <= 10⁵`，`0 <= profits[i] <= 10⁴`，`0 <= capital[i] <= 10⁹`。

- 範例 1：`k = 2, w = 0, profits = [1, 2, 3], capital = [0, 1, 1]`，先做專案 0（資本變 1），再做專案 2（資本變 4），回傳 `4`。
- 範例 2：`k = 3, w = 0, profits = [1, 2, 3], capital = [0, 1, 2]`，三個都做，回傳 `6`。
- 範例 3：`k = 3, w = 1, profits = [2, 5, 1, 4, 3], capital = [0, 7, 1, 3, 5]`，依序做利潤 2、4、5 的專案，回傳 `12`。
- 範例 4（邊界）：`k = 1, w = 0, profits = [5, 6], capital = [1, 2]`，一個都做不起，回傳 `0`；k 大於專案數時，最多就是全部做完。

### 提示

> [!tip]- 提示 1
> 每一步你只能做「目前資本做得起」的專案。在做得起的專案裡，應該挑哪一個？挑了之後，做得起的範圍會怎麼變？

> [!tip]- 提示 2
> 利潤非負，所以資本只會增加，做得起的專案只會越來越多。每一步挑做得起的之中利潤最大的，為什麼不會吃虧？

> [!tip]- 提示 3
> 把專案依門檻排序，用一個指標把「門檻 ≤ 目前資本」的專案依序推進 max-heap（以利潤為鍵）。每一輪先推進新解鎖的專案，再從 heap 彈出利潤最大的。heap 空了就提早結束。

### 詳解

**為什麼直覺做法不夠**。最直接的貪婪是每一輪掃描所有專案，找出做得起且利潤最大的，O(k · n)，k 和 n 都到 10⁵ 時是 10¹⁰，太慢。另一個直覺是「依利潤排序，從大到小做」，但利潤最大的專案可能門檻太高、一開始做不起，必須先做小專案累積資本，所以單純排序不對。也有人會想到 DP 或背包，但專案的順序與門檻交織，狀態空間巨大，而且完全不需要。

**突破點：做得起的集合只會擴大**。因為利潤非負，資本在過程中單調不減，所以「門檻 ≤ 目前資本」的專案集合只會增加、不會減少（除了被做掉的）。這讓我們可以把專案依門檻排序，用一個只往前走的指標，把新解鎖的專案推進 heap；heap 以利潤為鍵（max-heap），堆頂就是目前最好的選擇。排序負責「何時可選」，heap 負責「可選的之中挑誰」，這是 14.4 節「排序 + heap」形態的標準形。

**為什麼貪婪最佳**。用交換論證。設目前資本 w，貪婪選了做得起的專案中利潤最大的 g。考慮任一個最佳方案，它的第一個專案 f 也必須是 w 做得起的，所以 `profit(g) >= profit(f)`。若最佳方案中沒有 g，把 f 換成 g：第一步後的資本不會變少，之後每一步的資本也都不會變少，所以原本做得起的專案仍然做得起，總資本不減。若最佳方案在後面的第 j 步才做 g，把 g 和 f 對調：前 j − 1 步的資本都不會變少（因為一開始就多拿了 `profit(g) − profit(f) ≥ 0`），所以每個專案仍做得起，第 j 步之後兩個方案的資本相同。不論哪種情況，都存在一個以 g 開頭的最佳方案，歸納下去，貪婪就是最佳的。

```text
k = 3，w = 1，依門檻排序後的 (capital, profit)：
(0, 2)  (1, 1)  (3, 4)  (5, 3)  (7, 5)

輪   資本 w   推進 heap（門檻 <= w）    heap 中的利潤     做哪個    新資本
1    1        (0,2) (1,1)              {2, 1}           利潤 2    3
2    3        (3,4)                    {1, 4}           利潤 4    7
3    7        (5,3) (7,5)              {1, 3, 5}        利潤 5    12
結束  做滿 k = 3 個，回傳 12
```

第 1 輪資本只有 1，利潤 5 的專案（門檻 7）還看不到，只能在 2 和 1 之中挑 2。資本變成 3 之後解鎖了 (3, 4)，第 2 輪挑 4；資本變成 7，(5, 3) 和 (7, 5) 同時解鎖，第 3 輪挑 5。指標 i 從頭到尾只往右走一次，每個專案最多進出 heap 各一次。

### 解法

```python
import heapq
import random
from itertools import permutations


def find_maximized_capital(k: int, w: int, profits: list[int], capital: list[int]) -> int:
    projects = sorted(zip(capital, profits))      # 依門檻由低到高
    available: list[int] = []                     # max-heap（負數）：目前做得起的專案利潤
    i = 0
    for _ in range(k):
        while i < len(projects) and projects[i][0] <= w:
            heapq.heappush(available, -projects[i][1])
            i += 1
        if not available:                         # 沒有做得起的專案，資本不會再變
            break
        w -= heapq.heappop(available)             # 做利潤最大的那一個
    return w


def brute(k, w, profits, capital):
    best = w
    n = len(profits)
    for r in range(1, min(k, n) + 1):
        for order in permutations(range(n), r):
            cur, ok = w, True
            for j in order:
                if capital[j] > cur:
                    ok = False
                    break
                cur += profits[j]
            if ok:
                best = max(best, cur)
    return best


assert find_maximized_capital(2, 0, [1, 2, 3], [0, 1, 1]) == 4
assert find_maximized_capital(3, 0, [1, 2, 3], [0, 1, 2]) == 6
assert find_maximized_capital(3, 1, [2, 5, 1, 4, 3], [0, 7, 1, 3, 5]) == 12
assert find_maximized_capital(1, 0, [5, 6], [1, 2]) == 0          # 一個都做不起
assert find_maximized_capital(10, 3, [1, 1], [0, 0]) == 5         # k 大於專案數
for _ in range(400):
    n = random.randint(1, 5)
    profits = [random.randint(0, 5) for _ in range(n)]
    capital = [random.randint(0, 8) for _ in range(n)]
    k, w = random.randint(1, 5), random.randint(0, 4)
    assert find_maximized_capital(k, w, profits, capital) == brute(k, w, profits, capital)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n + k log n)：排序 O(n log n)；每個專案最多 push 一次、pop 一次，各 O(log n)；k 輪迴圈中若 heap 空了就提早結束，所以 k 很大時不會空轉。空間 O(n)。邊界情況：一開始就沒有做得起的專案，第一輪就 break，回傳 w；k 大於 n 時最多做 n 個，heap 用完就停；利潤為 0 的專案做了也不影響，所以不需要特別排除；門檻相同的專案在排序後相鄰，會被同一輪一起推進；資本可到 10⁹ + 10⁵ × 10⁴ ≈ 2 × 10⁹，Java 中要注意 `int` 的上限。

### Follow-up

> [!question]- F1. 如果利潤可以是負的呢？
> 負利潤的專案永遠不該做：做了只會讓資本變少，讓之後能解鎖的專案變少，而題目是「最多」k 個而不是「恰好」。所以在建立 heap 時直接跳過利潤 ≤ 0 的專案（或在 pop 出的利潤 ≤ 0 時停止），其餘不變，O(n log n)。若題目改成必須「恰好」做 k 個，問題就變難了：負利潤會讓資本下降、做得起的集合不再單調擴大，交換論證失效，需要重新設計（例如先做正利潤的、再挑損失最小且做得起的），面試中要能指出單調性是貪婪的關鍵前提。

> [!question]- F2. 如果目標改成「達到資本 W 最少要做幾個專案」呢？
> 同樣的貪婪，只是終止條件改成 `w >= W` 時回傳目前做了幾個，heap 空了還沒達到就回傳 -1。因為貪婪在每一步都讓「做了 t 個之後的資本」達到最大（上面的交換論證對每個前綴都成立），所以它也是最早達到 W 的方案。時間 O(n log n)。這個變形和第 20 章難題 4（871. Minimum Number of Refueling Stops）幾乎是同一個結構：加油站依位置解鎖，heap 存油量，每次不得不加油時挑最大的。

> [!question]- F3. 如果每個專案可以重複做無限次呢？
> 那麼做過的專案不從 heap 移除：每一輪 peek 堆頂的最大利潤直接加上，然後檢查是否有新專案解鎖。若連續多輪都沒有新專案解鎖，可以一次跳很多輪：設堆頂利潤 p、下一個門檻 c，需要 `t = ceil((c − w) / p)` 輪才能解鎖下一個（p = 0 時永遠解鎖不了），直接把 `min(t, 剩餘輪數)` 輪一次算完。時間 O(n log n)，與 k 無關。這種「沒有新事件發生時跳時間」的技巧，和核心題 4 的閒置跳躍是同一個想法。

> [!question]- F4. 如果啟動資本會被花掉（真的支付 capital[i]，完成後拿回 capital[i] + profits[i]）呢？
> 只要支付和拿回發生在同一個專案內、專案之間依序進行，資本的淨變化仍是 `profits[i]`，門檻條件也還是「目前資本 ≥ capital[i]」，所以答案和原題完全一樣。面試官問這個，通常是想看你能不能抓住「只有淨變化與門檻重要」。若改成可以同時進行多個專案、資本被鎖住直到完成，問題就變成帶時間維度的排程，需要事件模擬（以完成時間為鍵的 heap）加上貪婪，不再是單純的 502。

### 心得

關鍵突破是「利潤非負 ⇒ 資本單調 ⇒ 做得起的集合只會擴大」，於是依門檻排序加上一個只往前走的指標，就能把每一步的「挑最好的可選項」交給 max-heap。它是本章「排序 + heap」形態的標準形，難題 5（857）是同一個形態但 heap 的用途反過來（踢掉最差的）。面試時先說 O(k · n) 的逐輪掃描，再指出單調性，提出排序加 heap，最後用交換論證說明貪婪為什麼最佳；面試官很常追問負利潤（F1），能說出「單調性壞掉，交換論證失效」就是最好的答案。

## 難題 4｜632. Smallest Range Covering Elements from K Lists｜Hard

### 題目

給 k 個整數串列，每個串列都以非遞減順序排序。找一個最小的區間 `[a, b]`，使得每個串列都至少有一個數落在區間內（含端點）。區間 `[a, b]` 比 `[c, d]` 小的定義是：`b − a < d − c`，或兩者寬度相同且 `a < c`。限制：`1 <= k <= 3500`，每個串列長度 1 到 50，元素在 `-10⁵` 到 `10⁵` 之間。

- 範例 1：`nums = [[4, 10, 15, 24, 26], [0, 9, 12, 20], [5, 18, 22, 30]]`，回傳 `[20, 24]`：24 來自第一條、20 來自第二條、22 來自第三條。
- 範例 2：`nums = [[1, 2, 3], [1, 2, 3], [1, 2, 3]]`，回傳 `[1, 1]`。
- 範例 3（邊界）：只有一個串列 `[[5, 7]]`，回傳 `[5, 5]`（寬度 0，且 5 < 7）。
- 範例 4（邊界）：`[[1], [100]]`，回傳 `[1, 100]`；元素可以是負數，例如 `[[-5, 2], [-3, 8], [1, 9]]` 回傳 `[-3, 2]`。

### 提示

> [!tip]- 提示 1
> 如果你從每個串列各挑一個數，涵蓋它們的最小區間就是 `[這些數的最小值, 這些數的最大值]`。所以問題是：要怎麼挑，才能讓最大值減最小值最小？

> [!tip]- 提示 2
> 從每條串列的第一個數開始。目前區間由最小值和最大值決定，想縮小區間，移動最大值那條沒有用（只會更大），唯一可能有用的是把最小值那條往前移一格。

> [!tip]- 提示 3
> 用 min-heap 存每條串列目前的數，另外記錄目前的最大值。每次彈出最小值、用 `[最小值, 最大值]` 更新答案，再推入同一條串列的下一個數並更新最大值。某條串列用完時停止。

### 詳解

**為什麼直覺做法不夠**。暴力是從每條串列各挑一個數，組合數是各串列長度的乘積，指數級。稍微好一點是枚舉左端點 a（所有元素之一），對每條串列 bisect 找第一個 ≥ a 的數，取最大值當 b，O(N · k log L)，N 是元素總數，最多 1.75 × 10⁵，k 是 3500，log L 約 6，總共達數十億次操作，太慢。瓶頸在於每換一個左端點，就重新對 k 條串列各查一次，但左端點往右移一點點時，大部分串列的選擇根本沒變。

**突破點：k-way merge 的指標推進**。每條串列維護一個指標，指向目前選的數；heap 存這 k 個數，堆頂是最小值，再用一個變數記錄最大值。目前區間 `[堆頂, cur_max]` 涵蓋每條串列。想得到更小的區間，移動最大值那條或任何非最小值的串列都只會讓數變大、區間不會縮小；唯一有希望的是把最小值那條往前推一格。所以每一步彈出堆頂、推入同一條的下一個數、更新 cur_max。當被彈出的那條串列已經用完，之後的任何區間都無法涵蓋它（它的所有數都已經小於目前的左端點），演算法結束。heap 大小始終是 k，總時間 O(N log k)。

**為什麼一定會遇到最佳區間**。設最佳區間是 `[a, b]`。對每條串列 i，令 `e_i` 是它第一個 ≥ a 的數，因為最佳區間涵蓋串列 i，`e_i <= b`。只要還有某條串列的指標在 `e_i` 之前（指向的數 < a），heap 的最小值就 < a，被彈出的一定是某個 < a 的數，不會是任何 `e_j`（它們都 ≥ a），所以沒有指標會越過自己的 `e_j`；而且被彈出的那條串列一定還有下一個數（至少有 `e_i`），演算法不會提前結束。因此最終會到達所有指標恰好都在 `e_i` 的狀態，此時區間是 `[min e_i, max e_i]`，左端 ≥ a、右端 ≤ b，寬度不超過最佳，所以它就是最佳寬度。寬度相同時要 a 較小：堆頂的值在過程中單調不減，只在寬度**嚴格**變小時更新，就自然保留了最早、也就是 a 最小的那一個。

```text
A = [4, 10, 15, 24, 26]，B = [0, 9, 12, 20]，C = [5, 18, 22, 30]

步  指標 (A, B, C)    區間 [min, max]   寬度   最佳         彈出（推進）
1   (4, 0, 5)         [0, 5]            5      [0, 5]       B：0 → 9
2   (4, 9, 5)         [4, 9]            5      [0, 5]       A：4 → 10
3   (10, 9, 5)        [5, 10]           5      [0, 5]       C：5 → 18
4   (10, 9, 18)       [9, 18]           9      [0, 5]       B：9 → 12
5   (10, 12, 18)      [10, 18]          8      [0, 5]       A：10 → 15
6   (15, 12, 18)      [12, 18]          6      [0, 5]       B：12 → 20
7   (15, 20, 18)      [15, 20]          5      [0, 5]       A：15 → 24
8   (24, 20, 18)      [18, 24]          6      [0, 5]       C：18 → 22
9   (24, 20, 22)      [20, 24]          4      [20, 24]     B：20 已是最後一個 → 結束
```

第 1、2、3、7 步的寬度都是 5，但因為只在嚴格變小時更新，答案一直保留最早的 `[0, 5]`，直到第 9 步出現寬度 4 的 `[20, 24]`。第 9 步彈出的是 B 的 20，B 已經沒有下一個數，之後任何區間的左端都會 > 20，無法涵蓋 B，所以停止。整個過程中 heap 一直只有 3 個元素。

### 解法

```python
import heapq
import random


def smallest_range(nums: list[list[int]]) -> list[int]:
    heap = [(lst[0], i, 0) for i, lst in enumerate(nums)]   # 每條串列目前的指標
    heapq.heapify(heap)
    cur_max = max(lst[0] for lst in nums)
    best = [heap[0][0], cur_max]
    while True:
        val, i, j = heapq.heappop(heap)          # val 是目前的最小值，[val, cur_max] 涵蓋每條串列
        if cur_max - val < best[1] - best[0]:
            best = [val, cur_max]
        if j + 1 == len(nums[i]):                # 第 i 條用完：之後的區間都缺少它
            return best
        nxt = nums[i][j + 1]
        cur_max = max(cur_max, nxt)
        heapq.heappush(heap, (nxt, i, j + 1))


def brute(nums):
    cands = sorted({x for lst in nums for x in lst})
    best = None
    for a in cands:
        b = a
        ok = True
        for lst in nums:
            ge = [x for x in lst if x >= a]
            if not ge:
                ok = False
                break
            b = max(b, min(ge))
        if ok and (best is None or b - a < best[1] - best[0]):
            best = [a, b]
    return best


assert smallest_range([[4, 10, 15, 24, 26], [0, 9, 12, 20], [5, 18, 22, 30]]) == [20, 24]
assert smallest_range([[1, 2, 3], [1, 2, 3], [1, 2, 3]]) == [1, 1]
assert smallest_range([[5, 7]]) == [5, 5]
assert smallest_range([[1], [100]]) == [1, 100]
assert smallest_range([[-5, 2], [-3, 8], [1, 9]]) == [-3, 2]
for _ in range(1000):
    lists = [sorted(random.randint(-10, 10) for _ in range(random.randint(1, 5)))
             for _ in range(random.randint(1, 4))]
    assert smallest_range(lists) == brute(lists)
print("all tests passed")
```

### 複雜度與邊界

時間 O(N log k)：N 是所有串列的元素總數，每個元素最多進出 heap 一次，heap 大小固定為 k；建初始 heap 用 `heapify` 是 O(k)。空間 O(k)。邊界情況：只有一條串列時，第一次彈出就得到 `[第一個數, 第一個數]`，寬度 0，之後只會更新成同寬但 a 更大的區間，因為用嚴格小於所以不更新，答案正確；串列中有重複值時（範例 2），指標會一格一格推進，heap 中可能同時有多個相同的值，tuple 的第二欄 i 保證比較不會出錯；所有串列各只有一個數時，答案就是 `[全體最小, 全體最大]`；第一個區間 `[heap[0][0], cur_max]` 在迴圈前就設為初始答案，迴圈第一次會再比較一次同一個區間，不影響正確性。

### Follow-up

> [!question]- F1. 能不能不用 heap，改用 sliding window？
> 可以。把所有元素連同所屬串列編號合併成一個陣列並依值排序（O(N log N)，或用 k-way merge O(N log k)），問題就變成第 6 章難題 1（76. Minimum Window Substring）的形式：找最短的連續片段，使片段中出現所有 k 種「顏色」。用 two pointers 加上每種顏色的計數與「已涵蓋的顏色數」，右指標擴張到涵蓋全部 k 種，再收縮左指標，O(N)。兩種做法複雜度相近，sliding window 版更容易推廣到其他條件（見 F2）。

> [!question]- F2. 如果只要求至少涵蓋其中 m 條串列（m < k）呢？
> heap 版不再適用，因為「唯一該推進的是最小值那條」的論證依賴於每條都必須被涵蓋。改用 F1 的 sliding window：合併排序後，維護視窗中出現的不同串列數，條件從「等於 k」改成「≥ m」，其餘不變，O(N log N)（排序）加上 O(N)（掃描）。這個 follow-up 正好說明了為什麼要同時會兩種解法：heap 版在「全部涵蓋」時最自然，sliding window 版能處理更一般的條件。

> [!question]- F3. 如果串列沒有排序呢？
> 先把每條串列各自排序，O(Σ L_i log L_i) ≤ O(N log L)，再用原本的 heap 解法，總時間 O(N log L + N log k)。也可以直接走 F1 的路線，把所有元素標上串列編號後一次排序，O(N log N)。無論哪種，排序都是必要的前處理，因為區間的概念依賴值的大小關係。

> [!question]- F4. 如果要的是讓每條串列各挑一個數之後，「最大值減最小值」最小的那組數本身呢？
> 就是本題的答案區間附帶每條串列的選擇。在 heap 版中，更新最佳區間的那一刻，heap 裡剩下的 k − 1 個元素加上剛彈出的那一個，恰好每條串列各一個，就是一組合法的選擇：把它們的 `(值, 串列編號)` 記錄下來即可。但每次更新都複製 k 個元素，最差 O(N·k)；更好的做法是只記錄最佳區間 `[a, b]`，最後再對每條串列 bisect 找第一個 ≥ a 的數，O(k log L)，那一定 ≤ b。

### 心得

關鍵突破是「從每條各挑一個時，區間由最小值和最大值決定，而唯一值得推進的是最小值那條」，這把指數級的組合搜尋變成 k-way merge 的指標推進，heap 負責隨時給出最小值、一個變數負責最大值。它和第 11 章難題 2（23. Merge k Sorted Lists）是同一個骨架，只是多追蹤了最大值與答案。面試時先說枚舉左端點加 bisect 的 O(N · k log L)，再提出指標推進，接著用「指標不會越過 `e_i`」的論證說明為什麼一定會碰到最佳區間；若面試官問「至少 m 條」，就切換到 sliding window。

## 難題 5｜857. Minimum Cost to Hire K Workers｜Hard

### 題目

有 n 個工人，第 i 個的品質是 `quality[i]`、最低期望薪資是 `wage[i]`。你要雇用**恰好** k 個人組成一組，薪資規則有兩條：同組中每個人的薪資必須和他的品質成正比（品質是別人兩倍的，薪資也必須是兩倍）；每個人拿到的薪資不能低於他的最低期望。回傳滿足條件的最小總薪資，誤差在 10⁻⁵ 以內都算正確。限制：`1 <= k <= n <= 10⁴`，`1 <= quality[i], wage[i] <= 10⁴`。

- 範例 1：`quality = [10, 20, 5]`、`wage = [70, 50, 30]`、`k = 2`，選工人 0 和 2：每單位品質付 7，分別拿 70 和 35，總共 `105.0`。
- 範例 2：`quality = [3, 1, 10, 10, 1]`、`wage = [4, 8, 2, 2, 7]`、`k = 3`，選工人 0、2、3：每單位品質付 4/3，總共 (3 + 10 + 10) × 4/3 ≈ `30.66667`。
- 範例 3（邊界）：`k = 1` 時只雇一個人，答案是最小的 `wage[i]`，例如 `quality = [4, 2]`、`wage = [9, 3]` 回傳 `3.0`。
- 範例 4（邊界）：所有人的 `wage / quality` 都相同時，任何一組的單價都一樣，答案是單價乘上最小的 k 個品質之和。

### 提示

> [!tip]- 提示 1
> 「薪資與品質成正比」代表同組有一個共同的單價 r（每單位品質的薪資），每個人拿 r × quality。r 至少要多大，才能讓每個人都不低於期望？

> [!tip]- 提示 2
> r 必須 ≥ 每個人的 `wage[i] / quality[i]`，所以 r 就是組內這個比例的最大值，總成本是 `max(比例) × sum(品質)`。如果固定「誰的比例最大」，剩下的人應該怎麼挑？

> [!tip]- 提示 3
> 依比例由小到大排序。枚舉第 i 個人當作比例最大的那一位，他前面的人比例都不比他大，可以任意挑；要讓總品質最小，就挑品質最小的 k − 1 個（連同他自己共 k 個）。用一個大小為 k 的 max-heap 維護「目前品質最小的 k 個」與它們的總和。

### 詳解

**為什麼直覺做法不夠**。枚舉所有 C(n, k) 組，對每組算 `max(比例) × sum(品質)`，指數級。另一個直覺是「挑比例最小的 k 個」或「挑品質最小的 k 個」，兩者都錯：比例小的人可能品質很高（例如範例 1 的工人 1，比例 2.5 但品質 20），品質小的人可能要價很高。成本是兩個維度的乘積，單看一個維度都不行。

**突破點：先寫出成本公式**。設單價 r，工人 i 拿 `r × quality[i]`，條件 `r × quality[i] >= wage[i]` 等價於 `r >= wage[i] / quality[i]`。所以一組人的最小單價就是組內比例的最大值，總成本 = `max(ratio) × sum(quality)`。這種「最大值 × 總和」的成本，標準做法是**枚舉誰是最大值**：依比例由小到大排序，當第 i 個人是組內比例最大的人時，組內其他人只能從前 i 個人（比例 ≤ 他的）中挑，而且單價已經固定為 `ratio[i]`，所以要讓 `sum(quality)` 最小，就挑前面品質最小的 k − 1 個。

**用 heap 維護「品質最小的 k 個」**。掃描時把每個人的品質放進一個 max-heap，heap 超過 k 個就踢掉品質最大的，同時維護 heap 中品質的總和。這是 14.3 節 top-k 模板的「最小 k 個」版本，堆頂是最大的那個，是門檻。當 heap 剛好有 k 個時，用目前這個人的比例乘上總和，就是「以他為比例最大者」的一個候選成本。

**一個細節：目前這個人一定在 heap 裡嗎**？不一定。若他的品質很大，push 之後馬上被踢掉，heap 裡的 k 個人都是他之前的人，此時算出的 `ratio[i] × sum` 用的單價比必要的還大（因為這 k 個人的最大比例 ≤ `ratio[i]`），是一個「偏高但合法」的成本：這組人用 `ratio[i]` 付薪資一定滿足所有人的期望。它不會讓答案變錯，因為真正的最佳值會在處理那 k 個人中比例最大者時被算到，且那時的單價更低。所以程式不需要特判，取所有候選的最小值即可。

```text
quality = [10, 20, 5]，wage = [70, 50, 30]，k = 2
比例 wage / quality：工人 0 = 7.0，工人 1 = 2.5，工人 2 = 6.0
依比例排序：(q=20, r=2.5)  (q=5, r=6.0)  (q=10, r=7.0)

步  加入的人       heap 中的品質（max-heap）   sum   heap 有 k 個？   候選成本
1   q=20, r=2.5    {20}                        20    否               -
2   q=5,  r=6.0    {20, 5}                     25    是               6.0 × 25 = 150
3   q=10, r=7.0    {20, 5, 10} → 踢掉 20       15    是               7.0 × 15 = 105
答案 = min(150, 105) = 105
```

第 2 步時比例最大的是 6.0，組員只能是前兩人，成本 150。第 3 步時單價升到 7.0，但可以踢掉品質 20 的工人 1，總品質從 25 降到 15，成本反而降到 105。這展現了兩個維度的取捨：單價隨枚舉單調上升，heap 則盡量把總品質壓低，答案是兩者乘積的最小值。

### 解法

```python
import heapq
import random
from itertools import combinations


def mincost_to_hire_workers(quality: list[int], wage: list[int], k: int) -> float:
    workers = sorted(zip(quality, wage), key=lambda qw: qw[1] / qw[0])   # 依「每單位品質要價」排序
    heap: list[int] = []        # max-heap（負數）：目前選中的 k 個品質
    q_sum = 0
    best = float("inf")
    for q, w in workers:
        heapq.heappush(heap, -q)
        q_sum += q
        if len(heap) > k:
            q_sum += heapq.heappop(heap)       # 踢掉品質最大的（彈出的是負數）
        if len(heap) == k:
            best = min(best, w / q * q_sum)    # 目前這位的比例最高，由他決定單價
    return best


def brute(quality, wage, k):
    best = float("inf")
    for group in combinations(range(len(quality)), k):
        r = max(wage[i] / quality[i] for i in group)
        best = min(best, r * sum(quality[i] for i in group))
    return best


assert abs(mincost_to_hire_workers([10, 20, 5], [70, 50, 30], 2) - 105.0) < 1e-5
assert abs(mincost_to_hire_workers([3, 1, 10, 10, 1], [4, 8, 2, 2, 7], 3) - 30.66667) < 1e-5
assert abs(mincost_to_hire_workers([4, 2], [9, 3], 1) - 3.0) < 1e-5          # k = 1：最低要價
assert abs(mincost_to_hire_workers([2, 3], [4, 6], 2) - 10.0) < 1e-5          # 比例相同
for _ in range(500):
    n = random.randint(1, 7)
    quality = [random.randint(1, 10) for _ in range(n)]
    wage = [random.randint(1, 10) for _ in range(n)]
    k = random.randint(1, n)
    assert abs(mincost_to_hire_workers(quality, wage, k) - brute(quality, wage, k)) < 1e-6
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n)：排序 O(n log n)，每個人 push 一次、最多 pop 一次，heap 大小 ≤ k + 1，各 O(log k)。空間 O(n)（排序後的陣列）加上 O(k)（heap）。邊界情況：k = 1 時 heap 每一步都只留品質最小的那一個，但候選成本是 `ratio × q`，對目前這個人自己恰好等於 `wage`，取最小值就是最低要價；k = n 時只有最後一步 heap 才滿，答案是最大比例乘上全部品質；比例相同的工人在排序後順序任意，不影響答案，因為單價相同；浮點誤差只發生在比例與最終乘法，題目容許 10⁻⁵ 誤差，若需要精確比較，可以用 `fractions.Fraction` 或交叉相乘 `w1 * q2 < w2 * q1` 排序。

### Follow-up

> [!question]- F1. 如果還要回傳被雇用的是哪 k 個人呢？
> heap 中存 `(-quality, 原始索引)` 而不是只存品質，每次更新 best 時把 heap 中的 k 個索引複製一份，最差 O(n·k)。更省的做法是只記下達到最佳成本時的那個「比例最大者」在排序中的位置 i*，最後再跑一次：在前 i* + 1 個人中，以品質為鍵選出最小的 k 個（用 `heapq.nsmallest`，O(n log k)），就是一組最佳解。總時間仍是 O(n log n)。

> [!question]- F2. 如果改成給定預算 B，問最多能雇幾個人呢？
> 先證明「雇 k 個人的最小成本」對 k 單調不減：從雇 k + 1 人的最佳組中移除任何一人，單價不會上升、總品質下降，所以 k 人的成本不超過它。因此可以對 k 做第 8 章的答案空間二分，每次用本題的 O(n log n) 演算法檢查 `cost(k) <= B`，總時間 O(n log² n)。也可以排序一次之後重用排序結果，讓每次檢查只剩 O(n log k) 的 heap 掃描。

> [!question]- F3. 如果薪資規則改成「每個人拿一樣多」呢？
> 那麼每個人拿的薪資必須 ≥ 組內最高的 `wage`，總成本是 `k × max(wage)`。要讓它最小，就挑 `wage` 最小的 k 個人，答案是 `k × 第 k 小的 wage`，用 quickselect 期望 O(n) 或大小為 k 的 heap O(n log k)。這個對比說明了原題的難點：成本是「比例最大值 × 品質總和」兩個維度的乘積，所以才需要「排序一個維度、heap 另一個維度」。

> [!question]- F4. 還有哪些題目是同一個「枚舉瓶頸 + heap 保留最佳 k 個」的骨架？
> 1383. Maximum Performance of a Team：表現 = `min(efficiency) × sum(speed)`，依效率由大到小排序，枚舉目前這位當作最小效率，用大小為 k 的 min-heap 保留速度最大的 k 個，O(n log n)。2542. Maximum Subsequence Score 完全同構（`min(nums2) × sum(nums1)`）。共同的辨識方式是成本或分數寫成「某個極值 × 某個總和」：依產生極值的那個維度排序並枚舉，另一個維度交給 heap 維持最佳的 k 個。

### 心得

關鍵突破是把規則化成公式「總成本 = 組內最大比例 × 品質總和」，接著用「枚舉誰是最大值」把兩個維度拆開：排序處理比例，heap 處理品質。它和難題 3（502）同屬「排序 + heap」形態，差別在於 502 的 heap 用來挑最好的，這題的 heap 用來踢掉最差的（維持最小的 k 個）。面試時先說明為什麼單看比例或單看品質都錯（舉範例 1 的工人 1），再推出公式，然後說「依比例排序、枚舉單價、heap 保留最小品質」；若面試官質疑「目前這個人被踢掉了怎麼辦」，就說明那時的成本偏高但合法，不影響最小值。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| Top-K 元素 | 「第 k 大／小」「最大的 k 個」，k 遠小於 n 或資料是串流 | 大小為 k 的反向 heap（找最大用 min-heap），堆頂是門檻；一次給齊時可用 quickselect | 核心題 1（215）、703、414 |
| Top-K 依分數 | 「最常出現」「最近」「最高分」的 k 個 | 先算分數（Counter、距離平方），再 top-k；分數範圍小時用 bucket | 核心題 2（347）、核心題 3（973）、692、451 |
| K-way merge | k 條已排序串列，合併、找第 k 小、找跨串列組合 | heap 中每條串列一個代表，彈出後補同一條的下一個 | 難題 4（632）、第 11 章難題 2（23）、373、378 |
| 冷卻排程 | 「同一種之間要間隔」「相鄰不能相同」 | 每步挑剩最多的；冷卻中的暫存在佇列；或直接用框的公式／填位法 | 核心題 4（621）、核心題 5（767）、358、1054 |
| Two heaps | 串流中位數、百分位數 | max-heap 存小的一半、min-heap 存大的一半，維持順序與大小兩個 invariant | 難題 1（295） |
| Two heaps + lazy deletion | 中位數加上刪除（滑動視窗） | 待刪記在 hash map，自己維護有效大小，堆頂髒了才 prune | 難題 2（480） |
| 排序解鎖 + 挑最好 | 選項有門檻，門檻隨過程放寬 | 依門檻排序，指標推進到 heap，每步彈出最好的 | 難題 3（502）、第 20 章難題 4（871）、1834 |
| 枚舉瓶頸 + 保留最佳 k 個 | 成本是「某極值 × 某總和」 | 依產生極值的維度排序並枚舉，另一維度用大小 k 的 heap 維持 | 難題 5（857）、1383、2542 |
| Heap 加貪婪的最短路徑 | 非負權重的最短路徑、最小生成樹 | heap 依目前距離取出下一個要確定的點 | 第 18 章核心題 1（743）、核心題 5（1584） |
| 反悔貪婪 | 先貪心選，之後發現更好的就換掉 | heap 存已選的項目，違反限制時彈出最差的 | 第 20 章難題 3（630. Course Schedule III） |

**下限與上限**。最簡單的形式是「直接呼叫 heap」：215、973 只要知道 top-k 模板與 heap 的方向，考的是你會不會用 min-heap 找最大的 k 個，以及能不能比較 heap、排序、quickselect 的取捨。中間層是「heap 加上一個觀察」：621、767 需要看出「剩最多的最難安排」，502 需要看出「資本單調、做得起的集合只會擴大」，632 需要看出「唯一值得推進的是最小值那條」。上限的題目難在三個地方，常常同時出現：第一，**heap 不支援的操作**，例如 480 的任意刪除，必須用 lazy deletion 並且把計數與清理寫對；第二，**成本由兩個維度組合而成**，例如 857 的「最大比例 × 總品質」，必須先推出公式，再用「排序一維、heap 一維」拆開；第三，**證明貪婪正確**，例如 502 的交換論證、632 的「指標不會越過 `e_i`」，面試官常常會要求你說明為什麼不會漏掉最佳解。

**與其他 pattern 的關係**。heap 與 binary search（第 8 章）常是第 k 小問題的兩種解法：k 小時用 heap 的 k-way merge，k 大或候選數巨大（例如第 8 章難題 3 的 668，候選 9 × 10⁸ 個）時用計數二分。heap 與 sliding window（第 6 章）在 632 和 480 交會：632 可以改寫成合併後的最短涵蓋視窗，480 是視窗加上中位數，而視窗最大值（239）則用單調佇列比 heap 更好。heap 與 greedy（第 20 章）的關係最緊密：凡是「每一步從可選集合挑最好的」且可選集合會變動，heap 就是實作工具。heap 也是 Dijkstra 與 Prim（第 18 章）的核心，兩者本質上都是「依目前最佳估計值取出下一個要確定的點」。

**容易混淆之處**。第一，heap 的方向：找最大的 k 個用 min-heap，找最小的 k 個用 max-heap，因為堆頂必須是「最容易被淘汰的那個」。第二，heap 不是排序結構：`heap[1]` 不是第二小，要有序輸出必須 pop 或排序；需要任意排名、任意刪除時，該換成排序陣列、`SortedList` 或第 26 章的 Fenwick tree。第三，不是所有 top-k 都該用 heap：資料一次給齊且可修改時 quickselect 期望 O(n)，分數範圍小時 bucket O(n)，資料已排序時用二分（973 的 F4，658）。第四，「每步挑最好的」不一定正確：621 的貪婪在冷卻時間都相同時正確，冷卻時間不同時就不保證；502 的貪婪依賴利潤非負。用 heap 之前，先確認貪婪本身成立。

## 本章重點整理

- Heap 的本質是「反覆取極值」：push、pop O(log n)，看堆頂 O(1)，`heapify` O(n)；它只保證堆頂，不保證整體有序。
- Python 的 `heapq` 只有 min-heap，max-heap 存負數；tuple 用 `(鍵, 唯一索引, …)` 避免比較到不可比較的物件。
- Top-K 模板：找最大的 k 個用大小為 k 的 **min-heap**，堆頂是門檻，新元素超過門檻才 `heapreplace`；O(n log k)、O(k) 空間，天生支援串流。
- 一次給齊的 top-k 還有 quickselect（隨機 pivot 加三路切分，期望 O(n)）與 bucket（分數範圍小時 O(n)）；面試時先說 heap，再說這兩者的前提與取捨。
- K-way merge 模板：每條串列在 heap 中恰好一個代表，彈出後補同一條的下一個；O(N log k)。632 在此之上多追蹤最大值，並在某條用完時停止。
- 冷卻排程的貪婪是「每步挑剩最多、且目前可用的」；621 可以用框的公式 `max(T, (max_f − 1)(n + 1) + num_max)`，767 的可行條件是 `max_f ≤ (n + 1) // 2`，填偶數位再填奇數位即可構造。
- Two heaps 維持兩個 invariant：左堆頂 ≤ 右堆頂、左邊個數等於右邊或多一個；插入時「先進左、交出左邊最大、必要時移回」。
- Lazy deletion：待刪記在 hash map，自己維護有效大小，刪到堆頂或平衡後立刻 prune；只有堆頂會影響答案，所以沉在底部的待刪元素可以不管。
- 「排序 + heap」：排序處理「何時可選」（502 的門檻）或「誰是瓶頸」（857 的比例），heap 處理「可選的之中挑最好」或「保留最佳 k 個」。
- 成本是「極值 × 總和」時，枚舉誰是極值，另一個維度用大小 k 的 heap 維持；857、1383、2542 都是這個骨架。
- 用 heap 實作貪婪前，先證明貪婪本身正確：502 靠利潤非負與交換論證，632 靠「指標不會越過第一個 ≥ a 的數」。
- 需要任意刪除或任意排名時，heap 不是對的工具，改用 lazy deletion、`SortedList`、Fenwick tree 或排序陣列加 bisect。
