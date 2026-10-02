---
chapter: 17
title: 寫出 Cache-friendly 的程式
part: 4
---

# 第 17 章　寫出 Cache-friendly 的程式：迴圈順序、Blocking 與資料布局

> [!abstract] 本章地圖
> **核心問題**：兩段指令數一模一樣、算出同樣結果的程式，為什麼一段可以比另一段快十倍以上？怎麼寫程式，才能讓 cache 替你工作，而不是跟你作對？
>
> **你會學到**：
> - 從一段迴圈手算出每次迭代平均幾次 cache miss，並用它預測哪個版本比較快
> - 分析矩陣乘法六種迴圈順序的存取模式，說出為什麼 `kij`／`ikj` 最快、`jki`／`kji` 最慢
> - 用 blocking（tiling）縮小 working set，並算出 tile 該取多大
> - 讀懂 memory mountain：哪裡是 temporal locality 的山脊、哪裡是 spatial locality 的斜坡
> - 在 AoS 與 SoA 之間做選擇，辨認 2 的冪次 stride 造成的 conflict miss，並用 `perf stat` 確認 cache 是不是瓶頸
>
> **前置知識**：第 10 章（row-major 與陣列位址計算）、第 14 章（量測與迴圈最佳化）、第 15 章（locality 與記憶體階層）、第 16 章（cache 的 set、tag 與三種 miss）
>
> **對應 CS:APP 3e**：第 6 章 6.5–6.6 節

## 17.1 故事：直拍的照片特別慢

拾光相簿的手機 App 上傳的照片，大約一半是「直拍」：感光元件其實是橫著存的，只在 EXIF 裡註記「顯示時要轉 90 度」。`thumbd` 在縮圖之前會先把這種照片轉正。某天產品經理 Lisa 轉來客訴：「新款手機拍的直式照片，縮圖要等很久。」

小安去翻監控。同樣是 1,600 萬像素的照片，舊款手機的 4000×4000 原圖從頭到尾大約幾十毫秒，新款手機輸出的 4096×4096 卻慢了好幾倍；而且慢的部分幾乎全在「旋轉」這一步，縮放本身沒什麼差別。像素只多了 5%，時間卻翻了好幾倍，這完全不是演算法複雜度能解釋的。

小安把旋轉函式貼給老周看。那是一個再普通不過的雙層迴圈：`dst[j][W-1-i] = src[i][j]`。老周看了一眼就說：「這個迴圈讀 `src` 的時候是一格一格往右走，寫 `dst` 的時候卻是一列一列往下跳。每一次寫入都落在一個新的 cache line 上。而且 4096 剛好是 2 的冪，那些 line 全都擠進 cache 的同一個 set，互相把對方踢出去。」

第 15 章告訴我們 locality 很重要，第 16 章告訴我們 cache 怎麼用位址決定資料放在哪裡。這一章要把兩者變成**寫程式的手藝**：怎麼看一段迴圈就預測它的 miss rate、怎麼調整迴圈順序與資料布局、怎麼用 blocking 讓資料在 cache 裡被反覆使用，以及怎麼用量測確認你的推理是對的。本章最後會把 `thumbd` 的旋轉加速八倍以上。

## 17.2 從 cache 的角度讀一段迴圈

### 兩條基本規則

在高階語言裡，我們習慣用「做了幾次運算」衡量程式的成本。但第 15 章已經看到，一次 L1 hit 大約 1 ns，一次 DRAM 存取超過 100 ns。只要 miss 夠多，運算次數幾乎無關緊要。CS:APP 把寫 cache-friendly 程式的心法濃縮成兩條規則：

1. **把力氣花在最內層迴圈。** 程式大部分的記憶體存取都發生在最內層迴圈，外層的存取次數通常少好幾個數量級。分析效能時，先看最內層迴圈裡每一個陣列存取的走法。
2. **讓最內層迴圈的 miss 最少。** 具體做法有兩個：重複使用已經在 cache 裡的資料（temporal locality），以及按記憶體順序存取（spatial locality），最好是 **stride-1**。

stride（步幅，第 15 章）量的是相鄰兩次存取之間隔了幾個元素：`a[0]`、`a[1]`、`a[2]` 是 stride-1；`a[0]`、`a[8]`、`a[16]` 是 stride-8。stride 越大，每個被搬進 cache 的 line 裡被用到的 bytes 就越少。

### 手算 miss rate

用一個簡單的模型就能估算 miss rate：假設 cache line 大小是 B bytes、元素大小是 e bytes，而且資料量遠大於 cache（line 被用完一輪之後就會被踢掉，不會再回來）。

```text
stride-k 存取時，每個 line 裡會被用到的元素數 = max(1, B ÷ (k × e))
每次存取的平均 miss 數 ≈ min(1, k × e ÷ B)
```

以 x86-64 常見的 64-byte line、4-byte `int` 為例：

| stride（元素） | 每次跳幾 bytes | 每個 line 用到幾個元素 | 每次存取平均 miss | miss rate |
|---|---|---|---|---|
| 1 | 4 | 16 | 1/16 | 6.25% |
| 2 | 8 | 8 | 1/8 | 12.5% |
| 4 | 16 | 4 | 1/4 | 25% |
| 8 | 32 | 2 | 1/2 | 50% |
| 16 以上 | 64 以上 | 1 | 1 | 100% |

這張表的意思是：stride-1 時，每 16 次存取只有 1 次 miss，第一次把整條 line 搬上來，接下來 15 次都免費；stride 到 16 之後，每次存取都是一次完整的 miss，line 裡其他 60 bytes 全部浪費。Apple M 系列的 line 是 128 bytes，表格的轉折點要往後挪一倍，但道理完全相同。

### 例子：列優先與行優先加總

C 的二維陣列是 row-major（第 10 章）：`a[i][j]` 和 `a[i][j+1]` 相鄰，`a[i][j]` 和 `a[i+1][j]` 相隔一整列。下面兩個函式都把 4096×4096 的 `int` 陣列加總，只差在迴圈的巢狀順序：

```c
#define N 4096
long sum_rows(int a[N][N]) {          /* 內層走 j：stride-1 */
    long s = 0;
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            s += a[i][j];
    return s;
}
long sum_cols(int a[N][N]) {          /* 內層走 i：stride-N */
    long s = 0;
    for (int j = 0; j < N; j++)
        for (int i = 0; i < N; i++)
            s += a[i][j];
    return s;
}
```

先用前面的模型手算：

- `sum_rows`：內層 stride-1，每 16 次存取 1 次 miss，miss rate 6.25%。
- `sum_cols`：內層每次跳 4096 × 4 = 16,384 bytes，每次都落在不同的 line。一整行有 4,096 個元素，分別在 4,096 條 line 上，總共 4,096 × 64 bytes = 256 KiB。如果 cache 放得下這 256 KiB，下一行（`j+1`）就能重用這些 line；但常見的 L1 只有 32 到 48 KiB，所以等到回頭存取時早就被踢掉了。結論是 L1 miss rate 接近 100%。

兩者的 miss 數差了 16 倍。再看編譯器產生的組合語言（`clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - loops.c`，只保留最內層迴圈）：

```asm
# sum_rows 最內層：%rdx 是 j，位址 = %rdi + 4*j
.LBB0_2:
	movslq	(%rdi,%rdx,4), %rsi
	addq	%rsi, %rax
	incq	%rdx
	cmpq	$4096, %rdx
	jne	.LBB0_2

# sum_cols 最內層：%rdx 每次加 16384（一整列的 bytes）
.LBB1_2:
	movslq	(%rdi,%rdx), %rsi
	addq	%rsi, %rax
	addq	$16384, %rdx
	cmpq	$67108864, %rdx
	jne	.LBB1_2
```

兩個迴圈都是五條指令、一次 load、一次加法。從指令的角度看，它們的成本完全一樣；唯一的差別是位址每次前進 4 bytes 還是 16,384 bytes。下面實際量測：

```c
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define ROWS 4096
#define COLS 4096   /* 4096 × 4096 個 int = 64 MiB，遠大於任何一層 cache */

static double now_sec(void) {   /* 單調時鐘：不受系統校時影響 */
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static long sum_rows(int (*a)[COLS]) {      /* 內層走 j：stride-1 */
    long s = 0;
    for (int i = 0; i < ROWS; i++)
        for (int j = 0; j < COLS; j++)
            s += a[i][j];
    return s;
}

static long sum_cols(int (*a)[COLS]) {      /* 內層走 i：stride = COLS 個 int */
    long s = 0;
    for (int j = 0; j < COLS; j++)
        for (int i = 0; i < ROWS; i++)
            s += a[i][j];
    return s;
}

int main(void) {
    int (*a)[COLS] = malloc(sizeof(int[ROWS][COLS]));
    if (!a) return 1;
    for (int i = 0; i < ROWS; i++)
        for (int j = 0; j < COLS; j++)
            a[i][j] = (i + j) & 7;

    long (*fn[2])(int (*)[COLS]) = {sum_rows, sum_cols};
    const char *name[2] = {"列優先 (row-wise)  ", "行優先 (column-wise)"};
    for (int k = 0; k < 2; k++) {
        double best = 1e9; long s = 0;
        for (int rep = 0; rep < 3; rep++) {          /* 取三次中最快的一次 */
            double t0 = now_sec();
            s = fn[k](a);
            double t = now_sec() - t0;
            if (t < best) best = t;
        }
        printf("%s 總和 %ld  %7.1f ms  %5.2f ns/元素\n",
               name[k], s, best * 1e3, best * 1e9 / ((double)ROWS * COLS));
    }
    free(a);
    return 0;
}
```

在 macOS arm64（Apple M4 Pro，Apple clang 21，`-O1`）上執行：

```text
列優先 (row-wise)   總和 58720256      4.7 ms   0.28 ns/元素
行優先 (column-wise) 總和 58720256     61.5 ms   3.67 ns/元素
```

同樣的總和、同樣的指令數，行優先慢了 13 倍。手算預測的是「miss 數差 16 倍」，量到的時間差距略小，因為硬體預取器（prefetcher）能部分預測固定的大步幅、提早發出讀取。模型不會算出精確的時間，但它正確預測了**哪一個比較快、差距大約是什麼數量級**，這就是它在工作上的價值。

> [!warning] 常見誤解
> 「現代 CPU 有很大的 cache 和聰明的預取器，存取順序沒那麼重要了。」上面的實驗正是在一台 L2 有 16 MiB、預取器很積極的機器上跑的，差距仍然超過十倍。預取器能把延遲藏起來，卻沒辦法讓沒用到的 bytes 變得有用：stride 大的時候，記憶體頻寬被浪費在搬運不需要的資料上。

## 17.3 矩陣乘法：六種迴圈順序

矩陣乘法 C = A × B 是分析迴圈順序的經典例子，因為它有三層迴圈 `i`、`j`、`k`，可以排成 3! = 6 種順序，每一種算出的結果完全相同，運算次數也都是 n³ 次乘加，存取模式卻大不相同。影像處理、機器學習推論、科學計算都充滿這種三層迴圈，`thumbd` 的縮放（每個輸出像素是周圍輸入像素的加權和）也是同一種結構。

### 三類存取模式

六種順序依照「最內層迴圈是哪個變數」分成三類，最內層決定了一切：

```text
內層走 k（ijk、jik）：C[i][j] += A[i][k] * B[k][j]
   A[i][k]：同一列往右  → stride-1
   B[k][j]：同一行往下  → stride-n
   C[i][j]：固定不動    → 放在暫存器裡

內層走 j（kij、ikj）：C[i][j] += r * B[k][j]，r = A[i][k]
   B[k][j]：同一列往右  → stride-1
   C[i][j]：同一列往右  → stride-1
   A[i][k]：固定不動    → 放在暫存器裡

內層走 i（jki、kji）：C[i][j] += A[i][k] * r，r = B[k][j]
   A[i][k]：同一行往下  → stride-n
   C[i][j]：同一行往下  → stride-n
   B[k][j]：固定不動    → 放在暫存器裡
```

### 手算每次迭代的 miss 數

假設元素是 8-byte 的 `double`、cache line 64 bytes（一條 line 裝 8 個 `double`），n 很大，大到一整行的資料放不進 cache。用 17.2 節的模型逐一計算最內層每次迭代的平均 miss：

| 類別 | 迴圈順序 | 每次迭代的存取 | A 的 miss | B 的 miss | C 的 miss | 合計 |
|---|---|---|---|---|---|---|
| AB | ijk、jik | 2 次讀取 | 1/8 = 0.125 | 1 | 0 | **1.125** |
| BC | kij、ikj | 2 次讀取、1 次寫入 | 0 | 0.125 | 0.125 | **0.25** |
| AC | jki、kji | 2 次讀取、1 次寫入 | 1 | 0 | 1 | **2.0** |

推導過程：stride-1 的存取每 8 次才 miss 一次，貢獻 0.125；stride-n 的存取每次都是新的 line，貢獻 1；放在暫存器裡的值不存取記憶體，貢獻 0。BC 類雖然每次迭代多一次寫入，miss 卻最少，因為它的兩個陣列都是 stride-1。這說明了一個重要觀察：**存取次數不是重點，miss 次數才是**。

### 用模擬器驗證手算

手算模型有一些簡化（例如假設 line 用完就被踢掉）。我們用一個小型的 fully associative、LRU 的 cache 模擬器實際跑一遍，確認數字。為了讓「一整行放不進 cache」這個前提成立，把 cache 設得很小：只有 8 條 line（512 bytes），矩陣是 48×48。

```python
from collections import OrderedDict

N = 48                 # 矩陣 48×48 個 double
LINE = 64              # cache line 64 bytes = 8 個 double
LINES = 8              # 小 cache：8 條 line = 512 bytes，fully associative、LRU
BASE = {"A": 0, "B": N * N * 8, "C": 2 * N * N * 8}


class Cache:
    def __init__(self):
        self.lines = OrderedDict()
        self.misses = 0

    def touch(self, name, i, j):
        block = (BASE[name] + (i * N + j) * 8) // LINE
        if block in self.lines:
            self.lines.move_to_end(block)          # hit：變成最近使用
        else:
            self.misses += 1
            self.lines[block] = True
            if len(self.lines) > LINES:
                self.lines.popitem(last=False)     # 踢掉最久沒用的 line


def run(order):
    c = Cache()
    idx = {}
    rng = range(N)
    for idx[order[0]] in rng:                      # 依指定順序展開三層迴圈
        for idx[order[1]] in rng:
            for idx[order[2]] in rng:
                i, j, k = idx["i"], idx["j"], idx["k"]
                c.touch("A", i, k)
                c.touch("B", k, j)
                c.touch("C", i, j)
    return c.misses / N ** 3


for order in ("ijk", "jik", "kij", "ikj", "jki", "kji"):
    print(f"{order}: 每次內層迴圈平均 {run(order):.3f} 次 miss")
```

執行結果（Python 3，任何平台結果相同）：

```text
ijk: 每次內層迴圈平均 1.128 次 miss
jik: 每次內層迴圈平均 1.146 次 miss
kij: 每次內層迴圈平均 0.271 次 miss
ikj: 每次內層迴圈平均 0.253 次 miss
jki: 每次內層迴圈平均 2.021 次 miss
kji: 每次內層迴圈平均 2.003 次 miss
```

模擬結果和手算的 1.125、0.25、2.0 幾乎一致，多出來的一點點是外層迴圈切換時的額外 miss。如果把 `LINES` 改成 32，`kij`／`ikj` 會降到 0.15 以下，因為 C 的一整列（6 條 line）開始能留在 cache 裡被重用。這也提醒我們：手算模型描述的是「n 遠大於 cache」的情況，資料量小時，實際表現會比模型更好。

### 真實機器上的時間

下面是六種順序的 C 實作，矩陣 512×512（每個 2 MiB）：

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef N
#define N 512                       /* 每個矩陣 512×512 個 double = 2 MiB */
#endif
static double A[N][N], B[N][N], C[N][N];

static double now_sec(void) {   /* 回傳秒數（含小數） */
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

/* 六種迴圈順序；最內層迴圈決定記憶體的走法 */
static void ijk(void) { for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) { double s = 0;
    for (int k = 0; k < N; k++) s += A[i][k] * B[k][j]; C[i][j] += s; } }
static void jik(void) { for (int j = 0; j < N; j++) for (int i = 0; i < N; i++) { double s = 0;
    for (int k = 0; k < N; k++) s += A[i][k] * B[k][j]; C[i][j] += s; } }
static void kij(void) { for (int k = 0; k < N; k++) for (int i = 0; i < N; i++) { double r = A[i][k];
    for (int j = 0; j < N; j++) C[i][j] += r * B[k][j]; } }
static void ikj(void) { for (int i = 0; i < N; i++) for (int k = 0; k < N; k++) { double r = A[i][k];
    for (int j = 0; j < N; j++) C[i][j] += r * B[k][j]; } }
static void jki(void) { for (int j = 0; j < N; j++) for (int k = 0; k < N; k++) { double r = B[k][j];
    for (int i = 0; i < N; i++) C[i][j] += A[i][k] * r; } }
static void kji(void) { for (int k = 0; k < N; k++) for (int j = 0; j < N; j++) { double r = B[k][j];
    for (int i = 0; i < N; i++) C[i][j] += A[i][k] * r; } }

int main(void) {
    struct { const char *name; void (*fn)(void); } v[] = {
        {"ijk", ijk}, {"jik", jik}, {"kij", kij}, {"ikj", ikj}, {"jki", jki}, {"kji", kji}};
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++) { A[i][j] = (i + j) % 7; B[i][j] = (i * j) % 5; }
    double ops = (double)N * N * N;            /* 內層迴圈本體執行的次數 */
    for (size_t t = 0; t < sizeof v / sizeof v[0]; t++) {
        memset(C, 0, sizeof C);
        double t0 = now_sec();
        v[t].fn();
        double sec = now_sec() - t0;
        printf("%s  %7.1f ms  %5.2f ns/次內層迴圈  C[7][9] = %.0f\n",
               v[t].name, sec * 1e3, sec * 1e9 / ops, C[7][9]);
    }
    return 0;
}
```

在 macOS arm64（Apple M4 Pro，Apple clang 21，`-O1`）上執行：

```text
ijk    180.4 ms   1.34 ns/次內層迴圈  C[7][9] = 3061
jik    185.8 ms   1.38 ns/次內層迴圈  C[7][9] = 3061
kij     43.2 ms   0.32 ns/次內層迴圈  C[7][9] = 3061
ikj     39.0 ms   0.29 ns/次內層迴圈  C[7][9] = 3061
jki    699.1 ms   5.21 ns/次內層迴圈  C[7][9] = 3061
kji    731.5 ms   5.45 ns/次內層迴圈  C[7][9] = 3061
```

用 `cc -O1 -DN=1024` 重新編譯（每個矩陣 8 MiB）再執行一次：

```text
ijk   1363.2 ms   1.27 ns/次內層迴圈  C[7][9] = 6136
jik   1376.8 ms   1.28 ns/次內層迴圈  C[7][9] = 6136
kij    318.8 ms   0.30 ns/次內層迴圈  C[7][9] = 6136
ikj    309.8 ms   0.29 ns/次內層迴圈  C[7][9] = 6136
jki   7014.6 ms   6.53 ns/次內層迴圈  C[7][9] = 6136
kji   6931.0 ms   6.45 ns/次內層迴圈  C[7][9] = 6136
```

逐步解讀：

1. **三類清楚分成三組，同一類的兩種順序幾乎一樣快。** 這正是「最內層迴圈決定一切」的證據：`kij` 和 `ikj` 的外兩層不同，但最內層都是 stride-1 走 B 與 C。
2. **排名與手算一致**：BC 類（0.25 miss）最快，AB 類（1.125）居中，AC 類（2.0）最慢。最快與最慢差了約 20 倍（512 時約 19 倍、1024 時約 23 倍），運算次數卻完全相同。
3. **矩陣變大時，AC 類從 5.2 ns 惡化到 6.5 ns，BC 類幾乎不變。** 512 的時候，三個矩陣共 6 MiB，還放得進 16 MiB 的 L2；1024 的時候共 24 MiB，AC 類的 stride-n 存取開始頻繁落到 DRAM。BC 類只做 stride-1 存取，預取器能完美預測，所以不受影響。
4. **AB 類 1.3 ns 的一部分不是 cache 造成的。** `ijk` 的 `s += ...` 每次加法都要等上一次加法完成，形成一條長的相依鏈（第 14 章的關鍵路徑），浮點加法的 latency 本身就約 3 到 4 個 cycle。所以分析效能時要同時想「記憶體」與「相依關係」兩件事。

## 17.4 Blocking：讓資料在 cache 裡多用幾次

### 為什麼需要 blocking

迴圈重排改善的是 **spatial locality**：讓搬上來的 line 被用完。但 BC 類每次迭代仍有 0.25 次 miss，總共 n³/4 次 miss。仔細看 `ikj`：對每一個 `i`，它要把整個 B 矩陣從頭到尾掃一次。n = 1024 時，B 有 8 MiB，掃完一遍之後，開頭的部分早就被擠出 L1 了，下一個 `i` 只好再從更下層搬一次。B 的每個元素被用了 n 次，卻幾乎每次都要重新搬，**temporal locality** 完全沒發揮。

**Blocking**（分塊，也叫 **tiling**）的想法是：與其讓一個大迴圈掃過整個矩陣，不如把矩陣切成可以整個放進 cache 的小塊（block 或 tile），在小塊裡把所有該做的計算做完，再換下一塊。一個生活中的例子：圖書館整理書時，與其每處理一本就跑一趟書庫，不如一次搬一推車到桌邊，把這一車相關的工作全部做完。

```text
     C 的一個 block            A 的一列 block           B 的一行 block
 ┌──┬──┬──┬──┐           ┌──┬──┬──┬──┐           ┌──┬──┬──┬──┐
 │  │  │  │  │           │  │  │  │  │           │  │▓▓│  │  │
 ├──┼──┼──┼──┤           ├──┼──┼──┼──┤           ├──┼──┼──┼──┤
 │  │▓▓│  │  │   +=      │▓▓│▓▓│▓▓│▓▓│    ×      │  │▓▓│  │  │
 ├──┼──┼──┼──┤           ├──┼──┼──┼──┤           ├──┼──┼──┼──┤
 │  │  │  │  │           │  │  │  │  │           │  │▓▓│  │  │
 ├──┼──┼──┼──┤           ├──┼──┼──┼──┤           ├──┼──┼──┼──┤
 │  │  │  │  │           │  │  │  │  │           │  │▓▓│  │  │
 └──┴──┴──┴──┘           └──┴──┴──┴──┘           └──┴──┴──┴──┘
   每格是 b×b            依序取出 n/b 個 block     依序取出 n/b 個 block
   C 的這一塊 = Σ（A 的第 r 塊 × B 的第 r 塊），r = 1..n/b
```

圖中 C 被切成 (n/b)² 個 b×b 的小塊。要算出 C 的一個小塊，需要 A 的同一列小塊和 B 的同一行小塊，兩兩相乘再累加。關鍵是：每一次「小塊乘小塊」只碰三個 b×b 的區域，只要這三塊同時放得進 cache，裡面的 b³ 次乘加就只需要付出搬三個小塊的 miss。

### 手算：blocking 省下多少 miss

沿用前面的假設（8 個 `double` 一條 line），並假設三個 b×b 的小塊放得進 cache：

| 步驟 | 計算 | 結果 |
|---|---|---|
| 搬一個 b×b 小塊的 miss | b² 個元素 ÷ 每條 line 8 個 | b²/8 |
| 算 C 的一個小塊：A、B 各要搬 n/b 塊 | 2 × (n/b) × b²/8 | nb/4 |
| C 一共有 (n/b)² 個小塊 | (n/b)² × nb/4 | **n³/(4b)** |
| 對照：不分塊的 BC 類 | 0.25 × n³ | n³/4 |

blocking 讓 miss 數再少 b 倍。n = 1024、b = 64 時，從約 2.7 億次降到約 420 萬次。

b 不能任意大，前提是三個小塊同時放得進 cache：3 × b² × 8 bytes ≤ cache 容量。

```text
x86-64 常見 L1d 48 KiB：3 × b² × 8 ≤ 49,152 → b² ≤ 2,048 → b ≤ 45，取 32
Apple M4 效能核心 L1d 128 KiB：3 × b² × 8 ≤ 131,072 → b² ≤ 5,461 → b ≤ 73，取 64
```

實務上會取比上限再小一點的 2 的冪或 8 的倍數，因為 cache 裡還有別的資料（stack、迴圈變數、其他陣列），而且 set associative cache 不能像理想模型那樣完美地裝滿。

### 實測：blocking 不一定會贏

```c
#include <stdio.h>
#include <string.h>
#include <time.h>

#define N 1024                        /* 每個矩陣 8 MiB */
static double A[N][N], B[N][N], C[N][N];

static double now_sec(void) {   /* 計時用 */
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static void ikj(void) {               /* 17.3 節最快的順序，當作比較基準 */
    for (int i = 0; i < N; i++)
        for (int k = 0; k < N; k++) {
            double r = A[i][k];
            for (int j = 0; j < N; j++) C[i][j] += r * B[k][j];
        }
}

/* 把三個矩陣切成 bs×bs 的小塊；最內三層只在三個小塊裡打轉 */
static void blocked(int bs) {
    for (int ii = 0; ii < N; ii += bs)
        for (int kk = 0; kk < N; kk += bs)
            for (int jj = 0; jj < N; jj += bs)
                for (int i = ii; i < ii + bs; i++)
                    for (int k = kk; k < kk + bs; k++) {
                        double r = A[i][k];
                        for (int j = jj; j < jj + bs; j++) C[i][j] += r * B[k][j];
                    }
}

int main(void) {
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++) { A[i][j] = (i + j) % 7; B[i][j] = (i * j) % 5; }
    double t0 = now_sec();
    ikj();
    printf("ikj（不分塊）   %7.1f ms  C[7][9] = %.0f\n", (now_sec() - t0) * 1e3, C[7][9]);
    int sizes[] = {32, 64, 128};
    for (int s = 0; s < 3; s++) {
        memset(C, 0, sizeof C);
        t0 = now_sec();
        blocked(sizes[s]);
        printf("blocked bs=%-4d %7.1f ms  C[7][9] = %.0f\n", sizes[s], (now_sec() - t0) * 1e3, C[7][9]);
    }
    return 0;
}
```

在 macOS arm64（Apple M4 Pro，Apple clang 21）上，分別用 `-O1` 與 `-O3` 編譯執行（`== -O1 ==` 兩行是為了區分兩次執行而加上的標示）：

```text
== -O1 ==
ikj（不分塊）     304.3 ms  C[7][9] = 6136
blocked bs=32     383.0 ms  C[7][9] = 6136
blocked bs=64     405.5 ms  C[7][9] = 6136
blocked bs=128    353.0 ms  C[7][9] = 6136
== -O3 ==
ikj（不分塊）     139.1 ms  C[7][9] = 6136
blocked bs=32     138.1 ms  C[7][9] = 6136
blocked bs=64     117.3 ms  C[7][9] = 6136
blocked bs=128    168.4 ms  C[7][9] = 6136
```

這個結果值得仔細讀，因為它和「blocking 一定快很多」的直覺不同：

1. **`-O1` 時 blocking 反而變慢。** 這時程式是**運算受限**的：純量程式每次迭代要約 0.3 ns，記憶體系統（加上預取器）跟得上 `ikj` 的 stride-1 存取，miss 並不是瓶頸。blocking 多了三層迴圈的開銷、內層迴圈變短，所以變慢。
2. **`-O3` 時 bs=64 快了約 16%，bs=128 反而變慢。** `-O3` 會用 SIMD 指令一次處理多個 `double`（第 14 章），運算變快，記憶體開始成為瓶頸，減少 miss 就有回報。bs=64 剛好是前面手算的 L1 上限（73）以下的最大選擇；bs=128 時三個小塊要 384 KiB，放不進 L1，優勢就消失了。
3. **在這台機器上，blocking 的收益比教科書小。** M4 Pro 的 L2 有 16 MiB，B 的 8 MiB 放得進 L2，「被擠出 L1」的代價只是一次 L2 存取。在 L2 只有 1 到 2 MiB、多核心共用 L3 與記憶體頻寬的伺服器上，或是多個執行緒同時搶頻寬時，blocking 的效果通常更明顯。

這就是第 14 章一再強調的原則：**先量測，確認瓶頸在哪裡，再選最佳化手段**。blocking 是減少 miss 的工具，如果 miss 不是瓶頸，它只會增加複雜度。真正的高效能矩陣乘法函式庫（OpenBLAS、Intel MKL、Apple Accelerate）會同時對暫存器、L1、L2、L3 各做一層 blocking，再加上 SIMD 與資料重新打包，自己寫的版本很難追上。工作上需要矩陣運算時，請直接呼叫 BLAS。

## 17.5 Memory mountain：一張圖看懂一台機器的記憶體系統

前面兩節分別討論了 spatial locality（stride）與 temporal locality（working set 大小）。**Memory mountain**（記憶體山）把這兩個維度畫在同一張圖上：x 軸是 working set 大小，y 軸是 stride，高度是讀取吞吐量（MB/s）。第 15 章用指標追逐量了每一層的延遲、用 stride 實驗看了 line 大小；memory mountain 則是同時改變兩者，量測「頻寬」。

程式的核心是一個以固定 stride 掃過前 `elems` 個元素的函式，並用四個累加器讓 CPU 能同時發出多個 load，量到的才是記憶體系統的吞吐量，而不是加法的相依鏈：

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define MAXBYTES (64L << 20)            /* 最大工作集 64 MiB */
#define MAXELEMS (MAXBYTES / sizeof(long))
static long data[MAXELEMS];
static volatile long sink;              /* 防止編譯器把整個迴圈刪掉 */

static double now_sec(void) {   /* 量測用的時鐘 */
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

/* 以 stride 讀取前 elems 個 long，四個累加器讓 CPU 可以同時發出多個 load */
static void scan(long elems, long stride) {
    long a0 = 0, a1 = 0, a2 = 0, a3 = 0, s4 = stride * 4, limit = elems - s4, i;
    for (i = 0; i < limit; i += s4) {
        a0 += data[i];              a1 += data[i + stride];
        a2 += data[i + 2 * stride]; a3 += data[i + 3 * stride];
    }
    for (; i < elems; i += stride) a0 += data[i];
    sink = a0 + a1 + a2 + a3;
}

/* 回傳讀取吞吐量（MB/s）：工作集先暖身，再量固定總讀取量 */
static double throughput(long bytes, long stride) {
    long elems = bytes / (long)sizeof(long);
    long touched = elems / stride;                     /* 每輪實際讀幾個 long */
    long rounds = (128L << 20) / (touched * (long)sizeof(long)) + 1;
    double best = 1e9;
    scan(elems, stride);                               /* 暖身：把資料帶進 cache */
    for (int rep = 0; rep < 3; rep++) {                /* 取三次中最快的，降低雜訊 */
        double t0 = now_sec();
        for (long r = 0; r < rounds; r++) scan(elems, stride);
        double sec = now_sec() - t0;
        if (sec < best) best = sec;
    }
    return (double)rounds * touched * sizeof(long) / best / 1e6;
}

int main(void) {
    for (long i = 0; i < (long)MAXELEMS; i++) data[i] = i;
    long strides[] = {1, 2, 4, 8, 16, 32};
    printf("%8s", "size\\stride");
    for (int s = 0; s < 6; s++) printf("%8ld", strides[s]);
    printf("   (MB/s)\n");
    for (long bytes = MAXBYTES; bytes >= (16L << 10); bytes >>= 1) {
        if (bytes >= (1L << 20)) printf("%8ldM  ", bytes >> 20);
        else                     printf("%8ldK  ", bytes >> 10);
        for (int s = 0; s < 6; s++) printf("%8.0f", throughput(bytes, strides[s]));
        printf("\n");
    }
    return 0;
}
```

在 macOS arm64（Apple M4 Pro，`-O1`）上執行（stride 的單位是 8-byte 的 `long`）：

```text
size\stride       1       2       4       8      16      32   (MB/s)
      64M     67787   39457   21804   11855    3330    2873
      32M     67297   39673   23732   12938    4282    5896
      16M     79849   49706   28776   14548   11059   10528
       8M     78919   53586   31129   15427   14778   11168
       4M     73079   54265   31031   15111   14865   14203
       2M     82917   54742   31241   15577   15770   14144
       1M     77163   52737   30418   15344   15242   13024
     512K     79494   53238   31611   16719   15890   14490
     256K     82150   55793   33018   22941   16039   14254
     128K     91084   90548   86003   73232   50404   27882
      64K     91786   92714   87392   74819   55054   30884
      32K     92639   93608   88481   74817   55532   31522
      16K     92896   90693   85383   76391   53538   29780
```

把表格想成一座山的等高線圖。沿著兩個方向切開來看：

```text
 固定 stride = 4，沿 working set 看（temporal locality 的山脊）
 MB/s
 90000 ┤███████████████
       │               ╲
 30000 ┤                ╲████████████████████████
       │                                         ╲
 20000 ┤                                          ╲██████
       └──┬────┬────┬────┬────┬────┬────┬────┬────┬────
         16K  64K 128K 256K  1M   4M  16M  32M  64M
         └── L1 ──┘ └────── L2 ──────────┘ └ DRAM ┘
```

1. **山脊（ridge）：沿著 working set 方向的平台與斷崖。** 每一個平台對應一層 cache。128 KiB 以下的資料放在 L1（效能核心的 L1d 是 128 KiB），stride-4 有 86 GB/s；256 KiB 到 8 MiB 落在 L2，降到約 31 GB/s；32 MiB 以上主要靠 DRAM，降到約 22 GB/s。16 MiB 剛好是 L2 的容量，處在過渡區。這些斷崖是 **temporal locality** 的地形：working set 越小，資料越能留在上層被重複使用。
2. **斜坡（slope）：沿著 stride 方向往下。** 在 L2 與 DRAM 區域，stride 從 1 增加到 8，吞吐量幾乎每次減半：stride 加倍，每條 line 裡被用到的 bytes 就減半。這是 **spatial locality** 的地形。到了 stride 16（128 bytes，等於 Apple M 系列的 line 大小）之後，每次讀取都是一條新的 line，L2 區域的斜坡就變平了（stride 8、16 都約 15 GB/s）。DRAM 區域在 stride 16 反而又掉了一大截（64 MiB 時從約 12 GB/s 掉到約 3 GB/s），可能是預取器對跨 line 的大步幅效果變差，加上 DRAM 的 row buffer 較少命中；這一點是依量測結果推論，不同機器的表現會不同。
3. **L1 區域的斜坡比較緩。** 資料都在 L1 時，stride 1 到 4 幾乎一樣快，因為 L1 每個 cycle 可以服務多次 load，瓶頸在指令本身，而不是搬資料。
4. **stride-1 在 DRAM 區域仍有約 67 GB/s。** 這是硬體預取器的功勞：它偵測到循序存取，提早把後面的 line 搬上來，把 DRAM 的延遲藏了起來。這也是為什麼循序掃描大資料（資料庫的 full scan、log 處理）比隨機存取快得多。

> [!note] 每台機器的山都不一樣
> 在 Linux x86-64 伺服器上執行同一個程式，你會看到 L1 平台在 32 或 48 KiB 結束、L2 平台在 1 到 2 MiB 結束、接著有一段很寬的 L3 平台，line 大小造成的斜坡轉折在 stride 8（64 bytes）。memory mountain 是了解一台陌生機器最快的方法之一：它直接告訴你「多大的 working set 可以保持高速」。

## 17.6 資料布局：AoS、SoA 與熱冷分離

迴圈順序決定了「怎麼走過資料」，**資料布局**（data layout）決定了「資料在記憶體裡怎麼排」。即使迴圈已經是 stride-1，如果每個元素裡大部分欄位都用不到，搬上來的 line 仍然大半浪費。

### AoS 與 SoA

`thumbd` 有一個縮圖快取，每筆紀錄有 key、寬、高、命中次數、旗標與檔案路徑。最直覺的寫法是 **AoS**（array of structures，結構陣列）：每筆紀錄是一個 struct，整個快取是 struct 的陣列。另一種寫法是 **SoA**（structure of arrays，陣列結構）：每個欄位各自是一個陣列。

```text
 AoS：一筆紀錄的欄位放在一起（每筆 64 bytes）
 ┌key─────┬w──┬h──┬hits┬flag┬path────────────────────┐┌key─────┬w──┬...
 │ 8 B    │4 B│4 B│4 B │4 B │ 40 B                   ││        │   │
 └────────┴───┴───┴────┴────┴────────────────────────┘└────────┴───┴...
   掃描 hits 時：每 64 bytes 只用到 4 bytes

 SoA：同一個欄位的值放在一起
 hits:  ┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬...
        │ h0 │ h1 │ h2 │ h3 │ h4 │ h5 │ h6 │ h7 │ h8 │ h9 │h10 │h11 │
        └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴...
   掃描 hits 時：每條 64-byte line 裡的 16 個值全部用到
 width: ┌────┬────┬...
 key:   ┌────────┬────────┬...
```

清理快取時，`thumbd` 要掃過所有紀錄的 `hits` 欄位，找出命中次數最低的淘汰。下面的程式比較兩種布局：

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define COUNT (1 << 20)                 /* 一百萬張縮圖的快取紀錄 */

/* AoS：一筆紀錄的所有欄位放在一起，64 bytes 一筆 */
struct entry {
    uint64_t key;
    uint32_t width, height;
    uint32_t hits;                      /* 掃描時只用到這個欄位 */
    uint32_t flags;
    char     path[40];
};

/* SoA：同一個欄位的值放在同一個陣列 */
struct table {
    uint64_t *key;
    uint32_t *width, *height, *hits, *flags;
    char    (*path)[40];
};

static double now_sec(void) {   /* 單調時鐘，單位為秒 */
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(void) {
    struct entry *aos = calloc(COUNT, sizeof *aos);
    struct table soa = { .hits = calloc(COUNT, sizeof(uint32_t)) };
    if (!aos || !soa.hits) return 1;
    for (int i = 0; i < COUNT; i++) aos[i].hits = soa.hits[i] = (uint32_t)(i % 13);

    double best_aos = 1e9, best_soa = 1e9;
    uint64_t s1 = 0, s2 = 0;
    for (int rep = 0; rep < 5; rep++) {
        double t0 = now_sec();
        s1 = 0;
        for (int i = 0; i < COUNT; i++) s1 += aos[i].hits;   /* stride 64 bytes */
        double t1 = now_sec();
        s2 = 0;
        for (int i = 0; i < COUNT; i++) s2 += soa.hits[i];   /* stride 4 bytes */
        double t2 = now_sec();
        if (t1 - t0 < best_aos) best_aos = t1 - t0;
        if (t2 - t1 < best_soa) best_soa = t2 - t1;
    }
    printf("sizeof(struct entry) = %zu bytes\n", sizeof(struct entry));
    printf("AoS 掃 hits：總和 %llu，%.2f ms，掃過 %zu MiB\n", (unsigned long long)s1,
           best_aos * 1e3, (size_t)COUNT * sizeof(struct entry) >> 20);
    printf("SoA 掃 hits：總和 %llu，%.2f ms，掃過 %zu MiB\n", (unsigned long long)s2,
           best_soa * 1e3, (size_t)COUNT * sizeof(uint32_t) >> 20);
    free(aos); free(soa.hits);
    return 0;
}
```

在 macOS arm64（Apple M4 Pro，`-O1`）上執行：

```text
sizeof(struct entry) = 64 bytes
AoS 掃 hits：總和 6291438，0.79 ms，掃過 64 MiB
SoA 掃 hits：總和 6291438，0.28 ms，掃過 4 MiB
```

SoA 快了約 2.8 倍。原因有兩層：第一，AoS 為了 4 MiB 的有用資料搬了 64 MiB，SoA 只搬 4 MiB，記憶體流量差 16 倍；第二，SoA 的 4 MiB 放得進 L2，重複掃描時都從 L2 讀，而 AoS 的 64 MiB 每次都要到 DRAM。時間差距小於 16 倍，是因為循序存取時預取器很有效率，而且迴圈本身也有固定的指令成本。

但 SoA 不是永遠比較好。當程式「一次要用到一筆紀錄的多數欄位」（例如回應一個請求時要讀 key、寬、高、路徑），AoS 只要碰一兩條 line，SoA 卻要從五六個陣列各取一條。選擇的依據永遠是**最熱的存取模式**：

| 布局 | 適合的存取模式 | 例子 | 缺點 |
|---|---|---|---|
| AoS | 一次處理一筆紀錄的多數欄位 | 依 key 查快取、處理單一 HTTP 請求 | 只掃單一欄位時浪費頻寬 |
| SoA | 批次掃描少數欄位 | 統計、淘汰、SIMD 運算、欄式資料庫 | 讀寫單筆紀錄要碰多個陣列 |
| 熱冷分離（hot/cold splitting） | 少數欄位很熱、其他很少用 | 把 `key`、`hits` 留在主 struct，`path` 移到另一個陣列 | 冷資料要多一次間接存取 |
| AoSoA（分組交錯） | 需要 SIMD 又要保留區域性 | 每 8 筆紀錄一組，組內 SoA | 程式較複雜 |

這個取捨在業界隨處可見：欄式資料庫（ClickHouse、Parquet 檔案格式）就是 SoA，因為分析查詢通常只讀少數欄位；遊戲引擎的 entity component system 用 SoA 讓每幀更新位置時只掃位置陣列；機器學習框架在 NCHW 與 NHWC 兩種張量布局之間選擇，也是同一個問題。

### 指標追逐：linked list 為什麼慢

另一種常見的不友善布局是**指標追逐**（pointer chasing）。linked list、樹、以指標串起來的物件圖，每個節點可能散落在 heap 的任何地方。走訪時，下一個節點的位址要等目前節點讀進來才知道，CPU 無法預先發出讀取，預取器也猜不到規律，所以每一步都可能付出一次完整的 miss 延遲（第 15 章用這個特性量測了每一層的延遲）。

工作上的對策：能用陣列就用陣列（`std::vector` 通常比 `std::list` 快，即使中間插入是 O(n)）；需要指標結構時，用 arena 或 pool 配置，讓節點在記憶體中靠在一起；hash table 用 open addressing（資料存在連續陣列裡）而不是每個 bucket 一條 linked list；B-tree 一個節點放很多 key，正是為了讓每一次「跳指標」換來一整條 line 甚至一整頁的有用資料。

### 欄位順序與對齊

第 10 章介紹過 struct 的 padding。從 cache 的角度，還有兩個要點：一，把一起使用的欄位放在一起，最好在同一條 line 裡；二，經常整批存取的 struct，大小最好剛好是 line 的整數倍或因數，並且對齊 line 的邊界，避免一筆紀錄橫跨兩條 line。C11 的 `_Alignas(64)` 或 `aligned_alloc(64, size)` 可以指定對齊。

## 17.7 多核心的陷阱：false sharing 預告

到目前為止我們只看單一核心。多核心時還有一個 cache 層級的陷阱，它的根源和本章一樣：**cache 以 line 為單位運作**。

每個核心有自己的 L1 與 L2。當核心 A 寫入某條 line 時，硬體的 **cache coherence**（快取一致性）協定必須讓其他核心手上的同一條 line 失效，確保大家不會讀到舊資料。如果兩個核心各自寫入**不同的變數**，但這兩個變數剛好在**同一條 line** 裡，這條 line 就會在兩個核心之間來回傳遞，每次寫入都像一次 miss。這叫 **false sharing**（偽共享）：程式邏輯上沒有共享，硬體卻把它們當成共享。

```text
 struct { long count_a; long count_b; } stats;   // 兩個計數器只差 8 bytes

        核心 0（thread A）               核心 1（thread B）
        ┌──────────────────┐            ┌──────────────────┐
        │ L1：stats 那條 line│◀── 失效 ──│ 寫 count_b       │
        │ 寫 count_a        │── 失效 ──▶│ L1：stats 那條 line│
        └──────────────────┘            └──────────────────┘
          line 在兩個核心之間來回傳遞，每次寫入都要等對方交出這條 line
```

`thumbd` 的 thread pool 若讓每個 worker 在一個緊密排列的陣列裡更新自己的統計數字，就會遇到這個問題：明明每個 thread 只寫自己的計數器，加 thread 卻變慢。修法是讓每個 thread 的資料各自佔一條 line（例如 `_Alignas(64)` 或在中間補 padding），或讓每個 thread 先在區域變數累加，最後再合併。第 32 章會實際量測 false sharing 的代價，並討論 Apple M 系列 128-byte line 對 padding 大小的影響。

## 17.8 動手做：讓 thumbd 的旋轉快八倍

現在回到 17.1 節的客訴。旋轉 90 度的本質是**轉置**（transpose）：讀的時候一列一列走，寫的時候一行一行走。不管迴圈怎麼排，`src` 和 `dst` 總有一個是 stride-n，不能像矩陣乘法那樣靠重排迴圈解決。這正是 blocking 最能發揮的場合。

### 原始版本為什麼慢：手算 conflict miss

先用一台典型的 x86-64 伺服器來手算（Intel Skylake 世代的 L1d：32 KiB、8-way、64-byte line）：

```text
set 數 S = 32 KiB ÷ (8 ways × 64 B) = 64 個 set
位址切分：offset = log2(64) = 6 bits，set index = log2(64) = 6 bits（第 6–11 位元）
→ 位址相差 4,096 的整數倍時，set index 完全相同

dst 的一行（同一個 j、連續的 i）：相鄰像素在記憶體中相差
  W × 4 bytes = 4096 × 4 = 16,384 bytes = 4 × 4,096
→ 一整行 4,096 個像素全部落在「同一個 set」
→ 這個 set 只有 8 個 way，第 9 條 line 進來就要踢掉一條
```

這就是第 16 章的 **conflict miss**：cache 總容量還有很多空間，但所有資料都被位址映射到同一個 set，互相踢出。原始版本每寫一個像素就要搬一條新的 line，下一列（`i+1`）要寫隔壁的像素時，那條 line 早已被踢掉，64 bytes 只用了 4 bytes。

如果寬度不是 2 的冪會怎樣？以 4000 為例，一列是 16,000 bytes，16,000 mod 4,096 = 3,712，相鄰列的 set index 每次位移 3,712 ÷ 64 = 58 個 set（模 64）。因為 58 和 64 的最大公因數是 2，一整行會輪流落在 32 個不同的 set 上，總共 32 × 8 = 256 條 line 的空間，而不是全部擠在同一個 set 的 8 條 line 裡。這解釋了為什麼 4000×4000 比 4096×4096 快：不是像素少了 5%，而是 conflict miss 消失了。

### 修法：tiling ＋ 列尾留白

修法有兩個，正好對應兩個問題：

1. **Tiling**：把影像切成 t×t 的小塊，一次轉完一小塊。在一個小塊內，`dst` 的寫入只碰 t 條 line，每條 line 會被連續寫 t 次（同一列的 t 個相鄰像素），line 被踢掉之前就用完了。
2. **列尾留白**（padding）：讓每一列實際佔的空間（也就是第 10 章的 pitch，列距）比寬度多一點，例如 4096 + 32 個像素。這樣相鄰列的位址差不再是 4,096 的倍數，`dst` 一行的 line 就會分散到不同的 set。很多影像函式庫（例如 GPU 的 texture、FFmpeg 的 frame buffer）本來就允許 pitch 大於寬度，就是為了對齊與避開這類衝突。

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define W 4096                       /* 4096×4096 的 RGBA 影像，一個像素 4 bytes */

static double now_sec(void) {   /* 計時：CLOCK_MONOTONIC */
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

/* 順時針轉 90 度：src 的第 i 列第 j 行 → dst 的第 j 列第 (W-1-i) 行。
 * pitch 是「一列佔幾個像素的空間」，可以大於 W（列尾留白）。tile = 1 就是原始寫法。 */
static void rotate(const uint32_t *src, uint32_t *dst, int pitch, int tile) {
    for (int ii = 0; ii < W; ii += tile)
        for (int jj = 0; jj < W; jj += tile)
            for (int i = ii; i < ii + tile; i++)
                for (int j = jj; j < jj + tile; j++)
                    dst[(size_t)j * pitch + (W - 1 - i)] = src[(size_t)i * pitch + j];
}

static double best_ms(const uint32_t *src, uint32_t *dst, int pitch, int tile) {
    double best = 1e9;
    for (int rep = 0; rep < 3; rep++) {
        double t0 = now_sec();
        rotate(src, dst, pitch, tile);
        double t = now_sec() - t0;
        if (t < best) best = t;
    }
    return best * 1e3;
}

int main(void) {
    int pitches[] = {W, W + 32};          /* 第二種：每列多留 32 個像素（128 bytes） */
    int tiles[] = {1, 8, 32, 64};
    for (int p = 0; p < 2; p++) {
        int pitch = pitches[p];
        uint32_t *src = malloc((size_t)W * pitch * sizeof *src);
        uint32_t *dst = malloc((size_t)W * pitch * sizeof *dst);
        if (!src || !dst) return 1;
        for (size_t i = 0; i < (size_t)W * pitch; i++) { src[i] = (uint32_t)i; dst[i] = 0; }
        printf("pitch = %d 像素（一列 %d bytes）\n", pitch, pitch * 4);
        for (int t = 0; t < 4; t++) {
            double ms = best_ms(src, dst, pitch, tiles[t]);
            int ok = dst[(size_t)5 * pitch + (W - 1 - 7)] == src[(size_t)7 * pitch + 5];
            printf("  tile %2d × %-2d  %6.1f ms  %s\n", tiles[t], tiles[t], ms, ok ? "結果正確" : "結果錯誤");
        }
        free(src);
        free(dst);
    }
    return 0;
}
```

在 macOS arm64（Apple M4 Pro，Apple clang 21，`-O1`）上執行：

```text
pitch = 4096 像素（一列 16384 bytes）
  tile  1 × 1     84.0 ms  結果正確
  tile  8 × 8     32.0 ms  結果正確
  tile 32 × 32    72.9 ms  結果正確
  tile 64 × 64    72.4 ms  結果正確
pitch = 4128 像素（一列 16512 bytes）
  tile  1 × 1     64.4 ms  結果正確
  tile  8 × 8     14.3 ms  結果正確
  tile 32 × 32     8.2 ms  結果正確
  tile 64 × 64    10.8 ms  結果正確
```

逐步解讀：

1. **原始寫法（tile 1、pitch 4096）84 ms，最佳組合（tile 32、pitch 4128）8.2 ms，快了約 10 倍。** 演算法、運算次數、輸出都沒變，只改了存取順序與記憶體布局。重複執行時最佳組合在 8 到 10 ms 之間浮動，所以標題保守地寫「八倍」。
2. **pitch 4096 時，tile 8 有幫助，tile 32 以上幾乎打回原形。** 這是 conflict miss 的指紋：一個 t×t 的 tile 要同時保留 `dst` 的 t 條 line（`src` 也一樣，相鄰列同樣相差 16 KiB），而它們全都落在同一個 set。t 小的時候還裝得下，t 一旦超過 set 的容量就開始互相踢出。Apple 沒有公開 M4 的 L1 associativity，所以無法從規格算出確切的臨界值；可以確定的是這台機器的 line 是 128 bytes、L1d 是 128 KiB，假如它是 8-way，set 數就是 128 KiB ÷ (8 × 128 B) = 128，set index 的週期是 128 × 128 B = 16 KiB，正好等於一列的 bytes。這只是與量測結果一致的推論，不是官方規格。
3. **pitch 改成 4128 之後，大 tile 開始發揮作用。** 每列多 128 bytes，相鄰列的 set index 就錯開一個 set，一行的 line 分散到不同 set。conflict miss 消失後，tile 越大，每條 line 在被踢出前用到的 bytes 就越多：tile 8 時一個 tile 只用到 128-byte line 的 32 bytes，tile 32 時剛好用滿一條 line。tile 32 與 tile 64 的差距在量測誤差內，重跑時兩者互有勝負；tile 再大，working set 終究會超過 L1 與 TLB 的覆蓋範圍。
4. **連 tile 1 也從 84 ms 變成 64 ms。** padding 本身就減少了 conflict miss，即使不改迴圈也有幫助。

`thumbd` 最後的修法是：配置影像緩衝區時，pitch 一律向上取整到「64 bytes 的倍數，且不是 4 KiB 的倍數」（實作上就是：向上取整後如果剛好是 4 KiB 的倍數，例如寬度是 2 的冪的影像，就再多加一條 line），旋轉與轉置改用 32×32 的 tile。修完之後，新款手機的直拍照片和舊款一樣快。

> [!tip] 4K aliasing
> 2 的冪次 stride 不只造成 cache 的 conflict miss。在 Intel 處理器上，load 與更早的 store 如果位址的低 12 位元相同，硬體可能誤判兩者相依而延遲 load，Intel 的文件稱為 4K aliasing。兩個問題的對策相同：避免讓熱的陣列以 4 KiB 的整數倍互相錯開。

## 17.9 在工作上怎麼用

### 確認 cache 是不是瓶頸：perf stat

前面的分析都是推理。在 Linux 上，`perf stat` 可以讀取 CPU 的硬體效能計數器（PMU），直接告訴你 miss 有多少：

```bash
# 整體：IPC 與 cache 相關事件（事件名稱依 CPU 而定，perf list 可列出）
perf stat -e cycles,instructions,cache-references,cache-misses ./thumbd_bench

# L1 data cache 與 LLC（last-level cache）的 load 與 miss
perf stat -e L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses ./thumbd_bench

# 對執行中的服務量 10 秒
perf stat -e cycles,instructions,L1-dcache-load-misses -p "$(pgrep thumbd)" -- sleep 10

# 找出 miss 發生在哪一行程式（需要 -g 編譯以對應原始碼）
perf record -e L1-dcache-load-misses -g ./thumbd_bench
perf report
```

讀 `perf stat` 的結果時，看這幾個比例：

| 指標 | 怎麼算 | 怎麼解讀 |
|---|---|---|
| IPC | instructions ÷ cycles | 現代 x86 核心每個 cycle 可以執行好幾條指令；IPC 明顯低於 1 時，CPU 多半在等東西，常常是等記憶體 |
| L1 miss rate | L1-dcache-load-misses ÷ L1-dcache-loads | 循序處理的程式通常只有幾個百分比；明顯偏高時，檢查最內層迴圈的 stride |
| LLC miss rate | LLC-load-misses ÷ LLC-loads | 高表示 working set 超過最後一層 cache，資料要到 DRAM |
| 前後比較 | 修改前後各量一次 | 最佳化後 miss 數下降、時間也下降，才證明推理正確 |

macOS 沒有 `perf`；Apple Silicon 上可以用 Xcode 的 Instruments 中的 CPU Counters 工具讀取效能計數器。另一個跨平台的選擇是 Valgrind 的 **Cachegrind**（`valgrind --tool=cachegrind ./prog`），它用模擬的方式統計每一行程式的 cache miss，速度慢很多，但結果穩定、可以精確對應到原始碼，很適合比較兩個版本。

### 判斷流程

當一段程式「比預期慢」，可以照這個流程檢查是否和 cache 有關：

```text
程式比預期慢
  │
  ├─ 1. profiler 找出熱點函式（perf record／perf report，第 14 章）
  │
  ├─ 2. 量 IPC 與 miss：perf stat -e cycles,instructions,L1-dcache-load-misses,LLC-load-misses
  │      ├─ IPC 高、miss 少 → 運算受限：減少指令、SIMD、多累加器（第 14 章）
  │      └─ IPC 低、miss 多 → 記憶體受限，繼續往下
  │
  ├─ 3. 看熱點的最內層迴圈
  │      ├─ 有 stride-n 存取？        → 重排迴圈、改布局（AoS → SoA）
  │      ├─ 有指標追逐？              → 改用陣列、arena 配置
  │      ├─ working set 大於 cache？  → blocking／tiling、資料壓縮（更小的型別）
  │      └─ stride 是 2 的冪？         → 加 padding 避開 conflict miss
  │
  ├─ 4. 多執行緒時加 thread 反而變慢？ → 懷疑 false sharing（perf c2c，第 32 章）
  │
  └─ 5. 修改後重新量測：時間與 miss 都下降，才算完成
```

### 工作上會遇到的情境

- **後端服務的熱路徑**：一個 request 要查好幾層 map、走一串物件指標。把熱資料攤平成連續陣列、用 open addressing 的 hash table（例如 Abseil 的 `flat_hash_map`、Rust 的 `HashMap`）通常比換演算法更有效。
- **資料處理與分析**：同樣的查詢在欄式格式（Parquet、Arrow）上比在列式格式上快，原因就是 17.6 節的 SoA；挑選資料格式時要看查詢讀幾個欄位。
- **影像、音訊、機器學習**：卷積、轉置、旋轉都是 tiling 的應用；選擇 NCHW 還是 NHWC 布局，要看推論引擎的最內層迴圈走哪一個維度。
- **高階語言也一樣**：Java 的 `int[]` 是連續的，`ArrayList<Integer>` 卻是一堆指向 heap 物件的指標；Python 的 list 存的也是指標，NumPy 的 array 才是連續的原始數值。這就是 NumPy 比純 Python 迴圈快得多的原因之一，也是為什麼對 NumPy 的 `a[:, j]`（一行，stride 很大）做運算，比對 `a[i, :]`（一列，連續）慢。
- **Code review 檢查清單**：最內層迴圈是不是 stride-1？二維陣列的索引順序和迴圈順序一致嗎？熱的 struct 是否混了很少用的大欄位？多個 thread 寫的計數器是否擠在同一條 line？緩衝區的寬度是否是 2 的冪？

## 17.10 常見錯誤與除錯

| 症狀 | 常見原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 二維陣列處理慢了一個數量級 | 迴圈順序和 row-major 不一致，內層 stride-n | 交換迴圈後計時；`perf stat` 看 L1 miss | 讓最內層迴圈走最後一個索引 |
| 影像寬度是 1024、2048、4096 時特別慢 | 2 的冪次 pitch 造成 conflict miss | 把寬度加一點（例如 +16）重測，時間明顯下降 | pitch 加 padding；tiling |
| blocking 之後沒變快，甚至變慢 | 原本就不是記憶體受限；或 tile 太大放不進 cache | 先量 IPC 與 miss；改變 tile 大小畫出曲線 | 只在 miss 是瓶頸時 blocking；tile 依 L1 容量計算 |
| 掃描某個欄位很慢，資料量看起來不大 | AoS 的 struct 很大，搬了大量用不到的欄位 | 算「實際搬的 bytes ÷ 用到的 bytes」 | 熱冷分離或改 SoA |
| 加 thread 之後總吞吐量反而下降 | false sharing：不同 thread 的資料在同一條 line | `perf c2c`（Linux）找出 HITM 熱點 | 每個 thread 的資料對齊到 line 邊界或分開配置 |
| benchmark 結果每次差很多 | 沒有暖身、CPU 頻率變化、被排到不同核心、資料量剛好在 cache 邊界 | 重複多次取最小值或中位數；固定 CPU（`taskset`） | 標準化量測流程，報告環境與編譯選項 |
| 最佳化版本「快了 100 倍」 | 編譯器把結果沒被使用的迴圈整個刪掉 | 看組合語言；印出計算結果 | 讓結果被使用（印出、寫入 `volatile`） |

最後一列值得特別提醒：本章所有的量測程式都印出了總和或檢查值，就是為了避免編譯器發現「結果沒人用」而把整個迴圈刪掉。寫 benchmark 時，第一個要懷疑的永遠是量測本身。

## 17.11 動手練習

1. **手算**：一個 `double a[1024][1024]` 陣列，cache line 64 bytes，L1 48 KiB。估算下面兩段的 L1 miss rate：(a) `for i for j sum += a[i][j]`；(b) `for j for i sum += a[i][j]`。再估算 (c)：`for i for j sum += a[i][j] + a[j][i]` 每次迭代平均幾次 miss。（答案：(a) 1/8；(b) 約 1；(c) 約 1.125。驗證方法：把 17.3 節的 Python 模擬器改成模擬這三種存取。）
2. **手算**：L1 是 32 KiB、8-way、64-byte line。一個 `float` 影像寬 2048 像素，沿著一行往下讀。相鄰兩次存取相差幾 bytes？會落在幾個不同的 set？如果寬度改成 2048 + 16 呢？（提示：先算 set 數與 set index 的週期。答案：8,192 bytes、全部在同一個 set；加 16 之後每列錯開 1 個 set，64 列就能分散到全部 64 個 set。）
3. 在你的電腦上執行 17.5 節的 memory mountain，畫出 stride 1 與 stride 8 兩條曲線，標出 L1、L2、L3（如果有）與 DRAM 的邊界，並和 `lscpu`（Linux）或 `sysctl hw`（macOS）回報的 cache 大小對照。
4. 修改 17.8 節的程式，加入 tile 16 與 tile 128，並測試 pitch 為 W+1、W+16、W+32、W+64 四種情況。哪一種 pitch 最好？為什麼 W+1 可能反而不理想？（提示：想一想每列的起點是否還對齊 line 邊界。）
5. 把 17.6 節的程式改成「熱冷分離」：`struct hot { uint64_t key; uint32_t hits; uint32_t flags; }` 留在主陣列，`width`、`height`、`path` 移到另一個陣列。量測掃描 `hits` 的時間，並和 AoS、SoA 比較。
6. 如果你有 Linux 機器，用 `perf stat -e L1-dcache-loads,L1-dcache-load-misses` 分別執行 17.3 節的 `ijk`、`kij`、`jki` 三種版本（可以加命令列參數只跑其中一種），把量到的 miss 數除以 n³，與 17.3 節手算的 1.125、0.25、2.0 比較。

## 本章重點整理

- 寫 cache-friendly 程式的兩條規則：把注意力放在最內層迴圈，並讓它的 miss 最少；重複使用 cache 裡的資料（temporal locality），以及用 stride-1 存取（spatial locality）。
- stride-k 存取時，每次存取的平均 miss 約為 min(1, k × 元素大小 ÷ line 大小)；這個簡單模型足以預測哪個版本比較快。
- 指令數完全相同的兩段迴圈，只因為存取的 stride 不同，效能可以差十倍以上；C 的二維陣列是 row-major，最內層迴圈應該走最後一個索引。
- 矩陣乘法的六種迴圈順序依最內層變數分成三類：BC 類（kij、ikj）每次迭代 0.25 次 miss 最快，AB 類（ijk、jik）1.125 次居中，AC 類（jki、kji）2.0 次最慢。
- 衡量效能要看 miss 次數，不是存取次數：BC 類每次迭代的存取比 AB 類多，卻最快。
- Blocking／tiling 把資料切成放得進 cache 的小塊，讓每個元素在被踢出前多用幾次；矩陣乘法分塊後 miss 約為 n³/(4b)，tile 大小 b 要滿足三個小塊同時放得進 cache。
- Blocking 只在程式受記憶體限制時有效；在大 cache、強預取器的機器上，或運算本身是瓶頸時，它可能沒有幫助甚至變慢，所以要先量測。
- Memory mountain 用 working set 大小與 stride 兩個維度描繪一台機器的記憶體系統：山脊對應各層 cache 的容量（temporal locality），斜坡對應 line 大小（spatial locality）。
- AoS 適合一次處理整筆紀錄，SoA 適合批次掃描少數欄位；依最熱的存取模式選布局，必要時熱冷分離。
- 指標追逐的結構（linked list、散落的物件圖）讓 CPU 無法預先讀取，應優先使用連續陣列或集中配置。
- 2 的冪次 stride 會讓資料集中在少數 cache set，造成 conflict miss；影像緩衝區的 pitch 加一點 padding 就能避開。
- 轉置與旋轉無法靠重排迴圈解決，tiling 加 padding 讓 `thumbd` 的旋轉快了約十倍。
- 多核心時，不同 thread 寫入同一條 line 的不同變數會造成 false sharing，第 32 章會詳細處理。
- 在 Linux 用 `perf stat` 量 IPC 與 cache miss、用 `perf record` 找出 miss 發生的位置；Cachegrind 適合精確比較兩個版本。

## 延伸問答

> [!question]- Q1. 兩段迴圈的指令數完全相同，為什麼一段可以快十倍以上？
> 指令數只描述 CPU 要「做」多少事，沒有描述它要「等」多久。每一條 load 指令的成本取決於資料在哪一層：L1 hit 大約 1 ns，到 DRAM 超過 100 ns。stride-1 的迴圈每 16 次（64-byte line、4-byte `int`）才 miss 一次，其餘都是 L1 hit；stride-n 的迴圈幾乎每次都 miss。
>
> 17.2 節的實驗中，`sum_rows` 與 `sum_cols` 的最內層都是五條指令，差別只在位址每次加 4 還是加 16,384，結果一個 4.7 ms、一個 61.5 ms。所以分析效能時，除了數指令，還要估算每次迭代的 miss 數，後者常常才是決定性的因素。

> [!question]- Q2. 手算題：矩陣乘法 `jki` 版本，元素是 `double`、line 是 32 bytes，每次內層迭代平均幾次 miss？換成 `kij` 呢？
> 32-byte line 可以裝 4 個 `double`。`jki` 的最內層走 `i`：`A[i][k]` 與 `C[i][j]` 都是同一行往下走，stride-n，每次都 miss，各貢獻 1；`B[k][j]` 在內層固定，放在暫存器，貢獻 0。合計 2 次。
>
> `kij` 的最內層走 `j`：`B[k][j]` 與 `C[i][j]` 都是 stride-1，每 4 次存取 miss 一次，各貢獻 0.25；`A[i][k]` 固定，貢獻 0。合計 0.5 次。這正是 CS:APP 原書使用的參數，line 變小時 stride-1 的優勢也跟著變小，但排名不變：AC 類永遠最差、BC 類永遠最好。

> [!question]- Q3. 為什麼 blocking 能減少 miss？tile 的大小該怎麼決定？
> 不分塊時，即使存取是 stride-1，大矩陣的每個元素被重複使用時，中間隔了太多其他存取，早就被踢出 cache，每次使用都要重新搬一次。Blocking 把計算重新排列，讓一小塊資料在放進 cache 之後，把所有和它有關的計算一次做完，等於把「重複使用的距離」縮短到 cache 裝得下的範圍。
>
> tile 大小的上限來自 working set：矩陣乘法每一步要同時用到 A、B、C 各一個 b×b 小塊，所以 3 × b² × 元素大小 ≤ cache 容量。48 KiB 的 L1 算出 b ≤ 45，實務上取 32；128 KiB 的 L1 算出 b ≤ 73，取 64。最後一定要實際量測幾個候選值，因為 associativity、其他資料與預取器都會影響結果。

> [!question]- Q4. 你把一段影像處理程式改成 tiling，結果沒有變快，甚至變慢了。可能的原因有哪些？
> 第一個可能是瓶頸根本不在記憶體。如果原本的程式已經是 stride-1，而且預取器跟得上，CPU 其實在忙著執行指令，這時 tiling 只是多了迴圈開銷、讓內層迴圈變短，17.4 節 `-O1` 的結果就是這種情況。先用 `perf stat` 看 IPC 與 miss 數，確認是記憶體受限再動手。
>
> 第二個可能是 tile 選錯：太大放不進 cache，或剛好遇到 conflict miss。17.8 節 pitch 4096 時，tile 32 和不分塊幾乎一樣慢，因為一個 tile 的 32 條 line 全都擠在同一個 set。這時要同時處理資料布局（加 padding），tiling 才會生效。第三個可能是量測本身有問題，例如沒有暖身、資料量太小全部在 cache 裡，或編譯器把迴圈刪掉了。

> [!question]- Q5. 什麼時候該用 SoA 而不是 AoS？在高階語言裡也有這個問題嗎？
> 判斷依據是最熱的存取模式。如果最常做的是「拿出一筆紀錄，用它大部分的欄位」，AoS 讓這些欄位在同一兩條 line 裡，一次就搬齊；如果最常做的是「對所有紀錄的某一兩個欄位做批次運算」，SoA 讓這些欄位連續排列，每條 line 都塞滿有用的資料，也方便 SIMD。17.6 節只掃 `hits` 欄位時，SoA 比 AoS 快了 2.8 倍。
>
> 高階語言同樣有這個問題，而且更嚴重。Java 的物件陣列、Python 的 list 存的是指向 heap 物件的指標，連 AoS 都談不上，而是指標追逐。這就是 pandas 與 NumPy 用欄式的連續陣列儲存資料、Apache Arrow 與 Parquet 採用欄式格式的原因：分析工作通常只讀少數欄位，欄式布局能讓 cache 與 SIMD 發揮作用。

> [!question]- Q6. 為什麼影像寬度是 4096 時，轉置比寬度 4000 慢？
> cache 用位址中的 set index 位元決定一條 line 放在哪個 set。以 32 KiB、8-way、64-byte line 的 L1 為例，set index 是位址的第 6 到 11 位元，位址相差 4,096 的整數倍時會落在同一個 set。寬 4096 的 RGBA 影像一列是 16,384 bytes，正好是 4,096 的 4 倍，所以同一行往下的每個像素都落在同一個 set，而那個 set 只有 8 個 way，第 9 條 line 就開始互相踢出，這是 conflict miss。
>
> 寬 4000 時一列是 16,000 bytes，除以 4,096 的餘數是 3,712，相鄰列的 set index 每次位移 58 個 set，一整行會輪流用到 32 個 set（58 與 64 的最大公因數是 2），可用的 line 從 8 條變成 256 條，cache 的容量才真正被用上。所以修法不是減少像素，而是讓 pitch 不要是 4 KiB 的倍數，例如每列多留一條 line 的空間。

> [!question]- Q7. 你在 production 看到一個服務在 32 核心的機器上，從 8 個 thread 加到 16 個 thread 後吞吐量下降。cache 層面可能發生了什麼？怎麼確認？
> 一個常見原因是 false sharing：多個 thread 頻繁寫入不同的變數，但這些變數在同一條 cache line 裡，例如一個緊密排列的「每個 thread 一格」的計數器陣列。每次寫入，cache coherence 協定都要讓其他核心的那條 line 失效，line 在核心之間來回傳遞，thread 越多越嚴重。另一個可能是所有 thread 的 working set 加起來超過共用的 L3，或記憶體頻寬已經飽和。
>
> 在 Linux 上可以用 `perf c2c record` 與 `perf c2c report` 找出被多個核心爭搶的 line（報告中的 HITM 事件），並對應到原始碼中的變數。確認是 false sharing 後，把每個 thread 的資料對齊到 line 邊界或分開配置；如果是頻寬飽和，就要減少每個 thread 搬運的資料量，例如用更緊湊的資料布局或 blocking。第 32 章會實際量測這個問題。

> [!question]- Q8. 面試題：給你一個很大的 `int` 二維陣列，請寫出最快的「全部加總」程式，並說明你會怎麼驗證它真的快。
> 第一步是讓存取順序符合 row-major：外層走列、內層走行，最內層 stride-1，讓每條搬上來的 line 全部被用到。如果陣列其實是連續配置的，甚至可以把它當成一維陣列從頭掃到尾，連外層迴圈的邊界檢查都省掉。接著可以用多個累加器打破加法的相依鏈（第 14 章），讓編譯器向量化；資料量非常大時，可以用多個 thread 各自處理不同的列區段，最後再合併，但要注意每個 thread 的部分和不要放在同一條 line 上。
>
> 驗證時要說明量測方法：用固定且足夠大的資料（遠大於 LLC），暖身後重複量測取最小值或中位數，印出總和避免迴圈被刪除，並和行優先版本對照。在 Linux 上用 `perf stat` 看 L1 miss 數是否接近「元素數 ÷ 每條 line 的元素數」，以及吞吐量是否接近 memory mountain 上 stride-1 的高度。能講出「預期值是多少、怎麼證明達到了」，比只寫出程式更能說服面試官。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 6 章 6.5–6.6 節的 memory mountain 與矩陣乘法分析，可以和本章的量測結果對照。
- [CS:APP 3e 學生資源](https://csapp.cs.cmu.edu/3e/students.html)：包含原書範例程式碼，其中有 memory mountain 的原始實作。
- [CS:APP 3e Labs](https://csapp.cs.cmu.edu/3e/labs.html)：Cache Lab 的第二部分要求寫出 miss 最少的矩陣轉置，正是本章 tiling 與 conflict miss 的練習；Performance Lab 則要求最佳化一個 kernel 函式（官網舉的例子是 convolution 或矩陣轉置），同樣會碰到本章的 cache 議題。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：Cache Memories 與 Cache-friendly code 相關講次的投影片。
- [Linux man pages](https://man7.org/linux/man-pages/)：`perf_event_open(2)` 說明 Linux 效能計數器的介面。
- [Intel 64 and IA-32 Architectures Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)：cache 組態與效能監控事件的官方說明。
