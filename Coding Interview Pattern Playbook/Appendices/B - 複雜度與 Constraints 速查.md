# 附錄 B　複雜度與 Constraints 速查

> [!abstract] 本附錄地圖
> **用途**：寫完解法、要說出複雜度之前，或讀完 constraints、要決定做法之前，翻到這裡查表。原理與推導在第 3 章，本附錄只做集中整理與補充。
>
> **內容**：
> - B.1 記號與三種「複雜度」：worst、average、amortized
> - B.2 Python 內建資料結構操作複雜度（list、dict、set、deque、heapq、str、sorted、bisect）
> - B.3 本書用到的資料結構：BST／平衡樹、Trie、Union-Find、Fenwick tree、Segment tree、monotonic stack／deque
> - B.4 常見演算法複雜度：排序、圖、字串、DP 與其他
> - B.5 Constraints 對應可接受複雜度（Python 估算版）
> - B.6 遞迴樹與 Master theorem 速算
> - B.7 Amortized 分析：動態陣列、monotonic stack、union-find
> - B.8 空間複雜度與遞迴 stack
> - B.9 看起來 O(n²) 其實 O(n)，以及反過來的陷阱
> - B.10 面試中講複雜度的句型

## B.1 記號與三種「複雜度」

本附錄的表格統一使用以下記號：n 是主要輸入的長度（陣列元素數、字串長度、節點數），m 是第二個輸入的長度，k 是題目給的參數（前 k 個、k 個串列），L 是單一字串或單字的長度，V 與 E 是圖的節點數與邊數，W 是背包容量，U 是數值範圍的大小。面試時第一件事就是**先定義這些變數**，因為「O(n)」在兩個人腦中可能指不同的 n。

同一個操作常常有三種不同的複雜度，表格中會分開標示。**最壞情況（worst case）** 是任何輸入下的上界，例如 quicksort 遇到最差的 pivot 時是 O(n²)。**平均情況（average／expected）** 是對輸入分布或隨機性取期望，例如 hash table 的查詢平均 O(1)，前提是雜湊值分散得夠好。**攤銷（amortized）** 則是「任意一連串操作的總成本除以操作次數」，它不依賴機率：`list.append` 攤銷 O(1) 代表 n 次 append 的總成本一定是 O(n)，只是個別某一次可能是 O(n)。

這三者最常被混淆的是 average 與 amortized。Hash table 的 O(1) 是 average，理論上可能被刻意構造的輸入打成 O(n)；動態陣列的 O(1) 是 amortized，沒有任何輸入能讓 n 次 append 超過 O(n)。面試中說「dict 查詢 O(1)」通常不會被挑剔，但如果面試官追問最壞情況，要能說出「平均 O(1)，碰撞嚴重時最壞 O(n)」。

## B.2 Python 內建資料結構操作複雜度

以下以 CPython 為準。這些數字是實作細節而非語言規格，但多年來都穩定，面試中可以直接使用。Python 語法與用法的詳細說明在附錄 A，這裡只列複雜度。

### list（動態陣列）

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `a[i]`、`a[i] = x`、`len(a)` | O(1) | 連續記憶體，直接定位 |
| `a.append(x)` | 攤銷 O(1)，單次最壞 O(n) | 擴容時複製全部元素，見 B.7 |
| `a.pop()` | 攤銷 O(1) | 移除尾端 |
| `a.pop(i)`、`a.insert(i, x)` | O(n − i) | 後面的元素都要平移；`pop(0)`、`insert(0, x)` 是 O(n) |
| `del a[i]`、`a.remove(x)` | O(n) | `remove` 要先線性搜尋再平移 |
| `x in a`、`a.index(x)`、`a.count(x)` | O(n) | 線性掃描 |
| `a[i:j]`（切片） | O(j − i) | 會**複製**一份新 list |
| `a + b`、`a.extend(b)` | O(len(a) + len(b))、O(len(b)) | `a + b` 建立新 list；`extend` 攤銷 |
| `a * k` | O(n·k) | 例如 `[0] * n` 是 O(n) |
| `a.copy()`、`list(a)`、`a[:]` | O(n) | 淺複製 |
| `a.reverse()`、`a[::-1]` | O(n) | 前者原地，後者建立新 list |
| `min(a)`、`max(a)`、`sum(a)` | O(n) | 線性掃描 |
| `a.sort()`、`sorted(a)` | O(n log n)，已排序時 O(n) | Timsort，穩定排序；`sorted` 另需 O(n) 空間 |
| `a == b` | O(n) | 逐一比較 |

### dict 與 set（hash table）

| 操作 | 平均 | 最壞 | 說明 |
|---|---|---|---|
| `d[k]`、`d[k] = v`、`del d[k]`、`k in d`、`d.get(k)` | O(1) | O(n) | 最壞發生在大量碰撞 |
| `s.add(x)`、`s.remove(x)`、`s.discard(x)`、`x in s` | O(1) | O(n) | 同上 |
| 走訪 `for k in d`、`d.items()` | O(n) | O(n) | dict 保留插入順序 |
| `d.copy()`、`set(a)`、`dict(pairs)` | O(n) | — | 建立時每個元素一次雜湊 |
| `d.popitem()` | O(1) | — | 移除最後插入的一筆 |
| `s \| t`（聯集） | O(len(s) + len(t)) | — | 建立新 set |
| `s & t`（交集） | O(min(len(s), len(t))) | O(len(s)·len(t)) | 掃描較小的那一個 |
| `s - t`（差集） | O(len(s)) | — | 對 s 的每個元素查 t |
| `s <= t`（子集判斷） | O(len(s)) | — | 對 s 的每個元素查 t |

兩個常被忽略的成本。第一，**雜湊本身不是 O(1)**：長度 L 的字串第一次雜湊要 O(L)（之後會快取在該字串物件上），長度 k 的 tuple 每次雜湊都是 O(k)。所以「用 `tuple(sorted(word))` 當 key 分組」的成本是 O(L log L) 而不是 O(1)。第二，`collections.Counter` 與 `defaultdict` 都是 dict，操作複雜度相同；`Counter(a)` 是 O(n)，`most_common(k)` 是 O(n log k)，不給 k 時是完整排序 O(n log n)。`OrderedDict.move_to_end` 與 `popitem(last=False)` 都是 O(1)，這是 LRU cache（第 27 章）的基礎。

### collections.deque（雙端佇列）

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `append`、`appendleft`、`pop`、`popleft` | O(1) | 兩端操作都是常數，這是它取代 `list.pop(0)` 的原因 |
| `d[0]`、`d[-1]` | O(1) | 兩端索引 |
| `d[i]`（中間） | O(n) | 內部是區塊組成的 linked list，不能當隨機存取陣列 |
| `x in d`、`d.remove(x)` | O(n) | 線性掃描 |
| `d.rotate(k)` | O(k) | 搬動 k 個元素 |
| `deque(maxlen=k)` 的 append | O(1) | 滿了會自動丟掉另一端，適合固定長度窗口 |

BFS 的佇列一定要用 deque。用 list 搭配 `pop(0)` 的 BFS，每次出隊都是 O(n)，整體從 O(V + E) 退化成 O(V² + E)，在 10⁵ 個節點時就會超時。

### heapq（binary min-heap）

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `heapq.heappush(h, x)`、`heapq.heappop(h)` | O(log n) | 沿樹高上浮或下沉 |
| `h[0]`（看最小值） | O(1) | 不移除 |
| `heapq.heapify(a)` | O(n) | 不是 O(n log n)，見 B.9 |
| `heapq.heappushpop`、`heapq.heapreplace` | O(log n) | 一次完成 push 與 pop，比分開做省一次調整 |
| `heapq.nlargest(k, a)`、`heapq.nsmallest(k, a)` | O(n log k) | k 接近 n 時不如直接排序 |
| `heapq.merge(*iterables)` | 總長 N 時 O(N log k) | k 路合併，惰性產生 |
| 刪除任意元素 | O(n) | 要找位置再重建；實務上用 lazy deletion：標記為刪除，pop 到時再丟掉 |
| 減少某個元素的 key | 不支援 | Dijkstra 改成「push 新的 (距離, 節點)，pop 到過期的就跳過」 |

heapq 只有 min-heap。要 max-heap 時存 `-x`；要依多個欄位排序時存 tuple，並注意 tuple 的第二個欄位必須可以比較，否則加一個遞增的序號當 tie-breaker。

### str（不可變字串）

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `s[i]`、`len(s)` | O(1) | |
| `s[i:j]` | O(j − i) | 建立新字串 |
| `s + t` | O(len(s) + len(t)) | 建立新字串 |
| 迴圈中 `res += ch` | 最壞 O(n²) 總成本 | 每次可能複製整個字串；用 list 收集再 `"".join` |
| `"".join(parts)` | O(總長度) | 建字串的標準做法 |
| `s == t`、`hash(s)`（第一次） | O(n) | |
| `sub in s`、`s.find(sub)`、`s.count(sub)` | 保守寫 O(n·m) | CPython 的實作對多數輸入接近線性，但不要把它當成 O(1)；若題目本身就是字串比對，要自己講 KMP 或 Z（第 25 章） |
| `s.split()`、`s.replace(a, b)`、`s.lower()`、`s[::-1]` | O(n) | 都會產生新字串 |
| `sorted(s)` | O(n log n) | 回傳 list，常與 `"".join` 搭配 |
| `ord(c)`、`chr(i)` | O(1) | 字元計數陣列的基礎 |

### sorted 與 bisect

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `sorted(a, key=f)` | O(n log n) 次比較 ＋ n 次呼叫 f | key 對每個元素只算一次；穩定排序，可以依多個鍵分次排序 |
| `bisect.bisect_left(a, x)`、`bisect.bisect_right(a, x)` | O(log n) | a 必須已排序；Python 3.10 起支援 `key=` |
| `bisect.insort(a, x)` | O(n) | 找位置 O(log n)，但插入要平移 O(n) |
| 「每次 insort 後查詢」做 n 次 | O(n²) | 平移是 C 層級的記憶體搬移，常數很小，n ≤ 10⁵ 時常常還能通過，但要誠實說出最壞複雜度 |

標準函式庫**沒有**平衡二元搜尋樹。需要「動態插入、刪除、找前驅後繼、找第 k 小」時，面試中的選項是：說明會用平衡 BST 並描述介面；用 heap 加 lazy deletion（只需要最小或最大值時）；把所有可能出現的值先離散化，再用 Fenwick tree 做計數與第 k 小（第 26 章）；或在 n 不大時用 `bisect.insort` 並說明 O(n) 的插入成本。

## B.3 本書用到的資料結構

| 資料結構 | 操作 | 時間 | 空間 | 本書章節 |
|---|---|---|---|---|
| BST（不平衡） | 搜尋、插入、刪除 | O(h)，h 平均 O(log n)、最壞 O(n) | O(n) | 13 |
| | 中序走訪 | O(n) | O(h) stack | 13 |
| | 第 k 小 | O(h + k)；節點存子樹大小時 O(h) | | 13 |
| 平衡 BST（AVL、紅黑樹） | 搜尋、插入、刪除、前驅、後繼 | O(log n) | O(n) | 13（Python 無內建） |
| Binary heap | push、pop | O(log n) | O(n) | 14 |
| | 建堆 | O(n) | | 14 |
| Trie（字典樹） | 插入、搜尋、字首查詢一個長度 L 的字 | O(L) | O(總字元數)，子節點用 dict | 13 |
| | 帶 `.` 萬用字元的搜尋 | 最壞 O(總節點數) | | 13 |
| Union-Find | find、union（path compression ＋ union by rank／size） | 攤銷 O(α(n))，近乎常數 | O(n) | 17 |
| | 只用其中一種優化 | O(log n) | | 17 |
| | 都不用 | 最壞 O(n) | | 17 |
| Fenwick tree（Binary Indexed Tree） | 單點更新、前綴和查詢、區間和查詢 | O(log n) | O(n) | 26 |
| | 建立 | O(n)（逐一更新則 O(n log n)） | | 26 |
| | 找第 k 小（存計數時，用 binary lifting） | O(log n) | | 26 |
| Segment tree | 建立 | O(n) | O(n)，陣列實作常開 4n | 26 |
| | 單點更新、區間查詢 | O(log n) | | 26 |
| | 區間更新（lazy propagation） | O(log n) | | 26 |
| Sparse table | 建立；區間最小值查詢 | O(n log n)；O(1) | O(n log n) | 補充，本書不展開 |
| Monotonic stack | 每次 push／pop | 攤銷 O(1)，n 個元素總共 O(n) | O(n) | 10 |
| Monotonic deque | 每次加入、移除過期、取最值 | 攤銷 O(1)，取最值 O(1) | O(k)，k 是窗口大小 | 6 |
| Prefix sum 陣列 | 建立；區間和查詢 | O(n)；O(1) | O(n) | 7 |
| Difference array | 區間加值；最後還原 | O(1)；O(n) | O(n) | 7 |
| LRU cache（hash map ＋ 雙向 linked list） | get、put | O(1) | O(容量) | 27 |

選擇區間結構時的經驗法則：只有查詢、沒有更新，用 prefix sum；有單點更新又要區間和，Fenwick tree 最短最好寫；要區間最大最小值、區間更新或更複雜的合併，用 segment tree；靜態的區間最小值且查詢極多，sparse table 的 O(1) 查詢最快。

## B.4 常見演算法複雜度

### 排序與選擇

| 演算法 | 時間 | 額外空間 | 穩定 | 備註 |
|---|---|---|---|---|
| Timsort（`sorted`、`list.sort`） | O(n log n)，已排序或接近排序時 O(n) | O(n) | 是 | Python 內建 |
| Merge sort | O(n log n) | O(n) | 是 | linked list 版可做到 O(log n) 或 O(1) 額外空間（第 11 章難題 4） |
| Quicksort | 平均 O(n log n)，最壞 O(n²) | 平均 O(log n) stack | 否 | 隨機 pivot 讓最壞情況機率極低 |
| Heapsort | O(n log n) | O(1) | 否 | |
| Counting sort | O(n + U) | O(U) | 可以是 | 數值範圍 U 小時 |
| Radix sort | O(d·(n + b)) | O(n + b) | 是 | d 位數、基數 b |
| Bucket sort | 平均 O(n) | O(n) | | 輸入接近均勻分布時；也用於 top-k 頻率（第 14 章） |
| Quickselect | 平均 O(n)，最壞 O(n²) | O(1)（迭代版） | | 找第 k 小 |
| Median of medians | 最壞 O(n) | O(log n) | | 理論上的保證，常數大，面試中知道即可 |

任何只靠比較的排序，最壞情況都至少需要 Ω(n log n) 次比較。所以面試官問「能不能比 O(n log n) 更快」時，答案一定是「利用比較以外的資訊」：數值範圍小（counting sort）、只要部分結果（quickselect、heap）、或輸入已經有序。

### 搜尋與線性技巧

| 演算法 | 時間 | 空間 | 本書章節 |
|---|---|---|---|
| Binary search（陣列） | O(log n) | O(1) | 8 |
| Binary search on answer | O(log U × 判定成本)，常見 O(n log U) | 判定所需 | 8 |
| Two pointers | O(n)，需先排序則 O(n log n) | O(1) | 5 |
| Sliding window | O(n) | 窗口內的計數結構 | 6 |
| Sweep line（端點排序） | O(n log n) | O(n) | 9 |
| Backtracking：所有子集 | O(n·2ⁿ) | O(n) 遞迴深度（不含輸出） | 19 |
| Backtracking：所有排列 | O(n·n!) | O(n) | 19 |
| Backtracking：大小為 k 的組合 | O(k·C(n, k)) | O(k) | 19 |
| Meet in the middle | O(2^(n/2)·n) | O(2^(n/2)) | 19 |

### 圖

| 演算法 | 時間 | 空間 | 適用情況 | 本書章節 |
|---|---|---|---|---|
| BFS、DFS（adjacency list） | O(V + E) | O(V) | 可達性、連通塊、無權最短路 | 15 |
| BFS、DFS（adjacency matrix） | O(V²) | O(V²) | 稠密圖 | 15 |
| 格子圖 BFS／DFS | O(m·n) | O(m·n) | 每格是節點、最多 4 條邊 | 15 |
| 狀態 BFS（位置 × 額外狀態） | O(V·S + E·S) | O(V·S) | 帶鑰匙、剩餘次數等 | 15 |
| Multi-source BFS | O(V + E) | O(V) | 多個起點同時擴散 | 15 |
| 0-1 BFS | O(V + E) | O(V) | 邊權只有 0 或 1，用 deque | 18 |
| 二分圖判定 | O(V + E) | O(V) | 塗兩色 | 15 |
| Topological sort（Kahn 或 DFS） | O(V + E) | O(V) | DAG、依賴、偵測有向環 | 16 |
| Dijkstra（binary heap、lazy deletion） | O((V + E) log V) | O(V + E) | 非負邊權最短路 | 18 |
| Dijkstra（陣列版） | O(V²) | O(V) | 稠密圖，E 接近 V² 時反而較好 | 18 |
| Bellman-Ford | O(V·E) | O(V) | 有負權邊、偵測負環 | 18 |
| 最多 k 條邊的 Bellman-Ford | O(k·E) | O(V) | 第 18 章核心題 2 的限制步數 | 18 |
| Floyd-Warshall | O(V³) | O(V²) | 全點對最短路，V ≤ 數百 | 18 |
| Kruskal | O(E log E) | O(V + E) | 排序邊 ＋ union-find | 17、18 |
| Prim（heap） | O(E log V) | O(V + E) | 稀疏圖 MST | 18 |
| Prim（陣列） | O(V²) | O(V) | 完全圖，例如點與點之間都有邊 | 18 |
| Tarjan 找 bridge、SCC | O(V + E) | O(V) | 關鍵連線、強連通分量 | 18 |
| Hierholzer（Euler path） | O(E)，邊需排序時 O(E log E) | O(E) | 每條邊恰走一次 | 補充 |

Dijkstra 的 heap 在 lazy deletion 下最多同時有 O(E) 筆資料，所以精確的寫法是 O(E log E)；因為 E ≤ V²，log E ≤ 2 log V，兩種寫法是同一個量級。完全圖（例如 n 個點兩兩連線、E 約 n²/2）上，陣列版 Prim 的 O(V²) 比 heap 版的 O(V² log V) 好，這是第 18 章核心題 5 的常見追問。

### 字串

| 演算法 | 時間 | 空間 | 用途 | 本書章節 |
|---|---|---|---|---|
| 暴力比對 | O(n·m) | O(1) | 文字長 n、pattern 長 m | 25 |
| KMP | O(n + m) | O(m) | 單一 pattern 比對、最長相同前後綴 | 25 |
| Z-algorithm | O(n + m) | O(n + m) | 每個位置與字首的最長共同前綴 | 25 |
| Rolling hash（Rabin-Karp） | 期望 O(n + m) | O(1) 到 O(n) | 子字串比對、比較多個子字串是否相等；有碰撞機率 | 25 |
| Binary search ＋ rolling hash | 期望 O(n log n) | O(n) | 最長重複子字串 | 25 |
| 中心擴展找回文 | O(n²) | O(1) | 最長回文子字串、回文子字串計數 | 25 |
| Manacher | O(n) | O(n) | 同上，線性 | 25 |
| Trie 建立 | O(總字元數) | O(總字元數) | 多字串字首查詢 | 13 |

Rolling hash 用 Python 的大整數時，若不取 mod，數字會越來越長，每次乘法不再是 O(1)。一定要每一步都對一個大質數取 mod，讓數字保持在固定大小。

### Dynamic Programming

DP 的複雜度一律用「狀態數 × 每個狀態的轉移成本」計算，空間是「需要同時保存的狀態數」。

| 類型 | 代表問題 | 狀態數 | 轉移 | 時間 | 空間（可優化到） | 本書章節 |
|---|---|---|---|---|---|---|
| 一維線性 | House Robber、爬樓梯 | n | O(1) | O(n) | O(1) | 21 |
| 一維掃前面 | LIS 基本版 | n | O(n) | O(n²) | O(n) | 21 |
| LIS 優化 | patience sorting ＋ binary search | — | O(log n) | O(n log n) | O(n) | 21 |
| 字串切分 | Word Break | n | O(L) 個長度，每個切片 O(L) | O(n·L²) | O(n) | 21 |
| 狀態機 | 買賣股票（持有、冷卻、交易次數 k） | n·k·常數 | O(1) | O(n·k) | O(k) | 21 |
| 兩序列比對 | LCS、Edit Distance | m·n | O(1) | O(m·n) | O(min(m, n)) | 22 |
| 格子路徑 | Unique Paths、最小路徑和 | m·n | O(1) | O(m·n) | O(n) | 22 |
| 0/1 背包 | Partition Equal Subset Sum | n·W | O(1) | O(n·W) | O(W)，容量倒序更新 | 23 |
| 完全背包 | Coin Change、Coin Change II | n·W | O(1) | O(n·W) | O(W)，容量正序更新 | 21、23 |
| 區間 DP | 戳氣球、矩陣連乘 | n² | O(n) | O(n³) | O(n²) | 23 |
| 回文區間 | 最長回文子序列 | n² | O(1) | O(n²) | O(n) | 23 |
| Tree DP | House Robber III、樹的直徑 | n | O(子節點數) | O(n) | O(h) stack | 24 |
| Bitmask DP（分配） | 任務分配 | 2ⁿ | O(n) | O(2ⁿ·n) | O(2ⁿ) | 24 |
| Bitmask DP（TSP 類） | 走訪所有點 | 2ⁿ·n | O(n) | O(2ⁿ·n²) | O(2ⁿ·n) | 24 |
| 數位 DP | 計算 ≤ N 的合格數字個數 | D·S·2 | O(10) | O(D·S·10) | O(D·S) | 24 |

背包 DP 的 O(n·W) 是**偽多項式（pseudo-polynomial）**：它和容量的「數值」成正比，而不是和輸入的位元數成正比。所以 W ≤ 10⁴ 時沒問題，W 到 10⁹ 就不能這樣做，要改用其他觀察（例如 n 很小時改成 meet in the middle）。

### 數學與位元

| 演算法 | 時間 | 本書章節 |
|---|---|---|
| 歐幾里得 gcd | O(log min(a, b)) | 28 |
| 快速冪 | O(log e) | 28 |
| 判斷質數（試除） | O(√n) | 28 |
| Eratosthenes 篩法 | O(n log log n) | 28 |
| 枚舉每個數的倍數 | O(n log n)，調和級數 | 3、28 |
| 計算 popcount、取最低位 `x & -x` | O(1)（固定寬度整數） | 28 |

## B.5 Constraints 對應可接受複雜度

本節沿用第 3 章 3.2 節的表，再補上「代入上限後的操作次數」與 Python 的估計時間。估算基準是 **Python 每秒約 10⁷ 個簡單操作**（一次整數加法、比較、list 索引、dict 查詢這種量級的事情）。這是方便心算的**粗略估計**，不是量測結果：實際速度依機器、Python 版本與迴圈內容而異，迴圈本體越複雜，越接近每秒 10⁶；反過來，交給 C 實作的內建函式（`sorted`、`sum`、`set` 運算、`str` 方法）每個元素的成本低得多。各平台的時間限制也不同，下表只用來判斷量級。

| n 的上限 | 可接受的複雜度 | 代入上限的操作次數 | Python 估計時間 | 判斷 |
|---|---|---|---|---|
| ≤ 10 | O(n!)、O(n!·n) | 10! ≈ 3.6 × 10⁶ | 約 0.4 秒起 | 可以；n = 11、12 時要靠剪枝 |
| ≤ 20 | O(2ⁿ·n) | 2²⁰ × 20 ≈ 2 × 10⁷ | 約 2 秒 | 偏緊；O(2ⁿ) 的 10⁶ 很輕鬆 |
| ≤ 40 | O(2^(n/2)·n) | 2²⁰ × 20 ≈ 2 × 10⁷ | 約 2 秒 | Meet in the middle |
| ≤ 100–200 | O(n³) | 200³ = 8 × 10⁶ | 約 1 秒 | 可以 |
| ≤ 500 | O(n³)，常數要小 | 500³ ≈ 1.25 × 10⁸；區間 DP 的 i < k < j 約 n³/6 ≈ 2 × 10⁷ | 約 2–12 秒 | 只有常數小的三層迴圈可行 |
| ≤ 10³ | O(n²)、O(n² log n) | 10⁶ 到 10⁷ | 0.1–1 秒 | 可以 |
| ≤ 10⁴ | O(n²) 很危險 | 10⁸ | 約 10 秒 | 純 Python 雙層迴圈通常太慢，優先找 O(n log n) |
| ≤ 10⁵ | O(n log n)、O(n√n) 偏緊 | n log n ≈ 1.7 × 10⁶；n√n ≈ 3 × 10⁷ | 0.2 秒；約 3 秒 | O(n log n) 安全 |
| ≤ 10⁶ | O(n)、O(n log n) | 10⁶；n log n ≈ 2 × 10⁷ | 0.1 秒；約 2 秒 | 線性最安全；O(n log n) 的部分最好交給內建排序 |
| ≤ 10⁷–10⁸ | O(n) | 10⁷ 到 10⁸ | 約 1 秒到 10 秒 | 只能線性，而且迴圈要極簡或交給內建函式；到 10⁸ 時通常要找數學觀察 |
| ≥ 10⁹ | O(log n)、O(√n)、O(1) | log n ≈ 30；√n ≈ 3 × 10⁴ | 可忽略 | 不能逐一處理每個值 |

這張表和第 3 章的版本一致，只是多了一個提醒：同一個複雜度在 Python 中能撐的 n 比編譯語言小。第 3 章說「n ≤ 10⁴ 時 O(n²) 在 Python 中通常已經很緊」，代入這裡的估計就是約 10 秒；所以除非內層是內建函式或只有一兩個操作，否則就該找更好的做法。面試中的白板題通常不會真的計時，但說出這個估算本身就是加分。

多變數時要全部代入。例如 m, n ≤ 200 的矩陣上做 O(m²·n) 是 8 × 10⁶，安全；n 個單字、每個長 L ≤ 10 的題目，O(n·L²) 在 n = 10⁵ 時是 10⁷，也還可以。其他 constraints（數值範圍、k、查詢次數、mod 10⁹+7）透露的訊號，見第 3 章 3.2 節的第二張表。

下面的小程式把這個估算寫成函式。它只是一個量級計算器，不是效能預測。

```python
import math

OPS_PER_SEC = 10**7  # Python 簡單操作的粗略估計值，不是量測結果

COMPLEXITY = {
    "n": lambda n: n,
    "n log n": lambda n: n * max(1.0, math.log2(n)),
    "n sqrt n": lambda n: n * math.sqrt(n),
    "n^2": lambda n: n**2,
    "n^3": lambda n: n**3,
    "2^n * n": lambda n: 2.0**n * n,
}


def estimate_seconds(n: int, name: str) -> float:
    return COMPLEXITY[name](n) / OPS_PER_SEC


def verdict(n: int, name: str) -> str:
    sec = estimate_seconds(n, name)
    if sec <= 1:
        return "safe"
    if sec <= 5:
        return "tight"
    return "too slow"


assert verdict(10**5, "n log n") == "safe"        # 約 1.7 * 10^6 次
assert verdict(10**6, "n") == "safe"
assert verdict(10**4, "n^2") == "too slow"        # 10^8 次，約 10 秒
assert verdict(10**3, "n^2") == "safe"
assert verdict(200, "n^3") == "safe"              # 8 * 10^6 次
assert verdict(20, "2^n * n") == "tight"          # 約 2 * 10^7 次
assert verdict(10**5, "n sqrt n") == "tight"      # 約 3 * 10^7 次
print("all tests passed")
```

## B.6 遞迴樹與 Master theorem 速算

分析遞迴的通用方法是畫遞迴樹：總成本等於所有節點的工作量加總，通常可以「每層加總，再乘上層數」來算。Master theorem 是這個方法在「每次切成 a 個大小 n/b 的子問題」時的公式化結果，第 3 章 3.3 節有入門說明。

**Master theorem**：若 T(n) = a·T(n/b) + Θ(nᵈ)，其中 a ≥ 1、b > 1，令 c = log_b(a)，比較 d 與 c：

| 情況 | 條件 | 結果 | 直覺 |
|---|---|---|---|
| 1 | d < c | Θ(n^c) | 葉子太多，工作集中在最底層 |
| 2 | d = c | Θ(nᵈ log n) | 每層工作量一樣，乘上 log n 層 |
| 3 | d > c | Θ(nᵈ) | 根的工作最多，往下每層遞減成等比級數 |

情況 2 有一個常用的延伸：若額外工作是 Θ(nᵈ logᵏ n) 且 d = c，結果是 Θ(nᵈ logᵏ⁺¹ n)。例如 T(n) = 2T(n/2) + O(n log n) 是 O(n log² n)，這是「每層都排序一次」的分治會得到的複雜度。

| 遞迴式 | a, b, d | 情況 | 結果 | 例子 |
|---|---|---|---|---|
| T(n) = T(n/2) + O(1) | 1, 2, 0 | 2 | O(log n) | binary search |
| T(n) = T(n/2) + O(n) | 1, 2, 1 | 3 | O(n) | quickselect 平均情況（每次大約砍半） |
| T(n) = 2T(n/2) + O(1) | 2, 2, 0 | 1 | O(n) | 遍歷平衡二元樹、建 segment tree |
| T(n) = 2T(n/2) + O(n) | 2, 2, 1 | 2 | O(n log n) | merge sort、分治求逆序對 |
| T(n) = 2T(n/2) + O(n log n) | — | 2 延伸 | O(n log² n) | 每層排序的分治 |
| T(n) = 3T(n/2) + O(n) | 3, 2, 1 | 1 | O(n^1.585) | Karatsuba 大數乘法 |
| T(n) = 4T(n/2) + O(n) | 4, 2, 1 | 1 | O(n²) | 樸素的分治乘法，沒有比直接乘快 |
| T(n) = 8T(n/2) + O(n²) | 8, 2, 2 | 1 | O(n³) | 樸素的分治矩陣乘法 |

Master theorem 不適用的遞迴，就回到遞迴樹直接數：

| 遞迴式 | 遞迴樹的形狀 | 結果 | 例子 |
|---|---|---|---|
| T(n) = T(n − 1) + O(1) | 一條鏈，n 層各 O(1) | O(n) | 線性遞迴、走 linked list |
| T(n) = T(n − 1) + O(n) | 一條鏈，第 i 層 O(n − i) | O(n²) | quicksort／quickselect 最壞情況 |
| T(n) = 2T(n − 1) + O(1) | 滿二元樹，深度 n | O(2ⁿ) | 子集枚舉、河內塔 |
| T(n) = T(n − 1) + T(n − 2) + O(1) | 不平衡的二元樹 | O(φⁿ)，φ ≈ 1.618 | 不記憶化的 Fibonacci |
| T(n) = n·T(n − 1) + O(1) | 分支數遞減 | O(n!) | 排列枚舉 |
| T(n) = T(n/3) + T(2n/3) + O(n) | 每層總和 ≤ n，最長路徑 log_{3/2} n 層 | O(n log n) | 切分不均勻但比例固定的分治 |
| T(n) = T(√n) + O(1) | 每層開根號 | O(log log n) | 少見，知道即可 |

兩個實用的提醒。第一，遞迴樹的每個節點如果有額外工作，要乘進去：backtracking 在每個葉子複製一份長度 n 的路徑，所以子集枚舉是 O(n·2ⁿ) 而不只是 O(2ⁿ)。第二，加上記憶化之後，遞迴樹會「塌縮」成狀態圖，複雜度改用狀態數 × 轉移成本計算：Fibonacci 從 O(φⁿ) 變成 O(n)。

```text
T(n) = 2T(n/2) + n 的遞迴樹（n = 16），每層總和都是 n

層 0：                 16                         = 16
層 1：           8             8                  = 16
層 2：       4       4     4       4              = 16
層 3：     2   2   2   2 2   2   2   2            = 16
層 4：    1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1         = 16（基底）

log2(16) = 4，共 5 層 → 總和 16 × 5 = n log2 n + n → Θ(n log n)
```

下面的程式把 Master theorem 寫成函式，並用直接展開遞迴的方式驗證 merge sort 的結果確實是 n log₂ n + n。

```python
import math
from functools import cache


def power(e: float) -> str:
    if math.isclose(e, 0, abs_tol=1e-9):
        return "1"
    if math.isclose(e, 1):
        return "n"
    return f"n^{e:.4g}"


def master(a: int, b: int, d: float) -> str:
    """T(n) = a T(n/b) + Theta(n^d) 的漸近複雜度。"""
    c = math.log(a) / math.log(b)
    if math.isclose(c, d, abs_tol=1e-9):
        return "Theta(log n)" if math.isclose(d, 0, abs_tol=1e-9) else f"Theta({power(d)} log n)"
    return f"Theta({power(max(c, d))})"


assert master(1, 2, 0) == "Theta(log n)"        # binary search
assert master(1, 2, 1) == "Theta(n)"            # quickselect 平均
assert master(2, 2, 0) == "Theta(n)"            # 遍歷平衡樹
assert master(2, 2, 1) == "Theta(n log n)"      # merge sort
assert master(3, 2, 1) == "Theta(n^1.585)"      # Karatsuba
assert master(8, 2, 2) == "Theta(n^3)"


@cache
def merge_sort_cost(n: int) -> int:
    """T(1) = 1, T(n) = 2T(n/2) + n，n 為 2 的冪次。"""
    return 1 if n == 1 else 2 * merge_sort_cost(n // 2) + n


for k in range(0, 21):
    n = 2**k
    assert merge_sort_cost(n) == n * k + n      # n log2 n + n
print("all tests passed")
```

## B.7 Amortized 分析

Amortized 分析回答的問題是：「某些操作偶爾很貴，但整串操作的總成本是多少？」常用的論證方式有兩種。**總量法（aggregate）**直接數整串操作的總工作量，例如「每個元素最多進出 stack 各一次」。**記帳法（accounting／potential）**想像每次便宜的操作多付一點「存款」，留給之後昂貴的操作使用，只要存款永不為負，總成本就被便宜操作的總付款限制住。面試中幾乎都用總量法，因為最容易說清楚。

| 例子 | 偶爾昂貴的操作 | 為什麼攤銷後便宜 | 結論 |
|---|---|---|---|
| 動態陣列 `append` | 擴容時複製全部 n 個元素 | 容量倍數成長，複製總數 1 + 2 + 4 + … < 2n | 每次攤銷 O(1) |
| Monotonic stack | 一次 `while` 可能 pop 很多個 | 每個元素最多 push 一次、pop 一次 | n 個元素總共 O(n) |
| Monotonic deque | 一次加入可能從尾端移除很多個 | 同上，每個元素進出各一次 | 總共 O(n) |
| Sliding window | 內層 `while` 一次縮很多格 | 左指標從不後退，總移動 ≤ n | 總共 O(n) |
| 兩個 stack 模擬 queue | 輸出 stack 空了，要整個倒過來 | 每個元素最多被搬一次 | 每次攤銷 O(1) |
| Union-Find | 某次 find 走很長的路 | path compression 讓走過的路變短，之後不再付這筆成本 | 攤銷 O(α(n)) |
| KMP 建 failure function | 內層 `while` 一次退很多步 | 長度每次最多加 1，退的總步數 ≤ 加的總步數 | 總共 O(m) |

**動態陣列的細節。** 關鍵是**倍數**成長（CPython 實際的成長比例小於 2 倍，但仍是固定比例，結論相同）。若每次只多配置固定的 c 格，n 次 append 的複製總數是 c + 2c + 3c + … ≈ n²/(2c)，攤銷變成 O(n)。這也是為什麼不要自己用「每次加一格」的方式模擬可變長度陣列。

**Monotonic stack 的細節。** 第 3 章 3.4 節有完整的逐步追蹤。講解時的句型是：「內層 while 雖然一次可能 pop 很多，但每個索引只會被 push 一次、pop 一次，所以 push 與 pop 的總次數不超過 2n。」

**Union-Find 的細節。** 只用 union by rank 時，樹高不超過 log n，所以每次 O(log n)，這是**最壞情況**而非攤銷。加上 path compression 之後才變成攤銷 O(α(n))；α(n) 是反 Ackermann 函數，在任何實際的 n 下都不超過 4。有一個常見的追問：如果要支援「撤銷上一次 union」（rollback），就不能用 path compression，因為它會改動很多節點、無法便宜地復原，只能保留 union by rank，每次 O(log n)。

攤銷保證的是「整串操作」的總成本，所以有兩個限制要知道。第一，它不保證單次操作快：對延遲敏感的情境（例如每次回應都有時間上限），單次 O(n) 的擴容仍可能是問題。第二，如果有辦法讓昂貴操作反覆發生，攤銷論證就不成立：例如動態陣列若在「剛好滿」與「剛好一半」之間反覆 append、pop，且一縮到一半就立刻縮小容量，每次都會觸發複製；實作上會等到剩四分之一才縮小，來避免這種震盪。

## B.8 空間複雜度與遞迴 stack

空間複雜度通常指**額外空間（auxiliary space）**：除了輸入本身與題目要求的輸出之外，演算法另外用了多少記憶體。說的時候要講清楚是否把輸出算進去，例如「不計輸出的 O(n·2ⁿ) 個子集，額外空間是 O(n) 的遞迴深度與目前路徑」。如果原地修改輸入（例如把走過的格子改成 `#`），額外空間可以說是 O(1)，但要主動提到「這會修改輸入，如果不允許就要用 visited set，空間變成 O(m·n)」。

**遞迴的 stack 空間等於最大遞迴深度乘上每層的空間**，常被忽略：

| 情況 | 遞迴深度 | 額外空間 |
|---|---|---|
| 平衡二元樹的 DFS | O(log n) | O(log n) |
| 一般二元樹的 DFS | O(h)，最壞（退化成鏈）O(n) | O(h) |
| 格子圖的遞迴 DFS | 最壞 O(m·n)（蛇形路徑） | O(m·n) |
| Backtracking（子集、排列） | O(n) | O(n)，不含輸出 |
| 記憶化遞迴 | 最壞為最長的依賴鏈 | 狀態數（cache）＋ 遞迴深度 |
| Quicksort | 平均 O(log n)，最壞 O(n) | 先遞迴較小的一半、較大的一半用迴圈，可保證 O(log n) |
| Merge sort（陣列） | O(log n) | O(n) 的合併暫存 ＋ O(log n) stack |

**Python 的遞迴深度限制。** CPython 預設的遞迴上限是 1000 層（可用 `sys.getrecursionlimit()` 查看），超過會丟出 `RecursionError`。用 `sys.setrecursionlimit` 調高可以解決部分情況，但遞迴太深仍可能耗盡底層的 C stack 而讓程式崩潰。所以只要遞迴深度可能到 10⁴ 以上（退化成鏈的樹、10⁵ 個節點的圖、長度 10⁵ 的記憶化遞迴），面試中最穩妥的說法是：「遞迴版比較好讀，但深度可能到 n，Python 的遞迴上限會是問題，所以我改用顯式的 stack。」

**切片與複製造成的隱藏空間。** 遞迴時傳入 `nums[1:]` 或 `path + [x]`，每一層都會複製一份，時間與空間都多乘上一個 O(n)。例如用 `helper(nums[1:])` 遞迴走完一個陣列，總複製量是 n + (n−1) + … = O(n²)。改成傳索引 `helper(i + 1)`、用同一個 `path` 加入再撤回，就能避免。

**DP 的空間優化。** 若 `dp[i]` 只依賴 `dp[i−1]`、`dp[i−2]`，可以只留兩個變數，O(n) 變 O(1)；若二維 `dp[i][j]` 只依賴上一列與同一列，可以用一維陣列滾動，O(m·n) 變 O(n)。代價是無法再回溯重建完整的解，如果題目要輸出方案本身（而不只是最佳值），通常要保留完整表格或另存選擇。

下面的程式示範遞迴深度的問題：一條長度 10⁵ 的鏈，遞迴版會碰到上限，顯式 stack 版不會。

```python
def depth_recursive(nxt: list[int], u: int) -> int:
    """nxt[u] 是 u 的下一個節點，-1 代表結尾；回傳從 u 開始的鏈長。"""
    return 1 if nxt[u] == -1 else 1 + depth_recursive(nxt, nxt[u])


def depth_iterative(nxt: list[int], u: int) -> int:
    length = 0
    while u != -1:
        length += 1
        u = nxt[u]
    return length


n = 10**5
chain = list(range(1, n)) + [-1]          # 0 -> 1 -> ... -> n-1

assert depth_iterative(chain, 0) == n
assert depth_iterative([-1], 0) == 1
short = list(range(1, 500)) + [-1]           # 短鏈遞迴沒問題
assert depth_recursive(short, 0) == 500

try:
    depth_recursive(chain, 0)
    raised = False
except RecursionError:
    raised = True
assert raised                              # 預設上限 1000 層，10^5 層一定超過
print("all tests passed")
```

## B.9 看起來 O(n²) 其實 O(n)，以及反過來的陷阱

判斷複雜度時，不要只看迴圈的層數，而要問「每個元素總共被處理幾次」。下表的程式都有兩層迴圈或巢狀的 while，但總工作量是線性或接近線性。

| 情況 | 看起來 | 實際 | 為什麼 | 本書章節 |
|---|---|---|---|---|
| Sliding window 的內層 `while` 縮窗口 | O(n²) | O(n) | 左右指標都只往右，各移動最多 n 次 | 6 |
| Monotonic stack／deque 的內層 `while` pop | O(n²) | O(n) | 每個元素 push、pop 各最多一次 | 6、10 |
| Two pointers 從兩端收斂 | O(n²) | O(n) | 每一步至少一個指標前進，總步數 ≤ n | 5 |
| Longest Consecutive Sequence：只從序列起點往上數 | O(n²) | O(n) | 只有 `x − 1` 不在 set 中的 x 才開始數，每個數只被數到一次 | 4 |
| 格子 BFS／DFS：對每格呼叫一次搜尋 | O((m·n)²) | O(m·n) | visited 讓每格只被展開一次 | 15 |
| `heapq.heapify` | O(n log n) | O(n) | 大部分節點在底層，下沉距離很短，總和 Σ(n/2ʰ⁺¹)·h = O(n) | 14 |
| KMP 建 failure function 的內層 `while` | O(m²) | O(m) | 匹配長度每步最多加 1，退回的總量不超過加上的總量 | 25 |
| Z-algorithm、Manacher | O(n²) | O(n) | 右邊界只往右推，每個位置的擴展會推進右邊界 | 25 |
| 樹上對每個節點做 DFS 回傳子樹資訊 | O(n²) | O(n) | 每個節點只被自己的父節點呼叫一次 | 12 |
| Union-Find 對每條邊做 find | O(E·n) | O(E·α(n)) | path compression 攤銷 | 17 |
| 枚舉每個 i 的倍數 j = i, 2i, 3i… | O(n²) | O(n log n) | n/1 + n/2 + … + n/n 是調和級數 | 3、28 |
| 迴圈 26 次（字母表）× n | O(n²)？ | O(n) | 26 是常數；但要主動說出「O(26·n)，字元集大小視為常數」 | 4、6 |

反過來，也有很多寫法**看起來 O(n)，實際上是 O(n²)**，這是 Python 面試中最常見的失分點之一：

| 寫法 | 看起來 | 實際 | 修正 |
|---|---|---|---|
| 迴圈中 `queue.pop(0)` | O(n) | O(n²) | 用 `collections.deque.popleft()` |
| 迴圈中 `a.insert(0, x)` | O(n) | O(n²) | 用 deque 的 `appendleft`，或最後反轉一次 |
| 迴圈中 `if x in some_list` | O(n) | O(n²) | 先轉成 set |
| 迴圈中 `res += s`（字串） | O(n) | 最壞 O(n²) | 收集到 list，最後 `"".join` |
| 遞迴傳 `nums[1:]`、`s[i:]` | O(n) | O(n²) | 傳索引 |
| 每個節點複製 `path[:]` 或 `path + [x]` | O(節點數) | O(節點數 × 路徑長) | 加入、遞迴、撤回；只在葉子複製 |
| 迴圈中 `sorted(window)` 或 `max(window)` | O(n) | O(n·k log k) 或 O(n·k) | heap、monotonic deque 或計數陣列 |
| 迴圈中 `sum(a[i:j])` | O(n) | O(n·k) | prefix sum |
| 迴圈中 `a.index(x)`、`a.remove(x)` | O(n) | O(n²) | 用 dict 記錄位置 |
| 把長度 L 的 tuple 或字串當 dict key | O(n) | O(n·L) | 這通常可以接受，但要把 L 寫進複雜度 |

下面的程式用計數驗證 Longest Consecutive Sequence（第 4 章核心題 3）的線性論證：雖然 `for` 裡面有 `while`，內層總共只會走 n 步。

```python
def longest_consecutive(nums: list[int]) -> tuple[int, int]:
    """回傳 (最長連續序列長度, 內層 while 的總步數)。"""
    seen = set(nums)
    best = inner_steps = 0
    for x in seen:
        if x - 1 in seen:          # 不是序列起點，跳過
            continue
        length = 1
        while x + length in seen:  # 只有起點才往上數
            length += 1
            inner_steps += 1
        best = max(best, length)
    return best, inner_steps


assert longest_consecutive([100, 4, 200, 1, 3, 2]) == (4, 3)
assert longest_consecutive([]) == (0, 0)
assert longest_consecutive([7, 7, 7]) == (1, 0)

n = 10**5
best, steps = longest_consecutive(list(range(n, 0, -1)))   # 一整條長序列
assert best == n and steps == n - 1                        # 內層總步數是 n-1，不是 n^2
print("all tests passed")
```

## B.10 面試中講複雜度的句型

講複雜度時，面試官想聽的不只是答案，而是**理由**與**瓶頸**。好的說法有三個要素：先定義變數，再說時間與空間各是多少，最後指出主導成本的那一步。如果有取捨（更快但更耗空間、平均快但最壞慢），主動說出來。下面的句型可以直接套用，把括號中的內容換成你的題目。

**基本句型：定義變數、說結論、指出瓶頸。**
- 「設 n 是陣列長度。時間是 O(n log n)，瓶頸在排序；排序後的掃描只有 O(n)。空間是 O(n)，來自排序產生的新陣列。」
- 「設 m、n 是兩個字串的長度。DP 有 m·n 個狀態，每個狀態 O(1) 轉移，所以時間 O(m·n)。因為每一列只依賴上一列，空間可以壓到 O(min(m, n))。」
- 「格子是 m × n，每格最多被放進佇列一次，每次檢查 4 個鄰居，所以時間與空間都是 O(m·n)。」

**解釋看起來多一層、實際上線性的程式。**
- 「這裡雖然有一個 for 包著 while，但 left 只會往右走、最多走 n 步，所以兩個指標加起來總共 O(n)。」
- 「每個索引只會被 push 一次、pop 一次，所以整個 monotonic stack 是 O(n)，平均每個元素 O(1) amortized。」

**區分 worst、average 與 amortized。**
- 「dict 的查詢平均 O(1)；最壞情況下碰撞嚴重會退化成 O(n)，但在一般輸入下不會發生。」
- 「我用隨機 pivot 的 quickselect，期望時間 O(n)，最壞 O(n²)。如果需要最壞情況的保證，可以改用大小為 k 的 heap，O(n log k)。」
- 「Union-find 加上 path compression 和 union by rank，每次操作攤銷 O(α(n))，實務上可以當成常數。」

**連結 constraints 與做法。**
- 「n 到 10⁵，O(n²) 會是 10¹⁰ 次操作，一定太慢，所以我需要 O(n log n) 以內的做法。」
- 「n 只有 20，2²⁰ 大約一百萬，所以枚舉所有子集是可行的。」
- 「答案的範圍到 10⁹，但判定一個值是否可行只要 O(n)，所以對答案 binary search 是 O(n log 10⁹)，大約 30n。」

**說明圖演算法與字串演算法。**
- 「Dijkstra 用 binary heap，每條邊最多讓一個項目進 heap，所以是 O((V + E) log V)，空間 O(V + E)。」
- 「建 trie 的成本是所有單字的總長度；每次查詢是 O(L)，和字典大小無關。」
- 「KMP 的預處理 O(m)，比對 O(n)，合計 O(n + m)，不會像暴力法退化成 O(n·m)。」

**說明空間時把遞迴 stack 算進去。**
- 「除了輸出之外，額外空間是遞迴深度 O(h)；如果樹退化成鏈，最壞是 O(n)。在 Python 中深度太大會超過遞迴上限，所以如果 n 到 10⁵，我會改成迭代版。」
- 「我直接把走過的格子改成 0 來標記，額外空間是 O(1)，不計遞迴 stack；如果不允許修改輸入，就需要 O(m·n) 的 visited。」

**回應「能不能更快」。**
- 「至少要讀過每個元素一次，所以 O(n) 已經是下限。」
- 「題目要求列出所有排列，輸出本身就有 n! 個、每個長度 n，所以 O(n·n!) 不可能再降低。」
- 「這是比較式排序的問題，下限是 Ω(n log n)；但數值範圍只有 10⁴，可以用 counting sort 做到 O(n + U)。」

要避免的說法也有幾種：只說「很快」「大概線性」而不給出 Big-O；忘記定義 n 就說「O(n)」，而題目其實有兩個長度；把 hash table 的 O(1) 說成絕對保證；忽略字串操作、切片、tuple key 的 O(L) 成本；以及說出空間 O(1) 卻用了遞迴。這些在 senior 等級的面試中都會被追問，事先講清楚比被追問後才修正好得多。
