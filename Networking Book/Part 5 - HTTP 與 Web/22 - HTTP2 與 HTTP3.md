---
chapter: 22
title: HTTP/2 與 HTTP/3
part: 5
---

# 第 22 章　HTTP/2 與 HTTP/3

> [!abstract] 本章地圖
> **核心問題**：HTTP 的語意沒變，為什麼換一種「上線格式」就能讓頁面快好幾倍？什麼時候升級真的有效，什麼時候根本沒差？
>
> **你會學到**：
> - 說清楚 HTTP/1.1 的效能瓶頸（一條連線一次一個請求、六條連線上限、重複的 header），以及 domain sharding、sprite、inline 這些 workaround 在 HTTP/2 下為什麼反而有害
> - 逐欄讀懂 HTTP/2 的 9 bytes frame header，認得 DATA、HEADERS、SETTINGS、WINDOW_UPDATE、RST_STREAM、GOAWAY，並用 Python 編解碼、在 127.0.0.1 上跑一次自寫的 h2c 對話
> - 畫出 stream 的狀態機與 connection preface，解釋 multiplexing、flow control 與優先順序怎麼運作
> - 手算 HPACK 的整數編碼、查 static table 與 dynamic table，理解 Huffman 的角色與 header 壓縮的安全考量
> - 說明 server push 為什麼退場、103 Early Hints 怎麼接手，以及 HTTP/2 本身帶來的新攻擊面與防禦
> - 理解 HTTP/3 怎麼把 HTTP 對應到 QUIC stream、QPACK 為什麼和 HPACK 不同，並判斷連線合併、升級與否的取捨
>
> **前置知識**：第 12 章（擁塞控制與 head-of-line blocking）、第 13 章（QUIC 的 stream、varint 與 0-RTT）、第 18 章（TLS 與 ALPN）、第 20 章（HTTP/1.1 的訊息格式與 keep-alive）

## 22.1 故事：老師列表頁的八十張大頭照

聲聲 Live 的「找老師」頁面（`www.shengsheng.example/teachers`）一次列出八十位老師，每位老師一張大頭照、一段自我介紹，再加上頁面自己的 `app.css` 與 `app.js`。上個月，CDN 團隊把邊緣節點全面開啟 HTTP/2，產品經理在週會上期待「頁面至少快一倍」。結果美國學生（第 1 章那位 RTT 約 180 ms 的學生）的載入時間只從 3.4 秒降到 2.6 秒左右，和期待差了一大截。

小晴打開 DevTools 的 Network 面板，Protocol 欄確實寫著 `h2`，但瀑布圖（waterfall）看起來還是一段一段的。仔細看 Connection ID 欄，頁面一共開了三條連線：一條連 `www.shengsheng.example`，另外兩條連 `img1.shengsheng.example` 與 `img2.shengsheng.example`。這兩個圖片網域是五年前的前端工程師為了「讓瀏覽器多開幾條連線」刻意拆出來的，CNAME 到另一個 CDN 名稱 `ss.cdnedge.test`（198.51.100.7、.8），用的是另一張只涵蓋 `img1`、`img2` 的憑證。頁面上的小圖示還被拼成一張 1.2 MB 的 sprite 圖，只為了少發幾個請求。

```text
 學生瀏覽器（RTT 180 ms）
   │
   ├─ 連線 A ─ h2 ─► www.shengsheng.example   203.0.113.10   HTML、app.css、app.js
   ├─ 連線 B ─ h2 ─► img1.shengsheng.example  198.51.100.7   大頭照 1–40
   └─ 連線 C ─ h2 ─► img2.shengsheng.example  198.51.100.8   大頭照 41–80、icons-sprite.png（1.2 MB）
         │
         └─ B、C 各自要 DNS 查詢＋TCP 交握＋TLS 交握，約 3 個 RTT（540 ms）才拿到第一張圖
            三條連線各自做擁塞控制，彼此不知道對方，優先順序無法協調
```

這張圖是小晴畫給阿德看的現況。三條連線各自付出建立連線的成本；B 和 C 的 DNS 名稱、IP 與憑證都和 A 不同，瀏覽器沒辦法把它們合併成一條。HTTP/2 最核心的好處是「一條連線同時跑很多請求」，但這個頁面硬是把請求分散到三條連線；那張 1.2 MB 的 sprite 又讓每個小圖示都得等整張圖下載完才能顯示，還和大頭照搶同一條連線的頻寬。

阿德看完說：「HTTP/1.1 時代的偏方，在 HTTP/2 下大多變成毒藥。」Joe 則補了另一個觀察：在高鐵上用手機看課程回放時，換成 HTTP/2 之後偶爾整頁一起卡住，好像比以前多條連線時還糟。Rita 那週剛好也轉來一則 CDN 廠商的安全公告，提到 HTTP/2 的「Rapid Reset」攻擊，要大家確認 nginx 與 CDN 的版本。

這一章跟著小晴回答：HTTP/1.1 慢在哪裡、HTTP/2 在線路上長什麼樣子、為什麼它在掉封包時可能更糟、HTTP/3 怎麼解決，以及升級協定什麼時候有用、什麼時候沒差。

## 22.2 HTTP/1.1 的效能限制與那些偏方

第 20 章看過 HTTP/1.1 的訊息格式：一行請求行、一串文字 header、一個空行、可選的 body。這個格式簡單、好讀、好除錯，但它有一個根本限制：**在同一條連線上，回應必須依請求的順序一個接一個送回來**。回應沒有編號，client 只能靠「順序」把回應對回請求。

最直接的用法是一次只送一個請求，等回應收完再送下一個。這時每個請求至少要等 1 個 RTT。HTTP/1.1 其實定義了 **pipelining**（管線化：不等回應就連續送出多個請求），但 server 仍得依序回應，第一個請求如果很慢（例如要查資料庫），後面已經準備好的回應全部得排隊等它，這叫**應用層的 head-of-line blocking**（隊頭阻塞，第 12 章講過 TCP 層的版本）。再加上許多 proxy 處理 pipelining 有 bug，主流瀏覽器最後都沒有預設啟用它。

既然一條連線一次只能有一個請求在路上，瀏覽器就開多條連線。主流瀏覽器對同一個主機名稱通常最多同時開大約 **6 條** HTTP/1.1 連線（第 3 章在 DevTools 的 Stalled 階段看過這個上限的效果）。一個需要 82 個資源的頁面，等於要排成大約 14 輪，每輪至少 1 個 RTT。對 RTT 180 ms 的學生，光是排隊等 round trip 就要 2.5 秒。

```text
 HTTP/1.1：6 條連線，每條一次一個請求（時間往右）
 連線1 │交握│HTML│css │av06│av12│av18│av24│av30│av36│av42│av48│av54│...
 連線2 │    │    │交握│js       │av07│av13│av19│av25│av31│av37│av43│...
 連線3 │    │    │交握│av00│av08│av14│av20│av26│av32│av38│av44│av50│...
 連線4 │    │    │交握│av01│av09│av15│av21│av27│av33│av39│av45│av51│...
 連線5 │    │    │交握│av02│av10│av16│av22│av28│av34│av40│av46│av52│...
 連線6 │    │    │交握│av03│av11│av17│av23│av29│av35│av41│av47│av53│...
        每一格至少 1 個 RTT；格子之間的空白是「等回應」的時間，頻寬閒著

 HTTP/2：1 條連線，所有請求一次送出，回應切成 frame 交錯回來
 連線1 │交握│HTML│css js av00 av01 av02 … av79（回應交錯填滿頻寬）│
```

上半部是 HTTP/1.1 的瀑布圖示意：每條連線一格一格往右排，一格代表一個請求到回應的往返。瓶頸不是頻寬，而是「每一格都要等 1 個 RTT」；連線開了之後，大部分時間花在等待，鏈路其實是閒的。下半部是 HTTP/2：只有一次交握，HTML 回來之後，八十幾個請求在同一個 RTT 內全部送出，回應被切成小塊交錯傳回，鏈路一直是滿的。22.15 節會用模擬時鐘把這兩張圖算成具體的毫秒數。

第二個限制是 **header 重複**。每個請求都帶著幾乎相同的 `Host`、`User-Agent`、`Accept`、`Cookie`，每次 500 bytes 到 1 KB 是常態。八十個請求就是好幾十 KB 的重複文字，而 client 的上行頻寬通常比下行小；在 slow start 初期（第 12 章），這些 header 會吃掉寶貴的初始擁塞視窗。

為了繞過這些限制，前端社群發展出一整套偏方。它們在 HTTP/1.1 下確實有效，但每一個都有代價：

| 偏方 | 解決什麼 | 在 HTTP/1.1 的代價 | 在 HTTP/2／3 下 |
|---|---|---|---|
| domain sharding（拆成 img1、img2 多個網域） | 突破每個主機 6 條連線的上限 | 多一次 DNS、TCP、TLS；多條連線互搶頻寬 | 有害：破壞單連線多工與優先順序，除非能被連線合併 |
| sprite（多張小圖拼成一張） | 減少請求數 | 改一個圖示就讓整張圖的快取失效；必須整張下載完才能顯示 | 多半不需要；小檔案各自請求的成本已經很低 |
| 合併 JS／CSS（concatenation） | 減少請求數 | 改一行就讓整包快取失效 | 適度合併仍有價值（壓縮率、執行成本），但不必合成一大包 |
| inline（把小圖 base64 或 CSS 塞進 HTML） | 省掉一個請求 | 不能被獨立快取；base64 讓大小增加約三分之一 | 只保留首屏關鍵 CSS 這類小量內容 |
| 開更多 keep-alive 連線、cookie-free 網域 | 減少 header 與連線成本 | 網域越多、交握越多 | HPACK 已大幅壓縮重複 header，效益有限 |

讀這張表要抓住一個共同點：所有偏方都在「用別的成本換請求數」。請求數變少了，代價是快取粒度變粗、交握變多、優先順序失控。HTTP/2 從協定層解決了「請求很貴」這件事，偏方的好處消失，代價卻還在，這正是小晴的頁面升級後效果打折的原因。

> [!warning] 常見誤解
> 「HTTP/2 比 HTTP/1.1 快，是因為它是二進位格式。」二進位格式讓解析更快、更不容易出錯，但它不是效能提升的主因。真正的差別在於 multiplexing（不用排隊等 RTT）與 header 壓縮（不重送重複的 header）。在只抓一個大檔的情境下，HTTP/2 和 HTTP/1.1 幾乎一樣快。

## 22.3 HTTP/2 的全貌：同樣的語意，新的上線格式

HTTP/2 最早來自 Google 的 SPDY 實驗，2015 年標準化為 RFC 7540，2022 年改版為 **RFC 9113**。理解 HTTP/2 最重要的一句話是：**HTTP 的語意完全沒變**。method、status code、header 的意義、快取規則、cookie，全部依照 RFC 9110 與 RFC 9111，和 HTTP/1.1 一模一樣（第 20、21 章）。改變的只有「這些語意在線路上怎麼編碼」。所以 Flask 的 view 不必改一行程式，就能被 HTTP/2 的 client 呼叫。

HTTP/2 用四個層次的名詞來描述一條連線：

```text
 TCP 連線（加上 TLS）
 ┌──────────────────────────────────────────────────────────────┐
 │ connection：一條 HTTP/2 連線，有自己的 SETTINGS 與 HPACK 狀態   │
 │                                                              │
 │  stream 1（GET /teachers）  stream 3（GET /app.css）  stream 5 … │
 │  ┌───────────────────────┐  ┌───────────────────────┐        │
 │  │ message：請求          │  │ message：請求          │        │
 │  │  HEADERS frame         │  │  HEADERS frame         │        │
 │  │ message：回應          │  │ message：回應          │        │
 │  │  HEADERS frame         │  │  HEADERS frame         │        │
 │  │  DATA frame × N        │  │  DATA frame × N        │        │
 │  └───────────────────────┘  └───────────────────────┘        │
 │                                                              │
 │  線路上實際的順序：H1 H3 H5 D1 D3 D1 D5 D3 D1 …（frame 交錯）     │
 └──────────────────────────────────────────────────────────────┘
```

由外往內讀。**connection** 是一條 TCP（通常加 TLS）連線，雙方在上面交換設定、共用一份 header 壓縮狀態。**stream** 是 connection 裡一條雙向的邏輯通道，一次請求加回應就佔用一條 stream，每條 stream 有一個整數編號。**message** 是 HTTP 語意上的一個請求或一個回應。**frame** 是線路上最小的單位，每個 frame 都標明自己屬於哪一條 stream。最下面那一行是關鍵：不同 stream 的 frame 可以任意交錯，接收端依 stream 編號把它們分開重組。這就是 **multiplexing**（多工：在一條連線上同時進行很多請求）。

HTTP/1.1 的文字格式要在 HTTP/2 裡找到對應。請求行被拆成 **pseudo-header**（偽 header，名稱以冒號開頭的特殊欄位）：`:method`、`:scheme`、`:authority`、`:path`；回應的狀態行變成 `:status`。`:authority` 取代了 `Host` 的角色。另外幾條規則常讓人第一次碰到時踩雷：

- header 名稱一律小寫。HTTP/1.1 不分大小寫，HTTP/2 規定送出時必須是小寫，收到大寫要視為錯誤。
- 和「這條連線」綁定的 header 不能出現：`Connection`、`Keep-Alive`、`Proxy-Connection`、`Transfer-Encoding`、`Upgrade`。HTTP/2 自己有連線管理，也不需要 chunked（DATA frame 本身就有長度）。`TE` 只能是 `trailers`。
- `Cookie` 可以拆成多個欄位分開送，讓 HPACK 能分別快取不變的那幾段（22.7 節）。

反向代理（nginx、CDN）在 HTTP/2 與 HTTP/1.1 之間轉換時，做的就是這些雙向翻譯：請求行拆成 pseudo-header、`Host` 換成 `:authority`、名稱轉小寫、丟掉連線層級的 header。

**怎麼知道對方會說 HTTP/2？** 在 HTTPS 上，client 在 TLS ClientHello 的 **ALPN** 擴充（Application-Layer Protocol Negotiation，第 18 章）裡列出 `h2`、`http/1.1`，server 選一個回覆，交握完成時雙方就知道要說哪一種，不必多花一個 RTT。`h2` 這個 ALPN 名稱代表「跑在 TLS 上的 HTTP/2」；RFC 9113 也要求 HTTP/2 在 TLS 1.2 上使用時避開一批較弱的 cipher suite，TLS 1.3 則沒有這個問題。

不加密的 HTTP/2 叫 **h2c**（cleartext）。舊版規格允許 client 先送 HTTP/1.1 請求加上 `Upgrade: h2c` 來升級，RFC 9113 已經把這個升級機制標為 deprecated；現在 h2c 實務上只用「**prior knowledge**」：client 事先知道對方說 HTTP/2，一連上就直接送 HTTP/2 的開場白。主流瀏覽器只在 TLS 上支援 HTTP/2，所以 h2c 只會出現在資料中心內部，例如 load balancer 到後端、gRPC 服務之間（第 24 章），或像本章這樣在 127.0.0.1 上做實驗。

## 22.4 Frame：每一個 frame 都從 9 bytes 開始

HTTP/2 的每一個 frame 都有一個固定 9 bytes 的 header，後面接長度可變的 payload：

```text
 byte   0        1        2        3        4        5        6        7        8
     ┌────────┬────────┬────────┬────────┬────────┬─┬───────┬────────┬────────┬────────┐
     │      Length（24 bits）     │  Type  │ Flags  │R│   Stream Identifier（31 bits）     │
     └────────┴────────┴────────┴────────┴────────┴─┴───────┴────────┴────────┴────────┘
     ┌──────────────────────────────────────────────────────────────────────────────┐
     │                    Frame Payload（Length 個 bytes）                              │
     └──────────────────────────────────────────────────────────────────────────────┘
   R 是 byte 5 的最高位元；Stream Identifier 是 byte 5–8 剩下的 31 bits

 例：00 00 1b │ 01 │ 05 │ 00 00 00 01
      長度 27   HEADERS  END_STREAM|END_HEADERS   stream 1
```

逐欄解說。**Length** 是 payload 的長度，不含這 9 bytes，用 24 bits 表示，最大約 16 MB；但雙方預設只接受 16,384 bytes（2^14）以內的 frame，想收更大的要用 SETTINGS 宣告。**Type** 說明這是哪一種 frame。**Flags** 的意義依 type 而定，例如 HEADERS 的 `END_HEADERS`（0x4）表示 header 已經完整、`END_STREAM`（0x1）表示這個方向不會再有資料。**R** 是保留位元，必須為 0。**Stream Identifier** 是 31 bits 的 stream 編號；0 代表「整條連線」，SETTINGS、PING、GOAWAY 這類管理用的 frame 都用 stream 0。

最下面那一行是 22.15 節程式真的會產生的 header：長度 `0x00001b` 是 27 bytes，type `0x01` 是 HEADERS，flags `0x05` 是 `END_STREAM` 加 `END_HEADERS`，stream 1。和第 11 章的 framing 討論對照，HTTP/2 用的是「長度前綴」法：接收端先讀固定 9 bytes，就知道接下來要再讀多少，不需要像 HTTP/1.1 那樣在文字裡找 `\r\n\r\n`，也不必在 Content-Length 和 chunked 之間猜。這讓解析器簡單得多，也消除了第 20 章提到的那類「兩端對訊息邊界理解不同」的 request smuggling 問題（但只限 HTTP/2 端到端；proxy 把 HTTP/2 轉回 HTTP/1.1 時，問題又可能出現）。

RFC 9113 定義了十種 frame：

| Type | 名稱 | 用在 | 作用 |
|---|---|---|---|
| 0x0 | DATA | 某條 stream | 帶 body；受 flow control 管制；可設 END_STREAM |
| 0x1 | HEADERS | 某條 stream | 開啟 stream 並帶 HPACK 壓縮後的 header（也用於 trailer） |
| 0x2 | PRIORITY | 某條 stream | 舊版的優先順序樹，RFC 9113 已標為 deprecated |
| 0x3 | RST_STREAM | 某條 stream | 立刻終止一條 stream，帶錯誤碼（例如 CANCEL） |
| 0x4 | SETTINGS | stream 0 | 宣告本端的參數；對方要回一個帶 ACK flag 的空 SETTINGS |
| 0x5 | PUSH_PROMISE | 某條 stream | server push 預告（22.9 節，已退場） |
| 0x6 | PING | stream 0 | 8 bytes 的探測，量 RTT 或確認連線還活著，對方回 ACK |
| 0x7 | GOAWAY | stream 0 | 宣告不再接受新 stream，並告知最後處理到的 stream 編號 |
| 0x8 | WINDOW_UPDATE | 0 或某條 stream | 增加 flow control 視窗（22.8 節） |
| 0x9 | CONTINUATION | 某條 stream | header 太大、一個 HEADERS 裝不下時的續接 |

表中有幾個值得多看一眼。RST_STREAM 讓 client 可以取消單一請求而不必斷掉整條連線，例如使用者捲動頁面、某張大頭照已經不需要了；HTTP/1.1 想取消一個進行中的回應，只能關掉整條 TCP 連線。GOAWAY 是優雅關閉：server 要重啟或縮容時，先送 GOAWAY 告訴 client「編號大於 N 的 stream 我不會處理」，client 就知道哪些請求可以安全地在新連線上重送。PING 是第 11 章提到的「應用層心跳」，可以穿過 NAT 維持連線、也能量 RTT。未知的 frame type 必須被忽略，這讓日後的擴充（例如 RFC 8336 的 ORIGIN frame、RFC 9218 的 PRIORITY_UPDATE）不會讓舊實作出錯。

## 22.5 Stream：編號、狀態與多工

stream 編號有固定的規則：**client 開的 stream 用奇數**（1、3、5…），**server 開的用偶數**（只用在 push）。編號必須遞增，用過的不能再用；31 bits 的編號用完了，就只能開新連線。這個規則讓雙方不必協調就能各自開 stream，也讓 GOAWAY 只要一個「最後的編號」就能說清楚哪些請求被處理過。

每條 stream 都有自己的狀態機：

```text
                        ┌────────┐
                        │  idle  │
                        └───┬────┘
          送出／收到 HEADERS │
                        ┌───▼────┐
     收到 END_STREAM ┌───│  open  │───┐ 送出 END_STREAM
                     │   └───┬────┘   │
              ┌──────▼─────┐ │ ┌──────▼──────┐
              │half-closed │ │ │ half-closed │
              │  (remote)  │ │ │   (local)   │
              │ 只能送不能收 │ │ │ 只能收不能送 │
              └──────┬─────┘ │ └──────┬──────┘
     送出 END_STREAM │  任一方送 RST_STREAM │ 收到 END_STREAM
                     │   ┌───▼────┐   │
                     └──►│ closed │◄──┘
                         └────────┘
   （server push 另有 reserved (local)／reserved (remote) 兩個狀態，此處省略）
```

一個普通的 GET 是這樣走的，以 client 的角度看：client 送出帶 `END_STREAM` 的 HEADERS，stream 從 idle 直接進入 **half-closed (local)**，意思是「我這邊說完了，等你說」。server 回 HEADERS 和幾個 DATA，最後一個 DATA 帶 `END_STREAM`，stream 進入 **closed**。POST 上傳時，client 的 HEADERS 不帶 `END_STREAM`，stream 進入 open，接著送 DATA，最後一個 DATA 才帶 `END_STREAM`。任何時候任一方送出 RST_STREAM，stream 立刻 closed。這和第 10 章 TCP 的半關閉是同一個概念，只是縮小到單一請求的範圍。

**多少條 stream 可以同時 open？** 由對方的 `SETTINGS_MAX_CONCURRENT_STREAMS` 決定，規格建議不要小於 100。超過上限時 client 自己排隊；server 也可以用 RST_STREAM 帶 `REFUSED_STREAM` 拒絕，它保證「這個請求完全沒被處理」，即使不是 idempotent 的請求也能安全重送。

多工的意義，要放回 TCP 的脈絡才完整。HTTP/2 解決了 HTTP/1.1 的「應用層 HOL」：慢的回應不再擋住快的回應，因為它們在不同 stream 上，server 可以先送已經準備好的 frame。但所有 stream 仍然共用一條 TCP byte stream，只要一個 TCP segment 遺失，核心就會扣住之後所有已經到達的 bytes，等重傳補齊才交給應用程式（第 12 章）。HTTP/1.1 開 6 條連線時，一個封包遺失只會卡住其中一條；HTTP/2 只有一條連線，一個封包遺失卡住所有請求。這就是 Joe 在高鐵上看到「整頁一起卡住」的原因，也是 HTTP/3 存在的主要理由。

## 22.6 開始一條連線：preface、SETTINGS 與 ACK

TLS 交握並以 ALPN 選定 `h2` 之後，雙方各自送出 **connection preface**（連線開場白），確認對方真的說 HTTP/2：

```text
 Client                                                     Server
   │══ TCP 三向交握 + TLS 1.3 交握（ALPN 協商出 h2）════════════│
   │                                                          │
   │── "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"（24 bytes）──────────►│ ① client preface
   │── SETTINGS  stream=0  ENABLE_PUSH=0, INITIAL_WINDOW…  ───►│
   │── HEADERS   stream=1  GET /teachers  [END_STREAM]   ─────►│ ② 不必等，直接送請求
   │                                                          │
   │◄── SETTINGS stream=0  MAX_CONCURRENT_STREAMS=128 … ──────│ ③ server preface
   │◄── SETTINGS stream=0  [ACK]（確認收到 client 的設定）─────│
   │── SETTINGS  stream=0  [ACK]（確認收到 server 的設定）────►│
   │◄── HEADERS  stream=1  :status 200 ───────────────────────│
   │◄── DATA     stream=1  …  [END_STREAM] ───────────────────│
```

逐步解說。① client 先送一段 24 bytes 的固定字串 `PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n`，緊接一個 SETTINGS frame（可以是空的）。這段字串刻意長得像一個 HTTP/1.1 請求（method 是 PRI），如果對方其實是一台只懂 HTTP/1.1 的 server 或 proxy，它會把這當成一個看不懂的請求而回錯誤，不會把後面的二進位 frame 誤當成某種合法請求處理。② client 不必等 server 回覆，就可以接著送請求。③ server 的 preface 就是它的第一個 SETTINGS frame。

SETTINGS 的「ACK」規則很重要：每一方送出 SETTINGS 後，對方必須回一個帶 ACK flag、payload 為空的 SETTINGS，表示「我已經套用了」。在收到 ACK 之前，送出設定的一方不能假設對方已經照新設定運作。例如 client 把 `HEADER_TABLE_SIZE` 調小，要等 server ACK 後，才能確定 server 不會再參照被縮掉的表格內容。

SETTINGS 的 payload 是一串 6 bytes 的項目（16 bits 的 ID 加 32 bits 的值），常見的有：

| ID | 名稱 | 預設值 | 意義與實務 |
|---|---|---|---|
| 0x1 | HEADER_TABLE_SIZE | 4,096 | 對方可以用多大的 HPACK dynamic table 壓縮 header 給我 |
| 0x2 | ENABLE_PUSH | 1 | client 設 0 表示不要 server push；瀏覽器現在普遍設 0 |
| 0x3 | MAX_CONCURRENT_STREAMS | 無上限 | 對方最多同時開幾條 stream 給我；規格建議至少 100 |
| 0x4 | INITIAL_WINDOW_SIZE | 65,535 | 每條新 stream 的 flow control 初始視窗（不含連線層級） |
| 0x5 | MAX_FRAME_SIZE | 16,384 | 我願意收的最大 frame payload，可設到 2^24 − 1 |
| 0x6 | MAX_HEADER_LIST_SIZE | 無上限 | 我願意收的解壓後 header 總大小，防禦超大 header 的重要設定 |

這張表要注意方向：SETTINGS 描述的是「**送出者自己的接收能力**」，約束的是對方的行為。server 宣告 `MAX_CONCURRENT_STREAMS=128`，意思是「你最多同時開 128 條 stream 給我」。`MAX_HEADER_LIST_SIZE` 雖然預設無上限，實務上 server 都應該設，22.10 節會看到它和安全的關係。RFC 8441 另外定義了 `ENABLE_CONNECT_PROTOCOL`（0x8），讓 WebSocket 可以跑在 HTTP/2 的 stream 上（第 32 章）。

## 22.7 HPACK：把重複的 header 壓到一兩個 byte

HTTP/2 用 **HPACK**（RFC 7541）壓縮 header。為什麼不直接用 gzip？SPDY 早期確實用 DEFLATE 壓縮 header，結果在 2012 年被 **CRIME** 攻擊打穿：如果攻擊者能讓受害者的瀏覽器送出夾帶自己猜測字串的請求（例如在網址裡放 `cookie=a`、`cookie=b`），又能觀察加密後封包的長度，猜對的那一次會因為和真正的 cookie 重複而壓得比較短，一個字元一個字元就能猜出 session cookie。只要「攻擊者控制的資料」和「秘密」被同一個自適應壓縮器處理，長度就會洩漏秘密。

HPACK 的設計刻意放棄通用壓縮，只做三件事：**查表**（整個 header 欄位在表裡就只送一個編號）、**整數編碼**（編號與長度用很省的變長整數）、**靜態 Huffman 編碼**（字串用一張固定的碼表縮短）。它只能以「整個名稱」或「整個名稱加值」為單位比對，猜中一部分不會讓長度變短，CRIME 那種逐字元猜測就失效了。

### 兩張表與同一個編號空間

HPACK 有兩張表，共用一個從 1 開始的編號空間：

```text
  編號    內容                                   來源
 ┌────┬──────────────────────────────────┐
 │  1 │ :authority                        │
 │  2 │ :method          GET              │
 │  3 │ :method          POST             │   static table
 │  4 │ :path            /                │   61 筆，寫死在 RFC 裡，
 │  … │ …                                 │   兩端都有、永遠不變
 │  8 │ :status          200              │
 │  … │ …                                 │
 │ 61 │ www-authenticate                  │
 ├────┼──────────────────────────────────┤
 │ 62 │ cookie           sid=3f9c…（最新） │   dynamic table
 │ 63 │ accept           image/webp,*/*   │   連線期間累積，新的插在最前面，
 │ 64 │ user-agent       Mozilla/5.0 …    │   超過 HEADER_TABLE_SIZE（預設 4,096 bytes）
 │ 65 │ :authority       www.shengsheng…  │   就從最舊的開始淘汰
 └────┴──────────────────────────────────┘
   每筆的「大小」= 名稱長度 + 值長度 + 32（管理成本）
```

由上往下讀。**static table** 有 61 筆，收錄最常見的 header 名稱與少數常見的「名稱加值」組合，例如 2 號是 `:method: GET`、8 號是 `:status: 200`、4 號是 `:path: /`；只有名稱的項目（例如 1 號 `:authority`、32 號 `cookie`）可以拿來當「名稱的縮寫」。**dynamic table** 是這條連線自己累積的表，編號從 62 開始，**最新加入的永遠是 62 號**，舊的往後推。注意每個方向各有一份：client 送請求用一份、server 送回應用另一份，每一份都由送出端的 encoder 與接收端的 decoder 各自維護一模一樣的副本。

dynamic table 的大小以 bytes 計，每筆是名稱長度加值長度再加 32。加 32 是為了把實作裡的指標與管理成本算進去，讓「4,096 bytes」大致等於實際的記憶體用量。表滿了就從最舊的開始淘汰。這張表就是 HPACK 的「狀態」：兩端必須以完全相同的順序處理每一個 header block，表才會保持一致。這也是後面 HTTP/3 不能直接沿用 HPACK 的原因。

### 四種表示法

header block 裡的每一個欄位，用第一個 byte 的最高幾位區分表示法：

| 第一個 byte | 表示法 | 後面接什麼 | 會加進 dynamic table？ |
|---|---|---|---|
| `1xxxxxxx` | Indexed（整筆查表） | 7-bit prefix 的編號 | 否 |
| `01xxxxxx` | Literal with incremental indexing | 6-bit 名稱編號（0 表示名稱用字串）＋值字串 | 是 |
| `0000xxxx` | Literal without indexing | 4-bit 名稱編號＋值字串 | 否（這次不加，proxy 轉送時可以加） |
| `0001xxxx` | Literal never indexed | 4-bit 名稱編號＋值字串 | 否，而且任何中介都**不得**加 |
| `001xxxxx` | Dynamic table size update | 5-bit 的新大小 | 調整表格大小 |

這張表的判斷邏輯是：會重複出現的欄位（`user-agent`、`accept`、`:authority`）第一次用 incremental indexing 送，之後只要 1 byte；每次都不同的欄位（`:path` 帶不同的 ID、`content-length`）用 without indexing，免得把表塞滿沒用的東西；敏感而且值很短、容易被猜中的欄位（短的 token、密碼）用 **never indexed**，避免它進入可被探測的壓縮狀態，proxy 轉送時也必須保持 never indexed。

### 整數編碼：N-bit prefix

編號與字串長度都用 **N-bit prefix 整數**：第一個 byte 剩下的 N 個 bit 放得下就直接放；放不下就把 N 個 bit 全部填 1，剩下的值每 7 bits 一組、由低到高放在後續 byte，最高位是 1 表示「後面還有」。手算 RFC 7541 附錄的例子，在 5-bit prefix 下編碼 1337：

```text
 5-bit prefix 的上限是 2^5 − 1 = 31，1337 ≥ 31，放不下
 第 1 個 byte：前綴填滿           ???11111                      → 0x1f（??? 是表示法的旗標位元）
 剩下 1337 − 31 = 1306 = 0b 1010 0011010
   低 7 bits  0011010 = 26，後面還有 → 1 0011010 = 0x9a
   再 7 bits  0001010 = 10，結束     → 0 0001010 = 0x0a
 結果：1f 9a 0a   （解碼：31 + 26 + 10×128 = 1337）
```

這個編碼和第 13 章 QUIC 的 varint 不同：QUIC 用前兩位表示總長度，HPACK 則讓整數「寄生」在第一個 byte 剩下的位元裡，小數字（例如 static table 的編號）連一個額外 byte 都不用。0x82 就是 `1` 加上 7-bit 的 2，也就是「整筆查表，第 2 號」，代表 `:method: GET`；0x88 是 `:status: 200`。一個最常見的 GET 請求，`:method`、`:scheme`、`:path` 三個欄位加起來只要 3 bytes。

字串的格式是「1 bit 的 H 旗標＋7-bit prefix 的長度＋內容」。H 為 1 表示內容經過 Huffman 編碼。

### Huffman：只講概念

HPACK 的 Huffman 碼表是一張**固定的**碼表，依大量真實 HTTP header 的字元出現頻率統計而成，寫死在 RFC 7541 附錄。常見字元碼短：小寫字母、數字、`-`、`.`、`/` 大多是 5 到 6 bits；罕見的控制字元可以長到 30 bits。編碼後如果最後不滿一個 byte，用 1 補滿（最多 7 bits，對應碼表裡 EOS 符號的前綴）。以 RFC 附錄的例子，`www.example.com` 從 15 bytes 縮成 12 bytes，大約省兩成。

固定碼表有兩個好處。第一，不必在連線上傳碼表，也不會因為內容而「學習」，不會有 CRIME 式的長度洩漏。第二，實作可以預先建好查表結構，解碼很快。encoder 可以逐欄決定要不要用 Huffman：如果 Huffman 後反而變長（例如隨機的 base64 token），就送原文。本章的程式為了聚焦在查表與整數編碼，不實作 Huffman；讀真實封包時看到長度 byte 的最高位是 1，就知道那是 Huffman 字串。

## 22.8 Flow control 與優先順序

### 為什麼 TCP 已經有流量控制，HTTP/2 還要一層

第 11 章的 TCP 流量控制保護的是「接收端的 socket buffer」。但 HTTP/2 把很多 stream 塞進一條 TCP 連線，接收端的應用程式可能對不同 stream 有不同的處理速度：一個 proxy 從 client 收上傳資料，如果後端很慢，它不想讓某一條 stream 把記憶體塞滿，同時又不想停止讀取整條 TCP 連線，否則其他 stream 也會被拖住。所以 HTTP/2 在 stream 層級與連線層級各有一個視窗，**只有 DATA frame 受管制**，HEADERS、SETTINGS 這些控制 frame 不受影響，避免控制訊息被卡死。

```text
 接收端宣告：stream 1 的視窗 65,535，連線的視窗 65,535
 送出端：
   DATA stream=1 16,384 bytes  →  stream 1 剩 49,151   連線剩 49,151
   DATA stream=3 16,384 bytes  →  stream 3 剩 49,151   連線剩 32,767
   DATA stream=1 16,384 bytes  →  stream 1 剩 32,767   連線剩 16,383
   DATA stream=1 16,383 bytes  →  stream 1 剩 16,384   連線剩      0  ← 全部停住
 接收端處理完資料後：
   WINDOW_UPDATE stream=0 +65,535   （連線層級加回）
   WINDOW_UPDATE stream=1 +32,768   （stream 1 加回）
 送出端：連線剩 65,535，stream 1 剩 49,152 → 可以繼續送
```

這段追蹤顯示兩個視窗同時生效：每送一個 DATA，就同時扣 stream 視窗與連線視窗，任一個歸零就必須停。第四步之後連線視窗變成 0，即使 stream 1 和 stream 3 自己的視窗都還有餘額，也不能再送任何 DATA。接收端用 **WINDOW_UPDATE** 加回額度，stream 0 代表連線層級。初始值都是 65,535 bytes；stream 的初始視窗可以用 `SETTINGS_INITIAL_WINDOW_SIZE` 改，**連線層級的視窗只能用 WINDOW_UPDATE 加大**，這是實作者常漏掉的細節。

這套機制是 **credit-based**（額度制）：接收端給多少額度，送出端就送多少，沒有任何協商。它的危險在於預設值很小。手算一下：視窗 65,535 bytes、RTT 180 ms 時，送出端每個 RTT 最多送 65,535 bytes，等 WINDOW_UPDATE 回來才能再送，上限約 65,535 ÷ 0.18 ≈ 364 KB/s，大約 2.9 Mbps。第 12 章的 bandwidth-delay product 告訴我們，20 Mbps、180 ms 的路徑需要約 450 KB 的資料在路上才能填滿。瀏覽器通常會宣告大得多的視窗，但如果是 server 或 proxy 這端在「接收」，例如老師上傳整堂課的錄影，就要確認 server 的 HTTP/2 接收視窗夠大，否則上傳速度會被卡在幾 Mbps，而且 RTT 越大越慢。

### 優先順序：從依賴樹到 Extensible Priorities

多工之後出現新問題：八十二個請求同時送出，server 先送哪個？HTML 解析需要 CSS 才能繪製首屏，JS 可能阻塞渲染，大頭照晚一點沒關係。RFC 7540 設計了一棵**優先順序依賴樹**：每條 stream 可以宣告依賴另一條 stream，並帶一個 1 到 256 的權重。這套設計很有表達力，但實作複雜、各瀏覽器建樹的方式差異很大，很多 server 乾脆沒有正確實作，RFC 9113 把它標為 deprecated。

取而代之的是 **RFC 9218 Extensible Priorities**，HTTP/2 與 HTTP/3 共用。它只有兩個參數：urgency `u`（0 到 7，數字越小越急，預設 3）與 incremental `i`（這個資源能不能邊收邊用，例如漸進式圖片）。client 用一個普通的 header 表達，也可以在請求送出後用 PRIORITY_UPDATE frame 更改：

```text
 priority: u=0          ← 首屏 CSS：最急，而且要整份到齊才有用
 priority: u=1          ← HTML 裡同步載入的 JS
 priority: u=5, i       ← 頁面下方的大頭照：不急，收到一部分就能先畫
```

server 的排程規則很直覺：先送 urgency 最小的；同一個 urgency 裡，非 incremental 的一個一個送完，incremental 的輪流交錯送。因為它是 header，CDN 與 origin 之間也看得懂，前端也能用 HTML 的 `fetchpriority` 屬性影響瀏覽器給的優先順序。小晴的頁面拆成三條連線的另一個代價就在這裡：優先順序只在同一條連線內有意義，A 連線上 `u=0` 的 CSS，沒辦法讓 C 連線上那張 1.2 MB 的 sprite 讓路。

## 22.9 Server push 的退場與 103 Early Hints

**Server push** 是 HTTP/2 最受期待的功能：server 在回 HTML 的同時，主動用 PUSH_PROMISE 預告「我也會把 `/app.css` 給你」，接著在一條偶數編號的 stream 上把 CSS 送過去，省下瀏覽器解析 HTML 後才發請求的那 1 個 RTT。

實務上卻問題連連：server 不知道瀏覽器的快取裡已經有什麼，常把早就快取好的 CSS 又推一次；推送的資料和真正需要的回應搶頻寬，推太多反而拖慢首屏；CDN、瀏覽器、server 的 push 語意也很難對齊。大型網站的量測顯示正面效果很小，甚至常是負面的。Chrome 在 2022 年起預設停用 HTTP/2 push，HTTP/3 規格雖然保留了 push，瀏覽器幾乎都沒有實作；本書建議把 push 視為已退場的功能，新設計不要依賴它。

接手的是兩個更簡單的機制。一個是 HTML 裡的 `<link rel="preload">` 與 `<link rel="preconnect">`，讓瀏覽器自己決定要不要抓、什麼時候抓，它知道自己的快取。另一個是 **103 Early Hints**（RFC 8297）：

```text
 Browser                         CDN／nginx                       Flask（要 300 ms 產生頁面）
   │── GET /teachers ──────────────►│── GET /teachers ─────────────────►│
   │◄─ 103 Early Hints ─────────────│  （CDN 依設定或 origin 先回的 103）  │
   │   link: </app.css>; rel=preload; as=style                         │
   │   link: <https://img…>; rel=preconnect                            │
   │── GET /app.css ───────────────►│   （瀏覽器先抓 CSS，和 origin 平行）  │
   │◄─ 200 app.css ─────────────────│                                   │
   │                                │◄──────────────── 200 HTML（300 ms 後）│
   │◄─ 200 HTML ────────────────────│                                   │
```

Early Hints 是一個 1xx 的「中途回應」：server 在還沒算完最終回應之前，先回一個 103，帶上 `link` header，告訴瀏覽器「你等一下大概會需要這些」。瀏覽器利用 server 思考的這 300 ms 先去抓 CSS 或預先建好連線。和 push 不同，決定權在瀏覽器：已經快取的就不抓，頻寬由瀏覽器排程。它在 HTTP/1.1 也能用（只是 1xx 回應在某些舊 proxy 上不穩定），HTTP/2 與 HTTP/3 上最常見。實作支援依瀏覽器、CDN 與 server 而定，部署前要實測。

## 22.10 HTTP/2 的代價：單一 TCP 連線與新的攻擊面

HTTP/2 不是免費的。第一個代價就是 22.5 節說的 **TCP 層 HOL**：所有請求押在一條 TCP 連線上，丟一個封包就全部等。在乾淨的網路上，單一連線的多工完勝；在掉包率高的行動網路上，HTTP/1.1 的 6 條連線反而分散了風險。第 13 章的模擬已經量過這個差距：一個封包遺失時，TCP 讓同一條連線上的其他資料多等了超過 100 ms。

第二個代價是**擁塞視窗**。6 條 TCP 連線各自從 slow start 開始，加起來的初始視窗是一條連線的 6 倍，遇到遺失時也只有一條連線砍半。HTTP/2 的一條連線起步較慢、遺失時整條減速。這不代表 HTTP/2 比較慢，而是說「HTTP/2 永遠比 HTTP/1.1 快」並不成立：在高 RTT、資源多而小的頁面上，HTTP/2 大勝；在高遺失率、少量大檔的情境下，差距可能消失甚至反轉。

第三個代價是**實作複雜度與攻擊面**。HTTP/1.1 的 server 處理一個請求要讀一段文字；HTTP/2 的 server 要維護 stream 狀態、HPACK 表、兩層視窗與優先順序，每一項都是可以被濫用的狀態。幾個值得認識的案例，以及防禦方式：

| 名稱 | 濫用的機制 | 影響 | 防禦 |
|---|---|---|---|
| Rapid Reset（2023，CVE-2023-44487） | 開 stream 後立刻 RST_STREAM，被取消的 stream 不算在並行上限內 | server 不斷開始處理又丟棄請求，CPU 被耗盡 | 更新 server／CDN；限制每條連線的 reset 速率，超過就送 GOAWAY 關閉連線 |
| CONTINUATION flood（2024） | 不斷送不帶 END_HEADERS 的 CONTINUATION | server 一直累積 header 等它結束，記憶體或 CPU 耗盡 | 更新實作；設 MAX_HEADER_LIST_SIZE，限制總 header 大小與 frame 數 |
| HPACK bomb | 小小的 header block 反覆參照 dynamic table 裡的大欄位 | 解壓後的 header 遠大於線路上的大小 | 限制解壓後的 header 總量（MAX_HEADER_LIST_SIZE） |
| PING／SETTINGS flood（2019 一系列公告） | 大量需要回應的控制 frame | 回應排隊佔用記憶體 | 限制控制 frame 速率；對方不讀回應就關連線 |

這張表的共同模式是：**HTTP/2 讓一條連線能做的事變多了，限制必須跟著設到每條連線上**。只限制「每秒請求數」不夠，因為 Rapid Reset 的請求都被取消、從未完成；只限制「連線數」也不夠，因為一條連線就能發動。Rita 的檢查清單因此是：CDN 與 nginx 版本是否包含這些修補、`MAX_CONCURRENT_STREAMS` 與 header 大小是否有上限、異常連線是否會被 GOAWAY 關掉，以及監控是否看得到「每條連線的 reset 數」。

最後要記得，「網站開了 HTTP/2」通常只代表瀏覽器到 edge 這一段。CDN 和 nginx 對 origin 往往說 HTTP/1.1（nginx 的 `proxy_pass` 傳統上只用 HTTP/1.x 連 upstream，gRPC 才用 `grpc_pass` 走 HTTP/2，細節依版本而定），而這在資料中心內部通常沒問題，因為內部 RTT 不到一毫秒，排隊成本可以忽略。

## 22.11 HTTP/3：把 HTTP 搬到 QUIC 上

第 13 章已經把 QUIC 講完：它在 UDP 上提供多條獨立的 stream、內建 TLS 1.3、1-RTT 交握與 0-RTT、connection migration，而且一個封包遺失只影響所屬的 stream。**HTTP/3**（RFC 9114）要做的事因此很單純：把 HTTP 的語意對應到 QUIC 的 stream 上，並把 HTTP/2 裡和 QUIC 重複的部分拿掉。

```text
 一條 QUIC 連線（UDP 443，ALPN = h3）
 ┌───────────────────────────────────────────────────────────────────┐
 │ 雙向 stream 0  ── GET /teachers ──   HEADERS │ DATA │ DATA │ FIN   │ 一個請求
 │ 雙向 stream 4  ── GET /app.css  ──   HEADERS │ DATA │ FIN          │ 一條 stream
 │ 雙向 stream 8  ── GET /avatars/1 ─   HEADERS │ DATA │ FIN          │
 │                                                                   │
 │ 單向 stream 2  client control（type 0x00）  SETTINGS …              │ 每端各一條，
 │ 單向 stream 3  server control（type 0x00）  SETTINGS、GOAWAY …      │ 不能關閉
 │ 單向 stream 6  client QPACK encoder（0x02）  表格插入指令            │
 │ 單向 stream 7  server QPACK encoder（0x02）                         │
 │ 單向 stream 10 client QPACK decoder（0x03）  確認收到                │
 │ 單向 stream 11 server QPACK decoder（0x03）                         │
 └───────────────────────────────────────────────────────────────────┘
   stream ID 的最低兩位：bit0 = 誰開的（0 client、1 server），bit1 = 單向或雙向
```

逐行解說。每個請求佔一條 **client 開的雙向 stream**，編號 0、4、8…（第 13 章講過 QUIC stream ID 的最低兩位編碼了發起者與方向）。stream 上依序是 HEADERS frame、零到多個 DATA frame，然後 QUIC 的 FIN 表示結束，HTTP/3 不需要 `END_STREAM` flag。除此之外，雙方各開一條**單向的 control stream**，第一個 byte 是 stream type 0x00，上面先送 SETTINGS，之後是 GOAWAY 這類連線層級的控制訊息；另外各有一條 QPACK encoder stream 與 decoder stream（下一節）。單向 stream 的實際編號依開啟順序而定，圖中只是一種可能的分配。

和 HTTP/2 相比，HTTP/3 的 frame 少了很多東西：

| 功能 | HTTP/2 | HTTP/3 |
|---|---|---|
| 傳輸 | 一條 TCP（加 TLS）連線 | 一條 QUIC 連線（UDP，TLS 1.3 內建） |
| frame header | 固定 9 bytes，含 stream ID | Type 與 Length 兩個 varint，不含 stream ID |
| stream 與多工 | HTTP/2 自己做 | 交給 QUIC 的 stream |
| flow control | WINDOW_UPDATE | 交給 QUIC 的 MAX_DATA／MAX_STREAM_DATA |
| 取消請求 | RST_STREAM | QUIC 的 RESET_STREAM 與 STOP_SENDING |
| 存活探測 | PING frame | QUIC 的 PING frame |
| header 壓縮 | HPACK | QPACK |
| 優先順序 | RFC 9218（舊的依賴樹已 deprecated） | RFC 9218 |
| header 續接 | CONTINUATION | 不需要（frame 長度是 varint，不受 16 KB 限制） |
| 遺失的影響 | 整條連線的所有 stream 等待 | 只有所屬 stream 等待 |
| 新連線到送出請求 | 2 RTT（TCP＋TLS 1.3） | 1 RTT；resumption 可 0-RTT |

這張表說明了 HTTP/3 的分工哲學：凡是傳輸層該做的，全部交給 QUIC，HTTP/3 只剩 HTTP 自己的事。HTTP/3 的 frame 格式也因此變得很簡單，type 和 length 都是第 13 章的 varint：

```python
# HTTP/3 frame = Type(varint) + Length(varint) + Payload；varint 規則同第 13 章
def varint(v: int) -> bytes:
    for limit, prefix, n in ((63, 0, 1), (16383, 1, 2), (2**30 - 1, 2, 4), (2**62 - 1, 3, 8)):
        if v <= limit:
            raw = v.to_bytes(n, "big")
            return bytes([raw[0] | prefix << 6]) + raw[1:]
    raise ValueError(v)


def h3_frame(ftype: int, payload: bytes) -> bytes:
    return varint(ftype) + varint(len(payload)) + payload


for size in (10, 1_000, 100_000):
    h3 = len(h3_frame(0x0, b"x" * size)) - size      # DATA frame 的 type 也是 0x0
    print(f"DATA payload {size:>7} bytes：HTTP/3 frame header {h3} bytes，HTTP/2 固定 9 bytes")
# 沒有 stream ID：HTTP/3 的 frame 屬於哪個請求，由它所在的 QUIC stream 決定
assert h3_frame(0x1, b"\x00\x00\xd1") == bytes.fromhex("0103 0000d1")
```

```text
DATA payload      10 bytes：HTTP/3 frame header 2 bytes，HTTP/2 固定 9 bytes
DATA payload    1000 bytes：HTTP/3 frame header 3 bytes，HTTP/2 固定 9 bytes
DATA payload  100000 bytes：HTTP/3 frame header 5 bytes，HTTP/2 固定 9 bytes
```

輸出顯示 HTTP/3 的 frame header 只有 2 到 5 bytes，比 HTTP/2 的 9 bytes 小，原因是它不必帶 stream ID，長度也用變長整數。最後一行 assert 組了一個最小的 HEADERS frame：type `01`、長度 `03`，payload 是 QPACK 編碼的 `00 00 d1`，前兩個 byte 是下一節會講的 field section prefix（表示不參照 dynamic table），`d1` 代表「static table 第 17 號」，在 QPACK 的表裡就是 `:method: GET`。HTTP/3 的 frame type 編號刻意和 HTTP/2 的對齊（DATA 0x0、HEADERS 0x1、SETTINGS 0x4、GOAWAY 0x7），但兩者的格式並不相容，不能混用。

**怎麼找到 HTTP/3？** QUIC 是另一條 UDP 連線，不能在 TCP 的 ALPN 裡協商。第 13 章 13.10 節講過兩條路：回應裡的 `Alt-Svc: h3=":443"; ma=86400`，或 DNS 的 HTTPS record（第 14 章）宣告 `alpn="h3,h2"`；QUIC 交握裡的 ALPN 是 `h3`。UDP 被擋時瀏覽器退回 HTTP/2，所以上線 HTTP/3 一定要保留 HTTP/2。

**0-RTT 與 HTTP 語意**。HTTP/3 讓 resumption 的請求可以放進 0-RTT，但 0-RTT 資料可能被重放（第 13、18 章）。聲聲 Live 的規則和全書一致：只讓 GET 與 HEAD 走 0-RTT，其他請求若出現在 early data 中，CDN 或後端回 **425 Too Early**，瀏覽器會在交握完成後自動重送。CDN 轉給 origin 時，可以加上 `Early-Data: 1` header（RFC 8470）讓後端知道這個請求來自 early data，後端據此決定要不要回 425。

## 22.12 QPACK：在亂序的世界裡壓縮 header

HTTP/3 為什麼不能直接用 HPACK？HPACK 的 dynamic table 是靠「header block 依序處理」來同步的：stream 1 的 HEADERS 插入一筆、stream 3 的 HEADERS 參照它，接收端一定先處理完 stream 1，才會處理 stream 3。在 HTTP/2 裡這成立，因為所有 frame 都在同一條 TCP byte stream 上依序到達。QUIC 的 stream 之間沒有順序保證：stream 4 的 HEADERS 可能比 stream 0 的先到。如果 stream 4 參照了 stream 0 才插入的表項，接收端根本查不到。如果硬要等，又把 QUIC 消除的 HOL 請回來了。

**QPACK**（RFC 9204）的解法是把「修改表格」和「使用表格」分開：

```text
 Encoder（例如 client）                                    Decoder（server）
   │                                                          │
   │══ encoder stream：Insert「:authority www.shengsheng…」═══►│ 表格插入只走這條
   │══ encoder stream：Insert「user-agent Mozilla/5.0…」══════►│ 單向 stream，依序處理
   │                                                          │
   │── stream 0 HEADERS：prefix(Required Insert Count=2) ─────►│ 「解這個 block 需要
   │      欄位：參照 dynamic 第 0、1 筆                         │   表裡至少有 2 筆」
   │                                                          │
   │   情況 A：插入指令先到 → 立刻解碼                           │
   │   情況 B：插入指令的封包遺失 → stream 0 暫時 blocked，       │
   │          其他沒參照新表項的 stream 照常解碼                    │
   │                                                          │
   │◄══ decoder stream：Section Acknowledgment（stream 0）═════│ 確認「我解完了」，
   │◄══ decoder stream：Insert Count Increment ════════════════│ encoder 從此可放心參照
```

逐步解說。所有修改 dynamic table 的指令都放在單向的 **encoder stream** 上，單一 stream 內是保序的，所以接收端看到的插入順序一定正確。每個 header block 開頭有一個 **field section prefix**，其中的 **Required Insert Count** 說明「解碼這個 block 至少需要表格已經插入過幾筆」。接收端如果還沒收到那麼多插入指令，就讓這條 stream 暫時 **blocked**，等 encoder stream 補上；其他 stream 不受影響。解碼完成後，decoder 透過 **decoder stream** 回送確認，encoder 才知道哪些表項對方確定有了。

這留給 encoder 一個取捨：參照剛插入的表項壓縮率高，但偶爾 blocked；只參照對方已確認的表項則零阻塞。接收端用 `SETTINGS_QPACK_BLOCKED_STREAMS` 宣告最多允許幾條 stream 同時 blocked，用 `SETTINGS_QPACK_MAX_TABLE_CAPACITY` 宣告 dynamic table 的上限；這兩個值的預設都是 0，意思是「預設不使用 dynamic table、也不允許阻塞」，雙方要明確宣告才會啟用。QPACK 的 static table 也重新設計過：共 99 筆、編號從 0 開始，收錄更多常見的「名稱加值」（例如多個 `:status` 與 `content-type` 值），讓不用 dynamic table 時也有不錯的壓縮率。

## 22.13 連線合併：兩個網域共用一條連線

HTTP/2 和 HTTP/3 只要一條連線就能多工，那麼 `www.shengsheng.example` 和 `img1.shengsheng.example` 能不能共用同一條？可以，這叫 **connection coalescing**（連線合併）。規格允許 client 把另一個 origin 的請求送到已經建好的連線上，只要那條連線的 server 對這個 origin 是「有權威的」（authoritative）。瀏覽器實際上會檢查這些條件：

```text
 已有連線：www.shengsheng.example → 203.0.113.10，h2，憑證 SAN = www、img1、img2
 頁面要抓：https://img1.shengsheng.example/avatars/7.webp
        │
        ├─ ① scheme 都是 https？                         否 → 開新連線
        ├─ ② 這條連線的憑證涵蓋 img1.shengsheng.example？  否 → 開新連線
        ├─ ③ img1 的 DNS 結果包含 203.0.113.10？          否 → 開新連線（多數瀏覽器要求；細節依瀏覽器而定）
        │       （server 若送過 ORIGIN frame 宣告 img1，支援的瀏覽器可略過這步）
        ▼
     沿用同一條連線送 GET /avatars/7.webp（:authority = img1.shengsheng.example）
        │
        └─ server 發現自己其實不服務 img1 → 回 421 Misdirected Request → 瀏覽器開新連線重試
```

依序看。① 只合併 https 的 origin。② 連線的憑證必須對新的主機名稱有效，這是安全底線：沒有這張憑證，就不能證明這台 server 有權代表 img1。③ 多數瀏覽器還要求新名稱的 DNS 解析結果包含這條連線的 IP，作為「這台機器真的服務那個名稱」的額外佐證；RFC 8336 的 **ORIGIN frame** 讓 server 直接宣告「這條連線服務哪些 origin」，支援的 client 可以少做這個檢查。最後一層保險是 **421 Misdirected Request**（RFC 9110）：如果 server 收到一個它不能在這條連線上處理的 `:authority`，例如 CDN 以 SNI 決定後端、不同網域其實在不同叢集，就回 421，瀏覽器會開新連線重送。

回到故事。小晴的 img1、img2 用另一個 CDN 名稱、另一組 IP、另一張憑證，三個條件都不成立，瀏覽器只能開三條連線。阿德給的修法有兩種：一是讓 `img1`、`img2` 指到和 `www` 相同的 CDN edge、換一張同時涵蓋三個名稱的憑證，讓瀏覽器合併；二是直接把大頭照搬回 `www.shengsheng.example/avatars/`，舊網域用 301 導回，並在 CDN 上設長快取。團隊選了第二種，因為合併依賴瀏覽器的實作細節，而同源的方案在任何瀏覽器都成立，也順便讓 CORS 與 cookie 的設定（第 23 章）變簡單。

## 22.14 何時升級有效、何時沒差

把前面的機制收斂成判斷：HTTP/2 省的是「排隊等 RTT」與「重複 header」，HTTP/3 再省掉「TCP 交握的 1 RTT」與「封包遺失造成的跨請求等待」，外加換網路不斷線。所以升級效益大的情境，是 RTT 大、請求多而小、網路會掉包或換網路的情境；效益小的情境，是 RTT 很小、請求很少、或瓶頸根本不在網路的情境。

| 情境 | HTTP/2 的效果 | HTTP/3 的額外效果 | 判斷依據 |
|---|---|---|---|
| 高 RTT、頁面有幾十到上百個小資源 | 很大：從十幾輪 round trip 變成一兩輪 | 中等：新連線少 1 RTT | 瓶頸是 RTT × 輪數 |
| 行動網路、會掉包、會切換 Wi-Fi／4G | 可能變差：一條 TCP 連線的 HOL | 很大：stream 獨立、connection migration | 遺失與遷移是主因 |
| 下載單一大檔（課程錄影） | 幾乎沒差 | 幾乎沒差，CPU 成本可能更高 | 瓶頸是頻寬與擁塞控制 |
| 資料中心內部（nginx → gunicorn） | 幾乎沒差：RTT 不到 1 ms | 通常不值得 | 排隊成本可以忽略 |
| 後端慢（Flask view 要 2 秒） | 沒差 | 沒差 | 瓶頸在應用程式 |
| gRPC、大量並行的內部 RPC | 必要：gRPC 建在 HTTP/2 上（第 24 章） | 依框架支援而定 | 協定本身的需求 |
| 長連線的即時訊息（WebSocket、SSE） | SSE 不再受 6 條連線限制（第 31 章） | WebSocket 多半仍走 TCP（第 32 章） | 看協定實際跑在哪一層 |

讀表時要特別注意第二列：HTTP/2 在掉包網路上可能比 HTTP/1.1 多條連線還差，這正是 Joe 在高鐵上看到的現象，也是聲聲 Live 接著啟用 HTTP/3 的理由。第四列也常被誤解：「全站升級 HTTP/2」不需要改 nginx 到 gunicorn 這一段。第一列的效益最大，但前提是不要用 domain sharding 把請求分散掉。

> [!note] 2026 現況
> 以下截至 2026 年 10 月，依 `tools/.network_survey.md` 的整理；標示「依知識」的項目未經本次網路查證。
>
> - **規格**（依知識）：HTTP/2 是 RFC 9113（2022，取代 RFC 7540）、HPACK 是 RFC 7541、HTTP/3 是 RFC 9114、QPACK 是 RFC 9204、Extensible Priorities 是 RFC 9218；HTTP 語意與快取是 RFC 9110、9111。
> - **瀏覽器**（依知識）：主流瀏覽器都支援 HTTP/2（只在 TLS 上）與 HTTP/3；HTTP/2 server push 已被 Chrome 預設停用，新設計請改用 preload 與 103 Early Hints。HTTP/3 的流量占比本書不提供數字，請以 Cloudflare Radar 或 HTTP Archive Web Almanac 的最新資料為準。
> - **Python 生態**：依 2026 年 10 月查證，gunicorn 25 起提供 HTTP/2（beta），26.2 加入 h2c 支援並修補了 HTTP/2 header 處理的問題；uvicorn 不支援 HTTP/2，需要 HTTP/2 或 HTTP/3 的 ASGI 服務可考慮 Hypercorn 或 Granian（依知識）。多數部署仍是 CDN／nginx 對外說 HTTP/2、HTTP/3，對內用 HTTP/1.1 連 gunicorn。
> - **nginx**（依知識）：新版用 `http2 on;` 指令啟用 HTTP/2，舊版是寫在 `listen` 上的 `http2` 參數；HTTP/3 需要支援 QUIC 的版本。指令依版本而定，以官方文件為準。

## 22.15 動手做：frame、HPACK、載入模擬與本機 h2c 對拍

這一節的四段程式都只用標準函式庫、可以離線執行。第一段編解碼 frame header 與 connection preface；第二段實作 HPACK 的 static table、整數編碼與 dynamic table，並用 RFC 7541 附錄的例子驗證；第三段用模擬時鐘比較 HTTP/1.1 六條連線與 HTTP/2 單連線的頁面載入時間；第四段在 127.0.0.1 上用真的 TCP socket，讓自寫的 client 與自寫的 server 用 h2c 對話，觀察兩個回應交錯在同一條連線上。

### 練習一：frame header、SETTINGS 與 connection preface

```python
import struct

# RFC 9113 第 4.1 節：9 bytes 的 frame header
# Length(24) | Type(8) | Flags(8) | R(1) + Stream Identifier(31)
FRAME_TYPES = {0x0: "DATA", 0x1: "HEADERS", 0x3: "RST_STREAM", 0x4: "SETTINGS",
               0x6: "PING", 0x7: "GOAWAY", 0x8: "WINDOW_UPDATE", 0x9: "CONTINUATION"}
END_STREAM, ACK, END_HEADERS = 0x1, 0x1, 0x4
SETTING_NAMES = {0x1: "HEADER_TABLE_SIZE", 0x2: "ENABLE_PUSH", 0x3: "MAX_CONCURRENT_STREAMS",
                 0x4: "INITIAL_WINDOW_SIZE", 0x5: "MAX_FRAME_SIZE", 0x6: "MAX_HEADER_LIST_SIZE"}
PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"


def encode_frame(ftype: int, flags: int, stream_id: int, payload: bytes = b"") -> bytes:
    if len(payload) >= 1 << 24:
        raise ValueError("length 只有 24 bits")
    # length 是 3 bytes：先用 4 bytes 打包再丟掉最高的那個 byte
    header = struct.pack("!I", len(payload))[1:] + struct.pack("!BBI", ftype, flags, stream_id & 0x7FFFFFFF)
    return header + payload


def decode_frames(data: bytes):
    """把一段 byte stream 切成 frame；不完整的尾巴留給下一次 recv。"""
    frames, pos = [], 0
    while len(data) - pos >= 9:
        length = int.from_bytes(data[pos:pos + 3], "big")
        ftype, flags, sid = struct.unpack("!BBI", data[pos + 3:pos + 9])
        if len(data) - pos - 9 < length:
            break
        frames.append((ftype, flags, sid & 0x7FFFFFFF, data[pos + 9:pos + 9 + length]))
        pos += 9 + length
    return frames, data[pos:]


def settings_payload(pairs: dict) -> bytes:
    return b"".join(struct.pack("!HI", k, v) for k, v in pairs.items())


def describe(ftype, flags, sid, payload) -> str:
    name = FRAME_TYPES.get(ftype, f"0x{ftype:x}")
    marks = []
    if ftype in (0x0, 0x1) and flags & END_STREAM:
        marks.append("END_STREAM")
    if ftype == 0x1 and flags & END_HEADERS:
        marks.append("END_HEADERS")
    if ftype in (0x4, 0x6) and flags & ACK:
        marks.append("ACK")
    text = f"{name:<13} stream={sid} len={len(payload):<3} flags=[{','.join(marks)}]"
    if ftype == 0x4:
        items = [struct.unpack("!HI", payload[i:i + 6]) for i in range(0, len(payload), 6)]
        text += " " + " ".join(f"{SETTING_NAMES[k]}={v}" for k, v in items)
    elif ftype == 0x0:
        text += f" data={payload!r}"
    return text


# 1) 手組一個 frame header，逐 byte 看
# HPACK（22.7 節）：0x82 :method GET、0x87 :scheme https、0x84 :path /、
# 0x41 0x16 + 22 bytes 字串是 :authority www.shengsheng.example
REQ_BLOCK = b"\x82\x87\x84\x41\x16" + b"www.shengsheng.example"
hdr = encode_frame(0x1, END_STREAM | END_HEADERS, 1, REQ_BLOCK)[:9]
print("HEADERS frame header:", hdr.hex(" "))
assert hdr == bytes.fromhex("00001b 01 05 00000001")

# 2) client 的 connection preface：24 bytes 魔術字串 + SETTINGS
client_bytes = PREFACE + encode_frame(0x4, 0, 0, settings_payload({0x2: 0, 0x3: 100, 0x4: 1 << 20}))
client_bytes += encode_frame(0x1, END_STREAM | END_HEADERS, 1, REQ_BLOCK)
print(f"preface {len(PREFACE)} bytes:", PREFACE)

assert client_bytes.startswith(PREFACE)
frames, rest = decode_frames(client_bytes[len(PREFACE):])
for f in frames:
    print("client →", describe(*f).rstrip())

# 3) server 的回應：SETTINGS、ACK、HEADERS、兩個 DATA
server_bytes = (encode_frame(0x4, 0, 0, settings_payload({0x3: 128, 0x5: 16384}))
                + encode_frame(0x4, ACK, 0)
                + encode_frame(0x1, END_HEADERS, 1, b"\x88")      # :status 200
                + encode_frame(0x0, 0, 1, b"<html>")
                + encode_frame(0x0, END_STREAM, 1, b"</html>"))
# 模擬 TCP 把資料切在任意位置：第一次 recv 只拿到 33 bytes
frames1, rest = decode_frames(server_bytes[:33])
print(f"第一次 recv 33 bytes：解出 {len(frames1)} 個 frame，剩 {len(rest)} bytes 等下一批")
frames2, rest = decode_frames(rest + server_bytes[33:])
for f in frames1 + frames2:
    print("server →", describe(*f).rstrip())
assert [f[0] for f in frames1 + frames2] == [0x4, 0x4, 0x1, 0x0, 0x0] and rest == b""
```

```text
HEADERS frame header: 00 00 1b 01 05 00 00 00 01
preface 24 bytes: b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'
client → SETTINGS      stream=0 len=18  flags=[] ENABLE_PUSH=0 MAX_CONCURRENT_STREAMS=100 INITIAL_WINDOW_SIZE=1048576
client → HEADERS       stream=1 len=27  flags=[END_STREAM,END_HEADERS]
第一次 recv 33 bytes：解出 2 個 frame，剩 3 bytes 等下一批
server → SETTINGS      stream=0 len=12  flags=[] MAX_CONCURRENT_STREAMS=128 MAX_FRAME_SIZE=16384
server → SETTINGS      stream=0 len=0   flags=[ACK]
server → HEADERS       stream=1 len=1   flags=[END_HEADERS]
server → DATA          stream=1 len=6   flags=[] data=b'<html>'
server → DATA          stream=1 len=7   flags=[END_STREAM] data=b'</html>'
```

逐段解說。`encode_frame` 把 24 bits 的長度用「先打包成 4 bytes 再丟掉最高 byte」的技巧放進 3 bytes，接著是 type、flags 與 31 bits 的 stream ID；`decode_frames` 反過來，先確認至少有 9 bytes，再確認 payload 完整才切出一個 frame，不完整的部分原封不動留給下一次。這是第 11 章「byte stream 沒有訊息邊界」的標準處理方式。

輸出第一行是 HEADERS frame 的 9 bytes：`00 00 1b` 長度 27、`01` HEADERS、`05` 是 END_STREAM 加 END_HEADERS、`00 00 00 01` 是 stream 1，和 22.4 節的圖一致。27 bytes 的 header block 裡，前 3 bytes 是 `:method`、`:scheme`、`:path`，後面 24 bytes 是 `:authority`。第二行是 24 bytes 的 preface。client 的 SETTINGS 帶三個 6 bytes 的項目共 18 bytes：關掉 push、允許 100 條並行 stream、把每條 stream 的初始視窗放大到 1 MB，這正是 22.8 節說的「接收端主動放大視窗」。

server 這段刻意模擬 TCP 把資料切在任意位置：第一次 recv 只拿到 33 bytes，剛好包含 21 bytes 的 SETTINGS 與 9 bytes 的 SETTINGS ACK，剩下 3 bytes 是 HEADERS frame header 的前三個 byte，解析器不會誤判，而是等下一批資料接上後再解。最後的 assert 確認五個 frame 的 type 順序與沒有殘留資料。

### 練習二：HPACK 的 static table、整數編碼與 dynamic table

```python
# HPACK（RFC 7541）：static table、整數編碼、dynamic table；不實作 Huffman
STATIC = [None,  # index 從 1 開始
    (":authority", ""), (":method", "GET"), (":method", "POST"), (":path", "/"),
    (":path", "/index.html"), (":scheme", "http"), (":scheme", "https"), (":status", "200"),
    (":status", "204"), (":status", "206"), (":status", "304"), (":status", "400"),
    (":status", "404"), (":status", "500"), ("accept-charset", ""),
    ("accept-encoding", "gzip, deflate"), ("accept-language", ""), ("accept-ranges", ""),
    ("accept", ""), ("access-control-allow-origin", ""), ("age", ""), ("allow", ""),
    ("authorization", ""), ("cache-control", ""), ("content-disposition", ""),
    ("content-encoding", ""), ("content-language", ""), ("content-length", ""),
    ("content-location", ""), ("content-range", ""), ("content-type", ""), ("cookie", ""),
    ("date", ""), ("etag", ""), ("expect", ""), ("expires", ""), ("from", ""), ("host", ""),
    ("if-match", ""), ("if-modified-since", ""), ("if-none-match", ""), ("if-range", ""),
    ("if-unmodified-since", ""), ("last-modified", ""), ("link", ""), ("location", ""),
    ("max-forwards", ""), ("proxy-authenticate", ""), ("proxy-authorization", ""),
    ("range", ""), ("referer", ""), ("refresh", ""), ("retry-after", ""), ("server", ""),
    ("set-cookie", ""), ("strict-transport-security", ""), ("transfer-encoding", ""),
    ("user-agent", ""), ("vary", ""), ("via", ""), ("www-authenticate", "")]
assert len(STATIC) - 1 == 61


def encode_int(value: int, prefix_bits: int, first_byte_flags: int = 0) -> bytes:
    """N-bit prefix 整數：放得下就直接放，放不下就填滿前綴，餘數每 7 bit 一組。"""
    limit = (1 << prefix_bits) - 1
    if value < limit:
        return bytes([first_byte_flags | value])
    out, value = [first_byte_flags | limit], value - limit
    while value >= 128:
        out.append((value & 0x7F) | 0x80)   # 最高位 1 表示「後面還有」
        value >>= 7
    out.append(value)
    return bytes(out)


def decode_int(data: bytes, pos: int, prefix_bits: int):
    limit = (1 << prefix_bits) - 1
    value = data[pos] & limit
    pos += 1
    if value < limit:
        return value, pos
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        value += (b & 0x7F) << shift
        shift += 7
        if not b & 0x80:
            return value, pos


class Decoder:
    def __init__(self, max_size: int = 4096):
        self.dynamic, self.max_size = [], max_size   # dynamic[0] 是最新的，index 62

    def size(self):
        return sum(len(n) + len(v) + 32 for n, v in self.dynamic)   # 每筆多算 32 bytes 管理成本

    def lookup(self, index):
        return STATIC[index] if index <= 61 else self.dynamic[index - 62]

    def read_string(self, data, pos):
        if data[pos] & 0x80:
            raise NotImplementedError("Huffman 字串：本例不實作")
        length, pos = decode_int(data, pos, 7)
        return data[pos:pos + length].decode(), pos + length

    def decode(self, block: bytes):
        headers, pos = [], 0
        while pos < len(block):
            b = block[pos]
            if b & 0x80:                                    # 1xxxxxxx：Indexed
                index, pos = decode_int(block, pos, 7)
                headers.append(self.lookup(index))
                continue
            incremental = b & 0x40                           # 01xxxxxx：要加進 dynamic table
            index, pos = decode_int(block, pos, 6 if incremental else 4)
            name = self.lookup(index)[0] if index else None
            if name is None:
                name, pos = self.read_string(block, pos)
            value, pos = self.read_string(block, pos)
            headers.append((name, value))
            if incremental:
                self.dynamic.insert(0, (name, value))
                while self.size() > self.max_size:
                    self.dynamic.pop()                        # 從最舊的開始淘汰
        return headers


# 1) RFC 7541 附錄 C.1 的整數範例
assert encode_int(10, 5) == b"\x0a"
assert encode_int(1337, 5) == bytes.fromhex("1f9a0a")
assert decode_int(bytes.fromhex("1f9a0a"), 0, 5) == (1337, 3)
print("1337 用 5-bit prefix 編碼:", encode_int(1337, 5).hex(" "))

# 2) 附錄 C.3：同一條連線上的連續兩個請求（不用 Huffman）
dec = Decoder()
req1 = bytes.fromhex("828684410f7777772e6578616d706c652e636f6d")
req2 = bytes.fromhex("828684be58086e6f2d6361636865")
for n, block in enumerate([req1, req2], 1):
    print(f"請求 {n}：{len(block)} bytes → {dec.decode(block)}")
    print(f"  dynamic table（{dec.size()} bytes）:",
          [(62 + i, f"{k}: {v}") for i, (k, v) in enumerate(dec.dynamic)])
assert dec.size() == 110 and dec.lookup(63) == (":authority", "www.example.com")

# 3) 聲聲 Live 的情境：同一個瀏覽器連續要 3 張大頭照
plain = ("GET /avatars/{n}.webp HTTP/1.1\r\nHost: www.shengsheng.example\r\n"
         "User-Agent: Mozilla/5.0 (Macintosh) ExampleBrowser/1.0\r\n"
         "Accept: image/webp,*/*\r\nCookie: sid=3f9c2a7b1e5d4c88\r\n\r\n")


def literal_indexed(name_index: int, value: str) -> bytes:
    """01xxxxxx：用 static table 的名稱，值用原文，並加進 dynamic table。"""
    raw = value.encode()
    return encode_int(name_index, 6, 0x40) + encode_int(len(raw), 7) + raw


first = (b"\x82\x87" + literal_indexed(1, "www.shengsheng.example")
         + literal_indexed(58, "Mozilla/5.0 (Macintosh) ExampleBrowser/1.0")
         + literal_indexed(19, "image/webp,*/*") + literal_indexed(32, "sid=3f9c2a7b1e5d4c88"))
d2 = Decoder()
for n in (1, 2, 3):
    path = f"/avatars/{n}.webp".encode()
    # :path 每次不同 → literal without indexing（0000xxxx，name 用 static index 4）
    path_field = encode_int(4, 4) + encode_int(len(path), 7) + path
    if n == 1:
        block = first + path_field
    else:   # 其他 header 都已在 dynamic table：62..65 各 1 byte
        block = b"\x82\x87" + bytes([0x80 | 65, 0x80 | 64, 0x80 | 63, 0x80 | 62]) + path_field
    got = dict(d2.decode(block))
    assert got[":path"] == path.decode() and got["cookie"] == "sid=3f9c2a7b1e5d4c88"
    print(f"大頭照 {n}：HTTP/1.1 文字 {len(plain.format(n=n))} bytes，HPACK {len(block)} bytes")
```

```text
1337 用 5-bit prefix 編碼: 1f 9a 0a
請求 1：20 bytes → [(':method', 'GET'), (':scheme', 'http'), (':path', '/'), (':authority', 'www.example.com')]
  dynamic table（57 bytes）: [(62, ':authority: www.example.com')]
請求 2：14 bytes → [(':method', 'GET'), (':scheme', 'http'), (':path', '/'), (':authority', 'www.example.com'), ('cache-control', 'no-cache')]
  dynamic table（110 bytes）: [(62, 'cache-control: no-cache'), (63, ':authority: www.example.com')]
大頭照 1：HTTP/1.1 文字 172 bytes，HPACK 125 bytes
大頭照 2：HTTP/1.1 文字 172 bytes，HPACK 23 bytes
大頭照 3：HTTP/1.1 文字 172 bytes，HPACK 23 bytes
```

第一段驗證整數編碼：1337 在 5-bit prefix 下是 `1f 9a 0a`，和 22.7 節的手算一致。第二段解碼 RFC 7541 附錄 C.3 的兩個連續請求。請求 1 的 20 bytes 裡，`82 86 84` 是三個 static 查表，`41` 是「literal with incremental indexing、名稱用 static 1 號 `:authority`」，`0f` 是長度 15、未經 Huffman，後面是 `www.example.com`；解完之後 dynamic table 多了一筆，大小 15 + 10 + 32 = 57 bytes。請求 2 只有 14 bytes：`be` 是 0x80 | 62，直接查到上一個請求留下的 `:authority`；`58` 是 0x40 | 24，名稱用 static 24 號 `cache-control`，值 `no-cache` 被插入表中成為新的 62 號，原本的 `:authority` 被推到 63 號，表的大小變成 110 bytes。這就是「新的永遠是 62 號」的實際效果。

第三段是聲聲 Live 的情境。第一張大頭照的 header block 要把 `:authority`、`user-agent`、`accept`、`cookie` 各用 literal 送一次並加進表裡，共 125 bytes；第二張之後，這四個欄位各只要 1 byte（62 到 65 號），加上 `:method`、`:scheme` 各 1 byte，剩下的 17 bytes 都是每次不同的 `:path`。HTTP/1.1 的文字版每次 172 bytes，八十張圖就是約 13.7 KB 的上行 header；HPACK 只要約 2 KB。真實瀏覽器的 header 更多更長，省下的比例通常更高。

### 練習三：模擬時鐘比較六條連線與單一連線

```python
import heapq

# 模擬時鐘（毫秒）。模型刻意簡化：
#  - 一條瓶頸鏈路，回應依「抵達 server 的順序」排隊傳送（FIFO）
#  - 新連線要 2 RTT（TCP 交握 + TLS 1.3 交握）才能送第一個請求
#  - 忽略 slow start、server 處理時間與封包遺失
HTML = ("index.html", 30_000)
SUBRESOURCES = [("app.css", 40_000), ("app.js", 120_000)] + \
               [(f"avatar{i:02d}.webp", 6_000) for i in range(80)]


class Link:
    def __init__(self, rtt, mbps):
        self.rtt, self.rate, self.free_at = rtt, mbps * 125, 0.0   # 1 Mbps = 125 bytes/ms

    def fetch(self, send_at, size):
        """client 在 send_at 送出請求，回傳整份回應抵達 client 的時間。"""
        arrive = send_at + self.rtt / 2
        start = max(arrive, self.free_at)
        self.free_at = start + size / self.rate
        return self.free_at + self.rtt / 2


def http1(rtt, mbps, max_conns=6, resources=SUBRESOURCES):
    link = Link(rtt, mbps)
    html_done = link.fetch(2 * rtt, HTML[1])        # 第一條連線：建好就要 HTML
    queue = list(resources)
    # 解析完 HTML 才知道要什麼；第一條連線立刻可用，其他連線要現在才開始交握
    ready = [(html_done, 0)] + [(html_done + 2 * rtt, c) for c in range(1, max_conns)]
    heapq.heapify(ready)
    finish = html_done
    while queue:
        t, conn = heapq.heappop(ready)
        name, size = queue.pop(0)
        done = link.fetch(t, size)                  # 同一條連線一次只能有一個請求在路上
        finish = max(finish, done)
        heapq.heappush(ready, (done, conn))
    return finish


def http2(rtt, mbps, resources=SUBRESOURCES):
    link = Link(rtt, mbps)
    html_done = link.fetch(2 * rtt, HTML[1])
    # 一條連線：所有請求同時送出（multiplexing），回應在同一條管子裡交錯
    return max(link.fetch(html_done, size) for _, size in resources)


SCENARIOS = [
    ("美國學生 RTT 180ms／20Mbps", 180, 20, SUBRESOURCES),
    ("台灣學生 RTT 20ms／100Mbps", 20, 100, SUBRESOURCES),
    ("高鐵上 RTT 180ms／3Mbps", 180, 3, SUBRESOURCES),
    ("只下載一支 5MB 錄影", 180, 20, [("lesson.mp4", 5_000_000)]),
]
print(f"{'h1 x6':>8}{'h1 x12':>9}{'h2':>8}{'省下':>8}  情境")
results = {}
for label, rtt, mbps, res in SCENARIOS:
    h1 = http1(rtt, mbps, 6, res)
    h1_shard = http1(rtt, mbps, 12, res)             # domain sharding：兩個主機名各 6 條
    h2 = http2(rtt, mbps, res)
    results[label] = (h1, h2)
    print(f"{h1:>6.0f}ms{h1_shard:>7.0f}ms{h2:>6.0f}ms{h1 - h2:>7.0f}ms  {label}")

# 一次 round trip 的估算：82 個請求 / 6 條連線 ≈ 14 輪，每輪至少 1 RTT
rounds = -(-len(SUBRESOURCES) // 6)
print(f"\nHTTP/1.1×6 至少要 {rounds} 輪 round trip；RTT 180ms 時光等待就約 {rounds * 180}ms")
us, tw, slow, video = (results[s[0]] for s in SCENARIOS)
assert us[0] - us[1] > 2000 and tw[0] - tw[1] < 300           # RTT 越大，HTTP/2 省越多
assert abs(video[0] - video[1]) < 1                          # 單一大檔：一樣快
assert slow[0] / slow[1] < us[0] / us[1]                     # 頻寬是瓶頸時差距縮小
print("RTT 越大、資源越多越小，HTTP/2 越有感；頻寬不足或單一大檔時差距縮小或消失")
```

```text
   h1 x6   h1 x12      h2      省下  情境
  3468ms   2206ms   988ms   2480ms  美國學生 RTT 180ms／20Mbps
   390ms    249ms   134ms    256ms  台灣學生 RTT 20ms／100Mbps
  3987ms   2711ms  2507ms   1480ms  高鐵上 RTT 180ms／3Mbps
  2732ms   2732ms  2732ms      0ms  只下載一支 5MB 錄影

HTTP/1.1×6 至少要 14 輪 round trip；RTT 180ms 時光等待就約 2520ms
RTT 越大、資源越多越小，HTTP/2 越有感；頻寬不足或單一大檔時差距縮小或消失
```

模型的核心是 `Link.fetch`：請求花半個 RTT 到 server，回應在瓶頸鏈路上排隊、依頻寬傳完，再花半個 RTT 回到 client。`http1` 讓每條連線一次只處理一個請求，用 heap 找出「最早空出來的連線」接下一個資源；HTML 回來之前瀏覽器不知道還要什麼，所以另外五條連線要等 HTML 解析後才開始交握，這也是 `preconnect` 的價值所在。`http2` 只有一條連線，HTML 回來後所有請求在同一刻送出。

看輸出第一列，美國學生的情境：HTTP/1.1 六條連線要 3,468 ms，其中光是 14 輪 round trip 就約 2,520 ms；HTTP/2 只要 988 ms，等於 2 RTT 交握＋HTML 的 1 RTT 與傳輸時間＋子資源的 1 RTT＋640 KB 在 20 Mbps 上的 256 ms。domain sharding 把連線數加倍到 12，可以降到 2,206 ms，但仍遠不及 HTTP/2，而且模型還沒算進多出來的 DNS 查詢與憑證驗證。第二列台灣學生 RTT 只有 20 ms，HTTP/2 只省下 256 ms，對使用者來說差異小得多。第三列頻寬只有 3 Mbps 時，大部分時間花在傳輸本身，HTTP/2 的優勢從 3.5 倍縮小到約 1.6 倍。第四列只下載一個大檔，三種方式完全一樣，因為根本沒有排隊可以省。

模型刻意忽略 slow start、封包遺失、server 處理時間與渲染，絕對數字和 DevTools 量到的不同，要看的是相對趨勢；被忽略的因素有些對 HTTP/1.1 有利（初始擁塞視窗加起來是 6 倍），有些對 HTTP/2 有利（header 更小、可排優先順序）。

### 練習四：在 127.0.0.1 上用自寫的 frame 跑 h2c

```python
import socket
import struct
import threading

# 在 127.0.0.1 上用自寫的 frame 跑一次 h2c（prior knowledge，不經 TLS、不經 Upgrade）
PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
DATA, HEADERS, SETTINGS, GOAWAY = 0x0, 0x1, 0x4, 0x7
END_STREAM, ACK, END_HEADERS = 0x1, 0x1, 0x4
NAMES = {0: "DATA", 1: "HEADERS", 4: "SETTINGS", 7: "GOAWAY"}
STATIC = {1: ":authority", 4: ":path", 31: "content-type"}   # 本例用到的 static table 項目


def frame(ftype, flags, sid, payload=b""):
    return struct.pack("!I", len(payload))[1:] + struct.pack("!BBI", ftype, flags, sid) + payload


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("對方關閉連線")
        buf += chunk
    return buf


def read_frame(sock):
    head = recv_exact(sock, 9)
    length = int.from_bytes(head[:3], "big")
    ftype, flags, sid = struct.unpack("!BBI", head[3:])
    return ftype, flags, sid & 0x7FFFFFFF, recv_exact(sock, length)


def literal(name_index, value: str) -> bytes:
    """0000xxxx literal without indexing；本例的 index 與長度都小於 127，簡化整數編碼。"""
    first = bytes([name_index]) if name_index < 15 else bytes([15, name_index - 15])
    return first + bytes([len(value)]) + value.encode()


def decode_block(block):
    out, pos = {}, 0
    while pos < len(block):
        b = block[pos]
        if b & 0x80:                       # indexed：本例只會出現 GET、https、200
            out[{0x82: ":method", 0x87: ":scheme", 0x88: ":status"}[b]] = {0x82: "GET", 0x87: "https", 0x88: "200"}[b]
            pos += 1
            continue
        index, pos = (b, pos + 1) if b < 15 else (15 + block[pos + 1], pos + 2)
        length = block[pos]
        out[STATIC[index]] = block[pos + 1:pos + 1 + length].decode()
        pos += 1 + length
    return out


BODIES = {"/api/teachers": b'[{"name":"misaki","lang":"ja"},{"name":"minjun","lang":"ko"}]',
          "/avatars/1.webp": b"RIFF....WEBPVP8 " + b"\x00" * 24}


def server(listener):
    conn, _ = listener.accept()
    with conn:
        assert recv_exact(conn, len(PREFACE)) == PREFACE        # 不是 preface 就不是 HTTP/2
        conn.sendall(frame(SETTINGS, 0, 0, struct.pack("!HI", 0x3, 100)))
        pending = {}
        while len(pending) < 2:
            ftype, flags, sid, payload = read_frame(conn)
            if ftype == SETTINGS and not flags & ACK:
                conn.sendall(frame(SETTINGS, ACK, 0))
            elif ftype == HEADERS:
                pending[sid] = BODIES[decode_block(payload)[":path"]]
        for sid, body in pending.items():
            ctype = "application/json" if sid == 1 else "image/webp"
            conn.sendall(frame(HEADERS, END_HEADERS, sid, b"\x88" + literal(31, ctype)))
        # 兩個回應切成 16 bytes 的 DATA，輪流送：同一條 TCP 連線上交錯
        chunks = {sid: [b[i:i + 16] for i in range(0, len(b), 16)] for sid, b in pending.items()}
        while any(chunks.values()):
            for sid in sorted(chunks):
                if chunks[sid]:
                    piece = chunks[sid].pop(0)
                    conn.sendall(frame(DATA, 0 if chunks[sid] else END_STREAM, sid, piece))
        conn.sendall(frame(GOAWAY, 0, 0, struct.pack("!II", 3, 0)))   # last stream 3、NO_ERROR
        # 優雅關閉：先半關閉，再把對方還在路上的 frame（例如 SETTINGS ACK）讀完，避免 RST
        conn.shutdown(socket.SHUT_WR)
        while conn.recv(4096):
            pass


listener = socket.create_server(("127.0.0.1", 0))
t = threading.Thread(target=server, args=(listener,))
t.start()
cli = socket.create_connection(listener.getsockname())
auth = literal(1, "www.shengsheng.example")
cli.sendall(PREFACE + frame(SETTINGS, 0, 0)
            + frame(HEADERS, END_STREAM | END_HEADERS, 1, b"\x82\x87" + literal(4, "/api/teachers") + auth)
            + frame(HEADERS, END_STREAM | END_HEADERS, 3, b"\x82\x87" + literal(4, "/avatars/1.webp") + auth))
bodies, order = {1: b"", 3: b""}, []
while True:
    ftype, flags, sid, payload = read_frame(cli)
    note = ""
    if ftype == SETTINGS and not flags & ACK:
        cli.sendall(frame(SETTINGS, ACK, 0))
        note = "（回 ACK）"
    elif ftype == HEADERS:
        note = str(decode_block(payload))
    elif ftype == DATA:
        bodies[sid] += payload
        order.append(sid)
        note = "END_STREAM" if flags & END_STREAM else ""
    elif ftype == GOAWAY:
        note = "last_stream_id=%d error=%d" % struct.unpack("!II", payload)
    print(f"{NAMES[ftype]:<9} stream={sid} len={len(payload):<3} {note}".rstrip())
    if ftype == GOAWAY:
        break
cli.close()
t.join()
listener.close()
print("DATA 抵達的 stream 順序:", order)
assert bodies[1] == BODIES["/api/teachers"] and bodies[3] == BODIES["/avatars/1.webp"]
assert order[:4] == [1, 3, 1, 3]          # 兩個回應真的交錯在同一條連線上
print("兩個回應都完整重組，且交錯傳送")
```

```text
SETTINGS  stream=0 len=6   （回 ACK）
SETTINGS  stream=0 len=0
HEADERS   stream=1 len=20  {':status': '200', 'content-type': 'application/json'}
HEADERS   stream=3 len=14  {':status': '200', 'content-type': 'image/webp'}
DATA      stream=1 len=16
DATA      stream=3 len=16
DATA      stream=1 len=16
DATA      stream=3 len=16
DATA      stream=1 len=16
DATA      stream=3 len=8   END_STREAM
DATA      stream=1 len=13  END_STREAM
GOAWAY    stream=0 len=8   last_stream_id=3 error=0
DATA 抵達的 stream 順序: [1, 3, 1, 3, 1, 3, 1]
兩個回應都完整重組，且交錯傳送
```

這段程式是一次完整、但極度精簡的 h2c 對話，兩端都是我們自己寫的，所以是「對拍」：client 依規格組 frame，server 依規格解，雙方任一邊寫錯，assert 就會失敗。client 一連上就送 preface、空的 SETTINGS 與兩個 HEADERS（stream 1 要老師清單、stream 3 要一張大頭照），完全不等 server 回應，這就是 prior knowledge 的 h2c。

依輸出逐行看。第一行是 server 的 SETTINGS（一個 6 bytes 項目：MAX_CONCURRENT_STREAMS=100），client 回 ACK；第二行是 server 對 client SETTINGS 的 ACK。接著是兩個 HEADERS：`:status` 用 0x88 一個 byte，`content-type` 用 literal without indexing，因為 static 31 號大於 4-bit prefix 的上限 15，名稱編號要用兩個 byte（`0f 10`）表示。然後 DATA frame 在 stream 1 與 3 之間輪流出現，各自在最後一個 frame 帶 END_STREAM，最後 GOAWAY 告訴 client「最後處理的是 stream 3，沒有錯誤」。最後的 assert 確認兩個 body 都完整重組，而且前四個 DATA 真的是 1、3、1、3 交錯，這就是 multiplexing 在線路上的樣子。

server 收尾時先 `shutdown(SHUT_WR)` 再把剩下的資料讀完，這個細節不是裝飾。第一版程式沒有這一步，server 送完 GOAWAY 就直接 close，而 client 的 SETTINGS ACK 還在 server 的接收緩衝區裡沒被讀走，核心因此送出 RST（第 10 章 10.9 節的情況），client 讀 GOAWAY 時拿到 `ConnectionResetError`。真實的 HTTP/2 server 關閉連線時也是同樣的順序：送 GOAWAY、停止接受新 stream、處理完進行中的 stream、讀完對方送來的資料，最後才關閉 TCP。

## 22.16 在工作上怎麼用

### 情境一：前端效能檢查，把 HTTP/1.1 偏方拆掉

小晴替「找老師」頁面做的改造清單，順序就是判斷流程：

1. **先確認協定與連線數**：DevTools Network 面板打開 Protocol 與 Connection ID 欄。同一個頁面的資源如果分散在多個 Connection ID，先找出原因（不同網域、不同憑證、不同 IP）。
2. **移除 domain sharding**：把 `img1`、`img2` 的資源搬回 `www`，舊網址 301 導回；或至少讓它們能被合併（同一組 IP、同一張涵蓋所有名稱的憑證）。
3. **拆掉 sprite 與大量 inline**：改成獨立的小檔案，讓每個檔案可以獨立快取、獨立失效；只保留首屏關鍵 CSS 的 inline。
4. **設定優先順序與提示**：首屏 CSS 用 `<link rel="preload">`，非首屏的大頭照用 `loading="lazy"` 與較低的 `fetchpriority`；server 若需要較長的思考時間，評估 103 Early Hints。
5. **重新量測**：分別在高 RTT（模擬美國學生）與低 RTT 下量 LCP（最大內容繪製時間）與總載入時間，用中位數比較，不要只看一次。

改完之後，「找老師」頁面只剩一條連線，美國學生的載入時間降到約 1.3 秒。Chrome DevTools 的 Network throttling 可以模擬高延遲，但它是在瀏覽器層加延遲，和真實的高 RTT 網路行為不完全相同；需要更接近真實的量測，可以在 Linux 測試機上用 `tc qdisc ... netem delay 180ms` 加延遲（第 12 章的動手練習用過 netem）。

### 情境二：確認一個請求到底用了哪個協定

```bash
# 看 ALPN 協商結果與 HTTP 版本（-v 會印出 "ALPN: server accepted h2" 一類訊息，格式依 curl 版本而定）
curl -sv -o /dev/null https://www.shengsheng.example/teachers 2>&1 | grep -iE "ALPN|HTTP/2|HTTP/1.1"
# 強制 HTTP/1.1 與 HTTP/2 各量一次，比較 time_connect、time_starttransfer
curl -so /dev/null --http1.1 -w '%{http_version} %{time_connect} %{time_starttransfer}\n' https://www.shengsheng.example/
curl -so /dev/null --http2   -w '%{http_version} %{time_connect} %{time_starttransfer}\n' https://www.shengsheng.example/
# 用 openssl 只看 ALPN（不送 HTTP 請求）
openssl s_client -connect www.shengsheng.example:443 -alpn h2,http/1.1 </dev/null 2>/dev/null | grep -i alpn
# 對內部的 h2c 服務（例如 gRPC 或支援 h2c 的 gunicorn）用 prior knowledge 測試
curl -sv --http2-prior-knowledge http://10.20.3.21:8000/healthz -o /dev/null
```

示意輸出（每台機器、每個版本的格式略有不同）：

```text
* ALPN: curl offers h2,http/1.1
* ALPN: server accepted h2
> GET /teachers HTTP/2
< HTTP/2 200
1.1 0.181 0.552
2 0.180 0.548
ALPN protocol: h2
```

讀法：`server accepted h2` 代表 TLS 交握時已經選定 HTTP/2；`-w` 的 `%{http_version}` 印出實際使用的版本。單一請求下 HTTP/1.1 與 HTTP/2 的時間幾乎一樣，這是正常的，因為差別只在「很多請求同時進行」時才會顯現。要比較整頁效果，要用瀏覽器或能同時發多個請求的工具（例如 `h2load`，屬於 nghttp2 工具組）。

### 情境三：SRE 調整 nginx 與 CDN 的 HTTP/2 設定

```bash
# 示意設定片段（nginx，指令名稱依版本而定）
#   listen 443 ssl;
#   http2 on;
#   http2_max_concurrent_streams 128;     # 預設值依版本而定
#   large_client_header_buffers 4 16k;    # 也限制了 HTTP/2 的 header 大小
#   location / { proxy_pass http://gunicorn_upstream; proxy_http_version 1.1; proxy_set_header Connection ""; }
nginx -t && nginx -s reload
```

檢查重點有四個。第一，`http2` 只影響 client 到 nginx；到 gunicorn 仍是 HTTP/1.1，要用 `proxy_http_version 1.1` 加上清空 `Connection` 才能讓 upstream 連線 keep-alive（第 25 章）。第二，並行 stream 與 header 大小的上限要明確設定，這是 22.10 節那些攻擊的第一道防線。第三，`keepalive_timeout`、`keepalive_requests` 一類設定決定 nginx 何時送 GOAWAY，部署或縮容時要確認進行中的請求能完成。第四，access log 要記錄協定版本（`$server_protocol`），才能依協定拆分錯誤率與延遲。

## 22.17 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 開了 HTTP/2，頁面只快一點點 | domain sharding、多張憑證或多組 IP 讓連線無法合併；sprite 與大包資源還在 | DevTools 的 Connection ID 欄有多個值；比較各網域的 DNS 結果與憑證 SAN | 移除 sharding、資源回到同源；拆掉 sprite；必要時統一憑證與 edge |
| 行動網路上 HTTP/2 偶爾整頁一起卡住 | 單一 TCP 連線遇到封包遺失，所有 stream 被 HOL 擋住 | 抓包看到重傳期間所有 stream 都沒有 DATA 送到應用程式；netlog 的 HTTP/2 session 同時停頓 | 啟用 HTTP/3 並保留 HTTP/2 fallback；檢查擁塞控制設定（第 12 章） |
| 老師上傳錄影在 HTTP/2 下比 HTTP/1.1 慢很多 | server 端的接收視窗太小，送出端每個 RTT 只能送一個視窗的量 | 抓包或 server log 看到 client 頻繁等 WINDOW_UPDATE；上傳速度約等於視窗 ÷ RTT | 調大 server 的 stream 與連線層級接收視窗；確認 proxy 不會因後端慢而停止給額度 |
| 某些 client 連線後立刻被斷，log 有 PROTOCOL_ERROR | client 送了大寫 header 名稱或 `Connection` 等禁止的 header；或自製 client 的 frame 格式錯誤 | 用 `nghttp -nv` 或 Wireshark 看 GOAWAY／RST_STREAM 的錯誤碼與最後一個 frame | 修 client：header 名稱小寫、移除連線層級 header；用成熟的函式庫 |
| 瀏覽器收到 421 Misdirected Request | 請求被合併到一條 server 無法服務該網域的連線上 | DevTools 看到 421 後立刻有新連線重試；比對憑證 SAN 與 CDN 的網域設定 | 讓 edge 能服務所有合併的名稱，或縮小萬用字元憑證的範圍；421 本身是正確的保護 |
| 內部 h2c 服務完全連不上，log 顯示看不懂的請求 `PRI * HTTP/2.0` | 一端用 prior knowledge 送 h2c，另一端只說 HTTP/1.1（或反過來） | server log 出現 method `PRI`；`curl --http2-prior-knowledge` 與 `curl --http1.1` 結果不同 | 兩端設定一致：都用 h2c，或都用 HTTP/1.1；跨網路時改用 TLS 加 ALPN |
| CDN 公告 HTTP/2 漏洞後 server CPU 異常飆高，但請求數沒有增加 | Rapid Reset 一類濫用：大量 stream 開了就取消，從未完成 | 監控每條連線的 RST_STREAM 數量；access log 裡完成的請求數和 CPU 不成比例 | 更新 CDN、nginx 與函式庫；限制 reset 速率並以 GOAWAY 關閉異常連線 |
| 0-RTT 開啟後出現重複寫入 | 非 idempotent 請求進入 early data 被重放 | 後端 log 看到帶 `Early-Data: 1` 的 POST | 只允許 GET／HEAD 走 0-RTT，其他回 425 Too Early；寫入 API 加 idempotency key（第 24 章） |

最常見的思考錯誤，是把「協定版本」當成單一事實：瀏覽器到 CDN 可能是 h3，CDN 到 nginx 是 h2，nginx 到 gunicorn 是 HTTP/1.1。問題出在哪一段，就到那一段的 log 與抓包找證據；Flask 這端也不要依賴 `Connection` 這類只在 HTTP/1.1 有意義的 header。

## 22.18 動手練習

1. **延伸 frame 解析器**：在練習一的 `describe` 加上 WINDOW_UPDATE（payload 是 4 bytes，最高位保留，取低 31 bits）、RST_STREAM（4 bytes 錯誤碼）與 GOAWAY（last stream ID 加錯誤碼）的解析，並把錯誤碼對應成名稱（0x0 NO_ERROR、0x1 PROTOCOL_ERROR、0x3 FLOW_CONTROL_ERROR、0x7 REFUSED_STREAM、0x8 CANCEL、0xb ENHANCE_YOUR_CALM）。
   *答案要點*：`struct.unpack("!I", payload)[0] & 0x7FFFFFFF` 取 increment；GOAWAY 用 `"!II"`。用 `encode_frame(0x3, 0, 5, struct.pack("!I", 8))` 自己組一個 CANCEL 來驗證。

2. **延伸 HPACK**：替練習二寫一個 `Encoder`，規則是「static table 有整筆就用 Indexed；dynamic table 有整筆就用 Indexed；名稱在表裡就用 literal with incremental indexing；`authorization` 一律用 never indexed」，再用練習二的 `Decoder` 解回來，確認結果一致，並印出八十張大頭照的總 header bytes。
   *答案要點*：encoder 要維護和 decoder 一模一樣的 dynamic table（同樣的插入與淘汰順序）；never indexed 的第一個 byte 是 `0x10 | 名稱編號`（4-bit prefix）。對拍時兩邊表格不一致是最常見的 bug。

3. **在載入模擬裡加入封包遺失**：在 `Link` 加一個參數「在時間 T 遺失一個封包」，對 HTTP/2 的單一連線，讓所有在 T 之後才完成的回應延後 1 個 RTT；對 HTTP/1.1，只延後遺失發生時那一條連線上進行中的回應。再加一欄 HTTP/3：只延後遺失那一個資源。比較美國學生情境下三者的差距。
   *驗證方法*：遺失越早發生，HTTP/2 被拖累的資源越多；HTTP/3 欄應該幾乎不受影響。這也是第 13 章練習三的結論在頁面層級的版本。

4. **改 h2c 程式觀察 flow control**：讓 client 在 SETTINGS 裡宣告 `INITIAL_WINDOW_SIZE=20`，server 每送一個 DATA 就扣視窗，視窗不夠時停下來等 client 送 WINDOW_UPDATE；client 每收到一個 DATA 就回一個對應大小的 WINDOW_UPDATE。印出每一步的視窗變化。
   *答案要點*：連線層級的視窗仍是 65,535（只能用 WINDOW_UPDATE 改），只有 stream 層級變成 20；server 要能同時處理「讀 WINDOW_UPDATE」與「送 DATA」，最簡單的作法是送一個 DATA 後就讀一個 frame。

5. **用真實工具觀察**：在自己的電腦上用 `curl -sv --http2 -o /dev/null` 連一個大型網站，找出 ALPN 結果；再用 DevTools 打開一個圖片很多的網站，打開 Protocol 與 Connection ID 欄，數一數頁面用了幾條連線、有沒有被合併的不同網域。
   *驗證方法*：同一個 Connection ID 下出現不同網域，就是連線合併；用 `openssl s_client -connect 網域:443 < /dev/null | openssl x509 -noout -ext subjectAltName` 看那張憑證是否涵蓋這些名稱。

6. **用 Wireshark 看 HTTP/2 frame**：設定 `SSLKEYLOGFILE` 後用瀏覽器開一個 HTTPS 網站並抓包，在 Wireshark 用顯示過濾 `http2` 找出 Magic（preface）、雙方的 SETTINGS 與 ACK、第一個 HEADERS，展開看 HPACK 解出的 header 與「Header table size」。
   *答案要點*：Wireshark 會標出每個 header 是 Indexed 還是 Literal；同一條連線上第二個請求的 HEADERS 會明顯比第一個小，這就是 dynamic table 的效果。抓完記得刪除 key log 檔。

## 本章重點整理

- HTTP/2 與 HTTP/3 沒有改變 HTTP 的語意，method、status code、header、快取規則都沿用 RFC 9110 與 9111，改變的只是上線格式與傳輸方式，所以應用程式通常不必修改。
- HTTP/1.1 的根本限制是一條連線一次只能有一個回應在路上，加上每個主機約 6 條連線的上限，資源多時要排成很多輪 round trip；pipelining 因應用層 HOL 與 proxy 相容性問題而沒有普及。
- domain sharding、sprite、合併與 inline 都是用快取粒度、交握次數與優先順序換取請求數的偏方，在 HTTP/2 下多半變成負擔，尤其 sharding 會破壞單連線多工。
- HTTP/2 的每個 frame 都以 9 bytes 開頭：24 bits 長度、8 bits type、8 bits flags、1 bit 保留與 31 bits stream ID；stream 0 用於連線層級的控制，client 的 stream 用奇數且不重用，RST_STREAM 只取消單一請求，GOAWAY 用於優雅關閉。
- 連線一開始 client 送 24 bytes 的 preface 加 SETTINGS，雙方都要 ACK 對方的 SETTINGS；SETTINGS 描述的是送出者自己的接收能力。
- HPACK 用 61 筆的 static table、連線內累積的 dynamic table、N-bit prefix 整數與固定 Huffman 碼表壓縮 header，避開了 CRIME 式的長度洩漏；敏感欄位應用 never indexed。
- HTTP/2 的 flow control 有 stream 與連線兩層，只管 DATA frame，預設視窗 65,535 bytes；在高 RTT 路徑上視窗太小會把吞吐量限制在視窗 ÷ RTT。
- 舊的優先順序依賴樹已被 deprecated，改用 RFC 9218 的 urgency 與 incremental；server push 已實質退場，由 preload 與 103 Early Hints 取代。
- HTTP/2 把所有請求押在一條 TCP 連線上，封包遺失會造成跨 stream 的 HOL；它也帶來 Rapid Reset、CONTINUATION flood 等新攻擊面，必須在每條連線上設限制並保持更新。
- HTTP/3 把每個請求放在一條 QUIC 雙向 stream，flow control、取消、PING 都交給 QUIC，frame 只剩 varint 的 type 與 length；發現 h3 靠 Alt-Svc 或 DNS HTTPS record，失敗時退回 HTTP/2。
- QPACK 把表格插入放在單向的 encoder stream，header block 用 Required Insert Count 說明依賴，讓亂序到達的 stream 只在必要時才 blocked，encoder 可以在壓縮率與阻塞之間取捨。
- 連線合併要求憑證涵蓋新名稱，多數瀏覽器還要求 IP 相符；ORIGIN frame 可以放寬檢查，server 遇到不該服務的名稱要回 421。
- 升級協定在高 RTT、資源多而小、會掉包或換網路時效益最大；在資料中心內部、單一大檔或後端本身很慢時幾乎沒差。

## 延伸問答

> [!question]- Q1. HTTP/2 已經有 multiplexing，為什麼還說它有 head-of-line blocking？HTTP/1.1 的 HOL 和 HTTP/2 的 HOL 是同一件事嗎？
> 不是同一件事，要分層看。HTTP/1.1 的 HOL 在應用層：同一條連線上的回應必須依請求順序送回，第一個回應慢，後面已經準備好的回應也得排隊。HTTP/2 用 stream 編號解決了這一層，server 可以先送任何已經準備好的 frame。
>
> 但 HTTP/2 的所有 stream 仍然跑在一條 TCP byte stream 上。TCP 保證整條連線的位元組依序交付，一個 segment 遺失時，核心會扣住後面所有已到達的資料，不論它們屬於哪一條 stream。所以 HTTP/2 把 HOL 從應用層推到了傳輸層。HTTP/3 改用 QUIC，每條 stream 各自依 offset 重組，一個封包遺失只影響它所屬的 stream，才真正消除跨請求的 HOL；stream 內部的順序仍然要等重傳。
>
> 判斷依據是「誰在強制順序」：HTTP/1.1 是協定本身沒有編號，HTTP/2 是 TCP 只有一條 byte stream，HTTP/3 只剩各 stream 內部的順序。

> [!question]- Q2. 手算：一個 HTTP/2 frame 的前 9 bytes 是 `00 40 00 00 01 00 00 00 05`，這是什麼 frame？如果對方沒有調過任何 SETTINGS，這個 frame 合法嗎？
> 拆欄位：`00 40 00` 是長度 0x004000 = 16,384 bytes；`00` 是 type DATA；`01` 是 flags，對 DATA 來說是 END_STREAM；`00 00 00 05` 是 stream 5（最高位 R 為 0）。所以這是 stream 5 的最後一個 DATA frame，payload 剛好 16,384 bytes。
>
> 預設的 SETTINGS_MAX_FRAME_SIZE 是 16,384，規則是 payload 長度「不得超過」這個值，所以剛好等於是合法的；只要再多 1 byte，接收端就應該以 FRAME_SIZE_ERROR 處理。另外 DATA 還受 flow control 約束：如果 stream 5 或連線層級的剩餘視窗小於 16,384，送出端就不該送這個 frame。stream 5 是奇數，代表是 client 開的 stream；server 在這條 stream 上送 DATA，表示這是某個請求的回應 body。

> [!question]- Q3. 你在 production 看到：HTTP/2 上線後，桌機使用者明顯變快，但地鐵上的手機使用者抱怨「整頁一起卡住」的次數變多了。怎麼解釋，怎麼確認，怎麼處理？
> 最可能的解釋是 TCP 層的 HOL 加上單一連線的擁塞反應。HTTP/1.1 時代，瀏覽器開 6 條連線，一條連線掉包只卡住其中一個資源，其他五條照常；HTTP/2 只有一條連線，任何一個封包遺失都會讓所有 stream 一起等重傳，而且整條連線的擁塞視窗被砍半。桌機網路遺失率低，多工的好處佔上風；地鐵上的手機遺失率高又常換基地台，缺點被放大。
>
> 確認方法：依網路類型或 ASN 拆分 RUM 指標（真實使用者量測），看「卡住」集中在行動網路；在受影響裝置錄 netlog，觀察 HTTP/2 session 上所有 stream 同時停頓，對應到 TCP 重傳。處理方式是啟用 HTTP/3（保留 HTTP/2 fallback），讓支援的瀏覽器改走 QUIC；同時檢查 server 的擁塞控制設定與 RTO 參數（第 11、12 章）。不建議為此退回 HTTP/1.1，因為那會讓大多數使用者變慢。

> [!question]- Q4. 為什麼 HPACK 不直接用 gzip 壓縮 header？HPACK 就完全不會洩漏秘密了嗎？
> 因為通用的自適應壓縮會讓「攻擊者能控制的資料」和「秘密」互相影響壓縮後的長度。CRIME 攻擊就是讓瀏覽器送出含有猜測字串的請求，觀察加密後的長度：猜中秘密的一部分時，壓縮器會找到重複，封包就短一點，一個字元一個字元就能還原 cookie。加密只隱藏內容，不隱藏長度。
>
> HPACK 只以「整個欄位」為單位查表，加上固定的 Huffman 碼表，部分猜中不會讓長度變短，逐字元猜測失效。但它不是零風險：如果攻擊者能精確猜中整個欄位值，例如一個很短、可列舉的 token，表中有沒有這一筆仍會影響長度。所以 RFC 7541 提供 never indexed 表示法，建議對短的、低熵的敏感值使用，並要求中介設備轉送時保持不進表。高熵、夠長的 session cookie 被整個猜中的機率可以忽略，這也是 cookie 應該使用 `secrets` 產生足夠長度的理由之一（第 17 章）。

> [!question]- Q5. 面試題：HTTP/3 為什麼不能沿用 HPACK？QPACK 怎麼解決，代價是什麼？
> HPACK 的 dynamic table 是隱含同步的：每個 header block 都可能修改表格，接收端必須依送出順序處理所有 header block，兩端的表才會一致。HTTP/2 跑在一條 TCP byte stream 上，順序天然保證。QUIC 的不同 stream 之間沒有順序，如果 stream 8 的 header 參照了 stream 4 才插入的表項，而 stream 4 的封包遺失了，接收端要嘛查錯、要嘛等待，等待就把 QUIC 消除的跨 stream HOL 又請回來。
>
> QPACK 把「改表」移到單向、保序的 encoder stream，header block 只「使用」表格，並在開頭用 Required Insert Count 宣告自己依賴幾筆插入。依賴還沒到的 block 才會 blocked，其他 stream 不受影響；decoder stream 回報確認，讓 encoder 知道哪些表項可以放心參照。代價是協定更複雜、多了兩條單向 stream，而且 encoder 必須在壓縮率與阻塞風險之間取捨；為了不阻塞而只參照已確認的表項，第一次出現的 header 就只能用 literal 送。預設 dynamic table 容量是 0，雙方要明確啟用。

> [!question]- Q6. 看 log 找原因：nginx 的 error log 出現 `client sent invalid header`，同時一個自製的 Python 內部工具改用 HTTP/2 函式庫後開始被 GOAWAY，錯誤碼是 PROTOCOL_ERROR。最可能的原因是什麼？
> 最可能是這個工具沿用了 HTTP/1.1 的習慣送 header。HTTP/2 有幾條 HTTP/1.1 沒有的硬規則：header 名稱必須小寫；`Connection`、`Keep-Alive`、`Proxy-Connection`、`Transfer-Encoding`、`Upgrade` 這些連線層級的 header 不得出現；`TE` 只能是 `trailers`；pseudo-header 必須排在一般 header 之前，而且請求不能帶 `:status`。很多 HTTP/1.1 時代的程式碼會手動加 `Connection: keep-alive` 或寫成 `X-Request-Id` 這種大小寫混合的名稱，在 HTTP/1.1 下沒事，在 HTTP/2 下就是協定錯誤。
>
> 確認方法：用 Wireshark 加 key log，或在工具裡打開函式庫的 frame 層 debug log，看被拒前的最後一個 HEADERS 內容；GOAWAY 的 last stream ID 會指出是哪一個請求。修法是移除連線層級 header、名稱一律小寫，並讓函式庫自己產生 pseudo-header。這也說明了為什麼不要自己手寫 HTTP/2 的 header 處理，本章的手寫程式只用於學習。

> [!question]- Q7. 設計取捨：聲聲 Live 的 `www`、`api`、`rt` 三個網域要不要共用一張萬用字元憑證、放在同一組 CDN IP 上，讓瀏覽器可以合併連線？
> 合併的好處是少做交握、共用一條連線的擁塞狀態與優先順序。以 `www` 和它的靜態資源來說，合併幾乎只有好處，最好的作法甚至是直接同源。但 `api` 與 `rt` 的性質不同：API 回應通常不能被 CDN 快取、需要 CORS 與不同的安全設定，`rt` 承載 WebSocket 長連線，可能在不同的 LB（203.0.113.40）上。
>
> 如果用一張涵蓋所有名稱的憑證、又讓 DNS 指到同一組 IP，瀏覽器可能把 API 請求合併到 www 的連線上；只要 edge 不能正確把這個 `:authority` 轉到 API 的 origin，就會出錯。所以要嘛確保 edge 能服務所有合併後的名稱，要嘛讓 edge 對不該出現的名稱回 421，瀏覽器才會開新連線重試。實務上較穩的作法是：`www` 與靜態資源同源；`api` 與 `rt` 用各自的憑證或各自的 IP，讓合併只在明確想要的地方發生。萬用字元憑證還會擴大私鑰外洩時的影響範圍，這是 Rita 會從資安角度提出的另一個反對理由（第 19 章）。

> [!question]- Q8. 概念辨析：HTTP/2 有自己的 flow control，HTTP/3 卻把它拿掉了，這是不是代表 HTTP/3 沒有 flow control？
> 不是，HTTP/3 的 flow control 由 QUIC 提供。QUIC 本身就有 stream 層級（MAX_STREAM_DATA）與連線層級（MAX_DATA）兩層視窗（第 13 章），和 HTTP/2 的 WINDOW_UPDATE 是同一個概念，只是放在傳輸層。HTTP/2 必須自己做，是因為 TCP 只有一條 byte stream、只有一個視窗，沒辦法對單一 stream 喊停；如果只靠 TCP 的視窗，一條慢的 stream 會讓接收端停止讀取整條連線，拖住所有 stream。
>
> 這也是 HTTP/3 設計的一致原則：凡是傳輸層已經提供的功能，HTTP/3 就不再重做，包括多工、flow control、取消（RESET_STREAM、STOP_SENDING）與 PING。實務上的意義是，調整 HTTP/3 的上傳或下載吞吐量時，要找的是 QUIC 的傳輸參數，例如 initial_max_data 與 initial_max_stream_data，而不是 HTTP 層的設定；兩者的計算方式相同，吞吐量上限約等於視窗除以 RTT。

## 延伸閱讀

- RFC 9113〈HTTP/2〉
- RFC 7541〈HPACK: Header Compression for HTTP/2〉
- RFC 9114〈HTTP/3〉
- RFC 9204〈QPACK: Field Compression for HTTP/3〉
- RFC 9218〈Extensible Prioritization Scheme for HTTP〉
- RFC 8297〈An HTTP Status Code for Indicating Hints〉
- RFC 8336〈The ORIGIN HTTP/2 Frame〉
- Ilya Grigorik《High Performance Browser Networking》（O'Reilly）中 HTTP/1.1 與 HTTP/2 的章節
