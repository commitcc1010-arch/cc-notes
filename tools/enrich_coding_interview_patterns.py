#!/usr/bin/env python3
"""Add a visual learning layer and deeper follow-ups to all 160 problems.

The original problem statements, explanations, and code remain authoritative.
This script adds a consistent teaching layer around them:

* what the interviewer is actually testing;
* a visual flow from brute force to the maintained state;
* a five-step derivation and a proof skeleton;
* edge cases and a one-sentence memory hook;
* three additional, folded follow-ups about changed constraints,
  answer reconstruction, and production/online requirements.

The generated regions are delimited by HTML comments, so the script is
idempotent and can be rerun after editing the original solutions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PATTERN_DIR = ROOT / "Coding Interview Patterns" / "Patterns"
QUESTION_RE = re.compile(
    r"(?ms)^## (?P<kind>核心題|難題) (?P<number>\d+)：(?P<title>[^\n]+)\n"
    r"(?P<body>.*?)"
    r"(?=^## (?:核心題|難題) \d+：|^# 上限題|^## 本章檢查|\Z)"
)
LEARNING_RE = re.compile(
    r"\n?<!-- deep-learning:start -->.*?<!-- deep-learning:end -->\n?",
    re.S,
)
FOLLOWUPS_RE = re.compile(
    r"\n?<!-- deep-followups:start -->.*?<!-- deep-followups:end -->\n?",
    re.S,
)


@dataclass(frozen=True)
class Guide:
    name: str
    brute_force: str
    state: str
    transition: str
    invariant: str
    proof: str
    edges: str
    failure: str
    alternative: str
    witness: str
    production: str


GUIDES = {
    "01": Guide(
        "Hashing、計數與 canonical representation",
        "對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題",
        "hash table：canonical key → 已處理資料的最小充分摘要",
        "由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要",
        "處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key",
        "證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。",
        "重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable",
        "key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。",
        "可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。",
        "在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。",
        "線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。",
    ),
    "02": Guide(
        "Two Pointers 與單調淘汰",
        "枚舉所有 index pair 或每次移動一端後重新掃描另一端",
        "兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區",
        "依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選",
        "指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案",
        "每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。",
        "重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值",
        "若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。",
        "可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。",
        "保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。",
        "Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。",
    ),
    "03": Guide(
        "Sliding Window 與可逆的區間狀態",
        "枚舉所有連續區間，並對每個區間重新計算是否合法",
        "window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count",
        "右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻",
        "每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案",
        "證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。",
        "空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index",
        "若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。",
        "改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。",
        "最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。",
        "Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。",
    ),
    "04": Guide(
        "Prefix Summary、Difference Array 與離線聚合",
        "對每個 query 或每個區間重新走訪所有元素",
        "prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件",
        "把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原",
        "prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部",
        "由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。",
        "prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移",
        "若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。",
        "改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。",
        "保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。",
        "大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。",
    ),
    "05": Guide(
        "Binary Search on Boundary／Answer",
        "逐一測試每個 index 或答案值，直到找到第一個可行者",
        "一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF",
        "測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍",
        "真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False",
        "先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。",
        "空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度",
        "若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。",
        "改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。",
        "找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。",
        "Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。",
    ),
    "06": Guide(
        "Sorting、Intervals 與 Sweep Line",
        "逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件",
        "依 start/end 排序後的事件流，加上目前 active intervals 的摘要",
        "掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案",
        "掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間",
        "排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。",
        "端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序",
        "若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。",
        "改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。",
        "合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。",
        "Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。",
    ),
    "07": Guide(
        "Stack、Monotonic Stack 與延後決策",
        "對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構",
        "stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序",
        "新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區",
        "stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選",
        "證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。",
        "相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator",
        "若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。",
        "改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。",
        "stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。",
        "超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。",
    ),
    "08": Guide(
        "Linked List 指標重接與局部不變量",
        "為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理",
        "少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap",
        "先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結",
        "已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達",
        "以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。",
        "空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer",
        "若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。",
        "可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。",
        "回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。",
        "Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。",
    ),
    "09": Guide(
        "Binary Tree Traversal 與子樹資訊合併",
        "對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑",
        "DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要",
        "選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果",
        "函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解",
        "以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。",
        "空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設",
        "若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。",
        "可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。",
        "保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。",
        "大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。",
    ),
    "10": Guide(
        "BST Order、Trie Prefix 與逐位決策",
        "忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串",
        "BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata",
        "BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進",
        "BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix",
        "BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。",
        "duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word",
        "BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。",
        "使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。",
        "BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。",
        "Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。",
    ),
    "11": Guide(
        "Heap、Top-K 與 K-way Merge",
        "反覆排序全部候選，或每次都線性尋找目前最小／最大值",
        "size-k heap 或由多條已排序序列各提供一個 frontier 的 heap",
        "加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列",
        "heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻",
        "證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。",
        "min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key",
        "需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。",
        "改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。",
        "heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。",
        "Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。",
    ),
    "12": Guide(
        "Graph DFS/BFS、State Graph 與最短步數",
        "從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態",
        "node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue",
        "從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier",
        "visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開",
        "可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。",
        "圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited",
        "若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。",
        "改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。",
        "保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。",
        "超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。",
    ),
    "13": Guide(
        "Topological Order、Union-Find 與 Weighted Shortest Path",
        "反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑",
        "依問題選 indegree queue、DSU parent/size，或 distance＋priority queue",
        "拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation",
        "已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短",
        "分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。",
        "重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry",
        "負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。",
        "改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。",
        "Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。",
        "動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。",
    ),
    "14": Guide(
        "Backtracking、Constraint Propagation 與搜尋樹剪枝",
        "生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支",
        "path（已做決定）、剩餘 choices、增量 constraint state",
        "選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝",
        "進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前",
        "以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。",
        "重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth",
        "若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。",
        "加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。",
        "path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。",
        "Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。",
    ),
    "15": Guide(
        "Greedy Choice、Exchange Argument 與可行區間",
        "枚舉所有決策序列或以 DP 保存每一步的所有歷史",
        "目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit",
        "每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要",
        "目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功",
        "使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。",
        "局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow",
        "找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。",
        "回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。",
        "保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。",
        "線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。",
    ),
    "16": Guide(
        "1D DP、有限狀態機與歷史壓縮",
        "枚舉所有決策序列，或為每個位置重算所有較早 prefix",
        "dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數",
        "列出最後一步選擇，從較小 prefix/state 轉移到目前狀態",
        "更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致",
        "以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。",
        "base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction",
        "狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。",
        "重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。",
        "保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。",
        "線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。",
    ),
    "17": Guide(
        "2D／Interval DP 與結構化子問題",
        "枚舉所有對齊、切點或操作序列，造成指數分支",
        "dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案",
        "依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間",
        "填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案",
        "依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。",
        "空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)",
        "若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。",
        "壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。",
        "保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。",
        "長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。",
    ),
    "18": Guide(
        "Bit Representation、數學分解與幾何事件",
        "逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係",
        "bit mask、位階貢獻、倍增量，或正規化幾何事件與座標",
        "把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積",
        "目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離",
        "由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。",
        "signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo",
        "固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。",
        "使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。",
        "保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。",
        "Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。",
    ),
    "19": Guide(
        "Data Structure Composition 與跨結構 invariant",
        "讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度",
        "一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access",
        "每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態",
        "每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證",
        "逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。",
        "容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為",
        "需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。",
        "改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。",
        "保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。",
        "併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。",
    ),
    "20": Guide(
        "Matrix Simulation、Parser 與精確狀態轉移",
        "直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence",
        "明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state",
        "把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token",
        "每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態",
        "用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。",
        "矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件",
        "規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。",
        "採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。",
        "記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。",
        "不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。",
    ),
}

FALLBACK_KNOWLEDGE = {
    "Valid Palindrome": (
        "忽略非英數字元與大小寫後，判斷字串是否為 palindrome。",
        "左右指標只停在有效字元；每次比較後同步向內移動，任何不相等都可立即判 False。",
    ),
    "Longest Substring Without Repeating Characters": (
        "求不含重複字元的最長連續 substring 長度。",
        "用 last_seen 記錄字元最新位置；right 前進時，left 直接跳到重複字元上次位置的下一格，但不能後退。",
    ),
    "Max Consecutive Ones III": (
        "最多把 k 個 0 改成 1，求最長連續 1 區間。",
        "window 只需維護其中 0 的數量；zeros > k 時收縮 left，重新合法後用 window 長度更新答案。",
    ),
    "Minimum Size Subarray Sum": (
        "在正整數陣列中找總和至少 target 的最短連續 subarray。",
        "正數保證右擴 sum 只增、左縮 sum 只減；每次 sum 達標就持續縮左端，找出該 right 的最短合法 window。",
    ),
    "Find First and Last Position": (
        "在排序陣列中找 target 的第一與最後位置，不存在回傳 [-1,-1]。",
        "分別找第一個 >= target 的位置與第一個 > target 的位置；答案是 left 與 right-1，而不是命中後向兩側線性掃描。",
    ),
    "Koko Eating Bananas": (
        "求能在 h 小時內吃完所有香蕉的最小整數速度。",
        "速度越大，所需時數單調不增；以 feasible(k)=總時數<=h 搜尋第一個 True，範圍為 1 到最大 pile。",
    ),
    "Merge Intervals": (
        "合併所有重疊區間並回傳互不重疊、依起點排序的結果。",
        "先按 start 排序；若下一段 start <= 已合併尾段 end 就延長 end，否則尾段已不可能再被未來區間碰到，可安全輸出。",
    ),
    "Insert Interval": (
        "在已排序且互不重疊的區間中插入一段新區間，維持同樣性質。",
        "依序分成完全在新區間左側、與新區間重疊、完全在右側三段；中間重疊區只需累積 min start 與 max end。",
    ),
    "Valid Parentheses": (
        "判斷括號字串是否每個 opening bracket 都以正確種類與巢狀順序關閉。",
        "stack 保存尚未匹配的 opening brackets；遇 closing bracket 時，它只能匹配 stack top，最後 stack 必須為空。",
    ),
    "Daily Temperatures": (
        "對每一天找右側第一個更高溫度的距離，若不存在則為 0。",
        "monotonic decreasing stack 保存尚未找到更高溫的 indices；新溫度較高時依序 pop，當下 index 就是被 pop 日子的第一個答案。",
    ),
    "Reverse Linked List": (
        "將 singly linked list 原地反轉並回傳新 head。",
        "每輪先保存 next_node，再把 current.next 指向 prev；完成後 prev 是反轉區段的新 head，current 是尚未處理區段。",
    ),
    "Remove Nth Node From End": (
        "刪除 linked list 倒數第 n 個節點並回傳 head。",
        "dummy 消除刪 head 特例；fast 先走 n+1 步，再讓 fast/slow 同速前進，fast 到尾時 slow 正好在待刪節點前一格。",
    ),
    "Balanced Binary Tree": (
        "判斷每個節點的左右子樹高度差是否都不超過 1。",
        "postorder 一次同時算高度與合法性；用 -1 作為不平衡 sentinel，child 一旦回傳 -1 就立即向上傳播。",
    ),
    "Lowest Common Ancestor": (
        "在 binary tree 中找兩個指定節點的 lowest common ancestor。",
        "postorder 回傳 subtree 是否找到 p 或 q；若左右各找到一個，或目前節點本身是其中之一且另一個在 child，當前節點就是 LCA。",
    ),
    "Binary Tree Level Order Traversal": (
        "依深度由上到下、每層由左到右輸出 binary tree。",
        "BFS 每輪先記錄 queue 長度，這個固定長度就是本層節點數；處理時加入 children，但不讓它們混入本層輸出。",
    ),
    "Validate Binary Search Tree": (
        "判斷 binary tree 是否滿足嚴格 BST ordering。",
        "每個節點都繼承 ancestor 給的合法開區間 (low, high)；只比較 parent 不夠，因為右子樹深處仍受 root 下界限制。",
    ),
    "Kth Smallest in BST": (
        "找 BST 中第 k 小的值。",
        "BST inorder 產生遞增序列；走到第 k 個 visited node 即可停止。若有 subtree size metadata，可按左子樹大小做 rank selection。",
    ),
    "Implement Trie": (
        "支援 insert、完整 word search 與 prefix search。",
        "每個 node 代表一個 prefix；children edge 消耗一個字元，terminal flag 區分完整 word 與只有共同 prefix。",
    ),
    "Kth Largest Element": (
        "找未排序陣列中的第 k 大元素。",
        "維持 size k 的 min heap：root 是目前看過元素中的第 k 大門檻；新元素進 heap 後若超過 k，就淘汰最小者。",
    ),
    "Top K Frequent Elements": (
        "回傳出現頻率最高的 k 個不同元素。",
        "先用 hash 計頻率，再用 size-k heap、bucket by frequency 或 quickselect 選出 top k；核心是比較 distinct keys 而非原陣列元素。",
    ),
    "Find Median from Data Stream": (
        "支援持續加入數字，並隨時回傳目前 median。",
        "max heap 保存較小一半、min heap 保存較大一半；兩邊大小差不超過 1，且 lower 的每個值不大於 upper。",
    ),
    "Number of Islands": (
        "計算 0/1 grid 中四方向相連的陸地 connected components 數。",
        "每遇到未訪問陸地就發現一個新 component，答案加一，再用 DFS/BFS 標記整座 island，避免之後重複計數。",
    ),
    "Clone Graph": (
        "深拷貝一個可能含 cycle 的 graph。",
        "map old_node→new_node 同時負責 identity preservation 與 visited；第一次看到節點就先建立 clone，再遞迴／迭代連接 neighbors。",
    ),
    "Rotting Oranges": (
        "每分鐘 rotten orange 同時感染相鄰 fresh orange，求全部感染的最少時間。",
        "multi-source BFS 把所有初始 rotten oranges 同時入 queue；每一層代表一分鐘，並用 fresh count 判斷是否仍有不可達橘子。",
    ),
    "Course Schedule": (
        "判斷 directed prerequisite graph 是否無 cycle，亦即能否完成所有課程。",
        "Kahn topological sort 從 indegree 0 課程開始；每移除一門課就降低後繼 indegree，最後處理數等於 V 才代表沒有 cycle。",
    ),
    "Redundant Connection": (
        "找出在 tree 上額外加入、因而形成 cycle 的那條 undirected edge。",
        "依輸入順序 union endpoints；若兩端在加入前已有同一 root，這條 edge 連接同一 component，正是造成 cycle 的 redundant edge。",
    ),
    "Network Delay Time": (
        "在非負權 directed graph 中，求 source 的訊號到達所有節點的最長最短路徑。",
        "Dijkstra 每次 settle 目前距離最小的節點並 relax outgoing edges；所有節點最短距離的最大值就是廣播完成時間。",
    ),
    "Subsets": (
        "列出陣列的所有 subsets。",
        "決策樹每個 index 只有選與不選兩條分支；path 表示前 i 個元素的決策，走到 n 時恰得到一個 subset。",
    ),
    "Combination Sum": (
        "找可重複使用候選數字、總和為 target 的所有組合。",
        "依 index 限制後續只能選目前或更右的候選以避免 permutation duplicates；remaining 變負時剪枝，變 0 時收集 path。",
    ),
    "N-Queens": (
        "在 n×n 棋盤放 n 個 queens，使任兩者不共享 row、column 或 diagonal。",
        "逐 row 放一個 queen；columns、row-col 與 row+col 三個 set 能 O(1) 判斷衝突，離開分支時必須完整 restore。",
    ),
    "Jump Game": (
        "判斷從 index 0 能否到達最後 index。",
        "掃描時維護目前所有可達位置能延伸到的 farthest；若 i>farthest 代表 frontier 已斷裂，否則用 i+nums[i] 擴張。",
    ),
    "Gas Station": (
        "找一個起點，使車繞環狀加油站一圈不會缺油。",
        "總油量不足則無解；掃描中 current tank 一旦為負，先前區間內任何站都不能作起點，因此下一站成為新候選。",
    ),
    "Task Scheduler": (
        "安排含 cooldown n 的 tasks，求完成全部工作的最短時間。",
        "瓶頸由最高頻 task 建立的 frame 決定；答案至少是 (maxFreq-1)(n+1)+並列最高頻 task 數，也不能小於 tasks 總數。",
    ),
    "Maximum Subarray": (
        "求連續 subarray 的最大總和。",
        "Kadane 的 current 表示必須以目前位置結尾的最佳和；若先前和為負就捨棄，best 則保存所有結尾位置的最大值。",
    ),
    "House Robber": (
        "相鄰房屋不可同時選，求可取得的最大金額。",
        "處理到 i 時只有 rob i（接 i-2）或 skip i（沿用 i-1）兩種互斥最後決策，因此只需保存前兩個 DP 值。",
    ),
    "Coin Change": (
        "使用可重複硬幣組成 amount，求最少硬幣數。",
        "dp[x] 是湊出金額 x 的最少枚數；最後一枚若為 coin，前驅是 dp[x-coin]，對所有 coin 取最小並以 infinity 表示不可達。",
    ),
    "Longest Common Subsequence": (
        "求兩字串不必連續但保持相對順序的最長共同 subsequence 長度。",
        "dp[i][j] 表示 a[:i] 與 b[:j] 的 LCS；末字元相同走 diagonal+1，不同則丟棄其中一個末字元並取上、左較大值。",
    ),
    "Edit Distance": (
        "允許 insert、delete、replace，求把字串 a 轉成 b 的最少操作數。",
        "dp[i][j] 比較兩個 prefix；末字元相同沿用 diagonal，否則從刪除、插入、替換三個前驅取最小再加一。",
    ),
    "Partition Equal Subset Sum": (
        "判斷正整數陣列能否分成總和相同的兩個 subsets。",
        "總和必須為偶數，問題化為 0/1 subset sum target=sum/2；容量由大到小更新，確保每個數只使用一次。",
    ),
    "Single Number": (
        "除了某元素出現一次，其餘皆出現兩次，找唯一元素。",
        "利用 x^x=0、x^0=x 與 XOR 的交換結合律；把所有元素 XOR 後，成對元素互相抵消，只剩 single number。",
    ),
    "Counting Bits": (
        "對 0..n 每個整數計算二進位 1 的數量。",
        "去掉最低 set bit 得到 i&(i-1)，因此 bits[i]=bits[i&(i-1)]+1；或用 bits[i>>1]+(i&1)。",
    ),
    "Pow(x, n)": (
        "在 O(log |n|) 時間計算 x 的整數次方。",
        "binary exponentiation 依 n 的 bits 決定是否把目前 base 乘進答案；每輪 base 平方、exponent 右移，負指數先取倒數。",
    ),
    "Time Based Key-Value Store": (
        "支援依遞增 timestamp 寫入，並查詢不超過指定時間的最新 value。",
        "每個 key 對應一條按 timestamp 排序的 history；set 直接 append，get 用 upper_bound 找第一個 >t 的位置再退一格。",
    ),
    "Insert Delete GetRandom O(1)": (
        "支援平均 O(1) insert、remove 與均勻 random sample。",
        "array 提供 O(1) random index，map 提供 value→index；刪除時把尾元素 swap 到洞的位置，再 pop 並同步 map。",
    ),
    "LFU Cache": (
        "固定容量 cache 依最低使用頻率淘汰，頻率相同時淘汰最久未使用者。",
        "key map 定位 value/frequency；frequency buckets 內維持 LRU，min_freq 直接指向淘汰 bucket，touch 只移到相鄰頻率。",
    ),
    "All O`one Data Structure": (
        "支援 key 計數增減與 O(1) 取得任一最大／最小計數 key。",
        "依 count 排序的 doubly linked bucket list，加上 key→bucket；key 每次只移到相鄰 count，空 bucket 立即移除。",
    ),
    "Spiral Matrix": (
        "依順時針 spiral order 輸出矩陣所有元素。",
        "維護 top/bottom/left/right 四邊界；走完一條邊立即內縮，走 bottom 與 left 前重新檢查邊界避免重複。",
    ),
    "Set Matrix Zeroes": (
        "若某格為 0，將其整個 row 與 column 設為 0，要求 O(1) 額外空間。",
        "用第一 row/column 當 marker 儲存哪些列欄需清零，另以兩個 flag 保存第一 row/column 自己原本是否含 0。",
    ),
    "Rotate Image": (
        "將 n×n matrix 原地順時針旋轉 90 度。",
        "先沿主對角線 transpose，再反轉每一 row；座標 (r,c) 因而映射到 (c,n-1-r)，且每步都可原地完成。",
    ),
}


def compact_plain(text: str, limit: int = 220) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"^>\s*\[![^\]]+\].*$", " ", text, flags=re.M)
    text = re.sub(r"^>\s?", "", text, flags=re.M)
    text = re.sub(r"\[\[([^]|#]+)(?:#[^]|]+)?(?:\|([^]]+))?\]\]",
                  lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`#|]", "", text)
    text = re.sub(r"^\s*[-+]\s+", "", text, flags=re.M)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def subsection(body: str, names: tuple[str, ...]) -> str:
    pattern = "|".join(re.escape(name) for name in names)
    match = re.search(
        rf"(?ms)^### (?:{pattern})\s*\n(?P<text>.*?)(?=^### |\Z)",
        body,
    )
    return match.group("text") if match else ""


def first_prose_block(text: str) -> str:
    text = re.split(
        r"(?m)^```|^\s*-\s*(?:時間|空間|每個操作|Feed|發文)|^>\s*\[!",
        text,
        maxsplit=1,
    )[0]
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    return blocks[0] if blocks else ""


def extract_goal(title: str, body: str) -> str:
    goal = compact_plain(first_prose_block(subsection(body, ("題目",))))
    if goal:
        return goal
    if title in FALLBACK_KNOWLEDGE:
        return FALLBACK_KNOWLEDGE[title][0]
    prefix = re.split(r"(?m)^### |^```", body, maxsplit=1)[0]
    goal = compact_plain(prefix)
    return goal or "依題目定義計算正確結果，並滿足指定時間與空間限制。"


def extract_insight(title: str, body: str, guide: Guide) -> str:
    insight = compact_plain(
        first_prose_block(subsection(body, ("推導", "解法", "詳解"))),
        300,
    )
    if insight:
        return insight
    if title in FALLBACK_KNOWLEDGE:
        return FALLBACK_KNOWLEDGE[title][1]
    return (
        f"把題目轉成「{guide.state}」，再用「{guide.transition}」逐步縮小或組合答案。"
    )


def extract_complexity(body: str) -> str:
    lines = []
    for line in body.splitlines():
        if re.match(r"^\s*-\s*(時間|空間|每個操作|Feed|發文)", line):
            lines.append(compact_plain(line, 120))
    return "；".join(lines[:3]) or "以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。"


def quote_callout(kind: str, title: str, paragraphs: list[str], folded: bool = True) -> str:
    marker = "-" if folded else ""
    lines = [f"> [!{kind}]{marker} {title}"]
    for paragraph in paragraphs:
        lines.append(">")
        for line in paragraph.splitlines():
            lines.append(f"> {line}" if line else ">")
    return "\n".join(lines)


def visual(title: str, insight: str, guide: Guide) -> str:
    return "\n".join([
        f"題目：{title}",
        "      │",
        f"      ├─ 暴力路線：{guide.brute_force}",
        "      │",
        "      ▼  找出本題最關鍵的轉換",
        f"核心觀察：{insight}",
        "      │",
        f"Pattern toolbox：{guide.state}",
        "      │",
        f"      ├─ 狀態轉移：{guide.transition}",
        "      │",
        f"      ├─ 永遠成立：{guide.invariant}",
        "      │",
        "      ▼",
        "在狀態足以回答題目時更新／輸出答案",
    ])


def learning_block(title: str, body: str, guide: Guide) -> str:
    goal = extract_goal(title, body)
    insight = extract_insight(title, body, guide)
    complexity = extract_complexity(body)
    overview = quote_callout(
        "abstract",
        "這題真正考什麼",
        [
            f"**題目目標：** {goal}",
            f"**核心轉換：** {insight}",
            f"**主要知識點：** {guide.name}。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。",
        ],
        folded=False,
    )
    proof = quote_callout(
        "success",
        "正確性證明骨架",
        [
            f"1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「{guide.invariant}」的 base case。",
            f"2. **維持：** 每次執行「{guide.transition}」後，狀態仍與已處理資料一致。關鍵論證是：{guide.proof}",
            "3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。",
        ],
        folded=True,
    )
    edge = quote_callout(
        "warning",
        "最容易錯的地方",
        [
            f"優先手算並測試：{guide.edges}。",
            "不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。",
        ],
        folded=True,
    )
    memory = (
        f"先說清楚「{guide.state}」代表什麼，再說每一步如何「{guide.transition}」。"
        "只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。"
    )
    return f"""<!-- deep-learning:start -->
{overview}

### 視覺化題解：從暴力到最佳模型

```text
{visual(title, insight, guide)}
```

### 五步推導

1. **重述輸出：** {goal}
2. **寫出暴力：** {guide.brute_force}。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** {insight}
4. **定義 state 與轉移：** 使用「{guide.state}」承載上述觀察，再執行「{guide.transition}」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：{complexity}

> [!tip] 一句話記憶
> {memory}

{proof}

{edge}
<!-- deep-learning:end -->
"""


def followup_block(title: str, goal: str, insight: str, guide: Guide) -> str:
    contract = goal.rstrip("。！？.!?")
    changed_constraints = quote_callout(
        "question",
        f"Follow-up 2：如果《{title}》的 constraints 改變，原方法何時會失效？",
        [
            "**答案：先指出失效的假設，而不是立刻換資料結構。**",
            f"目前解法依賴的核心是：{insight} 失效情境包括：{guide.failure}",
            f"替代路線是：{guide.alternative} 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。",
        ],
        folded=True,
    )
    reconstruction = quote_callout(
        "question",
        "Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？",
        [
            "**答案：把 reconstruction 資訊視為 state 的一部分。**",
            f"針對這個 pattern，典型做法是：{guide.witness}",
            f"套回《{title}》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。",
        ],
        folded=True,
    )
    production = quote_callout(
        "question",
        "Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？",
        [
            "**答案：先保護 invariant，再談擴充。**",
            f"{guide.production}",
            f"此外必須把《{title}》目前隱含的前提寫成 contract：{contract}。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。",
        ],
        folded=True,
    )
    return (
        "<!-- deep-followups:start -->\n"
        + changed_constraints
        + "\n\n"
        + reconstruction
        + "\n\n"
        + production
        + "\n<!-- deep-followups:end -->\n"
    )


def insert_before_solution(body: str, block: str) -> str:
    match = re.search(r"(?m)^### (?:推導|解法|詳解)\s*$", body)
    if match:
        return (
            body[: match.start()].rstrip()
            + "\n\n"
            + block.strip()
            + "\n\n"
            + body[match.start():].lstrip()
        )
    code = re.search(r"(?m)^```", body)
    if code:
        return (
            body[: code.start()].rstrip()
            + "\n\n"
            + block.strip()
            + "\n\n"
            + body[code.start():].lstrip()
        )
    followup = re.search(r"(?m)^### Follow-up", body)
    if followup:
        return (
            body[: followup.start()].rstrip()
            + "\n\n"
            + block.strip()
            + "\n\n"
            + body[followup.start():].lstrip()
        )
    return block.strip() + "\n\n" + body.lstrip()


def append_followups(body: str, block: str) -> str:
    trailing_rule = re.search(r"\n---\s*$", body)
    if trailing_rule:
        return (
            body[: trailing_rule.start()].rstrip()
            + "\n\n"
            + block.strip()
            + "\n"
            + body[trailing_rule.start():]
        )
    return body.rstrip() + "\n\n" + block.strip() + "\n"


def enrich_question(match: re.Match[str], guide: Guide) -> str:
    kind = match.group("kind")
    number = match.group("number")
    title = match.group("title").strip()
    body = match.group("body")
    body = LEARNING_RE.sub("\n", body)
    body = FOLLOWUPS_RE.sub("\n", body)
    body = re.sub(
        r"(?m)^### Follow-up(?: 1：原題直接變形)?\s*$",
        "### Follow-up 1：原題直接變形",
        body,
        count=1,
    )
    goal = extract_goal(title, body)
    insight = extract_insight(title, body, guide)
    body = insert_before_solution(body, learning_block(title, body, guide))
    body = append_followups(body, followup_block(title, goal, insight, guide))
    return f"## {kind} {number}：{title}\n{body}"


def update_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end < 0:
        return text
    frontmatter = text[4:end]
    rest = text[end + 5:]
    additions = {
        "followups_per_question": "4",
        "visual_explanations": "true",
        "deep_solution_layer": "true",
    }
    for key, value in additions.items():
        pattern = rf"(?m)^{re.escape(key)}:.*$"
        line = f"{key}: {value}"
        if re.search(pattern, frontmatter):
            frontmatter = re.sub(pattern, line, frontmatter)
        else:
            frontmatter += "\n" + line
    return "---\n" + frontmatter + "\n---\n" + rest


def enrich_file(path: Path) -> tuple[int, int]:
    prefix = path.name[:2]
    guide = GUIDES[prefix]
    original = path.read_text(encoding="utf-8")
    text = update_frontmatter(original)
    text, count = QUESTION_RE.subn(lambda match: enrich_question(match, guide), text)
    if count != 8:
        raise SystemExit(f"{path}: expected 8 questions, found {count}")
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return count, text.count("<!-- deep-followups:start -->")


def main() -> None:
    total_questions = 0
    total_followup_groups = 0
    for path in sorted(PATTERN_DIR.glob("*.md")):
        questions, followups = enrich_file(path)
        total_questions += questions
        total_followup_groups += followups
        print(f"  ✔ {path.name}: {questions} visual solutions, {followups * 4} follow-ups")
    print(
        f"\nEnriched {total_questions} problems with visual explanations and "
        f"{total_followup_groups * 4} total follow-ups."
    )


if __name__ == "__main__":
    main()
