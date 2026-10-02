---
chapter: 24
title: Linux 虛擬記憶體與 mmap
part: 7
---

# 第 24 章　Linux 虛擬記憶體：Process 位址空間、mmap 與 Copy-on-Write

> [!abstract] 本章地圖
> **核心問題**：第 23 章的硬體只會「查表、翻譯、發 page fault」，Linux 怎麼用這套機制，組出 process 的位址空間、檔案映射、共享記憶體與便宜的 `fork`？
>
> **你會學到**：
> - 讀懂 `/proc/PID/maps` 的每一欄，說出每一段 mapping 是什麼、權限是什麼、背後是檔案還是匿名記憶體
> - 描述 Linux 收到 page fault 之後的判斷流程，並分辨 minor fault、major fault、copy-on-write 與 `SIGSEGV`／`SIGBUS`
> - 用 `mmap` 讀大檔、建立共享記憶體，並說明 `MAP_SHARED` 與 `MAP_PRIVATE` 的差別
> - 解釋 `fork` 為什麼不會真的複製整個位址空間，以及它在什麼情況下仍然很貴
> - 手算 RSS、PSS、USS，判斷一個服務真正佔了多少記憶體，並理解 OOM killer 怎麼挑選要殺的 process
>
> **前置知識**：第 23 章（page table、page fault、VSZ 與 RSS）、第 18 章（ELF 與 section）、第 21 章（`fork` 與 `execve`）
>
> **對應 CS:APP 3e**：第 9 章 9.7–9.8 節

## 24.1 故事：凌晨三點的 OOM killer

拾光相簿上線了「原圖下載與高解析縮圖」功能之後，`thumbd` 開始收到攝影師上傳的大檔：一張 1 億像素的 TIFF 動輒 200 到 300 MB。某天凌晨三點，SRE 阿哲被 page 叫醒：`thumbd` 在三台機器上同時消失，`dmesg` 裡只留下一段 OOM 報告，最後一行是 `Out of memory: Killed process 4127 (thumbd) …`。

小安隔天早上看程式碼，發現讀檔的寫法很直覺：`fstat` 拿到檔案大小，`malloc` 一塊同樣大的緩衝區，`read` 把整個檔案讀進來，再交給解碼器。十六個 worker thread 同時處理大圖時，光是原圖緩衝區就要好幾 GB。老周看完說：「檔案本來就在 page cache 裡，你又用 `read` 複製一份到 heap。改成 `mmap`，讓解碼器直接讀 page cache 的那一份。」

小安照做之後，同樣的流量下 OOM 再也沒有發生。但小安心裡有一串問題：`mmap` 之後檔案內容「在」記憶體的哪裡？為什麼 `top` 上的 RSS 看起來沒少多少，`smaps` 裡卻顯示它們大多是「可回收」的？`thumbd` 用 `fork` 呼叫外部轉檔工具時，一個 RSS 6 GB 的 process 被複製，為什麼不會瞬間吃掉另外 6 GB？

這些問題的答案，都在 Linux 怎麼「使用」第 23 章那套硬體機制。page table 只是工具，真正決定一個位址該對到什麼、第一次碰到時該怎麼處理的，是 kernel 裡一份以「區域」為單位的記錄。這一章就從這份記錄開始。

## 24.2 從硬體到 kernel：Linux 怎麼記錄一個 process 的記憶體

第 23 章講到，page fault 發生時 kernel 要先判斷「這個位址屬不屬於合法區域」。這個判斷不能靠 page table 本身：一個剛 `mmap` 完、還沒碰過的區域，PTE 全部是無效的，和「根本沒有映射」的位址在 page table 裡長得一模一樣。kernel 需要另一份資料，記錄「process 宣告過要用哪些範圍、每個範圍是什麼」。

Linux 為每個 process 維護一個 **`mm_struct`**（memory descriptor，記憶體描述子），裡面有兩樣最重要的東西：指向第一層 page table 的指標（context switch 時載入 `CR3`），以及一組 **VMA**（virtual memory area，虛擬記憶體區域）。CS:APP 把 VMA 稱為 **area** 或 **segment**：位址空間中一段連續、屬性一致的範圍。例如 `thumbd` 的程式碼是一個 VMA，heap 是一個 VMA，每個 thread 的 stack、每個用 `mmap` 打開的原圖，也都各是一個 VMA。

```text
 task_struct（thumbd 的一個 thread）
      │ mm
      ▼
 ┌───────────────────────────┐
 │ mm_struct                  │
 │   pgd ──────────────────────────▶ 第一層 page table（硬體用）
 │   VMA 集合 ─┐              │
 └─────────────┼─────────────┘
               ▼
 ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
 │ VMA：程式碼       │   │ VMA：heap         │   │ VMA：IMG_8812.tif │
 │ 0x55d0..02000    │   │ 0x55d0..3e000    │   │ 0x7f2a..f2000    │
 │ ~0x55d0..09000   │   │ ~0x55d0..5f000   │   │ ~0x7f2a..f2000   │
 │ r-x、private     │ … │ rw-、private     │ … │ r--、shared      │
 │ file=thumbd      │   │ file=（匿名）     │   │ file=IMG_8812    │
 └──────────────────┘   └──────────────────┘   └──────────────────┘
```

圖中同一個 process 的所有 thread 指向同一個 `mm_struct`，這正是「thread 共享位址空間」在 kernel 裡的意思（第 30 章）。VMA 只是「宣告」：它說這段範圍合法、權限是什麼、資料該從哪裡來，但不保證任何一頁已經在實體記憶體裡。真正的 PTE 要等 page fault 時才由 kernel 依照 VMA 的內容填上。

| VMA 欄位 | 意義 | `thumbd` 的例子 |
|---|---|---|
| 起始、結束位址 | 範圍 `[start, end)`，一定是 page 的整數倍 | `0x7f2a1b5f2000`～`0x7f2a1d1f2000` |
| 權限 | 可讀、可寫、可執行 | 原圖映射只允許讀 |
| shared／private | 寫入要不要讓別人看到 | 原圖用 shared（唯讀時兩者效果相同） |
| 背後的檔案與 offset | 資料來源；匿名區域沒有檔案 | `/data/photos/IMG_8812.tif`，offset 0 |
| 其他旗標 | 例如 stack 可以往下長、`mlock` 鎖住、`madvise` 的提示 | thread stack 底下有一頁 guard |

VMA 的數量通常是幾十到幾千個，kernel 用平衡樹快速找出「某個位址落在哪個 VMA」。早期 Linux 用紅黑樹加串列，6.1 版之後換成一種叫 maple tree 的結構，但對使用者來說意義相同：給一個位址，很快就能找到它所屬的區域或確認不屬於任何區域。

> [!warning] 常見誤解
> 「`mmap` 會把檔案讀進記憶體。」不會。`mmap` 只新增一個 VMA，幾乎是瞬間完成，不讀任何資料。資料是在程式第一次碰到某一頁時，才由 page fault handler 讀進來。這就是第 23 章說的 demand paging 在檔案上的版本。

## 24.3 Process 位址空間的全貌

有了 VMA 的觀念，就可以看懂一個 Linux process 的完整位址空間。x86-64 目前用 48-bit 虛擬位址（第 23 章），但 64-bit 指標不能隨便填：第 47 bit 以上必須全部相同，這叫 **canonical address**（標準形式位址）。結果是位址空間被切成兩半：下半 `0x0000000000000000`～`0x00007fffffffffff`（128 TiB）給 user，上半 `0xffff800000000000` 以上給 kernel，中間是一大片永遠不合法的空洞。

```text
 0xffffffffffffffff ┌────────────────────────────┐
                    │ kernel（user mode 碰不到）  │
 0xffff800000000000 ├────────────────────────────┤
                    │   非 canonical，永遠不合法   │
 0x00007fffffffffff ├────────────────────────────┤
                    │ [vvar] [vdso]               │ kernel 提供給 user 的小頁
                    ├────────────────────────────┤
                    │ main thread 的 stack ↓      │ 0x7ffc…，往低位址長
                    │ （argv、envp、auxv 在頂端） │
                    ├────────────────────────────┤
                    │ mmap 區域 ↓                 │ 0x7f…，由高往低配置：
                    │  ・ld.so、libc、libjpeg      │  共享 library
                    │  ・thread stack＋guard page  │  每個 thread 一段
                    │  ・malloc 的大配置與 arena   │  匿名 mapping
                    │  ・mmap 的原圖檔案           │  檔案 mapping
                    ├────────────────────────────┤
                    │       （大片未使用）         │
                    ├────────────────────────────┤
                    │ heap ↑（brk）               │ 從 .bss 後面往上長
                    ├────────────────────────────┤
                    │ .bss  .data                 │ 可讀寫
                    │ .rodata                     │ 唯讀
                    │ .text                       │ 可讀、可執行
 0x000055…（PIE）   ├────────────────────────────┤
                    │ 第 0 頁附近：永遠不映射      │ 讓 NULL 指標必定當機
 0x0000000000000000 └────────────────────────────┘
```

從下往上讀這張圖。最低的一段位址刻意不映射（Linux 預設從 `vm.mmap_min_addr` 以上才允許映射，常見值 64 KiB），所以 `NULL` 和 `NULL + 小 offset` 的存取一定 segfault，而不是悄悄讀到東西。接著是執行檔本身：`.text`、`.rodata`、`.data`、`.bss`，它們來自 ELF 的 segment（第 18 章）。現代發行版預設把執行檔編成 PIE（position-independent executable，第 19 章），所以這一段通常從 `0x55` 或 `0x56` 開頭的隨機位址開始；非 PIE 的傳統位址是 `0x400000`。

heap 在 `.bss` 之後不遠處開始（ASLR 會在兩者之間加一段隨機間隔），由 `brk` 系統呼叫往高位址延伸（第 25 章會細講）。另一端，main thread 的 stack 在 user 空間頂端附近，往低位址長，預設上限由 `ulimit -s` 決定（常見 8 MiB）；在 x86-64 上，`[vvar]` 與 `[vdso]` 通常就放在 stack 上方不遠處（vDSO 是 kernel 映射進來、讓 `gettimeofday` 這類呼叫不必進 kernel 的小 library）。兩者之間的廣大空間是 mmap 區域：共享 library、thread stack、大的 `malloc`、檔案映射都在這裡，由 kernel 從高往低挑空位。

**ASLR**（address space layout randomization，位址空間配置隨機化）讓 stack、mmap 區域、heap 與 PIE 執行檔的起點每次執行都不同（第 11 章），攻擊者因此很難預測位址。這也是為什麼你每次跑程式印出的指標值都不一樣。

### 讀懂 `/proc/PID/maps`

Linux 把每個 process 的 VMA 列在 `/proc/PID/maps`，一行一個。下面是 `thumbd` 處理一張大圖時的節錄（示意輸出，位址與 inode 會因機器而不同，右側的「←」說明是本書加上的）：

```text
55d0c8a00000-55d0c8a02000 r--p 00000000 103:02 1835012  /usr/local/bin/thumbd
55d0c8a02000-55d0c8a09000 r-xp 00002000 103:02 1835012  /usr/local/bin/thumbd  ← .text
55d0c8a09000-55d0c8a0c000 r--p 00009000 103:02 1835012  /usr/local/bin/thumbd  ← .rodata
55d0c8a0c000-55d0c8a0d000 r--p 0000b000 103:02 1835012  /usr/local/bin/thumbd  ← RELRO
55d0c8a0d000-55d0c8a0e000 rw-p 0000c000 103:02 1835012  /usr/local/bin/thumbd  ← .data
55d0c9b3e000-55d0c9b5f000 rw-p 00000000 00:00 0         [heap]
7f2a10000000-7f2a10021000 rw-p 00000000 00:00 0         ← thread 的 malloc arena
7f2a10021000-7f2a14000000 ---p 00000000 00:00 0         ← arena 預留但未啟用
7f2a1b5f2000-7f2a1d1f2000 r--s 00000000 103:02 2490371  /data/photos/IMG_8812.tif
7f2a1d1f2000-7f2a1d1f3000 ---p 00000000 00:00 0         ← guard page
7f2a1d1f3000-7f2a1d9f3000 rw-p 00000000 00:00 0         ← worker thread 的 stack
7f2a1e200000-7f2a1e228000 r--p 00000000 103:02 3672     /usr/lib/x86_64-linux-gnu/libc.so.6
7f2a1e228000-7f2a1e3bd000 r-xp 00028000 103:02 3672     /usr/lib/x86_64-linux-gnu/libc.so.6
7ffd4c1e0000-7ffd4c201000 rw-p 00000000 00:00 0         [stack]
7ffd4c3f6000-7ffd4c3fa000 r--p 00000000 00:00 0         [vvar]
7ffd4c3fa000-7ffd4c3fc000 r-xp 00000000 00:00 0         [vdso]
```

| 欄位 | 例子 | 意義 |
|---|---|---|
| 位址範圍 | `7f2a1b5f2000-7f2a1d1f2000` | VMA 的 `[start, end)`；這段長 `0x1c00000` = 28 MiB |
| 權限 | `r--s` | 讀、寫、執行，第四個字元 `p` 是 private（copy-on-write）、`s` 是 shared |
| offset | `00028000` | 這段 mapping 從檔案的第幾個 byte 開始；匿名區域為 0 |
| 裝置 | `103:02` | 檔案所在裝置的 major:minor 編號，以十六進位印出（`103` 就是十進位的 259，NVMe 磁碟常見的 major）；匿名為 `00:00` |
| inode | `2490371` | 檔案的 inode 編號；匿名為 0 |
| 路徑或名稱 | `[heap]`、`[stack]` | 檔案路徑，或 kernel 給的特殊名稱；匿名 mapping 通常空白 |

幾個值得注意的地方。第一，同一個檔案 `thumbd` 被切成好幾個 VMA，因為各段權限不同：程式碼 `r-x`、常數 `r--`、可寫資料 `rw-`。一個 VMA 內權限一致，權限不同就必須分開。第二，`---p` 的區域什麼都不能做，它們是刻意保留的：guard page 讓 thread stack 用完時立刻 segfault，而不是悄悄寫進相鄰的記憶體；allocator 的預留區則是「先佔住位址，之後再用 `mprotect` 開放」。第三，原圖那一行是 `r--s`，offset 0，背後是真正的檔案，這就是小安改用 `mmap` 之後多出來的 VMA。

## 24.4 Linux 的 page fault 處理流程

第 23 章把 page fault 的處理畫成一個簡化的判斷。現在有了 VMA，可以把 Linux 實際的判斷順序完整列出來。CPU 觸發 page fault 時會告訴 kernel 兩件事：出事的位址（x86-64 存在 `CR2` 暫存器），以及存取的種類（讀、寫或取指令；是 user 還是 kernel mode；是 PTE 無效還是權限不符）。

```text
 page fault：位址 A、存取種類 K
   │
   ├─① A 落在某個 VMA 裡嗎？
   │     否 → 若 A 緊鄰 stack VMA 的下方且在上限內 → 擴大 stack，繼續
   │          其他情況 → SIGSEGV（SEGV_MAPERR：位址沒有映射）
   │
   ├─② K 符合 VMA 的權限嗎？（寫入需要 w、執行需要 x）
   │     否 → SIGSEGV（SEGV_ACCERR：位址存在但權限不符）
   │
   └─③ 合法的 fault，依 VMA 的種類處理：
         ├─ 匿名、第一次碰：讀 → 對到共用的「全零頁」；寫 → 配一頁、填零
         ├─ 檔案 mapping：到 page cache 找這一頁
         │     ├─ 在 cache 裡 → 直接對上（minor fault）
         │     ├─ 不在 → 從磁碟讀入（major fault）
         │     └─ 超出檔案結尾整頁 → SIGBUS
         ├─ 寫入 private 頁，但 PTE 是唯讀（copy-on-write）→ 複製一頁，改成可寫
         └─ 頁被換到 swap → 從 swap 讀回（major fault）
       更新 PTE → 返回 user mode，重新執行那條指令
```

這張圖有三個新東西是第 23 章沒講的。第一是 stack 的自動成長：main thread 的 stack VMA 一開始只有一小段，函式呼叫越來越深時，存取會落在 VMA 下方一點點的位置，kernel 認得這種情況就把 VMA 往下延伸。thread stack 則不會自動長，它是固定大小加 guard page。第二是 **全零頁**（zero page）：一個匿名區域如果只被讀、從沒被寫，kernel 讓它的 PTE 都指向同一個內容全為零的實體頁，以唯讀方式掛上，等第一次寫入時才真正配一頁。第三是 **`SIGBUS`**：位址在 VMA 裡、權限也對，但背後的檔案已經沒有那一頁的資料（例如檔案被截短），kernel 無法生出內容，只好送出 bus error。

### 手算：判斷每一次存取的結果

用 24.3 節的 maps 節錄，假設 `thumbd` 做了下面幾次存取。每一題都照著上圖的三個步驟判斷：

| 存取 | ① 在哪個 VMA？ | ② 權限？ | 結果 |
|---|---|---|---|
| 讀 `0x55d0c8a03010` | `.text`（`r-xp`） | 讀，允許 | 若 PTE 有效是 page hit；第一次碰則到 page cache 找 `thumbd` 執行檔那一頁（多半 minor） |
| 寫 `0x55d0c8a03010` | `.text`（`r-xp`） | 寫，不允許 | `SIGSEGV`（`SEGV_ACCERR`） |
| 寫 `0x7f2a10010000` | arena（`rw-p`，匿名） | 允許 | 第一次寫就配一頁填零（minor fault），之後 page hit |
| 寫 `0x7f2a10030000` | arena 預留區（`---p`） | 不允許 | `SIGSEGV`（`SEGV_ACCERR`） |
| 讀 `0x0000000000000010` | 沒有任何 VMA | — | `SIGSEGV`（`SEGV_MAPERR`），典型的 `NULL->field` |
| 讀 `0x7f2a1d1f2800` | guard page（`---p`） | 不允許 | `SIGSEGV`，worker thread 的 stack 用完了 |
| 讀 `0x7f2a1c000000` | 原圖（`r--s`） | 允許 | 檔案在 page cache 就是 minor，否則 major |

第五列的判斷方法值得記住：`0x10` 比任何 VMA 的起點都小，所以是 `SEGV_MAPERR`，在 gdb 裡看到這種「很小的位址」幾乎都是對 `NULL` 指標取欄位，`0x10` 就是那個欄位在 struct 裡的位移（第 10 章）。第六列則說明 guard page 的價值：沒有它，stack 用完會默默寫壞下面那段記憶體，等到別處當機時才發現，非常難追。

> [!tip] `si_code` 告訴你是哪一種 segfault
> `SIGSEGV` 的 handler（第 22 章）或 core dump 中的 `siginfo` 有 `si_code` 與 `si_addr` 兩個欄位：`SEGV_MAPERR` 表示位址沒有映射，`SEGV_ACCERR` 表示權限不符，`si_addr` 就是出事的位址。gdb 用 `p $_siginfo` 可以直接看到它們。

## 24.5 Memory mapping：把物件對進位址空間

到目前為止，VMA 背後的資料來源有兩種：檔案，或「什麼都沒有」。CS:APP 把這種「把一個區域和一個磁碟上的物件關聯起來」的動作稱為 **memory mapping**（記憶體映射），Linux 的所有 VMA 都是用它建立的。

**檔案 mapping**（file-backed mapping）把一個普通檔案的某一段對到位址空間。第一次碰到某一頁時，kernel 到 **page cache**（頁快取）找這個檔案的這一頁。page cache 是 kernel 用空閒記憶體快取檔案內容的地方，`read`、`write`、`mmap` 共用同一份：剛被 `cp` 讀過的檔案、昨天被 `thumbd` 處理過的原圖，可能都還在 page cache 裡。找到了就把 PTE 指向它（minor fault），找不到才讀磁碟（major fault）。

**匿名 mapping**（anonymous mapping）沒有對應的檔案；原書的說法是把它對到一個由 kernel 建立、內容全為零的 anonymous file（匿名檔案）。第一次寫入某頁時，kernel 配一個實體頁並填零，所以這類頁也叫 **demand-zero page**（需要時才填零的頁）。heap、stack、`.bss`、大的 `malloc` 都是匿名的。

| | private（`MAP_PRIVATE`） | shared（`MAP_SHARED`） |
|---|---|---|
| 檔案 | 讀到檔案內容，寫入時複製一份私有的頁（copy-on-write），**不會**寫回檔案。用途：載入執行檔與 library 的程式碼和資料 | 讀寫都直接作用在 page cache 的那一頁，其他映射同一檔案的 process 看得到，之後會被寫回檔案。用途：資料庫檔案、`thumbd` 讀原圖 |
| 匿名 | 每個 process 自己的零頁。用途：heap、stack、`malloc` 的大配置 | 可以在 `fork` 之後的父子行程間共享。用途：父子行程共用的計數器或緩衝區 |

這四格涵蓋了 Linux user 空間裡所有的 mapping。一般 process 之間要共享記憶體，最常見的做法是 POSIX 的 `shm_open` 建立一個有名字的共享記憶體物件，再用 `MAP_SHARED` 映射；在 Linux 上，它其實是 `/dev/shm` 這個記憶體檔案系統（tmpfs）裡的一個檔案，所以本質上仍然是「檔案 mapping」。

### 記憶體不夠時，誰可以被丟掉

這兩種 mapping 在記憶體壓力下的命運完全不同，這是小安的 OOM 問題能被 `mmap` 解決的關鍵。

```text
 實體記憶體不夠了，kernel 要回收頁：

 檔案頁（page cache）                    匿名頁
 ┌───────────────────────────┐          ┌───────────────────────────┐
 │ clean（和磁碟一致）        │          │ 沒有檔案可以「重新讀回」   │
 │   → 直接丟掉，需要時再讀   │          │   有 swap → 寫到 swap，    │
 │ dirty（被 write 等改過）   │          │            需要時再讀回    │
 │   → 先寫回檔案，再丟掉     │          │   沒有 swap → 不能回收     │
 └───────────────────────────┘          └───────────────────────────┘
           便宜、隨時可回收                    昂貴，或根本無法回收
```

`thumbd` 原本的寫法，是把原圖從 page cache 再 `read` 一份到 heap：page cache 裡一份（可以丟），heap 裡一份（匿名、而伺服器沒有開 swap，所以丟不掉）。改用 `mmap` 之後，解碼器直接讀 page cache 那一份，沒有匿名的副本；記憶體緊張時 kernel 可以丟掉暫時沒在讀的部分，之後再從磁碟讀回來。代價只是可能多幾次 major fault，而不是整個 process 被殺掉。

> [!note] Swap 不是只給「記憶體不夠的窮機器」
> 很多伺服器關閉 swap，理由是「寧可被殺也不要變慢」。但這也表示所有匿名頁都無法回收，kernel 只能回收 page cache，壓力一大就直接 OOM。是否開 swap 是一個取捨，重點是知道匿名頁和檔案頁在回收時的差別。

## 24.6 Shared object 與 private copy-on-write

CS:APP 用 **shared object** 指「以 shared 方式映射的物件」：多個 process 映射同一個物件時，它們的 PTE 指向同一組實體頁，任何一方寫入，其他方立刻看得到。這裡的 shared object 和 `.so` 檔（shared library，第 19 章）是兩回事，只是名字很像；不過 `.so` 檔的程式碼頁在實體記憶體中只有一份，背後靠的正是同一套 mapping 機制。

**private object** 則用 **copy-on-write**（COW，寫入時才複製）實作：一開始多個 process 共用同一組實體頁，但 PTE 都標記為唯讀；任何一方嘗試寫入時觸發 protection fault，kernel 發現這是 private 且原本可寫的 VMA，就複製一份給寫入者、改成可寫，再重新執行那條寫入指令。

```text
 寫入前：兩個 process 都映射 libjpeg 的 .data（private）

  process A 的 PTE ──┐ 唯讀
                      ├──▶ 實體頁 #812（來自 libjpeg.so 的 page cache）
  process B 的 PTE ──┘ 唯讀

 A 寫入其中一個變數 → protection fault → kernel 檢查：VMA 可寫、private → COW

  process A 的 PTE ─────▶ 實體頁 #3305（#812 的副本） 可寫
  process B 的 PTE ─────▶ 實體頁 #812                 仍然唯讀
```

圖中有兩個重點。第一，COW 是「以頁為單位」：A 只改了一個 4 bytes 的變數，複製的是一整頁。第二，B 完全沒有感覺，它的 PTE 沒有被改動；如果之後 B 也寫入，B 也會得到自己的副本，原本的 #812 在沒有人使用後才被回收。

這個機制讓「每個 process 都有自己的一份 library 資料」的成本變得很低：只有真的被改過的頁才會複製，沒改過的頁全部共用。一台機器上跑一百個用 libc 的 process，libc 的程式碼和大部分唯讀資料在實體記憶體裡只有一份。

> [!warning] 常見誤解
> 「`MAP_PRIVATE` 映射檔案之後，檔案再被別人修改，我一定看不到。」不一定。POSIX 沒有規定這種情況；在 Linux 上，你還沒寫過（還沒被 COW 複製）的頁，仍然直接對到 page cache，別人修改後你會看到新內容；已經寫過的頁才是你的私有副本。需要穩定的快照，應該自己複製一份資料，或確保檔案不會被原地修改。

## 24.7 fork：用 copy-on-write 複製整個位址空間

第 21 章說 `fork` 會建立一個「和父行程一模一樣」的子行程，包括整個位址空間。如果真的把父行程的每一頁都複製一遍，一個 RSS 6 GB 的 `thumbd` 每次 `fork` 都要複製 6 GB，可能要好幾秒。實際上 Linux 的 `fork` 是這樣做的：

1. 為子行程建立新的 `mm_struct`，複製父行程的每一個 VMA。
2. 複製父行程的 page table，讓子行程的 PTE 指向**同一組實體頁**。需要複製的主要是含有匿名頁的區域（heap、stack、被寫過的 `.data`）；純檔案映射、從沒被寫過的區域，Linux 可以不複製 PTE，讓子行程之後再由 page fault 從 page cache 對上。
3. 把雙方所有可寫的 private 頁的 PTE 都改成唯讀，這些 private VMA 在雙方都成為 COW 區域。`MAP_SHARED` 的區域則不變，父子之後仍然共用同一份（24.5 節表格中「匿名 shared」的用途）。
4. 返回。之後任何一方寫入某頁，就觸發 24.6 節的 COW，只複製那一頁。

```text
 fork 之前                      fork 之後（還沒有人寫入）
 父：VMA heap（rw-p）          父：VMA heap（rw-p）  PTE 全部改為唯讀 ─┐
     PTE → 頁 P1、P2、P3                                                  ├→ P1 P2 P3
                               子：VMA heap（rw-p）  PTE 也是唯讀 ─────┘

 子程序寫入 P2 所在的位址 → COW
                               父：P1 P2 P3
                               子：P1 P2' P3        （只多出一頁 P2'）
```

所以 `fork` 的成本不是「複製資料」，而是「複製 VMA 和 page table、把 PTE 改成唯讀」。這比複製資料便宜得多，但不是零。用 `thumbd` 估算一下：

```text
RSS 6 GiB、page 4 KiB → 6 × 2^30 ÷ 2^12 = 1,572,864 個 PTE
每個 PTE 8 bytes      → 1,572,864 × 8 = 12 MiB 的最底層 page table 要複製
```

複製 12 MiB 的表、逐一調整每頁的計數與權限，加上之後兩邊都要重新處理 TLB，`fork` 本身可能要花上數十毫秒，依硬體、虛擬化環境與 kernel 版本而定（Redis 官方文件收錄的實測中，實體機大約每 GB RSS 10 毫秒上下，某些舊型虛擬機慢上一到兩個數量級）。更麻煩的是 `fork` 之後的 COW：如果父行程在子行程還活著的時候大量寫入，每一頁都要複製一次，RSS 可能接近翻倍。Redis 用 `fork` 做背景快照（子行程把記憶體寫到磁碟，父行程繼續服務），官方文件特別提醒 `fork` 的延遲與 COW 造成的額外記憶體，就是這個原因。

`thumbd` 呼叫外部轉檔工具時，子行程 `fork` 後立刻 `execve`，幾乎不寫任何頁，COW 幾乎不會發生；但 `fork` 本身複製 page table 的成本照付。這時更好的選擇是 `posix_spawn`，或 Linux 的 `vfork`／`clone(CLONE_VM | CLONE_VFORK)`：子行程暫時借用父行程的位址空間直接 `execve`，連 page table 都不複製。glibc 的 `posix_spawn` 在 Linux 上就是這樣實作的。

| 做法 | 複製 page table | COW 風險 | 適合 |
|---|---|---|---|
| `fork` 後繼續做事 | 是 | 父子任一方寫入就複製 | 需要子行程擁有父行程資料的快照（例如 Redis 背景存檔） |
| `fork` 後立刻 `execve` | 是 | 很小 | 傳統寫法，小行程沒問題，大 RSS 的行程會付明顯的 `fork` 延遲 |
| `posix_spawn`／`vfork` | 否 | 無 | 大型服務呼叫外部工具，例如 `thumbd` 呼叫轉檔程式 |

## 24.8 execve：丟掉舊的 mapping，建立新的

`fork` 複製位址空間，`execve` 則把它整個換掉。第 21 章從 process 的角度看 `execve`：同一個 PID，換成另一支程式。從 VM 的角度，`execve("/usr/bin/convert", argv, envp)` 做了這幾件事：

1. 刪除目前 process 所有的 user VMA 和對應的 page table（舊程式的一切都消失）。
2. 依照新執行檔 ELF 的 program header（第 18 章的 `PT_LOAD` segment），建立 private 的檔案 mapping。
3. 建立匿名的 `.bss` 與 heap 起點、建立新的 stack，把 `argv`、`envp` 和 auxiliary vector 複製到 stack 頂端。
4. 如果執行檔需要動態連結，再映射 dynamic loader（`ld-linux-x86-64.so.2`），由它接著映射 libc 等 library（第 19 章）。
5. 把 PC 設成進入點（loader 或程式本身的 `_start`）。

```text
 ELF 執行檔（磁碟上）                    新的位址空間（VMA）
 ┌────────────────────┐
 │ ELF header          │
 │ program headers     │
 ├────────────────────┤  PT_LOAD r-x   ┌─────────────────────────┐
 │ .text               │ ─────────────▶ │ 程式碼  r-xp（檔案）     │
 ├────────────────────┤  PT_LOAD r--   ├─────────────────────────┤
 │ .rodata             │ ─────────────▶ │ 常數    r--p（檔案）     │
 ├────────────────────┤  PT_LOAD rw-   ├─────────────────────────┤
 │ .data               │ ─────────────▶ │ 資料    rw-p（檔案，COW）│
 │ .bss（不佔檔案空間）│ ─ ─ ─ ─ ─ ─ ─▶ │ .bss    rw-p（匿名）     │
 └────────────────────┘                ├─────────────────────────┤
                                        │ heap（匿名，從空開始）   │
                                        │        ⋮                │
                                        │ ld.so、libc（之後映射） │
                                        │        ⋮                │
                                        │ stack：argv、envp、auxv  │
                                        └─────────────────────────┘
```

這張圖解釋了幾個常見問題。`.data` 是 private 的檔案 mapping，所以全域變數的初始值直接來自執行檔，改了也不會寫回檔案。`.bss` 在檔案裡不佔空間（第 18 章），因為它對到的是匿名的 demand-zero 頁，載入時根本不需要讀任何東西。而整個 `execve` 也沒有把程式「讀進記憶體」：它只建立 VMA，程式碼頁是在第一次執行到時才透過 page fault 讀入，這就是為什麼一個 100 MB 的執行檔可以瞬間啟動。

## 24.9 mmap 函式：介面、旗標與相關呼叫

使用者程式透過 `mmap` 系統呼叫自己建立 VMA：

```c
#include <sys/mman.h>

void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset);
int   munmap(void *addr, size_t length);
```

`mmap` 請 kernel 把 `fd` 這個檔案從 `offset` 開始、長 `length` bytes 的部分映射到位址空間，回傳映射的起點；失敗時回傳 `MAP_FAILED`（也就是 `(void *)-1`，不是 `NULL`）。`addr` 通常傳 `NULL`，讓 kernel 自己挑位址。

| 參數 | 常用值 | 說明 |
|---|---|---|
| `prot` | `PROT_READ`、`PROT_WRITE`、`PROT_EXEC`、`PROT_NONE` | 這段區域的權限，必須和 `fd` 的開啟模式相容（唯讀開的檔案不能 `MAP_SHARED` 加 `PROT_WRITE`） |
| `flags` | `MAP_SHARED` 或 `MAP_PRIVATE`（二選一） | 24.5 節的兩種語意 |
| | `MAP_ANONYMOUS`（`MAP_ANON`） | 不用檔案，`fd` 傳 −1 |
| | `MAP_POPULATE`（Linux） | 映射時就把頁全部載入，避免之後的 page fault |
| | `MAP_FIXED_NOREPLACE`（Linux） | 一定要用 `addr`，若已被佔用就失敗；舊的 `MAP_FIXED` 會默默蓋掉原本的 mapping，很危險 |
| | `MAP_NORESERVE` | 不為這段映射預留 swap 額度（見 24.11 節）；overcommit 模式 2 下會被忽略 |
| `offset` | page 大小的整數倍 | 不是整數倍會回傳 `EINVAL` |

`offset` 必須對齊 page 是初學者最常踩的坑。假設 `thumbd` 只想映射一張 TIFF 裡從第 10,000,000 個 byte 開始的影像資料，page 4 KiB：

```text
10,000,000 ÷ 4,096 = 2,441.40625     → 往下取整數 2,441 頁
對齊後的 offset = 2,441 × 4,096 = 9,998,336
多映射的前置量  = 10,000,000 − 9,998,336 = 1,664 bytes
→ mmap(NULL, len + 1664, PROT_READ, MAP_SHARED, fd, 9998336)
→ 真正的資料從回傳位址 + 1664 開始
```

寫成程式就是 `aligned = off & ~(page - 1)`、`delta = off - aligned`。page 大小要用 `sysconf(_SC_PAGESIZE)` 查，不要寫死 4096：Apple Silicon 的 macOS 是 16 KiB，部分 ARM Linux 也用 16 KiB 或 64 KiB。

除了 `mmap`／`munmap`，還有三個常一起出現的呼叫：

- **`mprotect(addr, len, prot)`**：改變一段已映射區域的權限。JIT 編譯器先寫入機器碼、再改成可執行（第 23 章的 W^X），allocator 把預留的 `PROT_NONE` 區域開放成可讀寫，都是用它。
- **`madvise(addr, len, advice)`**：給 kernel 存取模式的提示。`MADV_SEQUENTIAL` 表示會循序讀，kernel 可以積極預讀、讀過的頁早點丟掉；`MADV_WILLNEED` 請 kernel 先開始讀入；`MADV_DONTNEED` 表示這段暫時不需要，對 private 匿名區域而言，kernel 會釋放實體頁，之後再碰到時得到全新的零頁。第 25 章的 allocator 就是靠它把 free 掉的記憶體還給系統。
- **`msync(addr, len, MS_SYNC)`**：把 `MAP_SHARED` 區域中改過的頁寫回檔案並等待完成。注意寫入 `MAP_SHARED` 區域只保證「其他映射者看得到」，不保證已經落到磁碟；需要 durability 時要 `msync`（或對檔案 `fsync`，第 27 章）。

### mmap 和 read 怎麼選

`mmap` 不是「比較快的 `read`」，兩者各有適合的場景：

| 面向 | `read` 進緩衝區 | `mmap` |
|---|---|---|
| 記憶體副本 | page cache 一份 ＋ 你的緩衝區一份（匿名） | 只有 page cache 一份 |
| 隨機存取大檔 | 每次都要 `lseek`／`pread` 加系統呼叫 | 直接用指標，像操作陣列 |
| 小檔或只讀一次 | 簡單、成本低 | 建立 VMA、page fault、`munmap` 的固定成本可能比 `read` 高 |
| 錯誤處理 | 回傳值與 `errno`（第 27 章） | 讀到被截短的部分會收到 `SIGBUS`，I/O 錯誤也變成 signal |
| 檔案被別人改 | 你讀到的是當時的副本 | 你看到的內容可能跟著變 |
| 多個 process 共讀 | 各自一份副本 | 自動共用 page cache 的同一組實體頁 |

`thumbd` 的原圖讀取符合 `mmap` 的強項：檔案大、解碼器會隨機跳著讀（TIFF 的 strip、JPEG 的 marker）、同一張熱門圖片常被多個請求同時處理。但老周也提醒了 `SIGBUS` 的風險：如果有人在 `thumbd` 讀的時候把原圖原地截短，`thumbd` 會直接被 signal 打掉。拾光相簿的上傳服務一律寫入暫存檔再 `rename` 覆蓋，舊的 inode 在 `thumbd` 還映射時會繼續存在（第 27 章），所以這個風險在這裡被消除了。

## 24.10 記憶體到底用了多少：VSZ、RSS、PSS 與 USS

第 23 章已經區分了 VSZ（所有合法範圍）與 RSS（實際在實體記憶體的頁）。有了共享和 COW 之後，RSS 也不夠精確了：同一個實體頁被十個 process 共用，它會出現在十個 process 的 RSS 裡。Linux 因此提供了更細的指標：

| 指標 | 怎麼算 | 用途 |
|---|---|---|
| VSZ | 所有 VMA 的長度總和 | 偵測位址空間耗盡、不合理的預留 |
| RSS | 這個 process 的 PTE 指到的實體頁總和，共享頁全額計入 | `top` 的 RES，最常見但會重複計算 |
| PSS | 每個實體頁除以「共用它的 process 數」再加總 | 把一群 process 的 PSS 相加，就是它們真正佔的量 |
| USS | 只算這個 process 獨佔的頁 | 殺掉這個 process 能立刻釋放多少 |

### 手算：四個 thumbd worker 真正佔多少

假設在某台機器上以 prefork 模式跑四個 `thumbd` process，每個都有：100 MiB 私有匿名記憶體（解碼緩衝區與縮圖快取）；12 MiB 的 libc、libjpeg、libpng 程式碼頁，四個 process 共用；40 MiB 的浮水印與色彩設定檔，以 `MAP_SHARED` 映射同一個檔案，四個 process 共用。

```text
每個 process 的 RSS = 100 + 12 + 40 = 152 MiB
四個 RSS 相加       = 152 × 4       = 608 MiB   ← 監控面板常顯示這個，偏高

每個 process 的 PSS = 100 + 12/4 + 40/4 = 100 + 3 + 10 = 113 MiB
四個 PSS 相加       = 113 × 4           = 452 MiB   ← 真正佔用：400 + 12 + 40

每個 process 的 USS = 100 MiB             ← 殺掉一個 worker 能立刻釋放的量
```

這個算例說明為什麼「把每個 process 的 RSS 加起來」會高估一個多 process 服務的用量：共享的 52 MiB 被算了四次。PSS 的加總剛好等於真實用量 452 MiB。

在 Linux 上，`/proc/PID/smaps` 列出每個 VMA 的細項，`/proc/PID/smaps_rollup` 則是整個 process 的加總。下面是小安改用 `mmap` 之後在 `thumbd` 上看到的 rollup（示意輸出，只節錄部分欄位，數字為說明用）：

```text
$ cat /proc/4127/smaps_rollup
Rss:             2621440 kB
Pss:             2598012 kB
Pss_Anon:        1101320 kB
Pss_File:        1496692 kB
Shared_Clean:      36120 kB
Private_Clean:   1460572 kB
Private_Dirty:   1124748 kB
Anonymous:       1101320 kB
Swap:                  0 kB
```

這組數字回答了故事裡的疑問。RSS 還有約 2.5 GiB，看起來沒少多少；但其中 `Pss_File` 約 1.4 GiB 是 page cache 裡的原圖，它們大多算在 `Private_Clean`：clean 表示和檔案一致；這裡的 private 指「目前只有這個 process 映射這些頁」，和 `MAP_PRIVATE` 無關（一個 `MAP_SHARED` 的頁若只有一個 process 在用，也算 private）。clean 的檔案頁在記憶體不夠時 kernel 可以直接丟掉。真正丟不掉的是 `Anonymous` 那約 1 GiB。判斷一個服務的記憶體風險，要看匿名與 dirty 的部分，不能只看 RSS 一個數字。

## 24.11 記憶體不夠時：overcommit 與 OOM killer

`mmap` 一大塊匿名記憶體、或 `fork` 一個大 process，kernel 當下並沒有分配實體頁，只是答應「之後要用的時候會給」。如果所有 process 同時兌現承諾，實體記憶體加 swap 可能不夠。Linux 怎麼面對這種「超額承諾」，由 `vm.overcommit_memory` 決定：

| 值 | 名稱 | 行為 |
|---|---|---|
| 0 | heuristic（預設） | 用經驗法則拒絕明顯不可能滿足的請求，其餘都答應 |
| 1 | always | 永遠答應，不檢查 |
| 2 | never | 總承諾量不得超過 CommitLimit（大致是 swap ＋ RAM × `vm.overcommit_ratio`%，預設 50%）；超過就讓 `mmap`／`malloc` 失敗 |

在模式 0 與 1 下，`malloc` 幾乎不會回傳 `NULL`，問題被延後到「真的寫入那一頁、kernel 卻找不到可用的實體頁」的時候。這時 kernel 先嘗試回收 page cache、寫 swap；全部無效時，就啟動 **OOM killer**（out-of-memory killer），挑一個 process 殺掉來換取記憶體。

```text
 寫入新頁 → page fault → 需要一個實體頁
   │
   ├─ 有空閒頁？ ── 是 → 配給它，繼續
   │
   ├─ 回收：丟 clean page cache、寫回 dirty 頁、匿名頁換到 swap
   │     └─ 回收成功 → 配給它，繼續（但這段時間延遲飆高）
   │
   └─ 回收失敗 → OOM killer
          ├─ 對每個 process 算 badness：大致是 RSS ＋ swap ＋ page table，
          │  再加上 oom_score_adj（−1000～1000）的調整
          ├─ 分數最高的 process 收到 SIGKILL（無法攔截）
          └─ dmesg 留下 "Out of memory: Killed process …"
```

`thumbd` 在凌晨被殺，正是這條路徑的終點：十六個 worker 各自 `read` 一張 300 MB 的原圖進匿名緩衝區，機器沒有 swap，匿名頁無法回收，`thumbd` 又是 RSS 最大的 process，於是被選中。

在容器環境中多了一層：cgroup（control group）。Kubernetes 的 memory limit 會設定 cgroup v2 的 `memory.max`，容器內的匿名記憶體與 page cache 都計入；超過時 kernel 先在這個 cgroup 內回收，失敗就在 cgroup 內觸發 OOM，行程被 `SIGKILL`，Kubernetes 顯示 `OOMKilled`、結束碼 137（128 ＋ 9）。這時整台機器可能還有很多空閒記憶體，但容器自己的額度用完了。

| 調整 | 作用 | 注意 |
|---|---|---|
| `/proc/PID/oom_score_adj` | −1000 表示永遠不殺，1000 表示優先殺 | 保護關鍵 process（例如 sshd），但不要把所有服務都設成 −1000 |
| `vm.overcommit_memory=2` | 讓 `malloc` 在承諾不了時直接失敗 | 程式必須正確處理 `NULL`；`fork` 大 process 也可能失敗 |
| 容器 memory limit | 限制單一服務，不拖垮整台機器 | 要把 page cache 和 COW 的峰值算進去 |

## 24.12 動手做：mmap 讀大檔、私有與共享寫入、fork 的 copy-on-write

### 程式一：read 與 mmap，以及 MAP_PRIVATE 和 MAP_SHARED 的差別

這段程式先建立一個 16 MiB 的假原圖，再分別用 `read` 和 `mmap` 讀它，比較 minor fault；最後同時用 private 與 shared 兩種方式映射，觀察寫入能不能被檔案與另一個映射看到。

```c
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <unistd.h>

static long minflt(void) {
    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    return ru.ru_minflt;
}

int main(void) {
    const char *path = "photo.raw";
    size_t len = 16UL * 1024 * 1024;              /* 假裝這是一張 16 MiB 的原圖 */
    int fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { perror("open"); return 1; }
    char *chunk = calloc(1, 1 << 20);
    for (int i = 0; i < 16; i++)
        if (write(fd, chunk, 1 << 20) != 1 << 20) { perror("write"); return 1; }
    free(chunk);

    /* 方法一：read() 進 malloc 的緩衝區，資料會多一份副本 */
    long f0 = minflt();
    char *buf = malloc(len);
    if (!buf || pread(fd, buf, len, 0) != (ssize_t)len) { perror("pread"); return 1; }
    printf("read()  ：minor fault %5ld 次（緩衝區每一頁第一次被寫入）\n", minflt() - f0);
    free(buf);

    /* 方法二：mmap 把檔案直接對到位址空間，讀取時共用 page cache */
    f0 = minflt();
    unsigned char *p = mmap(NULL, len, PROT_READ, MAP_PRIVATE, fd, 0);
    if (p == MAP_FAILED) { perror("mmap"); return 1; }
    printf("mmap()  ：剛映射完 minor fault %ld 次\n", minflt() - f0);
    unsigned long sum = 0;
    for (size_t off = 0; off < len; off += 4096) sum += p[off];
    printf("mmap()  ：掃過整個檔案後 minor fault %5ld 次（sum=%lu）\n", minflt() - f0, sum);
    munmap(p, len);

    /* MAP_PRIVATE 與 MAP_SHARED 的寫入，誰看得到？ */
    char *priv = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, 0);
    char *shr  = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (priv == MAP_FAILED || shr == MAP_FAILED) { perror("mmap"); return 1; }
    char c;
    priv[0] = 'P';                                /* 寫在私有副本上 */
    pread(fd, &c, 1, 0);
    printf("寫 MAP_PRIVATE 後，檔案第 0 byte = %d，shared 映射看到 %d\n", c, shr[0]);
    shr[1] = 'S';                                 /* 寫在共享的 page cache 上 */
    pread(fd, &c, 1, 1);
    printf("寫 MAP_SHARED  後，檔案第 1 byte = '%c'，private 映射看到 %d\n", c, priv[1]);
    munmap(priv, len);
    munmap(shr, len);
    close(fd);
    unlink(path);
    return 0;
}
```

在 macOS arm64（Apple clang 21，page 16 KiB）上執行：

```text
read()  ：minor fault  1026 次（緩衝區每一頁第一次被寫入）
mmap()  ：剛映射完 minor fault 0 次
mmap()  ：掃過整個檔案後 minor fault  1024 次（sum=0）
寫 MAP_PRIVATE 後，檔案第 0 byte = 0，shared 映射看到 0
寫 MAP_SHARED  後，檔案第 1 byte = 'S'，private 映射看到 0
```

逐行解讀：

1. `read` 的版本有 1,026 次 minor fault：16 MiB ÷ 16 KiB = 1,024 頁，`malloc` 來的緩衝區每一頁第一次被 `pread` 寫入時都要配一個新的匿名頁，多出的 2 次來自 `malloc` 與程式其他部分第一次碰到的頁。這 1,024 頁是 page cache 之外**額外**的一份副本。
2. `mmap` 剛完成時 0 次 fault，證實 `mmap` 只建立 VMA，不讀任何東西。
3. 掃過整個檔案後是 1,024 次，和 `read` 差不多。差別不在 fault 次數，而在 fault 的內容：這裡每次 fault 只是把 PTE 指向 page cache 中已經存在的頁，沒有配置新的匿名記憶體。在 Linux 上，kernel 處理檔案 mapping 的 fault 時會順便把附近幾頁一起對上（fault-around），所以次數可能比頁數少。
4. 寫入 private 映射後，檔案內容與 shared 映射都還是 0：寫入觸發 COW，`priv` 拿到自己的副本。
5. 寫入 shared 映射後，`pread` 立刻讀到 `'S'`，因為 `pread` 和 `shr` 共用 page cache 的同一頁；但 `priv[1]` 仍是 0，因為 `priv` 的第 0 頁在第 4 步已經被複製成私有的，和 page cache 分家了。

### 程式二：fork 之後的 copy-on-write

第二段程式模擬 `thumbd` 有一個 32 MiB 的縮圖快取，`fork` 出子行程，讓子行程先讀全部、再寫前四分之一，觀察 fault 次數與父行程看到的值。

```c
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

static long minor_faults_now(void) {   /* 這個 process 累計的 minor fault 次數 */
    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    return usage.ru_minflt;
}

int main(void) {
    long page = sysconf(_SC_PAGESIZE);
    size_t len = 32UL * 1024 * 1024;               /* 模擬 thumbd 的 32 MiB 縮圖快取 */
    char *cache = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (cache == MAP_FAILED) { perror("mmap"); return 1; }
    memset(cache, 'A', len);                       /* 父程序先把每一頁都寫過 */
    long pages = (long)(len / (size_t)page);
    printf("父程序：快取共 %ld 頁（page = %ld bytes）\n", pages, page);
    fflush(stdout);                                /* 避免 stdio 緩衝在 fork 後印兩次 */

    pid_t pid = fork();
    if (pid < 0) { perror("fork"); return 1; }
    if (pid == 0) {
        long f0 = minor_faults_now();
        unsigned long sum = 0;
        for (size_t off = 0; off < len; off += (size_t)page) sum += (unsigned char)cache[off];
        printf("子程序：讀完全部 %ld 頁，新增 minor fault %ld 次\n", pages, minor_faults_now() - f0);
        f0 = minor_faults_now();
        for (size_t off = 0; off < len / 4; off += (size_t)page) cache[off] = 'B';
        printf("子程序：寫入前 1/4（%ld 頁），新增 minor fault %ld 次\n",
               pages / 4, minor_faults_now() - f0);
        printf("子程序：cache[0] = %c（sum=%lu）\n", cache[0], sum);
        fflush(stdout);                            /* _exit 不會替我們清 stdio 緩衝 */
        _exit(0);
    }
    waitpid(pid, NULL, 0);
    printf("父程序：子程序結束後 cache[0] = %c\n", cache[0]);
    munmap(cache, len);
    return 0;
}
```

在 macOS arm64（Apple clang 21）上執行：

```text
父程序：快取共 2048 頁（page = 16384 bytes）
子程序：讀完全部 2048 頁，新增 minor fault 2048 次
子程序：寫入前 1/4（512 頁），新增 minor fault 512 次
子程序：cache[0] = B（sum=133120）
父程序：子程序結束後 cache[0] = A
```

逐步解讀：

1. 最後兩行是 COW 的語意：子行程把 `cache[0]` 改成 `'B'`，父行程看到的仍是 `'A'`。兩者在 `fork` 後有各自的「邏輯副本」。
2. 子行程寫入 512 頁，剛好多了 512 次 minor fault：每一頁第一次寫入都觸發一次 COW，kernel 複製一頁。沒寫的 1,536 頁從頭到尾沒被複製，這就是 `fork` 便宜的原因。sum 的值 133,120 = 2,048 × 65（`'A'` 的 ASCII），說明讀到的是父行程的資料。
3. 「讀完全部 2048 頁」也產生了 2,048 次 fault，這是平台差異：從結果看，macOS 的 kernel 在 `fork` 時沒有替子行程預先建立這些頁的硬體映射，子行程第一次讀每一頁時才 fault 一次，以唯讀方式掛上**同一個**實體頁，不複製資料。Linux 在 `fork` 時會複製這類匿名頁的 PTE，所以預期讀取迴圈幾乎不產生 fault，寫入時才出現 COW fault（4 KiB page 下是 2,048 次）；如果該區域用了 Transparent Huge Pages 的 2 MiB 大頁，fault 次數與每次複製的量會依 kernel 版本而不同。這也再次提醒：minor fault 的次數不等於「複製了多少資料」。
4. 程式在 `fork` 前和 `_exit` 前都呼叫 `fflush`。stdio 的緩衝區也是 process 記憶體的一部分，`fork` 會把還沒印出的內容 COW 給子行程，造成重複輸出；`_exit` 則不會清 stdio 緩衝，不 `fflush` 子行程的輸出會消失（第 27 章）。

### 程式三：看看自己的位址空間

最後一段程式印出幾種東西的位址，對照 24.3 節的配置圖。它在 macOS 與 Linux 都能執行：

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

int initialized = 42;            /* .data */
int zeroed;                      /* .bss */
const char banner[] = "thumbd";  /* .rodata */

typedef struct { const char *name; uintptr_t addr; } item_t;

static int by_addr(const void *a, const void *b) {
    uintptr_t x = ((const item_t *)a)->addr, y = ((const item_t *)b)->addr;
    return (x > y) - (x < y);
}

int main(void) {
    int local = 0;
    void *small = malloc(64);                 /* 小配置：通常來自 heap */
    void *anon = mmap(NULL, 1 << 20, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (!small || anon == MAP_FAILED) return 1;
    item_t items[] = {
        {"main（.text）", (uintptr_t)&main},
        {"banner（.rodata）", (uintptr_t)banner},
        {"initialized（.data）", (uintptr_t)&initialized},
        {"zeroed（.bss）", (uintptr_t)&zeroed},
        {"malloc(64)", (uintptr_t)small},
        {"mmap 1 MiB", (uintptr_t)anon},
        {"memcpy（libc）", (uintptr_t)&memcpy},
        {"local（stack）", (uintptr_t)&local},
    };
    size_t n = sizeof items / sizeof items[0];
    qsort(items, n, sizeof items[0], by_addr);
    for (size_t i = n; i-- > 0;)              /* 由高位址往低位址印，和圖的方向一致 */
        printf("0x%016jx  %s\n", (uintmax_t)items[i].addr, items[i].name);
    munmap(anon, 1 << 20);
    free(small);
    return 0;
}
```

在 macOS arm64 上執行：

```text
0x0000000187bd5360  memcpy（libc）
0x000000016d920fe4  local（stack）
0x0000000102e41cd0  malloc(64)
0x00000001024fc000  mmap 1 MiB
0x00000001024e4004  zeroed（.bss）
0x00000001024e4000  initialized（.data）
0x00000001024dc790  banner（.rodata）
0x00000001024dc598  main（.text）
```

從下往上看，執行檔本身的 `.text`、`.rodata`、`.data`、`.bss` 依序排列，和執行檔格式（Linux 的 ELF、macOS 的 Mach-O）裡 segment 的順序一致；`initialized` 與 `zeroed` 只差 4 bytes，說明 `.data` 與 `.bss` 緊鄰。再跑一次，除了 libc，其他位址都會改變，這是 ASLR。

macOS 的配置和 24.3 節的 Linux 圖不同：系統 library 放在一個所有 process 共用的「shared cache」區域，位址比 stack 還高。在 Linux x86-64 上跑同一支程式，預期會看到 stack 在 `0x7ffc…` 附近最高，libc 與 `mmap` 區域在 `0x7f…`，`malloc(64)` 和執行檔在 `0x55…` 或 `0x56…` 附近，順序和 24.3 節的圖一致。教科書畫的圖是一種典型配置，不是所有系統的固定規則；真正可靠的是 `/proc/PID/maps`（Linux）或 `vmmap PID`（macOS）列出的實際 VMA。

## 24.13 在工作上怎麼用

### 情境一：服務被 OOM killer 殺掉

被 OOM killer 殺掉的 process 不會留下 core dump，也無法攔截 `SIGKILL`，所以證據都在 kernel log 和監控裡。`thumbd` 事件之後，阿哲和小安整理出這份檢查流程：

```text
1. 確認是 OOM：
   dmesg -T | grep -i -E "out of memory|oom-kill"      （主機）
   kubectl describe pod … → Last State: OOMKilled      （容器，exit code 137）
2. 看被殺時的組成：log 中的 anon-rss、file-rss、shmem-rss
   └─ anon-rss 佔大部分 → 匿名記憶體太多（緩衝區、快取、leak）
3. 看平常的組成：/proc/PID/smaps_rollup 的 Anonymous、Private_Dirty、Pss_File
4. 找出成長的 VMA：比較兩個時間點的 /proc/PID/smaps 或 pmap -x PID
   ├─ [heap] 或匿名 arena 成長 → 第 25 章（allocator）、第 26 章（leak）
   ├─ 某個檔案 mapping 成長 → 通常是可回收的 page cache，不是元兇
   └─ 很多 8 MiB 的匿名區域 → thread 數量失控
5. 修：減少匿名副本（read → mmap）、限制並行處理的大圖數量、
       設定合理的容器 limit、必要時調整 oom_score_adj
```

### 情境二：用 mmap 處理大型唯讀資料

`thumbd` 最終的原圖讀取方式，可以當作「大型唯讀檔案」的範本：

- 用 `open(O_RDONLY)` ＋ `fstat` 取得大小；大小為 0 時不要 `mmap`（會回傳 `EINVAL`）。
- `mmap(NULL, size, PROT_READ, MAP_SHARED, fd, 0)`，成功後就可以 `close(fd)`，mapping 仍然有效。
- 依存取模式呼叫 `madvise`：整張循序解碼用 `MADV_SEQUENTIAL`，已知馬上要讀用 `MADV_WILLNEED`。
- 確保檔案不會被原地截短或修改（用「寫暫存檔再 `rename`」的上傳流程），否則要準備好處理 `SIGBUS`。
- 用完立刻 `munmap`，避免 VMA 數量累積；Linux 的 `vm.max_map_count`（kernel 預設 65,530，部分發行版已調高）限制了一個 process 的 VMA 數量，同時映射大量小檔可能撞到它，此時 `mmap` 會回傳 `ENOMEM`。

### 情境三：呼叫外部程式

大 RSS 的服務需要呼叫外部工具時，預設用 `posix_spawn` 而不是 `fork` ＋ `execve`。若某個 library 只提供 `fork` 介面，至少要量測 `fork` 的延遲（例如用 `strace -T -e trace=clone,fork` 看系統呼叫花費的時間），並確認父行程不會在子行程存活期間大量寫入。這也適用於 Python 的 `subprocess`、Java 的 `ProcessBuilder` 這類高階 API：它們在 Linux 上底層可能用 `vfork`、`posix_spawn` 或 `fork`，依版本與參數而定，大型服務出現「呼叫子行程時延遲尖峰」時值得往這裡查。

### 情境四：在 production 上快速看懂一個 process 的記憶體

```bash
# 依大小列出 VMA（Linux）：位址、大小、RSS、dirty、權限、名稱
pmap -x <PID> | sort -k3 -n | tail -20

# 整體組成：匿名 vs 檔案、clean vs dirty、swap
cat /proc/<PID>/smaps_rollup

# 一群 process 的 PSS 加總（例如所有 thumbd worker）
for p in $(pgrep thumbd); do grep '^Pss:' /proc/$p/smaps_rollup; done | awk '{s+=$2} END {print s " kB"}'

# 系統層級：page cache、可用記憶體、承諾量
grep -E 'MemAvailable|^Cached|Committed_AS|CommitLimit' /proc/meminfo
```

判斷原則：`MemAvailable` 才是「還能用多少」，`MemFree` 很小是正常的（空閒記憶體都被拿去當 page cache）；`Committed_AS` 遠大於實體記憶體，代表系統依賴 overcommit，一旦大家同時兌現就會 OOM。

## 24.14 常見錯誤與除錯

| 症狀 | 常見原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| `mmap` 回傳 `EINVAL` | `offset` 沒對齊 page、`length` 為 0、`flags` 沒指定 shared 或 private | `strace -e trace=mmap` 看參數；檢查檔案大小 | `offset` 往下對齊並記住差值；空檔案特別處理 |
| 檢查 `mmap` 失敗卻沒抓到錯 | 拿回傳值和 `NULL` 比較 | 讀程式碼 | 和 `MAP_FAILED` 比較 |
| 程式隨機收到 `SIGBUS` | 映射的檔案被截短或被原地覆寫 | core dump 的 `si_addr` 落在檔案 mapping；檢查是否有程式在改檔 | 只讀不可變的檔案；更新用「寫暫存檔再 `rename`」 |
| `MAP_SHARED` 寫入後機器斷電，資料不見 | 寫入只進了 page cache | 程式中沒有 `msync`／`fsync` | 需要持久化的地方呼叫 `msync(MS_SYNC)` |
| 父行程 `fork` 後 RSS 暴增 | 子行程存活期間父行程大量寫入，COW 複製 | `smaps_rollup` 的 `Private_Dirty` 在 `fork` 後成長 | 縮短子行程存活時間；改用 `posix_spawn`；預留記憶體 |
| 大服務呼叫外部工具時延遲尖峰 | `fork` 複製大量 page table | `strace -T` 看 `clone`／`fork` 的耗時 | 改用 `posix_spawn` |
| 輸出被印兩次 | `fork` 前 stdio 緩衝區有資料，被 COW 給子行程 | 輸出接到檔案或 pipe 時才出現 | `fork` 前 `fflush`；子行程用 `_exit` 前也要 `fflush` |
| `mmap` 回傳 `ENOMEM`，但記憶體還很多 | VMA 數量超過 `vm.max_map_count`，或 overcommit 模式 2 的額度用完 | `wc -l /proc/PID/maps`；`/proc/meminfo` 的 `Committed_AS` | 及時 `munmap`；合併小映射；調整限制 |
| 容器被 `OOMKilled`，主機記憶體卻很多 | 超過 cgroup 的 `memory.max` | `kubectl describe pod`；容器內 `cat /sys/fs/cgroup/memory.current` | 調整 limit，或減少匿名記憶體與 COW 峰值 |

> [!tip] 在 gdb 中確認 segfault 位址屬於哪個 VMA
> 載入 core dump 後執行 `info proc mappings`（或在 live process 上 `info proc mappings`），找出包含 `$_siginfo._sifields._sigfault.si_addr` 的那一行。落在 guard page 是 stack overflow，落在 `---p` 是碰到預留區，不在任何一行通常是壞指標，落在 `r-xp` 而且是寫入就是改到了程式碼或常數。

## 24.15 動手練習

1. **手算**：`thumbd` 要映射一個檔案從 offset 123,456,789 開始的 50,000 bytes，page 4 KiB。`mmap` 的 offset 與 length 該傳多少？真正的資料從回傳位址加多少開始？（驗證方法：寫一段程式，用 `sysconf(_SC_PAGESIZE)` 與位元運算算出同樣的值。）
2. **手算**：一台機器上有 6 個 process 都映射了同一個 30 MiB 的唯讀模型檔，各自另有 80 MiB 私有匿名記憶體，並共用 9 MiB 的 library。算出每個 process 的 RSS、PSS、USS，以及 RSS 加總與 PSS 加總。（答案：RSS 119 MiB、PSS 86.5 MiB、USS 80 MiB；RSS 加總 714 MiB，PSS 加總 519 MiB = 480 + 30 + 9。）
3. 修改 24.12 節程式一，把 `MAP_PRIVATE` 的寫入改成寫在第 100 頁，再讓 shared 映射寫第 100 頁和第 200 頁，觀察 private 映射在兩頁看到的值。用 24.6 節的「常見誤解」解釋結果（結果在 macOS 和 Linux 上可能不同，這正是 POSIX 不規定的部分）。
4. 修改程式二，讓子行程寫入全部的頁，並在父行程 `waitpid` 之前呼叫 `sleep(1)`，在另一個終端機用 `ps -o pid,rss,command` 觀察父子行程的 RSS。在 Linux 上改用 `/proc/PID/smaps_rollup` 看 `Private_Dirty` 與 `Shared_Dirty` 的變化。
5. 在 Linux 上執行 `cat /proc/self/maps`，對照 24.3 節的表格，指出哪一行是 `cat` 自己的 `.text`、哪一行是 heap、哪一行是 libc 的程式碼，以及 `[vdso]` 的位址。再跑一次，哪些位址變了？
6. 寫一段程式，`mmap` 一個 1 頁大小的檔案後，用 `ftruncate` 把檔案截成 0，再讀映射區域的第一個 byte，觀察收到的 signal。用 24.4 節的流程圖解釋為什麼是 `SIGBUS` 而不是 `SIGSEGV`。

## 本章重點整理

- Linux 用 `mm_struct` 和一組 VMA 描述 process 的位址空間；VMA 記錄範圍、權限、shared 或 private、背後的檔案與 offset，page table 則在 page fault 時依 VMA 的內容逐頁填上。
- `mmap` 與 `execve` 都只是建立 VMA，不讀任何資料；資料在第一次碰到某頁時才透過 page fault 載入。
- x86-64 Linux 的 user 位址空間是下半的 128 TiB，由低到高大致是：不映射的第 0 頁附近、執行檔、heap、mmap 區域（library、thread stack、大配置、檔案映射）、stack；ASLR 讓各區起點隨機化。
- `/proc/PID/maps` 每一行是一個 VMA，權限欄的第四個字元 `p`／`s` 表示 private 或 shared；同一個檔案會因權限不同而分成多個 VMA。
- Page fault 處理依序檢查「位址是否在 VMA 內」「權限是否符合」，再依 VMA 種類做 demand-zero、page cache 對應、COW 或從 swap 讀回；位址不合法是 `SEGV_MAPERR`，權限不符是 `SEGV_ACCERR`，檔案資料不存在是 `SIGBUS`。
- Memory mapping 分成檔案與匿名、shared 與 private 四種組合，涵蓋 heap、stack、程式碼、library、共享記憶體與檔案映射。
- 記憶體壓力下，clean 的檔案頁可以直接丟掉，匿名頁只能寫到 swap；沒有 swap 時匿名頁無法回收，是 OOM 的主要來源。
- Private mapping 用 copy-on-write 實作：共享實體頁並設為唯讀，第一次寫入時才以頁為單位複製。
- `fork` 複製 VMA 與 page table、把可寫的 private 頁改成唯讀，不複製資料；但大 RSS 的 process `fork` 仍要付 page table 複製的成本，且之後的寫入會造成 COW。
- 大型服務呼叫外部程式應優先使用 `posix_spawn`，它避免了複製 page table 與 COW 的風險。
- `mmap` 的 offset 必須對齊 page，失敗回傳 `MAP_FAILED`；寫入 `MAP_SHARED` 只保證其他映射者可見，持久化需要 `msync` 或 `fsync`。
- RSS 會重複計算共享頁，PSS 把共享頁平均分攤，USS 只算獨佔頁；估算多 process 服務的真實用量要加總 PSS。
- 在預設的 overcommit 策略下，`malloc` 很少失敗，記憶體不足會延後到寫入新頁時，由 OOM killer 依 badness 分數挑選 process 以 `SIGKILL` 結束；容器中則是 cgroup 的 `memory.max` 先觸發。

## 延伸問答

> [!question]- Q1. VMA 和 page table 都在描述位址空間，為什麼兩者都需要？
> Page table 是給硬體看的：它必須是 MMU 能直接走訪的固定格式，每一頁一個 PTE，只記錄「現在對到哪個實體頁、權限是什麼」。它沒有地方記錄「這一頁還沒載入，但它應該來自某個檔案的第幾個 byte」，因為無效的 PTE 對硬體來說就是無效。
>
> VMA 是給 kernel 看的：它以「區域」為單位，記錄合法範圍、權限、shared 或 private、背後的檔案與 offset。page fault 時 kernel 靠 VMA 判斷該送 signal 還是該載入資料、載入什麼。兩者分工的結果是：VMA 數量少（幾十到幾千個），描述完整的意圖；PTE 數量多，但只為真正碰過的頁建立。沒有 VMA，demand paging 和 COW 都無法實作。

> [!question]- Q2. 手算題：一個 process 在 `/proc/PID/maps` 有一行 `7f2a1d1f3000-7f2a1d9f3000 rw-p 00000000 00:00 0`，這是什麼？大小多少？
> 先算大小：`0x7f2a1d9f3000 − 0x7f2a1d1f3000 = 0x800000`，也就是 8 × 2^20 = 8 MiB。權限 `rw-p` 表示可讀寫、不可執行、private；offset 0、裝置 `00:00`、inode 0 表示它是匿名 mapping，沒有對應的檔案。
>
> 8 MiB、匿名、可讀寫，而且緊鄰在它下方有一頁 `---p` 的區域，這幾乎可以確定是一個 thread 的 stack 和它的 guard page：glibc 建立 thread 時預設依 `ulimit -s` 配置 8 MiB 的 stack。如果一個服務的 maps 裡有幾百個這樣的區域，代表它有幾百個 thread，VSZ 也會因此多出幾 GB，但只有真正被用到的 stack 頁才算進 RSS。

> [!question]- Q3. 你在 production 看到一個 Python 服務每次用 `subprocess` 呼叫外部指令時，p99 延遲就會出現尖峰，而這個服務的 RSS 有 20 GB。你會懷疑什麼？怎麼確認？
> 第一個懷疑是 `fork` 的成本。即使有 copy-on-write，`fork` 仍要複製 VMA 和 page table：20 GiB ÷ 4 KiB 約 524 萬個 PTE，約 40 MiB 的最底層 page table，加上逐頁調整計數與權限，可能讓呼叫 `fork` 的 thread 卡住相當長的時間；`fork` 期間父行程的其他工作也可能受影響。若子行程存活期間父行程大量寫入，還會額外付 COW 的成本。
>
> 確認方法是用 `strace -f -T -e trace=clone,clone3,fork,vfork,execve -p <PID>` 看每次系統呼叫的耗時，或用 `perf` 看 `copy_page_range` 之類的 kernel 函式。修法是讓呼叫走 `posix_spawn` 或 `vfork` 路徑（不同 Python 版本與參數組合會選擇不同機制），或把呼叫外部指令的工作交給一個 RSS 很小的輔助 process 處理。

> [!question]- Q4. 為什麼讀一個從來沒寫過的 `malloc` 大區塊，RSS 幾乎不會增加？
> 大的 `malloc` 通常直接用匿名 `mmap` 取得記憶體（第 25 章），新的 VMA 裡所有 PTE 都是無效的。第一次讀某一頁時發生 page fault，kernel 發現這是匿名、private 的區域，而且是讀取，就讓 PTE 以唯讀方式指向一個全系統共用、內容全為零的實體頁，不需要配置新的頁。
>
> 所以「只讀不寫」的匿名記憶體幾乎不佔實體記憶體。直到第一次寫入，kernel 才配一個新的實體頁並填零（這一步其實也是一種 copy-on-write，複製的來源是零頁）。這也說明為什麼 benchmark 只讀不寫的大陣列，看不到真實的記憶體壓力與 page fault 成本。

> [!question]- Q5. `MAP_SHARED` 和 `MAP_PRIVATE` 映射同一個檔案，都只讀不寫，有什麼差別？
> 只讀的情況下，兩者的 PTE 都指向 page cache 中同一組實體頁，記憶體用量相同，讀到的內容在一般情況下也相同，所以多數只讀的應用兩者都可以。差別在於語意承諾：`MAP_SHARED` 保證你看到檔案的最新內容（別人透過 `write` 或另一個 shared 映射修改後你會看到）；`MAP_PRIVATE` 對這件事沒有保證，POSIX 未規定。
>
> 另一個差別是「之後會不會寫」：private 映射一旦寫入就產生私有副本，不會影響檔案；shared 映射寫入會修改檔案。若你只想讀，就用 `PROT_READ` 讓任何寫入都直接 segfault，比依賴旗標更安全。在 `/proc/PID/maps` 中，兩者的差別就是權限欄第四個字元的 `s` 或 `p`。

> [!question]- Q6. 程式找錯：下面這段讀檔程式有什麼問題？`char *p = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 4000); if (p == NULL) { perror("mmap"); exit(1); }`
> 有兩個錯誤。第一，offset 4000 不是 page 大小的整數倍（4 KiB 系統上應是 4096 的倍數），`mmap` 會失敗並設定 `errno = EINVAL`。正確做法是把 offset 往下對齊到 0，映射時多算 4000 bytes，資料從 `p + 4000` 開始；或用 `off & ~(page − 1)` 計算對齊值。
>
> 第二，`mmap` 失敗時回傳的是 `MAP_FAILED`（`(void *)-1`），不是 `NULL`，所以這個檢查永遠不會成立，程式會繼續用 `(void *)-1` 當指標，在別的地方 segfault，錯誤訊息也會指向錯誤的位置。此外，`st.st_size` 為 0 時 `mmap` 也會失敗，空檔案要另外處理；從 4000 開始的有效資料只有 `st.st_size - 4000` bytes；若映射長度照用 `st.st_size`，範圍會超出檔案結尾，程式讀到檔案結尾之後的整頁時就會收到 `SIGBUS`。

> [!question]- Q7. 面試題：解釋 copy-on-write，並舉出 Linux 裡至少三個用到它的地方。
> Copy-on-write 是一種延遲複製的策略：需要「各自一份」的資料一開始先共用同一組實體頁，把 PTE 設成唯讀；任何一方第一次寫入時觸發 protection fault，kernel 確認這是 private 且原本可寫的區域，才複製那一頁給寫入者並改成可寫，然後重新執行寫入指令。沒被寫的頁永遠不必複製。
>
> 用到它的地方至少有：`fork`（父子行程共用所有 private 頁，誰寫誰複製）；以 `MAP_PRIVATE` 映射檔案，包括載入執行檔與 shared library 的 `.data`（改全域變數不會改到檔案或其他 process）；匿名記憶體的第一次寫入（從共用的零頁複製一份）。在 kernel 之外，同樣的想法也出現在檔案系統（Btrfs、ZFS 的寫入策略）與程式語言（某些字串或容器實作）中，回答時能提到「以頁為單位」與「寫入觸發 fault」兩個細節最加分。

> [!question]- Q8. 一台 64 GB 的機器上，`free` 顯示 `free` 只剩 1 GB，但 `available` 有 40 GB。SRE 說記憶體快用完了，你同意嗎？
> 不同意。Linux 會把沒在用的實體記憶體拿去當 page cache，快取最近讀寫過的檔案，所以 `free` 欄位很小是正常、甚至是好事：閒置的記憶體沒有任何價值。`available`（對應 `/proc/meminfo` 的 `MemAvailable`）估計的是「在不需要 swap 的前提下，還能給新程式用多少」，它把可以直接丟掉的 clean page cache 算進去了。
>
> 要判斷是否真的有記憶體壓力，應該看 `MemAvailable` 是否持續下降、major fault 與 swap 進出（`vmstat` 的 `si`／`so`）是否增加、以及 kernel log 有沒有 OOM 紀錄；在容器中則看 cgroup 的 `memory.current` 與 `memory.max`。如果是 `thumbd` 這種大量 `mmap` 原圖的服務，page cache 佔很多更是預期中的，那些頁在壓力下會先被回收。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 9.7、9.8 節以 Linux 與 Core i7 為例的 VM 系統、memory mapping、`fork` 與 `execve`。
- [Linux man pages](https://man7.org/linux/man-pages/)：`mmap(2)`、`mprotect(2)`、`madvise(2)`、`msync(2)`、`posix_spawn(3)`、`shm_open(3)`，以及 `proc(5)` 中 `/proc/PID/maps`、`smaps`、`oom_score_adj` 的說明。
- [POSIX（The Open Group Base Specifications）](https://pubs.opengroup.org/onlinepubs/9799919799/)：`mmap` 的標準語意，包括 `MAP_PRIVATE` 對檔案後續修改「未規定」的部分。
- [ELF 規格](https://refspecs.linuxfoundation.org/elf/elf.pdf)：program header 與 `PT_LOAD` segment，對照 24.8 節 `execve` 建立的 mapping。
- [GDB 文件](https://sourceware.org/gdb/current/onlinedocs/gdb.html/)：`info proc mappings` 與 `$_siginfo` 的用法。
