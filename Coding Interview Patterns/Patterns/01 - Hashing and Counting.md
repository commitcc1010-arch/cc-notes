---
title: Hashing and Counting
aliases:
  - Hash Map Pattern
tags:
  - coding-interview/pattern
  - hashing
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 01 — Hashing and Counting

[[00 - Book Index|目錄]] · [[02 - Two Pointers|下一章 →]]

> [!abstract] Mental model
> 用額外空間記住「過去看過什麼」或「每種東西出現幾次」，把重複掃描降成平均 $O(1)$ 查找。真正要設計的是 key：值、頻率向量、prefix state、normalized slope，或某個 canonical representation。

## 辨認訊號

- 問是否存在、第一個位置、所有分組或出現次數。
- Brute force 反覆往回找相同或互補元素。
- 順序不重要，identity 或 frequency 才重要。
- 需要把複雜物件正規化後判斷相等。

## 核心 invariant

處理 index `i` 時，hash table 只包含已處理區域的必要摘要；查詢答案時，不需要重新掃描該區域。

---

## 核心題 1：Two Sum

### 題目

給整數陣列 `nums` 與目標 `target`，回傳兩個不同 index，使其值相加為 `target`。假設恰有一組答案。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給整數陣列 nums 與目標 target，回傳兩個不同 index，使其值相加為 target。假設恰有一組答案。
>
> **核心轉換：** 枚舉 nums[i] 時，需要知道 target - nums[i] 是否已出現。用 map 保存 value -> index，先查再放，可避免同一元素使用兩次。
>
> **主要知識點：** Hashing、計數與 canonical representation。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Two Sum
      │
      ├─ 暴力路線：對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題
      │
      ▼  找出本題最關鍵的轉換
核心觀察：枚舉 nums[i] 時，需要知道 target - nums[i] 是否已出現。用 map 保存 value -> index，先查再放，可避免同一元素使用兩次。
      │
Pattern toolbox：hash table：canonical key → 已處理資料的最小充分摘要
      │
      ├─ 狀態轉移：由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要
      │
      ├─ 永遠成立：處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給整數陣列 nums 與目標 target，回傳兩個不同 index，使其值相加為 target。假設恰有一組答案。
2. **寫出暴力：** 對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 枚舉 nums[i] 時，需要知道 target - nums[i] 是否已出現。用 map 保存 value -> index，先查再放，可避免同一元素使用兩次。
4. **定義 state 與轉移：** 使用「hash table：canonical key → 已處理資料的最小充分摘要」承載上述觀察，再執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「hash table：canonical key → 已處理資料的最小充分摘要」代表什麼，再說每一步如何「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key」的 base case。
>
> 2. **維持：** 每次執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」後，狀態仍與已處理資料一致。關鍵論證是：證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

枚舉 `nums[i]` 時，需要知道 `target - nums[i]` 是否已出現。用 map 保存 `value -> index`，先查再放，可避免同一元素使用兩次。

```python
def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        need = target - x
        if need in seen:
            return [seen[need], i]
        seen[x] = i
    return []
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：若要回傳所有不重複的「值配對」，且輸入可能有重複值？**

**答：**用 set 去重答案；遇到互補值時，把較小值放前面形成 canonical pair。

```python
def all_value_pairs(nums, target):
    seen, ans = set(), set()
    for x in nums:
        y = target - x
        if y in seen:
            ans.add((min(x, y), max(x, y)))
        seen.add(x)
    return list(ans)
```

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Two Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：枚舉 nums[i] 時，需要知道 target - nums[i] 是否已出現。用 map 保存 value -> index，先查再放，可避免同一元素使用兩次。 失效情境包括：key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。
>
> 替代路線是：可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。
>
> 套回《Two Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。
>
> 此外必須把《Two Sum》目前隱含的前提寫成 contract：給整數陣列 nums 與目標 target，回傳兩個不同 index，使其值相加為 target。假設恰有一組答案。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Group Anagrams

### 題目

將一組小寫英文字串依 anagram 關係分組。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 將一組小寫英文字串依 anagram 關係分組。
>
> **核心轉換：** Anagram 的字母順序不同，但 26 個字母的出現次數完全相同。頻率 tuple 是穩定且可 hash 的 key。
>
> **主要知識點：** Hashing、計數與 canonical representation。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Group Anagrams
      │
      ├─ 暴力路線：對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Anagram 的字母順序不同，但 26 個字母的出現次數完全相同。頻率 tuple 是穩定且可 hash 的 key。
      │
Pattern toolbox：hash table：canonical key → 已處理資料的最小充分摘要
      │
      ├─ 狀態轉移：由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要
      │
      ├─ 永遠成立：處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 將一組小寫英文字串依 anagram 關係分組。
2. **寫出暴力：** 對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Anagram 的字母順序不同，但 26 個字母的出現次數完全相同。頻率 tuple 是穩定且可 hash 的 key。
4. **定義 state 與轉移：** 使用「hash table：canonical key → 已處理資料的最小充分摘要」承載上述觀察，再執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(C)$，C 是所有字元總數；空間：$O(C)$，包含輸出

> [!tip] 一句話記憶
> 先說清楚「hash table：canonical key → 已處理資料的最小充分摘要」代表什麼，再說每一步如何「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key」的 base case。
>
> 2. **維持：** 每次執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」後，狀態仍與已處理資料一致。關鍵論證是：證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

Anagram 的字母順序不同，但 26 個字母的出現次數完全相同。頻率 tuple 是穩定且可 hash 的 key。

```python
from collections import defaultdict

def group_anagrams(words):
    groups = defaultdict(list)
    for word in words:
        count = [0] * 26
        for ch in word:
            count[ord(ch) - ord("a")] += 1
        groups[tuple(count)].append(word)
    return list(groups.values())
```

- 時間：$O(C)$，`C` 是所有字元總數
- 空間：$O(C)$，包含輸出

### Follow-up 1：原題直接變形
**問：若字元可能是任意 Unicode，不能配置固定大小字母表？**

**答：**用排序後字串作 key，時間變成每個字串 $O(k\log k)$；或把 `Counter` 的項目排序後轉 tuple。

```python
def group_unicode_anagrams(words):
    groups = defaultdict(list)
    for word in words:
        groups["".join(sorted(word))].append(word)
    return list(groups.values())
```

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Group Anagrams》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Anagram 的字母順序不同，但 26 個字母的出現次數完全相同。頻率 tuple 是穩定且可 hash 的 key。 失效情境包括：key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。
>
> 替代路線是：可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。
>
> 套回《Group Anagrams》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。
>
> 此外必須把《Group Anagrams》目前隱含的前提寫成 contract：將一組小寫英文字串依 anagram 關係分組。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Longest Consecutive Sequence

### 題目

在未排序整數陣列中，找出最長連續整數序列的長度，要求期望 $O(n)$。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在未排序整數陣列中，找出最長連續整數序列的長度，要求期望 $O(n)$。
>
> **核心轉換：** 只有當 x - 1 不存在時，x 才可能是序列起點。每個數最多被某個起點向右走訪一次。
>
> **主要知識點：** Hashing、計數與 canonical representation。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Longest Consecutive Sequence
      │
      ├─ 暴力路線：對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題
      │
      ▼  找出本題最關鍵的轉換
核心觀察：只有當 x - 1 不存在時，x 才可能是序列起點。每個數最多被某個起點向右走訪一次。
      │
Pattern toolbox：hash table：canonical key → 已處理資料的最小充分摘要
      │
      ├─ 狀態轉移：由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要
      │
      ├─ 永遠成立：處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在未排序整數陣列中，找出最長連續整數序列的長度，要求期望 $O(n)$。
2. **寫出暴力：** 對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 只有當 x - 1 不存在時，x 才可能是序列起點。每個數最多被某個起點向右走訪一次。
4. **定義 state 與轉移：** 使用「hash table：canonical key → 已處理資料的最小充分摘要」承載上述觀察，再執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：期望 $O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「hash table：canonical key → 已處理資料的最小充分摘要」代表什麼，再說每一步如何「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key」的 base case。
>
> 2. **維持：** 每次執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」後，狀態仍與已處理資料一致。關鍵論證是：證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

只有當 `x - 1` 不存在時，`x` 才可能是序列起點。每個數最多被某個起點向右走訪一次。

```python
def longest_consecutive(nums):
    values = set(nums)
    best = 0
    for x in values:
        if x - 1 not in values:
            y = x
            while y in values:
                y += 1
            best = max(best, y - x)
    return best
```

- 時間：期望 $O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：除了長度，也要回傳實際序列？**

**答：**記錄最佳起點與長度，最後建立 range。

```python
def longest_consecutive_values(nums):
    values = set(nums)
    best_start = best_len = 0
    for x in values:
        if x - 1 not in values:
            y = x
            while y in values:
                y += 1
            if y - x > best_len:
                best_start, best_len = x, y - x
    return list(range(best_start, best_start + best_len))
```

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Longest Consecutive Sequence》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：只有當 x - 1 不存在時，x 才可能是序列起點。每個數最多被某個起點向右走訪一次。 失效情境包括：key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。
>
> 替代路線是：可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。
>
> 套回《Longest Consecutive Sequence》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。
>
> 此外必須把《Longest Consecutive Sequence》目前隱含的前提寫成 contract：在未排序整數陣列中，找出最長連續整數序列的長度，要求期望 $O(n)$。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Longest Duplicate Substring

### 題目

找出字串中最長、至少出現兩次的 substring；重疊也算。

> [!tip]- 三層提示
> 1. 若長度 `L` 的重複 substring 存在，更短長度也一定存在。
> 2. 對答案長度 binary search。
> 3. 用 rolling hash 在 $O(n)$ 檢查某個長度是否重複。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 找出字串中最長、至少出現兩次的 substring；重疊也算。
>
> **核心轉換：** 「是否存在長度至少 L 的重複 substring」具有單調性，因此 binary search L。固定 L 後，以 rolling hash 滑過所有 substring，把 hash pair 放進 set。使用兩個 modulus 降低 collision 風險。
>
> **主要知識點：** Hashing、計數與 canonical representation。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Longest Duplicate Substring
      │
      ├─ 暴力路線：對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題
      │
      ▼  找出本題最關鍵的轉換
核心觀察：「是否存在長度至少 L 的重複 substring」具有單調性，因此 binary search L。固定 L 後，以 rolling hash 滑過所有 substring，把 hash pair 放進 set。使用兩個 modulus 降低 collision 風險。
      │
Pattern toolbox：hash table：canonical key → 已處理資料的最小充分摘要
      │
      ├─ 狀態轉移：由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要
      │
      ├─ 永遠成立：處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 找出字串中最長、至少出現兩次的 substring；重疊也算。
2. **寫出暴力：** 對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 「是否存在長度至少 L 的重複 substring」具有單調性，因此 binary search L。固定 L 後，以 rolling hash 滑過所有 substring，把 hash pair 放進 set。使用兩個 modulus 降低 collision 風險。
4. **定義 state 與轉移：** 使用「hash table：canonical key → 已處理資料的最小充分摘要」承載上述觀察，再執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「hash table：canonical key → 已處理資料的最小充分摘要」代表什麼，再說每一步如何「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key」的 base case。
>
> 2. **維持：** 每次執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」後，狀態仍與已處理資料一致。關鍵論證是：證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

「是否存在長度至少 `L` 的重複 substring」具有單調性，因此 binary search `L`。固定 `L` 後，以 rolling hash 滑過所有 substring，把 hash pair 放進 set。使用兩個 modulus 降低 collision 風險。

```python
def longest_duplicate_substring(s):
    nums = [ord(c) for c in s]
    n = len(s)
    base = 911382323
    mod1, mod2 = 1_000_000_007, 1_000_000_009

    def duplicate_start(length):
        if length == 0:
            return 0
        p1 = pow(base, length, mod1)
        p2 = pow(base, length, mod2)
        h1 = h2 = 0
        seen = set()
        for i, x in enumerate(nums):
            h1 = (h1 * base + x) % mod1
            h2 = (h2 * base + x) % mod2
            if i >= length:
                h1 = (h1 - nums[i - length] * p1) % mod1
                h2 = (h2 - nums[i - length] * p2) % mod2
            if i >= length - 1:
                key = (h1, h2)
                if key in seen:
                    return i - length + 1
                seen.add(key)
        return -1

    lo, hi = 0, n
    best_start = best_len = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        start = duplicate_start(mid)
        if start != -1:
            best_start, best_len = start, mid
            lo = mid + 1
        else:
            hi = mid - 1
    return s[best_start:best_start + best_len]
```

**正確性：**若檢查長度 `L` 成功，代表至少兩個 substring 有相同雙 hash；在忽略極低 collision 機率下即為相同內容。可行長度形成 `[0, answer]`，binary search 因而找到最大可行值。

- 時間：$O(n\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：要求 deterministic、完全不能接受 hash collision？**

**答：**改用 suffix array 搭配 LCP。排序所有 suffix 後，任何重複 substring 都會出現在相鄰 suffix 的共同 prefix；最大 LCP 即答案。典型複雜度為 $O(n\log n)$ 或更佳。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Longest Duplicate Substring》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：「是否存在長度至少 L 的重複 substring」具有單調性，因此 binary search L。固定 L 後，以 rolling hash 滑過所有 substring，把 hash pair 放進 set。使用兩個 modulus 降低 collision 風險。 失效情境包括：key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。
>
> 替代路線是：可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。
>
> 套回《Longest Duplicate Substring》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。
>
> 此外必須把《Longest Duplicate Substring》目前隱含的前提寫成 contract：找出字串中最長、至少出現兩次的 substring；重疊也算。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：First Missing Positive

### 題目

在未排序陣列中找最小缺失正整數，要求 $O(n)$ 時間、$O(1)$ 額外空間。

> [!tip]- 三層提示
> 1. 長度為 `n` 時，答案只可能在 `[1, n + 1]`。
> 2. 把陣列本身當 hash table。
> 3. 值 `x` 應被交換到 index `x - 1`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在未排序陣列中找最小缺失正整數，要求 $O(n)$ 時間、$O(1)$ 額外空間。
>
> **核心轉換：** 不斷把合法值 x 放到 nums[x - 1]。交換後同一 index 可能拿到新的合法值，所以用 while。重複值必須停止，否則會無限交換。
>
> **主要知識點：** Hashing、計數與 canonical representation。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：First Missing Positive
      │
      ├─ 暴力路線：對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題
      │
      ▼  找出本題最關鍵的轉換
核心觀察：不斷把合法值 x 放到 nums[x - 1]。交換後同一 index 可能拿到新的合法值，所以用 while。重複值必須停止，否則會無限交換。
      │
Pattern toolbox：hash table：canonical key → 已處理資料的最小充分摘要
      │
      ├─ 狀態轉移：由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要
      │
      ├─ 永遠成立：處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在未排序陣列中找最小缺失正整數，要求 $O(n)$ 時間、$O(1)$ 額外空間。
2. **寫出暴力：** 對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 不斷把合法值 x 放到 nums[x - 1]。交換後同一 index 可能拿到新的合法值，所以用 while。重複值必須停止，否則會無限交換。
4. **定義 state 與轉移：** 使用「hash table：canonical key → 已處理資料的最小充分摘要」承載上述觀察，再執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；每次交換至少把一個值放到最終位置；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「hash table：canonical key → 已處理資料的最小充分摘要」代表什麼，再說每一步如何「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key」的 base case。
>
> 2. **維持：** 每次執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」後，狀態仍與已處理資料一致。關鍵論證是：證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

不斷把合法值 `x` 放到 `nums[x - 1]`。交換後同一 index 可能拿到新的合法值，所以用 `while`。重複值必須停止，否則會無限交換。

```python
def first_missing_positive(nums):
    n = len(nums)
    for i in range(n):
        while (
            1 <= nums[i] <= n
            and nums[nums[i] - 1] != nums[i]
        ):
            target = nums[i] - 1
            nums[i], nums[target] = nums[target], nums[i]

    for i, x in enumerate(nums):
        if x != i + 1:
            return i + 1
    return n + 1
```

**正確性：**整理完成後，只要值 `x` 存在，index `x-1` 必為 `x`。第一個不符合的位置 `i` 表示 `i+1` 不存在；若全部符合，`1..n` 都存在，答案為 `n+1`。

- 時間：$O(n)$；每次交換至少把一個值放到最終位置
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：輸入不可修改，還能同時維持 $O(n)$ 時間與 $O(1)$ 空間嗎？**

**答：**一般情況無法使用上述 index hashing；可用 set 得到 $O(n)$ 時間、$O(n)$ 空間，或排序副本得到 $O(n\log n)$ 時間。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《First Missing Positive》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：不斷把合法值 x 放到 nums[x - 1]。交換後同一 index 可能拿到新的合法值，所以用 while。重複值必須停止，否則會無限交換。 失效情境包括：key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。
>
> 替代路線是：可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。
>
> 套回《First Missing Positive》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。
>
> 此外必須把《First Missing Positive》目前隱含的前提寫成 contract：在未排序陣列中找最小缺失正整數，要求 $O(n)$ 時間、$O(1)$ 額外空間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Max Points on a Line

### 題目

給平面座標點，找同一直線上的最多點數。

> [!tip]- 三層提示
> 1. 固定一個 anchor，其他點依 slope 分組。
> 2. 不要使用浮點 slope。
> 3. 用 `gcd(dx, dy)` 約分並統一正負號。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給平面座標點，找同一直線上的最多點數。
>
> **核心轉換：** 對每個 anchor 建立 normalized slope -> count。垂直線與水平線也會被統一正規化。若座標可重複，額外計算 duplicate。
>
> **主要知識點：** Hashing、計數與 canonical representation。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Max Points on a Line
      │
      ├─ 暴力路線：對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題
      │
      ▼  找出本題最關鍵的轉換
核心觀察：對每個 anchor 建立 normalized slope -> count。垂直線與水平線也會被統一正規化。若座標可重複，額外計算 duplicate。
      │
Pattern toolbox：hash table：canonical key → 已處理資料的最小充分摘要
      │
      ├─ 狀態轉移：由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要
      │
      ├─ 永遠成立：處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給平面座標點，找同一直線上的最多點數。
2. **寫出暴力：** 對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 對每個 anchor 建立 normalized slope -> count。垂直線與水平線也會被統一正規化。若座標可重複，額外計算 duplicate。
4. **定義 state 與轉移：** 使用「hash table：canonical key → 已處理資料的最小充分摘要」承載上述觀察，再執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n^2)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「hash table：canonical key → 已處理資料的最小充分摘要」代表什麼，再說每一步如何「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key」的 base case。
>
> 2. **維持：** 每次執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」後，狀態仍與已處理資料一致。關鍵論證是：證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

對每個 anchor 建立 `normalized slope -> count`。垂直線與水平線也會被統一正規化。若座標可重複，額外計算 duplicate。

```python
from collections import defaultdict
from math import gcd

def max_points(points):
    if len(points) <= 2:
        return len(points)
    answer = 0
    for i, (x1, y1) in enumerate(points):
        slopes = defaultdict(int)
        duplicates = 1
        local = 0
        for j in range(i + 1, len(points)):
            x2, y2 = points[j]
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0:
                duplicates += 1
                continue
            g = gcd(abs(dx), abs(dy))
            dx //= g
            dy //= g
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            slope = (dy, dx)
            slopes[slope] += 1
            local = max(local, slopes[slope])
        answer = max(answer, local + duplicates)
    return answer
```

- 時間：$O(n^2)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：還要回傳直線方程式？**

**答：**保存最佳 anchor 與 slope `(dy, dx)`，再把直線轉成 normalized `Ax + By + C = 0`，其中 `A=dy`、`B=-dx`、`C=-(A*x+B*y)`，最後再以 gcd 與符號正規化。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Max Points on a Line》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：對每個 anchor 建立 normalized slope -> count。垂直線與水平線也會被統一正規化。若座標可重複，額外計算 duplicate。 失效情境包括：key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。
>
> 替代路線是：可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。
>
> 套回《Max Points on a Line》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。
>
> 此外必須把《Max Points on a Line》目前隱含的前提寫成 contract：給平面座標點，找同一直線上的最多點數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Palindrome Pairs

### 題目

給互不相同的字串，找所有 `(i, j)`，使 `words[i] + words[j]` 是 palindrome。

> [!tip]- 三層提示
> 1. 對每個字串枚舉切點。
> 2. 若左半已是 palindrome，右半需要什麼字串放在前面？
> 3. 用 `word -> index` map 查反轉字串。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給互不相同的字串，找所有 (i, j)，使 words[i] + words[j] 是 palindrome。
>
> **核心轉換：** 把字串切成 left + right：
>
> **主要知識點：** Hashing、計數與 canonical representation。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Palindrome Pairs
      │
      ├─ 暴力路線：對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題
      │
      ▼  找出本題最關鍵的轉換
核心觀察：把字串切成 left + right：
      │
Pattern toolbox：hash table：canonical key → 已處理資料的最小充分摘要
      │
      ├─ 狀態轉移：由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要
      │
      ├─ 永遠成立：處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給互不相同的字串，找所有 (i, j)，使 words[i] + words[j] 是 palindrome。
2. **寫出暴力：** 對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 把字串切成 left + right：
4. **定義 state 與轉移：** 使用「hash table：canonical key → 已處理資料的最小充分摘要」承載上述觀察，再執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(nk^2)$，k 為最大字串長度；空間：$O(nk)$

> [!tip] 一句話記憶
> 先說清楚「hash table：canonical key → 已處理資料的最小充分摘要」代表什麼，再說每一步如何「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key」的 base case。
>
> 2. **維持：** 每次執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」後，狀態仍與已處理資料一致。關鍵論證是：證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

把字串切成 `left + right`：

- 若 `left` 是 palindrome，前面接 `reverse(right)` 即可。
- 若 `right` 是 palindrome，後面接 `reverse(left)` 即可。
- 第二種在切點位於結尾時跳過，避免同一 pair 重複加入。

```python
def palindrome_pairs(words):
    index = {word: i for i, word in enumerate(words)}
    answer = []

    def is_palindrome(text):
        return text == text[::-1]

    for i, word in enumerate(words):
        for cut in range(len(word) + 1):
            left, right = word[:cut], word[cut:]

            if is_palindrome(left):
                j = index.get(right[::-1])
                if j is not None and j != i:
                    answer.append([j, i])

            if cut != len(word) and is_palindrome(right):
                j = index.get(left[::-1])
                if j is not None and j != i:
                    answer.append([i, j])
    return answer
```

- 時間：$O(nk^2)$，`k` 為最大字串長度
- 空間：$O(nk)$

### Follow-up 1：原題直接變形
**問：如何改善大量長字串時的 palindrome 判斷？**

**答：**可預先用 rolling hash 建立正向與反向 hash，使任意 substring 的 palindrome 判斷接近 $O(1)$；或使用 trie，在插入反轉字串時記錄剩餘 prefix 是否為 palindrome。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Palindrome Pairs》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：把字串切成 left + right： 失效情境包括：key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。
>
> 替代路線是：可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。
>
> 套回《Palindrome Pairs》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。
>
> 此外必須把《Palindrome Pairs》目前隱含的前提寫成 contract：給互不相同的字串，找所有 (i, j)，使 words[i] + words[j] 是 palindrome。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：All O`one Data Structure

### 題目

設計資料結構支援：

- `inc(key)`：計數加一。
- `dec(key)`：計數減一，變零時刪除。
- `getMaxKey()` / `getMinKey()`：回傳任一最大／最小計數 key。

所有操作皆要求平均 $O(1)$。

> [!tip]- 三層提示
> 1. 單靠 `key -> count` 無法 $O(1)$ 找 min/max。
> 2. 建立「相同 count 的 bucket」。
> 3. bucket 依 count 組成 doubly linked list，key 再指向 bucket。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 設計資料結構支援：
>
> **核心轉換：** 鏈結串列中的每個 bucket 保存某個 count 的所有 keys。增加或減少 key 時，它只會移到相鄰 count；若相鄰 bucket 不存在就建立。空 bucket 立即刪除。head 後第一個 bucket 是最小值，tail 前最後一個是最大值。
>
> **主要知識點：** Hashing、計數與 canonical representation。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：All O`one Data Structure
      │
      ├─ 暴力路線：對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題
      │
      ▼  找出本題最關鍵的轉換
核心觀察：鏈結串列中的每個 bucket 保存某個 count 的所有 keys。增加或減少 key 時，它只會移到相鄰 count；若相鄰 bucket 不存在就建立。空 bucket 立即刪除。head 後第一個 bucket 是最小值，tail 前最後一個是最大值。
      │
Pattern toolbox：hash table：canonical key → 已處理資料的最小充分摘要
      │
      ├─ 狀態轉移：由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要
      │
      ├─ 永遠成立：處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 設計資料結構支援：
2. **寫出暴力：** 對每個候選重新掃描其餘資料，反覆回答相同的「是否看過／出現幾次」問題。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 鏈結串列中的每個 bucket 保存某個 count 的所有 keys。增加或減少 key 時，它只會移到相鄰 count；若相鄰 bucket 不存在就建立。空 bucket 立即刪除。head 後第一個 bucket 是最小值，tail 前最後一個是最大值。
4. **定義 state 與轉移：** 使用「hash table：canonical key → 已處理資料的最小充分摘要」承載上述觀察，再執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：每個操作：平均 $O(1)$；空間：$O(K)$，K 為 key 數

> [!tip] 一句話記憶
> 先說清楚「hash table：canonical key → 已處理資料的最小充分摘要」代表什麼，再說每一步如何「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「處理位置 i 前，表中只含已處理 prefix，且同一語意物件一定映射到同一 key」的 base case。
>
> 2. **維持：** 每次執行「由目前元素建立 key；先用舊狀態查答案，再依題意更新摘要」後，狀態仍與已處理資料一致。關鍵論證是：證明 key 不會把不同狀態錯誤合併，也不會把相同狀態拆開；再證明查詢發生時，所有合法前驅都已進表。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、負數、空輸入、同一元素不可重用、hash collision，以及 key 是否真的 immutable。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

鏈結串列中的每個 bucket 保存某個 count 的所有 keys。增加或減少 key 時，它只會移到相鄰 count；若相鄰 bucket 不存在就建立。空 bucket 立即刪除。head 後第一個 bucket 是最小值，tail 前最後一個是最大值。

```python
class Bucket:
    def __init__(self, count=0):
        self.count = count
        self.keys = set()
        self.prev = self.next = None


class AllOne:
    def __init__(self):
        self.head = Bucket()
        self.tail = Bucket()
        self.head.next = self.tail
        self.tail.prev = self.head
        self.where = {}

    def _insert_after(self, node, new_node):
        new_node.prev = node
        new_node.next = node.next
        node.next.prev = new_node
        node.next = new_node

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def inc(self, key):
        if key not in self.where:
            first = self.head.next
            if first is self.tail or first.count != 1:
                first = Bucket(1)
                self._insert_after(self.head, first)
            first.keys.add(key)
            self.where[key] = first
            return

        current = self.where[key]
        target = current.next
        if target is self.tail or target.count != current.count + 1:
            target = Bucket(current.count + 1)
            self._insert_after(current, target)
        current.keys.remove(key)
        target.keys.add(key)
        self.where[key] = target
        if not current.keys:
            self._remove(current)

    def dec(self, key):
        current = self.where[key]
        current.keys.remove(key)
        if current.count == 1:
            del self.where[key]
        else:
            target = current.prev
            if target is self.head or target.count != current.count - 1:
                target = Bucket(current.count - 1)
                self._insert_after(current.prev, target)
            target.keys.add(key)
            self.where[key] = target
        if not current.keys:
            self._remove(current)

    def getMaxKey(self):
        if self.tail.prev is self.head:
            return ""
        return next(iter(self.tail.prev.keys))

    def getMinKey(self):
        if self.head.next is self.tail:
            return ""
        return next(iter(self.head.next.keys))
```

**正確性：**bucket list 始終嚴格依 count 排序，且每個 key 恰存在於其目前 count 的 bucket。每次更新只移動到相鄰 count，因此最多插入／移除常數個節點。

- 每個操作：平均 $O(1)$
- 空間：$O(K)$，`K` 為 key 數

### Follow-up 1：原題直接變形
**問：要回傳 top `k` 個 keys？**

**答：**從 tail 往前走 bucket，逐一輸出 keys，直到收集 `k` 個。時間為 $O(B + k)$，其中 `B` 是走訪到的 bucket 數；若要求任意 `k` 下都嚴格 $O(k)$，需對 bucket 內部與跨 bucket iteration 再定義更強的順序結構。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《All O`one Data Structure》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：鏈結串列中的每個 bucket 保存某個 count 的所有 keys。增加或減少 key 時，它只會移到相鄰 count；若相鄰 bucket 不存在就建立。空 bucket 立即刪除。head 後第一個 bucket 是最小值，tail 前最後一個是最大值。 失效情境包括：key 無法穩定正規化、碰撞必須完全排除，或 distinct keys 多到記憶體放不下時，單機 hash 解法會失去保證。
>
> 替代路線是：可改用排序後掃描、Trie／suffix structure、外部排序或分桶；若需 deterministic worst case，使用 balanced tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：在 value 中額外保存 index、代表元素、parent 或最佳前驅；更新答案時同步保存來源，即可重建實際配對、群組或序列。
>
> 套回《All O`one Data Structure》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上系統要定義 key 的序列化、hash flooding 防護、容量與淘汰策略；併發更新需讓「查詢＋寫入」保持原子性。
>
> 此外必須把《All O`one Data Structure》目前隱含的前提寫成 contract：設計資料結構支援：。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 能說明 key 如何 canonicalize。
- [ ] 知道何時 `Counter` 不夠，必須保存 index 或結構。
- [ ] 能辨認 index hashing。
- [ ] 能解釋 hash collision 與 deterministic 替代方案。
