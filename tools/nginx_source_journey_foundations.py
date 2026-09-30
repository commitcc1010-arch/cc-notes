"""Chapter-local prerequisite explanations for the NGINX source journey.

The book must remain understandable when a beginner jumps directly to any
chapter.  Each chapter therefore selects a small set of terms from this
library.  Every term is explained before the chapter's design discussion and
source code.
"""
from __future__ import annotations


def T(title: str, meaning: str, example: str, nginx_role: str) -> dict[str, str]:
    return {
        "title": title,
        "meaning": meaning,
        "example": example,
        "nginx_role": nginx_role,
    }


TERMS = {
    "reverse_proxy": T(
        "Reverse proxy（反向代理）",
        "Client 只連到代理伺服器；代理再代表 client 連到內部 backend。Client 不需要知道 backend 的位址，也不會直接與它建立連線。",
        "瀏覽器請求 `shop.example.com`，NGINX 收到後轉給內網的 `10.0.0.8:8080`，再把結果送回瀏覽器。",
        "NGINX 在 client connection 與 upstream connection 之間轉換、緩衝並轉送 HTTP 資料。",
    ),
    "request_response": T(
        "Request 與 Response",
        "Request 是 client 提出的要求，通常包含 method、URL、headers 與可選 body；response 是 server 回覆的 status、headers 與 body。",
        "`GET /users/7` 是 request；`200 OK` 加上一段 JSON 是 response。",
        "NGINX 先解析 request，依設定選 handler，再建立或轉送 response。",
    ),
    "transport": T(
        "Transport（傳輸層工作）",
        "Transport 只關心 bytes 如何經由連線抵達與送出，不理解這些 bytes 代表登入、圖片或 HTTP header。",
        "TCP 保證有順序的 byte stream，但不保證一個 `send()` 對應另一端的一個 `recv()`。",
        "NGINX 的 connection/event layer 處理 socket 與 readiness，上層 HTTP module 才解釋語意。",
    ),
    "backend": T(
        "Backend / application server",
        "真正執行商業邏輯的程式，例如登入、付款、查詢資料庫。它通常位於 NGINX 後方。",
        "Python Django、Java Spring 或 Go service 都可以是 backend。",
        "NGINX 選擇 backend、建立 upstream connection，並把 request 轉成 backend 能理解的格式。",
    ),
    "callback": T(
        "Callback（回呼函式）",
        "現在先把『未來某件事發生時要做什麼』存成函式；事件發生後，由框架呼叫它。",
        "Socket 現在沒有資料時不等待；先記住 `on_readable`，有資料可讀時再執行。",
        "`ngx_event_t.handler` 保存下一次 read、write 或 timer event 到來時要執行的函式。",
    ),
    "observability": T(
        "Observability（可觀察性）",
        "利用 log、metrics、trace 與 debugger，從程式外部推回內部實際發生的狀態轉換。",
        "同一個 request ID 出現在 accept、upstream connect 與 response log，便能重建完整時間線。",
        "Debug log、錯誤碼、request/connection 編號與 timing 欄位是驗證源碼理解的證據。",
    ),
    "syscall": T(
        "System call（系統呼叫）",
        "一般程式不能直接控制網卡、socket 或 process；它必須呼叫作業系統核心提供的入口。",
        "`read()`、`write()`、`accept()`、`epoll_wait()` 都是 system calls。",
        "用 `strace` 觀察 syscall，可以確認 NGINX 最後真的向 kernel 要求了什麼。",
    ),
    "debugger": T(
        "Debugger / GDB",
        "Debugger 可以暫停程式、查看 call stack、變數與記憶體，並逐步執行。",
        "在 `ngx_http_upstream_handler` 設 breakpoint，觀察 `r->upstream` 當時指向什麼。",
        "它適合回答單次執行中的 object state；不適合取代 production metrics 或 protocol 測試。",
    ),
    "worker": T(
        "Worker process",
        "長時間運行並實際處理 client connections 的 NGINX 子程序。每個 worker 通常有自己的 event loop。",
        "四核心主機可能啟動四個 workers，各自處理一批 connections。",
        "阻塞其中一個 worker 會延遲該 worker 管理的所有 ready events。",
    ),
    "codebase": T(
        "Codebase 與 call graph",
        "Codebase 是一個專案的完整程式集合；call graph 是『誰可能呼叫誰』的關係圖。",
        "不要從第一個檔案一路讀；先從 `proxy_pass` 找到 handler，再沿呼叫與 callback 關係追蹤。",
        "NGINX 的 call graph 除了直接 function call，也包含 function pointer assignment 與 module registration。",
    ),
    "function_pointer": T(
        "Function pointer",
        "C 可以把函式位址存進變數或 struct 欄位，之後再透過該欄位呼叫。它常用來模擬 interface 或 method。",
        "`event.handler = read_request` 表示未來 event ready 時要呼叫 `read_request`。",
        "NGINX 用 function pointers 注入 event handler、module hook、filter 與 upstream protocol callback。",
    ),
    "module": T(
        "Module（模組）",
        "一組遵守固定介面的功能程式碼，可以註冊設定指令、request handler、filter 或 lifecycle hook。",
        "Proxy、gzip、access control 都是不同 modules，但共同掛在 NGINX core 提供的擴充點。",
        "Core 負責協調生命週期；module 專注自己的 configuration 與 request 行為。",
    ),
    "pointer": T(
        "Pointer（指標）",
        "Pointer 保存另一塊記憶體的位址。`p->field` 表示到 `p` 指向的 object 取出 `field`。",
        "函式收到 `ngx_http_request_t *r`，並不是複製整個 request，而是取得它的位置。",
        "讀 NGINX 時要同時追 pointer 指向誰、object 由誰擁有，以及 object 何時失效。",
    ),
    "macro": T(
        "Macro（巨集）",
        "C preprocessor 在編譯前做文字展開。Macro 看起來像函式或常數，但可能沒有型別檢查，也可能多次使用參數。",
        "`ngx_string(\"ok\")` 會展開成一個帶長度與 data pointer 的初始化值。",
        "NGINX 用 macros 減少平台差異與重複樣板；讀 source 時必要時先看展開後的概念。",
    ),
    "intrusive_container": T(
        "Intrusive container",
        "資料結構的 link node 直接嵌在業務 object 裡，而不是另外配置 wrapper node。",
        "Timer object 內含 rbtree node；已知 node 位址後，可計算回原本的 timer/event object。",
        "這能減少 allocation 與 pointer chasing，但要求讀者理解 container-of 與 object lifetime。",
    ),
    "lifetime": T(
        "Lifetime / ownership",
        "Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。",
        "Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。",
        "NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。",
    ),
    "process": T(
        "Process（行程）",
        "Process 是正在執行的程式實例，擁有自己的虛擬記憶體與 OS resources。",
        "啟動 `nginx` 後，可能有一個 master process 和多個 worker processes。",
        "NGINX 利用 process isolation 使用多核心並限制單一 crash 的影響範圍。",
    ),
    "initialization": T(
        "Initialization order",
        "大型程式啟動時，後一步常依賴前一步產生的資料；因此初始化不是可以任意排列的函式清單。",
        "必須先解析 config，才能知道要建立哪些 listening sockets。",
        "NGINX 依序建立 log、cycle、module configuration、sockets 與 workers，失敗時回滾尚未公開的資源。",
    ),
    "socket": T(
        "Socket",
        "Socket 是程式與網路連線互動的 OS object。程式用它 listen、accept、connect、read 與 write。",
        "Listening socket 等待新客人；accepted socket 則只代表某一位 client 的 TCP connection。",
        "NGINX 把 socket 包裝成 `ngx_connection_t`，再附加 read/write events 與 protocol state。",
    ),
    "fork": T(
        "fork",
        "`fork()` 建立一個新的 child process；child 一開始看見 parent 記憶體的邏輯副本，但之後各自執行。",
        "Master 完成設定後 fork workers，讓它們繼承 listening sockets。",
        "這讓 workers 共用啟動結果，同時保持故障與一般 heap 更新彼此隔離。",
    ),
    "lexer_parser": T(
        "Lexer 與 parser",
        "Lexer 把字元切成 token；parser 再依文法把 tokens 組成有意義的結構。",
        "`proxy_read_timeout 3s;` 可被切成指令名、參數與分號，再交給對應 module。",
        "NGINX config loader 讀 token、尋找 directive command table，並檢查參數與所在 context。",
    ),
    "directive": T(
        "Directive（設定指令）",
        "設定檔中的一條命令，由名稱與參數構成，告訴某個 module 建立或修改 configuration。",
        "`listen 443 ssl;` 與 `proxy_pass http://app;` 都是 directives。",
        "每個 module 用 command table 宣告自己認識哪些 directives 及其 setter callback。",
    ),
    "config_context": T(
        "Configuration context 與 merge",
        "同一設定可能出現在全域、server 或 location；merge 是把父層預設值與子層覆寫組成最終設定。",
        "父 location 設 timeout 30 秒，子 location 可改成 3 秒；沒改的欄位繼承父層。",
        "NGINX 在 config time 建立多份 conf object，runtime request 只需選擇合併後的結果。",
    ),
    "generation": T(
        "Configuration generation",
        "一次完整載入的設定與相關資源稱為一個 generation。新舊 generation 可以暫時同時存在。",
        "Reload 後新 workers 使用新路由；舊 workers 繼續用舊設定完成既有 requests。",
        "`ngx_cycle_t` 是一個 generation 的根 object，集中持有 sockets、files、shared memory 與 module conf。",
    ),
    "shared_memory": T(
        "Shared memory",
        "可被多個 processes 看見的同一塊記憶體。因為會同時讀寫，所以通常需要 atomic operation 或 lock。",
        "所有 workers 共用 rate-limit counter，不能只存在某一個 worker 的一般 heap。",
        "NGINX 用 shared memory zones 保存 cache metadata、upstream state 與跨 worker counters。",
    ),
    "master_worker": T(
        "Master–worker model",
        "Master 負責控制與生命週期；workers 負責大量日常資料處理。兩者刻意分工。",
        "Master 收到 reload signal 後建立新 workers；worker 的 event loop 實際讀寫 client sockets。",
        "這把低頻 control plane 與高頻 data plane 分開，簡化 worker hot path。",
    ),
    "thread_process": T(
        "Process 與 thread 的差別",
        "同一 process 內的 threads 共用大部分記憶體；不同 processes 通常彼此隔離。兩者都可以被 OS 排程到 CPU。",
        "Thread 間共享 object 很方便，但需要同步；worker processes 的一般 request state 則天然分離。",
        "NGINX 主要用多 workers 擴充 CPU，少數 blocking 工作才交給 thread pool。",
    ),
    "graceful_reload": T(
        "Graceful reload",
        "載入新設定時不立刻殺死舊工作，而是先啟動新 generation，再讓舊 generation 停止接新工作並逐步退出。",
        "部署新 certificate 時，正在下載檔案的 client 不會立刻被 reset。",
        "NGINX master 驗證新 cycle、啟動新 workers，向舊 workers 發送 graceful shutdown 訊號。",
    ),
    "draining": T(
        "Draining 與 in-flight work",
        "In-flight 是已開始但尚未完成的工作；draining 是停止接新工作，同時等待 in-flight 工作結束。",
        "餐廳打烊後不再接新單，但仍把廚房中已下的單做完。",
        "舊 worker 關閉 idle listeners/keep-alive admission，完成 active requests 後退出。",
    ),
    "long_lived_connection": T(
        "Long-lived connection",
        "持續很久而不是每個 request 結束就關閉的連線，可能大部分時間沒有資料。",
        "WebSocket、長時間下載與 streaming response 都可能存活數分鐘或數小時。",
        "它們會延長舊 worker、舊 config 與 connection resources 的存活時間。",
    ),
    "kernel_userspace": T(
        "Kernel space 與 user space",
        "Kernel 是作業系統中有權管理 CPU、memory、files 與 network devices 的核心；NGINX 在限制較多的 user space 執行，必須透過 system call（程式請作業系統工作的入口）請 kernel 工作。",
        "網卡收到封包後先由 kernel 放入 socket buffer；NGINX 之後呼叫 `recv()` 取走 bytes。",
        "Epoll 的 interest set 與 ready list 位於 kernel；NGINX 保存更高層的 request 與 callback state。",
    ),
    "file_descriptor": T(
        "File descriptor（fd）",
        "Fd 是 process（正在執行的程式實例）內的一個小整數，用來引用 kernel 管理的 file、socket 或 pipe。它是索引，不是網路資料本身。",
        "`fd = 8` 可能代表某條 client socket；close 後數字 8 可以被下一個 socket 重用。",
        "NGINX 用 fd 做 syscall，並用 `ngx_connection_t` 補上 owner、events、log 與 generation 資訊。",
    ),
    "tcp_stream": T(
        "TCP byte stream",
        "TCP 提供可靠、有順序的 bytes，但沒有 application message boundary。資料可以被任意拆分或合併。",
        "Sender 一次送出 `GET / HTTP/1.1`，receiver 可能先讀到 `GET / HT`，下一次才讀到其餘部分。",
        "NGINX parser 必須支援 partial read，不能假設一次 `recv()` 得到完整 HTTP request。",
    ),
    "nonblocking_eagain": T(
        "Non-blocking I/O 與 EAGAIN",
        "Non-blocking socket 在目前不能前進時立即返回，而不是讓整個 worker 睡在 `read()` 或 `write()` 裡。EAGAIN 表示『現在沒有，之後再試』。",
        "Client 尚未送下一段 body 時，`recv()` 回 EAGAIN；worker 去處理別的 connections。",
        "NGINX 保存 parser/output state，等待 epoll 再次通知 readiness 後由 callback 繼續。",
    ),
    "accept": T(
        "listen、accept 與 connection queue",
        "Server 先用 listening socket 表示願意接收某個 address/port；kernel 排隊已完成握手的 connections，程式再用 `accept()` 取出其中一條。",
        "門口叫號系統先收集到店客人；櫃台每次叫一位進來，建立專屬服務紀錄。",
        "NGINX 收到 listening fd readable 後 accept clients，為每條 accepted fd 配置 connection object。",
    ),
    "connection_pool": T(
        "Connection slot / object pool",
        "預先準備一批可重用 object；需要時取一個，結束時清理並歸還，避免高頻 malloc/free。",
        "`worker_connections 1024` 代表 worker 可管理的 connection slots 有上限，不只計算 client。",
        "NGINX 將 read/write event objects 內嵌於 connection slot，重用時用 instance bit 辨識舊通知。",
    ),
    "readiness": T(
        "Readiness（可前進狀態）",
        "Readiness 只表示某個 I/O 操作現在『可能取得進展』，不表示完整 request 已抵達或整個 response 已送完。",
        "Readable 可能只有 3 bytes、EOF（對方已關閉）或 error；writable 可能只能再送一小段。",
        "Epoll 回報 readiness 後，NGINX 的 handler（回呼函式）仍要呼叫 `recv()`／`send()`；EAGAIN 表示這次已無法再前進，應回 event loop 等下次通知。",
    ),
    "select": T(
        "select / poll 的基本模型",
        "Application 每次等待前交出一批想觀察的 fds；返回後還要檢查哪些項目 ready。模型簡單，但大量 idle fds 時，重建與掃描成本會持續發生。",
        "每秒逐間敲一萬個房門問『有事嗎』，即使只有兩個房間真的需要服務。",
        "NGINX 支援不同 event backends；在 Linux 大量 connections 的常見情況下通常選 epoll。",
    ),
    "epoll": T(
        "epoll",
        "Linux kernel 提供的 readiness 通知機制。Application 先登記關心哪些 fd/event，之後 `epoll_wait()` 主要取回目前 ready 的項目。Epoll 不讀寫資料，也不替你執行 handler。",
        "櫃台先留下所有房號，只有房間按服務鈴時才收到通知，不必不停敲每扇門。",
        "NGINX 用 `epoll_ctl` 更新 interest set，用 `epoll_wait` 取得 ready events，再呼叫對應 `ngx_event_t.handler`（事件回呼函式）。",
    ),
    "interest_set": T(
        "Interest set 與 ready list",
        "Interest set 是 application 想監看的 fd/event；ready list 是 kernel 判斷目前可前進的那個子集合。",
        "監看 10,000 條 connections 的 READ，但這一刻可能只有 fd 8 與 fd 91 有資料。",
        "NGINX 只在確實需要時關注 write readiness，送完 pending output 後移除 interest，避免空轉。",
    ),
    "keep_alive": T(
        "HTTP keep-alive",
        "完成一個 HTTP request 後不立刻關閉 TCP connection，讓同一 client 之後可在同一條連線上再送 request，省下重新建立 TCP 連線的時間。",
        "瀏覽器用同一條 connection 先取 HTML，再依序取圖片與 API response。",
        "NGINX finalize 舊 request、清除 request-lifetime state，再把 connection handler 改成等待下一個 request。",
    ),
    "websocket": T(
        "WebSocket",
        "一種長時間、雙向傳訊協定。它通常先用 HTTP Upgrade 把連線切換成 WebSocket，之後 client 與 server 都能主動傳送一小段一小段的訊息；連線可能長時間沒有資料但仍保持開啟。",
        "聊天室不用每秒重新發 HTTP request 問『有新訊息嗎』，server 可在有訊息時直接推送。",
        "對 epoll 而言它仍是一條 socket；長時間 idle 正是不能逐 fd 掃描或一連線一 thread 的典型情境。",
    ),
    "trigger_modes": T(
        "Level-triggered 與 edge-triggered",
        "Level-triggered（LT）在條件持續成立時會繼續提醒；edge-triggered（ET）主要在狀態從不可用變成可用的那一刻提醒。",
        "LT 像燈只要門沒關就一直亮；ET 像門鈴只在門被推開的瞬間響一次。",
        "ET handler 通常要持續 `recv()`／`send()` 直到 EAGAIN，否則剩餘資料可能沒有新的狀態邊緣來提醒。",
    ),
    "event_object": T(
        "Event object",
        "把『發生什麼事件、屬於誰、之後呼叫誰、是否有 timer』集中保存的 object。",
        "同一條 connection 有 read event 與 write event，各自可以指向不同 callback。",
        "`ngx_event_t` 用 `data` 找回 owner，用 `handler` 保存 continuation，並帶有 ready/timedout/active 等 flags。",
    ),
    "state_machine": T(
        "State machine（狀態機）",
        "把流程表示成有限狀態與允許的轉移。遇到等待時保存目前 state；事件到來後從該 state 繼續。",
        "CONNECTING → SENDING → READING_HEADER → STREAMING_BODY → DONE。",
        "NGINX 常把 state 分散在 struct fields 與可替換 callbacks，而不是寫成一個巨大 switch。",
    ),
    "protocol": T(
        "Protocol（協定）",
        "通訊雙方對資料格式、順序與錯誤處理的共同規則。TCP 只提供 bytes；HTTP 再定義 request/response 語意。",
        "同樣的 socket API 可以承載 HTTP、WebSocket、SMTP 或自訂 binary protocol。",
        "NGINX event layer 不理解 HTTP；HTTP/stream/mail layers 透過 callbacks 注入各自的解析與處理。",
    ),
    "event_loop": T(
        "Event loop",
        "單一執行流程反覆等待 events，取回 ready work，呼叫短小 handlers，然後回到等待。",
        "A 讀一段、B 寫一段、處理一個 timer，再回來讀 A 的下一段。",
        "NGINX worker event loop 協調 accept、read/write readiness、posted events 與 expired timers。",
    ),
    "scheduler": T(
        "Scheduler、公平性與 starvation",
        "Scheduler 決定下一個執行誰；fairness 表示不同工作都有前進機會；starvation 是某類工作長期搶不到執行。",
        "若 accept handler 一次無限接新 connections，已連線 client 的 response 可能一直延遲。",
        "NGINX 控制每輪 work、posted event 順序與 accept 策略，避免單一來源壟斷 event loop。",
    ),
    "timer": T(
        "Timer 與 deadline",
        "Timer 表示某個時間到達後執行工作；deadline 是某件事最晚必須完成的時刻。它們讓無事件的失敗仍能被發現。",
        "Backend 30 秒都沒回 header，即使 socket 沒有新 event，也必須 timeout。",
        "NGINX 將 event timer 放入有序結構，event loop 用最近 deadline 決定 `epoll_wait` 最長睡多久。",
    ),
    "posted_event": T(
        "Posted event",
        "已經可以執行，但刻意放入 queue 稍後處理的 callback。這能打斷深遞迴或調整同一輪的執行順序。",
        "Read handler 不立刻巢狀呼叫另一長串 handler，而是把它排到目前 callback 返回後。",
        "NGINX 用 posted queues 協調 accept、I/O callbacks 與 request continuations。",
    ),
    "red_black_tree": T(
        "Red-black tree（紅黑樹）",
        "一種保持大致平衡的排序樹，使查找、插入與刪除通常維持 O(log n)。重點不是旋轉公式，而是它支援的 operations。",
        "數萬個 timers 依 deadline 排序；需要快速找最早到期者，也要任意取消其中一個。",
        "NGINX 將 timer node intrusive 地放進 event object，最左節點就是下一個 deadline。",
    ),
    "backpressure": T(
        "Backpressure（背壓）",
        "下游處理不過來時，限制上游繼續產生或讀入資料，讓系統內的待處理資料有明確上限。",
        "Backend 每秒產生 10 MB，但手機只能收 100 KB；不能無限把差額塞進 memory。",
        "NGINX 依 buffer 水位暫停 upstream read，等 client write 消耗資料後再恢復。",
    ),
    "buffering": T(
        "Buffering 與 streaming",
        "Buffering 先暫存資料以吸收兩端速度差；streaming 則資料一到便逐段往下游傳，不等待完整內容。",
        "小 response 可留在 memory；大 response 可能落 temporary file；即時事件適合 streaming。",
        "NGINX 依 module/config 在 latency、memory、disk I/O 與 backend connection 占用之間取捨。",
    ),
    "producer_consumer": T(
        "Producer、consumer 與水位",
        "Producer 產生資料，consumer 消耗資料。High/low watermark 是何時暫停與恢復 producer 的容量門檻。",
        "Upstream 是 response producer，慢速 client 是 consumer。",
        "Event pipe 追蹤 free/busy buffers 與 downstream write 結果，形成 bounded pipeline。",
    ),
    "request_object": T(
        "`ngx_http_request_t`",
        "代表一次 HTTP request/response 交換的核心 object，不等於底層 TCP connection。",
        "同一 keep-alive connection 可以先後建立兩個不同 request objects。",
        "它保存 method、URI、headers、body、module contexts、routing、upstream 與 output state。",
    ),
    "http_parts": T(
        "Method、URI、headers、body",
        "Method 表示動作，URI 表示目標，headers 是控制資訊，body 是可選內容。",
        "`POST /orders` 加 `Content-Type: application/json` 與 JSON body。",
        "NGINX 分階段解析這些部分，並讓 routing、access、proxy 與 filter modules 讀取結果。",
    ),
    "incremental_parser": T(
        "Incremental parser",
        "資料不完整時不阻塞也不丟失進度，而是保存 parser state；下一段 bytes 到來後繼續。",
        "第一次只收到 `GET / HT`，parser 記住目前在 version 前；第二次從該位置繼續。",
        "NGINX request line/header parser 回報 AGAIN、DONE 或 ERROR，state 保存在 request/parse fields。",
    ),
    "http_framing": T(
        "HTTP framing",
        "Framing 是判斷一個 request 或 body 在 byte stream 中從哪裡開始、哪裡結束的規則。",
        "`Content-Length: 10` 表示讀十個 body bytes；chunked encoding 則每段先給長度，最後以零長 chunk 結束。",
        "NGINX 必須拒絕矛盾或含糊的 framing，否則 proxy 前後端可能對邊界產生不同理解。",
    ),
    "request_smuggling": T(
        "Request smuggling",
        "前端 proxy 與 backend 對 request 邊界理解不同時，攻擊者可讓一段 bytes 被一端視為 body、另一端視為下一個 request。",
        "同時出現互相衝突的 Content-Length 與 Transfer-Encoding 是典型危險輸入。",
        "NGINX header parser 與 upstream encoder 必須使用一致、保守且不可含糊的 framing policy。",
    ),
    "virtual_location": T(
        "Virtual server 與 location",
        "Virtual server 依 address/hostname 選網站；location 再依 URI 選該網站中的處理規則。",
        "`api.example.com` 與 `static.example.com` 可共用 IP；前者的 `/v1/` 再走 proxy。",
        "NGINX config time 建立查找結構，request time 依 Host 與 URI 取得合併後 configuration。",
    ),
    "regex": T(
        "Regular expression（正規表示式）",
        "用模式描述一組字串，適合複雜匹配，但通常比精確或 prefix 查找更昂貴且較難推理。",
        "`~ \\.php$` 匹配以 `.php` 結尾的 URI。",
        "NGINX location matching 有固定優先規則，不能把所有 location 當成由上到下的普通 if。",
    ),
    "phase_engine": T(
        "HTTP phase engine",
        "把 request 處理拆成有順序的階段，每個 module 可以把 handler 註冊到適合的階段。",
        "先 rewrite URI，再做 access control，最後產生或 proxy content。",
        "NGINX 在 config time 編譯 handler pipeline，runtime 用 return code 決定繼續、跳轉、暫停或結束。",
    ),
    "handler_return": T(
        "Handler 與 return code contract",
        "Handler 是處理一小段責任的函式；它的 return code 不是隨意數字，而是告訴框架下一步。",
        "`DECLINED` 可表示『我不處理，交給下一個』；`AGAIN` 表示 async 工作尚未完成。",
        "讀 NGINX source 時必須同時看 caller 如何解釋回傳值，不能只讀 handler 本身。",
    ),
    "request_body": T(
        "Request body",
        "Headers 後面的可選內容，可能是 JSON、表單或大型檔案；它可以分多次抵達。",
        "上傳 4 GB 檔案時，不能先把全部內容放進 memory 才開始處理。",
        "NGINX 依 framing 增量讀 body，並按 module/config 選 memory buffer、temporary file 或 streaming。",
    ),
    "buffer": T(
        "Buffer",
        "一段可讀或可寫的資料範圍，加上目前讀到哪裡、送到哪裡等位置資訊。",
        "8 KB memory 裡只有索引 100–340 是尚未送出的資料。",
        "`ngx_buf_t` 可以描述 memory 或 file range；位置前進即可表示 partial read/write，而不必複製內容。",
    ),
    "response_filter": T(
        "Response 與 filter chain",
        "Content handler 產生 response；filters 依序檢查或轉換 headers/body，再交給下一層。",
        "Proxy body 先經 gzip，再套 chunked framing，最後寫入 socket。",
        "NGINX 用 top/next function pointers 串接 filters，新增功能不必修改每個 content module。",
    ),
    "http_status": T(
        "Status、response headers 與 body",
        "Status 表示結果類型，headers 描述 response metadata，body 才是主要內容；某些 method/status 不允許 body。",
        "`204 No Content` 不應附一般 response body；HEAD 回覆 headers 但不傳實際 body。",
        "Module 必須先正確設定 headers，再呼叫 header/body filter，並遵守 Content-Length 與 final flags。",
    ),
    "finalize": T(
        "Finalize",
        "把分散的成功、錯誤與 async completion 統一帶到同一個收尾協定，確保 request 只真正結束一次。",
        "Client abort 與正常完成最後都要取消 timers、執行 cleanup，並決定 connection close 或 keep-alive。",
        "NGINX 用 request count、buffered flags 與 finalize functions 協調多個 callbacks 的共同終點。",
    ),
    "reference_count": T(
        "Reference count",
        "用數字表示還有多少未完成工作需要某 object；只有歸零後才能安全釋放。",
        "Main request 啟動兩個 subrequests，必須等兩者都完成才能整體 finalize。",
        "NGINX request count 是 async branches 的 join gate；漏減造成 leak，重複減可能 use-after-free。",
    ),
    "subrequest": T(
        "Subrequest",
        "由一個 request 在 NGINX 內部建立的子 request，用同一套 HTTP phase/filter machinery 取得額外內容。",
        "主頁 response 中的一小段內容由內部 location 生成。",
        "Subrequest 不是新的 client TCP connection；它與 main request 共享部分 context 並受 reference count 管理。",
    ),
    "proxy_pass": T(
        "`proxy_pass`",
        "告訴 NGINX：這個 location 的 content 不在本機產生，而要轉成另一個 HTTP request 送往 upstream。",
        "`location /api/ { proxy_pass http://app; }` 將 `/api/` requests 交給 backend group。",
        "Proxy module 處理 URI、headers、body、timeouts 與 buffering，再呼叫通用 upstream framework。",
    ),
    "upstream": T(
        "Upstream",
        "從 NGINX 角度看出去的 backend 交易或 backend 群組。它不是 client 連進來的那條 connection。",
        "一次 client request 可能建立一條 upstream connection 到 `app-2:8080`。",
        "`ngx_http_upstream_t` 保存 peer selection、connect/send/read state、retry、buffering 與 timing。",
    ),
    "peer": T(
        "Peer",
        "一個可被選來連線的遠端 endpoint，通常是一台 backend 的 IP/port 加上權重與健康狀態。",
        "Upstream group 有 app-1、app-2、app-3；某次 request 選 app-2 作為 peer。",
        "Balancer 的 get callback 選 peer；free callback 回報 success/failure，讓後續選擇調整。",
    ),
    "protocol_adapter": T(
        "Protocol adapter",
        "把共用 transport state machine 與特定協定的編碼／解析分離。",
        "HTTP proxy、FastCGI 與 memcached 都需要 connect/retry/timeout，但 request bytes 與 response parser 不同。",
        "NGINX upstream core 管 async transport；各 module 提供 create_request、process_header 等 callbacks。",
    ),
    "tcp_connect": T(
        "TCP handshake 與 connect",
        "TCP 連線建立前，雙方要交換控制封包確認彼此可達與初始狀態；這段時間可能成功、拒絕或 timeout。",
        "Backend port 沒開可能快速回 connection refused；封包被丟棄則可能長時間沒有答案。",
        "NGINX 使用 non-blocking connect，不讓 worker 等待 handshake，結果由後續 write readiness 與 socket error 確認。",
    ),
    "einprogress": T(
        "EINPROGRESS 與 writable",
        "Non-blocking `connect()` 回 EINPROGRESS 表示尚未完成，不是成功也不是失敗。之後 writable 只表示結果可查。",
        "門鈴已按下但屋主尚未回應；燈亮起只表示現在可以查看結果，不保證對方接受。",
        "NGINX 在 write event 到來後讀 `SO_ERROR`，判斷 connect 成功或取得真正 error。",
    ),
    "weighted_rr": T(
        "Weighted round robin",
        "依 backend capacity 用不同頻率分配 requests。Weight 5:1 表示長期比例約五比一，不代表必須連續五次選同一台。",
        "大機器每六次約接五次，小機器約接一次。",
        "NGINX smooth algorithm 累加 current weight，選最大者後扣總權重，使高權重選擇均勻穿插。",
    ),
    "feedback_control": T(
        "Feedback control",
        "系統根據實際成功或失敗回饋調整下一次決策，而不是永遠使用固定參數。",
        "Backend 剛失敗時降低 effective weight，之後成功再逐步恢復。",
        "Balancer state 同時表達靜態 capacity 與動態健康程度。",
    ),
    "load_policy": T(
        "Load-balancing policy 與 workload",
        "Policy 是選擇 backend 的規則；workload 是實際 requests 的大小、時間、key 分布與失敗特性。沒有脫離 workload 的最佳 policy。",
        "短 requests 可用 round robin；長短差很多時 least connections 可能更合理。",
        "NGINX 提供 round robin、least connections、hash/random 等策略，使用者依 constraints 選擇。",
    ),
    "affinity": T(
        "Affinity 與 cache locality",
        "Affinity 讓相同 user/key 傾向同一 backend；cache locality 則希望相同資料落到已經有 cache 的節點。",
        "同一 session ID 經 hash 後總是優先選 app-2。",
        "它可減少 cache miss 或支援 legacy session，但 backend 變動時需要處理重新映射與偏斜。",
    ),
    "timeout_retry": T(
        "Timeout、deadline 與 retry",
        "Timeout 限制單一等待；deadline 限制整個操作的總時間；retry 是失敗後再嘗試另一個 peer。",
        "總預算 2 秒時，不能對三個 peers 各等待 2 秒。",
        "NGINX 依 failure stage、method/config 與剩餘 peers 決定是否呼叫 upstream next。",
    ),
    "idempotency": T(
        "Idempotency 與副作用",
        "Idempotent operation 重複執行仍等同執行一次；副作用是付款、寄信或寫入資料等外部改變。",
        "重複讀取同一資源通常安全；重複扣款則可能造成真實損失。",
        "Request body 已送往 backend 後若結果未知，proxy retry 可能重複副作用，不能只看 transport error。",
    ),
    "retry_storm": T(
        "Retry storm",
        "大量失敗 requests 同時重試會放大流量，使已經過載的 backend 更難恢復。",
        "每個 request 重試三次，原本 1,000 QPS 可瞬間變成接近 3,000 次嘗試。",
        "需要限制次數、整體 deadline、可重試條件並搭配 capacity/admission control。",
    ),
    "tls_ephemeral": T(
        "Handshake 與 ephemeral port",
        "TCP/TLS handshake 是建立新安全連線的額外往返與 CPU 成本；client 端每條 outgoing connection 還需要暫時使用一個 local port。",
        "高 QPS 短 requests 若每次重連，會浪費 latency 並可能耗盡可用 port 範圍。",
        "Upstream keepalive 重用已完成握手的 backend connection，降低 connect/TLS 與 port 壓力。",
    ),
    "upstream_keepalive": T(
        "Upstream keepalive cache",
        "保存少量已完成 request、目前 idle 且仍可重用的 backend connections。它是 cache，不是所有 requests 的固定 pool。",
        "下一個 request 可直接取出 app-1 的 idle socket，不必重新 connect。",
        "NGINX 必須檢查協定是否允許重用、connection 是否乾淨，並處理 backend 已悄悄關閉的 stale socket。",
    ),
    "event_pipe": T(
        "Event pipe",
        "協調 upstream read、buffer/temp file 與 downstream write 的 bounded pipeline。",
        "Backend 快速送 100 MB，手機很慢；event pipe 只允許有限在途資料，必要時寫 disk 或暫停 upstream read。",
        "NGINX 以 free/in/out/busy chains 與 read/write readiness 推進資料，同時維持 backpressure。",
    ),
    "cache": T(
        "Proxy cache",
        "保存 backend response，讓之後相同 cache key 的 requests 可直接重用，不必每次打 backend。",
        "熱門圖片第一次向 backend 取得，接下來一萬個 clients 從 cache 讀。",
        "NGINX 將 body 放 disk，metadata/locks 放 shared memory，並管理 key、freshness 與 eviction。",
    ),
    "cache_freshness": T(
        "Fresh、stale 與 revalidation",
        "Fresh 表示 cache 仍可直接使用；stale 表示期限已過；revalidation 是詢問 backend 內容是否真的改變。",
        "過期圖片可用 If-Modified-Since 驗證，若 backend 回 304 就延長使用。",
        "NGINX policy 決定何時更新、backend 故障時是否暫用 stale response。",
    ),
    "cache_stampede": T(
        "Cache stampede",
        "熱門 key 同時失效時，大量 requests 一起穿透到 backend，形成瞬間尖峰。",
        "一萬個 users 在同一秒發現首頁 cache 過期。",
        "NGINX 可用 cache lock 讓一個 request 更新，其餘等待或使用 stale data。",
    ),
    "heap_pool": T(
        "Heap、malloc/free 與 memory pool",
        "Heap 支援個別配置與釋放；memory pool/arena 把許多相同 lifetime 的小 allocations 綁在一起，最後整批釋放。",
        "一個 request 建立數十個 headers/nodes，逐一處理所有 error-path free 很容易遺漏。",
        "NGINX request pool 用 pointer bump 快速配置，request 結束時 destroy pool；大型 allocation 與 cleanup 另行追蹤。",
    ),
    "cleanup": T(
        "Cleanup handler",
        "Memory 消失不代表外部資源或副作用會自動復原；cleanup handler 是 object 結束時必須執行的收尾工作。",
        "Temporary file、open fd 或第三方 library handle 必須明確 close。",
        "NGINX 將 cleanup 掛在 pool，讓正常與錯誤路徑共用同一個 lifecycle 收口。",
    ),
    "data_structure": T(
        "從 operations 選資料結構",
        "先列出最常做的 operations、排序需求、刪除方式與 lifetime，再選 array、queue、hash 或 tree；不要先背資料結構名稱。",
        "Headers 常 append/iterate；timer 要找最小 deadline 並任意刪除，需求完全不同。",
        "NGINX 依 hot path 與 memory layout 選 intrusive queue、rbtree、hash、radix tree 等 containers。",
    ),
    "zero_copy": T(
        "Zero-copy 思維",
        "目標是避免把同一批 bytes 在 application buffers 間反覆複製；不代表整條路徑真的完全零次 copy。",
        "傳檔案時讓 kernel 直接把 file pages 送到 socket，比先讀進 user buffer 再 write 更省。",
        "NGINX 用 `ngx_buf_t` 描述 memory/file ranges，以 `writev` 聚合 memory，以 `sendfile` 傳 file region。",
    ),
    "buffer_chain": T(
        "Buffer chain",
        "把多段不一定連續、來源不同的資料，用 linked nodes 表示成一個輸出序列。",
        "Response headers 在 memory，body 在 file，最後還有一個 end marker。",
        "`ngx_chain_t` 串起 `ngx_buf_t`；partial write 只移動 positions，未送完 nodes 留在 busy chain。",
    ),
    "copy_on_write": T(
        "Copy-on-write",
        "Fork 後 parent/child 起初可共享相同 physical pages；某 process 寫入時才複製該 page，因此一般 heap 的更新不會自動同步給其他 workers。",
        "Worker A 修改自己的 counter，worker B 不會看見新值。",
        "真正跨 worker state 必須使用明確 shared memory zone，而不是依賴 fork 繼承的普通變數。",
    ),
    "slab": T(
        "Slab allocator",
        "在固定 shared memory 區域中，按大小類別管理小 objects 的 allocator。它不能像一般 heap 一樣向 OS 任意擴張。",
        "共享 cache metadata 需要從預先劃定的 zone 配置與歸還空間。",
        "NGINX slab 配合 shared mutex 管理 pages/slots，並要求所有 shared pointers 都位於可共同解讀的區域。",
    ),
    "atomic_lock": T(
        "Atomic operation 與 lock",
        "Atomic operation 對單一小更新提供不可分割性；lock 則讓一段較大的 critical section 同時只由一個執行者進入。",
        "遞增 counter 可用 atomic；同時修改 tree 多個 links 通常需要 lock。",
        "NGINX 依 invariant 選擇 atomic、spinlock/mutex，並盡量縮短 shared-memory critical section。",
    ),
    "module_system": T(
        "Module system 與 extension point",
        "Core 事先定義可插入的位置與 contract，module 再提供實作；因此新增功能不必修改主控制流。",
        "新 module 可註冊 directive、access handler 或 body filter。",
        "NGINX module descriptor、context callbacks、command table 與 indices 形成 C 語言的 plugin framework。",
    ),
    "lifecycle_hook": T(
        "Lifecycle hook",
        "在啟動、configuration 完成、worker 初始化或退出等固定時機，由 framework 呼叫 module callback。",
        "Module 在 worker init 建立 per-process resource，在 exit 時釋放。",
        "正確 hook 讓 resource lifetime 與 process/cycle 對齊，避免 request path 臨時做昂貴初始化。",
    ),
    "content_handler": T(
        "Content handler",
        "在 HTTP phase pipeline 中負責真正產生 response，或啟動一個之後會產生 response 的 async 工作。",
        "Hello module 直接回文字；proxy handler 則啟動 upstream 交易。",
        "Handler 必須設定 status/headers/body，正確使用 filters，並遵守 HEAD、partial write 與 finalize contract。",
    ),
    "access_control": T(
        "Authentication、authorization 與 access phase",
        "Authentication 確認你是誰；authorization 判斷你能做什麼。Access phase 是 content 工作前做允許／拒絕決策的位置。",
        "API key 可識別 caller，但是否能存取 admin endpoint 是另一個授權決策。",
        "NGINX access handler 回 OK、DECLINED 或 HTTP error，並與其他 access modules/satisfy policy 共存。",
    ),
    "fail_closed": T(
        "Fail closed",
        "發生解析、設定或驗證錯誤時預設拒絕，而不是因為檢查失敗就放行。",
        "Token verifier timeout 時回 503/拒絕，不能把它當成『驗證通過』。",
        "Security-sensitive NGINX modules 必須讓每個 error branch 都有明確且保守的結果。",
    ),
    "lazy_variable": T(
        "Variable 與 lazy evaluation",
        "Variable 提供統一名稱取得 request data；lazy evaluation 表示只有真的被 log/rewrite/header 使用時才計算。",
        "沒有任何 consumer 使用 request ID 時，不必為每個 request 都產生它。",
        "NGINX variable get handler 第一次被查詢時產生 value，並依 cache flags 決定是否重用。",
    ),
    "correlation_id": T(
        "Correlation ID",
        "在同一個邏輯 request 經過多個 logs/services 時保持不變的識別碼，用來把分散事件串回同一條因果鏈。",
        "`req-7f2a` 同時出現在 client response header、NGINX access log 與 backend log。",
        "值應 request-scoped、只生成一次，並避免在 subrequest/filter 重入時重複加入 header。",
    ),
    "streaming_filter": T(
        "Streaming body filter 與 chunk boundary",
        "Filter 每次只看到一部分 bytes；任意語意 token 可能跨兩個 buffers，因此不能把每個 chunk 當完整字串。",
        "第一段以 `f` 結尾、第二段以 `oo` 開頭，合起來才是 `foo`。",
        "NGINX module ctx 保存跨 callback carry state，並傳遞 flush、sync、last 等 buffer flags。",
    ),
    "config_runtime": T(
        "Config time 與 request time",
        "Config time 低頻地解析規則並建立可重用資料；request time 高頻地使用結果，應避免重做相同工作。",
        "Backend 清單與 hash ring 在 reload 時建立；每個 request 只做選擇。",
        "NGINX modules 常有 main/server/location conf 與 per-request ctx，兩者 lifetime 不可混用。",
    ),
    "balancer_callbacks": T(
        "Balancer get/free callbacks",
        "`get` 在一次連線嘗試前選 peer；`free` 在嘗試結束後回報結果。選擇與回饋是同一 contract 的兩半。",
        "先選 latency score 最低的 peer；connect 失敗後增加它的 failure penalty。",
        "NGINX per-request tried state 防止同一次 retry 重複選到已失敗 peer，shared state 則處理跨 worker visibility。",
    ),
    "testing_layers": T(
        "不同問題需要不同測試",
        "Source correctness、protocol edge case、failure recovery 與 performance 是不同問題，不能只用一次成功的 curl 證明。",
        "Fragmented input test parser；slow client test backpressure；profiler 找 CPU hot path。",
        "NGINX/module 驗證需組合 unit/black-box/fault injection/debug log/syscall trace 與 benchmark。",
    ),
    "profiler": T(
        "Profiler 與 flame graph",
        "Profiler 以抽樣或 instrumentation 統計 CPU 時間花在哪些 call stacks；flame graph 把熱門 stack 視覺化。",
        "Worker CPU 100% 時，先確認時間在 application handler、regex、copy 還是 busy event wake-up。",
        "效能分析必須在代表性 workload 下進行，並同時觀察 latency、throughput 與資源使用。",
    ),
    "patch_invariant": T(
        "Patch、regression 與 invariant",
        "Patch 是一次程式差異；regression 是修改使舊功能退步；invariant 是每條路徑都必須維持的條件。",
        "修正 stale flag 時，要測正常路徑、timeout、fd reuse 與舊平台，證明沒有引入新問題。",
        "讀 NGINX bug fix 時先找被破壞的 invariant，再看三行 diff，才能理解修改位置為何必要。",
    ),
    "compatibility": T(
        "Backward compatibility",
        "新版本仍維持既有設定、協定或 module 所依賴的行為，避免升級造成無預警破壞。",
        "看似更乾淨的 return code 改法，可能破壞第三方 module 的既有判斷。",
        "成熟 NGINX code review 會把 API/ABI、平台差異、舊 config 與 error behavior 納入成本。",
    ),
    "layering": T(
        "Layering 與 dependency direction",
        "底層提供通用能力，上層加入特定語意；dependency 應主要由上層指向底層，而不是讓底層知道所有上層協定。",
        "Socket layer 只回報 bytes/readiness；HTTP layer 才理解 method 與 location。",
        "NGINX 用 listening handler、event callbacks 與 module hooks 反轉控制，讓 HTTP、stream、mail 共用 connection layer。",
    ),
    "technical_debt": T(
        "Trade-off 與 technical debt",
        "Trade-off 是為取得某些好處而接受成本；technical debt 是早期選擇在新需求下產生的持續維護負擔。",
        "Global module indices 在 C 中高效，但讓動態擴充與推理更困難。",
        "評估 NGINX 設計要區分核心 invariant、當年環境限制、相容性成本與今天可改善的部分。",
    ),
    "transfer_model": T(
        "可遷移的閱讀模型",
        "不要只記函式名稱；用事件來源、state owner、喚醒方式、backpressure、resource ownership 與 failure policy 描述系統。",
        "讀 Redis 或 Envoy 時，也先問『不能前進時狀態放哪裡？誰之後叫醒它？』",
        "這些問題把 NGINX 的具體實作提升成可用於其他 codebase 與 system design 的能力。",
    ),
}


CHAPTER_FOUNDATIONS = {
    1: ["reverse_proxy", "request_response", "transport", "backend", "callback"],
    2: ["observability", "syscall", "debugger", "worker"],
    3: ["codebase", "function_pointer", "module", "callback"],
    4: ["pointer", "function_pointer", "macro", "intrusive_container", "lifetime"],
    5: ["process", "initialization", "socket", "fork"],
    6: ["lexer_parser", "directive", "config_context", "module"],
    7: ["generation", "lifetime", "socket", "shared_memory"],
    8: ["master_worker", "thread_process", "worker", "fork"],
    9: ["graceful_reload", "draining", "generation", "long_lived_connection", "keep_alive"],
    10: ["kernel_userspace", "socket", "file_descriptor", "tcp_stream", "nonblocking_eagain"],
    11: ["accept", "socket", "file_descriptor", "connection_pool", "callback"],
    12: ["kernel_userspace", "file_descriptor", "readiness", "select", "epoll", "interest_set", "keep_alive", "websocket", "trigger_modes"],
    13: ["event_object", "callback", "state_machine", "protocol", "readiness"],
    14: ["event_loop", "scheduler", "timer", "posted_event", "worker"],
    15: ["timer", "red_black_tree", "intrusive_container", "event_loop"],
    16: ["producer_consumer", "backpressure", "buffering", "event_loop"],
    17: ["request_object", "http_parts", "transport", "keep_alive", "lifetime"],
    18: ["tcp_stream", "incremental_parser", "state_machine", "nonblocking_eagain"],
    19: ["http_framing", "http_parts", "request_smuggling", "incremental_parser"],
    20: ["virtual_location", "regex", "config_context", "request_object"],
    21: ["phase_engine", "handler_return", "module", "config_runtime"],
    22: ["request_body", "http_framing", "buffer", "buffering", "nonblocking_eagain"],
    23: ["http_status", "response_filter", "buffer_chain", "handler_return"],
    24: ["finalize", "reference_count", "subrequest", "keep_alive", "lifetime"],
    25: ["proxy_pass", "reverse_proxy", "upstream", "protocol_adapter", "buffering"],
    26: ["upstream", "peer", "state_machine", "callback", "protocol_adapter"],
    27: ["tcp_connect", "nonblocking_eagain", "einprogress", "readiness"],
    28: ["weighted_rr", "peer", "feedback_control", "load_policy"],
    29: ["load_policy", "affinity", "peer", "feedback_control"],
    30: ["timeout_retry", "idempotency", "retry_storm", "upstream"],
    31: ["tls_ephemeral", "upstream_keepalive", "keep_alive", "lifetime"],
    32: ["event_pipe", "producer_consumer", "backpressure", "buffering", "buffer_chain"],
    33: ["cache", "cache_freshness", "cache_stampede", "shared_memory"],
    34: ["heap_pool", "lifetime", "cleanup", "pointer"],
    35: ["data_structure", "intrusive_container", "red_black_tree", "lifetime"],
    36: ["buffer", "buffer_chain", "zero_copy", "nonblocking_eagain"],
    37: ["copy_on_write", "shared_memory", "slab", "atomic_lock", "fork"],
    38: ["module_system", "directive", "config_context", "lifecycle_hook"],
    39: ["content_handler", "http_status", "response_filter", "handler_return"],
    40: ["access_control", "phase_engine", "config_context", "fail_closed"],
    41: ["lazy_variable", "correlation_id", "request_object", "response_filter"],
    42: ["streaming_filter", "buffer_chain", "backpressure", "state_machine"],
    43: ["config_runtime", "balancer_callbacks", "peer", "feedback_control", "shared_memory"],
    44: ["testing_layers", "observability", "profiler", "syscall"],
    45: ["patch_invariant", "compatibility", "lifetime", "testing_layers"],
    46: ["layering", "transport", "protocol", "callback"],
    47: ["technical_debt", "compatibility", "layering", "lifetime"],
    48: ["transfer_model", "state_machine", "backpressure", "lifetime", "timeout_retry"],
}


DEEP_PRIMERS = {
    12: r"""
### 從一條 connection 一直等，到讓一個 worker 管理數萬條 connection

先看最直覺、也最容易卡住的 server：

```python
while True:
    client, address = listening_socket.accept()
    request = client.recv(4096)   # client 沒送資料時，整個執行流程停在這裡
    client.sendall(handle(request))
    client.close()
```

這個版本一次只能照顧一位 client。第二位 client 即使資料已經到達，也必須等第一位完成。常見的第一個改進是「每條 connection 一個 thread」，但一萬條大多 idle 的 connections 會帶來大量 thread stack（每條 thread 保存函式呼叫與 local variables 的記憶體）、context switch（OS 暫停一條 thread 並切換到另一條的成本）與同步成本。

NGINX 採另一種模型：

```text
connections 擁有各自的 state 與 callback
             │
             ▼
worker 把想等待的 fd/event 登記給 kernel
             │
             ▼
        epoll_wait()
             │
       只取回 ready subset
             │
             ▼
呼叫短小 handler；不能前進就保存 state 並返回
```

### `select` 與 `epoll` 差在哪裡？

假設 worker 管理 10,000 條 connections，但此刻只有 fd 8 與 fd 91 有資料：

```text
select/poll 的思考方式

每一輪交出／檢查大量 fd
fd 0?  fd 1?  fd 2?  ...  fd 9999?
        最後找出 [8, 91]

epoll 的思考方式

一次維護 interest set：
READ = {0, 1, 2, ... 9999}

每次等待主要取回 ready list：
[8 READABLE, 91 READABLE]
```

重要的是模型差異，不要把複雜度口號背成絕對定律。Epoll 的優勢最明顯於「很多 connections、大多數 idle、每次只有少數 ready」；若只有十條 connections，兩者差異可能毫無實務意義。

### Epoll 的三個動作

1. `epoll_create`：建立一個 kernel 內的 epoll instance。
2. `epoll_ctl`：新增、修改或刪除 interest，例如「fd 8 目前要等 READ」。
3. `epoll_wait`：目前沒有工作時讓 worker 睡眠，直到有 ready event 或 timeout。

```text
NGINX / user space                    Linux kernel

epoll_ctl(fd=8, READ)  ────────────> interest set 加入 fd 8
epoll_ctl(fd=9, WRITE) ────────────> interest set 加入 fd 9

epoll_wait(timeout)     ───────────> 等待 socket 狀態改變
                         <────────── [fd 8 READ, fd 9 WRITE]

recv(fd=8)              ───────────> 真正把 bytes 從 socket buffer 取走
send(fd=9)              ───────────> 真正把 bytes 放入 send buffer
```

Epoll 只負責「通知」，`recv`／`send` 才負責搬資料。因此 `EPOLLIN` 不等於「完整 HTTP request 已經好了」，`EPOLLOUT` 也不等於「整個 response 已經送完」。

### 為什麼 keep-alive、WebSocket 特別需要這個模型？

- HTTP keep-alive：一個 request 完成後，TCP connection 留著等待下一個 request。等待期間可能數秒都沒有 bytes。
- WebSocket：HTTP Upgrade 後變成長時間雙向 channel，可能維持數小時，但大部分時間 idle。
- 慢速 client：每次只傳或只接收少量 bytes；worker 不能為它停住。

如果使用逐 fd 掃描，idle connections 仍會持續產生檢查成本；如果使用一 connection 一 thread，idle connections 仍占用 thread resources。Epoll 讓 idle connection 主要只占 connection state 與 kernel registration，真正 ready 時才消耗 handler CPU。

### Epoll 沒有解決什麼？

- 不會把一個 request 自動分配到另一條 thread。
- 不會讓 CPU-heavy 或呼叫 `sleep()` 的 handler 變快。
- 不會替 application 保存 HTTP parser state。
- 不會保證一次 read/write 完成。
- 不會自動提供 fairness、timeout、retry 或 backpressure。

所以 NGINX 還需要 `ngx_event_t`、callbacks、timers、request/upstream state machines 與 bounded buffers。Epoll 是事件來源，不是整個架構。
""",
}


assert set(CHAPTER_FOUNDATIONS) == set(range(1, 49))
assert all(len(keys) >= 4 for keys in CHAPTER_FOUNDATIONS.values())
assert all(key in TERMS for keys in CHAPTER_FOUNDATIONS.values() for key in keys)
