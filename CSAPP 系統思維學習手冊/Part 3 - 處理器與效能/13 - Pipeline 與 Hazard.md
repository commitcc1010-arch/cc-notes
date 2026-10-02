---
chapter: 13
title: Pipeline 與 Hazard
part: 3
---

# 第 13 章　Pipeline：Hazard、Forwarding 與分支預測

> [!abstract] 本章地圖
> **核心問題**：處理器怎麼讓好幾條指令同時「在路上」，把每秒完成的指令數提高好幾倍，又讓程式看起來像是一條一條依序執行？代價會在什麼時候浮上檯面？
>
> **你會學到**：
> - 分清楚 throughput 與 latency，手算 pipeline 切成幾段、每段多長時，時脈與吞吐量各是多少
> - 畫出指令在五階段 pipeline 中的時序圖，指出 data hazard、load-use hazard 與 control hazard 在哪一個 cycle 發生、要付幾個 cycle
> - 解釋 forwarding、stall、bubble、flush 各自做什麼，以及 pipeline 如何維持 precise exception
> - 用 CPI 公式估算 hazard 對效能的影響，並說明現代 out-of-order、superscalar 處理器為何讓分支預測錯誤更貴
> - 用實驗量到分支預測錯誤的代價，並說明 Spectre 與 Meltdown 為什麼和推測執行有關
>
> **前置知識**：第 8 章（條件碼與條件跳躍、conditional move）、第 12 章（Y86-64 與循序處理器的六個階段）
>
> **對應 CS:APP 3e**：第 4 章 4.4–4.5 節（並補充 4.6 節的現代處理器概念）

## 13.1 故事：測試圖很快，真實圖很慢

拾光相簿上線了「浮水印貼紙」功能：使用者可以在照片上疊一張半透明的貼紙。`thumbd` 合成貼紙前，會先掃過貼紙的 alpha 通道（每個像素的不透明度，0 是全透明、255 是全不透明），把「夠不透明」（alpha 至少 128）的像素索引收集起來，後面只處理這些像素。

小安寫完這段程式，在 CI 上用測試貼紙跑 benchmark：一張 1024×1024 的貼紙，掃描只要 0.27 ms 左右，大約每個像素 0.25 ns。上線一週後，SRE 阿哲在 dashboard 上發現貼紙合成的 p99 延遲比預期高了好幾倍。小安把 production 的一張使用者貼紙抓下來重跑，同一段程式、同樣大小，卻要約 3 ms，慢了十倍以上。

小安先懷疑是 cache miss，可是兩張圖一樣大，存取順序也完全一樣，都是從頭掃到尾。再懷疑是不透明像素比較多、寫入比較多，但數了一下，兩邊的寫入次數差不到兩倍。老周看了一眼那張使用者貼紙，說：「這張是手繪的，邊緣有大量抗鋸齒，alpha 值忽高忽低。你的 `if (alpha[i] >= 128)` 在 CPU 眼裡變成一枚每次都要猜的硬幣。測試圖全部是 255，CPU 每次都猜對。」

「CPU 在猜？」小安不解。程式明明是一行一行執行的，為什麼要猜？這就是本章的主題。現代 CPU 不是做完一條指令才開始下一條，而是像工廠生產線一樣，讓許多條指令同時處在不同的加工階段。生產線要一直有東西可做才快，所以遇到「下一條要執行哪裡還不知道」的分支時，CPU 只能先猜一個方向繼續做；猜錯了，就得把已經做了一半的工作全部丟掉。理解這條生產線的運作方式，才能解釋為什麼「同樣的指令、同樣的資料量」可以差十倍。

## 13.2 Pipelining 的原理：throughput 與 latency

第 12 章的循序處理器（SEQ）在一個 clock cycle 裡完成一整條指令：fetch、decode、execute、memory、write back、PC update 全部是一大塊組合電路，訊號從頭流到尾，最後在 clock 上升時一起寫進暫存器。這個設計很好懂，但有個根本問題：clock cycle 必須長到讓最慢的指令走完全部電路，而在這段時間裡，負責 fetch 的電路在訊號流過之後就閒著，等著下一個 cycle。

**Pipelining**（管線化）的想法和洗衣店一樣：洗衣機、烘衣機、摺衣台是三個階段，第一批衣服進烘衣機的同時，第二批就可以開始洗。每一批衣服從進門到摺好的時間沒有變短，但每小時可以處理的批數變多了。套到處理器上，就是把一條指令的處理切成幾段，段與段之間放一排暫存器，讓不同的指令同時處在不同的段。

這裡有兩個一定要分清楚的量：

- **Latency**（延遲）：一條指令從開始到完成要多久。例如一條指令要走完五個階段，每階段 1 ns，latency 就是 5 ns。
- **Throughput**（吞吐量）：單位時間完成多少條指令。單位常用 GIPS（每秒十億條指令）。同一個例子，pipeline 填滿之後每 1 ns 就完成一條，throughput 是 1 GIPS。

Pipelining 提高的是 throughput，不是 latency。事實上它會讓 latency 稍微變長，因為每多切一段就多一排暫存器，訊號要多花時間寫進去。

```text
 沒有 pipeline：一條做完才做下一條（每條 500 ps）
 時間(ps)  0        500       1000      1500
 指令 1    [██ 組合邏輯 ██][R]
 指令 2                        [██ 組合邏輯 ██][R]
 指令 3                                            [██ ...

 四段 pipeline：每段 120 ps 邏輯 + 20 ps 暫存器 = 140 ps
 時間(ps)  0    140  280  420  560  700  840
 指令 1    [ S1 ][ S2 ][ S3 ][ S4 ]
 指令 2          [ S1 ][ S2 ][ S3 ][ S4 ]
 指令 3                [ S1 ][ S2 ][ S3 ][ S4 ]
 指令 4                      [ S1 ][ S2 ][ S3 ][ S4 ]
           每 140 ps 完成一條；但每條本身要 560 ps
```

上面的圖用了一個具體的數字：整條指令的組合邏輯需要 480 ps，每排暫存器的寫入時間（加上時脈偏差等開銷）是 20 ps。沒有 pipeline 時，一個 cycle 是 480 + 20 = 500 ps。切成四段平均的 pipeline 後，每段只有 120 ps 邏輯，加上自己那排暫存器，cycle 變成 140 ps。指令 1 要走完四段，latency 是 4 × 140 = 560 ps，比原本的 500 ps 還慢；但從第四個 cycle 開始，每 140 ps 就有一條指令完成。

### 手算：切成幾段、怎麼切

把各種切法列成表，每一欄都可以自己驗算：cycle 時間取「最慢那一段的邏輯 + 20 ps」，throughput 是 1 ÷ cycle 時間，latency 是段數 × cycle 時間。

| 設計 | 各段邏輯（ps） | cycle（ps） | throughput（GIPS） | latency（ps） | 暫存器開銷佔 cycle |
|---|---|---|---|---|---|
| 不切 | 480 | 500 | 2.00 | 500 | 4% |
| 4 段，平均 | 120 × 4 | 140 | 7.14 | 560 | 14% |
| 4 段，不平均 | 80、160、120、120 | 180 | 5.56 | 720 | 11% |
| 8 段，平均 | 60 × 8 | 80 | 12.50 | 640 | 25% |
| 16 段，平均 | 30 × 16 | 50 | 20.00 | 800 | 40% |

從這張表可以讀出 pipeline 設計的兩個基本限制：

**第一，段與段要平衡。** 「4 段，不平均」那一列裡，最慢的一段 160 ps 決定了整條 pipeline 的節奏，其他三段每個 cycle 都有一部分時間在等。同樣是四段，throughput 從 7.14 掉到 5.56 GIPS。實際的硬體很難完美平衡，例如記憶體存取本來就比加法慢，這就是設計者要煩惱的地方。

**第二，切越細，回報越小。** 從 8 段到 16 段，段數加倍，throughput 只從 12.5 提高到 20 GIPS，而不是 25 GIPS，因為那固定的 20 ps 暫存器開銷佔 cycle 的比例越來越高。更麻煩的是，後面幾節會看到，pipeline 越深，遇到 hazard 時要丟掉或等待的 cycle 越多。2000 年代初期 Intel 的 Pentium 4 把 pipeline 做到二十段以上、追求極高時脈，最後因為功耗與分支預測錯誤的代價太高而回頭。今天的高效能核心大多落在十多段的量級，依微架構而定。

> [!warning] 常見誤解
> 「pipeline 讓每條指令變快。」不是。單一指令的 latency 不變甚至變長，變快的是「每秒完成幾條」。這個區別在第 14 章會變得非常重要：如果下一條指令要等上一條的結果，throughput 再高也幫不上忙，速度會被 latency 綁住。

## 13.3 從 SEQ 到 PIPE：階段暫存器

CS:APP 把 Y86-64 的循序處理器改造成一個五階段 pipeline，叫 **PIPE**。五個階段幾乎就是第 12 章的六個階段，只是把 PC update 搬到最前面，變成 fetch 的一部分：

| 階段 | 縮寫 | 做什麼 | 對應第 12 章 |
|---|---|---|---|
| Fetch | F | 依 PC 讀出指令位元組，算出（或預測）下一個 PC | fetch ＋ PC update |
| Decode | D | 解析暫存器編號，從 register file 讀出運算元 | decode |
| Execute | E | ALU 計算、算出記憶體位址、判斷條件跳躍是否成立 | execute |
| Memory | M | 需要時讀寫資料記憶體 | memory |
| Write back | W | 把結果寫回 register file | write back |

各階段之間的那排暫存器叫 **pipeline register**（階段暫存器）。CS:APP 用它「後面那個階段」的名字稱呼它：F 暫存器放在 fetch 前面，存預測的 PC；D 暫存器放在 fetch 與 decode 之間，存剛抓到的指令；依此類推。

```text
           ┌───┐        ┌───┐        ┌───┐        ┌───┐        ┌───┐
 predPC ─▶ │ F │─Fetch─▶│ D │─Decode▶│ E │─Exec──▶│ M │─Memory▶│ W │─Write back─┐
           └───┘        └───┘        └───┘        └───┘        └───┘            │
             ▲          icode       icode        icode         icode            │
             │          ifun        ifun         Cnd           valE             │
             │          rA, rB      valC         valE          valM             │
             │          valC        valA, valB   valA          dstE, dstM       │
             │          valP        dstE, dstM   dstE, dstM    stat             │
             │          stat        srcA, srcB   stat                           │
             │                      stat                                        │
             └──────────────── 下一個 PC：預測值、或從後段修正 ◀──────────────────┘
                                          register file ◀───────────────────────┘
```

每個 cycle 結束時，每排暫存器把前一段算好的結果鎖住，交給下一段用。所以一條指令往右走，它需要的所有資訊（是什麼指令、要寫哪個暫存器、算出了什麼值、目前狀態正不正常）都跟著它一起走。這一點很重要：同一個 cycle 裡，五排暫存器裝的是五條**不同**指令的資訊。D 暫存器裡的 `dstE` 和 W 暫存器裡的 `dstE` 是兩條指令各自的目的暫存器。

把 PC update 搬到最前面有一個理由：pipeline 要在每個 cycle 都抓一條新指令，所以 fetch 必須在一個 cycle 內決定「下一條在哪裡」。對大多數指令這很容易，下一條就在 `valP`（目前 PC 加上指令長度）。真正麻煩的是條件跳躍和 `ret`：條件跳躍要到 execute 才知道跳不跳，`ret` 要到 memory 讀出 return address 才知道去哪。fetch 不能等，所以只能**預測**。這是 13.7 節的主題。

在理想狀態下，每個 cycle 都有一條指令進入 F、一條指令離開 W，五個階段永遠滿載，處理器每個 cycle 完成一條指令。現實中，有三類情況會打斷這個節奏，統稱 **hazard**（冒險、危障）：

| 類型 | 白話 | Y86-64 例子 | 基本對策 |
|---|---|---|---|
| Data hazard | 要用的值還沒算好或還沒寫回 | `addq %rdx,%rax` 緊跟在寫 `%rdx` 的指令後面 | forwarding；不行就 stall |
| Control hazard | 不知道下一條指令在哪裡 | 條件跳躍、`ret` | 預測；猜錯就 flush |
| Structural hazard | 兩條指令同時要用同一個硬體 | 指令與資料共用一個記憶體埠 | 加硬體（分開的指令／資料 cache）或讓其中一條等 |

PIPE 的設計刻意分開指令記憶體與資料記憶體，也讓 register file 有兩個讀取埠與兩個寫入埠，所以不會有 structural hazard。接下來三節依序處理 data hazard 與 control hazard。

## 13.4 Data hazard：要用的值還沒準備好

看這三條 Y86-64 指令：

```text
irmovq $10, %rdx      # 指令 1：%rdx = 10
irmovq $3,  %rax      # 指令 2：%rax = 3
addq   %rdx, %rax     # 指令 3：%rax = %rax + %rdx
```

指令 3 在 decode 階段要讀 `%rdx` 與 `%rax`。可是在 pipeline 裡，指令 3 進入 decode 的時候，指令 2 才剛進 execute、指令 1 才剛進 memory，兩者都還沒到 write back，register file 裡的 `%rdx` 和 `%rax` 還是舊值。如果什麼都不做，指令 3 會讀到錯誤的資料，算出錯誤的結果。這就是 **data hazard**（資料冒險）：後面的指令要讀某個暫存器，而前面某條「還在路上」的指令正要寫它。

這種「先寫後讀」的依賴叫 **RAW**（read after write）。在像 PIPE 這樣依序執行的 pipeline 中，只有 RAW 會造成問題。「先讀後寫」（WAR）與「寫後再寫」（WAW）在依序 pipeline 裡不會出錯，因為讀永遠發生在 decode、寫永遠發生在 write back，前面的指令一定比後面的指令先完成每一個階段。13.10 節會看到，亂序執行的處理器就必須額外處理這兩種情況。

### 最簡單的解法：stall

最直接的辦法是讓指令 3 在 decode 等著，直到它要的值寫進 register file。在 PIPE 裡，write back 在 cycle 結束時才把值寫進去，所以消費者最早要在生產者 write back 的**下一個** cycle 才能在 decode 讀到正確值。用時序圖來看（這張圖是 13.12 節的模擬器輸出）：

```text
                        1  2  3  4  5  6  7  8  9 10 11
irmovq $10,%rdx         F  D  E  M  W
irmovq $3,%rax             F  D  E  M  W
addq %rdx,%rax                F  s  s  s  D  E  M  W
halt                             F  F  F  F  D  E  M  W
```

指令 2 在 cycle 6 做 write back，所以指令 3 最早在 cycle 7 才能完成 decode。它在 cycle 4、5、6 卡在 decode 階段（圖中的 `s`），後面的 `halt` 也只能跟著卡在 fetch。這種「讓指令停在原地」的動作叫 **stall**（停頓）。

停住的同時，execute 階段在 cycle 5、6、7 本來應該有指令進來，現在沒有，硬體就往 E 暫存器塞一個「什麼都不做」的假指令，叫 **bubble**（氣泡）。bubble 像一個自動生成的 `nop`，會一路流到 write back，但不改變任何暫存器、記憶體或條件碼。所以 stall 和 bubble 是同一件事的兩面：

- **stall**：讓某排 pipeline register 在下一個 cycle **保持原值**，裡面的指令留在原階段。
- **bubble**：讓某排 pipeline register 在下一個 cycle 被設成 `nop`，往下游送出一個空位。

處理 data hazard 時，PIPE 同時 stall F 與 D 兩排暫存器，並往 E 注入 bubble。這樣前面的生產者繼續往前走，後面的消費者在原地等。

這個方法正確，但很貴：相鄰的兩條指令只要有依賴，就要損失三個 cycle。而真實程式裡，相鄰指令互相依賴是常態，例如 `sum += a[i]` 的每一次加法都依賴上一次的結果。如果每次都等三個 cycle，pipeline 的好處就幾乎沒了。

## 13.5 Forwarding：不等寫回，直接抄近路

仔細看上面那張圖：指令 2 的結果 `%rax = 3` 其實在 cycle 4 結束時就算好了，它在 execute 階段的 ALU 輸出端，只是還要再走 memory、write back 兩段才寫進 register file。指令 3 在 cycle 4 正在 decode，如果有一條線直接把 ALU 的輸出拉到 decode 階段，指令 3 根本不用等。

這條「近路」叫 **forwarding**（轉送），也叫 **bypassing**（旁路）。PIPE 在 decode 階段的運算元輸入端放了多工器，可以從五個地方挑選來源：

```text
                    ┌──────────────────────────────────────────────┐
                    │  decode 階段：要讀 srcA／srcB                  │
                    │                                              │
  register file ───▶│ ─┐                                           │
                    │  │  多工器：依序檢查                             │
  e_valE  (E 段 ALU 輸出，最新) ───────────▶ ① 這條在 E 的指令要寫 srcA？
  m_valM  (M 段剛讀出的記憶體資料) ────────▶ ② 這條在 M 的 load 要寫 srcA？
  M_valE  (M 暫存器裡的 ALU 結果) ─────────▶ ③
  W_valM  (W 暫存器裡的 load 結果) ────────▶ ④
  W_valE  (W 暫存器裡的 ALU 結果，最舊) ───▶ ⑤
                    │  都不是 → 用 register file 讀出的值            │
                    └──────────────────────────────────────────────┘
```

控制邏輯比較目前 decode 要讀的暫存器編號（`srcA`、`srcB`）和後面每一段指令要寫的暫存器編號（`dstE`、`dstM`）。只要有相符，就直接拿那一段的值，不必等它寫回。

檢查的**順序**有意義：如果 E 段和 M 段的指令都要寫 `%rax`，E 段那條是比較新的指令，程式語意上它的值才是 decode 這條指令應該看到的，所以必須優先取 E 段的值。這相當於「同一個變數被連續賦值兩次，後面讀到的是最後一次的值」，硬體必須保證這個語意。

有了 forwarding，同樣三條指令的時序變成：

```text
                        1  2  3  4  5  6  7  8
irmovq $10,%rdx         F  D  E  M  W
irmovq $3,%rax             F  D  E  M  W
addq %rdx,%rax                F  D  E  M  W
halt                             F  D  E  M  W
```

cycle 4 時，指令 3 在 decode，`%rax` 從 E 段的 `e_valE` 拿、`%rdx` 從 M 段的 `M_valE` 拿，完全不用停。從 11 個 cycle 降到 8 個 cycle，pipeline 又回到每個 cycle 完成一條指令的理想狀態。

forwarding 的硬體成本是額外的線路與多工器，而且多工器本身在關鍵路徑上，會拉長 decode 階段的時間。這是設計上的取捨，但幾乎所有 pipeline 處理器都會這樣做，因為不做的代價太大。

## 13.6 Load-use hazard：forwarding 也救不了的情況

Forwarding 能解決 ALU 結果的依賴，是因為 ALU 在 execute 階段就算完了。但從記憶體讀資料的指令（Y86-64 的 `mrmovq` 與 `popq`）要到 **memory 階段結束**才拿到資料。如果下一條指令立刻要用這個值：

```text
mrmovq 0(%rdi), %rax   # 從記憶體讀到 %rax
addq   %rax, %rbx      # 馬上用 %rax
```

`addq` 在 cycle 3 進入 decode 時，`mrmovq` 才剛進 execute，正在計算位址，資料要到 cycle 4 結束才從記憶體出來。時間不能倒流，資料還沒存在的時候，沒有任何線路能把它送過去。這種情況叫 **load-use hazard**（載入使用冒險）。

PIPE 的對策是 stall 一個 cycle：

```text
                        1  2  3  4  5  6  7  8
mrmovq 0(%rdi),%rax     F  D  E  M  W
addq %rax,%rbx             F  s  D  E  M  W
halt                          F  F  D  E  M  W
```

cycle 3 時控制邏輯發現「E 段是 load，而且它的目的暫存器正是 decode 要讀的暫存器」，於是讓 `addq` 在 decode 多待一個 cycle、往 E 注入一個 bubble。到了 cycle 4，`mrmovq` 在 memory 階段讀出資料，`addq` 就能透過 `m_valM` forwarding 拿到它。整體只損失一個 cycle，這個技巧叫 **load interlock**（載入互鎖）。

CS:APP 用一個條件寫出 load-use 的偵測：E 段是 `mrmovq` 或 `popq`，而且 `E_dstM` 等於 decode 正要讀的 `srcA` 或 `srcB`。這只是一行邏輯，但它把「哪一排 stall、哪一排塞 bubble」完全決定了。

這個一個 cycle 的代價看似很小，但它告訴你一件影響深遠的事：**讀記憶體的結果，比算術的結果晚到**。真實處理器上，L1 cache 命中的 load 大約要 4–5 個 cycle 才拿到資料（依微架構而定），cache miss 更是數十到數百個 cycle（第 15、16 章）。編譯器因此會做 **instruction scheduling**（指令排程）：盡量把 load 往前移，在 load 和使用之間塞進其他不相關的指令，讓等待的時間被有用的工作填滿。亂序執行的處理器（13.10 節）則是在硬體裡自動做這件事。

> [!tip] 怎麼判斷一個依賴要等多久
> 不要背「哪兩種指令會 stall」，而是每次都問三個問題：生產者在哪個階段**最早**產生結果？消費者在哪個階段**最晚**需要它？中間有沒有 forwarding 線路？兩者的時間差就是要等的 cycle 數。這個思考方式在第 14 章分析迴圈效能時會再用到。

## 13.7 Control hazard 與分支預測

Data hazard 是「值還沒到」，**control hazard**（控制冒險）則是「不知道下一條指令在哪裡」。Fetch 階段每個 cycle 都要抓一條新指令，但遇到條件跳躍時，要不要跳得等到 execute 階段檢查條件碼才知道；遇到 `ret` 時，回去的位址要到 memory 階段從 stack 讀出來才知道。

### PIPE 怎麼處理條件跳躍

PIPE 的策略是**永遠預測會跳**（always taken），fetch 直接從跳躍目標開始抓。如果猜錯了，就要等到條件跳躍進入 execute 才會發現。那時候，pipeline 裡已經有兩條「錯誤路徑」上的指令：一條在 decode、一條在 fetch。

```text
                        1  2  3  4  5  6  7  8  9 10
andq %rax,%rax          F  D  E  M  W
jne done (mispredict)      F  D  E  M  W
  (wrong path #1)             F  D  x
  (wrong path #2)                F  x
irmovq $1,%rcx                      F  D  E  M  W
halt                                   F  D  E  M  W
```

cycle 4 時，`jne` 在 execute 判斷出「其實不跳」。這時兩條錯誤路徑的指令還沒走到 execute，所以還沒改變任何條件碼、暫存器或記憶體。控制邏輯在下一個 cycle 把它們換成 bubble（圖中的 `x`），叫做 **flush**（沖掉），同時讓 fetch 改從正確的位址（跳躍指令的下一條，`valP` 已經跟著 `jne` 流到 M 暫存器的 `valA` 欄位）開始抓。損失兩個 cycle，這叫 **branch misprediction penalty**（分支預測錯誤懲罰）。

`ret` 更麻煩：PIPE 不嘗試預測 return address，而是讓 fetch 停住，直到 `ret` 走到 write back 階段、從 stack 讀出的位址可以使用時才繼續，損失三個 cycle。

這裡有一個關鍵的安全網：**錯誤路徑上的指令永遠不能留下程式看得到的痕跡**。PIPE 能做到，是因為條件跳躍在 execute 就決定了，錯誤路徑的指令最遠只走到 decode，還沒有任何階段會寫入狀態。更深的 pipeline 裡，錯誤路徑可能已經走了十幾個階段，就必須有更完整的機制（13.10 節的 reorder buffer）保證它們不會提交。

### 預測策略：從固定規則到學習歷史

「永遠猜跳」在迴圈裡還算有效，因為迴圈的條件跳躍大部分時間都會跳回去。但對 `if` 來說就像丟硬幣。真實處理器的預測器會**記住過去的行為**。最經典的入門設計是 **2-bit saturating counter**（兩位元飽和計數器）：每個分支有一個 0 到 3 的計數器，跳了就加一（最多 3），沒跳就減一（最少 0），計數器 ≥ 2 就預測會跳。

```text
  N 時停在 0                                         T 時停在 3
   ┌──┐                                               ┌──┐
   │  ▼     T            T            T               ▼  │
 ┌────────┐ ───▶ ┌────────┐ ───▶ ┌────────┐ ───▶ ┌────────┐
 │ 0 猜 N │      │ 1 猜 N │      │ 2 猜 T │      │ 3 猜 T │
 └────────┘ ◀─── └────────┘ ◀─── └────────┘ ◀─── └────────┘
             N               N               N
   強烈不跳        偏向不跳        偏向會跳        強烈會跳
   （T = 實際跳了，N = 實際沒跳；箭頭是依實際結果更新計數器）
```

為什麼要兩個位元？手算一個例子就懂。假設一個內層迴圈每次跑 4 圈，迴圈尾端的條件跳躍行為是 T T T N（前三圈結束時跳回去、第四圈結束時不跳，離開迴圈），外層不斷重複。

| 第幾次 | 實際 | 1-bit（記住上一次） | 對錯 | 2-bit 計數器（起始 3） | 預測 | 對錯 | 更新後 |
|---|---|---|---|---|---|---|---|
| 1 | T | 上次 T → 猜 T | ✓ | 3 | T | ✓ | 3 |
| 2 | T | 猜 T | ✓ | 3 | T | ✓ | 3 |
| 3 | T | 猜 T | ✓ | 3 | T | ✓ | 3 |
| 4 | N | 猜 T | ✗ | 3 | T | ✗ | 2 |
| 5 | T | 上次 N → 猜 N | ✗ | 2 | T | ✓ | 3 |
| 6 | T | 猜 T | ✓ | 3 | T | ✓ | 3 |
| 7 | T | 猜 T | ✓ | 3 | T | ✓ | 3 |
| 8 | N | 猜 T | ✗ | 3 | T | ✗ | 2 |

穩定之後，1-bit 預測器每 4 次錯 2 次（50% 準確率），2-bit 計數器每 4 次只錯 1 次（75%）。差別在於迴圈結束時那一次「不跳」只把計數器從 3 降到 2，下一輪迴圈開始時依然預測「跳」，不會被一次例外帶偏。

現代處理器的預測器遠比這複雜，但原理相通：

| 元件 | 作用 | 例子 |
|---|---|---|
| 方向預測器（history-based） | 不只看這個分支自己，還看最近幾十到上千個分支的歷史，找出規律 | `if (i % 2)` 這種交錯模式也能學會 |
| BTB（branch target buffer） | 記住「位於這個位址的分支，上次跳到哪裡」，讓 fetch 在 decode 之前就知道目標 | 函式指標、`switch` 的 jump table（第 8 章） |
| RAS（return address stack） | 硬體內部的小 stack，`call` 時推入返回位址，`ret` 時彈出來當預測 | 解決 PIPE 裡 `ret` 要等三個 cycle 的問題 |

但無論預測器多聰明，有一種情況它無能為力：**分支的結果本身就是隨機的**。小安那張手繪貼紙的 alpha 值在 128 上下亂跳，`alpha[i] >= 128` 沒有任何規律可學，預測器大約只能猜對一半。測試貼紙全部是 255，條件永遠成立，預測器幾乎每次都對。這就是 13.1 節十倍差距的來源，13.12 節會親手量出來。

> [!warning] 常見誤解
> 「分支本身很慢，所以要盡量避免 `if`。」不對。**預測正確的分支幾乎免費**，昂貴的是預測錯誤。一個在迴圈裡跑一百萬次、99.9% 都走同一邊的 `if`，對效能的影響通常微乎其微。要擔心的是那些結果取決於資料、而資料又沒有規律的分支。

## 13.8 例外處理：pipeline 裡的 precise exception

第 20 章會介紹 **exception**（例外）：指令執行中發生了需要作業系統介入的事件，例如除以零、存取不合法的位址（page fault）、執行非法指令。Y86-64 有幾種狀態碼：`AOK`（正常）、`HLT`（執行了 `halt`）、`ADR`（不合法的位址）、`INS`（不合法的指令）。

在循序處理器中，例外很單純：哪條指令出事，就停在那條。但在 pipeline 裡，同時有五條指令在不同階段，例外可能在任何一段被發現，而且可能有好幾條指令同時出事。處理器必須遵守一個原則，叫 **precise exception**（精確例外）：

> 從作業系統的角度看，出事那條指令**之前**的所有指令都已經完整生效，出事那條和**之後**的所有指令都好像從來沒執行過。

為什麼這麼堅持？因為作業系統要能「修好再重來」。第 23 章的 page fault 就是最好的例子：kernel 把缺的頁載入之後，CPU 要重新執行同一條指令，程式完全察覺不到中間發生過什麼。如果出事那條之後的指令已經改了暫存器，重新執行就會得到錯誤的結果。

PIPE 實現 precise exception 的方式很簡潔：

```text
 cycle 7 的 pipeline 狀態（由新到舊）
 ┌────────┬────────┬────────┬────────┬────────┐
 │ F      │ D      │ E      │ M      │ W      │
 │ 指令 5 │ 指令 4 │ 指令 3 │ 指令 2 │ 指令 1 │
 │        │ INS!   │        │ ADR!   │ AOK    │
 └────────┴────────┴────────┴────────┴────────┘
   指令 4 在 fetch 時就被發現是非法指令，INS 跟著它到了 decode；
   指令 2 在 memory 讀到不合法位址。
   規則：狀態碼跟著指令往右走，到 W 才真正處理 → 先處理最舊的指令 2。
         指令 2 一旦帶著例外進入 M，就禁止後面的指令 3 改條件碼、
         禁止它們寫記憶體；它們永遠不會提交。
```

1. **狀態碼跟著指令走。** 每排 pipeline register 都有 `stat` 欄位，指令在哪一段發現問題，就把狀態記在自己身上，繼續往下走，而不是立刻停機。
2. **到 write back 才處理。** 只有當帶著例外狀態的指令走到 W，處理器才真正停下來。因為最舊的指令最先到 W，自然保證了「先處理程式順序上最早的那個例外」。上圖中，指令 4 的非法指令雖然也被偵測到，但指令 2 先到 W，指令 4 根本不會被處理，這是對的，因為按照程式順序，執行到指令 2 就該停了。
3. **阻止後面的指令留下痕跡。** 一條指令帶著例外進入 memory 或 write back 階段後，它後面的指令就不能再寫記憶體或改條件碼。

另一種例外來源是外部的 **interrupt**（中斷，例如計時器或網卡），它不屬於任何一條指令。處理器只需選一個位置當作邊界，讓之前的指令完成、之後的作廢，再跳去處理中斷，同樣維持 precise 的語意。

## 13.9 CPI：把 hazard 的代價算出來

Hazard 的代價可以量化。**CPI**（cycles per instruction，每條指令平均 cycle 數）是處理器效能分析最常用的指標之一，它的倒數 **IPC**（instructions per cycle）在現代處理器的工具中更常見。理想的 PIPE 每個 cycle 完成一條指令，CPI = 1.0；每個 bubble 都讓 CPI 往上加。

把三種主要的懲罰分開算：

```text
CPI = 1.0 + lp + mp + rp

lp（load penalty）     = load 佔指令比例 × 其中緊接著使用的比例 × 1 cycle
mp（mispredict penalty）= 條件跳躍佔比 × 預測錯誤率 × 2 cycles
rp（return penalty）    = ret 佔比 × 3 cycles
```

用 `thumbd` 縮圖迴圈的一組假設指令組成來算：

| 項目 | 假設值 | 計算 | 懲罰 |
|---|---|---|---|
| load-use | load 佔 30%，其中 15% 緊接使用 | 0.30 × 0.15 × 1 | 0.045 |
| 條件跳躍（一般照片） | 佔 18%，預測錯誤 10% | 0.18 × 0.10 × 2 | 0.036 |
| `ret` | 佔 2% | 0.02 × 3 | 0.060 |
| 合計 | | 1.0 + 0.045 + 0.036 + 0.060 | **CPI = 1.141** |

在 PIPE 上，hazard 讓效能損失約 14%。現在換成那張手繪貼紙：預測錯誤率從 10% 升到 45%，mp = 0.18 × 0.45 × 2 = 0.162，CPI 變成 1.267，多了約 11%。看起來還好？

問題在於真實處理器的預測錯誤懲罰不是 2 個 cycle。現代高效能核心的 pipeline 深得多，分支要到很後面才確定，猜錯時要丟掉的工作也多得多，懲罰大約是十多到二十個 cycle（依微架構而定）。把懲罰換成 15 cycles 再算一次：

| 情境 | mp 計算 | mp | 合計 CPI（其他項不變） |
|---|---|---|---|
| 一般照片，錯 10% | 0.18 × 0.10 × 15 | 0.27 | 1.375 |
| 手繪貼紙，錯 45% | 0.18 × 0.45 × 15 | 1.215 | 2.320 |

更糟的是，現代處理器每個 cycle 可以完成好幾條指令（13.10 節），理想的 CPI 遠小於 1。假設理想 CPI 是 0.25（每 cycle 4 條），那麼 1.215 的分支懲罰會讓程式慢上好幾倍。這就是 13.1 節裡，同一段程式差十倍的量級從哪裡來。

> [!note] 這個公式的用途
> CPI 公式在真實系統上不能精確預測效能（還有 cache miss、多發射、亂序等因素），但它教你一個非常實用的思考方式：**某種事件的總代價 = 發生頻率 × 每次的代價**。看到 `perf` 報告每千條指令有 20 次 branch miss，乘上每次十幾個 cycle，就能估計分支預測吃掉了多少比例的時間。

## 13.10 現代處理器：superscalar 與 out-of-order

PIPE 是教學用的五段依序 pipeline。你手上的筆電、伺服器裡的 CPU 在同樣的原理上走得遠得多。CS:APP 第 5 章（本書第 14 章）用一個抽象模型描述現代處理器，這裡先把關鍵概念建立起來。

```text
 ┌────────────── 前端（依程式順序）──────────────┐
 │ 分支預測器 ─▶ fetch ─▶ decode ─▶ 拆成 micro-op ─▶ register renaming
 │   （每 cycle 抓好幾條指令，沿著預測的路徑一直往前）        │
 └───────────────────────────────────────────────┬──┘
                                                 ▼
                                  ┌──────────────────────────────┐
                                  │ 排程器：運算元就緒的 micro-op │
                                  │ 先送出（不管程式順序）         │
                                  └──┬──────┬──────┬──────┬───────┘
                                     ▼      ▼      ▼      ▼
                                  整數 ALU  整數 ALU  浮點／SIMD  load／store
                                     │      │      │      │
                                     ▼      ▼      ▼      ▼
 ┌──────────────────────── reorder buffer（ROB）────────────────────────┐
 │  依程式順序排隊；最舊的指令完成了才 retire（提交到架構狀態）           │
 │  預測錯誤或例外 → 丟掉這條之後的所有 entry                           │
 └──────────────────────────────────────────────────────────────────────┘
```

這張圖裡有四個 PIPE 沒有的概念：

**Superscalar**（超純量）：每個 cycle 可以 fetch、decode、執行、提交**多條**指令，而不是一條。現代高效能核心每個 cycle 可以處理四條、六條甚至更多，所以 IPC 可以大於 1。這也表示 CPI 可以小於 1。

**Out-of-order execution**（亂序執行）：指令按程式順序進來，但只要運算元準備好就可以先執行，不必等前面不相關的指令。例如一個 load 正在等 cache miss，後面十條和它無關的加法可以先算完。這是硬體版的 instruction scheduling。

**Register renaming**（暫存器重新命名）：程式碼裡的 `%rax` 只是一個名字，硬體內部有數百個實體暫存器。每次有指令寫 `%rax`，就分配一個新的實體暫存器給它。這樣「先讀後寫」（WAR）和「寫後再寫」（WAW）這兩種假依賴就消失了，只剩真正的 RAW 依賴會限制執行順序。

**Reorder buffer**（ROB，重排序緩衝區）與 **retirement**（退休、提交）：亂序執行的結果先放在 ROB 裡，不直接改架構狀態（程式看得到的暫存器與記憶體）。ROB 依程式順序，最舊的指令完成後才讓它 retire。猜錯分支或發生例外時，丟掉那條指令之後的所有 entry 就好。這就是 precise exception 在亂序處理器上的實現方式：**執行可以亂序，提交必須依序**。

| 概念 | PIPE（教學用） | 現代高效能核心（量級，依微架構而定） |
|---|---|---|
| 每 cycle 處理的指令 | 1 條 | 數條到十條左右 |
| pipeline 深度 | 5 段 | 十多段 |
| 執行順序 | 依序 | 亂序，視窗可容納數百條指令 |
| 分支預測 | 永遠猜跳 | 學習歷史的複雜預測器、BTB、RAS |
| 預測錯誤懲罰 | 2 cycles | 約十多到二十個 cycles |
| data hazard | forwarding ＋ load interlock | renaming 消除假依賴，只剩真依賴 |
| precise exception | `stat` 欄位跟著走，到 W 處理 | ROB 依序 retire |

亂序執行讓「預測」變得更重要也更危險。前端沿著預測的路徑一直抓、一直執行，ROB 裡可能有上百條推測出來的指令。猜對了，這些工作全部有效；猜錯了，全部丟掉，前端還要重新填滿。這種「先做再說」的策略叫 **speculative execution**（推測執行）。下一節會看到，「全部丟掉」並沒有想像中那麼乾淨。

> [!warning] 常見誤解
> 「亂序執行代表程式的結果也可能亂序。」不會。對單一 thread 來說，ROB 保證結果和依序執行完全一樣。亂序執行只影響**時間**，不影響結果。多個 thread 之間觀察到的記憶體順序是另一個問題，第 32 章談記憶體模型時再說。

## 13.11 推測執行的陰影：Spectre 與 Meltdown

推測執行有一個前提：錯誤路徑上的指令被丟掉後，不會留下任何程式看得到的痕跡。這對**架構狀態**（暫存器、記憶體內容）是成立的。但 2018 年公開的一系列漏洞指出，**微架構狀態**（cache 裡有哪些資料、預測器學到了什麼）並不會被回滾，而且可以透過量測時間間接讀出來。

### Spectre：讓預測器帶著程式走錯路

**Spectre** 的核心想法可以用一段很普通的程式說明：

```c
/* 一段看起來完全安全的程式：先檢查邊界，再讀陣列 */
if (x < array1_size) {
    unsigned char secret = array1[x];
    y = array2[secret * 4096];
}
```

正常執行時，`x` 超出範圍就不會讀 `array1[x]`。但攻擊者可以先用很多次合法的 `x` 呼叫這段程式，把分支預測器訓練成「這個 `if` 通常會成立」。然後傳入一個超出範圍的 `x`，並讓 `array1_size` 不在 cache 裡（比較要等很久）。在比較結果出來之前，CPU 依照預測先執行了 `if` 裡面的兩行：讀出邊界外的某個 byte（可能是密碼或金鑰），再用這個值當索引讀 `array2`，於是 `array2` 的某一個 cache line 被載入 cache。

比較結果出來，CPU 發現猜錯，丟掉這兩行的結果，`secret` 和 `y` 從來沒有被寫入架構狀態。但 `array2[secret * 4096]` 那一條 cache line 還留在 cache 裡。攻擊者接著量測讀取 `array2` 每一頁的時間，哪一頁特別快，就知道 `secret` 是多少。這種從 cache 時間推出資料的手法叫 **cache timing side channel**（快取時間旁路），第 16 章會說明 cache hit 與 miss 的時間差為何這麼明顯。

### Meltdown：權限檢查來得太晚

**Meltdown** 利用的是另一個實作細節：部分處理器在推測執行一個讀取 kernel 記憶體的 load 時，先把資料送給後面的指令用，權限檢查的結果等到 retire 時才處理。指令最後當然會觸發例外而不會提交，但後面的指令已經用那個值在 cache 留下了痕跡。第 23 章提到 kernel 的頁會映射在每個 process 的位址空間中，只用 PTE 的 user／supervisor 位元保護，Meltdown 正是繞過了這道檢查。

| 漏洞 | 利用的推測機制 | 主要緩解方式 |
|---|---|---|
| Spectre v1（bounds check bypass） | 條件分支預測 | 在敏感的邊界檢查後插入 `lfence` 之類的序列化指令；把索引遮罩到合法範圍（Linux kernel 的 `array_index_nospec`） |
| Spectre v2（branch target injection） | 間接跳躍目標預測（BTB） | retpoline、硬體的 IBRS／eIBRS 等控制 |
| Meltdown | 權限檢查前就把資料交給後續指令 | KPTI（user mode 不映射 kernel 頁，第 23 章）；新硬體已修正 |
| 瀏覽器中的 Spectre | 同上，攻擊程式是網頁的 JavaScript | 降低計時器精度、site isolation（不同網站放在不同 process） |

這些漏洞給系統工程師的教訓是：**效能最佳化和安全隔離是同一套硬體機制的兩面**。推測執行讓程式快，也讓隔離有了縫隙；緩解措施補上縫隙，也要付出效能代價，例如 KPTI 讓每次 system call 都要切換 page table。在 Linux 上可以看到目前系統對每一種漏洞的狀態：

```bash
grep . /sys/devices/system/cpu/vulnerabilities/*
lscpu | grep -i vulnerab
```

> [!warning] 常見誤解
> 「Spectre 是 bug，換新 CPU 就沒事了。」部分變種（例如 Meltdown）已在新硬體中修正，但 Spectre v1 的本質是「推測執行會在 cache 留下痕跡」，只要處理器還在做推測執行，這類問題就很難從根本消除。處理敏感資料的程式碼（密碼學函式庫、kernel、瀏覽器）仍需要軟體層的防護。

## 13.12 動手做：模擬 pipeline，量測分支預測

### 程式一：五階段 pipeline 時序模擬器

這段 Python 程式實作 13.4–13.7 節的規則，自動畫出時序圖。它不是完整的處理器模擬器，只模擬「每條指令在哪個 cycle 進入哪個階段」，但已經足以驗證本章所有的手算時序。

```python
# 五階段 pipeline（F D E M W）的時序模擬器，規則對應 CS:APP 的 PIPE 設計：
#   - 指令在 D 階段讀暫存器；沒有 forwarding 時，必須等生產者寫回（W）之後的下一個 cycle
#   - 有 forwarding 時，ALU 結果在生產者的 E 階段就能送到 D；load 的資料要到 M 階段
#   - 條件跳躍預測「會跳」；猜錯要到跳躍指令的 E 階段才知道，已抓進來的兩條作廢

def simulate(prog, forwarding):
    timing, last_writer = [], {}
    for i, (text, dst, srcs, kind) in enumerate(prog):
        if i == 0:
            f, d_entry = 1, 2
        elif timing[-1]["mispredict"]:
            f = timing[-1]["E"] + 1               # 從正確位址重新抓
            d_entry = f + 1
        else:
            f = timing[-1]["D_entry"]             # 前一條進 D 的同一個 cycle，我進 F
            d_entry = timing[-1]["D_final"] + 1   # 前一條離開 D，我才能進 D
        need = d_entry
        for r in srcs:
            if r in last_writer:
                p = timing[last_writer[r]]
                if not forwarding:
                    need = max(need, p["W"] + 1)
                elif p["kind"] == "load":
                    need = max(need, p["M"])
                else:
                    need = max(need, p["E"])
        e = need + 1
        timing.append({"text": text, "kind": kind, "F": f, "D_entry": d_entry,
                       "D_final": need, "E": e, "M": e + 1, "W": e + 2,
                       "mispredict": kind == "jmp-miss"})
        if dst:
            last_writer[dst] = i
    return timing

def show(title, prog, forwarding):
    t = simulate(prog, forwarding)
    last = t[-1]["W"]
    print(f"== {title}")
    print(" " * 22 + "".join(f"{c:>3}" for c in range(1, last + 1)))
    for row in t:
        cells = {c: "F" for c in range(row["F"], row["D_entry"])}  # 連續的 F = 卡在 F
        cells.update({row["E"]: "E", row["M"]: "M", row["W"]: "W"})
        for c in range(row["D_entry"], row["D_final"] + 1):
            cells[c] = "D" if c == row["D_final"] else "s"   # s = stall，卡在 D
        print(f"{row['text']:<22}" + "".join(f"{cells.get(c, ''):>3}" for c in range(1, last + 1)))
        if row["mispredict"]:                      # 猜錯路徑上被抓進來、之後作廢的兩條
            for k, wrong in enumerate([{row["F"] + 1: "F", row["F"] + 2: "D", row["F"] + 3: "x"},
                                       {row["F"] + 2: "F", row["F"] + 3: "x"}]):
                print(f"{'  (wrong path #' + str(k + 1) + ')':<22}"
                      + "".join(f"{wrong.get(c, ''):>3}" for c in range(1, last + 1)))
    bubbles = sum(r["D_final"] - r["D_entry"] for r in t)
    squashed = 2 * sum(r["mispredict"] for r in t)
    print(f"共 {last} cycles，{len(t)} 條指令，stall {bubbles} 次，作廢 {squashed} 條\n")

dep = [("irmovq $10,%rdx", "rdx", [], "alu"),
       ("irmovq $3,%rax", "rax", [], "alu"),
       ("addq %rdx,%rax", "rax", ["rdx", "rax"], "alu"),
       ("halt", None, [], "alu")]
load_use = [("mrmovq 0(%rdi),%rax", "rax", ["rdi"], "load"),
            ("addq %rax,%rbx", "rbx", ["rax", "rbx"], "alu"),
            ("halt", None, [], "alu")]
branch = [("andq %rax,%rax", None, ["rax"], "alu"),
          ("jne done (mispredict)", None, [], "jmp-miss"),
          ("irmovq $1,%rcx", "rcx", [], "alu"),
          ("halt", None, [], "alu")]

show("data hazard，沒有 forwarding", dep, forwarding=False)
show("data hazard，有 forwarding", dep, forwarding=True)
show("load-use hazard，有 forwarding", load_use, forwarding=True)
show("條件跳躍預測錯誤", branch, forwarding=True)
```

在 macOS arm64（Python 3）上執行的輸出：

```text
== data hazard，沒有 forwarding
                        1  2  3  4  5  6  7  8  9 10 11
irmovq $10,%rdx         F  D  E  M  W
irmovq $3,%rax             F  D  E  M  W
addq %rdx,%rax                F  s  s  s  D  E  M  W
halt                             F  F  F  F  D  E  M  W
共 11 cycles，4 條指令，stall 3 次，作廢 0 條

== data hazard，有 forwarding
                        1  2  3  4  5  6  7  8
irmovq $10,%rdx         F  D  E  M  W
irmovq $3,%rax             F  D  E  M  W
addq %rdx,%rax                F  D  E  M  W
halt                             F  D  E  M  W
共 8 cycles，4 條指令，stall 0 次，作廢 0 條

== load-use hazard，有 forwarding
                        1  2  3  4  5  6  7  8
mrmovq 0(%rdi),%rax     F  D  E  M  W
addq %rax,%rbx             F  s  D  E  M  W
halt                          F  F  D  E  M  W
共 8 cycles，3 條指令，stall 1 次，作廢 0 條

== 條件跳躍預測錯誤
                        1  2  3  4  5  6  7  8  9 10
andq %rax,%rax          F  D  E  M  W
jne done (mispredict)      F  D  E  M  W
  (wrong path #1)             F  D  x
  (wrong path #2)                F  x
irmovq $1,%rcx                      F  D  E  M  W
halt                                   F  D  E  M  W
共 10 cycles，4 條指令，stall 0 次，作廢 2 條
```

逐段解說：

1. `simulate` 的核心只有一個變數 `need`：消費者最早能完成 decode 的 cycle。它從「正常情況下的 decode 時間」開始，對每個來源暫存器找出最近一個寫它的生產者，再依規則把 `need` 往後推。沒有 forwarding 時要等到生產者 `W + 1`；有 forwarding 時，ALU 結果在生產者的 E 那一個 cycle 就能送到，load 則要到 M。
2. 第一張圖的 3 次 stall 就是 13.4 節推導的結果。注意 `halt` 和 `addq` 沒有任何依賴，卻也在 fetch 等了三個 cycle：依序 pipeline 裡，前面的指令卡住，後面全部要排隊。
3. 第二張圖證實 forwarding 讓同樣的指令完全不用等，總共 8 個 cycle = 4 條指令 + 4 個 cycle 的填充時間（pipeline 從空到滿）。
4. 第三張圖的 1 次 stall 是 load-use hazard 的最小代價：`addq` 的 `need` 被推到 `mrmovq` 的 M 階段（cycle 4）。
5. 第四張圖的兩條 wrong path 在 cycle 5 被沖掉，正確的 `irmovq` 從 cycle 5 才開始 fetch，比沒猜錯晚了兩個 cycle。

### 程式二：量測分支預測錯誤的代價

這段 C 程式就是 13.1 節小安的掃描函式，用四種 alpha 資料各跑一次。`__attribute__((noinline))` 讓函式保持獨立，方便在組合語言裡找到它。

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* thumbd 合成浮水印前，先挑出「不透明」的像素（alpha >= 128）並收集它們的索引。
 * if 裡有一次 store 和 k++，編譯器通常會留下真正的條件分支。 */
__attribute__((noinline))
static long collect_opaque(const uint8_t *alpha, long n, int32_t *out) {
    long k = 0;
    for (long i = 0; i < n; i++)
        if (alpha[i] >= 128)
            out[k++] = (int32_t)i;
    return k;
}

static double now_ns(void) {             /* 單調時鐘，不受系統校時影響 */
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec * 1e9 + (double)t.tv_nsec;
}

static int by_alpha(const void *p, const void *q) {   /* qsort 用：由小到大 */
    uint8_t a = *(const uint8_t *)p, b = *(const uint8_t *)q;
    return (a > b) - (a < b);
}

static double bench(const uint8_t *alpha, long n, int32_t *out, long *count) {
    double best = 1e30;
    for (int t = 0; t < 9; t++) {
        double t0 = now_ns();
        *count = collect_opaque(alpha, n, out);
        double el = now_ns() - t0;
        if (el < best) best = el;
    }
    return best / n;
}

int main(void) {
    enum { N = 1 << 20 };                          /* 一張 1024x1024 圖的 alpha 通道 */
    uint8_t *alpha = malloc(N);
    int32_t *out = malloc(N * sizeof(int32_t));
    long count;
    srand(42);
    for (long i = 0; i < N; i++) out[i] = 0;       /* 先碰過 out 的每一頁，避免 page fault 混進量測 */

    for (long i = 0; i < N; i++) alpha[i] = 255;   /* 測試圖：全部不透明 */
    for (int w = 0; w < 200; w++) collect_opaque(alpha, N, out);  /* 暖機，讓 CPU 升到高時脈 */
    printf("全部不透明     %.3f ns/像素\n", bench(alpha, N, out, &count));

    for (long i = 0; i < N; i++) alpha[i] = (uint8_t)(rand() & 0xFF);  /* 真實圖：雜亂 */
    double t_rand = bench(alpha, N, out, &count);
    printf("隨機 alpha     %.3f ns/像素（不透明 %ld 個）\n", t_rand, count);

    qsort(alpha, N, 1, by_alpha);                  /* 同一批資料，排序後 */
    double t_sorted = bench(alpha, N, out, &count);
    printf("排序後 alpha   %.3f ns/像素（不透明 %ld 個）\n", t_sorted, count);

    for (long i = 0; i < N; i++) alpha[i] = (i % 2) ? 255 : 0;  /* 規律交錯 */
    printf("交錯 0/255     %.3f ns/像素\n", bench(alpha, N, out, &count));

    printf("隨機比排序慢 %.1f 倍\n", t_rand / t_sorted);
    free(alpha); free(out);
    return 0;
}
```

在一台 Apple M4 Pro 的 macOS arm64 上，以 Apple clang 21 與 `cc -std=c17 -O1 -Wall -Wextra` 編譯執行，得到：

```text
全部不透明     0.254 ns/像素
隨機 alpha     2.910 ns/像素（不透明 523962 個）
排序後 alpha   0.257 ns/像素（不透明 523962 個）
交錯 0/255     0.511 ns/像素
隨機比排序慢 11.3 倍
```

上面是接上電源時的結果。另外在同一台機器改用電池、開著低耗電模式重跑五次，四列的時間全部變成約 2.2 倍（例如全部不透明約 0.56 ns、隨機約 6.2–6.4 ns），但「隨機比排序慢」的倍數仍然穩定在 11.2–11.5 倍。時脈降低會讓每個 cycle 變長，ns 跟著變大；分支預測錯誤要付出的 cycle 數不變，所以倍數不變。自己重跑時，絕對數字和這裡不同是正常的，要比較的是同一次執行裡各列之間的比例。

逐行解讀：

1. **全部不透明（0.254 ns）**：分支永遠成立，預測器每次都對。這是小安在 CI 上看到的數字。
2. **隨機 alpha（2.910 ns）**：同一個函式、同樣的元素數，慢了十倍以上。不透明的像素有 523,962 個，大約一半，`alpha[i] >= 128` 等於每個像素擲一次公平硬幣，預測器大約只能猜對一半。
3. **排序後 alpha（0.257 ns）**：這是最有說服力的對照組。資料**完全相同**，只是順序變了：前一半全部不成立、後一半全部成立。寫入次數、讀取次數、cache 行為都一樣，唯一的差別是分支變得可以預測。時間回到和全部不透明幾乎一樣。
4. **交錯 0/255（0.511 ns）**：條件每個像素都翻轉一次。如果預測器只用 2-bit 計數器，這種模式最多只能猜對一半，起始狀態不巧時甚至每次都錯；但實際只比可預測的情況慢一點，遠比隨機快，說明現代預測器會利用歷史紀錄學到「一跳一不跳」的規律。這一列的數字在不同次執行、不同機器上可能有些變動，但始終遠低於隨機的情況。

可以粗略估計每次預測錯誤的代價：隨機與排序相差約 2.65 ns/像素，而隨機情況下約一半的像素會猜錯，所以每次猜錯大約多花 5 ns。以這台機器約 4.5 GHz 的時脈（第 14 章 14.2 節說明這個數字的來源）換算，相當於二十多個 cycle 的量級；低耗電模式下的那組數字（每次約 11 ns、時脈約減半）換算出來也是同一個量級。這只是粗估，因為它也包含了猜錯之後前端重新填滿、以及原本可以重疊執行的工作被打斷的時間。

> [!note] 為什麼要量「排序後」
> 好的效能實驗要**只改變一個變數**。如果只比較「全部 255」和「隨機」，有人會質疑寫入次數不同（前者寫 100 萬次，後者寫 52 萬次）。排序後的資料和隨機資料寫入次數完全相同，時間卻差十倍，這就排除了寫入量、cache、記憶體頻寬等其他解釋。

### 確認編譯器真的產生了分支

C 的 `if` 不一定會變成條件跳躍：第 8 章提過，編譯器可能改用 conditional move。要確認，就看組合語言。用以下指令在任何機器上產生 x86-64 的版本（`-O1`，與上面的量測相同等級）：

```bash
clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - br.c
```

其中 `br.c` 是同一個 `collect_opaque` 函式，外加一個對照用的 `clamp_u8`（`return v > 255 ? 255 : v;`）。輸出刪去 directive 後：

```asm
collect_opaque:
	testq	%rsi, %rsi
	jle	.LBB0_1
	xorl	%ecx, %ecx
	xorl	%eax, %eax
	jmp	.LBB0_4
.LBB0_6:
	incq	%rcx
	cmpq	%rcx, %rsi
	je	.LBB0_2
.LBB0_4:
	cmpb	$0, (%rdi,%rcx)
	jns	.LBB0_6
	movl	%ecx, (%rdx,%rax,4)
	incq	%rax
	jmp	.LBB0_6
.LBB0_1:
	xorl	%eax, %eax
.LBB0_2:
	retq
clamp_u8:
	cmpl	$255, %edi
	movl	$255, %eax
	cmovll	%edi, %eax
	retq
```

`collect_opaque` 的迴圈裡，`cmpb $0, (%rdi,%rcx)` 把 alpha byte 當成有號數和 0 比較：`alpha >= 128` 等價於「最高位元是 1」，也就是有號解讀為負數。`jns`（sign flag 為 0 時跳）在 alpha 小於 128 時跳過寫入。這個 `jns` 就是那枚硬幣。

`clamp_u8` 則沒有任何條件跳躍：`cmovll` 依條件碼選擇兩個值之一，沒有東西要預測。為什麼編譯器對 `collect_opaque` 不用 cmov？因為 `if` 裡面有一個**記憶體寫入**和計數器遞增，cmov 只能選擇暫存器的值，無法「有條件地寫入記憶體」。第 14 章會示範怎麼手動把這段程式改寫成沒有分支的版本，以及它在什麼情況下反而比較慢。在本機 arm64 上，clang 產生的是 `tbz`（測試某一位元為零就跳），原理相同。

## 13.13 在工作上怎麼用

### 情境一：效能和輸入資料有關

`thumbd` 的事件有一個典型特徵：**同樣的程式碼，效能隨輸入內容而變，而不只是隨輸入大小而變**。看到這種症狀，分支預測錯誤應該列在嫌疑名單前幾名。判斷流程：

```text
症狀：同樣大小的輸入，某些資料特別慢
  │
  ├─ 1. 先確認不是 I/O、lock、GC：CPU time 是否也同比例變高？
  │      └─ 否 → 不是 CPU 問題，看 I/O 與等待（第 27、31 章）
  │
  ├─ 2. 用 hardware counter 量分支（Linux）
  │      perf stat -e cycles,instructions,branches,branch-misses ./bench fast.png
  │      perf stat -e cycles,instructions,branches,branch-misses ./bench slow.png
  │      └─ branch-misses 比例差很多、IPC 掉很多 → 分支預測問題
  │      └─ branch-misses 差不多 → 看 cache miss（第 16、17 章）
  │
  ├─ 3. 找出是哪個分支
  │      perf record -e branch-misses ./bench slow.png
  │      perf annotate   → 標出 miss 最多的那條條件跳躍指令
  │
  └─ 4. 對策（第 14 章詳述）
         ├─ 改成 branchless（cmov、位元運算、查表）
         ├─ 先把資料分類或排序，讓分支變得可預測
         └─ 把判斷移出最內層迴圈（例如先整塊判斷是否全不透明）
```

`perf stat` 的輸出大致長這樣（示意輸出，數字依機器而定）：

```text
 Performance counter stats for './bench slow.png':

     3,120,455,201      cycles
     4,402,118,930      instructions          #    1.41  insn per cycle
       905,331,207      branches
        98,772,410      branch-misses         #   10.91% of all branches
```

讀法是先看 IPC（insn per cycle），再看 branch-misses 的比例。一般程式的 branch miss 比例通常在百分之幾以下；超過 5% 而且集中在熱點函式，就值得深入。在 macOS 上沒有 `perf`，可以用 Xcode Instruments 的 CPU Counters 範本看同類的硬體計數器。

### 情境二：讀懂 IPC 這個數字

很多監控與 profiling 工具會顯示 IPC 或 CPI。用本章的知識可以這樣解讀：

| 觀察 | 可能的原因 | 下一步 |
|---|---|---|
| IPC 高（例如 3 以上） | 指令之間沒什麼依賴，預測準確、資料在 cache 裡 | 要更快只能減少指令數或用 SIMD（第 14 章） |
| IPC 中等（1–2） | 有一些依賴鏈或零星的 miss | 看 critical path（第 14 章） |
| IPC 低（低於 1）且 branch-misses 高 | 分支預測錯誤頻繁 | 找出熱點分支，考慮 branchless 或重排資料 |
| IPC 低且 cache-misses 高 | 記憶體延遲，CPU 在等資料 | 改善 locality（第 17 章） |

注意 IPC 的「好壞」沒有絕對標準，它依處理器與工作類型而定。最有用的是**同一台機器、同一個程式、不同輸入或不同版本之間的比較**。

### 情境三：評估 Spectre 緩解的效能成本

SRE 有時會遇到「升級 kernel 之後 system call 密集的服務變慢了」。原因之一可能是新的推測執行緩解措施（例如 KPTI 讓每次進出 kernel 都要切換 page table）。檢查清單：

1. 用 `grep . /sys/devices/system/cpu/vulnerabilities/*` 比較升級前後各項緩解狀態。
2. 用 `strace -c -p <PID>`（短時間取樣）確認服務是否 system call 密集（第 20 章）。
3. 優先減少 system call 次數（批次化 I/O、加大 buffer），而不是關閉緩解措施。
4. kernel 開機參數 `mitigations=off` 可以關閉大部分緩解，但這會讓同一台機器上的其他 process 或租戶可能讀到你的資料。只有在確定機器是單一信任域（沒有不受信任的程式碼）時才考慮，而且需要安全團隊同意。

## 13.14 常見錯誤與除錯

| 症狀 | 常見原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 同樣大小的輸入，某些資料慢好幾倍 | 資料決定的分支無法預測 | 用排序後的同一份資料重測；`perf stat` 比較 branch-misses | branchless 改寫、資料分類、把判斷提到外層（第 14 章） |
| benchmark 很快，production 很慢 | 測試資料太規律（全 0、全 255、排序過），預測器每次都對 | 用 production 的真實樣本跑 benchmark | 建立具代表性的測試資料集，納入 CI |
| 把 `if` 改成三元運算子，效能沒變 | 編譯器本來就已經用 cmov，或改寫後仍然產生分支 | 看組合語言（`-S` 或 `objdump -d`）找條件跳躍指令 | 先確認問題真的是分支，再改寫；以組合語言為準 |
| 把分支改成 branchless 之後反而變慢 | 原本的分支其實可預測，branchless 版本每次都要做兩邊的工作 | 分別用可預測與隨機資料量兩個版本 | 只在分支真的不可預測時改寫，並保留量測證據 |
| 微基準測試結果時好時壞 | CPU 時脈尚未升高、page fault、其他程式干擾 | 多跑幾次看變異；加暖機；取多次中的最佳值或中位數 | 暖機、固定輸入、記錄環境（第 14 章的量測守則） |
| 升級 kernel 後 system call 密集的服務變慢 | 新的推測執行緩解措施 | 比較 `/sys/devices/system/cpu/vulnerabilities/` 前後差異 | 減少 system call 次數；不要輕易關閉緩解 |

## 13.15 動手練習

1. **手算**：一條 pipeline 的組合邏輯總共 600 ps，暫存器開銷 25 ps。分別算出不切、平均切成 3 段、平均切成 6 段時的 cycle 時間、throughput 與 latency。切成 6 段比 3 段的 throughput 提高了幾倍？（答案：625 ps／1.6 GIPS／625 ps；225 ps／4.44 GIPS／675 ps；125 ps／8.0 GIPS／750 ps；約 1.8 倍，不是 2 倍。）
2. **手算**：在 PIPE 上畫出這段程式的時序圖：`mrmovq 0(%rdi),%rax`、`mrmovq 8(%rdi),%rbx`、`addq %rax,%rbx`。`addq` 需要 stall 嗎？要幾個 cycle？為什麼？用程式一驗證（提示：`addq` 同時讀 `%rax` 與 `%rbx`，分別找出它們的生產者在哪個階段；答案是 stall 1 個 cycle，原因是緊鄰的第二條 load 寫的 `%rbx`，而不是 `%rax`）。
3. **延伸程式一**：在模擬器中加入 `ret` 的處理：遇到 `ret` 時，下一條指令要等 `ret` 進入 W、從 `W_valM` 拿到返回位址的那個 cycle 才能 fetch（3 個 bubble）。然後模擬 `call`、`ret` 各一次的程式，確認多出的 cycle 數。
4. **手算 2-bit 預測器**：分支模式是 T N T N T N…（交錯），2-bit 計數器從 3 開始。寫出前 8 次的預測與計數器狀態，算出穩定後的準確率。再和程式二「交錯 0/255」那一列的實測結果比較，說明真實預測器顯然不只是 2-bit 計數器。
5. **延伸程式二**：把隨機資料改成「90% 是 255、10% 是隨機值」與「99% 是 255」，記錄每像素時間。畫出「預測錯誤率（估計值）」對「時間」的關係，看看是不是接近線性。
6. 在一台 Linux 機器上執行 `grep . /sys/devices/system/cpu/vulnerabilities/*`，列出每一項的狀態，挑兩項查 man page 或 kernel 文件，用自己的話說明它對應的是哪種推測機制、目前採用了什麼緩解。

## 本章重點整理

- Pipelining 把指令處理切成多個階段，讓多條指令同時在不同階段處理，提高的是 throughput，單一指令的 latency 不變甚至變長。
- Pipeline 的 cycle 時間由最慢的階段加上暫存器開銷決定，所以階段要平衡；切得越細，暫存器開銷比例越高、hazard 的代價越大，回報遞減。
- PIPE 有五個階段（F、D、E、M、W），階段之間的 pipeline register 讓每條指令帶著自己的資訊（指令種類、運算元、目的暫存器、狀態碼）往下走。
- Data hazard 是後面的指令要讀前面還沒寫回的暫存器；依序 pipeline 只需要處理 RAW 依賴。
- Stall 讓 pipeline register 保持原值、指令留在原地；bubble 往下游注入不做事的 `nop`；兩者合起來讓生產者前進、消費者等待。
- Forwarding 把 E、M、W 段已算好的值直接送到 decode，解決大多數 data hazard；多個來源同時符合時，要取最新的那條指令的值。
- Load-use hazard 無法完全用 forwarding 解決，因為資料到 memory 階段才出現，PIPE 要 stall 一個 cycle；這也說明讀記憶體的結果總是比算術晚到。
- Control hazard 來自條件跳躍與 `ret`；PIPE 預測條件跳躍會跳，猜錯時 flush 兩條指令，損失兩個 cycle。
- 分支預測器會學習歷史，可預測的分支幾乎免費；真正昂貴的是由資料決定、沒有規律的分支，實測中可以讓同一段程式慢十倍。
- Precise exception 要求出事指令之前的都已生效、之後的都沒發生；PIPE 讓狀態碼跟著指令走、到 write back 才處理，並阻止後面的指令寫入狀態。
- CPI = 1 + 各類懲罰（頻率 × 每次代價），這個「頻率乘代價」的思考方式可以用來估算任何事件對效能的影響。
- 現代處理器是 superscalar、out-of-order 的：每 cycle 處理多條指令、運算元就緒就執行、用 register renaming 消除假依賴、用 reorder buffer 依序提交，預測錯誤的懲罰約十多到二十個 cycle。
- 推測執行在架構狀態上會被回滾，但在 cache 等微架構狀態上會留下痕跡，這是 Spectre 與 Meltdown 的根源；緩解措施有真實的效能成本。

## 延伸問答

> [!question]- Q1. Pipeline 讓處理器變快，為什麼不把 pipeline 切成一百段？
> 有幾個原因讓切分的回報快速遞減。第一，每一段之間都要一排暫存器，暫存器有固定的寫入時間與時脈偏差開銷。段數越多、每段的邏輯越短，固定開銷佔 cycle 的比例就越大，13.2 節的表中 16 段時已經佔 40%，throughput 遠低於段數的倍數。
>
> 第二，hazard 的代價隨深度增加。分支要到更後面的階段才能確定，猜錯時要丟掉的指令更多；load 的結果也要更多 cycle 才能送到後面的指令。更高的時脈與更多的暫存器也帶來更高的功耗與發熱。Pentium 4 的歷史就是這個取捨的實例：深 pipeline 換到了高時脈，卻在分支預測錯誤與功耗上付出太多代價。
>
> 第三，不論切多細，指令之間的依賴不會消失。後一條指令要等前一條的結果時，等待時間由「算出結果實際需要的時間」決定，切再多段也只是把同樣的工作分散到更多 cycle。

> [!question]- Q2. Stall 和 bubble 有什麼不同？處理 load-use hazard 時各用在哪裡？
> Stall 是讓某一排 pipeline register 在下一個 cycle 保持原來的內容，所以裡面的指令停在原階段不往前走。Bubble 是讓某一排 pipeline register 在下一個 cycle 被設成 `nop` 的控制訊號，等於往下游送出一個不做任何事的空位，它不會改變暫存器、記憶體或條件碼。
>
> 處理 load-use hazard 時，PIPE 讓 F 和 D 兩排暫存器 stall（後面的指令和使用 load 結果的指令都停在原地），同時往 E 注入一個 bubble（因為 E 階段這個 cycle 沒有合法的指令可以進來）。前面的 load 照常往 M 走，下一個 cycle 資料出來，就能透過 forwarding 送給還在 decode 的指令。如果不往 E 注入 bubble，E 暫存器會照常載入 D 暫存器的內容，也就是那條還在等待的 `addq`：它會帶著錯誤的運算元往下執行，下一個 cycle 又從 D 再進 E 一次，等於同一條指令執行兩次，造成錯誤。

> [!question]- Q3. 手算題：在 PIPE 上執行 1,000 萬條指令，其中 load 佔 25%，有 20% 的 load 緊接著被使用；條件跳躍佔 20%，預測錯誤率 30%；`ret` 佔 1%。總共要多少 cycle？
> 依 CPI 公式計算三項懲罰：lp = 0.25 × 0.20 × 1 = 0.05；mp = 0.20 × 0.30 × 2 = 0.12；rp = 0.01 × 3 = 0.03。CPI = 1.0 + 0.05 + 0.12 + 0.03 = 1.20。
>
> 總 cycle 數約為 1,000 萬 × 1.20 = 1,200 萬（再加上 pipeline 一開始填滿的 4 個 cycle，可以忽略）。可以看到在這個組合裡，分支預測錯誤是最大的一項懲罰，佔額外 cycle 的 60%。如果要改善效能，優先順序應該是降低預測錯誤率，而不是去處理 load-use。這就是用公式定量比較的價值。

> [!question]- Q4. 你在 production 看到某個 API 處理同樣大小的 JSON，有些請求特別慢。怎麼判斷是不是分支預測的問題？
> 先排除外部因素：比較慢請求的 CPU time 是否也同比例增加。如果 wall time 變長但 CPU time 沒變，問題在 I/O、lock 或排程等待，和分支無關。如果 CPU time 也變長，再用 `perf stat -e cycles,instructions,branches,branch-misses` 分別對快與慢的輸入量測，比較 IPC 與 branch-misses 比例。
>
> 若慢的輸入 branch-misses 比例明顯較高、IPC 明顯較低，就用 `perf record -e branch-misses` 搭配 `perf annotate` 找出 miss 集中的指令，對照原始碼看是哪個分支。JSON 解析器常見的情況是「依字元類型分派」的分支，當輸入裡字串、數字、跳脫字元交錯得很亂時就難以預測。很多高效能 JSON 解析器正是用 SIMD 與 branchless 的技巧來處理這個問題。

> [!question]- Q5. 為什麼 forwarding 的多工器要「優先取最新的那條指令」？舉一個會出錯的例子。
> 考慮 `irmovq $1,%rax`、`irmovq $2,%rax`、`addq %rax,%rbx` 三條指令。當 `addq` 在 decode 時，第二條在 E、第一條在 M，兩條都要寫 `%rax`，forwarding 邏輯會同時發現兩個來源都符合。
>
> 依照程式的語意，`addq` 應該看到最後一次賦值的結果，也就是 2。第二條指令是比較新的，它在 E 階段，所以多工器必須先檢查 E 段（`e_valE`），再檢查 M 段。如果順序反過來，`addq` 會拿到 1，結果錯誤。這和高階語言裡「同一個變數連續賦值兩次，讀到的是最後一次」是同一件事，只是在硬體裡要靠檢查順序來保證。

> [!question]- Q6. 亂序執行的處理器怎麼保證 precise exception？
> 亂序處理器把「執行」和「提交」分開。指令依程式順序進入 reorder buffer（ROB），運算元準備好就可以先執行，但結果只寫進內部的實體暫存器與 ROB，不會立刻改變程式看得到的架構狀態。ROB 只允許最舊的指令在完成後 retire，把結果正式提交。
>
> 當某條指令發生例外，它在 ROB 裡會被標記，等到它成為最舊的指令時，處理器才處理例外：它之前的指令都已經 retire，它和它之後的指令都還沒有提交，只要把 ROB 裡從它開始的所有 entry 丟掉即可。這和 PIPE「狀態碼跟著指令走、到 W 才處理」是同樣的原理，只是規模大得多。分支預測錯誤也是用同一套機制回復。

> [!question]- Q7. 程式找錯：同事把下面這段改成 branchless，說「分支很慢」。這個改動一定有幫助嗎？`for (i = 0; i < n; i++) if (err_flag[i]) handle_error(i);`
> 不一定，而且很可能沒有幫助。分支昂貴的是**預測錯誤**，不是分支本身。錯誤旗標在正常情況下幾乎都是 0，這個分支 99.9% 以上的時間都不成立，預測器幾乎每次都猜對，代價接近零。
>
> 此外，這個 `if` 裡面是一個函式呼叫，根本無法改成 cmov 這類 branchless 形式；硬改成「每次都呼叫、在函式裡判斷」反而會讓每個元素都付出呼叫的成本。正確做法是先量測：用 `perf stat` 看 branch-misses 的比例，用 `perf annotate` 確認這個分支是否真的是熱點。只有在分支由資料決定、而且資料沒有規律時，branchless 改寫才值得考慮。

> [!question]- Q8. 面試題：請解釋 Spectre 為什麼能讀到程式「從來沒有執行過」的資料？
> 關鍵在於「沒有執行過」只對架構狀態成立。現代處理器在分支結果出來前，會依照預測先推測執行後面的指令。Spectre v1 先把邊界檢查的分支訓練成「通常會成立」，再傳入越界的索引，並讓比較所需的資料不在 cache 中。處理器在等比較結果時，推測執行了越界讀取，並用讀到的秘密值當索引去存取另一個陣列，讓特定的 cache line 被載入。
>
> 分支結果出來後，處理器發現猜錯，丟掉推測執行的結果，暫存器與記憶體都沒有改變；但 cache 的內容沒有被回滾。攻擊者接著量測存取那個陣列各個位置的時間，被載入過的那一個特別快，從位置就能推出秘密值。所以 Spectre 不是讀到了「沒有執行」的資料，而是讀到了「執行了但被撤銷」的指令在微架構狀態上留下的痕跡。緩解方式包括在敏感檢查後加入序列化指令、把索引遮罩到合法範圍，以及在瀏覽器中降低計時器精度。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 4 章 4.4–4.5 節完整說明 PIPE 的 HCL 實作，以及 Y86-64 模擬器下載。
- [CS:APP 3e Web Asides](https://csapp.cs.cmu.edu/3e/waside.html)：原書的補充章節，包括處理器設計的延伸主題。
- [CS:APP 3e Labs](https://csapp.cs.cmu.edu/3e/labs.html)：Architecture Lab 讓你修改 PIPE 的 HCL，親手加入新指令並最佳化 pipeline。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：講義與錄影，對應本章的處理器架構課程。
- [Intel 64 and IA-32 Architectures Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)：`lfence` 等序列化指令的正式定義，以及推測執行相關的控制。
