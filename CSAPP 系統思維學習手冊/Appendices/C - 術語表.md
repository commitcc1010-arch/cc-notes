---
title: 附錄 C　術語表
---

# 附錄 C　術語表

這份術語表收錄全書 34 章中重要的系統術語，依英文字母排序；數字開頭的放在「0–9」，正文沒有對應英文的概念放在最後的「中文術語」。每一條的定義都取自正文第一次解釋它的地方，只保留一句話的白話版本，細節與例子請回到「首次詳細說明」欄指出的章節。

「首次詳細說明」的寫法有兩種：只寫「第 N 章」表示該章第一次以粗體介紹並說明這個術語；寫成「第 1 章（詳見第 23 章）」表示它在前面的章節已經先出現並給了簡短說明，完整的機制要等到括號裡的章節才展開。全書譯名已統一，同一個概念只用一種中文說法；條目中的斜線用來分隔同一列裡並列的幾個相關術語（例如 kernel mode / user mode 或 miss rate / miss penalty）。

## 0–9

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| 2-bit saturating counter | 兩位元飽和計數器 | 每個分支一個 0–3 的計數器，跳了加一、沒跳減一，≥ 2 就預測會跳 | 第 13 章 |

## A

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| ABA problem | ABA 問題 | CAS 只比較值，值從 A 變 B 又變回 A 時察覺不到中間的變化 | 第 32 章 |
| ABI (application binary interface) | 應用程式二進位介面 | 規定編譯好的機器碼之間怎麼合作：參數放哪、struct 版面、符號名稱 | 第 9 章（詳見第 19 章） |
| abort | 中止 | 無法修復的硬體錯誤，不返回 | 第 20 章 |
| absorption | 吸收 | 大數加上很小的數時，小數被捨入掉、結果不變 | 第 6 章 |
| accept queue / backlog | 接受佇列／積壓上限 | kernel 中已完成握手、等程式 `accept` 的連線，以及其長度上限 | 第 28 章 |
| acquire / release | 取得／釋放語意 | release store 之前的讀寫不能移到它之後；acquire load 之後的讀寫不能移到它之前 | 第 32 章 |
| addend | 加數 | relocation 公式中的常數 A，例如 PC-relative 呼叫的 −4 | 第 19 章 |
| address | 位址 | 記憶體中每個 byte 的編號 | 第 1 章 |
| addressing mode | 定址模式 | 用 D(base, index, scale) 公式算出記憶體位址的寫法 | 第 7 章 |
| AddressSanitizer (ASan) | 位址檢查器 | 編譯器在每次記憶體存取前插入檢查、以 byte 等級抓越界與 UAF 的 sanitizer | 第 2 章（詳見第 26 章） |
| alignment | 對齊 | 資料的位址必須是它對齊要求（通常等於大小）的倍數 | 第 10 章 |
| ALU (arithmetic/logic unit) | 算術邏輯單元 | 做加減、位元運算與比較的電路 | 第 1 章 |
| AMAT (average memory access time) | 平均記憶體存取時間 | hit time + miss rate × miss penalty | 第 15 章 |
| Amdahl's law | 阿姆達爾定律 | 只加速程式的一部分時，整體加速比受沒有加速的部分限制 | 第 1 章（詳見第 14 章） |
| anonymous mapping | 匿名 mapping | 沒有對應檔案、內容一開始全為零的映射，heap 與 stack 都是 | 第 24 章 |
| AoS / SoA | 結構陣列／陣列結構 | 每筆紀錄一個 struct 排成陣列，或每個欄位各自是一個陣列 | 第 17 章 |
| API (application programming interface) | 應用程式介面 | 原始碼層級的約定：函式名稱、參數型別 | 第 19 章 |
| architectural state | 架構狀態 | 程式看得到的暫存器與記憶體內容 | 第 13 章 |
| Architecture Lab / Cache Lab / Performance Lab | 架構／快取／效能實驗 | 寫 Y86-64 程式並為處理器加新指令、寫 cache 模擬器並最佳化矩陣轉置、最佳化 convolution 或矩陣轉置等應用程式 kernel 函式的三個 Lab | 第 34 章 |
| archive (.a) | 封存檔 | 靜態函式庫的檔案格式 | 第 18 章 |
| arena allocator (region, bump allocator) | 區域配置器 | 請求開始時拿一大塊，配置只是把指標往前推，結束時一次丟掉 | 第 25 章 |
| argv / envp | 參數陣列／環境變數陣列 | 新程式啟動時放在 stack 頂端的命令列參數與環境變數 | 第 21 章 |
| arithmetic shift | 算術右移 | 右移時左邊補原本的最高位，主流編譯器對 signed 負數採用 | 第 3 章 |
| ARM64 (AArch64) | ARM 64 位元架構 | Apple Silicon 與許多伺服器使用的 64-bit RISC 指令集 | 第 7 章 |
| array decay | 陣列退化 | 陣列在多數運算式與函式參數中被轉成指向第一個元素的指標 | 第 2 章（詳見第 10 章） |
| ASCII | ASCII 編碼 | 把 0–127 對應到英文字母、數字與符號的字元編碼，每個字元一個 byte | 第 1 章 |
| ASLR (address space layout randomization) | 位址空間配置隨機化 | 每次載入時把程式、heap、stack、shared library 整塊放到隨機位置 | 第 1 章（詳見第 11 章） |
| assembler | 組譯器 | 把組合語言翻成機器碼、產生可重定位目的檔的工具 | 第 1 章 |
| assembly language | 組合語言 | 機器碼的文字版，每一行大致對應一條指令 | 第 1 章（詳見第 7 章） |
| async-signal-safe | 非同步信號安全 | 可以安全地在 signal handler 中呼叫的函式，例如 `write`、`_exit` | 第 22 章 |
| AT&T syntax / Intel syntax | AT&T 語法／Intel 語法 | 兩種 x86 組合語言寫法；AT&T 來源在前、目的在後，暫存器加 `%` | 第 7 章 |
| atomic operation | atomic 操作 | 不可分割、其他 thread 看不到做到一半狀態的操作，x86-64 上常是帶 `lock` 前綴的指令 | 第 32 章 |
| auto-vectorization | 自動向量化 | 編譯器自動把簡單迴圈改寫成 SIMD 指令 | 第 14 章 |

## B

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| backpressure | 背壓 | queue 滿時讓 producer 等待或拒絕，把壓力往上游傳 | 第 30 章 |
| bias | 偏移量 | exp 欄位存的是 E 加上的固定值：float 是 127，double 是 1023 | 第 6 章 |
| big endian | 大端序 | 把最高有效位元組放在最低位址的 byte order，也是網路位元組順序 | 第 3 章 |
| bijection | 雙射 | 位元串與值一一對應、可以來回轉換而不遺失資訊 | 第 4 章 |
| binary file | 二進位檔 | 文字檔以外的檔案，內容要依特定格式解讀 | 第 1 章 |
| binary semaphore | 二元號誌 | 初值為 1 的 semaphore，用來實現互斥 | 第 31 章 |
| bit | 位元 | 只能是 0 或 1 的最小資訊單位 | 第 1 章 |
| bit mask | 位元遮罩 | 指定要操作哪些位元的整數 | 第 3 章 |
| bit vector | 位元向量 | 用整數的第 i 位表示「元素 i 是否在集合裡」 | 第 3 章 |
| bitwise operation | 逐位元運算 | 結果的第 i 位只看運算元的第 i 位，彼此不影響、沒有進位 | 第 3 章 |
| block | 區塊 | 相鄰兩層儲存之間搬移資料的固定單位 | 第 15 章 |
| blocked set (signal mask) | 阻擋集合 | 目前被阻擋的 signal，可以送達但不會被接收，直到解除阻擋 | 第 22 章 |
| blocking (tiling) | 分塊 | 把大矩陣切成放得進 cache 的小塊，在小塊裡做完所有計算再換下一塊 | 第 17 章 |
| Boolean algebra | 布林代數 | 以 0、1 與 AND、OR、NOT、XOR 運算組成的代數，是數位電路的基礎 | 第 3 章 |
| boundary tag | 邊界標記 | 在每個 block 尾端也放一份 header，讓合併能找到前一塊 | 第 25 章 |
| branch misprediction penalty | 分支預測錯誤懲罰 | 猜錯分支時浪費的 cycle 數 | 第 13 章 |
| branch predictor | 分支預測器 | 根據分支過去的行為預測這次會不會跳的硬體 | 第 8 章（詳見第 13 章） |
| branchless code | 無分支程式碼 | 兩條路都算、再用不需預測的方式選一個，例如 `cmov` | 第 14 章 |
| brk / sbrk / program break | 程式斷點 | 標示 heap 結尾的位置；`sbrk(n)` 把它往高位址推 n bytes | 第 25 章 |
| bubble | 氣泡 | 自動插入、不改變任何狀態的空指令，隨管線流到最後 | 第 13 章 |
| buddy system | 夥伴系統 | 所有 block 大小都是 2 的冪，切割一分為二、只和夥伴合併 | 第 25 章 |
| buffer overflow | 越界寫入／緩衝區溢位 | 寫入超出緩衝區範圍，改掉旁邊的資料甚至 return address | 第 11 章 |
| __builtin_add_overflow / ckd_add | 溢位檢查函式 | GCC／Clang 內建函式與 C23 標準函式，回傳是否溢位並給出截斷後的結果 | 第 5 章 |
| bulkhead | 艙壁隔離 | 用分開的資源池隔離不同類型的工作，一類過載不拖垮另一類 | 第 30 章 |
| bus | 匯流排 | 在元件之間傳送位址、資料與控制訊號的一束平行電線 | 第 1 章（詳見第 15 章） |
| byte | 位元組 | 8 個位元，可表示 0 到 255 共 256 種值 | 第 1 章 |
| byte order (endianness) | 位元組順序 | 多 byte 數值的各個 byte 在記憶體中由低位址到高位址的排列方式 | 第 3 章 |
| byte stream | 位元組串流 | 只保證 bytes 依序到達、不保留每次 `write` 邊界的傳輸語意 | 第 28 章 |

## C

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| C string | C 字串 | 以值為 0 的 byte（`'\0'`，null terminator）標示結束的一串 `char` | 第 2 章 |
| C10K problem | C10K 問題 | 一台機器同時服務一萬條連線的挑戰 | 第 30 章 |
| cache | 快取記憶體 | 保存最近用過資料複本的小而快的記憶體 | 第 1 章（詳見第 16 章） |
| cache coherence protocol | 快取一致性協定 | 讓多個核心看到同一位址一致的值的硬體協定 | 第 16 章（詳見第 32 章） |
| cache hit | 命中 | 要找的資料已經在這一層 cache 裡 | 第 1 章（詳見第 15 章） |
| cache line | 快取行 | cache 每次從下一層搬上來的一整塊資料，x86-64 上是 64 bytes | 第 1 章（詳見第 16 章） |
| cache miss | 失誤 | 要找的資料不在這一層，必須去下一層拿 | 第 1 章（詳見第 15 章） |
| cache timing side channel | 快取時間旁路 | 利用 cache hit 與 miss 的時間差推測資料的手法 | 第 13 章 |
| Cachegrind | Cachegrind 模擬器 | Valgrind 的工具，模擬並統計每一行程式的 cache miss | 第 17 章 |
| call / ret | 呼叫／返回指令 | `call` push return address 並跳到目標；`ret` 從 stack pop 位址並跳回 | 第 9 章 |
| callee-saved register | 被呼叫者保存暫存器 | 函式若要使用，就必須在返回前還原原值的暫存器 | 第 7 章（詳見第 9 章） |
| caller-saved register | 呼叫者保存暫存器 | 呼叫別的函式之後值可能被改掉的暫存器，呼叫者要自己保存 | 第 7 章（詳見第 9 章） |
| calling convention | 呼叫慣例 | 參數與回傳值放在哪裡、哪些暫存器要保存的約定 | 第 7 章（詳見第 9 章） |
| canonical address | 標準形式位址 | x86-64 規定第 47 bit 以上必須全部相同的位址，位址空間因此切成 user 與 kernel 上下兩半 | 第 24 章 |
| capacity (functional unit) | 容量 | 能同時做某種運算的功能單元個數 | 第 14 章 |
| capacity miss | 容量失誤 | 正在使用的資料比 cache 大，怎麼放都放不下 | 第 15 章 |
| carry flag (CF) | 進位旗標 | 記錄無號意義下溢位（進位或借位）的條件碼 | 第 5 章（詳見第 8 章） |
| catastrophic cancellation | 相消 | 兩個非常接近的數相減，相同的有效位數抵銷，只剩下之前的捨入誤差 | 第 6 章 |
| CGI (Common Gateway Interface) | 通用閘道介面 | web server 把請求交給外部程式、再取回輸出的早期約定 | 第 29 章 |
| checker | 檢查器 | 專門驗證資料結構不變量的程式，讓錯誤在發生當下被抓到 | 第 34 章 |
| child process / parent process | 子行程／父行程 | fork 複製出來的 process，以及原本的 process | 第 21 章 |
| CISC | 複雜指令集 | 指令長度可變、指令可直接存取記憶體的 ISA 設計，例如 x86-64 | 第 7 章（詳見第 12 章） |
| client-server model | 主從式模型 | server 管理資源並等待請求，client 主動送出請求的架構 | 第 28 章 |
| clock | 時脈 | 週期性高低變化的訊號，決定儲存元件何時更新 | 第 12 章 |
| clocked register | 時脈暫存器 | 只在時脈上升緣（rising edge）才把輸入存進來的儲存元件 | 第 12 章 |
| CLOSE_WAIT | CLOSE_WAIT 狀態 | 對方已關閉、我方應用程式還沒 `close` 的狀態，長期堆積通常是程式漏關 | 第 28 章 |
| cmp / test | 比較／測試指令 | 只做減法或 AND 來設定條件碼、不保存結果的指令 | 第 8 章 |
| coalescing | 合併 | 把相鄰的 free block 合成一塊 | 第 25 章 |
| code injection | 程式碼注入 | 把機器碼放進輸入，再讓程式跳過去執行 | 第 34 章 |
| code motion | 程式碼移動 | 把每圈結果都一樣的計算移到迴圈外 | 第 14 章 |
| Coffman conditions | Coffman 條件 | deadlock 發生必須同時成立的四個條件，打破任一個即可避免 | 第 31 章 |
| cold miss (compulsory miss) | 冷失誤 | block 第一次被存取，cache 裡本來就不可能有 | 第 15 章 |
| combinational circuit | 組合電路 | 輸出只由目前的輸入決定、沒有記憶的電路 | 第 12 章 |
| COMMON symbol | COMMON 符號 | `-fcommon` 模式下沒有初值的全域變數，`nm` 顯示為 `C`，連結器對待方式類似 weak | 第 18 章 |
| compaction | 壓縮 | 移動存活物件、消除碎片；保守式 GC 做不到 | 第 26 章 |
| compare-and-swap (CAS) | 比較並交換 | 如果位址的值還是預期的 A 就換成 B，否則回報目前的值 | 第 32 章 |
| compilation | 編譯 | 把前處理後的 C 翻譯成組合語言（`.s`） | 第 1 章 |
| compiler driver | 編譯器驅動程式 | 本身不做翻譯，依序呼叫前處理器、編譯器、組譯器與連結器的程式，例如 `cc` | 第 1 章 |
| concurrency | 並行 | 多個活動在同一段時間內都在進行中，不一定在同一瞬間執行 | 第 1 章（詳見第 30 章） |
| concurrent flow | 並行流程 | 執行時間互相重疊的兩條邏輯控制流 | 第 20 章 |
| condition codes | 條件碼 | 記錄上一個運算結果是否為零、為負、有無溢位的旗標，是 `if` 與迴圈的基礎 | 第 7 章（詳見第 8 章） |
| condition variable | 條件變數 | 讓 thread 在 mutex 旁睡覺、等待「條件可能改變了」通知的同步工具 | 第 31 章 |
| conditional jump | 條件跳躍 | 依條件碼決定要不要跳的指令，例如 `jl`、`jb` | 第 8 章 |
| conditional move (cmov) | 條件搬移 | 條件成立才把來源搬到目的、不需要跳躍的指令 | 第 8 章 |
| conflict miss | 衝突失誤 | cache 還有空間，但放置規則讓幾個常用 block 搶同一個位置 | 第 15 章 |
| connect / bind / listen / accept | 連線相關系統呼叫 | client 主動連線；server 綁定位址、轉成被動等待、取出已完成的連線 | 第 28 章 |
| connection | 連線 | 由兩端「位址：port」唯一決定的 TCP 通道 | 第 28 章 |
| conservative GC | 保守式回收 | 只要一個值看起來像指向已配置 block 就當它是指標 | 第 26 章 |
| content / MIME type | 內容／媒體類型 | server 送出的資料，以及告訴 client 如何解讀它的類型標記 | 第 29 章 |
| Content-Length / chunked | 內容長度／分塊傳輸 | 標示 body 長度的兩種方式：事先寫明 bytes 數，或切成帶長度的 chunk | 第 29 章 |
| context | 上下文 | kernel 重新啟動一個 process 所需的全部狀態：暫存器、PC、page table 等 | 第 1 章（詳見第 20 章） |
| context switch | 上下文切換 | 保存目前 process 的 context、載入另一個 process 的 context 並把 CPU 交給它 | 第 1 章（詳見第 20 章） |
| contraction | 運算合併 | 編譯器把同一運算式中的 `a * b + c` 合併成 FMA，可能讓不同平台結果不同 | 第 6 章 |
| control flow | 控制流程 | CPU 依序執行的指令位址序列 | 第 20 章 |
| control hazard | 控制冒險 | 遇到分支或 `ret` 時不知道下一條指令在哪裡 | 第 13 章 |
| control logic | 控制邏輯 | 依 icode 決定各多工器選哪個值的電路 | 第 12 章 |
| controller / adapter | 控制器／介面卡 | 把 I/O 裝置接到 I/O bus 上的元件 | 第 1 章 |
| copy-on-write (COW) | 寫入時複製 | 先共用同一組實體頁並標成唯讀，某一方寫入時才複製那一頁 | 第 21 章（詳見第 24 章） |
| core | 核心 | CPU 晶片中能獨立執行指令的處理單元，通常有自己的 L1 cache | 第 1 章 |
| core dump | 核心傾印 | 當機那一刻的記憶體快照，之後可以用 gdb 打開分析 | 第 2 章 |
| CPE (cycles per element) | 每元素 cycle 數 | 迴圈處理每個元素平均花幾個 cycle，總時間約等於 CPE × n 加固定開銷 | 第 14 章 |
| CPI (cycles per instruction) | 每條指令平均 cycle 數 | 處理器效能分析常用指標，IPC 的倒數 | 第 13 章 |
| CPU | 中央處理器 | 執行指令的引擎 | 第 1 章 |
| CR3 | CR3 暫存器 | 存放目前 process 第一層 page table 實體位址的 x86-64 特權暫存器 | 第 20 章（詳見第 23 章） |
| critical path | 關鍵路徑 | 資料流圖中最長的依賴鏈，決定執行時間的下限 | 第 14 章 |
| critical section | 臨界區 | 存取共享資料、同一時間只能有一個 thread 執行的程式段 | 第 31 章 |

## D

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| dangling pointer | 懸置指標 | 指向已釋放記憶體的指標 | 第 26 章 |
| data hazard | 資料冒險 | 後面的指令要讀的暫存器，正被前面還在管線中的指令寫入 | 第 13 章 |
| Data Lab / Bomb Lab / Attack Lab | 資料／炸彈／攻擊實驗 | 只用少數位元運算子實作函式、逆向工程拆除炸彈程式、對有 buffer overflow 的程式做 code injection 與 ROP 的三個 Lab | 第 34 章 |
| data layout | 資料布局 | 資料在記憶體裡怎麼排列 | 第 17 章 |
| data model | 資料模型 | 規定 `int`、`long`、指標各佔幾位元的約定，例如 LP64、LLP64 | 第 3 章 |
| data race | 資料競爭 | 兩個 thread 未經同步存取同一位址且至少一個是寫入，在 C11 中是 UB | 第 31 章（詳見第 32 章） |
| data-flow graph | 資料流圖 | 以指令為節點、以「誰的結果被誰用到」為箭頭的圖 | 第 14 章 |
| DDR SDRAM | 雙倍資料率同步 DRAM | 跟時脈同步、在時脈上升與下降邊緣都傳資料的 DRAM | 第 15 章 |
| deadlock | 死結 | 一組 thread 都在等另一個持有的資源，誰也無法前進 | 第 31 章 |
| deadlock region | 死結區 | progress graph 中一旦進入就只能撞上禁區、無法前進的區域 | 第 31 章 |
| debugger | 除錯器 | 讓程式停在中途、查看變數、記憶體與呼叫堆疊的工具 | 第 2 章 |
| decimal type | 十進位浮點／定點型別 | 以十進位精確表示小數的型別，例如 `Decimal`、`BigDecimal`、`NUMERIC` | 第 6 章 |
| declaration | 宣告 | 告訴編譯器「有這個名字，型別長這樣」，不產生程式碼也不配置空間 | 第 2 章 |
| decode | 解碼 | 從暫存器檔讀出運算元 valA、valB 的階段 | 第 12 章 |
| default action | 預設動作 | process 沒有特別設定時 kernel 對某個 signal 的處理：終止、忽略、暫停等 | 第 22 章 |
| defense in depth | 縱深防禦 | 沒有一層防禦是完美的，但層層疊加後攻擊最可能的結果是被偵測並終止 | 第 11 章 |
| definition | 定義 | 真正產生程式碼或配置空間的那一處，每個名字只能有一個 | 第 2 章 |
| demand paging | 需求分頁 | 頁第一次被存取時才分配或讀入實體頁 | 第 23 章 |
| demand-zero page | 需要時才填零的頁 | 第一次存取才分配並清零的匿名頁 | 第 24 章 |
| denormalized (subnormal) | 非正規數 | exp 全為 0、M 為 0.frac 的浮點數，用來填補 0 附近的空洞 | 第 6 章 |
| dereference | 解參考 | 透過指標讀寫它指向的記憶體，也就是 `*p` | 第 26 章 |
| descriptor table | 描述符表 | 每個 process 一張、以 fd 為索引、每格指向 open file table 項目的表 | 第 27 章 |
| DIMM (memory module) | 記憶體模組 | 多顆 DRAM 晶片一起動作、一次提供 64 bits 的模組 | 第 15 章 |
| direct-mapped cache | 直接映射快取 | 每個 set 只有一條 line，一個 block 只有一個位置可以放 | 第 16 章 |
| directed graph (reachability graph) | 有向圖 | 把 heap block 當節點、指標當邊的圖，用來判斷誰是垃圾 | 第 26 章 |
| directive | 組譯器指示 | 以 `.` 開頭、給組譯器看而不是 CPU 執行的行，例如 `.text`、`.globl` | 第 7 章 |
| dirty bit | 髒位元 | 標示這條 line 被改過、尚未寫回下一層的位元 | 第 16 章 |
| disassemble | 反組譯 | 把目的檔或執行檔的機器碼解碼回組合語言文字 | 第 7 章 |
| dlopen | 執行期載入函式庫 | 程式執行中才打開 shared library 並取得其中符號，常用於 plugin | 第 19 章 |
| DMA (direct memory access) | 直接記憶體存取 | 裝置不經過 CPU、直接把資料寫進記憶體，搬完再通知 CPU | 第 1 章（詳見第 15 章） |
| DNS (Domain Name System) | 網域名稱系統 | 維護名稱與位址對照的分散式資料庫 | 第 28 章 |
| domain name | 網域名稱 | 人類可讀的主機名稱，例如 `photos.example.com` | 第 28 章 |
| double free | 重複釋放 | 對同一塊記憶體 `free` 兩次，可能讓 allocator 把同一塊交給兩個使用者 | 第 26 章 |
| DRAM | 動態隨機存取記憶體 | 每個 bit 用一個電容加一個電晶體存放、需要定期刷新的記憶體，用作主記憶體 | 第 1 章（詳見第 15 章） |
| dual-stack | 雙堆疊 | 同一台機器同時有 IPv4 與 IPv6 位址 | 第 28 章 |
| dup / dup2 | 複製描述符 | 讓另一個 fd 指向同一個 open file 項目，用來做 I/O 重導向 | 第 27 章 |
| durability | 持久性 | 資料在斷電或當機後仍然存在的保證 | 第 27 章 |
| dynamic linker (ld-linux.so) | 動態連結器 | 程式啟動時載入所需的 shared library 並完成動態重定位的程式 | 第 19 章 |
| dynamic linking | 動態連結 | 把連結延到載入或執行時才做，程式碼留在 shared library 裡 | 第 1 章（詳見第 19 章） |
| dynamic memory allocator | 動態記憶體配置器 | 在使用者空間管理 heap、實作 `malloc` 與 `free` 的程式碼 | 第 25 章 |
| dynamic relocation | 動態重定位 | 留到載入或執行時由 dynamic linker 完成的 relocation，例如 `R_X86_64_JUMP_SLOT` | 第 19 章 |

## E

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| ECC (error-correcting code) | 錯誤更正碼 | 多存檢查位元以偵測並修正單一 bit 錯誤的 DRAM 模組設計 | 第 15 章 |
| echo server | 回聲伺服器 | 把收到的資料原樣送回的 server | 第 28 章 |
| efficiency | 效率 | speedup 除以核心數，代表每個核心平均有多少時間在做有用的事 | 第 32 章 |
| EINTR | 被中斷的系統呼叫 | 阻塞中的 system call 被 signal 打斷時的錯誤碼 | 第 22 章 |
| ELF (Executable and Linkable Format) | 可執行與可連結格式 | Linux 使用的目的檔、執行檔與 shared library 格式 | 第 1 章（詳見第 18 章） |
| ELF header | ELF 標頭 | ELF 檔案開頭的結構，以 magic number `\x7fELF` 開始，記錄類型與各表的位置 | 第 18 章 |
| EOF (end of file) | 檔案結尾 | 已經沒有資料可讀這個條件，`read` 回傳 0；不是檔案裡的特殊字元 | 第 27 章 |
| errno | 錯誤碼變數 | system call 與函式庫失敗時存放錯誤原因的變數，成功時不保證被清除 | 第 20 章 |
| Ethernet / MAC address | 乙太網路／MAC 位址 | 常見的 LAN 技術，以及網路卡的 48-bit 硬體位址 | 第 28 章 |
| event | 事件 | 觸發 exception 的處理器狀態變化 | 第 20 章 |
| event loop | 事件迴圈 | 反覆等待就緒事件、依狀態做一小步再回去等的主迴圈 | 第 30 章 |
| event-driven | 事件驅動 | 不為每條連線開 thread，而是用事件迴圈處理所有 nonblocking socket | 第 29 章（詳見第 30 章） |
| exception | 例外 | 處理器狀態發生需要作業系統介入的變化，控制流程轉移到 exception handler | 第 13 章（詳見第 20 章） |
| exception handler | 例外處理程式 | 發生 exception 時 kernel 中被執行的那段程式 | 第 20 章 |
| exception number | 例外編號 | 每種 exception 的整數編號，用來在 exception table 中查 handler | 第 20 章 |
| exception table | 例外表 | 第 k 格放第 k 種 exception handler 位址的表，x86-64 稱為 IDT | 第 20 章 |
| exceptional control flow (ECF) | 例外控制流程 | 控制流程因系統狀態變化而突然轉向，涵蓋 exception、signal、nonlocal jump | 第 20 章 |
| executable object file | 可執行目的檔 | 連結器產生、可以直接被載入執行的目的檔 | 第 18 章（詳見第 19 章） |
| execute | 執行 | ALU 計算 valE、設定條件碼並判斷跳躍條件的階段 | 第 12 章 |
| execve | execve 系統呼叫 | 在目前 process 中載入並執行新程式，PID 不變，成功時不會回傳 | 第 21 章 |
| exit status | 結束狀態 | 程式結束時回報的數字，0 代表成功；父行程只看得到最低 8 bits。shell 中 `$?` 看到的具體數值（例如 139）稱為結束碼（exit code） | 第 2 章（詳見第 21 章） |
| explicit cast | 顯式轉換 | 程式中明確寫出的型別轉換，例如 `(unsigned)x` | 第 4 章 |
| explicit free list | 顯式空閒串列 | 把 free block 用雙向串列串起來，只需搜尋空閒的 block | 第 25 章 |
| explicitly / implicitly reentrant | 明確可重入／隱含可重入 | 參數全部傳值，或參數有指標但只要呼叫者傳入不共享的資料就可重入 | 第 32 章 |
| external fragmentation | 外部碎片 | free block 加起來夠大，但沒有任何一塊連續空間夠大 | 第 25 章 |
| external symbol | 外部符號 | 本檔參照、定義在別的檔案的符號 | 第 18 章 |

## F

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| false fragmentation | 假碎片 | 相鄰的小 free block 沒合併，加起來夠大卻用不上 | 第 25 章 |
| false sharing | 偽共享 | 兩個 thread 寫不同的變數，但變數在同一條 cache line，line 在核心之間來回搬 | 第 16 章（詳見第 32 章） |
| fault | 錯誤 | 可能可以修復的同步 exception，修好就重做目前指令，例如 page fault | 第 20 章 |
| fetch | 取指令 | 用 PC 讀指令記憶體、拆出各欄位並算出下一條指令位址 valP 的階段 | 第 12 章 |
| file | 檔案 | I/O 裝置的抽象，就是一串 bytes | 第 1 章（詳見第 27 章） |
| file descriptor (fd) | 檔案描述符 | `open` 回傳的小整數，之後所有操作都用它代表那個打開的檔案 | 第 27 章 |
| file position | 檔案位置 | 下一次讀寫從第幾個 byte 開始，也叫 offset | 第 27 章 |
| file-backed mapping | 檔案 mapping | 把普通檔案的某一段對到位址空間，內容來自 page cache | 第 24 章 |
| FIN / RST | 結束／重置封包 | 正常關閉連線方向，以及異常中止連線 | 第 28 章 |
| first fit / next fit / best fit | 首次適配／下次適配／最佳適配 | 從頭找第一個夠大的、從上次位置繼續找、挑夠大且最小的 | 第 25 章 |
| fixed-point | 定點數 | 規定小數點固定在某個位置的表示法，本質是「整數乘以 2^−k」 | 第 6 章 |
| flexible array member | 彈性陣列成員 | struct 最後一個不指定長度的陣列，讓 metadata 與資料放在同一塊配置裡 | 第 10 章 |
| floating-point number | 浮點數 | 以 (−1)^s × M × 2^E 表示實數的格式 | 第 6 章 |
| flush | 沖掉 | 預測錯誤時把管線中錯誤路徑上的指令換成 bubble | 第 13 章 |
| FMA (fused multiply-add) | 融合乘加 | 一次算出 a × b + c、中間乘積不捨入的指令 | 第 6 章 |
| forbidden region | 禁區 | progress graph 中 semaphore 不變量不允許進入的區域，包住 unsafe region | 第 31 章 |
| foreground / background | 前景／背景 | 終端機的 `Ctrl-C` 只送給前景 process group 的每一個成員 | 第 22 章 |
| fork | fork 系統呼叫 | 把呼叫者幾乎完整地複製一份，在父行程回傳子行程 PID、在子行程回傳 0 | 第 21 章 |
| _FORTIFY_SOURCE | 強化檢查巨集 | 讓 `memcpy`、`strcpy` 等函式在可得知目的地大小時改呼叫會檢查長度的版本 | 第 11 章 |
| forwarding (bypassing) | 轉送／旁路 | 把剛算出、還沒寫回的值直接送給需要它的後續指令 | 第 13 章 |
| fragmentation | 碎片化 | 記憶體沒有被使用卻無法拿來滿足請求的現象 | 第 25 章 |
| frame | 訊框 | LAN 上傳送的單位，header 寫著目的地 MAC 位址 | 第 28 章 |
| frame pointer (%rbp) | 框指標 | 在函式開頭固定指向 frame 基準點的暫存器，所有 frame 串成鏈結串列 | 第 9 章 |
| framing | 訊框化 | 在 byte stream 上標出每則訊息的邊界，例如分隔符號或長度前綴 | 第 28 章 |
| fsync | 強制寫入磁碟 | 等檔案的資料與 metadata 都寫到儲存裝置上才回傳的 system call | 第 27 章 |
| FTL (flash translation layer) | 快閃轉譯層 | SSD 韌體中把邏輯區塊對到實際 flash page 的對照層 | 第 15 章 |
| full adder | 全加器 | 處理一個 bit 的加法電路：輸入兩個 bit 與進位，輸出和與往上的進位 | 第 12 章 |
| fully associative cache | 全關聯快取 | 只有一個 set，block 可以放在任何一條 line | 第 16 章 |
| function pointer | 函式指標 | 存著函式位址的變數；呼叫它在機器層級就是間接跳躍 | 第 10 章 |
| futex (fast userspace mutex) | 快速使用者空間互斥 | 沒有競爭時只用一條 atomic 指令、真的要等才進 kernel 的機制 | 第 31 章 |
| fuzzing | 模糊測試 | 自動產生大量變形輸入、搭配 ASan 執行來找出越界等錯誤 | 第 11 章 |
| -fwrapv | 繞回選項 | 要求編譯器把 signed overflow 一律當成二補數繞回的編譯選項 | 第 5 章 |

## G

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| garbage collection (SSD) | 垃圾回收（SSD） | 把 block 中還有效的 page 搬走、再抹除整個 block | 第 15 章 |
| garbage collector (GC) | 垃圾回收器 | 找出不可能再被用到的記憶體並自動回收 | 第 26 章 |
| gdb / lldb | GNU 除錯器／LLVM 除錯器 | Linux 與 macOS 上的標準除錯器，概念相同、指令稍有不同 | 第 2 章 |
| general-purpose register | 通用暫存器 | x86-64 CPU 內 16 個 8-byte 的工作區，例如 `%rax`、`%rdi` | 第 7 章 |
| getaddrinfo / getnameinfo | 位址解析函式 | 把主機名稱與服務轉成 socket 位址結構，以及反向轉回字串 | 第 28 章 |
| global symbol | 全域符號 | 本檔定義、所有目的檔都能參照的符號：沒有 `static` 的函式與全域變數 | 第 18 章 |
| GOT (global offset table) | 全域位移表 | 資料段中每個外部符號一格的表，程式碼透過它取得真正的位址 | 第 19 章 |
| gradual underflow | 漸進式下溢 | 靠非正規數讓數線在 0 與最小正規數之間沒有斷層 | 第 6 章 |
| guard page | 保護頁 | stack 下方不可存取的頁，用超過時觸發 segfault 而不是踩到隔壁 | 第 9 章 |
| guarded-do / jump-to-middle | 守衛式 do／跳到中間 | 編譯器把 while 迴圈翻成組合語言的兩種形狀 | 第 8 章 |
| Gustafson's law | 古斯塔夫森定律 | 核心變多時通常是在同樣時間內做更大的工作，可擴展性比 Amdahl 樂觀 | 第 32 章 |

## H

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| half-close | 半關閉 | 用 `shutdown(fd, SHUT_WR)` 只關閉自己的寫入方向，仍可繼續讀 | 第 28 章 |
| happens-before | 先發生於 | 由同步操作建立的先後關係；沒有這個關係的衝突存取就是 data race | 第 31 章（詳見第 32 章） |
| hazard | 冒險、危障 | 管線中相鄰指令互相依賴，使下一條指令不能在下個 cycle 正確執行 | 第 13 章 |
| HCL (hardware control language) | 硬體控制語言 | CS:APP 用來描述控制邏輯的簡單語言 | 第 12 章 |
| HDD (hard disk drive) | 傳統硬碟 | 把資料存在旋轉磁性碟片上的儲存裝置 | 第 15 章 |
| head-of-line blocking | 隊頭阻塞 | 前面的請求沒完成，後面的請求只能等 | 第 29 章 |
| header / footer | 標頭／標尾 | block 開頭記錄大小與狀態的 word，以及尾端的副本 | 第 25 章 |
| header file (.h) | 標頭檔 | 放宣告、讓多個 `.c` 用 `#include` 共用的檔案 | 第 2 章 |
| header guard | 標頭檔防護 | 標頭檔開頭 `#ifndef`／`#define` 與結尾 `#endif`，防止同一份內容被重複引入 | 第 2 章 |
| heap | heap（動態配置區） | 位址空間中用來在執行期間配置記憶體的區域 | 第 1 章（詳見第 25 章） |
| heap checker | heap 一致性檢查器 | 走訪整個 heap 檢查所有不變量的除錯函式 | 第 25 章 |
| Heartbleed | Heartbleed 漏洞 | 2014 年 OpenSSL 依對方宣稱的長度回傳資料而造成的越界讀取漏洞 | 第 11 章 |
| hexadecimal (hex) | 十六進位 | 每個數字正好對應 4 個位元、兩個數字正好一個 byte 的表示法 | 第 3 章 |
| Host header | Host 標頭 | 告訴 server 這個請求要找哪個網站，讓一個 IP 服務多個網域 | 第 29 章 |
| HTTP (Hypertext Transfer Protocol) | 超文本傳輸協定 | 建立在 TCP 上的請求／回應協定，HTTP/1.x 是文字協定 | 第 29 章 |
| HTTP request smuggling | 請求走私 | 利用前後端對請求邊界解讀不同，夾帶第二個請求的攻擊 | 第 29 章 |
| HTTP/2 / HTTP/3 (QUIC) | HTTP/2／HTTP/3 | 二進位格式、在一條連線上交錯多個請求；HTTP/3 改用建立在 UDP 上的 QUIC | 第 29 章 |
| huge page | 大頁 | 2 MiB 等較大的 page，讓同樣的 TLB entry 涵蓋更多記憶體 | 第 23 章 |

## I

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| i-cache / d-cache / unified cache | 指令快取／資料快取／統一快取 | L1 分成只存指令與只存資料的兩個 cache；L2 以下通常兩者共用 | 第 16 章 |
| I/O device | 輸入輸出裝置 | 電腦與外界的連接，例如鍵盤、螢幕、磁碟、網路卡 | 第 1 章 |
| I/O multiplexing | I/O 多工 | 只有一條控制流，自己在多個連線之間切換的並行模型 | 第 30 章 |
| I/O redirection | I/O 重導向 | 把 stdin、stdout 改接到檔案或 pipe，shell 用 `dup2` 實作 | 第 27 章 |
| icode / ifun | 指令類別／功能碼 | Y86-64 指令第一個 byte 的高 4 bits 與低 4 bits | 第 12 章 |
| idempotent | 冪等 | 做一次和做很多次的效果相同 | 第 29 章 |
| IEEE 754 | IEEE 754 標準 | 規定浮點數格式、特殊值與捨入規則的標準 | 第 6 章 |
| immediate | 立即數 | 寫死在指令裡的常數，AT&T 語法以 `$` 開頭 | 第 7 章 |
| immediate / deferred coalescing | 立即合併／延遲合併 | 每次 `free` 都合併，或等到找不到空位時才一次合併 | 第 25 章 |
| implementation-defined behavior | 由實作定義的行為 | 標準不規定結果、但要求實作明確定義並記載的行為，不同於 UB | 第 4 章 |
| implicit conversion | 隱式轉換 | 編譯器依規則自動做的型別轉換，發生在賦值、運算與傳參時 | 第 4 章 |
| implicit free list | 隱式空閒串列 | 靠 header 中的大小走遍所有 block 來找 free block | 第 25 章 |
| implied leading 1 | 隱藏位元 | 正規數 M 開頭的 1 不必存，等於免費多一位精度 | 第 6 章 |
| inclusive / exclusive cache | 包含式／互斥式快取 | L3 是否保證包含 L1、L2 的所有內容 | 第 16 章 |
| indirect jump | 間接跳躍 | 目標位址在暫存器或記憶體裡、執行時才知道的跳躍 | 第 8 章 |
| infinity (∞) | 無限大 | exp 全為 1、frac 為 0 的特殊值，表示溢位的結果 | 第 6 章 |
| inode | inode | 檔案系統中存放檔案 metadata 與資料位置的結構 | 第 27 章 |
| instruction | 指令 | CPU 執行的一件小事，例如加法、讀記憶體、條件跳躍 | 第 7 章 |
| instruction encoding | 指令編碼 | 每條指令具體由哪幾個 byte 組成 | 第 12 章 |
| instruction scheduling | 指令排程 | 把 load 往前移、在依賴之間塞入不相關指令，以填滿等待時間 | 第 13 章 |
| instruction-level parallelism | 指令層級平行 | 單一 thread 內，硬體同時處理多條指令 | 第 1 章（詳見第 13 章） |
| integer promotion | 整數提升 | 比 `int` 窄的型別在運算前一律先轉成 `int` | 第 4 章 |
| internal fragmentation | 內部碎片 | block 比 payload 大，多出來的部分沒人用 | 第 25 章 |
| internet / Internet | 互連網路／網際網路 | 小寫泛指互連的網路；大寫指全球使用 TCP/IP 的那一個 | 第 28 章 |
| interrupt | 中斷 | 由處理器外部 I/O 裝置發出、與目前指令無關的非同步例外 | 第 13 章（詳見第 20 章） |
| invalid opcode | 非法指令 | CPU 讀到不認得的指令編碼時觸發的 exception，kernel 轉成 `SIGILL` | 第 12 章 |
| invariant | 不變量 | 無論執行到哪一步都必須成立的條件 | 第 31 章 |
| IP (Internet Protocol) | 網際網路協定 | 提供主機到主機、盡力而為封包傳送的協定 | 第 28 章 |
| IPC (instructions per cycle) | 每 cycle 完成指令數 | 處理器效能指標，CPI 的倒數 | 第 12 章（詳見第 13 章） |
| IPv4 address / dotted-decimal | IPv4 位址／點分十進位 | 32-bit 無號整數，人類寫成以點分隔的 4 個 0–255 | 第 28 章 |
| IPv6 | IPv6 | 128-bit 位址的 IP 版本，寫成 8 組十六進位 | 第 28 章 |
| ISA (instruction set architecture) | 指令集架構 | 軟體與硬體之間的合約：規定有哪些指令、暫存器與它們的語意 | 第 7 章（詳見第 12 章） |
| issue time | 發射間隔 | 同一個功能單元連續兩次開始某種運算至少要隔幾個 cycle | 第 14 章 |
| iterative server | 迭代式伺服器 | 一次只服務一個 client 的 server | 第 30 章 |

## J

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| job control | 工作控制 | shell 用 process group 與 signal 管理前景、背景工作的機制 | 第 21 章（詳見第 22 章） |
| joinable / detached | 可被等待／分離 | 結束後資源留到被 join，或結束時自動回收 | 第 30 章 |
| jump instruction | 跳躍指令 | 把 `%rip` 改成別的位址的指令 | 第 8 章 |
| jump table | 跳躍表 | 存放各 case 程式碼位址的陣列；`switch` 用值當索引查表再間接跳躍 | 第 8 章 |

## K

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| kernel | kernel（作業系統核心） | 作業系統中具有特權、常駐記憶體的部分；本書保留英文，「核心」只用來指 CPU core | 第 1 章（詳見第 20 章） |
| kernel mode / user mode | kernel 模式／使用者模式 | 能否執行特權指令、存取 kernel 記憶體的兩種執行模式 | 第 20 章 |
| KPTI | kernel page table 隔離 | 讓 user mode 不映射 kernel 頁以緩解 Meltdown，代價是 system call 要切換 page table | 第 13 章 |

## L

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Lab | 實作作業 | CS:APP 的一組小而完整的系統問題，附起始程式與自動評分工具 | 第 34 章 |
| lab notebook | 實驗筆記 | 每次實驗以固定格式記錄「改了什麼」與「知道了什麼」 | 第 34 章 |
| label | 標籤 | 組合語言中代表下一條指令位址的名字 | 第 7 章 |
| LAN (local area network) | 區域網路 | 例如一棟辦公室裡用 Ethernet 連起來的機器 | 第 28 章 |
| latency | 延遲 | 一件工作從開始到完成要多久 | 第 13 章 |
| latency bound | 延遲界限 | 運算一個等一個時 CPE 不可能低於運算的 latency | 第 14 章 |
| lazy binding | 延遲綁定 | 等到函式第一次被呼叫時才解析它的位址並寫回 GOT | 第 19 章 |
| LD_PRELOAD | 預先載入變數 | 指定優先載入的 shared library，用來在不重新編譯的情況下攔截函式 | 第 19 章 |
| ldd | 相依函式庫列表工具 | 列出執行檔需要哪些 shared library 以及實際會載入哪一份 | 第 1 章（詳見第 19 章） |
| lea (load effective address) | 載入有效位址 | 只計算位址、不讀記憶體也不改條件碼的指令，常被拿來做算術 | 第 7 章 |
| leaf function | 葉函式 | 不再呼叫其他函式的函式 | 第 9 章 |
| leaks (macOS) | macOS 洩漏偵測工具 | macOS 內建、不需重新編譯的 leak 偵測工具 | 第 26 章 |
| LeakSanitizer (LSan) | 洩漏檢查器 | 程式結束時從 root 出發掃描、回報找不到指標的 heap block | 第 26 章 |
| level-triggered / edge-triggered | 水平觸發／邊緣觸發 | 只要 fd 還有資料就一直回報，或只在狀態變化時通知一次 | 第 30 章 |
| library interpositioning | 函式庫插入 | 讓程式對某函式的呼叫先經過你寫的包裝函式 | 第 19 章 |
| line | 快取行 | cache 裡的一個容器：valid bit、tag 加上一個 block | 第 16 章 |
| line buffered / fully buffered | 行緩衝／全緩衝 | stdout 接終端機時遇到換行就寫出；接檔案或 pipe 時要等緩衝區滿 | 第 21 章 |
| link order | 連結順序 | 連結器從左到右只掃描一次輸入，函式庫要放在用到它的目的檔後面 | 第 18 章 |
| linkage | 連結的可見範圍 | 符號能被哪些檔案看到；`static` 讓它變成只有本檔可見 | 第 18 章 |
| linker | 連結器 | 把多個目的檔與函式庫合併成執行檔，負責符號解析與重定位 | 第 1 章（詳見第 18 章） |
| linking | 連結 | 把多個目的檔與函式庫合併成可執行檔的階段 | 第 18 章 |
| listening socket / connected socket | 監聽 socket／已連線 socket | server 用來等待連線的 socket，以及 `accept` 回傳、代表一條連線的新 socket | 第 28 章 |
| little endian | 小端序 | 把最低有效位元組放在最低位址的 byte order，x86-64 與 ARM64 都採用 | 第 2 章（詳見第 3 章） |
| Little's law | 利特爾法則 | 穩定系統中同時在系統裡的工作數 L = 到達率 λ × 平均停留時間 W | 第 30 章 |
| load | 載入 | 從記憶體把資料讀進暫存器的動作 | 第 1 章 |
| load interlock | 載入互鎖 | 遇到 load-use hazard 時停頓一個 cycle 再 forwarding 的機制 | 第 13 章 |
| load-use hazard | 載入使用冒險 | 下一條指令立刻要用 load 讀出的值，forwarding 也來不及 | 第 13 章 |
| loader | 載入器 | 依 program header 把執行檔映射進記憶體並跳到進入點的機制 | 第 19 章 |
| local miss rate | 區域失誤率 | 在到達這一層的存取中 miss 的比例 | 第 16 章 |
| local symbol | 區域符號 | 只有本檔能用的符號：加了 `static` 的函式與變數；不是 local 變數 | 第 18 章 |
| locality | 區域性 | 程式傾向存取最近用過的資料或其附近的資料 | 第 1 章（詳見第 15 章） |
| lock-and-copy | 加鎖並複製 | 用 mutex 包住呼叫 unsafe 函式並把結果複製到自己的 buffer | 第 32 章 |
| lock-free | 無鎖 | 不用 mutex、只用 atomic 操作，保證任何時刻至少一個 thread 能完成操作 | 第 32 章 |
| logic gate | 邏輯閘 | 最小的組合電路元件，例如 AND、OR、NOT | 第 12 章 |
| logical block | 邏輯區塊 | 磁碟對外呈現的區塊編號，由控制器轉成實際位置 | 第 15 章 |
| logical control flow | 邏輯控制流 | 一個 process 單獨看到的 PC 值序列，彷彿獨佔 CPU | 第 20 章（詳見第 30 章） |
| logical leak | 邏輯 leak | 物件仍被指著、卻永遠不會再用到，任何工具都抓不到 | 第 26 章 |
| logical operation | 邏輯運算 | `&&`、`\|\|`、`!`：把非零當真、結果只有 0 或 1，而且會短路 | 第 3 章 |
| logical shift | 邏輯右移 | 右移時左邊補 0，unsigned 一律如此 | 第 3 章 |
| loop unrolling | 迴圈展開 | 把迴圈主體複製 k 次、每圈處理 k 個元素，減少迴圈開銷 | 第 14 章 |
| loop-carried dependency | 跨迭代依賴 | 下一圈要用到上一圈結果的依賴 | 第 14 章 |
| loopback | 回送位址 | `127.0.0.1` 或 `::1`，封包不會離開這台機器 | 第 28 章 |
| lost update | 遺失更新 | 兩個 thread 都讀了舊值再寫回，其中一次更新消失 | 第 31 章 |
| lost wakeup | 遺失喚醒 | 通知剛好發生在「檢查條件」與「開始睡覺」之間，於是永遠睡下去 | 第 22 章（詳見第 31 章） |
| LP64 | LP64 資料模型 | `long` 與指標都是 64 bits 的資料模型，64-bit Linux 與 macOS 都採用 | 第 2 章（詳見第 3 章） |
| LRU (least recently used) | 最近最少使用 | 踢掉最久沒用的那一個，賭的是 temporal locality | 第 15 章 |
| ltrace | 函式庫呼叫追蹤工具 | 在 PLT 項目上設中斷點、追蹤 library 函式呼叫的工具 | 第 19 章 |

## M

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Mach-O | Mach-O 格式 | macOS 使用的目的檔與執行檔格式 | 第 1 章 |
| machine code | 機器碼 | 依指令集規格編碼的位元組串，每幾個 byte 代表一條指令 | 第 1 章（詳見第 7 章） |
| madvise | 存取提示 | 告訴 kernel 存取模式或歸還頁，例如 `MADV_SEQUENTIAL`、`MADV_DONTNEED` | 第 24 章 |
| main memory | 主記憶體 | 由 DRAM 組成、存放執行中程式指令與資料的巨大 byte 陣列 | 第 1 章 |
| malloc / free | 動態配置／釋放 | 向 allocator 要一塊 heap 記憶體與歸還它；`malloc` 不初始化，`calloc` 會清成 0 | 第 2 章（詳見第 25 章） |
| Malloc Lab | 配置器實驗 | 實作自己的 `malloc`、`free`、`realloc`，以 utilization 與 throughput 評分 | 第 25 章（詳見第 34 章） |
| man page | 手冊頁 | Unix 系統內建的指令、system call 與函式庫函式文件，分成多個 section | 第 2 章 |
| -march=native | 本機指令集選項 | 讓編譯器使用 build 機器支援的所有指令，部署到較舊機器可能 `SIGILL` | 第 12 章（詳見第 14 章） |
| mark-and-sweep | 標記－清除 | 先從 root 標記走得到的 block，再掃過 heap 釋放沒有標記的 | 第 26 章 |
| Meltdown | Meltdown 漏洞 | 部分處理器在權限檢查前就把 kernel 資料交給推測執行的指令所造成的漏洞 | 第 13 章 |
| memory aliasing | 記憶體別名 | 兩個指標可能指向同一塊記憶體 | 第 14 章 |
| memory hierarchy | 記憶體階層 | 由快而小到慢而大疊起的儲存層次，每一層是下一層的快取 | 第 1 章（詳見第 15 章） |
| memory leak | 記憶體洩漏 | 不再需要卻沒有釋放、且已沒辦法釋放的記憶體 | 第 26 章 |
| memory mapping | 記憶體映射 | 把一段虛擬位址空間關聯到一個物件（檔案或匿名記憶體）的機制 | 第 24 章 |
| memory model | 記憶體模型 | 語言規定的多執行緒記憶體語意：沒有 data race 就保證循序一致 | 第 32 章 |
| memory mountain | 記憶體山 | 以 working set 大小與 stride 為兩軸、讀取吞吐量為高度的圖 | 第 17 章 |
| memory order | 記憶體順序 | atomic 操作對周圍其他記憶體操作提供多少順序保證 | 第 32 章 |
| memory stage | 存取記憶體 | 讀寫資料記憶體、產生 valM 的階段 | 第 12 章 |
| memory wall | 記憶體牆 | CPU 與 DRAM 速度差距持續擴大的現象，是記憶體階層存在的理由 | 第 15 章 |
| memory-safe language | 記憶體安全語言 | 在執行時或編譯時保證存取不越界的語言，例如 Rust、Go、Java | 第 11 章 |
| MESI | MESI 協定 | 每條 line 處於 Modified、Exclusive、Shared、Invalid 四種狀態之一的一致性協定 | 第 16 章（詳見第 32 章） |
| metadata | 中繼資料 | 檔案的大小、類型、權限、擁有者、修改時間等，用 `stat` 取得 | 第 27 章 |
| method | 方法 | 說明請求要做什麼，例如 GET、POST | 第 29 章 |
| microarchitectural state | 微架構狀態 | cache 內容、預測器學到的歷史等程式看不到、但可被量測時間間接讀出的狀態 | 第 13 章 |
| microarchitecture | 微架構 | ISA 的具體硬體實作，例如 pipeline 級數、cache 大小、分支預測器設計 | 第 7 章 |
| microarchitecture level (x86-64-v2/v3/v4) | 微架構等級 | 用一個名字說清楚 binary 需要哪些指令擴充的等級 | 第 12 章 |
| minor fault / major fault | 輕微缺頁／嚴重缺頁 | 處理時不需要讀磁碟，以及需要從檔案或 swap 讀入 | 第 23 章 |
| miss rate / miss penalty | 失誤率／失誤代價 | 存取中 miss 的比例，以及每次 miss 要多花的時間 | 第 15 章 |
| mm_struct | 記憶體描述子 | Linux kernel 描述一個 process 位址空間的結構，指向 page table 與 VMA 串列 | 第 24 章 |
| mmap / munmap | 記憶體映射系統呼叫 | 建立與移除一段記憶體映射 | 第 23 章（詳見第 24 章） |
| mmap threshold | mmap 門檻 | glibc 中大於此大小的配置直接用 `mmap` 取得獨立區域，預設 128 KiB | 第 25 章 |
| MMU (memory management unit) | 記憶體管理單元 | CPU 晶片上負責把虛擬位址翻譯成實體位址的硬體 | 第 23 章 |
| mode bit | 模式位元 | 處理器中區分 kernel mode 與 user mode 的位元 | 第 20 章 |
| modular arithmetic | 模運算 | 丟掉第 w 位以上的進位，等於除以 2^w 取餘數；unsigned 運算就是如此 | 第 5 章 |
| mprotect | 修改映射權限 | 改變一段已映射區域的讀寫執行權限 | 第 24 章 |
| MSS (maximum segment size) | 最大分段大小 | 每個 TCP segment 能攜帶的最大 payload | 第 28 章 |
| msync | 映射同步 | 把 `MAP_SHARED` 區域改過的頁寫回檔案並等待完成 | 第 24 章 |
| multi-level page table | 多層 page table | 用「目錄的目錄」切分 VPN，沒用到的區域不必有下層表；x86-64 用四層 | 第 23 章 |
| multiple accumulators | 多個累加器 | 把元素分組累加到不同變數，最後再合併，拆開關鍵路徑 | 第 14 章 |
| multiple definition | 重複定義 | 同一個強符號在多個目的檔中都有定義的連結錯誤 | 第 18 章 |
| multiplexor (MUX) | 多工器 | 依控制訊號從幾個輸入中選一個送到輸出的電路 | 第 12 章 |
| mutex | 互斥鎖 | 由 lock 它的 thread 擁有、只能由同一 thread unlock 的鎖 | 第 31 章 |
| mutex lock ordering rule | 鎖順序規則 | 所有 thread 依同一個全域順序取得多把鎖，等待關係就不會形成環 | 第 31 章 |
| mutual exclusion | 互斥 | 同一時間最多一個 thread 在 critical section 裡 | 第 31 章 |

## N

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| name mangling | 名稱修飾 | C++ 編譯器把命名空間與參數型別編進符號名稱 | 第 18 章 |
| NaN (not a number) | 非數 | exp 全為 1、frac 不為 0 的特殊值，與任何值比較都不相等，包括它自己 | 第 6 章 |
| NAND flash | 快閃記憶體 | page 寫過不能直接覆寫、要先抹除整個 block，且抹除次數有限的非揮發性記憶體 | 第 15 章 |
| nc / tcpdump / ss | 網路除錯工具 | 萬用的 client／server、直接看封包、列出 socket 與佇列狀態的工具 | 第 28 章 |
| negative overflow | 負溢位 | 兩個負數相加低於 TMin，截斷後變成正數或零 | 第 5 章 |
| network byte order | 網路位元組順序 | 網路協定規定的 byte order，也就是 big endian | 第 3 章（詳見第 28 章） |
| nm | 符號列表工具 | 列出目的檔符號表的工具：`T` 表示有定義，`U` 表示未定義 | 第 1 章（詳見第 18 章） |
| non-temporal store | 非暫時性寫入 | 繞過 cache、避免污染 cache 的寫入指令，例如 x86-64 的 `movnt` 系列 | 第 16 章 |
| nonblocking I/O | 非阻塞 I/O | 資料還沒準備好時立刻回傳 `EAGAIN`，而不是睡著等待 | 第 30 章 |
| nonlocal jump (setjmp / longjmp) | 非區域跳躍 | 從深層函式直接跳回外層函式、跳過中間所有 return 的機制 | 第 22 章 |
| nonvolatile memory | 非揮發性記憶體 | 斷電後仍保存資料的記憶體，歷史上稱 ROM | 第 15 章 |
| normalized value | 正規數 | exp 不全為 0 也不全為 1、M 為 1.frac 的浮點數 | 第 6 章 |
| NULL | 空指標 | 保證不指向任何有效物件的特殊指標值 | 第 2 章 |
| NX (no-execute, DEP) | 不可執行位元 | PTE 中標記「這一頁不能執行」的權限位，讓 stack 上注入的程式碼無法執行 | 第 11 章（詳見第 23 章） |

## O

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| objdump | 反組譯工具 | 把目的檔或執行檔的機器碼反組譯、列出 section 與 relocation 的工具 | 第 1 章（詳見第 7 章） |
| object file | 目的檔 | 存放機器碼與資料的檔案，分成可重定位、可執行、共享三種 | 第 18 章 |
| off-by-one | 差一錯誤 | 邊界多算或少算一個，例如 `i <= n` 或忘了 `'\0'` | 第 26 章 |
| offset | 位移 | 欄位相對 struct 起點的距離，在編譯期決定 | 第 10 章 |
| ones' complement | 一補數 | 把正數每一位翻轉得到負數的編碼，同樣有兩個 0 | 第 4 章 |
| OOM killer (out-of-memory killer) | 記憶體耗盡殺手 | 記憶體真的不夠時，kernel 挑一個 process 殺掉來換回記憶體 | 第 24 章 |
| open file table | 打開檔案表 | 所有 process 共用；每次 `open` 新增一項，記錄 file position 與 reference count | 第 27 章 |
| open_clientfd / open_listenfd | 連線輔助函式 | CS:APP 的輔助函式：回傳已連上 server 的 fd，或已在 listen 的 fd | 第 28 章 |
| operand | 運算元 | 指令要處理的資料來源或結果去處：立即數、暫存器或記憶體 | 第 7 章 |
| operating system (OS) | 作業系統 | 夾在應用程式與硬體之間，保護硬體並提供簡單一致介面的軟體 | 第 1 章 |
| optimization blocker | 最佳化障礙 | 讓編譯器不敢最佳化的程式特徵，最常見的是 aliasing 與函式副作用 | 第 14 章 |
| oracle | 參考答案 | 慢但顯然正確的實作，拿來和要驗證的版本逐一比對 | 第 34 章 |
| orphan | 孤兒行程 | 父行程先結束的 process，會被過繼給 init 或 subreaper | 第 21 章 |
| out-of-bounds access | 越界存取 | 讀寫了陣列範圍之外的記憶體 | 第 11 章 |
| out-of-order execution | 亂序執行 | 運算元準備好就先執行，不必等前面不相關的指令 | 第 1 章（詳見第 13 章） |
| over-read | 越界讀取 | 讀出陣列之外的資料，可能把不該給人看的內容送出去，例如 Heartbleed | 第 11 章 |
| overcommit | 記憶體超額承諾 | kernel 允許配置的虛擬記憶體超過實際能提供的量 | 第 24 章 |
| overflow | 溢位 | 運算的真實結果超出型別能表示的範圍 | 第 5 章 |
| overflow flag (OF) | 溢位旗標 | 記錄有號（二補數）意義下溢位的條件碼 | 第 5 章（詳見第 8 章） |
| oversubscription | 超額訂閱 | 可執行的 thread 遠多於核心數，造成大量 context switch | 第 32 章 |
| ownership | 所有權 | 「誰負責釋放這塊記憶體」的約定，C 不會幫你檢查 | 第 2 章（詳見第 26 章） |

## P

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| P / V operation | P／V 操作 | P 在 s > 0 時減 1，否則等待；V 把 s 加 1 並叫醒一個等待者 | 第 31 章 |
| packet (datagram) | 封包 | 一個 header 加上資料的傳送單位 | 第 28 章 |
| padding | 填充 | 編譯器為了對齊，在欄位之間或 struct 尾端插入的空白 bytes | 第 2 章（詳見第 10 章） |
| page | 頁 | 虛擬記憶體管理的固定大小單位，x86-64 Linux 是 4 KiB，Apple Silicon macOS 是 16 KiB | 第 23 章 |
| page cache | 頁快取 | kernel 用空閒記憶體快取檔案內容的地方，`read`、`write`、`mmap` 共用 | 第 24 章 |
| page fault | 缺頁例外 | 虛擬頁不在實體記憶體或權限不符，硬體觸發 exception 交給作業系統處理 | 第 23 章 |
| page hit | 頁命中 | PTE 有效且權限允許，直接拿到 PPN | 第 23 章 |
| page table | 頁表 | 每個 process 一張、記錄每個虛擬頁對到哪個實體頁與權限的表 | 第 23 章 |
| page walk | 頁表走訪 | TLB miss 時逐層讀 page table 找 PTE，需要多次記憶體存取 | 第 23 章 |
| parallelism | 平行 | 多個活動在同一瞬間真的一起執行，需要多份硬體 | 第 1 章（詳見第 30 章） |
| pass by value | 傳值 | 參數是呼叫者那邊值的複本；要改呼叫者的變數就得傳位址 | 第 2 章 |
| path traversal | 路徑穿越 | 在路徑中放入 `..` 讓 server 讀到網站根目錄以外的檔案 | 第 29 章 |
| payload | 有效負載 | 程式要求的那些 bytes；在網路中指封包 header 之後的資料 | 第 25 章 |
| PC (program counter) | 程式計數器 | 存著下一條要執行的指令位址的暫存器，x86-64 上是 `%rip` | 第 1 章 |
| PC update | 更新 PC | 決定下一條指令位址的階段 | 第 12 章 |
| PC-relative encoding | 相對 PC 編碼 | 跳躍目標存成「目標位址減去下一條指令位址」的有號位移 | 第 8 章 |
| PCIe | PCIe 匯流排 | 現代主要的 I/O 匯流排 | 第 15 章 |
| PE/COFF | PE/COFF 格式 | Windows 的目的檔與執行檔格式 | 第 18 章 |
| peak utilization | 峰值使用率 | 尚未釋放的 payload 總和占 heap 大小的最大比例 | 第 25 章 |
| pending signal | 待處理信號 | 已送出、還沒被接收的 signal；同種 signal 不會排隊 | 第 22 章 |
| percent-encoding | 百分比編碼 | 把特殊字元表示成 `%` 加兩位十六進位 | 第 29 章 |
| perf | Linux 效能剖析工具 | 以取樣與硬體計數器量測熱點、cache miss、branch miss 的 Linux 工具 | 第 14 章 |
| persistent connection (keep-alive) | 持續連線 | 回應完畢後連線保持開啟，可以送下一個請求 | 第 29 章 |
| PGO (profile-guided optimization) | 剖析導引最佳化 | 先收集代表性工作負載的分支走向，再據此重新編譯 | 第 8 章 |
| physical address (PA) | 實體位址 | DRAM 中真正的位址 | 第 7 章（詳見第 23 章） |
| physical page (page frame) | 實體頁框 | 實體記憶體中一頁大小的格子 | 第 23 章 |
| PIC (position-independent code) | 位置無關程式碼 | 不管被載入到哪裡都能正確執行、程式碼頁不必修改的程式碼 | 第 19 章 |
| PID / PPID | 行程編號／父行程編號 | 每個 process 的唯一編號，以及建立它的 process 的編號 | 第 21 章 |
| PID 1 (init) | 初始行程 | 收養孤兒的 process；在 namespace 中只會收到它有安裝 handler 的 signal | 第 21 章 |
| PIE (position-independent executable) | 位置無關執行檔 | 程式本身的程式碼與資料也能被載入到隨機位置的執行檔 | 第 11 章（詳見第 19 章） |
| PIPE | PIPE 管線處理器 | CS:APP 的五階段管線化 Y86-64 處理器 | 第 13 章 |
| pipe | 管道 | kernel 提供的單向 byte 通道，所有寫端都關閉後讀端才看到 EOF | 第 27 章 |
| pipeline | 管線 | 把指令執行拆成多個階段，讓不同指令的不同階段重疊進行 | 第 1 章（詳見第 13 章） |
| pipeline register | 階段暫存器 | 插在管線各階段之間、保存該指令資訊的暫存器 | 第 13 章 |
| pipelining | 管線化 | 讓多條指令分處不同階段同時進行，提高吞吐量但不縮短單條指令的延遲 | 第 13 章 |
| pitch | 列距 | 影像或二維陣列中相鄰兩列起點的 byte 距離，也就是每列實際佔的空間；可以比寬度多一點，以便對齊或避開 conflict miss | 第 10 章（詳見第 16、17 章） |
| placement policy | 放置策略 | 決定新的 block 或配置可以放在哪些位置的規則 | 第 15 章 |
| PLT (procedure linkage table) | 程序連結表 | 每個外部函式一小段跳板程式，經由 GOT 跳到真正的函式 | 第 19 章 |
| pointer | 指標 | 存放位址的變數 | 第 2 章 |
| pointer arithmetic | 指標運算 | 指標加 n 時，位址前進 n × sizeof(*p) 個 byte | 第 2 章 |
| pointer chasing | 指標追逐 | 下一個位址要等目前這次讀完才知道的存取模式，例如走訪 linked list | 第 15 章（詳見第 17 章） |
| port | 埠號 | 16-bit 無號整數，決定封包交給主機上的哪個程式 | 第 28 章 |
| positive overflow | 正溢位 | 兩個正數相加超過 TMax，截斷後變成負數 | 第 5 章 |
| posix_spawn | posix_spawn 函式 | 把「fork、調整環境、exec」包成一個呼叫的函式 | 第 21 章 |
| PPN / PPO | 實體頁號／實體頁內位移 | 翻譯只把 VPN 換成 PPN，offset 原封不動 | 第 23 章 |
| precise exception | 精確例外 | 發生例外時，之前的指令都完成、之後的指令都像沒執行過 | 第 13 章 |
| prefetcher | 預取器 | 偵測存取模式、提前把下一塊資料搬進 cache 的硬體 | 第 1 章（詳見第 17 章） |
| preprocessing | 前處理 | 編譯的第一步：展開 `#include`、巨集與條件編譯，產生 `.i` | 第 1 章 |
| prethreading | 預先建立 thread | server 啟動時就建立固定數量的 worker thread | 第 30 章 |
| procedure call | 程序呼叫 | 函式呼叫在機器層級的實作：轉移控制、傳遞資料、配置與釋放 local 空間 | 第 9 章 |
| process | 行程 | 作業系統對「一支正在執行的程式」的抽象，有自己的位址空間與執行狀態 | 第 1 章（詳見第 20 章） |
| process graph | 行程圖 | 把每個 process 的執行畫成一條線、fork 讓線分岔的圖 | 第 21 章 |
| process group (PGID) | 行程群組 | 一組可以一起接收 signal 的 process，用 PGID 識別 | 第 22 章 |
| producer-consumer | 生產者－消費者 | 一方放工作、一方取工作，中間以有上限的共享 queue 連接的結構 | 第 30 章（詳見第 31 章） |
| profiler | 效能剖析工具 | 告訴你時間花在哪裡的工具 | 第 14 章 |
| program header table | 程式標頭表 | 給載入器看的表，描述哪些 segment 要映射到哪個虛擬位址、權限是什麼 | 第 19 章 |
| progress graph | 進度圖 | 以各 thread 已完成步數為座標軸、把交錯畫成路徑的圖 | 第 31 章 |
| prologue / epilogue | 序言／結語 | 函式開頭建立 frame 與結尾拆除 frame 的那幾條指令 | 第 9 章 |
| propagation delay | 傳遞延遲 | 輸入改變後輸出跟著穩定所需的時間，約 ps 量級 | 第 12 章 |
| protocol layering | 協定分層 | 每一層只依賴下一層提供的服務，再加上自己的 header | 第 28 章 |
| proxy / reverse proxy | 代理伺服器／反向代理 | 同時扮演 server 與 client 的程式；替 server 服務的叫 reverse proxy | 第 29 章 |
| Proxy Lab | 代理實驗 | 寫一個支援並行與快取的 HTTP proxy | 第 29 章（詳見第 34 章） |
| PTE (page table entry) | 頁表項目 | page table 的一格，記錄 valid bit、PPN 與讀寫執行權限 | 第 23 章 |
| pthread_create / pthread_join | 建立／等待執行緒 | 建立新 thread，以及等待它結束並回收資源 | 第 30 章 |
| Pthreads (POSIX threads) | POSIX 執行緒 | 操作 thread 的標準 API，函式失敗時直接回傳錯誤碼 | 第 30 章 |

## Q

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| quarantine | 隔離區 | ASan 延後重用已釋放記憶體的先進先出佇列，讓 UAF 被抓到 | 第 26 章 |

## R

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| race | 競爭條件 | 程式的正確性取決於兩條控制流誰先執行到某一點 | 第 30 章（詳見第 31 章） |
| race condition | 競爭條件 | 結果取決於 thread 執行時序的錯誤 | 第 31 章 |
| RAII (Resource Acquisition Is Initialization) | 資源取得即初始化 | 把資源所有權綁在物件生命週期上，解構時自動釋放 | 第 26 章 |
| RAS / CAS | 列位址選通／行位址選通 | 讀 DRAM 時先送列號（RAS）把整列搬進 row buffer，再送行號（CAS）取出一格 | 第 15 章 |
| RAW (read after write) | 寫後讀 | 先寫後讀的資料依賴，依序管線中唯一會造成問題的類型 | 第 13 章 |
| reachable / unreachable | 可達的／不可達的 | 從 root 走得到的 block，以及走不到、就是垃圾的 block | 第 26 章 |
| readelf | ELF 檢視工具 | 讀取並列出 ELF 標頭、section、segment 與動態資訊的 Linux 工具 | 第 18 章 |
| readers-writers problem | 讀者－寫者問題 | 允許多個 reader 同時讀、writer 必須獨占的同步問題 | 第 31 章 |
| real-time signal | 即時信號 | `SIGRTMIN` 到 `SIGRTMAX` 的 signal，會排隊並能附帶整數資料 | 第 22 章 |
| reap | 回收 | 父行程用 `waitpid` 讀取子行程結束狀態、讓 kernel 刪除它的紀錄 | 第 21 章 |
| reassociation | 重新結合 | 改變括號位置讓部分運算脫離關鍵路徑 | 第 14 章 |
| red zone | 紅區（stack） | `%rsp` 之下 128 bytes、leaf function 可以直接使用而不調整 `%rsp` 的區域 | 第 9 章 |
| redzone | 紅區（ASan） | ASan 在每個 block 與陣列前後放的禁區，存取就報錯 | 第 2 章（詳見第 26 章） |
| reentrant | 可重入 | 不使用全域或靜態資料，任何時候被打斷再重新呼叫都正確 | 第 22 章（詳見第 32 章） |
| reentrant function | 可重入函式 | 完全不碰共享資料、所有狀態來自參數與 local 變數的 thread-safe 函式 | 第 32 章 |
| reference count | 參照計數 | 有幾個 descriptor 指向同一個 open file 項目，歸零才真正關閉 | 第 27 章 |
| reference counting | 參照計數 | 每個物件記錄有幾個指標指著它，降到 0 就回收；無法回收循環參照 | 第 26 章 |
| refresh | 刷新 | DRAM 的電容會漏電，必須定期讀出再寫回 | 第 15 章 |
| register file | 暫存器檔 | CPU 內一小組速度最快的儲存格，所有計算都在這裡進行 | 第 1 章（詳見第 12 章） |
| register renaming | 暫存器重新命名 | 每次寫入架構暫存器都分配新的實體暫存器，消除假的依賴 | 第 13 章 |
| register specifier byte | 暫存器指定 byte | Y86-64 指令中指出 rA、rB 兩個暫存器的那個 byte | 第 12 章 |
| register spilling | 暫存器溢出 | 同時活著的值超過暫存器數，編譯器只好把值放到 stack 上 | 第 14 章 |
| regular file / directory | 一般檔案／目錄 | 磁碟上的一般資料，以及把名稱連到檔案的特殊檔案 | 第 27 章 |
| relative / absolute speedup | 相對／絕對加速比 | 以平行版開 1 個 thread 為基準，或以最好的循序版本為基準 | 第 32 章 |
| relocatable object file (.o) | 可重定位目的檔 | 還不知道最終位址、須經連結才能執行的機器碼與資料檔 | 第 1 章（詳見第 18 章） |
| relocation | 重定位 | 決定每段程式碼與資料的最終位址，再修補所有依賴這些位址的欄位 | 第 1 章（詳見第 19 章） |
| relocation entry | 重定位項目 | 目的檔中記錄「這個位置的位址要由連結器填入」的項目 | 第 1 章（詳見第 19 章） |
| relocation type | 重定位類型 | 指出修補公式的種類，例如 `R_X86_64_PC32` 是 S + A − P、`R_X86_64_32` 是 S + A | 第 19 章 |
| RELRO / BIND_NOW | 唯讀重定位／立即綁定 | 啟動時就解析所有函式，再把 GOT 改成唯讀 | 第 19 章 |
| reorder buffer (ROB) | 重排序緩衝區 | 暫存亂序執行的結果，依程式順序才讓指令 retire | 第 13 章 |
| replacement policy | 替換策略 | 這一層滿了時決定要踢掉誰的規則 | 第 15 章 |
| request header | 請求標頭 | 請求行之後的「名稱: 值」各行，以空行結束 | 第 29 章 |
| request line | 請求行 | HTTP 請求的第一行：method、URI、version | 第 29 章 |
| restrict | 不重疊承諾 | C 關鍵字，承諾指標指向的資料不會透過其他指標存取；違反是 UB | 第 14 章 |
| retirement | 退休、提交 | 指令結果依程式順序正式寫進架構狀態 | 第 13 章 |
| return address | 返回位址 | `call` 推入 stack 的「下一條指令位址」，`ret` 取回並跳過去 | 第 9 章 |
| reverse engineering | 逆向工程 | 沒有原始碼時從機器碼理解程式行為 | 第 34 章 |
| RIO (Robust I/O) | 健壯 I/O 套件 | CS:APP 把處理 short count 的迴圈包成可重用函式的小套件 | 第 27 章 |
| RIP-relative addressing | 相對 %rip 定址 | 把全域變數位址寫成「距離目前指令多遠」，程式載入到任何位址都不必改指令 | 第 7 章 |
| RISC | 精簡指令集 | 指令固定長度、只有 load／store 能存取記憶體的 ISA 設計，例如 ARM64、RISC-V | 第 7 章（詳見第 12 章） |
| root | 根 | 不在 heap 裡但存著指向 heap 指標的位置：暫存器、stack、全域變數 | 第 26 章 |
| ROP (return-oriented programming) | 返回導向程式設計 | 串接程式中已存在、以 `ret` 結尾的指令片段來達成攻擊 | 第 34 章 |
| rotational latency | 旋轉延遲 | 等碟片轉到目標 sector 的時間，平均半圈 | 第 15 章 |
| round toward zero | 向零捨入 | 直接丟掉小數部分，C 整數除法的規則 | 第 5 章 |
| round-to-even (banker's rounding) | 取偶數捨入／銀行家捨入 | 剛好一半時捨入到最低位是偶數的值，讓誤差長期互相抵銷 | 第 6 章 |
| rounding | 捨入 | 把無限精度的結果調整成可表示的鄰近值；IEEE 754 要求每個基本運算只捨入一次 | 第 6 章 |
| router | 路由器 | 連接多個 LAN、轉送封包的裝置 | 第 28 章 |
| row buffer | 列緩衝區 | DRAM 晶片內暫存一整列資料的緩衝區 | 第 15 章 |
| row-major order | 列優先順序 | 二維陣列一列接一列存放，`A[i][j]` 與 `A[i][j+1]` 相鄰 | 第 10 章 |
| run-time stack | 執行期堆疊 | 存放每一層函式呼叫資料的記憶體區域，最晚被呼叫的最早結束 | 第 9 章 |
| runtime alias check | 執行期別名檢查 | 編譯器在執行時檢查兩個陣列是否重疊，再選快或慢的版本 | 第 14 章 |

## S

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| sanitizer | 執行期檢查器 | 編譯器在程式中插入檢查碼、於執行時抓出記憶體錯誤或 UB 的功能 | 第 2 章（詳見第 26 章） |
| scheduler | 排程器 | kernel 中決定接下來讓哪個 process 執行的部分 | 第 20 章 |
| section | 區段（section） | 目的檔中依內容分類的一塊，例如 `.text`、`.data`、`.bss`，給連結器看 | 第 18 章 |
| section header table | section 標頭表 | 描述每個 section 名稱、類型、位置與大小的表 | 第 18 章 |
| seek time | 尋道時間 | 把讀寫頭臂移到正確 track 的機械時間，平均數 ms | 第 15 章 |
| segment | 區段（segment） | 執行檔中一段要以相同權限映射到記憶體的內容，由一或多個 section 組成 | 第 19 章 |
| segmentation fault (segfault) | 區段錯誤 | 存取不合法或權限不符的位址，kernel 送出 `SIGSEGV` 終止程式 | 第 1 章（詳見第 23 章） |
| segregated free lists | 分離空閒串列 | 每個 size class 一條 free list 的配置器設計 | 第 25 章 |
| select / poll / epoll | I/O 多工介面 | 一次等待多個 fd 就緒的 system call；`epoll` 把監看集合存在 kernel 裡 | 第 30 章 |
| self-pipe trick | 自我 pipe 技巧 | handler 只對 pipe 寫一個 byte，事件迴圈把它當成普通事件處理 | 第 22 章 |
| self-study handout | 自學版材料 | 任何人都能下載的 Lab 版本，評分不連線到課程伺服器 | 第 34 章 |
| semaphore | 號誌 | 只能用 P、V 操作改變的非負整數同步工具 | 第 31 章 |
| send / receive (signal) | 送出／接收 | kernel 在目標 process 記下 signal，以及目標真正對它做出反應 | 第 22 章 |
| separate compilation | 分別編譯 | 每個 `.c` 各自編譯成 `.o`，只有連結器同時看到全部 | 第 1 章（詳見第 18 章） |
| SEQ (sequential processor) | 循序處理器 | 每個時脈 cycle 完整執行一條指令的 Y86-64 處理器 | 第 12 章 |
| sequential consistency | 循序一致性 | 所有操作好像排成一條總順序，每個 thread 自己的操作維持程式碼順序 | 第 32 章 |
| server / client | 伺服器／用戶端 | 管理資源、等待請求的 process，以及主動送出請求的 process | 第 28 章 |
| set | 集合 | cache 中一組 E 條 line；一個 block 只能放進它對應的 set | 第 16 章 |
| set associative cache (E-way) | 集合關聯快取 | 每個 set 有 E > 1 條 line，block 可以放在自己 set 的任一條 | 第 16 章 |
| set index / block offset | 集合索引／區塊內位移 | 位址中決定落在哪個 set，以及在 block 中第幾個 byte 的兩段位元 | 第 16 章 |
| SF (sign flag) | 符號旗標 | 結果最高位元為 1（有號解讀為負）時設為 1 的條件碼 | 第 8 章 |
| shadow memory | 影子記憶體 | ASan 中每 8 bytes 應用程式記憶體對應 1 byte、記錄可存取狀態的區域 | 第 26 章 |
| shared library (.so) | 共享函式庫 | 把連結延到載入或執行時、程式碼頁可以被許多 process 共用的函式庫 | 第 19 章 |
| shared object / private object (mapping) | 共享物件／私有物件 | 以 `MAP_SHARED` 映射時寫入大家看得到；以 `MAP_PRIVATE` 映射時寫入用 copy-on-write | 第 24 章 |
| shared object file | 共享目的檔 | 可在載入或執行時被連結的目的檔，例如 `.so` | 第 18 章（詳見第 19 章） |
| shared variable | 共享變數 | 記憶體中被兩個以上 thread 存取的實體 | 第 31 章 |
| shell | 命令列解譯器 | 讀指令、解析成 argv、fork 子行程去 exec 並等待它的程式 | 第 21 章 |
| Shell Lab | Shell 實驗 | 實作支援 job control 的 shell（`tsh`） | 第 22 章（詳見第 34 章） |
| Shellshock | Shellshock 漏洞 | bash 解析環境變數中函式定義時會執行附加指令的漏洞（CVE-2014-6271） | 第 29 章 |
| shift | 移位 | 把位元整體往左或往右移動；shift 量大於或等於寬度是 UB | 第 3 章 |
| short count | 不足量 | `read` 或 `write` 回傳的 bytes 數少於要求，是正常行為而非錯誤 | 第 27 章 |
| side effect | 副作用 | 函式除了回傳值以外對外部狀態造成的改變 | 第 14 章 |
| sigaction | sigaction 函式 | 設定 signal handler、`sa_mask` 與 `SA_RESTART` 等旗標的函式 | 第 22 章 |
| SIGALRM | 鬧鐘信號 | `alarm` 設定的計時器到期時送出的 signal | 第 22 章 |
| SIGBUS | 匯流排錯誤信號 | 位址在 VMA 裡、權限也對，但背後的檔案已經沒有那一頁時送出 | 第 24 章 |
| SIGCHLD | 子行程狀態信號 | 子行程結束或暫停時 kernel 送給父行程的 signal | 第 22 章 |
| SIGFPE | 算術錯誤信號 | 整數除以零等算術 exception 被轉成的 signal | 第 22 章 |
| SIGHUP | 掛斷信號 | 終端機斷線時送出；慣例上用來要求 daemon 重新載入設定 | 第 22 章 |
| SIGILL | 非法指令信號 | 執行到 CPU 不支援的指令時收到的 signal，常見於 `-march=native` 的部署事故 | 第 12 章 |
| SIGINT | 中斷信號 | 在終端機按 `Ctrl-C` 送出的 signal，預設終止 | 第 22 章 |
| SIGKILL | 強制終止信號 | 無法被捕捉或忽略的終止 signal，`kill -9` 與 OOM killer 使用 | 第 22 章 |
| sign / exp / frac field | 符號／指數／小數欄位 | 浮點數的三個欄位：正負號、加上 bias 的指數、M 小數點後的位元 | 第 6 章 |
| sign extension | 符號擴展 | 二補數變寬時在高位補原本的最高位 | 第 4 章 |
| sign-magnitude | 符號-大小 | 最高位當正負號、其餘位當絕對值的編碼，有 +0 與 −0 | 第 4 章 |
| signal | 信號 | 把「某件事發生了」通知使用者程式的機制，只有一個整數編號 | 第 22 章 |
| signal handler | 信號處理函式 | 收到 signal 時被呼叫的使用者函式，用 `sigaction` 設定 | 第 22 章 |
| signalfd / sigwait | 同步等待信號 | 讓程式像讀資料一樣同步地等待 signal，避開 handler 的限制 | 第 22 章 |
| signed / unsigned | 有號／無號 | 同一串位元是否解讀成可以表示負數的值 | 第 4 章 |
| SIGPIPE | 管線破裂信號 | 寫入對方已關閉的 pipe 或 socket 時送出，預設終止 process | 第 22 章（詳見第 28 章） |
| sigprocmask | sigprocmask 函式 | 阻擋或解除阻擋一組 signal 的函式，用來消除 handler 與主程式的 race | 第 22 章 |
| SIGSEGV | 區段錯誤信號 | 存取不合法位址時 kernel 送出的 signal | 第 22 章（詳見第 23 章） |
| SIGSTOP / SIGTSTP / SIGCONT | 暫停／終端機暫停／繼續信號 | 讓 process 暫停（`Ctrl-Z` 送 SIGTSTP）與恢復執行的 signal | 第 22 章 |
| sigsuspend | sigsuspend 函式 | 在同一個不可分割的動作裡解除阻擋並開始等待 signal | 第 22 章 |
| SIGTERM | 終止信號 | 要求 process 正常結束的 signal，`kill` 與容器停止時預設送出 | 第 22 章 |
| SIMD | 單指令多資料 | 一條指令同時處理多筆資料，例如 SSE、AVX、NEON | 第 1 章（詳見第 14 章） |
| simple segregated storage / segregated fits | 簡單分離儲存／分離適配 | 每類 block 大小相同不切割不合併，或每類大小不一、可切割合併 | 第 25 章 |
| single / double precision | 單精度／雙精度 | 32 位元的 `float` 與 64 位元的 `double` 浮點格式 | 第 6 章 |
| size class | 大小類別 | 依大小範圍分類的多條 free list | 第 25 章 |
| size suffix | 大小後綴 | 指令名稱尾端表示一次處理幾 bytes 的字母：b、w、l、q | 第 7 章 |
| size_t | 大小型別 | 表示大小、長度與索引的無號整數型別，LP64 上是 64 bits | 第 3 章（詳見第 4 章） |
| slowloris | slowloris 攻擊 | 開很多連線、每條都極慢地送 header，耗盡 server 資源 | 第 29 章 |
| SMT (simultaneous multithreading) | 同時多執行緒 | 讓一個核心同時保有兩個 thread 的狀態並交錯使用執行單元，Intel 稱為 hyperthreading | 第 1 章 |
| SO_REUSEADDR | 位址重用選項 | 允許綁定仍有 TIME_WAIT 連線的位址，避免重啟時 `Address already in use` | 第 28 章 |
| socket | socket | kernel 提供的網路通訊端點，在程式看來就是一個 file descriptor | 第 28 章 |
| socket pair (4-tuple) | 四元組 | 連線兩端的位址與 port，唯一識別一條連線 | 第 28 章 |
| soname | soname | 寫在 `.so` 裡、代表 ABI 主版號的名稱，例如 `libjpeg.so.8` | 第 19 章 |
| spatial locality | 空間區域性 | 剛被存取過的位置，它附近的位置很可能很快被存取 | 第 1 章（詳見第 15 章） |
| Spectre | Spectre 漏洞 | 誘導處理器推測執行越界讀取，再透過 cache 時間差讀出秘密的攻擊 | 第 13 章 |
| speculative execution | 推測執行 | 沿預測的方向先往下執行，猜錯再丟掉結果 | 第 8 章（詳見第 13 章） |
| speedup | 加速比 | 1 個核心的時間除以 p 個核心的時間 | 第 32 章 |
| split lock | 分割鎖 | 跨越兩條 cache line 的未對齊 atomic 操作，CPU 必須鎖住記憶體匯流排 | 第 10 章 |
| splitting | 切割 | 把太大的 free block 切成已配置與剩下的 free 兩塊 | 第 25 章 |
| spurious wakeup | 虛假喚醒 | thread 在沒有人 signal 的情況下醒來，所以等待要放在 while 迴圈裡 | 第 31 章 |
| SRAM | 靜態隨機存取記憶體 | 每個 bit 由約六個電晶體組成，快但貴，用來做 cache | 第 1 章（詳見第 15 章） |
| SSD (solid state drive) | 固態硬碟 | 用 NAND flash 存資料、沒有會動零件的儲存裝置 | 第 15 章 |
| stack | 堆疊 | 記憶體中後進先出、往低位址成長的區域，存放 return address、local 變數與保存的暫存器 | 第 7 章（詳見第 9 章） |
| stack canary (stack protector) | 堆疊金絲雀 | 編譯器在 local 陣列與 saved 資料之間放的隨機值，函式返回前檢查是否被改寫 | 第 2 章（詳見第 11 章） |
| stack frame | 堆疊框 | 一層函式呼叫在 stack 上佔的一塊 | 第 9 章 |
| stack overflow | 堆疊溢位 | stack 用量超過上限、撞上 guard page，通常由過深的遞迴造成 | 第 9 章 |
| stack pointer (%rsp) | 堆疊指標 | 永遠指向 stack 頂端的暫存器 | 第 7 章 |
| stack walking | 走訪呼叫鏈 | 沿著 saved frame pointer 一層層找出所有 frame，產生 stack trace | 第 9 章 |
| stall | 停頓 | 讓指令留在原階段等一個 cycle | 第 13 章 |
| Standard I/O (stdio) | 標準 I/O | `fopen`、`printf`、`fgets` 等以 `FILE *` 操作、帶緩衝區的函式庫 | 第 27 章 |
| standard input / output / error | 標準輸入／標準輸出／標準錯誤 | 每個 process 一開始就打開的 fd 0、1、2 | 第 1 章（詳見第 27 章） |
| starvation | 飢餓 | 某個 thread 一直有機會前進，卻始終輪不到 | 第 31 章 |
| Stat (status code) | 狀態碼 | Y86-64 記錄程式是否正常的狀態：AOK、HLT、ADR、INS | 第 12 章 |
| state machine | 狀態機 | 每條連線一個狀態，每個 I/O 事件讓它轉移到下一個狀態 | 第 30 章 |
| static content / dynamic content | 靜態內容／動態內容 | 事先存在磁碟上的檔案，以及收到請求時才執行程式產生的內容 | 第 29 章 |
| static library | 靜態函式庫 | 把一群 `.o` 打包成 archive，連結器只挑出真正需要的成員複製進執行檔 | 第 18 章 |
| status code | 狀態碼 | 回應的三位數結果，第一位代表類別，例如 2xx 成功、4xx client 錯誤 | 第 29 章 |
| stdio buffer | 標準 I/O 緩衝區 | `printf` 等先把輸出放進使用者空間的緩衝區，滿了或遇到條件才 `write` | 第 21 章 |
| storage duration | 儲存期間 | 變數存在多久；`static` 變數放在 `.data` 或 `.bss`，整個程式執行期間都在 | 第 18 章 |
| storage element | 儲存元件 | 能記住值的電路元件，例如時脈暫存器與記憶體 | 第 12 章 |
| store | 存回 | 把暫存器的值寫回記憶體的動作 | 第 1 章 |
| store buffer | 寫入緩衝區 | 核心先把 store 放進的緩衝區，在寫進 cache 前其他核心看不到 | 第 32 章 |
| stream | 串流 | Standard I/O 中「一個 fd 加上使用者空間緩衝區」的抽象 | 第 27 章 |
| strict aliasing | 嚴格別名規則 | C 規定不能用不相容型別的指標存取同一個物件，違反是 UB | 第 10 章 |
| stride | 步幅 | 相鄰兩次存取之間的間隔（以元素數或 bytes 計）；相鄰兩列起點的距離另稱 pitch（列距） | 第 15 章 |
| stride-1 access | 循序存取 | 依序存取相鄰元素，spatial locality 最好；每隔 k 個讀一次是 stride-k | 第 15 章 |
| strong scaling / weak scaling | 強擴展／弱擴展 | 問題大小固定增加核心，或每核工作量固定、總量一起增加 | 第 32 章 |
| strong symbol / weak symbol | 強符號／弱符號 | 函式與有初值的全域變數是強符號；`weak` 標記或 `-fcommon` 下沒有初值的全域變數是弱符號 | 第 18 章 |
| struct | 結構 | 把不同型別的欄位組成一個整體；在機器層級就是一塊連續記憶體 | 第 2 章（詳見第 10 章） |
| subreaper | 子孫回收者 | 用 `prctl(PR_SET_CHILD_SUBREAPER)` 宣告接手底下孤兒的 process | 第 21 章 |
| supercell | 超級單元 | DRAM 晶片內以 (row, col) 定址的一格，存 w 個 bits | 第 15 章 |
| superscalar | 超純量 | 每個 cycle 可以發出並執行多條指令的處理器設計 | 第 1 章（詳見第 13 章） |
| swap | 交換空間 | 記憶體不足時作業系統暫存匿名頁的磁碟空間 | 第 23 章 |
| symbol | 符號 | 函式與全域變數的名字，連結器把「用到它的地方」接到「定義它的地方」 | 第 18 章 |
| symbol interposition | 符號 interposition | 執行檔或更早載入的 library 中的同名定義會蓋過 library 自己的定義 | 第 19 章 |
| symbol resolution | 符號解析 | 替每個符號參照找到唯一的定義 | 第 1 章（詳見第 18 章） |
| symbol table (.symtab) | 符號表 | 目的檔中列出所有符號名稱、位置與類型的表 | 第 18 章 |
| symbol versioning | 符號版本 | 每個匯出符號附帶版本標籤，同一函式可同時存在新舊實作 | 第 19 章 |
| synchronous / asynchronous | 同步／非同步 | 事件是否為執行某條指令的直接結果 | 第 20 章 |
| system call | 系統呼叫 | 程式請 kernel 代辦特權工作的受控入口，例如 `read`、`write` | 第 1 章（詳見第 20 章） |
| System V AMD64 ABI | System V AMD64 ABI | Linux 與 macOS x86-64 採用的 ABI，前六個整數參數依序放 `%rdi`、`%rsi`、`%rdx`、`%rcx`、`%r8`、`%r9` | 第 9 章 |

## T

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| tag | 標籤位元 | 位址的高位部分，用來辨認 line 裡存的是哪一個 block | 第 16 章 |
| tagged union | 帶標籤的聯合 | 用一個欄位記錄 union 目前存的是哪一種成員 | 第 10 章 |
| tail call | 尾呼叫 | 函式最後一步呼叫另一個函式時直接跳過去，省下一個 frame | 第 9 章 |
| task / TID / TGID | 任務／執行緒編號／執行緒群組編號 | Linux kernel 眼中每個 thread 是一個 task，有自己的 TID，同 process 共用 TGID | 第 30 章 |
| TCP | 傳輸控制協定 | 在 IP 上提供可靠、有序、雙向 byte stream 連線的協定，不保留訊息邊界 | 第 28 章 |
| temporal locality | 時間區域性 | 剛被存取過的位置，很可能很快又被存取 | 第 1 章（詳見第 15 章） |
| tentative definition | 暫定定義 | C 標準對「沒有初值的檔案層級變數定義」的稱呼 | 第 18 章 |
| .text / .rodata / .data / .bss | 程式碼／唯讀資料／已初始化資料／未初始化資料 | 目的檔中最常見的四個 section；`.bss` 不佔檔案空間 | 第 18 章 |
| text file | 文字檔 | 只由可印出字元組成的檔案 | 第 1 章 |
| thrashing | 顛簸 | 幾個常用 block 輪流把彼此踢出 cache，幾乎每次存取都 miss | 第 16 章 |
| thread | 執行緒 | 同一個 process 裡的一條邏輯控制流，共享程式碼與全域資料，各有自己的 stack 與暫存器 | 第 1 章（詳見第 30 章） |
| thread context | 執行緒情境 | 每個 thread 私有的狀態：thread ID、stack、stack pointer、PC、暫存器與條件碼 | 第 30 章 |
| thread-level parallelism | 執行緒層級平行 | 用多個核心或 SMT 讓多個 thread 同時執行 | 第 1 章 |
| thread-local storage | 執行緒區域儲存 | 每個 thread 存取同一個名字時拿到自己的那一份，C11 寫成 `_Thread_local` | 第 31 章 |
| thread-safe / thread-unsafe | 執行緒安全／不安全 | 多個 thread 同時重複呼叫時結果是否永遠正確 | 第 32 章 |
| ThreadSanitizer (TSan) | 執行緒檢查器 | 在記憶體存取與同步操作旁插入檢查、偵測 data race 的工具 | 第 31 章 |
| three-way handshake | 三次握手 | TCP 建立連線的 SYN、SYN-ACK、ACK 交換 | 第 28 章 |
| throughput | 吞吐量 | 單位時間能完成多少件工作 | 第 13 章 |
| throughput bound | 吞吐量界限 | 即使運算互相獨立，CPE 也不可能低於 issue time ÷ capacity | 第 14 章 |
| thumbd | 縮圖服務 | 本書貫穿案例中拾光相簿負責產生縮圖的 C 語言服務 | 第 1 章 |
| time slice | 時間片 | process 每次連續執行的一段時間 | 第 20 章 |
| TIME_WAIT | TIME_WAIT 狀態 | 主動關閉的一方在連線結束後停留一段時間的狀態 | 第 28 章 |
| timer interrupt | 計時器 interrupt | 硬體計時器定期觸發的 interrupt，讓 kernel 拿回控制權做排程 | 第 20 章 |
| Tiny | Tiny 伺服器 | CS:APP 的小型 iterative web server 範例 | 第 29 章 |
| TLB (translation lookaside buffer) | 轉譯後備緩衝區 | MMU 裡快取最近用過的 PTE 的小型硬體快取 | 第 16 章（詳見第 23 章） |
| TLB hit / TLB miss | TLB 命中／失誤 | PTE 是否已在 TLB 中，不必或必須查 page table | 第 23 章 |
| TMax / TMin | 有號最大值／最小值 | 二補數最大值是最高位 0、其餘全 1；最小值是最高位 1、其餘全 0 | 第 4 章 |
| topological sort | 拓撲排序 | 圖中所有頂點的一種排列，使每條邊都從前指向後；對應一種可能的輸出順序 | 第 21 章 |
| tracing GC | 追蹤式回收 | 從 root 沿指標追蹤來判斷存活物件的 GC 演算法家族 | 第 26 章 |
| track / sector | 磁軌／扇區 | 碟片上的同心圓，以及每條 track 切成的固定大小單位 | 第 15 章 |
| transaction | 交易 | client-server 的一次往返：送請求、處理、回應、處理回應 | 第 28 章 |
| transfer time | 傳輸時間 | sector 經過讀寫頭、資料被讀出的時間 | 第 15 章 |
| transpose | 轉置 | 讀一列寫一行的運算，`src` 與 `dst` 總有一邊是 stride-n | 第 17 章 |
| trap | 陷阱 | 程式刻意執行指令觸發的同步 exception，例如 system call，返回下一條指令 | 第 20 章 |
| TRIM | TRIM 指令 | 告訴 SSD 哪些 block 已經不用、garbage collection 不必搬它們 | 第 15 章 |
| truncation | 截斷 | 轉成較窄型別時直接丟掉高位，只留下低 k 位再重新解讀 | 第 4 章 |
| two's complement | 二補數 | 最高位權重改成負的 −2^(w−1)、其餘位與 unsigned 相同的有號編碼 | 第 4 章 |

## U

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| UDP | 使用者資料包協定 | 在 IP 上加上 port、保留訊息邊界但不可靠的協定 | 第 28 章 |
| ulp (unit in the last place) | 最後一位的單位 | 某個值附近相鄰兩個浮點數的間距 | 第 6 章 |
| umask | 權限遮罩 | 建立檔案時要從權限中拿掉的位元 | 第 27 章 |
| UMax | 無號最大值 | w 位元無號數的最大值 2^w − 1，即全部位元為 1 | 第 4 章 |
| undefined behavior (UB) | 未定義行為 | C 標準對該操作不再約束程式的任何行為，編譯器可假設它永遠不會發生 | 第 2 章（詳見第 5 章） |
| undefined reference | 未定義參照 | 連結器在所有輸入中找不到某個符號定義時的錯誤 | 第 18 章 |
| UndefinedBehaviorSanitizer (UBSan) | 未定義行為檢查器 | 在可能觸發 UB 的運算前插入檢查的 sanitizer | 第 26 章 |
| union | 聯合 | 所有欄位都從 offset 0 開始、共用同一塊記憶體的型別 | 第 10 章 |
| Unix I/O | Unix I/O | 把所有 I/O 裝置抽象成檔案、以 `open`、`read`、`write`、`close` 等 system call 操作的介面 | 第 27 章 |
| unsafe region | 不安全區 | progress graph 中兩個 thread 同時在 critical section 的區域 | 第 31 章 |
| unsigned encoding (B2U) | 無號編碼 | 每一位權重都是 2 的冪的解讀規則 | 第 4 章 |
| unwind information (CFI) | unwind 資訊 | `.eh_frame` 中以 DWARF 格式描述「每個位置如何找回呼叫者 frame」的資料 | 第 9 章 |
| unwinding | 展開堆疊 | 逐層回到呼叫者的過程，debugger、profiler 與 C++ 例外都需要 | 第 9 章 |
| URL / URI | 統一資源定位符／統一資源識別符 | 識別一份內容的字串；請求中只送 path 與 query 那一段（URI） | 第 29 章 |
| use-after-free (UAF) | 釋放後使用 | 記憶體已經 `free`，程式仍透過舊指標讀寫它 | 第 26 章 |
| usual arithmetic conversions | 一般算術轉換 | 兩個運算元型別不同時統一成共同型別的規則；寬度相同時 unsigned 贏 | 第 4 章 |
| UTF-8 | UTF-8 編碼 | 可變長度的 Unicode 編碼，常用中文字佔 3 個 byte | 第 3 章 |
| utilization | 空間利用率 | heap 峰值大小中真正在使用的 payload 比例 | 第 25 章（詳見第 34 章） |

## V

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| v-node table | v-node 表 | 所有 process 共用、每個檔案一項，存放檔案本身資訊的表 | 第 27 章 |
| Valgrind (Memcheck) | Valgrind 記憶體檢查器 | 不重新編譯，執行時把機器碼翻譯成加上檢查的版本 | 第 26 章 |
| valid bit | 有效位元 | 標示這條 line（或這個 PTE）存著有效內容的位元 | 第 16 章 |
| variadic function | 可變參數函式 | 參數個數不固定的函式，例如 `printf` | 第 9 章 |
| vDSO (virtual dynamic shared object) | 虛擬動態共享物件 | kernel 映射進每個 process 的一小段程式碼與資料，讓 `clock_gettime` 不必進 kernel | 第 20 章 |
| vector register | 向量暫存器 | 用於浮點運算與 SIMD 的寬暫存器，例如 `%xmm`、`%ymm` | 第 7 章（詳見第 14 章） |
| virtual address (VA) | 虛擬位址 | 程式使用的位址，要經 MMU 翻譯成實體位址 | 第 7 章（詳見第 23 章） |
| virtual address space | 虛擬位址空間 | 一個 process 看到的整片位址範圍，由低到高排著程式碼、資料、heap、shared library 與 stack | 第 1 章（詳見第 24 章） |
| virtual memory | 虛擬記憶體 | 主記憶體與磁碟的抽象，讓每個 process 以為自己獨佔一大片位址空間 | 第 1 章（詳見第 23 章） |
| VLA (variable-length array) | 可變長度陣列 | 長度在執行期才決定的陣列 | 第 10 章（詳見第 11 章） |
| VMA (virtual memory area) | 虛擬記憶體區域 | 位址空間中一段連續、屬性一致的範圍，CS:APP 稱為 area 或 segment | 第 24 章 |
| void pointer (void *) | 泛型指標 | 可以指向任何型別，但不能解參考、標準 C 也不允許做加減 | 第 10 章 |
| volatile memory | 揮發性記憶體 | 斷電後資料就消失的記憶體，例如 DRAM、SRAM | 第 15 章 |
| volatile sig_atomic_t | 信號安全旗標型別 | handler 與主程式之間傳遞旗標的型別：`volatile` 讓每次都真的讀寫記憶體 | 第 22 章 |
| voluntary / involuntary context switch | 自願／非自願切換 | process 主動等待而被切走，或時間片用完被強制切走（preemption，搶占） | 第 20 章 |
| VPN / VPO | 虛擬頁號／頁內位移 | 虛擬位址的高位（第幾頁）與低位（頁內第幾個 byte） | 第 23 章 |
| VSZ / RSS | 虛擬大小／常駐集大小 | process 映射的虛擬位址總量，以及實際佔用的實體記憶體 | 第 23 章 |

## W

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| W^X (write xor execute) | 寫入與執行互斥 | 同一頁不應同時可寫又可執行 | 第 23 章 |
| waitpid | waitpid 系統呼叫 | 等待並回收子行程；加 `WNOHANG` 時不等、立刻回傳 | 第 21 章 |
| wear leveling | 磨損平衡 | 讓所有 block 平均磨損的 FTL 機制 | 第 15 章 |
| Web | 全球資訊網 | 建立在 client-server 模型上、以 HTTP 傳送內容的應用 | 第 29 章 |
| well-known port / ephemeral port | 知名埠／臨時埠 | 0–1023 給標準服務用；client 連線時由 kernel 自動挑的 port | 第 28 章 |
| word | 字（機器字） | 匯流排一次搬運的固定大小，等於機器的 word size；64-bit 系統上是 8 bytes | 第 1 章 |
| word size | 字長 | 機器自然處理的整數與位址寬度，決定指標大小與虛擬位址空間上限 | 第 3 章 |
| worker thread / thread pool | 工作執行緒／執行緒池 | 預先建立、從共享 queue 取工作來做的一組 thread | 第 30 章 |
| working set | 工作集 | 某段時間內程式反覆存取的那批資料 | 第 15 章 |
| wrapper function | 包裝函式 | 把參數照約定放好、執行 `syscall` 並翻譯回傳值的 C 函式；也指攔截呼叫的函式 | 第 20 章 |
| write amplification | 寫入放大 | 主機只寫一份、flash 實際寫了好幾份 | 第 15 章 |
| write back | 寫回 | 把 valE、valM 寫進最多兩個暫存器的階段 | 第 12 章 |
| write-allocate / no-write-allocate | 寫入配置／不寫入配置 | 寫入 miss 時要先把 block 讀進 cache，或直接寫到下一層 | 第 16 章 |
| write-back | 回寫 | 只寫 cache 並標記 dirty，等 line 被踢掉時才寫回下一層 | 第 16 章 |
| write-through | 直寫 | 每次寫 cache 同時寫到下一層 | 第 16 章 |

## X

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| x86-64 | x86-64 架構 | Intel 與 AMD 的 64-bit 指令集，本書組合語言的主要對象 | 第 7 章 |

## Y

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| Y86-64 | Y86-64 教學指令集 | CS:APP 設計的簡化版 x86-64，保留暫存器、條件碼、記憶體與 stack 等核心元素 | 第 12 章 |

## Z

| 英文術語 | 中文 | 定義 | 首次詳細說明 |
|---|---|---|---|
| zero extension | 零擴展 | 無號數變寬時在高位補 0 | 第 4 章 |
| zero page | 全零頁 | 只讀不寫的匿名頁共用的唯讀全零實體頁，第一次寫入時才真正配頁 | 第 24 章 |
| ZF (zero flag) | 零旗標 | 結果為 0 時設為 1 的條件碼 | 第 8 章 |
| zombie | 殭屍行程 | 已終止但父行程還沒回收的 process，佔著一個 PID | 第 21 章 |

## 中文術語

| 中文 | 定義 | 首次詳細說明 |
|---|---|---|
| 拾光相簿 | 本書貫穿案例的相簿服務公司，`thumbd` 是它的縮圖後端 | 第 1 章 |
| 呼叫堆疊 | 目前從 `main` 一路到當下函式的呼叫鏈，debugger 用 backtrace 顯示 | 第 2 章 |
| 固定寬度整數型別 | `int8_t`、`uint32_t`、`int64_t` 等名字直接寫出位元數與有無號的型別 | 第 3 章 |
| 解讀規則 | 同一串位元依型別被解讀成不同的值；位元本身沒有型別 | 第 3 章 |
| 短路求值 | `&&`、`\|\|` 在結果已經確定時不再計算右邊 | 第 3 章 |
| 運算子優先順序 | `&`、`^`、`\|` 低於 `==`，shift 低於加減，混用時一律加括號 | 第 3 章 |
| 向下取整 | 往負無限大捨入，算術右移的效果；負數除法要先加 bias 才能變成向零捨入 | 第 5 章 |
| 結合律（浮點） | 浮點加法不滿足結合律，`(a + b) + c` 可能不等於 `a + (b + c)` | 第 6 章 |
| 長度前綴 | 先送固定大小的長度欄位、再送那麼多 bytes 的 framing 方式 | 第 28 章 |
| 分隔符號 | 每則訊息以特定字元（例如換行）結束的 framing 方式 | 第 28 章 |
| 由上往下診斷 | 從使用者看到的症狀開始，一次往下一層，每層都要有上一層的證據並提出可反證的假設 | 第 33 章 |
