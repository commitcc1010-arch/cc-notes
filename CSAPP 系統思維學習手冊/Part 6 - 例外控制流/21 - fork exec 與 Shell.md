---
chapter: 21
title: fork、exec 與 Shell
part: 6
---

# 第 21 章　Process 控制：fork、exec、wait 與 Shell

> [!abstract] 本章地圖
> **核心問題**：一個程式要怎麼啟動另一個程式、等它結束、拿回它的結果，而且不在系統裡留下垃圾？
>
> **你會學到**：
> - 解釋 `fork` 為什麼「呼叫一次、回傳兩次」，並用 process graph 推理多次 `fork` 之後的所有可能輸出
> - 分辨 `exit`、`_exit` 與 `return`，說清楚 zombie 和孤兒行程是怎麼產生、由誰回收
> - 正確使用 `waitpid` 與 `WIFEXITED`、`WEXITSTATUS` 等巨集，判斷子行程是正常結束還是被 signal 殺掉
> - 用 `execve` 載入新程式，知道 `argv`、`envp` 怎麼傳、哪些狀態會跨過 exec 保留下來
> - 寫出一個能執行外部指令、支援背景工作的迷你 shell，並理解真正的 shell 還多做了什麼
> - 在工作上診斷 zombie 累積、`fork: Resource temporarily unavailable`、容器內 PID 1 不回收子行程等問題
>
> **前置知識**：第 20 章（process 的抽象、system call 與錯誤處理）、第 2 章（C 的指標與字串陣列）
>
> **對應 CS:APP 3e**：第 8 章 8.4 節

## 21.1 故事：越積越多的 `<defunct>`

拾光相簿開始支援 iPhone 拍的 HEIC 照片。`thumbd` 內建的解碼器只認得 JPEG 和 PNG，於是老周當初的設計是：遇到少見格式時，呼叫一個外部轉檔工具 `heic-convert`，把 HEIC 轉成暫存的 PNG，再交給原本的流程處理。最早的版本用 C 標準函式庫的 `system()`，簡單但每次都要多啟動一個 `/bin/sh`，而且整個 worker thread 會卡住直到工具跑完。

小安接手後想「改得更有效率」：直接用 `fork` 和 `execvp` 啟動工具，不經過 shell，然後用一個計時器檢查暫存檔有沒有出現。上線後一切正常，縮圖都產生了。

兩週後，SRE 阿哲在值班頻道貼了一段 `ps` 輸出：`thumbd` 底下掛著兩萬多個 `[heic-convert] <defunct>`。又過了兩天，`thumbd` 的 log 開始出現 `fork: Resource temporarily unavailable`，所有 HEIC 照片的縮圖都失敗了。小安很困惑：「那些工具明明都已經跑完了，為什麼還在 process 列表裡？它們又沒有在用 CPU。」

老周看了程式碼，只說了一句：「孩子是你生的，後事也得由你來辦。」意思是：子行程結束之後，kernel 會保留一小筆紀錄，等父行程來讀它的結束狀態；沒有人來讀，這筆紀錄就永遠留著。這一章要講的就是 process 從出生到被回收的整個生命週期：`fork` 怎麼建立新 process、`execve` 怎麼換上新程式、`waitpid` 怎麼回收，以及把這些東西組合起來的經典程式：shell。

## 21.2 Process 的身分與生命週期

第 20 章說過，**process**（行程）是「一個正在執行的程式實例」：它有自己的虛擬位址空間、暫存器狀態、打開的檔案，以及一條邏輯上的控制流程。同一個程式可以同時有很多個 process，例如機器上可能有十個 `bash`，它們執行同一個執行檔，卻各自獨立。

要管理這麼多 process，作業系統給每個 process 一個號碼，叫 **PID**（process ID，行程編號），例如 `37583`。除此之外，每個 process 都記得是誰建立了它，這個建立者的 PID 叫 **PPID**（parent PID）。程式可以用兩個 system call 查到這兩個號碼：

```c
#include <unistd.h>
pid_t getpid(void);    /* 我自己的 PID */
pid_t getppid(void);   /* 我的父程序的 PID */
```

`pid_t` 在 Linux 和 macOS 上都是 `int` 的別名。所有 process 透過 PPID 串成一棵樹：最頂端是開機時 kernel 建立的第一個 user process（Linux 上通常是 systemd，macOS 上是 launchd，PID 都是 1），它啟動各種服務，服務再啟動自己的子行程。你可以用 `pstree` 或 `ps -ef` 看到這棵樹。

從程式設計師的角度，一個 process 一生會經過三種狀態：

| 狀態 | 意義 | 怎麼進入 | 在 `ps` 的 STAT 欄 |
|---|---|---|---|
| running（執行中） | 正在 CPU 上跑，或排隊等著被排程 | 被建立、被喚醒、收到 `SIGCONT` | `R`（執行或可執行）、`S`（睡眠等待事件） |
| stopped（暫停） | 被暫停，不會被排程，直到收到 `SIGCONT` | 收到 `SIGSTOP`、`SIGTSTP` 等 signal（第 22 章） | `T` |
| terminated（已終止） | 不會再執行；若父行程還沒回收，就是 zombie | 呼叫 `exit`、從 `main` return、被 signal 終止 | `Z` |

「running」在這裡包含了「正在用 CPU」和「可以用但正在排隊」，CS:APP 把它們視為同一個狀態，因為對程式來說兩者沒有差別：它隨時可能被排到。`ps` 的 `S` 表示 process 正在等某件事（例如等網路資料），嚴格說不是「正在跑」，但它也沒有被暫停或終止。

整個生命週期可以畫成這樣：

```text
                 fork()
   父程序 ─────────────────▶ 子程序誕生（running）
                                 │
                     ┌───────────┼──────────────┐
                     │           │              │
                 execve()     SIGSTOP         exit() / return / 被 signal 殺
                 換程式      ┌──▼──┐               │
                 （PID 不變） │stopped│              ▼
                     │       └──┬──┘          terminated（zombie）
                     │      SIGCONT              │ 還佔著 PID 與結束狀態
                     └──────────┘                │
                                         父程序 waitpid()
                                                 │
                                                 ▼
                                         kernel 釋放紀錄，PID 可重用
```

這張圖有三個關鍵點，接下來的三節各講一個。第一，新 process 只能由 `fork`（或它的變形）產生，它一開始執行的是和父行程**同一個程式**。第二，要執行別的程式，必須在 process 內部呼叫 `execve`，它換掉程式但不換 PID。第三，process 終止後不會立刻消失，必須由父行程用 `waitpid` 回收。小安的 bug 就是漏了第三步。

## 21.3 fork：呼叫一次，回傳兩次

**`fork`** 是建立新 process 的 system call。它的效果是：把呼叫它的 process 幾乎完整地複製一份，複製出來的叫**子行程**（child process），原本的叫**父行程**（parent process）。複製完成後，兩個 process 都從 `fork` 回傳的那一點繼續往下執行。

```c
#include <unistd.h>
pid_t fork(void);
/* 子程序得到 0；父程序得到子程序的 PID；失敗時父程序得到 -1，沒有子程序被建立 */
```

這就是「呼叫一次、回傳兩次」的意思：程式碼裡只寫了一次 `fork()`，但它在兩個 process 裡各回傳一次，回傳值不同。程式靠這個不同的回傳值分辨「我現在是誰」：

```c
pid_t pid = fork();
if (pid < 0) {
    perror("fork");          /* 失敗：常見原因是 process 數量到上限（EAGAIN）*/
} else if (pid == 0) {
    /* 這裡只有子程序會執行 */
} else {
    /* 這裡只有父程序會執行，pid 是子程序的 PID */
}
```

為什麼子行程拿到 0、父行程拿到子行程的 PID？因為子行程隨時可以用 `getppid()` 查到父行程是誰，不需要回傳值告訴它；父行程卻可能有很多個子行程，必須在建立的當下記下這個 PID，之後才能等它、殺它或查它的狀態。0 剛好不會是任何子行程的 PID，所以適合當「你是子行程」的訊號。

### 複製了什麼、共享了什麼

「幾乎完整地複製」要說得精確一點，因為工作上很多 bug 都出在這裡：

| 項目 | fork 之後的情況 | 後果 |
|---|---|---|
| 虛擬位址空間（stack、heap、全域變數、程式碼） | 子行程有**一份獨立的副本**，內容與 fork 當下相同 | 子行程改變數，父行程看不到，反之亦然 |
| 暫存器與程式計數器 | 相同，所以兩者都從 `fork` 回傳處繼續 | 唯一差別是 `%rax` 裡的回傳值 |
| 打開的 file descriptor | 子行程得到一份 descriptor table 的**副本**，但每個 descriptor 指向**同一個** open file（第 27 章） | 兩者共用檔案位移（offset）；父行程寫一半的檔案，子行程接著寫會接在後面 |
| stdio 的 buffer（`printf` 還沒寫出去的資料） | 它只是位址空間裡的一般記憶體，所以**也被複製** | 同一段文字可能被印兩次，見 21.4 節 |
| PID、PPID | 子行程有新的 PID，PPID 是父行程 | — |
| 執行緒 | 子行程**只有一條執行緒**：呼叫 `fork` 的那一條 | 多執行緒程式 fork 後，其他執行緒持有的鎖永遠不會被釋放，見 21.8 節 |
| 尚未處理的 signal、計時器 | 不繼承 pending signal；signal 處理方式與 mask 則繼承 | 第 22 章 |

「複製整個位址空間」聽起來很貴：`thumbd` 的 RSS 有 1.8 GB，每次 fork 都要複製 1.8 GB 嗎？不用。現代作業系統用 **copy-on-write**（寫入時複製）：fork 時只複製 page table，並把所有頁都標成唯讀、兩邊共用；等到某一邊真的寫入某一頁時，才觸發 page fault、複製那一頁。第 24 章會詳細說明這個機制。所以 fork 的成本主要是複製 page table，與 RSS 成正比但遠小於複製資料本身。

> [!warning] 常見誤解
> 「fork 之後，子行程從 `main` 的開頭重新執行。」不是。子行程從 `fork` 回傳的那一點繼續，`fork` 之前執行過的程式碼不會再跑一次，但 `fork` 之前產生的狀態（變數的值、buffer 裡的資料、打開的檔案）全部都在。

### 父子誰先跑？

fork 回傳之後，父子兩個 process 是**並行**（concurrent）的：它們由 kernel 的排程器決定誰先在 CPU 上跑，在多核心機器上甚至真的同時跑。你**不能假設**任何順序。Linux 曾經有過讓子行程先跑的設定，macOS 與不同版本的 Linux 行為也不一樣；就算你的機器上一萬次都是父行程先印，換一台機器或負載變高就可能反過來。如果程式的正確性依賴順序，就要用 `waitpid`、pipe 或 signal 明確同步。

## 21.4 Process graph：推理 fork 程式的輸出

只要 `fork` 一多，腦中模擬就很容易出錯。CS:APP 提供一個好用的工具：**process graph**（行程圖）。它把每個 process 的執行畫成一條由左到右的線，線上的點是會產生可觀察效果的動作（例如 `printf`），`fork` 則讓一條線分岔成兩條。

先看最簡單的兩次 fork：

```c
pid_t a = fork();
pid_t b = fork();
printf("a=%d b=%d\n", a == 0, b == 0);
```

畫成 process graph：

```text
 main ──●──────────●──────────── printf(a>0, b>0)    ← 原本的 process
       fork(a)     │ fork(b)
        │          └──────────── printf(a>0, b=0)    ← 第二次 fork 的子程序
        │
        └──────────●──────────── printf(a=0, b>0)    ← 第一次 fork 的子程序
                   │ fork(b)
                   └──────────── printf(a=0, b=0)    ← 孫程序
```

第一次 `fork` 之後有 2 個 process，兩者**都會**執行第二次 `fork`，所以變成 4 個，每個都印一行。規則可以一般化：一段沒有條件判斷、連續執行 n 次 `fork` 的程式，最後會有 2^n 個 process。

輸出的順序是什麼？Process graph 的用處就在這裡：圖上的箭頭只代表「同一條線上，左邊的事一定比右邊早發生」以及「fork 之前的事一定比 fork 之後兩條線上的事早」。只要一個輸出順序不違反這些箭頭，它就是**可能發生的**。在數學上，這叫做圖的一個 **topological sort**（拓撲排序）。上面四行彼此之間沒有箭頭相連，所以 4! = 24 種順序都可能出現。

### 手算一題：加上 waitpid 之後的輸出

下面的程式加入了 `waitpid`，它會讓父行程停下來等子行程結束，等於在圖上加了一條箭頭：

```c
printf("A\n");
pid_t pid = fork();
if (pid == 0) {
    printf("B\n");
    exit(0);
}
printf("C\n");
waitpid(pid, NULL, 0);
printf("D\n");
```

```text
 父 ──A──●──── C ──── waitpid ──── D
         │              ▲
         │fork          │（子程序結束後 waitpid 才回傳）
         └──── B ──── exit
```

逐步推理：

1. `A` 在 fork 之前，一定第一個印。
2. fork 之後，`B`（子）與 `C`（父）之間沒有箭頭，順序不確定。
3. `D` 在 `waitpid` 之後，而 `waitpid` 要等子行程 `exit`，子行程 exit 又在 `B` 之後，所以 `D` 一定在 `B` 之後；`D` 也在 `C` 之後。

| 輸出順序 | 可能嗎？ | 理由 |
|---|---|---|
| A B C D | 可能 | 子行程先跑 |
| A C B D | 可能 | 父行程先跑到 waitpid，等子行程 |
| A C D B | 不可能 | D 必須等子行程結束，而 B 在子行程結束之前 |
| B A C D | 不可能 | fork 之前子行程還不存在，B 不可能早於 A |

### stdio buffer 讓同一行印兩次

Process graph 假設 `printf` 一呼叫就輸出。現實中 `printf` 只是把文字放進 process 自己記憶體裡的 **stdio buffer**（標準 I/O 緩衝區），等 buffer 滿了、遇到換行（如果輸出是終端機）或程式結束時，才真的呼叫 `write` system call 寫出去。第 27 章會完整介紹 buffering 的規則，這裡只需要知道一件事：

- 輸出到**終端機**時，stdout 是 **line buffered**：遇到 `\n` 就寫出。
- 輸出到**檔案或 pipe** 時（例如 `./prog > out.txt`、`./prog | grep`、或被 systemd 收進 journal），stdout 是 **fully buffered**：要等 buffer 滿（通常數 KiB）或程式結束才寫出。

所以 `printf("before fork\n"); fork();` 在終端機上只印一次，但導向到檔案時會印兩次：fork 的時候那行字還在 buffer 裡，被複製到子行程；兩個 process 結束時各自把自己那份 buffer 寫出去。21.10 節的實驗會實際看到這個現象。解法是在 fork 之前呼叫 `fflush(stdout)`。這是真實世界常見的 bug：程式在開發時（輸出到終端機）一切正常，部署成 daemon（輸出到 log 檔）之後 log 卻出現重複的行。

## 21.5 結束與回收：exit、zombie 與 waitpid

### 三種結束方式

process 正常結束有三種寫法，差別在「結束前做了多少清理」：

| 方式 | 會做什麼 | 適合用在 |
|---|---|---|
| 從 `main` 中 `return n` | 等同於呼叫 `exit(n)` | 一般程式的正常結束 |
| `exit(n)`（`<stdlib.h>`） | 依序執行 `atexit` 註冊的函式、flush 並關閉所有 stdio stream，最後呼叫 `_exit` | 程式任何地方想正常結束 |
| `_exit(n)`（`<unistd.h>`） | 直接進入 kernel 結束 process，**不** flush stdio、**不**執行 `atexit` | fork 出來的子行程在 exec 失敗後結束；signal handler 裡 |

n 叫做 **exit status**（結束狀態），慣例上 0 代表成功、非 0 代表失敗，只有最低 8 bits 會被父行程看到，所以範圍是 0 到 255。為什麼子行程在 exec 失敗後應該用 `_exit`？因為子行程的 stdio buffer 是從父行程複製來的，若用 `exit`，子行程會把父行程還沒寫出去的資料再寫一次，或執行父行程註冊的清理函式（例如刪除父行程的暫存檔），造成很難追的副作用。

### Zombie：已經死了，但還沒被回收

process 結束時，kernel 會釋放它的記憶體、關閉它的檔案，但**保留一小筆紀錄**：PID、結束狀態、CPU 使用時間等。這筆紀錄是留給父行程看的，因為父行程通常想知道「子行程成功了嗎？」在父行程來讀取之前，這個已終止的 process 叫做 **zombie**（殭屍行程）：它不會再執行、不佔記憶體，但佔著一個 PID 與 process table 的一格。`ps` 會把它顯示成 `Z` 狀態，名稱後面加上 `<defunct>`。

父行程讀取子行程結束狀態、讓 kernel 刪除那筆紀錄的動作，叫做 **reap**（回收）。回收是靠 `waitpid`：

```c
#include <sys/wait.h>
pid_t waitpid(pid_t pid, int *status, int options);
/* 回傳被回收（或狀態改變）的子程序 PID；
   options 含 WNOHANG 且沒有子程序結束時回傳 0；
   錯誤時回傳 -1，沒有任何子程序時 errno 為 ECHILD */
```

`pid` 參數決定要等誰：

| `pid` 的值 | 等待的對象 |
|---|---|
| `> 0` | 只等這一個 PID 的子行程 |
| `-1` | 任何一個子行程（`wait(&status)` 就是 `waitpid(-1, &status, 0)`） |
| `0` | 和自己同一個 process group 的任何子行程（process group 見第 22 章） |
| `< -1` | process group ID 等於 `-pid` 的任何子行程 |

`options` 預設是 0，意思是「沒有子行程結束就一直等」（阻塞）。最常用的選項是 **`WNOHANG`**：不等，馬上回傳；有已結束的子行程就回收並回傳它的 PID，沒有就回傳 0。另外 `WUNTRACED` 讓 `waitpid` 在子行程被暫停時也回傳，`WCONTINUED` 則在子行程被繼續時回傳，shell 的 job control 需要它們。

`status` 是一個整數，裡面打包了好幾種資訊，要用巨集解讀，不要自己去拆位元：

| 巨集 | 何時為真 | 再用哪個巨集取值 |
|---|---|---|
| `WIFEXITED(status)` | 子行程正常結束（`exit`、`return`） | `WEXITSTATUS(status)`：結束狀態（0–255） |
| `WIFSIGNALED(status)` | 子行程被 signal 終止 | `WTERMSIG(status)`：signal 編號 |
| `WIFSTOPPED(status)` | 子行程被暫停（需 `WUNTRACED`） | `WSTOPSIG(status)` |
| `WIFCONTINUED(status)` | 子行程被繼續（需 `WCONTINUED`） | — |

Shell 有個慣例：被 signal n 殺掉的指令，`$?` 會顯示 128 + n。所以你在 CI log 看到「exit code 137」（結束碼 137），就是 128 + 9，被 `SIGKILL` 殺掉（容器被 OOM killer 終止時最常見）；「exit code 143」是 128 + 15，被 `SIGTERM` 終止。

### 孤兒行程與 init

如果父行程比子行程先結束呢？子行程變成 **orphan**（孤兒行程），kernel 會把它過繼給另一個 process，讓它的 PPID 改成那個 process，未來由它負責回收。傳統上接手的是 PID 1（init、systemd、launchd），它們的工作之一就是不斷回收被過繼來的子行程。Linux 3.4 之後還有 **subreaper** 機制：一個 process 可以用 `prctl(PR_SET_CHILD_SUBREAPER)` 宣告「我底下的孤兒交給我」，systemd 的使用者 session、容器的 init 程式常這麼做，所以在 Linux 桌面上你可能看到孤兒的新 PPID 不是 1。

```text
 父程序先結束：                       子程序先結束、父程序不 waitpid：

  bash                                 thumbd（還活著，從不 waitpid）
   └─ thumbd  ← 結束                     ├─ heic-convert  Z <defunct>
        └─ heic-convert                  ├─ heic-convert  Z <defunct>
              │                          └─ ...（兩萬個）
              ▼ 過繼                    
  PID 1（或 subreaper）                 只要 thumbd 不死、不 waitpid，
   └─ heic-convert ← 結束後由 PID 1 回收  它們就永遠留著
```

左邊的情況通常無害，因為 PID 1 會負責回收。右邊才是 `thumbd` 的狀況：父行程是長期執行的服務，它活著，所以子行程不會被過繼；它又從不呼叫 `waitpid`，所以 zombie 一個個累積。殺掉 zombie 本身沒用（它已經死了，`kill -9` 對它無效），唯一的解法是讓父行程回收，或讓父行程結束、交給 PID 1 回收。

> [!warning] 常見誤解
> 「zombie 不佔記憶體，所以無害。」每個 zombie 佔一個 PID。Linux 傳統的 `pid_max` 預設是 32768（核心數很多的機器上，kernel 會依 CPU 數自動調高），較新的發行版常由 systemd 調高到 4194304，容器的 cgroup 通常也有 `pids.max` 限制。PID 用完之後，整台機器（或整個容器）的任何程式都不能再 fork，連 SSH 登入都可能失敗。`thumbd` 的 `fork: Resource temporarily unavailable` 就是 `EAGAIN`：process 數量到上限了。

## 21.6 sleep 與 pause：讓 process 暫停

有兩個簡單的函式能讓 process 主動停下來，它們在後面的程式和第 22 章都會用到：

```c
#include <unistd.h>
unsigned int sleep(unsigned int secs);   /* 睡 secs 秒；被 signal 打斷時提早返回，回傳剩下的秒數 */
int pause(void);                         /* 一直睡，直到收到一個會呼叫 handler 或終止程式的 signal */
```

`sleep` 正常睡完時回傳 0；如果睡到一半收到 signal 而被叫醒，回傳「還剩幾秒沒睡」。這是第一個讓你看到「signal 會打斷 system call」的例子，第 22 章會解釋為什麼。需要更細的時間可以用 POSIX 的 `nanosleep`，它也有同樣的「被打斷時回報剩餘時間」設計。本章程式為了簡短使用 `usleep`（微秒），它是舊的 BSD 函式，Linux 與 macOS 都提供，但新程式碼建議用 `nanosleep`。

`pause` 則沒有時間限制：它讓 process 一直睡到有 signal 抵達。21.10 節的 zombie 實驗就用它製造一個「永遠在睡、等著被 `SIGTERM` 叫醒」的子行程。要注意，用 `pause` 等待「某件事發生」有一個經典的 race condition，第 22 章會介紹正確的替代品 `sigsuspend`。

在 `thumbd` 裡，這兩個函式不該出現在處理請求的路徑上：worker thread 呼叫 `sleep` 會讓那條 thread 什麼事都不做。它們適合用在測試、重試的退避（backoff）或簡單的工具程式。

## 21.7 execve：把 process 換成另一個程式

fork 出來的子行程執行的還是父行程的程式。要讓它變成 `heic-convert`，需要 **`execve`**：在目前的 process 裡**載入並執行一個新程式**，取代原本的程式碼、資料、heap 與 stack。

```c
#include <unistd.h>
int execve(const char *path, char *const argv[], char *const envp[]);
/* 成功時不會回傳；失敗時回傳 -1 並設定 errno */
```

三個參數分別是：

- `path`：要執行的檔案路徑，例如 `"/usr/bin/heic-convert"`。`execve` 不會幫你搜尋 `PATH`。
- `argv`：傳給新程式的命令列參數，一個以 `NULL` 結尾的字串指標陣列。慣例上 `argv[0]` 是程式名稱，它不一定等於 `path`，`ps` 顯示的名稱就是從這裡來的。
- `envp`：環境變數，一樣是以 `NULL` 結尾的陣列，每個字串的格式是 `"NAME=value"`。

`execve` 最特別的地方是**成功時不會回傳**：呼叫它的那段程式已經不存在了，沒有地方可以回去。所以 `execve` 後面的程式碼只會在失敗時執行，通常就是印出錯誤並 `_exit`。常見的失敗原因有 `ENOENT`（檔案不存在）、`EACCES`（沒有執行權限）、`ENOEXEC`（不是可執行格式）。Shell 的慣例是：找不到指令回傳 127，找到但無法執行回傳 126。

### 新程式啟動時看到的 stack

`execve` 呼叫 loader（第 19 章）把新程式的程式碼與資料 map 進位址空間，然後在新的 stack 上排好 `argc`、`argv`、`envp`，最後跳到程式的進入點，經過 C runtime 的初始化之後呼叫 `main(int argc, char **argv, char **envp)`。以執行 `heic-convert in.heic out.png` 為例，新程式剛啟動時 stack 頂端大致長這樣：

```text
 高位址
 ┌────────────────────────────────────┐ ← stack 底部
 │ "LANG=C.UTF-8\0" "PATH=/usr/bin\0"  │   環境變數字串本身
 │ "heic-convert\0" "in.heic\0"        │   參數字串本身
 │ "out.png\0"                         │
 ├────────────────────────────────────┤
 │ （對齊用的 padding、auxv 等）        │
 ├────────────────────────────────────┤
 │ envp[2] = NULL                     │
 │ envp[1] ─────────▶ "PATH=..."       │
 │ envp[0] ─────────▶ "LANG=..."       │ ← envp 指向這裡
 ├────────────────────────────────────┤
 │ argv[3] = NULL                     │
 │ argv[2] ─────────▶ "out.png"        │
 │ argv[1] ─────────▶ "in.heic"        │
 │ argv[0] ─────────▶ "heic-convert"   │ ← argv 指向這裡
 ├────────────────────────────────────┤
 │ argc = 3                           │ ← 程式進入點時的 %rsp
 └────────────────────────────────────┘
 低位址
```

從圖可以看出 `argv` 和 `envp` 都只是「指向字串的指標陣列」，兩者都以 `NULL` 指標作為結尾，`argc` 只是方便用的計數。`getenv("PATH")` 就是在 `envp` 這個陣列裡線性搜尋。環境變數與參數的總大小有上限（Linux 上可用 `getconf ARG_MAX` 查），超過時 `execve` 回傳 `E2BIG`，這就是 `rm *` 在檔案太多時出現「Argument list too long」的原因。

### exec 家族

C 函式庫在 `execve` 之上包了好幾個方便的版本，名字的字尾告訴你差別：`l` 表示參數用可變長度的 list 傳（`execl("ls", "ls", "-l", NULL)`），`v` 表示用陣列（vector）傳，`p` 表示會在 `PATH` 中搜尋程式，`e` 表示可以自己指定環境變數。

| 函式 | 參數形式 | 搜尋 `PATH` | 環境變數 |
|---|---|---|---|
| `execve(path, argv, envp)` | 陣列 | 否 | 自己給 |
| `execv(path, argv)` | 陣列 | 否 | 沿用目前的 `environ` |
| `execvp(file, argv)` | 陣列 | 是 | 沿用 |
| `execl(path, arg0, ..., NULL)` | list | 否 | 沿用 |
| `execlp(file, arg0, ..., NULL)` | list | 是 | 沿用 |
| `execle(path, arg0, ..., NULL, envp)` | list | 否 | 自己給 |

### 什麼會跨過 exec 保留下來

exec 換掉了程式，但**沒有換掉 process**。PID、PPID、目前工作目錄、user ID、資源限制（rlimit）、signal mask、被設為忽略的 signal、以及**打開的 file descriptor**，全部保留。被重設的是：整個位址空間（包括 stdio buffer，所以 exec 前沒 flush 的輸出會消失）、所有 signal handler（因為 handler 函式的程式碼已經不在了，所以恢復成預設動作）、所有執行緒（只剩一條）。

保留 file descriptor 是 shell 能做 I/O 重導的基礎（第 27 章），但也是資源洩漏的來源：`thumbd` 打開的 socket 和圖檔，如果沒有特別處理，也會被 `heic-convert` 繼承。正確做法是開檔時加 `O_CLOEXEC` 旗標（或對 socket 用 `SOCK_CLOEXEC`），讓 kernel 在 exec 時自動關閉它們。

## 21.8 fork 加 exec：為什麼要分成兩步

Windows 用一個 `CreateProcess` 就能「建立新 process 並執行指定程式」，Unix 卻要先 `fork` 再 `exec`。這看起來繞遠路，其實是刻意的設計：**fork 和 exec 之間的那段時間，子行程還在執行父行程的程式碼，可以用一般的 system call 調整自己的環境**，再交棒給新程式。

```text
 父程序                         子程序（fork 之後、exec 之前）
 ───────                        ─────────────────────────────
 pid = fork() ──────────────▶  ① dup2(fd, 1)         把 stdout 導到檔案（第 27 章）
   │                            ② close 不需要的 fd     例如 pipe 用不到的那一端
   │                            ③ setpgid(0, 0)       自己成立新的 process group（第 22 章）
   │                            ④ chdir、setrlimit    調整目錄、限制 CPU 時間或記憶體
   │                            ⑤ sigprocmask         恢復 signal mask（第 22 章）
   │                            ⑥ execve(...)  ──▶    變成新程式，繼承以上設定
   ▼
 waitpid(pid, ...)
```

Shell 的 `ls > out.txt`、`cmd1 | cmd2`、`ulimit -v 1000000; ./prog`，全部都是靠這個空檔做到的。新程式完全不需要知道自己的 stdout 被導到了檔案，它只是照常寫 descriptor 1。

### 多執行緒程式裡的 fork

`thumbd` 是 thread pool 架構，在 worker thread 裡呼叫 fork 時要特別小心。子行程只複製了呼叫 fork 的那一條 thread，其他 thread 在子行程裡**直接消失**，但它們當時持有的鎖狀態被原封不動地複製了。如果 fork 的瞬間另一條 thread 正在 `malloc` 裡面、拿著 allocator 的鎖，子行程裡那把鎖就永遠是鎖住的，子行程一呼叫 `malloc`（或 `printf`，它內部可能 malloc）就會永遠卡住。

因此 POSIX 規定：多執行緒程式 fork 之後，子行程在 exec 之前**只能呼叫 async-signal-safe 的函式**（第 22 章會列出這份清單，`dup2`、`close`、`execve`、`_exit` 都在其中，`malloc`、`printf` 不在）。實務上的守則是：在子行程裡只做 21.8 節圖中那幾件事，然後立刻 exec，所有需要 malloc 的準備工作（例如組好 `argv` 陣列）都在 fork **之前**完成。

### 更現代的選擇：posix_spawn

POSIX 另外定義了 **`posix_spawn`**，把「fork、調整環境、exec」包成一個呼叫，用 `posix_spawn_file_actions_t` 描述要做的 `dup2`、`close`。它的實作可以使用 `vfork` 或 Linux 的 `clone(CLONE_VM | CLONE_VFORK)`，讓子行程暫時借用父行程的位址空間，完全不必複製 page table，對 RSS 很大的服務特別有利。glibc、musl 和 macOS 都有實作，Python 的 `subprocess` 在條件允許時也會改用這類路徑。對 `thumbd` 這種大記憶體、多執行緒的服務，`posix_spawn` 通常是比手寫 fork 加 exec 更安全的選擇；但理解 fork 與 exec 仍然必要，因為 `posix_spawn` 的語意就是用它們定義的，除錯時也看得到它們。

## 21.9 寫一個迷你 shell

有了 `fork`、`execve`、`waitpid`，我們已經能寫出 Unix 世界最經典的程式：**shell**（命令列解譯器）。Shell 本身是一個迴圈：讀一行指令、解析成 `argv`、如果是內建指令就自己做，否則 fork 一個子行程去 exec 那個程式，再決定要不要等它。

```text
 ┌──────────────────────────────────────────────────────┐
 │ 迴圈：                                                 │
 │   回收已結束的背景工作（waitpid + WNOHANG）              │
 │   印出提示字元，讀一行                                   │
 │   解析成 argv；最後一個字是 & 嗎？→ 背景執行              │
 │        │                                              │
 │        ├─ 內建指令（cd、exit）→ shell 自己執行           │
 │        │                                              │
 │        └─ 外部指令 → fork()                            │
 │                 ├─ 子程序：execvp(argv[0], argv)        │
 │                 │          失敗 → 印錯誤、_exit(127)    │
 │                 └─ 父程序：前景 → waitpid 等它結束       │
 │                            背景 → 印出 PID，不等         │
 └──────────────────────────────────────────────────────┘
```

為什麼 `cd` 一定要是內建指令？因為目前工作目錄是 process 的屬性。如果 shell fork 一個子行程去執行 `chdir`，改變的是子行程的目錄，子行程結束後 shell 自己的目錄完全沒變。同理，`exit`、`export`（改 shell 自己的環境變數）、`ulimit` 都必須是內建的。

下面是一個大約 80 行的實作。為了讓輸出可以重現，它預設執行一段內建的指令腳本；加上任意參數執行（例如 `./minish -`）則改從鍵盤讀入。

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define MAXARGS 16

/* 把一行切成 argv（只認空白，不處理引號）；回傳是否要在背景執行。 */
static int parse(char *line, char **argv) {
    int argc = 0;
    for (char *tok = strtok(line, " \t\n"); tok && argc < MAXARGS - 1; tok = strtok(NULL, " \t\n"))
        argv[argc++] = tok;
    argv[argc] = NULL;
    int bg = argc > 0 && strcmp(argv[argc - 1], "&") == 0;
    if (bg) argv[--argc] = NULL;
    return bg;
}

static void report(pid_t pid, int status, const char *tag) {
    if (WIFEXITED(status))
        printf("[%s %d] exit %d\n", tag, (int)pid, WEXITSTATUS(status));
    else if (WIFSIGNALED(status))
        printf("[%s %d] killed by signal %d\n", tag, (int)pid, WTERMSIG(status));
}

/* 每次顯示提示字元前，順手回收已經結束的背景工作，避免 zombie。 */
static void reap_background(void) {
    int status;
    pid_t pid;
    while ((pid = waitpid(-1, &status, WNOHANG)) > 0)
        report(pid, status, "bg done");
}

static int builtin(char **argv) {
    if (strcmp(argv[0], "exit") == 0) exit(0);
    if (strcmp(argv[0], "cd") == 0) {      /* cd 必須在 shell 自己的 process 裡做 */
        if (chdir(argv[1] ? argv[1] : "/") < 0) perror("cd");
        return 1;
    }
    return 0;
}

static void eval(char *line) {
    char *argv[MAXARGS];
    int bg = parse(line, argv);
    if (argv[0] == NULL || builtin(argv)) return;
    fflush(stdout);                        /* fork 前清空，避免子程序重複輸出 */
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); return; }
    if (pid == 0) {
        execvp(argv[0], argv);             /* 成功就不會回來 */
        fprintf(stderr, "minish: %s: %s\n", argv[0], strerror(errno));
        _exit(127);                        /* 慣例：找不到指令回傳 127 */
    }
    if (bg) { printf("[bg %d] %s\n", (int)pid, argv[0]); return; }
    int status;
    if (waitpid(pid, &status, 0) == pid) report(pid, status, "fg");
}

int main(int argc, char **argv) {
    (void)argv;
    const char *script[] = {
        "echo hello from a child process", "cd /", "pwd",
        "sleep 0.2 &", "echo the shell did not wait for sleep",
        "false", "no_such_command", "sleep 0.3", "exit", NULL };
    char line[256];
    for (int i = 0;; i++) {
        reap_background();
        printf("minish> ");
        if (argc > 1) {                    /* ./minish - ：改從鍵盤讀 */
            fflush(stdout);
            if (!fgets(line, sizeof line, stdin)) break;
        } else {
            if (!script[i]) break;
            snprintf(line, sizeof line, "%s", script[i]);
            printf("%s\n", line);
        }
        eval(line);
    }
    return 0;
}
```

在 macOS arm64（Apple clang 21）上，以 `cc -std=c17 -O1 -Wall -Wextra` 編譯後執行：

```text
minish> echo hello from a child process
hello from a child process
[fg 81735] exit 0
minish> cd /
minish> pwd
/
[fg 81736] exit 0
minish> sleep 0.2 &
[bg 81737] sleep
minish> echo the shell did not wait for sleep
the shell did not wait for sleep
[fg 81738] exit 0
minish> false
[fg 81739] exit 1
minish> no_such_command
minish: no_such_command: No such file or directory
[fg 81740] exit 127
minish> sleep 0.3
[fg 81741] exit 0
[bg done 81737] exit 0
minish> exit
```

逐段對照：

1. `echo hello...`：shell fork 出 PID 81735，子行程 exec 成 `/bin/echo` 印出文字；shell 用 `waitpid` 等到它，回報 exit 0。
2. `cd /` 沒有產生任何子行程，它是內建指令；接著外部的 `pwd` 印出 `/`，證明 shell 自己的目錄改變了，而這個目錄被 fork 出的子行程繼承。
3. `sleep 0.2 &` 只印出背景 PID 就回到提示字元，shell 沒有等它，所以下一個 `echo` 立刻執行。
4. `false` 是一個什麼都不做、只回傳 1 的程式，shell 正確解讀出 exit 1。
5. `no_such_command`：子行程的 `execvp` 失敗，印出錯誤後以 127 結束，和 bash 的慣例相同。
6. 背景的 `sleep` 在某個時間點結束，變成 zombie；shell 在下一次顯示提示字元前用 `WNOHANG` 回收它，印出 `bg done`。它出現在哪一行取決於排程與時間，每次執行可能不同。

這個 shell 刻意省略了很多東西：它不處理引號、pipe（`|`）、重導（`>`），也沒有 job control（`Ctrl-C` 只該殺前景工作、`Ctrl-Z` 暫停、`fg`／`bg` 切換）。它回收背景工作的方式也很粗糙：只在顯示提示字元前檢查一次，如果使用者一直不按 Enter，結束的背景工作就一直是 zombie。真正的 shell 用 `SIGCHLD` signal 在子行程結束的當下得到通知，並用 process group 管理前景與背景，這些要等第 22 章介紹 signal 之後才能做對。

## 21.10 動手做：觀察 fork、zombie、孤兒與 exec

這一節用四個小程式，把前面講的語意一一變成看得到的輸出。所有程式都在 macOS arm64（Apple clang 21）上以 `cc -std=c17 -O1 -Wall -Wextra` 編譯，輸出導向 pipe（`./prog | cat`），以便重現 fully buffered 的情況。程式第一行的 `_DEFAULT_SOURCE` 是給 Linux 的 glibc 看的：在嚴格的 `-std=c17` 下，glibc 預設不宣告 `usleep` 等 POSIX 與 BSD 函式，這個巨集把它們打開；macOS 會忽略它。

### 程式一：fork 的回傳值、buffer 複製與 process graph

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

/* 實驗一：fork 回傳兩次，父子各有一份變數。 */
static void demo_fork_return(void) {
    int counter = 100;
    fflush(stdout);                       /* 先清空 buffer，原因見實驗二 */
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); exit(1); }
    if (pid == 0) {                       /* 子程序：fork 回傳 0 */
        counter += 1;
        printf("[child ] fork 回傳 0，counter = %d\n", counter);
        exit(0);                          /* 子程序一定要自己結束 */
    }
    waitpid(pid, NULL, 0);                /* 父程序：等子程序先印完 */
    counter -= 1;
    printf("[parent] fork 回傳子程序 PID，counter = %d\n", counter);
}

/* 實驗二：fork 之前留在 stdio buffer 裡的資料，會被複製一份。 */
static void demo_buffer(int flush_first) {
    printf("before fork (flush_first=%d)\n", flush_first);
    if (flush_first) fflush(stdout);
    pid_t pid = fork();
    if (pid == 0) exit(0);                /* exit 會 flush 子程序那份 buffer */
    waitpid(pid, NULL, 0);
    fflush(stdout);
}

/* 實驗三：連續兩次 fork，數一數有幾個 process 走到最後一行。 */
static void demo_two_forks(void) {
    fflush(stdout);
    int fds[2];
    if (pipe(fds) < 0) { perror("pipe"); exit(1); }
    pid_t a = fork();
    pid_t b = fork();
    char line[64];
    int n = snprintf(line, sizeof line, "  a=%s b=%s\n",
                     a == 0 ? "0  " : ">0 ", b == 0 ? "0  " : ">0 ");
    if (write(fds[1], line, (size_t)n) != n) _exit(1);  /* 一次 write 一整行，不會交錯 */
    if (b == 0) exit(0);
    waitpid(b, NULL, 0);
    if (a == 0) exit(0);
    waitpid(a, NULL, 0);
    close(fds[1]);
    char buf[256];
    ssize_t got = read(fds[0], buf, sizeof buf - 1);
    buf[got > 0 ? got : 0] = '\0';
    printf("兩次 fork 之後，共有 %d 個 process 回報：\n%s",
           (int)(got / (ssize_t)strlen(line)), buf);
}

int main(void) {
    printf("=== 實驗一 ===\n");
    demo_fork_return();
    printf("=== 實驗二 ===\n");
    fflush(stdout);
    demo_buffer(0);
    demo_buffer(1);
    printf("=== 實驗三 ===\n");
    demo_two_forks();
    return 0;
}
```

```text
=== 實驗一 ===
[child ] fork 回傳 0，counter = 101
[parent] fork 回傳子程序 PID，counter = 99
=== 實驗二 ===
before fork (flush_first=0)
before fork (flush_first=0)
before fork (flush_first=1)
=== 實驗三 ===
兩次 fork 之後，共有 4 個 process 回報：
  a=>0  b=>0 
  a=>0  b=0  
  a=0   b=>0 
  a=0   b=0  
```

逐步解說：

1. **實驗一**：子行程把自己的 `counter` 加 1 得到 101，父行程減 1 得到 99。兩者都從 100 開始，因為 fork 時複製了當下的值；之後各改各的，互不影響，這就是「獨立的位址空間」。父行程先 `waitpid` 才印，所以子行程那行一定在前。
2. **實驗二**：`flush_first=0` 那行印了兩次，`flush_first=1` 只印一次。因為輸出是 pipe，stdout 是 fully buffered，fork 時那行字還在 buffer 裡，被複製到子行程；子行程 `exit` 時 flush 一次，父行程之後又 flush 一次。先 `fflush` 再 fork，buffer 已經是空的，就不會重複。如果直接在終端機執行，stdout 是 line buffered，兩種情況都只會印一次，這正是這類 bug 在開發機上看不到的原因。
3. 實驗一開頭的 `fflush(stdout)` 也是同一個原因：沒有它，`=== 實驗一 ===` 這行也會被子行程複製，印兩次。（筆者第一次寫這段程式時就踩到了。）
4. **實驗三**：四個 process 各自用一次 `write` 把一行寫進同一個 pipe，主行程最後一次讀出來。四行代表 process graph 的四條線。行的順序每次執行都可能不同，因為四個 process 是並行的；這裡顯示的只是其中一次的結果。之所以用 `write` 而不是 `printf`，是要避開 buffer 複製的問題，並確保每一行是一次完整的寫入。

### 程式二：親眼看到 zombie，再把它回收

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

/* 用 fork + exec 呼叫系統的 ps，看指定 PID 的狀態。 */
static void show_ps(pid_t target, const char *label) {
    char pidstr[16];
    snprintf(pidstr, sizeof pidstr, "%d", (int)target);
    printf("--- %s ---\n", label);
    fflush(stdout);                        /* exec 前先清空 buffer，避免重複輸出 */
    pid_t pid = fork();
    if (pid == 0) {
        char *argv[] = {"ps", "-o", "pid,ppid,stat,comm", "-p", pidstr, NULL};
        execvp("ps", argv);
        perror("execvp");                  /* 只有 exec 失敗才會走到這裡 */
        _exit(127);
    }
    waitpid(pid, NULL, 0);
}

static void describe(pid_t pid, int status) {
    if (WIFEXITED(status))
        printf("回收 PID %d：正常結束，exit status = %d\n", (int)pid, WEXITSTATUS(status));
    else if (WIFSIGNALED(status))
        printf("回收 PID %d：被 signal %d 終止\n", (int)pid, WTERMSIG(status));
}

int main(void) {
    printf("parent PID = %d\n", (int)getpid());
    fflush(stdout);
    pid_t quick = fork();
    if (quick == 0) _exit(3);              /* 子程序立刻以 3 結束 */

    pid_t sleeper = fork();
    if (sleeper == 0) { pause(); _exit(0); }   /* 子程序一直睡，等 signal */

    usleep(200 * 1000);                    /* 給 quick 時間結束 */
    show_ps(quick, "quick 已結束、還沒 waitpid");

    int status;
    pid_t r = waitpid(quick, &status, 0);
    describe(r, status);
    show_ps(quick, "waitpid 之後");

    kill(sleeper, SIGTERM);                /* 送 SIGTERM 給還在睡的子程序 */
    r = waitpid(sleeper, &status, 0);
    describe(r, status);

    r = waitpid(-1, &status, WNOHANG);     /* 已經沒有子程序了 */
    printf("再呼叫一次 waitpid：回傳 %d（沒有子程序可等）\n", (int)r);
    return 0;
}
```

```text
parent PID = 81618
--- quick 已結束、還沒 waitpid ---
  PID  PPID STAT COMM
81629 81618 Z    <defunct>
回收 PID 81629：正常結束，exit status = 3
--- waitpid 之後 ---
  PID  PPID STAT COMM
回收 PID 81630：被 signal 15 終止
再呼叫一次 waitpid：回傳 -1（沒有子程序可等）
```

1. `quick` 子行程以 `_exit(3)` 立刻結束，但父行程還沒 `waitpid`。這時用 fork 加 exec 呼叫系統的 `ps`，看到它的 STAT 是 `Z`、名稱變成 `<defunct>`：記憶體已經釋放，只剩一筆等待回收的紀錄。
2. `waitpid` 回傳它的 PID，`WIFEXITED` 為真，`WEXITSTATUS` 是 3，和 `_exit(3)` 對得上。之後再查 `ps`，只剩標題列，紀錄已經被 kernel 刪除。
3. `sleeper` 子行程一直在 `pause`。父行程送 `SIGTERM` 給它，`SIGTERM` 的預設動作是終止 process，所以 `WIFSIGNALED` 為真、`WTERMSIG` 是 15。
4. 所有子行程都回收之後，再呼叫 `waitpid(-1, ..., WNOHANG)` 回傳 −1（errno 為 `ECHILD`），表示「你沒有子行程了」。注意這和回傳 0（「有子行程，但都還沒結束」）意義不同，寫回收迴圈時要分清楚。
5. `show_ps` 本身就是一個小型的 fork、exec、wait 範例，而且在 fork 之前 `fflush`，避免重複輸出。

### 程式三：孤兒被過繼

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    int fds[2];
    if (pipe(fds) < 0) { perror("pipe"); return 1; }
    pid_t middle = fork();
    if (middle == 0) {                     /* 中間層：生一個孫程序後立刻結束 */
        if (fork() == 0) {                 /* 孫程序 */
            pid_t before = getppid();
            for (int i = 0; i < 100 && getppid() == before; i++)
                usleep(10 * 1000);         /* 等中間層結束 */
            dprintf(fds[1], "孫程序：原本的 parent 是 %d，現在 getppid() = %d\n",
                    (int)before, (int)getppid());
            _exit(0);
        }
        usleep(50 * 1000);
        _exit(0);                          /* 中間層結束，孫程序變成孤兒 */
    }
    close(fds[1]);
    waitpid(middle, NULL, 0);
    printf("main：已回收中間層 %d\n", (int)middle);
    char buf[200];
    ssize_t n = read(fds[0], buf, sizeof buf - 1);   /* 等孫程序回報 */
    if (n > 0) { buf[n] = '\0'; printf("%s", buf); }
    return 0;
}
```

```text
main：已回收中間層 81695
孫程序：原本的 parent 是 81695，現在 getppid() = 1
```

中間層 process 生了孫行程之後立刻結束，孫行程變成孤兒，它的 `getppid()` 從中間層的 PID 變成 1（macOS 的 launchd）。在 Linux 上，如果你的桌面 session 或容器 runtime 設定了 subreaper，看到的會是那個 process 的 PID，而不是 1。程式用 pipe 讓孫行程把結果傳回最外層，因為最外層並不是孫行程的父行程，無法 `waitpid` 它；孫行程最後由接手的 PID 1 回收。

### 程式四：exec 換程式但不換 PID

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    fflush(stdout);
    pid_t pid = fork();
    if (pid == 0) {
        printf("child before exec: pid=%d\n", (int)getpid());
        fflush(stdout);                    /* exec 會丟掉 stdio buffer，先寫出去 */
        char *argv[] = {"sh", "-c", "echo \"after exec:  pid=$$ argv0=$0 mode=$THUMBD_MODE\"", NULL};
        char *envp[] = {"THUMBD_MODE=heic", "PATH=/usr/bin:/bin", NULL};
        execve("/bin/sh", argv, envp);     /* 換掉整個程式；成功就不會回來 */
        perror("execve");
        _exit(127);
    }
    int status;
    waitpid(pid, &status, 0);
    printf("parent: child %d exited with %d\n", (int)pid, WEXITSTATUS(status));
    return 0;
}
```

```text
child before exec: pid=81705
after exec:  pid=81705 argv0=sh mode=heic
parent: child 81705 exited with 0
```

1. 子行程在 exec 之前印出自己的 PID 81705（實際數字每次不同）。
2. exec 之後，新程式是 `/bin/sh`，它用 `$$` 印出自己的 PID，仍然是同一個數字：exec 沒有建立新 process。
3. `$0` 是 `sh`，來自我們給的 `argv[0]`；`$THUMBD_MODE` 是 `heic`，來自我們給的 `envp`。新程式看不到父行程原本的任何其他環境變數，因為 `execve` 只傳入我們指定的陣列。
4. exec 之前的 `fflush` 不能省：exec 會丟棄整個位址空間，包括還沒寫出去的 stdio buffer。

## 21.11 在工作上怎麼用

### 修好 `thumbd` 的外部工具呼叫

回到故事。小安的版本漏掉了 `waitpid`，而且沒有處理工具卡住的情況。老周和小安一起改寫成下面這個函式：它保證每一個 fork 出來的子行程都會被回收，並在逾時時先禮後兵：先送 `SIGTERM` 讓工具有機會清理，0.5 秒後還沒結束就送 `SIGKILL`。

```c
#define _DEFAULT_SOURCE   /* 讓 glibc 在 -std=c17 下也宣告 POSIX 函式 */
#include <signal.h>
#include <stdio.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

/* 執行外部工具，最多等 limit 秒；逾時先 SIGTERM、再 SIGKILL。一定回收子程序。 */
static int run_with_timeout(char *const argv[], double limit) {
    fflush(stdout);
    pid_t pid = fork();
    if (pid < 0) return -1;                         /* EAGAIN：process 數量到上限 */
    if (pid == 0) { execvp(argv[0], argv); _exit(127); }

    double start = now();
    int status, sent_term = 0;
    for (;;) {
        pid_t r = waitpid(pid, &status, WNOHANG);   /* 不阻塞地問：結束了嗎？ */
        if (r == pid) break;
        double elapsed = now() - start;
        if (!sent_term && elapsed > limit) { kill(pid, SIGTERM); sent_term = 1; }
        else if (sent_term && elapsed > limit + 0.5) kill(pid, SIGKILL);
        usleep(10 * 1000);
    }
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return 128 + WTERMSIG(status);                  /* 和 shell 的慣例一樣 */
}

int main(void) {
    char *ok[] = {"true", NULL};
    char *slow[] = {"sleep", "5", NULL};
    char *missing[] = {"heic-convert-not-installed", NULL};
    printf("true        → %d\n", run_with_timeout(ok, 0.3));
    printf("sleep 5     → %d（逾時被 SIGTERM 終止）\n", run_with_timeout(slow, 0.3));
    printf("不存在的工具 → %d\n", run_with_timeout(missing, 0.3));
    return 0;
}
```

```text
true        → 0
sleep 5     → 143（逾時被 SIGTERM 終止）
不存在的工具 → 127
```

輸出的三行分別對應三種結果：正常結束得到 0；`sleep 5` 超過 0.3 秒的限制被 `SIGTERM` 終止，依 shell 慣例回報 128 + 15 = 143；找不到工具時 exec 失敗，子行程以 127 結束。這個版本用 `WNOHANG` 每 10 ms 輪詢一次，對 `thumbd` 這種一次只有少數外部工具在跑的情境足夠；需要大量並行的服務，可以改用 `SIGCHLD` 通知（第 22 章），或在 Linux 5.3 之後用 `pidfd_open` 取得一個代表子行程的 file descriptor，放進 epoll 一起等待（第 30 章）。

上線前的檢查清單：

- 每一個 `fork` 成功的路徑，都有一個對應的 `waitpid`，包括錯誤處理與逾時的路徑。
- `fork` 失敗（回傳 −1）時要處理 `EAGAIN`，回報錯誤而不是當成子行程繼續執行。
- 子行程 exec 失敗後用 `_exit`，不用 `exit`。
- 多執行緒程式中，子行程在 exec 前只呼叫 async-signal-safe 函式；`argv` 在 fork 之前準備好。
- 服務自己打開的檔案與 socket 都加 `O_CLOEXEC`，避免外部工具繼承。
- 有逾時與升級機制（`SIGTERM` 之後才 `SIGKILL`），並記錄工具的結束狀態或 signal，方便追查。
- 外部工具的參數來自使用者輸入時，不要經過 `/bin/sh -c` 拼字串，直接用 `execvp` 傳 `argv` 陣列，避免 command injection。

### 診斷 zombie 累積

當監控顯示 process 數量一直上升，或 `ps` 出現大量 `<defunct>`：

```bash
# 列出所有 zombie 與它們的父程序
ps -eo pid,ppid,stat,comm | awk '$3 ~ /^Z/'

# 數一數每個父程序底下有幾個 zombie，找出元兇
ps -eo ppid,stat | awk '$2 ~ /^Z/ {print $1}' | sort | uniq -c | sort -rn | head

# 看系統的 PID 上限，與容器的 pids 限制（cgroup v2）
cat /proc/sys/kernel/pid_max
cat /sys/fs/cgroup/pids.max /sys/fs/cgroup/pids.current

# 追蹤一個服務的 fork／exec／wait 呼叫（-f 一併追蹤子程序）
strace -f -e trace=%process -p <PID>
```

判斷流程是：先找出 zombie 的父行程是誰；如果父行程是你的服務，就是程式漏了 `waitpid`；如果父行程是 PID 1，而 PID 1 不是一個真正的 init（容器裡常見），就是下一節的問題。短期止血可以重啟父行程，讓 zombie 被過繼給 PID 1 回收；長期一定要修程式。

### 容器裡的 PID 1

在 Docker 或 Kubernetes 裡，容器的進入點程式就是容器內的 PID 1。如果你直接用 `thumbd` 當進入點，它就要負起 init 的責任：回收所有被過繼過來的孤兒。`thumbd` 呼叫的 `heic-convert` 如果自己又 fork 了子行程然後先結束，那些孫行程會被過繼給 `thumbd`，而 `thumbd` 只會 `waitpid` 自己記得的 PID，孫行程就變成永遠回收不了的 zombie。此外，PID 1 對 signal 的處理也有特殊規則（第 22 章）。業界的標準解法是在容器裡放一個極小的 init，例如 `tini`（`docker run --init` 就是用它），讓它當 PID 1，負責回收與轉送 signal，`thumbd` 則當它的子行程。

### 高階語言裡的同一件事

你在 Python、Go、Java 啟動子行程時，底下做的就是本章的事。理解這一點，才能看懂這些 API 為什麼要求你呼叫 `wait`：

| 語言／API | 底層對應 | 不回收時會怎樣 |
|---|---|---|
| Python `subprocess.run` | fork／exec（或 `posix_spawn`）＋ `waitpid` | `run` 會等待並回收，安全 |
| Python `subprocess.Popen` | 只做 fork／exec | 必須呼叫 `wait()` 或 `communicate()`，否則子行程會以 zombie 留著，直到物件被回收或下次建立 `Popen` 時才被順便清理 |
| Go `exec.Command(...).Start()` | fork／exec | 必須呼叫 `cmd.Wait()` |
| Java `ProcessBuilder.start()` | `posix_spawn` 或 `vfork`（依版本與平台） | JDK 內部有一條 reaper thread 負責 `waitpid`，不會留 zombie；但仍要讀完 stdout，否則子行程可能卡在寫滿的 pipe |
| C `system()` | fork ＋ `execl("/bin/sh", "sh", "-c", cmd)` ＋ `waitpid` | 會回收，但經過 shell，有 injection 風險，也會阻塞呼叫者 |

## 21.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| `ps` 出現大量 `<defunct>`，最後 `fork` 回傳 `EAGAIN` | 父行程沒有 `waitpid` 回收子行程 | `ps -eo pid,ppid,stat,comm` 找出 zombie 的 PPID | 每個子行程都要回收：同步 `waitpid`、`WNOHANG` 迴圈，或 `SIGCHLD` handler |
| 輸出到檔案時某些 log 行出現兩次，終端機上卻正常 | fork 前 stdio buffer 還有資料，被父子各寫一次 | 把輸出導到 pipe（例如接到 `cat`）就能重現 | fork 前 `fflush(stdout)`；子行程用 `_exit` 結束 |
| 子行程跑完後，父行程後面的程式碼被執行了兩次 | 子行程的分支沒有 `exit`，繼續往下執行父行程的程式碼 | 在可疑位置印出 `getpid()` | 子行程的分支最後一定要 `_exit` 或 `exit`；exec 失敗後也要 |
| fork 之後子行程偶爾卡死不動 | 多執行緒程式 fork 時其他 thread 持有鎖（例如 malloc 的鎖），子行程在 exec 前呼叫了 `malloc`／`printf` | 用 `gdb -p` 附加到卡住的子行程看 `bt`，常停在鎖的函式裡 | fork 前準備好所有資料，子行程只呼叫 async-signal-safe 函式後立刻 exec；或改用 `posix_spawn` |
| 外部工具執行時，服務的 port 被佔住、無法重啟 | 子行程繼承了服務的 listening socket | `lsof -i :<port>` 看到工具也持有那個 socket | 開 socket 與檔案時加 `SOCK_CLOEXEC`／`O_CLOEXEC` |
| `execvp` 失敗，`errno` 是 `ENOENT`，但檔案明明存在 | `PATH` 被改過或 `envp` 沒帶 `PATH`；或腳本的 shebang 指到不存在的直譯器 | `strace -f -e execve` 看實際嘗試的路徑 | 用絕對路徑；檢查 shebang 第一行 |
| 容器裡 zombie 越來越多，但程式有 `waitpid` | 程式是容器的 PID 1，孫行程被過繼給它，它卻只等自己記得的 PID | `ps` 顯示 zombie 的 PPID 是 1 | 用 `tini` 或 `docker run --init`；或用 `waitpid(-1, ...)` 回收所有子行程 |

## 21.13 動手練習

1. **手算**：下面的程式會印出幾個 `x`？畫出 process graph 再回答。

   ```c
   for (int i = 0; i < 3; i++)
       fork();
   printf("x\n");
   ```

   （答案：8 個。迴圈執行 3 次 fork，每次 process 數量加倍，2^3 = 8。驗證方法：把它包進 `main` 執行，輸出用 `| wc -l` 計數；記得注意 21.4 節的 buffer 問題，這裡 `printf` 在 fork 之後，所以不會重複。）

2. **手算**：把第 1 題的 `printf("x\n")` 移到 `fork()` 的前面（在迴圈內），並把輸出導向 pipe。會印出幾個 `x`？（提示：先算每個 process 的 buffer 裡會累積幾個 `x`。答案是 24：最後 8 個 process，每個的 buffer 都累積了 3 個 `x`；在終端機上則是 1 + 2 + 4 = 7 個。用 `./a.out | wc -l` 與直接在終端機執行比較。）
3. 修改 21.9 節的迷你 shell，讓它在每個前景指令結束後，像 bash 一樣把結束狀態存起來，並支援內建指令 `status` 印出上一個指令的結束碼（被 signal 殺掉時用 128 + n）。
4. 修改程式二，讓父行程 fork 5 個子行程，各自以不同的結束狀態（1 到 5）結束，父行程用 `waitpid(-1, &status, 0)` 迴圈回收並印出結果。執行幾次，觀察回收順序是否固定，並解釋為什麼。
5. 在 Linux 上執行 `sleep 1000 &`，然後用 `cat /proc/<PID>/status` 看 `State`、`PPid`；再用 `strace -f -e trace=%process bash -c 'ls > /dev/null'` 觀察 bash 怎麼 fork（實際上是 `clone`）、exec 與 wait。
6. 用 Python 寫一個程式：用 `subprocess.Popen` 啟動 10 個 `sleep 0.1`，故意不呼叫 `wait()`，在 1 秒後用 `ps` 觀察 zombie；再加上 `wait()` 比較結果。

## 本章重點整理

- 每個 process 有 PID 與 PPID，所有 process 串成一棵以 PID 1 為根的樹；一個 process 的狀態可以是 running、stopped 或 terminated。
- `fork` 呼叫一次、回傳兩次：子行程得到 0，父行程得到子行程的 PID，失敗時回傳 −1；子行程從 fork 回傳處繼續執行，而不是從 `main` 開頭。
- fork 後子行程有獨立的位址空間副本（以 copy-on-write 實作），但 file descriptor 指向同一個 open file，共用檔案位移。
- 父子行程並行執行，順序不可預測；process graph 的任何 topological sort 都是可能的輸出順序，需要順序時必須用 `waitpid` 等機制同步。
- stdio buffer 也會被 fork 複製，輸出到檔案或 pipe 時，fork 前沒 flush 的內容會印兩次；fork 與 exec 之前應先 `fflush`。
- process 結束後成為 zombie，保留 PID 與結束狀態，直到父行程用 `waitpid` 回收；zombie 累積會耗盡 PID，讓整台機器無法 fork。
- `waitpid` 的 `pid` 參數決定等誰，`WNOHANG` 讓它不阻塞；`status` 要用 `WIFEXITED`、`WEXITSTATUS`、`WIFSIGNALED`、`WTERMSIG` 解讀，shell 用 128 + n 表示被 signal n 終止。
- 父行程先結束時，子行程成為孤兒，被過繼給 PID 1 或 subreaper 並由它回收；容器的 PID 1 必須負起這個責任。
- `execve` 在同一個 process 中載入新程式，成功時不回傳；PID、file descriptor、工作目錄與 signal mask 會保留，位址空間與 signal handler 會被重設。
- fork 與 exec 分成兩步，讓子行程能在 exec 前重導 I/O、設定 process group 與資源限制，這是 shell 實作重導與 pipe 的基礎。
- 多執行緒程式 fork 後，子行程只有一條 thread，在 exec 前只能呼叫 async-signal-safe 函式；`posix_spawn` 是更安全、通常也更快的替代方案。
- Shell 是一個「讀取、解析、fork、exec、wait」的迴圈；`cd`、`exit` 這類改變 shell 自身狀態的指令必須是內建指令。

## 延伸問答

> [!question]- Q1. 為什麼 fork 讓子行程得到 0、父行程得到子行程的 PID，而不是反過來？
> 因為兩邊需要的資訊不一樣。子行程只有一個父行程，隨時可以呼叫 `getppid()` 查到它，不需要 fork 告訴它；父行程卻可能建立很多子行程，如果不在 fork 回傳的當下拿到 PID，之後就沒有可靠的方法知道剛剛建立的是哪一個，也就無法針對它 `waitpid`、`kill` 或記錄到工作表裡。
>
> 0 被選來代表「你是子行程」，是因為 0 不會是任何一般子行程的 PID（PID 0 在 kernel 內部有特殊用途），也和失敗的 −1 不同。這讓程式用一個簡單的 `if (pid == 0)` 就能分出兩條路徑，是 Unix API 設計很漂亮的地方。

> [!question]- Q2. 程式找錯：下面的程式想讓 3 個子行程各印一行，結果印出了 7 行，哪裡錯了？
> ```c
> for (int i = 0; i < 3; i++) {
>     if (fork() == 0)
>         printf("child %d\n", i);
> }
> ```
>
> 子行程印完之後沒有結束，而是繼續執行迴圈的下一輪，於是它自己也會 fork。i = 0 時產生的子行程會在 i = 1、2 時繼續 fork，它的子行程又會在 i = 2 時 fork。畫 process graph 可以算出：所有子行程總共 1 + 2 + 4 = 7 個，每個都印一行，所以 7 行（這是輸出到終端機的情況；導向 pipe 時，還沒 flush 的 `child 0` 等字串會隨著 fork 被複製，印出的行數更多，筆者在 macOS 上得到 12 行）。
>
> 修法是在子行程的分支最後加上 `_exit(0)`（或 `exit(0)`，前面記得 flush），讓子行程做完自己的事就結束。這是 fork 最常見的錯誤之一，原則是：子行程的分支一定要以 exit 或 exec 收尾，不要讓它「掉進」父行程的程式碼。父行程也要記得最後回收這 3 個子行程。

> [!question]- Q3. Zombie 已經死了，為什麼 `kill -9` 殺不掉它？要怎麼清除？
> Zombie 已經終止，不再執行任何指令，它只是 kernel 裡的一筆紀錄，保存 PID 與結束狀態，等父行程來讀。signal 是送給「正在執行的 process」的通知，zombie 不會再執行，所以 signal 對它沒有任何效果，`SIGKILL` 也一樣。
>
> 清除 zombie 的方法只有一個：讓它被回收。最好的做法是修正父行程，讓它呼叫 `waitpid`；臨時止血可以結束父行程，zombie 會被過繼給 PID 1（或 subreaper），由它回收。工作上要記住：看到 zombie 時，要追的永遠是它的**父行程**，而不是 zombie 本身。

> [!question]- Q4. 你在 production 看到 `thumbd` 的 log 出現 `fork: Resource temporarily unavailable`，而 CPU 與記憶體都很正常。你會怎麼查？
> 這個訊息是 `EAGAIN`，表示 process（或 thread）數量碰到某個上限，和 CPU、記憶體沒有直接關係。可能的上限包括：系統的 `kernel.pid_max` 與 `kernel.threads-max`、使用者的 `RLIMIT_NPROC`（`ulimit -u`）、以及容器 cgroup 的 `pids.max`。注意在 Linux 上 thread 也佔 PID，所以 thread 太多也會觸發。
>
> 調查順序：先用 `ps -eo ppid,stat | awk '$2 ~ /^Z/'` 看有沒有大量 zombie，並找出它們的父行程；再看 `/sys/fs/cgroup/pids.current` 與 `pids.max`、`ulimit -u`；最後用 `ps -eLf | wc -l` 看 thread 總數。如果是 zombie，就是程式漏了 `waitpid`（本章故事的情況）；如果是 thread 太多，就要檢查 thread pool 的上限設定是否失控。

> [!question]- Q5. 為什麼 fork 之後、exec 失敗時要呼叫 `_exit` 而不是 `exit`？
> `exit` 會在結束前執行 `atexit` 註冊的函式並 flush 所有 stdio buffer。fork 出來的子行程擁有父行程 buffer 與清理函式的副本，若 exec 失敗後呼叫 `exit`，它會把父行程還沒寫出去的資料再寫一次（造成重複的輸出或重複寫入檔案），也可能執行父行程的清理邏輯，例如刪除父行程還要用的暫存檔、關閉共享的連線。
>
> `_exit` 直接進入 kernel 結束 process，不做任何 user space 的清理，所以子行程不會干擾父行程的狀態。此外，`_exit` 是 async-signal-safe 的，在多執行緒程式 fork 後的子行程裡可以安全呼叫；`exit` 不是。

> [!question]- Q6. 面試題：既然 fork 會複製整個位址空間，為什麼 fork 一個使用 10 GB 記憶體的程式不需要 10 GB 的額外記憶體與時間？
> 因為 fork 使用 copy-on-write。kernel 不複製資料頁，只複製 page table，並把父子雙方的頁都標成唯讀、共用同一份實體記憶體。只有當某一方寫入某一頁時，才觸發 page fault，kernel 在那一刻複製那一頁。如果子行程馬上 exec，幾乎沒有頁會被複製。
>
> 但「不複製資料」不等於免費：複製 10 GB 位址空間的 page table 仍然要時間（4 KiB page 時大約是 20 MB 的 page table），fork 期間也要鎖住位址空間；之後父行程每寫一頁都會產生一次 COW fault。Redis 在背景存檔時 fork，就常因此看到延遲尖峰與記憶體上升。這也是 `posix_spawn`、`vfork` 存在的理由：它們讓子行程暫時共用父行程的位址空間，連 page table 都不用複製。第 24 章會再深入 COW。

> [!question]- Q7. 為什麼 `cd` 必須是 shell 的內建指令，而 `ls` 不用？
> 目前工作目錄是 process 的屬性，每個 process 各自一份，fork 時會被複製給子行程。如果 `cd` 是外部程式，shell 會 fork 一個子行程去執行它，子行程呼叫 `chdir` 改變的是自己的目錄，然後結束；shell 自己的目錄完全沒變，下一個指令還是在原來的目錄執行。
>
> `ls` 只是讀取目錄內容並印出來，不需要改變 shell 的任何狀態，所以可以是獨立的程式。判斷一個指令是否必須內建的原則是：它是否需要改變 shell process 自己的狀態，例如工作目錄（`cd`）、環境變數（`export`）、資源限制（`ulimit`）、或 shell 本身是否繼續執行（`exit`）。

> [!question]- Q8. 一個 process 呼叫 `execve` 之後，哪些東西還在、哪些消失了？這對服務有什麼影響？
> 保留的是「process 的身分與環境」：PID、PPID、user ID、目前工作目錄、資源限制、signal mask、被設為忽略的 signal，以及沒有設定 close-on-exec 的 file descriptor。消失的是「程式本身」：程式碼、全域變數、heap、stack、stdio buffer、所有 thread，以及 signal handler（恢復成預設，因為 handler 的程式碼已經不在了）。
>
> 對服務的影響有兩個。第一，exec 前沒 flush 的 log 會消失。第二，服務打開的 socket、檔案如果沒加 `O_CLOEXEC`，會被外部工具繼承：listening socket 被繼承後，服務重啟時可能 bind 不到 port；資料庫連線被繼承則可能造成協定錯亂。現代 C 程式的好習慣是所有 `open`、`socket`、`accept4`、`pipe2` 都預設加上 close-on-exec 旗標。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 8 章 8.4 節，以及 Shell Lab 的說明。
- [Linux man pages](https://man7.org/linux/man-pages/)：`fork(2)`、`execve(2)`、`waitpid(2)`、`wait(2)` 的 NOTES 段落、`posix_spawn(3)`、`prctl(2)` 中的 `PR_SET_CHILD_SUBREAPER`。
- [POSIX.1-2024（The Open Group Base Specifications）](https://pubs.opengroup.org/onlinepubs/9799919799/)：`fork`、`exec`、`posix_spawn` 的標準定義，以及 fork 後只能呼叫 async-signal-safe 函式的規定。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：Exceptional Control Flow 的投影片與錄影。
