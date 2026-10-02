---
chapter: 40
title: 從 Socket 寫一個 HTTP Server
part: 9
---

# 第 40 章　從 Socket 寫一個 HTTP Server

> [!abstract] 本章地圖
> **核心問題**：一個 HTTP server 拿到 listening socket 之後，到底要做哪些事，才能同時服務成千上萬條連線，又不被一個慢吞吞的 client 拖垮？
>
> **你會學到**：
> - 用 socket 從零寫出支援 keep-alive、request 大小上限與 header／body 期限的 HTTP/1.1 server，並說清楚每一道限制擋的是什麼
> - 依序實作 iterative、thread-per-connection、thread pool、pre-fork、selectors（epoll／kqueue）與 asyncio 六種並行模型，說出各自把「等待」放在哪裡
> - 在非阻塞 socket 上正確處理 partial read、partial write 與 backpressure
> - 解釋 C10K 問題、fd 上限、`EMFILE`，以及 backlog 與第 10 章 accept queue 的關係
> - 用同一組並行 client 量測各版本，從 p50 與 p99 讀出模型的差異，並對應到 gunicorn、uvicorn 與 nginx 的設計
>
> **前置知識**：第 9 章（socket API、blocking 與 timeout）、第 10 章（accept queue、backlog、CLOSE_WAIT、RST）、第 11 章（byte stream 與 framing、Nagle）、第 20 章（HTTP/1.1 訊息格式、Content-Length、keep-alive、request smuggling）

## 40.1 故事：彩排夜的在線名單

聲聲 Live 想在教室畫面右上角顯示「目前在線的學生」，老師一眼就知道誰掉線了。這個功能交給小晴：學生的瀏覽器每 15 秒送一次 `POST /presence` 心跳，內容是學生 ID（例如 `student-0457`），服務把名單存在記憶體裡，老師端用 `GET /presence` 查詢。服務叫 `presence`，暫時放在 VPC 裡的一台主機 10.20.3.41:8090。小晴覺得這只是幾十行的小事，用標準函式庫的 `http.server.HTTPServer` 寫完，還記得第 20 章的提醒，把 handler 的 `protocol_version` 設成 `HTTP/1.1` 以支援 keep-alive，本機測試一切正常。

週五晚上八點是上線前的彩排：合成監測主機 10.20.3.30 模擬兩千名學生，每人一條 keep-alive 連線，每 15 秒送一次心跳。開始不到一分鐘，壓測報表上的心跳 p50 只有 2 毫秒，p99 卻是 30 秒的逾時上限，大部分模擬學生被標成「離線」。阿德登進主機打了 `ss -ltn 'sport = :8090'`，看到 listening socket 的 `Recv-Q 6`、`Send-Q 5`。阿德說：「`HTTPServer` 一次只服務一條連線，而且 backlog 只有 5。第一個學生的 keep-alive 連線還開著，其他人全在第 10 章的 accept queue 裡排隊，排不進去的 SYN 被丟掉。」

小晴改成 `ThreadingHTTPServer`，第二次彩排果然順利：兩千條連線、兩千條 thread，p99 降到 10 毫秒。接著輪到資安工程師 Rita 的測試：另外開三千條連線，每條每 10 秒才送出 header 的一個 byte。五分鐘後 presence 的 log 開始噴 `OSError: [Errno 24] Too many open files`，thread 數衝到四千多條，記憶體一路往上，連正常學生的心跳也被拒絕。小晴不解：這些慢速連線什麼都沒做，為什麼能拖垮整個服務？

```text
 監測主機 10.20.3.30                                  presence 10.20.3.41:8090
 ┌──────────────────────┐                           ┌──────────────────────────────────────┐
 │ 2,000 個模擬學生     │── keep-alive，每 15 秒 ──►│ 第一版 HTTPServer（iterative）        │
 │ （每人一條連線）     │                           │  ① 一次服務一條連線                   │
 └──────────────────────┘                           │  ② backlog = 5：accept queue 很快滿   │
 ┌──────────────────────┐                           ├──────────────────────────────────────┤
 │ Rita 的 3,000 條     │── 每 10 秒 1 byte ───────►│ 第二版 ThreadingHTTPServer            │
 │ 慢速連線             │                           │  ③ 每條連線一條 thread：四千多條     │
 └──────────────────────┘                           │  ④ header 沒有期限：慢速連線永不釋放  │
                                                    │  ⑤ fd 上限 4,096 → accept() EMFILE    │
                                                    └──────────────────────────────────────┘
```

這張圖是阿德在檢討會上畫的，五個編號對應五個問題。① 和 ② 是第一版的問題：iterative server 處理完一條連線才 `accept()` 下一條，而 keep-alive 讓「處理完」遙遙無期；`socketserver` 預設的 `request_queue_size` 是 5（第 10 章的 backlog 表），accept queue 幾乎一開始就滿。③、④、⑤ 是第二版的問題：每條連線一條 thread，連線數就是 thread 數；`http.server` 的 handler 預設沒有讀取逾時，一條每 10 秒送 1 byte 的連線可以永遠佔住一條 thread 和一個 fd；fd 用完之後，連正常的新連線都無法 `accept()`。

阿德沒有直接叫小晴換成 gunicorn 或 uvicorn，反而出了一個作業：「從 socket 開始，把 HTTP server 自己寫五遍：iterative、thread、thread pool、selectors、asyncio。每一版都要支援 keep-alive、request 大小上限、header 和 body 的期限，最後用同一組 client 量一次。寫完你就知道 gunicorn 的 worker 類型、uvicorn 的 event loop、nginx 的 `client_header_timeout` 各自在解決什麼。」本章就是這份作業。

## 40.2 一個 HTTP server 的工作：從 accept 到 keep-alive

第 20 章從 client 的角度看 HTTP/1.1：送出請求、依 Content-Length 或 chunked 切出回應的邊界。server 的工作是鏡像：從 byte stream 切出**請求**的邊界，呼叫應用程式，再寫出一個邊界明確的回應。差別在於 server 面對的是**很多個彼此不認識、也不一定守規矩的 client**，所以除了「解析正確」，還要回答兩個問題：同時有很多條連線時，誰先被服務？client 不送資料、送得很慢、或送得太多時，server 什麼時候放棄？

把一條連線在 server 端的一生畫成狀態機，兩個問題的答案都在上面：

```text
          accept()
             │  開始計算 header 期限
             ▼
      ┌──────────────┐  超過 header 上限 ─────────────► 回 431，關閉
      │ 讀 header     │  期限到了還沒看到空行 ──────────► 回 408，關閉
      └──────────────┘  格式錯誤 ───────────────────────► 回 400，關閉
             │ 看到 \r\n\r\n，解析請求行與 header
             │ Content-Length 超過上限 ─────────────────► 回 413，關閉
             ▼
      ┌──────────────┐
      │ 讀 body       │  期限到了還沒收齊 ───────────────► 回 408，關閉
      └──────────────┘
             │ 收齊 N bytes
             ▼
      ┌──────────────┐
      │ 呼叫應用程式  │
      └──────────────┘
             ▼
      ┌──────────────┐
      │ 寫回應        │  對方太久不讀（送不出去）────────► 關閉
      └──────────────┘
             │ 送完；請求是 Connection: close？ ─── 是 ──► 關閉
             ▼ 否
      ┌──────────────┐
      │ 閒置          │  閒置太久 ──────────────────────► 關閉（不回應）
      │（keep-alive） │  對方關閉（recv 得到 b""）─────► 關閉
      └──────────────┘
             │ 下一個請求的第一個 byte 到了
             └──────────► 回到「讀 header」
```

從上往下讀。每個方框都是一段「等待」：等 header、等 body、等應用程式、等對方把回應讀走、等下一個請求。每一段等待都有一條往右的出口，也就是**期限**（deadline）：沒有期限的等待，就是讓 client 決定 server 的資源什麼時候釋放。第二個重點在最下面：keep-alive 讓連線在送完回應之後回到「閒置」，而不是關閉，所以一條連線的壽命遠比一個請求長。故事裡的第一版就是忘了這件事：iterative server 在閒置狀態等下一個請求時，其他連線只能在外面排隊。

右邊每一條出口都對應一個 status code，也對應業界 server 的一個設定。下表把本章 server 的限制和 nginx、gunicorn 的對應設定放在一起，數字是各自的預設值：

| 限制 | 本章 server | nginx | gunicorn | 超過時 |
|---|---|---|---|---|
| header 大小 | 8 KB | `large_client_header_buffers 4 8k` | `--limit-request-line 4094`、`--limit-request-field_size 8190`、`--limit-request-fields 100` | 431（或 400） |
| body 大小 | 64 KB | `client_max_body_size 1m` | 不限制，交給應用程式 | 413 |
| header 期限 | 0.5 秒（教學用） | `client_header_timeout 60s` | 沒有獨立設定；worker 卡太久會被 arbiter 依 `--timeout`（預設 30 秒）終止 | 408 |
| body 期限 | 0.5 秒（教學用） | `client_body_timeout 60s`（兩次讀取之間） | 同上 | 408 |
| 寫回應 | 2 秒沒進度就放棄 | `send_timeout 60s`（兩次寫入之間） | 同上 | 關閉 |
| keep-alive 閒置 | 0.5 秒（教學用） | `keepalive_timeout 75s` | `--keep-alive 2` | 關閉，不回應 |
| 每條連線的請求數 | 不限 | `keepalive_requests 1000` | `--max-requests` 是 worker 層級的另一回事 | 回應帶 `Connection: close` |

表裡有兩個細節。第一，nginx 的 `client_body_timeout` 與 `send_timeout` 量的是「兩次讀寫之間」的間隔，不是總時間；`client_header_timeout` 則是整個 header 的時間。間隔型的逾時容易被「每次只送一點點」的 client 繞過，總期限型則不會，40.3 節會用程式證明。第二，gunicorn 沒有獨立的 header 期限，它的 sync worker 本來就假設前面有 nginx 這類 proxy 先把慢速 client 擋掉、把請求完整收好再轉過來，這是 40.11 節部署建議的根據。status code 的語意在第 20 章已經講過，這裡要記住的是 431 是 header 太大、413 是 body 太大，而 408 代表「你太慢了，我不等了」。

還有一條規則表上沒有，但每一版都要遵守：**錯誤回應要真的送得到 client**。第 10 章實驗三說過，server 如果在接收 buffer 還有沒讀的資料時 `close()`，核心會送 RST，client 可能連 413 都讀不到就看到 `ECONNRESET`。所以本章的 server 回錯誤時，先 `shutdown(SHUT_WR)` 送出 FIN，再花一點時間把殘留的資料讀掉，最後才 close，這個做法叫 **lingering close**。

## 40.3 第一版：iterative server 與四道防線

**iterative server**（循序 server）是最直接的寫法：一個迴圈，`accept()` 一條連線，服務到它結束，再 `accept()` 下一條。它不能同時服務多條連線，但它讓我們先專心把「一條連線」寫對：解析、keep-alive、大小上限和期限。後面每一版的並行模型都只是換掉外面那層迴圈，裡面這段處理邏輯的道理完全一樣。

期限要特別小心。直覺的寫法是 `conn.settimeout(0.5)`，但 socket 的 timeout 是**每一次** `recv()` 各自計算的：只要 client 每 0.4 秒送 1 byte，每一次 `recv()` 都在逾時之前拿到資料，整個 header 可以拖上好幾分鐘。這正是 Rita 那三千條慢速連線的手法，業界常把這類攻擊叫 **slowloris**（慢速 header 攻擊）。

```text
 client 每 0.1 秒送 1 byte："G" "E" "T" " " "/" ...（34 bytes 的 header 要送 3.4 秒）

 時間（秒）   0.0   0.1   0.2   0.3   0.4   0.5   0.6  ...  3.4
 收到 byte     │     │     │     │     │     │     │         │
 每次 recv     ├─0.1─┼─0.1─┼─0.1─┼─0.1─┼─0.1─┼─0.1─┤ ... 每次都在 0.3 秒內等到資料
 逾時 0.3 秒   從不觸發，thread 被佔住 3.4 秒（換成每 0.29 秒 1 byte，可以佔住更久）

 header 期限   ├────────── deadline = 0.5 ──────────┤
 0.5 秒                                        ▲ 到期：回 408，關閉
```

上半部是「每次 recv 的逾時」：計時器在每個 byte 抵達時歸零，慢速 client 只要比逾時快一點點，就能無限期地佔住資源。下半部是**期限**：從開始讀 header 的那一刻算起，不管中間收到幾個 byte，0.5 秒一到就結束。實作方式是記下 `deadline = 現在 + 0.5`，每次 `recv()` 之前把 socket 的 timeout 設成「離期限還剩多久」，剩下的時間小於等於 0 就直接回 408。

下面是第一版的完整程式。`read_request()` 依狀態機的順序處理閒置、header、body 三段等待，每段都有自己的期限；`handle_connection()` 負責 keep-alive 迴圈與 lingering close；`serve_iterative()` 就是那個「一次一條」的外層迴圈。程式最後用五個 client 測試四道防線。

```python
import json
import socket
import threading
import time

MAX_HEADER = 8 * 1024      # header 區（含請求行）上限；nginx 預設的大 header buffer 是 8k
MAX_BODY = 64 * 1024       # body 上限；超過回 413
HEADER_TIMEOUT = 0.5       # 從連線建立（或第一個 byte）起，整個 header 必須在這段時間內到齊
BODY_TIMEOUT = 0.5         # body 的總期限
IDLE_TIMEOUT = 0.5         # keep-alive 閒置多久就關
REASONS = {200: "OK", 400: "Bad Request", 408: "Request Timeout", 413: "Content Too Large",
           431: "Request Header Fields Too Large", 501: "Not Implemented"}


class HTTPError(Exception):
    def __init__(self, status):
        super().__init__(status)
        self.status = status


def recv_into(conn, buf, deadline, status):
    """讀一次，但等待時間不超過 deadline：這是「期限」，不是「每次 recv 的逾時」。"""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise HTTPError(status)
    conn.settimeout(remaining)
    try:
        chunk = conn.recv(4096)
    except TimeoutError:
        raise HTTPError(status) from None
    if not chunk:
        raise ConnectionAbortedError("client 中途關閉")
    buf += chunk


def read_request(conn, buf, first):
    """回傳 (method, path, headers, body, keep_alive)；閒置逾時或 client 關閉則回傳 None。"""
    if not buf and not first:                  # keep-alive：等下一個請求的第一個 byte
        conn.settimeout(IDLE_TIMEOUT)
        try:
            chunk = conn.recv(4096)
        except TimeoutError:
            return None
        if not chunk:
            return None
        buf += chunk
    deadline = time.monotonic() + HEADER_TIMEOUT
    while (end := buf.find(b"\r\n\r\n")) < 0:
        if len(buf) > MAX_HEADER:
            raise HTTPError(431)
        recv_into(conn, buf, deadline, 408)
    if end > MAX_HEADER:
        raise HTTPError(431)
    lines = bytes(buf[:end]).decode("latin-1").split("\r\n")
    del buf[:end + 4]                          # 留下的 bytes 屬於 body 或下一個請求
    parts = lines[0].split(" ")
    if len(parts) != 3 or parts[2] not in ("HTTP/1.1", "HTTP/1.0"):
        raise HTTPError(400)
    method, path, version = parts
    headers = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if not sep or not name or name != name.strip():
            raise HTTPError(400)               # 名稱與冒號之間有空白：第 20 章的 smuggling 防線
        headers[name.lower()] = value.strip()
    if "transfer-encoding" in headers:
        raise HTTPError(501)                   # 這個教學 server 不實作 chunked request
    length = headers.get("content-length", "0")
    if not length.isdigit():
        raise HTTPError(400)
    if int(length) > MAX_BODY:
        raise HTTPError(413)                   # 看 header 就拒絕，不必先收完 body
    deadline = time.monotonic() + BODY_TIMEOUT
    while len(buf) < int(length):
        recv_into(conn, buf, deadline, 408)
    body = bytes(buf[:int(length)])
    del buf[:int(length)]
    conn_hdr = headers.get("connection", "").lower()
    keep = conn_hdr != "close" if version == "HTTP/1.1" else conn_hdr == "keep-alive"
    return method, path, headers, body, keep


def response(status, body, keep):
    head = (f"HTTP/1.1 {status} {REASONS[status]}\r\n"
            f"Content-Length: {len(body)}\r\nContent-Type: application/json\r\n")
    if not keep:
        head += "Connection: close\r\n"
    return head.encode() + b"\r\n" + body      # header 與 body 一次送出，避開 Nagle（第 11 章）


ONLINE = set()


def app(method, path, body):
    if method == "POST" and path == "/presence":
        ONLINE.add(body.decode())
    return 200, json.dumps({"online": len(ONLINE)}).encode()


def handle_connection(conn):
    buf, first = bytearray(), True
    with conn:
        try:
            while (req := read_request(conn, buf, first)) is not None:
                first = False
                method, path, headers, body, keep = req
                status, payload = app(method, path, body)
                conn.sendall(response(status, payload, keep))
                if not keep:
                    break
        except HTTPError as exc:
            conn.sendall(response(exc.status, b"", keep=False))
            conn.shutdown(socket.SHUT_WR)      # 先送 FIN，再稍微讀掉殘留資料，避免 RST 蓋掉錯誤回應
            conn.settimeout(0.1)
            try:
                while conn.recv(4096):
                    pass
            except OSError:
                pass
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass


def serve_iterative(listener):
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return                              # listener 被關閉：結束
        handle_connection(conn)                 # 一次只服務一條連線，做完才 accept 下一條


listener = socket.create_server(("127.0.0.1", 0), backlog=16)
threading.Thread(target=serve_iterative, args=(listener,), daemon=True).start()
addr = listener.getsockname()


def read_all(s):
    data = b""
    while chunk := s.recv(65536):
        data += chunk
    return data


# 1. keep-alive：同一條連線送兩個請求
with socket.create_connection(addr, timeout=2) as s:
    s.sendall(b"POST /presence HTTP/1.1\r\nHost: rt.shengsheng.example\r\nContent-Length: 12\r\n\r\nstudent-0457"
              b"GET /presence HTTP/1.1\r\nHost: rt.shengsheng.example\r\nConnection: close\r\n\r\n")
    replies = read_all(s).split(b"HTTP/1.1 ")[1:]
print("1. keep-alive    ", [r.split(b"\r\n")[0].decode() for r in replies], replies[-1].split(b"\r\n\r\n")[1].decode())

# 2. header 太大
with socket.create_connection(addr, timeout=2) as s:
    s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\nCookie: " + b"a" * 9000 + b"\r\n\r\n")
    print("2. 9 KB cookie   ", read_all(s).split(b"\r\n")[0].decode())

# 3. 宣告的 body 太大：server 看 header 就拒絕
with socket.create_connection(addr, timeout=2) as s:
    s.sendall(b"POST /upload HTTP/1.1\r\nHost: x\r\nContent-Length: 1000000\r\n\r\n")
    print("3. 1 MB body     ", read_all(s).split(b"\r\n")[0].decode())

# 4. 每 0.1 秒滴一個 byte：每次 recv 都不會逾時，但整體期限會到
with socket.create_connection(addr, timeout=2) as s:
    s.settimeout(0.1)
    start, reply = time.monotonic(), b""
    for byte in b"GET /presence HTTP/1.1\r\nHost: x\r\n":
        s.send(bytes([byte]))
        try:
            reply = s.recv(65536)               # 每滴一個 byte 就看一下 server 有沒有回話
            break
        except TimeoutError:
            continue
    status = reply.split(b"\r\n")[0].decode()
    print(f"4. 慢速 header   {status}，約 {time.monotonic() - start:.1f} 秒")

# 5. keep-alive 閒置：送完一個請求後不再說話
with socket.create_connection(addr, timeout=2) as s:
    s.sendall(b"GET /presence HTTP/1.1\r\nHost: x\r\n\r\n")
    start = time.monotonic()
    first = s.recv(65536)
    rest = read_all(s)                           # 等 server 因閒置而關閉
    print(f"5. 閒置連線      回應後約 {time.monotonic() - start:.1f} 秒收到 EOF")

assert [r.split(b"\r\n")[0] for r in replies] == [b"200 OK", b"200 OK"]
assert status.endswith("408 Request Timeout")
listener.close()
```

```text
1. keep-alive     ['200 OK', '200 OK'] {"online": 1}
2. 9 KB cookie    HTTP/1.1 431 Request Header Fields Too Large
3. 1 MB body      HTTP/1.1 413 Content Too Large
4. 慢速 header   HTTP/1.1 408 Request Timeout，約 0.5 秒
5. 閒置連線      回應後約 0.5 秒收到 EOF
```

逐行看。第 1 行是 keep-alive：client 在一次 `sendall()` 裡連送兩個請求（HTTP/1.1 的 pipelining），server 依序回了兩個 200，第二個請求帶 `Connection: close`，server 回完就關閉。能處理這種情況，是因為 `read_request()` 把 `\r\n\r\n` 之後多讀到的 bytes 留在 `buf` 裡，下一輪直接從那裡開始解析，這和第 11 章的 framing 是同一件事：一次 `recv()` 可能拿到半個請求，也可能拿到一個半。

第 2、3 行是大小上限。9 KB 的 cookie 讓 header 超過 8 KB 上限，server 回 431；宣告 1 MB 的 body 時，server 只看 `Content-Length` 就回 413，一個 body 的 byte 都沒讀。先檢查宣告的長度再決定要不要讀，是 body 上限的關鍵：如果先讀完再檢查，攻擊者照樣能讓你收下 1 GB。第 4 行是期限：client 每 0.1 秒送 1 byte，每一次 `recv()` 都很快拿到資料，但 header 期限在 0.5 秒時到期，server 回 408 並關閉。第 5 行是 keep-alive 的閒置期限：回應送完之後 0.5 秒沒有新請求，server 主動關閉，client 讀到 EOF；這時 TIME_WAIT 會落在 server 端（第 10 章）。

這個 server 的解析刻意嚴格：header 名稱與冒號之間有空白就回 400，看到 `Transfer-Encoding` 就回 501（Not Implemented，本章不實作 chunked request），`Content-Length` 不是純數字就回 400。這些都是第 20 章 request smuggling 那張表的防線：寧可拒絕，也不要猜。

## 40.4 一次一條連線：accept queue 裡的等待

iterative server 的問題在哪裡？把它放到故事的情境裡：學生 A 的瀏覽器送完心跳，連線依 HTTP/1.1 的預設保持開著。server 還在 A 的連線上等下一個請求，這時 B、C 連進來。

```text
 學生 A                    server（iterative）                    學生 B
   │── 心跳 ─────────────────►│ handle(A)                            │
   │◄────────────── 200 ──────│                                      │
   │  （keep-alive，連線不關）│ 在 A 的連線上等下一個請求……         │
   │                          │                       ◄── SYN ───────│
   │                          │ 核心自動回 SYN+ACK    ─── SYN+ACK ──►│
   │                          │                       ◄── ACK ───────│ connect() 回傳
   │                          │ B 躺在 accept queue                  │
   │                          │                       ◄── 心跳 ──────│ 資料進了核心 buffer
   │                          │ ……A 閒置逾時，server 關閉 A          │
   │                          │ accept() 拿到 B，讀到心跳            │
   │                          │──────────────────────── 200 ────────►│ 等了一整個閒置逾時
```

這張時序圖幾乎是第 10 章實驗二的重演。B 的 `connect()` 立刻成功，因為交握由核心完成，連線放進 accept queue，B 的心跳也已經在核心的接收 buffer 裡。但應用程式要等 A 的連線結束才會 `accept()` 下一條，所以 B 的等待時間等於 A 的閒置逾時。如果 B 也是 keep-alive，C 就要等 A 加上 B。等排隊的連線數超過 backlog，新的 SYN 被核心默默丟掉，client 看到的是 connect 逾時，而不是被拒絕。下面的程式量出這個現象：

```python
import socket
import threading
import time

IDLE_TIMEOUT = 0.4   # keep-alive 閒置上限
RESPONSE = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"


def handle(conn):
    """極簡版：每讀到一個完整 header 就回一次，閒置超過 IDLE_TIMEOUT 才關閉。"""
    buf = b""
    conn.settimeout(IDLE_TIMEOUT)
    with conn:
        while True:
            try:
                chunk = conn.recv(4096)
            except TimeoutError:
                return
            if not chunk:
                return
            buf += chunk
            while b"\r\n\r\n" in buf:
                _, buf = buf.split(b"\r\n\r\n", 1)
                conn.sendall(RESPONSE)


def serve_iterative(listener):
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        handle(conn)                       # 這條連線結束前，accept queue 裡的人只能等


listener = socket.create_server(("127.0.0.1", 0), backlog=16)
threading.Thread(target=serve_iterative, args=(listener,), daemon=True).start()
addr = listener.getsockname()
t0 = time.monotonic()
ms = lambda: (time.monotonic() - t0) * 1000

# 學生 A：送一個請求，拿到回應後把連線留著（瀏覽器的 keep-alive 就是這樣）
a = socket.create_connection(addr)
a.sendall(b"GET /presence HTTP/1.1\r\nHost: x\r\n\r\n")
a.recv(100)
print(f"A 拿到回應          {ms():6.1f} ms，連線保持開著")

# 學生 B、C：連線立刻成功（核心完成交握、放進 accept queue），回應卻要等
others = []
for name in "BC":
    s = socket.create_connection(addr)
    print(f"{name} connect() 回傳     {ms():6.1f} ms")
    s.sendall(b"GET /presence HTTP/1.1\r\nHost: x\r\n\r\n")
    others.append((name, s))
waits = {}
for name, s in others:
    s.recv(100)
    waits[name] = ms()
    print(f"{name} 拿到回應          {waits[name]:6.1f} ms")

assert waits["B"] > IDLE_TIMEOUT * 1000 * 0.9     # B 等的正是 A 的閒置逾時
for s in [a] + [s for _, s in others]:
    s.close()
listener.close()
```

```text
A 拿到回應             1.8 ms，連線保持開著
B connect() 回傳        2.0 ms
C connect() 回傳        2.2 ms
B 拿到回應           406.3 ms
C 拿到回應           808.5 ms
```

三個 `connect()` 都在 2 毫秒內完成，但 B 的回應在 406 毫秒才到，C 在 808 毫秒，剛好是一個與兩個閒置逾時（毫秒數每次執行略有不同）。這就是故事裡「p50 只有 2 毫秒、p99 是逾時上限」的原因：排到的人很快，排隊的人等了別人的整個 keep-alive 時間。在 Linux 上用 `ss -ltn` 看這個 server，`Recv-Q` 會隨排隊的連線數上升；`Send-Q` 是 backlog 上限，`socketserver.TCPServer` 預設只有 5。

所以 iterative server 只適合兩種情況：每條連線只處理一個請求而且處理得很快（例如 HTTP/1.0、`Connection: close`），或者前面有一個會把請求收完整才轉過來的 proxy。gunicorn 的 **sync worker** 就是第二種：每個 worker process 一次只處理一個請求，而且不支援 keep-alive，回完就關閉連線，所以官方建議一定要放在 nginx 這類會緩衝請求的 proxy 後面。我們在 40.6 節會看到，它用多個 process 來彌補「一次一條」的限制。

## 40.5 thread-per-connection 與 thread pool

讓多條連線同時被服務，最直接的方法是**每條連線一條 thread**（thread-per-connection）：主 thread 只負責 `accept()`，每拿到一條連線就開一條新的 thread 去跑 `handle_connection()`。程式幾乎不用改，原本的阻塞式寫法照用，等待的工作交給作業系統的排程器：一條 thread 卡在 `recv()`，核心就切去跑別的 thread。`ThreadingHTTPServer` 就是這個模型。

它的問題是**資源跟著連線數走，而連線數由 client 決定**。故事裡 Rita 開三千條慢速連線，server 就有三千條 thread 在 `recv()` 裡睡覺，每條都佔著一個 fd、一份 thread stack 與核心的排程結構。另一個選擇是 **thread pool**：預先開固定數量的 worker thread，主 thread 把 accept 到的連線放進佇列，worker 有空就取一條來處理。資源有了上限，代價是 worker 全部被佔住時，新的連線只能在佇列裡等。

```text
 thread-per-connection                          thread pool（4 個 worker）
 ┌──────────┐                                   ┌──────────┐     ┌───────────────────┐
 │ accept   │── conn 1 ──► thread 1              │ accept   │────►│ 佇列 queue.Queue  │
 │ thread   │── conn 2 ──► thread 2              │ thread   │     │ [c5] [c6] [c7]... │
 │          │── conn 3 ──► thread 3              └──────────┘     └───────────────────┘
 │          │── ...                                                  │  │  │  │ 有空才取
 │          │── conn N ──► thread N                                  ▼  ▼  ▼  ▼
 └──────────┘                                               worker1 worker2 worker3 worker4
 thread 數 = 連線數（沒有上限）                  thread 數固定；慢速連線佔住 worker，後面的人排隊
```

左邊的 thread 數隨連線無限增加，慢速 client 不會擋到別人，但會吃掉資源；右邊的 thread 數固定，資源可控，但 4 個慢速 client 就能讓整個 pool 停擺，這時佇列成了第二個 accept queue。兩者都依賴 40.3 節的期限：沒有期限，thread-per-connection 會被慢速連線撐爆，thread pool 會被慢速連線卡死。下面用 6 個「header 送一半就停」的慢速 client 測試兩種模型，再看 300 條閒置連線會產生多少條 thread：

```python
import queue
import socket
import threading
import time

HEADER_TIMEOUT = 0.6
RESPONSE = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"


def handle(conn):
    """讀完 header 就回應並關閉；header 期限到了就放棄（慢速 client 最多佔住 worker 這麼久）。"""
    deadline, buf = time.monotonic() + HEADER_TIMEOUT, b""
    with conn:
        while b"\r\n\r\n" not in buf:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            conn.settimeout(remaining)
            try:
                chunk = conn.recv(4096)
            except (TimeoutError, OSError):
                return
            if not chunk:
                return
            buf += chunk
        conn.sendall(RESPONSE)


def thread_per_connection(listener):
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        threading.Thread(target=handle, args=(conn,), name="thread_per_connection", daemon=True).start()


def thread_pool(listener, workers=4):
    jobs = queue.Queue()                       # accept 之後、worker 有空之前，連線在這裡排隊

    def worker():
        while True:
            handle(jobs.get())

    for _ in range(workers):
        threading.Thread(target=worker, name="thread_pool", daemon=True).start()
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        jobs.put(conn)


def trial(model, slow=6, idle=0):
    listener = socket.create_server(("127.0.0.1", 0), backlog=512)
    threading.Thread(target=model, args=(listener,), name=model.__name__, daemon=True).start()
    addr = listener.getsockname()
    hogs = [socket.create_connection(addr) for _ in range(slow + idle)]
    for h in hogs[:slow]:
        h.sendall(b"GET /presence HTTP/1.1\r\n")   # header 只送一半就停住
    time.sleep(0.1)
    threads = sum(t.name == model.__name__ for t in threading.enumerate())
    start = time.monotonic()
    with socket.create_connection(addr, timeout=3) as s:
        s.sendall(b"GET /presence HTTP/1.1\r\nHost: x\r\n\r\n")
        ok = s.recv(100).startswith(b"HTTP/1.1 200")
    wait = (time.monotonic() - start) * 1000
    for h in hogs:
        h.close()
    listener.close()
    time.sleep(0.05)                           # 讓這一輪的 thread 結束，下一輪重新計數
    return threads, wait, ok


for label, model in (("thread-per-connection", thread_per_connection), ("thread pool (4)", thread_pool)):
    threads, wait, ok = trial(model)
    print(f"{label:<22} 6 個慢 client：server thread {threads:>3} 條，正常請求等了 {wait:6.1f} ms")
    if model is thread_per_connection:
        assert ok and wait < 100
    else:
        assert ok and wait > HEADER_TIMEOUT * 1000 * 0.8

threads, _, _ = trial(thread_per_connection, slow=0, idle=300)
print(f"thread-per-connection  300 條閒置連線：server thread {threads} 條")
assert threads >= 300
```

```text
thread-per-connection  6 個慢 client：server thread   7 條，正常請求等了    0.7 ms
thread pool (4)        6 個慢 client：server thread   5 條，正常請求等了  500.9 ms
thread-per-connection  300 條閒置連線：server thread 301 條
```

第 1 行，thread-per-connection 為 6 個慢速 client 各開了一條 thread（加上 accept thread 共 7 條），正常請求開了第 8 條，不到 1 毫秒就拿到回應。第 2 行，thread pool 只有 4 個 worker 加 1 條 accept thread，6 個慢速 client 佔住了全部 worker，正常請求在佇列裡等了大約 500 毫秒，也就是 header 期限 0.6 秒減去測試前等待的 0.1 秒：worker 要等慢速連線逾時才會空出來。第 3 行，300 條什麼都不送的連線就產生 301 條 thread。把數字放大十幾倍，就是故事裡的四千多條 thread，直到 fd 上限讓 `accept()` 失敗為止。

thread 到底貴在哪裡？在 Linux 上，每條 thread 預設保留 8 MB 的虛擬位址空間當 stack（`ulimit -s`，可以用 `threading.stack_size()` 調小），實際佔用的實體記憶體只有用到的頁面，通常是幾十 KB 到數百 KB；另外還有核心的排程結構、context switch 的成本，以及 Python 自己的 thread 狀態。幾千條 thread 在現代 Linux 上跑得動，但記憶體與排程成本會隨連線數線性上升。對 CPython 還有一個額外限制：預設的直譯器有 **GIL**（Global Interpreter Lock，全域直譯器鎖），同一時刻只有一條 thread 在執行 Python bytecode，thread 只在等 I/O 時才真正平行。所以 Python 的 thread 適合 I/O 密集的工作，不能拿來擴展 CPU 運算。

> [!note] 2026 現況
> 截至 2026 年 10 月，CPython 有一個可選的 **free-threaded** 建置（PEP 703），移除了 GIL，讓多條 thread 能同時執行 Python 程式；它在 3.13 以實驗性質推出，3.14 起成為官方支援的選項，但仍不是預設建置，部分 C extension 也還在適配中（依 2026 年 10 月的了解整理，版本細節請以 Python 官方文件為準）。即使 GIL 不再存在，thread 的記憶體與排程成本、以及「資源跟著連線數走」的問題都還在，本章的結論不變。

## 40.6 用 process 擴展：pre-fork 與 arbiter

thread 共享記憶體，一條 thread 把 process 弄壞（例如 C extension 記憶體錯誤，或程式呼叫 `os._exit`），整個 process 一起倒下。另一條路是用 **process**：每個 worker 是獨立的 process，有自己的記憶體與自己的 GIL，可以真正用滿多顆 CPU，一個 worker 當掉也不影響其他人。歷史上有兩種寫法。**fork-per-connection** 是每 accept 一條連線就 `fork()` 一個子 process 去處理，早期的 inetd 與一些經典 Unix 服務就是這樣，但 fork 的成本讓它撐不住高連線數。**pre-fork** 則是先開好固定數量的 worker：

```text
                     ┌──────────────────────────────────────┐
                     │ arbiter（主 process）                │
                     │ 1. bind + listen 10.20.3.21:8000     │
                     │ 2. fork 出 N 個 worker               │
                     │ 3. waitpid()：worker 死了就重新 fork │
                     └──────────────────────────────────────┘
                          │ fork 時，子 process 繼承 listening socket 的 fd
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │ worker 1 │   │ worker 2 │   │ worker 3 │   每個 worker 自己呼叫 accept()，
     │ accept() │   │ accept() │   │ accept() │   核心把每條新連線交給其中一個
     └──────────┘   └──────────┘   └──────────┘
           ▲              ▲              ▲
           └──────────────┴──────────────┘
              同一個 accept queue（同一個 listening socket）
```

arbiter（gunicorn 對主 process 的稱呼）先 `listen()`，再 `fork()`；子 process 繼承了同一個 listening socket 的 fd，所以三個 worker 是從**同一個** accept queue 取連線。arbiter 本身不處理請求，只負責管理 worker：worker 結束時，`waitpid()` 會讓 arbiter 知道，於是重新 fork 一個補上。gunicorn 的 sync worker、經典的 Apache prefork 都是這個架構；gunicorn 的 gthread worker 則是在每個 worker process 裡再放一個 thread pool，兩層並行。

```python
import os
import signal
import socket
from collections import Counter

WORKERS = 3


def worker_loop(listener, number):
    """子 process：和 gunicorn 的 sync worker 一樣，自己 accept、自己處理，一次一條連線。"""
    while True:
        conn, _ = listener.accept()
        with conn:
            request = conn.recv(4096)
            if request.startswith(b"GET /crash"):
                os._exit(1)                         # 模擬 worker 當掉：只影響這一個 process
            body = f"worker-{number}".encode()
            conn.sendall(b"HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: %d\r\n\r\n%s"
                         % (len(body), body))


def spawn(listener, number):
    pid = os.fork()
    if pid == 0:                                    # 子 process 繼承了 listening socket 的 fd
        try:
            worker_loop(listener, number)
        finally:
            os._exit(0)
    return pid


listener = socket.create_server(("127.0.0.1", 0), backlog=64)   # 先 listen，再 fork
children = {spawn(listener, n): n for n in range(1, WORKERS + 1)}
addr = listener.getsockname()


def get(path):
    with socket.create_connection(addr, timeout=2) as s:
        s.sendall(f"GET {path} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        data = s.recv(4096)
    return data.split(b"\r\n\r\n", 1)[1].decode() if data else "（連線被關閉，沒有回應）"


served = Counter(get("/presence") for _ in range(12))
print("12 個請求的分布：", dict(sorted(served.items())))

print("請求 /crash：", get("/crash"))
pid, status = os.waitpid(-1, 0)                     # arbiter 的工作：發現有 worker 死了
number = children.pop(pid)
print(f"arbiter：worker-{number}（pid {pid}）結束，exit code {os.waitstatus_to_exitcode(status)}，重新 fork")
children[spawn(listener, number)] = number

after = Counter(get("/presence") for _ in range(12))
print("重生後 12 個請求：", dict(sorted(after.items())))

for pid in children:
    os.kill(pid, signal.SIGTERM)
    os.waitpid(pid, 0)
listener.close()
assert sum(served.values()) == 12 and sum(after.values()) == 12
assert len(children) == WORKERS
```

```text
12 個請求的分布： {'worker-1': 4, 'worker-2': 4, 'worker-3': 4}
請求 /crash： （連線被關閉，沒有回應）
arbiter：worker-1（pid 91962）結束，exit code 1，重新 fork
重生後 12 個請求： {'worker-1': 4, 'worker-2': 4, 'worker-3': 4}
```

前 12 個請求分散到三個 worker；在 macOS 上這次剛好平均分配，在 Linux 上分布可能不平均，因為核心只保證每條連線交給一個 worker，不保證輪流。接著請求 `/crash` 讓 worker-1 直接結束：client 只看到連線被關閉，沒有任何回應，但其他 worker 完全不受影響。arbiter 從 `waitpid()` 得知 exit code 1，立刻重新 fork 一個 worker-1，之後 12 個請求又平均分散（pid 每次執行都不同）。這就是 process 模型的「故障隔離」。

多個 process 一起等同一個 listening socket，會遇到一個古老的名詞：**thundering herd**（驚群），也就是一條新連線到達時，把所有等待中的 worker 都叫醒，結果只有一個搶到、其他白醒一次。對阻塞式 `accept()`，Linux 早已只叫醒一個；但如果每個 worker 是用 epoll 監看 listening socket，就需要 `EPOLLEXCLUSIVE`（Linux 4.5 起）之類的機制來避免。另一個做法是第 10 章提過的 `SO_REUSEPORT`：每個 worker 各自建立 listening socket、bind 到同一個 port，核心依連線的四元組雜湊把新連線分給不同的 socket，各有各的 accept queue。nginx 的 `listen ... reuseport` 與 gunicorn 的 `--reuse-port` 就是這個選項。注意 macOS 與 BSD 上 `SO_REUSEPORT` 的語意不同，不會做這種分流。

process 模型也有代價：每個 worker 都有一份完整的記憶體（fork 之後靠 copy-on-write 共享一部分，但 Python 的引用計數會讓共享頁面很快被寫髒），worker 之間不能直接共享 Python 物件。故事裡的在線名單如果放在 process 的記憶體裡，三個 worker 會有三份不同的名單，這也是 production 服務把共享狀態放到 Redis 或資料庫的原因。

## 40.7 C10K、fd 上限與每條連線的成本

1999 年，Dan Kegel 寫了一篇文章，標題是〈The C10K problem〉：一台伺服器要怎麼**同時**服務一萬個 client？當時的硬體其實撐得住一萬條連線的流量，撐不住的是「每條連線一條 thread 或一個 process」的模型。這篇文章整理了當時所有的做法，結論指向本章接下來的主角：用少數幾條 thread，搭配**非阻塞 I/O** 與作業系統提供的**事件通知機制**（Linux 的 epoll、BSD 的 kqueue），讓一條 thread 同時照顧成千上萬條連線。今天 nginx、Node.js、Go 的 netpoller、Python 的 asyncio 都建立在這個想法上。

C10K 的核心觀察是：**連線很多，但同一時刻真正有事可做的連線很少**。presence 服務的兩千條 keep-alive 連線，每條每 15 秒才送一次心跳，任何一個瞬間絕大多數連線都在閒置。thread 模型為每條閒置連線付出一整條 thread 的成本；event loop 模型只為它付出一個 fd 和一小塊 buffer。下表比較各模型的每條連線成本與面對慢速 client 的行為：

| 模型 | 每條連線的成本 | 慢速或閒置 client 的影響 | 能否用到多核 | 代表實作 |
|---|---|---|---|---|
| iterative | 極低（同一時間只有一條） | 擋住所有人 | 否 | 教學用 server |
| thread-per-connection | 一條 thread（stack、排程） | 不擋別人，但吃資源 | Python 受 GIL 限制 | `ThreadingHTTPServer` |
| thread pool | 佇列裡只是一個 fd；被服務時佔一條 worker | 佔滿 worker 後其他人排隊 | 同上 | gunicorn gthread（每個 process 內） |
| pre-fork process | 一個 process（數十 MB） | 每個 worker 一次一條 | 是 | gunicorn sync、Apache prefork |
| event loop | 一個 fd 加幾 KB buffer | 幾乎不影響，只佔一個 fd | 單 thread；多核靠多 process | nginx、uvicorn、asyncio |

不管哪個模型，有一個成本躲不掉：**每條連線一個 fd**。fd 有兩層上限：process 層的 `RLIMIT_NOFILE`（`ulimit -n` 看到的 soft limit，Linux 常見預設 1024，macOS 的 shell 常見 256；systemd 服務用 `LimitNOFILE=` 設定），以及整台主機的 `fs.file-max`。server 用到的 fd 不只客戶端連線：listening socket、log 檔、連到資料庫與上游服務的連線、event loop 的 epoll／kqueue 本身都要一個。fd 用完時，`accept()` 會失敗並得到 `EMFILE`（Too many open files），這就是故事裡 presence 倒下的方式。

`EMFILE` 有一個陷阱：發生時，連線已經完成交握、躺在 accept queue 裡。在 Linux 上，`accept()` 失敗不會把連線從佇列移除，所以 listening socket 一直是「可讀」的，一個天真的 event loop 會不停地被叫醒、`accept()`、失敗、再被叫醒，吃滿一顆 CPU 卻什麼事都沒做。下面的程式把 soft limit 壓低來重現 `EMFILE`，並觀察排隊中的連線後來怎麼了：

```python
import errno
import os
import resource
import selectors
import socket
import sys
import time

soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
print(f"{sys.platform}：這個 process 的 fd 上限 soft={soft}, hard={hard}（依機器與 shell 設定而異）")

listener = socket.create_server(("127.0.0.1", 0), backlog=32)
listener.setblocking(False)
sel = selectors.DefaultSelector()              # selector 本身（kqueue／epoll）也佔一個 fd
sel.register(listener, selectors.EVENT_READ)
clients = [socket.create_connection(listener.getsockname()) for _ in range(10)]

# 把 soft limit 壓到「目前最大的 fd 號碼 + 4」，模擬一個 fd 快用完的 server
highest = max(int(n) for n in os.listdir("/dev/fd"))
resource.setrlimit(resource.RLIMIT_NOFILE, (highest + 4, hard))

accepted, emfile, end = [], 0, time.monotonic() + 0.1
while time.monotonic() < end:                  # 天真的 event loop：可讀就 accept
    if not sel.select(timeout=0.01):
        continue
    try:
        accepted.append(listener.accept()[0])
    except BlockingIOError:
        pass
    except OSError as exc:
        assert exc.errno == errno.EMFILE
        emfile += 1
resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))
print(f"accept 成功 {len(accepted)} 條，之後 0.1 秒內 EMFILE {emfile} 次")

still_queued = 0
while True:                                    # fd 恢復後，accept queue 裡還剩幾條？
    try:
        accepted.append(listener.accept()[0])
        still_queued += 1
    except BlockingIOError:
        break
dropped = 0
for c in clients:
    c.setblocking(False)
    try:
        dropped += c.recv(1) == b""            # 讀到 EOF：連線已被 server 端核心關掉
    except BlockingIOError:
        pass                                   # 沒資料也沒 EOF：連線還活著
    except ConnectionResetError:
        dropped += 1
print(f"上限恢復後 accept queue 還剩 {still_queued} 條；client 端發現被關閉的 {dropped} 條")

assert emfile >= 1 and still_queued + dropped == len(clients) - (len(accepted) - still_queued)
for s in clients + accepted + [listener]:
    s.close()
sel.close()
```

```text
darwin：這個 process 的 fd 上限 soft=1048576, hard=1048576（依機器與 shell 設定而異）
accept 成功 4 條，之後 0.1 秒內 EMFILE 6 次
上限恢復後 accept queue 還剩 0 條；client 端發現被關閉的 6 條
```

第 1 行印出目前的上限，這台機器的 shell 把它設得很高，你的機器很可能不同。第 2 行，壓低上限之後 server 只 accept 到 4 條，之後每次嘗試都是 `EMFILE`。第 3 行顯示一個平台差異：在 macOS 上，每次失敗的 `accept()` 都把一條排隊的連線取出並由核心關閉，所以 0.1 秒內剛好失敗 6 次，accept queue 被清空，那 6 個 client 讀到 EOF。在 Linux 上，同一段程式會看到 `EMFILE` 的次數多得多（listener 一直可讀，迴圈原地空轉），而上限恢復後 accept queue 裡還留著那 6 條連線。兩個平台的共同教訓是：**等到 `EMFILE` 才處理就太晚了**。

正確的做法有三層。第一，把 soft limit 調到足夠大，例如 systemd 的 `LimitNOFILE=65536`，並把它納入部署設定，而不是靠登入 shell 的預設值。第二，server 自己設一個**連線數上限**，遠低於 fd 上限，滿了就暫停 accept，讓多出來的連線留在 accept queue（受 backlog 保護），而不是觸發 `EMFILE`；nginx 的 `worker_connections`、gunicorn gthread 與非同步 worker 的 `--worker-connections` 都是這個角色，40.8 節的 event loop 版本也會實作它。第三，監控 fd 用量（`ls /proc/<pid>/fd | wc -l` 對照 `/proc/<pid>/limits`）與第 10 章的 CLOSE_WAIT 數量，fd 洩漏通常會先在這裡現形。有些 server 另外會預留一個空閒的 fd，`EMFILE` 時先釋放它、接下連線回 503 再關閉，讓 client 至少拿到明確的錯誤，這是最後一道保險。

## 40.8 Event loop：非阻塞 socket 與 selectors

前面每一版都用**阻塞式**（blocking）socket：`recv()` 沒資料就讓 thread 睡著，所以「同時等很多條連線」只能靠很多條 thread。event loop 反過來：把 socket 設成**非阻塞**（non-blocking，`setblocking(False)`），沒資料時 `recv()` 不等待，而是立刻丟出 `BlockingIOError`（errno `EAGAIN`／`EWOULDBLOCK`）。然後由一條 thread 問作業系統：「這一大堆 socket 裡，哪些現在可以讀、哪些可以寫？」作業系統回答之後，只對那些 socket 做事，做完再問一次。這個「問、做、再問」的迴圈就是 **event loop**（事件迴圈）。

```text
                ┌───────────────────────────────────────────────────────────┐
                │ event loop（一條 thread）                                 │
                │                                                           │
                │  ① events = selector.select(timeout = 最近的期限 - 現在)  │◄───┐
                │       │  核心回報：fd 7 可讀、fd 9 可寫、listener 可讀    │    │
                │       ▼                                                   │    │
                │  ② listener 可讀 → accept()，新連線註冊 EVENT_READ        │    │
                │     fd 7 可讀    → recv() 放進 inbuf，夠一個請求就處理    │    │
                │     fd 9 可寫    → send(outbuf)，送多少算多少             │    │
                │       │                                                   │    │
                │       ▼                                                   │    │
                │  ③ 檢查期限：header／body／閒置／寫入逾時的連線一律關閉   │────┘
                └───────────────────────────────────────────────────────────┘
       每條連線的狀態：inbuf（收到還沒處理）、outbuf（該送還沒送）、state、deadline
```

逐步看這個迴圈。① `select()` 是唯一會等待的地方，它的 timeout 設成「離最近的期限還有多久」，這樣期限一到迴圈就會醒來；② 只對準備好的 socket 做一次非阻塞操作，絕不在任何一條連線上等待；③ 掃過所有連線，把過期的關掉。因為沒有 thread 可以「停在某一行等待」，每條連線的進度都要存在資料結構裡：收到一半的 header 在 `inbuf`，送到一半的回應在 `outbuf`，目前在哪一段等待記在 `state`。換句話說，40.2 節那張狀態機，在 thread 模型裡藏在程式碼的執行位置裡，在 event loop 裡則是明明白白的一個欄位。

「哪些 socket 準備好了」要怎麼問？作業系統提供了好幾代介面，Python 的 `selectors` 模組把它們包成同一個 API，`selectors.DefaultSelector` 會選目前平台最好的那一個：

| 機制 | 平台 | 每次呼叫的成本 | 限制與特性 |
|---|---|---|---|
| `select` | 幾乎所有平台 | 與監看的 fd 數量成正比，每次都要把整份清單交給核心 | fd 編號受 `FD_SETSIZE`（常見 1024）限制，Python 在 Linux 上遇到更大的 fd 會丟 `ValueError` |
| `poll` | Unix | 與監看的 fd 數量成正比 | 沒有 1024 的限制，但每次仍要掃整份清單 |
| `epoll` | Linux | 與「準備好的」fd 數量成正比 | 監看清單存在核心裡，只回報有事的 fd；支援 level-triggered 與 edge-triggered |
| `kqueue` | macOS、BSD | 與準備好的事件數成正比 | 除了 socket，也能監看檔案、process、timer 等事件 |
| IOCP | Windows | 完成通知模型 | 不是「告訴你可以讀了」，而是「告訴你讀完了」；asyncio 在 Windows 預設用它 |

表的前兩列是 C10K 問題的根源：select 與 poll 每次呼叫都要把一萬個 fd 的清單交給核心、讓核心逐一檢查，連線一多，光是「問」的成本就壓過了真正的工作。epoll 與 kqueue 把監看清單存在核心裡，只回傳有事的 fd，所以成本只和「活躍」的連線數有關，這正好符合 C10K 的觀察。最後一列的 IOCP 是另一種思路，叫 **completion-based**（完成通知）；Linux 5.1 起的 io_uring 也屬於這一類，它讓應用程式把讀寫請求整批交給核心，完成後再取回結果，標準函式庫目前沒有使用它。

epoll 還有一個常被問到的選項：**level-triggered**（水平觸發，預設）表示「只要 buffer 裡還有資料，每次問都回報可讀」；**edge-triggered**（邊緣觸發，`EPOLLET`）只在「從沒有變成有」的那一刻回報一次，應用程式必須一直讀到 `EAGAIN` 為止，否則剩下的資料不會再被提醒。`selectors` 一律使用 level-triggered，寫起來比較不容易漏資料；nginx 這類追求效能的 server 則使用 edge-triggered，並嚴格遵守「讀到 `EAGAIN`」的規則。

### partial read、partial write 與 backpressure

非阻塞 socket 讓兩件在阻塞模式下被隱藏的事浮上檯面。第一是 **partial read**：一次 `recv()` 拿到多少 bytes 完全不保證，可能是半行 header，也可能是兩個請求加上第三個的開頭（第 11 章的 framing）。所以每條連線都要有自己的 `inbuf`，收到什麼先存起來，湊滿一個完整的請求才處理，剩下的留給下一次。第二是 **partial write**：非阻塞的 `send()` 只會把資料放進核心的送出 buffer，放得下多少就送多少，回傳實際送出的 byte 數，可能遠小於你給它的長度；buffer 全滿時則直接丟 `BlockingIOError`。阻塞模式的 `sendall()` 會替你一直等到全部送完，非阻塞模式則要自己把沒送完的部分留在 `outbuf`，等 socket 可寫時再送。

```text
 應用程式                 outbuf（使用者空間）          核心送出 buffer          client（下載很慢）
 回應 2 MB ─────────────► [██████████████████]
                          send() 回傳 400 KB ─────────► [████ 滿了 ████] ─────► 每次只讀 64 KB
                          [██████████████]              │
                          註冊 EVENT_WRITE，等可寫       │ client 讀走一些，騰出空間
                          send() 回傳 300 KB ─────────► [████████████]
                          ……直到 outbuf 清空，改回只關心 EVENT_READ
 outbuf 超過 high-water mark 時：暫停讀這條連線的新請求（backpressure）
```

這張圖說明 2 MB 的錄影片段怎麼送給一個下載很慢的手機。核心的送出 buffer 只有幾百 KB，第一次 `send()` 只送出一部分，剩下的留在 `outbuf`；server 這時註冊 `EVENT_WRITE`，去服務別的連線，等 client 讀走資料、buffer 有空間了，selector 回報可寫，再送下一段。兩個細節很重要。第一，**只有 `outbuf` 不是空的時候才註冊 `EVENT_WRITE`**：一條正常的連線幾乎永遠是可寫的，一直監看可寫會讓 `select()` 每次都立刻返回，event loop 原地空轉。第二，`outbuf` 超過一個上限（**high-water mark**）時，暫停讀取這條連線的新請求，這叫 **backpressure**（背壓）：如果 client 一直送 pipelined 請求卻從不讀回應，沒有這個上限，server 的記憶體會被它的回應塞滿。

下面是 event loop 版的 server。它保留了前幾版的全部防線（大小上限、header／body 期限、keep-alive 閒置期限），另外加上寫入期限、high-water mark，以及 40.7 節建議的連線數上限：連線數到達 `MAX_CONNECTIONS` 時，把 listening socket 從 selector 移除，讓多的連線留在 accept queue。

```python
import selectors
import socket
import threading
import time

MAX_HEADER, MAX_BODY = 8 * 1024, 64 * 1024
HEADER_TIMEOUT = BODY_TIMEOUT = IDLE_TIMEOUT = 0.5
WRITE_TIMEOUT = 2.0               # 對方多久不讀（送不出任何 byte）就放棄
HIGH_WATER = 256 * 1024           # 送出 buffer 超過這個量，就暫停讀取（backpressure）
MAX_CONNECTIONS = 3               # 連線數上限：遠低於 fd 上限，滿了就暫停 accept
REASONS = {200: "OK", 400: "Bad Request", 408: "Request Timeout", 413: "Content Too Large",
           431: "Request Header Fields Too Large", 501: "Not Implemented"}
RECORDING = b"x" * (2 * 1024 * 1024)


class HTTPError(Exception):
    pass


class Conn:
    def __init__(self, sock):
        self.sock, self.inbuf, self.outbuf = sock, bytearray(), bytearray()
        self.state, self.deadline = "header", time.monotonic() + HEADER_TIMEOUT
        self.close_after, self.need, self.req = False, 0, None
        self.sends = self.partial = 0


def parse_head(head):
    lines = head.decode("latin-1").split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 3 or parts[2] not in ("HTTP/1.1", "HTTP/1.0"):
        raise HTTPError(400)
    headers = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if not sep or not name or name != name.strip():
            raise HTTPError(400)
        headers[name.lower()] = value.strip()
    if "transfer-encoding" in headers:
        raise HTTPError(501)
    length = headers.get("content-length", "0")
    if not length.isdigit():
        raise HTTPError(400)
    if int(length) > MAX_BODY:
        raise HTTPError(413)
    c = headers.get("connection", "").lower()
    keep = c != "close" if parts[2] == "HTTP/1.1" else c == "keep-alive"
    return parts[0], parts[1], keep, int(length)


def app(method, path, body):
    return 200, RECORDING if path == "/recording" else b'{"online": 1}'


class EventLoopServer:
    def __init__(self, listener):
        self.listener, self.sel = listener, selectors.DefaultSelector()
        listener.setblocking(False)
        self.sel.register(listener, selectors.EVENT_READ, None)
        self.conns, self.paused, self.peak, self.closed = {}, False, 0, []

    def run(self, stop):
        while not stop.is_set():
            now = time.monotonic()
            soonest = min((c.deadline for c in self.conns.values()), default=now + 0.05)
            for key, mask in self.sel.select(timeout=min(max(soonest - now, 0), 0.05)):
                if key.data is None:
                    self.accept()
                    continue
                conn = key.data
                if mask & selectors.EVENT_READ:
                    self.on_read(conn)
                if mask & selectors.EVENT_WRITE and conn.sock.fileno() in self.conns:
                    self.on_write(conn)
            self.expire()

    def accept(self):
        while len(self.conns) < MAX_CONNECTIONS:
            try:
                sock, _ = self.listener.accept()
            except BlockingIOError:
                return
            sock.setblocking(False)
            conn = Conn(sock)
            self.conns[sock.fileno()] = conn
            self.sel.register(sock, selectors.EVENT_READ, conn)
            self.peak = max(self.peak, len(self.conns))
        self.sel.unregister(self.listener)         # 滿了：其餘連線留在 accept queue，不空轉
        self.paused = True

    def close(self, conn):
        self.sel.unregister(conn.sock)
        del self.conns[conn.sock.fileno()]
        conn.sock.close()
        self.closed.append(conn)
        if self.paused:
            self.sel.register(self.listener, selectors.EVENT_READ, None)
            self.paused = False

    def on_read(self, conn):
        try:
            data = conn.sock.recv(65536)
        except BlockingIOError:
            return
        except ConnectionError:
            data = b""
        if not data:
            return self.close(conn)
        conn.inbuf += data                        # partial read：可能只有半行 header，先存起來
        self.process(conn)

    def process(self, conn):
        try:
            while not conn.close_after and len(conn.outbuf) <= HIGH_WATER:
                if conn.state == "idle":
                    if not conn.inbuf:
                        break
                    conn.state, conn.deadline = "header", time.monotonic() + HEADER_TIMEOUT
                if conn.state == "header":
                    end = conn.inbuf.find(b"\r\n\r\n")
                    if end < 0 or end > MAX_HEADER:
                        if len(conn.inbuf) > MAX_HEADER:
                            raise HTTPError(431)
                        break
                    conn.req = parse_head(bytes(conn.inbuf[:end]))
                    del conn.inbuf[:end + 4]
                    conn.state, conn.deadline = "body", time.monotonic() + BODY_TIMEOUT
                if len(conn.inbuf) < conn.req[3]:
                    break                             # body 還沒收齊
                method, path, keep, n = conn.req
                body, conn.inbuf[:n] = bytes(conn.inbuf[:n]), b""
                self.queue(conn, *app(method, path, body), keep)
        except HTTPError as exc:
            self.queue(conn, exc.args[0], b"", keep=False)
        self.update_interest(conn)

    def queue(self, conn, status, payload, keep):
        conn.outbuf += (f"HTTP/1.1 {status} {REASONS[status]}\r\nContent-Length: {len(payload)}\r\n"
                        + ("" if keep else "Connection: close\r\n") + "\r\n").encode() + payload
        conn.close_after = not keep
        conn.state, conn.deadline = "writing", time.monotonic() + WRITE_TIMEOUT

    def update_interest(self, conn):
        events = 0
        if not conn.close_after and len(conn.outbuf) <= HIGH_WATER:
            events |= selectors.EVENT_READ          # 送出 buffer 太滿就先不讀新請求
        if conn.outbuf:
            events |= selectors.EVENT_WRITE         # 只有「有東西要送」才關心可寫，否則會空轉
        self.sel.modify(conn.sock, events or selectors.EVENT_READ, conn)

    def on_write(self, conn):
        try:
            sent = conn.sock.send(conn.outbuf)
        except BlockingIOError:
            return
        except ConnectionError:
            return self.close(conn)
        conn.sends += 1
        conn.partial += sent < len(conn.outbuf)     # partial write：核心只收下一部分
        del conn.outbuf[:sent]
        conn.deadline = time.monotonic() + WRITE_TIMEOUT
        if not conn.outbuf:
            if conn.close_after:
                return self.close(conn)
            conn.state, conn.deadline = "idle", time.monotonic() + IDLE_TIMEOUT
            self.process(conn)                      # buffer 裡可能已有下一個（pipelined）請求
        else:
            self.update_interest(conn)

    def expire(self):
        now = time.monotonic()
        for conn in [c for c in self.conns.values() if now > c.deadline]:
            if conn.state == "body" or (conn.state == "header" and conn.inbuf):
                try:
                    conn.sock.send(b"HTTP/1.1 408 Request Timeout\r\nContent-Length: 0\r\n"
                                   b"Connection: close\r\n\r\n")
                except OSError:
                    pass
            self.close(conn)                        # 閒置、寫不出去、header 沒到齊：一律關閉


listener = socket.create_server(("127.0.0.1", 0), backlog=64)
server, stop = EventLoopServer(listener), threading.Event()
loop_thread = threading.Thread(target=server.run, args=(stop,))
loop_thread.start()
addr = listener.getsockname()
print("selector：", type(server.sel).__name__)

# 1. 慢慢讀 2 MB 的 client A，同時 B 來問一個小請求
a = socket.create_connection(addr)
a.sendall(b"GET /recording HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
got = len(a.recv(65536))
t = time.monotonic()
with socket.create_connection(addr, timeout=2) as b:
    b.sendall(b"GET /presence HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
    b_status = b.recv(4096).split(b"\r\n")[0].decode()
print(f"A 才讀了 {got // 1024} KB；B 的小請求花了 {(time.monotonic() - t) * 1000:.1f} ms 就拿到 {b_status}")
while chunk := a.recv(65536):
    got += len(chunk)
    time.sleep(0.003)                               # 模擬下載很慢的手機
a.close()
time.sleep(0.05)
big = max(server.closed, key=lambda c: c.sends)
print(f"A 共收到 {got // 1024} KB；server 呼叫 send() {big.sends} 次，其中 {big.partial} 次只送出一部分")

# 2. header 送一半就停的 C；與此同時 D 照常被服務
c = socket.create_connection(addr, timeout=2)
c.sendall(b"GET /presence HTTP/1.1\r\nHost:")
t = time.monotonic()
with socket.create_connection(addr, timeout=2) as d:
    d.sendall(b"GET /presence HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
    d_ok = d.recv(4096).startswith(b"HTTP/1.1 200")
c_reply = c.recv(4096).split(b"\r\n")[0].decode()
print(f"慢速 header 的 C 在 {(time.monotonic() - t):.1f} 秒後收到 {c_reply}；D 不受影響：{d_ok}")
c.close()

# 3. 一次來 6 條連線，但 MAX_CONNECTIONS = 3
server.peak = 0
socks = [socket.create_connection(addr, timeout=2) for _ in range(6)]
for s in socks:
    s.sendall(b"GET /presence HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
codes = [s.recv(4096).split(b"\r\n")[0].decode() for s in socks]
print(f"6 條連線全部拿到 200：{all(x.endswith('200 OK') for x in codes)}；同時服務的最大連線數 {server.peak}")

stop.set()
loop_thread.join()
for s in socks:
    s.close()
listener.close()
assert got > len(RECORDING) and big.partial > 0 and d_ok and c_reply.endswith("408 Request Timeout")
assert server.peak == MAX_CONNECTIONS
```

```text
selector： KqueueSelector
A 才讀了 63 KB；B 的小請求花了 2.0 ms 就拿到 HTTP/1.1 200 OK
A 共收到 2048 KB；server 呼叫 send() 7 次，其中 6 次只送出一部分
慢速 header 的 C 在 0.5 秒後收到 HTTP/1.1 408 Request Timeout；D 不受影響：True
6 條連線全部拿到 200：True；同時服務的最大連線數 3
```

第 1 行，macOS 上 `DefaultSelector` 選了 `KqueueSelector`，在 Linux 上會是 `EpollSelector`，程式不用改。第 2 行是 event loop 的核心價值：A 正在慢慢下載 2 MB，B 的小請求照樣在 2 毫秒內完成，因為同一條 thread 從來沒有在 A 身上等待。第 3 行，2 MB 的回應只呼叫了 7 次 `send()`（每次執行略有不同），其中大多數只送出一部分，剩下的都是靠 `outbuf` 加上 `EVENT_WRITE` 接力完成；macOS 的 loopback 送出 buffer 相當大，換成真實網路與較小的 buffer，次數會多很多。

第 4 行，header 送一半的 C 在 0.5 秒時收到 408，D 完全不受影響。注意 event loop 裡的期限不是靠 socket 的 timeout，而是迴圈每一輪自己檢查 `deadline`；這個版本每輪掃過所有連線，連線數很大時，真實的 server 會改用 heap 或 timer wheel（依到期時間排序的資料結構），只檢查最早到期的那幾個。第 5 行，同時來 6 條連線，server 同時服務的最大數量是 3，其餘 3 條在 accept queue 裡等，前面的連線一關閉就恢復 accept，6 條最後都拿到 200。

這個版本也暴露了 event loop 的弱點：**任何一個 handler 只要阻塞，整個迴圈就停住**。如果 `app()` 裡呼叫了一個要 200 毫秒的同步資料庫查詢，這 200 毫秒裡所有連線都沒人服務；CPU 密集的運算也一樣。event loop 模型要求所有 I/O 都是非阻塞的，需要阻塞的工作必須交給另一個 thread 或 process，這是第 42 章 ASGI 生態系反覆強調的規則。

## 40.9 asyncio streams：同一個 event loop，寫成循序的樣子

40.8 節的程式能動，但讀起來很累：一個請求的處理被切成 `on_read`、`process`、`on_write` 好幾段，狀態散落在 `Conn` 的欄位裡。**asyncio** 把同一個 event loop 包裝起來，讓你用 `async`／`await` 寫出看起來像阻塞式的程式。`await reader.readuntil(b"\r\n\r\n")` 的意思是：「header 還沒到齊的話，把這個 **coroutine**（協程，可以在 `await` 處暫停、之後從同一個地方繼續的函式）暫停，先去跑別人，資料到了再回來。」每條連線是一個 **Task**，暫停時它的進度（執行到哪一行、區域變數）自動保存，不再需要手寫狀態機。

```text
 你寫的程式碼      async def handle(reader, writer):  await reader.readuntil(...) / writer.drain()
                                │
 Streams 層        StreamReader（inbuf、limit）     StreamWriter（write 放進 buffer、drain 等待）
                                │
 Transport／       Transport：非阻塞 socket 的 recv／send、partial write、high-water mark
 Protocol 層       Protocol：收到資料就 feed 給 StreamReader
                                │
 event loop        selectors（epoll／kqueue）＋ timer heap（asyncio.timeout 的期限）
```

由下往上看這四層。最底下的 event loop 和 40.8 節做的事一樣：用 selector 等待 I/O，用依到期時間排序的 heap 管理計時器。Transport 層負責非阻塞 socket 的細節，包括 partial write 的緩衝；它有自己的 high-water mark（預設 64 KiB），超過時會通知上層暫停寫入。Streams 層提供 `StreamReader` 與 `StreamWriter`：`readuntil()` 與 `readexactly()` 會在內部 buffer 湊滿需要的資料才返回，`writer.write()` 只是把資料交給 transport，`await writer.drain()` 則在 buffer 超過 high-water mark 時暫停這個 Task，直到 client 讀走資料，這就是 asyncio 版的 backpressure。最上面才是你寫的 handler。

前面幾版的防線在 asyncio 裡都有對應的寫法：`asyncio.start_server(..., limit=8192)` 設定 `StreamReader` 的上限，`readuntil()` 超過上限還沒看到分隔符號時丟 `LimitOverrunError`，對應 431；`asyncio.timeout_at(deadline)`（Python 3.11 起）把一段 `await` 包在總期限裡，對應 408；`readexactly(n)` 讀 body，client 中途關閉時丟 `IncompleteReadError`。

```python
import asyncio
import resource
import threading
import time

MAX_HEADER, MAX_BODY = 8 * 1024, 64 * 1024
HEADER_TIMEOUT = BODY_TIMEOUT = IDLE_TIMEOUT = 0.5
REASONS = {200: "OK", 400: "Bad Request", 408: "Request Timeout", 413: "Content Too Large",
           431: "Request Header Fields Too Large", 501: "Not Implemented"}


class HTTPError(Exception):
    pass


def parse_head(head):
    lines = head.decode("latin-1").split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 3 or parts[2] not in ("HTTP/1.1", "HTTP/1.0"):
        raise HTTPError(400)
    headers = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if not sep or not name or name != name.strip():
            raise HTTPError(400)
        headers[name.lower()] = value.strip()
    if "transfer-encoding" in headers:
        raise HTTPError(501)
    length = headers.get("content-length", "0")
    if not length.isdigit():
        raise HTTPError(400)
    if int(length) > MAX_BODY:
        raise HTTPError(413)
    c = headers.get("connection", "").lower()
    keep = c != "close" if parts[2] == "HTTP/1.1" else c == "keep-alive"
    return parts[0], parts[1], keep, int(length)


def response(status, payload, keep):
    return (f"HTTP/1.1 {status} {REASONS[status]}\r\nContent-Length: {len(payload)}\r\n"
            + ("" if keep else "Connection: close\r\n") + "\r\n").encode() + payload


async def handle(reader, writer):
    loop = asyncio.get_running_loop()
    deadline, first = loop.time() + HEADER_TIMEOUT, True    # 新連線：從 accept 起算 header 期限
    try:
        while True:
            try:
                if not first:                    # keep-alive：等下一個請求的第一個 byte
                    async with asyncio.timeout(IDLE_TIMEOUT):
                        start = await reader.read(1)
                    deadline = loop.time() + HEADER_TIMEOUT
                else:
                    async with asyncio.timeout_at(deadline):
                        start = await reader.read(1)
            except TimeoutError:
                if first:
                    raise HTTPError(408) from None
                return                           # 閒置逾時：安靜地關閉
            if not start:
                return                           # client 關閉了連線
            first = False
            try:
                async with asyncio.timeout_at(deadline):        # 整個 header 的期限
                    head = start + await reader.readuntil(b"\r\n\r\n")
                method, path, keep, n = parse_head(head[:-4])
                async with asyncio.timeout(BODY_TIMEOUT):
                    body = await reader.readexactly(n)
            except TimeoutError:
                raise HTTPError(408) from None
            except asyncio.LimitOverrunError:
                raise HTTPError(431) from None   # 超過 StreamReader 的 limit 還沒看到空行
            except asyncio.IncompleteReadError:
                return                           # client 中途關閉
            writer.write(response(200, b'{"online": 1}', keep))
            await writer.drain()                 # 送出 buffer 太滿時在這裡等：backpressure
            if not keep:
                return
    except HTTPError as exc:
        writer.write(response(exc.args[0], b"", keep=False))
        await writer.drain()
    except ConnectionError:
        pass
    finally:
        writer.close()


async def request(port, raw):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(raw)
    data = await reader.read()                   # 讀到 server 關閉為止
    writer.close()
    return data


async def main():
    server = await asyncio.start_server(handle, "127.0.0.1", 0, limit=MAX_HEADER, backlog=1024)
    port = server.sockets[0].getsockname()[1]

    two = await request(port, b"GET /a HTTP/1.1\r\nHost: x\r\n\r\n"
                              b"GET /b HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
    print("keep-alive 兩個請求：", two.count(b"HTTP/1.1 200 OK"), "個 200")

    big = await request(port, b"GET / HTTP/1.1\r\nCookie: " + b"a" * 9000 + b"\r\n\r\n")
    print("9 KB header：", big.split(b"\r\n")[0].decode())

    t = time.monotonic()
    slow = await request(port, b"GET /presence HTTP/1.1\r\nHost:")
    print(f"header 送一半：{time.monotonic() - t:.1f} 秒後收到", slow.split(b"\r\n")[0].decode())

    idle = [await asyncio.open_connection("127.0.0.1", port) for _ in range(N_IDLE)]
    t = time.monotonic()
    ok = await request(port, b"GET /presence HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
    tasks = len(asyncio.all_tasks())
    print(f"{N_IDLE} 條連線還沒送 header 時：正常請求 {(time.monotonic() - t) * 1000:.1f} ms 拿到 "
          f"{ok.split(b' ')[1].decode()}；task {tasks} 個、OS thread {threading.active_count()} 條")
    for _, w in idle:
        w.close()
    server.close()
    await server.wait_closed()
    assert two.count(b"200 OK") == 2 and b"431" in big and b"408" in slow and b"200" in ok
    assert tasks > N_IDLE and threading.active_count() == 1


# 每條連線在同一個 process 裡用掉兩個 fd（client 端＋server 端），先確認上限夠用
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
N_IDLE = 500
if soft < 2 * N_IDLE + 50:
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(4096, hard), hard))
    except (ValueError, OSError):
        N_IDLE = max(10, soft // 2 - 50)
asyncio.run(main())
```

```text
keep-alive 兩個請求： 2 個 200
9 KB header： HTTP/1.1 431 Request Header Fields Too Large
header 送一半：0.5 秒後收到 HTTP/1.1 408 Request Timeout
500 條連線還沒送 header 時：正常請求 0.4 ms 拿到 200；task 501 個、OS thread 1 條
```

前三行和 40.3 節的 iterative 版本做一樣的測試，結果相同：pipelined 的兩個請求都拿到 200、9 KB 的 header 被 `StreamReader` 的 limit 擋下回 431、header 送一半在 0.5 秒時收到 408。程式碼卻和阻塞式的版本幾乎一樣好讀，期限也是用「整段的總期限」而不是每次讀取的逾時。第 4 行是 C10K 的縮影：500 條連線同時停在「等 header」的狀態，一條正常請求仍在 1 毫秒內完成；server 端有 501 個 Task，但 OS thread 只有 1 條。每個 Task 的成本是一個 Python 物件加上它暫停時的 frame，通常只有幾 KB。

程式開頭有一段處理 fd 上限：這個測試在同一個 process 裡同時開了 client 與 server 兩端，每條連線用掉兩個 fd，所以先確認 soft limit 足夠，不夠就在 hard limit 允許的範圍內調高。這也是寫壓測工具時常見的坑：壓測端本身也會先撞到 fd 上限。

asyncio 繼承了 event loop 的全部弱點：handler 裡只要有一個同步的阻塞呼叫（`time.sleep()`、`requests.get()`、同步的資料庫 driver），整個 loop 就停住，所有連線一起變慢。需要呼叫同步函式時要用 `await asyncio.to_thread(...)` 交給 thread pool。uvicorn 就是一個建立在 asyncio（可選用基於 libuv 的 uvloop 取代預設 loop）上的 server，它的 HTTP 解析與本章的思路相同，只是更完整、更快，第 42 章會從 ASGI 的角度拆解它。

## 40.10 動手做：同一組 client 量測五個版本

現在把五個並行模型放在同一個測試裡比較。為了讓整段程式能在一個區塊裡放下，這裡的五個 server 共用一個精簡的解析函式，錯誤處理也簡化成「直接關閉」；功能完整的版本分別是 40.3、40.8、40.9 節的程式。負載固定為兩組：

- **正常負載**：40 個 client 同時連線，每個在同一條 keep-alive 連線上連續送 5 個心跳（共 200 個請求），最後一個帶 `Connection: close`。
- **加上慢速 client**：先開 6 條「header 送一半就停」的連線，再跑同樣的 40 個 client。header 期限是 0.3 秒。

量測每個請求從送出到收齊回應的時間（p50 與 p99），整組的總時間，以及期間 server 端的 thread 數峰值。

```python
import asyncio
import queue
import selectors
import socket
import statistics
import threading
import time

MAX_HEADER, MAX_BODY = 8 * 1024, 64 * 1024
HEADER_TIMEOUT = BODY_TIMEOUT = IDLE_TIMEOUT = 0.3
OK = b"HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\n{\"online\": 1}"


def parse_head(head):
    """共用的嚴格解析：回傳 (keep_alive, body 長度)；不合法就丟 ValueError（簡化成一律回 400）。"""
    lines = head.decode("latin-1").split("\r\n")
    method, path, version = lines[0].split(" ")
    headers = dict((n.lower(), v.strip()) for n, _, v in (l.partition(":") for l in lines[1:]))
    n = int(headers.get("content-length", "0"))
    if "transfer-encoding" in headers or n > MAX_BODY or version not in ("HTTP/1.1", "HTTP/1.0"):
        raise ValueError
    return headers.get("connection", "").lower() != "close", n


# ---------- 三個阻塞式版本共用的連線處理 ----------
def handle_blocking(conn):
    buf, first = b"", True
    with conn:
        while True:
            deadline = time.monotonic() + (HEADER_TIMEOUT if first else IDLE_TIMEOUT)
            while b"\r\n\r\n" not in buf:
                if len(buf) > MAX_HEADER or (left := deadline - time.monotonic()) <= 0:
                    return                       # 太大或逾時：關閉（完整版會先回 431／408）
                conn.settimeout(left)
                try:
                    chunk = conn.recv(65536)
                except OSError:
                    return
                if not chunk:
                    return
                if not buf:
                    deadline = time.monotonic() + HEADER_TIMEOUT   # 第一個 byte 到了，開始算 header 期限
                buf += chunk
            first = False
            head, buf = buf.split(b"\r\n\r\n", 1)
            try:
                keep, n = parse_head(head)
            except ValueError:
                return
            buf = buf[n:]                        # 這組 client 不送 body；完整版見 40.3 節
            conn.sendall(OK)
            if not keep:
                return


def run_iterative(listener, stop):
    while not stop.is_set():
        handle_blocking(listener.accept()[0])


def run_threads(listener, stop):
    while not stop.is_set():
        conn, _ = listener.accept()
        threading.Thread(target=handle_blocking, args=(conn,), name="srv-conn", daemon=True).start()


def run_pool(listener, stop, size=4):
    jobs = queue.Queue()

    def worker():
        while (conn := jobs.get()) is not None:
            handle_blocking(conn)

    workers = [threading.Thread(target=worker, name="srv-worker") for _ in range(size)]
    for w in workers:
        w.start()
    while not stop.is_set():
        jobs.put(listener.accept()[0])
    for w in workers:
        jobs.put(None)                           # 每個 worker 一個結束訊號
    for w in workers:
        w.join()


def run_selectors(listener, stop):
    sel = selectors.DefaultSelector()
    listener.setblocking(False)
    sel.register(listener, selectors.EVENT_READ)
    conns = {}                                   # sock -> [inbuf, outbuf, deadline, keep]

    def close(s):
        sel.unregister(s)
        conns.pop(s)
        s.close()

    while not stop.is_set():
        for key, mask in sel.select(timeout=0.02):
            s = key.fileobj
            if s is listener:
                conn = listener.accept()[0]
                conn.setblocking(False)
                conns[conn] = [b"", b"", time.monotonic() + HEADER_TIMEOUT, True]
                sel.register(conn, selectors.EVENT_READ)
                continue
            st = conns[s]
            if mask & selectors.EVENT_READ:
                data = s.recv(65536)
                if not data:
                    close(s)
                    continue
                if not st[0]:
                    st[2] = time.monotonic() + HEADER_TIMEOUT
                st[0] += data
                try:
                    while b"\r\n\r\n" in st[0] and st[3]:   # 一次 recv 可能帶來多個請求
                        head, st[0] = st[0].split(b"\r\n\r\n", 1)
                        st[3], n = parse_head(head)
                        st[0], st[1] = st[0][n:], st[1] + OK
                except ValueError:
                    st[0] = b"x" * (MAX_HEADER + 1)      # 解析失敗：走下面的關閉路徑
                if len(st[0]) > MAX_HEADER:
                    close(s)
                    continue
            if st[1]:
                try:
                    st[1] = st[1][s.send(st[1]):]    # partial write：沒送完的留在 outbuf
                except BlockingIOError:
                    pass
                st[2] = time.monotonic() + IDLE_TIMEOUT
            if not st[1] and not st[3]:
                close(s)
                continue
            sel.modify(s, selectors.EVENT_READ | (selectors.EVENT_WRITE if st[1] else 0))
        now = time.monotonic()
        for s in [s for s, st in conns.items() if now > st[2]]:
            close(s)                             # header、閒置期限到了：關閉
    for s in list(conns):
        close(s)
    sel.close()


def run_asyncio(listener, stop):
    async def handle(reader, writer):
        try:
            timeout = HEADER_TIMEOUT
            while True:
                async with asyncio.timeout(timeout):
                    head = await reader.readuntil(b"\r\n\r\n")
                keep, n = parse_head(head[:-4])
                await reader.readexactly(n)
                writer.write(OK)
                await writer.drain()
                if not keep:
                    break
                timeout = IDLE_TIMEOUT + HEADER_TIMEOUT
        except (TimeoutError, ValueError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
            pass
        finally:
            writer.close()

    async def main():
        server = await asyncio.start_server(handle, sock=listener, limit=MAX_HEADER)
        while not stop.is_set():
            await asyncio.sleep(0.02)
        server.close()

    asyncio.run(main())


# ---------- 同一組 client ----------
def normal_client(addr, latencies, requests=5):
    with socket.create_connection(addr, timeout=5) as s:
        for i in range(requests):
            last = i == requests - 1
            t = time.monotonic()
            s.sendall(b"GET /presence HTTP/1.1\r\nHost: rt.shengsheng.example\r\n"
                      + (b"Connection: close\r\n" if last else b"") + b"\r\n")
            got = b""
            while len(got) < len(OK):
                got += s.recv(65536)
            latencies.append((time.monotonic() - t) * 1000)


def bench(model, slow):
    listener = socket.create_server(("127.0.0.1", 0), backlog=128)
    addr = listener.getsockname()
    stop = threading.Event()
    server = threading.Thread(target=model, args=(listener, stop), name="srv-main")
    server.start()
    hogs = [socket.create_connection(addr) for _ in range(slow)]
    for h in hogs:
        h.sendall(b"GET /presence HTTP/1.1\r\nHost:")       # 慢速 client：header 送一半就停
    time.sleep(0.02)
    latencies, peak = [], 0
    clients = [threading.Thread(target=normal_client, args=(addr, latencies)) for _ in range(40)]
    start = time.monotonic()
    for c in clients:
        c.start()
    while any(c.is_alive() for c in clients):
        peak = max(peak, sum(t.name.startswith("srv") for t in threading.enumerate()))
        time.sleep(0.002)
    total = (time.monotonic() - start) * 1000
    for h in hogs:
        h.close()
    stop.set()
    socket.create_connection(addr).close()      # 叫醒阻塞在 accept() 的 server，讓它看到 stop
    server.join()
    listener.close()
    q = statistics.quantiles(latencies, n=100)
    return total, q[49], q[98], peak, len(latencies)


models = [("iterative", run_iterative), ("thread-per-conn", run_threads), ("thread pool(4)", run_pool),
          ("selectors", run_selectors), ("asyncio", run_asyncio)]
print(f"{'model':<16}{'slow':>6}{'total ms':>10}{'p50 ms':>9}{'p99 ms':>9}{'threads':>9}")
results = {}
for slow in (0, 6):
    for label, model in models:
        total, p50, p99, peak, n = bench(model, slow)
        results[label, slow] = (total, p99)
        print(f"{label:<16}{slow:>6}{total:>10.0f}{p50:>9.1f}{p99:>9.1f}{peak:>9}")
        assert n == 200

assert results["iterative", 6][0] > 6 * HEADER_TIMEOUT * 1000 * 0.8     # 6 個慢 client 輪流擋住
assert results["thread pool(4)", 6][1] > HEADER_TIMEOUT * 1000 * 0.5     # 4 個 worker 全被佔住
assert results["selectors", 6][1] < 100 and results["asyncio", 6][1] < 100
```

```text
model             slow  total ms   p50 ms   p99 ms  threads
iterative            0        19      0.1     11.2        1
thread-per-conn      0        20      1.1      6.2       14
thread pool(4)       0        16      0.2      7.3        5
selectors            0        11      0.8      3.5        1
asyncio              0        13      1.3      4.3        1
iterative            6      1820      0.2   1815.3        1
thread-per-conn      6        29      2.5     10.0       36
thread pool(4)       6       300      0.2    294.4        5
selectors            6        32      3.5      9.2        1
asyncio              6        25      2.6      6.7        1
```

先提醒：這些數字是在一台 macOS 筆電的 loopback 上、client 與 server 在同一個 process 裡量到的，絕對值會因機器、作業系統與當下負載而不同，每次執行也會有幾毫秒的差異；值得看的是**各版本之間的模式**，而不是單一數字。下表把模式整理出來：

| 版本 | 正常負載 | 加上 6 個慢速 client | thread 數 | 讀法 |
|---|---|---|---|---|
| iterative | p50 很低，p99 明顯較高 | 總時間約 1.8 秒，p99 約 1.8 秒 | 1 | 慢速 client 依序擋住所有人：6 × 0.3 秒 |
| thread-per-connection | 正常 | 幾乎不受影響 | 隨連線數增加（十幾到數十條） | 用資源換隔離 |
| thread pool（4） | 正常 | p99 約 0.3 秒 | 固定 5 | 慢速 client 佔住 worker 直到期限 |
| selectors | 正常 | 幾乎不受影響 | 1 | 慢速 client 只佔一個 fd |
| asyncio | 正常 | 幾乎不受影響 | 1 | 同上，程式碼更好讀 |

逐列讀。iterative 在正常負載下的 p50 是全場最低（每個請求只有一條連線在競爭），但 p99 已經高出一截：每個 client 的**第一個**請求都要等前面的連線服務完，這 40 個請求佔了 200 個請求的 20%，正好落在 p99。加上慢速 client 之後，6 條慢速連線排在最前面，每條佔滿 0.3 秒的期限，於是總時間約等於 6 × 0.3 ＝ 1.8 秒；p50 依然漂亮，p99 卻是 1.8 秒。這就是故事開頭那份報表的樣子：**只看平均或 p50，永遠看不到排隊的人**。

thread pool 的 4 個 worker 被 6 個慢速 client 佔滿，前 4 個在 0.3 秒時逾時釋放，worker 才開始服務正常請求，所以 p99 約等於一個 header 期限。如果沒有期限，這個 pool 會永遠卡住。thread-per-connection、selectors 與 asyncio 在兩種負載下都很穩定，差別在成本：thread-per-connection 的 thread 數峰值隨同時存在的連線數變動（每次執行不同），event loop 的兩個版本從頭到尾只有 1 條 thread。

你可能注意到，在這個小測試裡 event loop 版本的 p50 不一定比 thread pool 好。原因是 40 個 client thread 和 server 搶同一個 GIL，而純 Python 的 event loop 每個事件都要跑不少 bytecode。event loop 的優勢不在「單一請求更快」，而在**連線數上升時成本不會跟著上升**，以及**慢速或閒置的連線幾乎免費**。要驗證這一點，可以把慢速 client 從 6 條加到 600 條（動手練習 1）：thread pool 會更糟，thread-per-connection 的 thread 數會衝到 600 以上，event loop 版本的 p99 則幾乎不變。

## 40.11 在工作上怎麼用

檢討會後，presence 服務沒有用小晴的手寫 server 上線，而是依照這次的理解重新設計。阿德說：「自己寫一次是為了看懂別人的設定，不是為了取代它們。」下面依角色整理。

**後端工程師：先知道你的 server 是哪一種模型。** 部署 Python 服務時，第一個問題是「這個 worker 用什麼方式等待」：

```text
 學生瀏覽器 ──► LB 203.0.113.80 ──► nginx 10.20.3.11（event loop，每個 worker 處理上千條連線）
                                      │  ① 接住慢速 client：client_header_timeout、client_body_timeout
                                      │  ② 把整個請求收完、緩衝好才轉送（proxy_request_buffering）
                                      │  ③ 對上游重用少量 keep-alive 連線
                                      ▼
                     ┌─────────────────────────────┬──────────────────────────────┐
                     │ gunicorn（Flask，WSGI）      │ uvicorn／gunicorn ASGI worker │
                     │ 10.20.3.21:8000              │ 即時服務、presence            │
                     │ sync：pre-fork，一次一個請求 │ asyncio event loop            │
                     │ gthread：pre-fork＋thread pool│ 長連線、WebSocket、心跳        │
                     └─────────────────────────────┴──────────────────────────────┘
```

這張圖是聲聲 Live 的分工。① nginx 是 event loop 架構，用一個 fd 和幾 KB 的 buffer 就能照顧一條慢速連線，而且有完整的 header／body 期限，所以讓它站在最前面面對 internet。② 預設情況下 nginx 會把請求 body 收完才轉給上游，所以 gunicorn 的 worker 只會看到「完整、快速到達」的請求，sync worker 一次一條的弱點因此被遮住。③ nginx 到上游的連線是少數幾條長連線，上游 server 不用面對成千上萬條 client 連線。presence 這種「大量閒置連線、每個請求很輕」的服務，則適合 asyncio 模型（uvicorn 或 gunicorn 的 ASGI worker，第 42、43 章）。

選 worker 類型時可以用這張檢查表：請求處理時間短、主要是 CPU 或同步資料庫呼叫，用 gunicorn sync 或 gthread，worker 數依 CPU 核心數估算（第 43 章）；有長連線、WebSocket、SSE 或大量閒置 keep-alive，用 asyncio 模型，並確保 handler 裡沒有同步的阻塞呼叫；不管哪一種，前面都放 nginx 或 LB 擋住慢速 client。

**SRE：用 accept queue、fd 與 thread 數判斷是哪一層撐不住。** 故事裡的兩次事故，都能用幾個指令在一分鐘內看出來：

```bash
ss -ltn 'sport = :8090'                        # Recv-Q 接近 Send-Q：應用程式 accept 太慢（第 10 章）
nstat -az TcpExtListenOverflows                # 持續增加：accept queue 滿，SYN 被丟
ls /proc/<pid>/fd | wc -l                      # fd 用量
grep 'open files' /proc/<pid>/limits           # fd 上限（systemd 服務看 LimitNOFILE）
ls /proc/<pid>/task | wc -l                    # thread 數：隨連線數上升就是 thread-per-connection
ss -tn state established '( sport = :8090 )' | wc -l   # 目前連線數
ss -tni state established '( sport = :8090 )' | head   # 看個別連線的 Recv-Q／Send-Q 與 bytes_received
```

判斷順序是：`Recv-Q` 長期不為 0，代表 server 的 accept 迴圈跟不上，原因可能是 iterative 被一條連線卡住、thread pool 滿了、或 fd 用完導致 `accept()` 失敗；thread 數與連線數同步上升，就是 thread-per-connection 模型；連線數很大但每條的 bytes_received 很少、存活很久，就是慢速 client 或閒置 keep-alive。把連線數、fd 用量與 thread 數放進監控，並設定在 fd 上限的 70% 時告警。

**資安工程師：期限與上限是 DoS 防線。** Rita 的審查清單裡，每個面對 client 的 server 都要回答四個問題：header 有沒有**總期限**（不只是每次讀取的逾時）？body 有沒有大小上限，而且是在讀之前就依 `Content-Length` 拒絕？連線數有沒有上限，滿了是排隊還是拒絕？單一來源 IP 能開幾條連線？最後一項通常在 LB 或 nginx 用 `limit_conn` 之類的機制處理。慢速攻擊的成本極低（每條連線只要偶爾送一個 byte），所以防線必須放在「每條連線最便宜」的那一層，也就是 event loop 架構的 proxy，而不是每條連線一條 thread 的應用程式 server。

**影音與即時服務：長連線讓 C10K 成為日常。** Joe 負責的 WebSocket 教室與觀看端，每個學生一條長時間存在的連線，晚上八點同時在線的連線數就是同時在線的人數。這類服務的容量規劃要以「連線數」而不只是「每秒請求數」為單位：每條連線的記憶體（buffer、Task、應用狀態）乘以尖峰連線數，再加上 fd 上限與 LB 的連線上限。心跳間隔則要兼顧兩邊：短於路徑上最短的閒置逾時（第 11 章），但不要短到讓上萬條連線的心跳本身成為負載。

## 40.12 常見錯誤與除錯

下表是自己寫 server、或設定現成 server 時最常見的錯誤。很多問題在小流量時完全不會出現，一到尖峰或遇到不守規矩的 client 才爆發。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| p50 很低、p99 等於逾時上限；client connect 很快但回應很慢 | iterative 或 sync worker 被 keep-alive 連線卡住，其他連線在 accept queue 排隊 | `ss -ltn` 的 Recv-Q 不為 0；連線數遠多於 worker 數 | 換成並行模型；sync worker 前面放 nginx；回應帶 `Connection: close` |
| 少量連線就讓服務停擺，CPU 卻很低 | header／body 沒有總期限，慢速 client 佔住 thread 或 worker | thread dump 看到大量 thread 停在 `recv()`；`ss -tni` 看到連線存活很久但 bytes 很少 | 用 deadline 實作總期限；前面放 nginx 設 `client_header_timeout` |
| `OSError: [Errno 24] Too many open files` | fd 用完：連線數超過 `RLIMIT_NOFILE`，或有 fd 洩漏 | `/proc/<pid>/fd` 數量對照 `/proc/<pid>/limits`；看 CLOSE_WAIT 數量（第 10 章） | 調高 `LimitNOFILE`；設連線數上限並在滿時暫停 accept；修洩漏 |
| event loop 服務 CPU 100%，但沒有在處理請求 | 永遠監看 `EVENT_WRITE`，或 `EMFILE` 後 listener 一直可讀 | `strace -c`／`dtruss` 看到大量 select 與失敗的 accept；py-spy 看迴圈熱點 | 只在 outbuf 非空時監看可寫；`EMFILE` 時暫停 accept 並告警 |
| asyncio 服務所有連線一起變慢，週期性卡頓 | handler 裡有同步阻塞呼叫，卡住整個 event loop | 開 asyncio debug 模式看 slow callback 警告；py-spy 看卡在哪個同步函式 | 改用 async driver；同步呼叫用 `asyncio.to_thread()` |
| 大回應被截斷，或 client 收到不完整的資料 | 非阻塞 `send()` 的回傳值被忽略，以為一次送完 | 比對送出 bytes 與 `Content-Length`；log 每次 send 的回傳值 | 把未送完的部分留在 outbuf，等可寫時再送；阻塞模式用 `sendall()` |
| 偶發 JSON 解析失敗，或兩個請求黏在一起 | 假設一次 `recv()` 就是一個完整請求，沒有處理 partial read 與 pipelining | 用 `nc` 慢慢送一個請求，或一次送兩個請求測試 | 每條連線維護 inbuf，依 `\r\n\r\n` 與 Content-Length 切邊界 |
| client 收到 `ECONNRESET`，看不到 server 的 413／431 | 回錯誤後直接 close，接收 buffer 還有資料，核心送 RST | tcpdump 看到錯誤回應後緊跟 RST | lingering close：`shutdown(SHUT_WR)` 後短暫讀掉殘留資料再 close |
| 記憶體隨某些連線持續上升 | 沒有 backpressure：client 不讀回應卻一直送請求，outbuf 無限增長 | 依連線列出 outbuf 大小；`ss -tm` 看 socket 記憶體 | 設 high-water mark，超過就暫停讀取；設寫入期限 |

這張表的前兩列最常被誤判成「server 太慢」，於是有人去加 CPU 或加 worker。判斷的關鍵是 CPU 使用率：CPU 很低而延遲很高，問題幾乎都在「等待」的設計，也就是並行模型與期限，而不是運算能力。

## 40.13 動手練習

1. **放大慢速 client**（延伸本章程式）。把 40.10 節的慢速 client 從 6 條改成 200 條，header 期限維持 0.3 秒，比較五個版本的 p99 與 thread 數。答案要點：iterative 的總時間約為 200 × 0.3 秒，必須縮小 client 數或期限才跑得完；thread pool 的 p99 約為 ⌈200 ÷ 4⌉ × 0.3 秒；thread-per-connection 的 thread 數超過 240；selectors 與 asyncio 的 p99 幾乎不變。注意同一個 process 的 fd 用量會加倍，必要時先調高 soft limit。

2. **把期限換回每次讀取的逾時**（延伸本章程式）。修改 40.3 節的 `recv_into()`，讓它每次都用固定的 `settimeout(0.3)`，不再計算剩餘時間，再跑一次「每 0.1 秒滴一個 byte」的測試。答案要點：server 不再回 408，而是一直等到 client 送完整個 header（約 3.4 秒），證明間隔型逾時擋不住慢速 client。接著把滴的間隔改成 0.35 秒，觀察間隔型逾時才會觸發。

3. **用真實工具觀察 accept queue**（真實工具）。在 Linux 上執行 `python3 -m http.server 8765 --bind 127.0.0.1`（它是 thread 模型，但預設 backlog 很小），另一個終端用 `nc 127.0.0.1 8765` 開 10 條連線但不送任何東西，再用 `ss -ltn 'sport = :8765'` 與 `ss -tn state established '( sport = :8765 )'` 觀察。答案要點：連線全部 ESTABLISHED，server 為每條連線開了一條 thread 在等 header，而且因為 `http.server` 沒有預設的讀取逾時，這些連線會一直存在；用 `ls /proc/<pid>/task | wc -l` 驗證 thread 數。

4. **在 Linux 上重現 EMFILE 空轉**（延伸本章程式）。在 Linux 上執行 40.7 節的程式，記錄 `EMFILE` 的次數與上限恢復後 accept queue 剩下的連線數，和本書的 macOS 輸出比較。再加一個「預留 fd」：程式開頭先開一個 `/dev/null`，`EMFILE` 時關掉它、accept 一條連線、回 503 後關閉、再把 `/dev/null` 開回來。答案要點：Linux 上 `EMFILE` 次數會多出好幾個數量級，佇列裡的 6 條連線仍在；加上預留 fd 後，排隊的 client 會收到明確的 503，而不是無限等待。

5. **讓 event loop 被一個同步呼叫卡住**（延伸本章程式）。在 40.9 節 asyncio 版本的 handler 裡加上 `time.sleep(0.2)`，量測 20 個並行請求的總時間；再改成 `await asyncio.sleep(0.2)` 與 `await asyncio.to_thread(time.sleep, 0.2)` 比較。答案要點：`time.sleep` 讓請求被逐一處理，總時間約 20 × 0.2 秒；另外兩種寫法的總時間約 0.2 秒，因為等待時 event loop 可以服務其他連線。

6. **讀 gunicorn 與 nginx 的設定**（真實工具）。用 `gunicorn --help` 找出 `--worker-class`、`--threads`、`--worker-connections`、`--keep-alive`、`--backlog`、`--limit-request-line` 的說明，再對照 `nginx -T` 輸出中的 `worker_connections`、`client_header_timeout`、`keepalive_timeout`、`client_max_body_size`，把它們填進 40.2 節的限制表與 40.7 節的模型表。答案要點：每一個設定都能對應到本章 server 的某一行程式；如果某一層沒有對應的期限或上限，那一層就是慢速 client 的突破口。

## 本章重點整理

- HTTP server 的核心工作是從 byte stream 切出請求的邊界、呼叫應用程式、寫出邊界明確的回應；HTTP/1.1 的 keep-alive 讓一條連線在回應之後回到閒置，而不是關閉。
- 一條連線在 server 端依序經歷「讀 header、讀 body、處理、寫回應、閒置」幾段等待，每一段都必須有期限，否則就是讓 client 決定 server 的資源何時釋放。
- 期限必須是總期限（deadline），不能只是每次 `recv()` 的逾時；每次滴一個 byte 的慢速 client 可以無限期繞過間隔型逾時。
- 大小上限要在讀取之前執行：header 超過上限回 431，`Content-Length` 超過上限直接回 413，不必先收下 body；回錯誤時用 lingering close，避免 RST 蓋掉回應。
- iterative server 一次只服務一條連線，其他連線完成交握後在第 10 章的 accept queue 裡排隊；connect 很快、回應很慢，p50 好看、p99 等於別人的 keep-alive 時間。
- thread-per-connection 用資源換隔離，thread 數跟著連線數走；thread pool 讓資源有上限，但慢速 client 能佔滿所有 worker，佇列成了第二個 accept queue。
- pre-fork 讓多個 worker process 從同一個 listening socket accept，arbiter 監看並重生死掉的 worker，提供多核與故障隔離；`SO_REUSEPORT` 讓每個 worker 有自己的 accept queue。
- C10K 的關鍵觀察是「連線很多，活躍的很少」；event loop 用非阻塞 socket 與 epoll／kqueue，讓一條 thread 照顧大量連線，每條閒置連線只佔一個 fd 和少量 buffer。
- 每條連線都要一個 fd；fd 用完時 `accept()` 得到 `EMFILE`，Linux 上連線仍留在佇列、event loop 可能空轉，macOS 上排隊的連線會被關閉。server 應設低於 fd 上限的連線數上限，滿了就暫停 accept。
- 非阻塞 I/O 必須自己處理 partial read（每條連線一個 inbuf）與 partial write（未送完的留在 outbuf，只在 outbuf 非空時監看可寫），並用 high-water mark 做 backpressure。
- asyncio 把同一個 event loop 包成 coroutine，`readuntil` 的 limit、`asyncio.timeout_at` 與 `drain()` 分別對應大小上限、總期限與 backpressure；任何同步阻塞呼叫都會卡住整個 loop。
- 量測並行模型要同時看 p50、p99 與資源用量，並加入慢速 client；同樣的數字在不同機器上會不同，要比較的是模型之間的模式。
- 生產環境的分工是：event loop 架構的 nginx 面對 internet、擋住慢速 client 並緩衝請求，gunicorn 的 sync／gthread worker 或 asyncio 架構的 uvicorn 在後面處理應用程式。

## 延伸問答

> [!question]- Q1. 為什麼 `socket.settimeout(5)` 擋不住慢速 client？要怎麼改？
> socket 的 timeout 是「每一次阻塞操作」各自計算的：每次呼叫 `recv()` 時重新開始計時，只要在 5 秒內收到任何一個 byte，這次 `recv()` 就成功返回，下一次 `recv()` 又重新給 5 秒。一個每 4.9 秒送 1 byte 的 client，送完 1 KB 的 header 可以花上一個多小時，整段期間都佔著一條 thread 或一個 worker，而每一次讀取都沒有逾時。
>
> 正確的做法是**總期限**：開始讀 header 時記下 `deadline = now + 5`，每次 `recv()` 之前把 timeout 設成 `deadline - now`，剩餘時間小於等於 0 就回 408 並關閉。asyncio 裡對應的寫法是把整段 `readuntil()` 包在 `asyncio.timeout_at(deadline)` 裡。nginx 的 `client_header_timeout` 也是針對整個 header；但它的 `client_body_timeout` 與 `send_timeout` 是兩次讀寫之間的間隔，所以大檔案上傳的防線還要搭配 body 大小上限與連線數限制。

> [!question]- Q2. 手算：thread pool 有 8 個 worker，header 期限 10 秒。攻擊者開 40 條「header 送一半就停」的連線，正常使用者的請求最久要等多久？
> 40 條慢速連線依序進入佇列。前 8 條立刻佔住 8 個 worker，10 秒後因期限到期被關閉；接下來 8 條再佔 10 秒，如此重複。40 ÷ 8 ＝ 5 輪，所以在最壞的情況下，排在慢速連線之後的正常請求要等約 5 × 10 ＝ 50 秒才輪得到 worker，這遠遠超過一般 client 的逾時，對使用者來說服務等於掛了。
>
> 這個計算說明三件事：第一，期限是必要的，沒有期限這個 pool 會永久停擺；第二，期限只把「永遠」變成「很久」，攻擊者只要持續開新連線就能維持效果；第三，真正的解法是不讓慢速連線佔用昂貴的 worker，也就是前面放一層 event loop 架構的 proxy（nginx），把請求完整收好才交給 pool，並在 proxy 層限制單一來源的連線數。

> [!question]- Q3. 面試題：說明 select、poll、epoll 的差別，以及它們和 C10K 的關係。
> 三者都回答同一個問題：「這些 fd 裡，哪些現在可以讀或寫？」select 用固定大小的 bitmap 表示 fd 集合，fd 編號受 `FD_SETSIZE`（常見 1024）限制，每次呼叫都要把整份集合從使用者空間複製到核心、核心逐一檢查、再複製回來。poll 改用陣列，沒有 1024 的限制，但每次呼叫仍要傳整份清單、逐一檢查。兩者的成本都和「監看的 fd 總數」成正比。
>
> epoll 把監看清單存在核心裡（`epoll_ctl` 增刪），`epoll_wait` 只回傳準備好的 fd，成本和「活躍的 fd 數」成正比。C10K 的場景是一萬條連線、任何時刻只有少數活躍，select／poll 每次都要為一萬個 fd 付出成本，epoll 只為活躍的少數付出，這就是 event loop 能撐起大量連線的原因。kqueue 是 BSD／macOS 上的對應機制。加分點可以提到 level-triggered 與 edge-triggered 的差別，以及 edge-triggered 必須讀到 `EAGAIN` 為止。

> [!question]- Q4. 你在 production 看到 presence 服務的 CPU 使用率 100%，請求卻幾乎都逾時，log 裡有零星的 `Too many open files`。可能是什麼？
> 這個組合很像 event loop 在空轉。`EMFILE` 代表 fd 已經用完；在 Linux 上，`accept()` 因 `EMFILE` 失敗時，連線不會離開 accept queue，所以 listening socket 一直是「可讀」的，event loop 每一輪都被叫醒、嘗試 accept、失敗，再被叫醒，CPU 被吃滿，卻沒有任何請求得到處理。另一個常見的空轉原因是對所有連線一直監看 `EVENT_WRITE`，因為正常的 socket 幾乎永遠可寫。
>
> 確認方法是看 fd 用量是否接近上限（`/proc/<pid>/fd` 對照 limits）、用 `strace -c` 或 py-spy 看迴圈是否大量呼叫失敗的 accept。修法分三層：先找出 fd 為什麼用完（連線數暴增、CLOSE_WAIT 洩漏、檔案沒關）；server 設定低於 fd 上限的連線數上限，滿了就暫停監看 listener；`EMFILE` 時也暫停一小段時間並告警，而不是立刻重試。最後再依容量調高 `LimitNOFILE`。

> [!question]- Q5. 設計取捨：presence 服務要支援晚上八點三萬條同時在線的 keep-alive 連線，每 15 秒一次心跳。你會選哪種並行模型？怎麼估算資源？
> 先估負載：三萬條連線、每 15 秒一個請求，平均每秒約 2,000 個請求，每個請求只是更新記憶體或 Redis 裡的一筆資料，工作量很輕；但同時存在的連線數是三萬。這是典型的「連線很多、活躍很少」，thread-per-connection 需要三萬條 thread，thread pool 會被閒置的 keep-alive 佔住，都不適合；event loop 模型（asyncio 上的 uvicorn 或 gunicorn ASGI worker）每條閒置連線只要一個 fd 與幾 KB 的記憶體。
>
> 資源估算：fd 至少三萬再加上餘裕，`LimitNOFILE` 設 65536 以上；記憶體以每條連線數 KB 到數十 KB 估，三萬條約數百 MB 等級，要實測；為了用到多核，開幾個 worker process（例如每顆核心一個），各自跑一個 event loop，連線由核心或 `SO_REUSEPORT` 分散。名單本身放在 Redis，避免各 worker 各有一份。前面的 LB 與 nginx 也要檢查連線上限與閒置逾時，心跳間隔要短於它們的閒置逾時。最後用本章的方法加上慢速 client 做壓測，看 p99 而不是平均。

> [!question]- Q6. 看輸出找原因：小晴的 event loop server 對小請求一切正常，但下載 2 MB 錄影檔時，client 有時只收到幾百 KB 就停住，server 的 log 沒有任何錯誤。可能是什麼？
> 最可能的原因是忽略了非阻塞 `send()` 的回傳值。非阻塞模式下，`send()` 只把資料放進核心的送出 buffer，放得下多少就回傳多少，2 MB 的回應第一次可能只送出幾百 KB；如果程式以為一次就送完、把剩下的資料丟掉，client 收到的 bytes 會少於 `Content-Length`，於是一直等待剩下的部分，直到自己的逾時。server 端沒有任何例外，所以 log 一片安靜。小請求不會出問題，是因為幾 KB 的回應一定放得進 buffer。
>
> 修法是每條連線維護 outbuf：`send()` 送出多少就從 outbuf 移除多少，沒送完就註冊 `EVENT_WRITE`，等 socket 可寫時繼續送，送完再取消監看可寫。另一個可能的成因是 outbuf 正確、但只在收到新資料時才嘗試送出，沒有監看可寫事件，結果 client 不再送東西時，剩下的回應永遠沒有機會送出。兩種情況都可以用 tcpdump 確認：server 在某個時間點之後就不再送資料，而 client 的 receive window 並沒有被塞滿。

> [!question]- Q7. 概念辨析：gunicorn 的 sync worker 為什麼「一定要」放在 nginx 後面？uvicorn 前面還需要 nginx 嗎？
> sync worker 是 pre-fork 加上 iterative：每個 worker process 一次只處理一個請求，讀取期間沒有獨立的 header 期限。如果它直接面對 internet，一個慢速上傳或慢速 header 的 client 就能佔住一個 worker，幾條這樣的連線就能讓整個服務停擺，正好是本章 40.4 與 40.10 節的情境。nginx 是 event loop 架構，它以極低的成本接住慢速連線，套用 `client_header_timeout` 與 `client_body_timeout`，並且預設把請求完整收好才轉給上游，所以 sync worker 只會看到「完整、快速到達」的請求。
>
> uvicorn 是 event loop 架構，本身不怕大量閒置或慢速連線，所以「被慢速 client 拖垮」的理由弱很多。但實務上前面通常仍有 nginx 或 LB，理由換成別的：TLS 終結與憑證管理（第 19 章）、靜態檔案、統一的存取 log 與限流、多個後端服務的路由、以及 graceful deploy 時的連線排空（第 43 章）。所以答案是「不一定為了慢速 client，但通常還是需要」。

> [!question]- Q8. 手算與判斷：一台 Linux 主機上的服務 `listen(128)`，`net.core.somaxconn` 是 4096，`ulimit -n` 是 1024，服務是 thread-per-connection。尖峰時同時有 1,500 條連線要進來，會發生什麼？
> 先看 accept queue：實際上限是 min(128, 4096) ＝ 128，所以排隊的空間只有 128 條（Linux 上可容納 129 條）。再看 fd：process 的 soft limit 是 1024，扣掉 listening socket、log 檔、對資料庫的連線等，大約只能再 accept 一千條左右。thread-per-connection 會一路 accept，直到 fd 用完，第一千條左右之後 `accept()` 開始得到 `EMFILE`。
>
> 接下來，Linux 上 `EMFILE` 不會移除佇列中的連線，所以 accept queue 很快塞滿 129 條；之後新的 SYN 被丟棄，client 看到 connect 變慢或逾時（第 10 章）。已經被服務的一千條連線則擠在一千條 thread 裡，記憶體與排程成本上升。要撐住 1,500 條連線，至少要把 fd 上限調到數千以上、設定連線數上限讓溢出的部分排隊而不是觸發 `EMFILE`，並考慮把 backlog 調大以吸收瞬間尖峰；長期而言，大量同時連線的服務應改用 event loop 模型或放在 nginx 後面。

## 延伸閱讀

- Dan Kegel〈The C10K problem〉：整理同時服務一萬個 client 的各種 I/O 模型，event loop 架構的經典起點
- RFC 9112〈HTTP/1.1〉：訊息解析、body 長度判斷與連線管理（keep-alive、pipelining、關閉）
- RFC 9110〈HTTP Semantics〉與 RFC 6585〈Additional HTTP Status Codes〉：408、413、431 等 status code 的定義
- W. Richard Stevens、Bill Fenner、Andrew M. Rudoff《UNIX Network Programming, Volume 1》：I/O 模型、I/O multiplexing 與各種 server 設計方式的比較
- Python 官方文件：`socket`、`selectors`、`asyncio` 的 Streams 與 Transports and Protocols、`socketserver`
- Linux man-pages：epoll(7)、accept(2)、listen(2)、getrlimit(2)
- gunicorn 官方文件〈Design〉：arbiter 與 sync、gthread、非同步 worker 的設計說明
