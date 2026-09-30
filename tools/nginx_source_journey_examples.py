"""Runnable Python analogies and source-reading bridges for all 48 chapters."""
from __future__ import annotations


def E(naive, python, mapping, microscope):
    return {
        "naive": naive.strip(),
        "python": python.strip(),
        "mapping": mapping,
        "microscope": microscope,
    }


EXAMPLES = {
    1: E(
        """
最直覺的寫法是讓一個函式從 accept 一路 blocking 到 backend response。問題是任何一次等待都會占住整條執行線。NGINX 將工作拆成短 callback，每次只推進一小步，狀態留在長命物件中。
""",
        r"""
from collections import deque

ready = deque()

class Request:
    def __init__(self):
        self.state = "READ_CLIENT"
        self.response = None

def on_client_read(r):
    r.state = "CONNECT_BACKEND"
    ready.append((on_backend_writable, r))

def on_backend_writable(r):
    r.state = "READ_BACKEND"
    ready.append((on_backend_readable, r))

def on_backend_readable(r):
    r.response = b"HTTP/1.1 200 OK\r\n\r\nhello"
    r.state = "DONE"

r = Request()
ready.append((on_client_read, r))
while ready:
    callback, request = ready.popleft()
    callback(request)
print(r.state, r.response)
""",
        [("`Request.state`", "`ngx_http_request_t`／`ngx_http_upstream_t` 中跨 event 保存的狀態"), ("`ready` queue", "epoll ready list 加上 posted events"), ("`callback(request)`", "`ev->handler(ev)` 再由 connection 找回 request"), ("三個 callbacks", "client read、upstream connect/write、upstream read 等 continuation")],
        ["先找 accepted client 如何從 `ngx_connection_t` 進入 HTTP handler。", "看到 return 時確認工作是完成，還是已安排下一個 event。", "畫出 client 與 backend 兩組 read/write events，不要合成一條。", "找 request finalize 前最後一個仍引用 request pool 的 callback。"],
    ),
    2: E(
        """
直接大量 `print()` 會改變 timing，且不同 request 的訊息混在一起。較好的方法是固定 correlation ID、只記錄狀態轉換，並用不同工具各自回答 source、runtime 與 syscall 問題。
""",
        r"""
import functools
import time
import uuid

def traced(fn):
    @functools.wraps(fn)
    def wrapper(ctx, *args):
        start = time.perf_counter()
        before = ctx["state"]
        try:
            return fn(ctx, *args)
        finally:
            print({
                "request_id": ctx["id"],
                "handler": fn.__name__,
                "from": before,
                "to": ctx["state"],
                "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
            })
    return wrapper

@traced
def parse(ctx):
    ctx["state"] = "PARSED"

ctx = {"id": str(uuid.uuid4()), "state": "READING"}
parse(ctx)
""",
        [("`request_id`", "debug log 中用 connection/request number 或自訂 header 串起事件"), ("decorator", "在少數 state-transition functions 加 instrumentation"), ("`elapsed_ms`", "upstream connect/header/response timing"), ("structured dict", "比散落文字更容易依 request、handler、state 過濾")],
        ["從 log 字串反查 source，確認訊息是在進入還是離開狀態時記錄。", "同時保存 build flags；條件編譯會改變可見路徑。", "用 GDB 看 struct、用 strace 看 syscall，不要要求單一工具回答所有層。", "觀測程式碼也可能阻塞或 allocation；測一次有無 instrumentation 的差異。"],
    ),
    3: E(
        """
從 `main()` 逐行展開所有 helper 會形成無限樹。問題驅動閱讀只保留與目標行為相交的節點，並特別追蹤 callback 的賦值點與跨等待存活的 object。
""",
        r"""
graph = {
    "accept": ["init_http_connection"],
    "init_http_connection": ["install_request_handler"],
    "request_handler": ["parse", "run_phases"],
    "run_phases": ["proxy_handler"],
    "proxy_handler": ["connect_upstream"],
}

goal = "connect_upstream"
frontier = [("accept", ["accept"])]
while frontier:
    node, path = frontier.pop(0)
    if node == goal:
        print(" -> ".join(path))
        break
    for nxt in graph.get(node, []):
        frontier.append((nxt, path + [nxt]))
""",
        [("graph edge", "直接 call、function pointer assignment 或 module registration"), ("path", "一條 user-visible vertical slice"), ("goal", "可觀察出口，例如 upstream connect 或 response write"), ("frontier", "尚未確認是否與問題相關的 symbols")],
        ["搜尋 `handler =` 找動態邊，再搜尋 handler definition。", "每碰到 struct 就記 owner、建立者、cleanup 與跨哪些 callback 存活。", "Helper 先只記 contract；阻塞主線時才往內展開。", "最後用 debug trace 刪掉實際沒有走過的靜態候選路徑。"],
    ),
    4: E(
        """
Python class 已把 method dispatch 與 ownership 隱藏起來；C 必須用 struct、function pointer 與明確 owner 表達。先用 Python 寫出同一模型，再看 NGINX 的 C 寫法就不會把 callback 當魔法。
""",
        r"""
from dataclasses import dataclass
from typing import Callable, Any

Handler = Callable[["Event"], None]

@dataclass
class Event:
    data: Any
    handler: Handler
    ready: bool = False

def read_request(event):
    connection = event.data
    print("read fd", connection["fd"])
    event.handler = wait_keepalive

def wait_keepalive(event):
    print("same event, new behavior")

event = Event(data={"fd": 7}, handler=read_request, ready=True)
event.handler(event)
event.handler(event)
""",
        [("`Event` dataclass", "`struct ngx_event_s`"), ("`handler: Handler`", "`ngx_event_handler_pt handler` function pointer"), ("`data: Any`", "`void *data`，動態型別由 contract 決定"), ("替換 `event.handler`", "HTTP 狀態轉換時安裝下一個 callback")],
        ["先讀 callback typedef，再看欄位與所有 assignment sites。", "遇到 `void *` 不要猜；由註冊該 callback 的 code 決定型別。", "Macro 取回外層 object 時，畫出 embedded node 與 owner 的 memory layout。", "確認資料配置於哪個 pool，因為 C 不會自動延長 lifetime。"],
    ),
    5: E(
        """
把所有初始化塞成一個無邊界函式，任何一步失敗時都不知道哪些資源已建立。Staged bootstrap 讓每一階段只依賴前一階段，並能在明確邊界停止。
""",
        r"""
def bootstrap(argv):
    state = {}
    stages = [
        ("options", lambda: {"config": argv[1]}),
        ("logging", lambda: {"log_ready": True}),
        ("cycle", lambda: {"cycle": "validated generation"}),
        ("sockets", lambda: {"listeners": [8080]}),
        ("mode", lambda: {"mode": "master"}),
    ]
    for name, build in stages:
        try:
            state.update(build())
            print("ready:", name)
        except Exception:
            print("failed after:", list(state))
            raise
    return state

bootstrap(["nginx", "nginx.conf"])
""",
        [("stages list", "`main()` 中 argument/log/OS/cycle/process mode 的初始化順序"), ("`cycle` stage", "`ngx_init_cycle()`"), ("listeners", "config 驗證後準備的 listening sockets"), ("mode", "`ngx_single_process_cycle` 或 `ngx_master_process_cycle`")],
        ["把 `main()` 先切成階段，不要立即進每個 helper。", "找每個 early return 前已建立哪些 global/resource。", "注意 `ngx_init_cycle()` 同時用於初次啟動與 reload。", "檢查 inherited sockets 與 daemonize 發生的相對順序。"],
    ),
    6: E(
        """
中央 parser 若為每個 directive 寫 `if/elif`，加入 module 就必須修改 core。Table-driven dispatch 讓 directive 自己帶名稱、合法 context 與 setter；merge 則區分『未設定』與合法零值。
""",
        r"""
UNSET = object()

def set_timeout(conf, args):
    conf["timeout_ms"] = int(args[0])

COMMANDS = {
    "proxy_read_timeout": {
        "contexts": {"http", "server", "location"},
        "setter": set_timeout,
    }
}

def apply(parent, child, context, tokens):
    command = COMMANDS[tokens[0]]
    if context not in command["contexts"]:
        raise ValueError("directive not allowed here")
    command["setter"](child, tokens[1:])
    child["timeout_ms"] = child.get(
        "timeout_ms", parent.get("timeout_ms", 60_000)
    )

child = {}
apply({"timeout_ms": 30_000}, child, "location",
      ["proxy_read_timeout", "3000"])
print(child)
""",
        [("`COMMANDS`", "各 module 的 `ngx_command_t[]`"), ("`contexts`", "directive type/context flags"), ("`setter`", "command set callback"), ("parent/child merge", "create/merge loc conf 與 `NGX_CONF_UNSET*` sentinel")],
        ["Parser 找到 command 後仍要定位正確 module conf slot。", "Setter 的 return contract 是 `NGX_CONF_OK`／error string，不是 request handler return code。", "Merge 要在 nested blocks 建立完成後執行。", "Runtime 快路徑通常使用已編譯／合併結果，不再解析文字 directive。"],
    ),
    7: E(
        """
原地修改 global config 會讓 request 看見半新半舊狀態。Generation object 先建立完整候選世界，全部成功後一次 publish；失敗就丟棄候選，不碰 active generation。
""",
        r"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Generation:
    version: int
    routes: dict
    listeners: tuple

active = Generation(1, {"/": "backend-a"}, (8080,))

def reload(old, new_routes):
    candidate = Generation(old.version + 1, new_routes, old.listeners)
    if not all(path.startswith("/") for path in candidate.routes):
        raise ValueError("invalid config")
    return candidate

try:
    active = reload(active, {"broken": "backend-b"})
except ValueError:
    pass
print(active.version, active.routes)
""",
        [("`Generation`", "`ngx_cycle_t`"), ("candidate", "`ngx_init_cycle(old_cycle)` 建出的新 cycle"), ("validation before assignment", "全部 config/resource 成功後才交給新 workers"), ("old remains", "reload 失敗時舊 cycle 繼續服務")],
        ["Reload 時新舊 cycle 會同時存在，global pointer 不代表只有一個 object。", "找哪些 sockets/shared zones 可以 reuse，哪些 metadata 必須新建。", "Cycle pool 是 generation lifetime root。", "任何 module init failure 都應讓 candidate rollback，而不是部分 publish。"],
    ),
    8: E(
        """
用 threads 共享所有 request state 會需要大量 locks。NGINX 預設用多個 process，每個 worker 擁有自己的 event loop 與 connections，只把必要狀態放 shared memory。
""",
        r"""
from multiprocessing import Process
import os

def worker(listener_name):
    print("worker", os.getpid(), "serves", listener_name)
    local_connections = {}
    local_connections[7] = {"state": "READING"}
    print("private state:", local_connections)

workers = [
    Process(target=worker, args=("shared-listener:8080",))
    for _ in range(2)
]
for process in workers:
    process.start()
for process in workers:
    process.join()
""",
        [("parent process", "NGINX master"), ("child `Process`", "worker process"), ("listener name", "fork 前準備並由 workers 繼承的 listening fd"), ("`local_connections`", "每個 worker 私有的 connection table/event loop state")],
        ["Fork 後普通 memory 更新不會自動跨 worker 可見。", "Master 處理 signal/child status，worker 處理 request。", "Listening accept 的協調策略與 process count/reuseport 有關。", "檢查 worker init hooks 在 fork 後建立哪些 process-local resources。"],
    ),
    9: E(
        """
直接殺掉舊 workers 再啟動新 workers 會中斷既有連線。Graceful reload 讓新 generation 先開始接新工作，舊 generation 只停止 admission，等手上的工作歸零再退出。
""",
        r"""
class Worker:
    def __init__(self, generation):
        self.generation = generation
        self.accepting = True
        self.active = 0

    def accept(self):
        if not self.accepting:
            return False
        self.active += 1
        return True

    def finish(self):
        self.active -= 1

old = Worker(generation=1)
old.accept()
new = Worker(generation=2)     # publish new workers first
old.accepting = False          # then drain old workers
old.finish()
print("old may exit:", old.active == 0, "new accepts:", new.accept())
""",
        [("two `Worker` objects", "reload 時並存的新舊 worker generations"), ("`accepting=False`", "graceful quit 後關閉 listening sockets"), ("`active`", "仍在處理的 connections/requests"), ("exit when zero", "舊 worker 完成 existing work 後離開")],
        ["HUP path 先建新 cycle；失敗時不可 signal old workers。", "舊 worker 停止 accept 不代表立即退出。", "長連線會延長 old generation lifetime。", "Module cleanup 不得假設 reload 後 old conf 已無 request 引用。"],
    ),
    10: E(
        """
一次 `recv()` 不保證拿到完整 message，一次 `send()` 也不保證送完。正確模型是 byte stream 加 cursor：能處理多少就處理多少，EAGAIN 時保存位置。
""",
        r"""
import socket

left, right = socket.socketpair()
left.setblocking(False)
right.sendall(b"GET /")
right.sendall(b"api HTTP/1.1\r\n")

buffer = bytearray()
while b"\r\n" not in buffer:
    try:
        chunk = left.recv(4)
        if not chunk:
            break
        buffer.extend(chunk)
        print("received piece:", chunk)
    except BlockingIOError:
        print("would block; wait for readable")
        break
print(buffer)
left.close()
right.close()
""",
        [("nonblocking socket", "NGINX accepted/upstream fd"), ("`BlockingIOError`", "`EAGAIN`／`NGX_AGAIN`"), ("`buffer`", "`ngx_buf_t` 的可用區間"), ("loop until delimiter/EAGAIN", "parser/output handler 的 bounded progress")],
        ["TCP 是 bytes，不保存 HTTP line boundary。", "Zero bytes、EAGAIN、ECONNRESET 與 timeout 必須分開處理。", "Fd close 後可被 reuse，舊 event 不能只靠數字判斷身分。", "每次 partial I/O 後確認哪個 cursor 已被移動。"],
    ),
    11: E(
        """
Accept 不只是取得 fd；它是建立 connection object、events、pool 與 protocol handoff 的 admission transaction。任何中途失敗都必須逆向釋放已取得資源。
""",
        r"""
class ConnectionPool:
    def __init__(self, capacity):
        self.free = [{"slot": i} for i in range(capacity)]

    def acquire(self, fd):
        if not self.free:
            raise RuntimeError("no connection slots")
        connection = self.free.pop()
        connection.update(fd=fd, read_handler=None, write_handler=None)
        return connection

    def release(self, connection):
        connection.clear()
        self.free.append(connection)

pool = ConnectionPool(2)
connection = pool.acquire(fd=12)
connection["read_handler"] = "init_http_connection"
print(connection)
pool.release(connection)
""",
        [("`ConnectionPool`", "預配置的 `ngx_connection_t` free list"), ("`acquire(fd)`", "`ngx_get_connection`"), ("handler assignment", "listening protocol handler 初始化 HTTP connection"), ("`release`", "close/error path 的 `ngx_free_connection`")],
        ["Accepted fd 與 connection slot 是兩個資源，error path 要同時歸還。", "Read/write events 內嵌於 connection slot，reuse 前需重設 flags/instance。", "Connection pool 不等於 request memory pool。", "最後一步的 `ls->handler(c)` 是 event layer 到 protocol layer 的注入點。"],
    ),
    12: E(
        """
每輪掃描所有 fd 在大量 idle connections 下浪費 CPU。Selector/epoll 保存 interest set，只回傳本輪 ready subset；但 handler 還是要真正讀寫並處理 partial I/O。
""",
        r"""
import selectors
import socket

selector = selectors.DefaultSelector()
reader, writer = socket.socketpair()
reader.setblocking(False)
selector.register(reader, selectors.EVENT_READ, data="client-7")

writer.sendall(b"hello")
for key, mask in selector.select(timeout=1):
    if mask & selectors.EVENT_READ:
        print(key.data, "ready:", key.fileobj.recv(1024))

selector.unregister(reader)
reader.close()
writer.close()
""",
        [("`DefaultSelector`", "Linux 上通常對應 epoll"), ("`register`", "`epoll_ctl` 維護 interest set"), ("`select` result", "`epoll_wait` 的 ready events"), ("`data`", "epoll event data 指回 connection/instance")],
        ["Ready 不表示完整 request 或完整 write。", "ET 模式下確認 handler 讀到 EAGAIN。", "無 pending output 時不要持續訂閱 writable。", "檢查 instance bit 如何丟棄 fd reuse 造成的 stale event。"],
    ),
    13: E(
        """
若 event loop 內寫一個巨大 switch 判斷 HTTP 每個階段，transport 與 protocol 會耦合。把下一步存在 handler 欄位，狀態轉換就是替換 callback。
""",
        r"""
class Event:
    def __init__(self, owner, handler):
        self.owner = owner
        self.handler = handler

def read_request(event):
    print("parse request")
    event.owner["state"] = "KEEPALIVE"
    event.handler = wait_for_next_request

def wait_for_next_request(event):
    print("same fd now waits for another request")

event = Event({"state": "READING"}, read_request)
event.handler(event)
event.handler(event)
""",
        [("`Event.owner`", "`ev->data` → connection → request"), ("handler field", "`ngx_event_t.handler`"), ("handler replacement", "request parsing、keepalive、lingering close 等狀態切換"), ("same event", "同一 connection read event 在不同時間承擔不同 continuation")],
        ["找 handler 的所有 assignment，依時間排序。", "找 handler 內如何由 `ev->data` 還原 owner。", "檢查 timer 與 I/O callback 是否可能競爭完成同一 owner。", "Posted events 會延後 callback；靜態 call stack 看不到這條邊。"],
    ),
    14: E(
        """
Event loop 是 cooperative scheduler；它不會中斷一個慢 handler。每輪要在 ready I/O、posted work 與 expired timers 間維持順序與有限工作量。
""",
        r"""
from collections import deque
import heapq
import time

posted = deque()
timers = []

def call_later(delay, fn):
    heapq.heappush(timers, (time.monotonic() + delay, fn))

posted.append(lambda: print("ready I/O"))
call_later(0.01, lambda: print("timer"))

while posted or timers:
    while posted:
        posted.popleft()()      # each callback must stay short
    now = time.monotonic()
    while timers and timers[0][0] <= now:
        heapq.heappop(timers)[1]()
    if timers:
        time.sleep(max(0, timers[0][0] - time.monotonic()))
""",
        [("outer loop", "`ngx_process_events_and_timers` 所在 worker cycle"), ("`posted`", "NGINX posted event queues"), ("`timers[0]`", "timer rbtree 的最小 deadline"), ("short callback", "run-to-completion、沒有 preemption 的 handler contract")],
        ["先看 loop 每輪的處理順序，再看每個 helper。", "任何 synchronous DNS/file/library call 都可能凍結 worker。", "Timer timeout 會成為 OS wait 的最大睡眠時間。", "Accept events、normal events、posted events 的優先順序影響公平性。"],
    ),
    15: E(
        """
只用 list 保存 timers，找最近 deadline 或取消任意 event 會變慢。Python 用 heap 示範 ordered deadline；NGINX 因需要 intrusive arbitrary deletion，選擇紅黑樹。
""",
        r"""
import heapq
import itertools

clock = 1000
sequence = itertools.count()
heap = []
cancelled = set()

def add_timer(event_id, delay_ms):
    heapq.heappush(heap, (clock + delay_ms, next(sequence), event_id))

def cancel(event_id):
    cancelled.add(event_id)    # heap example uses lazy deletion

add_timer("read-timeout", 500)
add_timer("keepalive", 100)
cancel("read-timeout")
while heap:
    deadline, _, event_id = heapq.heappop(heap)
    if event_id not in cancelled:
        print("next:", event_id, deadline)
        break
""",
        [("heap minimum", "NGINX timer rbtree 最左節點"), ("event id", "`ngx_event_t` 內嵌的 `timer` node"), ("cancel set", "NGINX 可直接 `ngx_rbtree_delete`，不需 lazy tombstone"), ("deadline", "`ngx_msec_t` absolute timer key")],
        ["列出 operation set：min、insert、arbitrary delete，再理解為何不是只用 heap。", "Timer node 內嵌於 event，不能同時重複插入。", "I/O 完成時要取消 timer 並清 `timer_set`。", "時間差比較要能處理整數 wraparound。"],
    ),
    16: E(
        """
Producer 若不理會 consumer 速度，queue 只會變大。Bounded queue 讓 `put` 在容量滿時停止 producer；NGINX 則透過 buffer 水位與 read/write event interest 傳遞同樣訊號。
""",
        r"""
from collections import deque

HIGH_WATER = 3
LOW_WATER = 1
buffer = deque()
producer_enabled = True

for chunk in [b"a", b"b", b"c", b"d"]:
    if producer_enabled:
        buffer.append(chunk)
    if len(buffer) >= HIGH_WATER:
        producer_enabled = False
        print("pause upstream reads")

while buffer:
    print("send", buffer.popleft())
    if len(buffer) <= LOW_WATER and not producer_enabled:
        producer_enabled = True
        print("resume upstream reads")
""",
        [("`buffer`", "out/busy/free buffer chains"), ("high water", "buffer/temp-file capacity policy"), ("pause producer", "移除/停用 upstream read interest"), ("resume", "client write 釋放 buffers 後重新啟用 read")],
        ["AGAIN 後保留 unsent cursor，不能重新產生資料。", "Pause read 與 close upstream 是不同動作。", "一輪處理 bytes 太多也會讓其他 ready connections starvation。", "Buffering 將成本從 backend connection 轉移到 memory/disk，並非免費。"],
    ),
    17: E(
        """
若把 HTTP method、headers 與 routing 結果直接塞進 connection，keep-alive 的下一個 request 會繼承上一個 request 的狀態。獨立 request context 讓 transport 可重用，而語意交換可各自建立與釋放。
""",
        r"""
from dataclasses import dataclass, field

@dataclass
class Connection:
    fd: int
    request: "Request | None" = None

@dataclass
class Request:
    connection: Connection
    method: str = ""
    headers: dict = field(default_factory=dict)
    module_ctx: dict = field(default_factory=dict)
    references: int = 1

connection = Connection(fd=7)
first = Request(connection, method="GET")
connection.request = first
connection.request = None          # first request finalized
second = Request(connection, method="POST")
connection.request = second        # same transport, new semantics
print(connection.fd, second.method)
""",
        [("`Connection`", "`ngx_connection_t`"), ("`Request`", "`ngx_http_request_t`"), ("`module_ctx`", "各 HTTP module 以 ctx index 保存 request-local state"), ("`references`", "main/subrequest/async work 使用的 request count")],
        ["從 `ngx_http_create_request` 看哪些欄位在 request birth 時初始化。", "分清 request pool 與 connection pool 的 owner/lifetime。", "追 `r->main`、`r->parent`、`r->count` 如何影響 finalize。", "Internal redirect 會改 routing state，但不應讓舊 module ctx 產生不一致。"],
    ),
    18: E(
        """
用 `split()` 解析 request line 假設整行一次到齊，遇到 fragmented TCP input 就失敗。Incremental FSM 保存 state 與 token buffer；資料不足不是錯誤，而是等待更多 bytes。
""",
        r"""
class RequestLineParser:
    def __init__(self):
        self.state = "METHOD"
        self.method = bytearray()
        self.uri = bytearray()

    def feed(self, data):
        for byte in data:
            ch = chr(byte)
            if self.state == "METHOD":
                if ch == " ":
                    self.state = "URI"
                elif ch.isupper():
                    self.method.append(byte)
                else:
                    raise ValueError("invalid method")
            elif self.state == "URI":
                if ch == " ":
                    self.state = "VERSION"
                else:
                    self.uri.append(byte)
        return self.state

p = RequestLineParser()
print(p.feed(b"GE"), p.feed(b"T /ap"), p.feed(b"i HTTP/1.1\r\n"))
print(p.method.decode(), p.uri.decode())
""",
        [("`state`", "`r->state` parser state"), ("`feed`", "`ngx_http_parse_request_line` 可被多次呼叫"), ("data exhausted", "`NGX_AGAIN`：prefix 合法但尚未完整"), ("method/URI markers", "NGINX 以 buffer pointers 避免複製 token")],
        ["把大 switch 畫成 state graph，再看每個 case 接受哪些字元。", "區分 invalid prefix 與 incomplete prefix 的 return code。", "檢查 token start/end pointer 是否仍落在有效 buffer。", "Raw URI、normalized URI、args markers 在安全與 routing 上不可混用。"],
    ),
    19: E(
        """
把 headers 全部放普通 dict 會遺失重複順序，也無法對 `Host`、framing headers 套專屬規則。較好的模型同時保留 generic list 與 known-header typed fields。
""",
        r"""
class Headers:
    def __init__(self):
        self.all = []
        self.host = None
        self.content_length = None

    def add(self, name, value):
        lower = name.lower()
        self.all.append((name, value))
        if lower == "host":
            if self.host is not None:
                raise ValueError("duplicate Host")
            self.host = value
        elif lower == "content-length":
            length = int(value)
            if self.content_length not in (None, length):
                raise ValueError("conflicting Content-Length")
            self.content_length = length

h = Headers()
h.add("Host", "example.test")
h.add("X-Trace", "abc")
print(h.all, h.host)
""",
        [("`all` list", "`r->headers_in.headers` generic list"), ("typed fields", "`headers_in.host`、`content_length` 等 shortcut"), ("`add` dispatch", "known-header hash 對應的 processing callback"), ("conflict error", "`ngx_http_process_request_header` 的整體 semantic validation")],
        ["Generic line parser 與 known-header handler 要分開讀。", "檢查重複 header 的 policy；不同欄位不能一律 merge。", "Host 可能切換 virtual server/config context。", "Content-Length/Transfer-Encoding 影響 message boundary，需防 parser differential。"],
    ),
    20: E(
        """
每次 request 線性掃描所有 location 規則既慢又容易搞錯 precedence。啟動時先編譯 exact/prefix/regex 結構，runtime 只按明確規則查找。
""",
        r"""
import re

exact = {"/health": "health-handler"}
prefixes = {
    "/": "frontend",
    "/api/": "api-proxy",
    "/static/": "file-server",
}
regexes = [(re.compile(r"\.php$"), "fastcgi")]

def match(uri):
    if uri in exact:
        return exact[uri]
    best = max((p for p in prefixes if uri.startswith(p)),
               key=len, default=None)
    for pattern, handler in regexes:
        if pattern.search(uri):
            return handler
    return prefixes.get(best)

for uri in ["/health", "/api/users", "/index.php"]:
    print(uri, "->", match(uri))
""",
        [("exact dict", "exact location lookup"), ("longest prefix", "static location tree 的最長 prefix 結果"), ("ordered regexes", "regex location 保留 configuration order"), ("returned handler/config", "切換到匹配 location 的 module loc conf array")],
        ["先手算 location precedence，再讀 tree/regex implementation。", "URI normalization 先後會改變匹配與安全結果。", "Internal redirect 可能再次執行 location lookup。", "Runtime 使用的不是原始 config text，而是 init/merge 後的結構。"],
    ),
    21: E(
        """
讓每個 middleware 自己呼叫下一個容易造成重複、漏呼叫與 async continuation 混亂。Phase engine 用 index 與 return-code protocol 統一決定 continue、stop、pause 或 finalize。
""",
        r"""
DECLINED = "DECLINED"
OK = "OK"
AGAIN = "AGAIN"

def rewrite(request):
    request["uri"] = request["uri"].replace("/old", "/new")
    return DECLINED

def access(request):
    return OK if request.get("authorized") else 403

def content(request):
    request["body"] = b"hello"
    return OK

def run_phases(request, handlers):
    for handler in handlers:
        rc = handler(request)
        if rc == DECLINED:
            continue
        if rc == AGAIN or isinstance(rc, int):
            return rc
    return OK

print(run_phases({"uri": "/old", "authorized": True},
                 [rewrite, access, content]))
""",
        [("handlers list", "configuration-time 編好的 phase engine array"), ("loop index", "`r->phase_handler`"), ("`DECLINED`", "本 handler 不處理，交給下一個"), ("`AGAIN`/status", "暫停 async work 或直接 short-circuit/finalize")],
        ["Handler 與 phase checker 必須一起讀，因為 return code 語意由 checker 解釋。", "找 phase engine 在 postconfiguration 如何被編譯。", "Rewrite 可能修改 URI 並跳回 location lookup。", "Async handler 返回前必須保存 state 並安排未來 callback。"],
    ),
    22: E(
        """
將所有 request body 讀進 RAM 對大上傳不安全；完全 streaming 又可能無法 retry。這個例子先在 memory 累積，超過門檻便 spill 到 temporary file。
""",
        r"""
import tempfile

class BodyStore:
    def __init__(self, memory_limit=8):
        self.limit = memory_limit
        self.memory = bytearray()
        self.file = None

    def feed(self, chunk):
        if self.file is None and len(self.memory) + len(chunk) <= self.limit:
            self.memory.extend(chunk)
            return
        if self.file is None:
            self.file = tempfile.TemporaryFile()
            self.file.write(self.memory)
            self.memory.clear()
        self.file.write(chunk)

store = BodyStore()
for chunk in [b"abcd", b"efgh", b"ijkl"]:
    store.feed(chunk)
print("spilled:", store.file is not None)
store.file.close()
""",
        [("`feed(chunk)`", "client read event 逐批填 request-body buffers"), ("memory limit", "`client_body_buffer_size` 類政策"), ("temporary file", "`ngx_temp_file_t` request body storage"), ("completion callback", "body 完整後才呼叫 module 的 post handler")],
        ["Header buffer 中可能已有 preread body bytes。", "Body API 是 async；初次呼叫返回不代表 body ready。", "Chunked parser 與 storage/filter 是不同層。", "Client abort/error 時檢查 temporary file cleanup 與 callback ownership。"],
    ),
    23: E(
        """
Content producer 若自己同時做 gzip、header 修改、chunking 與 socket write，功能組合會爆炸。Filter chain 讓每一層只做一種轉換並轉交下一層。
""",
        r"""
def sink(chunks):
    return b"".join(chunks)

def uppercase_filter(next_filter):
    def run(chunks):
        return next_filter([chunk.upper() for chunk in chunks])
    return run

def prefix_filter(next_filter):
    def run(chunks):
        return next_filter([b"[proxy] "] + chunks)
    return run

top_filter = prefix_filter(uppercase_filter(sink))
print(top_filter([b"hello", b" nginx"]))
""",
        [("`top_filter`", "`ngx_http_top_body_filter`"), ("closure `next_filter`", "每個 module 保存的 `ngx_http_next_body_filter`"), ("chunks", "`ngx_chain_t` buffers"), ("sink", "最終 write/output filter")],
        ["註冊順序決定 filter order；不要依 source file 排列猜。", "跨 buffers 的 transformation state 必須放 request ctx。", "下游回 AGAIN 時上游不能丟失 busy buffers。", "傳遞 `last_buf`、`flush`、`sync` 等 framing/stream flags。"],
    ),
    24: E(
        """
每個 callback 都直接 free request 會 double free；等到所有 subrequests/async work 完成又需要 join。Reference count 加單一 finalize gate 能讓多分支只收口一次。
""",
        r"""
class Request:
    def __init__(self):
        self.references = 1
        self.closed = False

    def retain(self):
        self.references += 1

    def finalize(self):
        self.references -= 1
        if self.references == 0 and not self.closed:
            self.closed = True
            print("run cleanup, then keepalive-or-close")

r = Request()
r.retain()       # subrequest
r.retain()       # asynchronous output
r.finalize()     # main path done
r.finalize()     # subrequest done
r.finalize()     # output done: cleanup exactly once
""",
        [("`references`", "`r->main->count`"), ("`retain`", "建立 subrequest/async work 時增加 completion dependency"), ("`finalize`", "`ngx_http_finalize_request` protocol"), ("cleanup once", "request pool cleanup 後切 keepalive/lingering close/close")],
        ["Finalize 不一定立即 free；先看 rc、count 與 posted requests。", "Headers 已送出後 error path 不能任意換 status。", "Keep-alive 重用 connection，不重用已 finalize 的 request object。", "所有 timers/events 在 owner cleanup 前必須取消或轉移。"],
    ),
    25: E(
        """
通用 upstream engine 不應知道 HTTP proxy request 如何拼 URI/header。Proxy module 以 callbacks 提供 encode/decode 細節，讓 core 只處理 connect、timeout、retry 與搬運。
""",
        r"""
class UpstreamAdapter:
    def create_request(self, request):
        headers = {"Host": "backend", "X-Forwarded-For": request["ip"]}
        lines = [f"{request['method']} {request['uri']} HTTP/1.1"]
        lines += [f"{k}: {v}" for k, v in headers.items()]
        return ("\r\n".join(lines) + "\r\n\r\n").encode()

    def process_header(self, raw):
        status_line = raw.split(b"\r\n", 1)[0]
        return int(status_line.split()[1])

adapter = UpstreamAdapter()
wire = adapter.create_request(
    {"method": "GET", "uri": "/api", "ip": "203.0.113.5"}
)
print(wire.decode(), adapter.process_header(b"HTTP/1.1 200 OK\r\n"))
""",
        [("`UpstreamAdapter`", "proxy module 注入 upstream 的 callback set"), ("`create_request`", "`ngx_http_proxy_create_request`"), ("`process_header`", "`ngx_http_proxy_process_status_line/header`"), ("wire bytes", "`u->request_bufs` backend-side buffer chain")],
        ["Proxy URI replacement 要用有/無 trailing slash 的案例推演。", "Hop-by-hop headers 應刪除或重建，不能盲目複製 client headers。", "Protocol callback 配置在 `ngx_http_upstream_t` 哪些欄位。", "Variables 可能讓 upstream URL/headers 到 runtime 才確定。"],
    ),
    26: E(
        """
把 upstream 寫成一個 blocking 函式會在 connect/read 等待時卡住 worker。顯式 state machine 把每個 readiness event 映射成一個 transition。
""",
        r"""
from enum import Enum, auto

class State(Enum):
    CREATE = auto()
    CONNECTING = auto()
    SENDING = auto()
    READING_HEADER = auto()
    STREAMING_BODY = auto()
    DONE = auto()

class Upstream:
    def __init__(self):
        self.state = State.CREATE

    def advance(self, event):
        transitions = {
            (State.CREATE, "start"): State.CONNECTING,
            (State.CONNECTING, "writable"): State.SENDING,
            (State.SENDING, "sent"): State.READING_HEADER,
            (State.READING_HEADER, "header"): State.STREAMING_BODY,
            (State.STREAMING_BODY, "eof"): State.DONE,
        }
        self.state = transitions[(self.state, event)]

u = Upstream()
for event in ["start", "writable", "sent", "header", "eof"]:
    u.advance(event)
print(u.state)
""",
        [("`Upstream.state`", "`ngx_http_upstream_t` 中的 buffers/handlers/flags 所表示的階段"), ("`advance`", "upstream read/write event handlers"), ("event names", "connect writable、send complete、header readable、body EOF"), ("transition table", "替換 `u->read_event_handler`／`write_event_handler`")],
        ["先列出 handler replacement timeline，再看大函式內部。", "Attempt timings 每 retry 一次就新增 state record。", "Protocol reinit 是 retry transition 的必要部分。", "Client abort、timer、peer error 都可從任意 state 導向 next/finalize。"],
    ),
    27: E(
        """
Non-blocking `connect()` 的『正在進行』不是失敗；socket writable 也不保證成功。完成階段必須讀 socket error，才能區分 connected 與 refused。
""",
        r"""
import errno
import selectors
import socket

sock = socket.socket()
sock.setblocking(False)
rc = sock.connect_ex(("127.0.0.1", 9))

if rc in (0, errno.EINPROGRESS, errno.EWOULDBLOCK):
    selector = selectors.DefaultSelector()
    selector.register(sock, selectors.EVENT_WRITE)
    ready = selector.select(timeout=0.1)
    if ready:
        error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        print("connected" if error == 0 else f"failed: {error}")
    else:
        print("connect timeout")
    selector.close()
sock.close()
""",
        [("`connect_ex`", "`connect()` 與 `NGX_AGAIN`/EINPROGRESS"), ("EVENT_WRITE", "upstream connect write event"), ("`SO_ERROR`", "`ngx_http_upstream_test_connect` 類確認"), ("timeout", "connect event timer")],
        ["Epoll writable 只是 connect 已完成到可檢查狀態。", "Connect timer 成功/失敗後應刪除，再切 send/read timer。", "失敗時 close connection 並呼叫 peer free 回饋。", "Immediate success 與 async success 最後必須進同一 send-request path。"],
    ),
    28: E(
        """
將權重份額連續送出會產生 burst。Smooth weighted round robin 每輪累加 current weight、選最大者，再從 winner 扣除總權重，使長期比例正確且短期更平滑。
""",
        r"""
class Peer:
    def __init__(self, name, weight):
        self.name = name
        self.weight = weight
        self.effective = weight
        self.current = 0

def choose(peers):
    total = 0
    best = None
    for peer in peers:
        peer.current += peer.effective
        total += peer.effective
        if best is None or peer.current > best.current:
            best = peer
    best.current -= total
    return best.name

peers = [Peer("A", 5), Peer("B", 1)]
print([choose(peers) for _ in range(12)])
""",
        [("`Peer.current`", "`current_weight`"), ("`Peer.effective`", "`effective_weight`，可因失敗降低"), ("`total`", "本輪所有有效權重總和"), ("winner subtract", "平滑分布的核心 invariant")],
        ["手算前數輪 current weights，不要只背 code。", "區分 configured/effective/current 三種 weight。", "Per-request tried bitmap 避免 retry 重選同一 peer。", "Free callback 的失敗回饋會改 effective weight 與 fail counters。"],
    ),
    29: E(
        """
不同 workload 需要不同 selection signal。Strategy interface 讓 round robin、least-connections 與 hash 共用同一 `choose` contract，transport 不必知道演算法。
""",
        r"""
import hashlib

peers = [
    {"name": "A", "connections": 8},
    {"name": "B", "connections": 2},
    {"name": "C", "connections": 4},
]

def round_robin(request, peers):
    return peers[request["number"] % len(peers)]

def least_connections(request, peers):
    return min(peers, key=lambda peer: peer["connections"])

def hash_key(request, peers):
    value = int(hashlib.md5(request["key"].encode()).hexdigest(), 16)
    return peers[value % len(peers)]

request = {"number": 5, "key": "tenant-42"}
for strategy in [round_robin, least_connections, hash_key]:
    print(strategy.__name__, strategy(request, peers)["name"])
""",
        [("strategy function", "upstream peer init/get callback"), ("request key", "ip hash/hash module 的 runtime key"), ("connection metric", "least_conn peer counters"), ("same return shape", "共用 `ngx_peer_connection_t` output contract")],
        ["先問 metric 是否真的代表 load；connections 不等於 CPU work。", "Hash 的 key distribution 與 backend churn 會造成 hotspot/remap。", "State 是 per worker 還是 shared zone 會影響精確度。", "所有策略都需處理 tried/down/unavailable 與 fallback。"],
    ),
    30: E(
        """
遇到任何錯誤都 retry 看似提高成功率，實際可能重複付款或造成 retry storm。Decision 必須同時看失敗階段、method semantics、body replayability、剩餘 peers 與 deadline。
""",
        r"""
def may_retry(*, method, stage, body_buffered,
              response_started, tries_left):
    if tries_left <= 0 or response_started:
        return False
    if stage == "connect":
        return True
    idempotent = method in {"GET", "HEAD", "PUT", "DELETE"}
    if stage in {"send", "read_header"}:
        return idempotent and body_buffered
    return False

cases = [
    dict(method="GET", stage="connect", body_buffered=True,
         response_started=False, tries_left=1),
    dict(method="POST", stage="read_header", body_buffered=True,
         response_started=False, tries_left=1),
]
for case in cases:
    print(case, may_retry(**case))
""",
        [("`stage`", "connect/send/read header/body 的 upstream failure context"), ("`body_buffered`", "request 是否可重播"), ("`response_started`", "header/body 是否已送 client"), ("`tries_left`", "next_upstream_tries、tried peers 與 timeout budget")],
        ["HTTP method 不能完整代表 application idempotency。", "記錄 bytes/request_sent 狀態，判斷結果是否可能已產生。", "Retry 前需 reinit protocol parser/buffers。", "總 latency budget 應限制多次 per-attempt timeout 疊加。"],
    ),
    31: E(
        """
無界保存 backend connections 會耗盡 fd；只用 stack/list 又無法快速取用與淘汰。有限 LRU cache 保存 idle、乾淨且 identity 相符的 connections。
""",
        r"""
from collections import OrderedDict

class KeepaliveCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.idle = OrderedDict()

    def put(self, peer, connection):
        self.idle[peer] = connection
        self.idle.move_to_end(peer)
        if len(self.idle) > self.capacity:
            old_peer, old_connection = self.idle.popitem(last=False)
            old_connection["closed"] = True

    def get(self, peer):
        return self.idle.pop(peer, None)

cache = KeepaliveCache(2)
cache.put("A", {"fd": 10})
cache.put("B", {"fd": 11})
print(cache.get("A"))
""",
        [("`OrderedDict`", "keepalive cache queue/LRU ordering"), ("`peer` key", "sockaddr/peer identity matching"), ("`put`", "upstream free callback 判定可 keepalive 後回收"), ("`get`", "wrapped peer get callback 命中 idle connection")],
        ["回收前確認 response framing 完整且沒有 unread bytes。", "Idle read handler 用來偵測 backend 主動 close。", "Cache 通常 per worker，容量不是全機精確總數。", "Eviction/close 必須移除 timer/event 並釋放 connection pool。"],
    ),
    32: E(
        """
直接將 backend `recv()` 結果立刻 `send()` 給 client，慢 client 會長期占住 backend。Bounded buffer pump 能暫停 upstream、逐步送 downstream，必要時 spill disk。
""",
        r"""
from collections import deque

class ProxyPump:
    def __init__(self, capacity=3):
        self.capacity = capacity
        self.queue = deque()
        self.upstream_read_enabled = True

    def from_upstream(self, chunk):
        if len(self.queue) >= self.capacity:
            self.upstream_read_enabled = False
            return False
        self.queue.append(chunk)
        return True

    def to_client(self):
        if not self.queue:
            return None
        chunk = self.queue.popleft()
        if len(self.queue) < self.capacity:
            self.upstream_read_enabled = True
        return chunk

pump = ProxyPump()
for chunk in [b"a", b"b", b"c", b"d"]:
    print("accepted:", pump.from_upstream(chunk))
while pump.queue:
    print("sent:", pump.to_client())
""",
        [("queue", "event pipe 的 out/busy chains"), ("capacity", "memory buffers 與 temp-file policy"), ("disable upstream read", "backpressure 調整 upstream event interest"), ("`to_client`", "downstream write/output filter 釋放 buffers")],
        ["先分 buffered 與 non-buffered upstream body path。", "追 buffer 在 free/in/out/busy lists 間的 ownership。", "Temporary file 是容量層，不是自動錯誤。", "Client write AGAIN 時不能繼續無界讀 upstream。"],
    ),
    33: E(
        """
普通 dict cache 沒有 freshness、single-flight、disk publish 或跨 worker metadata。這個縮小模型示範同 key 只讓一個 owner 回源，其他 callers 等待結果，避免熱門 key 同時擊穿 backend。
""",
        r"""
import threading
import time

cache = {}
locks = {}
global_lock = threading.Lock()

def get_or_load(key, loader):
    with global_lock:
        lock = locks.setdefault(key, threading.Lock())
    with lock:                       # single flight per key
        item = cache.get(key)
        if item and item["expires"] > time.time():
            return item["value"], "HIT"
        value = loader()
        cache[key] = {"value": value, "expires": time.time() + 10}
        return value, "MISS"

value, status = get_or_load("/news", lambda: b"from backend")
print(status, value)
""",
        [("`cache`", "shared cache metadata + cache files 的概念合體"), ("per-key `lock`", "cache lock/single-flight 防 stampede"), ("`expires`", "valid_sec/freshness metadata"), ("`loader`", "cache miss 後進 upstream")],
        ["真實 NGINX 的 body 多在 disk，shared memory 主要保存 metadata/index。", "Cache key 要包含所有會改變 response 的維度。", "Temporary file 完成後才 atomic publish，避免讀到半檔。", "Stale、revalidate、bypass、lock timeout 都是不同 policy branch。"],
    ),
    34: E(
        """
逐一追蹤每個短命 allocation 的 free 會讓所有 error path 複雜。Arena 將同壽命 objects 放進同一 owner，結束時整批釋放；外部資源則另登記 cleanup。
""",
        r"""
class Arena:
    def __init__(self):
        self.objects = []
        self.cleanups = []

    def allocate(self, factory):
        value = factory()
        self.objects.append(value)
        return value

    def cleanup(self, fn):
        self.cleanups.append(fn)

    def destroy(self):
        for fn in reversed(self.cleanups):
            fn()
        self.objects.clear()

request_pool = Arena()
headers = request_pool.allocate(list)
request_pool.cleanup(lambda: print("close temp file"))
headers.append(("Host", "example.test"))
request_pool.destroy()
""",
        [("`Arena`", "`ngx_pool_t`"), ("`allocate`", "`ngx_palloc`/`ngx_pcalloc`"), ("objects clear", "pool blocks 一次 destroy，而非逐物件 free"), ("cleanup list", "`ngx_pool_cleanup_t` 用於 file/library side effects")],
        ["先問 pool owner 是 cycle、connection 還是 request。", "Small allocations 通常不能用 `ngx_pfree` 逐一回收。", "Pointer 不得逃到比 pool 更長命的 cache/global object。", "Cleanup callback 的順序與是否可能重入需要明確。"],
    ),
    35: E(
        """
看到資料就使用 dict/list 是語言便利，不代表符合 operation set。這個例子先列需求，再選 heap、dict 或 deque；NGINX 同樣依 min、prefix、append、arbitrary delete 等操作選不同 container。
""",
        r"""
from collections import deque
import heapq

def choose_structure(operations):
    if {"lookup_by_key", "insert"} <= operations:
        return "hash table"
    if {"find_min", "insert"} <= operations:
        return "heap or ordered tree"
    if {"append", "pop_left"} <= operations:
        return "queue/deque"
    return "array/list"

workloads = [
    {"lookup_by_key", "insert"},
    {"find_min", "insert", "delete_arbitrary"},
    {"append", "pop_left"},
]
for operations in workloads:
    print(operations, "->", choose_structure(operations))
""",
        [("lookup workload", "config/header hashes"), ("find min + arbitrary delete", "timer rbtree"), ("append/iterate", "NGINX array/list"), ("queue/deque", "posted events、LRU、free/busy chains")],
        ["確認 container 是否 owns element，或只掛 intrusive node。", "同一 object 可嵌多個 node 參與不同索引。", "Big-O 之外看資料量、cache locality 與 configuration-time/runtime 比例。", "Queue macros 通常不防重複插入，invariant 在 caller。"],
    ),
    36: E(
        """
每個 filter 都複製 bytes 會增加 memory bandwidth 與 allocation。Python `memoryview` 展示 buffer 作為底層資料的 view；移動 cursor 即可表示 partial consumption。
""",
        r"""
data = bytearray(b"HTTP header|response body")
header = memoryview(data)[:11]
body = memoryview(data)[12:]

chain = [
    {"view": header, "sent": 0},
    {"view": body, "sent": 0},
]

def consume(buffer, amount):
    start = buffer["sent"]
    end = min(len(buffer["view"]), start + amount)
    piece = bytes(buffer["view"][start:end])
    buffer["sent"] = end
    return piece

print(consume(chain[0], 5))
print(consume(chain[0], 99))
print(bytes(chain[1]))
""",
        [("`memoryview`", "`ngx_buf_t` 對 memory range 的 view"), ("chain list", "`ngx_chain_t`"), ("`sent` cursor", "`b->pos`/`b->file_pos`"), ("same underlying data", "shadow/sliced buffers 避免複製")],
        ["Memory 與 file buffers 有兩組不同 cursor。", "Flags 決定資料能否修改、是否在 file、是否 response 結束。", "Partial write 只前進 cursor，不能丟掉整個 node。", "Shadow buffers 共用 storage，回收 owner 時要避免 dangling view。"],
    ),
    37: E(
        """
Fork 後普通 Python dict 與 C heap 都是 process-private。跨 workers 計數需要真正 shared memory 加同步；lock 的目的不是包住某行，而是保護多欄位 invariant。
""",
        r"""
from multiprocessing import Lock, Process, Value

counter = Value("i", 0)
lock = Lock()

def add_requests(amount):
    for _ in range(amount):
        with lock:
            counter.value += 1

workers = [Process(target=add_requests, args=(10_000,)) for _ in range(2)]
for worker in workers:
    worker.start()
for worker in workers:
    worker.join()
print(counter.value)
""",
        [("`Value`", "mmap/shared memory zone 中的 shared field"), ("`Lock`", "`ngx_shmtx_t` 或 atomic protocol"), ("worker processes", "多 NGINX workers"), ("shared object creation", "zone init callback + slab allocation")],
        ["Shared zone name/size 是 reload compatibility contract。", "Slab allocator 的 metadata 也必須在 shared mapping 內。", "列出 lock 保護的完整 invariant，避免只鎖部分更新。", "Process-local pointer/allocator state 不能錯放進 shared data。"],
    ),
    38: E(
        """
每新增功能都修改 central core 會造成耦合與回歸。Plugin registry 將名稱、config parser、lifecycle 與 runtime callback 放進 descriptor，core 只依共同 contract 操作。
""",
        r"""
MODULES = []

class Module:
    def __init__(self, name, directives, on_request):
        self.name = name
        self.directives = directives
        self.on_request = on_request

def register(module):
    MODULES.append(module)

register(Module(
    name="hello",
    directives={"hello": lambda value: {"text": value}},
    on_request=lambda request, conf: conf["text"].encode(),
))

for module in MODULES:
    if "hello" in module.directives:
        conf = module.directives["hello"]("NGINX")
        print(module.on_request({}, conf))
""",
        [("`Module` descriptor", "`ngx_module_t` + type-specific module context"), ("`directives`", "`ngx_command_t[]`"), ("`register`", "build-time module list/indices"), ("lifecycle/runtime callbacks", "create/merge/postconfiguration/process init/request handlers")],
        ["Module generic descriptor 與 HTTP-specific ctx 要一起讀。", "`index` 與 `ctx_index` 服務不同查找空間。", "Create/merge conf 在 configuration lifecycle；request handler 在 data plane。", "Filter 註冊靠保存 previous top pointer，形成全域 chain。"],
    ),
    39: E(
        """
第一個 module 不應直接寫 socket；那會繞過 TLS、HTTP/2、gzip 與 partial write。正確做法是建立 framework response object/buffer，再交給共同 output pipeline。
""",
        r"""
from dataclasses import dataclass

@dataclass
class Response:
    status: int
    headers: dict
    body: bytes

def hello_handler(request, text="hello nginx\n"):
    body = text.encode()
    headers = {
        "Content-Type": "text/plain",
        "Content-Length": str(len(body)),
    }
    if request["method"] == "HEAD":
        body = b""
    elif request["method"] != "GET":
        return Response(405, {"Content-Length": "0"}, b"")
    return Response(200, headers, body)

print(hello_handler({"method": "GET"}))
""",
        [("`Response`", "`r->headers_out` + output buffer chain"), ("handler", "core loc conf 中安裝的 content handler"), ("body bytes", "request pool 配置的 `ngx_buf_t`"), ("framework return", "`ngx_http_send_header` + `ngx_http_output_filter`")],
        ["Directive callback 如何把 handler 安裝到 location。", "GET/HEAD/body discard/header-only 分支。", "Content-Length、buffer length 與 `last_buf` 必須一致。", "Output filter 的 return code 可能代表 AGAIN/error，不是一定立即送完。"],
    ),
    40: E(
        """
把 auth 寫進每個 content handler 會重複且容易漏保護。Access middleware 在固定 phase 執行；未啟用就 DECLINED，拒絕就 short-circuit，允許則依 satisfy policy 繼續。
""",
        r"""
DECLINED = object()

def api_key_access(request, configured_key=None):
    if configured_key is None:
        return DECLINED
    supplied = request["headers"].get("X-API-Key")
    return DECLINED if supplied == configured_key else 403

def run_access(request, handlers):
    for handler in handlers:
        rc = handler(request)
        if rc is DECLINED:
            continue
        return rc
    return "continue to content"

request = {"headers": {"X-API-Key": "secret"}}
print(run_access(request, [lambda r: api_key_access(r, "secret")]))
""",
        [("access handler", "掛在 `NGX_HTTP_ACCESS_PHASE` 的 module handler"), ("`DECLINED`", "未處理／允許其他 handlers 繼續"), ("403", "HTTP status short-circuit phase engine"), ("configured key", "merged location configuration")],
        ["Return code 要配合 access phase checker/satisfy policy理解。", "未設定與設定為空值需用 sentinel 分辨。", "Internal redirect/subrequest 是否重驗 policy 要明確。", "錯誤 branch 預設 fail closed，且不要將 secret 寫入 log。"],
    ),
    41: E(
        """
每次 log/header 使用時都重新產生 request ID 會得到不同值；啟動時替所有 requests 預算又浪費。Lazy property 在第一次需要時生成並 cache，所有 consumers 讀同一份。
""",
        r"""
from functools import cached_property
import secrets

class Request:
    @cached_property
    def request_id_short(self):
        print("computed once")
        return secrets.token_hex(4)

request = Request()
access_log_value = request.request_id_short
response_header = request.request_id_short
print(access_log_value, response_header)
""",
        [("`cached_property`", "variable get handler + request variables cache"), ("first lookup", "consumer 取 indexed variable 時呼叫 get handler"), ("cached string", "request pool/module ctx 中穩定資料"), ("second lookup", "`valid/not_found/no_cacheable` 控制的重用")],
        ["Variable value 的 data pointer 不能指向 stack。", "`not_found` 與空字串不同。", "若值可能隨時間變才設 `no_cacheable`。", "Header filter 使用同一 ctx，並避免 subrequest/重入時重複加入。"],
    ),
    42: E(
        """
對每個 chunk 單獨 `replace()` 會漏掉跨 chunk token。Streaming transform 必須保存最多 token 長度減一的 suffix，直到確定不可能與下一 chunk 組成 match。
""",
        r"""
class StreamingReplace:
    def __init__(self, old, new):
        self.old = old
        self.new = new
        self.carry = b""

    def feed(self, chunk, final=False):
        data = self.carry + chunk
        if final:
            self.carry = b""
            return data.replace(self.old, self.new)
        keep = min(len(self.old) - 1, len(data))
        stable, self.carry = data[:-keep], data[-keep:]
        return stable.replace(self.old, self.new)

f = StreamingReplace(b"foo", b"bar")
print(f.feed(b"xxf"), f.feed(b"ooyy", final=True))
""",
        [("`carry`", "body filter request ctx 中跨 buffers 的 parser state"), ("`feed`", "每次 top body filter 收到一條 chain"), ("`final`", "`last_buf`/`last_in_chain`"), ("returned bytes", "新建或 shadow output buffers 交 next filter")],
        ["若 replacement 改變長度，原 Content-Length 必須移除/重算。", "Read-only/file buffer 不可直接原地修改。", "Flush/sync/last flags 要移到語意正確的 output buffer。", "對 token 的每一種切分位置做測試，並加入 downstream AGAIN。"],
    ),
    43: E(
        """
Custom balancer 的演算法通常不難，難的是 config-time data、per-request tried set、shared feedback 與 get/free callback contract。這個例子把 selection 與 completion feedback 分開。
""",
        r"""
class LatencyBalancer:
    def __init__(self, peers):
        self.peers = {
            name: {"latency_ms": latency, "failures": 0}
            for name, latency in peers.items()
        }

    def get(self, tried):
        candidates = [
            (state["latency_ms"] + state["failures"] * 100, name)
            for name, state in self.peers.items()
            if name not in tried
        ]
        return min(candidates)[1]

    def free(self, name, success, latency_ms):
        state = self.peers[name]
        state["latency_ms"] = 0.8 * state["latency_ms"] + 0.2 * latency_ms
        state["failures"] = 0 if success else state["failures"] + 1

b = LatencyBalancer({"A": 20, "B": 50})
peer = b.get(tried=set())
b.free(peer, success=False, latency_ms=200)
print(b.get(tried={peer}))
""",
        [("`get`", "peer get callback 填 sockaddr/name"), ("`tried`", "per-request tried bitmap"), ("`free`", "request attempt 完成後的 peer free callback"), ("peer state", "local upstream peers 或 shared zone state")],
        ["先包住 round-robin initializer/data，再替換最小 selection。", "Per-request exclusion 與 global health/latency state 不同。", "Free flags 要分類 failure，不是單一 success boolean。", "Shared feedback 需要 slab/lock/reload-compatible layout。"],
    ),
    44: E(
        """
只寫 happy-path assertion 無法重現 async edge cases。Fault injection 將 connect timeout、partial read、client abort 等分支變成可控制輸入，再對 state invariant 驗證。
""",
        r"""
class FaultySocket:
    def __init__(self, actions):
        self.actions = iter(actions)

    def recv(self, size):
        action = next(self.actions)
        if action == "AGAIN":
            raise BlockingIOError()
        if action == "RESET":
            raise ConnectionResetError()
        return action

sock = FaultySocket([b"GET ", "AGAIN", b"/ HTTP/1.1\r\n"])
buffer = bytearray()
for _ in range(3):
    try:
        buffer.extend(sock.recv(1024))
    except BlockingIOError:
        print("state preserved; wait for next event")
print(buffer)
""",
        [("scripted actions", "故障 backend/netcat/tc/timeout 的 deterministic fault injection"), ("exceptions", "EAGAIN/reset/timeout branches"), ("preserved buffer", "跨 callback invariant"), ("test loop", "針對 state transition 的 regression test")],
        ["先定義症狀與 invariant，再選工具。", "Debug log、GDB、strace、perf 各回答不同層。", "測每個 I/O boundary 的 AGAIN、EOF、timeout、error。", "修正後保留能穩定觸發原 bug 的 regression harness。"],
    ),
    45: E(
        """
Patch 若只讓 crash 消失，可能把 reference leak 或 stale state 留到其他 branch。Review 應先寫出 invariant，再用測試證明所有 paths 都維持它。
""",
        r"""
class Request:
    def __init__(self):
        self.finalized = False
        self.cleanup_count = 0

    def finalize(self):
        if self.finalized:          # invariant repair
            return
        self.finalized = True
        self.cleanup_count += 1

def test_finalize_is_idempotent():
    request = Request()
    request.finalize()
    request.finalize()
    assert request.cleanup_count == 1

test_finalize_is_idempotent()
""",
        [("`finalized` invariant", "NGINX 中常由 flags/count/owner state 表達"), ("guard", "bug fix 新增的狀態檢查"), ("test twice", "重入/timeout+I/O race 的 regression scenario"), ("cleanup count", "resource side effect 必須 exactly once")],
        ["先重現舊 code 的 invariant violation，再看 diff。", "找 patch 影響的 success/error/timeout/cleanup paths。", "`git blame/log` 用來找 constraint，不是追究作者。", "小 diff 也要檢查 lifecycle、ABI/config 與 performance side effects。"],
    ),
    46: E(
        """
若 connection layer 直接 `if protocol == HTTP`，加入 TCP stream/mail/new protocol 會讓底層充滿條件。注入 protocol handler 讓 transport 只知道 bytes/events。
""",
        r"""
class Connection:
    def __init__(self, fd, protocol_handler):
        self.fd = fd
        self.protocol_handler = protocol_handler

def http_init(connection):
    print("create HTTP parser for fd", connection.fd)

def stream_init(connection):
    print("create raw TCP proxy state for fd", connection.fd)

def on_accept(fd, handler):
    connection = Connection(fd, handler)
    connection.protocol_handler(connection)

on_accept(10, http_init)
on_accept(11, stream_init)
""",
        [("`on_accept`", "generic `ngx_event_accept`"), ("injected handler", "`ngx_listening_t.handler`"), ("`http_init`", "`ngx_http_init_connection`"), ("`stream_init`", "stream module 的 connection initialization")],
        ["Event core 不應解析 HTTP method/location。", "Generic `c->data` 由 protocol contract 賦予動態型別。", "Transport 提供 read/write/event/timer 機制，上層提供 policy。", "新 protocol 若要求修改 event core，先檢查 extension boundary 是否放錯層。"],
    ),
    47: E(
        """
看到 global、macro 或 C 就直接重寫，容易破壞成熟的 failure behavior。架構評估需要把原始目的、現在痛點、替代方案與 migration risk 放在同一張表。
""",
        r"""
def evaluate(design):
    score = (
        design["throughput_benefit"]
        + design["maintenance_benefit"]
        - design["compatibility_risk"]
        - design["migration_cost"]
        - design["failure_uncertainty"]
    )
    return score

rewrite = {
    "throughput_benefit": 1,
    "maintenance_benefit": 4,
    "compatibility_risk": 5,
    "migration_cost": 5,
    "failure_uncertainty": 4,
}
incremental = {
    "throughput_benefit": 1,
    "maintenance_benefit": 2,
    "compatibility_risk": 1,
    "migration_cost": 1,
    "failure_uncertainty": 1,
}
print(evaluate(rewrite), evaluate(incremental))
""",
        [("benefits", "新 abstraction/語言可能降低的具體成本"), ("compatibility risk", "module ABI、config behavior、protocol edge cases"), ("failure uncertainty", "少見 timeout/reload/cleanup paths 是否被保留"), ("incremental option", "在穩定 contract 內逐步替換 implementation")],
        ["先說清楚現有設計原本解決什麼。", "Technical debt 必須有可觀察 symptom，不只是審美。", "比較 rollout、rollback、operability 與 regression surface。", "找 stable contract 與 accidental implementation 的分界。"],
    ),
    48: E(
        """
把函式名稱背熟無法遷移。對任何陌生系統，都可以用同一組問題抽取 ingress、state owner、wakeup、backpressure、failure 與 cleanup，再以小實驗驗證。
""",
        r"""
def investigate(system):
    questions = [
        "資料從哪裡進來、到哪裡離開？",
        "哪個 object 跨等待保存狀態？",
        "誰在未來喚醒或重新排程它？",
        "queue/buffer 的上限與 backpressure 在哪裡？",
        "timeout、cancel、retry、cleanup 如何交會？",
        "怎麼用 trace 或小修改證明這張圖？",
    ]
    return {
        "system": system,
        "questions": questions,
        "deliverable": "一張 flow、一張 lifetime、一張 failure matrix",
    }

for system in ["Redis", "Node/libuv", "Envoy", "database"]:
    print(investigate(system))
""",
        [("ingress/egress", "accept/read → parse → output 的 golden path"), ("state owner", "cycle/connection/request/upstream 的可遷移概念"), ("wakeup", "epoll callback、completion、actor message 或 async task"), ("failure matrix", "stage × error × ownership × retry semantics")],
        ["不要強迫新系統使用 NGINX 的 thread/process model。", "把 container 名稱改寫成 operation set 與 constraints。", "Mechanism 與 policy 分開比較。", "最後必須做一個安全小修改，才能驗證自己不只理解圖。"],
    ),
}


assert set(EXAMPLES) == set(range(1, 49))
for number, example in EXAMPLES.items():
    compile(example["python"], f"chapter-{number}-example.py", "exec")


# One compact, real source window per chapter.  The builder reads these lines
# from the pinned official release, so the HTML/EPUB contains actual NGINX C
# rather than requiring the reader to follow an external link.
SOURCE_WINDOWS = {
    1: ("src/event/ngx_event_accept.c", 21, 46),
    2: ("src/core/nginx.c", 200, 54),
    3: ("src/http/ngx_http_request.c", 211, 44),
    4: ("src/event/ngx_event.h", 30, 46),
    5: ("src/core/nginx.c", 200, 54),
    6: ("src/core/ngx_conf_file.c", 158, 46),
    7: ("src/core/ngx_cycle.c", 39, 48),
    8: ("src/os/unix/ngx_process_cycle.c", 74, 48),
    9: ("src/os/unix/ngx_process_cycle.c", 233, 45),
    10: ("src/os/unix/ngx_recv.c", 14, 44),
    11: ("src/event/ngx_event_accept.c", 21, 46),
    12: ("src/event/modules/ngx_epoll_module.c", 784, 48),
    13: ("src/event/ngx_event.h", 30, 46),
    14: ("src/event/ngx_event.c", 195, 43),
    15: ("src/event/ngx_event_timer.c", 54, 45),
    16: ("src/event/ngx_event_pipe.c", 104, 45),
    17: ("src/http/ngx_http_request.c", 539, 48),
    18: ("src/http/ngx_http_parse.c", 108, 48),
    19: ("src/http/ngx_http_parse.c", 871, 48),
    20: ("src/http/ngx_http_core_module.c", 1446, 46),
    21: ("src/http/ngx_http_core_module.c", 889, 44),
    22: ("src/http/ngx_http_request_body.c", 32, 48),
    23: ("src/http/ngx_http_core_module.c", 1954, 45),
    24: ("src/http/ngx_http_request.c", 2743, 50),
    25: ("src/http/modules/ngx_http_proxy_module.c", 876, 48),
    26: ("src/http/ngx_http_upstream.c", 1316, 42),
    27: ("src/event/ngx_event_connect.c", 21, 50),
    28: ("src/http/ngx_http_upstream_round_robin.c", 811, 48),
    29: ("src/http/modules/ngx_http_upstream_least_conn_module.c", 100, 48),
    30: ("src/http/ngx_http_upstream.c", 4599, 50),
    31: ("src/http/modules/ngx_http_upstream_keepalive_module.c", 205, 50),
    32: ("src/event/ngx_event_pipe.c", 23, 48),
    33: ("src/http/ngx_http_file_cache.c", 265, 48),
    34: ("src/core/ngx_palloc.c", 123, 46),
    35: ("src/core/ngx_array.c", 48, 46),
    36: ("src/core/ngx_output_chain.c", 42, 48),
    37: ("src/core/ngx_slab.c", 184, 48),
    38: ("src/http/ngx_http.c", 123, 50),
    39: ("src/http/modules/ngx_http_empty_gif_module.c", 92, 48),
    40: ("src/http/modules/ngx_http_access_module.c", 123, 48),
    41: ("src/http/ngx_http_variables.c", 619, 46),
    42: ("src/http/modules/ngx_http_sub_filter_module.c", 285, 50),
    43: ("src/http/modules/ngx_http_upstream_random_module.c", 337, 48),
    44: ("src/core/ngx_log.c", 102, 48),
    45: ("src/http/ngx_http_request.c", 3948, 45),
    46: ("src/http/ngx_http_request.c", 211, 44),
    47: ("src/core/ngx_module.h", 227, 48),
    48: ("src/event/ngx_event.c", 195, 43),
}

assert set(SOURCE_WINDOWS) == set(range(1, 49))
