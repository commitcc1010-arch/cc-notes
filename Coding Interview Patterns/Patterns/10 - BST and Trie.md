---
title: BST and Trie
tags:
  - coding-interview/pattern
  - bst
  - trie
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 10 — BST and Trie

[[09 - Binary Tree|← 上一章]] · [[00 - Book Index|目錄]] · [[11 - Heap Top-K and K-way Merge|下一章 →]]

> [!abstract] Mental model
> BST 利用全域有序範圍剪枝；Trie 利用 prefix 共用搜尋路徑。兩者都不是普通 tree traversal：每個節點都代表「目前仍可能的搜尋空間」。

---

## 核心題 1：Validate Binary Search Tree

### 題目

判斷 binary tree 是否滿足所有左子樹值小於節點、所有右子樹值大於節點。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 判斷 binary tree 是否滿足所有左子樹值小於節點、所有右子樹值大於節點。
>
> **核心轉換：** 每個節點都繼承 ancestor 給的合法開區間 (low, high)；只比較 parent 不夠，因為右子樹深處仍受 root 下界限制。
>
> **主要知識點：** BST Order、Trie Prefix 與逐位決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Validate Binary Search Tree
      │
      ├─ 暴力路線：忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每個節點都繼承 ancestor 給的合法開區間 (low, high)；只比較 parent 不夠，因為右子樹深處仍受 root 下界限制。
      │
Pattern toolbox：BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata
      │
      ├─ 狀態轉移：BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進
      │
      ├─ 永遠成立：BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 判斷 binary tree 是否滿足所有左子樹值小於節點、所有右子樹值大於節點。
2. **寫出暴力：** 忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每個節點都繼承 ancestor 給的合法開區間 (low, high)；只比較 parent 不夠，因為右子樹深處仍受 root 下界限制。
4. **定義 state 與轉移：** 使用「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」承載上述觀察，再執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」代表什麼，再說每一步如何「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix」的 base case。
>
> 2. **維持：** 每次執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」後，狀態仍與已處理資料一致。關鍵論證是：BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def is_valid_bst(root):
    def validate(node, low, high):
        if not node:
            return True
        if not (low < node.val < high):
            return False
        return (
            validate(node.left, low, node.val)
            and validate(node.right, node.val, high)
        )

    return validate(root, float("-inf"), float("inf"))
```

**常見錯誤：**只比較 node 與直接 children，會漏掉祖先範圍限制。

### Follow-up 1：原題直接變形
**問：允許重複值，且規定重複只能放右子樹？**

**答：**邊界需帶 inclusive/exclusive 語意，不能只用數值。左側 upper exclusive，右側 lower inclusive；或使用 tuple boundary。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Validate Binary Search Tree》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每個節點都繼承 ancestor 給的合法開區間 (low, high)；只比較 parent 不夠，因為右子樹深處仍受 root 下界限制。 失效情境包括：BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。
>
> 替代路線是：使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。
>
> 套回《Validate Binary Search Tree》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。
>
> 此外必須把《Validate Binary Search Tree》目前隱含的前提寫成 contract：判斷 binary tree 是否滿足所有左子樹值小於節點、所有右子樹值大於節點。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Kth Smallest in BST

### 題目

找 BST 中第 `k` 小節點值。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 找 BST 中第 k 小節點值。
>
> **核心轉換：** BST inorder 產生遞增序列；走到第 k 個 visited node 即可停止。若有 subtree size metadata，可按左子樹大小做 rank selection。
>
> **主要知識點：** BST Order、Trie Prefix 與逐位決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Kth Smallest in BST
      │
      ├─ 暴力路線：忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串
      │
      ▼  找出本題最關鍵的轉換
核心觀察：BST inorder 產生遞增序列；走到第 k 個 visited node 即可停止。若有 subtree size metadata，可按左子樹大小做 rank selection。
      │
Pattern toolbox：BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata
      │
      ├─ 狀態轉移：BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進
      │
      ├─ 永遠成立：BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 找 BST 中第 k 小節點值。
2. **寫出暴力：** 忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** BST inorder 產生遞增序列；走到第 k 個 visited node 即可停止。若有 subtree size metadata，可按左子樹大小做 rank selection。
4. **定義 state 與轉移：** 使用「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」承載上述觀察，再執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(h+k)$；空間：$O(h)$

> [!tip] 一句話記憶
> 先說清楚「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」代表什麼，再說每一步如何「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix」的 base case。
>
> 2. **維持：** 每次執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」後，狀態仍與已處理資料一致。關鍵論證是：BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def kth_smallest(root, k):
    stack = []
    current = root
    while True:
        while current:
            stack.append(current)
            current = current.left
        current = stack.pop()
        k -= 1
        if k == 0:
            return current.val
        current = current.right
```

- 時間：$O(h+k)$
- 空間：$O(h)$

### Follow-up 1：原題直接變形
**問：樹經常更新，且大量 kth 查詢？**

**答：**每個 node 保存 subtree size。查詢時比較 `k` 與 left size，在 $O(h)$ 決定往左、回傳目前、或往右；插入刪除需沿路更新 size。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Kth Smallest in BST》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：BST inorder 產生遞增序列；走到第 k 個 visited node 即可停止。若有 subtree size metadata，可按左子樹大小做 rank selection。 失效情境包括：BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。
>
> 替代路線是：使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。
>
> 套回《Kth Smallest in BST》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。
>
> 此外必須把《Kth Smallest in BST》目前隱含的前提寫成 contract：找 BST 中第 k 小節點值。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Implement Trie


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 支援 insert、完整 word search 與 prefix search。
>
> **核心轉換：** 每個 node 代表一個 prefix；children edge 消耗一個字元，terminal flag 區分完整 word 與只有共同 prefix。
>
> **主要知識點：** BST Order、Trie Prefix 與逐位決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Implement Trie
      │
      ├─ 暴力路線：忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每個 node 代表一個 prefix；children edge 消耗一個字元，terminal flag 區分完整 word 與只有共同 prefix。
      │
Pattern toolbox：BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata
      │
      ├─ 狀態轉移：BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進
      │
      ├─ 永遠成立：BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 支援 insert、完整 word search 與 prefix search。
2. **寫出暴力：** 忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每個 node 代表一個 prefix；children edge 消耗一個字元，terminal flag 區分完整 word 與只有共同 prefix。
4. **定義 state 與轉移：** 使用「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」承載上述觀察，再執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」代表什麼，再說每一步如何「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix」的 base case。
>
> 2. **維持：** 每次執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」後，狀態仍與已處理資料一致。關鍵論證是：BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.end = False


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for ch in word:
            node = node.children.setdefault(ch, TrieNode())
        node.end = True

    def search(self, word):
        node = self._walk(word)
        return bool(node and node.end)

    def startsWith(self, prefix):
        return self._walk(prefix) is not None

    def _walk(self, text):
        node = self.root
        for ch in text:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node
```

### Follow-up 1：原題直接變形
**問：支援刪除 word？**

**答：**遞迴走到 word 結尾取消 `end`，回程時若 child 沒有 children 且不是其他 word 終點才刪除；不能破壞共享 prefix。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Implement Trie》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每個 node 代表一個 prefix；children edge 消耗一個字元，terminal flag 區分完整 word 與只有共同 prefix。 失效情境包括：BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。
>
> 替代路線是：使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。
>
> 套回《Implement Trie》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。
>
> 此外必須把《Implement Trie》目前隱含的前提寫成 contract：支援 insert、完整 word search 與 prefix search。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Serialize and Deserialize BST

### 題目

以比一般 binary tree 更精簡的格式序列化 BST。

> [!tip]- 三層提示
> 1. BST 的 preorder 加上值域限制即可唯一重建。
> 2. 不必保存 null sentinel。
> 3. 若下一個值不在目前 `(low,high)`，它不屬於此子樹。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 以比一般 binary tree 更精簡的格式序列化 BST。
>
> **核心轉換：** Serialize 只輸出 preorder。Deserialize 依序看下一個值：若落在目前範圍，消費並建立節點；接著以縮小範圍遞迴建立左右子樹。
>
> **主要知識點：** BST Order、Trie Prefix 與逐位決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Serialize and Deserialize BST
      │
      ├─ 暴力路線：忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Serialize 只輸出 preorder。Deserialize 依序看下一個值：若落在目前範圍，消費並建立節點；接著以縮小範圍遞迴建立左右子樹。
      │
Pattern toolbox：BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata
      │
      ├─ 狀態轉移：BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進
      │
      ├─ 永遠成立：BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 以比一般 binary tree 更精簡的格式序列化 BST。
2. **寫出暴力：** 忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Serialize 只輸出 preorder。Deserialize 依序看下一個值：若落在目前範圍，消費並建立節點；接著以縮小範圍遞迴建立左右子樹。
4. **定義 state 與轉移：** 使用「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」承載上述觀察，再執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(h)$ recursion，加 serialized output

> [!tip] 一句話記憶
> 先說清楚「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」代表什麼，再說每一步如何「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix」的 base case。
>
> 2. **維持：** 每次執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」後，狀態仍與已處理資料一致。關鍵論證是：BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Serialize 只輸出 preorder。Deserialize 依序看下一個值：若落在目前範圍，消費並建立節點；接著以縮小範圍遞迴建立左右子樹。

```python
class BSTCodec:
    def serialize(self, root):
        values = []

        def preorder(node):
            if not node:
                return
            values.append(str(node.val))
            preorder(node.left)
            preorder(node.right)

        preorder(root)
        return " ".join(values)

    def deserialize(self, data):
        if not data:
            return None
        values = list(map(int, data.split()))
        index = 0

        def build(low, high):
            nonlocal index
            if index == len(values) or not (low < values[index] < high):
                return None
            value = values[index]
            index += 1
            node = TreeNode(value)
            node.left = build(low, value)
            node.right = build(value, high)
            return node

        return build(float("-inf"), float("inf"))
```

- 時間：$O(n)$
- 空間：$O(h)$ recursion，加 serialized output

### Follow-up 1：原題直接變形
**問：允許 duplicate 時怎麼辦？**

**答：**必須先定義 duplicate placement policy，再把 boundary 改成 inclusive/exclusive；沒有一致 policy，只有 preorder 不能唯一還原。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Serialize and Deserialize BST》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Serialize 只輸出 preorder。Deserialize 依序看下一個值：若落在目前範圍，消費並建立節點；接著以縮小範圍遞迴建立左右子樹。 失效情境包括：BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。
>
> 替代路線是：使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。
>
> 套回《Serialize and Deserialize BST》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。
>
> 此外必須把《Serialize and Deserialize BST》目前隱含的前提寫成 contract：以比一般 binary tree 更精簡的格式序列化 BST。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Recover Binary Search Tree

### 題目

BST 中恰有兩個節點值被交換，不改結構將其修復。

> [!tip]- 三層提示
> 1. BST inorder 應嚴格遞增。
> 2. 交換後會出現一或兩個 inversion。
> 3. 第一個錯誤節點是第一次 inversion 的前者；第二個是不斷更新的後者。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** BST 中恰有兩個節點值被交換，不改結構將其修復。
>
> **核心轉換：** Inorder 時比較 previous.val > current.val。第一次 inversion 設 first=previous；每次 inversion 都更新 second=current。最後交換值。
>
> **主要知識點：** BST Order、Trie Prefix 與逐位決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Recover Binary Search Tree
      │
      ├─ 暴力路線：忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Inorder 時比較 previous.val > current.val。第一次 inversion 設 first=previous；每次 inversion 都更新 second=current。最後交換值。
      │
Pattern toolbox：BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata
      │
      ├─ 狀態轉移：BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進
      │
      ├─ 永遠成立：BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** BST 中恰有兩個節點值被交換，不改結構將其修復。
2. **寫出暴力：** 忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Inorder 時比較 previous.val > current.val。第一次 inversion 設 first=previous；每次 inversion 都更新 second=current。最後交換值。
4. **定義 state 與轉移：** 使用「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」承載上述觀察，再執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(h)$

> [!tip] 一句話記憶
> 先說清楚「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」代表什麼，再說每一步如何「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix」的 base case。
>
> 2. **維持：** 每次執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」後，狀態仍與已處理資料一致。關鍵論證是：BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Inorder 時比較 `previous.val > current.val`。第一次 inversion 設 `first=previous`；每次 inversion 都更新 `second=current`。最後交換值。

```python
def recover_tree(root):
    stack = []
    current = root
    previous = first = second = None

    while stack or current:
        while current:
            stack.append(current)
            current = current.left
        current = stack.pop()
        if previous and previous.val > current.val:
            if first is None:
                first = previous
            second = current
        previous = current
        current = current.right

    first.val, second.val = second.val, first.val
```

- 時間：$O(n)$
- 空間：$O(h)$

### Follow-up 1：原題直接變形
**問：要求 $O(1)$ 額外空間？**

**答：**使用 Morris inorder traversal，以 temporary threaded links 取代 stack；偵測 inversion 的邏輯完全相同，結束前必須恢復所有暫時指標。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Recover Binary Search Tree》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Inorder 時比較 previous.val > current.val。第一次 inversion 設 first=previous；每次 inversion 都更新 second=current。最後交換值。 失效情境包括：BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。
>
> 替代路線是：使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。
>
> 套回《Recover Binary Search Tree》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。
>
> 此外必須把《Recover Binary Search Tree》目前隱含的前提寫成 contract：BST 中恰有兩個節點值被交換，不改結構將其修復。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Word Search II

### 題目

在字母矩陣中找出 dictionary 內所有可由上下左右相鄰、不重複使用格子形成的 words。

> [!tip]- 三層提示
> 1. 對每個 word 個別 DFS 會重複探索共同 prefix。
> 2. 把 dictionary 建成 trie。
> 3. DFS 走到 trie 不存在的 child 時立即剪枝；找到 word 後移除避免重複。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在字母矩陣中找出 dictionary 內所有可由上下左右相鄰、不重複使用格子形成的 words。
>
> **核心轉換：** Trie node 保存完整 word 作終點標記。DFS 同步在 board 與 trie 上前進；回程若某 child 已無分支且非終點，從 parent 刪除，讓後續搜尋更快。
>
> **主要知識點：** BST Order、Trie Prefix 與逐位決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Word Search II
      │
      ├─ 暴力路線：忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Trie node 保存完整 word 作終點標記。DFS 同步在 board 與 trie 上前進；回程若某 child 已無分支且非終點，從 parent 刪除，讓後續搜尋更快。
      │
Pattern toolbox：BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata
      │
      ├─ 狀態轉移：BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進
      │
      ├─ 永遠成立：BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在字母矩陣中找出 dictionary 內所有可由上下左右相鄰、不重複使用格子形成的 words。
2. **寫出暴力：** 忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Trie node 保存完整 word 作終點標記。DFS 同步在 board 與 trie 上前進；回程若某 child 已無分支且非終點，從 parent 刪除，讓後續搜尋更快。
4. **定義 state 與轉移：** 使用「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」承載上述觀察，再執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：上限與 board 分支及 word 長度相關，trie 大幅剪枝；空間：$O(\sum word)$

> [!tip] 一句話記憶
> 先說清楚「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」代表什麼，再說每一步如何「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix」的 base case。
>
> 2. **維持：** 每次執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」後，狀態仍與已處理資料一致。關鍵論證是：BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Trie node 保存完整 `word` 作終點標記。DFS 同步在 board 與 trie 上前進；回程若某 child 已無分支且非終點，從 parent 刪除，讓後續搜尋更快。

```python
def find_words(board, words):
    root = {}
    end = "$"
    for word in words:
        node = root
        for ch in word:
            node = node.setdefault(ch, {})
        node[end] = word

    rows, cols = len(board), len(board[0])
    answer = []

    def dfs(r, c, parent):
        ch = board[r][c]
        if ch not in parent:
            return
        node = parent[ch]
        word = node.pop(end, None)
        if word:
            answer.append(word)

        board[r][c] = "#"
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != "#":
                dfs(nr, nc, node)
        board[r][c] = ch

        if not node:
            parent.pop(ch)

    for r in range(rows):
        for c in range(cols):
            dfs(r, c, root)
    return answer
```

- 時間：上限與 board 分支及 word 長度相關，trie 大幅剪枝
- 空間：$O(\sum |word|)$

### Follow-up 1：原題直接變形
**問：board 不可修改？**

**答：**使用 visited set 或 boolean matrix；path 長度為 `L` 時額外空間 $O(L)$。若允許 bitmask 且格子數小，也可把 visited 壓成整數。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Word Search II》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Trie node 保存完整 word 作終點標記。DFS 同步在 board 與 trie 上前進；回程若某 child 已無分支且非終點，從 parent 刪除，讓後續搜尋更快。 失效情境包括：BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。
>
> 替代路線是：使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。
>
> 套回《Word Search II》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。
>
> 此外必須把《Word Search II》目前隱含的前提寫成 contract：在字母矩陣中找出 dictionary 內所有可由上下左右相鄰、不重複使用格子形成的 words。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Design Search Autocomplete System

### 題目

輸入字元後回傳具有目前 prefix 的前三個熱門句子；先依頻率降序，再依字典序。輸入 `#` 代表完成並把句子頻率加一。

> [!tip]- 三層提示
> 1. Trie 對應 prefix。
> 2. 終點保存 sentence frequency。
> 3. 簡單版可 DFS 收集 subtree；高效版在每個 node cache top 3。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 輸入字元後回傳具有目前 prefix 的前三個熱門句子；先依頻率降序，再依字典序。輸入 代表完成並把句子頻率加一。
>
> **核心轉換：** 以下版本把所有句子頻率保存在 map，Trie node 保存通過該 prefix 的 sentence set。輸入字元後排序候選。這個版本易於面試說明；production 版應在更新時維護每個 node 的 top 3。
>
> **主要知識點：** BST Order、Trie Prefix 與逐位決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Design Search Autocomplete System
      │
      ├─ 暴力路線：忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串
      │
      ▼  找出本題最關鍵的轉換
核心觀察：以下版本把所有句子頻率保存在 map，Trie node 保存通過該 prefix 的 sentence set。輸入字元後排序候選。這個版本易於面試說明；production 版應在更新時維護每個 node 的 top 3。
      │
Pattern toolbox：BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata
      │
      ├─ 狀態轉移：BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進
      │
      ├─ 永遠成立：BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 輸入字元後回傳具有目前 prefix 的前三個熱門句子；先依頻率降序，再依字典序。輸入 代表完成並把句子頻率加一。
2. **寫出暴力：** 忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 以下版本把所有句子頻率保存在 map，Trie node 保存通過該 prefix 的 sentence set。輸入字元後排序候選。這個版本易於面試說明；production 版應在更新時維護每個 node 的 top 3。
4. **定義 state 與轉移：** 使用「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」承載上述觀察，再執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」代表什麼，再說每一步如何「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix」的 base case。
>
> 2. **維持：** 每次執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」後，狀態仍與已處理資料一致。關鍵論證是：BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

以下版本把所有句子頻率保存在 map，Trie node 保存通過該 prefix 的 sentence set。輸入字元後排序候選。這個版本易於面試說明；production 版應在更新時維護每個 node 的 top 3。

```python
from collections import defaultdict

class AutocompleteSystem:
    def __init__(self, sentences, times):
        self.root = {}
        self.frequency = defaultdict(int)
        self.current = ""
        for sentence, count in zip(sentences, times):
            self.frequency[sentence] += count
            self._insert(sentence)

    def _insert(self, sentence):
        node = self.root
        for ch in sentence:
            node = node.setdefault(ch, {"_sentences": set()})
            node["_sentences"].add(sentence)

    def input(self, ch):
        if ch == "#":
            self.frequency[self.current] += 1
            self._insert(self.current)
            self.current = ""
            return []

        self.current += ch
        node = self.root
        for char in self.current:
            if char not in node:
                return []
            node = node[char]
        candidates = node["_sentences"]
        return sorted(
            candidates,
            key=lambda sentence: (-self.frequency[sentence], sentence),
        )[:3]
```

### Follow-up 1：原題直接變形
**問：如何讓每次查詢接近 $O(prefix+3)$？**

**答：**每個 trie node cache 排序後 top 3。新增或頻率更新句子時，沿其 path 更新 cache；若句子數大且更新頻繁，可保存 bounded heap 或 ordered set。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Design Search Autocomplete System》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：以下版本把所有句子頻率保存在 map，Trie node 保存通過該 prefix 的 sentence set。輸入字元後排序候選。這個版本易於面試說明；production 版應在更新時維護每個 node 的 top 3。 失效情境包括：BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。
>
> 替代路線是：使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。
>
> 套回《Design Search Autocomplete System》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。
>
> 此外必須把《Design Search Autocomplete System》目前隱含的前提寫成 contract：輸入字元後回傳具有目前 prefix 的前三個熱門句子；先依頻率降序，再依字典序。輸入 代表完成並把句子頻率加一。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Maximum XOR of Two Numbers

### 題目

在非負整數陣列中選兩數，使 XOR 最大。

> [!tip]- 三層提示
> 1. XOR 從最高 bit 開始決定大小。
> 2. 對目前 bit，最好選相反 bit。
> 3. 把所有數的 bit representation 插入 binary trie。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在非負整數陣列中選兩數，使 XOR 最大。
>
> **核心轉換：** 對每個數從最高 bit 往下查 trie。若存在相反 bit，就選它並在答案該位設 1；否則只能選相同 bit。
>
> **主要知識點：** BST Order、Trie Prefix 與逐位決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Maximum XOR of Two Numbers
      │
      ├─ 暴力路線：忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串
      │
      ▼  找出本題最關鍵的轉換
核心觀察：對每個數從最高 bit 往下查 trie。若存在相反 bit，就選它並在答案該位設 1；否則只能選相同 bit。
      │
Pattern toolbox：BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata
      │
      ├─ 狀態轉移：BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進
      │
      ├─ 永遠成立：BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在非負整數陣列中選兩數，使 XOR 最大。
2. **寫出暴力：** 忽略有序性做全樹搜尋，或對每次 prefix query 掃描所有字串。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 對每個數從最高 bit 往下查 trie。若存在相反 bit，就選它並在答案該位設 1；否則只能選相同 bit。
4. **定義 state 與轉移：** 使用「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」承載上述觀察，再執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(nB)$，B 為 bit 數；空間：$O(nB)$

> [!tip] 一句話記憶
> 先說清楚「BST 的上下界／inorder rank，或 Trie node 的 children、terminal 與聚合 metadata」代表什麼，再說每一步如何「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「BST 節點受 ancestor bounds 約束；Trie 路徑恰代表已匹配 prefix，node metadata 只描述該 prefix」的 base case。
>
> 2. **維持：** 每次執行「BST 用 order 排除整個 subtree；Trie 每次消耗一個字元或 bit，沿 prefix state 前進」後，狀態仍與已處理資料一致。關鍵論證是：BST 以區間 bound induction 證明；Trie 以已消耗字元數 induction，證明每一步與 prefix 一一對應。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：duplicate key 政策、空字串、Unicode、刪除後空 node、深樹、prefix 本身也是 word。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

對每個數從最高 bit 往下查 trie。若存在相反 bit，就選它並在答案該位設 1；否則只能選相同 bit。

```python
def find_maximum_xor(nums):
    root = {}
    highest = max(nums, default=0).bit_length() - 1

    for number in nums:
        node = root
        for bit in range(highest, -1, -1):
            value = (number >> bit) & 1
            node = node.setdefault(value, {})

    answer = 0
    for number in nums:
        node = root
        value = 0
        for bit in range(highest, -1, -1):
            current = (number >> bit) & 1
            wanted = 1 - current
            if wanted in node:
                value |= 1 << bit
                node = node[wanted]
            else:
                node = node[current]
        answer = max(answer, value)
    return answer
```

- 時間：$O(nB)$，`B` 為 bit 數
- 空間：$O(nB)$

### Follow-up 1：原題直接變形
**問：資料 streaming，需支援插入後立即查目前最大 XOR？**

**答：**每次新數先查既有 trie 的最佳 XOR，再插入；單次 $O(B)$。若還要刪除，trie node 需保存 reference count。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Maximum XOR of Two Numbers》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：對每個數從最高 bit 往下查 trie。若存在相反 bit，就選它並在答案該位設 1；否則只能選相同 bit。 失效情境包括：BST 失衡會退化；Trie alphabet 太大會爆記憶體；動態 rank 只靠普通 BST metadata 不夠。
>
> 替代路線是：使用 balanced BST/order-statistic tree、compressed/radix trie、hash children 或 bitwise trie。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：BST 保存 parent/rank；Trie terminal 保存原字串、頻率或 top suggestions，搜尋時即可重建完整答案。
>
> 套回《Maximum XOR of Two Numbers》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Autocomplete 要處理頻率更新、cache 與 normalization；大量 Trie node 需壓縮。併發更新採 copy-on-write 或細粒度 lock。
>
> 此外必須把《Maximum XOR of Two Numbers》目前隱含的前提寫成 contract：在非負整數陣列中選兩數，使 XOR 最大。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] BST 會傳遞祖先範圍。
- [ ] 知道 inorder 與 order statistic 的關係。
- [ ] Trie node 代表 prefix，不只是字元。
- [ ] 能在 trie 搜尋時做結構 pruning。
