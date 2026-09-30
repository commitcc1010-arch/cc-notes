---
title: Bit Math and Geometry
tags:
  - coding-interview/pattern
  - bit-manipulation
  - math
  - geometry
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 18 — Bit, Math and Geometry

[[17 - DP 2D Sequence and Interval|← 上一章]] · [[00 - Book Index|目錄]] · [[19 - Data Structure Design|下一章 →]]

> [!abstract] Mental model
> 位元題利用 XOR、mask 與 binary representation 的代數性質；數學題先找週期、位數或不變量；幾何題避免浮點比較，優先使用 cross product、gcd 與 normalized representation。

---

## 核心題 1：Single Number


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 除了某元素出現一次，其餘皆出現兩次，找唯一元素。
>
> **核心轉換：** 利用 x^x=0、x^0=x 與 XOR 的交換結合律；把所有元素 XOR 後，成對元素互相抵消，只剩 single number。
>
> **主要知識點：** Bit Representation、數學分解與幾何事件。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Single Number
      │
      ├─ 暴力路線：逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係
      │
      ▼  找出本題最關鍵的轉換
核心觀察：利用 x^x=0、x^0=x 與 XOR 的交換結合律；把所有元素 XOR 後，成對元素互相抵消，只剩 single number。
      │
Pattern toolbox：bit mask、位階貢獻、倍增量，或正規化幾何事件與座標
      │
      ├─ 狀態轉移：把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積
      │
      ├─ 永遠成立：目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 除了某元素出現一次，其餘皆出現兩次，找唯一元素。
2. **寫出暴力：** 逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 利用 x^x=0、x^0=x 與 XOR 的交換結合律；把所有元素 XOR 後，成對元素互相抵消，只剩 single number。
4. **定義 state 與轉移：** 使用「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」承載上述觀察，再執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」代表什麼，再說每一步如何「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離」的 base case。
>
> 2. **維持：** 每次執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」後，狀態仍與已處理資料一致。關鍵論證是：由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def single_number(nums):
    answer = 0
    for x in nums:
        answer ^= x
    return answer
```

因為 `x ^ x = 0`、`x ^ 0 = x`，所有成對元素抵消。

### Follow-up 1：原題直接變形
**問：每個數出現三次，只有一個出現一次？**

**答：**逐 bit 計數後對 3 取模；固定寬度 signed integer 要處理 sign bit。也可使用 ones/twos bit-state machine。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Single Number》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：利用 x^x=0、x^0=x 與 XOR 的交換結合律；把所有元素 XOR 後，成對元素互相抵消，只剩 single number。 失效情境包括：固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。
>
> 替代路線是：使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。
>
> 套回《Single Number》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。
>
> 此外必須把《Single Number》目前隱含的前提寫成 contract：除了某元素出現一次，其餘皆出現兩次，找唯一元素。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Counting Bits


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 對 0..n 每個整數計算二進位 1 的數量。
>
> **核心轉換：** 去掉最低 set bit 得到 i&(i-1)，因此 bits[i]=bits[i&(i-1)]+1；或用 bits[i>>1]+(i&1)。
>
> **主要知識點：** Bit Representation、數學分解與幾何事件。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Counting Bits
      │
      ├─ 暴力路線：逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係
      │
      ▼  找出本題最關鍵的轉換
核心觀察：去掉最低 set bit 得到 i&(i-1)，因此 bits[i]=bits[i&(i-1)]+1；或用 bits[i>>1]+(i&1)。
      │
Pattern toolbox：bit mask、位階貢獻、倍增量，或正規化幾何事件與座標
      │
      ├─ 狀態轉移：把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積
      │
      ├─ 永遠成立：目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 對 0..n 每個整數計算二進位 1 的數量。
2. **寫出暴力：** 逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 去掉最低 set bit 得到 i&(i-1)，因此 bits[i]=bits[i&(i-1)]+1；或用 bits[i>>1]+(i&1)。
4. **定義 state 與轉移：** 使用「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」承載上述觀察，再執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」代表什麼，再說每一步如何「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離」的 base case。
>
> 2. **維持：** 每次執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」後，狀態仍與已處理資料一致。關鍵論證是：由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def count_bits(n):
    answer = [0] * (n + 1)
    for value in range(1, n + 1):
        answer[value] = answer[value >> 1] + (value & 1)
    return answer
```

### Follow-up 1：原題直接變形
**問：只計算單一整數的 set bits？**

**答：**反覆 `x &= x-1`，每次移除最低 set bit，時間與 1 的數量成正比。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Counting Bits》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：去掉最低 set bit 得到 i&(i-1)，因此 bits[i]=bits[i&(i-1)]+1；或用 bits[i>>1]+(i&1)。 失效情境包括：固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。
>
> 替代路線是：使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。
>
> 套回《Counting Bits》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。
>
> 此外必須把《Counting Bits》目前隱含的前提寫成 contract：對 0..n 每個整數計算二進位 1 的數量。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Pow(x, n)


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在 O(log |n|) 時間計算 x 的整數次方。
>
> **核心轉換：** binary exponentiation 依 n 的 bits 決定是否把目前 base 乘進答案；每輪 base 平方、exponent 右移，負指數先取倒數。
>
> **主要知識點：** Bit Representation、數學分解與幾何事件。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Pow(x, n)
      │
      ├─ 暴力路線：逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係
      │
      ▼  找出本題最關鍵的轉換
核心觀察：binary exponentiation 依 n 的 bits 決定是否把目前 base 乘進答案；每輪 base 平方、exponent 右移，負指數先取倒數。
      │
Pattern toolbox：bit mask、位階貢獻、倍增量，或正規化幾何事件與座標
      │
      ├─ 狀態轉移：把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積
      │
      ├─ 永遠成立：目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在 O(log |n|) 時間計算 x 的整數次方。
2. **寫出暴力：** 逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** binary exponentiation 依 n 的 bits 決定是否把目前 base 乘進答案；每輪 base 平方、exponent 右移，負指數先取倒數。
4. **定義 state 與轉移：** 使用「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」承載上述觀察，再執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(\log n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」代表什麼，再說每一步如何「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離」的 base case。
>
> 2. **維持：** 每次執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」後，狀態仍與已處理資料一致。關鍵論證是：由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def fast_power(x, n):
    if n < 0:
        x = 1 / x
        n = -n
    answer = 1.0
    while n:
        if n & 1:
            answer *= x
        x *= x
        n >>= 1
    return answer
```

- 時間：$O(\log |n|)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：計算 modular exponent `x^n mod m`？**

**答：**每次乘法與平方後都 `% m`；Python 可直接使用 `pow(x,n,m)`，但面試應能寫 binary exponentiation。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Pow(x, n)》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：binary exponentiation 依 n 的 bits 決定是否把目前 base 乘進答案；每輪 base 平方、exponent 右移，負指數先取倒數。 失效情境包括：固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。
>
> 替代路線是：使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。
>
> 套回《Pow(x, n)》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。
>
> 此外必須把《Pow(x, n)》目前隱含的前提寫成 contract：在 O(log |n|) 時間計算 x 的整數次方。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Divide Two Integers

### 題目

不用乘法、除法與 modulo，計算 32-bit signed integer division，向零截斷。

> [!tip]- 三層提示
> 1. 先用絕對值處理 magnitude，最後補 sign。
> 2. 不要一次減 divisor；用 bit shift 找最大倍數。
> 3. 從最高 bit 到最低 bit 嘗試扣除。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 不用乘法、除法與 modulo，計算 32-bit signed integer division，向零截斷。
>
> **核心轉換：** 若 divisor << bit 不超過目前 dividend，就扣掉並在 quotient 設該 bit。最後依符號與 32-bit 範圍截斷。
>
> **主要知識點：** Bit Representation、數學分解與幾何事件。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Divide Two Integers
      │
      ├─ 暴力路線：逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係
      │
      ▼  找出本題最關鍵的轉換
核心觀察：若 divisor << bit 不超過目前 dividend，就扣掉並在 quotient 設該 bit。最後依符號與 32-bit 範圍截斷。
      │
Pattern toolbox：bit mask、位階貢獻、倍增量，或正規化幾何事件與座標
      │
      ├─ 狀態轉移：把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積
      │
      ├─ 永遠成立：目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 不用乘法、除法與 modulo，計算 32-bit signed integer division，向零截斷。
2. **寫出暴力：** 逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 若 divisor << bit 不超過目前 dividend，就扣掉並在 quotient 設該 bit。最後依符號與 32-bit 範圍截斷。
4. **定義 state 與轉移：** 使用「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」承載上述觀察，再執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(word\ size)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」代表什麼，再說每一步如何「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離」的 base case。
>
> 2. **維持：** 每次執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」後，狀態仍與已處理資料一致。關鍵論證是：由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

若 `divisor << bit` 不超過目前 dividend，就扣掉並在 quotient 設該 bit。最後依符號與 32-bit 範圍截斷。

```python
def divide(dividend, divisor):
    negative = (dividend < 0) != (divisor < 0)
    a, b = abs(dividend), abs(divisor)
    quotient = 0

    for bit in range(31, -1, -1):
        if (b << bit) <= a:
            a -= b << bit
            quotient |= 1 << bit

    if negative:
        quotient = -quotient
    return min(max(quotient, -(1 << 31)), (1 << 31) - 1)
```

- 時間：$O(word\ size)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：語言的 `abs(INT_MIN)` 會 overflow 怎麼辦？**

**答：**先轉成更寬整數型別，或統一在負數域計算，因為 two's complement 負數範圍多一個值。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Divide Two Integers》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：若 divisor << bit 不超過目前 dividend，就扣掉並在 quotient 設該 bit。最後依符號與 32-bit 範圍截斷。 失效情境包括：固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。
>
> 替代路線是：使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。
>
> 套回《Divide Two Integers》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。
>
> 此外必須把《Divide Two Integers》目前隱含的前提寫成 contract：不用乘法、除法與 modulo，計算 32-bit signed integer division，向零截斷。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Number of Digit One

### 題目

計算 `0..n` 的十進位表示中 digit `1` 總共出現幾次。

> [!tip]- 三層提示
> 1. 分別計算 ones、tens、hundreds 每個位置的貢獻。
> 2. 對 factor `f`，把 n 分成 high、current、low。
> 3. current 為 0、1、>1 時公式不同。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算 0..n 的十進位表示中 digit 1 總共出現幾次。
>
> **核心轉換：** 對位置 factor：
>
> **主要知識點：** Bit Representation、數學分解與幾何事件。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Number of Digit One
      │
      ├─ 暴力路線：逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係
      │
      ▼  找出本題最關鍵的轉換
核心觀察：對位置 factor：
      │
Pattern toolbox：bit mask、位階貢獻、倍增量，或正規化幾何事件與座標
      │
      ├─ 狀態轉移：把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積
      │
      ├─ 永遠成立：目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算 0..n 的十進位表示中 digit 1 總共出現幾次。
2. **寫出暴力：** 逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 對位置 factor：
4. **定義 state 與轉移：** 使用「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」承載上述觀察，再執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(\log{10} n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」代表什麼，再說每一步如何「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離」的 base case。
>
> 2. **維持：** 每次執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」後，狀態仍與已處理資料一致。關鍵論證是：由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

對位置 `factor`：

- `current == 0`：`high * factor`
- `current == 1`：`high * factor + low + 1`
- `current > 1`：`(high+1) * factor`

```python
def count_digit_one(n):
    answer = 0
    factor = 1
    while factor <= n:
        low = n % factor
        current = (n // factor) % 10
        high = n // (factor * 10)
        if current == 0:
            answer += high * factor
        elif current == 1:
            answer += high * factor + low + 1
        else:
            answer += (high + 1) * factor
        factor *= 10
    return answer
```

- 時間：$O(\log_{10} n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：計算任意 digit `d`？**

**答：**`d != 0` 可泛化同一公式；`d == 0` 必須排除 leading zeros，high 部分要少算一個 cycle。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Number of Digit One》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：對位置 factor： 失效情境包括：固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。
>
> 替代路線是：使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。
>
> 套回《Number of Digit One》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。
>
> 此外必須把《Number of Digit One》目前隱含的前提寫成 contract：計算 0..n 的十進位表示中 digit 1 總共出現幾次。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Rectangle Area II

### 題目

給多個 axis-aligned rectangles，計算 union area。

> [!tip]- 三層提示
> 1. 對每個 left/right x 建立 add/remove event。
> 2. 相鄰 x events 之間，active rectangles 不變。
> 3. 面積增加 `delta_x * active_y_union_length`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給多個 axis-aligned rectangles，計算 union area。
>
> **核心轉換：** 按 x sweep。active 保存目前 y intervals；在處理 x 的 events 前，先用上一段 active 計算 [previousx,x) 面積。Y union 以排序 merge 計算。
>
> **主要知識點：** Bit Representation、數學分解與幾何事件。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Rectangle Area II
      │
      ├─ 暴力路線：逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係
      │
      ▼  找出本題最關鍵的轉換
核心觀察：按 x sweep。active 保存目前 y intervals；在處理 x 的 events 前，先用上一段 active 計算 [previousx,x) 面積。Y union 以排序 merge 計算。
      │
Pattern toolbox：bit mask、位階貢獻、倍增量，或正規化幾何事件與座標
      │
      ├─ 狀態轉移：把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積
      │
      ├─ 永遠成立：目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給多個 axis-aligned rectangles，計算 union area。
2. **寫出暴力：** 逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 按 x sweep。active 保存目前 y intervals；在處理 x 的 events 前，先用上一段 active 計算 [previousx,x) 面積。Y union 以排序 merge 計算。
4. **定義 state 與轉移：** 使用「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」承載上述觀察，再執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：樸素 active merge 為 $O(n^2\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」代表什麼，再說每一步如何「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離」的 base case。
>
> 2. **維持：** 每次執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」後，狀態仍與已處理資料一致。關鍵論證是：由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

按 x sweep。`active` 保存目前 y intervals；在處理 x 的 events 前，先用上一段 active 計算 `[previous_x,x)` 面積。Y union 以排序 merge 計算。

```python
def rectangle_area(rectangles):
    events = []
    for x1, y1, x2, y2 in rectangles:
        events.append((x1, 1, y1, y2))
        events.append((x2, -1, y1, y2))
    events.sort()

    def covered_y(intervals):
        total = 0
        current_start = current_end = None
        for start, end in sorted(intervals):
            if current_end is None or start > current_end:
                if current_end is not None:
                    total += current_end - current_start
                current_start, current_end = start, end
            else:
                current_end = max(current_end, end)
        if current_end is not None:
            total += current_end - current_start
        return total

    active = []
    area = 0
    previous_x = events[0][0] if events else 0
    i = 0
    while i < len(events):
        x = events[i][0]
        area += (x - previous_x) * covered_y(active)
        while i < len(events) and events[i][0] == x:
            _, event_type, y1, y2 = events[i]
            if event_type == 1:
                active.append((y1, y2))
            else:
                active.remove((y1, y2))
            i += 1
        previous_x = x
    return area % 1_000_000_007
```

- 時間：樸素 active merge 為 $O(n^2\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：如何改善到約 $O(n\log n)$？**

**答：**對所有 y 座標 coordinate compression，segment tree 維護 cover count 與 covered length；每個 x event 做 range add。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Rectangle Area II》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：按 x sweep。active 保存目前 y intervals；在處理 x 的 events 前，先用上一段 active 計算 [previousx,x) 面積。Y union 以排序 merge 計算。 失效情境包括：固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。
>
> 替代路線是：使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。
>
> 套回《Rectangle Area II》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。
>
> 此外必須把《Rectangle Area II》目前隱含的前提寫成 contract：給多個 axis-aligned rectangles，計算 union area。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Find the Closest Palindrome

### 題目

給十進位整數字串，找不同於自身且數值距離最近的 palindrome；tie 取較小值。

> [!tip]- 三層提示
> 1. 最近 palindrome 通常由前半 mirror 而來。
> 2. 只需嘗試 prefix-1、prefix、prefix+1。
> 3. 還要加入位數改變的邊界：`999...` 與 `100...001`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給十進位整數字串，找不同於自身且數值距離最近的 palindrome；tie 取較小值。
>
> **核心轉換：** 取前 (length+1)//2 位作 prefix。對三個相鄰 prefix 建 palindrome；再加入 10^(L-1)-1 與 10^L+1。移除原值後以 (distance,value) 取最小。
>
> **主要知識點：** Bit Representation、數學分解與幾何事件。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Find the Closest Palindrome
      │
      ├─ 暴力路線：逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係
      │
      ▼  找出本題最關鍵的轉換
核心觀察：取前 (length+1)//2 位作 prefix。對三個相鄰 prefix 建 palindrome；再加入 10^(L-1)-1 與 10^L+1。移除原值後以 (distance,value) 取最小。
      │
Pattern toolbox：bit mask、位階貢獻、倍增量，或正規化幾何事件與座標
      │
      ├─ 狀態轉移：把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積
      │
      ├─ 永遠成立：目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給十進位整數字串，找不同於自身且數值距離最近的 palindrome；tie 取較小值。
2. **寫出暴力：** 逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 取前 (length+1)//2 位作 prefix。對三個相鄰 prefix 建 palindrome；再加入 10^(L-1)-1 與 10^L+1。移除原值後以 (distance,value) 取最小。
4. **定義 state 與轉移：** 使用「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」承載上述觀察，再執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」代表什麼，再說每一步如何「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離」的 base case。
>
> 2. **維持：** 每次執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」後，狀態仍與已處理資料一致。關鍵論證是：由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

取前 `(length+1)//2` 位作 prefix。對三個相鄰 prefix 建 palindrome；再加入 `10^(L-1)-1` 與 `10^L+1`。移除原值後以 `(distance,value)` 取最小。

```python
def nearest_palindromic(number):
    length = len(number)
    value = int(number)
    prefix_length = (length + 1) // 2
    prefix = int(number[:prefix_length])
    candidates = {
        10 ** (length - 1) - 1,
        10 ** length + 1,
    }

    for candidate_prefix in (prefix - 1, prefix, prefix + 1):
        text = str(candidate_prefix)
        if length % 2:
            palindrome = text + text[-2::-1]
        else:
            palindrome = text + text[::-1]
        candidates.add(int(palindrome))

    candidates.discard(value)
    return str(min(candidates, key=lambda x: (abs(x - value), x)))
```

### Follow-up 1：原題直接變形
**問：輸入可能有 leading zeros？**

**答：**必須先定義它是數值還是固定寬度字串。數值語意應 canonicalize 去除 leading zeros；固定寬度語意則不能直接轉 int 後丟失長度。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Find the Closest Palindrome》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：取前 (length+1)//2 位作 prefix。對三個相鄰 prefix 建 palindrome；再加入 10^(L-1)-1 與 10^L+1。移除原值後以 (distance,value) 取最小。 失效情境包括：固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。
>
> 替代路線是：使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。
>
> 套回《Find the Closest Palindrome》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。
>
> 此外必須把《Find the Closest Palindrome》目前隱含的前提寫成 contract：給十進位整數字串，找不同於自身且數值距離最近的 palindrome；tie 取較小值。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Minimum One Bit Operations to Make Integer Zero

### 題目

允許依特殊規則翻轉 bit，求把非負整數變成零的最少操作數。此操作序列等價於 binary-reflected Gray code。

> [!tip]- 三層提示
> 1. 題目操作順序對應 Gray code 相鄰數只差一 bit。
> 2. 問題等價於把 Gray code 值轉回 binary index。
> 3. Gray inverse 可用不斷 XOR 自己的右移結果。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 允許依特殊規則翻轉 bit，求把非負整數變成零的最少操作數。此操作序列等價於 binary-reflected Gray code。
>
> **核心轉換：** Gray code g = b ^ (b >> 1)。反解時，binary 的每個 prefix bit 是 Gray prefix XOR；因此反覆 answer ^= n; n >>= 1。
>
> **主要知識點：** Bit Representation、數學分解與幾何事件。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum One Bit Operations to Make Integer Zero
      │
      ├─ 暴力路線：逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Gray code g = b ^ (b >> 1)。反解時，binary 的每個 prefix bit 是 Gray prefix XOR；因此反覆 answer ^= n; n >>= 1。
      │
Pattern toolbox：bit mask、位階貢獻、倍增量，或正規化幾何事件與座標
      │
      ├─ 狀態轉移：把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積
      │
      ├─ 永遠成立：目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 允許依特殊規則翻轉 bit，求把非負整數變成零的最少操作數。此操作序列等價於 binary-reflected Gray code。
2. **寫出暴力：** 逐一模擬算術操作、枚舉每個數位／格點，或使用浮點近似精確關係。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Gray code g = b ^ (b >> 1)。反解時，binary 的每個 prefix bit 是 Gray prefix XOR；因此反覆 answer ^= n; n >>= 1。
4. **定義 state 與轉移：** 使用「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」承載上述觀察，再執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(\log n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「bit mask、位階貢獻、倍增量，或正規化幾何事件與座標」代表什麼，再說每一步如何「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前結果精確代表已處理 bits/digits/events；尚未處理部分與已處理部分的貢獻分離」的 base case。
>
> 2. **維持：** 每次執行「把整體答案拆成彼此可組合的位元／數位／區間貢獻，再以移位或 sweep 累積」後，狀態仍與已處理資料一致。關鍵論證是：由二進位／十進位展開或幾何 measure 的可加性證明；每個基本貢獻恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：signed overflow、負數位移、語言整數寬度、除法截斷、浮點誤差、座標端點與 modulo。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Gray code `g = b ^ (b >> 1)`。反解時，binary 的每個 prefix bit 是 Gray prefix XOR；因此反覆 `answer ^= n; n >>= 1`。

```python
def minimum_one_bit_operations(n):
    answer = 0
    while n:
        answer ^= n
        n >>= 1
    return answer
```

- 時間：$O(\log n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：如何由 binary index 產生 Gray code？**

**答：**`gray = index ^ (index >> 1)`。這也常用於枚舉相鄰只改一 bit 的 bitmask 順序。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum One Bit Operations to Make Integer Zero》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Gray code g = b ^ (b >> 1)。反解時，binary 的每個 prefix bit 是 Gray prefix XOR；因此反覆 answer ^= n; n >>= 1。 失效情境包括：固定寬度假設、數值範圍或可加性失效時，bit trick 可能不可移植；浮點比較也不能取代 exact arithmetic。
>
> 替代路線是：使用 arbitrary precision、rational/gcd normalization、coordinate compression 或可靠幾何 predicates。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每個 set bit／digit contribution，或幾何 sweep 的來源事件；可輸出分解步驟作為可驗證證據。
>
> 套回《Minimum One Bit Operations to Make Integer Zero》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production code 必須寫明 integer width、overflow policy 與精度；跨語言時特別測負除法和 shift semantics。
>
> 此外必須把《Minimum One Bit Operations to Make Integer Zero》目前隱含的前提寫成 contract：允許依特殊規則翻轉 bit，求把非負整數變成零的最少操作數。此操作序列等價於 binary-reflected Gray code。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 熟悉 XOR identity 與 set-bit 操作。
- [ ] 能做 binary exponentiation。
- [ ] 幾何表示會避免浮點。
- [ ] 會從位數、週期或編碼關係推導公式。
