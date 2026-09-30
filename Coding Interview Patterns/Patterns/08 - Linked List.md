---
title: Linked List
tags:
  - coding-interview/pattern
  - linked-list
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 08 — Linked List

[[07 - Stack and Monotonic Stack|← 上一章]] · [[00 - Book Index|目錄]] · [[09 - Binary Tree|下一章 →]]

> [!abstract] Mental model
> Linked list 題的難點不是走訪，而是修改 pointer 前先保存下一步，並維護「已處理區與未處理區」的邊界。Dummy node 能消除 head 的特殊案例。

## 基本節點

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
```

---

## 核心題 1：Reverse Linked List


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 將 singly linked list 原地反轉並回傳新 head。
>
> **核心轉換：** 每輪先保存 next_node，再把 current.next 指向 prev；完成後 prev 是反轉區段的新 head，current 是尚未處理區段。
>
> **主要知識點：** Linked List 指標重接與局部不變量。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Reverse Linked List
      │
      ├─ 暴力路線：為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每輪先保存 next_node，再把 current.next 指向 prev；完成後 prev 是反轉區段的新 head，current 是尚未處理區段。
      │
Pattern toolbox：少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap
      │
      ├─ 狀態轉移：先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結
      │
      ├─ 永遠成立：已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 將 singly linked list 原地反轉並回傳新 head。
2. **寫出暴力：** 為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每輪先保存 next_node，再把 current.next 指向 prev；完成後 prev 是反轉區段的新 head，current 是尚未處理區段。
4. **定義 state 與轉移：** 使用「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」承載上述觀察，再執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」代表什麼，再說每一步如何「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達」的 base case。
>
> 2. **維持：** 每次執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」後，狀態仍與已處理資料一致。關鍵論證是：以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def reverse_list(head):
    previous = None
    current = head
    while current:
        next_node = current.next
        current.next = previous
        previous = current
        current = next_node
    return previous
```

**Invariant：**`previous` 是已反轉 prefix 的 head；`current` 是尚未處理 suffix 的 head。

### Follow-up 1：原題直接變形
**問：反轉 index `[left,right]`？**

**答：**用 dummy 走到反轉區前一個節點，再做 head-insertion：反覆把 `current.next` 摘下插到區間前端，總時間 $O(n)$、空間 $O(1)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Reverse Linked List》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每輪先保存 next_node，再把 current.next 指向 prev；完成後 prev 是反轉區段的新 head，current 是尚未處理區段。 失效情境包括：若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。
>
> 替代路線是：可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。
>
> 套回《Reverse Linked List》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。
>
> 此外必須把《Reverse Linked List》目前隱含的前提寫成 contract：將 singly linked list 原地反轉並回傳新 head。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Remove Nth Node From End


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 刪除 linked list 倒數第 n 個節點並回傳 head。
>
> **核心轉換：** dummy 消除刪 head 特例；fast 先走 n+1 步，再讓 fast/slow 同速前進，fast 到尾時 slow 正好在待刪節點前一格。
>
> **主要知識點：** Linked List 指標重接與局部不變量。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Remove Nth Node From End
      │
      ├─ 暴力路線：為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理
      │
      ▼  找出本題最關鍵的轉換
核心觀察：dummy 消除刪 head 特例；fast 先走 n+1 步，再讓 fast/slow 同速前進，fast 到尾時 slow 正好在待刪節點前一格。
      │
Pattern toolbox：少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap
      │
      ├─ 狀態轉移：先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結
      │
      ├─ 永遠成立：已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 刪除 linked list 倒數第 n 個節點並回傳 head。
2. **寫出暴力：** 為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** dummy 消除刪 head 特例；fast 先走 n+1 步，再讓 fast/slow 同速前進，fast 到尾時 slow 正好在待刪節點前一格。
4. **定義 state 與轉移：** 使用「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」承載上述觀察，再執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」代表什麼，再說每一步如何「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達」的 base case。
>
> 2. **維持：** 每次執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」後，狀態仍與已處理資料一致。關鍵論證是：以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def remove_nth_from_end(head, n):
    dummy = ListNode(0, head)
    fast = slow = dummy
    for _ in range(n):
        fast = fast.next
    while fast.next:
        fast = fast.next
        slow = slow.next
    slow.next = slow.next.next
    return dummy.next
```

### Follow-up 1：原題直接變形
**問：為何 fast 先走 `n` 步，最後 slow 在待刪節點前一格？**

**答：**fast 與 slow 始終相距 `n` 個 edge；當 fast 到 tail，slow 後面的節點數恰為 `n`，所以 `slow.next` 是倒數第 `n` 個。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Remove Nth Node From End》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：dummy 消除刪 head 特例；fast 先走 n+1 步，再讓 fast/slow 同速前進，fast 到尾時 slow 正好在待刪節點前一格。 失效情境包括：若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。
>
> 替代路線是：可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。
>
> 套回《Remove Nth Node From End》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。
>
> 此外必須把《Remove Nth Node From End》目前隱含的前提寫成 contract：刪除 linked list 倒數第 n 個節點並回傳 head。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Copy List with Random Pointer

### 題目

每個節點除 `next` 外還有 `random`。建立深拷貝，要求 $O(1)$ 額外空間。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每個節點除 next 外還有 random。建立深拷貝，要求 $O(1)$ 額外空間。
>
> **核心轉換：** 把 copy node 插在原 node 後方；此時原節點 x 的 copy 是 x.next，所以 copy 的 random 是 x.random.next。最後拆開兩條 list。
>
> **主要知識點：** Linked List 指標重接與局部不變量。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Copy List with Random Pointer
      │
      ├─ 暴力路線：為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理
      │
      ▼  找出本題最關鍵的轉換
核心觀察：把 copy node 插在原 node 後方；此時原節點 x 的 copy 是 x.next，所以 copy 的 random 是 x.random.next。最後拆開兩條 list。
      │
Pattern toolbox：少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap
      │
      ├─ 狀態轉移：先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結
      │
      ├─ 永遠成立：已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每個節點除 next 外還有 random。建立深拷貝，要求 $O(1)$ 額外空間。
2. **寫出暴力：** 為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 把 copy node 插在原 node 後方；此時原節點 x 的 copy 是 x.next，所以 copy 的 random 是 x.random.next。最後拆開兩條 list。
4. **定義 state 與轉移：** 使用「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」承載上述觀察，再執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」代表什麼，再說每一步如何「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達」的 base case。
>
> 2. **維持：** 每次執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」後，狀態仍與已處理資料一致。關鍵論證是：以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

把 copy node 插在原 node 後方；此時原節點 `x` 的 copy 是 `x.next`，所以 copy 的 random 是 `x.random.next`。最後拆開兩條 list。

```python
def copy_random_list(head):
    current = head
    while current:
        copy = Node(current.val)
        copy.next = current.next
        current.next = copy
        current = copy.next

    current = head
    while current:
        if current.random:
            current.next.random = current.random.next
        current = current.next.next

    dummy = Node(0)
    copy_tail = dummy
    current = head
    while current:
        copy = current.next
        current.next = copy.next
        copy_tail.next = copy
        copy_tail = copy
        current = current.next
    return dummy.next
```

### Follow-up 1：原題直接變形
**問：random 可指向任意圖節點，不保證都在 next chain？**

**答：**interleaving 不再足夠；應把結構視為 graph，以 map `original -> copy` 搭配 DFS/BFS 複製所有 edge。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Copy List with Random Pointer》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：把 copy node 插在原 node 後方；此時原節點 x 的 copy 是 x.next，所以 copy 的 random 是 x.random.next。最後拆開兩條 list。 失效情境包括：若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。
>
> 替代路線是：可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。
>
> 套回《Copy List with Random Pointer》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。
>
> 此外必須把《Copy List with Random Pointer》目前隱含的前提寫成 contract：每個節點除 next 外還有 random。建立深拷貝，要求 $O(1)$ 額外空間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Reverse Nodes in k-Group

### 題目

每 `k` 個節點一組反轉；最後不足 `k` 個保持原順序。

> [!tip]- 三層提示
> 1. Dummy 指向整條 list。
> 2. 每輪先確認第 `k` 個節點存在。
> 3. 反轉範圍是 `[group_start, group_next)`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每 k 個節點一組反轉；最後不足 k 個保持原順序。
>
> **核心轉換：** groupprev 是本組前一節點，kth 是本組最後節點，groupnext = kth.next。反轉時初始 previous = groupnext，可讓新 tail 自動接回後段。
>
> **主要知識點：** Linked List 指標重接與局部不變量。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Reverse Nodes in k-Group
      │
      ├─ 暴力路線：為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理
      │
      ▼  找出本題最關鍵的轉換
核心觀察：groupprev 是本組前一節點，kth 是本組最後節點，groupnext = kth.next。反轉時初始 previous = groupnext，可讓新 tail 自動接回後段。
      │
Pattern toolbox：少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap
      │
      ├─ 狀態轉移：先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結
      │
      ├─ 永遠成立：已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每 k 個節點一組反轉；最後不足 k 個保持原順序。
2. **寫出暴力：** 為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** groupprev 是本組前一節點，kth 是本組最後節點，groupnext = kth.next。反轉時初始 previous = groupnext，可讓新 tail 自動接回後段。
4. **定義 state 與轉移：** 使用「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」承載上述觀察，再執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」代表什麼，再說每一步如何「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達」的 base case。
>
> 2. **維持：** 每次執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」後，狀態仍與已處理資料一致。關鍵論證是：以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`group_prev` 是本組前一節點，`kth` 是本組最後節點，`group_next = kth.next`。反轉時初始 `previous = group_next`，可讓新 tail 自動接回後段。

```python
def reverse_k_group(head, k):
    dummy = ListNode(0, head)
    group_prev = dummy

    while True:
        kth = group_prev
        for _ in range(k):
            kth = kth.next
            if not kth:
                return dummy.next

        group_next = kth.next
        previous = group_next
        current = group_prev.next
        while current != group_next:
            next_node = current.next
            current.next = previous
            previous = current
            current = next_node

        old_start = group_prev.next
        group_prev.next = kth
        group_prev = old_start
```

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：若每組大小依序為 `1,2,3,...`，只有偶數長度組反轉？**

**答：**每輪先計算實際 group length；若為偶數使用同樣區間反轉，否則只前進。最後一組以實際長度判斷。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Reverse Nodes in k-Group》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：groupprev 是本組前一節點，kth 是本組最後節點，groupnext = kth.next。反轉時初始 previous = groupnext，可讓新 tail 自動接回後段。 失效情境包括：若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。
>
> 替代路線是：可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。
>
> 套回《Reverse Nodes in k-Group》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。
>
> 此外必須把《Reverse Nodes in k-Group》目前隱含的前提寫成 contract：每 k 個節點一組反轉；最後不足 k 個保持原順序。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Merge k Sorted Lists

### 題目

合併 `k` 條排序 linked lists。

> [!tip]- 三層提示
> 1. 每次答案只可能來自某條 list 的 head。
> 2. 用 min heap 保存每條非空 list 的目前 head。
> 3. Python heap tie 時不能直接比較任意 node，要加入 unique id。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 合併 k 條排序 linked lists。
>
> **核心轉換：** Heap 大小最多 k。彈出最小節點接到答案，再把該節點的 next 推入。
>
> **主要知識點：** Linked List 指標重接與局部不變量。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Merge k Sorted Lists
      │
      ├─ 暴力路線：為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Heap 大小最多 k。彈出最小節點接到答案，再把該節點的 next 推入。
      │
Pattern toolbox：少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap
      │
      ├─ 狀態轉移：先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結
      │
      ├─ 永遠成立：已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 合併 k 條排序 linked lists。
2. **寫出暴力：** 為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Heap 大小最多 k。彈出最小節點接到答案，再把該節點的 next 推入。
4. **定義 state 與轉移：** 使用「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」承載上述觀察，再執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(N\log k)$；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」代表什麼，再說每一步如何「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達」的 base case。
>
> 2. **維持：** 每次執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」後，狀態仍與已處理資料一致。關鍵論證是：以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Heap 大小最多 `k`。彈出最小節點接到答案，再把該節點的 next 推入。

```python
from heapq import heappush, heappop
from itertools import count

def merge_k_lists(lists):
    heap = []
    unique = count()
    for node in lists:
        if node:
            heappush(heap, (node.val, next(unique), node))

    dummy = ListNode()
    tail = dummy
    while heap:
        _, _, node = heappop(heap)
        tail.next = node
        tail = node
        if node.next:
            heappush(heap, (node.next.val, next(unique), node.next))
    return dummy.next
```

- 時間：$O(N\log k)$
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：不用 heap？**

**答：**以 divide and conquer 兩兩 merge，仍為 $O(N\log k)$，額外 heap 空間可省下；recursive 版本使用 $O(\log k)$ call stack。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Merge k Sorted Lists》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Heap 大小最多 k。彈出最小節點接到答案，再把該節點的 next 推入。 失效情境包括：若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。
>
> 替代路線是：可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。
>
> 套回《Merge k Sorted Lists》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。
>
> 此外必須把《Merge k Sorted Lists》目前隱含的前提寫成 contract：合併 k 條排序 linked lists。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：LRU Cache

### 題目

設計固定容量 cache，`get`、`put` 皆為平均 $O(1)$；超過容量時刪除 least recently used。

> [!tip]- 三層提示
> 1. Hash map 提供 $O(1)$ 定位。
> 2. Doubly linked list 提供 $O(1)$ 刪除與移到前端。
> 3. Map 保存 `key -> node`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 設計固定容量 cache，get、put 皆為平均 $O(1)$；超過容量時刪除 least recently used。
>
> **核心轉換：** Head 後方是 MRU，tail 前方是 LRU。任何 get 或更新都把 node 移到前方。
>
> **主要知識點：** Linked List 指標重接與局部不變量。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：LRU Cache
      │
      ├─ 暴力路線：為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Head 後方是 MRU，tail 前方是 LRU。任何 get 或更新都把 node 移到前方。
      │
Pattern toolbox：少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap
      │
      ├─ 狀態轉移：先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結
      │
      ├─ 永遠成立：已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 設計固定容量 cache，get、put 皆為平均 $O(1)$；超過容量時刪除 least recently used。
2. **寫出暴力：** 為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Head 後方是 MRU，tail 前方是 LRU。任何 get 或更新都把 node 移到前方。
4. **定義 state 與轉移：** 使用「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」承載上述觀察，再執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：每個操作：平均 $O(1)$；空間：$O(capacity)$

> [!tip] 一句話記憶
> 先說清楚「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」代表什麼，再說每一步如何「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達」的 base case。
>
> 2. **維持：** 每次執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」後，狀態仍與已處理資料一致。關鍵論證是：以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Head 後方是 MRU，tail 前方是 LRU。任何 `get` 或更新都把 node 移到前方。

```python
class DNode:
    def __init__(self, key=0, value=0):
        self.key = key
        self.value = value
        self.prev = self.next = None


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.nodes = {}
        self.head = DNode()
        self.tail = DNode()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_front(self, node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def _touch(self, node):
        self._remove(node)
        self._add_front(node)

    def get(self, key):
        if key not in self.nodes:
            return -1
        node = self.nodes[key]
        self._touch(node)
        return node.value

    def put(self, key, value):
        if key in self.nodes:
            node = self.nodes[key]
            node.value = value
            self._touch(node)
            return

        node = DNode(key, value)
        self.nodes[key] = node
        self._add_front(node)
        if len(self.nodes) > self.capacity:
            victim = self.tail.prev
            self._remove(victim)
            del self.nodes[victim.key]
```

- 每個操作：平均 $O(1)$
- 空間：$O(capacity)$

### Follow-up 1：原題直接變形
**問：加入 TTL 與 thread safety？**

**答：**node 增加 expiry，另用 min heap lazy 清理過期項目；多執行緒需以 lock 保護 map 與 list 的原子更新。若要求高併發，可考慮分片 cache，但全域 LRU 語意會改變。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《LRU Cache》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Head 後方是 MRU，tail 前方是 LRU。任何 get 或更新都把 node 移到前方。 失效情境包括：若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。
>
> 替代路線是：可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。
>
> 套回《LRU Cache》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。
>
> 此外必須把《LRU Cache》目前隱含的前提寫成 contract：設計固定容量 cache，get、put 皆為平均 $O(1)$；超過容量時刪除 least recently used。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：LFU Cache

### 題目

超過容量時刪除使用頻率最低者；頻率相同時刪除最久未使用者。`get`、`put` 平均 $O(1)$。

> [!tip]- 三層提示
> 1. 保存 `key -> (value, frequency)`。
> 2. 每個 frequency 需要一個維持 LRU 順序的容器。
> 3. 維護目前最小 frequency。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 超過容量時刪除使用頻率最低者；頻率相同時刪除最久未使用者。get、put 平均 $O(1)$。
>
> **核心轉換：** freqtokeys[f] 是 OrderedDict，最前端是該頻率最久未使用 key。Touch 時從 f 移到 f+1；若最小頻率 bucket 空了，minfreq += 1。
>
> **主要知識點：** Linked List 指標重接與局部不變量。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：LFU Cache
      │
      ├─ 暴力路線：為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理
      │
      ▼  找出本題最關鍵的轉換
核心觀察：freqtokeys[f] 是 OrderedDict，最前端是該頻率最久未使用 key。Touch 時從 f 移到 f+1；若最小頻率 bucket 空了，minfreq += 1。
      │
Pattern toolbox：少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap
      │
      ├─ 狀態轉移：先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結
      │
      ├─ 永遠成立：已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 超過容量時刪除使用頻率最低者；頻率相同時刪除最久未使用者。get、put 平均 $O(1)$。
2. **寫出暴力：** 為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** freqtokeys[f] 是 OrderedDict，最前端是該頻率最久未使用 key。Touch 時從 f 移到 f+1；若最小頻率 bucket 空了，minfreq += 1。
4. **定義 state 與轉移：** 使用「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」承載上述觀察，再執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：每個操作：平均 $O(1)$；空間：$O(capacity)$

> [!tip] 一句話記憶
> 先說清楚「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」代表什麼，再說每一步如何「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達」的 base case。
>
> 2. **維持：** 每次執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」後，狀態仍與已處理資料一致。關鍵論證是：以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`freq_to_keys[f]` 是 OrderedDict，最前端是該頻率最久未使用 key。Touch 時從 `f` 移到 `f+1`；若最小頻率 bucket 空了，`min_freq += 1`。

```python
from collections import defaultdict, OrderedDict

class LFUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.values = {}
        self.freq_to_keys = defaultdict(OrderedDict)
        self.min_freq = 0

    def _touch(self, key):
        value, freq = self.values[key]
        del self.freq_to_keys[freq][key]
        if not self.freq_to_keys[freq]:
            del self.freq_to_keys[freq]
            if self.min_freq == freq:
                self.min_freq += 1
        self.values[key] = (value, freq + 1)
        self.freq_to_keys[freq + 1][key] = None

    def get(self, key):
        if key not in self.values:
            return -1
        value = self.values[key][0]
        self._touch(key)
        return value

    def put(self, key, value):
        if self.capacity == 0:
            return
        if key in self.values:
            _, freq = self.values[key]
            self.values[key] = (value, freq)
            self._touch(key)
            return

        if len(self.values) == self.capacity:
            victim, _ = self.freq_to_keys[self.min_freq].popitem(last=False)
            if not self.freq_to_keys[self.min_freq]:
                del self.freq_to_keys[self.min_freq]
            del self.values[victim]

        self.values[key] = (value, 1)
        self.freq_to_keys[1][key] = None
        self.min_freq = 1
```

- 每個操作：平均 $O(1)$
- 空間：$O(capacity)$

### Follow-up 1：原題直接變形
**問：頻率會無限增長怎麼辦？**

**答：**production cache 常使用 aging／decay，例如定期把頻率除二，或使用近似 sketch。這會犧牲嚴格 LFU 語意以避免舊熱門項目永久佔據 cache。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《LFU Cache》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：freqtokeys[f] 是 OrderedDict，最前端是該頻率最久未使用 key。Touch 時從 f 移到 f+1；若最小頻率 bucket 空了，minfreq += 1。 失效情境包括：若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。
>
> 替代路線是：可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。
>
> 套回《LFU Cache》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。
>
> 此外必須把《LFU Cache》目前隱含的前提寫成 contract：超過容量時刪除使用頻率最低者；頻率相同時刪除最久未使用者。get、put 平均 $O(1)$。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Sort List

### 題目

在 $O(n\log n)$ 時間排序 linked list。

> [!tip]- 三層提示
> 1. Linked list 不適合 random-access quicksort。
> 2. 用快慢指標切半。
> 3. Merge sort 的 merge 可用 $O(1)$ pointer 操作。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在 $O(n\log n)$ 時間排序 linked list。
>
> **核心轉換：** 快慢指標找到中點並切斷；遞迴排序兩半，再 merge。
>
> **主要知識點：** Linked List 指標重接與局部不變量。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Sort List
      │
      ├─ 暴力路線：為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理
      │
      ▼  找出本題最關鍵的轉換
核心觀察：快慢指標找到中點並切斷；遞迴排序兩半，再 merge。
      │
Pattern toolbox：少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap
      │
      ├─ 狀態轉移：先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結
      │
      ├─ 永遠成立：已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在 $O(n\log n)$ 時間排序 linked list。
2. **寫出暴力：** 為了找前驅或搬移節點而從 head 重複掃描，或把資料複製到 array 再處理。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 快慢指標找到中點並切斷；遞迴排序兩半，再 merge。
4. **定義 state 與轉移：** 使用「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」承載上述觀察，再執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(\log n)$ recursion

> [!tip] 一句話記憶
> 先說清楚「少量 pointer：prev/current/next、dummy head，以及必要的 map 或 heap」代表什麼，再說每一步如何「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已處理區段連結正確且可由新 head 到達；未處理區段仍由保存的 pointer 完整可達」的 base case。
>
> 2. **維持：** 每次執行「先保存下一步仍需存取的 pointer，再依固定順序斷開與重接連結」後，狀態仍與已處理資料一致。關鍵論證是：以處理區段長度做 induction，逐步證明無節點遺失、重複或形成非預期 cycle。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空串列、單節點、head/tail 改變、k 不整除、cycle、共享節點與 random pointer。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

快慢指標找到中點並切斷；遞迴排序兩半，再 merge。

```python
def sort_list(head):
    if not head or not head.next:
        return head

    slow, fast = head, head.next
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    right = slow.next
    slow.next = None

    left = sort_list(head)
    right = sort_list(right)

    dummy = ListNode()
    tail = dummy
    while left and right:
        if left.val <= right.val:
            tail.next, left = left, left.next
        else:
            tail.next, right = right, right.next
        tail = tail.next
    tail.next = left or right
    return dummy.next
```

- 時間：$O(n\log n)$
- 空間：$O(\log n)$ recursion

### Follow-up 1：原題直接變形
**問：要求 $O(1)$ 額外空間？**

**答：**使用 bottom-up merge sort。依序合併長度 `1,2,4,...` 的 runs，避免 recursion stack；pointer manipulation 較長，但額外空間為 $O(1)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Sort List》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：快慢指標找到中點並切斷；遞迴排序兩半，再 merge。 失效情境包括：若需要頻繁 random access，linked list 不是合適表示；若節點可能被其他執行緒同時修改，局部重接也不安全。
>
> 替代路線是：可搭配 array index、hash map、skip list、heap 或改變底層容器；排序常用 merge sort 而非 quicksort。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：回傳新 head 並保存每段頭尾；複製題用 old→new map，merge 題可記錄來源 list 與 next pointer。
>
> 套回《Sort List》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Lock-free list 涉及 ABA 與 memory reclamation；一般面試先用 mutex。持久化時要定義 node identity 與序列化。
>
> 此外必須把《Sort List》目前隱含的前提寫成 contract：在 $O(n\log n)$ 時間排序 linked list。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 修改 `next` 前會先保存後繼。
- [ ] 會用 dummy 消除 head 特例。
- [ ] 能維護 doubly linked list 的雙向 invariant。
- [ ] 會在 list 上使用快慢指標與 merge sort。
