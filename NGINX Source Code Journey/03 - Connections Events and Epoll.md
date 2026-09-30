---
title: "Connection、Event Loop 與 epoll"
part: 3
source_baseline: release-1.31.5
---

# Part 3　Connection、Event Loop 與 epoll

這是 NGINX 的心臟：socket readiness、callback、timer、紅黑樹與 backpressure 如何共同形成 cooperative scheduler。

# 第 10 章　Socket、File Descriptor 與 TCP 最小基礎

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Kernel space 與 user space</h3><div class="foundation-block"><span>白話定義</span><p>Kernel 是作業系統中有權管理 CPU、memory、files 與 network devices 的核心；NGINX 在限制較多的 user space 執行，必須透過 system call（程式請作業系統工作的入口）請 kernel 工作。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>網卡收到封包後先由 kernel 放入 socket buffer；NGINX 之後呼叫 <code>recv()</code> 取走 bytes。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Epoll 的 interest set 與 ready list 位於 kernel；NGINX 保存更高層的 request 與 callback state。</p></div></section><section class="foundation-card"><h3>Socket</h3><div class="foundation-block"><span>白話定義</span><p>Socket 是程式與網路連線互動的 OS object。程式用它 listen、accept、connect、read 與 write。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Listening socket 等待新客人；accepted socket 則只代表某一位 client 的 TCP connection。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 把 socket 包裝成 <code>ngx_connection_t</code>，再附加 read/write events 與 protocol state。</p></div></section><section class="foundation-card"><h3>File descriptor（fd）</h3><div class="foundation-block"><span>白話定義</span><p>Fd 是 process（正在執行的程式實例）內的一個小整數，用來引用 kernel 管理的 file、socket 或 pipe。它是索引，不是網路資料本身。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>fd = 8</code> 可能代表某條 client socket；close 後數字 8 可以被下一個 socket 重用。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 fd 做 syscall，並用 <code>ngx_connection_t</code> 補上 owner、events、log 與 generation 資訊。</p></div></section><section class="foundation-card"><h3>TCP byte stream</h3><div class="foundation-block"><span>白話定義</span><p>TCP 提供可靠、有順序的 bytes，但沒有 application message boundary。資料可以被任意拆分或合併。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Sender 一次送出 <code>GET / HTTP/1.1</code>，receiver 可能先讀到 <code>GET / HT</code>，下一次才讀到其餘部分。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX parser 必須支援 partial read，不能假設一次 <code>recv()</code> 得到完整 HTTP request。</p></div></section><section class="foundation-card"><h3>Non-blocking I/O 與 EAGAIN</h3><div class="foundation-block"><span>白話定義</span><p>Non-blocking socket 在目前不能前進時立即返回，而不是讓整個 worker 睡在 <code>read()</code> 或 <code>write()</code> 裡。EAGAIN 表示『現在沒有，之後再試』。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Client 尚未送下一段 body 時，<code>recv()</code> 回 EAGAIN；worker 去處理別的 connections。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 保存 parser/output state，等待 epoll 再次通知 readiness 後由 callback 繼續。</p></div></section></div>



<p class="chapter-question">在讀 accept、recv 與 epoll 前，哪些 OS 與 TCP 概念是不可跳過的？</p>

<div class="chapter-meta"><span>難度：初階</span><span>file descriptor · TCP · non-blocking I/O</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

用一個 server socket 與一條 client connection 建立 fd、socket、TCP、HTTP 的正確分層。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node active"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-09-graceful-reload-為什麼不會中斷連線"><span>上一站</span><strong>09. Graceful Reload 為什麼不會中斷連線</strong></a><div class="position-card current"><span>你在這裡</span><strong>10. Socket、File Descriptor 與 TCP 最小基礎</strong></div><a class="position-card" href="#chapter-11-nginx-如何接受新連線"><span>下一站</span><strong>11. NGINX 如何接受新連線</strong></a></div>

本章位於 **Part 3：Connection、Event Loop 與 epoll**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

NGINX 的 event model 最終建立在 OS socket 與 file descriptor 上。若不知道 `read()` 為何可能只讀一部分、TCP 為何沒有 message boundary、non-blocking 為何回 EAGAIN，後面的 parser 與 callback 都會像魔法。

Use case 是同一條 TCP stream 分多次抵達 request line，或 `send()` 只送出 response 的前半段。Server 必須保存 cursor，不能假設一次 syscall 完成一個語意操作。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>NGINX 的 event model 最終建立在 OS socket 與 file descriptor 上。若不知道 <code>read()</code> 為何可能只讀一部分、TCP 為何沒有 message boundary、non-blocking 為何回 EAGAIN，後面的 parser 與 callback 都會像魔法。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是同一條 TCP stream 分多次抵達 request line，或 <code>send()</code> 只送出 response 的前半段。Server 必須保存 cursor，不能假設一次 syscall 完成一個語意操作。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Non-blocking socket transport」這個責任邊界；接收 kernel socket buffers 與 fd readiness，交付 讀到／寫出零到多個 bytes。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 <code>ngx_connection_t</code> + read/write event + buffer cursors 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 EAGAIN、EOF、reset、timeout、partial I/O。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Non-blocking socket transport</p></div><div class="contract-card"><span>接收什麼</span><p>kernel socket buffers 與 fd readiness</p></div><div class="contract-card"><span>產生什麼</span><p>讀到／寫出零到多個 bytes</p></div><div class="contract-card"><span>狀態由誰保存</span><p><code>ngx_connection_t</code> + read/write event + buffer cursors</p></div><div class="contract-card"><span>主要失敗出口</span><p>EAGAIN、EOF、reset、timeout、partial I/O</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>socket/bind/listen 建立 listening endpoint</p></div><div class="flow-step"><span>2</span><p>accept 產生 connected fd</p></div><div class="flow-step"><span>3</span><p>設定 non-blocking</p></div><div class="flow-step"><span>4</span><p>readiness 後呼叫 recv/read</p></div><div class="flow-step"><span>5</span><p>處理 partial bytes 或 EAGAIN</p></div><div class="flow-step"><span>6</span><p>write readiness 後 send/writev</p></div><div class="flow-step"><span>7</span><p>EOF/error 時 cleanup fd 與 owner</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
process file table
fd 7 ──> listening socket 0.0.0.0:8080
fd 8 ──> connected socket client:53122 ↔ nginx:8080
fd 9 ──> connected socket nginx:49210 ↔ backend:9001

TCP connection ≠ HTTP request
一條 client TCP connection：request 1 → response 1 → request 2 → response 2
```

## 從零建立心智模型

File descriptor 是 process 內的小整數索引，指向 kernel 管理的 open-file/socket 狀態。Listening socket 表示一個等待連線的入口；每次成功 `accept()` 會得到新的 connected socket fd。原 listening fd 繼續存在，兩者不可混淆。

TCP 提供有序 byte stream，沒有「一次 send 對應一次 recv」的訊息邊界。`recv()` 可能只得到半個 HTTP header，也可能得到 header 加部分 body；`send()` 也可能只接受部分 bytes。HTTP parser 必須在 byte stream 上自行建立語意邊界。

Non-blocking 表示 syscall 無法立即前進時返回 `EAGAIN`，不是表示 kernel 在背景替你完成所有業務邏輯。程式需保存尚未完成的範圍，等 readiness notification 後重試。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

一次 `recv()` 不保證拿到完整 message，一次 `send()` 也不保證送完。正確模型是 byte stream 加 cursor：能處理多少就處理多少，EAGAIN 時保存位置。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>nonblocking socket</td><td>NGINX accepted/upstream fd</td></tr><tr><td><code>BlockingIOError</code></td><td><code>EAGAIN</code>／<code>NGX_AGAIN</code></td></tr><tr><td><code>buffer</code></td><td><code>ngx_buf_t</code> 的可用區間</td></tr><tr><td>loop until delimiter/EAGAIN</td><td>parser/output handler 的 bounded progress</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/os/unix/ngx_recv.c`，官方 `release-1.31.5` 第 14–57 行

```c
ngx_unix_recv(ngx_connection_t *c, u_char *buf, size_t size)
{
    ssize_t       n;
    ngx_err_t     err;
    ngx_event_t  *rev;

    rev = c->read;

#if (NGX_HAVE_KQUEUE)

    if (ngx_event_flags & NGX_USE_KQUEUE_EVENT) {
        ngx_log_debug3(NGX_LOG_DEBUG_EVENT, c->log, 0,
                       "recv: eof:%d, avail:%d, err:%d",
                       rev->pending_eof, rev->available, rev->kq_errno);

        if (rev->available == 0) {
            if (rev->pending_eof) {
                rev->ready = 0;
                rev->eof = 1;

                if (rev->kq_errno) {
                    rev->error = 1;
                    ngx_set_socket_errno(rev->kq_errno);

                    return ngx_connection_error(c, rev->kq_errno,
                               "kevent() reported about an closed connection");
                }

                return 0;

            } else {
                rev->ready = 0;
                return NGX_AGAIN;
            }
        }
    }

#endif

#if (NGX_HAVE_EPOLLRDHUP)

    if ((ngx_event_flags & NGX_USE_EPOLL_EVENT)
        && ngx_use_epoll_rdhup)
    {
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Listening sockets 在 cycle init 中建立、設定 options、bind、listen。</p></div><div class="source-step"><span>2</span><p><code>accept4(..., SOCK_NONBLOCK)</code> 直接產生 non-blocking connected socket；不支援時再用 <code>fcntl/ioctl</code> 設定。</p></div><div class="source-step"><span>3</span><p><code>ngx_connection_t</code> 把 fd、read/write events、I/O function pointers 與 protocol data 組合。</p></div><div class="source-step"><span>4</span><p><code>ngx_unix_recv()</code> 將 <code>EAGAIN</code> 翻成 <code>NGX_AGAIN</code>，將 EOF 與其他 error 寫入 event/connection 狀態。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>TCP 是 bytes，不保存 HTTP line boundary。</p></div><div class="microscope-card"><span>2</span><p>Zero bytes、EAGAIN、ECONNRESET 與 timeout 必須分開處理。</p></div><div class="microscope-card"><span>3</span><p>Fd close 後可被 reuse，舊 event 不能只靠數字判斷身分。</p></div><div class="microscope-card"><span>4</span><p>每次 partial I/O 後確認哪個 cursor 已被移動。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- fd 只是 process-local 整數索引，close 後很快可能被 reuse。
- Readiness 不等於完整 request，也不保證下一次 syscall 一定完成全部工作。
- EOF、RST 與 timeout 是不同 failure semantics。
- 連線有 client 與 upstream 兩側；方向與 owner 不能只看 fd 數字判斷。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/os/unix/ngx_socket.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_socket.c#L1) · [`src/core/ngx_connection.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_connection.c#L1) · [`src/os/unix/ngx_recv.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_recv.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Readiness 是提示「現在操作可能不阻塞」，不是承諾「能完成整個 request」。在 edge-triggered 模式，handler 通常持續 read 到 `EAGAIN` 才算把當前通知消耗乾淨；write 也要追蹤 `pos/last` 或 chain 中未送完的位置。

EOF、RST、timeout 與應用層 4xx/5xx 是不同層次的失敗。`recv()==0` 表示 peer orderly close；`ECONNRESET` 是 transport error；HTTP 502 則是 NGINX 將 upstream failure 映射為 protocol response。

一條 proxy request 通常同時涉及 client socket 與 upstream socket。兩邊速度不同，因此 buffer、backpressure、timeout 與 cleanup 必須明確屬於哪一側。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Byte stream abstraction</h3><p>TCP 保證有序 bytes，不保證 application message 邊界。</p></div><div class="pattern-card"><h3>Non-blocking contract</h3><p>syscall 只做現在能做的工作，不能做就回 EAGAIN。</p></div><div class="pattern-card"><h3>Cursor-based progress</h3><p>buffer positions 明確記錄已處理與尚未處理區間。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 用 `ss -tnlp` 找 listening socket，再發 request 找 connected socket。
2. 用一個小 client 將 request line 分三次 send，確認 NGINX 仍能 incremental parse。
3. 把 response body 設大並限制 client 讀取速度，觀察多次 write/writev。
4. 用 strace 分辨 listening fd、client fd 與 upstream fd。

## 常見誤解與失敗模式

- 把 TCP 當 message queue，假設一次 recv 得到完整 request。
- 把 fd 當全系統唯一 ID；它只在特定 process 與時間範圍內有效，close 後可重用。
- 看到 writable 就假設所有 output 都已寫完。

## 可以帶走的 Coding／CS 能力

- 理解 stream framing、partial I/O 與半開 buffer range。
- 建立 transport error、protocol error、application error 的分層。
- 理解所有 event-driven networking library 的底層 contract。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

理解 transport 後，下一章看 listening socket ready 時 NGINX 如何 accept 並建立 connection object。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Listening socket 與 accepted socket 的關係是什麼？</summary>

前者代表服務入口並持續監聽；後者代表一條具體 client TCP connection。Accept 不會把 listening fd 變成 connected fd，而是回傳新 fd。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為什麼兩次 `send()` 不一定對應兩次 `recv()`？</summary>

TCP 只保證有序 byte stream，kernel 可分段、合併與緩衝。應用協定必須靠長度、delimiter 或狀態機恢復訊息邊界。

</details>

<details class="qa" markdown="1">
<summary>Q3. Non-blocking `recv()` 回 EAGAIN 是錯誤嗎？</summary>

它是正常控制結果：目前沒有更多 bytes，應返回 event loop 並等待下一次 readable 通知，不應記成服務故障。

</details>

<details class="qa" markdown="1">
<summary>Q4. 一個 fd 為何可能產生 stale event？</summary>

fd close 後數字可很快被新 socket 重用，而舊 epoll event 可能仍在本輪結果中；NGINX 使用 connection instance bit 等機制辨認過期事件。

</details>

<details class="qa" markdown="1">
<summary>Q5. Client connection 和 upstream connection 可以共用一個 timeout 嗎？</summary>

不適合。Client header/read/write 與 upstream connect/send/read 是不同風險與 SLO，需分開 timer、錯誤映射與 log。

</details>

<details class="qa" markdown="1">
<summary>Q6. HTTP keep-alive 對 object model 有什麼要求？</summary>

Transport connection 必須可在一個 request finalize 後回到 waiting state，再建立下一個 request；request-lifetime memory 不能污染下一次交換。

</details>

---

# 第 11 章　NGINX 如何接受新連線

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>listen、accept 與 connection queue</h3><div class="foundation-block"><span>白話定義</span><p>Server 先用 listening socket 表示願意接收某個 address/port；kernel 排隊已完成握手的 connections，程式再用 <code>accept()</code> 取出其中一條。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>門口叫號系統先收集到店客人；櫃台每次叫一位進來，建立專屬服務紀錄。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 收到 listening fd readable 後 accept clients，為每條 accepted fd 配置 connection object。</p></div></section><section class="foundation-card"><h3>Socket</h3><div class="foundation-block"><span>白話定義</span><p>Socket 是程式與網路連線互動的 OS object。程式用它 listen、accept、connect、read 與 write。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Listening socket 等待新客人；accepted socket 則只代表某一位 client 的 TCP connection。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 把 socket 包裝成 <code>ngx_connection_t</code>，再附加 read/write events 與 protocol state。</p></div></section><section class="foundation-card"><h3>File descriptor（fd）</h3><div class="foundation-block"><span>白話定義</span><p>Fd 是 process（正在執行的程式實例）內的一個小整數，用來引用 kernel 管理的 file、socket 或 pipe。它是索引，不是網路資料本身。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>fd = 8</code> 可能代表某條 client socket；close 後數字 8 可以被下一個 socket 重用。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 fd 做 syscall，並用 <code>ngx_connection_t</code> 補上 owner、events、log 與 generation 資訊。</p></div></section><section class="foundation-card"><h3>Connection slot / object pool</h3><div class="foundation-block"><span>白話定義</span><p>預先準備一批可重用 object；需要時取一個，結束時清理並歸還，避免高頻 malloc/free。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>worker_connections 1024</code> 代表 worker 可管理的 connection slots 有上限，不只計算 client。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 將 read/write event objects 內嵌於 connection slot，重用時用 instance bit 辨識舊通知。</p></div></section><section class="foundation-card"><h3>Callback（回呼函式）</h3><div class="foundation-block"><span>白話定義</span><p>現在先把『未來某件事發生時要做什麼』存成函式；事件發生後，由框架呼叫它。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Socket 現在沒有資料時不等待；先記住 <code>on_readable</code>，有資料可讀時再執行。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_event_t.handler</code> 保存下一次 read、write 或 timer event 到來時要執行的函式。</p></div></section></div>



<p class="chapter-question">Listening socket readable 之後，NGINX 如何把一個 fd 變成可由 HTTP 層處理的 connection？</p>

<div class="chapter-meta"><span>難度：中階</span><span>accept · connection pool · resource exhaustion</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

逐步走過 `ngx_event_accept()`，理解 connection slot、pool、non-blocking、protocol handler 與 fd exhaustion。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node active"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-10-socket-file-descriptor-與-tcp-最小基礎"><span>上一站</span><strong>10. Socket、File Descriptor 與 TCP 最小基礎</strong></a><div class="position-card current"><span>你在這裡</span><strong>11. NGINX 如何接受新連線</strong></div><a class="position-card" href="#chapter-12-從-select-到-epoll"><span>下一站</span><strong>12. 從 select 到 epoll</strong></a></div>

本章位於 **Part 3：Connection、Event Loop 與 epoll**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Accept 是 kernel 世界進入 NGINX object 世界的邊界。這一步不只取得 fd，還要從 connection pool 取物件、建立 pool、初始化 read/write events、套用 socket options，最後交給 HTTP 或 stream protocol handler。

Use case 是瞬間大量新連線、fd/connection 不足，以及多 worker 同時競爭 listening socket。若 accept error path 漏掉任一步 cleanup，就會洩漏 fd 或留下半初始化 connection。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Accept 是 kernel 世界進入 NGINX object 世界的邊界。這一步不只取得 fd，還要從 connection pool 取物件、建立 pool、初始化 read/write events、套用 socket options，最後交給 HTTP 或 stream protocol handler。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是瞬間大量新連線、fd/connection 不足，以及多 worker 同時競爭 listening socket。若 accept error path 漏掉任一步 cleanup，就會洩漏 fd 或留下半初始化 connection。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Connection admission」這個責任邊界；接收 listening socket readable event，交付 完整初始化、交給 protocol layer 的 <code>ngx_connection_t</code>。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 connection slot + per-connection pool + read/write events 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 EMFILE/ENFILE、connection limit、accept mutex contention、client 立即關閉。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Connection admission</p></div><div class="contract-card"><span>接收什麼</span><p>listening socket readable event</p></div><div class="contract-card"><span>產生什麼</span><p>完整初始化、交給 protocol layer 的 <code>ngx_connection_t</code></p></div><div class="contract-card"><span>狀態由誰保存</span><p>connection slot + per-connection pool + read/write events</p></div><div class="contract-card"><span>主要失敗出口</span><p>EMFILE/ENFILE、connection limit、accept mutex contention、client 立即關閉</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>event backend 回報 listening fd readable</p></div><div class="flow-step"><span>2</span><p><code>ngx_event_accept</code> 反覆 accept 可取得的 clients</p></div><div class="flow-step"><span>3</span><p>取得 connection slot 並綁定 fd</p></div><div class="flow-step"><span>4</span><p>建立 connection pool 與 sockaddr metadata</p></div><div class="flow-step"><span>5</span><p>初始化 read/write event fields</p></div><div class="flow-step"><span>6</span><p>設定 non-blocking/socket options</p></div><div class="flow-step"><span>7</span><p>呼叫 listening handler，例如 HTTP init</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

Event backend 不知道 HTTP。它只知道 listening connection 的 read event ready，呼叫該 event 的 accept handler。`ngx_event_accept()` 從 kernel 取新 fd，再從預先配置的 connection free list 取得 `ngx_connection_t` 與配對 events。

每條 accepted connection 建立自己的 pool，保存 peer sockaddr、log context 與協定資料。最後呼叫 `ls->handler(c)`；HTTP 在設定 listening socket 時把 handler 指向 `ngx_http_init_connection`。這個 callback 是通用 event layer 與 protocol layer 的接縫。

若 file descriptor 耗盡，繼續 accept 只會產生錯誤風暴。程式會暫停 accept events 或設定 delay timer，讓系統有時間釋放 fd。這是 overload control，而不只是 error log。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Accept 不只是取得 fd；它是建立 connection object、events、pool 與 protocol handoff 的 admission transaction。任何中途失敗都必須逆向釋放已取得資源。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>ConnectionPool</code></td><td>預配置的 <code>ngx_connection_t</code> free list</td></tr><tr><td><code>acquire(fd)</code></td><td><code>ngx_get_connection</code></td></tr><tr><td>handler assignment</td><td>listening protocol handler 初始化 HTTP connection</td></tr><tr><td><code>release</code></td><td>close/error path 的 <code>ngx_free_connection</code></td></tr></tbody></table></div>

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

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>由 listening read event 取回 listening connection 與 <code>ngx_listening_t</code>。</p></div><div class="source-step"><span>2</span><p>在 multi-accept 模式可循環 accept，直到 <code>EAGAIN</code> 或配額結束。</p></div><div class="source-step"><span>3</span><p><code>ngx_get_connection()</code> 從 free list 取 slot，初始化 read/write event 並綁 fd。</p></div><div class="source-step"><span>4</span><p>建立 connection pool、複製 sockaddr、設定 recv/send function pointers。</p></div><div class="source-step"><span>5</span><p>註冊 event backend 後呼叫 protocol-specific listening handler。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Accepted fd 與 connection slot 是兩個資源，error path 要同時歸還。</p></div><div class="microscope-card"><span>2</span><p>Read/write events 內嵌於 connection slot，reuse 前需重設 flags/instance。</p></div><div class="microscope-card"><span>3</span><p>Connection pool 不等於 request memory pool。</p></div><div class="microscope-card"><span>4</span><p>最後一步的 <code>ls-&gt;handler(c)</code> 是 event layer 到 protocol layer 的注入點。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 先區分 listening connection 與 accepted client connection。
- 所有 accept 後失敗 branch 都要 close fd 並歸還 connection slot。
- Multi-accept、accept mutex 與 reuseport 會改變一次事件處理多少連線。
- Listening handler 是 protocol injection point；event layer 不應知道 HTTP。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/ngx_event_accept.c#L21`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event_accept.c#L21) · [`src/core/ngx_connection.c#L1068`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_connection.c#L1068) · [`src/http/ngx_http.c#L1804`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http.c#L1804)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Connection array 大小受 `worker_connections` 影響，但可代理連線數通常小於這個值，因為一個 proxy request 可能同時佔 client 與 upstream connection，還有 listening、resolver 等 fd。

NGINX 會重用 `ngx_connection_t` slot，因此 event 的 instance/generation 必須辨認舊事件。這是 object pool 常見 ABA 類問題：記憶體地址相同，不代表仍是同一代物件。

Accept fairness 取決於 epoll exclusive、reuseport、accept mutex、multi_accept 與負載。新 Linux 常有更好的 kernel wake-up 機制，但理解 accept mutex 仍能學到 thundering herd 與 work distribution。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Adapter boundary</h3><p>把 OS fd 轉成 NGINX 通用 connection/event abstraction。</p></div><div class="pattern-card"><h3>Object pool</h3><p>預先配置 connection slots，避免高頻 malloc/free。</p></div><div class="pattern-card"><h3>Admission control</h3><p>資源不足時快速停止 accept，等待可恢復條件。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 在 `ngx_event_accept` 設 breakpoint，檢查 `lc`、`ls`、新 `c` 與 read/write event。
2. 把 `worker_connections` 設得很小，建立大量 keep-alive connection，觀察告警。
3. 調整 `multi_accept`，比較一次 readiness 中 accept 次數。
4. 降低 process fd limit，觀察 `EMFILE` 後 accept 暫停與恢復。

## 常見誤解與失敗模式

- 把 `worker_connections` 當成可同時代理的 request 數。
- 忽略 connection slot 重用，將舊 event 誤派給新 fd。
- 在 fd exhaustion 時無限制重試 accept，形成 busy loop 與 log storm。

## 可以帶走的 Coding／CS 能力

- 理解 object pool、generation token 與 stale callback 防護。
- 理解 overload 時應暫停入口，而不是更激烈重試。
- 辨認 framework layer 與 protocol plugin 的 callback boundary。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Connection 建立後不會 busy-wait；下一章由 epoll 告訴 worker 哪些 fd 可以前進。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼 accepted connection 需要自己的 pool？</summary>

Sockaddr、log context、protocol state 等都和 connection 共同存亡；pool 讓 close 時可整體釋放並執行 cleanup。HTTP request 仍可另建更短生命週期 pool。

</details>

<details class="qa" markdown="1">
<summary>Q2. `worker_connections` 為何不等於最大 client 數？</summary>

Listening、upstream、resolver、cache helper 等都使用 connection/fd；reverse proxy 常每個 active request 至少用 client 與 backend 兩條 connection。

</details>

<details class="qa" markdown="1">
<summary>Q3. `ls->handler` 的架構意義是什麼？</summary>

Accept core 只完成通用 socket/connection 初始化，再由 callback 選 HTTP、Stream、Mail 等協定，避免 event layer 依賴上層。

</details>

<details class="qa" markdown="1">
<summary>Q4. 發生 EMFILE 時暫停 accept 有何作用？</summary>

避免同一 readable listener 不斷喚醒並立即失敗，降低 CPU/log 壓力，等待既有 connection 關閉釋放 fd。

</details>

<details class="qa" markdown="1">
<summary>Q5. 為什麼 object pool 需要 instance bit？</summary>

Slot 地址與 fd 數字都可能重用；舊 readiness 若晚到，必須用 generation 資訊判斷它不屬於當前 connection。

</details>

<details class="qa" markdown="1">
<summary>Q6. `multi_accept on` 一定更好嗎？</summary>

不一定。它可快速清空 accept queue，但單 worker 一次拿太多新連線可能降低其他 events 公平性；要依 connection burst 與 tail latency 實測。

</details>

---

# 第 12 章　從 select 到 epoll

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Kernel space 與 user space</h3><div class="foundation-block"><span>白話定義</span><p>Kernel 是作業系統中有權管理 CPU、memory、files 與 network devices 的核心；NGINX 在限制較多的 user space 執行，必須透過 system call（程式請作業系統工作的入口）請 kernel 工作。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>網卡收到封包後先由 kernel 放入 socket buffer；NGINX 之後呼叫 <code>recv()</code> 取走 bytes。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Epoll 的 interest set 與 ready list 位於 kernel；NGINX 保存更高層的 request 與 callback state。</p></div></section><section class="foundation-card"><h3>File descriptor（fd）</h3><div class="foundation-block"><span>白話定義</span><p>Fd 是 process（正在執行的程式實例）內的一個小整數，用來引用 kernel 管理的 file、socket 或 pipe。它是索引，不是網路資料本身。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>fd = 8</code> 可能代表某條 client socket；close 後數字 8 可以被下一個 socket 重用。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 fd 做 syscall，並用 <code>ngx_connection_t</code> 補上 owner、events、log 與 generation 資訊。</p></div></section><section class="foundation-card"><h3>Readiness（可前進狀態）</h3><div class="foundation-block"><span>白話定義</span><p>Readiness 只表示某個 I/O 操作現在『可能取得進展』，不表示完整 request 已抵達或整個 response 已送完。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Readable 可能只有 3 bytes、EOF（對方已關閉）或 error；writable 可能只能再送一小段。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Epoll 回報 readiness 後，NGINX 的 handler（回呼函式）仍要呼叫 <code>recv()</code>／<code>send()</code>；EAGAIN 表示這次已無法再前進，應回 event loop 等下次通知。</p></div></section><section class="foundation-card"><h3>select / poll 的基本模型</h3><div class="foundation-block"><span>白話定義</span><p>Application 每次等待前交出一批想觀察的 fds；返回後還要檢查哪些項目 ready。模型簡單，但大量 idle fds 時，重建與掃描成本會持續發生。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>每秒逐間敲一萬個房門問『有事嗎』，即使只有兩個房間真的需要服務。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 支援不同 event backends；在 Linux 大量 connections 的常見情況下通常選 epoll。</p></div></section><section class="foundation-card"><h3>epoll</h3><div class="foundation-block"><span>白話定義</span><p>Linux kernel 提供的 readiness 通知機制。Application 先登記關心哪些 fd/event，之後 <code>epoll_wait()</code> 主要取回目前 ready 的項目。Epoll 不讀寫資料，也不替你執行 handler。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>櫃台先留下所有房號，只有房間按服務鈴時才收到通知，不必不停敲每扇門。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 <code>epoll_ctl</code> 更新 interest set，用 <code>epoll_wait</code> 取得 ready events，再呼叫對應 <code>ngx_event_t.handler</code>（事件回呼函式）。</p></div></section><section class="foundation-card"><h3>Interest set 與 ready list</h3><div class="foundation-block"><span>白話定義</span><p>Interest set 是 application 想監看的 fd/event；ready list 是 kernel 判斷目前可前進的那個子集合。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>監看 10,000 條 connections 的 READ，但這一刻可能只有 fd 8 與 fd 91 有資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 只在確實需要時關注 write readiness，送完 pending output 後移除 interest，避免空轉。</p></div></section><section class="foundation-card"><h3>HTTP keep-alive</h3><div class="foundation-block"><span>白話定義</span><p>完成一個 HTTP request 後不立刻關閉 TCP connection，讓同一 client 之後可在同一條連線上再送 request，省下重新建立 TCP 連線的時間。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>瀏覽器用同一條 connection 先取 HTML，再依序取圖片與 API response。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX finalize 舊 request、清除 request-lifetime state，再把 connection handler 改成等待下一個 request。</p></div></section><section class="foundation-card"><h3>WebSocket</h3><div class="foundation-block"><span>白話定義</span><p>一種長時間、雙向傳訊協定。它通常先用 HTTP Upgrade 把連線切換成 WebSocket，之後 client 與 server 都能主動傳送一小段一小段的訊息；連線可能長時間沒有資料但仍保持開啟。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>聊天室不用每秒重新發 HTTP request 問『有新訊息嗎』，server 可在有訊息時直接推送。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>對 epoll 而言它仍是一條 socket；長時間 idle 正是不能逐 fd 掃描或一連線一 thread 的典型情境。</p></div></section><section class="foundation-card"><h3>Level-triggered 與 edge-triggered</h3><div class="foundation-block"><span>白話定義</span><p>Level-triggered（LT）在條件持續成立時會繼續提醒；edge-triggered（ET）主要在狀態從不可用變成可用的那一刻提醒。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>LT 像燈只要門沒關就一直亮；ET 像門鈴只在門被推開的瞬間響一次。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>ET handler 通常要持續 <code>recv()</code>／<code>send()</code> 直到 EAGAIN，否則剩餘資料可能沒有新的狀態邊緣來提醒。</p></div></section></div>

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

<p class="chapter-question">epoll 解決了什麼問題，又有哪些常見的錯誤神話？</p>

<div class="chapter-meta"><span>難度：中階</span><span>epoll · readiness · edge-triggered</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 readiness、interest set、只取回 ready subset 的模型、LT/ET 與 non-blocking contract，而不是把 epoll 當魔法加速器。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node active"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-11-nginx-如何接受新連線"><span>上一站</span><strong>11. NGINX 如何接受新連線</strong></a><div class="position-card current"><span>你在這裡</span><strong>12. 從 select 到 epoll</strong></div><a class="position-card" href="#chapter-13-ngx-event-t-與-callback-architecture"><span>下一站</span><strong>13. ngx_event_t 與 Callback Architecture</strong></a></div>

本章位於 **Part 3：Connection、Event Loop 與 epoll**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

當 worker 同時持有數萬條大多 idle 的 connection，逐一詢問每條 fd 是否 ready 會浪費時間。Epoll 在 kernel 維護 interest set，`epoll_wait` 只回報 ready subset，讓 worker 把時間花在能前進的 connection。

Use case 是大量 keep-alive、WebSocket 或慢速 clients。Epoll 解決的是等待與掃描成本，不會自動讓 slow handler 變快，也不會把 request 分配到不同 thread。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>當 worker 同時持有數萬條大多 idle 的 connection，逐一詢問每條 fd 是否 ready 會浪費時間。Epoll 在 kernel 維護 interest set，<code>epoll_wait</code> 只回報 ready subset，讓 worker 把時間花在能前進的 connection。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是大量 keep-alive、WebSocket 或慢速 clients。Epoll 解決的是等待與掃描成本，不會自動讓 slow handler 變快，也不會把 request 分配到不同 thread。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Linux readiness demultiplexer」這個責任邊界；接收 fd interest set、timer timeout，交付 本輪 ready event list。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 kernel epoll instance + NGINX event objects 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 stale fd event、EPOLLERR/HUP、錯誤的 ET drain、永久 EPOLLOUT。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Linux readiness demultiplexer</p></div><div class="contract-card"><span>接收什麼</span><p>fd interest set、timer timeout</p></div><div class="contract-card"><span>產生什麼</span><p>本輪 ready event list</p></div><div class="contract-card"><span>狀態由誰保存</span><p>kernel epoll instance + NGINX event objects</p></div><div class="contract-card"><span>主要失敗出口</span><p>stale fd event、EPOLLERR/HUP、錯誤的 ET drain、永久 EPOLLOUT</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>以 epoll_ctl 註冊 read/write interest</p></div><div class="flow-step"><span>2</span><p>event loop 計算最近 timer deadline</p></div><div class="flow-step"><span>3</span><p>呼叫 epoll_wait</p></div><div class="flow-step"><span>4</span><p>解碼 event data 與 stale-instance bit</p></div><div class="flow-step"><span>5</span><p>標記 read/write ready</p></div><div class="flow-step"><span>6</span><p>直接或 post 對應 handler</p></div><div class="flow-step"><span>7</span><p>handler 處理到 EAGAIN 後更新 interest</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
application interest set              kernel ready list
fd 8: READ  ───────────────────────┐
fd 9: WRITE ────────────────┐      │
fd10: READ                  │      │
                           ▼      ▼
epoll_wait()  ─────────> [fd9 WRITE, fd8 READ]

只回傳 ready 的 fd；handler 仍必須實際 recv/send。
```

## 從零建立心智模型

傳統 select/poll 每輪把大量 fd 描述交給 kernel，回來後 application 還要掃描集合。epoll 維護持久 interest set，`epoll_wait` 回傳本輪 ready events；優勢主要出現在大量大多數 idle 的 connection。

Readiness 不是 completion。`EPOLLIN` 表示 read 操作可能前進，handler 還是要呼叫 recv；`EPOLLOUT` 表示 send buffer 可能有空間，不表示先前整個 response 已完成。

Level-triggered 在條件持續成立時會繼續通知；edge-triggered 著重狀態邊緣，通常必須一直操作到 EAGAIN。NGINX 用 event flags 抽象不同 backend，將 ET/clear event 差異包在 event handling contract。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

每輪掃描所有 fd 在大量 idle connections 下浪費 CPU。Selector/epoll 保存 interest set，只回傳本輪 ready subset；但 handler 還是要真正讀寫並處理 partial I/O。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>DefaultSelector</code></td><td>Linux 上通常對應 epoll</td></tr><tr><td><code>register</code></td><td><code>epoll_ctl</code> 維護 interest set</td></tr><tr><td><code>select</code> result</td><td><code>epoll_wait</code> 的 ready events</td></tr><tr><td><code>data</code></td><td>epoll event data 指回 connection/instance</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/event/modules/ngx_epoll_module.c`，官方 `release-1.31.5` 第 784–831 行

```c
ngx_epoll_process_events(ngx_cycle_t *cycle, ngx_msec_t timer, ngx_uint_t flags)
{
    int                events;
    uint32_t           revents;
    ngx_int_t          instance, i;
    ngx_uint_t         level;
    ngx_err_t          err;
    ngx_event_t       *rev, *wev;
    ngx_queue_t       *queue;
    ngx_connection_t  *c;

    /* NGX_TIMER_INFINITE == INFTIM */

    ngx_log_debug1(NGX_LOG_DEBUG_EVENT, cycle->log, 0,
                   "epoll timer: %M", timer);

    events = epoll_wait(ep, event_list, (int) nevents, timer);

    err = (events == -1) ? ngx_errno : 0;

    if (flags & NGX_UPDATE_TIME || ngx_event_timer_alarm) {
        ngx_time_update();
    }

    if (err) {
        if (err == NGX_EINTR) {

            if (ngx_event_timer_alarm) {
                ngx_event_timer_alarm = 0;
                return NGX_OK;
            }

            level = NGX_LOG_INFO;

        } else {
            level = NGX_LOG_ALERT;
        }

        ngx_log_error(level, cycle->log, err, "epoll_wait() failed");
        return NGX_ERROR;
    }

    if (events == 0) {
        if (timer != NGX_TIMER_INFINITE) {
            return NGX_OK;
        }

        ngx_log_error(NGX_LOG_ALERT, cycle->log, 0,
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Epoll module 初始化 epoll fd 與 event list，設定 add/del/process function table。</p></div><div class="source-step"><span>2</span><p>Add event 使用 <code>epoll_ctl</code> 維護 fd 的 interest mask，read/write 共享同一 fd registration。</p></div><div class="source-step"><span>3</span><p><code>ngx_epoll_process_events()</code> 呼叫 <code>epoll_wait(ep, event_list, nevents, timer)</code>。</p></div><div class="source-step"><span>4</span><p>對回傳 event 檢查 instance，設定 read/write event ready，再直接呼叫或 post handler。</p></div><div class="source-step"><span>5</span><p>EPOLLERR/HUP 會轉成 read/write 都 ready，讓既有 handler 有機會處理錯誤。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Ready 不表示完整 request 或完整 write。</p></div><div class="microscope-card"><span>2</span><p>ET 模式下確認 handler 讀到 EAGAIN。</p></div><div class="microscope-card"><span>3</span><p>無 pending output 時不要持續訂閱 writable。</p></div><div class="microscope-card"><span>4</span><p>檢查 instance bit 如何丟棄 fd reuse 造成的 stale event。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Epoll 回的是 readiness，不是 I/O completion。
- Edge-triggered 模式下通常要讀／寫到 EAGAIN 才不會漏掉後續通知。
- EPOLLOUT 幾乎常成立，無 pending data 時不要長期關注。
- 檢查 ERR/HUP 如何被轉成 read/write ready，讓既有 handler 統一處理。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/modules/ngx_epoll_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/modules/ngx_epoll_module.c#L1) · [`src/event/ngx_event.c#L127`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.c#L127) · [`src/event/ngx_event.h#L433`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.h#L433)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Epoll 的 scalable 不代表 handler 可以慢。只要某 handler 在 event loop 中阻塞 100ms，該 worker 其他 ready events 都至少延遲 100ms。Epoll 降低等待與掃描成本，不能提供 CPU parallelism。

EPOLLOUT 通常幾乎一直成立，若沒有 pending output 卻長期訂閱 write event，loop 可能持續被喚醒。正確做法是只在 partial write/EAGAIN 時啟用，送完就關閉或忽略。

Stale event 檢查解決 fd reuse：event data 同時攜帶 connection pointer 與 instance bit，若 connection 已 close/reuse，舊 event 被丟棄。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Event demultiplexer</h3><p>把大量 fd 的 readiness 聚合成少量 ready callbacks。</p></div><div class="pattern-card"><h3>Generation token</h3><p>instance bit 防止 fd reuse 後舊通知打到新 connection。</p></div><div class="pattern-card"><h3>Interest management</h3><p>只有真正需要等待 writable 時才訂閱 write event。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 用 strace 觀察 idle NGINX 阻塞在 `epoll_wait`，再發 request 看返回數量。
2. 寫一個 non-blocking socket lab，故意在 ET 收到通知後只讀 1 byte，觀察剩餘資料。
3. 建立 slow-reading client，觀察何時註冊/觸發 write event。
4. 在 handler 人為 sleep，測量同 worker 另一請求的延遲。

## 常見誤解與失敗模式

- 以為 epoll 讓每個 request 在不同 thread 執行。
- 把 readiness 當完成通知，未處理 partial I/O。
- 永久關注 EPOLLOUT，造成高 CPU busy wake-up。

## 可以帶走的 Coding／CS 能力

- 理解 readiness-based I/O、interest management 與 event demultiplexing。
- 辨認 scalability bottleneck 是 fd scanning、handler CPU 還是 downstream latency。
- 理解 LT/ET 對 handler contract 的影響。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Epoll 只知道 fd；下一章看 `ngx_event_t` 如何把 readiness 連回目前應執行的業務 callback。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Epoll 相較 select 最重要的模型差異是什麼？</summary>

Interest set 持久保存在 kernel，wait 回傳 ready subset，不必每輪重傳並掃描全部 fd；但實際 I/O 與狀態管理仍由 application 完成。

</details>

<details class="qa" markdown="1">
<summary>Q2. EPOLLIN 是否保證一次 recv 得到完整 HTTP request？</summary>

不保證。它只表示目前至少可讀或有 EOF/error；TCP 分段與 buffer 大小仍可能讓 parser 多次進入。

</details>

<details class="qa" markdown="1">
<summary>Q3. Edge-triggered 為何常要求讀到 EAGAIN？</summary>

通知代表狀態由不可讀變可讀；若未排空，可能沒有新的邊緣提醒剩餘資料，導致 connection 卡住。

</details>

<details class="qa" markdown="1">
<summary>Q4. 為什麼 write event 不應永遠啟用？</summary>

多數 socket 的 send buffer 有空，因此 writable 幾乎常成立，會讓 event loop 無意義醒來；只有 pending output 送不完時才需要等待。

</details>

<details class="qa" markdown="1">
<summary>Q5. Epoll 能解決 blocking DNS/library 嗎？</summary>

不能。只要在 event handler 同步阻塞，worker 仍停住；需 async resolver、thread pool、子程序或外部服務隔離。

</details>

<details class="qa" markdown="1">
<summary>Q6. Stale event 和 ABA 問題有何關聯？</summary>

Pointer/fd 看似回到相同值，但已是新 generation。Instance token 提供額外身分，避免把舊通知作用於新物件。

</details>

---

# 第 13 章　ngx_event_t 與 Callback Architecture

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Event object</h3><div class="foundation-block"><span>白話定義</span><p>把『發生什麼事件、屬於誰、之後呼叫誰、是否有 timer』集中保存的 object。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同一條 connection 有 read event 與 write event，各自可以指向不同 callback。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_event_t</code> 用 <code>data</code> 找回 owner，用 <code>handler</code> 保存 continuation，並帶有 ready/timedout/active 等 flags。</p></div></section><section class="foundation-card"><h3>Callback（回呼函式）</h3><div class="foundation-block"><span>白話定義</span><p>現在先把『未來某件事發生時要做什麼』存成函式；事件發生後，由框架呼叫它。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Socket 現在沒有資料時不等待；先記住 <code>on_readable</code>，有資料可讀時再執行。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_event_t.handler</code> 保存下一次 read、write 或 timer event 到來時要執行的函式。</p></div></section><section class="foundation-card"><h3>State machine（狀態機）</h3><div class="foundation-block"><span>白話定義</span><p>把流程表示成有限狀態與允許的轉移。遇到等待時保存目前 state；事件到來後從該 state 繼續。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>CONNECTING → SENDING → READING_HEADER → STREAMING_BODY → DONE。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 常把 state 分散在 struct fields 與可替換 callbacks，而不是寫成一個巨大 switch。</p></div></section><section class="foundation-card"><h3>Protocol（協定）</h3><div class="foundation-block"><span>白話定義</span><p>通訊雙方對資料格式、順序與錯誤處理的共同規則。TCP 只提供 bytes；HTTP 再定義 request/response 語意。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同樣的 socket API 可以承載 HTTP、WebSocket、SMTP 或自訂 binary protocol。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX event layer 不理解 HTTP；HTTP/stream/mail layers 透過 callbacks 注入各自的解析與處理。</p></div></section><section class="foundation-card"><h3>Readiness（可前進狀態）</h3><div class="foundation-block"><span>白話定義</span><p>Readiness 只表示某個 I/O 操作現在『可能取得進展』，不表示完整 request 已抵達或整個 response 已送完。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Readable 可能只有 3 bytes、EOF（對方已關閉）或 error；writable 可能只能再送一小段。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Epoll 回報 readiness 後，NGINX 的 handler（回呼函式）仍要呼叫 <code>recv()</code>／<code>send()</code>；EAGAIN 表示這次已無法再前進，應回 event loop 等下次通知。</p></div></section></div>



<p class="chapter-question">同一條 connection 為什麼能先等待 request、再解析 header、再等待 keep-alive，而 event loop 不需知道這些階段？</p>

<div class="chapter-meta"><span>難度：中階</span><span>callback · state machine · inversion of control</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 event object、generic data pointer、handler 切換與手寫動態派發。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node active"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-12-從-select-到-epoll"><span>上一站</span><strong>12. 從 select 到 epoll</strong></a><div class="position-card current"><span>你在這裡</span><strong>13. ngx_event_t 與 Callback Architecture</strong></div><a class="position-card" href="#chapter-14-事件循環完整解剖"><span>下一站</span><strong>14. 事件循環完整解剖</strong></a></div>

本章位於 **Part 3：Connection、Event Loop 與 epoll**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

同一個 client fd 在不同時間要做不同工作：先等待 request line、再讀 headers、處理 request 後等待 keep-alive。Event loop 不應寫滿 HTTP-specific switch，因此 `ngx_event_t` 保存 handler，狀態轉換時直接替換下一個 callback。

Use case 是讓 transport 層只負責『某 fd ready』，由 request/upstream state 決定下一步。這是 NGINX C code 中最接近 object method 與 continuation 的核心抽象。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>同一個 client fd 在不同時間要做不同工作：先等待 request line、再讀 headers、處理 request 後等待 keep-alive。Event loop 不應寫滿 HTTP-specific switch，因此 <code>ngx_event_t</code> 保存 handler，狀態轉換時直接替換下一個 callback。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是讓 transport 層只負責『某 fd ready』，由 request/upstream state 決定下一步。這是 NGINX C code 中最接近 object method 與 continuation 的核心抽象。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Event callback object」這個責任邊界；接收 read/write readiness 或 timer expiration，交付 推進 owner state 一小步並安排下一次喚醒。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 <code>ngx_event_t.data</code> 指向 connection；handler 指向 continuation 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 handler 用錯、owner 已釋放、timer/event 同時觸發、遞迴重入。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Event callback object</p></div><div class="contract-card"><span>接收什麼</span><p>read/write readiness 或 timer expiration</p></div><div class="contract-card"><span>產生什麼</span><p>推進 owner state 一小步並安排下一次喚醒</p></div><div class="contract-card"><span>狀態由誰保存</span><p><code>ngx_event_t.data</code> 指向 connection；handler 指向 continuation</p></div><div class="contract-card"><span>主要失敗出口</span><p>handler 用錯、owner 已釋放、timer/event 同時觸發、遞迴重入</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>建立 connection 時配置 read/write events</p></div><div class="flow-step"><span>2</span><p>protocol layer 安裝初始 handler</p></div><div class="flow-step"><span>3</span><p>event backend 標記 ready</p></div><div class="flow-step"><span>4</span><p>event loop 呼叫 <code>ev-&gt;handler(ev)</code></p></div><div class="flow-step"><span>5</span><p>handler 由 <code>ev-&gt;data</code> 找回 connection/request</p></div><div class="flow-step"><span>6</span><p>處理 bytes 並更新 state</p></div><div class="flow-step"><span>7</span><p>若未完成，替換／保留 handler 與 timer 後返回</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
同一個 read event

accept 後       rev->handler = ngx_http_wait_request_handler
收到首批 bytes  rev->handler = ngx_http_process_request_line
request line 完 rev->handler = ngx_http_process_request_headers
request 完成後   rev->handler = ngx_http_keepalive_handler

epoll 只做：rev->ready = 1; rev->handler(rev);
```

## 從零建立心智模型

`ngx_event_t` 是「一個可能發生的 I/O/timer 工作」。它保存 `data`、`handler`、timer node 以及 ready、active、timedout、eof、error 等 flags。`ngx_connection_t` 通常有一個 read event 和一個 write event。

Event loop 不硬編碼 HTTP 狀態。上層每到新階段就替換 handler；下一次 readiness 進入新的 callback。這是 continuation 的 C 實作：call stack 消失，但下一步函式與需要的資料都保存在 heap object。

`data` 常指向 connection，handler 再由 `c->data` 取得 protocol-specific object。這兩層 indirection 讓 event core 完全不知道 HTTP request layout。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

若 event loop 內寫一個巨大 switch 判斷 HTTP 每個階段，transport 與 protocol 會耦合。把下一步存在 handler 欄位，狀態轉換就是替換 callback。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Event.owner</code></td><td><code>ev-&gt;data</code> → connection → request</td></tr><tr><td>handler field</td><td><code>ngx_event_t.handler</code></td></tr><tr><td>handler replacement</td><td>request parsing、keepalive、lingering close 等狀態切換</td></tr><tr><td>same event</td><td>同一 connection read event 在不同時間承擔不同 continuation</td></tr></tbody></table></div>

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

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Event backend 找到 ready fd，取 connection，再取 read/write event。</p></div><div class="source-step"><span>2</span><p>設定 <code>ready/eof/error</code> flags，呼叫 <code>event-&gt;handler(event)</code>。</p></div><div class="source-step"><span>3</span><p>Handler 從 <code>event-&gt;data</code> 取得 connection，從 <code>connection-&gt;data</code> 取得當前 protocol state。</p></div><div class="source-step"><span>4</span><p>若階段改變，handler 更新 function pointer；若暫停，保留 object state 後返回。</p></div><div class="source-step"><span>5</span><p>Timer 到期也設定 <code>timedout</code> 後呼叫同一 handler，使 I/O 與 timeout 共用 cleanup path。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>找 handler 的所有 assignment，依時間排序。</p></div><div class="microscope-card"><span>2</span><p>找 handler 內如何由 <code>ev-&gt;data</code> 還原 owner。</p></div><div class="microscope-card"><span>3</span><p>檢查 timer 與 I/O callback 是否可能競爭完成同一 owner。</p></div><div class="microscope-card"><span>4</span><p>Posted events 會延後 callback；靜態 call stack 看不到這條邊。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 搜尋 handler assignment 才能重建狀態轉換圖。
- `ev->data` 的動態型別由 contract 決定，常先是 connection，再從 `c->data` 找 request。
- Read event 與 write event 可同時存在 timer，注意誰先 finalize owner。
- Posted event 可能延後 callback，避免深遞迴或改善公平性。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/ngx_event.h#L30`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.h#L30) · [`src/core/ngx_connection.h#L127`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_connection.h#L127) · [`src/http/ngx_http_request.c#L211`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L211)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Event flags 是壓縮後的狀態機輸入。Handler 入口先檢查 `timedout`、`close`、`error`，再處理正常 I/O。若忘記清 timer 或 active flag，未來 callback 可能重入已 finalize 的 request。

NGINX 另有 `r->read_event_handler`、`r->write_event_handler` 與 upstream 的 read/write handlers，形成兩階 dispatch：socket event 先進共用 wrapper，再依 request/upstream 狀態分派。這讓 connection handler 保持穩定，同時細分 protocol 工作流。

這種手寫 callback 速度快、allocation 可控，但可讀性成本高。現代 async/await 編譯器本質上也把函式切成狀態機，只是由 compiler 產生 continuation frame。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Continuation</h3><p>handler 就是『未來 ready 時從哪裡繼續』。</p></div><div class="pattern-card"><h3>Inversion of control</h3><p>event loop 決定何時呼叫；protocol 決定呼叫後做什麼。</p></div><div class="pattern-card"><h3>State pattern</h3><p>透過 handler replacement 避免中央巨大 switch。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 記錄 client read handler 從 accept 到 keep-alive 的每次賦值。
2. 在 GDB 印出 `c->read->handler` 位址，用 symbol lookup 對應函式。
3. 找 upstream 共用 `ngx_http_upstream_handler` 的第二層 dispatch。
4. 故意觸發 timeout，證明同 handler 可由 timer 而非 fd readiness 叫醒。

## 常見誤解與失敗模式

- 只看 handler 定義，不找它在何種狀態下被安裝。
- 假設 `c->data` 永遠是 request；accept 初期可能是 HTTP connection context。
- Finalize 後未取消 timer/event，造成 stale callback 或 use-after-free。

## 可以帶走的 Coding／CS 能力

- 理解 callback、continuation、async state machine 的等價關係。
- 追蹤 function pointer dispatch 與狀態轉移。
- 設計 framework core 不依賴 protocol-specific 型別。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

有了 callback abstraction，下一章把 timer、accept 與 posted events 放回完整 event loop。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Event loop 如何知道下一步要解析 request line？</summary>

它不知道。HTTP 層先把 read event handler 設為對應函式；epoll 只在 readable 時呼叫目前的 function pointer。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為什麼 handler 狀態不放在 call stack？</summary>

I/O 可能等待任意時間，不能讓每條 connection 佔一個 blocking stack/thread；跨等待狀態保存在 request/connection object。

</details>

<details class="qa" markdown="1">
<summary>Q3. Timer 為何可重用 I/O handler？</summary>

Timer 到期把 `timedout` flag 設定後呼叫 event handler，入口依 flag 走 timeout path；正常 I/O 與 timeout 可共享該階段的 cleanup context。

</details>

<details class="qa" markdown="1">
<summary>Q4. 兩階 dispatch 的優點是什麼？</summary>

Socket 層可維持少數穩定入口，request/upstream 內再切換細部 continuation，降低直接改 epoll registration 與通用層耦合。

</details>

<details class="qa" markdown="1">
<summary>Q5. Callback 架構最大風險是什麼？</summary>

控制流分散、lifetime 難推理、重入與取消複雜。必須明確記錄 owner、timer、active event、reference count 與 finalize contract。

</details>

<details class="qa" markdown="1">
<summary>Q6. Async/await 與這種 C callback 有何共同點？</summary>

都在等待點保存局部狀態和下一個 program counter；async/await 由 compiler 生成 state machine，NGINX 由 struct 欄位與 function pointer 手寫。

</details>

---

# 第 14 章　事件循環完整解剖

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Event loop</h3><div class="foundation-block"><span>白話定義</span><p>單一執行流程反覆等待 events，取回 ready work，呼叫短小 handlers，然後回到等待。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>A 讀一段、B 寫一段、處理一個 timer，再回來讀 A 的下一段。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX worker event loop 協調 accept、read/write readiness、posted events 與 expired timers。</p></div></section><section class="foundation-card"><h3>Scheduler、公平性與 starvation</h3><div class="foundation-block"><span>白話定義</span><p>Scheduler 決定下一個執行誰；fairness 表示不同工作都有前進機會；starvation 是某類工作長期搶不到執行。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>若 accept handler 一次無限接新 connections，已連線 client 的 response 可能一直延遲。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 控制每輪 work、posted event 順序與 accept 策略，避免單一來源壟斷 event loop。</p></div></section><section class="foundation-card"><h3>Timer 與 deadline</h3><div class="foundation-block"><span>白話定義</span><p>Timer 表示某個時間到達後執行工作；deadline 是某件事最晚必須完成的時刻。它們讓無事件的失敗仍能被發現。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 30 秒都沒回 header，即使 socket 沒有新 event，也必須 timeout。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 將 event timer 放入有序結構，event loop 用最近 deadline 決定 <code>epoll_wait</code> 最長睡多久。</p></div></section><section class="foundation-card"><h3>Posted event</h3><div class="foundation-block"><span>白話定義</span><p>已經可以執行，但刻意放入 queue 稍後處理的 callback。這能打斷深遞迴或調整同一輪的執行順序。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Read handler 不立刻巢狀呼叫另一長串 handler，而是把它排到目前 callback 返回後。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 posted queues 協調 accept、I/O callbacks 與 request continuations。</p></div></section><section class="foundation-card"><h3>Worker process</h3><div class="foundation-block"><span>白話定義</span><p>長時間運行並實際處理 client connections 的 NGINX 子程序。每個 worker 通常有自己的 event loop。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>四核心主機可能啟動四個 workers，各自處理一批 connections。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>阻塞其中一個 worker 會延遲該 worker 管理的所有 ready events。</p></div></section></div>



<p class="chapter-question">Worker 每一輪到底按什麼順序處理 timer、accept、I/O 與 posted events？</p>

<div class="chapter-meta"><span>難度：進階</span><span>event loop · scheduling · posted events</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

逐行建立 `ngx_process_events_and_timers()` 的排程模型，理解順序如何影響公平性與鎖。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node active"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-13-ngx-event-t-與-callback-architecture"><span>上一站</span><strong>13. ngx_event_t 與 Callback Architecture</strong></a><div class="position-card current"><span>你在這裡</span><strong>14. 事件循環完整解剖</strong></div><a class="position-card" href="#chapter-15-timer-與紅黑樹"><span>下一站</span><strong>15. Timer 與紅黑樹</strong></a></div>

本章位於 **Part 3：Connection、Event Loop 與 epoll**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Event loop 是 worker 的 scheduler。它每輪決定可睡多久、向 OS 取得 ready events、更新時間、處理 accept/normal/posted events，再執行過期 timers。順序會直接影響 latency、公平性與 starvation。

Use case 是同時處理新連線、已有連線、timeout 與由 handler 延後排程的工作。若某類事件無限占用一輪，其他 connection 即使 ready 也會延遲。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Event loop 是 worker 的 scheduler。它每輪決定可睡多久、向 OS 取得 ready events、更新時間、處理 accept/normal/posted events，再執行過期 timers。順序會直接影響 latency、公平性與 starvation。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是同時處理新連線、已有連線、timeout 與由 handler 延後排程的工作。若某類事件無限占用一輪，其他 connection 即使 ready 也會延遲。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Worker scheduler loop」這個責任邊界；接收 ready fd、posted queue、timer deadlines、signals，交付 一批短 callback 的公平執行。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 event queues、timer tree、process flags 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 slow callback、事件洪水、timer starvation、遞迴 callback。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Worker scheduler loop</p></div><div class="contract-card"><span>接收什麼</span><p>ready fd、posted queue、timer deadlines、signals</p></div><div class="contract-card"><span>產生什麼</span><p>一批短 callback 的公平執行</p></div><div class="contract-card"><span>狀態由誰保存</span><p>event queues、timer tree、process flags</p></div><div class="contract-card"><span>主要失敗出口</span><p>slow callback、事件洪水、timer starvation、遞迴 callback</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>找最近 timer 計算 wait timeout</p></div><div class="flow-step"><span>2</span><p>呼叫 OS process_events</p></div><div class="flow-step"><span>3</span><p>更新 cached time</p></div><div class="flow-step"><span>4</span><p>優先處理 accept events／posted accept</p></div><div class="flow-step"><span>5</span><p>處理 normal ready callbacks</p></div><div class="flow-step"><span>6</span><p>處理 expired timers</p></div><div class="flow-step"><span>7</span><p>處理 posted events</p></div><div class="flow-step"><span>8</span><p>檢查 terminate/reconfigure 等 process flags</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

Worker 主循環每輪只呼叫 `ngx_process_events_and_timers(cycle)`。函式先取得最近 timer 到期時間，將它作為 epoll wait timeout；所以 timer tree 和 I/O wait 不是兩個 thread，而是同一 scheduler 的兩種喚醒來源。

若使用 accept mutex，worker 嘗試取得鎖。持鎖時 epoll 返回的 accept events 先 post 到專用 queue，離開 kernel wait 後優先處理，接著釋放鎖，避免持鎖執行一般 request handler。

Timers 在 accept 後、一般 posted events 前過期。Posted queue 讓 backend 可以先收集 readiness，再由一致順序執行 callbacks；也能避免深層同步遞迴，將工作延後到安全點。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Event loop 是 cooperative scheduler；它不會中斷一個慢 handler。每輪要在 ready I/O、posted work 與 expired timers 間維持順序與有限工作量。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>outer loop</td><td><code>ngx_process_events_and_timers</code> 所在 worker cycle</td></tr><tr><td><code>posted</code></td><td>NGINX posted event queues</td></tr><tr><td><code>timers[0]</code></td><td>timer rbtree 的最小 deadline</td></tr><tr><td>short callback</td><td>run-to-completion、沒有 preemption 的 handler contract</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/event/ngx_event.c`，官方 `release-1.31.5` 第 195–237 行

```c
ngx_process_events_and_timers(ngx_cycle_t *cycle)
{
    ngx_uint_t  flags;
    ngx_msec_t  timer, delta;

    if (ngx_timer_resolution) {
        timer = NGX_TIMER_INFINITE;
        flags = 0;

    } else {
        timer = ngx_event_find_timer();
        flags = NGX_UPDATE_TIME;

#if (NGX_WIN32)

        /* handle signals from master in case of network inactivity */

        if (timer == NGX_TIMER_INFINITE || timer > 500) {
            timer = 500;
        }

#endif
    }

    if (ngx_use_accept_mutex) {
        if (ngx_accept_disabled > 0) {
            ngx_accept_disabled--;

        } else {
            if (ngx_trylock_accept_mutex(cycle) == NGX_ERROR) {
                return;
            }

            if (ngx_accept_mutex_held) {
                flags |= NGX_POST_EVENTS;

            } else {
                if (timer == NGX_TIMER_INFINITE
                    || timer > ngx_accept_mutex_delay)
                {
                    timer = ngx_accept_mutex_delay;
                }
            }
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_event_find_timer()</code> 回最近 deadline 或 infinite。</p></div><div class="source-step"><span>2</span><p>Accept mutex 與 posted-next queue 可能縮短 wait timeout。</p></div><div class="source-step"><span>3</span><p><code>ngx_process_events()</code> 經 function table 進入 epoll/kqueue 等 backend。</p></div><div class="source-step"><span>4</span><p>先處理 posted accept events，必要時 release accept mutex。</p></div><div class="source-step"><span>5</span><p><code>ngx_event_expire_timers()</code> 逐個觸發已到期 timer。</p></div><div class="source-step"><span>6</span><p>最後 drain ordinary posted events。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先看 loop 每輪的處理順序，再看每個 helper。</p></div><div class="microscope-card"><span>2</span><p>任何 synchronous DNS/file/library call 都可能凍結 worker。</p></div><div class="microscope-card"><span>3</span><p>Timer timeout 會成為 OS wait 的最大睡眠時間。</p></div><div class="microscope-card"><span>4</span><p>Accept events、normal events、posted events 的優先順序影響公平性。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Event loop 沒有 preemption；任何 blocking call 都會凍結該 worker。
- Cached time 降低頻繁 syscall，但要注意何時更新。
- Accept events 與 normal events 的處理順序可能受 flags/config 影響。
- Loop 本身很短；真正複雜度分散在 handlers 與狀態物件。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
while (!exiting) {
    timeout = nearest_timer_deadline();
    maybe_acquire_accept_right();

    backend_wait(timeout);          /* epoll_wait */

    run(posted_accept_events);
    release_accept_right();
    run(expired_timers);
    run(posted_events);
}
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/ngx_event.c#L195`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.c#L195) · [`src/event/ngx_event_posted.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event_posted.c#L1) · [`src/event/modules/ngx_epoll_module.c#L812`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/modules/ngx_epoll_module.c#L812)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Event loop latency 可以分成 wait latency、queueing latency 與 handler service time。即使 epoll 立即回傳，前面某個 handler 很慢，後面的 ready event 仍排隊。這就是為何 tail latency 與 callback budget 重要。

Posted-next queue 可保證事件至少延到下一輪，避免同一輪不斷 self-post 造成 starvation。這是 cooperative scheduler 的 yield 概念。

排序不是普遍真理，而是具體取捨：accept 太優先可能餓死既有連線；只處理既有連線又可能讓 accept queue overflow。NGINX 透過 queue、mutex、multi_accept、timer 與 event backend flags 平衡。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Run-to-completion task</h3><p>每個 handler 在單 worker 上跑完才輪到下一個。</p></div><div class="pattern-card"><h3>Cooperative scheduling</h3><p>公平性依賴每個 handler 主動保持短小。</p></div><div class="pattern-card"><h3>Deferred work queue</h3><p>posted events 把立即遞迴改成稍後排程。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 在四個階段加低成本 trace id，驗證一次 loop 的真實順序。
2. 建立大量新連線加一批既有慢 response，比較 accept 與 ordinary event 延遲。
3. 找出一個使用 posted event 避免直接遞迴的路徑。
4. 量測單一 handler sleep 10ms 對同 worker p99 的影響。

## 常見誤解與失敗模式

- 把 event loop 想成公平 preemptive scheduler；handler 不會被自動搶占。
- 認為 timer 有獨立 thread 精準觸發；實際精度受 loop latency 影響。
- 在 callback 中無界迴圈處理資料，造成其他 events starvation。

## 可以帶走的 Coding／CS 能力

- 理解 cooperative scheduling、run queue 與 callback budget。
- 拆解 tail latency 的 queueing component。
- 設計 event/timer 統一 scheduler 與安全 deferred work。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Event loop 必須知道下一個 timeout；下一章看 timer 為何由紅黑樹管理。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Epoll timeout 為何取最近 timer？</summary>

若沒有 I/O，kernel wait 最多睡到下一個 deadline；若 I/O 提前發生則先回來處理。這把兩種喚醒來源合併。

</details>

<details class="qa" markdown="1">
<summary>Q2. Posted event 與直接呼叫 handler 有何差異？</summary>

Post 只入 queue，延後到明確 scheduler 階段執行，可控制順序、避免深遞迴、配合 accept mutex 或下一輪公平性。

</details>

<details class="qa" markdown="1">
<summary>Q3. Timer 到期是否會在 deadline 那一毫秒精準執行？</summary>

不保證。若 worker 正在執行長 handler，timer 只能等控制權回到 loop；deadline 是不早於的排程目標，不是 real-time guarantee。

</details>

<details class="qa" markdown="1">
<summary>Q4. 為什麼 accept event 使用獨立 posted queue？</summary>

可先處理新連線並及早釋放 accept mutex，避免持鎖執行普通 request callbacks，降低跨 worker 阻塞。

</details>

<details class="qa" markdown="1">
<summary>Q5. 什麼是 event-loop starvation？</summary>

某 callback 或不斷 repost 的工作長時間佔用 loop，其他 ready I/O/timers 無法獲得執行。解法包括有界批次、yield、thread pool 或分割工作。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何量化 handler 是否太慢？</summary>

量 event loop lag、callback duration、ready queue delay 與 p99；CPU profile 找長 hot path，並用單 worker controlled load 建立因果。

</details>

---

# 第 15 章　Timer 與紅黑樹

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Timer 與 deadline</h3><div class="foundation-block"><span>白話定義</span><p>Timer 表示某個時間到達後執行工作；deadline 是某件事最晚必須完成的時刻。它們讓無事件的失敗仍能被發現。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 30 秒都沒回 header，即使 socket 沒有新 event，也必須 timeout。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 將 event timer 放入有序結構，event loop 用最近 deadline 決定 <code>epoll_wait</code> 最長睡多久。</p></div></section><section class="foundation-card"><h3>Red-black tree（紅黑樹）</h3><div class="foundation-block"><span>白話定義</span><p>一種保持大致平衡的排序樹，使查找、插入與刪除通常維持 O(log n)。重點不是旋轉公式，而是它支援的 operations。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>數萬個 timers 依 deadline 排序；需要快速找最早到期者，也要任意取消其中一個。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 將 timer node intrusive 地放進 event object，最左節點就是下一個 deadline。</p></div></section><section class="foundation-card"><h3>Intrusive container</h3><div class="foundation-block"><span>白話定義</span><p>資料結構的 link node 直接嵌在業務 object 裡，而不是另外配置 wrapper node。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Timer object 內含 rbtree node；已知 node 位址後，可計算回原本的 timer/event object。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>這能減少 allocation 與 pointer chasing，但要求讀者理解 container-of 與 object lifetime。</p></div></section><section class="foundation-card"><h3>Event loop</h3><div class="foundation-block"><span>白話定義</span><p>單一執行流程反覆等待 events，取回 ready work，呼叫短小 handlers，然後回到等待。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>A 讀一段、B 寫一段、處理一個 timer，再回來讀 A 的下一段。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX worker event loop 協調 accept、read/write readiness、posted events 與 expired timers。</p></div></section></div>



<p class="chapter-question">課本裡的紅黑樹為什麼會出現在 NGINX timer，而不是換成 heap 或排序陣列？</p>

<div class="chapter-meta"><span>難度：進階</span><span>red-black tree · timer · ordered set</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

從 timer workload 推導 ordered structure，理解最小 deadline、任意刪除、重設 timer 與 wraparound。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node active"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-14-事件循環完整解剖"><span>上一站</span><strong>14. 事件循環完整解剖</strong></a><div class="position-card current"><span>你在這裡</span><strong>15. Timer 與紅黑樹</strong></div><a class="position-card" href="#chapter-16-backpressure-與-event-loop-公平性"><span>下一站</span><strong>16. Backpressure 與 Event Loop 公平性</strong></a></div>

本章位於 **Part 3：Connection、Event Loop 與 epoll**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

每條 connection 可能有 read timeout、write timeout、keep-alive timeout；worker 需要快速知道『最近哪個 deadline』，也要能在事件完成時取消任意 timer。這組操作不是單純 FIFO，所以 NGINX 使用按到期時間排序的紅黑樹。

Use case 是數萬條 timer 動態新增、刪除與找最小值。Heap 找最小也快，但任意刪除需要額外 index；紅黑樹配合 intrusive node 讓 event 自己攜帶可刪除節點。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>每條 connection 可能有 read timeout、write timeout、keep-alive timeout；worker 需要快速知道『最近哪個 deadline』，也要能在事件完成時取消任意 timer。這組操作不是單純 FIFO，所以 NGINX 使用按到期時間排序的紅黑樹。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是數萬條 timer 動態新增、刪除與找最小值。Heap 找最小也快，但任意刪除需要額外 index；紅黑樹配合 intrusive node 讓 event 自己攜帶可刪除節點。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Deadline index」這個責任邊界；接收 event + absolute expiration time，交付 最近 timeout 與所有已過期 events。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 timer rbtree；node 嵌在 <code>ngx_event_t</code> 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 時間 wrap、重複更新、expired callback 釋放 owner。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Deadline index</p></div><div class="contract-card"><span>接收什麼</span><p>event + absolute expiration time</p></div><div class="contract-card"><span>產生什麼</span><p>最近 timeout 與所有已過期 events</p></div><div class="contract-card"><span>狀態由誰保存</span><p>timer rbtree；node 嵌在 <code>ngx_event_t</code></p></div><div class="contract-card"><span>主要失敗出口</span><p>時間 wrap、重複更新、expired callback 釋放 owner</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>handler 為 event 計算 absolute deadline</p></div><div class="flow-step"><span>2</span><p>將 event timer node 插入 rbtree</p></div><div class="flow-step"><span>3</span><p>event loop 讀最小 key 決定 epoll timeout</p></div><div class="flow-step"><span>4</span><p>I/O 先完成時刪除 timer</p></div><div class="flow-step"><span>5</span><p>deadline 到時依序移除 expired nodes</p></div><div class="flow-step"><span>6</span><p>標記 timedout 並呼叫 event handler</p></div><div class="flow-step"><span>7</span><p>handler 決定 retry、finalize 或 close</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

Timer scheduler 的核心操作是：加入 deadline、取消任意 event 的 timer、找最小 deadline、依序取出所有已到期項目。紅黑樹提供 O(log n) 插入/刪除，最左節點給最小值；event 內嵌 node，取消時不需額外 map 找 heap index。

NGINX timer tree 允許 duplicate keys，因為主要需求只是找 minimum，不要求 deadline 唯一。到期時從最左開始，若 deadline 已過就刪除、標記 `timedout`、呼叫 handler；遇到第一個未到期便停止。

時間比較用 signed difference 處理 millisecond counter wraparound。直接比較 unsigned `a < b` 在 counter 回繞附近會錯；理解這點比背旋轉四種 case 更接近 production engineering。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

只用 list 保存 timers，找最近 deadline 或取消任意 event 會變慢。Python 用 heap 示範 ordered deadline；NGINX 因需要 intrusive arbitrary deletion，選擇紅黑樹。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>heap minimum</td><td>NGINX timer rbtree 最左節點</td></tr><tr><td>event id</td><td><code>ngx_event_t</code> 內嵌的 <code>timer</code> node</td></tr><tr><td>cancel set</td><td>NGINX 可直接 <code>ngx_rbtree_delete</code>，不需 lazy tombstone</td></tr><tr><td>deadline</td><td><code>ngx_msec_t</code> absolute timer key</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/event/ngx_event_timer.c`，官方 `release-1.31.5` 第 54–98 行

```c
ngx_event_expire_timers(void)
{
    ngx_event_t        *ev;
    ngx_rbtree_node_t  *node, *root, *sentinel;

    sentinel = ngx_event_timer_rbtree.sentinel;

    for ( ;; ) {
        root = ngx_event_timer_rbtree.root;

        if (root == sentinel) {
            return;
        }

        node = ngx_rbtree_min(root, sentinel);

        /* node->key > ngx_current_msec */

        if ((ngx_msec_int_t) (node->key - ngx_current_msec) > 0) {
            return;
        }

        ev = ngx_rbtree_data(node, ngx_event_t, timer);

        ngx_log_debug2(NGX_LOG_DEBUG_EVENT, ev->log, 0,
                       "event timer del: %d: %M",
                       ngx_event_ident(ev->data), ev->timer.key);

        ngx_rbtree_delete(&ngx_event_timer_rbtree, &ev->timer);

#if (NGX_DEBUG)
        ev->timer.left = NULL;
        ev->timer.right = NULL;
        ev->timer.parent = NULL;
#endif

        ev->timer_set = 0;

        ev->timedout = 1;

        ev->handler(ev);
    }
}


```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>全域 timer rbtree 以 timer-specific insert function 初始化。</p></div><div class="source-step"><span>2</span><p><code>ngx_add_timer</code> 設 node key、插入 tree、標記 <code>timer_set</code>。</p></div><div class="source-step"><span>3</span><p><code>ngx_event_find_timer</code> 取最左 node，計算 deadline-current time。</p></div><div class="source-step"><span>4</span><p><code>ngx_event_expire_timers</code> 反覆取 minimum，處理所有到期 events。</p></div><div class="source-step"><span>5</span><p>取消或重設 timer 時依 embedded node O(log n) 刪除。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>列出 operation set：min、insert、arbitrary delete，再理解為何不是只用 heap。</p></div><div class="microscope-card"><span>2</span><p>Timer node 內嵌於 event，不能同時重複插入。</p></div><div class="microscope-card"><span>3</span><p>I/O 完成時要取消 timer 並清 <code>timer_set</code>。</p></div><div class="microscope-card"><span>4</span><p>時間差比較要能處理整數 wraparound。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 不要從『紅黑樹很高級』倒推需求；先列出 operation set。
- Timer handler 與 I/O handler 常是同一函式，透過 `timedout` flag 分支。
- 刪除 timer 後要同步清 `timer_set` invariant。
- 到期時間比較需考慮整數 wraparound，不能只用普通大於小於直覺。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/ngx_event_timer.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event_timer.c#L1) · [`src/event/ngx_event_timer.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event_timer.h#L1) · [`src/core/ngx_rbtree.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_rbtree.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

為何不是 binary heap？Heap 找 min 與插入很好，但取消任意 event 需要知道其 heap index並在 swap 時維護；紅黑樹 node 直接嵌入 event，pointer 即刪除位置。兩者都可行，選擇取決於 cancellation frequency 與既有 infrastructure。

為何不是 timer wheel？Wheel 對大量近似精度 timer 可達 O(1) amortized，但有 bucket resolution、遠期 timer 與實作複雜度。NGINX 的 ordered tree 簡單、通用且 deadline 精度直觀。

`timer_set` 是 ownership flag：同一 embedded node 不能同時插入兩次。重設 timer 前必須刪舊節點，否則 tree 結構損壞。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Ordered set by deadline</h3><p>operation set 是 min、insert、arbitrary delete。</p></div><div class="pattern-card"><h3>Intrusive node</h3><p>event 直接嵌 timer node，無額外 wrapper allocation。</p></div><div class="pattern-card"><h3>Lazy scheduler wake-up</h3><p>最近 deadline 直接成為 epoll_wait timeout。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 建立三個不同 timeout 的連線，觀察 timer tree minimum 變化。
2. 找一條收到 I/O 後刪 timer 的路徑，確認不會之後再 timeout。
3. 用小程式比較 heap 取消任意 timer 所需 metadata。
4. 模擬 32-bit millisecond counter wraparound，比較 unsigned 與 signed-difference 判斷。

## 常見誤解與失敗模式

- 只從 Big-O 選結構，忽略任意取消與 embedded node。
- 重設 timer 不先刪除舊 node。
- 把 timeout 當精準執行時間，忽略 event loop lag。

## 可以帶走的 Coding／CS 能力

- 從 workload 推導資料結構，而不是由題型反推場景。
- 理解 intrusive tree、container_of 與 cancellation metadata。
- 處理 monotonic counter wraparound 與 deadline arithmetic。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Timer 解決 deadline，但資料速度不匹配仍會塞住；下一章處理 backpressure 與公平性。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. NGINX timer tree 最常需要哪些操作？</summary>

插入 deadline、取消已知 event、找最小 deadline、逐一彈出到期節點。紅黑樹讓前三者都維持對數或常數取得 minimum。

</details>

<details class="qa" markdown="1">
<summary>Q2. Duplicate deadline 為什麼沒問題？</summary>

Scheduler 不要求 key 唯一，只要所有相同 deadline 都位於可遍歷的有序位置；expire 會一直取 minimum 直到未到期。

</details>

<details class="qa" markdown="1">
<summary>Q3. Heap 為何不是明顯更好的答案？</summary>

Heap 也可行，但任意 cancellation 需要 index handle 且 swap 時更新。Embedded rb node 讓 event pointer 本身就是可刪除 handle。

</details>

<details class="qa" markdown="1">
<summary>Q4. Timer wheel 可能在哪種 workload 更好？</summary>

數量極大、timeout 範圍可分 bucket、允許固定解析度且頻繁增刪時；代價是遠期 timer、精度與 bucket 管理更複雜。

</details>

<details class="qa" markdown="1">
<summary>Q5. 為何 deadline 比較要使用差值 cast？</summary>

有限位寬 counter 會回繞；在兩時間相距不超過半個範圍的前提下，signed difference 可正確判斷前後，直接 unsigned 比較會在 wrap 點失敗。

</details>

<details class="qa" markdown="1">
<summary>Q6. Timer handler 執行前為何先把 node 刪除並清 flag？</summary>

Handler 可能重新加 timer或 finalize object；先解除舊 ownership 可避免 double insert/delete 與重入時看見錯誤狀態。

</details>

---

# 第 16 章　Backpressure 與 Event Loop 公平性

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Producer、consumer 與水位</h3><div class="foundation-block"><span>白話定義</span><p>Producer 產生資料，consumer 消耗資料。High/low watermark 是何時暫停與恢復 producer 的容量門檻。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Upstream 是 response producer，慢速 client 是 consumer。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Event pipe 追蹤 free/busy buffers 與 downstream write 結果，形成 bounded pipeline。</p></div></section><section class="foundation-card"><h3>Backpressure（背壓）</h3><div class="foundation-block"><span>白話定義</span><p>下游處理不過來時，限制上游繼續產生或讀入資料，讓系統內的待處理資料有明確上限。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 每秒產生 10 MB，但手機只能收 100 KB；不能無限把差額塞進 memory。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 buffer 水位暫停 upstream read，等 client write 消耗資料後再恢復。</p></div></section><section class="foundation-card"><h3>Buffering 與 streaming</h3><div class="foundation-block"><span>白話定義</span><p>Buffering 先暫存資料以吸收兩端速度差；streaming 則資料一到便逐段往下游傳，不等待完整內容。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>小 response 可留在 memory；大 response 可能落 temporary file；即時事件適合 streaming。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 module/config 在 latency、memory、disk I/O 與 backend connection 占用之間取捨。</p></div></section><section class="foundation-card"><h3>Event loop</h3><div class="foundation-block"><span>白話定義</span><p>單一執行流程反覆等待 events，取回 ready work，呼叫短小 handlers，然後回到等待。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>A 讀一段、B 寫一段、處理一個 timer，再回來讀 A 的下一段。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX worker event loop 協調 accept、read/write readiness、posted events 與 expired timers。</p></div></section></div>



<p class="chapter-question">Backend 很快、client 很慢時，NGINX 為什麼不會無限制把 response 堆進記憶體？</p>

<div class="chapter-meta"><span>難度：進階</span><span>backpressure · flow control · tail latency</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 partial write、buffer waterline、read suppression、temporary file 與 bounded work。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node active"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-15-timer-與紅黑樹"><span>上一站</span><strong>15. Timer 與紅黑樹</strong></a><div class="position-card current"><span>你在這裡</span><strong>16. Backpressure 與 Event Loop 公平性</strong></div><a class="position-card" href="#chapter-17-ngx-http-request-t-一次-http-交換的核心物件"><span>下一站</span><strong>17. ngx_http_request_t：一次 HTTP 交換的核心物件</strong></a></div>

本章位於 **Part 3：Connection、Event Loop 與 epoll**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Backend 可能很快、client 很慢；request body 也可能由 client 慢慢上傳。若 producer 不受限制地產生資料，memory、temporary files 或 socket queue 會持續膨脹。Backpressure 是讓下游容量反向限制上游速度。

Use case 是大型 download 遇到慢速行動網路、backend streaming 遇到 client 暫停讀取。沒有 high-water mark 與 event interest 切換，一個 connection 就可能耗盡 worker 記憶體或造成其他請求 tail latency。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Backend 可能很快、client 很慢；request body 也可能由 client 慢慢上傳。若 producer 不受限制地產生資料，memory、temporary files 或 socket queue 會持續膨脹。Backpressure 是讓下游容量反向限制上游速度。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是大型 download 遇到慢速行動網路、backend streaming 遇到 client 暫停讀取。沒有 high-water mark 與 event interest 切換，一個 connection 就可能耗盡 worker 記憶體或造成其他請求 tail latency。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Flow-control loop」這個責任邊界；接收 producer bytes、consumer capacity、buffer occupancy，交付 有上限且可恢復的資料流。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 buffer chains、busy/free lists、read/write event interest 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 unbounded buffering、busy loop、starvation、timeout policy 錯誤。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Flow-control loop</p></div><div class="contract-card"><span>接收什麼</span><p>producer bytes、consumer capacity、buffer occupancy</p></div><div class="contract-card"><span>產生什麼</span><p>有上限且可恢復的資料流</p></div><div class="contract-card"><span>狀態由誰保存</span><p>buffer chains、busy/free lists、read/write event interest</p></div><div class="contract-card"><span>主要失敗出口</span><p>unbounded buffering、busy loop、starvation、timeout policy 錯誤</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>從 producer 讀入有限 buffers</p></div><div class="flow-step"><span>2</span><p>把 buffers 交給 downstream output chain</p></div><div class="flow-step"><span>3</span><p>若 write partial/EAGAIN，保留 unsent cursor</p></div><div class="flow-step"><span>4</span><p>buffer 高水位時停止 producer read interest</p></div><div class="flow-step"><span>5</span><p>等待 consumer socket writable</p></div><div class="flow-step"><span>6</span><p>送出後回收 free buffers</p></div><div class="flow-step"><span>7</span><p>低於水位再恢復 producer</p></div><div class="flow-step"><span>8</span><p>deadline 到時決定中止</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
fast backend                         slow client
   │ 100 MB/s                           │ 100 KB/s
   ▼                                    ▼
[upstream read] → [memory buffers] → [client write]
       ▲                │ full             │ EAGAIN
       │                ▼                  │
       └──── pause read / spill temp file ─┘

沒有邊界：memory grows → OOM
有 backpressure：限制在途資料，讓速度差可控
```

## 從零建立心智模型

Backpressure 是下游消化不及時，向上游傳遞「先別再產生」的訊號。Non-blocking write 回 `NGX_AGAIN` 時，NGINX 保留未送完 chain，註冊 write event；是否繼續讀 upstream 取決於 buffer 空間、busy buffers、buffering 與 temporary file policy。

Buffering 可把 backend 與 client 速度解耦，提高 backend connection 釋放速度；但 memory 有上限，較大 response 可能落 temporary file。Streaming 降低首 byte latency 與磁碟使用，卻讓慢 client 長時間占用 upstream connection。

公平性也屬 backpressure。單次 callback 若無界讀寫，即使每次 syscall non-blocking，也可能長時間占據 CPU。NGINX 使用 chain limit、sendfile max chunk、posted events 等方式讓控制權回到 loop。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Producer 若不理會 consumer 速度，queue 只會變大。Bounded queue 讓 `put` 在容量滿時停止 producer；NGINX 則透過 buffer 水位與 read/write event interest 傳遞同樣訊號。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>buffer</code></td><td>out/busy/free buffer chains</td></tr><tr><td>high water</td><td>buffer/temp-file capacity policy</td></tr><tr><td>pause producer</td><td>移除/停用 upstream read interest</td></tr><tr><td>resume</td><td>client write 釋放 buffers 後重新啟用 read</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/event/ngx_event_pipe.c`，官方 `release-1.31.5` 第 104–148 行

```c
ngx_event_pipe_read_upstream(ngx_event_pipe_t *p)
{
    off_t         limit;
    ssize_t       n, size;
    ngx_int_t     rc;
    ngx_buf_t    *b;
    ngx_msec_t    delay;
    ngx_chain_t  *chain, *cl, *ln;

    if (p->upstream_eof || p->upstream_error || p->upstream_done
        || p->upstream == NULL)
    {
        return NGX_OK;
    }

#if (NGX_THREADS)

    if (p->aio) {
        ngx_log_debug0(NGX_LOG_DEBUG_EVENT, p->log, 0,
                       "pipe read upstream: aio");
        return NGX_AGAIN;
    }

    if (p->writing) {
        ngx_log_debug0(NGX_LOG_DEBUG_EVENT, p->log, 0,
                       "pipe read upstream: writing");

        rc = ngx_event_pipe_write_chain_to_temp_file(p);

        if (rc != NGX_OK) {
            return rc;
        }
    }

#endif

    ngx_log_debug1(NGX_LOG_DEBUG_EVENT, p->log, 0,
                   "pipe read upstream: %d", p->upstream->read->ready);

    for ( ;; ) {

        if (p->upstream_eof || p->upstream_error || p->upstream_done) {
            break;
        }

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Output chain 將 memory/file buffers 轉成適合 OS send/writev/sendfile 的 chain。</p></div><div class="source-step"><span>2</span><p>Write filter 累積尚未送完的 output，partial write 後保留 position。</p></div><div class="source-step"><span>3</span><p>Upstream event pipe 在 input、output、free、busy chains 間搬動 buffers。</p></div><div class="source-step"><span>4</span><p>Buffer 超過 memory policy 時可寫 temporary file；下游可再從 file buffer 送出。</p></div><div class="source-step"><span>5</span><p>Socket writable 後 writer handler 繼續先前未完成範圍。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>AGAIN 後保留 unsent cursor，不能重新產生資料。</p></div><div class="microscope-card"><span>2</span><p>Pause read 與 close upstream 是不同動作。</p></div><div class="microscope-card"><span>3</span><p>一輪處理 bytes 太多也會讓其他 ready connections starvation。</p></div><div class="microscope-card"><span>4</span><p>Buffering 將成本從 backend connection 轉移到 memory/disk，並非免費。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- `NGX_AGAIN` 後必須保留未送資料，不能重新產生或丟失 cursor。
- 停止 read interest 和關閉 connection 完全不同；前者只是暫停 producer。
- Buffering 將 backend lifetime 與 client speed 解耦，但成本轉移到 memory/disk。
- 平均 throughput 正常仍可能有 tail latency；檢查單次 handler 工作量。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_upstream.c#L3780`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L3780) · [`src/core/ngx_output_chain.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_output_chain.c#L1) · [`src/os/unix/ngx_writev_chain.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_writev_chain.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

背壓不是單一布林值，而是多層 flow control：kernel send buffer、NGINX busy buffer、proxy buffer/temp file、upstream read event、HTTP/2 window 都可能形成邊界。分析時要指出哪一層滿了、誰停止讀、誰負責重新喚醒。

取消 upstream read event 可能是 ET 模式敏感操作；framework 要維護 active/ready flags，確保恢復時不丟失通知。這也是為何 event abstraction 比直接散落 epoll_ctl 重要。

Slowloris 是反方向：client 太慢地送 request header，長期佔用 connection。Header timeout、buffer limit 與 connection limit是入口 backpressure/security。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Backpressure</h3><p>容量訊號沿 pipeline 反向傳回 producer。</p></div><div class="pattern-card"><h3>Watermarks</h3><p>高／低水位避免頻繁開關與無界成長。</p></div><div class="pattern-card"><h3>Bounded work per turn</h3><p>每輪限制 bytes/events，維持多 connection 公平。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 產生 100MB response，用 `curl --limit-rate` 建立慢 client，觀察 memory 與 temp path。
2. 切換 `proxy_buffering`，比較 upstream connection 持有時間與 client TTFB。
3. 限制 proxy buffer/temp file，觀察 read/write events 如何交替。
4. 設定小 `sendfile_max_chunk`，壓測時比較 event loop lag。

## 常見誤解與失敗模式

- 把 buffering 一律視為延遲或一律視為效能最佳；它是資源與耦合取捨。
- 只限制單 buffer 大小，未限制所有 in-flight chains。
- 在 writable callback 無界 flush，造成其他 connection starvation。

## 可以帶走的 Coding／CS 能力

- 理解 bounded queue、producer/consumer 與 backpressure propagation。
- 比較 buffering、streaming、spooling 的 latency/resource tradeoff。
- 辨認慢消費者與 retry/queue 放大造成的系統崩潰。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Connection 與事件基礎完成；Part 4 開始把收到的 bytes 提升成 HTTP request。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Partial write 後剩餘資料存在哪裡？</summary>

Buffer/chain 的 `pos` 與 busy/output lists 保存未送範圍；write event handler 在下次 writable 時從該位置繼續，而不是重送整個 response。

</details>

<details class="qa" markdown="1">
<summary>Q2. Buffering 如何幫助 fast backend？</summary>

NGINX 可較快讀完 backend response 並釋放 upstream connection，之後慢慢送 client；代價是 NGINX memory/disk 與額外 copy。

</details>

<details class="qa" markdown="1">
<summary>Q3. 關掉 proxy buffering 有什麼代價？</summary>

可降低部分 latency 與 temp file，但 backend connection 的生命週期更受慢 client 牽制，並降低吸收速度差與故障隔離能力。

</details>

<details class="qa" markdown="1">
<summary>Q4. Backpressure 為什麼不只是 memory limit？</summary>

還包括暫停 producer read、控制 syscall batch、connection/time limits、HTTP flow window 與 queue admission；limit 只是訊號，還需傳播策略。

</details>

<details class="qa" markdown="1">
<summary>Q5. Non-blocking handler 為何仍可能餓死 event loop？</summary>

它可以在 user-space loop 處理大量立即 ready 工作而不返回。Non-blocking只保證 syscall，不保證 callback 執行時間有界。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何判斷 temp file 是問題還是合理設計？</summary>

同時看 response size、client rate、memory budget、disk latency、upstream occupancy 與 SLO；spooling 可能是有意的速度解耦，也可能表示下游長期壅塞。

</details>

---
