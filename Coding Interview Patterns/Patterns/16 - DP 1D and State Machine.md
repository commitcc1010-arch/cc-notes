---
title: DP 1D and State Machine
tags:
  - coding-interview/pattern
  - dynamic-programming
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 16 — DP I：1D and State Machine

[[15 - Greedy|← 上一章]] · [[00 - Book Index|目錄]] · [[17 - DP 2D Sequence and Interval|下一章 →]]

> [!abstract] Mental model
> DP 的第一步不是寫 table，而是定義「能代表所有未來決策的最小狀態」。接著列出最後一步選擇、base case、計算順序，最後才考慮壓縮空間。

## 五問

1. State 代表什麼？
2. 最後一步有哪些選擇？
3. Transition 從哪些較小 state 來？
4. Base case 是什麼？
5. 計算順序是否保證 dependency 已完成？

---

## 核心題 1：Maximum Subarray


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 求連續 subarray 的最大總和。
>
> **核心轉換：** Kadane 的 current 表示必須以目前位置結尾的最佳和；若先前和為負就捨棄，best 則保存所有結尾位置的最大值。
>
> **主要知識點：** 1D DP、有限狀態機與歷史壓縮。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Maximum Subarray
      │
      ├─ 暴力路線：枚舉所有決策序列，或為每個位置重算所有較早 prefix
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Kadane 的 current 表示必須以目前位置結尾的最佳和；若先前和為負就捨棄，best 則保存所有結尾位置的最大值。
      │
Pattern toolbox：dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數
      │
      ├─ 狀態轉移：列出最後一步選擇，從較小 prefix/state 轉移到目前狀態
      │
      ├─ 永遠成立：更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 求連續 subarray 的最大總和。
2. **寫出暴力：** 枚舉所有決策序列，或為每個位置重算所有較早 prefix。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Kadane 的 current 表示必須以目前位置結尾的最佳和；若先前和為負就捨棄，best 則保存所有結尾位置的最大值。
4. **定義 state 與轉移：** 使用「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」承載上述觀察，再執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」代表什麼，再說每一步如何「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致」的 base case。
>
> 2. **維持：** 每次執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」後，狀態仍與已處理資料一致。關鍵論證是：以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def max_subarray(nums):
    current = best = nums[0]
    for x in nums[1:]:
        current = max(x, current + x)
        best = max(best, current)
    return best
```

**State：**`current` 是「必須以目前位置結尾」的最大 subarray sum。

### Follow-up 1：原題直接變形
**問：Circular Maximum Subarray？**

**答：**答案是一般 maximum，或總和減去 minimum subarray。若所有數皆負，後者會選空區間，必須直接回傳一般 maximum。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Maximum Subarray》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Kadane 的 current 表示必須以目前位置結尾的最佳和；若先前和為負就捨棄，best 則保存所有結尾位置的最大值。 失效情境包括：狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。
>
> 替代路線是：重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。
>
> 套回《Maximum Subarray》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。
>
> 此外必須把《Maximum Subarray》目前隱含的前提寫成 contract：求連續 subarray 的最大總和。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：House Robber


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 相鄰房屋不可同時選，求可取得的最大金額。
>
> **核心轉換：** 處理到 i 時只有 rob i（接 i-2）或 skip i（沿用 i-1）兩種互斥最後決策，因此只需保存前兩個 DP 值。
>
> **主要知識點：** 1D DP、有限狀態機與歷史壓縮。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：House Robber
      │
      ├─ 暴力路線：枚舉所有決策序列，或為每個位置重算所有較早 prefix
      │
      ▼  找出本題最關鍵的轉換
核心觀察：處理到 i 時只有 rob i（接 i-2）或 skip i（沿用 i-1）兩種互斥最後決策，因此只需保存前兩個 DP 值。
      │
Pattern toolbox：dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數
      │
      ├─ 狀態轉移：列出最後一步選擇，從較小 prefix/state 轉移到目前狀態
      │
      ├─ 永遠成立：更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 相鄰房屋不可同時選，求可取得的最大金額。
2. **寫出暴力：** 枚舉所有決策序列，或為每個位置重算所有較早 prefix。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 處理到 i 時只有 rob i（接 i-2）或 skip i（沿用 i-1）兩種互斥最後決策，因此只需保存前兩個 DP 值。
4. **定義 state 與轉移：** 使用「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」承載上述觀察，再執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」代表什麼，再說每一步如何「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致」的 base case。
>
> 2. **維持：** 每次執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」後，狀態仍與已處理資料一致。關鍵論證是：以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def rob(nums):
    previous_two = previous_one = 0
    for value in nums:
        current = max(previous_one, previous_two + value)
        previous_two, previous_one = previous_one, current
    return previous_one
```

**Transition：**`dp[i] = max(dp[i-1], dp[i-2]+nums[i])`。

### Follow-up 1：原題直接變形
**問：房屋成環？**

**答：**第一與最後不能同選。答案是 `rob(nums[:-1])` 與 `rob(nums[1:])` 的最大值；單一房屋需特判。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《House Robber》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：處理到 i 時只有 rob i（接 i-2）或 skip i（沿用 i-1）兩種互斥最後決策，因此只需保存前兩個 DP 值。 失效情境包括：狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。
>
> 替代路線是：重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。
>
> 套回《House Robber》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。
>
> 此外必須把《House Robber》目前隱含的前提寫成 contract：相鄰房屋不可同時選，求可取得的最大金額。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Coin Change

### 題目

硬幣可無限使用，求組成 amount 的最少硬幣數。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 硬幣可無限使用，求組成 amount 的最少硬幣數。
>
> **核心轉換：** dp[x] 是湊出金額 x 的最少枚數；最後一枚若為 coin，前驅是 dp[x-coin]，對所有 coin 取最小並以 infinity 表示不可達。
>
> **主要知識點：** 1D DP、有限狀態機與歷史壓縮。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Coin Change
      │
      ├─ 暴力路線：枚舉所有決策序列，或為每個位置重算所有較早 prefix
      │
      ▼  找出本題最關鍵的轉換
核心觀察：dp[x] 是湊出金額 x 的最少枚數；最後一枚若為 coin，前驅是 dp[x-coin]，對所有 coin 取最小並以 infinity 表示不可達。
      │
Pattern toolbox：dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數
      │
      ├─ 狀態轉移：列出最後一步選擇，從較小 prefix/state 轉移到目前狀態
      │
      ├─ 永遠成立：更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 硬幣可無限使用，求組成 amount 的最少硬幣數。
2. **寫出暴力：** 枚舉所有決策序列，或為每個位置重算所有較早 prefix。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** dp[x] 是湊出金額 x 的最少枚數；最後一枚若為 coin，前驅是 dp[x-coin]，對所有 coin 取最小並以 infinity 表示不可達。
4. **定義 state 與轉移：** 使用「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」承載上述觀察，再執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」代表什麼，再說每一步如何「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致」的 base case。
>
> 2. **維持：** 每次執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」後，狀態仍與已處理資料一致。關鍵論證是：以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def coin_change(coins, amount):
    dp = [amount + 1] * (amount + 1)
    dp[0] = 0
    for value in range(1, amount + 1):
        for coin in coins:
            if coin <= value:
                dp[value] = min(dp[value], dp[value - coin] + 1)
    return -1 if dp[amount] == amount + 1 else dp[amount]
```

### Follow-up 1：原題直接變形
**問：計算組合數量，順序不同視為同一組？**

**答：**外層遍歷 coins、內層 amount 由小到大，避免把不同排列重複計數。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Coin Change》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：dp[x] 是湊出金額 x 的最少枚數；最後一枚若為 coin，前驅是 dp[x-coin]，對所有 coin 取最小並以 infinity 表示不可達。 失效情境包括：狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。
>
> 替代路線是：重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。
>
> 套回《Coin Change》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。
>
> 此外必須把《Coin Change》目前隱含的前提寫成 contract：硬幣可無限使用，求組成 amount 的最少硬幣數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Best Time to Buy and Sell Stock IV

### 題目

最多完成 `k` 次交易，一次交易是一買一賣，持有股票時不能再買。求最大利潤。

> [!tip]- 三層提示
> 1. State 需要交易次數與是否持有。
> 2. `buy[t]`：完成到第 t 次交易中的買入後最佳現金；`sell[t]`：完成 t 次賣出後最佳現金。
> 3. 若 `k >= n/2`，限制等同不存在。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 最多完成 k 次交易，一次交易是一買一賣，持有股票時不能再買。求最大利潤。
>
> **核心轉換：** 對每個價格更新：
>
> **主要知識點：** 1D DP、有限狀態機與歷史壓縮。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Best Time to Buy and Sell Stock IV
      │
      ├─ 暴力路線：枚舉所有決策序列，或為每個位置重算所有較早 prefix
      │
      ▼  找出本題最關鍵的轉換
核心觀察：對每個價格更新：
      │
Pattern toolbox：dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數
      │
      ├─ 狀態轉移：列出最後一步選擇，從較小 prefix/state 轉移到目前狀態
      │
      ├─ 永遠成立：更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 最多完成 k 次交易，一次交易是一買一賣，持有股票時不能再買。求最大利潤。
2. **寫出暴力：** 枚舉所有決策序列，或為每個位置重算所有較早 prefix。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 對每個價格更新：
4. **定義 state 與轉移：** 使用「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」承載上述觀察，再執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(nk)$；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」代表什麼，再說每一步如何「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致」的 base case。
>
> 2. **維持：** 每次執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」後，狀態仍與已處理資料一致。關鍵論證是：以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

對每個價格更新：

```text
buy[t]  = max(buy[t], sell[t-1] - price)
sell[t] = max(sell[t], buy[t] + price)
```

大 `k` 時可直接累加所有正相鄰差。

```python
def max_profit_k_transactions(k, prices):
    n = len(prices)
    if k >= n // 2:
        return sum(
            max(0, prices[i] - prices[i - 1])
            for i in range(1, n)
        )

    buy = [float("-inf")] * (k + 1)
    sell = [0] * (k + 1)
    for price in prices:
        for transaction in range(1, k + 1):
            buy[transaction] = max(
                buy[transaction],
                sell[transaction - 1] - price,
            )
            sell[transaction] = max(
                sell[transaction],
                buy[transaction] + price,
            )
    return sell[k]
```

- 時間：$O(nk)$
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：加入 transaction fee 或 cooldown？**

**答：**fee 可在 sell transition 扣除；cooldown 需要讓 buy 依賴更早的 sell，例如前兩天狀態。先畫 finite-state machine 再寫 transition。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Best Time to Buy and Sell Stock IV》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：對每個價格更新： 失效情境包括：狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。
>
> 替代路線是：重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。
>
> 套回《Best Time to Buy and Sell Stock IV》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。
>
> 此外必須把《Best Time to Buy and Sell Stock IV》目前隱含的前提寫成 contract：最多完成 k 次交易，一次交易是一買一賣，持有股票時不能再買。求最大利潤。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Decode Ways II

### 題目

Digit string 中 `*` 可代表 `1..9`。依 `1->A ... 26->Z`，計算 decoding 數量。

> [!tip]- 三層提示
> 1. 每個位置只依賴前一與前二位置。
> 2. 寫 helper 計算單字元有幾種解法。
> 3. 再寫 helper 計算兩字元合在一起有幾種合法數字。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** Digit string 中 可代表 1..9。依 1->A ... 26->Z，計算 decoding 數量。
>
> **核心轉換：** dp[i] = dp[i-1]single(s[i-1]) + dp[i-2]pair(s[i-2],s[i-1])。把複雜 wildcard case 隔離在兩個 counting helpers。
>
> **主要知識點：** 1D DP、有限狀態機與歷史壓縮。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Decode Ways II
      │
      ├─ 暴力路線：枚舉所有決策序列，或為每個位置重算所有較早 prefix
      │
      ▼  找出本題最關鍵的轉換
核心觀察：dp[i] = dp[i-1]single(s[i-1]) + dp[i-2]pair(s[i-2],s[i-1])。把複雜 wildcard case 隔離在兩個 counting helpers。
      │
Pattern toolbox：dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數
      │
      ├─ 狀態轉移：列出最後一步選擇，從較小 prefix/state 轉移到目前狀態
      │
      ├─ 永遠成立：更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** Digit string 中 可代表 1..9。依 1->A ... 26->Z，計算 decoding 數量。
2. **寫出暴力：** 枚舉所有決策序列，或為每個位置重算所有較早 prefix。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** dp[i] = dp[i-1]single(s[i-1]) + dp[i-2]pair(s[i-2],s[i-1])。把複雜 wildcard case 隔離在兩個 counting helpers。
4. **定義 state 與轉移：** 使用「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」承載上述觀察，再執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」代表什麼，再說每一步如何「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致」的 base case。
>
> 2. **維持：** 每次執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」後，狀態仍與已處理資料一致。關鍵論證是：以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`dp[i] = dp[i-1]*single(s[i-1]) + dp[i-2]*pair(s[i-2],s[i-1])`。把複雜 wildcard case 隔離在兩個 counting helpers。

```python
def num_decodings_star(s):
    mod = 1_000_000_007
    if not s:
        return 0

    def single(ch):
        if ch == "*":
            return 9
        return 0 if ch == "0" else 1

    def pair(a, b):
        if a == "*" and b == "*":
            return 15
        if a == "*":
            return 2 if "0" <= b <= "6" else 1
        if b == "*":
            if a == "1":
                return 9
            if a == "2":
                return 6
            return 0
        return 1 if 10 <= int(a + b) <= 26 else 0

    previous_two = 1
    previous_one = single(s[0])
    for i in range(1, len(s)):
        current = (
            previous_one * single(s[i])
            + previous_two * pair(s[i - 1], s[i])
        ) % mod
        previous_two, previous_one = previous_one, current
    return previous_one
```

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：空字串如何定義？**

**答：**組合 DP 內部通常把空 prefix 定義為一種方法 `dp[0]=1`；但完整輸入為空是否算一種 decoding 屬於 API contract。本書實作選擇回傳 0。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Decode Ways II》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：dp[i] = dp[i-1]single(s[i-1]) + dp[i-2]pair(s[i-2],s[i-1])。把複雜 wildcard case 隔離在兩個 counting helpers。 失效情境包括：狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。
>
> 替代路線是：重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。
>
> 套回《Decode Ways II》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。
>
> 此外必須把《Decode Ways II》目前隱含的前提寫成 contract：Digit string 中 可代表 1..9。依 1->A ... 26->Z，計算 decoding 數量。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Frog Jump

### 題目

石頭位置遞增。青蛙上次跳 `k`，下次只能跳 `k-1`、`k`、`k+1` 且必須為正。判斷能否到最後石頭。

> [!tip]- 三層提示
> 1. 只知道 stone index 不足，還需知道上次 jump。
> 2. 對每個 position 保存可到達它的 jump sizes。
> 3. 從 state `(position,jump)` 推三個下一 state。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 石頭位置遞增。青蛙上次跳 k，下次只能跳 k-1、k、k+1 且必須為正。判斷能否到最後石頭。
>
> **核心轉換：** 這是 sparse DP。Map position -> set(lastjump)；對每個可達 state，檢查下一位置是否為石頭。
>
> **主要知識點：** 1D DP、有限狀態機與歷史壓縮。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Frog Jump
      │
      ├─ 暴力路線：枚舉所有決策序列，或為每個位置重算所有較早 prefix
      │
      ▼  找出本題最關鍵的轉換
核心觀察：這是 sparse DP。Map position -> set(lastjump)；對每個可達 state，檢查下一位置是否為石頭。
      │
Pattern toolbox：dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數
      │
      ├─ 狀態轉移：列出最後一步選擇，從較小 prefix/state 轉移到目前狀態
      │
      ├─ 永遠成立：更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 石頭位置遞增。青蛙上次跳 k，下次只能跳 k-1、k、k+1 且必須為正。判斷能否到最後石頭。
2. **寫出暴力：** 枚舉所有決策序列，或為每個位置重算所有較早 prefix。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 這是 sparse DP。Map position -> set(lastjump)；對每個可達 state，檢查下一位置是否為石頭。
4. **定義 state 與轉移：** 使用「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」承載上述觀察，再執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：worst case $O(n^2)$；空間：$O(n^2)$

> [!tip] 一句話記憶
> 先說清楚「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」代表什麼，再說每一步如何「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致」的 base case。
>
> 2. **維持：** 每次執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」後，狀態仍與已處理資料一致。關鍵論證是：以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

這是 sparse DP。Map `position -> set(last_jump)`；對每個可達 state，檢查下一位置是否為石頭。

```python
from collections import defaultdict

def can_cross(stones):
    jumps = defaultdict(set)
    jumps[stones[0]].add(0)
    positions = set(stones)

    for position in stones:
        for last in jumps[position]:
            for step in (last - 1, last, last + 1):
                if step > 0 and position + step in positions:
                    jumps[position + step].add(step)
    return bool(jumps[stones[-1]])
```

- 時間：worst case $O(n^2)$
- 空間：$O(n^2)$

### Follow-up 1：原題直接變形
**問：求最少跳躍次數？**

**答：**把 `(position,last_jump)` 視為 graph state 做 BFS；第一次到最後石頭的層數即最少 jumps。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Frog Jump》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：這是 sparse DP。Map position -> set(lastjump)；對每個可達 state，檢查下一位置是否為石頭。 失效情境包括：狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。
>
> 替代路線是：重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。
>
> 套回《Frog Jump》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。
>
> 此外必須把《Frog Jump》目前隱含的前提寫成 contract：石頭位置遞增。青蛙上次跳 k，下次只能跳 k-1、k、k+1 且必須為正。判斷能否到最後石頭。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Odd Even Jump

### 題目

從 index `i`：

- odd jump 到右側值不小於目前值中的最小值，tie 取最小 index。
- even jump 到右側值不大於目前值中的最大值，tie 取最小 index。

計算多少起點能到最後 index。

> [!tip]- 三層提示
> 1. 先求每個 index 的 odd-next 與 even-next。
> 2. 依 `(value,index)` 排序後，用 monotonic stack 求 next index。
> 3. 從右向左 DP：odd-good 依賴 next 的 even-good。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 從 index i：
>
> **核心轉換：** 將 indices 依 (arr[i],i) 排序，用 stack 求原 index 序列中的 next greater-or-equal；依 (-arr[i],i) 排序求 next smaller-or-equal。
>
> **主要知識點：** 1D DP、有限狀態機與歷史壓縮。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Odd Even Jump
      │
      ├─ 暴力路線：枚舉所有決策序列，或為每個位置重算所有較早 prefix
      │
      ▼  找出本題最關鍵的轉換
核心觀察：將 indices 依 (arr[i],i) 排序，用 stack 求原 index 序列中的 next greater-or-equal；依 (-arr[i],i) 排序求 next smaller-or-equal。
      │
Pattern toolbox：dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數
      │
      ├─ 狀態轉移：列出最後一步選擇，從較小 prefix/state 轉移到目前狀態
      │
      ├─ 永遠成立：更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 從 index i：
2. **寫出暴力：** 枚舉所有決策序列，或為每個位置重算所有較早 prefix。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 將 indices 依 (arr[i],i) 排序，用 stack 求原 index 序列中的 next greater-or-equal；依 (-arr[i],i) 排序求 next smaller-or-equal。
4. **定義 state 與轉移：** 使用「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」承載上述觀察，再執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」代表什麼，再說每一步如何「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致」的 base case。
>
> 2. **維持：** 每次執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」後，狀態仍與已處理資料一致。關鍵論證是：以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

將 indices 依 `(arr[i],i)` 排序，用 stack 求原 index 序列中的 next greater-or-equal；依 `(-arr[i],i)` 排序求 next smaller-or-equal。

```python
def odd_even_jumps(arr):
    n = len(arr)

    def make_next(indices):
        result = [-1] * n
        stack = []
        for index in indices:
            while stack and index > stack[-1]:
                result[stack.pop()] = index
            stack.append(index)
        return result

    higher = make_next(sorted(range(n), key=lambda i: (arr[i], i)))
    lower = make_next(sorted(range(n), key=lambda i: (-arr[i], i)))

    odd = [False] * n
    even = [False] * n
    odd[-1] = even[-1] = True

    for i in range(n - 2, -1, -1):
        if higher[i] != -1:
            odd[i] = even[higher[i]]
        if lower[i] != -1:
            even[i] = odd[lower[i]]
    return sum(odd)
```

- 時間：$O(n\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：若 jump 規則改成右側距離最近，而非值最接近？**

**答：**next-state 預處理會改變，可能可用 monotonic stack 直接按原順序求 next greater/smaller；先精確區分「值最佳」與「index 最近」。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Odd Even Jump》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：將 indices 依 (arr[i],i) 排序，用 stack 求原 index 序列中的 next greater-or-equal；依 (-arr[i],i) 排序求 next smaller-or-equal。 失效情境包括：狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。
>
> 替代路線是：重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。
>
> 套回《Odd Even Jump》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。
>
> 此外必須把《Odd Even Jump》目前隱含的前提寫成 contract：從 index i：。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Super Egg Drop

### 題目

有 `k` 顆蛋與 `n` 層樓，找出臨界樓層所需最少 worst-case moves。

> [!tip]- 三層提示
> 1. 傳統 `dp[eggs][floors]` 轉移太慢。
> 2. 反過來問：給 `moves` 與 `eggs`，最多能測多少 floors？
> 3. 一次丟蛋後，碎與不碎覆蓋兩個子範圍，再加目前樓層。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 有 k 顆蛋與 n 層樓，找出臨界樓層所需最少 worst-case moves。
>
> **核心轉換：** 令 dp[e] 為使用目前 moves、e 顆蛋最多可確認的樓層數：
>
> **主要知識點：** 1D DP、有限狀態機與歷史壓縮。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Super Egg Drop
      │
      ├─ 暴力路線：枚舉所有決策序列，或為每個位置重算所有較早 prefix
      │
      ▼  找出本題最關鍵的轉換
核心觀察：令 dp[e] 為使用目前 moves、e 顆蛋最多可確認的樓層數：
      │
Pattern toolbox：dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數
      │
      ├─ 狀態轉移：列出最後一步選擇，從較小 prefix/state 轉移到目前狀態
      │
      ├─ 永遠成立：更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 有 k 顆蛋與 n 層樓，找出臨界樓層所需最少 worst-case moves。
2. **寫出暴力：** 枚舉所有決策序列，或為每個位置重算所有較早 prefix。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 令 dp[e] 為使用目前 moves、e 顆蛋最多可確認的樓層數：
4. **定義 state 與轉移：** 使用「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」承載上述觀察，再執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(k \cdot answer)$；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「dp[i]/state 表示處理固定 prefix 後、在明確限制下的最佳值或方案數」代表什麼，再說每一步如何「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「更新某狀態前，所有依賴狀態仍代表上一個正確階段；dp 定義與迴圈順序一致」的 base case。
>
> 2. **維持：** 每次執行「列出最後一步選擇，從較小 prefix/state 轉移到目前狀態」後，狀態仍與已處理資料一致。關鍵論證是：以 prefix length induction，證明所有方案依最後一步被完整且互斥地分類，再取 min/max/sum。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：base case、不可達狀態、原地更新方向、重複計數、模數、負值與答案 reconstruction。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

令 `dp[e]` 為使用目前 moves、`e` 顆蛋最多可確認的樓層數：

$$
dp[e] = dp[e-1] + dp[e] + 1
$$

右邊舊 `dp[e-1]` 是碎掉後下方可測範圍，舊 `dp[e]` 是未碎後上方範圍。更新需由大 `e` 往小。

```python
def super_egg_drop(k, n):
    covered = [0] * (k + 1)
    moves = 0
    while covered[k] < n:
        moves += 1
        for eggs in range(k, 0, -1):
            covered[eggs] = (
                covered[eggs]
                + covered[eggs - 1]
                + 1
            )
    return moves
```

- 時間：$O(k \cdot answer)$
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：每次丟蛋成本依樓層不同？**

**答：**moves 不再是均一成本，coverage recurrence 失效；需要以區間與剩餘蛋數做 minimax DP，轉移加入該樓層成本。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Super Egg Drop》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：令 dp[e] 為使用目前 moves、e 顆蛋最多可確認的樓層數： 失效情境包括：狀態缺少會影響未來的資訊時，DP 會錯誤合併歷史；狀態過多則時間／空間爆炸。
>
> 替代路線是：重新定義最小充分狀態，採 bitset、monotonic optimization、matrix exponentiation 或 graph shortest path。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 choice/parent；從終點沿 predecessor 回走。若壓成 O(1) 空間，要另外保留重建資訊或二次計算。
>
> 套回《Super Egg Drop》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上更新通常無法只維持單一 prefix DP；可做 segment tree of transitions。服務化時注意 cache key 與版本。
>
> 此外必須把《Super Egg Drop》目前隱含的前提寫成 contract：有 k 顆蛋與 n 層樓，找出臨界樓層所需最少 worst-case moves。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 能用一句話定義 state。
- [ ] 能列出 transition 的最後一步。
- [ ] 知道 loop 方向會影響 0/1 與 unbounded knapsack。
- [ ] 會把狀態改寫以降低維度或 transition 成本。
