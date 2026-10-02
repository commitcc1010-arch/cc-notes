---
chapter: 20
title: HTTP/1.1：請求與回應
part: 5
---

# 第 20 章　HTTP/1.1：請求與回應

> [!abstract] 本章地圖
> **核心問題**：HTTP/1.1 的請求與回應在一條 TCP 連線上到底長什麼樣？兩端怎麼知道一個訊息在哪裡結束、哪些請求可以安全重送？
>
> **你會學到**：
> - 逐 byte 讀懂請求行、狀態行、header 與 body，知道哪些寫法合法、哪些必須拒絕
> - 分辨 safe 與 idempotent 的 method，判斷「送出去但沒收到回應」時能不能自動重試
> - 依 status code 的家族判斷問題出在 client、server 還是中間的 proxy
> - 說明 Host header 為什麼存在、缺少或被偽造時會發生什麼，以及怎麼用允許清單防禦
> - 用 Content-Length 與 chunked 正確切出訊息邊界，並在同一條連線上重用 keep-alive
> - 解釋 request smuggling 的成因（兩個解析器對邊界意見不同）與防禦方式
> - 用 Python socket 手寫一個 HTTP/1.1 client，在 127.0.0.1 上驗證以上每一件事
>
> **前置知識**：第 1 章（URL 與請求的旅程）、第 3 章（curl 與 nc）、第 10 章（TCP 連線與關閉）、第 11 章（byte stream 與 framing）

## 20.1 故事：自己寫的探針卡了 75 秒

聲聲 Live 每次大改版，阿德都會要求一件事：上線前，先讓**合成監測**（synthetic monitoring，用程式定期假裝成使用者去打服務，在真人抱怨之前發現問題）跑起來。這次輪到小晴負責新的預約 API。需求很具體：每 10 秒從 VPC 裡的監測主機 10.20.3.30 打一次 `api.shengsheng.example`，而且刻意繞過 API LB（203.0.113.80）、直接連內部的 nginx 10.20.3.11，把 LB 之後的那一段（nginx 與 gunicorn 主機 10.20.3.21:8000）單獨量出來，分別記下連線、送出、等待第一個 byte、下載的時間，而且要重用同一條連線，模擬瀏覽器的行為。

小晴心想，HTTP 不就是送幾行文字嗎？為了能精確量到每一段時間，小晴決定直接用 `socket` 寫。第一版程式送出 `GET /api/classes/today HTTP/1.1`，然後用一個 `while True: recv()` 迴圈把回應讀完，讀到 `b""` 才停。程式一跑，第一個檢查就卡了整整 75 秒才結束，而且每一次都是 75 秒。小晴以為是 API 太慢，可是 gunicorn 的 log 顯示每個請求 30 毫秒就處理完了。

小晴改成讀到 `}` 就停，探針變快了。隔天早上，課表頁的檢查開始報「JSON 解析失敗」，回應內容的開頭多了一串看不懂的 `1f4\r\n`。小晴又加了一個「自動重試一次」的包裝，結果測試帳號一個晚上多出了 37 筆重複的測試預約，Rita 在對帳報表上看到後找了過來。最後，小晴為了讓解析器「更寬容」，打算接受任何看起來像 header 的行，Rita 在 code review 時直接擋下：「你這樣寫，和 nginx 對同一段 bytes 的理解不一樣，就是 request smuggling 的起點。」

```text
 監測主機 10.20.3.30                                   nginx 10.20.3.11     gunicorn 10.20.3.21:8000
   │ ① 送 GET，讀到 EOF 才停                              │                       │
   │─────────────────────────────────────────────────────►│──────────────────────►│ 30 ms 處理完
   │◄──────── 回應（Content-Length: 35） ─────────────────│◄──────────────────────│
   │   …連線保持開著（keep-alive）……                     │ keepalive_timeout 75s │
   │   recv() 一直等不到 EOF                             │                       │
   │◄──────────────── 75 秒後 nginx 送 FIN ──────────────│                       │
   │ ② 課表 API 改用 chunked：body 開頭多出 "1f4\r\n"                                         │
   │ ③ POST 沒收到回應就重送：同一筆預約寫了兩次                                              │
   │ ④ 寬鬆的 header 解析：和 nginx 對訊息邊界的判斷不同                                       │
```

這張圖把四個問題排成時間順序，它們其實是同一個問題的四個面向。① 是**訊息邊界**：HTTP/1.1 預設保持連線，server 回完一個回應並不會關閉 TCP，client 必須自己依 `Content-Length` 判斷回應在哪裡結束；等 EOF 的程式只能等到 nginx 的 `keepalive_timeout`（預設 75 秒）把閒置連線關掉；如果探針經過 API LB，先關掉閒置連線的會是 LB 的 60 秒 idle timeout，卡住的時間就變成 60 秒（整條 timeout 鏈見第 43 章）。② 是同一件事的另一種格式：課表 API 是邊查邊送的串流回應，事先不知道總長度，於是用 **chunked** 編碼，`1f4` 是十六進位的 chunk 長度（500 bytes），不是 body 的一部分。③ 是 **method 語意**：POST 不是 idempotent，送出後沒收到回應，不代表 server 沒處理。④ 是**解析一致性**：同一段 bytes，如果 proxy 與後端對 body 長度的理解不同，攻擊者就能把一個請求藏進另一個請求裡。

阿德聽完沒有責怪，反而說這是學 HTTP/1.1 最好的方式：「把你踩過的四個坑對照規格走一遍，這一章就學完了。」本章就從一個請求在線路上的 bytes 開始，依序講 method、status code、Host、訊息邊界、keep-alive 與 smuggling，最後在動手做裡把小晴的探針重寫成正確的版本。

## 20.2 HTTP/1.1 的全貌：在 byte stream 上講話

**HTTP**（HyperText Transfer Protocol，超文字傳輸協定）是 client 與 server 之間「一問一答」的應用層協定：client 送出一個**請求**（request），server 回一個**回應**（response），例如瀏覽器送「給我 `/teachers/美咲` 這一頁」，server 回「200 OK，這是 HTML」。HTTP/1.1 是這個協定的文字格式版本，它直接跑在 TCP（或 TLS over TCP）上。第 11 章說過，TCP 只提供一條沒有邊界的 byte stream，所以 HTTP/1.1 的第一個任務，就是在這條 stream 上自己劃出「一個訊息從哪裡開始、到哪裡結束」。

HTTP 的規格在 2022 年重新整理成三份：**RFC 9110**〈HTTP Semantics〉定義各版本共用的**語意**（method 是什麼意思、status code 代表什麼、header 的用途），**RFC 9112**〈HTTP/1.1〉只定義 HTTP/1.1 的**線路格式**（請求行怎麼寫、訊息怎麼切、連線怎麼管理），快取另外寫在 RFC 9111。這個切法很重要：本章講的 method 與 status code，在第 22 章的 HTTP/2 與 HTTP/3 裡意思完全一樣，變的只有「怎麼把它們變成 bytes」。

| 版本 | 年代 | 線路格式 | 連線 | 關鍵差異 |
|---|---|---|---|---|
| HTTP/0.9 | 1991 | 只有 `GET /path` 一行，沒有 header、沒有 status | 每個請求一條，回應完就關 | 只能抓 HTML |
| HTTP/1.0 | 1996 | 請求行＋header＋body，回應有狀態行 | 預設每個請求一條；可用 `Connection: keep-alive` 協商保持 | 有 header、status code、Content-Type |
| HTTP/1.1 | 1997 起，現行為 RFC 9112 | 同上，文字格式 | **預設保持連線**（persistent） | 必須有 `Host`、chunked、更嚴謹的邊界規則 |
| HTTP/2 | 2015 | binary frame，多個 stream 共用一條連線 | 一條長連線 | 第 22 章 |
| HTTP/3 | 2022 | binary frame，跑在 QUIC 上 | 一條 QUIC 連線 | 第 13、22 章 |

這張表最值得記住的是 HTTP/1.1 那一列的兩個「預設」：連線預設保持，以及每個請求都必須帶 `Host`。故事裡的 75 秒，就是第一個預設造成的；本章後半的 Host 與 smuggling，則都和「一條連線上有好幾個訊息、好幾個網站」有關。

一個 HTTP/1.1 訊息，不論是請求還是回應，都由四個部分組成：一行**起始行**（start line，請求叫 request line，回應叫 status line）、零或多行 **header**（又叫 field，標頭欄位，例如 `Content-Type: application/json`）、一個空行、以及可有可無的 **body**（訊息本體，又叫 content）。每一行都以 **CRLF**（`\r\n`，兩個 byte：0x0D 0x0A）結尾。

```text
  ┌──────────────────────────────────────────────┐
  │ start line                           CRLF    │  請求：GET /path HTTP/1.1
  │                                              │  回應：HTTP/1.1 200 OK
  ├──────────────────────────────────────────────┤
  │ field-name ":" OWS field-value OWS   CRLF    │  ┐
  │ field-name ":" OWS field-value OWS   CRLF    │  ├ header section（零或多行）
  │ ...                                          │  ┘
  ├──────────────────────────────────────────────┤
  │                                      CRLF    │  空行：header 到此結束
  ├──────────────────────────────────────────────┤
  │ body（長度由 Content-Length 或 chunked 決定） │  可能是 0 byte
  └──────────────────────────────────────────────┘
  ← 下一個訊息緊接著從這裡開始（同一條 TCP 連線）
```

逐列讀這張圖。start line 與每一行 header 都用 CRLF 結束，`OWS`（optional whitespace）表示冒號後、值的前後可以有空格或 tab，解析時要去掉。header 與 body 之間一定有一個只含 CRLF 的空行，這是「header 結束」唯一的訊號，所以 header 裡不能出現空行。最關鍵的是最下面那一列：body 之後**沒有**任何結束記號，下一個訊息直接接在後面。HTTP/1.1 判斷 body 長度的規則因此決定了一切，20.7 節會專門處理它。

> [!warning] 常見誤解
> 「HTTP 是純文字，所以用 `readline()` 讀到底就好。」start line 與 header 確實是以行為單位的文字（而且規格只保證 ASCII，其他 byte 要謹慎處理），但 body 是任意 bytes，可能是 JSON、圖片或 gzip 壓縮的資料，裡面可能剛好有 `\r\n`，也可能完全沒有。body 只能依長度讀，不能依內容猜。

## 20.3 請求：請求行、header 與 body

先看小晴的探針實際要送的一個請求。下面是一個 POST 預約請求在線路上的樣子，左邊是 bytes 的內容，右邊標出每一段的角色：

```text
 P O S T ␠ / v 1 / b o o k i n g s ? s r c = w e b ␠ H T T P / 1 . 1 ␍␊   ← request line
 └method┘   └──────────── request-target ────────────┘   └─ version ─┘
 H o s t : ␠ a p i . s h e n g s h e n g . e x a m p l e ␍␊          ← header（必備）
 C o n t e n t - T y p e : ␠ a p p l i c a t i o n / j s o n ␍␊      ← header
 C o n t e n t - L e n g t h : ␠ 1 9 ␍␊                                ← header（body 長度）
 ␍␊                                                                     ← 空行
 { " l e s s o n " : " j a - 1 0 1 " }                                  ← body，剛好 19 bytes
 （␠ = 空格 0x20，␍␊ = CRLF 0x0D 0x0A）
```

請求行由三段組成，中間各用**一個**空格隔開。**method**（方法）說明要對資源做什麼，例如 `GET` 讀取、`POST` 送出資料處理；method 區分大小寫，`get` 和 `GET` 是不同的東西。**request-target**（請求目標）是要操作的資源，最常見的形式是 path 加上 query，例如 `/v1/bookings?src=web`；它不含 scheme、主機名稱，也不含 `#` 後面的 fragment（第 1 章看過，fragment 永遠不會送給 server）。最後的 **HTTP-version** 告訴對方這個訊息用哪一版的格式，對方據此決定連線行為。

request-target 其實有四種形式，各自用在不同場合。junior 工程師平常只會看到第一種，但在 proxy 與除錯時其他三種都會出現：

| 形式 | 例子 | 使用場合 |
|---|---|---|
| origin-form | `GET /v1/bookings?src=web HTTP/1.1` | 一般請求，直接送給 origin server（最常見） |
| absolute-form | `GET` 後面接完整的 URI（含 scheme `http`、主機 `api.shengsheng.example` 與 path `/v1/bookings`），再接 `HTTP/1.1` | 送給 forward proxy 的請求（第 25 章）；server 也必須能接受 |
| authority-form | `CONNECT api.shengsheng.example:443 HTTP/1.1` | 只用於 `CONNECT`，請 proxy 打通一條到目的地的隧道 |
| asterisk-form | `OPTIONS * HTTP/1.1` | 只用於 `OPTIONS`，詢問整台 server 而非某個資源的能力 |

header 的格式是「名稱、冒號、值」。名稱**不分大小寫**（`content-length` 和 `Content-Length` 相同），只能由規格定義的 token 字元組成；名稱與冒號之間**不准有空白**，RFC 9112 要求 server 遇到這種請求時回 400，因為不同實作對 `Transfer-Encoding : chunked` 這種寫法的處理方式不同，正是 20.9 節 smuggling 的來源之一。舊規格允許把一個 header 值折到下一行（以空格開頭的續行，叫 **obs-fold**），現行規格已經廢止，server 必須拒絕或把它換成空格。

同一個名稱可以出現多次，語意上等於用逗號把值串起來，例如兩行 `Accept: text/html` 與 `Accept: application/json` 等於一行 `Accept: text/html, application/json`。`Set-Cookie` 是著名的例外：它的值本身可能含逗號（日期格式），所以每個 cookie 一定要分開成獨立的一行（第 21 章）。另一個例外是只能有一個值的 header，例如 `Host` 與 `Content-Length`，重複出現就是錯誤，本章後面會反覆遇到。

body 是可選的。`GET` 請求通常沒有 body，有 body 的請求必須用 `Content-Length` 或 `Transfer-Encoding: chunked` 說明長度；**請求兩者都沒有，就代表 body 長度是 0**，server 不能「讀到連線關閉」，因為 client 還在等回應，不會關閉連線。

要確認自己對格式的理解，最好的方法是看真正的 HTTP client 送了什麼。下面的程式在 127.0.0.1 上開一個只會「錄音」的 server，用 Python 標準函式庫的 `http.client` 送一個 POST，再把 server 收到的原始 bytes 逐行印出：

```python
import http.client
import socket
import threading

# 一個只會「錄音」的 server：把收到的原始 bytes 存起來，回一個最小的回應
listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen(1)
captured = []


def record():
    conn, _ = listener.accept()
    with conn:
        data = b""
        while b"\r\n\r\n" not in data:
            data += conn.recv(4096)
        head, _, body = data.partition(b"\r\n\r\n")
        length = int(dict(l.split(b": ", 1) for l in head.split(b"\r\n")[1:])[b"Content-Length"])
        while len(body) < length:
            body += conn.recv(4096)
        captured.append(head + b"\r\n\r\n" + body)
        conn.sendall(b"HTTP/1.1 201 Created\r\nContent-Length: 0\r\n\r\n")


t = threading.Thread(target=record)
t.start()
port = listener.getsockname()[1]
client = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
client.request("POST", "/v1/bookings?src=web", body=b'{"lesson":"ja-101"}',
               headers={"Host": "api.shengsheng.example", "Content-Type": "application/json"})
resp = client.getresponse()
print(resp.status, resp.reason)
client.close()
t.join()
listener.close()

for line in captured[0].split(b"\r\n"):
    print(repr(line)[2:-1] if line else "（空行：header 結束）")
assert captured[0].startswith(b"POST /v1/bookings?src=web HTTP/1.1\r\n")
assert b"Content-Length: 19\r\n" in captured[0]
```

```text
201 Created
POST /v1/bookings?src=web HTTP/1.1
Accept-Encoding: identity
Content-Length: 19
Host: api.shengsheng.example
Content-Type: application/json
（空行：header 結束）
{"lesson":"ja-101"}
```

第一行是 server 回給 client 的狀態，證明一問一答完成了。接著是 `http.client` 實際寫進 socket 的內容：請求行完全符合上面的格式；`Accept-Encoding: identity` 是 `http.client` 自動加上的，意思是「請不要壓縮回應」；`Content-Length: 19` 是它依 body 長度自動算出來的；`Host` 因為我們明確指定，所以用了我們給的值，而不是連線的 IP 與 port。header 之後的空行與剛好 19 bytes 的 body，也和圖上一致。兩個 `assert` 把這兩個關鍵事實寫成檢查：請求行的格式，以及 body 長度被正確宣告。

## 20.4 Method 語意：safe、idempotent 與重試

method 不只是「動詞」，它對 client、proxy、快取與 server 是一個**承諾**。RFC 9110 用兩個性質描述這個承諾。**safe**（安全）表示這個請求在語意上是唯讀的，client 不要求、也不預期它改變 server 上的狀態，例如 `GET /api/classes/today` 只是查詢；瀏覽器的預先載入、爬蟲、連結預覽都依賴這個性質，會自由地送出 safe 的請求。**idempotent**（冪等）表示同一個請求送一次和送很多次，對 server 的「預期效果」相同，例如 `PUT /v1/bookings/1001` 把預約 1001 設成某個內容，送三次結果還是那個內容；`DELETE /v1/bookings/1001` 刪除後再刪，預約仍然是不存在的狀態（回應碼可能從 204 變成 404，但效果相同）。

| method | 用途 | safe | idempotent | 請求通常有 body | 例子 |
|---|---|---|---|---|---|
| GET | 取得資源的表示 | 是 | 是 | 否 | `GET /teachers/美咲` |
| HEAD | 同 GET，但回應不含 body | 是 | 是 | 否 | 檢查檔案大小、連結是否有效 |
| OPTIONS | 詢問資源支援的通訊選項 | 是 | 是 | 否 | CORS preflight（第 23 章） |
| TRACE | 讓 server 把收到的請求原樣回傳 | 是 | 是 | 否 | 除錯用，多數 server 關閉 |
| PUT | 用請求內容取代整個資源 | 否 | 是 | 是 | `PUT /users/me/avatar` |
| DELETE | 刪除資源 | 否 | 是 | 否 | `DELETE /v1/bookings/1001` |
| POST | 依資源自己的語意處理請求內容 | 否 | 否 | 是 | `POST /v1/bookings` 建立預約 |
| PATCH | 部分修改資源（RFC 5789） | 否 | 否（看內容而定） | 是 | `PATCH /users/me {"nickname":…}` |
| CONNECT | 請 proxy 建立隧道 | 否 | 否 | 否 | HTTPS 經過 forward proxy |

所有 safe 的 method 都是 idempotent，反過來不成立。注意「idempotent」講的是**預期效果**，不是回應內容，也不是 server 的所有副作用：GET 也會寫 access log、增加統計計數，這些不影響 GET 的 safe 性質，因為 client 沒有要求這些事。表上的性質也是一個「承諾」，server 必須自己守住：如果有人把「取消預約」做成 `GET /v1/bookings/1001/cancel`，瀏覽器預先載入或聊天軟體產生連結預覽時，就可能替使用者把預約取消掉。

為什麼這兩個性質這麼重要？因為網路會失敗，而失敗最難處理的形式，是「請求送出去了，但沒有收到回應」。看下面這張時序圖，它就是故事裡重複預約的成因：

```text
 探針（client）                        nginx                     gunicorn／資料庫
   │── POST /v1/bookings（lesson=ja-101）─►│────────────────────────►│
   │                                    │                         │ INSERT 預約 1002 ✔
   │                                    │      worker 被重啟 ✘     │
   │◄──── 連線被關閉，沒有任何回應 ──────│◄──── 連線中斷 ───────────│
   │
   │  client 能確定的只有：「我送出了，沒收到回應」
   │  ┌─ 情況 A：請求根本沒到 server ──────────► 重送是正確的
   │  └─ 情況 B：server 做完了，只是回應丟了 ──► 重送 = 第二筆預約
   │
   │── POST /v1/bookings（同樣內容，重送）──►│────────────────────────►│ INSERT 預約 1003 ✘ 重複
```

從上往下讀。探針送出 POST，gunicorn 已經把預約 1002 寫進資料庫，卻在送出回應之前被重啟（部署、OOM、逾時都可能），nginx 收到上游中斷，只能把連線關掉或回 502。對 client 而言，情況 A（請求沒到）與情況 B（做完了但回應丟了）在網路上看起來**完全一樣**：都是「送出、然後沒有回應」。如果 method 是 idempotent，兩種情況都可以放心重送，因為重送不會改變結果；POST 不是，重送在情況 B 就會產生第二筆預約。

因此 RFC 9110 規定：client **不應該**自動重試非 idempotent 的請求，除非它有辦法知道這個請求實際上是 idempotent 的，或確定原本的請求沒有被處理。這條規則落實在各層的實作裡：nginx 的 `proxy_next_upstream` 自 1.9.13 版起，預設不會把已經送給上游的 POST、PATCH 再轉送到下一台 server，除非明確加上 `non_idempotent`；常見的 HTTP client 函式庫，預設的自動重試清單也只包含 idempotent 的 method。

那 POST 真的需要重試時怎麼辦？業界標準做法是 **idempotency key**：client 為每個「邏輯上的操作」產生一個唯一值，放進 header（常見名稱是 `Idempotency-Key`），重試時帶同一個值；server 記住每個 key 第一次的結果，看到重複的 key 就直接回傳舊結果，不再重做。這等於把 POST 在應用層變成 idempotent。金流 API 普遍採用這個做法，第 24 章會講 key 的儲存、過期與併發處理；本章的實驗三會在本機重現「盲目重試寫兩筆、帶 key 只寫一筆」的差別。

> [!note] 0-RTT 也是同一個問題
> 第 13 章與第 18 章提過，TLS 1.3 與 QUIC 的 0-RTT 資料可能被重放。聲聲 Live 的規則是只放行 GET 與 HEAD 走 0-RTT，其他請求回 `425 Too Early` 要求 client 等交握完成再送。這條規則背後的判斷，正是本節的 safe 與 idempotent。

## 20.5 回應：狀態行與 status code 家族

回應的起始行叫**狀態行**（status line），由版本、三位數的 **status code**（狀態碼）與 **reason phrase**（原因短語）組成，例如 `HTTP/1.1 404 Not Found`。程式只應該看 status code；reason phrase 只是給人看的說明，規格允許它是任何文字甚至空白，HTTP/2 乾脆把它拿掉了。所以 client 判斷成功與否時要寫 `status == 404`，不要比對 `"Not Found"` 字串。

status code 的第一位數字代表**家族**，這是除錯時最快的第一刀：它告訴你「該去誰那裡找問題」。

| 家族 | 意思 | 該找誰 | 常見例子 |
|---|---|---|---|
| 1xx | 資訊：請求收到，處理繼續中，還會有最終回應 | 通常不用找 | 100 Continue、101 Switching Protocols（第 32 章 WebSocket）、103 Early Hints |
| 2xx | 成功 | 不用找 | 200 OK、201 Created、204 No Content、206 Partial Content（第 21 章） |
| 3xx | 重新導向或使用快取 | 看 `Location` 或快取設定 | 301、302、303、307、308（第 21 章）、304 Not Modified |
| 4xx | client 的請求有問題，原樣重送不會成功 | 呼叫方 | 400、401、403、404、405、409、413、429、431 |
| 5xx | server 或中間的 gateway 處理失敗 | 服務方與 proxy | 500、502、503、504 |

1xx 是唯一「不是最終回應」的家族，一個請求可以先收到零到多個 1xx，最後才是 2xx 到 5xx 的最終回應。最常見的是 **100 Continue**：client 要上傳大檔案時，先送 header 並帶 `Expect: 100-continue`，等 server 回 100 才送 body；如果 server 看了 header 就知道要拒絕（例如檔案太大回 413、沒登入回 401），client 就不用白白上傳幾百 MB。**103 Early Hints** 讓 server 在還在計算主回應時，先告訴瀏覽器「你等一下一定會需要這些 CSS」，讓瀏覽器提早預載。寫 client 時要記得：收到 1xx 後要繼續讀，下一個狀態行才是真正的回應。

4xx 與 5xx 的分界是 on-call 時最常用的判斷。4xx 表示「這個請求本身有問題」，同樣的請求重送多少次結果都一樣，除非 client 修正它；5xx 表示「請求可能沒問題，是處理的一方失敗了」，其中一部分（尤其是 502、503、504）值得稍後重試。下表是在聲聲 Live 的 log 裡最常見、也最容易混淆的幾個：

| status | 名稱 | 誰產生的 | 聲聲 Live 的典型情境 |
|---|---|---|---|
| 400 | Bad Request | 任何一層 | 缺 `Host`、header 格式錯誤、JSON 壞掉 |
| 401 | Unauthorized | 應用程式 | 沒帶或帶了過期的 token（其實是「未驗證」，第 26、27 章） |
| 403 | Forbidden | 應用程式、WAF | 驗證過了但沒有權限，例如學生想改老師的課表 |
| 404 | Not Found | 應用程式、nginx | 路徑錯誤，或 Host 打到錯誤的虛擬主機 |
| 405 | Method Not Allowed | 應用程式 | 對只接受 GET 的路由送 POST；回應必須附 `Allow` header |
| 409 | Conflict | 應用程式 | 預約的時段剛好被別人搶走 |
| 413 | Content Too Large | nginx | 上傳超過 `client_max_body_size`（nginx 預設 1 MB） |
| 421 | Misdirected Request | server、LB | 請求送到了不負責這個 Host 的 server |
| 429 | Too Many Requests | API gateway、應用程式 | 觸發限速；常附 `Retry-After` |
| 431 | Request Header Fields Too Large | server | cookie 累積太多，header 超過上限 |
| 500 | Internal Server Error | 應用程式 | Flask view 拋出未處理的例外 |
| 502 | Bad Gateway | nginx、LB | 上游回了壞掉的回應，或連線被上游關閉、拒絕 |
| 503 | Service Unavailable | nginx、LB、應用程式 | 沒有健康的上游，或主動降載；可附 `Retry-After` |
| 504 | Gateway Timeout | nginx、LB | 上游在逾時內沒有回應，例如 gunicorn 卡在呼叫金流 |

這張表的第三欄比名稱更重要。502 與 504 永遠是「中間那一層」產生的：nginx 回 504 時，Flask 的 log 裡可能完全沒有錯誤，甚至那個請求最後成功寫入了資料庫，這正是 20.4 節「送出但沒收到回應」的另一個來源。所以看到 5xx 時，先確認是哪一層產生的（看回應的 `Server` header、回應內容的格式、各層 log 裡的 `x-request-id`），再去對應的地方找原因。

## 20.6 Host header：一個 IP 上的很多網站

HTTP/1.0 早期的請求行只有 path，例如 `GET /index.html`，server 只能從「連到哪個 IP」判斷你要哪個網站，於是每個網站都要一個 IP。IPv4 位址很快就不夠用了。HTTP/1.1 的解法是 **Host header**：client 在每個請求裡寫明「我要的是哪個主機名稱（與 port）」，同一個 IP 上就能放很多網站，這叫**虛擬主機**（virtual hosting，又叫 name-based virtual hosting）。聲聲 Live 的 nginx 就是靠它，在同一組 IP 上同時服務 `www` 與 `api`。

```text
                         DNS（第 14 章）
  www.shengsheng.example ─┐            ┌──► 203.0.113.80
  api.shengsheng.example ─┴─ 解析 ─────┘    （同一個 IP、同一個 port 443）

  TCP 連到 203.0.113.80:443
   └─ TLS ClientHello 的 SNI：api.shengsheng.example   ← 選哪一張憑證（第 18 章）
       └─ HTTP 請求的 Host：api.shengsheng.example     ← 選哪一個 server block／app
           └─ request-target：/v1/bookings                ← 選哪一個路由

  nginx：
   server { server_name www.shengsheng.example; ... }  ──► 靜態網站
   server { server_name api.shengsheng.example; ... }  ──► gunicorn 10.20.3.21:8000
   server { listen 443 default_server; return 444; }   ──► Host 不認識：直接關閉連線
```

這張圖由上往下是一個請求「選擇目的地」的三個層次。DNS 把兩個名稱都解析到同一個 IP，所以光看 IP 與 port 分不出要哪個網站。TLS 交握時，client 先在 **SNI**（Server Name Indication，第 18 章）裡告訴 server 主機名稱，讓 server 拿出對的憑證；TLS 建立後，HTTP 請求裡的 `Host` 再決定交給哪一個 `server` 區塊或哪個應用程式；最後才是 request-target 決定路由。最下面的 `default_server` 是防禦設定：任何 `Host` 不符合已知名稱的請求，都落到這裡並被關閉，`444` 是 nginx 專用的「不回應、直接關閉連線」代碼，不是標準的 status code。

RFC 9112 對 Host 的要求很嚴格：HTTP/1.1 的 client **必須**在每個請求送出 Host；server 收到缺少 Host、有兩個以上 Host、或 Host 值不合法的 HTTP/1.1 請求，**必須**回 400。值的格式是主機名稱，port 不是預設值時要加上，例如 `Host: api.shengsheng.example:8443`；主機名稱和 DNS 一樣不分大小寫。使用 absolute-form 送給 proxy 時，request-target 裡的主機優先，Host 仍然要送而且要一致。到了 HTTP/2 與 HTTP/3，同樣的資訊放在 `:authority` pseudo-header（第 22 章），角色相同。

Host 與 SNI 正常情況下是同一個名稱，但兩者是分開送的，所以可能不一致。一個常見的例子是**連線合併**（connection coalescing，第 22 章）：瀏覽器發現 `www` 與 `api` 解析到同一個 IP，而且憑證同時涵蓋兩者，可能直接重用 `www` 的連線送 `api` 的請求。如果那台 server 其實不服務 `api`，正確的回應是 **421 Misdirected Request**，告訴 client「換一條連線再試」。

Host 的另一面是安全。Host 是 client 自己填的，任何人都可以送 `Host: attacker.invalid`。如果應用程式拿它來產生**絕對網址**，例如「忘記密碼」信裡的重設連結、或 OAuth 的 redirect URI，攻擊者就能讓受害者收到一封寄自聲聲 Live、連結卻指向外部網站的信，這類問題統稱 **Host header 攻擊**。防禦有兩層。第一，在入口設定**允許清單**：nginx 用明確的 `server_name` 加上一個拒絕一切的 `default_server`，應用程式也只接受已知的 Host（Django 的 `ALLOWED_HOSTS` 是同一個概念）。第二，需要絕對網址時，從設定檔讀出正式網域，而不是從請求裡讀 Host。實驗二會在本機示範這兩件事。

> [!warning] 常見誤解
> 「放在 LB 後面，Host 就一定是我們的網域。」LB 通常只是把 Host 原樣轉給後端，而且可能接受任何 Host。經過 proxy 時，原始的 Host 也可能被改寫，真正的值放在 `X-Forwarded-Host` 或 `Forwarded` header；這些 header 只有來自信任的 proxy 時才能相信（第 25、43 章）。

## 20.7 訊息邊界：Content-Length 與 chunked

現在回到故事裡最先出問題的地方：client 怎麼知道回應在哪裡結束？答案取決於一組有先後順序的規則。RFC 9112 定義了判斷 body 長度的完整流程，下圖是對 client 讀回應時的版本：

```text
 收到回應的 header
   │
   ├─ 這是對 HEAD 的回應？或 status 是 1xx、204、304？
   │     └─ 是 ──► 沒有 body（就算 header 裡有 Content-Length 也一樣）
   │
   ├─ 有 Transfer-Encoding，而且最後一個 coding 是 chunked？
   │     └─ 是 ──► 依 chunked 格式讀到 last-chunk（TE 優先於 Content-Length）
   │
   ├─ 有 Transfer-Encoding，但最後不是 chunked？
   │     └─ 是 ──► 讀到連線關閉為止（請求遇到這種情況必須回 400）
   │
   ├─ 有合法的 Content-Length？
   │     └─ 是 ──► 剛好讀 N bytes，多一個 byte 都不讀
   │           （值不合法：請求回 400；proxy 收到這種回應要回 502）
   │
   └─ 都沒有
         ├─ 請求 ──► body 長度是 0
         └─ 回應 ──► 讀到 server 關閉連線為止（這條連線之後不能重用）
```

由上往下逐條判斷，第一個成立的規則決定一切。第一條是「規定沒有 body」的情況：HEAD 的回應 header 和 GET 一模一樣，包括告訴你「如果用 GET，body 會是 35 bytes」的 `Content-Length`，但實際上一個 byte 都不會送，client 如果照 Content-Length 去讀，就會把下一個回應的開頭當成 body，或卡住等待永遠不會來的資料。204 與 304 也一樣，1xx 則是後面還有最終回應。第二條是 chunked，它優先於 Content-Length；第四條才是 Content-Length。最後一條區分請求與回應：回應可以用「關閉連線」當作結束（HTTP/1.0 時代的做法），請求不行，因為 client 送完請求還要等回應，不可能先關連線。

故事裡第一版探針的錯誤，就是對每個回應都套用最後一條：nginx 的回應明明帶了 `Content-Length: 35`，連線依 HTTP/1.1 預設保持開著，探針卻一直等 EOF，直到 nginx 的閒置逾時把連線關掉。正確的做法是讀完 header 後依上面的流程決定讀多少，讀完立刻處理，連線留給下一個請求用。

**Content-Length** 是最簡單的方式：一個十進位數字，表示 body 的 byte 數（不是字元數，UTF-8 的「美咲」是 6 bytes）。它要求 server 在送出 header 之前就知道整個 body 有多大，對靜態檔案和一次產生完的 JSON 沒問題，但對「邊查邊送」的串流、大型匯出檔、或 LLM 逐字產生的回應，server 要嘛把全部內容先存在記憶體裡算長度，要嘛就需要另一種方式。

**chunked**（分塊傳輸編碼）就是那另一種方式：body 被切成一塊一塊，每塊前面寫上這塊的長度，最後用一個長度為 0 的塊表示結束。下面是課表 API 送出三行資料時，線路上真正的 bytes：

```text
 HTTP/1.1 200 OK␍␊
 Transfer-Encoding: chunked␍␊
 Trailer: X-Row-Count␍␊
 ␍␊                                   ← header 結束
 d␍␊                                  ← chunk-size：十六進位 d = 13 bytes
 19:00 ja-101⏎␍␊                      ← 13 bytes 資料（含換行 ⏎），後面固定一個 CRLF
 d␍␊
 20:00 ja-102⏎␍␊
 d;note=last-row␍␊                    ← 可選的 chunk extension（分號後），接收方通常忽略
 21:00 en-201⏎␍␊
 0␍␊                                  ← last-chunk：長度 0，body 結束
 X-Row-Count: 3␍␊                     ← trailer section（可選）：body 之後才知道的 header
 ␍␊                                   ← 整個訊息結束
```

逐行解讀。每個 chunk 都是「十六進位長度（可以帶分號開頭的 extension）＋ CRLF ＋ 剛好那麼多 bytes 的資料 ＋ CRLF」，長度不含資料後面的 CRLF。故事裡的 `1f4` 就是 chunk-size，十六進位 1f4 等於 500，表示接下來 500 bytes 是資料；小晴的探針把它當成 body 的開頭，JSON 解析自然失敗。長度為 0 的 **last-chunk** 表示資料結束，後面可以接 **trailer**：在 body 送完之後才知道的 metadata，例如資料筆數或整個 body 的 checksum，`Trailer` header 預告會有哪些 trailer。最後的空行代表整個訊息真正結束，下一個回應從下一個 byte 開始。

| 方式 | 何時用 | 優點 | 代價與注意事項 |
|---|---|---|---|
| Content-Length | 送出前就知道長度：靜態檔案、一般 JSON | 最簡單；client 能顯示下載進度；可以搭配 Range（第 21 章） | server 必須先知道全部長度 |
| chunked | 串流、邊產生邊送、SSE（第 31 章）、長時間匯出 | 不用先知道長度；首個 byte 更早送出；可帶 trailer | 只有 HTTP/1.1 有；解析器較複雜，是 smuggling 的常見來源 |
| 讀到連線關閉 | 只用於回應，且是不得已的最後手段 | 不需要任何長度資訊 | 連線不能重用；無法分辨「送完了」與「中途斷線」 |

最後一欄點出「讀到連線關閉」最大的問題：如果 server 在送到一半時 crash，client 看到的也是 EOF，它沒有辦法知道內容被截斷了。這是 HTTP/1.1 偏好明確長度的理由。也要分清楚兩個名字很像的 header：`Transfer-Encoding` 是**這一段連線上**怎麼傳（hop-by-hop，每經過一個 proxy 都可能改變），`Content-Encoding: gzip` 則是**內容本身**被壓縮了（end-to-end，第 21 章），兩者可以同時存在。chunked 是 HTTP/1.1 專屬的機制，HTTP/1.0 沒有它，HTTP/2 與 HTTP/3 有自己的 frame 來標示結束，所以在這兩個版本裡出現 `Transfer-Encoding` header 反而是錯誤。

## 20.8 Keep-alive 與連線重用

為什麼 HTTP/1.1 要把「保持連線」設成預設？回想第 1 章的時間軸：一個全新的 HTTPS 請求，在送出第一個 byte 之前就要花 TCP 交握 1 個 RTT 加上 TLS 1.3 交握 1 個 RTT。對 RTT 180 毫秒的美國學生，這是 360 毫秒的固定成本；新連線還要從 TCP slow start 開始（第 12 章），一開始只能送少量資料。**persistent connection**（持久連線，俗稱 **keep-alive**）讓同一條連線送完一個請求後繼續送下一個，這些成本只付一次。

```text
 每個請求一條新連線（HTTP/1.0 預設）           重用一條連線（HTTP/1.1 預設）
 Client                 Server                Client                 Server
   │── SYN ────────────►│  ┐                    │── SYN ────────────►│  ┐
   │◄──────── SYN+ACK ──│  │ 1 RTT              │◄──────── SYN+ACK ──│  │ 1 RTT（只有一次）
   │── ACK、GET /a ────►│  ┘                    │── ACK、GET /a ────►│  ┘
   │◄────────── 200 /a ─│  ← 1 RTT              │◄────────── 200 /a ─│  ← 1 RTT
   │── FIN ────────────►│                       │── GET /b ─────────►│
   │── SYN ────────────►│  ┐                    │◄────────── 200 /b ─│  ← 1 RTT
   │◄──────── SYN+ACK ──│  │ 再 1 RTT           │── GET /c ─────────►│
   │── ACK、GET /b ────►│  ┘                    │◄────────── 200 /c ─│  ← 1 RTT
   │◄────────── 200 /b ─│                       │     ……閒置……       │
   │── FIN ────────────►│                       │◄────────────── FIN ─│ ← 閒置逾時，server 先關
   │   ……每個請求都重來……                      │
   3 個請求：6 RTT（不含 TLS）                   3 個請求：4 RTT（不含 TLS）
```

左右兩欄比較同樣三個請求的成本。左邊每個請求都重做交握，3 個請求花 6 個 RTT，加上 TLS 還要再多 3 個 RTT；右邊只有第一個請求付交握的成本，之後每個請求只要 1 個 RTT。右下角是另一個重點：持久連線最後通常是 **server 因為閒置逾時而主動關閉**，這會讓 TIME_WAIT 落在 server 端（第 10 章），也帶出本節後半要講的競態問題。

連線行為由 `Connection` header 控制。HTTP/1.1 預設保持；任何一方送出 `Connection: close`，就表示「這個訊息之後我會關閉連線」，對方讀完這個訊息就不該再送。HTTP/1.0 預設關閉，雙方都送 `Connection: keep-alive` 才保持，這是一個非正式的擴充。`Keep-Alive: timeout=5, max=100` 這個 header 只是提示（告訴對方我大概會保持多久、最多處理幾個請求），不是保證。`Connection` 還有另一個用途：它列出的 header 名稱都是 **hop-by-hop**，只對這一段連線有效，proxy 轉送前必須移除，例如 `Connection`、`Keep-Alive`、`Transfer-Encoding`、`Upgrade`。

Python 的 `http.server` 是很好的反面教材：`BaseHTTPRequestHandler` 的 `protocol_version` 預設是 `"HTTP/1.0"`，回完一個回應就關閉連線。下面的程式在同一條連線上連送兩個請求，分別對兩種設定的 server：

```python
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def make_handler(version):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = version  # http.server 預設是 "HTTP/1.0"

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            pass
    return Handler


def two_requests(addr):
    """在同一條連線上連送兩個請求，回傳各自的狀態行。"""
    answers = []
    with socket.create_connection(addr, timeout=1) as s:
        f = s.makefile("rb")
        for _ in range(2):
            try:
                s.sendall(b"GET / HTTP/1.1\r\nHost: www.shengsheng.example\r\n\r\n")
                status = f.readline().decode().strip()
            except OSError as exc:      # 對方已經關閉，送出時可能直接收到 RST
                status = ""
            if not status:
                answers.append("（沒有回應：server 已關閉連線）")
                break
            while f.readline() not in (b"\r\n", b""):
                pass                    # 這裡只關心狀態行，略過 header
            f.read(2)                   # body 固定是 2 bytes
            answers.append(status)
    return answers


for version in ("HTTP/1.0", "HTTP/1.1"):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(version))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    answers = two_requests(server.server_address)
    print(f"protocol_version = {version}：{' ／ '.join(answers)}")
    server.shutdown()
    server.server_close()
    expected = 1 if version == "HTTP/1.0" else 2
    assert sum(a.endswith("200 OK") for a in answers) == expected
```

```text
protocol_version = HTTP/1.0：HTTP/1.0 200 OK ／ （沒有回應：server 已關閉連線）
protocol_version = HTTP/1.1：HTTP/1.1 200 OK ／ HTTP/1.1 200 OK
```

設成 `HTTP/1.0` 時，server 回應的狀態行也是 `HTTP/1.0`，送完就關閉連線，第二個請求得不到回應；改成 `HTTP/1.1` 後，兩個請求都在同一條連線上得到 200。改成 HTTP/1.1 有一個前提：handler **一定要**送出正確的 `Content-Length`（或用 chunked），否則 client 不知道 body 在哪裡結束，第 1 章的 Q&A 已經提醒過。這也是第 40 章自己寫 server 時要處理的事。

持久連線帶來一個無法完全消除的競態：**server 關閉閒置連線的那一刻，client 可能正好送出新請求**。client 的 `send()` 會成功（資料只是進了本機的送出 buffer），接著讀到 EOF 或 `ECONNRESET`。這個請求有沒有被處理？如果 server 在收到前就關了，沒有；但從 client 的角度，它和 20.4 節「做完了但回應丟了」看起來一樣。實務上的應對有三條：client 的閒置上限要**短於** server 的 keep-alive timeout（例如 nginx 對外 75 秒，client 池設 60 秒）；在重用的連線上失敗時，只對 idempotent 的請求自動重送；非 idempotent 的請求靠 idempotency key。各層的 keep-alive timeout 怎麼排，是第 43 章 timeout 鏈的主題。

| 位置 | 設定 | 預設值 | 說明 |
|---|---|---|---|
| nginx 對 client | `keepalive_timeout` | 75 秒 | 閒置多久關閉對外連線；`keepalive_requests` 限制每條連線的請求數 |
| nginx 對上游 | `upstream { keepalive N; }` | 不重用 | 要同時設 `proxy_http_version 1.1` 並清掉 `Connection` header 才會重用 |
| gunicorn | `--keep-alive` | 2 秒 | 只對非 sync worker 有意義；nginx 對上游開了 keepalive 時，它必須比 nginx 重用連線的時間長（第 43 章） |
| Python `http.server` | `protocol_version` | `"HTTP/1.0"` | 改成 HTTP/1.1 才會保持連線 |
| 瀏覽器 | 每個 origin 的 HTTP/1.1 連線數 | 約 6 條 | 超過就排隊；HTTP/2 改用一條連線多工（第 22 章） |

表上第二列是常見的陷阱：nginx 對上游預設每個請求都開新連線，因為它對上游預設用 HTTP/1.0 並送 `Connection: close`。在高流量下，這會讓 nginx 主機累積大量對 gunicorn 的 TIME_WAIT（第 10 章）。開啟上游 keep-alive 時要注意兩端逾時的方向：上游（gunicorn）的閒置逾時必須比 nginx 重用連線的時間長，否則就會出現「upstream prematurely closed connection」。

HTTP/1.1 還定義了 **pipelining**（管線化）：client 不等回應就在同一條連線上連送多個請求，server 必須依序回應。只要第一個回應很慢，後面全部被擋住，這是 HTTP 層的 **head-of-line blocking**（第 12 章），加上 proxy 相容性問題，瀏覽器幾乎都沒有啟用它，而是對每個 origin 開約 6 條平行連線（延伸問答 Q4 會比較 HTTP/2 的解法）。

> [!tip] header 與 body 分兩次 send 的 40 毫秒
> 自己寫 client 或 server 時，如果先 `send(header)` 再 `send(body)`，第二個小封包可能被 Nagle 演算法擋住，等對方的 ACK，而對方的 delayed ACK 在 Linux 上最少約 40 毫秒（第 11 章），結果每個請求莫名多出約 40 毫秒。解法是把 header 與 body 組成一個 buffer 一次送出，或設定 `TCP_NODELAY`。本章的程式都用 `sendall(head + body)`。

## 20.9 Request smuggling：當兩個解析器意見不同

前面幾節反覆出現同一件事：一條連線上的訊息邊界，完全取決於接收方怎麼解讀 `Content-Length` 與 `Transfer-Encoding`。當請求經過好幾層（CDN、LB、nginx、gunicorn），每一層都要自己解析一次邊界。如果其中兩層對**同一段 bytes** 的邊界判斷不同，就會出現 **HTTP request smuggling**（請求走私）：前一層以為自己轉送的是一個完整的請求，後一層卻把其中一部分當成「下一個請求的開頭」，而那條連線上的下一個請求，很可能來自另一個使用者。

```text
 前端 proxy（依 Content-Length）         後端 server（依 Transfer-Encoding）
 ┌──────────────────────────────┐        ┌──────────────────────────────┐
 │ 請求 1 的 header              │        │ 請求 1 的 header              │
 │ body：N bytes ← 整段都是請求 1 │ ─────► │ body：chunked，到 0 chunk 結束 │
 │                              │        ├──────────────────────────────┤
 │                              │        │ 剩下的 bytes ← 被當成「下一個 │
 │                              │        │ 請求」的開頭，留在連線裡       │
 └──────────────────────────────┘        └──────────────────────────────┘
               │                                         ▲
               └── 同一條重用的上游連線 ─────────────────┘
     下一個使用者的請求接在後面 ──► 被拼接到留下的 bytes 之後，語意被改變
```

這張圖說明成因，不是操作方法。左邊的前端只看 `Content-Length`，認為 N bytes 都屬於請求 1，原封不動地轉給後端；右邊的後端優先看 `Transfer-Encoding`，在遇到 last-chunk 時就認為請求 1 結束了，剩下的 bytes 留在緩衝區裡等待「下一個請求」。因為前端到後端的連線是重用的（20.8 節），下一個真正的使用者請求就接在這些殘留的 bytes 之後，被後端解讀成一個被竄改過的請求。後果包括繞過前端的存取控制、把別人的回應送給錯的人、污染快取等。

不一致從哪裡來？幾乎都來自「規格要求拒絕、但某個實作選擇寬容」的情況。常見的成因有這幾類：

| 成因 | 不一致的方式 | 規格的要求 |
|---|---|---|
| 同時有 `Content-Length` 與 `Transfer-Encoding` | 一層用 CL，另一層用 TE | TE 優先；這種請求應視為錯誤，server 可以拒絕，就算處理也必須在回應後關閉連線；proxy 轉送前必須移除 CL |
| 兩個不同的 `Content-Length` | 一層取第一個，另一層取最後一個 | 值不一致時必須當作無法恢復的錯誤（請求回 400） |
| `Transfer-Encoding` 的變形寫法 | 名稱前後有空白、值的大小寫或拼法怪異，一層認得、另一層不認得 | 名稱與冒號間有空白必須回 400；最後一個 coding 不是 chunked 的請求必須回 400 |
| chunk-size 或 chunked 格式的邊界情況 | 對非法的十六進位、超長的 size、少了 CRLF 的處理不同 | 依 RFC 9112 的文法嚴格解析，不合法就拒絕 |
| HTTP/2 轉成 HTTP/1.1（降版） | 前端用 HTTP/2 frame 判斷長度，轉成 HTTP/1.1 時保留了與實際長度不符的 `Content-Length` 或不該有的 TE | HTTP/2 不允許 `Transfer-Encoding`，`content-length` 必須與實際資料相符，不符就是 malformed |
| HTTP/1.0 下的 chunked、obs-fold 等舊語法 | 新舊實作的處理方式不同 | 拒絕或正規化，不要原樣轉送 |

表上每一列的共同點是：**問題不在於某一層的解析「錯了」，而在於兩層「不一樣」**。所以防禦的核心是讓整條路徑對邊界只有一種解讀：

- **在邊緣嚴格、不寬容**：最前面的 proxy 遇到任何模糊的請求（CL 與 TE 並存、重複且不一致的 CL、怪異的 TE、非法的 header 名稱），直接回 400 並關閉連線，而不是「猜一個合理的意思」再轉送。這也是 Rita 擋下小晴「寬容解析器」的原因。
- **正規化後再轉送**：proxy 重新產生乾淨的訊息，而不是原樣轉送收到的 bytes；例如移除 CL、自己重新做 chunked 或算出新的 Content-Length。
- **讓整條路徑使用相同或一致的解析器**，並保持更新。主流的 proxy 與 application server 都修補過大量 smuggling 相關的問題，舊版本是最大的風險來源。
- **前端到後端盡量用 HTTP/2**，它用 frame 標示長度，沒有 CL／TE 的二義性；但降版成 HTTP/1.1 的那一跳仍要嚴格檢查。
- **出錯就關連線**：解析錯誤後，這條連線上的 bytes 已經不可信，回完錯誤要關閉連線，不要繼續重用。
- **偵測**：監控各層的 400 數量、上游連線被意外關閉的次數，以及「前端 log 一個請求、後端 log 兩個請求」這類數量對不上的情況。

> [!note] 2026 現況
> 截至 2026 年 10 月（依 2026 年 10 月查證），gunicorn 在 25.3 與 26.x 系列加入了一批針對 request smuggling 的防護，包括拒絕重複的 `Content-Length`、拒絕 CL 與 TE 並存、拒絕 HTTP/1.0 下的 chunked、拒絕重複的 `Host`，以及拒絕被截斷的 chunked body。升級後，過去「勉強能用」的不合規 client（例如自己手寫、送了兩個 Host 的監測程式）可能開始收到 400，這是預期中的行為，應該修 client 而不是降級 server。實驗四的嚴格解析器採用的就是同樣的規則。

## 20.10 動手做：用 socket 手寫 HTTP/1.1 client

這一節把小晴的探針重寫成正確的版本，並在 127.0.0.1 上逐一驗證本章的規則。四個實驗都只用標準函式庫，server 用 `http.server` 或自己寫的小 handler 跑在 thread 裡，port 由系統分配。以下輸出是在 macOS 上實際執行的結果；含 port 的那一行每次執行數字不同。

### 實驗一：狀態行、header、Content-Length、chunked 與 keep-alive

第一段是探針的核心：送出請求、讀狀態行與 header，依 20.7 節的流程決定 body 怎麼讀，再在同一條連線上送下一個請求。server 端有三種回應：一般 JSON（Content-Length）、邊產生邊送的課表（chunked 加 trailer）、以及 HEAD。server 會記下每個請求的 client port，證明三個請求真的走同一條 TCP 連線。

```python
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

seen_peers = []  # server 端記下每個請求來自哪個 client port，用來證明連線被重用


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # 預設是 HTTP/1.0：回應完就關連線

    def do_GET(self):
        seen_peers.append(self.client_address[1])
        if self.path == "/api/classes/today":
            body = json.dumps({"classes": 3, "teacher": "美咲"}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/schedule/stream":
            # 邊產生邊送：事先不知道總長度，所以用 chunked
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Trailer", "X-Row-Count")
            self.end_headers()
            rows = [b"19:00 ja-101\n", b"20:00 ja-102\n", b"21:00 en-201\n"]
            for row in rows:
                self.wfile.write(f"{len(row):x}\r\n".encode() + row + b"\r\n")
            self.wfile.write(b"0\r\nX-Row-Count: 3\r\n\r\n")  # last-chunk + trailer + 空行
        else:
            self.send_error(404)

    def do_HEAD(self):
        seen_peers.append(self.client_address[1])
        # HEAD 回應的 header 和 GET 一樣（包括 Content-Length），但絕對沒有 body
        self.send_response(200)
        self.send_header("Content-Length", "35")
        self.end_headers()

    def log_message(self, *args):
        pass


class Response:
    def __init__(self, version, status, reason, headers, body, trailers):
        self.version, self.status, self.reason = version, status, reason
        self.headers, self.body, self.trailers = headers, body, trailers

    def header(self, name):
        values = [v for k, v in self.headers if k.lower() == name.lower()]
        return ", ".join(values) if values else None


def read_headers(f):
    fields = []
    while (line := f.readline(8192)) not in (b"\r\n", b"\n", b""):
        name, sep, value = line.decode("latin-1").partition(":")
        if not sep or name != name.strip():
            raise ValueError(f"壞掉的 header 行：{line!r}")
        fields.append((name, value.strip()))
    return fields


def read_chunked(f):
    body = b""
    while True:
        size_line = f.readline(1024).split(b";", 1)[0].strip()  # 忽略 chunk extension
        size = int(size_line, 16)
        if size == 0:
            return body, read_headers(f)  # last-chunk 之後是 trailer section
        body += f.read(size)
        if f.read(2) != b"\r\n":
            raise ValueError("chunk 資料後面少了 CRLF")


def request(sock, f, method, target, host):
    head = f"{method} {target} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: probe/0.1\r\n\r\n"
    sock.sendall(head.encode())
    status_line = f.readline(8192).decode("latin-1").rstrip("\r\n")
    version, status, reason = status_line.split(" ", 2)
    headers = read_headers(f)
    status = int(status)
    te = ", ".join(v for k, v in headers if k.lower() == "transfer-encoding").lower()
    cl = [v for k, v in headers if k.lower() == "content-length"]
    trailers = []
    if method == "HEAD" or status in (204, 304) or 100 <= status < 200:
        body = b""                                  # 規格規定這些回應沒有 body
    elif te:
        body, trailers = read_chunked(f)           # TE 優先於 CL
    elif cl:
        body = f.read(int(cl[0]))                  # 剛好讀這麼多，不多讀一個 byte
    else:
        body = f.read()                            # 只能讀到對方關閉連線
    return Response(version, status, reason, headers, body, trailers)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
host, port = server.server_address

with socket.create_connection((host, port), timeout=2) as sock:
    f = sock.makefile("rb")
    my_port = sock.getsockname()[1]
    for method, target in [("GET", "/api/classes/today"), ("GET", "/api/schedule/stream"),
                           ("HEAD", "/api/classes/today")]:
        r = request(sock, f, method, target, f"api.shengsheng.example:{port}")
        print(f"{r.version} {r.status} {r.reason}  ← {method} {target}")
        for name in ("Content-Type", "Content-Length", "Transfer-Encoding"):
            if r.header(name):
                print(f"  {name}: {r.header(name)}")
        print(f"  body   {len(r.body)} bytes: {r.body.decode()!r}")
        if r.trailers:
            print(f"  trailer {r.trailers}")
    f.close()

print(f"client 本地 port {my_port}；server 看到的 client port {seen_peers}")
assert seen_peers == [my_port] * 3          # 三個請求走同一條 TCP 連線
assert r.body == b"" and r.header("Content-Length") == "35"
server.shutdown()
server.server_close()
```

```text
HTTP/1.1 200 OK  ← GET /api/classes/today
  Content-Type: application/json; charset=utf-8
  Content-Length: 35
  body   35 bytes: '{"classes": 3, "teacher": "美咲"}'
HTTP/1.1 200 OK  ← GET /api/schedule/stream
  Content-Type: text/plain; charset=utf-8
  Transfer-Encoding: chunked
  body   39 bytes: '19:00 ja-101\n20:00 ja-102\n21:00 en-201\n'
  trailer [('X-Row-Count', '3')]
HTTP/1.1 200 OK  ← HEAD /api/classes/today
  Content-Length: 35
  body   0 bytes: ''
client 本地 port 59970；server 看到的 client port [59970, 59970, 59970]
```

逐段對照輸出。第一個回應帶 `Content-Length: 35`，client 剛好讀 35 bytes，其中「美咲」佔 6 bytes，所以字元數比 byte 數少；讀完就回傳，不等 EOF，這就修好了故事裡的 75 秒。第二個回應沒有 Content-Length，而是 `Transfer-Encoding: chunked`，`read_chunked()` 依序讀出三個 13 bytes 的 chunk，組成 39 bytes 的 body，並在 last-chunk 之後讀到 trailer `X-Row-Count: 3`；body 裡沒有任何十六進位的長度字樣，這就修好了 `1f4` 的問題。

第三個請求是 HEAD：回應帶著 `Content-Length: 35`，但 body 是 0 bytes。如果 `request()` 沒有先檢查 method，而是照 Content-Length 去讀 35 bytes，就會卡在 `f.read(35)` 直到 2 秒的 socket timeout。最後一行是 keep-alive 的證據：server 看到的三個 client port 都和 client 的本地 port 相同，三個請求共用一條連線、只做了一次交握。

程式有兩個刻意的設計。`sock.makefile("rb")` 提供帶緩衝的讀取，多收到的 bytes 會留給下一個回應；自己用 `recv()` 切邊界時，最常見的 bug 就是把下一個回應的開頭吃進這一個。`readline(8192)` 則設了單行上限，避免被壞掉的 server 耗盡記憶體，`http.client` 也有類似的限制。

### 實驗二：Host header 與虛擬主機

第二段在同一個 IP 與 port 上放兩個虛擬主機，依 Host 決定回哪個網站，並套用 RFC 9112 的規則與允許清單。最後用 `/reset-link` 示範「產生絕對網址時不相信 Host」。

```python
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 同一個 IP:port 上的兩個「虛擬主機」，用 Host header 區分
SITES = {"www.shengsheng.example": b"<h1>shengsheng www</h1>",
         "api.shengsheng.example": b'{"status": "ok"}'}
CANONICAL = "www.shengsheng.example"  # 產生絕對網址時只用設定值


class VHostHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        hosts = self.headers.get_all("Host") or []
        if self.request_version == "HTTP/1.1" and len(hosts) != 1:
            return self.reply(400, b"need exactly one Host")  # RFC 9112：缺少或重複都回 400
        name = hosts[0].rsplit(":", 1)[0].lower() if hosts else ""  # 名稱不分大小寫，去掉 port
        if name not in SITES:
            return self.reply(421, b"not served here")  # 不在允許清單的 Host 一律拒絕
        if self.path == "/reset-link":
            # 寄給使用者的絕對網址用設定值組出來，不用請求裡的 Host
            return self.reply(200, f"https://{CANONICAL}/reset?token=t0k3n".encode())
        self.reply(200, SITES[name])

    def log_message(self, *args):
        pass


def raw(port, head):
    with socket.create_connection(("127.0.0.1", port), timeout=2) as s:
        s.sendall(head.encode() + b"Connection: close\r\n\r\n")
        data = b""
        while chunk := s.recv(4096):
            data += chunk
    status = data.split(b"\r\n", 1)[0].decode()
    body = data.split(b"\r\n\r\n", 1)[1].decode()
    return status, body


server = ThreadingHTTPServer(("127.0.0.1", 0), VHostHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
port = server.server_address[1]

cases = [
    ("Host: www", "GET / HTTP/1.1\r\nHost: www.shengsheng.example\r\n"),
    ("Host: api", "GET / HTTP/1.1\r\nHost: api.shengsheng.example\r\n"),
    ("Host 大寫加 port", f"GET / HTTP/1.1\r\nHost: API.ShengSheng.example:{port}\r\n"),
    ("沒有 Host", "GET / HTTP/1.1\r\n"),
    ("兩個 Host", "GET / HTTP/1.1\r\nHost: www.shengsheng.example\r\nHost: api.shengsheng.example\r\n"),
    ("未知 Host", "GET / HTTP/1.1\r\nHost: shengsheng-mirror.invalid\r\n"),
    ("HTTP/1.0 沒有 Host", "GET / HTTP/1.0\r\n"),
]
results = {}
for label, head in cases:
    status, body = raw(port, head)
    results[label] = status.split()[1]
    print(f"{label} → {status} | {body}")

for host in ("www.shengsheng.example", "attacker.invalid"):
    status, body = raw(port, f"GET /reset-link HTTP/1.1\r\nHost: {host}\r\n")
    results[host] = body
    print(f"/reset-link（Host: {host}）→ {status} | {body}")

assert results["Host: www"] == results["Host: api"] == "200"
assert results["沒有 Host"] == results["兩個 Host"] == "400"
assert results["未知 Host"] == "421" and results["HTTP/1.0 沒有 Host"] == "421"
assert results["www.shengsheng.example"].startswith("https://www.shengsheng.example/")
assert results["attacker.invalid"] == "not served here"
server.shutdown()
server.server_close()
```

```text
Host: www → HTTP/1.1 200 OK | <h1>shengsheng www</h1>
Host: api → HTTP/1.1 200 OK | {"status": "ok"}
Host 大寫加 port → HTTP/1.1 200 OK | {"status": "ok"}
沒有 Host → HTTP/1.1 400 Bad Request | need exactly one Host
兩個 Host → HTTP/1.1 400 Bad Request | need exactly one Host
未知 Host → HTTP/1.1 421 Misdirected Request | not served here
HTTP/1.0 沒有 Host → HTTP/1.1 421 Misdirected Request | not served here
/reset-link（Host: www.shengsheng.example）→ HTTP/1.1 200 OK | https://www.shengsheng.example/reset?token=t0k3n
/reset-link（Host: attacker.invalid）→ HTTP/1.1 421 Misdirected Request | not served here
```

前三行證明虛擬主機的運作：同一個 IP:port，`Host` 不同就得到不同網站；主機名稱不分大小寫，port 在比對前被拿掉。第四、五行是 RFC 9112 的強制規則：HTTP/1.1 請求缺少 Host 或有兩個 Host，一律 400。第六行是允許清單：不認識的 Host 被拒絕，這裡回 421 表示「這台 server 不負責這個名稱」，實務上也常見 400、404 或 nginx 的 444，重點是**不要**把它交給預設的應用程式處理。

第七行是 HTTP/1.0 的請求：HTTP/1.0 不要求 Host，所以沒有被 400 擋下，但因為沒有名稱可以比對，仍然被允許清單拒絕。最後兩行是 Host header 攻擊的防禦：合法的 Host 拿到的重設連結使用設定檔裡的正式網域；`Host: attacker.invalid` 在入口就被擋下，根本到不了產生連結的程式。即使允許清單哪天被設錯，連結的網域也不會被請求左右，這是兩層防禦的意義。

### 實驗三：stale 連線、method 語意與 idempotency key

第三段重現故事裡的重複預約。server 的閒置逾時是 0.2 秒（縮小版的 keepalive timeout），並用故障注入模擬「每個 client 的第一個 POST 寫入資料庫後、送出回應前 worker 掛掉」。client 的重試策略只對 idempotent 的 method，或帶了 `Idempotency-Key` 的請求自動重送一次；`retry_any=True` 則模擬小晴原本「失敗就重送」的包裝。

```python
import itertools
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

IDEMPOTENT = {"GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE"}
bookings = []            # server 端真正寫入的預約
replies_by_key = {}      # Idempotency-Key → 第一次的回應
crashed_for = set()      # 故障注入：每個 client 的第一個 POST「做完了，但回應丟了」
lock = threading.Lock()
ids = itertools.count(1001)


class BookingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    timeout = 0.2        # 閒置 0.2 秒就關閉 keep-alive 連線（縮小版的 keepalive_timeout）

    def send_body(self, status, body):
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send_body(200, f"bookings={len(bookings)}".encode())

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        key = self.headers.get("Idempotency-Key")
        with lock:
            if key in replies_by_key:          # 同一個 key 重送：不重做，回同一個結果
                return self.send_body(201, replies_by_key[key])
            booking_id = next(ids)
            bookings.append(booking_id)        # 先寫入資料庫……
            reply = f"booking_id={booking_id}".encode()
            if key:
                replies_by_key[key] = reply
            agent = self.headers.get("User-Agent")
            crash = agent not in crashed_for
            crashed_for.add(agent)
        if crash:                              # ……回應還沒送出 worker 就掛了
            self.close_connection = True
            return
        self.send_body(201, reply)

    def log_message(self, *args):
        pass


class Client:
    def __init__(self, port, name, retry_any=False):
        self.addr, self.name, self.retry_any, self.sock = ("127.0.0.1", port), name, retry_any, None

    def _send_once(self, head, body):
        if self.sock is None:
            self.sock = socket.create_connection(self.addr, timeout=2)
            self.f = self.sock.makefile("rb")
        self.sock.sendall(head + body)
        status_line = self.f.readline()
        if not status_line:                    # 對方關了連線：請求到底有沒有被處理？不知道
            raise ConnectionError("連線被關閉，沒有收到回應")
        length = 0
        while (line := self.f.readline()) != b"\r\n":
            name, _, value = line.decode().partition(":")
            if name.lower() == "content-length":
                length = int(value)
        return status_line.split()[1].decode(), self.f.read(length).decode()

    def call(self, method, path, body=b"", key=None):
        head = f"{method} {path} HTTP/1.1\r\nHost: api.shengsheng.example\r\nUser-Agent: {self.name}\r\nContent-Length: {len(body)}\r\n"
        head += (f"Idempotency-Key: {key}\r\n" if key else "") + "\r\n"
        retryable = self.retry_any or method in IDEMPOTENT or key is not None
        for attempt in (1, 2):
            try:
                return self._send_once(head.encode(), body) + (attempt,)
            except (ConnectionError, OSError) as exc:
                self.sock = None               # 這條連線不能再用了
                if attempt == 2 or not retryable:
                    return "ERR", str(exc), attempt


server = ThreadingHTTPServer(("127.0.0.1", 0), BookingHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
port = server.server_address[1]

c = Client(port, "A")
print("A. 重用閒置過久的連線:", c.call("GET", "/v1/bookings")[0])
time.sleep(0.35)                               # 超過 server 的閒置逾時，連線已被關掉
print("   閒置後同一條連線再送:", c.call("GET", "/v1/bookings"))

print("B. POST 不帶 key，不重試:", Client(port, "B").call("POST", "/v1/bookings", b"lesson=ja-101"))
print("C. POST 不帶 key，盲目重試:", Client(port, "C", retry_any=True).call("POST", "/v1/bookings", b"lesson=ja-101"))
print("D. POST 帶 Idempotency-Key 重試:", Client(port, "D").call("POST", "/v1/bookings", b"lesson=ja-101", key="7f3c-b2"))
print("   server 端實際寫入的預約:", bookings)

assert len(bookings) == 4          # B 寫了一筆（但 client 不知道）、C 寫了兩筆、D 只寫一筆
server.shutdown()
server.server_close()
```

```text
A. 重用閒置過久的連線: 200
   閒置後同一條連線再送: ('200', 'bookings=0', 2)
B. POST 不帶 key，不重試: ('ERR', '連線被關閉，沒有收到回應', 1)
C. POST 不帶 key，盲目重試: ('201', 'booking_id=1003', 2)
D. POST 帶 Idempotency-Key 重試: ('201', 'booking_id=1004', 2)
   server 端實際寫入的預約: [1001, 1002, 1003, 1004]
```

A 段是 20.8 節的競態：client 等了 0.35 秒，超過 server 的 0.2 秒閒置逾時，連線已經被 server 關閉；client 在這條連線上送出 GET，讀到 EOF，因為 GET 是 idempotent，client 開新連線重送，第 2 次嘗試成功（輸出最後的 `2` 是嘗試次數）。這正是瀏覽器與連線池在背後默默做的事，也說明為什麼只能對 idempotent 的請求這樣做。

B 段是 POST 遇到故障：client 收到「連線被關閉，沒有收到回應」，依規則**不重試**，而是把「結果未知」交給上層。注意此時 server 其實已經寫入了預約 1001，client 卻不知道，這就是 20.4 節的情況 B。C 段是小晴原本的寫法：第一次嘗試寫入 1002 後回應丟失，盲目重送又寫入 1003，同一個操作產生兩筆預約，正是 Rita 在對帳報表上看到的 37 筆重複。D 段帶著 `Idempotency-Key: 7f3c-b2`：第一次嘗試寫入 1004 並記下結果，重送時 server 認出同一個 key，直接回傳 `booking_id=1004`，沒有寫第二筆。最後一行列出 server 端真正寫入的四筆預約，和以上分析完全吻合。

### 實驗四：嚴格解析訊息邊界

最後一段是 Rita 要求的防禦：一個依 RFC 9112 決定 request body 長度、遇到任何模糊情況都拒絕的函式，並對照兩個「各自看起來都合理」的寬鬆解析器，說明 smuggling 的成因。程式只判斷 header，不處理也不構造任何夾帶的內容。

```python
import re

TOKEN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")  # header 名稱允許的字元


class BadRequest(Exception):
    pass


def parse_head(raw: bytes):
    """解析請求的 start line 與 header，回傳 (version, fields)。"""
    lines = raw.decode("latin-1").split("\r\n")
    method, target, version = lines[0].split(" ")
    fields = []
    for line in lines[1:]:
        if line[:1] in (" ", "\t"):
            raise BadRequest("obs-fold：header 折行已被廢止")
        name, sep, value = line.partition(":")
        if not sep or not TOKEN.match(name):
            raise BadRequest(f"header 名稱不合法：{name!r}")  # 含「名稱與冒號之間的空白」
        fields.append((name.lower(), value.strip(" \t")))
    return version, fields


def body_framing(raw: bytes):
    """依 RFC 9112 的規則決定 request body 怎麼切；任何模糊情況都拒絕。"""
    version, fields = parse_head(raw)
    te = [v for n, v in fields if n == "transfer-encoding"]
    cl = [v for n, v in fields if n == "content-length"]
    if te and cl:
        raise BadRequest("同時有 Transfer-Encoding 與 Content-Length")
    if te:
        if version != "HTTP/1.1":
            raise BadRequest("HTTP/1.0 不支援 chunked")
        codings = [c.strip().lower() for c in ",".join(te).split(",")]
        if codings != ["chunked"]:
            raise BadRequest(f"不支援的 transfer coding：{codings}")
        return "chunked"
    if cl:
        values = {v.strip() for v in ",".join(cl).split(",")}
        if len(cl) > 1 or len(values) != 1:
            raise BadRequest(f"Content-Length 重複：{cl}")
        value = values.pop()
        if not value.isdigit() or not value.isascii():
            raise BadRequest(f"Content-Length 不是十進位數字：{value!r}")
        return int(value)
    return 0  # 請求沒有 CL 也沒有 TE：body 長度就是 0，不能「讀到關閉」


H = "POST /v1/bookings HTTP/1.1\r\nHost: api.shengsheng.example\r\n"
cases = {
    "只有 Content-Length": H + "Content-Length: 13",
    "只有 chunked": H + "Transfer-Encoding: chunked",
    "沒有 body 資訊": H.rstrip("\r\n"),
    "CL 與 TE 並存": H + "Content-Length: 13\r\nTransfer-Encoding: chunked",
    "兩個不同的 CL": H + "Content-Length: 13\r\nContent-Length: 7",
    "兩個相同的 CL": H + "Content-Length: 13\r\nContent-Length: 13",
    "CL 帶正負號": H + "Content-Length: +13",
    "TE 不是 chunked 結尾": H + "Transfer-Encoding: chunked, gzip",
    "TE 拼字變形": H + "Transfer-Encoding: xchunked",
    "名稱與冒號間有空白": H + "Transfer-Encoding : chunked",
    "header 折行": H + "Content-Length: 13\r\n  extra",
    "HTTP/1.0 用 chunked": H.replace("1.1", "1.0") + "Transfer-Encoding: chunked",
}
verdicts = {}
for label, head in cases.items():
    try:
        verdicts[label] = f"接受，body = {body_framing(head.encode())}"
    except BadRequest as exc:
        verdicts[label] = f"400，{exc}"
    print(f"{label} → {verdicts[label]}")

accepted = [k for k, v in verdicts.items() if v.startswith("接受")]
assert accepted == ["只有 Content-Length", "只有 chunked", "沒有 body 資訊"]


# 兩個「寬鬆」的解析器：各自看起來都合理，放在一起就會對 body 長度意見不同
def proxy_view(raw):          # 前端：名稱嚴格比對、只看 Content-Length 的第一個值
    _, fields = parse_head_lenient(raw, strip_names=False)
    cl = [v for n, v in fields if n == "content-length"]
    return int(cl[0]) if cl else 0


def backend_view(raw):        # 後端：名稱先去空白、TE 優先、CL 取最後一個值
    _, fields = parse_head_lenient(raw, strip_names=True)
    if any("chunked" in v.lower() for n, v in fields if n == "transfer-encoding"):
        return "chunked"
    cl = [v for n, v in fields if n == "content-length"]
    return int(cl[-1]) if cl else 0


def parse_head_lenient(raw, strip_names):
    lines = raw.decode("latin-1").split("\r\n")
    fields = []
    for line in lines[1:]:
        name, _, value = line.partition(":")
        fields.append(((name.strip() if strip_names else name).lower(), value.strip()))
    return lines[0], fields


print()
for label in ("CL 與 TE 並存", "兩個不同的 CL", "名稱與冒號間有空白"):
    raw = cases[label] if label != "名稱與冒號間有空白" else cases[label] + "\r\nContent-Length: 13"
    a, b = proxy_view(raw.encode()), backend_view(raw.encode())
    print(f"{label}：proxy 認為 body = {a}，backend 認為 body = {b} → {'一致' if a == b else '不一致'}")
    assert a != b
```

```text
只有 Content-Length → 接受，body = 13
只有 chunked → 接受，body = chunked
沒有 body 資訊 → 接受，body = 0
CL 與 TE 並存 → 400，同時有 Transfer-Encoding 與 Content-Length
兩個不同的 CL → 400，Content-Length 重複：['13', '7']
兩個相同的 CL → 400，Content-Length 重複：['13', '13']
CL 帶正負號 → 400，Content-Length 不是十進位數字：'+13'
TE 不是 chunked 結尾 → 400，不支援的 transfer coding：['chunked', 'gzip']
TE 拼字變形 → 400，不支援的 transfer coding：['xchunked']
名稱與冒號間有空白 → 400，header 名稱不合法：'Transfer-Encoding '
header 折行 → 400，obs-fold：header 折行已被廢止
HTTP/1.0 用 chunked → 400，HTTP/1.0 不支援 chunked

CL 與 TE 並存：proxy 認為 body = 13，backend 認為 body = chunked → 不一致
兩個不同的 CL：proxy 認為 body = 13，backend 認為 body = 7 → 不一致
名稱與冒號間有空白：proxy 認為 body = 13，backend 認為 body = chunked → 不一致
```

前三行是唯一被接受的三種情況：只有 Content-Length、只有 chunked，以及兩者都沒有（body 長度為 0）。接下來九行全部回 400，對應 20.9 節表格的每一列：CL 與 TE 並存、兩個 Content-Length（就算值相同也拒絕，這比規格要求的更嚴，和 gunicorn 的新版行為一致）、帶正負號的數字（`int("+13")` 在 Python 會成功，所以要用 `isdigit()` 自己檢查）、最後不是 chunked 的 TE、拼錯的 TE、名稱與冒號間的空白、obs-fold 折行，以及 HTTP/1.0 的 chunked。

最後三行是成因的示範：同一段 header，「前端」只認完全相符的名稱、只看第一個 Content-Length，「後端」會先去掉名稱的空白、TE 優先、取最後一個 Content-Length。兩者各自都說得通，對 body 長度的判斷卻不同，這就是 20.9 節那張圖左右兩欄的分歧。如果兩層都換成上面的嚴格函式，三個例子都會在第一層被 400 擋下，分歧根本沒有機會出現。

## 20.11 在工作上怎麼用

探針改寫完成後，阿德請小晴把這次學到的整理成團隊的檢查清單，依角色分工。

**後端工程師：設計 API 時守住 method 的承諾。** 讀取用 GET，絕不在 GET 裡改狀態；建立資源用 POST 並支援 `Idempotency-Key`，尤其是預約、付款、寄信這種「做兩次會出事」的操作；整體取代用 PUT，部分修改用 PATCH。錯誤的 status code 要選對家族：請求本身的問題用 4xx 並附上機器可讀的錯誤內容，伺服器的問題才用 5xx。回應一定要有明確的長度（框架通常會自動處理），串流回應確認中間的 nginx 沒有把它整個緩衝起來（`X-Accel-Buffering: no` 或 `proxy_buffering off`，第 31 章）。

**SRE：用 curl 直接看線路上的 HTTP/1.1。** 下面幾個指令能回答本章大部分的問題（示意，需要網路與實際主機）：

```bash
curl -sv --http1.1 https://api.shengsheng.example/healthz -o /dev/null      # 看請求行、Host、狀態行與 header
curl -sv --http1.1 https://api.shengsheng.example/a https://api.shengsheng.example/b 2>&1 | grep -i 're-using\|connected'
                                                                          # 兩個 URL 是否重用同一條連線
curl -s --raw --http1.1 https://api.shengsheng.example/api/schedule/stream | head   # --raw：不解碼 chunked，看見 chunk-size
curl -sv -H 'Host: unknown.invalid' https://203.0.113.80/ -k -o /dev/null  # 未知 Host 是否被 default_server 擋下
printf 'GET / HTTP/1.1\r\nHost: api.shengsheng.example\r\n\r\n' | nc 10.20.3.21 8000   # 繞過 nginx 直接打 gunicorn
```

第一個指令的 `-v` 會把送出的請求（以 `>` 開頭）與收到的回應 header（以 `<` 開頭）都印出來，是確認「實際送了什麼 Host、收到哪個 status」最快的方法。第二個指令一次給兩個 URL，curl 會嘗試重用連線，輸出中的「Re-using existing connection」證明 keep-alive 有效。第三個的 `--raw` 讓你看到 chunked 的原貌，對照 20.7 節的圖。第四個指令驗證允許清單；第五個用 `nc` 繞過 nginx，用來判斷問題出在 nginx 還是 gunicorn。

判斷「HTTP 請求失敗」的流程可以畫成這樣：

```text
 症狀：請求失敗或結果不對
   │
   ├─ 根本沒有 HTTP 回應（連線被拒、逾時、reset、EOF）
   │     ├─► TCP／TLS 層的問題：回到第 10、18 章
   │     └─► 在重用的連線上發生？ ── 是 ─► 閒置逾時競態：idempotent 才重試，對齊各層 keep-alive
   │
   ├─ 收到回應，但 client 卡住或內容錯亂
   │     └─► 訊息邊界：HEAD／204／304 誤讀 body？chunked 沒解碼？讀到 EOF 才停？
   │
   ├─ 4xx
   │     ├─► 400：Host、header 格式、CL／TE 衝突（新版 server 更嚴格）
   │     ├─► 404／421：Host 是否打到正確的虛擬主機
   │     └─► 413／431：body 或 header 太大（cookie 累積）
   │
   └─ 5xx
         ├─► 502／504：nginx 產生的，看上游 log 與 x-request-id；請求可能其實成功了
         └─► 500：應用程式例外，看 Flask 的 traceback
```

這張流程的第一刀是「有沒有 HTTP 回應」：沒有回應的錯誤屬於 TCP、TLS 層，HTTP 的 status code 根本還沒出現。第二刀是看回應能不能被正確解析。之後才依 status code 的家族分流。最右下角的提醒值得一再強調：502 與 504 的請求，資料庫裡可能已經有結果，處理客訴與重送前要先查證。

**前端工程師：讀懂瀏覽器替你做的事。** 在 DevTools 的 Network 面板打開「Connection ID」與「Protocol」欄位，就能看到哪些請求共用一條連線、走的是 `http/1.1` 還是 `h2`。使用者連點送出、或網路不穩時重送表單，同樣會產生重複預約，所以送出按鈕要防連點，同一次操作重送時要帶同一個 idempotency key。

**資安工程師：把邊界解析當成攻擊面。** Rita 的檢查清單：入口的 proxy 對 CL／TE 衝突、重複 Host、非法 header 一律回 400 並關連線；nginx 有明確的 `server_name` 與拒絕一切的 `default_server`；應用程式產生絕對網址時只用設定檔的網域；所有 proxy 與 application server 保持更新；定期比對各層的請求數量與 400 數量，作為 smuggling 的偵測訊號。審查自寫的 HTTP 解析器時，看到「寬容」的處理（去掉名稱空白、取第一個值、忽略無法解析的行）就要提問。

## 20.12 常見錯誤與除錯

下表收錄與 HTTP/1.1 訊息格式、method 語意與連線重用相關、在聲聲 Live 與一般團隊最常見的錯誤。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 自寫 client 每個請求都卡一段固定時間（例如 75 秒、5 秒） | 讀回應時等 EOF，沒有依 Content-Length 或 chunked 判斷結束；卡住的時間等於 server 的 keep-alive timeout | 卡住的秒數剛好等於對方的 keepalive 設定；tcpdump 看到回應早就收完，最後才有 FIN | 依 20.7 節的流程讀 body；或直接用 `http.client` 等現成的 client |
| 回應內容開頭出現 `1f4`、`2000` 之類的字串 | chunked 沒有解碼，把 chunk-size 當成資料 | `curl --raw` 看到相同的字串；回應 header 有 `Transfer-Encoding: chunked` | 實作 chunked 解碼，或改用會處理它的函式庫 |
| HEAD 請求或 304 回應後，client 卡住或下一個回應錯亂 | 照 Content-Length 讀了一個不存在的 body | 只在 HEAD、204、304 發生；抓包看到 server 沒有送 body | 先依 method 與 status 判斷「沒有 body」，再看長度 header |
| 偶發重複的預約或扣款 | 對 POST 自動重試，或使用者重複送出；第一次其實已經成功 | 重複的兩筆時間相差約一個逾時或重試間隔；nginx 有對應的 502／504 或 499 | 只對 idempotent 的請求自動重試；POST 加 `Idempotency-Key` 並在 server 端去重 |
| 閒置一段時間後的第一個請求偶爾失敗（`RemoteDisconnected`、`ECONNRESET`） | client 重用了 server 剛因閒置逾時關閉的連線 | 失敗都是閒置後的第一個請求；client 池的閒置上限比 server 的 keep-alive timeout 長 | client 閒置上限設得比 server 短；對 idempotent 請求在新連線上重試一次 |
| 打 API 拿到網站首頁、404，或別的服務的回應 | Host 錯誤或缺少：用 IP 直接打、proxy 改寫了 Host、`default_server` 指錯 | `curl -v` 看送出的 Host；nginx access log 記錄 `$host` | 送正確的 Host；nginx 設明確的 `server_name` 與拒絕一切的 `default_server` |
| 升級 gunicorn 或 proxy 後，某些 client 開始收到 400 | 新版拒絕 CL 與 TE 並存、重複 Host、HTTP/1.0 chunked 等模糊請求 | 錯誤集中在特定 User-Agent；抓包看請求是否不合規 | 修 client；不要為了相容而降低 server 的嚴格程度 |
| 每個請求莫名多出約 40 毫秒 | header 與 body 分兩次小量 send，Nagle 與 delayed ACK 互相等待 | 延遲穩定在 40 毫秒附近；抓包看到第二個 segment 等 ACK 才送 | 一次送出整個訊息，或設 `TCP_NODELAY` |
| 開發用的 `http.server` 每個請求都重新連線 | `protocol_version` 預設是 HTTP/1.0 | 回應狀態行是 `HTTP/1.0`；`ss` 看到大量 TIME_WAIT | 設 `protocol_version = "HTTP/1.1"`，並確保每個回應都有 Content-Length |
| 上傳大檔案得到 413，或 header 太大得到 400／431 | 超過 nginx 的 `client_max_body_size` 或 header buffer 上限；cookie 累積過多 | 錯誤由 nginx 產生，Flask 沒有 log；檢查請求的 cookie 大小 | 調整上限或改用直傳物件儲存；清理不必要的 cookie |

除錯 HTTP/1.1 的通則是：**先看線路上的 bytes，再看程式**。`curl -v`、`curl --raw` 與 `nc` 讓每個 header 與 chunk 現形。

## 20.13 動手練習

1. **擴充實驗一：處理 1xx 與 `Connection: close`。** 讓 server 對某個路徑先送 `HTTP/1.1 103 Early Hints` 再送最終回應，並讓另一個路徑回應時帶 `Connection: close`。修改 `request()`，讓它略過 1xx、回傳最終回應，並在看到 `Connection: close` 時標記這條連線不能再用。
   答案要點：讀到 1xx 狀態行與其 header 後，回到「讀狀態行」的步驟繼續讀（1xx 沒有 body）；`Connection` 的值要不分大小寫、以逗號切開比對 `close`。驗證方法是用 `assert` 檢查最終 status 是 200，以及帶 close 的回應之後，client 會開新連線（server 記到新的 client port）。

2. **用真實工具觀察 keep-alive 與 chunked。** 執行 `python3 -m http.server 8765 --bind 127.0.0.1`，用 `curl -v --http1.1 127.0.0.1:8765/ 127.0.0.1:8765/` 送兩個請求；接著把實驗一的 server 單獨跑起來（加一個 `input()` 讓它不要結束），用 `curl --raw` 打 `/api/schedule/stream`。
   答案要點：`http.server` 的命令列模式回應的狀態行是 `HTTP/1.0`，curl 會顯示連線在第一個回應後關閉、第二個 URL 重新連線；`--raw` 會看到 `d`、`0` 等 chunk-size 與 trailer。對照 20.7 節的圖確認每一行。

3. **擴充實驗三：idempotency key 的邊界情況。** 讓同一個 `Idempotency-Key` 搭配**不同的 body** 重送（例如改了課程代號），server 應該怎麼處理？再思考：同一個 key 的兩個請求**同時**抵達時，目前的程式會不會出錯？
   答案要點：同 key 不同內容是 client 的 bug，應回 4xx（常見 409 或 422）而不是回舊結果，所以 server 要連同請求內容的 hash 一起存；併發時，實驗中的 `lock` 讓「檢查 key」與「寫入」不可分割，真實系統要用資料庫的唯一索引或交易達到同樣的效果（第 24 章）。

4. **用 nc 驗證 Host 規則。** 在本機跑實驗二的 server（同樣加 `input()`），用 `printf 'GET / HTTP/1.1\r\n\r\n' | nc 127.0.0.1 <port>` 與 `printf 'GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n' | nc 127.0.0.1 <port>` 送出缺少與重複 Host 的請求，再改成對 `python3 -m http.server` 送同樣的內容，比較兩者的反應。
   答案要點：實驗二的 server 兩者都回 400；標準函式庫的 `http.server` 不檢查 Host，會照常回應。這說明「規格要求」不等於「每個實作都做到」，所以入口的 proxy 必須嚴格把關，不能假設後端會拒絕。

5. **手算 chunked 的 bytes。** 一個 chunked body 依序是 3 個 chunk，資料長度分別為 500、4096、17 bytes，沒有 extension，沒有 trailer。整個 body（從第一個 chunk-size 到最後的空行）在線路上佔多少 bytes？如果改用 Content-Length，header 需要寫什麼值？
   答案要點：chunk-size 是十六進位 `1f4`（3 bytes）、`1000`（4 bytes）、`11`（2 bytes），每個 chunk 額外有 size 後與資料後兩個 CRLF（4 bytes），所以 3 個 chunk 的額外負擔是 3＋4＋2＋3×4＝21 bytes；last-chunk `0\r\n` 是 3 bytes，最後的空行 2 bytes。總計 4613＋21＋5＝4639 bytes。改用 Content-Length 時值是 4613，只計算資料本身。

## 本章重點整理

- HTTP/1.1 是建在 TCP byte stream 上的文字協定，每個訊息由起始行、header、空行與可選的 body 組成，每一行以 CRLF 結束；body 之後沒有結束記號，邊界全靠長度規則。
- 語意（RFC 9110）與 HTTP/1.1 的線路格式（RFC 9112）是分開定義的，method、status code 與大部分 header 的意思在 HTTP/2、HTTP/3 中不變。
- 請求行是「method、request-target、版本」三段；header 名稱不分大小寫，名稱與冒號之間不能有空白，obs-fold 已廢止，`Host` 與 `Content-Length` 這類單值 header 不能重複。
- safe 的 method（GET、HEAD、OPTIONS、TRACE）不應改變 server 狀態；idempotent 的 method（再加上 PUT、DELETE）送多次與送一次效果相同；POST 與 PATCH 兩者都不是。
- 「送出但沒收到回應」時，client 無法分辨請求是否已被處理，所以只能自動重試 idempotent 的請求；POST 需要重試時用 idempotency key 讓 server 去重。
- status code 的第一位數字指出該找誰：4xx 是請求本身的問題，5xx 是處理方的問題，其中 502、504 由 proxy 產生，請求可能其實已經成功；程式只看數字，不看 reason phrase。
- Host header 讓同一個 IP 服務多個網站；HTTP/1.1 請求缺少或重複 Host 必須回 400；Host 由 client 自填，要用允許清單過濾，產生絕對網址時只用設定檔的網域。
- 判斷 body 長度的優先順序是：HEAD、1xx、204、304 沒有 body；其次 chunked；再其次 Content-Length；請求兩者都沒有就是 0，回應才能讀到連線關閉。
- chunked 用十六進位的 chunk-size 標示每一塊，以長度 0 的 last-chunk 結束，之後可以接 trailer；它讓 server 不必先知道總長度，但只存在於 HTTP/1.1。
- HTTP/1.1 預設保持連線，省下重複的 TCP 與 TLS 交握；`Connection: close` 表示這個訊息後關閉，`Connection` 與它列出的 header 都是 hop-by-hop。
- 持久連線有閒置逾時的競態：client 的閒置上限要短於 server 的 keep-alive timeout，在重用連線上失敗時只重試 idempotent 的請求。
- pipelining 因 head-of-line blocking 與 proxy 相容性問題幾乎沒有被瀏覽器採用，瀏覽器改用每個 origin 約 6 條平行連線，這些限制由 HTTP/2 解決。
- request smuggling 的成因是路徑上兩個解析器對同一段 bytes 的訊息邊界判斷不同，典型來源是 CL 與 TE 並存、重複的 CL 與變形的 TE。
- 防禦 smuggling 的核心是讓整條路徑只有一種解讀：入口嚴格拒絕模糊的請求並關閉連線、正規化後再轉送、保持 proxy 與 server 更新、後端盡量用 HTTP/2。

## 延伸問答

> [!question]- Q1. GET 一定是 safe 的嗎？如果某個 GET 端點會寫入資料庫，它還算 safe 嗎？
> safe 是 method 的**語意承諾**，不是實作的保證。RFC 9110 的意思是：client 送 GET 時，不要求也不預期 server 改變狀態，所以 client 不必為這個請求造成的副作用負責。server 寫 access log、增加瀏覽次數、更新快取，都是 client 沒有要求的附帶效果，不影響 GET 的 safe 性質，因為重複執行它們不會傷害使用者。
>
> 但如果 GET 端點做的是使用者在意的狀態改變，例如 `GET /v1/bookings/1001/cancel` 會取消預約，那是 server 違反了承諾，後果由 server 承擔：瀏覽器預先載入、搜尋引擎爬蟲、聊天軟體的連結預覽、proxy 的自動重試，都會自由地送出 GET，結果就是預約被莫名取消。判斷標準是「這個副作用如果發生十次，使用者會不會在意」。會在意，就應該用 POST、PUT 或 DELETE，並加上適當的驗證與 CSRF 防護（第 23 章）。

> [!question]- Q2. 你在 production 看到 nginx 對 `POST /v1/payments` 回了 504，但金流供應商顯示扣款成功，客服要你「幫使用者再送一次」。你會怎麼處理？
> 不要重送。504 是 nginx 產生的，意思是「我在逾時內沒有等到上游的回應」，它完全不代表上游沒有處理。這正是 20.4 節的情況 B：gunicorn 可能還在等金流 API 回應時被 nginx 放棄，之後金流成功、資料庫也寫入了，只是回應來不及送回使用者。再送一次的結果很可能是重複扣款。
>
> 正確的步驟是先查證：用 `x-request-id` 串起 nginx 與 Flask 的 log，確認請求是否抵達應用程式、處理花了多久、最後的結果；再到資料庫與金流後台確認交易狀態。長期修正有三項：付款 API 支援 `Idempotency-Key`，讓 client 安全重試；對外部金流的呼叫本身也帶 idempotency key（多數金流 API 都支援）；調整 timeout 鏈，讓應用程式對下游的逾時短於 nginx 對上游的逾時，應用程式才有機會回傳明確的錯誤（第 43 章）。

> [!question]- Q3. 手算：一個回應的 header 是 `Content-Length: 12`，body 是 UTF-8 的「預約成功！」。client 照 Content-Length 讀，會發生什麼事？
> 「預約成功！」是 5 個字元，每個在 UTF-8 中都佔 3 bytes（全形驚嘆號也是），所以 body 實際上是 15 bytes。Content-Length 宣告 12，client 只會讀 12 bytes，得到前 4 個字「預約成功」，剩下的 3 bytes（全形驚嘆號）留在連線的緩衝區裡。
>
> 更嚴重的是下一個回應：client 在同一條連線上讀下一個狀態行時，會先讀到這 3 個殘留的 bytes，狀態行變成亂碼開頭，解析失敗或把訊息錯位，這正是邊界錯誤會「污染下一個訊息」的典型表現。反過來，如果 Content-Length 宣告得比實際多，client 會卡住等待永遠不會來的 bytes。這類 bug 通常來自用 `len(text)` 而不是 `len(text.encode())` 計算長度，所以 Content-Length 一定要對編碼後的 bytes 計算；用框架時讓框架自動計算最安全。

> [!question]- Q4. 面試題：HTTP/1.1 有 pipelining，為什麼瀏覽器還要開 6 條連線？HTTP/2 怎麼解決？
> pipelining 允許 client 不等回應就連送多個請求，但 server 必須**依請求順序**回應。只要第一個請求很慢（例如要查資料庫），後面已經處理好的回應也只能排在後面等，這是 HTTP 層的 head-of-line blocking。再加上很多 proxy 與 server 對 pipelining 的實作有 bug，而且連線中斷時 client 無法判斷哪些請求已被處理、哪些可以安全重送（非 idempotent 的請求尤其麻煩），瀏覽器最後都沒有預設啟用它。
>
> 瀏覽器的替代做法是每個 origin 開約 6 條平行連線，代價是更多交握、更多 slow start、對 server 與中間設備更大的連線壓力，網站又為了突破 6 條的限制發明了 domain sharding 等技巧。HTTP/2 的解法是 binary framing：每個請求是一個有編號的 stream，不同 stream 的 frame 可以在同一條連線上交錯送出，回應不必依序，HTTP 層的 head-of-line blocking 就消失了。不過 TCP 層的 head-of-line blocking 仍在，掉一個封包會卡住所有 stream，這是 HTTP/3 改用 QUIC 的原因（第 12、13、22 章）。

> [!question]- Q5. 看 log 找原因：監測程式偶爾印出 `http.client.RemoteDisconnected: Remote end closed connection without response`，幾乎都發生在相隔 3 秒以上的兩次檢查之間，平常則完全正常。可能是什麼？
> 錯誤訊息表示 client 送出請求後，連線被對方關閉，沒有收到任何回應的 byte。「只發生在閒置一段時間之後」是強烈的線索：這是 keep-alive 閒置逾時的競態。監測程式重用了上一次的連線，而 server 的 keep-alive timeout 比這段閒置時間短。如果監測程式是直接打 gunicorn（預設 keep-alive 2 秒），閒置超過 2 秒後 gunicorn 就關閉了連線，下一個請求正好送進一條已經關閉的連線。
>
> 確認方法是對照錯誤發生前的閒置時間與 server 的 keep-alive 設定，並用 tcpdump 觀察：server 會在閒置 2 秒時送出 FIN，client 卻在之後才送請求，換來 RST 或 EOF。修正方式有三個方向：讓 client 的連線池閒置上限短於 server 的 keep-alive timeout；對 idempotent 的請求遇到這個錯誤時開新連線重試一次；或者讓監測程式走 nginx（keep-alive 較長），但仍要處理競態，因為它無法完全消除。

> [!question]- Q6. 設計取捨：課表匯出 API 要回傳可能長達 50 MB 的 CSV，應該用 Content-Length 還是 chunked？
> 用 Content-Length，server 必須在送出 header 前知道總長度，通常代表先把整份 CSV 產生在記憶體或暫存檔裡。好處是 client 能顯示下載進度、能用 Range 請求續傳（第 21 章），也能可靠地偵測截斷：收到的 bytes 少於宣告值就是不完整。代價是首個 byte 要等整份資料產生完才送出，記憶體或磁碟用量也高；同時有很多匯出請求時，server 可能撐不住。
>
> 用 chunked，server 可以邊查資料庫邊送，記憶體用量固定，首個 byte 很快送出，對使用者感受較好。代價是 client 不知道總長度，進度條只能顯示已下載量；中途出錯時，狀態碼早已送出 200，server 只能中斷連線，client 要靠「沒收到 last-chunk」判斷不完整。常見的折衷是：資料量小的匯出用 Content-Length；大型匯出改成非同步工作，先回 202 Accepted，產生完再提供一個有 Content-Length、可以續傳的下載連結，同時避免長時間占住 worker 與受 timeout 鏈限制。

> [!question]- Q7. 情境判斷：同事說「我們前面有 CDN 與 nginx，後端 gunicorn 也是新版，所以 request smuggling 不用擔心」。你同意嗎？
> 只同意一半。新版 gunicorn 拒絕 CL 與 TE 並存、重複的 Content-Length 與 Host 等模糊請求，確實大幅縮小了風險；但 smuggling 的本質是**任兩層之間**的解析不一致，不是單一元件的漏洞。路徑上有 CDN、LB、nginx、gunicorn，就有三個交界面，任何一個交界面兩側的解讀不同都可能出問題，例如 CDN 與 nginx 之間的 HTTP/2 降版、或某一層對 chunk 格式的寬容處理。
>
> 合理的做法是逐一檢查：每個交界面用什麼協定（HTTP/2 還是 HTTP/1.1）、最前面的元件是否對模糊請求回 400 並關閉連線、proxy 是否正規化後再轉送、各元件的版本與安全公告是否跟上。偵測方面，監控各層的 400 數量、上游連線被意外關閉的次數，以及前後端請求數是否對得上。最後，不要在應用程式或自寫工具裡寫「寬容」的解析器，讓它成為新的不一致來源。

> [!question]- Q8. 為什麼 HTTP/1.1 的請求「沒有 Content-Length 也沒有 Transfer-Encoding」時，body 長度是 0，而回應卻可以讀到連線關閉為止？
> 「讀到連線關閉」需要送出方在送完後關閉連線。對回應而言這是可行的：server 送完 body 後關閉連線，client 讀到 EOF 就知道結束了，這是 HTTP/1.0 時代的標準做法，代價是連線不能重用，而且無法分辨「送完了」與「中途斷線」。
>
> 對請求而言這行不通：client 送完請求後還要等回應，如果它關閉連線（就算只用 `shutdown(SHUT_WR)` 半關閉，很多 server 也會把它當成 client 離開），就收不到回應，server 也無從判斷「body 結束了」與「client 還在送」。如果允許 server 一直等更多 body，任何沒帶長度的 POST 都會讓 server 卡住，形同可以輕易耗盡 worker 的漏洞。所以規格明確規定：請求必須用 Content-Length 或 chunked 宣告 body，兩者都沒有就代表沒有 body。這也讓 server 能在讀完 header 後立刻知道請求是否完整，是 keep-alive 能正常運作的前提。

## 延伸閱讀

- RFC 9110〈HTTP Semantics〉：method 的 safe 與 idempotent、status code、Host 與各種 header 的語意
- RFC 9112〈HTTP/1.1〉：訊息格式、body 長度的判斷規則、chunked、連線管理與 smuggling 相關的安全考量
- RFC 5789〈PATCH Method for HTTP〉：PATCH 的定義與非 idempotent 的說明
- RFC 8297〈An HTTP Status Code for Indicating Hints〉：103 Early Hints
- Python 官方文件：`http.server`、`http.client`、`socket` 模組
- nginx 官方文件：`ngx_http_core_module`（keepalive_timeout、client_max_body_size、server_name）與 `ngx_http_upstream_module`（keepalive）
- MDN Web Docs：HTTP 指南中的 Messages、Methods 與 Status codes 章節
