---
chapter: 29
title: Matrix、模擬與解析
part: 6
---

# 第 29 章　Matrix、模擬與解析

> [!abstract] 本章地圖
> **一句話**：這類題目沒有聰明的演算法可以跳過工作，難點在於把規則**精確地**翻譯成程式：用方向陣列與邊界變數管理矩陣座標，用狀態編碼在原地更新，用 tokenizer、遞迴下降、狀態機與 stack 把字串變成結構。
>
> **辨識訊號**：
> - 題目給二維 grid，要求「螺旋」「旋轉」「轉置」「依某規則同時更新每一格」
> - 題目要求 O(1) 額外空間的原地修改，但新值依賴舊值
> - 題目是一長串規則（遊戲規則、排版規則、格式規則），沒有最佳化目標，只要求完全照做
> - 輸入是一段有文法的字串：運算式、化學式、標籤、數字格式，含括號或巢狀
> - 限制很小（n ≤ 100、字串長度 ≤ 1000），複雜度不是瓶頸，正確性才是
>
> **核心題**：54、48、73、36、289
>
> **難題**：65、68、591、726、770

## 29.1 這個 Pattern 解決什麼問題

先看一個最小的例子。給一個 3 × 4 的矩陣，要你從左上角開始順時針螺旋走一圈，把元素依序輸出。沒有什麼「暴力解」和「最佳解」的差別：每個元素都得讀一次，O(mn) 就是下限。真正讓人失敗的是細節：走到最後一列要不要往回走？只剩一列或一行時會不會重複輸出？方向什麼時候轉？這類題目考的不是你知不知道某個技巧，而是你能不能把一段口語規則，翻譯成一份**每個邊界都對**的程式。

這一章把這類「實作題」分成三群。第一群是**矩陣操作**：座標換算、方向陣列、一層一層的邊界收縮、旋轉與轉置的座標公式。第二群是**原地模擬**：所有格子要「同時」依舊狀態更新，卻只能在原陣列上改，解法是把舊狀態與新狀態編碼進同一格（狀態編碼），或借用矩陣的一部分當作記錄區。第三群是**解析**：把字串依照文法切成 token（詞元，有意義的最小單位），再用遞迴下降（recursive descent）、有限狀態機（finite state machine）或 stack 處理巢狀結構。

這三群看似無關，其實共用同一套工作方式：**先把規則寫成精確的不變式或文法，再把程式拆成小函式，每個小函式都能單獨測試**。以 L5 的標準來看，這類題目看的是你能否在不依賴「靈光一閃」的情況下，寫出結構清楚、邊界正確、可以逐步驗證的程式；面試官也常在你寫完後追問「如果規則改一條呢」，結構清楚的程式只需要改一個函式。

本章的核心題（54、48、73、36、289）是矩陣與原地模擬的標準形；難題（65、68、591、726、770）則是解析與複雜模擬：狀態機驗證數字格式、排版規則、標籤的巢狀驗證、化學式的括號倍數，以及最完整的多項式計算機。

## 29.2 辨識訊號

| 題目特徵 | 為什麼是本章的技巧 | 本章哪一題 |
|---|---|---|
| 「螺旋順序」「一圈一圈」輸出或填入 | 用四個邊界變數或「第 k 層」描述外框，每走完一邊收縮一個邊界 | 核心題 1（54） |
| 「旋轉 90 度」「轉置」「鏡射」，要求原地 | 每種變換都是座標公式；原地做法是轉置＋反轉，或四格一組循環交換 | 核心題 2（48） |
| 依某格的值去改整列、整行，且要 O(1) 空間 | 借用第一列與第一行當作標記區，處理順序要保護標記 | 核心題 3（73） |
| 列、行、九宮格的約束檢查 | 每格同時屬於三個群組，用 `(r // 3) * 3 + c // 3` 算出群組編號，hash set 或 bitmask 記錄 | 核心題 4（36） |
| 「所有格子同時更新」而且要原地 | 新值依賴鄰居的舊值，用位元同時存舊狀態與新狀態 | 核心題 5（289） |
| 驗證某種格式（數字、日期、識別字） | 規則可以畫成有限狀態機，每個字元觸發一次狀態轉移 | 難題 1（65） |
| 一長串排版或遊戲規則，沒有最佳化 | 拆成「分組」「單組處理」「特例」三個小函式，各自測試 | 難題 2（68） |
| 有開頭與結尾的配對結構（標籤、括號） | 用 stack 記錄尚未關閉的開頭，遇到結尾就和 stack 頂端比對 | 難題 3（591） |
| 括號後面帶倍數、可以巢狀 | 每一層括號一個計數器，關閉時乘上倍數再併入上一層 | 難題 4（726） |
| 有優先順序的運算式（+、−、×、括號） | 依優先順序寫文法，一個優先層級一個遞迴函式 | 難題 5（770） |

一個實用的反向檢查：如果題目有明確的最佳化目標（「最少幾步」「最大總和」），矩陣只是載體，真正的 pattern 通常是 BFS（第 15 章）、DP（第 22 章）或 binary search（第 8 章）；本章處理的是「沒有最佳化、只要求照規則做對」的那一類。

## 29.3 矩陣模板：座標、方向陣列與邊界收縮

**座標慣例**。全章固定用 `(r, c)` 表示「第 r 列、第 c 行」，r 往下增加，c 往右增加；矩陣大小是 m 列 n 行。這和數學的 (x, y) 正好相反，混用是最常見的錯誤來源，所以面試一開始就說清楚「我用 row、column」。四個常用的換算：

- **攤平索引**：`i = r * n + c`，反過來 `r, c = divmod(i, n)`。把二維格子當成一維陣列處理時（例如 binary search 整個矩陣、Union-Find 的節點編號）就靠它。
- **對角線**：同一條主對角線（左上到右下）上 `r − c` 相同，同一條反對角線上 `r + c` 相同。N-Queens（第 19 章難題 1）就用這兩個值判斷衝突。
- **區塊編號**：9 × 9 數獨的 3 × 3 區塊編號是 `(r // 3) * 3 + c // 3`。
- **旋轉與鏡射**：順時針轉 90 度把 `(r, c)` 送到 `(c, n − 1 − r)`；轉置是 `(c, r)`；左右鏡射是 `(r, n − 1 − c)`。

**方向陣列**。把「上下左右」寫成一個 list，比寫四段 if 更短，也更不容易漏。順時針排列 `右、下、左、上` 的好處是「右轉」只要 `d = (d + 1) % 4`，「左轉」是 `(d + 3) % 4`，「迴轉」是 `(d + 2) % 4`。也可以直接對向量做旋轉：在 `(r, c)` 座標下，順時針轉 90 度是 `(dr, dc) → (dc, −dr)`。八方向（含斜角）用兩層迴圈產生，排除 `(0, 0)`。

**邊界收縮**。螺旋、一圈一圈處理的題目，有兩種等價的描述方式。第一種是四個邊界變數 `top、bottom、left、right`，每走完一條邊就把對應的邊界往內收一格（核心題 1 用這種）。第二種是「第 k 層」：第 k 層的外框是 `top = k、bottom = m − 1 − k、left = k、right = n − 1 − k`，每條邊取**半開區間**（每條邊不含終點，終點由下一條邊負責），四條邊剛好不重複地拼成一圈；只剩一列或一行時要特判，因為半開的四條邊在那時會漏掉或重複。

```python
DIRS4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]            # 右、下、左、上（順時針）
DIRS8 = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]


def neighbors(r: int, c: int, m: int, n: int, dirs=DIRS4):
    """產生 (r, c) 在 m × n 範圍內的鄰居。"""
    for dr, dc in dirs:
        nr, nc = r + dr, c + dc
        if 0 <= nr < m and 0 <= nc < n:
            yield nr, nc


def ring(m: int, n: int, k: int) -> list[tuple[int, int]]:
    """第 k 層外框的座標，從左上角開始順時針；每條邊是半開區間。"""
    top, left, bottom, right = k, k, m - 1 - k, n - 1 - k
    if top > bottom or left > right:
        return []
    if top == bottom:                                  # 只剩一列
        return [(top, c) for c in range(left, right + 1)]
    if left == right:                                  # 只剩一行
        return [(r, left) for r in range(top, bottom + 1)]
    out = [(top, c) for c in range(left, right)]              # 上邊：不含右上角
    out += [(r, right) for r in range(top, bottom)]           # 右邊：不含右下角
    out += [(bottom, c) for c in range(right, left, -1)]      # 下邊：不含左下角
    out += [(r, left) for r in range(bottom, top, -1)]        # 左邊：不含左上角
    return out


# 方向：右轉一次等於向量順時針轉 90 度
for d, (dr, dc) in enumerate(DIRS4):
    assert DIRS4[(d + 1) % 4] == (dc, -dr)
assert len(DIRS8) == 8 and (0, 0) not in DIRS8
assert sorted(neighbors(0, 0, 3, 3)) == [(0, 1), (1, 0)]
assert len(list(neighbors(1, 1, 3, 3, DIRS8))) == 8
# 攤平索引與還原
assert all(divmod(r * 7 + c, 7) == (r, c) for r in range(5) for c in range(7))
# 旋轉公式：轉四次回到原位
n = 5
for r in range(n):
    for c in range(n):
        p = (r, c)
        for _ in range(4):
            p = (p[1], n - 1 - p[0])
        assert p == (r, c)
# 所有層的外框剛好覆蓋每一格一次
for m in range(1, 7):
    for n in range(1, 7):
        cells = [cell for k in range((min(m, n) + 1) // 2) for cell in ring(m, n, k)]
        assert sorted(cells) == [(r, c) for r in range(m) for c in range(n)]
assert ring(3, 4, 0)[:5] == [(0, 0), (0, 1), (0, 2), (0, 3), (1, 3)]
assert ring(3, 4, 1) == [(1, 1), (1, 2)]               # 中間只剩一列
print("all tests passed")
```

**不變式**。四個邊界變數的寫法維持一件事：「`top..bottom` × `left..right` 這個矩形裡的格子，恰好是還沒輸出的格子」。走完上邊就 `top += 1`，走完右邊就 `right -= 1`，不變式保持；當 `top > bottom` 或 `left > right` 時矩形為空，結束。分層的寫法維持「第 0 到 k − 1 層都已處理」，總層數是 `(min(m, n) + 1) // 2`，最後一層可能退化成一列、一行或一格。兩種寫法說到底都一樣：**每一步之後，剩下要處理的區域仍然是一個矩形**，這就是邊界收縮。

**為什麼最後的測試覆蓋所有 m、n 組合**。矩陣題的 bug 幾乎都出在 1 × n、m × 1、1 × 1、奇數邊長這些退化情況，而它們在手寫測試裡最容易被忘記。像上面那樣「對所有小尺寸檢查覆蓋性」，只需要三行，卻能一次抓到所有越界與重複，面試時說出「我會對 1 到 6 的所有尺寸檢查」也很加分。

## 29.4 原地修改：狀態編碼

很多矩陣題要求「所有格子同時更新」：新值依賴鄰居的**舊值**。最簡單的做法是開一份複本，從複本讀、往原陣列寫，O(mn) 額外空間。題目要求 O(1) 額外空間時，困難在於：一旦某格被改成新值，它的鄰居就讀不到舊值了。解法是讓每一格在過渡期間**同時記住舊值與新值**，全部算完後再統一換成新值。常見的四種編碼方式：

| 編碼方式 | 作法 | 前提 | 例題 |
|---|---|---|---|
| 位元打包 | 低位元存舊值、高位元存新值；讀舊值用 `x & mask`，最後 `x >>= bits` | 值域有界、可以放進同一個整數 | 核心題 5（289） |
| 值域外的標記 | 把「待處理」標成值域外的值（`-1`、`'#'`、`None`），最後再改成真正的新值 | 值域外確實有空間可用 | 130 Surrounded Regions（第 15 章核心題 5） |
| 正負號標記 | 用負號記錄「這個位置被看過」，值的大小保持不變 | 值全為正 | 41 First Missing Positive（第 4 章難題 1） |
| 借用矩陣的一部分當記錄區 | 用第一列、第一行記錄「整行／整列要清除」，另外用一個變數補救重疊的角落 | 記錄區本身的資訊可以先保存下來 | 核心題 3（73） |

以位元打包為例。假設每格的值在 `[0, 1024)`，要把每格同時換成「它與上下左右鄰居的最大值」。新值也在同一個範圍，所以可以把新值放在第 10 位元以上：`grid[r][c] |= new << 10`。之後任何鄰居要讀這一格的舊值，都用 `grid[r][c] & 1023`，不受高位元影響。全部算完後，每格右移 10 位元就只剩新值。

```python
import random

BITS = 10
MASK = (1 << BITS) - 1                                # 舊值存在低 10 位元


def max_filter_inplace(grid: list[list[int]]) -> None:
    """原地把每格換成它與上下左右鄰居（舊值）的最大值，值域 [0, 1024)。"""
    m, n = len(grid), len(grid[0])
    for r in range(m):
        for c in range(n):
            best = grid[r][c] & MASK
            for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < m and 0 <= nc < n:
                    best = max(best, grid[nr][nc] & MASK)   # 只讀舊值
            grid[r][c] |= best << BITS                      # 新值放高位元
    for r in range(m):
        for c in range(n):
            grid[r][c] >>= BITS                             # 統一換成新值


def max_filter_copy(grid):
    m, n = len(grid), len(grid[0])
    old = [row[:] for row in grid]
    for r in range(m):
        for c in range(n):
            cand = [old[r][c]] + [old[r + dr][c + dc] for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))
                                  if 0 <= r + dr < m and 0 <= c + dc < n]
            grid[r][c] = max(cand)


g = [[1, 0, 0], [0, 0, 0], [0, 0, 5]]
max_filter_inplace(g)
assert g == [[1, 1, 0], [1, 0, 5], [0, 5, 5]]
g = [[7]]
max_filter_inplace(g)
assert g == [[7]]                                     # 1 × 1：沒有鄰居
for _ in range(300):
    m, n = random.randint(1, 5), random.randint(1, 5)
    a = [[random.randint(0, 1023) for _ in range(n)] for _ in range(m)]
    b = [row[:] for row in a]
    max_filter_inplace(a)
    max_filter_copy(b)
    assert a == b
print("all tests passed")
```

**正確性的關鍵**是「每次讀取都只讀舊值的那幾個位元」。不論鄰居已經被處理過（高位元有新值）還是還沒（高位元是 0），`& MASK` 都得到舊值，所以處理順序不影響結果。這個想法在核心題 5 會變成兩個位元的版本：bit 0 是這一代的狀態，bit 1 是下一代的狀態。如果值域沒有上界（例如任意大的整數），位元打包就不適用，要改用其他編碼，或老實地用一列大小的緩衝區（每次只保留上一列的舊值，空間 O(n)）。

## 29.5 模擬題的寫法：拆成小函式、逐步驗證

模擬題沒有演算法上的難點，失敗的原因幾乎都是「一次寫一大坨程式，寫完才第一次執行」。面試時比較穩的寫法是**由下往上拆成小函式**：最底層是「狀態的表示」與「一步的轉移」，中間是「依指令跑完」，最上層才是題目要的輸出。每一層寫完就用一兩個手算的小例子驗證，再往上疊。這樣面試官追問「如果規則改了」，你只需要改一個函式；有 bug 時也能很快定位到哪一層。

以一個小模擬為例：機器人在 grid 上，`'#'` 是牆，從 `(0, 0)` 面向右出發，指令 `L`／`R` 是原地左轉／右轉，`F` 是往前一格（前方是牆或邊界就不動）。我們把它拆成四個函式：`turn` 只處理方向、`forward` 只處理一步移動、`run` 依序執行指令、`render` 把狀態畫出來方便除錯。模擬步數很大時（例如指令重複 10⁹ 次），再加一層**週期偵測**：狀態空間有限，重複執行同一個轉移必定進入循環，記下每個狀態第一次出現的步數，找到循環後直接跳過整數個週期。

```python
DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]             # 右、下、左、上


def turn(d: int, cmd: str) -> int:
    return (d + 1) % 4 if cmd == "R" else (d + 3) % 4


def forward(grid: list[str], r: int, c: int, d: int) -> tuple[int, int]:
    nr, nc = r + DIRS[d][0], c + DIRS[d][1]
    if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]) and grid[nr][nc] != "#":
        return nr, nc
    return r, c                                       # 撞牆或出界：原地不動


def run(grid: list[str], cmds: str, state=(0, 0, 0)) -> tuple[int, int, int]:
    r, c, d = state
    for cmd in cmds:
        if cmd == "F":
            r, c = forward(grid, r, c, d)
        else:
            d = turn(d, cmd)
    return r, c, d


def render(grid: list[str], r: int, c: int, d: int) -> str:
    rows = [list(row) for row in grid]
    rows[r][c] = ">v<^"[d]
    return "\n".join("".join(row) for row in rows)


def run_repeated(step, state, times: int):
    """把 state = step(state) 執行 times 次；狀態有限時用週期偵測跳過重複。"""
    seen = {}
    i = 0
    while i < times:
        if state in seen:
            cycle = i - seen[state]
            times = i + (times - i) % cycle           # 跳過整數個週期
            seen.clear()
            if i >= times:
                break
        seen[state] = i
        state = step(state)
        i += 1
    return state


grid = ["...#",
        ".#..",
        "...."]
# 第一層：單一函式各自驗證
assert turn(0, "R") == 1 and turn(0, "L") == 3 and turn(3, "R") == 0
assert forward(grid, 0, 2, 0) == (0, 2)               # 前方是牆
assert forward(grid, 0, 0, 3) == (0, 0)               # 前方出界
assert forward(grid, 0, 0, 1) == (1, 0)
# 第二層：組合起來
assert run(grid, "FF") == (0, 2, 0)
assert run(grid, "FFF") == (0, 2, 0)                  # 第三步撞牆
assert run(grid, "RFFLFFF") == (2, 3, 0)
assert run(grid, "") == (0, 0, 0)
assert render(grid, 0, 2, 0).splitlines()[0] == "..>#"
# 第三層：重複執行 10^9 次，結果與直接模擬一致
step = lambda s: run(grid, "FRF", s)
for times in range(40):
    direct = (0, 0, 0)
    for _ in range(times):
        direct = step(direct)
    assert run_repeated(step, (0, 0, 0), times) == direct
assert run_repeated(step, (0, 0, 0), 10**9) == step(run_repeated(step, (0, 0, 0), 10**9 - 1))
print("all tests passed")
```

**逐步驗證的四個習慣**。第一，**先寫狀態的表示**，例如 `(r, c, d)`，並決定它是否可 hash（週期偵測需要）。第二，**每個函式至少一個手算的例子**，特別是「什麼都不做」的情況（撞牆、空指令）。第三，**寫一個 render 或 dump**：小 grid 印出來一眼就看得出錯，面試時也能邊印邊和面試官對答案。第四，**大步數一定先問有沒有週期**：957 Prison Cells After N Days 這類題目的步數到 10⁹，直接模擬會超時，但狀態只有 2⁸ 種，必然很快進入循環。上面的 `run_repeated` 是通用的週期跳躍函式，它的正確性來自「轉移是確定的，所以同一個狀態之後的序列完全相同」。

## 29.6 解析模板：tokenizer、遞迴下降、狀態機與 stack

解析題的輸入是一段有文法的字串。直接一邊讀字元一邊寫 if 往往會變成義大利麵，比較穩的做法是分兩層：**tokenizer**（詞法分析）先把字串切成 token，例如 `"12*(x+3)"` 切成 `12、*、(、x、+、3、)`；**parser**（語法分析）再依照文法處理 token 序列。分層的好處是每一層都很小：tokenizer 只關心「一個數字到哪裡結束」，parser 只關心「乘法要先算」。

**遞迴下降**。把文法依優先順序寫成規則，每條規則一個函式，函式之間互相呼叫。以四則運算為例：

```text
expr   := term   (('+' | '-') term)*        加減：優先順序最低，最外層
term   := factor (('*' | '/') factor)*      乘除：比加減高一層
factor := ('+' | '-') factor                單元正負號
        | NUMBER
        | '(' expr ')'                      括號：回到最外層，形成遞迴
```

每條規則的函式都遵守同一個約定：**從目前位置 `pos` 開始，吃掉一段符合這條規則的 token，回傳它的值，並把 `pos` 移到這段之後**。`expr` 先呼叫 `term` 拿到第一項，然後只要下一個 token 是 `+` 或 `-`，就再吃一個 `term` 合併；因為 `term` 內部已經把乘除吃完，乘法自然比加法先算。左結合（`8 - 3 - 2 = 3`）來自 `while` 迴圈由左往右累積，而不是遞迴到右邊。

```python
import random


def tokenize(s: str) -> list[str]:
    """把運算式切成 token：多位數整數、運算子、括號；空白略過。"""
    tokens, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch.isspace():
            i += 1
        elif ch.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            tokens.append(s[i:j])
            i = j
        elif ch in "+-*/()":
            tokens.append(ch)
            i += 1
        else:
            raise ValueError(f"unexpected character {ch!r} at {i}")
    return tokens


def evaluate(s: str) -> int:
    tokens, pos = tokenize(s), 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def eat(expected=None):
        nonlocal pos
        tok = peek()
        if tok is None or (expected is not None and tok != expected):
            raise ValueError(f"expected {expected!r}, got {tok!r}")
        pos += 1
        return tok

    def expr():
        value = term()
        while peek() in ("+", "-"):
            value = value + term() if eat() == "+" else value - term()
        return value

    def term():
        value = factor()
        while peek() in ("*", "/"):
            if eat() == "*":
                value *= factor()
            else:
                d = factor()
                q = abs(value) // abs(d)                # 向零取整
                value = q if (value >= 0) == (d > 0) else -q
        return value

    def factor():
        tok = peek()
        if tok in ("+", "-"):
            eat()
            return factor() if tok == "+" else -factor()
        if tok == "(":
            eat("(")
            value = expr()
            eat(")")
            return value
        return int(eat())

    result = expr()
    if pos != len(tokens):
        raise ValueError(f"trailing token {tokens[pos]!r}")
    return result


assert tokenize(" 12 *(3+45) ") == ["12", "*", "(", "3", "+", "45", ")"]
assert evaluate("1 + 2 * 3") == 7                     # 乘法優先
assert evaluate("8 - 3 - 2") == 3                     # 左結合
assert evaluate("(1 + 2) * 3") == 9
assert evaluate("-(2 + 3) * -2") == 10                # 單元負號
assert evaluate("7 / -2") == -3                       # 向零取整
assert evaluate("42") == 42
for bad in ["1 +", "(1 + 2", "1 2", ")"]:
    try:
        evaluate(bad)
        assert False, bad
    except (ValueError, IndexError):
        pass


def gen(depth):
    if depth == 0 or random.random() < 0.3:
        return str(random.randint(0, 20))
    op = random.choice("+-*")
    left, right = gen(depth - 1), gen(depth - 1)
    return f"({left} {op} {right})" if random.random() < 0.5 else f"{left} {op} {right}"


for _ in range(500):
    e = gen(4)
    assert evaluate(e) == eval(e), e
print("all tests passed")
```

**有限狀態機**。當文法沒有巢狀（沒有括號、沒有遞迴），只是「先可以有什麼、接著必須有什麼」，用狀態機更直接：狀態代表「到目前為止讀到了什麼樣的前綴」，每讀一個字元查表轉移到下一個狀態，查不到就拒絕，讀完時看是否停在接受狀態。表格式的寫法（`dict` 或 list of dict）比一堆 if 好讀，加規則時只要加一列。下面驗證「以逗號分隔的整數清單」，例如 `"12,-3,45"`：

```python
def char_class(ch: str) -> str:
    if "0" <= ch <= "9":
        return "digit"
    if ch in "+-":
        return "sign"
    if ch == ",":
        return "comma"
    return "other"


# 狀態：0 = 期待一個新數字的開頭，1 = 剛讀到正負號，2 = 正在讀數字（接受）
TRANSITIONS = {
    0: {"sign": 1, "digit": 2},
    1: {"digit": 2},
    2: {"digit": 2, "comma": 0},
}
ACCEPT = {2}


def is_int_list(s: str) -> bool:
    state = 0
    for ch in s:
        state = TRANSITIONS[state].get(char_class(ch))
        if state is None:
            return False
    return state in ACCEPT


assert is_int_list("12,-3,45")
assert is_int_list("7")
assert not is_int_list("")                            # 空字串停在狀態 0
assert not is_int_list("1,,2")
assert not is_int_list("1,")                          # 結尾停在狀態 0
assert not is_int_list("+")
assert not is_int_list("1 2")
print("all tests passed")
```

**用 stack 處理巢狀**。遞迴下降其實就是用系統的呼叫堆疊記住「外層做到哪裡」。也可以自己管理一個 stack：遇到「開頭」（左括號、開始標籤）就把目前的上下文 push 進去，開一個新的空上下文；遇到「結尾」就 pop 出外層上下文，把內層的結果合併回去。394 Decode String（`"3[a2[c]]"` 展開成 `"accaccacc"`）是最小的例子：上下文是「目前累積的字串」與「這層的重複次數」。

```python
def decode_string(s: str) -> str:
    stack = []                                        # 每層存 (外層已累積的字串, 這層的倍數)
    cur, num = [], 0
    for ch in s:
        if ch.isdigit():
            num = num * 10 + int(ch)
        elif ch == "[":
            stack.append(("".join(cur), num))         # 保存外層上下文，開新的一層
            cur, num = [], 0
        elif ch == "]":
            outer, k = stack.pop()
            cur = [outer + "".join(cur) * k]          # 內層結果乘上倍數，併回外層
        else:
            cur.append(ch)
    return "".join(cur)


assert decode_string("3[a2[c]]") == "accaccacc"
assert decode_string("2[ab]3[c]d") == "ababcccd"
assert decode_string("10[x]") == "x" * 10             # 多位數倍數
assert decode_string("abc") == "abc"
assert decode_string("") == ""
print("all tests passed")
```

**何時用哪一種**。

| 結構 | 首選 | 理由 | 本章題目 |
|---|---|---|---|
| 沒有巢狀的格式驗證 | 狀態機 | 每個狀態就是「前綴的種類」，表格清楚、可以逐字元串流處理 | 難題 1（65） |
| 配對與巢狀，但沒有優先順序 | stack | 只需要記住「還沒關閉的開頭」 | 難題 3（591）、難題 4（726） |
| 有運算子優先順序 | 遞迴下降 | 一個優先層級一個函式，文法直接對應程式 | 難題 5（770）、第 10 章難題 4（224） |
| 巢狀很深（可能超過遞迴上限） | 顯式 stack | Python 預設遞迴上限約 1000 層 | 591 的 F4 |

## 29.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 混用 `(x, y)` 與 `(r, c)` | 非正方形矩陣上越界，或轉出來的方向是鏡像 | 一開始就宣告「r 是列、c 是行」，`m = len(grid)`、`n = len(grid[0])` |
| 螺旋走完上、右兩邊後沒檢查邊界 | 只剩一列或一行時元素被輸出兩次 | 走下邊前檢查 `top <= bottom`，走左邊前檢查 `left <= right` |
| 原地更新時讀到已經被改過的值 | 「同時更新」的結果依掃描順序而不同 | 用狀態編碼保留舊值，或先完整掃描記錄再統一修改 |
| 借用第一列／第一行當記錄區卻先處理它們 | 記錄被覆蓋，整個矩陣被清成 0 | 先用額外變數存下第一行（或第一列）原本的狀態，最後才處理記錄區 |
| 旋轉時座標公式寫反 | 轉成逆時針，或只有正方形的對角線正確 | 用一個 3 × 3 的例子手算 `(0, 0)` 和 `(0, 2)` 會去哪裡 |
| tokenizer 只讀一個字元的數字 | `"12"` 被當成 1 和 2 | 數字、名稱一律用內層 while 讀到結束 |
| 遞迴下降忘了檢查是否吃完所有 token | `"1 2"` 被當成 1 | parse 結束後確認 `pos == len(tokens)` |
| 狀態機忘了「讀完時是否在接受狀態」 | `"1e"`、`"1,"` 被判成合法 | 結尾一定 `return state in ACCEPT` |
| 負數除法或取整方向錯 | `7 / -2` 得到 -4 | Python 的 `//` 向下取整；題目要向零取整時用絕對值相除再補符號 |
| 模擬大步數時直接跑 | 10⁹ 步超時 | 狀態有限就做週期偵測，跳過整數個週期 |

## 核心題 1｜54. Spiral Matrix｜Medium

### 題目

給一個 m 列 n 行的整數矩陣 `matrix`，從左上角出發，以順時針螺旋的順序走過所有元素：先往右走完第一列，再往下走完最右行，再往左走完最後一列，再往上，然後進入內圈重複，直到每個元素都恰好被走過一次。回傳走過的元素序列。限制：`1 <= m, n <= 10`，元素在 `-100` 到 `100` 之間。

- 範例 1：`matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]`，回傳 `[1, 2, 3, 6, 9, 8, 7, 4, 5]`。
- 範例 2：`matrix = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]`，回傳 `[1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]`。
- 範例 3（邊界，只有一列）：`matrix = [[1, 2, 3]]`，回傳 `[1, 2, 3]`，不能再往回走。
- 範例 4（邊界，只有一行）：`matrix = [[1], [2], [3]]`，回傳 `[1, 2, 3]`。

### 思路

這題沒有比 O(mn) 更快的做法，因為每個元素都要輸出。所謂的「暴力解」是直接模擬一個人在格子上走：維持目前位置與方向（右、下、左、上），用一個 `visited` 矩陣記錄走過的格子，每一步先試著往前，前方出界或已經走過就右轉。這個做法正確而且很通用，代價是 O(mn) 的額外空間，以及每一步都要做邊界與 visited 檢查。

更乾淨的做法是 29.3 節的邊界收縮。用四個變數 `top、bottom、left、right` 描述「還沒走過的矩形」，不變式是：**這個矩形裡的格子恰好就是還沒輸出的格子**。每一輪依序做四件事：沿 `top` 列從 `left` 走到 `right`，然後 `top += 1`（這一列已經用完）；沿 `right` 行從 `top` 走到 `bottom`，然後 `right -= 1`；沿 `bottom` 列從 `right` 走回 `left`，然後 `bottom -= 1`；沿 `left` 行從 `bottom` 走回 `top`，然後 `left += 1`。這樣不需要 visited，也不需要方向變數。

唯一的陷阱在後兩步。走完上邊與右邊之後，矩形可能已經變空：例如只剩一列時，`top += 1` 之後 `top > bottom`，如果照樣走下邊，就會把同一列倒著再輸出一次。所以走下邊前要檢查 `top <= bottom`，走左邊前要檢查 `left <= right`。前兩步不需要檢查，因為迴圈條件 `top <= bottom and left <= right` 剛確認過矩形非空；走完上邊後右邊的 `range(top, bottom + 1)` 若為空，自然什麼都不做。

```text
matrix（3 × 4）：
      c=0  c=1  c=2  c=3
r=0    1    2    3    4
r=1    5    6    7    8
r=2    9   10   11   12

輪次  動作                         輸出            之後的邊界 (top, bottom, left, right)
 1    上邊 r=0, c=0..3             1 2 3 4         top=1        → (1, 2, 0, 3)
      右邊 c=3, r=1..2             8 12            right=2      → (1, 2, 0, 2)
      top<=bottom ✓ 下邊 r=2, c=2..0  11 10 9      bottom=1     → (1, 1, 0, 2)
      left<=right ✓ 左邊 c=0, r=1..1  5            left=1       → (1, 1, 1, 2)
 2    上邊 r=1, c=1..2             6 7             top=2        → (2, 1, 1, 2)
      右邊 c=2, r=2..1             （空）          right=1      → (2, 1, 1, 1)
      top<=bottom ✗ 跳過下邊（否則會再輸出一次 6）
      left<=right ✓ 左邊 c=1, r 從 bottom=1 倒序到 top=2 → range(1, 1, -1) 為空  left=2
結束  top > bottom
輸出：1 2 3 4 8 12 11 10 9 5 6 7
```

第 2 輪是整個演算法最關鍵的地方：內圈只剩一列 `6 7`，上邊把它輸出後 `top = 2 > bottom = 1`，矩形已經空了。若沒有 `top <= bottom` 的檢查，下邊會沿 r = 1 從 c = 1 走回 c = 1……實際上會再輸出一次 6，造成重複。這就是為什麼面試官特別喜歡拿 3 × 4、1 × n、m × 1 來測這題。

### 解法

```python
import random

DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def spiral_order(matrix: list[list[int]]) -> list[int]:
    res = []
    top, bottom, left, right = 0, len(matrix) - 1, 0, len(matrix[0]) - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):              # 上邊：左 → 右
            res.append(matrix[top][c])
        top += 1
        for r in range(top, bottom + 1):              # 右邊：上 → 下
            res.append(matrix[r][right])
        right -= 1
        if top <= bottom:                             # 還有列，才走下邊
            for c in range(right, left - 1, -1):
                res.append(matrix[bottom][c])
            bottom -= 1
        if left <= right:                             # 還有行，才走左邊
            for r in range(bottom, top - 1, -1):
                res.append(matrix[r][left])
            left += 1
    return res


def spiral_order_walk(matrix: list[list[int]]) -> list[int]:
    """方向陣列模擬：前方出界或走過就右轉。"""
    m, n = len(matrix), len(matrix[0])
    seen = [[False] * n for _ in range(m)]
    r = c = d = 0
    res = []
    for _ in range(m * n):
        res.append(matrix[r][c])
        seen[r][c] = True
        nr, nc = r + DIRS[d][0], c + DIRS[d][1]
        if not (0 <= nr < m and 0 <= nc < n) or seen[nr][nc]:
            d = (d + 1) % 4
            nr, nc = r + DIRS[d][0], c + DIRS[d][1]
        r, c = nr, nc
    return res


assert spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [1, 2, 3, 6, 9, 8, 7, 4, 5]
assert spiral_order([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]) == [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]
assert spiral_order([[1, 2, 3]]) == [1, 2, 3]
assert spiral_order([[1], [2], [3]]) == [1, 2, 3]
assert spiral_order([[7]]) == [7]
for _ in range(300):
    m, n = random.randint(1, 7), random.randint(1, 7)
    mat = [[r * n + c for c in range(n)] for r in range(m)]
    out = spiral_order(mat)
    assert sorted(out) == list(range(m * n))          # 每個元素恰好一次
    assert out == spiral_order_walk(mat)
print("all tests passed")
```

### 複雜度與邊界

兩種寫法時間都是 O(mn)，每個元素輸出一次。邊界收縮版的額外空間是 O(1)（不計輸出）；方向模擬版需要 O(mn) 的 `seen`，若允許修改輸入，可以把走過的格子改成值域外的標記（例如 `101`）省下這份空間。邊界情況：1 × n、m × 1、1 × 1 都靠兩個 if 檢查避免重複；m ≠ n 時最後剩下的是一列或一行，取決於 m 和 n 哪個較小；方向模擬版在最後一格之後也會「右轉」並算出一個新位置，但迴圈恰好結束，不會被讀取。

### Follow-up

> [!question]- F1. 如果要逆時針螺旋（先往下走左邊那一行）呢？
> 逆時針、從左上角先往下，恰好等於**轉置矩陣的順時針螺旋**：轉置把「往下走第 0 行」變成「往右走第 0 列」，其餘各邊依此對應。所以答案是 `spiral_order([list(col) for col in zip(*matrix)])`，O(mn) 時間、O(mn) 額外空間。若要 O(1) 空間，直接改邊界收縮的順序：先走左邊（`top..bottom`）並 `left += 1`，再走下邊（`left..right`）並 `bottom -= 1`，然後在 `left <= right` 時走右邊、在 `top <= bottom` 時走上邊。注意兩個檢查的條件也跟著交換。

> [!question]- F2. 反過來，給 n，產生一個依螺旋順序填入 1 到 n² 的 n × n 矩陣（59. Spiral Matrix II）？
> 同一個邊界收縮迴圈，只是把「讀」換成「寫」：維持一個計數器 `k`，每走過一格就 `mat[r][c] = k; k += 1`。正方形時兩個 if 檢查只在 n 為奇數的最中心那格才有作用。時間 O(n²)，除了輸出外 O(1) 空間。
> ```python
> def generate_matrix(n):
>     mat = [[0] * n for _ in range(n)]
>     top, bottom, left, right, k = 0, n - 1, 0, n - 1, 1
>     while top <= bottom and left <= right:
>         for c in range(left, right + 1): mat[top][c] = k; k += 1
>         top += 1
>         for r in range(top, bottom + 1): mat[r][right] = k; k += 1
>         right -= 1
>         if top <= bottom:
>             for c in range(right, left - 1, -1): mat[bottom][c] = k; k += 1
>             bottom -= 1
>         if left <= right:
>             for r in range(bottom, top - 1, -1): mat[r][left] = k; k += 1
>             left += 1
>     return mat
> ```

> [!question]- F3. 如果是從矩陣中間某一格 (r0, c0) 開始往外螺旋，走到矩陣外也繼續，直到走過所有格子（885. Spiral Matrix III）？
> 這時沒有「收縮」的邊界可用，改成方向模擬：步長的序列是 1, 1, 2, 2, 3, 3, …（往右 1、往下 1、往左 2、往上 2、往右 3……），每走一步檢查是否在矩陣內，在的話才記錄。每兩次轉向步長加一。最遠要走到離起點 max(m, n) 的距離，總步數是 O(max(m, n)²)，記錄 mn 個格子後停止。這題提醒我們：邊界收縮適合「由外往內」，「由內往外」用步長序列模擬比較自然。

> [!question]- F4. 如果只要螺旋順序的第 k 個元素（矩陣很大，不想全部走完）呢？
> 先跳過整層：第 i 層的外框高 `h = m − 2i`、寬 `w = n − 2i`，格數是 `h · w − (h − 2)(w − 2)`（當 h 或 w 為 1 時就是 `h · w`）。前 t 層合計 `m·n − (m − 2t)(n − 2t)` 格，所以可以用一次迴圈 O(min(m, n))，或解二次不等式 O(1)，找出第 k 個元素所在的層 i 與層內的偏移 `off`。接著在這一層的四條邊上依長度 `w − 1、h − 1、w − 1、h − 1`（半開區間，見 29.3 節 `ring`）扣掉 `off`，就能算出座標。總時間 O(min(m, n))，不需要產生任何序列。

> [!question]- F5. 如果要把螺旋走訪做成 iterator，每次呼叫 next() 回傳下一個元素呢？
> 把迴圈的狀態搬進物件：目前的四個邊界、正在走的邊（0 到 3）、這條邊上的位置。用 Python 的 generator 最簡單，把 `spiral_order` 中的 `res.append(x)` 換成 `yield x` 即可，狀態自動保存在 generator 的 frame 裡，每次 `next()` 均攤 O(1)，額外空間 O(1)。若要用其他語言寫成顯式的類別，關鍵是在「切換到下一條邊」時同時做邊界收縮與兩個空矩形檢查，並把「矩形已空」視為迭代結束；hasNext() 只需要檢查 `top <= bottom and left <= right`，加上目前這條邊是否還有元素。

## 核心題 2｜48. Rotate Image｜Medium

### 題目

給一個 n × n 的整數矩陣（一張影像），把它**原地**順時針旋轉 90 度：不能另外配置一個 n × n 的矩陣，只能在原陣列上交換元素。限制：`1 <= n <= 20`，元素在 `-1000` 到 `1000` 之間。

- 範例 1：`[[1, 2, 3], [4, 5, 6], [7, 8, 9]]` 旋轉後是 `[[7, 4, 1], [8, 5, 2], [9, 6, 3]]`。
- 範例 2：`[[1, 2], [3, 4]]` 旋轉後是 `[[3, 1], [4, 2]]`。
- 範例 3（邊界）：`[[5]]` 旋轉後不變。
- 範例 4：4 × 4 的 `1..16` 依列填入，旋轉後第一列是 `[13, 9, 5, 1]`，最後一列是 `[16, 12, 8, 4]`。

### 思路

先寫出座標公式。順時針轉 90 度時，原本的第 r 列會變成新矩陣的倒數第 r 行，原本的第 c 行會變成新矩陣的第 c 列，所以 `(r, c)` 被送到 `(c, n − 1 − r)`，等價地 `new[r][c] = old[n − 1 − c][r]`。用一個新矩陣照公式填，O(n²) 時間、O(n²) 空間，這是暴力解；它的問題只是違反了原地的要求。

直接原地照公式寫會出錯：把 `old[r][c]` 搬到 `(c, n − 1 − r)` 時，那一格原本的值被覆蓋了。關鍵觀察是：**旋轉是一個排列，它由長度 4 的循環組成**。`(r, c) → (c, n−1−r) → (n−1−r, n−1−c) → (n−1−c, r) → (r, c)`，四個位置互相輪替，只要用一個暫存變數，就能把這四個值一起轉一格。對每一層、每條邊上除了最後一格之外的位置做一次四格循環，就涵蓋了所有循環。

另一個更好記的做法是**兩次鏡射的合成**：先沿主對角線轉置（`(r, c) → (c, r)`），再把每一列左右反轉（`(r, c) → (r, n − 1 − c)`）。合成起來 `(r, c) → (c, r) → (c, n − 1 − r)`，正好是順時針旋轉。兩個步驟都是簡單的成對交換，各 O(n²)，空間 O(1)。面試時建議寫這個版本，並能說出四格循環作為第二種解法。

```text
原矩陣                 轉置（沿主對角線交換）       每列左右反轉
 1  2  3  4             1  5  9 13                 13  9  5  1
 5  6  7  8      →      2  6 10 14         →       14 10  6  2
 9 10 11 12             3  7 11 15                 15 11  7  3
13 14 15 16             4  8 12 16                 16 12  8  4

四格循環（第 0 層，偏移 j = 0..2）：
j=0： (0,0) → (0,3) → (3,3) → (3,0) → (0,0)     值  1 → 4 的位置，4 → 16 的位置，16 → 13 的位置，13 → 1 的位置
j=1： (0,1) → (1,3) → (3,2) → (2,0) → (0,1)     值  2、8、15、9 輪替
j=2： (0,2) → (2,3) → (3,1) → (1,0) → (0,2)     值  3、12、14、5 輪替
第 1 層只有 j=1：(1,1) → (1,2) → (2,2) → (2,1)  值  6、7、11、10 輪替
```

第 0 層的每條邊有 4 格，但只做 j = 0、1、2 三次，因為 j = 3 的位置 `(0, 3)` 已經是 j = 0 循環的一員。一般地，第 i 層做 `j = i .. n − 2 − i`，共 `n − 1 − 2i` 次；所有層加起來 `Σ (n − 1 − 2i)` 個循環 × 4 格 = n² 減去中心格（n 為奇數時），剛好每一格被搬動一次。

### 解法

```python
import random


def rotate(matrix: list[list[int]]) -> None:
    """轉置 + 每列反轉，原地順時針旋轉 90 度。"""
    n = len(matrix)
    for r in range(n):
        for c in range(r + 1, n):                     # 只交換上三角，避免換兩次又換回來
            matrix[r][c], matrix[c][r] = matrix[c][r], matrix[r][c]
    for row in matrix:
        row.reverse()


def rotate_cycles(matrix: list[list[int]]) -> None:
    """一層一層做四格循環。"""
    n = len(matrix)
    for i in range(n // 2):
        for j in range(i, n - 1 - i):
            tmp = matrix[i][j]
            matrix[i][j] = matrix[n - 1 - j][i]                   # 左 → 上
            matrix[n - 1 - j][i] = matrix[n - 1 - i][n - 1 - j]   # 下 → 左
            matrix[n - 1 - i][n - 1 - j] = matrix[j][n - 1 - i]   # 右 → 下
            matrix[j][n - 1 - i] = tmp                            # 上 → 右


def rotated_copy(matrix):
    return [list(row) for row in zip(*matrix[::-1])]


a = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
rotate(a)
assert a == [[7, 4, 1], [8, 5, 2], [9, 6, 3]]
a = [[1, 2], [3, 4]]
rotate_cycles(a)
assert a == [[3, 1], [4, 2]]
a = [[5]]
rotate(a)
assert a == [[5]]
a = [[r * 4 + c + 1 for c in range(4)] for r in range(4)]
rotate(a)
assert a[0] == [13, 9, 5, 1] and a[-1] == [16, 12, 8, 4]
for _ in range(200):
    n = random.randint(1, 7)
    m = [[random.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    x, y = [row[:] for row in m], [row[:] for row in m]
    rotate(x)
    rotate_cycles(y)
    assert x == y == rotated_copy(m)
    for _ in range(3):
        rotate(x)
    assert x == m                                     # 轉四次回到原樣
print("all tests passed")
```

### 複雜度與邊界

兩種寫法都是 O(n²) 時間、O(1) 額外空間。轉置版每格最多被交換兩次（轉置一次、反轉一次），四格循環版每格恰好被寫一次，常數略小。邊界情況：n = 1 時兩個迴圈都不做事；n 為奇數時中心格 `(n // 2, n // 2)` 不動，四格循環的 `range(n // 2)` 自然跳過它；轉置時內層必須從 `r + 1` 開始，若從 0 開始，每對元素會被交換兩次，等於沒轉置。`zip(*matrix[::-1])` 是一行的非原地寫法，適合當測試的對照組，但它配置了新矩陣，不符合題目要求。

### Follow-up

> [!question]- F1. 如果要逆時針旋轉 90 度，或旋轉 180 度呢？
> 逆時針是 `(r, c) → (n − 1 − c, r)`，分解成「先轉置、再上下反轉（把列的順序反過來）」，或「先每列左右反轉、再轉置」。180 度是 `(r, c) → (n − 1 − r, n − 1 − c)`，等於上下反轉再左右反轉，不需要轉置，也可以把矩陣攤平後整個反轉。三者都是 O(n²) 時間、O(1) 空間。若題目給的是旋轉 k 次 90 度，先取 `k % 4`，再套用對應的版本，最多做一次轉置加一次反轉。

> [!question]- F2. 如果矩陣不是正方形（m × n），要順時針旋轉呢？
> 旋轉後形狀變成 n × m，不可能在同一個二維 list 裡原地完成，只能建立新矩陣 `res[c][m − 1 − r] = A[r][c]`，O(mn) 時間與空間。若資料存在一個長度 mn 的一維陣列裡（列優先），「原地」旋轉就是對索引做一個排列，可以沿著排列的循環搬動，需要額外的位元記錄哪些位置已處理（O(mn) 個位元），或用「只從每個循環的最小索引出發」的技巧做到 O(1) 額外空間（樸素版本要沿循環檢查，最差 O((mn)²) 時間；文獻中有更快的 in-place transposition 演算法）。面試中說出「非正方形時原地旋轉等價於 in-place transposition，是一個不簡單的排列問題」就足夠。

> [!question]- F3. 怎麼判斷矩陣 B 是否能由 A 旋轉若干次得到（1886. Determine Whether Matrix Can Be Obtained By Rotation）？
> 最直接是把 A 原地旋轉最多四次，每次比較是否等於 B，O(n²) 時間。也可以不修改 A：用四個布林旗標同時檢查四種旋轉，對每個 `(r, c)` 比較 `B[r][c]` 是否等於 `A[r][c]`、`A[n−1−c][r]`、`A[n−1−r][n−1−c]`、`A[c][n−1−r]`，任一不相等就把對應旗標設為 False，一次掃描 O(n²)、O(1) 空間，最後回傳四個旗標的 or。

> [!question]- F4. 如果不是整張轉 90 度，而是把每一層外框沿著外框循環移動 k 格（1914. Cyclically Rotating a Grid）呢？
> 每一層獨立處理：用 29.3 節的 `ring(m, n, i)` 取出第 i 層的座標序列，長度 L；把這些位置的值讀成一個 list，旋轉 `k % L` 格，再依同樣的座標順序寫回。k 可能到 10⁹，取模是關鍵。總時間 O(mn)，額外空間是最外層的長度 O(m + n)。這也說明了為什麼把「外框座標」寫成獨立的函式很有用：它同時服務螺旋、旋轉外框與很多「一圈一圈」的題目。

> [!question]- F5. 如果影像非常大，存在磁碟上，每次只能讀寫一個 B × B 的方塊呢？
> 把矩陣切成 (n / B)² 個方塊，旋轉在方塊層級也是一個「四塊循環」：方塊 `(I, J)` 被送到 `(J, N − 1 − I)`，N = n / B。每次讀入四個互相輪替的方塊，在記憶體中把每塊各自旋轉 90 度，再寫到下一個位置。每個方塊只被讀寫一次，I/O 次數 O((n / B)²)，是最佳的；若逐格交換，四格循環中的四個位置幾乎都落在不同方塊，I/O 會變成 O(n²)。這個想法和矩陣轉置的 cache-oblivious 分塊演算法相同。

## 核心題 3｜73. Set Matrix Zeroes｜Medium

### 題目

給一個 m × n 的整數矩陣，如果某個元素是 0，就把它所在的**整列**與**整行**都設為 0。所有判斷都依據原始矩陣（新產生的 0 不會再擴散），並且要原地修改。題目進一步要求只用 O(1) 額外空間。限制：`1 <= m, n <= 200`，元素在 `-2³¹` 到 `2³¹ − 1` 之間（所以不能拿某個整數當「值域外的標記」）。

- 範例 1：`[[1, 1, 1], [1, 0, 1], [1, 1, 1]]` 變成 `[[1, 0, 1], [0, 0, 0], [1, 0, 1]]`。
- 範例 2：`[[1, 2, 3, 4], [5, 0, 7, 8], [0, 6, 9, 1]]` 變成 `[[0, 0, 3, 4], [0, 0, 0, 0], [0, 0, 0, 0]]`。原始的 0 在 `(1, 1)` 與 `(2, 0)`，所以第 1、2 列與第 0、1 行要清除。
- 範例 3（邊界）：`[[0]]` 不變；`[[5]]` 不變。
- 範例 4（邊界，0 在第一列）：`[[1, 0, 3]]` 變成 `[[0, 0, 0]]`。

### 思路

最天真的做法是掃描時一看到 0 就立刻清掉整列整行，但這會讓新產生的 0 在後面被當成原始的 0，繼續擴散，最後整個矩陣都變成 0。所以必須**先完整記錄、再統一修改**。最直接的記錄方式是開一份複本（O(mn) 空間）；更好的是只記「哪些列要清」「哪些行要清」，用兩個集合或兩個布林陣列，O(m + n) 空間，再掃一次把 `r in rows or c in cols` 的格子設為 0。

要做到 O(1) 空間，關鍵觀察是：「第 c 行要不要清」這個資訊只需要一個位元，而矩陣的第 0 列剛好有 n 個位置，可以拿來記；「第 r 列要不要清」則記在第 0 行。也就是說，看到 `matrix[r][c] == 0` 時，令 `matrix[r][0] = 0`（標記第 r 列）與 `matrix[0][c] = 0`（標記第 c 行）。這些標記本來就該是 0（因為該列、該行最後都會被清掉），所以寫進去不會破壞答案。

剩下兩個細節。第一，`matrix[0][0]` 同時位於第 0 列和第 0 行，只能代表其中一個；我們讓它代表「第 0 列要清」，另外用一個變數 `first_col_zero` 記錄「第 0 行原本有沒有 0」。第二，**處理順序**：標記區（第 0 列、第 0 行）必須最後才清，否則會把記錄先抹掉。從右下角往左上角處理每一列，並且每一列先處理 c ≥ 1 的格子、最後才依 `first_col_zero` 處理第 0 行，就能保證讀標記時它們還沒被改動。

```text
原始矩陣（0 在 (1,1) 與 (2,0)）
       c=0 c=1 c=2 c=3
r=0     1   2   3   4
r=1     5   0   7   8
r=2     0   6   9   1

步驟 1：first_col_zero = 第 0 行是否有 0 → (2,0) 是 0 → True
步驟 2：掃描 c >= 1 的格子，遇到 0 就在第 0 列、第 0 行做標記
        (1,1) = 0 → matrix[1][0] = 0（第 1 列要清），matrix[0][1] = 0（第 1 行要清）
       c=0 c=1 c=2 c=3
r=0     1  [0]  3   4        ← 第 0 列存「行標記」，matrix[0][0] 存「第 0 列標記」
r=1    [0]  0   7   8
r=2    [0]  6   9   1        ← 第 0 行存「列標記」（(2,0) 原本就是 0）

步驟 3：從 r = 2 往上，每列先處理 c = 3..1，最後處理 c = 0
  r=2：matrix[2][0] = 0 → c=3..1 全設 0；first_col_zero → matrix[2][0] = 0
  r=1：matrix[1][0] = 0 → c=3..1 全設 0；matrix[1][0] = 0
  r=0：matrix[0][0] = 1，看行標記：c=3 (4) 保留、c=2 (3) 保留、c=1 (0) 設 0；
       first_col_zero → matrix[0][0] = 0
結果
r=0     0   0   3   4
r=1     0   0   0   0
r=2     0   0   0   0
```

為什麼 r = 0 要最後處理：第 0 列存的是行標記，如果先處理第 0 列（例如 `matrix[0][0]` 是 0 而把第 0 列全清掉），所有行標記都會變成 0，下面每一列都會被誤清。從下往上處理，第 0 列在最後才被改，讀標記時它還是步驟 2 結束時的樣子。

### 解法

```python
import random


def set_zeroes(matrix: list[list[int]]) -> None:
    """O(1) 額外空間：第 0 列記行標記，第 0 行記列標記，matrix[0][0] 代表第 0 列。"""
    m, n = len(matrix), len(matrix[0])
    first_col_zero = any(matrix[r][0] == 0 for r in range(m))
    for r in range(m):
        for c in range(1, n):
            if matrix[r][c] == 0:
                matrix[r][0] = 0
                matrix[0][c] = 0
    for r in range(m - 1, -1, -1):                    # 由下往上：第 0 列最後才改
        for c in range(n - 1, 0, -1):
            if matrix[r][0] == 0 or matrix[0][c] == 0:
                matrix[r][c] = 0
        if first_col_zero:
            matrix[r][0] = 0


def set_zeroes_sets(matrix: list[list[int]]) -> None:
    """O(m + n) 空間版本，作為對照。"""
    rows = {r for r, row in enumerate(matrix) for v in row if v == 0}
    cols = {c for row in matrix for c, v in enumerate(row) if v == 0}
    for r, row in enumerate(matrix):
        for c in range(len(row)):
            if r in rows or c in cols:
                row[c] = 0


def run(f, mat):
    mat = [row[:] for row in mat]
    f(mat)
    return mat


assert run(set_zeroes, [[1, 1, 1], [1, 0, 1], [1, 1, 1]]) == [[1, 0, 1], [0, 0, 0], [1, 0, 1]]
assert run(set_zeroes, [[1, 2, 3, 4], [5, 0, 7, 8], [0, 6, 9, 1]]) == [[0, 0, 3, 4], [0, 0, 0, 0], [0, 0, 0, 0]]
assert run(set_zeroes, [[0]]) == [[0]]
assert run(set_zeroes, [[5]]) == [[5]]
assert run(set_zeroes, [[1, 0, 3]]) == [[0, 0, 0]]
assert run(set_zeroes, [[1], [0], [2]]) == [[0], [0], [0]]
assert run(set_zeroes, [[0, 1], [1, 1]]) == [[0, 0], [0, 1]]      # matrix[0][0] 是 0
for _ in range(1000):
    m, n = random.randint(1, 5), random.randint(1, 5)
    mat = [[random.choice([0, 1, 2, -3]) for _ in range(n)] for _ in range(m)]
    assert run(set_zeroes, mat) == run(set_zeroes_sets, mat)
print("all tests passed")
```

### 複雜度與邊界

時間 O(mn)：三次掃描，每次 O(mn)。額外空間 O(1)，只有 `first_col_zero` 一個變數。邊界情況：`matrix[0][0]` 原本就是 0 時，它代表「第 0 列要清」，而第 0 行由 `first_col_zero` 負責（此時也是 True），兩者都正確；只有一列時，第 0 列同時是資料與標記，從下往上的順序讓它最後才被改；只有一行時內層迴圈不執行，全靠 `first_col_zero`；元素可能是任意 32 位元整數，所以不能用「把要清的格子先改成某個特殊值」這種做法，這也是題目刻意設計的限制。

### Follow-up

> [!question]- F1. 為什麼不能一看到 0 就立刻清掉，或把待清除的格子先標成特殊值？
> 立刻清會讓新產生的 0 在後續掃描中被誤認為原始的 0，繼續擴散；例如 `[[0, 1], [1, 1]]` 立刻清第 0 列與第 0 行之後，掃到 `(0, 1)` 又會把第 1 行清掉，答案變成全 0。標成特殊值（例如 `None`）可以避免擴散：遇到原始 0 就把同列同行的非 0 格子標成 `None`，最後把 `None` 換成 0，空間 O(1)，但每個 0 都要掃一整列加一整行，時間 O(mn · (m + n))；而且如果值域是所有整數，在強型別語言裡沒有值域外的值可用。用第 0 列、第 0 行當標記區，是同時做到 O(mn) 時間與 O(1) 空間的標準做法。

> [!question]- F2. 如果不修改矩陣，只要回傳「最後會有幾個 0」呢？
> 統計原本含 0 的列數 `zr` 與行數 `zc`，答案是 `zr · n + zc · m − zr · zc`（列和行交叉處被算了兩次，用排容扣掉）。一次掃描 O(mn)，空間 O(m + n) 存哪些列和行含 0；若只能 O(1) 空間，可以先掃一次每一列得到 `zr`（每列是否含 0 不需存下來），再逐行掃描得到 `zc`，各 O(mn)。

> [!question]- F3. 如果矩陣很大，只能一列一列地串流讀取（讀兩遍），並且一列一列輸出結果呢？
> 第一遍串流記錄「哪些行含 0」（長度 n 的位元陣列）；列是否含 0 在第二遍讀到那一列時就能當場判斷，不需要記。第二遍讀第 r 列時：若這列含 0，輸出全 0；否則輸出原列，但把標記為含 0 的行設為 0。記憶體 O(n)，兩遍 I/O 各 O(mn)。如果只能讀一遍，就必須先把所有含 0 的列緩存起來或延後輸出，因為後面的列可能讓前面某一行需要清除，資訊上無法避免。

> [!question]- F4. 如果有很多次更新（把某格設為 0）與查詢（某格現在是不是 0），要怎麼支援？
> 不要真的清整列整行，改成**延遲處理**：維護兩個集合 `zero_rows`、`zero_cols`，更新 `(r, c)` 時把 r 和 c 分別加入，O(1)；查詢 `(r, c)` 時回傳 `r in zero_rows or c in zero_cols or 原值 == 0`，O(1)。若之後要輸出整個矩陣，再一次性套用，O(mn)。這是資料結構設計（第 27 章）中常見的「懶標記」想法：把昂貴的批次修改轉成查詢時的判斷。

> [!question]- F5. 如果規則改成「0 只會把同列、同行中距離 ≤ k 的格子清成 0」呢？
> 每個原始 0 影響的是一個十字形範圍，無法再用一個位元記錄整列。可以對每一列做一維的 difference array（第 7 章）：原始 0 在 `(r, c)` 時，在第 r 列的 `[c − k, c + k]` 區間加 1，在第 c 行的 `[r − k, r + k]` 區間加 1；各自做 prefix sum，計數大於 0 的格子就要清成 0。時間 O(mn)，空間 O(mn)（或逐列、逐行處理時 O(m + n) 加上一份標記）。這說明了原題的 O(1) 解法依賴「影響範圍是整列整行」這個特殊結構。

## 核心題 4｜36. Valid Sudoku｜Medium

### 題目

給一個 9 × 9 的數獨盤面，每格是 `'1'` 到 `'9'` 的字元或代表空格的 `'.'`。判斷**目前已填的數字**是否合法：每一列中沒有重複的數字、每一行中沒有重複的數字、九個 3 × 3 的區塊中也沒有重複的數字。空格不需要檢查，也不要求這個盤面有解。限制：盤面固定 9 × 9。

- 範例 1：一個部分填寫、且三種約束都沒有衝突的盤面，回傳 `True`（見解法中的 `valid_board`）。
- 範例 2：把上面盤面的 `(0, 0)` 改成 `'3'`，但第 0 列已經有 `'3'`（在 `(0, 2)`），回傳 `False`。
- 範例 3：把 `(1, 1)` 改成 `'9'`，而左上區塊在 `(2, 2)` 已經有 `'9'`，列與行都沒有衝突，只有區塊衝突，回傳 `False`。
- 範例 4（邊界）：全部是 `'.'` 的盤面，回傳 `True`。

### 思路

最直接的做法是做三輪檢查：9 列各檢查一次、9 行各檢查一次、9 個區塊各檢查一次，每次用一個 set 看有沒有重複，總共讀 3 × 81 格。這已經是 O(1)（盤面大小固定），但寫起來有三段相似的迴圈，區塊那段的索引特別容易寫錯。

更好的寫法是**一次掃描，每格同時更新三個群組**。每個格子 `(r, c)` 恰好屬於三個群組：第 r 列、第 c 行、第 `b = (r // 3) * 3 + c // 3` 個區塊。準備 27 個 set（或 27 個 9 位元的 bitmask），看到數字 d 時，若 d 已在這三個 set 的任一個中就回傳 False，否則加入。這個寫法的核心是區塊編號公式：`r // 3` 是區塊在第幾「列帶」（0 到 2），`c // 3` 是第幾「行帶」，攤平成 0 到 8。

用 bitmask 時，數字 d 對應位元 `1 << d`，檢查 `mask & bit`、加入 `mask |= bit`。bitmask 的好處是空間小、可以 O(1) 複製與合併，在需要回溯的 37 Sudoku Solver（第 19 章難題 2）中，「某格還能填哪些數字」就是 `~(row | col | box)` 的位元運算。

```text
區塊編號 b = (r // 3) * 3 + c // 3
        c: 0 1 2   3 4 5   6 7 8
r = 0      0 0 0 | 1 1 1 | 2 2 2
r = 1      0 0 0 | 1 1 1 | 2 2 2
r = 2      0 0 0 | 1 1 1 | 2 2 2
           ------+-------+------
r = 3      3 3 3 | 4 4 4 | 5 5 5
r = 4..5   ...
           ------+-------+------
r = 6..8   6 6 6 | 7 7 7 | 8 8 8

範例 3 的掃描過程（只列出前幾個數字，左上區塊 = 第 0 塊）
格子    數字  列集合 rows[r]   行集合 cols[c]   區塊集合 boxes[b]      結果
(0,2)   3     rows[0]={3}      cols[2]={3}      boxes[0]={3}           加入
(1,1)   9     rows[1]={9}      cols[1]={9}      boxes[0]={3,9}         加入
(1,4)   8     rows[1]={9,8}    cols[4]={8}      boxes[1]={8}           加入
 ...
(2,2)   9     rows[2]={7}      cols[2]={3}      boxes[0]={3,9} 已有 9 ✗ 回傳 False
```

區塊衝突是三種衝突中最容易被漏掉的：`(1, 1)` 和 `(2, 2)` 不同列也不同行，只有區塊編號都是 0。一次掃描的寫法讓三種檢查完全對稱，不會因為少寫一段迴圈而漏掉。

### 解法

```python
import random


def is_valid_sudoku(board: list[list[str]]) -> bool:
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    for r in range(9):
        for c in range(9):
            d = board[r][c]
            if d == ".":
                continue
            b = (r // 3) * 3 + c // 3
            if d in rows[r] or d in cols[c] or d in boxes[b]:
                return False
            rows[r].add(d)
            cols[c].add(d)
            boxes[b].add(d)
    return True


def is_valid_sudoku_bits(board: list[list[str]]) -> bool:
    rows, cols, boxes = [0] * 9, [0] * 9, [0] * 9
    for r in range(9):
        for c in range(9):
            if board[r][c] == ".":
                continue
            bit = 1 << int(board[r][c])
            b = (r // 3) * 3 + c // 3
            if (rows[r] | cols[c] | boxes[b]) & bit:
                return False
            rows[r] |= bit
            cols[c] |= bit
            boxes[b] |= bit
    return True


def brute(board):
    groups = [[(r, c) for c in range(9)] for r in range(9)]
    groups += [[(r, c) for r in range(9)] for c in range(9)]
    groups += [[(br + i, bc + j) for i in range(3) for j in range(3)]
               for br in (0, 3, 6) for bc in (0, 3, 6)]
    for g in groups:
        ds = [board[r][c] for r, c in g if board[r][c] != "."]
        if len(ds) != len(set(ds)):
            return False
    return True


rows_txt = ["..3......", "....8..23", "7.9.2....", "2.45.....", "5..8..23.",
            "8.12.4..7", "...6789.2", "67.91.3.5", "912..5..."]
valid_board = [list(row) for row in rows_txt]
assert is_valid_sudoku(valid_board) and is_valid_sudoku_bits(valid_board)
bad_row = [row[:] for row in valid_board]
bad_row[0][0] = "3"                                   # 與 (0,2) 同列重複
assert not is_valid_sudoku(bad_row) and not is_valid_sudoku_bits(bad_row)
bad_box = [row[:] for row in valid_board]
bad_box[1][1] = "9"                                   # 與 (2,2) 同區塊重複
assert not is_valid_sudoku(bad_box) and not is_valid_sudoku_bits(bad_box)
assert is_valid_sudoku([["."] * 9 for _ in range(9)])
solved = [[str((r * 3 + r // 3 + c) % 9 + 1) for c in range(9)] for r in range(9)]
assert is_valid_sudoku(solved)                        # 完整解也合法
for _ in range(2000):
    board = [[random.choice("123456789") if random.random() < 0.12 else "." for _ in range(9)]
             for _ in range(9)]
    assert is_valid_sudoku(board) == is_valid_sudoku_bits(board) == brute(board)
print("all tests passed")
```

### 複雜度與邊界

盤面固定 81 格，所以時間與空間都是 O(1)；若推廣到 N² × N² 的盤面（N = 3 是標準數獨），時間 O(N⁴)（每格一次），空間 O(N⁴)（3N² 個群組，每個最多 N² 個數字），bitmask 版本則是 3N² 個 N² 位元的整數。邊界情況：全空盤面直接回傳 True；完整填滿的合法解也是 True；題目保證字元只有 `'1'` 到 `'9'` 與 `'.'`，若輸入可能有 `'0'` 或其他字元，應該在加入前驗證；區塊編號必須是 `(r // 3) * 3 + c // 3`，常見的錯誤是寫成 `r // 3 + c // 3`，那會讓第 1 塊和第 3 塊撞號。

### Follow-up

> [!question]- F1. 合法（valid）和有解（solvable）有什麼不同？能舉一個合法但無解的盤面嗎？
> 合法只檢查已填數字之間沒有衝突；有解則要求存在一種填滿的方式。例如第 0 列填了 `1` 到 `8`、只剩 `(0, 8)` 是空格，而第 8 行的其他某格已經有 `9`：沒有任何重複，所以合法；但 `(0, 8)` 只能填 9，卻和同行的 9 衝突，所以無解。判斷有解需要回溯搜尋（37 Sudoku Solver，第 19 章難題 2），最差是指數時間；一般化的 N² × N² 數獨判斷有解是 NP-complete。

> [!question]- F2. 如果要回報所有衝突的格子（例如在 UI 上把它們標紅）呢？
> 不要在第一個衝突就回傳，而是用 `dict` 記錄每個群組中每個數字出現的位置：`seen[("row", r, d)]`、`seen[("col", c, d)]`、`seen[("box", b, d)]` 各是一個位置清單。掃描完後，所有長度 ≥ 2 的清單裡的格子都是衝突格，取聯集回傳。時間仍是 O(81)，空間 O(81)。這個做法也自然支援「同一格同時有列衝突與區塊衝突」的情況，不會重複回報。

> [!question]- F3. 如果是一個數獨 App，使用者會不斷填入與刪除數字，每次操作後要立即知道盤面是否合法呢？
> 為 27 個群組各維護一個長度 10 的計數陣列 `count[group][d]`，再維護一個全域變數 `conflicts` = 所有計數中「超過 1 的部分」的總和。填入 d 時，對三個群組各把 `count` 加一，若加完後 ≥ 2 就 `conflicts += 1`；刪除時反向操作。每次操作 O(1)，盤面合法若且唯若 `conflicts == 0`。這是把「每次重新掃描」改成「增量維護」的標準做法，和第 27 章的資料結構設計題同一個思路。

> [!question]- F4. 如果盤面是 16 × 16（4 × 4 區塊）或一般的 N² × N² 呢？
> 只需要把常數參數化：區塊編號改成 `(r // N) * N + c // N`，群組數量是 N²，數字範圍是 1 到 N²（16 × 16 常用 `1-9` 加 `A-G`，要先把字元映射成整數）。bitmask 需要 N² + 1 個位元，16 × 16 時 17 位元，仍然是一個機器字。時間 O(N⁴)，也就是每格一次。

> [!question]- F5. 如果盤面已經填滿，要驗證它是不是一個正確的解呢？
> 在合法檢查之外，還要確認沒有空格；滿盤又沒有重複時，每個群組的 9 個數字必然是 1 到 9 各一次（鴿籠原理），所以不需要另外檢查「每個數字都出現」。用 bitmask 的話可以更直接：每個群組的最終 mask 都必須等於 `0b1111111110`（位元 1 到 9 全為 1）。O(81) 時間。

## 核心題 5｜289. Game of Life｜Medium

### 題目

給一個 m × n 的 0／1 矩陣代表細胞，1 是活、0 是死。每個細胞有 8 個鄰居（上下左右與四個斜角，超出邊界的不算）。下一代的狀態由這一代**同時**決定：活細胞若活鄰居少於 2 個就死亡、有 2 或 3 個就存活、超過 3 個就死亡；死細胞若恰好有 3 個活鄰居就復活，否則維持死亡。請把矩陣**原地**更新成下一代。限制：`1 <= m, n <= 25`。

- 範例 1：`[[0, 1, 0], [0, 1, 0], [0, 1, 0]]`（直的三格）變成 `[[0, 0, 0], [1, 1, 1], [0, 0, 0]]`（橫的三格），這是週期 2 的振盪子。
- 範例 2：`[[1, 1], [1, 1]]` 不變：每個活細胞都有 3 個活鄰居。
- 範例 3（邊界）：`[[1]]` 變成 `[[0]]`：唯一的細胞沒有鄰居，死於孤立。
- 範例 4：`[[1, 1, 1], [1, 1, 1], [1, 1, 1]]` 變成 `[[1, 0, 1], [0, 0, 0], [1, 0, 1]]`：角落有 3 個鄰居存活，邊上有 5 個、中心有 8 個，都過度擁擠而死。

### 思路

暴力解是複製一份舊盤面，從複本讀鄰居、往原盤面寫新狀態，O(mn) 時間、O(mn) 額外空間。直接在原盤面上邊算邊改是錯的：先算出 `(0, 1)` 死亡並寫成 0，輪到 `(1, 0)` 數鄰居時就少算了一個活鄰居，結果依掃描順序而不同，違反了「同時更新」。

關鍵觀察是每格只有 1 位元的資訊，而一個整數有很多位元可用，這正是 29.4 節的位元打包：**bit 0 存這一代的狀態，bit 1 存下一代的狀態**。第一輪掃描時，數鄰居一律讀 `board[r][c] & 1`（只看這一代），算出下一代若為活就 `board[r][c] |= 2`；第二輪把每格右移一位 `board[r][c] >>= 1`，下一代就成為這一代。因為第一輪從頭到尾都沒有動過 bit 0，所以處理順序完全不影響結果。

四種編碼值有清楚的意義：`0b00` 死→死、`0b01` 活→死、`0b10` 死→活、`0b11` 活→活。規則也可以化簡成一句：**下一代為活，若且唯若「活鄰居 = 3」，或「自己活著且活鄰居 = 2」**。用這個化簡寫程式，比照抄四條規則更不容易出錯。

```text
範例 1：直的三格（直條振盪子）
這一代            每格的活鄰居數        第一輪後（bit1 = 下一代，bit0 = 這一代）
0 1 0             2 1 2                 0b00 0b01 0b00   →   0 1 0
0 1 0             3 2 3                 0b10 0b11 0b10   →   2 3 2
0 1 0             2 1 2                 0b00 0b01 0b00   →   0 1 0

逐格判斷（只讀 bit0）：
(0,1) 活，鄰居 1 個 → 死，編碼 0b01
(1,0) 死，鄰居 3 個 → 生，編碼 0b10
(1,1) 活，鄰居 2 個 → 活，編碼 0b11
(0,0) 死，鄰居 2 個 → 死，編碼 0b00

第二輪：每格 >>= 1
0 0 0
1 1 1
0 0 0
```

注意 `(1, 0)` 數鄰居時，`(0, 1)` 已經被處理成 `0b01`（下一代會死），但 `& 1` 讀到的仍然是 1，所以 `(1, 0)` 正確地數到 3 個活鄰居而復活。如果沒有編碼、直接寫成 0，`(1, 0)` 只會數到 2 個，振盪子就被破壞了。

### 解法

```python
import random

NEIGHBORS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]


def game_of_life(board: list[list[int]]) -> None:
    m, n = len(board), len(board[0])
    for r in range(m):
        for c in range(n):
            live = 0
            for dr, dc in NEIGHBORS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < m and 0 <= nc < n:
                    live += board[nr][nc] & 1          # 只讀這一代
            if live == 3 or (live == 2 and board[r][c] & 1):
                board[r][c] |= 2                       # 下一代為活
    for r in range(m):
        for c in range(n):
            board[r][c] >>= 1


def next_gen_copy(board):
    m, n = len(board), len(board[0])
    res = [[0] * n for _ in range(m)]
    for r in range(m):
        for c in range(n):
            live = sum(board[r + dr][c + dc] for dr, dc in NEIGHBORS
                       if 0 <= r + dr < m and 0 <= c + dc < n)
            if board[r][c] == 1:
                res[r][c] = 1 if live in (2, 3) else 0
            else:
                res[r][c] = 1 if live == 3 else 0
    return res


def step(board):
    board = [row[:] for row in board]
    game_of_life(board)
    return board


assert step([[0, 1, 0], [0, 1, 0], [0, 1, 0]]) == [[0, 0, 0], [1, 1, 1], [0, 0, 0]]
assert step(step([[0, 1, 0], [0, 1, 0], [0, 1, 0]])) == [[0, 1, 0], [0, 1, 0], [0, 1, 0]]
assert step([[1, 1], [1, 1]]) == [[1, 1], [1, 1]]
assert step([[1]]) == [[0]]
assert step([[1, 1, 1], [1, 1, 1], [1, 1, 1]]) == [[1, 0, 1], [0, 0, 0], [1, 0, 1]]
for _ in range(500):
    m, n = random.randint(1, 6), random.randint(1, 6)
    b = [[random.randint(0, 1) for _ in range(n)] for _ in range(m)]
    assert step(b) == next_gen_copy(b)
print("all tests passed")
```

### 複雜度與邊界

時間 O(mn)：每格看 8 個鄰居，常數 8。額外空間 O(1)，舊狀態與新狀態都存在原陣列的兩個位元中。邊界情況：1 × 1 的盤面沒有鄰居，活細胞必死；1 × n 的盤面每格最多 2 個鄰居，活細胞要恰好 2 個才能存活，死細胞永遠無法復活；第一輪中**一定要用 `& 1`** 讀鄰居與自己，直接比較 `board[r][c] == 1` 會在格子已經變成 `0b11` 時出錯；第二輪必須在第一輪全部結束後才開始，不能合併成一輪。

### Follow-up

> [!question]- F1. 如果盤面是無限大的（活細胞座標可以是任意整數）呢？
> 改用稀疏表示：只存活細胞的座標集合 `live`。下一代的計算是：對每個活細胞，把它 8 個鄰居的計數加一（用 `Counter`）；然後下一代 = `{p for p, k in cnt.items() if k == 3 or (k == 2 and p in live)}`。每一代時間 O(L)，L 是活細胞數，與盤面大小無關。這比固定大小的陣列更通用，也是實作上真正會用的方法。
> ```python
> from collections import Counter
> def next_gen_sparse(live):
>     cnt = Counter((r + dr, c + dc) for r, c in live
>                   for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)
>     return {p for p, k in cnt.items() if k == 3 or (k == 2 and p in live)}
> ```

> [!question]- F2. 如果盤面的上下、左右邊界相連（環面 torus）呢？
> 只要改鄰居的計算：`nr = (r + dr) % m`、`nc = (c + dc) % n`，不需要邊界檢查。位元編碼的原地做法完全不變，O(mn)。要注意 m 或 n 小於 3 時，同一個格子可能被當成多個方向的鄰居（例如 m = 1 時上下鄰居都是自己那一列），題目若有定義要照定義處理，通常是照樣重複計數。

> [!question]- F3. 如果盤面非常大，記憶體只放得下幾列（資料存在磁碟上，一列一列讀）呢？
> 下一代的第 r 列只依賴這一代的第 r − 1、r、r + 1 列，所以用一個大小為 3 列的滑動緩衝區：讀入第 r + 1 列後，就能算出並輸出第 r 列的下一代，然後丟掉第 r − 1 列。記憶體 O(n)，每列讀寫各一次。若連一列都放不下，就把每一列切成固定寬度的區段，區段間共享左右各一格的邊緣資料，原理相同。

> [!question]- F4. 如果要模擬 k 代，k 非常大（例如 10⁹）呢？
> 盤面大小固定時，狀態總數有限（2^(mn)），所以序列最終一定會進入循環。用 29.5 節的週期偵測：把每一代的盤面轉成 tuple（或位元整數）存入 `dict`，記錄第一次出現的代數，一旦重複就用 `(k − i) % 週期` 跳過剩下的整數個週期。實務上很多盤面會很快死光或變成穩定、週期 2 的圖形；最差情況下週期可能非常長，那時只能直接模擬 k 代，O(k · mn)。Hashlife 等演算法可以用 memoization 把大型重複結構的模擬加速到遠快於逐代計算，面試中提到名字與「把四分樹的子區塊快取起來」即可。

> [!question]- F5. 如果盤面大到要分散在多台機器上計算呢？
> 把盤面切成二維的區塊（tile），每台機器負責一塊。每一代開始前，相鄰的機器互相交換區塊邊緣的一圈格子（halo，又叫 ghost cells），之後每台機器就能獨立算出自己區塊的下一代。每代的通訊量是區塊周長，計算量是區塊面積，所以區塊越接近正方形，通訊與計算的比例越好。這是模擬類演算法（stencil computation）的標準平行化方式，同樣適用於熱傳導、影像濾波等「每格依鄰居更新」的問題。

## 難題 1｜65. Valid Number｜Hard

### 題目

給一個字串 `s`，判斷它是否是一個合法的數字。合法數字的定義如下：

- 一個**底數**，後面可以選擇性地接一個**指數部分**。
- 底數是**整數**或**小數**。整數是可選的正負號（`+` 或 `-`）加上至少一個數字。小數是可選的正負號，加上以下三種之一：「至少一個數字，接著 `.`」（例如 `3.`）、「至少一個數字，接著 `.`，再接至少一個數字」（例如 `3.14`）、「`.` 接著至少一個數字」（例如 `.5`）。
- 指數部分是 `e` 或 `E`，接著一個**整數**（可以有正負號，但必須至少一個數字，不能有小數點）。

字串只包含英文字母、數字、`+`、`-`、`.`，長度 1 到 20，不含空白。

- 範例 1：`"2"`、`"0089"`、`"-0.1"`、`"+3.14"`、`"4."`、`"-.9"`、`"2e10"`、`"-90E3"`、`"3e+7"`、`"53.5e93"` 都回傳 `True`。
- 範例 2：`"abc"`、`"1a"`、`"1e"`、`"e3"`、`"99e2.5"`、`"--6"`、`"-+3"`、`"95a54e53"` 都回傳 `False`。
- 範例 3（邊界）：`"."` 回傳 `False`（沒有任何數字）；`".e1"` 回傳 `False`（底數沒有數字）；`"+"` 回傳 `False`。
- 範例 4（邊界）：`"1E-0"` 回傳 `True`；`"6e6.5"` 回傳 `False`（指數不能有小數點）。

### 提示

> [!tip]- 提示 1
> 不要用 `float(s)`：它會接受 `"inf"`、`"nan"`、`"1_000"`、前後空白，這些都不合法。先把規則寫成「一個字元一個字元讀，每讀一個字元，目前讀過的前綴屬於哪一種狀態」。

> [!tip]- 提示 2
> 需要記住的資訊只有：有沒有讀過數字、有沒有讀過小數點、有沒有讀過 e、e 之後有沒有數字。正負號只能出現在開頭或緊接在 e 之後。

> [!tip]- 提示 3
> 把這些資訊組合成有限狀態機的 9 個狀態：開始、底數正負號、整數部分、「數字後的小數點」、「沒有數字的小數點」、小數部分、e、指數正負號、指數數字。接受狀態是整數部分、數字後的小數點、小數部分、指數數字。

### 詳解

**為什麼直覺做法不行**。很多人第一個想法是寫一長串 if：「如果是數字……如果是小數點，而且前面沒有小數點、也沒有 e……如果是 e，而且前面有數字……」。這可以寫對，但每加一條規則都要回頭檢查所有分支是否互相影響，面試時很容易漏掉像 `".e1"`（小數點後沒有數字就進入 e）或 `"1e+"`（e 的正負號後沒有數字）這種組合。另一個陷阱是 `float(s)` 或 `try: float(s)`，它接受的語言和題目不同。真正的問題是：**我們需要一個能證明「每一種前綴都被正確分類」的結構**。

**突破點：前綴的種類是有限的**。讀到一半時，未來還能接受什麼樣的字元，只取決於「目前前綴屬於哪一類」，而不是前綴的具體內容。例如 `"-12"` 和 `"7"` 屬於同一類（已經有整數部分，接下來可以接數字、小數點、e，或在此結束），`"-12."` 和 `"7."` 屬於另一類（可以接數字或 e，也可以結束），`"."` 和 `"-."` 又是另一類（必須接數字，不能結束）。把所有類別列出來就是 9 個狀態，把「這一類加上一個字元變成哪一類」寫成轉移表，這就是 29.6 節的有限狀態機。

**狀態與轉移**。字元先分成四類：`digit`、`sign`（`+-`）、`dot`、`exp`（`eE`），其他字元一律拒絕。

| 狀態 | 意義 | digit | sign | dot | exp | 接受？ |
|---|---|---|---|---|---|---|
| 0 | 開始 | 2 | 1 | 4 | | |
| 1 | 底數的正負號 | 2 | | 4 | | |
| 2 | 整數部分（至少一個數字） | 2 | | 3 | 6 | ✓ |
| 3 | 數字之後的小數點（如 `3.`） | 5 | | | 6 | ✓ |
| 4 | 沒有數字的小數點（如 `.`、`-.`） | 5 | | | | |
| 5 | 小數部分 | 5 | | | 6 | ✓ |
| 6 | 剛讀到 e | 8 | 7 | | | |
| 7 | 指數的正負號 | 8 | | | | |
| 8 | 指數的數字 | 8 | | | | ✓ |

**正確性**。每個狀態對應一個清楚的前綴集合，例如狀態 3 = 「可選正負號 + 至少一個數字 + 小數點」。驗證轉移表時只需要對每個狀態問兩個問題：「這個前綴加上某類字元後，屬於哪個集合？」與「這個前綴本身是不是完整的合法數字？」前者決定表格的每一格，後者決定接受狀態。狀態 4 和狀態 3 必須分開，因為 `"."` 不能結束也不能接 e，`"3."` 兩者都可以；狀態 6 和 7 必須分開，因為 e 之後可以接正負號，正負號之後不行。

```text
s = "-12.5e+3"
字元   類別    狀態轉移
 '-'   sign    0 → 1
 '1'   digit   1 → 2
 '2'   digit   2 → 2
 '.'   dot     2 → 3
 '5'   digit   3 → 5
 'e'   exp     5 → 6
 '+'   sign    6 → 7
 '3'   digit   7 → 8
結束：狀態 8 是接受狀態 → True

s = ".e1"
 '.'   dot     0 → 4
 'e'   exp     4 → （沒有轉移）→ False

s = "1e"
 '1'   digit   0 → 2
 'e'   exp     2 → 6
結束：狀態 6 不是接受狀態 → False
```

三個例子分別展示了三種結果：一路走到接受狀態、中途沒有轉移而拒絕、讀完但停在非接受狀態而拒絕。最後一種是最容易忘記的檢查：很多手寫的 if 版本會接受 `"1e"`，因為每個字元單獨看都沒有問題。

### 解法

```python
import random
import re

DIGITS = "0123456789"


def char_class(ch: str) -> str:
    if ch in DIGITS:
        return "digit"
    if ch in "+-":
        return "sign"
    if ch == ".":
        return "dot"
    if ch in "eE":
        return "exp"
    return "other"


TRANSITIONS = [
    {"digit": 2, "sign": 1, "dot": 4},                # 0 開始
    {"digit": 2, "dot": 4},                           # 1 底數正負號
    {"digit": 2, "dot": 3, "exp": 6},                 # 2 整數部分
    {"digit": 5, "exp": 6},                           # 3 數字後的小數點
    {"digit": 5},                                     # 4 沒有數字的小數點
    {"digit": 5, "exp": 6},                           # 5 小數部分
    {"digit": 8, "sign": 7},                          # 6 e
    {"digit": 8},                                     # 7 指數正負號
    {"digit": 8},                                     # 8 指數數字
]
ACCEPT = {2, 3, 5, 8}


def is_number(s: str) -> bool:
    state = 0
    for ch in s:
        state = TRANSITIONS[state].get(char_class(ch))
        if state is None:
            return False
    return state in ACCEPT


def is_number_flags(s: str) -> bool:
    """旗標版本：同一個語言，用四個布林變數表達狀態。"""
    seen_digit = seen_dot = seen_exp = False
    for i, ch in enumerate(s):
        if ch in DIGITS:
            seen_digit = True
        elif ch in "+-":
            if i > 0 and s[i - 1] not in "eE":       # 只能在開頭或緊接 e 之後
                return False
        elif ch == ".":
            if seen_dot or seen_exp:                  # 只能一個小數點，且不能在指數中
                return False
            seen_dot = True
        elif ch in "eE":
            if seen_exp or not seen_digit:            # e 前面必須有數字
                return False
            seen_exp = True
            seen_digit = False                        # e 後面必須重新有數字
        else:
            return False
    return seen_digit


VALID = ["2", "0089", "-0.1", "+3.14", "4.", "-.9", "2e10", "-90E3", "3e+7", "53.5e93", "1E-0"]
INVALID = ["abc", "1a", "1e", "e3", "99e2.5", "--6", "-+3", "95a54e53", ".", ".e1", "+", "6e6.5", "1e+", ""]
for s in VALID:
    assert is_number(s) and is_number_flags(s), s
for s in INVALID:
    assert not is_number(s) and not is_number_flags(s), s
REF = re.compile(r"[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?")
for _ in range(20000):
    s = "".join(random.choice("0123456789+-.eEa") for _ in range(random.randint(1, 7)))
    expect = REF.fullmatch(s) is not None
    assert is_number(s) == expect == is_number_flags(s), s
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，每個字元一次查表；空間 O(1)，狀態機是固定大小的表格。邊界情況：空字串停在狀態 0，不是接受狀態；`"."` 停在狀態 4；`"1e"` 停在狀態 6；`"e3"` 在狀態 0 遇到 e 沒有轉移。不要用 `str.isdigit()` 判斷數字，它會接受 `"²"`、`"٣"` 等 Unicode 數字字元，這裡用 `ch in "0123456789"`。旗標版本中 `seen_digit = False` 那一行是關鍵：它把「e 之後要有數字」與「整個字串最後要有數字」合併成同一個最終檢查。

### Follow-up

> [!question]- F1. 如果字串前後可以有空白（舊版題目），但中間不能有呢？
> 先去掉前後的空白再交給狀態機：`s.strip(" ")`；中間的空白在 `char_class` 中屬於 `other`，自然被拒絕。若要完全用狀態機表達，可以加兩個狀態：「開頭空白」（狀態 0 遇到空白留在 0）與「結尾空白」（任何接受狀態遇到空白轉到新狀態 9，狀態 9 只接受空白，且 9 是接受狀態）。兩種做法都是 O(n)。這個 follow-up 展示了狀態機的好處：加一條規則只需要加一列或一欄，不需要重新檢查所有 if 分支。

> [!question]- F2. 如果還要支援十六進位（`0x1F`）與數字之間的底線（`1_000`），要怎麼擴充？
> 十六進位：從狀態 0／1 讀到 `0` 時要轉到一個「可能是 0x 開頭」的新狀態（它本身也是接受狀態，因為 `"0"` 合法），再讀到 `x` 轉到「需要十六進位數字」，之後的數字類別擴大成 `0-9a-fA-F`。注意 `e` 在十六進位裡是數字而不是指數，所以字元分類要依狀態而定。底線：在每個「數字」狀態加一個「剛讀到底線」的影子狀態，它只能轉回同一個數字狀態，而且不是接受狀態（`"1_"` 不合法）。狀態數大約翻倍，仍然是 O(n) 時間、O(1) 空間。

> [!question]- F3. 除了判斷合法，還要把它轉成數值（不能用 float），怎麼做？
> 在走狀態機的同時累積三個整數：底數的所有數字組成的整數 `mant`、小數點之後的位數 `frac`、指數 `exp`（含正負號），以及底數的正負號。最終值是 `sign · mant · 10^(exp − frac)`。為了避免浮點誤差，可以用 `fractions.Fraction(mant) * Fraction(10) ** (exp - frac)` 得到精確值，最後才轉成 float。這和 8 String to Integer (atoi) 的累積方式相同，但 atoi 還要處理 32 位元溢位時截斷到上下限。

> [!question]- F4. 面試時可以直接用正規表示式嗎？
> 可以寫出來，但要能解釋它：`[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?`，第一組括號的兩個選項分別對應「有整數部分」（之後的小數點與小數部分都可選）與「沒有整數部分」（小數點後必須有數字）。要用 `fullmatch` 而不是 `match`，否則 `"1a"` 會被接受。Python 的 `\d` 預設會匹配 Unicode 數字，嚴格寫法是 `[0-9]`。面試官通常會接著要求「不用 regex 再寫一次」，因為 regex 引擎背後做的正是把這個式子編譯成狀態機；能說出這層關係就展現了你理解兩者的等價性。

> [!question]- F5. 如果字串是串流（一次只來一個字元，長度未知），而且要在不合法時立刻回報位置呢？
> 狀態機天生適合串流：只保存目前狀態（一個整數）與已讀的字元數，每個字元 O(1) 處理，不需要回看。查表失敗時立刻回報「第 i 個字元 `ch` 在狀態 q 不被接受」，還可以從狀態的意義產生友善的錯誤訊息，例如在狀態 6 收到非數字時回報「指數部分缺少數字」。串流結束時若停在非接受狀態，回報「輸入在 X 處意外結束」。旗標版本也能串流，但要額外保存前一個字元（判斷正負號位置），可讀性不如狀態表。

### 心得

關鍵突破是看出「未來能接受什麼，只取決於前綴的種類」，於是把格式規則改寫成 9 個狀態的轉移表，每個狀態都有清楚的意義，正確性可以逐列檢查。它和本章的關係是：29.6 節的狀態機模板處理「沒有巢狀」的格式；有巢狀時（難題 3、4）要加上 stack，有優先順序時（難題 5）要用遞迴下降。面試時建議先列出合法與不合法的例子各五個，和面試官確認規格（特別是 `"3."`、`".5"`、`"1e5"` 這類邊界），再畫狀態圖或表格，最後寫程式；先畫圖再寫碼，比邊寫 if 邊想快得多，也更容易說服面試官你沒有漏掉情況。

## 難題 2｜68. Text Justification｜Hard

### 題目

給一個單字陣列 `words` 和每行寬度 `max_width`，把文字排版成每行**恰好** `max_width` 個字元的左右對齊格式，回傳每一行的字串：

1. **分行**：採用貪婪法，每行盡可能放入最多的單字，相鄰單字之間至少一個空格。
2. **對齊**：除了最後一行，每行都要左右對齊：把多出來的空格平均分配到單字之間的空隙；若無法平均，**左邊的空隙**比右邊多分到一個。
3. **單字行**：若一行只有一個單字，它靠左，右邊補空格。
4. **最後一行**：靠左對齊，單字之間只用一個空格，右邊補空格到 `max_width`。

限制：`1 <= len(words) <= 300`，每個單字長度在 1 到 20 之間且不超過 `max_width`，`max_width <= 100`，單字由非空白字元組成。

- 範例 1：`words = ["Code", "is", "read", "much", "more", "often", "than", "written."]`、`max_width = 16`，回傳 `["Code   is   read", "much  more often", "than written.   "]`。
- 範例 2：`words = ["Do", "one", "thing", "well", "and", "test", "it"]`、`max_width = 10`，回傳 `["Do     one", "thing well", "and   test", "it        "]`。
- 範例 3（邊界）：`words = ["a", "bb", "ccc", "dddd"]`、`max_width = 4`，回傳 `["a bb", "ccc ", "dddd"]`；第二行只有一個單字，靠左補空格。
- 範例 4（邊界）：`words = ["hello"]`、`max_width = 5`，回傳 `["hello"]`；它既是唯一一行也是最後一行。

### 提示

> [!tip]- 提示 1
> 把問題拆成兩個獨立的小問題：「哪些單字放在同一行」以及「給定一行的單字，怎麼排出這一行」。前者只需要單字長度，後者只需要這一行的單字。

> [!tip]- 提示 2
> 分行：從第 i 個單字開始，累計「單字長度總和 + 單字數 − 1」（最少需要的空格），只要加入下一個單字後不超過 max_width 就繼續放。

> [!tip]- 提示 3
> 排一行：總空格數 = max_width − 字母總數，空隙數 g = 單字數 − 1。用 `q, r = divmod(總空格, g)`，前 r 個空隙放 q + 1 個空格，其餘放 q 個。g = 0（單字行）與最後一行要特別處理。

### 詳解

**為什麼這題難**。它沒有演算法上的難點：貪婪分行是題目規定的，不需要證明最佳；每一行的排法也是規定好的。難在**規則多、特例多**，而且特例之間會互相影響：最後一行如果只有一個單字，該套「單字行」還是「最後一行」的規則？（兩者結果相同，都是靠左補空格。）一行只有一個單字時空隙數是 0，`divmod` 會除以零。面試時一口氣寫完一個大迴圈，幾乎一定會在這些地方出錯。

**突破點：依 29.5 節的方式拆成小函式**。`pack(i)` 回傳從第 i 個單字開始、這一行能放到第幾個單字（不含），只看長度。`justify(line)` 處理一般行，`left_justify(line)` 處理最後一行與單字行。主迴圈只做「切出一行、決定用哪個函式排版」。每個函式都可以單獨用一兩個例子測試，主迴圈本身幾乎不會錯。

**分行的條件**。目前這一行已經放了單字 `i .. j − 1`，最少需要的寬度是 `width = Σ len + (j − i − 1)`（每個空隙至少一個空格）。加入第 j 個單字後變成 `width + 1 + len(words[j])`，不超過 `max_width` 就可以放。因為每個單字長度都 ≤ max_width，每行至少放得下一個單字，迴圈一定會前進。

**空格分配的正確性**。一般行有 k 個單字、g = k − 1 ≥ 1 個空隙，總空格 S = max_width − Σ len。令 `q, r = divmod(S, g)`，前 r 個空隙放 q + 1 個、後 g − r 個放 q 個，總共 `r(q + 1) + (g − r)q = gq + r = S`，剛好填滿；任兩個空隙最多差一個空格，而且多的那個在左邊，完全符合規則 2。因為分行時每個空隙至少留了一個空格，q ≥ 1，不會出現單字黏在一起。

```text
words = ["Code", "is", "read", "much", "more", "often", "than", "written."]，max_width = 16

分行（width = 已放單字的長度總和 + 空隙數）
i=0  "Code"(4)                        width = 4
     + "is"    → 4 + 1 + 2 = 7   ≤ 16 放入
     + "read"  → 7 + 1 + 4 = 12  ≤ 16 放入
     + "much"  → 12 + 1 + 4 = 17 > 16 停止       第 1 行：[Code, is, read]
i=3  "much"(4) + "more" → 9，+ "often" → 15，+ "than" → 20 > 16  第 2 行：[much, more, often]
i=6  "than"(4) + "written."(8) → 13，已到結尾       第 3 行（最後一行）

排版
第 1 行：字母 4+2+4 = 10，空格 S = 6，空隙 g = 2 → q = 3, r = 0 → 3, 3
         "Code" + "   " + "is" + "   " + "read"          = "Code   is   read"
第 2 行：字母 4+4+5 = 13，空格 S = 3，空隙 g = 2 → q = 1, r = 1 → 2, 1（左邊多一個）
         "much" + "  " + "more" + " " + "often"          = "much  more often"
第 3 行：最後一行 → "than written." 靠左，補 3 個空格  = "than written.   "
```

第 2 行是唯一需要 `r > 0` 的一行：3 個空格分給 2 個空隙，左邊的空隙拿到 2 個。若把餘數分給右邊，會得到 `"much more  often"`，這是最常見的錯誤之一，題目明確要求左邊優先。

### 解法

```python
def full_justify(words: list[str], max_width: int) -> list[str]:
    def pack(i: int) -> int:
        """從 words[i] 開始，回傳這一行最後一個單字的下一個索引。"""
        j, width = i + 1, len(words[i])
        while j < len(words) and width + 1 + len(words[j]) <= max_width:
            width += 1 + len(words[j])
            j += 1
        return j

    def left_justify(line: list[str]) -> str:
        return " ".join(line).ljust(max_width)

    def justify(line: list[str]) -> str:
        if len(line) == 1:                                # 單字行：沒有空隙可分配
            return left_justify(line)
        gaps = len(line) - 1
        q, r = divmod(max_width - sum(map(len, line)), gaps)
        parts = []
        for k, word in enumerate(line[:-1]):
            parts.append(word)
            parts.append(" " * (q + (1 if k < r else 0)))  # 前 r 個空隙多一格
        parts.append(line[-1])
        return "".join(parts)

    res, i = [], 0
    while i < len(words):
        j = pack(i)
        line = words[i:j]
        res.append(left_justify(line) if j == len(words) else justify(line))
        i = j
    return res


assert full_justify(["Code", "is", "read", "much", "more", "often", "than", "written."], 16) == [
    "Code   is   read", "much  more often", "than written.   "]
assert full_justify(["Do", "one", "thing", "well", "and", "test", "it"], 10) == [
    "Do     one", "thing well", "and   test", "it        "]
assert full_justify(["a", "bb", "ccc", "dddd"], 4) == ["a bb", "ccc ", "dddd"]
assert full_justify(["hello"], 5) == ["hello"]
assert full_justify(["a", "b", "c", "d", "e"], 3) == ["a b", "c d", "e  "]
out = full_justify(["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog."], 14)
assert out == ["The      quick", "brown      fox", "jumps over the", "lazy dog.     "]
assert all(len(line) == 14 for line in out)
print("all tests passed")
```

### 複雜度與邊界

時間 O(L)，L 是所有單字的總長度加上輸出的總長度：每個單字在 `pack` 中被看一次，每個輸出字元被產生一次；輸出共 `行數 × max_width` 個字元。空間除了輸出外是 O(max_width)（建一行的暫存）。邊界情況：單字行（包括「某個單字長度剛好等於 max_width」）走 `left_justify`，避免 `divmod` 除以零；最後一行即使有多個單字也只用單一空格；只有一個單字時它同時是最後一行；`pack` 的條件用 `<=`，剛好填滿 max_width 的情況要放進同一行。

### Follow-up

> [!question]- F1. 如果目標改成「讓排版最美觀」，例如最小化每行（最後一行除外）尾端空白數的平方和，貪婪還對嗎？
> 不對。貪婪讓前面的行盡量滿，可能把很大的空白留給後面某一行，而平方和懲罰大空白。例如寬度 6、單字 `["aaa", "bb", "cc", "ddddd"]`：貪婪排成 `aaa bb`、`cc`、`ddddd`，第二行尾端空 4 格，代價 0² + 4² = 16；改成 `aaa`、`bb cc`、`ddddd`，代價 3² + 1² = 10，更好。正確做法是 DP：`dp[i]` = 從第 i 個單字開始排到結尾的最小代價，`dp[i] = min over j (cost(i, j) + dp[j])`，其中 `i..j−1` 放在同一行且寬度合法；最後一行代價為 0。時間 O(n · 每行最多單字數) ≤ O(n · max_width)，這就是 TeX 斷行演算法（Knuth–Plass）的簡化版。

> [!question]- F2. 如果有單字比 max_width 還長呢？
> 原題保證不會發生，實務上要先和面試官確認規格。常見選擇有三種：直接拋出錯誤；把長單字硬切成多段，每段 `max_width − 1` 個字元加上連字號 `-`（最後一段不加），切完後當成多個單字照常排版；或讓它單獨成一行並允許超出寬度。不論哪種，修改都集中在「前處理單字清單」這一步，`pack` 和 `justify` 完全不用動，這正是把程式拆成小函式的好處。

> [!question]- F3. 如果要改成置中對齊或靠右對齊呢？
> 分行邏輯完全相同，只換掉 `justify`。靠右：`" ".join(line).rjust(max_width)`。置中：單字之間一個空格，總空白 `S = max_width − len(" ".join(line))`，左邊放 `S // 2`、右邊放 `S − S // 2`（或依規格讓左邊多一個）。每行 O(max_width)。面試官問這題通常是想看你的程式是否容易修改：如果分行與排版混在同一個迴圈裡，就得重寫大部分程式。

> [!question]- F4. 如果文字非常長（例如一本書），以串流方式一個一個單字讀入，要邊讀邊輸出呢？
> 貪婪分行只需要「目前這一行」的單字：維護一個緩衝區與目前寬度，新單字放不下時就用 `justify` 輸出緩衝區、清空，再放入新單字；串流結束時用 `left_justify` 輸出剩下的緩衝區作為最後一行。記憶體 O(max_width)，每個單字 O(1) 均攤。注意判斷「最後一行」需要知道串流已結束，所以緩衝區中的那一行要等到下一個單字到來（或串流結束）才能確定用哪種排法。F1 的 DP 版本則需要看到整段文字才能決定，無法這樣串流，實務上會以段落為單位做 DP。

> [!question]- F5. 如果文字包含中日韓字元（顯示寬度是 2 格）呢？
> 「長度」要改成「顯示寬度」：用 `unicodedata.east_asian_width(ch)` 判斷，`'W'`（寬）與 `'F'`（全形）算 2 格，其餘算 1 格，單字寬度是各字元寬度之和。`pack` 中的 `len(word)` 換成 `width(word)`，`justify` 中計算總空格時也用寬度，`ljust` 要改成手動補空格（因為 `ljust` 依字元數而非寬度）。另一個差別是中文通常沒有空格分隔單字，實務上會以字元為單位斷行，並加上「標點不能出現在行首」等避頭尾規則，這又是一層規則，同樣可以寫成獨立的函式。

### 心得

關鍵突破不是任何演算法，而是把題目拆成「分行」「一般行排版」「最後一行與單字行」三個小函式，讓每條規則只出現在一個地方。它和本章其他題的關係是：核心題 1 的螺旋也是「四條規則依序套用加兩個特例檢查」，難題 3 的標籤驗證也是「規則清單翻譯成程式」，三題的共同點是**特例要集中處理，不要散落在主迴圈裡**。面試時先和面試官把四條規則各舉一個例子確認（尤其是餘數給左邊、單字行、最後一行），寫完後用一個 `r > 0` 的行和一個單字行各手動驗證一次，這比寫完再盲目執行更能展現 L5 等級的嚴謹。

## 難題 3｜591. Tag Validator｜Hard

### 題目

給一個代表程式碼片段的字串 `code`，判斷它是否合法。規則如下：

1. 整段程式碼必須被**一個**合法的封閉標籤完整包住，標籤之外不能有任何字元（所以 `"<A></A><B></B>"` 不合法）。
2. 封閉標籤的格式是 `<TAG_NAME>TAG_CONTENT</TAG_NAME>`，開始與結束的 TAG_NAME 必須相同。
3. TAG_NAME 只能由 1 到 9 個**大寫英文字母**組成。
4. TAG_CONTENT 可以包含其他合法的封閉標籤、CDATA 區段，以及任意字元；但不能包含：不配對的 `<`、不配對的開始或結束標籤、名稱不合法的標籤。
5. 開始標籤若沒有對應的結束標籤就不合法；標籤必須正確巢狀（`<A><B></A></B>` 不合法）。
6. CDATA 區段的格式是 `<![CDATA[CDATA_CONTENT]]>`，CDATA_CONTENT 是從 `<![CDATA[` 之後到**第一個** `]]>` 之前的所有字元，裡面的任何東西（包括看起來像標籤的字串）都不解析。CDATA 只能出現在標籤內容中。
7. 任何一個 `<`，如果後面接的不是合法的開始標籤、結束標籤或 CDATA，就不合法。

限制：`1 <= len(code) <= 500`，字元是英文字母、數字、`<`、`>`、`/`、`!`、`[`、`]`、`.` 與空白。

- 範例 1：`"<A>x<![CDATA[</A>]]><B></B></A>"` 回傳 `True`：CDATA 中的 `</A>` 不被解析，`<B></B>` 是合法的內層標籤。
- 範例 2：`"<DIV>score > 90 is fine</DIV>"` 回傳 `True`：單獨的 `>` 是普通字元。
- 範例 3：`"<A><B></A></B>"` 回傳 `False`（交錯巢狀）；`"<A>a < b</A>"` 回傳 `False`（`< b</A>` 不是合法的標籤名稱）。
- 範例 4（邊界）：`"<A></A><B></B>"` 回傳 `False`（兩個根標籤）；`"<![CDATA[x]]>"` 回傳 `False`（CDATA 不在標籤內）；`"<ABCDEFGHIJ></ABCDEFGHIJ>"` 回傳 `False`（名稱 10 個字母）；`"x"` 回傳 `False`。

### 提示

> [!tip]- 提示 1
> 這是括號配對（20 Valid Parentheses，第 10 章核心題 1）的升級版：開始標籤是左括號、結束標籤是右括號，括號的「種類」就是標籤名稱。用什麼資料結構記住還沒關閉的標籤？

> [!tip]- 提示 2
> 由左往右掃描，每次看目前位置的前綴，只有四種情況：`<![CDATA[`、`</`、`<`、其他字元。前三種都能用 `find` 一次跳到對應的結尾（`]]>` 或 `>`），其他字元直接前進一格。CDATA 必須先判斷，因為它也以 `<` 開頭。

> [!tip]- 提示 3
> 「整段被一個標籤包住」等價於：除了位置 0，每當我們要處理新的東西時，stack 都不能是空的（stack 空了代表根標籤已經關閉）；而且掃描結束時 stack 必須為空。

### 詳解

**為什麼直覺做法不行**。最自然的想法是用正規表示式找出所有標籤再配對，但 CDATA 讓這條路很難走：CDATA 裡可以有 `</A>` 這種字串，必須先「遮蔽」掉；而 CDATA 本身的結尾是第一個 `]]>`，不能貪婪匹配。另一個陷阱是把「整段被一個標籤包住」理解成「第一個字元是 `<`、最後一個字元是 `>`」，`"<A></A><B></B>"` 就會被誤判。這題的規則多到必須有一個能逐條對應的結構。

**突破點：一個指標加一個 stack**。用 29.6 節「用 stack 處理巢狀」的模板：stack 裡存還沒關閉的標籤名稱。從位置 i 開始，依序判斷：

1. `code.startswith("<![CDATA[", i)`：必須在某個標籤內（stack 非空），找到之後的第一個 `]]>`，i 跳到它之後；找不到就不合法。
2. `code.startswith("</", i)`：找到下一個 `>`，取出名稱，必須等於 stack 頂端，pop，i 跳到 `>` 之後。
3. `code[i] == "<"`：找到下一個 `>`，名稱必須合法（1 到 9 個大寫字母），push，i 跳到 `>` 之後。
4. 其他字元：必須在某個標籤內，i 前進一格。

判斷的順序很重要：CDATA 和結束標籤都以 `<` 開頭，所以必須先判斷較長的前綴。另外，在每一輪開始時檢查 `i > 0 and not stack`：根標籤一旦關閉，後面就不能再有任何東西。

**正確性**。這個掃描實際上是在檢查一個文法：`code := TAG`、`TAG := <NAME> CONTENT </NAME>`、`CONTENT := (TAG | CDATA | 非 < 的字元)*`。stack 的內容恰好是「目前所在的巢狀路徑」，push 與 pop 對應進入與離開一個 TAG；規則 7（不合法的 `<`）由第 3 種情況的名稱檢查負責，因為任何不是 `<![CDATA[` 或 `</` 的 `<` 都被當成開始標籤嘗試解析，名稱不合法就拒絕。為了驗證這個對應，解法中附了一個直接照文法寫的遞迴下降版本，兩者在隨機產生的字串上交叉比對。

```text
code = "<A>x<![CDATA[</A>]]><B></B></A>"
位置   看到的前綴        動作                               stack
 0     "<A>"            開始標籤，名稱 A 合法 → push         [A]
 3     "x"              普通字元（stack 非空）→ i += 1       [A]
 4     "<![CDATA["      跳到第一個 "]]>" 之後（略過 </A>）    [A]
20     "<B>"            push                                 [A, B]
23     "</B>"           頂端是 B → pop                       [A]
27     "</A>"           頂端是 A → pop                       []
31     結束             stack 為空 → True

code = "<A><B></A></B>"
 0     "<A>"  push [A]；3 "<B>" push [A, B]；6 "</A>" 但頂端是 B → False

code = "<A></A><B></B>"
 0     "<A>"  push；3 "</A>" pop → []；7 輪開始時 i > 0 且 stack 為空 → False
```

第一個例子的 CDATA 從位置 4 開始，`<![CDATA[` 長 9 個字元，所以從位置 13 開始找 `]]>`，在位置 17 找到，i 跳到 20；中間的 `</A>` 完全沒有被當成標籤，這就是為什麼 CDATA 的判斷必須在 `</` 之前。第三個例子展示了「單一根標籤」規則如何用一行檢查實現。

### 解法

```python
import random


def valid_name(name: str) -> bool:
    return 1 <= len(name) <= 9 and all("A" <= ch <= "Z" for ch in name)


def is_valid(code: str) -> bool:
    stack, i, n = [], 0, len(code)
    while i < n:
        if i > 0 and not stack:                       # 根標籤已關閉，後面不能再有東西
            return False
        if code.startswith("<![CDATA[", i):
            if not stack:
                return False
            j = code.find("]]>", i + 9)
            if j < 0:
                return False
            i = j + 3
        elif code.startswith("</", i):
            j = code.find(">", i + 2)
            if j < 0 or not stack or stack[-1] != code[i + 2:j]:
                return False
            stack.pop()
            i = j + 1
        elif code[i] == "<":
            j = code.find(">", i + 1)
            if j < 0 or not valid_name(code[i + 1:j]):
                return False
            stack.append(code[i + 1:j])
            i = j + 1
        else:
            if not stack:                             # 位置 0 就是普通字元
                return False
            i += 1
    return n > 0 and not stack


def is_valid_recursive(code: str) -> bool:
    """直接照文法寫的遞迴下降版本，用來交叉驗證。"""
    n = len(code)

    def closed_tag(i: int) -> int:                    # 解析一個 TAG，回傳結束位置；失敗回傳 -1
        if not code.startswith("<", i):
            return -1
        j = code.find(">", i + 1)
        if j < 0 or not valid_name(code[i + 1:j]):
            return -1
        name, i = code[i + 1:j], j + 1
        while i < n:
            if code.startswith("</", i):
                j = code.find(">", i + 2)
                return j + 1 if j >= 0 and code[i + 2:j] == name else -1
            if code.startswith("<![CDATA[", i):
                j = code.find("]]>", i + 9)
                if j < 0:
                    return -1
                i = j + 3
            elif code[i] == "<":
                i = closed_tag(i)
                if i < 0:
                    return -1
            else:
                i += 1
        return -1

    return closed_tag(0) == n


CASES = {
    "<A>x<![CDATA[</A>]]><B></B></A>": True,
    "<DIV>score > 90 is fine</DIV>": True,
    "<A><![CDATA[]]>]]></A>": True,                   # CDATA 結束後的 "]]>" 是普通字元
    "<A><B></A></B>": False,
    "<A>a < b</A>": False,
    "<A></A><B></B>": False,
    "<![CDATA[x]]>": False,
    "<ABCDEFGHIJ></ABCDEFGHIJ>": False,
    "<ABCDEFGHI></ABCDEFGHI>": True,                  # 9 個字母剛好合法
    "x": False,
    "<A>": False,
    "<a></a>": False,
    "<A></A>": True,
}
for s, expect in CASES.items():
    assert is_valid(s) == expect == is_valid_recursive(s), s
TOKENS = ["<A>", "</A>", "<B>", "</B>", "<![CDATA[", "]]>", "<", ">", "x", "</", "<AB>", "</AB>"]
for _ in range(20000):
    s = "".join(random.choice(TOKENS) for _ in range(random.randint(1, 6)))
    if random.random() < 0.5:
        s = "<A>" + s + "</A>"
    assert is_valid(s) == is_valid_recursive(s), s
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：指標 i 只往前移動，每次 `find` 從目前位置往後找，找到後 i 直接跳過找過的部分；唯一的例外是 `find` 失敗時會掃到結尾，但那時直接回傳 False。名稱比較每次 O(9)。空間 O(n)，stack 最多 n / 7 層（最短的巢狀 `<A></A>` 是 7 個字元）。邊界情況：只有開始標籤 `"<A>"` 結束時 stack 非空；小寫名稱、空名稱 `"<>"`、超過 9 個字母都由 `valid_name` 擋下；CDATA 的內容是到**第一個** `]]>`，所以 `<![CDATA[]]>]]>` 的第二個 `]]>` 是普通內容；標籤內容裡單獨的 `>` 是合法的普通字元，單獨的 `<` 則一定不合法。

### Follow-up

> [!question]- F1. 如果開始標籤可以帶屬性，例如 `<A x="1" y="a>b">`，而且引號內可以有 `>` 呢？
> 這時「找下一個 `>`」不再正確，必須用一個小型 tokenizer 解析開始標籤：讀名稱，然後重複「跳過空白、讀屬性名稱、讀 `=`、讀一個以引號包住的值（在引號內遇到的 `>` 不算結尾）」，直到遇到標籤外的 `>`。這就是 29.6 節「先 tokenize 再 parse」的分層：stack 邏輯完全不變，只把「讀一個開始標籤」換成更完整的函式。時間仍是 O(n)。

> [!question]- F2. 如果要支援自我關閉的標籤，例如 `<BR/>`，怎麼改？
> 在處理開始標籤時，若 `>` 前一個字元是 `/`，名稱取 `code[i + 1 : j − 1]`，驗證合法後**不 push**（它同時開始又結束）。要注意它不能當作根標籤之外的第二個東西，所以仍然要在 stack 非空時才允許（或規定整段可以只是一個自我關閉標籤）。O(n) 不變。這類修改說明了為什麼四種情況要寫成清楚分開的分支：新規則只影響其中一個分支。

> [!question]- F3. 如果不只回傳 True／False，還要回報第一個錯誤的位置與原因呢？
> 把每個 `return False` 換成拋出帶有位置與訊息的例外，例如 `ParseError(i, "closing tag </A> does not match <B>")`、`ParseError(i, "unterminated CDATA")`、`ParseError(n, "unclosed tag <A>")`（掃描結束時 stack 非空，可以回報 stack 頂端那個開始標籤的位置，所以 push 時要連同位置一起存）。這在實務的 parser 中是必要的，面試時能主動提出「我會在 stack 中存 (名稱, 位置)」很加分。

> [!question]- F4. 如果巢狀非常深（例如 10⁵ 層），兩種寫法都還能用嗎？
> 顯式 stack 的版本沒有問題，記憶體 O(深度)。遞迴下降版本會撞到 Python 預設約 1000 層的遞迴上限而拋出 `RecursionError`；即使用 `sys.setrecursionlimit` 調高，也可能因為 C 層的堆疊大小而直接崩潰。解法是把遞迴改寫成顯式 stack（就是本題的主解法），或把遞迴放進一個有較大堆疊的 thread。這是「遞迴下降與 stack 等價、但工程上要選 stack」的典型理由，在處理使用者輸入的 parser 中尤其重要，因為惡意輸入可以刻意構造極深的巢狀。

> [!question]- F5. 如果要把合法的程式碼解析成一棵樹（像 DOM），回傳根節點呢？
> stack 裡改存節點物件而不是名稱：遇到開始標籤時建立新節點 `{"tag": name, "children": []}`，把它加入 stack 頂端節點的 children，再 push；遇到普通字元或 CDATA 時，把文字加入頂端節點的 children（相鄰的文字可以合併成一個文字節點）；遇到結束標籤時 pop。結束時根節點就是第一個被 push 的節點。時間與空間都是 O(n)。這和 297 Serialize and Deserialize Binary Tree（第 12 章難題 2）的反序列化是同一個想法：用 stack 記住「目前正在填哪個節點的子節點」。

### 心得

關鍵突破是把冗長的規則清單歸結為「一個指標、四種前綴、一個存標籤名稱的 stack」，並在每輪開始時用 `i > 0 and not stack` 一行實現「單一根標籤」。它和本章的關係是：難題 1 的狀態機處理沒有巢狀的格式，這題加上了巢狀所以需要 stack，難題 4 會在同樣的 stack 上再加「倍數」。面試時先列出規則並為每條規則舉一個不合法的例子，再說明四種前綴的判斷順序（CDATA 必須在 `</` 與 `<` 之前），寫完後用一個含 CDATA 的例子逐步追蹤 stack。若時間允許，主動提出「我可以再寫一個遞迴下降版本交叉驗證」，展現測試意識。

## 難題 4｜726. Number of Atoms｜Hard

### 題目

給一個化學式字串 `formula`，回傳每種原子的個數。化學式的文法如下：

- **原子名稱**是一個大寫字母，後面接零個或多個小寫字母，例如 `H`、`Mg`、`Uue`。
- 原子名稱後面可以接一個正整數表示個數；沒有數字代表 1。題目保證個數為 1 時不會寫出數字 `1`。
- 化學式可以串接，例如 `H2O2`；也可以用括號包住一段化學式，後面接一個倍數，例如 `(H2O2)3`，沒有數字代表倍數 1。括號可以巢狀。

輸出格式：把所有原子名稱依**字典序**排序，每個名稱後面接它的個數（個數為 1 時省略），串成一個字串。限制：`1 <= len(formula) <= 1000`，只包含英文字母、數字、`(`、`)`，化學式保證合法，所有個數都在 32 位元整數範圍內。

- 範例 1：`"H2O"` 回傳 `"H2O"`。
- 範例 2：`"Mg(OH)2"` 回傳 `"H2MgO2"`：括號內的 O 與 H 各乘 2，再依字典序 H、Mg、O 排列。
- 範例 3：`"Fe3(PO4(OH)2)2"` 回傳 `"Fe3H4O12P2"`：內層 `(OH)2` 給 O2H2，加上 PO4 得到 P1 O6 H2，再乘 2 得到 P2 O12 H4。
- 範例 4（邊界）：`"Al2(SO4)3"` 回傳 `"Al2O12S3"`；`"((H)2O)3"` 回傳 `"H6O3"`（巢狀括號，最外層沒有其他原子）。

### 提示

> [!tip]- 提示 1
> 先寫 tokenizer 的兩個小函式：「從位置 i 讀一個原子名稱」（一個大寫字母加上後面所有小寫字母）與「從位置 i 讀一個數字，沒有數字就回傳 1」。

> [!tip]- 提示 2
> 括號會巢狀，而每一層括號的計數要等到看見右括號後面的倍數才能決定怎麼併入外層。用什麼結構保存「外層還沒處理完的計數」？

> [!tip]- 提示 3
> 用一個 stack，每層一個 `Counter`。遇到 `(` push 一個新的空 `Counter`；遇到 `)` 讀倍數，pop 出內層，把每個原子的個數乘上倍數後加到新的頂端；遇到原子就把個數加到頂端。最後排序輸出。

### 詳解

**為什麼直覺做法不行**。一種直覺是「展開括號」：遇到 `(…)k` 就把括號內的字串複製 k 次，然後數原子。這在倍數很大時（例如 `(H)1000000`）會產生巨大的字串，而且巢狀時是倍數的乘積，例如 `((H)1000)1000` 展開後有 10⁶ 個 H。另一種直覺是用正規表示式抓出 `原子 + 數字` 再相加，但它無法處理「括號外的倍數要乘到括號內每一個原子」。題目的結構是巢狀的，需要能記住「外層狀態」的做法。

**突破點：一層括號一個計數器**。這正是 29.6 節「用 stack 處理巢狀」的模板，和 394 Decode String 的結構相同，只是上下文從「字串」換成「原子計數」。stack 的底部是最外層的計數器；`(` 開新的一層；原子直接加到目前這層；`)` 結束這一層，讀出倍數，把整層乘上倍數後併回外層。因為倍數寫在右括號**後面**，我們必須先把內層完整算完，才知道它要乘多少，這就是為什麼不能邊讀邊加到最終答案裡。

**另一個角度：從右往左掃描**。如果從右往左讀，每個右括號的倍數會**先**被看到，於是可以維護一個「目前的累積倍數」stack：遇到 `)` 時把「它後面的數字 × 目前倍數」push 進去，遇到 `(` 時 pop，遇到原子時直接把「個數 × 目前倍數」加到答案。這樣每個原子只被處理一次，不需要合併計數器，最差情況是嚴格的 O(n)。兩種寫法都附在解法中，互相驗證。

**正確性**。從左往右的版本維持的不變式是：stack 第 k 層的計數器，等於「第 k 層括號內、到目前為止已讀完的部分」各原子的個數（還沒乘上這層的倍數）。`)` 時把內層乘上倍數加到外層，恰好就是「外層括號內、已讀完部分」的定義，不變式保持；掃描結束時只剩最外層，就是整個化學式的計數。

```text
formula = "Fe3(PO4(OH)2)2"
讀到           動作                           stack（由底到頂）
"Fe3"          原子 Fe ×3 加到頂端             [{Fe:3}]
"("            push 新的一層                   [{Fe:3}, {}]
"P"            P ×1                            [{Fe:3}, {P:1}]
"O4"           O ×4                            [{Fe:3}, {P:1, O:4}]
"("            push                            [{Fe:3}, {P:1, O:4}, {}]
"O" "H"        O ×1、H ×1                      [{Fe:3}, {P:1, O:4}, {O:1, H:1}]
")2"           pop {O:1, H:1}，×2 併入頂端      [{Fe:3}, {P:1, O:6, H:2}]
")2"           pop {P:1, O:6, H:2}，×2 併入     [{Fe:3, P:2, O:12, H:4}]
結束           排序：Fe, H, O, P               "Fe3H4O12P2"

從右往左（倍數 stack，初始 [1]）
讀到 "2"      暫存數字 2
讀到 ")"      push 1 × 2 = 2                  mult = [1, 2]
讀到 "2" ")"  push 2 × 2 = 4                  mult = [1, 2, 4]
讀到 "H"      H += 1 × 4 = 4
讀到 "O"      O += 1 × 4 = 4
讀到 "("      pop                             mult = [1, 2]
讀到 "4" "O"  O += 4 × 2 = 8（O 共 12）
讀到 "P"      P += 1 × 2 = 2
讀到 "("      pop                             mult = [1]
讀到 "3" "Fe" Fe += 3 × 1 = 3
```

兩種掃描得到相同的計數。從右往左的版本中，原子名稱要從它的最後一個小寫字母往左找到大寫字母才算讀完，數字也要從個位往左讀到最高位，這是反向掃描的實作細節，寫的時候要小心索引。

### 解法

```python
import random
from collections import Counter


def format_counts(counts: Counter) -> str:
    return "".join(name + (str(counts[name]) if counts[name] > 1 else "") for name in sorted(counts))


def count_of_atoms(formula: str) -> str:
    n, i = len(formula), 0
    stack = [Counter()]

    def read_number() -> int:
        nonlocal i
        start = i
        while i < n and formula[i].isdigit():
            i += 1
        return int(formula[start:i]) if i > start else 1

    def read_name() -> str:
        nonlocal i
        start = i
        i += 1                                        # 大寫字母
        while i < n and formula[i].islower():
            i += 1
        return formula[start:i]

    while i < n:
        if formula[i] == "(":
            stack.append(Counter())
            i += 1
        elif formula[i] == ")":
            i += 1
            mult = read_number()
            inner = stack.pop()
            for name, cnt in inner.items():
                stack[-1][name] += cnt * mult
        else:
            name = read_name()
            stack[-1][name] += read_number()
    return format_counts(stack[0])


def count_of_atoms_reverse(formula: str) -> str:
    """從右往左掃描，維護累積倍數的 stack，每個原子只處理一次。"""
    counts, mult = Counter(), [1]
    i, pending = len(formula) - 1, 1                  # pending：剛讀到、還沒用掉的數字
    while i >= 0:
        ch = formula[i]
        if ch.isdigit():
            j = i
            while j > 0 and formula[j - 1].isdigit():
                j -= 1
            pending = int(formula[j:i + 1])
            i = j - 1
            continue
        if ch == ")":
            mult.append(mult[-1] * pending)
            i -= 1
        elif ch == "(":
            mult.pop()
            i -= 1
        else:
            j = i
            while not formula[j].isupper():
                j -= 1
            counts[formula[j:i + 1]] += pending * mult[-1]
            i = j - 1
        pending = 1
    return format_counts(counts)


ELEMENTS = ["H", "He", "O", "C", "Mg", "S", "N", "Uue"]


def random_formula(depth):
    """隨機產生化學式，同時回傳正確的計數。"""
    parts, counts = [], Counter()
    for _ in range(random.randint(1, 3)):
        if depth > 0 and random.random() < 0.4:
            inner, c = random_formula(depth - 1)
            k = random.choice([1, 2, 3, 12])
            parts.append(f"({inner})" + (str(k) if k > 1 else ""))
            for name, v in c.items():
                counts[name] += v * k
        else:
            name, k = random.choice(ELEMENTS), random.choice([1, 2, 3, 10])
            parts.append(name + (str(k) if k > 1 else ""))
            counts[name] += k
    return "".join(parts), counts


for f, expect in [("H2O", "H2O"), ("Mg(OH)2", "H2MgO2"), ("Fe3(PO4(OH)2)2", "Fe3H4O12P2"),
                  ("Al2(SO4)3", "Al2O12S3"), ("((H)2O)3", "H6O3"), ("Be32", "Be32"),
                  ("(H)1000000", "H1000000")]:
    assert count_of_atoms(f) == expect == count_of_atoms_reverse(f), f
for _ in range(3000):
    f, c = random_formula(3)
    assert count_of_atoms(f) == format_counts(c) == count_of_atoms_reverse(f), f
print("all tests passed")
```

### 複雜度與邊界

從右往左的版本時間 O(n + D log D)：每個字元處理一次，D 是不同原子的種類數，排序 D 個名稱（名稱長度有界）。從左往右的 stack 版本，每次 `)` 要把內層計數器的每一項併入外層，若括號巢狀很深、而內層有很多種原子（例如 `((((HHeLiBe…)2)2)2)2`），同一批原子會在每一層都被合併一次，最差 O(n · D)；在 n ≤ 1000 的限制下兩者都很快。空間 O(n)：stack 深度最多 n / 2。邊界情況：多位數的個數與倍數（`Be32`、`)12`）要用 while 讀完；括號後沒有數字代表倍數 1；多字母的原子名稱（`Uue`）要讀到大寫字母或非字母為止；輸出時個數為 1 不寫數字。

### Follow-up

> [!question]- F1. 如果還要支援方括號、大括號，以及結晶水的寫法（例如 `CuSO4·5H2O` 或 `K4[Fe(CN)6]`）呢？
> 方括號、大括號在語意上和圓括號相同，只要 tokenizer 把 `[` `{` 當成 `(`、把 `]` `}` 當成 `)`；若要驗證配對，stack 中多存一個「開括號的種類」，關閉時檢查是否匹配（同 20 Valid Parentheses）。結晶水的 `·` 代表「加上」，而且後面可以有一個前置係數：用 `·` 把式子切成幾段，每段讀開頭的數字作為係數（沒有就是 1），各自用本題的解法計數後乘上係數相加。整體仍是 O(n)。

> [!question]- F2. 如果輸入不保證合法，要能偵測錯誤呢？
> 在 tokenizer 與 stack 操作中加入檢查：遇到 `)` 時 stack 只剩最外層（多出來的右括號）、掃描結束時 stack 不只一層（缺右括號）、以小寫字母或數字開頭的原子、數字出現在開頭或緊接在 `(` 之後、空括號 `()`、個數為 0 或有前導零（依規格）。每種錯誤在被發現的位置拋出帶位置的例外。這些檢查都是 O(1)，總時間不變；面試時能主動列出這些錯誤類型，代表你會考慮真實輸入。

> [!question]- F3. 如果要計算分子量（給一張原子量表）呢？
> 計數完成後，分子量就是 `Σ counts[name] × weight[name]`，O(D)。也可以不建計數器，直接在 stack 上存「這一層目前的總重量」（一個浮點數或 Decimal），遇到原子加上 `weight × 個數`，遇到 `)` 把內層重量乘上倍數加到外層，空間降為 O(深度) 個數字。若重量要精確到小數位數，用 `decimal.Decimal` 避免浮點誤差累積。

> [!question]- F4. 如果輸出要用化學上常見的 Hill 順序（有碳時 C 第一、H 第二，其餘依字母序）呢？
> 只改排序的 key：若計數中有 `C`，key 是 `(0 if name == "C" else 1 if name == "H" else 2, name)`；若沒有 C，全部依字母序（H 不特別處理）。計數邏輯完全不動，這也是把 `format_counts` 寫成獨立函式的好處。O(D log D)。

> [!question]- F5. 如果倍數可能大到讓個數超過 64 位元呢？
> Python 的整數沒有上限，程式不用改，但每次乘法的成本會隨位數增加。在 Java 或 C++ 中要改用 `BigInteger` 或自己實作大數；若題目只要求個數對某個質數取模，就在每次乘法與加法後取模，用 64 位元整數即可。倍數相乘的路徑是 stack 中的累積倍數（從右往左的版本）或每次合併（從左往右的版本），兩處都要套用同一個取模規則。

### 心得

關鍵突破是「倍數寫在右括號之後，所以內層必須先算完」，這直接導出「一層括號一個計數器」的 stack；反過來從右往左讀，倍數就會先出現，可以改用累積倍數的 stack 達到嚴格 O(n)。它和本章的關係是：難題 3 的 stack 存「還沒關閉的標籤名稱」，這題存「還沒關閉的計數器」，難題 5 則讓每一層的值變成多項式並加入運算子優先順序。面試時先寫兩個 tokenizer 小函式（讀名稱、讀數字，沒有數字回傳 1）並各測一次，再寫主迴圈；說明解法時用一個兩層巢狀的例子畫出 stack 的變化，面試官很快就能確認你的邏輯。

## 難題 5｜770. Basic Calculator IV｜Hard

### 題目

給一個運算式字串 `expression`，以及兩個等長的陣列 `evalvars`（變數名稱）與 `evalints`（對應的整數值），表示這些變數要代換成指定的值。運算式由非負整數、小寫字母組成的變數名稱、`+`、`-`、`*`、括號組成，token 之間以單一空格分隔（括號緊貼內容，例如 `(a + b)`）。沒有單元負號，也沒有除法。

請把運算式代換、展開並化簡成多項式，以字串陣列回傳每一項，格式與順序如下：

- 每一項寫成 `係數*變數1*變數2*…`，變數依字典序排列，係數一定要寫出來（包括 `1` 與負數，例如 `"1*a*b"`、`"-2*x"`）；常數項只寫係數，例如 `"-6"`。
- 項的排序：**次數**（變數個數，重複計算）高的在前；次數相同時，依變數串列的字典序排列。
- 係數為 0 的項不輸出；若整個多項式為 0，回傳空陣列。

限制：`1 <= len(expression) <= 250`，`0 <= len(evalvars) <= 100`，代換值在 `-100` 到 `100` 之間，所有中間係數都在 32 位元整數範圍內。

- 範例 1：`expression = "e + 8 - a + 5"`、`evalvars = ["e"]`、`evalints = [1]`，回傳 `["-1*a", "14"]`。
- 範例 2：`expression = "(a - b) * (a + b)"`、沒有代換，回傳 `["1*a*a", "-1*b*b"]`：交叉項 `a*b` 與 `-b*a` 互相抵消。
- 範例 3：`expression = "(x + 2) * (x - 3) - y * x"`，回傳 `["1*x*x", "-1*x*y", "-1*x", "-6"]`：`x*x` 與 `x*y` 都是二次，依字典序 `x*x` 在前。
- 範例 4（邊界）：`"a - a"` 回傳 `[]`；`"a * b * c + b * a * c * 4"` 回傳 `["5*a*b*c"]`，變數順序不同的項要合併。

### 提示

> [!tip]- 提示 1
> 先決定多項式的表示方式：一個 dict，key 是「排序後的變數 tuple」（常數項的 key 是空 tuple），value 是係數。例如 `3*a*b - 2` 是 `{("a", "b"): 3, (): -2}`。這樣變數順序不同的項自然會合併。

> [!tip]- 提示 2
> 實作多項式的加、減、乘：加減是逐項合併係數；乘法是兩兩相乘，key 為兩個 tuple 串接後排序，係數相乘。每次運算後刪掉係數為 0 的項。

> [!tip]- 提示 3
> 用 29.6 節的遞迴下降：`expr := term (('+'|'-') term)*`、`term := factor ('*' factor)*`、`factor := 數字 | 變數 | '(' expr ')'`。每個函式回傳一個多項式；變數若在代換表中就回傳常數多項式。最後依 `(-len(key), key)` 排序輸出。

### 詳解

**為什麼直覺做法不行**。第 10 章難題 4（224 Basic Calculator）用 stack 處理加減與括號，因為值是整數，遇到運算子立刻計算即可。這題的值是**多項式**，而且有乘法：`(a + b) * (c + d)` 必須展開成四項，無法用「整數 stack ＋符號」的技巧；用兩個 stack 的 shunting-yard（調度場）演算法可以做，但運算子優先順序與括號的處理散落在 pop 迴圈裡，加上多項式運算後很難除錯。另一個陷阱是直接操作字串（例如把 `a*b` 與 `b*a` 視為不同項），化簡就會出錯。

**突破點：把「值」抽象成多項式，再套用標準的遞迴下降**。分成兩層：下層是一個小型的多項式代數（加、減、乘、化簡），完全不知道字串長什麼樣；上層是 29.6 節的運算式 parser，把四則運算模板中的 `int` 換成多項式、`+` 換成 `add`、`*` 換成 `mul`。這兩層各自都很好測試：多項式運算可以用 `(a − b)(a + b) = a² − b²` 驗證，parser 可以先用整數驗證優先順序。

**正確性與規格細節**。遞迴下降的正確性來自文法：`term` 先把乘法吃完，`expr` 才處理加減，所以乘法優先；`while` 迴圈讓同級運算左結合（`a - b - c = (a − b) − c`）。多項式的 key 用排序後的 tuple，讓交換律自動成立（`a*b` 與 `b*a` 的 key 都是 `("a", "b")`）。輸出排序 `(-len(key), key)` 正好實現「次數高的在前，同次數依變數字典序」。每次運算後刪除係數為 0 的項，保證輸出不含 0 項，也讓 `a - a` 回傳空陣列。為了驗證整個流程，測試中把隨機產生的運算式與我們的輸出，在隨機的變數值下各自求值比較：兩個多項式若在很多隨機點上都相等，幾乎可以確定它們相同。

```text
expression = "(x + 2) * (x - 3) - y * x"
tokens: ( x + 2 ) * ( x - 3 ) - y * x

遞迴下降的呼叫與回傳（多項式寫成 {key: 係數}）
expr
├─ term
│  ├─ factor "(" → expr
│  │     term → factor x      {(x,): 1}
│  │     "+" term → factor 2  {(): 2}
│  │     add                 → {(x,): 1, (): 2}
│  │  ")"
│  ├─ "*"
│  ├─ factor "(" → expr ... → {(x,): 1, (): -3}  ")"
│  └─ mul：
│        (x,)·(x,) = (x, x): 1·1 = 1
│        (x,)·()   = (x,):   1·(-3) = -3
│        ()·(x,)   = (x,):   2·1 = 2      → (x,) 合計 -1
│        ()·()     = ():     2·(-3) = -6
│      → {(x, x): 1, (x,): -1, (): -6}
├─ "-"
├─ term：factor y {(y,): 1} "*" factor x {(x,): 1} → mul → {(x, y): 1}
└─ add(sign = -1) → {(x, x): 1, (x,): -1, (): -6, (x, y): -1}

排序 key (-次數, 變數 tuple)：
(x, x) → (-2, (x, x))   (x, y) → (-2, (x, y))   (x,) → (-1, (x,))   () → (0, ())
輸出：["1*x*x", "-1*x*y", "-1*x", "-6"]
```

乘法那一步展示了多項式表示的威力：`(x,)` 這個 key 從兩個不同的乘積來（`x · (−3)` 與 `2 · x`），因為 key 相同，係數自動相加成 −1。`y * x` 的 key 是排序後的 `("x", "y")`，所以輸出時寫成 `x*y` 而不是 `y*x`。

### 解法

```python
import random
from collections import defaultdict

Poly = dict[tuple[str, ...], int]


def poly_add(p: Poly, q: Poly, sign: int = 1) -> Poly:
    res = defaultdict(int, p)
    for k, v in q.items():
        res[k] += sign * v
    return {k: v for k, v in res.items() if v}


def poly_mul(p: Poly, q: Poly) -> Poly:
    res = defaultdict(int)
    for k1, v1 in p.items():
        for k2, v2 in q.items():
            res[tuple(sorted(k1 + k2))] += v1 * v2
    return {k: v for k, v in res.items() if v}


def basic_calculator_iv(expression: str, evalvars: list[str], evalints: list[int]) -> list[str]:
    env = dict(zip(evalvars, evalints))
    tokens = expression.replace("(", " ( ").replace(")", " ) ").split()
    pos = 0

    def const(v: int) -> Poly:
        return {(): v} if v else {}

    def expr() -> Poly:
        nonlocal pos
        res = term()
        while pos < len(tokens) and tokens[pos] in ("+", "-"):
            sign = 1 if tokens[pos] == "+" else -1
            pos += 1
            res = poly_add(res, term(), sign)
        return res

    def term() -> Poly:
        nonlocal pos
        res = factor()
        while pos < len(tokens) and tokens[pos] == "*":
            pos += 1
            res = poly_mul(res, factor())
        return res

    def factor() -> Poly:
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        if tok == "(":
            res = expr()
            pos += 1                                  # 吃掉 ")"
            return res
        if tok.isdigit():
            return const(int(tok))
        if tok in env:
            return const(env[tok])
        return {(tok,): 1}

    poly = expr()
    keys = sorted(poly, key=lambda k: (-len(k), k))
    return ["*".join((str(poly[k]),) + k) for k in keys]


def eval_terms(terms: list[str], values: dict[str, int]) -> int:
    total = 0
    for t in terms:
        coef, *names = t.split("*")
        v = int(coef)
        for name in names:
            v *= values[name]
        total += v
    return total


assert basic_calculator_iv("e + 8 - a + 5", ["e"], [1]) == ["-1*a", "14"]
assert basic_calculator_iv("(a - b) * (a + b)", [], []) == ["1*a*a", "-1*b*b"]
assert basic_calculator_iv("(x + 2) * (x - 3) - y * x", [], []) == ["1*x*x", "-1*x*y", "-1*x", "-6"]
assert basic_calculator_iv("a - a", [], []) == []
assert basic_calculator_iv("a * b * c + b * a * c * 4", [], []) == ["5*a*b*c"]
assert basic_calculator_iv("7", [], []) == ["7"]
assert basic_calculator_iv("x * y", ["x"], [0]) == []                  # 代換成 0 後整項消失
assert basic_calculator_iv("((k))", ["k"], [-3]) == ["-3"]
VARS = ["a", "b", "cc", "x"]


def random_expr(depth):
    if depth == 0 or random.random() < 0.3:
        return random.choice(VARS + [str(random.randint(0, 9))])
    left, right = random_expr(depth - 1), random_expr(depth - 1)
    op = random.choice("+-*")
    return f"({left} {op} {right})" if random.random() < 0.5 else f"{left} {op} {right}"


for _ in range(1000):
    e = random_expr(4)
    subs = random.sample(VARS, random.randint(0, 2))
    ints = [random.randint(-3, 3) for _ in subs]
    terms = basic_calculator_iv(e, subs, ints)
    for _ in range(3):
        values = {v: random.randint(-5, 5) for v in VARS}
        values.update(zip(subs, ints))
        assert eval_terms(terms, values) == eval(e, {}, values), e
print("all tests passed")
```

### 複雜度與邊界

令 T 為過程中多項式的最大項數、d 為最大次數。每次乘法是 O(T² · d log d)（兩兩相乘，key 串接後排序），加法 O(T · d)，運算次數 O(n)，所以總時間是 O(n · T² · d log d)；最後排序輸出 O(T log T · d)。T 在最差情況下可能隨乘法次數指數成長（見 F3），但在這題的長度限制下很小。空間 O(T · d) 加上遞迴深度 O(n)。邊界情況：代換值為 0 時，`const(0)` 回傳空多項式，乘法後整項消失；係數抵消為 0 的項在每次運算後立即刪除；多個字母的變數名稱（`cc`）是一個變數；`a*a` 的 key 是 `("a", "a")`，次數為 2；括號緊貼內容時，tokenizer 先在括號兩側補空格再切割。

### Follow-up

> [!question]- F1. 如果要支援非負整數次方 `^`（例如 `(a + 1) ^ 3`）呢？
> 在文法中加一層，優先順序高於乘法：`term := power ('*' power)*`、`power := factor ('^' NUMBER)?`（次方通常是右結合，若要支援 `a ^ 2 ^ 3`，寫成 `power := factor ('^' power)?`）。計算 `p ^ k` 用快速冪：反覆平方 `p`，在 k 的二進位為 1 的位元把結果乘上去，只需要 O(log k) 次多項式乘法（第 28 章核心題 4 的 50 Pow(x, n) 是同一個方法）。k = 0 時回傳常數多項式 1。

> [!question]- F2. 如果運算式可以有單元負號，例如 `-(a + b) * -c`？
> 在 `factor` 加一條規則：`factor := '-' factor | '+' factor | ...`，遇到 `-` 時遞迴解析下一個 factor，再把每個係數取負。因為單元負號寫在 factor 層，它的優先順序高於乘法，`-a * b` 被解析成 `(−a) · b`，結果與 `−(a · b)` 相同，對多項式沒有差別。tokenizer 不需要修改，`-` 是二元還是單元，由它出現在 parser 的哪個位置決定，這正是遞迴下降比「看前一個 token 判斷」更乾淨的地方。

> [!question]- F3. 輸出的項數最多可以有多大？能不能避免？
> 不能避免，因為那是答案本身的大小。例如 `(a + b) * (c + d) * (e + f) * …` 共 k 個括號、每個括號的變數都不同，展開後有 2^k 項，每一項都要輸出。若變數重複，例如 `(x + 1)` 自乘 k 次，項數只有 k + 1，但係數是二項式係數，會成長得很快。面試中能指出「這題的複雜度由輸出大小主導」並估計 T 的上界，比給出一個漂亮但不正確的多項式時間宣稱更好。

> [!question]- F4. 如果同一個運算式要用很多組不同的變數值求值呢？
> 先不做代換，把運算式化簡成多項式一次（「編譯」），之後每組變數值都只需要對每一項計算 `係數 × Π 變數值`，O(T · d)，不必重新解析。若 T 很大但運算式本身很短，反而應該把運算式解析成一棵語法樹，每組值直接在樹上求值，O(n)，因為展開可能讓 T 遠大於 n。兩者的取捨就是「先展開」與「保留結構」：輸出需要化簡形式時展開，只需要數值時保留語法樹。

> [!question]- F5. 如何判斷兩個運算式在數學上是否相等？
> 最直接的做法是把兩者都化簡成本題的標準形式（排序後的 key 與係數），再比較兩個 dict 是否相等，正確但可能因為 F3 的指數展開而太慢。實務上常用隨機化檢驗：在一個大質數 p 的模下，對所有變數代入隨機值，比較兩邊的值。根據 Schwartz–Zippel 引理，若兩個多項式不相等、次數為 d，隨機代入後恰好相等的機率不超過 d / p，重複幾次就能讓錯誤機率小到可以忽略。每次檢驗只需要在語法樹上求值，O(n)，完全不需要展開。本題的隨機測試其實就用了同一個想法。

### 心得

關鍵突破是「把值的型別從整數換成多項式」，於是第 10 章那個整數計算機的遞迴下降骨架可以原封不動地重用，只是運算子換成多項式的 `add` 與 `mul`，而多項式以「排序後的變數 tuple → 係數」表示，讓交換律與同類項合併自動成立。它是本章解析題的總結：tokenizer（29.6 節）、遞迴下降處理優先順序、規格繁瑣的輸出格式（難題 2 的精神）、以及嚴謹的測試策略都用上了。面試時先花一兩分鐘定好多項式的表示法並寫出 `add`、`mul`，再寫 parser；先把 parser 用整數跑一次確認優先順序，再換成多項式。時間不夠時，清楚說出兩層分工並寫完其中一層，也比一個混在一起、無法驗證的大函式更有說服力。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 螺旋與分層走訪 | 「一圈一圈」「螺旋順序」 | 四個邊界變數收縮，走下邊、左邊前檢查矩形是否還非空；或 `ring(m, n, k)` 半開區間 | 核心題 1（54）、59、885、1914 |
| 座標變換 | 旋轉、轉置、鏡射、對角線 | 先寫出 `(r, c)` 的映射公式；原地做法是兩次鏡射合成，或沿排列的循環交換 | 核心題 2（48）、867 Transpose Matrix、498 Diagonal Traverse、1886 |
| 借用矩陣當記錄區 | O(1) 空間，資訊是「整列／整行」 | 第一列、第一行存標記，一個變數補救重疊的角落；記錄區最後處理 | 核心題 3（73） |
| 多群組約束檢查 | 列、行、區塊不能重複 | 每格同時屬於多個群組，用編號公式找群組，set 或 bitmask 記錄 | 核心題 4（36）、37（第 19 章難題 2） |
| 同時更新的原地模擬 | 「所有格子同時」依鄰居更新 | 位元打包：低位舊狀態、高位新狀態，第二輪統一右移 | 核心題 5（289）、130（第 15 章核心題 5） |
| 規則模擬與大步數 | 依指令或規則逐步更新狀態；步數到 10⁹ 而狀態有限 | 拆成狀態、單步轉移、執行三層小函式；大步數用週期偵測跳過整數個週期 | 874 Walking Robot Simulation、957 Prison Cells After N Days |
| 格式驗證 | 沒有巢狀的字串格式 | 有限狀態機：狀態 = 前綴的種類，轉移表 + 接受狀態 | 難題 1（65）、8 String to Integer (atoi)、468 Validate IP Address |
| 規則繁多的排版與輸出 | 長串規則、多個特例 | 拆成「分組」「單組處理」「特例」小函式，各自測試 | 難題 2（68）、6 Zigzag Conversion |
| 巢狀配對 | 開頭與結尾成對、可以巢狀 | stack 存「還沒關閉的開頭」與外層上下文 | 難題 3（591）、20（第 10 章核心題 1）、394 Decode String |
| 巢狀帶倍數的計數 | 括號後面接倍數 | 一層一個計數器的 stack；或從右往左、維護累積倍數 | 難題 4（726）、394、1096 Brace Expansion II |
| 運算式求值 | 運算子優先順序與括號 | 遞迴下降，一個優先層級一個函式；值的型別可以抽換 | 難題 5（770）、224（第 10 章難題 4）、227、772、282（第 19 章難題 3） |

**下限與上限**。最簡單的形式是單純的座標操作，例如 867 轉置或 54 螺旋，考的是迴圈邊界寫對；再往上一層是要求原地與 O(1) 空間的版本（48、73、289），難點是看出能把額外資訊存在哪裡：排列的循環、矩陣自己的第一列與第一行、整數的高位元。解析類的下限是單一字串的格式驗證，上限的題目通常同時具備三種難度：**文法本身有巢狀與優先順序**（770 需要完整的遞迴下降）、**值不是單純的整數**（726 的計數器、770 的多項式，需要先設計一個小型的資料型別）、**規格細節繁多**（68 的四條排版規則、591 的七條標籤規則、770 的輸出排序與格式）。這類題目最難的地方不是想不到解法，而是在 45 分鐘內寫出沒有 bug 的程式，所以結構化的拆解與測試策略本身就是答案的一部分。

**與其他 pattern 的關係**。矩陣走訪的方向陣列、邊界檢查，是 grid BFS／DFS（第 15 章）的基本零件；差別在於 BFS 有「最短距離」或「連通」的目標，本章則是固定的走訪順序。矩陣上的 prefix sum（第 7 章核心題 4 的 304）與 DP（第 22 章）也共用同一套座標慣例。解析題與 stack（第 10 章）高度重疊：括號配對、RPN 求值、224 計算機都是本章 29.6 節模板的特例；backtracking（第 19 章）中的 282 Expression Add Operators 則是在「產生運算式」時同時處理乘法優先順序。週期偵測與 linked list 的 Floyd 判圈（第 11 章）、287 Find the Duplicate Number（第 5 章難題 2）是同一個數學事實：有限狀態的確定性轉移必定進入循環。

**容易混淆之處**。第一，「矩陣題」不一定是本章的 pattern：若題目問最短路徑、連通塊或最大面積，應該想 BFS／DFS、Union-Find 或 DP，而不是模擬。第二，「原地」不代表可以邊讀邊寫：只要新值依賴舊值，就必須編碼或保存舊值，否則結果依掃描順序而不同。第三，解析時不要一開始就寫 regex 或一大串 if：沒有巢狀時用狀態機，有巢狀用 stack，有優先順序用遞迴下降；regex 只適合沒有巢狀的格式，而且面試官通常會要求你不用它再寫一次。

## 本章重點整理

- 矩陣題一開始就宣告座標慣例：`(r, c)` 是第 r 列第 c 行，`m = len(grid)`、`n = len(grid[0])`；方向陣列依順時針排列，右轉是 `(d + 1) % 4`。
- 常用座標公式：攤平 `r * n + c`、主對角線 `r − c`、反對角線 `r + c`、3 × 3 區塊 `(r // 3) * 3 + c // 3`、順時針旋轉 `(r, c) → (c, n − 1 − r)`。
- 邊界收縮的不變式是「剩下的區域仍是一個矩形」；走完上邊、右邊之後，要先檢查 `top <= bottom` 與 `left <= right` 才能走下邊、左邊。
- 順時針旋轉 90 度 = 轉置 + 每列反轉；也可以每層做四格循環交換。非正方形無法在同形狀的二維 list 中原地旋轉。
- 原地「同時更新」的三種做法：位元打包（289）、借用第一列第一行當記錄區並最後處理它們（73）、值域外的標記；核心都是「讀取時只讀舊值」。
- 模擬題由下往上拆成小函式（狀態、單步轉移、執行、render），每層用手算的小例子驗證；步數很大時用週期偵測跳過重複。
- 解析題先 tokenize 再 parse：數字、名稱一律用內層 while 讀到結束；parse 完要確認所有 token 都被吃掉。
- 沒有巢狀的格式用有限狀態機：狀態 = 前綴的種類，結尾一定要檢查是否停在接受狀態（`"1e"`、`"."` 都是陷阱）。
- 巢狀結構用 stack：開頭 push 外層上下文，結尾 pop 並合併；591 存標籤名稱，726 存計數器，394 存字串與倍數。
- 有優先順序的運算式用遞迴下降，一個優先層級一個函式，`while` 迴圈實現左結合；值的型別可以從整數換成多項式（770），骨架完全不變。
- 測試策略本身就是答案的一部分：對所有小尺寸檢查覆蓋性、用另一種寫法交叉比對、或像 770 一樣在隨機點上求值比較。
