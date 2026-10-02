---
chapter: 9
title: 程序呼叫與 Stack
part: 2
---

# 第 9 章　程序呼叫：Stack Frame 與 Calling Convention

> [!abstract] 本章地圖
> **核心問題**：一個函式呼叫另一個函式時，CPU 怎麼知道做完要回到哪裡、參數放在哪裡、自己的變數會不會被對方弄壞？
>
> **你會學到**：
> - 用 `call`／`ret` 與 return address 解釋「函式怎麼回家」，並能逐條指令手算 `%rsp` 的變化
> - 背出並運用 System V AMD64 calling convention：前六個整數參數、回傳值、浮點參數與超過六個參數時的 stack 布局
> - 畫出一個函式的 stack frame，說明 local 變數、saved register、return address 各在哪裡，以及 16-byte 對齊為什麼要算
> - 分辨 caller-saved 與 callee-saved 暫存器，讀懂編譯器在函式開頭與結尾的 `push`／`pop`
> - 理解 frame pointer、`-fomit-frame-pointer`、red zone 與 stack trace 的關係，知道 profiler 與 debugger 是怎麼「走回」呼叫鏈的
> - 在工作上用 gdb／lldb 讀 core dump 的 stack、估算 thread stack 夠不夠用
>
> **前置知識**：第 7 章（暫存器、`mov`、`push`／`pop`、`lea`）、第 8 章（條件碼、跳躍與迴圈）
>
> **對應 CS:APP 3e**：第 3 章 3.7 節

## 9.1 故事：只在 worker thread 上當掉的解析器

拾光相簿開始支援 TIFF 格式後的第二週，`thumbd` 在 production 偶爾會整個 process 當掉，log 最後一行是 `Segmentation fault`。SRE 阿哲從 core dump 抓出 stack trace 貼給小安（節錄），畫面上同一個函式名稱重複了兩千多行：

```text
#0    parse_ifd (buf=..., off=...) at tiff.c:88
#1    parse_ifd (buf=..., off=...) at tiff.c:112
#2    parse_ifd (buf=..., off=...) at tiff.c:112
...
#2339 parse_ifd (buf=..., off=...) at tiff.c:112
#2340 decode_tiff (...) at tiff.c:30
#2341 handle_request (...) at worker.c:57
```

小安用同一張圖在自己的筆電上跑單元測試，程式完全正常。TIFF 的 metadata 是一層一層的目錄（IFD），`parse_ifd` 遇到子目錄就遞迴呼叫自己；那張圖是使用者上傳的，裡面的子目錄指來指去，形成了一條非常長的鏈。老周看了一眼就說：「這不是邏輯錯，是 stack 用完了。測試在 main thread 跑，main thread 的 stack 有 8 MiB；production 的 worker thread 我們只給 256 KiB。」

小安心裡冒出一串問題：stack 到底是什麼，為什麼會「用完」？每一層遞迴到底吃掉多少 bytes？為什麼 thread 的 stack 和 main thread 不一樣大？當機之後 gdb 又是怎麼知道這兩千多層是誰呼叫誰的？

同一週還有第二件事：效能組用 `perf` 畫 `thumbd` 的 flame graph，結果一大半的呼叫鏈只顯示 `[unknown]`，看不出時間花在哪個函式底下。老周說：「因為我們的 build 拿掉了 frame pointer。」

這兩件事都指向同一個機制：**程序呼叫**（procedure call）。這一章從 `call` 這一條指令開始，一路看到參數、local 變數、暫存器保存、frame pointer 與 stack trace，最後回到 `thumbd`，把這兩個問題解掉。

## 9.2 為什麼需要 stack：一次函式呼叫要記住的四件事

高階語言裡，呼叫函式只是一行 `r = scale(w, 3)`。但在機器層級，CPU 只會「執行下一條指令」或「跳到某個位址」，它沒有「函式」的概念。要把一次呼叫做出來，必須自己處理四件事：

| 要處理的事 | 問題 | x86-64 的做法 | `thumbd` 裡的例子 |
|---|---|---|---|
| 控制轉移 | 跳進去之後，做完要回到哪裡？ | `call` 把 **return address** 存到 stack，`ret` 取回 | `handle_request` 呼叫 `decode_jpeg`，解完要回到 `handle_request` 的下一行 |
| 傳遞資料 | 參數怎麼給、結果怎麼拿回來？ | 前六個整數參數放暫存器，回傳值放 `%rax` | 把影像寬度與縮放倍率傳給 `scale` |
| local 儲存 | 函式自己的變數放哪裡？ | 能放暫存器就放，放不下或要取位址就放 stack | `parse_ifd` 的 48 bytes 暫存區 |
| 保護呼叫者的狀態 | 被呼叫的函式會不會改掉我正在用的暫存器？ | 約定哪些暫存器由誰負責保存 | `handle_request` 呼叫 `decode_jpeg` 之後，還要用原本的連線編號 |

這四件事有一個共同特徵：**最晚被呼叫的函式最早結束**。`worker_loop` 呼叫 `handle_request`，`handle_request` 呼叫 `decode_jpeg`；一定是 `decode_jpeg` 先回來，再輪到 `handle_request`。這就是後進先出（LIFO），剛好是 stack 這種資料結構的行為。所以每次呼叫需要的狀態，就放在一塊叫 **run-time stack**（執行期堆疊）的記憶體裡，一層呼叫佔一塊，叫 **stack frame**（堆疊框）。

Run-time stack 沒有什麼神祕的：它就是 process 位址空間裡一段普通的記憶體，加上一個專門指向「目前頂端」的暫存器 `%rsp`（stack pointer）。在 x86-64 Linux 上，stack 放在使用者位址空間的高處，**往低位址成長**：

```text
 process 位址空間（簡化，第 24 章會詳細看）
 高位址
 ┌──────────────────────────┐
 │ kernel                   │
 ├──────────────────────────┤
 │ main thread 的 stack     │ ← 從這裡往下長
 │          │               │
 │          ▼               │
 │                          │
 │ （mmap 區：library、     │
 │   其他 thread 的 stack） │
 │                          │
 │          ▲               │
 │          │               │
 │ heap（malloc）           │ ← 從這裡往上長
 ├──────────────────────────┤
 │ .data／.bss              │
 │ .text（程式碼）          │
 └──────────────────────────┘
 低位址
```

這張圖要讀出三件事。第一，「stack 頂端」在圖上看起來是最下面，因為它的位址最小；以後看到 stack 圖一定要先找「高位址／低位址」標示，不要靠上下方向判斷。第二，`push` 會讓 `%rsp` 變小、`pop` 會讓 `%rsp` 變大（第 7 章）。第三，每個 thread 都有自己的一塊 stack，main thread 的在最上面，其他 thread 的 stack 是建立 thread 時另外用 `mmap` 配置的，大小在建立時就決定了。這正是故事中 main thread 與 worker thread 表現不同的原因。

> [!warning] 常見誤解
> 「stack 是 C library 提供的資料結構。」不是。硬體只認 `%rsp` 這個暫存器，以及 `push`、`pop`、`call`、`ret` 這幾條會自動調整 `%rsp` 的指令。stack 就是一段記憶體，frame 的布局是編譯器和 ABI 約定出來的，沒有任何東西在執行期檢查「frame 有沒有越界」。

## 9.3 call 與 ret：return address 是怎麼來的

先看最核心的機制：怎麼跳過去、怎麼跳回來。下面是 `thumbd` 裡一個簡化的縮放計算。`noinline` 只是要求編譯器不要把 `scale` 直接展開進呼叫端，否則我們就看不到呼叫了。

```c
__attribute__((noinline))
long scale(long x, long factor) {
    return x * factor + 1;
}

long resize_width(long w) {
    long r = scale(w, 3);
    return r + 2;
}
```

用 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - call.c` 產生的組合語言（刪去 directive）：

```asm
scale:
	imulq	%rsi, %rdi
	leaq	1(%rdi), %rax
	retq
resize_width:
	pushq	%rax
	movl	$3, %esi
	callq	scale
	addq	$2, %rax
	popq	%rcx
	retq
```

`callq` 與 `retq` 就是 `call` 與 `ret`，clang 習慣加上 `q` 後綴。兩條指令的語意是：

- **`call 目標`**：把「下一條指令的位址」push 到 stack，然後跳到目標。被 push 的這個位址就是 **return address**（返回位址）。
- **`ret`**：從 stack pop 出一個位址，跳過去。

就這麼簡單。「回家的路」不是記在什麼特殊的硬體裡，而是普普通通地存在 stack 上。這也是第 11 章談 stack buffer overflow 時最在意的一點：如果越界寫入改掉了 stack 上的 return address，`ret` 不會檢查，照樣跳到那個錯誤的位址。

用 `objdump -d` 看目的檔，`scale` 在 offset `0x0`，`resize_width` 在 `0x10`，其中 `callq` 在 `0x16`、下一條 `addq` 在 `0x1b`。為了手算，假設連結後整段程式被放在 `0x401000`，且進入 `resize_width` 時 `%rsp = 0x7fffffffe438`（這兩個起點是假設的，相對關係才是重點）。逐條追蹤：

| 步驟 | 執行的指令 | 執行後 `%rip` | 執行後 `%rsp` | stack 上發生什麼 |
|---|---|---|---|---|
| 0 | （剛進入 `resize_width`） | `0x401010` | `0x7fffffffe438` | `[e438]` 是呼叫 `resize_width` 的人留下的 return address |
| 1 | `pushq %rax` | `0x401011` | `0x7fffffffe430` | 寫入 8 bytes（內容不重要，見下文） |
| 2 | `movl $3, %esi` | `0x401016` | `0x7fffffffe430` | 第二個參數 = 3；第一個參數 `w` 本來就在 `%rdi` |
| 3 | `callq scale` | `0x401000` | `0x7fffffffe428` | `[e428] = 0x40101b`，也就是 `addq` 的位址 |
| 4 | `imulq %rsi, %rdi` | `0x401004` | `0x7fffffffe428` | 無 |
| 5 | `leaq 1(%rdi), %rax` | `0x401008` | `0x7fffffffe428` | 無；回傳值放進 `%rax` |
| 6 | `retq` | `0x40101b` | `0x7fffffffe430` | 讀出 `[e428]` 當作新的 `%rip` |
| 7 | `addq $2, %rax` | `0x40101f` | `0x7fffffffe430` | 無 |
| 8 | `popq %rcx` | `0x401020` | `0x7fffffffe438` | 丟掉步驟 1 寫入的 8 bytes |
| 9 | `retq` | 呼叫者的位址 | `0x7fffffffe440` | 回到 `resize_width` 的呼叫者 |

把步驟 3 的 stack 畫出來：

```text
 高位址
 ┌────────────────────────────┐ 0x7fffffffe440
 │ （呼叫 resize_width 的人   │
 │   的 frame）               │
 ├────────────────────────────┤ 0x7fffffffe438
 │ return address：回到呼叫者 │ ← resize_width 進入時的 %rsp
 ├────────────────────────────┤ 0x7fffffffe430
 │ pushq %rax 寫入的 8 bytes  │ ← call 之前的 %rsp（16 的倍數）
 ├────────────────────────────┤ 0x7fffffffe428
 │ return address：0x40101b   │ ← 進入 scale 時的 %rsp
 └────────────────────────────┘
 低位址
```

從圖上可以看到兩個重點。第一，`scale` 一進來，`(%rsp)` 指的就是它的 return address；`scale` 沒有動 `%rsp`，所以 `retq` 直接拿到正確的位址。第二，`resize_width` 開頭那個奇怪的 `pushq %rax` 並不是要保存 `%rax`（`%rax` 裡根本沒有有用的值，結尾也是 pop 到 `%rcx` 丟掉）。它只是一個「把 `%rsp` 減 8」的便宜寫法，目的是讓 `call` 之前的 `%rsp` 是 16 的倍數。為什麼一定要 16 的倍數，9.5 節會解釋。

> [!warning] 常見誤解
> 「return address 指向 `call` 這條指令。」不對，它指向 `call` 的**下一條**指令。所以 debugger 在 stack trace 裡顯示的「呼叫位置」，其實是 return address 再往回推一點；有時 gdb 會因此把行號標在呼叫的下一行。

## 9.4 參數與回傳值：System V AMD64 calling convention

`scale` 怎麼知道第一個參數在 `%rdi`、第二個在 `%rsi`？因為呼叫者和被呼叫者都遵守同一份約定，叫 **calling convention**（呼叫慣例）。它是 **ABI**（application binary interface，應用程式二進位介面）的一部分。ABI 規定的是「編譯好的機器碼之間怎麼合作」：參數放哪、回傳值放哪、哪些暫存器可以亂用、struct 怎麼排、stack 怎麼對齊。只要遵守同一份 ABI，用 gcc 編的 library 就能被 clang 編的程式呼叫，Rust、Go 透過 FFI 呼叫 C 函式也靠它。

Linux、macOS、BSD 在 x86-64 上使用 **System V AMD64 ABI**。它的參數規則如下：

| 用途 | 暫存器（依序） | 例子 |
|---|---|---|
| 第 1–6 個整數或指標參數 | `%rdi`、`%rsi`、`%rdx`、`%rcx`、`%r8`、`%r9` | `memcpy(dst, src, n)`：`dst` 在 `%rdi`、`src` 在 `%rsi`、`n` 在 `%rdx` |
| 第 1–8 個浮點參數 | `%xmm0`–`%xmm7` | `pow(x, y)`：`x` 在 `%xmm0`、`y` 在 `%xmm1` |
| 整數回傳值 | `%rax`（128-bit 時再加 `%rdx`） | `strlen` 的結果在 `%rax` |
| 浮點回傳值 | `%xmm0` | `sqrt` 的結果在 `%xmm0` |
| 超過暫存器數量的參數 | stack，從第 7 個開始，依序放在 return address 上方 | 見下面的 `mix8` |

整數與浮點參數是分開計數的：`f(long a, double b, long c)` 中，`a` 在 `%rdi`、`b` 在 `%xmm0`、`c` 在 `%rsi`。參數比 64 bits 窄時，使用子暫存器：`int` 參數放在 `%edi`、`char` 放在 `%dil`（第 7 章）。被呼叫者不能假設高位元是乾淨的，所以常會看到 `movslq %edi, %rax` 這種先做 sign extension 的指令。

### 超過六個參數時

```c
__attribute__((noinline))
long mix8(long a, long b, long c, long d,
          long e, long f, long g, long h) {
    return a + b + c + d + e + f + g * h;
}

long call_mix8(void) {
    return mix8(1, 2, 3, 4, 5, 6, 7, 8);
}
```

`clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - args.c`：

```asm
mix8:
	movq	16(%rsp), %rax
	addq	%rdi, %rsi
	addq	%rdx, %rcx
	addq	%rsi, %rcx
	addq	%r8, %rcx
	addq	%r9, %rcx
	imulq	8(%rsp), %rax
	addq	%rcx, %rax
	retq
call_mix8:
	pushq	%rax
	movl	$1, %edi
	movl	$2, %esi
	movl	$3, %edx
	movl	$4, %ecx
	movl	$5, %r8d
	movl	$6, %r9d
	pushq	$8
	pushq	$7
	callq	mix8
	addq	$16, %rsp
	popq	%rcx
	retq
```

前六個參數直接 `movl` 進暫存器（寫 32-bit 暫存器會把高 32 位元清零，所以 `movl $1, %edi` 等於把 `%rdi` 設為 1，而且指令比較短）。第 7、8 個參數用 `push` 放上 stack，**先 push 第 8 個、再 push 第 7 個**，讓編號小的參數在低位址。進入 `mix8` 那一刻的 stack：

```text
 高位址
 ┌──────────────────────────┐
 │ call_mix8 的 return addr │
 ├──────────────────────────┤
 │ pushq %rax（對齊用）     │
 ├──────────────────────────┤ ← 16(%rsp)
 │ h = 8（第 8 個參數）     │
 ├──────────────────────────┤ ← 8(%rsp)
 │ g = 7（第 7 個參數）     │
 ├──────────────────────────┤ ← (%rsp)
 │ return addr（回 call_mix8│
 │ 的 addq）                │
 └──────────────────────────┘
 低位址
```

所以 `mix8` 用 `8(%rsp)` 讀 `g`、`16(%rsp)` 讀 `h`：`0(%rsp)` 永遠是 return address，第 7 個參數緊接在它上面。呼叫結束後，**由呼叫者**用 `addq $16, %rsp` 把這兩個參數清掉，因為只有呼叫者知道自己放了幾個。

對齊也可以手算：進入 `call_mix8` 時 `%rsp` 除以 16 餘 8（剛被 push 了 return address）；`pushq %rax` 後餘 0；再 push 兩次共 16 bytes，仍然餘 0。所以 `callq mix8` 執行前 `%rsp` 是 16 的倍數，符合 ABI。

### 其他值得知道的規則

- **小 struct 可以用暫存器傳**：不超過 16 bytes、只含整數的 struct，會被拆成一或兩個 8-byte 塊，分別放進參數暫存器；回傳時放在 `%rax` 與 `%rdx`。
- **大 struct 走記憶體**：超過 16 bytes 的 struct 參數會整個複製到 stack 上。回傳大 struct 時，呼叫者先準備一塊空間，把它的位址當作隱藏的第一個參數放在 `%rdi`，被呼叫者把結果寫進去，並在 `%rax` 回傳這個位址。所以「回傳一個大 struct」其實是一次記憶體複製，熱點路徑上要留意。
- **可變參數函式**（variadic，例如 `printf`）：呼叫者要在 `%al` 放「用了幾個向量暫存器」的上限，讓被呼叫者知道要不要把 `%xmm` 暫存器存起來。下面是 `log_msg("ratio=%f", ratio)` 編譯後的片段，`movb $1, %al` 就是在說「有一個浮點參數在 `%xmm0`」：

```c
void log_msg(const char *fmt, ...);

void report(double ratio) {
    log_msg("ratio=%f", ratio);
}
```

`clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - var.c`：

```asm
report:
	leaq	.L.str(%rip), %rdi
	movb	$1, %al
	jmp	log_msg@PLT
```

這個片段還藏了一個最佳化：最後不是 `call` 而是 `jmp`。因為 `report` 呼叫完 `log_msg` 之後什麼都不做，編譯器直接「跳」過去，讓 `log_msg` 的 `ret` 一次回到 `report` 的呼叫者。這叫 **tail call**（尾呼叫）最佳化：省下一個 frame，但 stack trace 裡也就看不到 `report` 這一層了。

不同平台的 ABI 不一樣，寫 FFI、讀別的平台的反組譯時要先確認：

| ABI | 整數參數暫存器 | 回傳 | 返回位址放哪 | 特別之處 |
|---|---|---|---|---|
| System V AMD64（Linux、macOS x86-64） | `%rdi`、`%rsi`、`%rdx`、`%rcx`、`%r8`、`%r9` | `%rax` | stack（`call` push） | 128-byte red zone（9.9 節） |
| Microsoft x64（Windows） | `%rcx`、`%rdx`、`%r8`、`%r9` | `%rax` | stack | 呼叫者要預留 32 bytes 的 shadow space；沒有 red zone |
| AArch64 AAPCS64（Linux、macOS ARM） | `x0`–`x7` | `x0` | link register `x30`（`bl` 指令寫入） | leaf function 可以完全不碰 stack |

ARM64 的差別值得多說一句：`bl`（branch with link）不寫 stack，而是把 return address 放在暫存器 `x30`。如果被呼叫者還要再呼叫別人，才需要自己把 `x30` 存到 stack。概念和 x86-64 一樣，只是「什麼時候存到記憶體」換了人負責。

## 9.5 Stack frame：local 變數、對齊與 frame 的完整樣貌

前面的 `scale` 和 `mix8` 連 `%rsp` 都沒怎麼動，因為它們的資料全部放得進暫存器。那什麼時候 local 變數一定要放在 stack 上？主要有三種情況：

1. **暫存器不夠用**：同時活著的值太多。
2. **要取位址**：C 的 `&x` 需要一個記憶體位址，暫存器沒有位址。
3. **陣列與 struct**：一整塊連續資料，不可能塞進暫存器。

`thumbd` 讀檔頭時就是第 2、3 種的例子：

```c
void read_header(char *buf, long n);
long parse_len(const char *buf);

long load(void) {
    char buf[32];
    read_header(buf, sizeof buf);
    return parse_len(buf);
}
```

`clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - local.c`：

```asm
load:
	pushq	%rbx
	subq	$32, %rsp
	movq	%rsp, %rbx
	movl	$32, %esi
	movq	%rbx, %rdi
	callq	read_header@PLT
	movq	%rbx, %rdi
	callq	parse_len@PLT
	addq	$32, %rsp
	popq	%rbx
	retq
```

`subq $32, %rsp` 在 stack 上挖出 32 bytes 給 `buf`，之後 `%rsp` 就是 `buf` 的起點，所以 `movq %rsp, %rbx` 等於 `%rbx = buf`。`@PLT` 表示透過動態連結的跳板呼叫外部函式，第 19 章會解釋。結尾 `addq $32, %rsp` 把空間還回去，這就是「local 變數在函式結束時消失」在機器層級的真面目：**沒有任何清除動作，只是 `%rsp` 往回移，那塊記憶體下一次呼叫就會被別人蓋掉。**

```text
 load 執行到 callq read_header 之前
 高位址
 ┌──────────────────────────┐
 │ return address（回呼叫者）│ ← 進入 load 時的 %rsp（餘 8）
 ├──────────────────────────┤
 │ saved %rbx               │ ← pushq %rbx 之後（餘 0）
 ├──────────────────────────┤
 │ buf[24..31]              │
 │ buf[16..23]              │
 │ buf[8..15]               │
 │ buf[0..7]                │ ← %rsp = %rbx = buf（餘 0）
 └──────────────────────────┘
 低位址
```

這張圖一併回答了「為什麼不能回傳 local 陣列的位址」：

```c
// not-runnable
char *make_key(int w) {
    char key[16];
    key[0] = (char)w;
    return key;    /* clang：address of stack memory associated with local variable 'key' returned */
}
```

`make_key` 回傳之後，`key` 所在的那塊 stack 已經不屬於任何人；呼叫者下一次呼叫任何函式，那個函式的 frame 就會覆蓋它。編譯器會發出 `-Wreturn-stack-address` 警告，請把它當作錯誤。

### 16-byte 對齊

System V ABI 規定：**執行 `call` 之前，`%rsp` 必須是 16 的倍數**。因為 `call` 會再 push 8 bytes，所以每個函式剛進來時，`%rsp` 除以 16 一定餘 8。函式如果還要呼叫別人，就得自己把 `%rsp` 調回 16 的倍數。

為什麼要這麼麻煩？因為 SSE 的某些指令（例如 `movaps`）要求記憶體運算元 16-byte 對齊，否則直接觸發 fault。編譯器在 stack 上放 `double` 陣列、或 library 在函式開頭用 `movaps` 保存 `%xmm` 暫存器時，都依賴「`%rsp` 對齊」這個約定。只要有一個函式（通常是手寫組合語言或 JIT 產生的碼）沒遵守，當機的地方會出現在下游某個完全無辜的函式裡，例如 `printf` 內部的一條 `movaps`。

判斷方法很機械，每個函式都能手算：

| 函式 | 進入時 | 調整 | 調整總量 | `call` 前 `%rsp` mod 16 |
|---|---|---|---|---|
| `resize_width` | 餘 8 | `pushq %rax` | 8 | 0，合法 |
| `call_mix8` | 餘 8 | `pushq %rax`、`pushq $8`、`pushq $7` | 24 | 0，合法 |
| `load` | 餘 8 | `pushq %rbx`、`subq $32` | 40 | 0，合法 |
| 規則 | 餘 8 | 所有 push 與 `sub` 的總和 | 必須是 8 + 16k | 0 |

### 一般化的 stack frame

把前面看到的元素合起來，一個函式在執行中的 frame 最多可以有這些部分：

```text
 高位址
 ┌──────────────────────────────┐
 │ 呼叫者的 frame               │
 │   ...                        │
 │   第 8 個參數                │
 │   第 7 個參數                │ ← 呼叫者 call 之前的 %rsp（16 的倍數）
 ├──────────────────────────────┤
 │ return address               │ ← 進入本函式時的 %rsp
 ├──────────────────────────────┤ ─┐
 │ saved %rbp（若使用 frame     │  │
 │   pointer，9.7 節）          │  │
 │ saved callee-saved 暫存器    │  │ 本函式的
 │   （%rbx、%r12–%r15）        │  │ stack frame
 │ local 變數、陣列、struct     │  │
 │ 對齊用的空隙                 │  │
 │ 要傳給下一個函式的第 7+ 參數 │  │
 └──────────────────────────────┘ ─┘ ← 目前的 %rsp
 低位址
```

讀這張圖要注意：**每一部分都是「需要才有」**。`scale` 的 frame 只有 return address；`load` 有 saved `%rbx` 與 local 陣列；只有參數超過六個時才有「傳給下一個函式的參數」區。CS:APP 用的也是這個模型，但最佳化後的真實程式通常比教科書的模板精簡得多，不要期待每個函式都長得一樣。

## 9.6 暫存器的分工：caller-saved 與 callee-saved

x86-64 只有 16 個通用暫存器，呼叫者與被呼叫者共用同一組。問題來了：`handle_request` 把連線編號放在 `%rbx`，呼叫 `decode_jpeg` 之後還要用；`decode_jpeg` 自己也想用 `%rbx`。誰負責保存？

ABI 的解法是把暫存器分成兩群，各自指定一個負責人：

| 類別 | 暫存器 | 規則 | 誰付出代價 |
|---|---|---|---|
| **callee-saved**（被呼叫者保存） | `%rbx`、`%rbp`、`%r12`、`%r13`、`%r14`、`%r15`（以及 `%rsp` 本身） | 被呼叫者可以用，但回傳前必須恢復原值 | 被呼叫者：用之前 push、回傳前 pop |
| **caller-saved**（呼叫者保存） | `%rax`、`%rcx`、`%rdx`、`%rsi`、`%rdi`、`%r8`–`%r11`，以及所有 `%xmm` | 被呼叫者可以隨意改寫 | 呼叫者：呼叫後還要用的值，自己想辦法保存 |

callee-saved 暫存器也叫 non-volatile，caller-saved 也叫 volatile 或 scratch。名稱很多，記住一句話就好：**跨過一次 `call` 還要活著的值，要嘛放在 callee-saved 暫存器，要嘛放在 stack。**

看一個實際例子：

```c
long checksum(long x);

long sum_two(long a, long b) {
    long ca = checksum(a);
    long cb = checksum(b);
    return ca + cb + a;
}
```

`clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - saved.c`：

```asm
sum_two:
	pushq	%r15
	pushq	%r14
	pushq	%rbx
	movq	%rsi, %rbx
	movq	%rdi, %r14
	callq	checksum@PLT
	movq	%rax, %r15
	movq	%rbx, %rdi
	callq	checksum@PLT
	addq	%r14, %r15
	addq	%r15, %rax
	popq	%rbx
	popq	%r14
	popq	%r15
	retq
```

逐步看編譯器的盤算：

1. `a` 在呼叫 `checksum` 之後還要用（最後要加），`b` 要留到第二次呼叫。但 `%rdi`、`%rsi` 是 caller-saved，`checksum` 可能改掉它們。所以編譯器把 `b` 搬到 `%rbx`、`a` 搬到 `%r14`。
2. 第一次呼叫的結果 `ca` 在 `%rax`，第二次呼叫會覆蓋 `%rax`，所以先搬到 `%r15`。
3. `%rbx`、`%r14`、`%r15` 是 callee-saved，`sum_two` 自己也有義務還給它的呼叫者原值。所以開頭先 push 三個、結尾以相反順序 pop。
4. 對齊檢查：進入時餘 8，三次 push 共 24 bytes，8 + 24 = 32，餘 0。剛好不用另外調整。

這裡可以看出兩類暫存器的取捨：caller-saved 適合「呼叫前就用完」的暫時值，完全不用保存；callee-saved 適合「要跨越呼叫」的值，只在函式開頭與結尾各付一次 push／pop，中間不管呼叫多少次都不用再存。

> [!warning] 常見誤解
> 「callee-saved 的意思是被呼叫者不能用這些暫存器。」不是，被呼叫者可以用，只要回傳前恢復原值。`sum_two` 自己就用了 `%rbx`、`%r14`、`%r15`，這也是為什麼它開頭要 push。另一個誤解是「caller-saved 暫存器在呼叫後一定會被改掉」：不一定會改，但呼叫者**不能假設**沒被改。

## 9.7 Frame pointer：%rbp 與 -fomit-frame-pointer

前面所有的函式都用 `%rsp` 加上固定位移來找東西，例如 `8(%rsp)`。這在函式內 `%rsp` 不變時沒問題，但 `%rsp` 每次 push 都會變，位移也跟著變，人與工具都很難追。傳統的解法是用另一個暫存器 `%rbp` 當 **frame pointer**（框指標）：在函式一開頭把它固定指向 frame 的基準點，之後整個函式都用 `-8(%rbp)` 這種固定位移存取。

用 `-O0` 編譯 `scale`（`clang -target x86_64-linux-gnu -O0 -S -fno-asynchronous-unwind-tables -o - call.c`），就能看到這個經典模板：

```asm
scale:
	pushq	%rbp
	movq	%rsp, %rbp
	movq	%rdi, -8(%rbp)
	movq	%rsi, -16(%rbp)
	movq	-8(%rbp), %rax
	imulq	-16(%rbp), %rax
	addq	$1, %rax
	popq	%rbp
	retq
```

`pushq %rbp; movq %rsp, %rbp` 這兩行叫 **prologue**（序言），`popq %rbp; retq` 叫 **epilogue**（結語）。prologue 做了一件很巧妙的事：它把「呼叫者的 `%rbp`」存在「自己的 `%rbp` 指向的位置」。於是所有 frame 串成一條鏈結串列：

```text
 高位址
 ┌──────────────────────┐
 │ return addr → main   │
 │ saved %rbp = 0       │ ← worker_loop 的 %rbp ───────┐
 ├──────────────────────┤                              │
 │ ...                  │                              │
 │ return addr → worker │                              │
 │ saved %rbp ──────────┼──────────────────────────────┘
 │                      │ ← handle_request 的 %rbp ────┐
 ├──────────────────────┤                              │
 │ ...                  │                              │
 │ return addr → handle │                              │
 │ saved %rbp ──────────┼──────────────────────────────┘
 │                      │ ← decode_jpeg 的 %rbp（目前的 %rbp）
 │ local 變數           │
 └──────────────────────┘ ← %rsp
 低位址
 規則：8(%rbp) 是 return address，0(%rbp) 是上一層的 %rbp
```

只要知道目前的 `%rbp`，就能讀出 `8(%rbp)`（這一層要回去的位址，也就知道呼叫者是誰），再讀 `0(%rbp)` 跳到上一層，一路走到底。這就是最便宜的 **stack walking**（走訪呼叫鏈）：每層兩次記憶體讀取，不需要任何額外資訊。

但 `-O1` 以上，x86-64 的 gcc 與 clang 預設**不用** frame pointer（`-fomit-frame-pointer`），把 `%rbp` 當成一般的 callee-saved 暫存器，拿來放變數。比較同一個函式加不加 `-fno-omit-frame-pointer`：

```c
long checksum(long x);

long twice(long a) {
    return checksum(a) + checksum(a + 1);
}
```

預設（`clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - fp.c`），省略 frame pointer：

```asm
twice:
	pushq	%r14
	pushq	%rbx
	pushq	%rax
	movq	%rdi, %rbx
	callq	checksum@PLT
	movq	%rax, %r14
	incq	%rbx
	movq	%rbx, %rdi
	callq	checksum@PLT
	addq	%r14, %rax
	addq	$8, %rsp
	popq	%rbx
	popq	%r14
	retq
```

加上 `-fno-omit-frame-pointer`（其餘選項相同）：

```asm
twice:
	pushq	%rbp
	movq	%rsp, %rbp
	pushq	%r14
	pushq	%rbx
	movq	%rdi, %rbx
	callq	checksum@PLT
	movq	%rax, %r14
	incq	%rbx
	movq	%rbx, %rdi
	callq	checksum@PLT
	addq	%r14, %rax
	popq	%rbx
	popq	%r14
	popq	%rbp
	retq
```

兩個版本的差別很小：第二個版本多了 `movq %rsp, %rbp` 一條指令，而且 `%rbp` 不能再拿來放變數。有趣的是，第一個版本為了對齊還得多一個 `pushq %rax`／`addq $8, %rsp`，第二個版本的 `pushq %rbp` 剛好順便完成了對齊。

| 選項 | 好處 | 代價 | 誰在用 |
|---|---|---|---|
| 省略 frame pointer（x86-64 `-O1` 以上的預設） | 多一個可用暫存器、少一兩條指令 | 走訪 stack 必須依賴 unwind 資訊，profiler 取 call stack 變貴或不準 | 多數 x86-64 編譯預設 |
| 保留 frame pointer（`-fno-omit-frame-pointer`） | profiler 與 crash handler 能便宜又可靠地走訪呼叫鏈 | 少一個暫存器；公開量測多在 1–2% 以內，少數程式（例如 CPython 直譯器）可能更明顯，依程式而定 | macOS ARM64 一律保留；部分 Linux 發行版已改為保留：Fedora 38 起套件建置旗標預設加上 `-fno-omit-frame-pointer`，Ubuntu 24.04 起多數 64-bit 平台的套件建置旗標也預設保留（改的是發行版的建置旗標，不是 gcc 本身的預設值） |

既然省略了 frame pointer，gdb 為什麼還是能印出完整的 stack trace？因為編譯器另外產生了 **unwind 資訊**：ELF 的 `.eh_frame` section 裡存著 DWARF 格式的 CFI（call frame information），描述「在這個函式的每一個位置，return address 在 `%rsp` 上方多遠、哪些暫存器被存在哪裡」。我們產生組合語言時加的 `-fno-asynchronous-unwind-tables`，就是為了把這些 `.cfi_*` directive 隱藏起來，方便閱讀。C++ 的 exception 也是靠這份資訊一層層退回 frame。

這也解開了故事中 flame graph 的謎：`perf record -g` 預設用 frame pointer 走訪，遇到省略 frame pointer 的函式，鏈就斷了，只能標成 `[unknown]`。9.12 節會給出對策。

## 9.8 遞迴：每一次呼叫都有自己的 frame

有了 frame 的概念，遞迴就不再神祕：**遞迴函式的每一次呼叫，都是一次普通的呼叫，有自己的 return address、自己的 saved 暫存器、自己的 local 變數。** 所謂「遞迴的每一層有自己的變數」，就是因為每一層的 frame 在 stack 上不同的位置。

先看一個會讓初學者意外的例子：

```c
long fact(long n) {
    if (n <= 1)
        return 1;
    return n * fact(n - 1);
}
```

`clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - fact.c`：

```asm
fact:
	movl	$1, %eax
	cmpq	$2, %rdi
	jl	.LBB0_3
.LBB0_2:
	imulq	%rdi, %rax
	decq	%rdi
	cmpq	$2, %rdi
	jge	.LBB0_2
.LBB0_3:
	retq
```

完全沒有 `call`！編譯器看出乘法可以交換順序，把遞迴改寫成一個累乘的迴圈（第 8 章的迴圈翻譯）。所以「C 程式寫遞迴」不保證「機器碼有遞迴」；反過來，你也不能依賴編譯器一定會做這種轉換，`-O0` 或稍微複雜一點的遞迴就不會。

再看一個無法完全攤平的例子，也比較像 `thumbd` 解析巢狀 metadata 的形狀：

```c
struct box {
    long size;
    struct box *first_child;
    struct box *next;
};

long total_size(const struct box *b) {
    if (b == 0)
        return 0;
    return b->size + total_size(b->first_child) + total_size(b->next);
}
```

`clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - rec.c`：

```asm
total_size:
	pushq	%r15
	pushq	%r14
	pushq	%rbx
	movq	%rdi, %rbx
	xorl	%r14d, %r14d
	testq	%rbx, %rbx
	je	.LBB0_3
.LBB0_2:
	movq	(%rbx), %r15
	movq	8(%rbx), %rdi
	callq	total_size
	movq	16(%rbx), %rbx
	addq	%r14, %r15
	addq	%rax, %r15
	movq	%r15, %r14
	testq	%rbx, %rbx
	jne	.LBB0_2
.LBB0_3:
	movq	%r14, %rax
	popq	%rbx
	popq	%r14
	popq	%r15
	retq
```

編譯器把「往 `next` 走」改成了迴圈（`.LBB0_2` 的回跳），但「往 `first_child` 走」仍然是真正的 `callq total_size`。`(%rbx)`、`8(%rbx)`、`16(%rbx)` 分別是 `size`、`first_child`、`next` 三個欄位，第 10 章會講 struct 欄位位移怎麼算。

每一層真正遞迴的 frame 有多大？數一下：return address 8 bytes，加上三次 push 24 bytes，共 **32 bytes**。如果有人上傳一個 `first_child` 一層包一層、深達 100,000 層的檔案：

```text
100,000 層 × 32 bytes = 3,200,000 bytes ≈ 3.05 MiB
```

在 8 MiB 的 main thread stack 上不會出事；放到 256 KiB 的 worker thread 上，大約 256 × 1024 ÷ 32 = 8,192 層就用完了。真實的 `parse_ifd` frame 更大（它有 48 bytes 的暫存區與更多 saved 暫存器），所以兩千多層就爆了，這就是故事裡 stack trace 的長度。

畫出三層遞迴時的 stack：

```text
 高位址
 ┌─────────────────────────────┐
 │ handle_request 的 frame     │
 ├─────────────────────────────┤
 │ ret → handle_request        │ total_size(root)
 │ saved %r15 %r14 %rbx        │   %rbx = root
 ├─────────────────────────────┤
 │ ret → total_size 的 addq    │ total_size(root->first_child)
 │ saved %r15 %r14 %rbx        │   這裡存的 %rbx 是上一層的 root
 ├─────────────────────────────┤
 │ ret → total_size 的 addq    │ total_size(更深的 child)
 │ saved %r15 %r14 %rbx        │
 └─────────────────────────────┘ ← %rsp
 ▼ 再往下是 guard page：碰到就 SIGSEGV
 低位址
```

stack 用完時會發生什麼？作業系統在每個 thread stack 的底端放了一個沒有讀寫權限的 **guard page**（保護頁）；main thread 的 stack 會自動往下長，但 kernel 同樣在它與下方的 mapping 之間保留一段不能用的間隔，效果相同。再多一層 frame，push 就會寫進 guard page，觸發 page fault；kernel 判斷這不是合法存取，送出 `SIGSEGV`（第 23 章會看到，權限不符的存取由 MMU 觸發 fault、再由 kernel 判定為非法）。這就是 **stack overflow**：不是什麼特別的錯誤，只是一次普通的 segfault，所以 log 裡只會看到 `Segmentation fault`，要看 stack trace 的深度才分辨得出來。

> [!warning] 常見誤解
> 「遞迴深度太深會拋出例外。」在 Java、Python 裡是（`StackOverflowError`、`RecursionError`），因為 runtime 自己數深度。C 沒有任何檢查，碰到 guard page 才由硬體與 kernel 發現；如果某一層 frame 本身大於 guard page（例如 local 陣列有 1 MiB），甚至可能直接跳過 guard page 寫到別的記憶體。gcc 與 clang 的 `-fstack-clash-protection` 就是為了防止這種跳過。

## 9.9 Red zone：leaf function 的免費空間

回頭看 9.7 節 `-O0` 的 `scale`：它把參數存到 `-8(%rbp)`、`-16(%rbp)`，可是從頭到尾沒有 `subq ..., %rsp`。因為 `movq %rsp, %rbp` 之後 `%rbp` 等於 `%rsp`，所以這兩個位置其實**在 `%rsp` 之下**，也就是 stack 頂端「外面」。這樣不會被覆蓋嗎？

System V AMD64 ABI 保證：**`%rsp` 之下的 128 bytes 是 red zone**（紅區），signal handler 與中斷處理都不會碰它。Linux kernel 在把 signal handler 的 frame 放到 user stack 上時（signal 遞送的流程見第 22 章），會刻意先跳過這 128 bytes。所以一個 **leaf function**（不再呼叫其他函式的函式）可以直接用這塊空間放 local 變數，省掉調整 `%rsp` 的兩條指令。

```text
 高位址
 ┌──────────────────────────┐
 │ return address           │
 │ saved %rbp               │ ← %rsp = %rbp
 ├──────────────────────────┤
 │ x（-8(%rbp)）            │ ┐
 │ factor（-16(%rbp)）      │ │ red zone：128 bytes
 │ （其餘未使用）           │ │ leaf function 可直接使用
 │                          │ ┘
 ├──────────────────────────┤ ← %rsp − 128
 │ 不保證安全               │
 └──────────────────────────┘
 低位址
```

為什麼只限 leaf function？因為一旦呼叫別人，`call` 本身就會 push return address 到 `%rsp − 8`，正好蓋掉 red zone。所以非 leaf 函式還是得老實地 `sub %rsp`。

Red zone 有兩個重要的例外。第一，Linux kernel 自己是用 `-mno-red-zone` 編譯的，因為 kernel 中的中斷會直接使用同一個 stack，沒有人幫它跳過 128 bytes。第二，Windows x64 與 AArch64 Linux 的 ABI 沒有 red zone。寫 kernel module、bootloader、或在中斷處理中執行的程式時，一定要確認這一點。

## 9.10 Stack trace 是怎麼來的

現在可以完整回答故事中的問題：「當機後，gdb 怎麼知道這兩千多層是誰呼叫誰？」

當程式收到 `SIGSEGV` 而產生 core dump 時，kernel 把 process 的記憶體與每個 thread 的暫存器（包括 `%rip`、`%rsp`、`%rbp`）寫進 core 檔。gdb 讀 core 檔後做 **unwinding**（展開堆疊）：

```text
 從 core dump 開始
       │
       ▼
 第 0 層：%rip 在哪個函式？（用符號表 .symtab 查）
       │
       ▼
 這個函式的 return address 在哪？
       ├─ 有 .eh_frame／.debug_frame 的 CFI → 照規則從 %rsp 推算（最可靠）
       ├─ 有 frame pointer → 讀 8(%rbp)，上一層 %rbp = 0(%rbp)
       └─ 都沒有 → 只能猜（掃描 stack 上像程式位址的值），結果可能錯亂
       │
       ▼
 得到上一層的 %rip、%rsp（以及恢復的 callee-saved 暫存器）
       │
       ▼
 重複，直到 return address 為 0 或走出 stack 範圍
```

每一層要做兩件事：從位址查出函式名稱（需要符號表），以及找到這一層的 return address（需要 CFI 或 frame pointer）。哪一步缺資料，stack trace 就壞在那裡：

| 你在 stack trace 看到 | 原因 | 怎麼改善 |
|---|---|---|
| `?? ()` | 位址查不到符號：binary 被 strip，或跳到非法位址 | 保留 debug symbol（另存 `.debug` 檔）；用 `addr2line` 對照沒 strip 的 binary |
| 只剩一兩層就斷了 | stack 本身被寫壞（例如 buffer overflow 蓋掉 return address） | 用 ASan 重現（第 26 章）；看 `x/32gx $rsp` 的原始內容 |
| 少了某一層函式 | inline 或 tail call：那一層根本沒有自己的 frame | gdb 會把 inline 的函式標出來；需要時用 `-fno-inline`、`-fno-optimize-sibling-calls` 重現 |
| 同一函式重複幾千層 | 無限或過深的遞迴，stack overflow | 看最深與最淺幾層的參數，找出遞迴的條件 |
| 變數顯示 `<optimized out>` | 值只活在暫存器裡，而且已被覆蓋 | 往上一層看參數來源；用 `-Og` 重現 |

## 9.11 動手做：觀察 frame、走一遍 frame pointer 鏈

這一節的程式都在本機（macOS arm64，Apple clang 21）實際執行。ARM64 的 frame pointer 暫存器是 `x29`、return address 暫存器是 `x30`，但 frame 的組織方式和 x86-64 保留 frame pointer 時一樣：frame pointer 指向「上一層的 frame pointer」，緊接著是 return address。

### 程式一：遞迴的每一層在 stack 上的哪裡

```c
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/resource.h>

/* 每一層遞迴印出：local 變數的位址、這一層 frame 的位址、return address。
 * noinline 讓編譯器不要把遞迴攤平成迴圈，才看得到一層一層的 frame。 */
static uintptr_t prev;

__attribute__((noinline))
static long walk_ifd(int depth, int max_depth) {
    volatile char tag_buf[48];             /* 模擬解析 IFD 時用的暫存區 */
    tag_buf[0] = (char)depth;
    uintptr_t here = (uintptr_t)tag_buf;
    printf("depth %d  local=%#lx  frame=%p  ret=%p  與上一層相差 %ld bytes\n",
           depth, (unsigned long)here, __builtin_frame_address(0),
           __builtin_return_address(0), prev ? (long)(prev - here) : 0L);
    prev = here;
    long sub = depth < max_depth ? walk_ifd(depth + 1, max_depth) : 0;
    return sub + tag_buf[0];
}

int main(void) {
    walk_ifd(0, 3);

    struct rlimit rl;
    getrlimit(RLIMIT_STACK, &rl);
    pthread_attr_t attr;
    size_t thread_stack;
    pthread_attr_init(&attr);
    pthread_attr_getstacksize(&attr, &thread_stack);
    printf("main thread stack 上限（RLIMIT_STACK）：%lu KiB\n", (unsigned long)rl.rlim_cur / 1024);
    printf("新 thread 的預設 stack：%lu KiB\n", (unsigned long)thread_stack / 1024);
    pthread_attr_destroy(&attr);
    return 0;
}
```

在 macOS arm64 上執行（位址每次執行都不同，因為有 ASLR，第 11 章）：

```text
depth 0  local=0x16f4d4fb8  frame=0x16f4d5010  ret=0x10092851c  與上一層相差 0 bytes
depth 1  local=0x16f4d4f28  frame=0x16f4d4f80  ret=0x100928614  與上一層相差 144 bytes
depth 2  local=0x16f4d4e98  frame=0x16f4d4ef0  ret=0x100928614  與上一層相差 144 bytes
depth 3  local=0x16f4d4e08  frame=0x16f4d4e60  ret=0x100928614  與上一層相差 144 bytes
main thread stack 上限（RLIMIT_STACK）：8176 KiB
新 thread 的預設 stack：512 KiB
```

逐行解讀：

1. **位址一層比一層小**：`local` 從 `...4fb8` 降到 `...4e08`，證實 stack 往低位址成長，越深的呼叫越靠近低位址。
2. **每層固定 144 bytes**：48 bytes 的 `tag_buf`，加上 saved frame pointer 與 return address（各 8 bytes）、為了跨呼叫保存值而用的 callee-saved 暫存器、`printf` 呼叫需要的空間，再對齊到 16 的倍數。這個數字依平台與編譯器而定，但「每層固定」這件事在任何平台都成立。
3. **`ret` 的規律**：depth 0 的 return address 是 `...851c`，指向 `main` 裡呼叫之後的位置；depth 1 到 3 都是 `...8614`，因為它們都是被 `walk_ifd` 自己呼叫，回去的是同一個位置。這就是 stack trace 裡同一函式重複的樣子。
4. **frame 與 local 的關係**：每層 `frame` 都比 `local` 高 `0x58` = 88 bytes，表示 `tag_buf` 放在 frame pointer 下方固定位移處，正如 x86-64 的 `-8(%rbp)` 一樣。
5. **兩種 stack 大小**：main thread 的上限約 8 MiB（就是 `ulimit -s` 的值），新 thread 預設只有 512 KiB（macOS）。照每層 144 bytes 估算，main thread 能遞迴約 8176 × 1024 ÷ 144 ≈ 58,000 層，一般 thread 只有 512 × 1024 ÷ 144 ≈ 3,640 層，相差 16 倍。故事中「測試正常、production 當掉」就是這個差距。

Linux 上的數字不同：glibc 建立 thread 時的預設 stack 取程式啟動時的 `ulimit -s`（常見為 8 MiB；若設為 unlimited，則改用架構的預設值），musl（Alpine 映像檔）預設只有 128 KiB。`thumbd` 自己用 `pthread_attr_setstacksize` 設成 256 KiB，所以不論在哪個平台都比 main thread 小得多。

### 程式二：自己走一遍 frame pointer 鏈

這段程式模擬 crash handler 的做法：從目前的 frame pointer 出發，一層層讀出 return address，再和 libc 的 `backtrace()` 對照。

```c
#include <execinfo.h>
#include <stdint.h>
#include <stdio.h>

/* 沿著 frame pointer 串起來的鏈結串列走回去：
 * frame pointer 指向的位置存著「上一層的 frame pointer」，緊接著是 return address。
 * x86-64（%rbp）與 ARM64（x29）都是這個布局，但前提是程式保留了 frame pointer。 */
struct frame {
    struct frame *caller;   /* [fp + 0]：上一層的 frame pointer */
    void *ret;              /* [fp + 8]：回到上一層的 return address */
};

__attribute__((noinline)) static void dump_stack(void) {
    struct frame *fp = __builtin_frame_address(0);
    for (int i = 0; fp != NULL && i < 8; i++) {
        printf("  #%d  fp=%p  ret=%p\n", i, (void *)fp, fp->ret);
        /* 保護：上一層一定在更高的位址，而且不會離太遠；否則鏈結已經斷了 */
        if (fp->caller <= fp || (uintptr_t)fp->caller - (uintptr_t)fp > (1u << 20))
            break;
        fp = fp->caller;
    }
    void *addrs[8];
    int n = backtrace(addrs, 8);           /* libc 提供的版本，對照用 */
    printf("backtrace() 找到 %d 層：", n);
    for (int i = 0; i < n; i++)
        printf(" %p", addrs[i]);
    printf("\n");
}

__attribute__((noinline)) static void decode_jpeg(void) { dump_stack(); __asm__ volatile(""); }
__attribute__((noinline)) static void handle_request(void) { decode_jpeg(); __asm__ volatile(""); }
__attribute__((noinline)) static void worker_loop(void) { handle_request(); __asm__ volatile(""); }

int main(void) {
    printf("decode_jpeg=%p handle_request=%p worker_loop=%p main=%p\n",
           (void *)decode_jpeg, (void *)handle_request, (void *)worker_loop, (void *)main);
    worker_loop();
    return 0;
}
```

在 macOS arm64 上執行：

```text
decode_jpeg=0x102bc44b4 handle_request=0x102bc44c8 worker_loop=0x102bc44dc main=0x102bc4460
  #0  fp=0x16d239030  ret=0x102bc44c0
  #1  fp=0x16d239040  ret=0x102bc44d4
  #2  fp=0x16d239050  ret=0x102bc44e8
  #3  fp=0x16d239060  ret=0x102bc44a4
  #4  fp=0x16d239090  ret=0x1878004e4
  #5  fp=0x16d2396f0  ret=0x0
backtrace() 找到 6 層： 0x102bc456c 0x102bc44c0 0x102bc44d4 0x102bc44e8 0x102bc44a4 0x1878004e4
```

逐步對照：

1. 第 #0 層是 `dump_stack` 自己的 frame，它的 return address `...44c0` 落在 `decode_jpeg`（從 `...44b4` 開始）的範圍內，也就是「`decode_jpeg` 裡呼叫 `dump_stack` 的下一條指令」。
2. 依此類推：`...44d4` 在 `handle_request` 裡、`...44e8` 在 `worker_loop` 裡、`...44a4` 在 `main` 裡。只靠 return address 加上「哪個函式的起點最接近」，就重建出了 `main → worker_loop → handle_request → decode_jpeg → dump_stack` 的呼叫鏈。debugger 做的符號查詢，本質就是這個比對。
3. 第 #4 層的 `0x1878004e4` 在 `main` 的呼叫者裡，也就是 macOS 的 `dyld` 啟動程式；第 #5 層 return address 為 0，鏈的終點。
4. `backtrace()` 的結果和我們自己走的完全一致，只多了最前面一個 `...456c`，那是 `backtrace()` 被呼叫的位置（在 `dump_stack` 內）。
5. 各層 `fp` 只差 16 bytes，因為這些函式除了 saved frame pointer 與 return address 之外什麼都沒存。

這段程式依賴 frame pointer。macOS arm64 的 ABI 要求一律保留，所以 `-O1` 也能走完；在 Linux x86-64 上要加 `-fno-omit-frame-pointer` 編譯。否則 `dump_stack` 自己雖然會因為呼叫 `__builtin_frame_address` 而建立 frame，上面幾層卻沒有，`%rbp` 裡裝的不是上一層的 frame 位址，所以通常只走得出第 #0 層，再往上讀到的就是無意義的值（程式裡的保護條件會讓它提早停止，而不是當機）。我們沒有 Linux 機器，改在本機用 Rosetta 以 `cc -arch x86_64 -O1 -fomit-frame-pointer` 模擬，結果正是只剩 #0 一層有效的 return address；在 macOS 上連 `backtrace()` 也只剩兩層，因為 macOS 的 `backtrace()` 同樣靠 frame pointer，而 Linux glibc 的 `backtrace()` 改用 `.eh_frame`，不受影響（練習 4）。

### 用 debugger 驗證

用 `cc -g -O0` 編譯程式二，在 lldb 裡停在 `decode_jpeg`，看 stack trace、暫存器與 frame pointer 指向的兩個 8-byte 值。以下是 macOS arm64 上 `lldb --batch` 的實際輸出（節錄）：

```text
(lldb) bt
* thread #1, queue = 'com.apple.main-thread', stop reason = breakpoint 1.1
  * frame #0: 0x00000001000004d4 p2g`decode_jpeg at p2.c:30:59
    frame #1: 0x00000001000004ec p2g`handle_request at p2.c:31:62
    frame #2: 0x0000000100000500 p2g`worker_loop at p2.c:32:59
    frame #3: 0x00000001000004bc p2g`main at p2.c:37:5
    frame #4: 0x00000001878004e4 dyld`start + 6992
(lldb) register read fp sp lr
      fp = 0x000000016fdfcdd0
      sp = 0x000000016fdfcdd0
      lr = 0x00000001000004ec  p2g`handle_request + 12 at p2.c:31:99
(lldb) memory read -fx -s8 -c2 $fp
0x16fdfcdd0: 0x000000016fdfcde0 0x00000001000004ec
```

最後一行就是 frame pointer 鏈的實體：`fp` 指向的第一個 8 bytes `0x16fdfcde0` 是上一層的 frame pointer（比目前高 16 bytes），第二個 8 bytes `0x1000004ec` 是 return address，正好等於 `bt` 中 frame #1 的位址 `handle_request + 12`。

在 Linux x86-64 上，gdb 的對應操作如下（示意輸出，位址每台機器不同）：

```text
(gdb) break decode_jpeg
(gdb) run
(gdb) bt
#0  decode_jpeg () at p2.c:30
#1  0x0000555555555201 in handle_request () at p2.c:31
#2  0x0000555555555215 in worker_loop () at p2.c:32
#3  0x0000555555555245 in main () at p2.c:37
(gdb) x/2gx $rbp
0x7fffffffe3f0: 0x00007fffffffe400  0x0000555555555201
(gdb) info frame
Stack level 0, frame at 0x7fffffffe400:
 rip = 0x5555555551e5 in decode_jpeg (p2.c:30); saved rip = 0x555555555201
 called by frame at 0x7fffffffe410
 ...
```

| 想看什麼 | gdb | lldb |
|---|---|---|
| 完整呼叫鏈 | `bt`（`bt full` 連 local 變數） | `bt` |
| 切到第 N 層 | `frame N`、`up`、`down` | `frame select N`、`up`、`down` |
| 這一層的 frame 資訊 | `info frame` | `frame info` |
| 暫存器 | `info registers rsp rbp rip` | `register read sp fp lr` |
| stack 原始內容 | `x/16gx $rsp` | `memory read -fx -s8 -c16 $sp` |
| 對照組合語言 | `disassemble`、`x/8i $rip` | `disassemble -f` |

## 9.12 在工作上怎麼用

### 讀 core dump 的 stack：一套固定流程

`thumbd` 當機時，阿哲和小安後來固定照這個流程走：

```bash
# 1. 取得 core（systemd 系統）
coredumpctl list thumbd
coredumpctl gdb thumbd            # 直接用 gdb 打開最近一次的 core

# 2. 在 gdb 裡
(gdb) bt                           # 呼叫鏈；太長時用 bt 20 與 bt -20 看頭尾
(gdb) info threads                 # 是哪個 thread 當的？
(gdb) frame 0
(gdb) x/i $rip                     # 當在哪一條指令
(gdb) info registers rsp rip
(gdb) info proc mappings           # %rsp 落在哪個區域？是不是剛好在 stack 的底端
```

判斷是不是 stack overflow 的關鍵是最後一步：如果 fault 時的 `%rsp` 剛好落在某個 thread stack 區域的最低處附近（緊鄰 guard page），而且 `bt` 是同一個函式重複上千層，就可以確定。接著用 `frame 100`、`frame 1000` 看不同深度的參數，找出是哪一種輸入讓遞迴停不下來。

### 修 stack overflow：不是只把 stack 開大

小安的第一個想法是把 worker 的 stack 從 256 KiB 調到 8 MiB。老周說這只是把門檻往後推：TIFF 的 IFD 鏈長度由使用者上傳的檔案決定，攻擊者可以做出任意深的圖。正確的修法有三層：

1. **限制深度**：`parse_ifd` 加上 depth 參數，超過合理上限（例如 32 層）就回傳格式錯誤。這同時防住了「子目錄互相指來指去」的循環。
2. **把遞迴改成迴圈**：用自己配置在 heap 上的陣列當 stack，存「待處理的 offset」。heap 上的 stack 可以檢查大小、可以回報錯誤，不會悄悄撞上 guard page。
3. **把 stack 大小當成設定，而且量一下**：用 `pthread_attr_setstacksize` 明確設定，並在壓力測試時觀察最深的使用量。

估算需要多少 stack，可以用編譯器報告每個函式的 frame 大小：

```bash
gcc -O2 -fstack-usage -c tiff.c      # 產生 tiff.su，列出每個函式的 stack 用量
cat tiff.su
# tiff.c:80:13:parse_ifd    112    static
gcc -O2 -Wstack-usage=4096 -c tiff.c # 單一函式超過 4 KiB 就警告
```

`112 static` 表示 `parse_ifd` 每層固定 112 bytes（示意數值），乘上允許的最大深度，再加上呼叫鏈上其他函式（libjpeg、libpng 的解碼函式可能各要好幾 KiB），就是 thread stack 的下限。

### 讓 profiler 看得到完整的呼叫鏈

flame graph 一半是 `[unknown]` 的對策，依成本由低到高：

| 做法 | 指令 | 優點 | 缺點 |
|---|---|---|---|
| 用 DWARF unwinding | `perf record --call-graph dwarf -p <PID>` | 不用重新編譯 | 每個樣本複製一段 stack，資料量大、開銷高 |
| 用 LBR（Intel 硬體記錄最近的分支） | `perf record --call-graph lbr` | 開銷低 | 需要較新的 Intel CPU、只限 user space、深度有限（數十層） |
| 重新編譯並保留 frame pointer | `CFLAGS += -fno-omit-frame-pointer`，再 `perf record -g` | 便宜、可靠，線上可長期開著 | 依賴的 library 也要有 frame pointer 才完整 |

`thumbd` 最後選了第三種：production build 加上 `-fno-omit-frame-pointer`，量測後整體吞吐量差距在誤差範圍內，flame graph 從此每一層都看得到。

### 跨語言與手寫組合語言的檢查清單

當你寫 FFI、callback、JIT 或幾行 inline assembly 時，calling convention 就從「編譯器的事」變成「你的事」：

- 宣告的原型和實際函式一致嗎？參數型別錯一個（例如 `int` 寫成 `long`、`float` 寫成 `double`），值就會從錯的暫存器或錯的寬度讀出。
- 有沒有用到 callee-saved 暫存器卻沒還原？症狀常常是「回到呼叫者之後，某個變數莫名其妙變了」。
- 呼叫其他函式之前，`%rsp` 是 16 的倍數嗎？症狀是在 `printf`、`memcpy` 這類 library 函式內部的 `movaps` 當機。
- 傳給別的平台的程式碼，ABI 一樣嗎？Windows x64 的參數暫存器和 Linux 不同。
- callback 會不會在另一個 thread、另一個 stack 上被呼叫？那個 stack 夠大嗎？

## 9.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| segfault，`bt` 是同一函式重複上千層 | 遞迴過深造成 stack overflow，常見於 thread stack 較小時 | `info proc mappings` 看 `%rsp` 是否在 stack 區域底端；比較 thread stack 大小 | 限制深度、改成迴圈；用 `-fstack-usage` 估算後設定 `pthread_attr_setstacksize` |
| 回傳的指標內容「過一下就變了」 | 回傳 local 變數的位址，frame 已被下一次呼叫覆蓋 | 編譯警告 `-Wreturn-stack-address`；ASan 的 `stack-use-after-return` 偵測 | 改成由呼叫者提供緩衝區，或用 `malloc` 配置並明確交代誰負責 `free` |
| 當在 `printf` 等 library 內部的 `movaps` | 手寫組合語言或 JIT 呼叫函式前 `%rsp` 沒有 16-byte 對齊 | gdb 中 `p/x $rsp`，看 `call` 前是否為 16 的倍數 | 依 9.5 節手算，補上 `sub $8, %rsp` 或調整 push 數量 |
| 回到呼叫者後某個變數莫名改變 | 被呼叫的組合語言改了 callee-saved 暫存器卻沒恢復 | 在呼叫前後 `info registers rbx r12 r13 r14 r15` 比較 | 在函式開頭 push、結尾 pop 用到的 callee-saved 暫存器 |
| stack trace 出現 `??` 或只有一兩層 | binary 被 strip、或 stack 被 overflow 寫壞 | `file` 看是否 stripped；`x/32gx $rsp` 看是否滿是同一個值（例如 `0x4141414141414141`） | 保留 debug symbol；用 ASan 重現寫壞 stack 的 bug（第 11、26 章） |
| flame graph 大量 `[unknown]` | 程式或 library 省略 frame pointer，`perf -g` 走不下去 | 反組譯看函式開頭有沒有 `push %rbp; mov %rsp,%rbp` | `-fno-omit-frame-pointer` 重新編譯，或改用 `--call-graph dwarf` |
| FFI 呼叫拿到的參數是亂碼 | 宣告的原型和實際函式不一致，或混用不同平台的 ABI | 對照兩邊的函式宣告；在被呼叫端 `info registers rdi rsi rdx` | 用共用的標頭檔產生 binding，不要手寫原型 |

## 9.14 動手練習

1. **手算**：一個函式開頭是 `pushq %rbp; pushq %rbx; subq $24, %rsp`，之後呼叫別的函式。`call` 之前 `%rsp` 有沒有 16-byte 對齊？如果把 `subq $24` 改成 `subq $16` 呢？（答案：進入時餘 8，加上 8 + 8 + 24 = 40，總共 48，餘 0，對齊；改成 16 則總共 40，餘 8，不對齊。）
2. **手算**：寫出 `long f(long a, double b, int c, double d, long e, long g, long h, long i)` 每個參數放在哪個暫存器或 stack 位置（相對於進入 `f` 時的 `%rsp`）。用 `clang -target x86_64-linux-gnu -O1 -S` 編譯一個用到所有參數的版本驗證。
3. **延伸程式一**：把 `tag_buf` 改成 16 bytes 與 256 bytes，記錄每層相差的 bytes，推算 frame 大小與 local 陣列大小的關係。再用 `pthread_attr_setstacksize` 建立一個 64 KiB stack 的 thread，在裡面呼叫 `walk_ifd`，算出理論上的最大深度（不要真的跑到當機）。
4. **延伸程式二**：在 Linux x86-64 上分別用 `-O1` 與 `-O1 -fno-omit-frame-pointer` 編譯，觀察自己走的鏈在哪一層斷掉，而 `backtrace()` 是否仍然完整，並解釋原因（提示：`.eh_frame`）。
5. 用 `clang -target x86_64-linux-gnu -O1 -S` 編譯一個會回傳 32-byte struct 的函式，在組合語言中找出「隱藏的第一個參數」：哪一個暫存器帶著結果的位址？`%rax` 回傳了什麼？
6. 在你工作上的某個 C／C++ 或 Rust 服務上執行 `perf record -g` 與 `perf record --call-graph dwarf`，比較兩份 flame graph 中 `[unknown]` 的比例。

## 本章重點整理

- 函式呼叫要處理控制轉移、資料傳遞、local 儲存與保護呼叫者狀態四件事；因為呼叫是後進先出，所以這些狀態放在 run-time stack 上，每次呼叫一個 frame。
- x86-64 的 stack 往低位址成長，`%rsp` 指向頂端；stack 只是一段普通記憶體，frame 布局由編譯器和 ABI 約定，沒有執行期檢查。
- `call` 把下一條指令的位址（return address）push 到 stack 再跳過去，`ret` 把它 pop 回 `%rip`；return address 就存在普通記憶體中，被越界寫入蓋掉時 `ret` 不會察覺，這是 stack buffer overflow 危險的原因。
- System V AMD64 ABI 用 `%rdi`、`%rsi`、`%rdx`、`%rcx`、`%r8`、`%r9` 傳前六個整數參數，`%xmm0`–`%xmm7` 傳浮點參數，回傳值放 `%rax` 或 `%xmm0`；第 7 個以後的參數放在 return address 上方，由呼叫者清除。
- local 變數在暫存器不夠、需要取位址、或是陣列與 struct 時才放上 stack；函式結束只是把 `%rsp` 移回去，所以回傳 local 變數的位址一定是錯的。
- `call` 之前 `%rsp` 必須是 16 的倍數；每個函式進入時餘 8，可以用「所有 push 與 sub 的總和」手算是否對齊。
- callee-saved 暫存器（`%rbx`、`%rbp`、`%r12`–`%r15`）由被呼叫者負責還原，適合放跨越呼叫的值；caller-saved 暫存器被呼叫者可以隨意改寫。
- frame pointer `%rbp` 讓所有 frame 串成鏈結串列，`8(%rbp)` 是 return address、`0(%rbp)` 是上一層的 `%rbp`；x86-64 在 `-O1` 以上預設省略它，改靠 `.eh_frame` 的 unwind 資訊。
- 遞迴的每一層都是普通呼叫、有自己的 frame；編譯器可能把部分遞迴改寫成迴圈或 tail call，但不能依賴這件事。
- stack overflow 是撞到 thread stack 底端的 guard page 而產生的普通 SIGSEGV；thread stack 通常比 main thread 小很多，深度由外部輸入決定的遞迴要限制深度或改成迴圈。
- red zone 是 `%rsp` 之下 128 bytes、leaf function 可直接使用的空間；Linux kernel、Windows x64 與 AArch64 Linux 沒有 red zone。
- stack trace 由 debugger 從 core dump 的暫存器出發，用 CFI 或 frame pointer 一層層找 return address，再用符號表查函式名稱；缺符號、缺 unwind 資訊或 stack 被寫壞時就會出現 `??` 或斷鏈。
- profiler 的 `[unknown]` 通常是省略 frame pointer 造成的，可以改用 DWARF unwinding，或重新編譯時加上 `-fno-omit-frame-pointer`。

## 延伸問答

> [!question]- Q1. 為什麼 `call` 之前 `%rsp` 要是 16 的倍數，而不是 8 的倍數就好？
> 因為 x86-64 有一些 SSE 指令（例如 `movaps`、`movdqa`）要求記憶體運算元 16-byte 對齊，否則直接觸發 fault。編譯器會在 stack 上放需要 16-byte 對齊的資料（`long double`、`__m128` 向量、某些 local 陣列），library 也常在函式開頭用這類指令保存 `%xmm` 暫存器。如果每個函式都能假設「進來時 `%rsp` 除以 16 餘 8」，就能用固定的偏移量算出對齊的位置，不必在執行期動態調整。
>
> 這是一個「全體遵守才有用」的約定：只要呼叫鏈上有一個函式沒對齊，下游所有函式算出的位置都會錯 8 bytes。所以這類 bug 的症狀常常出現在完全無辜的 library 函式裡，要往上找是哪一層手寫組合語言或 JIT 程式碼沒有遵守。

> [!question]- Q2. 程式找錯：下面這段為什麼有時印出正確的字串、有時印出亂碼？`char *fmt_size(int w, int h) { char buf[32]; snprintf(buf, sizeof buf, "%dx%d", w, h); return buf; }`
> `buf` 是 `fmt_size` 的 local 陣列，存在它的 stack frame 裡。函式回傳時只是把 `%rsp` 移回去，那塊記憶體的內容還在，但已經不屬於任何人。呼叫者如果立刻讀取，常常還能看到正確的字串，看起來「好像沒問題」；一旦中間又呼叫了別的函式（例如 `printf` 本身），新的 frame 就會蓋在同一塊位置，內容就變成亂碼。
>
> 這是 undefined behavior，結果依編譯器與呼叫順序而定，這也是它難以除錯的原因。clang 會發出 `-Wreturn-stack-address` 警告，ASan 開啟 `detect_stack_use_after_return` 可以在執行期抓到。修法是讓呼叫者提供緩衝區（`void fmt_size(char *out, size_t n, int w, int h)`），或回傳 `malloc` 的記憶體並在文件中寫清楚誰負責 `free`。

> [!question]- Q3. 手算題：`long g(long a1, ..., long a9)` 有九個 `long` 參數。進入 `g` 時，第 7、8、9 個參數分別在哪裡？
> 前六個參數依序放在 `%rdi`、`%rsi`、`%rdx`、`%rcx`、`%r8`、`%r9`。第 7 個以後的參數由呼叫者放在 stack 上，編號小的在低位址，而且緊接在 return address 上方。進入 `g` 的那一刻，`(%rsp)` 是 return address，所以第 7 個參數在 `8(%rsp)`、第 8 個在 `16(%rsp)`、第 9 個在 `24(%rsp)`。
>
> 對齊也要考慮：三個參數共 24 bytes，不是 16 的倍數，所以呼叫者在 push 參數之前會先多留 8 bytes 的空隙，讓 `call` 之前的 `%rsp` 仍是 16 的倍數。這個空隙在 24(%rsp) 之上，不影響上面算出的位移。如果 `g` 使用 frame pointer，`push %rbp; mov %rsp, %rbp` 之後，位移會各多 8，變成 `16(%rbp)`、`24(%rbp)`、`32(%rbp)`。

> [!question]- Q4. 面試題：caller-saved 和 callee-saved 暫存器各有什麼好處？如果全部都是 caller-saved 會怎樣？
> 兩種分類是在分攤保存的成本。caller-saved 暫存器適合放「呼叫前就用完」的暫時值，例如計算參數的中間結果，完全不用保存；leaf function 可以盡情使用而沒有任何成本。callee-saved 暫存器適合放「要跨越呼叫」的值，例如迴圈計數器、指向資料結構的指標，被呼叫者只在開頭與結尾各 push／pop 一次，不管中間呼叫多少次函式都不必再存。
>
> 如果全部都是 caller-saved，每個在迴圈中呼叫函式、又要保留狀態的程式，每次呼叫前都得把活著的值存到 stack、呼叫後再讀回來，記憶體存取大增。反過來全部都是 callee-saved，連最簡單的 leaf function 用一個暫存器都得先 push。System V 把 16 個暫存器大約對半分，是兩種成本之間的折衷。

> [!question]- Q5. 你在 production 看到 `thumbd` 的 core dump，`bt` 只顯示三層，最上面一層是 `0x4141414141414141 in ?? ()`。你會怎麼判斷？
> `0x41` 是字元 `'A'`，`%rip` 變成一連串 `A`，強烈暗示 stack 上的 return address 被一段使用者提供的資料蓋掉了，`ret` 把這段資料當成位址跳過去，結果 fault。這是典型的 stack buffer overflow（第 11 章）：某個 local 陣列寫入超過自己的大小，一路蓋到 saved 暫存器與 return address。因為 return address 已經被破壞，unwinder 也無法往上走，所以 stack trace 只剩幾層。
>
> 下一步是用 `x/64gx $rsp` 看 stack 的原始內容，找出被覆寫的範圍；再根據其他 thread 的狀態、log 中的請求內容，找出觸發的輸入。最有效率的做法是把那個輸入拿到開了 ASan 的 build 重放，ASan 會在越界寫入的那一刻停下並指出是哪一行。這同時也是安全事件，要評估是否有被利用的可能。

> [!question]- Q6. 為什麼 red zone 只有 leaf function 能用？Linux kernel 為什麼要用 `-mno-red-zone` 編譯？
> red zone 是 `%rsp` 之下的 128 bytes，ABI 保證 signal handler 與中斷不會碰它，所以函式可以不調整 `%rsp` 就直接在那裡放資料。但只要函式自己呼叫別人，`call` 就會把 return address push 到 `%rsp − 8`，被呼叫的函式也會在 `%rsp` 之下建立 frame，這些都會蓋掉 red zone 裡的資料。所以只有不呼叫別人的 leaf function 能安全使用。
>
> user space 的 red zone 之所以安全，是因為 kernel 在 user stack 上放 signal frame 時，會刻意先跳過 128 bytes。但在 kernel 內部，硬體中斷發生時，CPU 會直接把中斷的狀態 push 到目前的 kernel stack 上，沒有人會跳過 128 bytes。如果 kernel 函式用了 red zone，中斷一來資料就被蓋掉。因此 kernel 和其他會被中斷直接打斷的程式（bootloader、部分嵌入式程式）都必須關閉 red zone。

> [!question]- Q7. 省略 frame pointer 之後，gdb 為什麼還能印出完整的 stack trace？profiler 為什麼常常不行？
> 編譯器即使省略 frame pointer，也會在 ELF 的 `.eh_frame` section 產生 DWARF CFI，描述「在函式的每一個指令位置，CFA（上一層呼叫時的 `%rsp`）等於目前 `%rsp` 加多少、return address 與各 callee-saved 暫存器存在哪裡」。gdb 讀 core dump 時有充裕的時間解析這些表格，一層層算出上一層的暫存器，所以能得到完整的 stack trace。C++ exception 與 Linux glibc 的 `backtrace()` 也靠同一份資訊。
>
> profiler 的處境不同：它每秒要取樣成千上萬次，而且常常在 kernel 裡、在中斷的當下取 call stack，沒有時間也不方便解析 DWARF。`perf record -g` 預設只沿著 frame pointer 走，遇到省略 frame pointer 的函式就斷鏈。`--call-graph dwarf` 的做法是先把一段 stack 原始資料複製下來，事後再慢慢解析，所以資料量大、開銷高。這就是為什麼越來越多發行版與公司選擇在 production build 保留 frame pointer。

> [!question]- Q8. 同一個遞迴函式，為什麼在 main thread 跑得好好的，丟進 thread pool 就當機？要怎麼決定 thread stack 該設多大？
> main thread 的 stack 由 kernel 在 `execve` 時建立，上限由 `ulimit -s`（`RLIMIT_STACK`）決定，常見是 8 MiB，而且會隨使用量自動往下長。其他 thread 的 stack 是建立 thread 時一次 `mmap` 出來的固定大小區域，底下有 guard page：macOS 預設 512 KiB、musl 約 128 KiB，很多服務還會為了節省記憶體主動設小。同樣的遞迴深度，在 main thread 遠遠用不完，在小 stack 的 thread 上就撞到 guard page 而 SIGSEGV。
>
> 決定大小要估算最深的呼叫鏈：用 `-fstack-usage` 取得每個函式的 frame 大小，乘上遞迴的最大深度，加上呼叫的 library 的用量，再留一倍以上的餘裕。更重要的是，深度由外部輸入決定的遞迴（解析檔案、JSON、正規表示式）本來就不該只靠 stack 大小保護，要限制深度或改成迴圈。stack 開大只是延後問題，攻擊者總能做出更深的輸入。

## 延伸閱讀

- [System V AMD64 ABI（x86-64 psABI）](https://gitlab.com/x86-psABIs/x86-64-ABI)：參數傳遞、暫存器分類、stack 對齊與 red zone 的正式規格。
- [GDB 使用手冊](https://sourceware.org/gdb/current/onlinedocs/gdb.html/)：「Examining the Stack」一章說明 `bt`、`frame`、`info frame` 的完整用法。
- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書 3.7 節，以及 Bomb Lab 的說明（拆炸彈時大量用到本章的 stack 與暫存器知識）。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：「Machine-Level Programming III: Procedures」的投影片與錄影。
- [Linux man pages](https://man7.org/linux/man-pages/)：`pthread_attr_setstacksize(3)`、`getrlimit(2)`、`backtrace(3)`、`core(5)`。
- [Intel 64 and IA-32 Architectures Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)：第 1 卷關於 stack 與 `CALL`／`RET` 的說明。
