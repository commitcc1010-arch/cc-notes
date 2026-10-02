---
chapter: 21
title: HTTP 快取、Cookie 與內容協商
part: 5
---

# 第 21 章　HTTP 快取、Cookie 與內容協商

> [!abstract] 本章地圖
> **核心問題**：同一個 URL 的回應，誰可以存、存多久、過期了怎麼確認、該給哪一個版本？瀏覽器又依什麼規則把 cookie 帶回去？
>
> **你會學到**：
> - 分辨 private cache 與 shared cache，讀懂 `Cache-Control` 的每個常用指令，算出一份回應還「新鮮」多久
> - 用 `ETag`、`Last-Modified` 與條件請求拿到 304，並用 `If-Match` 防止兩個人互相覆蓋
> - 解釋 cache key 與 `Vary`，設計內容協商（語言、格式、壓縮）而不把 CDN 的命中率打爛
> - 看懂 gzip 的 header、`Content-Encoding` 與 `Transfer-Encoding` 的差別，以及 Range 請求如何支撐影片拖曳與續傳
> - 逐條說出瀏覽器存 cookie 與送 cookie 的規則（Domain、Path、Secure、過期、前綴），並分辨各種 redirect
> - 用 Python 在 127.0.0.1 上寫出條件請求 server、簡化版 shared cache、cookie jar，並重現與修正「個人化頁面被 CDN 快取」的事故
>
> **前置知識**：第 1 章（一個網頁請求的全貌）、第 20 章（HTTP/1.1 的請求、回應、method 語意與 status code）

## 21.1 故事：「為什麼首頁寫著別人的名字？」

聲聲 Live 每晚八點是尖峰，上萬個學生在前後兩分鐘內打開首頁。首頁是 Flask 產生的，第 1 章量過一次 view 大約 30 ms，但尖峰時 origin（原始伺服器，CDN 背後真正產生內容的那台服務）的 CPU 會衝到八成。小晴接到一張任務單：「提高 CDN 命中率，降低首頁對 origin 的壓力」。小晴查了一下，發現首頁回應帶著 `Cache-Control: private, max-age=0`，CDN 完全不存它；於是把它改成 `Cache-Control: public, max-age=60`，在 staging 用無痕視窗測了幾次，首頁果然變快，CDN 儀表板上的命中率從 41% 跳到 78%。

上線後二十分鐘，客服轉來一則訊息：一位學生打開首頁，看到的是「歡迎回來，小安！下一堂：日文會話（美咲老師）」，可是這位學生不叫小安。接著又來了三則。資安工程師 Rita 立刻把這件事升級為個資事故：別人的名字、課表、老師名稱都屬於不該外流的資料。阿德先把設定改回、請 CDN 清除（purge，把已快取的內容刪掉，第 25 章）首頁，事故在十二分鐘內止血。

```text
 21:58  小安（已登入）──GET / Cookie: sid=A──► CDN edge ──MISS──► origin（Flask）
                                                 │◄── 200「歡迎回來，小安」
                                                 │    Cache-Control: public, max-age=60
                                                 │    ← edge 把這份回應存起來，key = "/"
 21:58  阿哲（已登入）──GET / Cookie: sid=B──► CDN edge ──HIT──► 直接回「歡迎回來，小安」
 21:59  訪客（未登入）──GET /──────────────► CDN edge ──HIT──► 直接回「歡迎回來，小安」
          ……接下來 60 秒，所有連到這個 edge 的人都看到小安的首頁
```

這張圖是事後檢討時阿德畫在白板上的。第一列，小安是那個 edge 在快取過期後第一個造訪的人，edge 沒有存貨，只好向 origin 要；origin 依小安的 cookie 產生個人化頁面，卻在回應上標了 `public, max-age=60`，等於告訴所有中間的快取「這份東西大家都能用，60 秒內不用回來問我」。第二、三列，edge 的 cache key（快取用來找存貨的索引）預設只有 URL，不包含 cookie，所以阿哲和訪客的請求在 edge 看來和小安的一模一樣，直接拿到小安的頁面。每 60 秒過期一次，下一個 MISS 的人就成了新的「受害者」。

檢討會上小晴很沮喪：「我只改了一個 header。」阿德說，這正是 HTTP 快取危險的地方：一行字會被瀏覽器、CDN、nginx 這些你看不到的程式各自解讀。同一週，團隊的待辦清單上還有三張相關的單：老師在兩個分頁編輯自我介紹，後存的那一頁把先存的蓋掉了；切換成繁體中文後，課程列表偶爾還是日文；學生在課程錄影回放中拖曳進度條，影片每次都從頭下載。這一章就是要把這幾件事背後的機制講清楚：快取的新鮮度與驗證、cache key 與 `Vary`、內容協商與壓縮、Range、cookie 的規則，最後在 21.11 節把首頁事故在你的電腦上重現，再依第 1 章就定下的原則（個人化頁面用 `Cache-Control: private`）修好。

## 21.2 快取在哪裡：private cache 與 shared cache

**快取**（cache）是把某次請求得到的回應存起來，下次遇到「等價」的請求時直接拿來用，不再去問 origin。HTTP 快取的規格是 RFC 9111，它和 RFC 9110（HTTP 語意）一起在 2022 年發布。快取的好處有三個：使用者少等一趟網路（美國學生到台北的 RTT 是 180 ms，第 1 章）、origin 少做一次工、網路少傳一份 bytes。代價只有一個，但很嚴重：你給出去的可能是舊的，或者是別人的。

一個請求從瀏覽器到 Flask，沿路可能經過好幾層快取，而它們分成兩類。**private cache**（私有快取）只服務一個使用者，最典型的是瀏覽器的 HTTP cache：小安的瀏覽器存的東西只會給小安用。**shared cache**（共享快取）服務很多使用者，例如 CDN 的 edge、公司的 forward proxy、nginx 的 `proxy_cache`。兩者規則最大的差別是：shared cache 不能存標了 `private` 的回應，因為它無法保證下一個拿到的是同一個人。

```text
 小安的瀏覽器                      CDN edge                 nginx            gunicorn ─► Flask
 ┌──────────────┐  HTTPS   ┌─────────────────┐       ┌──────────────┐
 │ HTTP cache   │ ───────► │ shared cache    │ ────► │ proxy_cache  │ ─────► origin
 │（private）   │          │ 很多使用者共用  │       │（通常不開）  │
 └──────────────┘          └─────────────────┘       └──────────────┘
   看 max-age              看 s-maxage（優先）          同 shared cache
   可以存 private           不能存 private
   no-store：不存           no-store：不存
 ─────────────────────────────────────────────────────────────────────────────────
 Service Worker 的 Cache API 是另一套由 JavaScript 控制的儲存，不受 Cache-Control 支配
```

圖由左往右讀。最左邊的瀏覽器快取是 private cache，它看 `max-age` 決定存多久，可以存 `private` 的回應。中間的 CDN 是 shared cache，如果回應同時有 `max-age` 和 `s-maxage`，它優先看 `s-maxage`（s 是 shared 的意思），而且遇到 `private` 一律不存。nginx 若開了 `proxy_cache` 也是 shared cache，聲聲 Live 沒有開。最底下一行提醒一個常見的混淆：前端用 Service Worker 寫進 Cache API 的東西，是程式自己決定的，HTTP 快取的規則管不到它。

快取要回答的問題可以歸納成四個，本章後面就依這個順序展開。第一，**能不能存**：status code、`no-store`、`private`、請求是否帶 `Authorization`。第二，**能用多久**：新鮮度（freshness），21.3 節。第三，**過期了怎麼辦**：驗證（validation），用條件請求問 origin「我手上的還是最新的嗎」，21.4 節。第四，**哪些請求算等價**：cache key 與 `Vary`，21.5 節。故事裡的事故同時錯了第一題和第四題：個人化頁面不該讓 shared cache 存，而 cache key 又沒有區分使用者。

> [!warning] 常見誤解
> 「HTTPS 的內容不會被快取。」HTTPS 只保護傳輸途中的機密性；CDN 終結 TLS（第 19 章）之後看得到明文，一樣會依 `Cache-Control` 存起來。瀏覽器也照常快取 HTTPS 回應。要不要快取，看的是 header，不是 scheme。

## 21.3 新鮮度：Cache-Control 決定能用多久

**新鮮度**（freshness）是快取判斷「不用問 origin 就能直接用」的依據。每份存起來的回應有一個**新鮮期**（freshness lifetime），通常由 origin 用 `Cache-Control: max-age=秒數` 給定；快取另外記錄這份回應的**年齡**（age），也就是它從 origin 產生到現在過了多久。規則只有一行：年齡小於新鮮期，就是新鮮的（fresh），可以直接用；否則就是過期的（stale）。例如課程列表標了 `max-age=300`，CDN 在 20:00:00 拿到，20:04:59 之前都直接回給學生，20:05:00 之後就得先去驗證。

年齡不只是「我存了多久」。如果 CDN 從上一層快取（例如 origin shield，第 25 章）拿到的回應已經放了 40 秒，上一層會在回應裡加上 `Age: 40`，下一層要把這 40 秒算進去，否則新鮮期會在每一層被重新計算、越疊越長。所以在 `curl -I` 看到 `Age: 57` 而 `max-age=60`，意思是這份回應只剩 3 秒就過期了。

`Cache-Control` 有很多指令（directive），它們可以出現在回應，也有一部分可以出現在請求。下表是回應端最常用的指令：

| 指令 | 意思 | 誰會遵守 | 聲聲 Live 的例子 |
|---|---|---|---|
| `max-age=N` | 新鮮期 N 秒 | 所有快取 | 課程列表 `max-age=300` |
| `s-maxage=N` | 只給 shared cache 的新鮮期，優先於 `max-age` | CDN、proxy | 匿名首頁 `max-age=0, s-maxage=60` |
| `public` | 明確允許 shared cache 存（即使請求帶 `Authorization`） | 所有快取 | 公開的老師介紹頁 |
| `private` | 只有 private cache（瀏覽器）可以存 | shared cache 不存 | 個人化首頁、`/v1/me` |
| `no-cache` | 可以存，但每次使用前都要先向 origin 驗證 | 所有快取 | 今日課表 API |
| `no-store` | 完全不要存（記憶體與磁碟都不要） | 所有快取 | 付款結果、TOTP 設定頁 |
| `must-revalidate` | 過期後一定要驗證成功才能用，連不上 origin 就回錯誤 | 所有快取 | 價格、庫存 |
| `immutable` | 新鮮期內內容絕不會變，重新整理也不用驗證 | 支援的瀏覽器 | `app.3f9c.js` 這類檔名帶 hash 的靜態檔 |
| `stale-while-revalidate=N` | 過期後 N 秒內可先給舊的，同時在背景驗證 | 支援的快取 | 匿名首頁 |
| `stale-if-error=N` | origin 出錯時，過期後 N 秒內可以給舊的 | 支援的快取 | 課程目錄 |

這張表裡最容易被誤會的是 `no-cache` 和 `no-store`。`no-cache` 的字面像「不要快取」，實際上是「可以存，但不能不問就用」，配合 ETag 可以讓每次驗證都只換來一個沒有 body 的 304，非常省頻寬。`no-store` 才是真正的「不要存」。另一組要分清楚的是 `private` 與 `no-store`：`private` 只禁止 shared cache，小安的瀏覽器仍然可以存小安的首頁；如果連瀏覽器都不該留下（例如共用電腦上的付款紀錄），要用 `no-store`。

`stale-while-revalidate`（RFC 5861）值得單獨說明，它解決的是「過期那一刻的延遲尖峰」。沒有它的時候，快取在新鮮期結束後收到的第一個請求必須等 origin 回應；有了它，快取可以先把舊的給出去，再在背景向 origin 驗證，使用者感受不到那一趟。下面的時間軸是匿名首頁 `Cache-Control: public, max-age=0, s-maxage=60, stale-while-revalidate=30` 在 CDN 上的生命週期：

```text
 age(秒)  0                          60                 90
          ├──────────── fresh ────────┼── stale-while ────┼──────── stale ─────────►
          │  直接回應（HIT）           │  revalidate       │  必須先驗證才能回應
          │                            │  先回舊的，背景    │ （使用者要等 origin）
          │                            │  發條件請求        │
          ▲                            ▲                   ▲
       CDN 存入                      新鮮期結束          超過容忍範圍
 瀏覽器端：max-age=0 → 每次都要問 CDN（CDN 在 fresh 期內很快就能回答）
```

圖的上半是 CDN 的視角：0 到 60 秒是 fresh，直接命中；60 到 90 秒是 stale-while-revalidate 的容忍期，先回舊的、背景驗證，驗證成功後年齡歸零，重新回到 fresh；超過 90 秒才會讓使用者同步等待 origin。最下面一行是瀏覽器的視角：`max-age=0` 讓瀏覽器每次都要問，但它問的是近在咫尺的 CDN，而不是遠方的 origin。`s-maxage` 與 `max-age` 分開設，就是「讓 CDN 擋住流量，同時讓使用者很快看到更新」的常用組合。

如果回應完全沒有 `Cache-Control` 也沒有 `Expires`，快取不一定不存。RFC 9111 允許快取對某些 status code（例如 200、301、404）做**啟發式新鮮度**（heuristic freshness）：如果回應有 `Last-Modified`，常見做法是取「距離上次修改的時間」的 10% 當作新鮮期。一個三十天前修改的 CSS 檔，可能在沒有任何指示的情況下被快取三天。這就是「我沒設快取，為什麼使用者還是拿到舊檔」的常見答案：沒設不等於不快取，**明確地寫出 `Cache-Control`** 才是唯一可預測的做法。舊式的 `Expires`（一個絕對時間）與 `Pragma: no-cache` 仍會在老系統看到，有 `max-age` 時 `Expires` 會被忽略。

> [!tip]
> 請求也可以帶 `Cache-Control`。瀏覽器的「重新整理」通常會讓請求帶上 `max-age=0`，要求快取先驗證；強制重新整理（Shift＋重新整理）則帶 `no-cache`。所以「我按了重新整理就好了」不能證明 CDN 上的版本是對的，要用不帶這些 header 的 `curl` 再確認一次。

## 21.4 驗證：ETag、Last-Modified 與條件請求

回應過期以後，快取不必整份重抓，而是發一個**條件請求**（conditional request）：帶上它手上那份的「版本識別」，問 origin「從這個版本之後有變嗎」。沒變，origin 回 **304 Not Modified**，沒有 body，快取把手上那份的年齡歸零繼續用；變了，origin 回一般的 200 和新內容。用來識別版本的東西叫 **validator**（驗證器），HTTP 有兩種。

第一種是 **`Last-Modified`**：資源最後修改的時間，例如 `Last-Modified: Mon, 21 Sep 2026 14:13:20 GMT`。快取下次用 `If-Modified-Since` 把這個時間送回去。它簡單，但精度只到秒，同一秒內改兩次就分辨不出來；而且「時間」不一定等於「內容」，例如重新部署後檔案時間變了、內容卻沒變，就會白白重傳。第二種是 **`ETag`**（entity tag）：origin 替這一版內容取的不透明字串，例如 `ETag: "b3294d1ad6ba"`，常見做法是內容的 hash 或資料庫的版本號。快取下次用 `If-None-Match` 送回去。兩者都送時，server 要以 `If-None-Match` 為準。

```text
 瀏覽器                                         origin（老師介紹 API）
   │── GET /api/teachers/misaki/intro ──────────────►│
   │◄─ 200 OK  ETag: "b3294d1ad6ba"  ─────────────────│  body 79 bytes
   │          Cache-Control: no-cache                 │
   │   （存起來；no-cache → 每次使用前都要驗證）       │
   │                                                  │
   │── GET …/intro  If-None-Match: "b3294d1ad6ba" ───►│  比對目前版本
   │◄─ 304 Not Modified  ETag: "b3294d1ad6ba" ────────│  沒有 body
   │   （用自己存的 79 bytes）                         │
   │                                                  │
   │── PUT …/intro  If-Match: "b3294d1ad6ba" ────────►│  版本相符才寫入
   │◄─ 200 OK  ETag: "960b2f0e9b64" ──────────────────│
   │                                                  │
 （另一個分頁仍拿著舊 ETag）                            │
   │── PUT …/intro  If-Match: "b3294d1ad6ba" ────────►│  版本不符
   │◄─ 412 Precondition Failed ───────────────────────│  拒絕覆寫
```

前兩組往返是快取驗證：第一次拿到 200 和 ETag，之後每次用 `If-None-Match` 問，內容沒變就只換來 304。304 雖然沒有 body，但仍然要帶 `ETag`、`Cache-Control`、`Vary` 這些 header，讓快取更新它手上那份的中繼資料。後兩組往返是同一套 validator 的另一個用途：**樂觀並行控制**（optimistic concurrency control）。這正好對應待辦清單上「老師在兩個分頁編輯，後存的覆蓋先存的」那張單，這種問題叫 **lost update**（更新遺失）。PUT 帶上 `If-Match`，意思是「只有目前版本還是我讀到的那一版，才寫入」；第二個分頁拿的是舊 ETag，server 回 **412 Precondition Failed**，前端就能提示「內容已被更新，請重新載入」，而不是默默蓋掉。若 server 要求所有更新都必須帶條件，沒帶的請求可以回 **428 Precondition Required**。

ETag 還分強弱。**強 ETag**（例如 `"b3294d1ad6ba"`）承諾 byte 完全相同；**弱 ETag**（前面加 `W/`，例如 `W/"b3294d1ad6ba"`）只承諾語意相同，例如同一份 HTML 只差在壓縮方式或空白。`If-None-Match` 用**弱比較**，`W/"x"` 和 `"x"` 視為相符，因為快取驗證只在乎「能不能繼續用」；`If-Match` 與 Range 的 `If-Range` 用**強比較**，因為寫入和拼接 byte 需要確定是同一份 bytes。nginx 對回應做 gzip 時會把強 ETag 改成弱 ETag，就是因為壓縮後的 bytes 已經和原檔不同。

| 條件 header | 搭配的 validator | 比較方式 | 條件成立時 | 條件不成立時 | 典型用途 |
|---|---|---|---|---|---|
| `If-None-Match` | ETag | 弱比較 | GET 回 304 | 照常回 200 | 快取驗證 |
| `If-Modified-Since` | Last-Modified | 時間 ≤ | GET 回 304 | 照常回 200 | 快取驗證（沒有 ETag 時） |
| `If-Match` | ETag | 強比較 | 照常執行 | 回 412 | PUT／PATCH／DELETE 防覆寫 |
| `If-Unmodified-Since` | Last-Modified | 時間 ≤ | 照常執行 | 回 412 | 同上（較少用） |
| `If-Range` | 強 ETag 或日期 | 強比較 | 回 206 部分內容 | 回 200 整份 | 續傳時確保檔案沒換 |

表格的「條件成立時」一欄要小心讀：`If-None-Match` 的條件是「都不相符」，所以「相符」反而是條件不成立，GET 回 304；這個雙重否定是很多人自己實作時寫反的地方。另一個實務問題是 ETag 的產生方式。如果三台 origin 用各自的檔案 inode 或 mtime 算 ETag，同一份檔案在三台機器上會有三個 ETag，負載平衡把驗證請求送到另一台，就永遠拿不到 304。ETag 應該只由內容（hash）或資料版本決定，跨機器一致。

## 21.5 cache key 與 Vary：哪些請求算「同一個」

快取用 **cache key** 找存貨。RFC 9111 的基本 cache key 是「請求的 method 與目標 URI」，實務上 CDN 只快取 GET（和 HEAD），所以 key 幾乎就是完整的 URL（含 query string）。問題來了：同一個 URL，origin 可能依請求的 header 回不同的內容。學生送 `Accept-Language: ja` 拿到日文課程列表，送 `zh-TW` 拿到繁體中文，如果快取只用 URL 當 key，第一個人拿到什麼，之後所有人就拿到什麼，這就是待辦清單上「切換語言後偶爾還是日文」的原因。

**`Vary`** 是 origin 告訴快取「這份回應是依哪些請求 header 選出來的」的方式。回應帶 `Vary: Accept-Language`，快取就必須把請求的 `Accept-Language` 值也當作 key 的一部分；之後的請求只有在這些 header 的值相符時，才能用這份存貨。

```text
 回應：GET /courses → 200  Vary: Accept-Language   Cache-Control: public, max-age=300

 cache key（第一層：URL）           第二層：Vary 列出的請求 header 值
 ┌───────────────────────┐        ┌─────────────────────────────┬──────────────┐
 │ GET  /courses         │ ─────► │ Accept-Language = "ja"      │ 日文列表     │
 │                       │        ├─────────────────────────────┼──────────────┤
 │                       │        │ Accept-Language = "zh-TW"   │ 繁中列表     │
 │                       │        ├─────────────────────────────┼──────────────┤
 │                       │        │ Accept-Language = "zh-TW,   │ 繁中列表     │
 │                       │        │   zh;q=0.9,en;q=0.8"        │（又存一份！）│
 └───────────────────────┘        └─────────────────────────────┴──────────────┘
 Vary: Cookie → 每個 session 一格，命中率趨近 0；Vary: * → 永遠不命中
```

這張圖畫出兩層查找：先用 URL 找到這個資源，再用 `Vary` 指定的 header 值找到對應的版本（variant）。第三列揭露 `Vary` 的副作用：快取比對的是 header 的原始字串，`zh-TW` 和 `zh-TW,zh;q=0.9,en;q=0.8` 對人來說是同一個意思，對快取卻是兩格。瀏覽器送出的 `Accept-Language` 千變萬化，直接 `Vary: Accept-Language` 會讓同一份內容被存很多次、命中率下降。所以 CDN 常提供「正規化」：把 header 先歸類成少數幾個值（例如只留 `ja`、`zh-TW`、`en`）再當 key。最底下一行是兩個極端：`Vary: Cookie` 讓每個 session 都是獨立一格，等於不快取；`Vary: *` 表示「依你看不到的條件決定」，快取永遠無法重用。

`Vary` 的方向容易搞反：它列的是**請求** header，不是回應 header。最常見、也最該有的是 `Vary: Accept-Encoding`，因為同一個 URL 可能回 gzip、br 或未壓縮的版本，少了它，不支援 br 的舊 client 可能拿到一份解不開的 Brotli（21.7 節）。反過來，不該出現的是 `Vary: User-Agent`：User-Agent 字串有成千上萬種，等於把快取切成碎片。

回到故事。有人會問：既然問題是 cache key 沒區分使用者，那首頁加上 `Vary: Cookie` 不就好了？這樣在規格上確實不會再混用，但有兩個問題。第一，cookie 裡除了 session 還有語言偏好、A/B 測試、分析工具寫的各種值，每個使用者、甚至每次造訪的 cookie 字串都不同，CDN 等於替每個人各存一份，命中率回到接近零，還佔滿快取空間。第二，它把「隱私是否安全」押在每一層快取都正確實作 `Vary` 上；有些 CDN 對 `Vary` 的支援有限，可能直接不快取，也可能只認少數 header。個人化內容的正確答案是 `private`：從源頭宣告「這不是給共享快取的」，再讓 CDN 對帶登入 cookie 的請求直接 bypass，21.11 節的實驗五會驗證這兩步缺一不可。Flask 存取過 `session` 的回應會自動加上 `Vary: Cookie`，這是一道保險，但不能取代 `private`。

> [!warning] 常見誤解
> 「CDN 會自動把 cookie 當作 cache key。」多數 CDN 的預設 cache key 是 host、path 與 query string，不含 cookie 與大部分 header；有些 CDN 預設不快取帶 `Set-Cookie` 的回應，但請求帶 `Cookie` 通常不影響快取判斷。各家預設不同，要查你用的 CDN 文件，並用實驗確認。另外，若 origin 會依某個「不在 cache key 裡」的 header（例如 `X-Forwarded-Host`）改變回應內容，就可能被利用來污染快取（cache poisoning）；防禦方式是讓影響回應的 header 都進 key 或在 edge 剝除，細節在第 25 章。

## 21.6 內容協商：同一個 URL，不同的表示法

HTTP 把「資源」（resource，例如美咲老師的課程列表）和它的「表示法」（representation，例如日文 HTML、繁中 HTML、JSON、gzip 壓縮過的 JSON）分開。同一個資源可以有很多表示法，由 server 依請求挑一個，這叫**內容協商**（content negotiation）。最常見的是**主動協商**（proactive negotiation）：client 在請求中用 `Accept` 系列 header 說明偏好，server 據此選擇，並在回應用 `Vary` 說明選擇依據、用 `Content-Type`、`Content-Language`、`Content-Encoding` 標明選了什麼。

| 請求 header | 協商什麼 | 例子 | 回應對應的 header |
|---|---|---|---|
| `Accept` | 媒體類型 | `application/json, text/html;q=0.9` | `Content-Type` |
| `Accept-Language` | 語言 | `zh-TW, ja;q=0.7, en;q=0.3` | `Content-Language` |
| `Accept-Encoding` | 壓縮方式 | `gzip, deflate, br, zstd` | `Content-Encoding` |
| `Accept-Charset` | 字元集 | 現代瀏覽器已不送，一律用 UTF-8 | `Content-Type` 的 `charset` |

`q` 是**品質值**（quality value），0 到 1，代表偏好程度，沒寫就是 1。`zh-TW, ja;q=0.7, en;q=0.3` 讀作「最想要繁中，其次日文，再其次英文」；`q=0` 代表明確拒絕，例如 `gzip;q=0` 是「不要 gzip」。`*` 是萬用字元，`*;q=0.5` 表示其他沒列出的都可以接受但偏好較低。server 找不到任何可接受的表示法時，可以回 **406 Not Acceptable**，但實務上多半直接給預設版本，因為一個空白錯誤頁對使用者沒有幫助。與它對稱的是 **415 Unsupported Media Type**，用在 client 送上來的 body 格式 server 不接受（例如 API 只收 JSON，卻收到 XML）。

另一種是**被動協商**（reactive negotiation）：server 回 **300 Multiple Choices** 列出選項讓 client 自己挑，實務上幾乎沒人用。比較常見的折衷是「先主動協商猜一個，再讓使用者用 UI 切換」。聲聲 Live 的首頁第一次造訪時依 `Accept-Language` 猜語言，使用者在選單切換後，選擇寫進 URL（第 1 章的 `/?lang=ja`）或 cookie。

把語言放在 URL 而不是只靠 `Accept-Language`，對快取與搜尋引擎都更友善：URL 本身就是 cache key，`/courses?lang=ja` 和 `/courses?lang=zh-TW` 自然分成兩格，不需要 `Vary`；搜尋引擎也能分別索引每個語言版本。這是工程上常見的取捨：內容協商很優雅，但每多一個依 header 決定的維度，快取就多一個要正確處理的 `Vary`。API 的版本與格式也一樣，用 URL 路徑或明確的 `Accept` 媒體類型，都比依 User-Agent 猜測可靠（API 版本化的取捨見第 24 章）。

## 21.7 壓縮：gzip、br 與 Content-Encoding

文字類資源（HTML、CSS、JavaScript、JSON）壓縮後通常只剩原來的兩到三成，對行動網路上的學生差別很大。壓縮是內容協商的一種：瀏覽器在 `Accept-Encoding` 列出它會解的格式，server 挑一個，用 **`Content-Encoding`** 標明。常見的編碼有三種：**gzip**（DEFLATE 演算法加上 gzip 的 header 與 trailer，RFC 1952，幾乎所有 client 都支援）、**br**（Brotli，RFC 7932，壓縮率通常比 gzip 好，瀏覽器一般只在 HTTPS 上宣告支援）、**zstd**（Zstandard，RFC 8878，壓縮與解壓都快）。Python 標準函式庫有 `gzip` 與 `zlib`，沒有 Brotli。

gzip 格式本身有一個 10 bytes 的固定 header，在 Wireshark 或 `xxd` 看到 `1f 8b` 開頭，就知道這是 gzip：

```text
  byte:  0      1      2      3      4      5      6      7      8      9
       ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
       │ ID1  │ ID2  │  CM  │ FLG  │          MTIME（4 bytes，LE）  │ XFL  │  OS  │
       │ 1f   │ 8b   │ 08   │ 00   │ 00     00     00     00     │ 02   │ ff   │
       └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
         magic number  DEFLATE  旗標    原檔修改時間（0 = 未提供）  壓縮等級  作業系統
  之後：DEFLATE 壓縮資料 ……  最後 8 bytes：CRC-32（4）＋ 原始長度 mod 2³²（4）
```

這是 21.11 節實驗二實際產生的 header。前兩個 byte `1f 8b` 是 magic number；`08` 表示壓縮方法是 DEFLATE；`FLG` 是旗標位元組，各 bit 表示後面有沒有原檔名、註解、額外欄位等，`00` 代表都沒有；接著 4 bytes 的 `MTIME` 是 little-endian 的原檔修改時間，我們刻意設成 0，讓同樣的輸入每次產生同樣的 bytes（否則 ETag 會因時間不同而變）；`XFL` 的 `02` 表示用了最高壓縮等級；`OS` 的 `ff` 表示「未知」。最後的 CRC-32 讓解壓方檢查資料是否損壞。

**`Content-Encoding` 和 `Transfer-Encoding` 是兩回事**，這是讀 header 時最常混淆的一組。`Content-Encoding: gzip` 是表示法本身的屬性，從 origin 到瀏覽器一路保持，快取存的就是壓縮後的 bytes，ETag 與 Range 也都針對壓縮後的 bytes。`Transfer-Encoding: chunked`（第 20 章）是 HTTP/1.1 這一段連線的傳輸方式，屬於 hop-by-hop，每一跳都可能不同，HTTP/2 和 HTTP/3 根本沒有它。所以「nginx 對上游用 chunked、對瀏覽器用 HTTP/2」完全正常，但「CDN 把 gzip 解開再重新用 br 壓」就等於換了一個表示法，ETag 也該跟著變。

壓縮不是越多越好，有三個取捨。第一，JPEG、PNG、MP4、WOFF2 這些格式本身已經壓縮過，再 gzip 只會浪費 CPU，甚至變大，所以 nginx 的 `gzip_types` 只列文字類型。第二，太小的回應（例如幾百 bytes 的 JSON）壓縮省下的 bytes 抵不過 header 與 CPU 的成本。第三，壓縮會帶來資安上的**旁通道**（side channel）：當一個壓縮回應同時含有秘密（例如 CSRF token）與攻擊者能控制的反射內容時，壓縮後長度的變化可能洩漏秘密，這類問題以 BREACH 之名為人所知。防禦方式是不要在同一個壓縮回應裡混放秘密與使用者輸入的反射內容、對 token 做每次請求不同的遮罩，或對這類敏感回應關閉壓縮。

> [!note] 2026 現況
> 截至 2026 年 10 月，gzip 仍是相容性最好的選項，br 在主流瀏覽器與 CDN 普遍支援，zstd 已被 Chrome、Firefox 等瀏覽器加進 `Accept-Encoding`，CDN 支援度各家不同，部署前請查各家文件與 caniuse 的最新狀態。另有讓瀏覽器用「上一版檔案」當字典來壓縮新版的 Compression Dictionary Transport，適合頻繁小改版的 JavaScript，採用前請確認目前的標準化與瀏覽器支援狀態。

## 21.8 Range 請求：只要其中一段

課程錄影回放一部九十分鐘的影片可能有幾百 MB，學生拖曳進度條跳到第 45 分鐘，瀏覽器不需要、也不應該從頭下載。**Range 請求**讓 client 只要資源的某一段 bytes。server 用 `Accept-Ranges: bytes` 宣告支援；client 送 `Range: bytes=起-迄`，server 回 **206 Partial Content**，用 `Content-Range` 說明這是哪一段、總長多少。下載工具的斷點續傳、影片播放器的拖曳、PDF 閱讀器的分頁載入，背後都是它。

```text
 lesson-0815.bin（總長 10,240 bytes）
 byte  0          1023 1024        2047                          10000      10239
       ├──────────────┼──────────────┼──── … ──────────────────────┼───────────┤
       │ bytes=0-1023 │bytes=1024-   │                             │bytes=     │
       │ → 206        │2047 → 206    │                             │10000-→206 │
       │ Content-Range: bytes 0-1023/10240                         │ 240 bytes │
       └──────────────┴──────────────┴─────────────────────────────┴───────────┘
 bytes=-100      → 最後 100 bytes：Content-Range: bytes 10140-10239/10240
 bytes=20000-    → 超出範圍：416 Range Not Satisfiable，Content-Range: bytes */10240
 If-Range: "rec-0815-v0"（檔案已換新版）→ 不給片段，回 200 整份
```

圖上方是一條 byte 軸，範圍是**包含兩端**的：`bytes=0-1023` 是 1,024 bytes，不是 1,023。`bytes=10000-` 表示從 10000 到結尾，`bytes=-100` 表示最後 100 bytes。超出檔案長度的請求得到 **416 Range Not Satisfiable**，並用 `Content-Range: bytes */10240` 告訴 client 總長。最後一行是續傳的安全機制：如果下載到一半、伺服器上的檔案換成了新版，把新檔案的後半段接到舊檔案的前半段會得到損壞的檔案。所以續傳時要帶 **`If-Range`**，值是之前拿到的強 ETag（或 `Last-Modified`）：版本相同就回 206 片段，不同就回 200 整份。

一個請求也可以要多個區段（`bytes=0-99,500-599`），server 會回 `multipart/byteranges`；規格也允許 server 忽略 Range、直接回整份。待辦清單上「拖曳進度條就從頭下載」的根因後來查出來：錄影檔不是由 nginx 直接送出，而是經過一支 Flask view 讀檔後整份回傳，view 忽略了 `Range` 而且沒送 `Accept-Ranges`。改用 nginx 直接服務檔案（或 Flask 的 `send_file`，它支援條件請求與 Range）後就正常了。另外要注意，Range 作用在**選定的表示法**上：如果回應是 gzip 壓縮的，byte 位置指的是壓縮後的 bytes。影片本來就不該再壓縮，所以這在影音場景很少成為問題，但在對大型 JSON 做 Range 時會讓人困惑。

## 21.9 Cookie：語法、屬性與送出規則

HTTP 是**無狀態**（stateless）的：每個請求都獨立，server 不會自動記得「上一個請求是誰」。**cookie** 是讓瀏覽器替 server 記一小段資料、之後每次請求自動帶回來的機制，規格是 RFC 6265（將由 6265bis 取代）。server 在回應用 `Set-Cookie` 設定，瀏覽器存在自己的 **cookie jar**（cookie 儲存區）裡，之後符合條件的請求就在 `Cookie` header 帶上。聲聲 Live 的登入 session、語言偏好、教室的分頁狀態都靠它。

`Set-Cookie` 的語法是「一組 `name=value`，後面接零到多個以分號隔開的屬性」。每個 cookie 都要獨立一行 `Set-Cookie`，不能像其他 header 那樣用逗號合併，因為 `Expires` 的日期裡本身就有逗號。請求方向則只有一個 `Cookie` header，裡面只有 `name=value` 用 `; ` 串起來，**不會帶屬性**：server 收到 cookie 時，無從得知它的 Domain、Path 或過期時間。

```text
 Set-Cookie: __Host-sid=7f3a ; Path=/ ; Secure ; HttpOnly ; SameSite=Lax
             └─name─┘ └val┘   └─────────────── 屬性（只在設定時出現）───────────────┘

 Set-Cookie: lang=ja ; Domain=shengsheng.example ; Path=/ ; Max-Age=31536000

 之後的請求（屬性都不見了，只剩 name=value）：
 Cookie: tab=reviews; __Host-sid=7f3a; lang=ja
```

圖上把一個 `Set-Cookie` 拆成名稱、值、屬性三部分。下表是各屬性的意思，其中與攻擊防禦最相關的 `HttpOnly`、`SameSite` 只在這裡簡述，完整的威脅模型（XSS、CSRF）在第 23 章：

| 屬性 | 意思 | 沒寫的話 | 聲聲 Live 的設定 |
|---|---|---|---|
| `Expires=日期`／`Max-Age=秒` | 何時過期；兩者都有時 `Max-Age` 優先；`Max-Age=0` 代表刪除 | session cookie：瀏覽器工作階段結束就消失 | 語言偏好一年；登入 session 不設 |
| `Domain=網域` | 送給這個網域與其所有子網域 | host-only：只送回設定它的那個 host | 只有 `lang` 用 `shengsheng.example` |
| `Path=路徑` | 請求路徑符合這個前綴才送 | 預設路徑：請求路徑最後一個 `/` 之前 | 一律 `Path=/` |
| `Secure` | 只在 HTTPS 上送；非 HTTPS 的頁面也不能設定它 | HTTP 也會送 | 全部加 |
| `HttpOnly` | JavaScript 的 `document.cookie` 讀不到 | JavaScript 可讀 | session 一定加 |
| `SameSite=Strict／Lax／None` | 跨站請求時要不要送（第 23 章） | 依瀏覽器而定，Chrome 視為 `Lax` | session 用 `Lax` |
| `Partitioned` | 在第三方嵌入情境下依頂層網站分區儲存（CHIPS） | 不分區 | 目前未使用 |

`Domain` 的規則常被弄反：**寫了 `Domain` 範圍反而變大**。沒寫時是 host-only，`www.shengsheng.example` 設定的 cookie 只送回 `www`；寫了 `Domain=shengsheng.example`，就會送給 `api`、`rt`、`auth` 等所有子網域。所以 session cookie 不該寫 `Domain`，免得任何一個子網域（包括將來外包的行銷活動站）都收到它。瀏覽器也不允許把 `Domain` 設成 **public suffix**（公共後綴，例如 `com`、`com.tw` 這種任何人都能在底下註冊網域的層級），也不允許設成和目前 host 無關的網域，否則一個網站就能替別人設定 cookie。

**cookie 前綴**（cookie prefix）是讓 server 能從名字就確認屬性的機制，因為 server 收到 cookie 時看不到屬性。名字以 `__Secure-` 開頭的 cookie，瀏覽器只接受帶 `Secure` 且從 HTTPS 設定的；以 `__Host-` 開頭的，還必須沒有 `Domain`、`Path=/`，也就是「只屬於這一個 host、整個站都用」。聲聲 Live 把 session cookie 命名為 `__Host-sid`，就算某個子網域被入侵，也無法替 `www` 偷偷設一個同名的 session cookie（session fixation 的一種手法，第 26 章）。

瀏覽器決定一個請求要帶哪些 cookie，是依序過幾道篩子：

```text
 對每一個存著的 cookie：
   ① 過期了嗎？ ──── 是 ──► 丟掉（不送，並從 jar 刪除）
        │ 否
   ② host 符合嗎？  host-only：完全相同；有 Domain：等於或是其子網域 ── 否 ──► 不送
        │ 是
   ③ path 符合嗎？  cookie 的 Path 是請求路徑的前綴，且在 "/" 邊界上 ── 否 ──► 不送
        │ 是            （/teachers 符合 /teachers/misaki，不符合 /teachersroom）
   ④ Secure 但請求不是 HTTPS？ ─── 是 ──► 不送
        │ 否
   ⑤ SameSite 允許這次的跨站情境嗎？（第 23 章）─── 否 ──► 不送
        │ 是
   放進 Cookie header；多個 cookie 依 Path 長的在前、建立時間早的在前排序
```

這張流程圖就是 21.11 節實驗四 `cookie_header()` 的邏輯。第 ③ 步的「邊界」常被忽略：`Path=/teachers` 會送給 `/teachers/misaki`，但不送給 `/teachersroom`。`Path` 也不是安全邊界：同一個 origin 下的頁面能用 JavaScript 讀到其他路徑的非 HttpOnly cookie，要隔離就用不同子網域。最後的排序讓同名 cookie 有確定先後，但同名 cookie 出現兩次通常代表 Domain 或 Path 設錯了。

cookie 也和快取互相影響。請求帶 `Cookie` 不會讓快取自動區分使用者（21.5 節），而回應帶 `Set-Cookie` 如果被 shared cache 存下來，後面的人會拿到同一個 session，這比故事裡的事故更嚴重。規格本身並沒有禁止快取存帶 `Set-Cookie` 的回應，雖然很多 CDN 的預設是不存，但不能依賴預設：會設定 cookie 的回應，一律標 `private` 或 `no-store`。cookie 的大小也有限：規格要求瀏覽器至少支援每個 cookie 4,096 bytes、每個網域 50 個，而每個 cookie 都會在每個符合的請求中重送一次，塞滿 cookie 會讓每個請求的 header 多出好幾 KB，甚至超過 server 的 header 大小上限而得到 400 或 431。

> [!note] 2026 現況
> 依 2026 年 10 月查證：6265bis 已在 RFC Editor queue，尚未取得 RFC 編號，`SameSite` 與 `__Host-`／`__Secure-` 前綴都包含在其中。`Partitioned`（CHIPS）在 Chrome／Edge 114+、Firefox 141+ 支援，Safari 18.4 支援、18.5 到 26.1 標示不支援、26.2 起再度支援。Chrome 預設仍允許第三方 cookie，Safari 與 Firefox 則以封鎖或分區的方式限制。Flask 3.1.0 起有 `SESSION_COOKIE_PARTITIONED` 設定。

## 21.10 Redirect：五種 3xx 的差別

**redirect**（重新導向）是 server 用 3xx status code 加上 `Location` header 告訴 client「去另一個 URL 拿」。聲聲 Live 到處都用得到：HTTP 導向 HTTPS、舊網址搬家、登入後回到原頁、表單送出後導向結果頁。五種常用的 redirect 差別只在兩件事：是永久還是暫時，以及 client 重送時能不能把 method 改成 GET。

| 狀態碼 | 名稱 | 永久？ | 重送時的 method | 預設可快取 | 典型用途 |
|---|---|---|---|---|---|
| 301 | Moved Permanently | 是 | 歷史上瀏覽器會把 POST 改成 GET | 是（啟發式） | 舊網址永久搬家（GET 頁面） |
| 302 | Found | 否 | 歷史上瀏覽器會把 POST 改成 GET | 否 | 暫時導向、登入後回原頁 |
| 303 | See Other | 否 | 一律改用 GET | 否 | 表單 POST 後導向結果頁（PRG 模式） |
| 307 | Temporary Redirect | 否 | 保持原 method 與 body | 否 | 暫時把 API 的 POST 導到別處 |
| 308 | Permanent Redirect | 是 | 保持原 method 與 body | 是（啟發式） | API 永久搬家、HTTP 導向 HTTPS |

表的第四欄是實務上最重要的差別。301 與 302 的原始定義沒說要改 method，但早期瀏覽器把 POST 改成 GET，這個行為成了事實標準，規格只好承認它；為了消除模糊，後來才加了 303（明確改 GET）與 307、308（明確不改）。所以 API 搬家要用 307 或 308，否則 client 的 POST 會在導向後變成沒有 body 的 GET。表單送出後回 303，是 **PRG 模式**（Post/Redirect/Get）：使用者在結果頁按重新整理，只會重送 GET，不會再付一次款。

第五欄是一個坑：301 和 308 預設可被快取，測試時誤設一個 301 把 `/pricing` 導錯，修好 server 也沒用，造訪過的使用者會繼續被瀏覽器本地導走。所以新的導向規則先用 302 或 307 觀察，確定無誤再改成永久，或在 301 上明確加 `Cache-Control: max-age=` 限制時間。也要注意 **redirect loop**（導向迴圈）：最常見的是 CDN 用 HTTP 連 origin、origin 又把「HTTP 請求」導向 HTTPS，瀏覽器最後顯示「重新導向次數過多」；修法是讓 origin 依 `X-Forwarded-Proto` 判斷原始 scheme（第 25、43 章）。HTTP 導向 HTTPS 的第一次請求仍是明文，HSTS 可以讓瀏覽器之後直接用 HTTPS（第 19 章）。

## 21.11 動手做：條件請求、shared cache、cookie jar 與事故重現

這一節用五段程式把前面的規則變成可以觀察的行為。每段都只用標準函式庫，server 跑在 127.0.0.1、port 0，結束時關閉。以下輸出是在 macOS 上用 Python 3.14 實際執行的結果，Linux 上相同。

### 實驗一：支援 ETag、Last-Modified 與 If-Match 的 server

這段程式用 `http.server` 寫一個老師介紹 API：GET 支援 `If-None-Match` 與 `If-Modified-Since`，PUT 要求 `If-Match`。重點在 `etag_matches()`：`If-None-Match` 用弱比較，`If-Match` 用強比較，而且兩種條件都送時 `If-None-Match` 優先。

```python
import hashlib
import http.client
import json
import threading
from email.utils import formatdate, parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 老師的自我介紹：一份可以被讀、也可以被編輯的資源
STATE = {"body": json.dumps({"teacher": "misaki", "intro": "日文會話，N3 衝刺"}).encode(),
         "mtime": 1790000000}  # Unix 秒數，固定值讓輸出可重現


def etag_of(body: bytes) -> str:
    return '"' + hashlib.sha256(body).hexdigest()[:12] + '"'  # 強 ETag：內容一變就變


def etag_matches(header: str, current: str, weak: bool) -> bool:
    if header.strip() == "*":
        return True
    for tag in (t.strip() for t in header.split(",")):
        if weak:   # If-None-Match 用弱比較：去掉 W/ 再比
            if tag.removeprefix("W/") == current.removeprefix("W/"):
                return True
        elif tag == current and not tag.startswith("W/"):  # If-Match 用強比較
            return True
    return False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 不要把存取 log 混進輸出
        pass

    def validators(self):
        self.send_header("ETag", etag_of(STATE["body"]))
        self.send_header("Last-Modified", formatdate(STATE["mtime"], usegmt=True))
        self.send_header("Cache-Control", "no-cache")  # 可以存，但每次用之前都要回來問

    def do_GET(self):
        inm, ims = self.headers.get("If-None-Match"), self.headers.get("If-Modified-Since")
        if inm is not None:                         # 有 If-None-Match 就忽略 If-Modified-Since
            not_modified = etag_matches(inm, etag_of(STATE["body"]), weak=True)
        elif ims is not None:
            not_modified = STATE["mtime"] <= parsedate_to_datetime(ims).timestamp()
        else:
            not_modified = False
        if not_modified:
            self.send_response(304)                 # 沒有 body，但要帶回 validators
            self.validators()
            self.end_headers()
            return
        self.send_response(200)
        self.validators()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(STATE["body"])))
        self.end_headers()
        self.wfile.write(STATE["body"])

    def do_PUT(self):
        new_body = self.rfile.read(int(self.headers["Content-Length"]))
        if_match = self.headers.get("If-Match")
        if if_match is None:
            status = 428                            # Precondition Required：強制使用條件更新
        elif not etag_matches(if_match, etag_of(STATE["body"]), weak=False):
            status = 412                            # Precondition Failed：有人先改了
        else:
            STATE["body"], STATE["mtime"] = new_body, STATE["mtime"] + 60
            status = 200
        self.send_response(status)
        self.validators()
        self.send_header("Content-Length", "0")
        self.end_headers()


def call(port, method, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request(method, "/api/teachers/misaki/intro", body=body, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, resp.getheader("ETag"), len(data)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

status, tag, size = call(port, "GET")
print(f"1. 第一次 GET                 → {status}  ETag={tag}  body={size} bytes")
lm = formatdate(STATE["mtime"], usegmt=True)
print(f"   Last-Modified = {lm}")
r2 = call(port, "GET", {"If-None-Match": tag})
print(f"2. If-None-Match: {tag} → {r2[0]}  body={r2[2]} bytes")
r3 = call(port, "GET", {"If-Modified-Since": lm})
print(f"3. If-Modified-Since          → {r3[0]}  body={r3[2]} bytes")
r4 = call(port, "GET", {"If-None-Match": '"stale"', "If-Modified-Since": lm})
print(f"4. 兩個都送，ETag 不符        → {r4[0]}  （If-None-Match 優先）")

edit = json.dumps({"teacher": "misaki", "intro": "日文會話，N2 衝刺"}).encode()
r5 = call(port, "PUT", {"If-Match": tag}, edit)
print(f"5. 小晴 PUT If-Match 舊 ETag  → {r5[0]}  新 ETag={r5[1]}")
r6 = call(port, "PUT", {"If-Match": tag}, b'{"intro": "overwrite"}')
print(f"6. 阿德也拿舊 ETag PUT        → {r6[0]}  （避免 lost update）")
r7 = call(port, "PUT", {}, b'{"intro": "blind write"}')
print(f"7. 不帶 If-Match 的 PUT       → {r7[0]}")
r8 = call(port, "GET", {"If-None-Match": tag})
print(f"8. 用舊 ETag 再 GET           → {r8[0]}  body={r8[2]} bytes")

assert (status, r2[0], r3[0], r4[0]) == (200, 304, 304, 200)
assert (r5[0], r6[0], r7[0], r8[0]) == (200, 412, 428, 200) and r2[2] == 0
server.shutdown()
server.server_close()
```

```text
1. 第一次 GET                 → 200  ETag="b3294d1ad6ba"  body=79 bytes
   Last-Modified = Mon, 21 Sep 2026 14:13:20 GMT
2. If-None-Match: "b3294d1ad6ba" → 304  body=0 bytes
3. If-Modified-Since          → 304  body=0 bytes
4. 兩個都送，ETag 不符        → 200  （If-None-Match 優先）
5. 小晴 PUT If-Match 舊 ETag  → 200  新 ETag="960b2f0e9b64"
6. 阿德也拿舊 ETag PUT        → 412  （避免 lost update）
7. 不帶 If-Match 的 PUT       → 428
8. 用舊 ETag 再 GET           → 200  body=79 bytes
```

逐行對照 21.4 節的時序圖。第 1 行拿到 200、強 ETag 與 `Last-Modified`；第 2、3 行分別用兩種 validator 驗證，都得到 304 且 body 是 0 bytes，這就是 `no-cache` 搭配 validator 省下來的頻寬。第 4 行同時送兩種條件，`If-Modified-Since` 本來會成立，但 `If-None-Match` 帶的 ETag 不相符，server 依規則以 `If-None-Match` 為準，回 200。

第 5 到 7 行是樂觀並行控制。小晴拿著讀到的 ETag 更新成功，ETag 隨內容改變；阿德的分頁拿的是同一個舊 ETag，被 412 擋下，這正是待辦清單上「後存的蓋掉先存的」的修法；完全不帶條件的寫入被 428 拒絕，強迫所有 client 都走條件更新。第 8 行用舊 ETag 驗證，因為內容已改，得到 200 與新內容。注意 PUT 之後 `Last-Modified` 只前進 60 秒；真實系統若一秒內改兩次，`Last-Modified` 會分辨不出來，這是 ETag 比較可靠的原因。

### 實驗二：gzip 協商、Vary 與 Range

第二段 server 有兩個資源：靜態 JavaScript 依 `Accept-Encoding` 決定是否 gzip，並帶 `Vary: Accept-Encoding`；課程錄影檔支援單一區段的 Range 與 `If-Range`。

```python
import gzip
import http.client
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_JS = b"function joinClassroom(id){return fetch('/api/rooms/'+id);}\n" * 120
RECORDING = bytes(range(256)) * 40          # 假的課程錄影檔：10,240 bytes
REC_ETAG = '"rec-0815-v1"'


def accepts_gzip(header: str) -> bool:
    """解析 Accept-Encoding 的 q 值：gzip;q=0 代表明確拒絕。"""
    prefs = {}
    for item in header.split(","):
        name, _, params = item.strip().partition(";")
        m = re.search(r"q=([0-9.]+)", params)
        prefs[name.strip().lower()] = float(m.group(1)) if m else 1.0
    return prefs.get("gzip", prefs.get("*", 0.0)) > 0


def parse_range(header: str, size: int):
    """只支援單一區段：bytes=a-b、bytes=a-、bytes=-n。回傳 (start, end) 或 None。"""
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not m or m.groups() == ("", ""):
        return None
    first, last = m.groups()
    if first == "":                                   # 最後 n bytes
        start, end = max(size - int(last), 0), size - 1
    else:
        start, end = int(first), min(int(last), size - 1) if last else size - 1
    return (start, end) if start <= end and start < size else None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, headers):
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/static/app.js":
            headers = {"Content-Type": "text/javascript", "Vary": "Accept-Encoding",
                       "Cache-Control": "public, max-age=31536000, immutable"}
            body = APP_JS
            if accepts_gzip(self.headers.get("Accept-Encoding", "")):
                body = gzip.compress(APP_JS, mtime=0)  # mtime=0 讓同樣輸入得到同樣 bytes
                headers |= {"Content-Encoding": "gzip", "ETag": '"app-v7-gz"'}
            else:
                headers["ETag"] = '"app-v7"'          # 不同編碼是不同的表示法，ETag 也要不同
            return self.reply(200, body, headers)
        if self.path == "/recordings/lesson-0815.bin":
            size, base = len(RECORDING), {"Accept-Ranges": "bytes", "ETag": REC_ETAG}
            rng, if_range = self.headers.get("Range"), self.headers.get("If-Range")
            if rng is None or (if_range is not None and if_range != REC_ETAG):
                return self.reply(200, RECORDING, base)  # If-Range 不符：整份重給
            span = parse_range(rng, size)
            if span is None:
                return self.reply(416, b"", base | {"Content-Range": f"bytes */{size}"})
            start, end = span
            return self.reply(206, RECORDING[start:end + 1],
                              base | {"Content-Range": f"bytes {start}-{end}/{size}"})
        self.reply(404, b"", {})


def get(port, path, headers):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("GET", path, headers=headers)
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp, body


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

for ae in ["gzip, deflate, br, zstd", "identity", "gzip;q=0, *;q=0.5"]:
    resp, body = get(port, "/static/app.js", {"Accept-Encoding": ae})
    enc = resp.getheader("Content-Encoding", "(無)")
    print(f"AE={ae!r:28} → {len(body):5} bytes  Content-Encoding={enc:5} ETag={resp.getheader('ETag')}")
    if enc == "gzip":
        assert gzip.decompress(body) == APP_JS and body[:3] == b"\x1f\x8b\x08"
        print(f"   gzip header 前 10 bytes：{body[:10].hex(' ')}")
print(f"   原始大小 {len(APP_JS)} bytes，Vary={resp.getheader('Vary')}")

cases = [("bytes=0-1023", None), ("bytes=10000-", None), ("bytes=-100", None),
         ("bytes=20000-20100", None), ("bytes=1024-2047", '"rec-0815-v1"'),
         ("bytes=1024-2047", '"rec-0815-v0"')]
for rng, if_range in cases:
    headers = {"Range": rng} | ({"If-Range": if_range} if if_range else {})
    resp, body = get(port, "/recordings/lesson-0815.bin", headers)
    note = f" If-Range={if_range}" if if_range else ""
    print(f"Range: {rng:18}{note:26} → {resp.status}  {len(body):5} bytes  "
          f"Content-Range={resp.getheader('Content-Range')}")
    if resp.status == 206:
        start = int(resp.getheader("Content-Range").split()[1].split("-")[0])
        assert body == RECORDING[start:start + len(body)]
server.shutdown()
server.server_close()
```

```text
AE='gzip, deflate, br, zstd'    →   116 bytes  Content-Encoding=gzip  ETag="app-v7-gz"
   gzip header 前 10 bytes：1f 8b 08 00 00 00 00 00 02 ff
AE='identity'                   →  7200 bytes  Content-Encoding=(無)   ETag="app-v7"
AE='gzip;q=0, *;q=0.5'          →  7200 bytes  Content-Encoding=(無)   ETag="app-v7"
   原始大小 7200 bytes，Vary=Accept-Encoding
Range: bytes=0-1023                                 → 206   1024 bytes  Content-Range=bytes 0-1023/10240
Range: bytes=10000-                                 → 206    240 bytes  Content-Range=bytes 10000-10239/10240
Range: bytes=-100                                   → 206    100 bytes  Content-Range=bytes 10140-10239/10240
Range: bytes=20000-20100                            → 416      0 bytes  Content-Range=bytes */10240
Range: bytes=1024-2047    If-Range="rec-0815-v1"    → 206   1024 bytes  Content-Range=bytes 1024-2047/10240
Range: bytes=1024-2047    If-Range="rec-0815-v0"    → 200  10240 bytes  Content-Range=None
```

前三行是壓縮協商。瀏覽器常見的 `gzip, deflate, br, zstd` 拿到 gzip 版本；`identity`（不編碼）與 `gzip;q=0, *;q=0.5`（明確拒絕 gzip）都拿到原始版本。這份測試檔是同一行程式重複 120 次，所以 7,200 bytes 壓到 116 bytes，真實的 JavaScript 通常只能壓到兩三成，不要拿這個比例去估容量。兩個版本的 ETag 不同，因為它們是不同的表示法，bytes 不同；`Vary: Accept-Encoding` 則確保快取不會把 gzip 版本給一個不接受 gzip 的 client。印出來的 gzip header `1f 8b 08 00 00 00 00 00 02 ff` 就是 21.7 節那張位元布局圖。

後六行是 Range。前三個 206 分別示範「起到迄」「從某處到結尾」「最後 n bytes」，`Content-Range` 中的區間都是包含兩端的；第四個超出檔案長度，得到 416 與 `bytes */10240`。最後兩行是 `If-Range`：ETag 相同時給片段，ETag 是舊版時 server 改回 200 整份，client 不會把兩個版本的 bytes 拼在一起。

### 實驗三：一個簡化的 shared cache

第三段用一個類別模擬 CDN：依 `Cache-Control` 決定能不能存（`private`、`no-store`、帶 `Authorization` 的請求）、用 `s-maxage` 優先於 `max-age` 計算新鮮期、依 `Vary` 組 cache key、過期後用 `If-None-Match` 驗證，並實作 `stale-while-revalidate` 的「先給舊的、背景驗證」。為了讓輸出可重現，時間用模擬時鐘，origin 是一個函式。

```python
import re

CACHEABLE = {200, 203, 204, 206, 300, 301, 308, 404, 405, 410, 414, 501}


def directives(value: str) -> dict:
    """把 'public, max-age=60' 解析成 {'public': True, 'max-age': 60}。"""
    out = {}
    for part in filter(None, (p.strip().lower() for p in value.split(","))):
        name, _, arg = part.partition("=")
        out[name] = int(arg) if arg.isdigit() else True
    return out


class SharedCache:
    """簡化版 CDN：只處理 GET，依 Cache-Control 與 Vary 決定存不存、用多久、key 是什麼。"""

    def __init__(self, origin, clock):
        self.origin, self.clock, self.store, self.pending = origin, clock, {}, []

    def variant_key(self, path, req, vary):
        # cache key = URL ＋ Vary 列出的那些「請求」header 的值
        return (path,) + tuple((h, req.get(h, "")) for h in vary)

    def lifetime(self, cc):
        return cc.get("s-maxage", cc.get("max-age", 0))  # 共享快取優先看 s-maxage

    def storable(self, req, status, cc):
        if status not in CACHEABLE or "no-store" in cc or "private" in cc:
            return False
        if "Authorization" in req:   # 帶憑證的請求，回應要明確允許共享才可存
            return any(d in cc for d in ("public", "s-maxage", "must-revalidate"))
        return True

    def fetch(self, path, req, entry=None):
        headers = dict(req)
        if entry and "etag" in entry["headers"]:
            headers["If-None-Match"] = entry["headers"]["etag"]   # 條件請求
        status, resp_headers, body = self.origin(path, headers)
        if status == 304 and entry:
            entry["stored_at"] = self.clock()      # 304：沿用舊 body，更新新鮮度
            entry["headers"].update(resp_headers)
            return entry, "304"
        return {"status": status, "headers": resp_headers, "body": body,
                "stored_at": self.clock()}, str(status)

    def save(self, path, req, entry):
        cc = directives(entry["headers"].get("cache-control", ""))
        if not self.storable(req, entry["status"], cc):
            return False
        vary = [h.strip().title() for h in entry["headers"].get("vary", "").split(",") if h.strip()]
        if "*" in vary:
            return False
        self.store.setdefault(path, {})["vary"] = vary
        self.store[path][self.variant_key(path, req, vary)] = entry
        return True

    def get(self, path, req):
        slot = self.store.get(path)
        key = self.variant_key(path, req, slot["vary"]) if slot else None
        entry = slot.get(key) if slot else None
        if entry is None:
            fresh, _ = self.fetch(path, req)
            return fresh["body"], "MISS" if self.save(path, req, fresh) else "BYPASS"
        cc = directives(entry["headers"].get("cache-control", ""))
        age = self.clock() - entry["stored_at"]
        life = self.lifetime(cc)
        if age < life and "no-cache" not in cc:
            return entry["body"], f"HIT (age={age})"
        if age < life + cc.get("stale-while-revalidate", 0) and "no-cache" not in cc:
            self.pending.append((path, dict(req), entry))   # 先給舊的，背景再去問 origin
            return entry["body"], f"STALE (age={age}，背景重新驗證)"
        new, how = self.fetch(path, req, entry)
        self.save(path, req, new)
        return new["body"], "REVALIDATED (304)" if how == "304" else f"REFETCH ({how})"

    def run_background(self):
        for path, req, entry in self.pending:
            self.fetch(path, req, entry)
        self.pending.clear()


now = [0]
calls = []
VERSION = {"/": "v1"}


def origin(path, req):
    calls.append(path)
    if path == "/static/app.3f9c.js":
        return 200, {"cache-control": "public, max-age=31536000, immutable"}, b"js"
    if path == "/":
        etag = f'"home-{VERSION["/"]}"'
        if req.get("If-None-Match") == etag:
            return 304, {"etag": etag}, b""
        return 200, {"cache-control": "public, max-age=0, s-maxage=60, stale-while-revalidate=30",
                     "etag": etag}, b"<h1>Home</h1>"
    if path == "/courses":
        lang = req.get("Accept-Language", "en")[:2]
        return 200, {"cache-control": "public, max-age=300", "vary": "Accept-Language"}, lang.encode()
    if path == "/me":
        return 200, {"cache-control": "private, max-age=60"}, b"Hi, Xiaoqing"
    if path == "/api/schedule":   # no-cache：可以存，但每次都要先問 origin
        if req.get("If-None-Match") == '"sch-3"':
            return 304, {"etag": '"sch-3"'}, b""
        return 200, {"cache-control": "public, no-cache", "etag": '"sch-3"'}, b"3 classes"
    if path == "/api/plan":
        return 200, {"cache-control": "max-age=60"}, b"plan"
    return 404, {}, b""


cdn = SharedCache(origin, lambda: now[0])
script = [(0, "/static/app.3f9c.js", {}), (5, "/static/app.3f9c.js", {}),
          (10, "/", {}), (40, "/", {}), (80, "/", {}), (85, "/", {}), (210, "/", {}),
          (220, "/courses", {"Accept-Language": "ja"}), (221, "/courses", {"Accept-Language": "zh-TW"}),
          (222, "/courses", {"Accept-Language": "ja"}),
          (225, "/api/schedule", {}), (226, "/api/schedule", {}),
          (230, "/me", {"Cookie": "sid=A"}), (231, "/me", {"Cookie": "sid=B"}),
          (240, "/api/plan", {"Authorization": "Bearer t1"}), (241, "/api/plan", {"Authorization": "Bearer t2"})]
for t, path, req in script:
    now[0] = t
    before = len(calls)
    body, result = cdn.get(path, req)
    cdn.run_background()
    shown = "; ".join(f"{k}: {v}" for k, v in req.items()) or "-"
    print(f"t={t:3}s {path:20} {shown:24} → origin+{len(calls) - before}  {result}")

assert calls.count("/static/app.3f9c.js") == 1 and calls.count("/courses") == 2
assert calls.count("/") == 3 and calls.count("/me") == 2
assert calls.count("/api/schedule") == 2 and calls.count("/api/plan") == 2
```

```text
t=  0s /static/app.3f9c.js  -                        → origin+1  MISS
t=  5s /static/app.3f9c.js  -                        → origin+0  HIT (age=5)
t= 10s /                    -                        → origin+1  MISS
t= 40s /                    -                        → origin+0  HIT (age=30)
t= 80s /                    -                        → origin+1  STALE (age=70，背景重新驗證)
t= 85s /                    -                        → origin+0  HIT (age=5)
t=210s /                    -                        → origin+1  REVALIDATED (304)
t=220s /courses             Accept-Language: ja      → origin+1  MISS
t=221s /courses             Accept-Language: zh-TW   → origin+1  MISS
t=222s /courses             Accept-Language: ja      → origin+0  HIT (age=2)
t=225s /api/schedule        -                        → origin+1  MISS
t=226s /api/schedule        -                        → origin+1  REVALIDATED (304)
t=230s /me                  Cookie: sid=A            → origin+1  BYPASS
t=231s /me                  Cookie: sid=B            → origin+1  BYPASS
t=240s /api/plan            Authorization: Bearer t1 → origin+1  BYPASS
t=241s /api/plan            Authorization: Bearer t2 → origin+1  BYPASS
```

每一行最右邊是快取的判斷，`origin+N` 是這次請求讓 origin 多做幾次工。帶 hash 的 JavaScript 只讓 origin 被打一次。首頁那幾行對照 21.3 節的時間軸：t=10 存入；t=40 年齡 30 秒仍在 `s-maxage=60` 內，HIT；t=80 年齡 70 秒，已過期但在 `stale-while-revalidate=30` 的容忍期內，使用者立刻拿到舊版，背景發了一次條件請求（`origin+1`），origin 回 304 讓年齡歸零，所以 t=85 又是年齡 5 秒的 HIT；t=210 已經超出容忍期，只能同步驗證，origin 回 304，使用者這次要等一趟。

`/courses` 三行驗證 `Vary`：`ja` 與 `zh-TW` 各自 MISS 一次，存成兩個 variant，第二次 `ja` 才 HIT。`/api/schedule` 標的是 `no-cache`，第二次請求雖然有存貨，仍然先去問 origin，換來一個 304。最後四行都是 BYPASS：`/me` 標了 `private`，shared cache 不存，兩個不同的 session 都直接到 origin；`/api/plan` 雖然有 `max-age=60`，但請求帶 `Authorization`，回應又沒有 `public` 或 `s-maxage`，shared cache 也不能存。這個規則保護了「同一個 URL、不同 token 拿到不同資料」的 API，但也代表：如果你真的希望 CDN 快取需要驗證的內容，必須明確標 `public`，並自己確保內容與使用者無關。

### 實驗四：cookie 的解析與送出規則

第四段實作一個簡化的 cookie jar：解析 `Set-Cookie`、套用 Domain、Path、Secure、過期與前綴規則，再依 21.9 節的流程圖決定每個請求帶哪些 cookie。public suffix 只放了幾個示範值，真實瀏覽器使用完整的 Public Suffix List。Python 的 `http.cookies` 可以解析 cookie 字串，`http.cookiejar` 可以替 client 管理 cookie；這裡自己寫，是為了看清楚每一條規則。

```python
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

PUBLIC_SUFFIXES = {"example", "test", "com", "com.tw"}   # 真實瀏覽器用 Public Suffix List
NOW = 1790000000                                          # 模擬時鐘（Unix 秒）


def default_path(path):
    # 沒有 Path 屬性時：取請求路徑「最後一個 / 之前」的部分
    if not path.startswith("/") or path.count("/") == 1:
        return "/"
    return path[:path.rindex("/")]


def domain_match(host, domain):
    return host == domain or host.endswith("." + domain)


def path_match(req_path, cookie_path):
    if req_path == cookie_path:
        return True
    return req_path.startswith(cookie_path) and (
        cookie_path.endswith("/") or req_path[len(cookie_path)] == "/")


def set_cookie(jar, url, header, now=NOW):
    u = urlsplit(url)
    pair, *attrs = [p.strip() for p in header.split(";")]
    name, eq, value = pair.partition("=")
    if not eq or not name:
        return "拒絕：沒有 name=value"
    c = {"name": name, "value": value, "domain": u.hostname, "host_only": True,
         "path": default_path(u.path or "/"), "secure": False, "httponly": False,
         "samesite": "（未指定）", "expires": None}
    max_age = None
    for attr in attrs:
        key, _, val = attr.partition("=")
        key = key.lower()
        if key == "expires" and max_age is None:
            c["expires"] = parsedate_to_datetime(val).timestamp()
        elif key == "max-age":
            max_age = int(val)
            c["expires"] = now + max_age               # Max-Age 優先於 Expires
        elif key == "domain":
            d = val.lstrip(".").lower()
            if d in PUBLIC_SUFFIXES:
                return f"拒絕：Domain={d} 是 public suffix"
            if not domain_match(u.hostname, d):
                return f"拒絕：{u.hostname} 不屬於 Domain={d}"
            c["domain"], c["host_only"] = d, False
        elif key == "path" and val.startswith("/"):
            c["path"] = val
        elif key in ("secure", "httponly"):
            c[key] = True
        elif key == "samesite":
            c["samesite"] = val
    if c["secure"] and u.scheme != "https":
        return "拒絕：非 https 不能設定 Secure cookie"
    if name.startswith(("__Secure-", "__Host-")) and not c["secure"]:
        return "拒絕：__Secure-／__Host- 前綴必須有 Secure"
    if name.startswith("__Host-") and (not c["host_only"] or c["path"] != "/"):
        return "拒絕：__Host- 不能有 Domain，且 Path 必須是 /"
    key = (c["name"], c["domain"], c["path"])          # 同名＋同 domain＋同 path 才會覆寫
    if c["expires"] is not None and c["expires"] <= now:
        jar.pop(key, None)
        return "刪除（已過期）"
    jar[key] = c
    scope = c["domain"] + ("（host-only）" if c["host_only"] else "（含子網域）")
    return f"存入 {name}：{scope} Path={c['path']}"


def cookie_header(jar, url, now=NOW):
    u = urlsplit(url)
    picked = [c for c in jar.values()
              if (u.hostname == c["domain"] if c["host_only"] else domain_match(u.hostname, c["domain"]))
              and path_match(u.path or "/", c["path"])
              and (u.scheme == "https" or not c["secure"])
              and (c["expires"] is None or c["expires"] > now)]
    picked.sort(key=lambda c: -len(c["path"]))         # Path 較長的排前面
    return "; ".join(f"{c['name']}={c['value']}" for c in picked) or "（不送 Cookie）"


jar = {}
W = "https://www.shengsheng.example"
responses = [
    (W + "/login", "__Host-sid=7f3a; Path=/; Secure; HttpOnly; SameSite=Lax"),
    (W + "/", "lang=ja; Domain=shengsheng.example; Path=/; Max-Age=31536000"),
    (W + "/teachers/misaki", "tab=reviews"),
    (W + "/", "promo=fall; Expires=Thu, 01 Jan 2026 00:00:00 GMT"),
    ("http://www.shengsheng.example/", "__Secure-theme=dark; Secure"),
    (W + "/", "track=1; Domain=example"),
    (W + "/", "ad=1; Domain=other.example"),
    (W + "/", "__Host-csrf=9b; Secure; Domain=shengsheng.example; Path=/"),
]
for url, header in responses:
    print(f"Set-Cookie: {header}\n   ← {url}\n   ⇒ {set_cookie(jar, url, header)}")

print()
for url in [W + "/teachers/misaki", W + "/teachersroom", "https://api.shengsheng.example/v1/me",
            "http://www.shengsheng.example/"]:
    print(f"GET {url:40} Cookie: {cookie_header(jar, url)}")
two_years = NOW + 2 * 365 * 86400
print(f"兩年後 GET {W}/  Cookie: {cookie_header(jar, W + '/', two_years)}")

assert cookie_header(jar, W + "/teachers/misaki") == "tab=reviews; __Host-sid=7f3a; lang=ja"
assert cookie_header(jar, "https://api.shengsheng.example/v1/me") == "lang=ja"
assert cookie_header(jar, W + "/", two_years) == "__Host-sid=7f3a"
```

```text
Set-Cookie: __Host-sid=7f3a; Path=/; Secure; HttpOnly; SameSite=Lax
   ← https://www.shengsheng.example/login
   ⇒ 存入 __Host-sid：www.shengsheng.example（host-only） Path=/
Set-Cookie: lang=ja; Domain=shengsheng.example; Path=/; Max-Age=31536000
   ← https://www.shengsheng.example/
   ⇒ 存入 lang：shengsheng.example（含子網域） Path=/
Set-Cookie: tab=reviews
   ← https://www.shengsheng.example/teachers/misaki
   ⇒ 存入 tab：www.shengsheng.example（host-only） Path=/teachers
Set-Cookie: promo=fall; Expires=Thu, 01 Jan 2026 00:00:00 GMT
   ← https://www.shengsheng.example/
   ⇒ 刪除（已過期）
Set-Cookie: __Secure-theme=dark; Secure
   ← http://www.shengsheng.example/
   ⇒ 拒絕：非 https 不能設定 Secure cookie
Set-Cookie: track=1; Domain=example
   ← https://www.shengsheng.example/
   ⇒ 拒絕：Domain=example 是 public suffix
Set-Cookie: ad=1; Domain=other.example
   ← https://www.shengsheng.example/
   ⇒ 拒絕：www.shengsheng.example 不屬於 Domain=other.example
Set-Cookie: __Host-csrf=9b; Secure; Domain=shengsheng.example; Path=/
   ← https://www.shengsheng.example/
   ⇒ 拒絕：__Host- 不能有 Domain，且 Path 必須是 /

GET https://www.shengsheng.example/teachers/misaki Cookie: tab=reviews; __Host-sid=7f3a; lang=ja
GET https://www.shengsheng.example/teachersroom Cookie: __Host-sid=7f3a; lang=ja
GET https://api.shengsheng.example/v1/me     Cookie: lang=ja
GET http://www.shengsheng.example/           Cookie: lang=ja
兩年後 GET https://www.shengsheng.example/  Cookie: __Host-sid=7f3a
```

上半段是存入。`__Host-sid` 符合前綴的三個條件，存成 host-only；`lang` 帶了 `Domain`，範圍擴大到所有子網域；`tab=reviews` 沒寫 Path，從 `/teachers/misaki` 推出預設路徑 `/teachers`。接下來五個 cookie 都沒有存進去：過期日期在過去的 `promo` 等於刪除指令；從 HTTP 頁面設定 `Secure` cookie 被拒；`Domain=example` 是 public suffix；`Domain=other.example` 與目前的 host 無關；`__Host-csrf` 帶了 `Domain`，違反前綴規則。

下半段是送出。`/teachers/misaki` 拿到三個 cookie，`tab` 的 Path 最長所以排最前面；`/teachersroom` 不是 `/teachers` 底下的路徑，所以沒有 `tab`；`api.shengsheng.example` 只拿到 `lang`，因為 `__Host-sid` 是 host-only，這正是 session cookie 不寫 `Domain` 的效果；HTTP 請求拿不到 `Secure` 的 `__Host-sid`。最後一行把時鐘撥到兩年後，`lang` 的一年期限已過，只剩沒有過期時間的 session cookie；在真實瀏覽器裡，它會在工作階段結束時消失（但瀏覽器的「恢復分頁」功能可能讓工作階段延續，所以 server 端仍要有自己的 session 期限，第 26 章）。

### 實驗五：重現並修正「個人化首頁被 CDN 快取」

最後一段把故事搬到 127.0.0.1：一個 origin 扮演 Flask 首頁，依 cookie 回個人化內容；一個 CDN 是真正的 HTTP proxy，預設 cache key 只有 path，不存 `private`、`no-store` 與帶 `Set-Cookie` 的回應。四次造訪的順序固定為：小安、訪客、阿哲、小安。程式跑三個階段：事故版、只修 origin、完整修正。

```python
import http.client
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

USERS = {"sid=A": "小安", "sid=B": "阿哲"}
CONFIG = {"origin_fixed": False, "cdn_bypass_cookie": False}


class Origin(BaseHTTPRequestHandler):
    """Flask 首頁的替身：登入的人看到自己的名字與課表。"""
    def log_message(self, *args):
        pass

    def do_GET(self):
        name = USERS.get(self.headers.get("Cookie", ""))
        body = f"<p>歡迎回來，{name}！下一堂：日文會話</p>" if name else "<p>歡迎！免費試聽</p>"
        if not CONFIG["origin_fixed"]:
            cc = "public, max-age=60"                   # 事故版：為了衝命中率，全部標成 public
        elif name:
            cc = "private, max-age=0"                   # 修正版：個人化頁面只准瀏覽器存
        else:
            cc = "public, max-age=0, s-maxage=60"       # 匿名版：CDN 可以存 60 秒
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", cc)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class CDN(BaseHTTPRequestHandler):
    """預設 cache key 只有 path 的 edge；store 是 {path: (stored_at, headers, body)}。"""
    store = {}

    def log_message(self, *args):
        pass

    def do_GET(self):
        cookie = self.headers.get("Cookie")
        bypass = CONFIG["cdn_bypass_cookie"] and cookie and "sid=" in cookie
        hit = None if bypass else self.store.get(self.path)
        if hit and time.monotonic() - hit[0] < hit[1]["ttl"]:
            return self.relay(hit[2], hit[1]["cc"], "HIT")
        conn = http.client.HTTPConnection("127.0.0.1", ORIGIN_PORT, timeout=3)
        conn.request("GET", self.path, headers={"Cookie": cookie} if cookie else {})
        resp = conn.getresponse()
        body, cc = resp.read(), resp.getheader("Cache-Control", "")
        conn.close()
        d = {k.strip().split("=")[0]: k.strip().partition("=")[2] for k in cc.split(",")}
        ttl = int(d.get("s-maxage") or d.get("max-age") or 0)
        storable = not bypass and "private" not in d and "no-store" not in d \
            and resp.getheader("Set-Cookie") is None and ttl > 0
        if storable:
            self.store[self.path] = (time.monotonic(), {"ttl": ttl, "cc": cc}, body)
        self.relay(body, cc, "BYPASS" if bypass else "MISS")

    def relay(self, body, cc, result):
        self.send_response(200)
        self.send_header("Cache-Control", cc)
        self.send_header("X-Cache", result)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def visit(who, cookie):
    conn = http.client.HTTPConnection("127.0.0.1", CDN_PORT, timeout=3)
    conn.request("GET", "/", headers={"Cookie": cookie} if cookie else {})
    resp = conn.getresponse()
    page = resp.read().decode()
    conn.close()
    print(f"  {who:6} X-Cache={resp.getheader('X-Cache'):6} {page}")
    return page


origin, cdn = ThreadingHTTPServer(("127.0.0.1", 0), Origin), ThreadingHTTPServer(("127.0.0.1", 0), CDN)
ORIGIN_PORT, CDN_PORT = origin.server_address[1], cdn.server_address[1]
for srv in (origin, cdn):
    threading.Thread(target=srv.serve_forever, daemon=True).start()

stages = [("事故：全部 public, max-age=60", False, False),
          ("只修 origin：個人化改 private", True, False),
          ("完整修正：private ＋ CDN 遇到登入 cookie 就 bypass", True, True)]
results = []
for title, fixed, bypass in stages:
    CDN.store.clear()
    CONFIG.update(origin_fixed=fixed, cdn_bypass_cookie=bypass)
    print(title)
    results.append([visit("小安", "sid=A"), visit("訪客", None), visit("阿哲", "sid=B"), visit("小安", "sid=A")])

assert "小安" in results[0][2]                        # 事故：阿哲看到小安的頁面
assert "小安" in results[1][0] and "免費試聽" in results[1][3]   # 半套修正：小安像被登出
assert "阿哲" in results[2][2] and "小安" in results[2][3] and "免費試聽" in results[2][1]
for srv in (origin, cdn):
    srv.shutdown()
    srv.server_close()
```

```text
事故：全部 public, max-age=60
  小安     X-Cache=MISS   <p>歡迎回來，小安！下一堂：日文會話</p>
  訪客     X-Cache=HIT    <p>歡迎回來，小安！下一堂：日文會話</p>
  阿哲     X-Cache=HIT    <p>歡迎回來，小安！下一堂：日文會話</p>
  小安     X-Cache=HIT    <p>歡迎回來，小安！下一堂：日文會話</p>
只修 origin：個人化改 private
  小安     X-Cache=MISS   <p>歡迎回來，小安！下一堂：日文會話</p>
  訪客     X-Cache=MISS   <p>歡迎！免費試聽</p>
  阿哲     X-Cache=HIT    <p>歡迎！免費試聽</p>
  小安     X-Cache=HIT    <p>歡迎！免費試聽</p>
完整修正：private ＋ CDN 遇到登入 cookie 就 bypass
  小安     X-Cache=BYPASS <p>歡迎回來，小安！下一堂：日文會話</p>
  訪客     X-Cache=MISS   <p>歡迎！免費試聽</p>
  阿哲     X-Cache=BYPASS <p>歡迎回來，阿哲！下一堂：日文會話</p>
  小安     X-Cache=BYPASS <p>歡迎回來，小安！下一堂：日文會話</p>
```

第一階段就是故事本身：小安 MISS，CDN 存下 `public, max-age=60` 的個人化頁面，接下來的訪客和阿哲都 HIT 到它。CDN「不存帶 `Set-Cookie` 的回應」這道保險沒有作用，因為首頁平常不送 `Set-Cookie`。

第二階段只修 origin：個人化頁面改成 `private, max-age=0`，匿名頁面改成 `public, max-age=0, s-maxage=60`。個資外洩停止了，小安的頁面不再被存；但新的問題出現：訪客的匿名頁面被存下來，而 cache key 仍然只有 path，於是阿哲和小安都 HIT 到「歡迎！免費試聽」，看起來像被登出。如果只修一半就上線，客服會收到另一波「我被登出了」的抱怨。

第三階段加上 CDN 的規則：請求帶登入 cookie（這裡是 `sid=`）就 bypass 快取，直接到 origin。登入的人每次都拿到自己的頁面，訪客則享受 CDN 的快取。兩道防線各管一件事：`private` 是 origin 對所有快取的宣告，即使 CDN 規則寫錯也不會外洩；CDN 的 bypass 規則決定 cache key 的語意，讓登入與未登入的請求不會互相命中。真實系統常把 bypass 條件寫成「有 `__Host-sid` cookie」，並把匿名首頁上的 cookie 相關內容（例如右上角的登入狀態）改成用 JavaScript 呼叫 `private` 的 `/v1/me` 填入，讓 HTML 本身完全不個人化，命中率就能維持在高水準。

## 21.12 在工作上怎麼用

事故檢討後，阿德和小晴把聲聲 Live 各類回應的快取策略整理成一張表，往後新增路由時先對照：

| 回應類型 | Cache-Control | Validator | 備註 |
|---|---|---|---|
| 檔名帶 hash 的 JS、CSS、字型 | `public, max-age=31536000, immutable` | 可省略 | 內容變了就換檔名，舊檔名永遠不變 |
| 匿名 HTML（首頁、老師介紹頁） | `public, max-age=0, s-maxage=60, stale-while-revalidate=30` | ETag | 瀏覽器每次問 CDN，CDN 擋住 origin |
| 個人化 HTML、`/v1/me` | `private, max-age=0` 或 `private, no-cache` | ETag | 個人化首頁一律 `private`（第 1 章） |
| 一般 API 讀取（今日課表） | `private, no-cache` | ETag | 依使用者而異；省頻寬靠 304 |
| 公開 API（課程目錄） | `public, max-age=300` ＋ `Vary: Accept-Language` | ETag | CDN 對語言做正規化 |
| 付款結果、TOTP 設定、會設定 cookie 的回應 | `no-store` | 無 | 連瀏覽器都不留 |
| 錄影檔 | `private, max-age=3600` | 強 ETag | 由 nginx 直接送，支援 Range |

用一個流程圖決定新路由該用哪一列：

```text
 新的回應
   │
   ├─ 含秘密、一次性資料，或會 Set-Cookie？ ── 是 ──► no-store
   │
   ├─ 內容依使用者（cookie／token）而不同？ ── 是 ──► private ＋ (max-age=0 或 no-cache) ＋ ETag
   │                                                   CDN：帶登入 cookie 就 bypass
   ├─ 內容永不改變（URL 帶版本或 hash）？ ──── 是 ──► public, max-age=31536000, immutable
   │
   ├─ 內容依某個請求 header 而不同？ ──────── 是 ──► 加 Vary（只列必要的 header），
   │                                                   能改用 URL 區分就改用 URL
   └─ 其他公開內容 ──► public, max-age=短（瀏覽器）, s-maxage=較長（CDN）＋ ETag
                       視需要加 stale-while-revalidate／stale-if-error
```

這張圖越上面的問題越優先，因為安全比效能重要：前兩個分岔回答「是」的回應，不論效能多誘人都不能讓 shared cache 存。之後才是效能優化：不可變的資源給最長的快取，依 header 而變的加最少的 `Vary`，其餘用 `s-maxage` 讓 CDN 擋流量、用短的 `max-age` 讓使用者盡快看到更新。

**後端工程師：在 Flask 裡把策略寫進程式。** Werkzeug 的 Response 物件提供 `cache_control` 屬性、`add_etag()` 與 `make_conditional()`，後者會依請求的條件 header，在 ETag 相符時自動把回應改成 304。下面是首頁依登入狀態決定快取策略的寫法：

```python
# not-runnable
from flask import Flask, make_response, render_template, request, session

app = Flask(__name__)


@app.get("/")
def home():
    user = session.get("user")              # 存取 session 會讓 Flask 自動加上 Vary: Cookie
    resp = make_response(render_template("home.html", user=user))
    if user:
        resp.cache_control.private = True   # 個人化：只准瀏覽器存
        resp.cache_control.max_age = 0
    else:
        resp.cache_control.public = True    # 匿名：瀏覽器每次問，CDN 存 60 秒
        resp.cache_control.max_age = 0
        resp.cache_control.s_maxage = 60
    resp.add_etag()                         # 依 body 算 ETag
    return resp.make_conditional(request)   # If-None-Match 相符時改成 304
```

程式審查時要看：依 `session` 或 `g.user` 改變內容的 view 有沒有標 `private`，有沒有 view 設定 cookie 又標 `public`。最好做成測試：每個路由分別用登入與未登入身分請求，斷言回應 header。

**SRE：用 curl 檢查快取行為。** 下面這組指令可以快速確認一個 URL 在 CDN 上的實際狀態。CDN 回報命中與否的 header 名稱各家不同（`X-Cache`、`CF-Cache-Status`、`Cache-Status` 等），以下為示意輸出：

```bash
curl -sI https://www.shengsheng.example/ | grep -iE 'cache-control|age|etag|vary|x-cache'
curl -sI -H 'Cookie: __Host-sid=test' https://www.shengsheng.example/ | grep -iE 'cache-control|x-cache'
curl -sI -H 'If-None-Match: "home-v1"' https://www.shengsheng.example/        # 期待 304
curl -s -o /dev/null -w '%{size_download} %{http_code}\n' -H 'Accept-Encoding: gzip' https://www.shengsheng.example/static/app.3f9c.js
curl -sI -H 'Range: bytes=0-1023' https://www.shengsheng.example/recordings/lesson-0815.mp4   # 期待 206
```

```text
cache-control: public, max-age=0, s-maxage=60, stale-while-revalidate=30
age: 23
etag: "home-v1"
x-cache: HIT
```

示意輸出顯示匿名首頁在 CDN 上已存了 23 秒，`s-maxage=60` 下還有 37 秒新鮮期。第二行指令帶登入 cookie，應該看到 `private` 與 BYPASS 或 MISS；如果看到 HIT，就是故事裡的事故正在發生。第三行驗證條件請求，第四行比較壓縮後的大小，第五行確認 Range。把第二行做成部署後的 smoke test，就能在上線幾分鐘內抓到同類錯誤。

**前端工程師：讀懂 DevTools。** Network 面板的 Size 欄顯示「(disk cache)」或「(memory cache)」代表瀏覽器完全沒上網；Status 顯示 304 代表有上網驗證但沒下載 body。「Disable cache」只影響開著 DevTools 的分頁，不影響 CDN。HTML 用短快取加驗證、引用的 JS 與 CSS 檔名帶 hash，才能同時做到長快取與立即更新。

**資安工程師：把快取納入審查。** Rita 在路由審查中加了三個問題：回應含個人資料嗎？有沒有回應同時設 cookie 又可被 shared cache 存？origin 有沒有依不在 cache key 裡的 header 改變內容？事故處置順序是：改回設定、purge CDN、從 CDN log 估算受影響範圍，再依個資事故流程通報。

## 21.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 使用者看到別人的名字或資料 | 個人化回應被標 `public` 或 `s-maxage`，CDN 的 cache key 不含使用者 | `curl -I` 帶不同 cookie，看 `X-Cache` 與 `Cache-Control`；查 CDN log 的命中紀錄 | 立刻 purge；個人化回應改 `private`；CDN 對登入 cookie bypass |
| 部署新版後，部分使用者一直拿到舊的 JS | 檔名沒帶 hash 卻設了長 `max-age`；或沒設 `Cache-Control` 而被啟發式快取 | DevTools 看 Size 欄是 disk cache；`curl -I` 看 `Last-Modified` 與有沒有 `Cache-Control` | 靜態檔名帶 hash 加 `immutable`；HTML 用 `no-cache`；明確寫出每個回應的 `Cache-Control` |
| 切換語言後偶爾看到另一種語言 | 依 `Accept-Language` 決定內容，卻沒有 `Vary`，或語言只存在 cookie 裡 | 用不同 `Accept-Language` 打同一個 URL，看 CDN 是否 HIT 到同一份 | 語言放進 URL；或加 `Vary: Accept-Language` 並在 CDN 正規化 |
| CDN 命中率突然掉到接近 0 | 某次改動加了 `Vary: Cookie` 或 `Vary: User-Agent`；或 query string 帶了隨機追蹤參數 | 看回應的 `Vary`；看 CDN 的 cache key 統計 | 移除不必要的 `Vary`；CDN 設定忽略追蹤用的 query 參數 |
| 永遠拿不到 304，每次都整份重傳 | 多台 origin 的 ETag 不一致（依 inode 或 mtime）；或 gzip 讓 ETag 變弱後 server 用強比較 | 連打同一 URL，看 ETag 是否在不同 request 間跳動 | ETag 由內容 hash 或資料版本產生；`If-None-Match` 用弱比較 |
| 兩人同時編輯，後存的蓋掉先存的 | PUT 沒有條件，沒有版本檢查 | 重現兩個分頁的操作順序 | 回應帶 ETag，PUT 要求 `If-Match`，不符回 412，沒帶回 428 |
| 影片拖曳進度條就從頭下載 | 應用程式整份回傳，忽略 `Range`、沒有 `Accept-Ranges` | `curl -I -H 'Range: bytes=0-99'` 看是 200 還是 206 | 由 nginx 或 `send_file` 直接服務檔案 |
| API 搬家後 client 的 POST 變成 GET 失敗 | 用了 301／302，client 重送時改成 GET | 看 client log 的第二個請求 method | 改用 307（暫時）或 308（永久） |
| 「重新導向次數過多」 | CDN 用 HTTP 連 origin，origin 又導向 HTTPS | `curl -sIL` 看 `Location` 迴圈 | origin 依 `X-Forwarded-Proto` 判斷；或 CDN 用 HTTPS 連 origin |
| 登入後某些子網域收不到 session，或收到不該收的 | cookie 的 `Domain` 設錯：沒寫是 host-only，寫了會擴及所有子網域 | DevTools 的 Application → Cookies 看 Domain 欄 | session 用 `__Host-` 前綴、不寫 Domain；需要跨子網域的改用正式的 SSO（第 29 章） |
| 請求得到 400 或 431，只有部分使用者 | cookie 累積太多太大，超過 server 的 header 上限 | 看失敗請求的 `Cookie` header 長度 | 清掉不必要的 cookie；縮短值；分析工具的 cookie 不要設在共用網域 |

除錯的通則是：**先看 header，再看程式**。快取問題幾乎都能從 `Cache-Control`、`Age`、`ETag`、`Vary` 與 CDN 的命中 header 推出原因；cookie 問題則看 `Set-Cookie` 的屬性與 DevTools 存下來的 Domain、Path。測試時要用登入、未登入、不同語言幾種身分各試一次，因為快取的錯誤往往只在第二個人身上才看得到。

## 21.14 動手練習

1. **延伸實驗三：加上 `must-revalidate` 與 `stale-if-error`**。讓 origin 函式可以切換成「拋出例外」模擬故障，替 `SharedCache` 加上：過期的回應若帶 `stale-if-error=N`，在年齡不超過新鮮期加 N 秒時，origin 失敗就回舊的；若帶 `must-revalidate`，origin 失敗就回 504。
   答案要點：兩個指令的意圖相反，`stale-if-error` 是「寧可舊也不要錯」，適合課程目錄；`must-revalidate` 是「寧可錯也不要舊」，適合價格。你的實作要確認兩者同時出現時以 `must-revalidate` 為準，並在輸出中印出 `STALE (origin error)` 與 `504` 兩種結果。

2. **延伸實驗一：加上弱 ETag 與 gzip**。讓實驗一的 server 依 `Accept-Encoding` 回 gzip 版本，並把 ETag 改成 `W/"…"`；驗證 `If-None-Match` 帶強或弱形式都會得到 304，而 `If-Match` 帶弱 ETag 的 PUT 會得到 412。
   答案要點：弱比較忽略 `W/` 前綴，強比較要求兩邊都不是弱 ETag 且字串相同。這解釋了為什麼經過 nginx gzip 後，用 ETag 做條件寫入會失敗：寫入用的 API 回應不應該經過會改寫 ETag 的壓縮層，或改用資料版本號放在 body 或自訂 header 中。

3. **用真實工具觀察 DevTools 的快取**（真實工具）。在本機執行 `python3 -m http.server 8765 --bind 127.0.0.1`，用瀏覽器打開一個靜態檔，在 DevTools 的 Network 面板觀察第一次 200、重新整理後的狀態碼，以及請求 header 中的 `If-Modified-Since` 與 `Cache-Control`。
   答案要點：`http.server` 會送 `Last-Modified` 並支援 `If-Modified-Since`，但不送 `Cache-Control` 與 ETag；重新整理時瀏覽器送條件請求並得到 304。勾選 Disable cache 後條件 header 消失、每次都是 200。也可以觀察瀏覽器在沒有 `Cache-Control` 時的啟發式快取：在新分頁直接開同一網址，可能看到 (disk cache)。

4. **用 curl 觀察真實網站的快取與壓縮**（真實工具）。挑一個你常用的網站，用 `curl -sI -H 'Accept-Encoding: gzip, br'` 看首頁與一個靜態檔的 `Cache-Control`、`Age`、`ETag`、`Vary`、`Content-Encoding`，連打兩次比較 `Age` 的變化。
   答案要點：靜態檔多半是長 `max-age` 加 `immutable` 或 hash 檔名，首頁多半是短快取或 `no-cache`／`private`；`Age` 在兩次之間增加代表命中同一份存貨，歸零或消失代表 MISS 或換了 edge。登入後的頁面若出現 `public` 加長 `s-maxage`，就值得懷疑。

5. **延伸實驗四：實作 `Max-Age=0` 刪除與同名覆寫**。替 cookie jar 加三個 `Set-Cookie`：先設 `lang=ja; Path=/`，再設 `lang=zh-TW; Path=/teachers`，最後 `lang=; Max-Age=0; Path=/`。印出每一步後 `/teachers/misaki` 與 `/` 的 `Cookie` header。
   答案要點：`(name, domain, path)` 不同就是不同的 cookie，所以第二步後 `/teachers/misaki` 會同時帶兩個 `lang`，Path 長的 `zh-TW` 在前；第三步只刪掉 `Path=/` 那一個，`/teachers` 底下仍帶 `lang=zh-TW`。這是「我明明刪了 cookie 怎麼還在」的常見原因：刪除時的 Domain 與 Path 必須和設定時相同。

6. **手算新鮮度**。CDN 收到 origin 的回應：`Cache-Control: public, max-age=30, s-maxage=120`，上一層 origin shield 加了 `Age: 50`。CDN 存了 40 秒後，學生的瀏覽器拿到這份回應。請問 CDN 這時還有多少新鮮期？瀏覽器拿到的 `Age` 是多少？瀏覽器能直接用它多久？
   答案要點：CDN 看 `s-maxage=120`，年齡是 50＋40＝90 秒，還剩 30 秒。CDN 回給瀏覽器的 `Age` 是 90；瀏覽器看 `max-age=30`，年齡 90 已超過 30，所以一拿到就是過期的，下次使用前要驗證。這說明了多層快取時 `max-age` 要考慮上游已經消耗的年齡。

## 本章重點整理

- HTTP 快取分成只服務一個人的 private cache（瀏覽器）與服務很多人的 shared cache（CDN、proxy）；shared cache 不能存 `private` 的回應，這是個人化頁面的第一道防線。
- 快取要回答四個問題：能不能存、能用多久、過期了怎麼驗證、哪些請求算等價；一次事故往往同時錯了其中兩個。
- 回應的年齡小於新鮮期就是 fresh；shared cache 優先看 `s-maxage`，所有快取都要把上游的 `Age` 算進年齡。
- `no-cache` 是「可以存但每次要驗證」，`no-store` 才是「不要存」；沒寫 `Cache-Control` 不等於不快取，快取可能依 `Last-Modified` 做啟發式快取。
- `stale-while-revalidate` 讓快取在過期後先給舊的、背景驗證，消除過期瞬間的延遲尖峰；`stale-if-error` 讓 origin 故障時仍能提供舊內容。
- 條件請求用 `If-None-Match`（ETag，弱比較）或 `If-Modified-Since` 驗證快取，沒變就得到沒有 body 的 304；兩者都送時以 `If-None-Match` 為準。
- 同一套 validator 也能防止 lost update：寫入時帶 `If-Match`，版本不符回 412，強制要求條件時對沒帶的請求回 428。
- cache key 基本上是 URL，`Vary` 把列出的請求 header 加進 key；`Vary: Cookie` 與 `Vary: User-Agent` 會讓命中率崩潰，能用 URL 區分的維度就用 URL。
- 內容協商用 `Accept`、`Accept-Language`、`Accept-Encoding` 與 q 值表達偏好；`Content-Encoding` 是表示法的屬性，`Transfer-Encoding` 只是單一跳的傳輸方式。
- 壓縮只用在文字類資源，不同編碼的版本要有不同的 ETag 並帶 `Vary: Accept-Encoding`；秘密與攻擊者可控的內容不要放在同一個壓縮回應裡。
- Range 請求讓 client 只拿一段 bytes，成功回 206 與 `Content-Range`，超出範圍回 416；續傳時用 `If-Range` 確保檔案版本沒換。
- cookie 的屬性只在 `Set-Cookie` 出現，請求只帶 `name=value`；寫了 `Domain` 範圍反而變大，session cookie 應使用 `__Host-` 前綴、`Secure`、`HttpOnly`、`Path=/` 且不寫 Domain。
- 301 與 302 在重送時可能把 POST 改成 GET，要保留 method 就用 307 或 308；301 與 308 會被瀏覽器快取，新規則先用暫時導向驗證。
- 個人化首頁的正確修法是兩道防線：origin 標 `Cache-Control: private`，CDN 對帶登入 cookie 的請求 bypass；只做一半，不是外洩就是讓使用者看起來被登出。

## 延伸問答

> [!question]- Q1. `Cache-Control: no-cache`、`no-store`、`private` 與 `max-age=0` 有什麼不同？各舉一個聲聲 Live 的使用情境。
> `no-store` 是唯一真正的「不要存」：瀏覽器與 CDN 都不能把回應寫進快取，適合付款結果、TOTP 設定頁這種連在共用電腦上留下痕跡都不行的內容。`private` 只禁止 shared cache，瀏覽器仍然可以存，適合個人化首頁與 `/v1/me`：小安的瀏覽器存小安的頁面沒有問題，但 CDN 不能存。
>
> `no-cache` 與 `max-age=0` 很接近：兩者都允許存，但使用前都要驗證。差別在細節：`no-cache` 明確要求「每次都要先問 origin」，而 `max-age=0` 只是說「一存進來就過期」，規格允許快取在特定條件下（例如連不上 origin，且沒有 `must-revalidate`）提供過期內容。所以要確保每次都驗證，用 `no-cache`；只是想讓瀏覽器每次問、但讓 CDN 依 `s-maxage` 存，用 `max-age=0, s-maxage=60`。這幾個指令可以組合，例如個人化頁面寫成 `private, no-cache`，表示「只准瀏覽器存，而且每次都要驗證」。

> [!question]- Q2. 手算：origin 回應 `Cache-Control: public, max-age=60, stale-while-revalidate=30`，CDN 在 20:00:00 存入。20:00:45、20:01:10、20:01:40 各有一個請求進來，CDN 分別怎麼處理？
> 20:00:45 時年齡 45 秒，小於 `max-age=60`（沒有 `s-maxage`，CDN 就用 `max-age`），所以是 fresh，直接 HIT，origin 完全不知道這個請求。20:01:10 時年齡 70 秒，已經過期，但在 60＋30＝90 秒的容忍期內，CDN 立刻把舊的回應給使用者，同時在背景對 origin 發一個條件請求；假設 origin 在 20:01:10 回了 304，這份存貨的年齡就從那一刻歸零。
>
> 20:01:40 的答案取決於背景驗證有沒有成功。如果成功，年齡只有 30 秒，又是 fresh 的 HIT。如果背景驗證失敗或 CDN 沒有實作 `stale-while-revalidate`，年齡是 100 秒，超過 90 秒的容忍期，CDN 必須同步向 origin 驗證，使用者要等這一趟。這題的重點是：`stale-while-revalidate` 並不延長「不問 origin 的時間」，它只是把「問 origin」從使用者的等待路徑上移到背景。

> [!question]- Q3. 看 log 找原因：nginx 的 access log 顯示瀏覽器每次都帶著 `If-None-Match`，但 origin 永遠回 200，從來沒有 304。可能是什麼原因？怎麼查？
> 先比對瀏覽器送來的 `If-None-Match` 和 origin 這次回應的 `ETag` 是不是同一個字串。最常見的原因是多台 origin 的 ETag 不一致：例如 ETag 由檔案的 mtime 加大小產生，而每台機器部署的時間不同，同一份檔案在每台機器上的 ETag 都不一樣；負載平衡把請求送到另一台，ETag 自然不相符。查法是連打同一個 URL 幾十次，看回應的 ETag 是否在幾個值之間跳動，並對照 `x-request-id` 找出是哪台 upstream。
>
> 第二個常見原因是壓縮改寫了 ETag：nginx 對 gzip 過的回應把 `"abc"` 變成 `W/"abc"`，瀏覽器送回 `W/"abc"`，如果 origin 的比對邏輯是強比較或直接字串相等，就永遠不相符。第三個可能是 ETag 包含了會變的東西，例如把整頁 HTML 算 hash，而頁面裡有每次請求都不同的 CSRF token 或時間戳。修正方向分別是：ETag 只由內容 hash 或資料版本決定、`If-None-Match` 用弱比較、把每次都變的部分移出可快取的 HTML。

> [!question]- Q4. 設計取捨：首頁要同時服務登入與未登入使用者。`Vary: Cookie`、「CDN 對登入 cookie bypass」、「HTML 完全不個人化，個人資訊用 JavaScript 另外抓」三種做法各有什麼取捨？
> `Vary: Cookie` 在規格上最直接：cookie 不同的請求不會共用存貨。但 cookie 字串包含 session、語言、A/B 測試、分析工具等各種值，幾乎每個使用者都不同，CDN 等於替每個人存一份，命中率接近零，還會佔滿快取空間；而且它把隱私押在每一層快取都正確實作 `Vary` 上。它適合作為輔助保險，不適合當主要機制。
>
> 「CDN 對登入 cookie bypass」加上 origin 的 `private`，是實驗五的完整修正：登入的人每次都到 origin，未登入的人享受快取。它簡單、安全，代價是登入使用者的首頁完全沒有 CDN 加速，尖峰時 origin 仍要為每個登入學生產生一次頁面。第三種做法把 HTML 做成所有人都一樣的骨架，以 `public, s-maxage` 快取，再由 JavaScript 呼叫 `private` 的 `/v1/me` 填入名字與課表；它讓命中率最高、origin 負載最低，代價是多一次 API 請求、首屏的個人資訊會稍晚出現，前端也要處理載入狀態。聲聲 Live 的短期修正用第二種，長期往第三種改。

> [!question]- Q5. 面試題：說明 ETag 的強弱之分，以及為什麼 `If-None-Match` 用弱比較，`If-Match` 和 `If-Range` 用強比較。
> 強 ETag 承諾兩份表示法的 bytes 完全相同；弱 ETag（前面加 `W/`）只承諾語意相同，例如同一份 HTML 只差在壓縮或無關緊要的空白。強比較要求兩個 ETag 都是強的且字串相同；弱比較則忽略 `W/` 前綴，只比字串。
>
> 比較方式的選擇取決於「相符之後要做什麼」。`If-None-Match` 用於快取驗證，相符代表「你手上那份還能用」，語意相同就夠了，即使 bytes 有一點不同，使用者看到的內容仍然正確，所以用弱比較，讓經過壓縮層而變成弱 ETag 的回應也能得到 304。`If-Range` 相符時 server 只送一段 bytes，client 會把它接在手上的舊 bytes 後面，只要有一個 byte 不同，拼出來的檔案就是壞的，必須用強比較。`If-Match` 用於條件寫入，目的是確認「我讀到的就是現在這一版」，語意相同但內容不同的兩個版本仍可能讓更新覆蓋掉別人的修改，所以也用強比較。

> [!question]- Q6. 情境判斷：你在 production 看到 `Set-Cookie: sid=…; Domain=shengsheng.example; Path=/; HttpOnly`，Rita 要求修改。問題在哪？要改成什麼？
> 這個 cookie 有三個問題。第一，寫了 `Domain=shengsheng.example`，session 會送給所有子網域：`api`、`rt`、`auth`，以及未來任何一個子網域（例如外包的活動頁）。任何一個子網域被入侵或設定錯誤，都能收到使用者的 session。第二，沒有 `Secure`，如果有任何 HTTP 請求（例如 HSTS 還沒生效的第一次造訪），cookie 會以明文送出。第三，沒有 `SameSite`，跨站請求的行為依瀏覽器預設而定，CSRF 的防禦不完整（第 23 章）。
>
> 建議改成 `Set-Cookie: __Host-sid=…; Path=/; Secure; HttpOnly; SameSite=Lax`。`__Host-` 前綴讓瀏覽器強制檢查「有 Secure、沒有 Domain、Path 是 /」，server 收到這個名字的 cookie，就能確定它是 `www` 自己用 HTTPS 設定的，子網域無法偽造或覆寫。如果 `api` 子網域真的需要知道使用者是誰，應該用短效 token 或正式的 SSO 流程（第 27、29 章），而不是共用 session cookie。改名時要注意舊名稱的 cookie 會繼續存在，需要用相同的 Domain 與 Path 加 `Max-Age=0` 刪除。

> [!question]- Q7. 為什麼表單送出後應該回 303 而不是 200？又為什麼 API 搬家要用 308 而不是 301？
> 如果 POST /payments 直接回 200 和結果頁，使用者按重新整理時，瀏覽器會重送那個 POST，可能重複扣款；瀏覽器會跳出「確認重新提交表單」，但很多人會直接按確定。回 303 See Other 加上 `Location: /payments/123`，瀏覽器會改用 GET 去拿結果頁，之後的重新整理只是重送 GET，這就是 PRG（Post/Redirect/Get）模式。真正防止重複扣款仍需要 server 端的 idempotency key（第 24 章），303 只是讓正常操作不會觸發重送。
>
> API 搬家的情況相反：client 的 POST 帶著 body，導向後必須以同樣的 method 和 body 送到新位置。301 的歷史行為允許 client 把 POST 改成 GET，很多 HTTP 函式庫也這麼做，結果是新位置收到一個沒有 body 的 GET，回 405 或 404。308 Permanent Redirect 明確要求保持 method 與 body，307 是它的暫時版本。另外，301 與 308 都可能被快取，API 搬家前要確認新位置長期有效。

> [!question]- Q8. 看封包或 header 判斷：一位學生回報錄影回放拖曳後畫面卡住，DevTools 顯示請求帶 `Range: bytes=52428800-`，回應是 `200 OK`、`Content-Length: 314572800`、沒有 `Accept-Ranges`。發生了什麼？要怎麼修？
> 播放器要從第 50 MiB（52,428,800 bytes）開始讀，期待 206 Partial Content 與 `Content-Range: bytes 52428800-…/314572800`。server 卻回 200 和整份 300 MiB，表示它忽略了 Range，這在規格上是允許的，但播放器必須從頭下載到第 50 MiB 才能播放那一段，在行動網路上就是長時間卡住。沒有 `Accept-Ranges: bytes` 也證實了 server 不支援 Range，播放器之後連 seek 都可能放棄嘗試。
>
> 先找出是哪一層忽略了 Range：直接對 origin 與對 CDN 各打一次 `curl -I -H 'Range: bytes=0-99'`。如果 origin 就回 200，通常是應用程式自己讀檔回傳整份，修法是交給 nginx 直接服務檔案，或改用支援條件請求與 Range 的 `send_file`；如果 origin 回 206 而 CDN 回 200，要查 CDN 對大檔與 Range 的設定（有些 CDN 需要開啟分段快取）。修好後還要確認回應帶強 ETag，讓播放器續傳時能用 `If-Range` 確保檔案沒換。

## 延伸閱讀

- RFC 9111〈HTTP Caching〉：快取的儲存、新鮮度、驗證與 `Cache-Control` 指令的定義
- RFC 9110〈HTTP Semantics〉：條件請求、內容協商、Range、redirect 與 status code 的語意
- RFC 5861〈HTTP Cache-Control Extensions for Stale Content〉：`stale-while-revalidate` 與 `stale-if-error`
- RFC 8246〈HTTP Immutable Responses〉：`immutable` 指令
- RFC 6265〈HTTP State Management Mechanism〉與 draft-ietf-httpbis-rfc6265bis：cookie 的語法、屬性與儲存規則
- RFC 1952〈GZIP file format specification version 4.3〉：gzip header 與 trailer 的格式
- MDN Web Docs：HTTP caching、HTTP conditional requests、Using HTTP cookies
