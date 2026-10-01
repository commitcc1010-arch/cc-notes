"""Deepening content for CS:APP chapters 0–4."""
from csapp_supplement_model import S


SUPPLEMENTS = [
    S(
        "prereq",
        0,
        "C、Linux 與證據導向的最低地基",
        "開始談 bit、assembly 與 process 前，哪些語言與工具模型不能含糊？",
        (
            "一段 C 原始碼、編譯選項與執行環境",
            "用 object／lifetime／ABI／system call 模型推理，而不是靠『通常可以』",
            "能建立最小重現、閱讀 warning，並用 debugger 或 sanitizer 取得證據",
        ),
        [
            ("Object", "C 裡具有大小、對齊、storage duration 與 lifetime 的資料儲存區；不是物件導向的 class instance。", "`int a[4]` 是一個 array object，`a[1]` 是其中一個 subobject。"),
            ("Undefined behavior", "標準不再約束結果的程式行為；最佳化器可以假設合法程式不會走到這裡。", "signed overflow、越界、use-after-free、data race 都可能讓 debug 與 release 表現不同。"),
            ("ABI", "編譯後模組在 binary 邊界如何協作的契約，包括 calling convention、型別 layout 與 object format。", "Caller 把前幾個整數參數放到指定 registers，callee 依規則取用。"),
            ("Evidence loop", "先提出可被推翻的假說，再用最小實驗、trace 或 counter 驗證。", "懷疑 stack corruption 時，用 ASan 與 watchpoint 找第一個壞寫入，而非只看最後 crash。"),
            ("Ownership", "誰負責資源、何時移交、何時釋放的規則。C 不會替你自動表達它。", "函式回傳 `malloc` pointer 時，介面要說清楚 caller 是否必須 `free`。"),
        ],
        r"""
問題 → 固定輸入與平台 → 開啟 warnings / debug info
  ↓
建立最小重現 → 寫下 object、owner、lifetime、合法範圍
  ↓
選觀察工具：compiler / GDB / sanitizer / strace
  ↓
證據支持或推翻假說 → 修正模型 → 加入 regression test
""",
        r"""
### 0.A 先分清四個世界：語言、編譯器、ABI、作業系統

C 標準描述 expression、object、type 與哪些行為有定義；compiler 把合法程式轉成某個 target 的機器碼；ABI 規範不同 object file 與 library 如何在 binary 層合作；作業系統再提供 process、virtual memory、file descriptor 等執行環境。這四層不能互相代替。例如「Linux 上 `int` 是 32 bits」是平台事實，不是所有 C 實作的永恆真理；「讀越界通常看到附近資料」更不是 contract，而是 undefined behavior 的偶然現象。

學 CS:APP 時，遇到一句系統結論要先問它屬於哪一層。若是語言規則，看標準與 compiler diagnostics；若是 x86-64 ABI，看 calling convention 與 ELF；若是 Linux 行為，看 system call contract。這個分類會消除大量似是而非的爭論。

### 0.B Pointer 是帶型別的地址值，不是 allocation

Pointer variable 自己也是 object，內容是一個地址表示。它不自動攜帶 allocation 大小、owner 或是否仍有效。`p + 1` 的步長由 pointed-to type 決定；`*p` 是否合法則同時依賴 alignment、lifetime、bounds 與 access permission。Array 在多數 expression 會轉成首元素 pointer，但 array 本身有固定大小；因此 `sizeof array` 與 `sizeof pointer` 是兩件事。

建立一個可維護介面時，長度與 ownership 必須顯式存在：

```c
struct bytes {
    unsigned char *data;
    size_t len;
};

/* 成功時 caller 擁有 out->data；失敗時 out 維持空值。 */
int read_all(int fd, struct bytes *out);
void bytes_destroy(struct bytes *value);
```

這種 contract 比「回傳一個 pointer，大家應該知道怎麼用」更能防止跨章出現的 buffer overflow、double free 與 short read。

### 0.C Integer conversion 與 UB 要在看 assembly 前弄清楚

C 的 usual arithmetic conversions 可能把 signed operand 轉成 unsigned；小於 `int` 的整數型別通常先 promotion。若沒有先在 source level 說清楚，assembly 中的 unsigned branch、zero extension 或 sign extension 就會像魔法。建議每遇到混合型別 expression 都寫出：operand 原型別 → promotion 後型別 → 運算型別 → 結果型別。

Undefined behavior 的危險不只「結果不確定」。Compiler 可由「這裡不可能 overflow」推導某個 branch 永遠成立，再把防護刪掉。因此正確流程是消除 UB，而不是關閉最佳化。Warnings、ASan、UBSan 與 TSan 各自只看部分問題；沒有單一工具可以證明程式完全安全。

### 0.D 讀 man page 的方法

System call 或 library function 至少讀六件事：輸入與輸出、成功值、失敗值、`errno` 何時有效、是否可被 signal 中斷、是否可能只完成部分工作。再補 lifetime 與 thread/signal safety。例如 `read` 回傳正數但小於 requested count 是正常成功；回傳 0 對 regular file/socket 通常表示 EOF；回傳 -1 才看 `errno`。若把 short count 當錯誤，後面網路章一定會寫出脆弱程式。

### 0.E 工具不是答案，而是可觀察窗口

GDB 告訴你某次執行的 state；sanitizer 在被 instrument 且走到的 path 上偵測特定違規；`strace` 看 user/kernel 邊界；`perf` 的 counter 是硬體事件的近似量測。每個輸出都要連回假說。例如 `SIGSEGV` 只代表 CPU/OS 阻止某次 memory access，不等於根因就在 faulting instruction；真正錯誤可能是更早的 dangling pointer。
""",
        r"""
建立 `lifetime.c`，回傳 local variable 的地址，分別用 `-O0`、`-O2`、ASan 編譯。記錄 warning、執行結果與 assembly 差異，再把介面改成 caller 傳入 output pointer。接著用 GDB 的 `break`、`p/x`、`x/16xb` 與 `bt` 觀察 object lifetime。重點不是製造某個固定 crash，而是證明 UB 沒有可靠輸出可依賴。

```bash
cc -Wall -Wextra -Wconversion -g -O0 lifetime.c -o lifetime-O0
cc -Wall -Wextra -Wconversion -g -O2 lifetime.c -o lifetime-O2
cc -g -fsanitize=address,undefined lifetime.c -o lifetime-san
```
""",
        [
            "把 compiler warning 當風格問題直接關閉，失去最便宜的靜態證據。",
            "把 pointer、array、allocation 與 object lifetime 混成同一件事。",
            "只在 `-O0` 測試，讓 UB 或 data race 被偶然 layout 掩蓋。",
            "看到 crash 行就認定它是根因，沒有找第一個被破壞的 invariant。",
            "引用某平台觀察結果，卻沒有標出 compiler、architecture、libc 與 kernel。",
        ],
        [
            ("為何 `sizeof p` 無法得知 `malloc` 配置的大小？", "因為 `p` 的 object representation 只需要保存一個可指向 `int` 的 pointer value，C 型別系統沒有要求它保存 allocation metadata。Allocator 可能在 block 前後維護私有大小，但那不是任意 caller 可由 pointer 型別取得的 portable contract。若 API 需要長度，必須額外傳入、包進 struct，或提供專用查詢介面。"),
            ("`free(p); p = NULL;` 為何不能完整消除 use-after-free？", "它只清掉當前 variable 的一個 alias。其他 pointer、container entry 或 register copy 仍可能指向同一 allocation；而且 `free` 之後到設成 NULL 之前也可能發生並行存取。根本解法是明確 ownership、限制 alias、讓釋放點可推理，再以 ASan 或測試輔助驗證。"),
            ("為何 release build 才壞通常應先懷疑 UB 或 race？", "最佳化會改變 instruction ordering、register allocation、stack layout 與執行時序，但合法程式的 observable behavior 仍應符合語言與同步 contract。若只有最佳化後出錯，常表示程式依賴未定義行為、未初始化值、資料競爭或 timing。正確做法是保留 `-O2 -g` 重現並使用 sanitizer，而不是永久關最佳化。"),
            ("Declaration、definition、linkage 與 lifetime 如何分工？", "Declaration 提供名稱與型別資訊；definition 另外提供 function body 或 object storage。Linkage 回答不同 translation units 的同名宣告是否指向同一 entity；lifetime 回答 object 何時存在且可被存取。它們分別影響 compiler type checking、linker symbol resolution 與 runtime correctness。"),
            ("為何 `errno` 不能在任何時候直接讀？", "`errno` 只有在某 API 以其 contract 指示失敗後才有解釋價值；成功呼叫通常可以保留先前值。它也不是 exception object，而是 thread-local error code。先檢查 return value，再立即保存 `errno`，才能避免後續 library call 覆蓋診斷資訊。"),
            ("Sanitizer 沒報錯是否可證明沒有 bug？", "不能。它只覆蓋被 instrument 的程式與實際執行 path，而且不同 sanitizer 偵測不同問題；ASan 不負責 data race，TSan 也不證明邏輯 invariant。正確組合是 warnings、static analysis、sanitizers、fuzzing、邊界測試與清楚 contract。"),
            ("系統除錯時，什麼叫可被推翻的假說？", "假說必須預測一項尚未觀察的結果。例如『p99 變慢是 LLC miss 增加』預測 slow workload 的 LLC-load-misses 與 cycles 會上升，而且改善 layout 後應下降。『系統可能有問題』沒有排他預測，無法指導下一個最小實驗。"),
        ],
        ["csapp-students", "stanford-work", "gcc", "gdb", "clang-asan", "clang-ubsan"],
    ),
    S(
        "ch1",
        1,
        "系統全景：程式的一生與抽象契約",
        "一行 `hello` 從文字檔變成螢幕上的輸出，跨過哪些層？",
        (
            "source files、headers、libraries、命令列與輸入資料",
            "可執行檔、process address space、instructions、system calls 與 I/O devices",
            "能沿著一個結果回溯到產生它的 compiler、CPU、OS 與 hardware state",
        ),
        [
            ("Translation unit", "一個 `.c` 經 preprocess 後交給 compiler 的完整輸入。", "Header 內容與 macros 展開後都成為同一 translation unit。"),
            ("ISA", "軟體可見的指令、register、資料型別與例外行為契約。", "x86-64 ISA 規定 `addq` 的可見結果，但不規定 CPU 內部有幾級 pipeline。"),
            ("Process", "執行中程式的抽象：logical control flow 加上 private-looking virtual address space。", "兩個 shell 同時啟動同一 executable，會得到兩個 process。"),
            ("System call", "User program 請 kernel 代做特權操作的受控入口。", "`write(1, buf, n)` 請 kernel 把 bytes 送到 fd 1 所代表的資源。"),
            ("Amdahl's law", "局部加速對整體速度的收益受該部分占比限制。", "只占 5% 的步驟就算快 100 倍，整體仍不可能快 20 倍。"),
        ],
        r"""
source.c + headers
   ↓ preprocess
translation unit (.i)
   ↓ compile: semantics → assembly
assembly (.s)
   ↓ assemble: instructions + symbols + relocations
relocatable object (.o) + libraries
   ↓ link
ELF executable
   ↓ shell fork/exec + loader mappings
process: virtual memory + registers + kernel resources
   ↓ fetch / decode / execute / memory / system call
observable output through terminal, file, socket, or device
""",
        r"""
### 1.A 編譯流程是資訊逐步具體化

Preprocessor 處理 textual inclusion、macros 與 conditional compilation；compiler 檢查語言語意並將高階 control/data flow 轉成 assembly；assembler 把 mnemonic 變成 instruction bytes，同時保留尚未能決定的 symbol 與 relocation；linker 合併 object files、解析 symbol、配置最終地址並產生 executable 或 shared object。每一步失敗代表不同類型的問題：找不到 header 是 preprocess/compile 邊界，型別不合是 compiler，undefined reference 則是 linker。

這條 pipeline 也解釋為何 header 不是「共用程式碼貼上器」。Header 應描述跨 translation unit 的 contract；真正 storage 或一般 function definition 通常只放一處。否則每個包含它的 `.c` 都可能產生重複 definition。

### 1.B Executable 不是 process

Executable 是 filesystem 上的 byte sequence 與 metadata；process 是 kernel 管理的執行實體。Shell 啟動程式時，先解析命令、建立必要 redirection/pipe，再經 `fork`/`execve` 或等價路徑建立新程式 image。Loader 依 ELF program headers 建立 code、data、stack、shared libraries 等 mappings，設定初始 registers，最後把控制交給 runtime startup code；`main` 不是 CPU 看到的第一條 instruction。

Process 看似獨占 CPU 與 memory，是兩個重要抽象共同造成的：context switch 讓多個 logical flows 分享 processors；virtual memory 讓每個 process 看見自己的地址空間，同時提供保護、共享與按需載入。

### 1.C Hardware organization 要以資料流理解

CPU 透過 buses/interconnect 與 main memory、I/O controllers 溝通。Instruction bytes 與 data 都先進入 memory hierarchy，再由 registers/ALU 執行。Storage 的容量與速度呈現階層：register 最快最小，cache 稍大，DRAM 更大，SSD/disk 更慢但持久。Cache 存在的根本原因，是上層使用具有 locality，而相鄰層 latency/throughput 差距很大。

當 `hello` 呼叫輸出函式時，library 可能先在 user-space buffer 聚合 bytes，接著以 system call 進 kernel；kernel 根據 file descriptor 找到 terminal/pipe/file object，driver 再與 device 溝通。每層都可能 buffer，因此「函式 return」與「人已看到／資料已持久化」不能畫等號。

### 1.D 三個核心抽象

**Files** 把不同 I/O 資源統一成 byte-oriented interface；**virtual memory** 給每個 process 一個一致地址空間並支援 protection/sharing；**processes/threads** 提供 logical control flow。抽象的價值是讓 application 不必知道每個 device 與 scheduling 細節；抽象的風險是效能或 correctness 問題會在邊界洩漏。CS:APP 的主線正是學會何時停在抽象，何時往下一層。

### 1.E Amdahl 定律與系統最佳化

若原本執行時間中比例 `p` 的部分加速 `k` 倍，總 speedup 為 `1 / ((1-p) + p/k)`。它迫使你先 profile。即使把只占 10% 的 parser 加速無限倍，整體最多約 1.11 倍。實務上還要考慮 optimization 新增的 overhead、workload 分布與 tail latency；公式不是績效保證，而是避免局部英雄主義的上限模型。
""",
        r"""
建立 `hello.c`，依序保留 `.i/.s/.o/executable`，用 `wc`、`file`、`readelf`、`objdump` 比較每階段新增或失去的資訊。再以 `strace -f -e trace=process,file,write ./hello` 觀察 loader 與輸出邊界。最後回答：`main` 前有哪些 mappings？`printf` 是否一定造成一次 `write`？

```bash
cc -E hello.c -o hello.i
cc -S -O2 hello.i -o hello.s
cc -c hello.s -o hello.o
cc hello.o -o hello
readelf -h -S -l -s -r hello
objdump -d -Mintel hello
strace -f -e trace=process,file,write ./hello
```
""",
        [
            "把 preprocess、compile、assemble、link 的錯誤全部稱為 compile error。",
            "把 executable、process 與 thread 當成同一個實體。",
            "以為 `main` 是 process 的第一條 instruction，忽略 loader/runtime startup。",
            "把 library call return 誤解成 device 已完成或資料已 durable。",
            "沒有 profile 就最佳化最顯眼的函式，忽略 Amdahl 上限。",
        ],
        [
            ("為何 object file 中可以存在尚未知道地址的 function call？", "Assembler 知道要產生哪一類 instruction，卻未必知道 target 最終放在哪裡，因此先在欄位放 placeholder，並建立 relocation entry，記錄位置、symbol 與修補種類。Linker 配置所有 sections 後，再計算 absolute 或 PC-relative value 寫回。"),
            ("Executable 與 process 最關鍵的差異是什麼？", "Executable 是靜態 artifact；process 是某次執行的動態 state，包括 registers、virtual mappings、open files、signal disposition、credentials 與 scheduling state。同一 executable 可同時對應很多 process，而 process 也可用 `execve` 保留 identity 卻換掉 program image。"),
            ("為何 `printf(\"x\\n\")` 不保證只呼叫一次 `write`？", "stdio 是 library-level buffering abstraction；是否 flush、切成幾次 write，會受 stream mode、buffer state、輸出目的地與 implementation 影響。即使一次 write 成功，也只表示 kernel 接受相應 bytes，不一定表示 terminal 已顯示或 disk 已持久化。"),
            ("ISA 與 microarchitecture 為何必須分開？", "ISA 是 binary 對 CPU 的可見 contract，讓同一 executable 可在不同實作上得到相容語意；microarchitecture 是 pipeline、cache、execution units、prediction 等內部設計。效能分析需要理解後者，但 correctness 不能依賴未承諾的內部時序。"),
            ("Process 如何同時提供『獨占 CPU』與『獨占 memory』的錯覺？", "Scheduler 保存／恢復 architectural state，讓每個 logical control flow 輪流使用 CPU；MMU 與 page tables 將各 process 的 virtual addresses 映射到不同 physical frames，並檢查權限。兩者都是受控 multiplexing，不是真正物理獨占。"),
            ("Amdahl 定律為何不等於『小函式不用最佳化』？", "它只描述給定 workload 下的總體上限。小函式可能在其他 workload 成為熱點，也可能影響 tail latency、energy 或 capacity；安全性修正更不由 speedup 決定。正確結論是先定義目標、量測占比，再比較收益與複雜度。"),
            ("要證明一次輸出經過哪些層，最小證據鏈是什麼？", "保留各編譯 artifact 證明 source 到 executable；用 ELF 工具確認 entry/mappings；用 debugger 看 startup 到 `main`；用 `strace` 看 write-like system calls；必要時再用 packet/device trace。每一工具只證明相鄰邊界，組合後才形成端到端因果鏈。"),
        ],
        ["csapp-students", "csapp-asides", "gcc", "binutils", "linux-man"],
    ),
    S(
        "ch2",
        2,
        "資訊表示：有限位元、整數與浮點的完整模型",
        "同一串 bits 為何可以是負數、地址、字元或 NaN？",
        (
            "固定寬度 bit pattern 與一個型別／操作語境",
            "依 encoding、conversion 與 arithmetic 規則得到值或例外狀態",
            "能預測 overflow、cast、shift、endianness 與 IEEE 754 rounding",
        ),
        [
            ("Bit pattern", "固定數量 0/1；本身沒有 signed、float 或 pointer 等高階意義。", "`0xffffffff` 可依型別解讀成 unsigned 4294967295 或 two's-complement -1。"),
            ("Two's complement", "現代機器常用的 signed integer encoding，最高位權重為負。", "8-bit `11111110₂` 表示 -2。"),
            ("Modulo arithmetic", "固定 w-bit unsigned operation 等價於對 `2^w` 取模。", "8-bit 255 + 1 wrap 成 0。"),
            ("IEEE 754", "浮點 format 與運算的標準，包含 sign、exponent、fraction、特殊值與 rounding。", "binary32 的 1.5 編碼為 sign 0、biased exponent 127、fraction `1000...`。"),
            ("Endianness", "多 byte scalar 在 memory 中的 byte 排列順序。", "little-endian 將最低有效 byte 放在較低地址。"),
        ],
        r"""
mathematical value
   ↓ choose finite representation width w
bit pattern ── interpretation context ──> unsigned / signed / float / bytes
   ↓ memory layout
byte order + alignment
   ↓ C expression rules
promotion → common type → operation → truncation / rounding
   ↓
representable result, wraparound, infinity/NaN, or undefined behavior
""",
        r"""
### 2.A 從十六進位到 memory bytes

十六進位每一位對應 4 bits，因此是閱讀 memory 與 instruction 的共同速記。先區分「數值的高低位」與「記憶體的高低地址」：endianness 只決定 multi-byte object 的 bytes 如何排列，不會把單一 byte 裡的 bit 順序反轉。Network protocols 常指定 big-endian；host code 應使用明確 decode/encode，而不是把外部 bytes 強制 cast 成 struct pointer，否則會同時踩到 alignment、padding、endianness 與 aliasing。

```c
uint32_t decode_be32(const unsigned char b[4]) {
    return ((uint32_t)b[0] << 24) |
           ((uint32_t)b[1] << 16) |
           ((uint32_t)b[2] << 8)  |
            (uint32_t)b[3];
}
```

Cast 在 shift 前完成很重要：先提升到足夠寬的 unsigned type，才能避免 `int` 範圍與 sign extension 介入。

### 2.B Unsigned 與 signed 是兩個值域

w-bit unsigned 範圍是 0 到 `2^w-1`，加減乘以 modulo `2^w` 定義；two's-complement signed 範圍是不對稱的 `-2^(w-1)` 到 `2^(w-1)-1`。因此最小負數沒有對應的正值，`-INT_MIN` 在相同 signed type 會 overflow。C 對 unsigned overflow 定義為 wrap，對 signed overflow 則是 UB；不能把兩者混為一談。

混合 signed/unsigned expression 最危險之處，是 negative signed 值可能先轉成巨大 unsigned。安全檢查應先讓 domain 一致。例如長度、容量與 index 常使用 `size_t`，但外部輸入要在轉成 `size_t` 前驗證非負；兩個 size 相加要用 `if (a > SIZE_MAX - b)` 先檢查。

### 2.C Shift、mask 與 bit-level invariant

Mask 是保留或修改特定位的工具，但首先要寫出 bit layout。`x & (a-1)` 只有在 `a` 是 2 的冪時等價於 `x % a`；alignment up 可寫成 `(x + a - 1) & ~(a - 1)`，但加法本身要先檢查 overflow。Left shift negative value、shift count 大於等於 type width 等情況可能是 UB；signed right shift 的細節也不應拿來當 portable protocol logic。實務上以固定寬度 unsigned type 做 bit manipulation。

### 2.D Floating point 不是『帶小數的整數』

IEEE 754 binary floating point 使用 `(-1)^s × M × 2^E`。Normalized number 用 implicit leading 1 提高 precision；subnormal 在接近 0 時改用固定最小 exponent 與沒有 implicit 1 的 significand，提供 gradual underflow。Exponent 全 1 代表 infinity 或 NaN；正負零有不同 sign bit，但一般數值比較相等。

有限 precision 代表大多數十進位小數無法精確表示。每次 operation 先得到理想實數結果，再依 rounding mode 映射回 format；預設 round-to-nearest, ties-to-even 可降低累積 bias。Floating addition 不具 associativity：`(a+b)+c` 與 `a+(b+c)` 可能因中間 rounding 不同而不等。這會影響 compiler reassociation、parallel reduction 與 reproducibility。

### 2.E 用誤差模型而不是 `==` 恐慌

不是所有 float 都不能比較：與 0 或由相同 deterministic path 產生的離散 sentinel 可能合理；但量測與數值演算法通常需要 absolute/relative tolerance，並處理 NaN、infinity 與尺度接近 0 的情況。Kahan summation、pairwise reduction 或更高 precision accumulator 能降低誤差，但代價是 instructions、vectorization 與 reproducibility trade-off。

### 2.F 表示與安全

很多 security bug 都是 representation boundary：封包長度轉型、乘法計算 allocation、pointer difference 截短、sentinel 與 valid value 混用。固定流程是：以明確寬度 decode → 驗證 protocol range → checked arithmetic → 轉成內部 type → allocation/use。不要先做可能 wrap 的算術，再看結果是否小於上限。
""",
        r"""
寫一個程式列印 `int32_t(-1)`、`uint32_t(-1)`、`1.0f/10.0f` 的 bytes，並用 `memcpy` 而非 pointer punning 取得 bit pattern。再實作 `checked_size_add` 與 big-endian decoder，使用 `UINT32_MAX`、`SIZE_MAX`、負輸入與 NaN 測邊界。最後用 Python `struct` 交叉核對 binary32 的 sign/exponent/fraction。

```c
bool checked_size_add(size_t a, size_t b, size_t *out) {
    if (a > SIZE_MAX - b) return false;
    *out = a + b;
    return true;
}
```
""",
        [
            "把 endianness 說成每個 byte 內的 bits 反轉。",
            "在 signed 與 unsigned 混合比較前沒有寫出 common type。",
            "先做可能 overflow 的加法或乘法，再檢查結果。",
            "把 IEEE 754 說成純科學記號，忽略 subnormal、NaN 與 rounding。",
            "以任意 epsilon 比較所有尺度的浮點值，沒有定義誤差模型。",
        ],
        [
            ("為何 sign extension 複製最高位能保持 two's-complement 值？", "w-bit 值的最高位權重是 `-2^(w-1)`。擴成 w+k bits 時，複製的 k 個 1 與新的負最高位合起來，總權重恰好仍等於原本的負權重；若原最高位是 0，補 0 也不改值。因此它不是圖形技巧，而是位權代數的結果。"),
            ("`x < 0` 為何可能在與 unsigned 比較時永遠 false？", "Usual arithmetic conversions 可能先把 signed `x` 轉成 unsigned common type。Negative value 會以 modulo `2^w` 對應成很大的 unsigned 值，再與 0 比較，自然不小於 0。要先驗證 signed domain，或顯式轉到能表示雙方值域的型別。"),
            ("為何 `INT_MIN / -1` 是特殊邊界？", "Two's-complement 正範圍比負範圍少一個值，`abs(INT_MIN)` 無法由同寬 signed type 表示。數學結果超出範圍，在 C signed division 中屬未定義行為。Checked arithmetic 必須把這一對 operand 單獨處理。"),
            ("Subnormal number 解決什麼問題？", "若 normalized format 在最小 exponent 後直接跳到 0，接近 0 的間距會突然產生巨大缺口。Subnormal 固定 exponent 並逐步縮小 significand，讓 underflow 漸進發生，代價是較少 effective precision，某些硬體上也可能較慢。"),
            ("為何 NaN 不等於自己？", "IEEE 754 將 ordered comparisons 遇到 NaN 設為 false，用來讓未定義數值狀態不被誤當普通數字。檢查 NaN 應使用 `isnan`，而不是 `x == NAN`。排序或 serialization 還要自行定義 NaN placement 與 payload policy。"),
            ("為何 floating addition 不具 associativity，這對 parallel reduction 有何影響？", "每一步加法都需 rounding；改變 grouping 便改變中間量的尺度與捨入誤差。Parallel tree reduction 與 sequential left fold 的順序不同，所以低 bits 可能不同。若需要 reproducibility，要固定 reduction tree、使用 pairwise/Kahan 或更高 precision，並接受效能代價。"),
            ("安全解析 32-bit network length 的順序是什麼？", "先由 bytes 明確 decode 成 `uint32_t`，驗證 protocol maximum，再轉成 `size_t`；接著對 header、element count 與 payload 使用 checked add/multiply，最後才 allocation。每一 boundary 都要定義 0、最大值與拒絕策略，避免 wrap 後配置過小 buffer。"),
        ],
        ["csapp-asides", "csapp-errata", "posix", "gcc"],
    ),
    S(
        "ch3",
        3,
        "機器級程式：從 ABI 還原資料流與控制流",
        "Assembly 沒有變數名稱與高階型別時，如何看懂程式真正做什麼？",
        (
            "compiler 產生的 x86-64 instructions、registers、stack 與 memory",
            "依 ISA 與 ABI 重建 values、branches、procedure calls 與 data layout",
            "能從 disassembly 解釋 C 語意、效能與 memory-safety 風險",
        ),
        [
            ("Register", "CPU 可直接操作的少量 architectural storage；名稱與寬度由 ISA 定義。", "`rax/eax/ax/al` 是同一 register 的不同寬度視圖。"),
            ("Calling convention", "Caller/callee 對參數、回傳值、保存 registers 與 stack alignment 的共同規則。", "System V AMD64 的前幾個 integer/pointer arguments 放在指定 registers。"),
            ("Addressing mode", "由 base、index、scale、displacement 計算 effective address 的公式。", "`8(%rdi,%rsi,4)` 對應 `rdi + rsi*4 + 8`。"),
            ("Condition code", "算術或比較 instruction 留下的狀態，供 branch 或 conditional move 使用。", "`cmp b,a` 設 flags，`jl` 依 signed less-than 條件跳轉。"),
            ("Stack frame", "某次 procedure activation 為 local state、saved registers 與 call linkage 使用的 stack 區域。", "Recursive call 每次都有自己的 return address 與 locals。"),
        ],
        r"""
C types / control flow
   ↓ compiler lowering
instructions operate on registers and memory
   ├─ data flow: mov / lea / arithmetic / vector
   ├─ control flow: flags → jump / cmov / call / ret
   └─ address flow: base + index×scale + displacement
procedure boundary
   ├─ arguments / return registers
   ├─ caller-saved vs callee-saved
   └─ aligned stack + return address
memory layout
   └─ arrays / structs / unions / padding / buffers
""",
        r"""
### 3.A 不要逐行翻譯，要先標資料角色

Assembly 閱讀的最小單位不是 instruction，而是「一段 control-flow region 中的資料流」。先標出 function arguments、return register、loop index、accumulator、pointer 與 bound，再畫 basic blocks 和 edges。Compiler 會消除 source variable、合併 expressions、重排無副作用操作，因此逐行硬對 C 常造成誤解。

AT&T 與 Intel syntax 的 operand order、register/memory notation 不同，但 underlying instruction semantics 相同。選一種作為主視角，遇到另一種先確認 source/destination，不要同時背兩套表面符號。

### 3.B Data movement 與寬度

Instruction suffix/operand width 決定讀寫幾 bytes。x86-64 寫 32-bit general register 會把上半部清零；較窄寫入則可能保留高位。Zero extension 與 sign extension 對應 unsigned/signed widening。`lea` 計算 effective address 但不讀該地址的 memory，也不改 condition codes，因此 compiler 常把它當成 scaled arithmetic。

Memory operand 最終是地址公式。看到 `(%rdi,%rsi,8)`，先問 `rdi` 是否 base pointer、`rsi` 是否 index、8 是否 element size；這通常比查 instruction 表更快重建 array access。

### 3.C Control flow：signed 與 unsigned branch 不可混

`cmp src,dst` 以 `dst-src` 設定 flags，不保存結果。後續 `jl/jg` 解讀 signed overflow/sign/zero，`jb/ja` 解讀 carry/zero，對同一 bit pattern 可能得出不同關係。Conditional move 可避免 branch misprediction，但會計算兩條路徑的候選值，只有在 expression 安全、工作量小且 dependency 合理時才有利。

Loop 通常被 lowering 成 test + back edge；`switch` 在 case 密集時可能用 jump table，稀疏時則是 decision tree。辨識 jump table 要追 index range check、table base 與 indirect jump，不能把 data bytes 誤當 code。

### 3.D Procedure call 與 System V AMD64 ABI

`call` 保存下一條 instruction 的 return address並跳轉；`ret` 取回它。ABI 規定哪些 registers 由 caller 視為易失、哪些 callee 使用後必須恢復；stack 在 call boundary 需符合 alignment，variadic functions 還有額外規則。Leaf function 或最佳化後 function 未必建立傳統 frame pointer；因此「每個函式一定 `push rbp`」只是教學模板，不是 contract。

Stack 向低地址成長是常見 x86-64 layout，但圖的上下不等於地址語意。每畫一次 stack，都標明 high/low address、`rsp` 目前位置、return address 與 object bounds。

### 3.E Arrays、structs、unions 與 alignment

Array 是連續同型別 elements，index scaling 直接反映 element size；multi-dimensional C array 以 row-major 儲存，編譯器需要除第一維外的 dimensions 來算 stride。Struct 依 member order 加入 padding 以滿足 alignment，整體 size 通常也補到最大 alignment 的倍數，讓 struct array 中每個 element 合法對齊。Union members 共用 storage，size 至少容納最大 member；讀取非 active representation 涉及語言規則，不能把它當通用 type punning。

### 3.F Buffer overflow 與防禦是攻防鏈

Stack overflow 可覆蓋 adjacent locals、saved state 或 return address；現代系統用 stack canary、NX、ASLR、PIE、shadow stack、control-flow protection 等增加利用難度。它們不是 memory safety：越界仍可能洩漏或破壞資料，ROP 也利用既有 executable snippets 繞過 NX。根本修正是界限正確、長度 checked、使用 memory-safe abstraction；mitigations 是 defense in depth。

### 3.G Floating-point 與 vector code

現代 x86-64 多以 XMM/YMM 等 registers 執行 scalar/vector floating point。ABI 對 floating arguments/returns 另有 register 規則。SIMD instruction 同時處理多個 lanes，但需要處理 alignment、tail elements、aliasing 與 reduction order；看到 vectorized assembly 時，要把 lane width、unroll factor 與 scalar cleanup loop 一起重建。
""",
        r"""
用一個包含 `switch`、struct array、遞迴與 dot product 的小程式，分別以 `-O0`、`-O2 -fno-omit-frame-pointer`、`-O3 -march=native` 產生 assembly。對每個版本畫 control-flow graph，標記 argument/register roles，並用 GDB 在 call 前後比較 `rsp`、return address 與 callee-saved registers。

```bash
cc -O2 -g -fno-omit-frame-pointer -S -masm=intel machine.c
objdump -drwC -Mintel machine.o
gdb ./machine
(gdb) layout asm
(gdb) info registers
(gdb) x/24gx $rsp
```
""",
        [
            "逐行把 assembly 翻回 C，沒有先建立 register role 與 basic blocks。",
            "把 `lea` 一律理解為 memory load。",
            "用 signed branch 解讀 unsigned length 或反過來。",
            "假設每個 function 都有固定 stack-frame 模板。",
            "只談 exploit，沒有回到 object bounds 與安全介面。",
        ],
        [
            ("為何寫入 `eax` 會影響整個 `rax`？", "x86-64 規定 32-bit general-register write 會把對應 64-bit register 的高 32 bits 清零。這提供免費 zero extension，也避免部分 register dependency。寫 `ax` 或 `al` 不具同樣完整清零語意，因此閱讀後續 64-bit use 時要追高位來源。"),
            ("`lea` 與 `mov` 使用相同地址公式時差在哪？", "`mov` 的 memory form 會以公式得到地址並讀/寫該處資料；`lea` 只把公式計算出的數值放入 register，不存取 memory，也通常不改 flags。Compiler 因此可用 `lea` 實作 `x + 4*y + c`。"),
            ("Caller-saved 與 callee-saved registers 如何合作？", "Caller-saved 的值若跨 call 仍需要，caller 要先保存；callee 可自由覆寫。Callee-saved 則由 callee 在使用前保存、return 前恢復，使 caller 可假設值跨 call 不變。兩者讓常見 short-lived values 少付保存成本，同時保留長生命值的穩定位置。"),
            ("為何最佳化後可能看不到 stack frame？", "若 function 是 leaf、locals 可全放 registers、或 tail call 消除了普通 return linkage，就不需傳統 frame。Compiler 也可省略 frame pointer，把 `rbp` 當一般 register，透過 unwind metadata 除錯。ABI 約束的是可見 contract，不是固定 prologue 模板。"),
            ("Struct member 重排為何會改 size？", "每個 member 起始地址要滿足 alignment，compiler 會在前一 member 後插 padding；struct 尾端也需補齊，讓 array 中下一個 element 的最大 alignment 合法。把寬 alignment member 放前面常減少洞，但會改 ABI、serialization 與外部 layout contract。"),
            ("Stack canary、NX 與 ASLR 各阻止什麼？", "Canary 嘗試在 return 前偵測某類 stack overwrite；NX 讓資料頁不可直接執行，阻止傳統 injected code；ASLR 隨機化位置，提高猜測 code/data address 的成本。三者都不阻止越界本身，也不保證資料不被修改或洩漏。"),
            ("如何由 assembly 判斷 loop 是否 vectorized？", "尋找 packed SIMD instructions、每次處理多個 elements 的 pointer increment、vector accumulator，以及處理 `n % lanes` 的 scalar remainder。再檢查 compiler vectorization report與 benchmark，因為看到 SIMD 不代表整體一定更快，load bandwidth 或 reduction dependency 仍可能主導。"),
        ],
        ["csapp-changes", "sysv-abi", "intel-sdm", "binutils", "gdb", "clang-asan"],
    ),
    S(
        "ch4",
        4,
        "處理器架構：從 sequential datapath 到 pipeline control",
        "CPU 如何讓多條指令重疊執行，又維持 ISA 看起來像依序完成？",
        (
            "instruction bytes、architectural state 與 memory responses",
            "透過 combinational logic、state elements、pipeline registers 與 control policy更新可見狀態",
            "能由 dependency 與結果可用時間推導 forwarding、stall、bubble 與 misprediction",
        ),
        [
            ("Architectural state", "ISA 對程式可見的 registers、PC、condition codes 與 memory。", "兩顆不同微架構 CPU 只要更新出相同 architectural state，就能執行同一 binary。"),
            ("Combinational logic", "輸出由當前輸入決定、不自行記住歷史的電路。", "ALU 根據 operands 與 function code 計算結果。"),
            ("Sequential state", "在 clock edge 保存狀態供下一 cycle 使用的元件。", "Register file、PC 與 pipeline register。"),
            ("Hazard", "重疊執行使下一條 instruction 尚無法安全取得正確資料或控制方向。", "緊接 load 的 consumer 在 data 尚未回來時形成 load-use hazard。"),
            ("Precise exception", "出錯指令以前像已完成、以後像未完成的可恢復可見狀態。", "Page fault handler 返回後可重新執行 faulting instruction。"),
        ],
        r"""
ISA instruction
  ↓ fetch bytes at PC
decode operands / register ids
  ↓
execute ALU / effective address / branch condition
  ↓
memory access (when needed)
  ↓
write back architectural destination
  ↓
select next PC

pipeline: F | D | E | M | W overlap across instructions
control: forwarding ─ stall ─ bubble ─ redirect ─ exception priority
""",
        r"""
### 4.A 先從 sequential model 建立 correctness

Sequential datapath 可把一條 instruction 分成 fetch、decode、execute、memory、write-back、PC update。所有 combinational computation 在一個長 cycle 內完成，clock edge 才提交 state。它容易理解，但 clock period 被最慢 instruction path 限制，而且大量硬體在每條 instruction 的某些階段閒置。

Y86-64 的價值不是成為另一套要背的 ISA，而是把 x86-64 簡化到能完整追 control signal、datapath 與 exception。學習時每條 instruction 都回答：讀哪些 state、經過哪些 function、寫哪些 state、下一個 PC 從哪來。HCL 類描述是在表達硬體 mux/control 邏輯，不是依序執行的 C code。

### 4.B Pipeline 提升 throughput，不必降低單條 latency

把長 datapath 切成 stages 並加入 pipeline registers，允許不同 instructions 同時位於不同 stages。理想狀況每 cycle 完成一條，throughput 上升；但單條 instruction 還要穿越所有 stages，甚至因 registers 增加 latency。Clock period 受最慢 stage 加 register overhead 限制，所以切得越細不一定越好。

### 4.C Data hazard 要看『何時產生、何時需要』

若 instruction B 讀 instruction A 尚未寫回的結果，就有 RAW dependency。Forwarding 不必等值寫回 register file，而是從較晚 stage 的 pipeline register 直接送到 consumer input。能否救援取決於 producer result 何時 available、consumer 在哪個 stage need。ALU result 常可由 E/M forwarding；load data 到 M 結尾才產生，若下一條在 E 立刻使用，仍需一 cycle stall，並在 execute path 插 bubble。

WAR/WAW 在簡單 in-order pipeline 通常不形成相同問題，因 reads/writes 的順序固定；在 out-of-order processor 則需要 register renaming 等機制。這說明 hazard 分類必須連到 microarchitecture。

### 4.D Control hazard 與 speculation

Branch 的 next PC 可能到 execute 才知道；如果停等，每個 branch 都浪費 cycles。Predictor 先猜方向/target，frontend 沿預測 path fetch；猜對就保留工作，猜錯則 flush younger instructions、恢復正確 PC。Speculative instructions 不應留下不可回復的 architectural effects，但 microarchitectural state（cache、predictor）可能已改變，這也形成 side-channel security 的背景。

簡化教材常採 predict-taken 或 predict-not-taken；現代 CPU 使用 history、target buffer、return stack 等複雜 predictor。不要把教材 pipeline 當現代 CPU 全貌，但它提供推導 dependency 與 penalty 的最小模型。

### 4.E Pipeline control 必須處理多事件優先權

同一 cycle 可能同時看到 load-use hazard、misprediction、return 與 exception。Control logic 必須規定哪些 stage stall、哪些 bubble、PC 選哪個來源，並保證錯路徑或出錯後的 instructions 不更新 state。好的推理方式是先寫 invariant：若 instruction 最終不應提交，任何 register/memory write control 在抵達 commit point 前必須被取消。

### 4.F Exceptions 與 precise state

Exception 可能由 instruction 直接造成，也可能由外部 interrupt。Pipelined machine 同時有多條 in-flight instructions，必須選擇最老、應先被觀察的 exception，阻止 younger state updates，並把 faulting PC/cause 交給 handler。Precise exception 讓 OS 可以把 page 載入後重新執行，或向 process 發 signal；若 state 半提交，軟體恢復會極度困難。

### 4.G 從教材 CPU 接到真實效能

Superscalar/out-of-order CPU 可每 cycle issue 多條 instructions，以 reorder buffer 維持看似 in-order retirement；register renaming 消除 false dependencies；load/store queue 處理 memory ordering。即使不深入電路，CS:APP 的 CPE、dependency chain、branch prediction 與 cache miss 都可由這些概念理解：效能不是 instruction 數單一變數，而是可平行工作與 critical path 的結果。
""",
        r"""
手動畫五級 pipeline table，使用 `load → add → conditional branch → store` 序列。對每個 cycle 標出 stage、operand 來源、forward path、stall/bubble 與 branch redirect。再寫一個 Python 小模擬器，讓每條 instruction 宣告 `produces_at` 與 `needs_at`，自動判斷是否需 stall；改變 load latency 觀察結果。

另外以 `perf stat -e cycles,instructions,branches,branch-misses` 比較可預測與隨機 branch loop，將 CPI 差異連回 flush cost，而不是只說「branchless 比較快」。
""",
        [
            "把 pipeline 說成讓單一 instruction 必然更快，混淆 latency 與 throughput。",
            "只背 forwarding 規則，沒有追 producer availability 與 consumer need time。",
            "用教材五級 pipeline 解釋所有現代 CPU 細節。",
            "忽略 mispredicted path 對 cache/predictor 等 microarchitectural state 的影響。",
            "處理 exception 時只看 faulting instruction，沒有阻止 younger writes。",
        ],
        [
            ("Pipeline 為何提高 throughput 卻可能增加單條 instruction latency？", "Stages 可讓多條 instructions 重疊，所以穩態完成率提高；但每條 instruction 必須跨更多 pipeline registers，每個 register 有 clock-to-Q、setup 與 skew overhead。若切分不平衡，最慢 stage 仍限制 clock，單條總 cycles 也可能增加。"),
            ("為何 forwarding 無法消除緊鄰 load-use hazard？", "Consumer 通常在 execute stage 開始時需要 operand，而 load data 要到 memory stage 結尾才返回；同一 cycle 內時間方向來不及把結果送回較早需求點。Stall 一 cycle 後，consumer 的 need time 延後，才可 forwarding。"),
            ("Stall 與 bubble 的差異是什麼？", "Stall 讓某 pipeline register 保持原內容，使該 instruction 留在原 stage；bubble 則向 stage 注入一個不改 architectural state 的 nop-like control。處理 load-use 時常 stall fetch/decode，同時在 execute 插 bubble，讓 producer 前進而 consumer 等待。"),
            ("Branch prediction 猜錯時為何不能只改 PC？", "錯路徑 instructions 已被 fetch/decode，甚至進入 execute；若只 redirect PC，它們仍可能寫 register 或 memory。必須 invalidate/flush younger work，確保只有正確 path 更新 architectural state，並從正確 target 重新填 pipeline。"),
            ("Precise exception 的『精確』指什麼？", "在 handler 看來，faulting instruction 以前的 instructions 已完整生效，faulting 與以後的 instructions 尚未產生不可撤銷 effects。這建立一個乾淨 restart/termination boundary，使 OS 能 demand-page、deliver signal 或除錯。"),
            ("Out-of-order execution 如何仍看起來依序？", "Frontend 將 operations 放入 queues，ready 的可先執行；結果先存於 physical registers/reorder buffer，不立刻改 architectural state。Retirement 依 program order 提交，若 older instruction 出錯就丟棄 younger speculative results。"),
            ("為何 branchless code 不一定更快？", "Conditional move 或 mask 可能讓兩邊工作都執行、拉長 dependency chain、阻礙 vectorization，且原 branch 可能高度可預測。應比較輸入分布下的 cycles、instructions、branch misses 與 critical path，而不是把無 branch 當普遍優化。"),
        ],
        ["csapp-changes", "csapp-asides", "intel-sdm", "csapp-labs"],
    ),
]
