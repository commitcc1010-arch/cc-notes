---
chapter: 20
title: Exception 與 Process
part: 6
---

# 第 20 章　Exception 與 Process：程式如何把控制權交給作業系統

> [!abstract] 本章地圖
> **核心問題**：CPU 一條接一條執行你的指令，作業系統卻能在任何時刻插手：處理網路封包、讀磁碟、切換到別的程式、在你存取壞指標時終止你。控制權是怎麼在你的程式與 kernel 之間移交的？
>
> **你會學到**：
> - 說出 exceptional control flow 的各個層次，以及 interrupt、trap、fault、abort 的差別與返回位置
> - 描述一次 system call 從 C 函式、暫存器、`syscall` 指令到 kernel 再回來的完整路徑，並估算它的代價
> - 解釋 process 提供的兩個假象：獨占 CPU 的 logical control flow，以及私有的位址空間
> - 分辨 user mode 與 kernel mode、user time 與 sys time，說明 context switch 何時發生、保存什麼
> - 正確處理系統呼叫的錯誤：回傳值、`errno`、`EINTR`，以及三種錯誤回報風格
> - 用 `strace` 找出程式發出了哪些系統呼叫、花了多少時間，並據此最佳化
>
> **前置知識**：第 9 章（暫存器與 calling convention）、第 13 章（pipeline 與例外的關係）、第 19 章（PLT 與 shared library）
>
> **對應 CS:APP 3e**：第 8 章 8.1–8.3 節

## 20.1 故事：一次重構讓 `sys` 時間暴增

`thumbd` 有一段讀取原圖檔的程式，原本用 C 標準函式庫的 `fread`。上個月有人做了一次「簡化」：為了不依賴 stdio，改成直接呼叫 `read`，而且為了方便解析 JPEG 的標記，每次只讀 1 個 byte。程式碼看起來更短、更「底層」，測試也全部通過。

上線後，SRE 阿哲發現縮圖的 p99 延遲從 80 ms 漲到 400 ms 左右。`top` 上 `thumbd` 的 CPU 使用率升高了，但拆開來看，增加的幾乎都是 `sy`（kernel 時間）：系統整體的 `sy` 從 5% 漲到 40%，`us`（使用者程式時間）反而沒什麼變。小安看不懂：「我們的程式在跑，為什麼時間算在 kernel 頭上？」

老周在測試機上跑了一行指令：

```bash
strace -c -f -p $(pidof thumbd)
```

幾秒鐘後按下 Ctrl-C，統計表的第一列是 `read`，呼叫次數是幾百萬次。老周說：「每一次 `read` 都是一次 system call，CPU 要從你的程式切進 kernel、做完事再切回來。讀一個 3 MB 的 JPEG，你們發出了三百多萬次。」

同一週，阿哲還回報了另一件怪事：有一批檔案權限設錯，`thumbd` 的錯誤 log 卻寫著 `open /data/photos/a.jpg failed: Inappropriate ioctl for device`，完全看不出是權限問題。

這兩個問題都和本章的主題有關：程式怎麼把控制權交給作業系統（system call 是其中一種方式）、這要付出什麼代價，以及作業系統怎麼把錯誤告訴程式。要回答它們，得先看清楚 CPU 的「正常」控制流程在什麼情況下會被打斷。

## 20.2 Exceptional control flow：控制流程的突然轉向

CPU 從開機到關機，做的事情可以描述成一串位址 a₀、a₁、a₂…，每個位址是一條指令，這串序列叫 **control flow**（控制流程）。從 aₖ 到 aₖ₊₁ 的轉移，大部分是「下一條指令」，或者是 `jmp`、`call`、`ret` 這類由程式自己決定的跳躍（第 8、9 章）。這些轉移都是程式**預期中**的。

但系統還必須回應程式之外的事件：網卡收到了封包、計時器到了、磁碟讀完了資料、程式除以零、程式存取了一個還沒對應實體記憶體的頁（第 23 章的 page fault）、使用者按下了 Ctrl-C。這些事件會讓控制流程**突然轉向**，CS:APP 把這類轉移統稱為 **exceptional control flow**（ECF，例外控制流程）。

ECF 不是單一機制，而是在系統的每一層都出現：

| 層次 | 機制 | 誰觸發、誰處理 | 本書章節 |
|---|---|---|---|
| 硬體 | exception（interrupt、trap、fault、abort） | 硬體偵測事件，跳到 kernel 的 handler | 本章 |
| 作業系統 | context switch | kernel 從一個 process 切到另一個 | 本章 |
| 作業系統 → process | signal | kernel 通知 process 某事件發生，跳到 process 的 handler | 第 22 章 |
| 應用程式 | nonlocal jump（`setjmp`／`longjmp`） | 程式自己跳回較早的函式呼叫 | 第 22 章 |
| 程式語言 | `try`／`catch`、`raise` | 語言 runtime 展開 stack | 第 22 章簡介 |

這一章處理最底下的兩層。你熟悉的 Python `raise`、Java `throw` 是最上層的 ECF，它們的實作和硬體 exception 完全不同，只是名字相同；但理解底層之後，你會知道很多上層錯誤（例如 Java 的 `NullPointerException`、Python 的 `MemoryError`）其實源自底層的事件。

## 20.3 Exception：硬體與作業系統的合作

**exception**（例外）在這裡指的是：處理器狀態發生某種變化（叫 **event**，事件）時，控制流程突然轉移到作業系統的一段程式（**exception handler**，例外處理程式）。事件可能和目前執行的指令有關（除以零、page fault），也可能無關（計時器、網卡）。

### Exception table

系統中每一種 exception 都有一個編號，叫 **exception number**。有些由處理器設計者定義（除以零、page fault、一般保護錯誤），有些由作業系統定義（system call、各種外部裝置的 interrupt）。開機時，作業系統建立一張 **exception table**（例外表），第 k 格放著第 k 種 exception 的 handler 位址；表的起始位址存在一個特殊暫存器裡（x86-64 稱為 IDT，interrupt descriptor table，起點放在 IDTR 暫存器）。

```text
                  exception table（kernel 開機時建立）
                  ┌─────────────────────────────┐
 IDTR ──────────▶ │ 0   除以零的 handler 位址    │
                  │ 1   …                       │
 事件發生           │ …                           │
 exception k      │ 13  一般保護錯誤 handler     │
   │              │ 14  page fault handler      │ ─────▶ kernel 中的 handler 程式碼
   │ 硬體：       │ …                           │
   │ 位址 = IDTR  │ 32+ 計時器、網卡、磁碟 …     │
   │      + k×項目大小                          │
   └──────────▶   └─────────────────────────────┘
```

事件發生時，硬體做的事情很固定：

1. 判斷這是第幾號 exception（k）。
2. 從 exception table 第 k 格取出 handler 位址。
3. 切換到 **kernel mode**（20.7 節），換到 kernel 自己的 stack。
4. 把返回位址與被打斷時的處理器狀態（例如 flags 暫存器）推進 kernel stack。
5. 跳到 handler 執行。

handler 做完後，執行一條特殊的「從 interrupt 返回」指令（x86-64 是 `iretq`；system call 有專用的 `sysretq`），把狀態彈回來、切回 user mode，回到被打斷的程式。

### Exception 和函式呼叫哪裡不一樣

exception 看起來很像一次 `call`：跳到別處、執行完再回來。但有四個關鍵差異：

| 面向 | 函式呼叫（`call`） | Exception |
|---|---|---|
| 跳到哪裡 | 指令裡寫明的位址 | 由 exception 編號查表決定 |
| 返回位址 | 一定是下一條指令 | 依類型而定：可能是**目前這條指令**（重做）、下一條，或根本不返回 |
| 推進 stack 的東西 | 只有返回位址 | 返回位址加上處理器狀態，例如 flags |
| 用哪個 stack、什麼權限 | 程式自己的 stack、user mode | kernel stack、kernel mode，可以存取所有記憶體與硬體 |

「返回位址可能是目前這條指令」這一點特別重要。第 23 章的 page fault 就是如此：kernel 補好那一頁之後，CPU 重新執行同一條 `mov`，程式完全感覺不到中間發生過什麼。

## 20.4 四種 exception

依照「是不是由目前的指令造成」與「處理完回到哪裡」，exception 分成四類：

| 類別 | 原因 | 同步／非同步 | 處理完回到哪裡 | 例子 |
|---|---|---|---|---|
| **interrupt**（中斷） | 處理器外部的 I/O 裝置發出訊號 | 非同步（和目前的指令無關） | 下一條指令 | 計時器、網卡收到封包、磁碟 DMA 完成 |
| **trap**（陷阱） | 程式**刻意**執行的指令 | 同步 | 下一條指令 | system call（`syscall`）、除錯中斷點（`int3`） |
| **fault**（錯誤） | 指令執行時遇到**可能可以修復**的問題 | 同步 | 修好了就重做目前指令；修不好就終止程式 | page fault、除以零、一般保護錯誤 |
| **abort**（中止） | 無法修復的硬體錯誤 | 同步 | 不返回，程式（或系統）終止 | 無法更正的記憶體錯誤（machine check） |

**同步**（synchronous）的意思是：事件是執行某條指令的直接結果，重跑同一段程式，同一條指令還會再觸發一次。interrupt 是**非同步**（asynchronous）的：它和目前正在執行哪條指令無關，只是「剛好在這時候」到達。

### Interrupt：外部世界敲門

`thumbd` 的機器上，網卡收到一個 HTTP 請求的封包，就對處理器的 interrupt 腳位送出訊號。處理器**做完目前這條指令**後，才檢查有沒有待處理的 interrupt，有的話就跳到對應的 handler：

```text
 thumbd 的指令流     I(k-1)   I(k)   ┊          ┊  I(k+1)   I(k+2)
                                  ▲  ┊          ┊  ▲
 網卡送出 interrupt ──────────────┘  ┊          ┊  │
                    做完 I(k) 才處理  ┊          ┊  │
                                     ▼          │  │
 kernel                         interrupt handler ─┘ 回到下一條 I(k+1)
                                （把封包從網卡搬到記憶體、喚醒等待的程式）
```

**計時器 interrupt**（timer interrupt）是所有 interrupt 中最重要的一個：硬體計時器每隔一小段時間（通常是幾毫秒）就觸發一次，讓 kernel 有機會拿回控制權、決定要不要換別的程式執行（20.8 節）。沒有它，一個寫了 `while (1);` 的程式就能永遠霸佔 CPU。

### Trap：程式主動請求服務

trap 是程式**故意**觸發的 exception，最重要的用途是 **system call**（系統呼叫）：程式請 kernel 替它做自己沒有權限做的事，例如讀檔案（`read`）、建立 process（`fork`）、配置位址空間（`mmap`）。20.5 節會詳細拆解。

### Fault：可能可以修好的錯誤

fault 發生在指令執行**到一半**時，handler 會嘗試修正問題。最常見的是 page fault：存取的頁不在實體記憶體中，kernel 把它準備好，然後**重新執行**同一條指令。如果問題無法修正，例如位址根本不屬於任何合法區域，kernel 就不返回原指令，而是送出 signal 讓程式終止（第 22 章）。

用 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - fault.c` 產生下面三個函式的組合語言（只保留函式本體），各自對應一種 exception 的來源：

```c
int divide(int a, int b) { return a / b; }          /* b == 0 時 x86-64 產生 #DE fault */
int load(const int *p)   { return *p; }             /* p 無效時產生 page fault */
long my_getpid(void) {                              /* 自己發出 system call：trap */
    long ret;
    __asm__ volatile("syscall" : "=a"(ret) : "a"(39L) : "rcx", "r11", "memory");
    return ret;
}
```

```asm
divide:
	movl	%edi, %eax
	cltd
	idivl	%esi
	retq
load:
	movl	(%rdi), %eax
	retq
my_getpid:
	movl	$39, %eax
	#APP
	syscall
	#NO_APP
	retq
```

1. `idivl %esi`：除數為 0 時，處理器在這條指令觸發 0 號 exception（divide error）。Linux 的 handler 無法「修好」除以零，於是送 `SIGFPE` 給程式，預設行為是終止程式，shell 會印出 `Floating point exception`（名字有歷史包袱，其實是整數除法）。
2. `movl (%rdi), %eax`：如果 `%rdi` 指向的頁不在記憶體中，觸發 14 號 exception（page fault）。合法位址就補頁重做；不合法就送 `SIGSEGV`。
3. `syscall`：把 39（Linux x86-64 上 `getpid` 的系統呼叫編號）放進 `%eax`，執行 `syscall` 指令，這是一次 trap。

### Abort：無法挽回

abort 通常來自硬體本身的嚴重錯誤，例如記憶體發生無法更正的位元錯誤。x86-64 上叫 machine check（18 號）。handler 不會回到原程式；視錯誤影響範圍，kernel 可能終止受影響的 process，或讓整台機器 panic。在雲端環境，這類事件常會讓主機被標記為故障、上面的服務被遷移。

### x86-64 上常見的 exception 編號

| 編號 | 名稱 | 類別 | Linux 的處理結果 |
|---|---|---|---|
| 0 | divide error（#DE） | fault | 送 `SIGFPE` |
| 3 | breakpoint（#BP，`int3` 指令） | trap | 送 `SIGTRAP`，gdb 的中斷點就是靠它（第 2 章） |
| 6 | invalid opcode（#UD） | fault | 送 `SIGILL`，例如在不支援 AVX-512 的 CPU 上執行 AVX-512 指令 |
| 13 | general protection（#GP） | fault | 通常送 `SIGSEGV` |
| 14 | page fault（#PF） | fault | 補頁後重做，或送 `SIGSEGV`（第 23 章） |
| 18 | machine check（#MC） | abort | 終止 process 或 kernel panic |
| 32–255 | 作業系統定義 | interrupt 或 trap | 外部裝置的 interrupt、舊式 system call 等 |

> [!warning] 常見誤解
> 「除以零一定會讓程式當機」。這是 x86-64 的行為，不是普遍真理。ARM64 的整數除法指令遇到除數為 0 時**不會觸發 exception**，硬體直接把結果設為 0。在 C 語言裡，整數除以零是 undefined behavior，不同平台的實際結果不同，不能依賴「它會當機所以會被發現」。浮點數除以零在預設設定下也不會觸發 exception，而是得到 ∞ 或 NaN（第 6 章）。

## 20.5 System call：從 user 程式進入 kernel

你在 C 裡寫 `read(fd, buf, n)`，看起來和呼叫任何函式一樣。實際上 `read` 是 libc 提供的一個薄薄的 **wrapper**（包裝函式），它的工作是把參數照 kernel 的約定放進暫存器，執行 `syscall` 指令，再把 kernel 的回傳值翻譯成 C 的慣例。

Linux x86-64 的 system call 約定和一般函式呼叫（第 9 章）很像，但有一處不同：

| 項目 | 一般函式呼叫（System V ABI） | Linux x86-64 system call |
|---|---|---|
| 指定要做什麼 | `call` 的目標位址 | `%rax` 放 system call 編號 |
| 第 1–6 個參數 | `%rdi`、`%rsi`、`%rdx`、`%rcx`、`%r8`、`%r9` | `%rdi`、`%rsi`、`%rdx`、**`%r10`**、`%r8`、`%r9` |
| 回傳值 | `%rax` | `%rax`；失敗時是 −4095 到 −1 之間的負數，代表 −errno |
| 被破壞的暫存器 | 所有 caller-saved | `%rcx` 和 `%r11`（`syscall` 指令用它們保存返回位址與 flags） |

第四個參數從 `%rcx` 改成 `%r10`，正是因為 `syscall` 指令會把返回位址寫進 `%rcx`，`%rcx` 不能用來傳參數。

幾個常見 system call 在 Linux x86-64 上的編號（編號依架構而定，ARM64 Linux 完全不同）：

| 編號 | 名稱 | 用途 | 本書章節 |
|---|---|---|---|
| 0 | `read` | 從 file descriptor 讀資料 | 第 27 章 |
| 1 | `write` | 寫資料 | 第 27 章 |
| 3 | `close` | 關閉 file descriptor | 第 27 章 |
| 9 | `mmap` | 建立記憶體映射 | 第 24 章 |
| 39 | `getpid` | 取得自己的 process ID | 本章 |
| 57 | `fork` | 建立子行程 | 第 21 章 |
| 59 | `execve` | 載入並執行新程式 | 第 19、21 章 |
| 60 | `exit` | 結束目前的 thread（`exit_group`，231 號，才是結束整個 process） | 第 21 章 |
| 257 | `openat` | 開啟檔案（現代 glibc 的 `open` 實際上用這個） | 第 27 章 |

### 自己寫一個 wrapper

為了看清 libc 的 wrapper 做了什麼，我們自己寫一個簡化版的 `write`：

```c
extern __thread int my_errno;
/* 簡化版的 libc write wrapper：把參數放進暫存器、執行 syscall、處理錯誤 */
long my_write(int fd, const void *buf, unsigned long n) {
    long ret;
    __asm__ volatile("syscall"
                     : "=a"(ret)
                     : "a"(1L), "D"((long)fd), "S"(buf), "d"(n)   /* 1 = write */
                     : "rcx", "r11", "memory");                  /* syscall 會改寫 rcx、r11 */
    if (ret < 0 && ret > -4096) {    /* kernel 回傳 -errno */
        my_errno = (int)-ret;
        return -1;
    }
    return ret;
}
```

用 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - wrap.c` 產生：

```asm
my_write:
	movslq	%edi, %rdi
	movl	$1, %eax
	#APP
	syscall
	#NO_APP
	cmpq	$-4095, %rax
	jb	.LBB0_2
	negl	%eax
	movq	my_errno@GOTTPOFF(%rip), %rcx
	movl	%eax, %fs:(%rcx)
	movq	$-1, %rax
.LBB0_2:
	retq
```

逐行解讀：

1. 參數 `fd`、`buf`、`n` 本來就依 System V ABI 放在 `%rdi`、`%rsi`、`%rdx`，剛好也是 system call 前三個參數的位置，所以編譯器只需要把 32-bit 的 `fd` 符號擴展成 64-bit（`movslq`，第 7 章），再把編號 1 放進 `%eax`。
2. `syscall` 執行後，CPU 已經進入 kernel、做完 `write`、回到下一條指令，結果在 `%rax`。
3. `cmpq $-4095, %rax` 加上 `jb`（無號比較的「小於」，第 8 章）：把 `%rax` 當無號數看，−4095 到 −1 是最大的那 4,095 個值。比它小就是成功，直接回傳。編譯器把我們寫的兩個有號比較合併成一個無號比較，這是第 8 章技巧的實際應用。
4. 失敗時，`negl` 把 −errno 變成正的 errno，存進 `my_errno`。注意 `%fs:(%rcx)`：`my_errno` 宣告為 `__thread`（thread-local），每個 thread 一份，靠 `%fs` 暫存器找到目前 thread 的那一份。真正的 `errno` 也是這樣實作的，所以兩個 thread 的錯誤碼不會互相覆蓋。
5. 最後回傳 −1，這就是 C 程式看到的「失敗回傳 −1、原因在 `errno`」慣例的由來。

### 一次 system call 的完整路徑

```text
 user mode                                   │ kernel mode
 ───────────────────────────────────────────  │ ───────────────────────────────────
 thumbd: n = read(fd, buf, 4096);             │
   └▶ call read@PLT（第 19 章）               │
       └▶ libc 的 read wrapper                │
            %rax = 0, %rdi = fd,              │
            %rsi = buf, %rdx = 4096           │
            syscall ─────────────────────────┼─▶ ① 切到 kernel mode、kernel stack
                                              │   ② 依 %rax 查 system call table
                                              │   ③ 執行 ksys_read：檢查 fd、權限
                                              │      資料在 page cache？
                                              │       ├ 是：複製到 buf
                                              │       └ 否：發出磁碟 I/O，
                                              │          這個 process 進入睡眠，
                                              │          切到別的 process（20.8 節）
                                              │   ④ 回傳值放進 %rax
            ◀────────────────── sysretq ──────┼── ⑤ 切回 user mode
            %rax < 0 ? 設 errno, 回傳 -1      │
       ◀── 回傳讀到的 bytes 數                │
```

這張圖說明了為什麼 system call 比一般函式呼叫貴很多：除了 `syscall` 指令本身的模式切換，kernel 還要保存暫存器、檢查參數（kernel 不能信任 user 程式給的指標）、執行實際工作；在有 Spectre／Meltdown 防護（第 13、23 章）的系統上，進出 kernel 時還要做額外的處理。20.11 節會實際量測：在本機上，一次最簡單的 system call 比一次一般函式呼叫慢了將近 100 倍。

### 有些「系統呼叫」其實不進 kernel

讀取目前時間是極為頻繁的操作（log、計時、逾時判斷），如果每次都要進 kernel，代價太高。Linux 用 **vDSO**（virtual dynamic shared object）解決：kernel 在每個 process 的位址空間裡映射一小段程式碼與一頁唯讀資料，裡面有 kernel 持續更新的時間資訊。glibc 的 `clock_gettime`、`gettimeofday` 會直接呼叫 vDSO 裡的函式，在 user mode 讀取時間，完全不用 `syscall`。在 `/proc/PID/maps` 裡看到的 `[vdso]` 就是它。macOS 也有類似機制（commpage）。20.11 節的量測會看到 `clock_gettime` 比 `getppid` 快得多。

## 20.6 Process：每個程式都以為自己獨占電腦

有了 exception，作業系統就能實作它最重要的抽象：**process**（行程，正在執行的程式的實例）。這是電腦科學中最成功的抽象之一：你寫程式時從來不需要考慮「別的程式也在跑」，因為 process 給了你兩個假象。

**假象一：獨占的 logical control flow。** 每個 process 都覺得 CPU 只執行它的指令，一條接一條，從不中斷。用 gdb 單步執行，你看到的 program counter 序列就是這個 process 的 **logical control flow**（邏輯控制流）。實際上 CPU 在多個 process 之間輪流執行，只是切換得夠快、而且每個 process 的狀態都被完整保存，所以它察覺不到。

**假象二：私有的位址空間。** 每個 process 都有自己的虛擬位址空間（第 23 章），同一個位址在不同 process 裡對應不同的實體記憶體。一個 process 無法讀寫另一個 process 的記憶體，除非雙方刻意建立共享。

下面這段程式用 `fork` 建立一個子行程（`fork` 的細節在第 21 章），子行程修改全域變數，然後父行程讀同一個變數：

```c
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

static int cache_hits = 100;   /* 一個全域變數 */

int main(void) {
    pid_t pid = fork();                 /* fork 的細節在第 21 章 */
    if (pid == 0) {                     /* 子程序 */
        cache_hits = 999;
        printf("子程序 PID %d：&cache_hits=%p，值=%d\n", getpid(), (void *)&cache_hits, cache_hits);
        return 0;
    }
    waitpid(pid, NULL, 0);              /* 等子程序結束，確保它已經改過 */
    printf("父程序 PID %d：&cache_hits=%p，值=%d\n", getpid(), (void *)&cache_hits, cache_hits);
    return 0;
}
```

在 macOS arm64 上的實際輸出：

```text
子程序 PID 95978：&cache_hits=0x1047cc000，值=999
父程序 PID 95945：&cache_hits=0x1047cc000，值=100
```

兩個 process 印出的位址**完全相同**，值卻不同。這就是「私有位址空間」最直接的證據：`0x1047cc000` 是虛擬位址，兩個 process 各自的 page table 把它對應到不同的實體頁（fork 之後透過 copy-on-write 分開，第 24 章）。對只寫過 Python 或 Java 的讀者，這可以解釋一個常見的困惑：用 `multiprocessing` 開的子行程修改全域變數，父行程看不到，因為它們本來就是不同的 process。

### 並行的 flow

兩個 logical flow 在時間上重疊，就叫 **concurrent flow**（並行流程）。注意「並行」不要求同時執行：在單核 CPU 上，A 跑一段、B 跑一段、A 再跑一段，A 與 B 就是並行的。只有在多核上真正同時執行時，才叫 **parallel**（平行），這個區分在第 1、30 章也會用到。

```text
 時間 ──────────────────────────────────────────────────────▶
 
 單核 CPU：
   process A  ████████          ██████              ████
   process B          ██████          ████████
   process C                                  ████      ████
              A 與 B 並行（時間範圍重疊），但從未同時執行
              每個 █ 段落稱為一個 time slice（時間片）
 
 雙核 CPU：
   核心 0     A ████████████████████████████████
   核心 1     B ██████████      C ██████████████
              A 與 B 平行（同時執行）
```

每一段連續執行的時間叫 **time slice**（時間片）。切換的時機由 kernel 決定，對程式來說是無法預測的，這就是為什麼第 31 章的 race condition 會「偶爾才發生」：某次切換剛好落在兩個操作之間。

## 20.7 User mode 與 kernel mode

如果任何程式都能執行任何指令，process 的假象馬上就會破功：程式可以改 page table 讀別人的記憶體、關掉計時器 interrupt 霸佔 CPU、直接操作磁碟繞過檔案權限。所以處理器提供一個**模式位元**（mode bit），區分兩種執行模式：

| 面向 | user mode（使用者模式） | kernel mode（也叫 supervisor mode） |
|---|---|---|
| 誰在這個模式執行 | 你的程式、libc 等 library | 作業系統 kernel |
| 特權指令 | 不能執行（例如修改 `CR3`、關閉 interrupt、`hlt`、直接 I/O），執行就觸發 #GP | 可以 |
| 能存取的記憶體 | 只有 PTE 標記為 user 的頁（第 23 章） | 全部 |
| 怎麼進入 | 開機後 kernel 用特殊指令切換進來 | **只能透過 exception**：interrupt、trap（system call）、fault |
| x86-64 的叫法 | ring 3 | ring 0 |

關鍵在最後一列：user 程式**沒有任何方法**直接把自己變成 kernel mode。唯一的入口是 exception，而 exception 會強制跳到 exception table 裡 kernel 預先設定好的 handler。程式可以選擇「發哪一個 system call、給什麼參數」，但不能選擇「跳到 kernel 的哪個位置」，這就是作業系統能保護自己的根本原因。

這兩種模式直接反映在你每天看到的數字上。`time` 指令印出的三個時間：

```text
示意輸出（Linux）
$ time ./thumbd-bench photo.jpg
real    0m0.412s
user    0m0.095s
sys     0m0.301s
```

| 欄位 | 意義 | 偏高時代表 |
|---|---|---|
| `real` | 牆上時鐘的經過時間 | 包含等待 I/O、等待 CPU 的時間 |
| `user` | CPU 在 user mode 執行這個程式的時間 | 程式本身的計算多（解碼、縮放） |
| `sys` | CPU 在 kernel mode **替這個程式**工作的時間 | system call 太多或太貴、page fault 多 |

本章故事裡，讀檔改成一次 1 byte 之後，`sys` 遠大於 `user`：CPU 大部分時間在 kernel 裡處理數百萬次 `read`，真正解碼圖片的時間反而是小部分。`top` 的 `us`／`sy`、`/proc/PID/stat` 的 `utime`／`stime`、`perf` 的 `:u`／`:k` 修飾都是同一個區分。

> [!warning] 常見誤解
> 「kernel 是一個在背景一直執行的 process」。kernel 大部分時候不是一個獨立的 process，而是「在某個 process 的上下文中，以 kernel mode 執行的程式碼」：`thumbd` 呼叫 `read`，執行 `read` 邏輯的就是 `thumbd` 這個 process，只是切到了 kernel mode，所以那段時間記在 `thumbd` 的 `sys` 上。Linux 確實也有一些 kernel thread（`ps` 裡用方括號顯示的那些，例如 `[kworker/0:1]`），但 system call 不是交給它們處理的。

## 20.8 Context switch：kernel 如何在 process 之間切換

kernel 用 **context switch**（上下文切換）實作多個 process 輪流執行。每個 process 的 **context**（上下文）是 kernel 重新啟動它所需要的全部狀態：

```text
 一個 process 的 context
 ┌────────────────────────────────────────────────┐
 │ CPU 狀態：通用暫存器、%rip、%rsp、flags、       │
 │          浮點／SIMD 暫存器                      │ ← 切換時存入 kernel 的資料結構
 ├────────────────────────────────────────────────┤
 │ 位址空間：page table 的起點（CR3）              │ ← 換掉它 = 換掉整個虛擬記憶體
 ├────────────────────────────────────────────────┤
 │ kernel 狀態：kernel stack、開啟的檔案表、        │
 │            signal 設定、行程資訊（PID、使用者）  │
 └────────────────────────────────────────────────┘
```

決定「接下來讓誰跑」的 kernel 元件叫 **scheduler**（排程器）。一次 context switch 做三件事：保存目前 process 的 context、載入下一個 process 之前保存的 context、把控制權交給它。

context switch 只會在 kernel 拿到控制權時發生，也就是某個 exception 之後。常見的兩種時機：

1. **process 主動等待**：system call 需要等某件事（磁碟、網路、`sleep`、等 lock），kernel 把它標記為睡眠，切換到別的 process。這叫 **voluntary context switch**（自願切換）。
2. **時間片用完**：計時器 interrupt 觸發，kernel 發現目前的 process 已經跑夠久、有別的 process 在等，就強制切換。這叫 **involuntary context switch**（非自願切換），也叫 preemption（搶占）。

用 `thumbd` 讀一張不在 page cache 的圖片為例：

```text
 時間 ─────────────────────────────────────────────────────────────▶
 
 thumbd     user ██│kernel ▓▓│                          │▓▓ kernel│██ user
                   │ read()  │                          │ 複製資料 │ read 返回
                   │ 發出磁碟 │                          │         │
                   │ 請求    │                          │         │
                   │ 進入睡眠 ┊ context switch           ┊ context switch
                             ▼                          ▲
 nginx                       │▓▓│████ user ████│▓▓│     │
                             (載入 nginx 的 context)    │
 磁碟                         ……… 讀取中（數十 µs～數 ms）………▶ 完成
                                                interrupt ┘
                                    kernel 喚醒 thumbd，等下次排程
```

thumbd 在 `read` 裡進入睡眠，CPU 沒有閒著，而是去執行 nginx；磁碟完成後發出 interrupt，kernel 把 thumbd 標記為可執行，下次排程時再切回來。從 thumbd 的角度，它只是覺得「`read` 花了比較久」。

context switch 的直接成本（保存與載入暫存器、切換 page table、執行 scheduler）通常在微秒量級，但**間接成本**常常更大：新的 process 的資料不在 cache 與 TLB 裡（第 16、23 章），要重新暖身。這就是為什麼 thread 開得太多、互相搶 CPU 時，效能會不升反降（第 32 章）。

在 Linux 上，可以看到每個 process 的兩種切換次數：

```bash
grep ctxt_switches /proc/$(pidof thumbd)/status
pidstat -w -p $(pidof thumbd) 1        # 每秒的 cswch/s（自願）與 nvcswch/s（非自願）
```

| 現象 | 可能原因 | 下一步 |
|---|---|---|
| 自願切換很多 | 大量阻塞式 I/O、lock 競爭、`sleep` | 用 `strace -T` 看哪些呼叫在等；看 lock 競爭（第 31 章） |
| 非自願切換很多 | CPU 不夠用，可執行的 thread 比核心多 | 看 load average、CPU 使用率；減少 thread 數或增加 CPU |
| 兩者都少，但延遲高 | 時間花在 user mode 計算，或在等不會造成切換的東西 | 用 `perf` 做 profiling（第 14 章） |

## 20.9 系統呼叫的錯誤處理

system call 會失敗：檔案不存在、權限不足、磁碟滿了、被 signal 打斷、資源用完。Unix 的傳統慣例是：**失敗時回傳 −1（指標型別則回傳 NULL 或 `MAP_FAILED`），並把原因寫進全域變數 `errno`**。`errno` 是一個整數，`<errno.h>` 為每個值定義了名字，`strerror(errno)` 把它轉成人看得懂的字串。

| errno 名稱 | Linux 數值 | 意思 | `thumbd` 可能遇到的情境 |
|---|---|---|---|
| `ENOENT` | 2 | 檔案或目錄不存在 | 原圖已被刪除 |
| `EINTR` | 4 | 被 signal 打斷 | 在 `read` 等待時收到 `SIGHUP`（第 22 章） |
| `EBADF` | 9 | 不合法的 file descriptor | 用了已經 `close` 的 fd |
| `EAGAIN` | 11 | 暫時無法完成，稍後再試 | non-blocking socket 沒有資料（第 30 章） |
| `ENOMEM` | 12 | 記憶體不足 | `mmap` 大圖失敗 |
| `EACCES` | 13 | 權限不足 | 本章故事中權限設錯的檔案 |
| `EMFILE` | 24 | 這個 process 開的檔案太多 | fd leak（第 27 章） |

數值是 Linux 的；其他系統大致相同但不保證，例如 macOS 的 `EAGAIN` 是 35。程式裡永遠用名字比較，不要寫死數字。

### 使用 errno 的三條規則

**規則一：只有在回傳值表示失敗時才看 `errno`。** 成功的呼叫**不會**把 `errno` 清成 0，它可能還留著很久以前某次失敗的值（20.11 節的程式會證明這一點）。所以 `if (errno != 0)` 這種判斷是錯的。

**規則二：失敗後立刻把 `errno` 存起來。** 任何其他函式呼叫都可能改變 `errno`，包括 `printf`。本章故事的第二個謎團就是這樣來的：

```c
// not-runnable
int fd = open(path, O_RDONLY);
if (fd < 0) {
    log_line("open %s failed", path);          /* log_line 內部用 stdio 寫檔 */
    log_line("reason: %s", strerror(errno));   /* 這時 errno 已經被改掉了 */
}
```

第一個 `log_line` 內部做了好幾次 system call 與 library 呼叫，其中任何一個失敗都會留下新的 `errno`。`thumbd` 這次遇到的是：log 函式第一次輸出時，stdio 會檢查目的地是不是終端機，好決定要不要用行緩衝。檢查用的是 `isatty`，它對不是終端機的 fd 會失敗並留下 `errno = ENOTTY`（什麼情況下會做這個檢查依 C library 的實作與版本而定，例如目前的 glibc 只對字元裝置檢查，較舊的版本與其他實作則不一定），於是第二行印出「Inappropriate ioctl for device」，原本的 `EACCES` 已經不見了。修法是在 `open` 失敗後**第一件事**就 `int saved = errno;`，之後只用 `saved`。

**規則三：處理 `EINTR`。** 會阻塞的 system call（`read`、`write`、`accept`、`waitpid` 等）在等待期間如果收到 signal 並執行了 handler，可能提早返回 −1 且 `errno == EINTR`。這不是真正的錯誤，通常應該重試。第 22 章會說明如何用 `SA_RESTART` 讓 kernel 自動重試大部分的情況。

### 三種錯誤回報風格

並不是所有系統相關的函式都用 −1 加 `errno`。CS:APP 把它們整理成三種風格，混用時很容易寫錯：

| 風格 | 代表函式 | 失敗時 | 怎麼取得原因 |
|---|---|---|---|
| Unix 風格 | `open`、`read`、`fork`、`waitpid` | 回傳 −1 | `errno`，用 `strerror(errno)` |
| Posix threads 風格 | `pthread_create`、`pthread_mutex_lock` | 回傳非 0 的錯誤碼 | **回傳值本身**就是錯誤碼；不保證設定 `errno` |
| GAI 風格 | `getaddrinfo`、`getnameinfo` | 回傳非 0 的 `EAI_*` 值 | `gai_strerror(回傳值)`（第 28 章） |

### Wrapper：讓錯誤處理不被忘記

每一個 system call 後面都寫一段 `if (… < 0) { … }` 很繁瑣，所以 CS:APP 的範例程式為每個 system call 寫一個首字大寫的 wrapper，例如 `Fork`、`Open`：呼叫原函式，失敗就印出錯誤並結束程式。這讓教學程式短而且不會漏掉檢查。

但在 `thumbd` 這種長時間執行的 server 裡，**一個請求的錯誤不應該讓整個服務結束**。打不開一張圖，應該對那個請求回 404 或 500，而不是 `exit(1)`。所以工作上的 wrapper 通常是「記錄完整情境，然後把錯誤往上回傳」：

```c
// not-runnable
static int open_photo(const char *path) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        int saved = errno;                                  /* 規則二 */
        log_error("open(%s) failed: %s", path, strerror(saved));
        errno = saved;                                      /* 讓呼叫端也能判斷原因 */
        return -1;
    }
    return fd;
}
```

## 20.10 strace：看程式到底請 kernel 做了什麼

既然 process 和外界的所有互動（檔案、網路、記憶體、建立 process）都必須經過 system call，那麼只要記錄下所有的 system call，就能看見程式「對外做了什麼」，而且不需要原始碼。`strace` 就是做這件事的 Linux 工具：它利用 kernel 的 `ptrace` 機制，讓目標 process 每次進出 system call 時都先停下來通知 `strace`。

常用的幾種用法：

| 指令 | 用途 |
|---|---|
| `strace ./thumbd` | 從頭追蹤，印出每一個 system call、參數與回傳值 |
| `strace -p PID` | 附加到正在執行的 process |
| `strace -f` | 同時追蹤子行程與 thread（`thumbd` 有 thread pool，幾乎一定要加） |
| `strace -c` | 不逐筆印，最後輸出統計表：每種呼叫的次數、錯誤數、時間 |
| `strace -e trace=openat,read` | 只看指定的呼叫；也可以用類別，例如 `trace=%file`、`trace=%network`（不加 `%` 的舊寫法 `file`、`network` 也還能用） |
| `strace -T` | 每筆後面附上這次呼叫花了多少時間 |
| `strace -tt` | 每筆前面加上時間戳記（微秒） |
| `strace -o out.txt` | 輸出到檔案，避免和程式本身的輸出混在一起 |

故事中老周看到的統計表大致如下（Linux 專屬工具，示意輸出）：

```text
示意輸出（strace -c -f -p <thumbd>，約 5 秒）
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 93.61    4.102913           1   3145801           read
  3.02    0.132554          41      3200           write
  1.88    0.082611          51      1600       200 openat
  0.85    0.037345          26      1400           close
  0.63    0.027586          19      1400           newfstatat
------ ----------- ----------- --------- --------- ----------------
100.00    4.383009                3153401       200 total
```

逐筆模式看到的則是一長串一模一樣的呼叫：

```text
示意輸出（strace -f -e trace=openat,read -p <thumbd>）
[pid 41233] openat(AT_FDCWD, "/data/photos/7f/3a91.jpg", O_RDONLY|O_CLOEXEC) = 17
[pid 41233] read(17, "\377", 1)          = 1
[pid 41233] read(17, "\330", 1)          = 1
[pid 41233] read(17, "\377", 1)          = 1
[pid 41233] read(17, "\340", 1)          = 1
...
[pid 41234] openat(AT_FDCWD, "/data/photos/02/b7c4.jpg", O_RDONLY|O_CLOEXEC) = -1 EACCES (Permission denied)
```

這兩段輸出同時解開了故事的兩個謎團：每次 `read` 只要 1 byte（`\377\330` 正是 JPEG 檔開頭的 `0xFF 0xD8`，第 3 章），以及失敗的 `openat` 真正的原因是 `EACCES`，不是 log 裡寫的 ENOTTY。`strace` 直接顯示 kernel 回傳的錯誤碼，不受程式自己 log 寫錯的影響，所以它常常是「程式 log 說 A，實際上是 B」這類問題的仲裁者。

### 用手算估計影響

`strace -c` 的時間欄本身會被 `strace` 的額外負擔放大，不適合當作真實成本。比較可靠的估法是用「次數 × 單次成本」：

```text
一張 3 MB 的 JPEG = 3 × 1,048,576 = 3,145,728 bytes
一次讀 1 byte  → 3,145,728 次 read
一次 system call 約 80 ns（20.11 節在本機量到的數量級）
→ 3,145,728 × 80 ns ≈ 0.25 秒，只花在進出 kernel

改成一次讀 64 KiB = 65,536 bytes
→ 3,145,728 ÷ 65,536 = 48 次 read
→ 48 × 80 ns ≈ 4 µs（資料複製的成本兩者相同，這裡只比較呼叫次數）
```

次數差了 65,536 倍。修法很簡單：恢復使用有緩衝的讀取（`fread`，或自己用一個 64 KiB 的緩衝區一次讀一大塊，再從緩衝區逐 byte 解析，第 27 章的 RIO 套件就是這樣設計的）。這就是 stdio 存在的理由：它把大量小讀寫合併成少量的 system call。

> [!warning] 常見誤解
> 「`strace` 很輕量，可以一直開在 production 上」。`ptrace` 會讓目標 process 在每次 system call 進出時都停下來、切換到 `strace` process，再切回來，等於每個 system call 多了好幾次 context switch。對 system call 密集的程式，可能慢上數倍甚至更多。在 production 上短時間、針對性地使用（`-e trace=` 限縮範圍），或改用額外負擔低得多的 `perf trace` 與 eBPF 工具（例如 bpftrace）。macOS 上對應的工具是 `dtruss`，但在預設的 SIP 設定下無法追蹤大部分程式。

## 20.11 動手做：量測 system call 的代價、errno 與 context switch

### 程式一：一次 system call 有多貴

這段程式分別執行一百萬次一般函式呼叫、`getppid()`（一個幾乎不做事的 system call，因此量到的主要是進出 kernel 的成本），以及 `clock_gettime()`：

```c
#include <stdio.h>
#include <time.h>
#include <unistd.h>

/* noinline：避免編譯器把函式呼叫整個最佳化掉 */
__attribute__((noinline)) static int plain_function(int x) {
    __asm__ volatile("" ::: "memory");   /* 阻止編譯器合併迴圈 */
    return x + 1;
}

static double now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

int main(void) {
    const int n = 1000000;
    volatile long sink = 0;

    double t0 = now_ns();
    for (int i = 0; i < n; i++) sink += plain_function(i);
    double t1 = now_ns();
    for (int i = 0; i < n; i++) sink += getppid();   /* 每次都進 kernel */
    double t2 = now_ns();
    for (int i = 0; i < n; i++) {                    /* 量測 clock_gettime 本身 */
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC, &ts);
        sink += ts.tv_nsec;
    }
    double t3 = now_ns();

    printf("一般函式呼叫     ：%6.1f ns/次\n", (t1 - t0) / n);
    printf("getppid() 系統呼叫：%6.1f ns/次\n", (t2 - t1) / n);
    printf("clock_gettime()  ：%6.1f ns/次\n", (t3 - t2) / n);
    return 0;
}
```

在 macOS arm64（Apple Silicon、Apple clang 21、`-O1`）上連續執行兩次的實際輸出：

```text
一般函式呼叫     ：   0.8 ns/次
getppid() 系統呼叫：  75.3 ns/次
clock_gettime()  ：  17.3 ns/次
一般函式呼叫     ：   0.8 ns/次
getppid() 系統呼叫：  88.6 ns/次
clock_gettime()  ：  17.3 ns/次
```

逐步解說：

1. **一般函式呼叫約 0.8 ns**，也就是幾個 CPU cycle：`call`、幾條指令、`ret`，全部在 user mode、資料都在 L1 cache。
2. **`getppid()` 約 75–90 ns，大約是函式呼叫的 100 倍。** `getppid` 在 kernel 裡幾乎不做事，所以這個時間幾乎全是 20.5 節那張圖的固定成本：模式切換、保存與恢復暫存器、system call 分派。兩次執行的差異反映了量測雜訊。在 Linux x86-64 伺服器上，數字會隨 CPU 型號與 Spectre／Meltdown 防護設定而變，通常是數十到數百 ns 的量級。
3. **`clock_gettime()` 約 17 ns**，明顯比 `getppid` 快。它沒有進 kernel，而是讀取 kernel 共享出來的時間資料（macOS 的 commpage，Linux 上是 20.5 節的 vDSO）。它比一般函式呼叫慢，是因為要讀取時間計數器並做換算。
4. 對照 20.1 節：一次 system call 的固定成本約 80 ns，看起來很小，但乘上三百萬就是四分之一秒。**system call 的問題通常不是單次太慢，而是次數太多。**

### 程式二：errno 的行為與 context switch 次數

```c
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <unistd.h>

/* thumbd 風格的 wrapper：失敗時把「哪個呼叫、哪個參數、什麼錯」一起印出 */
static int Open(const char *path, int flags) {
    int fd = open(path, flags);
    if (fd < 0)
        fprintf(stderr, "open(\"%s\") 失敗：errno=%d (%s)\n", path, errno, strerror(errno));
    return fd;
}

static void show_switches(const char *label) {
    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    printf("%s：自願 %ld 次，非自願 %ld 次\n", label, ru.ru_nvcsw, ru.ru_nivcsw);
}

int main(void) {
    /* 1. 失敗的系統呼叫回傳 -1，原因放在 errno */
    Open("/no/such/photo.jpg", O_RDONLY);
    char buf[16];
    if (read(999, buf, sizeof buf) < 0)
        printf("read(999) 失敗：errno=%d (%s)\n", errno, strerror(errno));

    /* 2. 成功的呼叫不會把 errno 清成 0：只能在回傳值表示失敗時才讀 errno */
    int fd = Open("/dev/null", O_RDONLY);
    printf("open(/dev/null) 成功 fd=%d，但 errno 仍是 %d\n", fd, errno);
    close(fd);

    /* 3. 每次 sleep 都主動讓出 CPU，kernel 會做一次 context switch */
    show_switches("開始時");
    for (int i = 0; i < 50; i++) usleep(1000);
    show_switches("usleep 50 次之後");
    return 0;
}
```

在 macOS arm64 上的實際輸出（第一行來自 stderr）：

```text
open("/no/such/photo.jpg") 失敗：errno=2 (No such file or directory)
read(999) 失敗：errno=9 (Bad file descriptor)
open(/dev/null) 成功 fd=3，但 errno 仍是 9
開始時：自願 0 次，非自願 17 次
usleep 50 次之後：自願 0 次，非自願 67 次
```

逐步解說：

1. 打不開的檔案得到 `ENOENT`（2），不存在的 fd 999 得到 `EBADF`（9），和 20.9 節的表一致。
2. 第三行是規則一的證據：`open("/dev/null")` 成功了，`errno` 卻還是上一次失敗留下的 9。如果程式用「`errno` 不是 0」來判斷失敗，就會誤判。
3. 新開的 fd 是 3，因為 0、1、2 已經是標準輸入、輸出、錯誤（第 27 章），kernel 總是分配最小的可用編號。
4. 50 次 `usleep` 讓切換次數增加了 50 次，每次睡眠都讓出 CPU（機器忙碌時會再多幾次真正被搶占的切換）。但在 macOS 上，這些切換被算在「非自願」欄，「自願」欄一直是 0：從輸出可以推斷，macOS 的 kernel 統計這兩個欄位的方式和 Linux 不同。在 Linux 上執行同一段程式，增加的 50 次會出現在 `ru_nvcsw`（自願）。這提醒我們：**同一個欄位名稱，在不同系統上的統計方式可能不同**，判讀前要先確認平台的定義。

```text
示意輸出（Linux x86-64 上執行程式二的最後兩行，數字會因環境而異）
開始時：自願 1 次，非自願 0 次
usleep 50 次之後：自願 51 次，非自願 0 次
```

## 20.12 在工作上怎麼用

### 情境一：`sys` 時間偏高的診斷流程

```text
 症狀：top 上 sy 很高，或某個 process 的 sys time 遠大於 user time
   │
   ├─ 1. 是哪個 process？ top 按 P；pidstat -u 1 看 %system 欄
   │
   ├─ 2. 它在做哪種 system call？ strace -c -f -p PID（幾秒就停）
   │      ├─ 某個呼叫次數極高（read/write 每次很少 bytes）→ 加緩衝、批次處理
   │      ├─ futex 很多 → lock 競爭（第 31 章）
   │      ├─ mmap/munmap/brk 很多 → allocator 反覆向 kernel 要還記憶體（第 25 章）
   │      └─ 次數不多但 -T 顯示每次很久 → 不是次數問題，看 I/O 或 kernel 內部
   │
   ├─ 3. 不是 system call？ 看 page fault：ps -o min_flt,maj_flt -p PID（第 23 章）
   │
   └─ 4. 需要更細？ perf top 或 perf record -g，看 kernel 符號裡時間花在哪
```

### 情境二：減少 system call 次數的常見手法

| 手法 | 做法 | 適用情境 |
|---|---|---|
| 使用緩衝 | 用 stdio 或自己的緩衝區，一次讀寫一大塊 | 逐 byte、逐行處理檔案或 socket（本章故事） |
| 合併多個緩衝區 | `writev`／`readv` 一次送出多段資料 | HTTP 回應的 header 與 body 分開存放時 |
| 讓 kernel 直接搬資料 | `sendfile`、`copy_file_range` | 靜態檔案直接送到 socket，不經 user 空間 |
| 一次等多個事件 | `epoll_wait` 一次回傳多個就緒的 fd（第 30 章） | 大量連線的 server |
| 批次提交 | Linux 的 `io_uring` 透過共享的環狀佇列提交與收取 I/O，可以大幅減少 system call | 高效能儲存與網路服務 |
| 避免不必要的呼叫 | 快取 `getpid`、`stat` 的結果；用 vDSO 版本的時間函式 | 熱路徑上重複查詢不會變的資訊 |

### 情境三：用 `strace` 回答「它到底在幹嘛」

`strace` 最有價值的時候，常常不是效能分析，而是理解一個你沒有原始碼、或原始碼太大的程式：

```bash
strace -f -e trace=%file ./thumbd 2>&1 | grep -v ENOENT | head              # 讀了哪些設定檔
strace -f -e trace=openat ./thumbd 2>&1 | grep '\.so'                        # 載入了哪些 library（第 19 章）
strace -f -e trace=%network -p PID                                           # 連到哪裡、卡在哪個 connect
strace -T -e trace=read,write,poll -p PID                                    # 哪個呼叫在等、等多久
strace -f -e trace=%process ./start.sh                                       # fork、execve 了哪些程式（第 21 章）
```

一個 process 卡住不動時，`strace -p PID` 的第一行通常就是答案：如果停在 `read(5, ` 沒有回傳，表示它在等 fd 5 的資料；再用 `ls -l /proc/PID/fd/5` 或 `ss -p`（第 28 章）查出 fd 5 是哪個檔案或連線。

### 情境四：錯誤 log 的檢查清單

`thumbd` 團隊在故事之後，把下面幾項加進 code review 的檢查清單：

- system call 失敗後的第一行就保存 `errno`，log 裡同時印出 `strerror` 的文字與錯誤碼名稱。
- log 內容包含「哪個呼叫、主要參數（路徑、fd、大小）、錯誤」，例如 `open(/data/photos/02/b7c4.jpg) failed: Permission denied`。
- pthread 系列函式用回傳值判斷錯誤，不讀 `errno`；`getaddrinfo` 用 `gai_strerror`。
- 會阻塞的呼叫處理 `EINTR`；`EAGAIN` 在 non-blocking I/O 中是正常情況，不記成錯誤。
- server 的 wrapper 不在單一請求的錯誤上 `exit`，而是把錯誤回傳給呼叫端。

## 20.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| `sys` 時間很高、吞吐量低 | 大量小型 system call（未緩衝的 `read`／`write`） | `strace -c` 看呼叫次數；逐筆看每次的 byte 數 | 加緩衝、`writev`、批次處理 |
| 錯誤 log 的原因和實際不符（例如出現 `Inappropriate ioctl for device`） | 讀 `errno` 之前呼叫了其他函式，`errno` 被覆蓋 | 用 `strace` 看 kernel 實際回傳的錯誤 | 失敗後立刻保存 `errno` |
| 程式用 `errno != 0` 判斷失敗，偶爾誤報 | 成功的呼叫不會清除 `errno` | 印出回傳值與 `errno` 對照 | 只依回傳值判斷是否失敗 |
| `read`／`accept` 偶爾回傳 −1，`errno` 是 `EINTR` | 等待期間收到 signal | 確認程式有安裝 signal handler（第 22 章） | 重試，或用 `SA_RESTART` |
| 多執行緒程式的 pthread 錯誤訊息是「Success」 | pthread 函式不設定 `errno`，卻用 `strerror(errno)` 印 | 看程式碼是否讀 `errno` | 用 `strerror(回傳值)` |
| 程式收到 `SIGFPE` 結束 | 整數除以零（或 `INT_MIN / -1`）觸發 divide error | core dump 的 `bt` 停在 `idiv` 指令 | 除法前檢查除數；注意 ARM64 上不會 trap |
| 程式收到 `SIGILL` | 執行了 CPU 不支援的指令（例如編譯時用了 `-march=native`，部署到較舊的 CPU） | gdb 看當機指令；比較兩台機器的 `/proc/cpuinfo` flags | 用目標 CPU 支援的 `-march` 編譯 |
| 加了 `strace` 之後問題消失或程式變很慢 | `strace` 改變了時序，且額外負擔大 | 比較有無 `strace` 的行為 | 改用 `perf trace`、eBPF，或縮小追蹤範圍 |

## 20.14 動手練習

1. **手算**：`thumbd` 每處理一張圖會做 6 次 `openat` 與 6 次 `close`、對 2 MB 的原圖用 4 KiB 的緩衝區讀取、對 100 KB 的縮圖一次 `write`。總共大約多少次 system call？若每次固定成本 100 ns，佔一張圖 20 ms 處理時間的比例是多少？（答案：讀取 2,097,152 ÷ 4,096 = 512 次，加上約 6 ＋ 6 ＋ 1 次，約 525 次；525 × 100 ns ≈ 52.5 µs，約 0.26%。驗證方法：把數字代入程式一的量測結果重算。）
2. **手算**：一個 system call 回傳 `%rax = 0xfffffffffffffff3`。把它當作有號數是多少？對應哪個 errno？（答案：−13，`EACCES`，權限不足。）
3. 修改 20.11 節程式一，加入第四個迴圈：每次 `read` 一個 byte 從 `/dev/zero` 讀取（先 `open` 一次）。比較它和 `getppid` 的單次成本，並解釋差異來自哪裡。
4. 擴充 20.11 節程式二，加入一個「忙碌迴圈」（例如做 2 秒的浮點運算）同時在另一個終端機執行多個相同程式讓 CPU 滿載，觀察非自願切換次數的變化。如果你有 Linux 環境，比較 `/proc/self/status` 裡 `voluntary_ctxt_switches` 與 `nonvoluntary_ctxt_switches` 的值。
5. 在 Linux 上對 `ls`、`python3 -c 'pass'`、`curl -s https://example.com -o /dev/null` 各執行一次 `strace -c`，比較它們的 system call 總數與最常見的呼叫。哪一個最多？從呼叫的種類推測它們各自在做什麼。
6. 寫一個程式故意執行 `int x = 0; printf("%d\n", 1 / x);`（記得用 `volatile` 防止編譯器最佳化），分別在 x86-64 Linux 與 ARM64（例如 Apple Silicon）上執行，記錄結果是否相同，並用本章的 exception 分類解釋。

## 本章重點整理

- exceptional control flow 是控制流程因系統事件而突然轉向的統稱，存在於硬體（exception）、作業系統（context switch）、process（signal）與應用程式（nonlocal jump）各個層次。
- exception 是硬體偵測到事件後，依 exception 編號查 exception table，切換到 kernel mode 並跳到 kernel 的 handler；它和函式呼叫的差別在返回位址、推進的狀態、使用的 stack 與權限。
- exception 分四類：interrupt 由外部裝置非同步觸發、回到下一條指令；trap 由程式刻意觸發（system call）、回到下一條；fault 可能修復後重做目前指令；abort 無法修復、不返回。
- 計時器 interrupt 讓 kernel 定期拿回控制權，是多工與搶占的基礎。
- Linux x86-64 的 system call 用 `%rax` 放編號、`%rdi`、`%rsi`、`%rdx`、`%r10`、`%r8`、`%r9` 放參數，`syscall` 指令進入 kernel，失敗時回傳 −errno，由 libc wrapper 轉成 −1 加 `errno`。
- 一次 system call 的固定成本約為一般函式呼叫的數十到上百倍；效能問題通常來自呼叫次數太多，而不是單次太慢。vDSO 讓讀取時間這類操作不必進 kernel。
- process 提供兩個假象：獨占 CPU 的 logical control flow，以及私有的位址空間；同一個虛擬位址在不同 process 裡對應不同的資料。
- 時間上重疊的 flow 是並行（concurrent），真正同時執行才是平行（parallel）；切換時機由 kernel 決定，對程式而言無法預測。
- user mode 不能執行特權指令、不能存取 kernel 記憶體，唯一進入 kernel mode 的方式是 exception；`time` 的 `user` 與 `sys` 就是兩種模式的 CPU 時間。
- context switch 保存並載入暫存器、page table 起點與 kernel 狀態；process 等待 I/O 時發生自願切換，時間片用完時發生非自願切換，間接成本是 cache 與 TLB 需要重新暖身。
- 只在回傳值表示失敗時才讀 `errno`，失敗後立刻保存它，並正確處理 `EINTR`；pthread 與 `getaddrinfo` 用不同的錯誤回報風格。
- server 的錯誤處理 wrapper 應該記錄完整情境並回傳錯誤，而不是在單一請求失敗時結束整個程式。
- `strace` 透過 `ptrace` 記錄每一個 system call，能看到程式對外做的每件事與 kernel 實際回傳的錯誤，但額外負擔大，production 上要限縮範圍或改用 `perf trace`、eBPF。

## 延伸問答

> [!question]- Q1. page fault 和 system call 都會進入 kernel，為什麼一個叫 fault、一個叫 trap？
> 分類的依據是「事件是不是程式刻意造成的」以及「處理完回到哪裡」。system call 是程式**故意**執行 `syscall` 指令請求服務，kernel 做完後回到**下一條指令**繼續執行，這是 trap 的定義。
>
> page fault 則是程式只是想存取記憶體，並沒有打算進 kernel，是硬體在指令執行到一半時發現翻譯失敗。kernel 補好頁之後，要**重新執行**那條沒做完的指令，否則那次讀寫就遺失了；如果無法修復，就不返回而是送 signal。這種「可能修復、修好就重做」的性質就是 fault。兩者都是同步的，因為重跑同樣的程式，它們會在同一條指令再次發生。

> [!question]- Q2. 手算題：Linux x86-64 上，程式執行 `syscall` 前 `%rax = 1`、`%rdi = 1`、`%rsi` 指向字串 `"hi\n"`、`%rdx = 3`。這是什麼呼叫？如果返回時 `%rax = 3`、或 `%rax = -9`，各代表什麼？
> `%rax = 1` 是 `write`，參數依序是 fd = 1（標準輸出）、緩衝區位址、長度 3，所以等同 C 的 `write(1, "hi\n", 3)`，會在終端機印出 `hi`。
>
> 返回 3 表示成功寫入 3 個 bytes。返回 −9 落在 −4095 到 −1 之間，表示失敗，錯誤碼是 9，也就是 `EBADF`：fd 1 不是一個有效、可寫的 file descriptor（例如程式之前把標準輸出關掉了）。libc 的 wrapper 會把它轉成「回傳 −1、`errno = EBADF`」。也要記得 `write` 成功時可能回傳小於 3 的值（short count，第 27 章），所以真實程式要檢查回傳值是否等於要求的長度。

> [!question]- Q3. 為什麼 user 程式不能自己切換到 kernel mode，例如直接改那個模式位元？
> 因為切換模式的能力本身就是特權。如果 user 程式能直接設定模式位元，它就能在 kernel mode 執行任意程式碼：修改自己的 page table 讀取別人的記憶體、關閉計時器 interrupt 霸佔 CPU、直接操作磁碟繞過檔案權限。作業系統提供的所有隔離與保護都會失效。
>
> 所以處理器只提供一種進入 kernel mode 的方式：exception。而 exception 的目的地由 kernel 在開機時設定的 exception table 決定，user 程式只能選擇「觸發哪一種 exception、system call 帶什麼參數」，不能選擇「跳到 kernel 的哪一行」。kernel 再逐一檢查 system call 的參數（例如指標是否真的指向 user 空間），才替程式做事。這個設計讓 kernel 的入口數量有限而且受控。

> [!question]- Q4. 你在 production 看到 `thumbd` 的 `nvcswch/s`（非自願切換）突然暴增，延遲同時上升，`cswch/s` 沒什麼變化。你會怎麼判斷？
> 非自願切換代表 thread 還想繼續跑，卻因為時間片用完被 kernel 搶走 CPU，通常表示**可執行的 thread 比可用的 CPU 核心多**。自願切換沒變，表示 I/O 等待模式沒有改變，問題比較不像是磁碟或網路變慢。
>
> 接著要確認 CPU 為什麼不夠：用 `uptime` 或 `vmstat 1` 看 load average 與 `r` 欄（等待 CPU 的 thread 數）是否高於核心數；用 `top` 看是不是同一台機器上有別的 process 突然吃滿 CPU（例如備份或另一個服務）；在容器環境還要看是否碰到 CPU quota 限制（cgroup throttling）。如果是 `thumbd` 自己的 thread 太多，就減少 thread pool 大小，讓 thread 數接近核心數（第 30、32 章）。

> [!question]- Q5. 程式找錯：`if (pthread_mutex_lock(&m) != 0) { perror("lock"); }` 這段有什麼問題？
> `pthread_mutex_lock` 屬於 Posix threads 風格：失敗時直接**回傳**錯誤碼，不保證會設定 `errno`。`perror` 印出的是 `errno` 目前的值，可能是 0（印出 `Success`）或某個毫不相關的舊錯誤，完全誤導除錯。
>
> 正確寫法是保存回傳值：`int rc = pthread_mutex_lock(&m); if (rc != 0) fprintf(stderr, "lock: %s\n", strerror(rc));`。同樣的問題也會出現在 `getaddrinfo`，它要用 `gai_strerror(rc)`。這就是為什麼 20.9 節要把三種錯誤回報風格分開記：寫錯處理邏輯不會讓程式當機，卻會讓錯誤訊息在你最需要它的時候說謊。

> [!question]- Q6. 為什麼 `clock_gettime` 可以不進 kernel 就拿到時間，`getpid` 卻通常要進 kernel？
> 時間資訊是 kernel 持續更新、所有 process 都可以看的公開資料，而且讀取極為頻繁。Linux 透過 vDSO 把一頁唯讀的時間資料與讀取它的程式碼映射進每個 process，`clock_gettime` 在 user mode 讀取這頁資料，再配合 CPU 的時間計數器換算出目前時間，完全不需要模式切換。
>
> `getpid` 的值雖然也不常變，但它屬於「這個 process 自己的」kernel 狀態，而且呼叫頻率很低，沒有必要特別做 vDSO 版本。glibc 從 2.3.4 到 2.24 曾在 user 空間快取 PID，但只要程式繞過 glibc 的 `fork`／`clone` wrapper（例如直接用 `syscall(2)`），子行程就會拿到父行程的 PID，所以 glibc 2.25 起移除了這個快取，每次 `getpid` 都真的進 kernel。重點是：一個操作能不能避開 kernel，取決於它需要的資料能否安全地共享給 user 空間唯讀存取。

> [!question]- Q7. 面試題：context switch 的成本包含哪些？為什麼開更多 thread 不一定更快？
> 直接成本是 kernel 執行切換本身：進入 kernel、執行 scheduler 決定下一個執行者、保存目前 thread 的暫存器（包括可能很大的 SIMD 暫存器）、載入下一個的暫存器，若跨 process 還要切換 page table（`CR3`）。這部分通常在微秒量級。
>
> 間接成本往往更大：新執行的 thread 所需的資料與指令不在 L1／L2 cache 裡，跨 process 時 TLB 中的翻譯也可能失效（PCID 可以減輕），要經過一段時間的 cache miss 才能恢復速度。當 thread 數遠多於 CPU 核心數時，大量時間花在切換與重新暖身 cache，真正做事的時間反而減少，還會增加 lock 競爭。所以 CPU 密集的工作，thread 數通常設定在核心數附近；I/O 密集的工作才需要更多 thread 或改用事件驅動模型（第 30 章）。

> [!question]- Q8. `strace` 顯示 `thumbd` 停在 `read(12, ` 很久沒有回傳。這代表什麼？下一步怎麼查？
> 這表示 `thumbd` 的某個 thread 正阻塞在一次 `read` system call 裡：kernel 已經把它放進睡眠狀態，在等 fd 12 有資料可讀。此時它不使用 CPU，也不是當機，而是在等外部事件，所以 `top` 上看不到 CPU 使用率。
>
> 下一步是找出 fd 12 是什麼：`ls -l /proc/PID/fd/12` 會顯示它指向的檔案或 `socket:[inode]`；如果是 socket，用 `ss -tnp` 找到對應的連線，看對方是誰、接收佇列是否有資料（第 28 章）。常見原因是對方（例如上游的儲存服務）沒有回應，而程式沒有設定逾時。修法是對 socket 設定逾時（`SO_RCVTIMEO`），或改用 `poll`／`epoll` 搭配逾時（第 30 章），讓程式不會無限期等待。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 8 章 8.1–8.3 節，exception 分類與 process 抽象的原始敘述。
- [Linux man pages](https://man7.org/linux/man-pages/)：`syscall(2)`（各架構的 system call 呼叫約定）、`syscalls(2)`、`errno(3)`、`vdso(7)`、`getrusage(2)`、`strace(1)`、`proc(5)` 中 `/proc/PID/status` 的說明。
- [Intel 64 and IA-32 Architectures Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)：第 3 卷關於 interrupt 與 exception 處理、IDT 與 `SYSCALL`／`SYSRET` 指令的完整規格。
- [x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI)：附錄中 Linux kernel 介面的呼叫約定（`%r10` 取代 `%rcx` 的由來）。
- [POSIX 規格（The Open Group）](https://pubs.opengroup.org/onlinepubs/9799919799/)：`errno` 的定義與各函式的錯誤回報規則。
