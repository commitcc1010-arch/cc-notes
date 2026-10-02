---
chapter: 16
title: Cache 組織與運作
part: 4
---

# 第 16 章　Cache：組織、命中與失誤

> [!abstract] 本章地圖
> **核心問題**：CPU cache 只能在一兩個 ns 內決定「資料在不在這裡」，它怎麼組織才能找得這麼快？為什麼有些看起來無害的數字（例如影像寬度剛好 4096）會讓程式慢好幾倍？
>
> **你會學到**：
> - 用 (S, E, B, m) 四個參數描述任何一個 cache，並算出它的容量
> - 把一個位址切成 tag、set index、block offset，手算它會落在哪個 set、是 hit 還是 miss
> - 分辨 direct-mapped、set associative、fully associative 三種組織的取捨
> - 判斷一個 miss 屬於 cold、conflict 還是 capacity，並知道各自的修法
> - 說明 write-through、write-back、write-allocate 的差別，以及多層 cache 的 AMAT 怎麼算
> - 寫一個參數化的 cache 模擬器，用它解釋真實的效能問題
>
> **前置知識**：第 15 章（記憶體階層與 cache 的一般概念）、第 3 章（二進位與位元運算）
>
> **對應 CS:APP 3e**：第 6 章 6.4 節

## 16.1 故事：寬度 4096 的詛咒

拾光相簿上線了「全景照片」功能。上線第二天，產品經理 Lisa 在群組裡貼了一張監控截圖：「全景照片的縮圖延遲是一般照片的四倍，使用者在抱怨。」

小安先懷疑是全景照片比較大，但數字對不上：一般照片寬 4000 像素，全景照片的測試樣本寬 4096 像素，只多了 2%。小安再測了一張寬 4200 的照片，延遲卻完全正常。換句話說，4000 正常、4200 正常，偏偏 4096 慢了四倍。

小安用 profiler（第 14 章）定位到 `thumbd` 縮放的第二階段：縮放先做水平方向，再做垂直方向，垂直方向的迴圈要一行一行往下讀像素。老周看了一眼影像寬度，說：「4096 是 2 的 12 次方。你往下走一列，位址就加 4096，每一列的同一個 column 都會掉進 cache 的同一個 set，八個位置馬上就被擠滿。cache 明明還有大片空位，你的資料卻在同一格裡互相踢來踢去。」

小安聽不懂「set」是什麼，也不懂為什麼位址剛好差 4096 就會擠在一起。這一章要把 cache 的內部組織拆開：位址怎麼被切成幾段、每一段決定什麼、資料什麼時候會互相衝突。讀完之後，你可以手算出老周那句話，也能寫一個模擬器重現這個問題，並知道怎麼修。

## 16.2 Cache 的通用組織：S、E、B 與 m

第 15 章說過，cache 以 **block**（區塊）為單位存放下一層的資料。但 CPU cache 不能像一般的 hash table 那樣慢慢找，它必須在數個 cycle 內回答「這個位址的資料在不在」。為了做到這一點，所有 CPU cache 都採用同一種組織方式：

```text
 一個 cache = S 個 set，每個 set 有 E 條 line，每條 line 存一個 B bytes 的 block

          ┌── line 0 ──────────────────────────────────────┐
 set 0    │ valid │  tag  │ byte 0 │ byte 1 │ … │ byte B−1 │
          ├── line 1 ──────────────────────────────────────┤
          │ valid │  tag  │ byte 0 │ byte 1 │ … │ byte B−1 │
          ├── …（共 E 條）──────────────────────────────────┤
          └────────────────────────────────────────────────┘
 set 1    │ E 條 line，結構同上                              │
   ⋮
 set S−1  │ E 條 line                                       │

 每條 line 的組成：
   valid bit：1 表示這條 line 存著有效資料
   tag      ：用來辨認「這條 line 存的是哪一個 block」
   block    ：從下一層複製上來的 B bytes 資料
```

四個參數完整描述一個 cache：

| 參數 | 意義 | 推導出的位元數 | 例子（典型 L1 data cache） |
|---|---|---|---|
| m | 位址有幾個 bits | — | 48 |
| S | set 的數量（2 的冪） | s = log2(S) 個 set index bits | 64 → s = 6 |
| E | 每個 set 有幾條 line（associativity） | — | 8 |
| B | 每個 block 有幾個 bytes（2 的冪） | b = log2(B) 個 block offset bits | 64 → b = 6 |
| — | 剩下的高位 bits | t = m − s − b 個 tag bits | 48 − 6 − 6 = 36 |

**Cache 的容量** C 只算資料本身，不算 valid bit 與 tag：

```text
C = S × E × B = 64 × 8 × 64 bytes = 32,768 bytes = 32 KiB
```

這三個字要分清楚，它們常被混用：**block** 是資料的單位（從記憶體搬上來的那 B bytes）；**line** 是 cache 裡的一個容器（valid ＋ tag ＋ block）；**set** 是一組 E 條 line。業界常把 block 叫做 cache line，說「cache line 是 64 bytes」時指的就是 B。

## 16.3 位址切分：tag、set index、block offset

### 三段各管什麼

CPU 拿到一個位址，就把它切成三段：

```text
 m-bit 位址
 m−1                                                 0
 ┌──────────────────────┬──────────────┬─────────────┐
 │       tag (t bits)    │ set index (s)│ offset (b)  │
 └──────────┬───────────┴──────┬───────┴──────┬──────┘
            │                  │              │
            │                  │              └─ ③ 在 block 裡取第幾個 byte
            │                  └─ ① 決定去哪一個 set 找
            └─ ② 在那個 set 的 E 條 line 中，比對誰的 tag 相同
```

查找分三步：① 用 set index 直接選出一個 set，這一步像陣列索引一樣是 O(1)；② 把這個 set 裡所有 valid line 的 tag 與位址的 tag 比對，有相同的就是 **hit**；③ 用 block offset 從 block 中取出要的 byte。如果 ② 找不到，就是 **miss**，要從下一層搬整個 block 上來。

這個設計的關鍵在 ①：因為 set index 直接決定位置，硬體只需要在一個 set 的 E 條 line 裡比對，而不是整個 cache。E 通常只有 4 到 16，硬體可以同時（平行）比對完。

### 手算一次

用 16.2 節的 L1：S = 64、E = 8、B = 64、m = 48，所以 b = 6、s = 6、t = 36。切分位址 `0x12345678`：

```text
0x12345678 的最低 16 bits = 0101 0110 0111 1000
                                    └set──┘└off─┘
offset    = 位址 & 0x3F          = 0x38 = 56     （block 裡第 56 個 byte）
set index = (位址 >> 6) & 0x3F   = 25            （去 set 25 找）
tag       = 位址 >> 12           = 0x12345       （和 set 25 裡的 tag 比對）
```

再看兩個鄰居：

| 位址 | 和 0x12345678 的差 | offset | set index | tag | 說明 |
|---|---|---|---|---|---|
| 0x12345678 | 0 | 0x38 | 25 | 0x12345 | 基準 |
| 0x1234567C | +4 | 0x3C | 25 | 0x12345 | 同一個 block，一定一起進 cache |
| 0x123456B8 | +64 | 0x38 | 26 | 0x12345 | 下一個 block，落在下一個 set |
| 0x12346678 | +4096 | 0x38 | 25 | 0x12346 | 同一個 set，不同 tag：會搶位置 |

最後一列就是 16.1 節的答案。這個 cache 的 set index 與 offset 合起來只有 12 bits，也就是位址的最低 12 bits；**任何兩個相差 4096 整數倍的位址，最低 12 bits 都相同，所以一定落在同一個 set**。一張寬 4096 bytes 的影像，同一個 column 往下的每一列都相差 4096 bytes，全部擠進同一個 set，而一個 set 只有 8 條 line。

### 為什麼 set index 用中間的 bits

你可能會問：為什麼不用最高的幾個 bits 當 set index？看一個連續陣列被掃描時會發生什麼：

```text
 一段連續的記憶體（block 0 到 block 7），cache 有 4 個 set

 用「中間 bits」當 index：          用「高位 bits」當 index：
 block 0 → set 0                   block 0 → set 0
 block 1 → set 1                   block 1 → set 0
 block 2 → set 2                   block 2 → set 0
 block 3 → set 3                   block 3 → set 0
 block 4 → set 0                   block 4 → set 0   ← 相鄰的 block 高位相同，
 block 5 → set 1                   block 5 → set 0     全部擠在同一個 set
   …                                 …
 連續資料平均分到所有 set            整個 cache 只用到一個 set
```

相鄰的 block 位址只差在低位，高位幾乎都一樣。如果用高位當 index，掃描一個陣列時所有 block 都擠進同一個 set，其他 set 完全閒置。用 offset 正上方的中間 bits 當 index，連續的 block 會輪流分到不同 set，一段長度為 C 的連續資料剛好可以把整個 cache 填滿。這正是程式最常見的存取模式，所以所有 CPU cache 都這樣設計。

## 16.4 Direct-mapped cache：每個 set 只有一條 line

E = 1 的 cache 叫 **direct-mapped cache**（直接映射快取）：每個 set 只有一條 line，所以一個 block 只有一個位置可以放。它的硬體最簡單：選出 set 後只要比對一個 tag。

### 一個可以手算的迷你 cache

為了能用手算，我們設計一個很小的 cache：

| 參數 | 值 | 位元數 |
|---|---|---|
| 位址 | 8 bits | m = 8 |
| block | 8 bytes | b = 3 |
| set 數 | 4 | s = 2 |
| 每個 set | 1 條 line | E = 1（direct-mapped） |
| tag | — | t = 8 − 2 − 3 = 3 |
| 容量 | 4 × 1 × 8 = 32 bytes | — |

`thumbd` 的某段程式依序讀取下面 8 個位址（都是讀取，一次讀 1 byte）。先把每個位址切開：

| 位址 | 二進位（tag｜set｜offset） | block 編號 | tag | set |
|---|---|---|---|---|
| 0x00 | 000｜00｜000 | 0 | 0 | 0 |
| 0x04 | 000｜00｜100 | 0 | 0 | 0 |
| 0x1C | 000｜11｜100 | 3 | 0 | 3 |
| 0x20 | 001｜00｜000 | 4 | 1 | 0 |
| 0x00 | 000｜00｜000 | 0 | 0 | 0 |
| 0x24 | 001｜00｜100 | 4 | 1 | 0 |
| 0x3C | 001｜11｜100 | 7 | 1 | 3 |
| 0x1C | 000｜11｜100 | 3 | 0 | 3 |

block 編號就是位址除以 8（去掉 offset），set 是 block 編號除以 4 的餘數，tag 是 block 編號除以 4 的商。現在一步一步模擬，cache 一開始全部 invalid：

| 步驟 | 位址 | set | 結果 | 動作 | 執行後 set 0 | 執行後 set 3 |
|---|---|---|---|---|---|---|
| 1 | 0x00 | 0 | miss（cold） | 載入 block 0 | tag 0 | — |
| 2 | 0x04 | 0 | **hit** | 同一個 block | tag 0 | — |
| 3 | 0x1C | 3 | miss（cold） | 載入 block 3 | tag 0 | tag 0 |
| 4 | 0x20 | 0 | miss（cold） | 踢掉 block 0，載入 block 4 | tag 1 | tag 0 |
| 5 | 0x00 | 0 | miss（conflict） | 踢掉 block 4，載入 block 0 | tag 0 | tag 0 |
| 6 | 0x24 | 0 | miss（conflict） | 踢掉 block 0，載入 block 4 | tag 1 | tag 0 |
| 7 | 0x3C | 3 | miss（cold） | 踢掉 block 3，載入 block 7 | tag 1 | tag 1 |
| 8 | 0x1C | 3 | miss（conflict） | 踢掉 block 7，載入 block 3 | tag 1 | tag 0 |

結果：8 次存取只有 1 次 hit，7 次 miss，其中 4 次是 cold miss，3 次是 conflict miss。

注意整個過程中 **set 1 和 set 2 從來沒有被使用**。這段程式只用到 4 個不同的 block（0、3、4、7），總共 32 bytes，剛好等於 cache 容量；如果放置沒有限制，第一輪載入之後應該全部 hit。問題出在 block 0 和 block 4 都只能放 set 0、block 3 和 block 7 都只能放 set 3，它們互相把對方踢出去。這種反覆互踢的現象叫 **thrashing**（顛簸），是 direct-mapped cache 最大的弱點。

> [!warning] 常見誤解
> 「cache 還有空位，就不會 miss。」direct-mapped cache 裡，一個 block 只能放在它的 set，其他 set 再空也用不上。conflict miss 正是「整體有空間，但被規則擋住」的 miss。

## 16.5 Set associative cache：每個 set 有好幾條 line

**Set associative cache**（集合關聯快取）讓每個 set 有 E > 1 條 line，叫 **E-way set associative**。一個 block 仍然只能去它的 set，但在 set 裡面有 E 個位置可以選。查找時，硬體把位址的 tag 和 set 裡全部 E 條 line 的 tag 同時比對。

```text
 2-way set associative：查找 set 1

 位址：│ tag = 0001 │ set = 1 │ offset │
                      │
                      ▼
 set 1 ┌───────┬──────┬──────────┐
       │ v = 1 │ 0001 │ block 3  │ ──┐
       ├───────┼──────┼──────────┤   ├─ 兩個比較器同時比對 tag
       │ v = 1 │ 0011 │ block 7  │ ──┘
       └───────┴──────┴──────────┘
              第一條 tag 相同且 valid → hit，取出 block 3
```

miss 時要決定把新 block 放進 set 的哪一條 line。有空的（invalid）line 就放那裡；沒有空的，就要依 **replacement policy**（替換策略）挑一條踢掉，最常見的是 **LRU**（踢掉最久沒用的）。真實硬體常用 LRU 的近似版本（例如 pseudo-LRU），因為精確記錄 8 或 16 條 line 的使用順序太花電路。

### 同一串位址，換成 2-way

保持容量 32 bytes、block 8 bytes 不變，改成 2-way：E = 2，所以 S = 32 ÷ (2 × 8) = 2，s = 1，t = 8 − 1 − 3 = 4。set 變成 block 編號除以 2 的餘數：

| 步驟 | 位址 | block | set | 結果 | 執行後 set 0 | 執行後 set 1 |
|---|---|---|---|---|---|---|
| 1 | 0x00 | 0 | 0 | miss（cold） | {0} | {} |
| 2 | 0x04 | 0 | 0 | **hit** | {0} | {} |
| 3 | 0x1C | 3 | 1 | miss（cold） | {0} | {3} |
| 4 | 0x20 | 4 | 0 | miss（cold），放進空的第二條 | {0, 4} | {3} |
| 5 | 0x00 | 0 | 0 | **hit** | {0, 4} | {3} |
| 6 | 0x24 | 4 | 0 | **hit** | {0, 4} | {3} |
| 7 | 0x3C | 7 | 1 | miss（cold），放進空的第二條 | {0, 4} | {3, 7} |
| 8 | 0x1C | 3 | 1 | **hit** | {0, 4} | {3, 7} |

結果：4 次 hit、4 次 miss，而且剩下的 4 次 miss 全是無法避免的 cold miss。容量完全一樣，只是把「4 個只能放一個的位置」改成「2 個能放兩個的位置」，3 次 conflict miss 就消失了。16.11 節的模擬器會重現這兩張表。

associativity 越高，conflict miss 越少，代價是硬體：每多一 way 就要多一個 tag 比較器、更寬的多工器，耗電更多，hit time 也可能變長；替換策略也要記錄更多狀態。這就是為什麼 L1 通常是 8 到 12 way，而不是 64 way。

## 16.6 Fully associative cache：只有一個 set

把 associativity 推到極限，讓整個 cache 只有一個 set（S = 1，E = C ÷ B），就是 **fully associative cache**（全關聯快取）。這時位址沒有 set index，只有 tag 和 offset：

```text
 fully associative 的位址切分
 ┌────────────────────────────────────────┬─────────────┐
 │              tag (m − b bits)           │ offset (b)  │
 └────────────────────────────────────────┴─────────────┘
 任何 block 可以放在任何一條 line；查找時要和「所有」line 比對 tag
```

fully associative cache 沒有 conflict miss，任何 block 都能放在任何位置。但查找時要同時比對所有 line 的 tag，line 一多，電路就大到不可行。所以它只用在很小、而且 miss 代價很高的地方：

- **TLB**（第 23 章）：部分 TLB（尤其是小型的 L1 TLB）採用 fully associative 或高 associativity 的設計。
- **虛擬記憶體**：把 DRAM 當作磁碟的快取時，任何虛擬頁可以放在任何實體頁（第 23 章）。這裡的「比對」不是用電路，而是用 page table 查表，所以規模再大也做得到。

三種組織放在一起比較：

| 組織 | S | E | 一個 block 可以放的位置 | 查找成本 | conflict miss | 典型用途 |
|---|---|---|---|---|---|---|
| direct-mapped | C／B | 1 | 1 個 | 比對 1 個 tag，最快最省電 | 最多 | 早期 cache、部分特殊用途 |
| E-way set associative | C／(E × B) | E | E 個 | 平行比對 E 個 tag | 中等，E 越大越少 | 現代 L1、L2、L3 |
| fully associative | 1 | C／B | 任何位置 | 比對所有 tag | 沒有 | 小型 TLB、虛擬記憶體 |

可以把三者看成同一個設計的兩端與中間：direct-mapped 是 E = 1 的 set associative，fully associative 是 S = 1 的 set associative。理解了 set associative，另外兩種就是特例。

## 16.7 Miss 的分類：怎麼知道是哪一種

第 15 章介紹了三種 miss。現在有了具體的 cache 組織，可以用一個精確的方法把每一次 miss 分類：

```text
 對每一次 miss，依序問：
   │
   ├─ 這個 block 以前從來沒被存取過？
   │      └─ 是 → cold miss（compulsory miss）
   │
   ├─ 換成「同樣容量、fully associative、LRU」的 cache，這次也會 miss 嗎？
   │      └─ 會 → capacity miss（容量真的不夠）
   │
   └─ 不會 → conflict miss（容量夠，是放置規則造成的）
```

這個判斷法的道理是：fully associative 的 cache 沒有放置限制，它還會 miss，就只能怪容量；它不會 miss 而真實的 cache 會，就是 set 的限制造成的。16.11 節的 Python 程式就是用這個方法自動分類。

| 類型 | 在 `thumbd` 裡的例子 | 修法 |
|---|---|---|
| cold | 第一次讀進一張新圖的像素 | 無法消除；循序存取讓硬體預取器提前載入；一次 miss 帶進整個 block，盡量把 block 裡的資料都用掉 |
| conflict | 寬度 4096 的影像，直向走訪時每一列都落在同一個 set | 讓 pitch（列距，第 10 章）不是 2 的大冪次（加 padding）；改變存取順序 |
| capacity | 直向走訪時，一次要同時保留的列數乘以 block 大小超過 cache 容量 | 縮小 working set：分塊處理（第 17 章的 blocking） |

### 回到 16.1 節：為什麼 4096 這麼慢

`thumbd` 的垂直縮放迴圈大致長這樣：外層走 column x，內層往下走 y，讀 `img[y * pitch + x]`。對一個 column 往下走，會碰到每一列的一個 block；走到下一個 column x+1 時，如果這些 block 還在 cache 裡，就全部 hit（因為 x 和 x+1 在同一個 block）。所以這個迴圈要快，條件是「一整條 column 經過的所有 block 都能同時留在 cache」。

假設影像有 256 列、L1 是 32 KiB、8-way、64-byte block（S = 64）。一條 column 經過 256 個 block，共 16 KiB，小於 32 KiB，容量是夠的。關鍵在它們落在哪些 set：

```text
 pitch = 4000 bytes                        pitch = 4096 bytes
 第 y 列的 block 位址 = y × 4000 + x       第 y 列的 block 位址 = y × 4096 + x
 set = (位址 >> 6) & 63                    set = (位址 >> 6) & 63

 y = 0 → set 0                             y = 0 → set 0
 y = 1 → set 62                            y = 1 → set 0    ← 4096 的低 12 bits 全是 0，
 y = 2 → set 61                            y = 2 → set 0      y × 4096 不影響 set index
 y = 3 → set 59                            y = 3 → set 0
   …（平均分散到 64 個 set）                   …（256 個 block 全擠進同一個 set）

 每個 set 平均分到 4 個 block，8 way 放得下   一個 set 只有 8 way，要放 256 個 block
 → 下一個 column 幾乎全部 hit                → 每次都 miss，而且把下一個 column
                                                需要的 block 也踢掉了
```

pitch 4000 時，相鄰兩列的位址差 4000 bytes，4000 ÷ 64 = 62.5，每往下一列，set index 大約往前移 62 格，256 列被分散到所有 set。pitch 4096 時，4096 = 64 × 64，剛好是「set 數 × block 大小」，每往下一列 set index 完全不變。256 個 block 搶 8 個位置，LRU 下每一次都 miss，這就是純粹的 conflict miss：cache 的其他 63 個 set 都空著。

這也解釋了為什麼 4200 正常：4200 不是 4096 的倍數，各列會分散到不同 set。真正危險的是 2 的大冪次（或其倍數）的 stride，例如寬 2048、4096、8192 的影像，或大小是 2 的冪次的矩陣。

## 16.8 寫入：write-through、write-back 與 write-allocate

到目前為止都只談讀取。寫入比較複雜，因為 cache 裡的資料一旦被改，就和下一層的副本不一致了。寫入要回答兩個問題。

### 問題一：write hit 時，什麼時候更新下一層？

- **Write-through**（直寫）：每次寫 cache，同時寫到下一層。簡單，下一層永遠是最新的；但每次寫入都產生下一層的流量。
- **Write-back**（回寫）：只寫 cache，並把這條 line 的 **dirty bit**（髒位元）設為 1；等這條 line 被踢掉時，才把整個 block 寫回下一層。同一個 block 被寫很多次，只需要寫回一次，大幅減少流量；代價是每條 line 多一個 bit，替換時多一個步驟。

### 問題二：write miss 時，要不要把 block 載入 cache？

- **Write-allocate**（寫入配置）：先把 block 從下一層讀進 cache，再在 cache 裡寫。賭的是「寫了這裡，很快還會讀寫附近」。
- **No-write-allocate**（不寫入配置）：直接寫到下一層，不經過 cache。適合只寫一次、不會再讀的資料。

```text
 write-back ＋ write-allocate（現代 CPU cache 最常見的組合）

 store 到位址 A
   │
   ├─ hit ─────────────────▶ 改 cache 裡的資料，dirty = 1，結束
   │
   └─ miss ─▶ 選一條 victim line
               ├─ victim 的 dirty = 1？→ 先把 victim 整個 block 寫回下一層
               ▼
             從下一層讀入 A 所在的 block            ← write-allocate
               ▼
             在 cache 裡寫入，dirty = 1
```

兩個問題的答案通常成對出現：

| 組合 | 寫入流量 | 實作複雜度 | 典型用途 |
|---|---|---|---|
| write-through ＋ no-write-allocate | 每次寫入都到下一層 | 簡單 | 部分 L1 設計、某些嵌入式處理器 |
| write-back ＋ write-allocate | 只在踢出 dirty line 時寫回 | 需要 dirty bit 與寫回邏輯 | 現代 x86-64、ARM 的各層 cache 普遍採用 |

寫程式時，把 cache 想成 write-back ＋ write-allocate 是比較安全的心智模型。它帶來一個常被忽略的後果：**對一個不在 cache 的 block 做寫入，會先觸發一次讀取**。如果程式要把一大塊記憶體整個覆寫（例如 `memset` 一個大緩衝區、把縮圖寫進新配置的輸出陣列），那次讀取完全浪費。高效能的 `memset`／`memcpy` 實作會在適合時使用不經過 cache 的 **non-temporal store**（x86-64 的 `movnt` 系列指令）避開這個代價。

### 多核心的一致性

多核心各有自己的 L1、L2。如果核心 0 把某個 block 改了（在 write-back cache 裡只有它有最新版本），核心 1 再讀同一個位址，不能讀到舊值。硬體用 **cache coherence protocol**（快取一致性協定）處理這件事，最經典的是 **MESI**：每條 line 處於 Modified（我改過，只有我有）、Exclusive（只有我有，沒改過）、Shared（大家都有唯讀副本）、Invalid（無效）四種狀態之一，核心要寫入前必須先讓其他核心的副本變成 Invalid。

一致性以 block 為單位追蹤，這帶來 **false sharing**（偽共享）：兩個 thread 寫不同的變數，但變數剛好在同一個 block 裡，block 就會在兩個核心之間來回搬。第 32 章會詳細討論它和 thread 效能的關係。

## 16.9 真實的 cache 階層

### Intel Core i7 的例子

CS:APP 以 Intel Core i7（Haswell 世代）為例說明真實的 cache 階層。每個核心有自己的 L1 與 L2，所有核心共用 L3：

```text
 處理器晶片
 ┌──────────────────────────────────────────────────────────┐
 │  核心 0                          核心 3                    │
 │  ┌───────────────────────┐      ┌───────────────────────┐ │
 │  │ 暫存器                 │      │ 暫存器                 │ │
 │  │ ┌──────────┐┌────────┐│  …   │ ┌──────────┐┌────────┐│ │
 │  │ │L1 d-cache││L1 i-cache│      │ │L1 d-cache││L1 i-cache││ │
 │  │ └──────────┘└────────┘│      │ └──────────┘└────────┘│ │
 │  │ ┌───────────────────┐ │      │ ┌───────────────────┐ │ │
 │  │ │ L2 unified cache  │ │      │ │ L2 unified cache  │ │ │
 │  │ └───────────────────┘ │      │ └───────────────────┘ │ │
 │  └───────────────────────┘      └───────────────────────┘ │
 │  ┌──────────────────────────────────────────────────────┐ │
 │  │        L3 unified cache（所有核心共用）                 │ │
 │  └──────────────────────────────────────────────────────┘ │
 └─────────────────────────────┬────────────────────────────┘
                               ▼
                           主記憶體
```

| cache | 存什麼 | 容量 | associativity | 存取時間 | 屬於 |
|---|---|---|---|---|---|
| L1 i-cache | 指令 | 32 KiB | 8-way | 約 4 cycles | 每個核心 |
| L1 d-cache | 資料 | 32 KiB | 8-way | 約 4 cycles | 每個核心 |
| L2 unified | 指令與資料 | 256 KiB | 8-way | 約 10 cycles | 每個核心 |
| L3 unified | 指令與資料 | 8 MiB | 16-way | 約 40–75 cycles | 所有核心共用 |

所有層的 block 都是 64 bytes。幾個值得注意的設計：

- **L1 分成 i-cache 與 d-cache**：CPU 每個 cycle 同時要抓指令和讀寫資料，分開兩個 cache 可以同時服務，也能各自針對存取模式最佳化。只存資料的叫 d-cache，只存指令的叫 i-cache，兩者都存的叫 **unified cache**。
- **越下層越大、越慢、越共享**：L3 由所有核心共用，所以多個 thread 共用同一份資料時，可以在 L3 裡命中，而不用到 DRAM。
- **inclusive 或 exclusive**：有些設計保證 L3 一定包含 L1、L2 的所有內容（inclusive），有些則讓 L3 主要存放從 L2 被踢出的 block（exclusive 或 victim cache）。不同世代、不同廠商的作法不同，要查該處理器的文件。

新的世代數字都變了：近年的 x86-64 處理器 L1 data cache 常見 32 KiB 或 48 KiB，L2 從 1 MiB 到 2 MiB 以上，L3 可達數十 MiB。用 16.12 節的指令查自己機器的實際值。

### Apple Silicon 的例子

在本書作者使用的 Apple M4 Pro 上，`sysctl` 回報的數字如下（Apple 沒有透過 `sysctl` 提供 associativity）：

| 項目 | 效能核心（perflevel0） | 節能核心（perflevel1） |
|---|---|---|
| cache line（block）大小 | 128 bytes | 128 bytes |
| L1 data cache | 128 KiB | 64 KiB |
| L2 cache | 16 MiB（同一群核心共用） | 4 MiB（同一群核心共用） |

和 x86-64 最大的差別是 block 大小 128 bytes。這意味著位址切分的 b = 7，第 15 章 15.10 節量到的 stride 轉折點也落在 128 bytes。寫跨平台的效能敏感程式碼時，不能把 64 bytes 寫死。

### Cache 用的是實體位址還是虛擬位址？

程式用的是虛擬位址（第 23 章），但 L2、L3 是用實體位址索引與比對的。L1 為了快，常用一個巧妙的設計：**用虛擬位址的 set index 選 set，同時讓 TLB 轉譯出實體位址，再用實體位址的 tag 比對**，叫 VIPT（virtually indexed, physically tagged）。這要求 set index 與 offset 完全落在 page offset 之內（翻譯不會改變這些 bits），也就是：

```text
S × B ≤ page 大小   ⟺   C ÷ E ≤ page 大小

x86-64：32 KiB ÷ 8-way = 4 KiB = page 大小   ← 剛好相等
48 KiB 的 L1 則搭配 12-way：48 KiB ÷ 12 = 4 KiB
```

這說明了一個看似巧合的現象：x86-64 的 L1 容量長期停在「4 KiB × way 數」；要加大 L1，就必須同時提高 associativity。Apple Silicon 的 page 是 16 KiB，這讓它可以在相同 way 數下做出大得多的 L1。這也是 16.7 節 4096 問題的另一面：在 32 KiB、8-way 的 L1 裡，set index ＋ offset 剛好是 12 bits，任何相差 4 KiB 倍數的位址必然撞在同一個 set。

## 16.10 Cache 參數對效能的影響

### 衡量 cache 效能的指標

| 指標 | 定義 | 典型量級 |
|---|---|---|
| miss rate | miss 次數 ÷ 存取次數 | L1 通常只有幾 %，L2、L3 的 local miss rate 可能高得多 |
| hit rate | 1 − miss rate | — |
| hit time | 從 cache 取得資料的時間（含選 set、比 tag、取 byte） | L1 約 4 cycles |
| miss penalty | miss 時額外多花的時間 | 到 L2 約 10 cycles，到 DRAM 數百 cycles |

### 多層 cache 的 AMAT

第 15 章的 AMAT 公式可以一層一層展開：L1 的 miss penalty，就是「到 L2 去找」的平均時間。

```text
AMAT = L1 hit time + L1 miss rate × (L2 hit time + L2 miss rate × DRAM 時間)
```

手算一次：L1 hit 4 cycles、L1 miss rate 5%；L2 hit 12 cycles，L2 的 **local miss rate**（在到達 L2 的存取中 miss 的比例）20%；DRAM 200 cycles。

```text
有 L2：AMAT = 4 + 0.05 × (12 + 0.20 × 200)
            = 4 + 0.05 × 52
            = 4 + 2.6 = 6.6 cycles

沒有 L2：AMAT = 4 + 0.05 × 200 = 14 cycles
```

L2 的 miss rate 高達 20%，看起來很差，但它攔下了 80% 原本要到 DRAM 的存取，平均存取時間從 14 cycles 降到 6.6 cycles。所以下層 cache 的 local miss rate 高是正常的：最容易命中的存取早就在 L1 被處理掉了，到得了 L2 的都是「比較難」的那些。

### 每個參數的取捨

| 參數 | 加大的好處 | 加大的代價 |
|---|---|---|
| 容量 C | capacity miss 減少，working set 更容易放進去 | hit time 變長（電路更大、訊號走更遠）、更耗電、更佔晶片面積。所以 L1 小而快，L3 大而慢 |
| block 大小 B | 更好地利用 spatial locality，cold miss 減少 | 同容量下 line 數變少，temporal locality 差的程式更多 miss；miss penalty 變大（要搬更多 bytes）；false sharing 範圍更大 |
| associativity E | conflict miss 減少 | 比較器更多、hit time 可能變長、更耗電、替換邏輯更複雜。L1 通常 8–12 way，下層 cache 的 miss penalty 大，常用更高的 associativity |
| 寫入策略 | write-back 減少下層流量 | 需要 dirty bit 與寫回機制，一致性處理更複雜 |

這張表沒有「越大越好」的答案，每個選擇都在 hit time、miss rate 與 miss penalty 之間取捨。對寫軟體的人，重點不是設計 cache，而是知道自己的程式踩到的是哪一種限制：working set 太大（capacity）、stride 撞到 set（conflict）、還是 block 裡只用了一小部分（浪費頻寬）。

## 16.11 動手做：寫一個 cache 模擬器

### 程式一：參數化的 C 模擬器

這個模擬器接受 s、E、b 三個參數，實作 LRU 替換、write-back ＋ write-allocate。它不存真正的資料，只記錄每條 line 的 valid、dirty、tag 和最後使用時間，因為判斷 hit 或 miss 只需要這些。第一部分重現 16.4 與 16.5 節的手算；第二部分模擬 `thumbd` 的直向走訪。

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* 參數化的 cache 模擬器：S = 2^s 個 set、每個 set E 條 line、block B = 2^b bytes。
 * 替換策略 LRU；寫入策略 write-back + write-allocate。 */
typedef struct { int valid, dirty; uint64_t tag; long last_used; } line_t;
typedef struct {
    int s, E, b;
    line_t *lines;                       /* S × E 條 line，攤平成一維陣列 */
    long tick, hits, misses, evictions, writebacks;
} cache_t;

static cache_t *cache_new(int s, int E, int b) {
    cache_t *c = calloc(1, sizeof *c);
    c->s = s; c->E = E; c->b = b;
    c->lines = calloc((size_t)E << s, sizeof(line_t));
    return c;
}

/* 回傳 'H'（hit）、'M'（miss，放進空 line）或 'E'（miss 且踢掉一條 line） */
static char cache_access(cache_t *c, uint64_t addr, int is_write) {
    uint64_t set = (addr >> c->b) & ((1ULL << c->s) - 1);   /* 中間 s 個 bit */
    uint64_t tag = addr >> (c->b + c->s);                    /* 剩下的高位 bit */
    line_t *row = &c->lines[set * (uint64_t)c->E];
    c->tick++;
    for (int i = 0; i < c->E; i++)
        if (row[i].valid && row[i].tag == tag) {             /* 同一個 set 裡逐條比 tag */
            c->hits++;
            row[i].last_used = c->tick;
            row[i].dirty |= is_write;
            return 'H';
        }
    c->misses++;
    int victim = 0;                                          /* 先找空 line，否則挑最久沒用的 */
    for (int i = 0; i < c->E; i++) {
        if (!row[i].valid) { victim = i; break; }
        if (row[i].last_used < row[victim].last_used) victim = i;
    }
    char result = 'M';
    if (row[victim].valid) {
        c->evictions++;
        if (row[victim].dirty) c->writebacks++;              /* write-back：被踢掉時才寫回 */
        result = 'E';
    }
    row[victim] = (line_t){1, is_write, tag, c->tick};      /* write-allocate：寫 miss 也載入 */
    return result;
}

static void report(const char *name, const cache_t *c) {
    printf("%-30s hits %7ld  misses %7ld  evictions %7ld  miss rate %5.1f%%\n", name,
           c->hits, c->misses, c->evictions, 100.0 * c->misses / (c->hits + c->misses));
}

int main(void) {
    /* 第一部分：重現 16.4 與 16.5 節的手算（8-bit 位址、8-byte block、32-byte cache） */
    uint64_t trace[] = {0x00, 0x04, 0x1C, 0x20, 0x00, 0x24, 0x3C, 0x1C};
    int n = sizeof trace / sizeof trace[0];
    cache_t *dm = cache_new(2, 1, 3), *two = cache_new(1, 2, 3);
    printf("addr  direct-mapped  2-way\n");
    for (int i = 0; i < n; i++) {
        char r1 = cache_access(dm, trace[i], 0), r2 = cache_access(two, trace[i], 0);
        printf("0x%02llx  %c              %c\n", (unsigned long long)trace[i], r1, r2);
    }
    report("direct-mapped (S=4, E=1)", dm);
    report("2-way (S=2, E=2)", two);
    free(dm->lines); free(dm); free(two->lines); free(two);

    /* 第二部分：thumbd 的直向掃描。模型：32 KiB、8-way、64-byte line 的 L1 */
    long pitches[] = {4000, 4096};
    for (int k = 0; k < 2; k++) {
        cache_t *l1 = cache_new(6, 8, 6);                  /* 64 sets × 8 ways × 64 B */
        for (long x = 0; x < 256; x++)                     /* 256 個 column */
            for (long y = 0; y < 256; y++)                 /* 每個 column 往下讀 256 列 */
                cache_access(l1, (uint64_t)(y * pitches[k] + x), 0);
        char name[64];
        snprintf(name, sizeof name, "column walk, pitch %ld", pitches[k]);
        report(name, l1);
        free(l1->lines);
        free(l1);
    }
    return 0;
}
```

在 macOS arm64 上編譯執行（模擬的結果與執行平台無關）：

```text
addr  direct-mapped  2-way
0x00  M              M
0x04  H              H
0x1c  M              M
0x20  E              M
0x00  E              H
0x24  E              H
0x3c  E              M
0x1c  E              H
direct-mapped (S=4, E=1)       hits       1  misses       7  evictions       5  miss rate  87.5%
2-way (S=2, E=2)               hits       4  misses       4  evictions       0  miss rate  50.0%
column walk, pitch 4000        hits   64384  misses    1152  evictions     640  miss rate   1.8%
column walk, pitch 4096        hits       0  misses   65536  evictions   65504  miss rate 100.0%
```

逐段對照：

1. **前八行與 16.4、16.5 節的手算表完全一致。** direct-mapped 欄的 `E` 表示 miss 而且踢掉了別人：0x20 踢掉 block 0、0x00 又踢掉 block 4，這就是 thrashing。2-way 欄只有四次 cold miss，沒有任何 eviction。
2. **pitch 4000：miss rate 1.8%。** 256 個 column 共 65,536 次存取，只有 1,152 次 miss。每個 64-byte block 涵蓋 64 個 column，所以每條 column 的 block 只需要在第一次載入；之後 63 個 column 都 hit。miss 次數比理想的 1,024（256 列 × 4 個 block）多一點，因為 4000 不是 64 的倍數，有些列的 block 邊界沒有對齊。
3. **pitch 4096：miss rate 100%。** 正如 16.7 節的推導，每一列都落在同一個 set，8 條 line 要服務 256 個 block，LRU 下每一次都在 x 往下一格時被踢掉，整個 cache 只有 4 個 set 被用到（x 從 0 到 255 跨了 4 個 block）。

### 程式二：在真實的 CPU 上量

模擬器說 pitch 4096 會出事，真實硬體是不是這樣？這段程式在同一張 4000 × 512 的影像上做直向走訪，只改變 pitch（多出的部分是不使用的 padding）。

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* 直向掃描一張 4000 × 512 的灰階影像（每像素 1 byte），
 * 只改變 row pitch（每一列在記憶體中佔幾個 bytes），量測每個像素的平均時間。 */
#define WIDTH 4000
#define ROWS 512

static double now_ns(void) {                 /* 目前時間，單位 ns */
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static long column_sum(const uint8_t *img, long pitch) {
    long sum = 0;
    for (long x = 0; x < WIDTH; x++)          /* 外層走 column */
        for (long y = 0; y < ROWS; y++)       /* 內層往下走：每次跳 pitch bytes */
            sum += img[y * pitch + x];
    return sum;
}

int main(void) {
    long pitches[] = {4000, 4096, 4096 + 64, 8192, 8192 + 64};
    long checksum = 0;
    for (int k = 0; k < 5; k++) {
        long pitch = pitches[k];
        uint8_t *img = malloc((size_t)(pitch * ROWS));
        if (!img) return 1;
        for (long i = 0; i < pitch * ROWS; i++) img[i] = (uint8_t)i;
        double best = 1e30;
        for (int rep = 0; rep < 5; rep++) {   /* 取 5 次中最快的一次，減少雜訊 */
            double t0 = now_ns();
            checksum += column_sum(img, pitch);
            double t = now_ns() - t0;
            if (t < best) best = t;
        }
        printf("pitch %5ld bytes：%.2f ns／像素\n", pitch, best / ((double)WIDTH * ROWS));
        free(img);
    }
    printf("checksum = %ld\n", checksum);
    return 0;
}
```

在 macOS arm64（Apple M4 Pro，Apple clang 21，`-O1`）上執行：

```text
pitch  4000 bytes：0.25 ns／像素
pitch  4096 bytes：0.91 ns／像素
pitch  4160 bytes：0.28 ns／像素
pitch  8192 bytes：1.12 ns／像素
pitch  8256 bytes：0.28 ns／像素
checksum = 6486056960
```

解讀：

1. **pitch 4096 和 8192 比 4000 慢約四倍**，和 Lisa 回報的現象一致。每個像素處理的運算完全一樣，差別只在位址落在哪些 set。
2. **只要多加 64 bytes 的 padding（4160、8256），速度就恢復正常。** padding 讓相鄰兩列的位址不再相差 2 的大冪次，各列被分散到不同的 set。
3. **為什麼慢四倍而不是模擬器的「100% miss」？** 模擬器只模擬一層 L1；真實的 CPU 在 L1 miss 之後還有很大的 L2 接住，每次 miss 只付 L2 的代價，而不是 DRAM。M4 Pro 的 block 是 128 bytes、L1 是 128 KiB；如果它是 8-way（Apple 未公開），S = 128 KiB ÷ (8 × 128) = 128，set index ＋ offset 共 14 bits，相差 4096 bytes 的列只會落在 4 個不同的 set，同樣嚴重擠壓。具體倍數依處理器而定，但「2 的大冪次 stride 造成 conflict miss」在幾乎所有 CPU 上都會出現。

`thumbd` 最後的修法是：配置影像緩衝區時，把 pitch 向上取整到 64 的倍數之後，如果結果是 4096 的倍數，就再多加 64 bytes。這只多用了不到 2% 的記憶體。第 17 章還會介紹另一種修法：改變迴圈順序，根本不要直向走訪。

### 程式三：自動分類 3C miss

這段 Python 程式用 16.7 節的方法，把每一次 miss 分成 cold、capacity、conflict：同時模擬真實的 cache 和一個同容量的 fully associative cache，對照兩者的結果。

```python
from collections import OrderedDict


class Cache:
    """S 個 set、每個 set E 條 line、block B bytes，LRU 替換。"""

    def __init__(self, sets, ways, block):
        self.sets = [OrderedDict() for _ in range(sets)]
        self.ways, self.block = ways, block

    def access(self, addr):
        blk = addr // self.block                 # block 編號 = 去掉 offset
        lines = self.sets[blk % len(self.sets)]  # set index = block 編號的低位
        if blk in lines:
            lines.move_to_end(blk)               # 更新 LRU 順序
            return True
        if len(lines) == self.ways:
            lines.popitem(last=False)            # 踢掉最久沒用的
        lines[blk] = True
        return False


def classify(trace, sets, ways, block):
    real = Cache(sets, ways, block)
    full = Cache(1, sets * ways, block)          # 同容量的 fully associative 對照組
    seen = set()
    counts = {"hit": 0, "cold": 0, "capacity": 0, "conflict": 0}
    for addr in trace:
        hit_real, hit_full = real.access(addr), full.access(addr)
        blk = addr // block
        if hit_real:
            counts["hit"] += 1
        elif blk not in seen:
            counts["cold"] += 1                  # 第一次碰到這個 block
        elif not hit_full:
            counts["capacity"] += 1              # 連 fully associative 都放不下
        else:
            counts["conflict"] += 1              # 容量夠，只是擠在同一個 set
        seen.add(blk)
    return counts


def column_walk(pitch, rows, cols=256):
    return [y * pitch + x for x in range(cols) for y in range(rows)]


L1 = dict(sets=64, ways=8, block=64)             # 32 KiB、8-way、64-byte line
for label, trace in [
    ("pitch 4000, 256 列", column_walk(4000, 256)),
    ("pitch 4096, 256 列", column_walk(4096, 256)),
    ("pitch 4000, 1024 列", column_walk(4000, 1024)),
]:
    c = classify(trace, **L1)
    print(f"{label:18} hit {c['hit']:6}  cold {c['cold']:5}  "
          f"capacity {c['capacity']:6}  conflict {c['conflict']:6}")
```

執行結果（Python 3.14，macOS arm64；結果與平台無關）：

```text
pitch 4000, 256 列  hit  64384  cold  1152  capacity      0  conflict      0
pitch 4096, 256 列  hit      0  cold  1024  capacity      0  conflict  64512
pitch 4000, 1024 列 hit      0  cold  4608  capacity 257536  conflict      0
```

三列分別是三種情況的教科書範例：

1. **pitch 4000、256 列**：只有 cold miss。working set 16 KiB 放得進 32 KiB，又分散得很均勻。
2. **pitch 4096、256 列**：除了 1,024 次 cold miss，其餘 64,512 次全是 conflict miss。fully associative 的對照組在這串位址上幾乎全部 hit，證明容量夠，錯在放置規則。修法是 padding。
3. **pitch 4000、1024 列**：沒有 conflict，卻有 257,536 次 capacity miss。一條 column 經過 1,024 個 block，共 64 KiB，超過 cache 的 32 KiB，連 fully associative 都放不下。這時加 padding 沒用，要縮小 working set，例如一次只處理 256 列的一段（第 17 章的 blocking）。

第三列還藏著 LRU 的一個弱點：hit 是 0，不是「放得下的那一半會 hit」。因為存取是循環的，LRU 每次踢掉的剛好就是下一輪最早要用的 block。當 working set 只比 cache 大一點點，循環掃描在 LRU 下可能完全沒有命中，這也是真實硬體不一定用純 LRU 的原因之一。

### Cache Lab 的思路

CS:APP 的 Cache Lab 第一部分要你用 C 寫一個 cache 模擬器：從命令列讀 s、E、b 參數，讀取 valgrind 產生的記憶體存取紀錄（每行是一次 load、store 或 modify），用 LRU 替換，最後印出 hit、miss、eviction 的次數，並和參考實作比對。第二部分要你最佳化矩陣轉置，讓它在指定的 cache 參數下 miss 盡量少。

本節的程式一已經示範了模擬器的核心資料結構（S × E 條 line，每條記錄 valid、tag、LRU 時間），但 Lab 要求的 trace 解析、命令列處理、modify 的處理方式，以及各種邊界情況，都要你自己完成。做 Lab 時的幾個提醒：

- 先用紙筆手算一個小 trace，再寫程式，最後拿程式結果和手算比對，就像本章的做法。
- 位址要用 64-bit 無號整數處理，切 tag 時用位移，不要用有號整數。
- 想清楚一次「modify」對 cache 而言是幾次存取。
- 第二部分的關鍵是 16.7 節的分析：轉置時，來源矩陣的列與目的矩陣的行常常落在同一個 set，要在手算 set index 之後再設計分塊方式。

## 16.12 在工作上怎麼用

### 查清楚 cache 的參數

```bash
# Linux
getconf -a | grep -i CACHE                                # 大小、associativity、line size
lscpu --caches                                            # 新版 util-linux 才有此選項
cat /sys/devices/system/cpu/cpu0/cache/index0/{level,type,size,ways_of_associativity,number_of_sets,coherency_line_size}

# macOS
sysctl hw.cachelinesize hw.perflevel0.l1dcachesize hw.perflevel0.l2cachesize
```

有了 C、E、B，就能算出 S、s、b 與「多少 bytes 的 stride 會撞同一個 set」：S × B 的倍數。例如 32 KiB、8-way 的 L1，S × B = 4 KiB；1 MiB、16-way、64-byte 的 L2，S = 1024，S × B = 64 KiB。

### 量測真實的 cache miss

```bash
# Linux perf：用硬體計數器量 L1 與最後一層 cache 的 miss（可用事件依 CPU 而定）
perf stat -e L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses ./thumbd_bench

# 找出是哪一行程式造成 miss
perf record -e L1-dcache-load-misses ./thumbd_bench
perf report

# Valgrind cachegrind：用軟體模擬 cache，可以在任何機器上看到每一行的 miss
# （Valgrind 3.21 起預設關閉 cache 模擬，要加 --cache-sim=yes）
valgrind --tool=cachegrind --cache-sim=yes ./thumbd_bench
cg_annotate cachegrind.out.<pid>
```

`perf` 量的是真實硬體，但可用的事件名稱和精確度依處理器而定；cachegrind 是模擬，速度慢很多，模擬的 cache 參數也和真實硬體不完全一樣，但結果穩定、可以逐行對應原始碼。兩者搭配使用：先用 `perf stat` 確認 miss 真的是問題，再用 cachegrind 或 `perf record` 找出是哪一段程式。

### 診斷「某些大小特別慢」

```text
效能只在特定輸入大小時變差（例如 4096、8192、1024×1024）
  │
  ├─ 1. 輸入大小（或 stride）是 2 的大冪次嗎？
  │
  ├─ 2. 量測：大小 N 與 N + 一點點（例如 +64 bytes）各跑一次
  │      └─ 差很多 → 高度懷疑 conflict miss
  │
  ├─ 3. 確認：perf stat 看 L1／L2 miss 是否在 N 時暴增；
  │         或用本章的模擬器、cachegrind 模擬
  │
  └─ 4. 修法
         ├─ 在 row pitch、leading dimension 加 padding（如 +64 bytes）
         ├─ 改存取順序，讓內層迴圈走 stride-1（第 17 章）
         └─ 多個大陣列同時走訪時，讓它們的起始位址錯開，不要都對齊在 2 的大冪次
```

這類問題在工作上很常見，不只是影像處理：

- **矩陣與張量**：大小是 1024、2048 的矩陣做轉置或按 column 存取。數值函式庫（BLAS、LAPACK）的 API 讓你指定 leading dimension，部分原因就是允許加 padding。
- **多個陣列對齊**：同時走訪三個各 1 MiB、都對齊在 1 MiB 邊界的陣列，`a[i]`、`b[i]`、`c[i]` 會落在同一個 set。
- **自己的資料結構**：`thumbd` 的每個 worker 有一個大小為 4096 bytes 的狀態結構，放在連續陣列裡；如果每次只讀每個結構的第一個欄位，就是 stride 4096 的存取。

### 寫入密集的程式

- 大量覆寫不會再讀的資料（例如把縮圖寫進輸出緩衝區後直接送出網路），write-allocate 會先讀一次再寫。標準函式庫的 `memcpy`、`memset` 通常已經針對大區塊處理過，優先使用它們，而不是自己寫逐 byte 的迴圈。
- 多個 thread 頻繁寫入的計數器，不要放在同一個 64 bytes（或 128 bytes）的 block 裡，否則一致性協定會讓 block 在核心間來回搬（第 32 章）。

## 16.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 特定大小（2048、4096、8192…）的輸入特別慢 | stride 是 S × B 的倍數，所有存取擠進少數幾個 set，造成 conflict miss | 大小 N 與 N + 64 bytes 比較；`perf stat` 看 L1 miss；用模擬器重現 | pitch 或陣列大小加 padding；改存取順序 |
| 資料量稍微變大，效能突然掉很多 | working set 跨過某一層 cache 容量，capacity miss 暴增；循環掃描在 LRU 下尤其嚴重 | 逐步增加資料量量測，找出斷崖位置，對照 cache 大小 | 分塊處理，讓每一塊放得進 cache（第 17 章） |
| 手算 set index 和模擬器對不上 | 把 tag、index 的位元順序弄反；用了高位當 index；忘了先去掉 offset | 把位址寫成二進位，逐段標出 t、s、b | 依「offset 在最低、index 在中間、tag 在最高」重新切 |
| 程式在 x86-64 很好，在 Apple Silicon 上 false sharing 變嚴重 | 程式假設 cache line 是 64 bytes，但 Apple Silicon 是 128 bytes | `sysctl hw.cachelinesize`；C++ 可查 `std::hardware_destructive_interference_size` | 不要寫死 64，執行時查詢或依平台定義 |
| 寫入大量資料比讀取同樣資料慢很多 | write-allocate 讓每次 store miss 先讀入 block，再加上 dirty block 被踢出時要寫回，流量變成兩到三倍 | `perf stat` 觀察記憶體流量；比較用 `memset` 與手寫迴圈的差異 | 使用最佳化過的 `memcpy`／`memset`；避免不必要的覆寫 |
| 用 `perf stat` 看到 LLC miss rate 很高就以為有問題 | 下層 cache 的 local miss rate 本來就高，容易命中的早被 L1、L2 處理掉 | 看絕對的 miss 次數與總 cycles，而不只是比例 | 以總時間與 AMAT 判斷，而不是單看某層的 miss rate |

## 16.14 動手練習

1. **手算**：一個 L1 data cache 為 64 KiB、4-way、64-byte block，位址 48 bits。算出 S、s、b、t，並把位址 `0x7f00ab12c4d8` 切成 tag、set index、offset。（答案：S = 256，s = 8，b = 6，t = 34；offset = 0x18，set index = 19，tag = 0x1fc02ac4b。驗證方法：用 Python 計算 `a & 63`、`(a >> 6) & 255`、`a >> 14`。）
2. **手算**：沿用 16.4 節的 direct-mapped 迷你 cache（m = 8、B = 8、S = 4、E = 1），模擬位址序列 `0x08, 0x10, 0x48, 0x08, 0x50, 0x10`，標出每次是 hit 或 miss，並分類 miss。再換成 fully associative（S = 1、E = 4）重做一次。（驗證方法：把序列放進程式一的 `trace` 陣列，並新增一個 `cache_new(0, 4, 3)`。）
3. **延伸程式一**：在模擬器的第二部分，把 pitch 改成 4096 + 64、8192、2048，以及 associativity 改成 16，觀察 miss rate 的變化。找出「在 8-way 下，pitch 4096 時最多能有幾列而不發生 conflict miss」，並解釋。
4. **延伸程式一**：在模擬器中加入寫入：把直向走訪改成「讀 `img[y][x]`，寫 `out[x][y]`」（轉置），印出 `writebacks` 的數量。比較 write-back 與「假設是 write-through」時下一層的寫入次數差多少。
5. **延伸程式三**：設計一個存取序列，讓 2-way 的 cache 出現 conflict miss，但 4-way 的 cache 完全沒有 conflict miss（容量相同）。用程式三確認你的答案。
6. **工作練習**：在 Linux 機器上，用 `getconf -a | grep CACHE` 查出 L1、L2 的參數，算出各自的 S × B（多少 bytes 的 stride 會撞同一個 set）。修改程式二，把 pitch 換成你算出的數字與它的倍數，看看是否觀察到同樣的慢化。

## 本章重點整理

- 任何 CPU cache 都可以用 S（set 數）、E（每 set 的 line 數）、B（block 大小）、m（位址位元數）描述，容量 C = S × E × B，不含 valid bit 與 tag。
- 位址被切成三段：最低 b = log2(B) 位是 block offset，中間 s = log2(S) 位是 set index，剩下的 t = m − s − b 位是 tag。
- 查找時先用 set index 直接選出 set，再在 set 內平行比對 E 個 tag，最後用 offset 取出資料；比對成功且 valid 才是 hit。
- set index 取中間的 bits，是為了讓連續的 block 平均分散到不同的 set，充分利用整個 cache。
- direct-mapped（E = 1）最簡單但最容易 conflict miss；set associative 以 E 條 line 減少衝突；fully associative（S = 1）沒有 conflict miss，但只適合很小的 cache 或用軟體查表的虛擬記憶體。
- miss 分為 cold、conflict、capacity 三類；用「同容量的 fully associative cache 是否也會 miss」可以區分 capacity 與 conflict。
- 相差 S × B 整數倍的位址一定落在同一個 set；2 的大冪次的 stride（例如影像寬度 4096）會造成嚴重的 conflict miss，加一點 padding 就能修好。
- write-through 每次寫都更新下一層；write-back 只在踢出 dirty line 時寫回；write-allocate 在 write miss 時先載入 block，現代 CPU 普遍採用 write-back ＋ write-allocate。
- 多核心以 MESI 這類一致性協定維持 cache 一致，以 block 為單位追蹤，因此會出現 false sharing。
- 真實處理器有分開的 L1 i-cache 與 d-cache、每核心的 L2 與共用的 L3；block 在 x86-64 上通常是 64 bytes，在 Apple Silicon 上是 128 bytes。
- L1 常用 VIPT 設計，要求 C ÷ E 不超過 page 大小，這解釋了 x86-64 的 L1 為什麼長期是「4 KiB × way 數」。
- 多層 cache 的 AMAT 可以逐層展開；下層 cache 的 local miss rate 高是正常的，要看它攔下了多少原本要到 DRAM 的存取。
- cache 參數之間沒有「越大越好」，容量、block 大小、associativity 各自在 hit time、miss rate、miss penalty 之間取捨。
- 用 `getconf`／`sysctl` 查參數，用 `perf stat` 量真實 miss，用 cachegrind 或自己的模擬器逐行分析，是工作上處理 cache 問題的基本流程。

## 延伸問答

> [!question]- Q1. 手算題：一個 cache 有 C = 2 MiB、16-way、64-byte block，位址 48 bits。S、s、b、t 各是多少？相差多少 bytes 的位址一定落在同一個 set？
> S = C ÷ (E × B) = 2,097,152 ÷ (16 × 64) = 2,048，所以 s = log2(2048) = 11；b = log2(64) = 6；t = 48 − 11 − 6 = 31。
>
> set index 與 offset 合起來佔最低 17 bits，所以任何兩個相差 2^17 = 128 KiB 整數倍的位址，最低 17 bits 相同，必定落在同一個 set。這個數字也等於 S × B = 2,048 × 64 bytes。在這個 cache 中，stride 為 128 KiB（或其倍數）的存取最多只能有 16 個 block 同時共存，超過就會 conflict miss。

> [!question]- Q2. 為什麼 set index 要用位址中間的 bits，而不是最高的 bits？
> 因為程式最常見的存取是連續的，而連續的位址只在低位不同，高位幾乎都一樣。如果用高位當 set index，掃描一個陣列時所有 block 都會落在同一個 set，其他 set 完全閒置，cache 實際上只剩一個 set 的容量，conflict miss 會非常多。
>
> 用 offset 正上方的中間 bits 當 index，相鄰的 block 會輪流落在不同的 set，一段大小剛好為 C 的連續資料可以平均填滿整個 cache。tag 放在最高位則剛好合理：同一個 set 裡的不同 block，差別就在高位。

> [!question]- Q3. 你在 production 發現 `thumbd` 處理 2048 × 2048 的圖片時，旋轉 90 度比 2000 × 2000 的圖片慢了三倍多，像素數只差 5%。你會怎麼分析？
> 第一步先懷疑 2 的冪次造成的 conflict miss。旋轉 90 度需要讀一個方向、寫另一個方向，其中一邊必然是直向（按 column）走訪。以 32 KiB、8-way 的 L1（S × B = 4 KiB）來說，寬度 2048 的灰階影像每列相差 2048 bytes，每兩列就回到同一個 set，直向走訪只用到 2 個 set；RGBA 影像每列相差 8192 bytes，是 4 KiB 的倍數，每一列都落在同一個 set。
>
> 驗證方法：用 2048 寬但 pitch 加 64 bytes 的緩衝區重跑，如果速度回到正常，就確認了；也可以用 `perf stat -e L1-dcache-load-misses` 比較兩種大小，或用 cachegrind、本章的模擬器重現。修法是配置緩衝區時避開 2 的大冪次的 pitch，以及用分塊的方式做旋轉，讓每一塊的來源與目的都放得進 cache（第 17 章）。

> [!question]- Q4. Direct-mapped cache 的 miss 一定比同容量的 4-way cache 多嗎？
> 不一定，但大多數情況是。4-way 的放置更有彈性，通常能消除 direct-mapped 中的 conflict miss。然而 4-way 用 LRU 替換時，可能遇到 LRU 的病態情況：例如循環存取 5 個落在同一 set 的 block，4-way LRU 每次都踢掉下一個要用的 block，結果每次都 miss。
>
> 而 direct-mapped 下，這 5 個 block 可能分散在不同的 set（因為兩種組織的 set 數不同，set index 的位元也不同），反而有部分能 hit。所以 associativity 高是「統計上」較好，不是對每一個存取序列都較好。這也提醒我們：評估 cache 設計要用代表性的工作負載量測，而不是只靠直覺。

> [!question]- Q5. 面試題：說明 write-back 與 write-through 的差別，以及為什麼 write-back 通常搭配 write-allocate？
> write-through 在每次寫 cache 時同時寫下一層，下一層永遠是最新的，實作簡單，但每次寫入都產生流量；write-back 只改 cache 並設定 dirty bit，等到這條 line 被踢出時才把整個 block 寫回，同一個 block 被反覆寫只會寫回一次，流量小很多。
>
> write-back 搭配 write-allocate 是因為兩者賭的是同一件事：寫入有 locality。write-allocate 在 write miss 時把 block 載入 cache，之後對同一 block 的讀寫都在 cache 中完成；write-back 再讓這些寫入累積起來一次寫回。如果 write-back 搭配 no-write-allocate，write miss 會直接寫到下一層，之後的寫入仍然 miss，就失去了 write-back 的好處。

> [!question]- Q6. 為什麼 x86-64 處理器的 L1 data cache 長期是 32 KiB、8-way，而變大時（48 KiB）associativity 也跟著變成 12-way？
> 因為 L1 常採用 VIPT（virtually indexed, physically tagged）設計：用虛擬位址的 set index 選 set，同時讓 TLB 轉譯出實體位址來比對 tag，兩件事平行進行以縮短 hit time。這要求 set index 與 offset 完全落在 page offset 之內，因為只有 page offset 在轉譯前後保持不變。
>
> page 是 4 KiB，所以 S × B 不能超過 4 KiB，也就是 C ÷ E ≤ 4 KiB。32 KiB ÷ 8 = 4 KiB，48 KiB ÷ 12 = 4 KiB，都剛好滿足。要加大 L1 又不放棄 VIPT，就只能提高 associativity。Apple Silicon 使用 16 KiB page，同樣的限制放寬了四倍，這是它能有較大 L1 的原因之一。

> [!question]- Q7. 程式找錯：下面的結構陣列被 8 個 thread 各自更新自己的計數器，加了 thread 之後總吞吐量反而下降。`struct counter { long hits; long misses; }; struct counter stats[8];` 問題在哪？
> 每個 `struct counter` 只有 16 bytes，8 個 thread 的計數器合計 128 bytes，在 x86-64（64-byte block）上擠在 2 個 block 裡，在 Apple Silicon（128-byte block）上甚至全部在同一個 block。雖然每個 thread 只寫自己的計數器，但 cache coherence 以 block 為單位：一個核心要寫，就得讓其他核心的副本失效，block 在核心之間不斷來回搬，這就是 false sharing。
>
> 修法是讓每個 thread 的計數器各自佔滿一個 block，例如用 `_Alignas(128)` 對齊並填充到 block 大小（要考慮不同平台的 block 大小），或讓每個 thread 先累加在自己的 local 變數，最後再合併。第 32 章會用實驗量測這個效應。

> [!question]- Q8. 16.11 節的程式三中，pitch 4000、1024 列時 hit 是 0。容量 32 KiB 能放下 512 個 block，為什麼不是「一半 hit、一半 miss」？
> 因為存取是循環的，而 LRU 剛好在這種模式下表現最差。一條 column 經過 1,024 個 block，cache 只能保留最近用過的 512 個。走到下一個 column 時，第一個要用的是第 0 列的 block，但它正好是最久以前用的那個，早已被 LRU 踢掉；載入它又會踢掉第 1 列的 block，而第 1 列正是下一個要用的。如此連鎖，每一次都 miss。
>
> 這是 working set 稍大於 cache 時的典型病態：命中率不是線性下降，而是直接掉到接近零。真實硬體常用近似 LRU 或帶有隨機性、能偵測掃描模式的替換策略，部分緩解這個問題。對寫程式的人，解法是縮小 working set：例如一次只處理 256 列的一段，讓它完全放得進 cache，這就是第 17 章的 blocking。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 6 章 6.4 節，cache 組織與運作的完整說明。
- [CS:APP 3e Lab Assignments](https://csapp.cs.cmu.edu/3e/labs.html)：Cache Lab 的說明文件與講義，可以下載 handout 自己實作模擬器。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：Cache Memories 一講的投影片與錄影。
- [Intel 64 and IA-32 Architectures Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)：快取組織、記憶體類型與 non-temporal 指令的官方規格。
- [Linux man pages](https://man7.org/linux/man-pages/)：`perf-stat(1)`、`getconf(1)` 與 `sysconf(3)` 中關於 cache 參數的說明。
