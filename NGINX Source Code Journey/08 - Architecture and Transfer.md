---
title: "真正讀懂架構"
part: 8
source_baseline: release-1.31.5
---

# Part 8　真正讀懂架構

看見分層產生價值的時刻，也看見成熟 C 系統的歷史代價；最後把方法遷移到任何陌生系統。

# 第 46 章　為什麼 Connection Layer 不應知道 HTTP

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Layering 與 dependency direction</h3><div class="foundation-block"><span>白話定義</span><p>底層提供通用能力，上層加入特定語意；dependency 應主要由上層指向底層，而不是讓底層知道所有上層協定。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Socket layer 只回報 bytes/readiness；HTTP layer 才理解 method 與 location。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 listening handler、event callbacks 與 module hooks 反轉控制，讓 HTTP、stream、mail 共用 connection layer。</p></div></section><section class="foundation-card"><h3>Transport（傳輸層工作）</h3><div class="foundation-block"><span>白話定義</span><p>Transport 只關心 bytes 如何經由連線抵達與送出，不理解這些 bytes 代表登入、圖片或 HTTP header。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>TCP 保證有順序的 byte stream，但不保證一個 <code>send()</code> 對應另一端的一個 <code>recv()</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 connection/event layer 處理 socket 與 readiness，上層 HTTP module 才解釋語意。</p></div></section><section class="foundation-card"><h3>Protocol（協定）</h3><div class="foundation-block"><span>白話定義</span><p>通訊雙方對資料格式、順序與錯誤處理的共同規則。TCP 只提供 bytes；HTTP 再定義 request/response 語意。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同樣的 socket API 可以承載 HTTP、WebSocket、SMTP 或自訂 binary protocol。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX event layer 不理解 HTTP；HTTP/stream/mail layers 透過 callbacks 注入各自的解析與處理。</p></div></section><section class="foundation-card"><h3>Callback（回呼函式）</h3><div class="foundation-block"><span>白話定義</span><p>現在先把『未來某件事發生時要做什麼』存成函式；事件發生後，由框架呼叫它。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Socket 現在沒有資料時不等待；先記住 <code>on_readable</code>，有資料可讀時再執行。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_event_t.handler</code> 保存下一次 read、write 或 timer event 到來時要執行的函式。</p></div></section></div>



<p class="chapter-question">如果直接在connection read handler裡寫死HTTP不是更簡單嗎？分層何時真正產生價值？</p>

<div class="chapter-meta"><span>難度：架構</span><span>layering · dependency inversion · protocol independence</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

從listening callback、event abstraction與protocol data看dependency direction，再比較HTTP、Stream、Mail與QUIC。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node active"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-45-閱讀真實-bug-fix-與-code-review"><span>上一站</span><strong>45. 閱讀真實 Bug Fix 與 Code Review</strong></a><div class="position-card current"><span>你在這裡</span><strong>46. 為什麼 Connection Layer 不應知道 HTTP</strong></div><a class="position-card" href="#chapter-47-nginx-的優雅與歷史包袱"><span>下一站</span><strong>47. NGINX 的優雅與歷史包袱</strong></a></div>

本章位於 **Part 8：真正讀懂架構**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Event/connection layer 只應處理 bytes、readiness、timer 與 socket lifecycle；若它直接知道 HTTP method/location，加入 stream TCP proxy、mail protocol 或新 transport 時就必須修改底層。NGINX 以 listening handler 與 callbacks 把 protocol 注入上層。

Use case 是同一套 connection/event primitives 同時支援 HTTP、stream 與 mail。這不是為了抽象漂亮，而是讓新需求不破壞已驗證的底層。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Event/connection layer 只應處理 bytes、readiness、timer 與 socket lifecycle；若它直接知道 HTTP method/location，加入 stream TCP proxy、mail protocol 或新 transport 時就必須修改底層。NGINX 以 listening handler 與 callbacks 把 protocol 注入上層。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是同一套 connection/event primitives 同時支援 HTTP、stream 與 mail。這不是為了抽象漂亮，而是讓新需求不破壞已驗證的底層。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Protocol-independent transport layer」這個責任邊界；接收 fd readiness、generic connection、protocol callback，交付 bytes/event 服務，不解讀上層語意。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 connection/event structures；protocol state 位於上層 object 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 dependency inversion 破壞、底層 condition explosion、跨協定回歸。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Protocol-independent transport layer</p></div><div class="contract-card"><span>接收什麼</span><p>fd readiness、generic connection、protocol callback</p></div><div class="contract-card"><span>產生什麼</span><p>bytes/event 服務，不解讀上層語意</p></div><div class="contract-card"><span>狀態由誰保存</span><p>connection/event structures；protocol state 位於上層 object</p></div><div class="contract-card"><span>主要失敗出口</span><p>dependency inversion 破壞、底層 condition explosion、跨協定回歸</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>event layer accept generic connection</p></div><div class="flow-step"><span>2</span><p>listening config 提供 protocol handler</p></div><div class="flow-step"><span>3</span><p>handler 建立 HTTP/stream/mail state</p></div><div class="flow-step"><span>4</span><p>transport read/write wrappers 搬 bytes</p></div><div class="flow-step"><span>5</span><p>上層 parser 解讀 protocol</p></div><div class="flow-step"><span>6</span><p>上層替換 event callbacks</p></div><div class="flow-step"><span>7</span><p>event layer 只排程 readiness/timer</p></div><div class="flow-step"><span>8</span><p>close 時沿 owner contract cleanup</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
OS / socket
     ↓
connection + read/write events       不知道HTTP
     ↓ protocol handler callback
HTTP connection/request  |  Stream session  |  Mail session
     ↓                         ↓                    ↓
HTTP phases/upstream      TCP/UDP proxy       mail protocol

依賴方向：上層使用下層；下層只暴露callback seam。
```

## 從零建立心智模型

Core connection只知道fd、events、I/O functions、addresses、pool與generic data。Accept完成後透過listening handler交給HTTP或Stream；event backend只呼叫當前event handler。這讓底層不用include HTTP request type。

分層的價值在需求變化時顯現：新增Stream TCP/UDP proxy可重用listener、connection、event、timer、buffer、upstream peer等基礎，而不必在每個socket函式加`if HTTP else STREAM`。

抽象不是越多越好。好的邊界圍繞穩定機制：non-blocking I/O、timer、connection lifecycle；協定特有的parse、routing、header/filter留上層。若抽象洩漏大量protocol flags，層次就失效。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

若 connection layer 直接 `if protocol == HTTP`，加入 TCP stream/mail/new protocol 會讓底層充滿條件。注入 protocol handler 讓 transport 只知道 bytes/events。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>on_accept</code></td><td>generic <code>ngx_event_accept</code></td></tr><tr><td>injected handler</td><td><code>ngx_listening_t.handler</code></td></tr><tr><td><code>http_init</code></td><td><code>ngx_http_init_connection</code></td></tr><tr><td><code>stream_init</code></td><td>stream module 的 connection initialization</td></tr></tbody></table></div>

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

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Core建立listening/connection/event與OS I/O function table。</p></div><div class="source-step"><span>2</span><p>各protocol在config-time設定listening handler與servers metadata。</p></div><div class="source-step"><span>3</span><p>Accept core完成通用初始化後呼叫handler。</p></div><div class="source-step"><span>4</span><p>Protocol把<code>c-&gt;data</code>指向自己的connection/session/request state。</p></div><div class="source-step"><span>5</span><p>Protocol仍可使用共同upstream peer、buffer、pool與timer primitives。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Event core 不應解析 HTTP method/location。</p></div><div class="microscope-card"><span>2</span><p>Generic <code>c-&gt;data</code> 由 protocol contract 賦予動態型別。</p></div><div class="microscope-card"><span>3</span><p>Transport 提供 read/write/event/timer 機制，上層提供 policy。</p></div><div class="microscope-card"><span>4</span><p>新 protocol 若要求修改 event core，先檢查 extension boundary 是否放錯層。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 檢查 `listening->handler` 如何把 accepted connection 交給不同 protocol。
- Generic `c->data` 的型別會隨上層階段改變，contract 比 static type 更重要。
- 抽象不代表零成本；函式指標與 generic data 換來擴充隔離。
- 若一個新功能要求改 event core，先問是否其實應位於 protocol/module layer。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
void generic_accept(event_t *ev) {
    connection_t *c = accept_and_initialize(ev);
    c->listening->protocol_handler(c);  /* HTTP/Stream/Mail自己接手 */
}

void http_init_connection(connection_t *c) {
    c->data = create_http_connection_context(c->pool);
    c->read->handler = http_wait_request;
}
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_connection.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_connection.h#L1) · [`src/event/ngx_event.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.h#L1) · [`src/http/ngx_http_request.c#L211`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L211) · [`src/stream/ngx_stream_handler.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/stream/ngx_stream_handler.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Dependency inversion不是一定要物件導向interface；C的function pointer、opaque `void *`與module table已能實作。關鍵是ownership與contract清楚。

QUIC/HTTP/3提醒我們抽象也有邊界：QUIC以UDP承載多stream，connection/stream mapping與readiness模型不同，需要新event/quic與http/v3層；仍重用core，但不能硬套TCP一connection一stream。

判斷分層是否成功可問：加入新protocol時，哪些低層檔案需要改？若只是註冊新handler與上層module，多半邊界健康。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Layering</h3><p>下層提供機制，上層提供協定政策。</p></div><div class="pattern-card"><h3>Dependency inversion</h3><p>transport 呼叫注入的 protocol callback，而非依賴 HTTP。</p></div><div class="pattern-card"><h3>Stable waist</h3><p>connection/event API 成為多協定共用的窄介面。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 比較`ngx_http_init_connection`與`ngx_stream_init_connection`的共同輸入與不同state。
2. 列出新增一個toy protocol可直接重用的core primitives。
3. 找一個HTTP detail若被放進event core會造成的反向依賴。
4. 比較QUIC stream與TCP connection，標出舊抽象需擴充之處。

## 常見誤解與失敗模式

- 把所有共同程式都抽象，產生無語意的萬用layer。
- 用`void *`卻沒有清楚handler/type contract。
- 為新protocol在core到處加條件分支。

## 可以帶走的 Coding／CS 能力

- 辨認stable mechanism與volatile policy。
- 使用callback/opaque context實作dependency inversion。
- 以change impact評估架構邊界品質。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

分層帶來優雅，但任何長壽專案也會累積妥協；下一章學會同時看見優點與歷史包袱。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Connection layer不知道HTTP的直接證據？</summary>

核心struct只持generic data與I/O/events；HTTP由listening/event callbacks接手並將`c->data`解讀為HTTP context，core不需HTTP欄位。

</details>

<details class="qa" markdown="1">
<summary>Q2. 分層帶來哪些成本？</summary>

更多indirection、function pointer、context cast、初始化順序與debug難度；只有變化與重用需求足以時才值得。

</details>

<details class="qa" markdown="1">
<summary>Q3. 為什麼Stream能驗證這個設計？</summary>

它在相同event/connection底座上實作TCP/UDP session與proxy，底層不需改成理解HTTP headers或phases。

</details>

<details class="qa" markdown="1">
<summary>Q4. `void *` 是否代表良好抽象？</summary>

不一定。它只消除compile-time型別依賴；若lifetime/type約定不清，會變成不安全耦合。良好抽象還需contract。

</details>

<details class="qa" markdown="1">
<summary>Q5. QUIC為何不能完全套用TCP模型？</summary>

UDP、connection ID、多stream與user-space loss recovery改變transport/event語意；需要新層，但可重用pool、timer、module與HTTP上層概念。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何衡量一個layer是否放對？</summary>

看它是否以最少protocol知識提供穩定能力、新需求改動範圍、ownership是否單向、以及是否頻繁繞過/洩漏內部。

</details>

---

# 第 47 章　NGINX 的優雅與歷史包袱

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Trade-off 與 technical debt</h3><div class="foundation-block"><span>白話定義</span><p>Trade-off 是為取得某些好處而接受成本；technical debt 是早期選擇在新需求下產生的持續維護負擔。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Global module indices 在 C 中高效，但讓動態擴充與推理更困難。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>評估 NGINX 設計要區分核心 invariant、當年環境限制、相容性成本與今天可改善的部分。</p></div></section><section class="foundation-card"><h3>Backward compatibility</h3><div class="foundation-block"><span>白話定義</span><p>新版本仍維持既有設定、協定或 module 所依賴的行為，避免升級造成無預警破壞。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>看似更乾淨的 return code 改法，可能破壞第三方 module 的既有判斷。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>成熟 NGINX code review 會把 API/ABI、平台差異、舊 config 與 error behavior 納入成本。</p></div></section><section class="foundation-card"><h3>Layering 與 dependency direction</h3><div class="foundation-block"><span>白話定義</span><p>底層提供通用能力，上層加入特定語意；dependency 應主要由上層指向底層，而不是讓底層知道所有上層協定。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Socket layer 只回報 bytes/readiness；HTTP layer 才理解 method 與 location。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 listening handler、event callbacks 與 module hooks 反轉控制，讓 HTTP、stream、mail 共用 connection layer。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section></div>



<p class="chapter-question">讀懂之後，如何同時看見NGINX的優秀設計、C時代限制與不能盲目照搬的部分？</p>

<div class="chapter-meta"><span>難度：架構</span><span>tradeoff · technical debt · contextual design</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

用context而非崇拜評估event model、pool、module ABI、global state、callbacks與現代替代方案。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node active"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-46-為什麼-connection-layer-不應知道-http"><span>上一站</span><strong>46. 為什麼 Connection Layer 不應知道 HTTP</strong></a><div class="position-card current"><span>你在這裡</span><strong>47. NGINX 的優雅與歷史包袱</strong></div><a class="position-card" href="#chapter-48-將所學遷移到其他系統"><span>下一站</span><strong>48. 將所學遷移到其他系統</strong></a></div>

本章位於 **Part 8：真正讀懂架構**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

真正讀懂源碼不是從『所有設計都很漂亮』變成挑錯，而是能把設計放回當時 OS、硬體、相容性與使用情境，判斷哪些是核心 invariant、哪些是歷史成本、哪些在今天仍值得保留。

Use case 是評估 process model、global module indices、C macro、filter chaining 或 config inheritance。更現代的語言可能提供不同工具，但 trade-off 並不因此消失。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>真正讀懂源碼不是從『所有設計都很漂亮』變成挑錯，而是能把設計放回當時 OS、硬體、相容性與使用情境，判斷哪些是核心 invariant、哪些是歷史成本、哪些在今天仍值得保留。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是評估 process model、global module indices、C macro、filter chaining 或 config inheritance。更現代的語言可能提供不同工具，但 trade-off 並不因此消失。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Contextual architecture evaluation」這個責任邊界；接收 現有 design、history、workload 與新需求，交付 保留、局部重構或替換的有證據判斷。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 architectural invariants + compatibility constraints 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 以審美取代資料、忽略 migration cost、破壞成熟 failure behavior。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Contextual architecture evaluation</p></div><div class="contract-card"><span>接收什麼</span><p>現有 design、history、workload 與新需求</p></div><div class="contract-card"><span>產生什麼</span><p>保留、局部重構或替換的有證據判斷</p></div><div class="contract-card"><span>狀態由誰保存</span><p>architectural invariants + compatibility constraints</p></div><div class="contract-card"><span>主要失敗出口</span><p>以審美取代資料、忽略 migration cost、破壞成熟 failure behavior</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>先陳述原設計解決的問題</p></div><div class="flow-step"><span>2</span><p>列出當時與現在 constraints</p></div><div class="flow-step"><span>3</span><p>找出穩定 contract 與 incidental implementation</p></div><div class="flow-step"><span>4</span><p>蒐集實際 pain：bug、耦合、性能、維護成本</p></div><div class="flow-step"><span>5</span><p>提出至少兩個替代方案</p></div><div class="flow-step"><span>6</span><p>比較 migration/compatibility/failure risk</p></div><div class="flow-step"><span>7</span><p>用小實驗或 incremental refactor 驗證</p></div><div class="flow-step"><span>8</span><p>只在收益超過風險時改變</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
成功的核心約束                    長期代價
單thread event loop               blocking module風險、callback分散
pool + intrusive structures        lifetime靠discipline、工具較難
module tables + function pointers  ABI/ordering/型別安全成本
config-time預計算                  reload流程複雜
master/worker isolation            shared state與跨worker協調困難

設計好壞必須放回當時問題、語言與效能目標。
```

## 從零建立心智模型

NGINX的優雅來自一致：明確生命週期、非阻塞狀態機、config-time預計算、少量allocation、protocol/core分層。它不是因為每個函式都短，而是控制成本有共同原則。

同樣原則也產生包袱。大量global function pointers與module ordering使控制流隱性；`void *`與macros犧牲型別安全；request struct與flags隨功能成長；第三方module可在worker中阻塞整個event loop。

評估時避免兩個極端：一是看到乾淨C就照搬所有技巧；二是用現代語言標準否定歷史設計。正確問題是：這個constraint還存在嗎？現在有哪些更安全工具？替換是否破壞已驗證的hot path與生態？

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

看到 global、macro 或 C 就直接重寫，容易破壞成熟的 failure behavior。架構評估需要把原始目的、現在痛點、替代方案與 migration risk 放在同一張表。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>benefits</td><td>新 abstraction/語言可能降低的具體成本</td></tr><tr><td>compatibility risk</td><td>module ABI、config behavior、protocol edge cases</td></tr><tr><td>failure uncertainty</td><td>少見 timeout/reload/cleanup paths 是否被保留</td></tr><tr><td>incremental option</td><td>在穩定 contract 內逐步替換 implementation</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/ngx_module.h`，官方 `release-1.31.5` 第 227–274 行

```c
struct ngx_module_s {
    ngx_uint_t            ctx_index;
    ngx_uint_t            index;

    char                 *name;

    ngx_uint_t            spare0;
    ngx_uint_t            spare1;

    ngx_uint_t            version;
    const char           *signature;

    void                 *ctx;
    ngx_command_t        *commands;
    ngx_uint_t            type;

    ngx_int_t           (*init_master)(ngx_log_t *log);

    ngx_int_t           (*init_module)(ngx_cycle_t *cycle);

    ngx_int_t           (*init_process)(ngx_cycle_t *cycle);
    ngx_int_t           (*init_thread)(ngx_cycle_t *cycle);
    void                (*exit_thread)(ngx_cycle_t *cycle);
    void                (*exit_process)(ngx_cycle_t *cycle);

    void                (*exit_master)(ngx_cycle_t *cycle);

    uintptr_t             spare_hook0;
    uintptr_t             spare_hook1;
    uintptr_t             spare_hook2;
    uintptr_t             spare_hook3;
    uintptr_t             spare_hook4;
    uintptr_t             spare_hook5;
    uintptr_t             spare_hook6;
    uintptr_t             spare_hook7;
};


typedef struct {
    ngx_str_t             name;
    void               *(*create_conf)(ngx_cycle_t *cycle);
    char               *(*init_conf)(ngx_cycle_t *cycle, void *conf);
} ngx_core_module_t;


ngx_int_t ngx_preinit_modules(void);
ngx_int_t ngx_cycle_modules(ngx_cycle_t *cycle);
ngx_int_t ngx_init_modules(ngx_cycle_t *cycle);
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>選一個機制，先寫它解決的原始constraint與成功指標。</p></div><div class="source-step"><span>2</span><p>找隨時間加入的flags/hooks，辨認抽象壓力。</p></div><div class="source-step"><span>3</span><p>比較現代替代：async/await、typed trait、RAII、generational arena。</p></div><div class="source-step"><span>4</span><p>評估migration cost：module ecosystem、config compatibility、performance與operational knowledge。</p></div><div class="source-step"><span>5</span><p>提出可漸進改進，而非一次重寫所有核心。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先說清楚現有設計原本解決什麼。</p></div><div class="microscope-card"><span>2</span><p>Technical debt 必須有可觀察 symptom，不只是審美。</p></div><div class="microscope-card"><span>3</span><p>比較 rollout、rollback、operability 與 regression surface。</p></div><div class="microscope-card"><span>4</span><p>找 stable contract 與 accidental implementation 的分界。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 把『global』『macro』『C』直接當壞味道會錯過 workload 與 ABI context。
- 歷史包袱需有具體 symptom：修改擴散、bug 類型、性能或測試困難。
- 重構 async lifecycle 時最容易遺失少見 error/timeout branch。
- 比較替代方案時包含 rollout、observability 與 rollback，而非只比程式碼行數。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```text
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_core.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_core.h#L1) · [`src/core/ngx_module.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_module.h#L1) · [`src/event/ngx_event.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.h#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

重寫常低估behavioral compatibility。數十年邊界案例藏在error paths、timeouts、platform ifdefs與module expectations；「更漂亮」的新實作需重新付驗證成本。

可以局部現代化：更好的generated docs、typed wrappers、sanitizer/fuzz tests、清楚state tracing、限制blocking module、將複雜任務移thread pool。這些改善不必推翻event core。

真正學到架構是能說出「為什麼當初合理、今天哪裡痛、改動會傷到什麼、如何量化改善」。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Trade-off analysis</h3><p>每個 abstraction 同時降低一類成本並增加另一類成本。</p></div><div class="pattern-card"><h3>Evolutionary architecture</h3><p>成熟系統靠相容的小步演化，不是每次重寫。</p></div><div class="pattern-card"><h3>Chesterton&#x27;s fence</h3><p>刪改前先理解現有結構為何存在。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 挑pool、phase engine或module ABI寫一頁design review：收益、代價、替代。
2. 找一個歷史commit顯示某flag為相容性而加入。
3. 用ASan/fuzz/trace為舊設計增加安全網，再提出小重構。
4. 比較C callback與Rust async state machine的allocation/typing/debug取捨。

## 常見誤解與失敗模式

- 把成功專案的所有細節當universally best practice。
- 只批評可讀性，不量化效能、相容與運維收益。
- 提出big-bang rewrite卻沒有behavioral regression策略。

## 可以帶走的 Coding／CS 能力

- 以constraint與evidence做架構判斷。
- 辨認essential complexity與accidental complexity。
- 設計漸進式現代化與相容性安全網。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

最後一章把這些觀察抽象成能帶去 Redis、Node.js、Envoy、資料庫與 coding interview 的方法。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. NGINX最值得學的不是哪個具體API？</summary>

是一致的約束管理：把等待交event loop、把狀態放明確lifetime、把固定工作移config-time、把protocol policy放module。

</details>

<details class="qa" markdown="1">
<summary>Q2. Callback多就代表架構差嗎？</summary>

不必然。它是C中低成本continuation/plugin手段；問題在contract、typing、traceability與lifetime是否可管理。

</details>

<details class="qa" markdown="1">
<summary>Q3. 為何重寫可能比漸進修改危險？</summary>

成熟系統有大量隱含邊界與operational behavior；新系統需重新發現。除非收益可量化且有兼容/遷移計畫，風險很高。

</details>

<details class="qa" markdown="1">
<summary>Q4. 現代語言能自動解決哪些問題？</summary>

更強型別、RAII/borrow、async生成狀態機可降低部分錯誤；但backpressure、retry、timeouts、protocol ambiguity等系統問題仍需設計。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如何辨認technical debt而非必要複雜度？</summary>

看constraint是否已消失、變更是否反覆觸碰同脆弱區、bug密度與理解成本；同時驗證簡化不會失去效能/相容能力。

</details>

<details class="qa" markdown="1">
<summary>Q6. 一份好的改進提案要包含什麼？</summary>

當前invariant與痛點、數據、替代方案、compatibility、failure modes、分階段migration、rollback與benchmark/test plan。

</details>

---

# 第 48 章　將所學遷移到其他系統

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>可遷移的閱讀模型</h3><div class="foundation-block"><span>白話定義</span><p>不要只記函式名稱；用事件來源、state owner、喚醒方式、backpressure、resource ownership 與 failure policy 描述系統。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>讀 Redis 或 Envoy 時，也先問『不能前進時狀態放哪裡？誰之後叫醒它？』</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>這些問題把 NGINX 的具體實作提升成可用於其他 codebase 與 system design 的能力。</p></div></section><section class="foundation-card"><h3>State machine（狀態機）</h3><div class="foundation-block"><span>白話定義</span><p>把流程表示成有限狀態與允許的轉移。遇到等待時保存目前 state；事件到來後從該 state 繼續。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>CONNECTING → SENDING → READING_HEADER → STREAMING_BODY → DONE。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 常把 state 分散在 struct fields 與可替換 callbacks，而不是寫成一個巨大 switch。</p></div></section><section class="foundation-card"><h3>Backpressure（背壓）</h3><div class="foundation-block"><span>白話定義</span><p>下游處理不過來時，限制上游繼續產生或讀入資料，讓系統內的待處理資料有明確上限。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 每秒產生 10 MB，但手機只能收 100 KB；不能無限把差額塞進 memory。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 buffer 水位暫停 upstream read，等 client write 消耗資料後再恢復。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section><section class="foundation-card"><h3>Timeout、deadline 與 retry</h3><div class="foundation-block"><span>白話定義</span><p>Timeout 限制單一等待；deadline 限制整個操作的總時間；retry 是失敗後再嘗試另一個 peer。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>總預算 2 秒時，不能對三個 peers 各等待 2 秒。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 failure stage、method/config 與剩餘 peers 決定是否呼叫 upstream next。</p></div></section></div>



<p class="chapter-question">讀完NGINX後，如何把能力帶到Redis、Node.js、Netty、Envoy、資料庫與一般coding問題，而不是只會找NGINX函式？</p>

<div class="chapter-meta"><span>難度：架構</span><span>transfer learning · systems thinking · problem decomposition</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

把具體名稱抽象成event、state、lifetime、pipeline、scheduler與failure semantics六個可遷移模型。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node active"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-47-nginx-的優雅與歷史包袱"><span>上一站</span><strong>47. NGINX 的優雅與歷史包袱</strong></a><div class="position-card current"><span>你在這裡</span><strong>48. 將所學遷移到其他系統</strong></div><div class="position-card muted"><span>下一站</span><strong>完成全書，進入實作</strong></div></div>

本章位於 **Part 8：真正讀懂架構**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

若讀完只記得 `ngx_http_upstream_next` 在哪個檔案，能力無法遷移。真正可帶走的是六個問題：事件從哪來、誰保存跨等待狀態、誰喚醒、資料如何限流、資源由誰擁有、失敗後能否 retry/cleanup。

Use case 是第一次閱讀 Redis、libuv、Netty、Envoy、database storage engine 或陌生 interview system。具體 API 不同，但 event、state、lifetime、pipeline、scheduler 與 failure semantics 仍可比較。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>若讀完只記得 <code>ngx_http_upstream_next</code> 在哪個檔案，能力無法遷移。真正可帶走的是六個問題：事件從哪來、誰保存跨等待狀態、誰喚醒、資料如何限流、資源由誰擁有、失敗後能否 retry/cleanup。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是第一次閱讀 Redis、libuv、Netty、Envoy、database storage engine 或陌生 interview system。具體 API 不同，但 event、state、lifetime、pipeline、scheduler 與 failure semantics 仍可比較。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Transferable systems-reading method」這個責任邊界；接收 陌生 codebase + 一條 user-visible flow，交付 可驗證的 architecture/source map。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 問題清單、object/flow/failure diagrams、small experiments 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 強行套 NGINX 名詞、忽略 thread/I/O model 差異、技術選型先於 constraints。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Transferable systems-reading method</p></div><div class="contract-card"><span>接收什麼</span><p>陌生 codebase + 一條 user-visible flow</p></div><div class="contract-card"><span>產生什麼</span><p>可驗證的 architecture/source map</p></div><div class="contract-card"><span>狀態由誰保存</span><p>問題清單、object/flow/failure diagrams、small experiments</p></div><div class="contract-card"><span>主要失敗出口</span><p>強行套 NGINX 名詞、忽略 thread/I/O model 差異、技術選型先於 constraints</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>選一條可在一天內回答的 visible path</p></div><div class="flow-step"><span>2</span><p>找 ingress/egress 與 process/thread boundary</p></div><div class="flow-step"><span>3</span><p>找跨 async boundary 存活的 state object</p></div><div class="flow-step"><span>4</span><p>找 callback/wakeup/scheduler</p></div><div class="flow-step"><span>5</span><p>找 queues、buffers、watermarks 與 deadlines</p></div><div class="flow-step"><span>6</span><p>列 cancel/retry/cleanup failure matrix</p></div><div class="flow-step"><span>7</span><p>用 trace 與小修改驗證</p></div><div class="flow-step"><span>8</span><p>把具體名稱改寫成通用 pattern</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
NGINX具體概念              可遷移模型
ngx_event_t/handler         readiness + continuation
request/upstream structs    explicit async state
pool                        region/lifetime ownership
phase/filter chain          compiled middleware pipeline
peer.get/free               scheduler + feedback
timer rbtree                deadline queue
reload cycle                immutable generation + draining
buffer chain                slices + scatter/gather + backpressure
```

## 從零建立心智模型

遷移的第一步是去掉名字。例如不要只記`ngx_http_upstream_next`，而要記「一次attempt失敗後，根據idempotency、body replayability、deadline與tried set決定是否重試」。

Redis同樣以event loop推進socket與timer，但資料處理模型不同；Node/libuv把callback/async work包成更高層API；Netty用pipeline與event loop group；Envoy採typed C++ filter與cluster/connection pool。比較時先找共同mechanism，再看policy與thread model。

Coding面試也能受益：紅黑樹題不只背旋轉，而是先問是否需要ordered min與任意delete；state machine題先定義incomplete/error/complete；LRU題思考multi-index object與ownership。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

把函式名稱背熟無法遷移。對任何陌生系統，都可以用同一組問題抽取 ingress、state owner、wakeup、backpressure、failure 與 cleanup，再以小實驗驗證。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>ingress/egress</td><td>accept/read → parse → output 的 golden path</td></tr><tr><td>state owner</td><td>cycle/connection/request/upstream 的可遷移概念</td></tr><tr><td>wakeup</td><td>epoll callback、completion、actor message 或 async task</td></tr><tr><td>failure matrix</td><td>stage × error × ownership × retry semantics</td></tr></tbody></table></div>

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

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>對新系統找入口事件、核心loop與等待邊界。</p></div><div class="source-step"><span>2</span><p>列出跨等待存活的state object與owner。</p></div><div class="source-step"><span>3</span><p>找pipeline/plugin registration與return protocol。</p></div><div class="source-step"><span>4</span><p>找scheduler輸入訊號、feedback與failure policy。</p></div><div class="source-step"><span>5</span><p>找buffer/queue上限與backpressure傳播。</p></div><div class="source-step"><span>6</span><p>找reload/deploy時新舊generation如何交接。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>不要強迫新系統使用 NGINX 的 thread/process model。</p></div><div class="microscope-card"><span>2</span><p>把 container 名稱改寫成 operation set 與 constraints。</p></div><div class="microscope-card"><span>3</span><p>Mechanism 與 policy 分開比較。</p></div><div class="microscope-card"><span>4</span><p>最後必須做一個安全小修改，才能驗證自己不只理解圖。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 不要看到 event loop 就假設是單 thread；確認 thread/core/shard model。
- 不要看到 tree 就先背旋轉；先問它支援哪些 operations。
- 比較系統時把 correctness、latency、memory、operability 與 evolution 一起看。
- 最終驗收是能在陌生專案畫 flow、指出 owner/wakeup/failure，並做出一個安全小修改。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```text
read_new_system(codebase):
    path = choose_one_user_visible_flow()
    boundaries = find_io_and_process_boundaries(path)
    state = find_objects_surviving_waits(path)
    callbacks = find_wakeup_and_dispatch_points(path)
    limits = find_queues_timeouts_and_backpressure(path)
    failures = enumerate_cancel_retry_cleanup(path)
    verify_with_trace_and_small_change()
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/ngx_event.c#L195`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.c#L195) · [`src/http/ngx_http_core_module.c#L894`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_core_module.c#L894) · [`src/http/ngx_http_upstream.c#L1571`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L1571)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

不要強行套Reactor名稱。實作可能是completion-based I/O、thread-per-core、actor、async runtime；共同問題仍是誰保存state、誰喚醒、如何取消、如何限流。

面試或設計討論時，從constraint導出結構：連線數、消息大小、deadline、是否可重試、state是否共享、順序需求。這比先報出「用epoll＋紅黑樹」更有說服力。

最終能力是面對陌生系統仍能提出可驗證問題，快速建立golden path，並知道何時深入OS、算法、協定或語言。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Mechanism vs policy</h3><p>event loop/queue 是機制，routing/retry 是政策。</p></div><div class="pattern-card"><h3>Constraint-driven design</h3><p>先問 operation、scale、ordering、failure，再選結構。</p></div><div class="pattern-card"><h3>Learning loop</h3><p>問題 → source model → experiment → implementation → review。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 選Redis或Node，畫一條與本書相同格式的request/event路徑。
2. 把NGINX phase engine與一個middleware框架逐項比較。
3. 從任一coding題先寫workload/operations，再選資料結構。
4. 在新專案完成一個小功能，使用source trace＋failure matrix驗證。

## 常見誤解與失敗模式

- 只搬函式名稱與具體容器，不搬constraint reasoning。
- 看到event loop就假設thread model與NGINX相同。
- 設計題先宣布技術選型，再詢問流量與一致性需求。

## 可以帶走的 Coding／CS 能力

- 把源碼閱讀轉成通用systems investigation。
- 用constraint驅動algorithm/data structure選擇。
- 建立能從實作上升到architecture、再回到實驗的閉環。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

全書到此結束；接下來應選一個 lab 或真實小 patch，把閱讀轉成自己的實作與判斷力。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 如何判斷知識已從NGINX遷移出去？</summary>

在不同語言/系統中仍能找出event boundary、state owner、continuation、backpressure與failure semantics，而不依賴NGINX名稱。

</details>

<details class="qa" markdown="1">
<summary>Q2. Reactor是唯一高併發模型嗎？</summary>

不是。Completion I/O、async runtime、actor、thread-per-core等都可行；應比較工作負載、OS、語言與延遲需求。

</details>

<details class="qa" markdown="1">
<summary>Q3. 紅黑樹知識如何遷移到coding？</summary>

先辨認需要ordered min、dynamic insert與arbitrary delete，再比較heap/tree/wheel；場景與operation set比旋轉記憶更重要。

</details>

<details class="qa" markdown="1">
<summary>Q4. 讀新codebase第一個問題應多大？</summary>

足以穿過數個重要邊界但可在幾小時/一天回答，例如『一條消息如何進queue再ack』；不要一開始問『整個系統如何運作』。

</details>

<details class="qa" markdown="1">
<summary>Q5. 系統設計時為何先問failure semantics？</summary>

Retry、dedup、deadline、queue與state ownership都受失敗後是否知道結果影響；happy path無法決定真正架構。

</details>

<details class="qa" markdown="1">
<summary>Q6. 這本書最後的驗收是什麼？</summary>

能不看書畫出一次proxy request，解釋每個suspend/lifetime/failure；再寫一個小module並把同一分析框架用到陌生專案。

</details>

---
