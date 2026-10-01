"""Deepening content for CS:APP chapters 10–12."""
from csapp_supplement_model import S


SUPPLEMENTS = [
    S(
        "ch10",
        10,
        "系統級 I/O：descriptor、kernel objects 與 robust loops",
        "為何一個小整數 fd 能代表 file、pipe、terminal 與 socket，卻又藏著許多狀態？",
        (
            "path或既有descriptor、buffer、requested byte count與flags",
            "process descriptor table指向kernel open-file state，再由type-specific object完成I/O",
            "能正確處理short count、EINTR、EOF、sharing、redirection與durability",
        ),
        [
            ("File descriptor", "Process-local的小整數索引，本身不是file內容或全系統唯一identity。", "fd 1通常是stdout，但shell可在exec前讓它指向pipe或regular file。"),
            ("Open file description", "Kernel中保存offset、status flags等open instance state的object，可被多個fd entries共享。", "`dup`與`fork`後的descriptors可共同推進同一offset。"),
            ("Short count", "成功I/O處理的bytes少於requested count，是stream/device API的正常結果。", "`read(fd, buf, 4096)`可能只回37。"),
            ("EOF", "資料來源不會再提供更多bytes的狀態，不是某個特殊byte。", "Pipe只有在所有write-end references關閉且buffer耗盡後read才回0。"),
            ("Durability", "資料在crash/power loss後仍能依承諾存在的性質。", "`write`成功通常不等於disk已完成持久化。"),
        ],
        r"""
process fd table
  fd 0 ─┐
  fd 1 ─┼─> open file description
  fd 4 ─┘    offset + status flags + refcount
                    ↓
         inode / pipe / socket / terminal object
                    ↓
             filesystem / peer / device

read/write loop:
request N → positive k (advance) | 0 EOF | -1 errno
                    ↘ EINTR retry under API policy

fork/dup share references; close removes one reference
last relevant writer closes → pipe/socket peer may observe EOF
""",
        r"""
### 10.A Unix I/O 的力量來自小介面與不同實作

Regular file、directory、pipe、terminal、device、socket都可透過descriptor-oriented API操作，但它們不具有完全相同語意。Regular file有seekable offset；pipe/socket是stream且通常不可seek；terminal受line discipline與foreground process group影響；directory要用專用迭代API。『Everything is a file』是組合心智模型，不是每個operation都適用。

`open`先做path resolution、permission與flags處理，再建立或引用kernel objects並在process fd table配置最低可用entry。`close`只移除當前entry/reference；其他dup/inherited references仍可使用。程式應在ownership轉移與error path都清楚close，並用`O_CLOEXEC`或`FD_CLOEXEC`避免descriptor意外跨exec洩漏。

### 10.B 三層表模型解釋 sharing

Process fd entry保存descriptor flags並指向open file description；後者保存file offset與file status flags，再指向filesystem inode/vnode或pipe/socket state。`dup`建立另一fd entry指向同一open description；`fork`複製fd table entries，也共享底層open descriptions。因此parent與child讀同一regular file可互相推進offset。

若各自重新`open`同一路徑，會得到不同open descriptions與offset，但最終可能指向同一file object。這個差別影響append、locking與競爭推理。

### 10.C Robust I/O 是狀態機，不是一個 `read`

`read`正數代表成功取得k bytes；k可小於request。0代表EOF；-1才看`errno`。`EINTR`表示在完成前被signal打斷，通常可重試，但某些API或有partial side effect的operation需讀個別contract。Nonblocking fd的`EAGAIN/EWOULDBLOCK`表示目前無資料，不是永久錯誤，應回event loop等待readiness。

```c
ssize_t readn(int fd, void *buf, size_t n) {
    size_t off = 0;
    while (off < n) {
        ssize_t k = read(fd, (char *)buf + off, n - off);
        if (k > 0) off += (size_t)k;
        else if (k == 0) break;
        else if (errno != EINTR) return -1;
    }
    return (ssize_t)off;
}
```

這個loop適合「最多讀n bytes直到EOF」；protocol若要求恰好n，caller還要檢查return是否等於n。`write`也可能short；遇broken pipe可能收到EPIPE與SIGPIPE。API要定義partial progress如何回報。

### 10.D EOF 取決於reference lifecycle

Pipe reader只有在buffer空且系統中沒有任何write-end reference時才讀到0。Fork後每個process都繼承兩端，若任一process忘記close不使用的writer，reader會永遠等待。Socket half-close `shutdown(SHUT_WR)`可表示不再送bytes但仍接收，與close整個descriptor不同。把所有references畫出來，EOF問題就從玄學變成refcount。

### 10.E Redirection 是在 child 改環境

Shell在fork後、exec前open目標並用`dup2(newfd, STDOUT_FILENO)`，讓新program照常寫fd 1。`dup2`若target已開會原子地替換，避免close+dup之間被signal/thread搶走fd。成功後要close多餘descriptor，並處理source恰好等於target的情況。

Pipeline同理：每個child只保留需要的read/write end。Shell本身關閉兩端後wait。這種「application遵守標準fd contract，組合者改連線」是Unix composition核心。

### 10.F stdio 多了一層user-space state

`FILE *`除了fd還有buffer、error/EOF flags、locking與conversion state。Terminal stdout常line-buffered，redirect到file可能fully buffered；stderr策略依實作。Fork會複製尚未flush的user buffer，造成重複輸出。混用stdio與raw descriptor I/O時，兩層buffer與offset可能失同步，除非遵守標準同步規則。

### 10.G Atomicity、ordering與durability分開

一次`write`對某些object/size/flags可能有原子性保證，但多次writes組成的record仍可交錯。`O_APPEND`讓每次write的offset selection與write在kernel中原子結合，卻不保證跨多次call的transaction。`fsync`/`fdatasync`與directory sync涉及crash durability；rename常提供namespace atomic replacement，但完整可靠update還需temp file、flush、rename與parent directory policy，並依filesystem測試。

### 10.H Path安全與TOCTOU

先`stat(path)`再`open(path)`之間path可被替換，形成time-of-check/time-of-use race。優先使用能在同一次kernel operation帶flags驗證的API，以及dirfd-relative/openat系列、`O_NOFOLLOW`等；但完整安全依威脅模型與平台。Descriptor一旦取得通常比持續依賴可變path更適合作為capability。
""",
        r"""
寫一組pipe實驗：parent建立pipe後fork，刻意保留一個不使用的write end，觀察reader不收到EOF；再逐一關閉references。接著建立socketpair，把每次write/read最大長度故意限制為1–7 bytes，驗證framing loop不依賴單次完整I/O。最後以`strace -f -e trace=desc,file`核對實際open/dup/close順序。

```bash
strace -f -yy -e trace=openat,close,dup,dup2,read,write,pipe,socketpair ./fd_lab
ls -l /proc/$PID/fd
cat /proc/$PID/fdinfo/3
```
""",
        [
            "把fd當成全系統唯一file identity或直接保存到持久資料。",
            "把short read/write視為罕見錯誤，只在localhost測試。",
            "Fork/pipe後沒有逐process列出要關閉的ends。",
            "混用stdio/raw I/O，忽略user buffer與kernel offset。",
            "把`write`或`close`成功當成資料已durable。",
        ],
        [
            ("`dup`後兩個fd共享什麼、不共享什麼？", "它們是不同fd table entries，可有各自close-on-exec descriptor flag；但指向同一open file description，因此共享current offset與file status flags如O_APPEND。關閉一個entry不影響另一個，直到最後reference消失。"),
            ("Pipe reader為何可能永遠收不到EOF？", "EOF要求pipe buffer耗盡且所有write-end references都關閉。Fork後parent/children可能各持一份writer，即使真正producer已close，任何遺漏reference仍讓kernel認為未來可能有資料。需要逐process立即close不使用的ends。"),
            ("為何一次`read`不能當成一個message？", "Stream API只承諾有序bytes，不保留application write boundaries；kernel buffering、network segmentation或signal可讓一次read取得半個、多個或任意片段message。Application必須用length-prefix、delimiter或fixed-size framing重組。"),
            ("`dup2`為何優於`close(1); dup(fd);`？", "後者在close與dup之間有window，signal handler或另一thread可能open新fd占用1，造成錯誤連線；`dup2`對target替換是單一原子operation。它也明確指定target，不依賴最低可用fd猜測。"),
            ("`O_APPEND`保證了什麼，又沒有保證什麼？", "它使每次write在寫入前將offset設到EOF並與該write原子結合，避免多writers因共享/獨立offset覆蓋；不保證多次writes組成的record不交錯，也不等於durability或distributed filesystem上所有相同語意。"),
            ("`write`成功、`fsync`成功與使用者看到資料各代表什麼？", "`write`通常表示kernel接受bytes；reader可見性依buffer/cache與object；`fsync`要求把相關file data/metadata推到穩定儲存的特定contract，但rename/directory entry可能另需sync。使用者看到還經過應用protocol與device，三者不是同一完成點。"),
            ("如何設計能回報partial progress的write API？", "Return已寫bytes與明確error，或維護buffer offset讓caller/event loop續寫；不能失敗時只回boolean丟掉已完成量。對有side effect的protocol還要定義重試/idempotency，因peer可能已收到prefix。"),
        ],
        ["csapp-asides", "linux-man", "posix", "csapp-labs"],
    ),
    S(
        "ch11",
        11,
        "網路程式設計：從 byte stream 到可恢復協定",
        "Socket讓兩台主機交換bytes之後，application還必須自己定義什麼？",
        (
            "endpoint addresses、requests、timeouts、bytes與業務side effects",
            "DNS/IP/TCP/socket傳遞ordered stream；application protocol負責framing、語意與恢復",
            "能建立正確client/server lifecycle並處理partial I/O、ambiguity、overload",
        ),
        [
            ("Socket", "Process中的network communication endpoint，以fd介面操作。", "Listening socket接新連線；`accept`回傳connected socket服務特定peer。"),
            ("Framing", "把沒有message boundary的byte stream切回application messages的規則。", "4-byte length prefix加payload。"),
            ("Byte order", "多byte integer在protocol中的排列；Internet protocols慣用network byte order。", "`htons`/`ntohl`或明確byte decode在host與wire format間轉換。"),
            ("Deadline", "整個operation剩餘可用的絕對時間預算。", "Request總共500ms，DNS/connect/write/read共享這個budget。"),
            ("Ambiguous outcome", "Client無法判斷server是否已完成side effect。", "付款commit後response在網路遺失，client只看到timeout。"),
        ],
        r"""
name → DNS resolution → candidate IP addresses
client socket → connect → TCP connection
server: socket → bind → listen → accept connected socket

application message
  encode fields + length/delimiter
        ↓ repeated write
TCP ordered byte stream
        ↓ repeated read + parser state
validated message → business operation → application response

failure:
timeout / reset / EOF / overload / response lost
  ↓ protocol policy: retry? idempotency key? status query? reject?
""",
        r"""
### 11.A Network不是socket API的同義詞

Application先把hostname與service解析成address candidates；IP負責跨network傳datagrams，TCP在endpoints間提供有序、可靠、無重複的byte stream（在連線存活範圍內），socket是OS提供的programming interface。可靠stream不保證低延遲、peer application已處理、server不會crash，也不保證message boundaries。

IPv4/IPv6、DNS多結果與dual-stack讓程式不應手組單一`sockaddr_in`假設。`getaddrinfo`提供addresses list，client應依policy嘗試並處理timeout；server可用`AI_PASSIVE`建立bind candidates。Address文字格式與binary representation要用標準conversion。

### 11.B Client/server lifecycle

Server建立socket、設定必要options、bind local address、listen backlog，再loop accept。Listening socket代表passive endpoint；每次accept產生connected socket，local/peer四元組區分connection。Client建立socket並connect。Close/shutdown與error paths都要清楚ownership。

Backlog不是application無限queue，也不是capacity替代品；不同OS有不同細節。Server若accept/processing跟不上，latency與拒絕會出現在kernel queue、application queue或client timeout。需要bounded concurrency與overload policy。

### 11.C TCP只給bytes，所以parser必須是state machine

一次send可能被多次recv；多次send也可能一次recv。Length-prefix parser至少有`READ_HEADER`與`READ_BODY` state，累積bytes直到足夠，再驗證length上限、配置/引用buffer並讀payload。Delimiter protocol要處理delimiter跨buffer、line太長與escape。EOF若發生在message中間是truncated protocol error，而非正常完成。

```text
READ_LEN(need 4)
  ├─ bytes不足 → 保存offset，等待readable
  ├─ EOF且offset=0 → clean close
  └─ 4 bytes → decode+validate length
READ_BODY(need N)
  ├─ bytes不足 → 保存offset
  ├─ EOF → truncated message
  └─ complete → dispatch，再回READ_LEN
```

永遠先限制N，再做allocation；避免memory exhaustion與integer overflow。

### 11.D Blocking、nonblocking與readiness

Blocking call可讓thread睡到progress/error；nonblocking call在目前不能progress時回EAGAIN，由`select/poll/epoll/kqueue`等通知readiness。Readiness不是完成保證：事件到處理間state可變，且一次操作仍可能short；每次都loop直到EAGAIN。I/O multiplexing解決很多connections的等待成本，不讓CPU-heavy handler自動平行，也不防slow handler阻塞event loop。

### 11.E Timeout要用deadline傳遞

每層各自固定5秒，經DNS、connect、TLS、queue、RPC會把總時間放大。以monotonic clock計算absolute deadline，每個子步驟只使用remaining budget。Timeout後要取消或忽略late result，server也應知道client deadline，避免完成已無價值工作。

Retry只適合transient error且operation可安全重做。Exponential backoff+jitter降低同步重試，但不能修非idempotent side effect；budget內的attempts也要bounded。

### 11.F Ambiguous outcome是distributed systems核心

Client成功write只代表local kernel接受bytes；即使TCP ACK，也只證明remote network stack收到，不證明application commit。Server可能完成付款後在response送達前crash，client看到timeout無法判斷。解法是application-level idempotency key、deduplication、operation status query與明確response semantics，不是盲目重送。

### 11.G HTTP是application protocol，不是魔法

HTTP message有start line/headers/body framing，HTTP/1.1 persistent connection要求正確Content-Length/chunked處理；hop-by-hop headers、proxying與connection close都需遵守規則。簡化proxy lab的目標是練parser、robust I/O、concurrency與cache，不應把「找到空行」當完整production HTTP implementation。Production使用成熟library並限制header/body、timeouts與request smuggling風險。

### 11.H Overload、backpressure與安全

Unbounded thread/queue讓arrival rate超service rate時memory與latency一起失控。Bounded queue、connection limit、per-client quota、early rejection與load shedding保護有價值work。Protocol parser面對untrusted bytes，要有長度上限、incremental parsing、canonicalization、resource budget與fuzzing；network code首先是adversarial input code。
""",
        r"""
實作length-prefixed echo protocol，client故意把header/body切成隨機1–5 byte writes，server使用parser state累積。加入maximum length、monotonic deadline、half-close與truncated message測試；再用`tc netem`或本地proxy注入delay/reset，確認不存在「一次recv等於一個message」假設。

```bash
strace -f -e trace=network,read,write ./server
ss -ltnp
tcpdump -i lo -nn -X 'tcp port 8080'
```

最後加入帶idempotency key的`INCREMENT` operation：server保存key→result，故意在commit後丟response，再讓client重試，驗證counter只增加一次。
""",
        [
            "把TCP segment、send call、recv call與application message一一對應。",
            "讀到length後先allocation，再檢查上限與overflow。",
            "每一層使用獨立timeout，沒有共享end-to-end deadline。",
            "任何timeout都重試，未處理non-idempotent ambiguous outcome。",
            "用unboundedthreads/queue吸收流量，直到記憶體與tail latency崩潰。",
        ],
        [
            ("Listening socket與connected socket有何不同？", "Listening socket代表passive endpoint與pending connection queues，用accept取得新connection；connected socket綁定local/peer endpoint並承載stream bytes。Server通常保留一個listener，為每個client持有獨立connected fd。"),
            ("TCP為何不保留`send`邊界？", "TCP sequence space描述連續bytes，stack可依MSS、buffer、Nagle、retransmission等任意切分/合併segments；receiver API只回目前可用bytes。Message boundary不是TCP contract，必須由application framing重建。"),
            ("Readiness通知後`read`為何仍要處理EAGAIN？", "通知到實際read之間，其他thread/handler可能消耗資料；edge/level模式也各有語意，且readiness通常只保證至少某些progress可能。Nonblocking loop應讀到EAGAIN，並把parser state保留下次。"),
            ("Deadline比每步timeout好在哪？", "它保存端到端時間budget。每步計算remaining time，前一步耗時會自然壓縮後續，避免N層各等5秒變成總共N×5秒；也能在budget耗盡時停止retry與取消無價值work。"),
            ("Client收到timeout時為何不能判定server失敗？", "Timeout只表示期限內沒收到可確認response。Request可能沒離開client、在網路、正在queue、已執行、已commit但response遺失。對side effect需要idempotency key/status query，而非把transport error直接映成business failure。"),
            ("Length-prefix protocol至少要驗證哪些事情？", "Header是否完整、endianness、length是否在protocol上限、header+payload arithmetic是否overflow、buffer budget、EOF是否發生在message中、未知version/type如何處理。Parser要incremental並能在任意byte切點保持state。"),
            ("I/O multiplexing何時不夠？", "它有效管理大量idle/slow connections的等待，但callback若做CPU-heavy、blocking DNS/disk或長business logic，仍會卡住event loop。需worker pool/async dependencies、bounded queues與backpressure，並保持ownership/thread-safety清楚。"),
        ],
        ["csapp-labs", "linux-man", "posix", "csapp-asides"],
    ),
    S(
        "ch12",
        12,
        "並行程式設計：共享狀態、同步與進度",
        "多個logical flows交錯時，如何同時保證結果正確、能前進且可擴展？",
        (
            "threads/processes/events、shared mutable state與允許的schedule",
            "用isolation、message passing、locks、condition variables、semaphores或atomics建立happens-before",
            "能證明invariant、避免race/deadlock，並以bounded design控制負載",
        ),
        [
            ("Concurrency", "多個工作在時間上重疊、可能交錯；不要求真的同時執行。", "單核心event loop也同時管理很多connections。"),
            ("Parallelism", "多個工作在不同execution resources上同時執行。", "四核心同時處理四個array partitions。"),
            ("Data race", "依語言memory model，兩個conflicting accesses未由happens-before排序且至少一個write。", "兩threads未同步讀寫同一C variable，行為未定義。"),
            ("Invariant", "每個可觀察合法state都必須成立的規則。", "Bounded queue永遠滿足`0 <= count <= capacity`。"),
            ("Condition variable", "讓thread在保護同一predicate的mutex旁等待state可能改變。", "Consumer在queue空時wait，producer入隊後signal。"),
            ("Deadlock", "一組participants永久等待彼此持有或才能觸發的資源/事件。", "Thread A持L1等L2，B持L2等L1。"),
        ],
        r"""
choose concurrency model
  ├─ processes: isolation + IPC
  ├─ I/O multiplexing: one/few event-loop threads
  └─ threads: shared address space

shared state
  ↓ define invariant + owner
critical transition
  ↓ synchronization establishes mutual exclusion + visibility
mutex / semaphore / condition / atomic / message queue
  ↓
safety: nothing bad happens
liveness: useful work eventually progresses
performance: bounded queue + low contention + locality

always test schedules, cancellation, shutdown, overload
""",
        r"""
### 12.A 先選state-sharing模型，再選primitive

Process model提供address-space isolation，failure containment較好，但IPC/serialization成本高；event-driven model用nonblocking I/O與explicit state machines管理大量connections，避免每connection一thread的stack/scheduling成本，但任何blocking handler會卡整個loop；threads共享memory、溝通低成本，卻讓alias與lifetime跨flows。

沒有普遍最佳模型。先回答工作是CPU-bound或I/O-bound、shared state多少、failure是否需隔離、blocking libraries、debuggability與capacity，再選architecture。很多production server是hybrid：少量event loops + bounded worker pool + separate processes。

### 12.B Race condition與data race不同

Race condition是結果依賴timing的廣義邏輯問題；data race是語言memory model中的特定未同步conflicting access，在C/C++通常導致UB。即使使用atomics消除data race，check-then-act仍可能是邏輯race：

```text
if balance >= amount:
    balance -= amount
```

兩步需作為一個atomic state transition。先寫invariant與合法transition，再決定用mutex、single owner/message或compare-exchange loop。

### 12.C Mutex同時處理互斥與可見性

Lock保護critical section，使同一mutex的持有區間不重疊；unlock→後續lock建立synchronization，使writes可見。不是只要「大概同時不進去」；所有讀寫同一invariant state的paths都必須遵守同一locking policy。把pointer從lock內拿出、unlock後使用，還要確保object lifetime與內容不被其他thread改變。

Lock granularity是trade-off：coarse lock容易證明但contention高；fine-grained提高parallelism卻增加order、lifetime與composition複雜度。Sharding/ownership往往比加更多locks更可擴展。

### 12.D Condition variable等待predicate

Condition variable不保存「事件次數」。標準pattern是在mutex下以while檢查predicate，false時wait；wait原子地release mutex並睡眠，醒來重新acquire再檢查。While處理spurious wakeup，也處理其他thread先消耗state。

```c
pthread_mutex_lock(&q->mu);
while (q->count == 0 && !q->closed)
    pthread_cond_wait(&q->not_empty, &q->mu);
if (q->count > 0) item = pop_locked(q);
pthread_mutex_unlock(&q->mu);
```

Signal應在改變predicate的state transition附近；broadcast用於多種waiters都可能前進或shutdown。避免把condition當notification queue。

### 12.E Semaphore與bounded buffer

Counting semaphore可表示可用資源數。Producer-consumer常用`slots`初值N、`items`初值0，再用mutex保護ring indices/data；producer wait slot→lock寫→unlock→post item，consumer相反。Semaphore count與buffer state必須一致，error/cancellation path也要恢復permit，否則capacity永久流失。

Bounded queue不是限制功能，而是穩定性機制：當arrival > service，無限queue只延後失敗並放大latency/memory。滿時要block producer、return overload、drop低優先work或backpressure上游，策略需顯式。

### 12.F Thread lifecycle與共享變數

`pthread_create`建立thread，join回收joinable thread資源；detached thread自動回收但無法join取得結果。Main return/`exit`會終止整個process，thread function return只結束該thread。傳入stack local pointer前要確保lifetime跨thread；loop建立threads時不可讓所有threads引用同一個會改變的index variable。

哪些C variables「shared」要從memory location分析：global/heap object可共享；每thread stack frame本身private，但若其address傳出，所指object可被他人存取。Register/local這些source名稱不是shared判斷邊界。

### 12.G Deadlock、livelock與starvation

Deadlock常由mutual exclusion、hold-and-wait、no preemption、circular wait共同形成；打破任一條可避免。最常用是global lock order，所有paths依相同順序取得；也可try-lock/backoff、一次取得all resources或single owner。Livelock是participants一直動卻互相退讓無進展；starvation是某participant長期得不到資源，公平性與priority policy很重要。

Lock-order圖比口頭規則更可靠：每個「持A再取B」建立A→B edge，若graph有cycle就有潛在deadlock。Dynamic tests只能找到走到的schedule，不能證明無cycle。

### 12.H Atomics與memory ordering

Atomic operation保證單一object操作不撕裂，並依memory order建立不同強度的ordering；它不自動保護跨多objects的invariant。Sequential consistency易推理但可能較昂貴；acquire/release可在publication pattern建立可見性；relaxed只保證該atomic modification order，不建立一般data visibility。除簡單counter/flag外，先用mutex實作correct版本，再有證據地降級。

ABA、memory reclamation與lock-free progress非常進階：CAS看到相同bit pattern不代表object沒被移除再重用。Hazard pointers/epochs等需完整protocol。不要把「沒有mutex」等同簡單或一定快。

### 12.I Thread safety、reentrancy與API設計

Thread-safe function可被多threads並行呼叫而遵守contract；reentrant function在執行中被再次進入（如signal/recursive）仍安全，要求更嚴格。使用global scratch buffer、返回static storage、隱藏共享cache都可能破壞。把state放caller-owned context、明確ownership與immutable data，通常比內部加global lock更可組合。

### 12.J 測試並行程式

Sleep不是同步。使用barrier/latch控制interleaving，反覆stress、增加CPU數、隨機yield，搭配TSan；更重要的是assert invariant、bounded queue與shutdown。測試normal、empty/full、cancellation、producer/consumer先終止、signal/spurious wakeup與overload。Observability要能看queue depth、wait time、lock contention與active workers。
""",
        r"""
實作bounded ring queue：一版mutex+two condition variables，一版semaphore+mutex。建立多producer/consumer，為每個item帶unique id，最後驗證無遺失、無重複、queue invariant與clean shutdown。使用barrier讓兩threads同時執行check-then-act，先重現race，再修成single critical transition。

```bash
cc -O2 -g -pthread queue.c -o queue
clang -O1 -g -fsanitize=thread -pthread queue.c -o queue-tsan
./queue-tsan
perf stat -e context-switches,cpu-migrations ./queue
```

接著把queue改為unbounded，讓producer速率高於consumer，量queue length與p99 wait；再恢復bound並定義reject/backpressure policy。
""",
        [
            "以`sleep`安排thread順序，將機率當同步contract。",
            "只鎖writes不鎖reads，或不同paths用不同locks保護同一invariant。",
            "Condition wait使用`if`，把wake理解為predicate一定為true。",
            "無限queue掩蓋overload，直到OOM與timeout avalanche。",
            "使用atomics後就宣稱沒有race，忽略multi-object invariant與lifetime。",
        ],
        [
            ("Concurrency與parallelism差在哪？", "Concurrency描述多個tasks生命週期重疊、事件可交錯；單核心event loop也有concurrency。Parallelism要求同一時間在多execution resources上工作。Architecture可有concurrency但無parallelism，也可用data parallelism同時運算。"),
            ("Mutex除了互斥還提供什麼？", "依語言/thread library memory model，unlock與之後成功lock同一mutex建立happens-before，使critical section內writes對下一持有者可見。沒有這個ordering，即使CPU看似不『同時』操作，compiler/cache仍可讓未同步讀寫無合法語意。"),
            ("為何condition variable一定用while檢查predicate？", "Wake可能是spurious，或broadcast後另一thread先取得lock並消耗resource；signal也只表示state可能改變，不保證當前waiter的條件成立。While在持mutex狀態重新驗證，才把正確性建立在state而非通知次數。"),
            ("如何判斷一個C variable是否shared？", "看其所代表memory object是否可被多threads引用，而非看名稱宣告位置。Global/heap常shared；stack object若address傳出也shared；每thread各自的local instance通常private。Aliasing與lifetime決定實際sharing。"),
            ("Lock order如何防deadlock？", "為所有locks定義strict total/partial order，任何thread同時取多locks都只沿同方向。Wait-for graph因此不可能形成cycle。Error/try-lock paths也需遵守；若無法自然排序，考慮合併owner、一次取得或message passing。"),
            ("Atomics為何不能自動保護`if (balance >= x) balance -= x`？", "即使load與store各自atomic，兩者之間仍可被另一thread插入，讓兩個participants都通過check。需mutex把check+update變一個transition，或使用CAS loop在expected state未變時提交，並處理retry與multi-field invariant。"),
            ("Thread pool為何必須bounded？", "當arrival rate超過service rate，unbounded queue依排隊理論必然持續成長，memory與waiting latency增加；clients timeout後work仍執行，形成waste。Bound把overload轉成可觀察、可控制的block/reject/backpressure。"),
        ],
        ["csapp-labs", "posix", "linux-man", "clang-tsan", "csapp-asides"],
    ),
]
