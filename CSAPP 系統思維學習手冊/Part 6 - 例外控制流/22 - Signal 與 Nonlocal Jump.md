---
chapter: 22
title: Signal 與 Nonlocal Jump
part: 6
---

# 第 22 章　Signal 與 Nonlocal Jump

> [!abstract] 本章地圖
> **核心問題**：kernel 和其他 process 要怎麼「打斷」一個正在執行的程式、通知它某件事發生了？程式又要怎麼安全地回應這種隨時可能到來的打斷？
>
> **你會學到**：
> - 說出常見 signal 的意義與預設動作，知道 `Ctrl-C`、`kill`、`SIGSEGV` 各自從哪裡來
> - 用 pending 與 blocked 兩個位元向量解釋 signal 何時被遞送，以及為什麼 signal 不排隊
> - 用 `sigaction` 寫出正確的 handler，遵守 async-signal-safe、`errno`、`volatile sig_atomic_t` 等守則
> - 用 `sigprocmask` 消除「handler 比主程式先跑」的 race，用 `sigsuspend` 正確地等待 signal
> - 用 `setjmp`／`longjmp` 從深層呼叫直接跳回，並知道它的代價與陷阱
> - 在工作上為服務實作 `SIGHUP` 重新載入與 `SIGTERM` 優雅關閉，並診斷容器裡「關不掉」的服務
>
> **前置知識**：第 20 章（exception、kernel mode 與 context switch）、第 21 章（fork、waitpid 與 zombie）
>
> **對應 CS:APP 3e**：第 8 章 8.5–8.6 節

## 22.1 故事：凌晨三點的 SIGHUP

上一章修好 zombie 之後，`thumbd` 平靜了一陣子。某天早上，阿哲發現監控圖上每天凌晨 3:00 整，`thumbd` 都會重啟一次，伴隨幾十個 502 錯誤。log 的最後一行只是正常的請求紀錄，沒有任何錯誤訊息，也沒有 core dump。

追了半天，阿哲找到元兇：凌晨 3:00 是 `logrotate` 輪替 log 的時間。設定檔裡有一行 `postrotate kill -HUP $(cat /run/thumbd.pid)`，原意是「通知 `thumbd` 重新打開 log 檔」。問題是 `thumbd` 從來沒有處理過 `SIGHUP`，而 `SIGHUP` 的**預設動作是終止 process**。`thumbd` 等於每天凌晨被自己的維運腳本殺死一次，systemd 再把它重新啟動。

同一週，平台組開始用 Kubernetes 做滾動部署。每次部署，舊的 pod 都要等滿 30 秒才消失，部署時間拖得很長；而且在那 30 秒裡，送到舊 pod 的請求有一部分會失敗。更早之前，有人試過在 signal handler 裡直接 `fclose` 再 `fopen` log 檔來「重新載入」，結果 `thumbd` 偶爾會整個卡住，用 `gdb` 附加上去，看到所有 thread 都停在 `malloc` 的鎖上。

小安問老周：「signal 到底是什麼？為什麼一個簡單的通知會殺死程式、讓部署變慢，甚至讓程式卡死？」老周說：「signal 是 Unix 最古老的通知機制，簡單到幾乎沒有任何保證。它會在任何時刻打斷你的程式，而大部分你習慣呼叫的函式，都沒有準備好被這樣打斷。」這一章就要把這句話拆開來講清楚，最後幫 `thumbd` 實作正確的 `SIGHUP` 重新載入與 `SIGTERM` 優雅關閉。

## 22.2 Signal 是什麼

第 20 章介紹的 exception 是硬體與 kernel 之間的機制：使用者程式通常看不到它，例如 page fault 被 kernel 默默處理掉。**signal**（信號）則是把「某件事發生了」這個通知**往上送到使用者程式**的機制。它是一個很小的訊息：只有一個整數編號，沒有其他資料，代表某一類事件。

signal 的來源大致有三種：

- **kernel 偵測到硬體 exception**：程式除以零，CPU 觸發 divide error，kernel 把它轉成 `SIGFPE` 送給該 process；存取不合法的位址，kernel 送 `SIGSEGV`。
- **kernel 偵測到軟體事件**：子行程結束時，kernel 送 `SIGCHLD` 給父行程；寫入一個對方已經關閉的 pipe 或 socket，送 `SIGPIPE`；`alarm` 設定的計時器到期，送 `SIGALRM`。
- **其他 process（或自己）主動送**：`kill` 指令、`kill()` 函式、在終端機按 `Ctrl-C`。

每種 signal 都有一個**預設動作**（default action），也就是 process 沒有特別設定時 kernel 會怎麼做。常見的 signal 如下表；注意編號在 Linux 與 macOS 上不完全相同，程式裡永遠用名稱（`SIGTERM`）而不是數字。

| 名稱 | Linux 編號 | macOS 編號 | 預設動作 | 典型來源 |
|---|---|---|---|---|
| `SIGHUP` | 1 | 1 | 終止 | 終端機斷線；慣例上用來要求 daemon 重新載入設定 |
| `SIGINT` | 2 | 2 | 終止 | 在終端機按 `Ctrl-C` |
| `SIGQUIT` | 3 | 3 | 終止並產生 core dump | 在終端機按 `Ctrl-\` |
| `SIGABRT` | 6 | 6 | 終止並產生 core dump | `abort()`、`assert` 失敗 |
| `SIGFPE` | 8 | 8 | 終止並產生 core dump | 整數除以零 |
| `SIGKILL` | 9 | 9 | 終止（**無法攔截、無法忽略**） | `kill -9`、OOM killer |
| `SIGSEGV` | 11 | 11 | 終止並產生 core dump | 存取不合法的記憶體（第 23 章） |
| `SIGPIPE` | 13 | 13 | 終止 | 寫入讀取端已關閉的 pipe 或 socket |
| `SIGALRM` | 14 | 14 | 終止 | `alarm()` 計時器到期 |
| `SIGTERM` | 15 | 15 | 終止 | `kill` 指令的預設 signal；systemd、Kubernetes 要求程式結束 |
| `SIGUSR1` | 10 | 30 | 終止 | 留給應用程式自訂用途 |
| `SIGCHLD` | 17 | 20 | 忽略 | 子行程結束或暫停 |
| `SIGCONT` | 18 | 19 | 繼續執行（若已暫停） | `fg`、`bg`、`kill -CONT` |
| `SIGSTOP` | 19 | 17 | 暫停（**無法攔截、無法忽略**） | `kill -STOP`、除錯器 |
| `SIGTSTP` | 20 | 18 | 暫停 | 在終端機按 `Ctrl-Z` |

表裡有兩個特例：`SIGKILL` 與 `SIGSTOP` 不能被攔截、忽略或阻擋。這是作業系統給管理者的最後手段：不管程式寫得多糟，總有辦法讓它停下來。代價是被 `SIGKILL` 殺掉的程式完全沒有清理的機會，暫存檔不會刪、緩衝區不會寫出、正在處理的請求直接斷掉。

故事裡 `thumbd` 每天凌晨被殺，就是第一列的預設動作在作怪。要改變它，程式必須告訴 kernel「收到 `SIGHUP` 時不要終止我，改呼叫這個函式」，這就是 22.5 節的 signal handler。

## 22.3 送出 signal：kill、鍵盤與 process group

### 用 kill 送 signal

`kill` 這個名字有點誤導：它的功能是「送出任意 signal」，只是預設送的 `SIGTERM` 會終止程式。

```c
#include <signal.h>
int kill(pid_t pid, int sig);   /* 成功回傳 0，失敗回傳 -1 */
```

`pid` 的解讀和 `waitpid` 類似：大於 0 是送給那一個 process；小於 −1 是送給 process group `-pid` 裡的每一個 process；`0` 是送給自己所在的 process group。還有一個實用的技巧：`sig` 為 0 時不會真的送出任何 signal，只做權限與存在檢查，所以 `kill(pid, 0) == 0` 可以用來判斷「這個 PID 還活著嗎？」（注意 PID 可能已被別的 process 重用）。對應的指令是 `kill -TERM 1234`、`kill -HUP 1234`、`kill -- -5678`（送給整個 process group）。

權限上，一般使用者只能送 signal 給同一個使用者的 process，root 可以送給任何 process。

### Process group 與終端機

**process group**（行程群組）是一組 process 的集合，用一個 **PGID**（process group ID）識別，通常等於群組裡第一個 process（group leader）的 PID。它存在的目的是讓 shell 可以把「一個工作」當成一個單位來管理：`cat log | grep error | sort` 這條 pipeline 有三個 process，對使用者來說卻是一個工作，按 `Ctrl-C` 應該三個一起停。

```c
pid_t getpgrp(void);                  /* 我所在的 process group */
int setpgid(pid_t pid, pid_t pgid);   /* 把 pid 移到 pgid；兩者為 0 表示「自己」與「用自己的 PID 開新群組」 */
```

子行程預設和父行程在同一個 process group。shell 為每個工作開一個新的 process group，並告訴終端機「現在哪一個 group 是**前景**（foreground）」。當你按下 `Ctrl-C`，終端機驅動程式並不是把 `SIGINT` 送給 shell，而是送給**前景 process group 的每一個成員**：

```text
 終端機（tty）              前景 process group = 5678
 ┌──────────┐  Ctrl-C       ┌──────────────────────────────────┐
 │ 使用者按鍵 │ ── SIGINT ──▶ │ cat (5678)  grep (5679) sort (5680)│  三個都收到
 └──────────┘               └──────────────────────────────────┘
       │
       │                    process group 1200（shell 自己）
       └──── 不會送到 ─────▶ bash (1200)                         shell 不受影響
                            背景 process group 6000
                            sleep 1000 & (6000)                   背景工作也不受影響
```

這就是為什麼 `Ctrl-C` 能停掉正在跑的指令，卻不會把 shell 本身關掉；`Ctrl-Z` 送出的 `SIGTSTP` 也是同樣的規則。22.11 節講 Shell Lab 時會再回到這個設計。

### 其他送出方式

`raise(sig)` 送給自己，等同於 `kill(getpid(), sig)`。`alarm(secs)` 讓 kernel 在 secs 秒後送 `SIGALRM` 給自己，每個 process 同時只有一個 alarm，新的會取代舊的。`abort()` 送 `SIGABRT` 給自己，用來在偵測到不可能的狀態時留下 core dump。

## 22.4 接收 signal：pending、blocked 與遞送時機

signal 從「被送出」到「被處理」分成兩步。**送出**（send）是 kernel 在目標 process 的資料結構裡記下「有一個 signal k 要給你」；**接收**（receive）是目標 process 真的對它做出反應：執行預設動作、忽略，或執行 handler。兩步之間的 signal 叫做 **pending signal**（待處理信號）。

kernel 為每個 process（精確地說是每個 thread，22.13 節會提到）維護兩個位元向量，每個 bit 對應一種 signal：

- **pending**：哪些 signal 已經送到、還沒被接收。送出 signal k 時把第 k 位設為 1；接收之後清為 0。
- **blocked**（也叫 **signal mask**）：哪些 signal 目前被阻擋。被阻擋的 signal 可以被送達、在 pending 裡留著，但不會被接收，直到解除阻擋。

```text
 送出 SIGCHLD                     kernel 準備從 kernel mode 回到這個 process 時：
      │                           pending & ~blocked  = 可以遞送的集合
      ▼                                   │
 pending  : 0 0 1 0 1 0 ...      ┌────────┴─────────────┐
 blocked  : 0 0 1 0 0 0 ...      │ 集合為空 → 照常回到程式  │
            │     │   │          │ 不為空 → 挑一個 signal  │
           SIGINT │  SIGTERM     │   清掉它的 pending 位元  │
               SIGCHLD           │   執行預設動作、忽略，    │
                                 │   或跳到 handler        │
 SIGCHLD 被阻擋：留在 pending      └────────────────────────┘
 SIGTERM 沒被阻擋：下次回到 user mode 時遞送
```

**遞送的時機**是關鍵：kernel 只在 process 從 kernel mode 返回 user mode 的時候檢查 `pending & ~blocked`。這種返回發生得非常頻繁：每次 system call 結束、每次 interrupt 處理完（包括 timer interrupt）、每次 context switch 回到這個 process。所以從程式的角度看，signal 可以在**任何兩條指令之間**到來，你無法預測它會打斷哪一行程式碼。這正是 signal 難寫的根源。

### 手算：讀懂 `/proc/PID/status` 的 signal 欄位

Linux 把這些位元向量直接顯示在 `/proc/<PID>/status`，用 64-bit 十六進位表示，第 k 號 signal 對應第 k − 1 個 bit：

```text
SigPnd: 0000000000000000     ← 這個 thread 的 pending
ShdPnd: 0000000000000000     ← 整個 process 共享的 pending
SigBlk: 0000000000010000     ← blocked
SigIgn: 0000000000001000     ← 被設為忽略
SigCgt: 0000000000004003     ← 有安裝 handler（caught）
```

（示意輸出，數值為說明用。）逐一解讀：

| 欄位 | 十六進位 | 為 1 的 bit | signal 編號（bit + 1） | 意義 |
|---|---|---|---|---|
| `SigBlk` | `0x10000` | 16 | 17 | `SIGCHLD` 被阻擋 |
| `SigIgn` | `0x1000` | 12 | 13 | `SIGPIPE` 被忽略 |
| `SigCgt` | `0x4003` | 0、1、14 | 1、2、15 | `SIGHUP`、`SIGINT`、`SIGTERM` 有 handler |

以 `0x4003` 為例：`0x4003 = 0x4000 + 0x2 + 0x1`，`0x4000` 是 2^14，所以 bit 14 為 1，對應 signal 15；`0x2` 是 bit 1，對應 signal 2；`0x1` 是 bit 0，對應 signal 1。這個手算在工作上非常實用：當你懷疑「服務到底有沒有處理 `SIGTERM`」，看 `SigCgt` 的 bit 14 就知道，不必讀原始碼。

### 阻擋 signal：sigprocmask

程式可以用 `sigprocmask` 修改自己的 blocked 向量：

```c
int sigprocmask(int how, const sigset_t *set, sigset_t *oldset);
/* how：SIG_BLOCK（加入 set）、SIG_UNBLOCK（移除 set）、SIG_SETMASK（整個換成 set）
   oldset 不為 NULL 時，存下修改前的 mask，方便之後還原 */

sigset_t s;
sigemptyset(&s);          /* 清空集合 */
sigaddset(&s, SIGCHLD);   /* 加入一個 signal；另有 sigfillset、sigdelset、sigismember */
```

阻擋不等於忽略：被阻擋的 signal 會留在 pending，解除阻擋後**立刻**被遞送；被忽略的 signal 則直接丟掉。阻擋是「晚一點再處理」，22.8 節會看到它是消除 race condition 的主要工具。

### Signal 不排隊

pending 是一個**位元**，不是計數器。如果 signal k 已經 pending，再送一次 k 不會有任何效果，第二個 signal 就這樣消失了。換句話說：**同一種 signal 在 pending 狀態下最多只記一次**。22.7 節與動手做會看到，這個規則讓「一個 `SIGCHLD` 對應一個結束的子行程」的直覺完全錯誤。

POSIX 另外定義了 **real-time signal**（`SIGRTMIN` 到 `SIGRTMAX`，Linux 上有 30 多個），它們會排隊並且能附帶一個整數資料（用 `sigqueue` 送出），但一般系統程式很少使用，常見的 signal 都不排隊。

## 22.5 Signal handler：用 sigaction 改變反應方式

process 可以為每種 signal（`SIGKILL`、`SIGSTOP` 除外）選擇三種反應之一：恢復預設動作（`SIG_DFL`）、忽略（`SIG_IGN`），或指定一個函式，也就是 **signal handler**（信號處理函式）。設定的方式是 `sigaction`：

```c
#include <signal.h>
struct sigaction sa;
memset(&sa, 0, sizeof sa);
sa.sa_handler = on_hup;          /* handler：void on_hup(int sig) */
sigemptyset(&sa.sa_mask);        /* handler 執行期間「額外」要阻擋的 signal */
sa.sa_flags = SA_RESTART;        /* 被打斷的 system call 盡量自動重來 */
sigaction(SIGHUP, &sa, NULL);    /* 第三個參數可取回舊的設定 */
```

C 標準還有一個比較簡單的 `signal(sig, handler)`，但它在不同系統上的語意曾經不一致（舊的 System V 會在 handler 執行一次後自動恢復成預設動作），所以正式程式應該一律用 `sigaction`。

### handler 怎麼被執行

當 kernel 決定遞送一個有 handler 的 signal，它會在 user stack 上替程式「偽造」一次函式呼叫：保存被打斷時的暫存器，讓程式跳到 handler；handler `return` 之後，經過一個特殊的 `sigreturn` system call，kernel 還原暫存器，程式從被打斷的地方繼續，就像什麼都沒發生。

```text
 主程式                          handler
 ──────                          ───────
 指令 I_curr  ◀── 被 signal 打斷
     │
     │ kernel 保存暫存器，跳到 handler
     └──────────────────────────▶ on_hup(SIGHUP)
                                    want_reload = 1;
                                    return;
     ┌──────────────────────────── sigreturn：還原暫存器
     ▼
 指令 I_next  ← 繼續執行，程式「不知道」中間被打斷過
```

handler 執行期間，kernel 會自動阻擋**同一種** signal（所以 `SIGHUP` handler 不會被另一個 `SIGHUP` 打斷），以及 `sa_mask` 裡列出的其他 signal。但沒有列出的其他 signal 仍然可以打斷 handler，handler 本身也可能被另一個 handler 打斷。

### 被打斷的 system call 與 EINTR

如果 signal 到來時，程式正卡在一個會長時間等待的 system call 裡（`read` 一個沒有資料的 socket、`waitpid`、`accept`），kernel 會中斷那個 system call 去執行 handler。handler 返回後有兩種可能：如果設了 `SA_RESTART`，kernel 對大多數 system call 會自動重新執行；如果沒設，system call 回傳 −1，`errno` 為 **`EINTR`**（interrupted system call）。即使設了 `SA_RESTART`，部分 system call（例如 Linux 上的 `poll`、`select`、`epoll_wait` 與 `nanosleep`）仍然會回傳 `EINTR`，詳細清單見 `signal(7)`。

所以可攜的程式在呼叫可能阻塞的 system call 時，都要準備好處理 `EINTR`：通常是檢查有沒有該處理的旗標，然後重試。第 21 章的 `sleep` 被打斷時回傳剩餘秒數，也是同一個現象。

## 22.6 寫出安全的 handler

handler 和主程式**同時**存取同一份資料，而且 handler 可以在主程式的任何兩條指令之間插進來。這和第 31 章的多執行緒 race 很像，但更麻煩：主程式不能用 mutex 保護資料，因為如果主程式拿著鎖時被打斷，handler 再去拿同一把鎖，就會永遠等下去，那把鎖要等 handler 返回後主程式才能釋放，而 handler 永遠不會返回。這是一個 process 自己跟自己 deadlock。

### 為什麼 handler 裡不能呼叫 printf 和 malloc

故事裡 `thumbd` 卡死就是這個情況。`fopen` 內部會 `malloc` 一塊 `FILE` 結構，`malloc` 內部要拿 allocator 的鎖。時間軸是這樣的：

```text
 時間 ─────────────────────────────────────────────────────▶
 主程式： malloc() ── 拿到 allocator 鎖 ── 修改 free list 到一半
                                           ▲
                                     SIGHUP 到達
 handler：                                  fopen() → malloc() → 等 allocator 鎖
                                                                    │
                                     鎖在主程式手上，主程式要等 handler 返回
                                                                    ▼
                                                             永遠卡住（deadlock）
```

即使沒有鎖，問題也一樣：主程式修改 free list 修到一半，資料結構處於不一致的狀態；handler 這時去讀它，會看到壞掉的指標。能在這種情況下被安全呼叫的函式，叫做 **async-signal-safe**（非同步信號安全）函式：它們要嘛是 **reentrant**（可重入：不使用全域或靜態資料，任何時候被打斷再重新呼叫都正確），要嘛在執行期間不會被 signal 打斷。POSIX 明確列出了這份清單，大部分是直接對應 system call 的函式：

| 可以在 handler 裡呼叫（節錄） | 不可以在 handler 裡呼叫（常見陷阱） |
|---|---|
| `write`、`read`、`open`、`close` | `printf`、`fprintf`、`puts`（stdio 有內部 buffer 與鎖） |
| `_exit` | `exit`（會執行 `atexit` 與 flush stdio） |
| `waitpid`、`kill`、`getpid` | `malloc`、`free`、`calloc`，以及任何內部會配置記憶體的函式 |
| `sigprocmask`、`sigaction`、`sigsuspend` | `pthread_mutex_lock` 等鎖的操作 |
| `execve`、`dup2`、`alarm`、`sleep` | `syslog`、大部分第三方 logging library |
| `siglongjmp`、`longjmp`（有條件，見 22.10 節） | `strtok`、`localtime` 等使用靜態 buffer 的函式 |

完整清單在 `signal-safety(7)` 與 POSIX 標準裡。一個容易記的經驗法則是：**系統呼叫的薄包裝大多安全，C 函式庫裡比較「聰明」的函式大多不安全**。如果真的要在 handler 裡輸出訊息（例如除錯時），只能用 `write(STDERR_FILENO, msg, len)`，自己把數字轉成字串。

### 五條守則

綜合上面的原因，寫 handler 時遵守下面這些守則，就能避開絕大多數問題：

1. **handler 越簡單越好**。最好的 handler 只做一件事：設一個旗標，然後返回。真正的工作（重新載入設定、關閉連線）留給主程式在安全的地方做。
2. **只呼叫 async-signal-safe 的函式**。不確定時就不要呼叫。
3. **保存並還原 `errno`**。handler 裡呼叫的 `waitpid`、`write` 失敗時會改寫 `errno`；如果主程式剛好在「呼叫 system call」與「檢查 `errno`」之間被打斷，就會讀到 handler 留下的錯誤碼。handler 開頭存起來、結尾還原。
4. **存取和主程式共享的資料結構時，暫時阻擋所有 signal**。例如 handler 和主程式都會修改一張工作表，主程式在修改時要先 `sigprocmask` 擋住相關 signal，改完再還原，handler 裡也一樣。
5. **共享的旗標宣告為 `volatile sig_atomic_t`**。`sig_atomic_t` 是一個整數型別，C 標準保證對它的單次讀或寫不會被 signal 打斷到一半；`volatile` 則告訴編譯器「這個變數可能在你看不見的地方被改變，每次都要真的去記憶體讀」。

第 5 條的 `volatile` 為什麼必要？用一個等待旗標的迴圈來看編譯器做了什麼：

```c
typedef int sig_atomic_t;   /* glibc 在 x86-64 上的定義；交叉編譯時沒有系統標頭 */
sig_atomic_t plain_flag;
volatile sig_atomic_t safe_flag;
void wait_plain(void) { while (!plain_flag) { } }
void wait_safe(void)  { while (!safe_flag)  { } }
```

用 `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - flag.c` 產生的組合語言（刪去無關的 directive）：

```asm
wait_plain:
	cmpl	$0, plain_flag(%rip)
	je	.LBB0_1
	retq
.LBB0_1:
	jmp	.LBB0_1

wait_safe:
.LBB1_1:
	cmpl	$0, safe_flag(%rip)
	je	.LBB1_1
	retq
```

`wait_plain` 只讀了**一次** `plain_flag`：如果是 0，就跳進 `.LBB0_1` 這個「跳到自己」的無窮迴圈，之後再也不看記憶體。編譯器這麼做是合法的，因為從它的角度，迴圈裡沒有任何程式碼會改變 `plain_flag`，讀一次就夠了。handler 把旗標設成 1 也沒用，程式永遠出不來。`wait_safe` 則在每次迴圈都重新 `cmpl` 記憶體裡的 `safe_flag`，handler 一設定，下一輪就看得到。（實務上也不應該用忙碌迴圈等 signal，22.9 節會介紹 `sigsuspend`。）

> [!warning] 常見誤解
> 「`volatile` 讓變數變成 thread-safe。」不是。`volatile` 只保證編譯器不把讀寫最佳化掉，不提供多執行緒之間的 atomicity 或記憶體順序保證。它對 signal handler 足夠，是因為 handler 和主程式在同一條 thread 上交錯執行；多執行緒之間的共享變數要用 C11 的 `_Atomic` 或鎖（第 31、32 章）。

## 22.7 Signal 不排隊：正確地回收子行程

第 21 章的迷你 shell 只在顯示提示字元時回收背景工作，延遲很大。改進的方法是安裝 `SIGCHLD` handler：子行程一結束，kernel 就送 `SIGCHLD`，handler 裡呼叫 `waitpid` 回收。最直覺的寫法是「一個 signal 回收一個子行程」：

```c
static void on_chld(int sig) {      /* 錯誤示範 */
    (void)sig;
    waitpid(-1, NULL, 0);           /* 收到一次 SIGCHLD，回收一個 */
}
```

這個 handler 在子行程一個一個慢慢結束時看起來沒問題，但只要有幾個子行程**幾乎同時**結束，就會漏掉。原因正是 signal 不排隊：

```text
 時間 ──────────────────────────────────────────────────────────▶
 子程序 A 結束 → SIGCHLD pending
 子程序 B 結束 → SIGCHLD 已經 pending，這次被丟掉
 子程序 C 結束 →              （handler 執行中，SIGCHLD 被自動阻擋）
                 handler 開始：pending 清為 0  → waitpid 回收 A → 返回
                               C 的 SIGCHLD 在 handler 執行時送達 → pending
                 handler 再執行一次：waitpid 回收 B → 返回
 結果：A、B 被回收，C 永遠是 zombie（它的 signal 已經被「用掉」了）
```

在這個時間軸中，三個子行程結束，handler 只執行兩次，而且每次只回收一個，C 留了下來。實際上 handler 執行幾次取決於時機，可能是一次、兩次或三次，所以這個 bug 時有時無、很難重現。

正確的觀念是：**一個 `SIGCHLD` 的意思是「至少有一個子行程狀態改變了」，而不是「剛好有一個」**。所以 handler 必須用迴圈，把所有已經結束的子行程都回收完，並用 `WNOHANG` 避免在還有子行程活著時卡住：

```c
static void on_chld(int sig) {
    (void)sig;
    int saved_errno = errno;                        /* 守則 3 */
    while (waitpid(-1, NULL, WNOHANG) > 0)          /* 回收所有已結束的，沒有就立刻返回 */
        ;
    errno = saved_errno;
}
```

這個「signal 只代表『有事發生』，handler 要自己去查發生了多少」的模式，在其他通知機制裡也到處可見：epoll 的 edge-triggered 模式要一直讀到 `EAGAIN`（第 30 章），condition variable 被喚醒後要重新檢查條件（第 31 章），都是同一個道理。

## 22.8 Race：handler 比主程式先跑

加了 `SIGCHLD` handler 之後，`thumbd` 的外部工具管理變成這樣：主程式 fork 一個工具，把 PID 加進「執行中的工具表」，以便追蹤逾時；handler 在工具結束時把它從表中移除。看起來很合理，但有一個隱藏的 race：

```c
/* 有 race 的版本 */
pid_t pid = fork();
if (pid == 0) { execvp(argv[0], argv); _exit(127); }
tool_table_add(pid, deadline);     /* 主程式：加入工具表 */

static void on_chld(int sig) {     /* handler：從工具表移除 */
    pid_t pid;
    while ((pid = waitpid(-1, NULL, WNOHANG)) > 0)
        tool_table_remove(pid);
}
```

問題在於 fork 之後誰先跑是不確定的。如果工具非常快就失敗了（例如找不到檔案），可能發生這個順序：

```text
 主程式                         子程序                 handler
 ──────                         ──────                 ───────
 fork() ───────────────────────▶ execvp 失敗、_exit
 （還沒被排到 CPU）                    │
                                      └─ SIGCHLD ─────▶ tool_table_remove(pid)
                                                         表裡還沒有這個 pid，什麼都沒做
 tool_table_add(pid) ← 加入一個已經死掉、而且已被回收的 PID
 → 工具表裡永遠留著這一筆；逾時檢查之後還會對它 kill，可能殺到 PID 被重用的無辜 process
```

這是 signal 程式設計最經典的 race：**事件的處理（remove）跑到了事件的登記（add）前面**。修法是在 fork **之前**阻擋 `SIGCHLD`，等主程式登記完畢才解除阻擋。這段期間子行程就算結束了，`SIGCHLD` 也只會留在 pending，等解除阻擋後才遞送，那時表裡已經有這一筆：

```c
sigset_t chld, prev;
sigemptyset(&chld);
sigaddset(&chld, SIGCHLD);

sigprocmask(SIG_BLOCK, &chld, &prev);         /* ① 先擋住 SIGCHLD */
pid_t pid = fork();
if (pid == 0) {
    sigprocmask(SIG_SETMASK, &prev, NULL);    /* ② 子程序繼承了 mask，exec 前要還原 */
    execvp(argv[0], argv);
    _exit(127);
}
tool_table_add(pid, deadline);                /* ③ 登記：這時 handler 不可能插進來 */
sigprocmask(SIG_SETMASK, &prev, NULL);        /* ④ 解除阻擋，pending 的 SIGCHLD 現在才遞送 */
```

第 ② 步很容易漏掉：signal mask 會跨過 fork 與 exec 被繼承（第 21 章），如果不還原，外部工具一輩子都收不到 `SIGCHLD`，它自己若也要管理子行程就會出問題。另外依守則 4，handler 裡的 `tool_table_remove` 和主程式的其他工具表操作（例如逾時掃描）也要在阻擋 signal 的情況下進行。

## 22.9 等待 signal：pause 的陷阱與 sigsuspend

有時主程式需要「停下來，直到某個 signal 讓旗標改變」，例如 shell 等待前景工作結束、`thumbd` 的主執行緒等待 `SIGTERM`。最直覺的寫法是：

```c
while (!want_stop)      /* 檢查旗標 */
    pause();            /* 睡到有 signal 為止 */
```

這段程式有一個 **lost wakeup**（遺失喚醒）的 race：如果 signal 剛好在「檢查 `want_stop` 為 0」之後、「呼叫 `pause`」之前到達，handler 會把旗標設成 1，然後 `pause` 才開始睡。這次的 signal 已經用掉了，`pause` 會一直睡到**下一個** signal，可能永遠不會來。

```text
 主程式：  檢查 want_stop == 0 ──────────────────▶ pause()  ……一直睡
                                 ▲
 signal：                     SIGTERM 到達，handler 設 want_stop = 1
                              （主程式已經檢查過了，看不到）
```

把 `pause` 換成 `sleep(1)` 輪詢可以「避開」問題，但會讓反應慢最多 1 秒，又浪費 CPU。正確的解法是 **`sigsuspend`**：

```c
int sigsuspend(const sigset_t *mask);
/* 原子地：把 blocked 暫時換成 mask，並睡到有 signal 被遞送；
   handler 返回後，把 blocked 恢復成呼叫前的值，回傳 -1（errno 為 EINTR） */
```

使用模式是：平常保持 signal 被阻擋，檢查旗標時 handler 不可能插進來；需要睡的時候，呼叫 `sigsuspend`，它在**同一個不可分割的動作**裡解除阻擋並開始睡，中間沒有任何空檔：

```c
sigprocmask(SIG_BLOCK, &term_set, &prev);   /* 平常擋住 SIGTERM */
while (!want_stop)
    sigsuspend(&prev);                      /* 解除阻擋＋睡覺，一步完成 */
sigprocmask(SIG_SETMASK, &prev, NULL);
```

如果 `SIGTERM` 在檢查旗標之前就送到了，它會因為被阻擋而留在 pending；一呼叫 `sigsuspend` 解除阻擋，它立刻被遞送，handler 設旗標，`sigsuspend` 返回，迴圈看到旗標而結束。不管 signal 在哪個時間點到，都不會遺失。22.12 節的 `thumbd` 範例就是這個模式。

## 22.10 Nonlocal jump：setjmp 與 longjmp

到目前為止，控制流的轉移不是函式呼叫與返回，就是 kernel 介入的 exception 與 signal。C 還提供一種**使用者層級**的例外控制流：**nonlocal jump**（非區域跳躍），可以從一個深層的函式直接跳回某個外層函式，跳過中間所有的 return。

```c
#include <setjmp.h>
int  setjmp(jmp_buf env);             /* 存下目前的執行環境；第一次呼叫回傳 0 */
void longjmp(jmp_buf env, int val);   /* 跳回 env 存下的位置，讓那次 setjmp「再回傳一次」，值為 val */
```

`setjmp` 把目前的 stack pointer、program counter 與 callee-saved 暫存器存進 `jmp_buf`。之後在任何更深層的函式裡呼叫 `longjmp(env, val)`，就會還原這些暫存器，程式回到 `setjmp` 返回的那一點，這次回傳 `val`（如果 `val` 是 0，會被改成 1，避免和第一次混淆）。所以 `setjmp` 是另一個「呼叫一次、回傳多次」的函式，而 `longjmp` 是「呼叫了不會回傳」的函式。

```text
 try_parse()  ── setjmp(env) 回傳 0 ──▶ parse_size()
      ▲                                   └─▶ parse_number()
      │                                         └─ 發現錯誤：longjmp(env, 1)
      │                                                │
      └──── setjmp(env)「再回傳一次」，值為 1 ◀──────────┘
            （parse_size、parse_number 的 stack frame 直接被丟棄）
```

這個機制適合用在「深層發現錯誤，要立刻回到最外層處理」的情況，例如解析器、直譯器的錯誤回復。libpng 的錯誤處理，以及 libjpeg 範例程式建議的錯誤處理方式，都是用 `setjmp`／`longjmp` 把解碼錯誤送回呼叫者：`thumbd` 呼叫 `png_read_image` 時，要先 `setjmp(png_jmpbuf(png_ptr))`，否則壞掉的圖檔會讓 library 直接呼叫 `abort`。

### 代價與陷阱

`longjmp` 很強大，也很危險，因為它跳過了中間所有函式的正常結束路徑：

| 陷阱 | 說明 | 怎麼避免 |
|---|---|---|
| 資源洩漏 | 中間函式 `malloc` 的記憶體、打開的檔案、拿到的鎖都沒有被釋放 | 在 `setjmp` 那一層統一記錄與清理資源；不要跨過持有鎖的程式碼跳躍 |
| local 變數的值不確定 | 在 `setjmp` 之後被修改過、又不是 `volatile` 的 local 變數，`longjmp` 回來後的值是不確定的（可能是舊值） | 這類變數宣告為 `volatile` |
| 跳進已經結束的函式 | 呼叫 `setjmp` 的函式已經 return，`jmp_buf` 指向的 stack frame 已失效 | `longjmp` 只能跳到還在 stack 上的函式 |
| signal mask 沒有還原 | 從 handler 裡 `longjmp` 出去時，handler 期間被自動阻擋的 signal 可能一直被阻擋 | 用 `sigsetjmp(env, 1)` 與 `siglongjmp`，它們會一併保存與還原 signal mask |
| 和 C++ 不相容 | 跳過的 C++ 物件不會執行 destructor | C++ 用 exception，不要用 `longjmp` |

`sigsetjmp`／`siglongjmp` 讓 handler 可以「跳回」主程式的某一點，例如讓一個互動式程式在按下 `Ctrl-C` 時回到主選單，或讓一段卡住的計算在 `SIGALRM` 時被中止。但跳出 handler 時，被打斷的那段程式可能正在 `malloc` 裡面，跳走之後 allocator 永遠停在不一致的狀態。所以 POSIX 只在「被打斷的程式碼不是 async-signal-unsafe 函式」時保證這是安全的。實務上，只在被打斷的程式碼是純計算、不呼叫任何 library 的情況下這樣做。

C++ 與 Java 的 `try`／`catch` 可以看成「有紀律的 nonlocal jump」：它們同樣直接跳到外層的處理程式，但會在路上執行每一層的 destructor 或 `finally`，把資源清理乾淨。這正是 `setjmp`／`longjmp` 缺少的那一塊。

## 22.11 從迷你 shell 到 Shell Lab：job control 需要的拼圖

學完 signal，第 21 章的迷你 shell 缺的東西就都有了。CS:APP 的 **Shell Lab** 要你實作一個支援 job control 的 shell（`tsh`），它是把第 21、22 章所有概念組合起來的練習。這裡說明它要求什麼、練的是什麼，但不提供解答。

一個支援 job control 的 shell 需要把這些機制拼在一起：

| 功能 | 需要的機制 | 本書位置 |
|---|---|---|
| 執行前景與背景工作 | fork、execve、waitpid | 第 21 章 |
| 維護工作表（jobs） | 在 `SIGCHLD` handler 與主程式之間共享資料，阻擋 signal 保護它 | 22.6、22.8 節 |
| 子行程結束時立刻回收 | `SIGCHLD` handler 用 `WNOHANG` 迴圈 | 22.7 節 |
| 等待前景工作結束 | 不忙碌等待、不遺失喚醒 | 22.9 節 `sigsuspend` |
| `Ctrl-C` 只停前景工作 | 每個工作有自己的 process group；把 `SIGINT` 轉送給前景 group | 22.3 節 |
| `Ctrl-Z` 暫停、`fg`／`bg` 繼續 | `SIGTSTP`、`SIGCONT`、`WUNTRACED` | 22.2、21.5 節 |
| 不被自己的 signal 打亂 | fork 前阻擋 `SIGCHLD`，子行程 exec 前還原 mask | 22.8 節 |

Shell Lab 有一個簡化的地方值得注意：`tsh` 是在另一個 shell 底下執行的，所以它本身和它的子行程都在原 shell 為它開的前景 process group 裡，按 `Ctrl-C` 時連 `tsh` 自己也會收到 `SIGINT`。因此 lab 要求子行程各自成立新的 process group，`tsh` 收到 `SIGINT` 後再轉送給前景工作的 group。真正的 shell（bash、zsh）則會控制終端機，用 `tcsetpgrp` 直接把前景權交給工作的 process group，讓終端機自己把 signal 送對地方。

做這個 lab 時，真正要練的能力是：

- 對每一個共享的資料結構，說得出「哪些程式碼路徑會碰它、handler 可能在哪裡插進來」。
- 畫出 fork、signal 遞送、handler、主程式之間所有可能的交錯順序，並找出會出錯的那幾種。
- 用阻擋與 `sigsuspend` 讓錯誤的交錯**不可能發生**，而不是用 `sleep` 讓它「比較不容易發生」。
- 用 lab 附的參考 shell 與 trace 檔比對行為，並用 `strace -f` 或在 handler 裡用 `write` 觀察實際的事件順序。

這些能力在工作上直接對應到寫 daemon、supervisor、container runtime 與任何需要處理非同步事件的程式。

## 22.12 動手做：signal 不排隊、process group、優雅關閉與 nonlocal jump

以下程式都在 macOS arm64（Apple clang 21）上以 `cc -std=c17 -O1 -Wall -Wextra` 編譯，輸出導向 pipe 後記錄。

### 程式一：親眼看到 signal 不排隊

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t handled;     /* handler 執行了幾次 */
static volatile sig_atomic_t reaped;      /* handler 回收了幾個子程序 */
static volatile sig_atomic_t loop_mode;   /* 0：只 wait 一次；1：迴圈 wait */

static void on_usr1(int sig) { (void)sig; handled++; }

static void on_chld(int sig) {
    (void)sig;
    int saved = errno;                    /* waitpid 可能改 errno，先存起來 */
    handled++;
    if (loop_mode) {
        while (waitpid(-1, NULL, WNOHANG) > 0) reaped++;
    } else if (waitpid(-1, NULL, WNOHANG) > 0) {
        reaped++;                         /* 錯誤示範：一次 signal 只收一個 */
    }
    errno = saved;
}

static void install(int sig, void (*fn)(int)) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = fn;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    sigaction(sig, &sa, NULL);
}

static void block(int sig, int how) {
    sigset_t set;
    sigemptyset(&set);
    sigaddset(&set, sig);
    sigprocmask(how, &set, NULL);
}

static void chld_round(int mode) {
    handled = reaped = 0;
    loop_mode = mode;
    block(SIGCHLD, SIG_BLOCK);            /* 先擋住，讓三個 SIGCHLD 疊在一起 */
    for (int i = 0; i < 3; i++)
        if (fork() == 0) _exit(0);
    usleep(200 * 1000);                   /* 三個子程序都結束了 */
    block(SIGCHLD, SIG_UNBLOCK);          /* 解除阻擋，pending 的 signal 送達 */
    printf("%s：handler 執行 %d 次，回收 %d 個，", mode ? "迴圈 waitpid" : "只 wait 一次",
           (int)handled, (int)reaped);
    int left = 0;
    while (waitpid(-1, NULL, WNOHANG) > 0) left++;
    printf("留下 %d 個 zombie\n", left);
}

int main(void) {
    install(SIGUSR1, on_usr1);
    block(SIGUSR1, SIG_BLOCK);
    for (int i = 0; i < 5; i++) kill(getpid(), SIGUSR1);
    sigset_t pending;
    sigpending(&pending);
    printf("送了 5 次 SIGUSR1，pending 中有 SIGUSR1？%s\n",
           sigismember(&pending, SIGUSR1) ? "是" : "否");
    block(SIGUSR1, SIG_UNBLOCK);
    printf("解除阻擋後 handler 執行了 %d 次\n", (int)handled);

    install(SIGCHLD, on_chld);
    fflush(stdout);
    chld_round(0);
    fflush(stdout);
    chld_round(1);
    return 0;
}
```

```text
送了 5 次 SIGUSR1，pending 中有 SIGUSR1？是
解除阻擋後 handler 執行了 1 次
只 wait 一次：handler 執行 1 次，回收 1 個，留下 2 個 zombie
迴圈 waitpid：handler 執行 1 次，回收 3 個，留下 0 個 zombie
```

逐步解說：

1. 程式先阻擋 `SIGUSR1`，然後送給自己 5 次。`sigpending` 顯示 `SIGUSR1` 在 pending 裡，但 pending 只是一個 bit，5 次和 1 次無法區分。
2. 解除阻擋後 handler 只執行 **1 次**，另外 4 次 signal 就這樣消失了。`sigprocmask` 保證在它返回之前，至少一個剛解除阻擋的 pending signal 會被遞送，所以下一行 `printf` 看到的計數已經是 1。
3. 第二部分用同樣的手法讓 3 個子行程的 `SIGCHLD` 疊在一起：阻擋 `SIGCHLD`、fork 3 個立刻結束的子行程、等 200 ms、解除阻擋。「只 wait 一次」的 handler 只執行 1 次、回收 1 個，留下 2 個 zombie（最後由主程式清掉）。
4. 「迴圈 waitpid」的 handler 同樣只執行 1 次，但回收了全部 3 個。這就是 22.7 節的結論：handler 執行的次數不可靠，迴圈回收才可靠。

### 程式二：送 signal 給整個 process group

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <signal.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    printf("main：PID %d，process group %d\n", (int)getpid(), (int)getpgrp());
    fflush(stdout);
    pid_t leader = 0;
    for (int i = 0; i < 3; i++) {
        pid_t pid = fork();
        if (pid == 0) {
            setpgid(0, leader);            /* 第一個子程序自成一組，其餘加入它 */
            pause();                       /* 等 signal */
            _exit(0);
        }
        if (leader == 0) leader = pid;
        setpgid(pid, leader);              /* 父程序也設一次，避免 race */
    }
    usleep(100 * 1000);
    printf("三個子程序都在 process group %d\n", (int)getpgid(leader));
    kill(-leader, SIGINT);                 /* 負號：送給整個 process group，像 Ctrl-C */
    int status;
    pid_t pid;
    while ((pid = waitpid(-1, &status, 0)) > 0)
        printf("  PID %d 被 signal %d 終止\n", (int)pid, WTERMSIG(status));
    printf("main 自己不在那個 group，所以沒被影響\n");
    return 0;
}
```

```text
main：PID 94614，process group 94219
三個子程序都在 process group 94616
  PID 94618 被 signal 2 終止
  PID 94616 被 signal 2 終止
  PID 94617 被 signal 2 終止
main 自己不在那個 group，所以沒被影響
```

1. 主程式屬於啟動它的 shell 所建立的 process group（這裡是 94219），PGID 和自己的 PID 不同。
2. 三個子行程被放進同一個新的 process group，以第一個子行程的 PID（94616）為 PGID。父子都呼叫 `setpgid` 是 shell 的標準做法：不管 fork 之後誰先跑，子行程在 exec 之前一定已經在正確的 group 裡。
3. `kill(-leader, SIGINT)` 的負號表示送給整個 group，效果和終端機按 `Ctrl-C` 一樣，三個子行程都被 signal 2 終止，回收順序不固定。主程式不在那個 group，所以沒事。

### 程式三：`thumbd` 的 SIGHUP 重新載入與 SIGTERM 優雅關閉

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t want_reload;
static volatile sig_atomic_t want_stop;

/* handler 只設旗標，真正的工作留給主程式做。 */
static void on_hup(int sig)  { (void)sig; want_reload = 1; }
static void on_term(int sig) { (void)sig; want_stop = 1; }

static void install(int sig, void (*fn)(int)) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = fn;
    sigemptyset(&sa.sa_mask);
    sigaddset(&sa.sa_mask, SIGHUP);       /* 兩個 handler 執行時互相擋住 */
    sigaddset(&sa.sa_mask, SIGTERM);
    sigaction(sig, &sa, NULL);
}

int main(void) {
    sigset_t mask, prev;
    sigemptyset(&mask);
    sigaddset(&mask, SIGHUP);
    sigaddset(&mask, SIGTERM);
    sigprocmask(SIG_BLOCK, &mask, &prev); /* 先擋住，再裝 handler、再檢查旗標 */
    install(SIGHUP, on_hup);
    install(SIGTERM, on_term);

    pid_t parent = getpid();
    fflush(stdout);
    pid_t ops = fork();                   /* 模擬維運：logrotate 送 HUP，部署送 TERM */
    if (ops == 0) {
        sigprocmask(SIG_SETMASK, &prev, NULL);
        int script[] = {SIGHUP, SIGHUP, SIGTERM};
        for (int i = 0; i < 3; i++) { usleep(100 * 1000); kill(parent, script[i]); }
        _exit(0);
    }

    int config_version = 1, in_flight = 3;
    printf("thumbd 啟動：設定版本 %d，處理中請求 %d 個\n", config_version, in_flight);
    for (;;) {
        while (!want_reload && !want_stop)
            sigsuspend(&prev);            /* 原子地「解除阻擋並睡著」，醒來時恢復阻擋 */
        if (want_reload) {
            want_reload = 0;
            config_version++;
            printf("收到 SIGHUP：重新載入設定，現在是版本 %d\n", config_version);
        }
        if (want_stop) {
            printf("收到 SIGTERM：停止接新請求，等待 %d 個處理中的請求\n", in_flight);
            while (in_flight > 0) {
                usleep(20 * 1000);        /* 模擬把手上的請求做完 */
                printf("  完成一個請求，剩 %d 個\n", --in_flight);
            }
            break;
        }
    }
    waitpid(ops, NULL, 0);
    printf("優雅關閉完成，exit 0\n");
    return 0;
}
```

```text
thumbd 啟動：設定版本 1，處理中請求 3 個
收到 SIGHUP：重新載入設定，現在是版本 2
收到 SIGHUP：重新載入設定，現在是版本 3
收到 SIGTERM：停止接新請求，等待 3 個處理中的請求
  完成一個請求，剩 2 個
  完成一個請求，剩 1 個
  完成一個請求，剩 0 個
優雅關閉完成，exit 0
```

這是本章故事的解法縮影，逐步看：

1. 主程式一開始就阻擋 `SIGHUP` 與 `SIGTERM`，**然後**才安裝 handler、建立模擬維運的子行程。這個順序保證：不管 signal 什麼時候到，都會先停在 pending，不會在初始化做到一半時打斷程式。
2. 兩個 handler 都只設旗標（守則 1、5），`sa_mask` 讓它們執行時互相阻擋。
3. 主迴圈用 22.9 節的 `sigsuspend` 模式等待。收到 `SIGHUP` 時，在主程式裡（不是 handler 裡）重新載入設定；這時可以安心呼叫 `fopen`、`malloc`、`printf`，因為我們處在正常的控制流中。兩次 `SIGHUP` 間隔 100 ms，各自被處理；如果兩次幾乎同時到達，可能會合併成一次，但「重新載入」做一次和做兩次結果相同，所以沒關係。這也是設計 signal 協定的原則：讓處理動作是冪等的（idempotent，做多次和做一次效果一樣）。
4. 收到 `SIGTERM` 後不是立刻結束，而是停止接新請求，等手上的請求做完才 exit 0。
5. 模擬維運的子行程用 fork 之前存好的父行程 PID（`parent`）送 signal，最後主程式 `waitpid` 回收它，第 21 章的教訓沒有忘記。

### 程式四：setjmp／longjmp 的錯誤回復與逾時中止

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <ctype.h>
#include <setjmp.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

static jmp_buf parse_env;

/* 解析 "300x200" 這類尺寸；任何一層發現錯誤都直接跳回最外層。 */
static int parse_number(const char **s) {
    if (!isdigit((unsigned char)**s)) longjmp(parse_env, 1);   /* 錯誤碼 1：不是數字 */
    int v = 0;
    while (isdigit((unsigned char)**s)) {
        v = v * 10 + (*(*s)++ - '0');
        if (v > 10000) longjmp(parse_env, 2);                  /* 錯誤碼 2：太大 */
    }
    return v;
}

static void parse_size(const char *s, int *w, int *h) {
    *w = parse_number(&s);
    if (*s++ != 'x') longjmp(parse_env, 3);                     /* 錯誤碼 3：缺少 x */
    *h = parse_number(&s);
}

static void try_parse(const char *spec) {
    int w = 0, h = 0;
    int code = setjmp(parse_env);         /* 第一次回傳 0；被 longjmp 回來時回傳錯誤碼 */
    if (code == 0) {
        parse_size(spec, &w, &h);
        printf("%-10s → %d x %d\n", spec, w, h);
    } else {
        printf("%-10s → 解析失敗，錯誤碼 %d\n", spec, code);
    }
}

static sigjmp_buf timeout_env;
static void on_alarm(int sig) { (void)sig; siglongjmp(timeout_env, 1); }

int main(void) {
    const char *specs[] = {"300x200", "300y200", "abcx10", "99999x1"};
    for (int i = 0; i < 4; i++) try_parse(specs[i]);

    /* 用 SIGALRM ＋ siglongjmp 中止一段跑太久的純計算。 */
    signal(SIGALRM, on_alarm);                /* 示範求簡短；正式程式請用 sigaction */
    volatile unsigned long iterations = 0;    /* volatile：longjmp 之後值才可靠 */
    if (sigsetjmp(timeout_env, 1) == 0) {     /* 1：一併保存 signal mask */
        alarm(1);
        for (;;) iterations++;                /* 模擬卡住的解碼迴圈 */
    }
    printf("1 秒逾時，計算被中止（迴圈%s）\n", iterations > 1000 ? "已執行超過一千次" : "幾乎沒有執行");
    return 0;
}
```

```text
300x200    → 300 x 200
300y200    → 解析失敗，錯誤碼 3
abcx10     → 解析失敗，錯誤碼 1
99999x1    → 解析失敗，錯誤碼 2
1 秒逾時，計算被中止（迴圈已執行超過一千次）
```

1. `300x200` 正常解析。其他三個輸入分別在不同深度出錯：`300y200` 在 `parse_size` 發現缺少 `x`；`abcx10` 在 `parse_number` 的第一個字元就不是數字；`99999x1` 在累加數字時超過上限。三者都直接 `longjmp` 回 `try_parse`，`setjmp` 第二次回傳的值就是錯誤碼。
2. 中間的函式不需要一層層檢查回傳值，這是 nonlocal jump 的好處；代價是如果中間有 `malloc`，就會洩漏。
3. 第二部分用 `alarm(1)` 設定 1 秒後送 `SIGALRM`，handler 用 `siglongjmp` 跳出無窮迴圈。被打斷的是純計算迴圈，不在任何 library 函式裡，所以這樣做是安全的。`iterations` 宣告為 `volatile`，否則跳回來之後它的值是不確定的。

### 程式五：沒有 volatile 的 local 變數，在 longjmp 之後會怎樣

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <setjmp.h>
#include <stdio.h>

static jmp_buf env;
static void fail(void) { longjmp(env, 1); }

int main(void) {
    int plain = 1;              /* 一般的 local 變數：可能被放在暫存器裡 */
    volatile int vol = 1;       /* volatile：每次都讀寫記憶體 */
    if (setjmp(env) == 0) {
        plain = 2;
        vol = 2;
        fail();                 /* 跳回 setjmp，這次 setjmp 回傳 1 */
    }
    /* C 標準：setjmp 之後被修改過的非 volatile local 變數，值是不確定的 */
    printf("plain = %d, volatile = %d\n", plain, vol);
    return 0;
}
```

用 Apple clang 21 分別以 `-O0` 與 `-O1` 編譯執行（這是 C 標準說「值不確定」的情況，結果依編譯器與最佳化等級而定）：

```text
-O0: plain = 2, volatile = 2
-O1: plain = 1, volatile = 2
```

`-O0` 時每個變數都放在 stack 上，`plain = 2` 寫進了記憶體，`longjmp` 回來讀到 2。`-O1` 時編譯器把 `plain` 放在暫存器裡（或乾脆把它當成常數），`longjmp` 還原了 `setjmp` 當時的暫存器，`plain` 回到舊值 1。`volatile` 的變數每次都讀寫記憶體，所以兩種情況都是 2。這種「開了最佳化才出現」的 bug 非常難追，看到 `setjmp` 就要檢查它之後被修改的 local 變數。

## 22.13 在工作上怎麼用

### `thumbd` 的最終設計：專用的 signal thread

程式三的 handler 加 `sigsuspend` 模式適合單執行緒程式。`thumbd` 是 thread pool，還要多考慮一件事：**signal handler 的設定是整個 process 共用的，但 signal mask 是每條 thread 各自的**。送給 process 的 signal（例如 `kill` 送的 `SIGTERM`）會被遞送給**任何一條**沒有阻擋它的 thread，你無法控制是哪一條。由硬體錯誤產生的 `SIGSEGV`、`SIGFPE` 則固定送給出錯的那條 thread。

多執行緒服務的標準做法是：在建立任何 thread 之前，主程式先用 `pthread_sigmask` 阻擋所有要處理的 signal；之後建立的 worker thread 會繼承這個 mask，全部不會收到它們。再開一條專用的 thread，用 `sigwait` **同步地**等待這些 signal：

```c
/* 在 main 一開始、建立 worker 之前執行 */
sigset_t set;
sigemptyset(&set);
sigaddset(&set, SIGHUP);
sigaddset(&set, SIGTERM);
pthread_sigmask(SIG_BLOCK, &set, NULL);   /* 之後建立的 thread 都繼承這個 mask */

/* 專用的 signal thread */
static void *signal_thread(void *arg) {
    sigset_t *set = arg;
    for (;;) {
        int sig;
        sigwait(set, &sig);               /* 同步取出一個 pending signal，沒有 handler */
        if (sig == SIGHUP) reload_config();        /* 一般的程式碼，可以 malloc、log */
        if (sig == SIGTERM) { begin_shutdown(); break; }
    }
    return NULL;
}
```

`sigwait` 讓 signal 變成「一個 thread 呼叫函式、拿到結果」的普通同步事件，完全沒有 handler，也就沒有 async-signal-safe 的限制。Linux 還有 `signalfd`：把 signal 變成一個可以 `read` 的 file descriptor，直接放進 epoll 迴圈（第 30 章）；跨平台的事件迴圈 library（libuv、libevent）內部則常用 **self-pipe trick**：handler 只對一個 pipe `write` 一個 byte，事件迴圈把 pipe 的讀取端當成普通事件處理。三者的精神相同：**讓 handler 盡量小，把真正的處理搬回正常的控制流**。

### 優雅關閉的檢查清單

在 systemd、Docker、Kubernetes 底下，服務被要求停止時的流程都是：送 `SIGTERM`，等一段寬限時間，還沒結束就送 `SIGKILL`。`docker stop` 預設等 10 秒，Kubernetes 的 `terminationGracePeriodSeconds` 預設 30 秒。故事裡「每次都等滿 30 秒」，就是 `thumbd` 根本沒處理 `SIGTERM`。

```text
 收到 SIGTERM
   │
   ├─ 1. 標記為「正在關閉」，health check 開始回報失敗，讓 load balancer 不再送新請求
   ├─ 2. 停止 accept 新連線（關閉 listening socket）
   ├─ 3. 等待處理中的請求完成，設定上限（必須小於寬限時間）
   ├─ 4. 終止並 waitpid 所有外部工具子程序（第 21 章）
   ├─ 5. flush log、關閉檔案與資料庫連線
   └─ 6. exit(0)；超過上限仍未完成就記錄並以非 0 結束
```

工作上還要確認：

- **服務真的收到了 signal**。如果容器的進入點是 `sh -c "thumbd ..."`，PID 1 是 `sh`，`SIGTERM` 送給了 `sh`，而 `sh` 不會轉送給 `thumbd`。用 `exec thumbd ...` 讓 `thumbd` 取代 shell，或用 `tini` 當 PID 1。
- **PID 1 的特殊規則**。Linux 上，namespace 的 init process（PID 1）只會收到它**有安裝 handler** 的 signal；對於預設動作是終止的 signal（例如 `SIGTERM`），如果 PID 1 沒有 handler，kernel 會直接丟掉。所以 `thumbd` 直接當容器的 PID 1、又沒處理 `SIGTERM` 時，`docker stop` 只會等滿 10 秒後用 `SIGKILL`。（`SIGKILL` 從容器外部送來時仍然有效。）
- **確認 handler 已安裝**：`grep Sig /proc/<PID>/status`，用 22.4 節的手算檢查 `SigCgt`。
- **寫 socket 的服務要處理 `SIGPIPE`**。客戶端提早斷線時，`write` 會觸發 `SIGPIPE`，預設動作是終止整個服務。網路服務通常在啟動時 `signal(SIGPIPE, SIG_IGN)`，或在 `send` 時加 `MSG_NOSIGNAL`（Linux），改成檢查 `write` 回傳的 `EPIPE` 錯誤（第 28 章）。
- **logrotate 的協定要對齊**：要嘛服務處理 `SIGHUP` 並重新打開 log 檔，要嘛 logrotate 改用 `copytruncate`；不要讓維運腳本送服務不認得的 signal。

### 觀察 signal 的工具

```bash
kill -l                                   # 列出這台機器上的 signal 名稱與編號
grep -E 'Sig(Pnd|Blk|Ign|Cgt)' /proc/<PID>/status   # 看 pending、blocked、忽略、有 handler 的 signal
strace -e trace=%signal -p <PID>          # 觀察 signal 的遞送與 rt_sigaction 等呼叫
kill -0 <PID> && echo alive               # 只檢查 process 是否存在
timeout -s TERM -k 5 30 ./job             # 30 秒後送 SIGTERM，再 5 秒後送 SIGKILL
```

`strace` 輸出中，`--- SIGTERM {si_signo=SIGTERM, si_code=SI_USER, si_pid=1234, ...} ---` 這種行告訴你 signal 是誰送的（`si_pid`），在追「是誰殺了我的服務」時非常有用。

### 高階語言裡的 signal

Python 的 `signal.signal(signal.SIGTERM, handler)` 看起來像在 C 裡安裝 handler，但實際上 CPython 的 C handler 只設一個旗標，Python 層的 handler 會在主執行緒的下一個 bytecode 之間才執行。所以 Python 的 handler 可以呼叫任何 Python 函式，但只會在主執行緒執行，而且主執行緒卡在某些 C 擴充函式裡時會延遲。Go 用 `signal.Notify` 把 signal 轉成 channel 上的訊息，和前面介紹的 `sigwait` 是同一種設計。理解底層的 C 機制，才能解釋為什麼這些語言都選擇「把 signal 變成同步事件」。

## 22.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 服務在固定時間無聲無息地重啟，沒有 core dump | 收到沒處理的 `SIGHUP`、`SIGPIPE` 等預設動作為終止的 signal | systemd journal 的結束原因、`strace -e trace=%signal` 的 `si_pid`；結束碼 128 + n | 安裝 handler 或明確忽略；對齊維運腳本送的 signal |
| 服務偶爾整個卡住，所有 thread 停在 malloc 或 stdio 的鎖 | handler 呼叫了 `printf`、`malloc` 等非 async-signal-safe 函式 | `gdb -p <PID>` 後 `thread apply all bt`，看到 handler 的 frame 在鎖函式裡 | handler 只設旗標，工作移到主程式；或改用 `sigwait`／`signalfd` |
| 有時候留下幾個 zombie，很難重現 | `SIGCHLD` handler 每次只 `waitpid` 一個，signal 合併後漏收 | 用程式一的方法讓多個子行程同時結束 | handler 裡用 `while (waitpid(-1, ..., WNOHANG) > 0)` |
| 開了 `-O2` 後程式收到 signal 也不會停 | 旗標不是 `volatile`，編譯器把讀取移出迴圈 | 看組合語言（22.6 節）或加 `volatile` 測試 | 旗標宣告為 `volatile sig_atomic_t`；改用 `sigsuspend` 等待 |
| `read`、`accept` 偶爾回傳 −1，`errno` 是 `EINTR` | signal 打斷了阻塞中的 system call | 記錄 `errno`；檢查 `sa_flags` 有沒有 `SA_RESTART` | 設 `SA_RESTART`，並在迴圈中遇到 `EINTR` 時重試 |
| 容器停止時總是等滿寬限時間才被殺 | 程式是 PID 1 卻沒處理 `SIGTERM`；或進入點的 `sh -c` 沒有轉送 signal | `docker top`／`ps` 看 PID 1 是誰；看 `SigCgt` | 處理 `SIGTERM`；用 `exec` 或 `tini` |
| 工作表裡出現已經不存在的 PID | fork 後 handler 先跑，remove 發生在 add 之前 | 在 add／remove 加 `write` 記錄順序 | fork 前阻擋 `SIGCHLD`，登記後再解除；子行程 exec 前還原 mask |
| 用 `longjmp` 回復錯誤後，記憶體或檔案越用越多 | 跳過了中間函式的清理程式碼 | ASan／Valgrind 的 leak 報告（第 26 章）；`lsof` 看 fd 數量 | 在 `setjmp` 那一層集中管理資源；或改用回傳錯誤碼 |

## 22.15 動手練習

1. **手算**：某個 process 的 `/proc/<PID>/status` 顯示 `SigCgt: 0000000000014003`、`SigIgn: 0000000000001000`。在 Linux x86-64 上，它對哪些 signal 安裝了 handler、忽略了哪些？（答案：`0x14003` 的 bit 0、1、14、16 為 1，對應 signal 1、2、15、17，也就是 `SIGHUP`、`SIGINT`、`SIGTERM`、`SIGCHLD`；`0x1000` 是 bit 12，對應 signal 13 `SIGPIPE` 被忽略。驗證方法：在 Linux 上寫一個安裝這些 handler 的程式，執行時讀自己的 `/proc/self/status`。）
2. 修改程式一，把阻擋期間送出的 `SIGUSR1` 改成 real-time signal `SIGRTMIN`（Linux 才有，第一行加 `// linux-only`），觀察 handler 執行的次數是否變成 5，並解釋差別。
3. 修改第 21 章的迷你 shell：安裝 `SIGCHLD` handler，用 22.7 節的迴圈回收背景工作，並用 22.8 節的方法避免 race。handler 裡要印「背景工作結束」時，只能用 `write`。
4. 寫一個程式，在 `while (!flag) ;` 迴圈中等待 `SIGALRM` 設定旗標，分別用有與沒有 `volatile` 的旗標、`-O0` 與 `-O2` 編譯，記錄哪些組合會卡住（用 `timeout 3 ./a.out` 避免真的卡住），並和 22.6 節的組合語言對照。
5. 用 Python 寫一個在收到 `SIGTERM` 後完成手上工作才結束的程式，然後用 `timeout -s TERM 2 python3 your.py` 測試；再把它放進 Docker（不加 `--init`、直接當 PID 1）並用 `docker stop` 測試，記錄停止所需的時間。
6. 閱讀 CS:APP Shell Lab 的說明文件，對照 22.11 節的表格，為 `tsh` 的每個 handler 與每個共享資料結構寫下「誰會碰它、在哪些時間點可能被打斷、你要怎麼阻擋」，在寫任何程式碼之前先完成這張表。

## 本章重點整理

- signal 是 kernel 送給 process 的小型通知，只有一個編號；來源包括硬體 exception（`SIGSEGV`、`SIGFPE`）、軟體事件（`SIGCHLD`、`SIGPIPE`）與其他 process 的 `kill`。
- 每種 signal 有預設動作，多數是終止；`SIGHUP`、`SIGPIPE` 這類不起眼的 signal 也會殺死沒有處理它們的服務。`SIGKILL` 與 `SIGSTOP` 無法攔截、忽略或阻擋。
- `kill` 可以送 signal 給單一 process 或整個 process group；終端機的 `Ctrl-C`、`Ctrl-Z` 會送給前景 process group 的所有成員，這是 shell 管理工作的基礎。
- kernel 為每個 thread 維護 pending 與 blocked 兩個位元向量，在返回 user mode 時遞送 `pending & ~blocked` 中的 signal，所以 signal 可能在任何兩條指令之間到來。
- pending 是位元而不是計數器，同一種 signal 不排隊；一個 `SIGCHLD` 代表「至少一個」子行程狀態改變，handler 必須用 `WNOHANG` 迴圈回收。
- 用 `sigaction` 安裝 handler；被打斷的 system call 可能回傳 `EINTR`，`SA_RESTART` 能讓多數 system call 自動重來，但不是全部。
- handler 只能呼叫 async-signal-safe 函式；`printf`、`malloc`、鎖操作都不安全，可能造成 deadlock 或資料損壞。
- 安全 handler 的守則：保持簡單、只設旗標；保存並還原 `errno`；存取共享資料時阻擋 signal；旗標用 `volatile sig_atomic_t`。
- fork 後 handler 可能比主程式先跑，造成「先移除、後登記」的 race；在 fork 前阻擋 `SIGCHLD`、登記後再解除，子行程在 exec 前還原 mask。
- 用 `pause` 等待旗標有 lost wakeup 的 race，`sigsuspend` 把「解除阻擋」與「睡覺」合成一個不可分割的動作。
- 多執行緒程式應在建立 thread 前阻擋 signal，用專用 thread 的 `sigwait`（或 Linux 的 `signalfd`）把 signal 變成同步事件。
- `setjmp`／`longjmp` 能從深層函式直接跳回外層，適合錯誤回復，但會跳過資源清理；`setjmp` 之後被修改的 local 變數要宣告 `volatile`，從 handler 跳出要用 `sigsetjmp`／`siglongjmp`。
- 服務的優雅關閉是一個協定：收到 `SIGTERM` 後停止接新請求、完成手上工作、回收子行程、清理資源，在寬限時間內結束；容器的 PID 1 要特別確認 signal 真的送得到。

## 延伸問答

> [!question]- Q1. 為什麼 signal 不排隊？這個設計造成了什麼後果？
> 傳統 Unix 為每個 process 只記一個 pending 位元向量，每種 signal 一個 bit。這個設計極其簡單、固定大小，kernel 不必為每個 signal 配置記憶體，也不會被大量 signal 塞爆。代價是 signal 只能表達「這件事至少發生過一次」，無法表達「發生了幾次」或附帶任何資料。
>
> 後果是程式不能把 signal 當成訊息佇列使用。最常見的 bug 就是 `SIGCHLD` handler 每次只回收一個子行程：幾個子行程同時結束時，signal 合併，handler 執行的次數少於子行程數，留下 zombie。正確的寫法是把 signal 當成「去檢查一下」的提示，由 handler 或主程式自己查出所有發生的事件，例如用 `waitpid(-1, ..., WNOHANG)` 迴圈。需要排隊與附帶資料時，應該用 real-time signal 或改用 pipe、socket 等真正的通訊機制。

> [!question]- Q2. 程式找錯：下面的 handler 有哪些問題？
> ```c
> int got_hup = 0;
> void on_hup(int sig) {
>     printf("reloading config\n");
>     config = load_config("/etc/thumbd.conf");
>     got_hup = 1;
> }
> ```
>
> 第一，`printf` 不是 async-signal-safe：它有內部 buffer 與鎖，如果主程式正在 `printf` 時被打斷，可能 deadlock 或輸出錯亂。第二，`load_config` 幾乎一定會呼叫 `fopen`、`malloc`，同樣可能在主程式持有 allocator 鎖時 deadlock，或讀到修改到一半的 heap 資料結構。第三，handler 直接替換 `config`，主程式可能正在讀舊的 `config` 讀到一半，看到不一致的設定。第四，`got_hup` 不是 `volatile sig_atomic_t`，主程式的迴圈可能永遠看不到它的改變。
>
> 修法是讓 handler 只做 `got_hup = 1`（旗標宣告為 `volatile sig_atomic_t`），主程式在安全的時機檢查旗標，再呼叫 `load_config` 並替換設定。多執行緒的服務更好的做法是用專用 thread 的 `sigwait`，完全不用 handler。

> [!question]- Q3. 你在 production 發現 `thumbd` 每次部署都要等 30 秒才停下來，而且有請求失敗。你會怎麼查、怎麼修？
> 30 秒剛好是 Kubernetes 的預設 `terminationGracePeriodSeconds`，表示 `SIGTERM` 沒有讓程式結束，最後是被 `SIGKILL` 殺掉的；請求失敗則是因為被殺時還有處理中的請求。先確認 signal 有沒有送到：看容器的 PID 1 是誰，如果是 `sh -c` 啟動的 shell，`SIGTERM` 被 shell 收走，沒有轉送；如果 PID 1 就是 `thumbd`，看 `/proc/1/status` 的 `SigCgt` 有沒有 bit 14（`SIGTERM`），沒有的話，PID 1 的特殊規則會讓 kernel 直接丟掉這個 signal。
>
> 修法分兩層：讓 signal 送得到（進入點用 `exec`，或用 `tini` 當 PID 1）；讓程式正確處理（實作優雅關閉：health check 先失敗、停止 accept、等處理中的請求完成、回收子行程、在寬限時間內結束）。另外，Kubernetes 從 endpoint 移除 pod 和送 `SIGTERM` 是同時發生的，load balancer 可能還會送幾秒的新請求進來，常見的做法是用 `preStop` hook 或在收到 `SIGTERM` 後先等幾秒再停止 accept。

> [!question]- Q4. 阻擋（block）一個 signal 和忽略（ignore）一個 signal 有什麼不同？各自什麼時候用？
> 忽略是設定 signal 的處理方式為 `SIG_IGN`：signal 送達時 kernel 直接丟掉它，程式永遠不會知道它來過。阻擋是把 signal 加入 blocked 向量：signal 送達時留在 pending，解除阻擋後立刻被遞送，只是「延後處理」，不會遺失（雖然多次會合併成一次）。
>
> 忽略適合「這個事件我完全不在乎」的情況，最典型的是網路服務忽略 `SIGPIPE`，改從 `write` 的 `EPIPE` 錯誤得知對方斷線。阻擋適合「這個事件我要處理，但現在不是時候」，例如修改和 handler 共享的工作表時、fork 到登記子行程之間、以及配合 `sigsuspend` 等待時。還要注意兩者跨過 exec 的行為：被忽略的 signal 在 exec 後仍然被忽略，blocked mask 也會保留，所以子行程在 exec 前常常需要還原它們，否則外部工具會繼承奇怪的 signal 設定。

> [!question]- Q5. 面試題：為什麼 `SIGKILL` 不能被攔截？`kill -9` 之後程式一定會馬上消失嗎？
> `SIGKILL` 和 `SIGSTOP` 是作業系統保留給管理者的最後手段。如果它們能被攔截或忽略，一個有 bug 或惡意的程式就可以讓自己永遠無法被停止。所以 kernel 不允許為它們安裝 handler、忽略或阻擋，收到時直接執行預設動作。代價是程式沒有任何清理的機會，所以正常的停止流程應該先送 `SIGTERM`，給程式寬限時間，最後才用 `SIGKILL`。
>
> `kill -9` 之後程式也不一定「馬上」消失。如果 process 正處於不可中斷的睡眠（`ps` 顯示 `D` 狀態，通常在等磁碟或 NFS 的 I/O），signal 要等它離開那個狀態才會生效。即使 process 已經終止，它也會變成 zombie，直到父行程 `waitpid` 回收（第 21 章）。所以「`kill -9` 殺不掉」通常是 `D` 狀態或已經是 zombie。

> [!question]- Q6. 用 `while (!flag) pause();` 等待 signal 有什麼問題？`sigsuspend` 怎麼解決？
> 問題是 lost wakeup：如果 signal 剛好在「檢查 `flag` 為 0」之後、「呼叫 `pause`」之前到達，handler 把 `flag` 設為 1，然後 `pause` 才開始睡。這次的 signal 已經被處理掉了，`pause` 會一直睡到下一個 signal，而下一個可能永遠不會來。這個空檔雖然很小，但在高負載或特定排程下一定會發生。
>
> `sigsuspend(&mask)` 把「把 blocked 換成 mask」與「睡到有 signal」合成一個不可分割的動作。使用時平常保持 signal 被阻擋，檢查 `flag` 時 handler 不可能插進來；呼叫 `sigsuspend` 才解除阻擋並睡覺。如果 signal 在檢查之前就到了，它停在 pending，`sigsuspend` 一解除阻擋就立刻遞送並返回。返回時 mask 會恢復成阻擋狀態，迴圈可以安全地再次檢查。這和 condition variable 的 `pthread_cond_wait` 原子地「釋放鎖並等待」是同一個設計思想。

> [!question]- Q7. 什麼情況下適合用 `setjmp`／`longjmp`？為什麼 libpng 要求你使用它？
> `setjmp`／`longjmp` 適合「錯誤可能在很深的呼叫層級發生，而所有錯誤都要回到同一個外層處理」的情況，例如解析器、直譯器、以及用 C 寫的 library 想提供類似 exception 的錯誤處理。中間的函式不必一層層檢查與傳遞錯誤碼，程式比較簡潔。
>
> libpng 是用 C 寫的，解碼過程有很深的呼叫鏈，而損壞的圖檔可能在任何一層被發現。libpng 預設的錯誤處理是透過 `longjmp` 跳回使用者用 `setjmp(png_jmpbuf(png_ptr))` 設定的位置；如果使用者沒有設定，就無法回復。對 `thumbd` 來說，這代表處理使用者上傳的圖檔時一定要設好 `setjmp`，並在錯誤分支裡釋放這次解碼配置的所有資源（`png_destroy_read_struct`、關檔），否則每張壞圖都會洩漏一點記憶體。還要記得，`setjmp` 之後在 `if` 裡修改過的 local 變數（例如 row pointer 陣列）要宣告為 `volatile`。

> [!question]- Q8. 多執行緒的程式收到 `SIGTERM`，是哪一條 thread 執行 handler？這對 `thumbd` 有什麼影響？
> handler 的設定是整個 process 共用的，但 signal mask 是每條 thread 各自的。送給整個 process 的 signal（`kill` 送的 `SIGTERM`、`SIGHUP`）會由 kernel 挑一條**沒有阻擋它**的 thread 來執行 handler，具體是哪一條無法預測；由某條 thread 自己造成的同步 signal（存取壞指標的 `SIGSEGV`、除以零的 `SIGFPE`）則送給那條 thread。
>
> 對 `thumbd` 的影響是：如果不做任何處理，`SIGTERM` 可能打斷任何一條正在處理圖片的 worker thread，它可能正拿著快取的鎖或在 `malloc` 裡面，handler 一做事就可能 deadlock。標準解法是在 `main` 建立任何 thread 之前，用 `pthread_sigmask` 阻擋 `SIGHUP`、`SIGTERM`，讓所有 worker 繼承這個 mask，然後開一條專用 thread 用 `sigwait` 同步地接收它們。這樣 signal 永遠只在一個可預測的地方、以普通函式呼叫的方式被處理。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 8 章 8.5–8.6 節。
- [CS:APP 3e Labs](https://csapp.cs.cmu.edu/3e/labs.html)：Shell Lab 的說明文件與 trace 檔，用來對照 22.11 節的學習目標。
- [Linux man pages](https://man7.org/linux/man-pages/)：`signal(7)`（signal 列表、`SA_RESTART` 與 EINTR 的完整規則）、`signal-safety(7)`（async-signal-safe 函式清單）、`sigaction(2)`、`sigprocmask(2)`、`sigsuspend(2)`、`signalfd(2)`、`pthread_sigmask(3)`、`setjmp(3)`。
- [POSIX.1-2024（The Open Group Base Specifications）](https://pubs.opengroup.org/onlinepubs/9799919799/)：Signal Concepts 一節，以及 async-signal-safe 函式的標準定義。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：Exceptional Control Flow: Signals and Nonlocal Jumps 的投影片。
