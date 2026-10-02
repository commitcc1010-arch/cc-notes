---
chapter: 1
title: Hello World 背後的旅程
part: 0
---

# 第 1 章　Hello World 背後的旅程：一支程式如何被編譯、載入與執行

> [!abstract] 本章地圖
> **核心問題**：從你按下 Enter 執行 `./hello`，到螢幕上出現 `hello, world`，中間有哪些軟體與硬體一起參與，每一層負責什麼？
>
> **你會學到**：
> - 說出原始碼變成可執行檔的四個階段（preprocess、compile、assemble、link），並看懂每個階段的產物與典型錯誤訊息
> - 畫出 CPU、記憶體、匯流排與 I/O 裝置的關係，解釋一條指令與一筆資料怎麼在它們之間流動
> - 說明 cache 與記憶體階層為什麼存在，以及為什麼「走訪順序」會讓同一段計算快上十倍
> - 理解作業系統提供的三個抽象：process、virtual memory、file，以及它們對應本書哪些章節
> - 分辨並行（concurrency）與平行（parallelism），並用 Amdahl's law 估算最佳化的上限
> - 認識貫穿全書的拾光相簿與 `thumbd`，知道全書的地圖怎麼走
>
> **前置知識**：會用任何一種高階語言寫程式；C 的細節第 2 章會補
>
> **對應 CS:APP 3e**：第 1 章 1.1–1.10 節

## 1.1 故事：第一天的兩個問題

小安在拾光相簿上班的第一天，拿到一台筆電和一個任務：在縮圖服務 `thumbd` 的 `/healthz` 回應裡加上版本號。這看起來只是一行程式的事。小安在 `version.c` 裡定義了一個函式 `thumb_version()`，在 `http.c` 裡呼叫它，然後照著 README 執行 `make`。

終端機吐出一段紅字：

```text
/usr/bin/ld: http.o: in function `handle_healthz':
http.c:(.text+0x1a4): undefined reference to `thumb_version'
collect2: error: ld returned 1 exit status
```

小安盯著它看了很久。程式碼明明寫了，`http.c` 也 include 了宣告，編譯器沒有抱怨，為什麼還說「undefined」？在 Python 裡，只要 import 對了就能呼叫，從來沒有「看得到宣告卻找不到本體」這種事。

老周走過來，看了一眼就說：「這不是編譯錯誤，是連結錯誤。你的 `version.c` 沒有加進 Makefile 的 `OBJS`，所以 `version.o` 根本沒產生，linker 找不到 `thumb_version` 的本體。」小安改了 Makefile，問題解決了。但老周接著丟出第二個問題：「使用者在 app 上點一張照片，到縮圖出現在螢幕上，`thumbd` 這台機器裡發生了什麼？你能講到多細？」

小安只能回答到「nginx 把請求轉給 `thumbd`，`thumbd` 讀檔、縮圖、回傳」。老周笑著說：「這是 Python 工程師的答案。這份工作需要你能往下多講幾層：程式怎麼變成機器碼、怎麼被載入記憶體、CPU 怎麼一條一條執行、資料怎麼從磁碟跑到 cache、作業系統在中間做了什麼。等你能講清楚，這種 link error 你一眼就知道是哪一層出的事。」

這一章就是那個「往下多講幾層」的第一次全景。我們用最小的 `hello.c` 走完整趟旅程；每一站只先看個輪廓，後面各章再一站一站拆開。

## 1.2 程式只是位元組，意義來自解讀

在追 `hello.c` 的旅程之前，先建立一個貫穿全書的觀念：**電腦裡的一切資訊，都是一串位元（bit），意義完全取決於你用什麼方式解讀它。**

**位元**（bit）是只能是 0 或 1 的最小資訊單位；8 個位元組成一個 **位元組**（byte），可以表示 0 到 255 的 256 種值。我們的 `hello.c` 存在磁碟上，就是一串位元組。用 `xxd` 把它的前 48 個 byte 以十六進位印出來：

```text
00000000: 2369 6e63 6c75 6465 203c 7374 6469 6f2e  #include <stdio.
00000010: 683e 0a0a 696e 7420 6d61 696e 2876 6f69  h>..int main(voi
00000020: 6429 207b 0a20 2020 2070 7269 6e74 6628  d) {.    printf(
```

左邊是位移，中間是每個 byte 的十六進位值，右邊是把這些值當成 **ASCII** 字元（一種把 0–127 對應到英文字母、數字與符號的編碼）來解讀的結果。`0x23` 是 `#`、`0x69` 是 `i`、`0x0a` 是換行。只由這類可印出字元組成的檔案叫**文字檔**（text file），其他的都叫**二進位檔**（binary file）。

同一個 byte `0x23`，當成 ASCII 是 `#`，當成無號整數是 35，放在一段機器碼裡可能是某條指令的一部分。位元本身沒有型別，是程式「決定怎麼讀它」才賦予意義。這個觀念聽起來很抽象，但它是很多 bug 的根源：把網路上收到的 4 個 byte 用錯的順序解讀成整數（第 3 章）、把一個很大的無號數解讀成負數（第 4 章）、把一塊已經釋放的記憶體當成還有效的 struct（第 26 章），本質上都是「解讀錯了」。

| 同一串位元 | 用這種方式解讀 | 得到 | 本書哪一章 |
|---|---|---|---|
| `0x41` | ASCII 字元 | `A` | 第 3 章 |
| `0x41` | 8-bit 無號整數 | 65 | 第 4 章 |
| `0xFFFFFFFF` | 32-bit 無號整數 | 4,294,967,295 | 第 4 章 |
| `0xFFFFFFFF` | 32-bit 二補數整數 | −1 | 第 4 章 |
| `0x3F800000` | IEEE 754 單精度浮點數 | 1.0 | 第 6 章 |
| `0xC3` | x86-64 機器碼 | `ret` 指令 | 第 7 章 |

## 1.3 從原始碼到可執行檔：四個階段

回到 `hello.c`：

```c
#include <stdio.h>

int main(void) {
    printf("hello, world\n");
    return 0;
}
```

CPU 看不懂這段文字。它只能執行**機器碼**（machine code）：一串依照特定規格編碼的位元組，每幾個 byte 代表一條指令，例如「把這個值放進暫存器」「呼叫那個位址的函式」。把 C 文字變成機器碼的工作，由一整組工具分工完成。平常我們只打一行 `cc hello.c -o hello`，但 `cc` 其實是一個 **compiler driver**（編譯器驅動程式）：它依序呼叫四個工具，每一個的輸出是下一個的輸入。

```text
 hello.c ──▶ ① preprocessor ──▶ hello.i ──▶ ② compiler ──▶ hello.s
 (C 原始碼)     (cpp)            (展開後的 C)     (cc1/clang)    (組合語言文字)
                                                                  │
                                                                  ▼
 hello   ◀── ④ linker ◀── hello.o ＋ libc ◀── ③ assembler ◀──────┘
 (可執行檔)     (ld)        (可重定位目的檔)        (as)
```

**① Preprocess（前處理）**：處理所有 `#` 開頭的指令。`#include <stdio.h>` 會被替換成整個 `stdio.h` 檔案的內容，`#define` 定義的巨集會被展開，`#ifdef` 會決定哪些程式碼留下。結果仍然是 C 文字，只是變長了。用 `cc -E hello.c -o hello.i` 只做這一步。在這台 macOS 上，6 行的 `hello.c` 展開後變成 572 行，裡面多了 `printf` 的宣告：

```text
int printf(const char * restrict, ...) __attribute__((__format__ (__printf__, 1, 2)));
```

**② Compile（編譯）**：把展開後的 C 翻譯成**組合語言**（assembly language），也就是機器碼的文字版，每一行大致對應一條指令。`cc -S` 只做到這一步。下面是用 `clang -E` 展開後，再以 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - hello.i` 產生的 x86-64 組合語言（刪去了部分 directive）：

```asm
main:
	pushq	%rax
	leaq	.Lstr(%rip), %rdi
	callq	puts@PLT
	xorl	%eax, %eax
	popq	%rcx
	retq
	.section	.rodata.str1.1,"aMS",@progbits,1
.Lstr:
	.asciz	"hello, world"
```

這裡已經可以看到幾件有意思的事。編譯器把 `printf("hello, world\n")` 換成了 `puts("hello, world")`：因為字串裡沒有格式符號，而 `puts` 本身就會補換行，結果完全相同但比較快。`leaq .Lstr(%rip), %rdi` 把字串的位址放進 `%rdi` 暫存器，這是 x86-64 Linux 傳遞第一個參數的固定位置（第 9 章）。`xorl %eax, %eax` 把 `%eax` 清成 0，就是 `return 0`。現在看不懂每一行沒關係，第 7 到 9 章會逐行講。

**③ Assemble（組譯）**：assembler 把組合語言翻成真正的機器碼位元組，包成一個**可重定位目的檔**（relocatable object file，`.o`）。「可重定位」的意思是：它裡面的程式碼還不知道自己最後會被放在哪個位址，也還不知道 `puts` 在哪裡。用 `objdump -d` 反組譯這個 `.o`：

```text
0000000000000000 <main>:
       0: 50                           	pushq	%rax
       1: 48 8d 3d 00 00 00 00         	leaq	(%rip), %rdi
       8: e8 00 00 00 00               	callq	0xd <main+0xd>
       d: 31 c0                        	xorl	%eax, %eax
       f: 59                           	popq	%rcx
      10: c3                           	retq
```

中間那欄就是機器碼：`main` 一共 17 個 byte，`c3` 就是 1.2 節表格裡的 `ret`。注意 `callq` 後面是 `e8 00 00 00 00`，目標位址全是 0：assembler 不知道 `puts` 在哪，只好先填 0，並在檔案裡留下一筆「之後要回來補」的紀錄，叫 **relocation entry**（重定位項目）。用 `objdump -r` 可以看到它：

```text
OFFSET           TYPE                     VALUE
0000000000000004 R_X86_64_PC32            .Lstr-0x4
0000000000000009 R_X86_64_PLT32           puts-0x4
```

`nm` 列出這個檔案的符號，`U` 表示「用到了但這裡沒定義」：

```text
0000000000000000 r .Lstr
0000000000000000 T main
                 U puts
```

**④ Link（連結）**：linker 把一個或多個 `.o` 和函式庫（這裡是 C 標準函式庫 libc）合併成可執行檔。它做兩件主要的工作：**符號解析**（symbol resolution），替每個 `U` 找到唯一的定義；以及 **relocation**（重定位），決定每段程式碼與資料的最終位址，再回頭把那些填 0 的洞補上。`puts` 在 libc 裡，而 libc 通常是**動態連結**的 shared library，真正的位址要等程式載入時才決定（第 19 章）。

現在回頭看小安的錯誤就清楚了：`http.o` 裡 `thumb_version` 是 `U`，而所有被送進 linker 的 `.o` 與函式庫裡都沒有它的定義，linker 只好放棄。編譯器沒有抱怨，是因為編譯 `http.c` 時只需要宣告（知道函式長什麼樣），不需要本體。

| 階段 | 輸入 → 輸出 | 單獨執行的指令 | 這一階段典型的錯誤訊息 | 詳細在 |
|---|---|---|---|---|
| preprocess | `.c` → `.i` | `cc -E` | `fatal error: 'foo.h' file not found` | 第 2 章 |
| compile | `.i` → `.s` | `cc -S` | `error: use of undeclared identifier`、型別不符 | 第 2、7 章 |
| assemble | `.s` → `.o` | `cc -c` | 手寫組合語言才會遇到，例如不合法的指令 | 第 7 章 |
| link | `.o` ＋ 函式庫 → 可執行檔 | `cc a.o b.o -o prog` | `undefined reference`、`multiple definition` | 第 18、19 章 |

> [!warning] 常見誤解
> 「編譯成功就代表程式寫對了。」編譯只保證每個 `.c` 單獨看起來合法。函式有沒有本體、同一個名字有沒有被定義兩次，要到連結時才知道；邏輯對不對，要到執行時才知道。看到錯誤訊息時，先判斷它出自哪個階段，就已經解決了一半。

> [!note]
> 為什麼要拆成這麼多階段？最大的好處是**分別編譯**：大型專案有幾千個 `.c`，改了一個檔案，只要重新編譯那一個 `.o`，再重新連結即可，不必全部重來。`make` 這類建置工具就是根據檔案的修改時間決定哪些 `.o` 要重建。

## 1.4 硬體的組成：CPU、記憶體、匯流排與 I/O

`hello` 這個可執行檔現在躺在磁碟上。要讓它執行，先要知道它要在什麼樣的機器上跑。一台典型電腦的硬體可以畫成這樣：

```text
 ┌──────────────── CPU 晶片 ─────────────────┐
 │  ┌────────────┐                           │
 │  │ register   │   PC（下一條指令的位址）   │
 │  │ file       │                           │
 │  └─────┬──────┘                           │
 │        │      ┌─────┐                     │
 │        └─────▶│ ALU │  ┌──────────────┐   │
 │               └─────┘  │ L1/L2/L3     │   │
 │                        │ cache        │   │
 │  ┌────────────────┐    └──────┬───────┘   │
 │  │ bus interface  │◀──────────┘           │
 │  └───────┬────────┘                       │
 └──────────┼────────────────────────────────┘
            │ system bus
     ┌──────┴───────┐   memory bus   ┌────────────────┐
     │ I/O bridge   │◀──────────────▶│ main memory    │
     └──────┬───────┘                │ (DRAM)         │
            │ I/O bus                └────────────────┘
  ┌─────────┼───────────┬──────────────┬──────────────┐
  ▼         ▼           ▼              ▼              ▼
 USB      顯示卡     SSD／HDD 控制器   網路卡         其他裝置
 鍵盤滑鼠  螢幕       （hello 在這裡）  （thumbd 的請求從這裡進來）
```

**CPU**（central processing unit，中央處理器）是執行指令的引擎。它裡面有幾個本章需要知道的部件：

- **PC**（program counter，程式計數器）：一個存著「下一條要執行的指令在哪個位址」的暫存器。x86-64 上叫 `%rip`。
- **Register file**（暫存器檔）：一小組速度最快的儲存格，x86-64 有 16 個 64-bit 的通用暫存器，例如 `%rax`、`%rdi`。所有計算都在暫存器上進行。
- **ALU**（arithmetic/logic unit，算術邏輯單元）：做加減、位元運算、比較的電路。

CPU 的工作從開機到關機只有一個循環：**從 PC 指向的位址讀一條指令、解碼、執行、更新 PC 指向下一條**，然後重複。指令能做的事其實很少，大致就是四類：從記憶體**載入**（load）資料到暫存器、把暫存器**存回**（store）記憶體、對暫存器做**運算**、以及**跳躍**（改變 PC，實作 if、迴圈與函式呼叫）。所有高階語言的功能，最後都由這四類指令組合出來。第 12、13 章會看到這個循環在電路層面怎麼實作，以及現代 CPU 怎麼同時處理很多條指令。

**Main memory**（主記憶體）是一大片 **DRAM**（dynamic random access memory），可以想成一個巨大的 byte 陣列，每個 byte 有一個編號，叫**位址**（address）。程式執行時，它的指令與資料都放在這裡。

**Bus**（匯流排）是在元件之間搬運資料的電線，每次搬固定大小的一塊，叫一個 **word**。在 64-bit 系統上，word 是 8 bytes。（這裡的 word 指機器的 word size；x86 組合語言因為歷史因素，把 2 bytes 叫 word、8 bytes 叫 quad word，第 7 章會說明。）**I/O 裝置**（輸入輸出裝置）是電腦和外界的連接：鍵盤、螢幕、磁碟、網路卡。每個裝置透過一個**控制器**（controller）或**介面卡**（adapter）接到 I/O bus 上。

把這些部件放在一起，`./hello` 執行時資料是這樣流動的：

```text
 步驟                          資料的路徑
 ─────────────────────────────────────────────────────────────────
 ① 你在 shell 打 ./hello      鍵盤 → I/O bus → CPU 暫存器 → 記憶體
 ② shell 請 OS 載入 hello     磁碟 ──DMA──▶ 記憶體（不經過 CPU）
 ③ CPU 執行 main 的指令       記憶體 → cache → CPU（取指令與資料）
 ④ 字串 "hello, world\n"      記憶體 → CPU → I/O bus → 顯示裝置
```

步驟 ② 有一個重要的細節：從磁碟搬資料到記憶體時，CPU 不必一個 byte 一個 byte 地搬，而是交給磁碟控制器用 **DMA**（direct memory access，直接記憶體存取）直接寫進記憶體，搬完再通知 CPU。這讓 CPU 在等磁碟的期間可以去做別的事。`thumbd` 讀原圖檔、網路卡收到 HTTP 請求，都是用 DMA 進到記憶體的。

> [!example] 例子
> 這張圖也說明了一件工作上常被忽略的事：**資料被搬來搬去的成本，常常比計算本身還高**。`hello` 的機器碼從磁碟複製到記憶體、再從記憶體複製到 CPU；字串從記憶體複製到 CPU、再複製到顯示裝置。系統設計的很大一部分心力，都花在讓這些搬運變快，或乾脆避免搬運。

## 1.5 Cache 與記憶體階層：為什麼走訪順序會差十倍

1.4 節的圖裡，CPU 晶片上有一塊叫 cache 的東西。它存在的理由，是一個殘酷的物理事實：**CPU 算得很快，但從 DRAM 拿資料很慢**。一個 3 GHz 的 CPU 每個 cycle 只有約 0.33 ns，而從 DRAM 讀一筆資料約要 100 ns，相當於好幾百個 cycle 什麼事都不能做。而且更大的儲存裝置一定更慢、每 byte 更便宜；更快的一定更小、更貴。

解法是在 CPU 與 DRAM 之間放幾層又小又快的 **SRAM**（static RAM）做成的 **cache**（快取記憶體）。Cache 保存最近用過的資料的複本；CPU 要讀一個位址時，先去 cache 找，找到了叫 **cache hit**（命中），只要幾個 cycle；找不到叫 **cache miss**（失誤），才去下一層拿，並順便把附近的資料一起搬上來。把所有層次疊起來，就是**記憶體階層**（memory hierarchy）：

```text
                    ▲ 更快、更小、每 byte 更貴
                 ┌──┴──┐
          L0     │ 暫存器 │   數百 bytes
               ┌─┴──────┴─┐
          L1   │ L1 cache │   每核數十 KiB
             ┌─┴──────────┴─┐
          L2 │   L2 cache   │   數百 KiB 到數 MiB
           ┌─┴──────────────┴─┐
        L3 │     L3 cache     │   數 MiB 到上百 MiB，多核共享
         ┌─┴──────────────────┴─┐
      L4 │    主記憶體（DRAM）    │   數 GiB 到數 TiB
       ┌─┴──────────────────────┴─┐
    L5 │   本機磁碟（SSD／HDD）     │   數百 GiB 到數十 TiB
     ┌─┴──────────────────────────┴─┐
  L6 │ 遠端儲存（網路檔案系統、物件儲存）│
     └──────────────────────────────┘
                    ▼ 更慢、更大、每 byte 更便宜
```

每一層都是下一層的快取：L1 快取 L2 的資料，DRAM 快取磁碟的資料（這就是第 23 章的虛擬記憶體），本機磁碟快取遠端儲存的資料。各層的速度差距大到需要用數量級來記：

| 層次 | 典型延遲（量級） | 如果把 1 ns 放大成 1 秒 |
|---|---|---|
| 暫存器 | 不到 1 ns | 不到 1 秒 |
| L1 cache | 約 1 ns | 1 秒 |
| L2 cache | 約數 ns | 數秒 |
| L3 cache | 約十多 ns | 十多秒 |
| DRAM | 約 100 ns | 約 1.5 分鐘 |
| SSD 隨機讀 | 約數十到上百 µs | 約半天到一天 |
| HDD seek | 約數 ms | 約兩個月 |

這些數字依硬體不同而有差異，但數量級是穩定的，值得背下來（附錄 A 有完整速查表）。

Cache 之所以有效，靠的是程式的 **locality**（區域性）：程式傾向重複使用最近用過的資料（**temporal locality**，時間區域性，例如迴圈裡的計數器），也傾向使用位址相鄰的資料（**spatial locality**，空間區域性，例如依序走訪陣列）。Cache 每次從 DRAM 搬上來的是一整塊，叫 **cache line**（x86-64 上是 64 bytes，Apple Silicon 是 128 bytes）。以 64 bytes 為例，依序走訪 `int` 陣列時，讀第一個元素付出一次 miss，同一塊裡接下來 15 個 `int` 都是 hit。

這不只是理論。1.10 節的動手做會量測：同樣把一張 4096 × 4096 的影像所有像素加總，一列一列走和一行一行走，在這台 Apple Silicon 筆電上差了約 10 倍。兩段程式的運算次數完全一樣，差別只在走訪順序是否符合 spatial locality。`thumbd` 的影像旋轉就曾經栽在這裡（第 17 章）。第 15 到 17 章會完整講 cache 的組織，以及怎麼寫出 cache-friendly 的程式。

> [!warning] 常見誤解
> 「演算法複雜度一樣，執行時間就差不多。」Big-O 只數運算次數，不數 cache miss。兩個 O(n²) 的迴圈，可能因為存取模式不同而差上一個數量級。效能分析時要同時考慮「做了多少事」與「資料從哪一層來」。

## 1.6 作業系統：三個抽象

`hello` 從頭到尾沒有直接碰過鍵盤、磁碟、螢幕或記憶體晶片。它只呼叫了 `puts`，`puts` 再請**作業系統**（operating system，OS）代為輸出。作業系統是夾在應用程式與硬體之間的一層軟體，它有兩個目的：保護硬體不被失控的程式濫用，以及提供簡單一致的介面，讓程式不必知道各種硬體的細節。

作業系統裡永遠常駐在記憶體、擁有最高權限的那一部分叫 **kernel**（作業系統核心）。應用程式要做任何需要特權的事（讀檔、送網路封包、要更多記憶體、建立新程式），都必須透過 **system call**（系統呼叫）這個受控的入口，請 kernel 代辦。`hello` 最後印出字串，就是 libc 替它呼叫了 `write` 這個 system call。

作業系統用三個抽象把硬體包起來：

```text
 ┌────────────────────────── process ─────────────────────────┐
 │                                                            │
 │   ┌─────────────── virtual memory ───────────────┐         │
 │   │                                              │         │
 │   │       ┌──────── file ────────┐               │         │
 │   │       │                      │               │         │
 │   │       │   I/O 裝置           │  主記憶體      │  CPU    │
 │   │       └──────────────────────┘               │         │
 │   └──────────────────────────────────────────────┘         │
 └────────────────────────────────────────────────────────────┘
```

這張圖的意思是：**file** 是 I/O 裝置的抽象；**virtual memory** 是主記憶體加上 I/O 裝置（磁碟）的抽象；**process** 是 CPU、主記憶體與 I/O 裝置三者合起來的抽象。

### Process：一支正在執行的程式

**Process**（行程）是作業系統對「一支正在執行的程式」的抽象。它讓每支程式都以為自己獨佔了 CPU、記憶體與 I/O 裝置。你同時開著瀏覽器、編輯器和終端機，機器卻可能只有幾個 CPU 核心，作業系統靠著在 process 之間快速切換製造這個假象。

切換的動作叫 **context switch**（上下文切換）。每個 process 的「目前狀態」包括 PC、暫存器的值、記憶體內容等，統稱 **context**。作業系統決定換人時，把目前 process 的 context 存起來，載入另一個 process 的 context，CPU 就從後者上次停下的地方繼續執行：

```text
 時間 ──────────────────────────────────────────────────────▶

 shell    ████████│                         │████████
                  │ ← context switch        │ ← context switch
 hello            │████████│ read 磁碟…│█████│
                  │        │(等待)     │     │
 kernel        ▲  ▲        ▲          ▲     ▲
               └──┴─ 每次切換都要經過 kernel ┘
```

可執行檔和 process 是兩件事：`hello` 是磁碟上的一個檔案，執行它三次就產生三個 process，各自有自己的狀態。這個區別在工作上很重要：部署時你換掉的是檔案，正在執行的 process 仍然是舊版程式，必須重啟才會生效。第 20 到 22 章會詳細講 process、`fork`／`exec` 與 signal。

一個 process 裡可以有多個 **thread**（執行緒）。同一個 process 的 thread 共享程式碼與全域資料，但各有自己的 stack 與暫存器狀態。`thumbd` 用一個 thread pool 同時處理多個請求，thread 之間共享縮圖快取，這帶來效率，也帶來 race condition（第 30 到 32 章）。

### Virtual memory：每個 process 都以為自己獨佔記憶體

**Virtual memory**（虛擬記憶體）讓每個 process 都看到一份一模一樣、獨立的**虛擬位址空間**（virtual address space）。在 Linux x86-64 上，一個 process 的位址空間由低到高大致是：

```text
 高位址
 ┌──────────────────────────┐
 │ kernel 的程式碼與資料      │ ← user 程式不能存取
 ├──────────────────────────┤
 │ user stack（往下長）      │ ← 區域變數、函式呼叫
 │            ↓              │
 │                           │
 │ shared library（libc 等） │ ← 動態連結的函式庫
 │                           │
 │            ↑              │
 │ heap（往上長）            │ ← malloc 配置的記憶體
 ├──────────────────────────┤
 │ .data／.bss（全域變數）   │ ┐
 │ .rodata（唯讀資料）       │ ├ 從可執行檔載入
 │ .text（程式碼）           │ ┘
 └──────────────────────────┘
 低位址
```

每個 process 看到的配置都一樣，所以 linker 可以假設程式碼總是從某個固定區域開始；而硬體與 kernel 會在背後把每個虛擬位址翻譯成真正的實體記憶體位置，不同 process 的同一個虛擬位址對到不同的實體位置，互不干擾。1.10 節的程式會把 `main`、全域變數、heap 與 stack 的位址印出來，你會看到它們確實依這個順序分布。第 23 到 26 章會講翻譯機制、`mmap`、`malloc` 與記憶體錯誤。

### File：一切都是位元組序列

**File**（檔案）在 Unix 的意義比「磁碟上的文件」廣得多：它就是一串位元組。磁碟上的檔案、終端機、網路連線、pipe，甚至部分硬體裝置，都用同一組 system call（`open`、`read`、`write`、`close`）操作。`hello` 印字串時用的 `write(1, ...)`，那個 `1` 是**標準輸出**的 file descriptor；不管標準輸出接的是螢幕、檔案（`./hello > out.txt`）還是另一支程式（`./hello | wc`），`hello` 的程式碼都不用改。

網路也是這個抽象的延伸：從單一機器的角度看，網路只是另一個 I/O 裝置，`thumbd` 從網路卡收請求、把縮圖寫回去，用的也是 `read` 與 `write`。第 27 章講 Unix I/O，第 28、29 章講 socket 與 web server。

| 抽象 | 包住了哪些硬體 | 讓程式以為 | 本書章節 |
|---|---|---|---|
| process | CPU、記憶體、I/O | 自己獨佔整台機器 | 第 20–22 章 |
| virtual memory | 主記憶體、磁碟 | 有一大片連續、私有的記憶體 | 第 23–26 章 |
| file | 所有 I/O 裝置 | 所有輸入輸出都是位元組序列 | 第 27–29 章 |

## 1.7 並行與平行：讓電腦同時做更多事

最後一個全景主題是「同時」。日常用語裡「同時做很多事」在系統裡有兩個不同的詞：

- **Concurrency**（並行）：系統裡有多個活動「在同一段時間內都在進行中」，不一定真的在同一瞬間執行。單核 CPU 靠 context switch 輪流執行多個 process，就是並行。
- **Parallelism**（平行）：多個活動「在同一瞬間真的一起執行」，需要多份硬體。多核 CPU 讓兩個 thread 各用一個核心，就是平行。

並行是程式的結構（「我有很多件事要處理」），平行是執行的方式（「我有很多套硬體可以一起處理」）。電腦系統在三個層次上利用平行：

**Thread-level parallelism（執行緒層級）**。現代 CPU 晶片裡有多個**核心**（core），每個核心通常有自己的 L1 cache，L2 依設計可能每核一份或幾個核心共用，L3 與記憶體則由所有核心共享。有些 CPU 還支援 **SMT**（simultaneous multithreading，同時多執行緒，Intel 的產品名稱叫 hyperthreading），讓一個核心同時保有兩個 thread 的狀態，一個 thread 在等記憶體時另一個可以用運算單元。`thumbd` 的 thread pool 就是在這個層次取得平行。

**Instruction-level parallelism（指令層級）**。即使只有一個 thread，現代 CPU 也會同時處理很多條指令：用 **pipeline**（管線）把一條指令拆成多個階段，讓不同指令的不同階段重疊；**超純量**（superscalar）處理器每個 cycle 可以發出多條指令；還會在不改變結果的前提下**亂序執行**（out-of-order）。這些都是硬體自動做的，但程式怎麼寫會影響它能抓到多少平行（第 13、14 章）。

**SIMD（單指令多資料）**。一條指令同時處理多筆資料，例如一次把 8 對 32-bit 整數相加。x86-64 的 SSE／AVX 與 ARM 的 NEON 都是 SIMD 指令集。影像處理是 SIMD 的典型用途：`thumbd` 縮放時，每個像素做的運算都一樣，非常適合一次處理一整排像素（第 14 章）。

```text
 thread-level：           ILP（一個核心內）：          SIMD（一條指令）：
 core0  ██ req A ██        cycle  1  2  3  4  5         ┌──┬──┬──┬──┐
 core1  ██ req B ██        add    F  D  E  W            │a0│a1│a2│a3│
 core2  ██ req C ██        mul       F  D  E  W         └──┴──┴──┴──┘
 core3  ██ req D ██        load         F  D  E  W          ＋  一次
 四個請求真的同時處理        不同指令的不同階段重疊       ┌──┬──┬──┬──┐
                                                       │b0│b1│b2│b3│
                                                       └──┴──┴──┴──┘
```

| 層次 | 平行的單位 | 誰負責 | 程式設計師要做什麼 | 本書章節 |
|---|---|---|---|---|
| thread-level | thread／process | OS ＋ 多核硬體 | 拆分工作、處理同步與共享資料 | 第 30–32 章 |
| instruction-level | 指令 | CPU 硬體 | 減少資料相依、讓分支好預測 | 第 13–14 章 |
| SIMD | 資料元素 | 編譯器或手寫 intrinsic | 讓資料連續、迴圈簡單，方便編譯器向量化 | 第 14 章 |

## 1.8 Amdahl's law：最佳化的天花板

知道了這麼多加速手段，自然會想：把 `thumbd` 的某個部分加速 10 倍，整體會快多少？答案常常令人失望，原因由 **Amdahl's law**（阿姆達爾定律）描述。

假設一個工作原本花時間 T_old，其中比例 α 的部分被加速 k 倍，其他部分不變。新的時間是：

```text
T_new = (1 − α) × T_old + (α × T_old) / k
      = T_old × [(1 − α) + α / k]

整體加速比 S = T_old / T_new = 1 / [(1 − α) + α / k]
```

推導只是把時間拆成「沒被加速的部分」與「被加速的部分」兩段相加。關鍵在於 (1 − α) 這一項：無論 k 多大，它都不會變小。當 k 趨近無限大，S 的上限是 1 / (1 − α)。

用 `thumbd` 手算一次。假設老周在早期版本用 profiler 量到處理一張圖的時間分布是（第 14 章會看到後來 production 上實際量到的 profile，比例略有不同）：讀檔與解碼 50%、縮放 30%、編碼輸出 15%、HTTP 與其他 5%。小安想用 SIMD 把縮放加速 4 倍：

```text
α = 0.30，k = 4
S = 1 / [(1 − 0.30) + 0.30 / 4]
  = 1 / [0.70 + 0.075]
  = 1 / 0.775
  ≈ 1.29
```

縮放快了 4 倍，整體只快 29%。就算縮放變成零時間，上限也只是 1 / 0.70 ≈ 1.43 倍。反過來，如果把佔 50% 的解碼加速 2 倍，S = 1 / (0.5 + 0.25) ≈ 1.33，反而比縮放快 4 倍還划算。

| 被加速的部分 | α | k | 整體加速比 S | 上限 1 / (1 − α) |
|---|---|---|---|---|
| 縮放 | 0.30 | 4 | 1.29 | 1.43 |
| 解碼 | 0.50 | 2 | 1.33 | 2.00 |
| HTTP 與其他 | 0.05 | 100 | 約 1.05 | 1.05 |
| 全部（例如換更快的 CPU） | 1.00 | 1.5 | 1.50 | 無上限 |

Amdahl's law 在工作上的教訓有兩條。第一，**先量測再最佳化**：不知道時間花在哪，就可能把力氣花在只佔 5% 的部分（第 14 章會用 `perf` 量測）。第二，**平行化也受它限制**：如果程式有 10% 必須依序執行（例如排隊拿同一把鎖），那麼用再多核心，整體最多快 10 倍（第 32 章）。

## 1.9 全書地圖：拾光相簿與 `thumbd`

本書每一章都從拾光相簿的縮圖服務 `thumbd` 遇到的一個真實問題開場。先認識一下它的架構：

```text
 使用者 ─HTTP→ nginx ─HTTP→ thumbd（C，thread pool）
                              ├─ 解析 HTTP request（第 28–29 章）
                              ├─ 讀原圖檔（mmap／read，第 24、27 章）
                              ├─ 解碼（libjpeg／libpng，動態連結，第 19 章）
                              ├─ 縮放、旋轉（像素矩陣運算，第 14、17 章）
                              ├─ 快取縮圖（malloc／free，第 25–26 章）
                              └─ 回傳結果；少數格式用 fork/exec 呼叫外部工具（第 21 章）
```

使用者在 app 上點開相簿，前端要的是 320 像素寬的縮圖。請求先到 nginx，nginx 轉給 `thumbd`。`thumbd` 是用 C 寫的長駐服務，一個 thread pool 裡的 worker 接下請求後，讀原圖、呼叫 libjpeg 或 libpng 解碼成像素矩陣、縮放、再編碼回 JPEG，把結果放進記憶體快取並回傳。少數冷門格式則用 `fork`／`exec` 呼叫外部轉檔工具處理。

故事裡的人物：**小安**是剛入職的初階後端工程師，熟悉 Python 與 Java，C 只在大學學過；**老周**是資深系統工程師，`thumbd` 的原作者之一，小安的 mentor；有時還會出現 SRE **阿哲**與產品經理 **Lisa**。

全書分成 11 個 Part。除了 Part 0 的工具箱（先備知識）與 Part 10 的整合應用，每個 Part 大致對應 CS:APP 3e 的一到兩章，也對應 `thumbd` 的一類問題：

| Part | 章 | 主題 | `thumbd` 會遇到的問題 | 對應 CS:APP 3e |
|---|---|---|---|---|
| 0 起點 | 1–2 | 全景與工具箱 | 漏了一個 `.o` 造成 link error；長路徑讓 `sprintf` 寫爆 stack 上的 cache key | ch1（第 2 章為先備） |
| 1 資訊的表示 | 3–6 | 位元、整數、浮點數 | PNG header 的 byte order 讀錯；`char` 有沒有號讓 JPEG 檔頭判斷在 x86-64 失效；寬 × 高 × 4 溢位造成 heap overflow；縮圖高度算成 299、x86-64 與 ARM64 的像素差 1 | ch2 |
| 2 機器級程式 | 7–11 | 組合語言、控制流程、stack、struct、記憶體安全 | 在 core dump 裡讀組合語言；夜景照片讓迴圈慢十倍；遞迴解析 TIFF 撐爆 worker thread 的 stack；BMP 檔頭與快取 metadata 的 padding；過長的 EXIF 欄位觸發 stack canary | ch3 |
| 3 處理器與效能 | 12–14 | 處理器、pipeline、最佳化 | `-march=native` 編出的 binary 在舊機器上 SIGILL；真實貼紙讓分支預測失準；縮放迴圈拖高 CPU 帳單 | ch4、ch5 |
| 4 記憶體階層 | 15–17 | 儲存、cache | 批次重建縮圖卡在硬碟 seek；寬 4096 的全景照 conflict miss；4096 × 4096 的直拍照片旋轉特別慢 | ch6 |
| 5 連結 | 18–19 | 目的檔、動態連結 | static library 連結順序造成 undefined reference；換了 base image 後載入到另一份 libjpeg 而當機 | ch7 |
| 6 例外控制流 | 20–22 | exception、process、signal | 每次 `read` 1 byte 讓 kernel 時間暴增；呼叫外部工具留下 zombie；SIGHUP 讓服務每天凌晨重啟 | ch8 |
| 7 虛擬記憶體 | 23–26 | 位址轉譯、mmap、malloc、記憶體錯誤 | VIRT 30 GB；大圖整檔讀進 heap 引來 OOM killer；`free` 之後 RSS 不降；memory leak 讓 RSS 每天上升 | ch9 |
| 8 I/O 與網路 | 27–29 | Unix I/O、socket、HTTP | 寫檔漏掉 short write；TCP 只讀到半段 JSON、重啟時 `Address already in use`；`..` 造成 path traversal | ch10、ch11 |
| 9 並行程式設計 | 30–32 | 並行模型、同步、效能 | 一張全景照卡住 iterative server；快取計數器的 race；加 thread 反而變慢 | ch12 |
| 10 整合應用 | 33–34 | 跨層診斷、Labs | 六個 production 事件從症狀追到根因；用 Labs 帶新同事入門 | 全書 |

建議的讀法是依序讀。Part 1 到 Part 2 是後面所有內容的基礎：不懂整數表示，就看不懂組合語言裡的位元運算；不懂 stack frame，就看不懂 core dump。之後的 Part 3 到 Part 9 相依性較低，可以依工作需要調整順序，例如做效能工作的人先讀 Part 3、4，做後端服務的人先讀 Part 6、8、9。跳讀時要注意少數依賴，例如第 23 章需要第 15、16 章的 cache 概念，第 32 章需要第 16、17 章；附錄 D 畫出了完整的章節依賴圖，並依背景與目標整理了讀書路線。

## 1.10 動手做：追蹤 `hello` 的一生

這一節用三段程式，把本章的三個重點變成看得見的證據：編譯的各個階段、process 的記憶體配置、以及 cache 對效能的影響。最後用一段 Python 練習 Amdahl's law。

### 實驗一：自己跑一次四個階段

在任何裝了 gcc 或 clang 的機器上，把 1.3 節的 `hello.c` 存檔，一步一步執行：

```bash
cc -E hello.c -o hello.i     # ① 只做前處理
wc -l hello.i                # 看看 #include 帶進來多少東西
cc -S -O1 hello.c            # ② 編譯成組合語言 hello.s
cc -c -O1 hello.c            # ③ 組譯成目的檔 hello.o
nm hello.o                   # 看符號：main 是 T（有定義），puts 是 U（未定義）
cc hello.o -o hello          # ④ 連結
file hello.o hello           # 兩者的檔案類型不同
./hello
```

在這台 macOS arm64 上，`file` 的輸出是：

```text
hello.o: Mach-O 64-bit object arm64
hello:   Mach-O 64-bit executable arm64
```

macOS 的目的檔格式叫 **Mach-O**，Linux 用的則是 **ELF**（executable and linkable format）；1.3 節用 `-target x86_64-linux-gnu` 產生的 `.o`，`file` 會顯示 `ELF 64-bit LSB relocatable, x86-64`。格式不同，但「relocatable object 還有洞、executable 已經補好」的概念完全相同。本書的組合語言一律用 x86-64 Linux，因為它是 CS:APP 的主角，也是大多數伺服器的環境；你的筆電如果是 Apple Silicon，用 `-target x86_64-linux-gnu -S` 一樣可以產生（第 7 章會說明）。同一個 `hello.c` 在 ARM64 macOS 上原生編譯的組合語言長這樣（`clang -O1 -S -o - hello.c`，刪去 directive）：

```text
_main:
	stp	x29, x30, [sp, #-16]!
	mov	x29, sp
	adrp	x0, l_str@PAGE
	add	x0, x0, l_str@PAGEOFF
	bl	_puts
	mov	w0, #0
	ldp	x29, x30, [sp], #16
	ret
```

指令的名字和暫存器不同（`bl` 對應 `call`、`x0` 對應 `%rdi`），但結構一樣：準備參數、呼叫 `puts`、把回傳值設為 0、返回。這就是 1.4 節說的「指令能做的事只有少數幾類」。

### 實驗二：process 的記憶體長什麼樣

下面的程式把程式碼、唯讀資料、全域變數、heap 與 stack 上各一個東西的位址印出來，驗證 1.6 節的位址空間圖：

```c
#include <stdio.h>
#include <stdlib.h>

int counter = 42;                   /* 有初始值的全域變數：放在 .data */
int zeroed[1024];                   /* 沒有初始值的全域變數：放在 .bss */
const char banner[] = "thumbd v1";  /* 唯讀資料：放在 .rodata（macOS 叫 __const） */

static void where(const char *region, const char *name, const void *addr) {
    printf("%-8s %-8s %p\n", region, name, addr);
}

int main(void) {
    int local = 7;                  /* 區域變數：放在 stack */
    char *buf = malloc(64);         /* 動態配置：放在 heap */
    if (buf == NULL) return 1;

    where("code", "main", (const void *)&main);
    where("rodata", "banner", (const void *)banner);
    where("data", "counter", (const void *)&counter);
    where("bss", "zeroed", (const void *)zeroed);
    where("heap", "buf", (const void *)buf);
    where("stack", "local", (const void *)&local);
    free(buf);
    return 0;
}
```

在 macOS arm64 上用 `cc -std=c17 -O1 -Wall -Wextra` 編譯，連續執行兩次：

```text
code     main     0x104ec0598
rodata   banner   0x104ec06f4
data     counter  0x104ec8000
bss      zeroed   0x104ec8004
heap     buf      0x1054edcd0
stack    local    0x16af3d05c

code     main     0x1022bc598
rodata   banner   0x1022bc6f4
data     counter  0x1022c4000
bss      zeroed   0x1022c4004
heap     buf      0x102b0dcd0
stack    local    0x16db4105c
```

逐步解讀：

1. **順序和圖一致**：程式碼的位址最低，接著是唯讀資料、`.data`、`.bss`，heap 更高，stack 最高。`counter` 與 `zeroed` 只差 4 bytes，因為 `counter` 是一個 4-byte 的 `int`，載入後兩者在記憶體裡緊鄰（`.bss` 不佔可執行檔的空間，載入時才配置並清成 0）。
2. **程式碼與唯讀資料靠在一起**：`main` 與 `banner` 只差約 0x15c bytes，它們都是「不會被修改」的內容，通常放在同一類唯讀的區域。第 23 章會解釋為什麼對 `banner` 寫入會 segfault。
3. **heap 與 stack 離得很遠**：兩者之間留了一大片空白，讓 heap 往上長、stack 往下長時都有空間。
4. **兩次執行的位址不同，但同一區域內的相對距離一樣**：例如 `banner − main` 兩次都是 `0x15c`，`zeroed − counter` 兩次都是 4；而 heap、stack 與程式碼之間的距離每次都不同。這是 **ASLR**（address space layout randomization，位址空間配置隨機化）：每次載入時，作業系統把每一整塊區域（程式本身、heap、stack、shared library）各自隨機搬到不同的起點，讓攻擊者無法事先知道程式碼在哪（第 11 章）。所以 debug 時不要在筆記裡寫死「某變數在 0x104ec8000」，下次執行就不一樣了。

在 Linux 上跑，數字的樣子不同（例如程式碼常在 `0x55...` 開頭、stack 在 `0x7ff...` 附近），但順序與 ASLR 的行為相同。Linux 上還可以直接看 `/proc/self/maps`，第 24 章會用到。

### 實驗三：走訪順序與 cache

```c
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N 4096   /* 4096 x 4096 個 int = 64 MiB，遠大於任何一層 cache */

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(void) {
    int *img = malloc(sizeof(int) * N * N);    /* 把它想成一張灰階影像 */
    if (img == NULL) return 1;
    for (long i = 0; i < (long)N * N; i++) img[i] = (int)(i & 0xFF);

    double t0 = now_sec();
    long sum_row = 0;
    for (int r = 0; r < N; r++)          /* 一列一列走：位址連續 */
        for (int c = 0; c < N; c++)
            sum_row += img[(long)r * N + c];
    double t1 = now_sec();

    long sum_col = 0;
    for (int c = 0; c < N; c++)          /* 一行一行走：每次跳 N 個 int */
        for (int r = 0; r < N; r++)
            sum_col += img[(long)r * N + c];
    double t2 = now_sec();

    printf("%-12s sum=%ld  %6.1f ms\n", "row-major", sum_row, (t1 - t0) * 1e3);
    printf("%-12s sum=%ld  %6.1f ms\n", "column-major", sum_col, (t2 - t1) * 1e3);
    printf("兩種走法的時間比：%.1f 倍\n", (t2 - t1) / (t1 - t0));
    free(img);
    return 0;
}
```

在 Apple Silicon 的 macOS 上執行三次：

```text
row-major    sum=2139095040     5.8 ms
column-major sum=2139095040    61.1 ms
兩種走法的時間比：10.6 倍
row-major    sum=2139095040     5.7 ms
column-major sum=2139095040    61.7 ms
兩種走法的時間比：10.9 倍
row-major    sum=2139095040     5.7 ms
column-major sum=2139095040    63.0 ms
兩種走法的時間比：11.0 倍
```

逐步解讀：

1. **兩個總和完全一樣**，證明兩段迴圈做的是同一件事，加法次數都是 4096 × 4096 ≈ 1,677 萬次。
2. **時間差了約 10 倍**。C 的二維資料是一列接一列存放的（row-major，第 10 章），`img[r*N + c]` 與 `img[r*N + c + 1]` 在記憶體中相鄰。一列一列走時，cache 每搬上來一條 cache line 就能用到其中所有的 `int`（這台機器的 line 是 128 bytes，也就是 32 個 `int`）；一行一行走時，每次存取都跳過 4096 × 4 = 16 KiB，搬上來的 128 bytes 這一次只用到 4 bytes。同一條 line 要等走到下一行時才會再被用到，中間已經碰過另外 4095 條 line，它早就被擠出又小又快的 L1 cache，只能再去較慢的下一層拿；而且 16 KiB 剛好是 macOS 在 Apple Silicon 上的 page 大小，每一步都落在不同的 page，連位址轉譯的快取（TLB，第 23 章）也幫不上忙。
3. **row-major 版本還有額外的好處**：連續存取讓編譯器容易使用 SIMD 指令，硬體的 prefetcher（預取器）也能提前把下一塊搬上來。這幾個效果疊加，才有十倍的差距。
4. 具體倍數依 CPU、cache 大小與編譯選項而定，在 Linux x86-64 伺服器上跑通常也會看到數倍以上的差距。

### 實驗四：用 Python 練習 Amdahl's law

```python
# thumbd 處理一張圖的時間分布（假設值，用來練習 Amdahl's law）
stages = [
    ("decode", "讀檔與解碼", 0.50),
    ("resize", "縮放", 0.30),
    ("encode", "編碼輸出", 0.15),
    ("other", "HTTP 與其他", 0.05),
]


def speedup(p, k):
    """執行時間中比例 p 的部分加速 k 倍時，整體的加速比。"""
    return 1 / ((1 - p) + p / k)


print("stage    share   k=2    k=10   k=inf")
for key, label, p in stages:
    cols = [speedup(p, k) for k in (2, 10, float("inf"))]
    print(f"{key:<8} {p:5.0%}  " + "  ".join(f"{c:5.2f}" for c in cols) + f"   {label}")

# 反過來問：整體想快 target 倍，縮放（p = 0.30）要快幾倍？
# 由 1/target = 0.70 + 0.30/k 解出 k；如果 1/target <= 0.70 就無解
for target in (1.3, 1.5):
    rest = 1 / target - 0.70
    if rest <= 0:
        print(f"整體快 {target} 倍：只改縮放做不到（上限 {1 / 0.70:.2f} 倍）")
    else:
        print(f"整體快 {target} 倍：縮放必須快 {0.30 / rest:.1f} 倍")
```

在 macOS arm64 上用 Python 3 執行：

```text
stage    share   k=2    k=10   k=inf
decode     50%   1.33   1.82   2.00   讀檔與解碼
resize     30%   1.18   1.37   1.43   縮放
encode     15%   1.08   1.16   1.18   編碼輸出
other       5%   1.03   1.05   1.05   HTTP 與其他
整體快 1.3 倍：縮放必須快 4.3 倍
整體快 1.5 倍：只改縮放做不到（上限 1.43 倍）
```

這張表把 1.8 節的結論攤開來看：每一列由左到右，加速倍數 k 從 2 變成無限大，整體加速比很快就飽和在 1 / (1 − α)。最後兩行把問題倒過來問，這是工作上更常見的問法：「老闆要整體快 50%，只改縮放做得到嗎？」答案是做不到，必須同時處理解碼。

## 1.11 在工作上怎麼用

### 看錯誤訊息，先判斷是哪一層

建置失敗或程式出錯時，第一步不是 Google 整段錯誤訊息，而是判斷它出自哪一個階段。這決定了你該看哪裡、該找誰：

```text
 出錯了
   │
   ├─ 訊息有 "fatal error: ... file not found"、"#error"
   │     → preprocess：include 路徑（-I）、缺少開發套件（例如 libjpeg-dev）
   │
   ├─ 訊息有 "error:" 並指向 .c 檔的行號，例如型別不符、未宣告
   │     → compile：修程式碼或補 #include
   │
   ├─ 訊息來自 ld／collect2：
   │   "undefined reference"、"multiple definition"、"cannot find -ljpeg"
   │     → link：缺 .o 或函式庫、連結順序、重複定義（第 18 章）
   │
   ├─ 建置成功，執行時 "error while loading shared libraries"
   │     → 載入：找不到 .so，看 ldd 與 LD_LIBRARY_PATH（第 19 章）
   │
   └─ 執行到一半 Segmentation fault、Aborted
         → 執行期：記憶體錯誤或 signal，用 gdb 與 sanitizer（第 2、26 章）
```

小安第一天遇到的就是第三類。如果訊息是 `cannot find -ljpeg`，那是 linker 找不到 libjpeg 的函式庫檔，要安裝開發套件或加 `-L`；如果是建置成功但執行時說 `libjpeg.so.8: cannot open shared object file`，那是載入時找不到動態函式庫，問題在部署環境而不是程式碼。

### 「同一個 commit，為什麼 production 行為不一樣？」

這是後端與 SRE 很常遇到的問題。理解了編譯與載入的流程，就知道「同樣的原始碼」到「同樣的執行行為」之間還有好幾個變數。排查時依序確認：

| 檢查項目 | 為什麼會不同 | 怎麼確認 |
|---|---|---|
| 編譯器版本與選項 | `-O0` 與 `-O2` 可能讓含 undefined behavior 的程式表現不同（第 2 章） | 看建置 log 或 CI 設定；比較兩邊 binary 的 checksum |
| 連結的函式庫版本 | 靜態連結時，建置機上的版本被打包進去 | 建置環境的 lockfile 或 container image digest |
| 執行時載入的 `.so` | 動態連結時，用的是執行機器上的版本 | Linux 上 `ldd ./thumbd`、`cat /proc/PID/maps` |
| 正在執行的是不是新版 | 換了檔案但沒重啟，process 仍是舊程式 | 比較 process 啟動時間與部署時間；`ls -l /proc/PID/exe` |
| 硬體與 OS | CPU 架構、cache 大小、核心數、kernel 版本 | `uname -a`、`lscpu`、`nproc` |

### 用 `strace` 看程式和 kernel 的對話

在 Linux 上，`strace` 會列出一支程式發出的每個 system call，是理解「程式到底對作業系統做了什麼」最直接的工具。對 `hello` 執行，可以看到 1.6 節描述的整個過程（示意輸出，已大幅刪減，細節依發行版而定）：

```text
$ strace ./hello
execve("./hello", ["./hello"], 0x7ffc... /* 24 vars */) = 0
brk(NULL)                               = 0x55d0c3a2e000
openat(AT_FDCWD, "/lib/x86_64-linux-gnu/libc.so.6", O_RDONLY|O_CLOEXEC) = 3
mmap(NULL, 2170256, PROT_READ, MAP_PRIVATE|MAP_DENYWRITE, 3, 0) = 0x7f8a1c200000
close(3)                                = 0
write(1, "hello, world\n", 13)          = 13
exit_group(0)                           = ?
+++ exited with 0 +++
```

`execve` 是 shell 用來載入 `hello` 的 system call（第 21 章）；`openat` 與 `mmap` 是動態載入器在把 libc 映射進位址空間（第 19、24 章）；`write(1, ...)` 是 `puts` 最終發出的輸出，`1` 是標準輸出；`exit_group` 是 `return 0` 之後程式真正結束的方式。一支 6 行的程式背後有幾十個 system call，這也說明了為什麼「程式很小，啟動卻要幾毫秒」。

### 用 Amdahl's law 回答「這個最佳化值不值得做」

當有人提議「把 X 改寫成更快的版本」，先問兩個數字：X 佔整體時間的比例 α，以及預期能加速幾倍 k。代入 1 / [(1 − α) + α / k]，再和改寫的成本比較。在設計審查時，這個簡單的計算常常能在五分鐘內擋掉一個要花兩週、卻只能讓整體快 3% 的提案。

## 1.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| `undefined reference to 'foo'`，但程式碼裡明明有 `foo` | 定義 `foo` 的 `.c` 沒被編譯或沒被送進 linker；或函式庫順序錯 | `nm *.o \| grep foo` 看有沒有 `T foo`；看 Makefile 的物件清單 | 把檔案加入建置；函式庫放在使用它的 `.o` 後面（第 18 章） |
| `fatal error: jpeglib.h: No such file or directory` | 沒裝開發用標頭檔，或 include 路徑沒設 | 找找系統中有沒有這個檔案（`find / -name jpeglib.h`） | 安裝 `-dev`／`-devel` 套件，或加 `-I` |
| 部署後行為沒變 | 檔案換了，process 沒重啟 | 比較 process 的啟動時間與部署時間 | 重啟服務；部署流程加入版本檢查（例如 `/healthz` 回傳版本） |
| 執行時 `error while loading shared libraries` | 執行環境沒有對應版本的 `.so` | Linux 上 `ldd ./prog` 看哪個是 `not found` | 安裝函式庫、靜態連結，或調整 rpath（第 19 章） |
| 最佳化後整體幾乎沒變快 | 被最佳化的部分在總時間中佔比很小 | 先 profile 取得時間分布，套 Amdahl's law | 找佔比最大的部分下手 |
| 演算法一樣，換個寫法就慢很多 | 存取模式不符合 locality，cache miss 增加 | 比較走訪順序；用 `perf stat` 看 cache miss（第 17 章） | 改成連續存取，或調整資料布局 |

## 1.13 動手練習

1. **四個階段**：照 1.10 節實驗一，在你的機器上把 `hello.c` 一步一步編譯。用 `wc -l` 比較 `hello.c` 與 `hello.i` 的行數；把 `printf("hello, world\n")` 改成 `printf("hello, %d\n", 42)`，重新產生組合語言，看看編譯器還會不會換成 `puts`，並解釋原因。
2. **製造連結錯誤**：建立 `a.c`（呼叫 `int helper(void);`）與 `b.c`（定義 `helper`）。只用 `cc a.c -o prog` 編譯，記錄錯誤訊息；再用 `cc -c a.c` 單獨編譯，確認這一步會成功。說明為什麼兩者結果不同。
3. **延伸實驗二**：在程式裡再加一個 `static int` 區域變數、一個 `malloc(1 << 20)` 的大區塊，印出它們的位址。它們分別落在哪一區？大區塊的位址和小的 `buf` 差很多嗎？（第 25 章會解釋大區塊為什麼可能來自另一個地方。）
4. **延伸實驗三**：把 `N` 改成 256（整個陣列只有 256 KiB），再跑一次。兩種走法的時間比變成多少？為什麼陣列變小之後差距會縮小？
5. **手算 Amdahl**：`thumbd` 有 8% 的時間花在等一把全域鎖（只能依序執行），其餘可以完美平行化。用 4 核、16 核、無限多核時，整體加速比各是多少？（答案：4 核 1 / (0.08 + 0.92/4) ≈ 3.23；16 核 1 / (0.08 + 0.92/16) ≈ 7.27；上限 1 / 0.08 = 12.5。可以把數字代入實驗四的 `speedup` 函式驗證。）
6. **Linux 練習**：在 Linux 機器（或 container）上對 `ls` 執行 `strace -c ls`，看 `ls` 一共用了哪些 system call、各幾次。再執行 `ldd $(which ls)`，列出它動態連結了哪些函式庫。

## 本章重點整理

- 電腦裡的一切資訊都是位元，意義來自解讀方式；同一串位元可以是字元、整數、浮點數或機器指令。
- C 原始碼經過 preprocess、compile、assemble、link 四個階段變成可執行檔，compiler driver（`cc`）替你依序呼叫它們。
- 可重定位目的檔（`.o`）裡的程式碼還不知道最終位址，用到的外部符號以 relocation entry 留下待補的洞；linker 負責符號解析與 relocation。
- 錯誤訊息出自哪個階段，決定了該往哪裡找原因：找不到標頭檔是 preprocess，型別錯誤是 compile，undefined reference 是 link，找不到 `.so` 是載入。
- CPU 不斷重複「依 PC 讀指令、執行、更新 PC」的循環，指令只有載入、存回、運算、跳躍幾類。
- 硬體由 CPU、主記憶體、匯流排與 I/O 裝置組成；磁碟與網路卡用 DMA 把資料直接寫進記憶體，資料搬運常常比計算更花時間。
- 記憶體階層用又小又快的 cache 填補 CPU 與 DRAM 的速度差距，各層延遲差距以數量級計；cache 靠 temporal 與 spatial locality 生效。
- 運算次數相同的程式，可能因為存取模式不同而差上十倍；效能分析要同時看「做多少事」與「資料從哪一層來」。
- 作業系統用 process、virtual memory、file 三個抽象包住 CPU、記憶體與 I/O 裝置，應用程式透過 system call 請 kernel 代辦特權操作。
- 可執行檔是磁碟上的檔案，process 是它的一次執行；部署換了檔案，正在跑的 process 不會自動更新。
- 並行是多件事在同一段時間內都在進行，平行是多件事在同一瞬間真的一起執行；硬體在 thread、指令、資料三個層次提供平行。
- Amdahl's law：比例 α 的部分加速 k 倍，整體加速比是 1 / [(1 − α) + α / k]，上限是 1 / (1 − α)；最佳化前一定要先量測時間分布。
- 本書以拾光相簿的 `thumbd` 為貫穿案例，大多數 Part 對應 CS:APP 3e 的一到兩章與 `thumbd` 的一類真實問題。

## 延伸問答

> [!question]- Q1. 編譯器和 linker 的分工是什麼？為什麼「編譯成功」之後還可能出現 undefined reference？
> 編譯器一次只處理一個 translation unit（一個 `.c` 加上它 include 的內容），它只需要知道每個被呼叫的函式「長什麼樣」（宣告），就能產生呼叫它的機器碼，並在目的檔裡留下一筆 relocation entry，表示「這裡要填 `foo` 的位址」。至於 `foo` 的本體在哪個檔案、存不存在，編譯器既不知道也不在乎。
>
> Linker 才會把所有 `.o` 與函式庫放在一起看，替每個未定義的符號找到唯一的定義。如果沒有任何輸入檔定義它，就會出現 undefined reference；如果有兩個以上的強定義，就會出現 multiple definition。所以 undefined reference 的修法幾乎都不在程式碼本身，而在建置設定：漏了哪個 `.o`、少了哪個 `-l`、或函式庫的順序錯了。

> [!question]- Q2. 可執行檔和 process 有什麼不同？為什麼這個區別對部署很重要？
> 可執行檔是磁碟上的一個檔案，內容是機器碼、資料與載入所需的資訊；它是靜態的，不執行時什麼也不做。Process 是作業系統對「這個檔案的一次執行」的抽象，擁有自己的 PC、暫存器、位址空間、開啟的檔案等狀態。同一個可執行檔執行三次，就是三個互相獨立的 process。
>
> 部署時常見的誤會是「把新的 binary 複製上去就完成了」。正在執行的 process 早已把舊的程式碼載入記憶體，替換磁碟上的檔案不會改變它。必須重啟服務才會生效，而且最好有方法確認正在跑的是哪個版本，例如讓 `/healthz` 回傳版本號，或比較 process 的啟動時間與部署時間。這正是小安第一天的任務要加版本號的原因。

> [!question]- Q3. 為什麼需要 cache？如果 DRAM 和 CPU 一樣快，cache 還有必要嗎？
> Cache 存在的根本原因是速度差距：CPU 每個 cycle 不到 1 ns，從 DRAM 讀一筆資料卻要約 100 ns。沒有 cache，CPU 大部分時間都在等資料。而做成又大又快的記憶體在物理與成本上都不可行：越快的儲存技術越貴、越佔晶片面積，所以只能做成小容量放在 CPU 旁邊，靠 locality 讓大多數存取在小而快的那一層完成。
>
> 如果 DRAM 真的和 CPU 一樣快，CPU 與 DRAM 之間的 cache 就沒有存在的必要。但這個「如果」不成立，而且同樣的道理在階層的每一層都適用：DRAM 是磁碟的快取、本機磁碟是遠端儲存的快取，CDN、Redis 也是同樣的設計。理解 cache 的一般原理，等於理解了整個系統設計中最常用的一招。

> [!question]- Q4. 手算題：`thumbd` 的 JPEG 解碼佔 60% 時間，換一個快 3 倍的解碼函式庫，整體快多少？最多能快多少？
> 代入 Amdahl's law：α = 0.6，k = 3。S = 1 / [(1 − 0.6) + 0.6 / 3] = 1 / (0.4 + 0.2) = 1 / 0.6 ≈ 1.67。整體約快 1.67 倍，也就是處理時間變成原本的 60%。
>
> 上限是 k 趨近無限大時的 1 / (1 − α) = 1 / 0.4 = 2.5 倍。也就是說，即使解碼完全不花時間，剩下 40% 的工作仍然要做，整體最多只能快 2.5 倍。如果目標是快 3 倍，光換解碼函式庫是做不到的，必須同時處理其他部分。這種上限的計算在評估最佳化方案時非常實用。

> [!question]- Q5. 並行（concurrency）和平行（parallelism）有什麼不同？單核心 CPU 能不能有並行？
> 並行描述的是程式的結構：同一段時間內有多個活動都「進行到一半」，例如一個伺服器同時有 100 個連線在處理中。平行描述的是執行方式：多個活動在同一瞬間真的一起執行，需要多份硬體，例如四個核心各執行一個 thread。
>
> 單核心 CPU 可以有並行，但沒有 thread 層級的平行：作業系統用 context switch 讓多個 process 或 thread 輪流使用唯一的核心，每段時間片很短，看起來像同時進行。不過即使只有一個核心，指令層級的平行（pipeline、超純量）與 SIMD 仍然存在。工作上這個區別很重要：一個用 event loop 處理大量連線的服務是高度並行的，但若它是單執行緒，就無法利用多核做平行計算。

> [!question]- Q6. 你在 production 看到 `error while loading shared libraries: libjpeg.so.8: cannot open shared object file`，這是哪一個階段的問題？該怎麼處理？
> 這不是編譯也不是連結的錯誤，建置早已成功。它發生在程式啟動時：可執行檔記錄了「我需要 `libjpeg.so.8`」，作業系統的動態載入器在啟動時去找這個檔案，找不到就無法開始執行 `main`。所以問題出在執行環境，而不是程式碼。
>
> 處理方式是先在那台機器上執行 `ldd ./thumbd`，看哪些函式庫標示為 `not found`，再確認系統裡有沒有其他版本（例如只有 `libjpeg.so.9`）。解法依情況可以是安裝正確版本的套件、在建置時設定 rpath、或改用 container 讓執行環境與建置環境一致。第 19 章會詳細說明動態載入器怎麼搜尋函式庫，以及為什麼版本號不同的 `.so` 不能隨便替換。

> [!question]- Q7. 為什麼同一支程式每次執行時，變數的位址都不一樣？這會帶來什麼影響？
> 這是 ASLR 的效果。現代作業系統每次載入程式時，會把程式碼、heap、stack、shared library 等區域隨機放到不同的起始位址。目的是安全：很多攻擊需要事先知道某段程式碼或資料的確切位址，隨機化之後攻擊者就很難猜中（第 11 章）。在 1.10 節的實驗二可以看到，兩次執行的位址不同，但同一區域內的相對距離不變，因為整塊區域是一起搬動的。
>
> 對工作的影響是：除錯時不要依賴絕對位址，例如「上次 crash 在 0x55d0c3a2e123」對下次執行沒有意義；要用「函式名稱加位移」或 debug symbol 來描述位置。分析 core dump 時，工具會根據當時的映射資訊把位址換算回函式與行號。

> [!question]- Q8. 面試題：從你在終端機輸入 `./hello` 按下 Enter，到看見 `hello, world`，盡可能完整地描述發生了什麼。
> Shell 從鍵盤讀到這行命令，解析出要執行 `./hello`，用 `fork` 建立一個子 process，子 process 再用 `execve` 請 kernel 把 `hello` 載入：kernel 建立新的虛擬位址空間，依可執行檔的描述映射程式碼與資料區段，設定 stack，並交給動態載入器把 libc 映射進來、安排好 `puts` 的位址（可能在啟動時就補好，也可能等第一次呼叫才補，第 19 章）。資料從磁碟搬進記憶體時使用 DMA。
>
> 接著 CPU 從程式的進入點開始執行，先跑 libc 的啟動程式碼，再呼叫 `main`。`main` 把字串位址放進 `%rdi`、呼叫 `puts`；指令與資料經由 cache 從記憶體送進 CPU。`puts` 把字串放進標準輸出的緩衝區，最後發出 `write(1, "hello, world\n", 13)` system call，CPU 切換到 kernel mode，kernel 把位元組交給終端機的驅動程式，顯示在螢幕上。`main` 回傳後，libc 呼叫 `exit_group` 結束 process，shell 用 `wait` 回收它，再印出提示字元。能講到 fork／exec、載入與動態連結、system call、cache，就涵蓋了本書大部分的主題。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 1 章「A Tour of Computer Systems」是本章的對應內容，也有學生資源與勘誤。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：CS:APP 作者在 CMU 開設的課程，投影片與錄影依本書章節編排。
- [GCC 線上文件](https://gcc.gnu.org/onlinedocs/)：`-E`、`-S`、`-c` 等編譯階段選項的完整說明。
- [GNU Binutils 文件](https://sourceware.org/binutils/docs/)：`objdump`、`nm`、`as`、`ld` 的使用手冊。
- [Linux man pages](https://man7.org/linux/man-pages/)：`strace(1)`、`execve(2)`、`write(2)` 等本章提到的指令與 system call。
