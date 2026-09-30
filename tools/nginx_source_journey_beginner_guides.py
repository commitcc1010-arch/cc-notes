"""Beginner-first teaching scaffolding for every NGINX source chapter.

The core curriculum explains mechanisms.  This module supplies the missing
orientation layer: why a component exists, where it sits in the whole system,
what contract it fulfils, how data flows through it, and which implementation
patterns are worth noticing before opening the real source.
"""
from __future__ import annotations


STAGE_LABELS = [
    (1, "先認識系統"),
    (2, "啟動與設定"),
    (3, "連線與事件"),
    (4, "HTTP 請求"),
    (5, "代理與後端"),
    (6, "核心基礎設施"),
    (7, "親手擴充"),
    (8, "架構遷移"),
]


PROLOGUE = r"""
# 導讀　如果你連 NGINX 是什麼都不知道，從這裡開始

<p class="chapter-question">先不碰任何 C 程式碼：NGINX 在真實系統裡站在哪裡、替誰工作、為什麼值得讀它的源碼？</p>

<aside class="admonition" markdown="1">
<div class="admonition-title">先給一句話版本</div>

NGINX 是一個長時間運行的網路伺服器程序。它站在 client 與 application server 之間，接住大量連線，讀懂 HTTP，依設定決定要自己回應、轉發到哪個 backend，或拒絕請求，再把 response 安全而有效率地送回 client。

</aside>

## 1. 先把名詞換成一間餐廳

想像你用手機向餐廳下單：

| 系統名詞 | 餐廳比喻 | 真實責任 |
|---|---|---|
| Client | 顧客 | 瀏覽器、手機 App、另一個服務 |
| NGINX | 櫃台與調度員 | 接單、檢查、排隊、分流、回覆 |
| Backend / Application Server | 廚房 | 執行商業邏輯，例如登入、付款、查資料 |
| Request | 一張訂單 | method、URL、headers、body |
| Response | 完成的餐點與收據 | status、headers、body |
| Connection | 顧客與櫃台間的通道 | 通常是 TCP；上面可以承載 HTTP |
| Upstream | NGINX 看出去的後端群組 | 一台或多台 backend server |

NGINX 通常不負責「使用者密碼是否正確」或「商品還剩多少」。它擅長的是網路邊界工作：大量連線、協定解析、路由、TLS、靜態檔案、負載均衡、快取、限流與故障處理。

## 2. NGINX 在部署架構中的位置

```text
                         public Internet
                               │
                     HTTPS / HTTP request
                               ▼
                    ┌────────────────────┐
                    │       NGINX        │
                    │                    │
                    │ TLS termination    │
                    │ routing            │
                    │ load balancing     │
                    │ buffering/cache    │
                    │ access control     │
                    └───────┬─────┬──────┘
                            │     │
                ┌───────────┘     └───────────┐
                ▼                             ▼
        ┌──────────────┐              ┌──────────────┐
        │ Backend A    │              │ Backend B    │
        │ app process  │              │ app process  │
        └──────┬───────┘              └──────┬───────┘
               └──────────┬──────────────────┘
                          ▼
                    DB / cache / queue
```

這張圖先回答「為什麼需要 NGINX」：

- Backend 可以專心處理商業邏輯，不必每個服務都重新實作 TLS、慢速 client、防護與靜態檔案傳輸。
- 多台 backend 需要一個穩定入口，否則 client 必須知道每台機器的位置與健康狀態。
- Client 可能非常慢或不可靠；NGINX 可以 buffer 資料，避免昂貴的 application worker 長時間被占住。
- 部署新版本或某台 backend 故障時，入口層可以重新分流，不必要求所有 client 同時更新。

## 3. 它可以扮演四種常見角色

### Web server

若請求的是圖片、CSS、下載檔案，NGINX 可以直接從磁碟或 cache 回應，不一定需要 backend。

### Reverse proxy

Client 只連 NGINX；NGINX 代表 client 連到內部 backend。這和 redirect 不同：redirect 會叫 client 自己去另一個 URL，reverse proxy 則把 backend 隱藏在內部。

### Load balancer

當同一服務有多台 backend，NGINX 依 round robin、weight、hash 或 least connections 等規則選一台。選擇不只是「平均分配」，還要處理失敗、重試、連線重用與動態負載。

### Gateway / policy enforcement point

NGINX 可以在請求進入應用程式前做 TLS termination、header normalization、access control、rate limiting、觀測與 routing。它因此也是安全與可靠性邊界。

## 4. 一個 request 的完整生命線

```text
① OS 收到 TCP 連線
      │
      ▼
② NGINX accept，取得 client socket
      │
      ▼
③ event loop 等 socket 可讀
      │
      ▼
④ 增量解析 HTTP request line / headers / body
      │
      ▼
⑤ virtual server + location 找到處理規則
      │
      ▼
⑥ phase engine 執行 rewrite / access / content
      │
      ├── 靜態檔案：直接建立 response
      │
      └── proxy_pass：建立 upstream
                        │
                        ▼
⑦ 選 backend，non-blocking connect，送 request
                        │
                        ▼
⑧ 讀 backend response，經 filter / buffer / cache
      │
      ▼
⑨ 寫回 client；完成、keep-alive 或關閉 connection
```

後面 48 章並不是 48 個互不相干的主題。它們只是在放大這條生命線，並補上「程序如何啟動」「設定如何產生規則」「資料結構如何支撐它」「如何自己寫 module」。

## 5. NGINX 為什麼不用一條 thread 從頭等到尾？

先把這一節會用到的底層詞彙一次說清楚：

| 名詞 | 白話意思 |
|---|---|
| Kernel | 作業系統中管理 CPU、memory、files 與 network devices 的核心。NGINX 必須透過 system call 請它操作 socket。 |
| Socket | 程式與一條網路連線互動的 OS object。Listening socket 用來接新連線；accepted socket 對應某一位 client。 |
| File descriptor（fd） | Process 內引用 socket/file 的小整數，例如 fd 8。數字可在 close 後被重用，因此它不是永久身分。 |
| Blocking | 呼叫目前不能完成時，執行流程停在原地等待；若 worker 被卡住，它管理的其他 connections 也無法前進。 |
| Readiness | 某個 read/write 現在可能取得進展，不代表完整 request 已抵達或 response 已全部送完。 |
| epoll | Linux kernel 的 readiness 通知機制。NGINX 登記想監看的 fds，`epoll_wait()` 主要回傳目前 ready 的 subset；真正搬資料仍靠 `recv()`／`send()`。 |
| HTTP keep-alive | 一個 request 完成後保留 TCP connection，讓同一 client 之後可重用它發送下一個 request。 |
| WebSocket | 通常由 HTTP Upgrade 開始的長時間雙向連線；它可能維持數小時但大多數時間 idle。 |

最直覺的 server 寫法是：來一條 connection 就建立一條 thread，thread 呼叫 `read()`，沒資料時停著等；收到 request 後再連 backend，又停著等 response。這容易理解，但大量 idle 或慢速連線會帶來很多 thread、stack memory、context switch 與同步成本。

NGINX 的 worker 採 event-driven 模型：socket 暫時不能前進時，不讓整個 worker 停在那裡，而是記住「下次 ready 時該呼叫哪個 handler」，立刻去處理其他連線。Linux 上通常由 epoll 告訴它哪些 fd 現在可能可讀或可寫。

```text
同步等待：
thread A ──read────等待────parse──connect────等待────send
thread B ──read──等待──────────────parse...

事件驅動：
worker ──A讀一點──B accept──C寫一點──timer──A再讀──B parse...
          ▲ 每一步都短，不能前進就保存狀態並返回 event loop
```

這是全書最重要的心智模型：**NGINX 的主線不是一條很深的 call stack，而是一組會隨狀態改變的 callback。**

## 6. 先認識四個會一直出現的物件

| 物件 | 你可以怎麼想 | 生命週期 |
|---|---|---|
| `ngx_cycle_t` | 一整代設定與資源的世界 | 從啟動／reload 到該代 worker 全部退出 |
| `ngx_connection_t` | 一條 socket transport 的包裝 | accept/connect 到 close |
| `ngx_http_request_t` | 一次 HTTP 語意交換 | request 建立到 finalize |
| `ngx_http_upstream_t` | 這次 request 與 backend 的代理交易 | proxy 初始化到 upstream finalize |

很多看似困難的程式碼，其實是在回答兩題：現在操作哪個物件？它還能活多久？Memory pool、timer、cleanup、keep-alive、subrequest 與 reload 都建立在這個生命週期分層上。

## 7. Process 架構先看一次

```text
                    signals / reload / monitoring
                              │
                              ▼
                       ┌─────────────┐
                       │ master      │
                       │ process     │
                       └──┬───────┬──┘
                          │ fork  │ fork
                 ┌────────┘       └────────┐
                 ▼                         ▼
          ┌─────────────┐           ┌─────────────┐
          │ worker 1    │           │ worker 2    │
          │ event loop  │           │ event loop  │
          │ many conns  │           │ many conns  │
          └─────────────┘           └─────────────┘
```

Master 主要管理設定世代、signals 與 worker；真正處理 request 的是 workers。多程序隔離讓單一 worker crash 不必摧毀全部服務，也讓 graceful reload 可以讓新舊 worker 暫時並存。

## 8. Source tree 不需要全部讀

```text
src/
├── core/                 通用資料結構、pool、log、cycle、config
├── event/                connection、event loop、timer、OS event backend
│   └── modules/          epoll 等平台實作
├── http/                 HTTP request、phase、filter、upstream
│   └── modules/          proxy、rewrite、gzip、headers 等功能
├── os/unix/              Unix socket、process、sendfile 等平台層
├── stream/               TCP/UDP proxy；不是 HTTP
└── mail/                 mail proxy
```

讀某章時只需要三層：

1. 找到這個 component 在整條 request path 的位置。
2. 找到保存狀態的 struct 與推進狀態的函式。
3. 找到不能前進時如何返回、如何註冊下一個 callback／timer。

外部源碼連結只是讓你核對，不是正文的一部分。每章會先在書內把 flow、物件、狀態、return code 與實作 pattern 講完。

## 9. 每章應該怎麼讀

每章都固定回答以下問題：

1. **我現在在哪裡？** 前一個 component 已做完什麼，本章接手什麼。
2. **為什麼需要它？** 沒有它會出現哪個真實問題。
3. **Contract 是什麼？** Input、output、owner、等待點與失敗出口。
4. **Flow 怎麼走？** 從觸發到完成的逐步路徑。
5. **源碼在做什麼？** 不跳出去也能理解的壓縮版 source walkthrough。
6. **設計巧思是什麼？** Pattern、trade-off 與容易忽略的 invariant。
7. **怎麼證明真的懂？** Lab 與 follow-up answers。

如果一章暫時太難，先保住三件事：它為何存在、輸入輸出是什麼、不能前進時狀態放在哪裡。細節可以在第二輪補。
"""


def G(why, contract, flow, patterns, attention, bridge):
    return {
        "why": why.strip(),
        "contract": contract,
        "flow": flow,
        "patterns": patterns,
        "attention": attention,
        "bridge": bridge.strip(),
    }


BEGINNER_GUIDES = {
    1: G(
        """
這是全書的 GPS。初學者若先掉進 `main()`、macro 或資料結構，很快會失去「這段 code 最後替使用者做什麼」的方向。本章先把一個 reverse proxy request 從 client、NGINX 到 backend 再回來走完；以後看到任何函式，都能把它放回這張路線圖。

真實 use case 是一個公開網址背後有多台內部服務。NGINX 必須同時處理 transport、HTTP 語意、routing、backend 選擇與 response forwarding。沒有這張整體模型，connection、request、upstream 很容易被誤認為同一件事。
""",
        ("整條 reverse proxy 路徑", "client socket 上抵達的 bytes", "送往 backend 的 request 與回到 client 的 response", "cycle → connection → request → upstream", "任何 I/O 都可能暫停；任何一段都可能 timeout、close 或 retry"),
        ["OS 通知 listening socket 可讀", "accept client 並建立 connection/event", "逐段解析 HTTP，建立 request", "location 與 phase engine 選出 proxy handler", "建立 upstream、選 backend、non-blocking connect", "轉送 request 與 response", "finalize request，keep-alive 或 close"],
        [("Reactor", "event loop 收到 readiness 後呼叫短小 handler；不能前進就返回。"), ("Explicit state machine", "跨等待存活的狀態放在 request/upstream 欄位，而不是 stack。"), ("Pipeline", "phase 與 filter 把一條巨型流程拆成可插拔步驟。")],
        ["看到函式呼叫時先問它是在同步主線，還是由某個 event 之後重新進入。", "`NGX_AGAIN` 不是錯誤，而是『目前不能前進，狀態已保存』。", "分清 client connection 與 upstream peer connection；兩邊各有 read/write event。", "用 request number、connection number 與 handler 名稱重建時間線。"],
        "下一章先建立實驗室，讓這張概念圖能用 log、syscall 與故障注入被看見。",
    ),
    2: G(
        """
源碼閱讀若沒有可重現環境，很容易把猜測當事實。這一章不是工具清單，而是建立一條證據鏈：source 說可能怎麼走、debug log 顯示這次怎麼走、strace 顯示最後呼叫哪些 syscall、GDB 顯示物件當時長什麼樣。

Use case 是回答「為什麼這次回 502」「在哪個 callback 停住」「究竟有沒有重試」。若直接在 production 設定與多 worker 混合 log 中猜，因果關係會被併發與環境差異淹沒。
""",
        ("可重現的 NGINX lab", "固定 source tag、最小 config、可控制 request", "可比較的 log／trace／failure evidence", "獨立 prefix、build flags、單 worker 與 request ID", "工具本身會改變 timing；環境或版本不固定會產生假結論"),
        ["固定 tag 與 configure arguments", "用 debug symbol／debug log 編譯", "建立獨立 prefix 與最小 config", "啟動可控制的兩個 backend", "送出帶唯一 ID 的 request", "從 log → source → syscall 交叉驗證", "一次只改一個變因"],
        [("Scientific method", "提出假設、設計最小實驗、蒐集證據、修正模型。"), ("Observability by correlation", "用同一 request ID 串起 client、NGINX 與 backend。"), ("Controlled environment", "先消除多 worker、複雜 config 與不穩定 dependency。")],
        ["`--with-debug` 是 compile-time；`error_log ... debug` 是 runtime，兩者不可混為一談。", "GDB 適合停在狀態轉換點，不適合從 `main` 每行單步。", "strace 只能看 syscall，不能直接證明 phase handler 的語意。", "保存 `nginx -V`；相同 tag 因 build options 不同會走不同條件編譯。"],
        "有了證據環境後，下一章才談如何在大型 C codebase 中選擇閱讀切口。",
    ),
    3: G(
        """
NGINX 沒有單一 class hierarchy 或完整架構文件替你導航；控制流散在 struct、function pointer、module table 與初始化順序裡。本章教的是在陌生 codebase 中建立地圖，而不是背檔名。

Use case 是追「`/api` 如何到 backend」這種可驗證問題。若從目錄第一個檔案依序通讀，你會花大量時間理解與問題無關的平台 abstraction，卻仍不知道 request 的主線。
""",
        ("問題驅動的 source slice", "一個可觀察行為或 bug", "入口、狀態物件、callback 與出口形成的最小地圖", "object cards 與 callback cards", "靜態 call graph 會漏掉 function pointer、module dispatch 與 runtime branch"),
        ["定義一個 user-visible 問題", "找資料進入與離開邊界", "列出跨 callback 存活的 struct", "搜尋 handler 被賦值的位置", "只追與問題相交的 branch", "用 runtime trace 驗證", "做一個小修改檢查理解"],
        [("Vertical slice", "沿一條端到端行為切穿多層，而不是一次讀完單一資料夾。"), ("Object lifetime map", "以建立者、owner、cleanup 與存活時間理解 struct。"), ("Dynamic dispatch tracing", "function pointer 的賦值點常比呼叫點更重要。")],
        ["搜尋 `handler =`、`NGX_AGAIN`、`ngx_pcalloc(...pool)` 往往比只搜尋函式名稱有效。", "Macro 先辨認類型與 side effect；不是每個 macro 都需要展開。", "同名概念可能分 core、event、HTTP module 三層，先確認目前 abstraction level。", "Call graph 表示『可能』，debug trace 才表示『這次真的』。"],
        "下一章補上閱讀這些 struct、pointer 與 callback 所需的最小 C 語言。",
    ),
    4: G(
        """
讀 NGINX 不需要先修完一本 C 語言教科書，但必須能辨認 pointer、function pointer、macro、intrusive container 與手動 lifetime。這些語法不是裝飾，它們就是 NGINX 的物件模型與 polymorphism。

Use case 是看懂 `ev->handler(ev)` 為何能在不同階段做不同事，以及 `ngx_queue_data` 如何從嵌入節點找回外層物件。若把 function pointer 當普通函式、把 intrusive node 當獨立 allocation，就會誤讀 ownership。
""",
        ("NGINX 使用的 C object model", "struct pointer、callback、macro 與 embedded node", "可追蹤的 dispatch、container 與 lifetime", "pool／owner struct；編譯器不自動管理", "dangling pointer、錯誤 cast、macro 重複求值、生命週期不匹配"),
        ["辨認 pointer 指向哪種物件", "找 callback typedef 與賦值點", "把 macro 展開成概念操作", "看 intrusive node 嵌在哪個 owner", "確認 allocation 使用哪個 pool", "沿 return code 判斷 caller contract"],
        [("Manual vtable", "function pointers 與 module tables 提供 C 版 dynamic dispatch。"), ("Intrusive container", "節點嵌在 owner 內，減少 allocation 並支援多重索引。"), ("Region ownership", "物件由 pool 的整體 lifetime 管理，而非逐一 free。")],
        ["`data` 常是 `void *`，真正型別由 callback contract 決定。", "Bit fields 與 flags 常共同構成狀態，不要只看單一 enum。", "Container macro 可能做 pointer arithmetic；先理解 owner/node 關係。", "局部變數不能跨 event 存活；跨等待狀態必須進 heap/pool object。"],
        "具備最小語言後，Part 2 從 process 啟動開始建立 NGINX 的世界。",
    ),
    5: G(
        """
Request 能被處理以前，程序必須完成參數解析、log、設定、module 初始化、socket 建立與 process mode 選擇。本章解釋這些步驟為何有嚴格順序：後一步往往依賴前一步建立的 global context。

Use case 包括 `nginx -t` 只驗證設定、single mode 直接進 event loop、master mode fork workers。若初始化順序任意，錯誤訊息、設定 rollback 與 socket ownership 都會變得不可靠。
""",
        ("程序 bootstrap", "argv、環境、config path 與 inherited sockets", "一個可運行的 cycle，接著進 single/master mode", "process-global state 與第一個 `ngx_cycle_t`", "設定錯誤、資源建立失敗或 daemon/process 啟動失敗"),
        ["解析 command-line options", "初始化時間、pid、log 與 OS abstraction", "建立 init cycle 並解析設定", "開啟 listening sockets／files／shared memory", "依選項 daemonize", "選 single 或 master process cycle", "worker 初始化 module 後進 event loop"],
        [("Staged bootstrap", "每一步只使用已建立的 dependency，錯誤可在邊界停止。"), ("Two-phase construction", "先解析描述，再建立會產生 side effect 的 runtime 資源。"), ("Mode dispatch", "共同 bootstrap 後才分 single/master/signaller 路徑。")],
        ["`main()` 很長但多數是 orchestration；先標出 phase，不要陷入每個 helper。", "`ngx_init_cycle()` 是啟動與 reload 共用核心，不只是初始化函式。", "Inherited sockets 讓 binary upgrade/reload 不必重新 bind。", "Error path 與正常路徑同樣重要：初始化到哪裡，就只能 cleanup 到哪裡。"],
        "Bootstrap 的核心工作之一是讀設定；下一章把設定檔視為一門小語言。",
    ),
    6: G(
        """
NGINX 的設定檔不是一堆直接賦值，而是 lexer/parser、directive dispatch、context validation 與多層 merge 組成的小型語言。這讓 core 不必認識每個 module 的 directive，也讓同一 directive 能在 http/server/location 層覆寫。

Use case 是 `proxy_read_timeout 3s;` 如何找到 proxy module 的 command、解析時間、寫入正確層級的 conf，最後在 nested location 繼承。沒有這套模型，每加一個 module 都要修改中央 parser。
""",
        ("Configuration compiler", "文字 token 與目前 block context", "各 module 的 main/server/location conf 與 runtime tables", "temporary parser state + cycle pool configuration", "未知 directive、參數錯誤、context 不合法、merge 衝突"),
        ["Lexer 讀出 directive name 與 arguments", "遍歷 module command tables 找名稱", "檢查 directive 可出現的 context 與參數數量", "定位該 module 的 conf object", "呼叫 command setter 解析並寫值", "離開 block 時 merge parent/child", "init phase 把 config 編譯成 runtime 結構"],
        [("Table-driven parser", "directive metadata 與 setter table 取代中央 switch。"), ("Prototype/overlay config", "child 只覆寫明確值，其餘由 parent merge。"), ("Compile configuration", "昂貴 routing/hash/phase 結構在啟動時先建好。")],
        ["未設定值常用特殊 sentinel，而不是零；merge 必須分辨『未設』與合法零值。", "Create conf、merge conf、postconfiguration 是不同 lifecycle hook。", "Setter 回傳字串錯誤或 `NGX_CONF_OK`，不要套用普通 `NGX_OK` contract。", "Config context array 的 index 來自 module ctx index，不是 module 編譯順序直覺。"],
        "所有解析後的設定與資源會被包進一個 generation；下一章介紹 `ngx_cycle_t`。",
    ),
    7: G(
        """
NGINX 需要 reload 而不中斷服務，因此「目前設定」不能只是可原地修改的 global singleton。`ngx_cycle_t` 把一代設定、listening sockets、open files、shared memory、module conf 與 pool 包成一個完整 generation。

Use case 是先建立新設定世界，全部成功後再讓新 worker 使用；若失敗，舊 cycle 繼續服務。沒有 generation boundary，reload 到一半失敗會留下新舊資源混合的半成品。
""",
        ("Configuration generation", "舊 cycle、config files 與 inherited resources", "完整且可提交的新 cycle", "cycle pool 擁有該代 config/resource metadata", "任何解析或 resource prepare 失敗都必須放棄新 cycle"),
        ["以舊 cycle 作為可重用資源來源", "建立新 pool 與 cycle", "create 各 module conf", "解析並 merge config", "準備 files、shared zones、listening sockets", "全部成功後交給新 workers", "舊 cycle 等舊 workers drained 再釋放"],
        [("Generation object", "一個 immutable-ish object 代表完整設定版本。"), ("Transactional replace", "先 build/validate，再 publish；失敗不污染 active generation。"), ("Lifetime root", "大量子資源依附同一 cycle pool 與 cleanup。")],
        ["不要把 `ngx_cycle` global pointer 誤解成永遠只有一個 cycle；reload 時新舊代會並存。", "Socket 可被新 cycle reuse，但 metadata 與 worker ownership 屬於不同 generation。", "Shared memory zone 的 name/size compatibility 決定能否沿用資料。", "真正安全點是新 cycle 完整成功之後，而不是 config parse 完成之後。"],
        "有了 generation，下一章看 master 如何管理多個 worker 與這些資源。",
    ),
    8: G(
        """
單一 event loop 能處理很多 I/O，但仍只使用一個 CPU core，而且單一 process crash 會中斷全部服務。NGINX 以 master 管 control plane，以多個 worker 管 data plane；worker 通常彼此獨立處理 connection。

Use case 是利用多核心、隔離 crash、集中處理 signals 與 reload。這個設計刻意避免讓每個 request 在 threads 間共享大量 mutable state。
""",
        ("Master–worker runtime", "設定 generation、signals、listening sockets", "多個獨立 worker event loops", "master 擁有 process topology；worker 擁有自己的 connection state", "worker crash、signal race、spawn failure、shared resource contention"),
        ["master 完成 bootstrap", "建立 channel/socketpair", "fork worker", "worker 關閉不需要的 fd 並初始化 modules", "worker 進 event loop 處理 request", "master 接收 signal/child status", "必要時重生、reload 或優雅關閉"],
        [("Control plane / data plane split", "管理決策與 request 處理分離。"), ("Process isolation", "address space 隔離降低共享狀態與 crash blast radius。"), ("Supervisor", "master 監控 child 並依 policy 重生。")],
        ["Fork 後的記憶體看似相同，但 copy-on-write；普通變數不是跨 worker 共享。", "Listening socket 可由多 worker 共同 accept，需理解 accept mutex/reuseport policy。", "Worker 初始化失敗的 error path 會影響 master 是否重試。", "Channel message 與 Unix signals 都是 control message，注意各自可攜帶的資訊量。"],
        "多 generation 加上 master–worker，才能實現下一章的 graceful reload。",
    ),
    9: G(
        """
線上服務不能每次改設定都先關機。Graceful reload 的核心不是『修改正在跑的 worker』，而是建立新 generation 與新 workers，再請舊 workers 停止接新連線、把既有工作做完後退出。

Use case 是更新 routing、certificate、log 或 module config，同時保留長連線與正在傳輸的大 response。沒有 draining，新部署會直接 reset client connections。
""",
        ("Generation handoff", "reload signal + 舊 cycle", "新 workers 接新流量，舊 workers drained 後退出", "新舊 cycle／worker 各自擁有其 connection", "新 config 無效、舊連線不結束、資源版本不相容"),
        ["master 收到 HUP", "用舊 cycle 建立並驗證新 cycle", "spawn new-generation workers", "新 workers 開始 accept", "通知 old workers graceful quit", "舊 workers 關閉 listening sockets", "完成 existing connections 後退出", "master 回收 old cycle resources"],
        [("Blue-green inside one host", "新舊 generation 暫時並存並逐步交接。"), ("Drain protocol", "停止接新工作，但允許已接受工作完成。"), ("Transactional configuration", "新代失敗時舊代完全不受影響。")],
        ["Reload 成功不代表舊 worker 立即消失；長連線會延長並存時間。", "觀察 pid 與 generation，而不是只看 master pid。", "Module cleanup 必須尊重 old request 仍可能引用 old cycle conf。", "若 shared zone 需要保留資料，size/name 與 init callback 必須支援 generation handoff。"],
        "Part 2 建好了服務世界；Part 3 從最底層的 socket 開始看 request 如何真正進來。",
    ),
    10: G(
        """
NGINX 的 event model 最終建立在 OS socket 與 file descriptor 上。若不知道 `read()` 為何可能只讀一部分、TCP 為何沒有 message boundary、non-blocking 為何回 EAGAIN，後面的 parser 與 callback 都會像魔法。

Use case 是同一條 TCP stream 分多次抵達 request line，或 `send()` 只送出 response 的前半段。Server 必須保存 cursor，不能假設一次 syscall 完成一個語意操作。
""",
        ("Non-blocking socket transport", "kernel socket buffers 與 fd readiness", "讀到／寫出零到多個 bytes", "`ngx_connection_t` + read/write event + buffer cursors", "EAGAIN、EOF、reset、timeout、partial I/O"),
        ["socket/bind/listen 建立 listening endpoint", "accept 產生 connected fd", "設定 non-blocking", "readiness 後呼叫 recv/read", "處理 partial bytes 或 EAGAIN", "write readiness 後 send/writev", "EOF/error 時 cleanup fd 與 owner"],
        [("Byte stream abstraction", "TCP 保證有序 bytes，不保證 application message 邊界。"), ("Non-blocking contract", "syscall 只做現在能做的工作，不能做就回 EAGAIN。"), ("Cursor-based progress", "buffer positions 明確記錄已處理與尚未處理區間。")],
        ["fd 只是 process-local 整數索引，close 後很快可能被 reuse。", "Readiness 不等於完整 request，也不保證下一次 syscall 一定完成全部工作。", "EOF、RST 與 timeout 是不同 failure semantics。", "連線有 client 與 upstream 兩側；方向與 owner 不能只看 fd 數字判斷。"],
        "理解 transport 後，下一章看 listening socket ready 時 NGINX 如何 accept 並建立 connection object。",
    ),
    11: G(
        """
Accept 是 kernel 世界進入 NGINX object 世界的邊界。這一步不只取得 fd，還要從 connection pool 取物件、建立 pool、初始化 read/write events、套用 socket options，最後交給 HTTP 或 stream protocol handler。

Use case 是瞬間大量新連線、fd/connection 不足，以及多 worker 同時競爭 listening socket。若 accept error path 漏掉任一步 cleanup，就會洩漏 fd 或留下半初始化 connection。
""",
        ("Connection admission", "listening socket readable event", "完整初始化、交給 protocol layer 的 `ngx_connection_t`", "connection slot + per-connection pool + read/write events", "EMFILE/ENFILE、connection limit、accept mutex contention、client 立即關閉"),
        ["event backend 回報 listening fd readable", "`ngx_event_accept` 反覆 accept 可取得的 clients", "取得 connection slot 並綁定 fd", "建立 connection pool 與 sockaddr metadata", "初始化 read/write event fields", "設定 non-blocking/socket options", "呼叫 listening handler，例如 HTTP init"],
        [("Adapter boundary", "把 OS fd 轉成 NGINX 通用 connection/event abstraction。"), ("Object pool", "預先配置 connection slots，避免高頻 malloc/free。"), ("Admission control", "資源不足時快速停止 accept，等待可恢復條件。")],
        ["先區分 listening connection 與 accepted client connection。", "所有 accept 後失敗 branch 都要 close fd 並歸還 connection slot。", "Multi-accept、accept mutex 與 reuseport 會改變一次事件處理多少連線。", "Listening handler 是 protocol injection point；event layer 不應知道 HTTP。"],
        "Connection 建立後不會 busy-wait；下一章由 epoll 告訴 worker 哪些 fd 可以前進。",
    ),
    12: G(
        """
當 worker 同時持有數萬條大多 idle 的 connection，逐一詢問每條 fd 是否 ready 會浪費時間。Epoll 在 kernel 維護 interest set，`epoll_wait` 只回報 ready subset，讓 worker 把時間花在能前進的 connection。

Use case 是大量 keep-alive、WebSocket 或慢速 clients。Epoll 解決的是等待與掃描成本，不會自動讓 slow handler 變快，也不會把 request 分配到不同 thread。
""",
        ("Linux readiness demultiplexer", "fd interest set、timer timeout", "本輪 ready event list", "kernel epoll instance + NGINX event objects", "stale fd event、EPOLLERR/HUP、錯誤的 ET drain、永久 EPOLLOUT"),
        ["以 epoll_ctl 註冊 read/write interest", "event loop 計算最近 timer deadline", "呼叫 epoll_wait", "解碼 event data 與 stale-instance bit", "標記 read/write ready", "直接或 post 對應 handler", "handler 處理到 EAGAIN 後更新 interest"],
        [("Event demultiplexer", "把大量 fd 的 readiness 聚合成少量 ready callbacks。"), ("Generation token", "instance bit 防止 fd reuse 後舊通知打到新 connection。"), ("Interest management", "只有真正需要等待 writable 時才訂閱 write event。")],
        ["Epoll 回的是 readiness，不是 I/O completion。", "Edge-triggered 模式下通常要讀／寫到 EAGAIN 才不會漏掉後續通知。", "EPOLLOUT 幾乎常成立，無 pending data 時不要長期關注。", "檢查 ERR/HUP 如何被轉成 read/write ready，讓既有 handler 統一處理。"],
        "Epoll 只知道 fd；下一章看 `ngx_event_t` 如何把 readiness 連回目前應執行的業務 callback。",
    ),
    13: G(
        """
同一個 client fd 在不同時間要做不同工作：先等待 request line、再讀 headers、處理 request 後等待 keep-alive。Event loop 不應寫滿 HTTP-specific switch，因此 `ngx_event_t` 保存 handler，狀態轉換時直接替換下一個 callback。

Use case 是讓 transport 層只負責『某 fd ready』，由 request/upstream state 決定下一步。這是 NGINX C code 中最接近 object method 與 continuation 的核心抽象。
""",
        ("Event callback object", "read/write readiness 或 timer expiration", "推進 owner state 一小步並安排下一次喚醒", "`ngx_event_t.data` 指向 connection；handler 指向 continuation", "handler 用錯、owner 已釋放、timer/event 同時觸發、遞迴重入"),
        ["建立 connection 時配置 read/write events", "protocol layer 安裝初始 handler", "event backend 標記 ready", "event loop 呼叫 `ev->handler(ev)`", "handler 由 `ev->data` 找回 connection/request", "處理 bytes 並更新 state", "若未完成，替換／保留 handler 與 timer 後返回"],
        [("Continuation", "handler 就是『未來 ready 時從哪裡繼續』。"), ("Inversion of control", "event loop 決定何時呼叫；protocol 決定呼叫後做什麼。"), ("State pattern", "透過 handler replacement 避免中央巨大 switch。")],
        ["搜尋 handler assignment 才能重建狀態轉換圖。", "`ev->data` 的動態型別由 contract 決定，常先是 connection，再從 `c->data` 找 request。", "Read event 與 write event 可同時存在 timer，注意誰先 finalize owner。", "Posted event 可能延後 callback，避免深遞迴或改善公平性。"],
        "有了 callback abstraction，下一章把 timer、accept 與 posted events 放回完整 event loop。",
    ),
    14: G(
        """
Event loop 是 worker 的 scheduler。它每輪決定可睡多久、向 OS 取得 ready events、更新時間、處理 accept/normal/posted events，再執行過期 timers。順序會直接影響 latency、公平性與 starvation。

Use case 是同時處理新連線、已有連線、timeout 與由 handler 延後排程的工作。若某類事件無限占用一輪，其他 connection 即使 ready 也會延遲。
""",
        ("Worker scheduler loop", "ready fd、posted queue、timer deadlines、signals", "一批短 callback 的公平執行", "event queues、timer tree、process flags", "slow callback、事件洪水、timer starvation、遞迴 callback"),
        ["找最近 timer 計算 wait timeout", "呼叫 OS process_events", "更新 cached time", "優先處理 accept events／posted accept", "處理 normal ready callbacks", "處理 expired timers", "處理 posted events", "檢查 terminate/reconfigure 等 process flags"],
        [("Run-to-completion task", "每個 handler 在單 worker 上跑完才輪到下一個。"), ("Cooperative scheduling", "公平性依賴每個 handler 主動保持短小。"), ("Deferred work queue", "posted events 把立即遞迴改成稍後排程。")],
        ["Event loop 沒有 preemption；任何 blocking call 都會凍結該 worker。", "Cached time 降低頻繁 syscall，但要注意何時更新。", "Accept events 與 normal events 的處理順序可能受 flags/config 影響。", "Loop 本身很短；真正複雜度分散在 handlers 與狀態物件。"],
        "Event loop 必須知道下一個 timeout；下一章看 timer 為何由紅黑樹管理。",
    ),
    15: G(
        """
每條 connection 可能有 read timeout、write timeout、keep-alive timeout；worker 需要快速知道『最近哪個 deadline』，也要能在事件完成時取消任意 timer。這組操作不是單純 FIFO，所以 NGINX 使用按到期時間排序的紅黑樹。

Use case 是數萬條 timer 動態新增、刪除與找最小值。Heap 找最小也快，但任意刪除需要額外 index；紅黑樹配合 intrusive node 讓 event 自己攜帶可刪除節點。
""",
        ("Deadline index", "event + absolute expiration time", "最近 timeout 與所有已過期 events", "timer rbtree；node 嵌在 `ngx_event_t`", "時間 wrap、重複更新、expired callback 釋放 owner"),
        ["handler 為 event 計算 absolute deadline", "將 event timer node 插入 rbtree", "event loop 讀最小 key 決定 epoll timeout", "I/O 先完成時刪除 timer", "deadline 到時依序移除 expired nodes", "標記 timedout 並呼叫 event handler", "handler 決定 retry、finalize 或 close"],
        [("Ordered set by deadline", "operation set 是 min、insert、arbitrary delete。"), ("Intrusive node", "event 直接嵌 timer node，無額外 wrapper allocation。"), ("Lazy scheduler wake-up", "最近 deadline 直接成為 epoll_wait timeout。")],
        ["不要從『紅黑樹很高級』倒推需求；先列出 operation set。", "Timer handler 與 I/O handler 常是同一函式，透過 `timedout` flag 分支。", "刪除 timer 後要同步清 `timer_set` invariant。", "到期時間比較需考慮整數 wraparound，不能只用普通大於小於直覺。"],
        "Timer 解決 deadline，但資料速度不匹配仍會塞住；下一章處理 backpressure 與公平性。",
    ),
    16: G(
        """
Backend 可能很快、client 很慢；request body 也可能由 client 慢慢上傳。若 producer 不受限制地產生資料，memory、temporary files 或 socket queue 會持續膨脹。Backpressure 是讓下游容量反向限制上游速度。

Use case 是大型 download 遇到慢速行動網路、backend streaming 遇到 client 暫停讀取。沒有 high-water mark 與 event interest 切換，一個 connection 就可能耗盡 worker 記憶體或造成其他請求 tail latency。
""",
        ("Flow-control loop", "producer bytes、consumer capacity、buffer occupancy", "有上限且可恢復的資料流", "buffer chains、busy/free lists、read/write event interest", "unbounded buffering、busy loop、starvation、timeout policy 錯誤"),
        ["從 producer 讀入有限 buffers", "把 buffers 交給 downstream output chain", "若 write partial/EAGAIN，保留 unsent cursor", "buffer 高水位時停止 producer read interest", "等待 consumer socket writable", "送出後回收 free buffers", "低於水位再恢復 producer", "deadline 到時決定中止"],
        [("Backpressure", "容量訊號沿 pipeline 反向傳回 producer。"), ("Watermarks", "高／低水位避免頻繁開關與無界成長。"), ("Bounded work per turn", "每輪限制 bytes/events，維持多 connection 公平。")],
        ["`NGX_AGAIN` 後必須保留未送資料，不能重新產生或丟失 cursor。", "停止 read interest 和關閉 connection 完全不同；前者只是暫停 producer。", "Buffering 將 backend lifetime 與 client speed 解耦，但成本轉移到 memory/disk。", "平均 throughput 正常仍可能有 tail latency；檢查單次 handler 工作量。"],
        "Connection 與事件基礎完成；Part 4 開始把收到的 bytes 提升成 HTTP request。",
    ),
    17: G(
        """
Connection 只知道一條 byte stream；HTTP layer 需要一個物件保存這次語意交換的 method、URI、headers、body、routing 結果、module context 與 response 狀態。`ngx_http_request_t` 就是所有 HTTP modules 合作時共享的工作區。

Use case 是同一條 keep-alive connection 依序承載多個 requests，或一個 main request 建立 subrequests。若把 request state 塞進 connection，上一個請求的資料會污染下一個，生命週期與 cleanup 也無法分離。
""",
        ("HTTP request context", "connection 上已讀取或即將讀取的 HTTP bytes", "完成的 response，或轉交 content/upstream pipeline", "request pool、reference count、module ctx、headers/buffers", "client abort、internal redirect、subrequest 未完成、重複 finalize"),
        ["HTTP connection handler 決定開始新 request", "從 connection pool/large header buffer 取得解析空間", "配置 `ngx_http_request_t` 與 request pool", "解析 request line/headers 並填欄位", "選 virtual server/location", "phase/content/upstream modules 寫入各自 ctx", "filter 送 response", "reference count 歸零後 cleanup，connection keep-alive 或 close"],
        [("Context object", "一個 request object 聚合跨 module、跨 callback 的狀態。"), ("Per-request dependency container", "module ctx array 讓擴充功能保存私有資料而不改 core struct。"), ("Reference-counted async completion", "main/subrequest 與延後工作完成後才真正釋放。")],
        ["`r->connection` 是 client transport；`r->upstream->peer.connection` 是 backend transport。", "`main`、`parent` 與 `count` 決定 subrequest/finalize 關係。", "Request pool 釋放後所有指向其中資料的 pointer 都失效。", "Internal redirect 可能重跑部分 routing/phase，但仍在同一高階 request 生命線內。"],
        "Request object 建立後，下一章先看最前面的 request line 如何從碎片化 bytes 變成 method 與 URI。",
    ),
    18: G(
        """
TCP 不保證 `GET /path HTTP/1.1` 一次到齊；它可能拆成任意片段。Parser 必須在資料不完整時保存狀態，下一次 read 從正確位置繼續，同時拒絕非法字元與過長輸入。

Use case 包括慢速 client、封包分段與惡意超長 URI。若 parser 依賴 null-terminated string 或一次 read 完整行，會越界、阻塞或錯誤接受 ambiguous request。
""",
        ("Incremental request-line parser", "buffer 中目前可用的 bytes + 上次 parser state", "method、URI、HTTP version 或 AGAIN/error", "request parser state 與 buffer positions", "invalid syntax、line too long、buffer exhaustion、request smuggling ambiguity"),
        ["從 `r->state` 恢復 parser state", "逐 byte 判斷 method/token", "遇到 space 轉入 URI state", "處理 schema/host/path/query 等分支", "遇到 CR/LF 檢查 HTTP version 與完整性", "資料耗盡但合法時回 AGAIN", "完整時保存 offsets/pointers 並進 header parser", "錯誤時回明確 parse code"],
        [("Finite-state machine", "每個 state 只接受有限字元與轉移，適合增量解析。"), ("Streaming parser", "不複製完整字串也能跨 buffer 繼續。"), ("Fail closed", "未知或 ambiguous syntax 直接拒絕，避免不同 hop 解讀不一致。")],
        ["先畫 states 與 transition，不要直接逐行讀巨型 switch。", "注意 parser 回傳值：OK、AGAIN 與各類 invalid code 的 caller 行為不同。", "Pointer 通常指向 request buffer；buffer 生命週期與重新配置會影響有效性。", "安全重點是 bounds check、CR/LF、空白規則與不同 HTTP hop 的一致解讀。"],
        "有了 request line，下一章用類似但更敏感的 parser 讀 headers 與 message framing。",
    ),
    19: G(
        """
Headers 不只是 metadata；`Content-Length`、`Transfer-Encoding`、`Host` 與 connection headers 會決定 request 邊界、routing 與後續讀取方式。Parser 必須既高效又在安全邊界上非常保守。

Use case 是把 raw header lines 轉成 generic list，同時對常見 headers 建立快速欄位。若 proxy chain 對重複或衝突 framing headers 解讀不同，就可能產生 request smuggling。
""",
        ("HTTP header normalization", "一行行 header bytes", "header list、known-header fields 與 body framing decision", "request pool、header list、parser offsets", "oversized/invalid header、duplicate Host、CL/TE conflict、underscore policy"),
        ["增量找到 header name/token", "正規化或 hash header name", "解析 colon、optional whitespace 與 value", "配置 table element 保存 key/value", "known-header handler 填入 `headers_in` 快速欄位", "檢查 duplicates 與 semantic constraints", "空行表示 headers 結束", "決定是否及如何讀 request body"],
        [("Parse then validate semantics", "語法 parser 與 known-header 規則分層。"), ("Dual representation", "generic list 保留全部 headers，typed fields 加速核心路徑。"), ("Protocol normalization boundary", "入口統一模糊語法，後層只看明確結果。")],
        ["不要只讀 generic parser；真正安全政策常在各 known-header handler。", "重複 header 是否可合併取決於 header 語意，不能一律 concatenate。", "`Host` 會影響 virtual server；framing headers 會影響 body 邊界。", "檢查 NGINX 與 upstream 對 hop-by-hop headers 的刪除／重建，避免原樣轉發。"],
        "Request 語法完整後，下一章決定它屬於哪個 server 與 location。",
    ),
    20: G(
        """
同一個 IP/port 可以服務多個 hostname，同一 hostname 又依 URI 使用不同設定。Virtual server 與 location matching 把外部 request 映射到一份合併後的 configuration context。

Use case 是 `/static/` 直接讀檔、`/api/` proxy、`~ \\.php$` 走 FastCGI。若每次 request 都線性解讀原始 config，效能與規則一致性都很差，因此 NGINX 在啟動時先編譯 routing structures。
""",
        ("Configuration routing", "local address、Host/SNI、normalized URI", "選定 server conf 與 location conf", "啟動期建好的 address/name/location tables", "ambiguous rule、URI normalization 差異、regex order、internal redirect loop"),
        ["accept 後依 listen address 取得 server set", "解析 Host 後選 virtual server", "對 URI 做必要 normalization", "先做 exact/prefix location 查找", "依規則決定是否測 regex locations", "取得該 location 的 module conf array", "設定 content handler/phase config", "internal redirect 時按新 URI 重新查找"],
        [("Compile routing rules", "啟動時把宣告式 config 轉成高效查找結構。"), ("Most-specific match with exceptions", "prefix/exact/regex 有明確 precedence。"), ("Context switch", "選 location 等於切換整組 module configuration。")],
        ["Location precedence 不能靠『看起來最像』；要按 exact、prefix、`^~`、regex 規則推演。", "URI normalization 與 filesystem path mapping 是不同階段。", "Regex locations 通常保留順序語意；prefix tree 則偏向最長匹配。", "Internal redirect 可能再次 location lookup，需防止無限循環。"],
        "選定 location 後還沒真正執行功能；下一章由 phase engine 排定 rewrite、access 與 content handlers。",
    ),
    21: G(
        """
許多 modules 都想在 request 的不同時機介入：改 URI、做 access control、限制速率、產生 content。若 core 為每個 module 寫固定呼叫，擴充會造成巨大耦合。Phase engine 把 handlers 在 configuration time 編譯成 runtime pipeline。

Use case 是 access module 能在 proxy module 前拒絕 request，rewrite 能改 URI 後重新找 location。Return code 不是普通成功失敗，而是控制 pipeline 是否繼續、暫停、跳轉或 finalize。
""",
        ("HTTP middleware pipeline", "已解析且已有 location conf 的 request", "content handler、暫停中的 async request 或最終 status", "phase handler array + `r->phase_handler` cursor", "錯誤 return protocol、重複執行、async handler 未保存狀態、rewrite loop"),
        ["postconfiguration 收集各 module phase handlers", "啟動時建立扁平 phase engine array", "request 進 `ngx_http_core_run_phases`", "phase checker 呼叫目前 handler", "依 return code 繼續、跳下一 phase、暫停或 finalize", "rewrite 可能重新 location lookup", "content phase 找到 response producer", "未完成 async 工作由 callback 再續跑"],
        [("Chain of responsibility", "多個 handler 依序檢查／處理 request。"), ("Compiled interpreter", "config-time 把 phase graph 編成小型 instruction array。"), ("Return-code protocol", "NGX_DECLINED/AGAIN/DONE/HTTP status 共同控制 pipeline。")],
        ["同一 return code 在不同 checker 下可能有不同處理；要一起讀 handler 與 checker。", "`NGX_DECLINED` 常表示『我不處理，交給下一個』，不是 system error。", "Async handler 返回後若未 finalize，必須安排 future callback。", "Phase order 是 module interaction contract；錯掛 phase 會產生安全繞過。"],
        "Content handler 有時需要 client body；下一章看 body 如何在 memory、chain 與 temporary file 間流動。",
    ),
    22: G(
        """
Headers 到齊不代表 request 到齊。POST/PUT body 可能很大、分段到達，甚至超過 memory budget。NGINX 必須依 Content-Length/chunked framing 增量讀取，並讓 module 選擇 buffer、temporary file 或 streaming consumption。

Use case 是上傳 JSON、小表單、數 GB 檔案或 proxy request body。若一律全部讀進 memory，少數大 request 就能耗盡 worker；若完全不 buffer，retry 時又可能無法重播 body。
""",
        ("Request-body ingestion", "client read events + framing metadata", "memory chains、temporary file 或 streaming callbacks", "`ngx_http_request_body_t`、buffers、temp file、rest counter", "body too large、timeout、client abort、chunk parse error、unreplayable retry"),
        ["依 method/module 決定是否需要 body", "根據 framing 初始化剩餘長度/chunk parser", "先消費 header buffer 中已讀到的 body bytes", "read event 到來時填 buffers", "完整 buffers 交給 filter/consumer", "超過 memory threshold 時寫 temp file", "body 完成後呼叫 post handler", "finalize 時 cleanup file/buffers"],
        [("Streaming with bounded buffers", "資料可以逐塊交付，不要求整體一次存在。"), ("Spill to disk", "memory 超過上限時轉移到 temporary file。"), ("Replayability policy", "buffer body 可支援 retry；pure streaming 降低 latency 但難重播。")],
        ["Body read API 常是 async：函式返回不代表 body 已完成，真正 continuation 是 post handler。", "Header buffer 可能已含部分 body，不能忽略 preread bytes。", "Chunked 是 framing protocol，不等於 upstream 一定也使用 chunked。", "檢查 temp file cleanup 與 client abort branch，避免磁碟資源殘留。"],
        "不論 response 由 static、proxy 或其他 module 產生，都要經共同 output pipeline；下一章看 filter chain。",
    ),
    23: G(
        """
Response 可能需要 gzip、range、chunked encoding、header 修改、logging 或最終 socket write。若 content module 自己處理所有組合，功能會呈乘法爆炸。Filter chain 讓每個 filter 專注一種 transformation，再呼叫下一層。

Use case 是 proxy response 加 header 後 gzip，再做 chunked framing 與 write。Filter 必須處理任意 buffer 邊界、flush/last flags 與 downstream backpressure。
""",
        ("Response transformation pipeline", "response headers 或 buffer chain", "修改後的 headers/chains，最終送到 client", "filter module ctx + chain links + buffer flags", "順序錯誤、重入、跨 buffer state 丟失、未傳遞 last/flush、partial write"),
        ["Postconfiguration 把 module filter 掛到 top chain", "content/upstream 呼叫 top header filter", "各 filter 檢查／修改 headers 並呼叫 next", "body chunks 進 top body filter", "filter 轉換或旁路 buffers", "output/write filter 嘗試 send/writev", "送不完保存 busy chain 並回 AGAIN", "writable event 再續送"],
        [("Decorator / filter chain", "每層包住下一層，獨立組合 response 行為。"), ("Streaming transducer", "輸入 chunks 轉為輸出 chunks，state 可跨呼叫。"), ("Backpressure-preserving interface", "下游 AGAIN 必須原樣向上游反映。")],
        ["Filter order 由註冊順序與 top/next 保存方式決定，直覺上的 source file order不可靠。", "Buffer 的 `last_buf`、`last_in_chain`、`flush`、`sync` 都有語意。", "不可假設每次收到完整 token 或完整 response。", "修改 Content-Length 的 filter 必須同步處理 framing，否則 client 會誤判邊界。"],
        "Pipeline 最後仍需正確結束 request 並決定是否重用 connection；下一章收束生命週期。",
    ),
    24: G(
        """
Async 系統最難的不只是開始工作，而是只結束一次、在所有 child work 完成後結束，並把 transport 留在可重用或可安全關閉的狀態。Finalize 是 request lifecycle 的集中收口。

Use case 是正常 response、error page、subrequest、client abort 與 keep-alive。若多個 callback 都直接 free request，會 double free；若漏掉一次 reference decrement，request 永遠不釋放。
""",
        ("Request completion protocol", "handler result、I/O completion、error 或 child completion", "cleanup 完成，connection 進 keep-alive/lingering close/close", "request count、main/subrequest links、cleanup list", "double finalize、reference leak、response 已送後又改 status、殘留 timer"),
        ["某 handler 呼叫/觸發 finalize", "根據 rc 判斷是否仍有 async work", "處理 special response 或 error path", "更新 main request count", "等待 posted/subrequests 完成", "執行 request cleanup", "若可 keep-alive，重設 connection handler 等下一 request", "否則 lingering close 或直接 close"],
        [("Single completion gate", "所有成功失敗路徑集中通過 finalize protocol。"), ("Reference-counted join", "多個 async/subrequest 分支在 count 歸零時會合。"), ("Object recycling", "request 結束後 connection 可切回 keep-alive state。")],
        ["`ngx_http_finalize_request` 不等於立即 free；rc 與 count 決定後續。", "Headers 已送出後，錯誤處理不能再安全改 status/header。", "Keep-alive 是 connection lifecycle 延續，不是 request object 重用。", "Cleanup handler 可能關 file、釋放外部 library resource；pool free 本身不會替你做這些 side effects。"],
        "Client-side HTTP 生命週期完成；Part 5 放大 `proxy_pass` 之後與 backend 溝通的另一半。",
    ),
    25: G(
        """
`proxy_pass` 看似一行設定，背後要把 client request 轉換成 backend 可接受的 request，決定 URI rewrite、headers、body forwarding、buffering、timeouts 與 upstream group。Proxy module 是 HTTP configuration、content handler 與通用 upstream framework 的接合層。

Use case 是把 `/api/` 轉發到 application servers，同時重寫 Host、加入 forwarding headers。Core upstream 不知道 HTTP proxy request 長什麼樣，proxy module 透過 callbacks 提供 protocol-specific 行為。
""",
        ("HTTP proxy adapter", "已完成 routing 的 client request + proxy location conf", "初始化完成的 `ngx_http_upstream_t` 與 backend request buffers", "proxy module ctx/conf + request pool", "URI 拼接錯誤、hop-by-hop header 洩漏、body 不可重播、callback contract 錯誤"),
        ["Config parser 編譯 proxy_pass URL/variables", "location content handler 進 proxy module", "建立 upstream object", "填入 create_request/reinit/process_header 等 callbacks", "計算 backend URI 與 headers", "建立 request buffer chain", "呼叫通用 upstream init", "後續由 upstream state machine 接管"],
        [("Adapter", "proxy module 把 HTTP proxy 協定接到通用 upstream engine。"), ("Template method via callbacks", "core 定義流程，module 提供建立／解析協定細節。"), ("Configuration compilation", "複雜 variable/URI script 在啟動時預先編譯。")],
        ["Trailing slash 會影響 proxy_pass URI replacement，必須用具體例子推演。", "不要原樣轉發 hop-by-hop headers；proxy module 會重建部分 headers。", "`create_request` 產生的是 backend-side bytes，不是修改 client buffer。", "同一 proxy config 可能因 variables 在 runtime 決定不同 upstream/URI。"],
        "Proxy module 準備好 protocol-specific callbacks 後，下一章由通用 upstream state machine 推進整次 backend 交易。",
    ),
    26: G(
        """
Backend 交易包含選 peer、connect、send request、read header、read body、retry 與 finalize；每一步都可能因 I/O 暫停。`ngx_http_upstream_t` 把這些狀態與 protocol callbacks 集中，避免每個 proxy-like module 重寫整套 async transport。

Use case 是 HTTP proxy、FastCGI、memcached 等不同協定共享 connect、timeout、buffering、retry 與觀測框架，只替換 request encoding 與 response parsing。
""",
        ("Generic upstream transaction", "client request + module callbacks + upstream conf", "backend response pipeline 或可分類的 failure", "upstream object、peer connection、state timings、event pipe", "connect/send/read timeout、client abort、peer failure、retry state 未重設"),
        ["create upstream object", "module create_request 產生 backend bytes", "初始化 peer selection 與 attempt state", "non-blocking connect", "writable 後送 request/body", "readable 後 process_header", "選 buffered event pipe 或 non-buffered streaming", "成功 finalize/keepalive，失敗則判斷 next peer"],
        [("State machine with pluggable protocol", "transport 狀態固定，協定細節由 callback 注入。"), ("Second-level dispatch", "共用 socket handler 再分派 `u->read/write_event_handler`。"), ("Attempt history", "每次 peer 嘗試各自記錄 status 與 timing。")],
        ["先追 `u->read_event_handler`/`write_event_handler` 何時改變，再讀各大函式。", "一次 client request 可有多個 upstream states，代表 retry 歷史。", "Reinit callback 必須重設 parser與request buffers，不能只換 socket。", "Client abort 後是否繼續取決於 cache/store 等 policy，不是永遠立即停止。"],
        "State machine 的第一個 I/O 難點是 connect；下一章拆開 EINPROGRESS 到連線確認。",
    ),
    27: G(
        """
Blocking `connect()` 可能等待 TCP handshake；event-driven worker 不能停住。Non-blocking connect 通常回 EINPROGRESS，表示結果尚未知，NGINX 必須等待 socket writable，再用 socket error 狀態確認成功或失敗。

Use case 是 backend 延遲、拒絕或網路黑洞。Writable 不保證成功；它只表示 connect 已有結果可檢查。
""",
        ("Non-blocking peer connection", "選定 peer address + connect timeout", "connected upstream socket 或分類 failure", "`ngx_peer_connection_t`、write event、timer", "EINPROGRESS、ECONNREFUSED、timeout、stale peer state、fd leak"),
        ["從 load balancer 取得 peer", "socket 並設 non-blocking", "呼叫 connect", "立即成功則進 send request", "EINPROGRESS 則安裝 connect handler/timer", "write event 到來後讀 `SO_ERROR`", "成功切換 send handler", "失敗 free peer 並交 retry policy"],
        [("Split-phase operation", "開始 connect 與完成 connect 是兩個 callback 階段。"), ("Capability callback", "peer.get/free 將選擇與回饋從 transport 分離。"), ("Deadline guard", "timer 與 readiness 競賽，先發生者決定結果。")],
        ["不要把 EPOLLOUT 當 connect success；必須檢查 socket error。", "Connect timer 只覆蓋建立連線階段，之後會切換 send/read timeout。", "每個失敗 branch 都要正確 close fd 並呼叫 peer free 回饋。", "成功後 handler 立即換成 send-request continuation，這是關鍵狀態轉移。"],
        "有了可用 backend connection，下一章看多台 peers 中為何採 smooth weighted round robin。",
    ),
    28: G(
        """
普通 weighted round robin 若直接連續送出權重份額，會產生流量 burst：權重 5:1 可能先連續五次打 A，再一次打 B。Smooth weighted round robin 讓高權重 peer 更頻繁但盡量均勻地穿插。

Use case 是不同容量 backend 以 weight 分流，同時在失敗後降低有效權重、成功後逐步恢復。它不只是一道演算法題，而是 scheduler 加 feedback control。
""",
        ("Weighted peer scheduler", "可用 peers、weight、failure state、tried set", "本次選中的 peer + 後續成功失敗回饋入口", "per-request tried bitmap + per-peer current/effective weight", "全部 peers 不可用、burst、失敗 peer 持續被選、integer invariant 破壞"),
        ["遍歷未 tried 且健康的 peers", "每個 peer 的 current += effective", "累加 total effective weight", "選 current 最大者", "winner.current -= total", "標記 request tried", "連線結果透過 free callback 回饋", "失敗降低 effective，成功逐步恢復"],
        [("Smooth weighted round robin", "保持長期比例，同時降低短期 burst。"), ("Feedback-adjusted scheduling", "effective weight 依失敗與恢復動態改變。"), ("Per-request exclusion set", "retry 不應立刻重選同一 peer。")],
        ["區分 configured weight、effective weight 與 current weight。", "先手算 5:1、3:2 的前十次選擇，才能看懂 update invariant。", "Peer shared state 是否跨 workers 取決於 upstream zone 配置。", "失敗回饋時機與 classification 會影響 scheduler 是否過度懲罰。"],
        "Round robin 不是所有 workload 的最佳策略；下一章比較 hash、least connections 與其他選擇。",
    ),
    29: G(
        """
Load balancing 的目標可能是平均 request 數、平均 in-flight 工作、維持 session affinity 或提高 cache locality；不存在脫離 workload 的唯一最佳演算法。本章建立『先列 constraints，再選 policy』的思考方式。

Use case 包括長短 request 差異大時用 least connections、需要 key affinity 時用 hash、超大 fleet 用抽樣策略。選錯 metric 會看似平均，實際 latency 卻惡化。
""",
        ("Pluggable peer-selection policy", "peer states + request key/connection counts/weights", "一個候選 peer 與可解釋的選擇理由", "policy-specific peer data + common get/free interface", "hot key、remap storm、stale load metric、所有候選失敗"),
        ["定義 workload 與要最佳化的指標", "module 在 config time 建 policy data", "request time 取得 key或負載訊號", "排除 tried/down/unavailable peers", "依 policy 排序、hash 或抽樣", "回傳 peer 給通用 connect path", "free callback 更新 feedback", "失敗時 fallback 到下一 policy/peer"],
        [("Strategy pattern", "相同 get/free contract 下替換選擇演算法。"), ("Consistent hashing", "節點變動時降低 key remapping，但仍需處理 skew。"), ("Power of two choices", "只抽少量 candidates 即可大幅降低最大負載。")],
        ["比較演算法時同時問 state 是 local 還是 shared、更新是否精確、成本多高。", "Least connections 只看連線數，未必代表 CPU/queue work。", "Hash 提供 affinity，不等於高可用；peer down 時仍需 fallback。", "演算法名稱不是答案，要用 request duration、key distribution、fleet churn 驗證。"],
        "選到 peer 之後仍可能在不同階段失敗；下一章決定何時 timeout、retry 或停止。",
    ),
    30: G(
        """
分散式系統中的 failure 不是單一布林值：connect refused、connect timeout、header timeout、invalid response、mid-body close 的資訊與安全性不同。Retry 能提高可用性，也可能重複副作用、放大流量與突破整體 deadline。

Use case 是 GET 在 backend connect 前失敗可嘗試另一台；POST 已送出付款 body 後結果未知，盲目 retry 可能扣款兩次。
""",
        ("Failure and retry policy", "attempt stage、error class、method/body replayability、remaining peers", "retry next peer 或 finalize client response", "upstream state history、tried set、timeouts、request-sent flags", "duplicate side effect、retry storm、deadline amplification、response 已開始後重試"),
        ["I/O handler 分類 failure 與當前 stage", "記錄本次 status/timing", "檢查 `proxy_next_upstream` policy", "檢查 request 是否可安全重播", "檢查是否還有未 tried peers/tries/time budget", "若可重試，reinit protocol state", "free old peer 並 connect next", "否則選最合理 client status/finalize"],
        [("Retry budget", "限制 attempts 與總時間，避免故障放大。"), ("Idempotency-aware recovery", "是否重試取決於副作用與結果不確定性。"), ("Failure matrix", "按 stage × error × bytes-sent 系統化決策。")],
        ["分清 connect timeout、send timeout、read/header timeout，它們代表不同未知程度。", "HTTP method 只是線索；真正 idempotency 由 application semantics 決定。", "Body 若未 buffer 完成，即使語意安全也可能無法 replay。", "一旦部分 response 已送 client，通常不能透明切 peer 重來。"],
        "頻繁重建 backend TCP connection 很昂貴；下一章在安全邊界內重用 upstream connections。",
    ),
    31: G(
        """
每次 request 都做 TCP（甚至 TLS）handshake 會增加 latency、CPU 與 ephemeral port 壓力。Upstream keepalive cache 把已完成且仍健康的 idle backend connections 暫存，下一個 request 可直接使用。

Use case 是高 QPS、短 request 的 application servers。這不是無上限 connection pool：cache 只保存有限 idle connections，還要驗證 protocol 狀態乾淨、peer identity 相容且未被 backend 關閉。
""",
        ("Idle upstream connection cache", "完成 request 的 peer connection 或新 request 的 peer key", "可重用 connection，或 fallback 建新 connection", "per-worker keepalive cache/available queue、LRU metadata", "stale idle socket、跨 peer 誤用、cache 無界、response 未讀完就回收"),
        ["新 request 呼叫 wrapped get peer", "按 address/peer identity 搜 idle cache", "命中則移出 cache 並綁回 request", "未命中交原 load balancer + connect", "response 完成時檢查 keepalive eligibility", "把 connection 從 request state 拆下", "放入 cache 並安裝 idle read handler", "容量滿時淘汰最舊 idle connection"],
        [("Object pooling", "重用昂貴 transport resource。"), ("Decorator around strategy", "keepalive 包住原 get/free peer callbacks。"), ("LRU bounded cache", "只保留有限 idle connections並淘汰最久未用者。")],
        ["Keepalive cache 通常 per worker；不要把設定數字誤解成全機精確上限。", "回收前必須確認 response framing 完整、無 unread bytes、未要求 close。", "Idle read event 用來偵測 backend 主動關閉。", "Cache key 必須對應實際 peer；不能只因 hostname 相同就任意重用。"],
        "Backend 可以很快，但 client 可能很慢；下一章看 buffering 如何把兩者速度解耦。",
    ),
    32: G(
        """
若 NGINX 一邊從 backend 讀、一邊直接寫慢速 client，backend connection 會被占用很久；若無限制讀入，又會耗盡 memory。Event pipe 在有限 memory buffers、temporary file、upstream read 與 downstream write 間協調。

Use case 是 backend 快速產生 100 MB response，而手機 client 每秒只讀 50 KB。Buffering 讓 backend 較早釋放；streaming 則降低 first-byte latency 與磁碟使用，兩者是 policy trade-off。
""",
        ("Bidirectional response pump", "upstream readable + downstream writable + buffer limits", "有界地把 response 搬到 client", "event pipe、in/out/busy/free chains、temp file offsets", "memory growth、disk saturation、client timeout、upstream stall、buffer flag 遺失"),
        ["從 upstream 讀到 free buffers", "解析/套用 input filter", "buffers 加入待輸出 chain", "嘗試送到 client output filter", "送不完移入 busy chain", "超過 memory threshold 時 spill temp file", "下游釋放 buffers 後恢復 upstream read", "兩端完成或任一端失敗時 finalize"],
        [("Event-driven pump", "兩側 readiness 共同驅動資料搬運。"), ("Elastic buffering", "memory 快路徑不足時使用 disk 擴充，但仍有上限。"), ("Producer–consumer decoupling", "buffer 讓 backend 與 client 的 active lifetime 部分分離。")],
        ["先分清 buffered 與 non-buffered path，它們使用不同 handlers/structures。", "Busy/free/out chains 的 ownership 轉移是理解 event pipe 的核心。", "Temporary file 不是失敗；它是明確的容量策略。", "關閉 upstream read interest 是 backpressure，不代表 upstream connection 出錯。"],
        "Buffering 解決單次 response；下一章看 proxy cache 如何讓結果跨 requests 重用。",
    ),
    33: G(
        """
Proxy cache 讓多個 client requests 共用先前的 backend response，降低 backend load 與 latency。但 cache 不只是 key-value map：body 在 disk，metadata/locks 在 shared memory，還要處理 freshness、revalidation、stale、loader/manager 與同 key 併發。

Use case 是大量讀多寫少內容，或 backend 暫時故障時提供 stale response。沒有 cache lock，熱門 key 過期的一瞬間可能讓數百 requests 同時打 backend，形成 thundering herd。
""",
        ("Shared HTTP response cache", "cache key + request cache policy + backend response", "fresh/stale/revalidated response 或 cache miss", "shared metadata zone、disk files、per-request cache ctx", "stampede、stale metadata、disk eviction、partial file、錯誤 cache personalized content"),
        ["計算 normalized cache key", "在 shared metadata 查 entry", "fresh hit 直接開檔送 response", "stale/miss 時決定 lock/wait/bypass", "單一 owner 向 upstream 取資料", "邊收 response 邊寫 temporary cache file", "成功後 atomic rename/publish metadata", "manager/loader 維護容量與重啟恢復"],
        [("Cache-aside in proxy pipeline", "先查 cache，miss 才進 upstream。"), ("Single flight / cache lock", "同 key 同時只讓一個 request 回源。"), ("Metadata/data split", "小而熱的 index 在 shared memory，大 body 在 filesystem。")],
        ["Cache key 必須包含真正影響 response 的維度，否則會資料洩漏。", "Shared memory node 不是 response body；body 通常在 cache file。", "Stale-while-error 與 stale-while-updating 是可用性政策，不是免費正確性。", "Publish cache file 要避免其他 worker 看見半寫入內容；注意 temp file 與 rename。"],
        "Proxy 路徑到此完整；Part 6 回頭解剖支撐所有章節的 memory、container、buffer 與 module primitives。",
    ),
    34: G(
        """
Event-driven code 有大量短命小物件；若每個欄位都 malloc/free，error path 會非常複雜且容易 leak。NGINX pool 把 allocation 綁定明確 lifecycle：request 結束時整批釋放，必要 side effect 則登記 cleanup handler。

Use case 是 headers、module ctx、chain links 等數十個 request-lifetime allocations。Pool 不是通用 garbage collector；它的威力來自『同一批物件同生共死』。
""",
        ("Region/arena allocator", "指定 pool 上的 size/alignment allocation request", "與 pool 同壽命的 memory；可選 cleanup record", "small blocks、large allocation list、cleanup list", "把短命 pointer 存到長命 owner、忘記 cleanup 外部資源、誤以為可逐一 free"),
        ["建立與 cycle/connection/request 對應的 pool", "small allocation 從目前 block bump pointer 取得", "空間不足時找其他 block 或擴充", "large allocation 另外 malloc 並掛 list", "需要 close/free side effect 時註冊 cleanup", "工作期間通常不逐一 free", "owner lifecycle 結束時執行 cleanups", "一次釋放所有 blocks/large allocations"],
        [("Arena allocation", "大量同壽命物件以低成本配置與整批回收。"), ("Lifetime ownership", "pool 是明確 owner boundary，而非隱藏 global allocator。"), ("Cleanup registry", "memory 之外的 file/library resource 以 callback 收口。")],
        ["配置在哪個 pool 比『哪裡 palloc』更重要；先追 pool owner。", "`ngx_pfree` 主要針對 large allocations，不代表 small objects 可普遍逐一 free。", "Pool reset/destroy 後 pointer 全部失效，不能 cache 到更長生命週期。", "Cleanup handler 執行順序與重複註冊會影響 resource safety。"],
        "Pool 解決 allocation；下一章比較 array、list、queue、hash、rbtree 等資料結構為何各自存在。",
    ),
    35: G(
        """
資料結構不是因為教科書列過就使用，而是由 operation set、lifetime、ordering、mutation frequency 與 memory layout 決定。NGINX 同時使用 array、list、queue、hash、radix tree、rbtree，正好展示『從 workload 導出 container』。

Use case 是 headers 需要 append/iterate、timers 需要 ordered min/delete、config names 需要快速 lookup、LRU 需要 O(1) move/remove。把所有東西都放 hash map 會失去順序、最小值或 intrusive ownership 的優勢。
""",
        ("Container selection discipline", "操作需求、資料量、lifetime 與 locality", "符合 workload 的結構與 invariant", "通常由外層 pool/owner 管理；intrusive node 嵌在 object", "選錯 complexity、忽略常數/locality、node 重複掛載、mutation invariant 破壞"),
        ["先列主要 operations", "確認是否要排序、prefix、min、arbitrary delete", "估計資料量與啟動期/執行期比例", "決定 contiguous、chunked 或 pointer-linked layout", "決定 intrusive 或 owning container", "寫下 invariants", "用真實 workload benchmark/trace", "只在需求改變時換結構"],
        [("Workload-driven design", "先有操作與限制，再選 Big-O 與 layout。"), ("Intrusive multi-indexing", "同一 object 可嵌不同 node 同時進 timer/LRU 等索引。"), ("Build-time optimization", "config-time 花較多成本建立 runtime 快路徑。")],
        ["看 container API 時先問 ownership：container 是否配置 element，還是只掛 node。", "Array 的 contiguous locality 常比理論擴容成本更重要。", "NGINX list 是分塊 append 結構，不等同一般 doubly linked list。", "Queue macros 不檢查 node 是否已掛載；invariant 由 caller 保證。"],
        "Container 保存 metadata；下一章聚焦真正搬運 bytes 的 buffer 與 chain。",
    ),
    36: G(
        """
高效 proxy 不應反覆複製 response body。`ngx_buf_t` 描述 memory range 或 file range，`ngx_chain_t` 把多段資料串起來；output layer 可用 writev 聚合 memory buffers、用 sendfile 傳 file region。

Use case 是一個 response 同時含 header memory、file body 與 filter 產生的 chunks。Buffer 是 view/cursor，不一定擁有底層 bytes；這讓切片與轉送便宜，也提高 ownership 難度。
""",
        ("Scatter/gather byte representation", "memory/file regions + semantic flags", "可逐段消費與交給下一 filter 的 chain", "底層 storage owner + buffer cursors + chain links", "底層先釋放、cursor 錯誤、flags 丟失、shadow buffer 重複回收"),
        ["producer 建立 memory/file buffer views", "chain links 表示輸出順序", "filter 讀取 pos/last 或 file_pos/file_last", "必要時建立 shadow/copy view 而非複製 bytes", "output chain 合併相鄰/相容區段", "writev/sendfile 嘗試傳輸", "partial send 後只移動 cursor", "完全消費後回收 chain/buffer"],
        [("Slice/view", "buffer 描述資料區間，不必擁有或複製資料。"), ("Scatter/gather I/O", "多個區段一次 syscall 傳送。"), ("Zero-copy mindset", "減少 user-space copy，但仍尊重 framing/filter 限制。")],
        ["永遠同時看 memory 與 file 兩組 cursor。", "`temporary`、`memory`、`mmap`、`in_file` 等 flags 決定可否修改與如何傳送。", "`last_buf` 是 response 結束語意，不只是最後一個 list node。", "Shadow buffer 共用底層 storage；回收條件要避免 use-after-free。"],
        "單 worker 內資料流清楚後，下一章處理多 workers 真正共享 state 時的 allocator 與同步。",
    ),
    37: G(
        """
普通 heap memory 在 fork 後是 copy-on-write，不能自然讓 workers 看見彼此更新。Rate limit、upstream zone、cache metadata 等功能需要 shared memory，並在其中自行配置 object、使用 atomic/lock 維護一致性。

Use case 是所有 workers 共用一份計數器或 peer health state。Shared memory 只提供共同 bytes，不提供 allocator、type safety 或 race protection；NGINX 以 slab allocator 與 shmtx 補足。
""",
        ("Cross-process shared state", "named shared zone + size + init callback", "所有 workers 可見的 structured state", "mmap shared region、slab pool、atomic/shmtx-protected invariants", "race、dead process 持鎖、fragmentation、reload layout incompatibility"),
        ["config 註冊 named shared memory zone", "cycle 初始化或 reuse mapping", "zone init 建/接回 root data", "slab 在 shared region 配置 object", "讀寫前依 invariant 使用 atomic 或 shmtx", "更新 intrusive tree/queue/hash", "reload 新 workers attach compatible zone", "所有世代結束後才真正 unmap"],
        [("Shared-nothing by default", "只有明確需要的 state 才進 shared zone。"), ("Allocator inside mapped region", "pointer graph 與 metadata 都必須位於共享地址空間。"), ("Fine-grained synchronization policy", "atomic、mutex 或 immutable read 依 invariant 選擇。")],
        ["Shared zone name/size 是 reload compatibility contract。", "不要把 process-local pointer 存進可由不同 mapping address 解讀的持久格式。", "Lock 保護的是 invariant，不是『某行 code』；先列出共同更新的結構。", "Slab fragmentation 與 lock contention 都可能成為高併發瓶頸。"],
        "Core primitives 之所以可被眾多功能共用，靠的是下一章的 module system 與 lifecycle hooks。",
    ),
    38: G(
        """
NGINX core 不可能預先知道所有 protocol、directive、phase handler 與 filter。Module system 以 command tables、context callbacks、module type/index 與 lifecycle hooks，把擴充點固定下來，讓功能可加入而不修改主線。

Use case 是新增 HTTP module：提供 directives、建立/合併 config、註冊 phase/filter/content handler，worker 啟動時初始化。這是 C 語言中的 plugin architecture。
""",
        ("Module/plugin lifecycle", "module descriptor、commands 與 callbacks", "被 config/runtime pipeline 可發現的功能", "module indices、main/srv/loc conf arrays、global filter chains", "hook order、ctx index 錯誤、merge 漏失、ABI/build mismatch"),
        ["Build system 收集 module descriptor", "preconfiguration 註冊 variables 等前置項", "create main/srv/loc conf", "parser 透過 command table dispatch directives", "merge nested conf", "postconfiguration 掛 phase/filter handlers", "process/thread init hooks 建 runtime resources", "exit hooks cleanup"],
        [("Plugin architecture", "core 定義穩定 extension points，module 注入行為。"), ("Dependency inversion", "高階 flow 依 callback contract，不依具體 module。"), ("Lifecycle hooks", "配置、程序與 request 時期分開，避免初始化混亂。")],
        ["`ngx_module_t` 與 type-specific ctx 要一起讀。", "module index、ctx_index 用途不同；取 conf 的 macro 依 type/context 選擇。", "Filter module 必須保存 previous top filter 再替換，形成 chain。", "Dynamic module 仍有 binary compatibility/build options 約束，不等於任意共享 library。"],
        "理解 module framework 後，Part 7 不再只讀：從最小 content module 開始親手使用這些 contract。",
    ),
    39: G(
        """
第一個 module 的目標不是做複雜功能，而是走完『directive → config → content handler → response filter → cleanup』閉環。只有親手註冊並看到 request 進入 handler，module architecture 才從名詞變成可操作模型。

Use case 是一個 location 直接回傳文字與正確 HTTP status/headers/body。它會暴露最基本的 pool allocation、buffer flags 與 send header/output filter contract。
""",
        ("Minimal HTTP content module", "location directive + routed request", "合法的 HTTP response", "location conf、request pool buffer/chain", "directive context 錯誤、Content-Length 不符、buffer lifetime/last flag 錯誤"),
        ["定義 module commands 與 context", "create location conf", "directive setter 安裝 content handler/文字", "request location match 後進 handler", "檢查允許 method", "設定 status/content type/content length", "從 request pool 建 buffer/chain", "send header，再交 output filter"],
        [("Vertical feature slice", "從 config 到 runtime output 的最小完整功能。"), ("Framework contract learning", "透過真實 hook/return code 理解 core。"), ("Ownership by request", "response metadata 與 buffers 由 request pool 管理。")],
        ["先確認 handler 何時被設到 core loc conf，而不只是函式本身。", "HEAD request 與 header-only response 不應仍送 body。", "Output filter 可能回 AGAIN；不要假設一次呼叫已送完。", "Buffer 的 `last_buf`/memory flags 與 Content-Length 必須一致。"],
        "會產生內容後，下一章改成在 content 之前做 access decision，理解 phase short circuit。",
    ),
    40: G(
        """
Access control 必須在昂貴 content/upstream 工作開始前執行，並且能與其他 access modules 共存。這一章用自訂 header/token 規則練習 access phase、configuration merge 與拒絕 response。

Use case 是內部 endpoint、簡化 API key 或 allowlist。真正 production auth 會更複雜，但 phase contract 相同：允許就 declined/continue，拒絕就回 401/403，async 驗證則保存 state 後暫停。
""",
        ("Access-phase policy module", "parsed request + merged location policy", "continue pipeline 或拒絕 status", "location conf + optional request ctx", "fail-open、安全 phase 順序、internal redirect 重入、secret comparison 問題"),
        ["directive 解析 policy/token", "merge parent/child loc conf", "postconfiguration 把 handler push 到 access phase", "request 到 access phase 時取得 config", "讀 header/variable 並驗證", "未啟用則 DECLINED", "允許則 OK/DECLINED 依 satisfy contract", "拒絕則設定 challenge/status 並 finalize"],
        [("Policy enforcement point", "在固定 phase 集中安全判斷。"), ("Chain of responsibility", "多個 access handlers 可依 satisfy policy 組合。"), ("Fail closed", "配置或驗證異常不可意外繞過保護。")],
        ["理解 access checker 對 OK、DECLINED、401、403 的處理。", "Internal redirect 可能再次進 phase；module ctx 要處理重入。", "不要把 secret 直接長期明文 log；比較也要考慮 timing/normalization。", "Subrequest 是否應繼承或重新驗證 policy 必須明確。"],
        "除了 phase，module 也常向其他 config/filter 暴露資料；下一章加入惰性 variable 與 response header。",
    ),
    41: G(
        """
NGINX variables 讓 log、rewrite、proxy headers 等消費者用統一名稱取得 request 資料。它們通常惰性求值，避免每個 request 都計算所有可能變數；header filter 則能把同一 request ID 安全送回 client。

Use case 是產生一次 request-scoped correlation ID，同時出現在 access log、upstream header 與 response header。若每個 consumer 各算一次，跨服務追蹤會得到不同 ID。
""",
        ("Lazy request value + header filter", "variable lookup 或 response-header phase", "穩定 request ID value 與新增 header", "request module ctx/pool + variable cache metadata", "stack pointer、stale cached value、重複 header、CRLF injection"),
        ["preconfiguration 註冊 variable name/get handler", "consumer 首次 lookup 時呼叫 get handler", "get/create request ctx 並生成一次 ID", "填 variable value flags/data/len", "後續 lookup 使用 cache", "header filter 讀同一 ctx/value", "安全 push header table element", "呼叫 next header filter"],
        [("Lazy evaluation", "只有真正使用 variable 時才計算。"), ("Memoization", "request-stable value 計算一次，所有 consumers 共用。"), ("Correlation context", "同一 identity 穿過 logs、headers 與 upstream。")],
        ["Variable data 必須活到 consumer 完成，通常放 request pool。", "`not_found` 與存在但空字串語意不同。", "`no_cacheable` 決定同 request 多次讀取是否重算。", "Header filter 需考慮 subrequest、重入與 headers already sent。"],
        "普通 header filter 只處理 metadata；下一章挑戰可跨任意 buffer 邊界保存狀態的 streaming body filter。",
    ),
    42: G(
        """
Body filter 不會收到完整 response string，而是任意大小、任意次數的 buffer chains。若要替換 token、計算 digest 或轉碼，匹配可能跨兩個 buffers，還要保留 flush/last 與 downstream backpressure。

Use case 是把串流中的 `foo` 改成 `bar`；第一個 buffer 可能只以 `f` 結尾，下一個才從 `oo` 開始。Stateless 字串 replace 會漏匹配或重複資料。
""",
        ("Stateful streaming transform", "一批 input buffers + 上次殘留 partial token", "語意等價、flags 正確的 output chain", "request module ctx、carry bytes、busy/free chains", "跨 buffer corruption、Content-Length 錯誤、flag 遺失、下游 AGAIN 後重複輸出"),
        ["首次呼叫建立 request ctx", "逐 buffer 讀取可消費 bytes", "將前次 partial prefix 與新 bytes 合併判斷", "輸出已確定不可能再延伸的資料", "保存仍可能成為 match 的 suffix", "傳遞 flush/sync 並在 last 時 flush carry", "呼叫 next body filter", "AGAIN 時保留 output ownership，writable 後續送"],
        [("Streaming finite-state transducer", "有限 carry state 將 chunk stream 轉成另一條 stream。"), ("Boundary-independent processing", "結果不應依 input 如何切 chunk。"), ("Backpressure transparency", "filter 不吞掉或偽造下游 flow-control signal。")],
        ["先定義 Content-Length 是否仍有效；變長度通常需清除並改用 chunked/framing。", "不可修改 read-only memory/file buffer；必要時配置新 buffer 或 shadow。", "Last/flush/sync flags 必須附在語意正確的最後輸出 buffer。", "用每個可能切點測試 token，才能驗證跨 buffer state。"],
        "掌握 request/filter module 後，下一章實作更深入的 peer scheduler，串起 upstream callbacks 與 shared state。",
    ),
    43: G(
        """
自訂 load balancer 迫使你同時處理 config-time 初始化、per-upstream peer data、per-request tried state、get/free callbacks、失敗回饋與 multi-worker visibility。它是驗證 upstream 理解最完整的練習。

Use case 是根據 latency score、tenant 或自訂 capacity 選 peer。演算法本身可能只有十行，真正困難的是 callback contract、fallback、concurrency 與 lifecycle。
""",
        ("Custom upstream scheduler module", "upstream server config + request-time peer state", "一個 peer connection candidate 與完成後 feedback", "upstream peer data、per-request selection data、可選 shared zone", "選到 down/tried peer、所有 peers exhausted、race、feedback 遺失"),
        ["directive 選擇自訂 balancer", "upstream init 建立 peers/policy metadata", "request init 建 per-request tried/context", "get callback 過濾不可用 peers", "計算 score 並回傳 sockaddr/name", "通用 upstream connect/send/read", "free callback 接收 success/failure state", "更新 local/shared feedback 並保留 fallback"],
        [("Strategy plugin", "替換 peer selection，不重寫 upstream transport。"), ("Feedback loop", "完成結果影響未來 scheduling。"), ("Local fast path + optional shared truth", "精確跨 worker state 與低 contention 之間取捨。")],
        ["先完整包住原 round-robin data model，再改 selection，避免一開始重建全部 contract。", "Per-request tried set 與 global peer health 是兩種不同 state。", "Free callback 的 flags 是分類訊號，不是簡單 boolean success。", "若使用 shared memory，reload compatibility 與 lock invariant 必須一起設計。"],
        "實作完成仍需知道怎麼證明正確與不拖慢 worker；下一章建立除錯、測試與效能方法。",
    ),
    44: G(
        """
Source-level correctness、protocol correctness、failure recovery 與 performance 需要不同證據。單靠 happy-path curl 無法發現 fragmented input、slow client、retry duplicate 或 handler blocking。

Use case 是 module 偶發 502、worker CPU 100%、memory 隨 requests 增長。這一章把 debug log、GDB、sanitizer、strace/perf、fault injection 與 regression test 組成分層診斷法。
""",
        ("Evidence-driven validation", "症狀、可重現 workload、source hypothesis", "可定位的 root cause 與防回歸測試", "test harness、logs/traces/profiles/core dumps", "不可重現、觀測干擾、只測成功路徑、microbenchmark 誤導"),
        ["把症狀改寫成可觀察 invariant", "縮成最小 config/request", "用 request ID 建時間線", "source/log 找狀態轉換點", "fault injection 固定觸發 branch", "選 GDB/ASan/strace/perf 回答特定問題", "修正後加入 regression test", "以壓力與長時間測試驗證副作用"],
        [("Layered observability", "application log、syscall、CPU profile、memory checker 各回答不同層。"), ("Fault injection", "主動製造 timeout、partial I/O 與 abort。"), ("Invariant-based testing", "驗證 ownership/ordering/once-only，而不只驗 output。")],
        ["Debug build 的 timing 可能和 optimized build 不同；結論需交叉驗證。", "CPU profile 顯示花在哪裡，不自動告訴你為什麼。", "Leak 要區分仍被 cache/pool 合法持有，或 lifecycle 真正未釋放。", "測試至少涵蓋每個 I/O 邊界的 AGAIN、timeout、EOF 與 error。"],
        "知道如何重現後，下一章透過真實 bug fix 學會從 patch 反推 invariant 與架構判斷。",
    ),
    45: G(
        """
成熟 source code 的價值不只在當前實作，也在 bug fix 顯示哪些 assumption 曾經不成立。高品質 review 會問 ownership、all return paths、protocol edge cases、backward compatibility 與 regression proof。

Use case 是讀一個看似只改三行的 patch：為什麼必須在這裡清 flag？哪些 callback 可能再次進入？沒有測試時如何證明 bug 不會回來？
""",
        ("Patch-as-design-evidence", "bug report、diff、tests、history context", "被明確化的 invariant 與可驗證修正", "affected object lifecycle + regression scenario", "只看 happy diff、忽略 error branch、修 symptom 不修 invariant、history context 遺失"),
        ["先用舊版重現 bug", "描述預期 invariant 與實際違反", "找 state 第一次偏離的位置", "讀 patch 改了哪個 owner/transition", "列出所有進入與退出 branch", "檢查 cleanup/retry/reload/subrequest 交互", "執行新增與相鄰 tests", "用自己的話寫 review rationale"],
        [("Invariant repair", "好的 patch 恢復可陳述規則，不只是遮住 crash。"), ("Regression archaeology", "history 顯示 abstraction 在真實需求下的壓力點。"), ("Minimal change with complete reasoning", "diff 可小，但影響面分析必須完整。")],
        ["`git blame` 不是找人，而是找當時 constraint 與相關 commit。", "Patch 新增的 flag/check 常代表此前隱含 lifecycle assumption。", "Review success path、error path、timeout path 與 cleanup path。", "測試若無法穩定重現原 bug，綠燈不能證明修正有效。"],
        "親手實作與 review 後，Part 8 把具體程式提升成 architecture：先看 connection layer 為何不能知道 HTTP。",
    ),
    46: G(
        """
Event/connection layer 只應處理 bytes、readiness、timer 與 socket lifecycle；若它直接知道 HTTP method/location，加入 stream TCP proxy、mail protocol 或新 transport 時就必須修改底層。NGINX 以 listening handler 與 callbacks 把 protocol 注入上層。

Use case 是同一套 connection/event primitives 同時支援 HTTP、stream 與 mail。這不是為了抽象漂亮，而是讓新需求不破壞已驗證的底層。
""",
        ("Protocol-independent transport layer", "fd readiness、generic connection、protocol callback", "bytes/event 服務，不解讀上層語意", "connection/event structures；protocol state 位於上層 object", "dependency inversion 破壞、底層 condition explosion、跨協定回歸"),
        ["event layer accept generic connection", "listening config 提供 protocol handler", "handler 建立 HTTP/stream/mail state", "transport read/write wrappers 搬 bytes", "上層 parser 解讀 protocol", "上層替換 event callbacks", "event layer 只排程 readiness/timer", "close 時沿 owner contract cleanup"],
        [("Layering", "下層提供機制，上層提供協定政策。"), ("Dependency inversion", "transport 呼叫注入的 protocol callback，而非依賴 HTTP。"), ("Stable waist", "connection/event API 成為多協定共用的窄介面。")],
        ["檢查 `listening->handler` 如何把 accepted connection 交給不同 protocol。", "Generic `c->data` 的型別會隨上層階段改變，contract 比 static type 更重要。", "抽象不代表零成本；函式指標與 generic data 換來擴充隔離。", "若一個新功能要求改 event core，先問是否其實應位於 protocol/module layer。"],
        "分層帶來優雅，但任何長壽專案也會累積妥協；下一章學會同時看見優點與歷史包袱。",
    ),
    47: G(
        """
真正讀懂源碼不是從『所有設計都很漂亮』變成挑錯，而是能把設計放回當時 OS、硬體、相容性與使用情境，判斷哪些是核心 invariant、哪些是歷史成本、哪些在今天仍值得保留。

Use case 是評估 process model、global module indices、C macro、filter chaining 或 config inheritance。更現代的語言可能提供不同工具，但 trade-off 並不因此消失。
""",
        ("Contextual architecture evaluation", "現有 design、history、workload 與新需求", "保留、局部重構或替換的有證據判斷", "architectural invariants + compatibility constraints", "以審美取代資料、忽略 migration cost、破壞成熟 failure behavior"),
        ["先陳述原設計解決的問題", "列出當時與現在 constraints", "找出穩定 contract 與 incidental implementation", "蒐集實際 pain：bug、耦合、性能、維護成本", "提出至少兩個替代方案", "比較 migration/compatibility/failure risk", "用小實驗或 incremental refactor 驗證", "只在收益超過風險時改變"],
        [("Trade-off analysis", "每個 abstraction 同時降低一類成本並增加另一類成本。"), ("Evolutionary architecture", "成熟系統靠相容的小步演化，不是每次重寫。"), ("Chesterton's fence", "刪改前先理解現有結構為何存在。")],
        ["把『global』『macro』『C』直接當壞味道會錯過 workload 與 ABI context。", "歷史包袱需有具體 symptom：修改擴散、bug 類型、性能或測試困難。", "重構 async lifecycle 時最容易遺失少見 error/timeout branch。", "比較替代方案時包含 rollout、observability 與 rollback，而非只比程式碼行數。"],
        "最後一章把這些觀察抽象成能帶去 Redis、Node.js、Envoy、資料庫與 coding interview 的方法。",
    ),
    48: G(
        """
若讀完只記得 `ngx_http_upstream_next` 在哪個檔案，能力無法遷移。真正可帶走的是六個問題：事件從哪來、誰保存跨等待狀態、誰喚醒、資料如何限流、資源由誰擁有、失敗後能否 retry/cleanup。

Use case 是第一次閱讀 Redis、libuv、Netty、Envoy、database storage engine 或陌生 interview system。具體 API 不同，但 event、state、lifetime、pipeline、scheduler 與 failure semantics 仍可比較。
""",
        ("Transferable systems-reading method", "陌生 codebase + 一條 user-visible flow", "可驗證的 architecture/source map", "問題清單、object/flow/failure diagrams、small experiments", "強行套 NGINX 名詞、忽略 thread/I/O model 差異、技術選型先於 constraints"),
        ["選一條可在一天內回答的 visible path", "找 ingress/egress 與 process/thread boundary", "找跨 async boundary 存活的 state object", "找 callback/wakeup/scheduler", "找 queues、buffers、watermarks 與 deadlines", "列 cancel/retry/cleanup failure matrix", "用 trace 與小修改驗證", "把具體名稱改寫成通用 pattern"],
        [("Mechanism vs policy", "event loop/queue 是機制，routing/retry 是政策。"), ("Constraint-driven design", "先問 operation、scale、ordering、failure，再選結構。"), ("Learning loop", "問題 → source model → experiment → implementation → review。")],
        ["不要看到 event loop 就假設是單 thread；確認 thread/core/shard model。", "不要看到 tree 就先背旋轉；先問它支援哪些 operations。", "比較系統時把 correctness、latency、memory、operability 與 evolution 一起看。", "最終驗收是能在陌生專案畫 flow、指出 owner/wakeup/failure，並做出一個安全小修改。"],
        "全書到此結束；接下來應選一個 lab 或真實小 patch，把閱讀轉成自己的實作與判斷力。",
    ),
}


assert set(BEGINNER_GUIDES) == set(range(1, 49))
