"""Book-level guidance, bridge chapters, and appendices for the CS:APP book."""

GUIDE = r"""
## 先看依賴，不要把 12 章當 12 座孤島

CS:APP 的章序其實沿著兩條相互交會的主線前進：

<pre class="diagram deep-map"><code>程式如何執行
source → representation → instructions → processor → performance
                       ↘ memory references → cache / VM / allocator

程式如何成為服務
object files → linking/loading → process/signal → fd I/O → network → concurrency

兩線交會點
address、lifetime、buffer、system call、shared state、measurement</code></pre>

第一條線回答「CPU 如何理解並執行我的程式」；第二條線回答「程式如何被建置、由 OS 管理，並與外界合作」。Cache miss 可能造成 request latency，buffer lifetime 可能跨 system call，fork 會同時牽涉 VM 與 fd sharing；所以後半本不是忽然換成作業系統，而是把前半本的 data/control flow 放進真實執行環境。

### 每章固定使用同一個推理框架

1. **需求：**這個 component 為何存在？沒有它會遇到什麼限制？
2. **Contract：**上層能依賴哪些輸入、輸出與錯誤語意？
3. **State owner：**狀態在 register、cache、process、kernel object、peer 還是 disk？
4. **Flow：**正常路徑與失敗路徑如何穿過各層？
5. **Evidence：**用哪個 command、counter、trace 或最小程式推翻猜想？
6. **Trade-off：**哪個 constraint 改變後，原設計會不再合理？

只背名詞時，你會知道「TLB 是 translation cache」；套用框架後，你能回答：TLB 解決 page-table walk 成本、cache virtual-page mapping、miss 不等於 page fault、state 由 CPU/MMU 管、可用 counters 與 working-set experiment 驗證，而且 large page 會拿 fragmentation 換 reach。

### 21 天完整路線

| 日程 | 主題 | 必做輸出 |
|---|---|---|
| Day 1–2 | Chapter 0–1 | 建 toolchain；畫 source 到 process 的全景圖 |
| Day 3–4 | Chapter 2 | 手算 two's complement、checked arithmetic、binary32 |
| Day 5–6 | Chapter 3 | 對一個 C function 做 register role 與 CFG 標註 |
| Day 7 | Chapter 4 | 畫 pipeline timing，解釋 forwarding/stall/flush |
| Day 8–9 | Chapter 5 | 量 baseline、profile、CPE；只保留有證據的改善 |
| Day 10–11 | Chapter 6 | 手算 cache mapping；跑 stride/working-set 實驗 |
| Day 12 | Chapter 7 | 用 readelf/nm/objdump 追 symbol 與 relocation |
| Day 13–14 | Chapter 8 | 畫 process tree、signal mask 與 job-control flow |
| Day 15–16 | Chapter 9 | 畫 address translation；寫 allocator checker |
| Day 17 | Chapter 10 | 寫 robust read/write 與 pipe EOF reference map |
| Day 18–19 | Chapter 11 | 寫 incremental framing parser 與 deadline |
| Day 20 | Chapter 12 | 寫 bounded queue、invariant 與 shutdown protocol |
| Day 21 | 跨層整合 | 從一個 crash 或 latency 問題建立完整證據鏈 |

如果只有七天，讀 1、2、3、6、8、9、12；每章仍至少做一個實驗。若要準備 systems interview，先用每章 Follow-up 口述，再做綜合題。若目標是工作除錯，從「把系統知識用在工作上」反向連回各章。

### 怎樣才算真的讀懂？

「看得懂答案」不算完成。至少能在沒有本書時：

- 畫出 component 前後的 state 與資料流；
- 對一個小例子手算地址、bits、pipeline、cache set 或 page mapping；
- 說出一個正常案例、邊界案例、失敗案例；
- 指出哪個工具輸出能支持或推翻你的說法；
- 把概念接到真實工作，而不是只重述定義。
"""


LABS = r"""
## Labs 深化：不要追分數，要追 invariant

官方 labs 的共同設計不是「多寫幾個 C 程式」，而是把抽象 contract 變成可觀察、可破壞、可修復的系統。每個 lab 都用三輪：

<pre class="diagram deep-map"><code>Round 1 — Model
寫出 input / state / invariant / output，不急著最佳化
          ↓
Round 2 — Instrument
建立 checker、trace、counter 或 debugger checkpoint
          ↓
Round 3 — Adversarial
邊界輸入、隨機順序、錯誤時機、資源壓力、效能上限
          ↓
只有證據同時支持 correctness 與 performance 才算完成</code></pre>

| Lab | 先備模型 | 最關鍵的自製工具 | 最常見假理解 |
|---|---|---|---|
| Data Lab | 位權、modulo、two's complement、IEEE 754 | Exhaustive small-width oracle | 背出 bit trick，說不出 invariant |
| Bomb Lab | ABI、register roles、CFG、memory layout | 每個 phase 的資料流表 | 逐 instruction 翻譯，沒還原輸入約束 |
| Attack Lab | Stack、return linkage、bytes、mitigations | Stack map 與 payload byte map | 只會照 offset，不懂 NX/ROP 的設計壓力 |
| Architecture Lab | Datapath、availability/need time、CPE | Pipeline timing table | 背 stall cases，不懂 control priority |
| Cache Lab | tag/set/offset、LRU、locality | Trace-driven simulator 與 miss classifier | 只追正確輸出，不驗證 eviction state |
| Shell Lab | fork/exec/wait、signal mask、process group | Job-table invariant 與 race timeline | 用 sleep 讓測試暫時通過 |
| Malloc Lab | Block layout、split/coalesce、free structures | 每次 operation 後的 heap checker | 對 trace 補 if，沒有全域 invariant |
| Proxy Lab | Robust I/O、framing、HTTP、concurrency | Byte-fragmentation/fault-injection harness | localhost 正常就當 network code 正確 |
| Performance Lab | Baseline、CPE、locality、vectorization | Reproducible benchmark notebook | 只追最快一次或只看 instruction count |

### Lab notebook 的最小格式

```text
Hypothesis:
  哪個機制解釋目前現象？它預測什麼？
Invariant:
  每一步後必須成立哪些條件？
Experiment:
  固定哪些變因？改哪一個變因？
Raw evidence:
  command、版本、輸入、原始輸出
Interpretation:
  支持／推翻什麼？還有哪些替代解釋？
Next:
  下一個最小實驗，而不是下一個大改版
```

### Labs Follow-up Questions

<details class="deep-qa"><summary>為何 Malloc Lab 應先寫 heap checker，再追 throughput？</summary><div><p>Allocator bug 常在很早的 split、coalesce 或 free-list update 破壞 metadata，直到很後面的 allocation 才 crash。Checker在每次 transition 後驗證 alignment、block boundaries、free-set equality等 invariant，可把搜尋範圍縮到第一個錯誤操作。沒有 correctness foundation 的 throughput 分數不可解釋。</p></div></details>

<details class="deep-qa"><summary>為何 Shell Lab 用 sleep 通常只是掩蓋 race？</summary><div><p>Sleep只改變某次排程的機率，沒有建立 happens-before；換機器、負載或signal timing仍會失敗。應用 signal mask 關閉 race window、原子等待並讓 handler/main flow 共享狀態的規則可被證明。</p></div></details>

<details class="deep-qa"><summary>Cache simulator 為何需要保存每次 access 後的完整 state？</summary><div><p>最終 hit count 一致不代表 eviction policy 正確；錯誤 LRU timestamp 可能在目前 trace 尚未觸發差異。逐步 state trace能驗證 set選擇、valid/tag與recency transition，也方便產生最小反例。</p></div></details>

<details class="deep-qa"><summary>Proxy Lab 最重要的 adversarial 測試是什麼？</summary><div><p>把任意 request/response bytes 切成所有可能的小片段，搭配slow peer、mid-message EOF、oversized header/body、concurrent cache access與timeout。這直接檢驗程式是否把stream誤當message、是否bounded、以及error path會不會洩漏資源。</p></div></details>

<details class="deep-qa"><summary>Bomb/Attack Lab 怎樣避免變成照抄答案？</summary><div><p>保留每一步推理產物：register role、stack map、branch condition、input constraint與工具輸出。即使看到提示，也要能從原始binary獨立重建因果鏈。不要保存或散布可直接提交的payload/secret answers；學習價值在方法與證據。</p></div></details>
"""


WORK = r"""
## 跨層診斷：由症狀往下鑽，再把答案帶回上層

成熟的 systems debugging 不是從最底層開始，也不是看到任何 latency 就查 cache。先在使用者可見層定義症狀，再用 evidence 將問題空間逐層縮小：

<pre class="diagram deep-map"><code>使用者症狀：錯誤 / crash / latency / throughput / memory / deploy
        ↓ 先切範圍：哪些版本、輸入、機器、時間、requests？
Application invariant / protocol / ownership
        ↓
Runtime: allocation、threads、locks、queues、libraries
        ↓
OS boundary: syscalls、faults、scheduler、files、sockets
        ↓
Machine: instructions、branches、cache/TLB、bandwidth
        ↓
Hardware / external dependency

每往下一層都要有上一層證據，不做無限下鑽。</code></pre>

### 四個完整案例

**案例一：Release-only crash。** 先保留 exact binary、symbols、core與input；確認signal/fault address；用`-O2 -g`加ASan/UBSan重現；比較最後正確state與第一個corruption。Assembly用來解釋UB如何顯現，不是把compiler當bug來源。修復owner/bounds後加regression與多最佳化級別測試。

**案例二：p99突然上升。** 先確認traffic/version差異，從trace拆queue、CPU、lock、syscall、network；針對slow samples做profile。若cycles與LLC misses上升，再檢查layout/working set；若run queue/context switches上升，看thread pool與overload。平均profile不能代表tail。

**案例三：Memory持續成長。** 分virtual size、RSS/PSS、anonymous/file-backed、live allocations與allocator retained。用allocation profile看retained stacks；比較固定workload下成長斜率；檢查cache/queue policy與fragmentation。`free`後RSS不降不自動等於leak。

**案例四：部署後缺library。** 從ELF interpreter、architecture、NEEDED、RUNPATH與symbol versions逐層比較build/runtime artifact；不要用全域`LD_LIBRARY_PATH`暫時蓋過。修build provenance或packaging，再以乾淨environment驗證。

### Cross-layer Follow-up Questions

<details class="deep-qa"><summary>何時該往下一層看，而不是留在 application code？</summary><div><p>當上一層假說無法解釋證據，或觀察指出時間/錯誤跨過邊界時。例如trace顯示多數時間在page faults，才深入VM；若business invariant已在進system call前被破壞，就不需先研究kernel。下鑽應由可反證假說驅動。</p></div></details>

<details class="deep-qa"><summary>為何保存 exact binary 比只保存 source commit 更重要？</summary><div><p>Compiler版本、flags、generated code、linker、libraries與build inputs都會改變artifact；source相同不保證binary相同。Core/unwind/symbolization需要對應binary與debug info，供應鏈診斷也要知道production真正執行哪個digest。</p></div></details>

<details class="deep-qa"><summary>如何避免被單一 counter 誤導？</summary><div><p>Counter可能sampling、multiplex、speculative或有平台特定定義。先從metric建立多個競爭假說，再找互相支持的證據：例如cache miss上升同時應看到cycles/stall與layout/working-set變化；用controlled experiment改一個變因確認因果。</p></div></details>

<details class="deep-qa"><summary>為何修復後還要驗證 failure path？</summary><div><p>根因修正可能只讓正常輸入通過，error/cancellation/partial progress仍會洩漏fd、鎖或memory。Regression應重現原始trigger，並測timeout、resource exhaustion、concurrent shutdown與rollback，確保系統在相同壓力下安全失敗。</p></div></details>

<details class="deep-qa"><summary>最小可重現與production trace衝突時相信誰？</summary><div><p>兩者回答不同問題。最小程式用來隔離機制；production trace描述真實組合。若結果衝突，檢查被移除的環境/負載/依賴是否正是必要條件，再逐一加回。不要因microbenchmark乾淨就否定production現象，也不要因production複雜就拒絕隔離。</p></div></details>
"""


COVERAGE = r"""
<section id="coverage">
  <span class="chapter-tag">Appendix A</span>
  <h2>CS:APP 3e 完整覆蓋與完成標準</h2>
  <p>這張表不是目錄重述，而是每章讀完後應能交付的具體能力。若只能認出名詞，回到該章的 Blueprint、可執行實驗與 Follow-up。</p>
  <table>
    <tr><th>章</th><th>必懂知識鏈</th><th>實驗證據</th><th>完成標準</th></tr>
    <tr><td>0</td><td>C object、pointer、lifetime、UB、ABI、工具</td><td>warning / GDB / sanitizer</td><td>能找第一個被破壞的 invariant</td></tr>
    <tr><td>1</td><td>preprocess→compile→assemble→link→load→execute</td><td>中間檔、ELF、strace</td><td>能解釋 main 前後與一次輸出</td></tr>
    <tr><td>2</td><td>bits→encoding→conversion→arithmetic→rounding</td><td>手算＋bit dump</td><td>能安全處理外部長度與浮點誤差</td></tr>
    <tr><td>3</td><td>register/data flow→control flow→ABI→layout</td><td>objdump / GDB</td><td>能由assembly還原function contract</td></tr>
    <tr><td>4</td><td>datapath→pipeline→hazard→control→exception</td><td>timing table</td><td>能推導而非背誦stall/flush</td></tr>
    <tr><td>5</td><td>metric→profile→CPE→critical path→verification</td><td>perf / benchmark</td><td>改善可重現且不破壞correctness</td></tr>
    <tr><td>6</td><td>locality→mapping→miss→TLB→bandwidth/coherence</td><td>simulator / memory mountain</td><td>能由layout預測address stream</td></tr>
    <tr><td>7</td><td>symbol→resolution→relocation→ELF→dynamic loader</td><td>nm/readelf/objdump</td><td>能分類build/runtime linking failure</td></tr>
    <tr><td>8</td><td>exception→process→fork/exec/wait→signal→jobs</td><td>process tree / strace</td><td>沒有zombie與signal race</td></tr>
    <tr><td>9</td><td>VA→TLB→page table→mapping→allocator</td><td>fault counters / heap checker</td><td>能分層解釋memory症狀</td></tr>
    <tr><td>10</td><td>fd→open description→object→robust I/O→durability</td><td>fdinfo / fragmented I/O</td><td>正確處理short count與EOF</td></tr>
    <tr><td>11</td><td>name/address→socket→stream→framing→recovery</td><td>packet/byte fragmentation</td><td>能處理timeout與ambiguous outcome</td></tr>
    <tr><td>12</td><td>model→shared state→invariant→sync→liveness</td><td>TSan / stress / metrics</td><td>能證明bounded queue與shutdown</td></tr>
  </table>
</section>
"""


FORMULAS = r"""
<section id="formula-cards">
  <span class="chapter-tag">Appendix B</span>
  <h2>公式、地址與邊界速查卡</h2>
  <div class="formula-grid">
    <article><h3>Amdahl</h3><p><code>speedup = 1 / ((1-p) + p/k)</code></p><p>p 是被改善部分原占比，k 是該部分加速倍數。</p></article>
    <article><h3>Cache</h3><p><code>C = S × E × B</code></p><p><code>b=log₂B</code> offset bits；<code>s=log₂S</code> set bits。</p></article>
    <article><h3>Address translation</h3><p><code>VA = VPN | VPO</code></p><p>Page size為<code>2^p</code>時，低p bits offset不變。</p></article>
    <article><h3>Two's complement</h3><p>範圍 <code>-2^(w-1) … 2^(w-1)-1</code></p><p>Unsigned operation對<code>2^w</code>取模；signed overflow是UB。</p></article>
    <article><h3>Checked add</h3><p><code>a &gt; MAX-b</code> 時 <code>a+b</code> overflow。</p><p>檢查必須在運算前。</p></article>
    <article><h3>Queue stability</h3><p>長期 arrival rate ≥ service rate 時 queue無法穩定。</p><p>Bound、reject與backpressure是correctness的一部分。</p></article>
  </div>
  <h3>常用證據命令</h3>
  <pre><code>cc -Wall -Wextra -Wconversion -g -O2 source.c -o app
objdump -drwC -Mintel app
readelf -h -S -l -s -r -d app
nm -A --defined-only objects/*.o
gdb ./app
strace -f -yy ./app
perf stat -r 10 ./app
perf record -g ./app &amp;&amp; perf report
cat /proc/$PID/maps
ls -l /proc/$PID/fd
ss -ltnp
clang -g -fsanitize=address,undefined source.c
clang -g -fsanitize=thread -pthread source.c</code></pre>
  <p class="checkpoint"><strong>速查卡的限制：</strong>command output依architecture、compiler、libc、kernel與permission改變。它們是觀察入口，不是跨平台contract。</p>
</section>
"""


METHOD = r"""
<section id="research-method">
  <span class="chapter-tag">Appendix C</span>
  <h2>網路筆記與官方教材如何被用進本書</h2>
  <p>技術事實以 CS:APP 官方 student resources、Web Asides、labs、勘誤，以及 ABI、compiler、Linux/POSIX 正式文件校準。網路自學紀錄與課程筆記只用來找出讀者反覆卡住的地方，例如只背 cache 公式、逐行翻 assembly、用 sleep 修 signal race、Malloc Lab 沒有 checker；它們不作為唯一技術依據。</p>
  <div class="two-col">
    <div class="mini-card"><h4>採用的教學洞見</h4><p>以 labs 驗證每章；保存命令與原始輸出；先建立圖與 invariant；對容易混淆的成對概念做對照；把章節接回一個完整程式生命週期。</p></div>
    <div class="mini-card"><h4>刻意不採用</h4><p>直接提供官方作業秘密答案、只列結論沒有推導、把特定機器觀察當普遍規則、複製原書長段文字，或用過時 platform 數字取代概念模型。</p></div>
  </div>
  <p>CS:APP 官方勘誤仍可能更新；本版技術與來源檢查時間為 <strong>2026-10-01</strong>。遇到頁碼、練習或程式片段差異時，先確認書籍 printing 並查官方 errata。</p>
</section>
"""


EXTRA_GLOSSARY = {
    "Alignment": "Object起始地址必須是某個byte倍數的限制；影響layout、instruction與allocator。",
    "Basic block": "只有單一入口、除結尾外沒有branch的直線instruction序列，是CFG節點。",
    "Copy-on-write": "先共享read-only state，首次write時才複製，常用於fork與private mapping。",
    "CPI": "Cycles per instruction；受instruction mix、pipeline、cache與speculation共同影響。",
    "Critical section": "操作共享invariant state且不可與衝突操作交錯的code region。",
    "Demand paging": "Virtual page第一次被access時才由fault handler建立或載入。",
    "ELF": "Unix-like系統常見的object/executable/shared-library格式。",
    "Happens-before": "Memory model中保證一組effects對另一操作可見且有順序的關係。",
    "Idempotency": "相同operation重做多次，外部效果與做一次相同的protocol性質。",
    "Instruction-level parallelism": "同一thread中互不依賴instructions可重疊執行的程度。",
    "Page fault": "Address translation或permission需要OS介入的exception；可能是正常需求載入。",
    "PC-relative addressing": "以目前/下一instruction位置為基準表示target，利於position-independent code。",
    "Reentrancy": "執行中被再次進入仍保持contract，要求不依賴不安全的隱藏共享state。",
    "Relocation": "Linker/loader在地址確定後修補code/data引用的記錄與運算。",
    "Resident set": "Process目前實際resident於physical memory的pages集合；不同於virtual size。",
    "Spatial locality": "存取某位置後很快存取附近位置的傾向。",
    "Temporal locality": "近期使用的資料或instruction很快再次被使用的傾向。",
    "Throughput": "單位時間完成的工作量；與單一工作latency不同。",
    "TOCTOU": "檢查狀態與使用狀態分開時，中間被改變所形成的race。",
    "Working set": "時間窗口內活躍且反覆需要的code/data集合。",
}
