---
title: 工具指令速查
---

# 附錄 B　工具指令速查

這份附錄把全書用過的工具指令依「你正在做什麼」整理成表。每一列回答四件事：指令本身、它做什麼、什麼時候該想到它、哪一章有完整的例子。指令裡的 `PID`、`PORT`、`./prog` 是要換成實際值的佔位符。

平台標示的意思如下：

| 標示 | 意思 |
|---|---|
| 通用 | Linux 與 macOS 都能用（旗標可能有小差異） |
| Linux | 只在 Linux 上有；括號裡寫 macOS 上最接近的替代品，沒有就寫「無直接對應」 |
| macOS | 只在 macOS 上有，通常是某個 Linux 工具的對應 |
| GCC／clang | 只有其中一個編譯器支援 |

多數診斷工具（`strace`、`perf`、`/proc`、`ss`）是 Linux 專屬，因為 production 服務大多跑在 Linux 上。在 Mac 上學習時，可以先用 macOS 的對應工具理解概念，再到 Linux 虛擬機或容器裡練習原版。

## B.1 編譯與最佳化

### 編譯的四個階段

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `cc -E f.c -o f.i` | 只做前處理，展開 `#include` 與巨集 | 懷疑巨集展開錯、找不到標頭檔 | 第 1、18 章 | 通用 |
| `cc -S -O1 f.c` | 編譯成組合語言 `f.s` | 想看編譯器把某段 C 翻成什麼 | 第 1、7 章 | 通用 |
| `cc -c f.c` | 組譯成 relocatable 目的檔 `f.o` | 多檔案建置、檢查單一檔案的符號 | 第 1、18 章 | 通用 |
| `cc a.o b.o -o prog` | 連結成執行檔 | 遇到 `undefined reference` 時確認送進 linker 的檔案 | 第 1、18 章 | 通用 |
| `clang -target x86_64-linux-gnu -O1 -S -fno-asynchronous-unwind-tables -o - f.c` | 在任何機器上產生 x86-64 Linux 的組合語言 | 在 Mac（ARM64）上讀本書的 x86-64 範例 | 第 0、7 章 | clang |

### 警告與標準

| 旗標 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `-std=c17` | 指定 C 標準 | 一律加上，不依賴編譯器預設值 | 第 2 章 | 通用 |
| `-Wall -Wextra` | 開啟大部分常用警告（含 `-Wformat`、`-Wsign-compare`） | 一律加上 | 第 2、4 章 | 通用 |
| `-Werror` | 警告視為錯誤 | CI，避免新警告混進舊警告 | 第 2、4、26 章 | 通用 |
| `-Wconversion`、`-Wsign-conversion` | 抓可能遺失資料的隱式截斷與有號／無號轉換 | 解析器、協定、安全相關程式 | 第 4 章 | 通用 |
| `-fsigned-char`／`-funsigned-char` | 強制 `char` 的有無號 | 重現「x86-64 正常、ARM64 錯誤」這類 bug | 第 4 章 | 通用 |
| `-I dir`、`-L dir`、`-l name`、`-D NAME=val` | 標頭檔路徑、函式庫路徑、連結函式庫、定義巨集 | `jpeglib.h: No such file`、`undefined reference to jpeg_*` | 第 2 章 | 通用 |

### 最佳化與量測相關

| 旗標 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `-O0`、`-Og` | 不最佳化或「適合除錯的最佳化」 | 單步除錯，避免 `<optimized out>` | 第 2、7 章 | 通用 |
| `-O2` | 一般 production 的最佳化等級 | 正式版本；量效能時要用部署的等級 | 第 2、14 章 | 通用 |
| `-O3` | 更積極的展開與向量化 | 量過確實比 `-O2` 快時 | 第 14 章 | 通用 |
| `-g` | 產生 debug 資訊，不影響產生的程式碼 | 一律加；production 也保留或另存 | 第 2、14、33 章 | 通用 |
| `-fno-omit-frame-pointer` | 保留 frame pointer | 讓 `perf record -g`、crash handler 的呼叫鏈完整 | 第 9、14、33 章 | 通用 |
| `-march=x86-64-v3` 等 | 允許使用指定世代的指令集 | 確認所有部署機器都支援時；部署版本不要用 `-march=native` | 第 12、14 章 | 通用 |
| `-flto` | link-time optimization，跨檔案 inline | 熱點函式在別的檔案、編譯器看不到 | 第 14 章 | 通用 |
| `-fprofile-generate`／`-fprofile-use` | PGO，用真實執行資料指導最佳化 | 有代表性的訓練工作負載時 | 第 14 章 | 通用 |
| `-Rpass-missed=loop-vectorize` | 報告哪些迴圈沒向量化、為什麼 | 期待 SIMD 卻沒變快 | 第 14 章 | clang（GCC：`-fopt-info-vec-missed`） |
| `-ffast-math` | 允許重排浮點運算、假設沒有 NaN | 只對確定可接受的檔案開；會讓 `isnan` 失效 | 第 6、14 章 | 通用 |
| `-ffp-contract=off` | 禁止把乘加合併成 FMA | 要求 x86-64 與 ARM64 結果位元一致 | 第 6 章 | 通用 |
| `-fwrapv` | 把 signed overflow 定義為繞回 | 舊程式依賴繞回時的過渡手段 | 第 5 章 | 通用 |
| `-fno-strict-aliasing` | 關閉 strict aliasing 假設 | 診斷「`-O2` 後型別雙關出錯」；問題消失就是它 | 第 10 章 | 通用 |
| `-pg` 加 `gprof ./prog gmon.out` | 插樁式 profiling | 教學、單機程式 | 第 14 章 | Linux（macOS：`sample`、Instruments） |

### 安全強化與連結相關

| 旗標 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `-fstack-protector-strong` | stack canary | production 建置 | 第 11 章 | 通用 |
| `-D_FORTIFY_SOURCE=2`（需 `-O1` 以上） | 已知大小時檢查 `memcpy`、`strcpy` 的長度 | production 建置 | 第 11 章 | 通用 |
| `-fstack-clash-protection` | 防止大 stack frame 跳過 guard page | production 建置 | 第 11 章 | Linux |
| `-fPIE -pie` | 產生可被 ASLR 隨機化的執行檔 | production 建置（macOS 預設就是 PIE） | 第 11 章 | 通用 |
| `-Wl,-z,relro,-z,now` | full RELRO，GOT 執行中唯讀 | production 建置 | 第 11、19 章 | Linux |
| `-fPIC -shared` | 產生 shared library | 錯誤訊息 `relocation R_X86_64_32 ... can not be used when making a shared object` | 第 19 章 | 通用 |
| `-fno-plt` | 直接 `call *GOT`，少一次跳躍 | 搭配 BIND_NOW 時的微最佳化 | 第 19 章 | Linux |
| `-mcmodel=medium` | 允許超過 ±2 GiB 的靜態資料 | `relocation truncated to fit: R_X86_64_PC32` | 第 19 章 | Linux |
| `-fno-common` | 同名未初始化全域變數不合併 | 全域變數莫名被改掉 | 第 18 章 | 通用 |
| `-fstack-usage`、`-Wstack-usage=4096` | 列出每個函式的 stack 用量；超過門檻就警告 | 遞迴解析器、thread stack 很小時 | 第 9 章 | GCC |

## B.2 除錯：gdb 與 lldb

Linux 上用 gdb，macOS（尤其 Apple Silicon）上用 lldb；lldb 也接受 `b`、`n`、`s`、`c`、`bt` 這類 gdb 風格的簡寫。

### 基本操作對照

| 目的 | gdb | lldb | 什麼時候用 | 出處 |
|---|---|---|---|---|
| 載入程式 | `gdb ./prog` | `lldb ./prog` | 開始一次除錯 | 第 2 章 |
| 設中斷點 | `break scale_dim`、`b scale.c:12` | `b scale_dim`、`b scale.c:12` | 想在某函式或某行停下 | 第 2 章 |
| 執行 | `run arg1 arg2` | `run arg1 arg2` | — | 第 2 章 |
| 下一行（不進函式）／進入函式 | `next`／`step` | `next`／`step` | 單步追蹤 | 第 2 章 |
| 跑到函式返回／繼續 | `finish`／`continue` | `finish`／`continue` | — | 第 2 章 |
| 印運算式 | `print x`、`p/x $rax` | `p x`、`register read rax` | 看變數或暫存器 | 第 2、7 章 |
| 所有區域變數 | `info locals` | `frame variable` | 當機後看當下狀態 | 第 2、33 章 |
| 呼叫堆疊 | `bt`、`bt full` | `bt` | 當機後第一個要打的指令 | 第 2、9 章 |
| 切換 frame | `frame 1`、`up`、`down` | `frame select 1`、`up`、`down` | 看呼叫者當時的變數 | 第 2、9 章 |
| 這一層 frame 的資訊 | `info frame` | `frame info` | 看 saved registers、return address | 第 9 章 |
| 看記憶體 | `x/4xb &w`、`x/16gx $rsp` | `x/4xb &w`、`memory read -fx -s8 -c16 $sp` | 看原始 bytes、stack 內容 | 第 2、9 章 |
| 變數被改時停下 | `watch x` | `watchpoint set variable x` | 找「誰改壞了這個值」 | 第 2、11 章 |
| 暫存器 | `info registers`、`info registers rsp rip` | `register read`、`register read sp fp lr` | 看參數暫存器、`%rsp` 對齊 | 第 2、7、9 章 |

### 組合語言層級

| 目的 | gdb | lldb | 什麼時候用 | 出處 |
|---|---|---|---|---|
| 當機的那一條指令 | `x/i $pc` | `disassemble --pc` | segfault、`SIGILL`、`SIGFPE` | 第 7、12 章 |
| 反組譯整個函式 | `disassemble get_gray` | `disassemble --name get_gray` | 對照原始碼與機器碼 | 第 7 章 |
| 原始碼與組合語言交錯 | `disassemble /s`（需 `-g`） | `disassemble --mixed` | 最佳化後對不上原始碼 | 第 7 章 |
| 切換成 Intel 語法 | `set disassembly-flavor intel` | `settings set target.x86-disassembly-flavor intel` | 習慣 Intel 語法時 | 第 7 章 |
| 指令的原始 bytes | `x/8xb $pc`、`disassemble /r` | `memory read --size 1 --count 8 $pc` | 判斷是不是 AVX-512 等指令 | 第 12 章 |
| struct 的 offset 與 hole | `ptype /o struct thumb_meta` | 無直接對應（用 `clang -Xclang -fdump-record-layouts`） | 檢查 padding | 第 10 章 |

### Core dump、附加與多執行緒

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `ulimit -c unlimited` | 允許產生 core dump | 想在當機後留下現場 | 第 2、33 章 | 通用 |
| `coredumpctl list thumbd`、`coredumpctl gdb PID` | 列出並用 gdb 打開 systemd 收集的 core | systemd 系統上的當機分析 | 第 2、9、33 章 | Linux |
| `gdb ./prog core` | 打開 core dump | 有 core 檔時 | 第 2、12、34 章 | Linux（macOS：`lldb ./prog -c core`） |
| `info proc mappings` | 列出 process 的記憶體區域 | 判斷 `%rsp` 或可疑位址屬於哪個區域 | 第 9、23、34 章 | Linux |
| `p $_siginfo._sifields._sigfault.si_addr` | 印出造成 fault 的位址 | 判斷是 NULL、已釋放還是 guard page | 第 33 章 | Linux |
| `info threads`、`thread apply all bt` | 列出所有 thread 與它們的呼叫堆疊 | 卡住、deadlock、找出當掉的 thread | 第 9、30、31 章 | 通用（lldb：`thread list`、`bt all`） |
| `gdb -p PID -batch -ex "thread apply all bt" > bt.txt` | 附加到執行中的 process 抓所有 stack 後離開 | production 卡住時保存現場；會暫停 process 數秒 | 第 30、31、33 章 | Linux（macOS：`lldb -p PID`） |
| `gdb -p PID -batch -ex 'call (void) malloc_stats()'` | 讓 glibc 印出 heap 統計到程式的 stderr | RSS 上升時區分 in-use 與 allocator 保留 | 第 33 章 | Linux（glibc） |
| `lldb --batch -o "run overflow" ./drill` | 非互動地執行並在當機時印出狀態 | 腳本化重現 | 第 33 章 | 通用 |

## B.3 看二進位檔

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `file prog` | 檔案格式、架構、是否 stripped | `Exec format error`、混用 arm64 與 x86-64 的 `.o` | 第 12、18、19 章 | 通用 |
| `objdump -d prog` | 反組譯 | 看編譯器實際產生的指令 | 第 2、7 章 | 通用 |
| `objdump -d --no-show-raw-insn` | 反組譯但不印機器碼 bytes | 讓輸出好讀 | 第 2 章 | 通用 |
| `objdump -S prog`（需 `-g`） | 原始碼穿插組合語言 | 對照最佳化後的程式 | 第 2 章 | 通用 |
| `objdump -d -r x.o` | 反組譯並列出待填的 relocation | 學 relocation、看哪些位址連結時才決定 | 第 18、19 章 | 通用 |
| `objdump -t`、`objdump -h` | 符號表、section 列表 | 沒有 `readelf` 的平台 | 第 18 章 | 通用 |
| `objdump -M intel`／`--x86-asm-syntax=intel` | Intel 語法輸出 | GNU objdump 用前者，macOS 的 LLVM objdump 用後者 | 第 7 章 | 通用 |
| `readelf -h prog` | ELF header；`Type` 是 `DYN` 或 `EXEC` | 確認是不是 PIE | 第 11、34 章 | Linux |
| `readelf -S x.o` | section 列表與大小 | 看 `.text`、`.data`、`.bss` 各多大 | 第 18 章 | Linux（macOS：`objdump -h`、`size -m`） |
| `readelf -s x.o`、`readelf -sW prog` | 完整符號表 | 確認符號的 binding 與 section；`__stack_chk` 是否存在 | 第 18、34 章 | Linux（macOS：`objdump -t`） |
| `readelf -lW prog` | program header（segment） | 看 `GNU_STACK` 有沒有 `E`、`GNU_RELRO`、`PT_INTERP` | 第 11、19、34 章 | Linux |
| `nm x.o` | 精簡符號表（T、D、B、R、U、C、W） | `undefined reference` 時找定義在哪 | 第 1、18 章 | 通用 |
| `nm -u`、`nm -C`、`nm -A *.o \| grep ' x$'` | 只看 undefined、C++ demangle、印出檔名 | 找重複定義、C 與 C++ 名稱不符 | 第 18 章 | 通用 |
| `nm -D prog \| grep _chk` | 動態符號表 | 確認 fortify、canary 是否生效；`LD_PRELOAD` 能否攔到 | 第 11、19 章 | Linux |
| `ar t libx.a` | 列出 static library 的成員 | 確認某個 `.o` 有沒有被打包 | 第 18 章 | 通用 |
| `xxd file \| head` | 以 hex 檢視檔案 | 解析檔頭、byte order 問題 | 第 3 章 | 通用 |
| `addr2line -e prog 0x401234` | 位址轉成檔名與行號 | stack trace 只有位址時 | 第 9 章 | Linux（macOS：`atos`） |
| `pahole ./prog` | 從 debug info 列出每個 struct 的 hole 與 cache line 邊界 | 減少 padding、找 false sharing | 第 10 章 | Linux（dwarves 套件） |
| `clang -Xclang -fdump-record-layouts -fsyntax-only x.c` | 印出 clang 計算的 struct 布局 | 沒有 `pahole` 時 | 第 10 章 | clang |

**檢查一個 binary 的防護**（第 11、34 章，Linux）：

| 要確認 | 指令 | 看什麼 |
|---|---|---|
| PIE | `readelf -h ./thumbd \| grep Type` | `DYN` 是 PIE，`EXEC` 不是 |
| stack 不可執行 | `readelf -lW ./thumbd \| grep GNU_STACK` | 權限欄是 `RW`，沒有 `E` |
| stack canary | `nm -D ./thumbd \| grep __stack_chk_fail` | 有這個符號 |
| fortify | `nm -D ./thumbd \| grep _chk` | 出現 `__memcpy_chk` 等 |
| full RELRO | `readelf -lW ./thumbd \| grep GNU_RELRO` 與 `readelf -d ./thumbd \| grep BIND_NOW` | 兩者都有 |
| 系統的 ASLR | `cat /proc/sys/kernel/randomize_va_space` | `2` 表示完整隨機化 |

## B.4 連結與載入

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `ldd ./prog` | 在目前環境下，每個 `.so` 會解析到哪個檔案 | `error while loading shared libraries`、`not found` | 第 1、19、33 章 | Linux（macOS：`otool -L`） |
| `readelf -d ./prog \| grep -E 'NEEDED\|RUNPATH\|RPATH'` | 執行檔「要求」哪些 library 與搜尋路徑 | 不想執行目標程式時（`ldd` 可能會執行它） | 第 19 章 | Linux |
| `objdump -p ./prog` | 只讀取 ELF 的動態段資訊 | 檢查來路不明的執行檔 | 第 19 章 | 通用 |
| `grep jpeg /proc/PID/maps` | 執行中的 process「實際」載入了哪個檔案 | production 除錯時最可靠 | 第 19 章 | Linux（macOS：`vmmap PID`） |
| `LD_DEBUG=libs ./prog` | 印出 dynamic linker 的搜尋過程 | 搞不清楚為什麼載入了某個版本 | 第 19 章 | Linux（glibc） |
| `LD_DEBUG=bindings ./prog` | 印出符號綁定 | plugin 第一次呼叫才當機 | 第 19 章 | Linux（glibc） |
| `LD_LIBRARY_PATH=dir ./prog` | 臨時加入搜尋路徑 | 開發與測試；不要放在服務的全域設定 | 第 19 章 | Linux（macOS：`DYLD_LIBRARY_PATH`） |
| `-Wl,-rpath,'$ORIGIN/../lib'` | 把搜尋路徑寫進執行檔（RUNPATH） | library 跟著程式一起發佈 | 第 19 章 | Linux（macOS：`@rpath`、`@loader_path`） |
| `ldconfig -p \| grep libX` | 列出系統 library cache | 確認系統是否找得到某個 soname | 第 19 章 | Linux |
| `objdump -T prog \| grep -o 'GLIBC_[0-9.]*' \| sort -uV \| tail -1` | 執行檔需要的最高 glibc 版本 | `version 'GLIBC_2.34' not found` | 第 19 章 | Linux |
| `ldd --version` | 目標機器的 glibc 版本 | 同上，在目標機器上跑 | 第 19 章 | Linux |
| `LD_BIND_NOW=1 ./prog` | 啟動時就解析所有符號 | 測試 lazy binding 藏起來的缺符號 | 第 19 章 | Linux |
| `LD_PRELOAD=./shim.so ./prog` | 執行時 interposition，替換 library 函式 | 攔截 `malloc`、注入除錯程式 | 第 19 章 | Linux（macOS：`DYLD_INSERT_LIBRARIES`，受 SIP 限制） |
| `-Wl,--wrap=malloc` | 連結時把 `malloc` 改接到 `__wrap_malloc` | 只想在自己的程式裡攔截 | 第 19 章 | Linux（GNU ld；macOS linker 不支援） |
| `cc ... -Wl,--trace`、`-Wl,--trace-symbol=X`、`-Wl,-Map,out.map` | 連結器選了哪些檔案、某符號從哪來 | 改了 `.a` 但行為沒變、連結順序問題 | 第 18 章 | Linux（macOS：`-Wl,-map,out.map`、`-Wl,-why_load`） |
| `ltrace -c ./prog` | 統計 library 函式的呼叫次數與時間 | 懷疑某個 library 函式慢或被呼叫太多次 | 第 19 章 | Linux（無直接對應） |

## B.5 系統呼叫與 process

### strace

`strace` 透過 `ptrace` 讓目標在每次 system call 進出時停下來，對 system call 密集的程式可能慢上數倍；production 上只短時間、限縮範圍使用（第 20、33 章）。macOS 的對應是 `dtruss`，但在預設的 SIP 設定下無法追蹤大部分程式（第 20 章）。

| 指令 | 用途 | 什麼時候用 | 出處 |
|---|---|---|---|
| `strace ./prog` | 從頭追蹤，印出每一個 system call 與回傳值 | 看程式和 kernel 的對話 | 第 1、20 章 |
| `strace -p PID` | 附加到執行中的 process | 服務卡住或變慢 | 第 20 章 |
| `strace -f` | 一併追蹤子行程與 thread | 有 thread pool 或 fork 的程式幾乎一定要加 | 第 20、21 章 |
| `strace -c -f -p PID` | 只輸出統計表：次數、錯誤數、時間 | `sys` 時間高，找出是哪種呼叫太多 | 第 20、32 章 |
| `strace -e trace=openat,read` | 只看指定的呼叫 | 縮小範圍、降低負擔 | 第 20、27 章 |
| `strace -e trace=%file`／`%network`／`%process`／`%signal` | 依類別過濾 | 讀了哪些設定檔、連到哪裡、fork／exec 了誰、signal 怎麼遞送 | 第 20、21、22 章 |
| `strace -T`、`strace -tt` | 每筆附上耗時、時間戳記 | 哪個呼叫在等、等多久 | 第 20 章 |
| `strace -o out.txt` | 輸出到檔案 | 避免和程式輸出混在一起 | 第 20 章 |
| `timeout 10 strace -c -p TID` | 限時附加 | production 上的安全用法 | 第 33 章 |
| `perf trace` | 負擔較低的 system call 追蹤 | `strace` 改變了時序或太慢時 | 第 20 章 |

以上全部是 Linux 專屬。

### Process 與 signal

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `./prog; echo "exit=$?"` | 看上一個指令的結束碼；128 + n 代表被 signal n 終止 | 判斷是 `exit(1)` 還是 `SIGSEGV`（139） | 第 2 章 | 通用 |
| `time ./prog` | `real`、`user`、`sys` 三種時間 | 判斷時間花在計算、kernel 還是等待 | 第 20 章 | 通用 |
| `ps -eo pid,ppid,stat,comm` | 列出 process 狀態與父行程 | 找 zombie（STAT 為 `Z`）與它的父行程 | 第 21、30 章 | 通用 |
| `ps -o pid,rss,vsz,etime -p PID` | RSS、VSZ 與執行時間 | 記錄記憶體趨勢 | 第 26 章 | 通用 |
| `ps -o min_flt,maj_flt -p PID` | 累計 minor／major page fault | 重啟後慢、懷疑換頁 | 第 23 章 | Linux |
| `top`、`top -H -p PID` | 即時 CPU 使用；`-H` 以 thread 為單位 | 找出吃 CPU 的 thread | 第 2、30、33 章 | Linux（macOS 的 `top` 沒有 `-H`；改用 `sample PID`） |
| `pidstat -w -p PID 1` | 每秒自願（`cswch/s`）與非自願（`nvcswch/s`）context switch | 判斷是在等 I/O、等鎖，還是 CPU 不夠 | 第 20、32 章 | Linux（sysstat） |
| `grep ctxt_switches /proc/PID/status` | 累計的 context switch 次數 | 同上，不用另外安裝工具 | 第 20 章 | Linux |
| `kill -l` | 列出 signal 名稱與編號 | Linux 與 macOS 編號不同時查表 | 第 22 章 | 通用 |
| `kill -HUP PID`、`kill -TERM PID`、`kill -9 PID` | 送 signal | 重新載入設定、要求結束、強制結束 | 第 2、22 章 | 通用 |
| `kill -0 PID && echo alive` | 只檢查 process 是否存在 | 監控腳本 | 第 22 章 | 通用 |
| `timeout -s TERM -k 5 30 ./job` | 30 秒後送 `SIGTERM`，再 5 秒送 `SIGKILL` | 限制外部工具的執行時間 | 第 22 章 | Linux（GNU coreutils） |
| `grep -E 'Sig(Pnd\|Blk\|Ign\|Cgt)' /proc/PID/status` | pending、blocked、忽略、有 handler 的 signal | 服務對某個 signal 沒反應 | 第 22 章 | Linux |
| `cat /sys/fs/cgroup/pids.max /sys/fs/cgroup/pids.current` | 容器的 PID 上限與目前用量 | `fork` 回傳 `EAGAIN` | 第 21 章 | Linux（cgroup v2） |
| `cat /proc/sys/kernel/pid_max` | 系統的 PID 上限 | 同上 | 第 21 章 | Linux |
| `man 2 read`、`man 3 printf`、`man 7 signal` | 查 system call、函式庫、概觀 | 確認回傳值與錯誤規則 | 第 2 章 | 通用 |

## B.6 記憶體

### Sanitizer 與記憶體檢查工具

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `cc -g -O1 -fsanitize=address -fno-omit-frame-pointer` | ASan：越界、use-after-free、double free | 測試、CI、fuzzing；約慢 2 倍、記憶體多數倍 | 第 2、11、26 章 | 通用 |
| `-fsanitize=address,undefined` | ASan 加 UBSan 一起建置 | 開發與 CI 的標準組合 | 第 2、26 章 | 通用 |
| `-fsanitize=undefined` | UBSan：signed overflow、錯誤 shift、未對齊存取 | `-O0` 與 `-O2` 行為不同 | 第 2、5、10、26 章 | 通用 |
| `-fsanitize=leak`（Linux 上 ASan 預設附帶） | LSan：程式結束時報告 leak | 找真正的 unreachable leak | 第 26 章 | Linux（macOS：`leaks`） |
| `-fsanitize=memory` | MSan：讀取未初始化記憶體 | 同樣輸入結果偶爾不同；所有程式碼都要用它編譯 | 第 26 章 | Linux（clang） |
| `-fsanitize=implicit-conversion` | 執行時偵測改變了值的隱式截斷 | 解析器、大小計算 | 第 4 章 | clang |
| `ASAN_OPTIONS=detect_leaks=1:abort_on_error=1` | ASan 執行期選項；另有 `quarantine_size_mb` 加大 UAF 偵測窗口 | CI 中讓錯誤直接失敗 | 第 26 章 | 通用 |
| `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1` | UBSan 遇錯即停並印 stack | CI | 第 26 章 | 通用 |
| `valgrind --leak-check=full --error-exitcode=1 ./prog` | 不需重新編譯的記憶體檢查，含未初始化讀取 | 每晚測試；慢數十倍 | 第 26 章 | Linux（Apple Silicon 無法使用） |
| `leaks --atExit -- ./prog` | 程式結束時報告 leak | macOS 上找 leak | 第 26、33 章 | macOS |
| `heaptrack ./prog`、`heaptrack_print heaptrack.*.zst` | heap profiler，找出配置點 | RSS 上升、找邏輯 leak | 第 26 章 | Linux |

### 看 process 的記憶體

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `cat /proc/PID/maps` | 每一個 VMA：範圍、權限、檔案 | 看位址空間配置、確認載入的 `.so` | 第 1、19、23、24 章 | Linux（macOS：`vmmap PID`） |
| `cat /proc/PID/smaps_rollup` | RSS、PSS、匿名與檔案頁、dirty、swap 的總計 | 判斷 RSS 是 heap 還是檔案頁、fork 後 COW | 第 23、24、26、33 章 | Linux |
| `pmap -x PID \| sort -k3 -n \| tail` | 依 RSS 排序的映射區域 | 找出最大的區域在長 | 第 23、24、26、33 章 | Linux（macOS：`vmmap PID`） |
| `wc -l /proc/PID/maps` | VMA 數量 | `mmap` 回傳 `ENOMEM` 但記憶體還很多 | 第 24 章 | Linux |
| `grep -E 'MemAvailable\|^Cached\|Committed_AS\|CommitLimit' /proc/meminfo` | 系統可用記憶體、page cache、承諾量 | OOM 調查、overcommit 判斷 | 第 24 章 | Linux |
| `dmesg \| grep thumbd`、`journalctl` | kernel 記錄的 segfault 與 OOM kill | 服務無聲無息地消失 | 第 24、33 章 | Linux |
| `cat /proc/PID/oom_score_adj` | OOM killer 的優先度調整（−1000 到 1000） | 保護關鍵 process | 第 24 章 | Linux |
| `sysctl vm.overcommit_memory`、`sysctl vm.max_map_count` | overcommit 模式、VMA 上限 | `malloc` 不失敗卻被 OOM 殺掉；`ENOMEM` | 第 24 章 | Linux |
| `cat /sys/fs/cgroup/memory.current`、`kubectl describe pod` | 容器的記憶體用量與 `OOMKilled` 原因 | 容器被殺、主機卻有很多記憶體 | 第 24 章 | Linux |
| `cat /sys/kernel/mm/transparent_hugepage/enabled` | THP 設定 | 延遲尖峰、評估 huge page | 第 23 章 | Linux |
| `cat /proc/buddyinfo` | kernel buddy allocator 各大小的空閒塊 | 觀察實體記憶體碎片 | 第 25 章 | Linux |
| `vmstat 1`（看 `si`／`so`） | 換頁進出 | 懷疑 major fault 造成延遲 | 第 23 章 | Linux（macOS：`vm_stat`） |
| `malloc_stats()`、`malloc_info()`、`malloc_trim(0)` | glibc allocator 的統計與歸還 | `free` 後 RSS 不降 | 第 25、33 章 | Linux（glibc） |
| `MALLOC_ARENA_MAX=2 ./prog` | 限制 glibc 的 arena 數 | thread 多時 RSS 偏高 | 第 25 章 | Linux（glibc） |

## B.7 效能

### perf

| 指令 | 用途 | 什麼時候用 | 出處 |
|---|---|---|---|
| `perf stat ./prog` | cycles、instructions、IPC 等總計 | 先判斷 CPU 是在算還是在等 | 第 12、17 章 |
| `perf stat -e branches,branch-misses ./prog` | 分支總數與預測錯誤 | 某類輸入特別慢、工作量相同 | 第 8 章 |
| `perf stat -e L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses ./prog` | L1 與最後一層 cache 的 miss | IPC 低，懷疑存取模式 | 第 16、17 章 |
| `perf stat -e dTLB-load-misses,dTLB-loads` | TLB miss | 大資料集隨機存取慢、CPU 卻不忙 | 第 23、33 章 |
| `perf stat -e page-faults` | page fault 次數 | 剛啟動時延遲高 | 第 23 章 |
| `perf stat -e ... -p PID -- sleep 10` | 對執行中的服務量一段時間 | production 量測 | 第 17、33 章 |
| `perf record -g ./prog`、`perf report` | 取樣 CPU 時間與呼叫鏈 | 找熱點函式 | 第 14、33 章 |
| `perf report --children`／`--no-children --sort symbol` | 含子函式的總時間／只看自身時間 | 函式被 inline、要看整條路徑 | 第 14、33 章 |
| `perf record --call-graph dwarf -p PID` | 用 DWARF unwinding 取呼叫鏈 | 沒有 frame pointer、又不能重新編譯 | 第 9 章 |
| `perf record --call-graph lbr` | 用 Intel LBR 取呼叫鏈 | 較新的 Intel CPU、只需 user space | 第 9 章 |
| `perf record -e L1-dcache-load-misses -g` | 依事件取樣 | 找出 miss 發生在哪一行 | 第 16、17 章 |
| `perf annotate keep_bright` | 逐指令標出取樣比例 | 找出是哪一條分支或 load 最貴 | 第 8 章 |
| `perf top`、`perf top -t TID` | 即時熱點 | CPU 100% 時立刻看在跑什麼 | 第 32、33 章 |
| `perf list` | 列出這台 CPU 可用的事件 | 事件名稱依 CPU 而定 | 第 17 章 |
| `perf c2c record -p PID`、`perf c2c report` | 找出在核心間以 Modified 狀態轉手的 cache line（HITM） | 加 thread 反而變慢，懷疑 false sharing | 第 17、32 章 |

以上全部是 Linux 專屬；macOS 上的取樣 profiler 是 `sample PID 10` 與 Xcode Instruments 的 Time Profiler（第 14 章）。

### 其他效能工具

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `valgrind --tool=cachegrind --cache-sim=yes ./prog`、`cg_annotate cachegrind.out.PID` | 以軟體模擬 cache，列出每一行的 miss | 沒有硬體計數器權限的機器 | 第 16 章 | Linux |
| `lscpu`、`lscpu \| grep -i cache` | CPU 型號、核心數、各層 cache 大小 | 對照 working set 與 cache 容量 | 第 1、15、16 章 | Linux（macOS：`sysctl hw`） |
| `getconf -a \| grep -i CACHE` | cache 大小、associativity、line size | 同上 | 第 15、16 章 | Linux |
| `cat /sys/devices/system/cpu/cpu0/cache/index0/{level,size,ways_of_associativity,coherency_line_size}` | 單一層 cache 的詳細參數 | 手算 set 數與位址切分 | 第 15、16 章 | Linux |
| `sysctl hw.cachelinesize hw.perflevel0.l1dcachesize hw.perflevel0.l2cachesize` | Apple Silicon 的 line 大小與各層 cache | 在 Mac 上做 cache 實驗、決定 `alignas` | 第 15、16、32 章 | macOS |
| `nproc` | 可用的 CPU 數 | 決定 CPU-bound worker 數；容器內要看 CPU 配額 | 第 1、32 章 | Linux（macOS：`sysctl -n hw.ncpu`） |
| `taskset -c 2 ./bench` | 把程式固定在某個 CPU | benchmark 結果每次差很多 | 第 15、17 章 | Linux（無直接對應） |
| `vmstat 1` | run queue（`r`）、context switch（`cs`）、I/O 等待（`wa`） | 判斷 oversubscription 或 I/O 瓶頸 | 第 15、20、32 章 | Linux（macOS：`vm_stat`，欄位不同） |
| `iostat -x 1` | 每顆磁碟的 `await` 與 `%util` | 批次工作慢，懷疑磁碟 | 第 15 章 | Linux（sysstat） |
| `lsblk -d -o NAME,ROTA,SIZE,MODEL` | 是旋轉硬碟（ROTA=1）還是 SSD | 測試機與正式環境儲存不同 | 第 15 章 | Linux |
| `grep flags /proc/cpuinfo` | CPU 支援的指令集 | 部署後 `SIGILL` | 第 12、20 章 | Linux（macOS：`sysctl hw`） |
| `grep . /sys/devices/system/cpu/vulnerabilities/*` | Spectre、Meltdown 等緩解狀態 | 評估推測執行漏洞的影響 | 第 13 章 | Linux |
| `wrk -t16 -c256 -d300s URL` | HTTP 壓力測試 | 放大 race 出現的機率、量吞吐量 | 第 33 章 | 通用 |

## B.8 網路

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `ss -ltnp` | 所有 TCP listening socket 與所屬 process；`Recv-Q` 是 accept queue 長度 | `Connection refused`、確認 bind 的位址 | 第 28 章 | Linux（macOS：`netstat -an`、`lsof -i`） |
| `ss -tn state established '( sport = :PORT )'` | 連到某個 port 的連線 | 看有多少 client 連著 | 第 28、33 章 | Linux |
| `ss -tan state time-wait \| wc -l` | TIME_WAIT 數量 | `Address already in use`、ephemeral port 耗盡 | 第 28 章 | Linux |
| `ss -tan state close-wait` | 對方已關、我方還沒 `close` 的連線 | fd 洩漏、錯誤路徑漏了 `close` | 第 28、33 章 | Linux |
| `ss -s` | 各狀態的總數摘要 | 快速看整體連線狀況 | 第 28 章 | Linux |
| `ss -tanp` | 所有連線加上 process 與 fd | 事故現場收集 | 第 33 章 | Linux |
| `netstat` | `ss` 的前身 | 舊系統或 macOS | 第 28 章 | 通用（旗標不同） |
| `lsof -i :PORT` | 誰持有這個 port 的 socket | 子行程繼承了 listening socket、port 被佔住 | 第 21 章 | 通用 |
| `nc -v HOST PORT`、`printf 'STATS\n' \| nc HOST PORT` | 手動或用腳本送一段資料 | 測試自訂協定、管理 port | 第 28 章 | 通用（選項依版本不同） |
| `nc -l PORT` | 開一個臨時 server | 看 client 實際送了什麼 | 第 28 章 | 通用 |
| `printf 'GET / HTTP/1.1\r\nHost: x\r\n\r\n' \| nc localhost 8080` | 手寫原始 HTTP 請求 | 測試 server 的解析器 | 第 29 章 | 通用 |
| `sudo tcpdump -i any -nn 'tcp port PORT'` | 看握手、資料、FIN／RST | 訊息被拆成多個 segment、對方送 RST | 第 28、29 章 | 通用（macOS 用 `-i en0` 等實際介面名稱） |
| `sudo tcpdump -i any -nn 'tcp[tcpflags] & tcp-rst != 0'` | 只看 RST | client 偶爾收到 connection reset | 第 28 章 | 通用 |
| `curl -v URL -o /dev/null` | 完整的請求與回應 header | `Content-Length` 不符、狀態碼不對 | 第 29 章 | 通用 |
| `curl -sS -o /dev/null -w '%{http_code} %{time_connect} %{time_starttransfer} %{time_total}\n' URL` | 狀態碼與各階段時間 | 判斷慢在連線、等待還是傳輸 | 第 29 章 | 通用 |
| `curl --path-as-is 'URL/../../etc/passwd'` | 不讓 curl 整理 `..` | 測試 path traversal | 第 29 章 | 通用 |
| `curl -H "Cookie: ..." URL` | 送超長 header | 測試 header 大小限制與 431 | 第 29 章 | 通用 |
| `cat /proc/sys/net/ipv4/ip_local_port_range` | ephemeral port 範圍 | 估算短連線的速率上限 | 第 28 章 | Linux |

## B.9 並行

| 指令 | 用途 | 什麼時候用 | 出處 | 平台 |
|---|---|---|---|---|
| `clang -fsanitize=thread -g -O1 x.c` | TSan：找 data race；Linux 上也報告鎖順序相反 | 計數器偏低、偶發錯誤只在高併發出現；慢 5–15 倍 | 第 2、31、33 章 | 通用 |
| `gdb -p PID -batch -ex "thread apply all bt"` | 所有 thread 的 stack | 服務卡住、CPU 是 0，懷疑 deadlock | 第 30、31、33 章 | Linux（macOS：`lldb -p PID` 後 `bt all`） |
| `grep -n -B2 -A8 "pthread_mutex_lock\|__lll_lock_wait\|futex_wait" bt.txt` | 找出停在拿鎖的 thread | 分析上一列的輸出 | 第 31 章 | Linux（glibc） |
| `ps -L -o tid,stat,wchan:20,comm -p PID` | 每個 thread 的狀態與等待點 | thread 數暴增、找卡住的 thread | 第 30 章 | Linux（macOS：`ps -M`） |
| `ps -eLf \| wc -l` | 系統的 thread 總數 | `pthread_create` 回傳 `EAGAIN` | 第 21 章 | Linux |
| `top -H -p PID` | 以 thread 為單位看 CPU | 某個 thread 空轉 | 第 30、33 章 | Linux |
| `pidstat -w` | 每秒 context switch | 鎖競爭造成大量睡眠與喚醒 | 第 32、33 章 | Linux |
| `strace -c -f -p PID`（看 `futex` 次數） | 鎖競爭的間接證據 | 加 thread 吞吐量下降 | 第 32 章 | Linux |
| `perf c2c record`、`perf c2c report` | false sharing | per-thread 資料卻不會擴展 | 第 17、32 章 | Linux |
| `vmstat 1`（看 `r` 與 `cs`） | run queue 與 context switch | CPU-bound thread 數超過核心數 | 第 32 章 | Linux |
| `sysctl hw.cachelinesize` | cache line 大小 | 決定 `alignas` 的值，不要寫死 64 | 第 16、32 章 | macOS（Linux：`getconf -a \| grep -i LINESIZE`） |

## B.10 `/proc` 常用檔案

`/proc` 是 Linux kernel 用檔案介面提供的 process 與系統資訊，macOS 沒有；macOS 上對應的資訊分散在 `vmmap`、`lsof`、`ps` 與 `sysctl`。

| 路徑 | 看什麼 | 什麼時候用 | 出處 | macOS 對應 |
|---|---|---|---|---|
| `/proc/PID/maps` | VMA 清單：位址、權限（`r-xp`、`rw-p`、`r--s`）、offset、檔案 | 位址屬於哪個區域、載入了哪個 `.so` | 第 1、19、23、24 章 | `vmmap PID` |
| `/proc/PID/smaps` | 每個 VMA 的 RSS、PSS、dirty、swap | 細看某個區域 | 第 23、24、26 章 | `vmmap PID` |
| `/proc/PID/smaps_rollup` | 上面的總計，含 `RssAnon`、`RssFile`、`Private_Dirty` | RSS 上升時第一個看的檔案 | 第 23、24、26、33 章 | `vmmap -summary PID` |
| `/proc/PID/status` | `VmRSS`、`Threads`、`ctxt_switches`、`SigBlk`／`SigCgt` | 記憶體、thread 數、signal 狀態 | 第 20、22、33 章 | `ps`、`top` |
| `/proc/PID/stat` | 累計的 `minflt`、`majflt` 等 | 監控 page fault | 第 20、23 章 | `ps` |
| `/proc/PID/fd/` | 每個打開的 fd 指向什麼 | fd 洩漏（`ls /proc/PID/fd \| wc -l`）、pipe 等不到 EOF | 第 20、27、28、30、33 章 | `lsof -p PID` |
| `/proc/PID/exe` | 執行中的是哪個執行檔 | 部署後行為沒變，確認是不是新版 | 第 1 章 | `lsof -p PID` 的 `txt` 列 |
| `/proc/PID/environ` | 啟動時的環境變數 | 檢查服務有沒有被設了 `LD_LIBRARY_PATH` | 第 19 章 | 無直接對應 |
| `/proc/PID/task/` | 每個 thread 一個子目錄 | 逐 thread 檢查狀態 | 第 30 章 | `ps -M` |
| `/proc/PID/oom_score_adj` | OOM killer 的優先度調整 | 保護關鍵 process | 第 24 章 | 無直接對應 |
| `/proc/meminfo` | `MemAvailable`、`Cached`、`Committed_AS`、`CommitLimit` | 系統記憶體壓力、overcommit | 第 24 章 | `vm_stat` |
| `/proc/cpuinfo` | CPU 型號與指令集 flags | `SIGILL`、確認 `-march` 是否相容 | 第 12、20 章 | `sysctl hw` |
| `/proc/buddyinfo` | 實體頁的 buddy allocator 狀態 | 觀察碎片 | 第 25 章 | 無直接對應 |
| `/proc/sys/kernel/pid_max` | PID 上限 | `fork` 回傳 `EAGAIN` | 第 21 章 | `sysctl kern.maxproc` |
| `/proc/sys/kernel/randomize_va_space` | ASLR 等級（`2` 為完整） | 檢查系統防護 | 第 11 章 | 預設開啟 |
| `/proc/sys/net/ipv4/ip_local_port_range` | ephemeral port 範圍 | TIME_WAIT 造成 port 耗盡 | 第 28 章 | `sysctl net.inet.ip.portrange` |

## B.11 `ulimit` 與資源限制

`ulimit` 是 shell 的內建指令（它要改的是 shell 自己的資源限制，第 21 章），Linux 與 macOS 都有，設定只對這個 shell 與之後啟動的子行程有效。systemd 管理的服務要在 unit 檔裡設定，例如 `LimitCORE=infinity`、`LimitNOFILE=`（第 33 章）。

| 指令 | 限制什麼 | 什麼時候看 | 出處 |
|---|---|---|---|
| `ulimit -c unlimited` | core dump 大小（0 表示不產生） | 當機後沒有 core 可看 | 第 2、33 章 |
| `ulimit -n` | 每個 process 能開的 fd 數 | `EMFILE`、`accept: Too many open files` | 第 27、28、30、33 章 |
| `ulimit -s` | main thread 的 stack 上限（常見 8192 KiB）；glibc 也拿它當新 thread 的預設 stack | 遞迴過深的 segfault、VSZ 裡大量 8 MiB 區域 | 第 9、24、30 章 |
| `ulimit -u` | 使用者能建立的 process 數（`RLIMIT_NPROC`，Linux 上 thread 也算） | `fork`／`pthread_create` 回傳 `EAGAIN` | 第 21 章 |
| `ulimit -v` | 虛擬位址空間大小 | 刻意限制測試程式的記憶體 | 第 21 章 |

## B.12 從症狀找指令

最後把第 33 章的對照表濃縮成「第一個該打的指令」，方便在事故當下直接查。

| 症狀 | 第一步 | 接著用 | 章節 |
|---|---|---|---|
| `SIGSEGV`、`SIGBUS`、結束碼 139 | `dmesg`、`coredumpctl gdb`，然後 `bt` | ASan 版本重放輸入 | 9、11、23、26、33 |
| 當機點每次不同、在 `malloc`／`free` 裡 | `-fsanitize=address` 重新建置 | `valgrind` | 25、26 |
| 只在 `-O2` 出錯 | `-fsanitize=undefined` | 比較 `-O0` 與 `-O2` 的組合語言 | 4、5、26 |
| 部署後 `SIGILL` | gdb `x/i $pc` | `grep flags /proc/cpuinfo` | 12、20 |
| 啟動失敗、找不到 `.so` 或 glibc 版本 | `ldd`、`readelf -d` | `LD_DEBUG=libs`、`objdump -T` | 18、19 |
| 延遲上升、CPU 也上升 | `perf record -g` | `perf annotate` | 8、13、14 |
| 延遲上升、IPC 很低 | `perf stat -e LLC-load-misses,dTLB-load-misses` | `perf record -e L1-dcache-load-misses` | 15、16、17、23 |
| `sys` 時間很高 | `strace -c` | `strace -T -e trace=...` | 20、27 |
| RSS 持續上升 | `smaps_rollup`、`pmap -x` | `malloc_stats`、heaptrack、LSan | 24、25、26 |
| 被 OOM killer 殺掉 | `dmesg`、cgroup 的 `memory.current` | `/proc/meminfo` | 24 |
| zombie 越來越多 | `ps -eo pid,ppid,stat,comm` | `strace -f -e trace=%process` | 21 |
| `Too many open files` | `ls /proc/PID/fd \| wc -l`、`ulimit -n` | `lsof -p PID` | 27 |
| 連線卡住、CLOSE_WAIT 增加 | `ss -tan state close-wait` | `thread apply all bt`、`strace -e trace=read,close` | 27、28、29 |
| `Address already in use` | `ss -ltnp`、`ss -tan state time-wait` | 檢查 `SO_REUSEADDR` | 28 |
| 加 thread 沒變快 | `pidstat -w`、`perf top` | `perf c2c` | 32 |
| 程式停住、CPU 是 0 | `gdb -p PID -batch -ex "thread apply all bt"` | TSan 的 lock-order 報告 | 31 |
| 偶發錯誤、只在高併發出現 | TSan 版本壓測 | `wrk` 放大併發 | 31、32、33 |

## B.13 延伸閱讀

- [GCC 線上文件](https://gcc.gnu.org/onlinedocs/)：所有編譯旗標的完整說明。
- [GDB 使用手冊](https://sourceware.org/gdb/current/onlinedocs/gdb.html/)：中斷點、watchpoint、core dump 與多執行緒除錯。
- [GNU Binutils 文件](https://sourceware.org/binutils/docs/)：`objdump`、`readelf`、`nm`、`addr2line`、`ld`。
- [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html)、[ThreadSanitizer](https://clang.llvm.org/docs/ThreadSanitizer.html)、[UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)：三種 sanitizer 的選項與限制。
- [Linux man pages](https://man7.org/linux/man-pages/)：`strace(1)`、`perf(1)`、`ss(8)`、`proc(5)`、`ld.so(8)`。
