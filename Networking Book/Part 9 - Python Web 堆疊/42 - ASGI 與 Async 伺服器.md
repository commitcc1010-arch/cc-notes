---
chapter: 42
title: ASGI 與 Async 伺服器
part: 9
---

# 第 42 章　ASGI 與 Async 伺服器

> [!abstract] 本章地圖
> **核心問題**：WSGI 的「一個請求、一次函式呼叫、佔住一個 worker」模型，為什麼撐不住聊天、串流與 WebSocket？ASGI 用什麼介面取代它，uvicorn、Starlette、FastAPI 又各自負責哪一層？
>
> **你會學到**：
> - 用 worker 佔用時間手算，說明長連線為什麼會把 WSGI 服務拖垮，以及 async 為什麼能用一個執行緒撐住上萬條連線
> - 逐欄讀懂 ASGI 的 scope、receive、send，畫出 HTTP、WebSocket、lifespan 三種 scope 的事件時序
> - 說清楚 `more_body` 如何變成 HTTP/1.1 的 Content-Length 或 chunked，以及 `http.disconnect` 的用途
> - 分辨 uvicorn（server）、Starlette（toolkit）、FastAPI（framework）的分工，知道 h11、httptools、uvloop 換掉的是哪一塊
> - 認出「在 async handler 裡呼叫阻塞函式」的症狀，用 loop lag 量出來，用 `asyncio.to_thread` 或 async 函式庫修好
> - 用標準函式庫從零寫一個最小 ASGI server，並寫出正確的 ASGI middleware
>
> **前置知識**：第 20 章（HTTP/1.1 訊息邊界與 chunked）、第 40 章（從 socket 寫 HTTP server、並行模型與 asyncio）、第 41 章（WSGI 與 Werkzeug）、第 31、32 章（long polling、SSE 與 WebSocket）

## 42.1 故事：三百人講座讓整個網站停擺

聲聲 Live 第一次辦免費的大型日語講座，報名人數三百人。講座頁面有一個聊天室，讓學生即時發問。為了趕上線，聊天室用最熟悉的方式寫：Flask 加上 **long polling**（長輪詢，client 發出請求後，server 不立刻回應，而是等到有新訊息或逾時才回，第 31 章介紹過）。學生的瀏覽器不斷呼叫 `GET /chat/poll`，每個請求最多掛 25 秒。這支 API 和網站其他部分一起跑在既有的 gunicorn 上：app-a（10.20.3.21:8000）與 app-b（10.20.3.22:8000），每台 9 個 sync worker。

晚上八點講座開始，八點零一分告警全響了：不只聊天室，連「找老師」頁面、付款頁、登入都在逾時，nginx 的 log 塞滿 `upstream timed out`。小晴打開 gunicorn 的狀態，看到 18 個 worker 全部在忙，忙的全是 `/chat/poll`，而且每個都「什麼也沒做，只是在等」。阿德看了一眼就說：「18 個 worker，每個被一個 long poll 綁 25 秒；三百個學生在線，等於要同時 300 個 worker。WSGI 的世界裡，等待也要佔一個 worker。」

團隊連夜把聊天拆出去，改成 ASGI 的即時服務：WebSocket 走 `rt.shengsheng.example`，經 L4 LB（203.0.113.40）與 nginx（10.20.2.11～.13）轉給即時 gateway gw-41（10.20.1.41）與 gw-42（10.20.1.42）上的 uvicorn（8001 port；第 33 章擴充後每台 gateway 前面還有一層本機 nginx，經 Unix socket 轉接）。下一週的講座，同樣三百人，uvicorn 只用兩個 process 就撐住了。但第三週出了新事故：Rita 要求聊天訊息先經過內容審查，小晴在 `async def` 的 handler 裡加了一行 `requests.post(...)` 呼叫審查服務，每次約 80 毫秒。講座尖峰每秒 30 則訊息，所有學生的訊息延遲從幾十毫秒變成好幾秒，LB 的 health check 也跟著逾時，兩台 uvicorn 輪流被移出服務，三百條 WebSocket 一起斷線又一起重連。

```text
 第一次講座（WSGI + long polling）
  300 個學生 ──GET /chat/poll（掛 25 秒）──► nginx ──► gunicorn：18 個 sync worker
                                                     │ ① 每個 worker 被一個「只是在等」的請求綁住
                                                     │ ② 首頁、付款、登入的請求排不到 worker
                                                     └──► ③ nginx 等不到 → 504，全站看起來掛了

 第三次講座（ASGI + WebSocket，但 handler 裡有阻塞呼叫）
  300 條 WebSocket ──► uvicorn（一個 event loop）──► async def on_message():
                                                       requests.post(審查服務)  ← ④ 80 ms 內 loop 完全停住
                       ⑤ 每秒 30 則 × 80 ms = 2.4 秒的阻塞 / 每秒 → 訊息排隊越來越長
                       ⑥ /readyz 也排在隊伍裡 → health check 逾時 → LB 把整台移出
```

這張圖是事後檢討會的白板。上半部是 WSGI 的結構性限制：① 一個請求從頭到尾佔住一個 worker，就算它只是在等；② 長連線吃光 worker 之後，短請求也被拖下水；③ 使用者看到的是全站逾時。下半部是 ASGI 服務最典型的事故：④ event loop 只有一個執行緒，任何不交出控制權的呼叫都會讓它停住；⑤ 停住的時間加總超過一秒，佇列只會越來越長；⑥ 連 health check 都回不了，LB 誤判主機壞掉。

這兩個事故是本章的兩條主線。不懂 WSGI 的呼叫模型，你會以為加 worker 就能解決第一個；不懂 event loop，你會以為「寫成 async def 就是非同步」而造成第二個。讀完本章，你會知道 ASGI 為什麼長這樣、uvicorn 怎麼把 bytes 變成事件交給 FastAPI，以及哪一行程式會讓三百個學生同時卡住。

## 42.2 WSGI 的天花板：一個請求、一次呼叫、一個 worker

第 41 章的 WSGI 介面是一個同步函式：`app(environ, start_response)`。server 把請求整理成 `environ` dict，呼叫一次 app，app 回傳一個 iterable，server 把它逐塊寫回 socket。這個設計簡單又通用，二十年來撐起了 Django 與 Flask。但「一次同步呼叫」這個前提，決定了三件 WSGI 做不到或做不好的事。

第一，**等待也佔資源**。app 從被呼叫到回傳的整段時間，呼叫它的 worker（process 或 thread）不能做別的事。查資料庫的 5 毫秒、long poll 的 25 秒、串流影片的 40 分鐘，對 worker 而言都一樣是「被佔住」。第二，**只有一個方向**。app 讀 `wsgi.input`、寫回應，但介面裡沒有「client 又送來一則訊息」或「client 已經離開」的通知；WebSocket 這種雙向、長時間、由任一方主動發話的協定，在 WSGI 規格裡根本沒有位置，只能靠 server 特定的非標準手段拿到底層 socket。第三，**沒有 process 層級的生命週期**。WSGI 只定義「每個請求怎麼呼叫」，沒有「開機時建立連線池、關機時把它關乾淨」的標準掛點，各家 server 只好自己發明 hook。

```text
 時間 →        0s            5s            10s           15s           20s           25s
 worker 1   [poll 學生001 ··························································]  等新訊息
 worker 2   [poll 學生002 ··························································]
   ...
 worker 18  [poll 學生018 ··························································]
 首頁請求    ×排隊 ··········································································► 逾時（504）
 付款請求    ×排隊 ··········································································► 逾時

 [ ] 內的「···」代表 worker 只是在等，CPU 幾乎是 0，但它不能去處理別的請求
```

這張時間軸對照了故事的現場。18 個 worker 每個被一個 long poll 綁 25 秒，期間 CPU 幾乎沒在用，但它們對 gunicorn 而言是「忙碌中」。之後到達的任何請求，不管只需要 5 毫秒還是 30 毫秒，都只能排隊。用 **Little 定律**（系統內平均同時處理的請求數＝每秒到達數 × 每個請求停留的時間）手算：三百個學生在線，每人隨時掛著一個 poll，同時進行的請求就是 300；而網站本身每秒 200 個、每個 30 毫秒的一般請求，只需要 200 × 0.03＝6 個 worker。長連線讓需求從 6 暴增到 306，問題不在 CPU，而在「同時存在的連線數」。

能不能把 worker 加到 306？用 gthread 開幾百個 thread 可行，但每個 thread 都有自己的 stack（Linux 預設保留 8 MB 虛擬位址空間）、要作業系統排程、還要搶 GIL；連線數到上萬時成本太高，這正是第 40 章的 C10K 問題。gevent 這類 monkey-patch 方案能讓 WSGI app「看起來同步、底層非同步」，但隱式切換難以除錯，也仍無法表達 WebSocket 的雙向事件。Python 社群的答案是直接定義一個 async 版本的介面：**ASGI**（Asynchronous Server Gateway Interface）。

| 需求 | WSGI（PEP 3333） | ASGI 3.0 |
|---|---|---|
| 呼叫模型 | 同步函式，一個請求一次呼叫 | `async` callable，每個連線或請求一次呼叫，內部可以 await |
| 等待時的成本 | 佔住一個 worker（process 或 thread） | 一個暫停的 coroutine，幾 KB 等級的記憶體 |
| 讀取請求 body | `wsgi.input` 檔案物件，阻塞讀取 | `await receive()` 取得 `http.request` 事件，可分多次 |
| 得知 client 離開 | 只能在寫入失敗時發現 | 收到 `http.disconnect` 事件 |
| WebSocket | 規格不支援 | `websocket` scope，有完整事件 |
| 開機／關機掛點 | 無標準 | `lifespan` scope |
| 典型 server | gunicorn（sync、gthread）、uWSGI、mod_wsgi | uvicorn、Hypercorn、Daphne、Granian、gunicorn 新版的 ASGI worker |

這張表的重點是第二列與第四列。ASGI 不是讓程式「跑得比較快」：一個 30 毫秒的 Flask view 改寫成 async，處理時間不會變短。它改變的是**等待的成本**與**可以表達的互動**：等待只是一個暫停的 coroutine，不再是一個被佔住的 worker；client 送訊息、離開、server 開機關機，都變成 app 能收到的事件。

> [!warning] 常見誤解
> Flask 2.0 起可以寫 `async def` 的 view，但這不代表 Flask 變成了 ASGI 框架。Flask 仍是 WSGI app，每個請求仍佔一個 worker，async view 只是在這個 worker 裡跑一個 event loop 來執行它；它適合在一個請求內並行呼叫幾個下游服務，不能拿來承載上萬條長連線或 WebSocket。

## 42.3 async 的底層：event loop 與 coroutine

ASGI 建立在 Python 的 `asyncio` 上，第 40 章已經用它寫過 HTTP server，這裡只複習理解本章需要的三個概念。**coroutine**（協程）是用 `async def` 定義的函式，呼叫它不會立刻執行，而是得到一個可以「暫停、之後再繼續」的物件；在 `await` 的地方，它把控制權交出去。**event loop**（事件迴圈）是一個不斷循環的排程器：找出可以繼續的 coroutine，讓它跑到下一個 `await`，再換下一個。**task** 是被 event loop 排程的 coroutine，用 `asyncio.create_task()` 建立。

```text
                       ┌──────────────────── 一個執行緒 ────────────────────┐
                       │                                                     │
   socket 可讀／可寫 ─►│  selector（Linux epoll／macOS kqueue，第 40 章）    │
   計時器到期 ────────►│        │ 「哪些 fd 準備好了？哪些計時器到了？」      │
                       │        ▼                                            │
                       │  ready queue：[task A] [task C] [task F] ...        │
                       │        │ 依序取出                                   │
                       │        ▼                                            │
                       │  執行 task A，直到它 await 一個還沒好的東西          │
                       │        │ （例如 await reader.read()）                │
                       │        └──► 登記「A 在等 fd 37 可讀」，換下一個       │
                       └─────────────────────────────────────────────────────┘
```

event loop 的每一輪做兩件事：先問 selector 哪些 socket 有資料、哪些計時器到期，把對應的 task 放進 ready queue；再依序執行 ready queue 裡的 task，每個 task 都跑到下一個「需要等」的 `await` 為止。整個過程只有一個執行緒，所以一萬條閒置的連線只是一萬個登記在 selector 上的 fd 與一萬個暫停的 coroutine，不需要一萬個 thread。

這個模型叫 **cooperative multitasking**（合作式多工）：切換只發生在 `await`，由 coroutine 自願交出控制權。優點是兩個 `await` 之間不會被打斷，共享變數不必加鎖；弱點是只要一段程式不交出控制權（`time.sleep()`、同步的 `requests.post()`），整個 loop 上的連線都會停住，這就是故事第三週的事故（42.9 節）。下面的程式讓你看到切換發生在 await，以及一萬個等待中的 coroutine 只需要一個執行緒。

```python
import asyncio
import threading
import time

log = []


async def handle(name, wait_ms):
    log.append(f"{name} 開始")
    await asyncio.sleep(wait_ms / 1000)   # await：「我要等 I/O，先讓別人跑」
    log.append(f"{name} 等完 {wait_ms} ms，繼續")


async def main():
    await asyncio.gather(handle("A（查課表）", 30), handle("B（送聊天）", 10))
    t0 = time.perf_counter()
    await asyncio.gather(*(asyncio.sleep(0.2) for _ in range(10_000)))   # 一萬個同時在等的連線
    return (time.perf_counter() - t0) * 1000


elapsed = asyncio.run(main())
print(" → ".join(log))
print(f"10,000 個 coroutine 各等 200 ms，總共花 {elapsed:.0f} ms，"
      f"執行緒數仍是 {threading.active_count()}")
assert log[2].startswith("B") and elapsed < 2000 and threading.active_count() == 1
```

```text
A（查課表） 開始 → B（送聊天） 開始 → B（送聊天） 等完 10 ms，繼續 → A（查課表） 等完 30 ms，繼續
10,000 個 coroutine 各等 200 ms，總共花 240 ms，執行緒數仍是 1
```

第一行顯示 A 先開始，在 `await asyncio.sleep` 交出控制權後 B 才開始；B 只等 10 毫秒，所以先完成，A 等滿 30 毫秒後才繼續。兩個「請求」交錯執行，卻只有一個執行緒，執行順序完全由 await 點與等待時間決定。第二行是 async 的經濟學：一萬個 coroutine 同時等 200 毫秒，總共只花兩百多毫秒（多出來的是建立與排程一萬個 task 的成本，每次執行數字不同），執行緒數一直是 1。如果改用一萬個 thread 各自 `time.sleep(0.2)`，你會先撞上作業系統的 thread 上限或記憶體壓力，而不是 CPU。

## 42.4 ASGI 的核心：一個 async callable、三個參數

ASGI 規格（core 版本 3.0）把 app 定義成一個 async callable：

```text
 async def app(scope, receive, send):
     │         │      │        └─ async callable：app 呼叫 await send(event) 把事件交給 server
     │         │      └────────── async callable：app 呼叫 await receive() 向 server 要下一個事件
     │         └───────────────── dict：這條連線（或這個請求）的靜態資訊，type 決定其餘欄位
     └─────────────────────────── 每一個新的連線範圍呼叫一次

 server（uvicorn）                                                    app（FastAPI／你的程式）
 ┌───────────────────────┐   scope = {"type": "http", "path": ...}  ┌──────────────────────┐
 │ socket bytes          │ ────────────── 呼叫一次 ───────────────► │                      │
 │   ↓ 解析（h11 等）    │   receive() → {"type": "http.request"…}  │  await receive()     │
 │ 事件 dict             │ ───────────────────────────────────────► │                      │
 │   ↑ 序列化            │   send({"type": "http.response.start"…}) │  await send(...)     │
 │ socket bytes          │ ◄─────────────────────────────────────── │                      │
 └───────────────────────┘                                          └──────────────────────┘
```

上半部是介面本身。`scope` 是一個 dict，描述這個連線範圍的靜態資訊：是 HTTP 還是 WebSocket、path 是什麼、header 有哪些；它在呼叫時就決定了，之後不會變。`receive` 與 `send` 是兩個 async 函式，代表兩個方向的**事件**（event，也叫 message）：每個事件都是一個 dict，用 `"type"` 欄位說明它是什麼，例如 `"http.request"`、`"websocket.receive"`。下半部是分工：server 負責 socket、解析、序列化，app 完全不碰 bytes，只處理 dict。這和 WSGI 的 environ 有一個本質差異：WSGI 是「server 把一切準備好，呼叫 app 一次」；ASGI 是「server 開一個對話，app 和 server 用事件你來我往，直到對話結束」。

**scope 的範圍**依協定而定，這一點很容易誤解。HTTP 的 scope 是**每個請求一個**：一條 keep-alive 連線上的三個請求，會呼叫 app 三次、得到三個 scope。WebSocket 的 scope 是**每條連線一個**：從交握到關閉，app 只被呼叫一次，整個 coroutine 活多久，連線就活多久。lifespan 的 scope 則是**每個 process 一個**，從 server 啟動到關閉。

| scope type | 一次呼叫涵蓋的範圍 | app 從 receive 收到的事件 | app 用 send 送出的事件 |
|---|---|---|---|
| `http` | 一個 HTTP 請求與回應 | `http.request`、`http.disconnect` | `http.response.start`、`http.response.body` |
| `websocket` | 一條 WebSocket 連線 | `websocket.connect`、`websocket.receive`、`websocket.disconnect` | `websocket.accept`、`websocket.send`、`websocket.close` |
| `lifespan` | 一個 server process 的一生 | `lifespan.startup`、`lifespan.shutdown` | `lifespan.startup.complete`／`.failed`、`lifespan.shutdown.complete`／`.failed` |

規格的命名很規律：事件 type 以 scope type 開頭；app 收到的是「發生了什麼」，app 送出的是「我要你做什麼」。每個 scope 都帶 `scope["asgi"]`，例如 `{"version": "3.0", "spec_version": "2.5"}`：`version` 是 core 介面版本，`spec_version` 是該協定子規格的版本（HTTP 與 WebSocket 的子規格依 2026 年 10 月查證是 2.5）。app 遇到不認得的 scope type 應該丟出例外，server 會據此判斷它不支援（例如 lifespan，42.7 節）。

早期的 ASGI 2 是兩段式的 `app(scope)(receive, send)`，ASGI 3.0（2019 年）改成現在的單一 callable；2026 年的主流框架與 server 都是 ASGI 3。

## 42.5 HTTP over ASGI：scope、receive、send 的每一個欄位

### http scope：environ 的 async 版本

HTTP scope 的欄位大多能對應到第 41 章的 WSGI environ，但型別更嚴格：會被拿來做字串比對的欄位是 `str`，從網路原封不動搬來的是 `bytes`。

| ASGI scope 欄位 | 型別與範例 | 對應的 WSGI environ | 注意事項 |
|---|---|---|---|
| `type` | `"http"` | 無 | 決定其餘欄位 |
| `http_version` | `"1.1"`、`"2"` | `SERVER_PROTOCOL` | 不含 `HTTP/` 前綴 |
| `method` | `"POST"` | `REQUEST_METHOD` | 大寫 |
| `scheme` | `"https"` | `wsgi.url_scheme` | 經過 proxy 時要看 server 是否信任 `X-Forwarded-Proto`（第 25、43 章） |
| `path` | `"/teachers/美咲"` | `PATH_INFO` | 已做 percent-decoding 並以 UTF-8 解碼成 `str` |
| `raw_path` | `b"/teachers/%E7%BE%8E%E5%92%B2"` | 無（WSGI 拿不到） | 原始 bytes，做簽章驗證或精確路由時用 |
| `query_string` | `b"lang=ja&page=2"` | `QUERY_STRING` | bytes，**不**解碼、不含 `?` |
| `root_path` | `"/rt"` | `SCRIPT_NAME` | app 掛在子路徑下時使用 |
| `headers` | `[(b"host", b"rt.shengsheng.example"), ...]` | `HTTP_*` | 名稱與值都是 bytes 的二元組 list，保留順序與重複；名稱應為小寫 |
| `client`／`server` | `("198.51.100.23", 51514)` | `REMOTE_ADDR`、`SERVER_NAME` | 在 proxy 後面時，`client` 是 proxy 的位址，除非 server 依信任清單改寫 |
| `state` | dict | 無 | lifespan 放進去的共享資源的淺複本（42.7 節） |

最值得注意的是 `headers`。WSGI 把 header 轉成 `HTTP_X_REQUEST_ID` 這種鍵，同名 header 被合併，底線與連字號的區別也消失；ASGI 保留原始 list，重複的 header 都看得到。所以別用 `dict(scope["headers"])` 粗暴轉換後就做安全檢查：重複的 header 會被後者蓋掉，可能被利用（第 20 章的 smuggling 也源自各層對重複 header 的理解不同）。

### 事件：一個請求的完整對話

app 被呼叫後，用 `receive()` 取得請求 body，用 `send()` 送出回應。下面是聲聲 Live 學生上傳 40 KB 作業附件、server 串流回傳結果的完整事件時序：

```text
 client                     server（uvicorn）                             app
   │── POST /upload ───────►│ 解析 request line 與 header                  │
   │   Content-Length: 40000│── 呼叫 app(scope, receive, send) ───────────►│
   │                        │◄──────────────────────── await receive() ────│
   │── body 前 16 KB ──────►│── {"type":"http.request","body":…16384 bytes,│
   │                        │    "more_body": True} ──────────────────────►│
   │── body 中 16 KB ──────►│── {"http.request", 16384 bytes, more_body: True}►│
   │── body 後 7 KB ───────►│── {"http.request", 7232 bytes, more_body: False}►│ body 讀完
   │                        │◄── {"type":"http.response.start","status":200, │
   │                        │      "headers":[(b"content-type", …)]} ───────│
   │◄── 200 header ─────────│   （沒有 content-length → 改用 chunked）       │
   │                        │◄── {"type":"http.response.body","body":b"…",   │
   │◄── chunk ──────────────│      "more_body": True} ───────────────────────│
   │◄── 最後的 0 chunk ─────│◄── {"http.response.body", more_body: False} ──│ 回應結束
   │                        │◄──────────────────────── await receive() ────│（若 app 還在等）
   │                        │── {"type": "http.disconnect"} ──────────────►│
```

從上往下讀。server 讀完 request line 與 header 就呼叫 app，**不必等 body 到齊**；body 以一個或多個 `http.request` 事件交給 app，`more_body: True` 代表「後面還有」，最後一個事件的 `more_body` 是 `False`（沒有 body 的 GET 也會收到一個 body 為空、`more_body` 為 False 的事件）。這讓 app 能邊收邊處理大檔案，也能在讀到一半就決定拒絕（42.10 節的 body 上限 middleware）。

回應分成兩種事件。`http.response.start` 帶 status 與 headers，**必須先送、只能送一次**；接著送一個或多個 `http.response.body`，同樣用 `more_body` 表示後面還有沒有。最後一個 `more_body: False` 的 body 事件代表回應結束，server 據此決定這條 keep-alive 連線可以接下一個請求。如果回應已經結束、或 client 斷線之後 app 再呼叫 `receive()`，得到的是 `http.disconnect`；串流回應（例如第 31 章的 SSE）正是靠「同時等待 `receive()`」來及早發現學生關掉了分頁，停止白做工。這是 WSGI 做不到的事。

| 事件 type | 方向 | 欄位 | 預設值與規則 |
|---|---|---|---|
| `http.request` | server → app | `body`（bytes）、`more_body`（bool） | `body` 預設 `b""`、`more_body` 預設 `False` |
| `http.disconnect` | server → app | 無 | client 斷線，或回應送完後再 receive |
| `http.response.start` | app → server | `status`（int）、`headers`（bytes 二元組）、`trailers`（bool） | 必須第一個送；header 名稱必須小寫；`trailers` 預設 `False` |
| `http.response.body` | app → server | `body`（bytes）、`more_body`（bool） | 可以多次；`more_body: False` 代表結束 |

### more_body 變成 bytes：Content-Length 還是 chunked

ASGI 的事件裡沒有「chunked」這個字。app 只說「我要送這段 body，後面還有」，至於線上的 bytes 用什麼格式切出訊息邊界，是 server 依 HTTP 版本決定的。在 HTTP/1.1 上，規則很直接：app 在 `http.response.start` 裡給了 `content-length`，server 就照長度送；沒給，server 就用第 20 章的 chunked 編碼，每個 body 事件變成一個 chunk，最後補上長度為 0 的 last-chunk。在 HTTP/2 上，同樣的事件會變成 DATA frame，最後一個帶 END_STREAM 旗標（第 22 章），app 完全不用改。

app 只是一個 async 函式，這帶來一個很實用的性質：不需要 socket、不需要 server，你自己寫一個假的 `receive` 與 `send` 就能呼叫它。下面的程式就這樣測試一個課表 app，並示範 server 會怎麼把同一串事件翻譯成 bytes：

```python
import asyncio


def make_schedule_app(streaming):
    async def schedule_app(scope, receive, send):
        """今日課表：streaming=True 時邊查邊送，不給 Content-Length。"""
        event = await receive()
        assert event == {"type": "http.request", "body": b"", "more_body": False}
        rows = [b"20:00 Japanese|", b"21:00 English|"]
        headers = [(b"content-type", b"text/plain")]
        if not streaming:
            headers.append((b"content-length", str(sum(map(len, rows))).encode()))
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        for row in rows:
            await send({"type": "http.response.body", "body": row, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
    return schedule_app


def to_http1(events):
    """把 app 送出的事件翻譯成 HTTP/1.1 的 bytes：這是 server 的工作，不是 app 的。"""
    start, out = events[0], []
    names = [n for n, _ in start["headers"]]
    chunked = b"content-length" not in names
    head = [b"HTTP/1.1 %d OK" % start["status"]] + [n + b": " + v for n, v in start["headers"]]
    if chunked:
        head.append(b"transfer-encoding: chunked")
    out.append(b"\r\n".join(head) + b"\r\n\r\n")
    for ev in events[1:]:
        body = ev.get("body", b"")
        if chunked and body:
            out.append(b"%x\r\n" % len(body) + body + b"\r\n")
        elif body:
            out.append(body)
        if chunked and not ev.get("more_body", False):
            out.append(b"0\r\n\r\n")
    return b"".join(out)


async def run(streaming):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)
    scope = {"type": "http", "method": "GET", "path": "/schedule/today", "headers": []}
    await make_schedule_app(streaming)(scope, receive, send)
    return sent


events = asyncio.run(run(streaming=True))
for ev in events:
    print({k: v for k, v in ev.items() if k != "headers"})
print(to_http1(events).decode().replace("\r\n", "\\r\\n\n"))
fixed = to_http1(asyncio.run(run(streaming=False)))
print(fixed.decode().replace("\r\n", "\\r\\n\n"))
assert b"transfer-encoding: chunked" in to_http1(events) and b"0\r\n\r\n" in to_http1(events)
assert b"content-length: 29" in fixed and b"chunked" not in fixed
```

```text
{'type': 'http.response.start', 'status': 200}
{'type': 'http.response.body', 'body': b'20:00 Japanese|', 'more_body': True}
{'type': 'http.response.body', 'body': b'21:00 English|', 'more_body': True}
{'type': 'http.response.body', 'body': b'', 'more_body': False}
HTTP/1.1 200 OK\r\n
content-type: text/plain\r\n
transfer-encoding: chunked\r\n
\r\n
f\r\n
20:00 Japanese|\r\n
e\r\n
21:00 English|\r\n
0\r\n
\r\n

HTTP/1.1 200 OK\r\n
content-type: text/plain\r\n
content-length: 29\r\n
\r\n
20:00 Japanese|21:00 English|
```

前四行是 app 送出的事件（為了版面省略 headers）：一個 start、兩個帶資料的 body、一個空的結束 body。中段是串流模式下 server 會送出的 bytes：app 沒給 `content-length`，所以加上 `transfer-encoding: chunked`；`f` 是十六進位的 15，也就是 `20:00 Japanese|` 的長度，`e` 是 14；最後的 `0\r\n\r\n` 是 last-chunk，正是那個空的 `more_body: False` 事件翻譯出來的。最下面是非串流模式：app 事先算好 29 bytes 並放進 header，同樣的 body 事件就直接接在 header 後面。

Starlette 與 FastAPI 的 TestClient 能「不開 port 就測試整個 app」，本質上就是這個假的 receive 與 send。另一個推論是：**app 不應該自己送 `transfer-encoding` header**，訊息邊界是 server 的職責。

## 42.6 WebSocket over ASGI：事件序列

WebSocket 的細節在第 32 章：交握是一個帶 `Upgrade: websocket` 的 HTTP 請求，server 回 `101 Switching Protocols` 之後，同一條 TCP 連線改傳 WebSocket frame，frame 有 opcode、mask 與長度欄位。ASGI 把這些全部藏在 server 裡：交握的 `Sec-WebSocket-Accept` 計算、frame 的編解碼與 masking、ping／pong 心跳、分片重組，都是 uvicorn 這一層的事（uvicorn 交給 websockets 或 wsproto 函式庫）。app 看到的只是一串事件。

```text
 瀏覽器                         server（uvicorn）                                  app
   │── GET /ws/classroom/8812 ─►│ 收到 Upgrade 請求，先不回應                       │
   │   Upgrade: websocket       │── app(scope={"type":"websocket", "path": …,      │
   │   Origin: https://www…     │        "subprotocols": ["ss-chat.v1"]}, …) ─────►│
   │   Sec-WebSocket-Protocol   │── receive() → {"type": "websocket.connect"} ────►│ ① 檢查 Origin、cookie
   │                            │◄── send({"type":"websocket.accept",               │
   │◄── 101 Switching Protocols─│         "subprotocol": "ss-chat.v1"}) ───────────│ ② 決定接受
   │════ text frame「こんばんは」═►│── receive() → {"type":"websocket.receive",       │
   │                            │        "text": "こんばんは"} ────────────────────►│ ③ 處理訊息
   │◄═══ text frame ════════════│◄── send({"type":"websocket.send", "text": …}) ───│
   │   （ping／pong 由 server 自動處理，app 看不到）                                │
   │════ close frame 1001 ═════►│── receive() → {"type":"websocket.disconnect",    │
   │                            │        "code": 1001, "reason": ""} ─────────────►│ ④ 清理，return
```

① 交握請求抵達時，server 還沒回 101，而是先呼叫 app 並送出 `websocket.connect`。這個時間點非常重要：app 在這裡可以檢查 `Origin` header、讀取 cookie 或 token，決定要不要接受。② app 送 `websocket.accept`（可以指定選中的 subprotocol，spec 2.1 起還能附加回應 header），server 這時才回 101。如果 app 在 accept 之前就送 `websocket.close`，server 必須回 **HTTP 403** 並結束交握，瀏覽器端常常只看到一個籠統的 1006 錯誤。③ 之後雙方用 `websocket.receive` 與 `websocket.send` 交換訊息，每個事件的 `text` 與 `bytes` 恰好只有一個有值，對應 text frame 與 binary frame。④ 對方關閉時，app 收到 `websocket.disconnect`，帶 close code（client 沒給 code 時 server 填 1005），spec 2.5 起也帶 `reason`；app 應該清理狀態並結束 coroutine。

| 事件 type | 方向 | 欄位 | 說明 |
|---|---|---|---|
| `websocket.connect` | server → app | 無 | 交握請求到了，等 app 決定 |
| `websocket.accept` | app → server | `subprotocol`、`headers` | server 收到才回 101 |
| `websocket.receive` | server → app | `text` 或 `bytes` | 一則完整訊息（分片已由 server 重組） |
| `websocket.send` | app → server | `text` 或 `bytes` | 必須在 accept 之後 |
| `websocket.disconnect` | server → app | `code`、`reason` | 連線已關閉；之後再 send 應該拋錯（spec 2.4） |
| `websocket.close` | app → server | `code`（預設 1000）、`reason` | accept 前送出等於拒絕（403） |

下面用事件序列模擬 server，跑一次聲聲 Live 的教室聊天 app：一個正常學生進教室說話後關分頁，一個惡意網站嘗試用學生的 cookie 連進來。

```python
import asyncio

ALLOWED_ORIGINS = {b"https://www.shengsheng.example"}


async def classroom_chat(scope, receive, send):
    """教室聊天的 ASGI app：同一個 app 的 websocket scope 一條連線只呼叫一次。"""
    assert scope["type"] == "websocket"
    event = await receive()
    assert event["type"] == "websocket.connect"            # 交握請求到了，但還沒回 101
    origin = dict(scope["headers"]).get(b"origin")
    if origin not in ALLOWED_ORIGINS:                      # 擋跨站 WebSocket 劫持（第 23、32 章）
        await send({"type": "websocket.close", "code": 1008})  # accept 之前 close → server 回 403
        return
    proto = "ss-chat.v1" if "ss-chat.v1" in scope["subprotocols"] else None
    await send({"type": "websocket.accept", "subprotocol": proto})   # server 這時才送 101
    while True:
        event = await receive()
        if event["type"] == "websocket.disconnect":
            return                                         # 對方走了：清理狀態後結束
        text = event.get("text")
        if text == "/bye":
            await send({"type": "websocket.close", "code": 1000, "reason": "bye"})
            return
        await send({"type": "websocket.send", "text": f"[8812] {text}"})


async def simulate(name, origin, script):
    """模擬 server：把 HTTP Upgrade 與 WebSocket frame 翻譯成事件，印出雙方往來。"""
    print(f"── {name}")
    inbox = asyncio.Queue()
    for item in [{"type": "websocket.connect"}, *script]:
        inbox.put_nowait(item)

    async def receive():
        event = await inbox.get()
        print(f"  server → app  {event}")
        return event

    async def send(message):
        print(f"  app → server  {message}")
        if message["type"] == "websocket.close" and not accepted:
            print("  （尚未 accept：server 對瀏覽器回 HTTP 403，交握失敗）")
        if message["type"] == "websocket.accept":
            accepted.append(True)
    accepted = []
    scope = {"type": "websocket", "path": "/ws/classroom/8812", "scheme": "wss",
             "headers": [(b"origin", origin)], "subprotocols": ["ss-chat.v1"],
             "asgi": {"version": "3.0", "spec_version": "2.5"}}
    await asyncio.wait_for(classroom_chat(scope, receive, send), timeout=1)
    return accepted


async def main():
    ok = await simulate("學生正常進教室", b"https://www.shengsheng.example", [
        {"type": "websocket.receive", "text": "こんばんは"},
        {"type": "websocket.disconnect", "code": 1001, "reason": ""}])   # 1001：關分頁
    bad = await simulate("惡意網站嘗試連線", b"https://evil.example", [])
    assert ok and not bad


asyncio.run(main())
```

```text
── 學生正常進教室
  server → app  {'type': 'websocket.connect'}
  app → server  {'type': 'websocket.accept', 'subprotocol': 'ss-chat.v1'}
  server → app  {'type': 'websocket.receive', 'text': 'こんばんは'}
  app → server  {'type': 'websocket.send', 'text': '[8812] こんばんは'}
  server → app  {'type': 'websocket.disconnect', 'code': 1001, 'reason': ''}
── 惡意網站嘗試連線
  server → app  {'type': 'websocket.connect'}
  app → server  {'type': 'websocket.close', 'code': 1008}
  （尚未 accept：server 對瀏覽器回 HTTP 403，交握失敗）
```

第一段是正常流程：`websocket.connect` 進來，app 檢查 Origin 是允許清單裡的 `www.shengsheng.example`（https），從 client 提議的 subprotocol 中選了 `ss-chat.v1`（第 32 章定義的聊天協定版本）並 accept；學生送出「こんばんは」，app 加上課程編號 8812 回送；學生關掉分頁，瀏覽器送出 close code 1001（going away），app 收到 `websocket.disconnect` 後結束。注意整段對話裡 app 從頭到尾只被呼叫一次，連線的生命就是這個 coroutine 的生命。

第二段是 Rita 最在意的防線。WebSocket 交握不受 CORS 保護；只要 cookie 會被帶上（例如 cookie 沒有 SameSite 保護，或攻擊頁面來自同站的其他子網域），而 server 又不檢查 `Origin`，別的網頁就能以學生的身分連進教室，這叫 **CSWSH**（Cross-Site WebSocket Hijacking，第 23、32 章）。`__Host-sid` 的 `SameSite=Lax` 是一層保護，Origin 檢查是另一層，兩者都要有。app 在 `websocket.connect` 階段發現 Origin 不在允許清單，直接送 `websocket.close`，因為還沒 accept，server 會回 HTTP 403，連線從頭到尾沒有升級成 WebSocket。這個檢查必須在 accept **之前**做；accept 之後再關，對方已經連上，也可能已經送出訊息。

廣播、跨 process 的 pub/sub 與重連補發屬於第 33 章。這裡只需記住：同一個 process 的所有 WebSocket 共享一個 event loop，一個 handler 卡住，每一間教室都會同時卡住（42.9 節）。

## 42.7 lifespan：process 的開機與關機

即時服務在接客之前要做幾件事：建立到資料庫（10.20.17.15:5432）的連線池、建立一個共用的 HTTP client 連到 `reco` 服務、載入課程設定。關機時要把連線池關乾淨，否則資料庫那邊會留下一堆半開連線。這些事情不屬於任何一個請求，WSGI 沒有地方放；ASGI 用 **lifespan** scope 解決。

```text
 server（uvicorn）                                           app
   │── app(scope={"type": "lifespan", "state": {}}, …) ────►│  （coroutine 一直活到關機）
   │── receive() → {"type": "lifespan.startup"} ───────────►│  建立連線池，放進 scope["state"]
   │◄── send({"type": "lifespan.startup.complete"}) ────────│
   │  這時才開始 listen、接受連線                             │
   │   ⋮  （每個 http／websocket scope 都帶 state 的淺複本） │
   │  收到 SIGTERM：停止接新連線，等進行中的請求結束          │
   │── receive() → {"type": "lifespan.shutdown"} ──────────►│  關閉連線池
   │◄── send({"type": "lifespan.shutdown.complete"}) ───────│
   │  process 結束                                           │
```

lifespan 的 app 被呼叫一次，coroutine 從 server 啟動一直活到關機。server 先送 `lifespan.startup`，app 完成初始化後回 `lifespan.startup.complete`，server **這時才開始接受連線**，所以第一個請求一定看得到已經建好的連線池。app 把共享資源放進 `scope["state"]`，server 會把這個 dict 的淺複本放進之後每一個 http 與 websocket scope 的 `state` 欄位。關機時順序反過來：server 停止接受新連線、等進行中的請求結束，再送 `lifespan.shutdown`。

失敗有兩種情況，server 的處理方式不同。如果 app 回 `lifespan.startup.failed`（帶 `message`），代表「我支援 lifespan，但初始化失敗了」，server 應該記錄訊息並退出，而不是帶著壞掉的狀態接客。如果 app 一收到 lifespan scope 就丟出例外，規格規定 server 視為「這個 app 不支援 lifespan」，繼續啟動但不再送 lifespan 事件。uvicorn 的 `--lifespan auto`（預設）就是這個行為，`--lifespan on` 則要求 lifespan 一定要成功。下面的程式模擬 server 的這套判斷：

```python
import asyncio


async def start_server_like_uvicorn(app, mode="auto"):
    """模擬 server 啟動時的 lifespan 協商，回傳 (能否開始 listen, 說明)。"""
    inbox, outbox = asyncio.Queue(), asyncio.Queue()
    state = {}
    task = asyncio.create_task(app({"type": "lifespan", "asgi": {"version": "3.0"}, "state": state},
                                   inbox.get, outbox.put))
    await inbox.put({"type": "lifespan.startup"})
    reply = asyncio.create_task(outbox.get())
    done, _ = await asyncio.wait({task, reply}, return_when=asyncio.FIRST_COMPLETED)
    if task in done and reply not in done:      # app 直接丟例外：它不支援 lifespan
        reply.cancel()
        exc = task.exception()
        if mode == "on":
            return False, f"lifespan=on 但 app 丟出 {type(exc).__name__}，拒絕啟動"
        return True, f"app 不支援 lifespan（{type(exc).__name__}），auto 模式照常啟動"
    msg = reply.result()
    if msg["type"] == "lifespan.startup.failed":
        return False, f"startup.failed：{msg.get('message', '')}，拒絕啟動"
    await inbox.put({"type": "lifespan.shutdown"})  # 示範用：馬上走完關機流程
    assert (await outbox.get())["type"] == "lifespan.shutdown.complete"
    await task
    return True, f"startup.complete，state={state}"


async def good_app(scope, receive, send):
    while True:
        event = await receive()
        if event["type"] == "lifespan.startup":
            scope["state"]["db_pool"] = "pool(10.20.17.15:5432, size=10)"
            await send({"type": "lifespan.startup.complete"})
        elif event["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


async def db_down_app(scope, receive, send):
    event = await receive()
    try:
        raise ConnectionRefusedError("10.20.17.15:5432")   # 啟動時連不上資料庫
    except OSError as exc:
        await send({"type": "lifespan.startup.failed", "message": f"db unreachable {exc}"})


async def http_only_app(scope, receive, send):
    if scope["type"] != "http":                  # 只寫了 HTTP 的 app，遇到 lifespan 就丟例外
        raise RuntimeError(f"unsupported scope {scope['type']}")


async def main():
    results = []
    for app, mode in ((good_app, "auto"), (db_down_app, "auto"),
                      (http_only_app, "auto"), (http_only_app, "on")):
        ok, why = await start_server_like_uvicorn(app, mode)
        results.append(ok)
        print(f"{app.__name__:<14} lifespan={mode:<4} → {'listen' if ok else '退出'}｜{why}")
    assert results == [True, False, True, False]


asyncio.run(main())
```

```text
good_app       lifespan=auto → listen｜startup.complete，state={'db_pool': 'pool(10.20.17.15:5432, size=10)'}
db_down_app    lifespan=auto → 退出｜startup.failed：db unreachable 10.20.17.15:5432，拒絕啟動
http_only_app  lifespan=auto → listen｜app 不支援 lifespan（RuntimeError），auto 模式照常啟動
http_only_app  lifespan=on   → 退出｜lifespan=on 但 app 丟出 RuntimeError，拒絕啟動
```

第一行是正常情況：startup 完成，連線池放進 state，server 開始 listen。第二行是資料庫連不上：app 明確回 `startup.failed`，server 拒絕啟動。這是正確的：部署系統（第 43 章）看到 process 退出就不會把它放進 LB，舊版本繼續服務。第三、四行是同一個只寫了 HTTP 的 app：在 auto 模式下，server 把它的例外解讀成「不支援 lifespan」並照常啟動；在 on 模式下則拒絕啟動。

這裡藏著一個常見的除錯陷阱：auto 模式會把 lifespan 程式裡的**真正 bug** 也解讀成「不支援」。例如 startup 裡打錯變數名稱丟出 `NameError`，server 照樣啟動，直到第一個請求去拿連線池才爆炸。生產環境建議明確使用 `--lifespan on`。另外，lifespan 是**每個 process 一次**：`uvicorn --workers 4` 會有 4 個 process、各自執行一次 startup、各自建一個連線池，估算資料庫連線數時要乘上 worker 數。

## 42.8 分層：uvicorn、Starlette、FastAPI

小晴寫的 FastAPI 程式只有幾十行，但一個 WebSocket 訊息從網卡走到那幾十行，中間經過好幾層，每一層都可以替換。理解分層，才知道一個問題該去哪一層找。

```text
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ 你的程式：@app.websocket("/ws/classroom/{course_id}")、@app.get("/teachers")  │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ FastAPI（framework）：參數解析與驗證（Pydantic）、dependency injection、      │
 │                       OpenAPI 文件、把 def／async def 分派到正確的執行位置    │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ Starlette（ASGI toolkit）：routing、Request／Response／WebSocket 物件、        │
 │                StreamingResponse、middleware、lifespan、TestClient、thread pool│
 ├──────────────────────── ASGI：scope／receive／send ───────────────────────────┤
 │ uvicorn（ASGI server）：                                                      │
 │   HTTP 解析：h11（純 Python）或 httptools（llhttp 的 C 綁定）                  │
 │   WebSocket：websockets 或 wsproto；ping／pong、frame、交握                    │
 │   event loop：asyncio 預設 loop 或 uvloop（建在 libuv 上）                     │
 │   process 管理：--workers、訊號處理、graceful shutdown                        │
 ├──────────────────────────────────────────────────────────────────────────────┤
 │ 作業系統：socket、epoll／kqueue、TCP（第 10、11 章）                           │
 └──────────────────────────────────────────────────────────────────────────────┘
```

由下往上讀。最底層是作業系統，第 10、11 章的 TCP 狀態都在這裡。**uvicorn** 是 ASGI server，地位相當於 WSGI 世界的 gunicorn 加上 Werkzeug 的 dev server：它 listen socket、解析 HTTP、處理 WebSocket 協定，把結果變成 ASGI 事件。它的三個核心元件都可以替換：HTTP 解析器可以選純 Python 的 **h11**（一個 sans-I/O 函式庫，只負責「bytes 進、事件出」，不碰 socket）或速度較快的 **httptools**（Node.js 的 llhttp 解析器的 Python 綁定）；event loop 可以選標準的 asyncio 或 **uvloop**（用 Cython 寫、建在 libuv 上的 asyncio 替代實作）。用 `pip install "uvicorn[standard]"` 安裝時會一起裝上 httptools、uvloop（非 Windows 平台）與 websockets，`--http auto`、`--loop auto` 會自動選用它們。

ASGI 那條線以上是 app 的世界。**Starlette** 是一個輕量的 ASGI toolkit，提供 routing、Request 與 Response 物件、WebSocket 包裝、middleware 與 lifespan 的寫法；角色類似 WSGI 世界的 Werkzeug（第 41 章），本身也能直接當框架用。**FastAPI** 建在 Starlette 之上，加上型別註記宣告參數、Pydantic 驗證、dependency injection 與自動產生的 OpenAPI 文件；它的 `Request`、`WebSocket`、`StreamingResponse` 與 middleware 其實都是 Starlette 的。

| 層 | 聲聲 Live 用的 | 負責的事 | 可替換成 | 出問題時的典型症狀 |
|---|---|---|---|---|
| ASGI server | uvicorn | socket、HTTP／WebSocket 協定、event loop、process | Hypercorn、Daphne、Granian、gunicorn 的 ASGI worker | 連線被拒、keep-alive 斷線、WebSocket 心跳逾時 |
| HTTP 解析 | httptools | bytes → 請求事件 | h11 | 400 Bad Request、header 過大 |
| event loop | uvloop | 排程 coroutine、等待 I/O | asyncio 預設 loop | 全部請求同時變慢（通常是 app 阻塞，不是 loop 本身） |
| ASGI toolkit | Starlette | routing、Request／Response、middleware | 直接寫 ASGI、其他 toolkit | 404、middleware 順序錯誤 |
| framework | FastAPI | 參數驗證、DI、OpenAPI | Starlette 本身、Litestar、Django（ASGI 模式） | 422 驗證錯誤、dependency 錯誤 |

下面是三層各自的「真實長相」。這幾段程式依賴第三方套件，無法在本書的離線環境執行，標為 not-runnable；請對照前面自己寫的事件，看框架替你做了什麼。

```python
# not-runnable：需要安裝 Starlette
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route


async def teacher(request):
    name = request.path_params["name"]            # 來自 scope["path"] 的路由比對
    return JSONResponse({"name": name})            # 自動送出 http.response.start（含 content-length）與 body


async def history(request):
    async def rows():
        for i in range(1, 4):
            yield f"msg {i}\n"                     # 每個 yield 變成一個 more_body=True 的 body 事件
    return StreamingResponse(rows(), media_type="text/plain")


app = Starlette(routes=[Route("/teachers/{name}", teacher), Route("/chat/history", history)])
```

`JSONResponse` 先算好長度，所以 start 事件帶 `content-length`；`StreamingResponse` 把每次 `yield` 變成一個 `more_body: True` 的 body 事件，uvicorn 在 HTTP/1.1 上就用 chunked 送出，和 42.5 節的課表 app 完全一樣。

```python
# not-runnable：需要安裝 FastAPI
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rooms = {}                          # yield 之前 = lifespan.startup
    yield
    app.state.rooms.clear()                       # yield 之後 = lifespan.shutdown


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws/classroom/{course_id}")
async def classroom(websocket: WebSocket, course_id: int):
    if websocket.headers.get("origin") != "https://www.shengsheng.example":
        await websocket.close(code=1008)          # accept 之前 close → 交握以 403 結束
        return
    await websocket.accept(subprotocol="ss-chat.v1")  # 送出 websocket.accept
    try:
        while True:
            text = await websocket.receive_text()   # 等 websocket.receive 事件
            await websocket.send_text(f"[{course_id}] {text}")
    except WebSocketDisconnect as exc:              # 收到 websocket.disconnect
        print("left with code", exc.code)
```

FastAPI 的 lifespan 是一個 async context manager：`yield` 之前在 `lifespan.startup` 時執行，之後在 `lifespan.shutdown` 時執行。WebSocket handler 則一一對應 42.6 節的事件，`websocket.disconnect` 被轉成 `WebSocketDisconnect` 例外。

```bash
# 示意：在 gw-41（10.20.1.41）上啟動即時服務（真實部署細節見第 43 章）
uvicorn rt.main:app --host 10.20.1.41 --port 8001 --workers 2 \
    --lifespan on --proxy-headers --forwarded-allow-ips 10.20.2.11,10.20.2.12,10.20.2.13
```

`rt.main:app` 是「模組路徑:變數名稱」；`--workers 2` 開兩個 process，各有自己的 event loop 與 lifespan；`--proxy-headers` 搭配 `--forwarded-allow-ips`，只信任三台 nginx 送來的 `X-Forwarded-*`，據此改寫 scope 的 `client` 與 `scheme`（信任邊界同第 25 章）。幾個相關預設值：keep-alive 閒置逾時 5 秒、WebSocket 每 20 秒 ping 一次且 20 秒等不到 pong 就斷線、單則 WebSocket 訊息上限 16 MiB；數字依版本可能調整，部署前以所用版本的文件為準。

> [!note] 2026 現況
> 依 2026 年 10 月查證：ASGI core 版本仍是 3.0，HTTP 與 WebSocket 子規格為 2.5（2024 年發布，加入 WebSocket disconnect 的 `reason`）。uvicorn 最新版為 0.54.0，要求 Python 3.10 以上，仍是 0.x 版號；它支援 HTTP/1.1 與 WebSocket，不支援 HTTP/2，需要 HTTP/2 或 HTTP/3 的 ASGI 服務可考慮 Hypercorn 或 Granian（依知識，未逐一查證）。gunicorn 傳統上以 WSGI 為主，新版也支援 ASGI：24.0 加入內建的 asyncio ASGI worker（beta），25.1 升為 stable，目前最新為 26.2.x；過去常見的「gunicorn 配 `uvicorn.workers.UvicornWorker`」寫法仍可用，但 uvicorn 內建的 workers 模組已被標為 deprecated，改由獨立的 uvicorn-worker 套件提供（依知識）。Starlette 與 FastAPI 的最新版本號本書未查證，使用前請確認。

## 42.9 event loop 被阻塞：async 服務最常見的事故

回到故事第三週。小晴的程式長這樣：

```python
# not-runnable：示意故事中的錯誤寫法（需要 FastAPI 與 requests）
import requests
from fastapi import FastAPI, WebSocket

app = FastAPI()


@app.websocket("/ws/classroom/{course_id}")
async def classroom(websocket: WebSocket, course_id: int):
    await websocket.accept()
    while True:
        text = await websocket.receive_text()
        verdict = requests.post("http://moderation.internal.example/check",   # 同步 HTTP：80 ms 內不交出控制權
                                json={"text": text}, timeout=2).json()
        if verdict["ok"]:
            await websocket.send_text(text)
```

問題出在 `requests.post`。它是同步的：底層用阻塞的 socket，等審查服務回應的 80 毫秒裡，它不會 `await`，也就不會把控制權交還給 event loop。在這 80 毫秒內，loop 不能讀任何 socket、不能送任何訊息、不能回應 ping，也不能回應 LB 的 `/readyz`。同一個 process 裡的三百條 WebSocket 一起被凍住。

```text
 時間 →     0        80       160      240      320      400 ms
 event loop [審查#1 ][審查#2 ][審查#3 ][審查#4 ][審查#5 ]       ← 每段都是阻塞的 requests.post
 學生 A 訊息 ●────────► 送出（80 ms）
 學生 B 訊息 ●─────────────────► 送出（160 ms）
 學生 E 訊息 ●─────────────────────────────────────────► 送出（400 ms）
 /readyz     ●──────────────────────────────────────────► 回應（約 400 ms）
 ping／pong  ●──────────────────────────────────────────► 延遲

 改成 await asyncio.to_thread(審查)：
 event loop  [·][·][·][·][·]·····························  ← 只做分派，立刻空出來
 thread pool [審查#1 ]
             [審查#2 ]   （五個 thread 同時在等審查服務）
             [審查#5 ]
 學生 A～E   ●────────► 全部約 80 ms 送出；/readyz 立刻回應
```

上半部是阻塞時的時間軸：五則訊息幾乎同時到達，但 loop 一次只能做一件阻塞的事，第五則要等前四次審查都做完，延遲是 400 毫秒；`/readyz` 根本沒有阻塞的工作，卻也要等 400 毫秒。用故事的數字算：每秒 30 則 × 80 毫秒＝每秒 2.4 秒的阻塞，event loop 的「使用率」是 240%，超過 100% 之後佇列只會無限增長，延遲從幾百毫秒一路上升到好幾秒，直到 LB 的 health check 逾時（第 25 章的設定是 timeout 2 秒、連續 2 次失敗就移出）。下半部是修正後：審查被丟進 thread pool，loop 只做分派就立刻空出來處理其他事件，五個審查在五個 thread 裡同時等待，每則訊息都只花 80 毫秒。

### 哪些東西會阻塞 event loop

| 類別 | 例子 | 為什麼阻塞 | 正確做法 |
|---|---|---|---|
| 同步網路 I/O | `requests`、同步的資料庫 driver、`urllib.request`、`socket.recv` | 阻塞的系統呼叫，等待期間不交出控制權 | 換成 async 函式庫（例如 httpx 的 async client、asyncpg）；暫時用 `to_thread` |
| 睡眠 | `time.sleep(1)` | 讓整個執行緒睡著 | `await asyncio.sleep(1)` |
| CPU 密集計算 | bcrypt／argon2 雜湊、圖片縮放、大型 JSON 序列化、PDF 產生 | 純計算沒有 await 點 | `to_thread`（若函式庫會釋放 GIL）或 `ProcessPoolExecutor` |
| 檔案 I/O | 讀寫大檔案、`open().read()` 一個上百 MB 的錄影 | 一般檔案的讀寫在 asyncio 中是阻塞的 | `to_thread`，或交給 nginx 直接送檔（第 21 章） |
| 隱藏的同步呼叫 | 同步的 logging handler 寫到網路、第三方 SDK 內部用 requests | 看不出來，要 profile 才知道 | 用 loop lag 監測找出來 |

**`run_in_executor` 與 `to_thread`** 是把阻塞函式移出 event loop 的標準工具。`loop.run_in_executor(None, func, *args)` 把函式交給 loop 預設的 `ThreadPoolExecutor`（上限 `min(32, CPU 數 + 4)` 個 thread），回傳可以 await 的 future；Python 3.9 加入的 `asyncio.to_thread(func, *args)` 更方便，還會把 contextvars（例如 request id）帶進 thread。Starlette 與 FastAPI 另有自己的 thread pool：寫成一般 `def` 的 endpoint 會被自動丟進去執行（預設上限約 40 個 thread，由 anyio 決定），`async def` 的則直接在 event loop 上跑。

這帶出 FastAPI 最反直覺的規則：**handler 裡有同步阻塞呼叫時，寫成 `def` 反而比 `async def` 安全**。`def` 的阻塞只佔一個 thread，`async def` 裡的 `requests.post` 卻阻塞整個 event loop。

> [!warning] 常見誤解
> 「丟進 thread pool 就沒事了」只對 I/O 等待成立。純 Python 的 CPU 計算在 thread 裡仍要和 event loop 搶 GIL，loop 會斷斷續續，這類工作應交給 `ProcessPoolExecutor` 或獨立的背景服務。thread pool 也有上限，下游變慢時工作會在 pool 裡堆積，所以呼叫下游仍要設 timeout。

### 怎麼發現 loop 被阻塞

阻塞的症狀很有辨識度：**所有請求同時變慢，連完全不做事的 endpoint 也一樣慢**，CPU 卻不一定高。三個工具可以把它量出來。第一是 **loop lag**（事件迴圈延遲）：一個背景 task 每 10 毫秒醒來一次，記錄「實際醒來的時間比預期晚了多少」，正常應該接近 0，被阻塞時會跳到阻塞的長度；把它當成一個監控指標，比任何 CPU 圖都準。第二是 asyncio 的 **debug 模式**（`asyncio.run(..., debug=True)` 或環境變數 `PYTHONASYNCIODEBUG=1`），任何一次執行超過 `loop.slow_callback_duration`（預設 0.1 秒）的 callback 都會被記一行 `Executing <Task …> took 0.104 seconds`，直接指出是哪個 task。第三是取樣式 profiler，對正在跑的 process 取 stack，看 loop 執行緒停在哪個函式。動手做的實驗二會把前兩種都實際跑一次。

## 42.10 ASGI middleware：包住 app 的 app

**middleware** 是夾在 server 與 app 之間、對每個請求都會執行的程式，用來做 request id、存取紀錄、壓縮、body 大小限制、驗證等橫切的工作。在 ASGI 裡，middleware 的定義簡單到令人意外：**它本身就是一個 ASGI app，建構時接收另一個 ASGI app**。它可以改寫 scope、包住 receive 來檢查或修改進來的事件、包住 send 來檢查或修改出去的事件，最後呼叫內層的 app。

```text
            請求方向 ──────────────────────────────────────────►
 server ─► ┌ request_id ─────────────────────────────────────────┐
           │  包住 send：在 http.response.start 加 x-request-id  │
           │ ┌ body_limit ───────────────────────────────────┐   │
           │ │  包住 receive：累計 body 大小，超過就回 413    │   │
           │ │ ┌ upload_app ─────────────────────────────┐   │   │
           │ │ │  await receive() … await send(…)        │   │   │
           │ │ └─────────────────────────────────────────┘   │   │
           │ └───────────────────────────────────────────────┘   │
           └─────────────────────────────────────────────────────┘
            ◄────────────────────────────────────────── 回應方向
```

這是一個洋蔥結構。請求從最外層往內走：每一層 middleware 拿到 scope，決定要不要往內呼叫；app 的 `receive()` 實際上會穿過每一層包裝過的 receive，app 的 `send()` 也會穿過每一層包裝過的 send 才到 server。順序因此很重要：`request_id` 放在最外層，連 `body_limit` 直接回的 413 都會帶上 request id；如果反過來，被擋下的請求就沒有 id，查 log 時對不起來。

寫 ASGI middleware 有三條規則。第一，**不認得的 scope type 原樣放行**：lifespan 與 websocket 也會經過 middleware，只處理 http 的 middleware 必須把其他 scope 直接交給內層，否則 lifespan 會壞掉、WebSocket 會連不上。第二，**用包住 receive／send 的方式串流處理**，不要把整個 body 讀進記憶體再交給內層，否則就失去了 ASGI 的串流能力，也讓大檔案上傳變成記憶體炸彈。第三，**回應開始之後就不能改 status**：`http.response.start` 一旦送出，status 和 header 已經在線上了，middleware 只能在攔截 start 事件時修改它們。

```python
import asyncio
import itertools

trace = []


def logged(name, app):
    """最外層的觀察者：記下事件穿過每一層的順序。"""
    async def wrapper(scope, receive, send):
        trace.append(f"→ {name}")
        await app(scope, receive, send)
        trace.append(f"← {name}")
    return wrapper


def request_id(app):
    ids = itertools.count(1001)

    async def middleware(scope, receive, send):
        if scope["type"] != "http":                 # lifespan／websocket 不認得就原樣放行
            return await app(scope, receive, send)
        rid = f"r{next(ids)}".encode()

        async def send_with_id(message):            # 包住 send：改寫要送出去的事件
            if message["type"] == "http.response.start":
                message = {**message, "headers": [*message.get("headers", []), (b"x-request-id", rid)]}
            await send(message)
        await app(scope, receive, send_with_id)
    return middleware


def body_limit(app, max_bytes):
    async def middleware(scope, receive, send):
        if scope["type"] != "http":
            return await app(scope, receive, send)
        seen = 0

        async def limited_receive():                 # 包住 receive：邊收邊數，不先整包讀進記憶體
            nonlocal seen
            event = await receive()
            if event["type"] == "http.request":
                seen += len(event.get("body", b""))
                if seen > max_bytes:
                    raise OverflowError
            return event
        try:
            await app(scope, limited_receive, send)
        except OverflowError:                        # 假設 app 尚未開始回應（真實實作要追蹤這件事）
            await send({"type": "http.response.start", "status": 413,
                        "headers": [(b"content-length", b"0")]})
            await send({"type": "http.response.body", "body": b""})
    return middleware


async def upload_app(scope, receive, send):
    total = 0
    while True:
        event = await receive()
        total += len(event["body"])
        if not event["more_body"]:
            break
    body = f"saved {total} bytes".encode()
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


async def call(app, chunks):
    events = [{"type": "http.request", "body": c, "more_body": i < len(chunks) - 1}
              for i, c in enumerate(chunks)]
    sent = []

    async def receive():
        return events.pop(0)

    async def send(message):
        sent.append(message)
    await app({"type": "http", "method": "POST", "path": "/upload", "headers": []}, receive, send)
    start, body = sent[0], b"".join(m.get("body", b"") for m in sent[1:])
    return start["status"], dict(start["headers"]).get(b"x-request-id"), body


# 洋蔥：request_id 在最外層，所以連 413 回應也會帶上 request id
stack = logged("request_id", request_id(logged("body_limit", body_limit(
    logged("upload_app", upload_app), max_bytes=1_000_000))))


async def main():
    small = await call(stack, [b"a" * 400_000, b"b" * 400_000])
    print("800 KB  →", small)
    print("        穿過順序：", " ".join(trace))
    big = await call(stack, [b"a" * 600_000, b"b" * 600_000, b"c" * 600_000])
    print("1.8 MB  →", big)
    assert small[0] == 200 and big[0] == 413 and big[1] == b"r1002"


asyncio.run(main())
```

```text
800 KB  → (200, b'r1001', b'saved 800000 bytes')
        穿過順序： → request_id → body_limit → upload_app ← upload_app ← body_limit ← request_id
1.8 MB  → (413, b'r1002', b'')
```

第一行是 800 KB 的正常上傳：兩個 body 事件共 800,000 bytes，沒超過 1,000,000 的上限，app 回 200，而且回應帶有最外層加上的 `x-request-id: r1001`。第二行印出穿過的順序，正好是洋蔥圖：進去時 request_id → body_limit → upload_app，出來時倒過來。第三行是 1.8 MB 的上傳：第二個事件讀進來時累計 1,200,000 bytes 就超過上限，`limited_receive` 丟出例外，body_limit 回 413；第三個 600 KB 的事件根本沒被讀取。最重要的是 413 回應也帶著 `r1002`，因為 request_id 在更外層。

這段程式為了簡短，假設超過上限時 app 還沒開始回應；真實的 middleware 要追蹤 start 是否已送出，已送出就只能中止連線。Starlette 提供方便的 `BaseHTTPMiddleware`（`dispatch(request, call_next)` 形式），但它在串流、背景工作與 contextvars 傳遞上有已知限制，敏感的場合建議寫成本節這種純 ASGI middleware。另外，Starlette 的 `middleware=[Middleware(A), Middleware(B)]` 清單是由外到內，FastAPI 的 `app.add_middleware()` 則每次加在最外層，兩者順序相反。

```python
# not-runnable：Starlette 的純 ASGI middleware 寫法（需要 Starlette）
from starlette.applications import Starlette
from starlette.middleware import Middleware


class RequestIdMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        incoming = dict(scope["headers"]).get(b"x-request-id")   # 優先沿用 nginx 帶來的 id

        async def send_wrapper(message):
            if message["type"] == "http.response.start" and incoming:
                message["headers"] = [*message.get("headers", []), (b"x-request-id", incoming)]
            await send(message)
        await self.app(scope, receive, send_wrapper)


app = Starlette(middleware=[Middleware(RequestIdMiddleware)])
```

這個版本示範了聲聲 Live 的實際規則：`x-request-id` 由 nginx 產生，用來串接 nginx 與後端的 log，所以 middleware 優先沿用請求帶來的值，而不是自己產生一個新的。注意它只有在 nginx 確實會覆寫這個 header 時才安全，否則外部使用者可以塞任意值進你的 log，信任邊界的道理同第 25 章的 X-Forwarded-For。

## 42.11 動手做：從零寫一個最小 ASGI server

這一節把整章串起來：在 127.0.0.1 上寫一個真的會 listen 的 ASGI server，再重現故事第三週的事故並用 `to_thread` 修好。

### 實驗一：ASGI server、app 與 lifespan

這段程式分成三塊。server 端的 `serve_one()` 從 socket 讀一個 HTTP/1.1 請求，組出 scope，提供 receive 與 send：receive 依 Content-Length 每次最多讀 16 KB 包成 `http.request` 事件；send 把 start 事件變成狀態行與 header，沒有 content-length 就加上 chunked，再把 body 事件編成 chunk。`run_lifespan()` 在 listen 之前跑完 lifespan startup。app 端完全不碰 socket，有三個路由：`/teachers/<名字>` 回 JSON（固定長度）、`/chat/history` 串流三則訊息、`/upload` 分多次讀取 body。最後的 client 在同一條 keep-alive 連線上連發三個請求。

```python
import asyncio
import json
from urllib.parse import unquote

READ_CHUNK = 16 * 1024                    # 每個 http.request 事件最多帶多少 body
REASONS = {200: "OK", 404: "Not Found", 500: "Internal Server Error"}


# ─────────────── server 端：把 bytes 翻譯成 ASGI 事件，再把事件翻譯回 bytes ───────────────
async def serve_one(app, reader, writer, state):
    try:
        head = await reader.readuntil(b"\r\n\r\n")
    except asyncio.IncompleteReadError:
        return None                            # client 關掉了閒置的 keep-alive 連線
    lines = head[:-4].decode("latin-1").split("\r\n")
    method, target, version = lines[0].split(" ")
    headers = [(n.strip().lower().encode(), v.strip().encode())
               for n, _, v in (line.partition(":") for line in lines[1:])]
    hmap = dict(headers)
    keep_alive = hmap.get(b"connection", b"").lower() != b"close"
    remaining = int(hmap.get(b"content-length", b"0"))
    raw_path, _, query = target.partition("?")
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.5"},
             "http_version": version.removeprefix("HTTP/"), "method": method, "scheme": "http",
             "path": unquote(raw_path), "raw_path": raw_path.encode(), "query_string": query.encode(),
             "root_path": "", "headers": headers, "client": writer.get_extra_info("peername")[:2],
             "server": writer.get_extra_info("sockname")[:2], "state": state.copy()}
    finished, sent_first = asyncio.Event(), False
    resp = {"started": False, "chunked": False}

    async def receive():
        nonlocal remaining, sent_first
        if remaining or not sent_first:
            sent_first = True
            data = await reader.readexactly(min(remaining, READ_CHUNK))
            remaining -= len(data)
            return {"type": "http.request", "body": data, "more_body": remaining > 0}
        await finished.wait()                  # body 讀完還要 receive：回應結束後回報 disconnect
        return {"type": "http.disconnect"}

    async def send(msg):
        if msg["type"] == "http.response.start":
            hdrs = list(msg.get("headers", []))
            resp["chunked"] = all(n != b"content-length" for n, _ in hdrs)
            if resp["chunked"]:                # app 沒給長度 → server 決定用 chunked
                hdrs.append((b"transfer-encoding", b"chunked"))
            line = f"HTTP/1.1 {msg['status']} {REASONS.get(msg['status'], '')}\r\n".encode()
            writer.write(line + b"".join(n + b": " + v + b"\r\n" for n, v in hdrs) + b"\r\n")
            resp["started"] = True
        elif msg["type"] == "http.response.body":
            body, more = msg.get("body", b""), msg.get("more_body", False)
            if resp["chunked"]:
                writer.write((b"%x\r\n%s\r\n" % (len(body), body) if body else b"")
                             + (b"" if more else b"0\r\n\r\n"))   # 0 長度 chunk = 結束
            else:
                writer.write(body)
            await writer.drain()               # 背壓：client 讀得慢，app 的 send 就會等
            if not more:
                finished.set()

    try:
        await app(scope, receive, send)
    except Exception:
        if resp["started"]:
            return False                       # header 已送出，只能斷線
        await send({"type": "http.response.start", "status": 500,
                    "headers": [(b"content-length", b"0")]})
        await send({"type": "http.response.body", "body": b""})
    if remaining:                              # app 沒讀完 body：讀掉，下一個請求才對得齊
        await reader.readexactly(remaining)
    return keep_alive and finished.is_set()


async def run_lifespan(app, state):
    inbox, outbox = asyncio.Queue(), asyncio.Queue()
    scope = {"type": "lifespan", "asgi": {"version": "3.0"}, "state": state}
    task = asyncio.create_task(app(scope, inbox.get, outbox.put))

    async def phase(name):
        await inbox.put({"type": f"lifespan.{name}"})
        reply = await outbox.get()
        assert reply["type"] == f"lifespan.{name}.complete", reply
    return task, phase


# ─────────────── app 端：只認得 scope／receive／send，完全不碰 socket ───────────────
async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            event = await receive()
            if event["type"] == "lifespan.startup":
                scope["state"]["teachers"] = ["美咲", "Daniel"]   # 例如：建立連線池、載入設定
                print("[lifespan] startup：載入老師名單，開始接受連線")
                await send({"type": "lifespan.startup.complete"})
            elif event["type"] == "lifespan.shutdown":
                print("[lifespan] shutdown：關閉連線池")
                await send({"type": "lifespan.shutdown.complete"})
                return
    if scope["path"].startswith("/teachers/"):            # path 已解碼成 str；raw_path 保留原樣
        name = scope["path"].removeprefix("/teachers/")
        body = json.dumps({"name": name, "listed": name in scope["state"]["teachers"]},
                          ensure_ascii=False).encode()
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
    elif scope["path"] == "/chat/history":   # 串流：邊查邊送，事先不知道總長度
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
        for i in range(1, 4):
            await asyncio.sleep(0.01)
            await send({"type": "http.response.body", "body": f"msg {i}\n".encode(), "more_body": True})
        await send({"type": "http.response.body", "body": b""})
    elif scope["path"] == "/upload":
        size, events = 0, 0
        while True:
            event = await receive()
            size, events = size + len(event["body"]), events + 1
            if not event["more_body"]:
                break
        body = f"got {size} bytes in {events} http.request events".encode()
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
    else:
        await send({"type": "http.response.start", "status": 404, "headers": [(b"content-length", b"0")]})
        await send({"type": "http.response.body", "body": b""})


# ─────────────── client：用 raw bytes 在同一條 keep-alive 連線上發三個請求 ───────────────
async def read_response(reader):
    head = (await reader.readuntil(b"\r\n\r\n")).decode()
    status = head.split(" ", 2)[1]
    hdrs = {k.lower(): v for k, _, v in (l.partition(": ") for l in head.split("\r\n")[1:] if l)}
    if "content-length" in hdrs:
        return status, hdrs, await reader.readexactly(int(hdrs["content-length"])), None
    body, sizes = b"", []
    while (size := int((await reader.readline()).strip(), 16)) > 0:
        sizes.append(size)
        body += (await reader.readexactly(size + 2))[:-2]
    await reader.readline()                    # last-chunk 後的空行
    return status, hdrs, body, sizes


async def main():
    state, served = {}, []
    life_task, phase = await run_lifespan(app, state)
    await phase("startup")                     # startup 完成之前不 listen

    async def on_conn(reader, writer):
        n = 0
        while (keep := await serve_one(app, reader, writer, state)) is not None:
            n += 1
            if not keep:
                break
        served.append(n)
        writer.close()

    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    reader, writer = await asyncio.open_connection(host, port)
    upload = b"x" * 40_000
    for req in (b"GET /teachers/%E7%BE%8E%E5%92%B2 HTTP/1.1\r\nHost: rt.shengsheng.example\r\n\r\n",
                b"GET /chat/history HTTP/1.1\r\nHost: rt.shengsheng.example\r\n\r\n",
                b"POST /upload HTTP/1.1\r\nHost: rt.shengsheng.example\r\nConnection: close\r\n"
                b"Content-Length: %d\r\n\r\n%s" % (len(upload), upload)):
        writer.write(req)
        status, hdrs, body, sizes = await read_response(reader)
        framing = f"chunks={sizes}" if sizes else f"content-length={hdrs['content-length']}"
        print(f"{unquote(req.split(b' ')[1].decode()):<14} {status}  {framing:<22} body={body.decode()!r}")
    writer.close()
    server.close()
    await server.wait_closed()
    await phase("shutdown")
    await life_task
    print(f"連線數={len(served)}，這條連線服務了 {served[0]} 個請求")
    assert served == [3]


asyncio.run(main())
```

```text
[lifespan] startup：載入老師名單，開始接受連線
/teachers/美咲   200  content-length=34      body='{"name": "美咲", "listed": true}'
/chat/history  200  chunks=[6, 6, 6]       body='msg 1\nmsg 2\nmsg 3\n'
/upload        200  content-length=40      body='got 40000 bytes in 3 http.request events'
[lifespan] shutdown：關閉連線池
連線數=1，這條連線服務了 3 個請求
```

逐行對照前面的規格。第 1 行是 lifespan startup：server 先送 `lifespan.startup`，app 載入老師名單、放進 state、回 complete，server 這時才呼叫 `start_server` 開始 listen。第 2 行的請求路徑在線上是 `/teachers/%E7%BE%8E%E5%92%B2`，scope 的 `path` 已經解碼成「美咲」，app 用它比對名單；app 自己算了長度，所以回應走 `content-length=34`（「美咲」在 UTF-8 是 6 bytes）。第 3 行的 `/chat/history` 沒給長度，server 改用 chunked，client 解析出三個 6 bytes 的 chunk，每個對應 app 的一次 `more_body: True`。

第 4 行驗證了請求方向的串流：40,000 bytes 的 body 被 server 切成 16384、16384、7232 三個 `http.request` 事件，app 在迴圈裡讀到 `more_body` 為 False 才停。第 5 行是 client 送出 `Connection: close` 之後，server 關閉連線、跑 lifespan shutdown。最後一行證明 keep-alive 有效：三個請求只用了一條 TCP 連線，但 app 被呼叫了三次，每次一個新的 scope，這正是 42.4 節說的「HTTP scope 是每個請求一個」。

這個 server 離 production 還很遠：它沒有 header 大小上限與讀取逾時（第 40 章的慢速 client）、不處理 chunked 請求與 HTTP/1.0、沒有拒絕冒號前有空白或重複 Content-Length 的 header（第 20 章的 smuggling 防護）、不支援 WebSocket 升級與 graceful shutdown。這些正是 uvicorn 替你做的事。

### 實驗二：一行阻塞呼叫拖慢所有請求

`moderation_check_sync()` 用 `time.sleep(0.1)` 模擬同步呼叫審查服務；blocking 版直接呼叫它，to_thread 版用 `await asyncio.to_thread()`。每次試驗同時送進 5 則聊天訊息，5 毫秒後 LB 來打 `/readyz`；延遲從「請求抵達」算起，所以排隊等 loop 的時間也算在內。背景的 `lag_monitor` 每 10 毫秒量一次 loop lag，blocking 版另外開啟 asyncio 的 debug 模式。

```python
import asyncio
import logging
import time


def moderation_check_sync(text):
    """模擬同步的內容審查呼叫（例如用 requests 打審查服務），每次 100 ms。"""
    time.sleep(0.1)
    return "ok"


def make_app(mode):
    async def app(scope, receive, send):
        await receive()
        if scope["path"] == "/chat/send":
            if mode == "blocking":
                verdict = moderation_check_sync("hi")                       # 卡住整個 event loop
            else:
                verdict = await asyncio.to_thread(moderation_check_sync, "hi")  # 丟到 thread pool
        else:
            verdict = "alive"                                                # /readyz：什麼都不做
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": verdict.encode()})
    return app


async def call(app, path, arrive_at):
    """記憶體內的迷你 ASGI 驅動：不經過 socket，直接用 scope／receive／send 呼叫 app。
    延遲從「請求抵達」算起，所以排隊等 event loop 的時間也算在內，和使用者感受一致。"""
    await asyncio.sleep(max(0.0, arrive_at - time.perf_counter()))
    scope = {"type": "http", "method": "POST", "path": path, "headers": []}

    async def receive():
        return {"type": "http.request", "body": b"hi", "more_body": False}

    async def send(msg):
        pass
    await app(scope, receive, send)
    return (time.perf_counter() - arrive_at) * 1000


async def lag_monitor(stop, samples):
    """每 10 ms 醒來一次；實際醒來時間比預期晚多少，就是 event loop 被卡住多久。"""
    while not stop.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(0.01)
        samples.append((time.perf_counter() - t0 - 0.01) * 1000)


async def trial(mode):
    app, stop, lag = make_app(mode), asyncio.Event(), []
    monitor = asyncio.create_task(lag_monitor(stop, lag))
    t0 = time.perf_counter()
    chats = [call(app, "/chat/send", t0) for _ in range(5)]      # 5 則聊天訊息同時進來
    health = call(app, "/readyz", t0 + 0.005)                   # 5 ms 後 LB 來做 health check
    *chat_ms, health_ms = await asyncio.gather(*chats, health)
    total = (time.perf_counter() - t0) * 1000
    stop.set()
    await monitor
    print(f"{mode:<9} 全部完成 {total:4.0f} ms｜聊天各自 {[round(m) for m in chat_ms]} ms"
          f"｜readyz {health_ms:3.0f} ms｜loop 最大延遲 {max(lag):3.0f} ms")
    return total, health_ms


class SlowCallbackLog(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        if "took" in record.getMessage():
            self.lines.append(record.getMessage().split(" took ")[-1])


slow = SlowCallbackLog()
logging.getLogger("asyncio").addHandler(slow)
blocking_total, blocking_health = asyncio.run(trial("blocking"), debug=True)  # debug：偵測慢 callback
threaded_total, threaded_health = asyncio.run(trial("to_thread"))
print(f"debug 模式抓到 {len(slow.lines)} 次慢 callback，例如 took {slow.lines[0]}")

assert blocking_total >= 450 and blocking_health >= 100     # 五次 100 ms 依序執行，health 也排隊
assert threaded_total < 300 and threaded_health < 50        # 審查在 thread 裡並行，loop 保持暢通
assert slow.lines
```

```text
blocking  全部完成  517 ms｜聊天各自 [103, 207, 311, 414, 515] ms｜readyz 511 ms｜loop 最大延遲 506 ms
to_thread 全部完成  107 ms｜聊天各自 [107, 104, 106, 107, 107] ms｜readyz   0 ms｜loop 最大延遲   1 ms
debug 模式抓到 5 次慢 callback，例如 took 0.103 seconds
```

數字每次執行略有不同，但模式固定。第 1 行是阻塞版：五則訊息的延遲是 100、200、300、400、500 毫秒的階梯，因為 loop 一次只能做一件阻塞的事；`/readyz` 本身什麼都不做，卻花了 500 多毫秒，因為它排在五次審查後面；loop lag 的最大值約 500 毫秒，代表 loop 有半秒完全沒有回應。換成故事裡每秒 30 則、每則 80 毫秒，就是持續增長的延遲與逾時的 health check。

第 2 行是 to_thread 版：五則訊息都在 100 毫秒多一點完成，因為五個審查在 thread pool 裡同時等待；`/readyz` 幾乎是 0 毫秒，loop lag 只有 1 毫秒左右（偶爾會因為系統排程跳到十幾毫秒）。第 3 行是 debug 模式的輸出：asyncio 抓到 5 次超過 0.1 秒的慢 callback，每次略多於 0.1 秒，正好對應五次阻塞的審查。debug 模式有額外成本，不適合在 production 常開；loop lag 則可以一直開著，它是 ASGI 服務最值得畫在儀表板上的一條線。

## 42.12 在工作上怎麼用

事故檢討後，阿德與小晴把 ASGI 服務的注意事項依角色整理成清單。

**後端工程師：每寫一個 handler，先問「這裡面有沒有阻塞呼叫」。** I/O 全是 await 的 async 函式庫，就寫 `async def`；有同步 I/O（舊 SDK、`requests`、同步 ORM），就寫成 `def` 或用 `to_thread` 包住；CPU 重活交給 process pool 或背景工作。審查時看到 `async def` 裡出現 `requests.`、`time.sleep`、同步 driver，就該提問。共享資源（連線池、HTTP client）在 lifespan 建一次，不要每個請求新建，否則會重演第 10 章的 TIME_WAIT 問題。

**SRE：把 ASGI 特有的訊號加進監控。** 三個指標：loop lag（p99 超過幾十毫秒就該查）、每個 process 的 WebSocket 連線數（第 33 章）、thread pool 使用量。timeout 鏈要對齊：nginx 的 `proxy_read_timeout`（預設 60 秒，聲聲 Live 的 `/ws/` 設 75 秒，第 32 章）要長於心跳間隔（uvicorn 預設每 20 秒 ping，應用層心跳 25 秒），心跳才能讓閒置連線活著；uvicorn 的 keep-alive 預設只有 5 秒，比 nginx 對 upstream 保留閒置連線的時間短，會出現第 10 章 Q5 的「upstream prematurely closed connection」，所以第 43 章把 uvicorn 的 `--timeout-keep-alive` 調成 75 秒、nginx upstream 的 `keepalive_timeout` 設 60 秒。完整推導在第 43 章。

```bash
# 示意：在即時服務主機上快速檢查
ss -tn state established '( sport = :8001 )' | wc -l     # 目前的連線數（大多是 WebSocket）
ss -ltn 'sport = :8001'                                  # accept queue：Recv-Q 不是 0 代表 loop 忙到 accept 不及
py-spy dump --pid <uvicorn worker pid>                   # 取樣 stack：loop 執行緒停在哪個函式（需要安裝 py-spy）
curl -s -o /dev/null -w '%{time_total}\n' http://10.20.1.41:8001/readyz   # 不做事的端點也慢 = loop 被阻塞
```

判斷邏輯是：`/readyz` 這種不做事的端點也慢，幾乎一定是 event loop 被阻塞；`py-spy dump` 會顯示 loop 執行緒卡在哪一行，例如 `requests/adapters.py` 的 `send`。accept queue 堆積是同一個訊號：loop 忙到沒空 `accept()`（第 10 章 10.5 節）。

```text
 症狀：ASGI 服務變慢
   │
   ├─ 不做事的端點（/readyz）也慢？
   │     ├─ 是 ─► event loop 被阻塞：看 loop lag、debug 模式的 slow callback、py-spy
   │     │         └─► 找到阻塞呼叫 → 換 async 函式庫，或 to_thread／def endpoint
   │     └─ 否 ─► 只有特定端點慢：看該端點的下游延遲、thread pool 是否用滿
   │
   ├─ WebSocket 大量同時斷線？
   │     ├─ 同時有 health check 失敗 ─► 多半是 loop 阻塞導致 LB 移出主機
   │     └─ 閒置一段時間後才斷 ─► 中間設備的 idle timeout 比心跳間隔短（第 10、32 章）
   │
   └─ 啟動後第一個請求才爆炸？
         └─► lifespan auto 吞掉了 startup 的例外：改用 --lifespan on，檢查啟動 log
```

流程圖的第一刀最實用：「連不做事的端點都慢」指向 event loop，「只有某些端點慢」指向下游。WebSocket 大量斷線則要對照 health check 與斷線時間點，區分「主機被移出」與「中間設備清掉閒置連線」。

**前端工程師：WebSocket 斷線的錯誤碼要分開處理。** 交握被拒絕時瀏覽器常常只給 1006，分不出「沒權限」與「網路斷了」；可以先呼叫一般的 HTTP API 確認登入狀態，或約定 app 在 accept 之後用 4000 號段的自訂 close code 說明原因（第 32 章）。重連要加隨機退避，否則三百個學生同時重連，會把剛恢復的服務再打垮一次。

**影音工程師：signaling 服務裡不做重活。** Joe 的 WebRTC signaling（交換 SDP 與 ICE candidate，第 36 章）也跑在 ASGI 上，一則 candidate 晚兩秒，視訊就晚兩秒接通；所以錄影轉檔、縮圖一律交給獨立的 worker，loop lag 的告警門檻也設得比聊天服務更嚴。

**資安工程師：ASGI 把幾個檢查點交給了 app。** Rita 的清單：WebSocket 在 accept 前檢查 `Origin` 與身分；限制單則訊息大小與每條連線的訊息速率；在 nginx（`client_max_body_size`）與 middleware 兩層限制 body 大小；`--forwarded-allow-ips` 只列真正的 proxy，否則任何人都能偽造 `X-Forwarded-For`，讓依 IP 的限速失效。

## 42.13 常見錯誤與除錯

下表收錄 ASGI 服務在聲聲 Live 與一般團隊最常見的錯誤。每一列都可以用本章的工具在幾分鐘內確認。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 所有請求同時變慢，連 `/readyz` 也慢，CPU 不一定高 | `async def` 裡有同步阻塞呼叫（`requests`、`time.sleep`、同步 DB driver） | loop lag 指標跳高；debug 模式出現 `took 0.x seconds`；py-spy 看 loop 執行緒的 stack | 換成 async 函式庫；暫時用 `to_thread`；或改寫成 `def` endpoint |
| 服務啟動正常，第一個請求才出現 `AttributeError: … state …` | lifespan startup 丟例外，`--lifespan auto` 把它當成不支援 | 啟動 log 中有 lifespan 相關訊息；用 `--lifespan on` 重啟會直接失敗 | 生產環境用 `--lifespan on`；修正 startup 的 bug |
| WebSocket 交握失敗，瀏覽器只顯示 1006 | app 在 accept 前 close（Origin 或驗證失敗，server 回 403），或 nginx 沒轉送 Upgrade header | 看 uvicorn log 是否有 403；DevTools 看交握回應的 status | 修正 Origin 允許清單或驗證；nginx 設定 `proxy_http_version 1.1` 與 Upgrade／Connection header |
| 串流回應或 SSE 的資料一次才全部出現 | nginx 的 proxy buffering 把 chunk 攢起來，或 app 其實先把全部內容組好才送 | `curl -N` 直連 uvicorn 與經過 nginx 比較 | 對該路徑關閉 buffering（第 31 章）；確認 app 每段都 `send` 了 `more_body: True` |
| 客戶端斷線後，server 還在持續產生串流資料 | app 沒有監聽 `http.disconnect` | log 中出現對已關閉連線的寫入錯誤；連線數下降但 CPU 沒降 | 串流時同時等待 `receive()`；使用框架提供的斷線偵測 |
| middleware 加上後 WebSocket 或 lifespan 壞掉 | middleware 沒有把非 http 的 scope 原樣放行 | 拿掉該 middleware 後恢復正常 | 開頭加 `if scope["type"] != "http": return await app(...)` |
| log 裡的 client IP 全是 nginx 的位址，或被使用者偽造 | 沒開 `--proxy-headers`，或 `--forwarded-allow-ips` 設成 `*` | 比對 nginx access log 與 app log 的 IP | 只信任真正的 proxy 位址（第 25 章的信任清單） |

除錯時的通則是：**先分辨是「loop 的問題」還是「某個請求的問題」**。拿一個不做任何事的端點量延遲，就能一刀切開；loop 的問題看 loop lag 與 stack，某個請求的問題看那個請求的下游。

## 42.14 動手練習

1. **延伸實驗一：加上 http.disconnect 偵測**（延伸本章程式）。替 `/chat/history` 改成每 50 毫秒送一則、共送 100 則的長串流，並在 app 裡用一個背景 task 同時 `await receive()`；client 讀到第 3 則就關閉連線。觀察 server 是否能在 client 離開後停止產生資料。
   答案要點：server 要在讀到 EOF 時設一個 disconnected 事件，receive 才會回傳 `http.disconnect`，app 收到後取消串流迴圈。沒有這個機制，app 會送完 100 則才在 `drain()` 拋錯，這正是 SSE 服務浪費資源的典型原因。

2. **延伸實驗一：限制 header 大小與讀取逾時**（延伸本章程式）。替 `serve_one()` 加上兩個限制：header 超過 8 KB 回 431，3 秒內沒有讀到完整 header 就關閉連線。用一個只送 `GET / HTTP/1.1\r\n` 就不再送任何東西的 client 測試。
   答案要點：用 `asyncio.wait_for(reader.readuntil(...), 3)` 處理逾時，用 `StreamReader` 的 `limit` 或自行累計長度處理上限；這是防禦慢速 client（第 40 章）的基本手段。

3. **找出阻塞呼叫**（真實工具）。在自己的電腦上安裝 uvicorn 與 FastAPI，寫一個 `async def` endpoint 裡面呼叫 `time.sleep(0.5)`，另一個 endpoint 立刻回應。用下面的指令同時打五次 slow，再打一次 fast，觀察 fast 的耗時。再把 slow 改成 `def`，重複一次。

   ```bash
   for i in $(seq 5); do curl -s -o /dev/null -w 'slow %{time_total}\n' 127.0.0.1:8000/slow & done
   curl -s -o /dev/null -w 'fast %{time_total}\n' 127.0.0.1:8000/fast; wait
   ```

   答案要點：`async def` 版本的 fast 端點要等約 2.5 秒；改成 `def` 後 slow 被放進 thread pool，fast 立刻回應。這個實驗直接驗證了 42.9 節「有同步呼叫時 `def` 比 `async def` 安全」的規則。

4. **觀察 WebSocket 交握被拒絕**（真實工具）。用第 3 題的環境寫一個在 accept 前就 `close()` 的 WebSocket endpoint，用瀏覽器 DevTools 的 Network 面板（WS 分頁）連線，再用 curl 手動送一個交握請求，看 HTTP 層的回應：

   ```bash
   curl -i -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
        -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' 127.0.0.1:8000/ws
   ```

   答案要點：curl 會看到 `HTTP/1.1 403 Forbidden`，瀏覽器的 JavaScript 只看到 close code 1006；把 close 移到 accept 之後，curl 會看到 101，之後才收到 close frame。這說明前端為什麼無法從 close code 得知「被拒絕的原因」。

5. **手算：一台主機能撐幾個講座**。即時服務每台主機 2 個 uvicorn worker；每則聊天訊息在 event loop 上的處理時間（解析、驗證、廣播的 CPU 時間）平均 0.4 毫秒，每則訊息要廣播給同教室所有人，每次 send 約 0.02 毫秒。一場 300 人的講座尖峰每秒 30 則訊息。每個 worker 的 loop 使用率是多少？若希望使用率低於 50%，一個 worker 最多同時承載幾場這種講座？
   答案要點：每則訊息 0.4 ＋ 300 × 0.02＝6.4 毫秒；每秒 30 則就是每秒 192 毫秒，使用率 19.2%。50% 的預算是每秒 500 毫秒，可以承載 500 ÷ 192 ≈ 2.6，也就是 2 場。注意廣播的成本與人數成正比，大型講座的瓶頸往往是 fan-out 而不是訊息處理本身，這是第 33 章的主題。

## 本章重點整理

- WSGI 是同步的一次呼叫：請求從頭到尾佔住一個 worker，等待也一樣佔；它沒有 client 離開的通知、沒有 WebSocket、沒有開機關機的標準掛點。
- 長連線讓同時存在的請求數（Little 定律：到達率 × 停留時間）暴增，問題在連線數而不在 CPU；async 讓等待只是一個暫停的 coroutine，一個執行緒就能撐住上萬條閒置連線。
- event loop 是合作式多工：切換只發生在 `await`，所以任何不交出控制權的程式都會讓同一個 process 的所有連線同時停住。
- ASGI app 是 `async def app(scope, receive, send)`：scope 是靜態資訊，receive 與 send 交換以 `"type"` 區分的事件 dict；server 處理 bytes，app 只處理事件。
- HTTP scope 每個請求一個，WebSocket scope 每條連線一個，lifespan scope 每個 process 一個；一條 keep-alive 連線上的三個請求會呼叫 app 三次。
- HTTP 的 body 以一個或多個 `http.request` 事件送進來，回應以一次 `http.response.start` 加上一或多個 `http.response.body` 送出，`more_body` 決定是否還有下一段；回應結束或 client 斷線後 receive 回傳 `http.disconnect`。
- Content-Length 或 chunked 是 server 依 app 是否給長度、以及 HTTP 版本決定的；app 不應自己送 `transfer-encoding`。
- WebSocket over ASGI 的流程是 connect → accept → receive／send → disconnect；交握、frame、ping／pong 都由 server 處理；在 accept 前 close 會讓 server 回 403，Origin 與身分檢查必須在 accept 之前完成。
- lifespan 讓 app 在接客前建立共享資源、在關機時清理；startup.failed 會讓 server 拒絕啟動，app 丟例外則在 auto 模式下被當成不支援，生產環境應使用 `--lifespan on`。
- uvicorn 是 ASGI server（HTTP 解析可選 h11 或 httptools、event loop 可選 asyncio 或 uvloop），Starlette 是 ASGI toolkit，FastAPI 是建在 Starlette 上的 framework；問題要依層次去找。
- 阻塞 event loop 的典型來源是同步網路 I/O、`time.sleep`、CPU 密集計算與檔案 I/O；修法是換 async 函式庫、`asyncio.to_thread`／`run_in_executor`，或在 FastAPI 中寫成 `def` endpoint 交給 thread pool；CPU 重活用 process pool。
- loop lag 與 asyncio debug 模式的 slow callback 是發現阻塞的主要工具；「連不做事的端點都慢」是 loop 被阻塞的招牌症狀。
- ASGI middleware 本身就是包住另一個 app 的 ASGI app：包住 receive 檢查進來的事件、包住 send 修改出去的事件，必須放行不認得的 scope，並注意洋蔥的順序。

## 延伸問答

> [!question]- Q1. 把一個 Flask 服務原封不動地改用 uvicorn 加上 WSGI 轉 ASGI 的轉接層來跑，效能會變好嗎？
> 通常不會，甚至可能略差。轉接層（例如 asgiref 的 WsgiToAsgi 或 a2wsgi）的做法是把每個請求丟進 thread pool，在 thread 裡呼叫同步的 WSGI app，因為 WSGI app 本身是同步的，不可能在 event loop 上直接執行。於是每個請求仍然佔住一個 thread，等待時依然佔資源，和 gunicorn 的 gthread worker 本質相同，只是多了一層事件與 environ 之間的轉換。
>
> 這種轉接的價值不在效能，而在**共存**：同一個 ASGI 服務裡，新的 WebSocket 與串流功能用原生 ASGI 寫，舊的 Flask 頁面透過轉接層掛在某個子路徑下，讓團隊可以逐步遷移。想真正受益於 async，handler 內部的 I/O 必須是可以 await 的；只換 server 而不換 app 的呼叫模型，等待的成本不會消失。
>
> 故事裡的團隊也是這樣取捨：既有的 Flask 網站繼續跑在 gunicorn 上，只把會產生長連線的聊天拆成原生的 ASGI 服務，兩邊由 nginx 依路徑分流，而不是把整個網站搬到 uvicorn。

> [!question]- Q2. 看 log 找原因：即時服務每隔幾分鐘就出現一次「所有 WebSocket 訊息延遲約 1.5 秒」，之後自動恢復，CPU 使用率始終低於 30%。你會怎麼查？
> 「所有連線同時變慢、之後自動恢復」強烈指向 event loop 在那段時間被某個東西阻塞了大約 1.5 秒，而不是網路或下游的普遍變慢；CPU 低也不能排除，因為阻塞的 I/O 等待不吃 CPU。第一步是看 loop lag 指標，確認峰值是否與延遲事件同時出現、大小約 1.5 秒；如果還沒有這個指標，就先加上去。
>
> 第二步是找出那段阻塞的程式。週期性的事件常與定時工作有關：例如每幾分鐘重新載入一次設定，用同步的方式讀遠端檔案或查資料庫；或 log handler 在 buffer 滿時同步刷寫到網路。可以暫時開啟 asyncio debug 模式，它會記錄超過 0.1 秒的 callback 是哪個 task；或在事件發生時用 py-spy 取樣 loop 執行緒的 stack。找到後，把那段工作改成 async 版本、丟進 `to_thread`，或移到獨立的背景 process。

> [!question]- Q3. 手算：一個 FastAPI 服務的 endpoint 寫成 `def`，內部呼叫一個同步的下游 API，平均 200 毫秒。thread pool 上限 40，請求每秒 300 個。會發生什麼事？
> 用 Little 定律計算同時需要的 thread 數：每秒 300 個 × 0.2 秒＝60 個請求同時在等下游，但 thread pool 只有 40 個 thread。這代表 thread pool 長期滿載，多出來的請求要排隊等 thread 空出來；排隊隊伍會持續增長，延遲上升直到 client 逾時。event loop 本身沒有被阻塞，不做事的端點仍然很快，這正是它與「async def 裡呼叫阻塞函式」的症狀差異。
>
> 解法有幾個方向。最根本的是改用 async 的 HTTP client 並寫成 `async def`，讓 60 個並行的等待只是 60 個暫停的 coroutine，不需要 thread。如果暫時無法改，可以調大 thread pool 的上限（Starlette 透過 anyio 的 limiter 設定），但要評估每個 thread 的記憶體與下游能承受的並行數；同時一定要對下游設 timeout，否則下游一變慢，thread pool 會被整個佔滿。

> [!question]- Q4. 面試題：ASGI 的 HTTP scope 為什麼是「每個請求一個」，而不是像 WebSocket 一樣「每條連線一個」？
> HTTP 的語意單位是請求與回應：每個請求都有自己的 method、path、header，彼此獨立，同一條 keep-alive 連線上的前後兩個請求可能屬於完全不同的路由與使用者操作。把 scope 定義成每個請求一個，app 就能把每個請求當成一個獨立的呼叫來處理，連線重用與否是 server 的優化細節，app 不需要知道。HTTP/2 更進一步，一條連線上同時有多個 stream，每個 stream 是一個請求，「每連線一個 scope」在那裡根本無法表達。
>
> WebSocket 則相反：交握之後，整條連線就是一個長時間、雙向的對話，訊息之間有狀態（誰在哪個教室、已經驗證過的身分），所以 scope 涵蓋整條連線，app 的 coroutine 活多久連線就活多久。這個差異也影響資源設計：HTTP handler 結束就該釋放所有資源，WebSocket handler 則要在收到 disconnect 時自己清理它在共享結構（例如教室成員表）裡留下的東西。

> [!question]- Q5. 設計取捨：即時服務需要對每則訊息做 bcrypt 等級的 CPU 計算（例如驗證某種簽章），每次約 50 毫秒。用 `to_thread`、`ProcessPoolExecutor` 或獨立的 worker 服務，各有什麼取捨？
> `to_thread` 最簡單，但它只在函式會釋放 GIL 時才真正並行；如果計算是純 Python，thread 會和 event loop 搶 GIL，loop 雖然不會完全停住，卻會頻繁地被搶走執行時間，loop lag 上升。很多以 C 實作的雜湊函式庫在計算時會釋放 GIL，這時 `to_thread` 是可行的，但要以實測確認，而且 thread pool 的上限決定了最多同時算幾個。
>
> `ProcessPoolExecutor` 讓計算在別的 process 裡進行，完全不受 GIL 影響，代價是參數與結果要序列化傳遞、process 數受 CPU 核心數限制，且每個 uvicorn worker 都開一組 process pool 時，總 process 數要仔細估算。獨立的 worker 服務（透過佇列或內部 API）把 CPU 重活與即時服務的資源完全隔開，可以獨立擴展、獨立監控，代價是多一個服務與一次網路往返的延遲。每則訊息 50 毫秒、量又大時，通常應該選後者，讓即時服務的 event loop 只做 I/O 與分派。

> [!question]- Q6. 你在 production 看到 uvicorn 的 log 出現「ASGI 'lifespan' protocol appears unsupported.」，服務卻看似正常運作。這代表什麼？要不要處理？
> 這行訊息表示 uvicorn 在 `--lifespan auto` 模式下呼叫 app 的 lifespan scope 時，app 丟出了例外，uvicorn 依規格把它解讀成「這個 app 不支援 lifespan」，於是繼續啟動但不送任何 lifespan 事件。如果你的 app 確實沒有寫任何 startup 或 shutdown 邏輯（例如一個簡單的轉接 app），這是無害的。
>
> 但如果你的 app 明明在 lifespan 裡建立連線池或載入設定，這行訊息就是警訊：startup 的程式碼丟了例外，而例外被吞掉了。服務「看似正常」可能只是因為目前的請求還沒用到那些資源，或是某些請求路徑會在第一次使用時另外建立資源，掩蓋了問題。正確的處理是在本機用 `--lifespan on` 啟動，讓例外的完整 traceback 顯示出來並修正；生產環境也改用 `--lifespan on`，讓這類錯誤在部署時就讓 process 啟動失敗，而不是在流量進來後才出事。

> [!question]- Q7. 為什麼 ASGI 規格要讓 app 在 `websocket.connect` 之後自己決定 accept，而不是 server 收到交握就直接回 101？
> 因為「要不要接受這條連線」是應用層的判斷，server 不知道答案。app 需要檢查 Origin 是否在允許清單內（防止跨站 WebSocket 劫持）、從 cookie 或 query 裡的 token 驗證使用者身分、確認使用者有權進入這間教室、選擇雙方都支援的 subprotocol，甚至依目前負載決定是否拒絕。這些都必須在 101 送出之前完成，因為 101 一旦送出，連線就升級成 WebSocket，對方可以開始送訊息。
>
> 把決定權留給 app 也讓拒絕的語意清楚：accept 之前 close，server 回 HTTP 403，交握失敗，從 HTTP 的角度看就是一個被拒絕的請求，nginx 與 LB 的 log 都能記錄這個 status。代價是前端從 JavaScript 只看得到 1006，看不到 403；ASGI 另有一個 WebSocket Denial Response 擴充，讓 app 在拒絕時送出自訂的 HTTP 回應（例如 401 加上說明），但需要 server 支援。

> [!question]- Q8. 寫 middleware 時，為什麼不能「先把整個 request body 讀完、檢查後再交給內層 app」？什麼情況下可以？
> ASGI 的 body 是以多個 `http.request` 事件串流進來的。如果 middleware 先把所有事件讀完並拼成一整塊，再假造一個 receive 交給內層，會有三個後果：一是記憶體用量變成 body 的大小，一個 500 MB 的錄影上傳就要 500 MB 記憶體，同時幾個上傳就可能讓 process 被 OOM killer 殺掉；二是內層 app 失去邊收邊處理的能力，例如邊收邊寫入物件儲存、邊收邊算雜湊；三是延遲增加，app 要等最後一個 byte 到達才能開始做事。
>
> 比較好的做法是包住 receive，讓事件一個一個經過 middleware：本章的 body_limit 就是邊收邊累計大小，超過才中止，從不保存 body。可以整包讀的情況是 body 有明確且很小的上限，而且 middleware 確實需要完整內容才能判斷，例如驗證 webhook 的 HMAC 簽章需要原始 body（第 17、30 章）；這時要先檢查 Content-Length 與累計大小的上限，讀完後再用一個新的 receive 把同樣的 bytes 交給內層，讓內層讀到的內容與簽章驗證的內容完全一致。

## 延伸閱讀

- ASGI 規格文件〈ASGI (Asynchronous Server Gateway Interface) Specification〉：core 3.0，以及〈HTTP & WebSocket ASGI Message Format〉（2.5）與〈Lifespan Protocol〉
- PEP 3333〈Python Web Server Gateway Interface v1.0.1〉：對照 WSGI 的設計
- PEP 492〈Coroutines with async and await syntax〉：`async`／`await` 語法的由來
- Python 官方文件〈asyncio — Asynchronous I/O〉：event loop、`to_thread`、`run_in_executor` 與〈Developing with asyncio〉的 debug 模式章節
- uvicorn 官方文件：Settings 與 Deployment 章節（http、loop、ws、lifespan、proxy headers 的設定）
- Starlette 官方文件：Middleware、Lifespan、Thread Pool 章節；FastAPI 官方文件：Concurrency and async／await 章節
- RFC 6455〈The WebSocket Protocol〉：交握與 close code，搭配本書第 32 章
