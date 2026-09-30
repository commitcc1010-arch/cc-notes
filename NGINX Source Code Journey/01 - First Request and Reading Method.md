---
title: "先看到請求真的動起來"
part: 1
source_baseline: release-1.31.5
---

# Part 1　先看到請求真的動起來

先不囤積整套背景知識。用一次真實 reverse proxy request 建立黃金路徑、實驗環境、閱讀方法與最低限度 C。

# 第 1 章　一個請求究竟經過了什麼？

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Reverse proxy（反向代理）</h3><div class="foundation-block"><span>白話定義</span><p>Client 只連到代理伺服器；代理再代表 client 連到內部 backend。Client 不需要知道 backend 的位址，也不會直接與它建立連線。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>瀏覽器請求 <code>shop.example.com</code>，NGINX 收到後轉給內網的 <code>10.0.0.8:8080</code>，再把結果送回瀏覽器。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 client connection 與 upstream connection 之間轉換、緩衝並轉送 HTTP 資料。</p></div></section><section class="foundation-card"><h3>Request 與 Response</h3><div class="foundation-block"><span>白話定義</span><p>Request 是 client 提出的要求，通常包含 method、URL、headers 與可選 body；response 是 server 回覆的 status、headers 與 body。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>GET /users/7</code> 是 request；<code>200 OK</code> 加上一段 JSON 是 response。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 先解析 request，依設定選 handler，再建立或轉送 response。</p></div></section><section class="foundation-card"><h3>Transport（傳輸層工作）</h3><div class="foundation-block"><span>白話定義</span><p>Transport 只關心 bytes 如何經由連線抵達與送出，不理解這些 bytes 代表登入、圖片或 HTTP header。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>TCP 保證有順序的 byte stream，但不保證一個 <code>send()</code> 對應另一端的一個 <code>recv()</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 connection/event layer 處理 socket 與 readiness，上層 HTTP module 才解釋語意。</p></div></section><section class="foundation-card"><h3>Backend / application server</h3><div class="foundation-block"><span>白話定義</span><p>真正執行商業邏輯的程式，例如登入、付款、查詢資料庫。它通常位於 NGINX 後方。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Python Django、Java Spring 或 Go service 都可以是 backend。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 選擇 backend、建立 upstream connection，並把 request 轉成 backend 能理解的格式。</p></div></section><section class="foundation-card"><h3>Callback（回呼函式）</h3><div class="foundation-block"><span>白話定義</span><p>現在先把『未來某件事發生時要做什麼』存成函式；事件發生後，由框架呼叫它。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Socket 現在沒有資料時不等待；先記住 <code>on_readable</code>，有資料可讀時再執行。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_event_t.handler</code> 保存下一次 read、write 或 timer event 到來時要執行的函式。</p></div></section></div>



<p class="chapter-question">在瀏覽器按下 Enter 後，NGINX 到底做了哪些事，才把請求交給另一台伺服器？</p>

<div class="chapter-meta"><span>難度：入門</span><span>reverse proxy · request path · control flow</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

先建立一條可以反覆回到的黃金路徑；後面每一章只是把其中一個方塊放大。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node active"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><div class="position-card muted"><span>上一站</span><strong>全書導讀</strong></div><div class="position-card current"><span>你在這裡</span><strong>01. 一個請求究竟經過了什麼？</strong></div><a class="position-card" href="#chapter-02-建立可觀察的-nginx-實驗室"><span>下一站</span><strong>02. 建立可觀察的 NGINX 實驗室</strong></a></div>

本章位於 **Part 1：先看到請求真的動起來**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

這是全書的 GPS。初學者若先掉進 `main()`、macro 或資料結構，很快會失去「這段 code 最後替使用者做什麼」的方向。本章先把一個 reverse proxy request 從 client、NGINX 到 backend 再回來走完；以後看到任何函式，都能把它放回這張路線圖。

真實 use case 是一個公開網址背後有多台內部服務。NGINX 必須同時處理 transport、HTTP 語意、routing、backend 選擇與 response forwarding。沒有這張整體模型，connection、request、upstream 很容易被誤認為同一件事。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>這是全書的 GPS。初學者若先掉進 <code>main()</code>、macro 或資料結構，很快會失去「這段 code 最後替使用者做什麼」的方向。本章先把一個 reverse proxy request 從 client、NGINX 到 backend 再回來走完；以後看到任何函式，都能把它放回這張路線圖。</p></section><section class="design-decision-card"><span>真實 use case</span><p>真實 use case 是一個公開網址背後有多台內部服務。NGINX 必須同時處理 transport、HTTP 語意、routing、backend 選擇與 response forwarding。沒有這張整體模型，connection、request、upstream 很容易被誤認為同一件事。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「整條 reverse proxy 路徑」這個責任邊界；接收 client socket 上抵達的 bytes，交付 送往 backend 的 request 與回到 client 的 response。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 cycle → connection → request → upstream 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 任何 I/O 都可能暫停；任何一段都可能 timeout、close 或 retry。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>整條 reverse proxy 路徑</p></div><div class="contract-card"><span>接收什麼</span><p>client socket 上抵達的 bytes</p></div><div class="contract-card"><span>產生什麼</span><p>送往 backend 的 request 與回到 client 的 response</p></div><div class="contract-card"><span>狀態由誰保存</span><p>cycle → connection → request → upstream</p></div><div class="contract-card"><span>主要失敗出口</span><p>任何 I/O 都可能暫停；任何一段都可能 timeout、close 或 retry</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>OS 通知 listening socket 可讀</p></div><div class="flow-step"><span>2</span><p>accept client 並建立 connection/event</p></div><div class="flow-step"><span>3</span><p>逐段解析 HTTP，建立 request</p></div><div class="flow-step"><span>4</span><p>location 與 phase engine 選出 proxy handler</p></div><div class="flow-step"><span>5</span><p>建立 upstream、選 backend、non-blocking connect</p></div><div class="flow-step"><span>6</span><p>轉送 request 與 response</p></div><div class="flow-step"><span>7</span><p>finalize request，keep-alive 或 close</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

先把 NGINX 想成一個交通轉運站，而不是「會執行網站程式的框架」。它長時間持有許多 socket；核心工作是等待哪一條 socket 現在可以讀或可以寫，然後只推進那條連線的下一小步。

一個 TCP connection 可以承載多個 HTTP request。connection 是運輸通道，request 是一次語意操作。NGINX 接受連線後先建立 connection 與 read/write event；讀到 request line 和 headers 後才建立完整 HTTP request 語境。若 location 選中了 `proxy_pass`，HTTP proxy module 建立 upstream 物件，選 backend、非阻塞連線、送出請求、解析回應，再讓 filter chain 把資料送回 client。

這條路徑不是一次函式呼叫到底。遇到 socket 暫時不可讀或不可寫時，函式返回，控制權回到 event loop；下一個 readiness event 到來才繼續。因此真正的主角是「物件保存的狀態＋下一個 callback」，不是很深的同步 call stack。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

最直覺的寫法是讓一個函式從 accept 一路 blocking 到 backend response。問題是任何一次等待都會占住整條執行線。NGINX 將工作拆成短 callback，每次只推進一小步，狀態留在長命物件中。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Request.state</code></td><td><code>ngx_http_request_t</code>／<code>ngx_http_upstream_t</code> 中跨 event 保存的狀態</td></tr><tr><td><code>ready</code> queue</td><td>epoll ready list 加上 posted events</td></tr><tr><td><code>callback(request)</code></td><td><code>ev-&gt;handler(ev)</code> 再由 connection 找回 request</td></tr><tr><td>三個 callbacks</td><td>client read、upstream connect/write、upstream read 等 continuation</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/event/ngx_event_accept.c`，官方 `release-1.31.5` 第 21–66 行

```c
ngx_event_accept(ngx_event_t *ev)
{
    socklen_t          socklen;
    ngx_err_t          err;
    ngx_log_t         *log;
    ngx_uint_t         level;
    ngx_socket_t       s;
    ngx_event_t       *rev, *wev;
    ngx_sockaddr_t     sa;
    ngx_listening_t   *ls;
    ngx_connection_t  *c, *lc;
    ngx_event_conf_t  *ecf;
#if (NGX_HAVE_ACCEPT4)
    static ngx_uint_t  use_accept4 = 1;
#endif

    if (ev->timedout) {
        if (ngx_enable_accept_events((ngx_cycle_t *) ngx_cycle) != NGX_OK) {
            return;
        }

        ev->timedout = 0;
    }

    ecf = ngx_event_get_conf(ngx_cycle->conf_ctx, ngx_event_core_module);

    if (!(ngx_event_flags & NGX_USE_KQUEUE_EVENT)) {
        ev->available = ecf->multi_accept;
    }

    lc = ev->data;
    ls = lc->listening;
    ev->ready = 0;

    ngx_log_debug2(NGX_LOG_DEBUG_EVENT, ev->log, 0,
                   "accept on %V, ready: %d", &ls->addr_text, ev->available);

    do {
        socklen = sizeof(ngx_sockaddr_t);

#if (NGX_HAVE_ACCEPT4)
        if (use_accept4) {
            s = accept4(lc->fd, &sa.sockaddr, &socklen, SOCK_NONBLOCK);
        } else {
            s = accept(lc->fd, &sa.sockaddr, &socklen);
        }
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_event_accept()</code> 接受 client socket，取得一個 <code>ngx_connection_t</code>，建立 connection pool。</p></div><div class="source-step"><span>2</span><p>listening socket 的 protocol handler 把新 connection 交給 <code>ngx_http_init_connection()</code>。</p></div><div class="source-step"><span>3</span><p>read event handler 先等待資料，再逐步解析 request line 與 headers。</p></div><div class="source-step"><span>4</span><p><code>ngx_http_core_run_phases()</code> 執行 rewrite、access、content 等階段。</p></div><div class="source-step"><span>5</span><p>proxy content handler 建立 <code>ngx_http_upstream_t</code>，選 peer 並建立 backend connection。</p></div><div class="source-step"><span>6</span><p>response 經 header/body filters 與 write filter 回到 client，最後 finalize request。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先找 accepted client 如何從 <code>ngx_connection_t</code> 進入 HTTP handler。</p></div><div class="microscope-card"><span>2</span><p>看到 return 時確認工作是完成，還是已安排下一個 event。</p></div><div class="microscope-card"><span>3</span><p>畫出 client 與 backend 兩組 read/write events，不要合成一條。</p></div><div class="microscope-card"><span>4</span><p>找 request finalize 前最後一個仍引用 request pool 的 callback。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 看到函式呼叫時先問它是在同步主線，還是由某個 event 之後重新進入。
- `NGX_AGAIN` 不是錯誤，而是『目前不能前進，狀態已保存』。
- 分清 client connection 與 upstream peer connection；兩邊各有 read/write event。
- 用 request number、connection number 與 handler 名稱重建時間線。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/ngx_event_accept.c#L21`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event_accept.c#L21) · [`src/http/ngx_http_request.c#L211`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L211) · [`src/http/ngx_http_upstream.c#L543`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L543)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

最容易犯的錯是把整條流程畫成同步函式鏈。實際上，client read、upstream connect、upstream write、upstream read、client write 都可能各自停在 `NGX_AGAIN`。每一次停下來，都會把「下次該做什麼」放進 event handler 或 request/upstream 欄位。

第二個關鍵是分清三種生命週期：cycle 對應一代設定與 worker 世界；connection 對應一條 transport；request 對應一次 HTTP 交換。後面的 memory pool、reload、keep-alive 和 subrequest，全部依賴這個分層。

讀任何函式時固定問四題：現在處理哪個物件？物件處於哪個狀態？這次最多推進到哪裡？若資源尚未 ready，誰會在未來重新叫醒它？這四題比背 call graph 更可靠。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Reactor</h3><p>event loop 收到 readiness 後呼叫短小 handler；不能前進就返回。</p></div><div class="pattern-card"><h3>Explicit state machine</h3><p>跨等待存活的狀態放在 request/upstream 欄位，而不是 stack。</p></div><div class="pattern-card"><h3>Pipeline</h3><p>phase 與 filter 把一條巨型流程拆成可插拔步驟。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 準備兩個回傳不同文字的 backend，例如 9001 回 `A`、9002 回 `B`。
2. 設定一個 `upstream` 與 `proxy_pass`，連續呼叫十次，記錄回應落在哪個 backend。
3. 開啟 debug log，搜尋 `accept`、`http process request line`、`get rr peer` 與 `finalize request`，手動畫出一次請求。
4. 刻意讓其中一個 backend 延遲兩秒，觀察其他連線是否仍能前進。

## 常見誤解與失敗模式

- 把 reverse proxy 誤認為 HTTP redirect；redirect 是 client 重新發請求，proxy 對 client 隱藏 backend。
- 把 connection 與 request 當成同一物件，因而無法解釋 keep-alive。
- 認為一次 request 會由一個長 call stack 執行到底，忽略 event callback 的斷點。

## 可以帶走的 Coding／CS 能力

- 把複雜系統拆成資料流、控制流與生命週期三張圖。
- 理解 event-driven server、GUI loop、Node.js 與網路框架的共同模型。
- 面對陌生 codebase 時，先找一條 user-visible path，而不是先讀所有 utility。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

下一章先建立實驗室，讓這張概念圖能用 log、syscall 與故障注入被看見。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Reverse proxy 與 redirect 最大差異是什麼？</summary>

Redirect 回 3xx 與新網址，後續連線由 client 建立；reverse proxy 自己連 backend，client 通常只看見 NGINX。這使 proxy 能做負載均衡、重試、快取與協定轉換。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為什麼 connection 不能等同 request？</summary>

HTTP keep-alive 允許同一條 TCP connection 依序承載多個 request；HTTP/2 更能並行多個 stream。若生命週期綁死，就不能安全重用連線或分離 transport 與 protocol。

</details>

<details class="qa" markdown="1">
<summary>Q3. 哪個物件同時連起 client 與 backend？</summary>

`ngx_http_request_t` 持有 `r->connection` 指向 client connection，也可持有 `r->upstream`；後者再管理 peer connection。request 是這次代理交易的協調者。

</details>

<details class="qa" markdown="1">
<summary>Q4. 如果 upstream connect 尚未完成，worker 會等待在 `connect()` 嗎？</summary>

不會。non-blocking `connect()` 通常表示進行中，NGINX 為 backend write event 安裝 handler 與 timeout，返回 event loop；可寫事件出現後再檢查連線結果。

</details>

<details class="qa" markdown="1">
<summary>Q5. 為什麼先讀黃金路徑比先讀所有資料結構有效？</summary>

每個結構都有使用場景。先知道 timer、request、peer 在路徑中的責任，再學紅黑樹或 pool，知識會和真實約束綁在一起，也知道哪些欄位值得追。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何判斷自己真的理解了這一章？</summary>

不用看書，從 client 開始畫到 backend 再回 client，並在每個 I/O 邊界標出可能返回 `NGX_AGAIN` 的位置；還要能指出 cycle、connection、request 三種生命週期。

</details>

---

# 第 2 章　建立可觀察的 NGINX 實驗室

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Observability（可觀察性）</h3><div class="foundation-block"><span>白話定義</span><p>利用 log、metrics、trace 與 debugger，從程式外部推回內部實際發生的狀態轉換。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同一個 request ID 出現在 accept、upstream connect 與 response log，便能重建完整時間線。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Debug log、錯誤碼、request/connection 編號與 timing 欄位是驗證源碼理解的證據。</p></div></section><section class="foundation-card"><h3>System call（系統呼叫）</h3><div class="foundation-block"><span>白話定義</span><p>一般程式不能直接控制網卡、socket 或 process；它必須呼叫作業系統核心提供的入口。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>read()</code>、<code>write()</code>、<code>accept()</code>、<code>epoll_wait()</code> 都是 system calls。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>用 <code>strace</code> 觀察 syscall，可以確認 NGINX 最後真的向 kernel 要求了什麼。</p></div></section><section class="foundation-card"><h3>Debugger / GDB</h3><div class="foundation-block"><span>白話定義</span><p>Debugger 可以暫停程式、查看 call stack、變數與記憶體，並逐步執行。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>在 <code>ngx_http_upstream_handler</code> 設 breakpoint，觀察 <code>r-&gt;upstream</code> 當時指向什麼。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>它適合回答單次執行中的 object state；不適合取代 production metrics 或 protocol 測試。</p></div></section><section class="foundation-card"><h3>Worker process</h3><div class="foundation-block"><span>白話定義</span><p>長時間運行並實際處理 client connections 的 NGINX 子程序。每個 worker 通常有自己的 event loop。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>四核心主機可能啟動四個 workers，各自處理一批 connections。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>阻塞其中一個 worker 會延遲該 worker 管理的所有 ready events。</p></div></section></div>



<p class="chapter-question">讀源碼前需要哪些工具，才能把猜測轉成可重複驗證的證據？</p>

<div class="chapter-meta"><span>難度：入門</span><span>debug build · logs · strace · gdb</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

建立固定版本、debug build、最小設定與觀察工具；後面所有推論都能在這個環境重現。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node active"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-01-一個請求究竟經過了什麼"><span>上一站</span><strong>01. 一個請求究竟經過了什麼？</strong></a><div class="position-card current"><span>你在這裡</span><strong>02. 建立可觀察的 NGINX 實驗室</strong></div><a class="position-card" href="#chapter-03-如何閱讀一個陌生的-c-專案"><span>下一站</span><strong>03. 如何閱讀一個陌生的 C 專案</strong></a></div>

本章位於 **Part 1：先看到請求真的動起來**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

源碼閱讀若沒有可重現環境，很容易把猜測當事實。這一章不是工具清單，而是建立一條證據鏈：source 說可能怎麼走、debug log 顯示這次怎麼走、strace 顯示最後呼叫哪些 syscall、GDB 顯示物件當時長什麼樣。

Use case 是回答「為什麼這次回 502」「在哪個 callback 停住」「究竟有沒有重試」。若直接在 production 設定與多 worker 混合 log 中猜，因果關係會被併發與環境差異淹沒。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>源碼閱讀若沒有可重現環境，很容易把猜測當事實。這一章不是工具清單，而是建立一條證據鏈：source 說可能怎麼走、debug log 顯示這次怎麼走、strace 顯示最後呼叫哪些 syscall、GDB 顯示物件當時長什麼樣。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是回答「為什麼這次回 502」「在哪個 callback 停住」「究竟有沒有重試」。若直接在 production 設定與多 worker 混合 log 中猜，因果關係會被併發與環境差異淹沒。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「可重現的 NGINX lab」這個責任邊界；接收 固定 source tag、最小 config、可控制 request，交付 可比較的 log／trace／failure evidence。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 獨立 prefix、build flags、單 worker 與 request ID 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 工具本身會改變 timing；環境或版本不固定會產生假結論。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>可重現的 NGINX lab</p></div><div class="contract-card"><span>接收什麼</span><p>固定 source tag、最小 config、可控制 request</p></div><div class="contract-card"><span>產生什麼</span><p>可比較的 log／trace／failure evidence</p></div><div class="contract-card"><span>狀態由誰保存</span><p>獨立 prefix、build flags、單 worker 與 request ID</p></div><div class="contract-card"><span>主要失敗出口</span><p>工具本身會改變 timing；環境或版本不固定會產生假結論</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>固定 tag 與 configure arguments</p></div><div class="flow-step"><span>2</span><p>用 debug symbol／debug log 編譯</p></div><div class="flow-step"><span>3</span><p>建立獨立 prefix 與最小 config</p></div><div class="flow-step"><span>4</span><p>啟動可控制的兩個 backend</p></div><div class="flow-step"><span>5</span><p>送出帶唯一 ID 的 request</p></div><div class="flow-step"><span>6</span><p>從 log → source → syscall 交叉驗證</p></div><div class="flow-step"><span>7</span><p>一次只改一個變因</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
source ──configure──> Makefile ──make──> objs/nginx
   │                                      │
   ├── static reading: rg / ctags         ├── debug log
   ├── control flow: GDB                  ├── strace
   └── history: git blame/log             └── curl / load generator

猜測 ──> 設計小實驗 ──> 收集 log/syscall ──> 修正心智模型
```

## 從零建立心智模型

源碼閱讀最危險的狀態不是「看不懂」，而是覺得自己看懂卻沒有驗證。實驗室的目的不是建 production NGINX，而是讓每個問題都能用最小設定、單一 worker、清楚 log 與可控制 backend 重現。

固定 tag 與 commit 很重要。函式名稱通常穩定，但行號、欄位與模組會變；本書使用 `release-1.31.5` 的 commit `231a60ee…`。設定 `worker_processes 1` 可先消除跨 worker 干擾，等理解單 worker 後再打開競爭場景。

四種工具回答不同問題：`rg` 回答「符號在哪裡」；debug log 回答「這次真的走哪條路」；strace 回答「使用者空間最後呼叫了哪些 syscall」；GDB 回答「此刻資料結構內容與 call stack 是什麼」。不要拿一種工具解所有問題。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

直接大量 `print()` 會改變 timing，且不同 request 的訊息混在一起。較好的方法是固定 correlation ID、只記錄狀態轉換，並用不同工具各自回答 source、runtime 與 syscall 問題。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>request_id</code></td><td>debug log 中用 connection/request number 或自訂 header 串起事件</td></tr><tr><td>decorator</td><td>在少數 state-transition functions 加 instrumentation</td></tr><tr><td><code>elapsed_ms</code></td><td>upstream connect/header/response timing</td></tr><tr><td>structured dict</td><td>比散落文字更容易依 request、handler、state 過濾</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/nginx.c`，官方 `release-1.31.5` 第 200–253 行

```c
main(int argc, char *const *argv)
{
    ngx_buf_t        *b;
    ngx_log_t        *log;
    ngx_uint_t        i;
    ngx_cycle_t      *cycle, init_cycle;
    ngx_conf_dump_t  *cd;
    ngx_core_conf_t  *ccf;

    ngx_debug_init();

    if (ngx_strerror_init() != NGX_OK) {
        return 1;
    }

    if (ngx_get_options(argc, argv) != NGX_OK) {
        return 1;
    }

    if (ngx_show_version) {
        ngx_show_version_info();

        if (!ngx_test_config) {
            return 0;
        }
    }

    /* TODO */ ngx_max_sockets = -1;

    ngx_time_init();

#if (NGX_PCRE)
    ngx_regex_init();
#endif

    ngx_pid = ngx_getpid();
    ngx_parent = ngx_getppid();

    log = ngx_log_init(ngx_prefix, ngx_error_log);
    if (log == NULL) {
        return 1;
    }

    /* STUB */
#if (NGX_OPENSSL)
    ngx_ssl_init(log);
#endif

    /*
     * init_cycle->log is required for signal handlers and
     * ngx_process_options()
     */

    ngx_memzero(&init_cycle, sizeof(ngx_cycle_t));
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>auto/configure</code> 探測 OS 能力並產生 <code>objs/ngx_auto_config.h</code>、<code>objs/Makefile</code> 等 build artifacts。</p></div><div class="source-step"><span>2</span><p><code>--with-debug</code> 讓 <code>NGX_DEBUG</code> 區塊與 debug log 可用；設定檔仍需把 <code>error_log</code> level 設為 <code>debug</code>。</p></div><div class="source-step"><span>3</span><p><code>nginx -t</code> 只驗證設定；<code>-T</code> 還會輸出 include 後的完整設定，是排查設定來源的重要工具。</p></div><div class="source-step"><span>4</span><p>用前景模式與獨立 prefix 運行，避免干擾系統既有 NGINX。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>從 log 字串反查 source，確認訊息是在進入還是離開狀態時記錄。</p></div><div class="microscope-card"><span>2</span><p>同時保存 build flags；條件編譯會改變可見路徑。</p></div><div class="microscope-card"><span>3</span><p>用 GDB 看 struct、用 strace 看 syscall，不要要求單一工具回答所有層。</p></div><div class="microscope-card"><span>4</span><p>觀測程式碼也可能阻塞或 allocation；測一次有無 instrumentation 的差異。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- `--with-debug` 是 compile-time；`error_log ... debug` 是 runtime，兩者不可混為一談。
- GDB 適合停在狀態轉換點，不適合從 `main` 每行單步。
- strace 只能看 syscall，不能直接證明 phase handler 的語意。
- 保存 `nginx -V`；相同 tag 因 build options 不同會走不同條件編譯。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```bash
./auto/configure \
  --prefix=/tmp/nginx-lab \
  --with-debug \
  --with-cc-opt='-O0 -g3'
make -j4

./objs/nginx -p /tmp/nginx-lab -c conf/nginx.conf -t
./objs/nginx -p /tmp/nginx-lab -c conf/nginx.conf

strace -ff -p WORKER_PID \
  -e trace=network,epoll_wait,read,write,writev,sendfile
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`auto/configure#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/auto/configure#L1) · [`src/core/nginx.c#L200`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/nginx.c#L200) · [`src/core/ngx_log.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_log.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

建議使用獨立 prefix，例如 `/tmp/nginx-lab`，讓 config、logs、pid、temporary files 都在可丟棄目錄。編譯時保留 debug symbol 並關閉過度最佳化，GDB 才容易對應源碼。

觀察時先建立事件時間線：client 發出請求、accept、read、parse、upstream connect、write、read、client write。debug log 很細，不應從頭讀到尾；用 connection number、request URI 與關鍵函式訊息縮小範圍。

`strace -ff` 要跟隨 fork 出來的 worker；`-e trace=network,epoll_wait,read,write` 可降低雜訊。GDB 則可以在 `ngx_event_accept`、`ngx_http_process_request_line`、`ngx_http_upstream_connect` 下 conditional breakpoint。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Scientific method</h3><p>提出假設、設計最小實驗、蒐集證據、修正模型。</p></div><div class="pattern-card"><h3>Observability by correlation</h3><p>用同一 request ID 串起 client、NGINX 與 backend。</p></div><div class="pattern-card"><h3>Controlled environment</h3><p>先消除多 worker、複雜 config 與不穩定 dependency。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 以固定 tag 編譯，保存 `nginx -V` 輸出，確認 configure arguments。
2. 設定單 worker、非 daemon、debug error log，發出一次帶唯一 header 的 curl。
3. 用 `rg 'http process request line' src` 找 log 來源，再把 runtime log 對回源碼。
4. 用 strace 驗證 `epoll_wait`、`accept4`、`recvfrom`、`writev/sendfile` 的實際順序。

## 常見誤解與失敗模式

- 只開 `--with-debug` 卻未把 `error_log` 設為 debug，結果看不到細節。
- 在有多個 worker 時直接讀混合 log，誤把兩條請求拼成同一條。
- 用 debugger 單步每一行，破壞 timing 且迷失在 utility；應在狀態轉換點設 breakpoint。

## 可以帶走的 Coding／CS 能力

- 建立可重現的 debugging harness。
- 分辨 source-level、process-level、syscall-level 三種證據。
- 用最小實驗控制變因，而不是在完整 production config 猜測。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

有了證據環境後，下一章才談如何在大型 C codebase 中選擇閱讀切口。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. `--with-debug` 與 `error_log ... debug` 各做什麼？</summary>

前者在編譯期保留 debug instrumentation；後者在執行期允許輸出 debug level。只做其中一個都可能看不到預期訊息。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為何初學時建議 `worker_processes 1`？</summary>

它讓一條 log timeline 不受多程序交錯與 accept 分配影響。理解完成後必須再用多 worker 驗證 shared memory、accept 與 reload。

</details>

<details class="qa" markdown="1">
<summary>Q3. `rg` 和 GDB 應如何搭配？</summary>

先用 `rg` 找定義、呼叫點與 log 字串，再在少數狀態轉換函式設 breakpoint。直接從 `main` 單步通常成本極高。

</details>

<details class="qa" markdown="1">
<summary>Q4. strace 能證明 phase engine 執行了哪個 handler 嗎？</summary>

不能直接證明；它看 syscall 邊界，不知道 C 函式語意。phase handler 需靠 debug log、breakpoint 或 instrumentation，syscall 則用 strace 交叉驗證。

</details>

<details class="qa" markdown="1">
<summary>Q5. 為何要保存 `nginx -V`？</summary>

相同版本因 configure feature、編譯器與 library 不同，實際包含的模組和條件編譯路徑會不同。`-V` 是實驗可重現性的 build manifest。

</details>

<details class="qa" markdown="1">
<summary>Q6. 怎麼避免自己加的 log 造成錯誤結論？</summary>

只在狀態轉換點記錄 connection number、event flags、handler 名稱與 return code；避免大量同步 I/O，並用原生 debug log 或 debugger 再驗證一次。

</details>

---

# 第 3 章　如何閱讀一個陌生的 C 專案

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Codebase 與 call graph</h3><div class="foundation-block"><span>白話定義</span><p>Codebase 是一個專案的完整程式集合；call graph 是『誰可能呼叫誰』的關係圖。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>不要從第一個檔案一路讀；先從 <code>proxy_pass</code> 找到 handler，再沿呼叫與 callback 關係追蹤。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 call graph 除了直接 function call，也包含 function pointer assignment 與 module registration。</p></div></section><section class="foundation-card"><h3>Function pointer</h3><div class="foundation-block"><span>白話定義</span><p>C 可以把函式位址存進變數或 struct 欄位，之後再透過該欄位呼叫。它常用來模擬 interface 或 method。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>event.handler = read_request</code> 表示未來 event ready 時要呼叫 <code>read_request</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 function pointers 注入 event handler、module hook、filter 與 upstream protocol callback。</p></div></section><section class="foundation-card"><h3>Module（模組）</h3><div class="foundation-block"><span>白話定義</span><p>一組遵守固定介面的功能程式碼，可以註冊設定指令、request handler、filter 或 lifecycle hook。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Proxy、gzip、access control 都是不同 modules，但共同掛在 NGINX core 提供的擴充點。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Core 負責協調生命週期；module 專注自己的 configuration 與 request 行為。</p></div></section><section class="foundation-card"><h3>Callback（回呼函式）</h3><div class="foundation-block"><span>白話定義</span><p>現在先把『未來某件事發生時要做什麼』存成函式；事件發生後，由框架呼叫它。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Socket 現在沒有資料時不等待；先記住 <code>on_readable</code>，有資料可讀時再執行。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_event_t.handler</code> 保存下一次 read、write 或 timer event 到來時要執行的函式。</p></div></section></div>



<p class="chapter-question">面對數十萬行 C code，怎麼決定現在該讀什麼、可以先不讀什麼？</p>

<div class="chapter-meta"><span>難度：入門</span><span>source map · call graph · data flow</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

學會用問題、邊界、物件與狀態建立 source map，而不是從檔案清單開始背。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node active"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-02-建立可觀察的-nginx-實驗室"><span>上一站</span><strong>02. 建立可觀察的 NGINX 實驗室</strong></a><div class="position-card current"><span>你在這裡</span><strong>03. 如何閱讀一個陌生的 C 專案</strong></div><a class="position-card" href="#chapter-04-讀-nginx-所需的最小-c-語言"><span>下一站</span><strong>04. 讀 NGINX 所需的最小 C 語言</strong></a></div>

本章位於 **Part 1：先看到請求真的動起來**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

NGINX 沒有單一 class hierarchy 或完整架構文件替你導航；控制流散在 struct、function pointer、module table 與初始化順序裡。本章教的是在陌生 codebase 中建立地圖，而不是背檔名。

Use case 是追「`/api` 如何到 backend」這種可驗證問題。若從目錄第一個檔案依序通讀，你會花大量時間理解與問題無關的平台 abstraction，卻仍不知道 request 的主線。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>NGINX 沒有單一 class hierarchy 或完整架構文件替你導航；控制流散在 struct、function pointer、module table 與初始化順序裡。本章教的是在陌生 codebase 中建立地圖，而不是背檔名。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是追「<code>/api</code> 如何到 backend」這種可驗證問題。若從目錄第一個檔案依序通讀，你會花大量時間理解與問題無關的平台 abstraction，卻仍不知道 request 的主線。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「問題驅動的 source slice」這個責任邊界；接收 一個可觀察行為或 bug，交付 入口、狀態物件、callback 與出口形成的最小地圖。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 object cards 與 callback cards 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 靜態 call graph 會漏掉 function pointer、module dispatch 與 runtime branch。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>問題驅動的 source slice</p></div><div class="contract-card"><span>接收什麼</span><p>一個可觀察行為或 bug</p></div><div class="contract-card"><span>產生什麼</span><p>入口、狀態物件、callback 與出口形成的最小地圖</p></div><div class="contract-card"><span>狀態由誰保存</span><p>object cards 與 callback cards</p></div><div class="contract-card"><span>主要失敗出口</span><p>靜態 call graph 會漏掉 function pointer、module dispatch 與 runtime branch</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>定義一個 user-visible 問題</p></div><div class="flow-step"><span>2</span><p>找資料進入與離開邊界</p></div><div class="flow-step"><span>3</span><p>列出跨 callback 存活的 struct</p></div><div class="flow-step"><span>4</span><p>搜尋 handler 被賦值的位置</p></div><div class="flow-step"><span>5</span><p>只追與問題相交的 branch</p></div><div class="flow-step"><span>6</span><p>用 runtime trace 驗證</p></div><div class="flow-step"><span>7</span><p>做一個小修改檢查理解</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
問題：「/api 怎麼到 backend？」
  │
  ├─ 邊界：client socket / upstream socket
  ├─ 物件：connection / request / upstream
  ├─ 狀態：waiting / parsing / connecting / forwarding
  └─ callback：下一次 ready 時執行誰？

只展開與問題相交的節點；其餘先折疊。
```

## 從零建立心智模型

大型 C 專案沒有 class hierarchy 幫你導航，真正的架構散落在 struct、function pointer、module table、macro 與初始化順序裡。有效的讀法是先找「資料進來的邊界」和「可見結果出去的邊界」，再找中間承載狀態的物件。

每次閱讀維護兩張小表。第一張是 object card：誰建立、誰持有、何時銷毀、重要狀態欄位。第二張是 callback card：誰把 handler 設成誰、什麼事件觸發、handler 可能返回什麼、返回後狀態留在哪裡。

Call graph 只表示可能呼叫，不能表示 runtime 一定走過。Function pointer、條件編譯、模組註冊與 event callback 都會讓靜態圖不完整；所以源碼搜尋必須和一次真實 trace 配對。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

從 `main()` 逐行展開所有 helper 會形成無限樹。問題驅動閱讀只保留與目標行為相交的節點，並特別追蹤 callback 的賦值點與跨等待存活的 object。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>graph edge</td><td>直接 call、function pointer assignment 或 module registration</td></tr><tr><td>path</td><td>一條 user-visible vertical slice</td></tr><tr><td>goal</td><td>可觀察出口，例如 upstream connect 或 response write</td></tr><tr><td>frontier</td><td>尚未確認是否與問題相關的 symbols</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_request.c`，官方 `release-1.31.5` 第 211–254 行

```c
ngx_http_init_connection(ngx_connection_t *c)
{
    ngx_uint_t                 i;
    ngx_event_t               *rev;
    struct sockaddr_in        *sin;
    ngx_http_port_t           *port;
    ngx_http_in_addr_t        *addr;
    ngx_http_log_ctx_t        *ctx;
    ngx_http_connection_t     *hc;
    ngx_http_core_srv_conf_t  *cscf;
#if (NGX_HAVE_INET6)
    struct sockaddr_in6       *sin6;
    ngx_http_in6_addr_t       *addr6;
#endif

    hc = ngx_pcalloc(c->pool, sizeof(ngx_http_connection_t));
    if (hc == NULL) {
        ngx_http_close_connection(c);
        return;
    }

    c->data = hc;

    /* find the server configuration for the address:port */

    port = c->listening->servers;

    if (port->naddrs > 1) {

        /*
         * there are several addresses on this port and one of them
         * is an "*:port" wildcard so getsockname() in ngx_http_server_addr()
         * is required to determine a server address
         */

        if (ngx_connection_local_sockaddr(c, NULL, 0) != NGX_OK) {
            ngx_http_close_connection(c);
            return;
        }

        switch (c->local_sockaddr->sa_family) {

#if (NGX_HAVE_INET6)
        case AF_INET6:
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>從 user-visible 行為選一條 slice，例如 reverse proxy，而不是先讀 <code>src/core</code> 全部。</p></div><div class="source-step"><span>2</span><p>找入口與出口：accept/read 是輸入邊界，upstream connect/send 是另一側邊界。</p></div><div class="source-step"><span>3</span><p>列出跨 callback 存活的 struct；區域變數不會跨 event，物件欄位才是狀態。</p></div><div class="source-step"><span>4</span><p>搜尋 handler 被賦值的位置，比只搜尋 handler 被呼叫的位置更能理解狀態機。</p></div><div class="source-step"><span>5</span><p>遇到 helper 先讀 contract、return code 與 side effect；只有阻塞理解時才進入實作。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>搜尋 <code>handler =</code> 找動態邊，再搜尋 handler definition。</p></div><div class="microscope-card"><span>2</span><p>每碰到 struct 就記 owner、建立者、cleanup 與跨哪些 callback 存活。</p></div><div class="microscope-card"><span>3</span><p>Helper 先只記 contract；阻塞主線時才往內展開。</p></div><div class="microscope-card"><span>4</span><p>最後用 debug trace 刪掉實際沒有走過的靜態候選路徑。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 搜尋 `handler =`、`NGX_AGAIN`、`ngx_pcalloc(...pool)` 往往比只搜尋函式名稱有效。
- Macro 先辨認類型與 side effect；不是每個 macro 都需要展開。
- 同名概念可能分 core、event、HTTP module 三層，先確認目前 abstraction level。
- Call graph 表示『可能』，debug trace 才表示『這次真的』。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```text
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/nginx.c#L200`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/nginx.c#L200) · [`src/core/ngx_connection.h#L127`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_connection.h#L127) · [`src/event/ngx_event.h#L30`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.h#L30)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

對 NGINX 特別有用的搜尋模式包括：搜尋 `handler =` 找 callback 切換；搜尋 `NGX_AGAIN` 找可暫停邊界；搜尋 `ngx_pcalloc(r->pool` 找 request-lifetime state；搜尋 module symbol 找 command table 與 lifecycle hooks。

不要把每個 macro 都展開。先把 macro 分為四類：型別/常數、平台抽象、container 取回、module/config 取回。知道它在做哪類工作，通常足以繼續主線。

讀懂的驗收不是「我看過這個函式」，而是能預測改變一個條件後控制流在哪裡分叉。例如 client 分兩次送 header、backend connect 超時、response 比 proxy buffer 大，下一個 callback 與 timer 會如何改變。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Vertical slice</h3><p>沿一條端到端行為切穿多層，而不是一次讀完單一資料夾。</p></div><div class="pattern-card"><h3>Object lifetime map</h3><p>以建立者、owner、cleanup 與存活時間理解 struct。</p></div><div class="pattern-card"><h3>Dynamic dispatch tracing</h3><p>function pointer 的賦值點常比呼叫點更重要。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 選 `ngx_http_process_request_line`，找它的定義、誰把 read handler 指向它、它把 handler 改成什麼。
2. 為 `ngx_http_request_t` 製作 object card，只記十個最能解釋主線的欄位。
3. 找出 upstream read/write event 共用入口以及第二層 dispatch 欄位。
4. 預測 backend 延遲回 header 時 request 保存在哪裡，再用 GDB 驗證。

## 常見誤解與失敗模式

- 把『讀過很多檔案』當成進度，卻無法描述一條完整行為。
- 只畫函式呼叫、不畫 handler 賦值與物件生命週期。
- 看到 utility 就向下鑽到底，忘記原始問題。

## 可以帶走的 Coding／CS 能力

- 在任何 callback-heavy codebase 找到實際狀態機。
- 使用 object ownership 分析 memory leak 與 use-after-free。
- 把 source reading 轉成可證偽的預測。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

下一章補上閱讀這些 struct、pointer 與 callback 所需的最小 C 語言。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼搜尋 `handler =` 很重要？</summary>

event-driven control flow 的下一跳常透過 function pointer 保存。只看 `handler(ev)` 的共同入口看不出真正狀態；賦值點才說明何時切換階段。

</details>

<details class="qa" markdown="1">
<summary>Q2. Object card 最少要記哪些內容？</summary>

建立者、擁有者、銷毀點、生命週期、重要狀態、對其他物件的指標。這些足以回答 ownership 與跨 callback 狀態問題。

</details>

<details class="qa" markdown="1">
<summary>Q3. 靜態 call graph 為何不等於 runtime trace？</summary>

條件分支、function pointer、模組註冊、平台編譯選項和資料狀態都會改變實際路徑。Call graph 是可能集合，trace 是一次具體執行。

</details>

<details class="qa" markdown="1">
<summary>Q4. 遇到不懂的 macro，何時必須展開？</summary>

當它影響 ownership、控制流、型別安全或副作用時必須展開；若只是取得 module config 或平台名稱封裝，可先理解 contract。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如何防止閱讀範圍無限擴張？</summary>

每次 session 寫一個可回答的問題和停止條件，例如『能說明 connect 未完成後誰重新喚醒』；答案完成就先停，把新問題放 backlog。

</details>

<details class="qa" markdown="1">
<summary>Q6. 什麼證據表示你已讀懂某段非同步流程？</summary>

你能指出每個 suspend point、保存狀態的欄位、重新進入的 handler，以及 timeout/close 時的清理路徑，並能用一次 trace 驗證。

</details>

---

# 第 4 章　讀 NGINX 所需的最小 C 語言

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Pointer（指標）</h3><div class="foundation-block"><span>白話定義</span><p>Pointer 保存另一塊記憶體的位址。<code>p-&gt;field</code> 表示到 <code>p</code> 指向的 object 取出 <code>field</code>。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>函式收到 <code>ngx_http_request_t *r</code>，並不是複製整個 request，而是取得它的位置。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>讀 NGINX 時要同時追 pointer 指向誰、object 由誰擁有，以及 object 何時失效。</p></div></section><section class="foundation-card"><h3>Function pointer</h3><div class="foundation-block"><span>白話定義</span><p>C 可以把函式位址存進變數或 struct 欄位，之後再透過該欄位呼叫。它常用來模擬 interface 或 method。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>event.handler = read_request</code> 表示未來 event ready 時要呼叫 <code>read_request</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 function pointers 注入 event handler、module hook、filter 與 upstream protocol callback。</p></div></section><section class="foundation-card"><h3>Macro（巨集）</h3><div class="foundation-block"><span>白話定義</span><p>C preprocessor 在編譯前做文字展開。Macro 看起來像函式或常數，但可能沒有型別檢查，也可能多次使用參數。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>ngx_string(&quot;ok&quot;)</code> 會展開成一個帶長度與 data pointer 的初始化值。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 macros 減少平台差異與重複樣板；讀 source 時必要時先看展開後的概念。</p></div></section><section class="foundation-card"><h3>Intrusive container</h3><div class="foundation-block"><span>白話定義</span><p>資料結構的 link node 直接嵌在業務 object 裡，而不是另外配置 wrapper node。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Timer object 內含 rbtree node；已知 node 位址後，可計算回原本的 timer/event object。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>這能減少 allocation 與 pointer chasing，但要求讀者理解 container-of 與 object lifetime。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section></div>



<p class="chapter-question">不先學完整 C，最少要懂哪些語法與記憶體概念才能沿主線前進？</p>

<div class="chapter-meta"><span>難度：入門</span><span>pointer · function pointer · intrusive structure</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

讀懂 pointer、struct、function pointer、macro、intrusive container 與 NGINX return-code 慣例。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node active"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-03-如何閱讀一個陌生的-c-專案"><span>上一站</span><strong>03. 如何閱讀一個陌生的 C 專案</strong></a><div class="position-card current"><span>你在這裡</span><strong>04. 讀 NGINX 所需的最小 C 語言</strong></div><a class="position-card" href="#chapter-05-從-main-到可服務的程序"><span>下一站</span><strong>05. 從 main() 到可服務的程序</strong></a></div>

本章位於 **Part 1：先看到請求真的動起來**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

讀 NGINX 不需要先修完一本 C 語言教科書，但必須能辨認 pointer、function pointer、macro、intrusive container 與手動 lifetime。這些語法不是裝飾，它們就是 NGINX 的物件模型與 polymorphism。

Use case 是看懂 `ev->handler(ev)` 為何能在不同階段做不同事，以及 `ngx_queue_data` 如何從嵌入節點找回外層物件。若把 function pointer 當普通函式、把 intrusive node 當獨立 allocation，就會誤讀 ownership。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>讀 NGINX 不需要先修完一本 C 語言教科書，但必須能辨認 pointer、function pointer、macro、intrusive container 與手動 lifetime。這些語法不是裝飾，它們就是 NGINX 的物件模型與 polymorphism。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是看懂 <code>ev-&gt;handler(ev)</code> 為何能在不同階段做不同事，以及 <code>ngx_queue_data</code> 如何從嵌入節點找回外層物件。若把 function pointer 當普通函式、把 intrusive node 當獨立 allocation，就會誤讀 ownership。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「NGINX 使用的 C object model」這個責任邊界；接收 struct pointer、callback、macro 與 embedded node，交付 可追蹤的 dispatch、container 與 lifetime。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 pool／owner struct；編譯器不自動管理 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 dangling pointer、錯誤 cast、macro 重複求值、生命週期不匹配。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>NGINX 使用的 C object model</p></div><div class="contract-card"><span>接收什麼</span><p>struct pointer、callback、macro 與 embedded node</p></div><div class="contract-card"><span>產生什麼</span><p>可追蹤的 dispatch、container 與 lifetime</p></div><div class="contract-card"><span>狀態由誰保存</span><p>pool／owner struct；編譯器不自動管理</p></div><div class="contract-card"><span>主要失敗出口</span><p>dangling pointer、錯誤 cast、macro 重複求值、生命週期不匹配</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>辨認 pointer 指向哪種物件</p></div><div class="flow-step"><span>2</span><p>找 callback typedef 與賦值點</p></div><div class="flow-step"><span>3</span><p>把 macro 展開成概念操作</p></div><div class="flow-step"><span>4</span><p>看 intrusive node 嵌在哪個 owner</p></div><div class="flow-step"><span>5</span><p>確認 allocation 使用哪個 pool</p></div><div class="flow-step"><span>6</span><p>沿 return code 判斷 caller contract</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
ngx_event_t *ev
      │ ev->data
      ▼
ngx_connection_t *c
      │ c->data
      ▼
protocol state (ngx_http_request_t / ngx_http_connection_t)

function pointer:
ev->handler ───────────────> ngx_http_process_request_line(ev)
```

## 從零建立心智模型

C pointer 不是神祕地址，而是「到另一個物件的連結」。讀主線時優先理解指標關係，不必先做位元運算題。`ev->data` 常指回 connection，`c->data` 則依階段指向 HTTP connection 或 request；這種 generic pointer 讓底層 event layer 不需要知道上層協定型別。

`ngx_str_t` 是 length＋data，而不是以 `\0` 結尾為核心的字串。這使 substring 可以只引用既有 buffer，但也表示不能隨便交給期待 C string 的 API。`ngx_array_t`、`ngx_list_t`、`ngx_queue_t` 也各自反映 workload，而不是 STL 式統一容器。

Function pointer 是 NGINX 模組化與狀態機的骨架。讀到 `rev->handler(rev)` 時不要問「handler 是哪個函式」一次就結束；要往前找當前階段最後一次賦值。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Python class 已把 method dispatch 與 ownership 隱藏起來；C 必須用 struct、function pointer 與明確 owner 表達。先用 Python 寫出同一模型，再看 NGINX 的 C 寫法就不會把 callback 當魔法。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Event</code> dataclass</td><td><code>struct ngx_event_s</code></td></tr><tr><td><code>handler: Handler</code></td><td><code>ngx_event_handler_pt handler</code> function pointer</td></tr><tr><td><code>data: Any</code></td><td><code>void *data</code>，動態型別由 contract 決定</td></tr><tr><td>替換 <code>event.handler</code></td><td>HTTP 狀態轉換時安裝下一個 callback</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/event/ngx_event.h`，官方 `release-1.31.5` 第 30–75 行

```c
struct ngx_event_s {
    void            *data;

    unsigned         write:1;

    unsigned         accept:1;

    /* used to detect the stale events in kqueue and epoll */
    unsigned         instance:1;

    /*
     * the event was passed or would be passed to a kernel;
     * in aio mode - operation was posted.
     */
    unsigned         active:1;

    unsigned         disabled:1;

    /* the ready event; in aio mode 0 means that no operation can be posted */
    unsigned         ready:1;

    unsigned         oneshot:1;

    /* aio operation is complete */
    unsigned         complete:1;

    unsigned         eof:1;
    unsigned         error:1;

    unsigned         timedout:1;
    unsigned         timer_set:1;

    unsigned         delayed:1;

    unsigned         deferred_accept:1;

    /* the pending eof reported by kqueue, epoll or in aio chain operation */
    unsigned         pending_eof:1;

    unsigned         posted:1;

    unsigned         closed:1;

    /* to test on worker exit */
    unsigned         channel:1;
    unsigned         resolver:1;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_core.h</code> 聚合核心型別與平台抽象；先認得 typedef，不必展開所有 include。</p></div><div class="source-step"><span>2</span><p><code>ngx_str_t</code>、buffer 的 <code>pos/last/start/end</code> 都是 pointer range，區間通常採半開 <code>[pos,last)</code>。</p></div><div class="source-step"><span>3</span><p><code>ngx_queue_data()</code> 類 macro 用 embedded link 的位址反推出外層 struct，形成 intrusive container。</p></div><div class="source-step"><span>4</span><p><code>NGX_OK/ERROR/AGAIN/DONE/DECLINED</code> 是控制協定；相同值在不同 API 的精確 contract 仍需看 caller。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先讀 callback typedef，再看欄位與所有 assignment sites。</p></div><div class="microscope-card"><span>2</span><p>遇到 <code>void *</code> 不要猜；由註冊該 callback 的 code 決定型別。</p></div><div class="microscope-card"><span>3</span><p>Macro 取回外層 object 時，畫出 embedded node 與 owner 的 memory layout。</p></div><div class="microscope-card"><span>4</span><p>確認資料配置於哪個 pool，因為 C 不會自動延長 lifetime。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- `data` 常是 `void *`，真正型別由 callback contract 決定。
- Bit fields 與 flags 常共同構成狀態，不要只看單一 enum。
- Container macro 可能做 pointer arithmetic；先理解 owner/node 關係。
- 局部變數不能跨 event 存活；跨等待狀態必須進 heap/pool object。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_core.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_core.h#L1) · [`src/core/ngx_string.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_string.h#L1) · [`src/core/ngx_queue.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_queue.h#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Intrusive data structure 把 link node 直接放在業務 struct 內，免去額外 wrapper allocation，也讓同一物件可嵌入多個不同 queue/tree。代價是 container macro、ownership 與 removal discipline 更難。

`ngx_pcalloc(pool, sizeof(T))` 同時配置與清零，常讓零值代表預設狀態；若新增欄位卻不是零值安全，就必須顯式初始化。理解這點可以解釋大量「為什麼沒有逐欄位初始化」。

Macro 不提供型別檢查與單步體驗。讀 macro 時先人工代入一次，確認參數是否被多次求值、是否做 pointer arithmetic、是否只是一個 cast；之後把它當具名概念。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Manual vtable</h3><p>function pointers 與 module tables 提供 C 版 dynamic dispatch。</p></div><div class="pattern-card"><h3>Intrusive container</h3><p>節點嵌在 owner 內，減少 allocation 並支援多重索引。</p></div><div class="pattern-card"><h3>Region ownership</h3><p>物件由 pool 的整體 lifetime 管理，而非逐一 free。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 畫出 `ngx_event_t → ngx_connection_t → ngx_http_request_t` 的 cast 與指標方向。
2. 找一處 `ngx_queue_data`，手動用 `offsetof` 推導外層物件地址。
3. 找三個返回 `NGX_AGAIN` 的 API，比較 caller 下一步是否完全相同。
4. 用小 C 程式建立 length-prefixed string，故意傳給 `%s`，理解其風險。

## 常見誤解與失敗模式

- 把 `ngx_str_t.data` 當成永遠以 NUL 結尾。
- 看到 `void *` 就假設固定型別，忽略它可能隨 connection 階段改變。
- 只背 return code 名稱，不讀每個 API 的 ownership 與 side effect contract。

## 可以帶走的 Coding／CS 能力

- 掌握半開區間、pointer range 與零拷貝 slice。
- 理解 callback、plugin interface 和手寫多型。
- 理解 intrusive list/tree 對 allocation、cache locality 與複雜度的影響。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

具備最小語言後，Part 2 從 process 啟動開始建立 NGINX 的世界。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. `ngx_str_t` 為什麼要保存 length？</summary>

可包含 NUL、可引用非終止 substring，也不必每次掃描找結尾。代價是與傳統 C string API 互動時必須顯式控制長度。

</details>

<details class="qa" markdown="1">
<summary>Q2. `ev->data` 為什麼使用 `void *`？</summary>

event core 需要承載不同協定與事件來源，不能依賴 HTTP 型別。上層在建立 event 時約定 data 指向什麼，handler 負責按該約定 cast。

</details>

<details class="qa" markdown="1">
<summary>Q3. Intrusive queue 和一般 linked-list node wrapper 差在哪裡？</summary>

Link 嵌在業務物件內，不需額外配置與間接層；透過 offset 由 link 找回容器。它快且可控，但錯誤移除或生命週期更危險。

</details>

<details class="qa" markdown="1">
<summary>Q4. `ngx_pcalloc` 為什麼常減少初始化程式碼？</summary>

它把記憶體清零，而 NGINX 設計許多 flag、pointer、counter 的零值為安全預設。這是資料表示的設計選擇，不代表所有型別都可依賴零值。

</details>

<details class="qa" markdown="1">
<summary>Q5. Function pointer 如何實作狀態機？</summary>

同一 event 保持不變，但在不同階段把 `handler` 改指等待 request、解析 header、處理 keepalive 等函式；下次 readiness 自然進入正確狀態。

</details>

<details class="qa" markdown="1">
<summary>Q6. 遇到很長 macro 應如何閱讀？</summary>

先找輸入輸出與副作用，手動展開一個實例，標出 cast 和 pointer arithmetic；理解 contract 後再折疊，不必每次重新展開。

</details>

---
