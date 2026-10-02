# 附錄 C　全題索引

> [!abstract] 本附錄地圖
> **用途**：把第 4–29 章的 260 道題整理成五種查法：依 pattern、依難度、依常見程度、依 LeetCode 題號，每題附一句話的關鍵技巧，方便複習、抽題與考前快速回想。
>
> **你會拿到**：
> - C.1 使用方式：各欄位的意思、位置的寫法，以及常見程度分級的依據與限制
> - C.2 依 pattern：26 章各一張表，列出 10 道題的難度與關鍵技巧
> - C.3 依難度：Easy 13 題、Medium 126 題、Hard 121 題
> - C.4 依常見程度：高頻清單常見 106 題、面經常見 57 題、延伸與上限題 97 題
> - C.5 依 LeetCode 題號排序的總表

## C.1 使用方式

本附錄收錄第 4 章到第 29 章的全部 260 道題：26 個 pattern 章，每章 5 道核心題與 5 道難題。題號與題名以 LeetCode 為準，難度沿用各章題目標題上標示的 LeetCode 官方難度，所以「難題」不一定是 Hard，「核心題」也可能是 Hard（例如第 23 章核心題 5 的 1312 與第 26 章核心題 2 的 315）。位置一律寫成「第 N 章核心題 k」或「第 N 章難題 k」，和正文互相引用的寫法相同。

「一句話關鍵技巧」是該題思路或詳解中最關鍵的那一步，用來在複習時快速確認自己還記得解法的核心。建議的用法是先遮住這一欄，只看題號與題名，自己說出關鍵技巧與複雜度，再對照表格；說不出來或說錯的題，就照附錄 D 的規則放進錯題本。這一句話只是提示，不能取代正文中的推導、邊界處理與 follow-up。

第 11 章核心題 3 同時涵蓋 141. Linked List Cycle（Easy）與 142. Linked List Cycle II（Medium），兩題是同一個 Floyd 快慢指標的前後兩問，所以本附錄把它算作一題，難度依章節標題記為 Easy。

C.4 的常見程度是**定性分類，不是統計**。本書沒有、也不使用任何公司的出題頻率數字，分級只依據公開資訊的常識判斷：

| 分級 | 判斷依據 | 怎麼用 |
|---|---|---|
| 高頻清單常見 | 收錄在 Blind 75、NeetCode 150 這類公開的高頻練習清單中 | 準備時間有限時最優先，每題都要能在 20 分鐘內寫完並講清楚 |
| 面經常見 | 不在上述兩份清單，但屬於公開面經與其他公開題單中經常被提到的經典題或標準變形 | 第二優先，重點是辨識出它和高頻題之間的差異 |
| 延伸與上限題 | 較少出現在公開高頻清單，本書收錄是為了補齊 pattern 的主要變形或展示這個 domain 的上限 | 目標 L5 或時間充裕時練習，重點放在讀懂關鍵突破，不必背程式 |

清單的內容會隨時間調整，各公司、各團隊的出題習慣也不同，所以分級只能當作排序練習的參考，不代表某一題在真實面試中出現的機率。即使是延伸與上限題，它們的關鍵技巧也常常是高頻題 follow-up 的答案，值得至少讀過一次。

## C.2 依 pattern

每章一張表，順序與正文相同：先 5 道核心題，再 5 道難題。

### 第 4 章　Hashing 與計數

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 1. Two Sum | Easy | 由左往右掃，先查 target − x 是否已在「值 → 索引」表中再放入 x，一次走完且不會和自己配對 |
| 核心題 2 | 49. Group Anagrams | Medium | 排序後的字串或 26 格計數 tuple 當 canonical key，anagram 自然落進同一組 |
| 核心題 3 | 128. Longest Consecutive Sequence | Medium | 只從「x − 1 不在 set 中」的起點往上數，每個值只被踩一次，攤銷 O(n) |
| 核心題 4 | 454. 4Sum II | Medium | 拆成 A + B 與 C + D 兩半，先用 Counter 存左半的和與次數，再查 −(c + d)，O(n⁴) 折半成 O(n²) |
| 核心題 5 | 554. Brick Wall | Medium | 每列的前綴和就是接縫位置，用 Counter 找被最多列共享的接縫，答案是列數減去最大次數（不計牆的右緣） |
| 難題 1 | 41. First Missing Positive | Hard | 答案一定在 1 到 n + 1，把值 v 交換到索引 v − 1，讓輸入陣列本身當 hash set |
| 難題 2 | 30. Substring with Concatenation of All Words | Hard | 依起點 mod L 分成 L 組，每組以「詞」為單位滑動窗口，並維持每個詞都不超量 |
| 難題 3 | 149. Max Points on a Line | Hard | 固定錨點後按方向分組，方向用 gcd 約分並統一正負號的整數 tuple 當 key，避開浮點誤差 |
| 難題 4 | 336. Palindrome Pairs | Hard | 把每個字切成兩段，一段本身是回文時，另一段的反轉就是要查的搭檔，n² 次配對變成 n · k 次查表 |
| 難題 5 | 1224. Maximum Equal Frequency | Hard | 多維護一層「次數 → 有幾個值」，用三種合格形狀與長度等式 O(1) 判斷每個前綴 |

### 第 5 章　Two Pointers

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 167. Two Sum II - Input Array Is Sorted | Medium | 相向雙指標：和太小就移左、太大就移右，每步排除一個不可能的端點 |
| 核心題 2 | 15. 3Sum | Medium | 排序後固定最小的數，對右側做 Two Sum II，跳過相同值去重 |
| 核心題 3 | 11. Container With Most Water | Medium | 較短那條線已經配過最寬的搭檔，丟掉它（移動短邊），每步排除一條線 |
| 核心題 4 | 75. Sort Colors | Medium | Dutch national flag 三路分區：遇 0 和 lt 交換並前進，遇 2 和 gt 交換但 i 不動，因為換回來的還沒檢查 |
| 核心題 5 | 977. Squares of a Sorted Array | Easy | 最大的平方一定在兩端，從兩端比較絕對值，由後往前填結果 |
| 難題 1 | 42. Trapping Rain Water | Hard | 每欄水位是兩側最大值中較小者，哪一側的最大值較小就先結算哪一側 |
| 難題 2 | 287. Find the Duplicate Number | Medium | 把 i → nums[i] 看成 linked list，重複值就是環的入口，用 Floyd 快慢指標找 |
| 難題 3 | 923. 3Sum With Multiplicity | Medium | 排序後相向指標，相等時把兩端的重複段整段計數（同值用組合數、異值相乘） |
| 難題 4 | 1793. Maximum Score of a Good Subarray | Hard | 從 k 往兩側擴張時永遠走較大的那一邊，讓每個最小值門檻的最長區間都被經過 |
| 難題 5 | 2009. Minimum Number of Operations to Make Array Continuous | Hard | 改問最多能保留幾個：去重排序後，用窗口找值域長度不超過 n − 1 的最多元素 |

### 第 6 章　Sliding Window

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 3. Longest Substring Without Repeating Characters | Medium | 記錄每個字元最後出現的位置，重複時左端直接跳到 last[c] + 1（不能往回跳） |
| 核心題 2 | 209. Minimum Size Subarray Sum | Medium | 元素皆正，窗口和 ≥ target 時不斷收縮左端並更新最短長度 |
| 核心題 3 | 424. Longest Repeating Character Replacement | Medium | 窗口長度減去窗口內最多字母的次數必須 ≤ k，maxf 可以不隨收縮更新，窗口長度只增不減 |
| 核心題 4 | 567. Permutation in String | Medium | 固定長度 m 的窗口，維護 26 個字母中「次數剛好相符」的個數，等於 26 就找到排列 |
| 核心題 5 | 438. Find All Anagrams in a String | Medium | need 計數允許變負，超量就收縮，窗口長度恰好等於 len(p) 時就是一個 anagram |
| 難題 1 | 76. Minimum Window Substring | Hard | need 加 missing 計數讓「是否涵蓋 t」變成 O(1) 判斷，涵蓋時收縮左端求最短 |
| 難題 2 | 239. Sliding Window Maximum | Hard | 維護一個值遞減的 deque，被較新、較大元素支配的舊元素直接彈掉，隊首就是最大值 |
| 難題 3 | 992. Subarrays with K Different Integers | Hard | 恰好 K 種不單調，改算 atMost(K) − atMost(K − 1) |
| 難題 4 | 995. Minimum Number of K Consecutive Bit Flips | Hard | 最左邊的 0 只能由從它開始的翻轉處理，用差分記錄作用中的翻轉數奇偶，O(n) 貪婪 |
| 難題 5 | 2302. Count Subarrays With Score Less Than K | Hard | 分數 sum × 長度對窗口仍單調，維護和與長度即可收縮，每個右端貢獻 right − left + 1 個子陣列 |

### 第 7 章　Prefix Sum 與 Difference Array

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 238. Product of Array Except Self | Medium | answer[i] 等於前綴積乘後綴積，先把前綴積寫進輸出，再由右往左乘上累積的後綴積 |
| 核心題 2 | 560. Subarray Sum Equals K | Medium | 子陣列和為 k 等價於 P[r] − k 曾經出現過，hash map 記前綴和次數，初始放 {0: 1} |
| 核心題 3 | 525. Contiguous Array | Medium | 把 0 當 −1，問題變成找兩個相等的前綴和，記每個前綴值第一次出現的位置 |
| 核心題 4 | 304. Range Sum Query 2D - Immutable | Medium | 二維前綴和多開一列一行，子矩形和用四個角排容 O(1) 算出 |
| 核心題 5 | 1094. Car Pooling | Medium | 在 from 加 p、在 to 減 p 的 difference array，前綴和就是每站車上人數 |
| 難題 1 | 1074. Number of Submatrices That Sum to Target | Hard | 固定上下兩列把每行壓成一個數，二維子矩形變成一維的 Subarray Sum Equals K |
| 難題 2 | 363. Max Sum of Rectangle No Larger Than K | Hard | 固定上下列降成一維後，在有序結構中找 ≥ P[r] − k 的最小前綴 |
| 難題 3 | 862. Shortest Subarray with Sum at Least K | Hard | 有負數時改用 monotonic deque 維護遞增的前綴和候選，隊首一配到就能彈出 |
| 難題 4 | 1371. Find the Longest Substring Containing Vowels in Even Counts | Medium | 五個母音的奇偶性壓成 5 位元 mask，相同 mask 的最早位置到現在就是合法子字串 |
| 難題 5 | 2281. Sum of Total Strength of Wizards | Hard | monotonic stack 求每個元素當最小值的左右範圍，再用前綴和的前綴和 O(1) 算出範圍內所有子陣列和的總和 |

### 第 8 章　Binary Search

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 34. Find First and Last Position of Element in Sorted Array | Medium | 左界是第一個 ≥ target 的位置，右界是第一個 > target 的位置減一，兩次 bisect |
| 核心題 2 | 33. Search in Rotated Sorted Array | Medium | mid 兩側至少一半有序，用有序那一半的頭尾判斷 target 在不在裡面 |
| 核心題 3 | 153. Find Minimum in Rotated Sorted Array | Medium | 以 nums[i] ≤ nums[-1] 當判斷式，第一個為 True 的位置就是最小值 |
| 核心題 4 | 875. Koko Eating Bananas | Medium | 速度越快時數越少，在答案空間 [1, max(piles)] 上二分最小可行速度 |
| 核心題 5 | 1011. Capacity To Ship Packages Within D Days | Medium | 容量越大天數越少，在 [max, sum] 上二分容量，用貪婪裝船判定可行 |
| 難題 1 | 4. Median of Two Sorted Arrays | Hard | 在較短陣列上二分切點，讓兩邊左半合起來恰好是較小的一半 |
| 難題 2 | 410. Split Array Largest Sum | Hard | 二分最大段和 X，貪婪計算每段不超過 X 時最少要切幾段 |
| 難題 3 | 668. Kth Smallest Number in Multiplication Table | Hard | 二分答案 x，每列 min(x // i, n) 加總就是 ≤ x 的個數 |
| 難題 4 | 719. Find K-th Smallest Pair Distance | Hard | 排序後二分距離 d，用 two pointers 在 O(n) 內數出距離 ≤ d 的數對 |
| 難題 5 | 2040. Kth Smallest Product of Two Sorted Arrays | Hard | 二分乘積 x，固定一邊後依正負號決定另一邊是前綴或後綴，用 bisect 計數 |

### 第 9 章　Intervals 與 Sweep Line

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 56. Merge Intervals | Medium | 依起點排序，只需和目前最後一段比較右端，重疊就延長 |
| 核心題 2 | 57. Insert Interval | Medium | 清單分成「完全在左、重疊、完全在右」三段，中間那段全部併進新區間 |
| 核心題 3 | 435. Non-overlapping Intervals | Medium | 依終點排序能選就選（活動選擇），刪除數等於總數減去最多不重疊數 |
| 核心題 4 | 986. Interval List Intersections | Medium | 雙指標取 max(起點) 與 min(終點) 為交集，再推進終點較早的那個 |
| 核心題 5 | 253. Meeting Rooms II | Medium | 起點與終點各自排序後雙指標掃描，或用 min-heap 存每間會議室的結束時間 |
| 難題 1 | 218. The Skyline Problem | Hard | 掃描所有邊界，用 max-heap 加 lazy deletion 維護活著的最高建築，高度改變時輸出關鍵點 |
| 難題 2 | 759. Employee Free Time | Hard | 合併所有員工的工作時段（聯集），相鄰合併段之間的空隙就是共同空閒 |
| 難題 3 | 850. Rectangle Area II | Hard | 沿 x 掃描，每段寬度乘上目前 y 方向的覆蓋長度，覆蓋長度用座標壓縮的 segment tree 維護 |
| 難題 4 | 352. Data Stream as Disjoint Intervals | Hard | 有序結構存不相交區間，新數字只可能和左右兩個鄰居合併 |
| 難題 5 | 1851. Minimum Interval to Include Each Query | Hard | 查詢由小到大離線處理，起點 ≤ q 的區間依長度放入 min-heap，終點 < q 的延遲刪除 |

### 第 10 章　Stack 與 Monotonic Stack

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 20. Valid Parentheses | Easy | 開括號 push、閉括號必須和堆疊頂端配對，結束時堆疊要是空的 |
| 核心題 2 | 155. Min Stack | Medium | 每層同時存（值、到這層為止的最小值），pop 後下一層的最小值自然就是答案 |
| 核心題 3 | 150. Evaluate Reverse Polish Notation | Medium | 數字 push，運算子 pop 兩個（先彈出的是右運算元），除法用 int(a / b) 向零取整 |
| 核心題 4 | 739. Daily Temperatures | Medium | monotonic stack 存還在等待更暖日子的索引，新溫度把比它冷的全部結算 |
| 核心題 5 | 503. Next Greater Element II | Medium | 索引跑兩圈 i % n，第二圈只結算不再 push |
| 難題 1 | 84. Largest Rectangle in Histogram | Hard | monotonic stack 找每根柱子左右第一根更矮的柱子，以它的高為矩形高度 |
| 難題 2 | 85. Maximal Rectangle | Hard | 逐列累積成直方圖高度，每列跑一次 84 |
| 難題 3 | 32. Longest Valid Parentheses | Hard | stack 底部放「最後一個無法配對的位置」當基準，配對成功時長度是 i − stack[-1] |
| 難題 4 | 224. Basic Calculator | Hard | 只有加減時括號只會改變正負號，進括號 push（result、sign），出括號合併回去 |
| 難題 5 | 907. Sum of Subarray Minimums | Medium | 貢獻法：每個元素當最小值的子陣列數是左側距離乘右側距離，一邊嚴格、一邊不嚴格以避免重複計數 |

### 第 11 章　Linked List

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 206. Reverse Linked List | Easy | 三個指標 prev、cur、nxt，先存下一個再把 cur.next 指回 prev |
| 核心題 2 | 21. Merge Two Sorted Lists | Easy | dummy 節點加 tail 指標，每次接上較小的頭，最後把剩下的整段接上 |
| 核心題 3 | 141／142. Linked List Cycle（含 142. Linked List Cycle II） | Easy | Floyd 快慢指標：相遇代表有環；142 再讓一個指標從 head 出發、一個從相遇點出發，同速走到相遇處就是入口 |
| 核心題 4 | 19. Remove Nth Node From End of List | Medium | fast 先走 n + 1 步，兩指標從 dummy 同速前進，fast 到底時 slow 停在目標的前一個 |
| 核心題 5 | 143. Reorder List | Medium | 找第一個中點切開、反轉後半段、兩段交錯合併 |
| 難題 1 | 25. Reverse Nodes in k-Group | Hard | 先確認還有 k 個節點，把 prev 初值設成下一組的開頭，反轉後只需接一次 group_prev.next |
| 難題 2 | 23. Merge k Sorted Lists | Hard | min-heap 放 k 個頭，每次取最小再推入它的 next；或兩兩配對合併，O(N log k) |
| 難題 3 | 138. Copy List with Random Pointer | Medium | 把複製節點插在原節點後面，copy.random = orig.random.next，最後拆成兩條 |
| 難題 4 | 148. Sort List | Medium | linked list 上用 merge sort：快慢指標切半、合併不需暫存陣列，bottom-up 版可達 O(1) 額外空間 |
| 難題 5 | 1171. Remove Zero Sum Consecutive Nodes from Linked List | Medium | 兩個前綴和相等代表中間區段和為 0，記每個前綴和最後出現的節點，第二趟直接跳過去 |

### 第 12 章　Binary Tree：DFS 與 BFS

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 102. Binary Tree Level Order Traversal | Medium | BFS 每輪先記下 len(queue)，恰好彈出這一層的節點 |
| 核心題 2 | 199. Binary Tree Right Side View | Medium | BFS 取每層最後一個；或以根、右、左順序 DFS，每個深度第一次到達的節點 |
| 核心題 3 | 543. Diameter of Binary Tree | Easy | 後序回傳單側深度，在每個節點用 left + right 更新全域最長路徑 |
| 核心題 4 | 105. Construct Binary Tree from Preorder and Inorder Traversal | Medium | 前序依序取根，用「值 → 中序索引」hash map 切出左右子樹範圍，不切片 |
| 核心題 5 | 236. Lowest Common Ancestor of a Binary Tree | Medium | 後序：左右子樹各找到一個時目前節點就是 LCA，否則把非空的那邊往上傳 |
| 難題 1 | 124. Binary Tree Maximum Path Sum | Hard | 後序回傳 max(0, 單側最大鏈) 給父節點，在每個節點以 left + right + val 結算經過它的路徑 |
| 難題 2 | 297. Serialize and Deserialize Binary Tree | Hard | 前序走訪並寫出空節點標記，讓每棵子樹在字串中自我界定，反序列化時依序遞迴讀回 |
| 難題 3 | 968. Binary Tree Cameras | Hard | 後序回傳三種狀態（未覆蓋、已覆蓋、有相機），有子節點未覆蓋時才裝相機，葉子永遠不裝 |
| 難題 4 | 987. Vertical Order Traversal of a Binary Tree | Hard | 走訪時記錄 (col, row, val)，排序後依 col 分組輸出 |
| 難題 5 | 2458. Height of Binary Tree After Subtree Removal Queries | Hard | 刪掉子樹後的高度取決於子樹外面，用前序由上往下傳 rest 值，每個查詢 O(1) |

### 第 13 章　BST 與 Trie

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 98. Validate Binary Search Tree | Medium | 遞迴時傳下 (low, high) 開區間，或檢查中序序列嚴格遞增 |
| 核心題 2 | 230. Kth Smallest Element in a BST | Medium | 迭代中序到第 k 次彈出就停；頻繁修改時在節點存子樹大小 |
| 核心題 3 | 450. Delete Node in a BST | Medium | 有兩個子節點時用右子樹最左的後繼取代，再遞迴刪除後繼 |
| 核心題 4 | 208. Implement Trie (Prefix Tree) | Medium | 每個節點用 dict 存子節點加 is_end 標記，search 要求走完且 is_end，startsWith 只要走得完 |
| 核心題 5 | 211. Design Add and Search Words Data Structure | Medium | 遇到 . 就對目前節點的所有子節點 DFS，只走真的存在的分支 |
| 難題 1 | 212. Word Search II | Hard | 把所有單字建成 trie，DFS 同時走在網格與 trie 上，找到單字後刪掉以剪枝 |
| 難題 2 | 745. Prefix and Suffix Search | Hard | 把每個「後綴 + # + 單字」都插入 trie 並存最大索引，一次前綴查詢同時滿足兩個條件 |
| 難題 3 | 1707. Maximum XOR With an Element From Array | Hard | 查詢依 m 排序並逐步把 ≤ m 的數插入 binary trie，從高位貪婪走相反位元求最大 XOR |
| 難題 4 | 472. Concatenated Words | Hard | 依長度排序，只用比自己短的字建 trie，對每個字做 word break 判斷能否切成至少兩段 |
| 難題 5 | 99. Recover Binary Search Tree | Medium | 中序序列中第一個下降的前者與最後一個下降的後者就是被交換的兩點 |

### 第 14 章　Heap：Top-K 與 K-way Merge

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 215. Kth Largest Element in an Array | Medium | 大小 k 的 min-heap 的堆頂就是第 k 大；或用三路切分的 quickselect 期望 O(n) |
| 核心題 2 | 347. Top K Frequent Elements | Medium | 次數介於 1 到 n，用 bucket sort 由高次數往下收集 k 個，O(n) |
| 核心題 3 | 973. K Closest Points to Origin | Medium | 大小 k 的 max-heap 存 (−距離平方, 索引)，比較距離平方不必開根號 |
| 核心題 4 | 621. Task Scheduler | Medium | 答案是 max((maxf − 1) × (n + 1) + 最高次數的任務種類數, 任務總數) |
| 核心題 5 | 767. Reorganize String | Medium | 最多的字母不能超過 (n + 1) // 2，依次數由多到少交錯填入偶數位再填奇數位 |
| 難題 1 | 295. Find Median from Data Stream | Hard | max-heap 存較小的一半、min-heap 存較大的一半，保持大小差 ≤ 1，中位數看堆頂 |
| 難題 2 | 480. Sliding Window Median | Hard | 兩個 heap 加 lazy deletion，自行維護有效大小，過期元素浮到堆頂時才真正刪除 |
| 難題 3 | 502. IPO | Hard | 專案依所需資本排序，把做得起的利潤放進 max-heap，每輪選最大的 |
| 難題 4 | 632. Smallest Range Covering Elements from K Lists | Hard | k-way merge：min-heap 放每條清單目前的元素並記下最大值，每次推進最小值所在的清單 |
| 難題 5 | 857. Minimum Cost to Hire K Workers | Hard | 總成本等於組內最大比例乘品質總和，依比例排序後枚舉最大比例，用 max-heap 維持最小的 k 個品質 |

### 第 15 章　Graph：BFS 與 DFS

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 200. Number of Islands | Medium | 掃描每格，遇到未拜訪的陸地就計數並 DFS／BFS 淹掉整座島 |
| 核心題 2 | 133. Clone Graph | Medium | 用「原節點 → 副本」hash map 同時當 visited 與 memo，建立副本後先登記再遞迴 |
| 核心題 3 | 994. Rotting Oranges | Medium | 所有腐爛橘子一起當作第 0 層做 multi-source BFS，層數就是分鐘數 |
| 核心題 4 | 417. Pacific Atlantic Water Flow | Medium | 反過來從兩邊海岸往高處爬（鄰居 ≥ 自己），取兩次搜尋結果的交集 |
| 核心題 5 | 130. Surrounded Regions | Medium | 從邊界上的 O 出發標記安全格，剩下的 O 才是被包圍的 |
| 難題 1 | 127. Word Ladder | Hard | 單字當節點，用萬用字元桶（如 h*t）產生鄰居做 BFS，可再加雙向 BFS |
| 難題 2 | 126. Word Ladder II | Hard | BFS 只建「第 i 層 → 第 i + 1 層」的父節點表，再從終點回溯列出所有最短路徑 |
| 難題 3 | 1293. Shortest Path in a Grid with Obstacles Elimination | Hard | 狀態加上剩餘可消除次數 (r, c, rem)，每格只保留到達時最大的 rem；k 夠大時直接回傳曼哈頓距離 |
| 難題 4 | 847. Shortest Path Visiting All Nodes | Hard | 狀態是（目前節點、已拜訪集合 bitmask），所有節點同時當起點做 BFS |
| 難題 5 | 864. Shortest Path to Get All Keys | Hard | 狀態是（位置、已持有鑰匙的 bitmask），沒有對應鑰匙的鎖不能通過 |

### 第 16 章　Topological Sort

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 207. Course Schedule | Medium | Kahn 演算法取出的節點數等於 n 就代表沒有環 |
| 核心題 2 | 210. Course Schedule II | Medium | 邊方向是「先修 → 後修」，Kahn 的取出順序就是一組合法的修課順序 |
| 核心題 3 | 802. Find Eventual Safe States | Medium | 反轉邊後從終點做 Kahn，出度歸零的節點就是安全節點 |
| 核心題 4 | 310. Minimum Height Trees | Medium | 一層一層剝掉葉子（度數為 1），最後剩下的 1 或 2 個節點就是最小高度樹的根 |
| 核心題 5 | 1462. Course Schedule IV | Medium | 依拓撲順序把每門課的祖先集合用整數 bitset 聯集下傳，查詢 O(1) |
| 難題 1 | 269. Alien Dictionary | Hard | 只比較相鄰兩字的第一個不同字元建邊，前者比後者長且是其前綴時判定無解 |
| 難題 2 | 329. Longest Increasing Path in a Matrix | Hard | 嚴格遞增讓網格自動成為 DAG，從出度 0 的格子剝層，層數就是最長路徑；或 DFS 加 memo |
| 難題 3 | 1203. Sort Items by Groups Respecting Dependencies | Hard | 組與組、組內項目各做一次拓撲排序，沒有組的項目各自成為新的一組 |
| 難題 4 | 1857. Largest Color Value in a Directed Graph | Hard | Kahn 順序上對每個節點維護 26 種顏色的最長路徑計數，取不完所有節點代表有環 |
| 難題 5 | 2050. Parallel Courses III | Hard | 沿拓撲順序計算最早完成時間 = 自己的時間 + 所有前置課完成時間的最大值 |

### 第 17 章　Union-Find

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 547. Number of Provinces | Medium | union-find 合併相鄰城市，每次成功合併省數減一 |
| 核心題 2 | 684. Redundant Connection | Medium | 依序加入邊，第一條兩端已經同根的邊就是答案 |
| 核心題 3 | 721. Accounts Merge | Medium | 記錄每個 email 第一次出現的帳號，之後同 email 就 union 帳號，最後依根分組並排序 |
| 核心題 4 | 990. Satisfiability of Equality Equations | Medium | 先處理所有 == 做 union，再檢查每個 != 的兩端是否同根 |
| 核心題 5 | 1319. Number of Operations to Make Network Connected | Medium | 線少於 n − 1 條必定無解，否則答案是連通元件數減一 |
| 難題 1 | 685. Redundant Connection II | Hard | 先找入度為 2 的節點得到兩條候選邊，再用 union-find 判斷該刪哪一條；沒有入度 2 時退化成 684 |
| 難題 2 | 778. Swim in Rising Water | Hard | 依海拔由低到高逐格 union 相鄰的已開格子，起點與終點連通時的海拔就是答案；或用 Dijkstra 取路徑最大值 |
| 難題 3 | 803. Bricks Falling When Hit | Hard | 時間倒流：先打掉所有被打的磚，再倒序補回，用 roof 虛擬節點與集合大小計算每次新增的穩定磚數 |
| 難題 4 | 1579. Remove Max Number of Edges to Keep Graph Fully Traversable | Hard | 優先處理兩人共用的 type 3 邊，再分別用兩份 union-find 加 type 1、type 2，最後檢查兩者都連通 |
| 難題 5 | 1697. Checking Existence of Edge Length Limited Paths | Hard | 邊與查詢都依長度限制排序，離線地只加入 < limit 的邊，再問兩點是否同根 |

### 第 18 章　Shortest Path 與 Minimum Spanning Tree

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 743. Network Delay Time | Medium | Dijkstra，最後一個定案的節點距離就是答案，有點到不了就回傳 −1 |
| 核心題 2 | 787. Cheapest Flights Within K Stops | Medium | Bellman-Ford 跑 k + 1 輪，每輪只用上一輪的 dist 副本鬆弛，限制經過的邊數 |
| 核心題 3 | 1631. Path With Minimum Effort | Medium | Dijkstra 的路徑成本改成 max(目前成本, 這一步的高度差)；或二分答案加 BFS |
| 核心題 4 | 1514. Path with Maximum Probability | Medium | 機率相乘且每邊 ≤ 1，Dijkstra 改成每次取機率最大的節點（heap 存負值） |
| 核心題 5 | 1584. Min Cost to Connect All Points | Medium | 完全圖用陣列版 Prim，O(n²) 且不必建出所有邊 |
| 難題 1 | 882. Reachable Nodes In Subdivided Graph | Hard | 對原節點跑 Dijkstra（邊權 cnt + 1），每條邊上的新節點可達數是 min(cnt, 兩端剩餘步數之和) |
| 難題 2 | 1368. Minimum Cost to Make at Least One Valid Path in a Grid | Hard | 順著箭頭走成本 0、改方向成本 1，用 0-1 BFS（deque）求最短路 |
| 難題 3 | 1928. Minimum Cost to Reach Destination in Time | Hard | 狀態是（城市、已用時間），時間遞增讓狀態圖成為 DAG，可依時間分層 DP；或 Dijkstra 只在時間更短時才保留 |
| 難題 4 | 2045. Second Minimum Time to Reach Destination | Hard | 抵達時間只取決於經過的邊數，BFS 時每個節點保留嚴格次短的距離，再依紅綠燈換算時間 |
| 難題 5 | 1192. Critical Connections in a Network | Hard | Tarjan：DFS 記錄發現時間與 low 值，low[child] > disc[node] 的樹邊就是 bridge |

### 第 19 章　Backtracking

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 78. Subsets | Medium | start 寫法：每個遞迴節點本身就是一個子集，下一個元素只從更大的索引中選 |
| 核心題 2 | 46. Permutations | Medium | used 陣列標記已放入 path 的元素，每層從未用過的元素中選 |
| 核心題 3 | 39. Combination Sum | Medium | 下一層從 i 開始以允許重複使用，排序後元素大於剩餘目標就 break |
| 核心題 4 | 17. Letter Combinations of a Phone Number | Medium | 每層的選擇集合是目前數字對應的字母，深度等於位數時記錄答案 |
| 核心題 5 | 79. Word Search | Medium | DFS 時把格子暫時改成 # 表示已使用，回溯時改回原字元 |
| 難題 1 | 51. N-Queens | Hard | 逐列放皇后，用 c、r − c、r + c 三個集合 O(1) 檢查衝突 |
| 難題 2 | 37. Sudoku Solver | Hard | 列、行、宮各用 bitmask 記錄已用數字，每次挑候選最少的空格分岔（MRV） |
| 難題 3 | 282. Expression Add Operators | Hard | 遞迴帶著目前值與最後一個乘積項 last，乘法時用 value − last + last × x 修正優先序 |
| 難題 4 | 698. Partition to K Equal Sum Subsets | Medium | 由大到小排序後把數放進 k 個桶，和相同的空桶只試一個以消除對稱 |
| 難題 5 | 1240. Tiling a Rectangle with the Fewest Squares | Hard | 每次在最低最左的空格放正方形，以天際線為狀態做 branch and bound |

### 第 20 章　Greedy

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 55. Jump Game | Medium | 維護最遠可達位置 reach，掃到的 i 超過 reach 就失敗 |
| 核心題 2 | 45. Jump Game II | Medium | BFS 式分層：在目前這一跳的範圍內找下一跳最遠能到哪裡，走到範圍尾端時跳數加一 |
| 核心題 3 | 134. Gas Station | Medium | 油量變負就把起點改成下一站，總油量 ≥ 總耗油時最後的起點一定可行 |
| 核心題 4 | 763. Partition Labels | Medium | 記錄每個字母最後出現的位置，掃描時維護目前段的最遠結尾，i 等於它時切一刀 |
| 核心題 5 | 846. Hand of Straights | Medium | 目前最小的牌一定是某組順子的開頭，用 Counter 由小到大一次扣掉整組 |
| 難題 1 | 135. Candy | Hard | 左右各掃一次滿足單向條件，每個位置取兩者的最大值 |
| 難題 2 | 330. Patching Array | Hard | 維持 [1, miss) 都湊得出來，下一個數 ≤ miss 就延伸，否則補上 miss 讓範圍翻倍 |
| 難題 3 | 630. Course Schedule III | Hard | 依期限排序上課，超過期限就從 max-heap 丟掉目前最長的課（後悔式貪婪） |
| 難題 4 | 871. Minimum Number of Refueling Stops | Hard | 經過的加油站先放進 max-heap，油不夠時才從中取油最多的那站加油 |
| 難題 5 | 1326. Minimum Number of Taps to Open to Water a Garden | Hard | 把每個水龍頭轉成「左端點 → 最遠右端」，變成 Jump Game II |

### 第 21 章　DP：一維與狀態機

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 198. House Robber | Medium | dp[i] = max(dp[i − 1], dp[i − 2] + nums[i − 1])，只需兩個變數 |
| 核心題 2 | 322. Coin Change | Medium | dp[a] = min(dp[a − c] + 1)，以金額由小到大填表，湊不出的金額設為 amount + 1 |
| 核心題 3 | 300. Longest Increasing Subsequence | Medium | tails[k] 記錄長度 k + 1 的遞增子序列的最小結尾，用 bisect_left 替換，O(n log n) |
| 核心題 4 | 139. Word Break | Medium | dp[i] 表示前綴能否切開，只往回看單字最大長度以內的切點 |
| 核心題 5 | 91. Decode Ways | Medium | dp[i] 由一位數（非 0）與兩位數（10 到 26）兩種互斥情況相加，dp[0] = 1 |
| 難題 1 | 188. Best Time to Buy and Sell Stock IV | Hard | 狀態機 hold[j]、sold[j] 表示第 j 筆交易持有或已賣出，k ≥ n / 2 時退化成無限次交易 |
| 難題 2 | 354. Russian Doll Envelopes | Hard | 寬度遞增、同寬時高度遞減排序，再對高度做嚴格的 LIS |
| 難題 3 | 403. Frog Jump | Hard | 狀態是（石頭位置、上一跳距離），用 dict of set 記錄每顆石頭可能的上一跳 |
| 難題 4 | 1235. Maximum Profit in Job Scheduling | Hard | 依結束時間排序，dp[i] = max(不選, 選它 + bisect 找到的最後一個相容工作) |
| 難題 5 | 1335. Minimum Difficulty of a Job Schedule | Hard | dp[d][i] 枚舉最後一天的起點，往回枚舉時順便維護區間最大值 |

### 第 22 章　DP：二維與序列比對

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 62. Unique Paths | Medium | dp[i][j] = 上 + 左，壓成一列 row[j] += row[j − 1]；也可直接算組合數 C(m + n − 2, m − 1) |
| 核心題 2 | 64. Minimum Path Sum | Medium | dp[i][j] = grid[i][j] + min(上, 左)，可以原地或用一列滾動 |
| 核心題 3 | 1143. Longest Common Subsequence | Medium | 字元相同取左上加一，不同取上與左的最大值 |
| 核心題 4 | 72. Edit Distance | Medium | 相同時繼承左上，不同時取替換、刪除、插入三者最小值加一 |
| 核心題 5 | 97. Interleaving String | Medium | dp[i][j] 表示 s1[:i] 與 s2[:j] 能否組成 s3[:i + j]，最後一個字元來自 s1 或 s2 |
| 難題 1 | 10. Regular Expression Matching | Hard | x* 只做一個決定：整個單元消失退回 (i, j − 2)，或在字元相符時吃一個並保留自己退回 (i − 1, j) |
| 難題 2 | 44. Wildcard Matching | Hard | * 每次只決定再吃一個或停止；貪婪版只記住最近一個 * 的位置，失敗時讓它多吃一個字元 |
| 難題 3 | 115. Distinct Subsequences | Hard | s 的最後一個字元用或不用：相同時 dp[i][j] = dp[i − 1][j − 1] + dp[i − 1][j] |
| 難題 4 | 174. Dungeon Game | Hard | 從右下往左上填「進入這格前至少需要多少血」，每格至少為 1 |
| 難題 5 | 1092. Shortest Common Supersequence | Hard | 先算 LCS 表，從右下回溯時共用字元只輸出一次，被丟下的字元也要輸出 |

### 第 23 章　DP：背包與區間

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 416. Partition Equal Subset Sum | Medium | 總和為奇數直接無解，否則做目標 sum / 2 的 0/1 背包可行性，內層由大到小 |
| 核心題 2 | 494. Target Sum | Medium | 正號那組的和 P = (S + target) / 2，變成「和為 P 的子集個數」的 0/1 計數背包 |
| 核心題 3 | 518. Coin Change II | Medium | 外層硬幣、內層金額由小到大，算的是組合數而不是排列數 |
| 核心題 4 | 516. Longest Palindromic Subsequence | Medium | 兩端字元相同就配對加 2，否則取去掉左端或右端的較大值；也等於 s 與 reverse(s) 的 LCS |
| 核心題 5 | 1312. Minimum Insertion Steps to Make a String Palindrome | Hard | 最少插入數 = n − 最長回文子序列長度，區間 DP 不同時取 1 + min(去左, 去右) |
| 難題 1 | 312. Burst Balloons | Hard | 枚舉區間內最後一顆戳破的氣球 k，它被戳時的鄰居固定是區間外側的兩顆 |
| 難題 2 | 664. Strange Printer | Hard | s[i] 那一筆可以延伸到同色的 s[k] 一起印，dp[i][j] 在所有同色位置中選一個合併 |
| 難題 3 | 546. Remove Boxes | Hard | 狀態加一維 k 表示左邊黏著幾個同色盒子，dp[i][j][k] |
| 難題 4 | 1000. Minimum Cost to Merge Stones | Hard | (n − 1) % (K − 1) ≠ 0 時無解，分割點每次跳 K − 1，區間長度可合成一堆時加上區間和 |
| 難題 5 | 1547. Minimum Cost to Cut a Stick | Hard | 切點排序並加上 0 與 n 兩端，dp[i][j] 枚舉 (i, j) 之間的第一刀，成本是 cuts[j] − cuts[i] |

### 第 24 章　DP：樹、Bitmask 與數位

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 337. House Robber III | Medium | 每個節點回傳（偷、不偷）兩個值，偷自己時子節點都只能取不偷 |
| 核心題 2 | 338. Counting Bits | Easy | ans[i] = ans[i >> 1] + (i & 1)，或 ans[i & (i − 1)] + 1 |
| 核心題 3 | 526. Beautiful Arrangement | Medium | dp[mask] 表示用掉 mask 這些數字的方法數，下一個位置是 popcount(mask) + 1 |
| 核心題 4 | 1986. Minimum Number of Work Sessions to Finish the Tasks | Medium | dp[mask] 存（session 數、目前 session 的負載），取字典序最小者；或預算每個子集的總和後枚舉子集 |
| 核心題 5 | 902. Numbers At Most N Given Digit Set | Hard | 比 n 短的數直接用 kᴸ 計數，等長的數由高位逐位比較，貼著 n 走時繼續 tight |
| 難題 1 | 834. Sum of Distances in Tree | Hard | 先後序求子樹大小與根的答案，再換根：ans[child] = ans[parent] − size[child] + (n − size[child]) |
| 難題 2 | 943. Find the Shortest Superstring | Hard | 先算兩兩最大重疊，最短 superstring 變成 TSP：dp[mask][last] |
| 難題 3 | 1349. Maximum Students Taking Exam | Hard | 每列的坐法壓成 mask，合法條件是不坐壞椅、本列不相鄰、上一列左右斜前方沒人 |
| 難題 4 | 233. Number of Digit One | Hard | 對每一位分別數「這一位是 1」的數：把 n 拆成高位、這一位、低位三段分情況 |
| 難題 5 | 2376. Count Special Integers | Hard | 數位 DP 的狀態是（位置、tight、已用數字 mask、started），不 tight 時直接用排列數計算 |

### 第 25 章　字串演算法：KMP、Rolling Hash 與回文

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 5. Longest Palindromic Substring | Medium | 從 2n − 1 個中心（字元或字元之間）往外擴張，記錄最長的回文 |
| 核心題 2 | 647. Palindromic Substrings | Medium | 同樣從 2n − 1 個中心往外擴張，每成功擴張一次就多一個回文 |
| 核心題 3 | 28. Find the Index of the First Occurrence in a String | Easy | KMP：先建 failure function，失配時沿 pi 回跳，text 指標從不後退 |
| 核心題 4 | 459. Repeated Substring Pattern | Easy | 最短週期 p = n − pi[n − 1]，p < n 且 p 整除 n 時就是重複組成；或檢查 s 是否出現在 (s + s)[1:−1] |
| 核心題 5 | 686. Repeated String Match | Medium | a 最多重複 ⌈len(b) / len(a)⌉ + 1 次，在這個長度內用 KMP 找 b |
| 難題 1 | 214. Shortest Palindrome | Hard | 對 s + # + reverse(s) 求 failure function，最後的值就是最長回文前綴，把剩下部分反轉補在前面 |
| 難題 2 | 1044. Longest Duplicate Substring | Hard | 二分子字串長度，用 rolling hash 的 set 檢查該長度是否有重複 |
| 難題 3 | 1392. Longest Happy Prefix | Hard | KMP 的 pi[n − 1] 就是最長的「既是前綴也是後綴」 |
| 難題 4 | 1923. Longest Common Subpath | Hard | 二分共同長度，對每條路徑求該長度所有子路徑的 rolling hash，取 set 交集是否非空 |
| 難題 5 | 2223. Sum of Scores of Built Strings | Hard | 每個 built string 的分數就是 Z-function 的 z[i]，答案是 Z 陣列總和（z[0] 取 n） |

### 第 26 章　Range Query：Fenwick Tree 與 Segment Tree

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 307. Range Sum Query - Mutable | Medium | Fenwick tree 存陣列，update 時加上 val − nums[i] 的差值，區間和用兩個前綴和相減 |
| 核心題 2 | 315. Count of Smaller Numbers After Self | Hard | 從右往左掃，座標壓縮後用 BIT 查詢已插入的數中有幾個比目前小；或用 merge sort 計數 |
| 核心題 3 | 729. My Calendar I | Medium | 已預訂區間互不重疊，用 bisect 找插入位置，只需檢查前後兩個鄰居 |
| 核心題 4 | 731. My Calendar II | Medium | 另外維護「已被兩筆覆蓋」的清單，新區間碰到它就拒絕；或用 segment tree 查區間最大覆蓋數 |
| 核心題 5 | 1395. Count Number of Teams | Medium | 固定中間的人，左邊比他小的人數乘右邊比他大的人數（加上反向），用 BIT 計數 |
| 難題 1 | 327. Count of Range Sum | Hard | 子陣列和落在 [lower, upper] 等於前綴和之差落在範圍內，壓縮前綴和後用 BIT 範圍計數 |
| 難題 2 | 493. Reverse Pairs | Hard | merge sort 合併前先用雙指標數 nums[i] > 2 × nums[j] 的數對；或用 BIT 依 2 × nums[j] 的 rank 查詢 |
| 難題 3 | 699. Falling Squares | Hard | 座標壓縮後用支援區間覆蓋與區間最大值的 segment tree，每塊方塊落下時查詢再覆蓋 |
| 難題 4 | 715. Range Module | Hard | 排序的端點陣列表示不相交區間，點是否被覆蓋看 bisect 位置的奇偶，三種操作都是整段替換 |
| 難題 5 | 2407. Longest Increasing Subsequence II | Hard | 以值為索引的 segment tree 查詢 [x − k, x − 1] 的最大 dp 值，再更新 x |

### 第 27 章　資料結構設計

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 146. LRU Cache | Medium | dict 存 key → 雙向 linked list 節點，最近使用的移到頭、容量滿時刪除尾端 |
| 核心題 2 | 380. Insert Delete GetRandom O(1) | Medium | 陣列加「值 → 索引」map，刪除時和最後一個元素交換再 pop |
| 核心題 3 | 981. Time Based Key-Value Store | Medium | 每個 key 存時間遞增的版本串列，get 用 bisect_right − 1 找最後一個 ≤ timestamp 的版本 |
| 核心題 4 | 1472. Design Browser History | Medium | 陣列加游標 cur 與有效尾端 last，visit 時覆寫下一格並截斷 last，back／forward 用 min／max 一步到位 |
| 核心題 5 | 341. Flatten Nested List Iterator | Medium | 顯式 stack 存（串列、索引），hasNext 負責推進到下一個整數並跳過空串列 |
| 難題 1 | 460. LFU Cache | Hard | 每個次數各一個 LRU（OrderedDict），維護 min_freq，新 key 進來時 min_freq 重設為 1 |
| 難題 2 | 432. All O(1) Data Structure | Hard | 計數桶串成雙向 linked list，計數只會變 1，所以目標桶一定是目前桶的鄰居 |
| 難題 3 | 716. Max Stack | Hard | stack 與 max-heap 共用唯一 id，刪除只做標記，等它浮到頂端時才清掉 |
| 難題 4 | 895. Maximum Frequency Stack | Hard | 每個次數 f 各有一個 stack，push 第 f 次就放進第 f 層，pop 時從最高次數層彈出 |
| 難題 5 | 1146. Snapshot Array | Medium | 每個索引存（snap_id、值）的版本串列，get 用 bisect 找 ≤ snap_id 的最後一筆 |

### 第 28 章　Bit Manipulation 與數學

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 136. Single Number | Easy | 全部 XOR 起來，成對的數互相抵消，剩下落單的數 |
| 核心題 2 | 268. Missing Number | Easy | 把 0 到 n 的索引和所有值一起 XOR，缺的數只出現一次；或用總和公式相減 |
| 核心題 3 | 191. Number of 1 Bits | Easy | n &= n − 1 每次消掉最低位的 1，迴圈次數等於 1 的個數 |
| 核心題 4 | 50. Pow(x, n) | Medium | 快速冪：依指數的二進位逐位平方 base，負指數先轉成 1 / x |
| 核心題 5 | 204. Count Primes | Medium | Eratosthenes 篩法，每個質數 p 從 p² 開始劃掉倍數，p 只跑到 √n |
| 難題 1 | 137. Single Number II | Medium | 逐位元數 1 的個數 mod 3；或用 ones、twos 兩個整數組成的狀態機 |
| 難題 2 | 201. Bitwise AND of Numbers Range | Medium | 答案是 left 與 right 的共同二進位前綴，同時右移直到兩者相等再左移回去 |
| 難題 3 | 60. Permutation Sequence | Hard | 每個開頭對應 (n − 1)! 個排列，對 k − 1 依序除以階乘取 divmod 逐位決定（階乘進位制） |
| 難題 4 | 829. Consecutive Numbers Sum | Hard | 長度 k 的連續和要求 n − k(k − 1) / 2 能被 k 整除，k 只需枚舉到 √(2n)；答案等於 n 的奇因數個數 |
| 難題 5 | 1611. Minimum One Bit Operations to Make Integers Zero | Hard | 操作序列對應 Gray code，答案就是 Gray code 的反轉換（把 n 的所有右移結果 XOR 起來） |

### 第 29 章　Matrix、模擬與解析

| 題 | 題號與題名 | 難度 | 一句話關鍵技巧 |
|---|---|---|---|
| 核心題 1 | 54. Spiral Matrix | Medium | 用 top、bottom、left、right 四個邊界逐層收縮，走下邊與左邊前檢查矩形是否已空 |
| 核心題 2 | 48. Rotate Image | Medium | 先沿主對角線轉置，再把每一列左右反轉，即為順時針旋轉 90 度 |
| 核心題 3 | 73. Set Matrix Zeroes | Medium | 用第 0 列與第 0 行當標記，另用一個變數記第 0 行本身，最後才清標記區 |
| 核心題 4 | 36. Valid Sudoku | Medium | 一次掃描，每格同時檢查列、行、宮三個集合，宮編號 (r // 3) * 3 + c // 3 |
| 核心題 5 | 289. Game of Life | Medium | bit 0 存這一代、bit 1 存下一代，數鄰居只讀 bit 0，最後整盤右移一位 |
| 難題 1 | 65. Valid Number | Hard | 把格式規則寫成有限狀態機的轉移表，結束時檢查是否停在接受狀態 |
| 難題 2 | 68. Text Justification | Hard | 先貪婪分行，一般行把多餘空格平均分配且左邊多一，最後一行與單字行靠左對齊 |
| 難題 3 | 591. Tag Validator | Hard | 單一指標依序辨認四種前綴（CDATA、結束標籤、開始標籤、一般文字），stack 存標籤名稱 |
| 難題 4 | 726. Number of Atoms | Hard | 遇到左括號推入新的計數器，右括號後讀倍數再乘回外層；從右往左讀則可用累積倍數的 stack |
| 難題 5 | 770. Basic Calculator IV | Hard | 沿用計算機的遞迴下降骨架，值改成「排序後的變數 tuple → 係數」的多項式，運算換成多項式加乘 |

## C.3 依難度

同一難度內依章節順序排列。難度是 LeetCode 官方難度，只反映題目本身，不代表本書把它放在核心題或難題；面試時真正的難度還取決於 follow-up 追到多深。

### Easy（13 題）

141 所在的第 11 章核心題 3 也包含 142（Medium），練習時兩問要一起寫完。

| 題號與題名 | 位置 | Pattern |
|---|---|---|
| 1. Two Sum | 第 4 章核心題 1 | Hashing 與計數 |
| 977. Squares of a Sorted Array | 第 5 章核心題 5 | Two Pointers |
| 20. Valid Parentheses | 第 10 章核心題 1 | Stack 與 Monotonic Stack |
| 206. Reverse Linked List | 第 11 章核心題 1 | Linked List |
| 21. Merge Two Sorted Lists | 第 11 章核心題 2 | Linked List |
| 141／142. Linked List Cycle（含 142. Linked List Cycle II） | 第 11 章核心題 3 | Linked List |
| 543. Diameter of Binary Tree | 第 12 章核心題 3 | Binary Tree：DFS 與 BFS |
| 338. Counting Bits | 第 24 章核心題 2 | DP：樹、Bitmask 與數位 |
| 28. Find the Index of the First Occurrence in a String | 第 25 章核心題 3 | 字串演算法：KMP、Rolling Hash 與回文 |
| 459. Repeated Substring Pattern | 第 25 章核心題 4 | 字串演算法：KMP、Rolling Hash 與回文 |
| 136. Single Number | 第 28 章核心題 1 | Bit Manipulation 與數學 |
| 268. Missing Number | 第 28 章核心題 2 | Bit Manipulation 與數學 |
| 191. Number of 1 Bits | 第 28 章核心題 3 | Bit Manipulation 與數學 |

### Medium（126 題）

| 題號與題名 | 位置 | Pattern |
|---|---|---|
| 49. Group Anagrams | 第 4 章核心題 2 | Hashing 與計數 |
| 128. Longest Consecutive Sequence | 第 4 章核心題 3 | Hashing 與計數 |
| 454. 4Sum II | 第 4 章核心題 4 | Hashing 與計數 |
| 554. Brick Wall | 第 4 章核心題 5 | Hashing 與計數 |
| 167. Two Sum II - Input Array Is Sorted | 第 5 章核心題 1 | Two Pointers |
| 15. 3Sum | 第 5 章核心題 2 | Two Pointers |
| 11. Container With Most Water | 第 5 章核心題 3 | Two Pointers |
| 75. Sort Colors | 第 5 章核心題 4 | Two Pointers |
| 287. Find the Duplicate Number | 第 5 章難題 2 | Two Pointers |
| 923. 3Sum With Multiplicity | 第 5 章難題 3 | Two Pointers |
| 3. Longest Substring Without Repeating Characters | 第 6 章核心題 1 | Sliding Window |
| 209. Minimum Size Subarray Sum | 第 6 章核心題 2 | Sliding Window |
| 424. Longest Repeating Character Replacement | 第 6 章核心題 3 | Sliding Window |
| 567. Permutation in String | 第 6 章核心題 4 | Sliding Window |
| 438. Find All Anagrams in a String | 第 6 章核心題 5 | Sliding Window |
| 238. Product of Array Except Self | 第 7 章核心題 1 | Prefix Sum 與 Difference Array |
| 560. Subarray Sum Equals K | 第 7 章核心題 2 | Prefix Sum 與 Difference Array |
| 525. Contiguous Array | 第 7 章核心題 3 | Prefix Sum 與 Difference Array |
| 304. Range Sum Query 2D - Immutable | 第 7 章核心題 4 | Prefix Sum 與 Difference Array |
| 1094. Car Pooling | 第 7 章核心題 5 | Prefix Sum 與 Difference Array |
| 1371. Find the Longest Substring Containing Vowels in Even Counts | 第 7 章難題 4 | Prefix Sum 與 Difference Array |
| 34. Find First and Last Position of Element in Sorted Array | 第 8 章核心題 1 | Binary Search |
| 33. Search in Rotated Sorted Array | 第 8 章核心題 2 | Binary Search |
| 153. Find Minimum in Rotated Sorted Array | 第 8 章核心題 3 | Binary Search |
| 875. Koko Eating Bananas | 第 8 章核心題 4 | Binary Search |
| 1011. Capacity To Ship Packages Within D Days | 第 8 章核心題 5 | Binary Search |
| 56. Merge Intervals | 第 9 章核心題 1 | Intervals 與 Sweep Line |
| 57. Insert Interval | 第 9 章核心題 2 | Intervals 與 Sweep Line |
| 435. Non-overlapping Intervals | 第 9 章核心題 3 | Intervals 與 Sweep Line |
| 986. Interval List Intersections | 第 9 章核心題 4 | Intervals 與 Sweep Line |
| 253. Meeting Rooms II | 第 9 章核心題 5 | Intervals 與 Sweep Line |
| 155. Min Stack | 第 10 章核心題 2 | Stack 與 Monotonic Stack |
| 150. Evaluate Reverse Polish Notation | 第 10 章核心題 3 | Stack 與 Monotonic Stack |
| 739. Daily Temperatures | 第 10 章核心題 4 | Stack 與 Monotonic Stack |
| 503. Next Greater Element II | 第 10 章核心題 5 | Stack 與 Monotonic Stack |
| 907. Sum of Subarray Minimums | 第 10 章難題 5 | Stack 與 Monotonic Stack |
| 19. Remove Nth Node From End of List | 第 11 章核心題 4 | Linked List |
| 143. Reorder List | 第 11 章核心題 5 | Linked List |
| 138. Copy List with Random Pointer | 第 11 章難題 3 | Linked List |
| 148. Sort List | 第 11 章難題 4 | Linked List |
| 1171. Remove Zero Sum Consecutive Nodes from Linked List | 第 11 章難題 5 | Linked List |
| 102. Binary Tree Level Order Traversal | 第 12 章核心題 1 | Binary Tree：DFS 與 BFS |
| 199. Binary Tree Right Side View | 第 12 章核心題 2 | Binary Tree：DFS 與 BFS |
| 105. Construct Binary Tree from Preorder and Inorder Traversal | 第 12 章核心題 4 | Binary Tree：DFS 與 BFS |
| 236. Lowest Common Ancestor of a Binary Tree | 第 12 章核心題 5 | Binary Tree：DFS 與 BFS |
| 98. Validate Binary Search Tree | 第 13 章核心題 1 | BST 與 Trie |
| 230. Kth Smallest Element in a BST | 第 13 章核心題 2 | BST 與 Trie |
| 450. Delete Node in a BST | 第 13 章核心題 3 | BST 與 Trie |
| 208. Implement Trie (Prefix Tree) | 第 13 章核心題 4 | BST 與 Trie |
| 211. Design Add and Search Words Data Structure | 第 13 章核心題 5 | BST 與 Trie |
| 99. Recover Binary Search Tree | 第 13 章難題 5 | BST 與 Trie |
| 215. Kth Largest Element in an Array | 第 14 章核心題 1 | Heap：Top-K 與 K-way Merge |
| 347. Top K Frequent Elements | 第 14 章核心題 2 | Heap：Top-K 與 K-way Merge |
| 973. K Closest Points to Origin | 第 14 章核心題 3 | Heap：Top-K 與 K-way Merge |
| 621. Task Scheduler | 第 14 章核心題 4 | Heap：Top-K 與 K-way Merge |
| 767. Reorganize String | 第 14 章核心題 5 | Heap：Top-K 與 K-way Merge |
| 200. Number of Islands | 第 15 章核心題 1 | Graph：BFS 與 DFS |
| 133. Clone Graph | 第 15 章核心題 2 | Graph：BFS 與 DFS |
| 994. Rotting Oranges | 第 15 章核心題 3 | Graph：BFS 與 DFS |
| 417. Pacific Atlantic Water Flow | 第 15 章核心題 4 | Graph：BFS 與 DFS |
| 130. Surrounded Regions | 第 15 章核心題 5 | Graph：BFS 與 DFS |
| 207. Course Schedule | 第 16 章核心題 1 | Topological Sort |
| 210. Course Schedule II | 第 16 章核心題 2 | Topological Sort |
| 802. Find Eventual Safe States | 第 16 章核心題 3 | Topological Sort |
| 310. Minimum Height Trees | 第 16 章核心題 4 | Topological Sort |
| 1462. Course Schedule IV | 第 16 章核心題 5 | Topological Sort |
| 547. Number of Provinces | 第 17 章核心題 1 | Union-Find |
| 684. Redundant Connection | 第 17 章核心題 2 | Union-Find |
| 721. Accounts Merge | 第 17 章核心題 3 | Union-Find |
| 990. Satisfiability of Equality Equations | 第 17 章核心題 4 | Union-Find |
| 1319. Number of Operations to Make Network Connected | 第 17 章核心題 5 | Union-Find |
| 743. Network Delay Time | 第 18 章核心題 1 | Shortest Path 與 Minimum Spanning Tree |
| 787. Cheapest Flights Within K Stops | 第 18 章核心題 2 | Shortest Path 與 Minimum Spanning Tree |
| 1631. Path With Minimum Effort | 第 18 章核心題 3 | Shortest Path 與 Minimum Spanning Tree |
| 1514. Path with Maximum Probability | 第 18 章核心題 4 | Shortest Path 與 Minimum Spanning Tree |
| 1584. Min Cost to Connect All Points | 第 18 章核心題 5 | Shortest Path 與 Minimum Spanning Tree |
| 78. Subsets | 第 19 章核心題 1 | Backtracking |
| 46. Permutations | 第 19 章核心題 2 | Backtracking |
| 39. Combination Sum | 第 19 章核心題 3 | Backtracking |
| 17. Letter Combinations of a Phone Number | 第 19 章核心題 4 | Backtracking |
| 79. Word Search | 第 19 章核心題 5 | Backtracking |
| 698. Partition to K Equal Sum Subsets | 第 19 章難題 4 | Backtracking |
| 55. Jump Game | 第 20 章核心題 1 | Greedy |
| 45. Jump Game II | 第 20 章核心題 2 | Greedy |
| 134. Gas Station | 第 20 章核心題 3 | Greedy |
| 763. Partition Labels | 第 20 章核心題 4 | Greedy |
| 846. Hand of Straights | 第 20 章核心題 5 | Greedy |
| 198. House Robber | 第 21 章核心題 1 | DP：一維與狀態機 |
| 322. Coin Change | 第 21 章核心題 2 | DP：一維與狀態機 |
| 300. Longest Increasing Subsequence | 第 21 章核心題 3 | DP：一維與狀態機 |
| 139. Word Break | 第 21 章核心題 4 | DP：一維與狀態機 |
| 91. Decode Ways | 第 21 章核心題 5 | DP：一維與狀態機 |
| 62. Unique Paths | 第 22 章核心題 1 | DP：二維與序列比對 |
| 64. Minimum Path Sum | 第 22 章核心題 2 | DP：二維與序列比對 |
| 1143. Longest Common Subsequence | 第 22 章核心題 3 | DP：二維與序列比對 |
| 72. Edit Distance | 第 22 章核心題 4 | DP：二維與序列比對 |
| 97. Interleaving String | 第 22 章核心題 5 | DP：二維與序列比對 |
| 416. Partition Equal Subset Sum | 第 23 章核心題 1 | DP：背包與區間 |
| 494. Target Sum | 第 23 章核心題 2 | DP：背包與區間 |
| 518. Coin Change II | 第 23 章核心題 3 | DP：背包與區間 |
| 516. Longest Palindromic Subsequence | 第 23 章核心題 4 | DP：背包與區間 |
| 337. House Robber III | 第 24 章核心題 1 | DP：樹、Bitmask 與數位 |
| 526. Beautiful Arrangement | 第 24 章核心題 3 | DP：樹、Bitmask 與數位 |
| 1986. Minimum Number of Work Sessions to Finish the Tasks | 第 24 章核心題 4 | DP：樹、Bitmask 與數位 |
| 5. Longest Palindromic Substring | 第 25 章核心題 1 | 字串演算法：KMP、Rolling Hash 與回文 |
| 647. Palindromic Substrings | 第 25 章核心題 2 | 字串演算法：KMP、Rolling Hash 與回文 |
| 686. Repeated String Match | 第 25 章核心題 5 | 字串演算法：KMP、Rolling Hash 與回文 |
| 307. Range Sum Query - Mutable | 第 26 章核心題 1 | Range Query：Fenwick Tree 與 Segment Tree |
| 729. My Calendar I | 第 26 章核心題 3 | Range Query：Fenwick Tree 與 Segment Tree |
| 731. My Calendar II | 第 26 章核心題 4 | Range Query：Fenwick Tree 與 Segment Tree |
| 1395. Count Number of Teams | 第 26 章核心題 5 | Range Query：Fenwick Tree 與 Segment Tree |
| 146. LRU Cache | 第 27 章核心題 1 | 資料結構設計 |
| 380. Insert Delete GetRandom O(1) | 第 27 章核心題 2 | 資料結構設計 |
| 981. Time Based Key-Value Store | 第 27 章核心題 3 | 資料結構設計 |
| 1472. Design Browser History | 第 27 章核心題 4 | 資料結構設計 |
| 341. Flatten Nested List Iterator | 第 27 章核心題 5 | 資料結構設計 |
| 1146. Snapshot Array | 第 27 章難題 5 | 資料結構設計 |
| 50. Pow(x, n) | 第 28 章核心題 4 | Bit Manipulation 與數學 |
| 204. Count Primes | 第 28 章核心題 5 | Bit Manipulation 與數學 |
| 137. Single Number II | 第 28 章難題 1 | Bit Manipulation 與數學 |
| 201. Bitwise AND of Numbers Range | 第 28 章難題 2 | Bit Manipulation 與數學 |
| 54. Spiral Matrix | 第 29 章核心題 1 | Matrix、模擬與解析 |
| 48. Rotate Image | 第 29 章核心題 2 | Matrix、模擬與解析 |
| 73. Set Matrix Zeroes | 第 29 章核心題 3 | Matrix、模擬與解析 |
| 36. Valid Sudoku | 第 29 章核心題 4 | Matrix、模擬與解析 |
| 289. Game of Life | 第 29 章核心題 5 | Matrix、模擬與解析 |

### Hard（121 題）

| 題號與題名 | 位置 | Pattern |
|---|---|---|
| 41. First Missing Positive | 第 4 章難題 1 | Hashing 與計數 |
| 30. Substring with Concatenation of All Words | 第 4 章難題 2 | Hashing 與計數 |
| 149. Max Points on a Line | 第 4 章難題 3 | Hashing 與計數 |
| 336. Palindrome Pairs | 第 4 章難題 4 | Hashing 與計數 |
| 1224. Maximum Equal Frequency | 第 4 章難題 5 | Hashing 與計數 |
| 42. Trapping Rain Water | 第 5 章難題 1 | Two Pointers |
| 1793. Maximum Score of a Good Subarray | 第 5 章難題 4 | Two Pointers |
| 2009. Minimum Number of Operations to Make Array Continuous | 第 5 章難題 5 | Two Pointers |
| 76. Minimum Window Substring | 第 6 章難題 1 | Sliding Window |
| 239. Sliding Window Maximum | 第 6 章難題 2 | Sliding Window |
| 992. Subarrays with K Different Integers | 第 6 章難題 3 | Sliding Window |
| 995. Minimum Number of K Consecutive Bit Flips | 第 6 章難題 4 | Sliding Window |
| 2302. Count Subarrays With Score Less Than K | 第 6 章難題 5 | Sliding Window |
| 1074. Number of Submatrices That Sum to Target | 第 7 章難題 1 | Prefix Sum 與 Difference Array |
| 363. Max Sum of Rectangle No Larger Than K | 第 7 章難題 2 | Prefix Sum 與 Difference Array |
| 862. Shortest Subarray with Sum at Least K | 第 7 章難題 3 | Prefix Sum 與 Difference Array |
| 2281. Sum of Total Strength of Wizards | 第 7 章難題 5 | Prefix Sum 與 Difference Array |
| 4. Median of Two Sorted Arrays | 第 8 章難題 1 | Binary Search |
| 410. Split Array Largest Sum | 第 8 章難題 2 | Binary Search |
| 668. Kth Smallest Number in Multiplication Table | 第 8 章難題 3 | Binary Search |
| 719. Find K-th Smallest Pair Distance | 第 8 章難題 4 | Binary Search |
| 2040. Kth Smallest Product of Two Sorted Arrays | 第 8 章難題 5 | Binary Search |
| 218. The Skyline Problem | 第 9 章難題 1 | Intervals 與 Sweep Line |
| 759. Employee Free Time | 第 9 章難題 2 | Intervals 與 Sweep Line |
| 850. Rectangle Area II | 第 9 章難題 3 | Intervals 與 Sweep Line |
| 352. Data Stream as Disjoint Intervals | 第 9 章難題 4 | Intervals 與 Sweep Line |
| 1851. Minimum Interval to Include Each Query | 第 9 章難題 5 | Intervals 與 Sweep Line |
| 84. Largest Rectangle in Histogram | 第 10 章難題 1 | Stack 與 Monotonic Stack |
| 85. Maximal Rectangle | 第 10 章難題 2 | Stack 與 Monotonic Stack |
| 32. Longest Valid Parentheses | 第 10 章難題 3 | Stack 與 Monotonic Stack |
| 224. Basic Calculator | 第 10 章難題 4 | Stack 與 Monotonic Stack |
| 25. Reverse Nodes in k-Group | 第 11 章難題 1 | Linked List |
| 23. Merge k Sorted Lists | 第 11 章難題 2 | Linked List |
| 124. Binary Tree Maximum Path Sum | 第 12 章難題 1 | Binary Tree：DFS 與 BFS |
| 297. Serialize and Deserialize Binary Tree | 第 12 章難題 2 | Binary Tree：DFS 與 BFS |
| 968. Binary Tree Cameras | 第 12 章難題 3 | Binary Tree：DFS 與 BFS |
| 987. Vertical Order Traversal of a Binary Tree | 第 12 章難題 4 | Binary Tree：DFS 與 BFS |
| 2458. Height of Binary Tree After Subtree Removal Queries | 第 12 章難題 5 | Binary Tree：DFS 與 BFS |
| 212. Word Search II | 第 13 章難題 1 | BST 與 Trie |
| 745. Prefix and Suffix Search | 第 13 章難題 2 | BST 與 Trie |
| 1707. Maximum XOR With an Element From Array | 第 13 章難題 3 | BST 與 Trie |
| 472. Concatenated Words | 第 13 章難題 4 | BST 與 Trie |
| 295. Find Median from Data Stream | 第 14 章難題 1 | Heap：Top-K 與 K-way Merge |
| 480. Sliding Window Median | 第 14 章難題 2 | Heap：Top-K 與 K-way Merge |
| 502. IPO | 第 14 章難題 3 | Heap：Top-K 與 K-way Merge |
| 632. Smallest Range Covering Elements from K Lists | 第 14 章難題 4 | Heap：Top-K 與 K-way Merge |
| 857. Minimum Cost to Hire K Workers | 第 14 章難題 5 | Heap：Top-K 與 K-way Merge |
| 127. Word Ladder | 第 15 章難題 1 | Graph：BFS 與 DFS |
| 126. Word Ladder II | 第 15 章難題 2 | Graph：BFS 與 DFS |
| 1293. Shortest Path in a Grid with Obstacles Elimination | 第 15 章難題 3 | Graph：BFS 與 DFS |
| 847. Shortest Path Visiting All Nodes | 第 15 章難題 4 | Graph：BFS 與 DFS |
| 864. Shortest Path to Get All Keys | 第 15 章難題 5 | Graph：BFS 與 DFS |
| 269. Alien Dictionary | 第 16 章難題 1 | Topological Sort |
| 329. Longest Increasing Path in a Matrix | 第 16 章難題 2 | Topological Sort |
| 1203. Sort Items by Groups Respecting Dependencies | 第 16 章難題 3 | Topological Sort |
| 1857. Largest Color Value in a Directed Graph | 第 16 章難題 4 | Topological Sort |
| 2050. Parallel Courses III | 第 16 章難題 5 | Topological Sort |
| 685. Redundant Connection II | 第 17 章難題 1 | Union-Find |
| 778. Swim in Rising Water | 第 17 章難題 2 | Union-Find |
| 803. Bricks Falling When Hit | 第 17 章難題 3 | Union-Find |
| 1579. Remove Max Number of Edges to Keep Graph Fully Traversable | 第 17 章難題 4 | Union-Find |
| 1697. Checking Existence of Edge Length Limited Paths | 第 17 章難題 5 | Union-Find |
| 882. Reachable Nodes In Subdivided Graph | 第 18 章難題 1 | Shortest Path 與 Minimum Spanning Tree |
| 1368. Minimum Cost to Make at Least One Valid Path in a Grid | 第 18 章難題 2 | Shortest Path 與 Minimum Spanning Tree |
| 1928. Minimum Cost to Reach Destination in Time | 第 18 章難題 3 | Shortest Path 與 Minimum Spanning Tree |
| 2045. Second Minimum Time to Reach Destination | 第 18 章難題 4 | Shortest Path 與 Minimum Spanning Tree |
| 1192. Critical Connections in a Network | 第 18 章難題 5 | Shortest Path 與 Minimum Spanning Tree |
| 51. N-Queens | 第 19 章難題 1 | Backtracking |
| 37. Sudoku Solver | 第 19 章難題 2 | Backtracking |
| 282. Expression Add Operators | 第 19 章難題 3 | Backtracking |
| 1240. Tiling a Rectangle with the Fewest Squares | 第 19 章難題 5 | Backtracking |
| 135. Candy | 第 20 章難題 1 | Greedy |
| 330. Patching Array | 第 20 章難題 2 | Greedy |
| 630. Course Schedule III | 第 20 章難題 3 | Greedy |
| 871. Minimum Number of Refueling Stops | 第 20 章難題 4 | Greedy |
| 1326. Minimum Number of Taps to Open to Water a Garden | 第 20 章難題 5 | Greedy |
| 188. Best Time to Buy and Sell Stock IV | 第 21 章難題 1 | DP：一維與狀態機 |
| 354. Russian Doll Envelopes | 第 21 章難題 2 | DP：一維與狀態機 |
| 403. Frog Jump | 第 21 章難題 3 | DP：一維與狀態機 |
| 1235. Maximum Profit in Job Scheduling | 第 21 章難題 4 | DP：一維與狀態機 |
| 1335. Minimum Difficulty of a Job Schedule | 第 21 章難題 5 | DP：一維與狀態機 |
| 10. Regular Expression Matching | 第 22 章難題 1 | DP：二維與序列比對 |
| 44. Wildcard Matching | 第 22 章難題 2 | DP：二維與序列比對 |
| 115. Distinct Subsequences | 第 22 章難題 3 | DP：二維與序列比對 |
| 174. Dungeon Game | 第 22 章難題 4 | DP：二維與序列比對 |
| 1092. Shortest Common Supersequence | 第 22 章難題 5 | DP：二維與序列比對 |
| 1312. Minimum Insertion Steps to Make a String Palindrome | 第 23 章核心題 5 | DP：背包與區間 |
| 312. Burst Balloons | 第 23 章難題 1 | DP：背包與區間 |
| 664. Strange Printer | 第 23 章難題 2 | DP：背包與區間 |
| 546. Remove Boxes | 第 23 章難題 3 | DP：背包與區間 |
| 1000. Minimum Cost to Merge Stones | 第 23 章難題 4 | DP：背包與區間 |
| 1547. Minimum Cost to Cut a Stick | 第 23 章難題 5 | DP：背包與區間 |
| 902. Numbers At Most N Given Digit Set | 第 24 章核心題 5 | DP：樹、Bitmask 與數位 |
| 834. Sum of Distances in Tree | 第 24 章難題 1 | DP：樹、Bitmask 與數位 |
| 943. Find the Shortest Superstring | 第 24 章難題 2 | DP：樹、Bitmask 與數位 |
| 1349. Maximum Students Taking Exam | 第 24 章難題 3 | DP：樹、Bitmask 與數位 |
| 233. Number of Digit One | 第 24 章難題 4 | DP：樹、Bitmask 與數位 |
| 2376. Count Special Integers | 第 24 章難題 5 | DP：樹、Bitmask 與數位 |
| 214. Shortest Palindrome | 第 25 章難題 1 | 字串演算法：KMP、Rolling Hash 與回文 |
| 1044. Longest Duplicate Substring | 第 25 章難題 2 | 字串演算法：KMP、Rolling Hash 與回文 |
| 1392. Longest Happy Prefix | 第 25 章難題 3 | 字串演算法：KMP、Rolling Hash 與回文 |
| 1923. Longest Common Subpath | 第 25 章難題 4 | 字串演算法：KMP、Rolling Hash 與回文 |
| 2223. Sum of Scores of Built Strings | 第 25 章難題 5 | 字串演算法：KMP、Rolling Hash 與回文 |
| 315. Count of Smaller Numbers After Self | 第 26 章核心題 2 | Range Query：Fenwick Tree 與 Segment Tree |
| 327. Count of Range Sum | 第 26 章難題 1 | Range Query：Fenwick Tree 與 Segment Tree |
| 493. Reverse Pairs | 第 26 章難題 2 | Range Query：Fenwick Tree 與 Segment Tree |
| 699. Falling Squares | 第 26 章難題 3 | Range Query：Fenwick Tree 與 Segment Tree |
| 715. Range Module | 第 26 章難題 4 | Range Query：Fenwick Tree 與 Segment Tree |
| 2407. Longest Increasing Subsequence II | 第 26 章難題 5 | Range Query：Fenwick Tree 與 Segment Tree |
| 460. LFU Cache | 第 27 章難題 1 | 資料結構設計 |
| 432. All O(1) Data Structure | 第 27 章難題 2 | 資料結構設計 |
| 716. Max Stack | 第 27 章難題 3 | 資料結構設計 |
| 895. Maximum Frequency Stack | 第 27 章難題 4 | 資料結構設計 |
| 60. Permutation Sequence | 第 28 章難題 3 | Bit Manipulation 與數學 |
| 829. Consecutive Numbers Sum | 第 28 章難題 4 | Bit Manipulation 與數學 |
| 1611. Minimum One Bit Operations to Make Integers Zero | 第 28 章難題 5 | Bit Manipulation 與數學 |
| 65. Valid Number | 第 29 章難題 1 | Matrix、模擬與解析 |
| 68. Text Justification | 第 29 章難題 2 | Matrix、模擬與解析 |
| 591. Tag Validator | 第 29 章難題 3 | Matrix、模擬與解析 |
| 726. Number of Atoms | 第 29 章難題 4 | Matrix、模擬與解析 |
| 770. Basic Calculator IV | 第 29 章難題 5 | Matrix、模擬與解析 |

## C.4 依常見程度

分級依據見 C.1。這是定性分類，不是統計，不代表任何公司的實際出題頻率。每章一列，括號內是題目在該章的位置。

### 高頻清單常見（106 題）

收錄在 Blind 75、NeetCode 150 等公開高頻清單中的題目。這一級涵蓋了大部分 pattern 的標準形，是時間最少時也應該全部做過的部分。

| 章 | 題目 |
|---|---|
| 第 4 章 Hashing 與計數 | 1. Two Sum（核心題 1）、49. Group Anagrams（核心題 2）、128. Longest Consecutive Sequence（核心題 3） |
| 第 5 章 Two Pointers | 167. Two Sum II - Input Array Is Sorted（核心題 1）、15. 3Sum（核心題 2）、11. Container With Most Water（核心題 3）、42. Trapping Rain Water（難題 1）、287. Find the Duplicate Number（難題 2） |
| 第 6 章 Sliding Window | 3. Longest Substring Without Repeating Characters（核心題 1）、424. Longest Repeating Character Replacement（核心題 3）、567. Permutation in String（核心題 4）、76. Minimum Window Substring（難題 1）、239. Sliding Window Maximum（難題 2） |
| 第 7 章 Prefix Sum 與 Difference Array | 238. Product of Array Except Self（核心題 1） |
| 第 8 章 Binary Search | 33. Search in Rotated Sorted Array（核心題 2）、153. Find Minimum in Rotated Sorted Array（核心題 3）、875. Koko Eating Bananas（核心題 4）、4. Median of Two Sorted Arrays（難題 1） |
| 第 9 章 Intervals 與 Sweep Line | 56. Merge Intervals（核心題 1）、57. Insert Interval（核心題 2）、435. Non-overlapping Intervals（核心題 3）、253. Meeting Rooms II（核心題 5）、1851. Minimum Interval to Include Each Query（難題 5） |
| 第 10 章 Stack 與 Monotonic Stack | 20. Valid Parentheses（核心題 1）、155. Min Stack（核心題 2）、150. Evaluate Reverse Polish Notation（核心題 3）、739. Daily Temperatures（核心題 4）、84. Largest Rectangle in Histogram（難題 1） |
| 第 11 章 Linked List | 206. Reverse Linked List（核心題 1）、21. Merge Two Sorted Lists（核心題 2）、141／142. Linked List Cycle（核心題 3）、19. Remove Nth Node From End of List（核心題 4）、143. Reorder List（核心題 5）、25. Reverse Nodes in k-Group（難題 1）、23. Merge k Sorted Lists（難題 2）、138. Copy List with Random Pointer（難題 3） |
| 第 12 章 Binary Tree：DFS 與 BFS | 102. Binary Tree Level Order Traversal（核心題 1）、199. Binary Tree Right Side View（核心題 2）、543. Diameter of Binary Tree（核心題 3）、105. Construct Binary Tree from Preorder and Inorder Traversal（核心題 4）、124. Binary Tree Maximum Path Sum（難題 1）、297. Serialize and Deserialize Binary Tree（難題 2） |
| 第 13 章 BST 與 Trie | 98. Validate Binary Search Tree（核心題 1）、230. Kth Smallest Element in a BST（核心題 2）、208. Implement Trie (Prefix Tree)（核心題 4）、211. Design Add and Search Words Data Structure（核心題 5）、212. Word Search II（難題 1） |
| 第 14 章 Heap：Top-K 與 K-way Merge | 215. Kth Largest Element in an Array（核心題 1）、347. Top K Frequent Elements（核心題 2）、973. K Closest Points to Origin（核心題 3）、621. Task Scheduler（核心題 4）、295. Find Median from Data Stream（難題 1） |
| 第 15 章 Graph：BFS 與 DFS | 200. Number of Islands（核心題 1）、133. Clone Graph（核心題 2）、994. Rotting Oranges（核心題 3）、417. Pacific Atlantic Water Flow（核心題 4）、130. Surrounded Regions（核心題 5）、127. Word Ladder（難題 1） |
| 第 16 章 Topological Sort | 207. Course Schedule（核心題 1）、210. Course Schedule II（核心題 2）、269. Alien Dictionary（難題 1）、329. Longest Increasing Path in a Matrix（難題 2） |
| 第 17 章 Union-Find | 684. Redundant Connection（核心題 2）、778. Swim in Rising Water（難題 2） |
| 第 18 章 Shortest Path 與 Minimum Spanning Tree | 743. Network Delay Time（核心題 1）、787. Cheapest Flights Within K Stops（核心題 2）、1584. Min Cost to Connect All Points（核心題 5） |
| 第 19 章 Backtracking | 78. Subsets（核心題 1）、46. Permutations（核心題 2）、39. Combination Sum（核心題 3）、17. Letter Combinations of a Phone Number（核心題 4）、79. Word Search（核心題 5）、51. N-Queens（難題 1） |
| 第 20 章 Greedy | 55. Jump Game（核心題 1）、45. Jump Game II（核心題 2）、134. Gas Station（核心題 3）、763. Partition Labels（核心題 4）、846. Hand of Straights（核心題 5） |
| 第 21 章 DP：一維與狀態機 | 198. House Robber（核心題 1）、322. Coin Change（核心題 2）、300. Longest Increasing Subsequence（核心題 3）、139. Word Break（核心題 4）、91. Decode Ways（核心題 5） |
| 第 22 章 DP：二維與序列比對 | 62. Unique Paths（核心題 1）、1143. Longest Common Subsequence（核心題 3）、72. Edit Distance（核心題 4）、97. Interleaving String（核心題 5）、10. Regular Expression Matching（難題 1）、115. Distinct Subsequences（難題 3） |
| 第 23 章 DP：背包與區間 | 416. Partition Equal Subset Sum（核心題 1）、494. Target Sum（核心題 2）、518. Coin Change II（核心題 3）、312. Burst Balloons（難題 1） |
| 第 24 章 DP：樹、Bitmask 與數位 | 338. Counting Bits（核心題 2） |
| 第 25 章 字串演算法：KMP、Rolling Hash 與回文 | 5. Longest Palindromic Substring（核心題 1）、647. Palindromic Substrings（核心題 2） |
| 第 27 章 資料結構設計 | 146. LRU Cache（核心題 1）、981. Time Based Key-Value Store（核心題 3） |
| 第 28 章 Bit Manipulation 與數學 | 136. Single Number（核心題 1）、268. Missing Number（核心題 2）、191. Number of 1 Bits（核心題 3）、50. Pow(x, n)（核心題 4） |
| 第 29 章 Matrix、模擬與解析 | 54. Spiral Matrix（核心題 1）、48. Rotate Image（核心題 2）、73. Set Matrix Zeroes（核心題 3）、36. Valid Sudoku（核心題 4） |

### 面經常見（57 題）

不在上述清單，但在公開面經與其他公開題單中經常被提到的經典題與標準變形。它們多半是高頻題換一個條件，例如加上負數、改成計數、改成串流。

| 章 | 題目 |
|---|---|
| 第 4 章 Hashing 與計數 | 454. 4Sum II（核心題 4）、554. Brick Wall（核心題 5）、41. First Missing Positive（難題 1）、149. Max Points on a Line（難題 3） |
| 第 5 章 Two Pointers | 75. Sort Colors（核心題 4）、977. Squares of a Sorted Array（核心題 5） |
| 第 6 章 Sliding Window | 209. Minimum Size Subarray Sum（核心題 2）、438. Find All Anagrams in a String（核心題 5） |
| 第 7 章 Prefix Sum 與 Difference Array | 560. Subarray Sum Equals K（核心題 2）、525. Contiguous Array（核心題 3）、304. Range Sum Query 2D - Immutable（核心題 4）、1094. Car Pooling（核心題 5） |
| 第 8 章 Binary Search | 34. Find First and Last Position of Element in Sorted Array（核心題 1）、1011. Capacity To Ship Packages Within D Days（核心題 5）、410. Split Array Largest Sum（難題 2） |
| 第 9 章 Intervals 與 Sweep Line | 986. Interval List Intersections（核心題 4）、759. Employee Free Time（難題 2） |
| 第 10 章 Stack 與 Monotonic Stack | 503. Next Greater Element II（核心題 5）、224. Basic Calculator（難題 4） |
| 第 11 章 Linked List | 148. Sort List（難題 4） |
| 第 12 章 Binary Tree：DFS 與 BFS | 236. Lowest Common Ancestor of a Binary Tree（核心題 5）、987. Vertical Order Traversal of a Binary Tree（難題 4） |
| 第 13 章 BST 與 Trie | 450. Delete Node in a BST（核心題 3） |
| 第 14 章 Heap：Top-K 與 K-way Merge | 767. Reorganize String（核心題 5） |
| 第 16 章 Topological Sort | 310. Minimum Height Trees（核心題 4） |
| 第 17 章 Union-Find | 547. Number of Provinces（核心題 1）、721. Accounts Merge（核心題 3）、1319. Number of Operations to Make Network Connected（核心題 5） |
| 第 18 章 Shortest Path 與 Minimum Spanning Tree | 1631. Path With Minimum Effort（核心題 3）、1192. Critical Connections in a Network（難題 5） |
| 第 19 章 Backtracking | 37. Sudoku Solver（難題 2）、282. Expression Add Operators（難題 3）、698. Partition to K Equal Sum Subsets（難題 4） |
| 第 20 章 Greedy | 135. Candy（難題 1） |
| 第 21 章 DP：一維與狀態機 | 188. Best Time to Buy and Sell Stock IV（難題 1）、354. Russian Doll Envelopes（難題 2）、1235. Maximum Profit in Job Scheduling（難題 4） |
| 第 22 章 DP：二維與序列比對 | 64. Minimum Path Sum（核心題 2）、44. Wildcard Matching（難題 2） |
| 第 23 章 DP：背包與區間 | 516. Longest Palindromic Subsequence（核心題 4） |
| 第 24 章 DP：樹、Bitmask 與數位 | 337. House Robber III（核心題 1） |
| 第 25 章 字串演算法：KMP、Rolling Hash 與回文 | 28. Find the Index of the First Occurrence in a String（核心題 3）、459. Repeated Substring Pattern（核心題 4） |
| 第 26 章 Range Query：Fenwick Tree 與 Segment Tree | 307. Range Sum Query - Mutable（核心題 1）、315. Count of Smaller Numbers After Self（核心題 2）、729. My Calendar I（核心題 3） |
| 第 27 章 資料結構設計 | 380. Insert Delete GetRandom O(1)（核心題 2）、1472. Design Browser History（核心題 4）、341. Flatten Nested List Iterator（核心題 5）、460. LFU Cache（難題 1）、716. Max Stack（難題 3）、895. Maximum Frequency Stack（難題 4）、1146. Snapshot Array（難題 5） |
| 第 28 章 Bit Manipulation 與數學 | 204. Count Primes（核心題 5）、137. Single Number II（難題 1） |
| 第 29 章 Matrix、模擬與解析 | 289. Game of Life（核心題 5）、68. Text Justification（難題 2） |

### 延伸與上限題（97 題）

較少出現在公開高頻清單的題目，用來補齊 pattern 的主要變形或展示上限。面試中直接遇到的機會較低，但它們的關鍵突破常是高頻題 follow-up 的答案。

| 章 | 題目 |
|---|---|
| 第 4 章 Hashing 與計數 | 30. Substring with Concatenation of All Words（難題 2）、336. Palindrome Pairs（難題 4）、1224. Maximum Equal Frequency（難題 5） |
| 第 5 章 Two Pointers | 923. 3Sum With Multiplicity（難題 3）、1793. Maximum Score of a Good Subarray（難題 4）、2009. Minimum Number of Operations to Make Array Continuous（難題 5） |
| 第 6 章 Sliding Window | 992. Subarrays with K Different Integers（難題 3）、995. Minimum Number of K Consecutive Bit Flips（難題 4）、2302. Count Subarrays With Score Less Than K（難題 5） |
| 第 7 章 Prefix Sum 與 Difference Array | 1074. Number of Submatrices That Sum to Target（難題 1）、363. Max Sum of Rectangle No Larger Than K（難題 2）、862. Shortest Subarray with Sum at Least K（難題 3）、1371. Find the Longest Substring Containing Vowels in Even Counts（難題 4）、2281. Sum of Total Strength of Wizards（難題 5） |
| 第 8 章 Binary Search | 668. Kth Smallest Number in Multiplication Table（難題 3）、719. Find K-th Smallest Pair Distance（難題 4）、2040. Kth Smallest Product of Two Sorted Arrays（難題 5） |
| 第 9 章 Intervals 與 Sweep Line | 218. The Skyline Problem（難題 1）、850. Rectangle Area II（難題 3）、352. Data Stream as Disjoint Intervals（難題 4） |
| 第 10 章 Stack 與 Monotonic Stack | 85. Maximal Rectangle（難題 2）、32. Longest Valid Parentheses（難題 3）、907. Sum of Subarray Minimums（難題 5） |
| 第 11 章 Linked List | 1171. Remove Zero Sum Consecutive Nodes from Linked List（難題 5） |
| 第 12 章 Binary Tree：DFS 與 BFS | 968. Binary Tree Cameras（難題 3）、2458. Height of Binary Tree After Subtree Removal Queries（難題 5） |
| 第 13 章 BST 與 Trie | 745. Prefix and Suffix Search（難題 2）、1707. Maximum XOR With an Element From Array（難題 3）、472. Concatenated Words（難題 4）、99. Recover Binary Search Tree（難題 5） |
| 第 14 章 Heap：Top-K 與 K-way Merge | 480. Sliding Window Median（難題 2）、502. IPO（難題 3）、632. Smallest Range Covering Elements from K Lists（難題 4）、857. Minimum Cost to Hire K Workers（難題 5） |
| 第 15 章 Graph：BFS 與 DFS | 126. Word Ladder II（難題 2）、1293. Shortest Path in a Grid with Obstacles Elimination（難題 3）、847. Shortest Path Visiting All Nodes（難題 4）、864. Shortest Path to Get All Keys（難題 5） |
| 第 16 章 Topological Sort | 802. Find Eventual Safe States（核心題 3）、1462. Course Schedule IV（核心題 5）、1203. Sort Items by Groups Respecting Dependencies（難題 3）、1857. Largest Color Value in a Directed Graph（難題 4）、2050. Parallel Courses III（難題 5） |
| 第 17 章 Union-Find | 990. Satisfiability of Equality Equations（核心題 4）、685. Redundant Connection II（難題 1）、803. Bricks Falling When Hit（難題 3）、1579. Remove Max Number of Edges to Keep Graph Fully Traversable（難題 4）、1697. Checking Existence of Edge Length Limited Paths（難題 5） |
| 第 18 章 Shortest Path 與 Minimum Spanning Tree | 1514. Path with Maximum Probability（核心題 4）、882. Reachable Nodes In Subdivided Graph（難題 1）、1368. Minimum Cost to Make at Least One Valid Path in a Grid（難題 2）、1928. Minimum Cost to Reach Destination in Time（難題 3）、2045. Second Minimum Time to Reach Destination（難題 4） |
| 第 19 章 Backtracking | 1240. Tiling a Rectangle with the Fewest Squares（難題 5） |
| 第 20 章 Greedy | 330. Patching Array（難題 2）、630. Course Schedule III（難題 3）、871. Minimum Number of Refueling Stops（難題 4）、1326. Minimum Number of Taps to Open to Water a Garden（難題 5） |
| 第 21 章 DP：一維與狀態機 | 403. Frog Jump（難題 3）、1335. Minimum Difficulty of a Job Schedule（難題 5） |
| 第 22 章 DP：二維與序列比對 | 174. Dungeon Game（難題 4）、1092. Shortest Common Supersequence（難題 5） |
| 第 23 章 DP：背包與區間 | 1312. Minimum Insertion Steps to Make a String Palindrome（核心題 5）、664. Strange Printer（難題 2）、546. Remove Boxes（難題 3）、1000. Minimum Cost to Merge Stones（難題 4）、1547. Minimum Cost to Cut a Stick（難題 5） |
| 第 24 章 DP：樹、Bitmask 與數位 | 526. Beautiful Arrangement（核心題 3）、1986. Minimum Number of Work Sessions to Finish the Tasks（核心題 4）、902. Numbers At Most N Given Digit Set（核心題 5）、834. Sum of Distances in Tree（難題 1）、943. Find the Shortest Superstring（難題 2）、1349. Maximum Students Taking Exam（難題 3）、233. Number of Digit One（難題 4）、2376. Count Special Integers（難題 5） |
| 第 25 章 字串演算法：KMP、Rolling Hash 與回文 | 686. Repeated String Match（核心題 5）、214. Shortest Palindrome（難題 1）、1044. Longest Duplicate Substring（難題 2）、1392. Longest Happy Prefix（難題 3）、1923. Longest Common Subpath（難題 4）、2223. Sum of Scores of Built Strings（難題 5） |
| 第 26 章 Range Query：Fenwick Tree 與 Segment Tree | 731. My Calendar II（核心題 4）、1395. Count Number of Teams（核心題 5）、327. Count of Range Sum（難題 1）、493. Reverse Pairs（難題 2）、699. Falling Squares（難題 3）、715. Range Module（難題 4）、2407. Longest Increasing Subsequence II（難題 5） |
| 第 27 章 資料結構設計 | 432. All O(1) Data Structure（難題 2） |
| 第 28 章 Bit Manipulation 與數學 | 201. Bitwise AND of Numbers Range（難題 2）、60. Permutation Sequence（難題 3）、829. Consecutive Numbers Sum（難題 4）、1611. Minimum One Bit Operations to Make Integers Zero（難題 5） |
| 第 29 章 Matrix、模擬與解析 | 65. Valid Number（難題 1）、591. Tag Validator（難題 3）、726. Number of Atoms（難題 4）、770. Basic Calculator IV（難題 5） |

## C.5 依 LeetCode 題號排序

已知題號、想找本書在哪裡講解時查這張表。141 與 142 合併在同一列。

| 題號 | 題名 | 位置 | 難度 |
|---|---|---|---|
| 1 | Two Sum | 第 4 章核心題 1 | Easy |
| 3 | Longest Substring Without Repeating Characters | 第 6 章核心題 1 | Medium |
| 4 | Median of Two Sorted Arrays | 第 8 章難題 1 | Hard |
| 5 | Longest Palindromic Substring | 第 25 章核心題 1 | Medium |
| 10 | Regular Expression Matching | 第 22 章難題 1 | Hard |
| 11 | Container With Most Water | 第 5 章核心題 3 | Medium |
| 15 | 3Sum | 第 5 章核心題 2 | Medium |
| 17 | Letter Combinations of a Phone Number | 第 19 章核心題 4 | Medium |
| 19 | Remove Nth Node From End of List | 第 11 章核心題 4 | Medium |
| 20 | Valid Parentheses | 第 10 章核心題 1 | Easy |
| 21 | Merge Two Sorted Lists | 第 11 章核心題 2 | Easy |
| 23 | Merge k Sorted Lists | 第 11 章難題 2 | Hard |
| 25 | Reverse Nodes in k-Group | 第 11 章難題 1 | Hard |
| 28 | Find the Index of the First Occurrence in a String | 第 25 章核心題 3 | Easy |
| 30 | Substring with Concatenation of All Words | 第 4 章難題 2 | Hard |
| 32 | Longest Valid Parentheses | 第 10 章難題 3 | Hard |
| 33 | Search in Rotated Sorted Array | 第 8 章核心題 2 | Medium |
| 34 | Find First and Last Position of Element in Sorted Array | 第 8 章核心題 1 | Medium |
| 36 | Valid Sudoku | 第 29 章核心題 4 | Medium |
| 37 | Sudoku Solver | 第 19 章難題 2 | Hard |
| 39 | Combination Sum | 第 19 章核心題 3 | Medium |
| 41 | First Missing Positive | 第 4 章難題 1 | Hard |
| 42 | Trapping Rain Water | 第 5 章難題 1 | Hard |
| 44 | Wildcard Matching | 第 22 章難題 2 | Hard |
| 45 | Jump Game II | 第 20 章核心題 2 | Medium |
| 46 | Permutations | 第 19 章核心題 2 | Medium |
| 48 | Rotate Image | 第 29 章核心題 2 | Medium |
| 49 | Group Anagrams | 第 4 章核心題 2 | Medium |
| 50 | Pow(x, n) | 第 28 章核心題 4 | Medium |
| 51 | N-Queens | 第 19 章難題 1 | Hard |
| 54 | Spiral Matrix | 第 29 章核心題 1 | Medium |
| 55 | Jump Game | 第 20 章核心題 1 | Medium |
| 56 | Merge Intervals | 第 9 章核心題 1 | Medium |
| 57 | Insert Interval | 第 9 章核心題 2 | Medium |
| 60 | Permutation Sequence | 第 28 章難題 3 | Hard |
| 62 | Unique Paths | 第 22 章核心題 1 | Medium |
| 64 | Minimum Path Sum | 第 22 章核心題 2 | Medium |
| 65 | Valid Number | 第 29 章難題 1 | Hard |
| 68 | Text Justification | 第 29 章難題 2 | Hard |
| 72 | Edit Distance | 第 22 章核心題 4 | Medium |
| 73 | Set Matrix Zeroes | 第 29 章核心題 3 | Medium |
| 75 | Sort Colors | 第 5 章核心題 4 | Medium |
| 76 | Minimum Window Substring | 第 6 章難題 1 | Hard |
| 78 | Subsets | 第 19 章核心題 1 | Medium |
| 79 | Word Search | 第 19 章核心題 5 | Medium |
| 84 | Largest Rectangle in Histogram | 第 10 章難題 1 | Hard |
| 85 | Maximal Rectangle | 第 10 章難題 2 | Hard |
| 91 | Decode Ways | 第 21 章核心題 5 | Medium |
| 97 | Interleaving String | 第 22 章核心題 5 | Medium |
| 98 | Validate Binary Search Tree | 第 13 章核心題 1 | Medium |
| 99 | Recover Binary Search Tree | 第 13 章難題 5 | Medium |
| 102 | Binary Tree Level Order Traversal | 第 12 章核心題 1 | Medium |
| 105 | Construct Binary Tree from Preorder and Inorder Traversal | 第 12 章核心題 4 | Medium |
| 115 | Distinct Subsequences | 第 22 章難題 3 | Hard |
| 124 | Binary Tree Maximum Path Sum | 第 12 章難題 1 | Hard |
| 126 | Word Ladder II | 第 15 章難題 2 | Hard |
| 127 | Word Ladder | 第 15 章難題 1 | Hard |
| 128 | Longest Consecutive Sequence | 第 4 章核心題 3 | Medium |
| 130 | Surrounded Regions | 第 15 章核心題 5 | Medium |
| 133 | Clone Graph | 第 15 章核心題 2 | Medium |
| 134 | Gas Station | 第 20 章核心題 3 | Medium |
| 135 | Candy | 第 20 章難題 1 | Hard |
| 136 | Single Number | 第 28 章核心題 1 | Easy |
| 137 | Single Number II | 第 28 章難題 1 | Medium |
| 138 | Copy List with Random Pointer | 第 11 章難題 3 | Medium |
| 139 | Word Break | 第 21 章核心題 4 | Medium |
| 141／142 | Linked List Cycle（含 142. Linked List Cycle II） | 第 11 章核心題 3 | Easy |
| 143 | Reorder List | 第 11 章核心題 5 | Medium |
| 146 | LRU Cache | 第 27 章核心題 1 | Medium |
| 148 | Sort List | 第 11 章難題 4 | Medium |
| 149 | Max Points on a Line | 第 4 章難題 3 | Hard |
| 150 | Evaluate Reverse Polish Notation | 第 10 章核心題 3 | Medium |
| 153 | Find Minimum in Rotated Sorted Array | 第 8 章核心題 3 | Medium |
| 155 | Min Stack | 第 10 章核心題 2 | Medium |
| 167 | Two Sum II - Input Array Is Sorted | 第 5 章核心題 1 | Medium |
| 174 | Dungeon Game | 第 22 章難題 4 | Hard |
| 188 | Best Time to Buy and Sell Stock IV | 第 21 章難題 1 | Hard |
| 191 | Number of 1 Bits | 第 28 章核心題 3 | Easy |
| 198 | House Robber | 第 21 章核心題 1 | Medium |
| 199 | Binary Tree Right Side View | 第 12 章核心題 2 | Medium |
| 200 | Number of Islands | 第 15 章核心題 1 | Medium |
| 201 | Bitwise AND of Numbers Range | 第 28 章難題 2 | Medium |
| 204 | Count Primes | 第 28 章核心題 5 | Medium |
| 206 | Reverse Linked List | 第 11 章核心題 1 | Easy |
| 207 | Course Schedule | 第 16 章核心題 1 | Medium |
| 208 | Implement Trie (Prefix Tree) | 第 13 章核心題 4 | Medium |
| 209 | Minimum Size Subarray Sum | 第 6 章核心題 2 | Medium |
| 210 | Course Schedule II | 第 16 章核心題 2 | Medium |
| 211 | Design Add and Search Words Data Structure | 第 13 章核心題 5 | Medium |
| 212 | Word Search II | 第 13 章難題 1 | Hard |
| 214 | Shortest Palindrome | 第 25 章難題 1 | Hard |
| 215 | Kth Largest Element in an Array | 第 14 章核心題 1 | Medium |
| 218 | The Skyline Problem | 第 9 章難題 1 | Hard |
| 224 | Basic Calculator | 第 10 章難題 4 | Hard |
| 230 | Kth Smallest Element in a BST | 第 13 章核心題 2 | Medium |
| 233 | Number of Digit One | 第 24 章難題 4 | Hard |
| 236 | Lowest Common Ancestor of a Binary Tree | 第 12 章核心題 5 | Medium |
| 238 | Product of Array Except Self | 第 7 章核心題 1 | Medium |
| 239 | Sliding Window Maximum | 第 6 章難題 2 | Hard |
| 253 | Meeting Rooms II | 第 9 章核心題 5 | Medium |
| 268 | Missing Number | 第 28 章核心題 2 | Easy |
| 269 | Alien Dictionary | 第 16 章難題 1 | Hard |
| 282 | Expression Add Operators | 第 19 章難題 3 | Hard |
| 287 | Find the Duplicate Number | 第 5 章難題 2 | Medium |
| 289 | Game of Life | 第 29 章核心題 5 | Medium |
| 295 | Find Median from Data Stream | 第 14 章難題 1 | Hard |
| 297 | Serialize and Deserialize Binary Tree | 第 12 章難題 2 | Hard |
| 300 | Longest Increasing Subsequence | 第 21 章核心題 3 | Medium |
| 304 | Range Sum Query 2D - Immutable | 第 7 章核心題 4 | Medium |
| 307 | Range Sum Query - Mutable | 第 26 章核心題 1 | Medium |
| 310 | Minimum Height Trees | 第 16 章核心題 4 | Medium |
| 312 | Burst Balloons | 第 23 章難題 1 | Hard |
| 315 | Count of Smaller Numbers After Self | 第 26 章核心題 2 | Hard |
| 322 | Coin Change | 第 21 章核心題 2 | Medium |
| 327 | Count of Range Sum | 第 26 章難題 1 | Hard |
| 329 | Longest Increasing Path in a Matrix | 第 16 章難題 2 | Hard |
| 330 | Patching Array | 第 20 章難題 2 | Hard |
| 336 | Palindrome Pairs | 第 4 章難題 4 | Hard |
| 337 | House Robber III | 第 24 章核心題 1 | Medium |
| 338 | Counting Bits | 第 24 章核心題 2 | Easy |
| 341 | Flatten Nested List Iterator | 第 27 章核心題 5 | Medium |
| 347 | Top K Frequent Elements | 第 14 章核心題 2 | Medium |
| 352 | Data Stream as Disjoint Intervals | 第 9 章難題 4 | Hard |
| 354 | Russian Doll Envelopes | 第 21 章難題 2 | Hard |
| 363 | Max Sum of Rectangle No Larger Than K | 第 7 章難題 2 | Hard |
| 380 | Insert Delete GetRandom O(1) | 第 27 章核心題 2 | Medium |
| 403 | Frog Jump | 第 21 章難題 3 | Hard |
| 410 | Split Array Largest Sum | 第 8 章難題 2 | Hard |
| 416 | Partition Equal Subset Sum | 第 23 章核心題 1 | Medium |
| 417 | Pacific Atlantic Water Flow | 第 15 章核心題 4 | Medium |
| 424 | Longest Repeating Character Replacement | 第 6 章核心題 3 | Medium |
| 432 | All O(1) Data Structure | 第 27 章難題 2 | Hard |
| 435 | Non-overlapping Intervals | 第 9 章核心題 3 | Medium |
| 438 | Find All Anagrams in a String | 第 6 章核心題 5 | Medium |
| 450 | Delete Node in a BST | 第 13 章核心題 3 | Medium |
| 454 | 4Sum II | 第 4 章核心題 4 | Medium |
| 459 | Repeated Substring Pattern | 第 25 章核心題 4 | Easy |
| 460 | LFU Cache | 第 27 章難題 1 | Hard |
| 472 | Concatenated Words | 第 13 章難題 4 | Hard |
| 480 | Sliding Window Median | 第 14 章難題 2 | Hard |
| 493 | Reverse Pairs | 第 26 章難題 2 | Hard |
| 494 | Target Sum | 第 23 章核心題 2 | Medium |
| 502 | IPO | 第 14 章難題 3 | Hard |
| 503 | Next Greater Element II | 第 10 章核心題 5 | Medium |
| 516 | Longest Palindromic Subsequence | 第 23 章核心題 4 | Medium |
| 518 | Coin Change II | 第 23 章核心題 3 | Medium |
| 525 | Contiguous Array | 第 7 章核心題 3 | Medium |
| 526 | Beautiful Arrangement | 第 24 章核心題 3 | Medium |
| 543 | Diameter of Binary Tree | 第 12 章核心題 3 | Easy |
| 546 | Remove Boxes | 第 23 章難題 3 | Hard |
| 547 | Number of Provinces | 第 17 章核心題 1 | Medium |
| 554 | Brick Wall | 第 4 章核心題 5 | Medium |
| 560 | Subarray Sum Equals K | 第 7 章核心題 2 | Medium |
| 567 | Permutation in String | 第 6 章核心題 4 | Medium |
| 591 | Tag Validator | 第 29 章難題 3 | Hard |
| 621 | Task Scheduler | 第 14 章核心題 4 | Medium |
| 630 | Course Schedule III | 第 20 章難題 3 | Hard |
| 632 | Smallest Range Covering Elements from K Lists | 第 14 章難題 4 | Hard |
| 647 | Palindromic Substrings | 第 25 章核心題 2 | Medium |
| 664 | Strange Printer | 第 23 章難題 2 | Hard |
| 668 | Kth Smallest Number in Multiplication Table | 第 8 章難題 3 | Hard |
| 684 | Redundant Connection | 第 17 章核心題 2 | Medium |
| 685 | Redundant Connection II | 第 17 章難題 1 | Hard |
| 686 | Repeated String Match | 第 25 章核心題 5 | Medium |
| 698 | Partition to K Equal Sum Subsets | 第 19 章難題 4 | Medium |
| 699 | Falling Squares | 第 26 章難題 3 | Hard |
| 715 | Range Module | 第 26 章難題 4 | Hard |
| 716 | Max Stack | 第 27 章難題 3 | Hard |
| 719 | Find K-th Smallest Pair Distance | 第 8 章難題 4 | Hard |
| 721 | Accounts Merge | 第 17 章核心題 3 | Medium |
| 726 | Number of Atoms | 第 29 章難題 4 | Hard |
| 729 | My Calendar I | 第 26 章核心題 3 | Medium |
| 731 | My Calendar II | 第 26 章核心題 4 | Medium |
| 739 | Daily Temperatures | 第 10 章核心題 4 | Medium |
| 743 | Network Delay Time | 第 18 章核心題 1 | Medium |
| 745 | Prefix and Suffix Search | 第 13 章難題 2 | Hard |
| 759 | Employee Free Time | 第 9 章難題 2 | Hard |
| 763 | Partition Labels | 第 20 章核心題 4 | Medium |
| 767 | Reorganize String | 第 14 章核心題 5 | Medium |
| 770 | Basic Calculator IV | 第 29 章難題 5 | Hard |
| 778 | Swim in Rising Water | 第 17 章難題 2 | Hard |
| 787 | Cheapest Flights Within K Stops | 第 18 章核心題 2 | Medium |
| 802 | Find Eventual Safe States | 第 16 章核心題 3 | Medium |
| 803 | Bricks Falling When Hit | 第 17 章難題 3 | Hard |
| 829 | Consecutive Numbers Sum | 第 28 章難題 4 | Hard |
| 834 | Sum of Distances in Tree | 第 24 章難題 1 | Hard |
| 846 | Hand of Straights | 第 20 章核心題 5 | Medium |
| 847 | Shortest Path Visiting All Nodes | 第 15 章難題 4 | Hard |
| 850 | Rectangle Area II | 第 9 章難題 3 | Hard |
| 857 | Minimum Cost to Hire K Workers | 第 14 章難題 5 | Hard |
| 862 | Shortest Subarray with Sum at Least K | 第 7 章難題 3 | Hard |
| 864 | Shortest Path to Get All Keys | 第 15 章難題 5 | Hard |
| 871 | Minimum Number of Refueling Stops | 第 20 章難題 4 | Hard |
| 875 | Koko Eating Bananas | 第 8 章核心題 4 | Medium |
| 882 | Reachable Nodes In Subdivided Graph | 第 18 章難題 1 | Hard |
| 895 | Maximum Frequency Stack | 第 27 章難題 4 | Hard |
| 902 | Numbers At Most N Given Digit Set | 第 24 章核心題 5 | Hard |
| 907 | Sum of Subarray Minimums | 第 10 章難題 5 | Medium |
| 923 | 3Sum With Multiplicity | 第 5 章難題 3 | Medium |
| 943 | Find the Shortest Superstring | 第 24 章難題 2 | Hard |
| 968 | Binary Tree Cameras | 第 12 章難題 3 | Hard |
| 973 | K Closest Points to Origin | 第 14 章核心題 3 | Medium |
| 977 | Squares of a Sorted Array | 第 5 章核心題 5 | Easy |
| 981 | Time Based Key-Value Store | 第 27 章核心題 3 | Medium |
| 986 | Interval List Intersections | 第 9 章核心題 4 | Medium |
| 987 | Vertical Order Traversal of a Binary Tree | 第 12 章難題 4 | Hard |
| 990 | Satisfiability of Equality Equations | 第 17 章核心題 4 | Medium |
| 992 | Subarrays with K Different Integers | 第 6 章難題 3 | Hard |
| 994 | Rotting Oranges | 第 15 章核心題 3 | Medium |
| 995 | Minimum Number of K Consecutive Bit Flips | 第 6 章難題 4 | Hard |
| 1000 | Minimum Cost to Merge Stones | 第 23 章難題 4 | Hard |
| 1011 | Capacity To Ship Packages Within D Days | 第 8 章核心題 5 | Medium |
| 1044 | Longest Duplicate Substring | 第 25 章難題 2 | Hard |
| 1074 | Number of Submatrices That Sum to Target | 第 7 章難題 1 | Hard |
| 1092 | Shortest Common Supersequence | 第 22 章難題 5 | Hard |
| 1094 | Car Pooling | 第 7 章核心題 5 | Medium |
| 1143 | Longest Common Subsequence | 第 22 章核心題 3 | Medium |
| 1146 | Snapshot Array | 第 27 章難題 5 | Medium |
| 1171 | Remove Zero Sum Consecutive Nodes from Linked List | 第 11 章難題 5 | Medium |
| 1192 | Critical Connections in a Network | 第 18 章難題 5 | Hard |
| 1203 | Sort Items by Groups Respecting Dependencies | 第 16 章難題 3 | Hard |
| 1224 | Maximum Equal Frequency | 第 4 章難題 5 | Hard |
| 1235 | Maximum Profit in Job Scheduling | 第 21 章難題 4 | Hard |
| 1240 | Tiling a Rectangle with the Fewest Squares | 第 19 章難題 5 | Hard |
| 1293 | Shortest Path in a Grid with Obstacles Elimination | 第 15 章難題 3 | Hard |
| 1312 | Minimum Insertion Steps to Make a String Palindrome | 第 23 章核心題 5 | Hard |
| 1319 | Number of Operations to Make Network Connected | 第 17 章核心題 5 | Medium |
| 1326 | Minimum Number of Taps to Open to Water a Garden | 第 20 章難題 5 | Hard |
| 1335 | Minimum Difficulty of a Job Schedule | 第 21 章難題 5 | Hard |
| 1349 | Maximum Students Taking Exam | 第 24 章難題 3 | Hard |
| 1368 | Minimum Cost to Make at Least One Valid Path in a Grid | 第 18 章難題 2 | Hard |
| 1371 | Find the Longest Substring Containing Vowels in Even Counts | 第 7 章難題 4 | Medium |
| 1392 | Longest Happy Prefix | 第 25 章難題 3 | Hard |
| 1395 | Count Number of Teams | 第 26 章核心題 5 | Medium |
| 1462 | Course Schedule IV | 第 16 章核心題 5 | Medium |
| 1472 | Design Browser History | 第 27 章核心題 4 | Medium |
| 1514 | Path with Maximum Probability | 第 18 章核心題 4 | Medium |
| 1547 | Minimum Cost to Cut a Stick | 第 23 章難題 5 | Hard |
| 1579 | Remove Max Number of Edges to Keep Graph Fully Traversable | 第 17 章難題 4 | Hard |
| 1584 | Min Cost to Connect All Points | 第 18 章核心題 5 | Medium |
| 1611 | Minimum One Bit Operations to Make Integers Zero | 第 28 章難題 5 | Hard |
| 1631 | Path With Minimum Effort | 第 18 章核心題 3 | Medium |
| 1697 | Checking Existence of Edge Length Limited Paths | 第 17 章難題 5 | Hard |
| 1707 | Maximum XOR With an Element From Array | 第 13 章難題 3 | Hard |
| 1793 | Maximum Score of a Good Subarray | 第 5 章難題 4 | Hard |
| 1851 | Minimum Interval to Include Each Query | 第 9 章難題 5 | Hard |
| 1857 | Largest Color Value in a Directed Graph | 第 16 章難題 4 | Hard |
| 1923 | Longest Common Subpath | 第 25 章難題 4 | Hard |
| 1928 | Minimum Cost to Reach Destination in Time | 第 18 章難題 3 | Hard |
| 1986 | Minimum Number of Work Sessions to Finish the Tasks | 第 24 章核心題 4 | Medium |
| 2009 | Minimum Number of Operations to Make Array Continuous | 第 5 章難題 5 | Hard |
| 2040 | Kth Smallest Product of Two Sorted Arrays | 第 8 章難題 5 | Hard |
| 2045 | Second Minimum Time to Reach Destination | 第 18 章難題 4 | Hard |
| 2050 | Parallel Courses III | 第 16 章難題 5 | Hard |
| 2223 | Sum of Scores of Built Strings | 第 25 章難題 5 | Hard |
| 2281 | Sum of Total Strength of Wizards | 第 7 章難題 5 | Hard |
| 2302 | Count Subarrays With Score Less Than K | 第 6 章難題 5 | Hard |
| 2376 | Count Special Integers | 第 24 章難題 5 | Hard |
| 2407 | Longest Increasing Subsequence II | 第 26 章難題 5 | Hard |
| 2458 | Height of Binary Tree After Subtree Removal Queries | 第 12 章難題 5 | Hard |
