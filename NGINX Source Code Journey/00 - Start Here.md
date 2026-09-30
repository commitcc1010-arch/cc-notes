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
