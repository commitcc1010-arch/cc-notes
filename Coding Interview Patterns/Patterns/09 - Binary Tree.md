---
title: Binary Tree
tags:
  - coding-interview/pattern
  - binary-tree
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 09 — Binary Tree

[[08 - Linked List|← 上一章]] · [[00 - Book Index|目錄]] · [[10 - BST and Trie|下一章 →]]

> [!abstract] Mental model
> Tree recursion 的核心問題是：「子樹應該回傳什麼資訊，讓父節點能在 $O(1)$ 合併？」先定義 return contract，再寫 base case 與 combine。

## 基本節點

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

---

## 核心題 1：Balanced Binary Tree

### 題目

每個節點左右子樹高度差不超過一即為 balanced。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每個節點左右子樹高度差不超過一即為 balanced。
>
> **核心轉換：** postorder 一次同時算高度與合法性；用 -1 作為不平衡 sentinel，child 一旦回傳 -1 就立即向上傳播。
>
> **主要知識點：** Binary Tree Traversal 與子樹資訊合併。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Balanced Binary Tree
      │
      ├─ 暴力路線：對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：postorder 一次同時算高度與合法性；用 -1 作為不平衡 sentinel，child 一旦回傳 -1 就立即向上傳播。
      │
Pattern toolbox：DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要
      │
      ├─ 狀態轉移：選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果
      │
      ├─ 永遠成立：函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每個節點左右子樹高度差不超過一即為 balanced。
2. **寫出暴力：** 對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** postorder 一次同時算高度與合法性；用 -1 作為不平衡 sentinel，child 一旦回傳 -1 就立即向上傳播。
4. **定義 state 與轉移：** 使用「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」承載上述觀察，再執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」代表什麼，再說每一步如何「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解」的 base case。
>
> 2. **維持：** 每次執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」後，狀態仍與已處理資料一致。關鍵論證是：以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def is_balanced(root):
    def height(node):
        if not node:
            return 0
        left = height(node.left)
        if left == -1:
            return -1
        right = height(node.right)
        if right == -1 or abs(left - right) > 1:
            return -1
        return 1 + max(left, right)

    return height(root) != -1
```

**Contract：**回傳子樹高度；若已不平衡則回傳 sentinel `-1`。

### Follow-up 1：原題直接變形
**問：為什麼不對每個節點另外呼叫 `height`？**

**答：**那會重算子樹而退化成 $O(n^2)$。Postorder 一次同時取得高度與平衡狀態，只需 $O(n)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Balanced Binary Tree》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：postorder 一次同時算高度與合法性；用 -1 作為不平衡 sentinel，child 一旦回傳 -1 就立即向上傳播。 失效情境包括：若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。
>
> 替代路線是：可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。
>
> 套回《Balanced Binary Tree》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。
>
> 此外必須把《Balanced Binary Tree》目前隱含的前提寫成 contract：每個節點左右子樹高度差不超過一即為 balanced。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Lowest Common Ancestor


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在 binary tree 中找兩個指定節點的 lowest common ancestor。
>
> **核心轉換：** postorder 回傳 subtree 是否找到 p 或 q；若左右各找到一個，或目前節點本身是其中之一且另一個在 child，當前節點就是 LCA。
>
> **主要知識點：** Binary Tree Traversal 與子樹資訊合併。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Lowest Common Ancestor
      │
      ├─ 暴力路線：對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：postorder 回傳 subtree 是否找到 p 或 q；若左右各找到一個，或目前節點本身是其中之一且另一個在 child，當前節點就是 LCA。
      │
Pattern toolbox：DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要
      │
      ├─ 狀態轉移：選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果
      │
      ├─ 永遠成立：函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在 binary tree 中找兩個指定節點的 lowest common ancestor。
2. **寫出暴力：** 對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** postorder 回傳 subtree 是否找到 p 或 q；若左右各找到一個，或目前節點本身是其中之一且另一個在 child，當前節點就是 LCA。
4. **定義 state 與轉移：** 使用「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」承載上述觀察，再執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」代表什麼，再說每一步如何「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解」的 base case。
>
> 2. **維持：** 每次執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」後，狀態仍與已處理資料一致。關鍵論證是：以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def lowest_common_ancestor(root, p, q):
    if not root or root is p or root is q:
        return root
    left = lowest_common_ancestor(root.left, p, q)
    right = lowest_common_ancestor(root.right, p, q)
    if left and right:
        return root
    return left or right
```

### Follow-up 1：原題直接變形
**問：不保證 p、q 都存在？**

**答：**helper 回傳 `(candidate, found_count)`。只有根節點收到 `found_count == 2` 時，candidate 才是有效答案。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Lowest Common Ancestor》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：postorder 回傳 subtree 是否找到 p 或 q；若左右各找到一個，或目前節點本身是其中之一且另一個在 child，當前節點就是 LCA。 失效情境包括：若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。
>
> 替代路線是：可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。
>
> 套回《Lowest Common Ancestor》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。
>
> 此外必須把《Lowest Common Ancestor》目前隱含的前提寫成 contract：在 binary tree 中找兩個指定節點的 lowest common ancestor。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Binary Tree Level Order Traversal


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 依深度由上到下、每層由左到右輸出 binary tree。
>
> **核心轉換：** BFS 每輪先記錄 queue 長度，這個固定長度就是本層節點數；處理時加入 children，但不讓它們混入本層輸出。
>
> **主要知識點：** Binary Tree Traversal 與子樹資訊合併。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Binary Tree Level Order Traversal
      │
      ├─ 暴力路線：對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：BFS 每輪先記錄 queue 長度，這個固定長度就是本層節點數；處理時加入 children，但不讓它們混入本層輸出。
      │
Pattern toolbox：DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要
      │
      ├─ 狀態轉移：選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果
      │
      ├─ 永遠成立：函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 依深度由上到下、每層由左到右輸出 binary tree。
2. **寫出暴力：** 對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** BFS 每輪先記錄 queue 長度，這個固定長度就是本層節點數；處理時加入 children，但不讓它們混入本層輸出。
4. **定義 state 與轉移：** 使用「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」承載上述觀察，再執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」代表什麼，再說每一步如何「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解」的 base case。
>
> 2. **維持：** 每次執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」後，狀態仍與已處理資料一致。關鍵論證是：以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from collections import deque

def level_order(root):
    if not root:
        return []
    q = deque([root])
    answer = []
    while q:
        level = []
        for _ in range(len(q)):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        answer.append(level)
    return answer
```

### Follow-up 1：原題直接變形
**問：zigzag level order？**

**答：**BFS 不變；偶數層反轉輸出，或用 deque 在不同方向 append。為避免每層反轉成本，可預配置 level array 依方向填 index。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Binary Tree Level Order Traversal》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：BFS 每輪先記錄 queue 長度，這個固定長度就是本層節點數；處理時加入 children，但不讓它們混入本層輸出。 失效情境包括：若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。
>
> 替代路線是：可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。
>
> 套回《Binary Tree Level Order Traversal》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。
>
> 此外必須把《Binary Tree Level Order Traversal》目前隱含的前提寫成 contract：依深度由上到下、每層由左到右輸出 binary tree。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Serialize and Deserialize Binary Tree

### 題目

把任意 binary tree 編碼成字串，之後可完整還原。

> [!tip]- 三層提示
> 1. 只保存 preorder 值不足以區分形狀。
> 2. 為 null child 保存 sentinel。
> 3. Preorder token stream 可用遞迴依序消費。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 把任意 binary tree 編碼成字串，之後可完整還原。
>
> **核心轉換：** Preorder 依序輸出 node, left, right，null 輸出 。反序列化時每讀一個 token 就能判斷建立節點或回傳 null。
>
> **主要知識點：** Binary Tree Traversal 與子樹資訊合併。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Serialize and Deserialize Binary Tree
      │
      ├─ 暴力路線：對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Preorder 依序輸出 node, left, right，null 輸出 。反序列化時每讀一個 token 就能判斷建立節點或回傳 null。
      │
Pattern toolbox：DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要
      │
      ├─ 狀態轉移：選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果
      │
      ├─ 永遠成立：函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 把任意 binary tree 編碼成字串，之後可完整還原。
2. **寫出暴力：** 對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Preorder 依序輸出 node, left, right，null 輸出 。反序列化時每讀一個 token 就能判斷建立節點或回傳 null。
4. **定義 state 與轉移：** 使用「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」承載上述觀察，再執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$ serialized data 與 recursion

> [!tip] 一句話記憶
> 先說清楚「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」代表什麼，再說每一步如何「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解」的 base case。
>
> 2. **維持：** 每次執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」後，狀態仍與已處理資料一致。關鍵論證是：以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Preorder 依序輸出 `node, left, right`，null 輸出 `#`。反序列化時每讀一個 token 就能判斷建立節點或回傳 null。

```python
class Codec:
    def serialize(self, root):
        tokens = []

        def dfs(node):
            if not node:
                tokens.append("#")
                return
            tokens.append(str(node.val))
            dfs(node.left)
            dfs(node.right)

        dfs(root)
        return ",".join(tokens)

    def deserialize(self, data):
        tokens = iter(data.split(","))

        def dfs():
            token = next(tokens)
            if token == "#":
                return None
            node = TreeNode(int(token))
            node.left = dfs()
            node.right = dfs()
            return node

        return dfs()
```

- 時間：$O(n)$
- 空間：$O(n)$ serialized data 與 recursion

### Follow-up 1：原題直接變形
**問：如何處理非常深的 skewed tree？**

**答：**改用 iterative BFS serialization，queue 中包含 null；deserialize 逐節點填左右 child，避免 recursion-depth 限制。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Serialize and Deserialize Binary Tree》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Preorder 依序輸出 node, left, right，null 輸出 。反序列化時每讀一個 token 就能判斷建立節點或回傳 null。 失效情境包括：若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。
>
> 替代路線是：可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。
>
> 套回《Serialize and Deserialize Binary Tree》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。
>
> 此外必須把《Serialize and Deserialize Binary Tree》目前隱含的前提寫成 contract：把任意 binary tree 編碼成字串，之後可完整還原。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Binary Tree Maximum Path Sum

### 題目

Path 可從任意節點到任意節點，但不能重複節點。求最大節點值總和。

> [!tip]- 三層提示
> 1. 父節點最多只能延伸某一側 path。
> 2. 但以目前節點作最高點的完整答案可以同時使用左右兩側。
> 3. 負貢獻應截成零。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** Path 可從任意節點到任意節點，但不能重複節點。求最大節點值總和。
>
> **核心轉換：** DFS 回傳「從目前節點向下可提供給父節點的最大單支 gain」。全域答案則用 node + leftgain + rightgain 更新。
>
> **主要知識點：** Binary Tree Traversal 與子樹資訊合併。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Binary Tree Maximum Path Sum
      │
      ├─ 暴力路線：對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：DFS 回傳「從目前節點向下可提供給父節點的最大單支 gain」。全域答案則用 node + leftgain + rightgain 更新。
      │
Pattern toolbox：DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要
      │
      ├─ 狀態轉移：選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果
      │
      ├─ 永遠成立：函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** Path 可從任意節點到任意節點，但不能重複節點。求最大節點值總和。
2. **寫出暴力：** 對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** DFS 回傳「從目前節點向下可提供給父節點的最大單支 gain」。全域答案則用 node + leftgain + rightgain 更新。
4. **定義 state 與轉移：** 使用「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」承載上述觀察，再執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(height)$

> [!tip] 一句話記憶
> 先說清楚「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」代表什麼，再說每一步如何「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解」的 base case。
>
> 2. **維持：** 每次執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」後，狀態仍與已處理資料一致。關鍵論證是：以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

DFS 回傳「從目前節點向下可提供給父節點的最大單支 gain」。全域答案則用 `node + left_gain + right_gain` 更新。

```python
def max_path_sum(root):
    answer = float("-inf")

    def gain(node):
        nonlocal answer
        if not node:
            return 0
        left = max(0, gain(node.left))
        right = max(0, gain(node.right))
        answer = max(answer, node.val + left + right)
        return node.val + max(left, right)

    gain(root)
    return answer
```

- 時間：$O(n)$
- 空間：$O(height)$

### Follow-up 1：原題直接變形
**問：如何回傳實際 path？**

**答：**helper 除 gain 外保存最佳 downward path；更新全域答案時串接 reversed left path、node 與 right path。為避免大量複製，可保存 parent choice，最後重建。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Binary Tree Maximum Path Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：DFS 回傳「從目前節點向下可提供給父節點的最大單支 gain」。全域答案則用 node + leftgain + rightgain 更新。 失效情境包括：若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。
>
> 替代路線是：可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。
>
> 套回《Binary Tree Maximum Path Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。
>
> 此外必須把《Binary Tree Maximum Path Sum》目前隱含的前提寫成 contract：Path 可從任意節點到任意節點，但不能重複節點。求最大節點值總和。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Binary Tree Cameras

### 題目

Camera 可監控自己、parent 與直接 children。求監控所有節點的最少 cameras。

> [!tip]- 三層提示
> 1. Bottom-up 決定。
> 2. 子節點若未被覆蓋，父節點必須裝 camera。
> 3. 定義三種狀態：needs camera、has camera、covered。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** Camera 可監控自己、parent 與直接 children。求監控所有節點的最少 cameras。
>
> **核心轉換：** Postorder：
>
> **主要知識點：** Binary Tree Traversal 與子樹資訊合併。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Binary Tree Cameras
      │
      ├─ 暴力路線：對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Postorder：
      │
Pattern toolbox：DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要
      │
      ├─ 狀態轉移：選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果
      │
      ├─ 永遠成立：函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** Camera 可監控自己、parent 與直接 children。求監控所有節點的最少 cameras。
2. **寫出暴力：** 對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Postorder：
4. **定義 state 與轉移：** 使用「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」承載上述觀察，再執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」代表什麼，再說每一步如何「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解」的 base case。
>
> 2. **維持：** 每次執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」後，狀態仍與已處理資料一致。關鍵論證是：以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Postorder：

- 任一 child `NEEDS` → 目前裝 camera。
- 任一 child `CAMERA` → 目前已 covered。
- 兩 child 都 covered → 目前把需求交給 parent。

```python
def min_camera_cover(root):
    NEEDS, CAMERA, COVERED = 0, 1, 2
    cameras = 0

    def dfs(node):
        nonlocal cameras
        if not node:
            return COVERED
        left = dfs(node.left)
        right = dfs(node.right)
        if left == NEEDS or right == NEEDS:
            cameras += 1
            return CAMERA
        if left == CAMERA or right == CAMERA:
            return COVERED
        return NEEDS

    if dfs(root) == NEEDS:
        cameras += 1
    return cameras
```

**正確性：**leaf 不應自己裝 camera；把 camera 放在其 parent 能同時覆蓋更多節點。狀態轉移正是這個 bottom-up greedy。

### Follow-up 1：原題直接變形
**問：camera 有不同成本？**

**答：**局部 greedy 不再成立。對每節點做 tree DP，計算不同覆蓋／安裝狀態的最小成本，再由 children 狀態組合。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Binary Tree Cameras》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Postorder： 失效情境包括：若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。
>
> 替代路線是：可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。
>
> 套回《Binary Tree Cameras》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。
>
> 此外必須把《Binary Tree Cameras》目前隱含的前提寫成 contract：Camera 可監控自己、parent 與直接 children。求監控所有節點的最少 cameras。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Vertical Order Traversal

### 題目

Root 座標 `(row=0,col=0)`；左 child `(r+1,c-1)`、右 child `(r+1,c+1)`。依 column、row、value 排序輸出。

> [!tip]- 三層提示
> 1. DFS/BFS 收集座標。
> 2. 題目已完整定義排序 key。
> 3. 排序 `(col,row,value)` 後按 col 分組。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** Root 座標 (row=0,col=0)；左 child (r+1,c-1)、右 child (r+1,c+1)。依 column、row、value 排序輸出。
>
> **核心轉換：** 這題的陷阱通常不是 traversal，而是同 row、同 col 時必須依 value 排序。
>
> **主要知識點：** Binary Tree Traversal 與子樹資訊合併。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Vertical Order Traversal
      │
      ├─ 暴力路線：對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：這題的陷阱通常不是 traversal，而是同 row、同 col 時必須依 value 排序。
      │
Pattern toolbox：DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要
      │
      ├─ 狀態轉移：選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果
      │
      ├─ 永遠成立：函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** Root 座標 (row=0,col=0)；左 child (r+1,c-1)、右 child (r+1,c+1)。依 column、row、value 排序輸出。
2. **寫出暴力：** 對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 這題的陷阱通常不是 traversal，而是同 row、同 col 時必須依 value 排序。
4. **定義 state 與轉移：** 使用「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」承載上述觀察，再執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」代表什麼，再說每一步如何「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解」的 base case。
>
> 2. **維持：** 每次執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」後，狀態仍與已處理資料一致。關鍵論證是：以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

這題的陷阱通常不是 traversal，而是同 row、同 col 時必須依 value 排序。

```python
from collections import defaultdict

def vertical_traversal(root):
    nodes = []

    def dfs(node, row, col):
        if not node:
            return
        nodes.append((col, row, node.val))
        dfs(node.left, row + 1, col - 1)
        dfs(node.right, row + 1, col + 1)

    dfs(root, 0, 0)
    nodes.sort()
    groups = defaultdict(list)
    for col, row, value in nodes:
        groups[col].append(value)
    return [groups[col] for col in sorted(groups)]
```

- 時間：$O(n\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：若 tie 要保持 BFS 遇到順序而不是 value？**

**答：**使用 BFS 並為每個節點保存 sequence number，排序 key 改為 `(col,row,sequence)`；不要再用 value。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Vertical Order Traversal》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：這題的陷阱通常不是 traversal，而是同 row、同 col 時必須依 value 排序。 失效情境包括：若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。
>
> 替代路線是：可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。
>
> 套回《Vertical Order Traversal》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。
>
> 此外必須把《Vertical Order Traversal》目前隱含的前提寫成 contract：Root 座標 (row=0,col=0)；左 child (r+1,c-1)、右 child (r+1,c+1)。依 column、row、value 排序輸出。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：All Nodes Distance K in Binary Tree

### 題目

給 target node 與距離 `k`，回傳所有與 target graph distance 恰為 `k` 的節點值。

> [!tip]- 三層提示
> 1. 從 target 出發需要往 child，也需要往 parent。
> 2. 先建立 `child -> parent` map。
> 3. 接著把 tree 當無向圖做 BFS。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給 target node 與距離 k，回傳所有與 target graph distance 恰為 k 的節點值。
>
> **核心轉換：** 第一次 DFS 建 parent map。第二次從 target 做 BFS，鄰居是 left、right、parent，使用 visited 避免來回。
>
> **主要知識點：** Binary Tree Traversal 與子樹資訊合併。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：All Nodes Distance K in Binary Tree
      │
      ├─ 暴力路線：對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：第一次 DFS 建 parent map。第二次從 target 做 BFS，鄰居是 left、right、parent，使用 visited 避免來回。
      │
Pattern toolbox：DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要
      │
      ├─ 狀態轉移：選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果
      │
      ├─ 永遠成立：函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給 target node 與距離 k，回傳所有與 target graph distance 恰為 k 的節點值。
2. **寫出暴力：** 對每個節點重新遍歷其子樹，或枚舉所有 root-to-node 路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 第一次 DFS 建 parent map。第二次從 target 做 BFS，鄰居是 left、right、parent，使用 visited 避免來回。
4. **定義 state 與轉移：** 使用「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」承載上述觀察，再執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「DFS frame／BFS queue；postorder 時每個 child 回傳父節點真正需要的摘要」代表什麼，再說每一步如何「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「函式回傳值完整描述該 subtree 對父節點的貢獻；global answer 保存不能只向上傳的一般解」的 base case。
>
> 2. **維持：** 每次執行「選定 preorder/inorder/postorder/level-order，在恰當時機合併左右子樹結果」後，狀態仍與已處理資料一致。關鍵論證是：以 subtree size induction：假設左右子樹摘要正確，證明 combine formula 得到目前子樹正確摘要。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空樹、leaf、skewed tree、duplicate values、節點不存在、遞迴深度與 global state 未重設。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

第一次 DFS 建 parent map。第二次從 target 做 BFS，鄰居是 left、right、parent，使用 visited 避免來回。

```python
from collections import deque

def distance_k(root, target, k):
    parent = {}

    def build(node, par=None):
        if not node:
            return
        parent[node] = par
        build(node.left, node)
        build(node.right, node)

    build(root)
    q = deque([(target, 0)])
    seen = {target}
    answer = []

    while q:
        node, distance = q.popleft()
        if distance == k:
            answer.append(node.val)
            continue
        for neighbor in (node.left, node.right, parent[node]):
            if neighbor and neighbor not in seen:
                seen.add(neighbor)
                q.append((neighbor, distance + 1))
    return answer
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：同一棵樹有大量 `(target,k)` 查詢？**

**答：**可做 LCA／distance preprocessing、centroid decomposition，或依 constraints 為每個 centroid 保存距離 buckets；單次建立 parent map 再 BFS 不適合大量查詢。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《All Nodes Distance K in Binary Tree》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：第一次 DFS 建 parent map。第二次從 target 做 BFS，鄰居是 left、right、parent，使用 visited 避免來回。 失效情境包括：若樹會頻繁更新，重算整棵樹太慢；若不是 tree 而有 shared child/cycle，必須加 visited 或換模型。
>
> 替代路線是：可做 Euler tour＋segment tree、binary lifting、迭代 traversal，或把 tree 轉 graph 處理距離問題。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent pointer、choice 或 path；序列化題輸出 null marker，最佳路徑題保存在哪個 child 延伸。
>
> 套回《All Nodes Distance K in Binary Tree》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大型樹使用 iterative traversal 避免 stack overflow；共享可變樹需要 snapshot/lock，serialization 要 versioning。
>
> 此外必須把《All Nodes Distance K in Binary Tree》目前隱含的前提寫成 contract：給 target node 與距離 k，回傳所有與 target graph distance 恰為 k 的節點值。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 會先定義 recursion return contract。
- [ ] 能分辨 preorder、inorder、postorder 的用途。
- [ ] 知道何時把 tree 轉成無向 graph。
- [ ] 能設計多狀態 tree DP。
