---
chapter: 43
title: 部署：Gunicorn、Uvicorn 與 Nginx
part: 9
---

# 第 43 章　部署：Gunicorn、Uvicorn 與 Nginx

> [!abstract] 本章地圖
> **核心問題**：一個在筆電上 `flask run` 跑得好好的程式，放到 nginx 與 gunicorn 後面就出現 502、504、worker timeout，部署時還會掉請求。每一層各負責什麼？逾時、keep-alive、header 與關機流程要怎麼互相配合？
>
> **你會學到**：
> - 說清楚 reverse proxy（nginx）與 application server（gunicorn、uvicorn）的分工，以及 sync worker 為什麼一定要放在 proxy 後面
> - 畫出 gunicorn 的 prefork 架構：arbiter、worker、心跳、`timeout`、`max_requests` 與訊號，並看懂 `WORKER TIMEOUT` 的 log
> - 依 Little's law、CPU、記憶體與資料庫連線數，估算 worker 與 thread 的數量
> - 設計一條從瀏覽器到資料庫的 timeout 鏈，遵守「請求逾時外層比內層長、閒置逾時 server 端比 client 端長」兩條規則
> - 正確設定 `X-Forwarded-*`、nginx realip 與 Werkzeug 的 `ProxyFix`，讓 Flask 看到真正的 client IP 與 https
> - 用 readiness、drain 與 SIGTERM 做出不掉請求的 graceful shutdown 與 zero-downtime deploy，並在 127.0.0.1 上實作出來
>
> **前置知識**：第 10 章（accept queue、CLOSE_WAIT、RST）、第 20 章（HTTP/1.1 keep-alive 與 status code）、第 25 章（reverse proxy、health check、X-Forwarded-For）、第 41 章（WSGI）、第 42 章（ASGI）

## 43.1 故事：每次部署都有一波 502

聲聲 Live 的 API 跑在兩台主機上：app-a（10.20.3.21:8000）與 app-b（10.20.3.22:8000），每台跑一組 gunicorn，裡面是 Flask。前面依序是 API LB（對外 203.0.113.80，VPC 內 10.20.16.5）與一台 nginx（10.20.3.11），資料庫在 data 子網的 10.20.17.15:5432。第 25 章的事故之後，nginx 的設定已經改成 least connections、開了到 gunicorn 的 keep-alive，看起來一切都上了軌道。

這個月，小晴接手 API 的部署腳本，連續三個星期四都被叫起來。第一個問題發生在每週四晚上十點的例行部署：腳本依序對兩台主機執行 `systemctl restart`，每次都有大約四十秒的 502，而且全部是 `POST`。第二個問題在晚上八點的尖峰：老師按下「匯出本月課程報表」，有時拿到 502，有時拿到 504（這是報表改成串流下載之前的事，第 41 章），gunicorn 的 log 裡夾著一行 `[CRITICAL] WORKER TIMEOUT (pid:23817)`。第三個問題最詭異：上週為了省記憶體，把 worker 從 sync 改成 gthread，之後白天離峰時段反而多了零星的 502，nginx 寫的是 `upstream prematurely closed connection while reading response header from upstream`，而 gunicorn 那邊什麼錯誤都沒有。另外 Rita 順便回報了一件小事：新版「重設密碼」信裡的連結用的是 `http` 而不是 `https`，點下去要多轉一次 301。

```text
 週四 20:00 尖峰                                    週四 22:00 部署
 ─────────────────────────────────────────────────────────────────────────────
 老師：匯出報表（要跑 45 秒）                        deploy.sh：systemctl restart（app-a，再 app-b）
   │                                                   │
   ├─ 30s：gunicorn arbiter 殺掉 worker                ├─ 舊 worker 被砍：進行中的請求斷線
   │       [CRITICAL] WORKER TIMEOUT (pid:23817)       ├─ 新 process import 程式中：port 沒人聽
   ├─ 30s：nginx proxy_read_timeout 也到期             │     connect() failed (111: Connection refused)
   └─► 老師看到 502 或 504（看誰先到）                 └─► GET 被 nginx 改送另一台，POST 直接 502

 平日 14:00 離峰（改成 gthread 之後）
 ─────────────────────────────────────────────────────────────────────────────
 nginx 重用一條閒置 3 秒的上游連線 ──► gunicorn 在第 2 秒已經關掉它
   └─► upstream prematurely closed connection ─► 502（gunicorn 沒有任何 log）
```

這張圖是阿德在白板上幫小晴整理的三個現場。上半部左邊是尖峰：報表要跑 45 秒，gunicorn 的 `timeout` 和 nginx 的 `proxy_read_timeout` 都是 30 秒，兩個計時器同時到期，誰先動手決定老師看到 502 還是 504。右邊是部署：`systemctl restart` 直接砍掉舊 process，再花幾秒啟動新的，這段期間 nginx 連過去被拒絕；GET 會被 nginx 的 `proxy_next_upstream` 改送另一台，POST 不能重試，所以 502 全是 POST。下半部是離峰的 502：gthread 開始支援 keep-alive，gunicorn 只讓閒置連線活 2 秒，nginx 卻以為可以留 60 秒，於是把請求送進一條剛被關掉的連線。

小晴看完說：「所以三個問題都不是程式的 bug？」阿德點頭：「都是層與層之間的約定沒對好。application server 怎麼管 worker、每一層等多久、誰先關閒置連線、關機時誰先停手，這些都要一起設計。」這一章就從「為什麼需要兩種伺服器」講起，一路把這三個問題拆開、在 127.0.0.1 上重現，最後給出聲聲 Live 修正後的 nginx 與 gunicorn 設定。

## 43.2 為什麼要兩種伺服器：reverse proxy 與 application server

第 41 章講過，WSGI 是 Python 程式與 web server 之間的介面：server 把 HTTP 請求翻成 `environ` 字典、呼叫 app、再把回傳的 iterable 寫回 socket。真正負責「聽 port、管 process、呼叫 app」的程式叫 **application server**（應用伺服器），例如 gunicorn（WSGI，新版也支援 ASGI）與 uvicorn（ASGI，第 42 章）。前面再放一層 nginx 這種 **reverse proxy**（反向代理，替後端接收 client 請求再轉送的伺服器，第 25 章）。很多人第一次看到這個架構會問：gunicorn 自己就會講 HTTP，為什麼還要 nginx？

答案藏在兩者的設計假設裡。gunicorn 的 sync worker 一次只處理一個請求，從讀完請求到寫完回應，這個 worker 都被佔住。如果 client 很慢，例如一支在捷運上用 4G 的手機，以每秒 50 KB 的速度上傳一張 5 MB 的作業照片，worker 就要花 100 秒「等 bytes 進來」，這段時間完全不能做別的事。九個 worker 只要遇到九個慢 client，整台主機就停擺了。nginx 則是事件驅動的設計，一個 worker process 可以同時掛著上萬條連線，每條只佔幾 KB 記憶體，最適合做「慢慢跟 client 收送 bytes」這種事。

```text
 沒有 reverse proxy：慢 client 直接佔住 worker
 手機（50 KB/s）──── 5 MB body，傳 100 秒 ────► gunicorn sync worker #3（100 秒都被卡住）

 有 nginx：buffer 吸收慢速，gunicorn 只處理「完整」的請求
 手機（50 KB/s）──── 5 MB，傳 100 秒 ────► nginx（先存進 buffer／暫存檔）
                                              │ 收完整個請求才轉送
                                              ▼ 10.20.3.11 → 10.20.3.21，同一個 VPC
                                         gunicorn worker #3：讀 5 MB 只要幾十毫秒
                                              │ 回應也是一口氣寫給 nginx
                                              ▼
                                         nginx 再慢慢把回應送回手機，worker 早就去接下一個
```

圖的上半部是沒有 proxy 的情況：慢速上傳的整整 100 秒都算在 worker 頭上。下半部是 nginx 預設的行為：`proxy_request_buffering on` 讓 nginx 先把整個請求 body 收完（放在記憶體 buffer，太大就寫暫存檔）才連到上游；`proxy_buffering on` 讓 nginx 盡快把上游的回應讀進來，再依 client 的速度慢慢送出。對 gunicorn 而言，每個請求都是「從同一個機房、以 Gbps 速度一次送到」，worker 的時間全部花在 Python 程式上。gunicorn 的官方文件也因此強烈建議把它放在 proxy 後面，尤其是使用 sync worker 的時候。

除了吸收慢速，reverse proxy 還承擔了許多「每個請求都要做、但和商業邏輯無關」的工作。下表是聲聲 Live 的分工：

| 工作 | 由誰負責 | 原因 |
|---|---|---|
| TLS 終結 | API LB（第 19 章） | 憑證集中管理；nginx 到 gunicorn 走 VPC 內的明文 HTTP |
| 慢 client 的收送、request／response buffering | nginx | 事件驅動，掛著上萬條慢連線也不貴 |
| 靜態檔、錄影檔（含 Range） | nginx（前面再加 CDN） | `sendfile` 直接從核心送檔案，不經過 Python |
| 請求大小與 header 限制（`client_max_body_size`） | nginx，gunicorn 再擋一次 | 在進入 Python 之前就拒絕異常請求 |
| client IP 解析（realip）、`X-Request-ID` | nginx | 信任邊界只在一個地方實作（43.8 節） |
| 負載分配、被動 health check、重試 | nginx（與 LB） | 第 25 章 |
| process 管理、worker 數量、逾時殺 worker | gunicorn arbiter | 43.3 節 |
| HTTP ↔ WSGI／ASGI 轉換 | gunicorn／uvicorn | 第 41、42 章 |
| 商業邏輯、驗證授權、資料庫 | Flask app | 只做 Python 才能做的事 |

這張表的精神是「越外層做越便宜、越通用的事」。nginx 用 C 寫成、一個連線只佔幾 KB；gunicorn 的每個 worker 是一個完整的 Python process，常駐記憶體動輒一兩百 MB。凡是不需要 Python 的工作，都應該在進入 gunicorn 之前完成。反過來，nginx 不懂你的商業規則，像「這個學生能不能看這支錄影」這種判斷，仍然要交給 Flask，再用 43.10 節的 `X-Accel-Redirect` 把傳檔工作交回 nginx。

> [!warning] 常見誤解
> 「uvicorn 是 async 的，不怕慢 client，所以不需要 nginx。」event loop 確實不怕慢連線，但 TLS、靜態檔、請求大小限制、client IP 的信任邊界、多台後端的負載分配，這些工作仍然需要有人做。而且 ASGI app 裡只要有一個阻塞呼叫，整個 event loop 都會停住（第 42 章）。實務上，uvicorn 同樣放在 nginx 或 LB 後面。

## 43.3 gunicorn 的 prefork 架構：arbiter 與 worker

gunicorn 採用 **prefork**（預先 fork）模型：啟動時先建立 listening socket，再用 `fork()` 複製出多個 worker process。這個模型源自 Ruby 的 Unicorn，Apache 的 prefork MPM 也是同一類。負責管理的那個 process 在 gunicorn 裡叫 **arbiter**（仲裁者），它不處理任何請求，只做三件事：維持 worker 數量、監控 worker 是否還活著、處理外部送來的訊號。

```text
                       gunicorn arbiter（pid 23800）
                  ┌──────────────────────────────────────────┐
  systemd／k8s ──►│ 訊號：TERM、INT、HUP、TTIN、TTOU、USR2…   │
   （訊號）       │ 每秒巡邏：                                │
                  │   ① 每個 worker 的心跳檔多久沒更新？      │
                  │      超過 timeout → SIGABRT（再不走就 KILL）│
                  │   ② waitpid() 回收結束的 worker           │
                  │   ③ 數量不足就 fork() 補上                 │
                  └───────┬──────────────┬──────────────┬────┘
                    fork()│        fork()│        fork()│
                          ▼              ▼              ▼
                    worker 23811   worker 23812   worker 23813 …
                    ├ 心跳檔 ◄──── 每一輪迴圈都更新時間戳記
                    └ 共用同一個 listening socket 0.0.0.0:8000（fd 繼承自 arbiter）
                              ▲
                              │ accept queue（backlog 2048，第 10 章）
                       nginx 10.20.3.11 的連線
```

從下往上讀。nginx 的連線完成三向交握後，進入 listening socket 的 accept queue（第 10 章）。這個 socket 是 arbiter 建立的，每個 worker 透過 `fork()` 繼承了同一個檔案描述符，所以所有 worker 都在同一個佇列上 `accept()`，誰先搶到誰處理。這個設計有一個重要的好處：worker 重生時，listening socket 一直由 arbiter 持有，排在佇列裡的連線不會因為某個 worker 結束而消失。多個 process 同時等待同一個 socket，新連線到來時可能把它們一起喚醒，只有一個搶得到，這叫 **thundering herd**（驚群效應）；現代核心與 gunicorn 都有緩解手段，在 worker 數十個以內通常不是問題。

中間是 arbiter 的巡邏。每個 worker 有一個暫存的**心跳檔**，worker 主迴圈每轉一圈就更新一次它的時間戳記；arbiter 定期檢查，如果某個 worker 的心跳檔超過 `timeout` 秒（預設 30 秒）沒更新，就判定它卡住，送 SIGABRT 要它退出，log 裡出現 `[CRITICAL] WORKER TIMEOUT (pid:23817)`；如果它還是不走，下一輪改送 SIGKILL。worker 結束後，arbiter 用 `waitpid()` 回收，發現數量不足就再 fork 一個，log 出現 `Booting worker with pid: 23820`。

### timeout 到底在量什麼

`timeout` 量的是「worker 多久沒回報心跳」，不是「請求花多久」，這兩者只在 sync worker 上剛好相等。sync worker 一次只處理一個請求，處理期間主迴圈停在你的 Flask view 裡，心跳自然停了，所以「請求超過 30 秒」就等於「worker 被殺」。故事裡的報表匯出就是這樣：view 跑到第 30 秒時，arbiter 把 worker 殺掉，連線隨 process 結束而關閉，nginx 讀到 EOF，記下 `upstream prematurely closed connection`，回 502。gthread 與 ASGI worker 則不同，主迴圈在另一個 thread 或 event loop 裡持續回報心跳，一個請求跑 90 秒也不會觸發 `timeout`；這時 `timeout` 只能抓到「整個 process 卡死」的情況，例如某個 C 擴充在不釋放 GIL 的狀況下卡住。

這帶出一個實務結論：**gunicorn 的 `timeout` 是保險絲，不是請求逾時**。真正的請求逾時要在 app 裡設：呼叫資料庫要有 statement timeout、呼叫其他服務要有連線與讀取逾時，整個請求還要有一個總預算。被 arbiter 殺掉的 worker 不會執行任何 `finally`，正在進行的資料庫交易由資料庫端回滾，已經送出去的外部呼叫則可能已經生效，這種「做到一半」的狀態正是 43.6 節要避免的。

### max_requests：定期重生

**`max_requests`**（預設 0，代表關閉）讓 worker 在處理指定數量的請求後自行優雅退出，由 arbiter 補上新的。它的用途是對付「慢慢長大」的問題：記憶體洩漏、快取無限增長、第三方函式庫的資源累積。`max_requests_jitter` 再給每個 worker 加上一個隨機值，避免所有 worker 同時達到上限、同時重生、同時重新暖機。例如 `max_requests=2000`、`max_requests_jitter=200`，每個 worker 會在 2000 到 2200 個請求之間的某一點重生。

> [!warning] 常見誤解
> `max_requests` 是止血帶，不是修正。第 10 章的 CLOSE_WAIT 事故中，如果當時設了 `max_requests`，每個 worker 重生時會把洩漏的 fd 一併歸還，`Too many open files` 也許就不會出現，但洩漏的程式碼仍然在，只是被藏起來了。正確做法是設定 `max_requests` 當保險，同時監控每個 worker 的 RSS 與 fd 數量，看到單調上升就去找根因。

### 訊號：和 arbiter 溝通的方式

arbiter 透過 Unix 訊號接受指令。部署工具、systemd、Kubernetes 都是用這些訊號在操作 gunicorn，下表是最常用的幾個：

| 訊號 | 對 arbiter 的意思 | 實務用途 |
|---|---|---|
| `TERM` | graceful shutdown：worker 做完手上的請求再走，最多等 `graceful_timeout`（預設 30 秒） | systemd stop、Kubernetes 刪 Pod、`docker stop` |
| `INT`、`QUIT` | 快速關閉，不等進行中的請求 | 開發時按 Ctrl-C |
| `HUP` | 重讀設定，啟動新 worker，再優雅關掉舊 worker；沒有 `preload_app` 時也會載入新版程式碼 | 不換 process 的程式更新（`systemctl reload`） |
| `TTIN`、`TTOU` | worker 數量加一、減一 | 臨時應付尖峰 |
| `USR1` | 重新開啟 log 檔 | logrotate 之後 |
| `USR2` | 啟動一個新的 arbiter（含新 worker），新舊並存 | 升級 gunicorn 本身或 Python 版本時的熱更新 |
| `WINCH` | 優雅關掉所有 worker，arbiter 保留 | 搭配 `USR2`，把流量完全交給新 arbiter |

`HUP` 與 `preload_app` 的關係要特別注意。**`preload_app`** 讓 arbiter 在 fork 之前先 import 你的 app，worker 透過 copy-on-write 共用這些記憶體分頁，啟動快、省記憶體；代價是程式碼已經載入 arbiter，`HUP` 只會重新 fork，不會讀到新版程式碼，要換版就得整個重啟。另一個陷阱是 fork 之前不能先開資料庫連線或背景 thread：多個 worker 會繼承同一條連線的 socket，訊息交錯在一起；連線池應該在 worker 啟動之後才建立（gunicorn 提供 `post_fork` 等 hook）。CPython 的參考計數會寫到物件所在的分頁，讓 copy-on-write 的共用逐漸失效，`gc.freeze()` 可以減緩一部分。

## 43.4 worker 類型：sync、gthread 與 ASGI

arbiter 只管 process，worker 內部怎麼處理請求，由 **worker class**（`-k` 或 `worker_class`）決定。選錯 worker class 是部署問題最常見的根源之一，故事裡的第三個問題，就是從 sync 換到 gthread 時，keep-alive 的行為跟著改變了。

```text
 時間 ───────────────────────────────────────────────────────────────►

 sync（1 個 process ＝ 1 個 slot）
 worker #1  [請求 A：CPU 3ms｜等資料庫 25ms｜CPU 2ms][請求 B ……]   回應後一律關閉連線
             ▲ 等資料庫的 25ms 什麼也不做

 gthread（1 個 process × 4 threads）
 worker #1  thread 1 [A：CPU｜等 DB……………｜CPU]
            thread 2    [B：CPU｜等外部 API………………………｜CPU]
            thread 3       [C：CPU｜等 DB…｜CPU]
            主迴圈：accept、管理 keep-alive 連線、回報心跳（不被請求卡住）
            ※ GIL：同一時間只有一個 thread 在跑 Python bytecode

 ASGI（uvicorn worker 或 gunicorn 內建 ASGI worker）：1 個 process ＝ 1 個 event loop
 worker #1  [A 開始]─await DB─┐ [B 開始]─await API─┐ [C]… [A 繼續][B 繼續]
            上萬個 WebSocket 掛著也沒問題；但一個阻塞呼叫會讓所有請求一起停
```

三條時間軸用同一組請求比較。**sync** worker 一個 process 一次只服務一個請求，請求裡等資料庫的 25 毫秒，CPU 完全閒著；它也不支援 keep-alive，每個回應都帶 `Connection: close`。優點是最單純：沒有 thread 安全問題，`timeout` 直接等於請求上限。**gthread** 在每個 process 裡開一個 thread pool，等 I/O 的時候其他 thread 可以接手；由於 GIL，同一時間只有一個 thread 在執行 Python，所以它提升的是「I/O 等待時的並行」，不是 CPU 算力。它支援 keep-alive，閒置連線放回主迴圈的 selector 裡等待，不佔用 thread，上限由 `worker_connections`（預設 1000）控制。

**ASGI** worker 讓一個 process 跑一個 asyncio event loop，所有請求以 coroutine 交錯執行，最適合 WebSocket、SSE 與大量長時間等待的連線（第 31、42 章）。傳統上 gunicorn 以 WSGI 為主，要跑 ASGI 得借用 uvicorn 提供的 worker class；新版 gunicorn 也內建了 ASGI worker（見本節的 2026 現況）。另外也可以完全不用 gunicorn，直接用 uvicorn 的 `--workers` 啟動多個 process。gevent 等以 greenlet 實現協作式並行的 worker 仍然存在，但需要 monkey patch 標準函式庫，和許多函式庫的相容性要自己驗證，聲聲 Live 沒有採用。

| worker class | 每個 process 的並行數 | keep-alive | `timeout` 的意義 | 適合 |
|---|---|---|---|---|
| `sync`（預設） | 1 | 不支援，回應後關閉 | 單一請求的處理時間上限 | CPU 為主、請求短、流量小的服務 |
| `gthread` | `threads` 個 | 支援，閒置連線不佔 thread | 主迴圈是否卡死 | Flask 這類 WSGI app，請求裡有 I/O 等待 |
| uvicorn worker／gunicorn 內建 ASGI | 一個 event loop，數千以上 | 支援 | event loop 是否卡死 | FastAPI、Starlette、WebSocket、SSE |
| `gevent` | 很多 greenlet | 支援 | 主迴圈是否卡死 | 舊系統；需要 monkey patch |

聲聲 Live 最後的選擇是：API（Flask，WSGI）用 gthread；即時服務 `rt`（聊天與白板，ASGI）用 uvicorn，跑在即時 gateway gw-41（10.20.1.41）與 gw-42（10.20.1.42）的 8001 port，前面是 rt 的三台 TLS 終結 nginx（10.20.2.11～.13，第 42 章）；第 33 章擴充到六台 gateway 後，每台 gateway 前面再多一層本機 nginx，經 Unix socket 轉給 uvicorn，下面的原則不變。兩者使用相同的 timeout 與 keep-alive 原則，差別只在數量估算與長連線的關機流程（第 33 章）。

```bash
# API：gthread，8 個 process × 7 個 thread（數字的來源見 43.5 節）
gunicorn -c /etc/shengsheng/gunicorn.conf.py shengsheng.wsgi:app

# 即時服務（在 gw-41 上；gw-42 相同，--host 換成 10.20.1.42）：uvicorn 直接管理 2 個 process，只信任三台 nginx 寫的 X-Forwarded-*
uvicorn rt.main:app --host 10.20.1.41 --port 8001 --workers 2 \
    --timeout-keep-alive 75 --proxy-headers --forwarded-allow-ips 10.20.2.11,10.20.2.12,10.20.2.13 \
    --timeout-graceful-shutdown 25
```

第一行把所有設定放進設定檔，43.12 節會逐行解說。第二個指令延續第 42 章的啟動方式，每個參數都對應本章的一個主題：`--workers 2` 是 process 數；`--timeout-keep-alive 75` 是閒置連線的保留時間（uvicorn 預設 5 秒），要長於前面 nginx 重用上游連線的時間（43.7 節）；`--proxy-headers` 與 `--forwarded-allow-ips` 讓 uvicorn 只相信三台 nginx 寫的 `X-Forwarded-*`（43.8 節）；`--timeout-graceful-shutdown 25` 限制關機時最多等多久，對 WebSocket 這種不會自己結束的連線特別重要（43.9 節）。

> [!note] 2026 現況
> 截至 2026 年 10 月（依 2026 年 10 月查證）：gunicorn 已進入 26.x，要求 Python 3.10 以上。24.0 版加入以 asyncio 實作的內建 ASGI worker（當時為 beta），25.1 版升為 stable，並新增控制介面 `gunicornc`；25.0 版加入 HTTP/2（beta，用於 gthread、gevent 與 ASGI worker）與 103 Early Hints，同時移除了 eventlet worker；24.1 版支援 PROXY protocol v2，並可用 CIDR 指定可信任的網段；25.3 與 26.x 加入一批 request smuggling 防護（第 20 章）。因此「gunicorn 只能跑 WSGI，要 ASGI 一定得配 uvicorn」的說法已經過時，兩種做法並存。另外，uvicorn 原本附帶的 `uvicorn.workers.UvicornWorker` 已被標為 deprecated，改由獨立套件 `uvicorn-worker` 提供，這一點本書未經網路查證，採用前請以官方文件確認。uvicorn 最新為 0.54.0，仍是 0.x 版本，支援 HTTP/1.1 與 WebSocket，不支援 HTTP/2；需要 HTTP/2 或 HTTP/3 的 ASGI server 可以評估 Hypercorn 或 Granian。內建 ASGI worker 的 worker class 名稱與參數，請以你所用版本的 gunicorn 文件為準。

## 43.5 worker 數量怎麼估

gunicorn 文件給了一個起點：`(2 × CPU 核心數) + 1` 個 worker。這個公式背後的想法是「一半的 worker 在等 I/O 時，另一半在用 CPU」，對 sync worker 是不錯的第一個猜測，但它沒有考慮你的流量、延遲與記憶體。比較可靠的方法是從需求反推，核心工具是 **Little's law**（利特爾法則）：系統中平均同時存在的請求數 L，等於到達速率 λ 乘上每個請求的平均停留時間 W，也就是 L ＝ λ × W。例如每秒 900 個請求、每個平均在 app 裡停留 30 毫秒，平均就有 27 個請求同時在處理，你至少需要 27 個 slot（一個 slot 是「能同時處理一個請求的位置」，sync 是一個 worker，gthread 是一個 thread）。

估算還要考慮三個限制。第一是 **CPU**：Python 因為 GIL，一個 process 大約只能用滿一個核心，所以 process 數接近核心數就足以吃滿 CPU，再多只是增加切換成本。第二是**記憶體**：每個 worker 是完整的 Python process，載入 Flask、ORM 與各種函式庫後常駐記憶體（RSS）常見一兩百 MB，sync worker 開到幾十個就會吃光主機記憶體。第三是**下游的連線數**：每個 slot 可能同時握著一條資料庫連線，全部主機加起來不能超過資料庫的上限。下面這段程式用聲聲 Live 的假設數字，把這四個面向一起算出來：

```python
import math

# 聲聲 Live API 的假設數字（晚上八點尖峰）
peak_rps = 900          # 全站 API 尖峰每秒請求數
hosts = 2               # app-a、app-b；要能承受「一台掛掉，另一台扛全部」
vcpu_per_host = 8
service_s = 0.030       # 平均每個請求在 app 裡停留 30 ms（第 1 章的 Flask view）
cpu_s = 0.005           # 其中真正吃 CPU 的只有 5 ms，其餘在等資料庫與其他服務
burst = 2.0             # 瞬間尖峰與延遲變長的保險係數
rss_mb = 180            # 每個 worker process 的常駐記憶體
db_max_connections = 100

per_host_rps = peak_rps / (hosts - 1)          # N+1：剩下的主機要扛全部流量
in_flight = per_host_rps * service_s           # Little's law：L = λ × W
slots = math.ceil(in_flight * burst)           # 同時要能處理的請求數
cpu_cores = per_host_rps * cpu_s               # 純 CPU 需求

print(f"每台主機（容錯時）：{per_host_rps:.0f} req/s")
print(f"平均同時在處理的請求：{per_host_rps:.0f} × {service_s}s = {in_flight:.0f}，乘上保險係數 → {slots} 個 slot")
print(f"CPU 需求：{per_host_rps:.0f} × {cpu_s}s = {cpu_cores:.1f} 核（{cpu_cores / vcpu_per_host:.0%} of {vcpu_per_host} vCPU）")

# 方案一：全用 sync worker，一個 worker 一次只處理一個請求
sync_workers = slots
print(f"sync   ：{sync_workers} workers × 1 → 記憶體 {sync_workers * rss_mb / 1024:.1f} GB")

# 方案二：gthread，process 數約等於核心數（GIL 讓一個 process 大約只用滿一核），thread 補足等待
workers = vcpu_per_host
threads = math.ceil(slots / workers)
print(f"gthread：{workers} workers × {threads} threads = {workers * threads} slots → 記憶體 {workers * rss_mb / 1024:.1f} GB")

db_conns = hosts * workers * threads           # 每個 thread 可能各握一條資料庫連線
print(f"資料庫連線上限需求：{hosts} 台 × {workers} × {threads} = {db_conns}（資料庫 max_connections={db_max_connections}）")
assert cpu_cores < vcpu_per_host * 0.7, "容錯時 CPU 仍要留餘裕"
assert db_conns > db_max_connections           # 這就是要加連線池上限或 pooler 的原因
```

```text
每台主機（容錯時）：900 req/s
平均同時在處理的請求：900 × 0.03s = 27，乘上保險係數 → 54 個 slot
CPU 需求：900 × 0.005s = 4.5 核（56% of 8 vCPU）
sync   ：54 workers × 1 → 記憶體 9.5 GB
gthread：8 workers × 7 threads = 56 slots → 記憶體 1.4 GB
資料庫連線上限需求：2 台 × 8 × 7 = 112（資料庫 max_connections=100）
```

第一行是容錯設計：兩台主機要能承受「其中一台掛掉或部署中」，所以每台都要能扛全部 900 req/s，而不是一半。第二行是 Little's law：平均 27 個請求同時在處理，再乘上 2 倍的保險係數，因為延遲在尖峰時會變長（資料庫變慢時 W 變大，L 跟著變大），流量也不是均勻到達。第三行確認 CPU 足夠：每個請求只用 5 毫秒 CPU，900 req/s 需要 4.5 個核心，8 vCPU 的主機在容錯時約 56%，還有餘裕。

第四、五行是兩個方案的對比。全用 sync worker 要開 54 個 process，記憶體 9.5 GB；gthread 用 8 個 process（等於核心數）各 7 個 thread，提供 56 個 slot，記憶體只要 1.4 GB。這就是故事裡改用 gthread 的原因：這個 API 大部分時間在等資料庫，thread 比 process 便宜得多。最後一行是最容易被忽略的限制：兩台主機總共 112 個 slot，若每個 thread 都各自握一條資料庫連線，就超過 PostgreSQL 預設的 `max_connections` 100。解法是讓每個 worker 的連線池上限小於 thread 數（等待連線本身也是一種排隊），或在中間加一層連線 pooler，並把這個數字寫進容量規劃。

> [!tip] 數字要回頭驗證
> 估算只是起點。上線後看三個指標：worker 的忙碌比例（gunicorn 的 statsd 指標或 access log 的並行數）、accept queue 的長度（`ss -ltn` 的 Recv-Q，第 10 章）、以及 p99 延遲。Recv-Q 經常不是 0，代表 slot 不夠或請求變慢了；CPU 已經滿載時，加 worker 只會讓每個請求都更慢。

## 43.6 timeout 鏈：外層要比內層長

一個請求從瀏覽器到資料庫，要經過六、七層，每一層都有自己的計時器，而且每一層都只知道自己的那一個。**timeout 鏈**指的就是這一串計時器合起來的行為：哪一層先放棄，決定了使用者看到什麼錯誤、哪一層的 log 有紀錄、以及放棄之後裡面還有多少工作在白做。故事裡的報表匯出同時撞上兩個 30 秒，就是這條鏈沒有設計過的結果。

```text
            外層：等得比較久，只當最後的保險                內層：先放棄，回有意義的錯誤
 ◄──────────────────────────────────────────────────────────────────────────────────────►
 瀏覽器        CDN          API LB        nginx           gunicorn        Flask app       PostgreSQL
 fetch 90s    回源 75s     idle 60s      proxy_read 35s  timeout 30s     預算 10s        statement 5s
   │────────────►│────────────►│────────────►│─────────────►│──────────────►│──────────────►│
   │             │             │             │              │（保險絲：      │ 每個下游呼叫  │ 查詢超過 5s
   │             │             │             │              │ 殺卡死的 worker）│ 用剩餘預算    │ 由 DB 取消
   │◄────────────────────────── 503 + 錯誤說明（約 5 秒，在 app 這一層產生）─────────────────│
```

由右往左讀。最內層的 PostgreSQL 用 `statement_timeout` 5 秒限制單一查詢，超過就由資料庫自己取消，app 會拿到一個明確的例外。Flask app 對整個請求有 10 秒的預算，呼叫外部服務時用「剩餘預算」當讀取逾時。於是一個卡住的慢查詢，會在第 5 秒變成 app 自己產生的 503，附上錯誤說明與 `x-request-id`，log 寫在最了解狀況的那一層。往外每一層的逾時都比內一層長一些：gunicorn 30 秒只用來殺真的卡死的 worker，nginx 35 秒、LB 60 秒、CDN 75 秒、瀏覽器 90 秒，正常情況下它們都不會觸發。

為什麼一定是「外層比內層長」？反過來想就知道。如果 nginx 30 秒、gunicorn 120 秒，慢請求在第 30 秒被 nginx 放棄，使用者看到 504，但 gunicorn 的 worker 完全不知道，繼續把這個沒人等的請求做完，資料庫查詢也繼續跑；使用者這時多半會按重新整理，於是又多一個同樣的慢請求。在負載升高的時候，這種「外層先放棄、內層白做、使用者重試」的循環會把系統推向崩潰。內層先放棄則剛好相反：資源在第一時間被釋放，錯誤訊息最精確，外層收到的是一個正常的 HTTP 回應，不會觸發重試或把後端標記成失敗。

兩層的逾時**一樣長**也不行。故事裡 gunicorn 與 nginx 都是 30 秒，兩個計時器幾乎同時到期：如果 arbiter 先殺 worker，nginx 讀到 EOF 回 502；如果 nginx 先放棄，回 504，接著 worker 還是會被殺。同一個問題時而 502、時而 504，值班的人很容易以為是兩個不同的問題。所以相鄰兩層之間要留下明確的差距，至少幾秒，讓順序永遠確定。

| 層 | 設定 | 事故前 | 修正後 | 到期時使用者看到 |
|---|---|---|---|---|
| 瀏覽器 | 前端 `fetch` 的 AbortController | 未設定 | 90 秒 | 前端顯示「逾時，請重試」 |
| CDN | 回源讀取逾時（依供應商） | 60 秒 | 75 秒 | CDN 產生的 504 |
| API LB | idle timeout | 60 秒 | 60 秒 | LB 產生的 504；nginx 記 499 |
| nginx | `proxy_read_timeout` | 30 秒 | 35 秒 | 504，`upstream timed out` |
| gunicorn | `timeout`（sync 才等於請求上限） | 30 秒 | 30 秒 | 502，`WORKER TIMEOUT` |
| Flask app | 每個請求的總預算 | 無 | 10 秒 | app 產生的 503，附錯誤說明 |
| PostgreSQL | `statement_timeout` | 無 | 5 秒 | app 收到例外，轉成 503 |

表中有兩個細節要說明。第一，nginx 的 `proxy_read_timeout` 量的是「兩次成功讀取之間」的間隔，不是整個回應的總時間；上游每 10 秒送一點資料，回應就能無限期地串流下去，這正是 SSE 能穿過 nginx 的原因（第 31 章）。第二，**499** 是 nginx 自訂的狀態碼，意思是「client 在我回應之前先關閉了連線」；如果 LB 的逾時比 nginx 短，nginx 的 access log 會出現大量 499，這是「外層比內層短」最明顯的指紋。

重試會讓這條鏈更複雜。第 25 章的 nginx 設定有 `proxy_next_upstream error timeout`：一個 GET 在 35 秒讀取逾時後會被改送另一台，再等 35 秒，總共 70 秒，已經超過外面 LB 的 60 秒。所以有重試的那一層，它對外的總時間是「每次逾時 × 嘗試次數」，外層要能容納這個總和；或者像聲聲 Live 最後的做法，只對連線錯誤重試（`proxy_next_upstream error`），讀取逾時就不重試，因為讀取逾時的請求很可能已經在後端執行了一大半。

最後，報表匯出這種本來就要跑 45 秒的工作，不應該靠把整條鏈拉長來解決。阿德的建議是把它改成背景工作：`POST /reports` 立刻回 `202 Accepted` 與一個工作編號，前端每隔幾秒查詢進度，完成後再下載檔案。HTTP 請求只負責「交代工作」與「取回結果」，每一個都是短請求，timeout 鏈對所有 API 都可以維持同一套設定。43.11 節的實驗二會用模擬時鐘把這幾種設定跑一次，看誰先放棄、誰在白做。

## 43.7 keep-alive：讓 server 端最後關

timeout 鏈管的是「一個請求最多等多久」，keep-alive 管的則是「兩個請求之間，閒置的連線要留多久」。第 20 章講過，HTTP/1.1 預設保持連線，下一個請求可以省掉 TCP 交握；第 10 章則講過閒置連線的風險：對方可能已經關閉，你卻還在池子裡留著它。每一段連線都有兩端：**重用連線的一方**（client 端，例如 nginx 對 gunicorn 而言就是 client）決定把閒置連線留多久，**接受連線的一方**（server 端）也有自己的閒置上限，到期就主動關閉。

```text
 nginx（client 端，閒置上限 60s）                       gunicorn gthread（server 端，keep-alive 2s）
   │──── 請求 1 ───────────────────────────────────────────►│
   │◄─── 200 OK（Connection 保持）──────────────────────────│
   │          （連線放回 nginx 的 upstream keepalive 池）     │
   │                                                        │ 閒置 2 秒到期
   │◄─── FIN ───────────────────────────────────────────────│ gunicorn 關閉連線
   │     （nginx 的 worker 還沒處理到這個 FIN）              │
   │ 第 3 秒：請求 2 到來，nginx 從池子拿出這條連線            │
   │──── 請求 2 ───────────────────────────────────────────►│ 已經關閉，核心回 RST
   │◄─── EOF 或 RST ────────────────────────────────────────│
   │ upstream prematurely closed connection ／ recv() failed (104: Connection reset by peer)
   └─► 502 給 client（GET 可能被重試；POST 不會）
```

這就是故事裡離峰 502 的完整過程。改用 gthread 之前，sync worker 回應後一律關閉連線，nginx 的 upstream keepalive 形同虛設，所以這個問題從來沒出現。換成 gthread 後，gunicorn 開始保留閒置連線，但只保留 2 秒（`keepalive` 的預設值）；nginx 的 `upstream` 區塊裡 `keepalive_timeout` 預設 60 秒，它認為閒置 3 秒的連線還能用。gunicorn 在第 2 秒送出 FIN，nginx 在第 3 秒把請求送進這條已經關閉的連線，讀到 EOF 或被 RST，只好回 502。離峰時段特別容易發生，因為連線閒置的時間比較長；尖峰時連線一直在用，很少閒置超過 2 秒。

規則很簡單：**每一段連線，server 端的閒置上限都要比 client 端長**。這樣永遠是 client 端先決定不用這條連線、自己關掉，不會把請求送進一條對方已經關閉的連線。注意這條規則的方向，和 43.6 節的請求逾時剛好相反：請求逾時是「外層長、內層短」，閒置逾時是「內層（server 端）長、外層（client 端）短」。以 nginx 與 gunicorn 這一段為例，請求逾時是 nginx 35 秒大於 gunicorn 30 秒，閒置逾時卻是 gunicorn 75 秒大於 nginx 60 秒。

| 連線 | client 端（重用的一方）的閒置上限 | server 端的閒置上限 | 事故前 | 修正後 |
|---|---|---|---|---|
| 瀏覽器 ↔ API LB | 瀏覽器自行決定 | LB idle timeout 60 秒 | 符合 | 符合 |
| API LB ↔ nginx | LB idle 60 秒 | nginx `keepalive_timeout` 75 秒 | 符合（第 20 章） | 符合 |
| nginx ↔ gunicorn | nginx upstream `keepalive_timeout` 60 秒 | gunicorn `keepalive` 2 秒 | **違反** | gunicorn 改成 75 秒 |
| rt 的 nginx ↔ uvicorn（gw-41、gw-42） | nginx upstream 60 秒 | uvicorn `--timeout-keep-alive` 預設 5 秒 | 違反 | uvicorn 改成 75 秒 |
| Flask ↔ 課表服務（第 10 章） | 連線池閒置上限 | 課表服務 60 秒 | 違反（事故原因） | 連線池改成 50 秒 |

這張表把整條路徑上每一段連線都列出來，和第 10 章 CLOSE_WAIT 事故是同一種錯誤的不同位置。修正後的值都遵守同一個模式：server 端 75 秒、client 端 60 秒以下。gunicorn 的 `keepalive` 拉長到 75 秒，在 nginx 後面是安全的，因為只有 nginx 會連過來，閒置連線也不佔用 thread；但如果 gunicorn 直接面對 internet，長的 keep-alive 會讓任何人都能用大量閒置連線佔住資源，所以 gunicorn 文件建議直接對外時設在 1 到 5 秒。

即使設定方向正確，仍有一個無法完全消除的極小競態：server 端到期關閉的同一瞬間，client 端剛好送出請求。這是 HTTP/1.1 keep-alive 的本質（第 20 章），所以第二道防線是讓 nginx 對連線錯誤重試 idempotent 的請求（`proxy_next_upstream error`，nginx 預設不會對 POST 重試），第三道防線是 POST 的 idempotency key（第 24 章）。43.11 節的實驗三會實際重現「上游先關造成 502」與修正後的行為。

## 43.8 X-Forwarded-* 與 ProxyFix

放到 proxy 後面之後，Flask 看到的世界變了。TCP 的對端永遠是 nginx（10.20.3.11），所以 `request.remote_addr` 全是 10.20.3.11；TLS 在 LB 終結，nginx 到 gunicorn 是明文 HTTP，所以 `request.scheme` 是 `http`，`url_for(..., _external=True)` 產生的連結 scheme 也是 `http`，這就是 Rita 回報的重設密碼信問題。真正的資訊要靠 proxy 寫進 header 往後傳：`X-Forwarded-For`（client 位址鏈）、`X-Forwarded-Proto`（原始協定）、`X-Forwarded-Host`（原始 Host）。第 25 章已經講過它們的格式與信任邊界，這一節講聲聲 Live 實際怎麼在 nginx、gunicorn 與 Flask 三層設定。

```text
 學生 198.51.100.45 ─► CDN（出口 198.51.100.230）─► API LB 10.20.16.5 ─► nginx 10.20.3.11 ─► gunicorn ─► Flask
                         附加 XFF                    附加 XFF、           realip 從右往左
                                                     寫 X-Forwarded-Proto   跳過可信網段

 nginx 收到   XFF: 198.51.100.45, 198.51.100.230          TCP 對端: 10.20.16.5
 nginx 算出   $remote_addr = 198.51.100.45（10.20.16.5、198.51.100.230 都在信任清單內，跳過）
 nginx 送出   XFF: 198.51.100.45（覆寫成解析後的單一值）   X-Forwarded-Proto: https
 Flask 經過   ProxyFix(x_for=1, x_proto=1) ─► remote_addr = 198.51.100.45，scheme = https
```

從左往右讀。CDN 與 LB 都依慣例「附加」：把自己看到的 TCP 對端加在 `X-Forwarded-For` 的最右邊，LB 另外寫上 `X-Forwarded-Proto: https`。nginx 是聲聲 Live 自己掌控、而且所有流量必經的最後一層 proxy，所以在這裡用 realip 模組解析：信任清單是 VPC 網段 10.20.0.0/16 加上 CDN 的回源網段 198.51.100.224/27（第 25 章），從右往左跳過可信的位址，第一個不可信的就是真正的 client。解析完之後，nginx **覆寫** `X-Forwarded-For`，只送一個值給後端。到了 Flask，`ProxyFix` 只需要相信最右邊的 1 個值。

為什麼不讓 `ProxyFix` 直接數跳數？Werkzeug 的 `ProxyFix` 採用固定跳數：`x_for=3` 代表「從右邊數第 3 個值是 client」。這只在所有請求都經過完全相同的 proxy 層數時才正確。聲聲 Live 的 `www` 經過 CDN，但有人可以繞過 CDN 直接連 API LB；兩條路徑的跳數不同，固定跳數一定會在其中一條上算錯，而且算錯的那一條通常是攻擊者走的路。依網段判斷的 realip 不受路徑影響，所以把它放在 nginx，後面的層數就固定為 1。43.11 節的實驗四會用三種組合實際驗證這件事。

```python
# not-runnable
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# nginx 已經依網段解析好 client 位址並覆寫 X-Forwarded-For，所以這裡只信最右邊 1 個值；
# X-Forwarded-Proto 由 LB 寫入、nginx 原樣轉送，也是 1 層。Host 由 nginx 的 proxy_set_header Host 保留，不需要 x_host。
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0, x_port=0, x_prefix=0)
```

`ProxyFix` 會改寫 WSGI environ 裡的 `REMOTE_ADDR`、`wsgi.url_scheme` 等值，原本的值另外保存在 `environ["werkzeug.proxy_fix.orig"]`，除錯時可以拿來對照。之後 Flask 的 `request.remote_addr`、`request.scheme`、`url_for(_external=True)` 與 `request.is_secure` 就都正確了。設定的數字錯了，後果不對稱：設太小，所有人都變成同一個 proxy 的位址，限速全站共用一個額度（第 25 章的 429 事故）；設太大，就會相信 client 自己寫的值，限速與稽核 log 都能被偽造。

gunicorn 自己也會讀一部分 header。`forwarded_allow_ips`（預設只有 `127.0.0.1,::1`）列出「可以相信它送來的 `X-Forwarded-Proto` 等 header 的來源」，只有來自這些位址的請求，gunicorn 才會依 `secure_scheme_headers` 把 `wsgi.url_scheme` 設成 https。nginx 和 gunicorn 不在同一台主機時，預設值等於不相信 nginx，這就是很多人「明明設了 X-Forwarded-Proto 卻沒有作用」的原因。聲聲 Live 的設定是 `forwarded_allow_ips = "10.20.3.11"`，並且用 security group 讓 8000 port 只接受 nginx 的連線。千萬不要為了省事設成 `*`：只要有任何其他路徑能連到 8000 port，對方就能自稱是 https、自稱是任何 IP。

## 43.9 graceful shutdown 與 zero-downtime deploy

故事裡部署的 502 有兩個來源，對應關機流程的兩個缺口。第一，**進行中的請求被砍斷**：process 收到訊號就結束，正在處理的請求連線被關閉，nginx 回 502。第二，**新請求被送到正在關機的 process**：LB 與 nginx 還不知道這台要下線，照樣把請求送過來，而 listening socket 已經關了或很快就要關，連線被拒絕。**graceful shutdown**（優雅關機）要同時補上這兩個缺口，順序很重要：先讓上游停止送新請求，再停止接受新連線，最後等進行中的請求做完。

```text
 時間 ─────────────────────────────────────────────────────────────────────────►
        T0 SIGTERM      T0+2×5s（LB 判定失敗）   T0+15s              T0+15s+N        T0+40s
 app    │ /readyz 改回 503 │ 仍然正常服務          │ 停止 accept         │ 進行中的請求     │ 若還沒走，
 主機   │ 其他請求照常服務 │ （drain 期間）        │ 關閉 listening      │ 全部做完：exit 0 │ 被 SIGKILL
        │                  │                       │ socket              │                  │
 LB／   │ 繼續送（還不知道）│ 移出目標群組，         │                     │                  │
 nginx  │                  │ 不再送新請求           │                     │                  │
 使用者 │ 全部 200         │ 全部 200              │ 已經不會有新請求來  │ 全部 200         │（不應發生）
```

時間軸由左往右。T0 收到 SIGTERM 時，process 不是馬上停，而是先讓 **readiness**（就緒檢查，「我現在願意接新請求嗎」）的端點 `/readyz` 改回 503，其他請求照常服務。LB 的 health check 每 5 秒一次、連續失敗 2 次才移出（第 25 章的設定），所以最多要十秒左右它才會停止送新請求，這段等待叫 **drain**（排空）。drain 之後才關閉 listening socket，此時已經不會有新請求進來；接著等進行中的請求做完，全部做完就以狀態碼 0 結束。最右邊是最後的保險：systemd 的 `TimeoutStopSec` 或 Kubernetes 的 `terminationGracePeriodSeconds` 到期，process 會被 SIGKILL，所以這個上限必須比 drain 加上最長請求的時間還長。

readiness 要和 **liveness**（存活檢查，「我是不是卡死了、需不需要被重啟」）分開。關機中的 process 應該回報「沒有就緒」，但仍然「活著」；如果兩者共用一個端點，Kubernetes 可能在 drain 期間判定 liveness 失敗而直接重啟它，等於又回到粗暴關機。另外要知道 gunicorn 本身沒有「先回 503 再停」的階段：arbiter 收到 TERM 後就停止 accept，並讓 worker 在 `graceful_timeout` 內做完手上的請求。所以 drain 這一步要由部署流程或 app 自己完成，例如部署腳本先把主機從上游移除，或者在 Kubernetes 的 `preStop` hook 裡先等幾秒，再讓 SIGTERM 送到 gunicorn。

有幾個環境細節，決定了 SIGTERM 能不能正確送到 arbiter。在 Docker 裡，`CMD gunicorn ...` 這種 shell 寫法會讓 `/bin/sh` 成為 PID 1，它不會把 SIGTERM 轉給 gunicorn，`docker stop` 等滿預設的 10 秒後直接 SIGKILL；要用 `CMD ["gunicorn", ...]` 的 exec 寫法。在 systemd 裡，預設的 `KillMode=control-group` 會把 SIGTERM 同時送給 arbiter 與所有 worker，gunicorn 的部署文件因此建議設 `KillMode=mixed`，只把 SIGTERM 送給主 process，逾時後才對其餘 process 送 SIGKILL。Kubernetes 刪除 Pod 時，「從 Service 的 endpoints 移除」與「送出 SIGTERM」是同時開始、各自進行的，沒有 `preStop` 的等待，前幾秒仍會有新請求送到已經在關機的 Pod。

| 部署方式 | 怎麼切換 | 流量怎麼排空 | 注意事項 |
|---|---|---|---|
| rolling（逐台換） | 一次換一台，換完確認 `/readyz` 再換下一台 | 部署腳本先把主機從 nginx upstream 移除（或標成 `down` 後 `nginx -s reload`），等連線歸零 | 容量要能承受少一台（43.5 節的 N+1） |
| gunicorn `HUP` | 同一個 arbiter，換掉所有 worker | arbiter 先啟動新 worker，再優雅關掉舊的；listening socket 不中斷 | 用了 `preload_app` 就讀不到新程式碼；改不了 gunicorn 本身的版本 |
| gunicorn `USR2` ＋ `WINCH` ＋ `QUIT` | 新舊 arbiter 並存，共用 listening socket | 新 arbiter 就緒後，對舊的送 `WINCH` 停 worker，再 `QUIT` | 步驟多，通常只在升級 gunicorn 或 Python 時用 |
| Kubernetes rolling update | 新 Pod 通過 readiness 才接流量，舊 Pod 逐一終止 | `preStop` 先等幾秒，讓 endpoints 移除生效，再 SIGTERM | `terminationGracePeriodSeconds`（預設 30 秒）要大於 drain 加最長請求 |
| blue／green | 兩組完整環境，在 LB 一次切換 | 舊環境在切換後繼續服務已有連線，之後才關 | 成本加倍；資料庫 schema 變更要前後相容 |

這張表的每一列都在做同一件事：讓「停止接收新流量」發生在「停止處理」之前。聲聲 Live 的 API 是 VM 上的 systemd 服務，部署腳本採用 rolling：先在 nginx 把 app-a 標成 `down` 並 reload（nginx 的 reload 本身就是 graceful 的：新的 worker 接手新連線，舊 worker 處理完現有連線才退出），用 `ss` 確認 app-a 上已經沒有 ESTABLISHED 連線，再重啟 gunicorn，`curl /readyz` 通過後把它加回去，然後換 app-b。WebSocket 這種好幾個小時都不會結束的連線不可能「等它做完」，要主動請 client 重連（close code 1012），細節在第 33 章。

## 43.10 靜態檔案與大檔案

靜態檔案（CSS、JavaScript、圖片、字型）不需要任何 Python 邏輯，讓 gunicorn 服務它們是在浪費最貴的資源：每一次下載都佔用一個 slot，慢 client 下載一個 120 KB 的 `app.js` 也許要好幾秒。聲聲 Live 的做法分三層：建置時產生帶內容雜湊的檔名（例如 `app.3f9c.js`），nginx 直接從磁碟服務 `/static/`，前面再由 CDN 快取。檔名帶雜湊，內容一改檔名就變，所以可以放心設定 `Cache-Control: public, max-age=31536000, immutable`（第 21 章的快取策略），HTML 本身則不長期快取，靠它指向最新的檔名。

錄影檔是另一種情況：檔案很大、要支援 Range 請求讓播放器跳轉（第 21 章），而且**不是公開的**，只有買了課的學生能看。如果用 Flask 的 `send_file` 回傳，一部 500 MB 的錄影會讓一個 worker 被佔住整個下載時間。解法是 nginx 的 **`X-Accel-Redirect`**：Flask 只負責檢查權限，回應裡不放檔案內容，而是放一個 header，告訴 nginx「請改為內部服務這個路徑」。nginx 收到後丟掉上游的 body，改從一個標記為 `internal`（外部請求無法直接存取）的 location 送出檔案，Range、`sendfile`、慢 client 全部由 nginx 處理。

```python
# not-runnable
import re

from flask import Flask, Response, abort

app = Flask(__name__)
NAME = re.compile(r"lesson-\d{4}\.(mp4|m3u8|ts)")    # 只接受預期格式的檔名，避免路徑穿越


@app.get("/recordings/<name>")
def recording(name):
    if not NAME.fullmatch(name):
        abort(404)
    if not can_watch(current_student(), name):          # 權限判斷留在 Flask（函式為示意）
        abort(403)
    resp = Response(status=200)
    resp.headers["X-Accel-Redirect"] = f"/internal/recordings/{name}"   # 交給 nginx 送檔
    resp.headers["Cache-Control"] = "private, max-age=0"                # 個人化內容，CDN 不快取
    return resp
```

Flask 這邊只做兩件 Python 才做得到的事：驗證檔名格式、判斷這個學生能不能看。檔名用 `fullmatch` 嚴格限制，是因為這個值最後會變成 nginx 讀取磁碟的路徑，`..` 之類的輸入必須在這裡就擋掉。回應幾乎是空的，worker 在幾毫秒內就去處理下一個請求，接下來可能持續半小時的檔案傳送全部交給 nginx。對應的 nginx 設定在 43.12 節。

如果沒有 nginx（例如某些 PaaS 只給你一個 Python process），也有在 Python 內服務靜態檔的套件，例如 WhiteNoise，它會處理壓縮與快取 header，前面再加 CDN 也能有不錯的效果。反方向的大檔案，也就是上傳，同樣要在 nginx 先擋：`client_max_body_size`（預設 1 MB，超過回 413）設成業務上合理的上限，搭配 `client_body_timeout` 避免有人用極慢的速度佔住連線，真正的大檔案上傳則讓瀏覽器直接傳到物件儲存（用有時效的簽章網址），不經過 API。

## 43.11 動手做：prefork、timeout 鏈與優雅關機

這一節用五段程式重現故事裡的三個問題與兩個修正：prefork 架構與 worker timeout、timeout 鏈的設定比較、上游先關造成的 502、`ProxyFix` 的跳數、以及 graceful shutdown。全部只用標準函式庫，在 127.0.0.1 上用 port 0 讓系統分配埠號；所有時間都縮小成零點幾秒，註解裡寫了對應的真實數值。

### 實驗一：自己寫一個 prefork arbiter

第一段程式用 `os.fork()` 實作 gunicorn 的骨架：arbiter 建立 listening socket，fork 出兩個 worker；每個 worker 在共用的 socket 上 accept，每轉一圈就更新自己的心跳檔；arbiter 檢查心跳，超過 `TIMEOUT` 就送 SIGABRT，回收結束的 worker 並補上新的。worker 處理 `MAX_REQUESTS` 個請求後自行退出，模擬 `max_requests`。`/slow` 會讓 worker 卡住 2 秒，模擬報表匯出。

在 macOS 上用 fork 有幾件事要注意。第一，macOS 的系統框架不保證 fork 之後可以安全使用，所以 `multiprocessing` 在 macOS 上從 Python 3.8 起預設改用 `spawn`（啟動一個全新的直譯器），而不是 fork；Python 3.14 在 Linux 上的預設也從 fork 改成了 `forkserver`。`spawn` 的子行程無法直接繼承 listening socket 物件，不適合模擬 prefork。第二，從 Python 3.12 起，在已經有多個 thread 的 process 裡呼叫 `os.fork()` 會發出 DeprecationWarning，因為其他 thread 持有的鎖會以「被鎖住」的狀態複製到子行程，可能造成死結。所以這段程式刻意**完全不用 thread**：arbiter 在主 thread 裡一邊當 client 送請求、一邊在等待回應的空檔巡邏。gunicorn 本身也是在單一 thread 的 arbiter 裡 fork，它支援 Linux 與 macOS 等 Unix 系統，不支援 Windows（Windows 沒有 fork）。

```python
import os
import select
import signal
import socket
import tempfile
import time

TIMEOUT = 0.4        # 縮小版的 gunicorn --timeout（預設 30 秒）
MAX_REQUESTS = 2     # 縮小版的 --max-requests：處理這麼多個請求後，worker 自己退出
NUM_WORKERS = 2


def worker_main(listener, heartbeat, label):
    """worker：在共用的 listening socket 上 accept，每一輪迴圈都更新心跳檔。"""
    alive = True

    def on_term(*_):                       # SIGTERM：做完手上的請求就離開
        nonlocal alive
        alive = False
    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGABRT, lambda *_: os._exit(3))  # 被 arbiter 判定逾時
    handled = 0
    while alive and handled < MAX_REQUESTS:
        os.utime(heartbeat)                # 心跳：告訴 arbiter「我還在跑迴圈」
        ready, _, _ = select.select([listener], [], [], 0.05)
        if not ready:
            continue
        try:
            conn, _ = listener.accept()
        except BlockingIOError:            # 被別的 worker 搶先 accept 了（thundering herd）
            continue
        conn.setblocking(True)             # macOS 上 accept 回來的 socket 會繼承 non-blocking
        with conn:
            path = conn.recv(1024).split()[1].decode()
            if path == "/slow":
                time.sleep(2)              # 卡在請求裡：這段時間沒有任何心跳
            body = f"{label}(pid {os.getpid()}) 處理 {path}".encode()
            conn.sendall(b"HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: %d\r\n\r\n%s"
                         % (len(body), body))
        handled += 1
    os._exit(0)                            # os._exit：不要 flush 從 parent 繼承來的 stdout buffer


class Arbiter:
    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(64)
        self.listener.setblocking(False)   # 讓搶輸的 worker 拿到 BlockingIOError 而不是卡住
        self.workers, self.serial = {}, 0

    def spawn(self):
        self.serial += 1
        label = f"w{self.serial}"
        fd, path = tempfile.mkstemp()
        os.close(fd)
        pid = os.fork()                    # 子行程繼承 listening socket：所有 worker 共用同一個佇列
        if pid == 0:
            worker_main(self.listener, path, label)
        self.workers[pid] = (label, path)
        print(f"  arbiter：Booting worker {label}")

    def tick(self):
        """arbiter 的主迴圈每一輪做的事：檢查心跳、回收退出的 worker、補足數量。"""
        for pid, (label, path) in list(self.workers.items()):
            if time.time() - os.stat(path).st_mtime > TIMEOUT:
                print(f"  arbiter：WORKER TIMEOUT {label}（心跳停了超過 {TIMEOUT}s）→ SIGABRT")
                os.kill(pid, signal.SIGABRT)
                os.utime(path)             # 避免同一個 worker 在退出前被重複判定
        while self.workers:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
            label, path = self.workers.pop(pid)
            os.unlink(path)
            code = os.waitstatus_to_exitcode(status)
            reason = {0: "收到 SIGTERM，優雅退出" if self.stopping else "達到 max_requests，自行退出",
                      3: "被 arbiter 中止"}[code]
            print(f"  arbiter：{label} {reason}")
            if not self.stopping:
                self.spawn()

    stopping = False

    def stop(self):
        self.stopping = True
        for pid in self.workers:
            os.kill(pid, signal.SIGTERM)
        deadline = time.time() + 1
        while self.workers and time.time() < deadline:
            self.tick()
            time.sleep(0.02)
        self.listener.close()
        return not self.workers


def request(arbiter, path):
    arbiter.tick()                         # 送下一個請求前先巡邏一次：回收、補足 worker
    c = socket.create_connection(arbiter.listener.getsockname())
    c.sendall(f"GET {path} HTTP/1.1\r\nHost: api.shengsheng.example\r\n\r\n".encode())
    c.settimeout(0.05)
    data, deadline = b"", time.time() + 3
    while time.time() < deadline:
        try:
            chunk = c.recv(4096)
        except TimeoutError:
            arbiter.tick()                 # 等回應的同時，讓 arbiter 繼續巡邏
            continue
        if not chunk:
            break
        data += chunk
    c.close()
    return data.split(b"\r\n\r\n", 1)[1].decode() if data else None


arbiter = Arbiter()
for _ in range(NUM_WORKERS):
    arbiter.spawn()
for i in range(1, 5):
    print(f"請求 {i}：{request(arbiter, f'/classes/{i}')}")
reply = request(arbiter, "/slow")
print("請求 /slow：" + (reply or "連線被關閉、沒有回應（nginx 會記 upstream prematurely closed → 502）"))
print(f"請求 5：{request(arbiter, '/classes/5')}")
assert reply is None and arbiter.serial >= NUM_WORKERS + 2
assert arbiter.stop(), "所有 worker 都應該在 SIGTERM 後退出"
print(f"總共啟動過 {arbiter.serial} 個 worker，目前 0 個存活")
```

```text
  arbiter：Booting worker w1
  arbiter：Booting worker w2
請求 1：w1(pid 32346) 處理 /classes/1
請求 2：w1(pid 32346) 處理 /classes/2
請求 3：w2(pid 32347) 處理 /classes/3
  arbiter：w1 達到 max_requests，自行退出
  arbiter：Booting worker w3
請求 4：w2(pid 32347) 處理 /classes/4
  arbiter：w2 達到 max_requests，自行退出
  arbiter：Booting worker w4
  arbiter：WORKER TIMEOUT w3（心跳停了超過 0.4s）→ SIGABRT
請求 /slow：連線被關閉、沒有回應（nginx 會記 upstream prematurely closed → 502）
  arbiter：w3 被 arbiter 中止
  arbiter：Booting worker w5
請求 5：w4(pid 32349) 處理 /classes/5
  arbiter：w5 收到 SIGTERM，優雅退出
  arbiter：w4 收到 SIGTERM，優雅退出
總共啟動過 5 個 worker，目前 0 個存活
```

哪個 worker 接到哪個請求、pid 是多少，每次執行都不同，但事件的模式是固定的。前四個請求由 w1、w2 分擔，證明兩個 process 確實在同一個 listening socket 上競爭 accept。每個 worker 處理 2 個請求後自行退出，arbiter 在下一次巡邏時回收它並 fork 出新的 worker（w3、w4），這就是 `max_requests` 的效果；注意退出的訊息比該 worker 最後一個回應晚一步出現，因為 arbiter 是在下一輪巡邏才發現它結束了。

接著 `/slow` 被某個 worker 接走，它卡在 `time.sleep(2)` 裡，心跳停止；0.4 秒後 arbiter 印出 `WORKER TIMEOUT` 並送 SIGABRT，worker 的處理函式直接結束 process。client 這邊讀到的是 EOF：連線隨著 process 結束被核心關閉，沒有任何回應，這正是 nginx 記下 `upstream prematurely closed connection` 並回 502 的情況。arbiter 隨即補上新的 worker，下一個請求照常成功，服務沒有中斷，只是那一個請求失敗了。最後 `stop()` 對所有 worker 送 SIGTERM，它們讓迴圈自然結束後以狀態碼 0 退出。

程式裡有一行是在 macOS 上踩到的平台差異：`conn.setblocking(True)`。listening socket 設成 non-blocking，是為了讓搶輸的 worker 拿到 `BlockingIOError` 而不是卡在 accept；在 macOS（BSD 系列）上，accept 回來的新 socket 會繼承這個 non-blocking 旗標，Linux 則不會繼承。少了這一行，worker 在 macOS 上讀請求時可能立刻得到 `BlockingIOError`。另外 worker 結束時用 `os._exit()` 而不是 `sys.exit()`，避免把從 parent 繼承來、還沒 flush 的 stdout buffer 重複印出。

### 實驗二：timeout 鏈的四種設定

第二段程式不開任何 socket，而是用模擬時鐘計算：一個在資料庫卡 90 秒的慢查詢，穿過四種不同的 timeout 設定時，哪一層先放棄、使用者看到什麼、放棄之後 worker 與資料庫還白做了多久。`check_chain()` 則把「外層至少比內層長 5 秒」寫成可以放進 CI 的檢查。

```python
INF = float("inf")
# 由外而內：每一層「最多等多久」。None 代表沒設，等於無限等待
LAYERS = ["browser", "cdn", "lb", "nginx", "gunicorn", "app", "db"]


def simulate(cfg: dict, work: float):
    """一個需要 work 秒的請求穿過整條鏈：哪一層先放棄、使用者看到什麼、裡面白做了多久。"""
    t = {k: (cfg.get(k) or INF) for k in LAYERS}
    # 最內層：資料庫或 app 自己的 deadline 先到，就由 app 回一個有意義的錯誤
    inner = min(work, t["db"], t["app"])
    inner_status = 200 if inner == work else 503
    candidates = [
        (inner, "app", inner_status),
        (t["gunicorn"], "gunicorn", 502),   # worker 被 arbiter 殺掉，nginx 讀到 EOF
        (t["nginx"], "nginx", 504),         # proxy_read_timeout
        (t["lb"], "lb", 504),
        (t["cdn"], "cdn", 504),
        (t["browser"], "browser", "放棄"),
    ]
    first = min(c[0] for c in candidates)
    winners = [c for c in candidates if c[0] == first]
    when, who, status = winners[0]
    if len(winners) > 1:                     # 兩層逾時一樣長：誰先到看運氣
        status = "／".join(str(w[2]) for w in winners) + "（競態）"
        who = "+".join(w[1] for w in winners)
    # 放棄的那一層以內，還在做事的部分：worker 會做到 inner 或被 gunicorn 殺掉為止
    worker_end = min(inner, t["gunicorn"])
    wasted = max(0.0, worker_end - when)
    db_wasted = max(0.0, min(work, t["db"]) - when)  # 沒有 statement_timeout，查詢會一直跑
    return when, who, status, wasted, db_wasted


configs = {
    "事故前": dict(cdn=60, lb=60, nginx=30, gunicorn=30),
    "只拉長 nginx": dict(cdn=60, lb=60, nginx=120, gunicorn=30),
    "內長外短": dict(cdn=60, lb=60, nginx=30, gunicorn=120),
    "修正後": dict(browser=90, cdn=75, lb=60, nginx=35, gunicorn=30, app=10, db=5),
}
results = {}
runs = [(name, "慢查詢 90s", 90) for name in configs] + [("修正後", "一般請求", 0.03)]
for name, case, work in runs:
    cfg = configs[name]
    when, who, status, wasted, db_wasted = simulate(cfg, work)
    results[name, case] = (who, status)
    verb = "完成" if status == 200 else "先放棄"
    print(f"{name}｜{case}｜{who} 在 {when:g}s {verb}｜使用者看到 {status}"
          f"｜worker 白做 {wasted:g}s｜DB 白做 {db_wasted:g}s")


def check_chain(cfg, margin=5):
    """外層要比內層長：每一層至少比內一層多 margin 秒，否則列出問題。"""
    layered = [(k, cfg[k]) for k in LAYERS if cfg.get(k)]
    return [f"{outer}={a}s 不比 {inner}={b}s 長 {margin}s 以上"
            for (outer, a), (inner, b) in zip(layered, layered[1:]) if a < b + margin]


for name, cfg in configs.items():
    print(f"check_chain({name}):", check_chain(cfg) or "OK")
assert results["修正後", "慢查詢 90s"] == ("app", 503)
assert results["只拉長 nginx", "慢查詢 90s"] == ("gunicorn", 502)
assert "競態" in str(results["事故前", "慢查詢 90s"][1])
assert check_chain(configs["修正後"]) == []
```

```text
事故前｜慢查詢 90s｜gunicorn+nginx 在 30s 先放棄｜使用者看到 502／504（競態）｜worker 白做 0s｜DB 白做 60s
只拉長 nginx｜慢查詢 90s｜gunicorn 在 30s 先放棄｜使用者看到 502｜worker 白做 0s｜DB 白做 60s
內長外短｜慢查詢 90s｜nginx 在 30s 先放棄｜使用者看到 504｜worker 白做 60s｜DB 白做 60s
修正後｜慢查詢 90s｜app 在 5s 先放棄｜使用者看到 503｜worker 白做 0s｜DB 白做 0s
修正後｜一般請求｜app 在 0.03s 完成｜使用者看到 200｜worker 白做 0s｜DB 白做 0s
check_chain(事故前): ['cdn=60s 不比 lb=60s 長 5s 以上', 'nginx=30s 不比 gunicorn=30s 長 5s 以上']
check_chain(只拉長 nginx): ['cdn=60s 不比 lb=60s 長 5s 以上', 'lb=60s 不比 nginx=120s 長 5s 以上']
check_chain(內長外短): ['cdn=60s 不比 lb=60s 長 5s 以上', 'nginx=30s 不比 gunicorn=120s 長 5s 以上']
check_chain(修正後): OK
```

前四行是同一個慢查詢在四種設定下的命運。「事故前」gunicorn 與 nginx 都是 30 秒，結果是競態：502 或 504 看誰先到，而且資料庫在使用者已經看到錯誤後，還繼續跑了 60 秒，因為沒有任何一層告訴它停下來。「只拉長 nginx」是很多人的第一反應，結果使用者改看到 502，因為 gunicorn 的 30 秒還在，worker 照樣被殺。「內長外短」是把 gunicorn 拉長、nginx 不動，nginx 在 30 秒回 504，但 worker 與資料庫都白做了 60 秒，這是最危險的組合，負載越高越容易雪崩。

「修正後」的慢查詢在第 5 秒由資料庫的 `statement_timeout` 取消，app 回一個有意義的 503，沒有任何一層白做；一般的 30 毫秒請求完全不受影響。下面四行是 `check_chain()` 的結果，它抓出了所有違反規則的相鄰層，包括一個表格裡很容易漏看的問題：CDN 與 LB 都是 60 秒，兩者之間沒有差距。把這種檢查放進設定檔的 CI，比事故後再去比對六個系統的設定可靠得多。

### 實驗三：上游先關閉閒置連線造成的 502

第三段程式重現故事裡離峰的 502。假的 gunicorn 支援 keep-alive，閒置 0.2 秒就關閉連線；`Proxy` 模擬 nginx 的 upstream keepalive，重用池子裡的連線，但閒置超過 `idle_limit` 的連線會先自己關掉。實驗比較兩種設定：proxy 的閒置上限比上游長（事故前），以及比上游短（修正後）。

```python
import socket
import threading
import time

UPSTREAM_KEEPALIVE = 0.2   # 縮小版的 gunicorn --keep-alive（預設 2 秒）


def upstream_server(listener):
    """假的 gunicorn（非 sync worker）：一條連線可以處理多個請求，閒置超過 keep-alive 就關閉。"""
    def handle(conn):
        conn.settimeout(UPSTREAM_KEEPALIVE)
        with conn:
            try:
                while conn.recv(4096):
                    body = b"OK"
                    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n" + body)
            except (TimeoutError, OSError):
                pass                               # 閒置逾時：離開 with，送出 FIN
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


class Proxy:
    """縮小版 nginx 的 upstream keepalive：重用閒置連線，但閒置超過 idle_limit 就丟掉。"""
    def __init__(self, upstream, idle_limit):
        self.upstream, self.idle_limit = upstream, idle_limit
        self.pool = []                             # (socket, 放回池子的時間)
        self.opened = 0

    def _get(self):
        while self.pool:
            conn, since = self.pool.pop()
            if time.monotonic() - since < self.idle_limit:
                return conn
            conn.close()                           # 太舊了，自己先關，不冒險
        self.opened += 1
        return socket.create_connection(self.upstream, timeout=1)

    def forward(self, path):
        conn = self._get()
        conn.sendall(f"GET {path} HTTP/1.1\r\nHost: api.shengsheng.example\r\n\r\n".encode())
        try:
            data = conn.recv(4096)
        except ConnectionResetError:
            conn.close()
            return "502（recv() failed: Connection reset by peer）"
        if not data:                               # 送出成功，卻讀到 EOF
            conn.close()
            return "502（upstream prematurely closed connection）"
        self.pool.append((conn, time.monotonic()))
        return data.split(b"\r\n", 1)[0].decode().replace("HTTP/1.1 ", "")


listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen()
threading.Thread(target=upstream_server, args=(listener,), daemon=True).start()
addr = listener.getsockname()

results = {}
for label, idle_limit in [("proxy 閒置上限 1.0s > upstream 0.2s", 1.0),
                          ("proxy 閒置上限 0.1s < upstream 0.2s", 0.1)]:
    proxy = Proxy(addr, idle_limit)
    first = proxy.forward("/classes/today")
    second = proxy.forward("/classes/today")       # 立刻再來一個：重用同一條連線
    time.sleep(0.3)                                # 離峰：閒置 0.3 秒，upstream 已經關了
    third = proxy.forward("/classes/today")
    results[idle_limit] = third
    print(f"{label}")
    print(f"  第 1、2 個請求：{first}、{second}；閒置 0.3s 後第 3 個：{third}；開過 {proxy.opened} 條連線")
    for conn, _ in proxy.pool:
        conn.close()

assert results[1.0].startswith("502") and results[0.1] == "200 OK"
listener.close()
```

```text
proxy 閒置上限 1.0s > upstream 0.2s
  第 1、2 個請求：200 OK、200 OK；閒置 0.3s 後第 3 個：502（upstream prematurely closed connection）；開過 1 條連線
proxy 閒置上限 0.1s < upstream 0.2s
  第 1、2 個請求：200 OK、200 OK；閒置 0.3s 後第 3 個：200 OK；開過 2 條連線
```

第一組是事故現場。第 1、2 個請求在同一條連線上連續完成，只開了 1 條連線，keep-alive 正常運作；閒置 0.3 秒之後，上游早在第 0.2 秒就關閉了連線，proxy 卻認為閒置上限 1 秒還沒到，照樣把第 3 個請求送進去，`sendall()` 成功，`recv()` 讀到 EOF，回 502。多執行幾次，偶爾會看到 `Connection reset by peer`：請求抵達時對方的 socket 已經完全關閉，核心回 RST 而不是讓我們讀到 EOF，這兩種訊息在 nginx 的 error log 裡都會出現，成因相同。

第二組把 proxy 的閒置上限設成 0.1 秒，比上游的 0.2 秒短。閒置 0.3 秒後，proxy 在使用前就發現這條連線太舊，自己先關掉並開一條新的，所以總共開了 2 條連線，第 3 個請求正常拿到 200。代價只是偶爾多一次 TCP 交握（同一個 VPC 內不到 1 毫秒），換來的是不會有使用者看到 502。這就是 43.7 節「server 端的閒置上限要比 client 端長」的實際效果。

### 實驗四：ProxyFix 的跳數與 nginx realip

第四段程式模擬兩種請求路徑：經過 CDN 的學生（198.51.100.45），以及繞過 CDN、直接連 API LB 並自己偽造 `X-Forwarded-For: 192.0.2.66` 的攻擊者（198.51.100.99）。nginx 有兩種做法：照慣例附加 XFF，或用 realip 依網段解析後覆寫成單一值；後端再用仿 Werkzeug `ProxyFix` 的 middleware 依固定跳數取值。

```python
import ipaddress

TRUSTED = [ipaddress.ip_network(n) for n in ("10.20.0.0/16", "198.51.100.224/27")]  # VPC ＋ CDN 回源
LB, NGINX = "10.20.16.5", "10.20.3.11"


def trusted(ip):
    return any(ipaddress.ip_address(ip) in net for net in TRUSTED)


def nginx_realip(peer, xff):
    """nginx 的 set_real_ip_from + real_ip_recursive on：從右往左，跳過可信網段。"""
    chain = [p.strip() for p in xff.split(",") if p.strip()] + [peer]
    for ip in reversed(chain):
        if not trusted(ip):
            return ip
    return chain[0]


def proxy_fix(app, x_for=1, x_proto=1):
    """仿 Werkzeug ProxyFix：只相信 header 最右邊第 x_for 個值（固定跳數）。"""
    def wrapped(environ, start_response):
        values = [v.strip() for v in environ.get("HTTP_X_FORWARDED_FOR", "").split(",") if v.strip()]
        if len(values) >= x_for:
            environ["REMOTE_ADDR"] = values[-x_for]
        protos = [v.strip() for v in environ.get("HTTP_X_FORWARDED_PROTO", "").split(",") if v.strip()]
        if len(protos) >= x_proto:
            environ["wsgi.url_scheme"] = protos[-x_proto]
        return app(environ, start_response)
    return wrapped


def flask_like_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [f"{environ['REMOTE_ADDR']} {environ['wsgi.url_scheme']}".encode()]


def arrive_at_nginx(path):
    """回傳 nginx 收到的 (TCP 對端, X-Forwarded-For)。CDN 與 LB 都是「附加」。"""
    if path == "student":     # 學生 198.51.100.45 → CDN（出口 .230）→ LB → nginx
        return LB, "198.51.100.45, 198.51.100.230"
    if path == "attacker":    # 攻擊者繞過 CDN 直連 LB，自己帶了偽造的 XFF
        return LB, "192.0.2.66, 198.51.100.99"


def run(nginx_mode, x_for):
    seen = {}
    for who in ("student", "attacker"):
        peer, xff = arrive_at_nginx(who)
        if nginx_mode == "附加":                     # proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for
            to_app = f"{xff}, {peer}"
        else:                                         # realip 解析後覆寫：X-Forwarded-For $remote_addr
            to_app = nginx_realip(peer, xff)
        environ = {"REMOTE_ADDR": NGINX, "wsgi.url_scheme": "http",
                   "HTTP_X_FORWARDED_FOR": to_app, "HTTP_X_FORWARDED_PROTO": "https"}
        app = proxy_fix(flask_like_app, x_for=x_for)
        seen[who] = b"".join(app(environ, lambda *a: None)).decode()
    print(f"nginx {nginx_mode}、ProxyFix(x_for={x_for})：學生 → {seen['student']:<22} 攻擊者 → {seen['attacker']}")
    return seen


a = run("附加", 1)
b = run("附加", 3)
c = run("覆寫", 1)
assert a["student"].startswith(LB)                           # 所有人都變成 LB：限速全站共用
assert b["student"].startswith("198.51.100.45") and b["attacker"].startswith("192.0.2.66")
assert c["student"] == "198.51.100.45 https" and c["attacker"] == "198.51.100.99 https"
```

```text
nginx 附加、ProxyFix(x_for=1)：學生 → 10.20.16.5 https       攻擊者 → 10.20.16.5 https
nginx 附加、ProxyFix(x_for=3)：學生 → 198.51.100.45 https    攻擊者 → 192.0.2.66 https
nginx 覆寫、ProxyFix(x_for=1)：學生 → 198.51.100.45 https    攻擊者 → 198.51.100.99 https
```

第一行是「nginx 附加、ProxyFix 只信 1 個」：最右邊那個值永遠是 LB 的 10.20.16.5，所以每個人都變成同一個 IP，這是第 25 章 429 事故的翻版。第二行把 `x_for` 改成 3，學生的位址終於對了，但攻擊者的路徑少了 CDN 那一跳，從右邊數第 3 個剛好是攻擊者自己寫的 192.0.2.66，限速器與稽核 log 都被騙了。固定跳數只要路徑不只一種，就一定會在某條路上算錯。

第三行是聲聲 Live 採用的組合：nginx 依網段解析，對學生跳過 LB 與 CDN 出口兩個可信位址，得到 198.51.100.45；對攻擊者，198.51.100.99 不在信任清單內，解析就在那裡停下，偽造的 192.0.2.66 根本不會被看到。解析結果覆寫成單一值後，ProxyFix 只要 `x_for=1`，對兩條路徑都正確。三行的 scheme 都是 https，因為 `X-Forwarded-Proto` 由 LB 寫入；如果 Flask 沒有包 ProxyFix，這裡會是 http，也就是重設密碼信連結的成因。

### 實驗五：收到 SIGTERM 後的 graceful shutdown

最後一段程式實作 43.9 節的關機流程。`AppServer` 是一個 thread-per-connection 的小 server：`/readyz` 是 readiness 端點，`/export` 是 0.4 秒的慢請求。SIGTERM 的 signal handler 只設一個旗標，真正的流程在另一個 thread 裡依序執行：readiness 改回 503、等待 drain、停止 accept 並關閉 listening socket、等進行中的請求做完。主程式扮演 LB 與使用者，在每個階段各送一個請求。

```python
import signal
import socket
import threading
import time

DRAIN = 0.15      # 縮小版的「先等 LB 把我移出」：真實系統約 LB 偵測時間再加幾秒
GRACE = 1.0       # 縮小版的 graceful_timeout（gunicorn 預設 30 秒）


class AppServer:
    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.settimeout(0.02)       # accept 迴圈定期醒來，檢查是否該停止
        self.addr = self.listener.getsockname()
        self.ready, self.accepting = True, True
        self.inflight, self.lock = 0, threading.Lock()
        self.term = threading.Event()
        self.listener_closed = threading.Event()
        self.log = []
        threading.Thread(target=self.accept_loop, daemon=True).start()

    def accept_loop(self):
        while self.accepting:
            try:
                conn, _ = self.listener.accept()
            except TimeoutError:
                continue
            conn.settimeout(None)            # 不要繼承 listener 的 0.02 秒逾時
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()
        self.listener.close()                # 停止 accept：之後的新連線會被拒絕
        self.listener_closed.set()

    def handle(self, conn):
        with self.lock:
            self.inflight += 1
        with conn:
            path = conn.recv(1024).split()[1].decode()
            if path == "/readyz":
                status = "200 OK" if self.ready else "503 Service Unavailable"
            else:
                time.sleep(0.4 if path == "/export" else 0.01)   # /export 是一個慢請求
                status = "200 OK"
            closing = "close" if self.term.is_set() else "keep-alive"  # 關機中：叫 client 別再重用
            conn.sendall(f"HTTP/1.1 {status}\r\nConnection: {closing}\r\nContent-Length: 0\r\n\r\n".encode())
        with self.lock:
            self.inflight -= 1

    def on_sigterm(self, signum, frame):
        self.term.set()                      # signal handler 只設旗標，真正的工作交給下面的流程

    def graceful_shutdown(self):
        self.term.wait(timeout=5)
        self.ready = False                   # ① readiness 先變 503，讓 LB 把我移出
        self.log.append("收到 SIGTERM：/readyz 改回 503，但繼續服務")
        time.sleep(DRAIN)                    # ② 等 LB 真的不再送新請求過來
        self.accepting = False               # ③ 停止 accept
        self.listener_closed.wait()
        self.log.append(f"drain {DRAIN}s 結束：關閉 listening socket，等進行中的 {self.inflight} 個請求")
        deadline = time.monotonic() + GRACE  # ④ 等進行中的請求做完，最多 GRACE 秒
        while self.inflight and time.monotonic() < deadline:
            time.sleep(0.01)
        self.log.append(f"進行中的請求剩 {self.inflight} 個：process 結束")


def get(addr, path, out=None):
    try:
        with socket.create_connection(addr, timeout=2) as c:
            c.sendall(f"GET {path} HTTP/1.1\r\nHost: api.shengsheng.example\r\n\r\n".encode())
            reply = c.recv(1024).split(b"\r\n")[0].decode() or "連線被關閉（502）"
    except ConnectionRefusedError:
        reply = "ConnectionRefusedError（LB 若還在送，就是 502）"
    if out is not None:
        out.append(reply)
    return reply


server = AppServer()
signal.signal(signal.SIGTERM, server.on_sigterm)
shutdown = threading.Thread(target=server.graceful_shutdown, daemon=True)
shutdown.start()

print("1. LB 健康檢查 /readyz →", get(server.addr, "/readyz"))
export = []
slow = threading.Thread(target=get, args=(server.addr, "/export", export))
slow.start()                                 # 一個 0.4 秒的匯出請求正在進行
time.sleep(0.05)
signal.raise_signal(signal.SIGTERM)          # 部署工具送出 SIGTERM（等同 kill -TERM <pid>）
time.sleep(0.02)
print("2. SIGTERM 後的健康檢查 /readyz →", get(server.addr, "/readyz"))
print("3. LB 還沒反應過來時送進的新請求 →", get(server.addr, "/classes/today"))
server.listener_closed.wait()
print("4. listening socket 關閉後的新連線 →", get(server.addr, "/classes/today"))
slow.join()
shutdown.join()
print("5. 進行中的 /export →", export[0])
for line in server.log:
    print("   server：", line)
assert export[0].startswith("HTTP/1.1 200") and server.inflight == 0
```

```text
1. LB 健康檢查 /readyz → HTTP/1.1 200 OK
2. SIGTERM 後的健康檢查 /readyz → HTTP/1.1 503 Service Unavailable
3. LB 還沒反應過來時送進的新請求 → HTTP/1.1 200 OK
4. listening socket 關閉後的新連線 → ConnectionRefusedError（LB 若還在送，就是 502）
5. 進行中的 /export → HTTP/1.1 200 OK
   server： 收到 SIGTERM：/readyz 改回 503，但繼續服務
   server： drain 0.15s 結束：關閉 listening socket，等進行中的 1 個請求
   server： 進行中的請求剩 0 個：process 結束
```

逐行對照時間軸。第 1 行是正常狀態，健康檢查拿到 200。接著一個 0.4 秒的 `/export` 開始執行，主程式用 `signal.raise_signal()` 對自己送出 SIGTERM，效果等同部署工具執行 `kill -TERM`。第 2 行顯示 SIGTERM 之後，`/readyz` 立刻變成 503，這是給 LB 的訊號；但第 3 行同時證明 process 仍在正常服務：LB 還沒來得及反應時送進來的新請求，依然拿到 200。如果收到 SIGTERM 就立刻關閉 listening socket，這個請求就會被拒絕。

第 4 行是 drain 結束之後：listening socket 已經關閉，新的連線被核心直接拒絕（`ConnectionRefusedError`）。在真實系統裡，這時 LB 早已把這台主機移出，不會再有請求送來；如果 drain 時間比 LB 的偵測時間短，這一行就是使用者看到的 502。第 5 行是整個實驗的重點：SIGTERM 之前就開始的 `/export` 完整做完，拿到 200。最後三行是 server 自己的紀錄：drain 結束時還有 1 個進行中的請求，等它完成後 process 才結束。

程式裡有兩個細節和真實的 server 一致。第一，signal handler 只做 `self.term.set()`：Python 的 signal handler 在主 thread 的兩個 bytecode 之間執行，在裡面做會阻塞的事（例如 sleep、等待其他 thread）很容易出問題，正確做法是設旗標，讓其他流程去處理。第二，收到 SIGTERM 後的回應帶 `Connection: close`，告訴 client 不要再重用這條連線；否則 nginx 可能把下一個請求送進一條即將被關閉的 keep-alive 連線，又回到實驗三的 502。

## 43.12 在工作上怎麼用

事故檢討後，小晴和阿德把修正寫成設定檔與檢查清單。這一節先逐段解說 nginx 與 gunicorn 的設定，再依角色整理工作上的做法。

**nginx：API 的 server 區塊。** 下面是 nginx 10.20.3.11 上 `api.shengsheng.example` 的設定，延續第 25 章的 upstream，加上本章的 timeout、keep-alive、realip 與靜態檔：

```text
upstream app {
    least_conn;
    server 10.20.3.21:8000 max_fails=3 fail_timeout=10s;
    server 10.20.3.22:8000 max_fails=3 fail_timeout=10s;
    keepalive 32;                    # 每個 nginx worker 最多保留 32 條閒置的上游連線
    keepalive_timeout 60s;           # 閒置上游連線保留 60 秒，必須短於 gunicorn 的 keepalive 75
}

server {
    listen 80;
    server_name api.shengsheng.example;

    keepalive_timeout 75s;           # 對 LB 的閒置上限，長於 LB 的 idle timeout 60 秒
    client_max_body_size 10m;        # 超過回 413，不讓大 body 進入 Python
    client_body_timeout 15s;         # 兩次讀到 body 資料之間最多等 15 秒

    set_real_ip_from 10.20.0.0/16;          # VPC（LB 10.20.16.5 在這裡）
    set_real_ip_from 198.51.100.224/27;     # CDN 回源網段
    real_ip_header X-Forwarded-For;
    real_ip_recursive on;                   # 從右往左，跳過所有可信位址

    location /static/ {
        alias /srv/shengsheng/static/;
        add_header Cache-Control "public, max-age=31536000, immutable";
        access_log off;
    }

    location /internal/recordings/ {
        internal;                    # 只能由 X-Accel-Redirect 進入，外部請求一律 404
        alias /srv/recordings/;
    }

    location / {
        proxy_pass http://app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";                  # 清掉 Connection，upstream keepalive 才會生效
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;   # 覆寫成 realip 解析後的單一值
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;   # 沿用 LB 寫入的值
        proxy_set_header X-Request-ID $request_id;       # 串接 nginx 與 Flask 的 log
        proxy_connect_timeout 2s;
        proxy_send_timeout 35s;
        proxy_read_timeout 35s;      # 長於 gunicorn timeout 30，短於 LB 60
        proxy_next_upstream error;   # 只對連線錯誤改送另一台；讀取逾時不重試
        proxy_next_upstream_tries 2;
    }
}
```

從上往下逐段說明。`upstream` 區塊的 `keepalive 32` 是「每個 nginx worker process」保留的閒置連線數，不是總數；新加的 `keepalive_timeout 60s` 明確寫出預設值，讓讀設定的人一眼看出它要和 gunicorn 的 75 秒比較。`server` 區塊開頭三行處理對外的那一段：閒置 75 秒長於 LB 的 60 秒（43.7 節）、body 上限 10 MB、讀 body 的間隔上限 15 秒。

realip 的四行實作 43.8 節的信任邊界，把 `$remote_addr` 改成真正的 client；access log 與限速模組看到的也都是這個值。`/static/` 用 `alias` 對應到磁碟目錄並設定長期快取；要注意 nginx 的 `add_header` 有繼承陷阱，只要某個 location 自己寫了任何一個 `add_header`，就不會再繼承上層的 `add_header`。`/internal/recordings/` 加了 `internal`，只有 Flask 回應中的 `X-Accel-Redirect` 能把請求導進來，Range 請求由 nginx 自己處理。

最後的 `location /` 是轉送給 gunicorn 的部分。`proxy_http_version 1.1` 加上清空 `Connection`，是 upstream keepalive 生效的必要條件（第 20 章）。`X-Forwarded-For` 改用 `$remote_addr` 覆寫，取代第 25 章的 `$proxy_add_x_forwarded_for` 附加。三個 timeout 對應 timeout 鏈：連線 2 秒（同一個 VPC 內交握不到 1 毫秒，2 秒還連不上就是有問題）、送出與讀取 35 秒。`proxy_next_upstream` 從第 25 章的 `error timeout` 改成只有 `error`，理由在 43.6 節：讀取逾時重試會讓總時間超過 LB，並讓已經執行一半的請求再執行一次。

**gunicorn：設定檔。** gunicorn 的設定檔本身是一個 Python 檔，每個變數對應一個命令列參數：

```text
# /etc/shengsheng/gunicorn.conf.py（app-a、app-b 相同）
bind = "0.0.0.0:8000"               # security group 只允許 nginx 10.20.3.11 連到 8000
backlog = 2048                      # accept queue 上限（第 10 章），仍受 somaxconn 限制
worker_class = "gthread"
workers = 8                         # 等於 vCPU 數（43.5 節）
threads = 7                         # 8 × 7 = 56 個 slot
worker_connections = 1000           # 每個 worker 最多同時持有的連線（含閒置的 keep-alive）
timeout = 30                        # 保險絲：主迴圈 30 秒沒心跳就殺掉 worker
graceful_timeout = 25               # SIGTERM 後最多等進行中的請求 25 秒
keepalive = 75                      # 長於 nginx upstream keepalive_timeout 60
max_requests = 2000                 # 每個 worker 處理 2000～2200 個請求後重生
max_requests_jitter = 200
worker_tmp_dir = "/dev/shm"         # 心跳檔放記憶體檔案系統，避免磁碟 I/O 卡住心跳
forwarded_allow_ips = "10.20.3.11"  # 只相信 nginx 送來的 X-Forwarded-Proto
preload_app = False                 # 讓 HUP 能載入新版程式碼
accesslog = "-"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(L)s %({x-request-id}i)s'
```

`bind` 用 `0.0.0.0` 搭配 security group 限制來源，比綁定特定 IP 更不容易在換主機時出錯，但 security group 這一步絕不能省（43.8 節）。`workers` 與 `threads` 來自 43.5 節的估算，`worker_connections` 是 gthread 對連線數的上限，閒置的 keep-alive 連線也算在內。`timeout`、`graceful_timeout`、`keepalive` 三個值分別對應 timeout 鏈、關機流程與閒置規則：`graceful_timeout` 25 秒要比 systemd 的 `TimeoutStopSec` 短，才能在被 SIGKILL 之前自己結束。

`worker_tmp_dir` 是 gunicorn 文件特別提醒的設定：心跳檔預設放在系統暫存目錄，在某些容器環境裡它在磁碟上，磁碟 I/O 一卡，心跳就更新不了，arbiter 會誤殺正常的 worker；放到 `/dev/shm` 這種記憶體檔案系統可以避免。access log 的 `%(L)s` 是請求花費的秒數（小數），`%({x-request-id}i)s` 是 nginx 傳來的 request ID，有了這兩個欄位，就能把 nginx 的 502、504 對應到 gunicorn 這一側的同一個請求。

**SRE：systemd 與部署腳本。** systemd 的 unit 檔要配合 graceful shutdown：

```text
[Service]
ExecStart=/srv/shengsheng/venv/bin/gunicorn -c /etc/shengsheng/gunicorn.conf.py shengsheng.wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=40
Restart=on-failure
```

`ExecReload` 讓 `systemctl reload` 送 HUP，只替換 worker，不中斷 listening socket。`KillMode=mixed` 讓 stop 時只有 arbiter 收到 SIGTERM，由它依序關掉 worker；`TimeoutStopSec=40` 長於 `graceful_timeout` 25 秒加上一點餘裕。部署腳本對每台主機依序執行下面的步驟：

```bash
# 1. 從 nginx upstream 移除 app-a（設定中加上 down），reload 是 graceful 的
sudo sed -i 's/server 10.20.3.21:8000 /server 10.20.3.21:8000 down /' /etc/nginx/conf.d/api.conf
sudo nginx -t && sudo nginx -s reload
# 2. 等 app-a 上的連線歸零（在 app-a 上執行），最多等 30 秒
for i in $(seq 30); do n=$(ss -Htn state established '( sport = :8000 )' | wc -l); [ "$n" -eq 0 ] && break; sleep 1; done
# 3. 重啟並確認就緒
sudo systemctl restart shengsheng-api
curl -fsS --retry 10 --retry-delay 1 --retry-connrefused http://10.20.3.21:8000/readyz
# 4. 加回 upstream，換下一台
```

這四步就是 43.9 節 rolling 那一列的具體做法。第 2 步用 `ss` 計算 8000 port 上的 ESTABLISHED 連線，但因為 nginx 的 upstream keepalive 會在移除後由舊的 nginx worker 慢慢關閉，連線數歸零的時間大約是「最長的請求」或「舊 nginx worker 退出」兩者之中較晚的那一個。第 3 步的 `curl --retry-connrefused` 會重試直到新的 gunicorn 開始監聽並回 200，`/readyz` 應該真的檢查資料庫連線等依賴，而不是只回一個固定的 200。

**後端工程師：程式碼裡的 timeout 與關機。** 每個對外呼叫都設連線與讀取逾時，並從請求的總預算扣除已經花掉的時間；資料庫連線在建立時就設 `statement_timeout`。超過 10 秒的工作改成背景工作，API 回 202。不要在 import 階段建立資料庫連線或背景 thread（`preload_app` 會讓它們被所有 worker 共用），而是在第一次使用或 `post_fork` hook 裡建立。`/readyz` 與 `/livez` 分開實作，前者檢查依賴並在關機中回 503，後者只確認 process 能回應。

**影音工程師：即時服務的部署。** Joe 的 `rt` 服務跑 uvicorn，WebSocket 連線可能維持好幾個小時，graceful shutdown 不可能等它們自然結束。關機流程是先讓 readiness 失敗、等 LB 生效，再對每條連線送 close code 1012 請 client 重連（第 33 章），`--timeout-graceful-shutdown` 設為最後的上限。rt 主機上 nginx 轉給 uvicorn 的 `proxy_read_timeout` 要長於 WebSocket 心跳間隔，否則閒置的教室會被 nginx 當成讀取逾時切斷。

**資安工程師：檢查信任設定。** Rita 的檢查清單只有三條：gunicorn 的 8000 port 只允許 nginx 連入；`forwarded_allow_ips` 與 `ProxyFix` 的數字和實際路徑一致，而且沒有任何 `*`；nginx 的 `set_real_ip_from` 只列出自家網段與 CDN 公布的回源網段，並定期更新。每次架構變動（例如加一層 proxy、讓某個路徑繞過 CDN），這三條都要重新確認，因為跳數或信任清單一旦對不上，client IP 就能被偽造。

**判斷 502 與 504 從哪裡來。** 值班時看到 5xx，先依下面的流程分辨是哪一層、哪一種：

```text
 nginx access log 出現 5xx
   │
   ├─ 504 ── error log：upstream timed out … while reading response header
   │          └─► 上游太慢：看 gunicorn access log 同一個 x-request-id 的 %(L)s；查慢查詢
   │     ── error log：upstream timed out … while connecting to upstream
   │          └─► accept queue 滿或網路問題：上游 ss -ltn 的 Recv-Q（第 10 章）
   │
   ├─ 502 ── connect() failed (111: Connection refused)
   │          └─► 上游沒在聽：重啟中、process 掛了 → 檢查部署流程與 drain
   │     ── upstream prematurely closed connection／recv() failed (104 …)
   │          ├─ gunicorn log 同時有 WORKER TIMEOUT 或 SIGKILL ─► worker 被殺：請求太久或 OOM
   │          └─ gunicorn 沒有任何 log，且多在閒置之後 ─► keep-alive 方向反了（43.7 節）
   │     ── no live upstreams
   │          └─► 所有上游都被 max_fails 標記失敗：先救上游，再看 fail_timeout
   │
   └─ 499（不是 5xx，但常一起出現）─► client 或外層 LB 先放棄：外層逾時比 nginx 短
```

第一刀是 status code：504 代表 nginx 自己的計時器到期，502 代表上游的連線出了問題。第二刀是 error log 的訊息，每一種都對應到一個明確的成因。最關鍵的是 502 的 `upstream prematurely closed connection`：同一個訊息有兩種完全不同的原因，要用 gunicorn 這一側的 log 區分，有 `WORKER TIMEOUT` 或 SIGKILL 就是 worker 被殺，什麼都沒有就是 keep-alive 的方向反了。

## 43.13 常見錯誤與除錯

下表收錄聲聲 Live 與一般團隊在部署 Python web 服務時最常遇到的問題，每一列都可以用本章的工具在幾分鐘內確認。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 每次部署都有一波 502，集中在 POST | 重啟時進行中的請求被砍斷，或上游仍把請求送到正在關機的 process | 502 的時間點與部署時間重疊；nginx error log 有 `Connection refused` 或 `prematurely closed` | 先 drain（從 upstream 移除或 readiness 503），再 SIGTERM；`graceful_timeout`＜`TimeoutStopSec` |
| 長請求時而 502、時而 504 | gunicorn `timeout` 與 nginx `proxy_read_timeout` 一樣長，兩個計時器競爭 | 錯誤都發生在第 30 秒左右；gunicorn log 有 `WORKER TIMEOUT` | 相鄰兩層留出差距；app 內設請求預算與 `statement_timeout`；長工作改背景執行 |
| 離峰時零星 502，gunicorn 沒有任何錯誤 | nginx 的 upstream keepalive 比 gunicorn 的 `keepalive` 長，上游先關閉連線 | 錯誤多發生在閒置之後的第一個請求；tcpdump 看到 gunicorn 先送 FIN | gunicorn `keepalive` 設得比 nginx upstream `keepalive_timeout` 長；對連線錯誤重試 idempotent 請求 |
| `[ERROR] Worker (pid:…) was sent SIGKILL! Perhaps out of memory?` | worker 記憶體持續增長，被核心的 OOM killer 殺掉 | `dmesg` 有 OOM 紀錄；監控每個 worker 的 RSS 隨時間上升 | 找出洩漏；短期用 `max_requests` 加 jitter 定期重生；調整 worker 數與記憶體上限 |
| 所有請求的 client IP 都是 10.20.3.11 或 LB 的位址 | 沒有 ProxyFix，或 `x_for` 小於實際跳數 | 在 view 印出 `request.remote_addr` 與原始 `X-Forwarded-For` | nginx 用 realip 解析並覆寫，Flask 用 `ProxyFix(x_for=1)` |
| 產生的連結是 `http` 而非 `https`，或 HTTPS 轉向無限迴圈 | Flask 不知道原始協定是 https | `request.scheme` 是 `http`；`X-Forwarded-Proto` 有送但被忽略 | `ProxyFix(x_proto=1)`；或把 nginx 位址加入 gunicorn 的 `forwarded_allow_ips` |
| `docker stop` 一律等 10 秒才結束，進行中的請求被砍 | shell 形式的 `CMD` 讓 `/bin/sh` 成為 PID 1，SIGTERM 沒有轉給 gunicorn | `docker exec … ps` 看到 PID 1 是 `sh -c` | 改用 exec 形式 `CMD ["gunicorn", ...]` |
| 改了程式碼並送 HUP，跑的還是舊版 | 啟用了 `preload_app`，程式碼已經載入 arbiter | 設定中有 `preload_app = True`；worker 啟動時間沒有變化 | 換版時整個重啟，或關掉 `preload_app` |
| 容器裡 worker 經常被誤判 timeout，CPU 卻不高 | 心跳檔在磁碟上，I/O 延遲讓心跳更新被卡住 | `worker_tmp_dir` 未設定；問題與磁碟 I/O 尖峰同時發生 | `worker_tmp_dir = "/dev/shm"` |
| 加 worker 之後資料庫出現 `too many connections` | 主機數 × worker × thread 的總連線超過資料庫上限 | 資料庫的連線數監控在擴容後跳升 | 限制每個 worker 的連線池大小；加連線 pooler；容量規劃時一起計算 |

除錯時的通則和第 10 章相同：**先確認是哪一層產生的錯誤，再看那一層的 log**。502、504、499 永遠由中間那一層產生，Flask 的 log 裡可能什麼都沒有；用 `x-request-id` 把 nginx、gunicorn、Flask 的同一個請求串起來，再對照每一層的逾時設定，大部分問題在第一張表格裡就能找到答案。

## 43.14 動手練習

1. **延伸實驗一：加上 TTIN 與 TTOU**（延伸程式）。讓 arbiter 處理 SIGTTIN 與 SIGTTOU：收到 TTIN 時把目標 worker 數加一，收到 TTOU 時減一並對多出來的 worker 送 SIGTERM。用 `signal.raise_signal()` 在請求之間觸發，並印出每次巡邏後的 worker 數。
   答案要點：signal handler 只修改目標數量，實際的 fork 與 kill 放在 `tick()` 裡做，和 gunicorn 一樣；減少 worker 時要選擇送 SIGTERM（優雅）而不是 SIGKILL，正在處理請求的 worker 會先做完。驗證方式是 assert 巡邏後的存活 worker 數等於目標數。

2. **延伸實驗二：把重試算進 timeout 鏈**（延伸程式）。在 `simulate()` 中加入 nginx 的 `proxy_next_upstream` 嘗試次數 `tries`：讀取逾時後改送另一台再等一次。計算「事故前」設定在 `tries=2` 時，一個 90 秒的慢查詢讓使用者等多久、兩台主機一共白做多久，並修改 `check_chain()`，讓它用 `nginx × tries` 和外層比較。
   答案要點：nginx 這一層的總時間變成 30 × 2 ＝ 60 秒，剛好和 LB 的 60 秒相等，再次形成競態；兩台主機各有一個 worker 在做同一個沒人等的查詢。結論是有讀取逾時重試的層，外層要容納「逾時 × 次數」，或者乾脆不對讀取逾時重試。

3. **用真正的 gunicorn 觀察 arbiter 與 worker**（真實工具）。在虛擬環境安裝 gunicorn，寫一個 `/slow` 會 `time.sleep(40)` 的 WSGI app，用 `gunicorn -w 2 --timeout 5 app:app` 啟動，另一個終端執行 `ps -o pid,ppid,rss,command -ax | grep gunicorn` 與 `curl -s -w '%{http_code} %{time_total}\n' 127.0.0.1:8000/slow`。
   答案要點：`ps` 會看到一個 arbiter 與兩個 PPID 指向它的 worker；`curl` 在約 5 秒後收到空回應（`curl: (52) Empty reply from server`），gunicorn 的 log 依序出現 `WORKER TIMEOUT` 與新的 `Booting worker`，worker 的 pid 改變了。改用 `-k gthread --threads 4` 再試一次，`/slow` 不會被 timeout 殺掉，驗證 43.3 節的說法。

4. **觀察 graceful shutdown 與 SIGKILL 的差別**（真實工具）。延續練習 3，讓 `/slow` 睡 8 秒，在請求進行中分別對 arbiter 送 `kill -TERM <pid>` 與 `kill -KILL <pid>`（後者會留下孤兒 worker，事後用 `pkill -f gunicorn` 清理），比較 curl 的結果與 log。
   答案要點：TERM 時 log 出現 `Handling signal: term`，`/slow` 仍然完成並回 200，之後 arbiter 才結束；在 SIGTERM 之後立刻發出的新 curl 拿不到正常回應（依時機可能被拒絕，或連上後在 worker 結束時被中斷），說明 gunicorn 不會自己做 drain。KILL 打在 arbiter 上時，worker 不會立刻消失，變成沒有管理者的孤兒，這正是 systemd 要用 `KillMode=mixed` 在逾時後清掉其餘 process 的原因。

5. **手算 worker 數量**。聲聲 Live 的「找老師」搜尋 API 尖峰每秒 300 個請求，平均在 app 裡停留 120 毫秒，其中 CPU 20 毫秒；三台 4 vCPU 的主機，每個 worker 的 RSS 250 MB，資料庫上限 200 條連線。用 N+1 容錯、保險係數 2，算出每台需要的 slot、CPU 使用率，以及 gthread 的 workers × threads 配置。
   答案要點：容錯時每台承擔 300 ÷ 2 ＝ 150 req/s；L ＝ 150 × 0.12 ＝ 18，乘 2 得 36 個 slot；CPU 150 × 0.02 ＝ 3 核，4 vCPU 的 75%，偏高，應考慮加主機或優化查詢；gthread 4 workers × 9 threads ＝ 36 slot，記憶體 1 GB；資料庫最多 3 × 36 ＝ 108 條連線，低於 200。

## 本章重點整理

- reverse proxy 與 application server 分工：nginx 負責慢 client、buffering、靜態檔、請求限制與信任邊界，gunicorn 與 uvicorn 負責 process 管理與 HTTP 到 WSGI／ASGI 的轉換，Python 只做 Python 才能做的事。
- gunicorn 採用 prefork：arbiter 建立 listening socket 後 fork 出 worker，所有 worker 共用同一個 accept queue；arbiter 不處理請求，只負責維持數量、檢查心跳與處理訊號。
- `timeout` 量的是 worker 的心跳，只有 sync worker 才等於請求上限；gthread 與 ASGI worker 的長請求不會被它殺掉，所以真正的請求逾時要在 app 與資料庫設定。
- `max_requests` 加 jitter 讓 worker 定期重生，可以壓住記憶體與 fd 的緩慢洩漏，但它只是保險，洩漏的根因仍要找出來。
- 傳統上 gunicorn 以 WSGI 為主，新版也內建 ASGI worker；sync 一次一個請求、不支援 keep-alive，gthread 用 thread 覆蓋 I/O 等待，ASGI 用 event loop 支撐大量長連線。
- worker 數量從 Little's law（L ＝ λ × W）出發，再用 CPU（約一個 process 一核）、記憶體（每個 worker 的 RSS）與下游連線數（主機 × worker × thread）三個限制驗證，並以 N+1 容錯計算。
- timeout 鏈的規則是請求逾時外層比內層長：最內層先放棄並回有意義的錯誤，外層只當保險；相鄰兩層等長會造成 502 與 504 的競態，內長外短則會讓內層白做並引發重試雪崩。
- 有重試的那一層，對外總時間是逾時乘以嘗試次數；讀取逾時通常不該重試，超過幾秒的工作應改成回 202 的背景工作。
- keep-alive 的規則方向相反：每一段連線，server 端的閒置上限都要比重用連線的 client 端長，否則上游先關閉，nginx 會把請求送進死連線而回 502。
- 502 代表上游連線出問題（被拒、被關、被重置），504 代表 nginx 自己的計時器到期，499 代表外層先放棄；用 error log 的訊息與 `x-request-id` 對照 gunicorn log，就能分辨 worker 被殺與 keep-alive 競態。
- client IP 要在所有流量必經的自家 proxy 依網段解析（nginx realip）並覆寫，後面的 `ProxyFix` 只信固定的 1 層；固定跳數在多條路徑下一定會被偽造，`forwarded_allow_ips` 也絕不能設成 `*`。
- graceful shutdown 的順序是 readiness 先回 503、drain 等上游停止送流量、關閉 listening socket、等進行中的請求做完，最後才是 SIGKILL 的保險；gunicorn 本身不會做 drain。
- zero-downtime deploy 的每一種做法（rolling、HUP、USR2、Kubernetes、blue／green）都在保證「停止接收」發生在「停止處理」之前，並要注意 Docker 的 PID 1、systemd 的 `KillMode=mixed` 與 `preload_app` 對 HUP 的影響。
- 靜態檔由 nginx 與 CDN 服務並以帶雜湊的檔名長期快取；需要權限的大檔案由 Flask 檢查權限後用 `X-Accel-Redirect` 交給 nginx 傳送。

## 延伸問答

> [!question]- Q1. 為什麼 gunicorn 的文件強烈建議把它放在 nginx 這類 proxy 後面？用 uvicorn 是不是就不需要了？
> 核心原因是 sync worker 的設計假設：一個 worker 一次只處理一個請求，從讀請求到寫完回應都被佔住。如果 client 很慢，例如行動網路上傳大檔案、或下載回應的速度很低，worker 的時間就花在等 bytes，而不是執行 Python。少數幾個慢 client 就能佔滿所有 worker，這也是 slowloris 這類攻擊的原理。nginx 預設會先把整個請求 body 收完、也會盡快把上游回應讀進 buffer 再慢慢送給 client，讓 gunicorn 面對的永遠是「同一個機房、一次送完」的請求。
>
> uvicorn 的 event loop 不怕慢連線，所以慢 client 這個理由對它比較弱；但 reverse proxy 承擔的其他工作仍然需要：TLS 終結、靜態檔與大檔案、請求大小限制、client IP 的信任邊界解析、多台後端的負載分配與被動 health check、統一的 access log 與 request ID。此外，ASGI app 裡任何一個阻塞呼叫都會讓整個 event loop 停住，前面有一層能設定逾時與重試的 proxy，可以把影響限縮。所以實務上 uvicorn 也幾乎都放在 nginx 或雲端 LB 後面。

> [!question]- Q2. 手算：某服務尖峰每秒 400 個請求，平均在 app 裡停留 80 毫秒，其中 CPU 10 毫秒。兩台 8 vCPU 主機，要能承受一台故障。用 sync worker 與 gthread 各需要多少配置？每個 worker RSS 200 MB 時記憶體各多少？
> 先算容錯情況：一台故障時另一台承擔全部 400 req/s。Little's law 得到平均同時處理的請求 L ＝ 400 × 0.08 ＝ 32，乘上保險係數 2 得 64 個 slot。CPU 需求是 400 × 0.01 ＝ 4 核，8 vCPU 的 50%，有餘裕。sync worker 一個 slot 就是一個 process，需要 64 個 worker，記憶體約 64 × 200 MB ＝ 12.5 GB，大多數主機承受不了，而且其中大部分時間 worker 都在等 I/O。
>
> gthread 讓 process 數接近核心數，例如 8 個 worker，每個 8 個 thread，提供 64 個 slot，記憶體只需 8 × 200 MB ＝ 1.6 GB（thread 的額外記憶體很小）。最後別忘了下游：兩台主機各 64 個 slot，合計 128 個，如果每個 thread 都可能握一條資料庫連線，資料庫上限必須大於 128，否則要限制每個 worker 的連線池大小或加 pooler。估算完還要上線驗證 accept queue 與 p99 延遲，因為 80 毫秒的平均值在資料庫變慢時會跟著變大。

> [!question]- Q3. 看 log 找原因：nginx error log 在下午 2 點到 4 點之間每小時出現十幾次 `upstream prematurely closed connection while reading response header from upstream`，晚上尖峰反而很少；gunicorn 的 log 沒有任何錯誤。你會怎麼判斷？
> 這個訊息表示 nginx 在等待回應 header 時，上游的連線被關閉了。上游關閉連線的常見原因有兩類：worker 在處理中被殺（逾時或 OOM），或者 keep-alive 的閒置連線被上游關閉。前者在 gunicorn 這一側一定會留下紀錄，例如 `WORKER TIMEOUT`、`was sent SIGKILL`、或 worker 的重新啟動訊息；題目說 gunicorn 沒有任何錯誤，所以第一類的可能性很低。
>
> 時間分布是第二個線索：離峰比尖峰多，代表問題和「連線閒置」有關。尖峰時連線一直在使用，很少閒置到上游的 keep-alive 上限；離峰時連線常閒置數秒，正好落在 gunicorn 已經關閉、nginx 還認為可用的區間。確認方法是比對 nginx upstream 的 `keepalive_timeout`（預設 60 秒）與 gunicorn 的 `keepalive`（預設 2 秒），並在 nginx 與 gunicorn 之間抓包，看是否 gunicorn 先送 FIN，接著 nginx 才送出新請求。修正是讓 gunicorn 的閒置上限長於 nginx 的，並讓 nginx 對連線錯誤重試 idempotent 請求。

> [!question]- Q4. 情境判斷：同事為了解決報表匯出的 504，提議把 nginx、gunicorn、LB 的逾時全部改成 300 秒。你同意嗎？
> 不同意，這會讓問題換一種方式出現。把所有逾時拉長，代表每一個卡住的請求都能佔住一個 worker 長達 5 分鐘；資料庫一變慢，所有 slot 很快被佔滿，正常的短請求只能在 accept queue 裡排隊，最後整個 API 一起變成逾時。而且使用者不會等 5 分鐘，他們會重新整理，讓同樣的慢請求加倍。逾時的意義就是在資源被耗盡之前放手，拉長它等於拿掉保險絲。
>
> 正確的方向是兩件事。第一，把長工作從請求路徑上移走：匯出改成背景工作，`POST` 立刻回 202 與工作編號，前端輪詢或用 SSE 取得進度，完成後下載檔案，每個 HTTP 請求都維持在幾秒內。第二，讓 timeout 鏈由內而外遞增：資料庫的 `statement_timeout` 與 app 的請求預算最短、最先觸發並回有意義的錯誤，gunicorn、nginx、LB、CDN 依序更長、只當保險，相鄰兩層之間留下差距，避免同時到期造成 502 與 504 的競態。

> [!question]- Q5. 面試題：你要在 Kubernetes 上做到 zero-downtime deploy，Pod 裡跑的是 gunicorn。請說明關機時會發生什麼，以及要設定哪些東西。
> 刪除舊 Pod 時，Kubernetes 會同時做兩件事：把 Pod 從 Service 的 endpoints 移除（各節點的 kube-proxy、ingress 或 Gateway 實作陸續更新規則），以及執行 `preStop` hook、然後對容器送 SIGTERM。這兩件事沒有先後保證，endpoints 的移除要幾秒才會在整個叢集生效；如果 gunicorn 一收到 SIGTERM 就停止 accept，這幾秒內仍被送過來的請求就會失敗。所以第一個設定是 `preStop` 先等幾秒，讓流量確實停止，再讓 SIGTERM 送達。
>
> 接著 gunicorn 的 arbiter 收到 SIGTERM，worker 在 `graceful_timeout` 內做完手上的請求。`terminationGracePeriodSeconds`（預設 30 秒）必須大於 preStop 的等待加上 `graceful_timeout`，否則最後會被 SIGKILL。其他配套包括：readiness probe 與 liveness probe 分開，避免關機中被誤判為死掉而重啟；容器用 exec 形式啟動，讓 gunicorn 是 PID 1 或確實收得到訊號；rolling update 的 `maxUnavailable` 與副本數要讓容量在換版期間仍然足夠；回應在關機期間帶 `Connection: close`，避免 keep-alive 連線把新請求帶進來。WebSocket 這類長連線還要主動請 client 重連。

> [!question]- Q6. 設計取捨：團隊發現 worker 的記憶體每小時漲 50 MB，有人提議設 `max_requests = 100`，有人提議找出洩漏再說。你怎麼取捨？`max_requests_jitter` 的作用是什麼？
> 兩者不衝突，應該同時做，但數字要合理。`max_requests` 讓 worker 在處理固定數量的請求後優雅退出並由 arbiter 補上，能把記憶體壓在可控範圍，立刻降低 OOM 的風險。不過 100 太小：每個 worker 重生都要重新 import 程式、建立連線池、暖快取，太頻繁的重生會讓延遲出現週期性的尖刺，資料庫也會看到大量的連線建立與中斷。通常設在幾千，讓重生的間隔遠大於暖機時間，同時又能在記憶體超過上限之前觸發。
>
> `max_requests_jitter` 給每個 worker 的上限加上一個隨機值。沒有 jitter 時，同時啟動的 worker 處理的請求數差不多，會在幾乎同一時間一起重生，那一刻整台主機的可用 slot 突然大減，延遲飆高；加上 jitter 後重生被打散。同時一定要繼續找洩漏：監控每個 worker 的 RSS 與 fd 數量，用 tracemalloc 或比對不同時間的物件數量找出成長的部分。`max_requests` 會掩蓋症狀，例如第 10 章的 CLOSE_WAIT 洩漏在重生時被一併清掉，但下游服務仍然承受著那些沒有被關閉的連線。

> [!question]- Q7. 聲聲 Live 的聊天服務原本寫成 Flask＋gthread，教室一多就撐不住。改成 ASGI＋uvicorn 時，要注意哪些部署上的差異？
> 先說為什麼要改：每個 WebSocket 或 SSE 連線會長時間掛著，在 gthread 裡等於永久佔住一個 thread，幾千個教室就要幾千個 thread，記憶體與切換成本都無法承受。ASGI 的 event loop 讓每條連線只是一個等待中的 coroutine，一個 process 可以掛上萬條。部署時 process 數仍然大約等於核心數（每個 event loop 只用一個核心），可以用 uvicorn 的 `--workers`、gunicorn 搭配 uvicorn 的 worker class，或新版 gunicorn 的內建 ASGI worker。
>
> 差異主要有四點。第一，任何阻塞呼叫（同步的資料庫驅動、`time.sleep`、大量 CPU 運算）會讓整個 event loop 上的所有連線一起停住，要改用 async 版本或丟到 thread pool。第二，timeout 的意義改變：連線本來就應該長時間存在，nginx 的 `proxy_read_timeout` 要長於應用層心跳的間隔，並設定 `proxy_http_version 1.1` 與 Upgrade 相關 header。第三，keep-alive 與 header 設定要重新對齊：uvicorn 的 `--timeout-keep-alive` 預設只有 5 秒，要長於 nginx 重用上游連線的時間；`--forwarded-allow-ips` 只列出前面的 proxy。第四，graceful shutdown 不可能等連線自然結束，要先讓 readiness 失敗，再分批送 close code 1012 請 client 重連，並用 `--timeout-graceful-shutdown` 設上限（第 33 章）。

> [!question]- Q8. 情境判斷：一個新的內部報表服務部署在 10.20.3.40，前面只有一層 nginx（同一台主機的 127.0.0.1），同事設定了 `forwarded_allow_ips = "*"` 與 `ProxyFix(x_for=2)`。有什麼問題？
> 先看實際的路徑：client 連到 nginx，nginx 在本機轉給 gunicorn，所以 proxy 只有 1 層。`ProxyFix(x_for=2)` 會相信 `X-Forwarded-For` 從右邊數第 2 個值，而 nginx 只附加了 1 個值（它看到的 client），第 2 個值如果存在，就是 client 自己在請求裡帶的內容。結果是任何人只要自己加一個 `X-Forwarded-For` header，就能決定 Flask 看到的 IP，限速、稽核 log、以 IP 判斷的存取控制都能被繞過；沒帶的人則因為值不夠兩個，`REMOTE_ADDR` 維持 127.0.0.1。正確設定是 `x_for=1`，或讓 nginx 依網段解析後覆寫。
>
> `forwarded_allow_ips = "*"` 則讓 gunicorn 相信任何來源送來的 `X-Forwarded-Proto` 等 header。如果 gunicorn 只聽 127.0.0.1，影響範圍還算有限；但若它綁在 0.0.0.0、而主機的 security group 又允許其他機器連到 gunicorn 的 port，任何人都能繞過 nginx 直接連，並自稱是 https。修正方式是讓 gunicorn 只綁定 127.0.0.1（或用 security group 只允許 nginx）、`forwarded_allow_ips` 只列出 nginx 的位址，並在上線前用 curl 自己帶偽造的 header 測一次，確認後端看到的值沒有被影響。

## 延伸閱讀

- gunicorn 官方文件〈Design〉〈Settings〉〈Signal Handling〉〈Deploying Gunicorn〉：prefork 架構、所有設定的預設值、訊號與 systemd 的建議設定
- uvicorn 官方文件〈Settings〉〈Deployment〉：`--workers`、`--timeout-keep-alive`、`--proxy-headers` 與 graceful shutdown
- nginx 官方文件：`ngx_http_proxy_module`（proxy_read_timeout、proxy_buffering、proxy_next_upstream、X-Accel-Redirect）、`ngx_http_upstream_module`（keepalive、keepalive_timeout）、`ngx_http_realip_module`
- Werkzeug 官方文件〈Tell Werkzeug it is Behind a Proxy〉與 `werkzeug.middleware.proxy_fix` 的 API 說明
- Kubernetes 官方文件〈Pod Lifecycle〉中 Pod 終止流程的說明，以及 container lifecycle hooks（preStop）
- PEP 3333〈Python Web Server Gateway Interface v1.0.1〉：WSGI 規格（第 41 章）
- John D. C. Little〈A Proof for the Queuing Formula: L = λW〉，Operations Research，1961
