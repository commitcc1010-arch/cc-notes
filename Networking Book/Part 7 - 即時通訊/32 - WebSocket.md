---
chapter: 32
title: WebSocket 深入
part: 7
---

# 第 32 章　WebSocket 深入

> [!abstract] 本章地圖
> **核心問題**：一條 WebSocket 連線從一個 HTTP 請求「升級」之後，線上到底在傳什麼？要怎麼讓它在 proxy、LB、惡意網站與超大訊息之間活得安全又穩定？
>
> **你會學到**：
> - 逐行讀懂 HTTP Upgrade 握手，手算 `Sec-WebSocket-Accept` 並用 RFC 6455 的範例值驗證，說清楚它防什麼、不防什麼
> - 逐 bit 讀懂 WebSocket frame（FIN、RSV、opcode、MASK、7／16／64-bit payload length、masking key），自己寫出編解碼器
> - 解釋 client 為什麼一定要 mask、訊息與 frame 的差別、分片時 ping 為什麼能插隊，以及 UTF-8 要在哪一層驗證
> - 設計心跳、close handshake 與 close code 的處理方式，讓前端知道「什麼時候該重連、什麼時候不該」
> - 用 Origin 允許清單、cookie 或一次性 ticket 做認證，並在連線期間持續授權；替訊息大小、分片與壓縮設定上限
> - 用 Python asyncio 在 127.0.0.1 上從零實作 WebSocket server 與 client，重現協定錯誤、訊息過大與殭屍連線
>
> **前置知識**：第 10 章（TCP 連線的建立與關閉、TIME_WAIT）、第 11 章（byte stream 與 framing）、第 20 章（HTTP/1.1 訊息格式）、第 22 章（HTTP/2 的 stream 與 SETTINGS）、第 23 章（origin、CORS 與 cookie 的 SameSite）、第 27 章（JWT 與短效 token）、第 31 章（polling 與 SSE）

## 32.1 故事：貼上講義圖片之後，整間教室一直重連

週四晚上八點半，日文老師美咲正在聲聲 Live 上一堂十二人的會話小班課。Joe 上週剛替教室白板加了一個功能：老師可以把講義圖片直接貼到白板上。美咲貼上一張 3 MB 的掃描講義，瀏覽器把圖片轉成 base64，包進一則 JSON 訊息，透過白板的 WebSocket 送往即時服務 `rt.shengsheng.example`。下一秒，美咲畫面上方跳出「連線中斷，重新連線中…」，兩秒後恢復，接著又斷，就這樣反覆了三分鐘。更糟的是，十二位學生的白板跟著一起閃爍，聊天室裡剛打的字也不見了。

小晴是當晚的值班工程師。前端的錯誤回報只寫著 `disconnected, retrying`；即時服務（uvicorn 上的 ASGI 應用）的 log 則每兩秒出現一次 `connection closed: code=1009`。小晴的第一個念頭是「把訊息上限從 1 MiB 調大到 8 MiB 就好了」，正準備改設定時，資深平台工程師阿德攔了下來：「先別動上限。你知道 1009 是誰送的、前端收到它之後做了什麼嗎？」

```text
 美咲的瀏覽器                     L4 LB 203.0.113.40       nginx 10.20.2.11–.13 uvicorn 即時服務 10.20.1.40:8001
   │                                   │                     │                       │
   │── ① 一則 4 MB 的文字訊息（base64 圖片）────────────────────────────────────────►│ 上限 1 MiB
   │◄──────────────────────────────────────────────────── ② close frame，code 1009 ──│
   │                                                                                 │
   │ ③ 前端：任何 close 都 1 秒後重連，並把「還沒確認的訊息」重送一次                │
   │── 新的握手（101）＋ 同一則 4 MB 訊息 ──────────────────────────────────────────►│
   │◄──────────────────────────────────────────────────────────── 又是 close 1009 ───│
   │   ……每 2 秒一輪；④ 每次重連都觸發教室狀態重新同步，十二位學生的白板一起閃爍     │
```

這張圖是事後檢討時阿德畫的因果鏈。當時的即時服務還是擴充前的單機：只有 10.20.1.40 一台 uvicorn（綁 8001 port），前面是 `rt` 的三台 TLS 終結 nginx 與不解密的 L4 LB；第 33 章會把它擴充成多台 gateway。① 前端把整張圖片塞進一則 WebSocket 訊息，大小約是原圖的 4/3 倍。② 即時服務設定的訊息上限是 1 MiB，它沒有讀完 4 MB，看到長度超過上限就送出 close code 1009（Message Too Big）並關閉連線，這是完全正確的保護行為。③ 真正的 bug 在前端：重連邏輯不看 close code，把「訊息太大」當成「網路不穩」，重連後又把同一則訊息重送一次，變成無限迴圈。④ 每次重連，server 都要把教室裡所有人的白板狀態重新廣播，於是一個人的問題擴散成全班的問題。

隔天早上，資安工程師 Rita 在檢討會上又補了兩點：白板的 WebSocket 把一個白板功能自己簽發、效期 24 小時的 JWT（遠超過第 27 章 access token 最長 15 分鐘的政策）放在 URL 的 query string 裡，於是它完整地出現在 nginx 的 access log；而且即時服務完全不檢查 `Origin`，任何網站都能替已登入的學生開一條教室連線。阿德給小晴的作業是：「用 asyncio 從零寫一個 WebSocket server 和 client。寫完你就會知道 1009 從哪裡來、ticket 為什麼比 query string 裡的 JWT 好，以及前端到底該怎麼重連。」這一章就跟著小晴，把一條 WebSocket 連線從握手、frame、心跳、關閉到認證完整拆開，最後在 32.13 節的動手做裡全部實作一次。

## 32.2 為什麼需要 WebSocket

HTTP 的基本模式是「client 問、server 答」：server 不能在 client 沒有發請求的時候主動送資料。教室聊天與白板偏偏需要相反的方向，老師畫一筆，server 要立刻推給十二位學生。第 31 章介紹過三種在 HTTP 上「模擬推送」的做法：**short polling**（每隔幾秒問一次「有新訊息嗎」）、**long polling**（請求先掛著，有訊息才回應）與 **SSE**（Server-Sent Events，一個不結束的 HTTP 回應，server 持續往裡面寫事件）。它們都能推送，但白板還需要學生以同樣的頻率把筆畫送上去，雙向都要低延遲、低開銷。

**WebSocket** 是一個建立在 TCP 上的雙向訊息協定，規格是 RFC 6455。它先送一個普通的 HTTP/1.1 請求，請 server「把這條連線升級成 WebSocket」；server 同意之後，這條 TCP 連線就不再說 HTTP，而是兩端隨時都能送出一則一則的**訊息**（message），每則訊息被包在一個或多個**frame**（帶著小 header 的資料單位）裡。舉例來說，學生在白板畫一筆，瀏覽器送出一則約 60 bytes 的 JSON 訊息，線上只多 6 bytes 的 frame header；同樣的事情用 HTTP 請求做，光是 header 就常有幾百 bytes。

第 31 章的選型表已經比較過這幾種做法，結論不是「WebSocket 最好」：單向推送時 SSE 能沿用 HTTP 的快取、認證 header 與 HTTP/2 multiplexing，常常更省事。WebSocket 的優勢是雙向且開銷極低，代價是升級之後就脫離了 HTTP 的語意：沒有 status code、沒有 header、沒有快取，proxy 也看不懂內容，所以認證、重連、訊息格式與流量控制都得自己設計，這正是本章大部分篇幅在處理的事。

> [!warning] 常見誤解
> 「WebSocket 是 UDP」或「WebSocket 比 TCP 快」都是錯的。WebSocket 跑在 TCP 上（經由 TLS 時就是 TCP＋TLS），繼承 TCP 的可靠、有序與 head-of-line blocking（第 12 章）：一個封包遺失，後面的訊息全部要等重傳。它省下的是 HTTP 請求的重複開銷與「先問才能答」的往返，而不是傳輸層的延遲。

## 32.3 開場握手：一個 HTTP 請求變成另一種協定

WebSocket 為什麼要從 HTTP 開始，而不是直接開一個新的 TCP port？因為現實網路裡，能穩定穿過防火牆、公司 proxy 與 LB 的幾乎只有 80 與 443 port 上的 HTTP 流量。借用 HTTP 的請求，WebSocket 可以和網站共用同一個網域、同一張憑證、同一個 port，cookie 與 `Origin` 也照常送出。HTTP/1.1 本來就有一個「換協定」的機制：client 送 `Upgrade` header 提議，server 回 **101 Switching Protocols** 同意，之後這條連線就改說新協定。

```text
 瀏覽器（www.shengsheng.example 的頁面）                         rt.shengsheng.example
   │                                                                     │
   │── GET /ws/classroom/8812?ticket=Qm9…Zw HTTP/1.1 ───────────────────►│
   │   Host: rt.shengsheng.example                                       │
   │   Upgrade: websocket                    ← 想換成什麼協定            │
   │   Connection: Upgrade                   ← 這是 hop-by-hop 的升級請求│
   │   Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==   ← 16 bytes 隨機數   │
   │   Sec-WebSocket-Version: 13                                         │
   │   Origin: https://www.shengsheng.example                            │
   │   Sec-WebSocket-Protocol: ss-chat.v3, ss-chat.v2                    │
   │                                                                     │
   │◄── HTTP/1.1 101 Switching Protocols ────────────────────────────────│
   │    Upgrade: websocket                                               │
   │    Connection: Upgrade                                              │
   │    Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=               │
   │    Sec-WebSocket-Protocol: ss-chat.v2   ← server 從清單裡選一個     │
   │                                                                     │
   │◄═════════ 空行之後的每一個 byte 都是 WebSocket frame（雙向）═══════►│
```

逐行看請求。方法必須是 `GET`，版本至少是 HTTP/1.1。`Upgrade: websocket` 說明要換成的協定；`Connection: Upgrade` 告訴這一跳的接收者「`Upgrade` 這個 header 是給你的」，因為兩者都是 **hop-by-hop header**（只對相鄰的一跳有效、proxy 不會自動往下轉的 header）。Firefox 送的是 `Connection: keep-alive, Upgrade`，所以 server 要把 `Connection` 當成逗號分隔的 token 清單比對，而不是比對整個字串。

再看回應。狀態碼必須正好是 101，其他狀態碼都代表握手失敗。回應的空行之後，同一條 TCP 連線上的 bytes 全部屬於 WebSocket，server 甚至可能把第一個 frame 和 101 回應放在同一個 TCP segment 裡送出，所以 client 讀完 header 後不能把緩衝區裡剩下的 bytes 丟掉。

| Header | 誰送 | 必要性 | 意義與常見錯誤 |
|---|---|---|---|
| `Upgrade: websocket` | 雙方 | 必要 | 大小寫不拘；proxy 沒轉送時 server 看不到它，回 400 |
| `Connection: Upgrade` | 雙方 | 必要 | 是 token 清單，可能是 `keep-alive, Upgrade` |
| `Sec-WebSocket-Key` | client | 必要 | base64 編碼的 16 bytes 隨機數，每次連線都不同 |
| `Sec-WebSocket-Version` | client | 必要 | 只能是 13；不支援時 server 回 426 並附上自己支援的版本 |
| `Sec-WebSocket-Accept` | server | 必要 | 由 key 推導；client 驗證不符就必須放棄連線 |
| `Origin` | 瀏覽器 | 瀏覽器一定送 | 非瀏覽器的 client 可以不送或亂填，不能當作身分驗證 |
| `Sec-WebSocket-Protocol` | 雙方 | 選用 | client 列出候選，server 選一個；選了 client 沒提的，client 必須斷線 |
| `Sec-WebSocket-Extensions` | 雙方 | 選用 | 協商 extension，例如 `permessage-deflate`（32.9 節） |

### Sec-WebSocket-Accept：手算一次

計算方式寫死在規格裡：把 client 送來的 key **字串**（不解碼）接上一個固定的 GUID `258EAFA5-E914-47DA-95CA-C5AB0DC85B11`，算 SHA-1，再把 20 bytes 的 digest 做 base64。RFC 6455 用的範例 key 是 `dGhlIHNhbXBsZSBub25jZQ==`，正確答案是 `s3pPLMBiTxaQ9kYGzzhZRbK+xOo=`。下面的程式照公式算一次並和 RFC 的值比對，順便示範最常見的錯誤寫法。

```python
import base64
import hashlib

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"  # RFC 6455 寫死的常數，所有實作都一樣


def accept_for(key: str) -> str:
    """Sec-WebSocket-Accept = base64(SHA-1(key 字串 + GUID))；key 不需要先 base64 解碼。"""
    return base64.b64encode(hashlib.sha1(key.encode("ascii") + GUID).digest()).decode()


rfc_key = "dGhlIHNhbXBsZSBub25jZQ=="          # RFC 6455 第 1.3 節的範例
print("key 解碼後      =", base64.b64decode(rfc_key))
print("SHA-1 輸入      =", (rfc_key.encode() + GUID).decode())
digest = hashlib.sha1(rfc_key.encode() + GUID).digest()
print("SHA-1（hex）    =", digest.hex())
print("Accept          =", accept_for(rfc_key))
assert accept_for(rfc_key) == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="

# 常見錯誤：先把 key 解碼成 16 bytes 再算，結果就和瀏覽器算的不一樣
wrong = base64.b64encode(hashlib.sha1(base64.b64decode(rfc_key) + GUID).digest()).decode()
print("錯誤做法的結果  =", wrong)
assert wrong != accept_for(rfc_key)
```

```text
key 解碼後      = b'the sample nonce'
SHA-1 輸入      = dGhlIHNhbXBsZSBub25jZQ==258EAFA5-E914-47DA-95CA-C5AB0DC85B11
SHA-1（hex）    = b37a4f2cc0624f1690f64606cf385945b2bec4ea
Accept          = s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
錯誤做法的結果  = BXhwxM0SZasKmCD9S4BfpPmCnEw=
```

第一行揭開 RFC 範例 key 的小彩蛋：它解碼後正好是 16 個 ASCII 字元「the sample nonce」，真實的 key 則是 16 個隨機 byte。第二行是 SHA-1 的輸入：key 的 base64 字串原封不動地接上 GUID，中間沒有空格。第三、四行是 20 bytes 的 digest 與它的 base64，和 RFC 的範例完全一致。最後一行說明為什麼很多手寫 server 握手失敗：把 key 先解碼再算，得到的值完全不同，瀏覽器會在 console 顯示「Incorrect 'Sec-WebSocket-Accept' header value」之類的訊息並放棄連線。

這個機制要解決的問題常被誤解。它**不是**認證，也不是加密：任何人都能算出 Accept，SHA-1 在這裡只是一個「把 key 變成另一個值」的函式。它的目的是讓 client 確認「對面真的是理解 WebSocket 的 server，而且在回應我這一次的請求」，而不是把請求當普通 HTTP 處理的舊 server 或重播舊回應的快取。另一半的保護來自瀏覽器：以 `Sec-` 開頭的 header 是 fetch 規格裡的**禁止 header**（forbidden request header），網頁的 JavaScript 不能用 `fetch()` 或 XHR 自己設定它們，所以惡意網頁無法用一般的 HTTP 請求偽造出一個 WebSocket 握手。

### 握手失敗時，瀏覽器看到什麼

server 想拒絕握手時，就回一個普通的 HTTP 錯誤：`Origin` 不在允許清單回 403、ticket 無效回 401、版本不對回 426 並附上 `Sec-WebSocket-Version: 13`、根本不是升級請求回 400。問題在於，瀏覽器的 WebSocket API **不會把 HTTP 狀態碼交給 JavaScript**：前端只會收到一個沒有細節的 `error` 事件，接著是 code 1006 的 `close` 事件。這是刻意的安全設計，避免惡意網頁用 WebSocket 探測內網服務。後果是前端 log 裡的「1006」可能代表握手被 403 拒絕、DNS 失敗、TLS 錯誤或 TCP 被 reset，要分辨只能看 DevTools 的 Network 面板或 server 端的 log。

握手還要穿過路徑上的每一層 proxy。因為 `Upgrade` 與 `Connection` 是 hop-by-hop header，nginx 預設不會把它們轉給 upstream，而且 nginx 對 upstream 預設用 HTTP/1.0；所以反向代理 WebSocket 時一定要明確寫出下面三行，否則 uvicorn 收到的是一個沒有 `Upgrade` 的普通 GET，回 400 或 404。

```bash
# nginx 反向代理 WebSocket 的最小設定（示意；完整的 timeout 鏈見第 43 章）
location /ws/ {
    proxy_pass http://rt_upstream;
    proxy_http_version 1.1;                    # Upgrade 只存在於 HTTP/1.1
    proxy_set_header Upgrade $http_upgrade;    # hop-by-hop header 要手動往下傳
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 75s;                    # 預設 60s：沒有任何資料就斷線，心跳間隔必須更短
}
```

最後一行把 32.7 節的心跳和這一節串起來：nginx 的 `proxy_read_timeout` 預設 60 秒，指的是「從 upstream 連續多久讀不到任何資料就關閉」，對 WebSocket 來說就是閒置逾時。聲聲 Live 的心跳每 25 秒一次，所以 75 秒的設定留了足夠餘裕。

## 32.4 Frame 格式：逐 bit 讀懂 WebSocket

握手完成後，TCP 上流動的就是一個接一個的 frame。TCP 是 byte stream，沒有訊息邊界（第 11 章），WebSocket frame 的 header 正是用來畫出邊界的「自描述 header」：先告訴接收者「這個 frame 有多長」，接收者就知道讀到哪裡為止。下圖是 RFC 6455 的 frame 布局，最上方是 bit 編號：

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌─┬─┬─┬─┬───────┬─┬─────────────┬───────────────────────────────┐
 │F│R│R│R│opcode │M│ Payload len │   Extended payload length     │
 │I│S│S│S│  (4)  │A│     (7)     │  (16 bits，若 len == 126)     │
 │N│V│V│V│       │S│             │  (64 bits，若 len == 127)     │
 │ │1│2│3│       │K│             │                               │
 ├─┴─┴─┴─┴───────┴─┴─────────────┴ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
 │   Extended payload length（64-bit 時的後 32 bits）            │
 ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┬───────────────────────────────┤
 │                               │  Masking-key（MASK=1 時才有） │
 ├───────────────────────────────┼───────────────────────────────┤
 │  Masking-key（續，共 32 bits）│         Payload Data          │
 ├───────────────────────────────┘                               │
 │                Payload Data（長度由上面的欄位決定）           │
 └───────────────────────────────────────────────────────────────┘
```

從第一個 byte 讀起。**FIN**（1 bit）表示「這是這則訊息的最後一個 frame」，沒有分片的訊息 FIN 一律是 1。**RSV1–3**（各 1 bit）保留給 extension，沒有協商任何 extension 時必須是 0，收到非 0 就是協定錯誤。**opcode**（4 bits）說明這個 frame 的種類。第二個 byte 的最高位是 **MASK**，表示 payload 有沒有被遮罩；剩下 7 bits 是 **Payload len**。

長度欄位用了一個可變長度的編碼：7-bit 值 0–125 直接就是長度；126 表示「真正的長度在後面 2 bytes（16-bit 無號整數）」；127 表示「真正的長度在後面 8 bytes（64-bit，最高位必須是 0）」。規格要求用**最短的編碼**，100 bytes 的 payload 不能寫成 126 加上 16-bit 的 100。接著，如果 MASK 是 1，有 4 bytes 的 **masking key**；最後才是 payload。所以 header 最短 2 bytes（server 送出的小 frame），最長 14 bytes（client 送出、payload 超過 65,535 bytes 的 frame：2＋8＋4）。

| opcode | 名稱 | 類別 | 說明 |
|---|---|---|---|
| 0x0 | continuation | 資料 | 分片訊息的後續 frame |
| 0x1 | text | 資料 | payload 是 UTF-8 文字（整則訊息必須是合法 UTF-8） |
| 0x2 | binary | 資料 | 任意 bytes，例如 protobuf、圖片 |
| 0x3–0x7 | 保留 | 資料 | 收到就是協定錯誤 |
| 0x8 | close | 控制 | 開始或回應 close handshake（32.8 節） |
| 0x9 | ping | 控制 | 要求對方回 pong |
| 0xA | pong | 控制 | 回應 ping，或主動送出當作單向心跳 |
| 0xB–0xF | 保留 | 控制 | 收到就是協定錯誤 |

opcode 的最高位剛好把它分成兩類：0x8 以上是**控制 frame**（control frame），有三條額外規則：payload 最多 125 bytes、不能分片（FIN 必須是 1）、可以插在一則分片訊息的中間。這三條規則是一組設計：控制 frame 必須小而完整，才能在一則 100 MB 的檔案傳到一半時，讓 ping 或 close 立刻插隊送出。

下面的程式實作 frame 的編碼與解碼，並用 RFC 6455 第 5.7 節列出的範例 bytes 逐一驗證。

```python
import secrets
import struct

OPCODES = {0x0: "CONT", 0x1: "TEXT", 0x2: "BINARY", 0x8: "CLOSE", 0x9: "PING", 0xA: "PONG"}


def xor_mask(data: bytes, key: bytes) -> bytes:
    """masked[i] = data[i] XOR key[i % 4]；同一個函式既能 mask 也能 unmask。"""
    n = len(data)
    stream = (key * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "big") ^ int.from_bytes(stream, "big")).to_bytes(n, "big")


def encode_frame(opcode: int, payload: bytes, *, fin=True, mask_key: bytes | None = None) -> bytes:
    head = bytearray([(0x80 if fin else 0) | opcode])
    mbit = 0x80 if mask_key else 0
    n = len(payload)
    if n <= 125:                                   # 7-bit 長度直接放
        head.append(mbit | n)
    elif n <= 0xFFFF:                              # 126 ＋ 16-bit 長度
        head += bytes([mbit | 126]) + struct.pack("!H", n)
    else:                                          # 127 ＋ 64-bit 長度
        head += bytes([mbit | 127]) + struct.pack("!Q", n)
    if mask_key:
        head += mask_key
        payload = xor_mask(payload, mask_key)
    return bytes(head) + payload


def decode_frame(buf: bytes):
    b0, b1 = buf[0], buf[1]
    fin, rsv, opcode = b0 >> 7, (b0 >> 4) & 0b111, b0 & 0x0F
    masked, n, pos = b1 >> 7, b1 & 0x7F, 2
    if n == 126:
        n, pos = struct.unpack_from("!H", buf, 2)[0], 4
    elif n == 127:
        n, pos = struct.unpack_from("!Q", buf, 2)[0], 10
    key = buf[pos:pos + 4] if masked else b""
    pos += 4 if masked else 0
    data = buf[pos:pos + n]
    return dict(fin=fin, rsv=rsv, op=OPCODES[opcode], masked=bool(masked), header=pos,
                length=n, payload=xor_mask(data, key) if masked else data)


KEY = bytes.fromhex("37fa213d")                    # RFC 6455 第 5.7 節範例用的 masking key
cases = [
    ("server→client 文字 Hello", encode_frame(0x1, b"Hello"), "810548656c6c6f"),
    ("client→server 文字 Hello", encode_frame(0x1, b"Hello", mask_key=KEY), "818537fa213d7f9f4d5158"),
    ("分片 1/2：Hel", encode_frame(0x1, b"Hel", fin=False), "010348656c"),
    ("分片 2/2：lo", encode_frame(0x0, b"lo"), "80026c6f"),
    ("ping Hello", encode_frame(0x9, b"Hello"), "890548656c6c6f"),
    ("256 bytes binary", encode_frame(0x2, bytes(256)), "827e0100"),
    ("65536 bytes binary", encode_frame(0x2, bytes(65536)), "827f0000000000010000"),
]
for label, wire, rfc_prefix in cases:
    f = decode_frame(wire)
    shown = wire.hex() if len(wire) <= 16 else wire[:f["header"]].hex() + "…"
    print(f"{shown:<22} FIN={f['fin']} {f['op']:<6} mask={int(f['masked'])} "
          f"header={f['header']:>2}B len={f['length']:<5}  {label}")
    assert wire.hex().startswith(rfc_prefix)       # 和 RFC 的範例 bytes 逐一比對
    assert f["rsv"] == 0

# 每個 client frame 都要換一把新的隨機 key：同樣的內容，線上的 bytes 每次都不同
a = encode_frame(0x1, b"GET / HTTP/1.1", mask_key=secrets.token_bytes(4))
b = encode_frame(0x1, b"GET / HTTP/1.1", mask_key=secrets.token_bytes(4))
print("同一句話 mask 兩次，線上 bytes 相同？", a == b)
assert decode_frame(a)["payload"] == decode_frame(b)["payload"] == b"GET / HTTP/1.1"
```

```text
810548656c6c6f         FIN=1 TEXT   mask=0 header= 2B len=5      server→client 文字 Hello
818537fa213d7f9f4d5158 FIN=1 TEXT   mask=1 header= 6B len=5      client→server 文字 Hello
010348656c             FIN=0 TEXT   mask=0 header= 2B len=3      分片 1/2：Hel
80026c6f               FIN=1 CONT   mask=0 header= 2B len=2      分片 2/2：lo
890548656c6c6f         FIN=1 PING   mask=0 header= 2B len=5      ping Hello
827e0100…              FIN=1 BINARY mask=0 header= 4B len=256    256 bytes binary
827f0000000000010000…  FIN=1 BINARY mask=0 header=10B len=65536  65536 bytes binary
同一句話 mask 兩次，線上 bytes 相同？ False
```

第一行可以直接對照位元圖：`81` 是 `1000 0001`，FIN=1、RSV 全 0、opcode 1（text）；`05` 是 MASK=0、長度 5；後面五個 byte 就是 ASCII 的「Hello」。第二行是 client 送出的同一句話：第二個 byte 變成 `85`，最高位的 MASK 打開了，接著是 4 bytes 的 key `37fa213d`，payload 變成看不出原文的 `7f9f4d5158`，因為 `0x48 XOR 0x37 = 0x7f`，依此類推。第三、四行是一則分成兩片的訊息：第一片 `01` 的 FIN 是 0、opcode 是 text，第二片 `80` 的 FIN 是 1、opcode 是 0（continuation）。

最後兩行展示長度編碼的兩種擴充：256 bytes 時第二個 byte 是 `7e`（126），後面 `0100` 是 16-bit 的 256；65,536 bytes 剛好超過 16-bit 的上限，第二個 byte 是 `7f`（127），後面 8 bytes 是 64-bit 的 65,536。七個 frame 和 RFC 的範例逐 byte 相符。程式最後一行印出的是 `False`（每次執行都一樣，除非兩把隨機 key 恰好相同，機率約四十億分之一）：同一句話用兩把不同的 key 遮罩，線上的 bytes 完全不同，下一節就要解釋這件事為什麼重要。

## 32.5 Masking：為什麼 client 一定要遮罩

規格的要求很硬：**client 送往 server 的每一個 frame 都必須 mask**，server 收到沒有 mask 的 frame 必須關閉連線；反過來，**server 送往 client 的 frame 一律不能 mask**。遮罩的演算法很簡單：client 為每個 frame 產生一把 4 bytes 的隨機 key，payload 的第 i 個 byte 和 key 的第 i mod 4 個 byte 做 XOR。XOR 兩次會還原，所以 server 用同一把 key 再做一次就拿回原文。key 就明明白白地放在 header 裡，任何看得到封包的人都能還原，所以 masking **不是加密**，機密性要靠 wss（TLS）提供。

既然不保密，為什麼要多花這 4 bytes 和一輪 XOR？答案在 client 所處的環境：瀏覽器裡跑的是**任何網站的 JavaScript**，包括惡意網站的。如果沒有 masking，攻擊者的頁面可以開一條 WebSocket 連到自己的 server，再透過 `send()` 精確控制送上線路的每一個 byte。路徑上若有一台不懂 WebSocket 的**透明 proxy**（transparent proxy，使用者不知道它存在、會攔截 80 port 流量並快取回應的中間設備），它看到 101 之後的 bytes 長得像一個新的 HTTP 請求，就可能把它當成 HTTP 解析，再把攻擊者 server 準備好的「回應」快取起來，當成某個正常網站的資源，送給同一個網路上的其他人。

```text
 沒有 masking 的世界（RFC 6455 設計時要防的情境，只為說明成因）

 惡意頁面的 JS            透明 proxy（不懂 WebSocket，會快取 HTTP）         攻擊者的 server
   │── 握手（升級成功）───────────►│──────────────────────────────────────────►│
   │── send(看起來像 HTTP 請求的 bytes)►│ 以為是新的 HTTP 請求：               │
   │                               │ 「GET 某個正常網站的腳本」              │
   │                               │◄── 攻擊者準備好的、看起來像回應的 bytes │
   │                               │ 存進快取，key 是那個正常網站的 URL      │
 其他使用者 ──── 請求那個正常網站的腳本 ──►│ 快取命中，拿到被污染的內容          │

 有 masking 的世界：線上的 bytes = 攻擊者的資料 XOR 一把每個 frame 都不同的隨機 key
   → 攻擊者無法預測線上會出現什麼 bytes，也就無法讓 proxy 看到一個「像 HTTP」的請求
```

這張圖從上到下讀。前兩步是一條看似正常的 WebSocket 連線；第三步是關鍵，proxy 沒有實作 WebSocket，於是把應用資料誤認成 HTTP 請求。2010 年前後，研究人員實際在部分透明 proxy 上示範了這類快取污染，對象包括早期草案版本的 WebSocket 與當時瀏覽器外掛提供的 socket 功能，這直接促成了 masking 的設計。有了 masking，攻擊者在 `send()` 裡放的內容會被瀏覽器用一把**攻擊者看不到、也無法預測**的 key 打亂，送上線路的 bytes 等於是隨機的，proxy 再怎麼誤解也解析不出攻擊者想要的請求。

從這個成因可以推出兩個實作要點。第一，key 必須來自密碼學等級的隨機來源，而且每個 frame 都換一把；可預測的 key 等於沒有 mask，上一節程式的最後一行就是在驗證這件事。第二，server 送出的內容不受惡意網頁控制，所以不需要也不能 mask；至於「全站都用 wss 是否就能不 mask」，答案是不行，延伸問答 Q3 會說明原因。

> [!warning] 常見誤解
> 「masking 是為了防止別人偷看聊天內容」是錯的。masking 保護的是**路徑上的中間設備**，保密要靠 TLS。自己寫 client 時忘了 mask，連線會被正確實作的 server 用 1002 拒絕，32.13 節的實驗 B 會重現這件事。

## 32.6 訊息、frame 與分片

應用程式看到的單位是**訊息**，線上傳的單位是 **frame**，一則訊息可以由一個或多個 frame 組成，這叫**分片**（fragmentation）。規則只有三條：第一個 frame 的 opcode 是 text 或 binary、FIN=0；中間的 frame opcode 是 0（continuation）、FIN=0；最後一個 frame opcode 是 0、FIN=1。不分片的訊息就是一個 FIN=1、opcode 為 text 或 binary 的 frame。

為什麼需要分片？最主要的理由是**送出端不必先知道訊息的總長度**。server 要把一個邊產生邊壓縮的課堂錄影匯出串流給 client，如果不能分片，就得先把整個檔案放在記憶體裡算出長度才能寫 header。第二個理由是讓控制 frame 能插隊：一則 50 MB 的訊息若是一個 frame，送完之前 ping、pong、close 都只能排在後面；切成多片之後，控制 frame 可以夾在任兩片之間。下圖是 32.13 節實驗 A 實際送出的序列：

```text
 client                                                                  server
   │── frame 1  FIN=0 opcode=TEXT  "畫"＋「一」的前 2 bytes（5 bytes）────►│ 開始組一則文字訊息
   │── frame 2  FIN=1 opcode=PING  "hb-c1" ───────────────────────────────►│ 控制 frame 插隊：
   │◄──────────────────────────────────── FIN=1 opcode=PONG "hb-c1" ───────│   立刻回 pong
   │── frame 3  FIN=0 opcode=CONT  「一」的最後 1 byte＋「條」（4 bytes）─►│ 繼續累積
   │── frame 4  FIN=1 opcode=CONT  "線"（3 bytes）────────────────────────►│ FIN=1：訊息完整
   │                                                                       │ 驗證 UTF-8，交給應用程式
   │◄──────────────────────────── FIN=1 opcode=TEXT "echo: 畫一條線" ──────│
```

逐步看。frame 1 開啟一則 text 訊息，FIN=0 表示還沒完。frame 2 是一個 ping，它的 FIN 是 1，因為控制 frame 永遠不能分片，但它不屬於正在組裝的那則訊息；server 處理完 ping 立刻回 pong，然後回到組裝狀態。frame 3 與 frame 4 是 continuation，直到 FIN=1 才算一則完整的訊息。注意切點：「畫一條線」的 UTF-8 編碼是 12 bytes，每個字 3 bytes，frame 1 在第 5 個 byte 處切開，剛好把「一」字切成兩半。

這個切點說明了 UTF-8 驗證的位置：規格要求 text **訊息**整體是合法的 UTF-8，而不是每個 frame。如果 server 對每個 frame 各自 `decode()`，frame 1 就會被誤判為不合法。正確的做法是組完整則訊息再驗證，或者使用增量解碼器（incremental decoder）邊收邊驗證，好處是能更早發現錯誤；驗證失敗時用 close code 1007（Invalid frame payload data）關閉連線。還有兩條規則要記得：分片中途出現另一個 text 或 binary frame（而不是 continuation）是協定錯誤；中間設備可以重新切分訊息的分片，所以應用程式**不能**把「一個 frame」當成有意義的邊界。

瀏覽器的 WebSocket API 只給你完整的訊息：`onmessage` 拿到的永遠是組好的字串或 `Blob`／`ArrayBuffer`，`send()` 也是送出一則完整訊息，瀏覽器自己決定要不要分片。這讓前端寫起來簡單，但瀏覽器會先把整則訊息放進記憶體，所以訊息大小上限必須在兩端都設（32.10 節）。

## 32.7 Ping、Pong 與心跳

第 7、10、11 章都提過：TCP 連線在兩端看起來還活著，路徑上的 NAT、防火牆或 LB 卻可能早已因為閒置而刪掉這條連線的紀錄，等下一個封包經過時才發現連線已死。教室聊天常常好幾分鐘沒人說話，所以 WebSocket 需要自己的心跳。協定提供了兩種控制 frame：**ping** 要求對方回應，**pong** 是回應，而且 pong 的 payload 必須照抄對應 ping 的 payload，讓送出端知道是哪一次 ping 的回應。

```text
 server（每 25 秒送 ping）                                    client
   │── PING "hb-41" ────────────────────────────────────────────►│
   │◄─────────────────────────────────────────── PONG "hb-41" ───│  照抄 payload
   │   （25 秒後）                                               │
   │── PING "hb-42" ────────────────────────────────────────────►│  ✕ 路徑斷了、分頁被凍結
   │   等待 pong 的時限 20 秒……                                  │
   │   沒有回應 → 判定失聯：直接關閉 TCP，釋放這條連線的資源     │
   │   （不等 close handshake，因為對方多半收不到）              │
   │                                                     下次 client 讀 socket：
   │                                                     沒有 close frame 就斷了 → 1006，重連
```

這張時序圖說明心跳的兩個目的。第一個目的是**讓連線上一定有流量**，間隔短於路徑上最短的閒置逾時，中間設備就不會刪掉連線；第二個目的是**偵測對方已經消失**，超過時限沒收到 pong，就主動關閉，避免 server 為一條死連線保留記憶體、訂閱與 presence（線上狀態）。聲聲 Live 的設定是每 25 秒送一次 ping，20 秒內沒收到 pong 就關閉；32.13 節實驗 C 用縮小的時間尺度重現這個流程。

| 路徑上的元件 | 閒置逾時（聲聲 Live 的設定或常見值） | 太短的後果 | 心跳的要求 |
|---|---|---|---|
| nginx `proxy_read_timeout` | 預設 60 秒，聲聲 Live 設 75 秒 | 安靜的教室每分鐘斷一次 | 間隔 < 75 秒 |
| 雲端 LB 的 idle timeout | 依產品與設定而定，聲聲 Live 設 120 秒 | LB 送 RST 或默默丟棄 | 間隔 < 120 秒 |
| 家用路由器與電信 CGNAT | 數分鐘不等，可能遠短於 RFC 建議（第 7 章） | 學生閒置後第一則訊息失敗 | 業界常用 20–30 秒 |
| 行動網路與手機省電 | 背景分頁會被瀏覽器節流或凍結 | 心跳延遲、server 誤判失聯 | 判定失聯的時限要寬鬆一些 |

這張表的結論是：心跳間隔由路徑上**最短**的那個逾時決定，而你通常不知道學生家裡的 CGNAT 設多少，所以業界多半選 20 到 30 秒。表的最後一列提醒另一個方向：判定失聯的時限太短，手機切到背景、瀏覽器節流計時器時就會被誤殺，造成不必要的重連。

瀏覽器有兩個常被忽略的行為。第一，瀏覽器收到 ping 會**自動**回 pong，JavaScript 看不到 ping，也**沒有 API 可以主動送 ping**。所以「由 server 送 ping」是協定層的心跳；如果前端也想偵測「server 是否還活著」，只能在應用層送自訂的心跳訊息（例如 `{"type":"hb"}`），並在一段時間沒收到任何訊息時主動重連。第二，規格允許送出沒有對應 ping 的 pong（unsolicited pong），當作單向的「我還活著」，對方不需要回應。

## 32.8 Close handshake 與 close code

TCP 有自己的四次揮手（第 10 章），WebSocket 為什麼還要一個 close handshake？因為 TCP 的 FIN 只能說「我不再送資料」，無法說明**為什麼**結束，也無法區分「應用程式刻意結束」和「連線意外中斷」。WebSocket 的 **close frame**（opcode 0x8）帶著 2 bytes 的 **close code** 與一段可選的 UTF-8 **reason**；因為控制 frame 的 payload 最多 125 bytes，reason 最多 123 bytes。

```text
 client（學生按下「離開教室」）                                     server
 OPEN                                                                 OPEN
   │── CLOSE  code=1000 reason="下課" ───────────────────────────────►│
 CLOSING（不再送資料 frame，但繼續讀）                              收到 close：
   │                                                                  │ 不再送資料 frame
   │◄──────────────────────────────────── CLOSE  code=1000 ───────────│ 回一個 close（照抄 code）
   │                                                                  │ server 先關閉 TCP
   │◄──────────────────────────────────── TCP FIN ────────────────────│ → TIME_WAIT 留在 server
   │── TCP FIN／ACK ─────────────────────────────────────────────────►│
 CLOSED（wasClean = true，code = 1000）                             CLOSED
```

逐步看。任一方都可以先送 close；送出之後就不能再送資料 frame，但要繼續讀，因為對方可能還有正在路上的訊息，最後會等到對方的 close。收到 close 的一方如果還沒送過 close，就回一個，通常照抄對方的 code。兩邊都交換過 close 之後，規格建議**由 server 先關閉 TCP**，理由正是第 10 章的 TIME_WAIT：主動關閉的一方要背 TIME_WAIT，server 的四元組來自眾多 client，不會耗盡；如果讓 client 先關，大量手機與瀏覽器各自背一份 TIME_WAIT 倒是無妨，但 client 若是一台壓測機或後端服務，就可能耗盡來源 port。client 在送出或收到 close 後，應等一小段時間讓 server 關閉 TCP，逾時才自己關。

在瀏覽器裡，這整套流程最後變成一個 `close` 事件，帶著三個欄位：`code`、`reason`、`wasClean`。`wasClean` 為 true 表示雙方完成了 close handshake；為 false 則表示 TCP 在沒有完整交換 close frame 的情況下就斷了，這時 `code` 是 **1006**。1006 是一個**保留值**，永遠不會出現在線上，只用來向應用程式回報「沒有收到 close frame 就斷線」。同樣的保留值還有 1005（收到的 close frame 沒有帶 code）與 1015（TLS 握手失敗）。

| code | 名稱 | 誰會送 | 前端該怎麼做 |
|---|---|---|---|
| 1000 | Normal Closure | 任一方，正常結束 | 不重連 |
| 1001 | Going Away | server 下線部署、瀏覽器離開頁面 | 稍後重連 |
| 1002 | Protocol Error | 收到違反協定的 frame（例如沒 mask） | 不重連，回報 bug |
| 1003 | Unsupported Data | 收到無法處理的資料型別（例如只收 text 卻收到 binary） | 不重連，回報 bug |
| 1005 | No Status Received | 保留，不可送出；收到不帶 code 的 close 時回報 | 視同正常結束 |
| 1006 | Abnormal Closure | 保留，不可送出；沒有 close frame 就斷線 | 指數退避後重連 |
| 1007 | Invalid Frame Payload Data | 文字訊息不是合法 UTF-8 等 | 不重連，回報 bug |
| 1008 | Policy Violation | 違反政策，例如 Origin 或權限不符 | 不重連，提示使用者 |
| 1009 | Message Too Big | 訊息超過對方的上限 | **不要重送同一則訊息** |
| 1010 | Mandatory Extension | client 要求的 extension server 沒答應 | 不重連，修設定 |
| 1011 | Internal Error | server 遇到未預期的錯誤 | 退避後重連 |
| 1012／1013 | Service Restart／Try Again Later | server 重啟或暫時過載（IANA 登錄的值） | 退避加隨機抖動後重連 |
| 1015 | TLS Handshake | 保留，不可送出 | 檢查憑證 |
| 3000–4999 | 3000 起向 IANA 登錄；4000 起私有使用 | 框架或應用程式自訂，例如聲聲 Live 的 4001「授權到期」 | 依自訂語意 |

這張表最右邊一欄是故事事故的解法：前端的錯誤在於把所有 close 一視同仁，而 1009 要求的是改變行為，不是重連。另一個實務細節是瀏覽器的 `ws.close(code, reason)` 只接受 1000 或 3000–4999 的 code，reason 超過 123 bytes 會丟出例外，所以應用自訂的語意要放在 4000–4999。下面的程式把 close payload 的編解碼規則與重連策略寫成函式：

```python
import struct

# 可以放進 close frame 的 code：1004、1005、1006、1015 是保留值（後三個只用來在 API 回報）
SENDABLE = {1000, 1001, 1002, 1003, *range(1007, 1015), *range(3000, 5000)}


def build_close(code: int, reason: str = "") -> bytes:
    if code not in SENDABLE:
        raise ValueError(f"{code} 不能出現在 close frame 裡")
    payload = struct.pack("!H", code) + reason.encode("utf-8")
    if len(payload) > 125:                         # 控制 frame 的 payload 上限
        raise ValueError(f"reason 太長：{len(payload) - 2} bytes > 123")
    return payload


def parse_close(payload: bytes):
    if not payload:
        return 1005, ""                            # 沒帶 code：API 回報 1005
    if len(payload) == 1:
        raise ValueError("1 byte 的 close payload 是協定錯誤（1002）")
    code = struct.unpack("!H", payload[:2])[0]
    return code, payload[2:].decode("utf-8")       # reason 也必須是合法 UTF-8


def reconnect_policy(code: int) -> str:
    """前端收到 close 之後該怎麼做：不是每一種關閉都該立刻重連。"""
    if code == 1000:
        return "正常結束：不重連"
    if code == 1001:
        return "對方要離開（例如 server 重新部署）：稍後重連"
    if code in (1012, 1013, 1006):
        return "暫時性問題：指數退避加隨機抖動後重連"
    if code == 1009:
        return "訊息太大：不要重送同一則訊息，改走 HTTP 上傳"
    if code in (1002, 1003, 1007, 1008):
        return "協定或政策錯誤：重連也沒用，回報錯誤"
    if code == 4001:
        return "授權到期：先換新 ticket 再重連"
    return "未知：退避後重連並記錄"


print("close 1000 '下課' 的 payload：", build_close(1000, "下課").hex(" "))
print("解析 03 f1 + 'too big'：", parse_close(b"\x03\xf1too big"))
print("解析空 payload：", parse_close(b""))
for bad in (1006, 999):
    try:
        build_close(bad)
    except ValueError as exc:
        print("拒絕送出：", exc)
try:
    build_close(1008, "政策違規" * 11)              # 每個中文字 3 bytes，44 字 = 132 bytes
except ValueError as exc:
    print("拒絕送出：", exc)
for code in (1000, 1001, 1006, 1008, 1009, 1013, 4001):
    print(f"  {code} → {reconnect_policy(code)}")
assert parse_close(build_close(1009, "too big")) == (1009, "too big")
```

```text
close 1000 '下課' 的 payload： 03 e8 e4 b8 8b e8 aa b2
解析 03 f1 + 'too big'： (1009, 'too big')
解析空 payload： (1005, '')
拒絕送出： 1006 不能出現在 close frame 裡
拒絕送出： 999 不能出現在 close frame 裡
拒絕送出： reason 太長：132 bytes > 123
  1000 → 正常結束：不重連
  1001 → 對方要離開（例如 server 重新部署）：稍後重連
  1006 → 暫時性問題：指數退避加隨機抖動後重連
  1008 → 協定或政策錯誤：重連也沒用，回報錯誤
  1009 → 訊息太大：不要重送同一則訊息，改走 HTTP 上傳
  1013 → 暫時性問題：指數退避加隨機抖動後重連
  4001 → 授權到期：先換新 ticket 再重連
```

第一行是 close payload 的實際長相：`03 e8` 是 big-endian 的 1000，後面 6 bytes 是「下課」的 UTF-8。第二行反過來解析，`03 f1` 是 1009。第三行是沒有 payload 的 close frame，規格允許，API 回報 1005。第四到六行是三種不能送出的情況：1006 是保留值、999 不在任何範圍內、reason 超過 123 bytes。中文 reason 特別容易踩到最後這一條，因為每個字佔 3 bytes，41 個字就超過了。後半段是聲聲 Live 前端在事故後改寫的重連邏輯：遇到 1009 時把那則訊息標成失敗並提示「圖片太大，改用上傳」，而不是放回待送佇列。

退避的細節也值得一提：重連間隔應該指數成長（例如 1、2、4、8 秒，上限 30 秒），並加上**隨機抖動**（jitter，在間隔上加減一段隨機時間）。如果 server 重新部署時送出 1001 給一萬條連線，而所有前端都在固定的 1 秒後重連，server 一啟動就會同時收到一萬個握手，這叫**驚群**（thundering herd）；抖動能把它們攤平。第 33 章會把重連、補發與去重放進完整的即時系統設計裡。

## 32.9 Subprotocol 與 extension

WebSocket 只規定「怎麼送訊息」，不規定「訊息是什麼意思」。聲聲 Live 的聊天訊息是 JSON，白板筆畫可能是 JSON 也可能是 protobuf，版本一變，舊前端和新 server 就可能互相看不懂。**subprotocol** 是握手時協商「這條連線上的訊息用哪一種應用層協定」的機制：client 在 `Sec-WebSocket-Protocol` 列出自己會說的協定（依偏好排序），server 從中選**一個**放進回應；server 一個都不支援時就不回這個 header，由應用決定要不要繼續。

聲聲 Live 用 subprotocol 做訊息格式的版本管理：新版前端送 `ss-chat.v3, ss-chat.v2`，還沒升級的 server 只認得 v2 與 v1，就回 `ss-chat.v2`，前端依回應決定用哪一種格式。這比把版本號塞進 URL 好，因為選擇是雙方協商出來的，而且一條連線只會有一種格式。兩條規則要注意：server 選的值必須是 client 列出的其中一個，否則 client 必須斷線；瀏覽器端用 `new WebSocket(url, ["ss-chat.v3", "ss-chat.v2"])` 指定候選，連線後從 `ws.protocol` 讀出 server 選的結果。

**extension** 則是修改 frame 本身的機制，用 `Sec-WebSocket-Extensions` 協商，可以使用 RSV 位元與保留的 opcode。實務上唯一廣泛部署的是 RFC 7692 的 **permessage-deflate**：每則訊息用 DEFLATE 壓縮，壓縮過的訊息在第一個 frame 打開 RSV1。協商時可以帶參數，例如 `client_max_window_bits` 限制壓縮視窗大小，`server_no_context_takeover` 要求 server 每則訊息都重設壓縮狀態，不沿用上一則訊息的字典。

```text
 client → server：Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits
 server → client：Sec-WebSocket-Extensions: permessage-deflate; server_no_context_takeover; client_max_window_bits=12

 壓縮過的訊息：
 ┌─┬─┬─┬─┬───────┬─┬─────────────┐
 │1│1│0│0│ 0x1   │0│  len = 38   │  RSV1 = 1：「這則訊息是壓縮過的」（只標在第一個 frame）
 └─┴─┴─┴─┴───────┴─┴─────────────┘
   payload：DEFLATE 壓縮後的 bytes（原文 180 bytes 的 JSON；數字為示意）
```

這張圖的上半是一次協商：client 提議並表示願意接受 window bits 的限制，server 同意，並要求自己不沿用 context、client 的視窗最多 2¹² bytes。下半是壓縮後的 frame：第一個 byte 從 `0x81` 變成 `0xC1`，多出來的那個 bit 就是 RSV1。這也解釋了為什麼 32.4 節說「沒有協商 extension 時，RSV 不為 0 就是協定錯誤」：如果接收者不知道 RSV1 的意義，就會把壓縮後的 bytes 當成原文。

壓縮不是免費的，打開之前要想清楚三件事。第一是**記憶體**：沿用 context 時每條連線都要保留壓縮與解壓縮狀態，連線一多就可能比訊息本身還吃記憶體，所以常見的設定是限制 window bits 或關掉 context takeover。第二是**解壓縮炸彈**：一個 1 KB 的壓縮訊息可能解開成 1 GB，訊息大小上限必須套用在**解壓縮後**的大小，而且要邊解邊檢查。第三是**長度洩漏**：如果攻擊者能控制部分內容，而同一個壓縮 context 裡又有秘密（例如 token），壓縮後的長度變化可能洩漏秘密，這和 HTTPS 上的 CRIME、BREACH 是同一類問題。聲聲 Live 的結論是聊天訊息不壓縮，大型快照改走 HTTP 由 CDN 壓縮。

## 32.10 訊息大小上限與資源保護

回到故事。即時服務設定 1 MiB 的上限並送出 1009，是正確的行為，不是 bug。WebSocket 規格本身**沒有**訊息大小上限，64-bit 的長度欄位理論上能宣告 2⁶³ bytes 的 frame，而分片又讓一則訊息能由無限多個 frame 組成。如果 server 不設上限，一個惡意或有 bug 的 client 只要宣告一個巨大的長度，server 就可能試圖配置對應的記憶體，或把分片一片片累積到記憶體耗盡。

上限要放在正確的位置才有效。最常見的錯誤是「先把整個 payload 讀進來再檢查長度」，這時記憶體早就被吃掉了。正確的順序是：讀到 header 的長度欄位時，就和「這則訊息剩下的額度」比較，超過就立刻送 1009 並關閉，payload 一個 byte 都不讀。32.13 節實驗 B 的第二個案例只送了一個宣告 2 MiB 的 header、完全沒送 payload，server 依然立刻回 1009，證明它是看 header 做決定的。

| 要限制的東西 | 為什麼 | 聲聲 Live 的設定 | 超過時 |
|---|---|---|---|
| 握手請求的 header 大小 | 慢速或超大 header 佔住連線與記憶體 | 8 KiB、讀取逾時 2 秒 | 400 或直接關閉 |
| 單一 frame 宣告的長度 | 避免照宣告的長度配置記憶體 | 不超過訊息剩餘額度 | close 1009 |
| 一則訊息的總大小（分片加總、解壓縮後） | 分片與壓縮都能繞過單一 frame 的限制 | 聊天 64 KiB、白板 1 MiB | close 1009 |
| 每秒訊息數（每條連線） | 防止一個 client 洗版或打爆 fan-out | 依功能設定配額 | 丟棄並警告，持續超過則 close 1008 |
| 每個使用者的連線數 | 一個帳號開幾百個分頁或腳本 | 依功能設定上限 | 握手回 429 或關閉最舊的連線 |
| 送往 client 的待送佇列 | 慢速 client 讓 server 記憶體堆積 | 依訊息數與 bytes 雙重上限 | 丟棄非關鍵訊息，或以 1013 關閉讓它重連 |

這張表的前三列是「進來的資料」，每一層都要有上限，而且不能被分片或壓縮繞過；後三列是「資源」，即時服務真正的瓶頸常常是連線數與 fan-out（一則訊息要複製給多少人）。最後一列是 **backpressure**（背壓，接收端跟不上時讓送出端放慢或停下的機制）：TCP 的流量控制（第 11 章）會讓慢速 client 的接收視窗變小，server 的送出 buffer 就會開始堆積。asyncio 的 `drain()` 會在 buffer 超過高水位時暫停寫入的 task，但廣播時不能讓一個慢速學生拖住所有人，所以要替每條連線設佇列上限，第 33 章會展開這個設計。

瀏覽器端也有對應的工具：`ws.bufferedAmount` 表示「已經呼叫 `send()`、但還沒交給網路」的 bytes 數。白板在連續送筆畫時，如果 `bufferedAmount` 持續增加，代表網路跟不上，前端應該合併或丟棄過時的筆畫，而不是無限制地 `send()`。

故事的根本修正不是把上限調大，而是**讓大東西走 HTTP**：Joe 把「貼上圖片」改成先用 HTTPS 上傳到 `api.shengsheng.example`（可以續傳、有進度條、可以由 CDN 快取），上傳完成後只在 WebSocket 上送一則幾十 bytes 的訊息「白板 8812 新增圖片 `img_7f3a`」，其他學生收到後再各自從 CDN 下載。WebSocket 適合大量的小訊息，不適合搬運檔案：一則 4 MB 的訊息在 TCP 上傳輸時，同一條連線上的聊天與筆畫全部排在它後面，這就是 head-of-line blocking。

## 32.11 驗證與授權：Origin、cookie 與 ticket

WebSocket 的認證之所以麻煩，是因為瀏覽器的 API 很陽春：`new WebSocket(url, protocols)` 只能指定 URL 與 subprotocol，**不能自訂 header**，所以前端無法像呼叫 REST API 那樣在握手請求裡放 `Authorization: Bearer …`。能用來傳遞身分的，只剩瀏覽器自動帶上的 cookie、URL 本身，以及連線建立後送的第一則訊息。在討論怎麼選之前，要先理解一個 WebSocket 特有的漏洞。

### Cross-Site WebSocket Hijacking 與 Origin 檢查

第 23 章講過，WebSocket 不受 CORS 管制：任何網頁都能對任何網域開 WebSocket，瀏覽器不做 preflight，也不檢查回應。如果即時服務只靠 cookie 認證，而學生的瀏覽器在握手時帶上了 cookie，那麼惡意網站就能替學生開一條完整的教室連線，**而且能讀到 server 推送的所有訊息**，這比 CSRF 更嚴重，因為 CSRF 只能送、不能讀。這類攻擊叫 **Cross-Site WebSocket Hijacking**（CSWSH，跨站 WebSocket 劫持）。

```text
 學生的瀏覽器
 ┌──────────────────────────────────────────────┐
 │ 分頁 A：www.shengsheng.example（已登入）      │
 │ 分頁 B：某個惡意網站 evil.example             │
 │   JS：new WebSocket("wss://rt.shengsheng.example/ws/classroom/8812")
 └──────────────────────┬───────────────────────┘
                        │ 握手請求
                        │ Cookie：瀏覽器依 cookie 規則決定帶不帶
                        │ Origin: https://evil.example   ← 瀏覽器填的，網頁改不了
                        ▼
              rt.shengsheng.example
              ① Origin 在允許清單裡嗎？ ── 否 ──► 403，握手失敗
              ② 是：再驗身分（cookie／ticket）與教室權限
```

這張圖的關鍵在 `Origin` 那一行：瀏覽器在每個 WebSocket 握手都會帶上發起頁面的 origin，而且網頁的 JavaScript 無法修改它。所以防禦 CSWSH 的第一道關卡是 ① 的 **Origin 允許清單**：server 只接受 `www.shengsheng.example` 的 https 頁面這類自家來源發起的握手。比對必須是**完全相等**，比對 scheme、host 與 port 三者，最常見的錯誤寫法是 `origin.endswith("shengsheng.example")`，它會放行 `evilshengsheng.example` 這個別人的網域；`"shengsheng.example" in origin` 則會放行 `www.shengsheng.example.evil.example` 這個外站的子網域。`Origin: null`（來自 sandbox iframe 或本機檔案）也要拒絕。

Origin 檢查的邊界也要講清楚：它防的是「受害者的瀏覽器被別的網站利用」，**不是**身分驗證。非瀏覽器的程式（腳本、行動 App）可以送任何 `Origin`，甚至不送。所以 Origin 檢查之後，仍然要做真正的認證；而行動 App 這類非瀏覽器 client 可以自由設定 header，應該走另一條用 `Authorization` header 驗證的入口，不要為了它們放寬瀏覽器入口的 Origin 規則。

### 四種傳遞身分的方式

| 方式 | 怎麼做 | 優點 | 風險與注意事項 |
|---|---|---|---|
| Cookie | 握手時瀏覽器自動帶上 session cookie | 前端零程式碼；`HttpOnly` 讓 JS 讀不到 | 必須做 Origin 檢查防 CSWSH；cookie 的 Domain 與 SameSite 要和 `rt` 子網域相容；不要只依賴 SameSite |
| URL 裡的長效 token | `wss://…/ws?token=<JWT>` | 簡單 | token 會出現在 access log、監控、錯誤回報裡；效期長就等於長期憑證外洩 |
| 一次性 ticket | 先用 HTTPS API 換一張 30 秒、只能用一次的 ticket，放在 URL | log 裡的 ticket 很快就失效；可綁定使用者、教室與 origin | 需要共享儲存（多台即時服務都要查得到）；仍要做 Origin 檢查 |
| 連線後的第一則訊息 | 握手不驗證，連上後送 `{"type":"auth","token":…}` | token 不進 URL | 未驗證的連線也佔資源，要設很短的期限（例如 5 秒）；server 在驗證完成前不能推任何資料 |

這張表裡還有一種常見但不建議的做法沒有列進去：把 token 塞進 `Sec-WebSocket-Protocol`，因為它是瀏覽器唯一能自訂的握手 header。問題是 server 必須在回應中**照抄**一個被選中的值，token 很容易被原樣回傳並寫進 log，而且它扭曲了 subprotocol 的語意，和其他中間設備的行為可能不相容。

聲聲 Live 最後選了「Origin 檢查＋一次性 ticket」。流程如下：

```text
 瀏覽器（www 頁面）              api.shengsheng.example             rt.shengsheng.example
   │── POST /rt/tickets ─────────────►│                                    │
   │   Authorization: Bearer <短效 JWT>│ 驗 JWT；確認學生在教室 8812        │
   │   {"room": "8812"}               │ 產生 ticket（192 bits 隨機）        │
   │                                  │ 存入共享儲存：sha256(ticket) →     │
   │                                  │  {user, room, origin, 30 秒效期}   │
   │◄── {"ticket": "Qm9…Zw", "expires_in": 30} ─│                          │
   │                                                                        │
   │── GET /ws/classroom/8812?ticket=Qm9…Zw（Upgrade 握手）────────────────►│
   │   Origin: https://www.shengsheng.example                               │ ① Origin 完全比對
   │                                                                        │ ② 取出並刪除 ticket
   │                                                                        │ ③ 未過期、教室與 origin 相符
   │◄── 101 Switching Protocols ───────────────────────────────────────────│ ④ 連線記住 user 與授權到期時間
```

逐步看。第一步沿用一般 API 的認證：前端用短效 JWT（第 27 章）呼叫 HTTPS API，這一段可以用 `Authorization` header，也受 CORS 保護。API 確認學生有權進入這間教室後，簽發一張隨機 ticket，只在儲存裡放它的雜湊。第二步把 ticket 放在 URL 開 WebSocket；server 依序檢查 Origin、取出並刪除 ticket、檢查效期與綁定。Origin 檢查放在 ticket 之前，惡意網站即使拿到一張 ticket，也無法讓它在錯誤的 origin 下生效，而且不會先把 ticket 燒掉。ticket 即使出現在 access log 裡，看到 log 的人拿到的也是一張已經用過、或幾十秒內就過期的票。下面的程式實作 ticket 儲存，並用模擬時鐘驗證四種情況：

```python
import hashlib
import secrets
from dataclasses import dataclass


class FakeClock:
    def __init__(self):
        self.now = 1_000.0

    def __call__(self):
        return self.now


@dataclass
class Ticket:
    user: str
    room: str
    origin: str
    expires_at: float


class TicketStore:
    """一次性、短效、綁定 user／room／origin 的 WebSocket 連線票。"""
    TTL = 30.0

    def __init__(self, clock):
        self.clock, self._db = clock, {}

    @staticmethod
    def _k(ticket: str) -> str:
        return hashlib.sha256(ticket.encode()).hexdigest()   # 只存雜湊：儲存外洩也拿不到可用的票

    def issue(self, user, room, origin) -> str:
        """由已驗證的 HTTPS API 呼叫（例如 POST /rt/tickets，帶短效 JWT）。"""
        ticket = secrets.token_urlsafe(24)                    # 192 bits 隨機，不可猜
        self._db[self._k(ticket)] = Ticket(user, room, origin, self.clock() + self.TTL)
        return ticket

    def redeem(self, ticket, room, origin) -> str:
        t = self._db.pop(self._k(ticket), None)              # 先刪再檢查：失敗的嘗試也會燒掉票
        if t is None:
            return "reject: unknown or already used"
        if self.clock() > t.expires_at:
            return "reject: expired"
        if t.room != room or t.origin != origin:
            return "reject: bound to another room/origin"
        return f"accept: {t.user}"


clock = FakeClock()
store = TicketStore(clock)
WWW = "https://www.shengsheng.example"

a = store.issue("stu_1024", "8812", WWW)
r1 = store.redeem(a, "8812", WWW)
r2 = store.redeem(a, "8812", WWW)                             # 重放：例如從 access log 撿到的
b = store.issue("stu_1024", "8812", WWW)
clock.now += 31                                               # 拿到票 31 秒後才連線
r3 = store.redeem(b, "8812", WWW)
c = store.issue("stu_1024", "8812", WWW)
r4 = store.redeem(c, "9001", WWW)                             # 拿 8812 的票去進別的教室
for label, result in [("第一次使用", r1), ("同一張票再用", r2), ("過期的票", r3), ("換教室", r4)]:
    print(f"{label:　<6} → {result}")
assert r1 == "accept: stu_1024"
assert [r2, r3, r4] == ["reject: unknown or already used", "reject: expired",
                        "reject: bound to another room/origin"]


def session_check(conn_auth_exp: float, now: float):
    """長連線的授權會過期：到期就用 4000–4999 的自訂 code 關閉，讓前端換票重連。"""
    return (4001, "auth expired") if now >= conn_auth_exp else None


opened = clock()
print("連線 14 分鐘時：", session_check(opened + 15 * 60, opened + 14 * 60))
print("連線 15 分鐘時：", session_check(opened + 15 * 60, opened + 15 * 60))
```

```text
第一次使用　 → accept: stu_1024
同一張票再用 → reject: unknown or already used
過期的票　　 → reject: expired
換教室　　　 → reject: bound to another room/origin
連線 14 分鐘時： None
連線 15 分鐘時： (4001, 'auth expired')
```

前四行對應 ticket 的四個性質。第一次使用成功；同一張票再用一次失敗，因為 `redeem` 用 `pop` 先刪除再檢查，即使攻擊者從 log 撿到票，也只能撞上「已經用過」。第三行是效期：30 秒內沒用掉就作廢，所以 ticket 要在開 WebSocket 前一刻才申請。第四行是綁定：8812 教室的票不能拿去進 9001 教室，origin 的綁定同理。只存雜湊是便宜的保險：儲存外洩時，攻擊者拿到的不是可用的票。

最後兩行處理一個常被忽略的問題：**長連線的授權會過期**。握手時驗證通過，不代表兩小時後這位學生仍有權限：JWT 可能已過期、學生可能被老師移出教室、帳號可能被停權。聲聲 Live 讓每條連線記住授權的到期時間（例如 15 分鐘），到期時用自訂的 close code 4001 關閉，前端收到 4001 就去換一張新 ticket 再重連；被移出教室或停權時，server 則主動用 1008 關閉該使用者的所有連線。另一個同樣重要的原則是**每則訊息都要授權**：握手時確認「這個人能進教室 8812」，不代表這位使用者送來的「刪除白板」訊息就能直接執行，server 仍要依角色（老師或學生）檢查每一種操作。

> [!tip] 用 cookie 的團隊要補齊的三件事
> 用 cookie 認證時，至少要做到：握手時嚴格比對 Origin；cookie 設 `Secure`、`HttpOnly` 並明確寫出 `SameSite`（各瀏覽器預設不同，第 23 章）；session 撤銷時同步關閉該使用者的 WebSocket。另外 `rt` 和 `www` 是不同 host，host-only cookie 不會送到 `rt`；改寫 `Domain=shengsheng.example` 會讓所有子網域都收到它，要審慎評估。

## 32.12 WebSocket over HTTP/2、HTTP/3 與 WebTransport

RFC 6455 的握手依賴 HTTP/1.1 的 `Upgrade` 機制，而 HTTP/2 明確禁止 `Upgrade` 與 `Connection` header，因為一條 HTTP/2 連線上同時有很多 stream，「把整條連線換成另一個協定」說不通。結果是瀏覽器在一個用 HTTP/2 載入的頁面裡開 WebSocket，傳統上必須**另外開一條 TCP＋TLS 連線**，多付一次交握的往返。RFC 8441 用 **Extended CONNECT** 解決這件事：把一條 WebSocket 放進 HTTP/2 的**一條 stream** 裡。

```text
 瀏覽器                                                  server（同一條 h2 連線，頁面請求也在上面）
   │◄── SETTINGS  ENABLE_CONNECT_PROTOCOL = 1 ──────────────│ ① server 先宣告支援
   │                                                        │
   │── HEADERS（stream 7）──────────────────────────────────►│ ② 用 CONNECT 開一條「隧道」
   │     :method = CONNECT                                  │
   │     :protocol = websocket      ← Extended CONNECT 新增的 pseudo-header
   │     :scheme = https   :authority = rt.shengsheng.example
   │     :path = /ws/classroom/8812?ticket=…                │
   │     sec-websocket-version = 13   origin = https://www.shengsheng.example
   │                                                        │
   │◄── HEADERS（stream 7）:status = 200 ───────────────────│ ③ 成功是 200，不是 101
   │                                                        │
   │══ DATA（stream 7）：裡面就是 RFC 6455 的 frame ═══════►│ ④ frame 格式（含 client mask）照舊
   │◄═ DATA（stream 7）══════════════════════════════════════│
   │── DATA END_STREAM ─────────────────────────────────────►│ ⑤ END_STREAM ≈ TCP FIN；RST_STREAM ≈ TCP RST
```

逐步看。① server 在 SETTINGS frame（第 22 章）裡宣告 `SETTINGS_ENABLE_CONNECT_PROTOCOL`（0x8）為 1，表示接受 Extended CONNECT。② client 在新的 stream 上送 `CONNECT`，用新的 `:protocol` pseudo-header 指明要開 websocket；`origin` 照常送，但**沒有** `Sec-WebSocket-Key` 與 Accept，因為雙方已經在 HTTP/2 層確認了協定。③ 成功的回應是 200。④ 之後 DATA frame 的內容就是 RFC 6455 的 frame，本章的編解碼全部照用。⑤ END_STREAM 對應 TCP 的 FIN，RST_STREAM 對應 RST。

好處是和頁面的其他請求共用已建立的連線，省下 TCP 與 TLS 交握。代價是 HTTP/2 的老問題：所有 stream 共用一條 TCP，一個封包遺失會卡住所有 stream（第 12、22 章）。RFC 9220 把同一套 Extended CONNECT 機制搬到 HTTP/3，WebSocket 改跑在一條 QUIC stream 上，理論上能避開 TCP 的 head-of-line blocking，也能享受 QUIC 的 connection migration（第 13 章）。

**WebTransport** 則是另一條路：它不是「放在新傳輸上的 WebSocket」，而是一套新的 API 與協定，在一個 HTTP/3 session 裡同時提供多條可靠的 stream（雙向或單向）與**不可靠的 datagram**（可能遺失、不重傳，適合「晚到就沒用」的資料）。對白板來說，「游標位置」這種每 50 毫秒更新一次、遺失一筆無所謂的資料，用 datagram 比用 WebSocket 合適；聊天訊息則仍需要可靠、有序的 stream。

| 項目 | WebSocket（HTTP/1.1） | WebSocket over HTTP/2（RFC 8441） | WebSocket over HTTP/3（RFC 9220） | WebTransport（HTTP/3） |
|---|---|---|---|---|
| 傳輸 | 獨占一條 TCP（＋TLS） | h2 的一條 stream，共用 TCP | h3 的一條 stream，跑在 QUIC | QUIC 上的多條 stream＋datagram |
| 握手 | `Upgrade` → 101 | Extended CONNECT → 200 | Extended CONNECT → 200 | Extended CONNECT（`:protocol=webtransport`） |
| head-of-line blocking | 有（TCP） | 有，而且和其他 stream 互相影響 | 只在同一條 stream 內 | 各 stream 獨立；datagram 不重傳 |
| 不可靠傳輸 | 無 | 無 | 無 | 有（datagram） |
| UDP 被封鎖的網路 | 不受影響 | 不受影響 | 無法使用，要退回 TCP | 無法使用，要退回 WebSocket |

這張表的最後一列是現實中的關鍵：部分企業網路與公共 Wi-Fi 會擋掉 UDP 443，所以走 HTTP/3 的方案都必須保留 TCP 上的備援；即使未來把游標改用 WebTransport，WebSocket 仍要留著當退路。

> [!note] 2026 現況：WebSocket 的新傳輸與 WebTransport（依 2026 年 10 月查證）
> - **WebSocket 本體**：仍是 RFC 6455（2011），版本號 13；壓縮 extension 是 RFC 7692。
> - **over HTTP/2（RFC 8441）**：Chrome 與 Firefox 有支援，部分 server 與 proxy 也支援；各產品的預設是否開啟依版本而定，上線前要實測。
> - **over HTTP/3（RFC 9220）**：2022 年發布，截至 2026 年 10 月，瀏覽器與 server 的支援仍相對少。實務上多數部署仍走 HTTP/1.1 的 `Upgrade`，所以聲聲 Live 教室的 WebSocket 多半仍跑在 TCP 上，不受 QUIC connection migration 保護（第 13 章），換網路時要靠重連與補發（第 33 章）。
> - **Python 端**：uvicorn 截至 2026 年 10 月仍不支援 HTTP/2（依知識，未逐項查證），所以即使瀏覽器到 CDN 或 LB 走 h2，到 uvicorn 這一段仍是 HTTP/1.1 的 `Upgrade`；邊緣設備能否把 h2 的 WebSocket 轉成 HTTP/1.1 送往後端，依產品而定。
> - **WebTransport**：IETF 的 `draft-ietf-webtrans-http3-16`（2026-07）處於 WG Last Call，尚未成為 RFC；W3C 的 WebTransport API 仍是 Working Draft。瀏覽器支援（依 caniuse）為 Chrome 97+、Edge 98+、Firefox 114+、Safari 26.4+（含 iOS）。
> - **WebSocketStream**：一個以 stream 為基礎、內建 backpressure 的新 WebSocket API，Chrome 已提供；其他瀏覽器的狀態本書未能確認，使用前請查最新的支援表。

## 32.13 動手做：用 asyncio 從零實作 WebSocket

這一節把前面的規則全部寫成程式。實驗一專注在握手：一個會檢查 `Upgrade`、版本、key、Origin 與一次性 ticket 的 server，以及會驗證 Accept 與 subprotocol 的 client。實驗二是完整的 frame 層：分片重組、自動回 pong、close handshake、訊息大小上限、協定錯誤與心跳。兩段程式都只用標準函式庫，在 127.0.0.1 上用 port 0；為了讓每段都能單獨執行，實驗二重複了必要的編解碼函式。以下輸出是在 macOS 上實際執行的結果，在 Linux 上相同。

### 實驗一：握手、Origin 與 ticket

server 用 `asyncio.start_server` 建立，`limit=8192` 讓 `readuntil` 在 header 超過 8 KiB 時丟出例外，這就是 32.10 節表格第一列的「握手 header 上限」。client 依序嘗試七種情境，其中兩張 ticket 事先簽發好。

```python
import asyncio
import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlsplit

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
ALLOWED_ORIGINS = {"https://www.shengsheng.example"}
SUPPORTED = ["ss-chat.v2", "ss-chat.v1"]          # server 的偏好順序
TICKETS: dict[str, str] = {}                      # ticket → room；真實系統放在共享儲存並設 30 秒效期


def accept_for(key: str) -> str:
    return base64.b64encode(hashlib.sha1(key.encode() + GUID).digest()).decode()


def tokens(value: str) -> list[str]:
    return [t.strip().lower() for t in value.split(",") if t.strip()]


async def read_head(reader):
    raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 2)   # 上限由 StreamReader 的 limit 控制
    first, *lines = raw.decode("latin-1").split("\r\n")[:-2]
    headers = {}
    for line in lines:
        name, _, value = line.partition(":")
        k = name.strip().lower()
        headers[k] = f"{headers[k]}, {value.strip()}" if k in headers else value.strip()
    return first, headers


def check_upgrade(first: str, h: dict) -> tuple[str, list[str]]:
    method, target, version = first.split(" ")
    if method != "GET" or version != "HTTP/1.1":
        return "400 Bad Request", []
    if "websocket" not in tokens(h.get("upgrade", "")) or "upgrade" not in tokens(h.get("connection", "")):
        return "400 Bad Request", []
    if h.get("sec-websocket-version") != "13":
        return "426 Upgrade Required", ["Sec-WebSocket-Version: 13"]
    try:
        if len(base64.b64decode(h.get("sec-websocket-key", ""), validate=True)) != 16:
            return "400 Bad Request", []
    except ValueError:
        return "400 Bad Request", []
    if h.get("origin") not in ALLOWED_ORIGINS:     # 完全比對 scheme://host[:port]
        return "403 Forbidden", []
    url = urlsplit(target)
    room = TICKETS.pop(parse_qs(url.query).get("ticket", [""])[0], None)   # pop：只能用一次
    if room is None or url.path != f"/ws/classroom/{room}":
        return "401 Unauthorized", []
    extra = [f"Sec-WebSocket-Accept: {accept_for(h['sec-websocket-key'])}"]
    offered = [t.strip() for t in h.get("sec-websocket-protocol", "").split(",") if t.strip()]
    if chosen := next((p for p in SUPPORTED if p in offered), None):
        extra.append(f"Sec-WebSocket-Protocol: {chosen}")
    return "101 Switching Protocols", ["Upgrade: websocket", "Connection: Upgrade"] + extra


async def handle(reader, writer):
    try:
        first, headers = await read_head(reader)
        status, extra = check_upgrade(first, headers)
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, TimeoutError, ValueError):
        status, extra = "400 Bad Request", []
    if not status.startswith("101"):
        extra += ["Content-Length: 0", "Connection: close"]   # 拒絕時就是普通的 HTTP 回應
    writer.write(("\r\n".join([f"HTTP/1.1 {status}"] + extra) + "\r\n\r\n").encode())
    await writer.drain()
    writer.close()                                 # 這個實驗只看握手，101 之後也直接關


async def handshake(port, *, origin, ticket, version="13", upgrade=True):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    key = base64.b64encode(secrets.token_bytes(16)).decode()
    lines = [f"GET /ws/classroom/8812?ticket={ticket} HTTP/1.1", "Host: rt.shengsheng.example"]
    if upgrade:
        lines += ["Upgrade: websocket", "Connection: keep-alive, Upgrade"]   # Firefox 的寫法
    lines += [f"Sec-WebSocket-Key: {key}", f"Sec-WebSocket-Version: {version}",
              f"Origin: {origin}", "Sec-WebSocket-Protocol: ss-chat.v3, ss-chat.v2"]
    writer.write(("\r\n".join(lines) + "\r\n\r\n").encode())
    first, headers = await read_head(reader)
    writer.close()
    if first.startswith("HTTP/1.1 101"):           # client 一定要驗 Accept，不符就放棄連線
        assert headers["sec-websocket-accept"] == accept_for(key)
        return f"{first[9:]}（Accept 驗證通過，subprotocol={headers.get('sec-websocket-protocol')}）"
    hint = f"，{'Sec-WebSocket-Version: ' + headers['sec-websocket-version']}" \
        if "sec-websocket-version" in headers else ""
    return first[9:] + hint


async def main():
    server = await asyncio.start_server(handle, "127.0.0.1", 0, limit=8192)
    port = server.sockets[0].getsockname()[1]
    good = "https://www.shengsheng.example"
    t1 = secrets.token_urlsafe(16)
    TICKETS[t1] = "8812"
    t2 = secrets.token_urlsafe(16)
    TICKETS[t2] = "8812"
    cases = [
        ("正常的瀏覽器握手", dict(origin=good, ticket=t1)),
        ("同一張 ticket 再用一次", dict(origin=good, ticket=t1)),
        ("惡意網站發起", dict(origin="https://evil.example", ticket=t2)),
        ("偽裝成子網域的外站", dict(origin="https://www.shengsheng.example.evil.example", ticket=t2)),
        ("舊版協定 version 8", dict(origin=good, ticket=t2, version="8")),
        ("忘了帶 Upgrade（proxy 吃掉了）", dict(origin=good, ticket=t2, upgrade=False)),
        ("ticket 未被消耗，正常使用", dict(origin=good, ticket=t2)),
    ]
    results = []
    for label, kwargs in cases:
        results.append(await handshake(port, **kwargs))
        print(f"{len(results)}. {label} → {results[-1]}")
    server.close()
    await server.wait_closed()
    assert [r[:3] for r in results] == ["101", "401", "403", "403", "426", "400", "101"]

asyncio.run(main())
```

```text
1. 正常的瀏覽器握手 → 101 Switching Protocols（Accept 驗證通過，subprotocol=ss-chat.v2）
2. 同一張 ticket 再用一次 → 401 Unauthorized
3. 惡意網站發起 → 403 Forbidden
4. 偽裝成子網域的外站 → 403 Forbidden
5. 舊版協定 version 8 → 426 Upgrade Required，Sec-WebSocket-Version: 13
6. 忘了帶 Upgrade（proxy 吃掉了） → 400 Bad Request
7. ticket 未被消耗，正常使用 → 101 Switching Protocols（Accept 驗證通過，subprotocol=ss-chat.v2）
```

逐行對照 server 的檢查順序。第 1 行是正常的握手：client 送 `Connection: keep-alive, Upgrade`（Firefox 的寫法），server 用 token 清單比對所以接受；client 驗證 Accept 正確，並發現 server 從 `ss-chat.v3, ss-chat.v2` 裡選了自己支援的 `ss-chat.v2`。第 2 行重用同一張 ticket，因為第一次握手時已經被 `pop` 掉，回 401。第 3、4 行是 CSWSH 的兩種樣子：一個是明顯的外站，另一個把自家網域放在前面偽裝成子網域，如果 server 用 `"shengsheng.example" in origin` 檢查就會放行，完全比對則兩者都擋下。

第 5 行是版本不符，server 回 426 並告訴 client 自己支援 13。第 6 行模擬 nginx 沒轉送 `Upgrade` 的情況，server 把它當成普通的 GET 拒絕，對應 32.15 節表格的第一列。第 7 行用第二張 ticket 握手成功，證明第 3 到 6 行的失敗都**沒有**消耗它：Origin、版本等檢查都排在 ticket 之前，惡意網站或錯誤的請求無法把合法使用者的票燒掉。

### 實驗二：frame、分片、close、上限與心跳

這是本章的核心程式。`read_frame` 依 32.4 節的位元布局讀取 frame，並在讀 payload 之前完成所有檢查：RSV 位元、保留的 opcode、mask 的方向、控制 frame 的長度與 FIN，以及「宣告的長度是否超過這則訊息剩餘的額度」。`WebSocket` 類別由 server 與 client 共用，負責分片重組、遇到 ping 立刻回 pong、UTF-8 驗證與 close handshake；`heartbeat` 是 server 端的心跳 task。實驗 A 是正常的教室對話，實驗 B 是四種違規的 client，實驗 C 是不回 pong 的殭屍連線。

```python
import asyncio
import base64
import hashlib
import secrets
import struct

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
CONT, TEXT, BINARY, CLOSE, PING, PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA
MAX_MESSAGE = 128 * 1024                      # 一則訊息（所有分片加總）的上限


class ProtocolError(Exception):
    def __init__(self, code, reason):
        super().__init__(reason)
        self.code, self.reason = code, reason


def xor_mask(data, key):
    n = len(data)
    stream = (key * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "big") ^ int.from_bytes(stream, "big")).to_bytes(n, "big")


def encode_frame(opcode, payload, *, fin=True, mask=False):
    head, n, mbit = bytearray([(0x80 if fin else 0) | opcode]), len(payload), 0x80 if mask else 0
    if n <= 125:
        head.append(mbit | n)
    elif n <= 0xFFFF:
        head += bytes([mbit | 126]) + struct.pack("!H", n)
    else:
        head += bytes([mbit | 127]) + struct.pack("!Q", n)
    if mask:                                  # client：每個 frame 換一把新的隨機 key
        key = secrets.token_bytes(4)
        head, payload = head + key, xor_mask(payload, key)
    return bytes(head) + payload


async def read_frame(reader, *, expect_mask, budget):
    b0, b1 = await reader.readexactly(2)
    fin, op, masked, n = b0 >> 7, b0 & 0x0F, b1 >> 7, b1 & 0x7F
    if b0 & 0x70 or op not in (CONT, TEXT, BINARY, CLOSE, PING, PONG):
        raise ProtocolError(1002, "RSV bit or reserved opcode")
    if masked != expect_mask:
        raise ProtocolError(1002, "client frames must be masked" if expect_mask else "server must not mask")
    if n == 126:
        n = struct.unpack("!H", await reader.readexactly(2))[0]
    elif n == 127:
        n = struct.unpack("!Q", await reader.readexactly(8))[0]
    if op >= CLOSE and (not fin or n > 125):
        raise ProtocolError(1002, "bad control frame")
    if op < CLOSE and n > budget:             # 只看宣告的長度就拒絕，不先配置記憶體
        raise ProtocolError(1009, f"message too big ({n} bytes declared)")
    key = await reader.readexactly(4) if masked else b""
    payload = await reader.readexactly(n)
    return bool(fin), op, xor_mask(payload, key) if masked else payload


class WebSocket:
    def __init__(self, reader, writer, *, is_client, log):
        self.r, self.w, self.is_client, self.log = reader, writer, is_client, log
        self.close_sent, self.close_code = False, None
        self.last_pong = asyncio.get_running_loop().time()

    async def send(self, op, payload=b"", fin=True):
        payload = payload.encode() if isinstance(payload, str) else payload
        self.w.write(encode_frame(op, payload, fin=fin, mask=self.is_client))
        await self.w.drain()

    async def recv(self):
        parts, first_op, size = [], None, 0
        try:
            while True:
                fin, op, data = await read_frame(self.r, expect_mask=not self.is_client,
                                                 budget=MAX_MESSAGE - size)
                if op == PING:                    # 控制 frame 可以插在分片之間，要立刻處理
                    self.log.append(f"收到 ping {data!r} → 回 pong")
                    await self.send(PONG, data)
                elif op == PONG:
                    self.last_pong = asyncio.get_running_loop().time()
                    self.log.append(f"收到 pong {data!r}")
                elif op == CLOSE:
                    await self._on_close(data)
                    return None
                elif (op == CONT) != (first_op is not None):
                    raise ProtocolError(1002, "unexpected continuation state")
                else:
                    first_op, size = first_op or op, size + len(data)
                    parts.append(data)
                    if fin:
                        msg = b"".join(parts)
                        try:                      # UTF-8 要對整則訊息驗證：分片可能切在字元中間
                            return (TEXT, msg.decode()) if first_op == TEXT else (BINARY, msg)
                        except UnicodeDecodeError:
                            raise ProtocolError(1007, "invalid UTF-8") from None
        except ProtocolError as exc:
            self.log.append(f"協定錯誤 → 送 close {exc.code}（{exc.reason}）並關閉 TCP")
            self.close_sent, self.close_code = True, exc.code
            await self.send(CLOSE, struct.pack("!H", exc.code) + exc.reason.encode()[:123])
        except (asyncio.IncompleteReadError, ConnectionError):
            self.close_code = self.close_code or 1006   # 沒有 close frame 就斷線
            self.log.append("TCP 斷線，沒收到 close frame → 記為 1006")
        self.w.close()
        return None

    async def close(self, code=1000, reason=""):
        self.close_sent = True
        await self.send(CLOSE, struct.pack("!H", code) + reason.encode())

    async def _on_close(self, data):
        self.close_code = struct.unpack("!H", data[:2])[0] if len(data) >= 2 else 1005
        self.log.append(f"收到 close {self.close_code} {data[2:].decode()!r}")
        if not self.close_sent:                   # 對方先關：照抄 code 回一個 close
            self.close_sent = True
            await self.send(CLOSE, data[:2])
            self.log.append(f"回 close {self.close_code}")
        if self.is_client:                        # client 等 server 先關 TCP，TIME_WAIT 留在 server
            await asyncio.wait_for(self.r.read(), 1)
            self.log.append("讀到 EOF：server 已關閉 TCP")
        else:
            self.log.append("server 先關閉 TCP")
        self.w.close()


async def heartbeat(ws, interval=0.1, timeout=0.25):
    loop, seq = asyncio.get_running_loop(), 0
    while not ws.close_sent and not ws.w.is_closing():
        if loop.time() - ws.last_pong > timeout:  # 太久沒有 pong：對方可能已經消失
            ws.log.append(f"{timeout}s 沒有 pong → 判定失聯，直接關閉 TCP")
            ws.w.close()
            return
        seq += 1
        await ws.send(PING, f"hb-{seq}")
        await asyncio.sleep(interval)


async def handle(reader, writer, slog):
    raw = await reader.readuntil(b"\r\n\r\n")    # 握手細節見實驗一，這裡只算 Accept
    path = raw.split(b" ")[1].decode()
    key = next(l.split(b":", 1)[1].strip() for l in raw.split(b"\r\n") if l.lower().startswith(b"sec-websocket-key"))
    accept = base64.b64encode(hashlib.sha1(key + GUID).digest()).decode()
    writer.write(f"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                 f"Sec-WebSocket-Accept: {accept}\r\n\r\n".encode())
    log = []
    ws = WebSocket(reader, writer, is_client=False, log=log)
    hb = asyncio.create_task(heartbeat(ws)) if path == "/ws/heartbeat" else None
    while (msg := await ws.recv()) is not None:
        await ws.send(msg[0], ("echo: " + msg[1]) if msg[0] == TEXT else msg[1])
    if hb:
        hb.cancel()
    slog.append((path, log))


async def connect(port, path, clog):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    key = base64.b64encode(secrets.token_bytes(16)).decode()
    writer.write(f"GET {path} HTTP/1.1\r\nHost: rt.shengsheng.example\r\nUpgrade: websocket\r\n"
                 f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
                 f"Origin: https://www.shengsheng.example\r\n\r\n".encode())
    await reader.readuntil(b"\r\n\r\n")
    return WebSocket(reader, writer, is_client=True, log=clog)


async def main():
    slog = []
    server = await asyncio.start_server(lambda r, w: handle(r, w, slog), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    print("── 實驗 A：正常的教室對話")
    clog = []
    ws = await connect(port, "/ws/classroom/8812", clog)
    await ws.send(TEXT, "老師好")
    op, text = await ws.recv()
    clog.append(f"收到 TEXT {text!r}")
    stroke = "畫一條線".encode()                  # 12 bytes；在第 5 個 byte 切開，剛好切在「一」字中間
    await ws.send(TEXT, stroke[:5], fin=False)
    await ws.send(PING, b"hb-c1")                 # 控制 frame 插在分片之間
    await ws.send(CONT, stroke[5:9], fin=False)
    await ws.send(CONT, stroke[9:])
    op, text = await ws.recv()                    # recv 途中先處理 pong，再交出重組好的訊息
    clog.append(f"收到 TEXT {text!r}")
    for size in (300, 70_000):
        blob = secrets.token_bytes(size)
        await ws.send(BINARY, blob)
        op, back = await ws.recv()
        assert back == blob
        clog.append(f"binary {size} bytes 往返一致（client frame header {2 + (2 if size < 65536 else 8) + 4} bytes）")
    await ws.close(1000, "下課")
    clog.append("送出 close 1000 '下課'")
    assert await ws.recv() is None and ws.close_code == 1000
    print("\n".join("  client | " + line for line in clog))

    print("── 實驗 B：違規的 client")
    attacks = {
        "沒有 mask 的 frame": encode_frame(TEXT, b"hi", mask=False),
        "宣告 2 MiB 的 frame（只送 header）": bytes([0x82, 0xFF]) + struct.pack("!Q", 2 << 20) + b"\0" * 4,
        "三個 60000 bytes 分片": b"".join([encode_frame(BINARY, bytes(60000), fin=False, mask=True),
                                       encode_frame(CONT, bytes(60000), fin=False, mask=True),
                                       encode_frame(CONT, bytes(60000), mask=True)]),
        "不合法的 UTF-8 文字": encode_frame(TEXT, b"\xe7\x95", mask=True),
    }
    codes = []
    for label, wire in attacks.items():
        ws = await connect(port, "/ws/attack", [])
        ws.w.write(wire)
        assert await ws.recv() is None
        codes.append(ws.close_code)
        print(f"  {label} → server 回 close {ws.close_code}")

    print("── 實驗 C：不回 pong 的殭屍 client")
    zlog = []
    ws = await connect(port, "/ws/heartbeat", zlog)
    await asyncio.sleep(0.5)                      # 模擬瀏覽器分頁被凍結：完全不讀 socket
    while await ws.recv() is not None:            # 醒來後才讀到堆積的 ping，然後是斷線
        pass
    print("\n".join("  client | " + line for line in (zlog[0], zlog[-1])))

    await asyncio.sleep(0.05)
    server.close()
    await server.wait_closed()
    for path, log in slog:
        if path in ("/ws/classroom/8812", "/ws/heartbeat"):
            print("\n".join(f"  server {path} | {line}" for line in log[-3:]))
    assert codes == [1002, 1009, 1009, 1007] and ws.close_code == 1006

asyncio.run(main())
```

```text
── 實驗 A：正常的教室對話
  client | 收到 TEXT 'echo: 老師好'
  client | 收到 pong b'hb-c1'
  client | 收到 TEXT 'echo: 畫一條線'
  client | binary 300 bytes 往返一致（client frame header 8 bytes）
  client | binary 70000 bytes 往返一致（client frame header 14 bytes）
  client | 送出 close 1000 '下課'
  client | 收到 close 1000 ''
  client | 讀到 EOF：server 已關閉 TCP
── 實驗 B：違規的 client
  沒有 mask 的 frame → server 回 close 1002
  宣告 2 MiB 的 frame（只送 header） → server 回 close 1009
  三個 60000 bytes 分片 → server 回 close 1009
  不合法的 UTF-8 文字 → server 回 close 1007
── 實驗 C：不回 pong 的殭屍 client
  client | 收到 ping b'hb-1' → 回 pong
  client | TCP 斷線，沒收到 close frame → 記為 1006
  server /ws/classroom/8812 | 收到 close 1000 '下課'
  server /ws/classroom/8812 | 回 close 1000
  server /ws/classroom/8812 | server 先關閉 TCP
  server /ws/heartbeat | 0.25s 沒有 pong → 判定失聯，直接關閉 TCP
  server /ws/heartbeat | TCP 斷線，沒收到 close frame → 記為 1006
```

實驗 A 的第 1 行是普通的文字往返。第 2、3 行是 32.6 節的分片時序圖：client 在分片中間插了一個 ping，server 的 `recv` 在組裝訊息的途中先回 pong，所以 client 收到的順序是 pong 在前、echo 在後；「一」字被切在兩個 frame 之間，server 組完整則訊息才做 UTF-8 驗證，所以沒有誤判。第 4、5 行驗證長度編碼：300 bytes 用 16-bit 長度，client frame header 是 2＋2＋4＝8 bytes；70,000 bytes 超過 65,535，用 64-bit 長度，header 是 2＋8＋4＝14 bytes。最後三行是 32.8 節的 close handshake：client 送 1000，server 照抄 code 回覆（reason 沒有照抄，所以是空字串），然後 server **先**關閉 TCP，client 讀到 EOF 才結束。

實驗 B 的四行是四道防線。沒有 mask 的 frame 得到 1002，這是 32.5 節的規則。第二行最值得注意：client 只送了 14 bytes 的 header，宣告長度 2 MiB，一個 payload byte 都沒送，server 已經回 1009，因為檢查發生在讀 payload 之前，server 從未為這 2 MiB 配置記憶體。第三行的每個分片只有 60,000 bytes，單看都沒超過 128 KiB，但第三片會讓整則訊息達到 180,000 bytes，`budget` 參數記錄的是「整則訊息剩下的額度」，所以照樣被擋下。第四行的兩個 byte 是一個被截斷的 UTF-8 字元，得到 1007。

實驗 C 模擬一個被凍結的瀏覽器分頁：它完成握手後完全不讀 socket。server 每 0.1 秒送一次 ping，0.25 秒內沒收到 pong 就判定失聯並直接關閉 TCP，不等 close handshake。client 醒來後才讀到堆積的 ping（還盡責地回了 pong，但已經沒人在聽），接著讀到 EOF；因為沒有收到 close frame，它記錄的 code 是 1006，這就是瀏覽器裡 `wasClean=false, code=1006` 的來源。時間尺度放大約 100 倍，就是線上的 25 秒間隔與 20 秒時限。

這兩段程式省略了 TLS、最短編碼檢查、close handshake 的逾時、壓縮與送出佇列上限（部分留作 32.16 節的練習）。production 請使用成熟的實作（例如 ASGI server 內建的 WebSocket 支援，第 42 章），自己寫一次是為了看懂它們的設定與錯誤訊息。

## 32.14 在工作上怎麼用

事故檢討後，阿德、Joe、Rita 和小晴把 WebSocket 相關的做法依角色整理成團隊的檢查清單。

**後端工程師：每一個 WebSocket endpoint 上線前回答六個問題。** 第一，Origin 允許清單是什麼，比對是否完全相等。第二，身分從哪裡來（ticket、cookie、第一則訊息），授權何時到期、到期怎麼處理。第三，每則訊息的大小上限、每條連線的訊息速率上限、每個使用者的連線數上限各是多少。第四，心跳間隔與失聯時限是多少，是否短於路徑上所有的閒置逾時。第五，部署時怎麼結束連線：先送 1001 或 1012，讓前端帶著抖動重連，而不是直接殺掉 process 讓所有人看到 1006。第六，每一種應用層操作是否都檢查了角色與權限。

**前端工程師：讓重連邏輯讀懂 close code。** 把 32.8 節的 `reconnect_policy` 寫進前端：1000 不重連，1009 不重送同一則訊息，1008 提示使用者，4001 先換 ticket，其他情況指數退避加抖動。`onclose` 時把 `code`、`reason`、`wasClean` 送進錯誤回報，故事裡若有這一行 log，小晴五分鐘就能找到原因。大型資料（圖片、檔案、白板快照）一律走 HTTP 上傳與下載，WebSocket 只送通知與參照。

**SRE：用指令與工具確認握手與連線。** 不用瀏覽器，也能用 curl 送一個握手請求，確認 LB 與 nginx 有沒有正確轉送 `Upgrade`（示意輸出）：

```bash
curl -i -N --http1.1 \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Origin: https://www.shengsheng.example" \
  "https://rt.shengsheng.example/ws/healthz"
# ↓ 示意輸出：看到 101 與正確的 Accept，代表整條路徑的升級都通了
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=

ss -tn state established '( sport = :8001 )' | wc -l     # 即時服務節點上目前的 WebSocket 連線數
ss -tn state time-wait '( sport = :8001 )' | wc -l       # server 先關 TCP，TIME_WAIT 應該出現在這裡
```

curl 這一段用 RFC 的範例 key，所以回應的 Accept 一定是 `s3pPLMBiTxaQ9kYGzzhZRbK+xOo=`，一眼就能確認是不是真正的 WebSocket server 在回應；如果拿到 400、404 或 200，問題就在中間某一層沒有轉送升級。`--http1.1` 很重要，因為 curl 對 https 預設可能協商 HTTP/2，而 HTTP/2 不允許 `Upgrade`。`ss` 的連線數應該和應用程式回報的線上人數相符，長期偏高代表有殭屍連線沒被心跳清掉。

瀏覽器 DevTools 是另一個主力工具：Network 面板篩選 WS，點開握手請求可以看到狀態碼與 header（JavaScript 看不到的 403 在這裡看得到），Messages 分頁列出每一則收送的訊息與大小。判斷流程如下：

```text
 症狀：前端回報 WebSocket 斷線
   │
   ├─ onclose 的 code 是什麼？
   │    ├─ 1000／1001／1012 ─► 正常結束或部署：確認前端有退避與抖動
   │    ├─ 1008／4001 ───────► 授權問題：看 server log 的 Origin、ticket、權限檢查
   │    ├─ 1009 ─────────────► 訊息太大：找出送大訊息的功能，改走 HTTP
   │    ├─ 1002／1007 ───────► 協定錯誤：client 或 proxy 的實作 bug
   │    └─ 1006 ─────────────► 沒有 close frame，往下分
   │
   └─ 1006：DevTools 看握手狀態
        ├─ 握手沒成功（403／401／400／502）─► server 拒絕或 proxy 沒轉送 Upgrade
        ├─ 連線剛好在閒置 N 秒後斷 ────────► 某一層的 idle timeout：比對 nginx、LB、心跳間隔
        └─ 隨機時間斷、集中在行動網路 ─────► 換網路、NAT 逾時、背景分頁：靠重連與補發（第 33 章）
```

這張流程圖的第一刀是 close code：它直接告訴你是誰、為了什麼關閉的，所以前端一定要把它記錄下來。1006 是最難的一支，因為它只代表「沒有收到 close frame」；這時要看兩件事，握手有沒有成功，以及斷線的時間點有沒有規律。如果斷線總是在閒置剛好 60 秒時發生，幾乎可以確定是某一層的預設逾時（例如 nginx 的 `proxy_read_timeout`）比心跳間隔短。

**資安工程師：審查重點。** Rita 的清單：Origin 允許清單完全比對；URL 裡沒有長效 token，access log 遮罩 query string；ticket 一次性、短效、有綁定；每則訊息都授權；上限在讀 payload 前檢查；只開放 wss。WebSocket 收到的訊息和任何使用者輸入一樣不可信，聊天內容插入頁面前要做輸出編碼，否則就是第 23 章的 XSS。

## 32.15 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 經過 nginx 後握手一律 400 或 404，直連 uvicorn 卻正常 | nginx 沒有轉送 hop-by-hop 的 `Upgrade`／`Connection`，或對 upstream 用 HTTP/1.0 | upstream log 看到的請求沒有 `Upgrade`；用 curl 分別打 nginx 與 uvicorn 比較 | 加上 `proxy_http_version 1.1` 與兩行 `proxy_set_header`（32.3 節） |
| 安靜的教室每隔整整 60 秒斷線一次，code 1006 | `proxy_read_timeout` 或 LB idle timeout 短於心跳間隔，或心跳沒開 | 斷線時間點與最後一則訊息的間隔固定；DevTools 看不到 ping，但 server log 也沒送 | 心跳 20–30 秒；逾時設定大於心跳間隔並留餘裕 |
| 自寫 client 一送訊息就被 server 用 1002 關閉 | client frame 沒有 mask，或 mask 用了固定的 key | 抓包看第二個 byte 的最高位是否為 1 | 每個 frame 用 `secrets.token_bytes(4)` 產生新的 key |
| 貼上大圖後無限重連（故事的事故） | 訊息超過上限得到 1009，前端不看 code 就重連並重送 | 前端 log 記錄 `event.code`；server log 有 1009 | 依 close code 決定重連策略；大型資料改走 HTTP |
| 握手後偶爾少了第一則訊息 | 自寫 client 讀 101 回應時多讀了 bytes，卻把 header 之後的資料丟掉 | 抓包看 101 與第一個 frame 在同一個 TCP segment | 解析 header 後保留緩衝區剩餘的 bytes 給 frame 解析器 |
| 部署後所有學生在同一秒重連，server CPU 飆高 | 前端固定間隔重連，沒有抖動；部署時直接殺掉 process | 握手數量的時間序列在部署時刻出現尖峰 | 部署時送 1001／1012 並分批關閉；前端指數退避加隨機抖動 |
| 外站頁面能讀到教室訊息（安全審查發現） | 只用 cookie 認證，沒檢查 Origin（CSWSH） | 用另一個 origin 的頁面開 WebSocket，看握手是否成功 | Origin 完全比對的允許清單；改用一次性 ticket |

除錯的通則和第 10 章一樣：**先看狀態，再看程式**。WebSocket 的「狀態」就是 close code、`wasClean` 與握手的 HTTP 狀態碼，三者通常就能把問題縮小到某一層。

## 32.16 動手練習

1. **延伸實驗二：加上最短編碼檢查**。修改 `read_frame`，讓它拒絕「用 126 編碼小於 126 的長度」與「用 127 編碼小於 65,536 的長度」的 frame，以及 64-bit 長度最高位為 1 的 frame，並在實驗 B 加兩個案例驗證。
   答案要點：在讀出擴充長度後檢查 `n < 126` 或 `n < 65536`，違反就丟出 1002 的 `ProtocolError`。這項檢查讓同一則訊息只有一種合法的編碼，避免不同實作對長度的理解不一致。

2. **延伸實驗二：close handshake 的逾時**。讓 server 在送出 close 之後，如果 0.3 秒內沒有收到對方的 close 就直接關閉 TCP。寫一個「收到 close 卻不回覆」的 client 驗證。
   答案要點：用 `asyncio.wait_for` 包住「等待對方 close frame」的讀取，逾時就 `writer.close()`。沒有這個逾時，一個不合作的 client 就能讓 server 的連線永遠停在 CLOSING。真實函式庫通常有可設定的 close timeout。

3. **用 DevTools 觀察真實的 WebSocket**（真實工具）。在任何使用 WebSocket 的網站（或用第 42 章的 ASGI 範例在本機起一個）打開 DevTools 的 Network 面板，篩選 WS，找出握手請求的 `Sec-WebSocket-Key`、`Sec-WebSocket-Accept` 與 `Sec-WebSocket-Extensions`。
   答案要點：把看到的 key 丟進 32.3 節的 `accept_for`，結果必須和回應中的 Accept 相同。很多網站會協商 `permessage-deflate`；Messages 分頁的訊息長度是解壓縮後的大小。

4. **用 tcpdump 看 frame 的 bytes**（真實工具）。在本機用 `sudo tcpdump -i lo0 -X 'tcp port <實驗二的 port>'`（Linux 用 `-i lo`）抓實驗二的流量（先把 port 固定並在程式中加一點等待），找出 client 送出的第一個 frame。
   答案要點：第一個 byte 是 `0x81`，第二個 byte 的最高位是 1（`0x80 | 長度`），接著 4 bytes 是隨機 key，payload 看起來是亂碼；server 回的 frame 第二個 byte 最高位是 0，payload 是可讀的 UTF-8。這是 masking 只保護中間設備、不提供保密的直接證據。

## 本章重點整理

- WebSocket 是 TCP 上的雙向訊息協定（RFC 6455）：先用 HTTP/1.1 的 `Upgrade` 握手，server 回 101 之後，同一條連線上的 bytes 全部是 WebSocket frame。
- `Sec-WebSocket-Accept` 是 base64(SHA-1(key 字串＋固定 GUID))，用來確認對方真的是理解 WebSocket 的 server，不是認證；RFC 範例 key `dGhlIHNhbXBsZSBub25jZQ==` 對應 `s3pPLMBiTxaQ9kYGzzhZRbK+xOo=`。
- `Upgrade` 與 `Connection` 是 hop-by-hop header，反向代理必須明確轉送；握手失敗時 JavaScript 只看到 1006，狀態碼要從 DevTools 或 server log 看。
- frame header 2–14 bytes：FIN、RSV1–3、4-bit opcode、MASK、7-bit 長度（126 接 16-bit、127 接 64-bit，必須用最短編碼），client frame 另有 4 bytes 的 masking key。
- client 送出的每個 frame 必須用每次不同的隨機 key mask，server 送出的不能 mask；masking 防的是惡意網頁利用瀏覽器控制線上 bytes、污染不懂 WebSocket 的中間設備，不是加密。
- 一則訊息可以分成多個 frame；控制 frame 最多 125 bytes、不能分片、可以插在分片之間；text 訊息的 UTF-8 要對整則訊息驗證。
- 心跳由 server 定期送 ping，間隔要短於路徑上最短的閒置逾時（常用 20–30 秒），超過時限沒有 pong 就關閉；瀏覽器會自動回 pong，但 JavaScript 不能送 ping。
- close handshake 交換帶 code 與 reason 的 close frame，之後由 server 先關閉 TCP，讓 TIME_WAIT 留在 server；1005、1006、1015 是只用於回報、不能送出的保留值。
- 前端要依 close code 決定是否重連：1009 不能重送同一則訊息、1008 重連也沒用、暫時性錯誤用指數退避加隨機抖動。
- WebSocket 規格沒有訊息大小上限，server 必須在讀 payload 之前依宣告的長度檢查，並對分片加總與解壓縮後的大小設限；大型資料應改走 HTTP。
- WebSocket 不受 CORS 管制，只用 cookie 認證會導致 CSWSH；Origin 必須以允許清單完全比對，但 Origin 不是身分驗證，非瀏覽器 client 可以任意設定。
- URL 裡的長效 token 會進 log；一次性、30 秒效期、綁定使用者與教室與 origin 的 ticket 是較好的做法，而且連線期間仍要處理授權到期與每則訊息的授權。
- RFC 8441 與 RFC 9220 用 Extended CONNECT 把 WebSocket 放進 HTTP/2、HTTP/3 的一條 stream，frame 格式不變；截至 2026 年 10 月多數部署仍走 HTTP/1.1，WebTransport 仍是草案。

## 延伸問答

> [!question]- Q1. Sec-WebSocket-Key 與 Sec-WebSocket-Accept 能防止什麼？不能防止什麼？
> 它們能防止的是「誤會」：client 用一個隨機 key 發起握手，只有真正實作了 WebSocket 的 server 才會依規格算出對應的 Accept。一個不懂 WebSocket 的舊 HTTP server 可能對任何請求回 200，一個快取可能重播之前的 101 回應，這些情況下 Accept 都不會符合這次的 key，client 就會放棄連線，不會把一般的 HTTP 回應誤當成 WebSocket 資料流。搭配瀏覽器禁止網頁設定 `Sec-` 開頭的 header，惡意網頁也無法用 `fetch()` 偽造一個握手請求去騙不懂 WebSocket 的 server。
>
> 它們不能防止的是所有和身分、機密有關的事。Accept 的計算公式是公開的，任何人都算得出來，所以它不是認證，server 不能因為「Accept 算對了」就相信 client 是誰；SHA-1 在這裡只是一個混合函式，與 SHA-1 的碰撞弱點無關，也不提供完整性保護。身分要靠 32.11 節的 Origin、ticket 或 cookie，機密性與完整性要靠 wss 的 TLS。

> [!question]- Q2. 手算：client 送出一則 70,000 bytes 的 binary 訊息，不分片時 frame header 是多少 bytes？server 原樣回送呢？如果 client 把它切成 30,000、30,000、10,000 三片呢？
> 不分片時，70,000 大於 65,535，長度要用 127 加上 64-bit 的擴充長度：第一個 byte 1 個、第二個 byte 1 個、擴充長度 8 個、masking key 4 個，共 14 bytes。server 回送不能 mask，少了 4 bytes 的 key，header 是 2＋8＝10 bytes。這和 32.13 節實驗 A 的輸出一致。
>
> 切成三片時，每一片都不超過 65,535，長度欄位用 126 加 16-bit：每片 header 是 2＋2＋4＝8 bytes，三片共 24 bytes，比不分片多了 10 bytes。分片的代價很小，換來的是送出端不必先知道總長度，以及控制 frame 可以插在片與片之間。也要注意，接收端的訊息上限必須以三片的加總（70,000 bytes）計算，不能只看單片的 30,000。

> [!question]- Q3. 為什麼 server 送給 client 的 frame 不用 mask？既然全站都用 wss，client 可以不 mask 嗎？
> masking 要防的是惡意網頁透過瀏覽器控制線路上的 bytes，誤導路徑上不懂 WebSocket 的中間設備。server 送出的內容由 server 的程式決定，不在惡意網頁的掌控之中，而接收端是本來就理解 WebSocket 的瀏覽器，沒有被誤導的問題，所以規格不要求、而且禁止 server mask，省下 4 bytes 與一輪 XOR。client 收到被 mask 的 server frame 也必須斷線，讓兩個方向的規則都沒有模糊空間。
>
> wss 不改變這條規則。規格的要求和傳輸層無關，正確實作的 server 收到沒有 mask 的 client frame 會用 1002 關閉連線；而且 TLS 不一定一路到底，可能在 CDN、LB 或企業的 TLS 檢查 proxy 上就被解開，之後那一段的中間設備仍然看得到明文。規格的設計是「不管傳輸如何，client 一律 mask」，這比讓每個實作自行判斷路徑是否安全可靠得多。

> [!question]- Q4. 你在 production 看到前端回報的斷線中，1006 佔了九成，而且大多發生在連線建立後的第 60 秒附近。你會怎麼查？
> 1006 只代表「沒有收到 close frame 就斷了」，所以先從時間點下手。斷線集中在第 60 秒附近，強烈暗示路徑上某一層有 60 秒的閒置逾時，而且這段時間內連線上沒有任何流量；nginx 的 `proxy_read_timeout` 預設就是 60 秒，是第一個嫌疑。確認方法是看斷線前最後一則訊息與斷線時刻的間隔是否固定、server 端是否真的有送 ping（心跳是否被設定成關閉，或間隔被設成 60 秒以上），以及 nginx 的 error log 是否有 upstream timed out 之類的紀錄。
>
> 如果 nginx 設定沒問題，再往外一層查 LB 的 idle timeout，往內一層查 uvicorn 或應用程式自己的逾時設定。修正有兩個方向，通常兩者都做：讓 server 每 20 到 30 秒送一次 ping，確保連線上定期有流量；把每一層的閒置逾時設得比心跳間隔長並留餘裕。修完後，1006 應該下降到只剩行動網路與換網路這類無法避免的情況，那部分則交給前端的退避重連與補發處理。

> [!question]- Q5. 面試題：設計一個瀏覽器聊天服務的 WebSocket 認證方式，並說明為什麼不直接把登入用的 JWT 放在 URL 上。
> 瀏覽器的 WebSocket API 不能自訂 header，所以能用的只有 cookie、URL 與連線後的第一則訊息。把登入用的 JWT 放在 URL 上最簡單，但 URL 會被寫進 LB、nginx、應用程式的 access log，也可能出現在監控系統與錯誤回報裡；登入 JWT 的效期通常比一次連線長，任何看得到 log 的人在效期內都能冒用。故事裡的 24 小時 JWT 正是這個問題。
>
> 我會設計成兩步：前端先用一般的 HTTPS API（帶短效 JWT 的 `Authorization` header）申請一張一次性 ticket，server 只存它的雜湊，設定約 30 秒效期，並綁定使用者、聊天室與 origin；接著用 ticket 開 WebSocket，server 依序檢查 Origin 允許清單、取出並刪除 ticket、檢查效期與綁定。連線建立後，server 記住授權到期時間，到期時用自訂 code 關閉讓前端換票重連，並對每一則訊息檢查權限。如果團隊偏好 cookie，也可以，但一定要做 Origin 完全比對來防 CSWSH，並處理子網域的 cookie 範圍問題。

> [!question]- Q6. 看 log 找原因：uvicorn 的 log 出現大量「Unsupported upgrade request」之類的警告，nginx 的 access log 對 `/ws/classroom/...` 記錄的是 400，但用 curl 直接打 uvicorn 的 8001 port 握手成功。最可能的原因是什麼？
> 直連成功、經過 nginx 失敗，問題就在 nginx 這一跳。`Upgrade` 與 `Connection` 是 hop-by-hop header，nginx 不會自動把它們轉給 upstream，而且 nginx 對 upstream 預設使用 HTTP/1.0，HTTP/1.0 沒有升級機制。所以 uvicorn 收到的是一個沒有 `Upgrade` 的普通 GET，對 WebSocket 路由來說這是無法處理的請求，於是回 400，並在 log 裡抱怨收到不支援的升級請求或缺少升級 header。
>
> 確認方法是在 uvicorn 前抓包或打開應用程式的請求 header log，看請求裡是否缺少 `Upgrade: websocket`。修法是在對應的 `location` 加上 `proxy_http_version 1.1`、`proxy_set_header Upgrade $http_upgrade` 與 `proxy_set_header Connection "upgrade"`，同時順手檢查 `proxy_read_timeout` 是否大於心跳間隔。如果中間還有 LB，也要確認它支援 WebSocket 並把升級請求原樣轉給 nginx。

> [!question]- Q7. 設計取捨：白板服務要不要打開 permessage-deflate？
> 先看訊息的特性。白板筆畫多半是幾十到幾百 bytes 的 JSON，重複的欄位名稱很多，開啟壓縮並沿用 context（context takeover）時，壓縮率可能相當好，能省下行動網路的頻寬；但這種小訊息在 TCP 與 TLS 的開銷之下，省下的絕對 bytes 數有限。另一方面，沿用 context 代表每條連線都要保留壓縮與解壓縮的狀態，在大量連線的即時服務上，這份記憶體可能比訊息本身還貴，還要付出每則訊息的 CPU 成本。
>
> 安全面有兩個要點：訊息上限必須以解壓縮後的大小計算並邊解邊檢查，否則就是解壓縮炸彈；同一個壓縮 context 裡如果同時有攻擊者可控的內容與秘密，壓縮後的長度可能洩漏秘密。我的建議是先量測：如果頻寬不是瓶頸，就不開；如果要開，限制 window bits、考慮關閉 context takeover，並確保秘密不和使用者內容放在同一個壓縮 context。大型快照則不該走 WebSocket，改走 HTTP 讓 CDN 處理壓縮與快取。

> [!question]- Q8. 2026 年，聲聲 Live 該把教室的 WebSocket 改成 WebSocket over HTTP/3 或 WebTransport 嗎？
> 先分清楚兩者。WebSocket over HTTP/3（RFC 9220）只是把同樣的 WebSocket frame 搬到一條 QUIC stream 上，API 不變，好處是避開 TCP 的 head-of-line blocking、有機會靠 QUIC migration 撐過換網路；但截至 2026 年 10 月，瀏覽器與 server 的支援仍相對少，而聲聲 Live 後端的 uvicorn 也不支援 HTTP/2 與 HTTP/3，實際上只能在邊緣終結再轉成 HTTP/1.1。WebTransport 是新的 API，提供多條 stream 與不可靠的 datagram，主流瀏覽器都已支援，但 IETF 規格仍在 WG Last Call、W3C API 仍是 Working Draft，伺服器端的選擇也比 WebSocket 少得多。
>
> 我的建議是：教室聊天與白板的主路徑維持 WebSocket，把投資放在重連、補發與去重（第 33 章），因為換網路時的斷線本來就要能優雅處理。如果有明確受益於 datagram 的功能，例如游標位置或即時的筆畫預覽，可以用 WebTransport 做實驗性的加速通道，但必須保留 WebSocket 備援，因為部分網路會封鎖 UDP。規格與支援狀態會變，做決定前要重新查最新的支援情況。

## 延伸閱讀

- RFC 6455〈The WebSocket Protocol〉：握手、frame 格式、masking、close code 與安全考量的現行規格
- RFC 7692〈Compression Extensions for WebSocket〉：permessage-deflate 的協商參數與 RSV1 的用法
- RFC 8441〈Bootstrapping WebSockets with HTTP/2〉：Extended CONNECT 與 `:protocol` pseudo-header
- RFC 9220〈Bootstrapping WebSockets with HTTP/3〉：把 RFC 8441 的機制搬到 HTTP/3
- IANA〈WebSocket Protocol Registries〉：close code、subprotocol 名稱與 extension 名稱的登錄表
- WHATWG〈WebSockets Standard〉：瀏覽器 WebSocket API（`close()` 的 code 限制、`bufferedAmount` 等），living standard
- W3C〈WebTransport〉與 IETF `draft-ietf-webtrans-http3`：WebTransport 的 API 與協定（截至 2026 年 10 月仍為草案）
- Lin-Shung Huang、Eric Y. Chen、Adam Barth、Eric Rescorla、Collin Jackson〈Talking to Yourself for Fun and Profit〉：促成 WebSocket masking 設計的透明 proxy 快取污染研究
