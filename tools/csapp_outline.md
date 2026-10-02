# 《CS:APP 系統思維學習手冊》章節大綱

每一列：章｜檔名｜標題｜對應 CS:APP 3e｜Q&A 數｜必須涵蓋。CS:APP 3e 章節代號：**ch1** Tour、**ch2** Representing and Manipulating Information、**ch3** Machine-Level Representation、**ch4** Processor Architecture、**ch5** Optimizing Program Performance、**ch6** The Memory Hierarchy、**ch7** Linking、**ch8** Exceptional Control Flow、**ch9** Virtual Memory、**ch10** System-Level I/O、**ch11** Network Programming、**ch12** Concurrent Programming。舊稿：`/tmp/csapp_old/sections/*.txt`。

貫穿案例 **拾光相簿與 `thumbd`**：拾光相簿是一個線上相簿服務。後端有一個用 C 寫的縮圖服務 `thumbd`：接收 HTTP 請求、讀取原圖檔、做縮放（像素矩陣運算）、回傳縮圖，並用 thread pool 處理並行請求。人物：剛入職的初階後端工程師小安（只寫過 Python／Java，C 只在大學學過），以及資深系統工程師老周（mentor）。每章從 `thumbd` 遇到的一個真實問題開場（bug、效能、當機、資源洩漏），再用該章的系統知識解開它。

## Part 0　起點（`Part 0 - 起點/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 1 | 01 - Hello World 背後的旅程.md | Hello World 背後的旅程：一支程式如何被編譯、載入與執行 | ch1 | 8 | 原始碼到可執行檔的四個階段（preprocess、compile、assemble、link）；程式在記憶體中的樣子；CPU、記憶體、匯流排、I/O 裝置的硬體組成；cache 的意義；OS 的三個抽象（process、virtual memory、file）；並行與平行（thread、多核、超純量、SIMD）；Amdahl's law；全書地圖與 `thumbd` 介紹 |
| 2 | 02 - 系統工程師工具箱.md | 系統工程師的工具箱：C、指標、Linux 與除錯器 | 先備 | 8 | 給只會高階語言的讀者：C 的型別、指標與陣列、`&` 與 `*`、記憶體位址、`sizeof`、字串與 `\0`、struct；標頭檔與 header guard；Linux shell 基本操作；gcc/clang 編譯選項（-O、-g、-Wall、-fsanitize）；gdb／lldb 基本操作（break、step、print、x、bt）；objdump；undefined behavior 的概念；如何讀 man page |

## Part 1　資訊的表示（`Part 1 - 資訊表示/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 3 | 03 - 位元位元組與記憶體.md | 位元、位元組與記憶體中的資料 | ch2.1 | 8 | 二進位、十六進位轉換；word size 與資料型別大小（LP64）；byte order（big／little endian）與網路序；`show_bytes` 檢視記憶體；字串表示；布林代數與位元運算（&、\|、^、~）、位元遮罩；邏輯運算 vs 位元運算；shift（邏輯 vs 算術、shift 量超過寬度是 UB）；`thumbd` 解析 PNG／JPEG header 的 byte order bug |
| 4 | 04 - 整數表示.md | 整數：Unsigned 與二補數 | ch2.2 | 8 | unsigned 編碼；二補數編碼與直覺（最高位權重為負）；TMin、TMax、UMax；signed／unsigned 轉換（位元不變、解讀改變）；C 的隱式轉換規則與比較陷阱（`-1 < 0u`）；sign extension 與 zero extension；截斷；`size_t` 與迴圈陷阱；何時用 unsigned |
| 5 | 05 - 整數運算與溢位.md | 整數運算：加法、乘法、溢位與安全漏洞 | ch2.3 | 8 | unsigned 加法與模運算；二補數加法與溢位偵測；負數；乘法與溢位；用 shift 做乘法；除以 2 的冪與 bias（向零捨入）；signed overflow 是 UB（編譯器最佳化後果）；`__builtin_*_overflow`；真實漏洞（malloc 大小計算溢位、XDR／getpeername 類案例）；`thumbd` 寬×高×4 溢位造成 heap overflow |
| 6 | 06 - 浮點數.md | 浮點數：IEEE 754 與數值陷阱 | ch2.4 | 8 | 二進位小數；IEEE 754 single／double 格式（sign、exponent、fraction）；normalized、denormalized、special values（∞、NaN）；範例數值與數線分佈；rounding（round-to-even）；浮點加法不滿足結合律；C 的型別轉換與截斷；金額不該用 float；比較浮點數；`thumbd` 縮放比例累積誤差 |

## Part 2　機器級程式（`Part 2 - 機器級程式/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 7 | 07 - 從 C 到組合語言.md | 從 C 到組合語言：x86-64 基礎 | ch3.1–3.4 | 8 | ISA 的角色；用 `gcc -S`／`objdump -d` 看組合語言；AT&T vs Intel 語法；暫存器（16 個 general purpose、%rax..、子暫存器 %eax／%ax／%al）；operand 形式與 addressing mode（Imm(rb,ri,s)）；mov 指令家族與大小後綴；movz／movs；push／pop；`leaq`；用 `-target x86_64-linux-gnu -S` 在任何機器產生 x86-64 組合語言；ARM64 簡短對照 |
| 8 | 08 - 算術條件碼與控制流程.md | 算術、條件碼與控制流程 | ch3.5–3.6 | 8 | 算術與邏輯指令；特殊乘除（imul、cqto、idiv）；condition codes（CF、ZF、SF、OF）；cmp 與 test；set、jmp、條件跳躍；跳躍目標編碼；if 的翻譯；conditional move 與何時不能用；do-while／while／for 的翻譯；switch 與 jump table；branch prediction 對效能的影響 |
| 9 | 09 - 程序呼叫與 Stack.md | 程序呼叫：Stack Frame 與 Calling Convention | ch3.7 | 8 | run-time stack；call／ret 與 return address；System V AMD64 ABI 參數傳遞（rdi、rsi、rdx、rcx、r8、r9）；回傳值；caller-saved vs callee-saved；local 變數在 stack；frame pointer 與 `-fomit-frame-pointer`；遞迴；stack trace 怎麼來的；red zone；用 gdb 看 stack frame |
| 10 | 10 - 陣列結構與對齊.md | 陣列、結構、Union 與資料對齊 | ch3.8–3.9 | 8 | 陣列存取與指標運算；多維陣列與 row-major；定長與可變長度陣列的位址計算；struct 欄位位移；alignment 規則與 padding；重新排列欄位減少 padding；union 與型別雙關；函式指標；指標大小與 `void*`；`thumbd` 像素 struct 的記憶體配置 |
| 11 | 11 - 記憶體安全與攻擊.md | 記憶體安全：Buffer Overflow 的成因、偵測與防護 | ch3.10 | 8 | 越界存取與 undefined behavior；stack／heap／global 越界的不同後果；stack 上陣列與 saved 暫存器、return address 的相對位置（說明為何越界會破壞控制資料）；編譯器與作業系統的防護（stack canary、NX、ASLR、PIE）各自的作用，概念層級；variable-size stack frame 與 VLA 的風險；安全的字串處理；`_FORTIFY_SOURCE`、sanitizer、fuzzing；記憶體安全語言；在工作上檢查 binary 的防護與處理 crash 報告。只談成因、偵測與防護，不描述攻擊手法 |

## Part 3　處理器與效能（`Part 3 - 處理器與效能/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 12 | 12 - 處理器如何執行指令.md | 處理器如何執行指令：Y86-64 與循序實作 | ch4.1–4.3 | 8 | ISA 與微架構的分界；Y86-64 指令集；邏輯閘、組合電路、HCL；暫存器與時脈；循序處理器的六個階段（fetch、decode、execute、memory、write back、PC update）；用一條指令走一遍 datapath；循序實作為何慢 |
| 13 | 13 - Pipeline 與 Hazard.md | Pipeline：Hazard、Forwarding 與分支預測 | ch4.4–4.5 | 8 | pipelining 的原理（throughput vs latency）；pipeline 階段暫存器；data hazard 與 stall；forwarding／bypassing；load-use hazard；control hazard 與分支預測；例外處理；CPI；現代處理器（out-of-order、superscalar）的概念；Spectre／Meltdown 為何和推測執行有關 |
| 14 | 14 - 程式效能最佳化.md | 程式效能最佳化：從編譯器限制到指令級平行 | ch5 | 8 | 量測（CPE）；編譯器的能力與限制（memory aliasing、procedure side effects）；消除迴圈不變量、減少函式呼叫、減少記憶體存取；現代處理器的功能單元、latency 與 issue time；data-flow 圖與關鍵路徑；loop unrolling；多個累加器與 reassociation；SIMD 簡介；分支預測與 branchless；profiling（gprof、perf）；Amdahl's law；`thumbd` 縮放迴圈最佳化實例 |

## Part 4　記憶體階層（`Part 4 - 記憶體階層/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 15 | 15 - 儲存技術與記憶體階層.md | 儲存技術與記憶體階層 | ch6.1–6.3 | 8 | SRAM、DRAM、SSD、HDD 的原理與存取時間數量級；CPU 與記憶體速度差距；locality（temporal、spatial）；stride；記憶體階層金字塔；cache 的一般概念（hit、miss、block、placement、replacement）；每一層的大小與延遲數字（給量級即可） |
| 16 | 16 - Cache 組織與運作.md | Cache：組織、命中與失誤 | ch6.4 | 8 | direct-mapped cache、set associative、fully associative；位址切成 tag／set index／block offset；cold、conflict、capacity miss；寫入策略（write-through、write-back、write-allocate）；多層 cache；cache 參數對效能的影響；Cache Lab 模擬器的思路；用程式模擬 cache |
| 17 | 17 - Cache-friendly 程式.md | 寫出 Cache-friendly 的程式 | ch6.5–6.6 | 8 | 迴圈順序與 stride-1；矩陣乘法六種迴圈順序；blocking／tiling；memory mountain；false sharing 預告（第 32 章）；資料結構布局（AoS vs SoA）；`perf stat` 看 cache miss；`thumbd` 影像旋轉／縮放的 cache 最佳化 |

## Part 5　連結（`Part 5 - 連結/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 18 | 18 - 目的檔與符號解析.md | 從原始碼到執行檔：目的檔與符號解析 | ch7.1–7.6 | 8 | compiler driver；static linking；relocatable／executable／shared object 檔；ELF 格式（section：.text、.data、.bss、.rodata、.symtab）；符號與符號表；strong／weak symbol 與重複定義；static library（.a）與連結順序；`nm`、`readelf`、`objdump`；常見 link error（undefined reference、multiple definition）怎麼讀 |
| 19 | 19 - Relocation 與動態連結.md | Relocation、動態連結與 Library Interpositioning | ch7.7–7.13 | 8 | relocation；executable 的載入；dynamic linking 與 shared library（.so）；PIC；GOT 與 PLT、lazy binding；`dlopen`；`LD_LIBRARY_PATH`、rpath、`ldd`；ABI 相容與 symbol versioning；library interpositioning（compile-time、link-time、run-time `LD_PRELOAD`）；`thumbd` 換了 libjpeg 版本後當機 |

## Part 6　例外控制流（`Part 6 - 例外控制流/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 20 | 20 - Exception 與 Process.md | Exception 與 Process | ch8.1–8.3 | 8 | exceptional control flow 的層次；exception 類型（interrupt、trap、fault、abort）；system call 如何進入 kernel；process 的抽象（private address space、logical control flow）；user mode vs kernel mode；context switch；系統呼叫錯誤處理（errno、wrapper）；`strace` 看系統呼叫 |
| 21 | 21 - fork exec 與 Shell.md | Process 控制：fork、exec、wait 與 Shell | ch8.4 | 8 | getpid；fork 的語意（呼叫一次回傳兩次）、process graph；exit 與 zombie；waitpid 與回收子行程；sleep、pause；execve 與 argv／envp；寫一個簡單 shell；孤兒行程與 init；`thumbd` 用 fork／exec 呼叫外部轉檔工具造成 zombie 累積 |
| 22 | 22 - Signal 與 Nonlocal Jump.md | Signal 與 Nonlocal Jump | ch8.5–8.6 | 8 | signal 的概念與常見 signal；發送（kill、Ctrl-C）與接收；pending／blocked；signal handler；async-signal-safe 函式；handler 的寫法守則（errno、volatile sig_atomic_t、阻擋 signal）；signal 不排隊；race（fork 後 handler 先跑）與 sigprocmask；sigsuspend；setjmp／longjmp；`thumbd` 的 SIGHUP 重新載入設定與 SIGTERM 優雅關閉；Shell Lab 學習目標 |

## Part 7　虛擬記憶體（`Part 7 - 虛擬記憶體/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 23 | 23 - 位址轉譯.md | 位址轉譯：Page Table、TLB 與 Page Fault | ch9.1–9.6 | 8 | 實體與虛擬位址；VM 作為快取、記憶體管理與保護的工具；page、page table、PTE；page hit 與 page fault；位址轉譯（VPN、VPO、PPN）；TLB；多層 page table；完整轉譯算例（小型系統）；Core i7 的四層 page table 概念 |
| 24 | 24 - Linux 虛擬記憶體與 mmap.md | Linux 虛擬記憶體：Process 位址空間、mmap 與 Copy-on-Write | ch9.7–9.8 | 8 | Linux process 的位址空間配置；area／VMA；page fault 處理流程；memory mapping；shared object 與 private copy-on-write；fork 與 COW；execve 時的 mapping；`mmap` 函式與用途（讀大檔、共享記憶體）；`/proc/PID/maps`；RSS、VSZ、PSS；OOM killer；`thumbd` 用 mmap 讀大圖檔 |
| 25 | 25 - 動態記憶體配置.md | 動態記憶體配置：malloc 如何運作 | ch9.9 | 8 | heap 與 brk／sbrk、mmap；malloc／free 的需求與目標（throughput vs utilization）；fragmentation（internal、external）；implicit free list；placement（first／next／best fit）；splitting；coalescing 與 boundary tag；explicit free list；segregated free lists；heap checker；實際 allocator（ptmalloc、jemalloc、tcmalloc）的概念；Malloc Lab 學習目標 |
| 26 | 26 - 記憶體錯誤與 Garbage Collection.md | 記憶體錯誤與 Garbage Collection | ch9.10–9.11 | 8 | 常見記憶體 bug（dereference 壞指標、未初始化、buffer overflow、off-by-one、指標運算錯、use-after-free、double free、memory leak）；ASan、Valgrind、UBSan 的原理與用法；garbage collection 基礎（reachability、mark-and-sweep、保守式 GC）；RAII 與所有權的概念；`thumbd` memory leak 讓 RSS 持續上升 |

## Part 8　I/O 與網路（`Part 8 - IO 與網路/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 27 | 27 - Unix IO.md | Unix I/O：File Descriptor、Short Count 與 Buffered I/O | ch10 | 8 | Unix I/O 模型；檔案類型；open／close／read／write；short count 的成因與處理；RIO 套件（robust read／write、buffered）；metadata（stat）；kernel 資料結構（descriptor table、open file table、v-node）；共享檔案與 fork 後的 descriptor；I/O redirection（dup2）；Standard I/O 的 buffering 與何時不能混用；fsync 與 durability；`thumbd` 寫檔遺漏 short write |
| 28 | 28 - 網路與 Socket.md | 網路程式設計：Socket 與 Client-Server 模型 | ch11.1–11.4 | 8 | client-server 模型；網路分層與 TCP/IP 概念；IP 位址與 port；DNS 與 `getaddrinfo`；socket 介面（socket、connect、bind、listen、accept）；open_clientfd／open_listenfd；echo client／server；TCP 是 byte stream（訊息邊界、short read）；backlog、TIME_WAIT 概念；`ss`／`netstat`；IPv4 與 IPv6 |
| 29 | 29 - Web Server.md | 寫一台 Web Server：HTTP、靜態與動態內容 | ch11.5–11.6 | 8 | HTTP 請求與回應格式；URL、MIME type；靜態內容與動態內容（CGI）；Tiny web server 的完整流程；解析 request line 與 header；安全問題（path traversal、header 大小限制）；keep-alive 概念；proxy 的角色（Proxy Lab）；從 Tiny 到 `thumbd`；與現代 web server（nginx 事件驅動）的差異 |

## Part 9　並行程式設計（`Part 9 - 並行程式設計/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 30 | 30 - 三種並行模型.md | 三種並行模型：Process、I/O Multiplexing 與 Thread | ch12.1–12.3 | 8 | 為何需要並行；process-based server 與優缺點；I/O multiplexing（select、poll、epoll 概念）與 event-driven server；thread 的執行模型與 Posix threads（create、join、detach）；thread-based server；三種模型比較表；thread pool 與 prethreading（producer-consumer）；`thumbd` 從單執行緒到 thread pool |
| 31 | 31 - 同步與競爭.md | 同步：共享變數、Race、Semaphore 與 Deadlock | ch12.4–12.5, 12.7 | 8 | 哪些變數是共享的；`cnt++` 為何不是 atomic（progress graph）；semaphore 與 P／V；mutex；用 semaphore 排程共享資源（producer-consumer、readers-writers）；condition variable；deadlock 的條件與避免（鎖順序）；race 的除錯（ThreadSanitizer）；`thumbd` 快取計數器的 race |
| 32 | 32 - 並行效能與 Thread Safety.md | 並行效能、Thread Safety 與記憶體模型入門 | ch12.6–12.7 | 8 | 平行程式的 speedup 與 efficiency；同步的成本；false sharing；thread-safe 與 reentrant 函式；常見的 thread-unsafe 函式；atomic 操作與 memory ordering 入門；lock-free 的代價；Amdahl 與 Gustafson；`thumbd` 加 thread 反而變慢的分析 |

## Part 10　整合應用（`Part 10 - 整合應用/`）

| 章 | 檔名 | 標題 | 對應 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 33 | 33 - 跨層診斷實戰.md | 跨層診斷實戰：從症狀一路追到根因 | 全書 | 8 | 以 `thumbd` 的 6 個 production 事件串起全書：segfault（core dump、gdb bt）、延遲變高（perf、cache）、RSS 上升（leak vs 碎片 vs page cache）、CPU 100%（profiling）、連線卡住（strace、ss、short read）、偶發錯誤（race、TSan）；每個事件的診斷流程圖與工具；症狀到章節的對照表 |
| 34 | 34 - Labs 與學習路線.md | CS:APP Labs 實作指南與學習路線 | 全書 | 8 | 九個 Labs（Data、Bomb、Attack、Architecture、Cache、Performance、Shell、Malloc、Proxy）各自練什麼、先備知識、常見卡關、怎麼驗證自己真的懂（不談解答）；建議的學習順序與時程；如何把這些能力用在工作（後端、SRE、嵌入式、安全、效能工程） |

## 附錄（`Appendices/`）

| 檔名 | 內容 |
|---|---|
| A - 公式與數字速查.md | 進位轉換、整數範圍、浮點格式、位址切分、cache 參數公式、page table 計算、效能公式（CPE、Amdahl）、延遲數量級表 |
| B - 工具指令速查.md | gcc／clang、gdb／lldb、objdump、readelf、nm、ldd、strace、ltrace、perf、valgrind、ASan、TSan、/proc 檔案、ss 等常用指令與情境 |
| C - 術語表.md | 全書術語（英文、中文、一句話定義、首次出現章） |
| D - 讀書路線.md | 依背景與目標（大一、轉職後端、SRE、面試）的讀法與時程，對應 Labs |
| E - 延伸閱讀.md | 官方教材與課程、經典書籍與文件，依主題整理 |
