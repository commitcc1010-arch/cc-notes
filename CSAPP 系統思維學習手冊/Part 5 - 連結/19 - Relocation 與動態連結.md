---
chapter: 19
title: Relocation 與動態連結
part: 5
---

# 第 19 章　Relocation、動態連結與 Library Interpositioning

> [!abstract] 本章地圖
> **核心問題**：目的檔裡那些「還不知道位址」的洞，是誰、在什麼時候、用什麼公式填上的？一支程式執行時，為什麼會載入一個你以為不是它的 library？
>
> **你會學到**：
> - 讀懂 `objdump -dr` 印出的 relocation entry，並用 S + A − P 手算出 linker 寫進去的位元組
> - 說出 `execve` 到 `main` 之間發生的事：program header、dynamic linker、`_start`
> - 解釋 PIC、GOT、PLT 與 lazy binding 如何讓一份 library 程式碼被許多 process 共用
> - 依照 dynamic linker 的搜尋順序，判斷 process 實際載入的是哪一份 `.so`，並用 `ldd`、`LD_DEBUG`、`/proc/PID/maps` 證實
> - 分辨什麼改動會破壞 ABI，看懂 `version 'GLIBC_2.34' not found` 這類錯誤
> - 用 compile-time、link-time、run-time（`LD_PRELOAD`）三種 interpositioning 攔截函式呼叫，做量測與除錯
>
> **前置知識**：第 18 章（目的檔、ELF section、符號表、static library）、第 9 章（`call` 指令與 return address）、第 10 章（函式指標）
>
> **對應 CS:APP 3e**：第 7 章 7.7–7.13 節

## 19.1 故事：換了 base image 之後，`thumbd` 一解碼就當機

星期二早上，SRE 阿哲把 `thumbd` 的容器 base image 換成新版，順便把一個外部轉檔工具 `imgconv` 裝進同一個 image。部署完十分鐘，監控開始告警：大約三成的 JPEG 請求讓 worker 收到 `SIGSEGV`，core dump 的 backtrace 停在 `jpeg_read_header`。PNG 請求完全正常。

小安的第一個反應是「程式碼一行都沒改，怎麼可能壞」。原始碼確實沒變，執行檔的 hash 也跟上週一模一樣。老周請小安在出事的機器上執行一行指令：

```bash
cat /proc/$(pidof thumbd)/maps | grep jpeg
```

輸出裡 `libjpeg.so.8` 的路徑不是平常的 `/usr/lib/x86_64-linux-gnu/`，而是 `/opt/imgconv/lib/`。原來 `imgconv` 的安裝腳本在 image 的環境設定裡加了 `LD_LIBRARY_PATH=/opt/imgconv/lib`，那個目錄放著 `imgconv` 團隊自己從另一版原始碼編出來的 `libjpeg.so.8`。檔名一樣，內部的 struct 版面卻不同。`thumbd` 啟動時，dynamic linker 照規則先找 `LD_LIBRARY_PATH`，於是載入了錯的那一份。

「編譯好的執行檔並不完整，」老周說，「它只記得『我需要一個叫 `libjpeg.so.8` 的東西，裡面要有 `jpeg_read_header`』。真正的位址是每次啟動時才填上去的。要懂這件事，得先從 linker 怎麼填位址講起。」

這一章就沿著這條線走：先看 linker 在連結時怎麼填洞（relocation），再看程式怎麼被載入，然後看 shared library 怎麼把一部分填洞工作延到執行時，最後看如何刻意利用這個機制攔截函式（interpositioning）。

## 19.2 Relocation：把目的檔裡的洞填上

第 18 章講過，編譯器一次只看一個 `.c` 檔。`thumbd` 的 `main.c` 呼叫 `resize()`、讀取全域變數 `quality`，但這兩個東西定義在別的檔案裡，編譯 `main.c` 時沒人知道它們最後會在哪個位址。組譯器只能先在指令裡留下 `00 00 00 00` 的空位，再另外寫一張紙條：「這 4 個 byte 之後要填上 `resize` 的位置」。這張紙條叫 **relocation entry**（重定位項目），填洞的動作叫 **relocation**（重定位）。

linker 做 relocation 分兩步。第一步是**合併與配置**：把所有輸入目的檔的 `.text` 合成一個 `.text`、`.data` 合成一個 `.data`，然後替每個 section 和每個符號決定最終的執行時位址。第二步才是**修補**：依照每一張 relocation entry，算出值、寫進對應的位置。第二步需要第一步的結果，所以順序不能反。

### 看一個真實的 relocation entry

用一段小程式做實驗。`main.c` 呼叫外部的 `resize` 與 `printf`，並讀取外部變數 `quality`：

```c
// not-runnable：resize 與 quality 定義在別的檔案，這個檔案單獨只能編譯成 main.o
int printf(const char *fmt, ...);
int resize(int w);
extern int quality;

int main(void) {
    int r = resize(640);
    printf("%d %d\n", r, quality);
    return 0;
}
```

用 `clang -target x86_64-linux-gnu -O1 -fno-pic -c -fno-asynchronous-unwind-tables -o main.o main.c` 產生 x86-64 Linux 的目的檔，再用 `objdump -dr main.o` 反組譯並把 relocation 印在指令旁邊。下面是實際輸出（macOS 上的 Apple LLVM objdump 讀 ELF 檔）：

```text
0000000000000000 <main>:
       0: 50                            pushq   %rax
       1: bf 80 02 00 00                movl    $0x280, %edi
       6: e8 00 00 00 00                callq   0xb <main+0xb>
                0000000000000007:  R_X86_64_PLT32   resize-0x4
       b: 8b 15 00 00 00 00             movl    (%rip), %edx
                000000000000000d:  R_X86_64_PC32    quality-0x4
      11: bf 00 00 00 00                movl    $0x0, %edi
                0000000000000012:  R_X86_64_32      .rodata.str1.1
      16: 89 c6                         movl    %eax, %esi
      18: 31 c0                         xorl    %eax, %eax
      1a: e8 00 00 00 00                callq   0x1f <main+0x1f>
                000000000000001b:  R_X86_64_PLT32   printf-0x4
      1f: 31 c0                         xorl    %eax, %eax
      21: 59                            popq    %rcx
      22: c3                            retq
```

先看位移 `0x6` 的 `call`：機器碼 `e8` 後面跟著四個 `00`，那就是洞。下一行說明這個洞在位移 `0x7`，類型是 `R_X86_64_PLT32`，目標是 `resize`，**addend**（加數）是 −4。另外三個洞分別是 `quality` 的讀取、字串常數 `"%d %d\n"` 的位址、`printf` 的呼叫。

ELF 的 relocation entry 實際上就是一個小 struct，記錄四件事：

| 欄位 | 意思 | 在 `resize` 這一筆的值 |
|---|---|---|
| offset | 洞在 section 裡的位移 | `0x7` |
| type | 要用哪個公式算、寫幾個 byte | `R_X86_64_PLT32`（4 bytes，PC-relative） |
| symbol | 洞要指向誰 | `resize` |
| addend | 公式裡的常數修正 | −4 |

### 兩個最基本的公式

x86-64 有幾十種 relocation type，但都是幾個變數的組合。記住三個符號就能讀懂大部分：**S** 是目標符號的最終位址，**A** 是 addend，**P** 是洞本身的最終位址（place）。

| 類型 | 公式 | 寫入大小 | 用在哪裡 |
|---|---|---|---|
| `R_X86_64_32` | S + A | 4 bytes，要能放進 32-bit 無號 | 非 PIC 程式碼裡的絕對位址，例如 `movl $str, %edi` |
| `R_X86_64_64` | S + A | 8 bytes | 資料裡存的指標，例如 `.data` 中的函式指標表 |
| `R_X86_64_PC32` | S + A − P | 4 bytes，有號 | 用 `%rip` 相對定址讀寫資料 |
| `R_X86_64_PLT32` | L + A − P | 4 bytes，有號 | `call` 外部函式；L 是 PLT 項目，若目標就在同一個執行檔裡，linker 直接用 S |
| `R_X86_64_GOTPCREL`（及 `REX_GOTPCRELX`） | G + GOT + A − P | 4 bytes，有號 | 經由 GOT 間接取得位址，19.5 節會看到 |

PC-relative 為什麼要減 P，又為什麼 addend 是 −4？因為 x86-64 的 `call rel32` 與 `%rip` 相對定址，都是以「**下一條指令**的位址」為基準：CPU 執行 `call` 時，`%rip` 已經指到下一條指令。洞在指令的最後 4 個 byte，所以下一條指令的位址剛好是 P + 4。我們要寫入的值是「目標 − 下一條指令」= S − (P + 4) = S + (−4) − P。組譯器把那個 4 預先放進 addend，linker 只要照公式算。

### 手算一次

假設 linker 把各 section 配置完之後，得到下列位址（典型的非 PIE 執行檔，從 `0x400000` 附近開始）：

| 符號 | 最終位址 |
|---|---|
| `main` | `0x401130` |
| `resize` | `0x401160` |
| `printf` 的 PLT 項目 | `0x401030` |
| 字串常數 `.rodata.str1.1` | `0x402004` |
| `quality` | `0x404028` |

**第一個洞（`resize`）**：P = `0x401130` + `0x7` = `0x401137`，S = `0x401160`，A = −4。

```text
S + A − P = 0x401160 − 4 − 0x401137
          = 0x401160 − 0x40113b
          = 0x25
寫入（little-endian）：25 00 00 00
指令變成：e8 25 00 00 00   → call 0x40113b + 0x25 = 0x401160 ✓
```

**第二個洞（`quality`）**：P = `0x40113d`，S + A − P = `0x404028` − 4 − `0x40113d` = `0x2ee7`，寫入 `e7 2e 00 00`。CPU 執行到這條指令時，`%rip` 是下一條指令 `0x401141`，加上 `0x2ee7` 正好是 `0x404028`。

**第三個洞（字串常數）**：絕對位址，S + A = `0x402004`，寫入 `04 20 40 00`。注意它只有 4 bytes：非 PIC 程式碼預設使用 x86-64 psABI 的 small code model，假設所有程式與靜態資料都放在位址空間最低的 2 GiB 內，所以 32-bit 欄位就裝得下。傳統非 PIE 執行檔預設從 `0x400000` 這個低位址開始配置，正好符合這個假設。

**第四個洞（`printf`）**：S 是 PLT 項目 `0x401030`，它比 P 小，所以結果是負數。0x401030 − 4 − 0x40114b = −0x11f，以二補數（第 4 章）寫成 `e1 fe ff ff`。

19.11 節會用一段 Python 程式把這四次計算自動做完，結果和這裡的手算一致。

> [!warning] 常見誤解
> 「relocation 就是把程式搬到另一個位址」。在連結階段，relocation 指的是**修補指令與資料裡的位址欄位**，程式並沒有被搬動。之所以叫「重定位」，是因為每個目的檔原本都假設自己從位址 0 開始，linker 決定它的真正位置後，所有依賴位置的欄位都要跟著改。

## 19.3 執行檔怎麼被載入：從 `execve` 到 `main`

relocation 完成後，linker 輸出一個 **executable object file**（可執行目的檔）。它和目的檔一樣是 ELF，但多了一份給載入器看的資料：**program header table**（程式標頭表）。第 18 章的 section 是給 linker 看的「內容分類」；program header 描述的是 **segment**（區段），也就是「哪一段檔案內容要映射到哪個虛擬位址、權限是什麼」。

```text
 thumbd（ELF 執行檔）                      thumbd process 的虛擬位址空間
 ┌─────────────────────┐
 │ ELF header          │ ─ 記錄 entry point = _start 的位址
 │ program headers     │ ─ 給 loader：怎麼映射
 ├─────────────────────┤
 │ .interp             │ ── PT_INTERP：「請用 /lib64/ld-linux-x86-64.so.2」
 │ .text  .rodata      │ ┐                       ┌──────────────────┐
 │ .plt   .eh_frame    │ ┘─ PT_LOAD（R-X）─────▶ │ 程式碼  r-x       │
 │ .data  .got .bss    │ ── PT_LOAD（RW-）─────▶ │ 資料    rw-       │
 │ .dynamic            │ ── PT_DYNAMIC           │ .bss 補零         │
 ├─────────────────────┤                         └──────────────────┘
 │ .symtab .debug_*    │ ─ 不載入記憶體，只給除錯器與 nm 用
 │ section headers     │
 └─────────────────────┘
```

幾個重點：

1. 多個 section 合成一個 segment。權限相同、位置相鄰的 section 一起映射，這樣 page table（第 23 章）只要用少數幾種權限。
2. `.bss` 在檔案裡幾乎不佔空間，只記錄大小。載入時那段位址被映射成填零的頁，這正是第 24 章 demand paging 的應用。
3. `.symtab` 與除錯資訊不屬於任何 `PT_LOAD`，執行時不佔記憶體。`strip` 掉它們只會讓檔案變小，不會讓程式變快。

`readelf -l thumbd` 可以印出 program header。下面是示意輸出（Linux 專屬工具，本機無法執行）：

```text
示意輸出（readelf -lW thumbd，節錄）
  Type      Offset   VirtAddr           FileSiz  MemSiz   Flg Align
  PHDR      0x000040 0x0000000000000040 0x0002d8 0x0002d8 R   0x8
  INTERP    0x000318 0x0000000000000318 0x00001c 0x00001c R   0x1
      [Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]
  LOAD      0x000000 0x0000000000000000 0x0021a8 0x0021a8 R   0x1000
  LOAD      0x003000 0x0000000000003000 0x01a2c1 0x01a2c1 R E 0x1000
  LOAD      0x01e000 0x000000000001e000 0x004f10 0x004f10 R   0x1000
  LOAD      0x023d10 0x0000000000024d10 0x0012f0 0x0e3a8  RW  0x1000
  DYNAMIC   0x023d28 0x0000000000024d28 0x000200 0x000200 RW  0x8
  GNU_RELRO 0x023d10 0x0000000000024d10 0x0002f0 0x0002f0 R   0x1
```

最後一個 `LOAD` 的 `MemSiz` 比 `FileSiz` 大很多，多出來的就是 `.bss`。`VirtAddr` 從 0 開始，表示這是 **PIE**（position-independent executable，位置無關執行檔）：載入時 kernel 會挑一個隨機的基底位址加上去，這是 ASLR（第 11 章）的一部分。

### 從 `execve` 到 `main` 的完整路線

```text
 shell 呼叫 execve("./thumbd", argv, envp)          ← 第 21 章
   │
   ▼  kernel
 ① 讀 ELF header 與 program header
 ② 清掉舊的位址空間，依 PT_LOAD 建立新的映射（只建立對應，不讀內容）
 ③ 看到 PT_INTERP → 也把 ld-linux-x86-64.so.2 映射進來
 ④ 建立 stack，放好 argc、argv、envp 與 auxiliary vector
 ⑤ 跳到 dynamic linker 的入口（不是 thumbd 的 _start）
   │
   ▼  user mode：ld-linux-x86-64.so.2
 ⑥ 讀 thumbd 的 .dynamic，找出 NEEDED：libjpeg.so.8、libpng16.so.16、libc.so.6 …
 ⑦ 依搜尋規則找到並映射每個 .so（19.7 節）
 ⑧ 處理 dynamic relocation：填 GOT、修正指標
 ⑨ 執行各 shared library 的初始化函式（.init_array）
 ⑩ 跳到 thumbd 的 entry point：_start
   │
   ▼
 _start → __libc_start_main（執行 thumbd 自己的 .init_array）→ main(argc, argv, envp)
```

這張流程圖說明了兩件常讓人困惑的事。第一，`main` 不是程式第一個被執行的函式：在它之前，dynamic linker 和 C runtime 已經做了很多事：library 的 C++ 全域物件建構子在 ⑨ 執行，執行檔自己的建構子則由 `__libc_start_main` 在呼叫 `main` 之前執行（以 glibc 為例）。第二，如果 ⑥⑦ 找不到 library，`main` 根本不會開始，錯誤訊息來自 dynamic linker 而不是你的程式：

```text
./thumbd: error while loading shared libraries: libjpeg.so.8: cannot open shared object file: No such file or directory
```

只有在完全 static 連結的執行檔裡，才沒有 `PT_INTERP`，kernel 直接跳到 `_start`。

## 19.4 為什麼需要 shared library

static library（第 18 章的 `.a`）在連結時把需要的目的檔整份複製進執行檔。這很簡單，但有兩個問題。一是**重複**：機器上每個用到 `printf` 的程式都各自帶一份，磁碟與記憶體裡都有好幾百份相同的程式碼。二是**更新**：libjpeg 修了一個安全漏洞，所有 static 連結它的程式都要重新連結、重新部署。

**shared library**（共享函式庫，Linux 上副檔名 `.so`，shared object）把連結延到載入或執行時：執行檔只記錄「需要哪個 library」，程式碼留在 `.so` 裡。多個 process 映射同一個 `.so` 檔時，它的程式碼頁在實體記憶體中只有一份（第 24 章的 shared mapping）。

| 面向 | static 連結（`.a`） | 動態連結（`.so`） |
|---|---|---|
| 執行檔大小 | 大，包含 library 程式碼 | 小，只記錄依賴 |
| 記憶體 | 每個 process 各一份 | 程式碼頁跨 process 共享 |
| 啟動 | 快，沒有載入與符號查找 | 要找檔案、映射、做 dynamic relocation |
| 修補 library 漏洞 | 每個程式都要重新連結 | 換掉 `.so` 檔，重啟 process 即可 |
| 部署風險 | 低，執行檔自給自足 | 執行環境的 library 版本必須相容（本章故事） |
| 典型場景 | 單一執行檔部署（Go 預設）、救援工具、極小容器 | 一般 Linux 發行版、大部分 C／C++ 服務 |

一個 `.so` 有三種名字，搞清楚它們能省下很多部署時間：

| 名字 | 例子 | 誰用它 |
|---|---|---|
| real name（實際檔名） | `libjpeg.so.8.2.2` | 檔案系統上真正的檔案 |
| **soname** | `libjpeg.so.8` | 寫在 `.so` 裡的 `SONAME`，linker 會把它抄進執行檔的 `NEEDED`；執行時 dynamic linker 找的是這個名字 |
| linker name | `libjpeg.so` | 編譯時 `-ljpeg` 找的名字，通常是指向 real name 的 symlink，只在開發套件（`-dev`）裡有 |

soname 裡的 `8` 是 **ABI 的主版號**：同一個 soname 的不同版本應該可以互相替換，不相容的改動要換成 `libjpeg.so.9`。本章的故事之所以出事，正是因為有人做出了「soname 一樣、ABI 卻不同」的檔案，19.9 節會再回來談。

## 19.5 PIC：讓程式碼不在乎自己被放在哪裡

shared library 要被很多 process 共用，就有一個難題：每個 process 可能把 `libjpeg.so.8` 映射在不同的位址（ASLR 也會讓它每次都不同）。如果 library 的程式碼裡寫著絕對位址，每個 process 就得修改自己那份程式碼，程式碼頁就不能共享了。

解法是 **PIC**（position-independent code，位置無關程式碼）：編譯時加上 `-fPIC`，產生的程式碼不管被載入到哪裡都能正確執行，程式碼頁本身完全不需要修改。PIC 用兩個技巧。

**技巧一：同一個模組內，用相對距離。** 一個 `.so` 被映射時，它的程式碼段與資料段之間的距離是固定的。所以程式碼要讀自己模組的資料，用 `%rip` 相對定址就好：「從這條指令往後 `0x2ee7` bytes」在任何載入位址都成立。

**技巧二：要找別的模組的東西，透過一張表。** 外部符號的位置在連結時無從得知，所以在資料段放一張 **GOT**（global offset table，全域位移表），每個外部符號一格。程式碼用相對定址讀 GOT 的那一格，拿到真正的位址，再去用它。GOT 在資料段，每個 process 各有一份，由 dynamic linker 在載入時填好；程式碼段保持不變、可以共享。

```text
 libthumb.so 被映射到任意基底位址 B
 ┌──────────────────────────┐ B + 0x1000
 │ .text（共享，唯讀）        │
 │   movq quality@GOTPCREL(%rip), %rax   ──┐ 固定距離
 │   imull (%rax), %edi                    │
 ├──────────────────────────┤             │
 │ .got（每個 process 一份）  │ ◀───────────┘
 │   [quality 的實際位址] ────┼──────────────▶ 可能在 thumbd 執行檔裡，
 │   [clamp 的實際位址]       │                也可能在別的 .so 裡
 └──────────────────────────┘
       ▲ 載入時由 dynamic linker 填入
```

### 看編譯器怎麼做

用一段像 `thumbd` 內部 library 的程式比較不同選項。`quality` 是匯出的全域變數，`calls` 是 `static`，`clamp` 定義在別的 library：

```c
int quality = 85;             /* 匯出的全域變數：別的模組可能用同名變數取代它 */
static int calls;             /* static：只在這個 .so 內部可見 */
int clamp(int q);             /* 定義在別的 library */

int scaled_quality(int w) {
    calls++;
    return clamp(w * quality);
}
```

用 `clang -target x86_64-linux-gnu -O1 -fPIC -S -fno-asynchronous-unwind-tables -o - libthumb.c` 產生（只保留函式本體）：

```asm
scaled_quality:
	incl	calls(%rip)
	movq	quality@GOTPCREL(%rip), %rax
	imull	(%rax), %edi
	jmp	clamp@PLT                       # TAILCALL
```

同一個檔案加上 `-fvisibility=hidden`：

```asm
scaled_quality:
	incl	calls(%rip)
	imull	quality(%rip), %edi
	jmp	clamp@PLT                       # TAILCALL
```

逐行解讀：

1. `calls` 是 `static`，不可能被別的模組看到，所以兩個版本都直接用 `calls(%rip)`，這就是技巧一。
2. `quality` 雖然定義在同一個檔案，預設版本卻要經過 GOT（先 `movq` 取位址、再 `imull (%rax)`，多一次記憶體存取）。原因是 ELF 的規則允許**符號 interposition**：如果執行檔或更早載入的 library 也定義了 `quality`，執行時大家都要用那一份。編譯器不能假設 `quality` 一定是自己這份。
3. 加上 `-fvisibility=hidden` 後，`quality` 不再對外匯出，編譯器知道它一定在本模組，於是退回相對定址。這是 library 作者常用的最佳化：只匯出公開 API，其餘全部 hidden。
4. `clamp` 只有宣告，兩個版本都經過 `@PLT`，這是下一節的主題。順帶一提，`-O1` 把最後的 `call` 加 `ret` 合併成 `jmp`（tail call，第 9 章）。

回頭看 19.2 節的 `main.o`：用預設選項（clang 對 x86-64 Linux 預設產生 PIE）編譯時，`quality` 的那一筆會變成 `R_X86_64_REX_GOTPCRELX`，字串常數變成 `R_X86_64_PC32`，不再有 `R_X86_64_32` 這種絕對位址。名字裡的 `X` 表示「可放寬」：如果 linker 最後發現 `quality` 就在同一個執行檔裡，它可以把 `movq` 讀 GOT 改寫成 `leaq` 直接算位址，省掉一次記憶體存取。

> [!warning] 常見誤解
> 「PIC 很慢，所以 library 不該用 `-fPIC`」。在 32-bit x86 上 PIC 確實要佔用一個暫存器而有可量測的成本；x86-64 有 `%rip` 相對定址，額外成本主要只剩經過 GOT 的那一次讀取，而且 GOT 通常在 cache 裡。在 x86-64 上，要把非 PIC 的目的檔連成 `.so`，GNU ld 會直接報錯：`relocation R_X86_64_32 against '.rodata' can not be used when making a shared object; recompile with -fPIC`。

## 19.6 PLT 與 lazy binding：第一次呼叫才找函式

函式呼叫也可以用「讀 GOT 再間接 call」解決，`-fno-plt` 選項就是這樣做的（產生 `jmpq *clamp@GOTPCREL(%rip)`）。但傳統的預設做法多了一層 **PLT**（procedure linkage table，程序連結表）：程式碼 `call` 的是 PLT 裡的一小段跳板程式，跳板再經由 GOT 跳到真正的函式。

多這一層的理由是 **lazy binding**（延遲綁定）：一個大程式可能連結了上千個外部函式，但一次執行只呼叫其中一小部分。與其在啟動時把每一個都查好，不如等到第一次呼叫時才查。

```text
 thumbd 的程式碼            PLT（唯讀、共享）                    GOT（.got.plt，可寫）
 ────────────               ─────────────────────                ─────────────────────
                            PLT[0]:                              GOT[0] .dynamic 的位址
                              pushq GOT[1]   ─ 哪個模組           GOT[1] link_map（模組資訊）
                              jmp  *GOT[2]   ─ 跳到 resolver      GOT[2] _dl_runtime_resolve
 call jpeg_read_header@plt
         │                  PLT[1]: jpeg_read_header             GOT[3] ─┐ 第一次：指回 PLT[1] 的 pushq
         └───────────────▶    jmp  *GOT[3]  ────────────────────────────┘ 之後：libjpeg 裡的真正位址
                              pushq $0       ─ 第幾個 relocation
                              jmp  PLT[0]
```

第一次呼叫的流程：

1. `call` 跳到 `PLT[1]`，執行 `jmp *GOT[3]`。GOT[3] 一開始存的是 `PLT[1]` 下一條指令（`pushq $0`）的位址，所以等於往下走。
2. `pushq $0` 推入「這是第 0 筆 PLT relocation」，跳到 `PLT[0]`；`PLT[0]` 再推入模組資訊並跳到 dynamic linker 的 resolver。
3. resolver 依序搜尋已載入的模組，在 `libjpeg.so.8` 找到 `jpeg_read_header`，把位址**寫回 GOT[3]**，然後跳過去執行。

第二次以後，`jmp *GOT[3]` 直接跳到 `jpeg_read_header`，只多一次間接跳躍。下面這段 Python 模擬這個機制（為了簡化，用 `GOT[n]` 表示第 n 個函式的那一格，省略前三格保留項）：

```python
# 模擬 x86-64 lazy binding：PLT stub 永遠「jmp *GOT[n]」，差別只在 GOT[n] 裡放什麼
libjpeg = {"jpeg_read_header": "libjpeg.so.8 的 jpeg_read_header",
           "jpeg_start_decompress": "libjpeg.so.8 的 jpeg_start_decompress"}
plt_index = {"jpeg_read_header": 0, "jpeg_start_decompress": 1}
got = ["resolver", "resolver"]        # 載入時：GOT 先指回 PLT 的「去找 resolver」路徑
lookups = 0

def resolver(n, name):
    global lookups
    lookups += 1                      # 真實系統：在每個已載入的 library 的符號表裡依序搜尋
    got[n] = libjpeg[name]            # 把找到的位址寫回 GOT，下次就不用再找
    return got[n]

def call_via_plt(name):
    n = plt_index[name]
    target = got[n]
    if target == "resolver":
        target = resolver(n, name)
        print(f"call {name:22} GOT[{n}] 是 resolver → 查表，寫回 GOT → {target}")
    else:
        print(f"call {name:22} GOT[{n}] 已填好      → 直接跳到 {target}")

for name in ["jpeg_read_header", "jpeg_read_header", "jpeg_start_decompress", "jpeg_read_header"]:
    call_via_plt(name)
print(f"4 次呼叫，只做了 {lookups} 次符號查找")
```

在 macOS arm64、Python 3 上的實際輸出：

```text
call jpeg_read_header       GOT[0] 是 resolver → 查表，寫回 GOT → libjpeg.so.8 的 jpeg_read_header
call jpeg_read_header       GOT[0] 已填好      → 直接跳到 libjpeg.so.8 的 jpeg_read_header
call jpeg_start_decompress  GOT[1] 是 resolver → 查表，寫回 GOT → libjpeg.so.8 的 jpeg_start_decompress
call jpeg_read_header       GOT[0] 已填好      → 直接跳到 libjpeg.so.8 的 jpeg_read_header
4 次呼叫，只做了 2 次符號查找
```

### 現況：lazy binding 正在退場

lazy binding 有一個安全上的代價：GOT 在整個執行期間必須可寫，攻擊者只要有一個任意寫入漏洞，改掉 GOT 的一格就能劫持下一次函式呼叫（GOT overwrite 是經典的攻擊手法）。因此現代發行版的許多套件改用 **full RELRO**：連結時加 `-Wl,-z,relro,-z,now`，dynamic linker 在啟動時就解析所有函式（**BIND_NOW**），填完後用 `mprotect` 把 GOT 改成唯讀。

| 設定 | 啟動時 | 每次呼叫 | GOT 執行中可寫？ | 怎麼設定 |
|---|---|---|---|---|
| lazy binding | 只填資料用的 GOT | 第一次查找，之後一次間接跳躍 | 函式那部分可寫 | GNU ld 本身的預設；不少發行版的工具鏈已改成預設 `-z now` |
| BIND_NOW ＋ full RELRO | 解析所有函式，較慢 | 一次間接跳躍 | 否 | `-z now -z relro`；或執行時設 `LD_BIND_NOW=1` 測試 |
| `-fno-plt` ＋ BIND_NOW | 同上 | 直接 `call *GOT`，少一次跳躍 | 否 | 編譯加 `-fno-plt` |

BIND_NOW 還有一個工作上的好處：如果某個函式在新版 library 裡不見了，程式會在**啟動時**就失敗，而不是跑了三天後第一次走到那段程式碼才失敗。對 `thumbd` 這種長時間執行的服務，啟動失敗遠比半夜當機好處理。

## 19.7 Dynamic linker 怎麼找 library

現在可以回答本章故事的核心問題：`thumbd` 的 `NEEDED` 只寫著 `libjpeg.so.8`，沒有路徑，dynamic linker 怎麼決定用哪一份？glibc 的 `ld-linux-x86-64.so.2` 依照下面的順序搜尋（名字裡含有 `/` 時則直接當作路徑，不搜尋）：

```text
 要找 NEEDED: libjpeg.so.8
   │
   ├─ ① 執行檔的 DT_RPATH（只在沒有 DT_RUNPATH 時才看；舊式，連間接依賴也適用）
   ├─ ② 環境變數 LD_LIBRARY_PATH（secure-execution 模式下，例如 setuid 程式，會被忽略）
   ├─ ③ 執行檔的 DT_RUNPATH（新式，只用於這個檔案自己的直接依賴）
   ├─ ④ /etc/ld.so.cache（由 ldconfig 依 /etc/ld.so.conf 產生的索引）
   └─ ⑤ 預設目錄：/lib、/usr/lib（64-bit 系統上還有對應的 lib64 或多架構目錄）
   第一個找到且架構相符的檔案勝出；全部找不到 → error while loading shared libraries
```

故事裡的 `thumbd` 沒有設定 RPATH 或 RUNPATH，原本在 ④ 找到系統的 libjpeg。新 image 多了 `LD_LIBRARY_PATH=/opt/imgconv/lib`，在 ② 就先找到 `imgconv` 的那份，後面的規則根本沒機會執行。

| 機制 | 設定方式 | 適用時機 | 風險 |
|---|---|---|---|
| `LD_LIBRARY_PATH` | 環境變數 | 臨時測試、開發 | 會被子行程繼承、影響同一環境的所有程式；本章故事的成因 |
| RUNPATH | 連結時 `-Wl,-rpath,'$ORIGIN/../lib'`（許多發行版的工具鏈預設寫成 RUNPATH） | 把 library 跟著程式一起發佈 | 優先序低於 `LD_LIBRARY_PATH` |
| RPATH（舊式） | `-Wl,--disable-new-dtags,-rpath,…` | 需要蓋過 `LD_LIBRARY_PATH` 的少數情況 | 也套用到間接依賴，難以預料 |
| `ldconfig` | 把目錄加進 `/etc/ld.so.conf.d/` 再執行 `ldconfig` | 系統層級安裝 | 影響整台機器 |
| 完整路徑的 `dlopen` | `dlopen("/opt/thumbd/plugins/heic.so", …)` | plugin | 路徑若可被他人寫入，等於讓別人注入程式碼 |

`$ORIGIN` 是一個特殊字串，dynamic linker 會把它換成「執行檔所在的目錄」。把 library 放在 `bin/../lib`、執行檔寫入 `RUNPATH=$ORIGIN/../lib`，整個目錄搬到哪裡都能用，這是發佈自帶 library 的軟體（例如瀏覽器、IDE）常用的做法。

### 用工具證實「到底載入了哪一份」

```bash
readelf -d ./thumbd | grep -E 'NEEDED|RUNPATH|RPATH'   # 執行檔「要求」什麼
ldd ./thumbd                                           # 依目前環境「會」解析成什麼
LD_DEBUG=libs ./thumbd --version 2>&1 | grep jpeg      # 看搜尋過程
grep jpeg /proc/$(pidof thumbd)/maps                   # 執行中的 process「實際」載入了什麼
```

故事中出事機器上的示意輸出（Linux 專屬工具，本機無法執行）：

```text
示意輸出
$ ldd ./thumbd | grep jpeg
	libjpeg.so.8 => /opt/imgconv/lib/libjpeg.so.8 (0x00007f3c1a200000)

$ LD_DEBUG=libs ./thumbd --version 2>&1 | grep -A3 'file=libjpeg'
     41207:	file=libjpeg.so.8 [0];  needed by ./thumbd [0]
     41207:	find library=libjpeg.so.8 [0]; searching
     41207:	 search path=/opt/imgconv/lib		(LD_LIBRARY_PATH)
     41207:	  trying file=/opt/imgconv/lib/libjpeg.so.8
```

`LD_DEBUG` 的最後一欄括號直接寫出這個搜尋路徑的來源是 `LD_LIBRARY_PATH`，證據就齊全了。四個工具回答的問題不同：`readelf -d` 看「要求」、`ldd` 和 `LD_DEBUG` 看「在目前環境下會怎麼解析」、`/proc/PID/maps` 看「已經在跑的 process 實際用了什麼」。在 production 除錯時，最後一個最可靠，因為它不受你的 shell 環境影響。

> [!warning] 常見誤解
> 「`ldd` 只是讀檔案，很安全」。`ldd` 的 man page 明確警告，某些情況下它會嘗試直接執行目標程式來取得依賴資訊。對來路不明的執行檔，改用 `readelf -d` 或 `objdump -p` 只讀取 ELF 內容。

在 macOS 上，對應的工具是 `otool -L`、環境變數 `DYLD_LIBRARY_PATH`，以及 `@rpath`、`@loader_path`。下面是本機（macOS arm64）對 19.11 節程式的實際輸出，可以看到 macOS 把 libc、libm、libdl 等都合在 `libSystem` 裡：

```text
$ otool -L dl
dl:
	/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1356.0.0)
```

### 故事的結局

老周和小安做了三件事。立即止血：把 `LD_LIBRARY_PATH` 從容器的全域環境移除，只在 `thumbd` 呼叫 `imgconv` 的那一次 `execve` 傳入（第 21 章）。長期修正：`thumbd` 的部署流程加了一個啟動前檢查，比對 `ldd` 的結果是否都落在預期目錄。最後，`imgconv` 團隊把自編的 library 改成自己的 soname，不再冒用 `libjpeg.so.8`。

## 19.8 執行時載入：`dlopen` 與 plugin

到目前為止，library 都是啟動時由 `NEEDED` 決定的。但程式也可以在執行中途自己載入 library，這是 plugin 架構的基礎。`thumbd` 支援 HEIC 格式的方式就是如此：HEIC 解碼器授權複雜，只有部分客戶需要，所以做成 `heic.so`，設定檔開啟時才載入。

POSIX 定義了四個函式（`<dlfcn.h>`）：

| 函式 | 作用 | 重點 |
|---|---|---|
| `dlopen(path, flags)` | 載入 `.so`，回傳 handle | 同一個檔案重複 `dlopen` 只會增加參考計數；`flags` 用 `RTLD_NOW`（立即解析所有符號，缺符號就失敗）或 `RTLD_LAZY`，再加上 `RTLD_LOCAL`（glibc 的預設，符號不給之後載入的模組用；macOS 的預設則是 `RTLD_GLOBAL`）或 `RTLD_GLOBAL` |
| `dlsym(handle, name)` | 用名字找符號，回傳位址 | 回傳 `void *`，要轉成正確的函式指標型別（第 10 章）；型別錯了沒有任何檢查 |
| `dlclose(handle)` | 參考計數減一，歸零時可能卸載 | 卸載後還留著的函式指標會變成懸空指標 |
| `dlerror()` | 回傳最近一次錯誤的文字說明 | 讀一次就清除 |

`thumbd` 的 plugin 載入邏輯大致如下（片段，不可單獨執行）：

```c
typedef int (*decode_fn)(const unsigned char *buf, size_t len, struct image *out);

void *h = dlopen("/opt/thumbd/plugins/heic.so", RTLD_NOW | RTLD_LOCAL);
if (!h) { log_error("載入 HEIC plugin 失敗：%s", dlerror()); return -1; }
decode_fn decode = (decode_fn)dlsym(h, "thumbd_plugin_decode");
if (!decode) { log_error("plugin 缺少進入點：%s", dlerror()); dlclose(h); return -1; }
```

用 `RTLD_NOW` 而不是 `RTLD_LAZY`，理由和 19.6 節的 BIND_NOW 相同：plugin 缺符號時，在載入當下就失敗，而不是處理到第一張 HEIC 圖時才讓 worker 當機。

這個機制在你熟悉的高階語言裡無所不在。Python 的 `import numpy` 最後會 `dlopen` 一堆 `.cpython-3xx-x86_64-linux-gnu.so`；Java 的 `System.loadLibrary` 載入 JNI library；Node.js 的原生模組（`.node` 檔）其實也是 shared library。這些環境裡的「`ImportError: ... cannot open shared object file`」和本章故事是同一類問題。

## 19.9 ABI 相容與 symbol versioning

**API**（application programming interface）是原始碼層級的約定：函式叫什麼、參數是什麼型別。**ABI**（application binary interface）是二進位層級的約定：struct 每個欄位的位移與大小、參數放在哪些暫存器（第 9 章的 calling convention）、符號名稱、enum 的數值。動態連結的執行檔與 library 是分別編譯的，它們之間只靠 ABI 溝通，沒有編譯器幫你檢查。

很多看起來無害的原始碼改動，其實會破壞 ABI：

| 改動 | API 相容？ | ABI 相容？ | 為什麼 |
|---|---|---|---|
| 新增一個函式 | 是 | 是 | 舊程式不會用到它 |
| 在 public struct 中間插入欄位 | 是（重新編譯即可） | **否** | 後面欄位的位移全變了，舊程式讀錯位置（本章故事的成因） |
| 在 public struct 尾端加欄位 | 是 | 通常否 | 若呼叫端負責配置 struct（例如放在 stack），大小就不夠 |
| 把參數從 `int` 改成 `long` | 多半是 | 否 | 舊程式只設定 32-bit，callee 讀 64-bit |
| 刪除或改名一個匯出函式 | 否 | 否 | 舊程式會在載入或第一次呼叫時找不到符號 |
| 改變 enum 的數值 | 是 | 否 | 舊程式編進去的是舊數字 |
| 修改 header 裡 `inline` 函式或巨集的內容 | 是 | 不一致 | 舊程式內嵌的是舊版本的邏輯 |

再看本章的故事：`imgconv` 那份 `libjpeg.so.8` 的 `struct jpeg_decompress_struct` 欄位版面和系統版不同。`thumbd` 依照**編譯時** header 的版面配置這個 struct、填好欄位，傳給**執行時**載入的那份 library；library 依照它自己的版面去讀，讀到的指標其實是別的欄位，一解參考就 segfault。為什麼只有三成的 JPEG 出事？因為只有走到特定欄位的程式路徑（例如某些顏色空間的圖片）才會讀到錯位的指標。這也說明了 ABI 錯誤的可怕：它不一定立刻當機，可能只是偶爾算錯。

### Symbol versioning

soname 是整個 library 層級的版本號，太粗。glibc 這類需要長期相容的 library 用 **symbol versioning**（符號版本）：每個匯出符號附帶一個版本標籤，同一個函式可以同時存在新舊兩個實作。

經典例子是 `memcpy`：glibc 2.14 改了 `memcpy` 的實作，讓來源與目的重疊時的行為和以前不同（重疊時本來就是 undefined behavior，但有舊程式依賴舊行為）。為了不弄壞舊程式，glibc 同時保留 `memcpy@GLIBC_2.2.5`（舊行為）與 `memcpy@GLIBC_2.14`（新實作）。在新系統上連結的程式會記錄「我要 `memcpy@GLIBC_2.14`」，舊執行檔則繼續拿到舊版。

這也解釋了工作上最常見的部署錯誤之一：

```text
./thumbd: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.34' not found (required by ./thumbd)
```

意思是：`thumbd` 在 glibc 2.34 以上的機器上編譯，用到了某個帶 `GLIBC_2.34` 標籤的符號（在 glibc 2.34 以上連結的程式幾乎都會引用 `__libc_start_main@GLIBC_2.34`，所以就算程式碼沒用到新函式也會中）；部署目標的 glibc 比較舊，沒有這個版本。glibc 只保證**向後相容**（舊程式在新 glibc 上能跑），不保證反過來。所以標準做法是：**在你要支援的最舊系統上編譯**（或用對應的 sysroot、容器），而不是在開發機的最新系統上編譯再拿去舊機器跑。`objdump -T ./thumbd | grep GLIBC_` 可以列出執行檔要求的所有版本，找出最大的那一個。

> [!note] 想讓自己的 library 好維護
> 公開 API 用 `__attribute__((visibility("default")))`，其餘用 `-fvisibility=hidden` 隱藏；public struct 用 opaque pointer（只在 header 宣告 `struct jpeg_ctx;`，由 library 負責配置），呼叫端就不會依賴它的大小與版面；真的要做不相容改動時，換 soname 主版號。

## 19.10 Library interpositioning：攔截函式呼叫

前面幾節一直把「載入了別的版本」當成意外。但同一個機制也可以刻意使用：**library interpositioning**（函式庫插入）是讓程式對某個函式的呼叫，改為先到你寫的包裝函式（wrapper），包裝函式可以記錄、修改參數、計時，再決定要不要呼叫原本的函式。它不需要修改被攔截的程式，有時連重新編譯都不用。

依照「在哪個階段把名字換掉」，分成三種：

| 種類 | 在哪個階段換 | 怎麼做 | 需要什麼 | 限制 |
|---|---|---|---|---|
| compile-time | 前處理 | 用巨集 `#define malloc(n) my_malloc(n, __FILE__, __LINE__)`，`-I` 讓自己的 header 先被找到 | 原始碼，要重新編譯 | 只影響有 include 這個 header 的檔案；library 內部的呼叫攔不到 |
| link-time | static 連結 | GNU ld 的 `-Wl,--wrap=malloc`：把對 `malloc` 的未定義引用改接到 `__wrap_malloc`，`__real_malloc` 則接到原本的 `malloc` | 目的檔，要重新連結 | 只替換跨目的檔的未定義引用；macOS 的 linker 不支援 |
| run-time | 載入時 | `LD_PRELOAD=./shim.so ./thumbd`，shim 定義同名函式，用 `dlsym(RTLD_NEXT, "malloc")` 找到原版 | 只要執行檔 | static 連結的程式無效；secure-execution 模式（setuid）會限制；macOS 用 `DYLD_INSERT_LIBRARIES`，受 SIP 限制 |

run-time interpositioning 能成功，完全是因為 19.5 節提到的規則：dynamic linker 解析符號時，依「執行檔、然後各 library 依載入順序」搜尋，第一個找到的定義勝出。`LD_PRELOAD` 指定的 library 被插在執行檔之後、所有 `NEEDED` 之前，所以它的 `malloc` 會比 libc 的先被找到。`RTLD_NEXT` 的意思是「從我之後的模組開始找」，因此能拿到原本的 libc `malloc`。

```text
 符號搜尋順序（global scope）
 ┌─────────┐   ┌──────────────────┐   ┌────────────┐   ┌─────────┐
 │ thumbd  │ → │ shim.so          │ → │ libjpeg.so │ → │ libc.so │
 │（執行檔）│   │（LD_PRELOAD 插入）│   │            │   │ malloc  │
 └─────────┘   │ malloc ← 先找到   │   └────────────┘   └─────────┘
               │ dlsym(RTLD_NEXT) ─┼──────────────────────────▲
               └──────────────────┘   「從我之後開始找」
```

這個機制在工作上很常見，而且你可能每天都在用：

- **換 allocator 而不重新編譯**：`LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 ./thumbd`，用 jemalloc 取代 glibc 的 malloc（第 25 章）。
- **記憶體分析工具**：heaptrack 一類的工具用 preload 攔截 `malloc`／`free` 記錄呼叫堆疊。
- **測試與故障注入**：讓 `write` 每第 100 次回傳 short count（第 27 章），測試錯誤處理路徑；或讓 `time` 回傳假時間測試憑證過期。
- **`ltrace`**：追蹤 library 函式呼叫。它用的是 `ptrace` 在 PLT 項目上設中斷點，原理和 preload 不同，但同樣是利用動態連結「呼叫都經過 PLT」這個特性。

> [!warning] 常見誤解
> 「用 `LD_PRELOAD` 攔截 `malloc`，就能看到所有的記憶體配置」。不一定：編譯器可能把某些 `malloc` 呼叫最佳化掉，library 內部用 hidden 符號或直接呼叫的路徑攔不到，static 連結的程式完全不受影響。沒攔到不代表沒發生。另外，攔截 `malloc` 的 wrapper 裡如果呼叫 `printf`，而 `printf` 又呼叫 `malloc`，就會無限遞迴，所以這類 wrapper 通常改用 `write` 直接輸出。

`LD_PRELOAD` 也是攻擊面：如果攻擊者能寫入 `/etc/ld.so.preload`（對所有程式生效的 preload 設定檔）或控制某個服務的環境變數，就能把程式碼注入所有程式。這也是為什麼 setuid 程式在 secure-execution 模式下會限制 preload。

## 19.11 動手做：手算 relocation、反查符號來源、攔截函式

### 程式一：用 Python 驗算 19.2 節的 relocation

這段程式拿 19.2 節 `objdump` 印出的真實位元組與 relocation entry，套用 19.2 節假設的位址，自動算出 linker 要寫入的值：

```python
import struct

# main.o 的 .text（取自 objdump -dr，-fno-pic），洞都還是 00
text = bytearray.fromhex(
    "50" "bf80020000" "e800000000" "8b1500000000" "bf00000000"
    "89c6" "31c0" "e800000000" "31c0" "59" "c3")

# objdump -r 列出的 relocation：(offset, type, symbol, addend)
relocs = [
    (0x07, "R_X86_64_PLT32", "resize", -4),
    (0x0d, "R_X86_64_PC32", "quality", -4),
    (0x12, "R_X86_64_32", ".rodata.str1.1", 0),
    (0x1b, "R_X86_64_PLT32", "printf", -4),
]

# 假設 linker 決定的最終位址（一個非 PIE 執行檔的典型配置）
main_addr = 0x401130
symbols = {"resize": 0x401160, "printf": 0x401030,     # printf 走 PLT stub
           "quality": 0x404028, ".rodata.str1.1": 0x402004}

for off, rtype, sym, addend in relocs:
    S, A, P = symbols[sym], addend, main_addr + off
    if rtype == "R_X86_64_32":
        value = S + A                     # 絕對位址
        field = struct.pack("<I", value)
        formula = f"S + A = {S:#x} + {A}"
    else:
        value = S + A - P                 # PC-relative：目標減去「這個欄位的位址」
        field = struct.pack("<i", value)
        formula = f"S + A - P = {S:#x} + ({A}) - {P:#x}"
    text[off:off + 4] = field
    print(f"{rtype:15} {sym:15} {formula:38} = {value:#x}  → bytes {field.hex(' ')}")

print("修補後的 .text：", text.hex(" "))
# 驗證：call 的目標 = 下一條指令位址 + rel32
rel = struct.unpack("<i", text[0x07:0x0b])[0]
print(f"驗證：call 下一條指令在 {main_addr + 0x0b:#x}，加上 {rel:#x} = {main_addr + 0x0b + rel:#x}（resize）")
```

在 macOS arm64、Python 3 上的實際輸出：

```text
R_X86_64_PLT32  resize          S + A - P = 0x401160 + (-4) - 0x401137 = 0x25  → bytes 25 00 00 00
R_X86_64_PC32   quality         S + A - P = 0x404028 + (-4) - 0x40113d = 0x2ee7  → bytes e7 2e 00 00
R_X86_64_32     .rodata.str1.1  S + A = 0x402004 + 0                   = 0x402004  → bytes 04 20 40 00
R_X86_64_PLT32  printf          S + A - P = 0x401030 + (-4) - 0x40114b = -0x11f  → bytes e1 fe ff ff
修補後的 .text： 50 bf 80 02 00 00 e8 25 00 00 00 8b 15 e7 2e 00 00 bf 04 20 40 00 89 c6 31 c0 e8 e1 fe ff ff 31 c0 59 c3
驗證：call 下一條指令在 0x40113b，加上 0x25 = 0x401160（resize）
```

逐行對照：

1. 四個值和 19.2 節的手算完全相同。`struct.pack("<i", …)` 的 `<` 表示 little-endian、`i` 表示有號 32-bit，這正是 x86-64 指令裡 rel32 欄位的格式。
2. `printf` 那一筆是負數 −0x11f，二補數寫成 `e1 fe ff ff`：PLT 在 `.text` 前面，所以 `call` 往回跳。
3. 最後一行反向驗證：從 `call` 的下一條指令位址加上寫入的 rel32，回到了 `resize`。真實的 linker 就是對成千上萬個洞重複這個計算。

### 程式二：用 `dlopen` 載入 library，並反查符號來自哪個檔案

工作上常常需要回答「這個函式到底是哪個 library 提供的」。`dladdr` 可以從一個位址反查它所在的檔案與最接近的符號：

```c
#define _GNU_SOURCE            /* Linux 上 dladdr 需要這個巨集 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

/* 依平台嘗試幾個常見的 libm 名稱（Linux 是 .so.6，macOS 是 .dylib） */
static void *open_libm(void) {
    const char *names[] = {"libm.so.6", "libm.dylib", "/usr/lib/libm.dylib"};
    for (size_t i = 0; i < sizeof names / sizeof names[0]; i++) {
        void *h = dlopen(names[i], RTLD_NOW | RTLD_LOCAL);
        if (h) { printf("dlopen(\"%s\") 成功\n", names[i]); return h; }
    }
    return NULL;
}

/* 用 dladdr 反查：這個位址落在哪個檔案、最接近哪個符號 */
static void where_is(const char *label, const void *addr) {
    Dl_info info;
    if (dladdr(addr, &info) && info.dli_fname) {
        const char *base = strrchr(info.dli_fname, '/');
        printf("%-8s %p  來自 %s（符號 %s）\n", label, addr,
               base ? base + 1 : info.dli_fname, info.dli_sname ? info.dli_sname : "?");
    }
}

int main(void) {
    void *libm = open_libm();
    if (!libm) { printf("找不到 libm：%s\n", dlerror()); return 0; }

    /* dlsym 回傳 void*，轉成函式指標再呼叫 */
    double (*cos_fn)(double) = (double (*)(double))dlsym(libm, "cos");
    printf("cos(0.5) = %.6f\n", cos_fn(0.5));

    /* 查一個不存在的符號：dlsym 回傳 NULL，原因用 dlerror 取得 */
    void *missing = dlsym(libm, "jpeg_read_header");
    printf("jpeg_read_header → %p（%s）\n", missing, missing ? "found" : "找不到");

    where_is("cos", (const void *)cos_fn);
    where_is("printf", (const void *)printf);
    where_is("main", (const void *)main);
    dlclose(libm);
    return 0;
}
```

在 macOS arm64（Apple clang 21）連續執行兩次的實際輸出：

```text
dlopen("libm.dylib") 成功
cos(0.5) = 0.877583
jpeg_read_header → 0x0（找不到）
cos      0x19797fad4  來自 libsystem_m.dylib（符號 cos）
printf   0x187a85964  來自 libsystem_c.dylib（符號 printf）
main     0x1004544b0  來自 dl（符號 main）
dlopen("libm.dylib") 成功
cos(0.5) = 0.877583
jpeg_read_header → 0x0（找不到）
cos      0x19797fad4  來自 libsystem_m.dylib（符號 cos）
printf   0x187a85964  來自 libsystem_c.dylib（符號 printf）
main     0x1000044b0  來自 dl（符號 main）
```

逐步解說：

1. `dlopen("libm.so.6")` 在 macOS 上失敗，第二個名字才成功。在 Linux 上第一個就會成功，`cos` 會顯示來自 `libm.so.6`。這種「依平台嘗試多個名字」的寫法，正是跨平台 plugin 載入器常見的樣子。舊版 glibc（2.34 以前）上編譯這段程式要加 `-ldl`。
2. `dlsym` 找不到 `jpeg_read_header` 時回傳 NULL。真實程式一定要檢查，否則下一行呼叫 NULL 函式指標就是 segfault。
3. `dladdr` 告訴我們 `printf` 實際來自 `libsystem_c.dylib`。在 Linux 上做同樣的事，就能在故事那種情況下直接印出 `jpeg_read_header` 是從 `/opt/imgconv/lib/libjpeg.so.8` 來的。把這個檢查放進 `thumbd` 的啟動 log，下次就不必等當機才發現。
4. 兩次執行，`main` 的位址不同（`0x1004544b0` 與 `0x1000044b0`），但 `cos`、`printf` 的位址相同。執行檔是 PIE，每次啟動都隨機挑基底位址；macOS 的系統 library 放在 dyld shared cache 裡，它的隨機位址是開機時決定的，所以同一次開機內不變。Linux 上每次執行，library 的位址也會隨機變化。

### 程式三：compile-time interpositioning，追蹤 `thumbd` 的配置

這是三種 interpositioning 裡唯一能在任何平台、單一檔案示範的。平常巨集會放在一個 `trace_malloc.h`，編譯時用 `-I./trace` 讓它被優先 include；這裡為了能直接執行，把它放在同一個檔案的開頭（存成 `ct.c`）：

```c
#include <stdio.h>
#include <stdlib.h>

/* ---- 這一段平常放在 trace_malloc.h，用 -I 讓它比系統標頭先被找到 ---- */
static long live_blocks;
static void *trace_malloc(size_t n, const char *file, int line) {
    void *p = malloc(n);                 /* 這裡還沒 #define，呼叫的是真正的 malloc */
    live_blocks++;
    printf("[trace] %s:%d malloc(%zu) = %s\n", file, line, n, p ? "ok" : "NULL");
    return p;
}
static void trace_free(void *p, const char *file, int line) {
    if (p) live_blocks--;
    printf("[trace] %s:%d free\n", file, line);
    free(p);
}
#define malloc(n) trace_malloc((n), __FILE__, __LINE__)
#define free(p)   trace_free((p), __FILE__, __LINE__)
/* ---- 以下是「thumbd 的程式」，完全不用改 ---- */

static unsigned char *make_thumb(int w, int h) {
    return malloc((size_t)w * h * 4);    /* RGBA 每像素 4 bytes */
}

int main(void) {
    unsigned char *a = make_thumb(160, 120);
    unsigned char *b = make_thumb(320, 240);
    free(a);                             /* 故意忘了 free(b) */
    printf("還沒釋放的區塊：%ld\n", live_blocks);
    (void)b;
    return 0;
}
```

在 macOS arm64 上的實際輸出：

```text
[trace] ct.c:22 malloc(76800) = ok
[trace] ct.c:22 malloc(307200) = ok
[trace] ct.c:28 free
還沒釋放的區塊：1
```

1. 160 × 120 × 4 = 76,800、320 × 240 × 4 = 307,200，和輸出一致。
2. 兩次 `malloc` 都回報第 22 行，也就是 `make_thumb` 裡那一行，而不是呼叫 `make_thumb` 的地方。`__FILE__`／`__LINE__` 只記錄巨集展開的位置，要知道完整呼叫路徑得記錄 stack trace，這正是 ASan、heaptrack 這類工具做的事（第 26 章）。
3. 這個方法的弱點也很明顯：libjpeg 內部的 `malloc` 不會經過這個巨集，因為 libjpeg 是另外編譯的。

### 程式四：run-time interpositioning（`LD_PRELOAD`）

要攔截不能重新編譯的程式，就用 run-time 版本。下面是 Linux 版的 shim，記錄 `thumbd` 開啟的每一個檔案：

```c
// linux-only
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>

/* 與 libc 同名同型別：LD_PRELOAD 讓這個定義先被找到 */
FILE *fopen(const char *path, const char *mode) {
    static FILE *(*real_fopen)(const char *, const char *);
    if (!real_fopen)                                    /* 第一次呼叫時找原版 */
        real_fopen = (FILE *(*)(const char *, const char *))dlsym(RTLD_NEXT, "fopen");
    FILE *f = real_fopen(path, mode);
    fprintf(stderr, "[shim] fopen(\"%s\", \"%s\") = %p\n", path, mode, (void *)f);
    return f;
}
```

```bash
gcc -shared -fPIC -o shim.so shim.c          # 舊版 glibc 要加 -ldl
LD_PRELOAD=./shim.so ./thumbd --config /etc/thumbd.conf
```

```text
示意輸出（Linux x86-64）
[shim] fopen("/etc/thumbd.conf", "r") = 0x55d0c8e4a2a0
[shim] fopen("/var/lib/thumbd/watermark.png", "rb") = 0x55d0c8e4b4c0
```

macOS 沒有 `LD_PRELOAD`，對應的是 `DYLD_INSERT_LIBRARIES`，而且 macOS 預設採用 two-level namespace（每個符號綁定到特定的 library），所以不能只靠同名函式，要在 `__DATA,__interpose` section 放一張「替換誰」的表：

```c
#include <stdio.h>
static FILE *my_fopen(const char *path, const char *mode) {
    fprintf(stderr, "[shim] fopen(\"%s\", \"%s\")\n", path, mode);
    return fopen(path, mode);   /* 在 interpose 機制下，這裡呼叫的是原版 */
}
__attribute__((used)) static struct { const void *rep, *orig; } interpose_fopen
    __attribute__((section("__DATA,__interpose"))) = { (const void *)my_fopen, (const void *)fopen };
```

用一個只會開 `/etc/hosts` 再印出 `app: done` 的小程式測試，在本機 macOS arm64 實際執行：

```text
$ cc -O1 -dynamiclib -o libshim.dylib shim.c
$ ./app
app: done
$ DYLD_INSERT_LIBRARIES=./libshim.dylib ./app
[shim] fopen("/etc/hosts", "r")
app: done
```

同一個 `app` 執行檔，沒有重新編譯，只多一個環境變數，行為就改變了。這個能力反過來看就是本章故事的教訓：**執行環境可以改變程式實際執行的程式碼**。

## 19.12 在工作上怎麼用

### 情境一：「本機能跑，上線就不能跑」

這是動態連結最常見的工作情境。依照錯誤發生的時間點，分層排查：

```text
 程式在新環境無法啟動或行為異常
   │
   ├─ 1. 錯誤是 "No such file or directory"，但檔案明明存在？
   │      → readelf -l 看 PT_INTERP；目標系統可能沒有那個 dynamic linker
   │        （例如 glibc 編譯的程式放進 Alpine/musl 容器）
   │
   ├─ 2. "error while loading shared libraries: X: cannot open shared object file"
   │      → readelf -d 看 NEEDED 與 RUNPATH；ldd 看哪一個是 "not found"
   │      → 修：安裝套件、設定 RUNPATH，或把 library 一起打包
   │
   ├─ 3. "version `GLIBC_2.xx' not found" 或 "undefined symbol: foo"
   │      → objdump -T 看要求的版本；在目標的最舊系統（或容器）上重新編譯
   │
   ├─ 4. 能啟動，但特定請求當機或結果怪異
   │      → /proc/PID/maps 確認實際載入的每個 .so 路徑
   │      → LD_DEBUG=libs,bindings 看符號被綁到哪個檔案
   │      → 懷疑 ABI 不一致：比對編譯時 header 版本與執行時 library 版本
   │
   └─ 5. 只有某台機器有問題
          → 比較兩台的環境變數（LD_LIBRARY_PATH、LD_PRELOAD）、/etc/ld.so.preload、
            /etc/ld.so.conf.d/ 與 ldconfig -p 的結果
```

第 1 點值得特別記住：shell 回報「找不到檔案」，但 `ls` 明明看得到，原因常常是 `PT_INTERP` 指向的 `/lib64/ld-linux-x86-64.so.2` 不存在，kernel 的 `execve` 回傳 `ENOENT`（第 20 章的 errno）。

### 情境二：部署前的檢查清單

`thumbd` 團隊在故事之後，把下面幾項加進 CI 與部署流程：

| 檢查 | 指令 | 失敗時代表 |
|---|---|---|
| 執行檔需要的最高 glibc 版本 | `objdump -T thumbd \| grep -o 'GLIBC_[0-9.]*' \| sort -uV \| tail -1` | 編譯環境比目標環境新 |
| 所有依賴都找得到 | `ldd thumbd \| grep 'not found'`（在目標 image 裡跑） | image 缺套件 |
| 依賴都來自預期目錄 | `ldd thumbd`，比對路徑允許清單 | 有 `LD_LIBRARY_PATH` 或額外目錄介入 |
| 安全強化 | `readelf -d thumbd \| grep -E 'BIND_NOW\|FLAGS'`、`readelf -l` 看 `GNU_RELRO` | 沒開 full RELRO |
| 環境乾淨 | 確認服務的 unit 檔或容器設定沒有全域的 `LD_LIBRARY_PATH`／`LD_PRELOAD` | 本章故事的成因 |

### 情境三：不改程式碼就量測或修正行為

- 懷疑是 malloc 碎片造成 RSS 上升（第 25 章）：先用 `LD_PRELOAD` 換成 jemalloc 跑一段時間比較，再決定要不要正式改連結方式。
- 要知道一個第三方 binary 讀了哪些檔案：寫一個 `fopen`／`open` 的 shim，或直接用 `strace`（第 20 章）。
- 懷疑某個 library 函式慢：`ltrace -c` 統計 library 呼叫次數與時間，或用 `perf` 看 PLT 之後的符號。

### 情境四：Python、Node、Java 工程師也會遇到

`pip install` 裝的套件帶著預先編譯好的 `.so`（wheel），它們同樣有 `NEEDED` 與 glibc 版本需求。wheel 檔名中的 `manylinux_2_28` 就是在宣告「需要 glibc 2.28 以上」。看到 `ImportError: libxxx.so: cannot open shared object file`，用本章的工具對那個 `.so` 執行 `ldd`，就能知道缺什麼。

## 19.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| `error while loading shared libraries: libX.so.N: cannot open shared object file` | 搜尋路徑上沒有這個 soname | `ldd` 顯示 `not found`；`ldconfig -p \| grep libX` | 安裝對應套件、設定 RUNPATH（`$ORIGIN`）、或執行 `ldconfig` |
| 執行檔存在卻顯示 `No such file or directory` | `PT_INTERP` 指向的 dynamic linker 不存在（glibc 程式放到 musl 系統、架構不符） | `readelf -l` 看 interpreter；`file thumbd` | 用目標系統的工具鏈編譯，或改用 static 連結 |
| `version 'GLIBC_2.34' not found` | 在較新的 glibc 上編譯，部署到較舊的系統 | `objdump -T` 看要求的版本；目標機 `ldd --version` | 在最舊的目標環境（容器、sysroot）中編譯 |
| 換 library 版本後偶發 segfault 或數值錯誤 | ABI 不相容：struct 版面、參數型別或 enum 改變，但 soname 沒換 | `/proc/PID/maps` 看實際載入路徑；比對編譯時 header 版本 | 用與 header 相符的 library；library 端修正 soname |
| `relocation R_X86_64_32 against ... can not be used when making a shared object` | 把沒加 `-fPIC` 的目的檔連進 `.so` | 錯誤訊息直接點名目的檔 | 那些檔案重新以 `-fPIC` 編譯 |
| `relocation truncated to fit: R_X86_64_PC32` | 程式或靜態資料超過 ±2 GiB，32-bit 位移放不下 | 看是否有巨大的 static 陣列 | 改成執行時配置，或用 `-mcmodel=medium` |
| `LD_PRELOAD` 沒效果 | 目標是 static 連結、setuid 程式，或函式被 inline／內部直接呼叫 | `file` 看是否 statically linked；`nm -D` 看是否有該動態符號 | 改用其他方法（`strace`、eBPF、重新編譯） |
| plugin 載入後第一次使用才當機 | 用 `RTLD_LAZY`，缺的符號到呼叫時才發現 | `LD_DEBUG=bindings`；`nm -D --undefined-only plugin.so` | 改用 `RTLD_NOW`，載入時就失敗 |

## 19.14 動手練習

1. **手算**：延續 19.2 節，若 linker 改把 `main` 放在 `0x401200`，其他位址不變，四個洞要寫入的值各是多少？哪一個不會變，為什麼？（驗證方法：修改 19.11 節程式一的 `main_addr` 重新執行。提示：絕對位址的那一筆與 P 無關。）
2. **手算**：一條 `call` 指令位於 `0x7f00` 處，機器碼為 `e8 f0 ff ff ff`。它的目標位址是多少？（答案：rel32 = −0x10，下一條指令位址 `0x7f05`，目標 `0x7ef5`。）
3. 修改 19.11 節程式二，用 `dlsym(RTLD_DEFAULT, "printf")`（需要 `_GNU_SOURCE` 或 macOS 的 `<dlfcn.h>`）取得 `printf`，與直接寫 `printf` 取得的位址比較，並用 `dladdr` 印出它的來源檔案。如果你有 Linux 環境，加印 `jpeg_read_header`（需連結 `-ljpeg`）的來源。
4. 擴充 19.11 節程式三，替 `realloc` 也加上追蹤，並在程式結束前印出「仍未釋放的總 bytes 數」。思考：要記錄每個區塊的大小，資料要放在哪裡？
5. 在 Linux 上建立 `libhello.so`（兩個版本，輸出不同的字串），讓同一個執行檔分別透過 RUNPATH、`LD_LIBRARY_PATH` 載入兩個版本，用 `LD_DEBUG=libs` 觀察搜尋順序，驗證 19.7 節的優先序。
6. 對你工作上的一個服務（或系統上的 `/usr/bin/python3`）執行 `readelf -d`、`ldd`、`objdump -T | grep GLIBC_`，寫下它的 `NEEDED` 清單、是否有 RUNPATH、需要的最高 glibc 版本，以及是否開啟 BIND_NOW。

## 本章重點整理

- 編譯器不知道外部符號的最終位址，會在指令中留下空位並產生 relocation entry；linker 先合併 section、配置位址，再依 entry 修補。
- relocation entry 記錄 offset、type、symbol、addend；絕對位址用 S + A，PC-relative 用 S + A − P，addend 的 −4 來自「以下一條指令為基準」。
- 執行檔的 program header 描述 segment 如何映射與權限；section 給 linker 看，segment 給 loader 看，`.bss` 與符號表在執行時不佔檔案內容。
- `execve` 後 kernel 先把控制權交給 `PT_INTERP` 指定的 dynamic linker，它載入所有 `NEEDED`、做 dynamic relocation、執行初始化，最後才跳到 `_start` 與 `main`。
- shared library 讓程式碼頁跨 process 共享、可以獨立更新，代價是執行環境必須提供 ABI 相容的版本；soname 是 dynamic linker 實際尋找的名字。
- PIC 對模組內部的存取用 `%rip` 相對定址，對外部或可被 interpose 的符號經由每個 process 一份的 GOT；`-fvisibility=hidden` 能減少不必要的 GOT 存取。
- PLT 搭配 GOT 實作 lazy binding，第一次呼叫才解析；現代系統常用 BIND_NOW 與 full RELRO 讓 GOT 唯讀，並讓缺少的符號在啟動時就失敗。
- glibc 的 dynamic linker 依 RPATH、`LD_LIBRARY_PATH`、RUNPATH、`ld.so.cache`、預設目錄的順序尋找 library，第一個找到的勝出。
- 要知道 process 實際用了哪個 library，`/proc/PID/maps` 最可靠；`ldd` 與 `LD_DEBUG` 反映的是目前環境下的解析結果。
- `dlopen`／`dlsym` 讓程式在執行時載入 plugin；Python、Java、Node 的原生擴充都建立在這個機制上。
- ABI 比 API 嚴格：在 struct 中插入欄位、改參數型別、改 enum 值都會破壞 ABI；不相容改動應更換 soname 主版號。
- glibc 用 symbol versioning 保持向後相容，所以要在最舊的目標環境上編譯，否則會出現 `GLIBC_2.xx not found`。
- library interpositioning 可以在 compile-time（巨集）、link-time（`--wrap`）、run-time（`LD_PRELOAD` 與 `RTLD_NEXT`）攔截函式，常用於換 allocator、量測與故障注入，但攔不到 static 連結與內部呼叫。

## 延伸問答

> [!question]- Q1. relocation 在連結時做一次，dynamic linker 載入時又做一次，兩者有什麼不同？
> 連結時的 relocation 由 linker（`ld`）處理目的檔裡的 entry，把所有「同一個輸出檔內就能決定」的位址填好，例如 `main` 呼叫同一個執行檔裡的 `resize`。處理完之後，這些 entry 就不存在了，執行檔裡不會留下它們。
>
> 有些位址在連結時仍然無法決定：外部 `.so` 裡的函式與變數、以及 PIE 或 `.so` 被載入到隨機基底後才知道的絕對指標。linker 會把它們轉成 **dynamic relocation**（放在 `.rela.dyn`、`.rela.plt`，類型如 `R_X86_64_GLOB_DAT`、`R_X86_64_JUMP_SLOT`、`R_X86_64_RELATIVE`），由 dynamic linker 在載入時處理。設計上會盡量把這些修補集中在 GOT 與資料段，讓程式碼段保持不變、可以共享。

> [!question]- Q2. 手算題：一個 `R_X86_64_PC32` relocation 的 P = `0x1000`、S = `0x3000`、A = −4，寫入的 4 個 byte 是什麼？如果 S = `0x0800` 呢？
> 第一種情況：S + A − P = `0x3000` − 4 − `0x1000` = `0x1ffc`，little-endian 寫成 `fc 1f 00 00`。執行時 `%rip` 是下一條指令 `0x1004`，加上 `0x1ffc` 得到 `0x3000`，驗證正確。
>
> 第二種情況：`0x0800` − 4 − `0x1000` = −`0x804`。用 32-bit 二補數表示是 `0xfffff7fc`，寫成 `fc f7 ff ff`。這說明 PC-relative 欄位是有號數，可以往前也可以往後指，範圍是 ±2 GiB；超出時 linker 會報 `relocation truncated to fit`。

> [!question]- Q3. 為什麼 library 程式碼可以被多個 process 共享，GOT 卻必須每個 process 一份？
> 因為每個 process 可能把同一個 library 與它依賴的其他 library 映射在不同的位址（ASLR 讓這幾乎是必然的）。如果程式碼裡寫著外部符號的絕對位址，每個 process 都需要不同的程式碼內容，程式碼頁就無法共享，還要讓程式碼頁可寫，違反 W^X。
>
> PIC 把「會因 process 而異的東西」全部集中到 GOT：程式碼只用固定的相對距離找到 GOT，GOT 裡才放真正的位址。GOT 在可寫的資料段，用 private mapping 映射（第 24 章），每個 process 修改的是自己的副本；程式碼段保持唯讀，在實體記憶體裡只有一份。

> [!question]- Q4. 你在 production 看到 `thumbd` 只有在某一台主機上處理 JPEG 會 segfault，其他主機正常，執行檔完全相同。你會怎麼查？
> 執行檔相同而行為不同，先懷疑「執行環境改變了實際執行的程式碼」。第一步看那台機器上執行中 process 的 `/proc/PID/maps`，確認 `libjpeg` 與其他相關 library 的實際路徑與版本，和正常的主機比較；也可以用 `md5sum` 比對兩台的 `.so` 檔。
>
> 接著找出為什麼會載入不同的檔案：比較 process 的環境變數（`/proc/PID/environ` 裡的 `LD_LIBRARY_PATH`、`LD_PRELOAD`）、`/etc/ld.so.preload`、`/etc/ld.so.conf.d/` 與 `ldconfig -p` 的輸出。用 `LD_DEBUG=libs` 跑一次可以直接看到搜尋路徑來自哪個機制。找到原因後，從根本移除不該存在的路徑，而不是在 `thumbd` 這邊再加一層 `LD_LIBRARY_PATH` 蓋過去。

> [!question]- Q5. 面試題：說明一次外部函式呼叫在 lazy binding 下，第一次與第二次各發生了什麼。
> 第一次：程式碼 `call foo@plt`，PLT 項目執行 `jmp *GOT[n]`，但 GOT[n] 初始值指回同一個 PLT 項目的下一條指令，於是接著 `push` 這個函式的 relocation 索引並跳到 PLT[0]。PLT[0] 推入模組識別（GOT[1]）並跳到 GOT[2] 指向的 dynamic linker resolver。resolver 依搜尋順序在已載入的模組中找到 `foo`，把位址寫入 GOT[n]，再跳到 `foo`。
>
> 第二次：`jmp *GOT[n]` 直接跳到 `foo`，只比直接呼叫多一次間接跳躍。可以補充的加分點：lazy binding 要求 GOT 執行中保持可寫，是 GOT overwrite 攻擊的目標，所以現代系統常用 `-z now` 與 full RELRO 在啟動時全部解析並設為唯讀；`-fno-plt` 則讓程式碼直接 `call *foo@GOTPCREL(%rip)`，省去 PLT 那一跳。

> [!question]- Q6. 程式找錯：下面這個 `LD_PRELOAD` 的 malloc wrapper 為什麼一跑就當機或卡住？`void *malloc(size_t n) { static void *(*real)(size_t); if (!real) real = dlsym(RTLD_NEXT, "malloc"); void *p = real(n); printf("malloc(%zu)=%p\n", n, p); return p; }`
> 問題在 `printf`。`printf` 第一次輸出時需要為 stdout 配置緩衝區，會呼叫 `malloc`，而這個 `malloc` 就是 wrapper 自己，於是又呼叫 `printf`，形成無限遞迴，直到 stack overflow。在某些 glibc 版本中，`dlsym` 本身也可能在內部配置記憶體，造成第一次查找時就遞迴。
>
> 常見修法：輸出改用不會配置記憶體的 `write(2, buf, len)` 搭配 `snprintf` 到 stack 上的緩衝區；加一個 thread-local 的「正在 wrapper 中」旗標，遞迴進入時直接呼叫 `real`；必要時在 `real` 還沒找到時，從一塊靜態陣列配置少量記憶體應急。這也說明 interpositioning 雖然強大，wrapper 本身必須非常小心，不能依賴被攔截的函式。

> [!question]- Q7. 為什麼 `-fvisibility=hidden` 常被說「讓 library 變快、也更安全」？
> 變快：預設情況下，`.so` 裡的每個全域符號都可能被執行檔或更早載入的 library interpose，所以編譯器存取它們時必須經過 GOT、呼叫時經過 PLT；GCC 在 `-fPIC` 下預設也不會把這類函式 inline 或做跨函式最佳化（clang 對函式的處理較寬鬆）。19.5 節的組合語言就顯示，`quality` 設成 hidden 後，存取從兩條指令（讀 GOT、再讀值）變成一條。hidden 符號也不會進入動態符號表，dynamic linker 載入時要處理的符號與 relocation 更少，啟動更快。
>
> 更安全、更好維護：只匯出刻意公開的 API，內部函式不會被外部程式意外依賴，日後修改內部實作不必擔心破壞 ABI；也減少了能被 `LD_PRELOAD` 或同名符號意外覆蓋的表面。

> [!question]- Q8. Go 程式常被說「一個執行檔就能部署」，C 程式為什麼常常做不到？要 static 連結有什麼取捨？
> Go 的工具鏈預設自己實作 runtime，純 Go 程式不依賴 libc，產生的是 static 執行檔，沒有 `PT_INTERP`，也就沒有本章的 library 搜尋與 ABI 問題（但只要用到 cgo 或某些系統 resolver 功能，就又會動態連結 libc）。C 程式依賴 libc 與各種系統 library，發行版預設提供的是 `.so`，所以自然是動態連結。
>
> C 也可以 `-static` 連結，好處是部署簡單、不受目標環境 library 版本影響、啟動稍快。代價是：執行檔變大；library 的安全修補必須重新編譯整個程式才能生效；glibc 的部分功能（例如 `getaddrinfo` 透過 NSS 載入的模組、`dlopen`）在 static 連結下會受限或仍需執行時的 `.so`，所以需要完全 static 時，常改用 musl libc。`LD_PRELOAD` 類的工具也全部失效。選擇時要衡量「部署一致性」與「修補與觀測能力」。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 7 章 7.7–7.13 節，relocation 演算法與 PIC 的原始敘述。
- [ELF 規格（Tool Interface Standard）](https://refspecs.linuxfoundation.org/elf/elf.pdf)：section、segment、symbol 與 relocation entry 的正式格式。
- [x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI)：所有 `R_X86_64_*` relocation type 的公式、GOT 與 PLT 的標準布局。
- [Linux man pages](https://man7.org/linux/man-pages/)：`ld.so(8)`（搜尋順序、`LD_*` 環境變數、secure-execution 模式）、`ldd(1)`、`dlopen(3)`、`dladdr(3)`、`ldconfig(8)`。
- [GNU Binutils 文件](https://sourceware.org/binutils/docs/)：`ld` 的 `--wrap`、`-z now`、`-z relro`、`-rpath` 選項，以及 `objdump`、`readelf` 的用法。
