---
chapter: 24
title: API 風格：REST、gRPC 與 GraphQL
part: 5
---

# 第 24 章　API 風格：REST、gRPC 與 GraphQL

> [!abstract] 本章地圖
> **核心問題**：API 是 client 和 server 之間的契約。REST、gRPC、GraphQL 各自怎麼寫這份契約，失敗、重試、逾時與演進時又各自怎麼處理？
>
> **你會學到**：
> - 用資源與 HTTP method 語意設計 REST API，選對 status code，做好版本化、cursor 分頁與統一的錯誤格式（problem details）
> - 解釋為什麼「逾時後重試」會造成重複扣款，並用 idempotency key 讓非 idempotent 的請求可以安全重試
> - 讀懂 Protocol Buffers 的 varint 與 wire format，說出 gRPC 怎麼把一次函式呼叫放進 HTTP/2 的 HEADERS、DATA 與 trailers
> - 把 deadline 沿著呼叫鏈傳下去，避免使用者離開後後端還在白做工
> - 說清楚 GraphQL 解決什麼問題，以及 N+1 查詢、快取與查詢成本這些代價怎麼處理
> - 設計可靠的 webhook 接收端，並依情境在 REST、gRPC、GraphQL 之間做選擇
>
> **前置知識**：第 20 章（method 語意與 status code）、第 21 章（快取與條件請求）、第 22 章（HTTP/2 的 stream 與 frame）

## 24.1 故事：同一堂課被扣了兩次款

週五晚上八點，聲聲 Live 推出「日語會話十堂優惠包」，美咲老師的課一開賣就湧進大量學生。一位在高雄搭捷運的學生用手機 4G（對外位址 198.51.100.140）按下「付款 NT$12,000」，app 呼叫 `POST /v1/payments` 到 `api.shengsheng.example`（API LB 203.0.113.80），Flask 再去呼叫金流供應商 `pay.example.net`。那天晚上金流供應商很慢，一筆授權要四到六秒；app 的 HTTP client 設定 3 秒逾時，逾時後自動重試一次。

九點不到，客服收到三十七通電話：「我只按了一次，卻被扣了兩次。」小晴打開 log，同一位學生、同一堂課，兩筆 `POST /v1/payments` 相隔 3.1 秒，兩筆都回 201，金流那邊也真的有兩筆成功的授權。小晴很困惑：第一個請求明明「失敗」了，app 才會重試，為什麼它也扣款成功？

```text
 手機 app                         API（Flask）                    pay.example.net
   │── POST /v1/payments ───────────►│                                   │
   │   （第 1 次）                    │── 授權 NT$12,000 ────────────────►│
   │                                  │                                   │ 很慢……
   │ 3 秒到了，放棄並斷線              │                                   │
   │── POST /v1/payments ───────────►│                                   │
   │   （第 2 次，自動重試）           │── 授權 NT$12,000 ────────────────►│
   │                                  │◄─────────── 成功（第 1 筆）─────────│
   │                                  │   回應寫給已經斷掉的連線，沒人收到   │
   │                                  │◄─────────── 成功（第 2 筆）─────────│
   │◄──────────── 201 Created ────────│                                   │
   │   使用者只看到一次成功，帳單上有兩筆                                    │
```

這張時序圖要分兩條時間線讀。左邊的 app 在 3 秒時放棄，對 app 來說第一個請求「失敗」了；但對中間的 API 與右邊的金流，第一個請求一直在正常處理，只是回應寫進一條已經斷掉的連線。app 不知道第一次有沒有成功，只好重試；API 沒辦法分辨第二個請求是「新的購買」還是「同一筆購買的重試」，於是又扣了一次。問題不在任何一行程式寫錯，而在 API 的契約裡少了一條規則：**重試時，server 要怎麼認出這是同一件事。**

同一週還有另外兩件事擺在小晴的待辦清單上。行動 app 團隊抱怨課程頁要打六支 REST API 才湊得出畫面，在 4G 上很慢，提議改用 GraphQL。平台團隊正把推薦服務 `reco`（10.20.4.12:50051）改成 gRPC，因為上個月 `reco` 變慢時，課程頁的 worker 全部卡在等待，整個網站跟著逾時。阿德把三件事寫在白板上：「重複扣款、六支 API、卡住的 worker。看起來是三個問題，其實都在問同一件事：API 這份契約有沒有把『資料長什麼樣』『失敗時怎麼辦』『最多等多久』寫清楚。」

這一章就從這三件事出發，最後在 127.0.0.1 上做出一個不會重複扣款的付款 API、手工編解碼一則 gRPC 訊息，並重現 GraphQL 的 N+1 問題。

## 24.2 API 是契約：每種風格都要回答的問題

**API**（Application Programming Interface，應用程式介面）是兩個程式之間約定好的溝通方式。網路上的 API 和函式庫的 API 最大的差別在於：呼叫的另一端在另一台機器上，可能很慢、可能掛掉、可能是舊版本，而且你常常不知道請求到底有沒有送到。例如呼叫 `pay.example.net` 授權一筆款項，逾時並不代表沒扣款，這件事在本機函式呼叫裡永遠不會發生。

所以一份網路 API 的契約至少要回答五個問題。第一，**怎麼命名操作**：是「對某個資源做標準動作」，還是「呼叫某個函式」？第二，**資料怎麼表示**：JSON、Protocol Buffers，還是由 client 指定要哪些欄位？第三，**失敗怎麼表達**：用 HTTP status code、自訂錯誤碼，還是放在回應內容裡？第四，**重試與逾時**：哪些操作可以安全重試、最多等多久？第五，**怎麼演進**：新版 server 加了欄位、舊版 client 還在用時，會不會壞掉？

所謂 **API 風格**，就是對這五個問題的一組慣例。下表先給一個鳥瞰，後面每一節再展開：

| 風格 | 操作的單位 | 常見資料格式 | 傳輸 | 失敗怎麼表達 | 典型用途 |
|---|---|---|---|---|---|
| REST | 資源＋HTTP method（`GET /v1/lessons/les_004`） | JSON | HTTP/1.1、2、3 | HTTP status code＋錯誤內容 | 對外公開 API、瀏覽器與 app |
| gRPC | 服務的方法（`Reco/GetRecommendations`） | Protocol Buffers | HTTP/2 | `grpc-status` trailer | 內部服務之間、需要 streaming |
| GraphQL | 對 schema 的查詢（client 選欄位） | JSON | 多半是 HTTP POST | 回應裡的 `errors` 陣列 | 前端畫面組合多種資料 |
| Webhook | 事件（`payment.succeeded`） | JSON | HTTP POST（server 打給你） | 你回的 status code 決定是否重送 | 第三方通知、非同步結果 |

這張表的第二欄是三種風格最根本的差異。REST 把世界看成一堆有網址的**資源**（resource，可以被命名、被讀取與修改的東西，例如「一堂課」「一筆付款」），操作只有 HTTP 定義好的幾個 method；gRPC 是 **RPC**（Remote Procedure Call，遠端程序呼叫），把操作看成函式，名字和參數由你定義；GraphQL 則讓 client 寫一段查詢，說清楚要哪些資料、要哪些欄位。webhook 不算同一個層次的風格，但它把呼叫方向反過來，是幾乎每個系統都會遇到的整合方式，所以一起討論。

一個常見的誤解是「REST 是舊的，gRPC 和 GraphQL 是新的，所以比較好」。三者是不同的取捨，同一家公司常常三種都用；選型要看誰是 client、資料形狀變得多快、需不需要瀏覽器直接呼叫與 HTTP 快取，24.10 節會整理成決策流程。

## 24.3 REST：資源、URI 與 method 語意

**REST**（Representational State Transfer，表現層狀態轉移）是 Roy Fielding 在 2000 年的博士論文裡，從 Web 本身的設計歸納出來的一種架構風格。它不是協定，也不是規格，而是一組約束：client 與 server 分離；**無狀態**（stateless，每個請求都帶齊處理所需的資訊，server 不靠「上一個請求」記住你是誰）；回應要標明能不能快取；**統一介面**（uniform interface，所有資源都用同一組 method 操作，用 URI 識別）；允許中間有分層的 proxy 與快取。今天大家口中的「REST API」，多半指的是「用 HTTP method 操作 JSON 資源」的務實版本，不一定滿足論文的全部約束。

REST 的核心單位是資源，資源有網址（URI）和**表現**（representation，資源在某個時刻的一種呈現格式，例如一堂課的 JSON）。client 拿到的永遠是表現，不是資源本身：同一堂課可以有 JSON 表現，也可以有給行事曆用的 iCalendar 表現，靠第 21 章的內容協商選擇。下圖是聲聲 Live API 的資源樹：

```text
 /v1
  ├── /teachers                      集合：老師列表（GET 搜尋）
  │     └── /{teacher_id}            單一老師，例如 /teachers/t_misaki
  │           └── /slots             子集合：這位老師可預約的時段
  ├── /lessons                       集合：課程（GET 列表、POST 建立）
  │     └── /{lesson_id}             單一課程（GET、PATCH、DELETE）
  │           └── /cancellation      「取消」這件事本身也是資源（POST 建立）
  ├── /payments                      集合：付款（POST 建立，必須帶 Idempotency-Key）
  │     └── /{payment_id}
  └── /students/me                   目前登入的學生（由 token 決定是誰）
```

這棵樹有三個設計原則。第一，路徑用名詞的複數表示集合、加上 id 表示單一資源，動作交給 method 表達，所以是 `POST /v1/lessons` 而不是 `POST /v1/createLesson`。第二，巢狀只用來表達明確的從屬關係，而且最多兩層；「某老師的時段」是從屬，用 `/teachers/{id}/slots`，但「某學生上過的課」可以用 `/lessons?student=me` 篩選，避免路徑越長越深。第三，不容易對應到 CRUD 的動作，把它**名詞化**成一個資源：「取消課程」不是 `DELETE`（課程紀錄還要保留），而是建立一筆 `cancellation`，裡面可以帶取消原因與退款金額。有些團隊改用自訂方法的寫法，例如 `POST /v1/lessons/les_004:cancel`，這也是常見慣例，重點是全公司一致。

method 的語意是 REST 最需要記牢的部分，第 20 章介紹過 **safe**（安全：不改變 server 狀態，例如 GET）與 **idempotent**（冪等：做一次和做很多次，server 的最終狀態相同）。下表把它們對應到 API 設計：

| method | safe | idempotent | 在 API 裡的用途 | 成功時常見的回應 |
|---|---|---|---|---|
| GET | 是 | 是 | 讀取資源或集合 | 200，可搭配 ETag 與快取 |
| HEAD | 是 | 是 | 只要 header（例如檢查是否存在） | 200，沒有 body |
| POST | 否 | 否 | 在集合中建立新資源、觸發處理 | 201＋`Location`，或 202（非同步處理） |
| PUT | 否 | 是 | 用完整內容取代資源（不存在就建立） | 200 或 204；新建時 201 |
| PATCH | 否 | 否（依格式而定） | 修改部分欄位 | 200 或 204 |
| DELETE | 否 | 是 | 刪除資源 | 204；重複刪除可回 404 或 204 |

這張表直接決定「哪些請求可以自動重試」。GET、PUT、DELETE 是 idempotent，重送不會造成額外效果，所以 HTTP client 與 proxy 在某些情況下會自動重試它們；POST 不是，重送就可能多建一筆資料，這正是重複扣款的根源。要注意 idempotent 說的是「server 狀態」，不是「回應一樣」：第一次 DELETE 回 204、第二次回 404，狀態都是「已刪除」，依然是 idempotent。PATCH 是否 idempotent 取決於內容：`{"title": "日語會話"}` 這種「設成某值」重做沒有差別，但 JSON Patch 裡的「在陣列尾端加一筆」做兩次就有兩筆。

status code 是 REST 表達結果的主要管道。實務上最常用、也最常被用錯的是 4xx 的細分：

| 情境 | status code | 說明 |
|---|---|---|
| 建立成功 | 201 Created | 附 `Location: /v1/payments/pay_0001`，body 回傳新資源 |
| 已接受、稍後處理 | 202 Accepted | 例如轉檔、匯出；附一個可查詢進度的資源網址 |
| 請求格式錯誤 | 400 Bad Request | JSON 解析失敗、缺少必要 header |
| 沒有驗證身分 | 401 Unauthorized | 沒帶 token 或 token 過期（第 27 章） |
| 驗證了但沒有權限 | 403 Forbidden | 學生想看別人的付款紀錄 |
| 資源不存在 | 404 Not Found | 也常用來隱藏「存在但你無權知道」的資源 |
| 狀態衝突 | 409 Conflict | 時段已被別人預約、同一個 idempotency key 正在處理 |
| 前提不成立 | 412 Precondition Failed | `If-Match` 的 ETag 不符，別人先改過了（第 21 章） |
| 內容語意錯誤 | 422 Unprocessable Content | JSON 格式正確，但金額是負數 |
| 太多請求 | 429 Too Many Requests | 搭配 `Retry-After` 告訴 client 多久後再試 |
| 暫時無法服務 | 503 Service Unavailable | 維護或過載，也可搭配 `Retry-After` |

選 status code 的原則是：**讓 client 不用讀內容就能決定下一步**。4xx 表示「你的請求有問題，原封不動重送也沒用」，5xx 與 429 表示「可能是暫時的，稍後可以重試」。把所有錯誤都回 200、再在 JSON 裡放 `"success": false`，會讓 proxy、監控、client 函式庫都誤以為一切正常：告警看不到錯誤率，CDN 甚至可能把錯誤回應快取起來。

> [!warning] 常見誤解
> 「REST 一定要用 HATEOAS 才算 REST。」Fielding 的論文確實要求 **HATEOAS**（Hypermedia as the Engine of Application State：client 靠回應裡的連結發現下一步），但絕大多數 JSON API 只做到「資源＋method＋status code」，即 Richardson 成熟度模型的第二級。重要的是團隊一致；分頁時回傳 `next` 連結就是實用的超媒體做法。

## 24.4 讓 REST API 能長久使用：版本化、分頁與錯誤格式

資源與 method 決定了 API 的骨架，但讓一支 API 在上線三年後依然好用的，是版本化、分頁、錯誤格式這些細節。這一節逐一說明聲聲 Live 採用的做法，也會在 24.11 節的動手做裡實作。

### 版本化：什麼改變會弄壞 client

**破壞性變更**（breaking change）是指舊版 client 不改程式就會出錯的變更：刪除或改名欄位、改變欄位型別（數字變字串）、新增必要參數、改變既有欄位的意義（`amount` 從「元」改成「分」）、改變錯誤碼。相對地，新增一個可選欄位、新增一個 endpoint 通常不是破壞性變更，前提是 client 遵守**寬容讀取**（tolerant reader）原則：讀 JSON 時忽略不認得的欄位，不要把回應整包做嚴格驗證。

最好的版本策略是盡量不需要新版本：只做加法，欄位一旦公開就不改意義。真的需要破壞性變更時，常見的做法有四種：

| 做法 | 例子 | 優點 | 缺點 |
|---|---|---|---|
| 路徑版本 | `/v1/lessons`、`/v2/lessons` | 一眼看出版本，容易路由與快取 | 大版本切換成本高，常變成整套重寫 |
| header 版本 | `Accept: application/vnd.shengsheng.v2+json` | URI 保持穩定，符合內容協商 | 不易在瀏覽器測試，快取要設 `Vary` |
| 日期版本 | `Api-Version: 2026-09-01` | 每個帳號可以釘住某個日期，細粒度演進 | server 要維護版本轉換層，實作複雜 |
| query 參數 | `/lessons?version=2` | 簡單 | 容易被忽略、和其他參數混在一起 |

聲聲 Live 選擇路徑版本 `/v1`，原因很務實：app 的版本更新要靠使用者下載，舊版 app 會在外面存活很久，路徑上的版本號讓 nginx 與 LB 能直接把 `/v1` 和 `/v2` 導到不同的程式。不論哪種做法，淘汰舊版本都要提前公告，並在回應裡加上即將停用的提示，讓 client 的 log 能看得到；監控各版本的流量，確定舊版流量歸零才真正關閉。

### 分頁：offset 與 cursor

列表 API 一定要分頁，否則某天資料量長大，一個請求就會拖垮資料庫和 client 的記憶體。最直覺的是 **offset 分頁**：`?offset=20&limit=10` 表示「跳過前 20 筆，給我 10 筆」，對應 SQL 的 `LIMIT 10 OFFSET 20`。它有兩個問題。第一，資料庫還是要掃過被跳過的那 20 筆，翻到第一萬頁就要掃十萬筆，越後面越慢。第二，翻頁途中如果有資料插入或刪除，頁與頁之間會重複或遺漏：

```text
 時刻 1：client 讀第 1 頁（offset=0, limit=3）
   排序後的資料： [A] [B] [C] │ D  E  F  G
                  └─ 第 1 頁 ┘

 時刻 2：有人新增一筆排在最前面的 N
   排序後的資料：  N  A  B │[C] [D] [E]│ F  G
                           └ 第 2 頁（offset=3）┘
   → C 出現了兩次；如果是刪除一筆，則會有一筆被跳過

 cursor 分頁：第 1 頁回傳「最後一筆是 C」的 cursor
   第 2 頁：WHERE (start_at, id) > (C.start_at, C.id) LIMIT 3  →  D E F
   → 不論前面插入或刪除多少，都從 C 之後接著讀
```

這張圖說明了 offset 的本質：它記住的是「位置」，而位置會隨資料變動而移動。**cursor 分頁**（也叫 keyset 分頁）改為記住「上一頁最後一筆的排序鍵」，下一頁從那個鍵之後開始讀。因為條件是 `(start_at, id) > (?, ?)`，資料庫可以直接用索引跳到起點，第一頁和第一萬頁一樣快；插入在前面的新資料不會讓後面的頁錯位。排序鍵要加上唯一的 id 當最後一欄，否則兩堂課開始時間相同時，順序不確定，cursor 就會漏資料。

cursor 對 client 應該是**不透明**的（opaque）：client 只能原封不動地傳回來，不該解析或自己拼。實作上把排序鍵編碼成 base64url 字串，再加上 HMAC 簽章（第 17 章），server 收到時先驗章；這樣日後要改排序鍵或資料庫，cursor 格式可以自由改變，client 也沒辦法塞入奇怪的值。cursor 分頁的代價是不能「直接跳到第 37 頁」，也很難提供總筆數；對無限捲動與 API 同步這類用途，這幾乎不是問題，需要頁碼的後台報表才考慮 offset。

回應格式常見兩種：在 body 裡放 `next_cursor`，或用 `Link` header（Web Linking 規格定義的 `rel="next"`）指向下一頁的網址。聲聲 Live 兩者都提供，並且一律限制 `limit` 的上限（例如 50），避免有人一次要一百萬筆。

### 錯誤格式：problem details

錯誤回應如果每支 API 長得不一樣，client 就要為每支 API 寫不同的錯誤處理。**Problem Details**（RFC 9457，取代較早的 RFC 7807）定義了一種統一的 JSON 錯誤格式，media type 是 `application/problem+json`：

```text
 HTTP/1.1 409 Conflict
 Content-Type: application/problem+json
 x-request-id: 7f3c9a2e

 {
   "type":     "https://api.shengsheng.example/problems/slot-taken",  ← 錯誤種類的識別（URI）
   "title":    "Slot already booked",                               ← 給人看的簡短標題，同類錯誤固定
   "status":   409,                                                 ← 與 HTTP status 相同
   "detail":   "美咲老師 10/03 13:00 的時段已被預約",                  ← 這次發生的具體說明
   "instance": "/v1/lessons",                                       ← 發生在哪個請求或資源
   "alternatives": ["2026-10-03T14:00", "2026-10-03T15:00"]         ← 自訂的擴充欄位
 }
```

這個格式的重點是分工。`type` 是給程式判斷用的穩定識別：client 依 `type` 決定要顯示「換一個時段」還是「重新登入」，不要去比對 `detail` 的文字，因為那段文字隨時可能被改寫或翻譯。`title` 對同一個 `type` 固定不變，`detail` 則描述這一次的情況。規格允許加入自訂欄位，例如表單驗證錯誤常加一個 `errors` 陣列，逐欄列出哪個欄位錯在哪裡。`type` 若省略，預設值是 `about:blank`，表示「除了 status code 以外沒有更多語意」。

錯誤回應有兩件事不能做。第一，不要把 stack trace、SQL 或內部主機名稱放進 `detail`，那等於把系統內部結構交給攻擊者；內部細節寫在 log，回應裡只放 `x-request-id`，讓客服與工程師能用同一個 id 串起 nginx 與 Flask 的 log。第二，不要讓錯誤格式依框架而不同：Flask 的預設 404 是 HTML 頁面，API 的每一條錯誤路徑（包括框架自己產生的 404、405、413）都要轉成 problem details。

### 限流與「請稍後再試」

對外 API 一定會限流（rate limiting），被限流的 client 應收到 429 並附上 `Retry-After`（秒數或日期），這是 client 決定重試時機的最佳依據；503 也可以帶它。下一節會看到，「可以重試」只是第一步，真正難的是「重試之後不要做兩次」。

> [!note] 2026 現況
> 截至 2026 年 10 月，與 API 相關的幾個 HTTP header 處於不同的標準化階段，依 2026 年 10 月的了解整理如下，引用前請再確認。`Sunset` header（RFC 8594）用來公告某個資源或版本的停用時間；`Deprecation` header 已在 2025 年發布為 RFC（RFC 9745），用來標示「這個 endpoint 已不建議使用」。描述剩餘配額的 `RateLimit` 系列 header 仍是 IETF httpapi 工作小組的草案，各家 API 多半使用自訂的 `X-RateLimit-*` header。`Idempotency-Key` header 同樣有 httpapi 工作小組的草案，業界多家支付 API 早已採用相同名稱與類似語意，但細節（例如重用時回哪個 status code）各家不同。

## 24.5 idempotency key：讓重試變得安全

回到故事。app 在 3 秒時放棄，它面對的是分散式系統最根本的不確定：**逾時不代表失敗**。從 client 的角度，沒收到回應有三種可能，而且無法區分：請求在路上遺失了，server 根本沒收到；server 收到並處理完了，但回應在路上遺失或連線斷了；server 還在處理中。只有第一種情況重試是安全的。對 GET 來說三種都無所謂，因為重做沒有副作用；對扣款來說，後兩種重試就會扣第二次。

解法是讓 client 為**每一個操作**（不是每一次嘗試）產生一個獨一無二的 **idempotency key**，通常是隨機 UUID，放在 `Idempotency-Key` header。server 第一次看到這把 key 時正常處理，並把結果和 key 一起存起來；之後再看到同一把 key，就不再處理，直接回傳存好的結果。這樣，非 idempotent 的 POST 在「同一把 key」的範圍內就變成 idempotent 了：

```text
 手機 app                              API                         idempotency 儲存
   │ key = 4f9c2a1e…（按下付款時產生一次） │                                  │
   │── POST /v1/payments ─────────────►│── INSERT key, 狀態=處理中 ─────────►│ 成功：第一次見到
   │   Idempotency-Key: 4f9c2a1e…      │── 呼叫金流授權（很慢）…              │
   │ 3 秒逾時                           │                                  │
   │── 重試，同一把 key ───────────────►│── INSERT key ─────────────────────►│ 失敗：已存在，處理中
   │◄── 409 request-in-progress ───────│                                  │
   │   （等一下再試）                     │── 授權成功，存結果 201 ──────────────►│ 狀態=完成，存回應
   │── 再重試，同一把 key ──────────────►│── 查 key ─────────────────────────►│ 完成：取出存好的回應
   │◄── 201（Idempotent-Replayed）─────│                                  │
   │   只扣一次款，app 拿到正確的付款 id   │                                  │
```

這張圖有三個關鍵。第一，key 在使用者按下付款時就產生並保存在 app 裡，三次嘗試用的是同一把；如果每次重試都產生新 key，這個機制就完全失效。第二，「檢查 key 是否存在」和「佔住 key」必須是同一個原子動作，例如資料庫的 unique constraint 或 Redis 的 `SET key value NX`；如果先查詢、再寫入，兩個幾乎同時到達的重試會都以為自己是第一個。第三，第二次嘗試到達時第一次還沒完成，server 回 409，告訴 client「同一件事正在處理，稍後再來」，而不是再做一次或讓請求一直等。

一把 key 在 server 端的生命週期可以畫成狀態機：

```text
                    第一次收到 key（原子地寫入）
     （不存在）──────────────────────────────► 處理中 ──────► 回 409 給同時到達的重試
         ▲                                     │
         │ 尚未產生副作用就失敗                    │ 業務處理結束（成功或確定的失敗）
         │（例如參數驗證失敗、金流明確拒絕前）       ▼
         └───────────── 刪除 key ─────────── 已完成：存下 status code 與回應 body
                                               │
                                               │ 之後相同 key＋相同內容 → 直接回存好的回應
                                               │ 之後相同 key＋不同內容 → 422，拒絕
                                               ▼
                                         保存期限到（例如 24 小時）→ 清除
```

狀態機裡最容易做錯的是失敗的處理。如果失敗發生在任何副作用之前（例如請求內容驗證失敗），可以把 key 刪掉，讓 client 修正後用同一把 key 再試。如果失敗發生在副作用之後、或者不確定副作用有沒有發生（例如呼叫金流時逾時），就不能刪 key，要把狀態留在「需要人工或背景程序確認」，否則重試又會造成重複。另一個要點是**請求指紋**（fingerprint）：server 存下請求內容的雜湊，同一把 key 卻帶著不同的金額，代表 client 有 bug，必須拒絕，不能回傳舊結果假裝成功。

在聲聲 Live 的實作中，還有四個細節。第一，key 的範圍要綁定使用者或 API key，`(student_id, key)` 才是唯一值，避免不同使用者的 key 碰撞，也避免有人拿別人的 key 讀到別人的付款結果。第二，如果下游金流也支援 idempotency key，就把一把衍生的 key 傳下去，讓整條鏈都能安全重試，否則 API 這一層的保護會在呼叫金流時破功。第三，保存期限要長於 client 最長的重試時間，常見是 24 小時。第四，回應裡加上 `Idempotent-Replayed: true` 這類 header，讓 client 與除錯人員知道這是重播的結果。

client 端也有對應的責任。重試只針對「可能是暫時的」錯誤：連線失敗、逾時、429、409（處理中）與 5xx；4xx 的其他錯誤重試也不會成功。重試間隔要用**指數退避加隨機抖動**（exponential backoff with jitter：每次等待時間加倍，並加上隨機值），例如 0.5 秒、1 秒、2 秒再各自隨機打散，避免上千支手機在同一瞬間一起重試，把剛恢復的 server 再次打垮；有 `Retry-After` 時優先遵守它。

> [!warning] 常見誤解
> 「用『同一位學生、同一堂課、同樣金額、五分鐘內』判斷重複就好，不需要 key。」這種**內容去重**會誤殺合法的操作：學生可能真的想替兩個孩子各買一份同樣的課程。它也無法處理重試落在五分鐘之外的情況。idempotency key 的本質是讓 client 明確宣告「這是同一個操作」，只有 client 知道這件事，server 不該猜。

## 24.6 gRPC 與 Protocol Buffers：把函式呼叫搬到網路上

REST 很適合「對外、給很多不同 client 使用」的 API，但在服務之間，它有幾個不便之處。每個團隊要自己寫 HTTP client、自己處理 JSON 的欄位名稱與型別；JSON 是文字，數字和欄位名稱一再重複傳送；沒有標準方式表達「server 一邊算一邊回傳結果」。**gRPC** 是 Google 開源的 RPC 框架，用 **Protocol Buffers**（簡稱 protobuf，一種與語言無關的資料描述與二進位編碼格式）定義介面，建在 HTTP/2 之上，從同一份定義自動產生各種語言的 client 與 server 程式碼。

### 從 .proto 檔開始

gRPC 的契約寫在 `.proto` 檔裡，這種描述介面的語言叫 **IDL**（Interface Definition Language，介面定義語言）。下面是聲聲 Live 推薦服務的定義：

```protobuf
syntax = "proto3";
package shengsheng.reco.v1;

service Reco {
  // unary：一個請求、一個回應
  rpc GetRecommendations(RecoRequest) returns (RecoResponse);
  // server streaming：直播講座進行中，持續推送「現在有多少人在看」
  rpc WatchAudience(WatchRequest) returns (stream AudienceUpdate);
}

message RecoRequest {
  string student_id = 1;          // 等號後面是欄位編號，不是預設值
  int32 limit = 2;
  repeated string languages = 3;  // repeated = 陣列
  reserved 4;                     // 曾經用過、已刪除的編號，永遠不能再用
}

message RecoResponse {
  repeated Lesson lessons = 1;
}

message Lesson {
  string id = 1;
  string title = 2;
  string teacher_name = 3;
}

message WatchRequest { string lecture_id = 1; }
message AudienceUpdate { int32 viewers = 1; int64 at_unix_ms = 2; }
```

這份檔案就是契約本身。`service` 區塊定義方法，`message` 定義資料結構。最重要的是每個欄位後面的**欄位編號**（field number）：線上傳送的是編號，不是欄位名稱，所以欄位可以改名而不影響相容性，但編號一旦用過就不能改、也不能挪作其他用途；刪除欄位時要用 `reserved` 把編號保留起來，否則日後有人重用編號 4，舊版 client 送來的舊資料就會被解讀成另一個意思。用 `protoc` 編譯器搭配各語言的外掛，就能產生型別完整的 client（stub）與 server 骨架，兩邊不再需要手寫序列化程式。

### wire format：訊息在線上長什麼樣

protobuf 的編碼由一連串「欄位」組成，每個欄位以一個 **tag** 開頭，tag 同時包含欄位編號與 **wire type**（線上型別，告訴解碼器接下來的值怎麼讀、有多長）。tag 本身用 varint 編碼：

```text
 tag 的計算：  tag = (field_number << 3) | wire_type

     field_number（剩下的 bit）              wire_type（最低 3 bit）
   ┌───────────────────────────────┬───────┐
   │  0 0 0 0 1                    │ 0 1 0 │  = (1 << 3) | 2 = 0x0a
   └───────────────────────────────┴───────┘
     field 1                         2 = LEN（後面接長度＋內容）

 varint：每個 byte 用低 7 bit 放資料，最高 bit 表示「後面還有」
   150 = 1001 0110 (二進位)
   切成 7 bit 一組，低位在前：  001 0110 │ 000 0001
   加上延續位元：            1 0010110 │ 0 0000001
                                0x96        0x01        → 96 01
```

圖的上半部是 tag：欄位編號左移 3 位，空出的最低 3 bit 放 wire type。所以欄位 1 到 15 的 tag 只要 1 byte，16 到 2047 需要 2 bytes，這就是為什麼常用的欄位要分配小編號。下半部是 **varint**（variable-length integer，可變長度整數）：把整數切成 7 bit 一組，從低位開始，每組放進一個 byte，除了最後一個 byte 以外，最高 bit 都設成 1 表示「後面還有」。150 需要 8 bit，所以佔 2 bytes；小於 128 的數字只要 1 byte。下表列出常用的 wire type：

| wire type | 名稱 | 值怎麼讀 | 用在哪些 protobuf 型別 |
|---|---|---|---|
| 0 | VARINT | 讀到最高 bit 為 0 的 byte 為止 | int32、int64、uint32、bool、enum、sint32（zigzag） |
| 1 | I64 | 固定 8 bytes，little-endian | fixed64、sfixed64、double |
| 2 | LEN | 先讀一個 varint 長度，再讀那麼多 bytes | string、bytes、巢狀 message、packed repeated |
| 5 | I32 | 固定 4 bytes，little-endian | fixed32、sfixed32、float |

wire type 3 和 4 是已經淘汰的 group 編碼，現在不會用到。這張表透露了 protobuf 能向前相容的祕密：**解碼器不需要 schema 也能切開每個欄位**，因為 wire type 已經說明了值有多長。舊版 server 收到新版 client 多帶的欄位 5，看 wire type 就知道要跳過幾個 bytes，繼續讀下一個欄位，不會出錯。24.11 節的實驗二會親手驗證這件事。

protobuf 有幾個設計值得知道。proto3 的純量欄位若等於預設值（0、空字串、false）就不會被送出，所以接收方無法分辨「設成 0」和「沒設」；需要區分時要宣告 `optional`，或用包裝型別。負數用 int32 編碼會變成 10 bytes，因為它被當成 64 bit 補數；經常是負數的欄位（例如時區偏移 −60 分鐘）應該用 sint32，它先做 **zigzag 編碼**（把 0、−1、1、−2 對應成 0、1、2、3），讓小的負數也只佔 1 byte。protobuf 的二進位格式省空間、解析快，代價是人眼讀不懂，除錯時要靠 `grpcurl` 或解碼工具。

### gRPC 怎麼放進 HTTP/2

gRPC 沒有發明新的傳輸層，而是把每次呼叫對應到一條 HTTP/2 stream（第 22 章）。一次 unary 呼叫在線上長這樣：

```text
 classroom（client）                                       reco（server）
   │── HEADERS ───────────────────────────────────────────────►│
   │     :method POST                                          │
   │     :path /shengsheng.reco.v1.Reco/GetRecommendations     │  ← 服務與方法名稱
   │     content-type: application/grpc                        │
   │     te: trailers                                          │
   │     grpc-timeout: 300m                                    │  ← 還剩 300 毫秒
   │── DATA  [00][00 00 00 14][20 bytes protobuf] ────────────►│  ← 5 bytes 前綴＋訊息
   │          （END_STREAM：請求送完了）                          │
   │◄─────────────────────────────────────────────── HEADERS ──│
   │                    :status 200、content-type: application/grpc
   │◄────────────────────────── DATA [00][長度][RecoResponse] ──│
   │◄─────────────────────────────── HEADERS（trailers）─────────│
   │                    grpc-status: 0                          │  ← 真正的結果在這裡
   │                    grpc-message: （錯誤時的說明）            │
   │                    （END_STREAM）                           │
```

從上往下讀。請求是一個 POST，`:path` 固定是 `/套件.服務/方法`，所以 L7 proxy 可以依方法名稱路由與統計。每則 protobuf 訊息放進 DATA frame 時，前面加 5 bytes：1 byte 的壓縮旗標，加上 4 bytes big-endian 的訊息長度，這叫 **length-prefixed message**；因為有長度，同一條 stream 上可以連續放很多則訊息，這是 streaming 的基礎。回應的 HTTP status 幾乎總是 200，**真正的呼叫結果放在 trailers**（在 body 之後才送的 header，第 22 章）的 `grpc-status` 裡。這個設計讓 server 可以在串流途中才決定成功或失敗，但也帶來一個限制：瀏覽器的 fetch API 無法完整控制 HTTP/2 frame 與 trailers，所以瀏覽器不能直接呼叫 gRPC，要透過 gRPC-Web 這類協定，由 proxy（例如 Envoy）轉換。

`grpc-status` 是一組固定的狀態碼，和 HTTP status code 是兩套系統。下表列出最常見的幾個，以及它們大致對應的 HTTP 語意：

| grpc-status | 名稱 | 意思 | 大致對應 HTTP | 可以重試嗎 |
|---|---|---|---|---|
| 0 | OK | 成功 | 200 | 不需要 |
| 3 | INVALID_ARGUMENT | 參數錯誤 | 400 | 否 |
| 4 | DEADLINE_EXCEEDED | 超過 deadline | 504 | 視情況，要檢查剩餘時間 |
| 5 | NOT_FOUND | 找不到 | 404 | 否 |
| 7 | PERMISSION_DENIED | 沒有權限 | 403 | 否 |
| 8 | RESOURCE_EXHAUSTED | 配額用完、被限流 | 429 | 退避後可以 |
| 13 | INTERNAL | server 內部錯誤 | 500 | 通常否 |
| 14 | UNAVAILABLE | 暫時無法服務（連線失敗、重啟中） | 503 | 可以，這是最典型的可重試錯誤 |
| 16 | UNAUTHENTICATED | 沒有有效的身分 | 401 | 重新取得憑證後 |

把 gRPC 錯誤轉成對外的 REST 錯誤時，用這張表對照，再包成 problem details。特別注意 UNAVAILABLE 與 DEADLINE_EXCEEDED 的差別：前者通常表示請求沒被處理，重試相對安全；後者表示「時間到了，但不確定 server 做到哪裡」，對非 idempotent 的方法同樣需要 idempotency key 的保護。

### 四種呼叫模式

因為一條 stream 可以來回放很多則訊息，gRPC 支援四種模式：**unary**（一問一答，例如 `GetRecommendations`）；**server streaming**（一個請求，server 持續推送，例如直播講座的在線人數 `WatchAudience`）；**client streaming**（client 持續上傳，最後 server 回一個結果，例如分段上傳一段口說錄音，最後回傳發音評分）；**bidirectional streaming**（雙向同時傳送，例如即時發音矯正：一邊上傳聲音一邊收到逐句回饋）。streaming 讓 gRPC 能處理 REST 難以表達的長時間互動，但在大規模下也要處理 flow control、重連與斷點續傳。

gRPC 的長連線也影響負載分散。HTTP/2 會在一條 TCP 連線上多工所有呼叫，如果 LB 只在 L4 分配「連線」，一個 client 的所有請求會永遠落在同一台 server 上，新開的 server 分不到流量。所以 gRPC 需要 L7 的 LB（依每個請求分配），或者 client 端自己做負載分散，第 25 章會詳細說明。用 Python 的 grpcio 套件，server 與 client 大致長這樣：

```python
# not-runnable：需要 grpcio，以及由 reco.proto 產生的 reco_pb2、reco_pb2_grpc
from concurrent import futures
import grpc
import reco_pb2, reco_pb2_grpc

class RecoService(reco_pb2_grpc.RecoServicer):
    def GetRecommendations(self, request, context):
        if request.limit <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "limit must be positive")
        # context.time_remaining() 是這個呼叫還剩多少秒，往下游呼叫時要傳下去
        lessons = find_lessons(request.student_id, request.limit,
                               timeout=context.time_remaining())
        return reco_pb2.RecoResponse(lessons=lessons)

server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
reco_pb2_grpc.add_RecoServicer_to_server(RecoService(), server)
server.add_insecure_port("127.0.0.1:50051")   # production 要用 TLS 或 mTLS（第 30 章）
server.start()

# client 端：timeout 會變成 grpc-timeout header
with grpc.insecure_channel("127.0.0.1:50051") as channel:
    stub = reco_pb2_grpc.RecoStub(channel)
    try:
        reply = stub.GetRecommendations(
            reco_pb2.RecoRequest(student_id="stu_1024", limit=5, languages=["ja"]),
            timeout=0.3)
    except grpc.RpcError as err:
        print(err.code(), err.details())       # 例如 StatusCode.DEADLINE_EXCEEDED
```

這段程式的重點不是語法，而是兩個參數：client 的 `timeout=0.3` 會被 grpcio 轉成 `grpc-timeout` header；server 用 `context.time_remaining()` 取得剩餘時間，再傳給下游。下一節就說明為什麼這件事這麼重要。

## 24.7 deadline：讓「最多等多久」跟著請求走

故事裡課程頁卡住的原因，是 `reco` 變慢時，呼叫它的 classroom 服務沒有設定上限，worker 一個個卡在等待；更糟的是，就算 app 已經放棄，後端的整條呼叫鏈還在繼續工作，消耗 CPU 與連線，讓過載雪上加霜。

先分清兩個詞。**timeout** 是「這一次呼叫最多等多久」，每個呼叫者各自設定；**deadline** 是「整個操作必須在哪個時刻之前完成」，是一個屬於請求本身的期限。單獨設定 timeout 的問題在於每一層都各自計時：app 等 800 毫秒、classroom 等 reco 1 秒、reco 等 profile 2 秒，下游的 timeout 比上游長，上游放棄之後下游還在跑，白做的工沒有人收。deadline 的做法是只在入口決定一次期限，之後每一層往下呼叫時，都把「還剩多少時間」傳下去：

```text
 手機 app 給 800 ms
   │
   ▼  t=0      classroom 收到：deadline = 現在 + 800 ms
   │           自己處理 40 ms
   ▼  t=40     呼叫 reco：grpc-timeout = 800 − 40 − 5（保留回程）= 755m
   │           reco 處理 30 ms
   ▼  t=70     呼叫 profile：grpc-timeout = 755 − 30 − 5 = 720m
   │           profile 今晚過載，需要 1200 ms
   ▼  t≈790    profile 發現 deadline 已到 → 停止工作，回 DEADLINE_EXCEEDED
   │           reco、classroom 依序收到錯誤，釋放 worker，回應 app
   ▼
   app 在 800 ms 左右得到明確的失敗，可以顯示「推薦暫時無法載入」
```

這張圖的關鍵是 `grpc-timeout` 傳的是**相對時間**（還剩多少），而不是絕對時刻。不同機器的時鐘可能差了幾百毫秒，如果傳「必須在 20:00:01.800 前完成」，時鐘快的機器會提早放棄、時鐘慢的會多做；傳相對時間，每一層收到後用自己的時鐘換算成本機的 deadline，就不受時鐘差異影響，誤差只有網路傳輸的那一小段。每一層往下傳時還要扣掉一點餘裕，留給回程與序列化。

下面這段程式用模擬時鐘比較「不傳遞」與「傳遞」deadline：

```python
class Clock:                      # 模擬時鐘：不真的 sleep
    now = 0

class DeadlineExceeded(Exception):
    pass

# 每個服務：自己要做多少毫秒的工作，做完再呼叫下一個
CHAIN = [("classroom", 40), ("reco", 30), ("profile", 1200)]   # profile 今晚過載，要 1.2 秒

def serve(level, timeout_ms, log):
    """timeout_ms 就像 grpc-timeout header：線上傳的是「還剩多久」。"""
    name, cost = CHAIN[level]
    deadline = Clock.now + timeout_ms          # 收到請求時，換算成本機的絕對時刻
    done = 0
    while done < cost:                         # 以 50 ms 為單位工作，每段之間檢查 deadline
        if Clock.now >= deadline:
            log.append(f"{Clock.now:5d} ms  {name:9s} 放棄：DEADLINE_EXCEEDED（已做 {done} ms）")
            raise DeadlineExceeded
        step = min(50, cost - done)
        Clock.now += step; done += step
    log.append(f"{Clock.now:5d} ms  {name:9s} 完成自己的 {cost} ms")
    if level + 1 < len(CHAIN):
        remaining = deadline - Clock.now - 5   # 留 5 ms 給回程與序列化
        serve(level + 1, remaining, log)

for propagate in (False, True):
    Clock.now, log = 0, []
    timeout = 800 if propagate else float("inf")   # 不傳遞 = 下游以為有無限時間
    try:
        serve(0, timeout, log)
        outcome = "後端做完了（但 client 早已逾時，結果沒人收）"
    except DeadlineExceeded:
        outcome = "快速失敗，資源被釋放"
    print("== 傳遞 deadline ==" if propagate else "== 不傳遞 deadline ==")
    print("\n".join(log))
    print(f"手機 app 在 800 ms 放棄；最後一個服務停在 {Clock.now} ms → {outcome}")
    if propagate:
        assert Clock.now <= 800 + 50
    else:
        assert Clock.now == 1270
```

執行結果：

```text
== 不傳遞 deadline ==
   40 ms  classroom 完成自己的 40 ms
   70 ms  reco      完成自己的 30 ms
 1270 ms  profile   完成自己的 1200 ms
手機 app 在 800 ms 放棄；最後一個服務停在 1270 ms → 後端做完了（但 client 早已逾時，結果沒人收）
== 傳遞 deadline ==
   40 ms  classroom 完成自己的 40 ms
   70 ms  reco      完成自己的 30 ms
  820 ms  profile   放棄：DEADLINE_EXCEEDED（已做 750 ms）
手機 app 在 800 ms 放棄；最後一個服務停在 820 ms → 快速失敗，資源被釋放
```

不傳遞 deadline 時，profile 完整做了 1200 毫秒，整條鏈在 1270 毫秒才結束，比使用者放棄的時間晚了將近 0.5 秒；這段時間的 CPU、資料庫連線、worker 全都浪費了。過載時這種浪費會自我強化：越慢，被放棄的請求越多，白做的工也越多。傳遞 deadline 後，profile 在 820 毫秒時發現期限已過，立刻放棄；因為以 50 毫秒為單位檢查，最後停下的時間比 deadline 稍晚，這說明 deadline 要靠程式在適當的位置**主動檢查**，不會憑空中斷正在執行的運算。

deadline 還有幾個配套。第一是**取消傳遞**：client 放棄時，gRPC 會對那條 HTTP/2 stream 送出 RST_STREAM（第 22 章），server 端的 context 隨之變成已取消，程式應該檢查並停止工作，而且繼續把取消傳給下游。第二，重試也要在 deadline 內進行：剩下 50 毫秒時，重試一個平常要 100 毫秒的呼叫毫無意義，應該直接失敗。第三，每一層都重試會造成**重試放大**：三層各重試 3 次，最底層在最壞情況會收到 27 倍的請求；常見對策是只在最靠近失敗的那一層重試，並限制重試流量的比例（retry budget，例如重試不超過正常請求的 10%）。

不同語言的 gRPC 函式庫在傳遞上的便利程度不同。在 Go 裡，deadline 跟著 `context` 走，把收到的 ctx 傳給下游呼叫就自動傳遞；在 Python 的 grpcio 裡，要像上一節的程式那樣，自己把 `context.time_remaining()` 傳給下一個呼叫。REST 沒有標準的 deadline header，聲聲 Live 內部約定用 `x-deadline-ms`（剩餘毫秒數）在 Flask 服務之間傳遞，語意和 `grpc-timeout` 相同，並在 nginx 與 gunicorn 的設定中保證各層的逾時由外到內遞減。

> [!tip] 設定 deadline 的起點
> 從使用者能忍受的時間往回推：課程頁的 API 預算是 800 毫秒，扣掉網路與 nginx 的 50 毫秒，再依各下游的 p99 延遲分配。下游的 p99 已經超過分到的預算時，不是把 deadline 調長，而是重新設計（快取、預先計算、降級顯示）。

## 24.8 GraphQL：讓 client 決定要什麼

行動 app 團隊的抱怨是典型的 REST 痛點。課程頁要顯示課程資訊、老師、評價摘要、可預約時段、推薦課程與學生的優惠券，分散在六個資源上：client 要打六支 API，這叫 **under-fetching**（一次拿不夠）；而 `GET /v1/teachers/t_misaki` 回傳了三十個欄位，畫面只用三個，這叫 **over-fetching**（拿了太多）。在 4G、RTT 180 毫秒的環境下，六個請求即使用 HTTP/2 並行，仍然比一個請求慢，而且每個畫面改版都要等後端調整 API。

**GraphQL** 是 Facebook 在 2015 年公開的查詢語言與執行規格。server 公開一份帶型別的 **schema**（描述有哪些型別、每個型別有哪些欄位、欄位之間怎麼關聯），client 寫一段查詢，精確說明要哪些欄位，server 依查詢的形狀回傳 JSON。schema 用 SDL（Schema Definition Language）描述：

```text
 type Query {                              查詢（client 送來的）
   lesson(id: ID!): Lesson                 {
   lessons(first: Int = 10): [Lesson!]!      lesson(id: "les_004") {
 }                                             title
                                               teacher { name rating }
 type Lesson {                                 slots(first: 3) { startAt }
   id: ID!                                   }
   title: String!                          }
   teacher: Teacher!
   slots(first: Int): [Slot!]!             回應（形狀與查詢一一對應）
 }                                         { "data": { "lesson": {
                                               "title": "日語會話",
 type Teacher { name: String!                  "teacher": {"name": "美咲", "rating": 4.9},
                rating: Float }                "slots": [{"startAt": "2026-10-03T13:00"}, …]
 type Slot { startAt: String! }            } } }
```

左邊是 schema，右邊是一次查詢與它的回應，對照著讀就能看出 GraphQL 的核心特性：回應的形狀和查詢的形狀完全相同，client 沒寫的欄位不會出現，一次請求就能沿著關聯取到課程、老師與時段。型別後面的 `!` 表示不可為 null。schema 本身可以被查詢（**introspection**），所以工具能自動補完、驗證查詢，前端也能從 schema 產生型別。

在 server 端，每個欄位對應一個 **resolver**（解析函式，負責取得這個欄位的值）。執行查詢時，引擎從根欄位開始，一層層呼叫 resolver：`lessons` 的 resolver 查出課程列表，接著對**每一堂課**呼叫 `teacher` 的 resolver。這就帶出了 GraphQL 最有名的效能陷阱：

```text
 查詢：{ lessons(first: 4) { title teacher { name } } }

 naive resolver（每個欄位各自查資料庫）：
   lessons ──► SELECT * FROM lessons LIMIT 4                 1 次
     ├─ les_000.teacher ──► SELECT … WHERE id = t_misaki      ┐
     ├─ les_001.teacher ──► SELECT … WHERE id = t_misaki      │ N 次
     ├─ les_002.teacher ──► SELECT … WHERE id = t_minjun      │（N = 課程數）
     └─ les_003.teacher ──► SELECT … WHERE id = t_misaki      ┘
                                                     共 1 + N = 5 次

 batching（DataLoader）：
   lessons ──► SELECT * FROM lessons LIMIT 4                 1 次
     └─ 4 個 teacher resolver 在同一輪各自呼叫 loader.load(id)
          └─► 收集、去重後一次查詢：WHERE id IN (t_misaki, t_minjun)   1 次
                                                     共 2 次
```

這就是 **N+1 問題**：查 1 次列表，再為列表中的 N 筆資料各查 1 次。每個 resolver 單獨看都很合理，合起來卻讓查詢次數隨資料量線性增加；查詢再多巢狀一層（每位老師的評價），次數就變成乘法。標準解法是 **DataLoader** 模式：resolver 不直接查資料庫，而是向 loader 要求某個 key，loader 先把同一輪執行中所有的要求收集起來、去掉重複，再用一次 `IN (...)` 查詢取回，最後把結果分給各個 resolver。24.11 節的實驗三會用 asyncio 實作這個機制並數查詢次數。

GraphQL 的彈性帶來幾個 REST 沒有的代價，導入前要想清楚：

- **HTTP 快取幾乎失效**：查詢通常用 `POST /graphql` 送到同一個網址，CDN 與瀏覽器快取無法用網址區分不同查詢。常見對策是 **persisted queries**（把允許的查詢事先註冊，client 只送查詢的雜湊值，就能用 GET 並被快取），以及在 client 端用正規化快取。
- **錯誤不在 status code 上**：多數實作即使部分欄位失敗也回 200，錯誤放在回應的 `errors` 陣列，`data` 裡失敗的欄位是 null。監控只看 HTTP status 會漏掉錯誤，要另外統計 `errors`。
- **查詢成本難以預測**：client 可以寫出很深、很寬的查詢（例如老師 → 課程 → 學生 → 課程……），一個請求就可能拖垮資料庫。對外開放的 GraphQL 必須限制查詢深度與複雜度、對分頁欄位強制上限，或只允許 persisted queries。
- **授權要做到欄位層級**：REST 可以在 endpoint 層級檢查權限，GraphQL 的同一個 endpoint 可以拿到任何欄位，每個 resolver 都要檢查目前的使用者能不能看這個欄位。production 是否關閉 introspection 各團隊看法不同，它能減少資訊暴露，但不能取代 resolver 的授權檢查。

GraphQL 也有 **mutation**（修改資料，相當於 POST、PATCH）與 **subscription**（訂閱即時更新，通常走 WebSocket，第 32 章）。付款 mutation 一樣要靠 idempotency key，key 通常放在參數裡。

> [!note] 2026 現況
> 截至 2026 年 10 月，GraphQL 規格由 GraphQL Foundation 維護；「GraphQL over HTTP」這份描述 HTTP 傳輸細節（包括用 `application/graphql-response+json` 時以 HTTP status 表達錯誤）的規格，依 2026 年 10 月的了解仍在定稿過程中，不同 server 實作的行為不一致，串接前要確認對方的實作。

## 24.9 Webhook：反過來的 API

前面三種風格都是「client 呼叫 server」。但金流的授權結果、退款、拒付，是在金流供應商那邊發生的事，聲聲 Live 不可能每秒去問一次「有沒有新消息」。**webhook** 把方向反過來：事件發生時，供應商主動對你事先登記的網址送一個 HTTP POST，例如 `POST /v1/webhooks/pay`，內容是一個事件（event）物件。

```text
 pay.example.net（198.51.100.64/26 送出）           api.shengsheng.example
   │── POST /v1/webhooks/pay ─────────────────────────►│ 1. 驗證簽章與 timestamp（第 17 章）
   │   Pay-Signature: t=…,v1=…                         │ 2. 用 event id 去重（INSERT … unique）
   │   {"id":"evt_03","type":"payment.succeeded",…}    │ 3. 放進佇列，立刻回應
   │◄────────────────────────────── 200 OK（< 1 秒）──│
   │                                                   │ 4. 背景 worker 開通課程、寄信
   │                                                   │
   │ （若逾時或收到 5xx）                                 │
   │── 30 秒後重送同一個 evt_03 ──────────────────────►│ 去重：已處理過 → 直接回 200
   │── 再失敗：5 分鐘、30 分鐘……指數退避重送 ─────────────►│
```

這張圖概括了 webhook 接收端的四個步驟。第一步是驗證：任何人都能對你的網址送 POST，必須用 HMAC 簽章與 timestamp 確認來源並防止重放，第 17 章已經實作過這套驗證，第 30 章會再談經過多層 proxy 時怎麼保住原始 body；來源 IP 的允許清單（`198.51.100.64/26`）只能當額外一層，不能取代簽章。第二步去重。第三步立刻回 2xx：供應商通常只給幾秒鐘，處理太久會被當成失敗而重送，所以收到後先寫入佇列，由背景 worker 慢慢處理。第四步才是真正的業務邏輯。

webhook 的送達語意幾乎都是**至少一次**（at-least-once）：送出方收不到 2xx 就重送，而「你處理完了、但 2xx 在路上遺失」時，你會收到重複的事件。事件也可能**亂序**：退款事件可能比付款成功事件先到，或很晚才到的舊事件會想把狀態改回去。所以接收端要用事件 id 去重，並比較事件的版本或時間，只接受比目前狀態新的事件：

```python
# 金流 webhook 的接收端邏輯：至少一次送達 → 要去重；可能亂序 → 要比版本
events = [  # 供應商實際送來的順序：有重送、有亂序
    {"id": "evt_01", "payment": "pay_0001", "type": "payment.created", "version": 1},
    {"id": "evt_03", "payment": "pay_0001", "type": "payment.succeeded", "version": 3},
    {"id": "evt_03", "payment": "pay_0001", "type": "payment.succeeded", "version": 3},  # 我們回應太慢，對方重送
    {"id": "evt_04", "payment": "pay_0001", "type": "payment.refunded", "version": 4},
    {"id": "evt_02", "payment": "pay_0001", "type": "payment.processing", "version": 2},  # 很晚才到的舊事件
]
seen_ids = set()          # 實務上放資料庫，用 unique constraint 保證只處理一次
state = {}                # payment -> (version, type)
side_effects = []         # 例如寄信、開通課程

for ev in events:
    if ev["id"] in seen_ids:
        print(f"{ev['id']} 重複，直接回 200")
        continue
    seen_ids.add(ev["id"])
    current = state.get(ev["payment"], (0, None))
    if ev["version"] <= current[0]:
        print(f"{ev['id']} 版本 {ev['version']} 比目前的 {current[0]} 舊，忽略")
        continue
    state[ev["payment"]] = (ev["version"], ev["type"])
    side_effects.append(ev["type"])
    print(f"{ev['id']} 套用 {ev['type']}")

print("最終狀態:", state["pay_0001"][1], "| 副作用次數:", len(side_effects))
assert state["pay_0001"] == (4, "payment.refunded") and len(side_effects) == 3
```

執行結果：

```text
evt_01 套用 payment.created
evt_03 套用 payment.succeeded
evt_03 重複，直接回 200
evt_04 套用 payment.refunded
evt_02 版本 2 比目前的 4 舊，忽略
最終狀態: payment.refunded | 副作用次數: 3
```

逐行看：evt_03 第二次送來時被 id 去重擋下，副作用（開通課程、寄信）沒有重做；evt_02 雖然是第一次見到，但它代表的「處理中」比目前的「已退款」還舊，所以被忽略，否則一筆已退款的付款會被改回處理中。實務上，很多團隊進一步把 webhook 當成「有東西變了」的通知，收到後再用 REST API 向供應商查詢該付款的最新狀態，而不完全相信事件本身的內容；這樣即使亂序或遺漏，最後都會收斂到正確狀態。另外要有**對帳**（reconciliation）工作，定期列出供應商那邊的交易，補上漏收的事件。

反過來，如果聲聲 Live 要提供 webhook 給合作夥伴（例如企業客戶想在員工完成課程時收到通知），送出方的責任是：對事件簽章、帶上事件 id 與時間、失敗時指數退避重送並設上限、提供重送與查詢介面。還有一個資安重點：對方登記的網址是外部輸入，送出前要確認它不會解析到內部位址（例如 10.20.0.0/16 或雲端的 metadata 位址），否則 webhook 功能會變成讓外人探測內網的跳板，這類問題稱為 SSRF（Server-Side Request Forgery）。

## 24.10 選型：什麼時候用哪一種

看完四種做法，可以把取捨整理成一張比較表。沒有一種在每一欄都勝出，這正是需要選型的原因：

| 面向 | REST（JSON） | gRPC（protobuf） | GraphQL |
|---|---|---|---|
| 契約 | OpenAPI 文件（可選，靠紀律維持） | `.proto` 檔，強制且可產生程式碼 | schema，強制且可查詢 |
| 資料大小與解析 | 文字，較大，人類可讀 | 二進位，小而快，需工具解讀 | JSON，只回需要的欄位 |
| 瀏覽器直接呼叫 | 可以 | 不行，需要 gRPC-Web 等轉換 | 可以 |
| HTTP 快取與 CDN | 天生支援（GET＋URL＋Cache-Control） | 幾乎不用 | 困難，要靠 persisted queries |
| streaming | 要另外用 SSE、WebSocket（第 31、32 章） | 內建四種模式 | subscription（多半走 WebSocket） |
| 錯誤表達 | HTTP status＋problem details | `grpc-status` trailer | 回應中的 `errors`，HTTP 多半 200 |
| deadline 與取消 | 沒有標準，要自訂 header | `grpc-timeout` 與 stream 取消內建 | 沒有標準 |
| 演進方式 | 加欄位、版本號 | 欄位編號＋未知欄位跳過 | 加欄位、標記 `@deprecated` |
| 主要風險 | 過多或不足的資料、介面風格不一致 | L4 負載不均、除錯不直覺 | N+1、查詢成本、欄位層級授權 |

把這張表變成判斷流程：

```text
 誰是 client？
   │
   ├─ 外部開發者、合作夥伴、需要 CDN 快取的公開資料
   │     └─► REST：最容易理解、工具最多、HTTP 快取直接可用
   │
   ├─ 自己的後端服務之間（同一組織、可以共用 .proto）
   │     ├─ 需要 streaming、嚴格型別、低延遲 ─► gRPC
   │     └─ 簡單、少量的呼叫，團隊只熟 HTTP ─► REST 也完全可以
   │
   └─ 自己的前端（web、app），畫面需要組合很多種資料
         ├─ 畫面常改、client 種類多 ─► GraphQL（或一個 BFF 層）
         └─ 畫面固定、API 數量少 ─► REST＋為畫面設計的聚合 endpoint
```

最後一個分支提到 **BFF**（Backend for Frontend：為某個前端量身打造的一層 API，替前端把多個後端服務的資料組合好）。它是 GraphQL 之外的另一個選項：為 app 的課程頁做一支 `GET /v1/app/lesson-page/{id}`，由後端並行呼叫六個服務並組合回應，同樣能把六次往返變成一次，還保留了 HTTP 快取。代價是每個畫面改版都要動 BFF。

聲聲 Live 最後的決定是：對外與對 app 維持 REST，付款相關的 POST 一律要求 idempotency key，錯誤一律用 problem details，列表一律用 cursor 分頁；服務之間的 `reco`、`chat` 等內部呼叫改用 gRPC，並強制每個呼叫都要有 deadline；app 課程頁先用 BFF 解決六次往返的問題，半年後再依畫面變動的頻率評估是否導入 GraphQL。

## 24.11 動手做：付款 API、手工 protobuf 與 N+1

這一節有三個實驗，都只用標準函式庫，在 127.0.0.1 上離線執行。實驗一做出一個具備 cursor 分頁、problem details 與 idempotency key 的 REST API，並重現故事裡的「逾時後重試」；實驗二手工編解碼 protobuf 與 gRPC 的訊息框架；實驗三實作一個極小的 GraphQL 執行器，數出 N+1 與 batching 的查詢次數。

### 實驗一：不會重複扣款的 REST API

server 用 `ThreadingHTTPServer` 在 port 0 啟動，提供三種資源：`GET /v1/lessons`（cursor 分頁，另外保留 `offset` 參數做對照）、`GET /v1/lessons/{id}`、`POST /v1/payments`（必須帶 `Idempotency-Key`）。假金流用 0.25 秒模擬緩慢的授權，client 端第一次嘗試只等 0.1 秒，重現手機 app 逾時放棄的情況。

```python
import base64, hashlib, hmac, http.client, json, socket, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

SECRET = b"cursor-signing-key"           # 簽 cursor，避免 client 竄改或自己拼
LESSONS = [{"id": f"les_{i:03d}", "start_at": f"2026-10-0{2 + i // 3}T{12 + i % 3}:00",
            "teacher": "美咲"} for i in range(7)]
CHARGES = []                              # 假金流：每一筆都是真的扣款
IDEM = {}                                 # (student, key) -> 紀錄
IDEM_LOCK = threading.Lock()

def make_cursor(item):
    raw = json.dumps([item["start_at"], item["id"]]).encode()
    sig = hmac.new(SECRET, raw, hashlib.sha256).digest()[:8]
    return base64.urlsafe_b64encode(raw + sig).decode().rstrip("=")

def read_cursor(token):
    blob = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    raw, sig = blob[:-8], blob[-8:]
    if not hmac.compare_digest(sig, hmac.new(SECRET, raw, hashlib.sha256).digest()[:8]):
        raise ValueError("bad signature")
    return tuple(json.loads(raw))

class Api(BaseHTTPRequestHandler):
    def log_message(self, *args):        # 安靜，讓輸出只剩實驗結果
        pass

    def send_json(self, status, obj, ctype="application/json", extra=None):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def problem(self, status, slug, title, detail):
        self.send_json(status, {"type": f"https://api.shengsheng.example/problems/{slug}",
                                "title": title, "status": status, "detail": detail,
                                "instance": self.path}, "application/problem+json")

    def do_GET(self):
        url = urlsplit(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path.startswith("/v1/lessons/"):
            lid = url.path.rsplit("/", 1)[1]
            found = [x for x in LESSONS if x["id"] == lid]
            if not found:
                return self.problem(404, "not-found", "Lesson not found", f"沒有 id 為 {lid} 的課程")
            return self.send_json(200, found[0])
        limit = min(int(q.get("limit", 3)), 50)   # 上限保護資料庫
        rows = sorted(LESSONS, key=lambda x: (x["start_at"], x["id"]))
        if "offset" in q:                          # 舊做法，留著做對照
            page = rows[int(q["offset"]):int(q["offset"]) + limit]
            return self.send_json(200, {"data": [x["id"] for x in page]})
        if "cursor" in q:
            try:
                after = read_cursor(q["cursor"])
            except Exception:
                return self.problem(400, "invalid-cursor", "Invalid cursor", "cursor 無法驗證，請從第一頁重新開始")
            rows = [x for x in rows if (x["start_at"], x["id"]) > after]   # keyset：WHERE (start_at,id) > (?,?)
        page, more = rows[:limit], len(rows) > limit                         # 多取一筆判斷是否還有下一頁
        nxt = make_cursor(page[-1]) if more else None
        extra = {"Link": f'</v1/lessons?limit={limit}&cursor={nxt}>; rel="next"'} if nxt else {}
        self.send_json(200, {"data": [x["id"] for x in page], "next_cursor": nxt}, extra=extra)

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        student = self.headers.get("X-Student-Id", "anonymous")   # 實務上來自驗證過的 token
        key = self.headers.get("Idempotency-Key")
        if not key:
            return self.problem(400, "idempotency-key-required", "Idempotency-Key required", "付款請求必須帶 Idempotency-Key")
        fp = hashlib.sha256(body).hexdigest()
        with IDEM_LOCK:                                   # 「查有沒有」與「佔位」必須是同一個原子動作
            rec = IDEM.get((student, key))
            if rec is None:
                IDEM[(student, key)] = rec = {"fp": fp, "state": "in_progress"}
                mine = True
            else:
                mine = False
        if not mine:
            if rec["fp"] != fp:
                return self.problem(422, "idempotency-key-reused", "Key reused with different body", "同一把 key 不能用在不同內容的請求")
            if rec["state"] == "in_progress":
                return self.problem(409, "request-in-progress", "Request in progress", "同一把 key 的請求還在處理，請稍後重試")
            status, saved = rec["response"]
            return self.send_json(status, saved, extra={"Idempotent-Replayed": "true"})
        order = json.loads(body)
        time.sleep(0.25)                                  # 模擬金流供應商很慢
        CHARGES.append(order["amount"])
        result = {"id": f"pay_{len(CHARGES):04d}", "lesson_id": order["lesson_id"],
                  "amount": order["amount"], "status": "succeeded"}
        rec.update(state="done", response=(201, result))  # 先存結果，再回應
        self.send_json(201, result, extra={"Location": f"/v1/payments/{result['id']}"})

def call(port, method, path, body=None, headers=None, timeout=2.0):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    data = json.dumps(body).encode() if body is not None else None
    conn.request(method, path, body=data, headers={"Content-Type": "application/json", **(headers or {})})
    resp = conn.getresponse()
    out = (resp.status, resp.getheader("Content-Type"), json.loads(resp.read()), dict(resp.getheaders()))
    conn.close()
    return out

server = ThreadingHTTPServer(("127.0.0.1", 0), Api)
server.daemon_threads = True
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

print("== 1. cursor 分頁 ==")
path, seen = "/v1/lessons?limit=3", []
while path:
    st, _, js, hdr = call(port, "GET", path)
    print(st, js["data"], "next" if js["next_cursor"] else "end")
    seen += js["data"]
    path = f"/v1/lessons?limit=3&cursor={js['next_cursor']}" if js["next_cursor"] else None
assert seen == [x["id"] for x in LESSONS]

print("== 2. 翻頁途中有新資料插入 ==")
p1 = call(port, "GET", "/v1/lessons?limit=3&offset=0")[2]["data"]
c1 = call(port, "GET", "/v1/lessons?limit=3")[2]
LESSONS.append({"id": "les_new", "start_at": "2026-10-01T09:00", "teacher": "美咲"})  # 排在最前面
p2 = call(port, "GET", "/v1/lessons?limit=3&offset=3")[2]["data"]
c2 = call(port, "GET", f"/v1/lessons?limit=3&cursor={c1['next_cursor']}")[2]["data"]
print("offset：", p1, "→", p2, "重複", sorted(set(p1) & set(p2)))
print("cursor：", c1["data"], "→", c2, "重複", sorted(set(c1["data"]) & set(c2)))
assert set(p1) & set(p2) and not set(c1["data"]) & set(c2)

print("== 3. problem details ==")
for p in ["/v1/lessons/les_999", "/v1/lessons?cursor=" + c1["next_cursor"][:-2] + "AA"]:
    st, ctype, js, _ = call(port, "GET", p)
    print(st, ctype, js["type"].rsplit("/", 1)[1], "|", js["detail"])

print("== 4. idempotency key ==")
order, h = {"lesson_id": "les_004", "amount": 1200}, {"X-Student-Id": "stu_1024", "Idempotency-Key": "4f9c2a1e-7b1d-4c55-9e0a-1d2b3c4d5e6f"}
try:
    call(port, "POST", "/v1/payments", order, h, timeout=0.1)      # 手機端 0.1 秒就放棄
except socket.timeout:
    print("第一次：client 逾時，不知道有沒有扣款")
st, _, js, _ = call(port, "POST", "/v1/payments", order, h)
print("立刻重試：", st, js["title"])
time.sleep(0.3)
st, _, js, hdr = call(port, "POST", "/v1/payments", order, h)
print("稍後重試：", st, js["id"], "Idempotent-Replayed:", hdr.get("Idempotent-Replayed"))
st, _, js, _ = call(port, "POST", "/v1/payments", {**order, "amount": 9999}, h)
print("同 key 改金額：", st, js["title"])
st, _, js, _ = call(port, "POST", "/v1/payments", order, {"X-Student-Id": "stu_1024"})
print("沒帶 key：", st, js["title"])
print("實際扣款次數：", len(CHARGES))
assert len(CHARGES) == 1
server.shutdown(); server.server_close()
```

執行結果：

```text
== 1. cursor 分頁 ==
200 ['les_000', 'les_001', 'les_002'] next
200 ['les_003', 'les_004', 'les_005'] next
200 ['les_006'] end
== 2. 翻頁途中有新資料插入 ==
offset： ['les_000', 'les_001', 'les_002'] → ['les_002', 'les_003', 'les_004'] 重複 ['les_002']
cursor： ['les_000', 'les_001', 'les_002'] → ['les_003', 'les_004', 'les_005'] 重複 []
== 3. problem details ==
404 application/problem+json not-found | 沒有 id 為 les_999 的課程
400 application/problem+json invalid-cursor | cursor 無法驗證，請從第一頁重新開始
== 4. idempotency key ==
第一次：client 逾時，不知道有沒有扣款
立刻重試： 409 Request in progress
稍後重試： 201 pay_0001 Idempotent-Replayed: true
同 key 改金額： 422 Key reused with different body
沒帶 key： 400 Idempotency-Key required
實際扣款次數： 1
```

逐段解說輸出：

1. **cursor 分頁**：七筆課程以每頁三筆讀完，最後一頁的 `next_cursor` 是 null，client 據此停止。程式用「多取一筆」判斷是否還有下一頁，不需要另外做昂貴的 `COUNT(*)`。迴圈結束後的 assert 確認讀到的資料剛好是全部、沒有重複。
2. **翻頁途中插入資料**：在讀完第一頁後插入一筆排在最前面的 `les_new`。offset 版本的第二頁從「第 3 個位置」開始，因為所有資料往後移了一格，`les_002` 被讀了兩次；cursor 版本的第二頁從「`les_002` 之後」開始，完全不受影響。新插入的那筆排在 cursor 之前，這一輪不會讀到，這是 keyset 分頁的正常語意。
3. **problem details**：兩種錯誤都回 `application/problem+json`，client 用 `type` 的最後一段（`not-found`、`invalid-cursor`）判斷要怎麼處理，`detail` 只給人看。第二個請求把 cursor 的最後兩個字元竄改，HMAC 驗證失敗而回 400，證明 client 無法偽造 cursor。
4. **idempotency key**：第一次嘗試在 0.1 秒時逾時，client 不知道有沒有扣款；server 那邊其實正在處理。立刻重試時，key 處於「處理中」，server 回 409 而不是再扣一次。0.3 秒後再試，server 找到已完成的紀錄，原封不動地回傳 201 與同一個付款 id `pay_0001`，並加上 `Idempotent-Replayed: true`。同一把 key 改了金額回 422，沒帶 key 回 400。最後一行是最重要的驗證：三次嘗試、五個請求，真正的扣款只有 1 次。

注意 `do_POST` 裡的 `IDEM_LOCK`：它把「查 key」和「佔 key」包成同一個原子動作。這個程式只有一個 process，用 thread lock 就夠；在 production 有多台 gunicorn 主機時，要改成資料庫的 unique constraint，或 Redis 的 `SET NX`，原理完全相同。

### 實驗二：手工編解碼 protobuf 與 gRPC 訊息框架

這個實驗不需要 protobuf 套件，直接依 wire format 規則編碼 24.6 節的 `RecoRequest`，再用一個「不看 schema」的解碼器切開欄位，最後包上 gRPC 的 5 bytes 前綴，並示範 `grpc-timeout` header 的格式。

```python
import struct

VARINT, I64, LEN, I32 = 0, 1, 2, 5          # 常用的 wire type

def enc_varint(n):
    if n < 0:
        n += 1 << 64                            # int32/int64 的負數一律當 64 bit 補數
    out = bytearray()
    while True:
        low7, n = n & 0x7F, n >> 7
        out.append(low7 | (0x80 if n else 0))   # 最高位 1 = 後面還有
        if not n:
            return bytes(out)

def dec_varint(buf, i):
    n = shift = 0
    while True:
        b = buf[i]; i += 1
        n |= (b & 0x7F) << shift; shift += 7
        if not b & 0x80:
            return n, i

def zigzag(n):          # sint32：0,-1,1,-2 → 0,1,2,3，讓小負數也短
    return (n << 1) ^ (n >> 31)

def tag(field, wtype):
    return enc_varint(field << 3 | wtype)

def enc_string(field, s):
    b = s.encode()
    return tag(field, LEN) + enc_varint(len(b)) + b

def decode(buf):
    """不看 schema 也能切開欄位：wire type 告訴我們每個值有多長。"""
    i, fields = 0, []
    while i < len(buf):
        key, i = dec_varint(buf, i)
        field, wtype = key >> 3, key & 7
        if wtype == VARINT:
            val, i = dec_varint(buf, i)
        elif wtype == LEN:
            size, i = dec_varint(buf, i)
            val, i = bytes(buf[i:i + size]), i + size
        elif wtype == I64:
            val, i = struct.unpack_from("<q", buf, i)[0], i + 8
        elif wtype == I32:
            val, i = struct.unpack_from("<i", buf, i)[0], i + 4
        else:
            raise ValueError(f"wire type {wtype} 不支援")
        fields.append((field, wtype, val))
    return fields

# 1. 經典例子：150 → 96 01
assert enc_varint(150) == b"\x96\x01" and dec_varint(b"\x96\x01", 0) == (150, 2)
print("varint(150) =", enc_varint(150).hex(" "), "| varint(1) =", enc_varint(1).hex(" "))

# 2. RecoRequest{student_id="stu_1024", limit=5, languages=["ja","ko"]}
v1 = enc_string(1, "stu_1024") + tag(2, VARINT) + enc_varint(5) + enc_string(3, "ja") + enc_string(3, "ko")
print(f"v1 訊息 {len(v1)} bytes:", v1.hex(" "))
for f, w, v in decode(v1):
    print(f"  field {f} wire {w} ->", v.decode() if isinstance(v, bytes) else v)
json_size = len('{"student_id":"stu_1024","limit":5,"languages":["ja","ko"]}')
print("同樣內容的 JSON:", json_size, "bytes")

# 3. 新版加了 field 5（bool include_live），舊版 decoder 不認得也能跳過
v2 = v1 + tag(5, VARINT) + enc_varint(1)
known = {1, 2, 3}
old_view = [(f, v) for f, _, v in decode(v2) if f in known]
unknown = [f for f, _, _ in decode(v2) if f not in known]
print("舊版讀新訊息：認得", len(old_view), "個值，略過 field", unknown)
assert old_view == [(f, v) for f, _, v in decode(v1)]

# 4. 負數：int32 用 10 bytes，sint32 用 zigzag 只要 1 byte
print("int32(-1) =", enc_varint(-1).hex(" "), f"({len(enc_varint(-1))} bytes)")
print("sint32(-1) =", enc_varint(zigzag(-1)).hex(" "), "| sint32(-60) =", enc_varint(zigzag(-60)).hex(" "))
assert len(enc_varint(-1)) == 10 and enc_varint(zigzag(-1)) == b"\x01"

# 5. gRPC 在 HTTP/2 DATA 裡的格式：1 byte 壓縮旗標 + 4 bytes 長度（big-endian）+ 訊息
frame = struct.pack("!BI", 0, len(v1)) + v1
flag, length = struct.unpack("!BI", frame[:5])
print("gRPC message prefix:", frame[:5].hex(" "), f"→ compressed={flag} length={length}")
assert frame[5:] == v1

# 6. grpc-timeout header：最多 8 位數字 + 單位（H M S m u n）
def grpc_timeout(seconds):
    for unit, scale in (("n", 1e9), ("u", 1e6), ("m", 1e3), ("S", 1), ("M", 1 / 60), ("H", 1 / 3600)):
        value = int(seconds * scale)
        if value < 10 ** 8:
            return f"{value}{unit}"
UNITS = {"H": 3600, "M": 60, "S": 1, "m": 1e-3, "u": 1e-6, "n": 1e-9}
def parse_timeout(header):
    return int(header[:-1]) * UNITS[header[-1]]
print("encode 0.3 s →", grpc_timeout(0.3), "| encode 45 s →", grpc_timeout(45))
print("parse 300m →", parse_timeout("300m"), "s | parse 2S →", parse_timeout("2S"), "s")
assert abs(parse_timeout(grpc_timeout(0.3)) - 0.3) < 1e-9
```

執行結果：

```text
varint(150) = 96 01 | varint(1) = 01
v1 訊息 20 bytes: 0a 08 73 74 75 5f 31 30 32 34 10 05 1a 02 6a 61 1a 02 6b 6f
  field 1 wire 2 -> stu_1024
  field 2 wire 0 -> 5
  field 3 wire 2 -> ja
  field 3 wire 2 -> ko
同樣內容的 JSON: 59 bytes
舊版讀新訊息：認得 4 個值，略過 field [5]
int32(-1) = ff ff ff ff ff ff ff ff ff 01 (10 bytes)
sint32(-1) = 01 | sint32(-60) = 77
gRPC message prefix: 00 00 00 00 14 → compressed=0 length=20
encode 0.3 s → 300000u | encode 45 s → 45000000u
parse 300m → 0.3 s | parse 2S → 2 s
```

逐行對照輸出：

1. `varint(150) = 96 01` 與 24.6 節手算的結果相同；1 只需要 1 byte。
2. 20 bytes 的訊息可以這樣拆：`0a` 是 field 1、wire type 2 的 tag，`08` 是長度 8，接著 8 bytes 是 `stu_1024` 的 ASCII；`10` 是 field 2、wire type 0，`05` 就是 limit=5；`1a 02 6a 61` 與 `1a 02 6b 6f` 是 field 3 的兩個元素 `ja`、`ko`，repeated 的 string 就是同一個 tag 出現多次。同樣內容的 JSON 要 59 bytes，差異主要來自 JSON 每次都要送欄位名稱。
3. 新版訊息多了 field 5，舊版解碼器靠 wire type 0 知道要讀一個 varint，讀完就跳過，認得的四個值與舊訊息完全相同。這就是「新增欄位不會弄壞舊 client」在位元層級的原因，也說明了為什麼欄位編號絕對不能重用：舊版會把重用的編號當成舊欄位來解讀。
4. int32 的 −1 佔了 10 bytes，因為它被當成 64 bit 的全 1 補數；sint32 經過 zigzag 後只要 1 byte，−60 也只要 1 byte（`77`，也就是 119）。
5. gRPC 前綴 `00 00 00 00 14`：第一個 byte 0 表示沒有壓縮，後四個 byte 是 big-endian 的長度 0x14＝20，剛好是訊息長度。注意 protobuf 內部的固定長度數值是 little-endian，gRPC 的長度前綴卻是 big-endian（網路位元組順序，第 2 章），兩層是不同人設計的格式。
6. `grpc-timeout` 是「最多 8 位數字＋單位」（H、M、S、m、u、n 為時、分、秒、毫秒、微秒、奈秒）。編碼函式選放得下的最細單位，所以 0.3 秒寫成 `300000u`；`300m` 同樣合法。

### 實驗三：GraphQL 的 N+1 與 DataLoader

這個實驗實作一個只支援欄位、巢狀與整數參數的極小 GraphQL 子集：parser 把查詢轉成樹，executor 用 asyncio 並行呼叫各欄位的 resolver。同一個查詢先用 naive resolver 執行，再用 DataLoader 執行，比較資料庫查詢次數。

```python
import asyncio, json, re

# ---- 假資料庫：每次呼叫都記一筆「SQL」，用來數查詢次數 ----
LESSONS = [{"id": f"les_00{i}", "title": t, "teacher_id": tid} for i, (t, tid) in
           enumerate([("日語會話", "t_misaki"), ("五十音", "t_misaki"), ("韓語入門", "t_minjun"), ("JLPT N3", "t_misaki")])]
TEACHERS = {"t_misaki": {"name": "美咲", "rating": 4.9}, "t_minjun": {"name": "敏俊", "rating": 4.8}}
SQL_LOG = []

async def db_lessons(first):
    SQL_LOG.append(f"SELECT * FROM lessons LIMIT {first}")
    return LESSONS[:first]

async def db_teachers(ids):
    SQL_LOG.append(f"SELECT * FROM teachers WHERE id IN ({', '.join(ids)})")
    return [TEACHERS[i] for i in ids]

# ---- 極小的 GraphQL 子集 parser：欄位、巢狀 selection、整數參數 ----
def parse(query):
    tokens = re.findall(r"[A-Za-z_]\w*|\d+|[{}():]", query)
    pos = 0
    def selection():
        nonlocal pos
        assert tokens[pos] == "{"; pos += 1
        fields = []
        while tokens[pos] != "}":
            name, args, children = tokens[pos], {}, []
            pos += 1
            if tokens[pos] == "(":
                pos += 1
                while tokens[pos] != ")":
                    args[tokens[pos]] = int(tokens[pos + 2]); pos += 3
                pos += 1
            if tokens[pos] == "{":
                children = selection()
            fields.append((name, args, children))
        pos += 1
        return fields
    return selection()

def depth(fields):
    return 1 + max((depth(c) for _, _, c in fields if c), default=0)

# ---- DataLoader：同一輪 event loop 裡收集 key，一次查完 ----
class DataLoader:
    def __init__(self, batch_fn):
        self.batch_fn, self.pending = batch_fn, {}
    def load(self, key):
        loop = asyncio.get_running_loop()
        if not self.pending:
            loop.call_soon(lambda: asyncio.ensure_future(self.dispatch()))  # 等這一輪的 load 都進來
        if key not in self.pending:
            self.pending[key] = loop.create_future()        # 同一個 key 只查一次
        return self.pending[key]
    async def dispatch(self):
        batch, self.pending = self.pending, {}
        for key, value in zip(batch, await self.batch_fn(list(batch))):
            batch[key].set_result(value)

# ---- resolver 與 executor ----
def make_resolvers(batched):
    loader = DataLoader(db_teachers)
    async def teacher(lesson, args):
        if batched:
            return await loader.load(lesson["teacher_id"])
        return (await db_teachers([lesson["teacher_id"]]))[0]   # 每一堂課各查一次：N+1
    return {("Query", "lessons"): lambda _, a: db_lessons(a["first"]),
            ("Lesson", "teacher"): teacher}

CHILD_TYPE = {("Query", "lessons"): "Lesson", ("Lesson", "teacher"): "Teacher"}

async def execute(fields, obj, typename, resolvers):
    async def one(name, args, children):
        fn = resolvers.get((typename, name))
        value = await fn(obj, args) if fn else obj[name]       # 沒寫 resolver 就直接取屬性
        if not children:
            return name, value
        sub = CHILD_TYPE[(typename, name)]
        if isinstance(value, list):
            return name, list(await asyncio.gather(*(execute(children, v, sub, resolvers) for v in value)))
        return name, await execute(children, value, sub, resolvers)
    return dict(await asyncio.gather(*(one(*f) for f in fields)))

QUERY = "{ lessons(first: 4) { title teacher { name rating } } }"

async def main():
    tree = parse(QUERY)
    assert depth(tree) <= 5, "查詢太深，拒絕執行"                # 防止惡意的深層巢狀
    results = {}
    for batched in (False, True):
        SQL_LOG.clear()
        data = await execute(tree, None, "Query", make_resolvers(batched))
        results[batched] = data
        print("== batching ==" if batched else "== naive resolver ==")
        print("\n".join("  " + s for s in SQL_LOG))
        print(f"  共 {len(SQL_LOG)} 次查詢")
    assert results[False] == results[True]
    print("回應（兩種做法相同）的第一筆：")
    print(" ", json.dumps({"data": {"lessons": results[True]["lessons"][:1]}}, ensure_ascii=False))
    print("查詢深度:", depth(tree))

asyncio.run(main())
```

執行結果：

```text
== naive resolver ==
  SELECT * FROM lessons LIMIT 4
  SELECT * FROM teachers WHERE id IN (t_misaki)
  SELECT * FROM teachers WHERE id IN (t_misaki)
  SELECT * FROM teachers WHERE id IN (t_minjun)
  SELECT * FROM teachers WHERE id IN (t_misaki)
  共 5 次查詢
== batching ==
  SELECT * FROM lessons LIMIT 4
  SELECT * FROM teachers WHERE id IN (t_misaki, t_minjun)
  共 2 次查詢
回應（兩種做法相同）的第一筆：
  {"data": {"lessons": [{"title": "日語會話", "teacher": {"name": "美咲", "rating": 4.9}}]}}
查詢深度: 3
```

輸出的第一段就是 N+1：一次查課程列表，接著四堂課各查一次老師，其中三次查的都是 `t_misaki`，總共 5 次。第二段用 DataLoader，四個 `teacher` resolver 在同一輪 event loop 中各自呼叫 `loader.load()`，loader 用 `call_soon` 把真正的查詢延到「這一輪的 load 都登記完」之後，收集到的 key 去重成兩個，一次 `IN (...)` 查完，總共 2 次。兩種做法的回應完全相同，差別只在查詢次數；課程從 4 堂變成 50 堂時，naive 版會變成 51 次，batching 版仍然是 2 次。

程式還有兩個值得注意的地方。`depth()` 在執行前計算查詢深度，超過上限就拒絕，這是對外開放 GraphQL 時最基本的防護；真實的系統還會估算複雜度（例如每個列表欄位乘上它的 `first` 參數）。另外，DataLoader 的實例是在 `make_resolvers()` 裡建立的，也就是**每個請求一個**：如果整個 process 共用一個 loader 並快取結果，不同使用者之間可能讀到彼此的資料，也會讀到過期的資料。

## 24.12 在工作上怎麼用

**後端工程師：設計 API 的檢查清單。** 新增一支 API 前，逐項回答：資源名稱是不是名詞、method 是否符合語意；所有錯誤路徑是否都回 problem details，`type` 是否有文件；列表是否用 cursor 分頁並限制 `limit` 上限；有副作用的 POST 是否支援 idempotency key，key 是否綁定使用者、是否原子地佔位、是否存下回應；呼叫下游時是否設定 deadline 並傳遞；新欄位是不是只做加法。這份清單放進 pull request 的範本，比事後修正便宜得多。

**SRE：用工具驗證 API 的行為。** 下面這組指令可以快速確認一支 API 是否符合契約：

```bash
# 錯誤格式：看 Content-Type 是否為 application/problem+json
curl -sS -i https://api.shengsheng.example/v1/lessons/les_999 | sed -n '1,12p'

# 重試安全：同一把 key 送兩次，第二次應該看到相同的付款 id 與重播標記
KEY=$(uuidgen)
for i in 1 2; do
  curl -sS -i -X POST https://api.shengsheng.example/v1/payments \
    -H "Authorization: Bearer $TOKEN" -H "Idempotency-Key: $KEY" \
    -H 'Content-Type: application/json' -d '{"lesson_id":"les_004","amount":1200}' \
    | grep -Ei '^HTTP/|idempotent-replayed|"id"'
done

# gRPC：列出服務、帶 deadline 呼叫（需要 server 開啟 reflection）
grpcurl -plaintext 10.20.4.12:50051 list
grpcurl -plaintext -max-time 0.3 -d '{"student_id":"stu_1024","limit":5}' \
  10.20.4.12:50051 shengsheng.reco.v1.Reco/GetRecommendations
```

在 staging 環境跑這組指令時，第二段的兩次輸出應該有相同的 `"id"`，而且第二次多一行 `Idempotent-Replayed: true`；如果看到兩個不同的 id，就是重複扣款的漏洞。gRPC 的指令要注意，`grpcurl` 依賴 server reflection 列出服務，production 通常只在內網開啟。監控上，gRPC 要依 `grpc-status` 分類（不是 HTTP status，因為它幾乎都是 200），GraphQL 要統計回應裡的 `errors`。

**前端與 app 工程師：重試的責任在 client。** key 要持久保存到操作有明確結果為止，app 被系統殺掉再打開時才能用同一把 key 重試。付款按鈕送出後立即停用只是改善體驗，真正防止重複的是 server 端的 key。

**資安工程師：每種風格各自的檢查點。** REST 的每個 endpoint 都要檢查「這個資源屬於這個使用者」，避免改網址上的 id 就看到別人的付款；GraphQL 的每個 resolver 都要授權；gRPC 服務之間用 mTLS 確認身分（第 30 章）；webhook 接收端驗簽章，送出端防 SSRF。

**判斷流程：使用者回報「被扣了兩次款」。**

```text
 用付款紀錄找出兩筆的 request id 與 Idempotency-Key
   │
   ├─ 兩筆的 key 不同
   │     ├─ 同一個 app session 內 ─► client 每次重試都產生新 key：修 app
   │     └─ 不同 session ─► 使用者確實按了兩次，或 app 重開後遺失 key：key 要持久化
   │
   ├─ 兩筆的 key 相同，卻都扣款成功
   │     └─► server 的「查＋佔」不是原子操作，或 key 沒有綁對範圍：查儲存層與鎖
   │
   └─ API 只有一筆，金流卻有兩筆
         └─► API 呼叫金流時重試，卻沒有把 key 傳給金流：端到端傳遞 key
```

這張流程圖的第一刀是比較兩筆紀錄的 key，所以 log 裡一定要記下 `Idempotency-Key` 與 `x-request-id`。三個分支分別指向 client、API 與下游整合三個不同的修正位置，第三個分支最容易被忽略：只要整條鏈上有任何一段「重試但不帶 key」，前面所有的保護都會失效。

## 24.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 使用者被重複扣款或重複建立訂單 | POST 逾時後被 client 或 proxy 重試，server 沒有 idempotency 機制 | 比對兩筆紀錄的時間差是否約等於 client 逾時；檢查是否帶了 key | 有副作用的 POST 要求 `Idempotency-Key`；原子地佔位並存下回應；key 端到端傳遞 |
| 無限捲動時同一筆資料出現兩次或漏掉 | 用 offset 分頁，翻頁途中資料被新增或刪除 | 在翻頁時插入資料，觀察第二頁是否重複 | 改用 cursor（keyset）分頁，排序鍵加上唯一 id |
| 告警顯示錯誤率 0%，使用者卻大量回報失敗 | API 錯誤時回 200 並在 body 放錯誤；或 GraphQL 的 `errors` 沒被統計；或 gRPC 只看 HTTP 200 | 抽樣檢查失敗請求的 status code 與 body | REST 用正確的 status code＋problem details；監控 `grpc-status` 與 GraphQL `errors` |
| 下游一變慢，上游 worker 全部卡住、整站逾時 | 呼叫下游沒有設定 timeout 或 deadline，也沒有傳遞 | thread dump 看到大量 worker 停在等待下游；下游延遲上升時上游同步惡化 | 每個呼叫都設 deadline 並往下傳；檢查剩餘時間後再重試；必要時降級 |
| gRPC 服務新增節點後，新節點幾乎沒有流量 | HTTP/2 長連線＋L4 LB，連線建立後就不再重新分配 | 比較各節點的連線數與 RPS；新節點的連線數接近 0 | 用 L7 LB 或 client 端負載分散；設定連線的最長存活時間讓 client 定期重連（第 25 章） |
| 新版 server 上線後，舊版 client 解析失敗 | 改了欄位型別、重用了 protobuf 欄位編號，或 client 對 JSON 做了嚴格驗證 | 比對新舊 schema 或 `.proto`；看 client 的解析錯誤 | 只做加法；刪除欄位用 `reserved`；client 忽略未知欄位；破壞性變更走新版本 |
| GraphQL 頁面一變長，資料庫 QPS 暴增 | resolver 各自查資料庫，造成 N+1 | 打開查詢 log，數一個請求觸發幾次 SQL | 每個請求建立 DataLoader 做 batching；為關聯欄位加索引 |
| 同一個 webhook 事件被處理兩次，或狀態被舊事件改回去 | webhook 是至少一次送達且可能亂序，接收端沒去重、沒比版本 | 用事件 id 查處理紀錄；比對事件時間與目前狀態 | 以事件 id 做 unique 去重；只接受較新的版本；收到後再向供應商查最新狀態 |
| webhook 一直被重送，供應商最後停用了你的端點 | 接收端同步處理太久，超過供應商的逾時；或在驗證前就因格式錯誤回 5xx | 看 webhook 請求的處理時間與回應碼分布 | 驗證後先寫入佇列立即回 2xx，業務邏輯交給背景 worker |

表中多數問題的根源相同：契約只描述了成功時的樣子。除錯時先問「失敗後誰會重試、重試帶不帶同一個識別、等多久放棄」，答案往往就指向根因。

## 24.14 動手練習

1. **延伸實驗一：保存期限與重新開放 key**（延伸程式）。替 `IDEM` 的紀錄加上建立時間，超過 24 小時（用模擬時鐘）就視為不存在；再加上「業務驗證失敗（例如金額小於等於 0）時刪除 key」，讓 client 修正內容後能用同一把 key 再試。
   答案要點：驗證失敗發生在副作用之前，刪除 key 是安全的；但金流呼叫逾時這種「不確定是否已扣款」的失敗，不能刪 key。測試時要涵蓋三種情況：過期後同一把 key 被當成新請求、驗證失敗後能重試成功、金流逾時後重試仍回「處理中」或需要人工確認。

2. **延伸實驗二：解碼巢狀訊息**（延伸程式）。依 24.6 節的 `RecoResponse`，手工編碼一個包含兩個 `Lesson` 的回應（巢狀 message 是 wire type 2，內容是另一則完整的 protobuf 訊息），再寫一個遞迴解碼器把它還原。
   答案要點：外層每個 `lessons` 欄位的 tag 是 `0a`，接著是內層訊息的長度與內容；解碼器看到 wire type 2 時，無法只靠 wire format 判斷內容是字串還是巢狀訊息，必須依 schema 決定，這說明了「不看 schema 能切開欄位」與「不看 schema 能理解欄位」是兩回事。

3. **用 curl 觀察真實 API 的錯誤格式**（真實工具）。對你常用的某個公開 API 故意送錯誤請求（不存在的資源、缺少參數），用 `curl -i` 觀察 status code、`Content-Type` 與錯誤內容；再找一個列表 API，觀察它用 offset、page 還是 cursor 分頁，有沒有 `Link` header。
   答案要點：記錄每個 API 的錯誤格式是否一致、是否有機器可讀的錯誤碼、是否洩漏內部資訊。你會發現很多 API 的錯誤格式各不相同，這正是 problem details 想解決的問題。

4. **用 DevTools 數一個頁面的 API 呼叫**（真實工具）。打開瀏覽器 DevTools 的 Network 面板，篩選 Fetch/XHR，載入一個內容豐富的頁面（例如商品頁或課程頁），數一數呼叫了幾支 API、哪些可以並行、哪些必須等前一個回來才能發出。
   答案要點：找出「必須依序」的呼叫鏈（例如先拿到課程才知道要查哪位老師），這種依賴鏈在高 RTT 環境下最傷，是 BFF 或 GraphQL 能帶來最大改善的地方；只是數量多但能並行的請求，用 HTTP/2 已經能大幅緩解。

5. **手算 deadline 預算**。課程頁 API 的總預算是 800 毫秒。nginx 與網路耗用 50 毫秒，Flask 本身處理 30 毫秒，接著並行呼叫 `reco`（p99 250 毫秒）和評價服務（p99 400 毫秒），兩者都回來後再呼叫優惠券服務（p99 150 毫秒）。p99 的情況下還剩多少時間？如果評價服務的 p99 上升到 600 毫秒會怎樣？
   答案要點：並行的兩個呼叫取最慢的 400 毫秒，總和為 50＋30＋400＋150＝630 毫秒，剩 170 毫秒的餘裕。評價服務升到 600 毫秒時總和為 830 毫秒，超過預算；正確的應對是讓評價服務在剩餘時間不足時降級（例如顯示「評價載入中」），而不是把總預算調長。

## 本章重點整理

- 網路 API 是一份契約，除了資料格式，還必須說清楚失敗怎麼表達、哪些操作可以重試、最多等多久，以及新舊版本如何共存。
- REST 以資源為中心：URI 用名詞表示資源，動作交給 HTTP method；不容易對應 CRUD 的動作，名詞化成子資源或採用一致的自訂方法慣例。
- GET、PUT、DELETE 是 idempotent，POST 不是；idempotent 指的是 server 的最終狀態相同，不是每次回應都一樣。
- status code 要讓 client 不讀內容就能決定下一步：4xx 表示原封不動重送沒用，5xx 與 429 表示可以稍後重試；錯誤時回 200 會讓監控與快取都失靈。
- 版本化的首選是只做加法並讓 client 寬容讀取；需要破壞性變更時才開新版本，並提前公告、監控舊版流量。
- offset 分頁在翻頁途中資料變動時會重複或遺漏，而且越往後越慢；cursor（keyset）分頁記住上一頁最後一筆的排序鍵，cursor 對 client 應該不透明並經過簽章。
- Problem Details（RFC 9457）提供統一的錯誤格式，client 依 `type` 判斷錯誤種類，`detail` 只給人看，內部細節寫在 log 並用 `x-request-id` 串接。
- 逾時不代表失敗；idempotency key 讓 client 宣告「這是同一個操作」，server 必須原子地佔住 key、存下回應、比對請求指紋，並把 key 傳給下游。
- protobuf 以「欄位編號＋wire type」的 tag 和 varint 編碼資料，解碼器能跳過不認得的欄位，所以新增欄位向前相容，但欄位編號永遠不能重用。
- gRPC 把每次呼叫對應到一條 HTTP/2 stream，訊息加上 5 bytes 長度前綴，結果放在 trailers 的 `grpc-status`；瀏覽器無法直接呼叫，長連線需要 L7 或 client 端負載分散。
- deadline 是整個請求的期限，要以相對時間（例如 `grpc-timeout`）沿呼叫鏈傳遞並在程式中主動檢查，避免使用者離開後後端還在白做工，重試也必須在剩餘時間內進行。
- GraphQL 讓 client 精確選擇欄位、一次取得關聯資料，代價是 N+1 查詢、HTTP 快取困難、錯誤不在 status code 上，以及必須限制查詢成本並在每個 resolver 做授權。
- webhook 幾乎都是至少一次且可能亂序送達，接收端要驗簽章、用事件 id 去重、比較版本、快速回 2xx 並在背景處理。
- 選型依 client 而定：對外與需要快取用 REST，內部服務之間需要嚴格型別與 streaming 用 gRPC，前端畫面需要組合大量資料時考慮 GraphQL 或 BFF。

## 延伸問答

> [!question]- Q1. PUT 是 idempotent、POST 不是，那為什麼不把建立付款改成 PUT /v1/payments/{client 產生的 id}，就不需要 idempotency key 了？
> 這個方向在某些情境是可行的：client 自己產生付款 id，用 PUT 建立，重送時 server 發現同一個 id 已存在，就不會重複建立。它本質上和 idempotency key 是同一個想法，只是把「識別同一個操作」的值放進 URI。它適合資源本身就由 client 決定 id 的情況，例如 client 端離線建立的筆記同步到 server。
>
> 但用在付款上有幾個問題。第一，PUT 的語意是「用這份完整內容取代資源」，同一個 id 帶著不同金額重送時，按語意應該更新資源，而付款不能被更新成另一個金額；你仍然需要比對內容並拒絕，等於重新實作請求指紋。第二，付款 id 通常要由 server 產生，才能保證格式、不可猜測，並與金流供應商的紀錄對應。第三，「已存在時回什麼」仍需要定義：回原本的結果、回 409，還是回 200？最後還是要寫出一套和 idempotency key 等價的規則。所以業界多半保留 POST 的語意，另外用 header 承載 key，讓語意清楚分開。

> [!question]- Q2. 你在 production 看到同一個 Idempotency-Key 的兩個請求，相隔 20 毫秒，兩個都回了 201，扣款兩次。最可能的原因是什麼？
> 20 毫秒的間隔說明這是兩個幾乎同時到達的請求，而不是逾時後的重試。最可能的原因是 server 的「檢查 key」與「佔住 key」不是原子操作：兩個請求被分配到不同的 gunicorn worker 或不同主機，各自先查詢資料庫，都發現 key 不存在，於是都開始處理。這種 check-then-act 的競爭條件在單機測試時幾乎不會出現，只有在真實並行下才會發生。
>
> 確認方法是看兩個請求的 log 是否落在不同的 worker 或主機，以及儲存層的寫入順序。修正方法是讓佔位本身就是原子的：在資料庫的 `(user_id, idempotency_key)` 上建立 unique constraint，用 INSERT 佔位，INSERT 失敗就代表別人已經佔了；或使用 Redis 的 `SET key value NX`。只在單一 process 內用 thread lock（像實驗一那樣）無法保護多台主機的情況。另外也要檢查 key 的範圍是否正確，例如有沒有不小心把 key 和請求時間組合在一起，導致兩個請求得到不同的 key。

> [!question]- Q3. 手算：protobuf 訊息 `08 ac 02 12 03 6a 6c 70` 包含哪些欄位？
> 第一個 byte `08` 是 tag：0x08 右移 3 位得到欄位編號 1，最低 3 bit 是 0，所以是 field 1、wire type 0（varint）。接著讀 varint：`ac` 的最高位是 1，表示後面還有，取低 7 bit 得 0x2c＝44；`02` 的最高位是 0，是最後一個 byte，低 7 bit 是 2。varint 是低位在前，所以值是 44＋2×128＝300。
>
> 下一個 byte `12` 是 tag：0x12＝18，右移 3 位得 2，最低 3 bit 是 2，所以是 field 2、wire type 2（LEN）。長度是 `03`，接著 3 bytes `6a 6c 70` 是 ASCII 的 `jlp`。所以這則訊息是 field 1＝300、field 2＝"jlp"（假設 schema 說 field 2 是 string）。這題也說明了為什麼 300 要 2 bytes：它大於 127，超過一個 byte 能放的 7 bit。

> [!question]- Q4. 面試題：gRPC 的 deadline 為什麼用相對時間（grpc-timeout）而不是絕對時間傳遞？這樣不會有誤差嗎？
> 用絕對時間傳遞，前提是所有機器的時鐘完全同步。實際上即使用 NTP，不同主機之間的時鐘仍可能差幾毫秒到幾百毫秒，虛擬機暫停或時鐘跳動時差得更多。如果上游說「必須在 20:00:01.800 前完成」，而下游的時鐘快了 300 毫秒，下游會以為時間只剩一點點，提早放棄；時鐘慢的則會多做。這種錯誤很難除錯，因為它只在特定主機上出現。
>
> 用相對時間，每一層收到「還剩 720 毫秒」後，以自己的時鐘換算成本機的 deadline，時鐘的絕對誤差就不影響結果。代價是忽略了網路傳輸時間：請求在線上走的那幾毫秒沒有被扣掉，所以下游的 deadline 會比真實的稍晚一點。這個誤差通常只有同機房的 RTT 量級，遠小於時鐘差異，而且可以在往下傳時預留一點餘裕來抵銷，所以相對時間是更穩健的選擇。

> [!question]- Q5. 看 log 找原因：classroom 服務呼叫 reco 時，log 裡大量出現 DEADLINE_EXCEEDED，但 reco 自己的 log 顯示每個請求都在 20 毫秒內完成。可能是什麼？
> 第一個可能是 deadline 在到達 reco 之前就已經快用完了。如果上游傳下來的剩餘時間本來就很少（例如 classroom 在呼叫 reco 之前花了大部分預算在其他事情上），reco 處理得再快，回程時也已經超過期限；這時要看 classroom 送出時的 `grpc-timeout` 值，而不是 reco 的處理時間。第二個可能是時間花在排隊：reco 的 log 只記錄「開始處理到結束」，如果請求在 server 的 thread pool 或連線上排隊很久，這段時間不會出現在處理時間裡，要另外看 server 端的佇列長度與 worker 使用率。
>
> 第三個可能在網路與連線層：HTTP/2 連線剛建立、TLS 交握、或 client 端的負載分散把請求集中在少數幾條擁塞的連線上，都會增加延遲。確認方法是用分散式追蹤（trace）看同一個請求在各段的時間，比對 client 送出、server 收到、server 開始處理、server 回應這四個時間點。只看 server 的處理時間就下結論「reco 很快、問題不在我」，是這類事故最常見的誤判。

> [!question]- Q6. 設計取捨：app 團隊說「GraphQL 讓我們不用再等後端改 API」。導入 GraphQL 之前，你會要求哪些條件？
> 我會先確認導入的理由真的是 GraphQL 擅長的：畫面變動頻繁、client 種類多（web、iOS、Android 各自需要不同欄位）、資料之間的關聯複雜。如果只是一兩個畫面需要聚合，一個 BFF endpoint 的成本低得多，而且保留了 HTTP 快取與簡單的監控。GraphQL 把「決定要哪些資料」的權力交給 client，同時也把效能與安全的風險轉移到 server 端，這是需要明確接受的取捨。
>
> 如果要導入，至少要求四件事。第一，每個請求建立 DataLoader，關聯欄位都經過 batching，並在測試中檢查查詢次數，防止 N+1。第二，限制查詢深度、複雜度與分頁上限；對自家 app 最好只允許 persisted queries，也順便解決 CDN 快取的問題。第三，授權在 resolver 層級檢查，而不是只在 endpoint 入口。第四，監控要依 operation 名稱統計延遲與 `errors`，因為 HTTP status 幾乎永遠是 200。沒有這些配套，GraphQL 帶來的開發速度，很容易在第一次資料庫被拖垮時全部還回去。

> [!question]- Q7. 情境判斷：金流供應商的 webhook 先送來 payment.refunded，五秒後才送來 payment.succeeded。你的系統把這筆付款標記成「成功」，學生拿到了已退款的課程。怎麼修？
> 這是 webhook 亂序的典型後果：接收端依「收到的順序」套用事件，最後到的 succeeded 蓋掉了先到的 refunded。根本原因是把事件當成「命令」，而不是當成「狀態變化的通知」。修正有兩個層次。第一層是比較版本：如果事件帶有版本號、序號或發生時間，只接受比目前狀態新的事件，舊事件直接忽略，就像本章 webhook 程式裡的版本比較。也可以把狀態轉移寫成狀態機，規定「已退款」不能再轉回「成功」。
>
> 第二層更穩健：收到任何事件後，不直接相信事件內容，而是用事件中的付款 id 呼叫供應商的 API，查詢這筆付款目前的真實狀態，再據此更新。這樣不論事件亂序、重複或遺漏，結果都會收斂到供應商的最新狀態。再加上定期對帳，就能補上完全漏收的事件。最後也要修補已經造成的影響：找出所有「成功但其實已退款」的付款，收回課程權限並通知相關人員。

> [!question]- Q8. 為什麼很多公司對外提供 REST，內部卻用 gRPC？反過來對外提供 gRPC 有什麼困難？
> 對外 API 的 client 是你無法控制的外部開發者，他們使用各種語言、工具與環境，最需要的是「容易理解、容易除錯、到處都能呼叫」。REST 加 JSON 用 curl 就能測試，瀏覽器可以直接呼叫，錯誤用 HTTP status 表達，CDN 與快取天生支援，這些都降低了外部整合的門檻。內部服務則相反：雙方由同一個組織維護，可以共用 `.proto` 檔並產生程式碼，強型別能在編譯時抓到契約不一致，二進位編碼與 HTTP/2 多工降低延遲與 CPU，內建的 deadline 與 streaming 也正好是服務之間需要的。
>
> 對外提供 gRPC 的困難在於：瀏覽器無法直接呼叫，要架設 gRPC-Web 之類的轉換層；外部開發者要先取得 `.proto` 並學會產生程式碼；企業網路中的某些 proxy 對 HTTP/2 或 trailers 的支援不完整；除錯需要專門工具；HTTP 快取幾乎用不上。所以有些公司同時提供兩種介面，例如以 `.proto` 為唯一的契約來源，自動產生對外的 REST/JSON 轉換層，兼顧內部效率與外部易用性。

## 延伸閱讀

- Roy T. Fielding〈Architectural Styles and the Design of Network-based Software Architectures〉（2000 年博士論文）：REST 的原始定義，第 5 章
- RFC 9110〈HTTP Semantics〉：method 的 safe 與 idempotent 定義、status code 與 `Retry-After`
- RFC 9457〈Problem Details for HTTP APIs〉：統一錯誤格式
- RFC 8288〈Web Linking〉：`Link` header 與 `rel="next"` 分頁連結
- Protocol Buffers 官方文件〈Encoding〉與〈Language Guide (proto3)〉：wire format、欄位編號與相容性規則
- gRPC 官方文件〈gRPC over HTTP2〉（gRPC 原始碼庫中的 PROTOCOL-HTTP2 文件）與〈Deadlines〉：HTTP/2 對應方式與 `grpc-timeout`
- GraphQL Foundation〈GraphQL Specification〉，以及 DataLoader 專案的說明文件
- Google〈API Improvement Proposals（AIP）〉：資源導向設計、自訂方法與分頁的大型實務規範
