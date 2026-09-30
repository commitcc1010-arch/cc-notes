---
title: "從讀懂走向真的會"
part: 7
source_baseline: release-1.31.5
---

# Part 7　從讀懂走向真的會

依序寫 content、access、variable/filter、streaming 與 load-balancer modules，最後用故障注入和歷史 commit 建立 maintainer 視角。

# 第 39 章　實作 Hello Content Module

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Content handler</h3><div class="foundation-block"><span>白話定義</span><p>在 HTTP phase pipeline 中負責真正產生 response，或啟動一個之後會產生 response 的 async 工作。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Hello module 直接回文字；proxy handler 則啟動 upstream 交易。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Handler 必須設定 status/headers/body，正確使用 filters，並遵守 HEAD、partial write 與 finalize contract。</p></div></section><section class="foundation-card"><h3>Status、response headers 與 body</h3><div class="foundation-block"><span>白話定義</span><p>Status 表示結果類型，headers 描述 response metadata，body 才是主要內容；某些 method/status 不允許 body。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>204 No Content</code> 不應附一般 response body；HEAD 回覆 headers 但不傳實際 body。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Module 必須先正確設定 headers，再呼叫 header/body filter，並遵守 Content-Length 與 final flags。</p></div></section><section class="foundation-card"><h3>Response 與 filter chain</h3><div class="foundation-block"><span>白話定義</span><p>Content handler 產生 response；filters 依序檢查或轉換 headers/body，再交給下一層。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Proxy body 先經 gzip，再套 chunked framing，最後寫入 socket。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 top/next function pointers 串接 filters，新增功能不必修改每個 content module。</p></div></section><section class="foundation-card"><h3>Handler 與 return code contract</h3><div class="foundation-block"><span>白話定義</span><p>Handler 是處理一小段責任的函式；它的 return code 不是隨意數字，而是告訴框架下一步。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>DECLINED</code> 可表示『我不處理，交給下一個』；<code>AGAIN</code> 表示 async 工作尚未完成。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>讀 NGINX source 時必須同時看 caller 如何解釋回傳值，不能只讀 handler 本身。</p></div></section></div>



<p class="chapter-question">如何寫出第一個真正被location選中、建立response並安全送出的HTTP模組？</p>

<div class="chapter-meta"><span>難度：實作</span><span>content handler · dynamic module · response</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

走完directive、loc config、content handler、header/body output與dynamic-module build的最小閉環。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node active"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-38-module-system-與可擴充架構"><span>上一站</span><strong>38. Module System 與可擴充架構</strong></a><div class="position-card current"><span>你在這裡</span><strong>39. 實作 Hello Content Module</strong></div><a class="position-card" href="#chapter-40-實作-access-phase-module"><span>下一站</span><strong>40. 實作 Access Phase Module</strong></a></div>

本章位於 **Part 7：從讀懂走向真的會**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

第一個 module 的目標不是做複雜功能，而是走完『directive → config → content handler → response filter → cleanup』閉環。只有親手註冊並看到 request 進入 handler，module architecture 才從名詞變成可操作模型。

Use case 是一個 location 直接回傳文字與正確 HTTP status/headers/body。它會暴露最基本的 pool allocation、buffer flags 與 send header/output filter contract。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>第一個 module 的目標不是做複雜功能，而是走完『directive → config → content handler → response filter → cleanup』閉環。只有親手註冊並看到 request 進入 handler，module architecture 才從名詞變成可操作模型。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是一個 location 直接回傳文字與正確 HTTP status/headers/body。它會暴露最基本的 pool allocation、buffer flags 與 send header/output filter contract。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Minimal HTTP content module」這個責任邊界；接收 location directive + routed request，交付 合法的 HTTP response。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 location conf、request pool buffer/chain 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 directive context 錯誤、Content-Length 不符、buffer lifetime/last flag 錯誤。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Minimal HTTP content module</p></div><div class="contract-card"><span>接收什麼</span><p>location directive + routed request</p></div><div class="contract-card"><span>產生什麼</span><p>合法的 HTTP response</p></div><div class="contract-card"><span>狀態由誰保存</span><p>location conf、request pool buffer/chain</p></div><div class="contract-card"><span>主要失敗出口</span><p>directive context 錯誤、Content-Length 不符、buffer lifetime/last flag 錯誤</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>定義 module commands 與 context</p></div><div class="flow-step"><span>2</span><p>create location conf</p></div><div class="flow-step"><span>3</span><p>directive setter 安裝 content handler/文字</p></div><div class="flow-step"><span>4</span><p>request location match 後進 handler</p></div><div class="flow-step"><span>5</span><p>檢查允許 method</p></div><div class="flow-step"><span>6</span><p>設定 status/content type/content length</p></div><div class="flow-step"><span>7</span><p>從 request pool 建 buffer/chain</p></div><div class="flow-step"><span>8</span><p>send header，再交 output filter</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

第一個module應只做一件事：在location中啟用後回固定文字。這個練習把設定期與request期串起來，並強迫你正確處理method、header、buffer與return code。

Loc config保存文字。Directive callback解析參數並把core loc conf的handler設成自己的content handler。Request到來時配置temp buffer、寫內容、設`last_buf`，先送header再用`ngx_http_output_filter`送chain。

即使只是Hello也要處理HEAD：可以送headers但不必body；Content-Length仍描述GET表示的長度。不要直接對client fd呼叫write，否則繞過TLS、HTTP/2與filter chain。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

第一個 module 不應直接寫 socket；那會繞過 TLS、HTTP/2、gzip 與 partial write。正確做法是建立 framework response object/buffer，再交給共同 output pipeline。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Response</code></td><td><code>r-&gt;headers_out</code> + output buffer chain</td></tr><tr><td>handler</td><td>core loc conf 中安裝的 content handler</td></tr><tr><td>body bytes</td><td>request pool 配置的 <code>ngx_buf_t</code></td></tr><tr><td>framework return</td><td><code>ngx_http_send_header</code> + <code>ngx_http_output_filter</code></td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/modules/ngx_http_empty_gif_module.c`，官方 `release-1.31.5` 第 92–139 行

```c

ngx_module_t  ngx_http_empty_gif_module = {
    NGX_MODULE_V1,
    &ngx_http_empty_gif_module_ctx, /* module context */
    ngx_http_empty_gif_commands,   /* module directives */
    NGX_HTTP_MODULE,               /* module type */
    NULL,                          /* init master */
    NULL,                          /* init module */
    NULL,                          /* init process */
    NULL,                          /* init thread */
    NULL,                          /* exit thread */
    NULL,                          /* exit process */
    NULL,                          /* exit master */
    NGX_MODULE_V1_PADDING
};


static ngx_str_t  ngx_http_gif_type = ngx_string("image/gif");


static ngx_int_t
ngx_http_empty_gif_handler(ngx_http_request_t *r)
{
    ngx_http_complex_value_t  cv;

    if (!(r->method & (NGX_HTTP_GET|NGX_HTTP_HEAD))) {
        return NGX_HTTP_NOT_ALLOWED;
    }

    ngx_memzero(&cv, sizeof(ngx_http_complex_value_t));

    cv.value.len = sizeof(ngx_empty_gif);
    cv.value.data = ngx_empty_gif;
    r->headers_out.last_modified_time = 23349600;

    return ngx_http_send_response(r, NGX_HTTP_OK, &ngx_http_gif_type, &cv);
}


static char *
ngx_http_empty_gif(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
{
    ngx_http_core_loc_conf_t  *clcf;

    clcf = ngx_http_conf_get_module_loc_conf(cf, ngx_http_core_module);
    clcf->handler = ngx_http_empty_gif_handler;

    return NGX_CONF_OK;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>建立module descriptor、HTTP context與command table。</p></div><div class="source-step"><span>2</span><p>Create loc conf配置並設UNSET；directive callback填文字並安裝handler。</p></div><div class="source-step"><span>3</span><p>Handler驗證GET/HEAD，discard不需要的request body。</p></div><div class="source-step"><span>4</span><p>設定<code>headers_out.status/content_type/content_length_n</code>。</p></div><div class="source-step"><span>5</span><p>配置buffer/chain，標<code>last_buf</code>並呼叫top output filter。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Directive callback 如何把 handler 安裝到 location。</p></div><div class="microscope-card"><span>2</span><p>GET/HEAD/body discard/header-only 分支。</p></div><div class="microscope-card"><span>3</span><p>Content-Length、buffer length 與 <code>last_buf</code> 必須一致。</p></div><div class="microscope-card"><span>4</span><p>Output filter 的 return code 可能代表 AGAIN/error，不是一定立即送完。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 先確認 handler 何時被設到 core loc conf，而不只是函式本身。
- HEAD request 與 header-only response 不應仍送 body。
- Output filter 可能回 AGAIN；不要假設一次呼叫已送完。
- Buffer 的 `last_buf`/memory flags 與 Content-Length 必須一致。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/modules/ngx_http_empty_gif_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_empty_gif_module.c#L1) · [`src/http/modules/ngx_http_stub_status_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_stub_status_module.c#L1) · [`auto/module#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/auto/module#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Dynamic module的`config`檔告訴build system名稱、type與sources。使用和目標NGINX相容的source/configure flags編譯，再用`load_module`載入。

Handler返回值要依output API contract。`ngx_http_send_header`可能表示header-only或error；body output後通常返回filter結果。不要既return HTTP status又另外send一份response造成double finalize。

內容放request pool，output filter可能在handler返回後仍引用；stack buffer或立即free的heap不可用。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Vertical feature slice</h3><p>從 config 到 runtime output 的最小完整功能。</p></div><div class="pattern-card"><h3>Framework contract learning</h3><p>透過真實 hook/return code 理解 core。</p></div><div class="pattern-card"><h3>Ownership by request</h3><p>response metadata 與 buffers 由 request pool 管理。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 建立`ngx_http_hello_module`目錄、source與config檔，編成dynamic module。
2. 加入`load_module`與`location /hello { hello "NGINX"; }`。
3. 用GET、HEAD、POST驗證status、length與body。
4. 開gzip與HTTP/2，證明handler沒有直接依賴socket write。

## 常見誤解與失敗模式

- 使用stack上的body在handler返回後被filter引用。
- 忘記last_buf，response不完成。
- 直接write fd，繞過filter/TLS/protocol framing。

## 可以帶走的 Coding／CS 能力

- 完成plugin從config到runtime的端到端閉環。
- 正確使用framework output contract與request lifetime。
- 用最小功能建立可擴充、可測試的垂直切片。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

會產生內容後，下一章改成在 content 之前做 access decision，理解 phase short circuit。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼要設定Content-Length？</summary>

讓HTTP framing明確，HEAD也能描述GET的representation；若使用chunked/filter改寫，header filter可能調整，但module應提供正確已知長度。

</details>

<details class="qa" markdown="1">
<summary>Q2. Body為何要從request pool配置？</summary>

Output可能因client慢而跨event存活；stack在handler返回後失效，request pool保證到finalize前有效。

</details>

<details class="qa" markdown="1">
<summary>Q3. HEAD request應如何處理？</summary>

設定與GET相同的status/content headers，send header後因`r->header_only`不送body。

</details>

<details class="qa" markdown="1">
<summary>Q4. 為什麼不用`send()`？</summary>

Top filter處理HTTP版本、TLS、chunking、gzip、range、partial write與backpressure；直接send會破壞所有抽象。

</details>

<details class="qa" markdown="1">
<summary>Q5. Directive如何讓location使用handler？</summary>

Set callback取得core loc conf，將其handler function pointer設為module content handler；location match後content phase呼叫它。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何證明module遵守非阻塞模型？</summary>

用slow client/HTTP2/TLS測試，handler只建立buffers交filter，partial output由write event續送，沒有blocking loop。

</details>

---

# 第 40 章　實作 Access Phase Module

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Authentication、authorization 與 access phase</h3><div class="foundation-block"><span>白話定義</span><p>Authentication 確認你是誰；authorization 判斷你能做什麼。Access phase 是 content 工作前做允許／拒絕決策的位置。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>API key 可識別 caller，但是否能存取 admin endpoint 是另一個授權決策。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX access handler 回 OK、DECLINED 或 HTTP error，並與其他 access modules/satisfy policy 共存。</p></div></section><section class="foundation-card"><h3>HTTP phase engine</h3><div class="foundation-block"><span>白話定義</span><p>把 request 處理拆成有順序的階段，每個 module 可以把 handler 註冊到適合的階段。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>先 rewrite URI，再做 access control，最後產生或 proxy content。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 config time 編譯 handler pipeline，runtime 用 return code 決定繼續、跳轉、暫停或結束。</p></div></section><section class="foundation-card"><h3>Configuration context 與 merge</h3><div class="foundation-block"><span>白話定義</span><p>同一設定可能出現在全域、server 或 location；merge 是把父層預設值與子層覆寫組成最終設定。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>父 location 設 timeout 30 秒，子 location 可改成 3 秒；沒改的欄位繼承父層。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 config time 建立多份 conf object，runtime request 只需選擇合併後的結果。</p></div></section><section class="foundation-card"><h3>Fail closed</h3><div class="foundation-block"><span>白話定義</span><p>發生解析、設定或驗證錯誤時預設拒絕，而不是因為檢查失敗就放行。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Token verifier timeout 時回 503/拒絕，不能把它當成『驗證通過』。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Security-sensitive NGINX modules 必須讓每個 error branch 都有明確且保守的結果。</p></div></section></div>



<p class="chapter-question">如何在content handler之前依header拒絕request，並正確使用`NGX_DECLINED`與HTTP status？</p>

<div class="chapter-meta"><span>難度：實作</span><span>access phase · authorization · short circuit</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

實作簡單API key gate，理解phase registration、config inheritance、constant-time比較與fail-closed。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node active"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-39-實作-hello-content-module"><span>上一站</span><strong>39. 實作 Hello Content Module</strong></a><div class="position-card current"><span>你在這裡</span><strong>40. 實作 Access Phase Module</strong></div><a class="position-card" href="#chapter-41-加入自訂-variable-與-header-filter"><span>下一站</span><strong>41. 加入自訂 Variable 與 Header Filter</strong></a></div>

本章位於 **Part 7：從讀懂走向真的會**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Access control 必須在昂貴 content/upstream 工作開始前執行，並且能與其他 access modules 共存。這一章用自訂 header/token 規則練習 access phase、configuration merge 與拒絕 response。

Use case 是內部 endpoint、簡化 API key 或 allowlist。真正 production auth 會更複雜，但 phase contract 相同：允許就 declined/continue，拒絕就回 401/403，async 驗證則保存 state 後暫停。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Access control 必須在昂貴 content/upstream 工作開始前執行，並且能與其他 access modules 共存。這一章用自訂 header/token 規則練習 access phase、configuration merge 與拒絕 response。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是內部 endpoint、簡化 API key 或 allowlist。真正 production auth 會更複雜，但 phase contract 相同：允許就 declined/continue，拒絕就回 401/403，async 驗證則保存 state 後暫停。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Access-phase policy module」這個責任邊界；接收 parsed request + merged location policy，交付 continue pipeline 或拒絕 status。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 location conf + optional request ctx 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 fail-open、安全 phase 順序、internal redirect 重入、secret comparison 問題。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Access-phase policy module</p></div><div class="contract-card"><span>接收什麼</span><p>parsed request + merged location policy</p></div><div class="contract-card"><span>產生什麼</span><p>continue pipeline 或拒絕 status</p></div><div class="contract-card"><span>狀態由誰保存</span><p>location conf + optional request ctx</p></div><div class="contract-card"><span>主要失敗出口</span><p>fail-open、安全 phase 順序、internal redirect 重入、secret comparison 問題</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>directive 解析 policy/token</p></div><div class="flow-step"><span>2</span><p>merge parent/child loc conf</p></div><div class="flow-step"><span>3</span><p>postconfiguration 把 handler push 到 access phase</p></div><div class="flow-step"><span>4</span><p>request 到 access phase 時取得 config</p></div><div class="flow-step"><span>5</span><p>讀 header/variable 並驗證</p></div><div class="flow-step"><span>6</span><p>未啟用則 DECLINED</p></div><div class="flow-step"><span>7</span><p>允許則 OK/DECLINED 依 satisfy contract</p></div><div class="flow-step"><span>8</span><p>拒絕則設定 challenge/status 並 finalize</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
postconfiguration
  phases[NGX_HTTP_ACCESS_PHASE].handlers.push(api_key_handler)

request
  ├─ module未啟用 → NGX_DECLINED
  ├─ key正確     → NGX_OK / phase checker繼續
  └─ key缺失/錯  → 401/403 → finalize

satisfy any/all 會影響多個access modules如何合併。
```

## 從零建立心智模型

Access module不生成正常內容，而是在access phase做決策。Loc config保存是否啟用與expected secret來源；handler取request header，未啟用回DECLINED，驗證失敗回HTTP status。

回OK還是DECLINED要看你希望的語意與access checker。DECLINED表示本module不做決定；OK表示此access check通過，但`satisfy any/all`和其他modules仍由checker聚合。

真實認證不應把plaintext secret直接放容易暴露的config/log，也不應用可觀察timing比較高價值token。練習重點是phase/lifetime，不是自製production auth。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

把 auth 寫進每個 content handler 會重複且容易漏保護。Access middleware 在固定 phase 執行；未啟用就 DECLINED，拒絕就 short-circuit，允許則依 satisfy policy 繼續。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>access handler</td><td>掛在 <code>NGX_HTTP_ACCESS_PHASE</code> 的 module handler</td></tr><tr><td><code>DECLINED</code></td><td>未處理／允許其他 handlers 繼續</td></tr><tr><td>403</td><td>HTTP status short-circuit phase engine</td></tr><tr><td>configured key</td><td>merged location configuration</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/modules/ngx_http_access_module.c`，官方 `release-1.31.5` 第 123–170 行

```c
ngx_http_access_handler(ngx_http_request_t *r)
{
    struct sockaddr_in          *sin;
    ngx_http_access_loc_conf_t  *alcf;
#if (NGX_HAVE_INET6)
    u_char                      *p;
    in_addr_t                    addr;
    struct sockaddr_in6         *sin6;
#endif

    alcf = ngx_http_get_module_loc_conf(r, ngx_http_access_module);

    switch (r->connection->sockaddr->sa_family) {

    case AF_INET:
        if (alcf->rules) {
            sin = (struct sockaddr_in *) r->connection->sockaddr;
            return ngx_http_access_inet(r, alcf, sin->sin_addr.s_addr);
        }
        break;

#if (NGX_HAVE_INET6)

    case AF_INET6:
        sin6 = (struct sockaddr_in6 *) r->connection->sockaddr;
        p = sin6->sin6_addr.s6_addr;

        if (alcf->rules && IN6_IS_ADDR_V4MAPPED(&sin6->sin6_addr)) {
            addr = (in_addr_t) p[12] << 24;
            addr += p[13] << 16;
            addr += p[14] << 8;
            addr += p[15];
            return ngx_http_access_inet(r, alcf, htonl(addr));
        }

        if (alcf->rules6) {
            return ngx_http_access_inet6(r, alcf, p);
        }

        break;

#endif

#if (NGX_HAVE_UNIX_DOMAIN)

    case AF_UNIX:
        if (alcf->rules_un) {
            return ngx_http_access_unix(r, alcf);
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Create/merge loc conf保存enabled與key reference。</p></div><div class="source-step"><span>2</span><p>Postconfiguration把handler加入ACCESS phase handlers array。</p></div><div class="source-step"><span>3</span><p>Handler找自訂header，處理missing/duplicate/invalid。</p></div><div class="source-step"><span>4</span><p>比較成功後回適當control code；失敗回401/403。</p></div><div class="source-step"><span>5</span><p>測試與allow/deny、auth basic及<code>satisfy</code>的組合順序。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Return code 要配合 access phase checker/satisfy policy理解。</p></div><div class="microscope-card"><span>2</span><p>未設定與設定為空值需用 sentinel 分辨。</p></div><div class="microscope-card"><span>3</span><p>Internal redirect/subrequest 是否重驗 policy 要明確。</p></div><div class="microscope-card"><span>4</span><p>錯誤 branch 預設 fail closed，且不要將 secret 寫入 log。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 理解 access checker 對 OK、DECLINED、401、403 的處理。
- Internal redirect 可能再次進 phase；module ctx 要處理重入。
- 不要把 secret 直接長期明文 log；比較也要考慮 timing/normalization。
- Subrequest 是否應繼承或重新驗證 policy 必須明確。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
ngx_int_t api_key_access(ngx_http_request_t *r) {
    conf_t *cf = get_loc_conf(r);
    if (!cf->enabled) return NGX_DECLINED;

    ngx_str_t supplied = find_header(r, "X-API-Key");
    if (supplied.len == 0) return NGX_HTTP_UNAUTHORIZED;
    if (!constant_time_equal(supplied, cf->expected))
        return NGX_HTTP_FORBIDDEN;
    return NGX_OK;
}
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/modules/ngx_http_access_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_access_module.c#L1) · [`src/http/modules/ngx_http_auth_basic_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_auth_basic_module.c#L1) · [`src/http/ngx_http_core_module.c#L928`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_core_module.c#L928)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Fail-open/fail-closed需顯式決定。若外部auth subrequest timeout，安全系統通常fail closed，但可用性與緊急bypass需另設受控機制。

Header lookup可在known headers外掃generic list；若高頻使用，可註冊variable或預計算hash。永遠限制值長度並避免log secret。

Access decision可能需要async subrequest；此時handler要增加引用、保存ctx、返回suspension code，callback再恢復phase engine，不能block等遠端。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Policy enforcement point</h3><p>在固定 phase 集中安全判斷。</p></div><div class="pattern-card"><h3>Chain of responsibility</h3><p>多個 access handlers 可依 satisfy policy 組合。</p></div><div class="pattern-card"><h3>Fail closed</h3><p>配置或驗證異常不可意外繞過保護。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 加入`api_key`directive與access handler，測missing/wrong/correct。
2. 與`allow/deny`及`satisfy any/all`組合，記錄phase結果。
3. 確認access log/error log沒有輸出secret。
4. 把驗證改成auth subrequest，實作非阻塞resume。

## 常見誤解與失敗模式

- 未啟用時回OK，意外繞過其他access modules。
- 阻塞呼叫遠端auth服務。
- 把secret完整寫入debug/error log。

## 可以帶走的 Coding／CS 能力

- 理解middleware short-circuit與多policy聚合。
- 設計fail-open/fail-closed與async authorization。
- 處理secret comparison、logging與configuration scope。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

除了 phase，module 也常向其他 config/filter 暴露資料；下一章加入惰性 variable 與 response header。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 未啟用module為何通常回DECLINED？</summary>

表示本module不參與決策，讓同phase其他handlers繼續；回OK可能被`satisfy any`當成已通過。

</details>

<details class="qa" markdown="1">
<summary>Q2. 401和403應如何區分？</summary>

401通常表示需要/缺少有效authentication並可帶WWW-Authenticate；403表示已理解身份或憑證但不允許。實際API policy需一致。

</details>

<details class="qa" markdown="1">
<summary>Q3. 外部auth為何不能同步HTTP呼叫？</summary>

Worker event loop會被阻塞，所有同worker connections受影響；應用subrequest/async upstream並在callback恢復。

</details>

<details class="qa" markdown="1">
<summary>Q4. Constant-time比較能解決所有token安全嗎？</summary>

不能。它只降低某些timing side channel，仍需TLS、secret storage、rotation、length limit、rate limit與不記錄敏感值。

</details>

<details class="qa" markdown="1">
<summary>Q5. Config inheritance要注意什麼？</summary>

區分未設定、off與空值；child explicit設定應覆蓋parent，secret不可意外從不相關location繼承。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何測fail-closed？</summary>

讓auth backend timeout、連線失敗、回invalid response，確認protected route拒絕且無fallback繞過，同時保留可觀測error。

</details>

---

# 第 41 章　加入自訂 Variable 與 Header Filter

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Variable 與 lazy evaluation</h3><div class="foundation-block"><span>白話定義</span><p>Variable 提供統一名稱取得 request data；lazy evaluation 表示只有真的被 log/rewrite/header 使用時才計算。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>沒有任何 consumer 使用 request ID 時，不必為每個 request 都產生它。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX variable get handler 第一次被查詢時產生 value，並依 cache flags 決定是否重用。</p></div></section><section class="foundation-card"><h3>Correlation ID</h3><div class="foundation-block"><span>白話定義</span><p>在同一個邏輯 request 經過多個 logs/services 時保持不變的識別碼，用來把分散事件串回同一條因果鏈。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>req-7f2a</code> 同時出現在 client response header、NGINX access log 與 backend log。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>值應 request-scoped、只生成一次，並避免在 subrequest/filter 重入時重複加入 header。</p></div></section><section class="foundation-card"><h3>`ngx_http_request_t`</h3><div class="foundation-block"><span>白話定義</span><p>代表一次 HTTP request/response 交換的核心 object，不等於底層 TCP connection。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同一 keep-alive connection 可以先後建立兩個不同 request objects。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>它保存 method、URI、headers、body、module contexts、routing、upstream 與 output state。</p></div></section><section class="foundation-card"><h3>Response 與 filter chain</h3><div class="foundation-block"><span>白話定義</span><p>Content handler 產生 response；filters 依序檢查或轉換 headers/body，再交給下一層。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Proxy body 先經 gzip，再套 chunked framing，最後寫入 socket。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 top/next function pointers 串接 filters，新增功能不必修改每個 content module。</p></div></section></div>



<p class="chapter-question">如何讓`$request_id_short`可被log/config使用，並在response中安全加入一個header？</p>

<div class="chapter-meta"><span>難度：實作</span><span>variables · lazy evaluation · header filter</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解variable註冊與惰性求值、not_found/no_cacheable flags，以及header filter鏈。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node active"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-40-實作-access-phase-module"><span>上一站</span><strong>40. 實作 Access Phase Module</strong></a><div class="position-card current"><span>你在這裡</span><strong>41. 加入自訂 Variable 與 Header Filter</strong></div><a class="position-card" href="#chapter-42-實作-streaming-body-filter"><span>下一站</span><strong>42. 實作 Streaming Body Filter</strong></a></div>

本章位於 **Part 7：從讀懂走向真的會**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

NGINX variables 讓 log、rewrite、proxy headers 等消費者用統一名稱取得 request 資料。它們通常惰性求值，避免每個 request 都計算所有可能變數；header filter 則能把同一 request ID 安全送回 client。

Use case 是產生一次 request-scoped correlation ID，同時出現在 access log、upstream header 與 response header。若每個 consumer 各算一次，跨服務追蹤會得到不同 ID。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>NGINX variables 讓 log、rewrite、proxy headers 等消費者用統一名稱取得 request 資料。它們通常惰性求值，避免每個 request 都計算所有可能變數；header filter 則能把同一 request ID 安全送回 client。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是產生一次 request-scoped correlation ID，同時出現在 access log、upstream header 與 response header。若每個 consumer 各算一次，跨服務追蹤會得到不同 ID。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Lazy request value + header filter」這個責任邊界；接收 variable lookup 或 response-header phase，交付 穩定 request ID value 與新增 header。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 request module ctx/pool + variable cache metadata 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 stack pointer、stale cached value、重複 header、CRLF injection。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Lazy request value + header filter</p></div><div class="contract-card"><span>接收什麼</span><p>variable lookup 或 response-header phase</p></div><div class="contract-card"><span>產生什麼</span><p>穩定 request ID value 與新增 header</p></div><div class="contract-card"><span>狀態由誰保存</span><p>request module ctx/pool + variable cache metadata</p></div><div class="contract-card"><span>主要失敗出口</span><p>stack pointer、stale cached value、重複 header、CRLF injection</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>preconfiguration 註冊 variable name/get handler</p></div><div class="flow-step"><span>2</span><p>consumer 首次 lookup 時呼叫 get handler</p></div><div class="flow-step"><span>3</span><p>get/create request ctx 並生成一次 ID</p></div><div class="flow-step"><span>4</span><p>填 variable value flags/data/len</p></div><div class="flow-step"><span>5</span><p>後續 lookup 使用 cache</p></div><div class="flow-step"><span>6</span><p>header filter 讀同一 ctx/value</p></div><div class="flow-step"><span>7</span><p>安全 push header table element</p></div><div class="flow-step"><span>8</span><p>呼叫 next header filter</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
configuration:
register "$request_id_short" → get_handler

runtime consumer (log/header/script)
      ↓ evaluate variable lazily
get_handler(r, value, data)
      ↓ value { data, len, valid, not_found, no_cacheable }

response:
my_header_filter(r) → add X-Request-ID → next_header_filter(r)
```

## 從零建立心智模型

NGINX variable不是普通全域字串。Config-time註冊名稱與get/set handler；runtime只有consumer實際需要時才計算，結果可能cache在request variables array。

Get handler填`ngx_http_variable_value_t`的data/len與valid/not_found/no_cacheable。資料必須活到使用者完成，通常放request pool；不可回傳stack pointer。

Header filter可讀variable並push到`headers_out.headers`，然後呼叫next filter。它需避免重複執行時加入兩份、處理subrequest與header already sent狀態。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

每次 log/header 使用時都重新產生 request ID 會得到不同值；啟動時替所有 requests 預算又浪費。Lazy property 在第一次需要時生成並 cache，所有 consumers 讀同一份。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>cached_property</code></td><td>variable get handler + request variables cache</td></tr><tr><td>first lookup</td><td>consumer 取 indexed variable 時呼叫 get handler</td></tr><tr><td>cached string</td><td>request pool/module ctx 中穩定資料</td></tr><tr><td>second lookup</td><td><code>valid/not_found/no_cacheable</code> 控制的重用</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_variables.c`，官方 `release-1.31.5` 第 619–664 行

```c
ngx_http_get_indexed_variable(ngx_http_request_t *r, ngx_uint_t index)
{
    ngx_http_variable_t        *v;
    ngx_http_core_main_conf_t  *cmcf;

    cmcf = ngx_http_get_module_main_conf(r, ngx_http_core_module);

    if (cmcf->variables.nelts <= index) {
        ngx_log_error(NGX_LOG_ALERT, r->connection->log, 0,
                      "unknown variable index: %ui", index);
        return NULL;
    }

    if (r->variables[index].not_found || r->variables[index].valid) {
        return &r->variables[index];
    }

    v = cmcf->variables.elts;

    if (ngx_http_variable_depth == 0) {
        ngx_log_error(NGX_LOG_ERR, r->connection->log, 0,
                      "cycle while evaluating variable \"%V\"",
                      &v[index].name);
        return NULL;
    }

    ngx_http_variable_depth--;

    if (v[index].get_handler(r, &r->variables[index], v[index].data)
        == NGX_OK)
    {
        ngx_http_variable_depth++;

        if (v[index].flags & NGX_HTTP_VAR_NOCACHEABLE) {
            r->variables[index].no_cacheable = 1;
        }

        return &r->variables[index];
    }

    ngx_http_variable_depth++;

    r->variables[index].valid = 0;
    r->variables[index].not_found = 1;

    return NULL;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Preconfiguration或module init呼叫add variable，設定get handler。</p></div><div class="source-step"><span>2</span><p>Config compiler將變數名轉為index或script opcode。</p></div><div class="source-step"><span>3</span><p>Runtime第一次取值呼叫get handler並保存value metadata。</p></div><div class="source-step"><span>4</span><p>Header filter在top chain中執行，按條件加入table element。</p></div><div class="source-step"><span>5</span><p>呼叫next header filter完成protocol encoding。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Variable value 的 data pointer 不能指向 stack。</p></div><div class="microscope-card"><span>2</span><p><code>not_found</code> 與空字串不同。</p></div><div class="microscope-card"><span>3</span><p>若值可能隨時間變才設 <code>no_cacheable</code>。</p></div><div class="microscope-card"><span>4</span><p>Header filter 使用同一 ctx，並避免 subrequest/重入時重複加入。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Variable data 必須活到 consumer 完成，通常放 request pool。
- `not_found` 與存在但空字串語意不同。
- `no_cacheable` 決定同 request 多次讀取是否重算。
- Header filter 需考慮 subrequest、重入與 headers already sent。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_variables.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_variables.c#L1) · [`src/http/modules/ngx_http_headers_filter_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_headers_filter_module.c#L1) · [`src/http/ngx_http_header_filter_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_header_filter_module.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Variable cacheability影響一致性。若值在request期間不變，可cache；若每次讀取可能變，設no_cacheable讓consumer重算。錯設會得到stale或浪費CPU。

Request ID應在request早期一次生成並保存ctx，variable與header filter讀同一值；若兩邊各自生成，log與response無法關聯。

Header value是untrusted時需拒絕CR/LF，避免response splitting。NGINX核心有驗證，但module仍應限制來源與長度。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Lazy evaluation</h3><p>只有真正使用 variable 時才計算。</p></div><div class="pattern-card"><h3>Memoization</h3><p>request-stable value 計算一次，所有 consumers 共用。</p></div><div class="pattern-card"><h3>Correlation context</h3><p>同一 identity 穿過 logs、headers 與 upstream。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 註冊變數並放進access_log format，確認惰性求值。
2. 加入header filter，把同一ID送到response。
3. 同一request多次引用變數，確認只生成一次。
4. 建立subrequest，決定共用main ID或產生child ID並測試。

## 常見誤解與失敗模式

- Variable返回stack buffer。
- Log與response各生成不同request ID。
- Filter每次重入都追加header。

## 可以帶走的 Coding／CS 能力

- 理解惰性值、memoization與cacheability contract。
- 在pipeline中建立一致correlation ID。
- 安全擴充header並處理重入/subrequest。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

普通 header filter 只處理 metadata；下一章挑戰可跨任意 buffer 邊界保存狀態的 streaming body filter。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Variable為什麼惰性求值？</summary>

大量已註冊variables並非每request都使用；只有log/script/header真正引用時才付出計算與allocation成本。

</details>

<details class="qa" markdown="1">
<summary>Q2. `not_found` 與空字串差在哪裡？</summary>

Not found表示值不存在，可能影響rewrite條件與default；空字串是存在但長度零，語意不可混淆。

</details>

<details class="qa" markdown="1">
<summary>Q3. 何時設`no_cacheable`？</summary>

值在同一request不同讀取時間可能改變時；若request-stable應允許cache以保持一致並省成本。

</details>

<details class="qa" markdown="1">
<summary>Q4. Header filter如何避免重複加入？</summary>

用module ctx flag、先查既有header或限定main request/首次header path；理解filter可能因internal flow被再次觸發。

</details>

<details class="qa" markdown="1">
<summary>Q5. Request ID資料應放哪裡？</summary>

放request pool/module ctx，生命週期覆蓋log與output；若需跨服務，header value需穩定且長度受限。

</details>

<details class="qa" markdown="1">
<summary>Q6. Subrequest應共用ID嗎？</summary>

取決於trace模型。常見做法共用trace/root ID並另有span/child ID；必須明確，避免log關聯混亂。

</details>

---

# 第 42 章　實作 Streaming Body Filter

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Streaming body filter 與 chunk boundary</h3><div class="foundation-block"><span>白話定義</span><p>Filter 每次只看到一部分 bytes；任意語意 token 可能跨兩個 buffers，因此不能把每個 chunk 當完整字串。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>第一段以 <code>f</code> 結尾、第二段以 <code>oo</code> 開頭，合起來才是 <code>foo</code>。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX module ctx 保存跨 callback carry state，並傳遞 flush、sync、last 等 buffer flags。</p></div></section><section class="foundation-card"><h3>Buffer chain</h3><div class="foundation-block"><span>白話定義</span><p>把多段不一定連續、來源不同的資料，用 linked nodes 表示成一個輸出序列。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Response headers 在 memory，body 在 file，最後還有一個 end marker。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_chain_t</code> 串起 <code>ngx_buf_t</code>；partial write 只移動 positions，未送完 nodes 留在 busy chain。</p></div></section><section class="foundation-card"><h3>Backpressure（背壓）</h3><div class="foundation-block"><span>白話定義</span><p>下游處理不過來時，限制上游繼續產生或讀入資料，讓系統內的待處理資料有明確上限。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 每秒產生 10 MB，但手機只能收 100 KB；不能無限把差額塞進 memory。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 buffer 水位暫停 upstream read，等 client write 消耗資料後再恢復。</p></div></section><section class="foundation-card"><h3>State machine（狀態機）</h3><div class="foundation-block"><span>白話定義</span><p>把流程表示成有限狀態與允許的轉移。遇到等待時保存目前 state；事件到來後從該 state 繼續。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>CONNECTING → SENDING → READING_HEADER → STREAMING_BODY → DONE。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 常把 state 分散在 struct fields 與可替換 callbacks，而不是寫成一個巨大 switch。</p></div></section></div>



<p class="chapter-question">如果response被任意切成多個buffer，如何逐chunk轉換文字而不破壞跨chunk匹配、flush與backpressure？</p>

<div class="chapter-meta"><span>難度：實作</span><span>streaming transform · cross-buffer state · backpressure</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

完成一個可跨buffer保存狀態的stream filter，處理partial token、shadow/copy、flags與subrequest。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node active"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-41-加入自訂-variable-與-header-filter"><span>上一站</span><strong>41. 加入自訂 Variable 與 Header Filter</strong></a><div class="position-card current"><span>你在這裡</span><strong>42. 實作 Streaming Body Filter</strong></div><a class="position-card" href="#chapter-43-實作簡化版-load-balancer"><span>下一站</span><strong>43. 實作簡化版 Load Balancer</strong></a></div>

本章位於 **Part 7：從讀懂走向真的會**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Body filter 不會收到完整 response string，而是任意大小、任意次數的 buffer chains。若要替換 token、計算 digest 或轉碼，匹配可能跨兩個 buffers，還要保留 flush/last 與 downstream backpressure。

Use case 是把串流中的 `foo` 改成 `bar`；第一個 buffer 可能只以 `f` 結尾，下一個才從 `oo` 開始。Stateless 字串 replace 會漏匹配或重複資料。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Body filter 不會收到完整 response string，而是任意大小、任意次數的 buffer chains。若要替換 token、計算 digest 或轉碼，匹配可能跨兩個 buffers，還要保留 flush/last 與 downstream backpressure。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是把串流中的 <code>foo</code> 改成 <code>bar</code>；第一個 buffer 可能只以 <code>f</code> 結尾，下一個才從 <code>oo</code> 開始。Stateless 字串 replace 會漏匹配或重複資料。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Stateful streaming transform」這個責任邊界；接收 一批 input buffers + 上次殘留 partial token，交付 語意等價、flags 正確的 output chain。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 request module ctx、carry bytes、busy/free chains 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 跨 buffer corruption、Content-Length 錯誤、flag 遺失、下游 AGAIN 後重複輸出。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Stateful streaming transform</p></div><div class="contract-card"><span>接收什麼</span><p>一批 input buffers + 上次殘留 partial token</p></div><div class="contract-card"><span>產生什麼</span><p>語意等價、flags 正確的 output chain</p></div><div class="contract-card"><span>狀態由誰保存</span><p>request module ctx、carry bytes、busy/free chains</p></div><div class="contract-card"><span>主要失敗出口</span><p>跨 buffer corruption、Content-Length 錯誤、flag 遺失、下游 AGAIN 後重複輸出</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>首次呼叫建立 request ctx</p></div><div class="flow-step"><span>2</span><p>逐 buffer 讀取可消費 bytes</p></div><div class="flow-step"><span>3</span><p>將前次 partial prefix 與新 bytes 合併判斷</p></div><div class="flow-step"><span>4</span><p>輸出已確定不可能再延伸的資料</p></div><div class="flow-step"><span>5</span><p>保存仍可能成為 match 的 suffix</p></div><div class="flow-step"><span>6</span><p>傳遞 flush/sync 並在 last 時 flush carry</p></div><div class="flow-step"><span>7</span><p>呼叫 next body filter</p></div><div class="flow-step"><span>8</span><p>AGAIN 時保留 output ownership，writable 後續送</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
input chunks:  "hello NG" | "INX world" | last
pattern:       "NGINX"

ctx keeps suffix "NG"
next chunk completes match
output: "hello [server] world"

每次filter可能：
consume部分input / 保存suffix / 產生out chain / 等downstream
```

## 從零建立心智模型

串流filter不能假設pattern落在單一buffer。Module ctx要保存最多pattern length-1的suffix或parser state，下一chunk到來再繼續。這和incremental HTTP parser是同一思想。

若修改長度，Content-Length需清除或重算，ETag/range/content encoding也可能失效。Header filter先判斷content type/status並建立ctx，body filter才轉換。

下游可能返回AGAIN並保留out buffers。Module需管理free/busy/out chains；不能立刻重用仍被next filter引用的storage。Flush、sync、last flags必須映射到正確最後輸出。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

對每個 chunk 單獨 `replace()` 會漏掉跨 chunk token。Streaming transform 必須保存最多 token 長度減一的 suffix，直到確定不可能與下一 chunk 組成 match。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>carry</code></td><td>body filter request ctx 中跨 buffers 的 parser state</td></tr><tr><td><code>feed</code></td><td>每次 top body filter 收到一條 chain</td></tr><tr><td><code>final</code></td><td><code>last_buf</code>/<code>last_in_chain</code></td></tr><tr><td>returned bytes</td><td>新建或 shadow output buffers 交 next filter</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/modules/ngx_http_sub_filter_module.c`，官方 `release-1.31.5` 第 285–334 行

```c
ngx_http_sub_body_filter(ngx_http_request_t *r, ngx_chain_t *in)
{
    ngx_int_t                  rc;
    ngx_buf_t                 *b;
    ngx_str_t                 *sub;
    ngx_uint_t                 flush, last;
    ngx_chain_t               *cl;
    ngx_http_sub_ctx_t        *ctx;
    ngx_http_sub_match_t      *match;
    ngx_http_sub_loc_conf_t   *slcf;

    ctx = ngx_http_get_module_ctx(r, ngx_http_sub_filter_module);

    if (ctx == NULL) {
        return ngx_http_next_body_filter(r, in);
    }

    if ((in == NULL
         && ctx->buf == NULL
         && ctx->in == NULL
         && ctx->busy == NULL))
    {
        return ngx_http_next_body_filter(r, in);
    }

    if (ctx->once && (ctx->buf == NULL || ctx->in == NULL)) {

        if (ctx->busy) {
            if (ngx_http_sub_output(r, ctx) == NGX_ERROR) {
                return NGX_ERROR;
            }
        }

        return ngx_http_next_body_filter(r, in);
    }

    /* add the incoming chain to the chain ctx->in */

    if (in) {
        if (ngx_chain_add_copy(r->pool, &ctx->in, in) != NGX_OK) {
            return NGX_ERROR;
        }
    }

    ngx_log_debug1(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                   "http sub filter \"%V\"", &r->uri);

    flush = 0;
    last = 0;

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Header filter決定是否啟用，調整Content-Length/ETag並建立ctx。</p></div><div class="source-step"><span>2</span><p>Body filter逐input buffer讀取，結合pending suffix。</p></div><div class="source-step"><span>3</span><p>產生request-pool或可管理的output buffers，保留control flags。</p></div><div class="source-step"><span>4</span><p>呼叫next filter後更新busy/free chains與已消費位置。</p></div><div class="source-step"><span>5</span><p>Last input到來時flush pending suffix並傳last_buf/last_in_chain。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>若 replacement 改變長度，原 Content-Length 必須移除/重算。</p></div><div class="microscope-card"><span>2</span><p>Read-only/file buffer 不可直接原地修改。</p></div><div class="microscope-card"><span>3</span><p>Flush/sync/last flags 要移到語意正確的 output buffer。</p></div><div class="microscope-card"><span>4</span><p>對 token 的每一種切分位置做測試，並加入 downstream AGAIN。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 先定義 Content-Length 是否仍有效；變長度通常需清除並改用 chunked/framing。
- 不可修改 read-only memory/file buffer；必要時配置新 buffer 或 shadow。
- Last/flush/sync flags 必須附在語意正確的最後輸出 buffer。
- 用每個可能切點測試 token，才能驗證跨 buffer state。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/modules/ngx_http_sub_filter_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_sub_filter_module.c#L1) · [`src/http/modules/ngx_http_gzip_filter_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_gzip_filter_module.c#L1) · [`src/http/ngx_http_copy_filter_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_copy_filter_module.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

原地修改只適用temporary且有足夠空間、不改長度、沒有其他shadow owner。初學實作應產生新buffer，先以正確性為主。

Compression順序很重要。若filter位於gzip後，看到的是compressed bytes；通常文字轉換需在compression前。Dynamic module排序需驗證，不能假設。

Streaming parser要限制pending state大小。若等待delimiter而無上限，攻擊者可用沒有終止符的stream造成memory growth。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Streaming finite-state transducer</h3><p>有限 carry state 將 chunk stream 轉成另一條 stream。</p></div><div class="pattern-card"><h3>Boundary-independent processing</h3><p>結果不應依 input 如何切 chunk。</p></div><div class="pattern-card"><h3>Backpressure transparency</h3><p>filter 不吞掉或偽造下游 flow-control signal。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 先做不改長度的大寫filter，再進階跨chunk字串替換。
2. 用backend刻意把pattern拆在不同write中。
3. 以slow client測downstream AGAIN與busy chain。
4. 開gzip、subrequest、HEAD、empty body測試filter條件。

## 常見誤解與失敗模式

- 只搜尋每個buffer，漏掉跨邊界pattern。
- 下游尚未完成就覆寫/reuse output。
- 改body長度卻保留舊Content-Length。

## 可以帶走的 Coding／CS 能力

- 實作incremental streaming algorithm。
- 管理pipeline ownership、flush與partial consumption。
- 理解內容轉換與protocol metadata的一致性。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

掌握 request/filter module 後，下一章實作更深入的 peer scheduler，串起 upstream callbacks 與 shared state。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 跨buffer pattern如何處理？</summary>

保存可成為pattern前綴的尾端狀態，與下一chunk繼續automaton；不能無界保存全部歷史。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為什麼header filter也要參與？</summary>

Body長度、ETag、range與content encoding metadata可能因轉換失效；須在headers送出前調整。

</details>

<details class="qa" markdown="1">
<summary>Q3. 何時可以原地修改buffer？</summary>

Buffer標記temporary、storage可寫、無共享shadow、轉換不超容量且不破壞其他consumer時；否則建立新buffer。

</details>

<details class="qa" markdown="1">
<summary>Q4. 下游返回AGAIN意味input已完全消費嗎？</summary>

不一定只看return code；需依filter contract與buffer positions/free-busy chains判斷。通常已交出的out仍可能被引用。

</details>

<details class="qa" markdown="1">
<summary>Q5. Filter如何處理last buffer？</summary>

先輸出pending parser state，再把last_buf或last_in_chain放到真正最後的output buffer，確保下游完成。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何防止stream parser memory DoS？</summary>

限制pending token/prefix大小、總輸出擴張比例與buffer數，遇非法/過長輸入fail或pass-through。

</details>

---

# 第 43 章　實作簡化版 Load Balancer

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Config time 與 request time</h3><div class="foundation-block"><span>白話定義</span><p>Config time 低頻地解析規則並建立可重用資料；request time 高頻地使用結果，應避免重做相同工作。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 清單與 hash ring 在 reload 時建立；每個 request 只做選擇。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX modules 常有 main/server/location conf 與 per-request ctx，兩者 lifetime 不可混用。</p></div></section><section class="foundation-card"><h3>Balancer get/free callbacks</h3><div class="foundation-block"><span>白話定義</span><p><code>get</code> 在一次連線嘗試前選 peer；<code>free</code> 在嘗試結束後回報結果。選擇與回饋是同一 contract 的兩半。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>先選 latency score 最低的 peer；connect 失敗後增加它的 failure penalty。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX per-request tried state 防止同一次 retry 重複選到已失敗 peer，shared state 則處理跨 worker visibility。</p></div></section><section class="foundation-card"><h3>Peer</h3><div class="foundation-block"><span>白話定義</span><p>一個可被選來連線的遠端 endpoint，通常是一台 backend 的 IP/port 加上權重與健康狀態。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Upstream group 有 app-1、app-2、app-3；某次 request 選 app-2 作為 peer。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Balancer 的 get callback 選 peer；free callback 回報 success/failure，讓後續選擇調整。</p></div></section><section class="foundation-card"><h3>Feedback control</h3><div class="foundation-block"><span>白話定義</span><p>系統根據實際成功或失敗回饋調整下一次決策，而不是永遠使用固定參數。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Backend 剛失敗時降低 effective weight，之後成功再逐步恢復。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Balancer state 同時表達靜態 capacity 與動態健康程度。</p></div></section><section class="foundation-card"><h3>Shared memory</h3><div class="foundation-block"><span>白話定義</span><p>可被多個 processes 看見的同一塊記憶體。因為會同時讀寫，所以通常需要 atomic operation 或 lock。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>所有 workers 共用 rate-limit counter，不能只存在某一個 worker 的一般 heap。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 shared memory zones 保存 cache metadata、upstream state 與跨 worker counters。</p></div></section></div>



<p class="chapter-question">如何新增一個`first_two_least_conn`策略，又不重寫connection、retry與health邏輯？</p>

<div class="chapter-meta"><span>難度：實作</span><span>peer callbacks · scheduler · shared state</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

實作`init_upstream/init_peer/get/free`，重用round-robin peer eligibility，並測公平、失敗與並發。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node active"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-42-實作-streaming-body-filter"><span>上一站</span><strong>42. 實作 Streaming Body Filter</strong></a><div class="position-card current"><span>你在這裡</span><strong>43. 實作簡化版 Load Balancer</strong></div><a class="position-card" href="#chapter-44-除錯-測試與效能分析"><span>下一站</span><strong>44. 除錯、測試與效能分析</strong></a></div>

本章位於 **Part 7：從讀懂走向真的會**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

自訂 load balancer 迫使你同時處理 config-time 初始化、per-upstream peer data、per-request tried state、get/free callbacks、失敗回饋與 multi-worker visibility。它是驗證 upstream 理解最完整的練習。

Use case 是根據 latency score、tenant 或自訂 capacity 選 peer。演算法本身可能只有十行，真正困難的是 callback contract、fallback、concurrency 與 lifecycle。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>自訂 load balancer 迫使你同時處理 config-time 初始化、per-upstream peer data、per-request tried state、get/free callbacks、失敗回饋與 multi-worker visibility。它是驗證 upstream 理解最完整的練習。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是根據 latency score、tenant 或自訂 capacity 選 peer。演算法本身可能只有十行，真正困難的是 callback contract、fallback、concurrency 與 lifecycle。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Custom upstream scheduler module」這個責任邊界；接收 upstream server config + request-time peer state，交付 一個 peer connection candidate 與完成後 feedback。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 upstream peer data、per-request selection data、可選 shared zone 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 選到 down/tried peer、所有 peers exhausted、race、feedback 遺失。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Custom upstream scheduler module</p></div><div class="contract-card"><span>接收什麼</span><p>upstream server config + request-time peer state</p></div><div class="contract-card"><span>產生什麼</span><p>一個 peer connection candidate 與完成後 feedback</p></div><div class="contract-card"><span>狀態由誰保存</span><p>upstream peer data、per-request selection data、可選 shared zone</p></div><div class="contract-card"><span>主要失敗出口</span><p>選到 down/tried peer、所有 peers exhausted、race、feedback 遺失</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>directive 選擇自訂 balancer</p></div><div class="flow-step"><span>2</span><p>upstream init 建立 peers/policy metadata</p></div><div class="flow-step"><span>3</span><p>request init 建 per-request tried/context</p></div><div class="flow-step"><span>4</span><p>get callback 過濾不可用 peers</p></div><div class="flow-step"><span>5</span><p>計算 score 並回傳 sockaddr/name</p></div><div class="flow-step"><span>6</span><p>通用 upstream connect/send/read</p></div><div class="flow-step"><span>7</span><p>free callback 接收 success/failure state</p></div><div class="flow-step"><span>8</span><p>更新 local/shared feedback 並保留 fallback</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
configuration: first_two_least_conn;
      ↓ init_upstream
prepare peer set / wrap round-robin init
      ↓ per request init_peer
allocate request peer data + tried bitmap
      ↓ get
sample eligible A,B → compare conns/weight → choose
      ↓ free
decrement conns / report failed state
```

## 從零建立心智模型

自訂balancer不應自己建立socket。它實作peer interface：config-time指定upstream init，per-request配置peer data，get callback選候選並填sockaddr/name，free callback更新狀態。

可重用round-robin初始化、locks、eligibility與peer structures，避免漏掉down、max_fails、max_conns、backup、DNS resolve與shared zone。簡化算法只替換「eligible peers中選誰」。

Power-of-two類策略需處理只有一個peer、sample重複、tried bitmap、weight與tie-break。測試不只看平均分布，也看長request、peer failure、backup與多worker。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Custom balancer 的演算法通常不難，難的是 config-time data、per-request tried set、shared feedback 與 get/free callback contract。這個例子把 selection 與 completion feedback 分開。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>get</code></td><td>peer get callback 填 sockaddr/name</td></tr><tr><td><code>tried</code></td><td>per-request tried bitmap</td></tr><tr><td><code>free</code></td><td>request attempt 完成後的 peer free callback</td></tr><tr><td>peer state</td><td>local upstream peers 或 shared zone state</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/modules/ngx_http_upstream_random_module.c`，官方 `release-1.31.5` 第 337–384 行

```c
ngx_http_upstream_get_random2_peer(ngx_peer_connection_t *pc, void *data)
{
    ngx_http_upstream_random_peer_data_t  *rp = data;

    time_t                             now;
    uintptr_t                          m;
    ngx_uint_t                         i, n, p;
    ngx_http_upstream_rr_peer_t       *peer, *prev;
    ngx_http_upstream_rr_peers_t      *peers;
    ngx_http_upstream_rr_peer_data_t  *rrp;

    ngx_log_debug1(NGX_LOG_DEBUG_HTTP, pc->log, 0,
                   "get random2 peer, try: %ui", pc->tries);

    rrp = &rp->rrp;
    peers = rrp->peers;

    ngx_http_upstream_rr_peers_wlock(peers);

    if (rp->tries > 20 || peers->number < 2) {
        ngx_http_upstream_rr_peers_unlock(peers);
        return ngx_http_upstream_get_round_robin_peer(pc, rrp);
    }

#if (NGX_HTTP_UPSTREAM_ZONE)
    if (peers->config && rrp->config != *peers->config) {
        ngx_http_upstream_rr_peers_unlock(peers);
        return ngx_http_upstream_get_round_robin_peer(pc, rrp);
    }
#endif

    pc->cached = 0;
    pc->connection = NULL;

    now = ngx_time();

    prev = NULL;

#if (NGX_SUPPRESS_WARN)
    p = 0;
#endif

#if (NGX_HTTP_UPSTREAM_SID)
    peer = ngx_http_upstream_get_rr_peer_by_sid(rrp, pc->hint, &i, 0);

    if (peer) {
        n = i / (8 * sizeof(uintptr_t));
        m = (uintptr_t) 1 << i % (8 * sizeof(uintptr_t));
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Directive set upstream <code>peer.init_upstream</code>。</p></div><div class="source-step"><span>2</span><p>Init upstream先呼叫/重用round-robin建立peers，再安裝per-request init。</p></div><div class="source-step"><span>3</span><p>Per-request init配置自訂data並保留RR data/tried bitmap。</p></div><div class="source-step"><span>4</span><p>Get在lock內sample/過濾/選擇，增加conns並填pc。</p></div><div class="source-step"><span>5</span><p>Free委派或等價更新RR failure/conns state。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先包住 round-robin initializer/data，再替換最小 selection。</p></div><div class="microscope-card"><span>2</span><p>Per-request exclusion 與 global health/latency state 不同。</p></div><div class="microscope-card"><span>3</span><p>Free flags 要分類 failure，不是單一 success boolean。</p></div><div class="microscope-card"><span>4</span><p>Shared feedback 需要 slab/lock/reload-compatible layout。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 先完整包住原 round-robin data model，再改 selection，避免一開始重建全部 contract。
- Per-request tried set 與 global peer health 是兩種不同 state。
- Free callback 的 flags 是分類訊號，不是簡單 boolean success。
- 若使用 shared memory，reload compatibility 與 lock invariant 必須一起設計。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/modules/ngx_http_upstream_random_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_random_module.c#L1) · [`src/http/modules/ngx_http_upstream_least_conn_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_upstream_least_conn_module.c#L1) · [`src/http/ngx_http_upstream_round_robin.c#L486`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream_round_robin.c#L486)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Lock範圍需涵蓋讀取conns與increment選擇，否則多worker shared zone可能同時認為同peer最空。又不能在鎖內做random entropy、log大量資料或connect。

Random seed與測試重現要分開：production可使用合適PRNG state；unit/simulation應可固定seed，才能驗證分布與corner cases。

Scheduler correctness包括不選本次tried/down peer、tries遞減與free恰好一次。漏一項可能造成loop、conns永不下降或所有peer被誤判busy。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Strategy plugin</h3><p>替換 peer selection，不重寫 upstream transport。</p></div><div class="pattern-card"><h3>Feedback loop</h3><p>完成結果影響未來 scheduling。</p></div><div class="pattern-card"><h3>Local fast path + optional shared truth</h3><p>精確跨 worker state 與低 contention 之間取捨。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 複製最小dynamic upstream module骨架並重用RR init。
2. 寫純函式simulation，固定seed測1/2/N peers與權重。
3. 整合NGINX，混合短長request比較RR/least_conn/custom。
4. 故障一台、啟用backup、開shared zone做壓測。

## 常見誤解與失敗模式

- 忽略tried bitmap，retry重選同一失敗peer。
- 只increment conns不在free decrement。
- 在shared lock內connect或執行昂貴工作。

## 可以帶走的 Coding／CS 能力

- 把scheduler拆成候選過濾、score、selection與feedback。
- 重用穩定framework而只替換最小策略。
- 用simulation＋integration＋failure test驗證概率算法。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

實作完成仍需知道怎麼證明正確與不拖慢 worker；下一章建立除錯、測試與效能方法。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Balancing module為何不自己呼叫connect？</summary>

Peer interface只決定地址與狀態；event connect core統一處理non-blocking socket、timer、SSL與error，避免每算法重複。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為什麼重用RR peer structures？</summary>

它已處理weights、fails、max_conns、backup、shared zone、DNS與locks；重新實作容易漏掉production邊界。

</details>

<details class="qa" markdown="1">
<summary>Q3. Get與free必須成對維護哪些狀態？</summary>

Conns、fails/accessed/checked、effective weight、reference/lock與tried/tries；free還需知道本次成功或failed。

</details>

<details class="qa" markdown="1">
<summary>Q4. 兩個sample可能相同怎麼辦？</summary>

重新sample有限次或接受單候選；更重要是避免無限loop，並正確處理eligible只剩一個的情況。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如何測概率scheduler？</summary>

固定seed做deterministic unit tests，再大量simulation看分布/最大queue，最後真實並發與failure test看tail latency。

</details>

<details class="qa" markdown="1">
<summary>Q6. Shared zone下為何score讀取也需鎖？</summary>

讀conns與選擇/increment若非同一原子臨界區，多worker可同時基於舊值選同peer，形成herd；可用鎖或設計近似無鎖策略接受誤差。

</details>

---

# 第 44 章　除錯、測試與效能分析

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>不同問題需要不同測試</h3><div class="foundation-block"><span>白話定義</span><p>Source correctness、protocol edge case、failure recovery 與 performance 是不同問題，不能只用一次成功的 curl 證明。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Fragmented input test parser；slow client test backpressure；profiler 找 CPU hot path。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX/module 驗證需組合 unit/black-box/fault injection/debug log/syscall trace 與 benchmark。</p></div></section><section class="foundation-card"><h3>Observability（可觀察性）</h3><div class="foundation-block"><span>白話定義</span><p>利用 log、metrics、trace 與 debugger，從程式外部推回內部實際發生的狀態轉換。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>同一個 request ID 出現在 accept、upstream connect 與 response log，便能重建完整時間線。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Debug log、錯誤碼、request/connection 編號與 timing 欄位是驗證源碼理解的證據。</p></div></section><section class="foundation-card"><h3>Profiler 與 flame graph</h3><div class="foundation-block"><span>白話定義</span><p>Profiler 以抽樣或 instrumentation 統計 CPU 時間花在哪些 call stacks；flame graph 把熱門 stack 視覺化。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Worker CPU 100% 時，先確認時間在 application handler、regex、copy 還是 busy event wake-up。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>效能分析必須在代表性 workload 下進行，並同時觀察 latency、throughput 與資源使用。</p></div></section><section class="foundation-card"><h3>System call（系統呼叫）</h3><div class="foundation-block"><span>白話定義</span><p>一般程式不能直接控制網卡、socket 或 process；它必須呼叫作業系統核心提供的入口。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>read()</code>、<code>write()</code>、<code>accept()</code>、<code>epoll_wait()</code> 都是 system calls。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>用 <code>strace</code> 觀察 syscall，可以確認 NGINX 最後真的向 kernel 要求了什麼。</p></div></section></div>



<p class="chapter-question">遇到高CPU、偶發502、memory成長或event-loop卡頓時，如何用證據逐層縮小問題？</p>

<div class="chapter-meta"><span>難度：實作</span><span>debugging · profiling · fault injection</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

建立從症狀、request ID、NGINX log、syscall、profile到source hypothesis的可重複流程。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node active"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-43-實作簡化版-load-balancer"><span>上一站</span><strong>43. 實作簡化版 Load Balancer</strong></a><div class="position-card current"><span>你在這裡</span><strong>44. 除錯、測試與效能分析</strong></div><a class="position-card" href="#chapter-45-閱讀真實-bug-fix-與-code-review"><span>下一站</span><strong>45. 閱讀真實 Bug Fix 與 Code Review</strong></a></div>

本章位於 **Part 7：從讀懂走向真的會**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Source-level correctness、protocol correctness、failure recovery 與 performance 需要不同證據。單靠 happy-path curl 無法發現 fragmented input、slow client、retry duplicate 或 handler blocking。

Use case 是 module 偶發 502、worker CPU 100%、memory 隨 requests 增長。這一章把 debug log、GDB、sanitizer、strace/perf、fault injection 與 regression test 組成分層診斷法。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Source-level correctness、protocol correctness、failure recovery 與 performance 需要不同證據。單靠 happy-path curl 無法發現 fragmented input、slow client、retry duplicate 或 handler blocking。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 module 偶發 502、worker CPU 100%、memory 隨 requests 增長。這一章把 debug log、GDB、sanitizer、strace/perf、fault injection 與 regression test 組成分層診斷法。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Evidence-driven validation」這個責任邊界；接收 症狀、可重現 workload、source hypothesis，交付 可定位的 root cause 與防回歸測試。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 test harness、logs/traces/profiles/core dumps 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 不可重現、觀測干擾、只測成功路徑、microbenchmark 誤導。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Evidence-driven validation</p></div><div class="contract-card"><span>接收什麼</span><p>症狀、可重現 workload、source hypothesis</p></div><div class="contract-card"><span>產生什麼</span><p>可定位的 root cause 與防回歸測試</p></div><div class="contract-card"><span>狀態由誰保存</span><p>test harness、logs/traces/profiles/core dumps</p></div><div class="contract-card"><span>主要失敗出口</span><p>不可重現、觀測干擾、只測成功路徑、microbenchmark 誤導</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>把症狀改寫成可觀察 invariant</p></div><div class="flow-step"><span>2</span><p>縮成最小 config/request</p></div><div class="flow-step"><span>3</span><p>用 request ID 建時間線</p></div><div class="flow-step"><span>4</span><p>source/log 找狀態轉換點</p></div><div class="flow-step"><span>5</span><p>fault injection 固定觸發 branch</p></div><div class="flow-step"><span>6</span><p>選 GDB/ASan/strace/perf 回答特定問題</p></div><div class="flow-step"><span>7</span><p>修正後加入 regression test</p></div><div class="flow-step"><span>8</span><p>以壓力與長時間測試驗證副作用</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
symptom/SLO
   ↓ scope: all traffic? one worker? one upstream?
metrics + structured access log
   ↓ correlate request/connection/peer attempts
debug log / error path
   ↓
strace (syscall) | GDB (state) | perf (CPU)
   ↓ minimal reproduction + fault injection
   ↓ hypothesis confirmed / falsified
```

## 從零建立心智模型

先分類症狀：CPU、event loop lag、socket/resource exhaustion、upstream latency、output backpressure、memory lifetime或config routing。不同類別需要不同工具。

Access log應包含request id、status、request time、upstream addr/status/connect/header/response times、bytes與cache status。一次retry可能有多個peer值；只看最終200會掩蓋第一次timeout。

Debug log非常詳細，應在最小環境或特定connection使用；production高流量全開可能改變timing與磁碟。Perf找CPU hot path，strace找blocking/syscall pattern，GDB/core dump看object state。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

只寫 happy-path assertion 無法重現 async edge cases。Fault injection 將 connect timeout、partial read、client abort 等分支變成可控制輸入，再對 state invariant 驗證。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>scripted actions</td><td>故障 backend/netcat/tc/timeout 的 deterministic fault injection</td></tr><tr><td>exceptions</td><td>EAGAIN/reset/timeout branches</td></tr><tr><td>preserved buffer</td><td>跨 callback invariant</td></tr><tr><td>test loop</td><td>針對 state transition 的 regression test</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/ngx_log.c`，官方 `release-1.31.5` 第 102–149 行

```c
ngx_log_error_core(ngx_uint_t level, ngx_log_t *log, ngx_err_t err,
    const char *fmt, va_list args)

#endif
{
#if (NGX_HAVE_VARIADIC_MACROS)
    va_list      args;
#endif
    u_char      *p, *last, *msg;
    ssize_t      n;
    ngx_uint_t   wrote_stderr, debug_connection;
    u_char       errstr[NGX_MAX_ERROR_STR];

    last = errstr + NGX_MAX_ERROR_STR;

    p = ngx_cpymem(errstr, ngx_cached_err_log_time.data,
                   ngx_cached_err_log_time.len);

    p = ngx_slprintf(p, last, " [%V] ", &err_levels[level]);

    /* pid#tid */
    p = ngx_slprintf(p, last, "%P#" NGX_TID_T_FMT ": ",
                    ngx_log_pid, ngx_log_tid);

    if (log->connection) {
        p = ngx_slprintf(p, last, "*%uA ", log->connection);
    }

    msg = p;

#if (NGX_HAVE_VARIADIC_MACROS)

    va_start(args, fmt);
    p = ngx_vslprintf(p, last, fmt, args);
    va_end(args);

#else

    p = ngx_vslprintf(p, last, fmt, args);

#endif

    if (err) {
        p = ngx_log_errno(p, last, err);
    }

    if (level != NGX_LOG_DEBUG && log->handler) {
        p = log->handler(log, p, last - p);
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>先用SLO/metric確認時間窗、worker與request cohort。</p></div><div class="source-step"><span>2</span><p>從access log拆client time與每個upstream階段。</p></div><div class="source-step"><span>3</span><p>用error/debug log找到狀態轉換與return code。</p></div><div class="source-step"><span>4</span><p>選工具：perf CPU、strace syscall、GDB memory/control、ss network。</p></div><div class="source-step"><span>5</span><p>建立最小重現並注入delay/reset/partial response。</p></div><div class="source-step"><span>6</span><p>修正後用相同workload與failure驗證，不只跑happy path。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先定義症狀與 invariant，再選工具。</p></div><div class="microscope-card"><span>2</span><p>Debug log、GDB、strace、perf 各回答不同層。</p></div><div class="microscope-card"><span>3</span><p>測每個 I/O boundary 的 AGAIN、EOF、timeout、error。</p></div><div class="microscope-card"><span>4</span><p>修正後保留能穩定觸發原 bug 的 regression harness。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Debug build 的 timing 可能和 optimized build 不同；結論需交叉驗證。
- CPU profile 顯示花在哪裡，不自動告訴你為什麼。
- Leak 要區分仍被 cache/pool 合法持有，或 lifecycle 真正未釋放。
- 測試至少涵蓋每個 I/O 邊界的 AGAIN、timeout、EOF 與 error。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_log.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_log.c#L1) · [`src/http/ngx_http_request.c#L3981`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L3981) · [`src/http/ngx_http_upstream.c#L1571`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_upstream.c#L1571)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Memory問題先問是bounded cache/pool高水位還是真leak。RSS不下降不必然leak，allocator/page cache可能保留；應看跨request object count、pool lifetime、shared zone與長連線generation。

502只是映射結果。根因可能connect refused、timeout、invalid header、premature close、DNS、TLS或no live upstreams；必須讀error subtype與timings。

Benchmark要有warmup、固定CPU/worker、足夠connection數、正確client瓶頸檢查與p50/p95/p99。只報requests/sec會掩蓋tail與error。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Layered observability</h3><p>application log、syscall、CPU profile、memory checker 各回答不同層。</p></div><div class="pattern-card"><h3>Fault injection</h3><p>主動製造 timeout、partial I/O 與 abort。</p></div><div class="pattern-card"><h3>Invariant-based testing</h3><p>驗證 ownership/ordering/once-only，而不只驗 output。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 建立backend四種fault：delay connect、delay header、invalid header、body中斷。
2. 為每種fault整理access/error/upstream timing指紋。
3. 用perf找故意加入的CPU-heavy handler。
4. 用ASan/UBSan build跑自訂module與parser fuzz corpus。

## 常見誤解與失敗模式

- 看到502直接增加timeout或重試。
- 在production全域開debug log造成二次事故。
- 以RSS不下降直接判定memory leak。

## 可以帶走的 Coding／CS 能力

- 建立layered evidence與可證偽hypothesis。
- 區分CPU、I/O、queueing、allocation與downstream問題。
- 設計fault injection與回歸測試。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

知道如何重現後，下一章透過真實 bug fix 學會從 patch 反推 invariant 與架構判斷。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 502為什麼不是root cause？</summary>

它是gateway對多種upstream failure的HTTP映射；需看error log、upstream status與connect/header/response time判斷具體階段。

</details>

<details class="qa" markdown="1">
<summary>Q2. 何時用perf而不是strace？</summary>

CPU高或懷疑user-space hot path用perf；懷疑blocking syscall、重試、fd/error或I/O pattern用strace。兩者可互補。

</details>

<details class="qa" markdown="1">
<summary>Q3. RSS長期高為何不一定leak？</summary>

Allocator arena、page cache、pool高水位與長連線可保留pages；leak需證明不可回收objects隨工作量持續增長。

</details>

<details class="qa" markdown="1">
<summary>Q4. Debug log為何可能改變問題？</summary>

大量format/write I/O增加CPU、lock與disk延遲，改變event timing；應縮小scope或用sampling/breakpoint。

</details>

<details class="qa" markdown="1">
<summary>Q5. 怎麼設計upstream fault matrix？</summary>

至少覆蓋DNS、connect拒絕/timeout、TLS、send、header timeout/invalid、body中斷、slow client與retry exhaustion。

</details>

<details class="qa" markdown="1">
<summary>Q6. 效能修正如何驗證？</summary>

同硬體/config/workload與warmup，比較throughput、errors、CPU、memory、event-loop lag和p50/p95/p99，並保留correctness/failure tests。

</details>

---

# 第 45 章　閱讀真實 Bug Fix 與 Code Review

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Patch、regression 與 invariant</h3><div class="foundation-block"><span>白話定義</span><p>Patch 是一次程式差異；regression 是修改使舊功能退步；invariant 是每條路徑都必須維持的條件。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>修正 stale flag 時，要測正常路徑、timeout、fd reuse 與舊平台，證明沒有引入新問題。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>讀 NGINX bug fix 時先找被破壞的 invariant，再看三行 diff，才能理解修改位置為何必要。</p></div></section><section class="foundation-card"><h3>Backward compatibility</h3><div class="foundation-block"><span>白話定義</span><p>新版本仍維持既有設定、協定或 module 所依賴的行為，避免升級造成無預警破壞。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>看似更乾淨的 return code 改法，可能破壞第三方 module 的既有判斷。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>成熟 NGINX code review 會把 API/ABI、平台差異、舊 config 與 error behavior 納入成本。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section><section class="foundation-card"><h3>不同問題需要不同測試</h3><div class="foundation-block"><span>白話定義</span><p>Source correctness、protocol edge case、failure recovery 與 performance 是不同問題，不能只用一次成功的 curl 證明。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Fragmented input test parser；slow client test backpressure；profiler 找 CPU hot path。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX/module 驗證需組合 unit/black-box/fault injection/debug log/syscall trace 與 benchmark。</p></div></section></div>



<p class="chapter-question">從『看懂好程式』走到『能指出好程式哪裡仍會錯』，需要怎樣閱讀commit與設計測試？</p>

<div class="chapter-meta"><span>難度：進階</span><span>code review · invariant · regression test</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

用invariant、lifetime、state transition、failure matrix與最小diff閱讀歷史，建立maintainer視角。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node active"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-44-除錯-測試與效能分析"><span>上一站</span><strong>44. 除錯、測試與效能分析</strong></a><div class="position-card current"><span>你在這裡</span><strong>45. 閱讀真實 Bug Fix 與 Code Review</strong></div><a class="position-card" href="#chapter-46-為什麼-connection-layer-不應知道-http"><span>下一站</span><strong>46. 為什麼 Connection Layer 不應知道 HTTP</strong></a></div>

本章位於 **Part 7：從讀懂走向真的會**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

成熟 source code 的價值不只在當前實作，也在 bug fix 顯示哪些 assumption 曾經不成立。高品質 review 會問 ownership、all return paths、protocol edge cases、backward compatibility 與 regression proof。

Use case 是讀一個看似只改三行的 patch：為什麼必須在這裡清 flag？哪些 callback 可能再次進入？沒有測試時如何證明 bug 不會回來？

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>成熟 source code 的價值不只在當前實作，也在 bug fix 顯示哪些 assumption 曾經不成立。高品質 review 會問 ownership、all return paths、protocol edge cases、backward compatibility 與 regression proof。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是讀一個看似只改三行的 patch：為什麼必須在這裡清 flag？哪些 callback 可能再次進入？沒有測試時如何證明 bug 不會回來？</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Patch-as-design-evidence」這個責任邊界；接收 bug report、diff、tests、history context，交付 被明確化的 invariant 與可驗證修正。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 affected object lifecycle + regression scenario 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 只看 happy diff、忽略 error branch、修 symptom 不修 invariant、history context 遺失。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Patch-as-design-evidence</p></div><div class="contract-card"><span>接收什麼</span><p>bug report、diff、tests、history context</p></div><div class="contract-card"><span>產生什麼</span><p>被明確化的 invariant 與可驗證修正</p></div><div class="contract-card"><span>狀態由誰保存</span><p>affected object lifecycle + regression scenario</p></div><div class="contract-card"><span>主要失敗出口</span><p>只看 happy diff、忽略 error branch、修 symptom 不修 invariant、history context 遺失</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>先用舊版重現 bug</p></div><div class="flow-step"><span>2</span><p>描述預期 invariant 與實際違反</p></div><div class="flow-step"><span>3</span><p>找 state 第一次偏離的位置</p></div><div class="flow-step"><span>4</span><p>讀 patch 改了哪個 owner/transition</p></div><div class="flow-step"><span>5</span><p>列出所有進入與退出 branch</p></div><div class="flow-step"><span>6</span><p>檢查 cleanup/retry/reload/subrequest 交互</p></div><div class="flow-step"><span>7</span><p>執行新增與相鄰 tests</p></div><div class="flow-step"><span>8</span><p>用自己的話寫 review rationale</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
bug report / commit message
      ↓ reproduce old behavior
identify violated invariant
      ↓ read minimal diff
which state/lifetime/error edge changed?
      ↓ construct neighboring counterexamples
      ↓ regression + compatibility + performance review

不是問「diff做了什麼」，而是「什麼原本應永遠成立卻沒成立」。
```

## 從零建立心智模型

閱讀fix先不要看答案。從issue或commit parent重現症狀，寫出預期invariant，例如「event被free前timer必須移除」「body buffer仍被下游引用時不能重用」「retry不選tried peer」。

再看diff，把每一行分類為guard、state update、ownership transfer、cleanup、ordering或test。小diff常修的是時序：哪個flag先設、哪個callback可能重入、error path漏哪個decrement。

Review不能停在原case。沿相鄰維度擴張：同步/非同步、成功/timeout/abort、main/subrequest、buffered/unbuffered、single/multi-worker、reload前後。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Patch 若只讓 crash 消失，可能把 reference leak 或 stale state 留到其他 branch。Review 應先寫出 invariant，再用測試證明所有 paths 都維持它。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>finalized</code> invariant</td><td>NGINX 中常由 flags/count/owner state 表達</td></tr><tr><td>guard</td><td>bug fix 新增的狀態檢查</td></tr><tr><td>test twice</td><td>重入/timeout+I/O race 的 regression scenario</td></tr><tr><td>cleanup count</td><td>resource side effect 必須 exactly once</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http_request.c`，官方 `release-1.31.5` 第 3948–3992 行

```c
ngx_http_close_request(ngx_http_request_t *r, ngx_int_t rc)
{
    ngx_connection_t  *c;

    r = r->main;
    c = r->connection;

    ngx_log_debug2(NGX_LOG_DEBUG_HTTP, c->log, 0,
                   "http request count:%d blk:%d", r->count, r->blocked);

    if (r->count == 0) {
        ngx_log_error(NGX_LOG_ALERT, c->log, 0, "http request count is zero");
    }

    r->count--;

    if (r->count || r->blocked) {
        return;
    }

#if (NGX_HTTP_V2)
    if (r->stream) {
        ngx_http_v2_close_stream(r->stream, rc);
        return;
    }
#endif

    ngx_http_free_request(r, rc);
    ngx_http_close_connection(c);
}


void
ngx_http_free_request(ngx_http_request_t *r, ngx_int_t rc)
{
    ngx_log_t                 *log;
    ngx_pool_t                *pool;
    struct linger              linger;
    ngx_http_cleanup_t        *cln;
    ngx_http_log_ctx_t        *ctx;
    ngx_http_core_loc_conf_t  *clcf;

    log = r->connection->log;

    ngx_log_debug0(NGX_LOG_DEBUG_HTTP, log, 0, "http close request");
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>用<code>git log -- path</code>找目標模組歷史與reverts。</p></div><div class="source-step"><span>2</span><p>Checkout parent或讀old code，建立最小reproduction。</p></div><div class="source-step"><span>3</span><p>寫明violated invariant與object lifecycle。</p></div><div class="source-step"><span>4</span><p>讀diff並追caller/callee，不只局部函式。</p></div><div class="source-step"><span>5</span><p>檢查所有退出邊與對稱操作：add/del、inc/dec、lock/unlock、alloc/free。</p></div><div class="source-step"><span>6</span><p>建立regression與neighboring cases。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先重現舊 code 的 invariant violation，再看 diff。</p></div><div class="microscope-card"><span>2</span><p>找 patch 影響的 success/error/timeout/cleanup paths。</p></div><div class="microscope-card"><span>3</span><p><code>git blame/log</code> 用來找 constraint，不是追究作者。</p></div><div class="microscope-card"><span>4</span><p>小 diff 也要檢查 lifecycle、ABI/config 與 performance side effects。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- `git blame` 不是找人，而是找當時 constraint 與相關 commit。
- Patch 新增的 flag/check 常代表此前隱含 lifecycle assumption。
- Review success path、error path、timeout path 與 cleanup path。
- 測試若無法穩定重現原 bug，綠燈不能證明修正有效。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```text
review_checklist(change):
    invariant = state_what_must_always_hold(change)
    for edge in [success, again, timeout, abort, retry, reload]:
        verify_state_transition(edge)
        verify_add_del_symmetry(edge)
        verify_inc_dec_symmetry(edge)
        verify_owner_and_lifetime(edge)
    verify_hot_path_cost()
    verify_regression_test_fails_before_and_passes_after()
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/http/ngx_http_request.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L1) · [`src/event/ngx_event.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/event/ngx_event.c#L1) · [`src/core/ngx_cycle.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_cycle.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

NGINX風格偏小而精確的C變更。大規模重構可能掩蓋behavior change；學習時把mechanical cleanup與semantic fix分開看。

Compatibility包括config syntax/default、module ABI、platform backends與已有quirks。看似更漂亮的抽象若改變hot path allocation或filter order，可能不是可接受修正。

Maintainer review重視能否證明：bug為何發生、fix為何足夠、為何不破壞其他state、如何測試。這比「程式能跑」高一層。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Invariant repair</h3><p>好的 patch 恢復可陳述規則，不只是遮住 crash。</p></div><div class="pattern-card"><h3>Regression archaeology</h3><p>history 顯示 abstraction 在真實需求下的壓力點。</p></div><div class="pattern-card"><h3>Minimal change with complete reasoning</h3><p>diff 可小，但影響面分析必須完整。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 挑一個event/request/upstream歷史fix，先只讀parent與commit message重現。
2. 寫出fix前被破壞的invariant，再看diff校正。
3. 建立failure matrix並找至少兩個原commit未明說的neighbor cases。
4. 用`git blame`追一個看似多餘guard的歷史原因。

## 常見誤解與失敗模式

- 只看final diff，失去自行推理bug的機會。
- 確認原case通過就結束，未測相鄰state。
- 為了抽象漂亮增加hot-path allocation與不必要耦合。

## 可以帶走的 Coding／CS 能力

- 以invariant與state transition做code review。
- 從歷史與revert理解non-obvious constraints。
- 設計能在修正前失敗、修正後通過的regression。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

親手實作與 review 後，Part 8 把具體程式提升成 architecture：先看 connection layer 為何不能知道 HTTP。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為何先看parent再看fix？</summary>

迫使自己建立因果模型，而不是被答案引導；之後可比較自己的invariant與maintainer判斷差距。

</details>

<details class="qa" markdown="1">
<summary>Q2. 什麼是對稱操作檢查？</summary>

每個add timer/event、lock、reference increment、allocation、queue insert都應在所有退出路徑有對應del/unlock/decrement/free/remove。

</details>

<details class="qa" markdown="1">
<summary>Q3. Guard增加就一定安全嗎？</summary>

不一定。Guard可能掩蓋已損壞狀態、跳過必要cleanup或改變正常語意；需說明invariant與後續state。

</details>

<details class="qa" markdown="1">
<summary>Q4. 為何要測neighbor cases？</summary>

Root cause通常影響一類state transition，不只報告中的單一輸入；timeout/subrequest/retry等相鄰維度可能仍有同bug。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如何評估fix的hot-path成本？</summary>

看新增branch、hash/regex、allocation、lock、copy與cache miss是否每request發生，並以profile/benchmark量化。

</details>

<details class="qa" markdown="1">
<summary>Q6. 到什麼程度算真正讀懂一個fix？</summary>

能重現舊bug、陳述被破壞invariant、解釋diff每個state更新、列出風險邊界並設計回歸。

</details>

---
