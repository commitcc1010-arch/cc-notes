---
chapter: 31
title: 從 Polling 到 Server-Sent Events
part: 7
---

# 第 31 章　從 Polling 到 Server-Sent Events

> [!abstract] 本章地圖
> **核心問題**：HTTP 天生是「client 問、server 答」，server 有新消息時，要怎麼盡快、便宜又可靠地交到瀏覽器手上？
>
> **你會學到**：
> - 用請求數與延遲的公式比較 short polling、long polling 與 SSE，並為一個功能選出合適的做法
> - 逐行讀懂 `text/event-stream` 的格式（`data`、`event`、`id`、`retry`、註解行），照規格寫出解析器
> - 說清楚 EventSource 的狀態機、重連規則與 `Last-Event-ID`，設計 server 端的補發與 reset
> - 解釋 HTTP/1.1 的每主機連線上限為什麼會讓第七個分頁卡住，以及 HTTP/2、HTTP/3 改變了什麼
> - 找出 proxy、CDN、壓縮與應用程式各層的緩衝，用 `X-Accel-Buffering`、`proxy_buffering off` 等設定修好「事件一批一批到」
> - 用 Python 標準函式庫在 127.0.0.1 上實作三種 server 與 client，實際量測請求數與延遲，並重現 proxy 緩衝
>
> **前置知識**：第 10 章（TCP 連線與 RST）、第 20 章（HTTP/1.1 的 keep-alive、Content-Length 與 chunked）、第 22 章（HTTP/2 的 stream 與多工）、第 25 章（reverse proxy 的角色）

## 31.1 故事：等候室裡的「老師已上線」

聲聲 Live 的學生在上課前五分鐘會進入「等候室」頁面，畫面上寫著「美咲老師還沒進入教室」。老師按下「開始上課」後，每個學生的頁面要自動切換到教室。舊版的做法很直覺：頁面上的 JavaScript 每 2 秒呼叫一次 `GET /api/rooms/7/status`，問 server「老師來了沒」。晚上八點前後，全站同時大約有 6,000 名學生待在各自的等候室，光是這支 API 每秒就有 3,000 個請求，佔了 API 尖峰流量的四成，而其中絕大多數的答案都是「還沒」。

客服也收到另一種抱怨：「老師已經開始講話了，我的畫面過了快兩秒才跳進教室。」產品經理問小晴能不能把間隔改成 0.5 秒。小晴算了一下：那會變成每秒 12,000 個請求，API 主機要加三倍。阿德建議改用 **Server-Sent Events**（SSE，伺服器送出事件，讓 server 在一條一直不結束的 HTTP 回應裡持續推送訊息），由 ASGI 的即時服務 `rt.shengsheng.example` 負責。小晴花兩天做完，staging 上一切正常：老師一按按鈕，學生畫面幾乎同時跳轉。

上線第一晚卻出現三個怪現象。第一，有些學生要等十幾秒才跳轉，而且跳轉時，之前的好幾個通知（「老師進入」「白板已開啟」「講義第 1 頁」）一起湧進來。第二，監控顯示每條 SSE 連線大約每 60 秒就斷一次，接著重連。第三，晚上九點部署新版即時服務時，有一群學生漏掉了「小測驗開始」的通知，一直停在舊畫面。另外還有一位老師回報：開了七個後台分頁之後，第七個分頁完全載不出來。

```text
 學生瀏覽器 ──HTTPS──► rt 的 L4 LB 203.0.113.40 ──► nginx（TLS 終結）──► uvicorn（ASGI 即時服務）
     │                  （不解密，只轉送 TCP）        │                      │
     │ ④ 七個分頁各開一條                             │ ① proxy buffering    │ ③ 部署時連線全斷，
     │   SSE，HTTP/1.1                                │   把事件攢著不送     │   重連後沒有補發
     │   上限 6 條，                                  │ ② 60 秒沒從後端      │   斷線期間的事件
     │   第七條排隊                                   │   讀到資料就切斷     │
```

阿德在事後檢討時畫了這張圖，把四個問題標在發生的位置。① 在 nginx：預設會把 upstream 的回應先放進緩衝區，小小的事件攢不滿緩衝區，就一直不送出去。② 也在 nginx：`proxy_read_timeout` 預設 60 秒，連續 60 秒沒從後端讀到任何 bytes，就把這條請求當成逾時而切斷；路徑上的 LB 也有自己的閒置逾時，只是這次先到期的是 nginx。③ 在即時服務本身：重連的瀏覽器帶來了「我最後收到第幾號事件」的資訊，但 server 沒有理會，斷線期間發生的事件就這樣不見了。④ 在瀏覽器：HTTP/1.1 對同一個主機最多同時開大約 6 條連線，每個分頁的 SSE 各佔一條，第七個分頁只能排隊。

這一章就是要讓你看懂這張圖。我們會先從最簡單的 short polling 開始，算出它的請求數與延遲；再看 long polling 怎麼把延遲降下來、又帶來什麼新問題；然後逐行拆解 SSE 的格式、重連與補發機制，最後處理 HTTP 版本與 proxy 緩衝這些「規格沒寫、但上線一定會遇到」的問題。章末的動手做會在你的電腦上實作三種 server，量測它們的差別，並重現 nginx 緩衝讓 SSE 卡住的現象。

## 31.2 HTTP 只會一問一答：server 想主動說話怎麼辦

HTTP 是一個**請求／回應**（request/response）協定：一定是 client 先送請求，server 才回應，一個請求換一個回應（第 20 章）。這個模型叫做 **pull**（拉）：資料要靠 client 去拉。可是很多功能的資料是 server 先知道的：老師上線、聊天新訊息、直播開始、AI 家教逐字產生的回饋、背景轉檔完成。這種「server 有事要說」的需求叫做 **push**（推）。在 HTTP 上做 push，只有三條基本路線。

**第一條：一直問。** client 每隔一段時間就發一次請求，這是 **short polling**（短輪詢，簡稱 polling）。**第二條：問了先別答。** client 發出請求，server 若沒有新消息就把請求「掛著」，等到有消息或逾時才回應，client 一收到回應就立刻再問，這是 **long polling**（長輪詢）。**第三條：一次問、一直答。** client 發一個請求，server 回應的 header 送出後，body 永遠不結束，有消息就往 body 裡寫一段，這就是 SSE 的做法，也叫 **HTTP streaming**（串流回應）。

```text
 時間 ──────────────────────────────────────────────────────────────►
 server 端事件：            ▲E1                     ▲E2
                            │                       │
 short polling   ●───○  ●───○  ●───◉  ●───○  ●───○  ●───○  ●───◉     每格固定問一次
                 （○＝沒有變化，◉＝帶回事件；E1 要等到下一次輪詢才知道）

 long polling    ●──────────────◉●──────────────────────◉●─────── …  沒事件就掛著
                                ↑ E1 一發生就回應，client 立刻再問

 SSE             ●══════════════◉═══════════════════════◉═════════ …  一個回應、永不結束
                 （header 只送一次，之後每個事件只是 body 裡的幾行文字）
```

這張時間軸把三種做法放在同一組事件下比較。● 是 client 送出請求，線段是請求「在路上或被掛著」的時間。short polling 的請求數由時間決定，不管有沒有事件，每格都要問一次，所以大部分回應都是 ○；而事件 E1 發生在兩次輪詢之間，要等到下一次輪詢才會被發現。long polling 的請求數由事件數決定：每個事件換一次回應與一次新請求，延遲幾乎只剩網路傳輸時間。SSE 則只有一個請求，事件來了就直接寫進同一個回應。

三種做法都只用普通的 HTTP，不需要任何協定升級，這是它們和第 32 章 WebSocket 最大的不同：一般的 proxy、CDN、防火牆、驗證機制與 log 都照常運作。代價是它們的資料流本質上都是**單向**的：server 往 client 推，client 要說話還是得另外發一般的 HTTP 請求。對等候室、通知、進度條、股價、log 串流、LLM 逐字回應這類「server 說得多、client 說得少」的功能，這個限制完全不是問題。

| 做法 | 請求數取決於 | 平均延遲 | server 要同時保持 | 典型用途 |
|---|---|---|---|---|
| short polling | 時間：人數 × 時長 ÷ 間隔 | 約間隔的一半，最差一個間隔 | 幾乎不用（請求很短） | 低頻率狀態查詢、可被 CDN 快取的公開資料 |
| long polling | 事件數＋逾時次數 | 約一個單程傳輸，空檔中的事件多一個 RTT | 每個 client 一個掛著的請求 | 舊瀏覽器相容、聊天的後備方案 |
| SSE | 每個 client 一次（加上重連） | 約一個單程傳輸 | 每個 client 一條長連線 | 通知、即時看板、進度、LLM token 串流 |

這張表先給出結論，後面三節分別推導每一格的數字。注意「server 要同時保持」這一欄：polling 把成本放在請求數，long polling 與 SSE 把成本放在同時存在的連線數，選型就是在這兩種成本之間取捨。

## 31.3 Short polling：每隔一段時間問一次

short polling 的實作簡單到幾乎不需要解釋：client 設一個計時器，每 P 秒呼叫一次 API，API 照常查資料庫並回應。它的成本可以直接算出來。N 個 client、每 P 秒一次、持續 T 秒，總請求數就是 N × T ÷ P；聲聲 Live 的等候室是 6,000 × 1 ÷ 2 ＝ 每秒 3,000 個請求。延遲也能算：事件發生的時刻相對於輪詢時刻是隨機的，平均要等半個間隔才會被下一次輪詢看到，最差要等一整個間隔，再加上一個 RTT 的往返。所以 2 秒輪詢的平均延遲約 1 秒、最差約 2 秒，這正是客服抱怨的「快兩秒才跳」。

```text
 Client（學生瀏覽器）                     Server（API）
   │── GET /api/rooms/7/status ─────────────►│  查 DB：老師還沒來
   │◄──────── 200 {"teacher":"waiting"} ─────│
   │        （等 2 秒）                       │
   │── GET /api/rooms/7/status ─────────────►│
   │◄──────── 200 {"teacher":"waiting"} ─────│
   │        （等 2 秒）    ← 美咲老師在這裡按下「開始上課」
   │── GET /api/rooms/7/status ─────────────►│
   │◄──────── 200 {"teacher":"online"} ──────│  學生終於知道：已經晚了約 1.3 秒
```

這張時序圖顯示 short polling 的兩個問題同時存在。前兩次請求是純粹的浪費：client 送出完整的 HTTP 請求（含 cookie，常常有好幾百 bytes），server 驗證 session、查資料庫、組回應，最後只得到「沒有變化」。第三次請求帶回了事件，但事件是在等待期間發生的，學生白白多等了一段時間。把間隔縮短能降低延遲，代價是請求數等比例上升；把間隔拉長能省資源，代價是延遲等比例上升。short polling 沒有辦法同時改善兩者。

降低 short polling 成本的技巧有幾個，都值得知道。第一是**條件請求**：回應帶 `ETag`，下一次請求帶 `If-None-Match`，沒變化時 server 回 `304 Not Modified` 且不帶 body（第 21 章）。這省下的是回應的 body 與產生 body 的工夫，但請求數與 header 一個也沒少。第二是**讓 CDN 吸收**：如果被輪詢的資料是公開的、所有人都一樣（例如「今晚的講座名單」），可以讓回應帶 `Cache-Control: public, max-age=2`，6,000 個 client 的輪詢大多由 CDN edge 回答，origin 每 2 秒只需回答每個 edge 一次。這是 short polling 唯一能「越多人越便宜」的情境，SSE 和 long polling 都做不到。

第三是**加入隨機抖動**（jitter）。如果所有頁面都在整點同時打開、用同樣的間隔，請求會整齊地一波一波湧入；在間隔上加 ±10% 的隨機值，可以把尖峰攤平。第四是**依情境調整頻率**：分頁切到背景時（瀏覽器的 Page Visibility API 會告訴你），把間隔拉長或乾脆停止；距離上課時間還很久時用 10 秒，開課前一分鐘再改成 2 秒。這些技巧讓 short polling 在很多情境下其實夠用：對「每幾分鐘才變一次、晚幾秒也沒關係」的資料，short polling 是最簡單、最好除錯、最不怕中間設備的選擇。

> [!warning] 常見誤解
> 「把 polling 間隔從 2 秒改成 0.5 秒，延遲就會降到 0.25 秒，很划算。」延遲確實會降，但請求數是原本的 4 倍，而且這些請求大多數都是「沒有變化」。更隱蔽的成本在 client：手機每次發請求都可能喚醒無線電，頻繁輪詢會明顯耗電。間隔要縮到一秒以下時，就該考慮 long polling 或 SSE 了。

## 31.4 Long polling：沒有消息就先別回

long polling 的想法是：既然大部分輪詢的答案都是「沒有變化」，那 server 收到請求時，如果沒有新消息，就**先不要回應**，把請求掛著，等到有消息再回；如果一直沒消息，就等到一個逾時時間（例如 25 秒）回一個空結果。client 收到任何回應後立刻再發下一個請求。這樣一來，每個 client 幾乎隨時都有一個請求「埋伏」在 server 上，事件一發生就能立刻回應。這個技巧在 2000 年代被大量使用，當時常被統稱為 **Comet**。

```text
 Client                                         Server
   │── GET /rooms/7/updates?since=40 ──────────────►│  沒有 id > 40 的事件：掛著
   │                                                │  （最多掛 25 秒）
   │                                                │  ← 老師上線，產生事件 41
   │◄──────── 200 {"events":[41], "cursor":41} ─────│  立刻回應
   │── GET /rooms/7/updates?since=41 ──────────────►│  ← 空檔中（client 還在路上）
   │                                                │    產生了事件 42、43
   │◄──────── 200 {"events":[42,43],"cursor":43} ───│  cursor 落後：馬上回，一次帶兩則
   │── GET /rooms/7/updates?since=43 ──────────────►│  掛著……
   │                                                │  25 秒都沒有事件
   │◄──────── 200 {"events":[], "cursor":43} ───────│  逾時，回空結果
   │── GET /rooms/7/updates?since=43 ──────────────►│  再掛著……
```

這張圖裡最重要的是 `since` 參數，也就是 **cursor**（游標，代表「我已經收到哪一號為止」）。一次回應與下一個請求之間永遠有一段**空檔**：回應要花半個 RTT 傳到 client，client 處理完再發請求，又要半個 RTT 才到 server。這段時間裡發生的事件（圖中的 42、43），server 不可能用「掛著的請求」送出，因為根本沒有請求掛著。如果 server 只回「此刻之後」的新事件，這兩則就永遠消失了。帶著 cursor，server 一看就知道 client 落後了，立刻把漏掉的事件一次補齊。沒有 cursor 的 long polling 是會掉訊息的，這是初學者最常寫錯的地方。

long polling 的成本模型和 short polling 不同。請求數約等於「事件數＋逾時次數」：沒有事件時，每個 client 每 25 秒一個請求；有事件時，每個事件換一次回應。延遲大約是單程傳輸時間，事件落在空檔裡時再多一個 RTT。代價是 server 必須**同時保持**大量掛著的請求：6,000 名學生就有大約 6,000 個進行中的請求。如果後端是傳統的同步 WSGI worker（每個 worker 一次只能處理一個請求，第 41、43 章），6,000 個掛著的請求就要 6,000 個 worker 或 thread，這在 Flask＋gunicorn sync worker 的架構下根本不可行。這也是即時功能通常放在 asyncio 的 ASGI 服務（第 42 章）的原因：一個 event loop 可以掛著上萬個請求，每個只佔一點記憶體。

逾時時間要怎麼選？答案是**比整條路徑上最短的閒置逾時再短一些**。請求從瀏覽器出發，要經過 CDN、LB、nginx，每一層都有自己的「多久沒收到回應就放棄」的設定。nginx 的 `proxy_read_timeout` 預設 60 秒，許多雲端 LB 的閒置逾時預設也是 60 秒（依產品而定，可調），瀏覽器的 fetch 本身則通常沒有逾時。如果 server 掛 90 秒，請求會在第 60 秒被中間的 nginx 以 504 切斷，client 看到的是錯誤而不是空結果，還可能觸發錯誤重試與告警。所以實務上常用 20 到 30 秒。

long polling 還有一個不明顯的陷阱：**驚群**（thundering herd，一大群等待者被同一個事件同時喚醒）。假設全站公告「今晚九點維修」這個事件同時送給 6,000 個 client，6,000 個掛著的請求會在同一毫秒回應，6,000 個新請求又在幾十毫秒後同時湧入，每一個都要重新驗證 session、查一次 cursor。對 short polling 來說，請求是均勻分散的；對 long polling 來說，廣播事件會製造整齊的尖峰。緩解方法是讓 client 收到回應後等一個小的隨機延遲（例如 0 到 500 毫秒）再發下一個請求，以及讓「重新掛上」這個動作盡量便宜（不要每次都查資料庫，而是查記憶體裡的事件序號）。

> [!tip]
> long polling 的錯誤處理要和逾時分開。逾時回空結果是正常流程，client 應該**立刻**重發；網路錯誤或 5xx 則代表 server 有問題，client 應該用**指數退避加抖動**（exponential backoff with jitter：第一次等 1 秒，接著 2、4、8 秒，每次再加隨機值，並設上限）。如果兩者都立刻重發，server 一出錯，所有 client 就會以最快速度猛打，讓 server 更難恢復。

## 31.5 SSE 的格式：一條不會結束的文字回應

SSE 是 WHATWG HTML 標準的一部分，由兩件事組成：一個 **`text/event-stream` 格式**（規定 server 怎麼在回應 body 裡寫事件），和一個瀏覽器 API **`EventSource`**（規定瀏覽器怎麼連線、解析與重連，下一節介紹）。先看格式。SSE 的回應就是一個普通的 HTTP 200 回應，`Content-Type` 必須是 `text/event-stream`，body 是 UTF-8 文字，一行一行地寫，**永遠不結束**；server 想送事件時，就往 body 裡寫幾行文字並立刻送出。

```text
 HTTP/1.1 200 OK
 Content-Type: text/event-stream       ← 必須是這個 MIME type，否則 EventSource 直接放棄
 Cache-Control: no-cache               ← 不准任何快取存這個回應
 X-Accel-Buffering: no                 ← 給 nginx 的提示：不要緩衝（31.9 節）
 Transfer-Encoding: chunked            ← HTTP/1.1 下長度未知；HTTP/2 改用 DATA frame
                                       ← 空行：header 結束，以下是 body（永不結束）
 : connected␊                          ← 註解行：冒號開頭，瀏覽器直接忽略
 ␊
 retry: 3000␊                          ← 告訴瀏覽器：斷線後等 3000 ms 再重連
 ␊
 id: 41␊                               ┐
 event: teacher_online␊                │ 一個事件 ＝ 若干行「欄位名: 值」
 data: {"room":7,"teacher":"美咲"}␊    │
 ␊                                     ┘ 空行 ＝ 這個事件結束，交給 JavaScript（dispatch）
 data: 第一行␊                         ┐ 同一個事件可以有多行 data，
 data: 第二行␊                         │ 瀏覽器用換行字元把它們接起來
 ␊                                     ┘
 : hb␊                                 ← 心跳也是註解行，只是為了讓連線上有流量
 ␊
```

圖中的 ␊ 代表換行字元。從上往下讀：header 和一般回應一樣，只是 `Content-Type` 是 `text/event-stream`，而且沒有 `Content-Length`，因為長度永遠未知。header 之後的 body 由一行一行的文字組成，每一行要嘛是註解（以冒號開頭），要嘛是「欄位名、冒號、值」。**空行**是整個格式的關鍵：它表示「到這裡為止的欄位組成一個事件」，瀏覽器在看到空行時才把事件交給 JavaScript。所以 server 每送一個事件，結尾一定要有兩個換行（一個結束最後一行、一個是空行），少一個，事件就會停在瀏覽器的解析器裡，看起來像沒收到。

行尾可以是 CRLF、LF 或單獨的 CR，三種都算一行結束。冒號後面如果緊接一個空白，這**一個**空白會被去掉，所以 `data: hello` 與 `data:hello` 的值都是 `hello`，但 `data:  hello`（兩個空白）的值是「一個空白加 hello」。一行如果沒有冒號，整行都是欄位名、值是空字串。規格只認得四個欄位名，其他一律忽略，這讓格式可以向後相容地擴充，也意味著打錯字（例如 `dta:`）不會報錯，只會默默無效。

| 欄位 | 作用 | 規則與細節 | 常見錯誤 |
|---|---|---|---|
| `data` | 事件內容 | 每行的值後面加一個換行接進 data 緩衝區；dispatch 時去掉最後一個換行；緩衝區是空的就不送出事件 | 以為一個事件只能有一行；JSON 裡的換行沒處理導致事件被切開 |
| `event` | 事件類型 | 沒寫就是 `message`；寫了就要用 `addEventListener("類型")` 接，`onmessage` 收不到 | 送了 `event: update` 卻只寫 `onmessage` |
| `id` | 事件編號 | 設定瀏覽器的「最後事件 ID」，斷線重連時放進 `Last-Event-ID` header；值含 NULL 字元則忽略；空值會清除 | 以為 id 只屬於這一個事件；其實會一直沿用到下一個 id |
| `retry` | 重連等待（毫秒） | 值必須全是 ASCII 數字，否則整行忽略 | 寫成 `retry: 3s`，結果無效 |
| `:` 開頭 | 註解 | 完全忽略，不觸發任何事件 | 以為註解可以拿來傳資料 |

這張表裡最容易誤解的是 `id`。`id` 不是「這個事件的屬性」，而是設定一個**會持續保留**的狀態：瀏覽器記住最後看到的 id，之後沒有 `id` 欄位的事件，`event.lastEventId` 仍然是上一次的值。另一個重點是 `data` 的拼接規則：一個事件最後被交出去時，所有 `data` 行的值以換行連在一起。所以要送 JSON，最簡單的做法是把 JSON 序列化成單一行（`json.dumps` 預設就不會產生換行）；要送多行文字，就每行一個 `data:`。

還有兩個規格上的硬規定。第一，編碼固定是 UTF-8，瀏覽器不看 `charset` 參數，開頭若有 BOM 會被丟掉。第二，連線結束時，最後一個「還沒遇到空行」的事件會被丟棄，不會被送出。這個規定保護了 client：如果連線在 server 寫到一半時斷掉，瀏覽器不會把半個事件當成完整的事件交出去。

規格的解析演算法其實很短，用 Python 照著寫一遍是理解它最快的方式。下面這段程式逐行處理一段刻意設計過的串流，包含多行 data、CRLF、沒有空白的冒號、沒有 data 的事件、打錯字的欄位、含 NULL 的 id、不合法的 retry，以及沒有空行結尾的半個事件：

```python
import re

# 依 WHATWG HTML 規格的 event stream 解析規則，逐行處理（行尾可以是 CRLF、LF 或 CR）
def parse_stream(raw: bytes):
    text = raw.decode("utf-8", errors="replace")    # 規格固定 UTF-8，不看 charset
    if text.startswith("\ufeff"):
        text = text[1:]                              # 開頭的 BOM 要丟掉
    lines = re.split(r"\r\n|\r|\n", text)
    data, event_type, last_id, retry = [], "", "", None
    for line in lines:
        if line == "":                               # 空行：把累積的欄位組成一個事件送出
            if data:
                yield {"type": event_type or "message", "data": "\n".join(data), "lastEventId": last_id}
            data, event_type = [], ""                # 注意 last_id 不清空，會一直沿用
            continue
        if line.startswith(":"):
            yield {"comment": line[1:].strip()}      # 註解行：瀏覽器直接忽略，這裡印出來觀察
            continue
        name, sep, value = line.partition(":")
        if sep and value.startswith(" "):
            value = value[1:]                        # 冒號後只去掉「一個」空白
        if name == "data":
            data.append(value)
        elif name == "event":
            event_type = value
        elif name == "id":
            if "\0" not in value:
                last_id = value                      # 含 NULL 的 id 整行忽略
        elif name == "retry":
            if value.isascii() and value.isdigit():
                retry = int(value)
                yield {"retry": retry}
        # 其他欄位名稱（包括打錯字的）一律忽略


stream = (
    b": welcome\n\n"
    b"retry: 3000\n"
    b"id: 41\nevent: teacher_online\ndata: {\"teacher\": \"\xe7\xbe\x8e\xe5\x92\xb2\"}\n\n"
    b"data: line one\r\ndata:line two\r\ndata:  indented\r\n\r\n"
    b"event: no_data_here\n\n"
    b"id: 42\ndata\n\n"
    b"dta: typo field\nid: bad\x00id\ndata: after bad id\n\n"
    b"retry: 2s\ndata: incomplete event without blank line"
)
results = list(parse_stream(stream))
for item in results:
    print(item)
messages = [r for r in results if "data" in r]
assert messages[0]["type"] == "teacher_online" and messages[0]["lastEventId"] == "41"
assert messages[1]["data"] == "line one\nline two\n indented"
assert messages[2] == {"type": "message", "data": "", "lastEventId": "42"}
assert messages[3]["lastEventId"] == "42" and len(messages) == 4
```

```text
{'comment': 'welcome'}
{'retry': 3000}
{'type': 'teacher_online', 'data': '{"teacher": "美咲"}', 'lastEventId': '41'}
{'type': 'message', 'data': 'line one\nline two\n indented', 'lastEventId': '41'}
{'type': 'message', 'data': '', 'lastEventId': '42'}
{'type': 'message', 'data': 'after bad id', 'lastEventId': '42'}
```

逐行對照輸出。第 3 行是一個完整的具名事件，類型 `teacher_online`、id 41，`data` 裡的中文以 UTF-8 正確解出。第 4 行示範三件事：CRLF 行尾照樣被當成換行；`data:line two` 沒有空白也沒關係；`data:  indented` 只去掉一個空白，所以值保留了一個前導空白。它沒有自己的 `id`，`lastEventId` 沿用 41，這就是「id 會持續保留」的意思。輸入裡的 `event: no_data_here` 沒有任何 data，所以什麼都沒送出；而只有一個 `data`（沒有冒號）的那個事件則送出了一個 data 為空字串的事件，因為 data 緩衝區裡有一個空行。

接下來，打錯字的 `dta:` 被忽略；`id: bad\x00id` 因為含 NULL 而整行無效，所以 `after bad id` 這個事件的 `lastEventId` 仍是 42。最後兩行：`retry: 2s` 不是純數字，被忽略（輸出裡沒有第二個 retry）；而沒有空行結尾的半個事件被丟棄，總共只送出 4 個事件。這段解析器之後在動手做的 client 裡還會以簡化的形式出現。

## 31.6 EventSource：連線、重連與 Last-Event-ID

瀏覽器端的 `EventSource` 把連線管理全部包起來了。你只要 `new EventSource(url)`，瀏覽器就會送出一個 `GET` 請求（帶 `Accept: text/event-stream`），一邊收一邊解析，每遇到空行就觸發一個事件；連線斷了，它會自動重連。這份「自動」正是 SSE 比自己用 fetch 讀串流方便的地方，也是它和 WebSocket 的重要差別：WebSocket 斷線後怎麼重連、要不要補發，全部要自己寫（第 32、33 章）。

```javascript
const es = new EventSource("https://rt.shengsheng.example/rooms/7/events", { withCredentials: true });
es.addEventListener("teacher_online", (e) => enterClassroom(JSON.parse(e.data)));
es.addEventListener("reset", () => { es.close(); refetchRoomState(); });   // 補不回來時重抓全貌
es.onmessage = (e) => console.log("沒有 event 欄位的事件", e.lastEventId, e.data);
es.onerror = () => console.log("readyState =", es.readyState);             // 0：重連中；2：已放棄
```

這五行就是等候室前端的全部連線邏輯。`withCredentials: true` 讓跨來源請求帶上 cookie，因為 `rt.shengsheng.example` 和網頁所在的 `www.shengsheng.example` 不同來源，要走 CORS（第 23 章），server 必須回 `Access-Control-Allow-Origin` 指定確切來源與 `Access-Control-Allow-Credentials: true`。`addEventListener` 接具名事件，`onmessage` 只接沒有 `event` 欄位的事件。`onerror` 不代表「放棄了」：它在每次斷線時都會觸發，要看 `readyState` 才知道瀏覽器是在重連（0）還是已經關閉（2）。

```text
                     new EventSource(url)
                             │
                             ▼
              ┌──────────────────────────────┐
     ┌───────►│ CONNECTING（readyState = 0） │
     │        └──────────────────────────────┘
     │                 │                │
     │      回應 200 且 │                │ 回應不是 200（例如 204、401、500），
     │  text/event-    │                │ 或 Content-Type 不對
     │  stream         ▼                ▼
     │        ┌───────────────┐   ┌─────────────────────┐
     │        │ OPEN（1）     │   │ CLOSED（2）          │◄── 程式呼叫 es.close()
     │        │ 觸發 open，   │   │ 觸發 error，不再重連 │
     │        │ 收事件        │   └─────────────────────┘
     │        └───────────────┘
     │                 │ 連線中斷或 server 結束回應
     │                 ▼
     │        觸發 error，等待 retry 毫秒
     │        （瀏覽器可以再加上退避時間）
     └──────── 重新送 GET，帶 Last-Event-ID
```

這張狀態機回答了「什麼時候會重連、什麼時候不會」。只要回應曾經成功（200 加上正確的 `Content-Type`），之後不管是網路中斷還是 server 正常結束回應，瀏覽器都會等待 **reconnection time**（重連等待時間）後重連。這個時間的初始值由瀏覽器決定，通常是幾秒；server 可以用 `retry:` 欄位改掉它；規格也允許瀏覽器在連續失敗時自行加上指數退避。反過來，如果回應的狀態碼不是 200，或 `Content-Type` 不是 `text/event-stream`，瀏覽器會直接進入 CLOSED，不再重試。

這個規則給了 server 兩種截然不同的工具。想讓 client「稍後再連」（例如部署），就正常結束回應，或直接關閉連線，client 會在 retry 後回來。想讓 client「永遠別再連了」（例如課程結束、使用者已登出），就回 **204 No Content**。一個常見的事故是：驗證過期時 server 回 401，前端以為 EventSource 會自己重試，結果它直接 CLOSED，頁面從此收不到任何更新，而且沒有任何錯誤畫面。正確的做法是在 `onerror` 裡檢查 `readyState === 2`，若是就由前端程式決定要不要重新登入、重新建立 EventSource。

重連時最重要的資訊是 **`Last-Event-ID`** 這個 request header：如果瀏覽器之前收過帶 `id` 的事件，重連請求就會自動帶上最後那個 id。server 看到它，就能把斷線期間錯過的事件補發，這就是故事中問題 ③ 的解法。

```text
 Browser（EventSource）                         rt 即時服務
   │── GET /rooms/7/events ───────────────────────►│
   │◄── 200 text/event-stream ─────────────────────│
   │◄── retry: 3000 ───────────────────────────────│
   │◄── id: 41  event: teacher_online ─────────────│
   │◄── id: 42  event: whiteboard ─────────────────│
   │                                    ✕ 部署：舊 process 關閉所有連線
   │   readyState=0，觸發 error，等 3000 ms         │  ← 這期間產生事件 43、44
   │── GET /rooms/7/events ───────────────────────►│
   │   Last-Event-ID: 42                           │  新 process 查事件紀錄：
   │◄── 200 text/event-stream ─────────────────────│  42 之後還有 43、44
   │◄── id: 43  event: slide ──────────────────────│  先補發
   │◄── id: 44  event: quiz_start ─────────────────│
   │◄── id: 45 …（之後是即時事件）──────────────────│
```

這張時序圖要注意三點。第一，`Last-Event-ID` 是**瀏覽器自動帶的**，前端程式不用做任何事；但 server **必須自己實作**補發，規格只負責把 id 送回來。第二，補發要靠一份**事件紀錄**：server 必須能回答「42 之後有哪些事件」，所以事件不能只存在某個 process 的記憶體裡，至少要存在所有實例都能讀到的地方（例如 Redis Streams 或資料庫的流水號，第 33 章會設計）；部署時舊 process 被關掉，新 process 必須查得到同一份紀錄。第三，紀錄不可能無限保存，一定有個保留範圍。

當 client 帶來的 id 已經比保留範圍還舊（例如學生的筆電睡眠了兩小時才醒來），server 就補不回來了。這時最誠實的做法是送一個特殊事件（本章用 `event: reset`），告訴前端「你漏掉的太多，請直接重抓完整狀態」，前端收到後呼叫 API 取得教室的最新快照。這個「增量更新＋快照重設」的組合，是所有可靠推送系統的共同骨架：增量讓平常的更新便宜，快照讓任何落後的 client 都能回到正確狀態。

設計 id 時有幾個實務選擇。最簡單的是每個頻道（例如每間教室）一個遞增整數，server 用「大於 Last-Event-ID 的事件」補發。如果事件來自多個來源，可以用事件紀錄系統給的位移值，或「時間戳記加序號」的字串；id 對瀏覽器來說只是不透明的字串，只要 server 能從它找到續傳點就行。要避免的是用「每條連線自己的計數器」當 id：重連到另一個實例時計數器從 1 重來，補發就會錯亂。另外，補發與即時事件之間要避免重複：先記下「此刻的最新 id」，補發到這裡為止，再從這個 id 之後開始訂閱即時事件；前端也應該依 id 去重，因為 at-least-once 的系統總有可能送兩次（第 33 章）。

EventSource 也有明確的限制。它只能發 `GET`，不能帶自訂 header（所以不能放 `Authorization: Bearer …`），也不能帶 request body。驗證通常靠 cookie（同站或搭配 `withCredentials`）；把 token 放在 URL query string 雖然可行，但 URL 會出現在 access log、瀏覽器歷史與 proxy 的紀錄中，Rita 的規範是只允許放**一次性、幾十秒內過期的短效票券**，由 server 換成連線後立刻作廢。需要 POST、需要自訂 header 時，前端改用 `fetch()` 讀取 response body 的串流，自己照 31.5 節的規則解析，但重連與 `Last-Event-ID` 就得自己實作。

> [!note] 2026 現況
> 截至 2026 年 10 月，SSE 定義在 WHATWG HTML Living Standard，所有主流瀏覽器都支援 `EventSource`。近年 SSE 因為 LLM 的逐字（token）串流而重新普及：許多 LLM API 以 `text/event-stream` 格式回傳生成中的文字，但因為請求要用 POST 帶 prompt，瀏覽器端通常用 fetch 讀串流再自行解析，而不是用 `EventSource`。各家 API 在 SSE 之上的事件命名與結束訊號不盡相同，要以各自的文件為準。

## 31.7 心跳：長連線最怕安靜

故事中的問題 ② 是「每 60 秒斷一次」。原因是等候室大部分時間都很安靜：老師可能十分鐘後才上線，這十分鐘裡 SSE 連線上沒有任何 bytes 流動。路徑上的每一個中間設備都在追蹤連線，而它們都有**閒置逾時**（idle timeout）：nginx 的 `proxy_read_timeout`（預設 60 秒，指的是兩次從 upstream 讀到資料之間的最長間隔）、雲端 LB 的閒置逾時、CDN 的串流逾時、NAT 與防火牆的連線表逾時（第 7 章）。任何一個到期，連線就被切斷；切斷的方式有時是乾淨的 FIN 或 RST，有時是默默把狀態刪掉，兩端都不知道（第 10 章的半開連線）。

解法是**心跳**（heartbeat）：server 定期送一行註解，例如每 15 秒送一次 `: hb` 加空行。註解行在規格上會被瀏覽器完全忽略，不會觸發任何 JavaScript 事件，但對中間設備來說，連線上有 bytes 在流動，閒置計時器就會重設。心跳的間隔要短於路徑上**最短**的閒置逾時，並留足餘量；常見的選擇是 15 到 30 秒。成本非常低：`: hb\n\n` 只有 6 bytes，6,000 條連線每 15 秒一次，每秒只有 400 次小寫入。

心跳的第二個用途是**偵測死掉的 client**，這一點常被忽略。TCP 連線上如果沒有資料要送，server 不會知道 client 已經消失（筆電闔上、手機進了電梯）；server 只有在**寫入**時，才有機會從錯誤中得知連線已斷（第 10 章：寫入成功只代表核心收下，要等後續的 RST 或重傳逾時才會報錯）。沒有心跳的 SSE server，會累積大量「其實早就沒人在看」的連線，佔著記憶體與 fd。有了心跳，每次寫入都是一次探測，死連線最慢在幾個心跳週期內就會被發現並清掉。TCP keepalive 也能探測，但它的預設間隔通常長達兩小時，而且不會被應用層的中間設備（例如 nginx）視為流量，所以不能取代應用層心跳。

| 計時器 | 在哪一層 | 常見預設 | 心跳要怎麼配合 |
|---|---|---|---|
| `proxy_read_timeout` | nginx 等 reverse proxy | 60 秒 | 心跳間隔遠小於它；或對 SSE 路徑調長 |
| LB 閒置逾時 | 雲端或硬體 LB | 常見 60 秒（依產品而定） | 心跳間隔小於它 |
| CDN 串流／回應逾時 | CDN edge | 依產品而定 | 確認 CDN 是否支援長時間串流，或讓 SSE 繞過 CDN |
| NAT／防火牆連線表 | 家用路由器、電信 CGNAT | 幾分鐘到幾十分鐘不等 | 15–30 秒的心跳綽綽有餘 |
| `retry` | 瀏覽器 | 瀏覽器自訂，通常幾秒 | 斷線後等多久重連，由 server 用 `retry:` 指定 |

這張表把一條 SSE 連線上的計時器全列出來。實務上的設定順序是：先查清楚路徑上最短的閒置逾時，再把心跳間隔定在它的一半以下，最後把 nginx 對 SSE 路徑的 `proxy_read_timeout` 調到遠大於心跳間隔（例如 1 小時），讓 nginx 不會成為最短的那一個。同樣的道理也適用於第 32 章的 WebSocket ping。

## 31.8 SSE 與 HTTP 版本：六條連線的牆與多工

SSE 在 HTTP/1.1 上，每一條事件串流都**獨佔一條 TCP 連線**：回應永遠不結束，這條連線就不能再拿來送其他請求（HTTP/1.1 的連線同一時間只能有一個請求在進行，第 20 章）。回應的 body 長度未知，所以 server 要用 `Transfer-Encoding: chunked` 一段一段送（每段前面寫上十六進位的長度），或者乾脆不寫長度、以關閉連線表示結束。

問題出在瀏覽器的**每主機連線上限**：主流瀏覽器對同一個主機（嚴格說是同一組 scheme、host、port）的 HTTP/1.1 連線，同時最多約 6 條（第 22 章），而且這個上限是整個瀏覽器共用的，不是每個分頁各自計算。故事中的老師開了七個後台分頁，每個分頁都開一條 SSE，前六條佔滿了上限，第七個分頁的 SSE 只能排隊，更糟的是，連那個分頁要載入的 JSON API 也一起排隊，整頁都出不來。這個限制在主流瀏覽器裡被明確標為不會為 SSE 放寬。

```text
 HTTP/1.1：每條 SSE 獨佔一條連線             HTTP/2：所有 SSE 是同一條連線上的 stream

 分頁1 ══ TCP#1 ══ SSE ════════════►        分頁1 ─ stream 1  ─┐
 分頁2 ══ TCP#2 ══ SSE ════════════►        分頁2 ─ stream 3  ─┤
 分頁3 ══ TCP#3 ══ SSE ════════════►        分頁3 ─ stream 5  ─┤
 分頁4 ══ TCP#4 ══ SSE ════════════►        分頁4 ─ stream 7  ─┼══ 一條 TCP＋TLS ══►
 分頁5 ══ TCP#5 ══ SSE ════════════►        分頁5 ─ stream 9  ─┤   （上限由 SETTINGS_
 分頁6 ══ TCP#6 ══ SSE ════════════►        分頁6 ─ stream 11 ─┤    MAX_CONCURRENT_
 分頁7 ‥‥ 排隊中（連 API 也送不出去）        分頁7 ─ stream 13 ─┘    STREAMS 決定，常見 100）
```

左右兩邊是同樣七個分頁。左邊的 HTTP/1.1，每條 SSE 吃掉一條連線，第七個請求被卡在瀏覽器裡，根本沒送出去，所以 server 的 log 裡找不到它，DevTools 裡則顯示為 Stalled 或 Pending。右邊的 HTTP/2 把每個 SSE 變成同一條連線上的一個 **stream**（第 22 章），事件被包成 DATA frame 送出，HTTP/2 不使用 chunked（規格禁止 `Transfer-Encoding: chunked`），同時能開多少個 stream 由 server 的 `SETTINGS_MAX_CONCURRENT_STREAMS` 決定，常見值在 100 左右。所以在 HTTP/2 或 HTTP/3 下，六條連線的牆就消失了。

HTTP/2 的代價也要知道。所有 stream 共用一條 TCP 連線，一個 TCP segment 遺失，這條連線上所有 stream 都要等重傳（TCP 層的 head-of-line blocking，第 12、22 章），所以在丟包的行動網路上，SSE 事件可能和頁面的其他請求一起被延遲；HTTP/3 走 QUIC，每個 stream 獨立重傳，沒有這個問題（第 13 章）。另一個常被誤解的地方是：瀏覽器到 CDN 或 LB 用 HTTP/2，不代表 LB 到後端也是。很多架構在 nginx 終止 HTTP/2，往後端仍用 HTTP/1.1，所以後端看到的仍然是**每條 SSE 一條連線**；HTTP/2 解決的是瀏覽器端的上限，不是 server 端的連線數。

| 面向 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| 一條 SSE 的載體 | 一條 TCP 連線（獨佔） | 一條 stream | 一條 QUIC stream |
| body 怎麼分段 | `chunked`，或不寫長度、以關閉結束 | DATA frame（禁止 chunked） | DATA frame |
| 瀏覽器的同時上限 | 每主機約 6 條，所有分頁共用 | 由 `SETTINGS_MAX_CONCURRENT_STREAMS` 決定 | 由 QUIC 的 stream 上限決定 |
| 丟包的影響 | 只卡住那一條連線 | 同一條 TCP 上所有 stream 一起等 | 只卡住遺失的那個 stream |
| server 端結束一條 SSE | 關閉 TCP 連線或送 chunked 結尾 | 送 END_STREAM 或 RST_STREAM | 結束或重設該 stream |

這張表的實務結論有三點。第一，對外提供 SSE 的網域，最好在 edge 啟用 HTTP/2 或 HTTP/3。第二，如果某些使用者只能走 HTTP/1.1（例如公司 proxy），把 SSE 放在獨立的子網域（聲聲 Live 用 `rt.shengsheng.example`），至少不會讓 SSE 吃掉主站 API 的連線額度。第三，同一個使用者開多個分頁時，可以讓分頁共用一條 SSE：其中一個分頁持有 EventSource，透過 `BroadcastChannel` 把事件轉給其他分頁，或把連線放在 `SharedWorker` 裡（瀏覽器支援情況要另外確認），這同時減少了 server 端的連線數。

## 31.9 Proxy 緩衝：事件為什麼一批一批到

故事中最詭異的問題 ①，是事件延遲十幾秒，然後好幾則一起湧進來。這幾乎永遠是**緩衝**（buffering）造成的：資料在路徑上的某一層被暫存起來，攢夠了才往下送。緩衝在一般的 HTTP 回應中是好東西，對 SSE 卻是致命的，因為 SSE 每個事件都很小，可能永遠攢不夠。

以 nginx 為例，`proxy_buffering` 預設是開啟的。開啟時，nginx 會盡快從 upstream 把回應讀進自己的緩衝區（`proxy_buffer_size` 與 `proxy_buffers`，單塊大小常見是一個記憶體分頁，4 KB 或 8 KB），再依自己的節奏寫給 client；回應太大時還會寫進暫存檔。這樣設計的理由很好：後端的 gunicorn worker 是昂貴的資源，nginx 先把回應全部收下，worker 就能立刻去服務下一個請求，不必陪著網路很慢的手機使用者慢慢送。但對 SSE 來說，一個 40 bytes 的事件放進 8 KB 的緩衝區，nginx 不一定會立刻送出；在實務上常見的現象是，事件要等緩衝區累積到一定量或回應結束才往下送（確切的送出時機依版本與設定而定）。

```text
 Python 程式           ASGI／WSGI server        nginx                   CDN／LB          瀏覽器
 ┌───────────┐  寫入   ┌──────────────┐  TCP   ┌────────────────┐ TCP  ┌───────────┐  ┌──────────┐
 │ yield 事件 │──────► │ ① 應用層緩衝  │──────► │ ③ proxy_buffer │────► │ ④ edge 的 │─►│ ⑤ 解析器 │
 │           │        │  （write 沒   │        │   （預設開啟）  │      │   回應緩衝 │  │ 等空行   │
 │           │        │   flush）     │        │ ② gzip 壓縮緩衝 │      │           │  │          │
 └───────────┘        └──────────────┘        └────────────────┘      └───────────┘  └──────────┘
   修法：每個事件後            修法：用支援串流的        修法：X-Accel-Buffering: no、   修法：查 CDN 的串流   修法：每個事件
   flush；sync worker         server 與 worker；       proxy_buffering off、         設定，或讓 SSE      以空行結尾
   會被長請求卡住             避免壓縮 middleware      不壓縮 text/event-stream      繞過快取層
```

這張圖把一個事件從 Python 程式到瀏覽器 JavaScript 的路上，所有可能的緩衝點排成一列，每一格下面是對應的修法。除錯時要**一段一段往前推**：先在 nginx 主機上直接 `curl -N` 打後端（繞過 nginx），事件即時到達，表示 ① 沒問題；再打 nginx，事件卡住，就是 ② 或 ③；再從外面打 CDN，以此類推。每一段的判斷方式都一樣：事件是即時一則一則到，還是攢成一批才到。

③ 的修法有兩種。第一種是在 nginx 設定裡對 SSE 路徑關閉緩衝：`proxy_buffering off;`。第二種是讓後端在回應 header 裡帶 **`X-Accel-Buffering: no`**：nginx 看到這個 header，就對這一個回應停用緩衝（除非設定裡用 `proxy_ignore_headers` 刻意忽略它）。第二種的好處是「誰產生串流，誰負責宣告」：後端最清楚哪些回應是串流，基礎設施的設定不必隨每個新的 SSE 路徑修改。nginx 也不會把 `X-Accel-*` 這類 header 轉給瀏覽器，它只是後端寫給 proxy 看的指示。要注意 `X-Accel-Buffering` 是 nginx 的慣例，其他 proxy 或 CDN 不一定認得，各自有自己的設定方式。

② 是壓縮。gzip 這類演算法要累積一定的資料才能壓得有效率，壓縮器會把小資料留在內部緩衝區；除非程式在每個事件後明確要求壓縮器 flush，否則事件會被扣住。nginx 的 `gzip_types` 預設只壓縮 `text/html`，但很多團隊為了省事設成壓縮所有文字類型，就把 `text/event-stream` 也包進去了。SSE 的事件本來就小，壓縮的收益有限，最穩妥的做法是對 SSE 路徑關閉壓縮。回應 header 帶 `Cache-Control: no-cache` 能避免中間的快取把串流存起來；有些團隊再加上 `no-transform`，要求中間設備不要改寫內容（例如自動壓縮），但各家設備是否遵守依實作而定。

```nginx
# rt.shengsheng.example：SSE 路徑的 nginx 設定（示意）
location /rooms/ {
    proxy_pass http://rt_backend;
    proxy_http_version 1.1;            # 往後端用 HTTP/1.1，才能用 chunked 與連線重用
    proxy_set_header Connection "";    # 清掉 client 帶來的 Connection header
    proxy_buffering off;               # 或讓後端回 X-Accel-Buffering: no
    proxy_cache off;                   # 串流回應不能被快取
    proxy_read_timeout 1h;             # 遠大於 15 秒的心跳間隔
    gzip off;                          # 不壓縮事件串流
}
```

這段設定逐行對應前面的分析：關緩衝處理 ③，關壓縮處理 ②，關快取避免整條串流被存下，`proxy_read_timeout` 拉長讓 nginx 不會成為最短的閒置逾時。`proxy_http_version 1.1` 與清空 `Connection` 是 nginx 代理長連線與連線重用的常見寫法（第 43 章會再講 nginx 與 upstream 的 keep-alive）。

① 是應用程式自己的緩衝，最容易被忽略。Python 的檔案物件多半有緩衝區，寫入後不一定立刻送出；標準函式庫的 `http.server` 預設對回應不做緩衝（`wbufsize = 0`），所以本章的範例每次 `write` 都會直接送進 socket。框架層面，Flask 要用 generator 回傳串流回應，ASGI 框架則用對應的串流回應類別，而且中間不能有「先收集完整 body 再處理」的 middleware（例如某些壓縮或 log middleware）。在 gunicorn 的 sync worker 上跑 SSE 還有另一個問題：sync worker 處理請求期間無法回報存活，超過 `--timeout`（預設 30 秒）就會被 arbiter 殺掉；而且每條 SSE 會佔住一整個 worker。所以 SSE 應該放在 async 的服務上（第 42、43 章）。

```python
# not-runnable：Flask 版本的 SSE 端點（示意，events_after 是假設的事件紀錄查詢函式）
from flask import Flask, Response, request, stream_with_context

app = Flask(__name__)


@app.get("/rooms/<int:room_id>/events")
def room_events(room_id):
    last_id = request.headers.get("Last-Event-ID")

    def generate():
        yield "retry: 3000\n\n"
        for ev in events_after(room_id, last_id):   # 先補發，再阻塞等待新事件
            yield f"id: {ev.id}\nevent: {ev.type}\ndata: {ev.json}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

這段 Flask 程式只適合流量很小的內部工具：每條連線佔住一個 worker 或 thread，generator 阻塞等待新事件時也很難穿插心跳。聲聲 Live 的等候室最後放在 uvicorn 上的 ASGI 服務，用 asyncio 同時等待「新事件」與「心跳計時器」。

> [!note] 2026 現況
> 截至 2026 年 10 月，gunicorn 新版已內建 ASGI worker（依 gunicorn 官方發布紀錄，25.1 起為 stable），並在 25.0.x 修過 SSE 在 chunked encoding 下會卡住的問題。若用 gunicorn 跑串流回應，請確認版本與 worker 類型；傳統的 sync worker 仍不適合長時間的串流回應。

## 31.10 Server 端的成本：連線、記憶體與 fan-out

SSE 把成本從「請求數」轉成「同時存在的連線數」，所以容量規劃要改用新的單位。每條 SSE 連線在 server 端至少佔用：一個 fd（記得 `ulimit -n` 與第 10 章的 `EMFILE`）、核心裡這條 TCP 連線的收送緩衝區（依核心設定與流量動態調整，從幾 KB 到更多）、TLS 狀態（如果 TLS 在這一層終止），以及應用程式這一側的狀態（asyncio 的 task、訂閱紀錄、送出佇列）。確切的數字依實作而定，最可靠的方法是自己壓測：開一萬條閒置連線，看 process 的記憶體增加多少，除以一萬。

送出事件的那一側叫 **fan-out**（扇出）：一個事件要送給所有訂閱這個頻道的連線。即時服務通常有多個實例，學生的連線分散在不同實例上，所以事件產生時（例如 Flask API 收到「老師開始上課」的請求），要先發布到一個所有實例都訂閱的 pub/sub 系統，每個實例再把事件寫給自己身上、屬於這間教室的連線。這也是 31.6 節說事件紀錄必須共用的原因。完整的架構設計（訂閱管理、順序、去重、背壓）在第 33 章，這裡先記住一個原則：**連線所在的實例不一定是事件產生的實例**。

還有一個容易出事的地方是**慢的 client**。server 寫入的速度如果比某個 client 讀取的速度快（例如手機在很差的網路上），資料會先堆在核心的送出緩衝區，滿了之後應用程式的寫入就會阻塞或在 asyncio 裡等待。如果 fan-out 的程式是「依序寫給每條連線」，一個慢 client 就會拖住整間教室。正確的做法是每條連線一個有上限的送出佇列，滿了就丟棄這個 client（讓它重連後用 `Last-Event-ID` 或 reset 補回），而不是讓它拖垮其他人。

| 項目 | 估算方式 | 聲聲 Live 等候室（6,000 條） |
|---|---|---|
| 新連線速率 | 平常很低；部署或網路抖動時，所有 client 在 retry 時間內一起重連 | retry 3 秒加隨機抖動 → 尖峰約每秒 2,000 條新連線 |
| 心跳寫入 | 連線數 ÷ 心跳間隔 | 6,000 ÷ 15 ＝ 每秒 400 次 |
| 事件寫入 | 事件數 × 每個事件的訂閱者數 | 每間教室約 10 人，事件很少，可忽略 |
| fd | 每條連線一個，加上 upstream 與 pub/sub | `ulimit -n` 至少數萬，分散到多個實例 |
| 記憶體 | 每條連線的實測值 × 連線數 | 以壓測結果為準，預留重連尖峰的餘量 |

這張估算表的第一列最常被忽略。平常 SSE 的新連線很少，但部署時舊實例關閉，幾千個瀏覽器會在 retry 時間附近同時重連，每一個都要做 TLS 交握、驗證 cookie、查 `Last-Event-ID` 補發。這就是 SSE 版本的驚群。緩解方法包括：分批關閉舊實例的連線、讓 server 在關閉前送一個帶隨機值的 `retry:`，把重連時間攤開，以及讓補發的查詢走快取而不是直接打資料庫。

安全上，Rita 為 SSE 端點列了幾條規則。第一，SSE 是長時間存在的授權：連線建立時驗證了 cookie，不代表一小時後使用者仍有權限；session 被撤銷時要能主動關閉對應的連線，或定期讓連線結束、迫使重新驗證。第二，限制每個使用者同時的 SSE 連線數，避免單一帳號開幾千條連線耗盡資源。第三，CORS 只允許自家的來源，`withCredentials` 搭配明確的 `Access-Control-Allow-Origin`，不能用 `*`。第四，事件內容只放這個使用者有權看到的資料，不要因為「反正是推播」就把整間教室的內部狀態都送出去。

## 31.11 選型：三種做法加上 WebSocket

有了三種做法各自的成本模型，可以把它們放在同一個情境下比較。下面這段程式用模擬時鐘重現聲聲 Live 某一間大型講座的等候室：1,200 名學生待 10 分鐘，期間發生 12 個狀態變化，RTT 50 ms。它計算每種做法的總請求數與事件延遲（從事件發生到學生收到），SSE 假設沒有斷線。

```python
import math
import random

# 模擬時鐘：1,200 名學生在等候室待 10 分鐘，期間 server 發生 12 個狀態變化
N, T = 1200, 600.0
ONE_WAY = 0.025                       # 單程 25 ms（RTT 50 ms）
rng = random.Random(31)
events = sorted(rng.uniform(5, T - 5) for _ in range(12))


def short_polling(interval):
    reqs, lat = 0, []
    for _ in range(N):
        phase = rng.uniform(0, interval)              # 每個瀏覽器開頁時間不同
        reqs += math.floor((T - phase) / interval) + 1
        for e in events:
            k = math.ceil((e - ONE_WAY - phase) / interval)  # 第一個「抵達 server 時已有事件」的 poll
            lat.append(phase + k * interval + 2 * ONE_WAY - e)
    return reqs, lat


def long_polling(hold):
    reqs, lat = 0, []
    for _ in range(N):
        t, seen = rng.uniform(0, 1), 0                # t = 請求送出的時刻
        while t < T:
            reqs += 1
            arrive = t + ONE_WAY
            pending = [e for e in events[seen:]]
            if pending and pending[0] <= arrive:      # 斷線空檔發生的事件：靠 cursor 立刻補回
                done = arrive
            elif pending and pending[0] <= arrive + hold:
                done = pending[0]
            else:
                done = arrive + hold                  # 逾時，回空結果
            got = [e for e in pending if e <= done]
            lat += [done + ONE_WAY - e for e in got]
            seen += len(got)
            t = done + ONE_WAY                        # 收到回應立刻再問
    return reqs, lat


def sse(heartbeat):
    reqs = N                                          # 每人一條長連線（假設不斷線）
    lat = [ONE_WAY] * (N * len(events))
    beats = N * int(T // heartbeat)
    return reqs, lat, beats


def p(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


results = {"short polling 2s": short_polling(2.0),
           "short polling 10s": short_polling(10.0),
           "long polling 25s": long_polling(25.0)}
reqs, lat, beats = sse(15.0)
results["SSE (heartbeat 15s)"] = (reqs, lat)
print(f"{'mode':<20}{'requests':>10}{'req/s':>8}{'avg':>8}{'p99':>8}")
for name, (reqs, lat) in results.items():
    print(f"{name:<20}{reqs:>10,}{reqs / T:>8.1f}{sum(lat) / len(lat) * 1000:>6.0f}ms{p(lat, .99) * 1000:>6.0f}ms")
useful = N * len(events)
print(f"有用的通知 {useful:,} 則；short polling 2s 有 {1 - useful / results['short polling 2s'][0]:.1%} 的回應是「沒有變化」")
print(f"SSE 心跳註解行 {beats:,} 行，每行約 8 bytes，合計約 {beats * 8 / 1024:.0f} KB")
assert results["SSE (heartbeat 15s)"][0] < results["long polling 25s"][0] < results["short polling 10s"][0]
```

```text
mode                  requests   req/s     avg     p99
short polling 2s       360,000   600.0  1023ms  2006ms
short polling 10s       72,000   120.0  5009ms  9923ms
long polling 25s        37,200    62.0    27ms    49ms
SSE (heartbeat 15s)      1,200     2.0    25ms    25ms
有用的通知 14,400 則；short polling 2s 有 96.0% 的回應是「沒有變化」
SSE 心跳註解行 48,000 行，每行約 8 bytes，合計約 375 KB
```

這組數字把前面三節的公式具體化了。short polling 2 秒：360,000 個請求，平均延遲約 1 秒（間隔的一半），p99 約 2 秒（一整個間隔），而且 96% 的回應是「沒有變化」；拉長到 10 秒，請求數降為五分之一，延遲卻升到 5 秒。long polling 25 秒：請求數降到 37,200（每人約 31 次：12 次帶回事件，其餘約 19 次是逾時的空回應），平均延遲只有 27 ms，p99 的 49 ms 對應「事件落在空檔裡、要多一個 RTT」的情況。SSE：每人一個請求，延遲就是單程傳輸時間，心跳的總量只有幾百 KB。

這個模擬刻意沒有計入兩件事，讀數字時要記得。第一，SSE 與 long polling 的成本在「同時連線數」：兩者都要 1,200 條同時存在的連線或請求，而 short polling 在任一時刻只有幾十個請求在處理。第二，SSE 假設連線從不斷線；實際上部署與網路抖動會造成重連，每次重連都是一個新請求加一次補發。即使如此，SSE 的請求數仍然比 short polling 少兩個數量級。

| 需求 | short polling | long polling | SSE | WebSocket（第 32 章） |
|---|---|---|---|---|
| 方向 | client 拉 | server 推（模擬） | server 推 | 雙向 |
| 延遲 | 間隔的一半 | 約單程 | 約單程 | 約單程 |
| 斷線補發 | 每次都是完整查詢，天然沒有 | 靠 cursor | 內建 `Last-Event-ID`，server 要實作 | 全部自己做 |
| 資料格式 | 任意 | 任意 | UTF-8 文字（二進位要自己編碼） | 文字或二進位 frame |
| 對中間設備的友善度 | 最好，可被 CDN 快取 | 好，但要注意逾時 | 好，但要處理緩衝與閒置逾時 | 需要 proxy 支援 Upgrade |
| server 實作難度 | 最低 | 中 | 中（需要 async） | 高（frame、ping、背壓） |

這張表的讀法是從需求往右找。資料每分鐘才變一次、晚幾秒沒關係：short polling，而且盡量讓 CDN 快取。需要即時、資料只從 server 往 client：SSE，它有標準化的重連與補發，又是普通 HTTP。需要 client 也頻繁送資料、需要二進位或極低的額外負擔（例如白板筆跡、多人遊戲）：WebSocket。long polling 現在主要是後備方案：當環境裡有某個中間設備怎樣都會緩衝串流回應，或者要支援非常舊的 client 時才用。

```text
                     server 有新資料要給 client
                                │
              晚幾秒也沒關係，而且所有人看到的一樣？
                 │ 是                         │ 否
                 ▼                            ▼
   short polling＋CDN 快取        client 也需要頻繁送資料、或需要二進位？
   （加 jitter、背景分頁降頻）        │ 是                     │ 否
                                     ▼                        ▼
                            WebSocket（第 32 章）      路徑上能關掉所有緩衝？
                                                        │ 能          │ 不能
                                                        ▼             ▼
                                                  SSE＋心跳＋      long polling
                                                  Last-Event-ID   ＋cursor（後備）
```

這張決策流程圖就是小晴後來在設計文件裡用的版本。等候室屬於「server 推、client 幾乎不說話、要即時」，所以走到 SSE；教室的聊天與白板需要雙向而頻繁的訊息，走到 WebSocket；講座名單與老師列表的「剩餘名額」則是所有人看到一樣、晚幾秒沒關係的資料，用 short polling 讓 CDN 快取，origin 幾乎不受人數影響。同一個產品裡三種做法並存，是很正常的事。

## 31.12 動手做：在 127.0.0.1 上實作與量測三種做法

這一節有三個實驗，都只用標準函式庫，在 127.0.0.1 上用 port 0 讓系統分配埠號。實驗一在同一個 server 上實作 short polling、long polling 與 SSE 三個端點，讓三個 client 同時觀察同一串事件，量測請求數與延遲。實驗二實作完整的 SSE 重連：`retry`、`id`、`Last-Event-ID` 補發、心跳註解行、204 停止重連，以及補不回來時的 reset。實驗三寫一個會緩衝的迷你 reverse proxy，重現 SSE 卡住的現象，再用 `X-Accel-Buffering: no` 修好它。以下輸出都是在 macOS 上實際執行的結果，延遲數字每次執行會有些微不同，請求數與事件數則是固定的。

### 實驗一：同一串事件，三種送法

server 端用一個共用的 `EventLog` 保存所有事件，每個事件有遞增的 id 與發布時刻；三個端點只差在「怎麼交給 client」。`/short` 立刻回傳 cursor 之後的事件（可能是空的）；`/long` 沒有事件時用 `Condition.wait_for` 掛著，最多 0.5 秒；`/sse` 回 `text/event-stream`，用 chunked 編碼一則一則寫，閒置 0.3 秒就送一行心跳。事件在 2.4 秒內依序發生 6 次，間隔有密有疏。short polling 的 client 每 0.15 秒問一次。

```python
import http.client
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

T0 = time.monotonic()
SCHEDULE = [0.10, 0.25, 0.80, 1.60, 1.70, 2.05]   # 事件發生的時刻（秒）：有密集、也有長空檔
RUN_FOR, POLL_EVERY, HOLD, HEARTBEAT = 2.4, 0.15, 0.5, 0.3


class EventLog:
    """所有事件依序編號；三種 server 共用同一份資料，只差在「怎麼交給 client」。"""
    def __init__(self):
        self.events, self.cond, self.closed = [], threading.Condition(), False

    def publish(self, data):
        with self.cond:
            self.events.append({"id": len(self.events) + 1, "t": time.monotonic(), "data": data})
            self.cond.notify_all()

    def after(self, cursor, wait=0.0):
        with self.cond:   # wait_for 會在被 notify 或逾時後回來，期間不佔 CPU
            self.cond.wait_for(lambda: len(self.events) > cursor or self.closed, timeout=wait)
            return self.events[cursor:]


LOG = EventLog()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"                 # 讓 short／long polling 可以重用連線

    def do_GET(self):
        url = urlsplit(self.path)
        cursor = int(parse_qs(url.query).get("since", ["0"])[0])
        if url.path == "/short":
            self.reply_json(LOG.after(cursor))    # 有沒有新東西都立刻回
        elif url.path == "/long":
            self.reply_json(LOG.after(cursor, wait=HOLD))   # 沒東西就掛著，最多 HOLD 秒
        elif url.path == "/sse":
            self.stream_sse(cursor)

    def reply_json(self, events):
        body = json.dumps({"events": events}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def stream_sse(self, cursor):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")  # 長度未知：HTTP/1.1 用 chunked 一段段送
        self.end_headers()
        chunk = lambda s: self.wfile.write(f"{len(s.encode()):x}\r\n{s}\r\n".encode())
        while not LOG.closed:
            new = LOG.after(cursor, wait=HEARTBEAT)
            for ev in new:
                chunk(f"id: {ev['id']}\ndata: {json.dumps(ev)}\n\n")
            if not new and not LOG.closed:
                chunk(": ping\n\n")               # 心跳：註解行，client 不會觸發事件
            cursor += len(new)
        self.wfile.write(b"0\r\n\r\n")             # chunked 的結尾

    def log_message(self, *args):
        pass


def record(stats, events):
    now = time.monotonic()
    for ev in events:
        stats["lat"].append(now - ev["t"])
    return len(events)


def polling_client(path, stats):
    conn, cursor = http.client.HTTPConnection(*server.server_address), 0
    while time.monotonic() - T0 < RUN_FOR:
        conn.request("GET", f"{path}?since={cursor}")
        events = json.loads(conn.getresponse().read())["events"]
        stats["requests"] += 1
        stats["empty"] += not events
        cursor += record(stats, events)
        if path == "/short":
            time.sleep(POLL_EVERY)               # short polling：固定間隔再問一次
    conn.close()


def sse_client(stats):
    conn = http.client.HTTPConnection(*server.server_address)
    conn.request("GET", "/sse")
    resp = conn.getresponse()
    stats["requests"] += 1
    while line := resp.readline():               # http.client 會幫我們拆掉 chunked 的框
        if line.startswith(b"data: "):
            record(stats, [json.loads(line[6:])])
        elif line.startswith(b":"):
            stats["empty"] += 1                  # 這裡借用 empty 欄位計算心跳數
    conn.close()


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
stats = {name: {"requests": 0, "empty": 0, "lat": []} for name in ("short", "long", "sse")}
clients = [threading.Thread(target=polling_client, args=("/short", stats["short"])),
           threading.Thread(target=polling_client, args=("/long", stats["long"])),
           threading.Thread(target=sse_client, args=(stats["sse"],))]
for c in clients:
    c.start()
for i, at in enumerate(SCHEDULE, 1):
    time.sleep(max(0.0, at - (time.monotonic() - T0)))
    LOG.publish(f"room-7 update #{i}")
time.sleep(max(0.0, RUN_FOR - (time.monotonic() - T0)))
with LOG.cond:
    LOG.closed = True
    LOG.cond.notify_all()
for c in clients:
    c.join()
server.shutdown()
server.server_close()

print(f"{'mode':<8}{'requests':>9}{'empty/ping':>12}{'events':>8}{'avg ms':>8}{'max ms':>8}")
for name, s in stats.items():
    lat = [x * 1000 for x in s["lat"]]
    print(f"{name:<8}{s['requests']:>9}{s['empty']:>12}{len(lat):>8}{sum(lat) / len(lat):>8.1f}{max(lat):>8.1f}")
    assert len(lat) == len(SCHEDULE)
assert stats["sse"]["requests"] == 1 < stats["long"]["requests"] < stats["short"]["requests"]
```

```text
mode     requests  empty/ping  events  avg ms  max ms
short          16          10       6    98.1   148.8
long            9           3       6     1.0     2.2
sse             1           5       6     0.9     2.2
```

三個 client 都收到了全部 6 個事件（`events` 欄），差別在代價與延遲。**short**：2.4 秒內問了 16 次，其中 10 次是空的；平均延遲約 100 ms、最大約 150 ms，正好落在「間隔的一半到一整個間隔」之間（0.15 秒的一半是 75 ms，每輪再加上一點處理時間，輪詢時刻會慢慢往後漂）。**long**：9 個請求，其中 3 個是空回應：兩個是逾時，對應 0.25→0.80 與 0.80→1.60 這兩段超過 0.5 秒的空檔，另一個是最後掛著的請求在 server 關閉時回的空結果；延遲只有 1 ms 左右，這就是 loopback 上的傳輸時間。**sse**：只有 1 個請求，延遲同樣約 1 ms；`empty/ping` 的 5 是心跳次數，每一次都發生在超過 0.3 秒沒有事件的時候。

請求數 16、9、1 這三個數字就是 31.2 節表格的縮小版：short polling 由時間決定（2.4 ÷ 0.15 ＝ 16），long polling 由「事件＋空回應」決定（6＋3），SSE 永遠是一次。程式裡有兩個細節值得注意。第一，long polling 的 client 每次都帶 `since` cursor，server 用 `self.events[cursor:]` 回傳「cursor 之後的全部」，即使事件發生在兩次請求之間也不會漏。第二，SSE 端點手寫了 chunked 的框（十六進位長度、CRLF、內容、CRLF，最後 `0\r\n\r\n`），client 端的 `http.client` 自動把框拆掉，`readline()` 讀到的就是純粹的事件文字行。

### 實驗二：重連、Last-Event-ID、心跳與補發

這個實驗重現故事中的問題 ③ 並修好它。server 有一個只保留最近 4 則事件的環形緩衝（`deque(maxlen=4)`），第一條連線送完 3 則就主動斷線，模擬部署；client 是一個極簡版的 EventSource：解析 `retry`，斷線後等待 retry 毫秒，帶著 `Last-Event-ID` 重連，遇到非 200 就停止。斷線期間 server 又發布了兩則事件，看看它們能不能被補回來。最後再模擬一個「睡太久」的 client，帶著很舊的 id 回來。

```python
import socket
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RETRY_MS, HEARTBEAT, KEEP = 200, 0.15, 4        # 重連等待、心跳間隔、server 保留最近幾則事件
T0 = time.monotonic()


class Room:
    def __init__(self):
        self.buffer = deque(maxlen=KEEP)          # 補發用的環形緩衝：只留最近 KEEP 則
        self.last_id, self.ended = 0, False
        self.cond = threading.Condition()

    def publish(self, data, ended=False):
        with self.cond:
            self.last_id += 1
            self.buffer.append((self.last_id, data))
            self.ended = ended
            self.cond.notify_all()


ROOM = Room()


class SSEHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        last = self.headers.get("Last-Event-ID")
        cursor = int(last) if last and last.isdigit() else 0
        with ROOM.cond:
            oldest = ROOM.buffer[0][0] if ROOM.buffer else 1
            done = ROOM.ended and cursor >= ROOM.last_id
        if done:                                   # 課程結束而且你什麼都沒漏：叫瀏覽器別再連
            self.send_response(204)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()                         # HTTP/1.0：沒有 Content-Length，以關閉連線表示結束
        self.wfile.write(f"retry: {RETRY_MS}\n\n".encode())
        if cursor and cursor < oldest - 1:         # 漏掉的已經不在 buffer 裡，補不回來
            self.wfile.write(b'event: reset\ndata: {"refetch": "/api/rooms/7/state"}\n\n')
            return
        sent_here = 0
        while True:
            with ROOM.cond:
                ROOM.cond.wait_for(lambda: ROOM.last_id > cursor, timeout=HEARTBEAT)
                new = [(i, d) for i, d in ROOM.buffer if i > cursor]
                ended = ROOM.ended
            if not new:
                self.wfile.write(b": hb\n\n")      # 心跳：讓中間設備看到流量，也順便偵測斷線
                continue
            for i, d in new:
                self.wfile.write(f"id: {i}\nevent: room\ndata: {d}\n\n".encode())
                cursor, sent_here = i, sent_here + 1
            if ended or (last is None and sent_here >= 3):
                return                             # 第一條連線送 3 則就斷：模擬 server 重新部署

    def log_message(self, *args):
        pass


def event_source(addr, last_id=None, max_conns=4):
    """極簡版 EventSource：斷線就等 retry 毫秒、帶 Last-Event-ID 重連；非 200 就停止。"""
    retry, log = 3000, []
    for n in range(1, max_conns + 1):
        with socket.create_connection(addr) as s, s.makefile("rb") as f:
            extra = f"Last-Event-ID: {last_id}\r\n" if last_id else ""
            s.sendall(f"GET /rooms/7/events HTTP/1.1\r\nHost: rt.shengsheng.example\r\n"
                      f"Accept: text/event-stream\r\n{extra}\r\n".encode())
            status = f.readline().split()[1].decode()
            while f.readline() not in (b"\r\n", b"\n", b""):
                pass                               # 略過 response header
            log.append(f"[conn {n}] Last-Event-ID={last_id or '-'} → {status}")
            if status != "200":
                log.append(f"[conn {n}] 非 200，EventSource 進入 CLOSED，不再重連")
                return log
            ev = {}
            for raw in f:                          # 逐行讀到 server 關閉連線
                line = raw.decode().rstrip("\n")
                if line.startswith(":"):
                    log.append("           (heartbeat comment)")
                elif line.startswith("retry: "):
                    retry = int(line[7:])
                elif line == "" and "data" in ev:
                    last_id = ev.get("id", last_id)
                    tag = f" id={ev['id']}" if "id" in ev else ""
                    log.append(f"           {ev.get('event', 'message')}{tag} {ev['data']}")
                    if ev.get("event") == "reset":     # 補不回來：前端自己關掉，改抓完整狀態
                        log.append(f"[conn {n}] 收到 reset → close()，改打 API 重抓教室狀態")
                        return log
                    ev = {}
                elif ":" in line:
                    k, v = line.split(": ", 1)
                    ev[k] = v
        t_close = time.monotonic()
        time.sleep(retry / 1000)                   # 依 server 指定的 retry 等待，不是立刻重連
        assert time.monotonic() - t_close >= retry / 1000
        log.append(f"[conn {n}] server 關閉連線，等 retry={retry} ms 後帶 Last-Event-ID 重連")
    return log


def publisher():
    plan = [(0.05, "老師進入教室"), (0.10, "白板已開啟"), (0.15, "第 1 頁講義"),
            (0.20, "第 2 頁講義"), (0.25, "小測驗開始"), (0.75, "課程結束")]
    for at, msg in plan:
        time.sleep(max(0.0, at - (time.monotonic() - T0)))
        ROOM.publish(msg, ended=(msg == "課程結束"))


server = ThreadingHTTPServer(("127.0.0.1", 0), SSEHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
pub = threading.Thread(target=publisher)
pub.start()
log = event_source(server.server_address)
pub.join()
print("\n".join(log))
late = event_source(server.server_address, last_id=1, max_conns=1)   # 斷線太久的 client
print("\n".join(late))
server.shutdown()
server.server_close()
assert sum("room id=" in line for line in log) == 6           # 6 則一則不漏、不重複
assert any("204" in line for line in log) and "reset" in late[1] and len(late) == 3
```

```text
[conn 1] Last-Event-ID=- → 200
           room id=1 老師進入教室
           room id=2 白板已開啟
           room id=3 第 1 頁講義
[conn 1] server 關閉連線，等 retry=200 ms 後帶 Last-Event-ID 重連
[conn 2] Last-Event-ID=3 → 200
           room id=4 第 2 頁講義
           room id=5 小測驗開始
           (heartbeat comment)
           (heartbeat comment)
           room id=6 課程結束
[conn 2] server 關閉連線，等 retry=200 ms 後帶 Last-Event-ID 重連
[conn 3] Last-Event-ID=6 → 204
[conn 3] 非 200，EventSource 進入 CLOSED，不再重連
[conn 1] Last-Event-ID=1 → 200
           reset {"refetch": "/api/rooms/7/state"}
[conn 1] 收到 reset → close()，改打 API 重抓教室狀態
```

逐段對照 31.6 節的狀態機。**conn 1** 是第一次連線，沒有 `Last-Event-ID`；server 先送 `retry: 200`，接著送出 id 1 到 3，然後主動關閉，模擬部署。client 沒有立刻重連，而是照 server 指定的 200 ms 等待，程式中的 `assert` 驗證了實際等待時間不少於 retry。等待期間，publisher 發布了 id 4「第 2 頁講義」與 id 5「小測驗開始」，這兩則正是故事裡學生漏掉的通知。

**conn 2** 帶著 `Last-Event-ID: 3` 重連，server 從環形緩衝裡找出 3 之後的事件，先補發 4 與 5，然後進入即時模式。接下來有約 0.4 秒沒有事件，server 每 0.15 秒送一行 `: hb`，所以出現兩行心跳；client 只是記錄它們，不會當成事件。id 6「課程結束」送出後，server 結束回應。**conn 3** 帶著 `Last-Event-ID: 6` 回來，server 判斷課程已結束且 client 什麼都沒漏，回 204，client 進入 CLOSED，不再重連。最後的 `assert` 確認 6 則事件一則不漏、一則不重複。

最後三行是「睡太久」的 client：它帶著 `Last-Event-ID: 1` 回來，但環形緩衝只保留最近 4 則（id 3 到 6），id 2 已經被擠掉，server 無法保證補齊，就送出 `event: reset`。client 收到後自己呼叫 close，改打 API 抓教室的完整狀態。注意這裡的判斷條件 `cursor < oldest - 1`：client 需要的第一則是 cursor＋1，只要它還在緩衝區裡（大於等於 oldest），就能補發，否則一定得 reset。

### 實驗三：重現 proxy 緩衝，再用 X-Accel-Buffering 修好

這個實驗重現故事中的問題 ①。upstream 是 SSE 應用程式，每 100 ms 送一則事件，共 6 則，總共不到 300 bytes；事件內容帶著送出的時刻，讓 client 算出「送出到收到」的延遲。中間的 `BufferingProxy` 模擬 nginx 預設開啟的 `proxy_buffering`：把回應攢到 4 KB 或回應結束才往下送；但如果 upstream 的回應 header 有 `X-Accel-Buffering: no`，就對這個回應停用緩衝，而且像 nginx 一樣不把這個 header 轉給瀏覽器。

```python
import json
import socket
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BUF = 4096                    # 模擬 proxy 的緩衝區：攢滿 4 KB 或回應結束才往下送


class Upstream(BaseHTTPRequestHandler):
    """應用程式 server：每 100 ms 送一則 SSE 事件，共 6 則，每則不到 100 bytes。"""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        if self.path == "/unbuffered":
            self.send_header("X-Accel-Buffering", "no")   # 告訴 proxy：這個回應不要緩衝
        self.end_headers()
        for n in range(1, 7):
            if n > 1:
                time.sleep(0.1)
            self.wfile.write(f"data: {json.dumps({'n': n, 'sent': time.monotonic()})}\n\n".encode())

    def log_message(self, *args):
        pass


class BufferingProxy(socketserver.BaseRequestHandler):
    """極簡 reverse proxy：預設緩衝回應（像 nginx 的 proxy_buffering on），看到 header 才關掉。"""
    def handle(self):
        request = self.request.recv(65536)
        with socket.create_connection(upstream.server_address) as up:
            up.sendall(request)
            head = b""
            while b"\r\n\r\n" not in head:
                head += up.recv(65536)
            head, _, rest = head.partition(b"\r\n\r\n")
            buffering = b"x-accel-buffering: no" not in head.lower()
            # 像 nginx 一樣，X-Accel-* 是給 proxy 看的，不轉給瀏覽器
            lines = [l for l in head.split(b"\r\n") if not l.lower().startswith(b"x-accel-")]
            self.request.sendall(b"\r\n".join(lines) + b"\r\n\r\n")
            pending = rest
            if not buffering and pending:
                self.request.sendall(pending)      # 和 header 一起到的第一則事件也要立刻送
                pending = b""
            while chunk := up.recv(65536):
                pending += chunk
                if not buffering or len(pending) >= BUF:
                    self.request.sendall(pending)
                    pending = b""
            self.request.sendall(pending)          # upstream 結束，把剩下的全部倒出去


def watch(path):
    with socket.create_connection(proxy.server_address) as s, s.makefile("rb") as f:
        s.sendall(f"GET {path} HTTP/1.0\r\nHost: rt.shengsheng.example\r\n\r\n".encode())
        head = [line for line in iter(f.readline, b"\r\n")]
        delays = []
        for line in f:
            if line.startswith(b"data: "):
                ev = json.loads(line[6:])
                delays.append(time.monotonic() - ev["sent"])   # 事件送出到瀏覽器收到的時間
        return head, delays


upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
proxy = socketserver.ThreadingTCPServer(("127.0.0.1", 0), BufferingProxy)
for srv in (upstream, proxy):
    threading.Thread(target=srv.serve_forever, daemon=True).start()

head_b, slow = watch("/buffered")
head_u, fast = watch("/unbuffered")
print("event  buffered   X-Accel-Buffering: no")
for n, (a, b) in enumerate(zip(slow, fast), 1):
    print(f"  #{n}   {round(a * 100) * 10:>4} ms   {round(b * 100) * 10:>4} ms")
print("proxy 轉給瀏覽器的 header 有 X-Accel-Buffering 嗎？",
      any(l.lower().startswith(b"x-accel") for l in head_u))
for srv in (upstream, proxy):
    srv.shutdown()
    srv.server_close()
assert slow[0] > 0.45 and max(fast) < 0.05
```

```text
event  buffered   X-Accel-Buffering: no
  #1    520 ms      0 ms
  #2    410 ms      0 ms
  #3    310 ms      0 ms
  #4    210 ms      0 ms
  #5    110 ms      0 ms
  #6      0 ms      0 ms
proxy 轉給瀏覽器的 header 有 X-Accel-Buffering 嗎？ False
```

延遲以 10 ms 為單位四捨五入。左欄是預設緩衝的情況：6 則事件總共不到 300 bytes，永遠攢不滿 4 KB，所以 proxy 一直扣著，直到 upstream 在第 0.5 秒結束回應時才一次倒出去。第 1 則被扣了約 0.5 秒，第 6 則幾乎沒等，延遲呈現整齊的遞減，這正是「事件一批一批到」的指紋：**所有事件在同一個時刻抵達**，延遲＝「批次送出的時刻」減去「各自產生的時刻」。真實的 SSE 回應永遠不結束，所以在 production 上，事件會一直被扣到緩衝區滿或連線被逾時切斷為止，這就是故事中學生等了十幾秒、然後好幾則通知一起湧入的原因。

右欄是 upstream 加上 `X-Accel-Buffering: no` 之後：每則事件的延遲都是 0 ms（loopback 上不到 5 ms）。最後一行確認 proxy 沒有把這個 header 轉給瀏覽器。程式裡還藏著一個容易犯的錯：proxy 讀 header 時，第一則事件常常和 header 一起被讀進來（在 `rest` 裡），如果只在「下一次 recv」時才送，第一則事件就會晚一個事件間隔；這段程式在關閉緩衝時會立刻把 `rest` 送出。真實的 proxy 也有類似的細節，這也是為什麼要用 `curl -N` 實際量測，而不是只看設定檔就認定沒問題。

## 31.13 在工作上怎麼用

等候室改版穩定後，小晴把這次的經驗整理成團隊的檢查清單，依角色分成四份。

**後端工程師：上線一個 SSE 端點前，逐項確認。** 回應 header 有 `Content-Type: text/event-stream`、`Cache-Control: no-cache`、`X-Accel-Buffering: no`；每個事件以空行結尾，每個事件寫完立刻 flush；每 15 秒送一行註解心跳；事件有 `id`，server 讀 `Last-Event-ID` 並從共用的事件紀錄補發，補不回來時送 reset；課程結束或使用者無權限時回 204，而不是 401 或 500 讓前端默默死掉；跑在 async 的服務上，而不是 sync worker；每條連線的送出佇列有上限。

**SRE：用 curl 一段一段往前推，找出緩衝在哪一層。** `curl -N`（`--no-buffer`）讓 curl 收到什麼就印什麼，自己不緩衝。從離應用程式最近的地方開始打，逐步往外：

```bash
# 1. 在即時服務主機上直接打 uvicorn（繞過 nginx）
curl -N -H 'Accept: text/event-stream' http://127.0.0.1:8001/rooms/7/events
# 2. 在 VPC 內打其中一台 rt 的 nginx（繞過 L4 LB），用 --resolve 指到 10.20.2.11
curl -N --resolve rt.shengsheng.example:443:10.20.2.11 https://rt.shengsheng.example/rooms/7/events
# 3. 從外部正常打（經過 L4 LB 203.0.113.40），並印出 header 確認協定版本與緩衝相關 header
curl -N -sv https://rt.shengsheng.example/rooms/7/events 2>&1 | grep -E '^< (HTTP|content-type|cache-control)|^data|^:'
# 4. 模擬重連補發：帶上 Last-Event-ID
curl -N -H 'Last-Event-ID: 42' https://rt.shengsheng.example/rooms/7/events
```

```text
（示意輸出：第 3 步）
< HTTP/2 200
< content-type: text/event-stream
< cache-control: no-cache
: connected
retry: 3000
id: 43
data: {"room":7,"type":"slide","page":1}
: hb
```

讀這份輸出時看三件事。第一，`HTTP/2 200` 表示 client 到 rt 的 nginx 走的是 HTTP/2（L4 LB 不解密，HTTP 版本是在 nginx 終結 TLS 時協商的），六條連線的上限不適用。第二，`content-type` 正確，`X-Accel-Buffering` 沒有出現在 client 端，代表 nginx 照預期吃掉了它。第三，也是最重要的：盯著終端機看，`data:` 行是不是在事件發生的當下就出現，`: hb` 是不是每 15 秒準時出現。如果第 1 步即時、第 2 步卡住，問題在 nginx；第 2 步即時、第 3 步卡住，問題在 LB 或更外面的中間設備（例如使用者所在網路的公司 proxy）。

**前端工程師：用 DevTools 觀察 EventSource。** Chrome 的 Network 面板中，SSE 請求的類型顯示為 `eventsource`，點進去有一個 EventStream 分頁，即時列出每個事件的 id、type、data 與時間。分頁卡住時，看那個請求是否停在 Pending 或 Stalled，同時數一數同一個主機上有幾條進行中的 SSE；`onerror` 裡一定要檢查 `readyState`，等於 2 時要由程式決定接下來怎麼辦（重新登入或重新建立連線），並送出前端監控事件，否則使用者只會看到一個不再更新的頁面。

**容量與監控：把 SSE 的關鍵指標放上儀表板。** 至少包括：目前的連線數（依實例分）、每分鐘新建連線數（部署與網路抖動時會尖峰）、帶 `Last-Event-ID` 的重連比例、補發事件數與 reset 次數（reset 太多代表保留範圍太短）、每條連線送出佇列的長度分布（找出慢 client）、事件從產生到寫入 socket 的延遲。nginx 的 access log 對 SSE 的意義和一般請求不同：一條 SSE 的 log 在連線結束時才寫出，`$request_time` 是整條連線存活的時間，不是處理時間，看儀表板時不要把它當成延遲。

```text
 告警：「學生沒收到通知」
   │
   ├─ 完全沒收到，DevTools 看不到 eventsource 請求
   │     └─► 請求被瀏覽器卡住？數同主機的 SSE 數量（HTTP/1.1 上限 6）；前端是否 close() 了
   │
   ├─ 請求存在但 readyState = 2
   │     └─► 回應不是 200 或 Content-Type 錯了（401、502、text/html 錯誤頁）
   │
   ├─ 收到了，但晚很久、而且一批一批到
   │     └─► 緩衝：curl -N 一段一段往前推（應用 → nginx → CDN）
   │
   ├─ 每隔固定時間（例如 60 秒）斷一次
   │     └─► 閒置逾時：心跳間隔是否短於路徑上最短的 idle timeout
   │
   └─ 斷線重連後漏了幾則
         └─► server 是否讀 Last-Event-ID？事件紀錄是否跨實例共用？保留範圍夠不夠？
```

這張判斷流程圖依症狀分支，每一支都對應本章的一節。最上面兩支在瀏覽器端就能判斷，不用登入任何主機；中間的「一批一批到」與「固定週期斷線」是基礎設施的問題，用 curl 與設定檔查；最後的「漏訊息」是應用程式設計的問題，要看 server 的補發邏輯與事件紀錄。

## 31.14 常見錯誤與除錯

下表收錄 SSE 與 polling 在聲聲 Live 與一般團隊最常見的錯誤。大部分都能用 `curl -N` 與瀏覽器 DevTools 在幾分鐘內確認。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 事件延遲很久，然後好幾則一起到 | proxy 緩衝（nginx `proxy_buffering on`）、壓縮緩衝或應用層沒有 flush | `curl -N` 從應用程式往外一段一段打，找出第一個「事件攢成一批」的位置 | 回 `X-Accel-Buffering: no` 或對該路徑 `proxy_buffering off`；SSE 不壓縮；每個事件後 flush |
| 連線每 60 秒左右斷一次並重連 | 閒置逾時（nginx `proxy_read_timeout`、LB idle timeout）且沒有心跳 | 斷線間隔非常規律；對照路徑上各設備的逾時設定 | 每 15–30 秒送註解心跳；對 SSE 路徑調長 `proxy_read_timeout` |
| 部署或斷線後漏掉事件 | server 不理會 `Last-Event-ID`，或事件只存在單一 process 的記憶體 | 用 `curl -H 'Last-Event-ID: N'` 測試是否補發；檢查事件紀錄的位置 | 事件存到共用的事件紀錄；依 id 補發；超出保留範圍送 reset |
| `onmessage` 一直沒被呼叫，但 DevTools 看得到資料 | 事件帶了 `event:` 欄位，只能用 `addEventListener` 接；或事件結尾少了空行 | DevTools 的 EventStream 分頁看 type；`curl -N` 看每個事件後是否有空行 | 前端用對應名稱的 `addEventListener`；server 每個事件以 `\n\n` 結尾 |
| 頁面突然不再更新，console 只有一個 error | 回應不是 200（例如 session 過期回 401）或 Content-Type 錯，EventSource 進入 CLOSED 不再重連 | `onerror` 裡印 `readyState`；DevTools 看最後一次請求的狀態碼 | 前端在 `readyState === 2` 時處理（重新登入、重建連線）；server 用 204 表示「刻意停止」 |
| 開第七個分頁就整頁載不出來 | HTTP/1.1 每主機約 6 條連線的上限被 SSE 佔滿 | DevTools 中請求停在 Stalled；`curl -sv` 看 edge 是否只回 HTTP/1.1 | edge 啟用 HTTP/2／HTTP/3；SSE 放獨立子網域；用 BroadcastChannel 讓分頁共用一條 |
| 尖峰時 gunicorn worker 全滿，或 SSE 每 30 秒被切斷 | SSE 跑在 sync worker 上：每條佔一個 worker，且超過 `--timeout` 被殺 | gunicorn log 出現 worker timeout；連線數接近 worker 數 | 把 SSE 移到 ASGI／async 服務（uvicorn 或 gunicorn 的 async／ASGI worker） |
| long polling 偶爾漏訊息 | 沒有 cursor，回應與下一個請求之間的空檔中的事件遺失 | 在 server log 中找「事件產生時沒有掛著的請求」的時間點 | 請求帶 `since` cursor，server 回傳 cursor 之後的全部事件 |
| 部署後 API 與即時服務 CPU 尖峰 | 所有 client 在同一個 retry 時間點重連（驚群），每個都要驗證與補發 | 新連線數在部署時刻出現整齊的尖峰 | 分批關閉連線、用帶隨機值的 `retry:`、補發走快取 |

除錯的通則是依序回答：**事件有沒有產生、有沒有寫出去、卡在哪一層、到了瀏覽器有沒有被解析**。SSE 就是純文字的 HTTP，`curl -N` 看到的就是瀏覽器看到的，不需要特殊工具。

## 31.15 動手練習

1. **延伸實驗一：拉長 short polling 的間隔**。把實驗一的 `POLL_EVERY` 改成 0.6 秒，重新執行，記錄 short polling 的請求數與平均、最大延遲，並和 31.11 節模擬程式的公式比較。
   答案要點：請求數降到約 4 次（2.4 ÷ 0.6），平均延遲上升到幾百毫秒，最大延遲接近 0.6 秒，與「平均約半個間隔、最差一個間隔」的公式一致；事件數仍是 6，但可能出現一次回應帶回多則事件的情況，因為兩則事件落在同一個間隔裡。

2. **延伸實驗二：把保留範圍縮小**。把實驗二的 `KEEP` 從 4 改成 1，觀察 conn 2 的行為。再思考：在 production 中，保留範圍要怎麼決定？
   答案要點：conn 2 帶 `Last-Event-ID: 3` 回來時，緩衝裡只剩 id 5，id 4 已經被擠掉，server 送出 reset，client 改抓完整狀態。保留範圍應該涵蓋「最常見的斷線時間 × 事件產生速率」再加上餘量，例如部署期間的重連時間加上手機切換網路的時間；reset 次數是驗證這個設定是否足夠的指標。

3. **用 curl 觀察 SSE 與緩衝**（真實工具）。在本機執行實驗二的 server 部分（把 `serve_forever` 改成在前景執行並固定一個 port），用 `curl -N -i` 打本機的 `127.0.0.1:PORT/rooms/7/events` 觀察原始輸出，再拿掉 `-N` 比較一次。
   答案要點：`-i` 會印出回應 header，可以看到 `Content-Type: text/event-stream` 與沒有 `Content-Length`；`-N` 讓事件即時出現。沒有 `-N` 時，curl 的輸出緩衝可能讓事件延後出現，這正是「觀察工具本身也會緩衝」的例子，除錯 SSE 時一定要加 `-N`。

4. **用 DevTools 觀察 EventSource 的重連**（真實工具）。在本機起一個 SSE server，寫一個最小網頁用 `new EventSource()` 連它，打開 DevTools 的 Network 面板，然後在 server 端強制結束程式，再重新啟動。
   答案要點：EventStream 分頁會即時列出事件；server 結束後，`onerror` 觸發、`readyState` 變成 0，過了 retry 時間後出現一個新的 eventsource 請求，在 Headers 分頁可以看到它帶著 `Last-Event-ID`。把 server 改成回 500，就會看到 `readyState` 變成 2，之後不再出現新請求。

5. **手算：HTTP/1.1 的分頁上限與 polling 的成本**。一位老師在同一個瀏覽器開了 5 個後台分頁，每個分頁都開一條 SSE 到 `www.shengsheng.example`，同時每個分頁每 10 秒向同一個主機 poll 一次。如果 edge 只支援 HTTP/1.1，第 6 個分頁開啟時會發生什麼？改用 HTTP/2 後呢？
   答案要點：5 條 SSE 佔了 6 條上限中的 5 條，所有分頁的 polling 與第 6 個分頁的載入全部擠在剩下的 1 條連線上依序進行，頁面明顯變慢；第 6 個分頁再開 SSE，連線額度就完全用盡，之後所有到這個主機的請求都要等。改用 HTTP/2 後，全部變成同一條連線上的 stream，在 `SETTINGS_MAX_CONCURRENT_STREAMS`（常見約 100）之內都不會互相阻擋；更好的做法是讓分頁共用一條 SSE。

6. **改寫實驗三：模擬心跳在緩衝 proxy 前的效果**。在實驗三的 upstream 裡，每則事件後面加上大量心跳註解行（例如每次 `: ` 加 1,000 個空白），觀察 buffered 那一欄的延遲是否改善，並說明這為什麼不是好的修法。
   答案要點：心跳 bytes 讓緩衝區更快填滿，事件會比較早被送出，看起來「改善了」；但延遲取決於填滿緩衝區需要多久，仍然不是即時的，而且浪費頻寬。這種「塞 padding 把緩衝擠出來」的做法只適合在無法控制中間設備時當作權宜之計，正解是關掉那一層的緩衝。

## 本章重點整理

- HTTP 是一問一答的 pull 模型；在 HTTP 上做 server push 有三條路線：short polling 一直問、long polling 掛著請求等事件、SSE 用一個永不結束的回應持續寫入。
- short polling 的請求數由時間決定（人數 × 時長 ÷ 間隔），平均延遲約半個間隔、最差一個間隔，縮短間隔只能用請求數換延遲；公開且共用的資料可以讓 CDN 吸收輪詢。
- long polling 的請求數約等於事件數加逾時次數，延遲約單程傳輸時間；一定要用 cursor，否則回應與下一個請求之間的空檔會漏事件；掛著的時間要短於路徑上最短的逾時。
- SSE 的回應是 `Content-Type: text/event-stream` 的 UTF-8 文字，由 `data`、`event`、`id`、`retry` 欄位與冒號開頭的註解行組成，空行才會把事件送出，連線結束時沒有空行結尾的半個事件會被丟棄。
- `id` 設定的是會持續保留的「最後事件 ID」，瀏覽器重連時自動放進 `Last-Event-ID` header；補發由 server 實作，事件紀錄必須跨實例共用，超出保留範圍時要送 reset 讓前端重抓完整狀態。
- EventSource 在連線中斷或回應正常結束時，等 retry 毫秒後自動重連；回應不是 200 或 Content-Type 不對時進入 CLOSED、不再重連，所以 server 用 204 表示「別再連了」，前端要在 `readyState === 2` 時自行處理。
- 心跳註解行同時解決兩件事：重設路徑上各設備的閒置計時器，以及透過寫入盡早發現已經消失的 client；間隔要短於路徑上最短的閒置逾時，常見 15 到 30 秒。
- HTTP/1.1 下每條 SSE 獨佔一條連線，瀏覽器對同一主機約 6 條的上限由所有分頁共用；HTTP/2 與 HTTP/3 把 SSE 變成 stream，解除了瀏覽器端的上限，但不會減少 proxy 後方 server 端的連線數。
- 事件「一批一批到」幾乎都是緩衝造成的：nginx 預設的 `proxy_buffering`、壓縮、應用程式沒有 flush、CDN；修法是回 `X-Accel-Buffering: no` 或關閉該路徑的緩衝與壓縮，並用 `curl -N` 一段一段往前推找出問題層。
- SSE 把成本從請求數轉成同時連線數，server 必須用 async 模型承載長連線；sync worker 會被長回應佔滿或因逾時被殺，fan-out 要防慢 client 拖垮其他連線，部署時要防所有 client 同時重連的驚群。
- 選型的判斷依據是方向、即時性與中間設備：晚幾秒沒關係且資料共用用 short polling，server 往 client 的即時推送用 SSE，雙向高頻或二進位用 WebSocket，long polling 是無法關掉緩衝時的後備方案。

## 延伸問答

> [!question]- Q1. 概念辨析：long polling 和 SSE 的延遲都約等於單程傳輸時間，為什麼還說 SSE 比較好？
> 兩者在「沒有事件時」的行為幾乎一樣：都有一個請求或連線掛在 server 上。差別出現在「事件密集」與「斷線」的時候。long polling 每送出一批事件就要結束回應，client 再發一個新請求，每次都要付出完整的 request header（含 cookie）、server 端的驗證與路由成本，而且回應與下一個請求之間有一段空檔，必須靠 cursor 才不會漏訊息。事件越密集，long polling 越接近 short polling 的成本。
>
> SSE 只有一個請求，之後每個事件只是 body 裡的幾行文字，沒有額外的 header 與驗證；空檔問題不存在，因為連線一直開著。斷線補發也標準化了：`id` 欄位與 `Last-Event-ID` header 是規格的一部分，瀏覽器自動處理，server 只需要依 id 補發。long polling 的 cursor 則完全是自己約定的格式。所以除非路徑上有無法關閉的緩衝，否則 SSE 在請求數、實作一致性與可觀察性上都比 long polling 好。

> [!question]- Q2. 手算：3,000 名學生在等候室，short polling 間隔 3 秒，RTT 80 ms。每秒請求數、平均延遲與最差延遲大約是多少？改成 SSE、心跳 20 秒，每秒的心跳寫入是多少？
> short polling 的每秒請求數是 3,000 ÷ 3 ＝ 1,000。延遲的計算要拆成兩部分：事件發生後，平均要等半個間隔（1.5 秒）才會有下一個請求抵達 server，最差要等一整個間隔（3 秒）；再加上回應傳回 client 的單程時間約 40 ms。所以平均延遲約 1.54 秒，最差約 3.04 秒。嚴格來說請求本身在路上也有 40 ms，但它只是把輪詢的相位整體平移，不影響平均等待。
>
> 改用 SSE 後，延遲約為單程的 40 ms 加上 server 處理事件的時間；心跳寫入是 3,000 ÷ 20 ＝ 每秒 150 次，每次只有幾個 bytes。請求數從每秒 1,000 降到幾乎為 0（只剩重連），代價是 server 要同時保持 3,000 條連線。這個計算也說明了為什麼「把 polling 間隔從 3 秒縮到 1 秒」很少是好主意：請求數變成 3 倍，平均延遲仍有 0.5 秒。

> [!question]- Q3. 你在 production 看到：SSE 在 staging 一切正常，上線後事件總是延遲，而且延遲的時間不固定，有時 2 秒、有時 20 秒。可能是什麼？怎麼查？
> 「staging 正常、production 不正常」代表差異在環境而不在程式，最常見的就是 production 路徑上多了一層 staging 沒有的緩衝：CDN、另一層 nginx、WAF，或 production 的 nginx 設定開了 gzip 壓縮所有文字類型。延遲不固定是緩衝的典型特徵：事件要等緩衝區滿才送出，而填滿的速度取決於那段時間有多少事件與心跳；事件密集時延遲短，安靜時延遲長，甚至一直等到閒置逾時切斷連線才一次倒出。
>
> 查法是用 `curl -N` 一段一段往前推：先在即時服務主機上直接打應用程式，再打 nginx，再從外部打 CDN，找出第一個「事件不再即時」的位置。同時比較 staging 與 production 回應 header 的差異，例如 production 是否多了 `content-encoding: gzip`、`via` 或 CDN 特有的 header。找到那一層後，對 SSE 路徑關閉緩衝與壓縮；如果那一層是無法設定的設備，就讓 SSE 繞過它，或退回 long polling。

> [!question]- Q4. 面試題：EventSource 已經會自動重連了，為什麼 server 端還要處理 Last-Event-ID？不處理會怎樣？
> 自動重連只保證「連線會回來」，不保證「資料是連續的」。從連線中斷到重連成功之間至少有 retry 等待時間（通常幾秒），再加上斷線被發現的時間；這段期間 server 產生的事件，沒有任何連線可以送出。如果 server 重連後只送「從現在開始」的新事件，這些事件就永遠消失了，前端的狀態會和 server 不一致，例如故事中停在舊畫面、沒看到「小測驗開始」的學生。
>
> 瀏覽器做的只是把最後收到的 id 放進 `Last-Event-ID` header，規格不知道你的事件存在哪裡，所以補發一定要 server 實作：從共用的事件紀錄中找出這個 id 之後的事件先送出，再接上即時事件，並處理兩者交界處的重複。還要考慮補不回來的情況：id 太舊、事件紀錄已經過期，這時要送一個讓前端重抓完整狀態的事件。不處理 `Last-Event-ID`，等於把 SSE 退化成「盡力而為」的通知，只適合漏掉也無所謂的資料。

> [!question]- Q5. 看 log 找原因：nginx 的 access log 裡，SSE 請求的 `$request_time` 幾乎都是 60.0 秒左右，狀態碼 200，而前端的重連次數很高。這代表什麼？
> SSE 的 access log 是在連線結束時才寫出的，`$request_time` 是整條連線從開始到結束的時間，不是處理時間。幾乎都剛好 60 秒，而且狀態碼是 200（回應 header 早就送出了，之後的斷線不會改變狀態碼），強烈暗示連線是被一個 60 秒的計時器切斷的。nginx 的 `proxy_read_timeout` 預設 60 秒，指的是兩次從 upstream 讀到資料之間的最長間隔；等候室安靜時沒有事件，也沒有心跳，nginx 就在第 60 秒關閉連線，前端隨即重連，所以重連次數很高。
>
> 確認方法是看 nginx 的 error log 是否有 upstream timed out 的紀錄，以及斷線時刻與最後一個事件的時間差是否都是 60 秒。修法是讓 server 每 15 到 30 秒送一行註解心跳，並對 SSE 路徑把 `proxy_read_timeout` 調到遠大於心跳間隔。也要一併檢查 LB 與 CDN 的閒置逾時，心跳間隔必須短於路徑上最短的那一個。

> [!question]- Q6. 設計取捨：為什麼不乾脆把等候室也改成 WebSocket？既然教室聊天已經用 WebSocket 了。
> 技術上可以，但要比較兩者為這個需求付出的成本。等候室的資料流幾乎是單向的：server 告訴學生「老師上線了」「課程延後」，學生不需要透過這條通道送任何東西。SSE 正好符合這個形狀，而且它是普通的 HTTP：現有的 cookie 驗證、CORS、nginx 路由、access log、HTTP/2 多工都直接適用；斷線重連與 `Last-Event-ID` 由瀏覽器處理。WebSocket 需要 proxy 支援 Upgrade、自己實作 ping、重連、補發與訊息格式（第 32、33 章），這些工作對單向通知來說是多餘的。
>
> 反過來的考量也存在：如果等候室未來要加入「學生可以傳訊息給老師」或即時的出席回報，而且頻率很高，那麼共用教室的 WebSocket 連線可能更划算，因為一條連線就能同時承載雙向資料，也少一種協定要維運。所以結論是依資料方向與頻率選擇，而不是依「團隊已經有什麼」選擇；同一個產品裡同時有 SSE 與 WebSocket 很正常。

> [!question]- Q7. 情境判斷：Rita 審查時發現前端為了在 EventSource 裡帶驗證，把 access token 放在 URL：`/rooms/7/events?token=eyJ...`。問題在哪裡？要怎麼改？
> EventSource 不能設定自訂 header，所以有人會把 bearer token 放進 query string。問題是 URL 會被記錄在很多地方：nginx 與 CDN 的 access log、瀏覽器歷史、各種監控與錯誤回報工具，甚至在某些情況下透過 Referer 外洩。一個可以拿來呼叫 API 的 token 出現在這麼多地方，等於把憑證複製了很多份，任何能讀 log 的人都能冒用，而且 SSE 是長連線，token 在 URL 裡的時間往往比它應有的壽命更久。
>
> 比較好的做法有兩種。第一種是用 cookie 驗證：同站時 cookie 自動帶上，跨來源時用 `withCredentials: true` 並在 server 設定正確的 CORS（指定來源與允許 credentials），cookie 設 `HttpOnly`、`Secure` 與適當的 `SameSite`。第二種是一次性的短效票券：前端先用正常的 API（帶 `Authorization` header）換一張幾十秒內過期、只能用一次、只能用在這個 SSE 端點的票券，放進 URL；server 驗證後立刻作廢。另外 access log 也應該過濾掉 query string 裡的敏感參數，作為縱深防禦。

> [!question]- Q8. 看封包找原因：用 curl 打 SSE 端點，看到 header 正常回來，接著每 15 秒出現一行 `: hb`，但老師明明已經上線了，事件卻一直沒出現。server log 顯示事件已經寫出。可能是什麼？
> 心跳能即時出現，說明路徑上沒有緩衝問題，連線本身也是活的；server 又說事件已寫出，那麼問題很可能在「事件本身的格式」或「事件被送到哪裡」。第一個嫌疑是格式：事件結尾少了空行。如果 server 寫的是 `data: {...}\n` 而不是 `data: {...}\n\n`，這個事件就一直停在解析器裡，要等下一個空行才會被送出；而心跳 `: hb\n\n` 裡的空行反而可能把它「推出去」，造成事件晚一個心跳週期才出現，或和下一個事件黏在一起。用 `curl -N` 觀察時，要注意 `data:` 行後面有沒有空行。
>
> 第二個嫌疑是事件根本沒寫到這條連線：例如有多個即時服務實例，事件只送給了產生它的實例上的連線，而這條 curl 連線在另一個實例上（fan-out 沒有經過 pub/sub）。這時 server log 確實有「寫出」，但寫給的是別人。確認方法是在 log 裡印出每次寫入的連線識別與實例名稱，或用 `curl -sv` 看回應 header 裡的實例標記。第三個可能是前端問題，但這題是用 curl 觀察的，可以排除 `addEventListener` 名稱不符這類前端錯誤。

## 延伸閱讀

- WHATWG〈HTML Living Standard〉的 Server-sent events 一節：`text/event-stream` 格式、解析演算法與 EventSource 的重連規則
- RFC 9110〈HTTP Semantics〉：請求與回應的語意、狀態碼 200 與 204
- RFC 9112〈HTTP/1.1〉：chunked transfer coding 與以關閉連線界定訊息長度
- RFC 9113〈HTTP/2〉：stream、DATA frame 與 `SETTINGS_MAX_CONCURRENT_STREAMS`
- RFC 6202〈Known Issues and Best Practices for the Use of Long Polling and Streaming in Bidirectional HTTP〉：long polling 與 HTTP streaming 的問題整理
- nginx 官方文件 ngx_http_proxy_module：`proxy_buffering`、`proxy_read_timeout` 與 `X-Accel-Buffering`
- MDN Web Docs〈Using server-sent events〉與〈EventSource〉：瀏覽器端 API 與開發者工具的使用
