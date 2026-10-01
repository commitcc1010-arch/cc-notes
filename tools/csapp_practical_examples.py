"""Executable Python concept models and real-world transfer notes for every chapter."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PracticalExample:
    section_id: str
    number: int
    title: str
    situation: str
    why: str
    code: str
    walkthrough: tuple[str, ...]
    applications: tuple[str, ...]
    transfers: tuple[tuple[str, str], ...]


def E(
    section_id: str,
    number: int,
    title: str,
    situation: str,
    why: str,
    code: str,
    walkthrough: list[str],
    applications: list[str],
    transfers: list[tuple[str, str]],
) -> PracticalExample:
    item = PracticalExample(
        section_id=section_id,
        number=number,
        title=title,
        situation=situation,
        why=why,
        code=code.strip(),
        walkthrough=tuple(walkthrough),
        applications=tuple(applications),
        transfers=tuple(transfers),
    )
    assert len(item.situation) >= 80
    assert len(item.why) >= 100
    assert len(item.code) >= 250
    assert len(item.walkthrough) >= 4
    assert len(item.applications) >= 3
    assert len(item.transfers) >= 3
    compile(item.code, f"chapter-{number:02d}-example.py", "exec")
    return item


EXAMPLES = [
    E(
        "prereq",
        0,
        "資源已經釋放，舊 reference 為何仍然危險？",
        "想像一個 request handler 取得 database connection，完成後放回 pool；另一段程式卻仍保存舊 reference 並繼續使用。在 Python 裡可以主動檢查狀態，在 C 裡同型錯誤可能成為 use-after-free。",
        "Chapter 0 的 object、ownership、alias 與 lifetime 正是為了回答：資源目前由誰負責、何時失效、還有哪些 reference 能碰到它。沒有這個模型，buffer、fd、lock、heap block 都會出現『看起來還有地址，所以應該能用』的錯覺。",
        r'''
class OwnedConnection:
    def __init__(self, name: str):
        self.name = name
        self._open = True

    def execute(self, sql: str) -> str:
        if not self._open:
            raise RuntimeError("use after close")
        return f"{self.name}: {sql}"

    def close(self) -> None:
        if not self._open:
            raise RuntimeError("double close")
        self._open = False


conn = OwnedConnection("db-1")
alias = conn
print(conn.execute("SELECT 1"))
conn.close()

try:
    alias.execute("SELECT 2")
except RuntimeError as error:
    print("caught:", error)
''',
        [
            "`conn` 與 `alias` 是兩個名稱，卻指向同一個 resource object；清除其中一個名稱不會自動清除另一個 alias。",
            "`close()` 改變的是 resource lifecycle，不是 Python reference 是否存在；這對應 C 中 allocation 被 `free` 後 pointer bits 仍可能保留。",
            "模型用明確 exception 將 use-after-close 變成可見錯誤；C 的 use-after-free 通常沒有這種保護，可能靜默破壞其他資料。",
            "真正的介面設計應讓 owner 唯一、借用範圍短，並使 close/free 的責任可由 code review 與工具檢查。",
        ],
        [
            "C library API：誰配置 buffer、誰釋放，以及 callback 返回後 pointer 是否仍有效。",
            "Database／HTTP connection pool：borrow、return 與 stale handle 的生命週期。",
            "Lock、temporary file、GPU buffer 等必須成對 acquire/release 的資源。",
        ],
        [
            ("RAII／context manager", "把resource lifetime綁在lexical scope，離開scope自動release，減少遺漏error path。"),
            ("Database transaction", "Transaction commit/rollback後，原本的mutable session state也進入不同生命週期。"),
            ("Lease／capability", "Cloud lock、Kubernetes lease或signed URL都有有效期限；持有handle不代表權限仍有效。"),
        ],
    ),
    E(
        "ch1",
        1,
        "同一份 source 為何在 production 可能變成不同程式？",
        "團隊確認 Git commit 相同，開發環境正常，production 卻 crash。最後發現 compiler flag、library version或build image不同。只看 source 無法證明實際執行的 artifact 相同。",
        "Chapter 1 把 preprocess、compile、assemble、link、load 與 process 串起來，讓你知道每個階段都會加入新的輸入。實務上 build provenance、container digest、debug symbols與runtime mappings，都是這條生命週期的可觀察版本。",
        r'''
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class Artifact:
    stage: str
    payload: bytes
    parents: tuple[str, ...]

    @property
    def digest(self) -> str:
        return sha256(self.payload).hexdigest()[:12]


def transform(stage: str, artifact: Artifact, config: str) -> Artifact:
    payload = artifact.payload + b"\n" + config.encode()
    return Artifact(stage, payload, (artifact.digest,))


source = Artifact("source", b"int main(){return 0;}", ())
obj_debug = transform("object", source, "compiler=gcc;opt=O0")
obj_release = transform("object", source, "compiler=gcc;opt=O2")
exe_debug = transform("executable", obj_debug, "libc=2.x")
exe_release = transform("executable", obj_release, "libc=2.x")

for artifact in (source, obj_debug, obj_release, exe_debug, exe_release):
    print(artifact.stage, artifact.digest, artifact.parents)
''',
        [
            "Source digest相同，但不同compiler configuration產生不同object digest；『同commit』不是『同binary』。",
            "Link階段再加入library與linker options，因此object相同仍可能產生不同executable。",
            "Artifact保存parent digest，形成簡化provenance graph；真實系統還需記錄toolchain、environment與dependency lock。",
            "Production除比對executable digest，還要觀察loader實際載入的shared libraries與process mappings。",
        ],
        [
            "Reproducible builds、SBOM、artifact signing與部署追蹤。",
            "Core dump symbolization：需要與crash完全對應的binary和debug symbols。",
            "Container／serverless部署：image、entrypoint、dynamic libraries共同形成執行內容。",
        ],
        [
            ("Data pipeline lineage", "Dataset結果也應追到source data、transformation code與configuration。"),
            ("ML model provenance", "Model不只由code決定，還包含training data、weights、hyperparameters與runtime。"),
            ("CI/CD stage graph", "每個stage把輸入轉為artifact，失敗類型與可重跑邊界都應明確。"),
        ],
    ),
    E(
        "ch2",
        2,
        "網路封包的長度欄位為何會變成安全漏洞？",
        "Server從外部收到四個bytes作為payload長度。如果直接用host byte order、混合signed/unsigned，或先做 `header + length` 再檢查，攻擊者可能讓allocation過小、過大或繞過上限。",
        "Chapter 2 的endianness、固定寬度integer、conversion與overflow不是考試算術，而是所有binary protocol、file format與storage engine的信任邊界。Python model會安全decode並在allocation前驗證。",
        r'''
import struct

HEADER = struct.Struct("!BI")  # network order: version, payload length
MAX_PAYLOAD = 1024


def parse_packet(packet: bytes) -> bytes:
    if len(packet) < HEADER.size:
        raise ValueError("truncated header")
    version, length = HEADER.unpack_from(packet)
    if version != 1:
        raise ValueError("unsupported version")
    if length > MAX_PAYLOAD:
        raise ValueError("payload too large")
    expected = HEADER.size + length
    if len(packet) != expected:
        raise ValueError("length mismatch")
    return packet[HEADER.size:]


good = HEADER.pack(1, 5) + b"hello"
print(parse_packet(good))

for bad in (b"\x01", HEADER.pack(1, 5000), HEADER.pack(1, 4) + b"x"):
    try:
        parse_packet(bad)
    except ValueError as error:
        print("rejected:", error)
''',
        [
            "`!BI`明確指定network byte order與field width，避免依賴host layout。",
            "先確認header完整，才允許decode；先限制length，才計算與使用後續buffer。",
            "Model要求packet長度恰好等於宣告值；真實stream parser則會累積bytes，直到完整frame。",
            "C版本還必須在`size_t`上做checked addition/multiplication，因固定寬度field轉型後仍可能超平台容量。",
        ],
        [
            "TLS、DNS、HTTP/2、database wire protocol等binary parser。",
            "Image、archive、executable與模型權重等file format loader。",
            "Storage engine讀取page header、record length與checksum。",
        ],
        [
            ("Schema validation", "JSON/Protobuf雖較高階，仍需限制長度、版本、未知欄位與numeric range。"),
            ("Financial arithmetic", "Money通常用fixed-point integer，避免binary floating rounding與明確處理overflow。"),
            ("GPU tensor metadata", "Shape×stride×element size也需要checked multiplication，否則allocation與index會失配。"),
        ],
    ),
    E(
        "ch3",
        3,
        "為何兩個語言都叫 `Record`，跨 FFI 卻讀出錯資料？",
        "Python透過FFI呼叫C library時，雙方都宣稱struct含tag、count、flag，卻可能因alignment與padding得到不同offset。名稱與欄位順序看似一致，binary contract仍可能不一致。",
        "Chapter 3 的ABI、addressing mode與struct layout直接決定FFI、system call wrapper、debugger與binary parser如何解讀memory。以下用Python `ctypes`顯示compiler-style layout，讓padding變成可觀察資料。",
        r'''
import ctypes


class Record(ctypes.Structure):
    _fields_ = [
        ("tag", ctypes.c_uint8),
        ("count", ctypes.c_uint32),
        ("flag", ctypes.c_uint8),
    ]


class PackedRecord(ctypes.Structure):
    _pack_ = 1
    _fields_ = Record._fields_


def describe(cls) -> None:
    print(cls.__name__, "size=", ctypes.sizeof(cls),
          "alignment=", ctypes.alignment(cls))
    for name, _ in cls._fields_:
        print(" ", name, "offset=", getattr(cls, name).offset)


describe(Record)
describe(PackedRecord)
''',
        [
            "普通layout在`tag`後插入padding，讓32-bit `count`滿足alignment；尾端也可能補齊struct array stride。",
            "Packed layout移除padding，size較小，但misaligned access可能較慢或在某些architecture不合法。",
            "FFI兩側必須同意type width、alignment、calling convention與ownership，不能只對欄位名稱。",
            "真實network/disk format不應直接依賴native struct layout；應明確serialize，否則ABI或endianness改變就不相容。",
        ],
        [
            "Python/Rust/Java Native Interface呼叫C/C++ library。",
            "Core dump、debugger、eBPF或memory forensic工具解析native objects。",
            "OS kernel/userspace header、device driver與hardware register layout。",
        ],
        [
            ("Database row layout", "Column offsets、alignment與null bitmap同樣決定bytes如何被解讀。"),
            ("RPC ABI", "跨process contract將native ABI提升成schema、version與serialization規則。"),
            ("Plugin interface", "Dynamic plugin若直接共享struct，layout就成為長期binary compatibility責任。"),
        ],
    ),
    E(
        "ch4",
        4,
        "為何instruction數相同，dependency不同就有不同速度？",
        "兩段程式都做四次加法。一段每次依賴前一次結果，另一段使用兩個獨立accumulator。CPU有多個execution units時，第二段可重疊更多工作；只數instruction無法看出critical path。",
        "Chapter 4 的pipeline與hazard讓你用『result何時可用、consumer何時需要』理解stall。Python模型不模擬完整CPU，而是用dependency DAG計算最早完成時間，建立critical-path直覺。",
        r'''
from dataclasses import dataclass


@dataclass(frozen=True)
class Op:
    name: str
    dst: str
    srcs: tuple[str, ...]
    latency: int


def schedule(ops: list[Op]) -> int:
    ready: dict[str, int] = {}
    for op in ops:
        start = max((ready.get(src, 0) for src in op.srcs), default=0)
        done = start + op.latency
        ready[op.dst] = done
        print(f"{op.name:8} start={start} done={done}")
    return max(ready.values(), default=0)


chain = [Op(f"add{i}", "sum", ("sum",), 3) for i in range(4)]
parallel = [
    Op("add0", "s0", ("s0",), 3), Op("add1", "s1", ("s1",), 3),
    Op("add2", "s0", ("s0",), 3), Op("add3", "s1", ("s1",), 3),
    Op("merge", "sum", ("s0", "s1"), 3),
]

print("chain cycles:", schedule(chain))
print("parallel critical path:", schedule(parallel))
''',
        [
            "`ready`保存每個value最早可被consumer使用的時間，對應pipeline forwarding/availability觀念。",
            "單一`sum`讓四個adds形成一條dependency chain，即使有多個ALU也不能同時完成。",
            "兩個accumulators產生兩條獨立chain，可由superscalar/out-of-order硬體重疊；最後merge才匯合。",
            "真實CPU還有issue width、ports、cache、branch與retirement限制；此模型只隔離critical path。",
        ],
        [
            "解釋loop unrolling與multiple accumulators為何可能降低CPE。",
            "分析load-use hazard、branch misprediction與pipeline bubbles。",
            "閱讀CPU performance counter與compiler-generated assembly。",
        ],
        [
            ("CI pipeline", "兩個沒有dependency的tests可並行；所有stage串成單鏈時，總時間由critical path決定。"),
            ("Dataflow engine", "Spark/DAG scheduler也依dependencies決定task何時ready。"),
            ("Async request fan-out", "多個下游RPC可並行，但response merge與最慢dependency決定latency。"),
        ],
    ),
    E(
        "ch5",
        5,
        "最佳化最顯眼的函式，為何整體幾乎沒變快？",
        "Profiler顯示parser占20%，engine占80%。工程師把parser加速10倍，卻預期整體也快10倍。實際上未改善部分形成上限，而且量測noise可能比收益還大。",
        "Chapter 5 教你先定義metric與workload，再用Amdahl、profile和benchmark驗證。Python例子同時計算理論上限與多次量測的median，避免把單次最快結果當證據。",
        r'''
from statistics import median
from time import perf_counter


def amdahl(fraction: float, local_speedup: float) -> float:
    return 1.0 / ((1.0 - fraction) + fraction / local_speedup)


def workload(n: int) -> int:
    total = 0
    for value in range(n):
        total += (value * 17) % 101
    return total


def benchmark(fn, repeats: int = 9) -> float:
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        result = fn()
        samples.append(perf_counter() - start)
        assert result >= 0
    return median(samples)


print("20% part becomes 10x:", round(amdahl(0.20, 10), 3), "x")
print("80% part becomes 2x:", round(amdahl(0.80, 2), 3), "x")
print("median seconds:", benchmark(lambda: workload(200_000)))
''',
        [
            "Amdahl先把局部改善換算成端到端上限；改善20%區域10倍，整體仍只有約1.22倍。",
            "Benchmark多次執行取median，降低scheduler與background noise對單次樣本的影響。",
            "`assert`消費結果，避免某些runtime/compiler把無observable effect的工作消除；native benchmark還需更嚴格控制。",
            "真正優化要用profile定位hot path，再用counters/assembly解釋原因，最後回到端到端metric。",
        ],
        [
            "API latency、batch pipeline、database query與video processing最佳化。",
            "容量規劃：判斷CPU、memory bandwidth、I/O或dependency誰限制throughput。",
            "ML inference：tokenization、model compute、KV cache與network各占多少。",
        ],
        [
            ("Latency budget", "一個request的總時間也由各stage占比組成，局部改善受未改善stage限制。"),
            ("Cost optimization", "只降低小額資源不會大幅改總成本；先找spend占比與elasticity。"),
            ("Team process", "加速coding若review/deploy仍是瓶頸，lead time改善同樣受Amdahl限制。"),
        ],
    ),
    E(
        "ch6",
        6,
        "為何只是改變資料走訪順序，就能快很多？",
        "同一批array elements，連續讀取通常比大stride跳著讀更能利用cache line。演算法operation數沒有改變，搬移的cache blocks與miss數卻不同。",
        "Chapter 6 的locality、set mapping與working set用來解釋database scan、matrix、image與ML tensor layout。以下Python cache simulator刻意簡化硬體，只比較不同address stream造成的hits與misses。",
        r'''
class SetAssociativeCache:
    def __init__(self, sets: int, ways: int, line_size: int):
        self.sets = [[] for _ in range(sets)]
        self.line_size = line_size
        self.ways = ways
        self.hits = self.misses = 0

    def access(self, address: int) -> None:
        block = address // self.line_size
        bucket = self.sets[block % len(self.sets)]
        if block in bucket:
            self.hits += 1
            bucket.remove(block)
            bucket.append(block)
        else:
            self.misses += 1
            if len(bucket) == self.ways:
                bucket.pop(0)
            bucket.append(block)


def run(stride: int) -> tuple[int, int]:
    cache = SetAssociativeCache(sets=8, ways=2, line_size=16)
    for _ in range(4):
        for address in range(0, 256, stride):
            cache.access(address)
    return cache.hits, cache.misses


for stride in (4, 16, 64):
    print("stride", stride, "hits/misses", run(stride))
''',
        [
            "Address先除以line size得到memory block，再由block modulo set count選set。",
            "同set內list由least到most recently used，hit會更新recency，滿時evict最舊block。",
            "小stride在同一line使用多個addresses，產生spatial locality；大stride較容易每次帶回只用一次的line。",
            "真實CPU有多層cache、prefetch、physical indexing與concurrency；模型用來隔離address stream與mapping。",
        ],
        [
            "Matrix multiplication blocking、image processing與columnar analytics。",
            "Database buffer pool、B-tree page與hash-table layout。",
            "ML tensor contiguous layout、batching與CPU/GPU資料搬移。",
        ],
        [
            ("CDN／browser cache", "較慢來源前放較小快速層，仍利用temporal locality；只是block與replacement語意不同。"),
            ("Database buffer pool", "Page是搬移單位，working set與replacement同樣決定hit ratio。"),
            ("Memoization", "把昂貴計算結果留在近端，利用重複key的temporal locality。"),
        ],
    ),
    E(
        "ch7",
        7,
        "為何程式編譯成功，最後卻說找不到 symbol？",
        "某個translation unit看過function declaration，所以compiler接受呼叫；linker收集objects時卻找不到definition。另一類問題則是shared library存在，但production loader載入了不相容版本。",
        "Chapter 7把名稱、symbol、relocation與runtime loading分層。Python模型示範一個極小linker：先配置objects、建立global symbol table，再用PC-relative公式修補call site。",
        r'''
objects = [
    {
        "name": "main.o",
        "size": 32,
        "definitions": {"main": 0},
        "relocations": [{"offset": 8, "symbol": "helper"}],
    },
    {
        "name": "helper.o",
        "size": 16,
        "definitions": {"helper": 0},
        "relocations": [],
    },
]

base = 0x400000
symbols = {}

for obj in objects:
    obj["base"] = base
    for name, offset in obj["definitions"].items():
        if name in symbols:
            raise ValueError(f"multiple definition: {name}")
        symbols[name] = base + offset
    base += obj["size"]

for obj in objects:
    for relocation in obj["relocations"]:
        place = obj["base"] + relocation["offset"]
        target = symbols[relocation["symbol"]]
        displacement = target - (place + 4)
        print(obj["name"], relocation["symbol"], hex(displacement))
''',
        [
            "第一輪替每個object配置base並收集definitions；同名global可在此偵測multiple definition。",
            "Relocation保存call site offset與target symbol，因assembler當時不知道最終地址。",
            "PC-relative displacement以target減去下一條instruction位置；真實relocation還包含type、addend與range。",
            "Dynamic linking把部分resolution延到loader/runtime，增加search path、version、GOT/PLT與security問題。",
        ],
        [
            "診斷undefined reference、multiple definition與library order。",
            "Shared library、plugin、Python extension與native package部署。",
            "Crash symbolization與由address反查function/source line。",
        ],
        [
            ("Dependency injection", "Runtime把抽象名稱解析到具體implementation，概念上類似symbol resolution。"),
            ("DNS／service discovery", "Human-readable service name在使用前解析成目前endpoint。"),
            ("Plugin registry", "Module載入後把exported names登記，caller依contract查找並呼叫。"),
        ],
    ),
    E(
        "ch8",
        8,
        "Worker不回應時，如何停止又不留下zombie？",
        "Supervisor啟動child worker。Shutdown時若只送kill signal卻不wait，child結束後仍可能留下zombie；若只無限wait，卡住的worker會讓deploy永遠停不下來。",
        "Chapter 8 的process、signal與wait提供一個完整termination protocol：先請求graceful stop，在deadline內回收；超時才升級，最後仍必須wait取得termination status。",
        r'''
import subprocess
import sys


def stop_process(process: subprocess.Popen, grace: float = 0.2) -> int:
    process.terminate()  # SIGTERM on POSIX
    try:
        return process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait()


child = subprocess.Popen([
    sys.executable,
    "-c",
    "import time; time.sleep(10)",
])

status = stop_process(child)
print("child pid:", child.pid)
print("reaped status:", status)
print("poll after wait:", child.poll())
''',
        [
            "`Popen`建立child process；parent保存PID與process handle，成為lifecycle owner。",
            "`terminate`是graceful request，不保證child立刻退出；deadline避免shutdown無限阻塞。",
            "超時後`kill`升級，但仍呼叫`wait`回收status；signal與reaping是兩個不同步驟。",
            "Production supervisor還要處理process group、descendants、stdout/stderr pipes與restart policy。",
        ],
        [
            "Web worker、job runner、test harness與build executor。",
            "Container entrypoint、Kubernetes termination與service supervisor。",
            "Shell pipeline、IDE terminal與background job管理。",
        ],
        [
            ("Async task cancellation", "先送cancel request、給cleanup時間、超時再強制中止，也是一個termination protocol。"),
            ("Distributed lease expiry", "Owner失聯後不能永遠等待，需要deadline與新的reaper接手。"),
            ("Incident failover", "Graceful drain、deadline、force removal與state reconciliation同樣分階段。"),
        ],
    ),
    E(
        "ch9",
        9,
        "同一個virtual address如何映到不同physical page？",
        "兩個process都可能使用virtual address `0x4000`，卻各自看到不同資料。CPU先依目前process的page table做translation；近期mapping還會被TLB cache。",
        "Chapter 9需要同時理解VM與allocator：OS先管理page mapping與permission，malloc再在mapping內切小block。Python模型聚焦translation、TLB hit與page fault，避免把它們混成同一事件。",
        r'''
PAGE_SIZE = 4096


class AddressSpace:
    def __init__(self, page_table: dict[int, int]):
        self.page_table = page_table
        self.tlb: dict[int, int] = {}

    def translate(self, virtual_address: int) -> int:
        vpn, offset = divmod(virtual_address, PAGE_SIZE)
        if vpn in self.tlb:
            frame = self.tlb[vpn]
            print("TLB hit", vpn)
        else:
            print("TLB miss", vpn)
            if vpn not in self.page_table:
                raise MemoryError(f"page fault for VPN {vpn}")
            frame = self.page_table[vpn]
            self.tlb[vpn] = frame
        return frame * PAGE_SIZE + offset


left = AddressSpace({4: 100})
right = AddressSpace({4: 900})

print(hex(left.translate(0x4123)))
print(hex(left.translate(0x4123)))
print(hex(right.translate(0x4123)))
''',
        [
            "`divmod`把virtual address拆成virtual page number與page offset。",
            "TLB只cache近期translation；miss後查page table，mapping存在就填TLB，不必然是page fault。",
            "兩個address spaces可把相同VPN映到不同frames，因此process看到private-looking memory。",
            "Page offset在translation前後不變；allocator則在已映射pages內管理更細的block metadata。",
        ],
        [
            "Demand paging、copy-on-write fork、shared memory與memory-mapped files。",
            "Allocator、garbage collector、memory profiler與OOM診斷。",
            "Container/process isolation、JIT、database mmap與large-page tuning。",
        ],
        [
            ("Database virtual pages", "Buffer manager也把logical page id映到memory frame，並cache近期pages。"),
            ("Object storage indirection", "Logical key與physical location分離，允許migration、replication與cache。"),
            ("Copy-on-write snapshot", "VM fork、filesystem snapshot與persistent data structure都先共享，修改時才複製。"),
        ],
    ),
    E(
        "ch10",
        10,
        "一次 `read(4096)` 為何可能只拿到三個bytes？",
        "程式從pipe、socket或特殊device讀資料，卻假設一次read會填滿buffer。實際stream只保證回傳目前可取得的部分；若沒有loop，parser會把正常short read誤判成壞資料。",
        "Chapter 10 的robust I/O、EOF與descriptor lifecycle是file copy、shell、network與logging的共同底層。Python用刻意只回小chunk的stream，驗證caller不能依賴一次完整read。",
        r'''
class ChunkedStream:
    def __init__(self, data: bytes, max_chunk: int):
        self.data = data
        self.max_chunk = max_chunk
        self.offset = 0

    def read(self, requested: int) -> bytes:
        count = min(requested, self.max_chunk,
                    len(self.data) - self.offset)
        chunk = self.data[self.offset:self.offset + count]
        self.offset += count
        return chunk


def read_exact(stream: ChunkedStream, size: int) -> bytes:
    parts = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError("stream ended mid-record")
        parts.append(chunk)
        remaining -= len(chunk)
    return b"".join(parts)


stream = ChunkedStream(b"abcdefgh", max_chunk=3)
print(read_exact(stream, 8))
''',
        [
            "`ChunkedStream`即使caller要求8 bytes，每次最多只回3，模擬kernel/network的合法short count。",
            "`read_exact`保存remaining state並持續讀，只有空bytes才視為EOF。",
            "若EOF發生在固定長度record中間，這是truncation；若一開始就EOF，可能代表正常stream結束。",
            "真實nonblocking fd還要處理EAGAIN，signal可能造成EINTR，write同樣可能partial。",
        ],
        [
            "File copy、archive reader、database log與binary record reader。",
            "Shell pipe/redirection、subprocess stdout/stderr與logging agent。",
            "Socket/TLS stream、serial port與device I/O。",
        ],
        [
            ("Pagination API", "一次response只回部分集合，caller保存cursor並loop直到完成。"),
            ("Batch processing", "Work被切成chunks逐步提交，必須追partial progress與retry boundary。"),
            ("Object upload", "Multipart upload也需記錄已完成parts，不能用單一boolean表示全部成功。"),
        ],
    ),
    E(
        "ch11",
        11,
        "TCP收到的任意片段如何還原成完整message？",
        "Client先送4-byte length，再送payload；server可能先收到2 bytes，下一次收到header剩餘部分加半個payload。若parser把每次recv當一則message，就會在真實網路偶發失敗。",
        "Chapter 11 將ordered byte stream提升成application protocol。以下incremental parser可接受任意fragmentation，只有buffer中存在完整frame才輸出message，並在allocation前限制長度。",
        r'''
import struct


class FrameDecoder:
    HEADER = struct.Struct("!I")

    def __init__(self, max_frame: int = 1024):
        self.buffer = bytearray()
        self.max_frame = max_frame

    def feed(self, chunk: bytes) -> list[bytes]:
        self.buffer.extend(chunk)
        frames = []
        while len(self.buffer) >= self.HEADER.size:
            (length,) = self.HEADER.unpack_from(self.buffer)
            if length > self.max_frame:
                raise ValueError("frame too large")
            end = self.HEADER.size + length
            if len(self.buffer) < end:
                break
            frames.append(bytes(self.buffer[self.HEADER.size:end]))
            del self.buffer[:end]
        return frames


wire = struct.pack("!I", 5) + b"hello" + struct.pack("!I", 3) + b"bye"
decoder = FrameDecoder()
for chunk in (wire[:2], wire[2:7], wire[7:10], wire[10:]):
    print("decoded:", decoder.feed(chunk))
''',
        [
            "Decoder把未完成bytes保存在buffer，parser state跨越多次read。",
            "只有header完整才decode length，只有整個frame完整才consume；partial frame不是error。",
            "一次chunk也可能含多個frames，所以loop持續解析，直到buffer不足。",
            "Production還需deadline、memory budget、version/type、EOF-mid-frame與idempotent operation語意。",
        ],
        [
            "RPC、database protocol、message broker與game server。",
            "WebSocket frame、HTTP body、TLS record之上的application message。",
            "Payment/order API的timeout、retry與idempotency設計。",
        ],
        [
            ("Streaming parser", "JSON/SAX、media decoder與compiler lexer都保存跨chunk state。"),
            ("Event sourcing", "Log record也需framing、version、checksum與truncated-tail recovery。"),
            ("Distributed transaction", "Transport成功不代表business commit；都需要明確completion point與deduplication。"),
        ],
    ),
    E(
        "ch12",
        12,
        "Worker處理不及時，queue為何不能無限長？",
        "Incoming jobs每秒100個，workers只能處理80個。若queue無上限，表面上沒有拒絕，實際memory與waiting time持續增加；client早已timeout，server仍處理過期工作。",
        "Chapter 12 的bounded queue、condition synchronization與backpressure同時是correctness與reliability。Python標準Queue內含mutex/conditions，`maxsize`把capacity壓力轉成可觀察的block。",
        r'''
from queue import Queue
from threading import Thread

STOP = object()
queue = Queue(maxsize=2)
results = []


def worker() -> None:
    while True:
        item = queue.get()
        try:
            if item is STOP:
                return
            results.append(item * item)
        finally:
            queue.task_done()


thread = Thread(target=worker)
thread.start()

for value in range(6):
    queue.put(value)  # blocks when capacity is exhausted
queue.put(STOP)
queue.join()
thread.join()

print(results)
''',
        [
            "`maxsize=2`使producer在queue滿時等待，讓backpressure沿呼叫路徑返回，而非無限吃memory。",
            "`put/get`內部使用同步保護queue invariant；caller不應直接讀寫其internal container。",
            "`task_done/join`追蹤所有accepted work完成，STOP sentinel則定義worker shutdown。",
            "Production不能總是block：也可timeout、reject、drop低優先工作或將pressure傳給上游，policy必須明確。",
        ],
        [
            "Web/thread pool、background job、database connection pool與logging pipeline。",
            "Producer-consumer、stream processing、ETL與message brokerconsumer。",
            "GUI/event loop、actor mailbox與async runtime scheduler。",
        ],
        [
            ("Rate limiter", "Bounded queue限制已接受work，rate limiter在入口限制admission，兩者共同防overload。"),
            ("TCP flow control", "Receiver window把consumer capacity回傳sender，也是backpressure。"),
            ("Reactive streams", "Subscriber明確request可處理數量，避免producer無限制push。"),
        ],
    ),
]


assert [item.number for item in EXAMPLES] == list(range(13))
assert [item.section_id for item in EXAMPLES] == [
    "prereq",
    *[f"ch{number}" for number in range(1, 13)],
]
