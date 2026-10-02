---
chapter: 29
title: Web Server
part: 8
---

# 第 29 章　寫一台 Web Server：HTTP、靜態與動態內容

> [!abstract] 本章地圖
> **核心問題**：瀏覽器送來的一串文字，web server 怎麼把它變成一個檔案或一段程式的輸出送回去？自己寫 HTTP server 時，哪些細節會變成 bug 或安全漏洞？
>
> **你會學到**：
> - 讀寫 HTTP 請求與回應的原始格式，手算 `Content-Length` 與 chunked 編碼
> - 說明靜態內容與動態內容（CGI）的差別，以及 server 怎麼用 `fork`、`dup2`、`execve` 執行程式並把輸出送給 client
> - 走一遍 Tiny 這類最小 web server 的完整流程，並在同一支程式裡實際跑起來
> - 找出並修正 path traversal、header 過長、slowloris、CGI 注入等常見安全問題
> - 解釋 keep-alive、proxy 的角色，以及 Tiny、`thumbd` 與 nginx 在架構上的差異
>
> **前置知識**：第 21 章（fork、exec）、第 27 章（short count 與 `dup2`）、第 28 章（socket 與 TCP byte stream）
>
> **對應 CS:APP 3e**：第 11 章 11.5–11.6 節

## 29.1 故事：一個 `..` 引發的資安事件

`thumbd` 有一個除錯用的端點：`GET /originals/<檔名>` 會直接回傳原圖，方便工程師比對縮圖品質。這段程式是早期為了趕上線寫的，做法很直接：把 URL 裡 `/originals/` 後面的字串接在原圖目錄後面，打開檔案，送出去。

某天，資安團隊的掃描報告出現一條高風險項目。阿哲在測試環境重現給小安看：

```bash
curl --path-as-is 'http://thumbd-test:8080/originals/../../../etc/passwd'
```

螢幕上印出了整份 `/etc/passwd`。小安愣住了：「我測試的時候用瀏覽器輸入 `..`，瀏覽器會自己把路徑整理掉，根本送不出去。」阿哲說：「瀏覽器和 `curl` 預設會幫你正規化，攻擊者不會。他們直接對 socket 寫一串 bytes，你的 server 收到什麼就是什麼。」

同一個月，客服也轉來一個奇怪的問題：少數使用者打開相簿時縮圖全部破圖，`thumbd` 的 log 寫著 `bad request line`。追查之後發現，這些使用者的瀏覽器帶了很長的 cookie，整個請求超過 1 KB，而 `thumbd` 的 HTTP 解析器只呼叫一次 `read`、用 1024 bytes 的緩衝區，就以為讀到了完整的請求。

老周把兩件事放在一起看：「HTTP 是寫在 TCP 上的文字協定，第 28 章講的 byte stream 問題它全都有；而且它直接面對網路上任何人，所以每一個欄位都要當作惡意輸入來處理。」這一章從 HTTP 的格式開始，一路寫出一台能服務靜態檔案與動態內容的小型 web server，再回頭把 `thumbd` 的這兩個問題修好。

## 29.2 Web 的基本元素：HTTP、URL 與 MIME type

**Web** 是建立在 client-server 模型（第 28 章）上的一種應用：client 是瀏覽器或 `curl` 這類程式，server 是 nginx、`thumbd` 這類程式，兩者用 **HTTP**（Hypertext Transfer Protocol，超文本傳輸協定）溝通。HTTP/1.x 是一個建立在 TCP 連線上的**文字協定**：請求與回應的開頭幾行都是人類看得懂的 ASCII 文字，用 `nc` 手動打字就能和 web server 對話。

### Content 與 MIME type

server 回傳給 client 的東西統稱 **content**（內容），可以是 HTML 網頁、圖片、JSON、影片。每一份內容都帶有一個 **MIME type**（媒體類型），告訴 client 這串 bytes 該怎麼解讀。同樣一串 bytes，標成 `image/jpeg` 瀏覽器會顯示成圖片，標成 `text/plain` 就會顯示成亂碼文字。

| MIME type | 內容 | `thumbd` 何時用到 |
|---|---|---|
| `text/html` | HTML 網頁 | 除錯用的狀態頁 |
| `text/plain` | 純文字 | 錯誤訊息 |
| `application/json` | JSON 資料 | 縮圖的 metadata API |
| `image/jpeg`、`image/png`、`image/webp` | 圖片 | 縮圖本身 |
| `application/octet-stream` | 「一串 bytes，不知道是什麼」 | 無法判斷類型時的保守預設 |

MIME type 標錯不只是顯示問題。如果 server 把使用者上傳的檔案一律標成 `text/html`，攻擊者上傳一個含有 JavaScript 的「圖片」，就能在其他使用者的瀏覽器裡執行程式碼（stored XSS）。所以 server 應該依自己的判斷決定類型，並加上 `X-Content-Type-Options: nosniff`，要求瀏覽器不要自行猜測。

### URL 的結構

每一份內容由一個 **URL**（Uniform Resource Locator，統一資源定位符）識別。以一個縮圖請求為例：

```text
 https://photos.example.com:8443/thumb/cat.jpg?w=200&h=150#top
 └─┬─┘   └───────┬────────┘ └┬─┘└──────┬─────┘└────┬────┘└┬┘
 scheme        host        port      path        query   fragment
 （協定）   （DNS 名稱）  （省略時    （server 上   （參數）  （只在瀏覽器
                          http 80、   的資源）               內部使用，
                          https 443）                       不會送給 server）
```

client 用 host 與 port 建立 TCP 連線（第 28 章的 `getaddrinfo` 與 `connect`），然後只把 **path 與 query** 這一段放進 HTTP 請求送給 server，這一段叫 **URI**（在請求中常稱為 request target）。fragment 完全不會送出。server 端的工作就是決定 URI 對應到什麼內容：一個檔案、一段程式的輸出、或一個錯誤。

URL 裡有些字元有特殊意義（`/`、`?`、`&`、`#`、空白），要當作一般資料傳送時，必須用 **percent-encoding**（百分比編碼）表示成 `%` 加兩位十六進位。手算幾個例子：

| 原始字元 | ASCII 十六進位 | 編碼後 |
|---|---|---|
| 空白 | 0x20 | `%20` |
| `/` | 0x2F | `%2F` |
| `.` | 0x2E | `%2E` |
| `?` | 0x3F | `%3F` |
| `%` 本身 | 0x25 | `%25` |

所以 `..%2F..%2Fetc%2Fpasswd` 解碼後就是 `../../etc/passwd`。這個表在 29.8 節的安全問題中會再出現：檢查路徑時，必須先決定在「解碼前」還是「解碼後」檢查，順序錯了就會被繞過。

## 29.3 HTTP 請求：request line、header 與空行

用 `curl -v` 看一個真實的請求，`>` 開頭的是 client 送出的內容：

```text
> GET /thumb/cat.jpg?w=200 HTTP/1.1
> Host: photos.example.com
> User-Agent: curl/8.7.1
> Accept: */*
>
```

一個 HTTP 請求的格式如下（`\r\n` 是 CR LF 兩個 bytes，HTTP 規定用它當作行尾）：

```text
 GET /thumb/cat.jpg?w=200 HTTP/1.1\r\n      ← request line：method、URI、version
 Host: photos.example.com\r\n               ← request header：「名稱: 值」
 User-Agent: curl/8.7.1\r\n
 Accept: */*\r\n
 \r\n                                       ← 空行：header 結束
 （body：GET 通常沒有；POST 的資料放在這裡）
```

**request line**（請求行）有三個以空白分隔的欄位：**method**（方法）說明要做什麼，**URI** 指出對象，**version** 是 HTTP 版本。接著是零或多行 **request header**（請求標頭），每行是一個「名稱: 值」，名稱不分大小寫。最後一個**空行**（只有 `\r\n`）標記 header 結束。

這個空行就是 HTTP 在 TCP byte stream 上的 framing（第 28 章）：server 必須持續讀取，直到看到連續的 `\r\n\r\n`，才知道 header 已經完整，不能假設一次 `read` 就拿到全部。28.1 節與本章 29.1 節的 bug 是同一種錯誤。

常見的 method：

| method | 意義 | 有沒有 body | 可以安全重送嗎 |
|---|---|---|---|
| `GET` | 取得資源 | 通常沒有 | 可以（不應該改變 server 狀態） |
| `HEAD` | 和 GET 一樣，但只回 header | 沒有 | 可以 |
| `POST` | 送出資料，讓 server 處理（例如上傳圖片） | 有 | 不一定，重送可能重複上傳 |
| `PUT` | 用 body 取代指定資源 | 有 | 可以（結果相同） |
| `DELETE` | 刪除資源 | 通常沒有 | 可以（刪兩次結果相同） |

最後一欄叫 **idempotent**（冪等）：做一次和做很多次的效果相同。nginx 這類 proxy 在 upstream 連線出錯或逾時時，預設會把請求改送給另一台 upstream，但 `POST`、`PATCH` 這類非冪等的請求只要已經送出去，就不會自動重送（除非明確設定 `proxy_next_upstream non_idempotent`），原因就在這裡。

### Host header 與 HTTP 版本

**`Host` header** 告訴 server 這個請求要找哪個網站。因為多個網域名稱可以對到同一個 IP（第 28 章），同一個 server 可能同時服務 `photos.example.com` 與 `admin.example.com`，只靠 `Host` 區分，這叫 virtual hosting。HTTP/1.1 規定請求一定要帶 `Host`，沒有就該回 400。

HTTP/1.0 與 HTTP/1.1 最大的差別是連線管理：HTTP/1.0 預設每個請求用一條新連線，回應完就關閉；HTTP/1.1 預設連線保持開啟，可以送下一個請求（29.9 節的 keep-alive）。本章的範例 server 為了簡單，一律回應 `HTTP/1.0` 並在回應後關閉連線。

## 29.4 HTTP 回應：status line、header 與 body

回應的結構和請求對稱：

```text
 HTTP/1.1 200 OK\r\n                         ← status line：version、狀態碼、說明文字
 Content-Type: image/jpeg\r\n                ← response header
 Content-Length: 18342\r\n
 Cache-Control: max-age=86400\r\n
 \r\n                                        ← 空行
 （18342 bytes 的 JPEG 資料）                ← response body
```

**status code**（狀態碼）是三位數，第一位數代表類別：

| 狀態碼 | 意義 | 典型情境 |
|---|---|---|
| 200 OK | 成功 | 正常回傳縮圖 |
| 301／302 | 重新導向，新位址在 `Location` header | 網址搬家、HTTP 轉 HTTPS |
| 304 Not Modified | 內容沒變，請用你的快取 | 瀏覽器帶 `If-None-Match` 再次請求 |
| 400 Bad Request | 請求格式錯誤 | request line 解析失敗 |
| 403 Forbidden | 不允許存取 | 路徑含 `..` |
| 404 Not Found | 找不到資源 | 原圖不存在 |
| 413 Content Too Large | body 太大 | 上傳超過限制的圖片 |
| 431 Request Header Fields Too Large | header 太大 | 超長的 cookie |
| 500 Internal Server Error | server 自己出錯 | 解碼器 crash、未處理的錯誤 |
| 501 Not Implemented | 不支援這個 method | 只實作 GET 的 server 收到 POST |
| 502 Bad Gateway | proxy 從 upstream 收到無效回應或連不上 | `thumbd` 掛了，nginx 回給使用者 |
| 503 Service Unavailable | 暫時無法服務 | 過載、維護中 |
| 504 Gateway Timeout | proxy 等 upstream 逾時 | `thumbd` 處理太久 |

大致的分工是：4xx 表示「client 的錯」，5xx 表示「server 端的錯」。這個區分在監控上很有用：4xx 突然增加通常是 client 或攻擊流量的變化，5xx 增加才是自己的服務出了問題。

### client 怎麼知道 body 到哪裡結束

header 用空行結束，但 body 可能是任意的二進位資料（圖片裡也可能出現 `\r\n\r\n`），所以 body 需要另外的 framing。HTTP/1.x 有三種方式，正好對應第 28 章介紹的三種 framing：

1. **`Content-Length`**（長度前綴）：header 寫明 body 有幾個 bytes。client 讀滿這麼多就結束。
2. **`Transfer-Encoding: chunked`**（分塊）：server 事先不知道總長度時使用（例如邊產生邊送）。body 被切成多個 chunk，每個 chunk 前面用十六進位寫出長度，長度 0 的 chunk 表示結束。
3. **關閉連線**：沒有上面兩者時，server 送完就關閉連線，client 讀到 EOF 就結束。這是 HTTP/1.0 的傳統做法，但無法分辨「正常結束」與「連線中途斷掉」。

手算一次。本章 29.12 節的範例 CGI 程式回傳的 body 是 `800 x 600 x 4 = 1920000 bytes` 加一個換行：

```text
「800 x 600 x 4 = 1920000 bytes」
  800（3）＋空白（1）＋x（1）＋空白（1）＋600（3）＋空白（1）＋x（1）＋空白（1）
  ＋4（1）＋空白（1）＋=（1）＋空白（1）＋1920000（7）＋空白（1）＋bytes（5）
  = 29 個字元，再加換行 1 個 → Content-Length: 30
```

同樣的 body 用 chunked 分兩塊送（前 16 bytes、後 14 bytes）會長這樣：

```text
 10\r\n                          ← 0x10 = 16 bytes
 800 x 600 x 4 = \r\n            ← 16 bytes 的資料，後面接 CRLF
 e\r\n                           ← 0xe = 14 bytes
 1920000 bytes\n\r\n             ← 14 bytes 的資料（含換行），後面接 CRLF
 0\r\n                           ← 長度 0：結束
 \r\n
```

注意 chunk 長度是**十六進位**，`10` 是 16 而不是 10，這是手寫 parser 最常見的錯誤之一。另外，`Content-Length` 一定要是 body 的 **byte 數**，不是字元數：`<h1>拾光相簿</h1>` 裡每個中文字在 UTF-8 中佔 3 bytes，四個中文字就是 12 bytes。

## 29.5 靜態內容與動態內容

server 提供的內容分成兩種：

- **靜態內容**（static content）：事先存在磁碟上的檔案，server 讀出來原樣送出，例如 HTML、CSS、已經產生好的縮圖。同一個 URL 每次得到相同的 bytes。
- **動態內容**（dynamic content）：server 收到請求時才執行一段程式產生，例如依照 `w=200` 參數即時縮放的圖片、查資料庫產生的 JSON。

最簡單的對應規則是：URI 的 path 直接對應到某個目錄底下的檔案路徑。例如設定「網站根目錄」是 `/srv/www`，`GET /index.html` 就讀 `/srv/www/index.html`；並約定 `/cgi-bin/` 開頭的路徑是可執行的程式，要執行它而不是讀它。

### CGI：讓 server 執行一支程式

**CGI**（Common Gateway Interface，通用閘道介面）是一套很早期、很簡單的約定，規定 web server 怎麼把請求交給一支外部程式、又怎麼取回它的輸出。它的設計完全建立在本書前面學過的 process 機制上：

```text
 web server（父程序）                        CGI 程式（子程序）
 ────────────────────                        ──────────────────
 收到 GET /cgi-bin/bufsize?800&600
 送出 "HTTP/1.0 200 OK\r\n" 與部分 header
 fork() ─────────────────────────────────▶  （複製出來，還是 server 的程式碼）
   │                                        setenv("QUERY_STRING", "800&600")
   │                                        dup2(connfd, STDOUT_FILENO)
   │                                          ← 從此 printf 直接寫進 socket
   │                                        execve("www/cgi-bin/bufsize", ...)
   │                                          ← 換成 CGI 程式，環境變數與
   │                                            descriptor 都被保留下來
   │                                        印出 Content-Type、Content-Length、
   │                                        空行、body → 直接送到 client
 waitpid() ◀──────────────────────────────  exit
 回收子程序，關閉連線
```

這張圖把三章的知識接在一起：`fork` 建立子行程（第 21 章）；`dup2` 把標準輸出重新導向到 connected socket（第 27 章），所以 CGI 程式完全不知道自己在寫網路，它只是 `printf`；`execve` 換掉程式碼時會保留環境變數與已開啟的 descriptor，參數就能透過環境變數傳進去。父行程最後必須 `waitpid`，否則每個請求都會留下一個 zombie（第 21 章）。

CGI 規定了一組標準的環境變數：

| 環境變數 | 內容 | 例子 |
|---|---|---|
| `QUERY_STRING` | URI 中 `?` 後面的部分 | `800&600` |
| `REQUEST_METHOD` | HTTP method | `GET` |
| `CONTENT_LENGTH` | POST body 的長度（body 從 stdin 讀） | `5120` |
| `CONTENT_TYPE` | POST body 的 MIME type | `image/jpeg` |
| `REMOTE_ADDR` | client 的 IP 位址 | `10.0.3.17` |
| `SERVER_PORT` | server 的 port | `8080` |
| `HTTP_*` | 每個 request header，例如 `HTTP_USER_AGENT` | `curl/8.7.1` |

GET 的參數放在 `QUERY_STRING`；POST 的 body 則由 server 接到 CGI 程式的標準輸入，程式依 `CONTENT_LENGTH` 讀取。CGI 程式的輸出以自己的 header（至少 `Content-Type`）開頭，空一行後是 body。在正式的 CGI 規範中，server 會先解析這些 header（例如程式可以用 `Status:` 指定狀態碼）再加上 status line；Tiny 和本章的範例採用最簡單的做法，由 server 先送出 status line，CGI 的輸出直接接在後面。

CGI 的缺點是每個請求都要 `fork` 加 `execve` 一個新行程，代價很高，而且程式無法在請求之間保留狀態（例如資料庫連線）。現代系統大多改成**長駐的應用程式 server**：FastCGI、Python 的 WSGI／ASGI server、Java 的 servlet 容器，或像 `thumbd` 這樣自己就是 HTTP server。但 CGI 的模型仍然值得學，因為它把「web server 只是把 bytes 搬來搬去，內容由另一個程式產生」這件事講得最清楚。

## 29.6 Tiny：一台最小的 web server 長什麼樣

CS:APP 的 Tiny 是一台用幾百行 C 寫成的 iterative web server，支援 GET、靜態內容與 CGI 動態內容。它的價值不在功能，而在於把一台 web server 的骨架完整地攤開。整體流程如下：

```text
 main
  │ listenfd = open_listenfd(port)
  ▼
 ┌─▶ connfd = accept(listenfd)           ← 一次只服務一個 client（iterative）
 │    │
 │    ▼
 │   doit(connfd)
 │    ├─ 讀 request line，拆出 method、uri、version
 │    ├─ method 不是 GET → clienterror 501
 │    ├─ 讀掉其餘 header，直到空行
 │    ├─ parse_uri：判斷靜態或動態，算出檔名與 CGI 參數
 │    ├─ stat 檔案：不存在 → 404
 │    ├─ 靜態：不是一般檔案或不可讀 → 403
 │    │        否則 serve_static：送 header，再把檔案內容送出
 │    └─ 動態：不是一般檔案或不可執行 → 403
 │             否則 serve_dynamic：送 status line，fork、dup2、execve
 │    │
 │    ▼
 └── close(connfd)
```

Tiny 有幾個值得注意的實作選擇。它用第 27 章的 RIO 套件逐行讀取 request line 與 header，正確處理了 short read；`serve_static` 用 `mmap` 把檔案映射進記憶體（第 24 章），再一次寫到 socket；錯誤一律經過一個 `clienterror` 函式，產生一個簡單的 HTML 錯誤頁。

它同時也刻意保持簡單，因此有許多不能直接拿去 production 的地方：

| Tiny 的簡化 | 在 production 會造成的問題 |
|---|---|
| iterative，一次只處理一條連線 | 一個慢的 client 就讓所有人等待（第 30 章的並行模型解決這件事） |
| 沒有讀寫逾時 | 一個連上之後不送資料的 client 可以永遠佔住 server |
| 只要 URI 含有 `cgi-bin` 就當作動態內容 | 判斷規則太寬鬆，路徑處理也沒有防止 `..` |
| 不處理 request header，也不支援 keep-alive | 每個請求都要新建連線 |
| 寫入已關閉的連線時會收到 SIGPIPE | 若不忽略 SIGPIPE，client 中途離開可能讓整個 server 結束 |

這張表本身就是一份「從玩具到 production」的待辦清單，接下來幾節會逐項處理。

## 29.7 解析請求：每一個欄位都是不可信的輸入

HTTP 解析器是 server 上最直接暴露給攻擊者的程式碼。寫解析器時，要假設對方會送出任何 bytes：沒有空行、超長的行、缺欄位、多餘的空白、二進位垃圾、刻意互相矛盾的 header。幾條原則：

**一、先限制大小，再處理內容。** 讀 header 時設定長度上限（nginx 預設 request line 或單一 header 欄位都不能超過 8 KB，也就是 `large_client_header_buffers 4 8k` 中一個緩衝區的大小；`thumbd` 修正後設定 request line 加全部 header 共 8 KB），超過就回 431 並關閉連線。沒有上限的解析器，等於讓任何人都能決定你配置多少記憶體。

**二、在迴圈中讀到 framing 結束。** 持續 `read` 並累積，直到看到 `\r\n\r\n` 或超過上限。這正是 29.1 節長 cookie 問題的修法：舊程式只讀一次，請求超過 1 KB 時就把半截的資料當作完整請求，request line 之後的 header 被切斷，解析失敗。

**三、用有長度限制的函式拆欄位。** `sscanf(line, "%s %s %s", ...)` 沒有寬度限制，一個超長的 URI 就會造成 stack buffer overflow（第 11 章）。要寫成 `%15s %255s %15s`，寬度比緩衝區少 1，留給結尾的 `\0`。

**四、對「看起來合法」的請求也保持懷疑。** header 名稱不分大小寫（`content-length` 與 `Content-Length` 是同一個）；同一個 header 出現兩次、`Content-Length` 與 `Transfer-Encoding` 同時出現，都要明確處理（通常直接拒絕）。前端 proxy 與後端 server 對同一個請求的長度判斷不一致時，攻擊者可以把第二個請求「藏」在第一個請求的 body 裡，這類攻擊叫 **HTTP request smuggling**（請求走私）。最簡單的防禦是：任何有歧義的請求一律回 400。

**五、只接受你支援的東西。** 只實作 GET 就對其他 method 回 501；不認得的 HTTP 版本回 505 或 400。白名單比黑名單安全，因為你不可能列出所有異常輸入。

## 29.8 安全問題：path traversal、slowloris 與 CGI 注入

### Path traversal

**Path traversal**（路徑穿越）是指攻擊者在路徑中放入 `..`，讓 server 讀到網站根目錄以外的檔案。29.1 節的請求是這樣被處理的：

```text
 URI：/originals/../../../etc/passwd
 舊程式：path = "/data/originals/" + "../../../etc/passwd"
        = /data/originals/../../../etc/passwd
 kernel 解析路徑時處理 ..：
   /data/originals → ..  → /data
   /data           → ..  → /
   /               → ..  → /（根目錄的 .. 還是根目錄）
   → /etc/passwd
```

只用字串檢查 `..` 很容易被繞過，常見的繞法有：

| 繞法 | 例子 | 為什麼能繞過 |
|---|---|---|
| percent-encoding | `%2e%2e%2f` | 先檢查、後解碼，檢查時看不到 `..` |
| 雙重編碼 | `%252e%252e` | 解碼兩次才會變成 `..`，某一層多解了一次 |
| 反斜線 | `..\` | 在 Windows 上 `\` 也是路徑分隔符號 |
| symbolic link | 根目錄裡有一個指向 `/` 的 symlink | 路徑字串完全合法，但 kernel 會跟著 link 走 |
| 絕對路徑 | 去掉 `/originals/` 之後剩下 `/etc/passwd` | 有些拼接函式（例如 Python 的 `os.path.join(root, part)`）遇到以 `/` 開頭的參數，會直接丟掉前面的根目錄 |

可靠的做法是分層防禦：

1. 先完整解碼 URI（只解一次），再做所有檢查。
2. 拒絕任何「路徑段」等於 `..` 的請求，以及含有 `\0`、`\` 的路徑。
3. 用 `realpath` 把最終路徑正規化（它會處理 `..` 與 symlink），再檢查結果是否仍以網站根目錄加 `/` 開頭：

```c
/* 片段：檢查 path 正規化後是否仍在 root 底下（root 本身也必須是 realpath 的結果）。 */
char resolved[PATH_MAX];
if (realpath(path, resolved) == NULL) return 404;            /* 不存在或無法解析 */
size_t n = strlen(root);
if (strncmp(resolved, root, n) != 0 || (resolved[n] != '/' && resolved[n] != '\0'))
    return 403;                                              /* 跑到根目錄外面了 */
```

檢查 `resolved[n]` 是為了避免另一個陷阱：根目錄是 `/srv/www` 時，`/srv/www-secret/key` 也以 `/srv/www` 開頭。

4. 最後一道防線是作業系統層級的隔離：讓 server 以低權限使用者執行、只能讀它該讀的目錄，或用 container 與 chroot 限制它看得到的檔案系統。即使程式有漏洞，也讀不到 `/etc/shadow`。

### Header 大小限制與 slowloris

前面說過要限制 header 的大小，但還有一種攻擊不需要送很多資料：**slowloris**。攻擊者開很多條連線，每條都慢慢送 header，例如每 10 秒送一個 byte，永遠不送結束的空行。對 Tiny 這種 iterative server，一條這樣的連線就能讓它停止服務；對每條連線一個 thread 的 server，幾百條連線就能用光 thread pool。

防禦的關鍵是**時間限制**，而不只是大小限制：

- 讀完整個 header 有總時限（例如 10 秒），不是「每次 read 的間隔」時限，否則每 9 秒送一個 byte 就能繞過。nginx 的 `client_header_timeout`（預設 60 秒）就是這類設定：時間內沒收到完整的 header，就回 408 並關閉連線。
- 限制每個 client IP 的同時連線數。
- 讓前面的 proxy（nginx）先把整個請求緩衝起來，再轉交給後端。nginx 用事件驅動的架構（29.11 節），一條閒置的連線只佔用少量記憶體，不佔用 thread，所以比後端更適合承受這類攻擊。

### CGI 與 shell 注入

CGI 把使用者輸入放進環境變數，再執行一支程式。如果那支程式把這些輸入交給 shell 解讀，就可能執行攻擊者的指令。最有名的例子是 2014 年的 **Shellshock**（CVE-2014-6271）：bash 在啟動時會解析環境變數中的函式定義，而有漏洞的版本會把定義後面附加的指令也一起執行。CGI 會把 `User-Agent` 這類 header 放進 `HTTP_USER_AGENT` 環境變數，所以只要 CGI 程式（或它呼叫的任何東西）是 bash script，攻擊者在 `User-Agent` 裡放一段特製字串，就能在 server 上執行任意指令。

本章 29.12 節的範例 CGI 是一支 shell script，所以它在使用 `QUERY_STRING` 之前，會先檢查寬、高是否只含數字：在 shell 的 `$(( ))` 算術展開裡，某些 shell 會把變數內容當作運算式解讀，未經檢查的輸入可能被用來執行指令。一般原則是：

- 永遠不要把使用者輸入拼接進 `system()`、`popen()` 或 shell 指令字串。
- 需要執行外部程式時，用 `execve` 直接傳參數陣列（第 21 章），不經過 shell。
- 對輸入做白名單驗證（只允許數字、只允許特定字元），而不是試圖過濾危險字元。

`thumbd` 用 `fork`／`exec` 呼叫外部轉檔工具處理少數格式時，也遵守同樣的規則：檔名先對應成內部產生的暫存檔名，再以參數陣列傳給工具，使用者提供的字串從來不會經過 shell。

## 29.9 Keep-alive：一條連線送很多個請求

HTTP/1.0 預設每個請求開一條新連線。一張相簿頁面可能有 50 張縮圖，每張都要經過 TCP 三次握手（HTTPS 還要再加 TLS 握手）。HTTP/1.1 把 **persistent connection**（持續連線，俗稱 **keep-alive**）設為預設：回應完畢後連線保持開啟，client 可以在同一條連線上送下一個請求。

手算差異。假設 client 與 server 的來回延遲（RTT，round-trip time）是 50 ms，server 處理時間忽略不計，要依序抓 10 張縮圖：

```text
 每個請求一條新連線：
   每張 = 1 RTT（三次握手）＋ 1 RTT（請求與回應） = 2 RTT
   10 張 = 20 RTT = 20 × 50 ms = 1000 ms

 keep-alive，同一條連線：
   第一張 = 1 RTT（握手）＋ 1 RTT
   之後每張 = 1 RTT
   10 張 = 1 + 10 = 11 RTT = 550 ms

   ┌握手┐┌req1┐┌req2┐┌req3┐ ... ┌req10┐
   └────┘└────┘└────┘└────┘     └─────┘   ← 只握手一次
```

如果是 HTTPS，每條新連線還要加上 TLS 握手（TLS 1.3 約 1 RTT、TLS 1.2 約 2 RTT），差距更大。keep-alive 也直接解決了第 28 章提到的 TIME_WAIT 與 ephemeral port 耗盡問題，因為新建的連線少了很多。

keep-alive 有一個前提：**每個回應都必須有明確的結尾**。因為連線不會關閉，client 不能再用 EOF 判斷 body 結束，所以回應一定要帶 `Content-Length` 或使用 chunked 編碼。server 也要能在讀完一個請求之後，繼續解析同一條連線上的下一個請求，而且下一個請求的開頭可能已經和上一個請求一起被讀進緩衝區裡（byte stream 不保留邊界），解析器不能把這些 bytes 丟掉。

keep-alive 的代價是 server 要維護許多閒置連線。每條閒置連線都佔用一個 descriptor 與一些記憶體；如果是每條連線一個 thread 的 server，還佔用一個 thread。所以 server 會設定閒置逾時（nginx 的 `keepalive_timeout` 預設 75 秒），並限制每條連線最多服務幾個請求。

HTTP/1.1 的 keep-alive 仍然一次只能處理一個請求：前一個回應沒送完，後一個就得等，這叫 **head-of-line blocking**（隊頭阻塞）。**HTTP/2** 改成二進位格式，在一條 TCP 連線上同時交錯傳送多個請求與回應的 frame；**HTTP/3** 改用建立在 UDP 上的 QUIC，連 TCP 層的隊頭阻塞也一起避開。它們的語意（method、status code、header）和 HTTP/1.1 相同，改變的是 framing 與連線管理。

## 29.10 Proxy：站在 client 與 server 中間

**Proxy**（代理伺服器）是一個同時扮演 server 與 client 的程式：它接受 client 的請求（server 的角色），再向真正的 server 發出請求（client 的角色），把回應轉回去。依照它替誰服務，分成兩種：

```text
 forward proxy（替 client 服務，例如公司對外的上網代理）
   員工瀏覽器 ──▶ [公司 proxy] ──▶ 網際網路上的任何網站
                   控管、記錄、快取

 reverse proxy（替 server 服務，例如拾光相簿的 nginx）
   使用者 ──HTTPS──▶ [nginx] ──HTTP keep-alive──▶ thumbd-1
                     │  TLS 終結           ├────▶ thumbd-2
                     │  負載平衡           └────▶ thumbd-3
                     │  限制大小與速率
                     │  快取熱門縮圖
                     └─ 緩衝慢速 client 的請求與回應
```

拾光相簿的架構裡，`thumbd` 從來不直接面對使用者，前面一定有 nginx。這帶來幾個好處：TLS 加解密集中在 nginx；nginx 先把整個請求收完才轉給 `thumbd`，慢速 client 與 slowloris 只會消耗 nginx 的資源；nginx 可以快取熱門縮圖，命中時根本不必打擾 `thumbd`；某一台 `thumbd` 掛掉時，nginx 把流量轉給其他台，使用者看到的是 502 而不是連線逾時。

寫一個 proxy 的難處，在於它同時具有 client 與 server 的所有問題：要正確解析 client 的請求、改寫部分 header（例如把完整的 URL 改成 path、處理 `Connection` header）、對 upstream 建立連線、用迴圈轉送任意長度的回應、處理任何一端中途斷線，還要能同時服務很多 client。

### Proxy Lab 的學習目標

CS:APP 的 **Proxy Lab** 要求學生寫一個 HTTP proxy，分成三個階段。這裡只說明每個階段在練什麼，不提供解答：

| 階段 | 要做到什麼 | 練到的能力 |
|---|---|---|
| 循序 proxy | 接受請求、解析 URL、向目標 server 轉發、把回應送回 client | HTTP 格式、本章的解析原則、第 28 章的 socket 與 short count 處理 |
| 並行 proxy | 同時服務多個 client，一個慢的 client 不影響其他人 | 第 30 章的 thread 模型、descriptor 的擁有權與關閉 |
| 快取 | 在記憶體裡快取小的回應，總量有上限，用近似 LRU 淘汰 | 第 31、32 章的同步（readers-writers）、thread safety |

做這個 lab 時最常卡住的地方，往往不是 HTTP 本身，而是本書前面幾章的基本功：忘了處理 short count、對已關閉的連線寫入導致 SIGPIPE、錯誤路徑漏掉 `close`、快取的資料結構在多執行緒下沒有保護。把它當成第 27 到 32 章的綜合練習，比當成「寫 HTTP」更貼切。

## 29.11 從 Tiny 到 thumbd，再到 nginx

Tiny 和 production 的 web server 用的是同一套 HTTP 與 socket API，差別在於如何同時處理很多連線，以及如何面對不友善的網路。三者對照：

| 面向 | Tiny | `thumbd`（修正後） | nginx |
|---|---|---|---|
| 並行模型 | iterative，一次一條連線 | 一個 accept thread ＋ thread pool（第 30 章） | 少數 worker process，每個跑一個事件迴圈（Linux 上用 epoll） |
| 一條閒置連線的成本 | 整台 server 被它佔住 | 佔用一個 worker thread | 一個 descriptor 加少量記憶體 |
| 讀取請求 | RIO 逐行讀 | 迴圈讀到 `\r\n\r\n`，8 KB 上限，10 秒總時限 | 非阻塞讀取，狀態機解析，可設定緩衝區大小與逾時 |
| 路徑安全 | 未處理 | 解碼後檢查路徑段、`realpath` 比對根目錄 | 正規化 URI，設定檔決定根目錄 |
| 動態內容 | CGI，每個請求 fork／exec | 自己就是應用程式，在 thread 裡直接處理 | 不自己產生，轉交 upstream（proxy、FastCGI） |
| 送出檔案 | `mmap` ＋ 寫入 socket | `read`／`write` 迴圈 | 可開啟 `sendfile`（nginx 預設關閉，正式環境常打開），由 kernel 直接從 page cache 送到 socket |
| keep-alive | 不支援 | 支援，閒置逾時 | 支援，可對 client 與 upstream 分別設定 |

**事件驅動**（event-driven）是 nginx 能用少量資源服務大量連線的原因。它不為每條連線準備一個 thread，而是把所有 socket 設成 nonblocking，交給 epoll 這類機制監看；哪條連線有資料可讀、哪條可以寫，就處理那一條的「下一小步」，處理完立刻回到迴圈。每條連線的進度（讀到 header 的哪裡、回應送了多少）存在一個小的狀態結構裡，而不是存在 thread 的 stack 上。第 30 章會詳細比較這幾種並行模型。

這也說明了為什麼 `thumbd` 不需要自己變成 nginx：縮圖是 CPU 密集的工作，用 thread pool 平行處理很合理；而大量閒置連線、慢速 client、TLS 這些「網路面」的問題，交給前面的 nginx 處理更有效率。

## 29.12 動手做：解析請求，並跑一台迷你 web server

### 程式一：request line 解析與路徑檢查

先把最容易出錯的兩件事抽出來單獨測試：拆解 request line，以及把 URI 對應到檔案路徑並拒絕危險的路徑。

```c
#include <stdio.h>
#include <string.h>

/* 解析 request line："GET /thumb/cat.jpg?w=200 HTTP/1.1"。成功回傳 0。 */
static int parse_request_line(const char *line, char *method, char *uri, char *version) {
    /* 寬度限制讓 sscanf 不會寫出 buffer 外：method 15、uri 255、version 15 個字元 */
    if (sscanf(line, "%15s %255s %15s", method, uri, version) != 3) return -1;
    if (strncmp(version, "HTTP/1.", 7) != 0) return -1;
    return 0;
}

/* 把 uri 拆成路徑與 query，並決定對應到 www/ 底下的哪個檔案。
 * 回傳 1 = 動態內容（/cgi-bin/）、0 = 靜態檔案、-1 = 拒絕。 */
static int resolve(const char *uri, char *path, size_t pathsz, char *query, size_t qsz) {
    char copy[256];
    snprintf(copy, sizeof copy, "%s", uri);
    char *q = strchr(copy, '?');
    snprintf(query, qsz, "%s", q ? q + 1 : "");
    if (q) *q = '\0';
    if (copy[0] != '/') return -1;                    /* 一定要是絕對路徑 */
    for (char *s = copy; (s = strstr(s, "..")) != NULL; s += 2)   /* 任何 .. 路徑段都拒絕 */
        if ((s == copy || s[-1] == '/') && (s[2] == '/' || s[2] == '\0')) return -1;
    if (strchr(copy, '%') || strchr(copy, '\\')) return -1;   /* 這個簡化版不解碼 %xx，乾脆拒絕 */
    int dynamic = strncmp(copy, "/cgi-bin/", 9) == 0;
    snprintf(path, pathsz, "www%s%s", copy, copy[strlen(copy) - 1] == '/' ? "index.html" : "");
    return dynamic;
}

int main(void) {
    const char *lines[] = {
        "GET /index.html HTTP/1.1",
        "GET / HTTP/1.0",
        "GET /cgi-bin/bufsize?800&600 HTTP/1.1",
        "GET /../../etc/passwd HTTP/1.1",
        "GET /img/..%2f..%2fetc/passwd HTTP/1.1",
        "GET /notes..txt HTTP/1.1",
        "HELLO",
    };
    for (size_t i = 0; i < sizeof lines / sizeof lines[0]; i++) {
        char method[16], uri[256], version[16], path[300], query[256];
        printf("%-40s → ", lines[i]);
        if (parse_request_line(lines[i], method, uri, version) < 0) { puts("400 Bad Request"); continue; }
        int kind = resolve(uri, path, sizeof path, query, sizeof query);
        if (kind < 0) puts("403 Forbidden");
        else printf("%s %s%s%s\n", kind ? "動態" : "靜態", path, kind ? " 參數=" : "", kind ? query : "");
    }
    return 0;
}
```

在 macOS arm64（Apple clang 21）上執行：

```text
GET /index.html HTTP/1.1                 → 靜態 www/index.html
GET / HTTP/1.0                           → 靜態 www/index.html
GET /cgi-bin/bufsize?800&600 HTTP/1.1    → 動態 www/cgi-bin/bufsize 參數=800&600
GET /../../etc/passwd HTTP/1.1           → 403 Forbidden
GET /img/..%2f..%2fetc/passwd HTTP/1.1   → 403 Forbidden
GET /notes..txt HTTP/1.1                 → 靜態 www/notes..txt
HELLO                                    → 400 Bad Request
```

逐行看：

1. 前三行是正常請求：結尾是 `/` 的路徑補上 `index.html`；`/cgi-bin/` 開頭的被判為動態內容，`?` 後面的 `800&600` 被拆出來，之後會成為 CGI 的 `QUERY_STRING`。
2. 第四行的 `..` 是完整的路徑段，被拒絕。
3. 第五行用 percent-encoding 把 `/` 藏成 `%2f`。逐字檢查時 `..` 後面接的是 `%` 而不是 `/`，路徑段檢查**抓不到它**；是後面「含 `%` 一律拒絕」的規則擋下的。這正好示範了 29.8 節的重點：檢查必須在解碼之後做。這個簡化版選擇不支援 percent-encoding；真實的 server 要先解碼一次，再對解碼結果做路徑段檢查與 `realpath` 比對。
4. 第六行 `notes..txt` 的 `..` 不是獨立的路徑段，是合法的檔名，所以放行。只要用 `strstr(uri, "..")` 一律拒絕，就會誤擋這種檔名。誤擋比放行安全，但要知道自己做了什麼取捨。
5. `HELLO` 只有一個欄位，`sscanf` 回傳 1 而不是 3，回 400。

### 程式二：迷你 web server，靜態、動態與錯誤處理

這支程式在目前目錄下建立 `www/index.html` 與一支 CGI 程式 `www/cgi-bin/bufsize`（shell script，計算縮圖緩衝區大小），然後 `fork`：父行程是 iterative web server，子行程扮演瀏覽器，依序送出六個請求，最後兩者都自行結束。

```c
#define _DEFAULT_SOURCE   /* 讓 Linux 的 -std=c17 也宣告 setenv 等 POSIX 函式；macOS 忽略它 */
#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define MAX_HEADER 8192                     /* request line ＋ header 的上限 */

static int writen(int fd, const char *p, size_t n) {
    while (n > 0) {
        ssize_t k = write(fd, p, n);
        if (k <= 0) return -1;
        p += k, n -= (size_t)k;
    }
    return 0;
}

static void respond(int fd, int code, const char *reason, const char *type, const char *body, size_t len) {
    char hdr[256];
    int n = snprintf(hdr, sizeof hdr, "HTTP/1.0 %d %s\r\nServer: mini-thumbd\r\nConnection: close\r\n"
                     "Content-Type: %s\r\nContent-Length: %zu\r\n\r\n", code, reason, type, len);
    writen(fd, hdr, (size_t)n);
    writen(fd, body, len);
}

static int fail(int fd, int code, const char *reason) {
    respond(fd, code, reason, "text/plain", "", 0);
    return code;
}

static const char *mime(const char *path) {
    const char *dot = strrchr(path, '.');
    if (dot && strcmp(dot, ".html") == 0) return "text/html; charset=utf-8";
    if (dot && strcmp(dot, ".jpg") == 0) return "image/jpeg";
    return "application/octet-stream";
}

static int serve(int fd) {                  /* 處理一個連線，回傳狀態碼（給 access log 用） */
    char req[MAX_HEADER + 1], method[16], uri[256], version[16], path[300];
    size_t used = 0;
    req[0] = '\0';
    while (!strstr(req, "\r\n\r\n")) {      /* 讀到空行為止：header 結束 */
        if (used == MAX_HEADER) return fail(fd, 431, "Request Header Fields Too Large");
        ssize_t n = read(fd, req + used, MAX_HEADER - used);
        if (n <= 0) return 0;               /* client 中途斷線 */
        used += (size_t)n;
        req[used] = '\0';
    }
    if (sscanf(req, "%15s %255s %15s", method, uri, version) != 3)
        return fail(fd, 400, "Bad Request");
    if (strcmp(method, "GET") != 0)
        return fail(fd, 501, "Not Implemented");
    char *query = strchr(uri, '?');
    if (query) *query++ = '\0';
    if (uri[0] != '/' || strstr(uri, "..") || strchr(uri, '%'))   /* 保守：含 .. 或 % 一律拒絕 */
        return fail(fd, 403, "Forbidden");
    snprintf(path, sizeof path, "www%s%s", uri, strcmp(uri, "/") == 0 ? "index.html" : "");
    struct stat st;
    if (stat(path, &st) < 0 || !S_ISREG(st.st_mode))
        return fail(fd, 404, "Not Found");
    if (strncmp(uri, "/cgi-bin/", 9) == 0) {        /* 動態內容：fork ＋ exec 一支程式 */
        const char *first = "HTTP/1.0 200 OK\r\nServer: mini-thumbd\r\n";   /* 其餘 header 由 CGI 印 */
        writen(fd, first, strlen(first));
        pid_t pid = fork();
        if (pid == 0) {
            setenv("QUERY_STRING", query ? query : "", 1);
            dup2(fd, STDOUT_FILENO);                /* CGI 程式的 stdout 直接接到 socket */
            execl(path, path, (char *)NULL);
            _exit(127);
        }
        waitpid(pid, NULL, 0);                      /* 回收子程序，避免 zombie（第 21 章） */
        return 200;
    }
    char body[4096];                                /* 靜態內容：讀檔、加上 header 送出 */
    int file = open(path, O_RDONLY);
    ssize_t len = read(file, body, sizeof body);    /* 範例檔案很小；真實 server 要迴圈或 sendfile */
    close(file);
    respond(fd, 200, "OK", mime(path), body, len > 0 ? (size_t)len : 0);
    return 200;
}

static void put_file(const char *path, const char *text, mode_t mode) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, mode);
    writen(fd, text, strlen(text));
    close(fd);
}

int main(void) {
    signal(SIGPIPE, SIG_IGN);           /* 對方先關閉時，write 回傳 EPIPE 而不是殺掉 process */
    mkdir("www", 0755);
    mkdir("www/cgi-bin", 0755);
    put_file("www/index.html", "<h1>拾光相簿</h1>\n", 0644);
    put_file("www/cgi-bin/bufsize",     /* 一支用 shell 寫的 CGI 程式：算縮圖緩衝區大小 */
             "#!/bin/sh\nw=${QUERY_STRING%%&*}; h=${QUERY_STRING#*&}\n"
             "case \"$w\" in ''|*[!0-9]*) w=0;; esac\n"      /* 只接受數字：別把使用者輸入丟進 $(( )) */
             "case \"$h\" in ''|*[!0-9]*) h=0;; esac\n"
             "body=\"$w x $h x 4 = $((w * h * 4)) bytes\"\n"
             "printf 'Content-Type: text/plain\\r\\nContent-Length: %d\\r\\n\\r\\n%s\\n' "
             "$((${#body} + 1)) \"$body\"\n", 0755);

    int lfd = socket(AF_INET, SOCK_STREAM, 0), one = 1;
    struct sockaddr_in addr = {.sin_family = AF_INET, .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
    socklen_t alen = sizeof addr;
    setsockopt(lfd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    bind(lfd, (struct sockaddr *)&addr, sizeof addr);
    listen(lfd, 16);
    getsockname(lfd, (struct sockaddr *)&addr, &alen);   /* 取得 kernel 挑的 port */

    static char big[10000];
    memset(big, 'x', sizeof big - 1);
    char huge[10100];
    snprintf(huge, sizeof huge, "GET / HTTP/1.1\r\nCookie: %s\r\n\r\n", big);
    const char *reqs[] = {
        "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n",
        "GET /cgi-bin/bufsize?800&600 HTTP/1.1\r\nHost: localhost\r\n\r\n",
        "GET /../../etc/passwd HTTP/1.1\r\nHost: localhost\r\n\r\n",
        "GET /cat.jpg HTTP/1.1\r\nHost: localhost\r\n\r\n",
        "POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n",
        huge,
    };
    int nreq = (int)(sizeof reqs / sizeof reqs[0]);
    fflush(stdout);
    if (fork() == 0) {                  /* 子程序：扮演瀏覽器，依序送出每個請求 */
        for (int i = 0; i < nreq; i++) {
            int fd = socket(AF_INET, SOCK_STREAM, 0);
            connect(fd, (struct sockaddr *)&addr, sizeof addr);
            writen(fd, reqs[i], strlen(reqs[i]));
            shutdown(fd, SHUT_WR);
            char resp[2048];
            size_t got = 0;
            ssize_t n;
            while (got < sizeof resp - 1 && (n = read(fd, resp + got, sizeof resp - 1 - got)) > 0) got += (size_t)n;
            resp[got] = '\0';
            char *body = strstr(resp, "\r\n\r\n");
            printf("請求 %d → %.*s｜body：%s", i + 1, (int)strcspn(resp, "\r"), resp,
                   body && body[4] ? body + 4 : "（空）\n");
            close(fd);
        }
        fflush(stdout);
        _exit(0);
    }
    int codes[8];
    for (int i = 0; i < nreq; i++) {    /* 父程序：iterative server，一次服務一個連線 */
        int fd = accept(lfd, NULL, NULL);
        codes[i] = serve(fd);
        shutdown(fd, SHUT_WR);           /* 先送 FIN，再把 client 剩下的資料讀完才關 */
        char sink[512];
        while (read(fd, sink, sizeof sink) > 0) {}
        close(fd);
    }
    wait(NULL);                          /* 等 client 印完，再印 server 的紀錄 */
    printf("[server] 依序回應：");
    for (int i = 0; i < nreq; i++) printf("%d ", codes[i]);
    printf("\n");
    return 0;
}
```

在 macOS arm64（Apple clang 21）上執行，整支程式約半秒結束：

```text
請求 1 → HTTP/1.0 200 OK｜body：<h1>拾光相簿</h1>
請求 2 → HTTP/1.0 200 OK｜body：800 x 600 x 4 = 1920000 bytes
請求 3 → HTTP/1.0 403 Forbidden｜body：（空）
請求 4 → HTTP/1.0 404 Not Found｜body：（空）
請求 5 → HTTP/1.0 501 Not Implemented｜body：（空）
請求 6 → HTTP/1.0 431 Request Header Fields Too Large｜body：（空）
[server] 依序回應：200 200 403 404 501 431 
```

逐段解說：

1. **讀取 header 的迴圈**（`serve` 開頭）：不斷 `read` 並累積，直到出現 `\r\n\r\n`；緩衝區滿了還沒看到空行就回 431。請求 6 帶了將近 10 KB 的 cookie，正是這條路徑。這段迴圈就是 29.1 節長 cookie 問題的修法。注意迴圈前的 `req[0] = '\0'` 不能省：少了它，第一次 `strstr` 會讀到 stack 上殘留的舊資料（例如上一個請求的內容），可能誤以為 header 已經結束，結果每個回應都錯位一個請求。未初始化的緩衝區（第 26 章）在網路程式裡特別容易造成這種「看起來是協定錯誤」的 bug。
2. **檢查順序**：先檢查格式（400）、再檢查 method（501）、再檢查路徑安全（403）、最後才碰檔案系統（404）。越早拒絕，攻擊者能觸及的程式碼越少。請求 3 的 `..` 在呼叫 `stat` 之前就被擋下。這個版本比程式一更保守：路徑中只要出現 `..` 就拒絕。
3. **靜態內容**：請求 1 讀出 `www/index.html`，依副檔名設定 `Content-Type`，用 `Content-Length` 告訴 client body 的長度。`<h1>拾光相簿</h1>\n` 是 9 個 ASCII 字元、4 個中文字（各 3 bytes）、1 個換行，共 22 bytes，`Content-Length` 就是 22，不是 14。
4. **動態內容**：請求 2 走 29.5 節的 CGI 流程。server 先寫 status line，`fork` 出子行程；子行程設定 `QUERY_STRING`、`dup2` 把 socket 接到標準輸出、`execl` 執行 shell script。script 印出自己的 `Content-Type`、`Content-Length: 30`（29.4 節手算的結果）與 body。server 端用 `waitpid` 回收子行程。CGI script 在算術運算前先確認寬、高只含數字，這是 29.8 節的注入防護。
5. **關閉連線的順序**：server 回應後先 `shutdown(fd, SHUT_WR)` 送出 FIN，再把 client 剩下沒讀的資料讀完才 `close`。這對請求 6 很重要：server 只讀了 8 KB 就回 431，client 送的其餘資料還在 receive buffer 裡。如果直接 `close`，kernel 會送出 RST（第 28 章），client 可能還沒讀到 431 回應就收到 connection reset。nginx 把這個做法叫 lingering close。
6. **SIGPIPE**：`main` 一開始就忽略 SIGPIPE。如果 client 在回應送完之前就關閉連線，`write` 會回傳 `EPIPE`，而不是讓整個 server 被 signal 終止。

這支程式仍然是 iterative 的，也沒有逾時：在「瀏覽器」那一端加一個「連上之後什麼都不送」的連線，server 就會永遠卡在 `read`。這是 29.14 節的練習之一，也是第 30 章要解決的問題。

## 29.13 在工作上怎麼用

### 用 curl 與 nc 觀察與重現

`curl` 是 HTTP 除錯的第一個工具，`nc` 則讓你送出任何 bytes，包括瀏覽器絕對不會送的請求：

```bash
curl -v http://localhost:8080/thumb/cat.jpg?w=200 -o /dev/null   # 看完整的請求與回應 header
curl -sS -o /dev/null -w '%{http_code} %{time_connect} %{time_starttransfer} %{time_total}\n' \
     http://localhost:8080/thumb/cat.jpg?w=200                    # 狀態碼與各階段時間
curl --path-as-is 'http://localhost:8080/originals/../../etc/passwd'   # 不讓 curl 整理 ..
curl -H "Cookie: $(head -c 9000 /dev/zero | tr '\0' x)" http://localhost:8080/   # 超長 header
printf 'GET / HTTP/1.1\r\nHost: x\r\n\r\n' | nc localhost 8080     # 手寫原始請求
```

`-w` 的時間拆解特別有用：`time_connect` 很長表示連線建立慢（網路、accept queue 滿了），`time_starttransfer` 減去 `time_connect` 很長表示 server 處理慢，`time_total` 減去 `time_starttransfer` 很長表示傳輸慢（回應很大或網路頻寬不足）。

### HTTP 解析器的安全檢查清單

每次修改 `thumbd` 的請求處理邏輯，小安都用這份清單逐項確認，並把每一項寫成自動化測試：

- [ ] request line 加 header 有總大小上限，超過回 431 或 400
- [ ] 讀取 header 有總時限，不是每次 `read` 的時限
- [ ] 所有字串欄位的拆解都有長度限制（`%255s`、`snprintf`）
- [ ] URI 只解碼一次，所有路徑檢查都在解碼之後
- [ ] 拒絕 `..` 路徑段、`\0`、`\`；`realpath` 後確認仍在根目錄下
- [ ] 只接受支援的 method 與版本，其他一律明確拒絕
- [ ] `Content-Length` 與 `Transfer-Encoding` 同時出現、或 `Content-Length` 重複時拒絕
- [ ] body 有大小上限，超過回 413
- [ ] 回應的 `Content-Type` 由 server 決定，加上 `nosniff`
- [ ] 不把任何使用者輸入交給 shell
- [ ] 忽略 SIGPIPE，處理 `EPIPE` 與 `ECONNRESET`

### 讀懂 nginx 回給使用者的 5xx

`thumbd` 在 nginx 後面時，使用者看到的錯誤大多是 nginx 產生的，要學會從狀態碼推回 `thumbd` 發生了什麼：

```text
 nginx 回給使用者的狀態碼
   │
   ├─ 502 Bad Gateway
   │    └─ nginx 連不上 thumbd（connection refused：thumbd 沒在跑或 port 錯），
   │       或 thumbd 回了無法解析的回應、中途 reset（例如 crash）
   │       → 看 nginx error log 的 upstream 錯誤訊息；看 thumbd 是否重啟過
   │
   ├─ 504 Gateway Timeout
   │    └─ thumbd 在 proxy_read_timeout（預設 60 秒）內沒有送出任何資料
   │       （這是兩次讀取之間的間隔，不是整個回應的總時限）
   │       → thumbd 卡住或過載：看 thumbd 的 thread 是否全忙、accept queue 是否堆積
   │
   ├─ 499（nginx 自訂，只出現在 access log）
   │    └─ client 在 nginx 回應前就關閉連線：使用者不耐煩離開，或 client 的逾時太短
   │       → 499 和 504 同時上升通常是同一件事：後端變慢
   │
   └─ 413、414、400 "Request Header Or Cookie Too Large"
        └─ nginx 自己的大小限制擋下了請求，根本沒送到 thumbd
           → 檢查 client_max_body_size、large_client_header_buffers
```

### 讓 nginx 對 thumbd 使用 keep-alive

nginx 1.29.7 之前的版本，對 upstream 預設使用 HTTP/1.0、送出 `Connection: close`，每個請求後關閉連線；要啟用 keep-alive 需要下面三個設定一起出現。依 nginx 官方文件，從 1.29.7 起預設已改成 HTTP/1.1，upstream 也預設保留 `keepalive 32` 條閒置連線，但許多發行版內建的仍是較舊的版本，先用 `nginx -v` 確認版本，明確寫出來也不會錯：

```text
upstream thumbd {
    server 10.0.1.5:8080;
    server 10.0.1.6:8080;
    keepalive 32;                      # 每個 worker 保留的閒置連線數
}
server {
    location /thumb/ {
        proxy_pass http://thumbd;
        proxy_http_version 1.1;        # upstream 改用 HTTP/1.1（1.29.7 之前預設是 1.0）
        proxy_set_header Connection "";  # 清掉 1.29.7 之前預設送出的 Connection: close
        proxy_read_timeout 10s;        # 比預設的 60 秒短，配合 thumbd 的處理時間
    }
}
```

這個設定（示意，依你的部署調整）讓 nginx 與 `thumbd` 之間的連線被重複使用，同時解決了第 28 章提到的 TIME_WAIT 累積與 ephemeral port 耗盡。對應地，`thumbd` 這一側必須正確實作 keep-alive：每個回應都帶 `Content-Length`，並在同一條連線上繼續讀下一個請求。

## 29.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 少數請求解析失敗，通常是帶大 cookie 的使用者 | 只 `read` 一次就當作完整請求，或緩衝區太小 | 用 `curl -H` 送超長 header 重現；`strace` 看每次 `read` 的長度 | 迴圈讀到 `\r\n\r\n`，設定明確上限並回 431 |
| 讀得到網站根目錄外的檔案 | 路徑拼接沒有檢查 `..`，或在解碼前檢查 | `curl --path-as-is` 送 `..` 與 `%2e%2e` | 解碼後檢查路徑段，`realpath` 比對根目錄，低權限執行 |
| 瀏覽器顯示的圖片被截斷，或一直轉圈不結束 | `Content-Length` 與實際 body 長度不符（常見是用字元數而非 byte 數） | `curl -v` 比對 header 與實際收到的 bytes | 用實際寫出的 byte 數計算；不確定長度就用 chunked |
| CGI 請求越多，`ps` 裡 `<defunct>` 越多 | 父行程沒有 `waitpid` 子行程 | `ps -ef | grep defunct`，父行程是 web server | 每個 `fork` 都要配對 `waitpid`，或用 SIGCHLD handler 回收（第 22 章） |
| client 偶爾收到 connection reset 而不是錯誤頁 | server 還有未讀的請求資料時就 `close`，kernel 送 RST | `tcpdump` 看到 server 送出 `[R]` | 先 `shutdown(SHUT_WR)`，讀完剩餘資料（設時限）再 `close` |
| server 偶爾整個消失，沒有 core dump | client 提早斷線，寫入時收到 SIGPIPE | 結束碼 141；`strace` 看到 SIGPIPE | `signal(SIGPIPE, SIG_IGN)`，處理 `EPIPE` |
| 少量連線就讓 server 停止回應 | iterative server 或 thread 數固定，又沒有讀取逾時（slowloris） | `ss -tn` 看到很多連線，但幾乎沒有資料流動 | 讀取總時限、每 IP 連線上限、前面放 nginx |

## 29.15 動手練習

1. **手算**：一個回應的 body 是 `{"w":200,"h":150}`（不含換行），`Content-Length` 應該是多少？如果把它用 chunked 編碼分成 8 bytes 與其餘兩塊送出，寫出完整的 chunked body。（驗證方法：用 Python 的 `len(b'{"w":200,"h":150}')` 確認長度，答案是 17；第二塊是 9 bytes，長度行寫 `9`。）
2. **手算**：RTT 是 80 ms，HTTPS 使用 TLS 1.3（多 1 RTT），依序抓 20 張縮圖。比較每次新建連線與 keep-alive 的總時間（忽略 server 處理時間與傳輸時間）。（答案：每次新建連線每張 3 RTT，共 60 RTT = 4.8 秒；keep-alive 為 2 + 20 = 22 RTT = 1.76 秒。）
3. 擴充程式二的 `serve`：在拆出 URI 之後實作 percent-decoding（`%` 後面兩個十六進位字元轉成一個 byte），解碼後再檢查 `..` 路徑段，並加入請求 `GET /%2e%2e/%2e%2e/etc/passwd` 確認仍然回 403。
4. 修改程式二，讓 server 對每條連線用 `setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, ...)` 設定 2 秒的讀取逾時；在「瀏覽器」的請求清單最前面加一條「連上之後什麼都不送就等待」的連線，確認 server 會在 2 秒後放棄它、繼續服務後面的請求。思考：這個逾時能防禦每 1 秒送一個 byte 的 slowloris 嗎？為什麼不能？
5. 把程式二改成支援 keep-alive：回應改成 `HTTP/1.1`、移除 `Connection: close`，`serve` 處理完一個請求後保留緩衝區裡剩下的 bytes，繼續在同一條連線上處理下一個請求，直到 client 關閉連線。讓「瀏覽器」在一次 `write` 裡送出兩個請求，確認兩個都得到回應。
6. 用 `curl -w` 量測你工作上某個 HTTP 服務的 `time_connect`、`time_starttransfer` 與 `time_total`，分別在加上 `-H 'Connection: close'` 與不加的情況下連續請求 10 次，比較兩者的差異。

## 本章重點整理

- HTTP/1.x 是建立在 TCP 上的文字協定，請求由 request line、header、空行與可選的 body 組成，回應由 status line、header、空行與 body 組成，行尾是 `\r\n`。
- URL 由 scheme、host、port、path、query、fragment 組成；client 只把 path 與 query 送給 server，fragment 永遠不會送出。
- MIME type 告訴 client 如何解讀 body；server 應自己決定內容類型，避免使用者上傳的內容被當作 HTML 執行。
- header 以空行結束，body 以 `Content-Length`、chunked 編碼或關閉連線結束；`Content-Length` 是 byte 數，chunk 長度是十六進位。
- 靜態內容是事先存在的檔案；動態內容由程式在請求時產生。CGI 用 `fork`、環境變數、`dup2` 與 `execve` 執行外部程式，把它的標準輸出直接接到 socket，父行程必須 `waitpid`。
- Tiny 展示了 web server 的完整骨架：accept、讀 request line 與 header、解析 URI、判斷靜態或動態、送出回應或錯誤，但它是 iterative、沒有逾時、沒有路徑防護的教學版本。
- HTTP 解析器要先限制大小再處理內容、在迴圈中讀到 framing 結束、用有長度限制的函式拆欄位，並拒絕任何有歧義的請求以防 request smuggling。
- Path traversal 要在 URI 解碼之後檢查路徑段，再用 `realpath` 確認最終路徑仍在根目錄下，並以低權限執行 server 作為最後防線。
- slowloris 用極慢的請求佔住連線，防禦需要讀取 header 的總時限與每個 IP 的連線上限，而不只是大小限制。
- 不要把使用者輸入交給 shell；Shellshock 顯示了 CGI 把 header 放進環境變數再交給 bash 的風險。
- keep-alive 讓一條連線服務多個請求，省下握手的 RTT 並減少 TIME_WAIT，但要求每個回應都有明確的長度，server 也要管理閒置連線。
- reverse proxy（例如 nginx）負責 TLS、負載平衡、緩衝慢速 client 與快取，讓後端的 `thumbd` 專心處理縮圖；502、504、499 分別指向後端連不上、後端逾時與 client 提早離開。
- nginx 用少數 worker process 加上事件迴圈處理大量連線，`thumbd` 用 thread pool 處理 CPU 密集的工作，兩者分工比各自包辦所有事情更有效率。

## 延伸問答

> [!question]- Q1. HTTP server 怎麼知道一個請求的 header 已經結束？為什麼只呼叫一次 `read` 是錯的？
> HTTP 用一個空行（連續的 `\r\n\r\n`）標記 header 結束，這是它在 TCP byte stream 上的 framing。TCP 不保留訊息邊界，一個請求可能被切成好幾段到達，所以 server 必須在迴圈中持續 `read` 並把資料累積起來，直到在累積的內容中找到 `\r\n\r\n`，或累積量超過設定的上限。
>
> 只呼叫一次 `read`，在 loopback 測試中幾乎都會拿到完整請求，但在真實網路上，或請求比緩衝區大（例如帶了很長的 cookie）時，就只會拿到一部分，導致解析失敗或把半截的 header 當成完整請求。反過來，一次 `read` 也可能讀到 header 之後的 body，甚至 keep-alive 時的下一個請求開頭，這些 bytes 都要保留給後續處理。

> [!question]- Q2. 手算題：一個 chunked 回應的 body 是 `1a\r\n` 加 26 bytes 資料加 `\r\n`，再加 `0\r\n\r\n`。實際資料共有幾個 bytes？
> chunk 的長度欄位是十六進位，`1a` = 1 × 16 + 10 = 26，所以第一個 chunk 有 26 bytes 資料；長度 `0` 的 chunk 表示結束。實際資料總共 26 bytes。
>
> 常見的錯誤是把 `1a` 當成無法解析的字串，或把 `10` 當成十進位的 10。另外要注意每個 chunk 的資料後面還有一個 `\r\n`，它不算在 chunk 長度裡；最後的 `0\r\n` 之後可以接 trailer header，再以空行結束。解析 chunked 時也要限制每個 chunk 的長度與總長度，避免攻擊者寫一個極大的十六進位數造成整數溢位或過量配置。

> [!question]- Q3. 為什麼 CGI 程式只要 `printf`，輸出就會送到瀏覽器？它是怎麼拿到請求參數的？
> web server 在 `fork` 出子行程之後、`execve` 之前，呼叫 `dup2(connfd, STDOUT_FILENO)`，讓 descriptor 1（標準輸出）指向和 connected socket 相同的 open file（第 27 章）。`execve` 會保留已開啟的 descriptor，所以新程式的 `printf` 寫入標準輸出，實際上就是寫進 socket，CGI 程式完全不需要知道網路的存在。
>
> 參數則透過環境變數傳遞：server 在 `execve` 之前用 `setenv` 設定 `QUERY_STRING`、`REQUEST_METHOD`、`CONTENT_LENGTH` 等變數，`execve` 會把環境傳給新程式。POST 的 body 則被接到 CGI 程式的標準輸入，由程式依 `CONTENT_LENGTH` 讀取。這是第 21 章 process 控制與第 27 章 I/O 重新導向最直接的應用。

> [!question]- Q4. 你在 code review 看到 `if (strstr(uri, "..")) return 403;` 之後才對 URI 做 percent-decoding。這樣安全嗎？
> 不安全。攻擊者可以把 `..` 寫成 `%2e%2e`，把 `/` 寫成 `%2f`。檢查時字串裡沒有 `..`，通過檢查；解碼之後卻變成 `../`，路徑就穿越到根目錄外面了。檢查與解碼的順序錯誤，是 path traversal 漏洞最常見的成因之一，雙重編碼（`%252e`）則利用「某一層多解碼一次」的錯誤。
>
> 正確的順序是先完整解碼一次，再對解碼後的結果檢查路徑段；更可靠的做法是在組出完整路徑後用 `realpath` 正規化（處理 `..` 與 symlink），確認結果仍以根目錄加 `/` 開頭。另外，`strstr(uri, "..")` 也會誤擋 `notes..txt` 這種合法檔名，檢查「路徑段等於 `..`」比較精確。最後一道防線是讓 server 以低權限執行，即使檢查有漏洞也讀不到敏感檔案。

> [!question]- Q5. 情境題：使用者回報相簿頁面很慢，nginx 的 access log 裡 504 與 499 同時增加。你會怎麼判斷？
> 504 表示 nginx 在 `proxy_read_timeout` 內沒有等到 `thumbd` 的回應，499 表示 client 在 nginx 回應之前就放棄了。兩者同時上升，最常見的解釋是同一個根因：後端變慢。有些使用者等不及先關掉頁面（499），撐到 nginx 逾時的則收到 504。
>
> 接著要往 `thumbd` 查：它的 thread pool 是否全部忙碌、accept queue（`ss -ltn` 的 `Recv-Q`）是否堆積、CPU 是否飽和、是否有某類請求（例如超大原圖）處理特別久、是否卡在磁碟 I/O 或 lock。也要看 nginx error log 的 upstream 訊息，排除連線本身的問題。短期可以對超大的請求設上限、回 503 讓 client 稍後重試；長期要找出變慢的原因，而不是單純把逾時調長。

> [!question]- Q6. 為什麼 keep-alive 要求每個回應都有 `Content-Length` 或 chunked 編碼？
> HTTP/1.0 傳統上用「server 關閉連線」來標記 body 結束，client 讀到 EOF 就知道回應完整了。keep-alive 的目的就是讓連線保持開啟，好送下一個請求，所以 EOF 不能再用來標記結束，client 必須有其他方法知道 body 在哪裡結束、下一個回應從哪裡開始。
>
> `Content-Length` 直接給出 body 的 byte 數；server 事先不知道長度時（例如邊產生邊送），就用 chunked 編碼，以長度 0 的 chunk 表示結束。如果兩者都沒有，client 只能等連線關閉，keep-alive 就失去意義。server 端也有對應的責任：讀完一個請求後，緩衝區裡可能已經有下一個請求的開頭，解析器必須保留這些 bytes，而不是丟掉它們。

> [!question]- Q7. 面試題：為什麼 nginx 能用幾個 process 處理上萬條連線，而 thread-per-connection 的 server 很難做到？
> thread-per-connection 的 server 為每條連線配置一個 thread，即使那條連線只是閒置等待資料，thread 的 stack、kernel 資料結構與排程成本都還在。上萬條連線就需要上萬個 thread，記憶體與 context switch 的成本都很高；遇到 slowloris 這類攻擊時，thread 很快就會用光。
>
> nginx 採用事件驅動模型：少數幾個 worker process（通常和 CPU 核心數相同），每個執行一個事件迴圈，把所有 socket 設為 nonblocking，交給 epoll（Linux）或 kqueue 監看。只有「現在可以讀或寫」的連線才會被處理，而且每次只處理一小步，之後立刻回到迴圈。每條連線的進度存在一個小的狀態結構裡，閒置連線只佔用一個 descriptor 和少量記憶體。代價是程式必須寫成狀態機，任何阻塞操作（同步的磁碟 I/O、DNS 查詢、CPU 密集的計算）都會卡住整個迴圈，這也是 `thumbd` 這種 CPU 密集服務適合放在 nginx 後面、用 thread pool 實作的原因。第 30 章會詳細比較這些模型。

> [!question]- Q8. 程式找錯：下面的 CGI 處理有什麼問題？`snprintf(cmd, sizeof cmd, "convert %s -resize %s out.jpg", filename, getenv("QUERY_STRING")); system(cmd);`
> 這段程式把使用者可以控制的 `QUERY_STRING`（以及可能來自請求的 `filename`）直接拼進 shell 指令字串，再交給 `system` 執行。`system` 會啟動 `/bin/sh` 解讀整串文字，所以攻擊者只要在 query 裡放 `;`、`|`、`$(...)` 這類 shell 語法，例如 `200x200;rm -rf /tmp/x`，就能在 server 上執行任意指令。這是典型的 command injection。
>
> 此外，`getenv` 可能回傳 NULL（沒有 query 時），傳給 `%s` 是 undefined behavior；固定的輸出檔名 `out.jpg` 在並行請求下會互相覆蓋。修法是：對參數做白名單驗證（例如只接受 `^[0-9]{1,4}x[0-9]{1,4}$`）；用 `fork` 加 `execv` 直接傳參數陣列，完全不經過 shell；檔名由 server 內部產生（例如用 `mkstemp` 建立唯一的暫存檔），不使用請求中的字串；並檢查 `getenv` 的回傳值。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 11 章 Tiny web server 的完整說明與程式碼。
- [CS:APP 3e Labs](https://csapp.cs.cmu.edu/3e/labs.html)：Proxy Lab 的官方說明與自動評分工具，適合讀完第 30–32 章後挑戰。
- [Linux man pages](https://man7.org/linux/man-pages/)：`sendfile(2)`、`realpath(3)`、`execve(2)`、`dup2(2)`、`socket(7)`，以及 `epoll(7)` 中事件驅動模型的說明。
- [POSIX 規格（The Open Group Base Specifications）](https://pubs.opengroup.org/onlinepubs/9799919799/)：`realpath`、`execve`、`setenv` 等函式的可移植語意。
