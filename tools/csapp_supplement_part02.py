"""Deepening content for CS:APP chapters 5–9."""
from csapp_supplement_model import S


SUPPLEMENTS = [
    S(
        "ch5",
        5,
        "程式效能：從正確量測到 critical path",
        "程式慢究竟是工作太多、平行度不足，還是資料到得太晚？",
        (
            "一個定義清楚且可重現的 workload、正確程式與目標 metric",
            "以 profile、CPE、hardware counters 與實驗隔離 algorithm、CPU、memory、I/O 成本",
            "得到可驗證的改善，並保留 correctness、可讀性與 portability",
        ),
        [
            ("CPE", "Cycles per element；用來描述 steady-state loop 每處理一個元素的平均 CPU cycles。", "長度 n 的 dot product 可用時間對 n 的斜率估計 CPE。"),
            ("Critical path", "因 dependency 必須依序完成、決定最低可能 latency 的操作鏈。", "單一 accumulator 的 `sum += a[i]` 形成 loop-carried dependency。"),
            ("Throughput bound", "Execution units 或 memory 每 cycle 最多完成多少操作所形成的上限。", "兩個 load ports 會限制每 cycle 可供應的 loads 數。"),
            ("Aliasing", "兩個 pointer 可能指到重疊 storage，使 compiler 必須保守保留讀寫順序。", "`dst` 可能與 `src` 重疊時，某些 vectorization 不合法。"),
            ("Benchmark hygiene", "控制 warm-up、input、compiler、CPU frequency、noise 與統計方法的量測紀律。", "固定 workload，多次執行並報 median/p95，而非挑最快一次。"),
        ],
        r"""
correctness + representative workload
   ↓ baseline measurement
wall time / throughput / latency distribution
   ↓ profile: where is time spent?
hot region
   ↓ explain with model
algorithmic work ─ instruction count ─ dependency/ILP
cache/TLB/bandwidth ─ branches ─ syscalls/I/O
   ↓ change one cause
re-run correctness + counters + end-to-end metric
   ↓ keep only improvements with evidence
""",
        r"""
### 5.A 先定義「快」對誰有價值

Batch job 可能關心 total runtime 與 cost；online service 關心 p50/p99 latency、throughput 與 CPU capacity；interactive tool 還在意 startup。若 workload、input distribution 與 metric 沒有先固定，任何 optimization 都可能只是換一個數字。先建立 baseline、correctness oracle、環境資訊與 variance，再改 code。

Wall-clock time 是最終使用者感受，但不能直接解釋原因。Profile 告訴時間落在哪些 call stacks；hardware counters 提供 cycles、instructions、branches、cache/TLB events 等線索；assembly 與 compiler reports 再說明 code generation。工具形成由症狀到機制的證據鏈，不應跳過中間直接看一個 counter 下結論。

### 5.B 最高收益通常來自少做工作

改善演算法 complexity、避免重複 conversion/allocation、把 loop-invariant computation 移出迴圈、批次化 calls，通常比 instruction trick 更穩定。Amdahl 定律提醒先處理占比；但也要看 tail path，因平均 profile 可能稀釋少量極慢 requests。

Procedure call 本身未必昂貴，真正問題常是 call 阻止 optimization、重複 boundary check 或藏著不可見工作。Inlining 可以打開 constant propagation/vectorization，也增加 code size 與 instruction-cache pressure。應依 profile 與 compiler output 判斷，而非一律加 `inline`。

### 5.C Compiler 的邊界：memory alias 與 observable behavior

Compiler 必須保留 C abstract machine 可觀察語意。若每次 loop 都從 pointer 讀 accumulator，compiler 可能擔心其他 pointer alias 該位置，無法把值長留 register。把 local accumulator 放 register-like scalar，最後寫回，常能消除不必要 loads/stores；使用 `restrict` 則是 programmer 對 no-alias 的強 contract，違反會造成 UB。

Function call、volatile access、可能 trap 的 operation、floating-point rounding/errno 規則也會限制重排。看不到 optimization 時，先讀 vectorization/optimization report，找 compiler 缺少的 proof，而不是直接改寫成難懂 code。

### 5.D CPE、dependency chain 與多 accumulator

對長 loop，執行 cycles 常可近似 `C = a + b·n`，斜率 b 是 CPE。Loop unrolling 降低 branch/index overhead，也暴露更多 independent operations。若 reduction 只有一個 accumulator，下一次 add 要等前一次完成，critical path 受 operation latency 限制；使用多個 accumulators 讓 execution units 重疊，最後再合併，可接近 throughput bound。

```c
double sum4(const double *a, size_t n) {
    double s0=0, s1=0, s2=0, s3=0;
    size_t i=0;
    for (; i+3<n; i+=4) {
        s0 += a[i]; s1 += a[i+1];
        s2 += a[i+2]; s3 += a[i+3];
    }
    for (; i<n; ++i) s0 += a[i];
    return (s0+s1) + (s2+s3);
}
```

對 integer 在無 overflow/已定義 modulo 語意下 reassociation 較直接；floating point 會改變 rounding，因此可能改結果。Optimization 必須連回 numerical contract。

### 5.E Branch、SIMD 與 memory system

不規則 branch 的 penalty 來自 predictor error 與 pipeline recovery；若 branch 高度可預測，branchless 版本可能多做工作。SIMD 增加每條 instruction 的資料平行度，但前提是 contiguous/aligned-enough access、alias proof、無複雜 dependency，並處理 tail。當 working set 超過 cache 或 stream 已飽和 memory bandwidth，再增加 ALU 平行度不會改善。

Roofline 式思考可把 performance 限制分成 compute throughput 與 memory bandwidth：每 byte 做的 operations 太少時是 bandwidth-bound；反之可能 compute-bound。即使不畫正式 roofline，也要同時問「搬了多少 bytes」與「做了多少 useful operations」。

### 5.F Benchmark 要對抗自我欺騙

避免 dead-code elimination，消費結果；先 warm cache/JIT（若適用），也要另測 cold-start；固定 CPU affinity/frequency 只是降低 noise，不是 production 真相；多次量測並保留 distribution；記錄 compiler flags 與 binary。Microbenchmark 證明局部機制，最後仍需 end-to-end workload 驗證，因 code size、allocator、scheduler 與 I/O 交互可能抵消收益。
""",
        r"""
選一個 array reduction，寫 baseline、hoist、unroll、four-accumulator 與 compiler auto-vectorized 版本。先用 property test 確認結果（浮點使用明確 tolerance），再對多個 n 量測時間並估 CPE；搭配 `perf stat` 看 cycles、instructions、IPC、branch-misses、cache-misses。最後故意把 input 放大超過 LLC，觀察瓶頸由 execution 轉向 memory。

```bash
cc -O3 -march=native -g -fopt-info-vec-all reduce.c -o reduce
perf stat -r 10 -e cycles,instructions,branches,branch-misses,cache-misses ./reduce
perf record -g ./reduce && perf report
```
""",
        [
            "只報一個平均時間，沒有 workload、variance、compiler 與硬體資訊。",
            "先看 assembly 猜瓶頸，沒有先找 end-to-end hot region。",
            "把較少 instructions 當成一定較快，忽略 dependency 與 cache。",
            "使用 `restrict` 或 fast-math，卻沒有接受其 correctness contract。",
            "Microbenchmark 變快後未回到 production-like workload 驗證。",
        ],
        [
            ("為何 loop unrolling 本身不保證降低 CPE？", "它能減少 loop control overhead並暴露 independent work，但若主體受單一 accumulator dependency、memory latency/bandwidth 或 execution-unit throughput 限制，只複製同一依賴鏈不會突破 critical path；還可能增加 code size與 register pressure。"),
            ("多 accumulator 為何能改善 reduction？", "每個 accumulator 形成獨立 dependency chain，CPU 可讓多個 add 同時 in flight，將限制從單一 operation latency 移向 add units 的 throughput。最後合併有額外成本，對短 array 可能不划算；浮點 grouping 也會改 rounding。"),
            ("IPC 上升為何不一定代表使用者效能變好？", "IPC 是每 cycle retired instructions，可能因程式做了更多低價值 instructions 而上升；wall time 還受總 cycles、frequency、I/O 與 workload 影響。應以目標 latency/throughput 為主，IPC 只用於解釋原因。"),
            ("Compiler 為何因 aliasing 拒絕 vectorize？", "若 stores 可能覆蓋未來 loads，將多個 iterations 同時執行會改變 observable order。Compiler 沒有 no-overlap proof 時必須保守；可透過介面設計、local copies、runtime alias checks 或正確的 `restrict` contract 提供證明。"),
            ("什麼情況下 branchless code 反而較慢？", "原 branch 高度可預測、兩條路徑工作差異大、branchless 需執行昂貴的兩邊、增加 dependency 或 load，或妨礙 vectorization時。量測要使用真實 input distribution，而不是只用隨機資料偏袒某版本。"),
            ("如何分辨 compute-bound 與 memory-bound？", "改變 arithmetic intensity、working-set size與 memory layout；觀察 IPC、cache misses、bandwidth與 vector unit utilization。若減少算術幾乎不變、blocking/contiguous layout 有效且 bandwidth 接近平台上限，多半 memory-bound；若資料在 cache 而 execution ports 飽和，則偏 compute-bound。"),
            ("為何 `-O3 -march=native` 的結果不能直接代表可部署版本？", "`-march=native` 可能使用 build machine 才有的 ISA，部署到較舊 CPU 會 illegal instruction；`-O3` 也可能增加 code size或改浮點策略。應明確 target baseline/dispatch、測 binary compatibility，並在 deployment workload 上驗證。"),
        ],
        ["csapp-asides", "csapp-changes", "gcc", "intel-sdm", "csapp-labs"],
    ),
    S(
        "ch6",
        6,
        "記憶體階層：Locality、cache、TLB 與 bandwidth",
        "CPU 為何算得快卻常在等資料，而程式 layout 如何改變答案？",
        (
            "address stream、working set、cache/TLB 組態與 memory technology",
            "利用 temporal/spatial locality 在多層 hierarchy 搬移 fixed-size blocks",
            "能分類 miss、手算 mapping，並以 layout/blocking 降低資料移動",
        ),
        [
            ("Locality", "程式近期傾向重用相同位置（temporal）或鄰近位置（spatial）的性質。", "Row-major 逐列掃 matrix 通常連續使用 cache lines。"),
            ("Cache line", "相鄰階層一次搬移與追蹤的固定大小 block。", "64-byte line 可同時帶回 16 個 32-bit integers。"),
            ("Set associativity", "一個 memory block 可放入某 set 的 E 個候選 lines。", "4-way cache 的每個 set 有四個 tag/data slots。"),
            ("Working set", "某時間窗口內活躍且反覆使用的資料集合。", "Hash join 的 build table 若放得進 LLC，probe latency 會顯著不同。"),
            ("Memory bandwidth", "單位時間可搬移的資料量；與單次 access latency 不同。", "Streaming loop 可能隱藏部分 latency，卻受 DRAM GB/s 上限限制。"),
        ],
        r"""
CPU request address
  ↓ L1 cache: tag / set / offset
 hit → bytes immediately
 miss ↓
L2 → LLC → memory controller → DRAM
                    ↓ dirty eviction / writeback

virtual address first visits TLB
  hit → physical page quickly
  miss → page-table walk (itself uses caches)

program layout + traversal → address stream → locality
address stream + hierarchy → hits/misses → latency/bandwidth
""",
        r"""
### 6.A 儲存技術決定階層，不必死背單一延遲表

Registers 與 SRAM cache 快但昂貴、容量小；DRAM 以 capacitor 儲存，需要 refresh，容量大但 latency 高；SSD 以 flash pages/erase blocks 管理，讀寫非對稱且需 wear leveling；磁碟有 seek/rotation 機械成本。實際數字隨世代變動，但跨層級的量級差與「大、便宜、慢」取捨長期存在。

Hierarchy 把下一層視為 blocks 的 backing store。命中時由上層提供；miss 時抓一整 block，期待 locality 讓後續 accesses 受益。Cache 不是魔法加速所有程式；若 access 缺乏 locality，搬回的其他 bytes 只浪費 bandwidth。

### 6.B Cache 地址拆解

對 data capacity `C = S × E × B`：S sets、每 set E lines、每 line B bytes。若 S/B 是二的冪，physical address 常拆為 tag、set index、block offset。Offset 選 line 內 byte，index 選 set，tag 判斷是不是目標 block。Direct mapped 是 E=1；fully associative 是 S=1；set-associative 在 hit time、硬體成本與 conflict miss 間取捨。

手算時先由 `b=log2(B)`、`s=log2(S)` 求 bits，再對每個 address 寫 block number、set、tag。Replacement 只在同 set 的 valid candidates 中選。LRU 是常見模型，真實硬體可能使用近似策略。

### 6.C Miss 不只有一種

Compulsory miss 是 block 第一次出現；capacity miss 是活躍資料超過 cache 即使 fully associative 也放不下；conflict miss 是 mapping 讓互相活躍 blocks 擠進同 set。分類不是純命名：prefetch/較大 line 對 compulsory 有幫助；blocking/縮小 working set 對 capacity；提高 associativity或改 padding/layout 可減 conflict。

Write-through 每次 store 同步送下一層，簡單但 traffic 大；write-back 先標 dirty，eviction 才下寫。Write-allocate 在 store miss 先抓 line，適合後續重用；no-write-allocate 可直接向下寫，適合 streaming。Policy 必須與一致性、durability 分開：CPU cache write-back 不代表 filesystem durability。

### 6.D Locality 是 code 與 data layout 的共同產物

C multi-dimensional array row-major，內層迴圈若走最後一維便連續。Array of structs 對「一次使用每個 object 多數 fields」有 locality；structure of arrays 對「批次只掃一個 field」更利 SIMD/cache。Linked list 每個 node 可能分散，pointer chasing 形成 serial latency chain；pool/arena allocation 可改善位置與 metadata overhead。

Blocking/tiling 把大問題切成能在某 cache level 重用的小工作。例如 matrix multiplication 不讓每個 `B[k][j]` 在巨大 stride 下反覆 miss，而是在 tile 中多次使用已載入 lines。Tile size 要考慮多個 arrays、associativity與 element size，不是「等於 L1 容量」就完成。

### 6.E TLB 是地址轉譯的 cache

CPU 用 virtual address，cache 最終需要能定位 physical memory。TLB 保存近期 virtual page → physical frame 與 permissions；TLB miss 觸發 hardware/software page-table walk，不等於 page fault。若 page-table entry present，walk 完就可填 TLB；只有 mapping 不在 memory或權限不符等情況才進 OS exception path。

Large pages 可降低同一 working set 所需 TLB entries，但增加 allocation/fragmentation、migration與 page-level copying 成本。它是 workload trade-off，不是免費加速。

### 6.F Coherence 與 false sharing

多核心各有 private caches，需要 cache-coherence protocol 讓同一 physical line 的 writes 具有一致可見次序。即使 threads 更新不同 variables，只要它們在同一 line，ownership 仍會來回轉移，形成 false sharing。Padding/alignment 或 partitioning 可分離 hot writes，但會增加 memory footprint，也可能破壞其他 locality。

### 6.G 用 memory mountain 連起 stride 與 working set

固定讀取量，改變 array size 與 stride，量到的 throughput 會呈現 cache level/line/prefetch 的階梯。小 working set 命中上層；size 變大落到下層；stride 超過 line 能利用的 elements 時，spatial locality 降低。這比背「L1 幾 ns」更能理解特定機器與程式。
""",
        r"""
實作 address-trace cache simulator，參數為 s/E/b，逐筆輸出 hit/miss/eviction；再用同一組 matrix 分別做 row-major、column-major 與 tiled traversal。以 `perf stat` 觀察 cache/TLB events，並做二維 memory mountain：array size 從 KiB 到數 GiB、stride 從 1 到數百 bytes。

```bash
perf stat -e cycles,instructions,cache-references,cache-misses,\
dTLB-loads,dTLB-load-misses ./memory_mountain
getconf LEVEL1_DCACHE_SIZE
getconf LEVEL1_DCACHE_LINESIZE
```
""",
        [
            "把 cache capacity C 當成包含 tag/metadata 的實體總面積。",
            "只說 cache miss，沒有分類 compulsory/capacity/conflict。",
            "認為較大 cache line 永遠更好，忽略 wasted bandwidth 與 false sharing。",
            "把 TLB miss、page-table walk 與 page fault 當同一事件。",
            "為消除 false sharing 大量 padding，卻未量 memory footprint 與 NUMA 影響。",
        ],
        [
            ("為何 row-major array 逐列通常比逐欄快？", "C 將最後一維連續排列。逐列使 successive accesses 落在同一或下一條 cache line，充分利用每次 block transfer與 hardware prefetch；逐欄 stride 可能每次只用一個 element就跳到新 line，浪費 line 其餘 bytes並增加 TLB/cache misses。"),
            ("Direct-mapped cache 中兩個常用 blocks 對到同 set 會怎樣？", "因每 set 只有一個 line，它們會反覆互相 eviction，即使其他 sets 空著也不能使用，形成 conflict thrashing。提高 associativity、改變 array padding/alignment或重排 traversal 可解除 mapping 衝突。"),
            ("為何增大 line size 可能讓效能變差？", "若程式只用 line 中少量 bytes，較大 line 浪費 bandwidth並減少同容量 cache 可容納的不同 blocks；miss penalty 也可能上升，多核心寫入時 false-sharing 範圍更大。只有具足夠 spatial locality 時才受益。"),
            ("TLB miss 為何通常不是 page fault？", "TLB 只是 page-table entries 的小 cache。Miss 後 page walker 讀 page tables；若 valid/present mapping 已存在，就填入 TLB並繼續。Page fault 是 page-table state/permission要求 OS 介入，例如 demand paging、copy-on-write或非法 access。"),
            ("Blocking matrix multiplication 如何降低 miss？", "它把 i/j/k 空間切成小 tiles，讓 A/B/C 的子區塊在 cache 中被多次重用後才換下一塊，縮小短時間 working set並改善 B 的 spatial/temporal locality。Tile 太大會超 cache或衝突，太小則 loop overhead增加。"),
            ("False sharing 為何在變數彼此不同時仍發生？", "Coherence 追蹤的最小單位通常是 cache line，不是 language variable。兩核心對同 line 不同 offsets 反覆寫，line ownership仍需轉移並 invalidation，造成 latency與 interconnect traffic。"),
            ("Latency 與 bandwidth 應如何區分？", "Latency 是單次 request 從發出到可用的時間；bandwidth 是穩態單位時間可完成的資料量。多個 independent misses可重疊以接近高 bandwidth，卻不縮短單一 dependent pointer chase 的 latency。Optimization 要看 workload能否產生 memory-level parallelism。"),
        ],
        ["csapp-asides", "csapp-labs", "intel-sdm", "notes-akiyama"],
    ),
    S(
        "ch7",
        7,
        "連結與載入：symbol、relocation、ELF、GOT 與 PLT",
        "分開編譯的名稱如何在執行時變成正確地址？",
        (
            "relocatable objects、symbols、relocations、archives 與 shared libraries",
            "linker 解析定義、合併 sections、配置地址；loader 建立 segments 與動態依賴",
            "能診斷 undefined/multiple definition、library order、ABI 與 runtime loader 問題",
        ),
        [
            ("Symbol", "Linker 可見、代表 function/object/section 等 entity 的名稱與屬性。", "`main`、外部 global、某些 `static` entity 會以不同 binding 出現在 symbol table。"),
            ("Relocation", "記錄某個位置需要在地址確定後依特定公式修補。", "PC-relative call 要由 linker 填入 target 與下一條 instruction 的距離。"),
            ("ELF section", "以 linking/debugging 視角組織 code、data、symbols、relocations。", "`.text`、`.rodata`、`.data`、`.bss`、`.symtab`。"),
            ("ELF segment", "Loader 需要映射到 memory 的範圍與 permissions。", "`PT_LOAD` 可將多個相鄰 sections 映成 R-X 或 RW- pages。"),
            ("PIC", "不假設固定載入地址即可執行的 position-independent code。", "Shared library 透過 PC-relative addressing、GOT/PLT 存取外部 symbol。"),
        ],
        r"""
translation units → relocatable .o files
  ├─ sections: code/data
  ├─ symbol tables
  └─ relocation entries
          ↓ static linker
symbol resolution → section merge/layout → relocation
          ↓
ELF executable + dynamic dependencies
          ↓ execve / program interpreter
loader maps segments → dynamic linker loads DSOs
          ↓ GOT / PLT / symbol lookup / relocations
process reaches runtime entry → main
""",
        r"""
### 7.A Object file 是 code/data 加上尚未完成的關係

Compiler/assembler 可知道 local instruction bytes與 section內容，但跨 translation unit 的 function/global 最終地址仍未知。Relocatable ELF 因此同時保存 sections、symbol table 與 relocation entries。`.bss` 表示 zero-initialized storage 的大小而不需在檔案重複存零；debug sections 可很大但通常不映入 runtime。

Section 與 segment 是兩個視角。Linker 以 sections 合併與解析；loader 看 program headers/segments，依 file offset、virtual address、size、alignment與 flags 建 mappings。不要用 `.text` 等 section 名直接推測 page mapping，應看 `readelf -l` 的 section-to-segment mapping。

### 7.B Symbol resolution 與 C linkage

Global symbols 可由某 object 定義、被其他 object 引用。Traditional Unix linker 以 strong/weak 規則處理部分同名 definitions，但依賴 tentative definition/weak override 容易造成隱晦 bug；現代工具鏈常預設 `-fno-common` 讓多重 tentative definitions 直接失敗。`static` file-scope entity 有 internal linkage，不參與跨 object 同名解析。

Undefined reference 不等於 header 缺失：compiler 已接受 declaration，linker卻找不到 compatible definition。Multiple definition 則是多個 object 提供衝突 storage/body。診斷要先用 `nm/readelf -s` 看 symbol binding、type與所在 object。

### 7.C Static archive 為何有 order sensitivity

Archive `.a` 是 object members 的索引集合。Linker 通常由左到右維護已解析與未解析 symbol，遇 archive 時只抽出當下需要的 members；若提供者出現在引用者之前，之後新增的未解析 symbol不一定回頭重掃。一般把 objects 放前、libraries 放後；循環依賴可用 group options，但更應檢查模組邊界。

Static linking 讓 dependency code 進 executable，部署較獨立但 artifact大、更新 library需重建；dynamic linking 共享 DSO、可獨立修補，但增加 loader search path、ABI/symbol version與部署一致性問題。

### 7.D Relocation 是地址代數

Absolute relocation 把 symbol address加 addend寫入欄位；PC-relative relocation寫 target與 relocation place之間的差。x86-64 的 relative range有限，code model與linker stubs可能介入。理解公式比背 relocation type名稱更重要：先找要修的位置 P、symbol值 S、addend A，再看結果是 `S+A` 或 `S+A-P`。

### 7.E Shared library、GOT 與 PLT

PIC 盡量以 PC-relative方式取得 nearby data/code。GOT 是 runtime可修補的 address table，讓 code不需為每個load改寫 text pages；PLT 提供外部 function call trampoline，首次呼叫可進 dynamic resolver完成 lazy binding，再把結果寫入 GOT。Modern options也可 eager bind、RELRO保護 relocation tables，安全與startup成本之間有取捨。

Symbol interposition 允許先載入的 definition覆蓋後者，支援 `LD_PRELOAD` instrumentation，也可能阻止 compiler optimization或造成意外行為。Visibility/version scripts可縮小 exported ABI。Library介面一旦跨 binary boundary，struct layout、calling convention、exception/allocator ownership 都成為相容性責任。

### 7.F Loader 問題要分四層

第一層是檔案/architecture/interpreter是否正確；第二層是 `DT_NEEDED` dependency能否依搜尋規則找到；第三層是所需 symbol與version是否存在；第四層是初始化與runtime行為。`ldd` 便捷但對不可信 executable有風險；可用 `readelf -d`、loader diagnostics與受控環境調查。Build image有 library不代表runtime image相同。

### 7.G Linking 與安全/供應鏈

RPATH/RUNPATH、current directory、environment preload與writable library path都可能改變實際載入 code。Production artifact應記錄 dependency versions、interpreter、build flags與hash；最小 export surface、RELRO/PIE/NX與簽章/provenance共同降低風險，但無法替代相容性測試。
""",
        r"""
建立 `main.c`、`math.c`、`libhelper.a` 與 `libhelper.so`。故意調換 archive order製造 undefined reference，再用 `nm -A` 找 provider；用 `readelf -r/-s/-d/-l` 與 `objdump -d` 追一個外部 call 的 relocation、PLT與GOT。最後以 `LD_DEBUG=libs,bindings` 在隔離環境觀察 dynamic loader。

```bash
cc -fPIC -c helper.c
cc -shared helper.o -o libhelper.so
ar rcs libhelper.a helper.o
cc main.o -L. -lhelper -Wl,-rpath,'$ORIGIN' -o app
readelf -h -S -l -s -r -d app
objdump -d -Mintel app
```
""",
        [
            "把 declaration 存在誤認為 linker 一定能找到 definition。",
            "混淆 sections 與 runtime segments/permissions。",
            "使用 static archive 時忽略由左到右的抽取模型。",
            "用 `LD_LIBRARY_PATH` 永久修部署，掩蓋 artifact/runtime 不一致。",
            "把 symbol interposition 當穩定 API，未控制 visibility與ABI。",
        ],
        [
            ("為何 undefined reference 是 link-time 而非 compile-time 問題？", "Compiler只需有足夠 declaration檢查 call型別並產生未解析引用；definition可在另一 translation unit或library。Linker收集所有 objects後才負責找到 symbol definition並修補地址，所以缺 provider在這時顯現。"),
            ("Section 與 segment 的差別為何重要？", "Sections服務 linker/debugger，按語意細分；segments服務 loader，按映射範圍、alignment與permissions聚合。Runtime page權限由program headers決定，strip section table後 executable仍可載入。"),
            ("Static library順序為何可能改變結果？", "Linker遇 archive時通常只抽取能解決當前 unresolved set的members。若library先出現，當時還沒有需求就不抽取；後面的object新增引用時它不一定回頭。Objects先、providers後符合這個單向算法。"),
            ("GOT 與 PLT 分別解決什麼？", "GOT提供可由loader填入的data/function addresses，PIC code以相對方式取得table entry；PLT是外部function call的code trampoline，可把首次call送resolver並經GOT快取target。兩者讓shared code少做text relocations並支援dynamic binding。"),
            ("為何 shared-library struct直接暴露 layout 風險高？", "Member order、size、alignment、padding與compiler ABI都成為binary contract；新增field或改compile options可能讓舊client以錯誤offset存取。Opaque pointer加constructor/accessors可把layout留在library內，較容易演進。"),
            ("`LD_PRELOAD` 為何既是工具也是風險？", "它可插入同名symbols做profiling、fault injection或compatibility shim；同一機制也可在不安全environment載入惡意code。Privileged/production context要清理environment、控制search paths與file ownership。"),
            ("如何系統化診斷『在我機器可跑，容器不行』的 loader error？", "比較ELF architecture/interpreter、`DT_NEEDED`、RPATH/RUNPATH、實際library files與symbol versions；不要只比package name。保留build/runtime image digest，用`readelf`與loader debug輸出定位是找不到file、錯architecture或缺symbol version。"),
        ],
        ["csapp-asides", "csapp-changes", "elf", "sysv-abi", "binutils", "linux-man"],
    ),
    S(
        "ch8",
        8,
        "例外控制流：exception、process、signal 與 shell",
        "普通 instruction sequence 之外，OS 如何安全插入控制流？",
        (
            "CPU事件、system calls、process state、signals與parent/child關係",
            "透過exception table與kernel切換控制流，並以fork/exec/wait/signal管理logical flows",
            "能設計不漏 child、不lost wakeup、支援job control的process程式",
        ),
        [
            ("Exception", "硬體/軟體事件使CPU透過預先定義入口轉移到OS handler的控制流機制。", "System call trap、page fault、divide error、timer interrupt。"),
            ("Context switch", "Kernel保存一個task的執行state並恢復另一個，使CPU在logical flows間切換。", "Timer interrupt後scheduler改讓另一process執行。"),
            ("Zombie", "Child已終止但parent尚未wait回收其status，kernel保留最小紀錄。", "它不再執行，卻仍占process table entry。"),
            ("Signal mask", "暫時阻擋指定signals被delivered的per-thread state。", "Parent在fork前block SIGCHLD，登記job後再unblock以關閉race window。"),
            ("Process group", "Job control把相關process集合成可共同收signal與管理terminal前景權的單位。", "Pipeline中的commands通常屬於同一process group。"),
        ],
        r"""
normal user instructions
  ↓ event: interrupt / trap / fault / abort
CPU saves restart context → kernel exception handler
  ├─ service syscall
  ├─ schedule another task
  ├─ resolve page fault
  └─ deliver signal / terminate
  ↓ return to user or another flow

shell: parse → fork children → set process group → redirection → exec
parent: record job ↔ block/unblock signals ↔ wait/reap
terminal: foreground group receives interactive signals
""",
        r"""
### 8.A Exceptional control flow 是系統組合的骨架

Interrupt來自processor外部I/O/timer，通常在instruction邊界處理；trap是有意同步事件，如system call；fault可能可修復並重新執行，如page fault；abort通常不可恢復。分類重點是事件來源、handler返回位置與可否restart，而非只背名稱。CPU利用exception table/IDT找到kernel入口，切換privilege與stack，保存必要context。

System call是受控trap，不是普通function call。User-space wrapper依ABI放number/arguments並執行特定instruction；kernel驗證pointer、permission與resource state後返回結果/errno。Context switch可能在blocking syscall、timer或higher-priority work時發生，會帶來cache/TLB等間接成本。

### 8.B Process 是control flow與資源view

Process擁有virtual address space、descriptor table、credentials、signal dispositions等。`fork`建立child，邏輯上複製parent context並從同一位置返回不同值；memory多以copy-on-write延遲複製，open file descriptions可共享。`execve`不建立新process，而是用新program image替換當前address space，保留PID與依規則保留descriptors、credentials等。

`wait/waitpid`讓parent取得child termination status並回收zombie。Parent若不wait，zombie不會自行執行但仍占entry；parent先死的orphan會被指定reaper接管。Long-running server必須有明確child lifecycle policy。

### 8.C Fork輸出題要同時畫process tree與buffer

每個成功fork使當下control flow分叉，但後續fork只由走到該處的process執行。Output次數還受stdio buffer影響：fork前尚未flush的user-space buffer被複製，parent/child各自exit時可能重複flush；直接`write`的kernel interaction又是另一層。不能只數process，不畫buffer與termination path。

### 8.D Signal是coalescing notification，不是message queue

Standard signal同種類通常只保留pending bit，不會可靠累積每次event。Delivery可發生在幾乎任何instruction邊界；handler與main flow共享state時，只有極少operation與types有安全保證。Handler應短小，只使用async-signal-safe operations，例如設定`volatile sig_atomic_t` flag或寫入self-pipe/eventfd；`printf`、`malloc`與大多數library不安全。

Race的典型修法不是加sleep，而是block signal關閉critical window：parent先block SIGCHLD，fork後把child加入job table，再unblock；child在exec前恢復mask。等待事件時用`sigsuspend`原子地換mask並sleep，避免「檢查條件後、真正sleep前signal已到」的lost wakeup。

### 8.E Shell job control 是多個contract的交會

Shell為pipeline建立process group，將foreground group交給controlling terminal；terminal把Ctrl-C/Ctrl-Z等signals送給foreground group。Shell自己不應被child job的interactive signal殺死。Background job若讀terminal可能被stop。Shell需處理`SIGCHLD`並以nonblocking wait loop回收所有狀態變化，因一次signal可能代表多個children。

Redirection要在child `exec`前用`dup2`改descriptors；不使用的pipe ends在所有process都要關閉，否則reader永遠看不到EOF。這把Chapter 8與Chapter 10直接串起來。

### 8.F Nonlocal jump 與錯誤處理邊界

`setjmp/longjmp`可跨多層stack返回，但自動變數值、resource cleanup與signal mask語意容易出錯；`sigsetjmp`可選擇保存mask。它適合受控runtime/exception emulation，不應用來任意跳過locks、allocated resources或C++ destructors。多數application以顯式error propagation更可維護。

### 8.G 安全地終止process

`kill`是發signal，不保證立即終止；SIGTERM可被處理/忽略，SIGKILL不能被捕捉但仍需kernel安排執行並回收。Supervisor應先送graceful signal、停止接新工作、設deadline，再升級；同時處理child group、descendants與zombie。Termination是protocol，不是一個單一API。
""",
        r"""
實作一個最小shell：支援foreground/background、單一pipe與redirection。建立job table時在fork前block SIGCHLD，handler只以`waitpid(-1, ..., WNOHANG|WUNTRACED|WCONTINUED)`迴圈更新預先配置state或寫self-pipe；主迴圈負責格式化輸出。用快速exit child與隨機delay重複數千次驗證沒有lost child。

```bash
strace -f -e trace=process,signal,desc ./mini-shell
ps -o pid,ppid,pgid,sid,tpgid,stat,cmd
```
""",
        [
            "把 `fork` 理解成重新從 `main` 開始，而非從return point分叉。",
            "在 signal handler 中呼叫非 async-signal-safe library。",
            "用一個 boolean 表示收到幾次 standard signal，期待事件不遺失。",
            "先檢查條件再 `pause`，留下lost-wakeup window。",
            "Pipeline只關parent的pipe ends，child仍保留多餘writer reference。",
        ],
        [
            ("`fork` 後父子為何可看到相同初始memory卻互不直接覆蓋？", "Kernel建立近似相同virtual mappings並將private pages設為copy-on-write。讀取可共享physical frames；任一方寫入觸發protection fault，kernel配置/複製private frame後再繼續，因此virtual addresses可相同而後續內容分離。"),
            ("`execve` 為何不等於建立新process？", "它保留process identity並替換program image：舊code/data/stack mappings被新executable與libraries取代，從新entry開始。PID、部分credentials與未標close-on-exec descriptors按規則保留；因此fork+exec是先建立child，再讓child換程式。"),
            ("Zombie與orphan差在哪？", "Zombie已終止、不執行，只等parent回收status；orphan是parent先終止但child可能仍在執行，會被reaper接管。兩者一個是termination record lifecycle，一個是parent relationship變化。"),
            ("為何一個SIGCHLD handler要loop呼叫waitpid？", "Standard signals可能coalesce，多個children狀態變化只產生一個pending notification；handler被執行期間又可能有更多變化。每次醒來應nonblocking loop直到沒有可回收child，而不是假設一次signal對一個child。"),
            ("Signal handler中設定普通`int` flag安全嗎？", "Portable C只保證對`volatile sig_atomic_t`的簡單存取在signal context可安全表達；更複雜共享資料仍有ordering/reentrancy問題。多執行緒下signal delivery與C atomic rules更複雜，常用self-pipe/signalfd把事件轉回正常event loop處理。"),
            ("`sigsuspend`如何避免lost wakeup？", "先在blocked狀態檢查/更新shared condition，再以`sigsuspend`原子地暫時換成允許目標signal的mask並睡眠。Signal不可能落在『unblock後但sleep前』的縫隙；handler返回後原mask恢復，loop重新檢查predicate。"),
            ("Shell為何要管理process group而非逐一PID？", "一個job可能是多個pipeline processes。Terminal interactive signals、stop/continue與foreground ownership都以process group為單位；若只追第一個PID，其他members可能繼續跑、搶terminal或變zombie，無法提供一致job lifecycle。"),
        ],
        ["csapp-labs", "linux-man", "posix", "csapp-asides"],
    ),
    S(
        "ch9",
        9,
        "虛擬記憶體與動態配置：mapping、page、allocator",
        "一個 pointer 如何同時牽涉地址轉譯、保護、檔案映射與 heap metadata？",
        (
            "virtual address、page-table state、backing objects與allocation requests",
            "MMU/OS以pages建立映射；allocator再於process heap內切分、合併blocks",
            "能區分TLB miss/page fault/segfault，並設計可驗證allocator invariants",
        ),
        [
            ("Virtual page", "Virtual address space的固定大小區塊，是mapping與protection基本單位。", "4 KiB page讓低12 bits成為page offset。"),
            ("Page table", "描述virtual page映到哪個physical frame或backing state，以及permissions。", "PTE可標present、writable、user、dirty等狀態。"),
            ("Memory mapping", "把virtual address range關聯到anonymous memory、file或shared object。", "`mmap`可讓file pages按需出現在process address space。"),
            ("Fragmentation", "可用memory因block配置方式而浪費；分internal與external。", "16-byte request放進32-byte block造成internal waste。"),
            ("Allocator invariant", "heap在任何合法操作後都必須成立的結構規則。", "所有payload aligned、block不重疊、free-list entries恰好對應free blocks。"),
        ],
        r"""
virtual address = virtual page number | page offset
        ↓ TLB lookup
 hit → physical frame number | same offset
 miss → multi-level page-table walk
          ├─ valid mapping → fill TLB
          └─ exception → kernel page-fault handler
                ├─ demand-zero / file-in / copy-on-write
                └─ permission/invalid → signal

process mappings: code | data | heap | mmap | shared libs | stack
malloc layer: request → size/alignment → find free block
              → split/place → payload
free → mark → coalesce → free structure
""",
        r"""
### 9.A Virtual memory同時做cache、protection與sharing

VM把virtual pages映到physical frames，未resident資料可由file/swap/zero-fill等backing在需要時建立。每個process可有相同virtual address但映到不同frame；也可刻意映到同一frame共享library或IPC。PTE permissions在每次translation/access檢查，形成user/kernel、read/write/execute隔離。

把VM只說成「比RAM大的假memory」會漏掉最重要的地址空間、protection與mapping用途。即使完全不swap，ASLR、shared libraries、copy-on-write、memory-mapped files仍依賴VM。

### 9.B Multi-level page table為何存在

若64-bit address space為每個virtual page配置固定PTE，單process表會巨大。Multi-level structure只為實際使用的address regions配置下層tables；virtual page number切成多級indexes，page offset不變。Page-table walk本身也讀memory，會受cache影響；TLB用少量entries快取translation。

TLB miss只表示translation不在TLB；page fault表示walk/permission需要OS。Page fault也不必是錯誤：demand-zero、file page-in、stack growth、copy-on-write都是正常fault。非法address或permission violation無法修復時，OS才通常向process送SIGSEGV/SIGBUS等。

### 9.C `mmap`把file與address space接起來

File-backed mapping讓loads/stores透過page cache存取file內容；`MAP_SHARED` modifications可對其他mappings與file可見，`MAP_PRIVATE`以copy-on-write保留private changes。這些可見性不等於durability；何時writeback、是否需要`msync/fsync`要依OS/filesystem contract。Mapping長度、file truncation、offset alignment與concurrent writers都需要處理。

Anonymous mapping提供zero-filled pages，可用於heap、大allocation、thread stacks。`fork`複製mapping metadata並用COW共享private pages；`exec`建立全新program mappings。

### 9.D Process address space是許多mappings，不是固定圖片

教科書常畫code/data/heap/stack，但真實process還有loader、shared libraries、thread stacks、JIT、memory-mapped files、guard pages與kernel-provided regions。ASLR讓位置變動。`/proc/PID/maps`顯示ranges與permissions；`pmap`/debugger可輔助，但mapping存在不代表page resident，RSS/PSS/dirty需要其他統計。

### 9.E Allocator在VM之上管理較小blocks

`malloc`通常向OS取得較大regions，再維護block headers/free lists。Request先加metadata並round up alignment；搜尋合適free block，必要時split；`free`標記並與相鄰free blocks coalesce。Throughput與utilization衝突：精密best-fit可能省空間卻搜尋慢；簡單first-fit快但fragmentation pattern不同。

Implicit free list線性掃所有blocks；explicit list只串free blocks；segregated lists依size class分桶，縮短搜尋。Boundary tags/footer方便向前coalesce，但allocated block可用previous-allocation bit省footer。任何設計都應先寫heap checker，而不是靠某測資分數patch。

### 9.F Internal與external fragmentation

Internal fragmentation是allocated block內部因alignment、minimum size、metadata與size class浪費；external是free space總量足夠但分散，找不到所需contiguous block。Coalescing改善external但不能移動live blocks；compact GC可搬動objects，但C raw pointers讓一般allocator難以更新所有references。

Allocator也可能保留free memory在arena而不立刻還OS，所以application已`free`不代表RSS立即下降。多thread arenas降低lock contention卻增加fragmentation/footprint。診斷要分live allocations、allocator retained memory與mapped/resident pages。

### 9.G Memory correctness要按bug類型選工具

Use-after-free、heap overflow、double free、uninitialized read、leak、data race並非同一問題。ASan以shadow memory/redzones偵測部分bounds/lifetime；Valgrind類dynamic instrumentation有不同覆蓋/成本；UBSan看語言UB；TSan看data race；heap profiler看retained stacks。工具輸出仍需回到owner、lifetime與invariant根因。

### 9.H Garbage collection的系統觀

GC以roots出發判斷reachability，mark-sweep不搬objects但可能fragment；copying/compacting改善locality卻要更新references；generational利用多數objects短命的經驗。GC消除部分manual free錯誤，不消除logical leak、resource lifecycle或race；pause、throughput與memory headroom是production trade-off。
""",
        r"""
先用`/proc/self/maps`與`mincore`/page-fault counters觀察一個大型anonymous mapping：只`mmap`、逐頁讀、逐頁寫，分辨virtual size、RSS與minor faults。再做簡化allocator，支援aligned blocks、split/coalesce與explicit free list；每次operation後執行heap checker驗證不重疊、alignment、header/footer與free-list集合。

```bash
/usr/bin/time -v ./vm_touch
perf stat -e page-faults,minor-faults,major-faults,dTLB-load-misses ./vm_touch
cat /proc/$$/maps
```
""",
        [
            "把virtual memory只解釋為RAM不足時的swap技術。",
            "把TLB miss、minor/major page fault與segmentation fault混為一談。",
            "認為`mmap` store完成就等於資料已durable。",
            "Allocator沒有heap checker，遇錯只針對trace加case。",
            "看到RSS不降就直接判定memory leak，忽略arena與residency。",
        ],
        [
            ("Page offset為何在translation前後不變？", "Page大小相同且virtual page對齊映到physical frame；頁內第k個byte仍對應frame內第k個byte，因此只替換virtual page number，低`log2(page size)` bits直接保留。這也讓TLB entry只需cache page-level mapping。"),
            ("Minor與major page fault差在哪？", "兩者都進kernel fault path；minor通常不需從block device讀資料，例如demand-zero、COW或page cache已有內容；major需要等待storage I/O。分類是Linux accounting語意，實際成本仍受filesystem/device與contention影響。"),
            ("`MAP_PRIVATE`修改file mapping為何不直接改原file？", "Pages初始可共享file-backed content，第一次write觸發COW建立private anonymous copy，後續修改只屬該mapping。原file與其他private mappings不需看到變更；但file被外部修改時的可見細節仍應依平台contract處理。"),
            ("為何`fork`後寫大型array會讓RSS上升？", "Fork初始以COW共享private pages；每寫一個page都觸發fault並配置private frame、複製舊內容。Touch的pages越多，父子實體resident pages越分離。只讀或未touch的virtual range不會產生同等增量。"),
            ("Allocator為何需要minimum block size？", "Free block除了header/alignment，explicit list還要容納next/prev pointers，split出的remainder若太小便無法成為合法free block。Allocator應把這些需求納入adjusted size，避免產生永遠不能使用的碎片。"),
            ("Immediate與deferred coalescing如何取捨？", "Immediate free時立刻合併，快速提供大block但若相鄰block反覆alloc/free可能split/coalesce thrash；deferred在搜尋失敗或特定時機合併，free快但暫時fragment。Workload pattern決定最佳策略。"),
            ("`free`後RSS不降有哪些非leak原因？", "Allocator可能把block留在arena供未來reuse；含該block的page還有其他live objects，無法unmap；dirty pages仍resident；多thread arenas/fragmentation阻止形成可歸還的大區間。應以allocation profile、heap stats、maps與RSS/PSS共同判斷。"),
        ],
        ["csapp-asides", "csapp-labs", "linux-man", "clang-asan", "notes-yewentao"],
    ),
]
