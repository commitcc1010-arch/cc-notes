---
title: Two Pointers
tags:
  - coding-interview/pattern
  - two-pointers
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 02 — Two Pointers

[[01 - Hashing and Counting|← 上一章]] · [[00 - Book Index|目錄]] · [[03 - Sliding Window|下一章 →]]

> [!abstract] Mental model
> 兩個 pointer 不是「用了兩個 index」就算 pattern；關鍵是能根據某個單調關係，安全地排除一整批不可能答案。

## 常見形態

- 左右向中間逼近。
- 同方向快慢指標。
- sorted array 上一大一小調整。
- 讀寫指標做 in-place compaction。
- linked list cycle 上的 tortoise and hare。

---

## 核心題 1：Valid Palindrome

### 題目

忽略非英數字元與大小寫，判斷字串是否為 palindrome。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 忽略非英數字元與大小寫，判斷字串是否為 palindrome。
>
> **核心轉換：** 左右指標只停在有效字元；每次比較後同步向內移動，任何不相等都可立即判 False。
>
> **主要知識點：** Two Pointers 與單調淘汰。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Valid Palindrome
      │
      ├─ 暴力路線：枚舉所有 index pair 或每次移動一端後重新掃描另一端
      │
      ▼  找出本題最關鍵的轉換
核心觀察：左右指標只停在有效字元；每次比較後同步向內移動，任何不相等都可立即判 False。
      │
Pattern toolbox：兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區
      │
      ├─ 狀態轉移：依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選
      │
      ├─ 永遠成立：指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 忽略非英數字元與大小寫，判斷字串是否為 palindrome。
2. **寫出暴力：** 枚舉所有 index pair 或每次移動一端後重新掃描另一端。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 左右指標只停在有效字元；每次比較後同步向內移動，任何不相等都可立即判 False。
4. **定義 state 與轉移：** 使用「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」承載上述觀察，再執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」代表什麼，再說每一步如何「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案」的 base case。
>
> 2. **維持：** 每次執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」後，狀態仍與已處理資料一致。關鍵論證是：每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def is_palindrome(s):
    left, right = 0, len(s) - 1
    while left < right:
        while left < right and not s[left].isalnum():
            left += 1
        while left < right and not s[right].isalnum():
            right -= 1
        if s[left].lower() != s[right].lower():
            return False
        left += 1
        right -= 1
    return True
```

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：最多允許刪除一個字元？**

**答：**第一次 mismatch 時，只需嘗試跳過左邊或右邊其中一個。

```python
def valid_palindrome_one_delete(s):
    def check(left, right):
        while left < right:
            if s[left] != s[right]:
                return False
            left += 1
            right -= 1
        return True

    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return check(left + 1, right) or check(left, right - 1)
        left += 1
        right -= 1
    return True
```

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Valid Palindrome》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：左右指標只停在有效字元；每次比較後同步向內移動，任何不相等都可立即判 False。 失效情境包括：若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。
>
> 替代路線是：可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。
>
> 套回《Valid Palindrome》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。
>
> 此外必須把《Valid Palindrome》目前隱含的前提寫成 contract：忽略非英數字元與大小寫，判斷字串是否為 palindrome。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：3Sum

### 題目

找出所有不重複的三元組，使三數和為零。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 找出所有不重複的三元組，使三數和為零。
>
> **核心轉換：** 排序後固定第一個值，剩下兩數用左右 pointer。總和太小只能增加左值；太大只能減少右值。排序也讓去重變得局部。
>
> **主要知識點：** Two Pointers 與單調淘汰。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：3Sum
      │
      ├─ 暴力路線：枚舉所有 index pair 或每次移動一端後重新掃描另一端
      │
      ▼  找出本題最關鍵的轉換
核心觀察：排序後固定第一個值，剩下兩數用左右 pointer。總和太小只能增加左值；太大只能減少右值。排序也讓去重變得局部。
      │
Pattern toolbox：兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區
      │
      ├─ 狀態轉移：依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選
      │
      ├─ 永遠成立：指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 找出所有不重複的三元組，使三數和為零。
2. **寫出暴力：** 枚舉所有 index pair 或每次移動一端後重新掃描另一端。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 排序後固定第一個值，剩下兩數用左右 pointer。總和太小只能增加左值；太大只能減少右值。排序也讓去重變得局部。
4. **定義 state 與轉移：** 使用「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」承載上述觀察，再執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n^2)$；空間：排序額外空間依實作而定

> [!tip] 一句話記憶
> 先說清楚「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」代表什麼，再說每一步如何「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案」的 base case。
>
> 2. **維持：** 每次執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」後，狀態仍與已處理資料一致。關鍵論證是：每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

排序後固定第一個值，剩下兩數用左右 pointer。總和太小只能增加左值；太大只能減少右值。排序也讓去重變得局部。

```python
def three_sum(nums):
    nums.sort()
    answer = []
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        if nums[i] > 0:
            break
        left, right = i + 1, len(nums) - 1
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                answer.append([nums[i], nums[left], nums[right]])
                left += 1
                right -= 1
                while left < right and nums[left] == nums[left - 1]:
                    left += 1
                while left < right and nums[right] == nums[right + 1]:
                    right -= 1
    return answer
```

- 時間：$O(n^2)$
- 空間：排序額外空間依實作而定

### Follow-up 1：原題直接變形
**問：改成任意 `k` 個數總和為 target？**

**答：**遞迴固定一個數，把 `k-Sum` 降為 `(k-1)-Sum`；`k == 2` 時使用 two pointers。詳見本章 4Sum。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《3Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：排序後固定第一個值，剩下兩數用左右 pointer。總和太小只能增加左值；太大只能減少右值。排序也讓去重變得局部。 失效情境包括：若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。
>
> 替代路線是：可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。
>
> 套回《3Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。
>
> 此外必須把《3Sum》目前隱含的前提寫成 contract：找出所有不重複的三元組，使三數和為零。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Container With Most Water

### 題目

陣列代表每個位置的高度，選兩條線，使其與 x 軸形成的容器面積最大。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 陣列代表每個位置的高度，選兩條線，使其與 x 軸形成的容器面積最大。
>
> **核心轉換：** 面積由較短線限制。若移動較高線，寬度下降而短板不變，面積不可能增加；因此每次安全地丟棄較短的一端。
>
> **主要知識點：** Two Pointers 與單調淘汰。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Container With Most Water
      │
      ├─ 暴力路線：枚舉所有 index pair 或每次移動一端後重新掃描另一端
      │
      ▼  找出本題最關鍵的轉換
核心觀察：面積由較短線限制。若移動較高線，寬度下降而短板不變，面積不可能增加；因此每次安全地丟棄較短的一端。
      │
Pattern toolbox：兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區
      │
      ├─ 狀態轉移：依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選
      │
      ├─ 永遠成立：指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 陣列代表每個位置的高度，選兩條線，使其與 x 軸形成的容器面積最大。
2. **寫出暴力：** 枚舉所有 index pair 或每次移動一端後重新掃描另一端。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 面積由較短線限制。若移動較高線，寬度下降而短板不變，面積不可能增加；因此每次安全地丟棄較短的一端。
4. **定義 state 與轉移：** 使用「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」承載上述觀察，再執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」代表什麼，再說每一步如何「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案」的 base case。
>
> 2. **維持：** 每次執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」後，狀態仍與已處理資料一致。關鍵論證是：每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

面積由較短線限制。若移動較高線，寬度下降而短板不變，面積不可能增加；因此每次安全地丟棄較短的一端。

```python
def max_area(height):
    left, right = 0, len(height) - 1
    best = 0
    while left < right:
        best = max(best, (right - left) * min(height[left], height[right]))
        if height[left] <= height[right]:
            left += 1
        else:
            right -= 1
    return best
```

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：為什麼兩端等高時移動任一端都安全？**

**答：**目前高度為 `h`。保留其中一端並縮小寬度後，另一端高度即使更高，短板最多仍是 `h`，所以不可能得到更大面積；至少可安全排除其中一端。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Container With Most Water》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：面積由較短線限制。若移動較高線，寬度下降而短板不變，面積不可能增加；因此每次安全地丟棄較短的一端。 失效情境包括：若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。
>
> 替代路線是：可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。
>
> 套回《Container With Most Water》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。
>
> 此外必須把《Container With Most Water》目前隱含的前提寫成 contract：陣列代表每個位置的高度，選兩條線，使其與 x 軸形成的容器面積最大。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Trapping Rain Water

### 題目

給非負高度陣列，計算下雨後可儲存的總水量。

> [!tip]- 三層提示
> 1. index `i` 的水位由左右最高牆的較小值決定。
> 2. 不必真的預存兩個 prefix max 陣列。
> 3. 較小的一側已可確定最終水位。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給非負高度陣列，計算下雨後可儲存的總水量。
>
> **核心轉換：** 維護 leftmax 與 rightmax。若 leftmax <= rightmax，左側目前位置的右邊至少存在 rightmax 這面牆，因此左側水量只由 leftmax 決定；反之處理右側。
>
> **主要知識點：** Two Pointers 與單調淘汰。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Trapping Rain Water
      │
      ├─ 暴力路線：枚舉所有 index pair 或每次移動一端後重新掃描另一端
      │
      ▼  找出本題最關鍵的轉換
核心觀察：維護 leftmax 與 rightmax。若 leftmax <= rightmax，左側目前位置的右邊至少存在 rightmax 這面牆，因此左側水量只由 leftmax 決定；反之處理右側。
      │
Pattern toolbox：兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區
      │
      ├─ 狀態轉移：依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選
      │
      ├─ 永遠成立：指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給非負高度陣列，計算下雨後可儲存的總水量。
2. **寫出暴力：** 枚舉所有 index pair 或每次移動一端後重新掃描另一端。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 維護 leftmax 與 rightmax。若 leftmax <= rightmax，左側目前位置的右邊至少存在 rightmax 這面牆，因此左側水量只由 leftmax 決定；反之處理右側。
4. **定義 state 與轉移：** 使用「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」承載上述觀察，再執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」代表什麼，再說每一步如何「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案」的 base case。
>
> 2. **維持：** 每次執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」後，狀態仍與已處理資料一致。關鍵論證是：每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

維護 `left_max` 與 `right_max`。若 `left_max <= right_max`，左側目前位置的右邊至少存在 `right_max` 這面牆，因此左側水量只由 `left_max` 決定；反之處理右側。

```python
def trap(height):
    left, right = 0, len(height) - 1
    left_max = right_max = 0
    water = 0
    while left <= right:
        if left_max <= right_max:
            left_max = max(left_max, height[left])
            water += left_max - height[left]
            left += 1
        else:
            right_max = max(right_max, height[right])
            water += right_max - height[right]
            right -= 1
    return water
```

**正確性：**處理較低 max 的一側時，另一側已提供不低於它的邊界；未來再高的牆不會改變該位置由較低邊界決定的水位。

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：若要回傳每個位置儲存多少水？**

**答：**可建立 `water[i]`，在 pointer 被處理時記錄 `max(0, side_max - height[i])`；總空間變成 $O(n)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Trapping Rain Water》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：維護 leftmax 與 rightmax。若 leftmax <= rightmax，左側目前位置的右邊至少存在 rightmax 這面牆，因此左側水量只由 leftmax 決定；反之處理右側。 失效情境包括：若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。
>
> 替代路線是：可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。
>
> 套回《Trapping Rain Water》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。
>
> 此外必須把《Trapping Rain Water》目前隱含的前提寫成 contract：給非負高度陣列，計算下雨後可儲存的總水量。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：4Sum 與通用 k-Sum

### 題目

找所有不重複四元組，使其總和為 target。

> [!tip]- 三層提示
> 1. 先排序。
> 2. 固定一個數後，問題降成 3Sum。
> 3. 寫通用遞迴，base case 是 2Sum。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 找所有不重複四元組，使其總和為 target。
>
> **核心轉換：** 排序後可去重，也能用最小／最大可能總和 pruning。每層固定一個值，最後用 two pointers 解 2Sum。
>
> **主要知識點：** Two Pointers 與單調淘汰。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：4Sum 與通用 k-Sum
      │
      ├─ 暴力路線：枚舉所有 index pair 或每次移動一端後重新掃描另一端
      │
      ▼  找出本題最關鍵的轉換
核心觀察：排序後可去重，也能用最小／最大可能總和 pruning。每層固定一個值，最後用 two pointers 解 2Sum。
      │
Pattern toolbox：兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區
      │
      ├─ 狀態轉移：依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選
      │
      ├─ 永遠成立：指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 找所有不重複四元組，使其總和為 target。
2. **寫出暴力：** 枚舉所有 index pair 或每次移動一端後重新掃描另一端。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 排序後可去重，也能用最小／最大可能總和 pruning。每層固定一個值，最後用 two pointers 解 2Sum。
4. **定義 state 與轉移：** 使用「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」承載上述觀察，再執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：一般為 $O(n^{k-1})$；4Sum 為 $O(n^3)$；空間：遞迴深度 $O(k)$，不含輸出

> [!tip] 一句話記憶
> 先說清楚「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」代表什麼，再說每一步如何「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案」的 base case。
>
> 2. **維持：** 每次執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」後，狀態仍與已處理資料一致。關鍵論證是：每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

排序後可去重，也能用最小／最大可能總和 pruning。每層固定一個值，最後用 two pointers 解 2Sum。

```python
def four_sum(nums, target):
    nums.sort()

    def k_sum(start, k, goal):
        answer = []
        if len(nums) - start < k:
            return answer
        if nums[start] * k > goal or nums[-1] * k < goal:
            return answer

        if k == 2:
            left, right = start, len(nums) - 1
            while left < right:
                total = nums[left] + nums[right]
                if total < goal:
                    left += 1
                elif total > goal:
                    right -= 1
                else:
                    answer.append([nums[left], nums[right]])
                    left += 1
                    right -= 1
                    while left < right and nums[left] == nums[left - 1]:
                        left += 1
                    while left < right and nums[right] == nums[right + 1]:
                        right -= 1
            return answer

        for i in range(start, len(nums) - k + 1):
            if i > start and nums[i] == nums[i - 1]:
                continue
            for tail in k_sum(i + 1, k - 1, goal - nums[i]):
                answer.append([nums[i]] + tail)
        return answer

    return k_sum(0, 4, target)
```

- 時間：一般為 $O(n^{k-1})$；4Sum 為 $O(n^3)$
- 空間：遞迴深度 $O(k)$，不含輸出

### Follow-up 1：原題直接變形
**問：只需要計算有多少 index 組合，不要求去重值？**

**答：**若 `k=4`，可將前兩數和與後兩數和存入 map，以 meet-in-the-middle 在 $O(n^2)$ 時間與空間計數；要小心四個 index 不可重複。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《4Sum 與通用 k-Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：排序後可去重，也能用最小／最大可能總和 pruning。每層固定一個值，最後用 two pointers 解 2Sum。 失效情境包括：若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。
>
> 替代路線是：可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。
>
> 套回《4Sum 與通用 k-Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。
>
> 此外必須把《4Sum 與通用 k-Sum》目前隱含的前提寫成 contract：找所有不重複四元組，使其總和為 target。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Find the Duplicate Number

### 題目

長度 `n+1` 的陣列只含 `1..n`，恰有一個值重複。不可修改輸入，只能用 $O(1)$ 空間。

> [!tip]- 三層提示
> 1. 把 index 看成節點、`nums[index]` 看成下一個節點。
> 2. 有重複值代表兩條邊進入同一節點，因此形成 cycle。
> 3. 重複值就是 cycle entrance。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 長度 n+1 的陣列只含 1..n，恰有一個值重複。不可修改輸入，只能用 $O(1)$ 空間。
>
> **核心轉換：** 使用 Floyd cycle detection。第一階段讓 slow 與 fast 在 cycle 內相遇；第二階段從起點與相遇點同步前進，交會處就是 cycle entrance。
>
> **主要知識點：** Two Pointers 與單調淘汰。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Find the Duplicate Number
      │
      ├─ 暴力路線：枚舉所有 index pair 或每次移動一端後重新掃描另一端
      │
      ▼  找出本題最關鍵的轉換
核心觀察：使用 Floyd cycle detection。第一階段讓 slow 與 fast 在 cycle 內相遇；第二階段從起點與相遇點同步前進，交會處就是 cycle entrance。
      │
Pattern toolbox：兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區
      │
      ├─ 狀態轉移：依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選
      │
      ├─ 永遠成立：指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 長度 n+1 的陣列只含 1..n，恰有一個值重複。不可修改輸入，只能用 $O(1)$ 空間。
2. **寫出暴力：** 枚舉所有 index pair 或每次移動一端後重新掃描另一端。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 使用 Floyd cycle detection。第一階段讓 slow 與 fast 在 cycle 內相遇；第二階段從起點與相遇點同步前進，交會處就是 cycle entrance。
4. **定義 state 與轉移：** 使用「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」承載上述觀察，再執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」代表什麼，再說每一步如何「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案」的 base case。
>
> 2. **維持：** 每次執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」後，狀態仍與已處理資料一致。關鍵論證是：每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

使用 Floyd cycle detection。第一階段讓 slow 與 fast 在 cycle 內相遇；第二階段從起點與相遇點同步前進，交會處就是 cycle entrance。

```python
def find_duplicate(nums):
    slow = fast = nums[0]
    while True:
        slow = nums[slow]
        fast = nums[nums[fast]]
        if slow == fast:
            break

    slow = nums[0]
    while slow != fast:
        slow = nums[slow]
        fast = nums[fast]
    return slow
```

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：若可以修改輸入？**

**答：**可用 index marking，把 `abs(nums[i])` 對應位置變負；第一次遇到已為負的位置即為重複值。這會破壞輸入。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Find the Duplicate Number》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：使用 Floyd cycle detection。第一階段讓 slow 與 fast 在 cycle 內相遇；第二階段從起點與相遇點同步前進，交會處就是 cycle entrance。 失效情境包括：若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。
>
> 替代路線是：可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。
>
> 套回《Find the Duplicate Number》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。
>
> 此外必須把《Find the Duplicate Number》目前隱含的前提寫成 contract：長度 n+1 的陣列只含 1..n，恰有一個值重複。不可修改輸入，只能用 $O(1)$ 空間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Shortest Subarray to Remove to Make Array Sorted

### 題目

移除一段連續 subarray，使剩餘元素非遞減；求最短移除長度。

> [!tip]- 三層提示
> 1. 找最長已排序 prefix 與 suffix。
> 2. 答案可能只移除尾端或開頭。
> 3. 用 two pointers 嘗試把 prefix 與 suffix 接起來。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 移除一段連續 subarray，使剩餘元素非遞減；求最短移除長度。
>
> **核心轉換：** 先找 [0..left] 的最長非遞減 prefix，以及 [right..n-1] 的最長 suffix。接著令 i 在 prefix、j 在 suffix：若 arr[i] <= arr[j] 可接合，移除 (i, j)；否則必須增加 j。
>
> **主要知識點：** Two Pointers 與單調淘汰。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Shortest Subarray to Remove to Make Array Sorted
      │
      ├─ 暴力路線：枚舉所有 index pair 或每次移動一端後重新掃描另一端
      │
      ▼  找出本題最關鍵的轉換
核心觀察：先找 [0..left] 的最長非遞減 prefix，以及 [right..n-1] 的最長 suffix。接著令 i 在 prefix、j 在 suffix：若 arr[i] <= arr[j] 可接合，移除 (i, j)；否則必須增加 j。
      │
Pattern toolbox：兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區
      │
      ├─ 狀態轉移：依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選
      │
      ├─ 永遠成立：指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 移除一段連續 subarray，使剩餘元素非遞減；求最短移除長度。
2. **寫出暴力：** 枚舉所有 index pair 或每次移動一端後重新掃描另一端。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 先找 [0..left] 的最長非遞減 prefix，以及 [right..n-1] 的最長 suffix。接著令 i 在 prefix、j 在 suffix：若 arr[i] <= arr[j] 可接合，移除 (i, j)；否則必須增加 j。
4. **定義 state 與轉移：** 使用「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」承載上述觀察，再執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」代表什麼，再說每一步如何「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案」的 base case。
>
> 2. **維持：** 每次執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」後，狀態仍與已處理資料一致。關鍵論證是：每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

先找 `[0..left]` 的最長非遞減 prefix，以及 `[right..n-1]` 的最長 suffix。接著令 `i` 在 prefix、`j` 在 suffix：若 `arr[i] <= arr[j]` 可接合，移除 `(i, j)`；否則必須增加 `j`。

```python
def find_length_of_shortest_subarray(arr):
    n = len(arr)
    left = 0
    while left + 1 < n and arr[left] <= arr[left + 1]:
        left += 1
    if left == n - 1:
        return 0

    right = n - 1
    while right > 0 and arr[right - 1] <= arr[right]:
        right -= 1

    answer = min(n - left - 1, right)
    i, j = 0, right
    while i <= left and j < n:
        if arr[i] <= arr[j]:
            answer = min(answer, j - i - 1)
            i += 1
        else:
            j += 1
    return answer
```

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：要回傳實際移除區間？**

**答：**每次更新最短長度時，同時記錄 `(i+1, j-1)`；只刪尾端與只刪開頭的初始答案也要保存其區間。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Shortest Subarray to Remove to Make Array Sorted》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：先找 [0..left] 的最長非遞減 prefix，以及 [right..n-1] 的最長 suffix。接著令 i 在 prefix、j 在 suffix：若 arr[i] <= arr[j] 可接合，移除 (i, j)；否則必須增加 j。 失效情境包括：若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。
>
> 替代路線是：可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。
>
> 套回《Shortest Subarray to Remove to Make Array Sorted》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。
>
> 此外必須把《Shortest Subarray to Remove to Make Array Sorted》目前隱含的前提寫成 contract：移除一段連續 subarray，使剩餘元素非遞減；求最短移除長度。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Minimum Window Subsequence

### 題目

找 `s` 的最短 substring，使 `t` 是該 substring 的 subsequence。

> [!tip]- 三層提示
> 1. 一般 sliding window 無法用 count 判斷 subsequence。
> 2. 向前掃到完整匹配 `t`。
> 3. 再倒退收縮，找到這次匹配的最晚起點。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 找 s 的最短 substring，使 t 是該 substring 的 subsequence。
>
> **核心轉換：** 向前移動 i，依序匹配 t。完成一次後，從終點往回匹配 t 的反向，得到最短起點。下一輪從該起點後一格重新開始，避免漏掉重疊候選。
>
> **主要知識點：** Two Pointers 與單調淘汰。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum Window Subsequence
      │
      ├─ 暴力路線：枚舉所有 index pair 或每次移動一端後重新掃描另一端
      │
      ▼  找出本題最關鍵的轉換
核心觀察：向前移動 i，依序匹配 t。完成一次後，從終點往回匹配 t 的反向，得到最短起點。下一輪從該起點後一格重新開始，避免漏掉重疊候選。
      │
Pattern toolbox：兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區
      │
      ├─ 狀態轉移：依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選
      │
      ├─ 永遠成立：指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 找 s 的最短 substring，使 t 是該 substring 的 subsequence。
2. **寫出暴力：** 枚舉所有 index pair 或每次移動一端後重新掃描另一端。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 向前移動 i，依序匹配 t。完成一次後，從終點往回匹配 t 的反向，得到最短起點。下一輪從該起點後一格重新開始，避免漏掉重疊候選。
4. **定義 state 與轉移：** 使用「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」承載上述觀察，再執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：worst case $O(st)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「兩個只向單一方向移動的邊界，夾住仍可能產生答案的候選區」代表什麼，再說每一步如何「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「指標外的候選已被證明不可能更好；指標內仍包含至少一個最佳答案」的 base case。
>
> 2. **維持：** 每次執行「依比較結果或局部性質，安全地移動其中一端並永久淘汰一批不可能候選」後，狀態仍與已處理資料一致。關鍵論證是：每次移動必須附帶支配性或單調性證明：被跳過的候選即使與未來元素配對，也不可能改善目前答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複值、指標交錯、移動後漏算、輸入未排序，以及原地修改時覆蓋尚未讀取的值。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

向前移動 `i`，依序匹配 `t`。完成一次後，從終點往回匹配 `t` 的反向，得到最短起點。下一輪從該起點後一格重新開始，避免漏掉重疊候選。

```python
def min_window_subsequence(s, t):
    best = ""
    i = 0
    while i < len(s):
        j = 0
        while i < len(s):
            if s[i] == t[j]:
                j += 1
                if j == len(t):
                    break
            i += 1
        if j < len(t):
            break

        end = i + 1
        j = len(t) - 1
        while j >= 0:
            if s[i] == t[j]:
                j -= 1
            i -= 1
        start = i + 1
        candidate = s[start:end]
        if not best or len(candidate) < len(best):
            best = candidate
        i = start + 1
    return best
```

- 時間：worst case $O(|s||t|)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：有大量不同 `t` 查詢、但 `s` 固定？**

**答：**預先為每個字元保存其在 `s` 的 sorted positions。對每個 `t`，用 binary search 依序跳到下一個位置；若還要最短 window，需枚舉可能起點或使用更進階 automaton / DP。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum Window Subsequence》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：向前移動 i，依序匹配 t。完成一次後，從終點往回匹配 t 的反向，得到最短起點。下一輪從該起點後一格重新開始，避免漏掉重疊候選。 失效情境包括：若移動一端後無法永久排除候選，或負數／非單調評分破壞支配關係，雙指標可能不成立。
>
> 替代路線是：可回到排序＋binary search、prefix structure、DP 或完整搜尋；若要保留原 index，排序前先綁定 index。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存產生最佳值時的 left/right，或記錄每次 pointer decision；去重題則輸出 canonical tuple。
>
> 套回《Minimum Window Subsequence》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 通常只能保留一端與有限摘要；外部資料需 chunk merge。共享陣列上的原地 pointer 更新要明確定義 ownership。
>
> 此外必須把《Minimum Window Subsequence》目前隱含的前提寫成 contract：找 s 的最短 substring，使 t 是該 substring 的 subsequence。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 每次移動 pointer 時，能說明排除了哪些答案。
- [ ] 會處理排序後的 duplicate。
- [ ] 能分辨 two pointers 與 sliding window。
- [ ] 能把 array 映射成 linked structure 使用快慢指標。
