---
title: 公式與數字速查
---

# 附錄 A　公式與數字速查

這份附錄把全書散落在各章的公式、常數與數量級集中在一起，方便手算、面試前複習，或在 production 看到一個奇怪的數字時快速對照。每一項都附一個算例與出處章節；算例的數字直接取自該章，想看推導過程或完整的故事背景，就回到那一章。

除非另外註明，本附錄的數字都以 **x86-64 Linux（LP64、4 KiB page、64-byte cache line）** 為準；macOS on Apple Silicon 不同的地方會特別標出。延遲一律只給數量級，實際值依硬體世代而定。

## A.1 進位轉換

### 十六進位與二進位

一個 hex 數字剛好是 4 個 bit，所以 hex 與二進位互轉只要「每 4 位一組」查表。出處：第 3 章。

| hex | 二進位 | 十進位 | hex | 二進位 | 十進位 |
|---|---|---|---|---|---|
| 0 | 0000 | 0 | 8 | 1000 | 8 |
| 1 | 0001 | 1 | 9 | 1001 | 9 |
| 2 | 0010 | 2 | A | 1010 | 10 |
| 3 | 0011 | 3 | B | 1011 | 11 |
| 4 | 0100 | 4 | C | 1100 | 12 |
| 5 | 0101 | 5 | D | 1101 | 13 |
| 6 | 0110 | 6 | E | 1110 | 14 |
| 7 | 0111 | 7 | F | 1111 | 15 |

```text
 hex → 十進位：按 16 的冪展開
   0xFFD8 = 15 × 16^3 + 15 × 16^2 + 13 × 16 + 8 = 65496

 十進位 → hex：連續除以 16，餘數由下往上讀
   50000 ÷ 16 = 3125 餘 0
    3125 ÷ 16 =  195 餘 5
     195 ÷ 16 =   12 餘 3
      12 ÷ 16 =    0 餘 12（C）   → 0xC350
```

上圖兩個算例都出自第 3 章：`0xFFD8` 是 JPEG 檔頭的 marker，`50000` 用來示範「除 16 取餘數」的方向。讀的時候最常犯的錯是把餘數由上往下讀，記得最後一個餘數是最高位。

### 2 的冪

2^n 寫成 n = i + 4j（0 ≤ i ≤ 3），hex 就是「開頭一個 2^i，後面接 j 個 0」。例如 2^14：14 = 2 + 4 × 3，所以是 `0x4000`。出處：第 3 章。

| 2^n | hex | 十進位 | 常見用途（章節） |
|---|---|---|---|
| 2^8 | `0x100` | 256 | 一個 byte 的值域（第 3 章） |
| 2^10 | `0x400` | 1,024 | 1 KiB |
| 2^12 | `0x1000` | 4,096 | Linux x86-64 的 page 大小（第 23 章） |
| 2^14 | `0x4000` | 16,384 | Apple Silicon 的 page 大小（第 3、23 章） |
| 2^16 | `0x10000` | 65,536 | TCP port 的個數（第 3 章） |
| 2^20 | `0x100000` | 1,048,576 | 1 MiB |
| 2^21 | `0x200000` | 2,097,152 | 2 MiB huge page（第 23 章） |
| 2^24 | `0x1000000` | 16,777,216 | `float` 能精確表示的整數上限（第 6 章） |
| 2^30 | `0x40000000` | 1,073,741,824 | 1 GiB |
| 2^32 | `0x100000000` | 4,294,967,296 | 32 位元 unsigned 的模數（第 4、5 章） |
| 2^48 | — | 約 2.8 × 10^14 | 48-bit 虛擬位址空間 = 256 TiB（第 23 章） |
| 2^53 | — | 9,007,199,254,740,992 | `double` 能精確表示的整數上限（第 6 章） |

> [!tip] 位元組單位
> 本書的 KiB、MiB、GiB 是 2 的冪（1 KiB = 1,024 bytes）；KB、MB、GB 是 10 的冪，多用在磁碟容量與網路頻寬。看到 `ulimit -s` 的 8192（單位 KiB）就是 8 MiB。

## A.2 資料型別的大小（LP64）

64 位元的 Linux 與 macOS 都採用 **LP64**：`long` 與指標是 8 bytes；64 位元 Windows 是 LLP64，`long` 仍是 4 bytes。基本型別的對齊（alignment）等於它的大小。出處：第 2、3、10 章。

| 型別 | ILP32 | LP64（Linux、macOS） | LLP64（Windows） | 對齊（x86-64） |
|---|---|---|---|---|
| `char` | 1 | 1 | 1 | 1 |
| `short` | 2 | 2 | 2 | 2 |
| `int` | 4 | 4 | 4 | 4 |
| `long` | 4 | **8** | **4** | 8 |
| `long long` | 8 | 8 | 8 | 8 |
| 指標、`size_t`、`ptrdiff_t` | 4 | 8 | 8 | 8 |
| `float`／`double` | 4／8 | 4／8 | 4／8 | 4／8 |
| `long double`（x87 80-bit） | — | 16（x86-64） | — | 16 |

另外兩個常被忽略的平台差異：沒寫 `signed`／`unsigned` 的 `char` 在 x86-64 Linux 與 macOS 是 signed，在 AArch64 Linux 是 unsigned（第 4 章）；cache line 在 x86-64 是 64 bytes，在 Apple Silicon 是 128 bytes（第 15、16 章）。

**算例：struct 的 padding**（第 10 章）。欄位依序是 `char format; double scale; char rotate; int width; short quality;`：

| 欄位 | 大小／對齊 | 插入 padding | offset |
|---|---|---|---|
| `format` | 1／1 | 0 | 0 |
| `scale` | 8／8 | 7 | 8 |
| `rotate` | 1／1 | 0 | 16 |
| `width` | 4／4 | 3 | 20 |
| `quality` | 2／2 | 0 | 24 |
| 尾端 | struct 對齊 8 | 6 | 總大小 **32** |

規則只有兩條：每個欄位放在自己對齊值的倍數上；整個 struct 的大小補到「最大欄位對齊值」的倍數。欄位依對齊由大到小重排，這個 struct 可以縮成 24 bytes。

## A.3 整數範圍

w 位元的整數範圍由三個公式決定。出處：第 4 章（範圍）、第 5 章（TMin 沒有相反數）。

```text
 UMax_w = 2^w − 1                 位元全為 1
 TMin_w = −2^(w−1)                只有最高位是 1：1000…0
 TMax_w = 2^(w−1) − 1             最高位是 0，其餘全為 1：0111…1

 |TMin| = TMax + 1   → −TMin 在 w 位元裡仍然是 TMin
 UMax   = 2 × TMax + 1
```

| w | C 型別（LP64） | TMin | TMax | UMax | TMin 的 hex | −1 的 hex |
|---|---|---|---|---|---|---|
| 8 | `int8_t`、`signed char` | −128 | 127 | 255 | `0x80` | `0xFF` |
| 16 | `int16_t`、`short` | −32,768 | 32,767 | 65,535 | `0x8000` | `0xFFFF` |
| 32 | `int32_t`、`int` | −2,147,483,648 | 2,147,483,647 | 4,294,967,295 | `0x80000000` | `0xFFFFFFFF` |
| 64 | `int64_t`、`long` | −9,223,372,036,854,775,808 | 9,223,372,036,854,775,807 | 18,446,744,073,709,551,615 | `0x8000000000000000` | `0xFFFFFFFFFFFFFFFF` |

對應的 C 巨集在 `<limits.h>` 與 `<stdint.h>`：`INT_MIN`、`INT_MAX`、`UINT_MAX`、`INT64_MIN`、`SIZE_MAX` 等。

**算例：一看就該懷疑的數字**（第 4 章）。log 裡出現 4,294,967,295 或 18,446,744,073,709,551,615，幾乎一定是 −1 被當成 32 位元或 64 位元的 unsigned（例如 `read` 回傳 −1 後存進 `size_t`）；出現 65,535 或 255，是 16 或 8 位元的 −1。

## A.4 二補數與轉換規則

### 編碼與取負

```text
 B2U(x) =  Σ x_i × 2^i                       （i = 0 … w−1）
 B2T(x) = −x_(w−1) × 2^(w−1) + Σ x_i × 2^i   （i = 0 … w−2，最高位權重是負的）
 −x     = ~x + 1                              （在 w 位元內）
```

**算例**（第 4 章）：4 位元 `1011` 的 B2T = −8 + 0 + 2 + 1 = −5。16 位元的 −12345：12345 = `0x3039`，取反得 `0xCFC6`，加 1 得 **`0xCFC7`**。

### Signed 與 unsigned 互轉：位元不變，解讀改變

```text
 T2U_w(x) = x + 2^w     若 x < 0，否則不變
 U2T_w(u) = u − 2^w     若 u > TMax_w，否則不變
```

| 原值與型別 | 位元 | 轉成 | 結果 | 算法 |
|---|---|---|---|---|
| `int16_t` −12345 | `0xCFC7` | `uint16_t` | 53,191 | −12345 + 65536 |
| `int32_t` −1 | `0xFFFFFFFF` | `uint32_t` | 4,294,967,295 | −1 + 2^32 |
| `int32_t` TMin | `0x80000000` | `uint32_t` | 2,147,483,648 | TMax + 1 |
| `uint32_t` 3,000,000,000 | `0xB2D05E00` | `int32_t` | −1,294,967,296 | 3,000,000,000 − 2^32 |
| `uint8_t` 200 | `0xC8` | `int8_t` | −56 | 200 − 256 |

出處：第 4 章。

### C 的隱式轉換

運算前先做 **integer promotion**（比 `int` 窄的型別先變成 `int`），再做 **usual arithmetic conversions**：同寬度時 unsigned 贏；寬度不同時，若較寬的 signed 型別能裝下另一方的所有值，就轉成它。出處：第 4 章。

| 運算式 | 實際比較 | 結果 |
|---|---|---|
| `-1 < 0u` | `4294967295u < 0u` | **0** |
| `(unsigned char)200 > (signed char)-1` | 都提升成 `int`：`200 > -1` | 1 |
| `1u > -1L` | LP64 的 `long` 裝得下 `unsigned int`：`1L > -1L` | 1 |
| `n < sizeof hdr`（`n` 是 `ssize_t` 的 −1） | `18446744073709551615 < 24` | **0** |

### 擴展與截斷

- **Zero extension**：unsigned 變寬時高位補 0。
- **Sign extension**：二補數變寬時高位補原本的最高位。4 位元 `1011`（−5）擴成 8 位元是 `1111 1011`，仍是 −5。x86-64 的指令是 `movsbl`、`movslq`（sign）與 `movzbl`（zero）；寫入 32 位元暫存器會自動把高 32 位清 0。
- **截斷**到 k 位元：保留低 k 位，等於先取 mod 2^k 再重新解讀。70,000 轉 `uint16_t`：70,000 − 65,536 = **4,464**；`int32_t` 53,191 轉 `int16_t` 得 −12,345。

出處：第 4 章（規則）、第 7 章（指令）。

### 加法、乘法與除法

| 運算 | 規則 | 溢位怎麼判斷 | 算例（出處） |
|---|---|---|---|
| unsigned 加法 | 結果 mod 2^w，定義良好 | `x + y < x` 就是溢位；事前檢查 `y > UINT_MAX - x` | 4 位元 13 + 5 = 18 mod 16 = 2（第 5 章） |
| signed 加法 | 位元和 unsigned 相同；C 中溢位是 **UB** | 只有同號相加會溢位：正 + 正 得負、負 + 負 得非負；要在運算前檢查，或用 `__builtin_add_overflow` | 4 位元 5 + 6 = `1011` = −5（第 5 章） |
| 乘法 | 截斷後 signed 與 unsigned 的位元相同 | `a != 0 && b > MAX / a`（unsigned）；或 `__builtin_mul_overflow` | 4 位元 13 × 5 與 −3 × 5 的低 4 位都是 `0001`（第 5 章） |
| 取負 | −x = ~x + 1 | −TMin = TMin；`abs(INT_MIN)` 是 UB | 4 位元 −(`1000`) = `1000`（第 5 章） |
| unsigned ÷ 2^k | `x >> k`（邏輯右移） | — | — |
| signed ÷ 2^k | C 向零捨入；負數要先加 bias：`(x + (1 << k) − 1) >> k` | `INT_MIN / -1` 與除以 0 在 x86-64 送 `SIGFPE` | −7 / 4：`−7 >> 2` = −2，`(−7 + 3) >> 2` = **−1**（第 5 章） |

C 中 signed overflow 是 undefined behavior，unsigned overflow 定義為模 2^w；需要繞回語意時用 unsigned 型別或 `-fwrapv`（第 5 章）。

### Condition codes

x86-64 的 `add`、`sub`、`cmp`、`test` 會設定四個旗標。出處：第 8 章。

| 旗標 | 何時為 1 | 對誰有意義 | 算例（8 位元） |
|---|---|---|---|
| CF | 最高位進位或借位 | unsigned 溢位 | `0xFF + 0x01` = `0x00`：CF = 1 |
| ZF | 結果為 0 | 兩者 | 同上：ZF = 1 |
| SF | 結果最高位為 1 | signed 結果為負 | `0x7F + 0x01` = `0x80`：SF = 1 |
| OF | signed 溢位 | signed | 同上：127 + 1 溢位成 −128，OF = 1 |

`cmp S, D` 之後，signed 比較看 SF ^ OF（`jl`、`jg`），unsigned 比較看 CF（`jb`、`ja`）。組合語言裡出現 `jb`／`ja` 就表示編譯器把比較當成 unsigned。

## A.5 IEEE 754 浮點數

### 格式

```text
 V = (−1)^s × M × 2^E

 float（32 bits）   │s│ exp (8)  │ frac (23)               │   bias = 127
 double（64 bits）  │s│ exp (11) │ frac (52)               │   bias = 1023
 一般化：k 個 exp 位元時 bias = 2^(k−1) − 1
```

| 格式 | sign | exp | frac | bias | 有效位數 | 約略十進位精度 |
|---|---|---|---|---|---|---|
| `float`（binary32） | 1 | 8 | 23 | 127 | 24 bits | 約 7 位 |
| `double`（binary64） | 1 | 11 | 52 | 1023 | 53 bits | 約 15–16 位 |
| half（FP16） | 1 | 5 | 10 | 15 | 11 bits | 約 3 位 |
| bfloat16 | 1 | 8 | 7 | 127 | 8 bits | 約 2–3 位 |

出處：第 6 章。

### 三種編碼情況

| exp 欄位 | frac | 類別 | 數值 |
|---|---|---|---|
| 全 0 | 0 | ±0 | +0 與 −0 用 `==` 比較相等，但 `1.0 / -0.0` = −∞ |
| 全 0 | ≠ 0 | denormalized | ±0.frac × 2^(1 − bias)，沒有隱藏的 1 |
| 不是全 0 也不是全 1 | 任意 | normalized | ±1.frac × 2^(exp − bias) |
| 全 1 | 0 | ±∞ | 溢位、`1.0 / 0.0` |
| 全 1 | ≠ 0 | NaN | `0.0 / 0.0`、`sqrt(-1.0)`、∞ − ∞；`NaN == NaN` 為 false |

出處：第 6 章。

### 常用的位元型樣（float）

| 值 | 位元（hex） | 說明 |
|---|---|---|
| +0.0／−0.0 | `0x00000000`／`0x80000000` | 只差 sign |
| 1.0 | `0x3F800000` | exp = 127，E = 0（第 1、6 章） |
| 0.1f | `0x3DCCCCCD` | 實際值約 0.100000001490116，比 0.1 略大（第 6 章） |
| 最小正 denormalized | `0x00000001` | 2^−149 ≈ 1.4 × 10^−45 |
| 最小正 normalized | `0x00800000` | 2^−126 ≈ 1.18 × 10^−38（第 6 章） |
| 最大有限值 | `0x7F7FFFFF` | 約 3.4 × 10^38 |
| +∞／−∞ | `0x7F800000`／`0xFF800000` | exp 全 1、frac = 0 |
| NaN（之一） | 例如 `0x7FC00000` | exp 全 1、frac ≠ 0 的都是 NaN |

`double` 對應的幾個值：1.0 是 `0x3FF0000000000000`；最小正 normalized 2^−1022 ≈ 2.2 × 10^−308；最大有限值約 1.8 × 10^308。整數能精確表示的範圍：`float` 是 ±2^24（16,777,217 會被捨入成 16,777,216），`double` 是 ±2^53（第 6 章）。

### 手算編碼與解碼

```text
 5.75 → float
   5.75 = 101.11₂ = 1.0111₂ × 2^2      s = 0，E = 2
   exp  = 2 + 127 = 129 = 1000 0001₂
   frac = 0111 0000 … 0（23 位）
   位元 = 0 | 1000 0001 | 0111 000…0 = 0x40B80000

 0xC1480000 → 值
   s = 1，exp = 1000 0010₂ = 130 → E = 3
   M = 1.1001₂ = 1.5625
   V = −1.5625 × 2^3 = −12.5
```

兩個算例都出自第 6 章。編碼的步驟固定是：轉成二進位 → 正規化成 1.xxx × 2^E → exp 欄位存 E + bias → frac 存小數點後的位元（去掉開頭的 1）。

### 捨入與轉換

| 規則 | 內容 | 算例（第 6 章） |
|---|---|---|
| 預設捨入 | round-to-nearest-even：剛好在中間時取最低位為偶數者 | 1.5 → 2、2.5 → 2；二進位 1.0110₂ 保留兩位小數得 1.10₂ |
| 結合律 | 浮點加法**不**滿足 | (1e16 + −1e16) + 1 = 1；1e16 + (−1e16 + 1) = 0 |
| `int` → `float` | 可能失去精度 | 16,777,217 → 16,777,216 |
| `int` → `double` | 精確 | 53 位元有效數字裝得下 32 位元整數 |
| `float`／`double` → `int` | 向零捨入；超出範圍或 NaN 是 UB | 3.99 → 3、−3.99 → −3 |
| `double` → `float` | 可能溢位成 ±∞ 或失去精度 | `(double)0.1f` = 0.10000000149011612 |

## A.6 位址切分

### Cache：tag／set index／block offset

```text
 m-bit 位址
 ┌──────────────────┬────────────────┬──────────────┐
 │ tag (t bits)     │ set index (s)  │ offset (b)   │
 └──────────────────┴────────────────┴──────────────┘
 b = log2(B)      s = log2(S)      t = m − s − b
 容量 C = S × E × B
```

| 符號 | 意義 | 典型 L1d（第 16 章） |
|---|---|---|
| m | 位址位元數 | 48 |
| B | block 大小（bytes） | 64 → b = 6 |
| E | 每個 set 的 line 數（associativity） | 8 |
| S | set 數 = C ÷ (E × B) | 32 KiB ÷ (8 × 64) = 64 → s = 6 |
| t | tag 位元數 | 48 − 6 − 6 = 36 |

| 組織 | S | E | 一個 block 能放的位置 |
|---|---|---|---|
| direct-mapped | C ÷ B | 1 | 1 個 |
| E-way set associative | C ÷ (E × B) | E | E 個 |
| fully associative | 1 | C ÷ B | 任何位置 |

**算例**（第 16 章）：用上表的 L1 切分 `0x12345678`。

```text
 offset    = addr & 0x3F         = 0x38 = 56
 set index = (addr >> 6) & 0x3F  = 25
 tag       = addr >> 12          = 0x12345
```

相差 4,096（= S × B）的位址，例如 `0x12346678`，set index 同樣是 25、tag 不同，會搶同一個 set；這正是寬度 4096 的影像直向走訪時 conflict miss 的來源（第 16、17 章）。

**迷你算例**（第 16 章）：m = 8、B = 8、S = 4、E = 1，所以 b = 3、s = 2、t = 3。位址 `0x24` = `001｜00｜100`：tag 1、set 0、offset 4。

> [!note] VIPT 的限制
> L1 常用 virtually indexed, physically tagged 設計，要求 s + b ≤ page offset 位元數（第 16 章）。32 KiB、8-way、64-byte line：s + b = 6 + 6 = 12，剛好等於 4 KiB page 的 12 bits。所以 x86-64 的 L1 從 32 KiB、8-way 加大到 48 KiB 時，associativity 也跟著變成 12-way：C ÷ E 必須維持 4 KiB。

### 虛擬記憶體：VPN／VPO

```text
 p = log2(page 大小)
 VPN = VA >> p                 VPO = VA & (page 大小 − 1)
 PTE 位址 = page table 起點 + VPN × PTE 大小
 PA  = (PPN << p) | VPO        （翻譯只換頁號，offset 不變）
 TLB：TLBI = log2(TLB 的 set 數) 個 VPN 低位，TLBT = 其餘 VPN 位元
```

| page 大小 | offset 位元 | 48-bit 位址的 VPN 位元 | 常見系統 |
|---|---|---|---|
| 4 KiB | 12 | 36 | Linux x86-64、大部分 ARM Linux |
| 16 KiB | 14 | 34 | macOS on Apple Silicon |
| 2 MiB（huge page） | 21 | 27 | Linux huge page |
| 1 GiB（huge page） | 30 | 18 | 特殊用途 |

出處：第 23 章。

**算例一**（第 23 章）：`0x7f3a12345abc`、4 KiB page → VPO = `0xabc`、VPN = `0x7f3a12345`。無論翻譯到哪個實體頁，實體位址的結尾一定是 `abc`。

**算例二：迷你系統的完整轉譯**（第 23 章）。虛擬位址 16 bits、實體位址 14 bits、page 256 bytes、TLB 8 entries 2-way：

| 項目 | 推導 | 結果 |
|---|---|---|
| VPO | log2(256) | 8 bits |
| VPN | 16 − 8 | 8 bits |
| PPN | 14 − 8 | 6 bits |
| TLBI | 8 ÷ 2 = 4 sets → log2(4) | 2 bits |
| TLBT | 8 − 2 | 6 bits |
| 翻譯 `0x1234` | VPN `0x12`、VPO `0x34`；TLBI = 2、TLBT = `0x04`；查表得 PPN `0x2A` | PA = `0x2A34` |

### 多層 page table（x86-64 四層）

```text
 48-bit 虛擬位址
 ┌────────┬────────┬────────┬────────┬───────────┐
 │VPN1 (9)│VPN2 (9)│VPN3 (9)│VPN4 (9)│ VPO (12)  │
 └────────┴────────┴────────┴────────┴───────────┘
  bit 47–39  38–30    29–21    20–12     11–0

 每張表 = 512 entries × 8 bytes = 4 KiB = 一個 page
 一個 entry 涵蓋：L1 → 512 GiB、L2 → 1 GiB、L3 → 2 MiB、L4 → 4 KiB
```

本書沿用 CS:APP 的命名：L1 是 `CR3` 指向的最上層，L4 是指向實體頁的最下層。每一層的索引寬度 = log2(page 大小 ÷ PTE 大小) = log2(4096 ÷ 8) = 9；四層共 36 bits，剛好是 VPN 的寬度。57-bit 位址的系統用五層（第 23 章）。L3、L2 一個 entry 涵蓋的 2 MiB 與 1 GiB，正好是兩種 huge page 的大小。

**算例**：把算例一的 `0x7f3a12345abc` 切成四段索引。

```text
 VPN1 = (VA >> 39) & 0x1FF = 254
 VPN2 = (VA >> 30) & 0x1FF = 232
 VPN3 = (VA >> 21) & 0x1FF = 145
 VPN4 = (VA >> 12) & 0x1FF = 325
 VPO  =  VA        & 0xFFF = 0xabc
```

MMU 依序讀 L1 表的第 254 項、L2 表的第 232 項、L3 表的第 145 項、L4 表的第 325 項，得到 PPN，再接上 `0xabc`。TLB miss 時要做的就是這四次記憶體讀取（第 23 章）。

### 對齊 page 邊界

`mmap` 的 offset 必須是 page 大小的整數倍（否則 `EINVAL`），常用 `off & ~(page − 1)` 往下對齊（第 24 章）。例如 page 4096、想從檔案第 4000 byte 開始：對齊後的 offset 是 0，資料從 `p + 4000` 開始。

## A.7 Cache 與 AMAT

### 基本指標

| 指標 | 定義 | 典型量級（第 16 章） |
|---|---|---|
| miss rate | miss 次數 ÷ 存取次數 | L1 通常只有幾 % |
| hit time | 從這層取得資料的時間 | L1 約 4 cycles |
| miss penalty | miss 時額外多花的時間 | 到 L2 約 10 cycles；到 DRAM 數百 cycles |

三種 miss（第 15、16 章）：**cold**（第一次存取）、**conflict**（還有空間，但放置規則讓 block 搶同一個 set）、**capacity**（working set 比 cache 大）。

### AMAT

```text
 AMAT = hit time + miss rate × miss penalty

 多層展開：
 AMAT = L1 hit + L1 miss rate × (L2 hit + L2 local miss rate × DRAM 時間)
```

**算例一**（第 15 章）：L1 hit 1 ns、miss 到 DRAM 100 ns。miss rate 3% 時 AMAT = 1 + 0.03 × 100 = 4 ns；降到 1% 時 AMAT = 2 ns。miss rate 只差兩個百分點，平均存取時間差一倍。

**算例二**（第 16 章）：L1 hit 4 cycles、L1 miss rate 5%；L2 hit 12 cycles、L2 local miss rate 20%；DRAM 200 cycles。

```text
 有 L2：  4 + 0.05 × (12 + 0.20 × 200) = 4 + 0.05 × 52 = 6.6 cycles
 沒有 L2：4 + 0.05 × 200 = 14 cycles
```

L2 的 local miss rate 20% 看起來很差，卻把平均存取時間從 14 cycles 降到 6.6 cycles，所以判斷下層 cache 要看 AMAT，不要只看它自己的 miss rate。

### Stride 與迴圈的 miss 估算

```text
 每次存取的平均 miss ≈ min(1, stride × 元素大小 ÷ B)
```

| stride（`int`，B = 64） | 每次跳幾 bytes | miss rate |
|---|---|---|
| 1 | 4 | 1/16 = 6.25% |
| 4 | 16 | 25% |
| 16 以上 | 64 以上 | 100% |

出處：第 17 章。同一章的矩陣乘法（`double`，一條 line 8 個元素，n 很大）每次內層迭代的 miss 數：

| 類別 | 迴圈順序 | 每次迭代的 miss |
|---|---|---|
| AB | ijk、jik | 1.125 |
| BC | kij、ikj | **0.25** |
| AC | jki、kji | 2.0 |

### Blocking 的 tile 大小

```text
 三個 b × b 小塊要同時放進 cache：3 × b² × 元素大小 ≤ C
 分塊後總 miss ≈ n³ ÷ (4b)；不分塊的 BC 類 ≈ n³ ÷ 4
```

**算例**（第 17 章）：`double`、L1d 128 KiB → 3 × b² × 8 ≤ 131,072 → b ≤ 73，取 64；L1d 48 KiB → b ≤ 45，取 32。最後仍要實測幾個候選值。

## A.8 Page table 大小計算

```text
 單層 page table 大小 = 2^(n − p) × PTE 大小
 每張多層表的 entry 數 = page 大小 ÷ PTE 大小
 層數 = ⌈(n − p) ÷ log2(每張表的 entry 數)⌉
 多層表的總大小 ≈ 實際用到的區域需要的表數 × page 大小
```

| 項目 | 算法 | 結果 |
|---|---|---|
| 48-bit、4 KiB、8-byte PTE 的單層表 | 2^36 × 8 | 2^39 bytes = **512 GiB**（每個 process） |
| 每張表的 entry 數 | 4096 ÷ 8 | 512 = 2^9 |
| 層數 | 36 ÷ 9 | 4 層（57-bit 位址是 5 層） |
| `thumbd` 用了約 2 GiB 連續區域 | 2 GiB ÷ 4 KiB = 524,288 個 L4 PTE ÷ 512 | 1,024 張 L4 表 |
| 加上少量 L3、L2 與 1 張 L1 | 約 1,030 多張 × 4 KiB | 約 **4 MiB** |

出處：第 23 章。

## A.9 效能公式

### CPE

```text
 T(n) = a + b × n          b 就是 CPE（cycles per element），a 是固定開銷
 CPE ≈ (ns ÷ 元素) × 時脈（GHz）
```

**算例**（第 14 章）：n = 100 時 560 cycles、n = 1,000 時 3,260 cycles → b = (3260 − 560) ÷ 900 = **3.0**，a = 560 − 300 = 260 cycles。

### Latency bound 與 throughput bound

```text
 latency bound    = 運算的 latency（每一步都依賴上一步時）
 throughput bound = issue time ÷ capacity（還要受 load 單元數限制）
```

| 運算（Haswell，第 14 章） | latency | issue | capacity | latency bound | throughput bound |
|---|---|---|---|---|---|
| 整數加法 | 1 | 1 | 4 | 1.00 | 0.50（受 2 個 load 單元限制） |
| 整數乘法 | 3 | 1 | 1 | 3.00 | 1.00 |
| 浮點加法 | 3 | 1 | 1 | 3.00 | 1.00 |
| 浮點乘法 | 5 | 1 | 2 | 5.00 | 0.50 |

`acc = acc + d[i]`（`double`）這種單一累加器的迴圈，CPE 不可能低於浮點加法的 latency 3.0；用多個累加器打斷依賴鏈，才能往 throughput bound 靠近。

### CPI（pipeline）

```text
 CPI = 1.0 + lp + mp + rp
   lp = load 比例 × 緊接使用的比例 × load-use 懲罰
   mp = 條件跳躍比例 × 預測錯誤率 × 預測錯誤懲罰
   rp = ret 比例 × ret 懲罰
```

**算例**（第 13 章，PIPE）：lp = 0.30 × 0.15 × 1 = 0.045；mp = 0.18 × 0.10 × 2 = 0.036；rp = 0.02 × 3 = 0.060 → **CPI = 1.141**。把預測錯誤懲罰換成現代處理器的 15 cycles：錯 10% 時 CPI = 1.375，錯 45%（手繪貼紙）時 CPI = 2.320。

### Amdahl's law

```text
 S = 1 ÷ [(1 − α) + α ÷ k]       α：被加速部分的比例；k：加速倍數
 S_max（k → ∞）= 1 ÷ (1 − α)
```

| 情境 | α | k | S | S_max | 出處 |
|---|---|---|---|---|---|
| 縮放用 SIMD 加速 | 0.30 | 4 | 1.29 | 1.43 | 第 1 章 |
| 解碼加速 | 0.50 | 2 | 1.33 | 2.00 | 第 1 章 |
| 縮圖迴圈最佳化 | 0.35 | 78.9 | 1.53 | 1.54 | 第 14 章 |

每完成一次最佳化都要重新 profile：第 14 章縮圖最佳化之後總時間變成原本的 0.654，解碼原本佔 0.40，現在佔 0.40 ÷ 0.654 ≈ 61%。

### 平行化：Amdahl、Gustafson、speedup 與 efficiency

```text
 S(n)        = 1 ÷ [s + (1 − s) ÷ n]     s：只能循序執行的比例（單核心量）
 S(∞)        = 1 ÷ s
 S_scaled(n) = s + (1 − s) × n            Gustafson：s 在 n 核心時量
 speedup S_p = T_1 ÷ T_p      efficiency E_p = S_p ÷ p
```

**算例**（第 32 章）：s = 0.05 → S(8) ≈ 5.93、S(16) ≈ 9.14、S(∞) = 20；Gustafson 的 S_scaled(16) = 15.25。實測 T_1 = 48.0 秒、T_8 = 8.2 秒 → S_8 ≈ 5.85、E_8 ≈ 73%。

### 容量估算

| 公式 | 用途 | 算例（出處） |
|---|---|---|
| L = λ × W（Little's law） | 同時在處理中的請求數 | 400 個／秒 × 0.050 秒 = 平均 20 個，worker 至少 20、加上尖峰餘裕約 32–40（第 30 章） |
| thread 數 ≈ 核心數 × (1 + 等待時間 ÷ 計算時間) | 混合型工作的 thread pool 起點 | 純 CPU-bound 時約等於核心數（第 32 章） |
| system call 總成本 = 次數 × 單次固定成本 | 判斷是否該加緩衝 | 約 80 ns × 三百萬次 ≈ 0.24 秒（第 20 章） |
| 新連線上限 ≈ ephemeral port 數 ÷ TIME_WAIT 時間 | 短連線架構的 port 耗盡 | 28,232 ÷ 60 秒 ≈ 470 條／秒（第 28 章） |

### 硬碟隨機讀取時間

```text
 T_access ≈ T_seek + T_rotation（平均半圈）+ T_transfer
```

**算例**（第 15 章）：7,200 RPM、平均 seek 4 ms、每條 track 2,000 個 512-byte sector。一圈 60 ÷ 7,200 = 8.33 ms，平均旋轉延遲 4.17 ms，讀 4 KiB（8 個 sector）0.033 ms → 一次隨機讀約 **8.2 ms**，每秒約 120 次；同一顆碟循序讀約 120 MB/s，差兩百多倍。

## A.10 延遲數量級表

下表只給量級，真實數字依硬體而定。「L1 = 1 秒」一欄把時間放大十億倍，幫助建立直覺。出處：第 15 章（儲存階層，第 1 章有同一張表的精簡版）、第 13、16、20、23、32 章（其他事件）。

| 事件 | 延遲（量級） | L1 = 1 秒時 | 出處 |
|---|---|---|---|
| 暫存器 | 不到 1 ns | 不到 1 秒 | 第 1、15 章 |
| L1 cache hit | 約 1 ns（約 4 cycles） | 1 秒 | 第 15、16 章 |
| TLB hit | 約 1 cycle | — | 第 23 章 |
| L2 cache hit | 約數 ns（約 10 cycles） | 數秒 | 第 15、16 章 |
| 分支預測錯誤 | 約十多到二十幾個 cycles | — | 第 8、13 章 |
| L3 cache hit | 約十幾到數十 ns（約 40–75 cycles） | 十幾秒到半分鐘 | 第 15、16 章 |
| 無競爭的 atomic／mutex | 數 ns | — | 第 32 章 |
| cache line 在核心間搬移 | 每次數十到上百 cycles | — | 第 32 章 |
| TLB miss（page walk） | 數十到數百 cycles | — | 第 23 章 |
| DRAM | 約 100 ns | 約 1.5 分鐘 | 第 15 章 |
| 一次 system call 的固定成本 | 約 80 ns（本機量測） | — | 第 20 章 |
| minor page fault | 約數百 ns 到數 µs | — | 第 23 章 |
| 鎖競爭導致睡眠與喚醒 | µs 級 | — | 第 32 章 |
| NVMe SSD 隨機讀 | 約數十到上百 µs | 約半天到一天 | 第 15 章 |
| major page fault | 數十 µs 到數 ms | — | 第 23 章 |
| HDD 隨機讀（seek） | 約數 ms | 約兩個月 | 第 15 章 |

## A.11 常見 signal 編號與預設動作

Linux 與 macOS 的前 15 號大致相同，之後差很多；寫程式一律用名稱，不要寫數字。被 signal n 終止的 process，shell 看到的結束碼是 **128 + n**。出處：第 22 章（主表）、第 2 章（結束碼）、第 10、12、20、24 章（SIGBUS、SIGILL、SIGTRAP）。

| 名稱 | Linux | macOS | 預設動作 | 典型來源 | Linux 結束碼 | 章節 |
|---|---|---|---|---|---|---|
| `SIGHUP` | 1 | 1 | 終止 | 終端機斷線；慣例上要求 daemon 重新載入設定 | 129 | 22 |
| `SIGINT` | 2 | 2 | 終止 | `Ctrl-C` | 130 | 22 |
| `SIGQUIT` | 3 | 3 | 終止並 core dump | `Ctrl-\` | 131 | 22 |
| `SIGILL` | 4 | 4 | 終止並 core dump | 執行 CPU 不支援的指令（例如用 `-march=native` 編出的 binary 放到舊機器上） | 132 | 12、20 |
| `SIGTRAP` | 5 | 5 | 終止並 core dump | `int3` 中斷點、`__builtin_trap()` | 133 | 2、20 |
| `SIGABRT` | 6 | 6 | 終止並 core dump | `abort()`、`assert`、stack canary、glibc 偵測到 heap 損壞 | 134 | 2、22 |
| `SIGBUS` | 7 | 10 | 終止並 core dump | `mmap` 的檔案被截短；部分平台的未對齊存取 | 135 | 10、24 |
| `SIGFPE` | 8 | 8 | 終止並 core dump | 整數除以 0、`INT_MIN / -1` | 136 | 5、20、22 |
| `SIGKILL` | 9 | 9 | 終止（無法攔截、無法忽略） | `kill -9`、OOM killer | 137 | 2、22、24 |
| `SIGUSR1` | 10 | 30 | 終止 | 應用程式自訂 | 138 | 22 |
| `SIGSEGV` | 11 | 11 | 終止並 core dump | 存取未映射位址或違反權限 | 139 | 2、22、23 |
| `SIGUSR2` | 12 | 31 | 終止 | 應用程式自訂 | 140 | — |
| `SIGPIPE` | 13 | 13 | 終止 | 寫入對方已關閉的 pipe 或 socket | 141 | 22、28 |
| `SIGALRM` | 14 | 14 | 終止 | `alarm()` 到期 | 142 | 22 |
| `SIGTERM` | 15 | 15 | 終止 | `kill` 的預設；systemd、Kubernetes 要求結束 | 143 | 22 |
| `SIGCHLD` | 17 | 20 | 忽略 | 子行程結束或暫停 | — | 21、22 |
| `SIGCONT` | 18 | 19 | 繼續（若已暫停） | `fg`、`bg`、`kill -CONT` | — | 22 |
| `SIGSTOP` | 19 | 17 | 暫停（無法攔截、無法忽略） | `kill -STOP`、除錯器 | — | 22 |
| `SIGTSTP` | 20 | 18 | 暫停 | `Ctrl-Z` | — | 22 |

**算例一**（第 2 章）：程式結束碼 139 → 139 − 128 = 11 → `SIGSEGV`；137 → 9 → `SIGKILL`，在容器裡常是 OOM killer。

**算例二**（第 22 章）：`/proc/PID/status` 的 `SigCgt: 0x4003`，為 1 的 bit 是 0、1、14，signal 編號是 bit + 1，所以 `SIGHUP`、`SIGINT`、`SIGTERM` 有 handler。

另外三條規則（第 22 章）：同一種 pending signal 只記一次（signal 不排隊）；handler 只能呼叫 async-signal-safe 函式；共享旗標用 `volatile sig_atomic_t`。

## A.12 常見 errno

errno 的**名稱**由 POSIX 規定，**數值**依平台而定，程式中一律用名稱比較。表中 Linux 數值是 x86-64 與 ARM64 共用的通用值；`EAGAIN` 與 `EWOULDBLOCK` 在兩個平台上都是同一個值。

| 名稱 | Linux | macOS | `strerror` 意思 | 典型情境 | 章節 |
|---|---|---|---|---|---|
| `ENOENT` | 2 | 2 | No such file or directory | 原圖已刪；`execvp` 找不到程式或 shebang 的直譯器 | 20、21、27 |
| `EINTR` | 4 | 4 | Interrupted system call | 阻塞的 `read`、`accept` 期間收到 signal | 20、22、27 |
| `EBADF` | 9 | 9 | Bad file descriptor | 用了已經 `close` 的 fd | 20、27 |
| `ECHILD` | 10 | 10 | No child processes | `waitpid(-1, …)` 時已沒有子行程 | 21 |
| `EAGAIN` | 11 | 35 | Resource temporarily unavailable | non-blocking fd 沒有資料；`fork`／`pthread_create` 碰到數量上限 | 20、21、30 |
| `ENOMEM` | 12 | 12 | Cannot allocate memory | `mmap` 失敗、VMA 數超過 `vm.max_map_count` | 20、24 |
| `EACCES` | 13 | 13 | Permission denied | 權限設錯的檔案或目錄 | 20、27 |
| `EINVAL` | 22 | 22 | Invalid argument | `mmap` 的 offset 沒對齊 page、length 為 0 | 24 |
| `EMFILE` | 24 | 24 | Too many open files | fd 洩漏，碰到 `ulimit -n` | 20、27 |
| `ENOSPC` | 28 | 28 | No space left on device | 磁碟滿；先出現 short write，下一次才回傳錯誤 | 27 |
| `EPIPE` | 32 | 32 | Broken pipe | 忽略 `SIGPIPE` 後寫入已關閉的連線 | 22、28、29 |
| `ENOSYS` | 38 | 78 | Function not implemented | macOS 的 `sem_init` | 31 |
| `EADDRINUSE` | 98 | 48 | Address already in use | 重啟時舊連線停在 TIME_WAIT，或舊 process 還在 | 28 |
| `EADDRNOTAVAIL` | 99 | 49 | Cannot assign requested address | 短連線太多、ephemeral port 用完，`connect` 失敗 | 28 |
| `ECONNRESET` | 104 | 54 | Connection reset by peer | 對方 crash 或送出 RST | 27、28、29 |
| `ETIMEDOUT` | 110 | 60 | Connection timed out | `connect` 等很久才逾時 | 28 |
| `ECONNREFUSED` | 111 | 61 | Connection refused | 沒有程式在那個 IP:port listen | 28 |

錯誤回報有三種風格（第 20 章）：Unix 風格回傳 −1 並設定 `errno`；Posix threads 風格**回傳值本身就是錯誤碼**、不保證設定 `errno`；`getaddrinfo` 回傳 `EAI_*`，要用 `gai_strerror`。Linux 的原始 system call 失敗時在 `%rax` 回傳 −4095 到 −1 之間的值，也就是 −errno，由 libc 的 wrapper 轉成 −1 加 `errno`。

**算例**（第 20 章）：`strace` 印出 `openat(AT_FDCWD, "/data/a.jpg", O_RDONLY) = -1 EACCES (Permission denied)`，代表 kernel 實際回傳的是 −13；如果程式 log 寫的卻是 `Inappropriate ioctl for device`，就是讀 `errno` 之前又呼叫了別的函式把它覆蓋掉。

## A.13 延伸閱讀

- [Linux man pages](https://man7.org/linux/man-pages/)：`errno(3)`、`signal(7)`、`proc(5)`、`mmap(2)`。
- [System V AMD64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI)：型別大小、對齊與呼叫慣例的正式定義。
- [Intel 64 and IA-32 Architectures Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)：paging 與 condition codes 的完整規格。
- [CS:APP 3e 勘誤](https://csapp.cs.cmu.edu/3e/errata.html)：對照原書的公式與數字時使用。
