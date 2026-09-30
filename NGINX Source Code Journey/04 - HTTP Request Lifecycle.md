---
title: "HTTP Request 的一生"
part: 4
source_baseline: release-1.31.5
---

# Part 4　HTTP Request 的一生

從 request object、incremental parser、routing 與 phase engine，走到 body、filter、finalize、subrequest 與 keep-alive。

# 第 17 章　ngx_http_request_t：一次 HTTP 交換的核心物件

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>`ngx_http_request_t`</h3><div class="foundation-block"><span>白話定義</span><p>代表一次 HTTP request/response 交換的核心 object，不等於底層 TCP connection。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同一 keep-alive connection 可以先後建立兩個不同 request objects。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>它保存 method、URI、headers、body、module contexts、routing、upstream 與 output state。</p></div></section><section class="foundation-card"><h3>Method、URI、headers、body</h3><div class="foundation-block"><span>白話定義</span><p>Method 表示動作，URI 表示目標，headers 是控制資訊，body 是可選內容。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>POST /orders</code> 加 <code>Content-Type: application/json</code> 與 JSON body。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 分階段解析這些部分，並讓 routing、access、proxy 與 filter modules 讀取結果。</p></div></section><section class="foundation-card"><h3>Transport（傳輸層工作）</h3><div class="foundation-block"><span>白話定義</span><p>Transport 只關心 bytes 如何經由連線抵達與送出，不理解這些 bytes 代表登入、圖片或 HTTP header。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>TCP 保證有順序的 byte stream，但不保證一個 <code>send()</code> 對應另一端的一個 <code>recv()</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 connection/event layer 處理 socket 與 readiness，上層 HTTP module 才解釋語意。</p></div></section><section class="foundation-card"><h3>HTTP keep-alive</h3><div class="foundation-block"><span>白話定義</span><p>完成一個 HTTP request 後不立刻關閉 TCP connection，讓同一 client 之後可在同一條連線上再送 request，省下重新建立 TCP 連線的時間。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>瀏覽器用同一條 connection 先取 HTML，再依序取圖片與 API response。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX finalize 舊 request、清除 request-lifetime state，再把 connection handler 改成等待下一個 request。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section></div>



<p class="chapter-question">Connection 已經存在後，NGINX 何時建立 request，又把哪些跨 callback 狀態放進去？</p>

<div class="chapter-meta"><span>難度：中階</span><span>request lifecycle · ownership · reference count</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

建立 request、connection、pool、module context、main/subrequest 與 reference count 的生命週期圖。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node active"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-16-backpressure-與-event-loop-公平性"><span>上一站</span><strong>16. Backpressure 與 Event Loop 公平性</strong></a><div class="position-card current"><span>你在這裡</span><strong>17. ngx_http_request_t：一次 HTTP 交換的核心物件</strong></div><a class="position-card" href="#chapter-18-http-request-line-狀態機"><span>下一站</span><strong>18. HTTP Request Line 狀態機</strong></a></div>

本章位於 **Part 4：HTTP Request 的一生**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Connection 只知道一條 byte stream；HTTP layer 需要一個物件保存這次語意交換的 method、URI、headers、body、routing 結果、module context 與 response 狀態。`ngx_http_request_t` 就是所有 HTTP modules 合作時共享的工作區。

Use case 是同一條 keep-alive connection 依序承載多個 requests，或一個 main request 建立 subrequests。若把 request state 塞進 connection，上一個請求的資料會污染下一個，生命週期與 cleanup 也無法分離。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Connection 只知道一條 byte stream；HTTP layer 需要一個物件保存這次語意交換的 method、URI、headers、body、routing 結果、module context 與 response 狀態。<code>ngx_http_request_t</code> 就是所有 HTTP modules 合作時共享的工作區。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是同一條 keep-alive connection 依序承載多個 requests，或一個 main request 建立 subrequests。若把 request state 塞進 connection，上一個請求的資料會污染下一個，生命週期與 cleanup 也無法分離。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「HTTP request context」這個責任邊界；接收 connection 上已讀取或即將讀取的 HTTP bytes，交付 完成的 response，或轉交 content/upstream pipeline。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 request pool、reference count、module ctx、headers/buffers 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 client abort、internal redirect、subrequest 未完成、重複 finalize。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>HTTP request context</p></div><div class="contract-card"><span>接收什麼</span><p>connection 上已讀取或即將讀取的 HTTP bytes</p></div><div class="contract-card"><span>產生什麼</span><p>完成的 response，或轉交 content/upstream pipeline</p></div><div class="contract-card"><span>狀態由誰保存</span><p>request pool、reference count、module ctx、headers/buffers</p></div><div class="contract-card"><span>主要失敗出口</span><p>client abort、internal redirect、subrequest 未完成、重複 finalize</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>HTTP connection handler 決定開始新 request</p></div><div class="flow-step"><span>2</span><p>從 connection pool/large header buffer 取得解析空間</p></div><div class="flow-step"><span>3</span><p>配置 <code>ngx_http_request_t</code> 與 request pool</p></div><div class="flow-step"><span>4</span><p>解析 request line/headers 並填欄位</p></div><div class="flow-step"><span>5</span><p>選 virtual server/location</p></div><div class="flow-step"><span>6</span><p>phase/content/upstream modules 寫入各自 ctx</p></div><div class="flow-step"><span>7</span><p>filter 送 response</p></div><div class="flow-step"><span>8</span><p>reference count 歸零後 cleanup，connection keep-alive 或 close</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

Connection 先存在；收到足以開始 HTTP parsing 的資料後，`ngx_http_create_request()` 才建立 request pool 與 `ngx_http_request_t`。Request 保存解析指標、headers、URI、phase index、read/write continuation、output state、upstream 與每個 module 的 ctx。

Config 和 ctx 必須分開：config 來自 cycle，對許多 requests 共用且通常唯讀；ctx 是 module 對單一 request 的暫存狀態，配置在 request pool，隨 request 結束。

`r->main` 與 `main->count` 協調 subrequest、async operation 與延後 finalize。返回 `NGX_DONE` 往往表示目前控制流停止，但主 request 仍有 pending ownership，不能立刻 free。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

若把 HTTP method、headers 與 routing 結果直接塞進 connection，keep-alive 的下一個 request 會繼承上一個 request 的狀態。獨立 request context 讓 transport 可重用，而語意交換可各自建立與釋放。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Connection</code></td><td><code>ngx_connection_t</code></td></tr><tr><td><code>Request</code></td><td><code>ngx_http_request_t</code></td></tr><tr><td><code>module_ctx</code></td><td>各 HTTP module 以 ctx index 保存 request-local state</td></tr><tr><td><code>references</code></td><td>main/subrequest/async work 使用的 request count</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_request.c`，官方 `release-1.31.5` 第 539–586 行

```c
ngx_http_create_request(ngx_connection_t *c)
{
    ngx_http_request_t        *r;
    ngx_http_log_ctx_t        *ctx;
    ngx_http_core_loc_conf_t  *clcf;

    r = ngx_http_alloc_request(c);
    if (r == NULL) {
        return NULL;
    }

    c->requests++;

    clcf = ngx_http_get_module_loc_conf(r, ngx_http_core_module);

    ngx_set_connection_log(c, clcf->error_log);

    ctx = c->log->data;
    ctx->request = r;
    ctx->current_request = r;

#if (NGX_STAT_STUB)
    (void) ngx_atomic_fetch_add(ngx_stat_reading, 1);
    r->stat_reading = 1;
    (void) ngx_atomic_fetch_add(ngx_stat_requests, 1);
#endif

    return r;
}


static ngx_http_request_t *
ngx_http_alloc_request(ngx_connection_t *c)
{
    ngx_pool_t                 *pool;
    ngx_time_t                 *tp;
    ngx_http_request_t         *r;
    ngx_http_connection_t      *hc;
    ngx_http_core_srv_conf_t   *cscf;
    ngx_http_core_main_conf_t  *cmcf;

    hc = c->data;

    cscf = ngx_http_get_module_srv_conf(hc->conf_ctx, ngx_http_core_module);

    pool = ngx_create_pool(cscf->request_pool_size, c->log);
    if (pool == NULL) {
        return NULL;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_http_create_request(c)</code> 建 request pool，配置並初始化 request。</p></div><div class="source-step"><span>2</span><p>將 connection buffer 交給 <code>r-&gt;header_in</code>，避免不必要 copy。</p></div><div class="source-step"><span>3</span><p>配置 <code>ctx/main_conf/srv_conf/loc_conf</code> pointer arrays。</p></div><div class="source-step"><span>4</span><p>把 <code>c-&gt;data</code> 切換為 request，安裝 request-line handler。</p></div><div class="source-step"><span>5</span><p>最終 <code>ngx_http_free_request</code> 執行 cleanups、log、destroy request pool。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>從 <code>ngx_http_create_request</code> 看哪些欄位在 request birth 時初始化。</p></div><div class="microscope-card"><span>2</span><p>分清 request pool 與 connection pool 的 owner/lifetime。</p></div><div class="microscope-card"><span>3</span><p>追 <code>r-&gt;main</code>、<code>r-&gt;parent</code>、<code>r-&gt;count</code> 如何影響 finalize。</p></div><div class="microscope-card"><span>4</span><p>Internal redirect 會改 routing state，但不應讓舊 module ctx 產生不一致。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- `r->connection` 是 client transport；`r->upstream->peer.connection` 是 backend transport。
- `main`、`parent` 與 `count` 決定 subrequest/finalize 關係。
- Request pool 釋放後所有指向其中資料的 pointer 都失效。
- Internal redirect 可能重跑部分 routing/phase，但仍在同一高階 request 生命線內。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_request.h#L385`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.h#L385) · [`src/http/ngx_http_request.c#L539`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L539) · [`src/http/ngx_http_request.c#L3981`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L3981)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Request struct 很大，不應從第一個欄位背到最後。按責任分群：input parser、routing/config、phase control、body/output、upstream、lifetime/flags。每追一條路徑只打開相關群。

Buffer ownership 是重點。Header bytes 常仍位於 connection/request buffer，`ngx_str_t` 只指向其中區間；若 module 要跨越 buffer reuse 或 request lifetime保存，就必須 copy 到更長生命週期。

Main request count 類似 structured concurrency 的 join counter。每個新增 async/subrequest obligation 增加 count，完成時減少；歸零才能進入最終 free。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Context object</h3><p>一個 request object 聚合跨 module、跨 callback 的狀態。</p></div><div class="pattern-card"><h3>Per-request dependency container</h3><p>module ctx array 讓擴充功能保存私有資料而不改 core struct。</p></div><div class="pattern-card"><h3>Reference-counted async completion</h3><p>main/subrequest 與延後工作完成後才真正釋放。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 在 `ngx_http_create_request` 前後比較 `c->data` 的型別與 request pool。
2. 挑十個 request 欄位，按 parser/routing/output/lifetime 分類。
3. 建立 keep-alive 兩次 request，確認 request pointer/pool 改變而 connection 可重用。
4. 找一個增加 `r->main->count` 的 async/subrequest 路徑與對應 decrement。

## 常見誤解與失敗模式

- 把 module config 當 request 私有資料並嘗試修改。
- 保存指向 request buffer 的 slice 到比 request 更長的 cache。
- 看到 content handler 返回就立即 free，忽略 pending subrequest/output。

## 可以帶走的 Coding／CS 能力

- 使用 ownership tree 與 lifetime region 分析大型 struct。
- 理解 per-request context、shared immutable config 與 async join counter。
- 避免 dangling slice 與跨生命週期 pointer。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Request object 建立後，下一章先看最前面的 request line 如何從碎片化 bytes 變成 method 與 URI。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Request 為何要有自己的 pool，而 connection 已有 pool？</summary>

Request 通常比 keep-alive connection 短；分池可在每次交換後釋放解析、module ctx、body 等大量資料，而保留 transport buffer與 socket。

</details>

<details class="qa" markdown="1">
<summary>Q2. `main_conf/srv_conf/loc_conf` 和 `ctx` 有何差別？</summary>

前三者指向 configuration generation 的共享唯讀設定；ctx 是某 module 對此 request 的可變執行狀態。

</details>

<details class="qa" markdown="1">
<summary>Q3. `c->data` 為何會改變語意？</summary>

通用 connection 只提供 `void *` 協定資料；accept 初期可指 HTTP connection context，建立 request 後改指 request。Handler 與階段共同決定正確型別。

</details>

<details class="qa" markdown="1">
<summary>Q4. Request slice 為何可能變成 dangling pointer？</summary>

許多 `ngx_str_t` 只引用 header/body buffer；buffer reuse 或 request pool destroy 後 bytes 不再有效。若需長期保存必須複製。

</details>

<details class="qa" markdown="1">
<summary>Q5. Main request count 解決什麼？</summary>

讓主 request 等待 subrequest、AIO、thread task、buffered output 等 obligations 全部完成，避免過早 free。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何閱讀巨大 request struct？</summary>

先依責任分群，再從一條 runtime trace 記錄實際讀寫欄位；不要把 layout 當 API 文件逐欄背誦。

</details>

---

# 第 18 章　HTTP Request Line 狀態機

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>TCP byte stream</h3><div class="foundation-block"><span>白話定義</span><p>TCP 提供可靠、有順序的 bytes，但沒有 application message boundary。資料可以被任意拆分或合併。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Sender 一次送出 <code>GET / HTTP/1.1</code>，receiver 可能先讀到 <code>GET / HT</code>，下一次才讀到其餘部分。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX parser 必須支援 partial read，不能假設一次 <code>recv()</code> 得到完整 HTTP request。</p></div></section><section class="foundation-card"><h3>Incremental parser</h3><div class="foundation-block"><span>白話定義</span><p>資料不完整時不阻塞也不丟失進度，而是保存 parser state；下一段 bytes 到來後繼續。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>第一次只收到 <code>GET / HT</code>，parser 記住目前在 version 前；第二次從該位置繼續。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX request line/header parser 回報 AGAIN、DONE 或 ERROR，state 保存在 request/parse fields。</p></div></section><section class="foundation-card"><h3>State machine（狀態機）</h3><div class="foundation-block"><span>白話定義</span><p>把流程表示成有限狀態與允許的轉移。遇到等待時保存目前 state；事件到來後從該 state 繼續。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>CONNECTING → SENDING → READING_HEADER → STREAMING_BODY → DONE。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 常把 state 分散在 struct fields 與可替換 callbacks，而不是寫成一個巨大 switch。</p></div></section><section class="foundation-card"><h3>Non-blocking I/O 與 EAGAIN</h3><div class="foundation-block"><span>白話定義</span><p>Non-blocking socket 在目前不能前進時立即返回，而不是讓整個 worker 睡在 <code>read()</code> 或 <code>write()</code> 裡。EAGAIN 表示『現在沒有，之後再試』。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Client 尚未送下一段 body 時，<code>recv()</code> 回 EAGAIN；worker 去處理別的 connections。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 保存 parser/output state，等待 epoll 再次通知 readiness 後由 callback 繼續。</p></div></section></div>



<p class="chapter-question">如果 `GET /api HTTP/1.1` 被拆成三個 TCP packet，parser 如何從上次停下的位置繼續？</p>

<div class="chapter-meta"><span>難度：進階</span><span>finite-state machine · incremental parser · bounds checking</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 incremental finite-state machine、pointer markers、`NGX_AGAIN` 與 buffer 擴容。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node active"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-17-ngx-http-request-t-一次-http-交換的核心物件"><span>上一站</span><strong>17. ngx_http_request_t：一次 HTTP 交換的核心物件</strong></a><div class="position-card current"><span>你在這裡</span><strong>18. HTTP Request Line 狀態機</strong></div><a class="position-card" href="#chapter-19-header-parsing-與安全邊界"><span>下一站</span><strong>19. Header Parsing 與安全邊界</strong></a></div>

本章位於 **Part 4：HTTP Request 的一生**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

TCP 不保證 `GET /path HTTP/1.1` 一次到齊；它可能拆成任意片段。Parser 必須在資料不完整時保存狀態，下一次 read 從正確位置繼續，同時拒絕非法字元與過長輸入。

Use case 包括慢速 client、封包分段與惡意超長 URI。若 parser 依賴 null-terminated string 或一次 read 完整行，會越界、阻塞或錯誤接受 ambiguous request。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>TCP 不保證 <code>GET /path HTTP/1.1</code> 一次到齊；它可能拆成任意片段。Parser 必須在資料不完整時保存狀態，下一次 read 從正確位置繼續，同時拒絕非法字元與過長輸入。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 包括慢速 client、封包分段與惡意超長 URI。若 parser 依賴 null-terminated string 或一次 read 完整行，會越界、阻塞或錯誤接受 ambiguous request。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Incremental request-line parser」這個責任邊界；接收 buffer 中目前可用的 bytes + 上次 parser state，交付 method、URI、HTTP version 或 AGAIN/error。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 request parser state 與 buffer positions 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 invalid syntax、line too long、buffer exhaustion、request smuggling ambiguity。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Incremental request-line parser</p></div><div class="contract-card"><span>接收什麼</span><p>buffer 中目前可用的 bytes + 上次 parser state</p></div><div class="contract-card"><span>產生什麼</span><p>method、URI、HTTP version 或 AGAIN/error</p></div><div class="contract-card"><span>狀態由誰保存</span><p>request parser state 與 buffer positions</p></div><div class="contract-card"><span>主要失敗出口</span><p>invalid syntax、line too long、buffer exhaustion、request smuggling ambiguity</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>從 <code>r-&gt;state</code> 恢復 parser state</p></div><div class="flow-step"><span>2</span><p>逐 byte 判斷 method/token</p></div><div class="flow-step"><span>3</span><p>遇到 space 轉入 URI state</p></div><div class="flow-step"><span>4</span><p>處理 schema/host/path/query 等分支</p></div><div class="flow-step"><span>5</span><p>遇到 CR/LF 檢查 HTTP version 與完整性</p></div><div class="flow-step"><span>6</span><p>資料耗盡但合法時回 AGAIN</p></div><div class="flow-step"><span>7</span><p>完整時保存 offsets/pointers 並進 header parser</p></div><div class="flow-step"><span>8</span><p>錯誤時回明確 parse code</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
bytes: G E T _ / a p i _ H T T P / 1 . 1 \r \n
state: method ─> spaces ─> URI ─> version ─> CR ─> LF ─> done

packet 1: "GET /a"      → state=URI, save pos
packet 2: "pi HTTP/1"   → state=version, save pos
packet 3: ".1\r\n"      → NGX_OK
```

## 從零建立心智模型

HTTP parser 不能假設完整 line 一次到達。它把目前 state 存在 request 欄位，把 buffer position 與 request_start、method_end、uri_start 等 markers 指向已讀 bytes；下一次 read 後從原 state 繼續 switch。

Parser 回 `NGX_AGAIN` 表示語法目前仍可能有效，只是 bytes 不夠。Caller 檢查 buffer 是否滿；滿了就配置 large header buffer 並搬移必要資料，或回 URI too large。語法錯誤則映射到特定 parse code，再產生 400/414 等 HTTP response。

高效 parser 常使用手寫 switch 與 pointer arithmetic，因為每個 byte 都在 hot path；但安全性來自每一步先檢查 end，且不把未驗證 bytes 當 NUL-terminated string。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

用 `split()` 解析 request line 假設整行一次到齊，遇到 fragmented TCP input 就失敗。Incremental FSM 保存 state 與 token buffer；資料不足不是錯誤，而是等待更多 bytes。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>state</code></td><td><code>r-&gt;state</code> parser state</td></tr><tr><td><code>feed</code></td><td><code>ngx_http_parse_request_line</code> 可被多次呼叫</td></tr><tr><td>data exhausted</td><td><code>NGX_AGAIN</code>：prefix 合法但尚未完整</td></tr><tr><td>method/URI markers</td><td>NGINX 以 buffer pointers 避免複製 token</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_parse.c`，官方 `release-1.31.5` 第 108–155 行

```c
ngx_http_parse_request_line(ngx_http_request_t *r, ngx_buf_t *b)
{
    u_char  c, ch, *p, *m;
    enum {
        sw_start = 0,
        sw_method,
        sw_spaces_before_uri,
        sw_schema,
        sw_schema_slash,
        sw_schema_slash_slash,
        sw_spaces_before_host,
        sw_host_start,
        sw_host,
        sw_host_end,
        sw_host_ip_literal,
        sw_port_start,
        sw_port,
        sw_after_slash_in_uri,
        sw_check_uri,
        sw_uri,
        sw_http_09,
        sw_http_H,
        sw_http_HT,
        sw_http_HTT,
        sw_http_HTTP,
        sw_first_major_digit,
        sw_major_digit,
        sw_first_minor_digit,
        sw_minor_digit,
        sw_spaces_after_digit,
        sw_almost_done
    } state;

    state = r->state;

    for (p = b->pos; p < b->last; p++) {
        ch = *p;

        switch (state) {

        /* HTTP methods: GET, HEAD, POST */
        case sw_start:
            r->request_start = p;

            if (ch == CR || ch == LF) {
                break;
            }

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Read handler 呼叫 <code>ngx_http_read_request_header</code> 把 bytes 補進 <code>header_in</code>。</p></div><div class="source-step"><span>2</span><p><code>ngx_http_parse_request_line(r, b)</code> 由 <code>r-&gt;state</code> 恢復 parser。</p></div><div class="source-step"><span>3</span><p>成功時設定 request/method/URI/version markers 與 normalized URI。</p></div><div class="source-step"><span>4</span><p>不完整時保留 state；buffer 滿時嘗試 large-header allocation。</p></div><div class="source-step"><span>5</span><p>完成 request line 後把 read handler 切到 header parser。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>把大 switch 畫成 state graph，再看每個 case 接受哪些字元。</p></div><div class="microscope-card"><span>2</span><p>區分 invalid prefix 與 incomplete prefix 的 return code。</p></div><div class="microscope-card"><span>3</span><p>檢查 token start/end pointer 是否仍落在有效 buffer。</p></div><div class="microscope-card"><span>4</span><p>Raw URI、normalized URI、args markers 在安全與 routing 上不可混用。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 先畫 states 與 transition，不要直接逐行讀巨型 switch。
- 注意 parser 回傳值：OK、AGAIN 與各類 invalid code 的 caller 行為不同。
- Pointer 通常指向 request buffer；buffer 生命週期與重新配置會影響有效性。
- 安全重點是 bounds check、CR/LF、空白規則與不同 HTTP hop 的一致解讀。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_parse.c#L105`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_parse.c#L105) · [`src/http/ngx_http_request.c#L1115`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L1115) · [`src/http/ngx_http_request.c#L1639`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L1639)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

狀態機的價值是把「所有可能 prefix」壓成有限狀態，而不是每次重掃整個 buffer。Markers 避免 substring copy；parse 完成後以 pointer difference 形成 `ngx_str_t`。

安全 parser 需要區分 raw URI、normalized URI 與 arguments。Percent decoding、dot segments、multiple slashes 與平台特殊字元都可能影響 routing/security；不能先 decode 再用另一套規則做 access check。

面試中的 expression parser、CSV streaming、protocol framing 都可用相同方法：state＋cursor＋token start＋explicit incomplete result。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Finite-state machine</h3><p>每個 state 只接受有限字元與轉移，適合增量解析。</p></div><div class="pattern-card"><h3>Streaming parser</h3><p>不複製完整字串也能跨 buffer 繼續。</p></div><div class="pattern-card"><h3>Fail closed</h3><p>未知或 ambiguous syntax 直接拒絕，避免不同 hop 解讀不一致。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 用 netcat 分三次輸入 request line，觀察同一 request parser 多次進入。
2. 在 parser breakpoint 記錄 `r->state`、`b->pos`、`b->last`。
3. 發送超長 URI，追蹤 large header buffer 與 414 路徑。
4. 比較 raw URI、normalized URI、args 在 `%2F`、`..`、重複 slash 下的值。

## 常見誤解與失敗模式

- 每次新資料到來就從頭 parse，造成重複掃描甚至 O(n²)。
- 將不完整 prefix 當語法錯誤，無法處理 TCP segmentation。
- 不同安全檢查使用不同 URI normalization 規則。

## 可以帶走的 Coding／CS 能力

- 實作 incremental parser 與 resumable state machine。
- 使用 pointer markers 避免 copy，同時維持 bounds safety。
- 理解 normalization order 對 routing/security 的影響。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

有了 request line，下一章用類似但更敏感的 parser 讀 headers 與 message framing。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. `NGX_AGAIN` 和 parse error 有何差異？</summary>

AGAIN 表示目前 prefix 合法但資料不足，應保存 state 等更多 bytes；error 表示無論後續 bytes 為何都不能成為合法 request。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為何不在每次 read 後重新從 request start 解析？</summary>

會重複掃描長 prefix，在逐 byte 到達時可能退化為 O(n²)；保存 state/cursor 可保持總體近 O(n)。

</details>

<details class="qa" markdown="1">
<summary>Q3. Markers 指向原 buffer 有何優點與風險？</summary>

避免 substring allocation/copy；但 buffer 搬移或釋放時需同步修正 pointer，且不得跨生命週期保存。

</details>

<details class="qa" markdown="1">
<summary>Q4. 為什麼 raw URI 與 normalized URI 都要保留？</summary>

Routing/security 常用規範化結果，代理或 log 有時需原始表示。混用可能造成 path confusion 或簽章不一致。

</details>

<details class="qa" markdown="1">
<summary>Q5. Large header buffer 只是效能設定嗎？</summary>

也是資源與安全邊界。太小拒絕合法大 request；太大乘上大量慢連線會增加 memory DoS surface。

</details>

<details class="qa" markdown="1">
<summary>Q6. 這個 parser pattern 可用在哪些 coding 題？</summary>

串流 tokenizer、括號/運算式解析、網路 frame decoder、逐塊 JSON/CSV，以及任何輸入可能被任意切分的題。

</details>

---

# 第 19 章　Header Parsing 與安全邊界

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>HTTP framing</h3><div class="foundation-block"><span>白話定義</span><p>Framing 是判斷一個 request 或 body 在 byte stream 中從哪裡開始、哪裡結束的規則。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>Content-Length: 10</code> 表示讀十個 body bytes；chunked encoding 則每段先給長度，最後以零長 chunk 結束。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 必須拒絕矛盾或含糊的 framing，否則 proxy 前後端可能對邊界產生不同理解。</p></div></section><section class="foundation-card"><h3>Method、URI、headers、body</h3><div class="foundation-block"><span>白話定義</span><p>Method 表示動作，URI 表示目標，headers 是控制資訊，body 是可選內容。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>POST /orders</code> 加 <code>Content-Type: application/json</code> 與 JSON body。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 分階段解析這些部分，並讓 routing、access、proxy 與 filter modules 讀取結果。</p></div></section><section class="foundation-card"><h3>Request smuggling</h3><div class="foundation-block"><span>白話定義</span><p>前端 proxy 與 backend 對 request 邊界理解不同時，攻擊者可讓一段 bytes 被一端視為 body、另一端視為下一個 request。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同時出現互相衝突的 Content-Length 與 Transfer-Encoding 是典型危險輸入。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX header parser 與 upstream encoder 必須使用一致、保守且不可含糊的 framing policy。</p></div></section><section class="foundation-card"><h3>Incremental parser</h3><div class="foundation-block"><span>白話定義</span><p>資料不完整時不阻塞也不丟失進度，而是保存 parser state；下一段 bytes 到來後繼續。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>第一次只收到 <code>GET / HT</code>，parser 記住目前在 version 前；第二次從該位置繼續。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX request line/header parser 回報 AGAIN、DONE 或 ERROR，state 保存在 request/parse fields。</p></div></section></div>



<p class="chapter-question">NGINX 如何逐行解析 header，同時處理 Host、Content-Length、重複欄位與大小限制？</p>

<div class="chapter-meta"><span>難度：進階</span><span>HTTP headers · framing · security</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 generic header list、known-header dispatch、host 切換、framing 衝突與 request smuggling 防線。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node active"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-18-http-request-line-狀態機"><span>上一站</span><strong>18. HTTP Request Line 狀態機</strong></a><div class="position-card current"><span>你在這裡</span><strong>19. Header Parsing 與安全邊界</strong></div><a class="position-card" href="#chapter-20-virtual-server-與-location-matching"><span>下一站</span><strong>20. Virtual Server 與 Location Matching</strong></a></div>

本章位於 **Part 4：HTTP Request 的一生**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Headers 不只是 metadata；`Content-Length`、`Transfer-Encoding`、`Host` 與 connection headers 會決定 request 邊界、routing 與後續讀取方式。Parser 必須既高效又在安全邊界上非常保守。

Use case 是把 raw header lines 轉成 generic list，同時對常見 headers 建立快速欄位。若 proxy chain 對重複或衝突 framing headers 解讀不同，就可能產生 request smuggling。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Headers 不只是 metadata；<code>Content-Length</code>、<code>Transfer-Encoding</code>、<code>Host</code> 與 connection headers 會決定 request 邊界、routing 與後續讀取方式。Parser 必須既高效又在安全邊界上非常保守。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是把 raw header lines 轉成 generic list，同時對常見 headers 建立快速欄位。若 proxy chain 對重複或衝突 framing headers 解讀不同，就可能產生 request smuggling。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「HTTP header normalization」這個責任邊界；接收 一行行 header bytes，交付 header list、known-header fields 與 body framing decision。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 request pool、header list、parser offsets 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 oversized/invalid header、duplicate Host、CL/TE conflict、underscore policy。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>HTTP header normalization</p></div><div class="contract-card"><span>接收什麼</span><p>一行行 header bytes</p></div><div class="contract-card"><span>產生什麼</span><p>header list、known-header fields 與 body framing decision</p></div><div class="contract-card"><span>狀態由誰保存</span><p>request pool、header list、parser offsets</p></div><div class="contract-card"><span>主要失敗出口</span><p>oversized/invalid header、duplicate Host、CL/TE conflict、underscore policy</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>增量找到 header name/token</p></div><div class="flow-step"><span>2</span><p>正規化或 hash header name</p></div><div class="flow-step"><span>3</span><p>解析 colon、optional whitespace 與 value</p></div><div class="flow-step"><span>4</span><p>配置 table element 保存 key/value</p></div><div class="flow-step"><span>5</span><p>known-header handler 填入 <code>headers_in</code> 快速欄位</p></div><div class="flow-step"><span>6</span><p>檢查 duplicates 與 semantic constraints</p></div><div class="flow-step"><span>7</span><p>空行表示 headers 結束</p></div><div class="flow-step"><span>8</span><p>決定是否及如何讀 request body</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
raw header line
   ↓ incremental parser
name slice + value slice + hash
   ↓
append generic headers list
   ↓ hash lookup known headers
Host ─────────> virtual server / config context
Content-Length ─> body framing
Connection ─────> keep-alive policy
```

## 從零建立心智模型

Header parser 和 request-line parser 同樣可跨 read。每完成一行，NGINX 建 `ngx_table_elt_t` 放入 generic list；同時用 lowercase hash 查 known-header table，執行專屬 processing callback，把常用欄位放進 `headers_in` 快速欄位。

Host 特別重要：request line 或 Host header 可選 virtual server，進而替換 srv/loc configuration context。也就是 parser 不只產生資料，還可能改變後續 policy 世界。

Content-Length、Transfer-Encoding、Connection 等不是普通 metadata，而是 message framing。衝突或非法重複值若前後代理理解不同，可能形成 request smuggling；parser 必須拒絕 ambiguous framing。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

把 headers 全部放普通 dict 會遺失重複順序，也無法對 `Host`、framing headers 套專屬規則。較好的模型同時保留 generic list 與 known-header typed fields。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>all</code> list</td><td><code>r-&gt;headers_in.headers</code> generic list</td></tr><tr><td>typed fields</td><td><code>headers_in.host</code>、<code>content_length</code> 等 shortcut</td></tr><tr><td><code>add</code> dispatch</td><td>known-header hash 對應的 processing callback</td></tr><tr><td>conflict error</td><td><code>ngx_http_process_request_header</code> 的整體 semantic validation</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_parse.c`，官方 `release-1.31.5` 第 871–918 行

```c
ngx_http_parse_header_line(ngx_http_request_t *r, ngx_buf_t *b,
    ngx_uint_t allow_underscores)
{
    u_char      c, ch, *p;
    ngx_uint_t  hash, i;
    enum {
        sw_start = 0,
        sw_name,
        sw_space_before_value,
        sw_value,
        sw_space_after_value,
        sw_ignore_line,
        sw_almost_done,
        sw_header_almost_done
    } state;

    /* the last '\0' is not needed because string is zero terminated */

    static u_char  lowcase[] =
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0-\0\0" "0123456789\0\0\0\0\0\0"
        "\0abcdefghijklmnopqrstuvwxyz\0\0\0\0\0"
        "\0abcdefghijklmnopqrstuvwxyz\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
        "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0";

    state = r->state;
    hash = r->header_hash;
    i = r->lowcase_index;

    for (p = b->pos; p < b->last; p++) {
        ch = *p;

        switch (state) {

        /* first char */
        case sw_start:
            r->header_name_start = p;
            r->invalid_header = 0;

            switch (ch) {
            case CR:
                r->header_end = p;
                state = sw_header_almost_done;
                break;
            case LF:
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>補資料並呼叫 <code>ngx_http_parse_header_line</code>，保存跨 buffer state。</p></div><div class="source-step"><span>2</span><p>完成一行後配置 table element，保存 key/value slice 與 hash。</p></div><div class="source-step"><span>3</span><p>Known-header hash 找到 callback，填入 typed/shortcut fields。</p></div><div class="source-step"><span>4</span><p>空行代表 headers complete，進入 <code>ngx_http_process_request_header</code> 做整體驗證。</p></div><div class="source-step"><span>5</span><p>驗證 Host、body framing、method/version、keepalive 後開始 phase engine。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Generic line parser 與 known-header handler 要分開讀。</p></div><div class="microscope-card"><span>2</span><p>檢查重複 header 的 policy；不同欄位不能一律 merge。</p></div><div class="microscope-card"><span>3</span><p>Host 可能切換 virtual server/config context。</p></div><div class="microscope-card"><span>4</span><p>Content-Length/Transfer-Encoding 影響 message boundary，需防 parser differential。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 不要只讀 generic parser；真正安全政策常在各 known-header handler。
- 重複 header 是否可合併取決於 header 語意，不能一律 concatenate。
- `Host` 會影響 virtual server；framing headers 會影響 body 邊界。
- 檢查 NGINX 與 upstream 對 hop-by-hop headers 的刪除／重建，避免原樣轉發。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
for each complete_header_line {
    header h = parse_name_value_slice(buffer);
    generic_headers.push(h);

    known = known_header_hash.lookup(lowercase_hash(h.name));
    if (known)
        known->process(request, h);
}

if (end_of_headers)
    validate_host_and_message_framing(request);
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_parse.c#L842`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_parse.c#L842) · [`src/http/ngx_http_request.c#L1401`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L1401) · [`src/http/ngx_http_request.c#L82`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L82)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Generic list 保留未知 header，讓 proxy/module 能轉發或處理擴充欄位；typed shortcuts 避免每個模組重複 scan。這是 raw representation＋normalized index 的常見雙層資料模型。

Header names、underscores、invalid characters、duplicate Host/Content-Length 都有 policy。安全重點不是「符合某一 parser」，而是整條 proxy chain 必須對邊界做一致解讀。

記錄 header 時也要考慮 secrets 與 log injection。值是 untrusted bytes；不要直接把 Authorization/Cookie 或控制字元完整寫入 log。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Parse then validate semantics</h3><p>語法 parser 與 known-header 規則分層。</p></div><div class="pattern-card"><h3>Dual representation</h3><p>generic list 保留全部 headers，typed fields 加速核心路徑。</p></div><div class="pattern-card"><h3>Protocol normalization boundary</h3><p>入口統一模糊語法，後層只看明確結果。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 發送未知 `X-Lab` header，找它在 generic list 與 proxy output 的位置。
2. 發送兩個不同 Content-Length、Host 或同時 CL/TE，記錄拒絕路徑。
3. 在 Host callback 前後觀察 request 的 srv/loc conf pointer。
4. 測試 header line/total buffer limits與慢速逐 byte 傳送。

## 常見誤解與失敗模式

- 把所有 header 當無語意 key/value，忽略 framing 與 routing 欄位。
- 只在最外層 proxy 驗證，後端 parser 使用不同規則。
- 將敏感或未清理 header 原樣寫 log。

## 可以帶走的 Coding／CS 能力

- 設計 raw＋indexed representation。
- 理解 protocol ambiguity、parser differential 與 request smuggling。
- 對 untrusted metadata 做 limit、normalization 與安全 logging。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Request 語法完整後，下一章決定它屬於哪個 server 與 location。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼既有 generic list 又有 `headers_in.host` 等欄位？</summary>

List 保留全部與未知擴充欄位；shortcut 提供 O(1) 常用語意存取並集中驗證。兩者服務不同需求。

</details>

<details class="qa" markdown="1">
<summary>Q2. Host header 為什麼能改變 config context？</summary>

同一 IP:port 可承載多個 virtual servers；讀到 Host 後才能選正確 server configuration，後續 location、limits、TLS外 policy 可能不同。

</details>

<details class="qa" markdown="1">
<summary>Q3. Content-Length 與 Transfer-Encoding 衝突為何危險？</summary>

不同 hop 若選不同 framing，攻擊者可讓前端認為 request 已結束、後端把剩餘 bytes 當下一請求，形成 queue desynchronization。

</details>

<details class="qa" markdown="1">
<summary>Q4. 為什麼 header limits 也是安全機制？</summary>

限制每 connection 可佔 memory、parser CPU 與等待時間，降低慢速或超大 header 的資源耗盡。

</details>

<details class="qa" markdown="1">
<summary>Q5. Known-header hash 的效能優點是什麼？</summary>

解析每行時一次 dispatch，後續模組直接讀 typed field，不必多次對 list 做字串比較；config/startup 可預建 lookup。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何安全記錄 malformed header？</summary>

限制長度、轉義控制字元、遮蔽 secrets，並包含 connection/request identifier；不要讓 attacker 產生巨量或偽造多行 log。

</details>

---

# 第 20 章　Virtual Server 與 Location Matching

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Virtual server 與 location</h3><div class="foundation-block"><span>白話定義</span><p>Virtual server 依 address/hostname 選網站；location 再依 URI 選該網站中的處理規則。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>api.example.com</code> 與 <code>static.example.com</code> 可共用 IP；前者的 <code>/v1/</code> 再走 proxy。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX config time 建立查找結構，request time 依 Host 與 URI 取得合併後 configuration。</p></div></section><section class="foundation-card"><h3>Regular expression（正規表示式）</h3><div class="foundation-block"><span>白話定義</span><p>用模式描述一組字串，適合複雜匹配，但通常比精確或 prefix 查找更昂貴且較難推理。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>~ \.php$</code> 匹配以 <code>.php</code> 結尾的 URI。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX location matching 有固定優先規則，不能把所有 location 當成由上到下的普通 if。</p></div></section><section class="foundation-card"><h3>Configuration context 與 merge</h3><div class="foundation-block"><span>白話定義</span><p>同一設定可能出現在全域、server 或 location；merge 是把父層預設值與子層覆寫組成最終設定。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>父 location 設 timeout 30 秒，子 location 可改成 3 秒；沒改的欄位繼承父層。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 config time 建立多份 conf object，runtime request 只需選擇合併後的結果。</p></div></section><section class="foundation-card"><h3>`ngx_http_request_t`</h3><div class="foundation-block"><span>白話定義</span><p>代表一次 HTTP request/response 交換的核心 object，不等於底層 TCP connection。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同一 keep-alive connection 可以先後建立兩個不同 request objects。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>它保存 method、URI、headers、body、module contexts、routing、upstream 與 output state。</p></div></section></div>



<p class="chapter-question">同一個 port 上有很多 server/location 時，NGINX 如何選出最後的 configuration？</p>

<div class="chapter-meta"><span>難度：進階</span><span>routing · prefix tree · configuration context</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

分清 address、Host、normalized URI 三次選擇，以及 prefix、regex、named location 與 internal redirect。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node active"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-19-header-parsing-與安全邊界"><span>上一站</span><strong>19. Header Parsing 與安全邊界</strong></a><div class="position-card current"><span>你在這裡</span><strong>20. Virtual Server 與 Location Matching</strong></div><a class="position-card" href="#chapter-21-http-phase-engine"><span>下一站</span><strong>21. HTTP Phase Engine</strong></a></div>

本章位於 **Part 4：HTTP Request 的一生**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

同一個 IP/port 可以服務多個 hostname，同一 hostname 又依 URI 使用不同設定。Virtual server 與 location matching 把外部 request 映射到一份合併後的 configuration context。

Use case 是 `/static/` 直接讀檔、`/api/` proxy、`~ \.php$` 走 FastCGI。若每次 request 都線性解讀原始 config，效能與規則一致性都很差，因此 NGINX 在啟動時先編譯 routing structures。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>同一個 IP/port 可以服務多個 hostname，同一 hostname 又依 URI 使用不同設定。Virtual server 與 location matching 把外部 request 映射到一份合併後的 configuration context。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 <code>/static/</code> 直接讀檔、<code>/api/</code> proxy、<code>~ \.php$</code> 走 FastCGI。若每次 request 都線性解讀原始 config，效能與規則一致性都很差，因此 NGINX 在啟動時先編譯 routing structures。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Configuration routing」這個責任邊界；接收 local address、Host/SNI、normalized URI，交付 選定 server conf 與 location conf。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 啟動期建好的 address/name/location tables 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 ambiguous rule、URI normalization 差異、regex order、internal redirect loop。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Configuration routing</p></div><div class="contract-card"><span>接收什麼</span><p>local address、Host/SNI、normalized URI</p></div><div class="contract-card"><span>產生什麼</span><p>選定 server conf 與 location conf</p></div><div class="contract-card"><span>狀態由誰保存</span><p>啟動期建好的 address/name/location tables</p></div><div class="contract-card"><span>主要失敗出口</span><p>ambiguous rule、URI normalization 差異、regex order、internal redirect loop</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>accept 後依 listen address 取得 server set</p></div><div class="flow-step"><span>2</span><p>解析 Host 後選 virtual server</p></div><div class="flow-step"><span>3</span><p>對 URI 做必要 normalization</p></div><div class="flow-step"><span>4</span><p>先做 exact/prefix location 查找</p></div><div class="flow-step"><span>5</span><p>依規則決定是否測 regex locations</p></div><div class="flow-step"><span>6</span><p>取得該 location 的 module conf array</p></div><div class="flow-step"><span>7</span><p>設定 content handler/phase config</p></div><div class="flow-step"><span>8</span><p>internal redirect 時按新 URI 重新查找</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

第一層在 accept/HTTP init 時依 local address:port 找 default server 與 name table。第二層在 request line/Host 完成後，用 exact/wildcard/regex server name 選 srv config。第三層用 normalized URI 選 location。

Location matching 不是單純「設定檔從上到下第一個匹配」。Static locations 在 config-time 整理成 tree，runtime 尋找 longest prefix；regex 與 nested policy 再按規則介入。Named location 通常由內部跳轉直接指定，不參與一般 URI prefix 查找。

Internal redirect、rewrite、index 等可能改 URI並重跑 location。為防設定迴圈，NGINX 有 URI changes counter；routing 是 bounded state machine，不是一錘定音。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

每次 request 線性掃描所有 location 規則既慢又容易搞錯 precedence。啟動時先編譯 exact/prefix/regex 結構，runtime 只按明確規則查找。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>exact dict</td><td>exact location lookup</td></tr><tr><td>longest prefix</td><td>static location tree 的最長 prefix 結果</td></tr><tr><td>ordered regexes</td><td>regex location 保留 configuration order</td></tr><tr><td>returned handler/config</td><td>切換到匹配 location 的 module loc conf array</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_core_module.c`，官方 `release-1.31.5` 第 1446–1491 行

```c
ngx_http_core_find_location(ngx_http_request_t *r)
{
    ngx_int_t                   rc;
    ngx_uint_t                  noregex;
    ngx_http_core_loc_conf_t   *clcf, *pclcf, **clcfp;
    ngx_http_variable_value_t  *vv;
#if (NGX_PCRE)
    ngx_int_t                   n;
#endif

    noregex = 0;

    pclcf = ngx_http_get_module_loc_conf(r, ngx_http_core_module);

    rc = ngx_http_core_find_static_location(r, pclcf->static_locations);

    if (rc == NGX_AGAIN) {

        clcf = ngx_http_get_module_loc_conf(r, ngx_http_core_module);

        noregex = clcf->noregex;

        /* look up nested locations */

        rc = ngx_http_core_find_location(r);
    }

    if (rc == NGX_OK || rc == NGX_DONE) {
        return rc;
    }

    /* rc == NGX_DECLINED or rc == NGX_AGAIN in nested location */

#if (NGX_PCRE)

    if (noregex == 0 && pclcf->regex_locations) {

        for (clcfp = pclcf->regex_locations; *clcfp; clcfp++) {

            ngx_log_debug1(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                           "test location: ~ \"%V\"", &(*clcfp)->name);

            n = ngx_http_regex_exec(r, (*clcfp)->regex, &r->uri);

            if (n == NGX_OK) {
                r->loc_conf = (*clcfp)->loc_conf;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Address/port config 提供初始 default server context。</p></div><div class="source-step"><span>2</span><p><code>ngx_http_set_virtual_server</code> 依 Host/name table 切換 server context。</p></div><div class="source-step"><span>3</span><p><code>ngx_http_core_find_location</code> 先查 static location tree。</p></div><div class="source-step"><span>4</span><p>依結果與設定處理 nested/regex location。</p></div><div class="source-step"><span>5</span><p>更新 <code>r-&gt;loc_conf</code>，執行 location-specific handler/config。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先手算 location precedence，再讀 tree/regex implementation。</p></div><div class="microscope-card"><span>2</span><p>URI normalization 先後會改變匹配與安全結果。</p></div><div class="microscope-card"><span>3</span><p>Internal redirect 可能再次執行 location lookup。</p></div><div class="microscope-card"><span>4</span><p>Runtime 使用的不是原始 config text，而是 init/merge 後的結構。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Location precedence 不能靠『看起來最像』；要按 exact、prefix、`^~`、regex 規則推演。
- URI normalization 與 filesystem path mapping 是不同階段。
- Regex locations 通常保留順序語意；prefix tree 則偏向最長匹配。
- Internal redirect 可能再次 location lookup，需防止無限循環。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
route(request *r) {
    r->server_conf = find_server(r->local_addr, r->host);
    r->uri = normalize(r->raw_uri);

    loc = longest_prefix(r->server_conf->location_tree, r->uri);
    if (loc.allows_regex)
        loc = first_matching_regex_or(loc);

    r->loc_conf = loc->module_configs;
}
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_request.c#L2558`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L2558) · [`src/http/ngx_http_core_module.c#L1446`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_core_module.c#L1446) · [`src/http/ngx_http.c#L760`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http.c#L760)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Configuration pointer 切換比複製設定更便宜：request 的 loc_conf array 改指向 config generation 中已合併物件。這也是 config immutable 的好處。

URI normalization 必須先於 location security policy，否則 `%2e%2e`、重複 slash、case/platform 差異可能讓不同層看到不同 path。另一方面，proxy 到 upstream 時是否傳 raw 或 normalized URI又有明確規則。

排查 routing 不應只看 location 文字。固定輸出 `$request_uri`、`$uri`、host、server_name、location marker，才能分辨原始 URI、normalized URI 與最後 config。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Compile routing rules</h3><p>啟動時把宣告式 config 轉成高效查找結構。</p></div><div class="pattern-card"><h3>Most-specific match with exceptions</h3><p>prefix/exact/regex 有明確 precedence。</p></div><div class="pattern-card"><h3>Context switch</h3><p>選 location 等於切換整組 module configuration。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 建立 exact、prefix、nested、regex、named locations，為每個回不同 header。
2. 測試 `/a`、`/a/`、percent-encoded 與重複 slash，記錄 `$request_uri`/`$uri`。
3. 用 rewrite/internal redirect 讓 location search 重跑，觀察 counter。
4. 在 virtual server lookup 前後比較 srv_conf pointer。

## 常見誤解與失敗模式

- 用設定檔視覺順序推測所有 location precedence。
- 把 raw request URI 與 normalized routing URI 混為一談。
- Internal redirect 無上限，形成 rewrite loop。

## 可以帶走的 Coding／CS 能力

- 理解 multi-stage routing、prefix tree 與 regex fallback。
- 使用 immutable config pointer 快速切換 policy context。
- 設計有迴圈上限的 rewrite/routing state machine。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

選定 location 後還沒真正執行功能；下一章由 phase engine 排定 rewrite、access 與 content handlers。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼先選 server 再選 location？</summary>

Location tree 屬於特定 server；同一 address 可依 Host 使用不同 locations、limits、root 與 upstream，因此需要分層選擇。

</details>

<details class="qa" markdown="1">
<summary>Q2. Longest prefix 和 regex 如何共同存在？</summary>

Static tree 先找最具體 prefix，之後依 location flags/nesting 規則決定是否測 regex；不是簡單的全域排序。

</details>

<details class="qa" markdown="1">
<summary>Q3. Named location 為何不走一般 URI matching？</summary>

它是內部控制流標籤，通常由 error_page、try_files 或 module 跳轉，名稱不是 client URI prefix。

</details>

<details class="qa" markdown="1">
<summary>Q4. Internal redirect 為什麼需要計數上限？</summary>

Rewrite A→B 與 B→A 可形成無限 loop；bounded counter 將設定錯誤轉成可終止失敗。

</details>

<details class="qa" markdown="1">
<summary>Q5. `$request_uri` 與 `$uri` 的排障價值？</summary>

前者通常保留原始請求表示含 args，後者是目前 normalized/可能被 rewrite 的 URI；兩者差異能揭示 routing confusion。

</details>

<details class="qa" markdown="1">
<summary>Q6. Config pointer 切換為何優於每 request merge？</summary>

Merge 在 reload 時完成，runtime 只改 array pointer，降低 hot-path CPU/allocation 並確保同 generation 一致。

</details>

---

# 第 21 章　HTTP Phase Engine

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>HTTP phase engine</h3><div class="foundation-block"><span>白話定義</span><p>把 request 處理拆成有順序的階段，每個 module 可以把 handler 註冊到適合的階段。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>先 rewrite URI，再做 access control，最後產生或 proxy content。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 config time 編譯 handler pipeline，runtime 用 return code 決定繼續、跳轉、暫停或結束。</p></div></section><section class="foundation-card"><h3>Handler 與 return code contract</h3><div class="foundation-block"><span>白話定義</span><p>Handler 是處理一小段責任的函式；它的 return code 不是隨意數字，而是告訴框架下一步。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>DECLINED</code> 可表示『我不處理，交給下一個』；<code>AGAIN</code> 表示 async 工作尚未完成。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>讀 NGINX source 時必須同時看 caller 如何解釋回傳值，不能只讀 handler 本身。</p></div></section><section class="foundation-card"><h3>Module（模組）</h3><div class="foundation-block"><span>白話定義</span><p>一組遵守固定介面的功能程式碼，可以註冊設定指令、request handler、filter 或 lifecycle hook。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Proxy、gzip、access control 都是不同 modules，但共同掛在 NGINX core 提供的擴充點。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Core 負責協調生命週期；module 專注自己的 configuration 與 request 行為。</p></div></section><section class="foundation-card"><h3>Config time 與 request time</h3><div class="foundation-block"><span>白話定義</span><p>Config time 低頻地解析規則並建立可重用資料；request time 高頻地使用結果，應避免重做相同工作。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 清單與 hash ring 在 reload 時建立；每個 request 只做選擇。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX modules 常有 main/server/location conf 與 per-request ctx，兩者 lifetime 不可混用。</p></div></section></div>



<p class="chapter-question">Rewrite、access control、content handler 為什麼能由不同模組依序插入，而 core 不需要知道每個模組？</p>

<div class="chapter-meta"><span>難度：進階</span><span>pipeline · middleware · return-code protocol</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 config-time 編譯 phase table、checker/handler 雙層函式與 return-code protocol。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node active"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-20-virtual-server-與-location-matching"><span>上一站</span><strong>20. Virtual Server 與 Location Matching</strong></a><div class="position-card current"><span>你在這裡</span><strong>21. HTTP Phase Engine</strong></div><a class="position-card" href="#chapter-22-request-body-buffer-與暫存檔"><span>下一站</span><strong>22. Request Body、Buffer 與暫存檔</strong></a></div>

本章位於 **Part 4：HTTP Request 的一生**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

許多 modules 都想在 request 的不同時機介入：改 URI、做 access control、限制速率、產生 content。若 core 為每個 module 寫固定呼叫，擴充會造成巨大耦合。Phase engine 把 handlers 在 configuration time 編譯成 runtime pipeline。

Use case 是 access module 能在 proxy module 前拒絕 request，rewrite 能改 URI 後重新找 location。Return code 不是普通成功失敗，而是控制 pipeline 是否繼續、暫停、跳轉或 finalize。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>許多 modules 都想在 request 的不同時機介入：改 URI、做 access control、限制速率、產生 content。若 core 為每個 module 寫固定呼叫，擴充會造成巨大耦合。Phase engine 把 handlers 在 configuration time 編譯成 runtime pipeline。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 access module 能在 proxy module 前拒絕 request，rewrite 能改 URI 後重新找 location。Return code 不是普通成功失敗，而是控制 pipeline 是否繼續、暫停、跳轉或 finalize。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「HTTP middleware pipeline」這個責任邊界；接收 已解析且已有 location conf 的 request，交付 content handler、暫停中的 async request 或最終 status。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 phase handler array + <code>r-&gt;phase_handler</code> cursor 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 錯誤 return protocol、重複執行、async handler 未保存狀態、rewrite loop。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>HTTP middleware pipeline</p></div><div class="contract-card"><span>接收什麼</span><p>已解析且已有 location conf 的 request</p></div><div class="contract-card"><span>產生什麼</span><p>content handler、暫停中的 async request 或最終 status</p></div><div class="contract-card"><span>狀態由誰保存</span><p>phase handler array + <code>r-&gt;phase_handler</code> cursor</p></div><div class="contract-card"><span>主要失敗出口</span><p>錯誤 return protocol、重複執行、async handler 未保存狀態、rewrite loop</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>postconfiguration 收集各 module phase handlers</p></div><div class="flow-step"><span>2</span><p>啟動時建立扁平 phase engine array</p></div><div class="flow-step"><span>3</span><p>request 進 <code>ngx_http_core_run_phases</code></p></div><div class="flow-step"><span>4</span><p>phase checker 呼叫目前 handler</p></div><div class="flow-step"><span>5</span><p>依 return code 繼續、跳下一 phase、暫停或 finalize</p></div><div class="flow-step"><span>6</span><p>rewrite 可能重新 location lookup</p></div><div class="flow-step"><span>7</span><p>content phase 找到 response producer</p></div><div class="flow-step"><span>8</span><p>未完成 async 工作由 callback 再續跑</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

HTTP modules在 postconfiguration 把 handler push 到某 phase array。Config initialization 將各 phase 編譯成扁平 `ngx_http_phase_handler_t` table，每項包含 checker、真正 module handler 與 next index。

Request 只保存 `phase_handler` index。`ngx_http_core_run_phases()` 迴圈呼叫 checker；checker統一解讀 module return code、決定前進、跳 phase、暫停或 finalize。模組不必彼此直接呼叫。

這是高效 middleware pipeline，但和常見 nested `next()` 不同：控制流用 index與 return protocol 表達。理解 `NGX_DECLINED` 尤其重要，它通常表示「我不處理，讓同 phase 下一 handler 嘗試」，不是錯誤。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

讓每個 middleware 自己呼叫下一個容易造成重複、漏呼叫與 async continuation 混亂。Phase engine 用 index 與 return-code protocol 統一決定 continue、stop、pause 或 finalize。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>handlers list</td><td>configuration-time 編好的 phase engine array</td></tr><tr><td>loop index</td><td><code>r-&gt;phase_handler</code></td></tr><tr><td><code>DECLINED</code></td><td>本 handler 不處理，交給下一個</td></tr><tr><td><code>AGAIN</code>/status</td><td>暫停 async work 或直接 short-circuit/finalize</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_core_module.c`，官方 `release-1.31.5` 第 889–932 行

```c
    ngx_http_core_run_phases(r);
}


void
ngx_http_core_run_phases(ngx_http_request_t *r)
{
    ngx_int_t                   rc;
    ngx_http_phase_handler_t   *ph;
    ngx_http_core_main_conf_t  *cmcf;

    cmcf = ngx_http_get_module_main_conf(r, ngx_http_core_module);

    ph = cmcf->phase_engine.handlers;

    while (ph[r->phase_handler].checker) {

        rc = ph[r->phase_handler].checker(r, &ph[r->phase_handler]);

        if (rc == NGX_OK) {
            return;
        }
    }
}


ngx_int_t
ngx_http_core_generic_phase(ngx_http_request_t *r, ngx_http_phase_handler_t *ph)
{
    ngx_int_t  rc;

    /*
     * generic phase checker,
     * used by the post read and pre-access phases
     */

    ngx_log_debug1(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                   "generic phase: %ui", r->phase_handler);

    rc = ph->handler(r);

    if (rc == NGX_OK) {
        r->phase_handler = ph->next;
        return NGX_AGAIN;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>HTTP core 建立 phases arrays，各 module 在 postconfiguration 註冊 handler。</p></div><div class="source-step"><span>2</span><p><code>ngx_http_init_phase_handlers</code> 依 phase 生成 checker/handler/next table。</p></div><div class="source-step"><span>3</span><p>Request 完成 header 後設定 <code>phase_handler</code> 與 write continuation。</p></div><div class="source-step"><span>4</span><p><code>ngx_http_core_run_phases</code> 從目前 index 執行，直到 checker 要求返回。</p></div><div class="source-step"><span>5</span><p>Async handler 保存必要 state，未來 event 再呼叫 run phases 或專用 continuation。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Handler 與 phase checker 必須一起讀，因為 return code 語意由 checker 解釋。</p></div><div class="microscope-card"><span>2</span><p>找 phase engine 在 postconfiguration 如何被編譯。</p></div><div class="microscope-card"><span>3</span><p>Rewrite 可能修改 URI 並跳回 location lookup。</p></div><div class="microscope-card"><span>4</span><p>Async handler 返回前必須保存 state 並安排未來 callback。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 同一 return code 在不同 checker 下可能有不同處理；要一起讀 handler 與 checker。
- `NGX_DECLINED` 常表示『我不處理，交給下一個』，不是 system error。
- Async handler 返回後若未 finalize，必須安排 future callback。
- Phase order 是 module interaction contract；錯掛 phase 會產生安全繞過。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
while (phase[i].checker != NULL) {
    rc = phase[i].checker(r, &phase[i]);

    if (rc == STOP_FOR_NOW)
        return;                       /* async 或已 finalize */
    /* checker 已更新 r->phase_handler */
    i = r->phase_handler;
}
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http.c#L448`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http.c#L448) · [`src/http/ngx_http_core_module.c#L894`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_core_module.c#L894) · [`src/http/ngx_http_core_module.c#L928`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_core_module.c#L928)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Checker 將控制語意集中。例如 access phase 可能依 `satisfy any/all` 聚合多個 module 結果；rewrite phase可能改 URI；content phase找到 handler後停止搜尋。Phase 不是同質列表。

模組 return code 是 ABI。若把 `NGX_OK`、`DECLINED`、`AGAIN` 用錯，可能跳過後續 handler、重複 finalize 或讓 request 永遠懸掛。寫 module 前要讀該 phase checker，而不只讀範例 handler。

扁平 table 提高 instruction/data locality並避免 request-time 建 pipeline。代價是 debug 時要把 index 對回 phase與 module。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Chain of responsibility</h3><p>多個 handler 依序檢查／處理 request。</p></div><div class="pattern-card"><h3>Compiled interpreter</h3><p>config-time 把 phase graph 編成小型 instruction array。</p></div><div class="pattern-card"><h3>Return-code protocol</h3><p>NGX_DECLINED/AGAIN/DONE/HTTP status 共同控制 pipeline。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 列出一個 request 的 phase index、checker、module handler trace。
2. 寫最小 preaccess handler 回 `NGX_DECLINED`，確認後續 handler仍執行。
3. 改回 403，確認 finalize 與 content phase 不再執行。
4. 找 access phase checker如何處理 satisfy any/all。

## 常見誤解與失敗模式

- 把 `NGX_DECLINED` 當服務失敗。
- 不讀 checker就猜 return code 語意。
- Async handler 返回後既不保存 continuation也不 finalize，造成 request leak。

## 可以帶走的 Coding／CS 能力

- 理解 compiled pipeline、table-driven dispatch 與 middleware。
- 設計明確 return-code protocol。
- 分析 plugin ordering、short circuit 與 async suspension。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Content handler 有時需要 client body；下一章看 body 如何在 memory、chain 與 temporary file 間流動。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Phase table 為何在 config-time 編譯？</summary>

模組集合與順序在 reload 後固定，預先扁平化可避免每 request 遍歷 registry或建立 chain，並預計算 jump index。

</details>

<details class="qa" markdown="1">
<summary>Q2. Checker 與 handler 為何分開？</summary>

Handler只實作模組功能；checker統一處理該 phase 的 return code、跳轉、聚合與 finalize規則。

</details>

<details class="qa" markdown="1">
<summary>Q3. `NGX_DECLINED` 通常代表什麼？</summary>

當前模組不處理或不做決定，讓同 phase/後續路徑繼續；它是控制信號，不是一般錯誤。

</details>

<details class="qa" markdown="1">
<summary>Q4. Async access check 應如何暫停 phase engine？</summary>

啟動 async work、增加必要引用或保存 ctx，回傳該 checker認可的 suspension code；完成 callback再恢復 phases或 finalize。

</details>

<details class="qa" markdown="1">
<summary>Q5. 這和 Express middleware 的 `next()` 有何差異？</summary>

Express常以 nested callback顯式 next；NGINX以扁平 index、checker與 return code驅動，適合 C與預編譯 pipeline。

</details>

<details class="qa" markdown="1">
<summary>Q6. 怎麼 debug 某模組為何沒執行？</summary>

確認是否註冊到預期 phase、postconfiguration順序、前一 checker是否 short-circuit、location config是否啟用，並 trace phase index。

</details>

---

# 第 22 章　Request Body、Buffer 與暫存檔

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Request body</h3><div class="foundation-block"><span>白話定義</span><p>Headers 後面的可選內容，可能是 JSON、表單或大型檔案；它可以分多次抵達。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>上傳 4 GB 檔案時，不能先把全部內容放進 memory 才開始處理。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 framing 增量讀 body，並按 module/config 選 memory buffer、temporary file 或 streaming。</p></div></section><section class="foundation-card"><h3>HTTP framing</h3><div class="foundation-block"><span>白話定義</span><p>Framing 是判斷一個 request 或 body 在 byte stream 中從哪裡開始、哪裡結束的規則。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>Content-Length: 10</code> 表示讀十個 body bytes；chunked encoding 則每段先給長度，最後以零長 chunk 結束。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 必須拒絕矛盾或含糊的 framing，否則 proxy 前後端可能對邊界產生不同理解。</p></div></section><section class="foundation-card"><h3>Buffer</h3><div class="foundation-block"><span>白話定義</span><p>一段可讀或可寫的資料範圍，加上目前讀到哪裡、送到哪裡等位置資訊。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>8 KB memory 裡只有索引 100–340 是尚未送出的資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_buf_t</code> 可以描述 memory 或 file range；位置前進即可表示 partial read/write，而不必複製內容。</p></div></section><section class="foundation-card"><h3>Buffering 與 streaming</h3><div class="foundation-block"><span>白話定義</span><p>Buffering 先暫存資料以吸收兩端速度差；streaming 則資料一到便逐段往下游傳，不等待完整內容。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>小 response 可留在 memory；大 response 可能落 temporary file；即時事件適合 streaming。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 module/config 在 latency、memory、disk I/O 與 backend connection 占用之間取捨。</p></div></section><section class="foundation-card"><h3>Non-blocking I/O 與 EAGAIN</h3><div class="foundation-block"><span>白話定義</span><p>Non-blocking socket 在目前不能前進時立即返回，而不是讓整個 worker 睡在 <code>read()</code> 或 <code>write()</code> 裡。EAGAIN 表示『現在沒有，之後再試』。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Client 尚未送下一段 body 時，<code>recv()</code> 回 EAGAIN；worker 去處理別的 connections。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 保存 parser/output state，等待 epoll 再次通知 readiness 後由 callback 繼續。</p></div></section></div>



<p class="chapter-question">POST body 可能尚未到齊時，content handler 如何等待、落盤或串流而不阻塞 worker？</p>

<div class="chapter-meta"><span>難度：進階</span><span>request body · buffer chain · streaming</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 body framing、post handler continuation、buffer chain、temporary file 與 unbuffered mode。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node active"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-21-http-phase-engine"><span>上一站</span><strong>21. HTTP Phase Engine</strong></a><div class="position-card current"><span>你在這裡</span><strong>22. Request Body、Buffer 與暫存檔</strong></div><a class="position-card" href="#chapter-23-response-與-filter-chain"><span>下一站</span><strong>23. Response 與 Filter Chain</strong></a></div>

本章位於 **Part 4：HTTP Request 的一生**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Headers 到齊不代表 request 到齊。POST/PUT body 可能很大、分段到達，甚至超過 memory budget。NGINX 必須依 Content-Length/chunked framing 增量讀取，並讓 module 選擇 buffer、temporary file 或 streaming consumption。

Use case 是上傳 JSON、小表單、數 GB 檔案或 proxy request body。若一律全部讀進 memory，少數大 request 就能耗盡 worker；若完全不 buffer，retry 時又可能無法重播 body。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Headers 到齊不代表 request 到齊。POST/PUT body 可能很大、分段到達，甚至超過 memory budget。NGINX 必須依 Content-Length/chunked framing 增量讀取，並讓 module 選擇 buffer、temporary file 或 streaming consumption。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是上傳 JSON、小表單、數 GB 檔案或 proxy request body。若一律全部讀進 memory，少數大 request 就能耗盡 worker；若完全不 buffer，retry 時又可能無法重播 body。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Request-body ingestion」這個責任邊界；接收 client read events + framing metadata，交付 memory chains、temporary file 或 streaming callbacks。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 <code>ngx_http_request_body_t</code>、buffers、temp file、rest counter 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 body too large、timeout、client abort、chunk parse error、unreplayable retry。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Request-body ingestion</p></div><div class="contract-card"><span>接收什麼</span><p>client read events + framing metadata</p></div><div class="contract-card"><span>產生什麼</span><p>memory chains、temporary file 或 streaming callbacks</p></div><div class="contract-card"><span>狀態由誰保存</span><p><code>ngx_http_request_body_t</code>、buffers、temp file、rest counter</p></div><div class="contract-card"><span>主要失敗出口</span><p>body too large、timeout、client abort、chunk parse error、unreplayable retry</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>依 method/module 決定是否需要 body</p></div><div class="flow-step"><span>2</span><p>根據 framing 初始化剩餘長度/chunk parser</p></div><div class="flow-step"><span>3</span><p>先消費 header buffer 中已讀到的 body bytes</p></div><div class="flow-step"><span>4</span><p>read event 到來時填 buffers</p></div><div class="flow-step"><span>5</span><p>完整 buffers 交給 filter/consumer</p></div><div class="flow-step"><span>6</span><p>超過 memory threshold 時寫 temp file</p></div><div class="flow-step"><span>7</span><p>body 完成後呼叫 post handler</p></div><div class="flow-step"><span>8</span><p>finalize 時 cleanup file/buffers</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

Body 讀取是非同步子流程。Module 呼叫 `ngx_http_read_client_request_body(r, post_handler)`；若資料不完整，函式安裝 read handler、timer並返回。Body 完成後才呼叫 post handler，這就是 continuation passing。

Framing 由 Content-Length 或 chunked parser決定。Bytes 可能已有一部分跟 headers 同時進入 `header_in`，必須先消費，不能丟掉或重讀。

Body 可存在 chain of buffers，也可寫入 temporary file；proxy request buffering開啟時通常先完整接收 client body，再連/送 upstream。關閉 buffering則可邊收邊轉發，但 retry能力、backend occupancy與 flow control 更複雜。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

將所有 request body 讀進 RAM 對大上傳不安全；完全 streaming 又可能無法 retry。這個例子先在 memory 累積，超過門檻便 spill 到 temporary file。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>feed(chunk)</code></td><td>client read event 逐批填 request-body buffers</td></tr><tr><td>memory limit</td><td><code>client_body_buffer_size</code> 類政策</td></tr><tr><td>temporary file</td><td><code>ngx_temp_file_t</code> request body storage</td></tr><tr><td>completion callback</td><td>body 完整後才呼叫 module 的 post handler</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_request_body.c`，官方 `release-1.31.5` 第 32–79 行

```c
ngx_http_read_client_request_body(ngx_http_request_t *r,
    ngx_http_client_body_handler_pt post_handler)
{
    size_t                     preread;
    ssize_t                    size;
    ngx_int_t                  rc;
    ngx_buf_t                 *b;
    ngx_chain_t                out;
    ngx_http_request_body_t   *rb;
    ngx_http_core_loc_conf_t  *clcf;

    r->main->count++;

    if (r != r->main || r->request_body || r->discard_body) {
        r->request_body_no_buffering = 0;
        post_handler(r);
        return NGX_OK;
    }

    if (ngx_http_test_expect(r) != NGX_OK) {
        rc = NGX_HTTP_INTERNAL_SERVER_ERROR;
        goto done;
    }

    rb = ngx_pcalloc(r->pool, sizeof(ngx_http_request_body_t));
    if (rb == NULL) {
        rc = NGX_HTTP_INTERNAL_SERVER_ERROR;
        goto done;
    }

    /*
     * set by ngx_pcalloc():
     *
     *     rb->temp_file = NULL;
     *     rb->bufs = NULL;
     *     rb->buf = NULL;
     *     rb->free = NULL;
     *     rb->busy = NULL;
     *     rb->chunked = NULL;
     *     rb->received = 0;
     *     rb->filter_need_buffering = 0;
     *     rb->last_sent = 0;
     *     rb->last_saved = 0;
     */

    rb->rest = -1;
    rb->post_handler = post_handler;

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Header validation決定是否有 body與 framing方式。</p></div><div class="source-step"><span>2</span><p>Body reader先使用已在 header buffer中的 preread bytes。</p></div><div class="source-step"><span>3</span><p>不完整時安裝 client read handler與 timeout，逐 event讀取。</p></div><div class="source-step"><span>4</span><p>Chunked filter解析 chunk size/trailer；decoded bytes放入 buffers。</p></div><div class="source-step"><span>5</span><p>完成後呼叫 module提供的 post handler，恢復原業務流程。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Header buffer 中可能已有 preread body bytes。</p></div><div class="microscope-card"><span>2</span><p>Body API 是 async；初次呼叫返回不代表 body ready。</p></div><div class="microscope-card"><span>3</span><p>Chunked parser 與 storage/filter 是不同層。</p></div><div class="microscope-card"><span>4</span><p>Client abort/error 時檢查 temporary file cleanup 與 callback ownership。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Body read API 常是 async：函式返回不代表 body 已完成，真正 continuation 是 post handler。
- Header buffer 可能已含部分 body，不能忽略 preread bytes。
- Chunked 是 framing protocol，不等於 upstream 一定也使用 chunked。
- 檢查 temp file cleanup 與 client abort branch，避免磁碟資源殘留。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_request_body.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request_body.c#L1) · [`src/http/ngx_http_parse.c#L2075`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_parse.c#L2075) · [`src/http/ngx_http_upstream.c#L626`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L626)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Request body reference count防止讀取中 request被 finalize。Module callback必須遵守「可能同步完成，也可能稍後完成」的雙態 API；post handler不能假設一定在另一輪呼叫。

落盤不是失敗，而是 bounded memory策略。安全上需控制 temp path權限、最大 body、disk quota與 client timeout，避免大量慢 upload吃滿 disk或 connection。

Unbuffered forwarding需要處理三方背壓：client producer、NGINX中介、upstream consumer。Backend慢時應停止讀 client，否則仍會在 memory堆積。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Streaming with bounded buffers</h3><p>資料可以逐塊交付，不要求整體一次存在。</p></div><div class="pattern-card"><h3>Spill to disk</h3><p>memory 超過上限時轉移到 temporary file。</p></div><div class="pattern-card"><h3>Replayability policy</h3><p>buffer body 可支援 retry；pure streaming 降低 latency 但難重播。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. POST 小 body，證明 body bytes可能已在 header buffer。
2. 逐塊慢速上傳，觀察 body read handler與 timeout。
3. 將 buffer設小讓 body落 temp file，檢查 chain中的 file buffer。
4. 切換 `proxy_request_buffering` 比較 backend connect時機與 retry行為。

## 常見誤解與失敗模式

- 假設 body reader callback一定非同步，造成雙重繼續或未初始化狀態。
- 忽略 preread bytes，導致 body開頭遺失。
- 關掉 buffering卻未實作 backend慢時的 client backpressure。

## 可以帶走的 Coding／CS 能力

- 掌握 continuation API 的同步/非同步雙態。
- 理解 stream framing、spooling與 bounded memory。
- 設計三段 pipeline 的 flow control與 retry語意。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

不論 response 由 static、proxy 或其他 module 產生，都要經共同 output pipeline；下一章看 filter chain。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Body 為何可能在 header parsing時已收到？</summary>

TCP只傳 byte stream，一次 recv可同時包含 header結尾與部分body；parser消費到空行後剩餘 bytes必須交 body reader。

</details>

<details class="qa" markdown="1">
<summary>Q2. Post handler 為何必要？</summary>

Body可能跨多次 read event完成，原 content handler的 stack早已返回；post handler保存完成後的下一步。

</details>

<details class="qa" markdown="1">
<summary>Q3. Body落 temp file代表效能一定很差嗎？</summary>

不一定。它用disk換 bounded memory，可保護大量大 upload；是否合理取決於disk、size、latency與 forwarding策略。

</details>

<details class="qa" markdown="1">
<summary>Q4. `proxy_request_buffering off` 對 retry 有何影響？</summary>

若 body已部分串流給某 backend，換下一 peer可能無法重新取得完整body，尤其 client仍在傳；可重試範圍通常縮小。

</details>

<details class="qa" markdown="1">
<summary>Q5. 同步/非同步都可能完成的 API 有什麼陷阱？</summary>

Caller若在呼叫後無條件再執行 continuation，當 callback已同步執行會 double action；應依 return contract或只由 callback推進。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何防止慢 upload耗盡資源？</summary>

限制 body size、header/body timeout、connection數、temp disk/quota，並在 downstream阻塞時停止 read。

</details>

---

# 第 23 章　Response 與 Filter Chain

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Status、response headers 與 body</h3><div class="foundation-block"><span>白話定義</span><p>Status 表示結果類型，headers 描述 response metadata，body 才是主要內容；某些 method/status 不允許 body。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>204 No Content</code> 不應附一般 response body；HEAD 回覆 headers 但不傳實際 body。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Module 必須先正確設定 headers，再呼叫 header/body filter，並遵守 Content-Length 與 final flags。</p></div></section><section class="foundation-card"><h3>Response 與 filter chain</h3><div class="foundation-block"><span>白話定義</span><p>Content handler 產生 response；filters 依序檢查或轉換 headers/body，再交給下一層。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Proxy body 先經 gzip，再套 chunked framing，最後寫入 socket。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 top/next function pointers 串接 filters，新增功能不必修改每個 content module。</p></div></section><section class="foundation-card"><h3>Buffer chain</h3><div class="foundation-block"><span>白話定義</span><p>把多段不一定連續、來源不同的資料，用 linked nodes 表示成一個輸出序列。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Response headers 在 memory，body 在 file，最後還有一個 end marker。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_chain_t</code> 串起 <code>ngx_buf_t</code>；partial write 只移動 positions，未送完 nodes 留在 busy chain。</p></div></section><section class="foundation-card"><h3>Handler 與 return code contract</h3><div class="foundation-block"><span>白話定義</span><p>Handler 是處理一小段責任的函式；它的 return code 不是隨意數字，而是告訴框架下一步。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>DECLINED</code> 可表示『我不處理，交給下一個』；<code>AGAIN</code> 表示 async 工作尚未完成。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>讀 NGINX source 時必須同時看 caller 如何解釋回傳值，不能只讀 handler 本身。</p></div></section></div>



<p class="chapter-question">Content module 產生的 header/body 如何依序經過 gzip、chunked、range、copy 與 write filter？</p>

<div class="chapter-meta"><span>難度：進階</span><span>filter chain · decorator · output pipeline</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 top/next filter 鏈、註冊反序、header/body 分工、buffer flags與 partial output。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node active"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-22-request-body-buffer-與暫存檔"><span>上一站</span><strong>22. Request Body、Buffer 與暫存檔</strong></a><div class="position-card current"><span>你在這裡</span><strong>23. Response 與 Filter Chain</strong></div><a class="position-card" href="#chapter-24-finalize-keep-alive-與-subrequest"><span>下一站</span><strong>24. Finalize、Keep-Alive 與 Subrequest</strong></a></div>

本章位於 **Part 4：HTTP Request 的一生**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Response 可能需要 gzip、range、chunked encoding、header 修改、logging 或最終 socket write。若 content module 自己處理所有組合，功能會呈乘法爆炸。Filter chain 讓每個 filter 專注一種 transformation，再呼叫下一層。

Use case 是 proxy response 加 header 後 gzip，再做 chunked framing 與 write。Filter 必須處理任意 buffer 邊界、flush/last flags 與 downstream backpressure。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Response 可能需要 gzip、range、chunked encoding、header 修改、logging 或最終 socket write。若 content module 自己處理所有組合，功能會呈乘法爆炸。Filter chain 讓每個 filter 專注一種 transformation，再呼叫下一層。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 proxy response 加 header 後 gzip，再做 chunked framing 與 write。Filter 必須處理任意 buffer 邊界、flush/last flags 與 downstream backpressure。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Response transformation pipeline」這個責任邊界；接收 response headers 或 buffer chain，交付 修改後的 headers/chains，最終送到 client。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 filter module ctx + chain links + buffer flags 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 順序錯誤、重入、跨 buffer state 丟失、未傳遞 last/flush、partial write。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Response transformation pipeline</p></div><div class="contract-card"><span>接收什麼</span><p>response headers 或 buffer chain</p></div><div class="contract-card"><span>產生什麼</span><p>修改後的 headers/chains，最終送到 client</p></div><div class="contract-card"><span>狀態由誰保存</span><p>filter module ctx + chain links + buffer flags</p></div><div class="contract-card"><span>主要失敗出口</span><p>順序錯誤、重入、跨 buffer state 丟失、未傳遞 last/flush、partial write</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>Postconfiguration 把 module filter 掛到 top chain</p></div><div class="flow-step"><span>2</span><p>content/upstream 呼叫 top header filter</p></div><div class="flow-step"><span>3</span><p>各 filter 檢查／修改 headers 並呼叫 next</p></div><div class="flow-step"><span>4</span><p>body chunks 進 top body filter</p></div><div class="flow-step"><span>5</span><p>filter 轉換或旁路 buffers</p></div><div class="flow-step"><span>6</span><p>output/write filter 嘗試 send/writev</p></div><div class="flow-step"><span>7</span><p>送不完保存 busy chain 並回 AGAIN</p></div><div class="flow-step"><span>8</span><p>writable event 再續送</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
content handler
   │ ngx_http_send_header(r)
   ▼
[top header filter] → ... → protocol header encoder

body chain
   ▼
[gzip?] → [range?] → [chunked?] → [copy] → [write filter]
                                                    │
                                              socket / sendfile
```

## 從零建立心智模型

每個 filter module初始化時保存舊 top pointer為 `next`，再把 global top指向自己。結果是後註冊者先執行，形成手寫 decorator chain。Header filter決定 status/headers與是否需要 body transformation；body filter接收 `ngx_chain_t *`。

Buffer 不只是 byte array。Flags 表示 memory/file、flush、sync、last_buf、last_in_chain、temporary/recycled 等語意。Filter 可以引用原 buffer、產生新 buffer、延後輸出或回 `NGX_AGAIN`。

最底層 write filter合併 pending chain並嘗試 writev/sendfile；未送完的部分留在 request output state，等待 write-ready事件。上層不能在函式返回後修改仍被引用的 temporary buffer。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Content producer 若自己同時做 gzip、header 修改、chunking 與 socket write，功能組合會爆炸。Filter chain 讓每一層只做一種轉換並轉交下一層。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>top_filter</code></td><td><code>ngx_http_top_body_filter</code></td></tr><tr><td>closure <code>next_filter</code></td><td>每個 module 保存的 <code>ngx_http_next_body_filter</code></td></tr><tr><td>chunks</td><td><code>ngx_chain_t</code> buffers</td></tr><tr><td>sink</td><td>最終 write/output filter</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_core_module.c`，官方 `release-1.31.5` 第 1954–1998 行

```c
ngx_http_output_filter(ngx_http_request_t *r, ngx_chain_t *in)
{
    ngx_int_t          rc;
    ngx_connection_t  *c;

    c = r->connection;

    ngx_log_debug2(NGX_LOG_DEBUG_HTTP, c->log, 0,
                   "http output filter \"%V?%V\"", &r->uri, &r->args);

    rc = ngx_http_top_body_filter(r, in);

    if (rc == NGX_ERROR) {
        /* NGX_ERROR may be returned by any filter */
        c->error = 1;
    }

    return rc;
}


u_char *
ngx_http_map_uri_to_path(ngx_http_request_t *r, ngx_str_t *path,
    size_t *root_length, size_t reserved)
{
    u_char                    *last;
    size_t                     alias;
    ngx_http_core_loc_conf_t  *clcf;

    clcf = ngx_http_get_module_loc_conf(r, ngx_http_core_module);

    alias = clcf->alias;

    if (alias && !r->valid_location) {
        ngx_log_error(NGX_LOG_ALERT, r->connection->log, 0,
                      "\"alias\" cannot be used in location \"%V\" "
                      "where URI was rewritten", &clcf->name);
        return NULL;
    }

    if (clcf->root_lengths == NULL) {

        *root_length = clcf->root.len;

        path->len = clcf->root.len + reserved + r->uri.len - alias + 1;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>HTTP postconfiguration依 modules註冊 header/body filters。</p></div><div class="source-step"><span>2</span><p>Content handler設定 <code>headers_out</code>，呼叫 top header filter。</p></div><div class="source-step"><span>3</span><p>Body以 chain傳入 top body filter，每層轉換後呼叫 next。</p></div><div class="source-step"><span>4</span><p>Copy/output chain把 memory/file buffer轉成適合傳輸的形態。</p></div><div class="source-step"><span>5</span><p>Write filter做最後 send，partial output標記 request buffered並等待 writable。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>註冊順序決定 filter order；不要依 source file 排列猜。</p></div><div class="microscope-card"><span>2</span><p>跨 buffers 的 transformation state 必須放 request ctx。</p></div><div class="microscope-card"><span>3</span><p>下游回 AGAIN 時上游不能丟失 busy buffers。</p></div><div class="microscope-card"><span>4</span><p>傳遞 <code>last_buf</code>、<code>flush</code>、<code>sync</code> 等 framing/stream flags。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Filter order 由註冊順序與 top/next 保存方式決定，直覺上的 source file order不可靠。
- Buffer 的 `last_buf`、`last_in_chain`、`flush`、`sync` 都有語意。
- 不可假設每次收到完整 token 或完整 response。
- 修改 Content-Length 的 filter 必須同步處理 framing，否則 client 會誤判邊界。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
static body_filter_pt next_filter;

int my_filter(request_t *r, chain_t *in) {
    chain_t *out = transform_without_losing_flags(r, in);
    return next_filter(r, out);
}

void init_module(void) {
    next_filter = top_body_filter;
    top_body_filter = my_filter;
}
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http.c#L74`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http.c#L74) · [`src/http/ngx_http_header_filter_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_header_filter_module.c#L1) · [`src/http/ngx_http_write_filter_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_write_filter_module.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Filter ordering影響正確性：壓縮前後的 Content-Length、range作用於原始或編碼 representation、chunked framing位置都不能隨意。模組需理解自己在 chain中的相對位置。

Backpressure穿過 filter chain。某層保留 input等待更多資料時要管理 free/busy/out chains，不能假設 next filter同步消費完所有 bytes。

`last_buf` 對 main request表示整個 response最後 buffer；subrequest常用 `last_in_chain`。混用會提早終止或讓 response永不完成。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Decorator / filter chain</h3><p>每層包住下一層，獨立組合 response 行為。</p></div><div class="pattern-card"><h3>Streaming transducer</h3><p>輸入 chunks 轉為輸出 chunks，state 可跨呼叫。</p></div><div class="pattern-card"><h3>Backpressure-preserving interface</h3><p>下游 AGAIN 必須原樣向上游反映。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 用 debug build列出 top filter註冊結果，畫出實際順序。
2. 開關 gzip/chunked，觀察 headers與 body buffer flags。
3. 建立大 response與慢 client，在 write filter檢查未送 chain。
4. 寫只加 header的 filter，再寫 body prefix filter，比較生命週期。

## 常見誤解與失敗模式

- Filter傳完 next後立即覆寫 input memory，但下游尚未完成。
- 丟失 flush/last_buf flags，造成延遲或 response掛住。
- 只考慮 main request，破壞 subrequest chain語意。

## 可以帶走的 Coding／CS 能力

- 理解 decorator/filter pipeline與註冊順序。
- 用 immutable slice/ownership flags安全傳遞 buffer。
- 分析 streaming transformation與downstream backpressure。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Pipeline 最後仍需正確結束 request 並決定是否重用 connection；下一章收束生命週期。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼 filter通常保存 old top再替換 top？</summary>

這讓每個 module不需知道其他 filters；初始化時形成 linked function chain，執行時呼叫自己的 next。

</details>

<details class="qa" markdown="1">
<summary>Q2. Body filter返回後 input一定可重用嗎？</summary>

不一定。下游可能只部分送出並仍引用該 buffer；必須遵守 buffer temporary/recycled與free/busy chain contract。

</details>

<details class="qa" markdown="1">
<summary>Q3. `last_buf` 遺失會怎樣？</summary>

下游不知道 response完成，chunk terminator、flush、finalize或keepalive切換可能不發生，request長期掛起。

</details>

<details class="qa" markdown="1">
<summary>Q4. Filter ordering為何不是純效能問題？</summary>

Content-Length、content encoding、range與chunk framing都有語意依賴；錯序會產生無效甚至安全有問題的 response。

</details>

<details class="qa" markdown="1">
<summary>Q5. Write filter如何處理 partial write？</summary>

更新 buffer position，保留未完成 chain，標記 buffered並安裝/等待 write event；下次從剩餘位置續送。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何寫 streaming-safe filter？</summary>

不假設完整 body一次到達；保存跨 chunk state、正確傳播flush/last flags、尊重partial consumption與request pool lifetime。

</details>

---

# 第 24 章　Finalize、Keep-Alive 與 Subrequest

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Finalize</h3><div class="foundation-block"><span>白話定義</span><p>把分散的成功、錯誤與 async completion 統一帶到同一個收尾協定，確保 request 只真正結束一次。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Client abort 與正常完成最後都要取消 timers、執行 cleanup，並決定 connection close 或 keep-alive。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 request count、buffered flags 與 finalize functions 協調多個 callbacks 的共同終點。</p></div></section><section class="foundation-card"><h3>Reference count</h3><div class="foundation-block"><span>白話定義</span><p>用數字表示還有多少未完成工作需要某 object；只有歸零後才能安全釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Main request 啟動兩個 subrequests，必須等兩者都完成才能整體 finalize。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX request count 是 async branches 的 join gate；漏減造成 leak，重複減可能 use-after-free。</p></div></section><section class="foundation-card"><h3>Subrequest</h3><div class="foundation-block"><span>白話定義</span><p>由一個 request 在 NGINX 內部建立的子 request，用同一套 HTTP phase/filter machinery 取得額外內容。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>主頁 response 中的一小段內容由內部 location 生成。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Subrequest 不是新的 client TCP connection；它與 main request 共享部分 context 並受 reference count 管理。</p></div></section><section class="foundation-card"><h3>HTTP keep-alive</h3><div class="foundation-block"><span>白話定義</span><p>完成一個 HTTP request 後不立刻關閉 TCP connection，讓同一 client 之後可在同一條連線上再送 request，省下重新建立 TCP 連線的時間。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>瀏覽器用同一條 connection 先取 HTML，再依序取圖片與 API response。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX finalize 舊 request、清除 request-lifetime state，再把 connection handler 改成等待下一個 request。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section></div>



<p class="chapter-question">為什麼呼叫 finalize 不一定立刻 free request，而 response完成後 connection又如何回到等待下一個 request？</p>

<div class="chapter-meta"><span>難度：進階</span><span>finalization · keep-alive · subrequest</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

串起 return code、reference count、buffered output、subrequest、keep-alive reset與最終 pool destroy。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node active"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-23-response-與-filter-chain"><span>上一站</span><strong>23. Response 與 Filter Chain</strong></a><div class="position-card current"><span>你在這裡</span><strong>24. Finalize、Keep-Alive 與 Subrequest</strong></div><a class="position-card" href="#chapter-25-proxy-pass-從哪裡開始"><span>下一站</span><strong>25. proxy_pass 從哪裡開始</strong></a></div>

本章位於 **Part 4：HTTP Request 的一生**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Async 系統最難的不只是開始工作，而是只結束一次、在所有 child work 完成後結束，並把 transport 留在可重用或可安全關閉的狀態。Finalize 是 request lifecycle 的集中收口。

Use case 是正常 response、error page、subrequest、client abort 與 keep-alive。若多個 callback 都直接 free request，會 double free；若漏掉一次 reference decrement，request 永遠不釋放。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Async 系統最難的不只是開始工作，而是只結束一次、在所有 child work 完成後結束，並把 transport 留在可重用或可安全關閉的狀態。Finalize 是 request lifecycle 的集中收口。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是正常 response、error page、subrequest、client abort 與 keep-alive。若多個 callback 都直接 free request，會 double free；若漏掉一次 reference decrement，request 永遠不釋放。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Request completion protocol」這個責任邊界；接收 handler result、I/O completion、error 或 child completion，交付 cleanup 完成，connection 進 keep-alive/lingering close/close。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 request count、main/subrequest links、cleanup list 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 double finalize、reference leak、response 已送後又改 status、殘留 timer。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Request completion protocol</p></div><div class="contract-card"><span>接收什麼</span><p>handler result、I/O completion、error 或 child completion</p></div><div class="contract-card"><span>產生什麼</span><p>cleanup 完成，connection 進 keep-alive/lingering close/close</p></div><div class="contract-card"><span>狀態由誰保存</span><p>request count、main/subrequest links、cleanup list</p></div><div class="contract-card"><span>主要失敗出口</span><p>double finalize、reference leak、response 已送後又改 status、殘留 timer</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>某 handler 呼叫/觸發 finalize</p></div><div class="flow-step"><span>2</span><p>根據 rc 判斷是否仍有 async work</p></div><div class="flow-step"><span>3</span><p>處理 special response 或 error path</p></div><div class="flow-step"><span>4</span><p>更新 main request count</p></div><div class="flow-step"><span>5</span><p>等待 posted/subrequests 完成</p></div><div class="flow-step"><span>6</span><p>執行 request cleanup</p></div><div class="flow-step"><span>7</span><p>若可 keep-alive，重設 connection handler 等下一 request</p></div><div class="flow-step"><span>8</span><p>否則 lingering close 或直接 close</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
handler result / error
       ↓
finalize_request(r, rc)
       ├─ special response / redirect
       ├─ pending output → writer continuation
       ├─ subrequest/main count not zero → wait
       ├─ keep-alive eligible → reset connection to wait request
       └─ close → cleanup + destroy request pool + close connection
```

## 從零建立心智模型

Finalize 是狀態轉移入口，不等於 `free(r)`。它要解讀 rc、處理 special response、subrequest、postponed output、buffered filters、lingering close、keepalive與 error。只有所有 obligations結束才進到 free。

主 request可能有 subrequests。Subrequest完成後 output需按正確順序併回主請求；main count防止主 request在孩子仍引用 pool/config時被釋放。

Keep-alive成功時銷毀 request pool與 request-specific state，但保留 connection與部分 buffer，把 read handler改成 keepalive/wait request。下一個 HTTP交換會建立全新的 request。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

每個 callback 都直接 free request 會 double free；等到所有 subrequests/async work 完成又需要 join。Reference count 加單一 finalize gate 能讓多分支只收口一次。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>references</code></td><td><code>r-&gt;main-&gt;count</code></td></tr><tr><td><code>retain</code></td><td>建立 subrequest/async work 時增加 completion dependency</td></tr><tr><td><code>finalize</code></td><td><code>ngx_http_finalize_request</code> protocol</td></tr><tr><td>cleanup once</td><td>request pool cleanup 後切 keepalive/lingering close/close</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_request.c`，官方 `release-1.31.5` 第 2743–2792 行

```c
ngx_http_finalize_request(ngx_http_request_t *r, ngx_int_t rc)
{
    ngx_connection_t          *c;
    ngx_http_request_t        *pr;
    ngx_http_core_loc_conf_t  *clcf;

    c = r->connection;

    ngx_log_debug5(NGX_LOG_DEBUG_HTTP, c->log, 0,
                   "http finalize request: %i, \"%V?%V\" a:%d, c:%d",
                   rc, &r->uri, &r->args, r == c->data, r->main->count);

    if (rc == NGX_DONE) {
        ngx_http_finalize_connection(r);
        return;
    }

    if (rc == NGX_OK && r->filter_finalize) {
        c->error = 1;
    }

    if (rc == NGX_DECLINED) {
        r->content_handler = NULL;
        r->write_event_handler = ngx_http_core_run_phases;
        ngx_http_core_run_phases(r);
        return;
    }

    if (r != r->main && r->post_subrequest) {
        rc = r->post_subrequest->handler(r, r->post_subrequest->data, rc);
    }

    if (rc == NGX_ERROR
        || rc == NGX_HTTP_REQUEST_TIME_OUT
        || rc == NGX_HTTP_CLIENT_CLOSED_REQUEST
        || c->error)
    {
        if (ngx_http_post_action(r) == NGX_OK) {
            return;
        }

        ngx_http_terminate_request(r, rc);
        return;
    }

    if (rc >= NGX_HTTP_SPECIAL_RESPONSE
        || rc == NGX_HTTP_CREATED
        || rc == NGX_HTTP_NO_CONTENT)
    {
        if (rc == NGX_HTTP_CLOSE) {
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Module/phase/filter以 rc呼叫或觸發 <code>ngx_http_finalize_request</code>。</p></div><div class="source-step"><span>2</span><p>依 rc決定 special response、internal redirect、close或正常完成。</p></div><div class="source-step"><span>3</span><p>若 request buffered，設定 writer handler等待剩餘 output。</p></div><div class="source-step"><span>4</span><p>處理 subrequest/postponed chain與 main count。</p></div><div class="source-step"><span>5</span><p>符合 keepalive條件則 <code>ngx_http_set_keepalive</code>；否則 close request/connection。</p></div><div class="source-step"><span>6</span><p><code>ngx_http_free_request</code> 跑 cleanup、log phase並 destroy pool。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Finalize 不一定立即 free；先看 rc、count 與 posted requests。</p></div><div class="microscope-card"><span>2</span><p>Headers 已送出後 error path 不能任意換 status。</p></div><div class="microscope-card"><span>3</span><p>Keep-alive 重用 connection，不重用已 finalize 的 request object。</p></div><div class="microscope-card"><span>4</span><p>所有 timers/events 在 owner cleanup 前必須取消或轉移。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- `ngx_http_finalize_request` 不等於立即 free；rc 與 count 決定後續。
- Headers 已送出後，錯誤處理不能再安全改 status/header。
- Keep-alive 是 connection lifecycle 延續，不是 request object 重用。
- Cleanup handler 可能關 file、釋放外部 library resource；pool free 本身不會替你做這些 side effects。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_request.c#L2743`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L2743) · [`src/http/ngx_http_request.c#L3352`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L3352) · [`src/http/ngx_http_request.c#L3981`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L3981)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Finalize idempotency很難。不同 event可能幾乎同時看到 client close、upstream timeout與write error；flags/reference count需確保清理只執行一次，晚到 callback被安全忽略。

Lingering close在回應後仍讀掉 client剩餘 request body一段時間，避免直接 close造成 RST或讓未讀資料影響連線語意。它是 transport correctness與資源上限的折衷。

Keep-alive能節省 handshake，但 idle connections佔 fd與memory。Timeout、requests-per-connection與reload draining共同決定資源邊界。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Single completion gate</h3><p>所有成功失敗路徑集中通過 finalize protocol。</p></div><div class="pattern-card"><h3>Reference-counted join</h3><p>多個 async/subrequest 分支在 count 歸零時會合。</p></div><div class="pattern-card"><h3>Object recycling</h3><p>request 結束後 connection 可切回 keep-alive state。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 追蹤一個正常200、一個404與一個upstream timeout的 finalize分支。
2. 建立慢 client讓 output buffered，觀察 finalize後 request仍存活。
3. 同一 keep-alive connection送兩個 request，比較 request pool位址。
4. 建立 subrequest功能，觀察 main count與postponed output。

## 常見誤解與失敗模式

- 把 finalize當同步 destructor。
- Keep-alive重用 request-specific ctx，造成跨請求資料洩漏。
- 多個錯誤event重複 cleanup/free。

## 可以帶走的 Coding／CS 能力

- 理解 async finalization、idempotent cleanup與reference counting。
- 區分 transport reuse與transaction lifetime。
- 分析 parent/child task completion與ordered output。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Client-side HTTP 生命週期完成；Part 5 放大 `proxy_pass` 之後與 backend 溝通的另一半。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Finalize 為何可能返回後 request仍存在？</summary>

尚有 buffered output、subrequest、AIO/thread task、upstream cleanup或 reference count；finalize只推進到目前安全階段。

</details>

<details class="qa" markdown="1">
<summary>Q2. Keep-alive重用了什麼、沒有重用什麼？</summary>

重用TCP connection、fd、events與部分connection buffer；每次HTTP request物件、pool、module ctx與多數headers必須重新建立。

</details>

<details class="qa" markdown="1">
<summary>Q3. 為什麼需要 lingering close？</summary>

若client尚有未讀body，立即close可能產生RST或丟掉已送response；短暫讀棄剩餘資料可更乾淨結束，但需timeout防資源耗盡。

</details>

<details class="qa" markdown="1">
<summary>Q4. Subrequest為何不能完成就直接把body送socket？</summary>

主/子輸出有順序與嵌套關係，需postpone chain協調；直接送會打亂response。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如何避免 double free？</summary>

以單一owner、finalized/closed flags、reference count、取消timers/events與清空cleanup pointer建立一次性狀態轉移。

</details>

<details class="qa" markdown="1">
<summary>Q6. Requests-per-connection limit有何價值？</summary>

即使keep-alive正常，定期重建connection可限制長期memory fragmentation、config generation滯留與單client資源占用。

</details>

---
