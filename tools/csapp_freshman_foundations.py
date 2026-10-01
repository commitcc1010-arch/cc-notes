"""Zero-systems-background primer and DSA-to-systems bridges."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FoundationTerm:
    key: str
    name: str
    plain: str
    example: str
    boundary: str


@dataclass(frozen=True)
class FreshmanBridge:
    section_id: str
    number: int
    known: str
    new_layer: str
    analogy: str
    checkpoints: tuple[str, ...]


FOUNDATION_TERMS = [
    FoundationTerm("program", "Program（程式）", "寫好並儲存的一組指令與資料；尚未執行時，它通常只是磁碟上的檔案。", "一個 `hello` executable 放在資料夾裡。", "Program 是靜態內容；process 是它某一次正在執行的狀態。"),
    FoundationTerm("executable", "Executable（可執行檔）", "已依特定OS與CPU格式組裝好、可被loader用來建立process的binary檔。", "Linux上的`./app`或Windows上的`app.exe`。", "Executable是磁碟上的artifact；它不是正在執行的process。"),
    FoundationTerm("process", "Process（行程）", "作業系統用來代表「一次正在執行的程式」的容器，包含目前指令位置、記憶體與開啟資源。", "同時開兩個 Python，會有兩個process，各自有變數和PID。", "Process 不是原始碼或executable；同一程式可同時有很多process。"),
    FoundationTerm("pid", "PID（Process ID）", "OS在process存活期間用來辨識它的一個數字。", "Shell可用`ps`看到process的PID。", "PID可能在process結束後被重用，不能當永久身份。"),
    FoundationTerm("cpu", "CPU（中央處理器）", "逐步讀取並執行machine instructions的硬體。", "做加法、比較、跳轉、讀寫memory。", "CPU不直接理解Python或C文字；它最後執行machine code。"),
    FoundationTerm("instruction", "Machine instruction（機器指令）", "CPU能直接執行的一個小操作，其編碼是一串bytes。", "把兩個register相加，或跳到另一個address。", "一行C通常不只一條instruction，一條instruction也不等於一個完整功能。"),
    FoundationTerm("bit-byte", "Bit 與 byte", "Bit只有0或1；byte通常由8 bits組成，也是memory可逐址存取的基本小單位。", "ASCII字元`A`可由一個byte值65表示。", "Bit不是文字`0`/`1`本身；byte也不保證剛好保存一個完整人類字元。"),
    FoundationTerm("binary", "Binary（二進位／binary檔）", "二進位是用bits表示資料的方法；binary檔泛指內容主要依規格解讀、不是直接給人閱讀的文字檔。", "Object file與executable都是binary檔。", "Binary檔仍能被工具解析；它不等於加密或無法理解。"),
    FoundationTerm("register", "Register（暫存器）", "CPU內部少量、非常快的儲存位置，用來放目前運算的值、地址或控制狀態。", "函式參數可能先放在`rdi`，結果放在`rax`。", "Register不是一般變數名稱；compiler決定某個值何時放哪裡。"),
    FoundationTerm("memory", "Memory／RAM（主記憶體）", "程式執行時保存code與data的可隨機存取空間；斷電後通常不保留。", "Array elements、stack frames與heap objects在執行時位於memory。", "RAM不同於SSD/disk；後者較慢但可持久保存檔案。"),
    FoundationTerm("virtual-memory", "Virtual memory（虛擬記憶體）", "OS與CPU讓每個process使用自己的一組virtual addresses，再把它們映射到RAM、file或尚未配置的狀態。", "兩個process都可能有地址`0x400000`，卻映到不同physical memory。", "它不只是在RAM不足時使用disk；隔離、保護與mapping同樣重要。"),
    FoundationTerm("page", "Page（頁）", "Virtual memory以固定大小區塊管理mapping與permissions，這個區塊叫page。", "常見page大小是4 KiB，但不是所有系統都固定如此。", "Page不是一般文件頁面，也不等於cache line。"),
    FoundationTerm("cache", "Cache（快取）", "保存較慢資料來源近期或鄰近內容的小型快速層，利用locality減少平均等待時間。", "CPU cache暫存從RAM搬來的cache lines。", "Cache不是權威資料的同義詞；miss也不一定是錯誤。"),
    FoundationTerm("storage", "Storage（持久儲存）", "斷電後仍保存資料的裝置或服務，例如SSD、disk。", "Source code與executable通常先保存在filesystem。", "資料寫入library buffer或RAM不一定已經durable到storage。"),
    FoundationTerm("buffer", "Buffer（緩衝區）", "暫時保存正在搬運、組裝或等待處理資料的一段memory。", "`printf`可先把多次小輸出累積在user-space buffer。", "資料進入buffer不代表已送到device、peer或durable storage。"),
    FoundationTerm("os", "Operating system／OS（作業系統）", "管理CPU、memory、devices與process，並提供程式可使用的受控介面。", "Linux、macOS、Windows。", "OS不只是畫面；kernel是其中持有最高權限的核心部分。"),
    FoundationTerm("kernel", "Kernel（核心）", "作業系統中以高權限執行、直接管理硬體與全系統資源的部分。", "建立process、配置page、讀取disk、傳送network packet。", "一般application不應任意讀寫kernel memory或直接控制devices。"),
    FoundationTerm("mode", "User mode／Kernel mode", "CPU提供的權限層級。Application平常在user mode；需要特權工作時受控進入kernel mode。", "普通程式不能自己關閉別人的memory protection。", "Mode不是使用者帳號；它是CPU執行權限。"),
    FoundationTerm("system-call", "System call（系統呼叫）", "Application請kernel代做特權工作的正式入口。", "`read`讀fd、`write`輸出bytes、`fork`建立process。", "它不是普通函式的同義詞；library function可能在user space完成，也可能包裝system call。"),
    FoundationTerm("abi", "ABI（Application Binary Interface）", "規定已編譯code在binary邊界如何合作的規則，例如參數放哪、register誰保存、資料如何排列、system call如何傳值。", "x86-64 Linux會約定function與system-call arguments使用哪些registers。", "ABI不是source-level API；同一C介面換OS或architecture可能使用不同ABI。"),
    FoundationTerm("library", "Library（函式庫）", "可重用的程式碼與介面，讓application不必自己實作所有功能。", "`printf`屬於C standard library；它可能最後呼叫`write`。", "Library執行時不自動擁有kernel權限。"),
    FoundationTerm("source", "Source code（原始碼）", "人類使用程式語言撰寫的文字。", "C檔案中的`int main(void) { return 0; }`。", "CPU不直接執行source code。"),
    FoundationTerm("compiler", "Compiler（編譯器）", "分析高階語言並將它轉成較低階表示或assembly/machine code的工具。", "GCC或Clang把C轉成x86-64 instructions。", "Compiler不是linker；它通常先處理單一translation unit。"),
    FoundationTerm("assembler", "Assembler（組譯器）", "把assembly文字轉成machine instruction bytes，並留下尚未決定地址的資訊。", "把`addq %rax, %rbx`編成對應bytes。", "它不是assembly language本身，而是執行轉換的工具。"),
    FoundationTerm("linker", "Linker（連結器）", "把多個object files與libraries合併，讓跨檔名稱連到definition，並修補地址。", "`main.o`呼叫`helper`，linker到`helper.o`找到它。", "Header只有declaration不保證linker一定找到definition。"),
    FoundationTerm("symbol", "Symbol（連結符號）", "Object file中供linker辨識function、global object或section的名稱與屬性。", "`main.o`可留下「我需要helper」的undefined symbol。", "Symbol不是執行時所有變數名稱；最佳化後許多local names可能不存在。"),
    FoundationTerm("relocation", "Relocation（重定位紀錄）", "告訴linker某個instruction或data位置要在最終地址決定後依何種公式修補。", "Function call的target尚未確定時，object file留下placeholder與relocation。", "Relocation是待修補資訊，不等於把整個process搬到另一台機器。"),
    FoundationTerm("loader", "Loader（載入器）", "執行程式時，依executable描述把code/data/libraries映射到process memory並設定起始狀態。", "Shell啟動`./app`後，loader讓CPU最後能跑到`main`。", "Loader發生在執行時；linker通常發生在build時。"),
    FoundationTerm("object-file", "Object file（目的檔）", "一個尚未完全連結的binary檔，含machine code/data以及symbols與relocations。", "編譯`main.c`得到`main.o`。", "Object file不是C語言的object；兩者只是英文名稱相同。"),
    FoundationTerm("object-format", "Object format（目的檔格式）", "規定binary檔如何排列header、code、data、symbols與relocations的版面標準。", "ELF是Linux/Unix-like常見格式；macOS常見Mach-O。", "它不是檔案內容的演算法，而是讓tools能一致讀懂binary的容器規格。"),
    FoundationTerm("elf", "ELF", "Executable and Linkable Format的縮寫，是Linux常見的object、executable與shared-library格式。", "`readelf`可顯示ELF的sections、segments與symbols。", "ELF不是CPU instruction set；同一格式可包含特定architecture的machine code。"),
    FoundationTerm("address", "Address（地址）", "程式用來指出某個memory byte位置的數值。", "`&x`取得C object `x`的地址。", "Application看到的通常是virtual address，不是DRAM晶片上的固定位置。"),
    FoundationTerm("pointer", "Pointer（指標）", "保存地址的值；其型別告訴compiler解參考時如何解讀bytes與前進多少。", "`int *p`可指向一個`int` object。", "Pointer不自動保存allocation長度、owner或目前是否仍有效。"),
    FoundationTerm("lifetime", "Lifetime（生命週期）", "一個object或resource從何時開始存在，到何時不再可合法使用的時間範圍。", "Function返回後，它的普通local object lifetime結束。", "地址數值仍留在pointer中，不代表被指向object仍活著。"),
    FoundationTerm("ownership", "Ownership（所有權責任）", "程式設計上的責任約定：誰可使用資源、誰必須釋放、何時移交。", "API回傳`malloc` pointer時要說明caller是否負責`free`。", "C通常不在型別中自動強制ownership，需要靠介面與程式結構維持。"),
    FoundationTerm("stack", "Call stack（呼叫堆疊）", "多數程式用來保存函式呼叫資訊、return位置與部分local data的memory區域。", "`main`呼叫`f`，`f`再呼叫`g`，通常形成三層stack frames。", "這裡的stack是執行機制；雖有LIFO直覺，但不等同DSA中的抽象Stack ADT。"),
    FoundationTerm("heap", "Heap（動態配置區）", "程式執行時向allocator要求、由程式決定何時釋放的memory區域。", "C的`malloc/free`管理heap blocks。", "它不是DSA的binary heap／priority queue；只是歷史上同名。"),
    FoundationTerm("fd", "File descriptor／fd（檔案描述符）", "Process內的一個小整數索引，用來引用kernel管理的file、pipe、socket等資源。", "0通常是stdin，1是stdout，2是stderr。", "fd不是檔案內容，也不是全系統永久ID。"),
    FoundationTerm("shell", "Shell 與 terminal", "Terminal是互動文字介面；shell是讀取command、啟動program、設定pipe/redirection的程式。", "在terminal輸入`python3 app.py`，通常由shell解析並啟動process。", "Shell不是kernel，也不是compiler。"),
    FoundationTerm("debugger", "Debugger（除錯器）", "可暫停正在執行的程式、逐步前進並觀察register、memory與call stack的工具。", "在某一行前停止並查看變數值。", "Debugger顯示某次執行的證據，不會自動判斷設計是否正確。"),
    FoundationTerm("gdb", "GDB", "GNU Debugger的縮寫，常用於Linux上的C/C++與machine-level debugging。", "`gdb ./app`載入程式，`break main`在main前設breakpoint。", "名稱是GDB，不是GBD；它是一個具體debugger。"),
    FoundationTerm("breakpoint", "Breakpoint（中斷點）", "要求debugger在程式執行到某行、function或address時暫停。", "在`main`暫停後逐步看state如何改變。", "它監看『執行位置』；watchpoint主要監看『資料被改變』。"),
    FoundationTerm("watchpoint", "Watchpoint（資料監看點）", "要求debugger在指定memory位置的值被讀或寫時暫停。", "當某個array邊界外寫入覆蓋`count`時立即停下。", "Hardware watchpoints數量有限，也只捕捉實際監看的位置與執行路徑。"),
    FoundationTerm("stack-corruption", "Stack corruption（堆疊資料被破壞）", "程式錯誤地寫到某個stack object範圍之外，覆蓋鄰近local data、saved state或return資訊。", "把8 bytes寫進只有4 bytes的local array。", "Crash可能晚很多才發生；最後倒下的位置不一定是最早寫壞的位置。"),
    FoundationTerm("c-string", "C string（C字串）", "以一串bytes保存文字，並用值為0的NUL byte標記結尾。", "`char name[4]`最多容納3個一般單byte字元加一個`'\\0'`。", "Array容量與目前字串長度不同；若沒有NUL，字串函式可能越界讀取。"),
    FoundationTerm("undefined-behavior", "Undefined behavior／UB（未定義行為）", "C標準對某次操作不再承諾任何結果；compiler可假設合法程式不會發生它。", "越界存取、use-after-free、部分signed overflow。", "UB不是『一定立刻crash』；看似正常也不代表合法。"),
    FoundationTerm("sanitizer", "Sanitizer（動態錯誤偵測工具）", "Compiler在程式中加入額外檢查，執行時發現特定類型的非法行為。", "ASan檢查部分越界與use-after-free；UBSan檢查部分undefined behavior。", "它不是防毒軟體，也不能證明沒報錯的程式完全正確。"),
    FoundationTerm("asan", "ASan／AddressSanitizer", "一種sanitizer，利用instrumentation與shadow memory偵測許多memory bounds/lifetime錯誤。", "以`-fsanitize=address`編譯後，越界寫入可在發生處報告call stack。", "只檢查被instrument且實際執行到的路徑，並非所有memory bug都能抓到。"),
    FoundationTerm("crash", "Crash、SIGSEGV", "Crash是process因未處理錯誤而終止；SIGSEGV是Unix-like OS常用來通知非法memory access的signal。", "解參考無效pointer可能收到SIGSEGV。", "SIGSEGV指出最後被阻止的access，不保證那一行就是最早根因。"),
]


BRIDGES = [
    FreshmanBridge("prereq", 0, "你已經知道變數、array、function與DSA的stack/heap名稱。", "本章要把抽象資料結構接到C object、address、pointer與resource lifetime；同名詞在systems裡可能有不同意思。", "DSA告訴你stack支援push/pop；systems還要問stack的bytes在哪、誰建立frame、越界會覆蓋什麼。", ("能分清DSA stack與call stack", "知道program與process不同", "知道debugger是觀察工具")),
    FreshmanBridge("ch1", 1, "你知道source code經由程式語言描述演算法。", "現在要追source如何變成CPU可執行bytes，以及OS如何建立一次running process。", "像把食譜交給不同工作站：翻譯、分裝、組裝、上架；每站都有自己的輸入、輸出與錯誤。", ("能說明compiler與linker差異", "知道executable不是process", "知道system call是application到kernel的入口")),
    FreshmanBridge("ch2", 2, "你會分析integer、array index、bit operations與hash。", "現在要理解數學整數如何被有限bits表示，以及型別轉換、overflow與floating rounding。", "紙上整數沒有邊界；機器像只有固定格數的里程表，超出後必須依規則處理。", ("會把hex轉成bits", "知道signed與unsigned值域", "知道endianness只排列bytes")),
    FreshmanBridge("ch3", 3, "你知道function、loop、recursion、array與struct的高階語意。", "現在要看compiler如何用register、jump、stack frame與addresses實作它們。", "高階語言像地圖上的路線；assembly像逐個路口的轉彎指示，需重新組成完整資料流。", ("知道register是CPU storage", "知道call stack保存呼叫狀態", "知道ABI是binary協作規則")),
    FreshmanBridge("ch4", 4, "你知道DAG dependency與state machine。", "現在把instruction視為有dependency的工作，理解CPU如何pipeline、forward、stall與flush。", "洗衣流程可同時讓不同批次處於洗、烘、折；但下一步需要前一步結果時仍得等待。", ("分清latency與throughput", "能指出producer與consumer", "知道architectural state是軟體可見結果")),
    FreshmanBridge("ch5", 5, "你會Big-O並知道較好的algorithm通常更快。", "現在加入constant、CPU cycles、dependency、cache與benchmark noise，判斷實機瓶頸。", "Big-O像比較道路成長趨勢；profile與counter則告訴你今天塞在哪個路口。", ("先定義metric與workload", "知道profile找時間占比", "知道Amdahl限制局部改善")),
    FreshmanBridge("ch6", 6, "你知道array連續、linked list靠pointer、hash table會碰撞。", "現在研究address stream如何落到cache lines/sets，以及working set、TLB與bandwidth。", "書桌放近期會用的書；每次從書庫搬一整箱，若只用一頁就丟掉，搬運成本很浪費。", ("分清cache line與set", "知道temporal/spatial locality", "知道TLB cache的是地址轉譯")),
    FreshmanBridge("ch7", 7, "你知道大型程式可拆成functions與modules。", "現在理解分開編譯後，跨檔名稱如何以symbols/relocations合併，執行時library如何載入。", "每個小組先做零件並附標籤與待接接口；linker最後安排位置、接線並完成產品。", ("知道object file不是C object", "知道object format是binary容器規格", "知道link與load發生在不同時間")),
    FreshmanBridge("ch8", 8, "你知道function call會改變control flow，也知道queue/tree可描述狀態。", "現在加入OS可插入的exception flow、process建立/替換/回收，以及非同步signal。", "一般control flow像照劇本演出；exception像場務因火警、計時器或服務請求暫停演出並交給管理者。", ("知道process是running program", "知道fork/exec/wait角色不同", "知道signal是通知而非可靠queue")),
    FreshmanBridge("ch9", 9, "你知道array index把logical位置對到element，hash table把key對到bucket。", "現在看virtual address如何經page table對到physical frame，以及allocator如何在pages內切blocks。", "虛擬地址像公寓門牌，page table像管理室的門牌對實際房間表；malloc再分配房內空間。", ("知道virtual與physical address不同", "分清TLB miss與page fault", "知道heap allocator維護metadata")),
    FreshmanBridge("ch10", 10, "你用過Python的`open/read/write`，知道stream是一串有順序的資料。", "現在看fd如何引用kernel object、為何I/O會partial、EOF如何由所有references共同決定。", "fd像process錢包裡的取件號碼；真正包裹與進度保存在物流系統，不在號碼本身。", ("知道fd是process-local index", "接受short read是正常結果", "知道close只移除一個reference")),
    FreshmanBridge("ch11", 11, "你知道graph上的路徑、queue與producer-consumer。", "現在理解IP/TCP/socket只運送bytes，application還要定義message framing、deadline與重試語意。", "TCP像保證順序的水管，不會替你標出哪幾滴屬於同一杯；杯子的邊界由protocol決定。", ("知道一次send不等於一次recv", "知道framing重建message", "知道timeout不代表server一定沒完成")),
    FreshmanBridge("ch12", 12, "你知道queue、semaphore概念，並會推理多步algorithm invariant。", "現在允許多個flows任意交錯，學習用ownership、mutex、condition與bounded queue維持安全與進度。", "兩人同改一份白板時，問題不只誰先寫；還要約定哪些內容一起改、何時可看、塞車時誰等待。", ("分清concurrency與parallelism", "先寫shared-state invariant", "知道bounded queue提供backpressure")),
]


PRIMER_BODY = r"""
<section id="freshman-primer">
  <span class="chapter-tag">Start Here · No Systems Background Required</span>
  <h2>大一生的 Systems Primer：先建立這個世界，再讀 CS:APP</h2>
  <p class="freshman-lead">本節假設你只學過變數、函式、資料結構與演算法，不假設你會 C、Linux、組合語言或作業系統。你不需要先查外部資料。讀完後，後文的 system call、GDB、object format、stack corruption、ASan 與 watchpoint 才有上下文。</p>

  <div class="freshman-promise">
    <strong>讀完本節，你應該能回答：</strong>
    <span>程式與 process 差在哪？OS 與 kernel 做什麼？Application 為何需要 system call？Source 如何變成 executable？GDB、breakpoint、watchpoint、ASan 分別觀察什麼？Stack corruption 為何常在很晚才 crash？</span>
  </div>

  <h3>0. 先用一張圖看完整世界</h3>
  <pre class="diagram deep-map"><code>你寫的 source code（C / Python）
        │
        ├─ Python：interpreter 本身是一個已編譯程式，讀取並執行 Python
        │
        └─ C：compiler → assembler → object files → linker → executable
                                                        │
你在 shell 輸入 ./app                                  │
        ↓                                               │
作業系統建立 process ← loader 把 executable / libraries 放進 virtual memory
        ↓
CPU 從 memory 取得 machine instructions，使用 registers 執行
        ↓
需要檔案、網路、更多 memory？
        ↓ system call：user mode → kernel mode
kernel 檢查權限並操作 filesystem / network / devices
        ↓
結果回到 process；debugger / sanitizer / trace tools 可從不同邊界觀察</code></pre>

  <p>這本書後面所有章節都只是把圖中的某一條箭頭放大。Chapter 2 放大「值如何變成bits」；Chapter 3–4 放大「CPU如何執行instructions」；Chapter 6與9放大「memory如何被cache與映射」；Chapter 7放大「object files如何變executable」；Chapter 8–12放大「process如何透過kernel與其他程式合作」。</p>

  <h3 id="primer-hardware">1. 一台電腦最少有什麼？</h3>
  <p><strong>CPU</strong>負責執行很小的machine instructions；<strong>registers</strong>是CPU手邊少量快速儲存；<strong>RAM</strong>保存目前執行中的code與data；<strong>SSD/disk</strong>保存關機後仍要存在的檔案。CPU比RAM快，RAM又比storage快，因此後面會出現cache與memory hierarchy。</p>
  <p>DSA常把memory當成可用的抽象array，分析一次存取為O(1)。Systems不推翻這個抽象，而是再問：這個address對應哪個page？資料是否在cache？這次存取是否合法？O(1)背後可能差幾十到幾百倍constant。</p>

  <h3 id="primer-process">2. Program、executable、process 不同在哪？</h3>
  <table>
    <tr><th>東西</th><th>最簡單說法</th><th>何時存在</th></tr>
    <tr><td>Source code</td><td>人寫的程式文字</td><td>編輯與build時</td></tr>
    <tr><td>Executable</td><td>包含machine code與載入資訊的binary檔</td><td>磁碟上的artifact</td></tr>
    <tr><td>Process</td><td>一次正在執行的程式，含register、memory、fd等state</td><td>OS啟動後到結束</td></tr>
  </table>
  <p>類比：食譜是source，已包裝好的料理包是executable，廚師依料理包正在做的一鍋菜是process。同一料理包可以同時做很多鍋；每鍋目前做到哪一步、用了哪些材料都不同。</p>

  <h3 id="primer-os-kernel">3. OS、kernel、user mode 是什麼？</h3>
  <p>若每個application都能直接改任何memory、disk與network device，一個bug就能破壞整台電腦。CPU與OS因此把執行分成不同權限。Application平常在<strong>user mode</strong>，只能碰自己的合法memory與一般instructions；<strong>kernel</strong>在kernel mode管理全系統資源。Operating system包含kernel與許多周邊system programs。</p>
  <p>這是保護邊界，不是效能裝飾。當application需要特權工作，不能自己把權限打開，而要走system call入口，讓kernel驗證參數、權限與目前resource state。</p>

  <h3 id="primer-system-call">4. 什麼是 system call？</h3>
  <p><strong>System call是application請kernel代辦工作的正式介面。</strong>例如從檔案讀bytes、向terminal寫字、建立process、配置memory mapping、建立network connection。Application先把operation編號與arguments放在<strong>ABI（已編譯程式與OS約定如何傳值的binary規則）</strong>指定位置，執行一條特殊instruction切入kernel；kernel檢查後執行，最後返回result或error。</p>
  <pre class="diagram deep-map"><code>Python print("hi")
  ↓ Python runtime / C library 先做文字轉換與buffering
write(fd=1, bytes="hi\n", count=3)
  ↓ system-call boundary
kernel：fd 1 現在指向terminal、file還是pipe？
  ↓ driver / filesystem / pipe state
bytes抵達目的地

注意：print 是高階library operation；write 是可能跨入kernel的system call。
兩者不是同義詞，也不保證一對一。</code></pre>
  <pre><code>import os

message = b"hello from a system-call wrapper\n"
written = os.write(1, message)   # 1 通常是 stdout 的 file descriptor
print("kernel accepted bytes:", written)</code></pre>
  <p>Python的<code>os.write</code>仍是library wrapper，但它非常接近OS的<code>write</code>介面。回傳值表示這次接受了多少bytes，不代表螢幕一定已完成顯示，也不代表disk資料已持久化。</p>

  <h3 id="primer-build">5. Source 怎樣變成 executable？Object format 又是什麼？</h3>
  <pre class="diagram deep-map"><code>main.c
  ↓ compiler：理解C語意，產生assembly
main.s
  ↓ assembler：把assembly變成instruction bytes
main.o  ← object file：尚未完全接好的binary零件
  + helper.o + libraries
  ↓ linker：解析symbols、安排位置、修補relocations
app     ← executable
  ↓ loader：建立process memory mappings與初始state
CPU開始執行</code></pre>
  <p><strong>Object file</strong>是一個binary零件；<strong>object format</strong>則是這種binary零件的「包裝與目錄規格」。想像物流箱除了零件本身，還要有標籤：哪一區是code、哪一區是data；<strong>symbol</strong>記錄可供linker辨識的名稱；<strong>relocation</strong>記錄哪些位置要等最終地址確定後再修補。Linux常用的規格叫<strong>ELF（Executable and Linkable Format）</strong>。工具能讀ELF，是因為它們知道header與各表格如何排列。</p>
  <div class="freshman-contrast">
    <article><h4>C object</h4><p>一段保存值的storage，例如一個int或array。</p></article>
    <article><h4>Object file</h4><p>compiler/assembler產生的<code>.o</code> binary檔。</p></article>
    <article><h4>Object format</h4><p>規定binary內各區塊與metadata如何排列的標準。</p></article>
  </div>

  <h3 id="primer-stack">6. Call stack、heap 與 stack corruption</h3>
  <p>Function被呼叫時，需要保存「返回哪裡」、部分local data與saved registers，這些資訊通常形成一個<strong>stack frame</strong>。多層function calls形成call stack。動態、壽命不跟單一function綁定的memory通常向heap allocator要求。</p>
  <pre class="diagram deep-map"><code>較高地址
┌──────────────────────┐
│ caller 的 stack frame│
├──────────────────────┤
│ return information   │  ← function結束時需要
├──────────────────────┤
│ int count            │
├──────────────────────┤
│ char name[4]         │  ← 合法index只有0..3
└──────────────────────┘
較低地址

若程式錯把8 bytes寫進name[4]，多出的bytes可能覆蓋count或return資訊。
這就叫stack corruption：stack上的資料被越界寫壞。</code></pre>
  <p>真正layout由compiler與ABI決定，圖只是心智模型。危險在於越界寫發生時程式可能沒有立刻crash；被覆蓋的return資訊直到function結束才使用，因此「最後在return crash」不代表return本身做錯。除錯要找<strong>第一個壞寫入</strong>。</p>

  <h3 id="primer-gdb">7. GDB、breakpoint、watchpoint 是什麼？</h3>
  <p><strong>GDB（GNU Debugger）</strong>是Linux常用debugger。Debugger能控制另一個process：在指定位置暫停、一步步執行、讀register與memory、查看call stack。它像替執行中的程式按暫停並查看現場。</p>
  <table>
    <tr><th>命令</th><th>白話意思</th><th>何時使用</th></tr>
    <tr><td><code>gdb ./app</code></td><td>用GDB載入executable與debug symbols</td><td>開始debug session</td></tr>
    <tr><td><code>break main</code></td><td>在main入口設breakpoint</td><td>到這個執行位置時停下</td></tr>
    <tr><td><code>run</code></td><td>啟動被debug的process</td><td>第一次或重新執行</td></tr>
    <tr><td><code>next</code></td><td>執行下一行，不進被呼叫function</td><td>高階逐行觀察</td></tr>
    <tr><td><code>step</code></td><td>執行下一行，必要時進入function</td><td>追進可疑function</td></tr>
    <tr><td><code>print x</code></td><td>顯示expression目前值</td><td>檢查state</td></tr>
    <tr><td><code>bt</code></td><td>顯示backtrace，也就是目前call stack</td><td>看誰一路呼叫到這裡</td></tr>
    <tr><td><code>watch count</code></td><td>當count所在memory被寫時暫停</td><td>找出誰第一次改壞資料</td></tr>
  </table>
  <p><strong>Breakpoint監看執行位置；watchpoint監看資料位置。</strong>如果你知道<code>count</code>在稍後已經錯了，可先在仍正確時設<code>watch count</code>，讓GDB在第一次寫它時停下。Hardware可用watchpoints數量有限，而且只能看到這一次執行走過的路徑。</p>

  <h3 id="primer-asan">8. ASan 是什麼？和 GDB 有何不同？</h3>
  <p><strong>ASan（AddressSanitizer）</strong>由compiler在程式中插入額外檢查；這個插入過程叫<strong>instrumentation</strong>。執行時它追蹤哪些memory區域合法。越界、use-after-free（object lifetime結束後仍透過舊pointer使用）等錯誤發生時，它常能立即報告access位置、call stack與allocation來源。</p>
  <pre><code>cc -Wall -Wextra -g -fsanitize=address demo.c -o demo-asan
./demo-asan</code></pre>
  <p><code>-g</code>保留debug資訊，讓報告可顯示source line；<code>-fsanitize=address</code>開啟ASan instrumentation。ASan會增加memory與runtime成本，通常用於開發與測試。它沒報錯只代表「這次、這些被instrument的路徑、它能偵測的錯誤」沒被發現，不是完整正確性證明。</p>
  <div class="freshman-contrast">
    <article><h4>ASan</h4><p>自動在錯誤access發生附近報告，適合先捕捉memory bounds/lifetime問題。</p></article>
    <article><h4>GDB breakpoint</h4><p>在指定code位置暫停，適合逐步觀察control與state。</p></article>
    <article><h4>GDB watchpoint</h4><p>在指定資料被改動時暫停，適合找第一個錯誤writer。</p></article>
  </div>

  <h3 id="primer-corruption-walkthrough">9. 完整走一次：找 stack corruption 的第一個壞寫入</h3>
  <pre><code>#include &lt;stdio.h&gt;

void copy_name(const char *input) {
    char name[4];
    int count = 7;
    for (int i = 0; input[i] != '\0'; ++i) {
        name[i] = input[i];   // input超過3字元時會越界；還需保留'\0'
    }
    printf("%s %d\n", name, count);
}

int main(void) {
    copy_name("abcdefgh");
}</code></pre>
  <ol>
    <li><strong>先說contract：</strong><code>name</code>只有4 bytes，若要當C string，最多放3個字元加結尾<code>'\0'</code>。</li>
    <li><strong>找第一個違規：</strong>當<code>i == 4</code>時，<code>name[4]</code>已超出array bounds；這比最後在哪裡crash更接近根因。</li>
    <li><strong>先跑ASan：</strong>它常會在越界store處報stack-buffer-overflow與call stack。</li>
    <li><strong>需要更多state時進GDB：</strong>在loop設breakpoint，印<code>i</code>與地址；若某鄰近值稍後被改壞，可設watchpoint找writer。</li>
    <li><strong>修contract：</strong>傳入destination capacity、先驗證length、確保終止；不要只把array改大來掩蓋。</li>
    <li><strong>加regression：</strong>測空字串、剛好容納、超長input與不同最佳化設定。</li>
  </ol>
  <div class="warning"><strong>重要：</strong>局部變數的實際順序由compiler決定，示意圖不能預測一定覆蓋count或return address。你可依賴的是「越界本身已違反C contract」，而不是某一次memory layout的偶然結果。</div>

  <h3>10. 第一次操作時，只需記住這個順序</h3>
  <pre class="diagram deep-map"><code>我看到陌生術語
  ↓ 先讀本Primer的白話定義與邊界
我看到程式錯誤
  ↓ 固定輸入，讓問題可重現
先用compiler warnings / ASan找明確違規
  ↓
再用GDB breakpoint / watchpoint觀察「何時開始錯」
  ↓
修正bounds、ownership、lifetime或state transition
  ↓
加入能重現原問題的test

不要：看到crash → 隨機改code → 剛好不crash → 宣稱修好</code></pre>

  <h3>Primer 理解確認</h3>
  <details class="freshman-qa"><summary>Q1. Program與process最短的區別是什麼？</summary><div><p>Program是儲存好的code/data；process是它某一次正在執行的state。Process還包含registers、virtual memory mappings、open file descriptors與目前執行位置。同一program可以同時有很多process。</p></div></details>
  <details class="freshman-qa"><summary>Q2. 為何application不能直接操作所有硬體？</summary><div><p>如果沒有權限隔離，一個bug就能讀別人的memory、破壞filesystem或讓device進入錯誤狀態。Application在user mode，kernel在高權限mode集中管理資源；system call是經驗證的受控入口。</p></div></details>
  <details class="freshman-qa"><summary>Q3. System call與一般function call差在哪？</summary><div><p>一般function call通常仍在同一user-mode process內跳到另一段code；system call會依ABI進入kernel，跨越權限邊界，讓kernel驗證並執行特權操作。Library function可能完全不需system call，也可能在內部包裝一個或多個system calls。</p></div></details>
  <details class="freshman-qa"><summary>Q4. Object file、object format與C object有何不同？</summary><div><p>C object是一段保存值的storage；object file是build過程產生的binary零件；object format是規定該binary內header、code、data、symbols與relocations如何排列的標準。ELF是Linux常見object format。</p></div></details>
  <details class="freshman-qa"><summary>Q5. Linker與loader分別何時工作？</summary><div><p>Linker通常在build時合併object files、解析symbols並修補地址，產生executable/shared library；loader在執行時依executable描述建立process mappings、載入libraries並設定entry state。兩者都處理地址，但時間與責任不同。</p></div></details>
  <details class="freshman-qa"><summary>Q6. Stack corruption為何可能晚很久才crash？</summary><div><p>越界store可能先覆蓋目前尚未使用的local/saved data；直到function return或後續code讀取該值才顯現。Crash位置只是資料第一次被用到而造成不可繼續的位置，真正根因是更早的第一個非法write。</p></div></details>
  <details class="freshman-qa"><summary>Q7. Breakpoint與watchpoint如何選？</summary><div><p>想在某function/line/address停下，用breakpoint；已知某個值稍後被改壞，想找第一個writer，用watchpoint。實務上常先用breakpoint走到初始化完成、確認值正確，再設watchpoint縮小範圍。</p></div></details>
  <details class="freshman-qa"><summary>Q8. ASan與GDB誰比較好？</summary><div><p>它們解決不同問題。ASan自動偵測多種memory bounds/lifetime違規，適合先找到錯誤access；GDB讓你控制執行並檢查state，適合深入理解如何走到那裡。常見流程是ASan定位，再用GDB重現與觀察。</p></div></details>
  <details class="freshman-qa"><summary>Q9. ASan沒報錯是否代表沒有memory bug？</summary><div><p>不代表。錯誤path可能沒執行、某些library沒被instrument、bug類型可能不在ASan能力內。仍要搭配warnings、tests、UBSan/TSan、static analysis與清楚的bounds/ownership設計。</p></div></details>
  <details class="freshman-qa"><summary>Q10. 為何本書一直要求找第一個錯誤state？</summary><div><p>系統錯誤常延遲顯現：越界先寫壞memory、稍後return才crash；錯誤length先通過，之後allocation才出事。找到「最後仍正確」與「第一個變錯」之間的transition，才能修根因，而不是修最後症狀。</p></div></details>
</section>
"""


assert len(FOUNDATION_TERMS) >= 32
assert [bridge.number for bridge in BRIDGES] == list(range(13))
