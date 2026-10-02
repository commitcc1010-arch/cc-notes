---
title: 延伸閱讀
---

# 附錄 E　延伸閱讀

本書的設計是自給自足：不讀這裡的任何一項，也能讀懂全書。這份清單是給讀完某一章、想再往下挖的人，依主題整理，每一項都附一句「讀它能得到什麼」與最相關的章節。各章結尾的「延伸閱讀」列的是和該章直接相關的少數資源，這裡則是跨章的總整理。

使用這份清單有三個原則：

- **官方文件優先於二手整理。** 語言標準、ABI、man page、工具手冊是最終的依據；部落格與筆記可以幫你入門，但兩者衝突時以官方文件為準。
- **一次只讀一本。** 清單裡的書每一本都夠讀一個月，挑和你目前工作或附錄 D 路線最相關的一本，讀完再換。
- **注意版本。** 書籍標示的是版次；作業系統與工具的行為會隨版本改變，讀到和你的機器不同的輸出時，先查你那個版本的文件。

書籍只列書名、作者與版次；線上資源的連結都是本書查證過的官方或課程頁面。

## E.1 C 語言

- **《The C Programming Language》**，Brian W. Kernighan、Dennis M. Ritchie，第二版：C 的作者寫的經典入門，篇幅短，讀完能掌握 C 的核心語法與標準函式庫的設計精神（搭配第 2 章）。
- **《C Programming: A Modern Approach》**，K. N. King，第二版：比前一本更有耐心的教科書，每章附大量練習，適合第 2 章讀完仍覺得指標與陣列不熟的人。
- **《Effective C: An Introduction to Professional C Programming》**，Robert C. Seacord，第二版：以現代 C 標準為基礎，強調 undefined behavior、整數安全與正確的錯誤處理，能補上第 2、5 章「為什麼這樣寫才安全」的部分。
- **《Expert C Programming: Deep C Secrets》**，Peter van der Linden，初版：用大量真實案例解釋宣告語法、陣列與指標的差異和連結的怪現象，讀起來輕鬆，適合讀完第 10、18 章後當作複習。
- **《Hacker's Delight》**，Henry S. Warren, Jr.，第二版：收錄各種位元運算技巧與推導，是做 Data Lab 之後想知道「還有哪些位元技巧」的最佳參考（搭配第 3–5 章）。
- **《Secure Coding in C and C++》**，Robert C. Seacord，第二版：有系統地整理字串、整數、動態記憶體與格式化輸出的安全問題，能把第 5、11、26 章的防禦觀念延伸成程式碼審查的檢查清單。
- [Stanford CS107：Pointer Pitfalls](https://web.stanford.edu/class/archive/cs/cs107/cs107.1234/resources/pointer_pitfalls.html)：一頁整理初學者最常犯的指標錯誤，適合第 2 章讀完後對照自己的程式找問題。
- [GCC 線上文件](https://gcc.gnu.org/onlinedocs/)：查 `-O`、`-W`、`-f` 系列選項的正式定義，遇到「這個警告是什麼意思」「這個最佳化會做什麼」時以這裡為準（搭配第 2、14 章）。
- [POSIX 規格（The Open Group Base Specifications）](https://pubs.opengroup.org/onlinepubs/9799919799/)：C 標準函式庫與 POSIX 介面的正式規格，判斷一個行為是「標準保證」還是「某個實作碰巧如此」時查這裡。

## E.2 組合語言與 ABI

- [System V x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI)：x86-64 Linux 的 calling convention、stack 對齊、red zone 與資料型別大小的正式來源，第 9 章的每一條規則都可以在這裡找到出處。
- [Intel 64 and IA-32 Architectures Software Developer's Manuals](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)：每一條 x86-64 指令的精確語意與對條件碼的影響，讀 Bomb Lab 或 `perf annotate` 時遇到不認識的指令就查這裡（搭配第 7、8 章）。
- [GNU Binutils 文件](https://sourceware.org/binutils/docs/)：GNU assembler 的 AT&T 語法細節，以及 `objdump`、`as` 的完整選項（搭配第 7 章）。
- [CS:APP 3e Web Asides](https://csapp.cs.cmu.edu/3e/waside.html)：原書正文之外的補充小節，其中包含多篇機器級程式的延伸主題，適合讀完 Part 2 後挑感興趣的題目補讀。
- **《Low-Level Programming: C, Assembly, and Program Execution on Intel 64 Architecture》**，Igor Zhirkov，初版：從組合語言寫起，一路講到 C 的編譯、連結與載入，適合想親手寫 x86-64 組合語言、而不只是讀它的人（搭配第 7–9、18 章）。
- **《Computer Organization and Design ARM Edition: The Hardware/Software Interface》**，David A. Patterson、John L. Hennessy，ARM 版初版：以 ARMv8 為例講指令集與處理器，能補足第 7 章 ARM64 對照只點到為止的部分。

## E.3 處理器與效能

- **《Computer Organization and Design RISC-V Edition: The Hardware/Software Interface》**，David A. Patterson、John L. Hennessy，RISC-V 版第二版：從指令集到 pipeline 的完整教科書，讀完第 12、13 章後想看另一種指令集的 datapath 設計可以接著讀。
- **《Computer Architecture: A Quantitative Approach》**，John L. Hennessy、David A. Patterson，第六版：研究所等級的處理器與記憶體系統設計，能把第 13 章的 out-of-order、分支預測與第 16 章的 cache 設計推到量化分析的深度。
- **《Systems Performance: Enterprise and the Cloud》**，Brendan Gregg，第二版：涵蓋 CPU、記憶體、檔案系統、磁碟、網路的效能分析方法與工具，是第 14 章與第 33 章最直接的延伸，SRE 必讀。
- **《Performance Analysis and Tuning on Modern CPUs》**，Denis Bakhvalov，第二版：專注在用硬體效能計數器找出 CPU 端的瓶頸，能把第 14、17 章的 `perf stat` 用法延伸到 top-down 分析。
- Intel SDM（見 E.2）的第 3 冊描述了 cache、TLB 與效能監控的硬體介面，想知道 `perf` 的事件從哪裡來時可以查閱（搭配第 14、16 章）。

## E.4 記憶體與作業系統

- **《Operating Systems: Three Easy Pieces》**，Remzi H. Arpaci-Dusseau、Andrea C. Arpaci-Dusseau（作者持續修訂的線上教科書，讀最新版）：以虛擬化、並行、持久化三大主題講作業系統，和第 20–27、30–32 章幾乎一一對應，是最適合本書讀者的作業系統教科書。
- **《The Linux Programming Interface》**，Michael Kerrisk，初版：Linux 系統程式設計的百科全書，process、signal、`mmap`、file I/O、socket 都有完整範例，是第 20–30 章的最佳參考書。
- **《Advanced Programming in the UNIX Environment》**，W. Richard Stevens、Stephen A. Rago，第三版：Unix 系統程式設計的經典，對 process 控制、signal 與 terminal 的講解特別細，做 Shell Lab 時很有幫助（搭配第 21、22 章）。
- **《Understanding the Linux Kernel》**，Daniel P. Bovet、Marco Cesati，第三版：從 kernel 內部講 page fault 處理、記憶體管理與排程，內容以較舊的 2.6 版 kernel 為準，適合想知道第 23、24 章「kernel 那一側在做什麼」的人。
- **《The Garbage Collection Handbook: The Art of Automatic Memory Management》**，Richard Jones、Antony Hosking、Eliot Moss，第二版：完整整理 mark-sweep、copying、generational、concurrent GC 與 allocator 設計，是第 25、26 章之後的進階讀物。
- **〈What Every Programmer Should Know About Memory〉**，Ulrich Drepper（2007 年的長篇技術文章）：從 DRAM、cache 到 NUMA 講程式設計師需要知道的記憶體細節，部分硬體數字已經過時，但觀念仍然適用（搭配第 15–17 章）。
- [Linux man pages（man7.org）](https://man7.org/linux/man-pages/)：`mmap(2)`、`madvise(2)`、`proc(5)` 這些頁面是解讀 `/proc/PID/maps`、`smaps` 與 RSS 的正式依據（搭配第 23、24 章）。

## E.5 連結

- **《Linkers and Loaders》**，John R. Levine，初版：唯一一本專講連結器與載入器的書，從目的檔格式、符號解析到 shared library 都有，部分格式細節已舊，但觀念完整（搭配第 18、19 章）。
- [ELF 規格](https://refspecs.linuxfoundation.org/elf/elf.pdf)：ELF 檔頭、section、symbol table 與 relocation entry 的格式定義，自己寫程式解析 ELF（第 18 章的動手做）時以它為準。
- [System V x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI)（見 E.2）：x86-64 的 relocation 類型、GOT 與 PLT 的格式定義都在這份文件，是第 19 章手算 relocation 的依據。
- [GNU Binutils 文件](https://sourceware.org/binutils/docs/)（見 E.2）：`ld` 的連結順序、linker script，以及 `readelf`、`nm` 的完整選項，處理 link error 時最常查（搭配第 18 章）。
- **〈How To Write Shared Libraries〉**，Ulrich Drepper（技術文章）：從效能與 ABI 相容的角度講 shared library 該怎麼寫，能把第 19 章的 PIC、symbol versioning 延伸成實務守則。
- [Linux man pages](https://man7.org/linux/man-pages/)：`ld.so(8)` 說明 dynamic linker 搜尋 library 的順序與 `LD_LIBRARY_PATH`、`LD_PRELOAD` 的行為（搭配第 19 章）。

## E.6 I/O 與網路

- **《UNIX Network Programming, Volume 1: The Sockets Networking API》**，W. Richard Stevens、Bill Fenner、Andrew M. Rudoff，第三版：socket 程式設計的權威參考，對 TCP 狀態、非阻塞 I/O 與 I/O multiplexing 的講解遠比第 28、30 章深入。
- **《TCP/IP Illustrated, Volume 1: The Protocols》**，Kevin R. Fall、W. Richard Stevens，第二版：用封包擷取逐步展示 TCP/IP 各層協定的行為，讀完能真正理解第 28 章的三向交握、`TIME_WAIT` 與重送。
- **《High Performance Browser Networking》**，Ilya Grigorik，初版：從延遲與頻寬的角度講 TCP、TLS 與 HTTP，能把第 29 章的 keep-alive 與 RTT 手算延伸到現代 web 效能。
- [Linux man pages](https://man7.org/linux/man-pages/)：`socket(7)`、`tcp(7)`、`epoll(7)` 列出所有 socket 選項與 epoll 的觸發模式，是寫真實網路服務時的必備參考（搭配第 28、30 章）。
- [POSIX 規格](https://pubs.opengroup.org/onlinepubs/9799919799/)：`read`、`write` 在什麼情況下可以回傳少於要求的位元組數，以這裡的定義為準（搭配第 27 章的 short count）。
- 《The Linux Programming Interface》（見 E.4）的 file I/O 與 socket 各章，有比第 27、28 章更完整的錯誤處理範例。

## E.7 並行

- **《Programming with POSIX Threads》**，David R. Butenhof，初版：Pthreads 的經典教科書，對 mutex、condition variable 與 thread 取消的語意講得非常精確（搭配第 30、31 章）。
- **《The Art of Multiprocessor Programming》**，Maurice Herlihy、Nir Shavit、Victor Luchangco、Michael Spear，第二版：從正確性的理論基礎講 lock、lock-free 資料結構與 memory model，是第 32 章「lock-free 的代價」之後的進階讀物。
- **《C++ Concurrency in Action》**，Anthony Williams，第二版：雖然以 C++ 為例，但對 atomic、memory ordering 與 thread-safe 資料結構的說明可以直接套用到 C11 的 `<stdatomic.h>`（搭配第 32 章）。
- **《Rust Atomics and Locks》**，Mara Bos，初版：用短小的例子講 acquire、release 與 lock 的實作，是理解第 32 章記憶體模型最平易近人的一本。
- **《Is Parallel Programming Hard, And, If So, What Can You Do About It?》**，Paul E. McKenney（作者持續修訂的線上書，讀最新版）：Linux kernel 開發者寫的並行程式設計指南，對 cache、false sharing 與擴展性的分析非常實務（搭配第 32 章）。
- 《Operating Systems: Three Easy Pieces》（見 E.4）的並行篇：用簡短章節講 lock、condition variable 與 semaphore，適合第 31 章讀完後換一種講法複習。
- [ThreadSanitizer 文件](https://clang.llvm.org/docs/ThreadSanitizer.html)：說明 TSan 能偵測的 race 類型、使用限制與效能成本（搭配第 31 章）。

## E.8 除錯工具

- [GDB 官方文件](https://sourceware.org/gdb/current/onlinedocs/gdb.html/)：`break`、`watch`、`x`、`thread apply all bt` 與 core dump 分析的完整說明，是 Bomb Lab 與讀 core dump 時最常翻的手冊（搭配第 2、9、33 章）。
- [AddressSanitizer 文件](https://clang.llvm.org/docs/AddressSanitizer.html)：說明 ASan 能抓的錯誤類型、shadow memory 的原理與執行時選項（搭配第 11、26 章）。
- [UndefinedBehaviorSanitizer 文件](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)：列出 UBSan 可檢查的每一種 undefined behavior 與對應的編譯選項（搭配第 5、26 章）。
- [ThreadSanitizer 文件](https://clang.llvm.org/docs/ThreadSanitizer.html)（見 E.7）：race 偵測的正式說明。
- [GCC 線上文件](https://gcc.gnu.org/onlinedocs/)（見 E.1）：`-g`、`-fsanitize`、`-fstack-protector` 等除錯與防護選項的定義（搭配第 2、11 章）。
- [GNU Binutils 文件](https://sourceware.org/binutils/docs/)（見 E.2）：`objdump`、`readelf`、`nm`、`addr2line` 的用法，從位址反查原始碼行號時會用到。
- [Linux man pages](https://man7.org/linux/man-pages/)：`strace(1)` 與 `proc(5)` 是第 20、33 章診斷流程的依據。
- **《The Art of Debugging with GDB, DDD, and Eclipse》**，Norman Matloff、Peter Jay Salzman，初版：用完整的除錯案例示範中斷點、watchpoint 與多執行緒除錯，適合第 2 章之後想系統化練 `gdb` 的人。
- **《Debugging: The 9 Indispensable Rules for Finding Even the Most Elusive Software and Hardware Problems》**，David J. Agans，初版：不講特定工具，只講找 bug 的方法，和第 33 章「往下鑽要有證據」的精神一致。
- **《BPF Performance Tools》**，Brendan Gregg，初版：用 eBPF 在 production 上安全地追蹤 system call、page fault 與 I/O 延遲，是 `strace` 與 `perf` 之後的下一步（搭配第 33 章）。

## E.9 課程與 Labs

- **《Computer Systems: A Programmer's Perspective》**，Randal E. Bryant、David R. O'Hallaron，第三版：本書的骨架；附錄 D 的 D.7 節有逐章對照表，購買前可以先看官方網站對各版本的說明。
- [CS:APP 官方網站](https://csapp.cs.cmu.edu/)：原書的入口，從這裡可以連到第三版的 Labs、學生資源、勘誤與 web aside 等頁面。
- [CS:APP 3e Lab Assignments](https://csapp.cs.cmu.edu/3e/labs.html)：九個 Labs 的說明、writeup 與自學版材料下載（搭配第 34 章）。
- [CS:APP 3e 學生資源](https://csapp.cs.cmu.edu/3e/students.html)：官方提供給學生的補充資源。
- [CS:APP 3e 勘誤表](https://csapp.cs.cmu.edu/3e/errata.html)：原書已知錯誤的清單，對照讀原書時發現對不上，先查這裡。
- [CS:APP 3e 與 2e 的差異](https://csapp.cs.cmu.edu/3e/changes3e.html)：說明第三版改了什麼，手上的二手資料若以第二版為準，可以用它判斷哪些部分已經過時。
- [CMU 15-213 課程網站](https://www.cs.cmu.edu/~213/)：使用這些 Labs 的原始課程，有講義、時程與學期進度，可以拿來校準自己的學習速度（搭配附錄 D）。
- [CMU 15-213 2010 年春季講義](https://www.cs.cmu.edu/afs/cs/academic/class/15213-s10/www/lectures/)：較早學期的講義投影片，可以看到同一門課在不同時期的講法；和第三版不同之處以第三版為準。
- [Stanford CS107：Working on Assignments](https://web.stanford.edu/class/cs107/working-on-assignments.html)：另一門系統入門課給學生的作業方法建議，和第 34 章 34.3 節的 lab notebook 方法互相呼應。
- 社群學習筆記：[AkiyamaKunka/csapp-notes](https://github.com/AkiyamaKunka/csapp-notes)、[BanaHaker/CSAPP-Notes](https://github.com/BanaHaker/CSAPP-Notes)：讀者自行整理的原書筆記，可以用來對照別人怎麼理解同一個觀念；內容未經本書查證，若其中有 Lab 解答，請在自己完成該 Lab 之前跳過（理由見 34.2 節的學術誠信說明）。
