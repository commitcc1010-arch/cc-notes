---
title: "啟動、設定、Process 與 Reload"
part: 2
source_baseline: release-1.31.5
---

# Part 2　啟動、設定、Process 與 Reload

從 `main()` 建立一代 cycle，理解設定語言、master/worker 分工與新舊 generation 如何無中斷交接。

# 第 5 章　從 main() 到可服務的程序

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Process（行程）</h3><div class="foundation-block"><span>白話定義</span><p>Process 是正在執行的程式實例，擁有自己的虛擬記憶體與 OS resources。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>啟動 <code>nginx</code> 後，可能有一個 master process 和多個 worker processes。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 利用 process isolation 使用多核心並限制單一 crash 的影響範圍。</p></div></section><section class="foundation-card"><h3>Initialization order</h3><div class="foundation-block"><span>白話定義</span><p>大型程式啟動時，後一步常依賴前一步產生的資料；因此初始化不是可以任意排列的函式清單。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>必須先解析 config，才能知道要建立哪些 listening sockets。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依序建立 log、cycle、module configuration、sockets 與 workers，失敗時回滾尚未公開的資源。</p></div></section><section class="foundation-card"><h3>Socket</h3><div class="foundation-block"><span>白話定義</span><p>Socket 是程式與網路連線互動的 OS object。程式用它 listen、accept、connect、read 與 write。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Listening socket 等待新客人；accepted socket 則只代表某一位 client 的 TCP connection。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 把 socket 包裝成 <code>ngx_connection_t</code>，再附加 read/write events 與 protocol state。</p></div></section><section class="foundation-card"><h3>fork</h3><div class="foundation-block"><span>白話定義</span><p><code>fork()</code> 建立一個新的 child process；child 一開始看見 parent 記憶體的邏輯副本，但之後各自執行。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Master 完成設定後 fork workers，讓它們繼承 listening sockets。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>這讓 workers 共用啟動結果，同時保持故障與一般 heap 更新彼此隔離。</p></div></section></div>



<p class="chapter-question">NGINX 啟動時做了什麼，為什麼 `main()` 本身沒有處理任何 HTTP request？</p>

<div class="chapter-meta"><span>難度：初階</span><span>bootstrap · initialization order · process mode</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

看懂啟動分成 bootstrap、建立 cycle、選擇 process mode 三段，並理解初始化順序是架構的一部分。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node active"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-04-讀-nginx-所需的最小-c-語言"><span>上一站</span><strong>04. 讀 NGINX 所需的最小 C 語言</strong></a><div class="position-card current"><span>你在這裡</span><strong>05. 從 main() 到可服務的程序</strong></div><a class="position-card" href="#chapter-06-設定檔其實是一套小型語言"><span>下一站</span><strong>06. 設定檔其實是一套小型語言</strong></a></div>

本章位於 **Part 2：啟動、設定、Process 與 Reload**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Request 能被處理以前，程序必須完成參數解析、log、設定、module 初始化、socket 建立與 process mode 選擇。本章解釋這些步驟為何有嚴格順序：後一步往往依賴前一步建立的 global context。

Use case 包括 `nginx -t` 只驗證設定、single mode 直接進 event loop、master mode fork workers。若初始化順序任意，錯誤訊息、設定 rollback 與 socket ownership 都會變得不可靠。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Request 能被處理以前，程序必須完成參數解析、log、設定、module 初始化、socket 建立與 process mode 選擇。本章解釋這些步驟為何有嚴格順序：後一步往往依賴前一步建立的 global context。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 包括 <code>nginx -t</code> 只驗證設定、single mode 直接進 event loop、master mode fork workers。若初始化順序任意，錯誤訊息、設定 rollback 與 socket ownership 都會變得不可靠。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「程序 bootstrap」這個責任邊界；接收 argv、環境、config path 與 inherited sockets，交付 一個可運行的 cycle，接著進 single/master mode。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 process-global state 與第一個 <code>ngx_cycle_t</code> 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 設定錯誤、資源建立失敗或 daemon/process 啟動失敗。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>程序 bootstrap</p></div><div class="contract-card"><span>接收什麼</span><p>argv、環境、config path 與 inherited sockets</p></div><div class="contract-card"><span>產生什麼</span><p>一個可運行的 cycle，接著進 single/master mode</p></div><div class="contract-card"><span>狀態由誰保存</span><p>process-global state 與第一個 <code>ngx_cycle_t</code></p></div><div class="contract-card"><span>主要失敗出口</span><p>設定錯誤、資源建立失敗或 daemon/process 啟動失敗</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>解析 command-line options</p></div><div class="flow-step"><span>2</span><p>初始化時間、pid、log 與 OS abstraction</p></div><div class="flow-step"><span>3</span><p>建立 init cycle 並解析設定</p></div><div class="flow-step"><span>4</span><p>開啟 listening sockets／files／shared memory</p></div><div class="flow-step"><span>5</span><p>依選項 daemonize</p></div><div class="flow-step"><span>6</span><p>選 single 或 master process cycle</p></div><div class="flow-step"><span>7</span><p>worker 初始化 module 後進 event loop</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
main()
  ├─ parse options / init time / log
  ├─ init bootstrap pool + init_cycle
  ├─ OS capabilities / modules
  ├─ ngx_init_cycle(init_cycle)
  │      └─ parse config + open resources
  └─ single_process_cycle()
         or master_process_cycle()

HTTP request 尚未出現；這裡是在建立「可以處理 request 的世界」。
```

## 從零建立心智模型

`main()` 的責任是把 process 從普通 UNIX 程式轉成 NGINX runtime。它先建立一個很小的 `init_cycle`，只放足以解析完整設定的資源；真正設定、模組 context、listening sockets 與 shared memory 由 `ngx_init_cycle()` 建立。

初始化順序帶有依賴。例如 OS 初始化取得 page size 與 cache line size，之後 slab 與 CRC table 才能正確初始化。這類順序不是風格問題，而是隱含 dependency graph；讀啟動碼時應把「A 必須在 B 前」寫出原因。

完成 cycle 後，`main()` 不進 HTTP loop，而是選 single 或 master process cycle。HTTP 只是註冊在 listening socket 與 event layer 上的協定模組之一。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

把所有初始化塞成一個無邊界函式，任何一步失敗時都不知道哪些資源已建立。Staged bootstrap 讓每一階段只依賴前一階段，並能在明確邊界停止。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>stages list</td><td><code>main()</code> 中 argument/log/OS/cycle/process mode 的初始化順序</td></tr><tr><td><code>cycle</code> stage</td><td><code>ngx_init_cycle()</code></td></tr><tr><td>listeners</td><td>config 驗證後準備的 listening sockets</td></tr><tr><td>mode</td><td><code>ngx_single_process_cycle</code> 或 <code>ngx_master_process_cycle</code></td></tr></tbody></table></div>

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

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_get_options()</code> 處理 <code>-t/-T/-s/-p/-c/-g</code> 等啟動模式。</p></div><div class="source-step"><span>2</span><p>建立 bootstrap pool 與 <code>init_cycle</code>，初始化 log、argv、prefix。</p></div><div class="source-step"><span>3</span><p><code>ngx_os_init()</code> 探測頁面大小、CPU、socket 能力等平台資訊。</p></div><div class="source-step"><span>4</span><p><code>ngx_preinit_modules()</code> 先安排 module index；<code>ngx_init_cycle()</code> 再建立 module conf。</p></div><div class="source-step"><span>5</span><p>設定測試或 signal command 可提前返回；正常服務才進 process cycle。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>把 <code>main()</code> 先切成階段，不要立即進每個 helper。</p></div><div class="microscope-card"><span>2</span><p>找每個 early return 前已建立哪些 global/resource。</p></div><div class="microscope-card"><span>3</span><p>注意 <code>ngx_init_cycle()</code> 同時用於初次啟動與 reload。</p></div><div class="microscope-card"><span>4</span><p>檢查 inherited sockets 與 daemonize 發生的相對順序。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- `main()` 很長但多數是 orchestration；先標出 phase，不要陷入每個 helper。
- `ngx_init_cycle()` 是啟動與 reload 共用核心，不只是初始化函式。
- Inherited sockets 讓 binary upgrade/reload 不必重新 bind。
- Error path 與正常路徑同樣重要：初始化到哪裡，就只能 cleanup 到哪裡。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/nginx.c#L200`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/nginx.c#L200) · [`src/os/unix/ngx_posix_init.c#L35`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_posix_init.c#L35) · [`src/core/ngx_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_module.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

注意 `nginx -s reload` 並不是在這個新程序裡重建所有 worker。這個 command 讀 pid file，向既有 master 發 signal，然後退出；真正 reload 發生在 master process cycle。

`init_cycle` 和正式 cycle 的雙階段設計是 bootstrap pattern：解析完整世界前先建立最小世界。Compiler、database 與 dependency injection container 也常有類似階段。

條件編譯會讓不同 build 的 main 路徑不同，例如 SSL、PCRE、control API。讀源碼必須搭配 `nginx -V`，否則可能研究一條二進位根本沒有的分支。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Staged bootstrap</h3><p>每一步只使用已建立的 dependency，錯誤可在邊界停止。</p></div><div class="pattern-card"><h3>Two-phase construction</h3><p>先解析描述，再建立會產生 side effect 的 runtime 資源。</p></div><div class="pattern-card"><h3>Mode dispatch</h3><p>共同 bootstrap 後才分 single/master/signaller 路徑。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 在 `main()` 每個早退點旁寫出對應 CLI 情境。
2. 執行 `nginx -t`、`-T`、`-s reload`，用 strace 比較是否建立 listening socket 或 fork。
3. 從 `ngx_os_init` 找出 page size，追到哪個 allocator 使用它。
4. 比較含與不含 `--with-debug` 的 `nginx -V` 和 binary size。

## 常見誤解與失敗模式

- 認為 `nginx -s reload` 的程序就是 master；它通常只是 signal sender。
- 忽略 configure flags，閱讀不存在於目前 binary 的路徑。
- 把初始化順序當成任意排列，未辨認隱含依賴。

## 可以帶走的 Coding／CS 能力

- 理解 bootstrap initialization 與 dependency ordering。
- 讀懂 feature flags／conditional compilation 對產品行為的影響。
- 把 CLI mode、control plane 與 data plane 分開。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Bootstrap 的核心工作之一是讀設定；下一章把設定檔視為一門小語言。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 為什麼需要 `init_cycle`？</summary>

完整 cycle 的建立需要 pool、log、prefix 與 argv 等資源，但這些又不能依賴尚未解析的完整設定。最小 bootstrap cycle 打破循環依賴。

</details>

<details class="qa" markdown="1">
<summary>Q2. `main()` 為何幾乎不包含 HTTP 邏輯？</summary>

Core 只建立通用 runtime、process 與 event infrastructure；HTTP module 透過 module hooks 與 listening handler 接入，維持層次分離。

</details>

<details class="qa" markdown="1">
<summary>Q3. `nginx -t` 會完全不碰外部資源嗎？</summary>

不是。它需要解析設定並驗證許多檔案、socket 或憑證相關條件；但完成測試後不會進入長期 worker serving loop。精確行為應以 trace 驗證。

</details>

<details class="qa" markdown="1">
<summary>Q4. 初始化順序 bug 通常怎麼發生？</summary>

某 component 假設 global capability、page size、module index 或 log 已就緒。重構順序卻未把依賴顯式化，便會出現未初始化值或錯誤 allocation。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如何知道目前 binary 有哪些條件分支？</summary>

看 `nginx -V` configure arguments、產生的 `objs/ngx_auto_config.h` 與 module list，再對照 `#if`。

</details>

<details class="qa" markdown="1">
<summary>Q6. Control plane 與 data plane 在這裡怎麼區分？</summary>

解析設定、signal/reload、管理 worker 屬 control plane；worker 接受連線、解析與代理 request 屬 data plane。啟動流程建立兩者的邊界。

</details>

---

# 第 6 章　設定檔其實是一套小型語言

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Lexer 與 parser</h3><div class="foundation-block"><span>白話定義</span><p>Lexer 把字元切成 token；parser 再依文法把 tokens 組成有意義的結構。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>proxy_read_timeout 3s;</code> 可被切成指令名、參數與分號，再交給對應 module。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX config loader 讀 token、尋找 directive command table，並檢查參數與所在 context。</p></div></section><section class="foundation-card"><h3>Directive（設定指令）</h3><div class="foundation-block"><span>白話定義</span><p>設定檔中的一條命令，由名稱與參數構成，告訴某個 module 建立或修改 configuration。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>listen 443 ssl;</code> 與 <code>proxy_pass http://app;</code> 都是 directives。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>每個 module 用 command table 宣告自己認識哪些 directives 及其 setter callback。</p></div></section><section class="foundation-card"><h3>Configuration context 與 merge</h3><div class="foundation-block"><span>白話定義</span><p>同一設定可能出現在全域、server 或 location；merge 是把父層預設值與子層覆寫組成最終設定。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>父 location 設 timeout 30 秒，子 location 可改成 3 秒；沒改的欄位繼承父層。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 config time 建立多份 conf object，runtime request 只需選擇合併後的結果。</p></div></section><section class="foundation-card"><h3>Module（模組）</h3><div class="foundation-block"><span>白話定義</span><p>一組遵守固定介面的功能程式碼，可以註冊設定指令、request handler、filter 或 lifecycle hook。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Proxy、gzip、access control 都是不同 modules，但共同掛在 NGINX core 提供的擴充點。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>Core 負責協調生命週期；module 專注自己的 configuration 與 request 行為。</p></div></section></div>



<p class="chapter-question">一行 `proxy_pass http://backend;` 如何找到正確模組、欄位與設定 callback？</p>

<div class="chapter-meta"><span>難度：中階</span><span>parser · dispatch table · configuration merge</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

拆開 lexer、directive dispatch、context 驗證、create/merge config，理解 declarative config 背後的 interpreter。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node active"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-05-從-main-到可服務的程序"><span>上一站</span><strong>05. 從 main() 到可服務的程序</strong></a><div class="position-card current"><span>你在這裡</span><strong>06. 設定檔其實是一套小型語言</strong></div><a class="position-card" href="#chapter-07-ngx-cycle-t-一代設定的完整世界"><span>下一站</span><strong>07. ngx_cycle_t：一代設定的完整世界</strong></a></div>

本章位於 **Part 2：啟動、設定、Process 與 Reload**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

NGINX 的設定檔不是一堆直接賦值，而是 lexer/parser、directive dispatch、context validation 與多層 merge 組成的小型語言。這讓 core 不必認識每個 module 的 directive，也讓同一 directive 能在 http/server/location 層覆寫。

Use case 是 `proxy_read_timeout 3s;` 如何找到 proxy module 的 command、解析時間、寫入正確層級的 conf，最後在 nested location 繼承。沒有這套模型，每加一個 module 都要修改中央 parser。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>NGINX 的設定檔不是一堆直接賦值，而是 lexer/parser、directive dispatch、context validation 與多層 merge 組成的小型語言。這讓 core 不必認識每個 module 的 directive，也讓同一 directive 能在 http/server/location 層覆寫。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 <code>proxy_read_timeout 3s;</code> 如何找到 proxy module 的 command、解析時間、寫入正確層級的 conf，最後在 nested location 繼承。沒有這套模型，每加一個 module 都要修改中央 parser。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Configuration compiler」這個責任邊界；接收 文字 token 與目前 block context，交付 各 module 的 main/server/location conf 與 runtime tables。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 temporary parser state + cycle pool configuration 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 未知 directive、參數錯誤、context 不合法、merge 衝突。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Configuration compiler</p></div><div class="contract-card"><span>接收什麼</span><p>文字 token 與目前 block context</p></div><div class="contract-card"><span>產生什麼</span><p>各 module 的 main/server/location conf 與 runtime tables</p></div><div class="contract-card"><span>狀態由誰保存</span><p>temporary parser state + cycle pool configuration</p></div><div class="contract-card"><span>主要失敗出口</span><p>未知 directive、參數錯誤、context 不合法、merge 衝突</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>Lexer 讀出 directive name 與 arguments</p></div><div class="flow-step"><span>2</span><p>遍歷 module command tables 找名稱</p></div><div class="flow-step"><span>3</span><p>檢查 directive 可出現的 context 與參數數量</p></div><div class="flow-step"><span>4</span><p>定位該 module 的 conf object</p></div><div class="flow-step"><span>5</span><p>呼叫 command setter 解析並寫值</p></div><div class="flow-step"><span>6</span><p>離開 block 時 merge parent/child</p></div><div class="flow-step"><span>7</span><p>init phase 把 config 編譯成 runtime 結構</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

NGINX 設定不是逐行 if/else。每個 module 提供 `ngx_command_t` table，描述 directive 名稱、允許 context、參數數量、set callback，以及值應寫入哪類 config。Core parser 只負責 token、block 與通用 dispatch，不需要知道 `proxy_pass` 的語意。

HTTP module 通常有 main/server/location 三層 configuration。Parse 開始前，各 module 的 `create_*_conf` 先產生物件；block 結束後，`merge_*_conf` 把 parent 值、child 值與 default 合成 runtime config。這是 hierarchical configuration，不是簡單 inheritance。

大量 runtime 效能來自 config-time 預計算：編譯 regex、建立 hash、排序 location、解析 complex value script。Worker 處理每個 request 時直接讀已整理好的結構。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

中央 parser 若為每個 directive 寫 `if/elif`，加入 module 就必須修改 core。Table-driven dispatch 讓 directive 自己帶名稱、合法 context 與 setter；merge 則區分『未設定』與合法零值。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>COMMANDS</code></td><td>各 module 的 <code>ngx_command_t[]</code></td></tr><tr><td><code>contexts</code></td><td>directive type/context flags</td></tr><tr><td><code>setter</code></td><td>command set callback</td></tr><tr><td>parent/child merge</td><td>create/merge loc conf 與 <code>NGX_CONF_UNSET*</code> sentinel</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/ngx_conf_file.c`，官方 `release-1.31.5` 第 158–203 行

```c
ngx_conf_parse(ngx_conf_t *cf, ngx_str_t *filename)
{
    char             *rv;
    ngx_fd_t          fd;
    ngx_int_t         rc;
    ngx_buf_t         buf;
    ngx_conf_file_t  *prev, conf_file;
    enum {
        parse_file = 0,
        parse_block,
        parse_param
    } type;

#if (NGX_SUPPRESS_WARN)
    fd = NGX_INVALID_FILE;
    prev = NULL;
#endif

    if (filename) {

        /* open configuration file */

        fd = ngx_open_file(filename->data, NGX_FILE_RDONLY, NGX_FILE_OPEN, 0);

        if (fd == NGX_INVALID_FILE) {
            ngx_conf_log_error(NGX_LOG_EMERG, cf, ngx_errno,
                               ngx_open_file_n " \"%s\" failed",
                               filename->data);
            return NGX_CONF_ERROR;
        }

        prev = cf->conf_file;

        cf->conf_file = &conf_file;

        if (ngx_fd_info(fd, &cf->conf_file->file.info) == NGX_FILE_ERROR) {
            ngx_log_error(NGX_LOG_EMERG, cf->log, ngx_errno,
                          ngx_fd_info_n " \"%s\" failed", filename->data);
        }

        cf->conf_file->buffer = &buf;

        buf.start = ngx_alloc(NGX_CONF_BUFFER, cf->log);
        if (buf.start == NULL) {
            goto failed;
        }
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_conf_read_token()</code> 產生 token，處理引號、escape、<code>;</code> 與 <code>{}</code>。</p></div><div class="source-step"><span>2</span><p><code>ngx_conf_handler()</code> 遍歷當前 modules 的 command table，匹配名稱。</p></div><div class="source-step"><span>3</span><p>command type bitmask 驗證 directive 能否出現在 main/http/server/location 等 context。</p></div><div class="source-step"><span>4</span><p><code>cmd-&gt;set</code> 可能是通用 setter，也可能是模組自訂 parser。</p></div><div class="source-step"><span>5</span><p>HTTP block 建立每模組 main/srv/loc conf arrays，之後初始化與 merge。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Parser 找到 command 後仍要定位正確 module conf slot。</p></div><div class="microscope-card"><span>2</span><p>Setter 的 return contract 是 <code>NGX_CONF_OK</code>／error string，不是 request handler return code。</p></div><div class="microscope-card"><span>3</span><p>Merge 要在 nested blocks 建立完成後執行。</p></div><div class="microscope-card"><span>4</span><p>Runtime 快路徑通常使用已編譯／合併結果，不再解析文字 directive。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 未設定值常用特殊 sentinel，而不是零；merge 必須分辨『未設』與合法零值。
- Create conf、merge conf、postconfiguration 是不同 lifecycle hook。
- Setter 回傳字串錯誤或 `NGX_CONF_OK`，不要套用普通 `NGX_OK` contract。
- Config context array 的 index 來自 module ctx index，不是 module 編譯順序直覺。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_conf_file.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_conf_file.c#L1) · [`src/http/ngx_http.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http.c#L1) · [`src/http/modules/ngx_http_proxy_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/modules/ngx_http_proxy_module.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

`NGX_CONF_UNSET`、`NGX_CONF_UNSET_UINT` 等 sentinel 很重要：零可能是合法設定，不能用零同時代表「使用者沒寫」。Merge 通常遵循 child explicit > parent > default，但每個 directive 仍可定義特殊語意。

Module config lookup macro 看似魔法，本質是 module 的 `ctx_index` 當 array index。這讓 request-time 取得 config 近似 O(1)，代價是初始化期間必須一致安排 index。

錯誤訊息品質也是 parser 設計的一部分。好的 directive callback 應區分 invalid number、duplicate、unsupported context 與 resource failure，並附 file/line。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Table-driven parser</h3><p>directive metadata 與 setter table 取代中央 switch。</p></div><div class="pattern-card"><h3>Prototype/overlay config</h3><p>child 只覆寫明確值，其餘由 parent merge。</p></div><div class="pattern-card"><h3>Compile configuration</h3><p>昂貴 routing/hash/phase 結構在啟動時先建好。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 找 `proxy_pass` 的 command table entry，記下 type、set callback 與 loc conf。
2. 建立 parent/child location，分別設定 `proxy_read_timeout`，用 `nginx -T` 推理 merge 結果。
3. 新增一行參數數量錯誤的 directive，沿錯誤路徑找出 file/line 來源。
4. 找一個使用通用 slot setter 與一個自訂 setter 的 directive，比較差異。

## 常見誤解與失敗模式

- 以為所有未設定值都是零，忽略 UNSET sentinel。
- 把 merge 當一般物件導向繼承；實際上每個 module 自訂合成規則。
- 在 request path 重做 config-time 可完成的 parse 或 lookup。

## 可以帶走的 Coding／CS 能力

- 理解 table-driven parser 與 interpreter dispatch。
- 設計 hierarchical config、default 與 explicit-value precedence。
- 把昂貴工作移到初始化階段，縮短 hot path。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

所有解析後的設定與資源會被包進一個 generation；下一章介紹 `ngx_cycle_t`。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. NGINX core 如何在不知道 `proxy_pass` 的情況下解析它？</summary>

Proxy module 在 command table 註冊名稱、context 與 callback；core 做通用 tokenization 和 table lookup，找到後把控制交給 module。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為什麼需要 UNSET 而不能只用零？</summary>

零可能表示合法值，例如停用某上限。若零也表示未設定，merge 無法分辨 child 明確寫零還是應繼承 parent。

</details>

<details class="qa" markdown="1">
<summary>Q3. `ctx_index` 的價值是什麼？</summary>

將 module-specific config 放進 array，runtime 以 index 直接取得，避免每個 request 做名稱查找或型別遍歷。

</details>

<details class="qa" markdown="1">
<summary>Q4. 哪些工作適合 config-time 預計算？</summary>

不依 request 變動且可能昂貴的工作，如 regex compile、location tree/hash 建立、固定 upstream 解析與 script compile。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如果 reload 新設定失敗，舊 worker 為何還能服務？</summary>

新 cycle 在獨立 pool 與 config context 中建立；失敗可丟棄新 cycle，舊 cycle 與既有 worker 的資料不必被部分修改。

</details>

<details class="qa" markdown="1">
<summary>Q6. 這套模式可遷移到哪裡？</summary>

Compiler pass table、CLI subcommand、serialization schema、plugin registry 與 dependency injection container 都可使用 metadata＋callback dispatch。

</details>

---

# 第 7 章　ngx_cycle_t：一代設定的完整世界

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Configuration generation</h3><div class="foundation-block"><span>白話定義</span><p>一次完整載入的設定與相關資源稱為一個 generation。新舊 generation 可以暫時同時存在。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Reload 後新 workers 使用新路由；舊 workers 繼續用舊設定完成既有 requests。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_cycle_t</code> 是一個 generation 的根 object，集中持有 sockets、files、shared memory 與 module conf。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section><section class="foundation-card"><h3>Socket</h3><div class="foundation-block"><span>白話定義</span><p>Socket 是程式與網路連線互動的 OS object。程式用它 listen、accept、connect、read 與 write。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Listening socket 等待新客人；accepted socket 則只代表某一位 client 的 TCP connection。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 把 socket 包裝成 <code>ngx_connection_t</code>，再附加 read/write events 與 protocol state。</p></div></section><section class="foundation-card"><h3>Shared memory</h3><div class="foundation-block"><span>白話定義</span><p>可被多個 processes 看見的同一塊記憶體。因為會同時讀寫，所以通常需要 atomic operation 或 lock。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>所有 workers 共用 rate-limit counter，不能只存在某一個 worker 的一般 heap。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 shared memory zones 保存 cache metadata、upstream state 與跨 worker counters。</p></div></section></div>



<p class="chapter-question">為什麼 NGINX 不直接修改全域設定，而是每次建立新的 cycle？</p>

<div class="chapter-meta"><span>難度：中階</span><span>generation · resource ownership · transactional reload</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

把 cycle 理解為一個 configuration generation，掌握 reload、資源擁有權與新舊世界並存。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node active"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-06-設定檔其實是一套小型語言"><span>上一站</span><strong>06. 設定檔其實是一套小型語言</strong></a><div class="position-card current"><span>你在這裡</span><strong>07. ngx_cycle_t：一代設定的完整世界</strong></div><a class="position-card" href="#chapter-08-master-worker-process-model"><span>下一站</span><strong>08. Master–Worker Process Model</strong></a></div>

本章位於 **Part 2：啟動、設定、Process 與 Reload**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

NGINX 需要 reload 而不中斷服務，因此「目前設定」不能只是可原地修改的 global singleton。`ngx_cycle_t` 把一代設定、listening sockets、open files、shared memory、module conf 與 pool 包成一個完整 generation。

Use case 是先建立新設定世界，全部成功後再讓新 worker 使用；若失敗，舊 cycle 繼續服務。沒有 generation boundary，reload 到一半失敗會留下新舊資源混合的半成品。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>NGINX 需要 reload 而不中斷服務，因此「目前設定」不能只是可原地修改的 global singleton。<code>ngx_cycle_t</code> 把一代設定、listening sockets、open files、shared memory、module conf 與 pool 包成一個完整 generation。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是先建立新設定世界，全部成功後再讓新 worker 使用；若失敗，舊 cycle 繼續服務。沒有 generation boundary，reload 到一半失敗會留下新舊資源混合的半成品。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Configuration generation」這個責任邊界；接收 舊 cycle、config files 與 inherited resources，交付 完整且可提交的新 cycle。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 cycle pool 擁有該代 config/resource metadata 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 任何解析或 resource prepare 失敗都必須放棄新 cycle。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Configuration generation</p></div><div class="contract-card"><span>接收什麼</span><p>舊 cycle、config files 與 inherited resources</p></div><div class="contract-card"><span>產生什麼</span><p>完整且可提交的新 cycle</p></div><div class="contract-card"><span>狀態由誰保存</span><p>cycle pool 擁有該代 config/resource metadata</p></div><div class="contract-card"><span>主要失敗出口</span><p>任何解析或 resource prepare 失敗都必須放棄新 cycle</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>以舊 cycle 作為可重用資源來源</p></div><div class="flow-step"><span>2</span><p>建立新 pool 與 cycle</p></div><div class="flow-step"><span>3</span><p>create 各 module conf</p></div><div class="flow-step"><span>4</span><p>解析並 merge config</p></div><div class="flow-step"><span>5</span><p>準備 files、shared zones、listening sockets</p></div><div class="flow-step"><span>6</span><p>全部成功後交給新 workers</p></div><div class="flow-step"><span>7</span><p>舊 cycle 等舊 workers drained 再釋放</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
old cycle (generation N)             new cycle (generation N+1)
├─ old config                         ├─ parsed config
├─ old listening ───── reuse ───────> ├─ listening
├─ old shared memory ─ compatible ──> ├─ shared memory
└─ old workers continue               └─ new workers start

成功：切換 global current cycle
失敗：丟棄 new pool，old cycle 不受污染
```

## 從零建立心智模型

`ngx_cycle_t` 不只是設定物件。它聚合這一代 runtime 使用的 module conf、listening sockets、open files、shared memory zones、connection/event arrays、paths、log 與 pool。將它視為「generation root」比視為 config struct 更準確。

Reload 的核心不是修改舊 cycle，而是以舊 cycle 為輸入建立新 cycle。建立過程可比較 listening address、shared memory zone name/size 與 open files，決定重用、開新或延後關閉。只有全部成功才啟動新 worker。

這近似 transaction：prepare 新狀態、驗證、commit 切換；失敗則 rollback by discard。它不是完整資料庫 transaction，但 isolation 思路相同。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

原地修改 global config 會讓 request 看見半新半舊狀態。Generation object 先建立完整候選世界，全部成功後一次 publish；失敗就丟棄候選，不碰 active generation。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Generation</code></td><td><code>ngx_cycle_t</code></td></tr><tr><td>candidate</td><td><code>ngx_init_cycle(old_cycle)</code> 建出的新 cycle</td></tr><tr><td>validation before assignment</td><td>全部 config/resource 成功後才交給新 workers</td></tr><tr><td>old remains</td><td>reload 失敗時舊 cycle 繼續服務</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/ngx_cycle.c`，官方 `release-1.31.5` 第 39–86 行

```c
ngx_init_cycle(ngx_cycle_t *old_cycle)
{
    void                *rv, *data;
    char               **senv;
    ngx_uint_t           i, n;
    ngx_log_t           *log;
    ngx_time_t          *tp;
    ngx_conf_t           conf;
    ngx_pool_t          *pool;
    ngx_cycle_t         *cycle, **old;
    ngx_shm_zone_t      *shm_zone, *oshm_zone;
    ngx_list_part_t     *part, *opart;
    ngx_open_file_t     *file;
    ngx_listening_t     *ls, *nls;
    ngx_core_conf_t     *ccf, *old_ccf;
    ngx_core_module_t   *module;
    char                 hostname[NGX_MAXHOSTNAMELEN];

    ngx_timezone_update();

    /* force localtime update with a new timezone */

    tp = ngx_timeofday();
    tp->sec = 0;

    ngx_time_update();


    log = old_cycle->log;

    pool = ngx_create_pool(NGX_CYCLE_POOL_SIZE, log);
    if (pool == NULL) {
        return NULL;
    }
    pool->log = log;

    cycle = ngx_pcalloc(pool, sizeof(ngx_cycle_t));
    if (cycle == NULL) {
        ngx_destroy_pool(pool);
        return NULL;
    }

    cycle->pool = pool;
    cycle->log = log;
    cycle->old_cycle = old_cycle;

    cycle->conf_prefix.len = old_cycle->conf_prefix.len;
    cycle->conf_prefix.data = ngx_pstrdup(pool, &old_cycle->conf_prefix);
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_init_cycle(old_cycle)</code> 先建立全新 cycle pool 與 zeroed cycle。</p></div><div class="source-step"><span>2</span><p>複製 prefix、config path 等 bootstrap 資訊，建立各種 container。</p></div><div class="source-step"><span>3</span><p>建立 modules 與 core conf，解析完整設定。</p></div><div class="source-step"><span>4</span><p>初始化 modules、shared memory、listening sockets、open files。</p></div><div class="source-step"><span>5</span><p>成功後 global <code>ngx_cycle</code> 指向新 generation；舊 cycle 延後清理。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Reload 時新舊 cycle 會同時存在，global pointer 不代表只有一個 object。</p></div><div class="microscope-card"><span>2</span><p>找哪些 sockets/shared zones 可以 reuse，哪些 metadata 必須新建。</p></div><div class="microscope-card"><span>3</span><p>Cycle pool 是 generation lifetime root。</p></div><div class="microscope-card"><span>4</span><p>任何 module init failure 都應讓 candidate rollback，而不是部分 publish。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 不要把 `ngx_cycle` global pointer 誤解成永遠只有一個 cycle；reload 時新舊代會並存。
- Socket 可被新 cycle reuse，但 metadata 與 worker ownership 屬於不同 generation。
- Shared memory zone 的 name/size compatibility 決定能否沿用資料。
- 真正安全點是新 cycle 完整成功之後，而不是 config parse 完成之後。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_cycle.h#L39`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_cycle.h#L39) · [`src/core/ngx_cycle.c#L39`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_cycle.c#L39) · [`src/core/ngx_connection.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_connection.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Cycle pool 使失敗清理簡單：尚未發布的新 generation 可以整池銷毀。但 OS resources 仍需精確處理，因為 socket、file、shared memory 不是普通 heap bytes；所以 init code 有大量 error path 與 cleanup bookkeeping。

Listening socket 的重用是 graceful reload 的關鍵。若 address/options 相容，新 worker 可繼承既有 fd，避免先 close 再 bind 的空窗。舊 worker 停止 accept 後仍能完成手上連線。

Shared memory zone 需要更嚴格 compatibility。若名稱相同但 size 或 tag 不相容，不能把舊 memory 當新 layout 使用；這是 persistent state schema evolution 的縮影。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Generation object</h3><p>一個 immutable-ish object 代表完整設定版本。</p></div><div class="pattern-card"><h3>Transactional replace</h3><p>先 build/validate，再 publish；失敗不污染 active generation。</p></div><div class="pattern-card"><h3>Lifetime root</h3><p>大量子資源依附同一 cycle pool 與 cleanup。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 列出 `ngx_cycle_t` 中屬於設定、OS resource、runtime array 的欄位。
2. 對同一 listen address reload，使用 `ls -l /proc/PID/fd` 觀察 fd 是否跨 worker 繼承。
3. 故意把新設定寫成語法錯誤，確認舊 worker 與舊 cycle 仍服務。
4. 修改 shared memory zone size，觀察設定驗證與 reload 行為。

## 常見誤解與失敗模式

- 把 cycle 當 immutable 純設定；它也擁有大量 runtime resource。
- 認為 pool destroy 能自動處理所有 fd 與 shared memory。
- 直接原地修改共享結構，破壞 reload 失敗時的回退能力。

## 可以帶走的 Coding／CS 能力

- 理解 immutable generation、copy-on-reconfigure 與 transactional publish。
- 設計資源 root 與明確 ownership tree。
- 理解 schema compatibility、rolling upgrade 與 RCU 類思想。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

有了 generation，下一章看 master 如何管理多個 worker 與這些資源。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Cycle 為什麼適合當 generation root？</summary>

所有由同一設定推導的 module conf、listener、shared zone 與 runtime arrays 可掛在同一 ownership root，切換與清理都有清楚邊界。

</details>

<details class="qa" markdown="1">
<summary>Q2. Reload 失敗為什麼不會留下半套新設定？</summary>

新狀態在獨立 cycle/pool 建立，尚未 publish；任一步失敗即可關閉新資源並丟棄新 cycle，舊 generation 未被原地修改。

</details>

<details class="qa" markdown="1">
<summary>Q3. 舊 cycle 為何不能切換後立刻釋放？</summary>

舊 worker、舊 connection 或 cleanup 仍可能引用其中的 config、log、listener metadata；必須等引用它的 execution generation 退場。

</details>

<details class="qa" markdown="1">
<summary>Q4. Socket 重用避免了什麼問題？</summary>

避免 reload 中斷 accept、避免 bind 競爭與短暫 port unavailable，也讓新舊 worker 可平滑交接。

</details>

<details class="qa" markdown="1">
<summary>Q5. Shared memory 為何要檢查 tag/size？</summary>

同名不代表資料 layout 相同。錯把舊 bytes 按新 struct 解讀會造成越界或語意 corruption；tag/size 是最低限度 schema guard。

</details>

<details class="qa" markdown="1">
<summary>Q6. 這和 RCU 有何相似與不同？</summary>

相似處是發布新版本、舊讀者繼續使用舊版本、延後回收；不同處是 NGINX 主要以 process generation 和 resource lifecycle 實作，不是通用 kernel RCU primitive。

</details>

---

# 第 8 章　Master–Worker Process Model

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Master–worker model</h3><div class="foundation-block"><span>白話定義</span><p>Master 負責控制與生命週期；workers 負責大量日常資料處理。兩者刻意分工。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Master 收到 reload signal 後建立新 workers；worker 的 event loop 實際讀寫 client sockets。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>這把低頻 control plane 與高頻 data plane 分開，簡化 worker hot path。</p></div></section><section class="foundation-card"><h3>Process 與 thread 的差別</h3><div class="foundation-block"><span>白話定義</span><p>同一 process 內的 threads 共用大部分記憶體；不同 processes 通常彼此隔離。兩者都可以被 OS 排程到 CPU。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Thread 間共享 object 很方便，但需要同步；worker processes 的一般 request state 則天然分離。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 主要用多 workers 擴充 CPU，少數 blocking 工作才交給 thread pool。</p></div></section><section class="foundation-card"><h3>Worker process</h3><div class="foundation-block"><span>白話定義</span><p>長時間運行並實際處理 client connections 的 NGINX 子程序。每個 worker 通常有自己的 event loop。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>四核心主機可能啟動四個 workers，各自處理一批 connections。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>阻塞其中一個 worker 會延遲該 worker 管理的所有 ready events。</p></div></section><section class="foundation-card"><h3>fork</h3><div class="foundation-block"><span>白話定義</span><p><code>fork()</code> 建立一個新的 child process；child 一開始看見 parent 記憶體的邏輯副本，但之後各自執行。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Master 完成設定後 fork workers，讓它們繼承 listening sockets。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>這讓 workers 共用啟動結果，同時保持故障與一般 heap 更新彼此隔離。</p></div></section></div>



<p class="chapter-question">為什麼 NGINX 選擇多程序 worker，而不是讓所有工作都在 master 或大量 thread 中執行？</p>

<div class="chapter-meta"><span>難度：中階</span><span>process isolation · control plane · signals</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解 master 是 control plane、worker 是 data plane，以及 process isolation、signal 與 channel 的代價。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node active"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-07-ngx-cycle-t-一代設定的完整世界"><span>上一站</span><strong>07. ngx_cycle_t：一代設定的完整世界</strong></a><div class="position-card current"><span>你在這裡</span><strong>08. Master–Worker Process Model</strong></div><a class="position-card" href="#chapter-09-graceful-reload-為什麼不會中斷連線"><span>下一站</span><strong>09. Graceful Reload 為什麼不會中斷連線</strong></a></div>

本章位於 **Part 2：啟動、設定、Process 與 Reload**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

單一 event loop 能處理很多 I/O，但仍只使用一個 CPU core，而且單一 process crash 會中斷全部服務。NGINX 以 master 管 control plane，以多個 worker 管 data plane；worker 通常彼此獨立處理 connection。

Use case 是利用多核心、隔離 crash、集中處理 signals 與 reload。這個設計刻意避免讓每個 request 在 threads 間共享大量 mutable state。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>單一 event loop 能處理很多 I/O，但仍只使用一個 CPU core，而且單一 process crash 會中斷全部服務。NGINX 以 master 管 control plane，以多個 worker 管 data plane；worker 通常彼此獨立處理 connection。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是利用多核心、隔離 crash、集中處理 signals 與 reload。這個設計刻意避免讓每個 request 在 threads 間共享大量 mutable state。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Master–worker runtime」這個責任邊界；接收 設定 generation、signals、listening sockets，交付 多個獨立 worker event loops。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 master 擁有 process topology；worker 擁有自己的 connection state 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 worker crash、signal race、spawn failure、shared resource contention。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Master–worker runtime</p></div><div class="contract-card"><span>接收什麼</span><p>設定 generation、signals、listening sockets</p></div><div class="contract-card"><span>產生什麼</span><p>多個獨立 worker event loops</p></div><div class="contract-card"><span>狀態由誰保存</span><p>master 擁有 process topology；worker 擁有自己的 connection state</p></div><div class="contract-card"><span>主要失敗出口</span><p>worker crash、signal race、spawn failure、shared resource contention</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>master 完成 bootstrap</p></div><div class="flow-step"><span>2</span><p>建立 channel/socketpair</p></div><div class="flow-step"><span>3</span><p>fork worker</p></div><div class="flow-step"><span>4</span><p>worker 關閉不需要的 fd 並初始化 modules</p></div><div class="flow-step"><span>5</span><p>worker 進 event loop 處理 request</p></div><div class="flow-step"><span>6</span><p>master 接收 signal/child status</p></div><div class="flow-step"><span>7</span><p>必要時重生、reload 或優雅關閉</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
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
```

## 從零建立心智模型

Master 不處理一般 HTTP request。它啟動與監督 worker、接收管理 signal、reload config、reopen log、進行 binary upgrade。Worker 降低權限後進入 event loop，處理 client 與 upstream I/O。

多程序提供 fault containment：某 worker crash 不直接破壞另一 worker 的 heap；master 可以 reap 並 respawn。也減少共享 heap 與細粒度 lock 的需求。代價是跨 worker state 需 shared memory 或 IPC，connection 也不能像 thread 一樣任意搬移。

「一個 worker 一個 event loop」不表示一次只能處理一個 request；它表示某一時刻只有一段 handler 在該 worker CPU 上執行，但數千 request 的狀態可交錯停在不同 I/O 邊界。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

用 threads 共享所有 request state 會需要大量 locks。NGINX 預設用多個 process，每個 worker 擁有自己的 event loop 與 connections，只把必要狀態放 shared memory。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>parent process</td><td>NGINX master</td></tr><tr><td>child <code>Process</code></td><td>worker process</td></tr><tr><td>listener name</td><td>fork 前準備並由 workers 繼承的 listening fd</td></tr><tr><td><code>local_connections</code></td><td>每個 worker 私有的 connection table/event loop state</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/os/unix/ngx_process_cycle.c`，官方 `release-1.31.5` 第 74–121 行

```c
ngx_master_process_cycle(ngx_cycle_t *cycle)
{
    char              *title;
    u_char            *p;
    size_t             size;
    ngx_int_t          i;
    ngx_uint_t         sigio;
    sigset_t           set;
    struct itimerval   itv;
    ngx_uint_t         live;
    ngx_msec_t         delay;
    ngx_core_conf_t   *ccf;

    sigemptyset(&set);
    sigaddset(&set, SIGCHLD);
    sigaddset(&set, SIGALRM);
    sigaddset(&set, SIGIO);
    sigaddset(&set, SIGINT);
    sigaddset(&set, ngx_signal_value(NGX_RECONFIGURE_SIGNAL));
    sigaddset(&set, ngx_signal_value(NGX_REOPEN_SIGNAL));
    sigaddset(&set, ngx_signal_value(NGX_NOACCEPT_SIGNAL));
    sigaddset(&set, ngx_signal_value(NGX_TERMINATE_SIGNAL));
    sigaddset(&set, ngx_signal_value(NGX_SHUTDOWN_SIGNAL));
    sigaddset(&set, ngx_signal_value(NGX_CHANGEBIN_SIGNAL));

    if (sigprocmask(SIG_BLOCK, &set, NULL) == -1) {
        ngx_log_error(NGX_LOG_ALERT, cycle->log, ngx_errno,
                      "sigprocmask() failed");
    }

    sigemptyset(&set);


    size = sizeof(master_process);

    for (i = 0; i < ngx_argc; i++) {
        size += ngx_strlen(ngx_argv[i]) + 1;
    }

    title = ngx_pnalloc(cycle->pool, size);
    if (title == NULL) {
        /* fatal */
        exit(2);
    }

    p = ngx_cpymem(title, master_process, sizeof(master_process) - 1);
    for (i = 0; i < ngx_argc; i++) {
        *p++ = ' ';
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_master_process_cycle()</code> block 管理 signals，啟動 workers/cache helpers。</p></div><div class="source-step"><span>2</span><p>Master 用 signal flags 在安全主循環內執行複雜動作，而非直接在 signal handler 做。</p></div><div class="source-step"><span>3</span><p><code>ngx_spawn_process()</code> fork child，建立 channel socketpair。</p></div><div class="source-step"><span>4</span><p>Worker 初始化 module hooks、event backend、connection arrays，然後循環處理 events/timers。</p></div><div class="source-step"><span>5</span><p>Child exit 由 master reap；依 respawn policy 決定是否重建。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Fork 後普通 memory 更新不會自動跨 worker 可見。</p></div><div class="microscope-card"><span>2</span><p>Master 處理 signal/child status，worker 處理 request。</p></div><div class="microscope-card"><span>3</span><p>Listening accept 的協調策略與 process count/reuseport 有關。</p></div><div class="microscope-card"><span>4</span><p>檢查 worker init hooks 在 fork 後建立哪些 process-local resources。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Fork 後的記憶體看似相同，但 copy-on-write；普通變數不是跨 worker 共享。
- Listening socket 可由多 worker 共同 accept，需理解 accept mutex/reuseport policy。
- Worker 初始化失敗的 error path 會影響 master 是否重試。
- Channel message 與 Unix signals 都是 control message，注意各自可攜帶的資訊量。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/os/unix/ngx_process_cycle.c#L74`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_process_cycle.c#L74) · [`src/os/unix/ngx_process.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_process.c#L1) · [`src/os/unix/ngx_channel.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_channel.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Signal handler 必須 async-signal-safe，因此通常只設定 `sig_atomic_t` flag；master loop 被喚醒後再做 allocation、logging、fork 等工作。這是將 interrupt context 轉換為 normal context 的標準模式。

Worker 數量通常接近可用 CPU，但不是機械公式。CPU affinity、blocking third-party module、SSL workload、disk I/O 與容器 quota 都會改變最佳值。過多 worker 會增加 context switch、shared contention 與 cache footprint。

Channel 讓 master 通知 worker open/close channel、quit 等控制訊息。這比把所有管理狀態放 shared memory 更容易維護事件順序。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Control plane / data plane split</h3><p>管理決策與 request 處理分離。</p></div><div class="pattern-card"><h3>Process isolation</h3><p>address space 隔離降低共享狀態與 crash blast radius。</p></div><div class="pattern-card"><h3>Supervisor</h3><p>master 監控 child 並依 policy 重生。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 用 `ps -o pid,ppid,stat,cmd` 畫出 master/worker parent relation。
2. 向一個 worker 發 SIGKILL，觀察 master 是否 respawn 及既有連線影響。
3. 用 `/proc/PID/fd` 比較 master 與 worker 持有的 listening socket。
4. 在單 worker 的 handler 中 sleep，觀察同 worker 所有 request 延遲。

## 常見誤解與失敗模式

- 認為 event-driven 等同 parallel；單 worker handler 仍是 serial CPU execution。
- 在 signal handler 中直接做 malloc、log 或複雜 reload。
- 認為 worker 越多吞吐一定越高，忽略 CPU quota 與 contention。

## 可以帶走的 Coding／CS 能力

- 理解 process isolation、supervision tree 與 crash-only recovery。
- 區分 control plane/data plane。
- 理解 event concurrency、CPU parallelism 與 thread concurrency 的差別。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

多 generation 加上 master–worker，才能實現下一章的 graceful reload。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 一個 worker 如何同時服務很多 request？</summary>

它保存每個 request 的狀態，只在對應 fd ready 或 timer 到期時執行一小段 handler；等待 I/O 的 request 不佔用 call stack 或 thread。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為什麼 master 不直接處理 request？</summary>

管理與 serving 分離可讓 reload、respawn、權限下降與失敗隔離更清楚；master 的狀態也不會被複雜 request module 污染。

</details>

<details class="qa" markdown="1">
<summary>Q3. Signal handler 為何只設 flag？</summary>

可安全呼叫的函式極少；malloc、stdio、一般 logging 都可能 deadlock 或破壞狀態。設原子 flag 後由 normal loop 處理最安全。

</details>

<details class="qa" markdown="1">
<summary>Q4. Worker crash 後 client 一定無感嗎？</summary>

不是。該 worker 擁有的 active connections 會中斷；其他 worker 繼續服務，新連線可由 respawn worker 接手。Process isolation 降低 blast radius，不消除單連線失敗。

</details>

<details class="qa" markdown="1">
<summary>Q5. 什麼情況一個 worker per CPU 不合適？</summary>

容器 CPU quota、NUMA、blocking module、重 SSL/regex workload、磁碟 thread pool 等都可能需要實測；應看 CPU saturation、run queue、tail latency 和 lock contention。

</details>

<details class="qa" markdown="1">
<summary>Q6. 為何跨 worker connection 不容易遷移？</summary>

Socket fd、event registration、request pointers、pool 與 module context 都在該 process address space。遷移需要 fd passing 和完整狀態序列化，成本與複雜度高。

</details>

---

# 第 9 章　Graceful Reload 為什麼不會中斷連線

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Graceful reload</h3><div class="foundation-block"><span>白話定義</span><p>載入新設定時不立刻殺死舊工作，而是先啟動新 generation，再讓舊 generation 停止接新工作並逐步退出。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>部署新 certificate 時，正在下載檔案的 client 不會立刻被 reset。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX master 驗證新 cycle、啟動新 workers，向舊 workers 發送 graceful shutdown 訊號。</p></div></section><section class="foundation-card"><h3>Draining 與 in-flight work</h3><div class="foundation-block"><span>白話定義</span><p>In-flight 是已開始但尚未完成的工作；draining 是停止接新工作，同時等待 in-flight 工作結束。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>餐廳打烊後不再接新單，但仍把廚房中已下的單做完。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>舊 worker 關閉 idle listeners/keep-alive admission，完成 active requests 後退出。</p></div></section><section class="foundation-card"><h3>Configuration generation</h3><div class="foundation-block"><span>白話定義</span><p>一次完整載入的設定與相關資源稱為一個 generation。新舊 generation 可以暫時同時存在。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Reload 後新 workers 使用新路由；舊 workers 繼續用舊設定完成既有 requests。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_cycle_t</code> 是一個 generation 的根 object，集中持有 sockets、files、shared memory 與 module conf。</p></div></section><section class="foundation-card"><h3>Long-lived connection</h3><div class="foundation-block"><span>白話定義</span><p>持續很久而不是每個 request 結束就關閉的連線，可能大部分時間沒有資料。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>WebSocket、長時間下載與 streaming response 都可能存活數分鐘或數小時。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>它們會延長舊 worker、舊 config 與 connection resources 的存活時間。</p></div></section><section class="foundation-card"><h3>HTTP keep-alive</h3><div class="foundation-block"><span>白話定義</span><p>完成一個 HTTP request 後不立刻關閉 TCP connection，讓同一 client 之後可在同一條連線上再送 request，省下重新建立 TCP 連線的時間。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>瀏覽器用同一條 connection 先取 HTML，再依序取圖片與 API response。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX finalize 舊 request、清除 request-lifetime state，再把 connection handler 改成等待下一個 request。</p></div></section></div>



<p class="chapter-question">SIGHUP 之後新設定如何上線，而舊 request 又為什麼能繼續完成？</p>

<div class="chapter-meta"><span>難度：進階</span><span>graceful shutdown · draining · generation handoff</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

沿 master 與 worker 兩條時間線理解 zero-downtime reload、draining、失敗回退與長連線風險。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node active"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-08-master-worker-process-model"><span>上一站</span><strong>08. Master–Worker Process Model</strong></a><div class="position-card current"><span>你在這裡</span><strong>09. Graceful Reload 為什麼不會中斷連線</strong></div><a class="position-card" href="#chapter-10-socket-file-descriptor-與-tcp-最小基礎"><span>下一站</span><strong>10. Socket、File Descriptor 與 TCP 最小基礎</strong></a></div>

本章位於 **Part 2：啟動、設定、Process 與 Reload**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

線上服務不能每次改設定都先關機。Graceful reload 的核心不是『修改正在跑的 worker』，而是建立新 generation 與新 workers，再請舊 workers 停止接新連線、把既有工作做完後退出。

Use case 是更新 routing、certificate、log 或 module config，同時保留長連線與正在傳輸的大 response。沒有 draining，新部署會直接 reset client connections。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>線上服務不能每次改設定都先關機。Graceful reload 的核心不是『修改正在跑的 worker』，而是建立新 generation 與新 workers，再請舊 workers 停止接新連線、把既有工作做完後退出。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是更新 routing、certificate、log 或 module config，同時保留長連線與正在傳輸的大 response。沒有 draining，新部署會直接 reset client connections。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Generation handoff」這個責任邊界；接收 reload signal + 舊 cycle，交付 新 workers 接新流量，舊 workers drained 後退出。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 新舊 cycle／worker 各自擁有其 connection 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 新 config 無效、舊連線不結束、資源版本不相容。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Generation handoff</p></div><div class="contract-card"><span>接收什麼</span><p>reload signal + 舊 cycle</p></div><div class="contract-card"><span>產生什麼</span><p>新 workers 接新流量，舊 workers drained 後退出</p></div><div class="contract-card"><span>狀態由誰保存</span><p>新舊 cycle／worker 各自擁有其 connection</p></div><div class="contract-card"><span>主要失敗出口</span><p>新 config 無效、舊連線不結束、資源版本不相容</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>master 收到 HUP</p></div><div class="flow-step"><span>2</span><p>用舊 cycle 建立並驗證新 cycle</p></div><div class="flow-step"><span>3</span><p>spawn new-generation workers</p></div><div class="flow-step"><span>4</span><p>新 workers 開始 accept</p></div><div class="flow-step"><span>5</span><p>通知 old workers graceful quit</p></div><div class="flow-step"><span>6</span><p>舊 workers 關閉 listening sockets</p></div><div class="flow-step"><span>7</span><p>完成 existing connections 後退出</p></div><div class="flow-step"><span>8</span><p>master 回收 old cycle resources</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
time ─────────────────────────────────────────────>

master:  receive HUP ─ build new cycle ─ spawn N+1 ─ signal old quit
old WN:  accept───────┐ stop accept ─ drain active ─ exit
new W:                  init ─ accept new traffic ───────────────>

若 new cycle 建立失敗：
old WN:  繼續 accept 與服務；不發布半套設定
```

## 從零建立心智模型

Graceful reload 是 generation handoff，不是把 worker 內設定原地換掉。Master 收到 reconfigure flag 後呼叫 `ngx_init_cycle(old)`；成功才啟動新 workers，並向舊 workers 發 graceful shutdown signal。

舊 worker 收到 quit 後關閉 listening sockets、關閉 idle connections，但讓 active requests 與 non-cancelable timers 繼續。當 event loop 判斷沒有必要工作，worker 才退出。新 worker 同時接受新連線。

因此「不會中斷」有條件：正常而有限的 request 可以完成；無限 WebSocket、卡住 upstream、buggy module timer 或永不結束的 streaming 可能讓舊 generation 長時間不退。`worker_shutdown_timeout` 是最後邊界，不是正常控制手段。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

直接殺掉舊 workers 再啟動新 workers 會中斷既有連線。Graceful reload 讓新 generation 先開始接新工作，舊 generation 只停止 admission，等手上的工作歸零再退出。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
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
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>two <code>Worker</code> objects</td><td>reload 時並存的新舊 worker generations</td></tr><tr><td><code>accepting=False</code></td><td>graceful quit 後關閉 listening sockets</td></tr><tr><td><code>active</code></td><td>仍在處理的 connections/requests</td></tr><tr><td>exit when zero</td><td>舊 worker 完成 existing work 後離開</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/os/unix/ngx_process_cycle.c`，官方 `release-1.31.5` 第 233–277 行

```c
        if (ngx_reconfigure) {
            ngx_reconfigure = 0;

            if (ngx_new_binary) {
                ngx_start_worker_processes(cycle, ccf->worker_processes,
                                           NGX_PROCESS_RESPAWN);
                ngx_start_cache_manager_processes(cycle, 0);
                ngx_noaccepting = 0;

                continue;
            }

            ngx_log_error(NGX_LOG_NOTICE, cycle->log, 0, "reconfiguring");

            cycle = ngx_init_cycle(cycle);
            if (cycle == NULL) {
                cycle = (ngx_cycle_t *) ngx_cycle;
                continue;
            }

            ngx_cycle = cycle;
            ccf = (ngx_core_conf_t *) ngx_get_conf(cycle->conf_ctx,
                                                   ngx_core_module);
            ngx_start_worker_processes(cycle, ccf->worker_processes,
                                       NGX_PROCESS_JUST_RESPAWN);
            ngx_start_cache_manager_processes(cycle, 1);

            /* allow new processes to start */
            ngx_msleep(100);

            live = 1;
            ngx_signal_worker_processes(cycle,
                                        ngx_signal_value(NGX_SHUTDOWN_SIGNAL));
        }

        if (ngx_restart) {
            ngx_restart = 0;
            ngx_start_worker_processes(cycle, ccf->worker_processes,
                                       NGX_PROCESS_RESPAWN);
            ngx_start_cache_manager_processes(cycle, 0);
            live = 1;
        }

        if (ngx_reopen) {
            ngx_reopen = 0;
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Master signal handler 設 <code>ngx_reconfigure</code>，master loop 醒來。</p></div><div class="source-step"><span>2</span><p>建立新 cycle；若失敗記錄錯誤並保持舊 cycle。</p></div><div class="source-step"><span>3</span><p>成功後啟動新 worker/cache helper。</p></div><div class="source-step"><span>4</span><p>向舊 worker 發 graceful shutdown；舊 worker 設 <code>ngx_exiting</code>。</p></div><div class="source-step"><span>5</span><p>舊 worker 關 listener、idle connections，持續 event loop 到 timers/active work 完成。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>HUP path 先建新 cycle；失敗時不可 signal old workers。</p></div><div class="microscope-card"><span>2</span><p>舊 worker 停止 accept 不代表立即退出。</p></div><div class="microscope-card"><span>3</span><p>長連線會延長 old generation lifetime。</p></div><div class="microscope-card"><span>4</span><p>Module cleanup 不得假設 reload 後 old conf 已無 request 引用。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Reload 成功不代表舊 worker 立即消失；長連線會延長並存時間。
- 觀察 pid 與 generation，而不是只看 master pid。
- Module cleanup 必須尊重 old request 仍可能引用 old cycle conf。
- 若 shared zone 需要保留資料，size/name 與 init callback 必須支援 generation handoff。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/os/unix/ngx_process_cycle.c#L74`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_process_cycle.c#L74) · [`src/core/ngx_cycle.c#L39`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_cycle.c#L39) · [`src/core/ngx_connection.c#L1120`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_connection.c#L1120)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Listener fd 可能在 master 中跨 generation 保存，再由 fork 繼承。這避免重新 bind 的時間窗，也讓新 worker 能立即接流量。若 listen options 改變到不相容，cycle init 需要重新配置或報錯。

Drain 的判斷不能只看「active connection count 為零」。可取消 timer、cache helper、subrequest、upstream cleanup 都可能影響退出；實作使用 event/timer 狀態與 connection close 路徑共同完成。

Reload 也是 deploy correctness 問題。設定語法正確不代表行為正確；應先 `-t`、再 canary/觀察新 worker pid、錯誤率與舊 worker drain 時間。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Blue-green inside one host</h3><p>新舊 generation 暫時並存並逐步交接。</p></div><div class="pattern-card"><h3>Drain protocol</h3><p>停止接新工作，但允許已接受工作完成。</p></div><div class="pattern-card"><h3>Transactional configuration</h3><p>新代失敗時舊代完全不受影響。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 保持一條慢 request，同時 reload；用 pid 與 access log 證明它在哪一代完成。
2. 用語法錯誤 config reload，確認 master/old worker 不退出。
3. 建立長連線或很長 proxy timeout，測量舊 worker drain 時間。
4. 比較 `quit` 與 `stop` 對 active connection 的影響。

## 常見誤解與失敗模式

- 把 graceful 理解成所有連線永遠不會斷；它仍受 timeout、process crash 與 shutdown deadline 約束。
- 只看新 worker 已啟動，未監控舊 worker是否長期殘留。
- 在 reload 前只跑 syntax test，未驗證 upstream、憑證與實際 traffic 行為。

## 可以帶走的 Coding／CS 能力

- 設計 draining、rolling restart 與 deployment health gate。
- 理解 versioned config 與 active request 的一致性邊界。
- 辨識長連線對 zero-downtime deployment 的特殊需求。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Part 2 建好了服務世界；Part 3 從最底層的 socket 開始看 request 如何真正進來。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 舊 request 在 reload 後使用新設定嗎？</summary>

通常不會。它所在舊 worker 繼續引用舊 cycle/module conf；新連線由新 worker 使用新 generation，避免半途語意改變。

</details>

<details class="qa" markdown="1">
<summary>Q2. 新設定解析失敗時為什麼不影響舊服務？</summary>

新 cycle 隔離建立，失敗不 publish，也不先終止舊 worker。這是 prepare-before-switch。

</details>

<details class="qa" markdown="1">
<summary>Q3. 為什麼舊 worker要關閉 idle keep-alive connection？</summary>

若保留 idle connection，它可能持續接收新 request，使舊 generation 無法收斂退出；關閉 idle 讓 client 重連到新 worker。

</details>

<details class="qa" markdown="1">
<summary>Q4. 長 WebSocket 會造成什麼問題？</summary>

舊 worker可能因 active connection 長期不退，持有舊 binary、設定與資源。需要明確 max connection age、drain policy 或強制 shutdown deadline。

</details>

<details class="qa" markdown="1">
<summary>Q5. Graceful reload 與 load balancer draining 有何共同點？</summary>

都是先停止接新工作，再完成 in-flight，最後釋放舊 instance；核心指標是新工作入口、active work 與最大 drain time。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何驗證 reload 真正成功？</summary>

不只看 command exit code；確認新 worker pid、配置 generation、error log、真實 request 行為、舊 worker drain，以及 upstream health。

</details>

---
