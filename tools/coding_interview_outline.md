# 《Coding Interview Pattern Playbook》章節大綱

每一列：章｜檔名｜標題｜類型｜題數｜內容。類型 `guide` 是一般章節（無題目，需要 8 組延伸問答）；`pattern` 是題型章（5 道核心題 ＋ 5 道難題）。題號為 LeetCode 題號，題目一律用自己的話重述。

題目選擇依據：Blind 75、NeetCode 150、Grind 169、LeetCode Top Interview 150 等公開高頻清單，以及 Google、Meta、Amazon、Microsoft、Apple 公開面經中反覆出現的題型。核心題代表「這個 pattern 一定要會的標準形」，難題代表「這個 domain 的上限與主要變形」。

## Part 0　面試作業系統（`Part 0 - 面試作業系統/`）

| 章 | 檔名 | 標題 | 類型 | 題數 | 內容 |
|---|---|---|---|---|---|
| 1 | 01 - 如何使用本書.md | 如何使用本書：21 天看完所有 Pattern | guide | 0 | 本書結構、核心題與難題的讀法差異、21 天節奏（細節在附錄 D）、怎麼練（先自己寫、計時、再看解答）、怎麼複習（錯題本、間隔重複）、大廠題型傾向總覽（Google、Meta、Amazon、Microsoft、Apple 各自偏好與節奏）、調查方法與限制 |
| 2 | 02 - 面試流程與溝通.md | 面試流程與溝通：從題目到通過 | guide | 0 | 45 分鐘的時間分配；釐清題目（輸入範圍、重複、空輸入、回傳格式）；先講暴力解再優化；邊寫邊說；手動追蹤測試；複雜度分析；卡住時怎麼辦；面試官的評分維度（problem solving、coding、verification、communication）；常見扣分行為；follow-up 的應對 |
| 3 | 03 - 從限制推 Pattern.md | 從限制推 Pattern：複雜度、Constraints 與決策樹 | guide | 0 | n 的大小對應可接受的複雜度（n ≤ 20 → 指數；≤ 500 → n³；≤ 10⁴ → n²；≤ 10⁶ → n log n；更大 → n 或 log n）；Big-O 分析方法與 amortized；題目訊號 → pattern 的決策樹（排序陣列、連續子陣列、「最多／最少」、所有組合、依賴關係、區間…）；26 個 pattern 的一頁總覽表；Python 面試必備語法與資料結構（詳細版在附錄 A） |

## Part 1　陣列、字串與線性結構（`Part 1 - 線性結構/`）

| 章 | 檔名 | 標題 | 類型 | 題數 | 內容 |
|---|---|---|---|---|---|
| 4 | 04 - Hashing and Counting.md | Hashing 與計數 | pattern | 10 | 核心：1 Two Sum、49 Group Anagrams、128 Longest Consecutive Sequence、454 4Sum II、554 Brick Wall。難題：41 First Missing Positive、30 Substring with Concatenation of All Words、149 Max Points on a Line、336 Palindrome Pairs、1224 Maximum Equal Frequency |
| 5 | 05 - Two Pointers.md | Two Pointers | pattern | 10 | 核心：167 Two Sum II、15 3Sum、11 Container With Most Water、75 Sort Colors、977 Squares of a Sorted Array。難題：42 Trapping Rain Water、287 Find the Duplicate Number、923 3Sum With Multiplicity、1793 Maximum Score of a Good Subarray、2009 Minimum Operations to Make Array Continuous |
| 6 | 06 - Sliding Window.md | Sliding Window | pattern | 10 | 核心：3 Longest Substring Without Repeating Characters、209 Minimum Size Subarray Sum、424 Longest Repeating Character Replacement、567 Permutation in String、438 Find All Anagrams in a String。難題：76 Minimum Window Substring、239 Sliding Window Maximum、992 Subarrays with K Different Integers、995 Minimum Number of K Consecutive Bit Flips、2302 Count Subarrays With Score Less Than K |
| 7 | 07 - Prefix Sum and Difference Array.md | Prefix Sum 與 Difference Array | pattern | 10 | 核心：238 Product of Array Except Self、560 Subarray Sum Equals K、525 Contiguous Array、304 Range Sum Query 2D、1094 Car Pooling。難題：1074 Number of Submatrices That Sum to Target、363 Max Sum of Rectangle No Larger Than K、862 Shortest Subarray with Sum at Least K、1371 Longest Substring Containing Vowels in Even Counts、2281 Sum of Total Strength of Wizards |
| 8 | 08 - Binary Search.md | Binary Search | pattern | 10 | 核心：34 Find First and Last Position、33 Search in Rotated Sorted Array、153 Find Minimum in Rotated Sorted Array、875 Koko Eating Bananas、1011 Capacity To Ship Packages。難題：4 Median of Two Sorted Arrays、410 Split Array Largest Sum、668 Kth Smallest Number in Multiplication Table、719 Find K-th Smallest Pair Distance、2040 Kth Smallest Product of Two Sorted Arrays |
| 9 | 09 - Intervals and Sweep Line.md | Intervals 與 Sweep Line | pattern | 10 | 核心：56 Merge Intervals、57 Insert Interval、435 Non-overlapping Intervals、986 Interval List Intersections、253 Meeting Rooms II。難題：218 The Skyline Problem、759 Employee Free Time、850 Rectangle Area II、352 Data Stream as Disjoint Intervals、1851 Minimum Interval to Include Each Query |
| 10 | 10 - Stack and Monotonic Stack.md | Stack 與 Monotonic Stack | pattern | 10 | 核心：20 Valid Parentheses、155 Min Stack、150 Evaluate Reverse Polish Notation、739 Daily Temperatures、503 Next Greater Element II。難題：84 Largest Rectangle in Histogram、85 Maximal Rectangle、32 Longest Valid Parentheses、224 Basic Calculator、907 Sum of Subarray Minimums |
| 11 | 11 - Linked List.md | Linked List | pattern | 10 | 核心：206 Reverse Linked List、21 Merge Two Sorted Lists、141／142 Linked List Cycle、19 Remove Nth Node From End、143 Reorder List。難題：25 Reverse Nodes in k-Group、23 Merge k Sorted Lists、138 Copy List with Random Pointer、148 Sort List、1171 Remove Zero Sum Consecutive Nodes |

## Part 2　樹與堆積（`Part 2 - 樹與堆積/`）

| 章 | 檔名 | 標題 | 類型 | 題數 | 內容 |
|---|---|---|---|---|---|
| 12 | 12 - Binary Tree.md | Binary Tree：DFS 與 BFS | pattern | 10 | 核心：102 Level Order Traversal、199 Right Side View、543 Diameter of Binary Tree、105 Construct from Preorder and Inorder、236 Lowest Common Ancestor。難題：124 Maximum Path Sum、297 Serialize and Deserialize、968 Binary Tree Cameras、987 Vertical Order Traversal、2458 Height of Tree After Subtree Removal Queries |
| 13 | 13 - BST and Trie.md | BST 與 Trie | pattern | 10 | 核心：98 Validate BST、230 Kth Smallest in BST、450 Delete Node in BST、208 Implement Trie、211 Add and Search Word。難題：212 Word Search II、745 Prefix and Suffix Search、1707 Maximum XOR With an Element From Array、472 Concatenated Words、99 Recover BST |
| 14 | 14 - Heap Top-K and K-way Merge.md | Heap：Top-K 與 K-way Merge | pattern | 10 | 核心：215 Kth Largest Element、347 Top K Frequent Elements、973 K Closest Points、621 Task Scheduler、767 Reorganize String。難題：295 Find Median from Data Stream、480 Sliding Window Median、502 IPO、632 Smallest Range Covering Elements from K Lists、857 Minimum Cost to Hire K Workers |

## Part 3　圖（`Part 3 - 圖/`）

| 章 | 檔名 | 標題 | 類型 | 題數 | 內容 |
|---|---|---|---|---|---|
| 15 | 15 - Graph BFS and DFS.md | Graph：BFS 與 DFS | pattern | 10 | 核心：200 Number of Islands、133 Clone Graph、994 Rotting Oranges、417 Pacific Atlantic Water Flow、130 Surrounded Regions。難題：127 Word Ladder、126 Word Ladder II、1293 Shortest Path in a Grid with Obstacles Elimination、847 Shortest Path Visiting All Nodes、864 Shortest Path to Get All Keys |
| 16 | 16 - Topological Sort.md | Topological Sort | pattern | 10 | 核心：207 Course Schedule、210 Course Schedule II、802 Find Eventual Safe States、310 Minimum Height Trees、1462 Course Schedule IV。難題：269 Alien Dictionary、329 Longest Increasing Path in a Matrix、1203 Sort Items by Groups Respecting Dependencies、1857 Largest Color Value in a Directed Graph、2050 Parallel Courses III |
| 17 | 17 - Union-Find.md | Union-Find | pattern | 10 | 核心：547 Number of Provinces、684 Redundant Connection、721 Accounts Merge、990 Satisfiability of Equality Equations、1319 Number of Operations to Make Network Connected。難題：685 Redundant Connection II、778 Swim in Rising Water、803 Bricks Falling When Hit、1579 Remove Max Number of Edges to Keep Graph Fully Traversable、1697 Checking Existence of Edge Length Limited Paths |
| 18 | 18 - Shortest Path and MST.md | Shortest Path 與 Minimum Spanning Tree | pattern | 10 | 核心：743 Network Delay Time、787 Cheapest Flights Within K Stops、1631 Path With Minimum Effort、1514 Path with Maximum Probability、1584 Min Cost to Connect All Points。難題：882 Reachable Nodes In Subdivided Graph、1368 Minimum Cost to Make at Least One Valid Path、1928 Minimum Cost to Reach Destination in Time、2045 Second Minimum Time to Reach Destination、1192 Critical Connections in a Network |

## Part 4　搜尋與貪婪（`Part 4 - 搜尋與貪婪/`）

| 章 | 檔名 | 標題 | 類型 | 題數 | 內容 |
|---|---|---|---|---|---|
| 19 | 19 - Backtracking.md | Backtracking | pattern | 10 | 核心：78 Subsets、46 Permutations、39 Combination Sum、17 Letter Combinations of a Phone Number、79 Word Search。難題：51 N-Queens、37 Sudoku Solver、282 Expression Add Operators、698 Partition to K Equal Sum Subsets、1240 Tiling a Rectangle with the Fewest Squares |
| 20 | 20 - Greedy.md | Greedy | pattern | 10 | 核心：55 Jump Game、45 Jump Game II、134 Gas Station、763 Partition Labels、846 Hand of Straights。難題：135 Candy、330 Patching Array、630 Course Schedule III、871 Minimum Number of Refueling Stops、1326 Minimum Number of Taps to Open to Water a Garden |

## Part 5　Dynamic Programming（`Part 5 - Dynamic Programming/`）

| 章 | 檔名 | 標題 | 類型 | 題數 | 內容 |
|---|---|---|---|---|---|
| 21 | 21 - DP 1D and State Machine.md | DP：一維與狀態機 | pattern | 10 | 核心：198 House Robber、322 Coin Change、300 Longest Increasing Subsequence、139 Word Break、91 Decode Ways。難題：188 Best Time to Buy and Sell Stock IV、354 Russian Doll Envelopes、403 Frog Jump、1235 Maximum Profit in Job Scheduling、1335 Minimum Difficulty of a Job Schedule |
| 22 | 22 - DP 2D and Sequence.md | DP：二維與序列比對 | pattern | 10 | 核心：62 Unique Paths、64 Minimum Path Sum、1143 Longest Common Subsequence、72 Edit Distance、97 Interleaving String。難題：10 Regular Expression Matching、44 Wildcard Matching、115 Distinct Subsequences、174 Dungeon Game、1092 Shortest Common Supersequence |
| 23 | 23 - Knapsack and Interval DP.md | DP：背包與區間 | pattern | 10 | 核心：416 Partition Equal Subset Sum、494 Target Sum、518 Coin Change II、516 Longest Palindromic Subsequence、1312 Minimum Insertion Steps to Make a String Palindrome。難題：312 Burst Balloons、664 Strange Printer、546 Remove Boxes、1000 Minimum Cost to Merge Stones、1547 Minimum Cost to Cut a Stick |
| 24 | 24 - Tree Bitmask and Digit DP.md | DP：樹、Bitmask 與數位 | pattern | 10 | 核心：337 House Robber III、338 Counting Bits、526 Beautiful Arrangement、1986 Minimum Number of Work Sessions、902 Numbers At Most N Given Digit Set。難題：834 Sum of Distances in Tree、943 Find the Shortest Superstring、1349 Maximum Students Taking Exam、233 Number of Digit One、2376 Count Special Integers |

## Part 6　進階主題（`Part 6 - 進階主題/`）

| 章 | 檔名 | 標題 | 類型 | 題數 | 內容 |
|---|---|---|---|---|---|
| 25 | 25 - String Algorithms.md | 字串演算法：KMP、Rolling Hash 與回文 | pattern | 10 | 核心：5 Longest Palindromic Substring、647 Palindromic Substrings、28 Find the Index of the First Occurrence（KMP）、459 Repeated Substring Pattern、686 Repeated String Match。難題：214 Shortest Palindrome、1044 Longest Duplicate Substring、1392 Longest Happy Prefix、1923 Longest Common Subpath、2223 Sum of Scores of Built Strings |
| 26 | 26 - Range Query.md | Range Query：Fenwick Tree 與 Segment Tree | pattern | 10 | 核心：307 Range Sum Query Mutable、315 Count of Smaller Numbers After Self、729 My Calendar I、731 My Calendar II、1395 Count Number of Teams。難題：327 Count of Range Sum、493 Reverse Pairs、699 Falling Squares、715 Range Module、2407 Longest Increasing Subsequence II |
| 27 | 27 - Data Structure Design.md | 資料結構設計 | pattern | 10 | 核心：146 LRU Cache、380 Insert Delete GetRandom O(1)、981 Time Based Key-Value Store、1472 Design Browser History、341 Flatten Nested List Iterator。難題：460 LFU Cache、432 All O(1) Data Structure、716 Max Stack、895 Maximum Frequency Stack、1146 Snapshot Array |
| 28 | 28 - Bit Manipulation and Math.md | Bit Manipulation 與數學 | pattern | 10 | 核心：136 Single Number、268 Missing Number、191 Number of 1 Bits、50 Pow(x, n)、204 Count Primes。難題：137 Single Number II、201 Bitwise AND of Numbers Range、60 Permutation Sequence、829 Consecutive Numbers Sum、1611 Minimum One Bit Operations to Make Integers Zero |
| 29 | 29 - Matrix Simulation and Parsing.md | Matrix、模擬與解析 | pattern | 10 | 核心：54 Spiral Matrix、48 Rotate Image、73 Set Matrix Zeroes、36 Valid Sudoku、289 Game of Life。難題：65 Valid Number、68 Text Justification、591 Tag Validator、726 Number of Atoms、770 Basic Calculator IV |

## Part 7　衝刺（`Part 7 - 衝刺/`）

| 章 | 檔名 | 標題 | 類型 | 題數 | 內容 |
|---|---|---|---|---|---|
| 30 | 30 - 大廠題型與最後衝刺.md | 大廠題型與最後衝刺 | guide | 0 | Google、Meta、Amazon、Microsoft、Apple 的面試形式與題型傾向（只寫公開資訊與普遍經驗，不捏造統計）；各公司最常出現的 pattern 與本書對應題；考前一週複習法；面試當天檢查清單；遇到沒看過的題目怎麼拆解（以三題沒在本書出現的題型示範拆解過程，不給完整程式） |
| 31 | 31 - 模擬面試.md | 六場模擬面試 | guide | 0 | 六場模擬面試，每場 2 題（從本書題目中挑選不同 pattern 組合，或指定新的變形），附計時建議、面試官可能的追問、評分重點、自我檢討表；最後是一份「pattern 全回顧」：26 個 pattern 各一句話的辨識訊號與模板 |

## 附錄（`Appendices/`）

| 檔名 | 內容 |
|---|---|
| A - Python 面試工具箱.md | 面試常用的 Python：list／dict／set／deque／heapq／bisect／Counter／defaultdict／sorted 與 key／itertools／functools.cache／字串操作／遞迴深度／常見陷阱（可變預設值、淺複製、整數除法），每項附範例與複雜度 |
| B - 複雜度與 Constraints 速查.md | 各資料結構操作複雜度表、常見演算法複雜度、constraints 對應可接受複雜度表、遞迴樹與 Master theorem 速算 |
| C - 全題索引.md | 全書 260 題索引：依 pattern、依難度、依公司常見程度（只標「常見」程度，不捏造頻率）、依 LeetCode 題號；每題一句話的關鍵技巧 |
| D - 21 天讀書計畫.md | 21 天（每天約 2–3 小時）與 14 天快速版：每天讀哪幾章、哪些題必須自己寫、複習哪些錯題；以及 7 天考前衝刺版 |
