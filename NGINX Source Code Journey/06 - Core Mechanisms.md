---
title: "藏在 NGINX 裡的 CS 核心"
part: 6
source_baseline: release-1.31.5
---

# Part 6　藏在 NGINX 裡的 CS 核心

把記憶體池、資料結構、buffer chain、shared memory 與 module system 放回真實使用場景。

# 第 34 章　Memory Pool 與生命週期

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Heap、malloc/free 與 memory pool</h3><div class="foundation-block"><span>白話定義</span><p>Heap 支援個別配置與釋放；memory pool/arena 把許多相同 lifetime 的小 allocations 綁在一起，最後整批釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>一個 request 建立數十個 headers/nodes，逐一處理所有 error-path free 很容易遺漏。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX request pool 用 pointer bump 快速配置，request 結束時 destroy pool；大型 allocation 與 cleanup 另行追蹤。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section><section class="foundation-card"><h3>Cleanup handler</h3><div class="foundation-block"><span>白話定義</span><p>Memory 消失不代表外部資源或副作用會自動復原；cleanup handler 是 object 結束時必須執行的收尾工作。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Temporary file、open fd 或第三方 library handle 必須明確 close。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 將 cleanup 掛在 pool，讓正常與錯誤路徑共用同一個 lifecycle 收口。</p></div></section><section class="foundation-card"><h3>Pointer（指標）</h3><div class="foundation-block"><span>白話定義</span><p>Pointer 保存另一塊記憶體的位址。<code>p-&gt;field</code> 表示到 <code>p</code> 指向的 object 取出 <code>field</code>。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>函式收到 <code>ngx_http_request_t *r</code>，並不是複製整個 request，而是取得它的位置。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>讀 NGINX 時要同時追 pointer 指向誰、object 由誰擁有，以及 object 何時失效。</p></div></section></div>



<p class="chapter-question">NGINX 為什麼大量使用 pool，而不是每建立一個小物件就配對一次 malloc/free？</p>

<div class="chapter-meta"><span>難度：中階</span><span>arena allocation · lifetime · cleanup</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

從request/connection/cycle生命週期推導region allocation，理解small/large allocation、cleanup與限制。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node active"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-33-proxy-cache"><span>上一站</span><strong>33. Proxy Cache</strong></a><div class="position-card current"><span>你在這裡</span><strong>34. Memory Pool 與生命週期</strong></div><a class="position-card" href="#chapter-35-資料結構不是考題-而是設計選擇"><span>下一站</span><strong>35. 資料結構不是考題，而是設計選擇</strong></a></div>

本章位於 **Part 6：藏在 NGINX 裡的 CS 核心**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

Event-driven code 有大量短命小物件；若每個欄位都 malloc/free，error path 會非常複雜且容易 leak。NGINX pool 把 allocation 綁定明確 lifecycle：request 結束時整批釋放，必要 side effect 則登記 cleanup handler。

Use case 是 headers、module ctx、chain links 等數十個 request-lifetime allocations。Pool 不是通用 garbage collector；它的威力來自『同一批物件同生共死』。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>Event-driven code 有大量短命小物件；若每個欄位都 malloc/free，error path 會非常複雜且容易 leak。NGINX pool 把 allocation 綁定明確 lifecycle：request 結束時整批釋放，必要 side effect 則登記 cleanup handler。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 headers、module ctx、chain links 等數十個 request-lifetime allocations。Pool 不是通用 garbage collector；它的威力來自『同一批物件同生共死』。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Region/arena allocator」這個責任邊界；接收 指定 pool 上的 size/alignment allocation request，交付 與 pool 同壽命的 memory；可選 cleanup record。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 small blocks、large allocation list、cleanup list 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 把短命 pointer 存到長命 owner、忘記 cleanup 外部資源、誤以為可逐一 free。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Region/arena allocator</p></div><div class="contract-card"><span>接收什麼</span><p>指定 pool 上的 size/alignment allocation request</p></div><div class="contract-card"><span>產生什麼</span><p>與 pool 同壽命的 memory；可選 cleanup record</p></div><div class="contract-card"><span>狀態由誰保存</span><p>small blocks、large allocation list、cleanup list</p></div><div class="contract-card"><span>主要失敗出口</span><p>把短命 pointer 存到長命 owner、忘記 cleanup 外部資源、誤以為可逐一 free</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>建立與 cycle/connection/request 對應的 pool</p></div><div class="flow-step"><span>2</span><p>small allocation 從目前 block bump pointer 取得</p></div><div class="flow-step"><span>3</span><p>空間不足時找其他 block 或擴充</p></div><div class="flow-step"><span>4</span><p>large allocation 另外 malloc 並掛 list</p></div><div class="flow-step"><span>5</span><p>需要 close/free side effect 時註冊 cleanup</p></div><div class="flow-step"><span>6</span><p>工作期間通常不逐一 free</p></div><div class="flow-step"><span>7</span><p>owner lifecycle 結束時執行 cleanups</p></div><div class="flow-step"><span>8</span><p>一次釋放所有 blocks/large allocations</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
cycle pool ───────────────────────── configuration generation
   ├─ module conf / listeners / paths

connection pool ───────────── TCP connection
   ├─ sockaddr / log / protocol connection state

request pool ─────── one HTTP request
   ├─ headers / module ctx / upstream / chains
   └─ destroy whole pool at request end

生命週期越短的資料，不可被更長生命週期物件引用。
```

## 從零建立心智模型

Pool先配置一塊block，small allocations只做alignment與pointer bump；空間不足時串接新block。大配置可能單獨malloc並掛在large list，`ngx_pfree`主要能提早釋放這類large allocation。

價值不只速度，而是lifetime correctness：request內數十個小物件不需分散free；request結束時執行cleanups後整池銷毀。這把ownership從「每個pointer」提升成「region」。

Pool不會自動呼叫任意resource destructor。File、temp file、library handle等需註冊cleanup handler；否則heap bytes釋放了，OS resource仍leak。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

逐一追蹤每個短命 allocation 的 free 會讓所有 error path 複雜。Arena 將同壽命 objects 放進同一 owner，結束時整批釋放；外部資源則另登記 cleanup。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
class Arena:
    def __init__(self):
        self.objects = []
        self.cleanups = []

    def allocate(self, factory):
        value = factory()
        self.objects.append(value)
        return value

    def cleanup(self, fn):
        self.cleanups.append(fn)

    def destroy(self):
        for fn in reversed(self.cleanups):
            fn()
        self.objects.clear()

request_pool = Arena()
headers = request_pool.allocate(list)
request_pool.cleanup(lambda: print("close temp file"))
headers.append(("Host", "example.test"))
request_pool.destroy()
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Arena</code></td><td><code>ngx_pool_t</code></td></tr><tr><td><code>allocate</code></td><td><code>ngx_palloc</code>/<code>ngx_pcalloc</code></td></tr><tr><td>objects clear</td><td>pool blocks 一次 destroy，而非逐物件 free</td></tr><tr><td>cleanup list</td><td><code>ngx_pool_cleanup_t</code> 用於 file/library side effects</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/ngx_palloc.c`，官方 `release-1.31.5` 第 123–168 行

```c
ngx_palloc(ngx_pool_t *pool, size_t size)
{
#if !(NGX_DEBUG_PALLOC)
    if (size <= pool->max) {
        return ngx_palloc_small(pool, size, 1);
    }
#endif

    return ngx_palloc_large(pool, size);
}


void *
ngx_pnalloc(ngx_pool_t *pool, size_t size)
{
#if !(NGX_DEBUG_PALLOC)
    if (size <= pool->max) {
        return ngx_palloc_small(pool, size, 0);
    }
#endif

    return ngx_palloc_large(pool, size);
}


static ngx_inline void *
ngx_palloc_small(ngx_pool_t *pool, size_t size, ngx_uint_t align)
{
    u_char      *m;
    ngx_pool_t  *p;

    p = pool->current;

    do {
        m = p->d.last;

        if (align) {
            m = ngx_align_ptr(m, NGX_ALIGNMENT);
        }

        if ((size_t) (p->d.end - m) >= size) {
            p->d.last = m + size;

            return m;
        }

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p><code>ngx_create_pool</code> 建首block，保存d.last/end/next/failed。</p></div><div class="source-step"><span>2</span><p><code>ngx_palloc</code> 對small size掃blocks、對齊並bump last。</p></div><div class="source-step"><span>3</span><p>Block失敗次數高時更新current，避免每次從已滿block掃起。</p></div><div class="source-step"><span>4</span><p>Large allocation以獨立pointer node追蹤，可由<code>ngx_pfree</code>提早free。</p></div><div class="source-step"><span>5</span><p><code>ngx_destroy_pool</code> 先跑cleanup，再free large與所有blocks。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>先問 pool owner 是 cycle、connection 還是 request。</p></div><div class="microscope-card"><span>2</span><p>Small allocations 通常不能用 <code>ngx_pfree</code> 逐一回收。</p></div><div class="microscope-card"><span>3</span><p>Pointer 不得逃到比 pool 更長命的 cache/global object。</p></div><div class="microscope-card"><span>4</span><p>Cleanup callback 的順序與是否可能重入需要明確。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 配置在哪個 pool 比『哪裡 palloc』更重要；先追 pool owner。
- `ngx_pfree` 主要針對 large allocations，不代表 small objects 可普遍逐一 free。
- Pool reset/destroy 後 pointer 全部失效，不能 cache 到更長生命週期。
- Cleanup handler 執行順序與重複註冊會影響 resource safety。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_palloc.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_palloc.h#L1) · [`src/core/ngx_palloc.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_palloc.c#L1) · [`src/http/ngx_http_request.c#L539`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_request.c#L539)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Region allocation犧牲個別小物件回收；若在長生命週期connection pool不斷放request資料，就會像leak一樣成長到connection關閉。選pool比選allocator API更重要。

Pool reset可重用blocks但會使舊pointer失效；所有跨reset引用都危險。Memory sanitizer不一定能立即抓到，因為bytes仍映射。

Cleanup註冊順序與idempotency要清楚。Error path、normal finalize、connection abort可能交錯，cleanup應能辨認resource是否仍open。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Arena allocation</h3><p>大量同壽命物件以低成本配置與整批回收。</p></div><div class="pattern-card"><h3>Lifetime ownership</h3><p>pool 是明確 owner boundary，而非隱藏 global allocator。</p></div><div class="pattern-card"><h3>Cleanup registry</h3><p>memory 之外的 file/library resource 以 callback 收口。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 在一個request中連續palloc小物件，觀察地址與block last移動。
2. 配置超過max的小物件，找large list與`ngx_pfree`。
3. 註冊開檔cleanup，分別從成功與錯誤路徑驗證執行一次。
4. 故意把request資料放connection pool，長keepalive壓測觀察RSS。

## 常見誤解與失敗模式

- 把pool當garbage collector；它不追蹤可達性，也不自動析構外部資源。
- 從短生命週期pool返回pointer給長生命週期cache。
- 為方便全部放cycle/connection pool，造成長期成長。

## 可以帶走的 Coding／CS 能力

- 理解arena/region allocator與ownership tree。
- 使用lifetime分類降低free複雜度。
- 辨認resource cleanup與memory release的差異。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Pool 解決 allocation；下一章比較 array、list、queue、hash、rbtree 等資料結構為何各自存在。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Pool最大優點只是malloc比較快嗎？</summary>

不是。更大的價值是把同生命週期物件整批釋放，降低error path與ownership複雜度；速度與fragmentation是附帶收益。

</details>

<details class="qa" markdown="1">
<summary>Q2. 為什麼small allocation通常不能個別p_free？</summary>

Pool只bump pointer，沒有每個small object的獨立allocator metadata；中間洞也不易有效重用，設計目標是整region回收。

</details>

<details class="qa" markdown="1">
<summary>Q3. 什麼資料應放request pool而不是connection pool？</summary>

只服務單一HTTP交換的headers、module ctx、upstream state、body/output chains；keepalive後不再需要就應隨request釋放。

</details>

<details class="qa" markdown="1">
<summary>Q4. Cleanup handler解決什麼？</summary>

釋放file descriptor、temp file、library object等需要動作的resource；純free pool bytes不會自動執行這些副作用。

</details>

<details class="qa" markdown="1">
<summary>Q5. Pool reset後舊pointer為什麼危險？</summary>

Memory可能仍存在但已可被下一allocation覆寫，形成silent use-after-lifetime；不是只有munmap後才算dangling。

</details>

<details class="qa" markdown="1">
<summary>Q6. 何時不適合pool？</summary>

物件生命週期差異大、需頻繁個別刪除、長期資料量不可預測或ownership跨region時，專用allocator/refcount可能更清楚。

</details>

---

# 第 35 章　資料結構不是考題，而是設計選擇

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>從 operations 選資料結構</h3><div class="foundation-block"><span>白話定義</span><p>先列出最常做的 operations、排序需求、刪除方式與 lifetime，再選 array、queue、hash 或 tree；不要先背資料結構名稱。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Headers 常 append/iterate；timer 要找最小 deadline 並任意刪除，需求完全不同。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 hot path 與 memory layout 選 intrusive queue、rbtree、hash、radix tree 等 containers。</p></div></section><section class="foundation-card"><h3>Intrusive container</h3><div class="foundation-block"><span>白話定義</span><p>資料結構的 link node 直接嵌在業務 object 裡，而不是另外配置 wrapper node。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Timer object 內含 rbtree node；已知 node 位址後，可計算回原本的 timer/event object。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>這能減少 allocation 與 pointer chasing，但要求讀者理解 container-of 與 object lifetime。</p></div></section><section class="foundation-card"><h3>Red-black tree（紅黑樹）</h3><div class="foundation-block"><span>白話定義</span><p>一種保持大致平衡的排序樹，使查找、插入與刪除通常維持 O(log n)。重點不是旋轉公式，而是它支援的 operations。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>數萬個 timers 依 deadline 排序；需要快速找最早到期者，也要任意取消其中一個。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 將 timer node intrusive 地放進 event object，最左節點就是下一個 deadline。</p></div></section><section class="foundation-card"><h3>Lifetime / ownership</h3><div class="foundation-block"><span>白話定義</span><p>Lifetime 是 object 從建立到失效的期間；ownership 表示誰負責讓它保持有效並在最後釋放。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Request 結束後 request pool 會整批釋放，因此 timer callback 不能再引用其中資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 的 cycle、connection、request 與 upstream 各有不同 lifetime，許多 bug 都來自混用。</p></div></section></div>



<p class="chapter-question">Array、list、queue、hash、紅黑樹與radix tree在NGINX裡分別服務哪種workload？</p>

<div class="chapter-meta"><span>難度：中階</span><span>data structures · workload · intrusive containers</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

以操作分布、allocation、locality、ordering與prefix lookup選結構，建立可遷移的資料結構判斷表。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node active"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-34-memory-pool-與生命週期"><span>上一站</span><strong>34. Memory Pool 與生命週期</strong></a><div class="position-card current"><span>你在這裡</span><strong>35. 資料結構不是考題，而是設計選擇</strong></div><a class="position-card" href="#chapter-36-buffer-chain-與-zero-copy-思維"><span>下一站</span><strong>36. Buffer、Chain 與 Zero-Copy 思維</strong></a></div>

本章位於 **Part 6：藏在 NGINX 裡的 CS 核心**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

資料結構不是因為教科書列過就使用，而是由 operation set、lifetime、ordering、mutation frequency 與 memory layout 決定。NGINX 同時使用 array、list、queue、hash、radix tree、rbtree，正好展示『從 workload 導出 container』。

Use case 是 headers 需要 append/iterate、timers 需要 ordered min/delete、config names 需要快速 lookup、LRU 需要 O(1) move/remove。把所有東西都放 hash map 會失去順序、最小值或 intrusive ownership 的優勢。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>資料結構不是因為教科書列過就使用，而是由 operation set、lifetime、ordering、mutation frequency 與 memory layout 決定。NGINX 同時使用 array、list、queue、hash、radix tree、rbtree，正好展示『從 workload 導出 container』。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是 headers 需要 append/iterate、timers 需要 ordered min/delete、config names 需要快速 lookup、LRU 需要 O(1) move/remove。把所有東西都放 hash map 會失去順序、最小值或 intrusive ownership 的優勢。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Container selection discipline」這個責任邊界；接收 操作需求、資料量、lifetime 與 locality，交付 符合 workload 的結構與 invariant。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 通常由外層 pool/owner 管理；intrusive node 嵌在 object 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 選錯 complexity、忽略常數/locality、node 重複掛載、mutation invariant 破壞。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Container selection discipline</p></div><div class="contract-card"><span>接收什麼</span><p>操作需求、資料量、lifetime 與 locality</p></div><div class="contract-card"><span>產生什麼</span><p>符合 workload 的結構與 invariant</p></div><div class="contract-card"><span>狀態由誰保存</span><p>通常由外層 pool/owner 管理；intrusive node 嵌在 object</p></div><div class="contract-card"><span>主要失敗出口</span><p>選錯 complexity、忽略常數/locality、node 重複掛載、mutation invariant 破壞</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>先列主要 operations</p></div><div class="flow-step"><span>2</span><p>確認是否要排序、prefix、min、arbitrary delete</p></div><div class="flow-step"><span>3</span><p>估計資料量與啟動期/執行期比例</p></div><div class="flow-step"><span>4</span><p>決定 contiguous、chunked 或 pointer-linked layout</p></div><div class="flow-step"><span>5</span><p>決定 intrusive 或 owning container</p></div><div class="flow-step"><span>6</span><p>寫下 invariants</p></div><div class="flow-step"><span>7</span><p>用真實 workload benchmark/trace</p></div><div class="flow-step"><span>8</span><p>只在需求改變時換結構</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
需求                                  NGINX 常用結構
config-time append + runtime scan      ngx_array_t
append很多、地址穩定                   ngx_list_t (分part)
O(1) insert/remove已知節點             ngx_queue_t (intrusive)
字串exact/wildcard lookup              ngx_hash_t
排序、min、任意刪除                    ngx_rbtree_t
IP prefix longest-match                ngx_radix_tree_t

先問操作，再問 Big-O；還要問生命週期與cache locality。
```

## 從零建立心智模型

`ngx_array_t` 在pool內連續保存元素；若它恰好是pool最後allocation，可原地擴張，否則配置更大區域並copy。適合設定期逐步收集、之後唯讀遍歷。

`ngx_list_t` 不是傳統每node malloc linked list，而是由固定容量parts串接；每part內元素連續，兼顧append與地址穩定，常用於headers/open files。

`ngx_queue_t` 是intrusive doubly linked ring，適合LRU、posted events、free lists；已知node可O(1)移除。Hash與wildcard hash針對config/runtime名稱查找；rbtree支援timer/cache index；radix tree適合IPv4/IPv6 prefix。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

看到資料就使用 dict/list 是語言便利，不代表符合 operation set。這個例子先列需求，再選 heap、dict 或 deque；NGINX 同樣依 min、prefix、append、arbitrary delete 等操作選不同 container。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
from collections import deque
import heapq

def choose_structure(operations):
    if {"lookup_by_key", "insert"} <= operations:
        return "hash table"
    if {"find_min", "insert"} <= operations:
        return "heap or ordered tree"
    if {"append", "pop_left"} <= operations:
        return "queue/deque"
    return "array/list"

workloads = [
    {"lookup_by_key", "insert"},
    {"find_min", "insert", "delete_arbitrary"},
    {"append", "pop_left"},
]
for operations in workloads:
    print(operations, "->", choose_structure(operations))
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td>lookup workload</td><td>config/header hashes</td></tr><tr><td>find min + arbitrary delete</td><td>timer rbtree</td></tr><tr><td>append/iterate</td><td>NGINX array/list</td></tr><tr><td>queue/deque</td><td>posted events、LRU、free/busy chains</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/ngx_array.c`，官方 `release-1.31.5` 第 48–93 行

```c
ngx_array_push(ngx_array_t *a)
{
    void        *elt, *new;
    size_t       size;
    ngx_pool_t  *p;

    if (a->nelts == a->nalloc) {

        /* the array is full */

        size = a->size * a->nalloc;

        p = a->pool;

        if ((u_char *) a->elts + size == p->d.last
            && p->d.last + a->size <= p->d.end)
        {
            /*
             * the array allocation is the last in the pool
             * and there is space for new allocation
             */

            p->d.last += a->size;
            a->nalloc++;

        } else {
            /* allocate a new array */

            new = ngx_palloc(p, 2 * size);
            if (new == NULL) {
                return NULL;
            }

            ngx_memcpy(new, a->elts, size);
            a->elts = new;
            a->nalloc *= 2;
        }
    }

    elt = (u_char *) a->elts + a->size * a->nelts;
    a->nelts++;

    return elt;
}


```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>閱讀每個struct的layout，先列出提供的operations而非實作。</p></div><div class="source-step"><span>2</span><p>找一個真實caller，記錄資料何時建立、是否runtime修改。</p></div><div class="source-step"><span>3</span><p>比較allocation方式：連續、分part、intrusive embedded node。</p></div><div class="source-step"><span>4</span><p>分析lookup key：string exact、ordered numeric、prefix bit sequence。</p></div><div class="source-step"><span>5</span><p>最後才比較time complexity、memory overhead與cache locality。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>確認 container 是否 owns element，或只掛 intrusive node。</p></div><div class="microscope-card"><span>2</span><p>同一 object 可嵌多個 node 參與不同索引。</p></div><div class="microscope-card"><span>3</span><p>Big-O 之外看資料量、cache locality 與 configuration-time/runtime 比例。</p></div><div class="microscope-card"><span>4</span><p>Queue macros 通常不防重複插入，invariant 在 caller。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 看 container API 時先問 ownership：container 是否配置 element，還是只掛 node。
- Array 的 contiguous locality 常比理論擴容成本更重要。
- NGINX list 是分塊 append 結構，不等同一般 doubly linked list。
- Queue macros 不檢查 node 是否已掛載；invariant 由 caller 保證。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
typedef struct cache_node {
    rb_node   by_key;       /* lookup index */
    queue_link lru;         /* eviction order */
    string    key;
    value     data;
} cache_node;

lookup(key)  -> rbtree/hash
touch(node)  -> queue_remove(&node->lru), queue_insert_head(...)
evict()      -> container_of(queue_tail(), cache_node, lru)
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_array.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_array.c#L1) · [`src/core/ngx_list.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_list.c#L1) · [`src/core/ngx_queue.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_queue.h#L1) · [`src/core/ngx_hash.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_hash.c#L1) · [`src/core/ngx_rbtree.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_rbtree.c#L1) · [`src/core/ngx_radix_tree.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_radix_tree.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

資料結構可組合：file cache用rbtree做key lookup、queue做LRU；同一cache node內嵌tree node與queue link。這是「一份資料，多個index」的典型設計。

Config-time structures可接受較昂貴build，以換runtime compact lookup。NGINX hash builder會嘗試bucket size，避免每request動態resize；這是讀多寫少workload。

Intrusive結構要求物件不能在仍掛queue/tree時被釋放，也不能同一link同時進兩條queue；狀態discipline比wrapper container嚴格。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Workload-driven design</h3><p>先有操作與限制，再選 Big-O 與 layout。</p></div><div class="pattern-card"><h3>Intrusive multi-indexing</h3><p>同一 object 可嵌不同 node 同時進 timer/LRU 等索引。</p></div><div class="pattern-card"><h3>Build-time optimization</h3><p>config-time 花較多成本建立 runtime 快路徑。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 為headers、timers、LRU、IP allowlist各選一個結構並說明操作需求。
2. 找file cache node同時參與rbtree與queue的欄位。
3. 比較100個元素array scan與hash在build成本、memory、cache miss。
4. 故意把同一queue link插兩次，在小測試理解結構損壞。

## 常見誤解與失敗模式

- 只用漸進Big-O，不看元素數、build頻率與cache locality。
- 認為`ngx_list_t`是每元素一個heap node。
- 移除intrusive object前忘記先unlink所有indexes。

## 可以帶走的 Coding／CS 能力

- 以workload與資料生命週期選資料結構。
- 理解multi-index object與intrusive container。
- 平衡build-time cost、runtime lookup與memory layout。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Container 保存 metadata；下一章聚焦真正搬運 bytes 的 buffer 與 chain。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. Header為什麼常用part-based list而非單一array？</summary>

Header數量不確定且element地址需穩定；分part可append不搬移既有元素，同時每part仍連續，少於每node allocation。

</details>

<details class="qa" markdown="1">
<summary>Q2. Timer為什麼不用hash？</summary>

Scheduler需要最小deadline與有序到期，不只exact lookup；hash無法有效取得全域minimum。

</details>

<details class="qa" markdown="1">
<summary>Q3. File cache為何同時要tree與queue？</summary>

Tree按key快速找entry，queue按最近使用順序淘汰；兩種index服務不同操作。

</details>

<details class="qa" markdown="1">
<summary>Q4. Radix tree比普通hash適合IP policy在哪裡？</summary>

CIDR需要longest-prefix match，不是完整key exact match；radix沿bit prefix自然表示包含關係。

</details>

<details class="qa" markdown="1">
<summary>Q5. Config-time hash為何可不做動態resize？</summary>

設定reload時key集合已知，可一次計算bucket layout；runtime主要唯讀，避免鎖與resize。

</details>

<details class="qa" markdown="1">
<summary>Q6. 何時線性array反而勝hash？</summary>

元素很少、遍歷頻繁、build一次、cache locality重要時；hash的pointer/bucket與hash計算常數可能更高。

</details>

---

# 第 36 章　Buffer、Chain 與 Zero-Copy 思維

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Buffer</h3><div class="foundation-block"><span>白話定義</span><p>一段可讀或可寫的資料範圍，加上目前讀到哪裡、送到哪裡等位置資訊。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>8 KB memory 裡只有索引 100–340 是尚未送出的資料。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_buf_t</code> 可以描述 memory 或 file range；位置前進即可表示 partial read/write，而不必複製內容。</p></div></section><section class="foundation-card"><h3>Buffer chain</h3><div class="foundation-block"><span>白話定義</span><p>把多段不一定連續、來源不同的資料，用 linked nodes 表示成一個輸出序列。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Response headers 在 memory，body 在 file，最後還有一個 end marker。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p><code>ngx_chain_t</code> 串起 <code>ngx_buf_t</code>；partial write 只移動 positions，未送完 nodes 留在 busy chain。</p></div></section><section class="foundation-card"><h3>Zero-copy 思維</h3><div class="foundation-block"><span>白話定義</span><p>目標是避免把同一批 bytes 在 application buffers 間反覆複製；不代表整條路徑真的完全零次 copy。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>傳檔案時讓 kernel 直接把 file pages 送到 socket，比先讀進 user buffer 再 write 更省。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 <code>ngx_buf_t</code> 描述 memory/file ranges，以 <code>writev</code> 聚合 memory，以 <code>sendfile</code> 傳 file region。</p></div></section><section class="foundation-card"><h3>Non-blocking I/O 與 EAGAIN</h3><div class="foundation-block"><span>白話定義</span><p>Non-blocking socket 在目前不能前進時立即返回，而不是讓整個 worker 睡在 <code>read()</code> 或 <code>write()</code> 裡。EAGAIN 表示『現在沒有，之後再試』。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Client 尚未送下一段 body 時，<code>recv()</code> 回 EAGAIN；worker 去處理別的 connections。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 保存 parser/output state，等待 epoll 再次通知 readiness 後由 callback 繼續。</p></div></section></div>



<p class="chapter-question">一段response可以同時引用memory與file，NGINX如何在不複製全部資料的情況下組合並部分送出？</p>

<div class="chapter-meta"><span>難度：進階</span><span>buffer · scatter/gather · zero-copy</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解buffer是range descriptor、chain是scatter/gather計畫、sendfile/writev與shadow/flags ownership。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node active"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-35-資料結構不是考題-而是設計選擇"><span>上一站</span><strong>35. 資料結構不是考題，而是設計選擇</strong></a><div class="position-card current"><span>你在這裡</span><strong>36. Buffer、Chain 與 Zero-Copy 思維</strong></div><a class="position-card" href="#chapter-37-shared-memory-slab-atomic-與-lock"><span>下一站</span><strong>37. Shared Memory、Slab、Atomic 與 Lock</strong></a></div>

本章位於 **Part 6：藏在 NGINX 裡的 CS 核心**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

高效 proxy 不應反覆複製 response body。`ngx_buf_t` 描述 memory range 或 file range，`ngx_chain_t` 把多段資料串起來；output layer 可用 writev 聚合 memory buffers、用 sendfile 傳 file region。

Use case 是一個 response 同時含 header memory、file body 與 filter 產生的 chunks。Buffer 是 view/cursor，不一定擁有底層 bytes；這讓切片與轉送便宜，也提高 ownership 難度。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>高效 proxy 不應反覆複製 response body。<code>ngx_buf_t</code> 描述 memory range 或 file range，<code>ngx_chain_t</code> 把多段資料串起來；output layer 可用 writev 聚合 memory buffers、用 sendfile 傳 file region。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是一個 response 同時含 header memory、file body 與 filter 產生的 chunks。Buffer 是 view/cursor，不一定擁有底層 bytes；這讓切片與轉送便宜，也提高 ownership 難度。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Scatter/gather byte representation」這個責任邊界；接收 memory/file regions + semantic flags，交付 可逐段消費與交給下一 filter 的 chain。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 底層 storage owner + buffer cursors + chain links 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 底層先釋放、cursor 錯誤、flags 丟失、shadow buffer 重複回收。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Scatter/gather byte representation</p></div><div class="contract-card"><span>接收什麼</span><p>memory/file regions + semantic flags</p></div><div class="contract-card"><span>產生什麼</span><p>可逐段消費與交給下一 filter 的 chain</p></div><div class="contract-card"><span>狀態由誰保存</span><p>底層 storage owner + buffer cursors + chain links</p></div><div class="contract-card"><span>主要失敗出口</span><p>底層先釋放、cursor 錯誤、flags 丟失、shadow buffer 重複回收</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>producer 建立 memory/file buffer views</p></div><div class="flow-step"><span>2</span><p>chain links 表示輸出順序</p></div><div class="flow-step"><span>3</span><p>filter 讀取 pos/last 或 file_pos/file_last</p></div><div class="flow-step"><span>4</span><p>必要時建立 shadow/copy view 而非複製 bytes</p></div><div class="flow-step"><span>5</span><p>output chain 合併相鄰/相容區段</p></div><div class="flow-step"><span>6</span><p>writev/sendfile 嘗試傳輸</p></div><div class="flow-step"><span>7</span><p>partial send 後只移動 cursor</p></div><div class="flow-step"><span>8</span><p>完全消費後回收 chain/buffer</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
chain
  ├─ buf A: memory [pos,last)  "HTTP/1.1 ..."
  ├─ buf B: file   [file_pos,file_last) static.bin
  └─ buf C: memory [pos,last)  "\r\n"

writev(memory ranges) / sendfile(file range)
partial write → advance only sent ranges → keep remaining chain
```

## 從零建立心智模型

`ngx_buf_t` 不擁有固定類型的byte array；它描述memory range、file range或控制訊號。`pos/last` 是目前可送memory區間，`file_pos/file_last`是file區間，start/end則是可重用storage邊界。

`ngx_chain_t` 將buffers串成輸出計畫。Output chain可合併相鄰memory做writev，或用sendfile直接從page cache到socket路徑，並在partial send後更新各range。

Zero-copy是程度而不是絕對。TLS、gzip、filter transformation、unaligned boundary與platform可能需要copy；真正目標是避免不必要copy並保持ownership正確。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

每個 filter 都複製 bytes 會增加 memory bandwidth 與 allocation。Python `memoryview` 展示 buffer 作為底層資料的 view；移動 cursor 即可表示 partial consumption。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
data = bytearray(b"HTTP header|response body")
header = memoryview(data)[:11]
body = memoryview(data)[12:]

chain = [
    {"view": header, "sent": 0},
    {"view": body, "sent": 0},
]

def consume(buffer, amount):
    start = buffer["sent"]
    end = min(len(buffer["view"]), start + amount)
    piece = bytes(buffer["view"][start:end])
    buffer["sent"] = end
    return piece

print(consume(chain[0], 5))
print(consume(chain[0], 99))
print(bytes(chain[1]))
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>memoryview</code></td><td><code>ngx_buf_t</code> 對 memory range 的 view</td></tr><tr><td>chain list</td><td><code>ngx_chain_t</code></td></tr><tr><td><code>sent</code> cursor</td><td><code>b-&gt;pos</code>/<code>b-&gt;file_pos</code></td></tr><tr><td>same underlying data</td><td>shadow/sliced buffers 避免複製</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/ngx_output_chain.c`，官方 `release-1.31.5` 第 42–89 行

```c
ngx_output_chain(ngx_output_chain_ctx_t *ctx, ngx_chain_t *in)
{
    off_t         bsize;
    ngx_int_t     rc, last;
    ngx_chain_t  *cl, *out, **last_out;

    if (ctx->in == NULL && ctx->busy == NULL
#if (NGX_HAVE_FILE_AIO || NGX_THREADS)
        && !ctx->aio
#endif
       )
    {
        /*
         * the short path for the case when the ctx->in and ctx->busy chains
         * are empty, the incoming chain is empty too or has the single buf
         * that does not require the copy
         */

        if (in == NULL) {
            return ctx->output_filter(ctx->filter_ctx, in);
        }

        if (in->next == NULL
#if (NGX_SENDFILE_LIMIT)
            && !(in->buf->in_file && in->buf->file_last > NGX_SENDFILE_LIMIT)
#endif
            && ngx_output_chain_as_is(ctx, in->buf))
        {
            return ctx->output_filter(ctx->filter_ctx, in);
        }
    }

    /* add the incoming buf to the chain ctx->in */

    if (in) {
        if (ngx_output_chain_add_copy(ctx->pool, &ctx->in, in) == NGX_ERROR) {
            return NGX_ERROR;
        }
    }

    out = NULL;
    last_out = &out;
    last = NGX_NONE;

    for ( ;; ) {

#if (NGX_HAVE_FILE_AIO || NGX_THREADS)
        if (ctx->aio) {
```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Content/filter建立memory/file buffers並串成chain。</p></div><div class="source-step"><span>2</span><p><code>ngx_output_chain</code> 判斷是否可直接傳、需copy、directio或thread read。</p></div><div class="source-step"><span>3</span><p>OS-specific send chain組iovec或file segment，受limit控制。</p></div><div class="source-step"><span>4</span><p>Syscall回傳已送bytes，<code>ngx_chain_update_sent</code>推進range。</p></div><div class="source-step"><span>5</span><p>未送完chain留在busy/output，等write readiness繼續。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Memory 與 file buffers 有兩組不同 cursor。</p></div><div class="microscope-card"><span>2</span><p>Flags 決定資料能否修改、是否在 file、是否 response 結束。</p></div><div class="microscope-card"><span>3</span><p>Partial write 只前進 cursor，不能丟掉整個 node。</p></div><div class="microscope-card"><span>4</span><p>Shadow buffers 共用 storage，回收 owner 時要避免 dangling view。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- 永遠同時看 memory 與 file 兩組 cursor。
- `temporary`、`memory`、`mmap`、`in_file` 等 flags 決定可否修改與如何傳送。
- `last_buf` 是 response 結束語意，不只是最後一個 list node。
- Shadow buffer 共用底層 storage；回收條件要避免 use-after-free。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
typedef struct {
    unsigned char *pos, *last;    /* current memory range */
    off_t file_pos, file_last;    /* current file range */
    unsigned memory:1, in_file:1;
    unsigned flush:1, last_buf:1;
} buffer;

ssize_t n = send_chain(fd, chain, budget);
chain = advance_ranges_by(chain, n);
if (chain) wait_for_writable(fd);
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_buf.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_buf.h#L1) · [`src/core/ngx_buf.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_buf.c#L1) · [`src/core/ngx_output_chain.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_output_chain.c#L1) · [`src/os/unix/ngx_writev_chain.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_writev_chain.c#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Buffer flags是protocol：`temporary`表示可修改memory，`memory/mmap`通常不可覆寫，`recycled`提示backpressure，`flush/sync/last_buf`沒有bytes也有控制語意。只copy pointer不copyflags會破壞pipeline。

Shadow buffer允許不同view引用同一storage；只有最後consumer完成才能回收。這和Rust borrow、slice與reference lifetime有相同問題，只是C靠discipline。

Sendfile減少user-space copy，但如果client很慢，file pages與socket仍受backpressure；`sendfile_max_chunk`可避免單connection長時間霸占worker。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Slice/view</h3><p>buffer 描述資料區間，不必擁有或複製資料。</p></div><div class="pattern-card"><h3>Scatter/gather I/O</h3><p>多個區段一次 syscall 傳送。</p></div><div class="pattern-card"><h3>Zero-copy mindset</h3><p>減少 user-space copy，但仍尊重 framing/filter 限制。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 用靜態大檔比較writev與sendfile syscall trace。
2. 限制client速度，在多次sendfile後檢查file_pos前進。
3. 寫filter保留input buffer，驗證何時可放回free chain。
4. 開TLS比較sendfile路徑與CPU/copy變化。

## 常見誤解與失敗模式

- 把buffer當必然擁有memory的容器。
- 只更新chain pointer，不更新partial buffer range。
- 宣稱sendfile在所有TLS/filter場景都是zero-copy。

## 可以帶走的 Coding／CS 能力

- 掌握slice/range、scatter-gather與partial progress。
- 理解ownership flags與shared backing storage。
- 用syscall budget維持event-loop公平性。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

單 worker 內資料流清楚後，下一章處理多 workers 真正共享 state 時的 allocator 與同步。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. `pos/last` 和 `start/end` 有何不同？</summary>

前者是目前有效/未消費資料範圍；後者是整塊可用storage邊界。Partial write推進pos，不應改start。

</details>

<details class="qa" markdown="1">
<summary>Q2. File buffer如何不先把整檔讀進user memory？</summary>

它保存fd與file offset，OS-specific output可用sendfile；只有filter/TLS/directio條件要求時才copy/read。

</details>

<details class="qa" markdown="1">
<summary>Q3. 零長度buffer是否一定可丟棄？</summary>

不一定。Flush、sync、last_buf等控制flags即使無bytes也會改變下游行為。

</details>

<details class="qa" markdown="1">
<summary>Q4. Partial write後如何續送？</summary>

按回傳byte數跨chain逐段前進memory/file positions，完整消費的link移出，剩餘chain在下次writable繼續。

</details>

<details class="qa" markdown="1">
<summary>Q5. Shadow buffer最大風險？</summary>

多個descriptor共享storage，若其中一個過早回收或修改，其他view變成dangling/corrupt；需明確last shadow與busy ownership。

</details>

<details class="qa" markdown="1">
<summary>Q6. Sendfile為何仍需chunk limit？</summary>

單次可送大量ready file data，handler可能長時間占CPU/kernel work；限制每輪bytes讓其他connections獲得排程。

</details>

---

# 第 37 章　Shared Memory、Slab、Atomic 與 Lock

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Copy-on-write</h3><div class="foundation-block"><span>白話定義</span><p>Fork 後 parent/child 起初可共享相同 physical pages；某 process 寫入時才複製該 page，因此一般 heap 的更新不會自動同步給其他 workers。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Worker A 修改自己的 counter，worker B 不會看見新值。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>真正跨 worker state 必須使用明確 shared memory zone，而不是依賴 fork 繼承的普通變數。</p></div></section><section class="foundation-card"><h3>Shared memory</h3><div class="foundation-block"><span>白話定義</span><p>可被多個 processes 看見的同一塊記憶體。因為會同時讀寫，所以通常需要 atomic operation 或 lock。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>所有 workers 共用 rate-limit counter，不能只存在某一個 worker 的一般 heap。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 用 shared memory zones 保存 cache metadata、upstream state 與跨 worker counters。</p></div></section><section class="foundation-card"><h3>Slab allocator</h3><div class="foundation-block"><span>白話定義</span><p>在固定 shared memory 區域中，按大小類別管理小 objects 的 allocator。它不能像一般 heap 一樣向 OS 任意擴張。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>共享 cache metadata 需要從預先劃定的 zone 配置與歸還空間。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX slab 配合 shared mutex 管理 pages/slots，並要求所有 shared pointers 都位於可共同解讀的區域。</p></div></section><section class="foundation-card"><h3>Atomic operation 與 lock</h3><div class="foundation-block"><span>白話定義</span><p>Atomic operation 對單一小更新提供不可分割性；lock 則讓一段較大的 critical section 同時只由一個執行者進入。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>遞增 counter 可用 atomic；同時修改 tree 多個 links 通常需要 lock。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 依 invariant 選擇 atomic、spinlock/mutex，並盡量縮短 shared-memory critical section。</p></div></section><section class="foundation-card"><h3>fork</h3><div class="foundation-block"><span>白話定義</span><p><code>fork()</code> 建立一個新的 child process；child 一開始看見 parent 記憶體的邏輯副本，但之後各自執行。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Master 完成設定後 fork workers，讓它們繼承 listening sockets。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>這讓 workers 共用啟動結果，同時保持故障與一般 heap 更新彼此隔離。</p></div></section></div>



<p class="chapter-question">Worker彼此heap隔離時，rate limit、cache metadata與upstream state如何共享？</p>

<div class="chapter-meta"><span>難度：進階</span><span>shared memory · slab allocator · synchronization</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解mmap shared zone、slab allocator、process-shared mutex、atomic與一致性邊界。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node active"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-36-buffer-chain-與-zero-copy-思維"><span>上一站</span><strong>36. Buffer、Chain 與 Zero-Copy 思維</strong></a><div class="position-card current"><span>你在這裡</span><strong>37. Shared Memory、Slab、Atomic 與 Lock</strong></div><a class="position-card" href="#chapter-38-module-system-與可擴充架構"><span>下一站</span><strong>38. Module System 與可擴充架構</strong></a></div>

本章位於 **Part 6：藏在 NGINX 裡的 CS 核心**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

普通 heap memory 在 fork 後是 copy-on-write，不能自然讓 workers 看見彼此更新。Rate limit、upstream zone、cache metadata 等功能需要 shared memory，並在其中自行配置 object、使用 atomic/lock 維護一致性。

Use case 是所有 workers 共用一份計數器或 peer health state。Shared memory 只提供共同 bytes，不提供 allocator、type safety 或 race protection；NGINX 以 slab allocator 與 shmtx 補足。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>普通 heap memory 在 fork 後是 copy-on-write，不能自然讓 workers 看見彼此更新。Rate limit、upstream zone、cache metadata 等功能需要 shared memory，並在其中自行配置 object、使用 atomic/lock 維護一致性。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是所有 workers 共用一份計數器或 peer health state。Shared memory 只提供共同 bytes，不提供 allocator、type safety 或 race protection；NGINX 以 slab allocator 與 shmtx 補足。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Cross-process shared state」這個責任邊界；接收 named shared zone + size + init callback，交付 所有 workers 可見的 structured state。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 mmap shared region、slab pool、atomic/shmtx-protected invariants 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 race、dead process 持鎖、fragmentation、reload layout incompatibility。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Cross-process shared state</p></div><div class="contract-card"><span>接收什麼</span><p>named shared zone + size + init callback</p></div><div class="contract-card"><span>產生什麼</span><p>所有 workers 可見的 structured state</p></div><div class="contract-card"><span>狀態由誰保存</span><p>mmap shared region、slab pool、atomic/shmtx-protected invariants</p></div><div class="contract-card"><span>主要失敗出口</span><p>race、dead process 持鎖、fragmentation、reload layout incompatibility</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>config 註冊 named shared memory zone</p></div><div class="flow-step"><span>2</span><p>cycle 初始化或 reuse mapping</p></div><div class="flow-step"><span>3</span><p>zone init 建/接回 root data</p></div><div class="flow-step"><span>4</span><p>slab 在 shared region 配置 object</p></div><div class="flow-step"><span>5</span><p>讀寫前依 invariant 使用 atomic 或 shmtx</p></div><div class="flow-step"><span>6</span><p>更新 intrusive tree/queue/hash</p></div><div class="flow-step"><span>7</span><p>reload 新 workers attach compatible zone</p></div><div class="flow-step"><span>8</span><p>所有世代結束後才真正 unmap</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
worker 0 heap      worker 1 heap
     X                  X        彼此不可見
      \                /
       ┌────────────────────┐
       │ mmap shared zone   │
       │ slab pool + mutex  │
       │ rbtree/queue/data  │
       └────────────────────┘

Pointer只在所有process映射相容時才可共享；reload還要考慮schema。
```

## 從零建立心智模型

Fork後普通heap是copy-on-write，各worker修改不會互見。需要全域協調的module建立named shared memory zone；zone init callback在首次建立或reload重用時初始化資料結構。

Shared zone內常放`ngx_slab_pool_t`，用page與slot classes管理小物件。因多process同時配置/修改，需process-shared mutex或atomic。Lock保護的是invariant，不只是某一行assignment。

Atomic適合counter/flag等簡單狀態，不代表整個複合操作原子。Rbtree插入、queue移動、allocate＋publish通常仍需鎖。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

Fork 後普通 Python dict 與 C heap 都是 process-private。跨 workers 計數需要真正 shared memory 加同步；lock 的目的不是包住某行，而是保護多欄位 invariant。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
from multiprocessing import Lock, Process, Value

counter = Value("i", 0)
lock = Lock()

def add_requests(amount):
    for _ in range(amount):
        with lock:
            counter.value += 1

workers = [Process(target=add_requests, args=(10_000,)) for _ in range(2)]
for worker in workers:
    worker.start()
for worker in workers:
    worker.join()
print(counter.value)
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Value</code></td><td>mmap/shared memory zone 中的 shared field</td></tr><tr><td><code>Lock</code></td><td><code>ngx_shmtx_t</code> 或 atomic protocol</td></tr><tr><td>worker processes</td><td>多 NGINX workers</td></tr><tr><td>shared object creation</td><td>zone init callback + slab allocation</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/core/ngx_slab.c`，官方 `release-1.31.5` 第 184–231 行

```c
ngx_slab_alloc_locked(ngx_slab_pool_t *pool, size_t size)
{
    size_t            s;
    uintptr_t         p, m, mask, *bitmap;
    ngx_uint_t        i, n, slot, shift, map;
    ngx_slab_page_t  *page, *prev, *slots;

    if (size > ngx_slab_max_size) {

        ngx_log_debug1(NGX_LOG_DEBUG_ALLOC, ngx_cycle->log, 0,
                       "slab alloc: %uz", size);

        page = ngx_slab_alloc_pages(pool, (size >> ngx_pagesize_shift)
                                          + ((size % ngx_pagesize) ? 1 : 0));
        if (page) {
            p = ngx_slab_page_addr(pool, page);

        } else {
            p = 0;
        }

        goto done;
    }

    if (size > pool->min_size) {
        shift = 1;
        for (s = size - 1; s >>= 1; shift++) { /* void */ }
        slot = shift - pool->min_shift;

    } else {
        shift = pool->min_shift;
        slot = 0;
    }

    pool->stats[slot].reqs++;

    ngx_log_debug2(NGX_LOG_DEBUG_ALLOC, ngx_cycle->log, 0,
                   "slab alloc: %uz slot: %ui", size, slot);

    slots = ngx_slab_slots(pool);
    page = slots[slot].next;

    if (page->next != page) {

        if (shift < ngx_slab_exact_shift) {

            bitmap = (uintptr_t *) ngx_slab_page_addr(pool, page);

```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Config-time以name/size/tag註冊shared memory zone。</p></div><div class="source-step"><span>2</span><p>Cycle init建立或重用mmap區，呼叫module zone init callback。</p></div><div class="source-step"><span>3</span><p>Slab pool在shared bytes內管理free pages/slots。</p></div><div class="source-step"><span>4</span><p>Worker取得shared mutex後修改tree/queue/counters。</p></div><div class="source-step"><span>5</span><p>Reload以old data pointer協助保留相容狀態。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Shared zone name/size 是 reload compatibility contract。</p></div><div class="microscope-card"><span>2</span><p>Slab allocator 的 metadata 也必須在 shared mapping 內。</p></div><div class="microscope-card"><span>3</span><p>列出 lock 保護的完整 invariant，避免只鎖部分更新。</p></div><div class="microscope-card"><span>4</span><p>Process-local pointer/allocator state 不能錯放進 shared data。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- Shared zone name/size 是 reload compatibility contract。
- 不要把 process-local pointer 存進可由不同 mapping address 解讀的持久格式。
- Lock 保護的是 invariant，不是『某行 code』；先列出共同更新的結構。
- Slab fragmentation 與 lock contention 都可能成為高併發瓶頸。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/os/unix/ngx_shmem.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_shmem.c#L1) · [`src/core/ngx_slab.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_slab.c#L1) · [`src/core/ngx_shmtx.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_shmtx.c#L1) · [`src/os/unix/ngx_atomic.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/os/unix/ngx_atomic.h#L1)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Shared pointer的有效性依賴mapping。若process將同一區映在不同地址，內部絕對pointer可能失效；NGINX平台策略與reload重用需仔細處理。通用跨process格式更偏好offset。

鎖的臨界區應短，不能在持shared mutex時做DNS、disk或network I/O。Worker crash持鎖也是設計考量，shmtx實作需有owner/force unlock等機制。

False sharing會讓不同worker更新同一cache line上的counter互相失效；高頻統計可分worker sharding再聚合。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Shared-nothing by default</h3><p>只有明確需要的 state 才進 shared zone。</p></div><div class="pattern-card"><h3>Allocator inside mapped region</h3><p>pointer graph 與 metadata 都必須位於共享地址空間。</p></div><div class="pattern-card"><h3>Fine-grained synchronization policy</h3><p>atomic、mutex 或 immutable read 依 invariant 選擇。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 建立limit zone，以多worker壓測並觀察共享counter。
2. 找zone init callback，理解old data在reload時用途。
3. 在小實驗比較atomic counter與lock-protected tree update。
4. 把昂貴sleep放臨界區觀察所有worker延遲，再移除。

## 常見誤解與失敗模式

- 以為fork後global variable會自動共享。
- 用atomic更新複合tree/queue invariant。
- 持shared lock執行可能阻塞的I/O。

## 可以帶走的 Coding／CS 能力

- 理解process memory model、mmap與copy-on-write。
- 選擇atomic、mutex、sharding與eventual aggregation。
- 設計shared-memory schema與reload compatibility。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

Core primitives 之所以可被眾多功能共用，靠的是下一章的 module system 與 lifecycle hooks。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. 普通global variable為何不能跨worker共享更新？</summary>

Fork後各process有獨立virtual address space，頁面在寫入時copy-on-write；看似同地址但物理/內容分離。

</details>

<details class="qa" markdown="1">
<summary>Q2. Slab allocator解決什麼？</summary>

在固定shared zone內管理不同大小小物件，避免使用process-private malloc metadata，並能在共享鎖下配置/回收。

</details>

<details class="qa" markdown="1">
<summary>Q3. Atomic counter能否保護rbtree插入？</summary>

不能。Tree插入涉及多個pointer/color與可能旋轉，需要整體invariant原子可見；單欄位atomic不足。

</details>

<details class="qa" markdown="1">
<summary>Q4. Shared lock臨界區為何要短？</summary>

任何worker持鎖過久都阻塞其他process，將局部慢操作變成全域tail latency；I/O更可能無界。

</details>

<details class="qa" markdown="1">
<summary>Q5. Reload如何保留shared zone資料？</summary>

以name/size/tag判斷相容並把old zone data交新init callback；新generation重建config view但可沿用共享bytes。

</details>

<details class="qa" markdown="1">
<summary>Q6. 如何降低高頻counter的contention？</summary>

每worker/local shard累積後週期聚合、cache-line padding、採樣或無鎖近似；精確全域值與吞吐需取捨。

</details>

---

# 第 38 章　Module System 與可擴充架構

## 本章先備概念：先把名詞講成人話

<aside class="admonition prerequisite-note" markdown="1">
<div class="admonition-title">不需要先去查另一本文獻</div>

先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。

</aside>

<div class="foundation-grid" aria-label="本章開始前需要理解的技術名詞"><section class="foundation-card"><h3>Module system 與 extension point</h3><div class="foundation-block"><span>白話定義</span><p>Core 事先定義可插入的位置與 contract，module 再提供實作；因此新增功能不必修改主控制流。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>新 module 可註冊 directive、access handler 或 body filter。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX module descriptor、context callbacks、command table 與 indices 形成 C 語言的 plugin framework。</p></div></section><section class="foundation-card"><h3>Directive（設定指令）</h3><div class="foundation-block"><span>白話定義</span><p>設定檔中的一條命令，由名稱與參數構成，告訴某個 module 建立或修改 configuration。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p><code>listen 443 ssl;</code> 與 <code>proxy_pass http://app;</code> 都是 directives。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>每個 module 用 command table 宣告自己認識哪些 directives 及其 setter callback。</p></div></section><section class="foundation-card"><h3>Configuration context 與 merge</h3><div class="foundation-block"><span>白話定義</span><p>同一設定可能出現在全域、server 或 location；merge 是把父層預設值與子層覆寫組成最終設定。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>父 location 設 timeout 30 秒，子 location 可改成 3 秒；沒改的欄位繼承父層。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>NGINX 在 config time 建立多份 conf object，runtime request 只需選擇合併後的結果。</p></div></section><section class="foundation-card"><h3>Lifecycle hook</h3><div class="foundation-block"><span>白話定義</span><p>在啟動、configuration 完成、worker 初始化或退出等固定時機，由 framework 呼叫 module callback。</p></div><div class="foundation-block foundation-example"><span>具體例子</span><p>Module 在 worker init 建立 per-process resource，在 exit 時釋放。</p></div><div class="foundation-block foundation-role"><span>在 NGINX 中</span><p>正確 hook 讓 resource lifetime 與 process/cycle 對齊，避免 request path 臨時做昂貴初始化。</p></div></section></div>



<p class="chapter-question">一個第三方模組如何加入directive、phase handler、filter或upstream算法，而不修改core主流程？</p>

<div class="chapter-meta"><span>難度：進階</span><span>plugin architecture · module lifecycle · dependency inversion</span></div>

<aside class="admonition" markdown="1">
<div class="admonition-title">本章先得到什麼</div>

理解`ngx_module_t`、module context、command table、lifecycle hooks、ctx index與動態模組邊界。

</aside>

## 先建立 Context：你現在位於整張地圖的哪裡？

<div class="journey-map" aria-label="全書八階段地圖"><span class="journey-node"><b>1</b>先認識系統</span><span class="journey-node"><b>2</b>啟動與設定</span><span class="journey-node"><b>3</b>連線與事件</span><span class="journey-node"><b>4</b>HTTP 請求</span><span class="journey-node"><b>5</b>代理與後端</span><span class="journey-node active"><b>6</b>核心基礎設施</span><span class="journey-node"><b>7</b>親手擴充</span><span class="journey-node"><b>8</b>架構遷移</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-37-shared-memory-slab-atomic-與-lock"><span>上一站</span><strong>37. Shared Memory、Slab、Atomic 與 Lock</strong></a><div class="position-card current"><span>你在這裡</span><strong>38. Module System 與可擴充架構</strong></div><a class="position-card" href="#chapter-39-實作-hello-content-module"><span>下一站</span><strong>39. 實作 Hello Content Module</strong></a></div>

本章位於 **Part 6：藏在 NGINX 裡的 CS 核心**。先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；不要把下面的函式當成孤立知識點。

## 為什麼系統需要這個 Component？

NGINX core 不可能預先知道所有 protocol、directive、phase handler 與 filter。Module system 以 command tables、context callbacks、module type/index 與 lifecycle hooks，把擴充點固定下來，讓功能可加入而不修改主線。

Use case 是新增 HTTP module：提供 directives、建立/合併 config、註冊 phase/filter/content handler，worker 啟動時初始化。這是 C 語言中的 plugin architecture。

### Design Decision：從問題推導到實作邊界

<div class="design-decision-grid"><section class="design-decision-card"><span>外部壓力</span><p>NGINX core 不可能預先知道所有 protocol、directive、phase handler 與 filter。Module system 以 command tables、context callbacks、module type/index 與 lifecycle hooks，把擴充點固定下來，讓功能可加入而不修改主線。</p></section><section class="design-decision-card"><span>真實 use case</span><p>Use case 是新增 HTTP module：提供 directives、建立/合併 config、註冊 phase/filter/content handler，worker 啟動時初始化。這是 C 語言中的 plugin architecture。</p></section><section class="design-decision-card"><span>NGINX 的設計選擇</span><p>建立「Module/plugin lifecycle」這個責任邊界；接收 module descriptor、commands 與 callbacks，交付 被 config/runtime pipeline 可發現的功能。</p></section><section class="design-decision-card"><span>為什麼 state 放在這裡</span><p>跨函式或跨事件仍要存活的資料由 module indices、main/srv/loc conf arrays、global filter chains 保存，而不是依賴會消失的 local stack。</p></section><section class="design-decision-card"><span>這個設計付出的代價</span><p>必須明確處理 hook order、ctx index 錯誤、merge 漏失、ABI/build mismatch。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。</p></section></div>

### Component Contract

<div class="contract-grid"><div class="contract-card"><span>本章元件</span><p>Module/plugin lifecycle</p></div><div class="contract-card"><span>接收什麼</span><p>module descriptor、commands 與 callbacks</p></div><div class="contract-card"><span>產生什麼</span><p>被 config/runtime pipeline 可發現的功能</p></div><div class="contract-card"><span>狀態由誰保存</span><p>module indices、main/srv/loc conf arrays、global filter chains</p></div><div class="contract-card"><span>主要失敗出口</span><p>hook order、ctx index 錯誤、merge 漏失、ABI/build mismatch</p></div></div>

## 完整 Flow：從觸發到交付

<div class="flow-visual"><div class="flow-step"><span>1</span><p>Build system 收集 module descriptor</p></div><div class="flow-step"><span>2</span><p>preconfiguration 註冊 variables 等前置項</p></div><div class="flow-step"><span>3</span><p>create main/srv/loc conf</p></div><div class="flow-step"><span>4</span><p>parser 透過 command table dispatch directives</p></div><div class="flow-step"><span>5</span><p>merge nested conf</p></div><div class="flow-step"><span>6</span><p>postconfiguration 掛 phase/filter handlers</p></div><div class="flow-step"><span>7</span><p>process/thread init hooks 建 runtime resources</p></div><div class="flow-step"><span>8</span><p>exit hooks cleanup</p></div></div>

上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。

## 大框架圖：這個 Component 如何接入系統

```text
ngx_module_t
  ├─ type: CORE / EVENT / HTTP / STREAM ...
  ├─ ctx: type-specific lifecycle callbacks
  ├─ commands: directive table
  ├─ init_module / init_process / exit_process ...
  └─ index / ctx_index

HTTP module hooks:
preconfiguration → create conf → parse/merge → postconfiguration
request time: phase / content / variable / filter / upstream callbacks
```

## 從零建立心智模型

`ngx_module_t` 是通用module descriptor；`ctx` 依module type指向HTTP/event/core專用context。HTTP context提供pre/post configuration與main/srv/loc config create/merge callbacks。

Module index用於全域module arrays，`ctx_index`用於同type config/ctx arrays。Request取得某module loc conf，本質是以ctx_index索引 `r->loc_conf`。

擴充點很多但責任不同：directive建設定；phase處理控制流；content產生response；variable提供惰性值；filter改輸出；upstream peer callbacks改選擇。好module選最窄extension point，不攔截不必要階段。

## 先用 Python 跑一次同樣的設計

### 最直覺的寫法為什麼不夠？

每新增功能都修改 central core 會造成耦合與回歸。Plugin registry 將名稱、config parser、lifecycle 與 runtime callback 放進 descriptor，core 只依共同 contract 操作。

<aside class="admonition python-bridge" markdown="1">
<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>

這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，先預測輸出再往下讀。

</aside>

```python
MODULES = []

class Module:
    def __init__(self, name, directives, on_request):
        self.name = name
        self.directives = directives
        self.on_request = on_request

def register(module):
    MODULES.append(module)

register(Module(
    name="hello",
    directives={"hello": lambda value: {"text": value}},
    on_request=lambda request, conf: conf["text"].encode(),
))

for module in MODULES:
    if "hello" in module.directives:
        conf = module.directives["hello"]("NGINX")
        print(module.on_request({}, conf))
```

### Python 與 NGINX C 怎麼一一對回去？

<div class="mapping-table-wrap"><table class="mapping-table"><thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead><tbody><tr><td><code>Module</code> descriptor</td><td><code>ngx_module_t</code> + type-specific module context</td></tr><tr><td><code>directives</code></td><td><code>ngx_command_t[]</code></td></tr><tr><td><code>register</code></td><td>build-time module list/indices</td></tr><tr><td>lifecycle/runtime callbacks</td><td>create/merge/postconfiguration/process init/request handlers</td></tr></tbody></table></div>

這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX 會真正看到的 struct、field、callback 或 return code。

### 真實 NGINX C：不用跳出本書

`src/http/ngx_http.c`，官方 `release-1.31.5` 第 123–172 行

```c
ngx_http_block(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
{
    char                        *rv;
    ngx_uint_t                   mi, m, s;
    ngx_conf_t                   pcf;
    ngx_http_module_t           *module;
    ngx_http_conf_ctx_t         *ctx;
    ngx_http_core_loc_conf_t    *clcf;
    ngx_http_core_srv_conf_t   **cscfp;
    ngx_http_core_main_conf_t   *cmcf;

    if (*(ngx_http_conf_ctx_t **) conf) {
        return "is duplicate";
    }

    /* the main http context */

    ctx = ngx_pcalloc(cf->pool, sizeof(ngx_http_conf_ctx_t));
    if (ctx == NULL) {
        return NGX_CONF_ERROR;
    }

    *(ngx_http_conf_ctx_t **) conf = ctx;


    /* count the number of the http modules and set up their indices */

    ngx_http_max_module = ngx_count_modules(cf->cycle, NGX_HTTP_MODULE);


    /* the http main_conf context, it is the same in the all http contexts */

    ctx->main_conf = ngx_pcalloc(cf->pool,
                                 sizeof(void *) * ngx_http_max_module);
    if (ctx->main_conf == NULL) {
        return NGX_CONF_ERROR;
    }


    /*
     * the http null srv_conf context, it is used to merge
     * the server{}s' srv_conf's
     */

    ctx->srv_conf = ngx_pcalloc(cf->pool, sizeof(void *) * ngx_http_max_module);
    if (ctx->srv_conf == NULL) {
        return NGX_CONF_ERROR;
    }


```

第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；下面的 Source Microscope 會告訴你應該依什麼順序看。

## 源碼導覽：不跳出去也能理解

<aside class="admonition" markdown="1">
<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>

下面先把真正 source path 壓縮成可讀的 execution story。你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。

</aside>

<div class="source-walkthrough"><div class="source-step"><span>1</span><p>Build/static或dynamic load安排module list與index。</p></div><div class="source-step"><span>2</span><p>Cycle init呼叫core/module create config與解析commands。</p></div><div class="source-step"><span>3</span><p>HTTP block建立每HTTP module的main/srv/loc conf。</p></div><div class="source-step"><span>4</span><p>Merge後postconfiguration把handlers/filters註冊進runtime pipeline。</p></div><div class="source-step"><span>5</span><p>Worker init/exit hooks建立與釋放per-process資源。</p></div></div>

### Source Microscope：打開檔案時依序找這四件事

<div class="microscope-grid"><div class="microscope-card"><span>1</span><p>Module generic descriptor 與 HTTP-specific ctx 要一起讀。</p></div><div class="microscope-card"><span>2</span><p><code>index</code> 與 <code>ctx_index</code> 服務不同查找空間。</p></div><div class="microscope-card"><span>3</span><p>Create/merge conf 在 configuration lifecycle；request handler 在 data plane。</p></div><div class="microscope-card"><span>4</span><p>Filter 註冊靠保存 previous top pointer，形成全域 chain。</p></div></div>

### 讀真實 Source 時要盯住什麼？

- `ngx_module_t` 與 type-specific ctx 要一起讀。
- module index、ctx_index 用途不同；取 conf 的 macro 依 type/context 選擇。
- Filter module 必須保存 previous top filter 再替換，形成 chain。
- Dynamic module 仍有 binary compatibility/build options 約束，不等於任意共享 library。

### 把真實程式壓縮成最小可理解版本

<aside class="admonition" markdown="1">
<div class="admonition-title">這段不是要求背誦</div>

以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，本章的核心設計仍然完整。

</aside>

```c
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
```

### 選讀：核對官方 Source

**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）

**閱讀座標：** [`src/core/ngx_module.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_module.h#L1) · [`src/core/ngx_module.c#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/core/ngx_module.c#L1) · [`src/http/ngx_http_config.h#L1`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http_config.h#L1) · [`src/http/ngx_http.c#L186`](https://github.com/nginx/nginx/blob/release-1.31.5/src/http/ngx_http.c#L186)

這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。

## 關鍵機制拆解

Module ABI與conditional fields使binary compatibility敏感；dynamic module需匹配build signature。不能只看C symbol可載入就假設layout相容。

Hook ordering是隱含dependency。Filter top/next取決於初始化順序，phase handlers push順序也會影響執行。Module若依賴另一module的side effect，應有清楚contract或在config階段檢查。

Context allocation遵循生命週期：configuration在cycle pool，request ctx在r->pool，process-local library handle在init_process/exit_process管理，shared state在zone。

## Design Patterns 與 Implementation 巧思

<div class="pattern-grid"><div class="pattern-card"><h3>Plugin architecture</h3><p>core 定義穩定 extension points，module 注入行為。</p></div><div class="pattern-card"><h3>Dependency inversion</h3><p>高階 flow 依 callback contract，不依具體 module。</p></div><div class="pattern-card"><h3>Lifecycle hooks</h3><p>配置、程序與 request 時期分開，避免初始化混亂。</p></div></div>

Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，以及為此付出了哪些 state、indirection 或維護成本。

## 動手驗證

1. 挑一個小module，從module descriptor走到command與request handler。
2. 找module的ctx_index如何取得loc conf與request ctx。
3. 比較phase、content、filter三種註冊點。
4. 建立dynamic module，刻意用不匹配binary測試signature檢查。

## 常見誤解與失敗模式

- 把所有功能塞content handler，繞過適合的phase/filter擴充點。
- 把process-local pointer放shared zone或反之。
- 依賴未保證的module初始化順序。

## 可以帶走的 Coding／CS 能力

- 理解plugin registry、lifecycle hooks與dependency inversion。
- 選擇最小、最穩定的extension seam。
- 管理config/request/process/shared四種state scope。

## 本章收束：為什麼下一章會出現？

<aside class="admonition chapter-bridge" markdown="1">
<div class="admonition-title">把知識接回主線</div>

理解 module framework 後，Part 7 不再只讀：從最小 content module 開始親手使用這些 contract。

</aside>

## Follow-up Questions & Answers

<details class="qa" markdown="1">
<summary>Q1. `index` 和 `ctx_index` 有何差別？</summary>

Index辨認全域module位置；ctx_index是在同一module type內索引config/request ctx arrays，讓HTTP取得設定近似O(1)。

</details>

<details class="qa" markdown="1">
<summary>Q2. Postconfiguration通常做什麼？</summary>

在設定已解析/merge後註冊phase handlers、filters、variables等runtime pipeline，並可驗證跨directive條件。

</details>

<details class="qa" markdown="1">
<summary>Q3. 為何module要有init_process而不只init_module？</summary>

有些resource每worker獨立，如thread/library handle、timer或fd；master初始化後fork與每process初始化語意不同。

</details>

<details class="qa" markdown="1">
<summary>Q4. Dynamic module為何需build compatibility？</summary>

Core struct layout、feature macros、pointer size與module signature需一致，否則函式可找到但資料layout錯誤。

</details>

<details class="qa" markdown="1">
<summary>Q5. 如何選phase handler或filter？</summary>

要拒絕/授權request選phase；要生成內容選content；要轉換其他module輸出選filter。選最符合責任的seam。

</details>

<details class="qa" markdown="1">
<summary>Q6. Module state放哪裡？</summary>

固定設定放cycle config；單request可變狀態放request ctx；單worker資源放process scope；跨worker資料放shared zone並同步。

</details>

---
