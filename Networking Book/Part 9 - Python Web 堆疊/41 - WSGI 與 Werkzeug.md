---
chapter: 41
title: WSGI 與 Werkzeug
part: 9
---

# 第 41 章　WSGI 與 Werkzeug

> [!abstract] 本章地圖
> **核心問題**：gunicorn 收到一段 HTTP bytes 之後，到底用什麼約定把它交給 Flask？這個約定的每一條規則，在出事時又會怎麼咬你？
>
> **你會學到**：
> - 說清楚 WSGI 為什麼存在，並逐條讀懂 PEP 3333：environ 的必要鍵與 CGI 由來、`wsgi.input`、`start_response` 與 `exc_info`、回傳 iterable 與 `close()`、bytes 與 native string 規則
> - 寫出不破壞串流、不吞掉 `close()`、正確傳遞 `exc_info` 的 middleware，並用洋蔥模型推理 middleware 的順序
> - 拆解 Werkzeug 的架構：Request／Response、MultiDict、Headers、routing 的 Map／Rule／converter、dev server、reloader、debugger、ProxyFix、DispatcherMiddleware 與 test client
> - 說明 interactive debugger 的 PIN 機制，以及為什麼它絕對不能出現在 production
> - 畫出一個請求從 socket → gunicorn → WSGI → Werkzeug → Flask view → 回應的完整時序，知道每一段的 log 與錯誤長什麼樣
> - 只用標準函式庫（wsgiref）寫 WSGI app、迷你版 Werkzeug 與三個 middleware，並用 `wsgiref.validate` 驗證
>
> **前置知識**：第 20 章（HTTP/1.1 訊息格式、Content-Length 與 chunked）、第 25 章（reverse proxy 與 X-Forwarded-For 的信任規則）、第 40 章（用 socket 寫 HTTP server 與並行模型）

## 41.1 故事：月初的報表匯出把資料庫連線池吸乾了

聲聲 Live 每個月一號凌晨會產生上個月的老師月報，老師早上起床後到後台下載 `/teachers/reports/2026-09.csv`：每一列是一堂課、學生、時數與分潤。這支 Flask view 用一個資料庫游標逐批讀取資料、逐批 `yield` 給瀏覽器，大一點的老師報表有十幾 MB，要串流四十秒左右才送完。為了在送完之後歸還資料庫連線，view 把「歸還連線」登記在 Werkzeug 回應物件的 `call_on_close()` 上。

九月底，小晴接到一個看似簡單的任務：在 gunicorn 與 Flask 之間加一個 middleware，替每個請求記下耗時與回應大小，好在儀表板上找出慢的 API。第一版上線後，報表匯出的耗時全部顯示 3 ms，明顯不對。小晴改成「把 body 讀完、算出大小再回傳」，第二版一上線，十月一號早上 nginx 的 error log 開始大量出現 `upstream timed out (110: Connection timed out) while reading response header from upstream`，大報表的老師在瀏覽器等了三十秒，最後只看到 504，gunicorn worker 的記憶體也一路衝高。小晴趕緊再改成「用 generator 一塊一塊轉交」，504 消失了；可是一個小時後，連老師的課表頁都開始逾時，app 主機的資料庫連線池（每個 worker 40 條）被佔滿，新請求全部卡在「等待連線」。

同一週，資安工程師 Rita 的內部掃描在 staging VPC 裡發現一台主機 10.21.3.21 的 5000 port 回應 `Server: Werkzeug/3.1.9 Python/3.12`，回應頁面裡還有互動式 traceback。原來有人為了讓同事從辦公室 VPN 連過去看畫面，用 `flask run --debug --host 0.0.0.0` 把開發伺服器開在所有介面上。Rita 的判斷很直接：「這台機器上任何連得到 5000 port 的人，離執行任意 Python 程式只差一個 PIN。」

```text
 老師瀏覽器 ─► API LB ─► nginx 10.20.3.11（proxy_read_timeout 30 s）─► gunicorn 10.20.3.21:8000（gthread）
                                                      │
                                                      ▼  app(environ, start_response)
                                       ┌──────────── 小晴的 TimingMiddleware ────────────┐
                                       │ v1：只量到 app() 回傳 → 耗時 3 ms（量錯）       │
                                       │ v2：b"".join(body) → 40 s 後才送第一個 byte     │
                                       │     → nginx 30 s 等不到 header → 回 504         │
                                       │ v3：for chunk: yield chunk → 沒把 close() 往內傳│
                                       │     → call_on_close 沒執行 → 連線不歸還         │
                                       └──────────────────┬──────────────────────────────┘
                                                          ▼
                                     Flask view：串流匯出，close() 時歸還資料庫連線
                                                          │
                                                          ▼
                                     連線池 40 條 → 一小時後被吸乾 → 全站 504
```

這張圖是阿德在事後檢討會上畫的。三個版本的 middleware 各踩了 WSGI 規格的一條規則：v1 不知道「app 回傳」不等於「回應完成」，因為 body 要等 server 迭代時才產生；v2 違反了「middleware 不得為了等待多個區塊而阻擋迭代」，把串流變成緩衝，第一個 byte 拖到四十秒後，撞上 nginx 等待上游回應的 30 秒上限；v3 不再緩衝，卻違反了「回傳的 iterable 若有 `close()`，一定要呼叫」，於是 Werkzeug 在 `close()` 裡才會執行的 `call_on_close` 永遠沒有被觸發。staging 的 debugger 則是另一條規則：開發伺服器與 debugger 從設計上就不是給網路上的人用的。

小晴的困惑是：「我寫了兩年 Flask，從來沒看過 `start_response`。」這正是本章要補的那一層。Flask 和 gunicorn 之間有一份只有幾頁的合約，叫做 WSGI；Werkzeug 是把這份合約包裝成好用物件的工具箱，Flask 則建在 Werkzeug 之上。讀完本章，你會能逐條說出上面三個 bug 違反了哪一句規格，會自己寫出正確的 middleware，也會知道為什麼 debugger 只能出現在 127.0.0.1。

## 41.2 WSGI 為什麼存在

2000 年代初期，Python 已經有一堆 Web 框架（Zope、Quixote、Webware、Twisted Web 等），但每個框架都綁定自己的伺服器介面：有的只能跑在 mod_python（Apache 模組）裡，有的只能用 CGI 或 FastCGI，有的自帶 server。選了框架就等於選了部署方式，反過來，寫 server 的人要替每個框架各寫一套轉接層。這是經典的 **N×M 問題**：N 個框架乘上 M 種 server，就需要 N×M 份轉接程式碼。

```text
 沒有共同介面（N×M 份轉接）                     有了 WSGI（N＋M 份實作）

 框架 A ──┬── mod_python                        框架 A ──┐                ┌── gunicorn
          ├── CGI                               框架 B ──┤                ├── uWSGI
 框架 B ──┼── FastCGI                           Flask  ──┼──► WSGI ◄──────┼── mod_wsgi
          ├── 自帶 server                       Django ──┤   （一個函式   ├── Waitress
 框架 C ──┴── Twisted                           Bottle ──┘     呼叫約定） └── wsgiref
```

左邊每一條線都是一份要維護的轉接程式碼；右邊每個框架只要實作「WSGI 應用程式」那一端，每個 server 只要實作「WSGI server」那一端，任意組合都能直接接起來。這個想法借鏡了 Java 的 servlet API，由 Phillip J. Eby 在 2003 年提出為 **PEP 333**，定名 **WSGI**（Web Server Gateway Interface，Web 伺服器閘道介面）。2010 年的 **PEP 3333** 是它的 Python 3 版本：介面完全相同，主要補上 bytes 與字串的規則，也就是 41.7 節的主題。今天說 WSGI，指的就是 PEP 3333。

WSGI 刻意設計得很「薄」：不定義 Request 物件、routing、cookie 或 session，只定義一個函式呼叫的形狀，目標使用者是框架與 server 的作者。好處是規格小到二十年沒改過；代價是直接寫 WSGI 很囉唆，於是有了 Werkzeug、WebOb 這類「WSGI 工具箱」，Flask 再建在 Werkzeug 上。下表把今天會遇到的元件依角色分類：

| 角色 | 代表 | 在聲聲 Live 的位置 | 備註 |
|---|---|---|---|
| WSGI server（gateway） | gunicorn、uWSGI、mod_wsgi、Waitress | gunicorn 10.20.3.21:8000 | 解析 HTTP、管理 worker、呼叫 app；uWSGI 官方已宣告進入維護模式 |
| 參考實作 | 標準函式庫 `wsgiref` | 本章動手做 | 單執行緒、HTTP/1.0 回應，只適合學習與測試 |
| 開發用 server | Werkzeug `run_simple`（`flask run`） | 小晴的筆電 | 有 reloader 與 debugger，不能上 production |
| middleware | ProxyFix、DispatcherMiddleware、小晴的 Timing | gunicorn 與 Flask 之間 | 對外像 app、對內像 server |
| WSGI 工具箱 | Werkzeug、WebOb | Flask 的下層 | Request／Response、routing、測試工具 |
| 框架（WSGI app） | Flask、Django、Pyramid、Bottle、Falcon | 聲聲 Live 的 API | Django 同時支援 WSGI 與 ASGI |

重點是「角色」而不是名字：同一個程式可以同時扮演兩種角色，middleware 就是例子。WSGI 也有邊界：它是**同步**的呼叫約定，一個請求佔住一個 worker 直到回應送完，不適合長時間開著的 WebSocket，那是第 42 章 ASGI 要解決的問題。

## 41.3 最小合約：一個 callable、兩個參數、一個 iterable

WSGI 應用程式就是一個 **callable**（可呼叫物件：函式、有 `__call__` 的物件、類別都可以），簽名固定是 `app(environ, start_response)`。`environ` 是一個 dict，裝著這個請求的所有資訊；`start_response` 是 server 傳進來的函式，app 用它告訴 server 狀態碼與 header；app 的回傳值是一個 **iterable**（可以用 for 迴圈走訪的東西），每一項是一段 bytes 的 body。三件事，就是整份合約的骨架。

```text
 WSGI server（gunicorn）                                         WSGI app（Flask）
   │ ① 解析 HTTP 請求，組出 environ dict                              │
   │──── ② app(environ, start_response) ─────────────────────────────►│
   │                                                                  │ 處理請求
   │◄─── ③ start_response("200 OK", [("Content-Type", ...), ...]) ────│ server 先存起來，不送
   │◄─── ④ return iterable ───────────────────────────────────────────│
   │ ⑤ for chunk in iterable:                                         │
   │      第一個非空 chunk → 才把狀態列與 header 寫進 socket          │
   │      每個 chunk → 寫進 socket（不得拖延）                        │
   │ ⑥ iterable.close()（如果有）── 不論成功、出錯或 client 斷線 ────►│ 釋放資源
```

逐步看。① server 從 socket 讀出請求，依 CGI 的慣例組成 environ。② server 呼叫 app。③ app 呼叫 `start_response` 交出狀態與 header，規格要求 server 這時**只能存起來**，不能馬上送出。④ app 回傳 iterable，注意這時 body 可能根本還沒產生，如果它是一個 generator，裡面的程式碼要等 server 迭代時才會執行。⑤ server 迭代，遇到第一個**非空**的 bytes 時，才把狀態列與 header 送出。⑥ 最後，如果 iterable 有 `close()` 方法，server 必須呼叫它。

這個順序解釋了故事裡 v1 的「3 ms」：middleware 在 ④ 之後就停錶，量到的只是 app 建立 generator 的時間。下面用三十幾行程式寫一個「照規格辦事」的極簡 server，把每一步印出來。它不開 socket，只是把要送上線的 bytes 收集起來，讓我們看清楚 header 是在什麼時候被送出的：

```python
import io
import sys


def hello_app(environ, start_response):
    """一個完整的 WSGI 應用程式：一個函式、兩個參數、回傳 bytes 的 iterable。"""
    name = environ.get("QUERY_STRING", "").removeprefix("name=") or "world"
    body = f"hello, {name}\n".encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8"),
                              ("Content-Length", str(len(body)))])
    return [body]


def run_once(app, path="/", query=""):
    """極簡 gateway：照 PEP 3333 的規則呼叫 app，並把「線上送出的 bytes」記下來。"""
    environ = {
        "REQUEST_METHOD": "GET", "SCRIPT_NAME": "", "PATH_INFO": path, "QUERY_STRING": query,
        "SERVER_NAME": "127.0.0.1", "SERVER_PORT": "8000", "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0), "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": sys.stderr, "wsgi.multithread": False, "wsgi.multiprocess": False,
        "wsgi.run_once": True,
    }
    wire, state = [], {"status": None, "headers": None, "sent": False}
    log = lambda msg: print(f"  [server] {msg}")

    def start_response(status, headers, exc_info=None):
        log(f"start_response({status!r}, {len(headers)} headers) → 先存起來，還不送")
        state["status"], state["headers"] = status, headers
        return lambda data: send(data)          # 舊式 write()，現代程式不該用

    def send(data):
        if not state["sent"]:                  # 第一個非空 chunk 出現時才送 header
            head = f"HTTP/1.1 {state['status']}\r\n" + "".join(
                f"{k}: {v}\r\n" for k, v in state["headers"]) + "\r\n"
            wire.append(head.encode("latin-1"))
            state["sent"] = True
            log("第一個 body chunk 出現 → 送出狀態列與 header")
        wire.append(data)
        log(f"送出 body {len(data)} bytes")

    log("呼叫 app(environ, start_response)")
    result = app(environ, start_response)
    log(f"app 回傳 {type(result).__name__}，開始迭代")
    try:
        for chunk in result:
            if chunk:                          # 空 bytes 不觸發送出
                send(chunk)
        if not state["sent"]:
            send(b"")                           # body 全空也要送 header
    finally:
        if hasattr(result, "close"):            # 規格：不論成功失敗都要呼叫 close()
            result.close()
            log("呼叫 result.close()")
        else:
            log("list 沒有 close()，跳過")
    return b"".join(wire)


raw = run_once(hello_app, query="name=student23")
print(raw.decode("utf-8"))
assert raw.startswith(b"HTTP/1.1 200 OK\r\n") and raw.endswith("hello, student23\n".encode())
```

```text
  [server] 呼叫 app(environ, start_response)
  [server] start_response('200 OK', 2 headers) → 先存起來，還不送
  [server] app 回傳 list，開始迭代
  [server] 第一個 body chunk 出現 → 送出狀態列與 header
  [server] 送出 body 17 bytes
  [server] list 沒有 close()，跳過
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Length: 17

hello, student23
```

輸出的順序就是上面的時序圖：`start_response` 被呼叫時 server 只是存起來，迭代出第一個 body chunk 才送出狀態列與 header。這個延遲是刻意的：還沒送出任何 byte，app 就還能反悔，例如產生 body 途中發現錯誤而改回 500（41.5 節）。`start_response` 回傳的函式是舊式的 `write()`，給習慣「直接往輸出寫」的舊框架用；PEP 3333 明說新程式不該用它，因為它讓 server 無法用迭代控制流量。

「list 沒有 `close()`，跳過」也值得注意：只要 iterable 有 `close()`，server 就必須呼叫，這是故事中 v3 違反的規則。app 要回傳 `[body]` 而不是 `body`，是因為 bytes 本身也是 iterable，`for b in b"hello"` 一次給出一個整數，server 照單全收就會一個 byte 一個 byte 地送。

## 41.4 environ：CGI 的遺產與 wsgi.* 鍵

environ 的鍵名看起來很古老，`REQUEST_METHOD`、`PATH_INFO`、`HTTP_USER_AGENT`，全是大寫加底線。這不是 Python 的風格，而是 **CGI**（Common Gateway Interface，RFC 3875）的風格。CGI 是 1990 年代 Web server 執行外部程式的方式：每個請求啟動一個新 process，請求資訊透過**環境變數**傳進去，body 從 stdin 讀，回應寫到 stdout。WSGI 沿用了這套變數名稱，讓熟悉 CGI 的人與現有程式碼能直接上手，「environ」這個名字也是從「environment variables」來的。

```text
 線上的 HTTP 請求（第 20 章）                               environ（Python dict）
 POST /teachers/%E7%BE%8E%E5%92%B2/reviews?lang=ja HTTP/1.1
 ───┬ ──────────────────┬────────────────── ──┬── ────┬───
    │                   │                     │       └──► SERVER_PROTOCOL = "HTTP/1.1"
    │                   │                     └──────────► QUERY_STRING    = "lang=ja"
    │                   └────────────────────────────────► PATH_INFO       = 解碼後的路徑（latin-1 字串）
    └────────────────────────────────────────────────────► REQUEST_METHOD  = "POST"
 Host: api.shengsheng.example ───────────────────────────► HTTP_HOST
 Content-Type: application/json ─────────────────────────► CONTENT_TYPE（沒有 HTTP_ 前綴）
 Content-Length: 12 ─────────────────────────────────────► CONTENT_LENGTH（沒有 HTTP_ 前綴）
 X-Request-Id: 7f3c9a2e ─────────────────────────────────► HTTP_X_REQUEST_ID（轉大寫、- 變 _）
 （空行）
 {"stars": 5} ───────────────────────────────────────────► wsgi.input（只能讀 CONTENT_LENGTH 個 bytes）
 TCP 對端 10.20.3.11:51514 ──────────────────────────────► REMOTE_ADDR（CGI 變數，規格未強制）
 server 自己的設定 ───────────────────────────────────────► SERVER_NAME、SERVER_PORT、wsgi.* 鍵
```

圖的上半部是請求行的拆解：method、路徑、query、協定版本各自成為一個鍵，注意 `PATH_INFO` 是 server **已經做過 percent-decoding** 的路徑，`QUERY_STRING` 則保持原樣。中間是 header 的轉換規則：名稱轉大寫、`-` 換成 `_`、加上 `HTTP_` 前綴；唯二的例外是 `Content-Type` 與 `Content-Length`，它們直接叫 `CONTENT_TYPE`、`CONTENT_LENGTH`，這也是 CGI 的慣例。最下面兩行容易被忽略：`REMOTE_ADDR` 是 **TCP 對端**的位址，在 nginx 後面它永遠是 nginx，不是學生；`SERVER_NAME` 是 server 自己的名字，不是 client 送來的 `Host`。

PEP 3333 規定 environ 必須（或在可以是空字串時應該）包含下列鍵。前半是 CGI 變數，後半是 WSGI 自己加的 `wsgi.*` 鍵：

| 鍵 | 例子 | 說明 |
|---|---|---|
| `REQUEST_METHOD` | `"POST"` | 一定存在、不得為空 |
| `SCRIPT_NAME` | `""` 或 `"/ops"` | app 被「掛載」的前綴；app 掛在根目錄時為空字串 |
| `PATH_INFO` | `"/teachers/…"` | 掛載點之後的路徑，已 percent-decode；可為空 |
| `QUERY_STRING` | `"lang=ja&lang=en"` | `?` 之後的原始字串，未解碼；可為空或不存在 |
| `CONTENT_TYPE`、`CONTENT_LENGTH` | `"application/json"`、`"12"` | 可為空或不存在；沒有 `HTTP_` 前綴 |
| `SERVER_NAME`、`SERVER_PORT` | `"api.shengsheng.example"`、`"8000"` | 一定存在；組 URL 時以 `HTTP_HOST` 優先 |
| `SERVER_PROTOCOL` | `"HTTP/1.1"` | client 使用的協定版本 |
| `HTTP_*` | `HTTP_COOKIE`、`HTTP_X_REQUEST_ID` | 其他所有 request header |
| `wsgi.version` | `(1, 0)` | PEP 3333 仍是 `(1, 0)` |
| `wsgi.url_scheme` | `"http"` 或 `"https"` | 這一跳的 scheme；TLS 在 LB 終結時是 `http` |
| `wsgi.input` | 類檔案物件 | request body，只讀 bytes |
| `wsgi.errors` | 文字串流 | 給 app 寫錯誤訊息，通常接到 server 的 error log |
| `wsgi.multithread`、`wsgi.multiprocess` | `True`／`False` | 同一個 app 物件是否可能被多個 thread／process 同時呼叫 |
| `wsgi.run_once` | `False` | 是否每個 process 只處理一個請求（CGI 式），用來決定要不要做快取 |

server 與 middleware 可以加上自己的擴充鍵，名稱要帶前綴（通常是名稱加一個點），例如 `gunicorn.socket`、`werkzeug.request`；這是 middleware 把資訊傳給內層的標準管道。不在規格內但很常見的還有 `REMOTE_ADDR`、`REMOTE_PORT`，以及 gunicorn 放的 `RAW_URI`（未經解碼的原始路徑）。

### 掛載點：SCRIPT_NAME 與 PATH_INFO

路徑拆成兩段，是因為 app 不一定掛在網站根目錄。假設內部後台掛在 `/ops` 底下，請求 `/ops/users/42` 進來時，分派的那一層把 `/ops` 從 `PATH_INFO` 移到 `SCRIPT_NAME`，後台 app 看到 `/users/42`，就像自己在根目錄；產生連結時再把 `SCRIPT_NAME` 接回前面。PEP 3333 的 URL 重建演算法是：`wsgi.url_scheme` + `://` + `HTTP_HOST`（沒有才用 `SERVER_NAME` 加非預設 port）+ `quote(SCRIPT_NAME)` + `quote(PATH_INFO)` + `?QUERY_STRING`。Flask 的 `url_for(_external=True)` 就照這個邏輯組，所以 scheme 或 host 錯了（例如 TLS 在 LB 終結），連結就會錯，這是 ProxyFix 存在的理由。

### wsgi.input：body 只能讀一次，也只能讀 Content-Length 那麼多

`wsgi.input` 是類檔案物件，背後通常就是 socket 的讀取 buffer。規格要求 app **不要讀超過 `CONTENT_LENGTH` 的長度**：在 keep-alive 連線上，多讀會讀到下一個請求的開頭，或在沒有下一個請求時永遠卡住。正確寫法是 `environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH") or 0))`；`wsgiref.validate` 甚至要求 `read()` 一定要帶長度，動手做會看到。

另外兩個細節常在 production 咬人。第一，body **只能讀一次**：Werkzeug 解析 form 時會把它讀掉，所以第 17、30 章驗證 webhook 簽章時，一定要先呼叫會快取內容的 `request.get_data()`。第二，chunked 請求（第 20 章）沒有 `CONTENT_LENGTH`，WSGI 規格沒有定義該怎麼讀；部分 server 提供非標準的 `wsgi.input_terminated` 旗標表示「讀到 EOF 就是結束」，Werkzeug 會檢查它。實務上 nginx 預設會先收下完整的 chunked 請求，再帶著 `Content-Length` 轉給上游，所以 app 很少直接面對。

### header 變成 environ 鍵時遺失了什麼

header 轉成 `HTTP_*` 的規則是**多對一**的：`X-Request-Id` 與 `X_Request_Id` 都變成 `HTTP_X_REQUEST_ID`，同名 header 出現多次時依 CGI 慣例以逗號合併。如果信任邏輯依賴某個由 nginx 加上的 header（例如 `X-Forwarded-For`），攻擊者就可能送一個底線版本混進合併後的值。所以 nginx 預設忽略名稱含底線的 header（`underscores_in_headers off`），新版 gunicorn 也有對應的 header 名稱政策。下面用 `wsgiref.simple_server` 在 127.0.0.1 上實際跑一次：

```python
import http.client
import json
import threading
from wsgiref.simple_server import WSGIRequestHandler, make_server


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):              # 不印 access log，讓輸出只剩我們關心的
        pass


def environ_app(environ, start_response):
    """把 environ 裡的 CGI 變數與 wsgi.* 鍵整理成 JSON 回傳。"""
    length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(length)  # 只讀 CONTENT_LENGTH 這麼多，不多讀
    keys = ["REQUEST_METHOD", "SCRIPT_NAME", "PATH_INFO", "QUERY_STRING", "CONTENT_TYPE",
            "CONTENT_LENGTH", "SERVER_NAME", "SERVER_PORT", "SERVER_PROTOCOL", "REMOTE_ADDR"]
    report = {k: environ.get(k) for k in keys}
    report.update({k: v for k, v in environ.items() if k.startswith("HTTP_")})
    report.update({k: environ[k] for k in ("wsgi.version", "wsgi.url_scheme",
                                                  "wsgi.multithread", "wsgi.multiprocess")})
    report["body"] = body.decode("utf-8")
    report["PATH_INFO→utf-8"] = environ["PATH_INFO"].encode("latin-1").decode("utf-8")
    out = json.dumps(report, ensure_ascii=False, indent=1).encode("utf-8")
    start_response("200 OK", [("Content-Type", "application/json"), ("Content-Length", str(len(out)))])
    return [out]


server = make_server("127.0.0.1", 0, environ_app, handler_class=QuietHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
port = server.server_address[1]

conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
conn.putrequest("POST", "/teachers/%E7%BE%8E%E5%92%B2/reviews?lang=ja&lang=en",
                skip_host=True, skip_accept_encoding=True)
conn.putheader("Host", "api.shengsheng.example")
conn.putheader("Content-Type", "application/json")
conn.putheader("X-Request-Id", "7f3c9a2e")
conn.putheader("X_Request_Id", "forged")     # 底線版本：轉成 environ 後和上一行撞名
body = json.dumps({"stars": 5}).encode()
conn.putheader("Content-Length", str(len(body)))
conn.endheaders(body)
resp = conn.getresponse()
env = json.loads(resp.read())
conn.close()
server.shutdown()
server.server_close()

for k, v in env.items():
    print(f"{k:<17} {v!r}")
assert env["PATH_INFO"] != env["PATH_INFO→utf-8"] == "/teachers/美咲/reviews"
assert env["HTTP_X_REQUEST_ID"] == "7f3c9a2e,forged"
assert "HTTP_CONTENT_TYPE" not in env and env["CONTENT_LENGTH"] == "12"
```

```text
REQUEST_METHOD    'POST'
SCRIPT_NAME       ''
PATH_INFO         '/teachers/ç¾\x8eå\x92²/reviews'
QUERY_STRING      'lang=ja&lang=en'
CONTENT_TYPE      'application/json'
CONTENT_LENGTH    '12'
SERVER_NAME       '1.0.0.127.in-addr.arpa'
SERVER_PORT       '49548'
SERVER_PROTOCOL   'HTTP/1.1'
REMOTE_ADDR       '127.0.0.1'
HTTP_HOST         'api.shengsheng.example'
HTTP_X_REQUEST_ID '7f3c9a2e,forged'
wsgi.version      [1, 0]
wsgi.url_scheme   'http'
wsgi.multithread  False
wsgi.multiprocess False
body              '{"stars": 5}'
PATH_INFO→utf-8   '/teachers/美咲/reviews'
```

逐行看。`PATH_INFO` 那一行是亂碼：client 送的是 `%E7%BE%8E%E5%92%B2`（「美咲」的 UTF-8 percent-encoding），server 解碼成 6 個 bytes 後，依 PEP 3333 用 **latin-1** 把每個 byte 對應成一個字元，所以變成 `ç¾\x8eå\x92²`；最後一行把它 `.encode("latin-1").decode("utf-8")` 才得到正確的「美咲」，Werkzeug 的 `request.path` 做的就是這件事，41.7 節會解釋這個看似奇怪的規則。`QUERY_STRING` 保持原樣，兩個 `lang` 都在，要靠框架的 MultiDict 才能完整取出。

`HTTP_X_REQUEST_ID` 的值是 `7f3c9a2e,forged`：連字號與底線兩個版本被合併了。`SERVER_NAME` 是 server 反查 127.0.0.1 得到的名稱（macOS 上是 `1.0.0.127.in-addr.arpa`，Linux 上通常是 `localhost`），和 client 送的 `Host` 無關，所以組 URL 要以 `HTTP_HOST` 優先。`SERVER_PORT` 每次執行都不同；`wsgi.multithread` 是 False，因為 `wsgiref.simple_server` 一次只處理一個請求。

## 41.5 start_response：狀態、header 與 exc_info

`start_response(status, response_headers, exc_info=None)` 的參數格式很嚴格。`status` 是 `"200 OK"` 這樣的字串（三位數、一個空格、原因片語），不能是整數 200。`response_headers` 是 `(name, value)` tuple 組成的 **list**，同名 header（例如多個 `Set-Cookie`）就放多個 tuple。呼叫時機必須在 iterable 產出第一段 body **之前**，但可以延後到 generator 第一次被迭代時，讓 generator 形式的 app 先做點事再決定狀態碼。

app **不准**放 **hop-by-hop header**（只對「這一跳」連線有意義的 header），例如 `Connection`、`Keep-Alive`、`Transfer-Encoding`、`Upgrade`：連線要不要保持、body 要不要 chunked，是 server 依它和 client 之間的連線決定的，app 不知道前面隔了幾層 proxy。所以 app 想串流時不寫 `Transfer-Encoding: chunked`，而是**不給 `Content-Length`**，由 server 決定怎麼劃定 body 邊界。

| app 的做法 | server 的行為 | 典型情境 |
|---|---|---|
| 給了正確的 `Content-Length` | 照長度送；不得送出超過這個長度的 bytes | 一般 JSON API、Werkzeug 的 `Response` 在 body 已知時會自動補上 |
| 沒給 `Content-Length`，iterable 只有一個元素 | server 可以自己算出長度並補上 | `return [body]` |
| 沒給 `Content-Length`，多個元素 | HTTP/1.1 下用 chunked；HTTP/1.0 下送完就關閉連線 | 串流匯出、SSE |
| 放了 `Connection`、`Transfer-Encoding` | 規格禁止；`wsgiref` 預設（沒用 `-O` 執行時）直接 AssertionError | 從別的框架搬來的舊程式 |
| `Content-Length` 比實際 body 短或長 | client 被截斷或卡住等資料；keep-alive 連線可能錯位 | 手算長度時把字元數當 bytes 數 |

最後一列的常見成因是把字元數當 bytes 數：`len("美咲")` 是 2，`len("美咲".encode())` 是 6，症狀是中文回應的尾巴被截掉。

### exc_info：還來得及反悔的時候才能反悔

`start_response` 正常只能呼叫一次，第三個參數 `exc_info` 是唯一的例外。當 app（或錯誤處理 middleware）在處理途中發生例外，想把回應改成 500 時，可以再呼叫一次 `start_response("500 ...", headers, sys.exc_info())`。server 的處理規則是：如果 header **還沒送出**，就用新的狀態與 header 取代舊的；如果 header **已經送出**，就把 `exc_info` 裡的例外重新拋出，因為已經寫進 socket 的狀態列沒辦法收回。

```text
                      start_response 的三個狀態
 狀態 A：尚未呼叫 start_response
   ├─ start_response(status, headers) ───────────────► 狀態 B
   └─ start_response(status, headers, exc_info) ─────► 狀態 B（直接以錯誤回應開始）

 狀態 B：header 已存，還沒送出
   ├─ start_response(..., exc_info) ─────────────────► 狀態 B（取代狀態與 header）
   ├─ 沒帶 exc_info 又呼叫一次 ──────────────────────► 錯誤（規格不允許）
   └─ 迭代出第一個非空 chunk ────────────────────────► 狀態 C（送出狀態列與 header）

 狀態 C：header 已送出
   └─ start_response(..., exc_info) ─────────────────► server 重新拋出原例外，只能中斷連線
```

這張狀態圖有兩條規則。第一，只有帶著 `exc_info` 才能第二次呼叫，而且只在「header 已存、未送」時有效果。第二，header 送出之後再出錯，server 只能中斷連線，client 收到狀態碼 200、內容卻被截斷。這是串流回應本質上的限制：用 chunked 時 client 還能從「沒收到最後的 0 長度 chunk」判斷不完整（第 20 章），用「關閉連線」劃定邊界時就無從分辨。規格也要求帶 `exc_info` 呼叫的程式不得攔截它拋出的例外，要讓它傳回 server。

下面這段程式寫一個照規格處理 `exc_info` 的極簡 server，加上一個錯誤處理 middleware，再讓報表 app 在四個不同時間點出錯：

```python
import sys


def gateway(app):
    """極簡 server：實作 start_response 的 exc_info 規則，回傳（線上送出的內容, 結果）。"""
    state = {"status": None, "headers": None, "sent": False}
    wire = []

    def start_response(status, headers, exc_info=None):
        if exc_info:
            try:
                if state["sent"]:              # header 已經送出：無法反悔，只能把原例外丟回去
                    raise exc_info[1].with_traceback(exc_info[2])
            finally:
                exc_info = None                 # 規格建議：避免 traceback 造成循環參照
        elif state["status"] is not None:
            raise AssertionError("沒帶 exc_info 就第二次呼叫 start_response")
        state["status"], state["headers"] = status, headers
        return wire.append

    def send(chunk):
        if not state["sent"]:
            wire.append(f"<{state['status']}>".encode())
            state["sent"] = True
        wire.append(chunk)

    result = app({"PATH_INFO": "/teachers/reports/2026-09.csv"}, start_response)
    try:
        for chunk in result:
            if chunk:
                send(chunk)
        outcome = "完整送出"
    except Exception as exc:                    # 走到這裡代表 header 已送出，只能中斷連線
        outcome = f"中斷連線（{type(exc).__name__}: {exc}）"
    finally:
        if hasattr(result, "close"):
            result.close()
    return b"".join(wire).decode(), outcome


def catch_errors(app):
    """錯誤處理 middleware：把例外變成 500；但 header 已送出時，規格只允許中斷。"""
    def wrapped(environ, start_response):
        try:
            result = app(environ, start_response)
            try:
                yield from result               # 迭代期間的例外也要接住
            finally:
                if hasattr(result, "close"):
                    result.close()
        except Exception:
            start_response("500 Internal Server Error", [("Content-Type", "text/plain")],
                           sys.exc_info())
            yield b"internal error, x-request-id=7f3c9a2e\n"
    return wrapped


def make_report(fail):
    def report_app(environ, start_response):
        if fail == "before":
            raise ConnectionError("資料庫連不上")
        start_response("200 OK", [("Content-Type", "text/csv")])
        if fail == "after-start":
            raise ValueError("月份格式錯誤")     # 已呼叫 start_response，但還沒送出任何 byte

        def rows():
            yield b"teacher,lessons\n"
            yield b"teacher05,42\n"
            if fail == "mid-stream":
                raise TimeoutError("資料庫游標逾時")
            yield b"teacher09,17\n"
        return rows()
    return report_app


results = {}
for fail in ("none", "before", "after-start", "mid-stream"):
    wire, outcome = gateway(catch_errors(make_report(fail)))
    results[fail] = (wire, outcome)
    print(f"{fail:<12} {outcome}\n{'':<12} {wire!r}")

assert results["none"][0].startswith("<200 OK>")
assert results["before"][0].startswith("<500") and results["after-start"][0].startswith("<500")
assert results["mid-stream"][0].startswith("<200 OK>") and "中斷" in results["mid-stream"][1]
```

```text
none         完整送出
             '<200 OK>teacher,lessons\nteacher05,42\nteacher09,17\n'
before       完整送出
             '<500 Internal Server Error>internal error, x-request-id=7f3c9a2e\n'
after-start  完整送出
             '<500 Internal Server Error>internal error, x-request-id=7f3c9a2e\n'
mid-stream   中斷連線（TimeoutError: 資料庫游標逾時）
             '<200 OK>teacher,lessons\nteacher05,42\n'
```

四種情況對應狀態圖的四條路徑。`none` 正常完成。`before` 是 app 還沒呼叫 `start_response` 就出錯，middleware 帶著 `exc_info` 直接開始一個 500 回應。`after-start` 是 app 已呼叫 `start_response("200 OK")`、但還沒送出任何 byte 就出錯，server 把狀態換成 500，client 看不出曾經有過 200。`mid-stream` 是串流到一半資料庫游標逾時：前兩列已連同 200 送出，middleware 想改成 500，server 只能把原例外丟回並中斷連線，client 拿到少了尾巴的 CSV。

這個結果直接指導實務設計：會在串流途中失敗的工作，要在送出第一個 byte 之前把可能失敗的步驟（權限、查詢能否執行）做完；做不到就在資料裡加上結束標記或總列數，讓下載端驗證檔案完整。程式裡的 `finally: exc_info = None` 則是規格的建議：traceback 參照整個呼叫堆疊，用完就丟，避免循環參照延後釋放記憶體。

## 41.6 回傳 iterable、close() 與串流

回傳的 iterable 決定 body 什麼時候產生。list 的 body 已經全在記憶體裡；generator 或自訂 iterable 則每被迭代一次才產生下一段，這就是**串流回應**（streaming response），server 邊產生邊送，記憶體只需放得下一段。故事裡的報表匯出每讀完一批資料庫列就 `yield` 一段 CSV，老師在第一秒就開始收到資料。

PEP 3333 對串流有兩條要求。給 server 的是**不得延遲任何一段的傳送**；給 middleware 的是**不得為了等待多段資料而阻擋迭代**，真的需要先累積時，要先 `yield b""` 把控制權交回 server。故事裡 v2 的 `b"".join(body)` 正是違反了第二條。

```text
 時間（秒）    0    1    2    3    4    5    6 ...   40
 正確的串流   app: 批1  批2  批3  批4  批5  批6 ...  批N
              送：  ▓    ▓    ▓    ▓    ▓    ▓  ...   ▓     TTFB ≈ 1 s，記憶體 ≈ 一批
 v2 緩衝      app: 批1  批2  批3  批4  批5  批6 ...  批N
              送：  ·    ·    ·    ·    ·    ·  ...   ▓▓▓▓▓ TTFB ≈ 40 s，記憶體 ≈ 整份
                                                  ▲
                                   30 s：nginx 的 proxy_read_timeout 到期 → 504
```

上半部是正確的串流，**TTFB**（time to first byte，從送出請求到收到第一個 byte 的時間）約等於第一批的處理時間；下半部是 v2，第一個 byte 要等全部做完。這張圖也解釋了 504 的來源：nginx 的 `proxy_read_timeout` 量的是「兩次從上游讀到資料之間」的最長間隔，正確的串流每秒都有資料，計時器不斷重來；v2 讓上游沉默四十秒，聲聲 Live 當時設定的 30 秒一到，nginx 就放棄並回 504（這是第 43 章修正 timeout 鏈之前的設定，修正後是 35 秒，但同樣等不了四十秒）。報表服務用的是 gunicorn 的 gthread worker；如果是預設的 sync worker，情況更糟：sync worker 處理一個請求期間不會向 arbiter（管理 worker 的主 process）回報，任何超過 `--timeout`（預設 30 秒）的請求都會被當成卡死而被殺掉，不論它是否在串流。第 43 章會詳細談 gunicorn 的 worker 模型與 timeout 鏈。

### close()：串流回應唯一可靠的「結束」訊號

串流回應的資源（資料庫游標、檔案、鎖）不能在 app 回傳時釋放，因為 body 還沒產生；也不能只靠「迭代到最後」，因為 client 可能中途關掉分頁。PEP 3333 的答案是 `close()`：iterable 有 `close()` 時，server **必須**在請求結束時呼叫它，不論正常完成、迭代途中出錯或 client 提早斷線。Werkzeug 的 `response.call_on_close(func)` 就建立在這條規則上：回傳的 iterable 被包成 `ClosingIterator`，在 `close()` 裡依序呼叫登記的函式。

對 middleware 的含意是：**你回傳給 server 的是你自己的 iterable，就有責任在自己的 `close()` 裡呼叫內層的 `close()`**。v3 用 generator 包住內層 body，server 呼叫的是 generator 的 `close()`，它只結束 generator 自己。內層若也是 generator，CPython 通常會在參考消失時順帶關閉它；但 `ClosingIterator` 是普通物件，沒有這種保險，「歸還資料庫連線」就永遠沒被執行。

下面的程式用模擬時鐘重現故事的四個版本。`ExportBody` 是匯出 view 的 body，每批花 1 秒，`close()` 時歸還資料庫連線；`gateway()` 模擬 gunicorn，可以指定 client 在收到第 2 批後斷線：

```python
CLOCK = [0.0]                                   # 模擬時鐘（秒），讓輸出每次都一樣
POOL = {"in_use": 0}                            # 模擬資料庫連線池


class ExportBody:
    """匯出 view 的回應 body：逐批讀資料庫、逐批送出；close() 時歸還資料庫連線。"""
    def __init__(self, batches):
        POOL["in_use"] += 1
        self.batches = batches

    def __iter__(self):
        for i in range(self.batches):
            CLOCK[0] += 1.0                     # 每批查詢花 1 秒
            yield f"batch-{i},".encode() * 1000  # 每批約 8 KB

    def close(self):                            # 等同 Werkzeug 的 response.call_on_close()
        POOL["in_use"] -= 1


def export_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/csv")])
    return ExportBody(batches=6)


class TimingV1:                                  # 第一版：只量到 app() 回傳
    def __init__(self, app): self.app, self.log = app, {}
    def __call__(self, environ, start_response):
        t0 = CLOCK[0]
        result = self.app(environ, start_response)
        self.log["duration"] = CLOCK[0] - t0     # 這時 body 一個 byte 都還沒產生
        return result


class TimingV2(TimingV1):                        # 第二版：為了記錄大小，把 body 整個讀完
    def __call__(self, environ, start_response):
        t0 = CLOCK[0]
        body = b"".join(self.app(environ, start_response))   # 緩衝全部，也沒呼叫 close()
        self.log.update(duration=CLOCK[0] - t0, buffered=len(body))
        return [body]


class TimingV3(TimingV1):                        # 第三版：改成 generator，不緩衝了，但 close 沒傳下去
    def __call__(self, environ, start_response):
        t0 = CLOCK[0]
        try:
            for chunk in self.app(environ, start_response):
                yield chunk
        finally:
            self.log["duration"] = CLOCK[0] - t0


class Timing(TimingV1):                          # 正確版：包一層 iterable，close() 時才算結束
    def __call__(self, environ, start_response):
        return _TimedBody(self.app(environ, start_response), self.log, CLOCK[0])


class _TimedBody:
    def __init__(self, inner, log, t0): self.inner, self.log, self.t0 = inner, log, t0
    def __iter__(self): return iter(self.inner)  # 不緩衝：一批一批原樣往外交
    def close(self):
        try:
            if hasattr(self.inner, "close"):
                self.inner.close()               # 一定要把 close 往內傳
        finally:
            self.log["duration"] = CLOCK[0] - self.t0


def gateway(app, disconnect_after=None):
    """模擬 gunicorn：送出每個 chunk；學生關掉分頁時（disconnect_after）提早停止並呼叫 close()。"""
    CLOCK[0], POOL["in_use"] = 0.0, 0
    ttfb, sent = None, 0
    result = app({"PATH_INFO": "/teachers/reports/2026-09.csv"}, lambda s, h, e=None: None)
    try:
        for n, chunk in enumerate(result, 1):
            ttfb = CLOCK[0] if ttfb is None else ttfb
            sent += len(chunk)
            if n == disconnect_after:
                break                            # BrokenPipe：不再迭代
    finally:
        if hasattr(result, "close"):
            result.close()
    return ttfb, sent


seen = {}
for cls in (TimingV1, TimingV2, TimingV3, Timing):
    for disconnect in (None, 2):
        mw = cls(export_app)
        ttfb, sent = gateway(mw, disconnect)
        seen[cls.__name__, disconnect] = (mw.log["duration"], ttfb, POOL["in_use"])
        print(f"{cls.__name__:<8} 斷線於={str(disconnect):<4} log={mw.log}  "
              f"TTFB={ttfb}s 送出={sent}B 連線池佔用={POOL['in_use']}")

assert seen["TimingV1", None][0] == 0.0                 # 量錯了：只量到 app() 回傳
assert seen["TimingV2", None][1] == 6.0                 # 緩衝：第一個 byte 要等全部做完
assert seen["TimingV3", 2][2] == 1                      # close 沒傳下去：連線沒歸還
assert seen["Timing", None] == (6.0, 1.0, 0) and seen["Timing", 2] == (2.0, 1.0, 0)
```

```text
TimingV1 斷線於=None log={'duration': 0.0}  TTFB=1.0s 送出=48000B 連線池佔用=0
TimingV1 斷線於=2    log={'duration': 0.0}  TTFB=1.0s 送出=16000B 連線池佔用=0
TimingV2 斷線於=None log={'duration': 6.0, 'buffered': 48000}  TTFB=6.0s 送出=48000B 連線池佔用=1
TimingV2 斷線於=2    log={'duration': 6.0, 'buffered': 48000}  TTFB=6.0s 送出=48000B 連線池佔用=1
TimingV3 斷線於=None log={'duration': 6.0}  TTFB=1.0s 送出=48000B 連線池佔用=1
TimingV3 斷線於=2    log={'duration': 2.0}  TTFB=1.0s 送出=16000B 連線池佔用=1
Timing   斷線於=None log={'duration': 6.0}  TTFB=1.0s 送出=48000B 連線池佔用=0
Timing   斷線於=2    log={'duration': 2.0}  TTFB=1.0s 送出=16000B 連線池佔用=0
```

逐版對照。`TimingV1` 在 app 回傳 `ExportBody` 時就停錶，耗時永遠是 0.0；它沒有攔截 iterable，`close()` 照樣傳到內層，問題只是量錯。`TimingV2` 耗時正確，但 TTFB 變成 6 秒（故事裡的四十秒），送出一整塊 48000 bytes，client 第 2 批後斷線也來不及了；它用 `b"".join` 消費完內層就丟掉，沒有呼叫 `close()`，連線池佔用 1。

`TimingV3` 的 TTFB 回到 1 秒、斷線時只送 16000 bytes，看起來完全正常，但連線池佔用都是 1：這就是故事裡一小時後才爆發的洩漏，每個請求只漏一條，累積到 40 條才讓 worker 卡住。正確的 `Timing` 回傳自己的 `_TimedBody`，`__iter__` 原樣交出每一段，`close()` 先呼叫內層的 `close()`，再在 `finally` 裡記錄耗時，於是完成時記 6 秒、斷線時記 2 秒，連線都歸還了。停錶放在 `close()`，量到的才是整個回應的生命週期。

### wsgi.file_wrapper 與 proxy 的緩衝

送大型檔案時，可選的擴充鍵 `environ["wsgi.file_wrapper"](file, block_size)` 回傳一個特殊的 iterable，server 認得它就改用核心的 `sendfile()` 直接把檔案搬到 socket，不認得就當普通 iterable；Werkzeug 與 Flask 的 `send_file()` 會自動使用它。不過聲聲 Live 的錄影檔由 nginx 直接服務（第 21 章），根本不經過 Python。

另一個讓人以為「串流壞了」的原因在前面的 proxy：nginx 預設開啟 `proxy_buffering`，先把上游回應收進自己的 buffer。這讓 gunicorn 的 worker 能盡快脫身，但對 SSE（第 31 章）這類要「立刻送到」的串流是災難，要讓這類回應帶上 `X-Accel-Buffering: no` 或在對應的 location 關閉 buffering。curl 直打 gunicorn 是串流、經過 nginx 變整塊，問題就在 proxy。

## 41.7 bytes 與 native string：PEP 3333 最常被誤解的一節

Python 3 嚴格區分 `str` 與 `bytes`，而 HTTP 線上傳的全是 bytes。PEP 3333 的答案是：**中繼資料（environ、狀態、header）用 native string（Python 3 的 `str`），body 用 bytes**。header 裡可能出現任意 bytes，所以一律用 **latin-1**（ISO-8859-1）解碼：latin-1 恰好把 0–255 每個 byte 對應到一個字元，任何 bytes 都能無損變成 `str`，需要時 `.encode("latin-1")` 原封不動拿回來。規格稱之為「bytes-as-unicode」。

| 項目 | 型別 | 規則 | 常見錯誤 |
|---|---|---|---|
| environ 的 CGI 變數與 `HTTP_*` | `str` | 由原始 bytes 以 latin-1 解碼 | 直接拿 `PATH_INFO` 當 UTF-8 文字用，非 ASCII 路徑變亂碼 |
| `status` | `str` | 只能有 latin-1 字元，不能有控制字元 | 傳整數 `200`、原因片語放中文 |
| header 名稱與值 | `str` | 只能有 latin-1 字元，不能有換行等控制字元 | 檔名直接放中文、把使用者輸入直接塞進 header |
| body（iterable 的每一項、`write()` 的參數） | `bytes` | app 自己決定編碼，並在 `Content-Type` 宣告 charset | 回傳 `str`、`[body]` 寫成 `body` |
| `wsgi.input.read()` 的回傳 | `bytes` | app 自己依 `Content-Type` 解碼 | 以為讀到的是 `str` |

為什麼不規定 UTF-8？因為 HTTP 不保證 header 是 UTF-8，server 擅自用 UTF-8 解碼，遇到非法序列只能報錯或替換字元，原始資訊就消失了。latin-1 是唯一「一定成功又可逆」的選擇，把編碼的決定權留給框架：Werkzeug 把 `PATH_INFO` 轉回 bytes 再以 UTF-8 解碼，Flask 的 view 才拿到正確的「美咲」。但有一種損失無法挽救：`PATH_INFO` 已經 decode 過，`/files/a%2Fb` 和 `/files/a/b` 長得一樣，需要分辨時只能求助 gunicorn 的 `RAW_URI` 這類非標準鍵，或在 API 設計上避免把斜線放進路徑參數。

回應方向同樣嚴格。下面用 `wsgiref.handlers.SimpleHandler`（不開 socket，輸出寫進 BytesIO）跑三個 app：header 直接放中文檔名、body 回傳 `str`，以及正確寫法，也就是 RFC 6266 與 RFC 8187 的 `filename*=UTF-8''<percent-encoded>`：

```python
import io
from urllib.parse import quote
from wsgiref.handlers import SimpleHandler
from wsgiref.util import setup_testing_defaults


def run(app):
    """用 wsgiref 的 SimpleHandler 跑一次 app，回傳送出的原始 bytes 與錯誤訊息。"""
    environ = {}
    setup_testing_defaults(environ)             # 填好 PEP 3333 規定的必要鍵
    out, err = io.BytesIO(), io.StringIO()
    handler = SimpleHandler(io.BytesIO(), out, err, environ)
    handler.error_status = "500 Internal Server Error"
    handler.run(app)
    last = err.getvalue().strip().splitlines()[-1:] or ["-"]
    return out.getvalue(), last[0]


def make_app(header_value, body):
    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/csv; charset=utf-8"),
                                  ("Content-Disposition", header_value)])
        return [body]
    return app


name = "美咲-2026-09.csv"
cases = {
    "header 直接放中文": make_app(f'attachment; filename="{name}"', "a,b\n".encode()),
    "body 回傳 str": make_app("attachment", "a,b\n"),
    "RFC 8187 編碼": make_app(f"attachment; filename*=UTF-8''{quote(name)}", "a,b\n".encode()),
}
results = {}
for label, app in cases.items():
    raw, error = run(app)
    status = raw.split(b"\r\n", 1)[0].decode()
    complete = b"\r\n\r\n" in raw              # header 區有沒有完整結束
    print(f"{label}：狀態列 {status!r}，header 完整={complete}，送出 {len(raw)} bytes")
    print(f"    stderr: {error[:60]}")
    results[label] = (status, complete)
    if label == "RFC 8187 編碼":
        print("   ", [l for l in raw.decode("latin-1").split("\r\n") if "Disposition" in l][0])

assert results["header 直接放中文"] == ("HTTP/1.0 200 OK", False)   # 狀態列已送出，header 寫到一半就斷
assert results["body 回傳 str"][0].endswith("500 Internal Server Error")
assert results["RFC 8187 編碼"] == ("HTTP/1.0 200 OK", True)
```

```text
header 直接放中文：狀態列 'HTTP/1.0 200 OK'，header 完整=False，送出 54 bytes
    stderr: UnicodeEncodeError: 'latin-1' codec can't encode characters 
body 回傳 str：狀態列 'HTTP/1.0 500 Internal Server Error'，header 完整=True，送出 180 bytes
    stderr: AssertionError: write() argument must be a bytes instance
RFC 8187 編碼：狀態列 'HTTP/1.0 200 OK'，header 完整=True，送出 200 bytes
    stderr: -
    Content-Disposition: attachment; filename*=UTF-8''%E7%BE%8E%E5%92%B2-2026-09.csv
```

第一種最值得注意：server 已送出狀態列與 `Date`，編碼 `Content-Disposition` 時才發現無法用 latin-1 表示。header 送了一半，沒辦法改成 500，client 收到 54 bytes、連 header 結尾空行都沒有的殘缺回應。第二種 body 是 `str`，錯誤發生在送出任何 byte 之前，wsgiref 還能改回乾淨的 500。第三種把 UTF-8 檔名 percent-encode 成純 ASCII，header 合法，瀏覽器會正確顯示「美咲-2026-09.csv」。

header 值不能有換行，也是安全規則：把使用者輸入（例如 redirect 目標）未經檢查放進 header，其中的 `\r\n` 就能插入額外的 header 甚至另一個回應，這叫 **header injection**（或 response splitting）。Werkzeug 的 `Headers` 與 `wsgiref.validate` 都會擋下，動手做的迷你 Headers 也實作了同樣的檢查。

## 41.8 middleware：洋蔥模型

**middleware**（中介層）是同時扮演兩個角色的 WSGI 元件：對外層（server 或更外面的 middleware）而言，它是一個 app，簽名就是 `(environ, start_response)`；對內層而言，它是一個 server，負責呼叫內層 app、提供（或包裝）`start_response`、迭代並轉交內層回傳的 iterable。因為兩端的介面完全一樣，middleware 可以任意疊加：`app = TrustedProxy(RequestId(Timing(flask_app)))`。

```text
                     請求 ───────────────────────────────────────────►
   gunicorn ──► ┌──────────────────────────────────────────────────────────┐
                │ TrustedProxy：改寫 REMOTE_ADDR、wsgi.url_scheme          │
                │  ┌────────────────────────────────────────────────────┐  │
                │  │ RequestId：決定 x-request-id，放進 environ         │  │
                │  │  ┌──────────────────────────────────────────────┐  │  │
                │  │  │ Timing：開始計時；包裝 body，close() 時停錶  │  │  │
                │  │  │  ┌────────────────────────────────────────┐  │  │  │
                │  │  │  │ Flask app：routing → view → Response   │  │  │  │
                │  │  │  └────────────────────────────────────────┘  │  │  │
                │  │  │  start_response 往外傳：Timing 記下狀態碼    │  │  │
                │  │  └──────────────────────────────────────────────┘  │  │
                │  │  start_response 往外傳：RequestId 加上 header      │  │
                │  └────────────────────────────────────────────────────┘  │
                └──────────────────────────────────────────────────────────┘
                     ◄─────────────────────── 回應（start_response、body、close()）
```

請求從外往內穿過每一層，回應從內往外：`start_response` 由內層發起，每一層都能在往外傳之前修改狀態與 header；body 的每一段也由內往外經過每一層的 iterable；最後 server 呼叫最外層的 `close()`，一路往內傳到 Flask 的 `ClosingIterator`。這就是**洋蔥模型**：請求剝進去、回應包出來。

順序有語意。TrustedProxy 在最外層，因為內層所有記錄 client 位址的地方都需要改寫過的 `REMOTE_ADDR`，放到 Timing 內側，Timing 記下的就永遠是 nginx。Timing 越外層量到的範圍越完整；錯誤處理 middleware 通常放最外面，才接得住任何一層的例外。推理方法是問：「這一層需要看到的東西，是被哪些層加上或改寫的？」那些層就要在它外面。

寫 middleware 要守住以下幾條規則，每一條都對應本章前面的一節規格，也對應一種真實事故：

| 規則 | 違反時的症狀 | 對應的規格 |
|---|---|---|
| 不緩衝 body，原樣轉交每一段 | TTFB 暴增、記憶體暴增、proxy 逾時 | 41.6 不得阻擋迭代 |
| 回傳自己的 iterable 時，`close()` 要往內傳 | 資源洩漏、`call_on_close` 不執行、teardown 不跑 | 41.6 close() |
| 包裝 `start_response` 時，原樣傳遞 `exc_info` 與回傳值 | 錯誤處理失效、`write()` 呼叫失敗 | 41.5 exc_info |
| 修改 header 時移除舊值再加，避免重複 | 回應出現兩個 `x-request-id` 或兩個 `Content-Length` | 41.5 header 清單 |
| 改了 body 長度就要修正或移除 `Content-Length` | client 截斷或卡住 | 41.5 Content-Length |
| 放進 environ 的自訂鍵加上前綴 | 和 server 或其他 middleware 撞名 | 41.4 擴充鍵 |
| 不要假設 iterable 是 list | `len()`、索引失敗 | 41.6 iterable |

第一條與第五條最容易衝突：gzip middleware 必須改變 body，所以要移除 `Content-Length`，並在壓縮器累積不足一個區塊時 `yield b""`，而不是等整個 body 結束。這也是許多團隊把壓縮交給 nginx 或 CDN 的原因。

Werkzeug 本身就附帶幾個常用的 middleware，都在 `werkzeug.middleware` 底下：

| middleware | 用途 | 注意事項 |
|---|---|---|
| `proxy_fix.ProxyFix` | 依 `X-Forwarded-*` 改寫 `REMOTE_ADDR`、scheme、host、port、prefix | 固定信任右邊 N 跳，設錯就可能被偽造（41.12 節） |
| `dispatcher.DispatcherMiddleware` | 依路徑前綴把請求分派給不同 app，並調整 `SCRIPT_NAME` | 適合把後台、舊版 API 掛在同一個 process |
| `shared_data.SharedDataMiddleware` | 開發時直接服務靜態檔 | production 交給 nginx 或 CDN |
| `profiler.ProfilerMiddleware` | 對每個請求做 cProfile 分析 | 有明顯效能成本，只在除錯時開 |
| `lint.LintMiddleware` | 檢查 WSGI 規格的違反，和 `wsgiref.validate` 類似 | 只在測試時使用 |
| `http_proxy.ProxyMiddleware` | 把部分路徑轉發到另一個 HTTP 服務 | 開發用途 |

## 41.9 Werkzeug：把 WSGI 包成好用的工具箱

直接寫 WSGI，每個 app 都要自己解析 query string、處理 cookie、拼 header，既囉唆又容易踩到 41.7 節的陷阱。**Werkzeug**（德文的「工具」）是 Armin Ronacher 從 2007 年開始開發的 WSGI 工具箱，現在和 Flask 一樣由 Pallets 專案維護。它不是框架，不管專案結構、模板與資料庫，只把 WSGI 的原始資料包成正確好用的物件，並提供 routing、開發伺服器、debugger 與測試工具；Flask 大部分的「HTTP 能力」都來自它。

```text
 ┌──────────────────────────────────── Werkzeug ────────────────────────────────────┐
 │  wrappers         Request（包住 environ） ◄──► Response（本身是 WSGI app）       │
 │      │                 │                              │                          │
 │      ▼                 ▼                              ▼                          │
 │  datastructures   MultiDict、Headers、EnvironHeaders、FileStorage                │
 │  http／formparser  解析 header、cookie、日期、multipart；sansio 層與 I/O 無關    │
 │  routing          Map、Rule、converter、MapAdapter.match()／build()              │
 │  exceptions       HTTPException（NotFound、MethodNotAllowed…），本身也是 WSGI app│
 │  middleware       ProxyFix、DispatcherMiddleware、SharedDataMiddleware…          │
 │  serving          run_simple：開發伺服器、reloader                               │
 │  debug            DebuggedApplication：互動式 traceback 與 console（PIN 保護）   │
 │  test             EnvironBuilder、Client：不開 socket 就能測試 WSGI app          │
 │  local／utils／security  LocalProxy、redirect、send_file、密碼雜湊工具…          │
 └──────────────────────────────────────────────────────────────────────────────────┘
          ▲ 只依賴 WSGI 介面                                    ▲ Flask 建在這裡
```

從上往下讀。`wrappers` 是最常碰到的一層，底下依賴 `datastructures` 的容器與 `http`、`formparser` 的解析器；解析邏輯整理成與 I/O 無關的「sansio」層，ASGI 框架也能重用。`routing`、`exceptions`、`middleware` 各自獨立，可以只用其中一塊。最下面是開發與測試工具。

### Request：延遲解析，而且知道規格的陷阱

`Request(environ)` 幾乎不做事，解析都是**延遲的**（lazy）：第一次讀 `request.args` 才解析 query string，第一次讀 `request.form` 才讀 body，結果會快取。只看路徑的請求不必付出解析 body 的成本，Werkzeug 也能在讀 body 前先檢查長度限制。下面是 Werkzeug 的真實介面（需要安裝 Werkzeug，本書不執行）：

```python
# not-runnable
from werkzeug.wrappers import Request, Response


@Request.application
def app(request: Request) -> Response:
    # GET /teachers/美咲?lang=ja&lang=en
    request.path                   # '/teachers/美咲'：已從 latin-1 轉回 UTF-8
    request.args.get("lang")       # 'ja'：只取第一個
    request.args.getlist("lang")   # ['ja', 'en']
    request.args.get("page", 1, type=int)   # 轉型失敗時回傳預設值
    request.headers.get("X-Request-Id")     # 名稱不分大小寫
    request.remote_addr            # 就是 environ['REMOTE_ADDR']，在 proxy 後面是 proxy
    raw = request.get_data()       # 原始 body bytes，會快取，驗證 webhook 簽章要用它
    request.get_json()             # Content-Type 不是 JSON 時會回 415（依版本而定）
    return Response("ok", mimetype="text/plain")
```

`@Request.application` 把「接收 Request、回傳 Response」的函式轉成 WSGI app，正好示範兩層的關係。body 大小由 `max_content_length`、`max_form_memory_size` 等屬性限制（Flask 的 `MAX_CONTENT_LENGTH`、`MAX_FORM_MEMORY_SIZE`），超過回 413。

**MultiDict** 是 Werkzeug 最有代表性的資料結構：一個 key 對應多個值。query string 與表單本來就允許重複的 key（`?lang=ja&lang=en`、多選 checkbox），用普通 dict 裝不是遺失資料就是型別不一致。`get()` 永遠回傳第一個值，`getlist()` 才回傳全部。這也有安全意義：如果 WAF 檢查最後一個、app 使用第一個，攻擊者就能用 **HTTP parameter pollution** 讓兩者看到不同的值，所以各層要約定同一種取法。

**Headers** 保留順序、名稱不分大小寫、允許重複（多個 `Set-Cookie` 必須分開送）；`set()` 取代同名的所有值，`add()` 追加一個，含換行的值會被拒絕。Request 端的 `EnvironHeaders` 則是 environ 的唯讀視圖，知道 `CONTENT_TYPE` 沒有 `HTTP_` 前綴這類規則。

### Response：一個會自己回應的物件

`Response(response=None, status=200, headers=None, mimetype=None, content_type=None)` 的 `response` 可以是 str、bytes 或 iterable（串流）。它**本身就是 WSGI app**：`response(environ, start_response)` 呼叫 `start_response` 並回傳 body，所以 Flask 的 `wsgi_app` 最後一行就是 `return response(environ, start_response)`。`set_cookie()` 產生 `Set-Cookie`（第 21 章的 `__Host-sid`），`call_on_close(func)` 登記 `close()` 時的清理，就是故事裡歸還資料庫連線的機制。`NotFound()`、`MethodNotAllowed(valid_methods=[...])` 這些 `HTTPException` 也是 WSGI app，所以「丟出 404」和「回傳 404」是同一件事，`abort(404)` 只是捷徑。

## 41.10 routing：Map、Rule 與 converter

**routing**（路由，和第 6 章的 IP 路由無關）是把「method ＋路徑」對應到「要執行哪段程式」的機制。Werkzeug 的設計有三個角色：**Rule** 是一條規則（路徑樣板、endpoint 名稱、允許的 method）；**Map** 是規則的集合；**MapAdapter** 是 Map 綁定到某個請求（host、scheme、`SCRIPT_NAME`、method）之後的產物，提供 `match()` 與 `build()`。路徑樣板裡的 `<int:class_id>` 這種段落由 **converter** 處理：它決定這一段可以匹配什麼（一段正規表示式），以及怎麼轉成 Python 值、怎麼轉回 URL。

```python
# not-runnable
from werkzeug.routing import BaseConverter, Map, Rule
from werkzeug.exceptions import HTTPException


class LessonIdConverter(BaseConverter):
    """錄影檔編號：lesson- 加四位數字，例如 lesson-0815。"""
    regex = r"lesson-\d{4}"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


url_map = Map([
    Rule("/teachers/", endpoint="teacher_list"),
    Rule("/teachers/<name>", endpoint="teacher"),
    Rule("/v1/classes/<int:class_id>/schedule", endpoint="schedule", methods=["GET", "PUT"]),
    Rule("/recordings/<lesson:lesson_id>", endpoint="recording"),
    Rule("/files/<path:subpath>", endpoint="file"),
], converters={"lesson": LessonIdConverter})

adapter = url_map.bind("api.shengsheng.example", url_scheme="https")
adapter.match("/v1/classes/7781/schedule", method="PUT")   # ('schedule', {'class_id': 7781})
adapter.build("teacher", {"name": "美咲"})                   # '/teachers/%E7%BE%8E%E5%92%B2'
try:
    adapter.match("/v1/classes/7781/schedule", method="DELETE")
except HTTPException as exc:
    exc.code                                                 # 405，Allow header 列出 GET、HEAD、PUT
```

`match()` 把路徑轉成 endpoint 與參數，`build()` 反向產生 URL（自動 percent-encoding），失敗則丟出 HTTP 例外。永遠用 endpoint 產生連結（Flask 的 `url_for`）而不手寫字串，改路徑時才不會留下死連結，掛在 `SCRIPT_NAME` 底下時前綴也自動正確。

```text
 請求：PUT /v1/classes/7781/schedule
   │
   ▼
 ① 依規則的「複雜度」排序比對（靜態段落優先於變數段落，與定義順序無關）
   │
   ├─ 路徑不符任何規則 ───────────────────────────────────────► 404 NotFound
   │
   ├─ 路徑符合，但 method 不在 methods 裡 ──► 記下允許的 method，繼續找其他規則
   │                                          都找不到 ─────────► 405 MethodNotAllowed（帶 Allow）
   │
   ├─ 規則以 / 結尾、請求沒有（strict_slashes） ───────────────► 308 RequestRedirect 到 .../
   │
   └─ 完全符合 ─► converter.to_python("7781") → 7781 ─────────► ('schedule', {'class_id': 7781})
```

這張流程圖有三個值得記住的行為。第一，比對順序**不是定義順序**：Werkzeug 依規則的組成排序（Werkzeug 2.2 起改用狀態機實作 matcher），靜態段落優先，所以 `/teachers/new` 一定會贏過 `/teachers/<name>`，不必擔心誰先定義。第二，method 不符和路徑不符是兩種錯誤：前者回 405 並在 `Allow` header 列出允許的 method，前端與 API client 據此知道「路徑對了、方法錯了」；規則允許 GET 時，HEAD 會被自動加入。第三，**strict slashes**：規則 `/teachers/` 以斜線結尾，請求 `/teachers` 會被 redirect 到 `/teachers/`，新版 Werkzeug 用 308（保留 method 與 body），舊版是 301。反過來，規則沒有結尾斜線而請求有，就是 404。

| converter | 匹配 | 轉成 | 例子 |
|---|---|---|---|
| `string`（預設） | 不含 `/` 的一段，可設 `minlength`、`maxlength`、`length` | `str` | `<name>` → `'美咲'` |
| `int` | 數字，可設 `fixed_digits`、`min`、`max`、`signed` | `int` | `<int:class_id>` → `7781`；`abc` 不匹配，回 404 |
| `float` | 小數 | `float` | `<float:rate>` |
| `path` | 可以包含 `/` | `str` | `<path:subpath>` → `'2026/09/report.csv'` |
| `uuid` | UUID 字串 | `uuid.UUID` | `<uuid:id>` |
| `any` | 列舉值之一 | `str` | `<any(ja,en):lang>` |
| 自訂（繼承 `BaseConverter`） | 自訂 `regex` | 自訂 `to_python` | `<lesson:lesson_id>` → `'lesson-0815'` |

converter 是驗證的第一道防線：`<int:class_id>` 讓 `abc` 進不了 view，回 404 而不是 500。但它不是授權檢查，匹配成功不代表使用者有權改第 7781 堂課（第 27 章）。`path` converter 的值拿去開檔案時，一定要用 `safe_join()` 或等價檢查擋住 `..`，否則就是路徑穿越漏洞。

## 41.11 dev server、reloader 與 interactive debugger

Werkzeug 的 `run_simple()` 是 `flask run` 背後的開發伺服器，建在標準函式庫的 `http.server` 之上（請求處理類別繼承自 `BaseHTTPRequestHandler`），再加上兩個讓開發變舒服的功能：程式碼改了自動重啟的 **reloader**，以及出錯時在瀏覽器裡顯示互動式 traceback 的 **debugger**。它的定位寫在啟動時的警告裡：這是開發伺服器，不要用在 production，請改用 production 等級的 WSGI server。

```python
# not-runnable
from werkzeug.serving import run_simple

run_simple("127.0.0.1", 5000, app,
           use_reloader=True,    # 監看檔案，改了就重啟
           use_debugger=True,    # 互動式 debugger：只能在自己的電腦上開
           threaded=True)        # 每個請求一個 thread；run_simple 預設 False，flask run 預設 True
```

```bash
flask --app shengsheng run --debug          # 等同開啟 reloader 與 debugger，預設只聽 127.0.0.1:5000
# ↓ 示意輸出
 * Serving Flask app 'shengsheng'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 123-456-789
```

除了 debugger 這個致命問題，開發伺服器的設計目標也不同：沒有 worker 管理與自動重生、沒有 graceful reload、對慢速 client 與惡意請求的防護遠不如 gunicorn。gunicorn 預先 fork 多個 worker、監控健康、在卡死時換掉（log 裡的 `WORKER TIMEOUT`），這些是 production 才需要的。

### reloader：兩個 process 的接力

```text
 $ flask run --debug
                                                   child process（WERKZEUG_RUN_MAIN=true）
 parent process（監看用）
 ① 執行你的模組（頂層程式碼第一次）
 ② 以 WERKZEUG_RUN_MAIN=true 重新啟動自己 ───────► ③ 再執行一次模組（頂層程式碼第二次）
                                                   ④ 啟動 server，處理請求
                                                   ⑤ 每秒檢查檔案 mtime（stat），或用 watchdog 接收事件
                                                   ⑥ 發現變更 → 以 exit code 3 結束
 ⑦ 看到 exit code 3 → 回到 ②，重新啟動 child ◄───── ⑥ 的 child 結束
```

reloader 不是在同一個 process 裡重新 import，而是讓 child process 整個結束再重開，不會有新舊模組物件並存。① parent 執行一次模組；② 帶著 `WERKZEUG_RUN_MAIN=true` 重新啟動自己；③④ child 再執行一次模組並啟動 server；⑤⑥ 發現檔案變更就以 exit code 3 結束；⑦ parent 看到 3 就重開。副作用是模組頂層的程式碼會**執行兩次**，在頂層啟動的背景 thread 或排程器開了 debug 就跑兩份；把這類初始化移出模組頂層，或檢查 `WERKZEUG_RUN_MAIN`。

### debugger：為什麼它等於遠端執行任意程式碼

`DebuggedApplication` 是一個 middleware：它包住你的 app，當內層丟出未處理的例外時，回傳一個 HTML 頁面，列出 traceback 的每一個 frame，而且每個 frame 旁邊都有一個 **console**：你可以在瀏覽器裡輸入 Python 運算式，在那個 frame 的區域變數環境中執行。這對開發非常方便，但換個角度講，它就是「一個讓網頁使用者在伺服器上執行任意 Python 程式的功能」：讀環境變數裡的資料庫密碼、讀任何檔案、執行系統指令，全都只是一行 Python。

為了降低誤開的風險，Werkzeug 加了 **PIN**：debugger 啟動時在終端機印出一組 PIN，第一次在瀏覽器使用 console 前必須輸入，通過後以 cookie 記住。PIN 由那台機器上的一些資訊推導而來（例如執行的使用者、模組路徑與機器識別資訊），同一台機器重啟後通常不變；連續輸入錯誤會被鎖定（截至 2026 年 10 月的 Werkzeug 3.1.x 是錯 10 次）。新版本也會檢查請求的 `Host` header，預設只接受 localhost 一類的名稱，用來擋 DNS rebinding 這類從瀏覽器繞進來的攻擊（細節依版本而定）。

但 PIN 只是**最後一道防線**，不是安全邊界。它的熵有限；它的推導材料是機器上的資訊，如果同一台機器另有讀檔漏洞，這些材料可能外洩；PIN 也會印在 log 裡，看得到 log 的人就看得到 PIN；而且有人會為了方便用 `WERKZEUG_DEBUG_PIN=off` 關掉它。所以規則很簡單，也沒有例外：**debugger 只能在開發者自己的電腦上、只聽 127.0.0.1**。production 與 staging 一律不開 debug，錯誤由 gunicorn 的 log 與錯誤追蹤服務收集，回應裡只放 `x-request-id`。

```text
 故事裡 staging 的狀況                                  正確的配置
 辦公室 VPN 10.8.0.0/16 ──┐                             開發者筆電
                          ▼                              flask run --debug
 staging 10.21.3.21:5000  flask run --debug              └─ 只聽 127.0.0.1:5000
   └─ --host 0.0.0.0：所有介面                            staging／production
   └─ 任何能連到 5000 的人都看得到 traceback             gunicorn，debug 關閉
   └─ 能看到 Server: Werkzeug/... header                 錯誤 → log／錯誤追蹤，回應只帶 x-request-id
   └─ 離任意程式碼執行只差一個 PIN                        security group 只放行 LB → 8000
```

左邊是故事中 Rita 發現的狀況：問題不只是「開了 debug」，而是三個錯誤疊在一起：用了開發伺服器、開了 debugger、還把它綁在所有網路介面上。右邊是正確的配置。Rita 的處理順序也值得照抄：先關掉服務並封鎖該 port（止血）；再假設主機上的祕密可能已外洩，輪替環境變數裡的資料庫密碼與 API 金鑰；接著檢查存取 log 有沒有 `/console` 之類的請求；最後補上預防措施：部署檢查禁止 `FLASK_DEBUG`、內部掃描固定比對 `Server: Werkzeug` header 與 debugger 頁面特徵、security group 不放行開發 port。

## 41.12 ProxyFix、DispatcherMiddleware 與 test client

### ProxyFix：只信任你知道存在的那幾層

第 25 章講過，在 CDN、LB、nginx 後面，`REMOTE_ADDR` 永遠是最近一層 proxy，真正的 client 位址在 `X-Forwarded-For` 裡，而且只有自家 proxy 寫下的部分可信。Werkzeug 的 **ProxyFix** 是這條規則的固定跳數實作：你告訴它每個 header 有幾層可信的 proxy，它就從右邊數過去，取出對應的值，改寫 environ 的 `REMOTE_ADDR`、`wsgi.url_scheme`、`HTTP_HOST`、`SERVER_PORT` 與 `SCRIPT_NAME`，原始值保留在 `environ["werkzeug.proxy_fix.orig"]` 裡供除錯。

```python
# not-runnable
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# 包住 app.wsgi_app 而不是 app：app 仍是 Flask 物件，設定與測試都不受影響
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0, x_port=0, x_prefix=0)
```

`x_for=1` 的意思是「`X-Forwarded-For` 最右邊的 1 個值是可信的 proxy 寫的，取它當 client」。這只在**每個請求都恰好經過固定層數**的情況下正確；第 25 章示範過，聲聲 Live 的請求有的經過 CDN、有的直連 LB，固定跳數會在其中一條路徑上取錯。canon 的做法是：面對 internet 的那一層覆寫 XFF、內部各層附加，由最靠近 app 的自家 proxy（或 app 前的 middleware）從右往左解析、跳過可信網段（10.20.0.0/16 與 CDN 回源網段 198.51.100.224/27）。動手做的 `TrustedProxy` middleware 就實作這套規則，第 43 章再談 nginx 的 realip 與 ProxyFix 的實際部署設定。不論哪種做法，`x_proto` 與 `x_host` 都只能在確定前面的 proxy 會覆寫這些 header 時才開，否則 client 就能自己送 `X-Forwarded-Host` 汙染你產生的連結。

### DispatcherMiddleware：一個 process 裡掛好幾個 app

```python
# not-runnable
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from shengsheng.api import app as api_app       # 主要的 Flask app
from shengsheng.legacy import app as legacy_app  # 舊版 API，另一個 Flask app

application = DispatcherMiddleware(api_app, {"/legacy": legacy_app})
# GET /legacy/v0/lessons → legacy_app 看到 SCRIPT_NAME='/legacy'、PATH_INFO='/v0/lessons'
```

`DispatcherMiddleware` 依前綴分派，並把前綴從 `PATH_INFO` 移到 `SCRIPT_NAME`，正是 41.4 節掛載點的用途：舊版 API 不知道自己被掛在 `/legacy` 底下，`url_for` 產生的連結卻自動帶上前綴。適合遷移期間共用 worker；長期來說，獨立部署、由 nginx 依路徑分流更好隔離。

### test client：不開 socket 也能測 HTTP

WSGI app 只是一個函式，測試時不需要啟動 server：組 environ、呼叫 app、收集 `start_response` 的參數與 body 即可。Werkzeug 的 `EnvironBuilder` 正確組出 environ（percent-encoding、multipart、JSON、cookie），`Client` 在其上模擬瀏覽器，保存 cookie、跟隨 redirect；Flask 的 `app.test_client()` 就是它的子類別。

```python
# not-runnable
from werkzeug.test import Client

client = Client(app)
resp = client.get("/teachers/美咲", query_string={"lang": ["ja", "en"]})
assert resp.status_code == 200 and resp.json["teacher"] == "美咲"

resp = client.put("/v1/classes/7781/schedule", json={"slots": ["20:00"]},
                  headers={"Authorization": "Bearer <測試用 token>"})
assert resp.status_code in (200, 401, 403)
```

這種測試快、穩定，測到的是真正的 WSGI 介面；盲點是不經過 gunicorn、nginx 與真實 socket，測不到 keep-alive、timeout、proxy header 與緩衝，要另外在真實 server 上做整合測試，動手做的實驗三就是縮小版。

## 41.13 Flask 如何建在 Werkzeug 上

Flask 的 app 物件**就是一個 WSGI callable**：`Flask.__call__(environ, start_response)` 只做一件事，就是呼叫 `self.wsgi_app(environ, start_response)`。之所以多一層 `wsgi_app`，是為了讓你可以像 41.12 節那樣把 middleware 套在 `app.wsgi_app` 上，而 `app` 本身仍然是 Flask 物件。下面是 Flask 3.x 的 `wsgi_app` 精簡後的樣子（省略了部分細節，真實程式碼請以 Flask 原始碼為準）：

```python
# not-runnable
def wsgi_app(self, environ, start_response):
    ctx = self.request_context(environ)      # 建立 Request（Werkzeug）與 URL adapter
    error = None
    try:
        try:
            ctx.push()                       # 推入 app context 與 request context，做 URL 比對
            response = self.full_dispatch_request()   # before_request → view → after_request
        except Exception as e:
            error = e
            response = self.handle_exception(e)       # 未處理的例外 → 500（debug 時改為往外拋）
        return response(environ, start_response)      # Werkzeug Response 本身就是 WSGI app
    finally:
        ctx.pop(error)                       # teardown_request／teardown_appcontext 在這裡執行
```

這十幾行揭露了一個關鍵時序：`ctx.pop()` 在 `finally` 裡，也就是 `wsgi_app` **回傳**時就執行，而不是 body 送完時。一般回應沒有差別；串流 generator 卻要等 server 迭代才執行，那時 context 已彈出、`teardown_request` 已跑完。所以 generator 裡讀 `request` 會得到「Working outside of request context」，要用 `stream_with_context()` 延長 context；「串流結束才能歸還資料庫連線」這種清理不能放在 `teardown_request`，要放在 `call_on_close()`。

```text
 Flask.__call__ ─► wsgi_app
   │ ① request_context(environ)：Request(environ) ＋ url_map.bind_to_environ(environ)
   │ ② ctx.push()：app context（current_app、g）＋ request context（request、session）
   │      └─ match_request()：Werkzeug MapAdapter.match() → endpoint、view_args（或 404／405）
   │ ③ full_dispatch_request()
   │      ├─ before_request 函式（任何一個回傳值就短路，例如驗證失敗回 401）
   │      ├─ view_functions[endpoint](**view_args)
   │      ├─ make_response(rv)：str／dict／tuple → Response
   │      └─ after_request 函式、儲存 session（Set-Cookie）
   │ ④ return response(environ, start_response)：呼叫 start_response，回傳 iterable
   │ ⑤ finally ctx.pop()：teardown_request、teardown_appcontext ← 此時 body 可能還沒送！
   ▼
 server 迭代 body、送出、呼叫 close() → call_on_close 登記的函式
```

① 建立 Werkzeug 的 Request 與 MapAdapter；② 推入兩個 context 並比對 URL，失敗的 404、405 會先記下，留到 ③ 才丟出，讓 `before_request` 先跑；④ 回到純 WSGI；⑤ 清理。`request`、`g`、`current_app` 看似全域變數，其實是 **context-local proxy**：現在的 Flask 用 `contextvars` 實作，每個 thread（或 greenlet、asyncio task）看到自己那一份。所以在自己開的背景 thread 裡用 `request` 會失敗：那個 thread 沒有被推入 request context。

| Flask 的概念 | 底下的 Werkzeug 零件 | 你在工作上會碰到的地方 |
|---|---|---|
| `app(environ, start_response)` | WSGI callable | gunicorn 的 `module:app` 指的就是它 |
| `flask.request` | `werkzeug.wrappers.Request` 的子類別，經 context-local proxy 存取 | `request.args`、`get_data()`、`remote_addr` |
| `flask.Response`、`make_response` | `werkzeug.wrappers.Response` 的子類別 | `set_cookie`、`call_on_close`、串流 |
| `@app.route`、`url_for` | `Map`、`Rule`、converter、`MapAdapter.build()` | 404、405、308、自訂 converter |
| `abort(404)`、錯誤處理器 | `werkzeug.exceptions` | `@app.errorhandler(404)` 回 problem details |
| `app.run()`、`flask run` | `werkzeug.serving.run_simple` | 只用在開發 |
| `debug=True` | `werkzeug.debug.DebuggedApplication` | 絕不上 production |
| `app.test_client()` | `werkzeug.test.Client` | 單元測試 |
| `MAX_CONTENT_LENGTH` 等設定 | `Request.max_content_length` 等屬性 | 413 錯誤 |

遇到 Flask 的某個行為不知從何而來時，往右一欄找：「`/teachers` 為什麼被 redirect 到 `/teachers/`」是 routing 的 strict slashes，「`request.form` 讀完後 `get_data()` 為什麼是空的」是 body 只能讀一次，都不是 Flask 自己的設計。

```python
# not-runnable
from flask import Flask, Response, g, request, stream_with_context

app = Flask(__name__)


@app.get("/teachers/reports/<month>.csv")
def export_report(month):
    conn = db_pool.acquire()                 # 向連線池借一條資料庫連線
    def rows():
        yield "lesson,student,minutes\n"
        for row in conn.iter_rows("SELECT ... WHERE month = %s", month):
            yield ",".join(map(str, row)) + "\n"
    resp = Response(stream_with_context(rows()), mimetype="text/csv")
    resp.call_on_close(conn.release)         # 串流結束、出錯或斷線時才歸還
    return resp
```

這是故事中匯出 view 的骨架：`stream_with_context` 讓 generator 仍能使用 `request` 與 `g`；`call_on_close` 把歸還連線綁在 WSGI 的 `close()` 上，只要每一層 middleware 都把 `close()` 往內傳，不論下載完成或中途關分頁，連線都會歸還。v3 斷掉的就是這條鏈。

## 41.14 一個請求的完整旅程：從 socket 到 Flask view 再回來

現在把全書 Part 9 的拼圖接起來。下圖是老師下載月報的一個請求，在 app 主機 10.20.3.21 上的完整時序；前面 CDN、LB、nginx 的部分見第 25 章，nginx 與 gunicorn 之間的 timeout 鏈見第 43 章。

```text
 nginx 10.20.3.11       gunicorn（gthread）         middleware 洋蔥         Flask／Werkzeug
   │── SYN、SYN+ACK、ACK ──────►│                         │                       │  ① 核心完成交握，worker 呼叫 accept()
   │── GET …/2026-09.csv ──────►│                         │                       │  ② 解析請求；拒絕重複 CL、CL＋TE
   │                            │                         │                       │  ③ 組 environ：REMOTE_ADDR=10.20.3.11
   │                            │── app(environ, sr) ────►│                       │  ④ TrustedProxy → RequestId → Timing
   │                            │                         │── wsgi_app(...) ─────►│  ⑤ push context、match、執行 view
   │                            │                         │◄── sr("200 OK", h) ───│  ⑥ start_response 由內往外傳
   │                            │◄── sr＋x-request-id ────│                       │     gunicorn 先存起來，還不送
   │                            │                         │◄── return iterable ───│  ⑦ ctx.pop()、teardown：body 還沒產生
   │                            │◄── return iterable ─────│                       │
   │◄── 200＋header＋第一批 ────│                         │                       │  ⑧ 第一個非空 chunk 才送 header
   │◄── 後續批次（串流） ───────│                         │                       │     每批由 generator 現做現送
   │                            │── close() ─────────────►│                       │  ⑨ 送完（或 client 斷線）呼叫 close()
   │                            │                         │── close() 往內傳 ────►│  ⑩ Timing 停錶；call_on_close 歸還連線
   │◄── FIN ────────────────────│                         │                       │  ⑪ 關閉連線，處理下一個請求
```

逐步走一遍。① 交握由核心完成，worker 呼叫 `accept()` 才拿到連線（第 10 章）。② gunicorn 用自己的解析器讀請求，新版會拒絕重複的 `Content-Length` 或 CL 與 TE 並存的請求，這是第 20 章 request smuggling 的防線。③ 組出 environ：`REMOTE_ADDR` 是 nginx 的 10.20.3.11，`wsgi.url_scheme` 是 `http`，因為 TLS 在 LB 就終結了。④ TrustedProxy 改寫出真正的老師位址，RequestId 沿用 nginx 帶來的 id，Timing 開始計時。

⑤ Flask 推入 context，比對出 `export_report` 與 `month='2026-09'`，view 建立串流 Response 就回傳，只花幾毫秒。⑥ `start_response("200 OK", ...)` 由內往外穿過每一層，RequestId 加上 `x-request-id`，gunicorn 存起來還不送。⑦ `wsgi_app` 回傳，context 彈出、`teardown_request` 執行，此時 CSV 一列都還沒產生。⑧ gunicorn 開始迭代，generator 讀第一批資料庫列，產出第一個非空 chunk，gunicorn 這時才把狀態列與 header 寫進 socket。因為沒有 `Content-Length`，body 的結尾要另外劃定：nginx 對上游預設用 HTTP/1.0（第 20 章），gunicorn 就以「送完關閉連線」表示結束；如果 nginx 設了 `proxy_http_version 1.1`，則改用 chunked。

⑨ 最後一批送完，gunicorn 呼叫最外層的 `close()`，⑩ 每一層往內傳：Timing 停錶寫下「rid=… 200 18MB 41.2 s」，最內層的 `ClosingIterator` 執行 `conn.release`。⑪ 連線關閉，worker 的這個 thread 回去處理下一個請求；如果 nginx 開了上游 keep-alive，gthread worker 會讓連線閒置最多 `--keep-alive` 秒（預設 2 秒）等下一個請求。面對 internet 的慢速 client 與長時間保持的連線，則一律交給前面的 nginx（第 43 章）。老師若在 ⑧ 中途關掉分頁，nginx 會關閉對上游的連線（依設定而定），gunicorn 寫入失敗後直接跳到 ⑨，`close()` 照樣被呼叫，正是 41.6 節「斷線於=2」的情況。

對照 log 就能判斷時間花在哪裡：nginx 的 `$upstream_response_time` 涵蓋 ②到⑪，Timing 涵蓋 ④到⑩，view 裡的 log 只涵蓋 ⑤，也就是第 1 章說的「Flask log 裡的 30 毫秒」。三者的差距告訴你問題在排隊、middleware，還是 body 的產生與傳送。

## 41.15 2026 現況

> [!note] 2026 現況
> 以下依 2026 年 10 月查證，版本會持續變動，部署前請以各專案的 changelog 為準。
>
> - **WSGI**：規格仍是 PEP 3333（2010），內容穩定，沒有新版本的計畫；新的非同步需求由 ASGI 承接（第 42 章）。
> - **Werkzeug**：截至 2026 年 10 月最新為 3.1.9（2026-09-27），3.x 仍是最新主版本。3.1.7–3.1.9 強化了 `Request.host` 的字元驗證，3.1.9 調整了 urlencoded 表單的上限邏輯並改進容器環境下的 debugger PIN 產生；3.1.4 起 debugger PIN 錯 10 次就鎖定；3.1.0 移除了已 deprecated 的功能並放棄 Python 3.8。
> - **Flask**：截至 2026 年 10 月最新為 3.1.3（2026-02-18），尚未見 3.2 正式版。3.1.0 起要求 Werkzeug 3.1 以上，新增 `SECRET_KEY_FALLBACKS`（session 簽章金鑰輪替）、`SESSION_COOKIE_PARTITIONED`、`MAX_FORM_MEMORY_SIZE`、`MAX_FORM_PARTS`；3.1.1 與 3.1.3 各修補了一個 session 相關的安全問題。
> - **gunicorn**：截至 2026 年 10 月已進入 26.x（26.2.x），要求 Python 3.10 以上。傳統上以 WSGI 為主，新版也內建 ASGI worker（25.1 起 stable），並有 HTTP/2（beta）。25.3 與 26.x 加入大量 request smuggling 防護（拒絕重複 `Content-Length`、`Content-Length` 與 `Transfer-Encoding` 並存、重複 `Host` 等）；26.2.0 修補了 HTTP/2 路徑未套用 header 政策、可能讓 client 影響 environ 的問題，和 41.4 節的 header 名稱對應問題屬於同一類。
> - **uWSGI**：官方已宣告進入維護模式，新專案通常選 gunicorn、Waitress 或 mod_wsgi。

## 41.16 動手做：只用標準函式庫重建 WSGI 堆疊

這一節用三段只靠標準函式庫的程式重建本章的每一層：先認識規格檢查器 `wsgiref.validate`，再寫迷你版 Werkzeug，最後寫三個 middleware，層層夾著 validator，在 127.0.0.1（port 0）上用 `wsgiref.simple_server` 跑起來並以 `http.client` 測試。

### 實驗一：讓 wsgiref.validate 抓出常見的違規

`wsgiref.validate.validator(app)` 是一個 middleware，它不改變任何行為，只在 app 或 server 違反規格時丟出 `AssertionError`。下面讓它檢查五個有 bug 的 app 和一個正確的 app：

```python
import io
import sys
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator


def body_is_str(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return ["hello"]                                  # 應該是 bytes


def no_content_type(environ, start_response):
    start_response("200 OK", [("Content-Length", "2")])
    return [b"ok"]


def read_everything(environ, start_response):
    environ["wsgi.input"].read()                      # 沒給長度：可能讀過頭或卡住
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"ok"]


def status_is_int(environ, start_response):
    start_response(200, [("Content-Type", "text/plain")])
    return [b"ok"]


def header_value_newline(environ, start_response):
    start_response("302 Found", [("Content-Type", "text/plain"),
                                 ("Location", "/next\r\nSet-Cookie: x=1")])  # header injection
    return [b""]


def correct(environ, start_response):
    size = int(environ.get("CONTENT_LENGTH") or 0)
    data = environ["wsgi.input"].read(size)
    start_response("200 OK", [("Content-Type", "text/plain"), ("Content-Length", str(len(data)))])
    return [data]


def check(app):
    environ = {"REQUEST_METHOD": "POST", "SCRIPT_NAME": "", "PATH_INFO": "/", "QUERY_STRING": "",
               "CONTENT_LENGTH": "5", "wsgi.input": io.BytesIO(b"hello")}
    setup_testing_defaults(environ)
    try:
        result = validator(app)(environ, lambda s, h, e=None: None)
        try:
            body = b"".join(result)
        finally:
            result.close()                            # 少了這行，validator 會在 GC 時抱怨
        return f"通過，body={body!r}"
    except AssertionError as exc:
        return f"AssertionError: {str(exc) or '（沒有訊息，見下方解說）'}"


verdicts = {}
for app in (body_is_str, no_content_type, read_everything, status_is_int, header_value_newline, correct):
    verdicts[app.__name__] = check(app)
    print(f"{app.__name__:<21} {verdicts[app.__name__][:72]}")

assert verdicts["correct"] == "通過，body=b'hello'"
assert all(v.startswith("AssertionError") for k, v in verdicts.items() if k != "correct")
```

```text
body_is_str           AssertionError: Iterator yielded non-bytestring ('hello')
no_content_type       AssertionError: No Content-Type header found in headers ([('Content-Leng
read_everything       AssertionError: （沒有訊息，見下方解說）
status_is_int         AssertionError: Status must be of type str (got 200)
header_value_newline  AssertionError: Bad header value: '/next\r\nSet-Cookie: x=1' (bad char: 
correct               通過，body=b'hello'
```

前五行各對應一條規則。`body_is_str` 回傳 `str`（41.7 節）。`no_content_type` 缺 `Content-Type`：validator 要求 204、304 以外都要宣告，比規格嚴格，但少了它瀏覽器會自己猜型別（MIME sniffing，第 23 章）。`read_everything` 的錯誤沒有訊息，因為 validator 的 `InputWrapper.read()` 直接斷言必須帶 size 參數（41.4 節）。`status_is_int` 把狀態寫成整數。`header_value_newline` 在 `Location` 裡夾帶 `\r\n`，就是 header injection。正確版依 `CONTENT_LENGTH` 讀 body、回傳 bytes 的 list。`check()` 在 `finally` 裡呼叫 `result.close()`，因為 validator 也檢查 server 端：iterable 沒被關閉就被回收時，它會印出「Iterator garbage collected without being closed」。

### 實驗二：迷你版 Werkzeug

這段約兩百行的程式與 41.9、41.10 節的架構一一對應：`MultiDict`、`Headers` 是 datastructures，`Request`、`Response` 是 wrappers，`HTTPException` 是 exceptions，`Rule`、`MapAdapter` 是 routing（含自訂 converter），`App` 是極簡框架，`client()` 是包著 `wsgiref.validate`、不開 socket 的 test client：

```python
import io
import json
import re
from http import HTTPStatus
from urllib.parse import parse_qsl, quote, unquote
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator


# ── 資料結構：同一個 key 可以有多個值（?lang=ja&lang=en） ───────────────────
class MultiDict:
    def __init__(self, pairs=()):
        self._d = {}
        for k, v in pairs:
            self._d.setdefault(k, []).append(v)
    def get(self, key, default=None, type=None):
        if key not in self._d:
            return default
        return type(self._d[key][0]) if type else self._d[key][0]
    def getlist(self, key):
        return list(self._d.get(key, []))


class Headers:
    """回應 header：保留順序、名稱不分大小寫、允許重複（Set-Cookie），拒絕換行（header injection）。"""
    def __init__(self, items=()):
        self._items = []
        for k, v in items:
            self.add(k, v)
    def add(self, key, value):
        if "\r" in str(value) or "\n" in str(value):
            raise ValueError("header 值不可包含換行")
        self._items.append((key, str(value)))
    def set(self, key, value):
        self._items = [(k, v) for k, v in self._items if k.lower() != key.lower()]
        self.add(key, value)
    def get(self, key, default=None):
        return next((v for k, v in self._items if k.lower() == key.lower()), default)
    def to_wsgi_list(self):
        return list(self._items)


# ── Request：把 environ 包成好用的物件，能延後解析的都延後 ──────────────────
class Request:
    max_content_length = 64 * 1024
    def __init__(self, environ):
        self.environ, self._data = environ, None
        self.method = environ["REQUEST_METHOD"].upper()
        self.path = environ.get("PATH_INFO", "/").encode("latin-1").decode("utf-8", "replace")
        self.args = MultiDict(parse_qsl(environ.get("QUERY_STRING", ""), keep_blank_values=True))
    def header(self, name):
        key = name.upper().replace("-", "_")
        return self.environ.get(key if key in ("CONTENT_TYPE", "CONTENT_LENGTH") else "HTTP_" + key)
    def get_data(self):
        if self._data is None:                  # wsgi.input 只能讀一次，所以要快取
            length = int(self.environ.get("CONTENT_LENGTH") or 0)
            if length > self.max_content_length:
                raise HTTPException(413)
            self._data = self.environ["wsgi.input"].read(length)
        return self._data
    def get_json(self):
        if not (self.header("Content-Type") or "").startswith("application/json"):
            raise HTTPException(415)
        try:
            return json.loads(self.get_data())
        except ValueError:
            raise HTTPException(400, "body 不是合法的 JSON")


# ── Response：本身就是一個 WSGI app ─────────────────────────────────────────
class Response:
    def __init__(self, body=b"", status=200, headers=(), mimetype="text/plain; charset=utf-8"):
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.status, self.headers, self._on_close = status, Headers(headers), []
        self.headers.set("Content-Type", self.headers.get("Content-Type", mimetype))
    def call_on_close(self, func):
        self._on_close.append(func)
    def __call__(self, environ, start_response):
        status = f"{self.status} {HTTPStatus(self.status).phrase}"
        self.headers.set("Content-Length", len(self.body))
        start_response(status, self.headers.to_wsgi_list())
        return _ClosingIterator([self.body], self._on_close)


class _ClosingIterator:
    def __init__(self, it, callbacks): self.it, self.callbacks = it, callbacks
    def __iter__(self): return iter(self.it)
    def close(self):
        for cb in self.callbacks:
            cb()


class HTTPException(Exception):
    def __init__(self, code, detail=None, headers=()):
        super().__init__(code)
        self.code, self.detail, self.headers = code, detail or HTTPStatus(code).description, headers
    def get_response(self):                     # 錯誤也用 problem details（第 24 章）
        body = json.dumps({"status": self.code, "title": HTTPStatus(self.code).phrase,
                           "detail": self.detail}, ensure_ascii=False)
        return Response(body, self.code, self.headers, "application/problem+json")


# ── Routing：Map／Rule／converter ──────────────────────────────────────────
CONVERTERS = {"string": (r"[^/]+", str), "int": (r"\d+", int), "path": (r"[^/].*?", str),
              "lesson": (r"lesson-\d{4}", str)}  # 最後一個是自訂 converter


class Rule:
    def __init__(self, pattern, endpoint, methods=("GET",)):
        self.pattern, self.endpoint = pattern, endpoint
        self.methods = set(methods) | ({"HEAD"} if "GET" in methods else set())
        self.convs, regex = {}, ""
        for static, conv, name in re.findall(r"([^<]*)(?:<(?:(\w+):)?(\w+)>)?", pattern):
            regex += re.escape(static)
            if name:
                self.convs[name] = CONVERTERS[conv or "string"]
                regex += f"(?P<{name}>{self.convs[name][0]})"
        self.regex = re.compile(f"^{regex}$")
        self.weight = (len(self.convs), -len(pattern))   # 靜態規則優先於含變數的規則


class MapAdapter:
    def __init__(self, rules, method, path):
        self.rules, self.method, self.path = sorted(rules, key=lambda r: r.weight), method, path
    def match(self):
        allowed = set()
        for rule in self.rules:
            m = rule.regex.match(self.path) or (rule.pattern.endswith("/") and rule.regex.match(self.path + "/"))
            if not m:
                continue
            if self.method not in rule.methods:
                allowed |= rule.methods
                continue
            if not self.path.endswith("/") and rule.pattern.endswith("/"):
                raise HTTPException(308, headers=[("Location", quote(self.path + "/"))])
            return rule.endpoint, {k: rule.convs[k][1](v) for k, v in m.groupdict().items()}
        if allowed:
            raise HTTPException(405, headers=[("Allow", ", ".join(sorted(allowed)))])
        raise HTTPException(404)
    def build(self, endpoint, **values):
        rule = next(r for r in self.rules if r.endpoint == endpoint)
        return re.sub(r"<(?:\w+:)?(\w+)>", lambda m: quote(str(values[m.group(1)])), rule.pattern)
# ── 框架本體：把上面的零件組起來 ─────────────────────────────────────────────
class App:
    def __init__(self):
        self.rules, self.views = [], {}
    def route(self, pattern, methods=("GET",)):
        def deco(view):
            self.rules.append(Rule(pattern, view.__name__, methods))
            self.views[view.__name__] = view
            return view
        return deco
    def __call__(self, environ, start_response):  # 這就是 WSGI callable
        request = Request(environ)
        adapter = MapAdapter(self.rules, request.method, request.path)
        try:
            endpoint, values = adapter.match()
            rv = self.views[endpoint](request, **values)
            response = rv if isinstance(rv, Response) else Response(
                json.dumps(rv, ensure_ascii=False), mimetype="application/json")
        except HTTPException as exc:
            response = exc.get_response()
        except Exception as exc:                 # 細節寫進 log，回應裡不放 stack trace
            environ["wsgi.errors"].write(f"unhandled {type(exc).__name__}: {exc}\n")
            response = HTTPException(500, "請附上 x-request-id 聯絡我們").get_response()
        return response(environ, start_response)


app = App()

@app.route("/teachers/")
def teacher_list(request):
    return {"teachers": ["美咲", "teacher05"]}

@app.route("/teachers/<name>")
def teacher(request, name):
    return {"teacher": name, "lang": request.args.getlist("lang")}

@app.route("/v1/classes/<int:class_id>/schedule", methods=("GET", "PUT"))
def schedule(request, class_id):
    if request.method == "PUT":
        return {"class_id": class_id, "saved": request.get_json()["slots"]}
    return {"class_id": class_id, "slots": []}

@app.route("/recordings/<lesson:lesson_id>")
def recording(request, lesson_id):
    return {"lesson": lesson_id}

@app.route("/boom")
def boom(request):
    raise RuntimeError("db password=hunter2")    # 這種字串絕不能出現在回應裡


def client(method, url, body=b"", content_type="application/json"):
    """測試 client：不開 socket，直接組 environ 呼叫 app（外面包 wsgiref.validate 檢查規格）。"""
    path, _, query = url.partition("?")
    environ = {"REQUEST_METHOD": method, "SCRIPT_NAME": "", "PATH_INFO": unquote(quote(path), "latin-1"),
               "QUERY_STRING": query, "CONTENT_TYPE": content_type,
               "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body),
               "wsgi.errors": io.StringIO()}
    setup_testing_defaults(environ)
    captured = {}
    result = validator(app)(environ, lambda s, h, e=None: captured.update(status=s, headers=dict(h)))
    try:
        data = b"".join(result)
    finally:
        result.close()
    return captured["status"], captured["headers"], data.decode("utf-8")


cases = [("GET", "/teachers/美咲?lang=ja&lang=en"), ("GET", "/teachers"),
         ("GET", "/v1/classes/7781/schedule"), ("GET", "/v1/classes/abc/schedule"),
         ("PUT", "/v1/classes/7781/schedule", b'{"slots": ["20:00"]}'),
         ("PUT", "/v1/classes/7781/schedule", b"{oops"), ("DELETE", "/v1/classes/7781/schedule"),
         ("GET", "/recordings/lesson-0815"), ("GET", "/recordings/0815"), ("GET", "/boom")]
out = {}
for method, url, *body in cases:
    status, headers, text = client(method, url, *body)
    extra = "".join(f" {k}: {headers[k]}" for k in ("Location", "Allow") if k in headers)
    out[method, url] = status
    detail = json.loads(text).get("detail") if status[0] in "345" else text
    print(f"{method:<6} {url:<32} → {status}{extra}\n{'':<8}{detail}")

assert out["GET", "/teachers"] == "308 Permanent Redirect"
assert out["DELETE", "/v1/classes/7781/schedule"] == "405 Method Not Allowed"
assert out["GET", "/v1/classes/abc/schedule"] == out["GET", "/recordings/0815"] == "404 Not Found"
print("build →", MapAdapter(app.rules, "GET", "/").build("teacher", name="美咲"))
```

```text
GET    /teachers/美咲?lang=ja&lang=en     → 200 OK
        {"teacher": "美咲", "lang": ["ja", "en"]}
GET    /teachers                        → 308 Permanent Redirect Location: /teachers/
        Object moved permanently -- see URI list
GET    /v1/classes/7781/schedule        → 200 OK
        {"class_id": 7781, "slots": []}
GET    /v1/classes/abc/schedule         → 404 Not Found
        Nothing matches the given URI
PUT    /v1/classes/7781/schedule        → 200 OK
        {"class_id": 7781, "saved": ["20:00"]}
PUT    /v1/classes/7781/schedule        → 400 Bad Request
        body 不是合法的 JSON
DELETE /v1/classes/7781/schedule        → 405 Method Not Allowed Allow: GET, HEAD, PUT
        Specified method is invalid for this resource
GET    /recordings/lesson-0815          → 200 OK
        {"lesson": "lesson-0815"}
GET    /recordings/0815                 → 404 Not Found
        Nothing matches the given URI
GET    /boom                            → 500 Internal Server Error
        請附上 x-request-id 聯絡我們
build → /teachers/%E7%BE%8E%E5%92%B2
```

逐行對照。第一個請求驗證了三件事：「美咲」經 percent-encoding 與 latin-1 往返後被 `Request.path` 正確還原、`<name>` 由 string converter 取出、`getlist()` 取回兩個 `lang`。`/teachers` 缺結尾斜線，得到 308 與 `Location: /teachers/`。int converter 把 `7781` 轉成整數，`abc` 則匹配不到而回 404。PUT 走到 `get_json()`，`{oops` 轉成 400 的 problem details（第 24 章）。DELETE 回 405，`Allow` 裡的 HEAD 是因規則允許 GET 而自動加入（真實的 Flask 還會加上 OPTIONS）。自訂的 lesson converter 接受 `lesson-0815`、拒絕 `0815`。

`/boom` 的例外訊息裡刻意放了假密碼：框架把細節寫進 `wsgi.errors`（部署時就是 gunicorn 的 error log），回應只說「請附上 x-request-id 聯絡我們」，這是 production 錯誤處理的基本要求，也從另一個角度說明 debugger 為什麼不能上線。最後的 `build()` 把 endpoint 轉回 URL。這個迷你版省略了 multipart、cookie、`Host` 驗證、`SCRIPT_NAME`、HEAD 不送 body 等細節，但骨架和 Werkzeug 相同，讀原始碼時你會在 `wrappers`、`routing`、`exceptions` 裡找到每一個概念。

### 實驗三：三個 middleware 與真實的 server

最後是三個正確的 middleware：`TrustedProxy` 依 canon 的規則從右往左解析 `X-Forwarded-For`、跳過 10.20.0.0/16 與 CDN 回源網段 198.51.100.224/27，只有直接對端可信時才採信 `X-Forwarded-Proto`；`RequestId` 沿用上游的 `x-request-id`，格式不對就自己產生；`Timing` 是 41.6 節的正確版。本機上所有請求的對端都是 127.0.0.1，所以把它放進可信清單，代替部署中的 nginx 10.20.3.11。XFF 的五種情境沿用第 25 章：

```python
import http.client
import ipaddress
import json
import re
import secrets
import threading
import time
from wsgiref.simple_server import WSGIRequestHandler, make_server
from wsgiref.validate import validator

LOG, POOL = [], {"in_use": 0}
TRUSTED = [ipaddress.ip_network(n) for n in
           ("10.20.0.0/16", "198.51.100.224/27", "127.0.0.1/32")]  # VPC＋CDN 回源；127.0.0.1 代替 nginx


class TrustedProxy:
    """依 canon 的規則：XFF 從右往左走，跳過可信網段，第一個不可信的位址就是 client。"""
    def __init__(self, app, trusted):
        self.app, self.trusted = app, trusted
    def _is_trusted(self, ip):
        return any(ip in net for net in self.trusted)
    def __call__(self, environ, start_response):
        peer = ipaddress.ip_address(environ["REMOTE_ADDR"])
        hops = [h.strip() for h in environ.get("HTTP_X_FORWARDED_FOR", "").split(",") if h.strip()]
        client = peer
        if self._is_trusted(peer):                       # 只有直接對端可信，XFF 才有意義
            for raw in reversed(hops):
                try:
                    client = ipaddress.ip_address(raw)
                except ValueError:
                    break                                 # 非 IP 的值：停在它右邊那一跳
                if not self._is_trusted(client):
                    break
            if environ.get("HTTP_X_FORWARDED_PROTO") in ("http", "https"):
                environ["wsgi.url_scheme"] = environ["HTTP_X_FORWARDED_PROTO"]
        environ["shengsheng.orig_remote_addr"] = environ["REMOTE_ADDR"]
        environ["REMOTE_ADDR"] = str(client)
        return self.app(environ, start_response)


class RequestId:
    """沿用上游（nginx）給的 x-request-id；格式不對就自己產生，並寫進回應 header。"""
    VALID = re.compile(r"[A-Za-z0-9._-]{1,64}")
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        rid = environ.get("HTTP_X_REQUEST_ID", "")
        if not self.VALID.fullmatch(rid):
            rid = secrets.token_hex(8)                    # 不信任格式怪異的值，避免 log injection
        environ["shengsheng.request_id"] = rid
        def sr(status, headers, exc_info=None):
            headers = [(k, v) for k, v in headers if k.lower() != "x-request-id"]
            headers.append(("x-request-id", rid))
            return start_response(status, headers, exc_info) if exc_info else start_response(status, headers)
        return self.app(environ, sr)


class Timing:
    """量到 close() 為止；不緩衝 body；close() 一定往內傳。"""
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        t0, seen = time.perf_counter(), {}
        def sr(status, headers, exc_info=None):
            seen["status"] = status.split()[0]
            return start_response(status, headers, exc_info) if exc_info else start_response(status, headers)
        return _TimedBody(self.app(environ, sr), environ, seen, t0)


class _TimedBody:
    def __init__(self, inner, environ, seen, t0):
        self.inner, self.environ, self.seen, self.t0, self.size = inner, environ, seen, t0, 0
    def __iter__(self):
        for chunk in self.inner:
            self.size += len(chunk)
            yield chunk                                   # 一塊一塊往外交，不累積
    def close(self):
        try:
            if hasattr(self.inner, "close"):
                self.inner.close()
        finally:
            e, ms = self.environ, (time.perf_counter() - self.t0) * 1000
            LOG.append(f"rid={e['shengsheng.request_id'][:8]} client={e['REMOTE_ADDR']} "
                       f"{e['PATH_INFO']} {self.seen.get('status')} {self.size}B {ms:.0f}ms")


class ExportBody:                                         # 串流匯出：close() 時歸還資料庫連線
    def __init__(self):
        POOL["in_use"] += 1
    def __iter__(self):
        for i in range(3):
            time.sleep(0.02)
            yield f"teacher0{i},{40 + i}\n".encode()
    def close(self):
        POOL["in_use"] -= 1


def inner_app(environ, start_response):
    if environ["PATH_INFO"] == "/export.csv":
        start_response("200 OK", [("Content-Type", "text/csv")])
        return ExportBody()
    body = json.dumps({"client": environ["REMOTE_ADDR"], "scheme": environ["wsgi.url_scheme"],
                       "rid": environ["shengsheng.request_id"]}).encode()
    start_response("200 OK", [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
    return [body]


# 每一層之間都夾一個 validator：哪一層違反 PEP 3333，就在那一層丟出 AssertionError
stack = validator(TrustedProxy(validator(RequestId(validator(Timing(validator(inner_app))))), TRUSTED))


class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


server = make_server("127.0.0.1", 0, stack, handler_class=Quiet)
threading.Thread(target=server.serve_forever, daemon=True).start()


def get(path, **headers):
    conn = http.client.HTTPConnection(*server.server_address, timeout=5)
    conn.request("GET", path, headers={k.replace("_", "-"): v for k, v in headers.items()})
    resp = conn.getresponse()
    body, rid = resp.read(), resp.getheader("x-request-id")
    conn.close()
    return body, rid


scenarios = {
    "經 CDN 進站": "198.51.100.45, 198.51.100.230, 10.20.16.5",
    "直連 API LB": "198.51.100.23, 10.20.16.5",
    "經 CDN＋偽造 XFF": "192.0.2.66, 198.51.100.45, 198.51.100.230, 10.20.16.5",
    "繞過 CDN＋偽造": "192.0.2.66, 198.51.100.230, 198.51.100.99, 10.20.16.5",
    "XFF 塞非 IP": "<script>, 198.51.100.45, 198.51.100.230, 10.20.16.5",
}
got = {}
for label, xff in scenarios.items():
    body, rid = get("/whoami", X_Forwarded_For=xff, X_Forwarded_Proto="https", X_Request_Id="7f3c9a2e")
    got[label] = json.loads(body)
    print(f"client={got[label]['client']:<14} scheme={got[label]['scheme']} rid={rid}  ← {label}")

body, rid = get("/export.csv", X_Request_Id="x" * 100)     # 太長的 id：被換掉
print(f"串流匯出 {len(body)}B，回應的 x-request-id 長度={len(rid)}，連線池佔用={POOL['in_use']}")
time.sleep(0.05)
server.shutdown()
server.server_close()
print(*LOG, sep="\n")

assert [g["client"] for g in got.values()] == ["198.51.100.45", "198.51.100.23", "198.51.100.45",
                                               "198.51.100.99", "198.51.100.45"]
assert POOL["in_use"] == 0 and len(rid) == 16 and len(LOG) == 6

# 對照：直接對端不在可信清單時，XFF 完全不採信
probe = {"REMOTE_ADDR": "198.51.100.99", "HTTP_X_FORWARDED_FOR": "192.0.2.66"}
TrustedProxy(lambda env, sr: [env["REMOTE_ADDR"].encode()], TRUSTED)(probe, None)
print("不可信對端帶 XFF →", probe["REMOTE_ADDR"])
assert probe["REMOTE_ADDR"] == "198.51.100.99"
```

```text
client=198.51.100.45  scheme=https rid=7f3c9a2e  ← 經 CDN 進站
client=198.51.100.23  scheme=https rid=7f3c9a2e  ← 直連 API LB
client=198.51.100.45  scheme=https rid=7f3c9a2e  ← 經 CDN＋偽造 XFF
client=198.51.100.99  scheme=https rid=7f3c9a2e  ← 繞過 CDN＋偽造
client=198.51.100.45  scheme=https rid=7f3c9a2e  ← XFF 塞非 IP
串流匯出 39B，回應的 x-request-id 長度=16，連線池佔用=0
rid=7f3c9a2e client=198.51.100.45 /whoami 200 65B 0ms
rid=7f3c9a2e client=198.51.100.23 /whoami 200 65B 0ms
rid=7f3c9a2e client=198.51.100.45 /whoami 200 65B 0ms
rid=7f3c9a2e client=198.51.100.99 /whoami 200 65B 0ms
rid=7f3c9a2e client=198.51.100.45 /whoami 200 65B 0ms
rid=192e3cc8 client=127.0.0.1 /export.csv 200 39B 68ms
不可信對端帶 XFF → 198.51.100.99
```

前五行逐一驗證第 25 章的情境。經 CDN 進站時，從右往左的 10.20.16.5（LB）與 198.51.100.230（CDN 出口）都可信，第一個不可信的 198.51.100.45 就是學生；直連 LB 的短鏈同樣取到 198.51.100.23，不會像固定跳數那樣退回 proxy 位址。自帶偽造值的請求在 .45 就停了，偽造的 192.0.2.66 根本沒被看到；繞過 CDN 的攻擊者偽造了 CDN 出口，但 LB 附加的是它真正看到的對端 198.51.100.99，這段改不了，演算法停在這裡；`<script>` 也沒被讀到。`scheme` 都是 https，因為直接對端可信。

第六行的串流匯出帶了 100 個字元的 `X-Request-Id`，被換成自己產生的 16 個十六進位字元；連線池佔用為 0，證明 `close()` 穿過三層 middleware 與四個 validator 抵達了 `ExportBody`。接著六行是 Timing 的 log：前五行沿用 client 的 `7f3c9a2e`，最後一行的 id 與所有毫秒數每次執行都不同（匯出每批 sleep 20 毫秒，約 60 多毫秒）；匯出的 client 是 127.0.0.1，因為沒帶 XFF，就像 nginx 本機發出的 health check。最後一行是對照組：直接對端不可信時 XFF 完全不被採信。判斷「是不是自己的 proxy」只能看 TCP 對端，也就是 `REMOTE_ADDR`。四個 validator 全程沒有丟出 `AssertionError`，代表每一層都守住了 PEP 3333。

## 41.17 在工作上怎麼用

事故檢討之後，阿德請小晴把本章的內容整理成團隊的 WSGI 檢查清單，依角色分成四份。

**後端工程師：寫 view 與 middleware 時。** 寫 middleware 前先問三個問題：會不會讀完整個 body？`close()` 有沒有往內傳？`exc_info` 有沒有原樣傳遞？再用 `wsgiref.validate` 或 `LintMiddleware` 包住每一層測一次。串流的清理用 `call_on_close()`，generator 裡要讀 `request` 就用 `stream_with_context()`；需要原始 body 時先呼叫 `request.get_data()`；連結一律用 `url_for`。

**SRE：確認 production 沒有開發用元件。** 下面這組檢查可以放進部署前的自動檢查或定期巡檢（示意）：

```bash
# 1. production 與 staging 不能有開發伺服器或 debugger
curl -sI http://10.20.3.21:8000/readyz | grep -i '^server:'     # 不應出現 Werkzeug
env | grep -E '^(FLASK_DEBUG|WERKZEUG_DEBUG_PIN)='                # 不應有輸出
ps -eo args | grep -E 'flask run|run_simple' | grep -v grep       # 不應有輸出
ss -ltnp | grep -E ':5000\b'                                      # 開發 port 不應在聽

# 2. 用 x-request-id 串起每一層的 log
grep 'rid=7f3c9a2e' /var/log/shengsheng/app.log
grep '7f3c9a2e' /var/log/nginx/access.log
```

第一組從 `Server` header、環境變數、process 清單、listening port 四個方向確認沒有開發伺服器；從外面看到的 `Server` 是 nginx，要從內網直打 app 主機才看得到這一層。第二組用 request id 串接各層 log（第 3、20、24 章），前提是 RequestId 沿用 nginx 產生的 id，而不是各自產生。

**資安工程師：審查設定與掃描。** Rita 在 code review 時固定檢查：`app.run(debug=True)` 只出現在 `if __name__ == "__main__":` 底下且不會被部署；`ProxyFix` 的 `x_for` 等參數和實際的 proxy 層數一致，`x_host`、`x_proto` 只在前面的 proxy 會覆寫這些 header 時才開；`MAX_CONTENT_LENGTH` 有設定；錯誤處理器不會把例外訊息放進回應。內部掃描則比對兩個特徵：`Server: Werkzeug` header 與 debugger 的錯誤頁面，任何一個出現在非開發網段都要開單處理。

**判斷流程：回應怪怪的，該查哪一層？**

```text
 症狀出現在回應上
   │
   ├─ 第一個 byte 很晚才到，但總時間正常或更長
   │     └─► 有 middleware 或 proxy 在緩衝：curl 直打 gunicorn 比對；查 b"".join、proxy_buffering
   │
   ├─ 串流回應被截斷，狀態碼卻是 200
   │     └─► header 送出後才出錯（41.5 節）：看 gunicorn error log 的例外與 x-request-id
   │
   ├─ 資源（資料庫連線、檔案）慢慢耗盡，重啟就好
   │     └─► close() 沒傳到最內層：用 validator 或 LintMiddleware 包住每一層測試
   │
   ├─ client IP、scheme、產生的連結不對
   │     └─► ProxyFix／信任規則：印出 environ 的 REMOTE_ADDR、wsgi.url_scheme 與原始 XFF
   │
   └─ 非 ASCII 的路徑、檔名、header 出錯
         └─► bytes 與 native string（41.7 節）：PATH_INFO 要 latin-1 往返；header 值要編碼
```

每一支都指回本章的一節。第一刀看「時間的形狀」：TTFB 晚而總時間正常，幾乎一定是某層在緩衝；資源慢慢耗盡、重啟就好，則多半是 `close()` 鏈斷了。

## 41.18 常見錯誤與除錯

下表收錄 WSGI、Werkzeug 與 Flask 這一層最常見的錯誤，每一列都可以用本章的工具在幾分鐘內確認。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| middleware 記錄的耗時永遠只有幾毫秒 | 在 app 回傳時就停錶，body 還沒產生 | 對照 nginx 的 `$upstream_response_time` | 包裝 iterable，在 `close()` 時停錶 |
| 加了 middleware 之後，大回應的 TTFB 暴增、記憶體上升、nginx 回 504 | middleware 把 body 讀完（`b"".join`）才回傳 | curl 直打 gunicorn 看第一個 byte 的時間；看 worker RSS | 逐段轉交，需要累積時先 `yield b""`；大小在 `__iter__` 裡累加 |
| 資料庫連線池慢慢被吸乾，重啟就恢復 | 某層 middleware 沒把 `close()` 往內傳，`call_on_close`／清理沒執行 | 用 `wsgiref.validate` 或 `LintMiddleware` 包住每一層；計數 acquire 與 release | middleware 回傳自己的 iterable 時，在 `close()` 呼叫內層的 `close()` |
| 串流 generator 裡出現「Working outside of request context」 | `wsgi_app` 回傳時 context 已經 pop，generator 之後才執行 | 例外的 traceback 指向 generator 內部 | 用 `stream_with_context()`；或在 view 裡先把需要的值取出來 |
| `request.remote_addr` 全部是 10.20.3.11 | 在 proxy 後面，`REMOTE_ADDR` 是 nginx | 印出 environ 的 `REMOTE_ADDR` 與 `HTTP_X_FORWARDED_FOR` | 依 canon 的信任規則解析 XFF，或正確設定 ProxyFix（第 43 章） |
| `url_for(_external=True)` 產生 `http` 開頭的連結、HTTPS redirect 迴圈 | TLS 在 LB 終結，`wsgi.url_scheme` 是 http | 看 environ 的 `wsgi.url_scheme` 與 `HTTP_X_FORWARDED_PROTO` | 只信任自家 proxy 寫的 `X-Forwarded-Proto`（ProxyFix 的 `x_proto`） |
| 非 ASCII 路徑變亂碼，或 404 | 直接使用 `PATH_INFO`，沒做 latin-1 → UTF-8 的往返 | 印出 `repr(environ["PATH_INFO"])` | 用 Werkzeug 的 `request.path`，或自己 `.encode("latin-1").decode("utf-8")` |
| 下載中文檔名時 client 收到殘缺回應 | header 值含非 latin-1 字元，送到一半編碼失敗 | server log 有 `UnicodeEncodeError`；回應沒有完整的 header | 用 `filename*=UTF-8''…`（RFC 8187），Werkzeug 的 `send_file` 會處理 |
| webhook 簽章驗證偶爾失敗 | 先讀了 `request.form` 或 `get_json()`，原始 body 已被消耗或重新序列化 | 比對收到的原始 bytes 與簽章計算用的 bytes | 驗證時一律用 `request.get_data()` 的原始 bytes（第 30 章） |
| 模組頂層的背景 thread 或排程跑了兩份 | reloader 讓模組在 parent 與 child process 各執行一次 | 看 process 清單與 `WERKZEUG_RUN_MAIN` | 不在模組頂層做初始化；開發時檢查 `WERKZEUG_RUN_MAIN` |
| 內網掃描發現 `Server: Werkzeug`、debugger 頁面 | 用 `flask run --debug --host 0.0.0.0` 對外服務 | curl 該 port 看 header 與錯誤頁面 | 立即關閉並封鎖 port、輪替主機上的祕密、改用 gunicorn、部署檢查禁止 debug |

除錯這一層的通則是**印出 environ**。WSGI 的所有輸入都在 environ 裡，`REMOTE_ADDR`、`wsgi.url_scheme`、`PATH_INFO`、`HTTP_*` 一印出來，八成的問題就有了方向；剩下的兩成在 iterable 的生命週期裡，用 validator 包住每一層，看是哪一層違反了規格。

## 41.19 動手練習

1. **延伸實驗三：加上 gzip middleware**（延伸本章程式）。在實驗三的洋蔥裡加一個 `Gzip` middleware，當 client 送 `Accept-Encoding: gzip` 且回應是 `text/*` 或 JSON 時，用 `zlib.compressobj(wbits=31)` 逐段壓縮。要求：不緩衝整個 body、移除或修正 `Content-Length`、加上 `Content-Encoding: gzip` 與 `Vary: Accept-Encoding`、`close()` 往內傳，並且通過所有 validator。
   答案要點：在 `start_response` 包裝裡改 header；`__iter__` 對每段 `compress()`，結果為空時 `yield b""`，結束時 `yield flush()`。用 `gzip.decompress()` 驗證內容並確認連線池佔用為 0；放在 Timing 內側或外側，決定 Timing 記錄的是壓縮後還是壓縮前的大小。

2. **用 curl 觀察串流與緩衝**（真實工具）。把實驗三的 `ExportBody` 改成每批 sleep 0.3 秒、共 10 批，server 改成固定 port（例如 8765），用 `curl -N -s -w '%{time_starttransfer} %{time_total}\n' -o /dev/null 127.0.0.1:8765/export.csv` 量 TTFB 與總時間；再把 41.6 節的 `TimingV2` 套上去量一次。
   答案要點：正確版的 `time_starttransfer` 約 0.3 秒、`time_total` 約 3 秒；`TimingV2` 兩者都約 3 秒。`-N` 關閉 curl 自己的輸出緩衝。如果在前面加上 nginx 而 TTFB 又變長，就是 `proxy_buffering` 的效果。

3. **讀 Werkzeug 的原始碼**（真實工具）。在一個虛擬環境安裝 Werkzeug，找到 `werkzeug/wsgi.py` 裡的 `ClosingIterator` 與 `werkzeug/wrappers/response.py` 裡的 `call_on_close`、`__call__`，對照本章實驗二的 `_ClosingIterator` 與 `Response.__call__`，列出真實版本多處理了哪些情況。
   答案要點：真實的 `ClosingIterator` 會先呼叫原 iterable 的 `close()`，再呼叫登記的 callbacks；`Response.__call__` 透過 `get_wsgi_response()` 依 environ 處理 HEAD 請求（不送 body）與不帶 body 的狀態碼，並在能確定長度時補上 `Content-Length`。

4. **掛載點實驗**（延伸本章程式）。寫一個迷你版 `DispatcherMiddleware`：依前綴把 `/ops` 開頭的請求轉給第二個 app，並把前綴從 `PATH_INFO` 移到 `SCRIPT_NAME`；在第二個 app 裡用 41.4 節的 URL 重建演算法產生自己的絕對網址，確認結果帶有 `/ops` 前綴。
   答案要點：`/ops/users/42` 進來時，內層看到 `SCRIPT_NAME='/ops'`、`PATH_INFO='/users/42'`；`/ops` 本身要對應到 `PATH_INFO=''` 或 `/`，`/opsx` 不能被誤判為 `/ops` 的子路徑，所以要比對完整的路徑段落，而不是單純的字串前綴。

5. **在自己的電腦上安全地觀察 debugger**（真實工具）。在虛擬環境安裝 Flask，寫一個會丟例外的 view，用 `flask --app demo run --debug`（預設只聽 127.0.0.1）啟動，觸發例外，觀察終端機印出的 PIN、瀏覽器的 traceback 頁面與回應的 `Server` header；再用 `curl -sI` 確認 header 內容。做完立刻關閉。
   答案要點：`Server` header 是 `Werkzeug/3.1.x Python/3.x`；每個 frame 都有 console 圖示，使用前要求 PIN。記住它的長相，日後在掃描報告或截圖裡才能立刻認出；不要對任何不屬於自己的服務做這件事。

## 本章重點整理

- WSGI 解決的是框架與 server 之間的 N×M 問題：PEP 333（2003）定義、PEP 3333（2010）補上 Python 3 的 bytes 與字串規則，二十年來沒有改過介面。
- WSGI app 是 `app(environ, start_response)` 這樣的 callable，回傳 bytes 的 iterable；server 要等到第一個非空 chunk 才送出 header，讓 app 在送出前還能改變主意。
- environ 沿用 CGI 的變數名稱：header 轉成 `HTTP_*`（`Content-Type`、`Content-Length` 例外），`PATH_INFO` 已經 percent-decode，`SCRIPT_NAME` 表示掛載點；header 名稱的轉換是多對一，`-` 與 `_` 會撞名。
- `wsgi.input` 只能讀一次，也只能讀 `CONTENT_LENGTH` 那麼多；需要原始 body 的驗證（webhook 簽章）要先用 `request.get_data()` 取得並快取。
- `start_response` 只能呼叫一次，例外是帶 `exc_info` 的錯誤回應：header 還沒送出就能取代，已經送出就只能中斷連線，串流回應中途出錯時 client 會拿到被截斷的 200。
- app 不得設定 hop-by-hop header；想串流就不給 `Content-Length`，由 server 決定用 chunked 或關閉連線劃定邊界。
- iterable 有 `close()` 時 server 必須呼叫，不論成功、出錯或 client 斷線；Werkzeug 的 `call_on_close` 建立在這條規則上，串流回應的資源清理要放在這裡，而不是 Flask 的 `teardown_request`。
- environ、狀態與 header 一律是以 latin-1 表示的 native string，body 一律是 bytes；非 ASCII 的路徑要做 latin-1 → UTF-8 的往返，非 ASCII 的檔名要用 RFC 8187 的編碼。
- middleware 對外是 app、對內是 server，依洋蔥模型組合；正確的 middleware 不緩衝 body、把 `close()` 往內傳、原樣傳遞 `exc_info`，順序取決於「誰需要看到誰改過的東西」。
- Werkzeug 是 WSGI 工具箱：延遲解析的 Request、本身就是 WSGI app 的 Response 與 HTTPException、MultiDict 與 Headers、Map／Rule／converter 的 routing、開發伺服器、debugger 與 test client。
- Werkzeug 的 routing 依規則組成排序而非定義順序，method 不符回 405 並帶 `Allow`，結尾斜線不符時以 308 redirect；converter 是輸入驗證的第一道防線，但不是授權檢查。
- interactive debugger 等於讓網頁使用者執行任意 Python 程式，PIN 只是最後一道防線；debugger 與開發伺服器只能在開發者自己的電腦上、只聽 127.0.0.1。
- ProxyFix 是固定跳數的信任實作，只在路徑層數固定時正確；聲聲 Live 依 canon 從右往左解析 XFF 並跳過可信網段，且只有直接對端可信時才採信任何 `X-Forwarded-*`。
- Flask 的 app 物件就是 WSGI callable，`wsgi_app` 建立 request context、用 Werkzeug 比對 URL、執行 view，最後回傳 `response(environ, start_response)`；context 在 body 送出之前就已經 pop。

## 延伸問答

> [!question]- Q1. 為什麼 WSGI 要求 server 延遲送出 header，等到第一個非空 chunk 才送？直接在 start_response 時送出不是比較簡單嗎？
> 延遲送出讓 app 保有「反悔」的能力。只要還沒有任何 byte 寫進 socket，app 就可以在產生 body 的過程中發現錯誤，帶著 `exc_info` 再呼叫一次 `start_response`，把 200 改成 500；如果 server 在第一次呼叫時就送出狀態列，這個能力就消失了，所有在 body 產生前才發現的錯誤都只能變成截斷的 200。41.5 節的實驗裡，`after-start` 情況能乾淨地回 500，正是因為 header 還沒送。
>
> 第二個理由是效率與正確性：延遲讓 server 有機會在看到 body 之後才決定 `Content-Length`（例如 iterable 只有一個元素時自動補上），也避免「送了 header 卻沒有 body」的小封包。代價是 middleware 若緩衝 body，header 也會一起被延遲，這就是 TTFB 暴增的根源；所以規格同時要求 middleware 不得阻擋迭代，兩條規則要一起理解。

> [!question]- Q2. 面試題：請解釋 WSGI middleware 的洋蔥模型，並說明為什麼 ProxyFix 通常放在最外層。
> middleware 對外層表現為一個 WSGI app，對內層表現為一個 server，因此可以層層包裹。請求從最外層往內傳，每一層可以讀取或修改 environ；回應則由內往外，內層呼叫 `start_response` 時會經過每一層的包裝函式，body 的每一段也經過每一層的 iterable，最後 server 呼叫最外層的 `close()`，再一路往內傳。每一層都包住內層，請求剝進去、回應包出來，所以叫洋蔥模型。
>
> ProxyFix 改寫的是 `REMOTE_ADDR`、`wsgi.url_scheme`、`HTTP_HOST` 這些「請求從哪裡來」的資訊，而 request id、access log、限速、產生絕對 URL 的邏輯全都依賴這些值。放在最外層，內層每一個元件看到的都是改寫後的正確值；如果放在 Timing 或 log middleware 的內側，那些 middleware 記錄的就永遠是 nginx 的位址。判斷順序的通則是：一層需要看到的資訊被哪些層改寫，那些層就要在它外面。

> [!question]- Q3. 你在 production 看到：資料庫連線池每天下午慢慢被佔滿，重啟 gunicorn 就恢復，而上週剛加了一個新的 WSGI middleware。你會怎麼查？
> 「慢慢耗盡、重啟就好」是資源洩漏的典型形狀，而在 WSGI 這一層，最常見的洩漏是 `close()` 鏈斷掉：新的 middleware 回傳了自己的 iterable（例如一個 generator），卻沒有在自己的 `close()` 裡呼叫內層的 `close()`，於是 Werkzeug `call_on_close` 登記的清理、或框架在 close 時歸還資源的邏輯沒有執行。先看這個 middleware 的程式碼：它是不是 `for chunk in result: yield chunk`？有沒有 `finally: result.close()`？
>
> 接著用工具確認。在測試環境用 `wsgiref.validate` 或 Werkzeug 的 `LintMiddleware` 包住每一層，跑一個串流回應的請求，看有沒有「Iterator garbage collected without being closed」；同時在連線池的 acquire 與 release 加上計數，對照每個請求是否成對。修正方法是把 middleware 改寫成一個有 `__iter__` 與 `close()` 的類別，`close()` 裡先呼叫內層的 `close()`。最後補上回歸測試，模擬 client 中途斷線的情況，因為那條路徑最容易被漏掉。

> [!question]- Q4. 手算：PATH_INFO 是 `'/teachers/ç¾\x8eå\x92²'`，這個字串的 len 是多少？正確的老師名字是什麼？為什麼 PEP 3333 要用這種看起來是亂碼的表示法？
> 這個字串是「/teachers/」加上 6 個字元，每個字元代表一個 byte：0xE7、0xBE、0x8E、0xE5、0x92、0xB2，所以長度是 10＋6＝16。把它 `.encode("latin-1")` 得到這 6 個 bytes，再以 UTF-8 解碼：E7 BE 8E 是「美」，E5 92 B2 是「咲」，答案是「美咲」，對應 41.4 節實驗中 client 送出的 `%E7%BE%8E%E5%92%B2`。
>
> PEP 3333 選擇 latin-1，是因為它是唯一能把任意 0–255 的 byte 一對一對應到字元、而且一定成功又完全可逆的編碼。HTTP 不保證路徑與 header 用的是 UTF-8，server 如果擅自用 UTF-8 解碼，遇到非法序列就只能報錯或用替換字元破壞資料；用 latin-1，原始 bytes 一個不少地保存在 `str` 裡，該用什麼編碼解讀，留給更了解內容的框架決定。Werkzeug 的 `request.path` 就是在框架這一層做 UTF-8 解碼。

> [!question]- Q5. 看 log 找原因：老師回報下載的月報 CSV 最後幾百列不見了，瀏覽器顯示下載完成，nginx access log 記錄狀態 200。可能是什麼？
> 狀態 200 加上內容被截斷，是「header 送出之後才出錯」的典型結果。串流回應在第一批資料送出時就已經把 200 寫進 socket，之後 generator 若因資料庫游標逾時、查詢錯誤或 worker 被殺而中斷，server 無法再改狀態碼，只能中斷連線；41.5 節的 `mid-stream` 實驗就是這個情況。nginx 的 access log 記的是它送給 client 的狀態碼，也就是 200。先拿這個請求的 `x-request-id` 去 gunicorn 的 error log 找例外，再看 nginx 的 error log 有沒有 `upstream prematurely closed connection`。
>
> 瀏覽器為什麼會以為下載完成？如果 body 是用「關閉連線」劃定結尾（nginx 對上游用 HTTP/1.0，或 client 端連線沒有 `Content-Length`），截斷和正常結束在線路上無法分辨；用 chunked 時，client 可以從沒收到最後的 0 長度 chunk 判斷不完整，但不是每個下載工具都會報錯。改善方向有三個：把會失敗的步驟（權限、查詢計畫）移到送出第一個 byte 之前；在 CSV 末尾加上總列數或結束標記讓 client 驗證；對大型報表改成非同步產生檔案、完成後再提供下載連結。

> [!question]- Q6. 設計取捨：Werkzeug 的 ProxyFix 用「固定信任右邊 N 跳」，聲聲 Live 卻改用「從右往左跳過可信網段」。兩者的取捨是什麼？
> 固定跳數的優點是簡單、不需要維護網段清單，在「每個請求都經過完全相同的 proxy 層數」時完全正確，例如 app 只能透過一台 nginx 存取。它的弱點是路徑一旦不一致就會取錯：聲聲 Live 有的請求經過 CDN、有的直連 LB，鏈的長度不同，`x_for=2` 在短鏈上會取到 proxy 自己的位址，在攻擊者繞過 CDN 時則可能取到攻擊者偽造的值，41.16 節的對照實驗與第 25 章都示範過。
>
> 網段式的做法對路徑長度不敏感，只要清單正確，任何路徑都能停在第一個不可信的位址；代價是要維護清單（CDN 的回源網段會變動），清單過寬就等於信任了不該信任的來源。實務上兩者常常搭配：在最靠近 internet 的自家 proxy（或 nginx 的 realip 模組）用網段規則把 client 位址解析好、覆寫 header，後面固定的內部層數再用 ProxyFix 這類固定跳數設定。不論哪種，都要先確認 origin 只接受來自 CDN 與內網的連線，信任的假設才成立。

> [!question]- Q7. 為什麼 Flask 的串流 generator 裡讀 request 會出錯？stream_with_context 做了什麼？代價是什麼？
> Flask 的 `wsgi_app` 在 `finally` 裡呼叫 `ctx.pop()`，而 `wsgi_app` 在回傳 `response(environ, start_response)` 的結果時就結束了，這時串流 generator 一行都還沒執行；generator 要等 gunicorn 開始迭代才被推動，那時 request context 已經彈出，`request` 這個 context-local proxy 找不到對應的物件，就丟出「Working outside of request context」。這是 WSGI 「回傳不等於完成」這條規則在框架層的直接後果。
>
> `stream_with_context()` 把 generator 包起來，在 generator 開始執行時重新推入同一個 request context，並在 generator 結束或被 close 時才彈出，所以 generator 內可以使用 `request`、`g` 與 `session`。代價是 context 以及它參照的資源（例如 `g` 上的資料庫連線）會一直活到串流結束，長時間的串流會延長資源佔用；而且 `teardown_request` 的執行時機也因此改變。更乾淨的做法常常是在 view 裡先把需要的值取出、傳給 generator，資源清理則交給 `call_on_close`。

> [!question]- Q8. 同事說：「debugger 有 PIN 保護，而且 staging 只有內部 VPN 連得到，開著方便除錯沒關係。」你會怎麼回應？
> PIN 是避免「誤觸」的最後一道防線，不是安全邊界。debugger 的 console 等於在伺服器上執行任意 Python 程式，能讀取環境變數裡的資料庫密碼、雲端金鑰與任何檔案；PIN 的熵有限，它的推導材料來自機器本身，若主機另有讀檔漏洞就可能外洩，它也會印在 log 裡，看得到 log 的人就有 PIN。「只有內部 VPN 連得到」則把信任放在網路位置上：任何一台被入侵的員工電腦、任何能讓瀏覽器對內網發請求的網頁（新版 Werkzeug 用 Host 檢查擋 DNS rebinding，但這也只是另一道防線），都能碰到它。staging 的祕密也常常和 production 有重疊或相似的權限。
>
> 而且「方便除錯」有更安全的替代方案：在本機重現問題後用 debugger；staging 用 gunicorn 跑，錯誤送到 log 與錯誤追蹤服務，用 `x-request-id` 串起每一層；真的需要互動式除錯時，用 SSH 轉發只綁 127.0.0.1 的 port，並在結束後關閉。故事裡 Rita 的處理順序也說明了代價：一旦發現 debugger 曾經暴露，就要假設主機上的祕密已外洩並全部輪替，這比當初多花幾分鐘設定 log 昂貴得多。

## 延伸閱讀

- PEP 3333〈Python Web Server Gateway Interface v1.0.1〉：WSGI 的現行規格，含 environ、`start_response`、iterable 與 bytes／字串規則的完整條文
- PEP 333〈Python Web Server Gateway Interface v1.0〉：原始版本，Rationale 一節說明了 WSGI 的設計動機
- RFC 3875〈The Common Gateway Interface (CGI) Version 1.1〉：environ 變數名稱的來源
- Python 官方文件〈wsgiref — WSGI Utilities and Reference Implementation〉：`simple_server`、`validate`、`handlers`、`util`
- Werkzeug 官方文件：Request／Response Objects、URL Routing、Serving WSGI Applications、Debugging Applications、Tell Werkzeug it is Behind a Proxy、Test Utilities
- Flask 官方文件：Application Structure and Lifecycle、The Request Context、Streaming Contents、Deploying to Production
- RFC 6266〈Use of the Content-Disposition Header Field in HTTP〉與 RFC 8187〈Indicating Character Encoding and Language for HTTP Header Field Parameters〉：非 ASCII 檔名的編碼方式
