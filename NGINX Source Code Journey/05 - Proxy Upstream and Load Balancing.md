---
title: "Proxy、Upstream 與負載均衡"
part: 5
source_baseline: release-1.31.5
---

# Part 5　Proxy、Upstream 與負載均衡

回到最初問題：`proxy_pass` 如何建立 backend request、選 peer、非阻塞連線、重試、重用連線並控制快慢兩端。

# 第 25 章　proxy_pass 從哪裡開始

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>`proxy_pass`</h3><div class="foundation-block"><span>白話定義</span><p>告訴 NGINX：這個 location 的 content 不在本機產生，而要轉成另一個 HTTP request 送往 upstream。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>location /api/ { proxy_pass http://app; }</code> 將 <code>/api/</code> requests 交給 backend group。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Proxy module 處理 URI、headers、body、timeouts 與 buffering，再呼叫通用 upstream framework。</p></div></section><section class="foundation-card"><h3>Reverse proxy（反向代理）</h3><div class="foundation-block"><span>白話定義</span><p>Client 只連到代理伺服器；代理再代表 client 連到內部 backend。Client 不需要知道 backend 的位址，也不會直接與它建立連線。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>瀏覽器請求 <code>shop.example.com</code>，NGINX 收到後轉給內網的 <code>10.0.0.8:8080</code>，再把結果送回瀏覽器。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 client connection 與 upstream connection 之間轉換、緩衝並轉送 HTTP 資料。</p></div></section><section class="foundation-card"><h3>Upstream</h3><div class="foundation-block"><span>白話定義</span><p>從 NGINX 角度看出去的 backend 交易或 backend 群組。它不是 client 連進來的那條 connection。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>一次 client request 可能建立一條 upstream connection 到 <code>app-2:8080</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_http_upstream_t</code> 保存 peer selection、connect/send/read state、retry、buffering 與 timing。</p></div></section><section class="foundation-card"><h3>Protocol adapter</h3><div class="foundation-block"><span>白話定義</span><p>把共用 transport state machine 與特定協定的編碼／解析分離。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>HTTP proxy、FastCGI 與 memcached 都需要 connect/retry/timeout，但 request bytes 與 response parser 不同。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX upstream core 管 async transport；各 module 提供 create_request、process_header 等 callbacks。</p></div></section><section class="foundation-card"><h3>Buffering 與 streaming</h3><div class="foundation-block"><span>白話定義</span><p>Buffering 先暫存資料以吸收兩端速度差；streaming 則資料一到便逐段往下游傳，不等待完整內容。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>小 response 可留在 memory；大 response 可能落 temporary file；即時事件適合 streaming。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 module/config 在 latency、memory、disk I/O 與 backend connection 占用之間取捨。</p></div></section></div>



<p class="chapter-question">Location 命中 `proxy_pass` 後，proxy module 如何把 client request 轉成一個 upstream request？</p>

<div class="chapter-meta"><span>難度：中階</span><span>proxy module · content handler · request transformation</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

分開設定期與請求期，理解 content handler、complex value、header script與 upstream callback contract。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-24-finalize-keep-alive-與-subrequest"><span>上一站</span><strong>24. Finalize、Keep-Alive 與 Subrequest</strong></a><div class="position-card current"><span>你在這裡</span><strong>25. proxy_pass 從哪裡開始</strong></div><a class="position-card" href="#chapter-26-upstream-state-machine"><span>下一站</span><strong>26. Upstream State Machine</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

`proxy_pass` 看似一行設定，背後要把 client request 轉換成 backend 可接受的 request，決定 URI rewrite、headers、body forwarding、buffering、timeouts 與 upstream group。Proxy module 是 HTTP configuration、content handler 與通用 upstream framework 的接合層。

Use case 是把 `/api/` 轉發到 application servers，同時重寫 Host、加入 forwarding headers。Core upstream 不知道 HTTP proxy request 長什麼樣，proxy module 透過 callbacks 提供 protocol-specific 行為。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p><code>proxy_pass</code> 看似一行設定，背後要把 client request 轉換成 backend 可接受的 request，決定 URI rewrite、headers、body forwarding、buffering、timeouts 與 upstream group。Proxy module 是 HTTP configuration、content handler 與通用 upstream framework 的接合層。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是把 <code>/api/</code> 轉發到 application servers，同時重寫 Host、加入 forwarding headers。Core upstream 不知道 HTTP proxy request 長什麼樣，proxy module 透過 callbacks 提供 protocol-specific 行為。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「HTTP proxy adapter」這個責任邊界；接收 已完成 routing 的 client request + proxy location conf，交付 初始化完成的 <code>ngx_http_upstream_t</code> 與 backend request buffers。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 proxy module ctx/conf + request pool 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 URI 拼接錯誤、hop-by-hop header 洩漏、body 不可重播、callback contract 錯誤。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>HTTP proxy adapter</p></div><div class="contract-card"><span>接收什麼</span><p>已完成 routing 的 client request + proxy location conf</p></div><div class="contract-card"><span>產生什麼</span><p>初始化完成的 <code>ngx_http_upstream_t</code> 與 backend request buffers</p></div><div class="contract-card"><span>狀態由誰保存</span><p>proxy module ctx/conf + request pool</p></div><div class="contract-card"><span>主要失敗出口</span><p>URI 拼接錯誤、hop-by-hop header 洩漏、body 不可重播、callback contract 錯誤</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>Config parser 編譯 proxy_pass URL/variables</p></div><div class="flow-step"><span>2</span><p>location content handler 進 proxy module</p></div><div class="flow-step"><span>3</span><p>建立 upstream object</p></div><div class="flow-step"><span>4</span><p>填入 create_request/reinit/process_header 等 callbacks</p></div><div class="flow-step"><span>5</span><p>計算 backend URI 與 headers</p></div><div class="flow-step"><span>6</span><p>建立 request buffer chain</p></div><div class="flow-step"><span>7</span><p>呼叫通用 upstream init</p></div><div class="flow-step"><span>8</span><p>後續由 upstream state machine 接管</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

`proxy_pass` 有兩個世界。設定期解析 URL、upstream group、URI replacement與含變數的 complex value，並把 location content handler 設為 proxy handler。請求期 handler 不重新解釋整段設定，而是讀取已編譯 loc config。

Proxy module先建立通用 `ngx_http_upstream_t`，再填入 protocol-specific callbacks：如何產生 backend request、如何解析 response header、如何 reinit重試、如何 finalize。Upstream core負責連線、timer、buffer、retry與事件派發；proxy module負責 HTTP-to-HTTP 語意。

Client body可能必須先讀完。Proxy handler註冊 body post handler，等 body ready後才進 `ngx_http_upstream_init`；這延續上一章的 continuation pattern。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

通用 upstream engine 不應知道 HTTP proxy request 如何拼 URI/header。Proxy module 以 callbacks 提供 encode/decode 細節，讓 core 只處理 connect、timeout、retry 與搬運。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>UpstreamAdapter</code></td><td>proxy module 注入 upstream 的 callback set</td></tr><tr><td><code>create_request</code></td><td><code>ngx_http_proxy_create_request</code></td></tr><tr><td><code>process_header</code></td><td><code>ngx_http_proxy_process_status_line/header</code></td></tr><tr><td>wire bytes</td><td><code>u-&gt;request_bufs</code> backend-side buffer chain</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/modules/ngx_http_proxy_module.c`，官方 `release-1.31.5` 第 876–923 行

```c
ngx_http_proxy_handler(ngx_http_request_t *r)
{
    ngx_int_t                    rc;
    ngx_http_upstream_t         *u;
    ngx_http_proxy_ctx_t        *ctx;
    ngx_http_proxy_loc_conf_t   *plcf;
#if (NGX_HTTP_CACHE)
    ngx_http_proxy_main_conf_t  *pmcf;
#endif

    plcf = ngx_http_get_module_loc_conf(r, ngx_http_proxy_module);

#if (NGX_HTTP_V2)
    if (plcf->http_version == NGX_HTTP_VERSION_20) {
        return ngx_http_proxy_v2_handler(r);
    }
#endif

    if (ngx_http_upstream_create(r) != NGX_OK) {
        return NGX_HTTP_INTERNAL_SERVER_ERROR;
    }

    ctx = ngx_pcalloc(r->pool, sizeof(ngx_http_proxy_ctx_t));
    if (ctx == NULL) {
        return NGX_HTTP_INTERNAL_SERVER_ERROR;
    }

    ngx_http_set_ctx(r, ctx, ngx_http_proxy_module);

    u = r->upstream;

    if (plcf->proxy_lengths == NULL) {
        ctx->vars = plcf->vars;
        u->schema = plcf->vars.schema;
#if (NGX_HTTP_SSL)
        u->ssl = plcf->ssl;
#endif

    } else {
        if (ngx_http_proxy_eval(r, ctx, plcf) != NGX_OK) {
            return NGX_HTTP_INTERNAL_SERVER_ERROR;
        }
    }

    u->output.tag = (ngx_buf_tag_t) &ngx_http_proxy_module;

    u->conf = &plcf->upstream;

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>proxy_pass</code> directive callback在 config-time決定 static upstream或編譯 variable script。</p></div><div class="source-step"><span>2</span><p>HTTP phase engine進入 location content handler。</p></div><div class="source-step"><span>3</span><p>Proxy handler配置 module ctx與 <code>ngx_http_upstream_t</code>。</p></div><div class="source-step"><span>4</span><p>填 <code>create_request/reinit_request/process_header/abort/finalize</code> 等 callback。</p></div><div class="source-step"><span>5</span><p>設定 buffering、schema、resolved target與 headers；讀 body後啟動 upstream core。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Proxy URI replacement 要用有/無 trailing slash 的案例推演。</p></div><div class="microscope-card"><span>2</span><p>Hop-by-hop headers 應刪除或重建，不能盲目複製 client headers。</p></div><div class="microscope-card"><span>3</span><p>Protocol callback 配置在 <code>ngx_http_upstream_t</code> 哪些欄位。</p></div><div class="microscope-card"><span>4</span><p>Variables 可能讓 upstream URL/headers 到 runtime 才確定。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Trailing slash 會影響 proxy_pass URI replacement，必須用具體例子推演。
- 不要原樣轉發 hop-by-hop headers；proxy module 會重建部分 headers。
- `create_request` 產生的是 backend-side bytes，不是修改 client buffer。
- 同一 proxy config 可能因 variables 在 runtime 決定不同 upstream/URI。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
int proxy_handler(request_t *r) {
    upstream_t *u = upstream_create(r);

    u->create_request   = proxy_create_request;
    u->process_header   = proxy_process_status_and_headers;
    u->reinit_request   = proxy_reinit_for_retry;
    u->finalize_request = proxy_finalize;
    u->conf             = proxy_location_config(r);

    return read_client_body(r, upstream_init);
}
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/modules/ngx_http_proxy_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_proxy_module.c#L1) · [`src/http/ngx_http_upstream.c#L508`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L508) · [`src/http/ngx_http_script.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_script.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

URI replacement是常見陷阱：`proxy_pass` 是否帶 URI、location 是 prefix/regex/named、rewrite是否改過 URI，都會影響送往 backend的 path。理解時要同時追 `r->uri`、`r->unparsed_uri` 與 proxy vars，而不是背一句規則。

Header生成常使用 script engine，把常數與 variables預編譯成 length/value programs。這讓每個 request可組合 Host、X-Forwarded-* 等欄位，而不必重新 parse template。

Hop-by-hop headers不能盲目轉發；proxy module需要重建 request line與 headers，並處理 body framing、connection reuse和 upgrade。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Adapter</h3><p>proxy module 把 HTTP proxy 協定接到通用 upstream engine。</p></div><div class="pattern-card"><h3>Template method via callbacks</h3><p>core 定義流程，module 提供建立／解析協定細節。</p></div><div class="pattern-card"><h3>Configuration compilation</h3><p>複雜 variable/URI script 在啟動時預先編譯。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 為 static `proxy_pass` 與含變數版本各做一個 location，比較 config/runtime解析。
2. 在 proxy handler印出 `r->uri`、`unparsed_uri` 與實際 upstream request line。
3. 修改 Host、Connection、X-Forwarded-For，找出 header script輸出。
4. POST body時觀察 proxy handler先返回、body post handler再啟動 upstream。

## 常見誤解與失敗模式

- 把 directive parser與 request handler當同一條執行路徑。
- 直接複製全部 client headers到 backend，包含 hop-by-hop欄位。
- 只看 `$request_uri` 推理 proxy path，忽略 rewrite與 replacement規則。

## 可以帶走的 Coding／CS 能力

- 理解 protocol adapter與通用 transport framework的分工。
- 把 template/variable expression預編譯成 runtime bytecode。
- 設計安全的 request transformation與header ownership。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Proxy module 準備好 protocol-specific callbacks 後，下一章由通用 upstream state machine 推進整次 backend 交易。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Proxy module和upstream core如何分工？</summary>

Proxy module懂HTTP request/response格式與設定語意；upstream core提供peer選擇、connect、timer、retry、buffering與事件狀態機。兩者以callbacks連接。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為何 `proxy_pass` 的很多工作在config-time做？</summary>

URL、固定headers、變數program與upstream reference對一代設定不變；預編譯可降低每request parse與allocation。

</details>

<details class="qa" markdown="1">
<summary>Q3. 含變數的 upstream 有何額外成本與風險？</summary>

每request需評估字串，可能需要runtime DNS resolver；target cardinality、DNS timeout、cache與SSRF policy也更複雜。

</details>

<details class="qa" markdown="1">
<summary>Q4. 為什麼不能原樣轉發 Connection header？</summary>

它描述hop-by-hop連線選項，不是end-to-end metadata；不同兩段connection有各自keepalive/upgrade狀態，proxy需重建。

</details>

<details class="qa" markdown="1">
<summary>Q5. Client body為何讓proxy handler成為非同步流程？</summary>

Body可能尚未到齊，handler需先啟動讀取並返回；完成callback才能建立/送完整upstream request。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何驗證URI replacement而不靠記憶？</summary>

用backend echo實際method/path/headers，組合prefix、regex、rewrite與有/無URI的proxy_pass，對照 `r->uri` trace。

</details>

---

# 第 26 章　Upstream State Machine

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Upstream</h3><div class="foundation-block"><span>白話定義</span><p>從 NGINX 角度看出去的 backend 交易或 backend 群組。它不是 client 連進來的那條 connection。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>一次 client request 可能建立一條 upstream connection 到 <code>app-2:8080</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_http_upstream_t</code> 保存 peer selection、connect/send/read state、retry、buffering 與 timing。</p></div></section><section class="foundation-card"><h3>Peer</h3><div class="foundation-block"><span>白話定義</span><p>一個可被選來連線的遠端 endpoint，通常是一台 backend 的 IP/port 加上權重與健康狀態。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Upstream group 有 app-1、app-2、app-3；某次 request 選 app-2 作為 peer。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Balancer 的 get callback 選 peer；free callback 回報 success/failure，讓後續選擇調整。</p></div></section><section class="foundation-card"><h3>State machine（狀態機）</h3><div class="foundation-block"><span>白話定義</span><p>把流程表示成有限狀態與允許的轉移。遇到等待時保存目前 state；事件到來後從該 state 繼續。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>CONNECTING → SENDING → READING_HEADER → STREAMING_BODY → DONE。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 常把 state 分散在 struct fields 與可替換 callbacks，而不是寫成一個巨大 switch。</p></div></section><section class="foundation-card"><h3>Callback（回呼函式）</h3><div class="foundation-block"><span>白話定義</span><p>現在先把『未來某件事發生時要做什麼』存成函式；事件發生後，由框架呼叫它。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Socket 現在沒有資料時不等待；先記住 <code>on_readable</code>，有資料可讀時再執行。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_event_t.handler</code> 保存下一次 read、write 或 timer event 到來時要執行的函式。</p></div></section><section class="foundation-card"><h3>Protocol adapter</h3><div class="foundation-block"><span>白話定義</span><p>把共用 transport state machine 與特定協定的編碼／解析分離。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>HTTP proxy、FastCGI 與 memcached 都需要 connect/retry/timeout，但 request bytes 與 response parser 不同。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX upstream core 管 async transport；各 module 提供 create_request、process_header 等 callbacks。</p></div></section></div>



<p class="chapter-question">從建立 upstream 到收到完整 response，中間有哪些可暫停、重試與切換 callback 的狀態？</p>

<div class="chapter-meta"><span>難度：進階</span><span>upstream · state machine · callback interface</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

掌握 `ngx_http_upstream_t` 的通用狀態機與 module callbacks，能預測每個 I/O 邊界。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-25-proxy-pass-從哪裡開始"><span>上一站</span><strong>25. proxy_pass 從哪裡開始</strong></a><div class="position-card current"><span>你在這裡</span><strong>26. Upstream State Machine</strong></div><a class="position-card" href="#chapter-27-從-nginx-非阻塞連線到-backend"><span>下一站</span><strong>27. 從 NGINX 非阻塞連線到 Backend</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Backend 交易包含選 peer、connect、send request、read header、read body、retry 與 finalize；每一步都可能因 I/O 暫停。`ngx_http_upstream_t` 把這些狀態與 protocol callbacks 集中，避免每個 proxy-like module 重寫整套 async transport。

Use case 是 HTTP proxy、FastCGI、memcached 等不同協定共享 connect、timeout、buffering、retry 與觀測框架，只替換 request encoding 與 response parsing。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Backend 交易包含選 peer、connect、send request、read header、read body、retry 與 finalize；每一步都可能因 I/O 暫停。<code>ngx_http_upstream_t</code> 把這些狀態與 protocol callbacks 集中，避免每個 proxy-like module 重寫整套 async transport。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 HTTP proxy、FastCGI、memcached 等不同協定共享 connect、timeout、buffering、retry 與觀測框架，只替換 request encoding 與 response parsing。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Generic upstream transaction」這個責任邊界；接收 client request + module callbacks + upstream conf，交付 backend response pipeline 或可分類的 failure。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 upstream object、peer connection、state timings、event pipe 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 connect/send/read timeout、client abort、peer failure、retry state 未重設。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Generic upstream transaction</p></div><div class="contract-card"><span>接收什麼</span><p>client request + module callbacks + upstream conf</p></div><div class="contract-card"><span>產生什麼</span><p>backend response pipeline 或可分類的 failure</p></div><div class="contract-card"><span>狀態由誰保存</span><p>upstream object、peer connection、state timings、event pipe</p></div><div class="contract-card"><span>主要失敗出口</span><p>connect/send/read timeout、client abort、peer failure、retry state 未重設</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>create upstream object</p></div><div class="flow-step"><span>2</span><p>module create_request 產生 backend bytes</p></div><div class="flow-step"><span>3</span><p>初始化 peer selection 與 attempt state</p></div><div class="flow-step"><span>4</span><p>non-blocking connect</p></div><div class="flow-step"><span>5</span><p>writable 後送 request/body</p></div><div class="flow-step"><span>6</span><p>readable 後 process_header</p></div><div class="flow-step"><span>7</span><p>選 buffered event pipe 或 non-buffered streaming</p></div><div class="flow-step"><span>8</span><p>成功 finalize/keepalive，失敗則判斷 next peer</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

`ngx_http_upstream_t` 是client request代理到backend所需的協調物件。它保存 peer connection、module callbacks、request buffers、response buffer、event pipe、conf、state timings、cache與 read/write continuations。

Upstream socket的 read/write event都先進 `ngx_http_upstream_handler`，再分派到 `u->read_event_handler` 或 `u->write_event_handler`。Connect階段、send階段、read-header階段、body階段只需替換第二層 continuation。

每個狀態都可能遇到 timeout、client abort、peer failure或 `NGX_AGAIN`。理解 upstream不能只畫成功路徑；要把 retry邊與 finalize邊一起畫出來。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

把 upstream 寫成一個 blocking 函式會在 connect/read 等待時卡住 worker。顯式 state machine 把每個 readiness event 映射成一個 transition。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Upstream.state</code></td><td><code>ngx_http_upstream_t</code> 中的 buffers/handlers/flags 所表示的階段</td></tr><tr><td><code>advance</code></td><td>upstream read/write event handlers</td></tr><tr><td>event names</td><td>connect writable、send complete、header readable、body EOF</td></tr><tr><td>transition table</td><td>替換 <code>u-&gt;read_event_handler</code>／<code>write_event_handler</code></td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_upstream.c`，官方 `release-1.31.5` 第 1316–1357 行

```c
ngx_http_upstream_handler(ngx_event_t *ev)
{
    ngx_connection_t     *c;
    ngx_http_request_t   *r;
    ngx_http_upstream_t  *u;

    c = ev->data;
    r = c->data;

    u = r->upstream;
    c = r->connection;

    ngx_http_set_log_request(c->log, r);

    ngx_log_debug2(NGX_LOG_DEBUG_HTTP, c->log, 0,
                   "http upstream request: \"%V?%V\"", &r->uri, &r->args);

    if (ev->delayed && ev->timedout) {
        ev->delayed = 0;
        ev->timedout = 0;
    }

    if (ev->write) {
        u->write_event_handler(r, u);

    } else {
        u->read_event_handler(r, u);
    }

    ngx_http_run_posted_requests(c);
}


static void
ngx_http_upstream_rd_check_broken_connection(ngx_http_request_t *r)
{
    ngx_http_upstream_check_broken_connection(r, r->connection->read);
}


static void
ngx_http_upstream_wr_check_broken_connection(ngx_http_request_t *r)
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_http_upstream_create</code> 配置並清零通用 upstream object。</p></div><div class="source-step"><span>2</span><p><code>ngx_http_upstream_init_request</code> 處理cache、client abort監視與create_request callback。</p></div><div class="source-step"><span>3</span><p>初始化 peer selection與state timing，再呼叫 connect。</p></div><div class="source-step"><span>4</span><p>Upstream connection events經共用handler分派 send/read continuations。</p></div><div class="source-step"><span>5</span><p>Header完成後選 buffered/non-buffered body處理。</p></div><div class="source-step"><span>6</span><p>成功或失敗皆進 upstream finalize；可重試時先 reinit再選下一 peer。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先列出 handler replacement timeline，再看大函式內部。</p></div><div class="microscope-card"><span>2</span><p>Attempt timings 每 retry 一次就新增 state record。</p></div><div class="microscope-card"><span>3</span><p>Protocol reinit 是 retry transition 的必要部分。</p></div><div class="microscope-card"><span>4</span><p>Client abort、timer、peer error 都可從任意 state 導向 next/finalize。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 先追 `u->read_event_handler`/`write_event_handler` 何時改變，再讀各大函式。
- 一次 client request 可有多個 upstream states，代表 retry 歷史。
- Reinit callback 必須重設 parser與request buffers，不能只換 socket。
- Client abort 後是否繼續取決於 cache/store 等 policy，不是永遠立即停止。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
void upstream_event(event_t *ev) {
    connection_t *c = ev->data;
    request_t *r = c->data;
    upstream_t *u = r->upstream;

    if (ev->write)
        u->write_continuation(r, u);
    else
        u->read_continuation(r, u);
}
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_upstream.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.h#L1) · [`src/http/ngx_http_upstream.c#L508`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L508) · [`src/http/ngx_http_upstream.c#L543`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L543)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

State timings通常按每次嘗試記錄：connect time、header time、response time、status與peer name。一次client request可有多個upstream states，對應 retry歷史；觀測 `$upstream_*` 時要理解逗號/分隔值不是單一backend。

Client abort監視與upstream生命周期耦合。若response不可cache且client已離開，繼續讀backend通常沒有價值；但cache fill/store等情境可能選擇繼續。

Reinit callback讓protocol module重設parser與request buffers以重試，通用core不用知道FastCGI、proxy或memcached的內部格式。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>State machine with pluggable protocol</h3><p>transport 狀態固定，協定細節由 callback 注入。</p></div><div class="pattern-card"><h3>Second-level dispatch</h3><p>共用 socket handler 再分派 <code>u-&gt;read/write_event_handler</code>。</p></div><div class="pattern-card"><h3>Attempt history</h3><p>每次 peer 嘗試各自記錄 status 與 timing。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 用debug log把一次成功upstream的continuation切換列成時間線。
2. 讓backend connect慢、header慢、body慢，分別觸發三種等待狀態。
3. 讓第一次peer失敗、第二次成功，檢查upstream states陣列。
4. 中途讓client斷線，比較cacheable與non-cacheable行為。

## 常見誤解與失敗模式

- 只追函式call stack，忽略第二層read/write continuation。
- 把 `$upstream_response_time` 當永遠只有一個值。
- 重試時只換socket，未重設protocol parser與request body狀態。

## 可以帶走的 Coding／CS 能力

- 設計通用async transport core＋protocol callbacks。
- 為多次attempt建立結構化timing/diagnostic state。
- 分析cancel、retry、cache fill之間的ownership政策。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

State machine 的第一個 I/O 難點是 connect；下一章拆開 EINPROGRESS 到連線確認。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼 upstream read/write event使用共同入口？</summary>

共同入口處理request取得、timeout/error等通用工作，再由upstream內函式指標分派當前階段，減少直接替換底層socket handler。

</details>

<details class="qa" markdown="1">
<summary>Q2. 一次request為何有多個upstream state？</summary>

每次peer attempt都需獨立記錄地址、status與各階段時間；retry後保留歷史才能觀測真正延遲與失敗。

</details>

<details class="qa" markdown="1">
<summary>Q3. Protocol module為何需要reinit callback？</summary>

重試新peer時HTTP/FastCGI等parser、buffer cursor與request generation state需回到初始狀態，通用core無法安全猜測。

</details>

<details class="qa" markdown="1">
<summary>Q4. Client斷線後為何有時仍讀upstream？</summary>

若正在建立可供其他request使用的cache/store結果，繼續可能有價值；普通不可cache response則通常終止以節省資源。

</details>

<details class="qa" markdown="1">
<summary>Q5. 哪幾個地方最常返回 `NGX_AGAIN`？</summary>

Non-blocking connect未完成、backend send buffer滿、response header/body尚未到、client output送不完；每處都需保存不同continuation。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何判斷upstream卡在哪個階段？</summary>

結合connect/header/response timing、current read/write handler、event timer、debug log與socket state，而不是只看總response time。

</details>

---

# 第 27 章　從 NGINX 非阻塞連線到 Backend

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>TCP handshake 與 connect</h3><div class="foundation-block"><span>白話定義</span><p>TCP 連線建立前，雙方要交換控制封包確認彼此可達與初始狀態；這段時間可能成功、拒絕或 timeout。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend port 沒開可能快速回 connection refused；封包被丟棄則可能長時間沒有答案。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 使用 non-blocking connect，不讓 worker 等待 handshake，結果由後續 write readiness 與 socket error 確認。</p></div></section><section class="foundation-card"><h3>Non-blocking I/O 與 EAGAIN</h3><div class="foundation-block"><span>白話定義</span><p>Non-blocking socket 在目前不能前進時立即返回，而不是讓整個 worker 睡在 <code>read()</code> 或 <code>write()</code> 裡。EAGAIN 表示『現在沒有，之後再試』。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Client 尚未送下一段 body 時，<code>recv()</code> 回 EAGAIN；worker 去處理別的 connections。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 保存 parser/output state，等待 epoll 再次通知 readiness 後由 callback 繼續。</p></div></section><section class="foundation-card"><h3>EINPROGRESS 與 writable</h3><div class="foundation-block"><span>白話定義</span><p>Non-blocking <code>connect()</code> 回 EINPROGRESS 表示尚未完成，不是成功也不是失敗。之後 writable 只表示結果可查。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>門鈴已按下但屋主尚未回應；燈亮起只表示現在可以查看結果，不保證對方接受。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 write event 到來後讀 <code>SO_ERROR</code>，判斷 connect 成功或取得真正 error。</p></div></section><section class="foundation-card"><h3>Readiness（可前進狀態）</h3><div class="foundation-block"><span>白話定義</span><p>Readiness 只表示某個 I/O 操作現在『可能取得進展』，不表示完整 request 已抵達或整個 response 已送完。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Readable 可能只有 3 bytes、EOF（對方已關閉）或 error；writable 可能只能再送一小段。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Epoll 回報 readiness 後，NGINX 的 handler（回呼函式）仍要呼叫 <code>recv()</code>／<code>send()</code>；EAGAIN 表示這次已無法再前進，應回 event loop 等下次通知。</p></div></section></div>



<p class="chapter-question">Non-blocking `connect()` 回 EINPROGRESS 之後，誰在什麼時候確認連線成功？</p>

<div class="chapter-meta"><span>難度：進階</span><span>non-blocking connect · peer connection · timeout</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 peer callback、connect return codes、write readiness、SO_ERROR、connect timeout與socket pool。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-26-upstream-state-machine"><span>上一站</span><strong>26. Upstream State Machine</strong></a><div class="position-card current"><span>你在這裡</span><strong>27. 從 NGINX 非阻塞連線到 Backend</strong></div><a class="position-card" href="#chapter-28-smooth-weighted-round-robin"><span>下一站</span><strong>28. Smooth Weighted Round Robin</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Blocking `connect()` 可能等待 TCP handshake；event-driven worker 不能停住。Non-blocking connect 通常回 EINPROGRESS，表示結果尚未知，NGINX 必須等待 socket writable，再用 socket error 狀態確認成功或失敗。

Use case 是 backend 延遲、拒絕或網路黑洞。Writable 不保證成功；它只表示 connect 已有結果可檢查。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Blocking <code>connect()</code> 可能等待 TCP handshake；event-driven worker 不能停住。Non-blocking connect 通常回 EINPROGRESS，表示結果尚未知，NGINX 必須等待 socket writable，再用 socket error 狀態確認成功或失敗。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 backend 延遲、拒絕或網路黑洞。Writable 不保證成功；它只表示 connect 已有結果可檢查。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Non-blocking peer connection」這個責任邊界；接收 選定 peer address + connect timeout，交付 connected upstream socket 或分類 failure。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 <code>ngx_peer_connection_t</code>、write event、timer 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 EINPROGRESS、ECONNREFUSED、timeout、stale peer state、fd leak。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Non-blocking peer connection</p></div><div class="contract-card"><span>接收什麼</span><p>選定 peer address + connect timeout</p></div><div class="contract-card"><span>產生什麼</span><p>connected upstream socket 或分類 failure</p></div><div class="contract-card"><span>狀態由誰保存</span><p><code>ngx_peer_connection_t</code>、write event、timer</p></div><div class="contract-card"><span>主要失敗出口</span><p>EINPROGRESS、ECONNREFUSED、timeout、stale peer state、fd leak</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>從 load balancer 取得 peer</p></div><div class="flow-step"><span>2</span><p>socket 並設 non-blocking</p></div><div class="flow-step"><span>3</span><p>呼叫 connect</p></div><div class="flow-step"><span>4</span><p>立即成功則進 send request</p></div><div class="flow-step"><span>5</span><p>EINPROGRESS 則安裝 connect handler/timer</p></div><div class="flow-step"><span>6</span><p>write event 到來後讀 <code>SO_ERROR</code></p></div><div class="flow-step"><span>7</span><p>成功切換 send handler</p></div><div class="flow-step"><span>8</span><p>失敗 free peer 並交 retry policy</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

Peer selection先填 `ngx_peer_connection_t` 的 sockaddr/name/get/free callbacks。`ngx_event_connect_peer` 建socket、設non-blocking、套socket options並呼叫 connect。

EINPROGRESS不是失敗；它表示三向交握尚未完成。NGINX把 upstream connection的read/write handler設好，write event加 connect timeout，回到loop。可寫通知到來後需檢查 `SO_ERROR`，因為可寫也可能表示connect失敗。

Backend connection有獨立小pool，因為成功後可能被 upstream keepalive cache保留，生命週期超過單一request。Request資料仍不能放進該pool後被錯誤重用。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Non-blocking `connect()` 的『正在進行』不是失敗；socket writable 也不保證成功。完成階段必須讀 socket error，才能區分 connected 與 refused。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>connect_ex</code></td><td><code>connect()</code> 與 <code>NGX_AGAIN</code>/EINPROGRESS</td></tr><tr><td>EVENT_WRITE</td><td>upstream connect write event</td></tr><tr><td><code>SO_ERROR</code></td><td><code>ngx_http_upstream_test_connect</code> 類確認</td></tr><tr><td>timeout</td><td>connect event timer</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/event/ngx_event_connect.c`，官方 `release-1.31.5` 第 21–70 行

```c
ngx_event_connect_peer(ngx_peer_connection_t *pc)
{
    int                rc, type, value;
#if (NGX_HAVE_IP_BIND_ADDRESS_NO_PORT || NGX_LINUX)
    in_port_t          port;
#endif
    ngx_int_t          event;
    ngx_err_t          err;
    ngx_uint_t         level;
    ngx_socket_t       s;
    ngx_event_t       *rev, *wev;
    ngx_connection_t  *c;

    rc = pc->get(pc, pc->data);
    if (rc != NGX_OK) {
        return rc;
    }

    type = (pc->type ? pc->type : SOCK_STREAM);

    s = ngx_socket(pc->sockaddr->sa_family, type, 0);

    ngx_log_debug2(NGX_LOG_DEBUG_EVENT, pc->log, 0, "%s socket %d",
                   (type == SOCK_STREAM) ? "stream" : "dgram", s);

    if (s == (ngx_socket_t) -1) {
        ngx_log_error(NGX_LOG_ALERT, pc->log, ngx_socket_errno,
                      ngx_socket_n " failed");
        return NGX_ERROR;
    }


    c = ngx_get_connection(s, pc->log);

    if (c == NULL) {
        if (ngx_close_socket(s) == -1) {
            ngx_log_error(NGX_LOG_ALERT, pc->log, ngx_socket_errno,
                          ngx_close_socket_n " failed");
        }

        return NGX_ERROR;
    }

    c->type = type;

    if (pc->rcvbuf) {
        if (setsockopt(s, SOL_SOCKET, SO_RCVBUF,
                       (const void *) &pc->rcvbuf, sizeof(int))
            == -1)
        {
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Peer <code>get</code> callback選地址並填sockaddr/name。</p></div><div class="source-step"><span>2</span><p>建立socket、non-blocking、bind local/transparent/socket options。</p></div><div class="source-step"><span>3</span><p><code>connect</code> 回OK、AGAIN、DECLINED、ERROR等結果。</p></div><div class="source-step"><span>4</span><p>AGAIN時安裝write event與connect timeout。</p></div><div class="source-step"><span>5</span><p>Write-ready進send handler，先test connect；失敗走upstream next。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Epoll writable 只是 connect 已完成到可檢查狀態。</p></div><div class="microscope-card"><span>2</span><p>Connect timer 成功/失敗後應刪除，再切 send/read timer。</p></div><div class="microscope-card"><span>3</span><p>失敗時 close connection 並呼叫 peer free 回饋。</p></div><div class="microscope-card"><span>4</span><p>Immediate success 與 async success 最後必須進同一 send-request path。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 不要把 EPOLLOUT 當 connect success；必須檢查 socket error。
- Connect timer 只覆蓋建立連線階段，之後會切換 send/read timeout。
- 每個失敗 branch 都要正確 close fd 並呼叫 peer free 回饋。
- 成功後 handler 立即換成 send-request continuation，這是關鍵狀態轉移。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/ngx_event_connect.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event_connect.c#L1) · [`src/http/ngx_http_upstream.c#L1571`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L1571) · [`src/http/ngx_http_upstream.c#L1852`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L1852)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Connect timeout包含排隊與網路建立時間，但DNS resolution可能發生在更早階段並有獨立resolver timeout。排障要分DNS、TCP connect、TLS handshake、request send、header wait。

Happy Eyeballs、IPv4/IPv6、多地址DNS與dynamic upstream使peer selection不只是一次地址。NGINX的peer interface把「選哪個」和「怎麼connect」分開，讓算法可替換。

Connection pool重用時要清除request-specific log/data/event flags，並確認socket沒有未讀資料、EOF或timeout；keepalive章會再展開。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Split-phase operation</h3><p>開始 connect 與完成 connect 是兩個 callback 階段。</p></div><div class="pattern-card"><h3>Capability callback</h3><p>peer.get/free 將選擇與回饋從 transport 分離。</p></div><div class="pattern-card"><h3>Deadline guard</h3><p>timer 與 readiness 競賽，先發生者決定結果。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 連到不存在IP/拒絕port/正常backend，比較connect返回與timer。
2. 在 `ngx_event_connect_peer` 與test connect處看 errno/SO_ERROR。
3. 用 `ss -tan` 觀察 SYN-SENT 到 ESTABLISHED。
4. 設定很短 `proxy_connect_timeout`，驗證錯誤映射與retry。

## 常見誤解與失敗模式

- 把write-ready直接視為connect成功，不檢查SO_ERROR。
- 把DNS、connect、TLS與header latency混成一個timeout。
- 重用upstream connection時留下舊request pointer/timer。

## 可以帶走的 Coding／CS 能力

- 理解非阻塞connect的兩階段完成。
- 設計可插拔peer selection與transport establishment。
- 建立分階段timeout與可觀測性。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

有了可用 backend connection，下一章看多台 peers 中為何採 smooth weighted round robin。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. EINPROGRESS 為什麼不是錯誤？</summary>

Non-blocking socket不能等待TCP handshake；kernel已啟動連線，完成或失敗會透過write readiness與SO_ERROR呈現。

</details>

<details class="qa" markdown="1">
<summary>Q2. Write-ready為何可能代表連線失敗？</summary>

連線結果已可取得，不等於成功；RST、route error等也會讓fd進入可回報狀態，必須讀SO_ERROR。

</details>

<details class="qa" markdown="1">
<summary>Q3. Peer `get/free` callbacks的用途？</summary>

`get`按算法選地址並取得使用權；`free`依成功/失敗更新conns、fails、weight與availability，讓core與算法解耦。

</details>

<details class="qa" markdown="1">
<summary>Q4. Connect timeout和read timeout有何差別？</summary>

前者涵蓋建立backend connection；後者通常限制兩次read或等待response資料的時間。混用會誤判瓶頸。

</details>

<details class="qa" markdown="1">
<summary>Q5. Upstream connection為何可能有獨立pool？</summary>

Keepalive cache可讓socket跨request存活；若pool綁request，request結束就不能安全保留連線的SSL/event等資源。

</details>

<details class="qa" markdown="1">
<summary>Q6. 怎麼證明故障在TCP connect而非backend application？</summary>

看SYN/SYN-ACK、SO_ERROR、connect_time與是否收到任何HTTP header；application還沒收到request前不會有HTTP status。

</details>

---

# 第 28 章　Smooth Weighted Round Robin

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Weighted round robin</h3><div class="foundation-block"><span>白話定義</span><p>依 backend capacity 用不同頻率分配 requests。Weight 5:1 表示長期比例約五比一，不代表必須連續五次選同一台。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>大機器每六次約接五次，小機器約接一次。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX smooth algorithm 累加 current weight，選最大者後扣總權重，使高權重選擇均勻穿插。</p></div></section><section class="foundation-card"><h3>Peer</h3><div class="foundation-block"><span>白話定義</span><p>一個可被選來連線的遠端 endpoint，通常是一台 backend 的 IP/port 加上權重與健康狀態。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Upstream group 有 app-1、app-2、app-3；某次 request 選 app-2 作為 peer。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Balancer 的 get callback 選 peer；free callback 回報 success/failure，讓後續選擇調整。</p></div></section><section class="foundation-card"><h3>Feedback control</h3><div class="foundation-block"><span>白話定義</span><p>系統根據實際成功或失敗回饋調整下一次決策，而不是永遠使用固定參數。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 剛失敗時降低 effective weight，之後成功再逐步恢復。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Balancer state 同時表達靜態 capacity 與動態健康程度。</p></div></section><section class="foundation-card"><h3>Load-balancing policy 與 workload</h3><div class="foundation-block"><span>白話定義</span><p>Policy 是選擇 backend 的規則；workload 是實際 requests 的大小、時間、key 分布與失敗特性。沒有脫離 workload 的最佳 policy。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>短 requests 可用 round robin；長短差很多時 least connections 可能更合理。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 提供 round robin、least connections、hash/random 等策略，使用者依 constraints 選擇。</p></div></section></div>



<p class="chapter-question">NGINX 的預設負載均衡如何同時遵守權重，又避免把高權重流量一次爆量送給同一台？</p>

<div class="chapter-meta"><span>難度：進階</span><span>scheduling · weighted round robin · failure recovery</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

從公平性需求推導 current/effective weight演算法，並理解failure recovery。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-27-從-nginx-非阻塞連線到-backend"><span>上一站</span><strong>27. 從 NGINX 非阻塞連線到 Backend</strong></a><div class="position-card current"><span>你在這裡</span><strong>28. Smooth Weighted Round Robin</strong></div><a class="position-card" href="#chapter-29-其他負載均衡策略"><span>下一站</span><strong>29. 其他負載均衡策略</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

普通 weighted round robin 若直接連續送出權重份額，會產生流量 burst：權重 5:1 可能先連續五次打 A，再一次打 B。Smooth weighted round robin 讓高權重 peer 更頻繁但盡量均勻地穿插。

Use case 是不同容量 backend 以 weight 分流，同時在失敗後降低有效權重、成功後逐步恢復。它不只是一道演算法題，而是 scheduler 加 feedback control。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>普通 weighted round robin 若直接連續送出權重份額，會產生流量 burst：權重 5:1 可能先連續五次打 A，再一次打 B。Smooth weighted round robin 讓高權重 peer 更頻繁但盡量均勻地穿插。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是不同容量 backend 以 weight 分流，同時在失敗後降低有效權重、成功後逐步恢復。它不只是一道演算法題，而是 scheduler 加 feedback control。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Weighted peer scheduler」這個責任邊界；接收 可用 peers、weight、failure state、tried set，交付 本次選中的 peer + 後續成功失敗回饋入口。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 per-request tried bitmap + per-peer current/effective weight 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 全部 peers 不可用、burst、失敗 peer 持續被選、integer invariant 破壞。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Weighted peer scheduler</p></div><div class="contract-card"><span>接收什麼</span><p>可用 peers、weight、failure state、tried set</p></div><div class="contract-card"><span>產生什麼</span><p>本次選中的 peer + 後續成功失敗回饋入口</p></div><div class="contract-card"><span>狀態由誰保存</span><p>per-request tried bitmap + per-peer current/effective weight</p></div><div class="contract-card"><span>主要失敗出口</span><p>全部 peers 不可用、burst、失敗 peer 持續被選、integer invariant 破壞</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>遍歷未 tried 且健康的 peers</p></div><div class="flow-step"><span>2</span><p>每個 peer 的 current += effective</p></div><div class="flow-step"><span>3</span><p>累加 total effective weight</p></div><div class="flow-step"><span>4</span><p>選 current 最大者</p></div><div class="flow-step"><span>5</span><p>winner.current -= total</p></div><div class="flow-step"><span>6</span><p>標記 request tried</p></div><div class="flow-step"><span>7</span><p>連線結果透過 free callback 回饋</p></div><div class="flow-step"><span>8</span><p>失敗降低 effective，成功逐步恢復</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
weights: A=5, B=1, C=1

每輪：
1. 每個 current += effective
2. 選 current 最大者
3. winner.current -= total_effective

結果示意：A, A, B, A, C, A, A
比例接近 5:1:1，低權重節點不必等到最後一大段才收到流量。
```

## 從零建立心智模型

初始化時每個peer保存 `weight`、`effective_weight`、`current_weight`、conns、fails、checked等狀態。選擇時略過down、fail window內、max_conns已滿與本次已嘗試的peer。

每個候選的 current weight加effective weight，選最大者，再從winner current減所有候選effective總和。長期選中次數按權重，短期分布比傳統「AAAAB」更平滑。

Failure可降低effective weight；後續成功選擇時它逐步加回原weight，形成慢恢復。這不是精密健康模型，但可避免剛失敗peer立刻吃回全部比例。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

將權重份額連續送出會產生 burst。Smooth weighted round robin 每輪累加 current weight、選最大者，再從 winner 扣除總權重，使長期比例正確且短期更平滑。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Peer.current</code></td><td><code>current_weight</code></td></tr><tr><td><code>Peer.effective</code></td><td><code>effective_weight</code>，可因失敗降低</td></tr><tr><td><code>total</code></td><td>本輪所有有效權重總和</td></tr><tr><td>winner subtract</td><td>平滑分布的核心 invariant</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_upstream_round_robin.c`，官方 `release-1.31.5` 第 811–858 行

```c
ngx_http_upstream_get_peer(ngx_http_upstream_rr_peer_data_t *rrp,
    ngx_peer_connection_t *pc)
{
    time_t                        now;
    uintptr_t                     m;
    ngx_int_t                     total;
    ngx_uint_t                    i, n, p;
    ngx_http_upstream_rr_peer_t  *peer, *best;

#if (NGX_HTTP_UPSTREAM_SID)
    ngx_int_t                     low_limit;
    ngx_uint_t                    st_p;
    ngx_http_upstream_rr_peer_t  *st_peer;
#endif

    now = ngx_time();

    best = NULL;
    total = 0;

#if (NGX_SUPPRESS_WARN)
    p = 0;
#endif

#if (NGX_HTTP_UPSTREAM_SID)
    st_peer = ngx_http_upstream_get_rr_peer_by_sid(rrp, pc->hint, &p, 0);

    if (st_peer) {

        low_limit = -((ngx_int_t)(rrp->peers->total_weight - st_peer->weight));

        /*
         * note: current code accounts only one sticky request in a row, if it
         *       is required to account more, multiply low_limit by N below
         */
        if (st_peer->current_weight <= low_limit) {

            /* do not update weights if the limit exceeded */
            best = st_peer;
            goto best_chosen;
        }
        /* else: proceed to reweight with existing st_peer */
    }

    st_p = p;
#endif

    for (peer = rrp->peers->peer, i = 0;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Config-time建立primary/backup peer lists與weight totals。</p></div><div class="source-step"><span>2</span><p>Per-request peer data保存tried bitmap，避免retry同一peer。</p></div><div class="source-step"><span>3</span><p>Selection loop先過濾down/fails/max_conns/tried。</p></div><div class="source-step"><span>4</span><p>累加current/effective，選best，winner扣total。</p></div><div class="source-step"><span>5</span><p><code>free</code> callback更新conns、fails、accessed/checked與state。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>手算前數輪 current weights，不要只背 code。</p></div><div class="microscope-card"><span>2</span><p>區分 configured/effective/current 三種 weight。</p></div><div class="microscope-card"><span>3</span><p>Per-request tried bitmap 避免 retry 重選同一 peer。</p></div><div class="microscope-card"><span>4</span><p>Free callback 的失敗回饋會改 effective weight 與 fail counters。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 區分 configured weight、effective weight 與 current weight。
- 先手算 5:1、3:2 的前十次選擇，才能看懂 update invariant。
- Peer shared state 是否跨 workers 取決於 upstream zone 配置。
- 失敗回饋時機與 classification 會影響 scheduler 是否過度懲罰。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_upstream_round_robin.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream_round_robin.c#L1) · [`src/http/ngx_http_upstream_round_robin.c#L758`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream_round_robin.c#L758) · [`src/http/ngx_http_upstream_round_robin.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream_round_robin.h#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Smooth weighted RR只對request數比例公平，不保證工作量公平。若request cost差異極大，count-based scheduling會讓某backend承擔更多CPU；least_conn/least_time可能更適合。

Peer state若放shared zone可跨workers共享；否則每個worker有自己的選擇狀態。局部公平不一定等於全域精確比例，尤其流量低或connection分配不均。

Retry tried bitmap是bounded search：每peer最多一次，耗盡後回NGX_BUSY或轉backup group，避免無限重試。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Smooth weighted round robin</h3><p>保持長期比例，同時降低短期 burst。</p></div><div class="pattern-card"><h3>Feedback-adjusted scheduling</h3><p>effective weight 依失敗與恢復動態改變。</p></div><div class="pattern-card"><h3>Per-request exclusion set</h3><p>retry 不應立刻重選同一 peer。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 手算權重5:1:1的前14次結果，確認比例與平滑性。
2. 配置三backend回名稱，收集1000次分布。
3. 讓高權重peer間歇失敗，觀察effective weight恢復。
4. 用多worker、有/無zone比較全域分布。

## 常見誤解與失敗模式

- 只驗證長期比例，忽略短期burst與低流量。
- 把request數公平當CPU/latency公平。
- 失敗後立即恢復完整權重造成flapping。

## 可以帶走的 Coding／CS 能力

- 從公平性、burst與恢復需求設計scheduler。
- 理解weighted fair selection與feedback state。
- 使用bitmap限制retry搜索空間。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Round robin 不是所有 workload 的最佳策略；下一章比較 hash、least connections 與其他選擇。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Smooth weighted RR比簡單重複列表好在哪裡？</summary>

同樣維持長期比例，但會把低權重peer較均勻插入序列，避免高權重peer連續承受一大段burst。

</details>

<details class="qa" markdown="1">
<summary>Q2. `effective_weight` 和 `weight` 為何分開？</summary>

Weight是配置目標；effective可因失敗暫時下降並漸進恢復，不必修改原始設定。

</details>

<details class="qa" markdown="1">
<summary>Q3. 為什麼要扣除total weight？</summary>

Winner已獲得一次服務，扣總量形成債務；未選peer持續累積current，最終會超過winner，達成比例公平。

</details>

<details class="qa" markdown="1">
<summary>Q4. 算法能保證每7個request恰好5:1:1嗎？</summary>

在穩定eligible集合下序列接近且週期性，但fail/max_conns/retry、多worker與權重恢復都會改變；保證重點是長期傾向。

</details>

<details class="qa" markdown="1">
<summary>Q5. Shared zone如何影響選擇？</summary>

Peer counters/weights可跨worker共享，分布與max_conns更接近全域狀態；代價是shared locking/atomic與一致性成本。

</details>

<details class="qa" markdown="1">
<summary>Q6. 何時不該用weighted RR？</summary>

Request service time高度不均、sticky需求、cache locality或實時latency feedback更重要時，應考慮least_conn/hash/least_time等。

</details>

---

# 第 29 章　其他負載均衡策略

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Load-balancing policy 與 workload</h3><div class="foundation-block"><span>白話定義</span><p>Policy 是選擇 backend 的規則；workload 是實際 requests 的大小、時間、key 分布與失敗特性。沒有脫離 workload 的最佳 policy。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>短 requests 可用 round robin；長短差很多時 least connections 可能更合理。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 提供 round robin、least connections、hash/random 等策略，使用者依 constraints 選擇。</p></div></section><section class="foundation-card"><h3>Affinity 與 cache locality</h3><div class="foundation-block"><span>白話定義</span><p>Affinity 讓相同 user/key 傾向同一 backend；cache locality 則希望相同資料落到已經有 cache 的節點。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同一 session ID 經 hash 後總是優先選 app-2。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>它可減少 cache miss 或支援 legacy session，但 backend 變動時需要處理重新映射與偏斜。</p></div></section><section class="foundation-card"><h3>Peer</h3><div class="foundation-block"><span>白話定義</span><p>一個可被選來連線的遠端 endpoint，通常是一台 backend 的 IP/port 加上權重與健康狀態。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Upstream group 有 app-1、app-2、app-3；某次 request 選 app-2 作為 peer。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Balancer 的 get callback 選 peer；free callback 回報 success/failure，讓後續選擇調整。</p></div></section><section class="foundation-card"><h3>Feedback control</h3><div class="foundation-block"><span>白話定義</span><p>系統根據實際成功或失敗回饋調整下一次決策，而不是永遠使用固定參數。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 剛失敗時降低 effective weight，之後成功再逐步恢復。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Balancer state 同時表達靜態 capacity 與動態健康程度。</p></div></section></div>



<p class="chapter-question">Least connections、hash、consistent hash、random two choices與least time各自優化什麼，又犧牲什麼？</p>

<div class="chapter-meta"><span>難度：進階</span><span>load balancing · consistent hashing · power of two choices</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

用workload、state locality、feedback freshness與failure remapping比較算法，而不是背directive。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-28-smooth-weighted-round-robin"><span>上一站</span><strong>28. Smooth Weighted Round Robin</strong></a><div class="position-card current"><span>你在這裡</span><strong>29. 其他負載均衡策略</strong></div><a class="position-card" href="#chapter-30-timeout-failure-與-retry"><span>下一站</span><strong>30. Timeout、Failure 與 Retry</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Load balancing 的目標可能是平均 request 數、平均 in-flight 工作、維持 session affinity 或提高 cache locality；不存在脫離 workload 的唯一最佳演算法。本章建立『先列 constraints，再選 policy』的思考方式。

Use case 包括長短 request 差異大時用 least connections、需要 key affinity 時用 hash、超大 fleet 用抽樣策略。選錯 metric 會看似平均，實際 latency 卻惡化。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Load balancing 的目標可能是平均 request 數、平均 in-flight 工作、維持 session affinity 或提高 cache locality；不存在脫離 workload 的唯一最佳演算法。本章建立『先列 constraints，再選 policy』的思考方式。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 包括長短 request 差異大時用 least connections、需要 key affinity 時用 hash、超大 fleet 用抽樣策略。選錯 metric 會看似平均，實際 latency 卻惡化。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Pluggable peer-selection policy」這個責任邊界；接收 peer states + request key/connection counts/weights，交付 一個候選 peer 與可解釋的選擇理由。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 policy-specific peer data + common get/free interface 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 hot key、remap storm、stale load metric、所有候選失敗。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Pluggable peer-selection policy</p></div><div class="contract-card"><span>接收什麼</span><p>peer states + request key/connection counts/weights</p></div><div class="contract-card"><span>產生什麼</span><p>一個候選 peer 與可解釋的選擇理由</p></div><div class="contract-card"><span>狀態由誰保存</span><p>policy-specific peer data + common get/free interface</p></div><div class="contract-card"><span>主要失敗出口</span><p>hot key、remap storm、stale load metric、所有候選失敗</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>定義 workload 與要最佳化的指標</p></div><div class="flow-step"><span>2</span><p>module 在 config time 建 policy data</p></div><div class="flow-step"><span>3</span><p>request time 取得 key或負載訊號</p></div><div class="flow-step"><span>4</span><p>排除 tried/down/unavailable peers</p></div><div class="flow-step"><span>5</span><p>依 policy 排序、hash 或抽樣</p></div><div class="flow-step"><span>6</span><p>回傳 peer 給通用 connect path</p></div><div class="flow-step"><span>7</span><p>free callback 更新 feedback</p></div><div class="flow-step"><span>8</span><p>失敗時 fallback 到下一 policy/peer</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
策略                 主要訊號                 適合
round robin           配置權重                 cost近似
least_conn            active connections       長短請求不均
hash/consistent hash  request key              affinity/cache locality
random two            兩個sample後比較         大cluster低選擇成本
least_time            latency + inflight        尾延遲導向

沒有免費午餐：訊號越動態，噪音與同步成本越高。
```

## 從零建立心智模型

Least connections以active connection/weight選較空peer，對長request比純count更有回饋；但keepalive、HTTP multiplexing與每connection工作量不同會讓conns只是近似。

Hash用request key維持affinity。普通mod hash在增減節點時大量remap；consistent hash把peer映射到ring，通常只影響鄰近範圍，提高cache locality，但熱門key仍可形成hotspot。

Random two choices從少量sample選較佳者，避免每次掃全cluster；least time用latency與inflight估計完成時間，反應更直接但依賴量測品質、共享狀態與避免追逐瞬時噪音。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

不同 workload 需要不同 selection signal。Strategy interface 讓 round robin、least-connections 與 hash 共用同一 `choose` contract，transport 不必知道演算法。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>strategy function</td><td>upstream peer init/get callback</td></tr><tr><td>request key</td><td>ip hash/hash module 的 runtime key</td></tr><tr><td>connection metric</td><td>least_conn peer counters</td></tr><tr><td>same return shape</td><td>共用 <code>ngx_peer_connection_t</code> output contract</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/modules/ngx_http_upstream_least_conn_module.c`，官方 `release-1.31.5` 第 100–147 行

```c
ngx_http_upstream_get_least_conn_peer(ngx_peer_connection_t *pc, void *data)
{
    ngx_http_upstream_rr_peer_data_t  *rrp = data;

    time_t                         now;
    uintptr_t                      m;
    ngx_int_t                      rc, total;
    ngx_uint_t                     i, n, p, many;
    ngx_http_upstream_rr_peer_t   *peer, *best;
    ngx_http_upstream_rr_peers_t  *peers;

    ngx_log_debug1(NGX_LOG_DEBUG_HTTP, pc->log, 0,
                   "get least conn peer, try: %ui", pc->tries);

    if (rrp->peers->single) {
        return ngx_http_upstream_get_round_robin_peer(pc, rrp);
    }

    pc->cached = 0;
    pc->connection = NULL;

    now = ngx_time();

    peers = rrp->peers;

    ngx_http_upstream_rr_peers_wlock(peers);

#if (NGX_HTTP_UPSTREAM_ZONE)
    if (peers->config && rrp->config != *peers->config) {
        goto busy;
    }
#endif

    best = NULL;
    total = 0;

#if (NGX_SUPPRESS_WARN)
    many = 0;
    p = 0;
#endif

#if (NGX_HTTP_UPSTREAM_SID)
    best = ngx_http_upstream_get_rr_peer_by_sid(rrp, pc->hint, &p, 0);

    if (best) {
        goto best_chosen;
    }
#endif
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>各module替換upstream <code>init_upstream/init_peer/get/free/notify</code> callbacks。</p></div><div class="source-step"><span>2</span><p>大多策略重用round-robin peer結構的eligibility、failure與backup邏輯。</p></div><div class="source-step"><span>3</span><p>Hash module可建立consistent-hash points並binary search ring。</p></div><div class="source-step"><span>4</span><p>Random two先按weight取樣候選，再比較connections等訊號。</p></div><div class="source-step"><span>5</span><p>Least time維護EWMA/估計與inflight完成通知。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先問 metric 是否真的代表 load；connections 不等於 CPU work。</p></div><div class="microscope-card"><span>2</span><p>Hash 的 key distribution 與 backend churn 會造成 hotspot/remap。</p></div><div class="microscope-card"><span>3</span><p>State 是 per worker 還是 shared zone 會影響精確度。</p></div><div class="microscope-card"><span>4</span><p>所有策略都需處理 tried/down/unavailable 與 fallback。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 比較演算法時同時問 state 是 local 還是 shared、更新是否精確、成本多高。
- Least connections 只看連線數，未必代表 CPU/queue work。
- Hash 提供 affinity，不等於高可用；peer down 時仍需 fallback。
- 演算法名稱不是答案，要用 request duration、key distribution、fleet churn 驗證。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/modules/ngx_http_upstream_least_conn_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_least_conn_module.c#L1) · [`src/http/modules/ngx_http_upstream_hash_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_hash_module.c#L1) · [`src/http/modules/ngx_http_upstream_random_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_random_module.c#L1) · [`src/http/modules/ngx_http_upstream_least_time_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_least_time_module.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

選算法前先定義objective：平均latency、p99、cache hit、session affinity、backend utilization或failover stability。不同objective可能互相衝突。

Feedback loop有延遲。Least_conn看到的是當下connections，不知道剛排到backend但尚未反映的成本；latency metric是過去樣本。過度敏感會把流量集體趕向看似最快peer，造成振盪。

Affinity不能替代正確共享session storage。節點失敗、擴縮容、NAT聚合與key skew都會破壞「永遠同一台」的假設。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Strategy pattern</h3><p>相同 get/free contract 下替換選擇演算法。</p></div><div class="pattern-card"><h3>Consistent hashing</h3><p>節點變動時降低 key remapping，但仍需處理 skew。</p></div><div class="pattern-card"><h3>Power of two choices</h3><p>只抽少量 candidates 即可大幅降低最大負載。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 建立短/長request混合流量，比較RR與least_conn p95與分布。
2. 以user id做consistent hash，增減一台backend量測remap比例。
3. 製造熱門key，觀察hash affinity的hotspot。
4. 讓一台backend latency抖動，比較動態策略是否振盪。

## 常見誤解與失敗模式

- 只看算法名稱，不定義優化目標。
- 把connection count視為精確load。
- 依賴sticky掩蓋session state設計問題。

## 可以帶走的 Coding／CS 能力

- 將scheduler問題轉成objective、signal、cost與stability。
- 理解consistent hashing、sampling與feedback control。
- 分析key skew、state locality與failure remapping。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

選到 peer 之後仍可能在不同階段失敗；下一章決定何時 timeout、retry 或停止。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Least_conn為何可能勝過RR？</summary>

當request/connection持續時間差異大，active count提供工作尚未完成的回饋，避免長工作連續落同peer；但它仍不是CPU queue的完美量測。

</details>

<details class="qa" markdown="1">
<summary>Q2. Consistent hash主要解決什麼？</summary>

節點集合改變時降低key remapping，保留cache/session locality；它不自動解決熱門key或peer capacity差異。

</details>

<details class="qa" markdown="1">
<summary>Q3. Power of two choices為何有效？</summary>

只取少量隨機候選就能大幅降低最壞queue，相比掃全體成本低、共享狀態少；前提是sample與比較訊號合理。

</details>

<details class="qa" markdown="1">
<summary>Q4. Latency-based策略為何可能振盪？</summary>

Metric延遲與噪音讓所有流量追逐暫時最快peer，該peer變慢後再集體轉移。需要EWMA、inflight penalty、randomization與hysteresis。

</details>

<details class="qa" markdown="1">
<summary>Q5. Sticky session能否保證user永遠同一backend？</summary>

不能。節點故障、ring改變、cookie失效或配置更新都會重映射；應把它視為locality optimization，不是資料正確性基礎。

</details>

<details class="qa" markdown="1">
<summary>Q6. 怎麼選擇策略？</summary>

先以真實workload定義SLO與constraint，再離線/影子比較分布、p99、remap、failure recovery與state cost；不要只靠平均延遲。

</details>

---

# 第 30 章　Timeout、Failure 與 Retry

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Timeout、deadline 與 retry</h3><div class="foundation-block"><span>白話定義</span><p>Timeout 限制單一等待；deadline 限制整個操作的總時間；retry 是失敗後再嘗試另一個 peer。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>總預算 2 秒時，不能對三個 peers 各等待 2 秒。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 failure stage、method/config 與剩餘 peers 決定是否呼叫 upstream next。</p></div></section><section class="foundation-card"><h3>Idempotency 與副作用</h3><div class="foundation-block"><span>白話定義</span><p>Idempotent operation 重複執行仍等同執行一次；副作用是付款、寄信或寫入資料等外部改變。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>重複讀取同一資源通常安全；重複扣款則可能造成真實損失。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Request body 已送往 backend 後若結果未知，proxy retry 可能重複副作用，不能只看 transport error。</p></div></section><section class="foundation-card"><h3>Retry storm</h3><div class="foundation-block"><span>白話定義</span><p>大量失敗 requests 同時重試會放大流量，使已經過載的 backend 更難恢復。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>每個 request 重試三次，原本 1,000 QPS 可瞬間變成接近 3,000 次嘗試。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>需要限制次數、整體 deadline、可重試條件並搭配 capacity/admission control。</p></div></section><section class="foundation-card"><h3>Upstream</h3><div class="foundation-block"><span>白話定義</span><p>從 NGINX 角度看出去的 backend 交易或 backend 群組。它不是 client 連進來的那條 connection。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>一次 client request 可能建立一條 upstream connection 到 <code>app-2:8080</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_http_upstream_t</code> 保存 peer selection、connect/send/read state、retry、buffering 與 timing。</p></div></section></div>



<p class="chapter-question">某個 backend 失敗時，NGINX 何時能安全換下一台，何時重試反而會造成重複寫入或雪崩？</p>

<div class="chapter-meta"><span>難度：進階</span><span>retry · idempotency · failure amplification</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

建立分階段timeout、failure classification、tried peers、idempotency與retry budget模型。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-29-其他負載均衡策略"><span>上一站</span><strong>29. 其他負載均衡策略</strong></a><div class="position-card current"><span>你在這裡</span><strong>30. Timeout、Failure 與 Retry</strong></div><a class="position-card" href="#chapter-31-upstream-keepalive"><span>下一站</span><strong>31. Upstream Keepalive</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

分散式系統中的 failure 不是單一布林值：connect refused、connect timeout、header timeout、invalid response、mid-body close 的資訊與安全性不同。Retry 能提高可用性，也可能重複副作用、放大流量與突破整體 deadline。

Use case 是 GET 在 backend connect 前失敗可嘗試另一台；POST 已送出付款 body 後結果未知，盲目 retry 可能扣款兩次。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>分散式系統中的 failure 不是單一布林值：connect refused、connect timeout、header timeout、invalid response、mid-body close 的資訊與安全性不同。Retry 能提高可用性，也可能重複副作用、放大流量與突破整體 deadline。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 GET 在 backend connect 前失敗可嘗試另一台；POST 已送出付款 body 後結果未知，盲目 retry 可能扣款兩次。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Failure and retry policy」這個責任邊界；接收 attempt stage、error class、method/body replayability、remaining peers，交付 retry next peer 或 finalize client response。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 upstream state history、tried set、timeouts、request-sent flags 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 duplicate side effect、retry storm、deadline amplification、response 已開始後重試。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Failure and retry policy</p></div><div class="contract-card"><span>接收什麼</span><p>attempt stage、error class、method/body replayability、remaining peers</p></div><div class="contract-card"><span>產生什麼</span><p>retry next peer 或 finalize client response</p></div><div class="contract-card"><span>狀態由誰保存</span><p>upstream state history、tried set、timeouts、request-sent flags</p></div><div class="contract-card"><span>主要失敗出口</span><p>duplicate side effect、retry storm、deadline amplification、response 已開始後重試</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>I/O handler 分類 failure 與當前 stage</p></div><div class="flow-step"><span>2</span><p>記錄本次 status/timing</p></div><div class="flow-step"><span>3</span><p>檢查 <code>proxy_next_upstream</code> policy</p></div><div class="flow-step"><span>4</span><p>檢查 request 是否可安全重播</p></div><div class="flow-step"><span>5</span><p>檢查是否還有未 tried peers/tries/time budget</p></div><div class="flow-step"><span>6</span><p>若可重試，reinit protocol state</p></div><div class="flow-step"><span>7</span><p>free old peer 並 connect next</p></div><div class="flow-step"><span>8</span><p>否則選最合理 client status/finalize</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
attempt 1: peer A
  connect timeout / send error / invalid header / 5xx
       │ classify + policy
       ├─ not retryable → finalize client response
       └─ retryable and tries/time remain
               ↓ free peer state
          reinit protocol
          select untried peer B

危險窗口：A 可能已執行寫入，但response在回程遺失。
```

## 從零建立心智模型

Failure不是單一布林值。Upstream core用bitmask區分error、timeout、invalid header、特定HTTP status、no live peers等；location policy決定哪些可進下一peer，以及是否受 non-idempotent request限制。

真正困難是uncertain outcome：POST已完整送到A，A完成付款但response途中斷線。Proxy只看到read timeout，無法知道副作用是否發生；重試B可能重複執行。Idempotency key與backend dedup才是根本解法。

Retries消耗時間與容量。若每層各重試3次，總attempt可乘法放大。需要總deadline、max tries、retry budget、jitter/circuit policy與可觀測attempt history。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

遇到任何錯誤都 retry 看似提高成功率，實際可能重複付款或造成 retry storm。Decision 必須同時看失敗階段、method semantics、body replayability、剩餘 peers 與 deadline。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>stage</code></td><td>connect/send/read header/body 的 upstream failure context</td></tr><tr><td><code>body_buffered</code></td><td>request 是否可重播</td></tr><tr><td><code>response_started</code></td><td>header/body 是否已送 client</td></tr><tr><td><code>tries_left</code></td><td>next_upstream_tries、tried peers 與 timeout budget</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_upstream.c`，官方 `release-1.31.5` 第 4599–4648 行

```c
ngx_http_upstream_next(ngx_http_request_t *r, ngx_http_upstream_t *u,
    ngx_uint_t ft_type)
{
    ngx_msec_t  timeout;
    ngx_uint_t  status, state;

    ngx_log_debug1(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                   "http next upstream, %xi", ft_type);

    if (u->peer.sockaddr) {

        if (u->peer.connection) {
            u->state->bytes_sent = u->peer.connection->sent;
        }

        if (ft_type == NGX_HTTP_UPSTREAM_FT_HTTP_403
            || ft_type == NGX_HTTP_UPSTREAM_FT_HTTP_404)
        {
            state = NGX_PEER_NEXT;

        } else {
            state = NGX_PEER_FAILED;
        }

        u->peer.free(&u->peer, u->peer.data, state);
        u->peer.sockaddr = NULL;

#if (NGX_HTTP_UPSTREAM_SID)
        u->peer.sid = NULL;
#endif
    }

    if (ft_type == NGX_HTTP_UPSTREAM_FT_TIMEOUT) {
        ngx_log_error(NGX_LOG_ERR, r->connection->log, NGX_ETIMEDOUT,
                      "upstream timed out");
    }

    if (u->peer.cached && ft_type == NGX_HTTP_UPSTREAM_FT_ERROR) {
        /* TODO: inform balancer instead */
        u->peer.tries++;
    }

    switch (ft_type) {

    case NGX_HTTP_UPSTREAM_FT_TIMEOUT:
    case NGX_HTTP_UPSTREAM_FT_HTTP_504:
        status = NGX_HTTP_GATEWAY_TIME_OUT;
        break;

    case NGX_HTTP_UPSTREAM_FT_HTTP_500:
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Connect/send/read/header處將失敗分類傳入 <code>ngx_http_upstream_next</code>。</p></div><div class="source-step"><span>2</span><p>Policy檢查next_upstream flags、tries、timeout與request是否可重試。</p></div><div class="source-step"><span>3</span><p>呼叫peer free callback更新fails/effective weight/conns。</p></div><div class="source-step"><span>4</span><p>Protocol reinit並重設buffer/timer，再選未嘗試peer。</p></div><div class="source-step"><span>5</span><p>耗盡或不可重試時映射最終HTTP status並finalize。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>HTTP method 不能完整代表 application idempotency。</p></div><div class="microscope-card"><span>2</span><p>記錄 bytes/request_sent 狀態，判斷結果是否可能已產生。</p></div><div class="microscope-card"><span>3</span><p>Retry 前需 reinit protocol parser/buffers。</p></div><div class="microscope-card"><span>4</span><p>總 latency budget 應限制多次 per-attempt timeout 疊加。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 分清 connect timeout、send timeout、read/header timeout，它們代表不同未知程度。
- HTTP method 只是線索；真正 idempotency 由 application semantics 決定。
- Body 若未 buffer 完成，即使語意安全也可能無法 replay。
- 一旦部分 response 已送 client，通常不能透明切 peer 重來。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_upstream.c#L4175`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L4175) · [`src/http/ngx_http_upstream.c#L4510`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L4510) · [`src/http/ngx_http_upstream_round_robin.c#L924`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream_round_robin.c#L924)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Timeout不是越短越好。Connect timeout保護死地址；read timeout通常是兩次read間隔，不一定是整個response總deadline。若只設per-attempt timeout而無總budget，連續重試可遠超client SLO。

Passive health由真實request更新peer fails；低流量時恢復慢，高流量時短暫故障可能快速放大。Backup peers與slow recovery要一起看。

重試前若request body已無法重播，必須停止。Buffered body較容易重播；streaming body可能已消費client bytes且不能倒帶。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Retry budget</h3><p>限制 attempts 與總時間，避免故障放大。</p></div><div class="pattern-card"><h3>Idempotency-aware recovery</h3><p>是否重試取決於副作用與結果不確定性。</p></div><div class="pattern-card"><h3>Failure matrix</h3><p>按 stage × error × bytes-sent 系統化決策。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 依序製造connect refused、connect timeout、invalid header、502與body途中斷線。
2. 對GET與POST比較next_upstream行為與attempt數。
3. 加入backend idempotency key，模擬response遺失後安全重試。
4. 讓client deadline短於所有attempt總和，找出浪費的zombie work。

## 常見誤解與失敗模式

- 任何5xx都無條件重試。
- 每層各自重試，形成乘法流量。
- 只設per-attempt timeout，沒有end-to-end deadline。

## 可以帶走的 Coding／CS 能力

- 理解at-least-once delivery與uncertain outcome。
- 設計idempotency、retry budget與deadline propagation。
- 把failure分類映射成安全policy。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

頻繁重建 backend TCP connection 很昂貴；下一章在安全邊界內重用 upstream connections。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼read timeout後不能確定backend沒執行？</summary>

Request可能已到達並完成，只有response遺失或太慢；proxy看不到backend transaction state，因此結果不確定。

</details>

<details class="qa" markdown="1">
<summary>Q2. Buffered request body如何幫助retry？</summary>

完整body仍在memory/temp file，可從頭重新送給新peer；unbuffered streaming可能已消費且無法回放。

</details>

<details class="qa" markdown="1">
<summary>Q3. Idempotent method就一定可安全重試嗎？</summary>

HTTP語意上應無額外副作用，但實際application可能違反，且大response/資源成本仍存在；還需deadline與budget。

</details>

<details class="qa" markdown="1">
<summary>Q4. Retry storm如何形成？</summary>

大量request遇同一慢故障，每個都多次重試，把原流量乘上attempt數，進一步壓垮剩餘健康peers。

</details>

<details class="qa" markdown="1">
<summary>Q5. Passive health的限制？</summary>

依賴真實流量且有觀察延遲；錯誤分類、低流量、局部網路與瞬時尖峰都可能造成誤判。

</details>

<details class="qa" markdown="1">
<summary>Q6. 一個完整retry policy要包含什麼？</summary>

Failure分類、method/idempotency、body replayability、max attempts、總deadline、backoff/jitter、peer exclusion、budget與attempt-level telemetry。

</details>

---

# 第 31 章　Upstream Keepalive

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Handshake 與 ephemeral port</h3><div class="foundation-block"><span>白話定義</span><p>TCP/TLS handshake 是建立新安全連線的額外往返與 CPU 成本；client 端每條 outgoing connection 還需要暫時使用一個 local port。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>高 QPS 短 requests 若每次重連，會浪費 latency 並可能耗盡可用 port 範圍。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Upstream keepalive 重用已完成握手的 backend connection，降低 connect/TLS 與 port 壓力。</p></div></section><section class="foundation-card"><h3>Upstream keepalive cache</h3><div class="foundation-block"><span>白話定義</span><p>保存少量已完成 request、目前 idle 且仍可重用的 backend connections。它是 cache，不是所有 requests 的固定 pool。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>下一個 request 可直接取出 app-1 的 idle socket，不必重新 connect。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 必須檢查協定是否允許重用、connection 是否乾淨，並處理 backend 已悄悄關閉的 stale socket。</p></div></section><section class="foundation-card"><h3>HTTP keep-alive</h3><div class="foundation-block"><span>白話定義</span><p>完成一個 HTTP request 後不立刻關閉 TCP connection，讓同一 client 之後可在同一條連線上再送 request，省下重新建立 TCP 連線的時間。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>瀏覽器用同一條 connection 先取 HTML，再依序取圖片與 API response。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX finalize 舊 request、清除 request-lifetime state，再把 connection handler 改成等待下一個 request。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section></div>



<p class="chapter-question">Backend response完成後，什麼條件下 socket 可以放進 cache，下一個request又如何安全取出重用？</p>

<div class="chapter-meta"><span>難度：進階</span><span>connection pool · LRU · resource reuse</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解連線快取包裝peer callbacks、LRU/free queue、idle read handler與跨request pool。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-30-timeout-failure-與-retry"><span>上一站</span><strong>30. Timeout、Failure 與 Retry</strong></a><div class="position-card current"><span>你在這裡</span><strong>31. Upstream Keepalive</strong></div><a class="position-card" href="#chapter-32-buffering-streaming-與慢速-client"><span>下一站</span><strong>32. Buffering、Streaming 與慢速 Client</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

每次 request 都做 TCP（甚至 TLS）handshake 會增加 latency、CPU 與 ephemeral port 壓力。Upstream keepalive cache 把已完成且仍健康的 idle backend connections 暫存，下一個 request 可直接使用。

Use case 是高 QPS、短 request 的 application servers。這不是無上限 connection pool：cache 只保存有限 idle connections，還要驗證 protocol 狀態乾淨、peer identity 相容且未被 backend 關閉。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>每次 request 都做 TCP（甚至 TLS）handshake 會增加 latency、CPU 與 ephemeral port 壓力。Upstream keepalive cache 把已完成且仍健康的 idle backend connections 暫存，下一個 request 可直接使用。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是高 QPS、短 request 的 application servers。這不是無上限 connection pool：cache 只保存有限 idle connections，還要驗證 protocol 狀態乾淨、peer identity 相容且未被 backend 關閉。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Idle upstream connection cache」這個責任邊界；接收 完成 request 的 peer connection 或新 request 的 peer key，交付 可重用 connection，或 fallback 建新 connection。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 per-worker keepalive cache/available queue、LRU metadata 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 stale idle socket、跨 peer 誤用、cache 無界、response 未讀完就回收。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Idle upstream connection cache</p></div><div class="contract-card"><span>接收什麼</span><p>完成 request 的 peer connection 或新 request 的 peer key</p></div><div class="contract-card"><span>產生什麼</span><p>可重用 connection，或 fallback 建新 connection</p></div><div class="contract-card"><span>狀態由誰保存</span><p>per-worker keepalive cache/available queue、LRU metadata</p></div><div class="contract-card"><span>主要失敗出口</span><p>stale idle socket、跨 peer 誤用、cache 無界、response 未讀完就回收</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>新 request 呼叫 wrapped get peer</p></div><div class="flow-step"><span>2</span><p>按 address/peer identity 搜 idle cache</p></div><div class="flow-step"><span>3</span><p>命中則移出 cache 並綁回 request</p></div><div class="flow-step"><span>4</span><p>未命中交原 load balancer + connect</p></div><div class="flow-step"><span>5</span><p>response 完成時檢查 keepalive eligibility</p></div><div class="flow-step"><span>6</span><p>把 connection 從 request state 拆下</p></div><div class="flow-step"><span>7</span><p>放入 cache 並安裝 idle read handler</p></div><div class="flow-step"><span>8</span><p>容量滿時淘汰最舊 idle connection</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
request N get peer
  ├─ cache hit → detach idle connection
  └─ miss → original balancer + new connect

request N finalize/free peer
  ├─ reusable? → reset data/log/handlers → idle cache queue
  └─ no → original free + close

idle socket readable → peer closed/garbage → remove and close
```

## 從零建立心智模型

Keepalive module不重寫所有balancer。它包裝原本peer `get/free` callbacks：get先在cache找同sockaddr idle connection，miss才呼叫原算法；free判斷response與socket是否可重用，符合才把connection放cache。

Cache有free與cache queues；超過容量時淘汰最舊idle connection。Idle socket仍需read handler，因為backend可能主動關閉；readable時用peek/recv判斷EOF或unexpected data並移除。

Connection pool獨立於request pool，才能跨request保存SSL/session/event資源。放回cache前必須移除timers、清request data、設idle handlers；取出時再綁新request/log。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

無界保存 backend connections 會耗盡 fd；只用 stack/list 又無法快速取用與淘汰。有限 LRU cache 保存 idle、乾淨且 identity 相符的 connections。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>OrderedDict</code></td><td>keepalive cache queue/LRU ordering</td></tr><tr><td><code>peer</code> key</td><td>sockaddr/peer identity matching</td></tr><tr><td><code>put</code></td><td>upstream free callback 判定可 keepalive 後回收</td></tr><tr><td><code>get</code></td><td>wrapped peer get callback 命中 idle connection</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/modules/ngx_http_upstream_keepalive_module.c`，官方 `release-1.31.5` 第 205–254 行

```c
ngx_http_upstream_get_keepalive_peer(ngx_peer_connection_t *pc, void *data)
{
    ngx_http_upstream_keepalive_peer_data_t  *kp = data;
    ngx_http_upstream_keepalive_cache_t      *item;

    ngx_int_t          rc;
    ngx_queue_t       *q, *cache;
    ngx_connection_t  *c;

    ngx_log_debug0(NGX_LOG_DEBUG_HTTP, pc->log, 0,
                   "get keepalive peer");

    /* ask balancer */

    rc = kp->original_get_peer(pc, kp->data);

    if (rc != NGX_OK) {
        return rc;
    }

    /* search cache for suitable connection */

    cache = &kp->conf->cache;

    for (q = ngx_queue_head(cache);
         q != ngx_queue_sentinel(cache);
         q = ngx_queue_next(q))
    {
        item = ngx_queue_data(q, ngx_http_upstream_keepalive_cache_t, queue);
        c = item->connection;

        if (kp->conf->local && item->tag != kp->upstream->conf) {
            continue;
        }

        if (ngx_memn2cmp((u_char *) &item->sockaddr, (u_char *) pc->sockaddr,
                         item->socklen, pc->socklen)
            == 0)
        {
            ngx_queue_remove(q);
            ngx_queue_insert_head(&kp->conf->free, q);

            goto found;
        }
    }

    return NGX_OK;

found:

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Keepalive init保存original peer methods並安裝wrapper。</p></div><div class="source-step"><span>2</span><p>Get按sockaddr掃cache，命中則標cached並移出queue。</p></div><div class="source-step"><span>3</span><p>Miss呼叫original get/connect。</p></div><div class="source-step"><span>4</span><p>Free檢查status、body完整、keepalive flag、timeouts與socket state。</p></div><div class="source-step"><span>5</span><p>Reusable connection放LRU cache；idle close handler監視peer關閉。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>回收前確認 response framing 完整且沒有 unread bytes。</p></div><div class="microscope-card"><span>2</span><p>Idle read handler 用來偵測 backend 主動 close。</p></div><div class="microscope-card"><span>3</span><p>Cache 通常 per worker，容量不是全機精確總數。</p></div><div class="microscope-card"><span>4</span><p>Eviction/close 必須移除 timer/event 並釋放 connection pool。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Keepalive cache 通常 per worker；不要把設定數字誤解成全機精確上限。
- 回收前必須確認 response framing 完整、無 unread bytes、未要求 close。
- Idle read event 用來偵測 backend 主動關閉。
- Cache key 必須對應實際 peer；不能只因 hostname 相同就任意重用。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/modules/ngx_http_upstream_keepalive_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_keepalive_module.c#L1) · [`src/http/modules/ngx_http_upstream_keepalive_module.c#L207`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_keepalive_module.c#L207) · [`src/http/modules/ngx_http_upstream_keepalive_module.c#L281`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_keepalive_module.c#L281)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Keepalive cache是每worker上限，不是backend總連線上限。Worker數乘上cache size，再加active connections，才接近可能連線數；backend capacity planning必須按全域估算。

Connection reuse會放大 stale connection race：backend在cache後剛關閉，NGINX取出並send才發現broken。正確處理靠idle event檢測與send failure retry，但不能假設cache hit必成功。

長期connection可能遇DNS/backend deployment變更；max requests、time與timeout限制可促進輪替。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Object pooling</h3><p>重用昂貴 transport resource。</p></div><div class="pattern-card"><h3>Decorator around strategy</h3><p>keepalive 包住原 get/free peer callbacks。</p></div><div class="pattern-card"><h3>LRU bounded cache</h3><p>只保留有限 idle connections並淘汰最久未用者。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. Backend記錄remote port，連續請求確認connection reuse。
2. 比較每worker keepalive cache與backend實際連線總數。
3. 讓backend在idle期間主動close，觀察idle handler清理。
4. 部署重啟backend，量測stale reuse與retry。

## 常見誤解與失敗模式

- 把keepalive directive當backend最大連線數。
- 把request pointer留在idle connection。
- 認為cache hit後socket一定健康。

## 可以帶走的 Coding／CS 能力

- 理解resource pool wrapper、LRU與per-shard capacity。
- 安全重設可重用物件，避免跨租戶/跨request狀態洩漏。
- 處理stale pooled connection與validation race。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Backend 可以很快，但 client 可能很慢；下一章看 buffering 如何把兩者速度解耦。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Keepalive module為何包裝而非取代balancer？</summary>

它只負責connection reuse；peer選擇仍由RR/hash等算法。Wrapper可組合兩種責任並保留original callbacks。

</details>

<details class="qa" markdown="1">
<summary>Q2. Cache size為何不是全域上限？</summary>

每個worker有自己的address space/cache；總idle可能約為workers×size，還不含active與其他upstream groups。

</details>

<details class="qa" markdown="1">
<summary>Q3. Idle connection為何要監視read event？</summary>

Backend可隨時FIN/RST或送unexpected bytes；若不清理，cache會保存已死socket並在下次request才失敗。

</details>

<details class="qa" markdown="1">
<summary>Q4. 放回cache前要清哪些狀態？</summary>

Request data/log綁定、read/write handlers、timers、ready/error flags與protocol-specific keepalive條件；connection pool只保留跨request安全資料。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如何降低stale connection錯誤？</summary>

Idle close detection、合理timeout/max requests、send failure安全retry、backend graceful drain與觀測reuse failure。無法完全消除close race。

</details>

<details class="qa" markdown="1">
<summary>Q6. Connection reuse對latency的價值？</summary>

省TCP handshake，HTTPS還可能省TLS handshake；但需平衡backend連線容量、負載分布與長連線老化。

</details>

---

# 第 32 章　Buffering、Streaming 與慢速 Client

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Event pipe</h3><div class="foundation-block"><span>白話定義</span><p>協調 upstream read、buffer/temp file 與 downstream write 的 bounded pipeline。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 快速送 100 MB，手機很慢；event pipe 只允許有限在途資料，必要時寫 disk 或暫停 upstream read。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 以 free/in/out/busy chains 與 read/write readiness 推進資料，同時維持 backpressure。</p></div></section><section class="foundation-card"><h3>Producer、consumer 與水位</h3><div class="foundation-block"><span>白話定義</span><p>Producer 產生資料，consumer 消耗資料。High/low watermark 是何時暫停與恢復 producer 的容量門檻。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Upstream 是 response producer，慢速 client 是 consumer。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Event pipe 追蹤 free/busy buffers 與 downstream write 結果，形成 bounded pipeline。</p></div></section><section class="foundation-card"><h3>Backpressure（背壓）</h3><div class="foundation-block"><span>白話定義</span><p>下游處理不過來時，限制上游繼續產生或讀入資料，讓系統內的待處理資料有明確上限。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 每秒產生 10 MB，但手機只能收 100 KB；不能無限把差額塞進 memory。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 buffer 水位暫停 upstream read，等 client write 消耗資料後再恢復。</p></div></section><section class="foundation-card"><h3>Buffering 與 streaming</h3><div class="foundation-block"><span>白話定義</span><p>Buffering 先暫存資料以吸收兩端速度差；streaming 則資料一到便逐段往下游傳，不等待完整內容。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>小 response 可留在 memory；大 response 可能落 temporary file；即時事件適合 streaming。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 module/config 在 latency、memory、disk I/O 與 backend connection 占用之間取捨。</p></div></section><section class="foundation-card"><h3>Buffer chain</h3><div class="foundation-block"><span>白話定義</span><p>把多段不一定連續、來源不同的資料，用 linked nodes 表示成一個輸出序列。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Response headers 在 memory，body 在 file，最後還有一個 end marker。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_chain_t</code> 串起 <code>ngx_buf_t</code>；partial write 只移動 positions，未送完 nodes 留在 busy chain。</p></div></section></div>



<p class="chapter-question">同一個proxy response為什麼有時先讀完backend再慢慢送client，有時又一邊讀一邊送？</p>

<div class="chapter-meta"><span>難度：進階</span><span>buffering · streaming · event pipe</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

比較buffered event pipe與non-buffered path，理解temp file、busy buffers、latency與connection coupling。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-31-upstream-keepalive"><span>上一站</span><strong>31. Upstream Keepalive</strong></a><div class="position-card current"><span>你在這裡</span><strong>32. Buffering、Streaming 與慢速 Client</strong></div><a class="position-card" href="#chapter-33-proxy-cache"><span>下一站</span><strong>33. Proxy Cache</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

若 NGINX 一邊從 backend 讀、一邊直接寫慢速 client，backend connection 會被占用很久；若無限制讀入，又會耗盡 memory。Event pipe 在有限 memory buffers、temporary file、upstream read 與 downstream write 間協調。

Use case 是 backend 快速產生 100 MB response，而手機 client 每秒只讀 50 KB。Buffering 讓 backend 較早釋放；streaming 則降低 first-byte latency 與磁碟使用，兩者是 policy trade-off。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>若 NGINX 一邊從 backend 讀、一邊直接寫慢速 client，backend connection 會被占用很久；若無限制讀入，又會耗盡 memory。Event pipe 在有限 memory buffers、temporary file、upstream read 與 downstream write 間協調。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 backend 快速產生 100 MB response，而手機 client 每秒只讀 50 KB。Buffering 讓 backend 較早釋放；streaming 則降低 first-byte latency 與磁碟使用，兩者是 policy trade-off。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Bidirectional response pump」這個責任邊界；接收 upstream readable + downstream writable + buffer limits，交付 有界地把 response 搬到 client。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 event pipe、in/out/busy/free chains、temp file offsets 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 memory growth、disk saturation、client timeout、upstream stall、buffer flag 遺失。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Bidirectional response pump</p></div><div class="contract-card"><span>接收什麼</span><p>upstream readable + downstream writable + buffer limits</p></div><div class="contract-card"><span>產生什麼</span><p>有界地把 response 搬到 client</p></div><div class="contract-card"><span>狀態由誰保存</span><p>event pipe、in/out/busy/free chains、temp file offsets</p></div><div class="contract-card"><span>主要失敗出口</span><p>memory growth、disk saturation、client timeout、upstream stall、buffer flag 遺失</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>從 upstream 讀到 free buffers</p></div><div class="flow-step"><span>2</span><p>解析/套用 input filter</p></div><div class="flow-step"><span>3</span><p>buffers 加入待輸出 chain</p></div><div class="flow-step"><span>4</span><p>嘗試送到 client output filter</p></div><div class="flow-step"><span>5</span><p>送不完移入 busy chain</p></div><div class="flow-step"><span>6</span><p>超過 memory threshold 時 spill temp file</p></div><div class="flow-step"><span>7</span><p>下游釋放 buffers 後恢復 upstream read</p></div><div class="flow-step"><span>8</span><p>兩端完成或任一端失敗時 finalize</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
buffered:
backend → input bufs → temp file? → output bufs → client
   可較快釋放backend                client可慢

non-buffered:
backend ───────── small buffers ─────────> client
   client慢 ⇒ backend read暫停、connection持有更久
```

## 從零建立心智模型

Buffered response使用 event pipe協調upstream read與downstream write。Input buffers、in/out/free/busy chains與temporary file共同形成有界管線；backend可在client慢時較快完成。

Non-buffered path收到資料就交output filter，適合SSE、streaming與降低首塊延遲；但下游blocked時必須停止upstream read，兩條connection生命周期緊密耦合。

`X-Accel-Buffering`、module config、cache/store與response特性會影響路徑。分析問題時先確認實際走buffered還是non-buffered，不要只看directive字面。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

直接將 backend `recv()` 結果立刻 `send()` 給 client，慢 client 會長期占住 backend。Bounded buffer pump 能暫停 upstream、逐步送 downstream，必要時 spill disk。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>queue</td><td>event pipe 的 out/busy chains</td></tr><tr><td>capacity</td><td>memory buffers 與 temp-file policy</td></tr><tr><td>disable upstream read</td><td>backpressure 調整 upstream event interest</td></tr><tr><td><code>to_client</code></td><td>downstream write/output filter 釋放 buffers</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/event/ngx_event_pipe.c`，官方 `release-1.31.5` 第 23–70 行

```c
ngx_event_pipe(ngx_event_pipe_t *p, ngx_int_t do_write)
{
    ngx_int_t     rc;
    ngx_uint_t    flags;
    ngx_event_t  *rev, *wev;

    for ( ;; ) {
        if (do_write) {
            p->log->action = "sending to client";

            rc = ngx_event_pipe_write_to_downstream(p);

            if (rc == NGX_ABORT) {
                return NGX_ABORT;
            }

            if (rc == NGX_BUSY) {
                return NGX_OK;
            }
        }

        p->read = 0;
        p->upstream_blocked = 0;

        p->log->action = "reading upstream";

        if (ngx_event_pipe_read_upstream(p) == NGX_ABORT) {
            return NGX_ABORT;
        }

        if (!p->read && !p->upstream_blocked) {
            break;
        }

        do_write = 1;
    }

    if (p->upstream
        && p->upstream->fd != (ngx_socket_t) -1)
    {
        rev = p->upstream->read;

        flags = (rev->eof || rev->error) ? NGX_CLOSE_EVENT : 0;

        if (ngx_handle_read_event(rev, flags) != NGX_OK) {
            return NGX_ABORT;
        }

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Response header完成後依 <code>u-&gt;buffering</code> 選event pipe或non-buffered handlers。</p></div><div class="source-step"><span>2</span><p>Event pipe配置input filter、output filter、buf數量/大小、busy limit、temp policy。</p></div><div class="source-step"><span>3</span><p>每輪同時嘗試write downstream、read upstream、spool file並更新events。</p></div><div class="source-step"><span>4</span><p>Non-buffered handler直接讀入u buffer/chain後呼叫output filter。</p></div><div class="source-step"><span>5</span><p>兩條路徑都需在EAGAIN時正確arm read/write events與timers。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先分 buffered 與 non-buffered upstream body path。</p></div><div class="microscope-card"><span>2</span><p>追 buffer 在 free/in/out/busy lists 間的 ownership。</p></div><div class="microscope-card"><span>3</span><p>Temporary file 是容量層，不是自動錯誤。</p></div><div class="microscope-card"><span>4</span><p>Client write AGAIN 時不能繼續無界讀 upstream。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 先分清 buffered 與 non-buffered path，它們使用不同 handlers/structures。
- Busy/free/out chains 的 ownership 轉移是理解 event pipe 的核心。
- Temporary file 不是失敗；它是明確的容量策略。
- 關閉 upstream read interest 是 backpressure，不代表 upstream connection 出錯。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/event/ngx_event_pipe.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event_pipe.c#L1) · [`src/http/ngx_http_upstream.c#L3010`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L3010) · [`src/http/ngx_http_upstream.c#L3488`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L3488)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Buffer size不是總memory。要計算每request buffers、busy chains、header buffer、filter額外buffer，再乘concurrency；temp file則把壓力轉到disk與I/O queue。

Streaming不等於零拷貝，也不保證低tail latency。Filter、TLS、HTTP/2 framing、socket buffer仍可copy；小chunk過多還增加syscall與packet overhead。

Cache通常需要較完整的buffer/store語意；真正即時streaming與cache fill可能衝突，需要明確產品選擇。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Event-driven pump</h3><p>兩側 readiness 共同驅動資料搬運。</p></div><div class="pattern-card"><h3>Elastic buffering</h3><p>memory 快路徑不足時使用 disk 擴充，但仍有上限。</p></div><div class="pattern-card"><h3>Producer–consumer decoupling</h3><p>buffer 讓 backend 與 client 的 active lifetime 部分分離。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 用slow client比較buffering on/off的backend完成時間。
2. 限制buffer讓response落temp file，觀察disk I/O與memory。
3. 做SSE endpoint，測量首event與每event延遲。
4. 增加並發量，計算設定推導的memory上限並與RSS比較。

## 常見誤解與失敗模式

- 用單一buffer大小估算總memory。
- 宣稱streaming就是zero-copy。
- 忽略小chunk/TLS/filter帶來的額外buffer與syscall。

## 可以帶走的 Coding／CS 能力

- 設計bounded async pipeline與spooling。
- 量化latency、throughput、memory、disk與connection occupancy。
- 辨別產品上的realtime需求與基礎設施buffer策略。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Buffering 解決單次 response；下一章看 proxy cache 如何讓結果跨 requests 重用。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Buffering如何縮短backend connection占用？</summary>

NGINX可快速讀走response到memory/disk，讓backend完成並釋放socket，之後按client速度輸出。

</details>

<details class="qa" markdown="1">
<summary>Q2. Non-buffered為何仍需要buffer？</summary>

Socket與filters以chunk運作，partial read/write必須保存bytes；non-buffered指不主動完整吸收/落盤，不是完全零緩衝。

</details>

<details class="qa" markdown="1">
<summary>Q3. Busy buffers limit控制什麼？</summary>

限制已交給downstream filter但尚未可重用的buffer量，避免慢client讓所有input buffers永久被占住。

</details>

<details class="qa" markdown="1">
<summary>Q4. Temp file何時是合理設計？</summary>

Response大、backend快、client慢且memory需有界時；若disk成瓶頸或需求是真即時streaming，則需調整。

</details>

<details class="qa" markdown="1">
<summary>Q5. 為何SSE常需要關buffering？</summary>

應用期望每個event盡快到client；中介等待填滿buffer會增加可見延遲。但仍需flush語意與proxy/client backpressure。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何選buffer策略？</summary>

以body size分布、client速度、backend成本、TTFB/p99、memory/disk budget、cache與retry需求做壓測，不能只用通用最佳實務。

</details>

---

# 第 33 章　Proxy Cache

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Proxy cache</h3><div class="foundation-block"><span>白話定義</span><p>保存 backend response，讓之後相同 cache key 的 requests 可直接重用，不必每次打 backend。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>熱門圖片第一次向 backend 取得，接下來一萬個 clients 從 cache 讀。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 將 body 放 disk，metadata/locks 放 shared memory，並管理 key、freshness 與 eviction。</p></div></section><section class="foundation-card"><h3>Fresh、stale 與 revalidation</h3><div class="foundation-block"><span>白話定義</span><p>Fresh 表示 cache 仍可直接使用；stale 表示期限已過；revalidation 是詢問 backend 內容是否真的改變。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>過期圖片可用 If-Modified-Since 驗證，若 backend 回 304 就延長使用。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX policy 決定何時更新、backend 故障時是否暫用 stale response。</p></div></section><section class="foundation-card"><h3>Cache stampede</h3><div class="foundation-block"><span>白話定義</span><p>熱門 key 同時失效時，大量 requests 一起穿透到 backend，形成瞬間尖峰。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>一萬個 users 在同一秒發現首頁 cache 過期。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 可用 cache lock 讓一個 request 更新，其餘等待或使用 stale data。</p></div></section><section class="foundation-card"><h3>Shared memory</h3><div class="foundation-block"><span>白話定義</span><p>可被多個 processes 看見的同一塊記憶體。因為會同時讀寫，所以通常需要 atomic operation 或 lock。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>所有 workers 共用 rate-limit counter，不能只存在某一個 worker 的一般 heap。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 shared memory zones 保存 cache metadata、upstream state 與跨 worker counters。</p></div></section></div>



<p class="chapter-question">Cache hit為何能繞過backend，cache miss又如何避免大量request同時擊穿同一個key？</p>

<div class="chapter-meta"><span>難度：進階</span><span>cache · shared metadata · thundering herd</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解cache key、metadata、shared zone、file body、loader/manager、lock與stale策略。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node active"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-32-buffering-streaming-與慢速-client"><span>上一站</span><strong>32. Buffering、Streaming 與慢速 Client</strong></a><div class="position-card current"><span>你在這裡</span><strong>33. Proxy Cache</strong></div><a class="position-card" href="#chapter-34-memory-pool-與生命週期"><span>下一站</span><strong>34. Memory Pool 與生命週期</strong></a></div>

本章位於 **Part 5：Proxy、Upstream 與負載均衡**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Proxy cache 讓多個 client requests 共用先前的 backend response，降低 backend load 與 latency。但 cache 不只是 key-value map：body 在 disk，metadata/locks 在 shared memory，還要處理 freshness、revalidation、stale、loader/manager 與同 key 併發。

Use case 是大量讀多寫少內容，或 backend 暫時故障時提供 stale response。沒有 cache lock，熱門 key 過期的一瞬間可能讓數百 requests 同時打 backend，形成 thundering herd。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Proxy cache 讓多個 client requests 共用先前的 backend response，降低 backend load 與 latency。但 cache 不只是 key-value map：body 在 disk，metadata/locks 在 shared memory，還要處理 freshness、revalidation、stale、loader/manager 與同 key 併發。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是大量讀多寫少內容，或 backend 暫時故障時提供 stale response。沒有 cache lock，熱門 key 過期的一瞬間可能讓數百 requests 同時打 backend，形成 thundering herd。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Shared HTTP response cache」這個責任邊界；接收 cache key + request cache policy + backend response，交付 fresh/stale/revalidated response 或 cache miss。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 shared metadata zone、disk files、per-request cache ctx 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 stampede、stale metadata、disk eviction、partial file、錯誤 cache personalized content。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Shared HTTP response cache</p></div><div class="contract-card"><span>接收什麼</span><p>cache key + request cache policy + backend response</p></div><div class="contract-card"><span>產生什麼</span><p>fresh/stale/revalidated response 或 cache miss</p></div><div class="contract-card"><span>狀態由誰保存</span><p>shared metadata zone、disk files、per-request cache ctx</p></div><div class="contract-card"><span>主要失敗出口</span><p>stampede、stale metadata、disk eviction、partial file、錯誤 cache personalized content</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>計算 normalized cache key</p></div><div class="flow-step"><span>2</span><p>在 shared metadata 查 entry</p></div><div class="flow-step"><span>3</span><p>fresh hit 直接開檔送 response</p></div><div class="flow-step"><span>4</span><p>stale/miss 時決定 lock/wait/bypass</p></div><div class="flow-step"><span>5</span><p>單一 owner 向 upstream 取資料</p></div><div class="flow-step"><span>6</span><p>邊收 response 邊寫 temporary cache file</p></div><div class="flow-step"><span>7</span><p>成功後 atomic rename/publish metadata</p></div><div class="flow-step"><span>8</span><p>manager/loader 維護容量與重啟恢復</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
request → compute cache key → shared metadata lookup
   ├─ HIT   → open cached file → filters → client
   ├─ STALE → policy: serve stale / revalidate
   └─ MISS  → optional key lock
                   │ leader fetches backend
                   └ followers wait/bypass

shared memory: keys/status/usage
disk files: headers + response body
```

## 從零建立心智模型

Proxy cache把熱門lookup metadata放shared memory zone，把實際response放filesystem。Worker可跨process協調同一key狀態，而不把大body塞進共享heap。

Key由scheme、method、host、URI等組合；若漏掉會影響representation的header/user維度，可能產生錯誤資料或安全洩漏。反之維度過多降低hit ratio。

Cache lock讓第一個miss成為leader，其餘同key request等待或依policy bypass，降低thundering herd。Stale-while-error/update則用舊資料換可用性，必須接受freshness tradeoff。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

普通 dict cache 沒有 freshness、single-flight、disk publish 或跨 worker metadata。這個縮小模型示範同 key 只讓一個 owner 回源，其他 callers 等待結果，避免熱門 key 同時擊穿 backend。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>cache</code></td><td>shared cache metadata + cache files 的概念合體</td></tr><tr><td>per-key <code>lock</code></td><td>cache lock/single-flight 防 stampede</td></tr><tr><td><code>expires</code></td><td>valid_sec/freshness metadata</td></tr><tr><td><code>loader</code></td><td>cache miss 後進 upstream</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_file_cache.c`，官方 `release-1.31.5` 第 265–312 行

```c
ngx_http_file_cache_open(ngx_http_request_t *r)
{
    ngx_int_t                  rc, rv;
    ngx_uint_t                 test;
    ngx_http_cache_t          *c;
    ngx_pool_cleanup_t        *cln;
    ngx_open_file_info_t       of;
    ngx_http_file_cache_t     *cache;
    ngx_http_core_loc_conf_t  *clcf;

    c = r->cache;

    if (c->waiting) {
        return NGX_AGAIN;
    }

    if (c->reading) {
        return ngx_http_file_cache_read(r, c);
    }

    cache = c->file_cache;

    if (c->node == NULL) {
        cln = ngx_pool_cleanup_add(r->pool, 0);
        if (cln == NULL) {
            return NGX_ERROR;
        }

        cln->handler = ngx_http_file_cache_cleanup;
        cln->data = c;
    }

    c->buffer_size = c->body_start;

    rc = ngx_http_file_cache_exists(cache, c);

    ngx_log_debug2(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                   "http file cache exists: %i e:%d", rc, c->exists);

    if (rc == NGX_ERROR) {
        return rc;
    }

    if (rc == NGX_AGAIN) {
        return NGX_HTTP_CACHE_SCARCE;
    }

    if (rc == NGX_OK) {
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Upstream init先依config計算key並開啟file cache。</p></div><div class="source-step"><span>2</span><p>Shared rbtree/queue查metadata、狀態、uses與validity。</p></div><div class="source-step"><span>3</span><p>Hit讀cache header/body，可能直接完成而不建upstream。</p></div><div class="source-step"><span>4</span><p>Miss取得lock或等待，leader走正常upstream並寫temp/cache file。</p></div><div class="source-step"><span>5</span><p>Manager清理inactive/超量cache，loader在啟動時把disk metadata載回shared zone。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>真實 NGINX 的 body 多在 disk，shared memory 主要保存 metadata/index。</p></div><div class="microscope-card"><span>2</span><p>Cache key 要包含所有會改變 response 的維度。</p></div><div class="microscope-card"><span>3</span><p>Temporary file 完成後才 atomic publish，避免讀到半檔。</p></div><div class="microscope-card"><span>4</span><p>Stale、revalidate、bypass、lock timeout 都是不同 policy branch。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Cache key 必須包含真正影響 response 的維度，否則會資料洩漏。
- Shared memory node 不是 response body；body 通常在 cache file。
- Stale-while-error 與 stale-while-updating 是可用性政策，不是免費正確性。
- Publish cache file 要避免其他 worker 看見半寫入內容；注意 temp file 與 rename。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_cache.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_cache.h#L1) · [`src/http/ngx_http_file_cache.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_file_cache.c#L1) · [`src/http/ngx_http_upstream.c#L897`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L897)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Cache correctness包含vary、Set-Cookie、Authorization、range、revalidation與purge。簡化成key→bytes容易犯跨使用者洩漏或保存不可cache response。

原子發布通常先寫temporary file，再rename成cache path，避免讀者看到半寫檔；metadata狀態需與file lifecycle協調。

Cache stampede不只發生miss，也發生大量key同時過期。Lock、stale serving、TTL jitter、background update與上游capacity共同處理。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Cache-aside in proxy pipeline</h3><p>先查 cache，miss 才進 upstream。</p></div><div class="pattern-card"><h3>Single flight / cache lock</h3><p>同 key 同時只讓一個 request 回源。</p></div><div class="pattern-card"><h3>Metadata/data split</h3><p>小而熱的 index 在 shared memory，大 body 在 filesystem。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 讓backend計數，分別驗證HIT/MISS/EXPIRED/STALE。
2. 100個並發request打同一冷key，比較cache lock on/off的backend次數。
3. 修改cache key漏掉query或user維度，觀察錯誤並立即復原。
4. 停止backend，測試use_stale policy與資料年齡。

## 常見誤解與失敗模式

- Cache key漏掉影響內容的tenant/auth/language維度。
- 所有entry同時固定TTL過期造成stampede。
- 把shared zone大小當disk cache容量。

## 可以帶走的 Coding／CS 能力

- 理解metadata/data分層、atomic publish與cache coherence。
- 設計single-flight、stale與TTL jitter。
- 從correctness/security而不只hit ratio評估cache。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Proxy 路徑到此完整；Part 6 回頭解剖支撐所有章節的 memory、container、buffer 與 module primitives。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為何metadata放shared memory、body放disk？</summary>

跨worker需快速協調key與狀態，但body可能很大；共享區適合小而熱的index，filesystem適合容量與持久資料。

</details>

<details class="qa" markdown="1">
<summary>Q2. Cache key漏維度最嚴重的後果？</summary>

不同使用者或representation命中同entry，可能回錯內容甚至洩漏私人資料；這是correctness與security事故。

</details>

<details class="qa" markdown="1">
<summary>Q3. Cache lock如何減少擊穿？</summary>

同key只允許leader取backend，followers等待、bypass或讀stale；把N次昂貴生成合併為一次single-flight。

</details>

<details class="qa" markdown="1">
<summary>Q4. 為何需要stale策略？</summary>

Backend故障或更新中仍可用較舊資料維持可用性與降低尖峰；代價是freshness與需清楚標示的資料時效。

</details>

<details class="qa" markdown="1">
<summary>Q5. Shared zone滿和disk滿有何不同？</summary>

前者無法追蹤更多keys/metadata，即使disk仍有空間；後者限制body容量。兩者需獨立監控與清理。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何避免半寫cache file被讀？</summary>

先寫獨立temp file並完成header/body與fsync policy，再以原子rename發布，同時更新metadata可見狀態。

</details>

---
