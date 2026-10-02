---
chapter: 27
title: Unix I/O
part: 8
---

# 第 27 章　Unix I/O：File Descriptor、Short Count 與 Buffered I/O

> [!abstract] 本章地圖
> **核心問題**：程式讀寫檔案、pipe、socket 時，作業系統提供的介面到底長什麼樣？為什麼一次 `read` 或 `write` 不保證處理完你要求的量，而「寫進去了」也不等於「存到磁碟上了」？
>
> **你會學到**：
> - 用 `open`、`read`、`write`、`close` 正確地讀寫檔案，並處理 EOF、錯誤與 `EINTR`
> - 說出 short count 的成因，寫出「讀滿／寫滿」的迴圈與帶緩衝區的讀取器
> - 畫出 descriptor table、open file table 與 v-node table 的關係，預測 `open` 兩次、`dup`、`fork` 之後 file position 的變化
> - 用 `dup2` 實作 I/O redirection，理解 shell 的 `>` 與 `|` 怎麼運作
> - 判斷什麼時候該用 Standard I/O、什麼時候該用 Unix I/O，避開 buffering 與 `fork` 造成的重複輸出
> - 用 `fsync` 與「暫存檔＋`rename`」寫出斷電也不會留下半個檔案的程式
>
> **前置知識**：第 20 章（system call 與 errno）、第 21 章（fork、exec）、第 22 章（signal 中斷 system call）、第 24 章（page cache 與 mmap）
>
> **對應 CS:APP 3e**：第 10 章

## 27.1 故事：只有上半張的縮圖

拾光相簿的客服收到一批奇怪的回報：有些相簿的縮圖只有上半部正常，下半部是一片灰色。產品經理 Lisa 把截圖轉給小安，小安查了 `thumbd` 的磁碟快取，發現這些縮圖檔的大小都比正常的小，而且剛好集中在某一天的某幾個小時。

那段時間，SRE 阿哲正好在處理一台機器的磁碟快滿的告警。小安翻出 `thumbd` 寫快取的程式碼：

```c
int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
write(fd, jpeg, jpeg_len);      /* 沒有檢查回傳值 */
close(fd);
```

老周看了一眼：「`write` 不保證一次寫完。磁碟快滿時，它可能只寫進一部分就回傳；被 signal 打斷時也可能只寫一部分。你沒檢查回傳值，就把半個 JPEG 當成完整的縮圖存起來了。瀏覽器解碼到檔案結尾時資料不夠，剩下的部分就顯示成灰色。」

小安接著發現第二個問題：`thumbd` 用 pipe 把原圖交給外部轉檔工具處理（第 21 章），讀回結果時只呼叫一次 `read`，大圖的結果常常只拿到 64 KiB。還有第三個問題：上個月機房停電後，快取裡有幾百個縮圖檔大小是 0。程式明明 `write` 成功也 `close` 了，資料去哪裡了？

這三個問題都來自同一層：Unix 的 I/O 介面。這一章從最底層的 system call 開始，把「讀寫」這件看似簡單的事拆開來看。

## 27.2 Unix I/O 模型：一切都是 byte 序列

Unix 的 I/O 設計有一個非常簡潔的核心想法：**所有 I/O 裝置都被抽象成檔案**，而檔案就是一串 bytes。磁碟上的檔案、終端機、pipe、網路連線，甚至 `/dev/null` 這樣的虛擬裝置，都用同一組函式讀寫。這組函式叫 **Unix I/O**，由 kernel 以 system call 提供（第 20 章）。

程式要存取一個檔案，先用 `open` 請 kernel 打開它。kernel 回傳一個小的非負整數，叫 **file descriptor**（檔案描述符，常簡稱 fd）。之後所有操作都用這個整數代表那個檔案，就像餐廳發給你的號碼牌：你不需要知道廚房怎麼安排，只要拿號碼牌就能取餐。

每個 process 一開始就有三個已經打開的 descriptor：

| descriptor | 名稱 | `<unistd.h>` 常數 | 預設連到 |
|---|---|---|---|
| 0 | standard input | `STDIN_FILENO` | 終端機鍵盤，或 shell 重導向的來源 |
| 1 | standard output | `STDOUT_FILENO` | 終端機畫面，或 shell 重導向的目標 |
| 2 | standard error | `STDERR_FILENO` | 終端機畫面（通常不跟著 `>` 重導向） |

kernel 對每個打開的檔案記錄一個 **file position**（檔案位置），也叫 offset：下一次讀寫從第幾個 byte 開始。一開始是 0，每次讀寫 n bytes 就往後移 n。程式可以用 `lseek` 直接改變它，但 pipe 與 socket 沒有「位置」的概念，不能 `lseek`。

讀到檔案結尾之後再讀，`read` 回傳 0，這個狀態叫 **EOF**（end of file）。要注意，EOF 不是檔案裡的某個特殊字元，而是「已經沒有資料可讀」這個條件。對 pipe 來說，EOF 代表所有寫端都已經關閉；對 socket 來說，代表對方關閉了連線。

## 27.3 檔案類型

雖然「一切都是檔案」，kernel 仍然區分幾種不同類型的檔案，因為它們背後的行為差很多：

| 類型 | 是什麼 | 例子 | 能 `lseek` 嗎 |
|---|---|---|---|
| regular file | 磁碟上的一般資料 | `cat.jpg`、`thumbd.conf` | 能 |
| directory | 一組「名稱 → 檔案」的對應 | `/var/cache/thumbd/` | 不用 `read` 讀，用 `opendir`／`readdir` |
| symbolic link | 存著另一個路徑的小檔案 | `current -> releases/v42` | 通常操作的是它指向的檔案 |
| FIFO／pipe | kernel 中的單向 byte 管道 | `cmd1 \| cmd2` | 不能 |
| socket | 跨機器或同機器 process 間的雙向通訊端點 | `thumbd` 接收 HTTP 的連線（第 28 章） | 不能 |
| character device | 一次一個 byte 的裝置 | 終端機 `/dev/tty`、`/dev/null`、`/dev/urandom` | 依裝置而定 |
| block device | 以區塊存取的儲存裝置 | `/dev/sda`、`/dev/nvme0n1` | 能 |

對 kernel 來說，regular file 沒有「文字檔」與「二進位檔」的區別，都只是 bytes。所謂文字檔，只是內容剛好全是可讀的字元，並以換行字元 `\n`（0x0a）分隔每一行。Windows 用 `\r\n` 兩個 bytes 表示換行，這也是跨平台處理文字檔時常見的小麻煩。

**Directory**（目錄）裡的每一項把一個名稱連到一個檔案。路徑 `/var/cache/thumbd/a.jpg` 的解析過程，就是從根目錄 `/` 開始，一層一層查名稱。每個 process 都有一個 current working directory（目前工作目錄），不以 `/` 開頭的相對路徑從這裡開始解析，可以用 `cd` 或 `chdir` 改變。

## 27.4 打開、讀、寫、關閉

### open：打開或建立檔案

```c
#include <fcntl.h>
int open(const char *path, int flags, mode_t mode);   /* 成功回傳 fd，失敗回傳 -1 */
```

`flags` 說明要怎麼存取，用 `|` 組合：

| flag | 意義 | 典型用途 |
|---|---|---|
| `O_RDONLY`、`O_WRONLY`、`O_RDWR` | 只讀、只寫、讀寫（三選一） | 必選其一 |
| `O_CREAT` | 不存在就建立 | 寫入新檔 |
| `O_TRUNC` | 已存在就把長度截成 0 | 覆寫整個檔案 |
| `O_APPEND` | 每次寫入前都先把位置移到檔尾 | log 檔，多個 process 一起附加 |
| `O_EXCL` | 搭配 `O_CREAT`，檔案已存在就失敗 | 建立 lock 檔、避免覆蓋 |
| `O_CLOEXEC` | 執行 `execve` 時自動關閉這個 fd | 避免 fd 洩漏給子行程（27.13 節） |

`mode` 只在建立新檔時有意義，指定新檔的權限位元。但實際的權限還要再扣掉 process 的 **umask**（權限遮罩）：

```text
實際權限 = mode & ~umask
```

手算一次。`thumbd` 用 `mode = 0666`（所有人可讀寫）建立快取檔，process 的 umask 是常見的 `022`：

```text
mode    = 0666 = 110 110 110
umask   = 0022 = 000 010 010
~umask        = 111 101 101
mode & ~umask = 110 100 100 = 0644   → 擁有者可讀寫，其他人只能讀
```

如果 umask 是 `027`，同樣的 `0666` 會變成 `0640`：群組只能讀，其他人完全不能存取。這就是為什麼程式通常寫 `0666`（一般檔案）或 `0777`（目錄、可執行檔），讓使用者用 umask 決定最後的權限。27.13 節的程式會實際驗證這個計算。

### read 與 write

```c
#include <unistd.h>
ssize_t read(int fd, void *buf, size_t n);         /* 回傳讀到的 bytes；0 = EOF；-1 = 錯誤 */
ssize_t write(int fd, const void *buf, size_t n);  /* 回傳寫入的 bytes；-1 = 錯誤 */
```

`read` 從 fd 目前的位置最多讀 n bytes 到 `buf`，`write` 從 `buf` 最多寫 n bytes 到 fd。回傳型別 `ssize_t` 是 signed 的 `size_t`，因為它需要用 −1 表示錯誤。注意兩個函式說的都是「最多」，這就是下一節的主題。

### close

```c
int close(int fd);   /* 成功 0，失敗 -1 */
```

`close` 告訴 kernel「這個號碼牌我不用了」。kernel 會釋放 fd，並在沒有任何人再參照這個打開的檔案時，釋放相關的資料結構。關閉一個已經關閉的 fd 是錯誤，在多執行緒程式中更危險：同一個號碼可能已經被另一個 thread 的 `open` 重新拿到，你會關掉別人的檔案。

`close` 的回傳值也該檢查。在某些檔案系統（例如 NFS）上，延遲的寫入錯誤可能直到 `close` 時才回報。但即使 `close` 成功，也**不代表**資料已經寫到磁碟上，27.10 節會解釋。

### 錯誤處理

所有 Unix I/O 函式失敗時都回傳 −1，並把原因寫進全域變數 `errno`（第 20 章）。最常遇到的幾個：

| errno | 意義 | 常見情境 |
|---|---|---|
| `ENOENT` | 檔案或目錄不存在 | 路徑打錯、檔案已被刪除 |
| `EACCES` | 權限不足 | 寫入其他使用者擁有的目錄 |
| `EMFILE` | 這個 process 打開的 fd 太多 | fd 洩漏，達到 `ulimit -n` 上限 |
| `ENOSPC` | 裝置上沒有空間 | 磁碟滿了 |
| `EINTR` | system call 被 signal 打斷 | 慢速裝置（pipe、socket、終端機）上等待時收到 signal |
| `EBADF` | 不是有效的 fd | 關閉之後還在用 |

## 27.5 Short count：為什麼一次讀寫不保證完成

### 現象

**Short count**（不足量）是指 `read` 或 `write` 回傳的 bytes 數少於要求的 n。這不是錯誤，而是 Unix I/O 的正常行為，但它是 I/O 程式最常見的 bug 來源，27.1 節的三個問題有兩個就是它。

### 成因

| 情況 | 會發生 short count 嗎 | 原因 |
|---|---|---|
| 讀 regular file，還沒到結尾 | 一般不會 | 磁碟檔案的資料已經在那裡，kernel 會盡量給滿 |
| 讀 regular file，剩下的不到 n bytes | 會 | 檔案只剩這麼多；下一次 `read` 回傳 0（EOF） |
| 從終端機讀 | 會 | 終端機預設一次交出一行 |
| 從 pipe 或 socket 讀 | 經常 | 只能交出目前已經到達的資料；pipe 的緩衝區容量有限（Linux 預設 16 頁，也就是 64 KiB），網路資料分批到達 |
| 寫入 pipe 或 socket | 可能 | 緩衝區滿了；非阻塞模式下立刻回傳已寫的量 |
| 寫入磁碟檔案，空間快用完 | 可能 | 只寫得進剩下的空間，下一次 `write` 才會回傳 −1、`errno = ENOSPC` |
| 讀寫中途收到 signal | 可能 | 已經傳了一部分就回傳部分的量；完全沒傳就回傳 −1、`errno = EINTR` |

把 pipe 的情況畫成時間軸，就能看出為什麼「只呼叫一次 `read`」一定會出錯：

```text
 寫端（轉檔工具）                    pipe 緩衝區（容量 64 KiB）         讀端（thumbd）
 ───────────────                   ──────────────────────────         ──────────────
 write(256 KiB) 開始
 寫入前 64 KiB  ─────────────────▶ [■■■■ 64 KiB 滿了]
 （緩衝區滿，寫端被阻擋）                                    ◀──────── read(fd, buf, 256 KiB)
                                   [            空]  ─────────────▶ 回傳 65536（short count！）
 繼續寫入下一批 ────────────────▶ [■■■■ 64 KiB]                     天真的程式到這裡就停了
                                                     ◀──────────── 正確的程式：再呼叫 read
 ...                                                                直到湊滿 256 KiB 或遇到 EOF
 close(寫端)                                                        read 回傳 0 → EOF
```

`thumbd` 讀轉檔結果的 bug 就是這張圖的寫照：轉檔工具一次寫出 256 KiB，但 pipe 一次只能容納 64 KiB，第一次 `read` 只拿到 64 KiB，程式就以為結果只有這麼大。

### 處理方法

正確的寫法是把 `read`／`write` 包在迴圈裡，直到處理完 n bytes、遇到 EOF 或發生真正的錯誤。邏輯是：

```text
 剩下 left = n
 while left > 0:
     r = read(fd, p, left)
     r < 0 且 errno == EINTR → 被 signal 打斷，重試
     r < 0                  → 真正的錯誤，回傳 -1
     r == 0                 → EOF，回傳已讀的量（可能少於 n）
     否則 p += r，left -= r
```

`write` 的迴圈幾乎一樣，只是沒有 EOF 這種情況。27.12 節的實驗一會實作這兩個函式（`readn`、`writen`）並實際量到 pipe 的 short count。

> [!warning] 常見誤解
> 「我讀的是本機磁碟上的檔案，所以不用處理 short count。」今天讀的是檔案，明天這段程式碼可能被改成從 stdin、pipe 或 socket 讀，而且 `write` 在磁碟快滿時本來就可能 short。把讀寫一律包在迴圈裡，成本只是幾行程式碼，卻能避免最難重現的那一類 bug。

## 27.6 RIO：robust I/O 與使用者空間緩衝區

CS:APP 提供了一個叫 **RIO**（Robust I/O）的小套件，把上一節的迴圈包裝成可重複使用的函式。它分成兩組，分別解決兩個不同的問題。

**第一組：無緩衝的讀滿與寫滿。** `rio_readn` 與 `rio_writen` 就是上一節的迴圈，直接呼叫 `read`／`write`，沒有額外的緩衝區。適合傳輸「已知長度的大塊資料」，例如把一整張圖片寫到 socket。

**第二組：帶緩衝區的讀取。** 很多協定是以「行」為單位的：HTTP 的 request line 與 header 每行以 `\r\n` 結尾（第 29 章）、設定檔、log 檔也是。要讀一行，最直覺的做法是一次 `read` 1 byte，直到讀到 `\n`。但每一次 `read` 都是一次 system call，要進出 kernel 一次（第 20 章），一行 100 個字元就要 100 次。

解法是在使用者空間放一個緩衝區：一次向 kernel 要一大塊（例如 8 KiB），之後的「讀一個 byte」都從緩衝區裡拿，緩衝區空了才再呼叫 `read`。

```text
 kernel                       使用者空間的讀取器                    應用程式
 ──────                       ──────────────────                    ────────
                              ┌──────────────────────────────┐
 read(fd, buf, 8192) ───────▶ │GET /a.jpg\nGET /b.jpg\nGE... │
 （一次 system call）         └──────────────────────────────┘
                                ▲ next          cnt = 尚未取走的 bytes
                                │
                    readline() ─┴─ 從 next 開始複製到 '\n' ──────▶ "GET /a.jpg\n"
                    readline() ─── 繼續往後複製 ──────────────────▶ "GET /b.jpg\n"
                    ...
                    緩衝區用完（cnt == 0）→ 才再呼叫一次 read 補充
```

這個讀取器的狀態只有三個欄位：fd、緩衝區中還沒被取走的 bytes 數（`cnt`）、下一個要取的位置（`next`）。每次要資料時先看 `cnt`：大於 0 就直接從 `next` 複製；等於 0 才呼叫 `read` 補充。補充時回傳 short count 也沒關係，因為讀取器本來就只把「目前拿到的」放進緩衝區。

| 讀法 | 每行的 system call 數 | 適合 | 注意 |
|---|---|---|---|
| 每次 `read` 1 byte | 一行有幾個 byte 就幾次 | 幾乎不適合 | 慢，但不會多讀 |
| 無緩衝的 `readn` | 一次以上 | 已知長度的二進位資料 | 不能用來找行尾 |
| 帶緩衝區的 `readline` | 平均遠小於 1 | 行導向的協定、文字檔 | 同一個 fd 不能和無緩衝的讀取混用，否則緩衝區裡的資料會被跳過 |

最後一列的注意事項很重要：帶緩衝區的讀取器會「預先多讀」，緩衝區裡可能已經放著下一行，甚至 HTTP body 的開頭。如果讀完 header 之後改用 `read` 直接讀 body，就會漏掉已經進到緩衝區的那一段。RIO 的設計是讓同一個讀取器同時提供「讀一行」與「讀 n bytes」兩個帶緩衝的函式，兩者共用同一個緩衝區，就不會有這個問題。27.12 節的實驗二會實作一個這樣的讀取器，並量出 system call 次數的差距。

## 27.7 Metadata：stat 與目錄

檔案除了內容，還有一組關於它自己的資訊，叫 **metadata**（中繼資料）：大小、類型、權限、擁有者、修改時間等。程式用 `stat`（給路徑）或 `fstat`（給 fd）取得：

```c
#include <sys/stat.h>
int stat(const char *path, struct stat *st);
int fstat(int fd, struct stat *st);
```

`struct stat` 中最常用的欄位：

| 欄位 | 意義 | 例子 |
|---|---|---|
| `st_size` | 檔案大小（bytes） | 判斷快取檔是否完整、`mmap` 前取得長度（第 24 章） |
| `st_mode` | 類型與權限位元 | 用 `S_ISREG`、`S_ISDIR` 等巨集判斷類型，`st_mode & 0777` 取權限 |
| `st_mtime` | 最後修改時間 | HTTP 的 `Last-Modified` 與快取驗證 |
| `st_ino`、`st_dev` | inode 號碼與所在裝置 | 判斷兩個路徑是不是同一個檔案 |
| `st_nlink` | hard link 數 | 為 0 時表示已經沒有任何名稱指向它 |

讀目錄要用另一組函式：`opendir` 打開、`readdir` 一次回傳一個項目（名稱與 inode 號碼）、`closedir` 關閉。`thumbd` 的快取清理工具就是用 `readdir` 走過快取目錄，再對每個項目 `stat` 取得 `st_mtime`，刪掉太久沒被修改的縮圖。

> [!tip] 先 `fstat` 再 `read`
> 要把整個檔案讀進記憶體時，先 `fstat(fd, &st)` 取得 `st_size` 再配置緩衝區，比「一邊讀一邊 `realloc`」簡單。但不要假設檔案大小在讀的過程中不會變：別的 process 可能正在寫它。讀的迴圈仍然要以「`read` 回傳 0」為結束條件，而不是「讀滿 `st_size`」。

## 27.8 kernel 怎麼記錄打開的檔案

要理解 `fork` 之後父子行程的檔案為什麼會互相影響、`dup2` 為什麼能做 redirection，必須先看 kernel 內部用三層資料結構表示打開的檔案：

```text
  descriptor table               open file table                 v-node table
  （每個 process 一張）           （所有 process 共用）            （所有 process 共用）
 ┌──────────────┐
 │ fd 0 ─────── ┼──▶ ┌───────────────────┐             ┌──────────────────────┐
 │ fd 1 ─────── ┼──▶ │ 終端機             │ ──────────▶ │ 終端機的 v-node       │
 │ fd 2 ─────── ┼──▶ │ pos、refcnt = 3    │             └──────────────────────┘
 │ fd 3 ─────── ┼──▶ ┌───────────────────┐             ┌──────────────────────┐
 │ fd 4 ─────── ┼──▶ │ cat.jpg（A）       │ ──┐         │ cat.jpg 的 v-node     │
 └──────────────┘    │ pos = 4096，refcnt=1│   ├───────▶ │ 類型、大小、權限……    │
                     └───────────────────┘   │         │（來自 stat 的資訊）   │
                     ┌───────────────────┐   │         └──────────────────────┘
                     │ cat.jpg（B）       │ ──┘
                     │ pos = 0，refcnt = 1 │
                     └───────────────────┘
       fd 3、fd 4 各自 open 了一次 cat.jpg → 兩個 open file entry，兩個獨立的位置
```

三層各管不同的東西：

1. **Descriptor table**（描述符表）：每個 process 一張，以 fd 為索引，每一格只是一個指向 open file table 項目的指標。fd 就是這張表的索引。
2. **Open file table**（打開檔案表）：所有 process 共用。每呼叫一次 `open` 就建立一個新項目，記錄**目前的 file position**、打開時的旗標（唯讀、`O_APPEND` 等），以及一個 **reference count**（參照計數，有幾個 descriptor 指向它）。`close` 會把計數減一，歸零時才真正刪除這個項目。
3. **v-node table**：所有 process 共用。每個檔案一個項目，存放檔案本身的資訊，也就是 `stat` 看到的那些 metadata。同一個檔案不管被打開幾次，都只有一個 v-node。（v-node 是 CS:APP 沿用的 BSD 術語；Linux kernel 裡對應的結構叫 inode，open file table 的項目則是 `struct file`，概念相同。）

這個結構最重要的推論是：**file position 存在 open file table，不在 descriptor table。** 所以「兩個 fd 會不會互相影響位置」，取決於它們是否指向同一個 open file table 項目：

| 情況 | open file table 項目 | 共用 file position 嗎 |
|---|---|---|
| 同一個 process 對同一個檔案 `open` 兩次 | 兩個不同項目 | 不共用，各讀各的 |
| `dup(fd)` 或 `dup2(old, new)` | 同一個項目，refcnt 加一 | 共用 |
| `fork` 之後父子行程的同號 fd | 同一個項目（子行程複製的是 descriptor table），refcnt 加一 | 共用 |
| 兩個不同 process 各自 `open` 同一個檔案 | 兩個不同項目 | 不共用 |

### fork 之後的檔案

`fork`（第 21 章）會複製父行程的 descriptor table，但**不會**複製 open file table 的項目。所以父子行程的每個 fd 都指向同一個項目，共用 file position：子行程讀了 10 bytes，父行程接著讀到的是第 11 個 byte。

```text
         fork 之前                                fork 之後
 父 ┌────────┐                          父 ┌────────┐
    │ fd 3 ──┼──▶ [cat.jpg pos=0 refcnt=1]  │ fd 3 ──┼──▶ [cat.jpg pos=0 refcnt=2]
    └────────┘                             └────────┘          ▲
                                         子 ┌────────┐          │
                                            │ fd 3 ──┼──────────┘
                                            └────────┘
```

這帶來兩個實務上的重點。第一，如果父子行程同時寫同一個 fd（例如都寫到 stdout 指向的 log 檔），它們共用位置，輸出會交錯，但不會互相覆蓋。第二，要讓 open file table 的項目真正被釋放，父子行程**都要** `close`。pipe 的 EOF 就依賴這一點：只要還有任何一個 process 握著 pipe 寫端的 fd，讀端就永遠等不到 EOF。`thumbd` 呼叫外部工具時，如果父行程忘了關掉自己那份寫端，讀結果的迴圈就會卡住。

## 27.9 I/O redirection：dup2

Shell 的 `ls > out.txt` 會讓 `ls` 的輸出進到檔案，而 `ls` 本身完全不知道這件事，它只是照常寫 fd 1。這是怎麼做到的？答案是 `dup2`：

```c
int dup2(int oldfd, int newfd);   /* 讓 newfd 指向 oldfd 指向的 open file 項目 */
```

`dup2` 把 descriptor table 中 `oldfd` 那一格的指標，複製到 `newfd` 那一格；如果 `newfd` 原本開著，會先把它關閉。shell 執行 `ls > out.txt` 的步驟是：

```text
 1. fork 出子程序
 2. 子程序：fd = open("out.txt", O_WRONLY|O_CREAT|O_TRUNC, 0666)   → 假設得到 fd 3
 3. 子程序：dup2(3, 1)
           descriptor table 變成：
             fd 1 ──▶ [out.txt]   （原本的終端機項目 refcnt 減一）
             fd 3 ──▶ [out.txt]   （refcnt = 2）
 4. 子程序：close(3)                → 只剩 fd 1 指向 out.txt
 5. 子程序：execve("/bin/ls", ...)  → ls 寫 fd 1，資料進到 out.txt
```

Pipe 也是同樣的道理：`cmd1 | cmd2` 是先建立 pipe，再讓 `cmd1` 的 fd 1 指向寫端、`cmd2` 的 fd 0 指向讀端。`thumbd` 呼叫外部轉檔工具時，也是在子行程中用 `dup2` 把 pipe 接到工具的 stdin 與 stdout，再 `execve`。

因為 `dup2` 讓兩個 fd 指向同一個 open file table 項目，它們共用 file position。27.12 節的實驗三會實際驗證這點，並示範如何先用 `dup` 備份原本的 stdout、重導向後再還原。

## 27.10 Standard I/O：方便，但有自己的緩衝區

### 為什麼需要

C 標準函式庫提供另一套更高階的 I/O 介面，叫 **Standard I/O**：`fopen`、`fprintf`、`fgets`、`fread`、`fwrite`、`fclose` 等。它用 `FILE *` 代表一個打開的 **stream**（串流），內部其實就是「一個 fd 加上一個使用者空間的緩衝區」，概念上和 27.6 節帶緩衝區的讀取器一樣。它的好處是格式化輸出入方便，而且大幅減少 system call 次數。

### 緩衝模式

Standard I/O 的輸出不會在每次 `printf` 時都呼叫 `write`，而是先累積在緩衝區，依照模式決定何時真正寫出：

| 模式 | 何時 `write` | 預設用在 |
|---|---|---|
| unbuffered（不緩衝） | 每次輸出都立刻寫 | `stderr`，讓錯誤訊息不會延遲 |
| line buffered（行緩衝） | 遇到 `\n`、緩衝區滿或要讀輸入時 | 連到終端機的 `stdout` |
| fully buffered（完全緩衝） | 緩衝區滿、`fflush`、`fclose` 或程式正常結束時 | 連到檔案或 pipe 的 `stdout`、一般 `fopen` 的檔案 |

這解釋了一個常見的困惑：同一個程式直接在終端機執行時，`printf` 的訊息即時出現；改成 `./thumbd > log.txt` 或用 pipe 交給 log 收集程式時，log 卻要等很久才出現，甚至當機時最後幾行完全遺失。因為輸出目標不是終端機時，`stdout` 從行緩衝變成了完全緩衝。緩衝區的大小依 C 函式庫而定（常見為數 KiB），可以用 `setvbuf` 改變模式。

### 和 fork 一起用的陷阱

緩衝區在使用者空間，也就是 process 的記憶體裡。`fork` 會複製整個位址空間（第 24 章的 copy-on-write），**連還沒寫出的緩衝區內容也一起複製**。之後父子行程結束時各自把緩衝區寫出，同一段輸出就出現兩次：

```text
 printf("worker starting\n")   stdout 是 pipe → 完全緩衝 → 資料只在緩衝區裡
         │
       fork()
     ┌───┴─────────────────┐
     ▼                     ▼
  父：緩衝區 "worker..."   子：緩衝區 "worker..."（複製來的）
     │                     │
   exit() → write          exit() → write
     ▼                     ▼
       log 裡出現兩行 "worker starting"
```

解法是在 `fork` 之前呼叫 `fflush(stdout)`（以及其他有輸出的 stream），或在子行程中用 `_exit` 而不是 `exit` 結束，因為 `_exit` 不會沖出 stdio 緩衝區。27.12 節的實驗四會實際重現這個現象。

### 輸入與輸出不能隨意交替

CS:APP 特別指出 Standard I/O 的兩個限制。對同一個可讀寫的 stream：輸出之後要接著輸入，中間必須先 `fflush`、`fseek`、`fsetpos` 或 `rewind`；輸入之後要接著輸出，中間必須先 `fseek`、`fsetpos` 或 `rewind`（除非輸入已經讀到 EOF）。原因是兩個方向共用同一個緩衝區，不先清空或重新定位，緩衝區裡的狀態就會不一致。

這兩條限制在 socket 上很麻煩：socket 不能 `lseek`，所以第二條規則根本無法滿足。可行的變通是對同一個 socket 用 `fdopen` 開兩個 stream（一個讀、一個寫），但關閉時又會遇到同一個 fd 被關兩次的問題。因此在網路程式中，CS:APP 的建議是：**socket 上不要用 Standard I/O，改用 RIO 這類自己掌控的讀寫函式。**

### 該用哪一套

| 情境 | 建議 | 理由 |
|---|---|---|
| 讀寫磁碟上的文字檔、設定檔 | Standard I/O | 格式化方便，緩衝有效率 |
| 讀寫網路 socket | Unix I/O＋自己的緩衝讀取器（如 RIO） | 避開 stream 的限制，掌控 short count |
| 在 signal handler 裡輸出 | 只能用 `write` | `printf` 不是 async-signal-safe（第 22 章） |
| 需要精確控制何時寫出（例如 fork 前、寫 log） | Unix I/O，或 Standard I/O 加上明確的 `fflush` | 避免緩衝造成重複或遺失 |
| 讀寫大塊二進位資料（圖片） | Unix I/O 的 `read`／`write` 迴圈，或 `mmap`（第 24 章） | 不需要格式化，也省一次複製 |

## 27.11 fsync 與 durability：寫進去不等於存起來

### 資料在哪幾層

27.1 節的第三個問題：停電後，有些已經 `write` 成功、也 `close` 了的縮圖檔大小是 0。要理解這件事，得看一次 `write` 之後資料停在哪裡：

```text
 應用程式      fwrite / printf
    │          ① stdio 緩衝區（使用者空間）  ← fflush 把資料推到下一層
    ▼
 write() 回傳成功
    │          ② kernel 的 page cache（記憶體）← 這時 write 就回傳了
    ▼             kernel 稍後才在背景寫回磁碟（通常數秒到數十秒內）
 fsync() 回傳成功
    │          ③ 磁碟裝置（含裝置自己的快取）
    ▼             fsync 會要求裝置把資料真正寫入非揮發性的儲存
 持久的儲存媒體
```

`write` 回傳成功，只表示資料已經從你的緩衝區複製到 kernel 的 **page cache**（第 24 章），之後讀同一個檔案的 process 都能立刻看到新內容。但 page cache 在記憶體裡，停電就消失。kernel 會在背景把 dirty 的頁寫回磁碟，時間依系統設定而定。`close` 也不會等這件事完成。

**Durability**（持久性）是指「資料在斷電或當機後仍然存在」的保證。要達到它，要呼叫 `fsync(fd)`：它會等到這個檔案的資料與 metadata 都寫到儲存裝置上才回傳。`fdatasync(fd)` 只保證資料與「讀回資料所需的」metadata（例如檔案大小），可以省下一些寫入。

| 動作 | 資料到哪裡 | 程式 crash 後還在嗎 | 斷電後還在嗎 |
|---|---|---|---|
| `fprintf` 之後 | stdio 緩衝區 | 不一定（沒 flush 就消失） | 不在 |
| `fflush` 或 `write` 之後 | kernel page cache | 在（kernel 還在） | 不一定 |
| `fsync` 之後 | 儲存裝置 | 在 | 在（前提是裝置正確處理 flush） |

### 原子替換：暫存檔＋fsync＋rename

只有 `fsync` 還不夠。如果 `thumbd` 直接用 `O_TRUNC` 打開正式的快取檔再寫入，停電可能發生在「已經截成 0、還沒寫完」的中間，留下一個空的或半截的檔案。這正是 27.1 節大小為 0 的檔案的成因。

標準解法利用 `rename` 的一個特性：在同一個檔案系統內，`rename(tmp, dst)` 是原子的（atomic，不可分割的），其他 process 看到的 `dst` 要嘛是舊檔，要嘛是完整的新檔，不會看到中間狀態。完整步驟是：

1. 在同一個目錄建立暫存檔，例如 `.cat_200.jpg.tmp`。
2. 用 `writen` 寫滿所有資料，處理 short count。
3. `fsync` 暫存檔，確保內容已經落到磁碟。
4. `close`，並檢查回傳值。
5. `rename` 成正式名稱。
6. `fsync` 所在的目錄，確保「名稱改了」這個目錄的修改也落到磁碟。

任一步失敗就刪掉暫存檔，正式的檔案完全不受影響。27.13 節會給出完整可執行的實作。

> [!warning] 常見誤解
> 「`fsync` 很慢，所以每次都 `fsync` 一定不好。」`fsync` 的確可能花上數 ms 甚至更久，但該用時就要用。對 `thumbd` 的快取來說，縮圖可以重新產生，遺失一些可以接受，重點是「不能留下半個檔案」，所以最關鍵的是原子替換，`fsync` 可以視需求取捨。對資料庫的交易 log、使用者上傳的原圖，`fsync` 就不能省。判斷的依據是「這份資料遺失或損毀的代價」。

## 27.12 動手做：量 short count，觀察 descriptor 共享與 stdio 緩衝

以下四個實驗都在 macOS arm64（Apple clang 21.0.0）上以 `cc -std=c17 -O1 -Wall -Wextra` 編譯執行。程式開頭的 `#define _POSIX_C_SOURCE 200809L` 讓 `fork`、`pipe` 等 POSIX 函式在 `-std=c17` 下的 Linux 上也能正確宣告。

### 實驗一：pipe 上的 short count 與 readn／writen

子行程一次寫入 256 KiB 到 pipe，父行程先「天真地」呼叫一次 `read`，再用 `readn` 補讀剩下的部分。

```c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

/* 讀滿 n bytes，除非遇到 EOF；處理 short count 與 EINTR */
static ssize_t readn(int fd, void *buf, size_t n) {
    size_t left = n;
    char *p = buf;
    while (left > 0) {
        ssize_t r = read(fd, p, left);
        if (r < 0) { if (errno == EINTR) continue; return -1; }
        if (r == 0) break;                      /* EOF：回傳已讀到的量 */
        left -= (size_t)r; p += r;
    }
    return (ssize_t)(n - left);
}

/* 寫滿 n bytes；write 回傳得比較少時，從斷掉的地方接著寫 */
static ssize_t writen(int fd, const void *buf, size_t n) {
    size_t left = n;
    const char *p = buf;
    while (left > 0) {
        ssize_t w = write(fd, p, left);
        if (w < 0) { if (errno == EINTR) continue; return -1; }
        left -= (size_t)w; p += w;
    }
    return (ssize_t)n;
}

int main(void) {
    enum { SIZE = 256 * 1024 };                 /* 一張 256 KiB 的「縮圖」 */
    int fds[2];
    if (pipe(fds) < 0) { perror("pipe"); return 1; }
    pid_t pid = fork();
    if (pid == 0) {                             /* 子程序：寫端 */
        close(fds[0]);
        char *img = malloc(SIZE);
        memset(img, 'x', SIZE);
        writen(fds[1], img, SIZE);
        _exit(0);
    }
    close(fds[1]);
    char *buf = malloc(SIZE);
    ssize_t r = read(fds[0], buf, SIZE);        /* 天真的寫法：只呼叫一次 read */
    printf("一次 read 要 %d bytes，實際拿到 %zd bytes\n", SIZE, r);
    ssize_t rest = readn(fds[0], buf + r, SIZE - (size_t)r);
    printf("readn 補讀 %zd bytes，合計 %zd bytes\n", rest, r + rest);
    printf("再讀一次：%zd（0 代表 EOF）\n", read(fds[0], buf, 1));
    waitpid(pid, NULL, 0);
    free(buf);
    return 0;
}
```

執行結果：

```text
一次 read 要 262144 bytes，實際拿到 65536 bytes
readn 補讀 196608 bytes，合計 262144 bytes
再讀一次：0（0 代表 EOF）
```

逐行解讀：

1. 第一行就是 27.1 節的 bug：要求 262,144 bytes，只拿到 65,536 bytes，剛好是這台機器上 pipe 一次能交出的量。這個數字依平台、kernel 設定與排程時機而定，可能不同；重點是它少於要求的量，而且不是錯誤。
2. `readn` 的迴圈繼續呼叫 `read`，每次拿到一部分，直到湊滿剩下的 196,608 bytes，合計剛好 256 KiB。
3. 子行程寫完後 `_exit`，pipe 的寫端全部關閉（父行程在 `fork` 後也關了自己那一份），所以再讀一次得到 0，也就是 EOF。如果父行程沒有 `close(fds[1])`，這最後一次 `read` 會永遠等下去，因為 kernel 認為還有人可能寫入。

子行程的 `writen` 也在處理 short count：pipe 滿了時 `write` 會阻擋，等讀端取走資料後再繼續，在阻擋模式下通常一次就能寫完；但被 signal 打斷或在非阻擋模式時就可能回傳部分的量，迴圈讓兩種情況都正確。

### 實驗二：帶緩衝區的行讀取器

這支程式先產生一個 2,000 行的 log 檔，再用兩種方法數行數：一次 `read` 1 byte，以及 27.6 節的 8 KiB 緩衝讀取器。

```c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* 帶緩衝區的讀取器：一次向 kernel 要一大塊，之後從使用者空間的緩衝區取 */
typedef struct {
    int fd;
    size_t cnt;          /* 緩衝區裡還沒被取走的 bytes */
    char *next;          /* 下一個要取的 byte */
    char buf[8192];
    long syscalls;       /* 統計呼叫了幾次 read */
} linebuf_t;

static void lb_init(linebuf_t *lb, int fd) { lb->fd = fd; lb->cnt = 0; lb->next = lb->buf; lb->syscalls = 0; }

static ssize_t lb_fill_read(linebuf_t *lb, char *out, size_t n) {
    while (lb->cnt == 0) {                       /* 緩衝區空了才 refill */
        lb->syscalls++;
        ssize_t r = read(lb->fd, lb->buf, sizeof lb->buf);
        if (r < 0) { if (errno == EINTR) continue; return -1; }
        if (r == 0) return 0;                    /* EOF */
        lb->cnt = (size_t)r; lb->next = lb->buf;
    }
    size_t k = n < lb->cnt ? n : lb->cnt;
    memcpy(out, lb->next, k);
    lb->next += k; lb->cnt -= k;
    return (ssize_t)k;
}

/* 讀一行（含 '\n'），最多 max-1 bytes，結尾補 '\0'；回傳長度，0 表示 EOF */
static ssize_t lb_readline(linebuf_t *lb, char *line, size_t max) {
    size_t n = 0;
    while (n + 1 < max) {
        char c;
        ssize_t r = lb_fill_read(lb, &c, 1);
        if (r < 0) return -1;
        if (r == 0) break;
        line[n++] = c;
        if (c == '\n') break;
    }
    line[n] = '\0';
    return (ssize_t)n;
}

int main(void) {
    const char *path = "access.log";             /* 準備一個 2,000 行的 log 檔 */
    FILE *f = fopen(path, "w");
    for (int i = 0; i < 2000; i++) fprintf(f, "GET /thumb/%04d.jpg 200\n", i);
    fclose(f);

    int fd = open(path, O_RDONLY);
    long naive = 0; char c; long lines = 0;
    for (ssize_t r; (r = read(fd, &c, 1)) > 0; naive++) if (c == '\n') lines++;
    naive++;                                     /* 最後回傳 0 的那次也算 */
    printf("一次讀 1 byte：%ld 行，呼叫 read %ld 次\n", lines, naive);

    lseek(fd, 0, SEEK_SET);
    linebuf_t lb; lb_init(&lb, fd);
    char line[128]; lines = 0;
    while (lb_readline(&lb, line, sizeof line) > 0) lines++;
    printf("用 8 KiB 緩衝區：%ld 行，呼叫 read %ld 次\n", lines, lb.syscalls);
    close(fd); unlink(path);
    return 0;
}
```

執行結果：

```text
一次讀 1 byte：2000 行，呼叫 read 48001 次
用 8 KiB 緩衝區：2000 行，呼叫 read 7 次
```

每行 `GET /thumb/0000.jpg 200\n` 是 24 bytes，2,000 行共 48,000 bytes。一次讀 1 byte 需要 48,000 次 `read`，再加上最後回傳 0 的那一次，共 48,001 次。用 8 KiB 緩衝區時，48,000 ÷ 8,192 ≈ 5.86，需要 6 次有資料的 `read` 加上 1 次 EOF，共 7 次。兩者的 system call 次數差了將近 7,000 倍，而每次 system call 都要進出 kernel 一次，這就是緩衝 I/O 存在的理由。

### 實驗三：誰共用 file position

用一個內容為 `0123456789` 的檔案，依序驗證 27.8 節表格中的三種情況，最後示範 `dup2` 重導向與還原。

```c
#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

/* 用一個 10 bytes 的檔案觀察 file position 是誰的 */
int main(void) {
    const char *path = "fdtest.txt";
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    write(fd, "0123456789", 10);
    close(fd);

    char c;
    int a = open(path, O_RDONLY);           /* 兩次 open → 兩個 open file entry */
    int b = open(path, O_RDONLY);
    read(a, &c, 1); read(a, &c, 1);
    read(b, &c, 1);
    printf("情況一 兩次 open：a 讀了兩次、b 讀一次，b 讀到 '%c'\n", c);

    int d = dup(a);                         /* dup → 同一個 open file entry */
    read(d, &c, 1);
    printf("情況二 dup：a 讀過兩個 byte，d 接著讀到 '%c'\n", c);

    if (fork() == 0) {                      /* fork → 子程序共用同一個 entry */
        read(a, &c, 1);
        _exit(0);
    }
    wait(NULL);
    read(a, &c, 1);
    printf("情況三 fork：子程序讀走一個 byte，父程序接著讀到 '%c'\n", c);
    printf("a 的 offset = %ld、b 的 offset = %ld\n",
           (long)lseek(a, 0, SEEK_CUR), (long)lseek(b, 0, SEEK_CUR));

    int out = open("redirected.txt", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    int saved = dup(STDOUT_FILENO);         /* 先備份原本的 stdout */
    fflush(stdout);
    dup2(out, STDOUT_FILENO);               /* fd 1 現在指向 redirected.txt */
    printf("這一行跑到檔案裡\n");
    fflush(stdout);
    dup2(saved, STDOUT_FILENO);             /* 還原 */
    printf("情況四 dup2：還原 stdout 後，檔案有 %ld bytes\n", (long)lseek(out, 0, SEEK_END));
    close(a); close(b); close(d); close(out); close(saved);
    unlink(path); unlink("redirected.txt");
    return 0;
}
```

執行結果：

```text
情況一 兩次 open：a 讀了兩次、b 讀一次，b 讀到 '0'
情況二 dup：a 讀過兩個 byte，d 接著讀到 '2'
情況三 fork：子程序讀走一個 byte，父程序接著讀到 '4'
a 的 offset = 5、b 的 offset = 1
情況四 dup2：還原 stdout 後，檔案有 25 bytes
```

對照 27.8 節的表格：

1. **兩次 `open`**：`a` 讀了 `'0'`、`'1'`，但 `b` 讀到的仍是 `'0'`。兩個 fd 指向不同的 open file table 項目，各有自己的位置。
2. **`dup`**：`d` 和 `a` 指向同一個項目，`a` 已經讀到位置 2，所以 `d` 接著讀到 `'2'`，位置變成 3。
3. **`fork`**：子行程透過 `a` 讀走 `'3'`，位置變成 4；父行程再透過 `a` 讀到 `'4'`。父子行程共用同一個項目，所以最後 `a` 的位置是 5，而 `b` 一直停在 1。
4. **`dup2`**：fd 1 暫時指向 `redirected.txt`，`printf` 的那一行進了檔案（中文每個字在 UTF-8 中佔 3 bytes，8 個字加換行共 25 bytes），還原後的輸出又回到終端機。注意重導向前後各呼叫了一次 `fflush(stdout)`，否則 stdio 緩衝區裡的資料可能在 fd 1 已經換掉之後才寫出，跑到錯誤的地方去。

### 實驗四：stdio 緩衝區被 fork 複製

子行程把 stdout 接到 pipe（於是變成完全緩衝），`printf` 一行 log 後 `fork`，父行程數 pipe 中出現了幾行。

```c
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

/* 執行一次「先 printf、再 fork」，把子程序的 stdout 接到 pipe 上來數行數 */
static int run_once(int flush_before_fork) {
    int fds[2];
    pipe(fds);
    pid_t pid = fork();
    if (pid == 0) {
        dup2(fds[1], STDOUT_FILENO);       /* stdout 變成 pipe → 完全緩衝 */
        close(fds[0]); close(fds[1]);
        printf("thumbd: worker starting\n");  /* 這行還在 stdio 的緩衝區裡 */
        if (flush_before_fork) fflush(stdout);
        if (fork() == 0) exit(0);          /* 孫程序：exit() 會沖出「繼承來的」緩衝區 */
        wait(NULL);
        exit(0);                           /* 子程序也沖出自己的那一份 */
    }
    close(fds[1]);
    char buf[256] = {0};
    ssize_t total = 0, r;
    while ((r = read(fds[0], buf + total, sizeof buf - 1 - (size_t)total)) > 0) total += r;
    close(fds[0]);
    waitpid(pid, NULL, 0);
    int lines = 0;
    for (char *p = buf; (p = strchr(p, '\n')); p++) lines++;
    return lines;
}

int main(void) {
    int n1 = run_once(0);
    int n2 = run_once(1);
    printf("fork 前沒有 fflush：同一行 log 出現 %d 次\n", n1);
    printf("fork 前先 fflush ：同一行 log 出現 %d 次\n", n2);
    return 0;
}
```

執行結果：

```text
fork 前沒有 fflush：同一行 log 出現 2 次
fork 前先 fflush ：同一行 log 出現 1 次
```

沒有 `fflush` 時，`"thumbd: worker starting\n"` 還在子行程的 stdio 緩衝區裡，`fork` 把緩衝區連同內容一起複製給孫行程，兩者在 `exit` 時各寫一次，所以出現兩次。先 `fflush` 的話，資料在 `fork` 之前已經透過 `write` 交給 kernel，緩衝區是空的，只會出現一次。在真實的 `thumbd` 中，這個 bug 的樣子是：log 收集程式裡，每次啟動外部轉檔工具前的最後幾行 log 都莫名其妙地重複。

## 27.13 在工作上怎麼用

### 情境一：修好 thumbd 的快取寫入

把 27.11 節的步驟寫成函式。這支程式也順便用 `stat` 驗證檔案類型、大小與 umask 計算的結果：

```c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int writen(int fd, const char *p, size_t n) {
    while (n > 0) {
        ssize_t w = write(fd, p, n);
        if (w < 0) { if (errno == EINTR) continue; return -1; }
        p += w; n -= (size_t)w;
    }
    return 0;
}

/* 原子地替換 path：先寫暫存檔、fsync、rename，最後 fsync 所在目錄。
 * 任一步失敗都不會留下「寫一半」的 path。 */
static int atomic_write_file(const char *dir, const char *name, const char *data, size_t n) {
    char tmp[256], dst[256];
    snprintf(tmp, sizeof tmp, "%s/.%s.tmp", dir, name);
    snprintf(dst, sizeof dst, "%s/%s", dir, name);
    int fd = open(tmp, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) return -1;
    if (writen(fd, data, n) < 0 || fsync(fd) < 0) { close(fd); unlink(tmp); return -1; }
    if (close(fd) < 0 || rename(tmp, dst) < 0) { unlink(tmp); return -1; }
    int dfd = open(dir, O_RDONLY);                 /* rename 是目錄的修改，也要落地 */
    if (dfd >= 0) { fsync(dfd); close(dfd); }
    return 0;
}

int main(void) {
    umask(022);                                    /* 常見的預設 umask */
    const char *thumb = "fake-jpeg-bytes...";
    if (atomic_write_file(".", "cat_200.jpg", thumb, strlen(thumb)) < 0) { perror("write"); return 1; }
    struct stat st;
    if (stat("./cat_200.jpg", &st) < 0) { perror("stat"); return 1; }
    printf("一般檔案？%s，大小 %lld bytes，權限 %o\n",
           S_ISREG(st.st_mode) ? "是" : "否", (long long)st.st_size, (unsigned)(st.st_mode & 0777));
    stat(".", &st);
    printf("「.」是目錄？%s\n", S_ISDIR(st.st_mode) ? "是" : "否");
    unlink("./cat_200.jpg");
    return 0;
}
```

在 macOS arm64 上執行：

```text
一般檔案？是，大小 18 bytes，權限 644
「.」是目錄？是
```

權限是 `644`，正好是 27.4 節手算的 `0666 & ~022`。`thumbd` 換成這個函式之後，磁碟快滿時 `writen` 會在 `write` 回傳 −1（`ENOSPC`）時失敗並刪掉暫存檔，不會再產生半張縮圖；停電也只會讓最後幾個縮圖「不存在」（下次請求時重新產生），不會留下大小為 0 的檔案。

### 情境二：用 strace 看真實的 I/O 行為

懷疑 short count 或 I/O 次數過多時，最直接的方法是看 system call（Linux；以下為示意輸出）：

```bash
strace -f -e trace=read,write,openat,close -p <thumbd 的 PID>
```

```text
openat(AT_FDCWD, "/var/cache/thumbd/.a.jpg.tmp", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 17
write(17, "\377\330\377\340\0\20JFIF..."..., 48213) = 32768
write(17, "\215\3029\v..."..., 15445) = -1 ENOSPC (No space left on device)
```

看到 `write` 回傳值小於要求的長度，就是 short count；連續出現 1 byte 的 `read`，就是沒有緩衝的讀取。`strace -c` 可以統計每種 system call 的次數與耗時，快速找出「每個請求 `read` 了幾千次」這類問題。

### 情境三：fd 洩漏與 EMFILE

`thumbd` 某天開始對所有請求回傳 500，log 裡是 `accept: Too many open files`。這是 fd 洩漏：某條錯誤路徑 `open` 了檔案卻沒有 `close`，累積到 `ulimit -n` 的上限後，連新的連線都無法接受（socket 也是 fd）。檢查方法：

```bash
ls /proc/<PID>/fd | wc -l           # 目前打開了幾個 fd
ls -l /proc/<PID>/fd | awk '{print $NF}' | sort | uniq -c | sort -n | tail   # 哪個檔案被打開最多次
lsof -p <PID>                        # 每個 fd 指向什麼
ulimit -n                            # 上限
```

修法和第 26 章的 memory leak 一樣：用單一出口的 `goto out` 結構確保每個錯誤路徑都 `close`。另外，`thumbd` 會 `fork`／`exec` 外部工具，所有 `open` 都應該加上 `O_CLOEXEC`，否則父行程打開的每個 fd 都會被子行程繼承，在子行程結束前都不會真正關閉，pipe 的 EOF 也可能因此等不到。

### 情境四：磁碟被「已刪除」的檔案佔滿

阿哲發現 `df` 顯示磁碟幾乎滿了，`du` 加總卻少了 20 GB。原因是 `thumbd` 的 log 檔被 log 輪替工具改名並刪除，但 `thumbd` 還握著舊的 fd，持續寫入那個已經沒有名稱的 inode。27.7 節提過，`st_nlink` 為 0 的檔案只要還有人打開，空間就不會被釋放。

```bash
lsof +L1        # 列出 link 數小於 1（已刪除）但仍被打開的檔案
```

解法是讓 `thumbd` 在收到 SIGHUP 時重新打開 log 檔（第 22 章），並讓 log 輪替工具在改名後送出 SIGHUP；或者改用 `O_APPEND` 打開 log，搭配「複製後截斷」的輪替方式。

### 檢查清單：寫 I/O 程式碼時

- 每個 `read`／`write` 都包在處理 short count 與 `EINTR` 的迴圈裡。
- 每個 `open` 都有對應的 `close`，包括錯誤路徑；需要 `fork`／`exec` 的程式一律加 `O_CLOEXEC`。
- socket 上用自己的緩衝讀取器，不用 Standard I/O。
- `fork` 之前 `fflush` 所有輸出 stream；子行程用 `_exit` 結束。
- 不能留下半個檔案的寫入，用「暫存檔＋`fsync`＋`rename`＋目錄 `fsync`」。
- 檢查 `close` 的回傳值，但不要以為 `close` 成功就代表資料已經寫到磁碟。

## 27.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 檔案或傳輸的資料被截斷，大小不固定 | 沒有處理 short count | `strace` 看 `read`／`write` 的回傳值小於要求量 | 用 `readn`／`writen` 迴圈 |
| 讀 pipe 永遠等不到 EOF，程式卡住 | 還有 process（常常是自己）握著寫端 fd | `lsof` 或 `/proc/PID/fd` 看誰還開著寫端 | `fork` 後關掉不用的那一端；加 `O_CLOEXEC` |
| `Too many open files`（EMFILE） | fd 洩漏 | `/proc/PID/fd` 的數量持續成長 | 錯誤路徑也要 `close`；用 `goto out` |
| 輸出到檔案或 pipe 時 log 延遲出現、當機後遺失最後幾行 | stdout 在非終端機時是完全緩衝 | 改成輸出到終端機時就正常 | 重要訊息寫 `stderr`、`fflush`，或用 `setvbuf` 設為行緩衝 |
| `fork` 之後 log 重複出現 | stdio 緩衝區被複製 | 只有輸出被重導向時才發生 | `fork` 前 `fflush`；子行程用 `_exit` |
| 讀完 HTTP header 後 body 少了開頭一段 | 混用帶緩衝的讀取與直接 `read` | 少掉的長度剛好是緩衝區裡剩下的量 | 同一個 fd 只用同一個帶緩衝的讀取器 |
| 停電或當機後檔案是空的或半截 | 只 `write` 沒 `fsync`，或直接覆寫正式檔案 | 檢查寫檔流程是否用了 `O_TRUNC` 直接寫正式檔 | 暫存檔＋`fsync`＋`rename` |
| `df` 顯示磁碟滿，`du` 卻沒那麼多 | 已刪除的檔案仍被打開 | `lsof +L1` | 重新打開 log 檔，或重啟持有 fd 的 process |

## 27.15 動手練習

1. **手算 file position**：檔案 `pic.txt` 的內容是 `thumbd`（6 bytes）。程式依序執行：`fd1 = open("pic.txt", O_RDONLY); fd2 = open("pic.txt", O_RDONLY); read(fd2, &c, 1); dup2(fd2, fd1); read(fd1, &c, 1);`，最後 `c` 是什麼？畫出每一步之後的 descriptor table 與 open file table。（答案：`'h'`。`dup2` 之後 `fd1` 指向 `fd2` 的項目，位置已經是 1，所以讀到第 2 個字元。可以把這段寫成程式驗證。）
2. **手算 umask**：umask 是 `077` 時，`open(path, O_CREAT | O_WRONLY, 0666)` 建立的檔案權限是多少？`mkdir(path, 0777)` 呢？（答案：`0600` 與 `0700`。）用 27.13 節的程式改 `umask` 驗證。
3. **延伸實驗一**：把子行程改成每次只寫 1,000 bytes、寫 262 次，並在父行程記錄每次 `read` 回傳的量。觀察回傳量的分佈，解釋為什麼它和寫端的寫法有關。
4. **延伸實驗二**：在 `linebuf_t` 上加一個 `lb_readn(lb, buf, n)`，從同一個緩衝區讀 n bytes。用它解析一個「先一行 `Content-Length: N`，接著 N bytes 資料」的小檔案，並故意改用直接 `read` 讀資料部分，觀察少掉了哪些 bytes。
5. **寫一個迷你 shell 重導向**：寫一支程式，接受 `prog args... > file` 形式的參數，用 `fork`、`open`、`dup2`、`execvp` 實作輸出重導向（可以接續第 21 章的 shell 練習）。
6. **在工作上**：在 Linux 上對你維護的服務執行 `strace -c -f -p <PID>` 十秒，找出 `read`／`write` 的次數與平均每次的 bytes 數。如果平均值很小，評估是否該加上緩衝。

## 本章重點整理

- Unix 把所有 I/O 裝置抽象成 byte 序列的檔案，用 `open` 取得 file descriptor，再用 `read`、`write`、`lseek`、`close` 操作；每個 process 開始時就有 fd 0、1、2。
- Regular file、directory、symlink、pipe、socket、device 都是檔案，但行為不同；pipe 與 socket 沒有 file position，不能 `lseek`。
- `open` 建立檔案時的權限是 `mode & ~umask`，例如 `0666 & ~022 = 0644`。
- `read` 回傳 0 代表 EOF，回傳 −1 代表錯誤並設定 `errno`；EOF 是「沒有資料可讀」的狀態，不是特殊字元。
- Short count 是正常行為：遇到 EOF、從終端機、pipe、socket 讀、磁碟快滿或被 signal 打斷時，`read`／`write` 都可能處理少於要求的量。
- 健全的 I/O 程式把讀寫包在迴圈裡，處理 short count 與 `EINTR`；CS:APP 的 RIO 提供無緩衝的 `readn`／`writen` 與帶緩衝的行讀取。
- 帶緩衝區的讀取一次向 kernel 要一大塊，大幅減少 system call；但同一個 fd 不能混用帶緩衝與不帶緩衝的讀取。
- `stat`／`fstat` 取得檔案的 metadata：大小、類型、權限、修改時間；`opendir`／`readdir` 讀目錄。
- kernel 用 descriptor table（每個 process）、open file table（記錄 file position 與 refcnt）、v-node table（檔案 metadata）三層記錄打開的檔案。
- 兩次 `open` 得到獨立的位置；`dup`、`dup2` 與 `fork` 讓 fd 指向同一個 open file 項目，共用位置；所有參照都 `close` 後項目才釋放，pipe 的 EOF 也依賴這點。
- Shell 的 `>` 與 `|` 是在子行程中用 `dup2` 把 fd 0 或 1 換掉，再 `execve`。
- Standard I/O 在使用者空間有緩衝區：終端機上的 stdout 行緩衝，導向檔案或 pipe 時完全緩衝，stderr 不緩衝；`fork` 會複製未寫出的緩衝區。
- Socket 上不要用 Standard I/O；signal handler 中只能用 `write`。
- `write` 成功只代表資料進了 page cache；要保證斷電後仍在，需要 `fsync`；要避免半個檔案，用暫存檔＋`fsync`＋`rename`＋目錄 `fsync`。

## 延伸問答

> [!question]- Q1. 為什麼 `read` 回傳 0 和回傳 −1 要分開處理？如果把兩者都當成「結束」會怎樣？
> 回傳 0 代表 EOF：對檔案是讀到結尾，對 pipe 是所有寫端都關閉了，對 socket 是對方正常關閉連線。這是正常的結束條件，已經讀到的資料是完整的。回傳 −1 則代表出錯，要看 `errno`：如果是 `EINTR`，只是被 signal 打斷，應該重試；如果是 `ECONNRESET` 或 `EIO`，資料可能不完整，不能當成成功處理。
>
> 把兩者混為一談，最常見的後果是：被 signal 打斷的 `read` 被當成 EOF，程式誤以為資料已經讀完，留下截斷的結果；或者連線異常中斷時，程式仍把收到的半份資料當成完整的請求處理。正確的迴圈必須分別處理 `r > 0`、`r == 0`、`r < 0 && errno == EINTR` 與其他錯誤四種情況。

> [!question]- Q2. 你在 production 看到 `thumbd` 上傳到物件儲存的縮圖偶爾被截斷，但本機磁碟上的檔案都完整。可能的原因是什麼？
> 本機檔案完整表示產生縮圖的部分沒有問題，問題出在傳送的那一段。把資料寫到 socket 時，`write` 很容易回傳 short count：socket 的傳送緩衝區滿了、網路壅塞、或寫到一半被 signal 打斷。如果上傳程式只呼叫一次 `write` 而沒有檢查回傳值，送出去的就只有前半段，接收端在連線關閉時收到的是截斷的檔案。
>
> 確認方法是在 Linux 上用 `strace -e trace=write,sendto -p <PID>` 觀察寫到 socket 的回傳值是否小於要求的長度。修法是用 `writen` 這樣的迴圈寫滿所有資料，並在協定層面加上長度（例如 HTTP 的 `Content-Length`）或檢查碼，讓接收端能發現資料不完整。

> [!question]- Q3. 手算題：檔案 `abc.txt` 內容為 `abcdef`。程式先 `fd = open("abc.txt", O_RDONLY)`，讀 2 bytes，然後 `fork`。子行程讀 1 byte 後結束；父行程 `wait` 之後讀 1 byte。父行程讀到什麼？如果改成子行程自己重新 `open` 一次再讀呢？
> 前兩個 bytes `ab` 被讀走後，位置是 2。`fork` 讓子行程的 fd 指向同一個 open file table 項目，子行程讀到 `c`，共用的位置變成 3。父行程 `wait` 之後再讀，從位置 3 開始，讀到 `d`。
>
> 如果子行程自己再 `open` 一次，會建立一個新的 open file table 項目，位置從 0 開始，子行程讀到的是 `a`，而且完全不影響父行程的項目。父行程之後讀到的就是位置 2 的 `c`。這題的關鍵是判斷兩個 fd 是否指向同一個項目：`fork` 與 `dup` 共用，新的 `open` 不共用。

> [!question]- Q4. 為什麼程式直接在終端機執行時 log 正常，用 systemd 或 Docker 跑時 log 卻延遲出現，當機時還會少掉最後幾行？
> Standard I/O 根據 stdout 連到什麼來決定緩衝模式：連到終端機時是行緩衝，每個 `\n` 就寫出；連到檔案或 pipe（systemd 的 journal、Docker 的 log driver 都是透過 pipe 或 socket 接收）時是完全緩衝，要等緩衝區滿才寫出。所以 log 會一批一批出現。
>
> 程式當機（例如 SIGSEGV）時，process 被 kernel 直接終止，不會執行 `exit` 的清理，stdio 緩衝區裡還沒寫出的 log 就跟著消失，而這幾行往往正是最需要的。解法包括：重要的 log 寫到不緩衝的 `stderr`；在程式啟動時用 `setvbuf(stdout, NULL, _IOLBF, 0)` 改成行緩衝；或者 log 函式庫直接用 `write` 輸出完整的一行。

> [!question]- Q5. 面試題：`fsync` 之後，資料就一定不會因為斷電而遺失嗎？
> `fsync` 的語意是要求 kernel 把這個檔案的資料與 metadata 寫到儲存裝置，並等到裝置回報完成才回傳。在正常的硬體與檔案系統上，這就是應用程式能取得的最強保證。但它有幾個前提：儲存裝置要正確處理 flush 命令（有些裝置的寫入快取在斷電時會遺失資料，企業級裝置通常有斷電保護）；只 `fsync` 檔案並不保證「新建立或改名」的目錄項目也已落地，所以還要 `fsync` 所在的目錄。平台差異也要注意：macOS 的 `fsync(2)` 手冊明說它不保證磁碟把自己的寫入快取清空，需要這個保證的程式（例如資料庫）要改用 `fcntl(fd, F_FULLFSYNC)`。
>
> 另外，`fsync` 回傳錯誤時，不能假設重試就能成功：在 Linux 上，寫回失敗之後 page cache 中的 dirty 頁可能已經被標記為乾淨，資料實際上已經遺失。資料庫社群在 2018 年前後對這個行為有過廣泛討論，結論是 `fsync` 失敗應該被視為嚴重錯誤，通常要讓程式從可靠的來源（例如 log）復原，而不是單純重試。

> [!question]- Q6. 為什麼網路程式不建議用 `fdopen` 把 socket 包成 `FILE *`，再用 `fgets`／`fprintf` 讀寫？
> 一個可讀寫的 stream 有兩條規則：輸出之後要輸入，必須先 `fflush` 或重新定位；輸入之後要輸出，必須先重新定位（`fseek` 等）。socket 不支援 `lseek`，第二條規則無法滿足。常見的變通是對同一個 socket 開兩個 stream，一個專門讀、一個專門寫，但關閉時兩個 stream 都會 `close` 同一個 fd，第二次關閉可能關到別的執行緒剛打開的檔案。
>
> 此外，stdio 的緩衝讓程式很難精確掌握「資料什麼時候真的送出」與「緩衝區裡還剩多少沒處理」，在需要處理 short count、逾時與協定邊界的網路程式中，這些都是必須掌控的細節。因此 CS:APP 建議網路程式用 Unix I/O 加上 RIO 這類自己寫的緩衝讀取器，第 28、29 章的 echo server 與 web server 都採用這個做法。

> [!question]- Q7. 程式找錯：`while ((n = read(fd, buf, sizeof buf)) > 0) write(out, buf, n);` 這個複製檔案的迴圈有什麼問題？
> 第一，`write` 的回傳值沒有檢查。寫入 pipe、socket 或快滿的磁碟時，`write` 可能只寫了一部分，剩下的資料就被下一輪 `read` 的內容覆蓋而遺失；`write` 回傳 −1 時也完全不知道。應該把 `write(out, buf, n)` 換成會寫滿 n bytes 並檢查錯誤的 `writen`。
>
> 第二，迴圈在 `read` 回傳 −1 時也會結束，但程式分不出是 EOF 還是錯誤。如果是 `EINTR` 應該重試，如果是其他錯誤應該回報失敗，而不是假裝複製成功。迴圈結束後應該檢查 `n < 0` 的情況。讀端的 short count 在這個迴圈中倒是沒有問題，因為每次只寫出實際讀到的 `n` bytes。

> [!question]- Q8. 為什麼 shell 實作 `cmd > file` 時要在子行程中做 `dup2`，而不是在 shell 自己的 process 中做？
> `dup2(fd, 1)` 會改變呼叫者 process 的 descriptor table，讓 fd 1 指向檔案。如果 shell 在自己身上做，之後 shell 自己的提示字元與所有後續命令的輸出都會跑到那個檔案裡，除非再花工夫備份與還原。在 `fork` 之後的子行程中做，只會改變子行程的 descriptor table，shell 的 fd 1 仍然指向終端機。
>
> 接著子行程呼叫 `execve` 載入 `cmd`。`execve` 會替換程式的程式碼與資料，但保留 descriptor table（除非 fd 設了 `O_CLOEXEC`），所以 `cmd` 一開始就把 fd 1 當成標準輸出，寫進的就是檔案。這也是 `fork` 與 `exec` 分成兩個 system call 的好處之一：在兩者之間，子行程可以自由調整 descriptor、環境變數與工作目錄，再變成新程式。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 10 章，以及 RIO 套件的完整原始碼。
- [Linux man pages](https://man7.org/linux/man-pages/)：`open(2)`、`read(2)`、`write(2)`、`dup(2)`、`fsync(2)`、`rename(2)`、`stat(2)`、`pipe(7)`。
- [POSIX.1-2024（The Open Group Base Specifications）](https://pubs.opengroup.org/onlinepubs/9799919799/)：`read`、`write` 與 stream 在標準中的確切語意。
- [CS:APP 3e 勘誤表](https://csapp.cs.cmu.edu/3e/errata.html)：閱讀第 10 章時對照。
