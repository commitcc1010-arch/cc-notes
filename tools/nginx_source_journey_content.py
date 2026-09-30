"""Curriculum and chapter content for the NGINX source-code journey.

The prose deliberately explains an executable mental model first and names the
real NGINX structures/functions second.  Every chapter is source-pinned,
contains an experiment, and ends with six or more comprehension checks.
"""
from __future__ import annotations


def C(
    number,
    title,
    question,
    level,
    promise,
    concepts,
    sources,
    diagram,
    mental_model,
    trace,
    deep_dive,
    code,
    lab,
    pitfalls,
    transfer,
    qa,
    code_lang="c",
):
    assert len(qa) >= 6, f"chapter {number} needs at least six Q&A"
    assert len(trace) >= 3 and len(lab) >= 3
    return {
        "number": number,
        "title": title,
        "question": question,
        "level": level,
        "promise": promise,
        "concepts": concepts,
        "sources": sources,
        "diagram": diagram,
        "mental_model": mental_model,
        "trace": trace,
        "deep_dive": deep_dive,
        "code": code,
        "code_lang": code_lang,
        "lab": lab,
        "pitfalls": pitfalls,
        "transfer": transfer,
        "qa": qa,
    }


PART_1 = [
    C(
        1,
        "一個請求究竟經過了什麼？",
        "在瀏覽器按下 Enter 後，NGINX 到底做了哪些事，才把請求交給另一台伺服器？",
        "入門",
        "先建立一條可以反覆回到的黃金路徑；後面每一章只是把其中一個方塊放大。",
        ["reverse proxy", "request path", "control flow"],
        [
            "src/event/ngx_event_accept.c:21",
            "src/http/ngx_http_request.c:211",
            "src/http/ngx_http_upstream.c:543",
        ],
        r"""
Client
  │  GET /api
  ▼
[listen socket] ──accept──> [client connection]
                                │ readable event
                                ▼
                         [HTTP parser]
                                │ request object
                                ▼
                   [location + phase engine]
                                │ proxy_pass
                                ▼
                      [upstream selector]
                                │ backend connection
                                ▼
Backend  <──────── request ─────┘
Backend  ──────── response ────> filters ───> Client
""",
        """
先把 NGINX 想成一個交通轉運站，而不是「會執行網站程式的框架」。它長時間持有許多 socket；核心工作是等待哪一條 socket 現在可以讀或可以寫，然後只推進那條連線的下一小步。

一個 TCP connection 可以承載多個 HTTP request。connection 是運輸通道，request 是一次語意操作。NGINX 接受連線後先建立 connection 與 read/write event；讀到 request line 和 headers 後才建立完整 HTTP request 語境。若 location 選中了 `proxy_pass`，HTTP proxy module 建立 upstream 物件，選 backend、非阻塞連線、送出請求、解析回應，再讓 filter chain 把資料送回 client。

這條路徑不是一次函式呼叫到底。遇到 socket 暫時不可讀或不可寫時，函式返回，控制權回到 event loop；下一個 readiness event 到來才繼續。因此真正的主角是「物件保存的狀態＋下一個 callback」，不是很深的同步 call stack。
""",
        [
            "`ngx_event_accept()` 接受 client socket，取得一個 `ngx_connection_t`，建立 connection pool。",
            "listening socket 的 protocol handler 把新 connection 交給 `ngx_http_init_connection()`。",
            "read event handler 先等待資料，再逐步解析 request line 與 headers。",
            "`ngx_http_core_run_phases()` 執行 rewrite、access、content 等階段。",
            "proxy content handler 建立 `ngx_http_upstream_t`，選 peer 並建立 backend connection。",
            "response 經 header/body filters 與 write filter 回到 client，最後 finalize request。",
        ],
        """
最容易犯的錯是把整條流程畫成同步函式鏈。實際上，client read、upstream connect、upstream write、upstream read、client write 都可能各自停在 `NGX_AGAIN`。每一次停下來，都會把「下次該做什麼」放進 event handler 或 request/upstream 欄位。

第二個關鍵是分清三種生命週期：cycle 對應一代設定與 worker 世界；connection 對應一條 transport；request 對應一次 HTTP 交換。後面的 memory pool、reload、keep-alive 和 subrequest，全部依賴這個分層。

讀任何函式時固定問四題：現在處理哪個物件？物件處於哪個狀態？這次最多推進到哪裡？若資源尚未 ready，誰會在未來重新叫醒它？這四題比背 call graph 更可靠。
""",
        r"""
for (;;) {
    ready_events = wait_for_io_and_timers();

    for (event in ready_events) {
        event->handler(event);   /* 只推進這條工作流的一小步 */
    }
}

client readable
    -> parse request
    -> choose content handler
    -> connect upstream
    -> wait for writable
    -> send request
    -> wait for readable
    -> forward response
""",
        [
            "準備兩個回傳不同文字的 backend，例如 9001 回 `A`、9002 回 `B`。",
            "設定一個 `upstream` 與 `proxy_pass`，連續呼叫十次，記錄回應落在哪個 backend。",
            "開啟 debug log，搜尋 `accept`、`http process request line`、`get rr peer` 與 `finalize request`，手動畫出一次請求。",
            "刻意讓其中一個 backend 延遲兩秒，觀察其他連線是否仍能前進。",
        ],
        [
            "把 reverse proxy 誤認為 HTTP redirect；redirect 是 client 重新發請求，proxy 對 client 隱藏 backend。",
            "把 connection 與 request 當成同一物件，因而無法解釋 keep-alive。",
            "認為一次 request 會由一個長 call stack 執行到底，忽略 event callback 的斷點。",
        ],
        [
            "把複雜系統拆成資料流、控制流與生命週期三張圖。",
            "理解 event-driven server、GUI loop、Node.js 與網路框架的共同模型。",
            "面對陌生 codebase 時，先找一條 user-visible path，而不是先讀所有 utility。",
        ],
        [
            ("Reverse proxy 與 redirect 最大差異是什麼？", "Redirect 回 3xx 與新網址，後續連線由 client 建立；reverse proxy 自己連 backend，client 通常只看見 NGINX。這使 proxy 能做負載均衡、重試、快取與協定轉換。"),
            ("為什麼 connection 不能等同 request？", "HTTP keep-alive 允許同一條 TCP connection 依序承載多個 request；HTTP/2 更能並行多個 stream。若生命週期綁死，就不能安全重用連線或分離 transport 與 protocol。"),
            ("哪個物件同時連起 client 與 backend？", "`ngx_http_request_t` 持有 `r->connection` 指向 client connection，也可持有 `r->upstream`；後者再管理 peer connection。request 是這次代理交易的協調者。"),
            ("如果 upstream connect 尚未完成，worker 會等待在 `connect()` 嗎？", "不會。non-blocking `connect()` 通常表示進行中，NGINX 為 backend write event 安裝 handler 與 timeout，返回 event loop；可寫事件出現後再檢查連線結果。"),
            ("為什麼先讀黃金路徑比先讀所有資料結構有效？", "每個結構都有使用場景。先知道 timer、request、peer 在路徑中的責任，再學紅黑樹或 pool，知識會和真實約束綁在一起，也知道哪些欄位值得追。"),
            ("如何判斷自己真的理解了這一章？", "不用看書，從 client 開始畫到 backend 再回 client，並在每個 I/O 邊界標出可能返回 `NGX_AGAIN` 的位置；還要能指出 cycle、connection、request 三種生命週期。"),
        ],
    ),
    C(
        2,
        "建立可觀察的 NGINX 實驗室",
        "讀源碼前需要哪些工具，才能把猜測轉成可重複驗證的證據？",
        "入門",
        "建立固定版本、debug build、最小設定與觀察工具；後面所有推論都能在這個環境重現。",
        ["debug build", "logs", "strace", "gdb"],
        ["auto/configure:1", "src/core/nginx.c:200", "src/core/ngx_log.c:1"],
        r"""
source ──configure──> Makefile ──make──> objs/nginx
   │                                      │
   ├── static reading: rg / ctags         ├── debug log
   ├── control flow: GDB                  ├── strace
   └── history: git blame/log             └── curl / load generator

猜測 ──> 設計小實驗 ──> 收集 log/syscall ──> 修正心智模型
""",
        """
源碼閱讀最危險的狀態不是「看不懂」，而是覺得自己看懂卻沒有驗證。實驗室的目的不是建 production NGINX，而是讓每個問題都能用最小設定、單一 worker、清楚 log 與可控制 backend 重現。

固定 tag 與 commit 很重要。函式名稱通常穩定，但行號、欄位與模組會變；本書使用 `release-1.31.5` 的 commit `231a60ee…`。設定 `worker_processes 1` 可先消除跨 worker 干擾，等理解單 worker 後再打開競爭場景。

四種工具回答不同問題：`rg` 回答「符號在哪裡」；debug log 回答「這次真的走哪條路」；strace 回答「使用者空間最後呼叫了哪些 syscall」；GDB 回答「此刻資料結構內容與 call stack 是什麼」。不要拿一種工具解所有問題。
""",
        [
            "`auto/configure` 探測 OS 能力並產生 `objs/ngx_auto_config.h`、`objs/Makefile` 等 build artifacts。",
            "`--with-debug` 讓 `NGX_DEBUG` 區塊與 debug log 可用；設定檔仍需把 `error_log` level 設為 `debug`。",
            "`nginx -t` 只驗證設定；`-T` 還會輸出 include 後的完整設定，是排查設定來源的重要工具。",
            "用前景模式與獨立 prefix 運行，避免干擾系統既有 NGINX。",
        ],
        """
建議使用獨立 prefix，例如 `/tmp/nginx-lab`，讓 config、logs、pid、temporary files 都在可丟棄目錄。編譯時保留 debug symbol 並關閉過度最佳化，GDB 才容易對應源碼。

觀察時先建立事件時間線：client 發出請求、accept、read、parse、upstream connect、write、read、client write。debug log 很細，不應從頭讀到尾；用 connection number、request URI 與關鍵函式訊息縮小範圍。

`strace -ff` 要跟隨 fork 出來的 worker；`-e trace=network,epoll_wait,read,write` 可降低雜訊。GDB 則可以在 `ngx_event_accept`、`ngx_http_process_request_line`、`ngx_http_upstream_connect` 下 conditional breakpoint。
""",
        r"""
./auto/configure \
  --prefix=/tmp/nginx-lab \
  --with-debug \
  --with-cc-opt='-O0 -g3'
make -j4

./objs/nginx -p /tmp/nginx-lab -c conf/nginx.conf -t
./objs/nginx -p /tmp/nginx-lab -c conf/nginx.conf

strace -ff -p WORKER_PID \
  -e trace=network,epoll_wait,read,write,writev,sendfile
""",
        [
            "以固定 tag 編譯，保存 `nginx -V` 輸出，確認 configure arguments。",
            "設定單 worker、非 daemon、debug error log，發出一次帶唯一 header 的 curl。",
            "用 `rg 'http process request line' src` 找 log 來源，再把 runtime log 對回源碼。",
            "用 strace 驗證 `epoll_wait`、`accept4`、`recvfrom`、`writev/sendfile` 的實際順序。",
        ],
        [
            "只開 `--with-debug` 卻未把 `error_log` 設為 debug，結果看不到細節。",
            "在有多個 worker 時直接讀混合 log，誤把兩條請求拼成同一條。",
            "用 debugger 單步每一行，破壞 timing 且迷失在 utility；應在狀態轉換點設 breakpoint。",
        ],
        [
            "建立可重現的 debugging harness。",
            "分辨 source-level、process-level、syscall-level 三種證據。",
            "用最小實驗控制變因，而不是在完整 production config 猜測。",
        ],
        [
            ("`--with-debug` 與 `error_log ... debug` 各做什麼？", "前者在編譯期保留 debug instrumentation；後者在執行期允許輸出 debug level。只做其中一個都可能看不到預期訊息。"),
            ("為何初學時建議 `worker_processes 1`？", "它讓一條 log timeline 不受多程序交錯與 accept 分配影響。理解完成後必須再用多 worker 驗證 shared memory、accept 與 reload。"),
            ("`rg` 和 GDB 應如何搭配？", "先用 `rg` 找定義、呼叫點與 log 字串，再在少數狀態轉換函式設 breakpoint。直接從 `main` 單步通常成本極高。"),
            ("strace 能證明 phase engine 執行了哪個 handler 嗎？", "不能直接證明；它看 syscall 邊界，不知道 C 函式語意。phase handler 需靠 debug log、breakpoint 或 instrumentation，syscall 則用 strace 交叉驗證。"),
            ("為何要保存 `nginx -V`？", "相同版本因 configure feature、編譯器與 library 不同，實際包含的模組和條件編譯路徑會不同。`-V` 是實驗可重現性的 build manifest。"),
            ("怎麼避免自己加的 log 造成錯誤結論？", "只在狀態轉換點記錄 connection number、event flags、handler 名稱與 return code；避免大量同步 I/O，並用原生 debug log 或 debugger 再驗證一次。"),
        ],
        code_lang="bash",
    ),
    C(
        3,
        "如何閱讀一個陌生的 C 專案",
        "面對數十萬行 C code，怎麼決定現在該讀什麼、可以先不讀什麼？",
        "入門",
        "學會用問題、邊界、物件與狀態建立 source map，而不是從檔案清單開始背。",
        ["source map", "call graph", "data flow"],
        ["src/core/nginx.c:200", "src/core/ngx_connection.h:127", "src/event/ngx_event.h:30"],
        r"""
問題：「/api 怎麼到 backend？」
  │
  ├─ 邊界：client socket / upstream socket
  ├─ 物件：connection / request / upstream
  ├─ 狀態：waiting / parsing / connecting / forwarding
  └─ callback：下一次 ready 時執行誰？

只展開與問題相交的節點；其餘先折疊。
""",
        """
大型 C 專案沒有 class hierarchy 幫你導航，真正的架構散落在 struct、function pointer、module table、macro 與初始化順序裡。有效的讀法是先找「資料進來的邊界」和「可見結果出去的邊界」，再找中間承載狀態的物件。

每次閱讀維護兩張小表。第一張是 object card：誰建立、誰持有、何時銷毀、重要狀態欄位。第二張是 callback card：誰把 handler 設成誰、什麼事件觸發、handler 可能返回什麼、返回後狀態留在哪裡。

Call graph 只表示可能呼叫，不能表示 runtime 一定走過。Function pointer、條件編譯、模組註冊與 event callback 都會讓靜態圖不完整；所以源碼搜尋必須和一次真實 trace 配對。
""",
        [
            "從 user-visible 行為選一條 slice，例如 reverse proxy，而不是先讀 `src/core` 全部。",
            "找入口與出口：accept/read 是輸入邊界，upstream connect/send 是另一側邊界。",
            "列出跨 callback 存活的 struct；區域變數不會跨 event，物件欄位才是狀態。",
            "搜尋 handler 被賦值的位置，比只搜尋 handler 被呼叫的位置更能理解狀態機。",
            "遇到 helper 先讀 contract、return code 與 side effect；只有阻塞理解時才進入實作。",
        ],
        """
對 NGINX 特別有用的搜尋模式包括：搜尋 `handler =` 找 callback 切換；搜尋 `NGX_AGAIN` 找可暫停邊界；搜尋 `ngx_pcalloc(r->pool` 找 request-lifetime state；搜尋 module symbol 找 command table 與 lifecycle hooks。

不要把每個 macro 都展開。先把 macro 分為四類：型別/常數、平台抽象、container 取回、module/config 取回。知道它在做哪類工作，通常足以繼續主線。

讀懂的驗收不是「我看過這個函式」，而是能預測改變一個條件後控制流在哪裡分叉。例如 client 分兩次送 header、backend connect 超時、response 比 proxy buffer 大，下一個 callback 與 timer 會如何改變。
""",
        r"""
/* Object card */
object: ngx_http_request_t
created_by: ngx_http_create_request()
owned_until: ngx_http_free_request()
state: phase_handler, read_event_handler, write_event_handler
links: connection, upstream, pool

/* Callback card */
event: upstream socket writable
installed_at: ngx_http_upstream_connect()
entry: ngx_http_upstream_handler()
dispatches_to: u->write_event_handler(r, u)
""",
        [
            "選 `ngx_http_process_request_line`，找它的定義、誰把 read handler 指向它、它把 handler 改成什麼。",
            "為 `ngx_http_request_t` 製作 object card，只記十個最能解釋主線的欄位。",
            "找出 upstream read/write event 共用入口以及第二層 dispatch 欄位。",
            "預測 backend 延遲回 header 時 request 保存在哪裡，再用 GDB 驗證。",
        ],
        [
            "把『讀過很多檔案』當成進度，卻無法描述一條完整行為。",
            "只畫函式呼叫、不畫 handler 賦值與物件生命週期。",
            "看到 utility 就向下鑽到底，忘記原始問題。",
        ],
        [
            "在任何 callback-heavy codebase 找到實際狀態機。",
            "使用 object ownership 分析 memory leak 與 use-after-free。",
            "把 source reading 轉成可證偽的預測。",
        ],
        [
            ("為什麼搜尋 `handler =` 很重要？", "event-driven control flow 的下一跳常透過 function pointer 保存。只看 `handler(ev)` 的共同入口看不出真正狀態；賦值點才說明何時切換階段。"),
            ("Object card 最少要記哪些內容？", "建立者、擁有者、銷毀點、生命週期、重要狀態、對其他物件的指標。這些足以回答 ownership 與跨 callback 狀態問題。"),
            ("靜態 call graph 為何不等於 runtime trace？", "條件分支、function pointer、模組註冊、平台編譯選項和資料狀態都會改變實際路徑。Call graph 是可能集合，trace 是一次具體執行。"),
            ("遇到不懂的 macro，何時必須展開？", "當它影響 ownership、控制流、型別安全或副作用時必須展開；若只是取得 module config 或平台名稱封裝，可先理解 contract。"),
            ("如何防止閱讀範圍無限擴張？", "每次 session 寫一個可回答的問題和停止條件，例如『能說明 connect 未完成後誰重新喚醒』；答案完成就先停，把新問題放 backlog。"),
            ("什麼證據表示你已讀懂某段非同步流程？", "你能指出每個 suspend point、保存狀態的欄位、重新進入的 handler，以及 timeout/close 時的清理路徑，並能用一次 trace 驗證。"),
        ],
        code_lang="text",
    ),
    C(
        4,
        "讀 NGINX 所需的最小 C 語言",
        "不先學完整 C，最少要懂哪些語法與記憶體概念才能沿主線前進？",
        "入門",
        "讀懂 pointer、struct、function pointer、macro、intrusive container 與 NGINX return-code 慣例。",
        ["pointer", "function pointer", "intrusive structure"],
        ["src/core/ngx_core.h:1", "src/core/ngx_string.h:1", "src/core/ngx_queue.h:1"],
        r"""
ngx_event_t *ev
      │ ev->data
      ▼
ngx_connection_t *c
      │ c->data
      ▼
protocol state (ngx_http_request_t / ngx_http_connection_t)

function pointer:
ev->handler ───────────────> ngx_http_process_request_line(ev)
""",
        """
C pointer 不是神祕地址，而是「到另一個物件的連結」。讀主線時優先理解指標關係，不必先做位元運算題。`ev->data` 常指回 connection，`c->data` 則依階段指向 HTTP connection 或 request；這種 generic pointer 讓底層 event layer 不需要知道上層協定型別。

`ngx_str_t` 是 length＋data，而不是以 `\\0` 結尾為核心的字串。這使 substring 可以只引用既有 buffer，但也表示不能隨便交給期待 C string 的 API。`ngx_array_t`、`ngx_list_t`、`ngx_queue_t` 也各自反映 workload，而不是 STL 式統一容器。

Function pointer 是 NGINX 模組化與狀態機的骨架。讀到 `rev->handler(rev)` 時不要問「handler 是哪個函式」一次就結束；要往前找當前階段最後一次賦值。
""",
        [
            "`ngx_core.h` 聚合核心型別與平台抽象；先認得 typedef，不必展開所有 include。",
            "`ngx_str_t`、buffer 的 `pos/last/start/end` 都是 pointer range，區間通常採半開 `[pos,last)`。",
            "`ngx_queue_data()` 類 macro 用 embedded link 的位址反推出外層 struct，形成 intrusive container。",
            "`NGX_OK/ERROR/AGAIN/DONE/DECLINED` 是控制協定；相同值在不同 API 的精確 contract 仍需看 caller。",
        ],
        """
Intrusive data structure 把 link node 直接放在業務 struct 內，免去額外 wrapper allocation，也讓同一物件可嵌入多個不同 queue/tree。代價是 container macro、ownership 與 removal discipline 更難。

`ngx_pcalloc(pool, sizeof(T))` 同時配置與清零，常讓零值代表預設狀態；若新增欄位卻不是零值安全，就必須顯式初始化。理解這點可以解釋大量「為什麼沒有逐欄位初始化」。

Macro 不提供型別檢查與單步體驗。讀 macro 時先人工代入一次，確認參數是否被多次求值、是否做 pointer arithmetic、是否只是一個 cast；之後把它當具名概念。
""",
        r"""
typedef void (*event_handler_pt)(ngx_event_t *ev);

struct ngx_event_s {
    void             *data;       /* 通常指向 connection */
    event_handler_pt  handler;    /* 下一次事件的工作 */
    unsigned          ready:1;
    unsigned          timedout:1;
};

typedef struct {
    size_t  len;
    u_char *data;                  /* 不保證 data[len] == '\0' */
} ngx_str_t;
""",
        [
            "畫出 `ngx_event_t → ngx_connection_t → ngx_http_request_t` 的 cast 與指標方向。",
            "找一處 `ngx_queue_data`，手動用 `offsetof` 推導外層物件地址。",
            "找三個返回 `NGX_AGAIN` 的 API，比較 caller 下一步是否完全相同。",
            "用小 C 程式建立 length-prefixed string，故意傳給 `%s`，理解其風險。",
        ],
        [
            "把 `ngx_str_t.data` 當成永遠以 NUL 結尾。",
            "看到 `void *` 就假設固定型別，忽略它可能隨 connection 階段改變。",
            "只背 return code 名稱，不讀每個 API 的 ownership 與 side effect contract。",
        ],
        [
            "掌握半開區間、pointer range 與零拷貝 slice。",
            "理解 callback、plugin interface 和手寫多型。",
            "理解 intrusive list/tree 對 allocation、cache locality 與複雜度的影響。",
        ],
        [
            ("`ngx_str_t` 為什麼要保存 length？", "可包含 NUL、可引用非終止 substring，也不必每次掃描找結尾。代價是與傳統 C string API 互動時必須顯式控制長度。"),
            ("`ev->data` 為什麼使用 `void *`？", "event core 需要承載不同協定與事件來源，不能依賴 HTTP 型別。上層在建立 event 時約定 data 指向什麼，handler 負責按該約定 cast。"),
            ("Intrusive queue 和一般 linked-list node wrapper 差在哪裡？", "Link 嵌在業務物件內，不需額外配置與間接層；透過 offset 由 link 找回容器。它快且可控，但錯誤移除或生命週期更危險。"),
            ("`ngx_pcalloc` 為什麼常減少初始化程式碼？", "它把記憶體清零，而 NGINX 設計許多 flag、pointer、counter 的零值為安全預設。這是資料表示的設計選擇，不代表所有型別都可依賴零值。"),
            ("Function pointer 如何實作狀態機？", "同一 event 保持不變，但在不同階段把 `handler` 改指等待 request、解析 header、處理 keepalive 等函式；下次 readiness 自然進入正確狀態。"),
            ("遇到很長 macro 應如何閱讀？", "先找輸入輸出與副作用，手動展開一個實例，標出 cast 和 pointer arithmetic；理解 contract 後再折疊，不必每次重新展開。"),
        ],
    ),
]


PART_2 = [
    C(
        5,
        "從 main() 到可服務的程序",
        "NGINX 啟動時做了什麼，為什麼 `main()` 本身沒有處理任何 HTTP request？",
        "初階",
        "看懂啟動分成 bootstrap、建立 cycle、選擇 process mode 三段，並理解初始化順序是架構的一部分。",
        ["bootstrap", "initialization order", "process mode"],
        ["src/core/nginx.c:200", "src/os/unix/ngx_posix_init.c:35", "src/core/ngx_module.c:1"],
        r"""
main()
  ├─ parse options / init time / log
  ├─ init bootstrap pool + init_cycle
  ├─ OS capabilities / modules
  ├─ ngx_init_cycle(init_cycle)
  │      └─ parse config + open resources
  └─ single_process_cycle()
         or master_process_cycle()

HTTP request 尚未出現；這裡是在建立「可以處理 request 的世界」。
""",
        """
`main()` 的責任是把 process 從普通 UNIX 程式轉成 NGINX runtime。它先建立一個很小的 `init_cycle`，只放足以解析完整設定的資源；真正設定、模組 context、listening sockets 與 shared memory 由 `ngx_init_cycle()` 建立。

初始化順序帶有依賴。例如 OS 初始化取得 page size 與 cache line size，之後 slab 與 CRC table 才能正確初始化。這類順序不是風格問題，而是隱含 dependency graph；讀啟動碼時應把「A 必須在 B 前」寫出原因。

完成 cycle 後，`main()` 不進 HTTP loop，而是選 single 或 master process cycle。HTTP 只是註冊在 listening socket 與 event layer 上的協定模組之一。
""",
        [
            "`ngx_get_options()` 處理 `-t/-T/-s/-p/-c/-g` 等啟動模式。",
            "建立 bootstrap pool 與 `init_cycle`，初始化 log、argv、prefix。",
            "`ngx_os_init()` 探測頁面大小、CPU、socket 能力等平台資訊。",
            "`ngx_preinit_modules()` 先安排 module index；`ngx_init_cycle()` 再建立 module conf。",
            "設定測試或 signal command 可提前返回；正常服務才進 process cycle。",
        ],
        """
注意 `nginx -s reload` 並不是在這個新程序裡重建所有 worker。這個 command 讀 pid file，向既有 master 發 signal，然後退出；真正 reload 發生在 master process cycle。

`init_cycle` 和正式 cycle 的雙階段設計是 bootstrap pattern：解析完整世界前先建立最小世界。Compiler、database 與 dependency injection container 也常有類似階段。

條件編譯會讓不同 build 的 main 路徑不同，例如 SSL、PCRE、control API。讀源碼必須搭配 `nginx -V`，否則可能研究一條二進位根本沒有的分支。
""",
        r"""
int main(int argc, char **argv) {
    parse_options(argc, argv);
    init_time_log_os();

    cycle_t bootstrap = make_minimal_cycle();
    preinit_modules();

    cycle_t *cycle = init_cycle(&bootstrap);
    if (test_config_only) return report(cycle);
    if (signal_command)   return signal_master(cycle);

    return cycle->master ? master_loop(cycle)
                         : single_loop(cycle);
}
""",
        [
            "在 `main()` 每個早退點旁寫出對應 CLI 情境。",
            "執行 `nginx -t`、`-T`、`-s reload`，用 strace 比較是否建立 listening socket 或 fork。",
            "從 `ngx_os_init` 找出 page size，追到哪個 allocator 使用它。",
            "比較含與不含 `--with-debug` 的 `nginx -V` 和 binary size。",
        ],
        [
            "認為 `nginx -s reload` 的程序就是 master；它通常只是 signal sender。",
            "忽略 configure flags，閱讀不存在於目前 binary 的路徑。",
            "把初始化順序當成任意排列，未辨認隱含依賴。",
        ],
        [
            "理解 bootstrap initialization 與 dependency ordering。",
            "讀懂 feature flags／conditional compilation 對產品行為的影響。",
            "把 CLI mode、control plane 與 data plane 分開。",
        ],
        [
            ("為什麼需要 `init_cycle`？", "完整 cycle 的建立需要 pool、log、prefix 與 argv 等資源，但這些又不能依賴尚未解析的完整設定。最小 bootstrap cycle 打破循環依賴。"),
            ("`main()` 為何幾乎不包含 HTTP 邏輯？", "Core 只建立通用 runtime、process 與 event infrastructure；HTTP module 透過 module hooks 與 listening handler 接入，維持層次分離。"),
            ("`nginx -t` 會完全不碰外部資源嗎？", "不是。它需要解析設定並驗證許多檔案、socket 或憑證相關條件；但完成測試後不會進入長期 worker serving loop。精確行為應以 trace 驗證。"),
            ("初始化順序 bug 通常怎麼發生？", "某 component 假設 global capability、page size、module index 或 log 已就緒。重構順序卻未把依賴顯式化，便會出現未初始化值或錯誤 allocation。"),
            ("如何知道目前 binary 有哪些條件分支？", "看 `nginx -V` configure arguments、產生的 `objs/ngx_auto_config.h` 與 module list，再對照 `#if`。"),
            ("Control plane 與 data plane 在這裡怎麼區分？", "解析設定、signal/reload、管理 worker 屬 control plane；worker 接受連線、解析與代理 request 屬 data plane。啟動流程建立兩者的邊界。"),
        ],
    ),
    C(
        6,
        "設定檔其實是一套小型語言",
        "一行 `proxy_pass http://backend;` 如何找到正確模組、欄位與設定 callback？",
        "中階",
        "拆開 lexer、directive dispatch、context 驗證、create/merge config，理解 declarative config 背後的 interpreter。",
        ["parser", "dispatch table", "configuration merge"],
        ["src/core/ngx_conf_file.c:1", "src/http/ngx_http.c:1", "src/http/modules/ngx_http_proxy_module.c:1"],
        r"""
nginx.conf bytes
   ↓ tokenizer
[proxy_pass] [http://backend] [;]
   ↓ search ngx_command_t tables
module + directive match
   ↓ validate context/arity
cmd->set(cf, cmd, module_conf)
   ↓
location configuration object
   ↓ merge parent defaults
runtime read-only config
""",
        """
NGINX 設定不是逐行 if/else。每個 module 提供 `ngx_command_t` table，描述 directive 名稱、允許 context、參數數量、set callback，以及值應寫入哪類 config。Core parser 只負責 token、block 與通用 dispatch，不需要知道 `proxy_pass` 的語意。

HTTP module 通常有 main/server/location 三層 configuration。Parse 開始前，各 module 的 `create_*_conf` 先產生物件；block 結束後，`merge_*_conf` 把 parent 值、child 值與 default 合成 runtime config。這是 hierarchical configuration，不是簡單 inheritance。

大量 runtime 效能來自 config-time 預計算：編譯 regex、建立 hash、排序 location、解析 complex value script。Worker 處理每個 request 時直接讀已整理好的結構。
""",
        [
            "`ngx_conf_read_token()` 產生 token，處理引號、escape、`;` 與 `{}`。",
            "`ngx_conf_handler()` 遍歷當前 modules 的 command table，匹配名稱。",
            "command type bitmask 驗證 directive 能否出現在 main/http/server/location 等 context。",
            "`cmd->set` 可能是通用 setter，也可能是模組自訂 parser。",
            "HTTP block 建立每模組 main/srv/loc conf arrays，之後初始化與 merge。",
        ],
        """
`NGX_CONF_UNSET`、`NGX_CONF_UNSET_UINT` 等 sentinel 很重要：零可能是合法設定，不能用零同時代表「使用者沒寫」。Merge 通常遵循 child explicit > parent > default，但每個 directive 仍可定義特殊語意。

Module config lookup macro 看似魔法，本質是 module 的 `ctx_index` 當 array index。這讓 request-time 取得 config 近似 O(1)，代價是初始化期間必須一致安排 index。

錯誤訊息品質也是 parser 設計的一部分。好的 directive callback 應區分 invalid number、duplicate、unsupported context 與 resource failure，並附 file/line。
""",
        r"""
typedef struct {
    string       name;
    unsigned     allowed_contexts;
    set_fn       set;
    unsigned     conf_slot;
    unsigned     field_offset;
} command_t;

for (command in all_loaded_modules) {
    if (command.name == token[0] && context_is_valid(command)) {
        conf = current_context[module.ctx_index][command.conf_slot];
        return command.set(parser, &command, conf);
    }
}
""",
        [
            "找 `proxy_pass` 的 command table entry，記下 type、set callback 與 loc conf。",
            "建立 parent/child location，分別設定 `proxy_read_timeout`，用 `nginx -T` 推理 merge 結果。",
            "新增一行參數數量錯誤的 directive，沿錯誤路徑找出 file/line 來源。",
            "找一個使用通用 slot setter 與一個自訂 setter 的 directive，比較差異。",
        ],
        [
            "以為所有未設定值都是零，忽略 UNSET sentinel。",
            "把 merge 當一般物件導向繼承；實際上每個 module 自訂合成規則。",
            "在 request path 重做 config-time 可完成的 parse 或 lookup。",
        ],
        [
            "理解 table-driven parser 與 interpreter dispatch。",
            "設計 hierarchical config、default 與 explicit-value precedence。",
            "把昂貴工作移到初始化階段，縮短 hot path。",
        ],
        [
            ("NGINX core 如何在不知道 `proxy_pass` 的情況下解析它？", "Proxy module 在 command table 註冊名稱、context 與 callback；core 做通用 tokenization 和 table lookup，找到後把控制交給 module。"),
            ("為什麼需要 UNSET 而不能只用零？", "零可能表示合法值，例如停用某上限。若零也表示未設定，merge 無法分辨 child 明確寫零還是應繼承 parent。"),
            ("`ctx_index` 的價值是什麼？", "將 module-specific config 放進 array，runtime 以 index 直接取得，避免每個 request 做名稱查找或型別遍歷。"),
            ("哪些工作適合 config-time 預計算？", "不依 request 變動且可能昂貴的工作，如 regex compile、location tree/hash 建立、固定 upstream 解析與 script compile。"),
            ("如果 reload 新設定失敗，舊 worker 為何還能服務？", "新 cycle 在獨立 pool 與 config context 中建立；失敗可丟棄新 cycle，舊 cycle 與既有 worker 的資料不必被部分修改。"),
            ("這套模式可遷移到哪裡？", "Compiler pass table、CLI subcommand、serialization schema、plugin registry 與 dependency injection container 都可使用 metadata＋callback dispatch。"),
        ],
    ),
    C(
        7,
        "ngx_cycle_t：一代設定的完整世界",
        "為什麼 NGINX 不直接修改全域設定，而是每次建立新的 cycle？",
        "中階",
        "把 cycle 理解為一個 configuration generation，掌握 reload、資源擁有權與新舊世界並存。",
        ["generation", "resource ownership", "transactional reload"],
        ["src/core/ngx_cycle.h:39", "src/core/ngx_cycle.c:39", "src/core/ngx_connection.c:1"],
        r"""
old cycle (generation N)             new cycle (generation N+1)
├─ old config                         ├─ parsed config
├─ old listening ───── reuse ───────> ├─ listening
├─ old shared memory ─ compatible ──> ├─ shared memory
└─ old workers continue               └─ new workers start

成功：切換 global current cycle
失敗：丟棄 new pool，old cycle 不受污染
""",
        """
`ngx_cycle_t` 不只是設定物件。它聚合這一代 runtime 使用的 module conf、listening sockets、open files、shared memory zones、connection/event arrays、paths、log 與 pool。將它視為「generation root」比視為 config struct 更準確。

Reload 的核心不是修改舊 cycle，而是以舊 cycle 為輸入建立新 cycle。建立過程可比較 listening address、shared memory zone name/size 與 open files，決定重用、開新或延後關閉。只有全部成功才啟動新 worker。

這近似 transaction：prepare 新狀態、驗證、commit 切換；失敗則 rollback by discard。它不是完整資料庫 transaction，但 isolation 思路相同。
""",
        [
            "`ngx_init_cycle(old_cycle)` 先建立全新 cycle pool 與 zeroed cycle。",
            "複製 prefix、config path 等 bootstrap 資訊，建立各種 container。",
            "建立 modules 與 core conf，解析完整設定。",
            "初始化 modules、shared memory、listening sockets、open files。",
            "成功後 global `ngx_cycle` 指向新 generation；舊 cycle 延後清理。",
        ],
        """
Cycle pool 使失敗清理簡單：尚未發布的新 generation 可以整池銷毀。但 OS resources 仍需精確處理，因為 socket、file、shared memory 不是普通 heap bytes；所以 init code 有大量 error path 與 cleanup bookkeeping。

Listening socket 的重用是 graceful reload 的關鍵。若 address/options 相容，新 worker 可繼承既有 fd，避免先 close 再 bind 的空窗。舊 worker 停止 accept 後仍能完成手上連線。

Shared memory zone 需要更嚴格 compatibility。若名稱相同但 size 或 tag 不相容，不能把舊 memory 當新 layout 使用；這是 persistent state schema evolution 的縮影。
""",
        r"""
cycle_t *reload(cycle_t *old) {
    cycle_t *next = alloc_generation();

    if (!parse_config(next)
        || !prepare_shared_memory(next, old)
        || !prepare_listeners(next, old)
        || !init_modules(next)) {
        destroy_generation(next);
        return NULL;                 /* old 仍有效 */
    }

    publish(next);
    retire_later(old);
    return next;
}
""",
        [
            "列出 `ngx_cycle_t` 中屬於設定、OS resource、runtime array 的欄位。",
            "對同一 listen address reload，使用 `ls -l /proc/PID/fd` 觀察 fd 是否跨 worker 繼承。",
            "故意把新設定寫成語法錯誤，確認舊 worker 與舊 cycle 仍服務。",
            "修改 shared memory zone size，觀察設定驗證與 reload 行為。",
        ],
        [
            "把 cycle 當 immutable 純設定；它也擁有大量 runtime resource。",
            "認為 pool destroy 能自動處理所有 fd 與 shared memory。",
            "直接原地修改共享結構，破壞 reload 失敗時的回退能力。",
        ],
        [
            "理解 immutable generation、copy-on-reconfigure 與 transactional publish。",
            "設計資源 root 與明確 ownership tree。",
            "理解 schema compatibility、rolling upgrade 與 RCU 類思想。",
        ],
        [
            ("Cycle 為什麼適合當 generation root？", "所有由同一設定推導的 module conf、listener、shared zone 與 runtime arrays 可掛在同一 ownership root，切換與清理都有清楚邊界。"),
            ("Reload 失敗為什麼不會留下半套新設定？", "新狀態在獨立 cycle/pool 建立，尚未 publish；任一步失敗即可關閉新資源並丟棄新 cycle，舊 generation 未被原地修改。"),
            ("舊 cycle 為何不能切換後立刻釋放？", "舊 worker、舊 connection 或 cleanup 仍可能引用其中的 config、log、listener metadata；必須等引用它的 execution generation 退場。"),
            ("Socket 重用避免了什麼問題？", "避免 reload 中斷 accept、避免 bind 競爭與短暫 port unavailable，也讓新舊 worker 可平滑交接。"),
            ("Shared memory 為何要檢查 tag/size？", "同名不代表資料 layout 相同。錯把舊 bytes 按新 struct 解讀會造成越界或語意 corruption；tag/size 是最低限度 schema guard。"),
            ("這和 RCU 有何相似與不同？", "相似處是發布新版本、舊讀者繼續使用舊版本、延後回收；不同處是 NGINX 主要以 process generation 和 resource lifecycle 實作，不是通用 kernel RCU primitive。"),
        ],
    ),
    C(
        8,
        "Master–Worker Process Model",
        "為什麼 NGINX 選擇多程序 worker，而不是讓所有工作都在 master 或大量 thread 中執行？",
        "中階",
        "理解 master 是 control plane、worker 是 data plane，以及 process isolation、signal 與 channel 的代價。",
        ["process isolation", "control plane", "signals"],
        ["src/os/unix/ngx_process_cycle.c:74", "src/os/unix/ngx_process.c:1", "src/os/unix/ngx_channel.c:1"],
        r"""
                 signals / commands
                       │
               ┌───────▼───────┐
               │ master process │  control plane
               └───┬─────┬─────┘
                   │fork │channel
        ┌──────────┴─┐ ┌─┴──────────┐
        │ worker 0   │ │ worker 1   │  data plane
        │ event loop │ │ event loop │
        └────────────┘ └────────────┘
             shared listen fd / optional shared zones
""",
        """
Master 不處理一般 HTTP request。它啟動與監督 worker、接收管理 signal、reload config、reopen log、進行 binary upgrade。Worker 降低權限後進入 event loop，處理 client 與 upstream I/O。

多程序提供 fault containment：某 worker crash 不直接破壞另一 worker 的 heap；master 可以 reap 並 respawn。也減少共享 heap 與細粒度 lock 的需求。代價是跨 worker state 需 shared memory 或 IPC，connection 也不能像 thread 一樣任意搬移。

「一個 worker 一個 event loop」不表示一次只能處理一個 request；它表示某一時刻只有一段 handler 在該 worker CPU 上執行，但數千 request 的狀態可交錯停在不同 I/O 邊界。
""",
        [
            "`ngx_master_process_cycle()` block 管理 signals，啟動 workers/cache helpers。",
            "Master 用 signal flags 在安全主循環內執行複雜動作，而非直接在 signal handler 做。",
            "`ngx_spawn_process()` fork child，建立 channel socketpair。",
            "Worker 初始化 module hooks、event backend、connection arrays，然後循環處理 events/timers。",
            "Child exit 由 master reap；依 respawn policy 決定是否重建。",
        ],
        """
Signal handler 必須 async-signal-safe，因此通常只設定 `sig_atomic_t` flag；master loop 被喚醒後再做 allocation、logging、fork 等工作。這是將 interrupt context 轉換為 normal context 的標準模式。

Worker 數量通常接近可用 CPU，但不是機械公式。CPU affinity、blocking third-party module、SSL workload、disk I/O 與容器 quota 都會改變最佳值。過多 worker 會增加 context switch、shared contention 與 cache footprint。

Channel 讓 master 通知 worker open/close channel、quit 等控制訊息。這比把所有管理狀態放 shared memory 更容易維護事件順序。
""",
        r"""
signal_handler(sig) {
    if (sig == RELOAD) reload_requested = 1;  /* 只設 flag */
}

master_loop() {
    spawn_workers();
    for (;;) {
        wait_for_signal();
        if (child_exited) reap_and_maybe_respawn();
        if (reload_requested) build_new_cycle_and_workers();
        if (quit_requested) signal_workers_gracefully();
    }
}
""",
        [
            "用 `ps -o pid,ppid,stat,cmd` 畫出 master/worker parent relation。",
            "向一個 worker 發 SIGKILL，觀察 master 是否 respawn 及既有連線影響。",
            "用 `/proc/PID/fd` 比較 master 與 worker 持有的 listening socket。",
            "在單 worker 的 handler 中 sleep，觀察同 worker 所有 request 延遲。",
        ],
        [
            "認為 event-driven 等同 parallel；單 worker handler 仍是 serial CPU execution。",
            "在 signal handler 中直接做 malloc、log 或複雜 reload。",
            "認為 worker 越多吞吐一定越高，忽略 CPU quota 與 contention。",
        ],
        [
            "理解 process isolation、supervision tree 與 crash-only recovery。",
            "區分 control plane/data plane。",
            "理解 event concurrency、CPU parallelism 與 thread concurrency 的差別。",
        ],
        [
            ("一個 worker 如何同時服務很多 request？", "它保存每個 request 的狀態，只在對應 fd ready 或 timer 到期時執行一小段 handler；等待 I/O 的 request 不佔用 call stack 或 thread。"),
            ("為什麼 master 不直接處理 request？", "管理與 serving 分離可讓 reload、respawn、權限下降與失敗隔離更清楚；master 的狀態也不會被複雜 request module 污染。"),
            ("Signal handler 為何只設 flag？", "可安全呼叫的函式極少；malloc、stdio、一般 logging 都可能 deadlock 或破壞狀態。設原子 flag 後由 normal loop 處理最安全。"),
            ("Worker crash 後 client 一定無感嗎？", "不是。該 worker 擁有的 active connections 會中斷；其他 worker 繼續服務，新連線可由 respawn worker 接手。Process isolation 降低 blast radius，不消除單連線失敗。"),
            ("什麼情況一個 worker per CPU 不合適？", "容器 CPU quota、NUMA、blocking module、重 SSL/regex workload、磁碟 thread pool 等都可能需要實測；應看 CPU saturation、run queue、tail latency 和 lock contention。"),
            ("為何跨 worker connection 不容易遷移？", "Socket fd、event registration、request pointers、pool 與 module context 都在該 process address space。遷移需要 fd passing 和完整狀態序列化，成本與複雜度高。"),
        ],
    ),
    C(
        9,
        "Graceful Reload 為什麼不會中斷連線",
        "SIGHUP 之後新設定如何上線，而舊 request 又為什麼能繼續完成？",
        "進階",
        "沿 master 與 worker 兩條時間線理解 zero-downtime reload、draining、失敗回退與長連線風險。",
        ["graceful shutdown", "draining", "generation handoff"],
        ["src/os/unix/ngx_process_cycle.c:74", "src/core/ngx_cycle.c:39", "src/core/ngx_connection.c:1120"],
        r"""
time ─────────────────────────────────────────────>

master:  receive HUP ─ build new cycle ─ spawn N+1 ─ signal old quit
old WN:  accept───────┐ stop accept ─ drain active ─ exit
new W:                  init ─ accept new traffic ───────────────>

若 new cycle 建立失敗：
old WN:  繼續 accept 與服務；不發布半套設定
""",
        """
Graceful reload 是 generation handoff，不是把 worker 內設定原地換掉。Master 收到 reconfigure flag 後呼叫 `ngx_init_cycle(old)`；成功才啟動新 workers，並向舊 workers 發 graceful shutdown signal。

舊 worker 收到 quit 後關閉 listening sockets、關閉 idle connections，但讓 active requests 與 non-cancelable timers 繼續。當 event loop 判斷沒有必要工作，worker 才退出。新 worker 同時接受新連線。

因此「不會中斷」有條件：正常而有限的 request 可以完成；無限 WebSocket、卡住 upstream、buggy module timer 或永不結束的 streaming 可能讓舊 generation 長時間不退。`worker_shutdown_timeout` 是最後邊界，不是正常控制手段。
""",
        [
            "Master signal handler 設 `ngx_reconfigure`，master loop 醒來。",
            "建立新 cycle；若失敗記錄錯誤並保持舊 cycle。",
            "成功後啟動新 worker/cache helper。",
            "向舊 worker 發 graceful shutdown；舊 worker 設 `ngx_exiting`。",
            "舊 worker 關 listener、idle connections，持續 event loop 到 timers/active work 完成。",
        ],
        """
Listener fd 可能在 master 中跨 generation 保存，再由 fork 繼承。這避免重新 bind 的時間窗，也讓新 worker 能立即接流量。若 listen options 改變到不相容，cycle init 需要重新配置或報錯。

Drain 的判斷不能只看「active connection count 為零」。可取消 timer、cache helper、subrequest、upstream cleanup 都可能影響退出；實作使用 event/timer 狀態與 connection close 路徑共同完成。

Reload 也是 deploy correctness 問題。設定語法正確不代表行為正確；應先 `-t`、再 canary/觀察新 worker pid、錯誤率與舊 worker drain 時間。
""",
        r"""
on_reload() {
    next = init_cycle(current);
    if (!next) return;                 /* 舊服務保持 */

    spawn_workers(next);
    signal_old_workers(GRACEFUL_QUIT);
    current = next;
}

worker_on_quit() {
    stop_accepting();
    close_idle_connections();
    while (has_non_cancelable_work())
        process_events_and_timers();
    exit();
}
""",
        [
            "保持一條慢 request，同時 reload；用 pid 與 access log 證明它在哪一代完成。",
            "用語法錯誤 config reload，確認 master/old worker 不退出。",
            "建立長連線或很長 proxy timeout，測量舊 worker drain 時間。",
            "比較 `quit` 與 `stop` 對 active connection 的影響。",
        ],
        [
            "把 graceful 理解成所有連線永遠不會斷；它仍受 timeout、process crash 與 shutdown deadline 約束。",
            "只看新 worker 已啟動，未監控舊 worker是否長期殘留。",
            "在 reload 前只跑 syntax test，未驗證 upstream、憑證與實際 traffic 行為。",
        ],
        [
            "設計 draining、rolling restart 與 deployment health gate。",
            "理解 versioned config 與 active request 的一致性邊界。",
            "辨識長連線對 zero-downtime deployment 的特殊需求。",
        ],
        [
            ("舊 request 在 reload 後使用新設定嗎？", "通常不會。它所在舊 worker 繼續引用舊 cycle/module conf；新連線由新 worker 使用新 generation，避免半途語意改變。"),
            ("新設定解析失敗時為什麼不影響舊服務？", "新 cycle 隔離建立，失敗不 publish，也不先終止舊 worker。這是 prepare-before-switch。"),
            ("為什麼舊 worker要關閉 idle keep-alive connection？", "若保留 idle connection，它可能持續接收新 request，使舊 generation 無法收斂退出；關閉 idle 讓 client 重連到新 worker。"),
            ("長 WebSocket 會造成什麼問題？", "舊 worker可能因 active connection 長期不退，持有舊 binary、設定與資源。需要明確 max connection age、drain policy 或強制 shutdown deadline。"),
            ("Graceful reload 與 load balancer draining 有何共同點？", "都是先停止接新工作，再完成 in-flight，最後釋放舊 instance；核心指標是新工作入口、active work 與最大 drain time。"),
            ("如何驗證 reload 真正成功？", "不只看 command exit code；確認新 worker pid、配置 generation、error log、真實 request 行為、舊 worker drain，以及 upstream health。"),
        ],
    ),
]


PART_3 = [
    C(
        10,
        "Socket、File Descriptor 與 TCP 最小基礎",
        "在讀 accept、recv 與 epoll 前，哪些 OS 與 TCP 概念是不可跳過的？",
        "初階",
        "用一個 server socket 與一條 client connection 建立 fd、socket、TCP、HTTP 的正確分層。",
        ["file descriptor", "TCP", "non-blocking I/O"],
        ["src/os/unix/ngx_socket.c:1", "src/core/ngx_connection.c:1", "src/os/unix/ngx_recv.c:1"],
        r"""
process file table
fd 7 ──> listening socket 0.0.0.0:8080
fd 8 ──> connected socket client:53122 ↔ nginx:8080
fd 9 ──> connected socket nginx:49210 ↔ backend:9001

TCP connection ≠ HTTP request
一條 client TCP connection：request 1 → response 1 → request 2 → response 2
""",
        """
File descriptor 是 process 內的小整數索引，指向 kernel 管理的 open-file/socket 狀態。Listening socket 表示一個等待連線的入口；每次成功 `accept()` 會得到新的 connected socket fd。原 listening fd 繼續存在，兩者不可混淆。

TCP 提供有序 byte stream，沒有「一次 send 對應一次 recv」的訊息邊界。`recv()` 可能只得到半個 HTTP header，也可能得到 header 加部分 body；`send()` 也可能只接受部分 bytes。HTTP parser 必須在 byte stream 上自行建立語意邊界。

Non-blocking 表示 syscall 無法立即前進時返回 `EAGAIN`，不是表示 kernel 在背景替你完成所有業務邏輯。程式需保存尚未完成的範圍，等 readiness notification 後重試。
""",
        [
            "Listening sockets 在 cycle init 中建立、設定 options、bind、listen。",
            "`accept4(..., SOCK_NONBLOCK)` 直接產生 non-blocking connected socket；不支援時再用 `fcntl/ioctl` 設定。",
            "`ngx_connection_t` 把 fd、read/write events、I/O function pointers 與 protocol data 組合。",
            "`ngx_unix_recv()` 將 `EAGAIN` 翻成 `NGX_AGAIN`，將 EOF 與其他 error 寫入 event/connection 狀態。",
        ],
        """
Readiness 是提示「現在操作可能不阻塞」，不是承諾「能完成整個 request」。在 edge-triggered 模式，handler 通常持續 read 到 `EAGAIN` 才算把當前通知消耗乾淨；write 也要追蹤 `pos/last` 或 chain 中未送完的位置。

EOF、RST、timeout 與應用層 4xx/5xx 是不同層次的失敗。`recv()==0` 表示 peer orderly close；`ECONNRESET` 是 transport error；HTTP 502 則是 NGINX 將 upstream failure 映射為 protocol response。

一條 proxy request 通常同時涉及 client socket 與 upstream socket。兩邊速度不同，因此 buffer、backpressure、timeout 與 cleanup 必須明確屬於哪一側。
""",
        r"""
ssize_t read_nonblocking(int fd, buffer *b) {
    ssize_t n = recv(fd, b->last, b->end - b->last, 0);
    if (n > 0) {
        b->last += n;            /* 只得到一段 bytes */
        return n;
    }
    if (n == 0) return EOF_REACHED;
    if (errno == EAGAIN) return TRY_LATER;
    return IO_ERROR;
}
""",
        [
            "用 `ss -tnlp` 找 listening socket，再發 request 找 connected socket。",
            "用一個小 client 將 request line 分三次 send，確認 NGINX 仍能 incremental parse。",
            "把 response body 設大並限制 client 讀取速度，觀察多次 write/writev。",
            "用 strace 分辨 listening fd、client fd 與 upstream fd。",
        ],
        [
            "把 TCP 當 message queue，假設一次 recv 得到完整 request。",
            "把 fd 當全系統唯一 ID；它只在特定 process 與時間範圍內有效，close 後可重用。",
            "看到 writable 就假設所有 output 都已寫完。",
        ],
        [
            "理解 stream framing、partial I/O 與半開 buffer range。",
            "建立 transport error、protocol error、application error 的分層。",
            "理解所有 event-driven networking library 的底層 contract。",
        ],
        [
            ("Listening socket 與 accepted socket 的關係是什麼？", "前者代表服務入口並持續監聽；後者代表一條具體 client TCP connection。Accept 不會把 listening fd 變成 connected fd，而是回傳新 fd。"),
            ("為什麼兩次 `send()` 不一定對應兩次 `recv()`？", "TCP 只保證有序 byte stream，kernel 可分段、合併與緩衝。應用協定必須靠長度、delimiter 或狀態機恢復訊息邊界。"),
            ("Non-blocking `recv()` 回 EAGAIN 是錯誤嗎？", "它是正常控制結果：目前沒有更多 bytes，應返回 event loop 並等待下一次 readable 通知，不應記成服務故障。"),
            ("一個 fd 為何可能產生 stale event？", "fd close 後數字可很快被新 socket 重用，而舊 epoll event 可能仍在本輪結果中；NGINX 使用 connection instance bit 等機制辨認過期事件。"),
            ("Client connection 和 upstream connection 可以共用一個 timeout 嗎？", "不適合。Client header/read/write 與 upstream connect/send/read 是不同風險與 SLO，需分開 timer、錯誤映射與 log。"),
            ("HTTP keep-alive 對 object model 有什麼要求？", "Transport connection 必須可在一個 request finalize 後回到 waiting state，再建立下一個 request；request-lifetime memory 不能污染下一次交換。"),
        ],
    ),
    C(
        11,
        "NGINX 如何接受新連線",
        "Listening socket readable 之後，NGINX 如何把一個 fd 變成可由 HTTP 層處理的 connection？",
        "中階",
        "逐步走過 `ngx_event_accept()`，理解 connection slot、pool、non-blocking、protocol handler 與 fd exhaustion。",
        ["accept", "connection pool", "resource exhaustion"],
        ["src/event/ngx_event_accept.c:21", "src/core/ngx_connection.c:1068", "src/http/ngx_http.c:1804"],
        r"""
listen read event ready
       │
       ▼
accept4() → new fd
       │
       ▼
ngx_get_connection(fd)
       ├─ read event
       ├─ write event
       └─ generation/instance
       │
       ▼
create connection pool + peer address + log
       │
       ▼
ls->handler(c) → ngx_http_init_connection(c)
""",
        """
Event backend 不知道 HTTP。它只知道 listening connection 的 read event ready，呼叫該 event 的 accept handler。`ngx_event_accept()` 從 kernel 取新 fd，再從預先配置的 connection free list 取得 `ngx_connection_t` 與配對 events。

每條 accepted connection 建立自己的 pool，保存 peer sockaddr、log context 與協定資料。最後呼叫 `ls->handler(c)`；HTTP 在設定 listening socket 時把 handler 指向 `ngx_http_init_connection`。這個 callback 是通用 event layer 與 protocol layer 的接縫。

若 file descriptor 耗盡，繼續 accept 只會產生錯誤風暴。程式會暫停 accept events 或設定 delay timer，讓系統有時間釋放 fd。這是 overload control，而不只是 error log。
""",
        [
            "由 listening read event 取回 listening connection 與 `ngx_listening_t`。",
            "在 multi-accept 模式可循環 accept，直到 `EAGAIN` 或配額結束。",
            "`ngx_get_connection()` 從 free list 取 slot，初始化 read/write event 並綁 fd。",
            "建立 connection pool、複製 sockaddr、設定 recv/send function pointers。",
            "註冊 event backend 後呼叫 protocol-specific listening handler。",
        ],
        """
Connection array 大小受 `worker_connections` 影響，但可代理連線數通常小於這個值，因為一個 proxy request 可能同時佔 client 與 upstream connection，還有 listening、resolver 等 fd。

NGINX 會重用 `ngx_connection_t` slot，因此 event 的 instance/generation 必須辨認舊事件。這是 object pool 常見 ABA 類問題：記憶體地址相同，不代表仍是同一代物件。

Accept fairness 取決於 epoll exclusive、reuseport、accept mutex、multi_accept 與負載。新 Linux 常有更好的 kernel wake-up 機制，但理解 accept mutex 仍能學到 thundering herd 與 work distribution。
""",
        r"""
void on_accept_ready(event_t *listen_event) {
    while (accept_budget()) {
        int fd = accept_nonblocking(listen_event->fd);
        if (fd == EAGAIN) return;
        if (fd_exhausted(fd)) {
            temporarily_disable_accept();
            return;
        }

        connection_t *c = acquire_connection_slot(fd);
        c->pool = create_pool();
        initialize_socket_io(c);
        c->listening->protocol_handler(c);
    }
}
""",
        [
            "在 `ngx_event_accept` 設 breakpoint，檢查 `lc`、`ls`、新 `c` 與 read/write event。",
            "把 `worker_connections` 設得很小，建立大量 keep-alive connection，觀察告警。",
            "調整 `multi_accept`，比較一次 readiness 中 accept 次數。",
            "降低 process fd limit，觀察 `EMFILE` 後 accept 暫停與恢復。",
        ],
        [
            "把 `worker_connections` 當成可同時代理的 request 數。",
            "忽略 connection slot 重用，將舊 event 誤派給新 fd。",
            "在 fd exhaustion 時無限制重試 accept，形成 busy loop 與 log storm。",
        ],
        [
            "理解 object pool、generation token 與 stale callback 防護。",
            "理解 overload 時應暫停入口，而不是更激烈重試。",
            "辨認 framework layer 與 protocol plugin 的 callback boundary。",
        ],
        [
            ("為什麼 accepted connection 需要自己的 pool？", "Sockaddr、log context、protocol state 等都和 connection 共同存亡；pool 讓 close 時可整體釋放並執行 cleanup。HTTP request 仍可另建更短生命週期 pool。"),
            ("`worker_connections` 為何不等於最大 client 數？", "Listening、upstream、resolver、cache helper 等都使用 connection/fd；reverse proxy 常每個 active request 至少用 client 與 backend 兩條 connection。"),
            ("`ls->handler` 的架構意義是什麼？", "Accept core 只完成通用 socket/connection 初始化，再由 callback 選 HTTP、Stream、Mail 等協定，避免 event layer 依賴上層。"),
            ("發生 EMFILE 時暫停 accept 有何作用？", "避免同一 readable listener 不斷喚醒並立即失敗，降低 CPU/log 壓力，等待既有 connection 關閉釋放 fd。"),
            ("為什麼 object pool 需要 instance bit？", "Slot 地址與 fd 數字都可能重用；舊 readiness 若晚到，必須用 generation 資訊判斷它不屬於當前 connection。"),
            ("`multi_accept on` 一定更好嗎？", "不一定。它可快速清空 accept queue，但單 worker 一次拿太多新連線可能降低其他 events 公平性；要依 connection burst 與 tail latency 實測。"),
        ],
    ),
    C(
        12,
        "從 select 到 epoll",
        "epoll 解決了什麼問題，又有哪些常見的錯誤神話？",
        "中階",
        "理解 readiness、interest set、只取回 ready subset 的模型、LT/ET 與 non-blocking contract，而不是把 epoll 當魔法加速器。",
        ["epoll", "readiness", "edge-triggered"],
        ["src/event/modules/ngx_epoll_module.c:1", "src/event/ngx_event.c:127", "src/event/ngx_event.h:433"],
        r"""
application interest set              kernel ready list
fd 8: READ  ───────────────────────┐
fd 9: WRITE ────────────────┐      │
fd10: READ                  │      │
                           ▼      ▼
epoll_wait()  ─────────> [fd9 WRITE, fd8 READ]

只回傳 ready 的 fd；handler 仍必須實際 recv/send。
""",
        """
傳統 select/poll 每輪把大量 fd 描述交給 kernel，回來後 application 還要掃描集合。epoll 維護持久 interest set，`epoll_wait` 回傳本輪 ready events；優勢主要出現在大量大多數 idle 的 connection。

Readiness 不是 completion。`EPOLLIN` 表示 read 操作可能前進，handler 還是要呼叫 recv；`EPOLLOUT` 表示 send buffer 可能有空間，不表示先前整個 response 已完成。

Level-triggered 在條件持續成立時會繼續通知；edge-triggered 著重狀態邊緣，通常必須一直操作到 EAGAIN。NGINX 用 event flags 抽象不同 backend，將 ET/clear event 差異包在 event handling contract。
""",
        [
            "Epoll module 初始化 epoll fd 與 event list，設定 add/del/process function table。",
            "Add event 使用 `epoll_ctl` 維護 fd 的 interest mask，read/write 共享同一 fd registration。",
            "`ngx_epoll_process_events()` 呼叫 `epoll_wait(ep, event_list, nevents, timer)`。",
            "對回傳 event 檢查 instance，設定 read/write event ready，再直接呼叫或 post handler。",
            "EPOLLERR/HUP 會轉成 read/write 都 ready，讓既有 handler 有機會處理錯誤。",
        ],
        """
Epoll 的 scalable 不代表 handler 可以慢。只要某 handler 在 event loop 中阻塞 100ms，該 worker 其他 ready events 都至少延遲 100ms。Epoll 降低等待與掃描成本，不能提供 CPU parallelism。

EPOLLOUT 通常幾乎一直成立，若沒有 pending output 卻長期訂閱 write event，loop 可能持續被喚醒。正確做法是只在 partial write/EAGAIN 時啟用，送完就關閉或忽略。

Stale event 檢查解決 fd reuse：event data 同時攜帶 connection pointer 與 instance bit，若 connection 已 close/reuse，舊 event 被丟棄。
""",
        r"""
int process_events(int timeout_ms) {
    int n = epoll_wait(epfd, events, MAX, timeout_ms);
    for (int i = 0; i < n; i++) {
        connection_t *c = decode_pointer(events[i].data.ptr);
        if (is_stale(c, events[i])) continue;

        if (events[i].events & READABLE)
            c->read->handler(c->read);
        if (events[i].events & WRITABLE)
            c->write->handler(c->write);
    }
}
""",
        [
            "用 strace 觀察 idle NGINX 阻塞在 `epoll_wait`，再發 request 看返回數量。",
            "寫一個 non-blocking socket lab，故意在 ET 收到通知後只讀 1 byte，觀察剩餘資料。",
            "建立 slow-reading client，觀察何時註冊/觸發 write event。",
            "在 handler 人為 sleep，測量同 worker 另一請求的延遲。",
        ],
        [
            "以為 epoll 讓每個 request 在不同 thread 執行。",
            "把 readiness 當完成通知，未處理 partial I/O。",
            "永久關注 EPOLLOUT，造成高 CPU busy wake-up。",
        ],
        [
            "理解 readiness-based I/O、interest management 與 event demultiplexing。",
            "辨認 scalability bottleneck 是 fd scanning、handler CPU 還是 downstream latency。",
            "理解 LT/ET 對 handler contract 的影響。",
        ],
        [
            ("Epoll 相較 select 最重要的模型差異是什麼？", "Interest set 持久保存在 kernel，wait 回傳 ready subset，不必每輪重傳並掃描全部 fd；但實際 I/O 與狀態管理仍由 application 完成。"),
            ("EPOLLIN 是否保證一次 recv 得到完整 HTTP request？", "不保證。它只表示目前至少可讀或有 EOF/error；TCP 分段與 buffer 大小仍可能讓 parser 多次進入。"),
            ("Edge-triggered 為何常要求讀到 EAGAIN？", "通知代表狀態由不可讀變可讀；若未排空，可能沒有新的邊緣提醒剩餘資料，導致 connection 卡住。"),
            ("為什麼 write event 不應永遠啟用？", "多數 socket 的 send buffer 有空，因此 writable 幾乎常成立，會讓 event loop 無意義醒來；只有 pending output 送不完時才需要等待。"),
            ("Epoll 能解決 blocking DNS/library 嗎？", "不能。只要在 event handler 同步阻塞，worker 仍停住；需 async resolver、thread pool、子程序或外部服務隔離。"),
            ("Stale event 和 ABA 問題有何關聯？", "Pointer/fd 看似回到相同值，但已是新 generation。Instance token 提供額外身分，避免把舊通知作用於新物件。"),
        ],
    ),
    C(
        13,
        "ngx_event_t 與 Callback Architecture",
        "同一條 connection 為什麼能先等待 request、再解析 header、再等待 keep-alive，而 event loop 不需知道這些階段？",
        "中階",
        "理解 event object、generic data pointer、handler 切換與手寫動態派發。",
        ["callback", "state machine", "inversion of control"],
        ["src/event/ngx_event.h:30", "src/core/ngx_connection.h:127", "src/http/ngx_http_request.c:211"],
        r"""
同一個 read event

accept 後       rev->handler = ngx_http_wait_request_handler
收到首批 bytes  rev->handler = ngx_http_process_request_line
request line 完 rev->handler = ngx_http_process_request_headers
request 完成後   rev->handler = ngx_http_keepalive_handler

epoll 只做：rev->ready = 1; rev->handler(rev);
""",
        """
`ngx_event_t` 是「一個可能發生的 I/O/timer 工作」。它保存 `data`、`handler`、timer node 以及 ready、active、timedout、eof、error 等 flags。`ngx_connection_t` 通常有一個 read event 和一個 write event。

Event loop 不硬編碼 HTTP 狀態。上層每到新階段就替換 handler；下一次 readiness 進入新的 callback。這是 continuation 的 C 實作：call stack 消失，但下一步函式與需要的資料都保存在 heap object。

`data` 常指向 connection，handler 再由 `c->data` 取得 protocol-specific object。這兩層 indirection 讓 event core 完全不知道 HTTP request layout。
""",
        [
            "Event backend 找到 ready fd，取 connection，再取 read/write event。",
            "設定 `ready/eof/error` flags，呼叫 `event->handler(event)`。",
            "Handler 從 `event->data` 取得 connection，從 `connection->data` 取得當前 protocol state。",
            "若階段改變，handler 更新 function pointer；若暫停，保留 object state 後返回。",
            "Timer 到期也設定 `timedout` 後呼叫同一 handler，使 I/O 與 timeout 共用 cleanup path。",
        ],
        """
Event flags 是壓縮後的狀態機輸入。Handler 入口先檢查 `timedout`、`close`、`error`，再處理正常 I/O。若忘記清 timer 或 active flag，未來 callback 可能重入已 finalize 的 request。

NGINX 另有 `r->read_event_handler`、`r->write_event_handler` 與 upstream 的 read/write handlers，形成兩階 dispatch：socket event 先進共用 wrapper，再依 request/upstream 狀態分派。這讓 connection handler 保持穩定，同時細分 protocol 工作流。

這種手寫 callback 速度快、allocation 可控，但可讀性成本高。現代 async/await 編譯器本質上也把函式切成狀態機，只是由 compiler 產生 continuation frame。
""",
        r"""
void socket_event_entry(event_t *ev) {
    connection_t *c = ev->data;
    request_t *r = c->data;

    if (ev->timedout) {
        fail_request(r, TIMEOUT);
        return;
    }

    /* 真正下一步由先前階段安裝 */
    r->read_continuation(r);
}
""",
        [
            "記錄 client read handler 從 accept 到 keep-alive 的每次賦值。",
            "在 GDB 印出 `c->read->handler` 位址，用 symbol lookup 對應函式。",
            "找 upstream 共用 `ngx_http_upstream_handler` 的第二層 dispatch。",
            "故意觸發 timeout，證明同 handler 可由 timer 而非 fd readiness 叫醒。",
        ],
        [
            "只看 handler 定義，不找它在何種狀態下被安裝。",
            "假設 `c->data` 永遠是 request；accept 初期可能是 HTTP connection context。",
            "Finalize 後未取消 timer/event，造成 stale callback 或 use-after-free。",
        ],
        [
            "理解 callback、continuation、async state machine 的等價關係。",
            "追蹤 function pointer dispatch 與狀態轉移。",
            "設計 framework core 不依賴 protocol-specific 型別。",
        ],
        [
            ("Event loop 如何知道下一步要解析 request line？", "它不知道。HTTP 層先把 read event handler 設為對應函式；epoll 只在 readable 時呼叫目前的 function pointer。"),
            ("為什麼 handler 狀態不放在 call stack？", "I/O 可能等待任意時間，不能讓每條 connection 佔一個 blocking stack/thread；跨等待狀態保存在 request/connection object。"),
            ("Timer 為何可重用 I/O handler？", "Timer 到期把 `timedout` flag 設定後呼叫 event handler，入口依 flag 走 timeout path；正常 I/O 與 timeout 可共享該階段的 cleanup context。"),
            ("兩階 dispatch 的優點是什麼？", "Socket 層可維持少數穩定入口，request/upstream 內再切換細部 continuation，降低直接改 epoll registration 與通用層耦合。"),
            ("Callback 架構最大風險是什麼？", "控制流分散、lifetime 難推理、重入與取消複雜。必須明確記錄 owner、timer、active event、reference count 與 finalize contract。"),
            ("Async/await 與這種 C callback 有何共同點？", "都在等待點保存局部狀態和下一個 program counter；async/await 由 compiler 生成 state machine，NGINX 由 struct 欄位與 function pointer 手寫。"),
        ],
    ),
    C(
        14,
        "事件循環完整解剖",
        "Worker 每一輪到底按什麼順序處理 timer、accept、I/O 與 posted events？",
        "進階",
        "逐行建立 `ngx_process_events_and_timers()` 的排程模型，理解順序如何影響公平性與鎖。",
        ["event loop", "scheduling", "posted events"],
        ["src/event/ngx_event.c:195", "src/event/ngx_event_posted.c:1", "src/event/modules/ngx_epoll_module.c:812"],
        r"""
find nearest timer
       │
       ├─ try accept mutex / move next events
       ▼
epoll_wait(timeout)
       │
       ▼
posted accept events
       │
       ├─ release accept mutex
       ▼
expire timers
       │
       ▼
posted ordinary events
       └──────────────> next loop
""",
        """
Worker 主循環每輪只呼叫 `ngx_process_events_and_timers(cycle)`。函式先取得最近 timer 到期時間，將它作為 epoll wait timeout；所以 timer tree 和 I/O wait 不是兩個 thread，而是同一 scheduler 的兩種喚醒來源。

若使用 accept mutex，worker 嘗試取得鎖。持鎖時 epoll 返回的 accept events 先 post 到專用 queue，離開 kernel wait 後優先處理，接著釋放鎖，避免持鎖執行一般 request handler。

Timers 在 accept 後、一般 posted events 前過期。Posted queue 讓 backend 可以先收集 readiness，再由一致順序執行 callbacks；也能避免深層同步遞迴，將工作延後到安全點。
""",
        [
            "`ngx_event_find_timer()` 回最近 deadline 或 infinite。",
            "Accept mutex 與 posted-next queue 可能縮短 wait timeout。",
            "`ngx_process_events()` 經 function table 進入 epoll/kqueue 等 backend。",
            "先處理 posted accept events，必要時 release accept mutex。",
            "`ngx_event_expire_timers()` 逐個觸發已到期 timer。",
            "最後 drain ordinary posted events。",
        ],
        """
Event loop latency 可以分成 wait latency、queueing latency 與 handler service time。即使 epoll 立即回傳，前面某個 handler 很慢，後面的 ready event 仍排隊。這就是為何 tail latency 與 callback budget 重要。

Posted-next queue 可保證事件至少延到下一輪，避免同一輪不斷 self-post 造成 starvation。這是 cooperative scheduler 的 yield 概念。

排序不是普遍真理，而是具體取捨：accept 太優先可能餓死既有連線；只處理既有連線又可能讓 accept queue overflow。NGINX 透過 queue、mutex、multi_accept、timer 與 event backend flags 平衡。
""",
        r"""
while (!exiting) {
    timeout = nearest_timer_deadline();
    maybe_acquire_accept_right();

    backend_wait(timeout);          /* epoll_wait */

    run(posted_accept_events);
    release_accept_right();
    run(expired_timers);
    run(posted_events);
}
""",
        [
            "在四個階段加低成本 trace id，驗證一次 loop 的真實順序。",
            "建立大量新連線加一批既有慢 response，比較 accept 與 ordinary event 延遲。",
            "找出一個使用 posted event 避免直接遞迴的路徑。",
            "量測單一 handler sleep 10ms 對同 worker p99 的影響。",
        ],
        [
            "把 event loop 想成公平 preemptive scheduler；handler 不會被自動搶占。",
            "認為 timer 有獨立 thread 精準觸發；實際精度受 loop latency 影響。",
            "在 callback 中無界迴圈處理資料，造成其他 events starvation。",
        ],
        [
            "理解 cooperative scheduling、run queue 與 callback budget。",
            "拆解 tail latency 的 queueing component。",
            "設計 event/timer 統一 scheduler 與安全 deferred work。",
        ],
        [
            ("Epoll timeout 為何取最近 timer？", "若沒有 I/O，kernel wait 最多睡到下一個 deadline；若 I/O 提前發生則先回來處理。這把兩種喚醒來源合併。"),
            ("Posted event 與直接呼叫 handler 有何差異？", "Post 只入 queue，延後到明確 scheduler 階段執行，可控制順序、避免深遞迴、配合 accept mutex 或下一輪公平性。"),
            ("Timer 到期是否會在 deadline 那一毫秒精準執行？", "不保證。若 worker 正在執行長 handler，timer 只能等控制權回到 loop；deadline 是不早於的排程目標，不是 real-time guarantee。"),
            ("為什麼 accept event 使用獨立 posted queue？", "可先處理新連線並及早釋放 accept mutex，避免持鎖執行普通 request callbacks，降低跨 worker 阻塞。"),
            ("什麼是 event-loop starvation？", "某 callback 或不斷 repost 的工作長時間佔用 loop，其他 ready I/O/timers 無法獲得執行。解法包括有界批次、yield、thread pool 或分割工作。"),
            ("如何量化 handler 是否太慢？", "量 event loop lag、callback duration、ready queue delay 與 p99；CPU profile 找長 hot path，並用單 worker controlled load 建立因果。"),
        ],
    ),
    C(
        15,
        "Timer 與紅黑樹",
        "課本裡的紅黑樹為什麼會出現在 NGINX timer，而不是換成 heap 或排序陣列？",
        "進階",
        "從 timer workload 推導 ordered structure，理解最小 deadline、任意刪除、重設 timer 與 wraparound。",
        ["red-black tree", "timer", "ordered set"],
        ["src/event/ngx_event_timer.c:1", "src/event/ngx_event_timer.h:1", "src/core/ngx_rbtree.c:1"],
        r"""
                       1050
                      /    \
                   1010    1200
                  /   \
               1005   1030
               ↑
          nearest deadline

event 內嵌 timer node
ngx_event_t
  ├─ handler
  ├─ timedout
  └─ ngx_rbtree_node_t timer
""",
        """
Timer scheduler 的核心操作是：加入 deadline、取消任意 event 的 timer、找最小 deadline、依序取出所有已到期項目。紅黑樹提供 O(log n) 插入/刪除，最左節點給最小值；event 內嵌 node，取消時不需額外 map 找 heap index。

NGINX timer tree 允許 duplicate keys，因為主要需求只是找 minimum，不要求 deadline 唯一。到期時從最左開始，若 deadline 已過就刪除、標記 `timedout`、呼叫 handler；遇到第一個未到期便停止。

時間比較用 signed difference 處理 millisecond counter wraparound。直接比較 unsigned `a < b` 在 counter 回繞附近會錯；理解這點比背旋轉四種 case 更接近 production engineering。
""",
        [
            "全域 timer rbtree 以 timer-specific insert function 初始化。",
            "`ngx_add_timer` 設 node key、插入 tree、標記 `timer_set`。",
            "`ngx_event_find_timer` 取最左 node，計算 deadline-current time。",
            "`ngx_event_expire_timers` 反覆取 minimum，處理所有到期 events。",
            "取消或重設 timer 時依 embedded node O(log n) 刪除。",
        ],
        """
為何不是 binary heap？Heap 找 min 與插入很好，但取消任意 event 需要知道其 heap index並在 swap 時維護；紅黑樹 node 直接嵌入 event，pointer 即刪除位置。兩者都可行，選擇取決於 cancellation frequency 與既有 infrastructure。

為何不是 timer wheel？Wheel 對大量近似精度 timer 可達 O(1) amortized，但有 bucket resolution、遠期 timer 與實作複雜度。NGINX 的 ordered tree 簡單、通用且 deadline 精度直觀。

`timer_set` 是 ownership flag：同一 embedded node 不能同時插入兩次。重設 timer 前必須刪舊節點，否則 tree 結構損壞。
""",
        r"""
deadline = now_ms + timeout_ms;

add_timer(event, deadline):
    if event.timer_set:
        tree.delete(&event.timer)
    event.timer.key = deadline
    tree.insert(&event.timer)
    event.timer_set = true

expire(now):
    while tree.min().deadline <= now:
        event = container_of(tree.pop_min(), event_t, timer)
        event.timer_set = false
        event.timedout = true
        event.handler(event)
""",
        [
            "建立三個不同 timeout 的連線，觀察 timer tree minimum 變化。",
            "找一條收到 I/O 後刪 timer 的路徑，確認不會之後再 timeout。",
            "用小程式比較 heap 取消任意 timer 所需 metadata。",
            "模擬 32-bit millisecond counter wraparound，比較 unsigned 與 signed-difference 判斷。",
        ],
        [
            "只從 Big-O 選結構，忽略任意取消與 embedded node。",
            "重設 timer 不先刪除舊 node。",
            "把 timeout 當精準執行時間，忽略 event loop lag。",
        ],
        [
            "從 workload 推導資料結構，而不是由題型反推場景。",
            "理解 intrusive tree、container_of 與 cancellation metadata。",
            "處理 monotonic counter wraparound 與 deadline arithmetic。",
        ],
        [
            ("NGINX timer tree 最常需要哪些操作？", "插入 deadline、取消已知 event、找最小 deadline、逐一彈出到期節點。紅黑樹讓前三者都維持對數或常數取得 minimum。"),
            ("Duplicate deadline 為什麼沒問題？", "Scheduler 不要求 key 唯一，只要所有相同 deadline 都位於可遍歷的有序位置；expire 會一直取 minimum 直到未到期。"),
            ("Heap 為何不是明顯更好的答案？", "Heap 也可行，但任意 cancellation 需要 index handle 且 swap 時更新。Embedded rb node 讓 event pointer 本身就是可刪除 handle。"),
            ("Timer wheel 可能在哪種 workload 更好？", "數量極大、timeout 範圍可分 bucket、允許固定解析度且頻繁增刪時；代價是遠期 timer、精度與 bucket 管理更複雜。"),
            ("為何 deadline 比較要使用差值 cast？", "有限位寬 counter 會回繞；在兩時間相距不超過半個範圍的前提下，signed difference 可正確判斷前後，直接 unsigned 比較會在 wrap 點失敗。"),
            ("Timer handler 執行前為何先把 node 刪除並清 flag？", "Handler 可能重新加 timer或 finalize object；先解除舊 ownership 可避免 double insert/delete 與重入時看見錯誤狀態。"),
        ],
    ),
    C(
        16,
        "Backpressure 與 Event Loop 公平性",
        "Backend 很快、client 很慢時，NGINX 為什麼不會無限制把 response 堆進記憶體？",
        "進階",
        "理解 partial write、buffer waterline、read suppression、temporary file 與 bounded work。",
        ["backpressure", "flow control", "tail latency"],
        ["src/http/ngx_http_upstream.c:3780", "src/core/ngx_output_chain.c:1", "src/os/unix/ngx_writev_chain.c:1"],
        r"""
fast backend                         slow client
   │ 100 MB/s                           │ 100 KB/s
   ▼                                    ▼
[upstream read] → [memory buffers] → [client write]
       ▲                │ full             │ EAGAIN
       │                ▼                  │
       └──── pause read / spill temp file ─┘

沒有邊界：memory grows → OOM
有 backpressure：限制在途資料，讓速度差可控
""",
        """
Backpressure 是下游消化不及時，向上游傳遞「先別再產生」的訊號。Non-blocking write 回 `NGX_AGAIN` 時，NGINX 保留未送完 chain，註冊 write event；是否繼續讀 upstream 取決於 buffer 空間、busy buffers、buffering 與 temporary file policy。

Buffering 可把 backend 與 client 速度解耦，提高 backend connection 釋放速度；但 memory 有上限，較大 response 可能落 temporary file。Streaming 降低首 byte latency 與磁碟使用，卻讓慢 client 長時間占用 upstream connection。

公平性也屬 backpressure。單次 callback 若無界讀寫，即使每次 syscall non-blocking，也可能長時間占據 CPU。NGINX 使用 chain limit、sendfile max chunk、posted events 等方式讓控制權回到 loop。
""",
        [
            "Output chain 將 memory/file buffers 轉成適合 OS send/writev/sendfile 的 chain。",
            "Write filter 累積尚未送完的 output，partial write 後保留 position。",
            "Upstream event pipe 在 input、output、free、busy chains 間搬動 buffers。",
            "Buffer 超過 memory policy 時可寫 temporary file；下游可再從 file buffer 送出。",
            "Socket writable 後 writer handler 繼續先前未完成範圍。",
        ],
        """
背壓不是單一布林值，而是多層 flow control：kernel send buffer、NGINX busy buffer、proxy buffer/temp file、upstream read event、HTTP/2 window 都可能形成邊界。分析時要指出哪一層滿了、誰停止讀、誰負責重新喚醒。

取消 upstream read event 可能是 ET 模式敏感操作；framework 要維護 active/ready flags，確保恢復時不丟失通知。這也是為何 event abstraction 比直接散落 epoll_ctl 重要。

Slowloris 是反方向：client 太慢地送 request header，長期佔用 connection。Header timeout、buffer limit 與 connection limit是入口 backpressure/security。
""",
        r"""
int forward(upstream_t *u, client_t *c) {
    flush_pending_output(c);

    if (c->pending_output && socket_would_block(c)) {
        enable_write_event(c);
        if (buffers_are_full(c))
            pause_upstream_read(u);
        return TRY_LATER;
    }

    if (buffer_space_available(c))
        resume_upstream_read(u);
    return OK;
}
""",
        [
            "產生 100MB response，用 `curl --limit-rate` 建立慢 client，觀察 memory 與 temp path。",
            "切換 `proxy_buffering`，比較 upstream connection 持有時間與 client TTFB。",
            "限制 proxy buffer/temp file，觀察 read/write events 如何交替。",
            "設定小 `sendfile_max_chunk`，壓測時比較 event loop lag。",
        ],
        [
            "把 buffering 一律視為延遲或一律視為效能最佳；它是資源與耦合取捨。",
            "只限制單 buffer 大小，未限制所有 in-flight chains。",
            "在 writable callback 無界 flush，造成其他 connection starvation。",
        ],
        [
            "理解 bounded queue、producer/consumer 與 backpressure propagation。",
            "比較 buffering、streaming、spooling 的 latency/resource tradeoff。",
            "辨認慢消費者與 retry/queue 放大造成的系統崩潰。",
        ],
        [
            ("Partial write 後剩餘資料存在哪裡？", "Buffer/chain 的 `pos` 與 busy/output lists 保存未送範圍；write event handler 在下次 writable 時從該位置繼續，而不是重送整個 response。"),
            ("Buffering 如何幫助 fast backend？", "NGINX 可較快讀完 backend response 並釋放 upstream connection，之後慢慢送 client；代價是 NGINX memory/disk 與額外 copy。"),
            ("關掉 proxy buffering 有什麼代價？", "可降低部分 latency 與 temp file，但 backend connection 的生命週期更受慢 client 牽制，並降低吸收速度差與故障隔離能力。"),
            ("Backpressure 為什麼不只是 memory limit？", "還包括暫停 producer read、控制 syscall batch、connection/time limits、HTTP flow window 與 queue admission；limit 只是訊號，還需傳播策略。"),
            ("Non-blocking handler 為何仍可能餓死 event loop？", "它可以在 user-space loop 處理大量立即 ready 工作而不返回。Non-blocking只保證 syscall，不保證 callback 執行時間有界。"),
            ("如何判斷 temp file 是問題還是合理設計？", "同時看 response size、client rate、memory budget、disk latency、upstream occupancy 與 SLO；spooling 可能是有意的速度解耦，也可能表示下游長期壅塞。"),
        ],
    ),
]


PART_4 = [
    C(
        17,
        "ngx_http_request_t：一次 HTTP 交換的核心物件",
        "Connection 已經存在後，NGINX 何時建立 request，又把哪些跨 callback 狀態放進去？",
        "中階",
        "建立 request、connection、pool、module context、main/subrequest 與 reference count 的生命週期圖。",
        ["request lifecycle", "ownership", "reference count"],
        ["src/http/ngx_http_request.h:385", "src/http/ngx_http_request.c:539", "src/http/ngx_http_request.c:3981"],
        r"""
ngx_connection_t (TCP lifetime)
  ├─ c->pool
  ├─ read/write events
  └─ c->data ───────────────┐
                             ▼
                    ngx_http_request_t (HTTP lifetime)
                      ├─ r->pool
                      ├─ headers_in/out
                      ├─ phase_handler
                      ├─ module ctx/conf arrays
                      ├─ upstream
                      └─ main/count/subrequests
""",
        """
Connection 先存在；收到足以開始 HTTP parsing 的資料後，`ngx_http_create_request()` 才建立 request pool 與 `ngx_http_request_t`。Request 保存解析指標、headers、URI、phase index、read/write continuation、output state、upstream 與每個 module 的 ctx。

Config 和 ctx 必須分開：config 來自 cycle，對許多 requests 共用且通常唯讀；ctx 是 module 對單一 request 的暫存狀態，配置在 request pool，隨 request 結束。

`r->main` 與 `main->count` 協調 subrequest、async operation 與延後 finalize。返回 `NGX_DONE` 往往表示目前控制流停止，但主 request 仍有 pending ownership，不能立刻 free。
""",
        [
            "`ngx_http_create_request(c)` 建 request pool，配置並初始化 request。",
            "將 connection buffer 交給 `r->header_in`，避免不必要 copy。",
            "配置 `ctx/main_conf/srv_conf/loc_conf` pointer arrays。",
            "把 `c->data` 切換為 request，安裝 request-line handler。",
            "最終 `ngx_http_free_request` 執行 cleanups、log、destroy request pool。",
        ],
        """
Request struct 很大，不應從第一個欄位背到最後。按責任分群：input parser、routing/config、phase control、body/output、upstream、lifetime/flags。每追一條路徑只打開相關群。

Buffer ownership 是重點。Header bytes 常仍位於 connection/request buffer，`ngx_str_t` 只指向其中區間；若 module 要跨越 buffer reuse 或 request lifetime保存，就必須 copy 到更長生命週期。

Main request count 類似 structured concurrency 的 join counter。每個新增 async/subrequest obligation 增加 count，完成時減少；歸零才能進入最終 free。
""",
        r"""
request_t *create_request(connection_t *c) {
    pool_t *pool = create_pool(REQUEST_POOL_SIZE);
    request_t *r = pcalloc(pool, sizeof(*r));

    r->pool = pool;
    r->connection = c;
    r->main = r;
    r->count = 1;
    r->header_in = c->buffer;
    r->ctx = pcalloc(pool, module_count * sizeof(void *));
    c->data = r;
    return r;
}
""",
        [
            "在 `ngx_http_create_request` 前後比較 `c->data` 的型別與 request pool。",
            "挑十個 request 欄位，按 parser/routing/output/lifetime 分類。",
            "建立 keep-alive 兩次 request，確認 request pointer/pool 改變而 connection 可重用。",
            "找一個增加 `r->main->count` 的 async/subrequest 路徑與對應 decrement。",
        ],
        [
            "把 module config 當 request 私有資料並嘗試修改。",
            "保存指向 request buffer 的 slice 到比 request 更長的 cache。",
            "看到 content handler 返回就立即 free，忽略 pending subrequest/output。",
        ],
        [
            "使用 ownership tree 與 lifetime region 分析大型 struct。",
            "理解 per-request context、shared immutable config 與 async join counter。",
            "避免 dangling slice 與跨生命週期 pointer。",
        ],
        [
            ("Request 為何要有自己的 pool，而 connection 已有 pool？", "Request 通常比 keep-alive connection 短；分池可在每次交換後釋放解析、module ctx、body 等大量資料，而保留 transport buffer與 socket。"),
            ("`main_conf/srv_conf/loc_conf` 和 `ctx` 有何差別？", "前三者指向 configuration generation 的共享唯讀設定；ctx 是某 module 對此 request 的可變執行狀態。"),
            ("`c->data` 為何會改變語意？", "通用 connection 只提供 `void *` 協定資料；accept 初期可指 HTTP connection context，建立 request 後改指 request。Handler 與階段共同決定正確型別。"),
            ("Request slice 為何可能變成 dangling pointer？", "許多 `ngx_str_t` 只引用 header/body buffer；buffer reuse 或 request pool destroy 後 bytes 不再有效。若需長期保存必須複製。"),
            ("Main request count 解決什麼？", "讓主 request 等待 subrequest、AIO、thread task、buffered output 等 obligations 全部完成，避免過早 free。"),
            ("如何閱讀巨大 request struct？", "先依責任分群，再從一條 runtime trace 記錄實際讀寫欄位；不要把 layout 當 API 文件逐欄背誦。"),
        ],
    ),
    C(
        18,
        "HTTP Request Line 狀態機",
        "如果 `GET /api HTTP/1.1` 被拆成三個 TCP packet，parser 如何從上次停下的位置繼續？",
        "進階",
        "理解 incremental finite-state machine、pointer markers、`NGX_AGAIN` 與 buffer 擴容。",
        ["finite-state machine", "incremental parser", "bounds checking"],
        ["src/http/ngx_http_parse.c:105", "src/http/ngx_http_request.c:1115", "src/http/ngx_http_request.c:1639"],
        r"""
bytes: G E T _ / a p i _ H T T P / 1 . 1 \r \n
state: method ─> spaces ─> URI ─> version ─> CR ─> LF ─> done

packet 1: "GET /a"      → state=URI, save pos
packet 2: "pi HTTP/1"   → state=version, save pos
packet 3: ".1\r\n"      → NGX_OK
""",
        """
HTTP parser 不能假設完整 line 一次到達。它把目前 state 存在 request 欄位，把 buffer position 與 request_start、method_end、uri_start 等 markers 指向已讀 bytes；下一次 read 後從原 state 繼續 switch。

Parser 回 `NGX_AGAIN` 表示語法目前仍可能有效，只是 bytes 不夠。Caller 檢查 buffer 是否滿；滿了就配置 large header buffer 並搬移必要資料，或回 URI too large。語法錯誤則映射到特定 parse code，再產生 400/414 等 HTTP response。

高效 parser 常使用手寫 switch 與 pointer arithmetic，因為每個 byte 都在 hot path；但安全性來自每一步先檢查 end，且不把未驗證 bytes 當 NUL-terminated string。
""",
        [
            "Read handler 呼叫 `ngx_http_read_request_header` 把 bytes 補進 `header_in`。",
            "`ngx_http_parse_request_line(r, b)` 由 `r->state` 恢復 parser。",
            "成功時設定 request/method/URI/version markers 與 normalized URI。",
            "不完整時保留 state；buffer 滿時嘗試 large-header allocation。",
            "完成 request line 後把 read handler 切到 header parser。",
        ],
        """
狀態機的價值是把「所有可能 prefix」壓成有限狀態，而不是每次重掃整個 buffer。Markers 避免 substring copy；parse 完成後以 pointer difference 形成 `ngx_str_t`。

安全 parser 需要區分 raw URI、normalized URI 與 arguments。Percent decoding、dot segments、multiple slashes 與平台特殊字元都可能影響 routing/security；不能先 decode 再用另一套規則做 access check。

面試中的 expression parser、CSV streaming、protocol framing 都可用相同方法：state＋cursor＋token start＋explicit incomplete result。
""",
        r"""
parse_result parse_line(parser *p, buffer *b) {
    for (; b->pos < b->last; b->pos++) {
        char ch = *b->pos;
        switch (p->state) {
        case METHOD:  /* validate token, maybe enter URI */ break;
        case URI:     /* save args/ext markers */           break;
        case VERSION: /* parse digits incrementally */      break;
        case ALMOST_DONE:
            if (ch != '\n') return INVALID;
            return COMPLETE;
        }
    }
    return INCOMPLETE;
}
""",
        [
            "用 netcat 分三次輸入 request line，觀察同一 request parser 多次進入。",
            "在 parser breakpoint 記錄 `r->state`、`b->pos`、`b->last`。",
            "發送超長 URI，追蹤 large header buffer 與 414 路徑。",
            "比較 raw URI、normalized URI、args 在 `%2F`、`..`、重複 slash 下的值。",
        ],
        [
            "每次新資料到來就從頭 parse，造成重複掃描甚至 O(n²)。",
            "將不完整 prefix 當語法錯誤，無法處理 TCP segmentation。",
            "不同安全檢查使用不同 URI normalization 規則。",
        ],
        [
            "實作 incremental parser 與 resumable state machine。",
            "使用 pointer markers 避免 copy，同時維持 bounds safety。",
            "理解 normalization order 對 routing/security 的影響。",
        ],
        [
            ("`NGX_AGAIN` 和 parse error 有何差異？", "AGAIN 表示目前 prefix 合法但資料不足，應保存 state 等更多 bytes；error 表示無論後續 bytes 為何都不能成為合法 request。"),
            ("為何不在每次 read 後重新從 request start 解析？", "會重複掃描長 prefix，在逐 byte 到達時可能退化為 O(n²)；保存 state/cursor 可保持總體近 O(n)。"),
            ("Markers 指向原 buffer 有何優點與風險？", "避免 substring allocation/copy；但 buffer 搬移或釋放時需同步修正 pointer，且不得跨生命週期保存。"),
            ("為什麼 raw URI 與 normalized URI 都要保留？", "Routing/security 常用規範化結果，代理或 log 有時需原始表示。混用可能造成 path confusion 或簽章不一致。"),
            ("Large header buffer 只是效能設定嗎？", "也是資源與安全邊界。太小拒絕合法大 request；太大乘上大量慢連線會增加 memory DoS surface。"),
            ("這個 parser pattern 可用在哪些 coding 題？", "串流 tokenizer、括號/運算式解析、網路 frame decoder、逐塊 JSON/CSV，以及任何輸入可能被任意切分的題。"),
        ],
    ),
    C(
        19,
        "Header Parsing 與安全邊界",
        "NGINX 如何逐行解析 header，同時處理 Host、Content-Length、重複欄位與大小限制？",
        "進階",
        "理解 generic header list、known-header dispatch、host 切換、framing 衝突與 request smuggling 防線。",
        ["HTTP headers", "framing", "security"],
        ["src/http/ngx_http_parse.c:842", "src/http/ngx_http_request.c:1401", "src/http/ngx_http_request.c:82"],
        r"""
raw header line
   ↓ incremental parser
name slice + value slice + hash
   ↓
append generic headers list
   ↓ hash lookup known headers
Host ─────────> virtual server / config context
Content-Length ─> body framing
Connection ─────> keep-alive policy
""",
        """
Header parser 和 request-line parser 同樣可跨 read。每完成一行，NGINX 建 `ngx_table_elt_t` 放入 generic list；同時用 lowercase hash 查 known-header table，執行專屬 processing callback，把常用欄位放進 `headers_in` 快速欄位。

Host 特別重要：request line 或 Host header 可選 virtual server，進而替換 srv/loc configuration context。也就是 parser 不只產生資料，還可能改變後續 policy 世界。

Content-Length、Transfer-Encoding、Connection 等不是普通 metadata，而是 message framing。衝突或非法重複值若前後代理理解不同，可能形成 request smuggling；parser 必須拒絕 ambiguous framing。
""",
        [
            "補資料並呼叫 `ngx_http_parse_header_line`，保存跨 buffer state。",
            "完成一行後配置 table element，保存 key/value slice 與 hash。",
            "Known-header hash 找到 callback，填入 typed/shortcut fields。",
            "空行代表 headers complete，進入 `ngx_http_process_request_header` 做整體驗證。",
            "驗證 Host、body framing、method/version、keepalive 後開始 phase engine。",
        ],
        """
Generic list 保留未知 header，讓 proxy/module 能轉發或處理擴充欄位；typed shortcuts 避免每個模組重複 scan。這是 raw representation＋normalized index 的常見雙層資料模型。

Header names、underscores、invalid characters、duplicate Host/Content-Length 都有 policy。安全重點不是「符合某一 parser」，而是整條 proxy chain 必須對邊界做一致解讀。

記錄 header 時也要考慮 secrets 與 log injection。值是 untrusted bytes；不要直接把 Authorization/Cookie 或控制字元完整寫入 log。
""",
        r"""
for each complete_header_line {
    header h = parse_name_value_slice(buffer);
    generic_headers.push(h);

    known = known_header_hash.lookup(lowercase_hash(h.name));
    if (known)
        known->process(request, h);
}

if (end_of_headers)
    validate_host_and_message_framing(request);
""",
        [
            "發送未知 `X-Lab` header，找它在 generic list 與 proxy output 的位置。",
            "發送兩個不同 Content-Length、Host 或同時 CL/TE，記錄拒絕路徑。",
            "在 Host callback 前後觀察 request 的 srv/loc conf pointer。",
            "測試 header line/total buffer limits與慢速逐 byte 傳送。",
        ],
        [
            "把所有 header 當無語意 key/value，忽略 framing 與 routing 欄位。",
            "只在最外層 proxy 驗證，後端 parser 使用不同規則。",
            "將敏感或未清理 header 原樣寫 log。",
        ],
        [
            "設計 raw＋indexed representation。",
            "理解 protocol ambiguity、parser differential 與 request smuggling。",
            "對 untrusted metadata 做 limit、normalization 與安全 logging。",
        ],
        [
            ("為什麼既有 generic list 又有 `headers_in.host` 等欄位？", "List 保留全部與未知擴充欄位；shortcut 提供 O(1) 常用語意存取並集中驗證。兩者服務不同需求。"),
            ("Host header 為什麼能改變 config context？", "同一 IP:port 可承載多個 virtual servers；讀到 Host 後才能選正確 server configuration，後續 location、limits、TLS外 policy 可能不同。"),
            ("Content-Length 與 Transfer-Encoding 衝突為何危險？", "不同 hop 若選不同 framing，攻擊者可讓前端認為 request 已結束、後端把剩餘 bytes 當下一請求，形成 queue desynchronization。"),
            ("為什麼 header limits 也是安全機制？", "限制每 connection 可佔 memory、parser CPU 與等待時間，降低慢速或超大 header 的資源耗盡。"),
            ("Known-header hash 的效能優點是什麼？", "解析每行時一次 dispatch，後續模組直接讀 typed field，不必多次對 list 做字串比較；config/startup 可預建 lookup。"),
            ("如何安全記錄 malformed header？", "限制長度、轉義控制字元、遮蔽 secrets，並包含 connection/request identifier；不要讓 attacker 產生巨量或偽造多行 log。"),
        ],
    ),
    C(
        20,
        "Virtual Server 與 Location Matching",
        "同一個 port 上有很多 server/location 時，NGINX 如何選出最後的 configuration？",
        "進階",
        "分清 address、Host、normalized URI 三次選擇，以及 prefix、regex、named location 與 internal redirect。",
        ["routing", "prefix tree", "configuration context"],
        ["src/http/ngx_http_request.c:2558", "src/http/ngx_http_core_module.c:1446", "src/http/ngx_http.c:760"],
        r"""
local address:port
       ↓ default server + virtual-name table
Host/SNI/name
       ↓ server configuration
normalized URI
       ├─ longest static prefix
       ├─ nested location
       └─ regex policy
       ↓ final loc_conf

internal redirect → URI 改變 → location search 可重跑
""",
        """
第一層在 accept/HTTP init 時依 local address:port 找 default server 與 name table。第二層在 request line/Host 完成後，用 exact/wildcard/regex server name 選 srv config。第三層用 normalized URI 選 location。

Location matching 不是單純「設定檔從上到下第一個匹配」。Static locations 在 config-time 整理成 tree，runtime 尋找 longest prefix；regex 與 nested policy 再按規則介入。Named location 通常由內部跳轉直接指定，不參與一般 URI prefix 查找。

Internal redirect、rewrite、index 等可能改 URI並重跑 location。為防設定迴圈，NGINX 有 URI changes counter；routing 是 bounded state machine，不是一錘定音。
""",
        [
            "Address/port config 提供初始 default server context。",
            "`ngx_http_set_virtual_server` 依 Host/name table 切換 server context。",
            "`ngx_http_core_find_location` 先查 static location tree。",
            "依結果與設定處理 nested/regex location。",
            "更新 `r->loc_conf`，執行 location-specific handler/config。",
        ],
        """
Configuration pointer 切換比複製設定更便宜：request 的 loc_conf array 改指向 config generation 中已合併物件。這也是 config immutable 的好處。

URI normalization 必須先於 location security policy，否則 `%2e%2e`、重複 slash、case/platform 差異可能讓不同層看到不同 path。另一方面，proxy 到 upstream 時是否傳 raw 或 normalized URI又有明確規則。

排查 routing 不應只看 location 文字。固定輸出 `$request_uri`、`$uri`、host、server_name、location marker，才能分辨原始 URI、normalized URI 與最後 config。
""",
        r"""
route(request *r) {
    r->server_conf = find_server(r->local_addr, r->host);
    r->uri = normalize(r->raw_uri);

    loc = longest_prefix(r->server_conf->location_tree, r->uri);
    if (loc.allows_regex)
        loc = first_matching_regex_or(loc);

    r->loc_conf = loc->module_configs;
}
""",
        [
            "建立 exact、prefix、nested、regex、named locations，為每個回不同 header。",
            "測試 `/a`、`/a/`、percent-encoded 與重複 slash，記錄 `$request_uri`/`$uri`。",
            "用 rewrite/internal redirect 讓 location search 重跑，觀察 counter。",
            "在 virtual server lookup 前後比較 srv_conf pointer。",
        ],
        [
            "用設定檔視覺順序推測所有 location precedence。",
            "把 raw request URI 與 normalized routing URI 混為一談。",
            "Internal redirect 無上限，形成 rewrite loop。",
        ],
        [
            "理解 multi-stage routing、prefix tree 與 regex fallback。",
            "使用 immutable config pointer 快速切換 policy context。",
            "設計有迴圈上限的 rewrite/routing state machine。",
        ],
        [
            ("為什麼先選 server 再選 location？", "Location tree 屬於特定 server；同一 address 可依 Host 使用不同 locations、limits、root 與 upstream，因此需要分層選擇。"),
            ("Longest prefix 和 regex 如何共同存在？", "Static tree 先找最具體 prefix，之後依 location flags/nesting 規則決定是否測 regex；不是簡單的全域排序。"),
            ("Named location 為何不走一般 URI matching？", "它是內部控制流標籤，通常由 error_page、try_files 或 module 跳轉，名稱不是 client URI prefix。"),
            ("Internal redirect 為什麼需要計數上限？", "Rewrite A→B 與 B→A 可形成無限 loop；bounded counter 將設定錯誤轉成可終止失敗。"),
            ("`$request_uri` 與 `$uri` 的排障價值？", "前者通常保留原始請求表示含 args，後者是目前 normalized/可能被 rewrite 的 URI；兩者差異能揭示 routing confusion。"),
            ("Config pointer 切換為何優於每 request merge？", "Merge 在 reload 時完成，runtime 只改 array pointer，降低 hot-path CPU/allocation 並確保同 generation 一致。"),
        ],
    ),
    C(
        21,
        "HTTP Phase Engine",
        "Rewrite、access control、content handler 為什麼能由不同模組依序插入，而 core 不需要知道每個模組？",
        "進階",
        "理解 config-time 編譯 phase table、checker/handler 雙層函式與 return-code protocol。",
        ["pipeline", "middleware", "return-code protocol"],
        ["src/http/ngx_http.c:448", "src/http/ngx_http_core_module.c:894", "src/http/ngx_http_core_module.c:928"],
        r"""
config-time:
module handlers by phase
   ↓ compile
[checker, handler, next] [checker, handler, next] ...

request-time:
r->phase_handler = i
        │
        ▼
checker(r, ph) ──> module handler(r)
   ├─ DECLINED: i++
   ├─ OK: jump ph->next
   ├─ AGAIN/DONE: suspend
   └─ HTTP status/error: finalize
""",
        """
HTTP modules在 postconfiguration 把 handler push 到某 phase array。Config initialization 將各 phase 編譯成扁平 `ngx_http_phase_handler_t` table，每項包含 checker、真正 module handler 與 next index。

Request 只保存 `phase_handler` index。`ngx_http_core_run_phases()` 迴圈呼叫 checker；checker統一解讀 module return code、決定前進、跳 phase、暫停或 finalize。模組不必彼此直接呼叫。

這是高效 middleware pipeline，但和常見 nested `next()` 不同：控制流用 index與 return protocol 表達。理解 `NGX_DECLINED` 尤其重要，它通常表示「我不處理，讓同 phase 下一 handler 嘗試」，不是錯誤。
""",
        [
            "HTTP core 建立 phases arrays，各 module 在 postconfiguration 註冊 handler。",
            "`ngx_http_init_phase_handlers` 依 phase 生成 checker/handler/next table。",
            "Request 完成 header 後設定 `phase_handler` 與 write continuation。",
            "`ngx_http_core_run_phases` 從目前 index 執行，直到 checker 要求返回。",
            "Async handler 保存必要 state，未來 event 再呼叫 run phases 或專用 continuation。",
        ],
        """
Checker 將控制語意集中。例如 access phase 可能依 `satisfy any/all` 聚合多個 module 結果；rewrite phase可能改 URI；content phase找到 handler後停止搜尋。Phase 不是同質列表。

模組 return code 是 ABI。若把 `NGX_OK`、`DECLINED`、`AGAIN` 用錯，可能跳過後續 handler、重複 finalize 或讓 request 永遠懸掛。寫 module 前要讀該 phase checker，而不只讀範例 handler。

扁平 table 提高 instruction/data locality並避免 request-time 建 pipeline。代價是 debug 時要把 index 對回 phase與 module。
""",
        r"""
while (phase[i].checker != NULL) {
    rc = phase[i].checker(r, &phase[i]);

    if (rc == STOP_FOR_NOW)
        return;                       /* async 或已 finalize */
    /* checker 已更新 r->phase_handler */
    i = r->phase_handler;
}
""",
        [
            "列出一個 request 的 phase index、checker、module handler trace。",
            "寫最小 preaccess handler 回 `NGX_DECLINED`，確認後續 handler仍執行。",
            "改回 403，確認 finalize 與 content phase 不再執行。",
            "找 access phase checker如何處理 satisfy any/all。",
        ],
        [
            "把 `NGX_DECLINED` 當服務失敗。",
            "不讀 checker就猜 return code 語意。",
            "Async handler 返回後既不保存 continuation也不 finalize，造成 request leak。",
        ],
        [
            "理解 compiled pipeline、table-driven dispatch 與 middleware。",
            "設計明確 return-code protocol。",
            "分析 plugin ordering、short circuit 與 async suspension。",
        ],
        [
            ("Phase table 為何在 config-time 編譯？", "模組集合與順序在 reload 後固定，預先扁平化可避免每 request 遍歷 registry或建立 chain，並預計算 jump index。"),
            ("Checker 與 handler 為何分開？", "Handler只實作模組功能；checker統一處理該 phase 的 return code、跳轉、聚合與 finalize規則。"),
            ("`NGX_DECLINED` 通常代表什麼？", "當前模組不處理或不做決定，讓同 phase/後續路徑繼續；它是控制信號，不是一般錯誤。"),
            ("Async access check 應如何暫停 phase engine？", "啟動 async work、增加必要引用或保存 ctx，回傳該 checker認可的 suspension code；完成 callback再恢復 phases或 finalize。"),
            ("這和 Express middleware 的 `next()` 有何差異？", "Express常以 nested callback顯式 next；NGINX以扁平 index、checker與 return code驅動，適合 C與預編譯 pipeline。"),
            ("怎麼 debug 某模組為何沒執行？", "確認是否註冊到預期 phase、postconfiguration順序、前一 checker是否 short-circuit、location config是否啟用，並 trace phase index。"),
        ],
    ),
    C(
        22,
        "Request Body、Buffer 與暫存檔",
        "POST body 可能尚未到齊時，content handler 如何等待、落盤或串流而不阻塞 worker？",
        "進階",
        "理解 body framing、post handler continuation、buffer chain、temporary file 與 unbuffered mode。",
        ["request body", "buffer chain", "streaming"],
        ["src/http/ngx_http_request_body.c:1", "src/http/ngx_http_parse.c:2075", "src/http/ngx_http_upstream.c:626"],
        r"""
headers complete
      │ Content-Length / chunked
      ▼
read_request_body(r, post_handler)
      ├─ body already in header buffer
      ├─ read more on client read events
      ├─ memory chain
      └─ temp file if configured/large
      ▼ complete
post_handler(r) → content/upstream continues
""",
        """
Body 讀取是非同步子流程。Module 呼叫 `ngx_http_read_client_request_body(r, post_handler)`；若資料不完整，函式安裝 read handler、timer並返回。Body 完成後才呼叫 post handler，這就是 continuation passing。

Framing 由 Content-Length 或 chunked parser決定。Bytes 可能已有一部分跟 headers 同時進入 `header_in`，必須先消費，不能丟掉或重讀。

Body 可存在 chain of buffers，也可寫入 temporary file；proxy request buffering開啟時通常先完整接收 client body，再連/送 upstream。關閉 buffering則可邊收邊轉發，但 retry能力、backend occupancy與 flow control 更複雜。
""",
        [
            "Header validation決定是否有 body與 framing方式。",
            "Body reader先使用已在 header buffer中的 preread bytes。",
            "不完整時安裝 client read handler與 timeout，逐 event讀取。",
            "Chunked filter解析 chunk size/trailer；decoded bytes放入 buffers。",
            "完成後呼叫 module提供的 post handler，恢復原業務流程。",
        ],
        """
Request body reference count防止讀取中 request被 finalize。Module callback必須遵守「可能同步完成，也可能稍後完成」的雙態 API；post handler不能假設一定在另一輪呼叫。

落盤不是失敗，而是 bounded memory策略。安全上需控制 temp path權限、最大 body、disk quota與 client timeout，避免大量慢 upload吃滿 disk或 connection。

Unbuffered forwarding需要處理三方背壓：client producer、NGINX中介、upstream consumer。Backend慢時應停止讀 client，否則仍會在 memory堆積。
""",
        r"""
int begin_body_read(request_t *r, void (*done)(request_t *)) {
    r->body_done = done;
    consume_preread_bytes(r);

    if (body_complete(r)) {
        done(r);                   /* 可能同步完成 */
        return OK;
    }

    r->read_event_handler = continue_body_read;
    add_timeout(r->connection->read);
    return ASYNC_PENDING;
}
""",
        [
            "POST 小 body，證明 body bytes可能已在 header buffer。",
            "逐塊慢速上傳，觀察 body read handler與 timeout。",
            "將 buffer設小讓 body落 temp file，檢查 chain中的 file buffer。",
            "切換 `proxy_request_buffering` 比較 backend connect時機與 retry行為。",
        ],
        [
            "假設 body reader callback一定非同步，造成雙重繼續或未初始化狀態。",
            "忽略 preread bytes，導致 body開頭遺失。",
            "關掉 buffering卻未實作 backend慢時的 client backpressure。",
        ],
        [
            "掌握 continuation API 的同步/非同步雙態。",
            "理解 stream framing、spooling與 bounded memory。",
            "設計三段 pipeline 的 flow control與 retry語意。",
        ],
        [
            ("Body 為何可能在 header parsing時已收到？", "TCP只傳 byte stream，一次 recv可同時包含 header結尾與部分body；parser消費到空行後剩餘 bytes必須交 body reader。"),
            ("Post handler 為何必要？", "Body可能跨多次 read event完成，原 content handler的 stack早已返回；post handler保存完成後的下一步。"),
            ("Body落 temp file代表效能一定很差嗎？", "不一定。它用disk換 bounded memory，可保護大量大 upload；是否合理取決於disk、size、latency與 forwarding策略。"),
            ("`proxy_request_buffering off` 對 retry 有何影響？", "若 body已部分串流給某 backend，換下一 peer可能無法重新取得完整body，尤其 client仍在傳；可重試範圍通常縮小。"),
            ("同步/非同步都可能完成的 API 有什麼陷阱？", "Caller若在呼叫後無條件再執行 continuation，當 callback已同步執行會 double action；應依 return contract或只由 callback推進。"),
            ("如何防止慢 upload耗盡資源？", "限制 body size、header/body timeout、connection數、temp disk/quota，並在 downstream阻塞時停止 read。"),
        ],
    ),
    C(
        23,
        "Response 與 Filter Chain",
        "Content module 產生的 header/body 如何依序經過 gzip、chunked、range、copy 與 write filter？",
        "進階",
        "理解 top/next filter 鏈、註冊反序、header/body 分工、buffer flags與 partial output。",
        ["filter chain", "decorator", "output pipeline"],
        ["src/http/ngx_http.c:74", "src/http/ngx_http_header_filter_module.c:1", "src/http/ngx_http_write_filter_module.c:1"],
        r"""
content handler
   │ ngx_http_send_header(r)
   ▼
[top header filter] → ... → protocol header encoder

body chain
   ▼
[gzip?] → [range?] → [chunked?] → [copy] → [write filter]
                                                    │
                                              socket / sendfile
""",
        """
每個 filter module初始化時保存舊 top pointer為 `next`，再把 global top指向自己。結果是後註冊者先執行，形成手寫 decorator chain。Header filter決定 status/headers與是否需要 body transformation；body filter接收 `ngx_chain_t *`。

Buffer 不只是 byte array。Flags 表示 memory/file、flush、sync、last_buf、last_in_chain、temporary/recycled 等語意。Filter 可以引用原 buffer、產生新 buffer、延後輸出或回 `NGX_AGAIN`。

最底層 write filter合併 pending chain並嘗試 writev/sendfile；未送完的部分留在 request output state，等待 write-ready事件。上層不能在函式返回後修改仍被引用的 temporary buffer。
""",
        [
            "HTTP postconfiguration依 modules註冊 header/body filters。",
            "Content handler設定 `headers_out`，呼叫 top header filter。",
            "Body以 chain傳入 top body filter，每層轉換後呼叫 next。",
            "Copy/output chain把 memory/file buffer轉成適合傳輸的形態。",
            "Write filter做最後 send，partial output標記 request buffered並等待 writable。",
        ],
        """
Filter ordering影響正確性：壓縮前後的 Content-Length、range作用於原始或編碼 representation、chunked framing位置都不能隨意。模組需理解自己在 chain中的相對位置。

Backpressure穿過 filter chain。某層保留 input等待更多資料時要管理 free/busy/out chains，不能假設 next filter同步消費完所有 bytes。

`last_buf` 對 main request表示整個 response最後 buffer；subrequest常用 `last_in_chain`。混用會提早終止或讓 response永不完成。
""",
        r"""
static body_filter_pt next_filter;

int my_filter(request_t *r, chain_t *in) {
    chain_t *out = transform_without_losing_flags(r, in);
    return next_filter(r, out);
}

void init_module(void) {
    next_filter = top_body_filter;
    top_body_filter = my_filter;
}
""",
        [
            "用 debug build列出 top filter註冊結果，畫出實際順序。",
            "開關 gzip/chunked，觀察 headers與 body buffer flags。",
            "建立大 response與慢 client，在 write filter檢查未送 chain。",
            "寫只加 header的 filter，再寫 body prefix filter，比較生命週期。",
        ],
        [
            "Filter傳完 next後立即覆寫 input memory，但下游尚未完成。",
            "丟失 flush/last_buf flags，造成延遲或 response掛住。",
            "只考慮 main request，破壞 subrequest chain語意。",
        ],
        [
            "理解 decorator/filter pipeline與註冊順序。",
            "用 immutable slice/ownership flags安全傳遞 buffer。",
            "分析 streaming transformation與downstream backpressure。",
        ],
        [
            ("為什麼 filter通常保存 old top再替換 top？", "這讓每個 module不需知道其他 filters；初始化時形成 linked function chain，執行時呼叫自己的 next。"),
            ("Body filter返回後 input一定可重用嗎？", "不一定。下游可能只部分送出並仍引用該 buffer；必須遵守 buffer temporary/recycled與free/busy chain contract。"),
            ("`last_buf` 遺失會怎樣？", "下游不知道 response完成，chunk terminator、flush、finalize或keepalive切換可能不發生，request長期掛起。"),
            ("Filter ordering為何不是純效能問題？", "Content-Length、content encoding、range與chunk framing都有語意依賴；錯序會產生無效甚至安全有問題的 response。"),
            ("Write filter如何處理 partial write？", "更新 buffer position，保留未完成 chain，標記 buffered並安裝/等待 write event；下次從剩餘位置續送。"),
            ("如何寫 streaming-safe filter？", "不假設完整 body一次到達；保存跨 chunk state、正確傳播flush/last flags、尊重partial consumption與request pool lifetime。"),
        ],
    ),
    C(
        24,
        "Finalize、Keep-Alive 與 Subrequest",
        "為什麼呼叫 finalize 不一定立刻 free request，而 response完成後 connection又如何回到等待下一個 request？",
        "進階",
        "串起 return code、reference count、buffered output、subrequest、keep-alive reset與最終 pool destroy。",
        ["finalization", "keep-alive", "subrequest"],
        ["src/http/ngx_http_request.c:2743", "src/http/ngx_http_request.c:3352", "src/http/ngx_http_request.c:3981"],
        r"""
handler result / error
       ↓
finalize_request(r, rc)
       ├─ special response / redirect
       ├─ pending output → writer continuation
       ├─ subrequest/main count not zero → wait
       ├─ keep-alive eligible → reset connection to wait request
       └─ close → cleanup + destroy request pool + close connection
""",
        """
Finalize 是狀態轉移入口，不等於 `free(r)`。它要解讀 rc、處理 special response、subrequest、postponed output、buffered filters、lingering close、keepalive與 error。只有所有 obligations結束才進到 free。

主 request可能有 subrequests。Subrequest完成後 output需按正確順序併回主請求；main count防止主 request在孩子仍引用 pool/config時被釋放。

Keep-alive成功時銷毀 request pool與 request-specific state，但保留 connection與部分 buffer，把 read handler改成 keepalive/wait request。下一個 HTTP交換會建立全新的 request。
""",
        [
            "Module/phase/filter以 rc呼叫或觸發 `ngx_http_finalize_request`。",
            "依 rc決定 special response、internal redirect、close或正常完成。",
            "若 request buffered，設定 writer handler等待剩餘 output。",
            "處理 subrequest/postponed chain與 main count。",
            "符合 keepalive條件則 `ngx_http_set_keepalive`；否則 close request/connection。",
            "`ngx_http_free_request` 跑 cleanup、log phase並 destroy pool。",
        ],
        """
Finalize idempotency很難。不同 event可能幾乎同時看到 client close、upstream timeout與write error；flags/reference count需確保清理只執行一次，晚到 callback被安全忽略。

Lingering close在回應後仍讀掉 client剩餘 request body一段時間，避免直接 close造成 RST或讓未讀資料影響連線語意。它是 transport correctness與資源上限的折衷。

Keep-alive能節省 handshake，但 idle connections佔 fd與memory。Timeout、requests-per-connection與reload draining共同決定資源邊界。
""",
        r"""
void finalize(request_t *r, int rc) {
    if (needs_special_response(rc)) send_error_page(r, rc);
    if (r->buffered_output) {
        r->write_continuation = flush_and_finalize;
        return;
    }
    if (--r->main->pending != 0) return;

    run_request_cleanups_and_log(r);
    if (can_keep_alive(r))
        reset_connection_for_next_request(r->connection);
    else
        close_connection(r->connection);
}
""",
        [
            "追蹤一個正常200、一個404與一個upstream timeout的 finalize分支。",
            "建立慢 client讓 output buffered，觀察 finalize後 request仍存活。",
            "同一 keep-alive connection送兩個 request，比較 request pool位址。",
            "建立 subrequest功能，觀察 main count與postponed output。",
        ],
        [
            "把 finalize當同步 destructor。",
            "Keep-alive重用 request-specific ctx，造成跨請求資料洩漏。",
            "多個錯誤event重複 cleanup/free。",
        ],
        [
            "理解 async finalization、idempotent cleanup與reference counting。",
            "區分 transport reuse與transaction lifetime。",
            "分析 parent/child task completion與ordered output。",
        ],
        [
            ("Finalize 為何可能返回後 request仍存在？", "尚有 buffered output、subrequest、AIO/thread task、upstream cleanup或 reference count；finalize只推進到目前安全階段。"),
            ("Keep-alive重用了什麼、沒有重用什麼？", "重用TCP connection、fd、events與部分connection buffer；每次HTTP request物件、pool、module ctx與多數headers必須重新建立。"),
            ("為什麼需要 lingering close？", "若client尚有未讀body，立即close可能產生RST或丟掉已送response；短暫讀棄剩餘資料可更乾淨結束，但需timeout防資源耗盡。"),
            ("Subrequest為何不能完成就直接把body送socket？", "主/子輸出有順序與嵌套關係，需postpone chain協調；直接送會打亂response。"),
            ("如何避免 double free？", "以單一owner、finalized/closed flags、reference count、取消timers/events與清空cleanup pointer建立一次性狀態轉移。"),
            ("Requests-per-connection limit有何價值？", "即使keep-alive正常，定期重建connection可限制長期memory fragmentation、config generation滯留與單client資源占用。"),
        ],
    ),
]


PART_5 = [
    C(
        25,
        "proxy_pass 從哪裡開始",
        "Location 命中 `proxy_pass` 後，proxy module 如何把 client request 轉成一個 upstream request？",
        "中階",
        "分開設定期與請求期，理解 content handler、complex value、header script與 upstream callback contract。",
        ["proxy module", "content handler", "request transformation"],
        ["src/http/modules/ngx_http_proxy_module.c:1", "src/http/ngx_http_upstream.c:508", "src/http/ngx_http_script.c:1"],
        r"""
configuration time
proxy_pass http://backend/api;
   ├─ resolve upstream group / URL parts
   ├─ compile variables/scripts
   └─ install location content handler

request time
phase engine → proxy handler
   ├─ ngx_http_upstream_create(r)
   ├─ set create_request/process_header/finalize callbacks
   ├─ read client body if needed
   └─ ngx_http_upstream_init(r)
""",
        """
`proxy_pass` 有兩個世界。設定期解析 URL、upstream group、URI replacement與含變數的 complex value，並把 location content handler 設為 proxy handler。請求期 handler 不重新解釋整段設定，而是讀取已編譯 loc config。

Proxy module先建立通用 `ngx_http_upstream_t`，再填入 protocol-specific callbacks：如何產生 backend request、如何解析 response header、如何 reinit重試、如何 finalize。Upstream core負責連線、timer、buffer、retry與事件派發；proxy module負責 HTTP-to-HTTP 語意。

Client body可能必須先讀完。Proxy handler註冊 body post handler，等 body ready後才進 `ngx_http_upstream_init`；這延續上一章的 continuation pattern。
""",
        [
            "`proxy_pass` directive callback在 config-time決定 static upstream或編譯 variable script。",
            "HTTP phase engine進入 location content handler。",
            "Proxy handler配置 module ctx與 `ngx_http_upstream_t`。",
            "填 `create_request/reinit_request/process_header/abort/finalize` 等 callback。",
            "設定 buffering、schema、resolved target與 headers；讀 body後啟動 upstream core。",
        ],
        """
URI replacement是常見陷阱：`proxy_pass` 是否帶 URI、location 是 prefix/regex/named、rewrite是否改過 URI，都會影響送往 backend的 path。理解時要同時追 `r->uri`、`r->unparsed_uri` 與 proxy vars，而不是背一句規則。

Header生成常使用 script engine，把常數與 variables預編譯成 length/value programs。這讓每個 request可組合 Host、X-Forwarded-* 等欄位，而不必重新 parse template。

Hop-by-hop headers不能盲目轉發；proxy module需要重建 request line與 headers，並處理 body framing、connection reuse和 upgrade。
""",
        r"""
int proxy_handler(request_t *r) {
    upstream_t *u = upstream_create(r);

    u->create_request   = proxy_create_request;
    u->process_header   = proxy_process_status_and_headers;
    u->reinit_request   = proxy_reinit_for_retry;
    u->finalize_request = proxy_finalize;
    u->conf             = proxy_location_config(r);

    return read_client_body(r, upstream_init);
}
""",
        [
            "為 static `proxy_pass` 與含變數版本各做一個 location，比較 config/runtime解析。",
            "在 proxy handler印出 `r->uri`、`unparsed_uri` 與實際 upstream request line。",
            "修改 Host、Connection、X-Forwarded-For，找出 header script輸出。",
            "POST body時觀察 proxy handler先返回、body post handler再啟動 upstream。",
        ],
        [
            "把 directive parser與 request handler當同一條執行路徑。",
            "直接複製全部 client headers到 backend，包含 hop-by-hop欄位。",
            "只看 `$request_uri` 推理 proxy path，忽略 rewrite與 replacement規則。",
        ],
        [
            "理解 protocol adapter與通用 transport framework的分工。",
            "把 template/variable expression預編譯成 runtime bytecode。",
            "設計安全的 request transformation與header ownership。",
        ],
        [
            ("Proxy module和upstream core如何分工？", "Proxy module懂HTTP request/response格式與設定語意；upstream core提供peer選擇、connect、timer、retry、buffering與事件狀態機。兩者以callbacks連接。"),
            ("為何 `proxy_pass` 的很多工作在config-time做？", "URL、固定headers、變數program與upstream reference對一代設定不變；預編譯可降低每request parse與allocation。"),
            ("含變數的 upstream 有何額外成本與風險？", "每request需評估字串，可能需要runtime DNS resolver；target cardinality、DNS timeout、cache與SSRF policy也更複雜。"),
            ("為什麼不能原樣轉發 Connection header？", "它描述hop-by-hop連線選項，不是end-to-end metadata；不同兩段connection有各自keepalive/upgrade狀態，proxy需重建。"),
            ("Client body為何讓proxy handler成為非同步流程？", "Body可能尚未到齊，handler需先啟動讀取並返回；完成callback才能建立/送完整upstream request。"),
            ("如何驗證URI replacement而不靠記憶？", "用backend echo實際method/path/headers，組合prefix、regex、rewrite與有/無URI的proxy_pass，對照 `r->uri` trace。"),
        ],
    ),
    C(
        26,
        "Upstream State Machine",
        "從建立 upstream 到收到完整 response，中間有哪些可暫停、重試與切換 callback 的狀態？",
        "進階",
        "掌握 `ngx_http_upstream_t` 的通用狀態機與 module callbacks，能預測每個 I/O 邊界。",
        ["upstream", "state machine", "callback interface"],
        ["src/http/ngx_http_upstream.h:1", "src/http/ngx_http_upstream.c:508", "src/http/ngx_http_upstream.c:543"],
        r"""
create
  ↓
init request / cache lookup
  ↓
create backend request bytes
  ↓
select peer → connect
  ↓ writable
send request/body
  ↓ readable
parse response header
  ↓
buffered event pipe OR non-buffered streaming
  ↓
finalize / keepalive peer / retry next peer
""",
        """
`ngx_http_upstream_t` 是client request代理到backend所需的協調物件。它保存 peer connection、module callbacks、request buffers、response buffer、event pipe、conf、state timings、cache與 read/write continuations。

Upstream socket的 read/write event都先進 `ngx_http_upstream_handler`，再分派到 `u->read_event_handler` 或 `u->write_event_handler`。Connect階段、send階段、read-header階段、body階段只需替換第二層 continuation。

每個狀態都可能遇到 timeout、client abort、peer failure或 `NGX_AGAIN`。理解 upstream不能只畫成功路徑；要把 retry邊與 finalize邊一起畫出來。
""",
        [
            "`ngx_http_upstream_create` 配置並清零通用 upstream object。",
            "`ngx_http_upstream_init_request` 處理cache、client abort監視與create_request callback。",
            "初始化 peer selection與state timing，再呼叫 connect。",
            "Upstream connection events經共用handler分派 send/read continuations。",
            "Header完成後選 buffered/non-buffered body處理。",
            "成功或失敗皆進 upstream finalize；可重試時先 reinit再選下一 peer。",
        ],
        """
State timings通常按每次嘗試記錄：connect time、header time、response time、status與peer name。一次client request可有多個upstream states，對應 retry歷史；觀測 `$upstream_*` 時要理解逗號/分隔值不是單一backend。

Client abort監視與upstream生命周期耦合。若response不可cache且client已離開，繼續讀backend通常沒有價值；但cache fill/store等情境可能選擇繼續。

Reinit callback讓protocol module重設parser與request buffers以重試，通用core不用知道FastCGI、proxy或memcached的內部格式。
""",
        r"""
void upstream_event(event_t *ev) {
    connection_t *c = ev->data;
    request_t *r = c->data;
    upstream_t *u = r->upstream;

    if (ev->write)
        u->write_continuation(r, u);
    else
        u->read_continuation(r, u);
}
""",
        [
            "用debug log把一次成功upstream的continuation切換列成時間線。",
            "讓backend connect慢、header慢、body慢，分別觸發三種等待狀態。",
            "讓第一次peer失敗、第二次成功，檢查upstream states陣列。",
            "中途讓client斷線，比較cacheable與non-cacheable行為。",
        ],
        [
            "只追函式call stack，忽略第二層read/write continuation。",
            "把 `$upstream_response_time` 當永遠只有一個值。",
            "重試時只換socket，未重設protocol parser與request body狀態。",
        ],
        [
            "設計通用async transport core＋protocol callbacks。",
            "為多次attempt建立結構化timing/diagnostic state。",
            "分析cancel、retry、cache fill之間的ownership政策。",
        ],
        [
            ("為什麼 upstream read/write event使用共同入口？", "共同入口處理request取得、timeout/error等通用工作，再由upstream內函式指標分派當前階段，減少直接替換底層socket handler。"),
            ("一次request為何有多個upstream state？", "每次peer attempt都需獨立記錄地址、status與各階段時間；retry後保留歷史才能觀測真正延遲與失敗。"),
            ("Protocol module為何需要reinit callback？", "重試新peer時HTTP/FastCGI等parser、buffer cursor與request generation state需回到初始狀態，通用core無法安全猜測。"),
            ("Client斷線後為何有時仍讀upstream？", "若正在建立可供其他request使用的cache/store結果，繼續可能有價值；普通不可cache response則通常終止以節省資源。"),
            ("哪幾個地方最常返回 `NGX_AGAIN`？", "Non-blocking connect未完成、backend send buffer滿、response header/body尚未到、client output送不完；每處都需保存不同continuation。"),
            ("如何判斷upstream卡在哪個階段？", "結合connect/header/response timing、current read/write handler、event timer、debug log與socket state，而不是只看總response time。"),
        ],
    ),
    C(
        27,
        "從 NGINX 非阻塞連線到 Backend",
        "Non-blocking `connect()` 回 EINPROGRESS 之後，誰在什麼時候確認連線成功？",
        "進階",
        "理解 peer callback、connect return codes、write readiness、SO_ERROR、connect timeout與socket pool。",
        ["non-blocking connect", "peer connection", "timeout"],
        ["src/event/ngx_event_connect.c:1", "src/http/ngx_http_upstream.c:1571", "src/http/ngx_http_upstream.c:1852"],
        r"""
select peer address
      ↓
socket() + nonblocking
      ↓
connect()
  ├─ immediate success → send request
  ├─ EINPROGRESS → arm write event + connect timer → return loop
  └─ error → retry/finalize

write-ready
      ↓
getsockopt(SO_ERROR) / test_connect
      ├─ 0 → connected
      └─ error → next peer
""",
        """
Peer selection先填 `ngx_peer_connection_t` 的 sockaddr/name/get/free callbacks。`ngx_event_connect_peer` 建socket、設non-blocking、套socket options並呼叫 connect。

EINPROGRESS不是失敗；它表示三向交握尚未完成。NGINX把 upstream connection的read/write handler設好，write event加 connect timeout，回到loop。可寫通知到來後需檢查 `SO_ERROR`，因為可寫也可能表示connect失敗。

Backend connection有獨立小pool，因為成功後可能被 upstream keepalive cache保留，生命週期超過單一request。Request資料仍不能放進該pool後被錯誤重用。
""",
        [
            "Peer `get` callback選地址並填sockaddr/name。",
            "建立socket、non-blocking、bind local/transparent/socket options。",
            "`connect` 回OK、AGAIN、DECLINED、ERROR等結果。",
            "AGAIN時安裝write event與connect timeout。",
            "Write-ready進send handler，先test connect；失敗走upstream next。",
        ],
        """
Connect timeout包含排隊與網路建立時間，但DNS resolution可能發生在更早階段並有獨立resolver timeout。排障要分DNS、TCP connect、TLS handshake、request send、header wait。

Happy Eyeballs、IPv4/IPv6、多地址DNS與dynamic upstream使peer selection不只是一次地址。NGINX的peer interface把「選哪個」和「怎麼connect」分開，讓算法可替換。

Connection pool重用時要清除request-specific log/data/event flags，並確認socket沒有未讀資料、EOF或timeout；keepalive章會再展開。
""",
        r"""
int connect_peer(peer_connection *pc) {
    pc->connection = new_nonblocking_socket(pc->sockaddr);
    int rc = connect(pc->connection->fd, pc->sockaddr);

    if (rc == 0) return CONNECTED;
    if (errno == EINPROGRESS) {
        watch_writable(pc->connection);
        return IN_PROGRESS;
    }
    return FAILED;
}
""",
        [
            "連到不存在IP/拒絕port/正常backend，比較connect返回與timer。",
            "在 `ngx_event_connect_peer` 與test connect處看 errno/SO_ERROR。",
            "用 `ss -tan` 觀察 SYN-SENT 到 ESTABLISHED。",
            "設定很短 `proxy_connect_timeout`，驗證錯誤映射與retry。",
        ],
        [
            "把write-ready直接視為connect成功，不檢查SO_ERROR。",
            "把DNS、connect、TLS與header latency混成一個timeout。",
            "重用upstream connection時留下舊request pointer/timer。",
        ],
        [
            "理解非阻塞connect的兩階段完成。",
            "設計可插拔peer selection與transport establishment。",
            "建立分階段timeout與可觀測性。",
        ],
        [
            ("EINPROGRESS 為什麼不是錯誤？", "Non-blocking socket不能等待TCP handshake；kernel已啟動連線，完成或失敗會透過write readiness與SO_ERROR呈現。"),
            ("Write-ready為何可能代表連線失敗？", "連線結果已可取得，不等於成功；RST、route error等也會讓fd進入可回報狀態，必須讀SO_ERROR。"),
            ("Peer `get/free` callbacks的用途？", "`get`按算法選地址並取得使用權；`free`依成功/失敗更新conns、fails、weight與availability，讓core與算法解耦。"),
            ("Connect timeout和read timeout有何差別？", "前者涵蓋建立backend connection；後者通常限制兩次read或等待response資料的時間。混用會誤判瓶頸。"),
            ("Upstream connection為何可能有獨立pool？", "Keepalive cache可讓socket跨request存活；若pool綁request，request結束就不能安全保留連線的SSL/event等資源。"),
            ("怎麼證明故障在TCP connect而非backend application？", "看SYN/SYN-ACK、SO_ERROR、connect_time與是否收到任何HTTP header；application還沒收到request前不會有HTTP status。"),
        ],
    ),
    C(
        28,
        "Smooth Weighted Round Robin",
        "NGINX 的預設負載均衡如何同時遵守權重，又避免把高權重流量一次爆量送給同一台？",
        "進階",
        "從公平性需求推導 current/effective weight演算法，並理解failure recovery。",
        ["scheduling", "weighted round robin", "failure recovery"],
        ["src/http/ngx_http_upstream_round_robin.c:1", "src/http/ngx_http_upstream_round_robin.c:758", "src/http/ngx_http_upstream_round_robin.h:1"],
        r"""
weights: A=5, B=1, C=1

每輪：
1. 每個 current += effective
2. 選 current 最大者
3. winner.current -= total_effective

結果示意：A, A, B, A, C, A, A
比例接近 5:1:1，低權重節點不必等到最後一大段才收到流量。
""",
        """
初始化時每個peer保存 `weight`、`effective_weight`、`current_weight`、conns、fails、checked等狀態。選擇時略過down、fail window內、max_conns已滿與本次已嘗試的peer。

每個候選的 current weight加effective weight，選最大者，再從winner current減所有候選effective總和。長期選中次數按權重，短期分布比傳統「AAAAB」更平滑。

Failure可降低effective weight；後續成功選擇時它逐步加回原weight，形成慢恢復。這不是精密健康模型，但可避免剛失敗peer立刻吃回全部比例。
""",
        [
            "Config-time建立primary/backup peer lists與weight totals。",
            "Per-request peer data保存tried bitmap，避免retry同一peer。",
            "Selection loop先過濾down/fails/max_conns/tried。",
            "累加current/effective，選best，winner扣total。",
            "`free` callback更新conns、fails、accessed/checked與state。",
        ],
        """
Smooth weighted RR只對request數比例公平，不保證工作量公平。若request cost差異極大，count-based scheduling會讓某backend承擔更多CPU；least_conn/least_time可能更適合。

Peer state若放shared zone可跨workers共享；否則每個worker有自己的選擇狀態。局部公平不一定等於全域精確比例，尤其流量低或connection分配不均。

Retry tried bitmap是bounded search：每peer最多一次，耗盡後回NGX_BUSY或轉backup group，避免無限重試。
""",
        r"""
peer *choose(peers) {
    peer *best = NULL;
    int total = 0;

    for (peer *p : eligible_peers) {
        p->current += p->effective;
        total += p->effective;
        if (p->effective < p->weight) p->effective++;
        if (!best || p->current > best->current) best = p;
    }
    best->current -= total;
    return best;
}
""",
        [
            "手算權重5:1:1的前14次結果，確認比例與平滑性。",
            "配置三backend回名稱，收集1000次分布。",
            "讓高權重peer間歇失敗，觀察effective weight恢復。",
            "用多worker、有/無zone比較全域分布。",
        ],
        [
            "只驗證長期比例，忽略短期burst與低流量。",
            "把request數公平當CPU/latency公平。",
            "失敗後立即恢復完整權重造成flapping。",
        ],
        [
            "從公平性、burst與恢復需求設計scheduler。",
            "理解weighted fair selection與feedback state。",
            "使用bitmap限制retry搜索空間。",
        ],
        [
            ("Smooth weighted RR比簡單重複列表好在哪裡？", "同樣維持長期比例，但會把低權重peer較均勻插入序列，避免高權重peer連續承受一大段burst。"),
            ("`effective_weight` 和 `weight` 為何分開？", "Weight是配置目標；effective可因失敗暫時下降並漸進恢復，不必修改原始設定。"),
            ("為什麼要扣除total weight？", "Winner已獲得一次服務，扣總量形成債務；未選peer持續累積current，最終會超過winner，達成比例公平。"),
            ("算法能保證每7個request恰好5:1:1嗎？", "在穩定eligible集合下序列接近且週期性，但fail/max_conns/retry、多worker與權重恢復都會改變；保證重點是長期傾向。"),
            ("Shared zone如何影響選擇？", "Peer counters/weights可跨worker共享，分布與max_conns更接近全域狀態；代價是shared locking/atomic與一致性成本。"),
            ("何時不該用weighted RR？", "Request service time高度不均、sticky需求、cache locality或實時latency feedback更重要時，應考慮least_conn/hash/least_time等。"),
        ],
    ),
    C(
        29,
        "其他負載均衡策略",
        "Least connections、hash、consistent hash、random two choices與least time各自優化什麼，又犧牲什麼？",
        "進階",
        "用workload、state locality、feedback freshness與failure remapping比較算法，而不是背directive。",
        ["load balancing", "consistent hashing", "power of two choices"],
        [
            "src/http/modules/ngx_http_upstream_least_conn_module.c:1",
            "src/http/modules/ngx_http_upstream_hash_module.c:1",
            "src/http/modules/ngx_http_upstream_random_module.c:1",
            "src/http/modules/ngx_http_upstream_least_time_module.c:1",
        ],
        r"""
策略                 主要訊號                 適合
round robin           配置權重                 cost近似
least_conn            active connections       長短請求不均
hash/consistent hash  request key              affinity/cache locality
random two            兩個sample後比較         大cluster低選擇成本
least_time            latency + inflight        尾延遲導向

沒有免費午餐：訊號越動態，噪音與同步成本越高。
""",
        """
Least connections以active connection/weight選較空peer，對長request比純count更有回饋；但keepalive、HTTP multiplexing與每connection工作量不同會讓conns只是近似。

Hash用request key維持affinity。普通mod hash在增減節點時大量remap；consistent hash把peer映射到ring，通常只影響鄰近範圍，提高cache locality，但熱門key仍可形成hotspot。

Random two choices從少量sample選較佳者，避免每次掃全cluster；least time用latency與inflight估計完成時間，反應更直接但依賴量測品質、共享狀態與避免追逐瞬時噪音。
""",
        [
            "各module替換upstream `init_upstream/init_peer/get/free/notify` callbacks。",
            "大多策略重用round-robin peer結構的eligibility、failure與backup邏輯。",
            "Hash module可建立consistent-hash points並binary search ring。",
            "Random two先按weight取樣候選，再比較connections等訊號。",
            "Least time維護EWMA/估計與inflight完成通知。",
        ],
        """
選算法前先定義objective：平均latency、p99、cache hit、session affinity、backend utilization或failover stability。不同objective可能互相衝突。

Feedback loop有延遲。Least_conn看到的是當下connections，不知道剛排到backend但尚未反映的成本；latency metric是過去樣本。過度敏感會把流量集體趕向看似最快peer，造成振盪。

Affinity不能替代正確共享session storage。節點失敗、擴縮容、NAT聚合與key skew都會破壞「永遠同一台」的假設。
""",
        r"""
choose(strategy, request):
    if strategy == LEAST_CONN:
        return argmin(peer.conns / peer.weight)
    if strategy == CONSISTENT_HASH:
        return ring.successor(hash(request.key))
    if strategy == RANDOM_TWO:
        a, b = weighted_sample_two()
        return better(a, b)
    if strategy == LEAST_TIME:
        return argmin(estimated_latency(peer) + inflight_penalty(peer))
""",
        [
            "建立短/長request混合流量，比較RR與least_conn p95與分布。",
            "以user id做consistent hash，增減一台backend量測remap比例。",
            "製造熱門key，觀察hash affinity的hotspot。",
            "讓一台backend latency抖動，比較動態策略是否振盪。",
        ],
        [
            "只看算法名稱，不定義優化目標。",
            "把connection count視為精確load。",
            "依賴sticky掩蓋session state設計問題。",
        ],
        [
            "將scheduler問題轉成objective、signal、cost與stability。",
            "理解consistent hashing、sampling與feedback control。",
            "分析key skew、state locality與failure remapping。",
        ],
        [
            ("Least_conn為何可能勝過RR？", "當request/connection持續時間差異大，active count提供工作尚未完成的回饋，避免長工作連續落同peer；但它仍不是CPU queue的完美量測。"),
            ("Consistent hash主要解決什麼？", "節點集合改變時降低key remapping，保留cache/session locality；它不自動解決熱門key或peer capacity差異。"),
            ("Power of two choices為何有效？", "只取少量隨機候選就能大幅降低最壞queue，相比掃全體成本低、共享狀態少；前提是sample與比較訊號合理。"),
            ("Latency-based策略為何可能振盪？", "Metric延遲與噪音讓所有流量追逐暫時最快peer，該peer變慢後再集體轉移。需要EWMA、inflight penalty、randomization與hysteresis。"),
            ("Sticky session能否保證user永遠同一backend？", "不能。節點故障、ring改變、cookie失效或配置更新都會重映射；應把它視為locality optimization，不是資料正確性基礎。"),
            ("怎麼選擇策略？", "先以真實workload定義SLO與constraint，再離線/影子比較分布、p99、remap、failure recovery與state cost；不要只靠平均延遲。"),
        ],
    ),
    C(
        30,
        "Timeout、Failure 與 Retry",
        "某個 backend 失敗時，NGINX 何時能安全換下一台，何時重試反而會造成重複寫入或雪崩？",
        "進階",
        "建立分階段timeout、failure classification、tried peers、idempotency與retry budget模型。",
        ["retry", "idempotency", "failure amplification"],
        ["src/http/ngx_http_upstream.c:4175", "src/http/ngx_http_upstream.c:4510", "src/http/ngx_http_upstream_round_robin.c:924"],
        r"""
attempt 1: peer A
  connect timeout / send error / invalid header / 5xx
       │ classify + policy
       ├─ not retryable → finalize client response
       └─ retryable and tries/time remain
               ↓ free peer state
          reinit protocol
          select untried peer B

危險窗口：A 可能已執行寫入，但response在回程遺失。
""",
        """
Failure不是單一布林值。Upstream core用bitmask區分error、timeout、invalid header、特定HTTP status、no live peers等；location policy決定哪些可進下一peer，以及是否受 non-idempotent request限制。

真正困難是uncertain outcome：POST已完整送到A，A完成付款但response途中斷線。Proxy只看到read timeout，無法知道副作用是否發生；重試B可能重複執行。Idempotency key與backend dedup才是根本解法。

Retries消耗時間與容量。若每層各重試3次，總attempt可乘法放大。需要總deadline、max tries、retry budget、jitter/circuit policy與可觀測attempt history。
""",
        [
            "Connect/send/read/header處將失敗分類傳入 `ngx_http_upstream_next`。",
            "Policy檢查next_upstream flags、tries、timeout與request是否可重試。",
            "呼叫peer free callback更新fails/effective weight/conns。",
            "Protocol reinit並重設buffer/timer，再選未嘗試peer。",
            "耗盡或不可重試時映射最終HTTP status並finalize。",
        ],
        """
Timeout不是越短越好。Connect timeout保護死地址；read timeout通常是兩次read間隔，不一定是整個response總deadline。若只設per-attempt timeout而無總budget，連續重試可遠超client SLO。

Passive health由真實request更新peer fails；低流量時恢復慢，高流量時短暫故障可能快速放大。Backup peers與slow recovery要一起看。

重試前若request body已無法重播，必須停止。Buffered body較容易重播；streaming body可能已消費client bytes且不能倒帶。
""",
        r"""
while (attempts_left && before_deadline()) {
    peer = choose_untried_peer();
    result = try_once(peer);
    record_attempt(peer, result);

    if (result.ok) return result;
    if (!policy.retryable(result.failure)) break;
    if (!request.is_idempotent && result.may_have_committed) break;
    if (!request_body.replayable) break;
}
return final_error();
""",
        [
            "依序製造connect refused、connect timeout、invalid header、502與body途中斷線。",
            "對GET與POST比較next_upstream行為與attempt數。",
            "加入backend idempotency key，模擬response遺失後安全重試。",
            "讓client deadline短於所有attempt總和，找出浪費的zombie work。",
        ],
        [
            "任何5xx都無條件重試。",
            "每層各自重試，形成乘法流量。",
            "只設per-attempt timeout，沒有end-to-end deadline。",
        ],
        [
            "理解at-least-once delivery與uncertain outcome。",
            "設計idempotency、retry budget與deadline propagation。",
            "把failure分類映射成安全policy。",
        ],
        [
            ("為什麼read timeout後不能確定backend沒執行？", "Request可能已到達並完成，只有response遺失或太慢；proxy看不到backend transaction state，因此結果不確定。"),
            ("Buffered request body如何幫助retry？", "完整body仍在memory/temp file，可從頭重新送給新peer；unbuffered streaming可能已消費且無法回放。"),
            ("Idempotent method就一定可安全重試嗎？", "HTTP語意上應無額外副作用，但實際application可能違反，且大response/資源成本仍存在；還需deadline與budget。"),
            ("Retry storm如何形成？", "大量request遇同一慢故障，每個都多次重試，把原流量乘上attempt數，進一步壓垮剩餘健康peers。"),
            ("Passive health的限制？", "依賴真實流量且有觀察延遲；錯誤分類、低流量、局部網路與瞬時尖峰都可能造成誤判。"),
            ("一個完整retry policy要包含什麼？", "Failure分類、method/idempotency、body replayability、max attempts、總deadline、backoff/jitter、peer exclusion、budget與attempt-level telemetry。"),
        ],
    ),
    C(
        31,
        "Upstream Keepalive",
        "Backend response完成後，什麼條件下 socket 可以放進 cache，下一個request又如何安全取出重用？",
        "進階",
        "理解連線快取包裝peer callbacks、LRU/free queue、idle read handler與跨request pool。",
        ["connection pool", "LRU", "resource reuse"],
        ["src/http/modules/ngx_http_upstream_keepalive_module.c:1", "src/http/modules/ngx_http_upstream_keepalive_module.c:207", "src/http/modules/ngx_http_upstream_keepalive_module.c:281"],
        r"""
request N get peer
  ├─ cache hit → detach idle connection
  └─ miss → original balancer + new connect

request N finalize/free peer
  ├─ reusable? → reset data/log/handlers → idle cache queue
  └─ no → original free + close

idle socket readable → peer closed/garbage → remove and close
""",
        """
Keepalive module不重寫所有balancer。它包裝原本peer `get/free` callbacks：get先在cache找同sockaddr idle connection，miss才呼叫原算法；free判斷response與socket是否可重用，符合才把connection放cache。

Cache有free與cache queues；超過容量時淘汰最舊idle connection。Idle socket仍需read handler，因為backend可能主動關閉；readable時用peek/recv判斷EOF或unexpected data並移除。

Connection pool獨立於request pool，才能跨request保存SSL/session/event資源。放回cache前必須移除timers、清request data、設idle handlers；取出時再綁新request/log。
""",
        [
            "Keepalive init保存original peer methods並安裝wrapper。",
            "Get按sockaddr掃cache，命中則標cached並移出queue。",
            "Miss呼叫original get/connect。",
            "Free檢查status、body完整、keepalive flag、timeouts與socket state。",
            "Reusable connection放LRU cache；idle close handler監視peer關閉。",
        ],
        """
Keepalive cache是每worker上限，不是backend總連線上限。Worker數乘上cache size，再加active connections，才接近可能連線數；backend capacity planning必須按全域估算。

Connection reuse會放大 stale connection race：backend在cache後剛關閉，NGINX取出並send才發現broken。正確處理靠idle event檢測與send failure retry，但不能假設cache hit必成功。

長期connection可能遇DNS/backend deployment變更；max requests、time與timeout限制可促進輪替。
""",
        r"""
get_peer(pc):
    if cache.has(pc.address):
        c = cache.take(pc.address)
        reset_for_request(c, current_request)
        pc.connection = c
        pc.cached = true
        return OK
    return original_get(pc)

free_peer(pc, state):
    if reusable(pc, state):
        reset_for_idle(pc.connection)
        cache.put_lru(pc.connection)
    else:
        original_free(pc, state)
""",
        [
            "Backend記錄remote port，連續請求確認connection reuse。",
            "比較每worker keepalive cache與backend實際連線總數。",
            "讓backend在idle期間主動close，觀察idle handler清理。",
            "部署重啟backend，量測stale reuse與retry。",
        ],
        [
            "把keepalive directive當backend最大連線數。",
            "把request pointer留在idle connection。",
            "認為cache hit後socket一定健康。",
        ],
        [
            "理解resource pool wrapper、LRU與per-shard capacity。",
            "安全重設可重用物件，避免跨租戶/跨request狀態洩漏。",
            "處理stale pooled connection與validation race。",
        ],
        [
            ("Keepalive module為何包裝而非取代balancer？", "它只負責connection reuse；peer選擇仍由RR/hash等算法。Wrapper可組合兩種責任並保留original callbacks。"),
            ("Cache size為何不是全域上限？", "每個worker有自己的address space/cache；總idle可能約為workers×size，還不含active與其他upstream groups。"),
            ("Idle connection為何要監視read event？", "Backend可隨時FIN/RST或送unexpected bytes；若不清理，cache會保存已死socket並在下次request才失敗。"),
            ("放回cache前要清哪些狀態？", "Request data/log綁定、read/write handlers、timers、ready/error flags與protocol-specific keepalive條件；connection pool只保留跨request安全資料。"),
            ("如何降低stale connection錯誤？", "Idle close detection、合理timeout/max requests、send failure安全retry、backend graceful drain與觀測reuse failure。無法完全消除close race。"),
            ("Connection reuse對latency的價值？", "省TCP handshake，HTTPS還可能省TLS handshake；但需平衡backend連線容量、負載分布與長連線老化。"),
        ],
    ),
    C(
        32,
        "Buffering、Streaming 與慢速 Client",
        "同一個proxy response為什麼有時先讀完backend再慢慢送client，有時又一邊讀一邊送？",
        "進階",
        "比較buffered event pipe與non-buffered path，理解temp file、busy buffers、latency與connection coupling。",
        ["buffering", "streaming", "event pipe"],
        ["src/event/ngx_event_pipe.c:1", "src/http/ngx_http_upstream.c:3010", "src/http/ngx_http_upstream.c:3488"],
        r"""
buffered:
backend → input bufs → temp file? → output bufs → client
   可較快釋放backend                client可慢

non-buffered:
backend ───────── small buffers ─────────> client
   client慢 ⇒ backend read暫停、connection持有更久
""",
        """
Buffered response使用 event pipe協調upstream read與downstream write。Input buffers、in/out/free/busy chains與temporary file共同形成有界管線；backend可在client慢時較快完成。

Non-buffered path收到資料就交output filter，適合SSE、streaming與降低首塊延遲；但下游blocked時必須停止upstream read，兩條connection生命周期緊密耦合。

`X-Accel-Buffering`、module config、cache/store與response特性會影響路徑。分析問題時先確認實際走buffered還是non-buffered，不要只看directive字面。
""",
        [
            "Response header完成後依 `u->buffering` 選event pipe或non-buffered handlers。",
            "Event pipe配置input filter、output filter、buf數量/大小、busy limit、temp policy。",
            "每輪同時嘗試write downstream、read upstream、spool file並更新events。",
            "Non-buffered handler直接讀入u buffer/chain後呼叫output filter。",
            "兩條路徑都需在EAGAIN時正確arm read/write events與timers。",
        ],
        """
Buffer size不是總memory。要計算每request buffers、busy chains、header buffer、filter額外buffer，再乘concurrency；temp file則把壓力轉到disk與I/O queue。

Streaming不等於零拷貝，也不保證低tail latency。Filter、TLS、HTTP/2 framing、socket buffer仍可copy；小chunk過多還增加syscall與packet overhead。

Cache通常需要較完整的buffer/store語意；真正即時streaming與cache fill可能衝突，需要明確產品選擇。
""",
        r"""
void pump(pipe *p) {
    do {
        progress = false;
        progress |= write_ready_output_to_client(p);
        progress |= move_file_buffers_if_ready(p);

        if (has_input_capacity(p))
            progress |= read_from_upstream(p);

        if (memory_pressure(p))
            progress |= spool_to_temp_file(p);
    } while (progress && within_work_budget());
}
""",
        [
            "用slow client比較buffering on/off的backend完成時間。",
            "限制buffer讓response落temp file，觀察disk I/O與memory。",
            "做SSE endpoint，測量首event與每event延遲。",
            "增加並發量，計算設定推導的memory上限並與RSS比較。",
        ],
        [
            "用單一buffer大小估算總memory。",
            "宣稱streaming就是zero-copy。",
            "忽略小chunk/TLS/filter帶來的額外buffer與syscall。",
        ],
        [
            "設計bounded async pipeline與spooling。",
            "量化latency、throughput、memory、disk與connection occupancy。",
            "辨別產品上的realtime需求與基礎設施buffer策略。",
        ],
        [
            ("Buffering如何縮短backend connection占用？", "NGINX可快速讀走response到memory/disk，讓backend完成並釋放socket，之後按client速度輸出。"),
            ("Non-buffered為何仍需要buffer？", "Socket與filters以chunk運作，partial read/write必須保存bytes；non-buffered指不主動完整吸收/落盤，不是完全零緩衝。"),
            ("Busy buffers limit控制什麼？", "限制已交給downstream filter但尚未可重用的buffer量，避免慢client讓所有input buffers永久被占住。"),
            ("Temp file何時是合理設計？", "Response大、backend快、client慢且memory需有界時；若disk成瓶頸或需求是真即時streaming，則需調整。"),
            ("為何SSE常需要關buffering？", "應用期望每個event盡快到client；中介等待填滿buffer會增加可見延遲。但仍需flush語意與proxy/client backpressure。"),
            ("如何選buffer策略？", "以body size分布、client速度、backend成本、TTFB/p99、memory/disk budget、cache與retry需求做壓測，不能只用通用最佳實務。"),
        ],
    ),
    C(
        33,
        "Proxy Cache",
        "Cache hit為何能繞過backend，cache miss又如何避免大量request同時擊穿同一個key？",
        "進階",
        "理解cache key、metadata、shared zone、file body、loader/manager、lock與stale策略。",
        ["cache", "shared metadata", "thundering herd"],
        ["src/http/ngx_http_cache.h:1", "src/http/ngx_http_file_cache.c:1", "src/http/ngx_http_upstream.c:897"],
        r"""
request → compute cache key → shared metadata lookup
   ├─ HIT   → open cached file → filters → client
   ├─ STALE → policy: serve stale / revalidate
   └─ MISS  → optional key lock
                   │ leader fetches backend
                   └ followers wait/bypass

shared memory: keys/status/usage
disk files: headers + response body
""",
        """
Proxy cache把熱門lookup metadata放shared memory zone，把實際response放filesystem。Worker可跨process協調同一key狀態，而不把大body塞進共享heap。

Key由scheme、method、host、URI等組合；若漏掉會影響representation的header/user維度，可能產生錯誤資料或安全洩漏。反之維度過多降低hit ratio。

Cache lock讓第一個miss成為leader，其餘同key request等待或依policy bypass，降低thundering herd。Stale-while-error/update則用舊資料換可用性，必須接受freshness tradeoff。
""",
        [
            "Upstream init先依config計算key並開啟file cache。",
            "Shared rbtree/queue查metadata、狀態、uses與validity。",
            "Hit讀cache header/body，可能直接完成而不建upstream。",
            "Miss取得lock或等待，leader走正常upstream並寫temp/cache file。",
            "Manager清理inactive/超量cache，loader在啟動時把disk metadata載回shared zone。",
        ],
        """
Cache correctness包含vary、Set-Cookie、Authorization、range、revalidation與purge。簡化成key→bytes容易犯跨使用者洩漏或保存不可cache response。

原子發布通常先寫temporary file，再rename成cache path，避免讀者看到半寫檔；metadata狀態需與file lifecycle協調。

Cache stampede不只發生miss，也發生大量key同時過期。Lock、stale serving、TTL jitter、background update與上游capacity共同處理。
""",
        r"""
response get(request r) {
    key = build_cache_key(r);
    entry = shared_index.lookup(key);

    if (entry.fresh) return read_file(entry.path);
    if (!lock.try_become_leader(key))
        return wait_or_serve_stale(entry);

    response x = fetch_upstream();
    if (cacheable(x))
        atomic_publish(key, write_temp_then_rename(x));
    lock.release(key);
    return x;
}
""",
        [
            "讓backend計數，分別驗證HIT/MISS/EXPIRED/STALE。",
            "100個並發request打同一冷key，比較cache lock on/off的backend次數。",
            "修改cache key漏掉query或user維度，觀察錯誤並立即復原。",
            "停止backend，測試use_stale policy與資料年齡。",
        ],
        [
            "Cache key漏掉影響內容的tenant/auth/language維度。",
            "所有entry同時固定TTL過期造成stampede。",
            "把shared zone大小當disk cache容量。",
        ],
        [
            "理解metadata/data分層、atomic publish與cache coherence。",
            "設計single-flight、stale與TTL jitter。",
            "從correctness/security而不只hit ratio評估cache。",
        ],
        [
            ("為何metadata放shared memory、body放disk？", "跨worker需快速協調key與狀態，但body可能很大；共享區適合小而熱的index，filesystem適合容量與持久資料。"),
            ("Cache key漏維度最嚴重的後果？", "不同使用者或representation命中同entry，可能回錯內容甚至洩漏私人資料；這是correctness與security事故。"),
            ("Cache lock如何減少擊穿？", "同key只允許leader取backend，followers等待、bypass或讀stale；把N次昂貴生成合併為一次single-flight。"),
            ("為何需要stale策略？", "Backend故障或更新中仍可用較舊資料維持可用性與降低尖峰；代價是freshness與需清楚標示的資料時效。"),
            ("Shared zone滿和disk滿有何不同？", "前者無法追蹤更多keys/metadata，即使disk仍有空間；後者限制body容量。兩者需獨立監控與清理。"),
            ("如何避免半寫cache file被讀？", "先寫獨立temp file並完成header/body與fsync policy，再以原子rename發布，同時更新metadata可見狀態。"),
        ],
    ),
]


PART_6 = [
    C(
        34,
        "Memory Pool 與生命週期",
        "NGINX 為什麼大量使用 pool，而不是每建立一個小物件就配對一次 malloc/free？",
        "中階",
        "從request/connection/cycle生命週期推導region allocation，理解small/large allocation、cleanup與限制。",
        ["arena allocation", "lifetime", "cleanup"],
        ["src/core/ngx_palloc.h:1", "src/core/ngx_palloc.c:1", "src/http/ngx_http_request.c:539"],
        r"""
cycle pool ───────────────────────── configuration generation
   ├─ module conf / listeners / paths

connection pool ───────────── TCP connection
   ├─ sockaddr / log / protocol connection state

request pool ─────── one HTTP request
   ├─ headers / module ctx / upstream / chains
   └─ destroy whole pool at request end

生命週期越短的資料，不可被更長生命週期物件引用。
""",
        """
Pool先配置一塊block，small allocations只做alignment與pointer bump；空間不足時串接新block。大配置可能單獨malloc並掛在large list，`ngx_pfree`主要能提早釋放這類large allocation。

價值不只速度，而是lifetime correctness：request內數十個小物件不需分散free；request結束時執行cleanups後整池銷毀。這把ownership從「每個pointer」提升成「region」。

Pool不會自動呼叫任意resource destructor。File、temp file、library handle等需註冊cleanup handler；否則heap bytes釋放了，OS resource仍leak。
""",
        [
            "`ngx_create_pool` 建首block，保存d.last/end/next/failed。",
            "`ngx_palloc` 對small size掃blocks、對齊並bump last。",
            "Block失敗次數高時更新current，避免每次從已滿block掃起。",
            "Large allocation以獨立pointer node追蹤，可由`ngx_pfree`提早free。",
            "`ngx_destroy_pool` 先跑cleanup，再free large與所有blocks。",
        ],
        """
Region allocation犧牲個別小物件回收；若在長生命週期connection pool不斷放request資料，就會像leak一樣成長到connection關閉。選pool比選allocator API更重要。

Pool reset可重用blocks但會使舊pointer失效；所有跨reset引用都危險。Memory sanitizer不一定能立即抓到，因為bytes仍映射。

Cleanup註冊順序與idempotency要清楚。Error path、normal finalize、connection abort可能交錯，cleanup應能辨認resource是否仍open。
""",
        r"""
void *pool_alloc(pool *p, size_t n) {
    if (n <= p->small_limit) {
        for (block *b = p->current; b; b = b->next)
            if (aligned_space(b) >= n)
                return bump_pointer(b, n);
        return add_block_and_allocate(p, n);
    }
    return allocate_large_and_track(p, n);
}

destroy_pool(p):
    run_cleanups(p)
    free_all_large_allocations(p)
    free_all_blocks(p)
""",
        [
            "在一個request中連續palloc小物件，觀察地址與block last移動。",
            "配置超過max的小物件，找large list與`ngx_pfree`。",
            "註冊開檔cleanup，分別從成功與錯誤路徑驗證執行一次。",
            "故意把request資料放connection pool，長keepalive壓測觀察RSS。",
        ],
        [
            "把pool當garbage collector；它不追蹤可達性，也不自動析構外部資源。",
            "從短生命週期pool返回pointer給長生命週期cache。",
            "為方便全部放cycle/connection pool，造成長期成長。",
        ],
        [
            "理解arena/region allocator與ownership tree。",
            "使用lifetime分類降低free複雜度。",
            "辨認resource cleanup與memory release的差異。",
        ],
        [
            ("Pool最大優點只是malloc比較快嗎？", "不是。更大的價值是把同生命週期物件整批釋放，降低error path與ownership複雜度；速度與fragmentation是附帶收益。"),
            ("為什麼small allocation通常不能個別p_free？", "Pool只bump pointer，沒有每個small object的獨立allocator metadata；中間洞也不易有效重用，設計目標是整region回收。"),
            ("什麼資料應放request pool而不是connection pool？", "只服務單一HTTP交換的headers、module ctx、upstream state、body/output chains；keepalive後不再需要就應隨request釋放。"),
            ("Cleanup handler解決什麼？", "釋放file descriptor、temp file、library object等需要動作的resource；純free pool bytes不會自動執行這些副作用。"),
            ("Pool reset後舊pointer為什麼危險？", "Memory可能仍存在但已可被下一allocation覆寫，形成silent use-after-lifetime；不是只有munmap後才算dangling。"),
            ("何時不適合pool？", "物件生命週期差異大、需頻繁個別刪除、長期資料量不可預測或ownership跨region時，專用allocator/refcount可能更清楚。"),
        ],
    ),
    C(
        35,
        "資料結構不是考題，而是設計選擇",
        "Array、list、queue、hash、紅黑樹與radix tree在NGINX裡分別服務哪種workload？",
        "中階",
        "以操作分布、allocation、locality、ordering與prefix lookup選結構，建立可遷移的資料結構判斷表。",
        ["data structures", "workload", "intrusive containers"],
        [
            "src/core/ngx_array.c:1",
            "src/core/ngx_list.c:1",
            "src/core/ngx_queue.h:1",
            "src/core/ngx_hash.c:1",
            "src/core/ngx_rbtree.c:1",
            "src/core/ngx_radix_tree.c:1",
        ],
        r"""
需求                                  NGINX 常用結構
config-time append + runtime scan      ngx_array_t
append很多、地址穩定                   ngx_list_t (分part)
O(1) insert/remove已知節點             ngx_queue_t (intrusive)
字串exact/wildcard lookup              ngx_hash_t
排序、min、任意刪除                    ngx_rbtree_t
IP prefix longest-match                ngx_radix_tree_t

先問操作，再問 Big-O；還要問生命週期與cache locality。
""",
        """
`ngx_array_t` 在pool內連續保存元素；若它恰好是pool最後allocation，可原地擴張，否則配置更大區域並copy。適合設定期逐步收集、之後唯讀遍歷。

`ngx_list_t` 不是傳統每node malloc linked list，而是由固定容量parts串接；每part內元素連續，兼顧append與地址穩定，常用於headers/open files。

`ngx_queue_t` 是intrusive doubly linked ring，適合LRU、posted events、free lists；已知node可O(1)移除。Hash與wildcard hash針對config/runtime名稱查找；rbtree支援timer/cache index；radix tree適合IPv4/IPv6 prefix。
""",
        [
            "閱讀每個struct的layout，先列出提供的operations而非實作。",
            "找一個真實caller，記錄資料何時建立、是否runtime修改。",
            "比較allocation方式：連續、分part、intrusive embedded node。",
            "分析lookup key：string exact、ordered numeric、prefix bit sequence。",
            "最後才比較time complexity、memory overhead與cache locality。",
        ],
        """
資料結構可組合：file cache用rbtree做key lookup、queue做LRU；同一cache node內嵌tree node與queue link。這是「一份資料，多個index」的典型設計。

Config-time structures可接受較昂貴build，以換runtime compact lookup。NGINX hash builder會嘗試bucket size，避免每request動態resize；這是讀多寫少workload。

Intrusive結構要求物件不能在仍掛queue/tree時被釋放，也不能同一link同時進兩條queue；狀態discipline比wrapper container嚴格。
""",
        r"""
typedef struct cache_node {
    rb_node   by_key;       /* lookup index */
    queue_link lru;         /* eviction order */
    string    key;
    value     data;
} cache_node;

lookup(key)  -> rbtree/hash
touch(node)  -> queue_remove(&node->lru), queue_insert_head(...)
evict()      -> container_of(queue_tail(), cache_node, lru)
""",
        [
            "為headers、timers、LRU、IP allowlist各選一個結構並說明操作需求。",
            "找file cache node同時參與rbtree與queue的欄位。",
            "比較100個元素array scan與hash在build成本、memory、cache miss。",
            "故意把同一queue link插兩次，在小測試理解結構損壞。",
        ],
        [
            "只用漸進Big-O，不看元素數、build頻率與cache locality。",
            "認為`ngx_list_t`是每元素一個heap node。",
            "移除intrusive object前忘記先unlink所有indexes。",
        ],
        [
            "以workload與資料生命週期選資料結構。",
            "理解multi-index object與intrusive container。",
            "平衡build-time cost、runtime lookup與memory layout。",
        ],
        [
            ("Header為什麼常用part-based list而非單一array？", "Header數量不確定且element地址需穩定；分part可append不搬移既有元素，同時每part仍連續，少於每node allocation。"),
            ("Timer為什麼不用hash？", "Scheduler需要最小deadline與有序到期，不只exact lookup；hash無法有效取得全域minimum。"),
            ("File cache為何同時要tree與queue？", "Tree按key快速找entry，queue按最近使用順序淘汰；兩種index服務不同操作。"),
            ("Radix tree比普通hash適合IP policy在哪裡？", "CIDR需要longest-prefix match，不是完整key exact match；radix沿bit prefix自然表示包含關係。"),
            ("Config-time hash為何可不做動態resize？", "設定reload時key集合已知，可一次計算bucket layout；runtime主要唯讀，避免鎖與resize。"),
            ("何時線性array反而勝hash？", "元素很少、遍歷頻繁、build一次、cache locality重要時；hash的pointer/bucket與hash計算常數可能更高。"),
        ],
    ),
    C(
        36,
        "Buffer、Chain 與 Zero-Copy 思維",
        "一段response可以同時引用memory與file，NGINX如何在不複製全部資料的情況下組合並部分送出？",
        "進階",
        "理解buffer是range descriptor、chain是scatter/gather計畫、sendfile/writev與shadow/flags ownership。",
        ["buffer", "scatter/gather", "zero-copy"],
        ["src/core/ngx_buf.h:1", "src/core/ngx_buf.c:1", "src/core/ngx_output_chain.c:1", "src/os/unix/ngx_writev_chain.c:1"],
        r"""
chain
  ├─ buf A: memory [pos,last)  "HTTP/1.1 ..."
  ├─ buf B: file   [file_pos,file_last) static.bin
  └─ buf C: memory [pos,last)  "\r\n"

writev(memory ranges) / sendfile(file range)
partial write → advance only sent ranges → keep remaining chain
""",
        """
`ngx_buf_t` 不擁有固定類型的byte array；它描述memory range、file range或控制訊號。`pos/last` 是目前可送memory區間，`file_pos/file_last`是file區間，start/end則是可重用storage邊界。

`ngx_chain_t` 將buffers串成輸出計畫。Output chain可合併相鄰memory做writev，或用sendfile直接從page cache到socket路徑，並在partial send後更新各range。

Zero-copy是程度而不是絕對。TLS、gzip、filter transformation、unaligned boundary與platform可能需要copy；真正目標是避免不必要copy並保持ownership正確。
""",
        [
            "Content/filter建立memory/file buffers並串成chain。",
            "`ngx_output_chain` 判斷是否可直接傳、需copy、directio或thread read。",
            "OS-specific send chain組iovec或file segment，受limit控制。",
            "Syscall回傳已送bytes，`ngx_chain_update_sent`推進range。",
            "未送完chain留在busy/output，等write readiness繼續。",
        ],
        """
Buffer flags是protocol：`temporary`表示可修改memory，`memory/mmap`通常不可覆寫，`recycled`提示backpressure，`flush/sync/last_buf`沒有bytes也有控制語意。只copy pointer不copyflags會破壞pipeline。

Shadow buffer允許不同view引用同一storage；只有最後consumer完成才能回收。這和Rust borrow、slice與reference lifetime有相同問題，只是C靠discipline。

Sendfile減少user-space copy，但如果client很慢，file pages與socket仍受backpressure；`sendfile_max_chunk`可避免單connection長時間霸占worker。
""",
        r"""
typedef struct {
    unsigned char *pos, *last;    /* current memory range */
    off_t file_pos, file_last;    /* current file range */
    unsigned memory:1, in_file:1;
    unsigned flush:1, last_buf:1;
} buffer;

ssize_t n = send_chain(fd, chain, budget);
chain = advance_ranges_by(chain, n);
if (chain) wait_for_writable(fd);
""",
        [
            "用靜態大檔比較writev與sendfile syscall trace。",
            "限制client速度，在多次sendfile後檢查file_pos前進。",
            "寫filter保留input buffer，驗證何時可放回free chain。",
            "開TLS比較sendfile路徑與CPU/copy變化。",
        ],
        [
            "把buffer當必然擁有memory的容器。",
            "只更新chain pointer，不更新partial buffer range。",
            "宣稱sendfile在所有TLS/filter場景都是zero-copy。",
        ],
        [
            "掌握slice/range、scatter-gather與partial progress。",
            "理解ownership flags與shared backing storage。",
            "用syscall budget維持event-loop公平性。",
        ],
        [
            ("`pos/last` 和 `start/end` 有何不同？", "前者是目前有效/未消費資料範圍；後者是整塊可用storage邊界。Partial write推進pos，不應改start。"),
            ("File buffer如何不先把整檔讀進user memory？", "它保存fd與file offset，OS-specific output可用sendfile；只有filter/TLS/directio條件要求時才copy/read。"),
            ("零長度buffer是否一定可丟棄？", "不一定。Flush、sync、last_buf等控制flags即使無bytes也會改變下游行為。"),
            ("Partial write後如何續送？", "按回傳byte數跨chain逐段前進memory/file positions，完整消費的link移出，剩餘chain在下次writable繼續。"),
            ("Shadow buffer最大風險？", "多個descriptor共享storage，若其中一個過早回收或修改，其他view變成dangling/corrupt；需明確last shadow與busy ownership。"),
            ("Sendfile為何仍需chunk limit？", "單次可送大量ready file data，handler可能長時間占CPU/kernel work；限制每輪bytes讓其他connections獲得排程。"),
        ],
    ),
    C(
        37,
        "Shared Memory、Slab、Atomic 與 Lock",
        "Worker彼此heap隔離時，rate limit、cache metadata與upstream state如何共享？",
        "進階",
        "理解mmap shared zone、slab allocator、process-shared mutex、atomic與一致性邊界。",
        ["shared memory", "slab allocator", "synchronization"],
        ["src/os/unix/ngx_shmem.c:1", "src/core/ngx_slab.c:1", "src/core/ngx_shmtx.c:1", "src/os/unix/ngx_atomic.h:1"],
        r"""
worker 0 heap      worker 1 heap
     X                  X        彼此不可見
      \                /
       ┌────────────────────┐
       │ mmap shared zone   │
       │ slab pool + mutex  │
       │ rbtree/queue/data  │
       └────────────────────┘

Pointer只在所有process映射相容時才可共享；reload還要考慮schema。
""",
        """
Fork後普通heap是copy-on-write，各worker修改不會互見。需要全域協調的module建立named shared memory zone；zone init callback在首次建立或reload重用時初始化資料結構。

Shared zone內常放`ngx_slab_pool_t`，用page與slot classes管理小物件。因多process同時配置/修改，需process-shared mutex或atomic。Lock保護的是invariant，不只是某一行assignment。

Atomic適合counter/flag等簡單狀態，不代表整個複合操作原子。Rbtree插入、queue移動、allocate＋publish通常仍需鎖。
""",
        [
            "Config-time以name/size/tag註冊shared memory zone。",
            "Cycle init建立或重用mmap區，呼叫module zone init callback。",
            "Slab pool在shared bytes內管理free pages/slots。",
            "Worker取得shared mutex後修改tree/queue/counters。",
            "Reload以old data pointer協助保留相容狀態。",
        ],
        """
Shared pointer的有效性依賴mapping。若process將同一區映在不同地址，內部絕對pointer可能失效；NGINX平台策略與reload重用需仔細處理。通用跨process格式更偏好offset。

鎖的臨界區應短，不能在持shared mutex時做DNS、disk或network I/O。Worker crash持鎖也是設計考量，shmtx實作需有owner/force unlock等機制。

False sharing會讓不同worker更新同一cache line上的counter互相失效；高頻統計可分worker sharding再聚合。
""",
        r"""
shared_update(zone *z, key k) {
    lock(&z->slab->mutex);

    node *n = rbtree_lookup(z->tree, k);
    if (!n) {
        n = slab_alloc_locked(z->slab, sizeof(*n));
        initialize(n, k);
        rbtree_insert(z->tree, n);
    }
    n->counter++;

    unlock(&z->slab->mutex);
}
""",
        [
            "建立limit zone，以多worker壓測並觀察共享counter。",
            "找zone init callback，理解old data在reload時用途。",
            "在小實驗比較atomic counter與lock-protected tree update。",
            "把昂貴sleep放臨界區觀察所有worker延遲，再移除。",
        ],
        [
            "以為fork後global variable會自動共享。",
            "用atomic更新複合tree/queue invariant。",
            "持shared lock執行可能阻塞的I/O。",
        ],
        [
            "理解process memory model、mmap與copy-on-write。",
            "選擇atomic、mutex、sharding與eventual aggregation。",
            "設計shared-memory schema與reload compatibility。",
        ],
        [
            ("普通global variable為何不能跨worker共享更新？", "Fork後各process有獨立virtual address space，頁面在寫入時copy-on-write；看似同地址但物理/內容分離。"),
            ("Slab allocator解決什麼？", "在固定shared zone內管理不同大小小物件，避免使用process-private malloc metadata，並能在共享鎖下配置/回收。"),
            ("Atomic counter能否保護rbtree插入？", "不能。Tree插入涉及多個pointer/color與可能旋轉，需要整體invariant原子可見；單欄位atomic不足。"),
            ("Shared lock臨界區為何要短？", "任何worker持鎖過久都阻塞其他process，將局部慢操作變成全域tail latency；I/O更可能無界。"),
            ("Reload如何保留shared zone資料？", "以name/size/tag判斷相容並把old zone data交新init callback；新generation重建config view但可沿用共享bytes。"),
            ("如何降低高頻counter的contention？", "每worker/local shard累積後週期聚合、cache-line padding、採樣或無鎖近似；精確全域值與吞吐需取捨。"),
        ],
    ),
    C(
        38,
        "Module System 與可擴充架構",
        "一個第三方模組如何加入directive、phase handler、filter或upstream算法，而不修改core主流程？",
        "進階",
        "理解`ngx_module_t`、module context、command table、lifecycle hooks、ctx index與動態模組邊界。",
        ["plugin architecture", "module lifecycle", "dependency inversion"],
        ["src/core/ngx_module.h:1", "src/core/ngx_module.c:1", "src/http/ngx_http_config.h:1", "src/http/ngx_http.c:186"],
        r"""
ngx_module_t
  ├─ type: CORE / EVENT / HTTP / STREAM ...
  ├─ ctx: type-specific lifecycle callbacks
  ├─ commands: directive table
  ├─ init_module / init_process / exit_process ...
  └─ index / ctx_index

HTTP module hooks:
preconfiguration → create conf → parse/merge → postconfiguration
request time: phase / content / variable / filter / upstream callbacks
""",
        """
`ngx_module_t` 是通用module descriptor；`ctx` 依module type指向HTTP/event/core專用context。HTTP context提供pre/post configuration與main/srv/loc config create/merge callbacks。

Module index用於全域module arrays，`ctx_index`用於同type config/ctx arrays。Request取得某module loc conf，本質是以ctx_index索引 `r->loc_conf`。

擴充點很多但責任不同：directive建設定；phase處理控制流；content產生response；variable提供惰性值；filter改輸出；upstream peer callbacks改選擇。好module選最窄extension point，不攔截不必要階段。
""",
        [
            "Build/static或dynamic load安排module list與index。",
            "Cycle init呼叫core/module create config與解析commands。",
            "HTTP block建立每HTTP module的main/srv/loc conf。",
            "Merge後postconfiguration把handlers/filters註冊進runtime pipeline。",
            "Worker init/exit hooks建立與釋放per-process資源。",
        ],
        """
Module ABI與conditional fields使binary compatibility敏感；dynamic module需匹配build signature。不能只看C symbol可載入就假設layout相容。

Hook ordering是隱含dependency。Filter top/next取決於初始化順序，phase handlers push順序也會影響執行。Module若依賴另一module的side effect，應有清楚contract或在config階段檢查。

Context allocation遵循生命週期：configuration在cycle pool，request ctx在r->pool，process-local library handle在init_process/exit_process管理，shared state在zone。
""",
        r"""
ngx_module_t my_module = {
    .ctx      = &my_http_module_ctx,
    .commands = my_directives,
    .type     = NGX_HTTP_MODULE,
    .init_process = my_worker_init,
    .exit_process = my_worker_exit,
};

postconfiguration(cf):
    phases[ACCESS].handlers.push(my_access_handler)
    return OK
""",
        [
            "挑一個小module，從module descriptor走到command與request handler。",
            "找module的ctx_index如何取得loc conf與request ctx。",
            "比較phase、content、filter三種註冊點。",
            "建立dynamic module，刻意用不匹配binary測試signature檢查。",
        ],
        [
            "把所有功能塞content handler，繞過適合的phase/filter擴充點。",
            "把process-local pointer放shared zone或反之。",
            "依賴未保證的module初始化順序。",
        ],
        [
            "理解plugin registry、lifecycle hooks與dependency inversion。",
            "選擇最小、最穩定的extension seam。",
            "管理config/request/process/shared四種state scope。",
        ],
        [
            ("`index` 和 `ctx_index` 有何差別？", "Index辨認全域module位置；ctx_index是在同一module type內索引config/request ctx arrays，讓HTTP取得設定近似O(1)。"),
            ("Postconfiguration通常做什麼？", "在設定已解析/merge後註冊phase handlers、filters、variables等runtime pipeline，並可驗證跨directive條件。"),
            ("為何module要有init_process而不只init_module？", "有些resource每worker獨立，如thread/library handle、timer或fd；master初始化後fork與每process初始化語意不同。"),
            ("Dynamic module為何需build compatibility？", "Core struct layout、feature macros、pointer size與module signature需一致，否則函式可找到但資料layout錯誤。"),
            ("如何選phase handler或filter？", "要拒絕/授權request選phase；要生成內容選content；要轉換其他module輸出選filter。選最符合責任的seam。"),
            ("Module state放哪裡？", "固定設定放cycle config；單request可變狀態放request ctx；單worker資源放process scope；跨worker資料放shared zone並同步。"),
        ],
    ),
]


PART_7 = [
    C(
        39,
        "實作 Hello Content Module",
        "如何寫出第一個真正被location選中、建立response並安全送出的HTTP模組？",
        "實作",
        "走完directive、loc config、content handler、header/body output與dynamic-module build的最小閉環。",
        ["content handler", "dynamic module", "response"],
        ["src/http/modules/ngx_http_empty_gif_module.c:1", "src/http/modules/ngx_http_stub_status_module.c:1", "auto/module:1"],
        r"""
nginx.conf: hello "NGINX";
       │ directive callback
       ▼
location conf { text = "NGINX"; handler = hello_handler }
       │ request location match
       ▼
hello_handler(r)
  ├─ method check
  ├─ set status/content-type/content-length
  ├─ send header
  └─ output one memory buffer with last_buf
""",
        """
第一個module應只做一件事：在location中啟用後回固定文字。這個練習把設定期與request期串起來，並強迫你正確處理method、header、buffer與return code。

Loc config保存文字。Directive callback解析參數並把core loc conf的handler設成自己的content handler。Request到來時配置temp buffer、寫內容、設`last_buf`，先送header再用`ngx_http_output_filter`送chain。

即使只是Hello也要處理HEAD：可以送headers但不必body；Content-Length仍描述GET表示的長度。不要直接對client fd呼叫write，否則繞過TLS、HTTP/2與filter chain。
""",
        [
            "建立module descriptor、HTTP context與command table。",
            "Create loc conf配置並設UNSET；directive callback填文字並安裝handler。",
            "Handler驗證GET/HEAD，discard不需要的request body。",
            "設定`headers_out.status/content_type/content_length_n`。",
            "配置buffer/chain，標`last_buf`並呼叫top output filter。",
        ],
        """
Dynamic module的`config`檔告訴build system名稱、type與sources。使用和目標NGINX相容的source/configure flags編譯，再用`load_module`載入。

Handler返回值要依output API contract。`ngx_http_send_header`可能表示header-only或error；body output後通常返回filter結果。不要既return HTTP status又另外send一份response造成double finalize。

內容放request pool，output filter可能在handler返回後仍引用；stack buffer或立即free的heap不可用。
""",
        r"""
static ngx_int_t hello_handler(ngx_http_request_t *r) {
    ngx_str_t text = ngx_string("hello nginx\n");
    if (!(r->method & (NGX_HTTP_GET|NGX_HTTP_HEAD)))
        return NGX_HTTP_NOT_ALLOWED;

    r->headers_out.status = NGX_HTTP_OK;
    r->headers_out.content_type = ngx_string("text/plain");
    r->headers_out.content_length_n = text.len;

    ngx_int_t rc = ngx_http_send_header(r);
    if (rc == NGX_ERROR || r->header_only) return rc;

    ngx_buf_t *b = ngx_create_temp_buf(r->pool, text.len);
    b->last = ngx_cpymem(b->last, text.data, text.len);
    b->last_buf = 1;
    ngx_chain_t out = { b, NULL };
    return ngx_http_output_filter(r, &out);
}
""",
        [
            "建立`ngx_http_hello_module`目錄、source與config檔，編成dynamic module。",
            "加入`load_module`與`location /hello { hello \"NGINX\"; }`。",
            "用GET、HEAD、POST驗證status、length與body。",
            "開gzip與HTTP/2，證明handler沒有直接依賴socket write。",
        ],
        [
            "使用stack上的body在handler返回後被filter引用。",
            "忘記last_buf，response不完成。",
            "直接write fd，繞過filter/TLS/protocol framing。",
        ],
        [
            "完成plugin從config到runtime的端到端閉環。",
            "正確使用framework output contract與request lifetime。",
            "用最小功能建立可擴充、可測試的垂直切片。",
        ],
        [
            ("為什麼要設定Content-Length？", "讓HTTP framing明確，HEAD也能描述GET的representation；若使用chunked/filter改寫，header filter可能調整，但module應提供正確已知長度。"),
            ("Body為何要從request pool配置？", "Output可能因client慢而跨event存活；stack在handler返回後失效，request pool保證到finalize前有效。"),
            ("HEAD request應如何處理？", "設定與GET相同的status/content headers，send header後因`r->header_only`不送body。"),
            ("為什麼不用`send()`？", "Top filter處理HTTP版本、TLS、chunking、gzip、range、partial write與backpressure；直接send會破壞所有抽象。"),
            ("Directive如何讓location使用handler？", "Set callback取得core loc conf，將其handler function pointer設為module content handler；location match後content phase呼叫它。"),
            ("如何證明module遵守非阻塞模型？", "用slow client/HTTP2/TLS測試，handler只建立buffers交filter，partial output由write event續送，沒有blocking loop。"),
        ],
    ),
    C(
        40,
        "實作 Access Phase Module",
        "如何在content handler之前依header拒絕request，並正確使用`NGX_DECLINED`與HTTP status？",
        "實作",
        "實作簡單API key gate，理解phase registration、config inheritance、constant-time比較與fail-closed。",
        ["access phase", "authorization", "short circuit"],
        ["src/http/modules/ngx_http_access_module.c:1", "src/http/modules/ngx_http_auth_basic_module.c:1", "src/http/ngx_http_core_module.c:928"],
        r"""
postconfiguration
  phases[NGX_HTTP_ACCESS_PHASE].handlers.push(api_key_handler)

request
  ├─ module未啟用 → NGX_DECLINED
  ├─ key正確     → NGX_OK / phase checker繼續
  └─ key缺失/錯  → 401/403 → finalize

satisfy any/all 會影響多個access modules如何合併。
""",
        """
Access module不生成正常內容，而是在access phase做決策。Loc config保存是否啟用與expected secret來源；handler取request header，未啟用回DECLINED，驗證失敗回HTTP status。

回OK還是DECLINED要看你希望的語意與access checker。DECLINED表示本module不做決定；OK表示此access check通過，但`satisfy any/all`和其他modules仍由checker聚合。

真實認證不應把plaintext secret直接放容易暴露的config/log，也不應用可觀察timing比較高價值token。練習重點是phase/lifetime，不是自製production auth。
""",
        [
            "Create/merge loc conf保存enabled與key reference。",
            "Postconfiguration把handler加入ACCESS phase handlers array。",
            "Handler找自訂header，處理missing/duplicate/invalid。",
            "比較成功後回適當control code；失敗回401/403。",
            "測試與allow/deny、auth basic及`satisfy`的組合順序。",
        ],
        """
Fail-open/fail-closed需顯式決定。若外部auth subrequest timeout，安全系統通常fail closed，但可用性與緊急bypass需另設受控機制。

Header lookup可在known headers外掃generic list；若高頻使用，可註冊variable或預計算hash。永遠限制值長度並避免log secret。

Access decision可能需要async subrequest；此時handler要增加引用、保存ctx、返回suspension code，callback再恢復phase engine，不能block等遠端。
""",
        r"""
ngx_int_t api_key_access(ngx_http_request_t *r) {
    conf_t *cf = get_loc_conf(r);
    if (!cf->enabled) return NGX_DECLINED;

    ngx_str_t supplied = find_header(r, "X-API-Key");
    if (supplied.len == 0) return NGX_HTTP_UNAUTHORIZED;
    if (!constant_time_equal(supplied, cf->expected))
        return NGX_HTTP_FORBIDDEN;
    return NGX_OK;
}
""",
        [
            "加入`api_key`directive與access handler，測missing/wrong/correct。",
            "與`allow/deny`及`satisfy any/all`組合，記錄phase結果。",
            "確認access log/error log沒有輸出secret。",
            "把驗證改成auth subrequest，實作非阻塞resume。",
        ],
        [
            "未啟用時回OK，意外繞過其他access modules。",
            "阻塞呼叫遠端auth服務。",
            "把secret完整寫入debug/error log。",
        ],
        [
            "理解middleware short-circuit與多policy聚合。",
            "設計fail-open/fail-closed與async authorization。",
            "處理secret comparison、logging與configuration scope。",
        ],
        [
            ("未啟用module為何通常回DECLINED？", "表示本module不參與決策，讓同phase其他handlers繼續；回OK可能被`satisfy any`當成已通過。"),
            ("401和403應如何區分？", "401通常表示需要/缺少有效authentication並可帶WWW-Authenticate；403表示已理解身份或憑證但不允許。實際API policy需一致。"),
            ("外部auth為何不能同步HTTP呼叫？", "Worker event loop會被阻塞，所有同worker connections受影響；應用subrequest/async upstream並在callback恢復。"),
            ("Constant-time比較能解決所有token安全嗎？", "不能。它只降低某些timing side channel，仍需TLS、secret storage、rotation、length limit、rate limit與不記錄敏感值。"),
            ("Config inheritance要注意什麼？", "區分未設定、off與空值；child explicit設定應覆蓋parent，secret不可意外從不相關location繼承。"),
            ("如何測fail-closed？", "讓auth backend timeout、連線失敗、回invalid response，確認protected route拒絕且無fallback繞過，同時保留可觀測error。"),
        ],
    ),
    C(
        41,
        "加入自訂 Variable 與 Header Filter",
        "如何讓`$request_id_short`可被log/config使用，並在response中安全加入一個header？",
        "實作",
        "理解variable註冊與惰性求值、not_found/no_cacheable flags，以及header filter鏈。",
        ["variables", "lazy evaluation", "header filter"],
        ["src/http/ngx_http_variables.c:1", "src/http/modules/ngx_http_headers_filter_module.c:1", "src/http/ngx_http_header_filter_module.c:1"],
        r"""
configuration:
register "$request_id_short" → get_handler

runtime consumer (log/header/script)
      ↓ evaluate variable lazily
get_handler(r, value, data)
      ↓ value { data, len, valid, not_found, no_cacheable }

response:
my_header_filter(r) → add X-Request-ID → next_header_filter(r)
""",
        """
NGINX variable不是普通全域字串。Config-time註冊名稱與get/set handler；runtime只有consumer實際需要時才計算，結果可能cache在request variables array。

Get handler填`ngx_http_variable_value_t`的data/len與valid/not_found/no_cacheable。資料必須活到使用者完成，通常放request pool；不可回傳stack pointer。

Header filter可讀variable並push到`headers_out.headers`，然後呼叫next filter。它需避免重複執行時加入兩份、處理subrequest與header already sent狀態。
""",
        [
            "Preconfiguration或module init呼叫add variable，設定get handler。",
            "Config compiler將變數名轉為index或script opcode。",
            "Runtime第一次取值呼叫get handler並保存value metadata。",
            "Header filter在top chain中執行，按條件加入table element。",
            "呼叫next header filter完成protocol encoding。",
        ],
        """
Variable cacheability影響一致性。若值在request期間不變，可cache；若每次讀取可能變，設no_cacheable讓consumer重算。錯設會得到stale或浪費CPU。

Request ID應在request早期一次生成並保存ctx，variable與header filter讀同一值；若兩邊各自生成，log與response無法關聯。

Header value是untrusted時需拒絕CR/LF，避免response splitting。NGINX核心有驗證，但module仍應限制來源與長度。
""",
        r"""
ngx_int_t get_request_id(ngx_http_request_t *r,
                         ngx_http_variable_value_t *v,
                         uintptr_t data) {
    ctx_t *ctx = get_or_create_request_ctx(r);
    v->data = ctx->id.data;
    v->len = ctx->id.len;
    v->valid = 1;
    v->not_found = 0;
    v->no_cacheable = 0;
    return NGX_OK;
}
""",
        [
            "註冊變數並放進access_log format，確認惰性求值。",
            "加入header filter，把同一ID送到response。",
            "同一request多次引用變數，確認只生成一次。",
            "建立subrequest，決定共用main ID或產生child ID並測試。",
        ],
        [
            "Variable返回stack buffer。",
            "Log與response各生成不同request ID。",
            "Filter每次重入都追加header。",
        ],
        [
            "理解惰性值、memoization與cacheability contract。",
            "在pipeline中建立一致correlation ID。",
            "安全擴充header並處理重入/subrequest。",
        ],
        [
            ("Variable為什麼惰性求值？", "大量已註冊variables並非每request都使用；只有log/script/header真正引用時才付出計算與allocation成本。"),
            ("`not_found` 與空字串差在哪裡？", "Not found表示值不存在，可能影響rewrite條件與default；空字串是存在但長度零，語意不可混淆。"),
            ("何時設`no_cacheable`？", "值在同一request不同讀取時間可能改變時；若request-stable應允許cache以保持一致並省成本。"),
            ("Header filter如何避免重複加入？", "用module ctx flag、先查既有header或限定main request/首次header path；理解filter可能因internal flow被再次觸發。"),
            ("Request ID資料應放哪裡？", "放request pool/module ctx，生命週期覆蓋log與output；若需跨服務，header value需穩定且長度受限。"),
            ("Subrequest應共用ID嗎？", "取決於trace模型。常見做法共用trace/root ID並另有span/child ID；必須明確，避免log關聯混亂。"),
        ],
    ),
    C(
        42,
        "實作 Streaming Body Filter",
        "如果response被任意切成多個buffer，如何逐chunk轉換文字而不破壞跨chunk匹配、flush與backpressure？",
        "實作",
        "完成一個可跨buffer保存狀態的stream filter，處理partial token、shadow/copy、flags與subrequest。",
        ["streaming transform", "cross-buffer state", "backpressure"],
        ["src/http/modules/ngx_http_sub_filter_module.c:1", "src/http/modules/ngx_http_gzip_filter_module.c:1", "src/http/ngx_http_copy_filter_module.c:1"],
        r"""
input chunks:  "hello NG" | "INX world" | last
pattern:       "NGINX"

ctx keeps suffix "NG"
next chunk completes match
output: "hello [server] world"

每次filter可能：
consume部分input / 保存suffix / 產生out chain / 等downstream
""",
        """
串流filter不能假設pattern落在單一buffer。Module ctx要保存最多pattern length-1的suffix或parser state，下一chunk到來再繼續。這和incremental HTTP parser是同一思想。

若修改長度，Content-Length需清除或重算，ETag/range/content encoding也可能失效。Header filter先判斷content type/status並建立ctx，body filter才轉換。

下游可能返回AGAIN並保留out buffers。Module需管理free/busy/out chains；不能立刻重用仍被next filter引用的storage。Flush、sync、last flags必須映射到正確最後輸出。
""",
        [
            "Header filter決定是否啟用，調整Content-Length/ETag並建立ctx。",
            "Body filter逐input buffer讀取，結合pending suffix。",
            "產生request-pool或可管理的output buffers，保留control flags。",
            "呼叫next filter後更新busy/free chains與已消費位置。",
            "Last input到來時flush pending suffix並傳last_buf/last_in_chain。",
        ],
        """
原地修改只適用temporary且有足夠空間、不改長度、沒有其他shadow owner。初學實作應產生新buffer，先以正確性為主。

Compression順序很重要。若filter位於gzip後，看到的是compressed bytes；通常文字轉換需在compression前。Dynamic module排序需驗證，不能假設。

Streaming parser要限制pending state大小。若等待delimiter而無上限，攻擊者可用沒有終止符的stream造成memory growth。
""",
        r"""
body_filter(r, in):
    ctx = get_ctx(r)
    for each buffer b in in:
        feed(ctx.parser, b.pos, b.last)
        while parser has output:
            append_new_buffer(ctx.out, parser.take_output())
        preserve_flush_and_last_semantics(ctx, b)
        b.pos = b.last

    rc = next_filter(r, ctx.out)
    update_free_busy_chains(ctx, rc)
    return rc
""",
        [
            "先做不改長度的大寫filter，再進階跨chunk字串替換。",
            "用backend刻意把pattern拆在不同write中。",
            "以slow client測downstream AGAIN與busy chain。",
            "開gzip、subrequest、HEAD、empty body測試filter條件。",
        ],
        [
            "只搜尋每個buffer，漏掉跨邊界pattern。",
            "下游尚未完成就覆寫/reuse output。",
            "改body長度卻保留舊Content-Length。",
        ],
        [
            "實作incremental streaming algorithm。",
            "管理pipeline ownership、flush與partial consumption。",
            "理解內容轉換與protocol metadata的一致性。",
        ],
        [
            ("跨buffer pattern如何處理？", "保存可成為pattern前綴的尾端狀態，與下一chunk繼續automaton；不能無界保存全部歷史。"),
            ("為什麼header filter也要參與？", "Body長度、ETag、range與content encoding metadata可能因轉換失效；須在headers送出前調整。"),
            ("何時可以原地修改buffer？", "Buffer標記temporary、storage可寫、無共享shadow、轉換不超容量且不破壞其他consumer時；否則建立新buffer。"),
            ("下游返回AGAIN意味input已完全消費嗎？", "不一定只看return code；需依filter contract與buffer positions/free-busy chains判斷。通常已交出的out仍可能被引用。"),
            ("Filter如何處理last buffer？", "先輸出pending parser state，再把last_buf或last_in_chain放到真正最後的output buffer，確保下游完成。"),
            ("如何防止stream parser memory DoS？", "限制pending token/prefix大小、總輸出擴張比例與buffer數，遇非法/過長輸入fail或pass-through。"),
        ],
    ),
    C(
        43,
        "實作簡化版 Load Balancer",
        "如何新增一個`first_two_least_conn`策略，又不重寫connection、retry與health邏輯？",
        "實作",
        "實作`init_upstream/init_peer/get/free`，重用round-robin peer eligibility，並測公平、失敗與並發。",
        ["peer callbacks", "scheduler", "shared state"],
        ["src/http/modules/ngx_http_upstream_random_module.c:1", "src/http/modules/ngx_http_upstream_least_conn_module.c:1", "src/http/ngx_http_upstream_round_robin.c:486"],
        r"""
configuration: first_two_least_conn;
      ↓ init_upstream
prepare peer set / wrap round-robin init
      ↓ per request init_peer
allocate request peer data + tried bitmap
      ↓ get
sample eligible A,B → compare conns/weight → choose
      ↓ free
decrement conns / report failed state
""",
        """
自訂balancer不應自己建立socket。它實作peer interface：config-time指定upstream init，per-request配置peer data，get callback選候選並填sockaddr/name，free callback更新狀態。

可重用round-robin初始化、locks、eligibility與peer structures，避免漏掉down、max_fails、max_conns、backup、DNS resolve與shared zone。簡化算法只替換「eligible peers中選誰」。

Power-of-two類策略需處理只有一個peer、sample重複、tried bitmap、weight與tie-break。測試不只看平均分布，也看長request、peer failure、backup與多worker。
""",
        [
            "Directive set upstream `peer.init_upstream`。",
            "Init upstream先呼叫/重用round-robin建立peers，再安裝per-request init。",
            "Per-request init配置自訂data並保留RR data/tried bitmap。",
            "Get在lock內sample/過濾/選擇，增加conns並填pc。",
            "Free委派或等價更新RR failure/conns state。",
        ],
        """
Lock範圍需涵蓋讀取conns與increment選擇，否則多worker shared zone可能同時認為同peer最空。又不能在鎖內做random entropy、log大量資料或connect。

Random seed與測試重現要分開：production可使用合適PRNG state；unit/simulation應可固定seed，才能驗證分布與corner cases。

Scheduler correctness包括不選本次tried/down peer、tries遞減與free恰好一次。漏一項可能造成loop、conns永不下降或所有peer被誤判busy。
""",
        r"""
get_peer(pc, data):
    lock(peers)
    a = sample_eligible(peers, data.tried)
    b = sample_eligible(peers, data.tried)
    best = normalized_load(a) <= normalized_load(b) ? a : b
    mark_tried(data, best)
    best.conns++
    fill_peer_connection(pc, best)
    unlock(peers)
    return OK
""",
        [
            "複製最小dynamic upstream module骨架並重用RR init。",
            "寫純函式simulation，固定seed測1/2/N peers與權重。",
            "整合NGINX，混合短長request比較RR/least_conn/custom。",
            "故障一台、啟用backup、開shared zone做壓測。",
        ],
        [
            "忽略tried bitmap，retry重選同一失敗peer。",
            "只increment conns不在free decrement。",
            "在shared lock內connect或執行昂貴工作。",
        ],
        [
            "把scheduler拆成候選過濾、score、selection與feedback。",
            "重用穩定framework而只替換最小策略。",
            "用simulation＋integration＋failure test驗證概率算法。",
        ],
        [
            ("Balancing module為何不自己呼叫connect？", "Peer interface只決定地址與狀態；event connect core統一處理non-blocking socket、timer、SSL與error，避免每算法重複。"),
            ("為什麼重用RR peer structures？", "它已處理weights、fails、max_conns、backup、shared zone、DNS與locks；重新實作容易漏掉production邊界。"),
            ("Get與free必須成對維護哪些狀態？", "Conns、fails/accessed/checked、effective weight、reference/lock與tried/tries；free還需知道本次成功或failed。"),
            ("兩個sample可能相同怎麼辦？", "重新sample有限次或接受單候選；更重要是避免無限loop，並正確處理eligible只剩一個的情況。"),
            ("如何測概率scheduler？", "固定seed做deterministic unit tests，再大量simulation看分布/最大queue，最後真實並發與failure test看tail latency。"),
            ("Shared zone下為何score讀取也需鎖？", "讀conns與選擇/increment若非同一原子臨界區，多worker可同時基於舊值選同peer，形成herd；可用鎖或設計近似無鎖策略接受誤差。"),
        ],
    ),
    C(
        44,
        "除錯、測試與效能分析",
        "遇到高CPU、偶發502、memory成長或event-loop卡頓時，如何用證據逐層縮小問題？",
        "實作",
        "建立從症狀、request ID、NGINX log、syscall、profile到source hypothesis的可重複流程。",
        ["debugging", "profiling", "fault injection"],
        ["src/core/ngx_log.c:1", "src/http/ngx_http_request.c:3981", "src/http/ngx_http_upstream.c:1571"],
        r"""
symptom/SLO
   ↓ scope: all traffic? one worker? one upstream?
metrics + structured access log
   ↓ correlate request/connection/peer attempts
debug log / error path
   ↓
strace (syscall) | GDB (state) | perf (CPU)
   ↓ minimal reproduction + fault injection
   ↓ hypothesis confirmed / falsified
""",
        """
先分類症狀：CPU、event loop lag、socket/resource exhaustion、upstream latency、output backpressure、memory lifetime或config routing。不同類別需要不同工具。

Access log應包含request id、status、request time、upstream addr/status/connect/header/response times、bytes與cache status。一次retry可能有多個peer值；只看最終200會掩蓋第一次timeout。

Debug log非常詳細，應在最小環境或特定connection使用；production高流量全開可能改變timing與磁碟。Perf找CPU hot path，strace找blocking/syscall pattern，GDB/core dump看object state。
""",
        [
            "先用SLO/metric確認時間窗、worker與request cohort。",
            "從access log拆client time與每個upstream階段。",
            "用error/debug log找到狀態轉換與return code。",
            "選工具：perf CPU、strace syscall、GDB memory/control、ss network。",
            "建立最小重現並注入delay/reset/partial response。",
            "修正後用相同workload與failure驗證，不只跑happy path。",
        ],
        """
Memory問題先問是bounded cache/pool高水位還是真leak。RSS不下降不必然leak，allocator/page cache可能保留；應看跨request object count、pool lifetime、shared zone與長連線generation。

502只是映射結果。根因可能connect refused、timeout、invalid header、premature close、DNS、TLS或no live upstreams；必須讀error subtype與timings。

Benchmark要有warmup、固定CPU/worker、足夠connection數、正確client瓶頸檢查與p50/p95/p99。只報requests/sec會掩蓋tail與error。
""",
        r"""
diagnose(request_id):
    timeline = join(
        access_log[request_id],
        error_log[connection_id],
        upstream_attempts[request_id]
    )
    hypothesis = classify(timeline)
    evidence = run_targeted_tool(hypothesis)
    reproduce_with_fault_injection()
    verify_fix_with_same_test()
""",
        [
            "建立backend四種fault：delay connect、delay header、invalid header、body中斷。",
            "為每種fault整理access/error/upstream timing指紋。",
            "用perf找故意加入的CPU-heavy handler。",
            "用ASan/UBSan build跑自訂module與parser fuzz corpus。",
        ],
        [
            "看到502直接增加timeout或重試。",
            "在production全域開debug log造成二次事故。",
            "以RSS不下降直接判定memory leak。",
        ],
        [
            "建立layered evidence與可證偽hypothesis。",
            "區分CPU、I/O、queueing、allocation與downstream問題。",
            "設計fault injection與回歸測試。",
        ],
        [
            ("502為什麼不是root cause？", "它是gateway對多種upstream failure的HTTP映射；需看error log、upstream status與connect/header/response time判斷具體階段。"),
            ("何時用perf而不是strace？", "CPU高或懷疑user-space hot path用perf；懷疑blocking syscall、重試、fd/error或I/O pattern用strace。兩者可互補。"),
            ("RSS長期高為何不一定leak？", "Allocator arena、page cache、pool高水位與長連線可保留pages；leak需證明不可回收objects隨工作量持續增長。"),
            ("Debug log為何可能改變問題？", "大量format/write I/O增加CPU、lock與disk延遲，改變event timing；應縮小scope或用sampling/breakpoint。"),
            ("怎麼設計upstream fault matrix？", "至少覆蓋DNS、connect拒絕/timeout、TLS、send、header timeout/invalid、body中斷、slow client與retry exhaustion。"),
            ("效能修正如何驗證？", "同硬體/config/workload與warmup，比較throughput、errors、CPU、memory、event-loop lag和p50/p95/p99，並保留correctness/failure tests。"),
        ],
    ),
    C(
        45,
        "閱讀真實 Bug Fix 與 Code Review",
        "從『看懂好程式』走到『能指出好程式哪裡仍會錯』，需要怎樣閱讀commit與設計測試？",
        "進階",
        "用invariant、lifetime、state transition、failure matrix與最小diff閱讀歷史，建立maintainer視角。",
        ["code review", "invariant", "regression test"],
        ["src/http/ngx_http_request.c:1", "src/event/ngx_event.c:1", "src/core/ngx_cycle.c:1"],
        r"""
bug report / commit message
      ↓ reproduce old behavior
identify violated invariant
      ↓ read minimal diff
which state/lifetime/error edge changed?
      ↓ construct neighboring counterexamples
      ↓ regression + compatibility + performance review

不是問「diff做了什麼」，而是「什麼原本應永遠成立卻沒成立」。
""",
        """
閱讀fix先不要看答案。從issue或commit parent重現症狀，寫出預期invariant，例如「event被free前timer必須移除」「body buffer仍被下游引用時不能重用」「retry不選tried peer」。

再看diff，把每一行分類為guard、state update、ownership transfer、cleanup、ordering或test。小diff常修的是時序：哪個flag先設、哪個callback可能重入、error path漏哪個decrement。

Review不能停在原case。沿相鄰維度擴張：同步/非同步、成功/timeout/abort、main/subrequest、buffered/unbuffered、single/multi-worker、reload前後。
""",
        [
            "用`git log -- path`找目標模組歷史與reverts。",
            "Checkout parent或讀old code，建立最小reproduction。",
            "寫明violated invariant與object lifecycle。",
            "讀diff並追caller/callee，不只局部函式。",
            "檢查所有退出邊與對稱操作：add/del、inc/dec、lock/unlock、alloc/free。",
            "建立regression與neighboring cases。",
        ],
        """
NGINX風格偏小而精確的C變更。大規模重構可能掩蓋behavior change；學習時把mechanical cleanup與semantic fix分開看。

Compatibility包括config syntax/default、module ABI、platform backends與已有quirks。看似更漂亮的抽象若改變hot path allocation或filter order，可能不是可接受修正。

Maintainer review重視能否證明：bug為何發生、fix為何足夠、為何不破壞其他state、如何測試。這比「程式能跑」高一層。
""",
        r"""
review_checklist(change):
    invariant = state_what_must_always_hold(change)
    for edge in [success, again, timeout, abort, retry, reload]:
        verify_state_transition(edge)
        verify_add_del_symmetry(edge)
        verify_inc_dec_symmetry(edge)
        verify_owner_and_lifetime(edge)
    verify_hot_path_cost()
    verify_regression_test_fails_before_and_passes_after()
""",
        [
            "挑一個event/request/upstream歷史fix，先只讀parent與commit message重現。",
            "寫出fix前被破壞的invariant，再看diff校正。",
            "建立failure matrix並找至少兩個原commit未明說的neighbor cases。",
            "用`git blame`追一個看似多餘guard的歷史原因。",
        ],
        [
            "只看final diff，失去自行推理bug的機會。",
            "確認原case通過就結束，未測相鄰state。",
            "為了抽象漂亮增加hot-path allocation與不必要耦合。",
        ],
        [
            "以invariant與state transition做code review。",
            "從歷史與revert理解non-obvious constraints。",
            "設計能在修正前失敗、修正後通過的regression。",
        ],
        [
            ("為何先看parent再看fix？", "迫使自己建立因果模型，而不是被答案引導；之後可比較自己的invariant與maintainer判斷差距。"),
            ("什麼是對稱操作檢查？", "每個add timer/event、lock、reference increment、allocation、queue insert都應在所有退出路徑有對應del/unlock/decrement/free/remove。"),
            ("Guard增加就一定安全嗎？", "不一定。Guard可能掩蓋已損壞狀態、跳過必要cleanup或改變正常語意；需說明invariant與後續state。"),
            ("為何要測neighbor cases？", "Root cause通常影響一類state transition，不只報告中的單一輸入；timeout/subrequest/retry等相鄰維度可能仍有同bug。"),
            ("如何評估fix的hot-path成本？", "看新增branch、hash/regex、allocation、lock、copy與cache miss是否每request發生，並以profile/benchmark量化。"),
            ("到什麼程度算真正讀懂一個fix？", "能重現舊bug、陳述被破壞invariant、解釋diff每個state更新、列出風險邊界並設計回歸。"),
        ],
        code_lang="text",
    ),
]


PART_8 = [
    C(
        46,
        "為什麼 Connection Layer 不應知道 HTTP",
        "如果直接在connection read handler裡寫死HTTP不是更簡單嗎？分層何時真正產生價值？",
        "架構",
        "從listening callback、event abstraction與protocol data看dependency direction，再比較HTTP、Stream、Mail與QUIC。",
        ["layering", "dependency inversion", "protocol independence"],
        ["src/core/ngx_connection.h:1", "src/event/ngx_event.h:1", "src/http/ngx_http_request.c:211", "src/stream/ngx_stream_handler.c:1"],
        r"""
OS / socket
     ↓
connection + read/write events       不知道HTTP
     ↓ protocol handler callback
HTTP connection/request  |  Stream session  |  Mail session
     ↓                         ↓                    ↓
HTTP phases/upstream      TCP/UDP proxy       mail protocol

依賴方向：上層使用下層；下層只暴露callback seam。
""",
        """
Core connection只知道fd、events、I/O functions、addresses、pool與generic data。Accept完成後透過listening handler交給HTTP或Stream；event backend只呼叫當前event handler。這讓底層不用include HTTP request type。

分層的價值在需求變化時顯現：新增Stream TCP/UDP proxy可重用listener、connection、event、timer、buffer、upstream peer等基礎，而不必在每個socket函式加`if HTTP else STREAM`。

抽象不是越多越好。好的邊界圍繞穩定機制：non-blocking I/O、timer、connection lifecycle；協定特有的parse、routing、header/filter留上層。若抽象洩漏大量protocol flags，層次就失效。
""",
        [
            "Core建立listening/connection/event與OS I/O function table。",
            "各protocol在config-time設定listening handler與servers metadata。",
            "Accept core完成通用初始化後呼叫handler。",
            "Protocol把`c->data`指向自己的connection/session/request state。",
            "Protocol仍可使用共同upstream peer、buffer、pool與timer primitives。",
        ],
        """
Dependency inversion不是一定要物件導向interface；C的function pointer、opaque `void *`與module table已能實作。關鍵是ownership與contract清楚。

QUIC/HTTP/3提醒我們抽象也有邊界：QUIC以UDP承載多stream，connection/stream mapping與readiness模型不同，需要新event/quic與http/v3層；仍重用core，但不能硬套TCP一connection一stream。

判斷分層是否成功可問：加入新protocol時，哪些低層檔案需要改？若只是註冊新handler與上層module，多半邊界健康。
""",
        r"""
void generic_accept(event_t *ev) {
    connection_t *c = accept_and_initialize(ev);
    c->listening->protocol_handler(c);  /* HTTP/Stream/Mail自己接手 */
}

void http_init_connection(connection_t *c) {
    c->data = create_http_connection_context(c->pool);
    c->read->handler = http_wait_request;
}
""",
        [
            "比較`ngx_http_init_connection`與`ngx_stream_init_connection`的共同輸入與不同state。",
            "列出新增一個toy protocol可直接重用的core primitives。",
            "找一個HTTP detail若被放進event core會造成的反向依賴。",
            "比較QUIC stream與TCP connection，標出舊抽象需擴充之處。",
        ],
        [
            "把所有共同程式都抽象，產生無語意的萬用layer。",
            "用`void *`卻沒有清楚handler/type contract。",
            "為新protocol在core到處加條件分支。",
        ],
        [
            "辨認stable mechanism與volatile policy。",
            "使用callback/opaque context實作dependency inversion。",
            "以change impact評估架構邊界品質。",
        ],
        [
            ("Connection layer不知道HTTP的直接證據？", "核心struct只持generic data與I/O/events；HTTP由listening/event callbacks接手並將`c->data`解讀為HTTP context，core不需HTTP欄位。"),
            ("分層帶來哪些成本？", "更多indirection、function pointer、context cast、初始化順序與debug難度；只有變化與重用需求足以時才值得。"),
            ("為什麼Stream能驗證這個設計？", "它在相同event/connection底座上實作TCP/UDP session與proxy，底層不需改成理解HTTP headers或phases。"),
            ("`void *` 是否代表良好抽象？", "不一定。它只消除compile-time型別依賴；若lifetime/type約定不清，會變成不安全耦合。良好抽象還需contract。"),
            ("QUIC為何不能完全套用TCP模型？", "UDP、connection ID、多stream與user-space loss recovery改變transport/event語意；需要新層，但可重用pool、timer、module與HTTP上層概念。"),
            ("如何衡量一個layer是否放對？", "看它是否以最少protocol知識提供穩定能力、新需求改動範圍、ownership是否單向、以及是否頻繁繞過/洩漏內部。"),
        ],
    ),
    C(
        47,
        "NGINX 的優雅與歷史包袱",
        "讀懂之後，如何同時看見NGINX的優秀設計、C時代限制與不能盲目照搬的部分？",
        "架構",
        "用context而非崇拜評估event model、pool、module ABI、global state、callbacks與現代替代方案。",
        ["tradeoff", "technical debt", "contextual design"],
        ["src/core/ngx_core.h:1", "src/core/ngx_module.h:1", "src/event/ngx_event.h:1"],
        r"""
成功的核心約束                    長期代價
單thread event loop               blocking module風險、callback分散
pool + intrusive structures        lifetime靠discipline、工具較難
module tables + function pointers  ABI/ordering/型別安全成本
config-time預計算                  reload流程複雜
master/worker isolation            shared state與跨worker協調困難

設計好壞必須放回當時問題、語言與效能目標。
""",
        """
NGINX的優雅來自一致：明確生命週期、非阻塞狀態機、config-time預計算、少量allocation、protocol/core分層。它不是因為每個函式都短，而是控制成本有共同原則。

同樣原則也產生包袱。大量global function pointers與module ordering使控制流隱性；`void *`與macros犧牲型別安全；request struct與flags隨功能成長；第三方module可在worker中阻塞整個event loop。

評估時避免兩個極端：一是看到乾淨C就照搬所有技巧；二是用現代語言標準否定歷史設計。正確問題是：這個constraint還存在嗎？現在有哪些更安全工具？替換是否破壞已驗證的hot path與生態？
""",
        [
            "選一個機制，先寫它解決的原始constraint與成功指標。",
            "找隨時間加入的flags/hooks，辨認抽象壓力。",
            "比較現代替代：async/await、typed trait、RAII、generational arena。",
            "評估migration cost：module ecosystem、config compatibility、performance與operational knowledge。",
            "提出可漸進改進，而非一次重寫所有核心。",
        ],
        """
重寫常低估behavioral compatibility。數十年邊界案例藏在error paths、timeouts、platform ifdefs與module expectations；「更漂亮」的新實作需重新付驗證成本。

可以局部現代化：更好的generated docs、typed wrappers、sanitizer/fuzz tests、清楚state tracing、限制blocking module、將複雜任務移thread pool。這些改善不必推翻event core。

真正學到架構是能說出「為什麼當初合理、今天哪裡痛、改動會傷到什麼、如何量化改善」。
""",
        r"""
evaluate(design):
    constraints = historical_and_current_constraints(design)
    benefits = measured_properties(design)
    liabilities = failure_and_change_cost(design)
    alternatives = modern_options()

    for option in alternatives:
        compare(option,
                compatibility,
                performance,
                operability,
                migration_risk)
    choose_incremental_step()
""",
        [
            "挑pool、phase engine或module ABI寫一頁design review：收益、代價、替代。",
            "找一個歷史commit顯示某flag為相容性而加入。",
            "用ASan/fuzz/trace為舊設計增加安全網，再提出小重構。",
            "比較C callback與Rust async state machine的allocation/typing/debug取捨。",
        ],
        [
            "把成功專案的所有細節當universally best practice。",
            "只批評可讀性，不量化效能、相容與運維收益。",
            "提出big-bang rewrite卻沒有behavioral regression策略。",
        ],
        [
            "以constraint與evidence做架構判斷。",
            "辨認essential complexity與accidental complexity。",
            "設計漸進式現代化與相容性安全網。",
        ],
        [
            ("NGINX最值得學的不是哪個具體API？", "是一致的約束管理：把等待交event loop、把狀態放明確lifetime、把固定工作移config-time、把protocol policy放module。"),
            ("Callback多就代表架構差嗎？", "不必然。它是C中低成本continuation/plugin手段；問題在contract、typing、traceability與lifetime是否可管理。"),
            ("為何重寫可能比漸進修改危險？", "成熟系統有大量隱含邊界與operational behavior；新系統需重新發現。除非收益可量化且有兼容/遷移計畫，風險很高。"),
            ("現代語言能自動解決哪些問題？", "更強型別、RAII/borrow、async生成狀態機可降低部分錯誤；但backpressure、retry、timeouts、protocol ambiguity等系統問題仍需設計。"),
            ("如何辨認technical debt而非必要複雜度？", "看constraint是否已消失、變更是否反覆觸碰同脆弱區、bug密度與理解成本；同時驗證簡化不會失去效能/相容能力。"),
            ("一份好的改進提案要包含什麼？", "當前invariant與痛點、數據、替代方案、compatibility、failure modes、分階段migration、rollback與benchmark/test plan。"),
        ],
        code_lang="text",
    ),
    C(
        48,
        "將所學遷移到其他系統",
        "讀完NGINX後，如何把能力帶到Redis、Node.js、Netty、Envoy、資料庫與一般coding問題，而不是只會找NGINX函式？",
        "架構",
        "把具體名稱抽象成event、state、lifetime、pipeline、scheduler與failure semantics六個可遷移模型。",
        ["transfer learning", "systems thinking", "problem decomposition"],
        ["src/event/ngx_event.c:195", "src/http/ngx_http_core_module.c:894", "src/http/ngx_http_upstream.c:1571"],
        r"""
NGINX具體概念              可遷移模型
ngx_event_t/handler         readiness + continuation
request/upstream structs    explicit async state
pool                        region/lifetime ownership
phase/filter chain          compiled middleware pipeline
peer.get/free               scheduler + feedback
timer rbtree                deadline queue
reload cycle                immutable generation + draining
buffer chain                slices + scatter/gather + backpressure
""",
        """
遷移的第一步是去掉名字。例如不要只記`ngx_http_upstream_next`，而要記「一次attempt失敗後，根據idempotency、body replayability、deadline與tried set決定是否重試」。

Redis同樣以event loop推進socket與timer，但資料處理模型不同；Node/libuv把callback/async work包成更高層API；Netty用pipeline與event loop group；Envoy採typed C++ filter與cluster/connection pool。比較時先找共同mechanism，再看policy與thread model。

Coding面試也能受益：紅黑樹題不只背旋轉，而是先問是否需要ordered min與任意delete；state machine題先定義incomplete/error/complete；LRU題思考multi-index object與ownership。
""",
        [
            "對新系統找入口事件、核心loop與等待邊界。",
            "列出跨等待存活的state object與owner。",
            "找pipeline/plugin registration與return protocol。",
            "找scheduler輸入訊號、feedback與failure policy。",
            "找buffer/queue上限與backpressure傳播。",
            "找reload/deploy時新舊generation如何交接。",
        ],
        """
不要強行套Reactor名稱。實作可能是completion-based I/O、thread-per-core、actor、async runtime；共同問題仍是誰保存state、誰喚醒、如何取消、如何限流。

面試或設計討論時，從constraint導出結構：連線數、消息大小、deadline、是否可重試、state是否共享、順序需求。這比先報出「用epoll＋紅黑樹」更有說服力。

最終能力是面對陌生系統仍能提出可驗證問題，快速建立golden path，並知道何時深入OS、算法、協定或語言。
""",
        r"""
read_new_system(codebase):
    path = choose_one_user_visible_flow()
    boundaries = find_io_and_process_boundaries(path)
    state = find_objects_surviving_waits(path)
    callbacks = find_wakeup_and_dispatch_points(path)
    limits = find_queues_timeouts_and_backpressure(path)
    failures = enumerate_cancel_retry_cleanup(path)
    verify_with_trace_and_small_change()
""",
        [
            "選Redis或Node，畫一條與本書相同格式的request/event路徑。",
            "把NGINX phase engine與一個middleware框架逐項比較。",
            "從任一coding題先寫workload/operations，再選資料結構。",
            "在新專案完成一個小功能，使用source trace＋failure matrix驗證。",
        ],
        [
            "只搬函式名稱與具體容器，不搬constraint reasoning。",
            "看到event loop就假設thread model與NGINX相同。",
            "設計題先宣布技術選型，再詢問流量與一致性需求。",
        ],
        [
            "把源碼閱讀轉成通用systems investigation。",
            "用constraint驅動algorithm/data structure選擇。",
            "建立能從實作上升到architecture、再回到實驗的閉環。",
        ],
        [
            ("如何判斷知識已從NGINX遷移出去？", "在不同語言/系統中仍能找出event boundary、state owner、continuation、backpressure與failure semantics，而不依賴NGINX名稱。"),
            ("Reactor是唯一高併發模型嗎？", "不是。Completion I/O、async runtime、actor、thread-per-core等都可行；應比較工作負載、OS、語言與延遲需求。"),
            ("紅黑樹知識如何遷移到coding？", "先辨認需要ordered min、dynamic insert與arbitrary delete，再比較heap/tree/wheel；場景與operation set比旋轉記憶更重要。"),
            ("讀新codebase第一個問題應多大？", "足以穿過數個重要邊界但可在幾小時/一天回答，例如『一條消息如何進queue再ack』；不要一開始問『整個系統如何運作』。"),
            ("系統設計時為何先問failure semantics？", "Retry、dedup、deadline、queue與state ownership都受失敗後是否知道結果影響；happy path無法決定真正架構。"),
            ("這本書最後的驗收是什麼？", "能不看書畫出一次proxy request，解釋每個suspend/lifetime/failure；再寫一個小module並把同一分析框架用到陌生專案。"),
        ],
        code_lang="text",
    ),
]


BOOK_PARTS = [
    {
        "part": 1,
        "slug": "First Request and Reading Method",
        "title": "先看到請求真的動起來",
        "intro": "先不囤積整套背景知識。用一次真實 reverse proxy request 建立黃金路徑、實驗環境、閱讀方法與最低限度 C。",
        "chapters": PART_1,
    },
    {
        "part": 2,
        "slug": "Startup Process and Reload",
        "title": "啟動、設定、Process 與 Reload",
        "intro": "從 `main()` 建立一代 cycle，理解設定語言、master/worker 分工與新舊 generation 如何無中斷交接。",
        "chapters": PART_2,
    },
    {
        "part": 3,
        "slug": "Connections Events and Epoll",
        "title": "Connection、Event Loop 與 epoll",
        "intro": "這是 NGINX 的心臟：socket readiness、callback、timer、紅黑樹與 backpressure 如何共同形成 cooperative scheduler。",
        "chapters": PART_3,
    },
    {
        "part": 4,
        "slug": "HTTP Request Lifecycle",
        "title": "HTTP Request 的一生",
        "intro": "從 request object、incremental parser、routing 與 phase engine，走到 body、filter、finalize、subrequest 與 keep-alive。",
        "chapters": PART_4,
    },
    {
        "part": 5,
        "slug": "Proxy Upstream and Load Balancing",
        "title": "Proxy、Upstream 與負載均衡",
        "intro": "回到最初問題：`proxy_pass` 如何建立 backend request、選 peer、非阻塞連線、重試、重用連線並控制快慢兩端。",
        "chapters": PART_5,
    },
    {
        "part": 6,
        "slug": "Core Mechanisms",
        "title": "藏在 NGINX 裡的 CS 核心",
        "intro": "把記憶體池、資料結構、buffer chain、shared memory 與 module system 放回真實使用場景。",
        "chapters": PART_6,
    },
    {
        "part": 7,
        "slug": "Hands-on Modules and Debugging",
        "title": "從讀懂走向真的會",
        "intro": "依序寫 content、access、variable/filter、streaming 與 load-balancer modules，最後用故障注入和歷史 commit 建立 maintainer 視角。",
        "chapters": PART_7,
    },
    {
        "part": 8,
        "slug": "Architecture and Transfer",
        "title": "真正讀懂架構",
        "intro": "看見分層產生價值的時刻，也看見成熟 C 系統的歷史代價；最後把方法遷移到任何陌生系統。",
        "chapters": PART_8,
    },
]


APPENDICES = [
    {
        "slug": "Reading Map",
        "title": "附錄 A　閱讀地圖與使用方式",
        "body": r"""
這本書有兩條路，不必第一次就讀完所有細節。

## 21 天黃金路徑

只讀第 1、2、4、5、7–18、20–31、34、36、38、44、46、48 章。每天完成一個小實驗；先能畫完整 request path，再回來補 cache、shared memory與module實作。

## 完整路徑

依章節順序讀完 48 章，完成第 39–45 章至少三個module實作。每章關書後回答Q&A，再用debug log或GDB證明一個答案。

## 每次閱讀的四張卡

| 卡片 | 必答問題 |
|---|---|
| Object card | 誰建立、誰持有、何時銷毀、最重要狀態？ |
| Callback card | 誰安裝、何時觸發、返回後下一步是誰？ |
| Buffer card | bytes在哪、誰擁有、是否可改、部分消費如何表示？ |
| Failure card | timeout/abort/retry時哪些操作必須對稱撤銷？ |

## 停止條件

一次session只回答一個可驗證問題，例如「connect未完成後誰重新喚醒」。當你能畫狀態、指出源碼座標並以trace驗證，就先停。新問題放backlog，不讓閱讀無限展開。
""",
    },
    {
        "slug": "C Survival Kit",
        "title": "附錄 B　C 語言生存速查",
        "body": r"""
## 必會語法

```c
T *p;              /* 指向 T */
p->field;          /* (*p).field */
void *data;        /* generic pointer，型別由契約決定 */
typedef int (*handler_pt)(request_t *r);
handler_pt next;   /* function pointer */
```

## 半開區間

NGINX大量使用 `[pos, last)`。長度是 `last - pos`；空buffer是 `pos == last`。`start/end`通常描述storage容量，`pos/last`描述當前有效資料。

## `ngx_str_t`

```c
typedef struct {
    size_t  len;
    u_char *data;
} ngx_str_t;
```

`data[len]`不保證是NUL。輸出時使用有長度的format/API，不要直接當`%s`。

## Container-of

Intrusive queue/tree把link嵌進外層struct。已知link地址與欄位offset，可算回object start。它避免wrapper allocation，但要求unlink與lifetime嚴格。

## Return code閱讀法

- `NGX_OK`：本API定義的成功；不一定代表整個request完成。
- `NGX_ERROR`：不可恢復錯誤，通常需finalize/cleanup。
- `NGX_AGAIN`：目前不能前進，保存狀態等待event。
- `NGX_DECLINED`：本handler不處理，讓pipeline繼續。
- `NGX_DONE`：當前控制流停止，常有async ownership未完成。

永遠讀caller如何解釋；名稱不是完整contract。

## Bit fields與flags

大量狀態壓成bit fields。修改前問：誰初始化零值？何時清除？timer/event晚到時此flag是否仍可信？
""",
    },
    {
        "slug": "Linux Syscalls",
        "title": "附錄 C　Linux Syscall 與網路速查",
        "body": r"""
| Syscall | 在主線中的角色 | 常見結果 |
|---|---|---|
| `socket` | 建立listen/upstream socket | fd或error |
| `bind` | 綁local address/port | address in use/permission |
| `listen` | 建立accept queue入口 | backlog受kernel限制 |
| `accept4` | 取得client connected fd | fd、EAGAIN、EMFILE |
| `connect` | 啟動backend TCP連線 | 0、EINPROGRESS、error |
| `recv` | 讀byte stream | bytes、0 EOF、EAGAIN |
| `writev` | 送多段memory buffers | partial bytes、EAGAIN |
| `sendfile` | 送file range到socket | partial bytes、EAGAIN |
| `epoll_ctl` | 維護interest set | add/mod/del |
| `epoll_wait` | 等ready fd或timer timeout | ready events、EINTR |
| `mmap` | shared memory/file mapping | process-visible region |
| `fork` | 建worker | child複製address space/COW |

## TCP 狀態排障

- `SYN-SENT` 很久：route/firewall/backend accept問題。
- `ESTABLISHED`但header time高：application/queue慢。
- `CLOSE-WAIT`多：peer已FIN，本端未close。
- `TIME-WAIT`多：主動close與連線重用策略。
- RST：peer abort、未讀資料close或中間設備。

## Readiness檢查表

Read-ready不保證完整消息；write-ready不保證整個buffer可送；connect write-ready不保證成功；timer deadline不保證real-time準點。所有操作都要讀實際return value。
""",
    },
    {
        "slug": "Source Index",
        "title": "附錄 D　源碼檔案與核心函式索引",
        "body": r"""
## 啟動與程序

| 問題 | 主要座標 |
|---|---|
| 程式入口 | `src/core/nginx.c::main` |
| 建立configuration generation | `src/core/ngx_cycle.c::ngx_init_cycle` |
| Master loop | `src/os/unix/ngx_process_cycle.c::ngx_master_process_cycle` |
| Worker loop | `src/os/unix/ngx_process_cycle.c::ngx_worker_process_cycle` |

## Event

| 問題 | 主要座標 |
|---|---|
| 接受連線 | `src/event/ngx_event_accept.c::ngx_event_accept` |
| 一輪scheduler | `src/event/ngx_event.c::ngx_process_events_and_timers` |
| Linux epoll wait | `src/event/modules/ngx_epoll_module.c::ngx_epoll_process_events` |
| Timer tree | `src/event/ngx_event_timer.c` |

## HTTP

| 問題 | 主要座標 |
|---|---|
| 初始化HTTP connection | `src/http/ngx_http_request.c::ngx_http_init_connection` |
| 建request | `ngx_http_create_request` |
| Request line/header | `ngx_http_process_request_line` / `ngx_http_process_request_headers` |
| Parser | `src/http/ngx_http_parse.c` |
| Location | `ngx_http_core_find_location` |
| Phase engine | `ngx_http_core_run_phases` |
| Finalize/keepalive/free | `ngx_http_finalize_request` / `ngx_http_set_keepalive` / `ngx_http_free_request` |

## Upstream

| 問題 | 主要座標 |
|---|---|
| 建立/啟動 | `ngx_http_upstream_create` / `ngx_http_upstream_init` |
| 連backend | `ngx_http_upstream_connect` / `ngx_event_connect_peer` |
| Retry | `ngx_http_upstream_next` |
| Weighted RR | `ngx_http_upstream_get_peer` |
| Keepalive | `ngx_http_upstream_keepalive_module.c` |
| Buffer pipe | `src/event/ngx_event_pipe.c` |
| Cache | `src/http/ngx_http_file_cache.c` |

## Core primitives

Pool看`ngx_palloc.c`；buffer/chain看`ngx_buf.h`與`ngx_output_chain.c`；array/list/queue/hash/rbtree/radix看`src/core/ngx_*`對應檔；shared memory/slab/lock看`ngx_shmem.c`、`ngx_slab.c`、`ngx_shmtx.c`。
""",
    },
    {
        "slug": "Lab Config",
        "title": "附錄 E　最小實驗設定與故障後端",
        "body": r"""
## 最小 NGINX 設定

```nginx
daemon off;
worker_processes 1;
error_log logs/error.log debug;
pid logs/nginx.pid;

events {
    worker_connections 1024;
}

http {
    access_log logs/access.log combined;

    upstream lab_backend {
        server 127.0.0.1:9001 weight=2;
        server 127.0.0.1:9002;
        keepalive 8;
    }

    server {
        listen 8080;

        location / {
            proxy_pass http://lab_backend;
            proxy_set_header X-Lab-Request $request_id;
            proxy_connect_timeout 500ms;
            proxy_read_timeout 3s;
        }
    }
}
```

## 可直接執行的故障後端

以下程式只使用 Python 標準函式庫。存成 `backend.py`，分別啟動 A、B 兩個 backend：

```bash
python3 backend.py --port 9001 --name A
python3 backend.py --port 9002 --name B
```

```python
#!/usr/bin/env python3
import argparse
import hashlib
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "nginx-book-lab/1.0"

    def log_message(self, fmt, *args):
        print(f"[{self.server.backend_name}] {self.client_address[0]} "
              f"{fmt % args}", flush=True)

    def number(self, params, name, default, maximum):
        try:
            value = int(params.get(name, [default])[0])
        except (TypeError, ValueError):
            value = default
        return max(0, min(value, maximum))

    def read_body(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0
        return self.rfile.read(size)

    def send_bytes(self, status, body, content_type="text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Lab-Backend", self.server.backend_name)
        self.end_headers()
        self.wfile.write(body)

    def raw_response(self, data):
        self.connection.sendall(data)
        self.close_connection = True

    def handle_request(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path

        if path == "/header-delay":
            delay_ms = self.number(params, "ms", 500, 30_000)
            time.sleep(delay_ms / 1000)
            self.send_bytes(200, f"{self.server.backend_name}: headers delayed "
                            f"{delay_ms}ms\n".encode())
            return

        if path == "/body-delay":
            delay_ms = self.number(params, "ms", 250, 30_000)
            chunks = self.number(params, "chunks", 5, 100)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("X-Lab-Backend", self.server.backend_name)
            self.end_headers()
            for index in range(chunks):
                payload = f"{self.server.backend_name}: chunk {index}\n".encode()
                self.wfile.write(f"{len(payload):x}\r\n".encode())
                self.wfile.write(payload + b"\r\n")
                self.wfile.flush()
                time.sleep(delay_ms / 1000)
            self.wfile.write(b"0\r\n\r\n")
            return

        if path == "/invalid-header":
            self.raw_response(
                b"HTTP/1.1 200 OK\r\n"
                b"Bad Header: deliberately-invalid\r\n"
                b"Content-Length: 3\r\n\r\nbad"
            )
            return

        if path == "/close-mid-body":
            self.raw_response(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain\r\n"
                b"Content-Length: 100\r\n\r\npartial"
            )
            return

        if path == "/large":
            size = self.number(params, "n", 1_048_576, 100 * 1024 * 1024)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("X-Lab-Backend", self.server.backend_name)
            self.end_headers()
            block = (self.server.backend_name.encode() * 65_536)[:65_536]
            remaining = size
            while remaining:
                piece = block[:min(len(block), remaining)]
                self.wfile.write(piece)
                remaining -= len(piece)
            return

        if path == "/echo":
            body = self.read_body()
            response = {
                "backend": self.server.backend_name,
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers.items()),
                "body_bytes": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
            }
            payload = (json.dumps(response, ensure_ascii=False, indent=2)
                       + "\n").encode()
            self.send_bytes(200, payload, "application/json; charset=utf-8")
            return

        self.send_bytes(200, f"{self.server.backend_name}: ok\n".encode())

    do_GET = handle_request
    do_POST = handle_request
    do_PUT = handle_request
    do_DELETE = handle_request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.backend_name = args.name
    print(f"backend {args.name} listening on 127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
```

## 每個 endpoint 在隔離什麼問題

| Endpoint | 實驗目的 | 建議觀察 |
|---|---|---|
| `/ok` | 正常負載均衡基線 | backend 分布、connection reuse |
| `/header-delay?ms=500` | connect 已完成，但 response header 尚未到 | `proxy_read_timeout`、header time |
| `/body-delay?ms=250&chunks=5` | headers 已到，body 分段抵達 | buffering、streaming、backpressure |
| `/invalid-header` | backend 回傳不合法 header | parser error、502 與 retry policy |
| `/close-mid-body` | 宣告長度與實際 body 不一致 | premature close、已送出 response 後能否 retry |
| `/large?n=104857600` | 大型 response | memory、temporary file、slow client |
| `/echo` | 驗證 method、headers 與 body forwarding | request reconstruction、body replay |

先確認 backend 本身：

```bash
curl -i http://127.0.0.1:9001/ok
curl -i 'http://127.0.0.1:9002/header-delay?ms=500'
curl -N 'http://127.0.0.1:9001/body-delay?ms=200&chunks=4'
printf 'hello' | curl -i -X POST --data-binary @- http://127.0.0.1:9002/echo
```

再經過 NGINX 執行相同請求。每個實驗都帶唯一 request ID，保存 curl 輸出、access/error log 與必要的 strace 片段；只改一個變因，才知道觀察到的差異由哪個機制造成。
""",
    },
    {
        "slug": "21 Day Plan",
        "title": "附錄 F　21 天核心閱讀計畫",
        "body": r"""
| 天 | 章節 | 當日輸出 |
|---:|---|---|
| 1 | 1–2 | 跑通兩backend proxy，保存黃金路徑log |
| 2 | 3–4 | 完成object/callback cards |
| 3 | 5–7 | 畫main→cycle與generation |
| 4 | 8–9 | 實驗worker crash與reload |
| 5 | 10–11 | 追accept到HTTP init |
| 6 | 12–14 | 畫epoll/event loop |
| 7 | 15–16 | timer tree與slow client |
| 8 | 17–18 | request object與分段request line |
| 9 | 19–20 | header安全與location matrix |
| 10 | 21 | phase trace |
| 11 | 22–24 | body、filter、finalize |
| 12 | 25–27 | proxy/upstream/connect |
| 13 | 28–29 | 手算並實測load balancing |
| 14 | 30 | failure/retry/idempotency |
| 15 | 31–32 | keepalive與buffering |
| 16 | 33–35 | cache、pool、資料結構 |
| 17 | 36–38 | buffer/shared/module |
| 18 | 39 | Hello module |
| 19 | 40–42 | Access或filter module擇一 |
| 20 | 44–45 | fault matrix與歷史fix |
| 21 | 46–48 | 不看書重畫全流程與遷移模型 |

每天最後用十五分鐘口述：「物件、狀態、下一callback、timeout、cleanup」。說不清楚的地方才回源碼補。
""",
    },
    {
        "slug": "Eight Week Plan",
        "title": "附錄 G　8 週完整實作路線",
        "body": r"""
## Week 1：可觀察環境與C

完成第1–6章；固定build、建立source map與config parser trace。

## Week 2：Process、Reload、Connection

完成第7–11章；輸出master/worker/reload timeline與fd資源表。

## Week 3：Event Core

完成第12–16章；實作小型epoll echo server，加入timer與bounded write。

## Week 4：HTTP

完成第17–24章；寫分段parser測試、location matrix、phase trace與slow body/filter實驗。

## Week 5：Upstream

完成第25–33章；建立failure backend、比較balancers、retry、keepalive與buffer/cache。

## Week 6：Core Mechanisms

完成第34–38章；手寫arena、intrusive queue、timer heap/tree比較與shared counter。

## Week 7：Modules

完成第39–43章；至少交付content＋access/filter＋balancer三個module。

## Week 8：Maintainer Mode

完成第44–48章；選一個歷史bug重現、寫regression、做architecture review，並把方法套到第二個開源專案。
""",
    },
    {
        "slug": "Glossary",
        "title": "附錄 H　核心術語表",
        "body": r"""
| 術語 | 本書中的精確意思 |
|---|---|
| readiness | 某I/O操作現在可能前進，不保證完整完成 |
| continuation | 等待結束後要執行的下一段工作，常以function pointer保存 |
| event loop | 統一等待並派發I/O、timer與posted work的cooperative scheduler |
| connection | 一條transport/socket生命週期 |
| request | 一次HTTP語意交換，可短於connection |
| cycle | 一代configuration與runtime resources的根物件 |
| pool/arena | 依共同生命週期整批配置/釋放的region |
| phase | request控制pipeline中的語意階段 |
| filter | 以top/next鏈轉換response header/body |
| upstream | NGINX代表client與backend互動的通用框架/物件 |
| peer | 一次可選backend endpoint及其狀態 |
| backpressure | consumer變慢時限制producer與在途資料 |
| buffering | 主動吸收速度差，將資料留memory或disk |
| idempotency | 同一操作重複執行不產生額外副作用的語意 |
| graceful drain | 停止接新工作，等待in-flight完成後退出 |
| intrusive structure | link node嵌在業務物件中的container |
| stale event | 對已關閉/重用fd或object generation的延遲通知 |
""",
    },
    {
        "slug": "Sources",
        "title": "附錄 I　版本、資料來源與閱讀原則",
        "body": r"""
## 固定版本

- NGINX tag：`release-1.31.5`
- Commit：`231a60ee3e90a43b829b9ca0a3013a8359b98d7e`
- 主要平台：Linux epoll
- 主線協定：HTTP/1.1 reverse proxy

## 第一手資料

- 官方源碼：<https://github.com/nginx/nginx/tree/release-1.31.5>
- 官方 Development Guide：<https://nginx.org/en/docs/dev/development_guide.html>
- 官方 HTTP Load Balancing：<https://nginx.org/en/docs/http/load_balancing.html>
- 官方 Beginner's Guide：<https://nginx.org/en/docs/beginners_guide.html>
- 官方指令文件：<https://nginx.org/en/docs/>

## 方法

技術敘述以固定tag源碼與官方文件交叉核對。每章先用可執行的 Python 小模型隔離一個核心設計，再逐欄映射到 NGINX 的 C object、callback 與生命週期；Python 是概念等價模型，不是 NGINX 的逐行翻譯。其後直接內嵌同一主題的官方真實源碼視窗、檔案與行號，因此離線閱讀也能完成第一輪理解；外部連結只供繼續追完整上下文。

讀源碼的核心方法來自問題驅動：先追一條user-visible path；遇到epoll、紅黑樹、狀態機、pool再即時學背景；理解後用實驗、module或bug reproduction驗收。這避免把本書變成脫離場景的C、OS或算法百科。

本書內嵌的 C 摘錄來自上述固定版本的官方 repository；完整 copyright notices 與授權條款以該 release 的 `LICENSE` 為準。引用與修改時請遵守上游授權。本書內容是教學整理，不替代官方安全公告、版本 release notes 或 production 操作文件。
""",
    },
]
