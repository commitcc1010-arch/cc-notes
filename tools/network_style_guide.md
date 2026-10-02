# 《從封包到即時影音：工程師的網路全書》寫作規範

所有章節與附錄都必須遵守本規範。`tools/check_network_book.py` 會自動檢查可機器驗證的部分。

## 1. 讀者與目標

- **讀者**：junior 軟體工程師（後端、前端、全端），會寫 Python，用過 Flask 或類似框架、呼叫過 HTTP API，但對網路底層只有零碎概念：知道「DNS 把名字變 IP」「HTTPS 比較安全」，說不清楚為什麼、出事時不知道從哪裡查。
- **目標**：讀者**只靠這本書**就能完整認識整個網路：從 Ethernet、IP、TCP、DNS、TLS、HTTP，到驗證與授權（session、JWT、OAuth、OIDC、passkeys）、即時通訊（SSE、WebSocket）、即時影音（RTP、SDP、WebRTC、SRT、HLS），以及 Python 的 Web 伺服器堆疊（WSGI、Werkzeug、ASGI、gunicorn、uvicorn）與雲端網路。讀完能看懂封包與 log、設計正確的 API 與驗證流程、在工作上獨立除錯網路問題，並在系統設計討論中說清楚取捨。
- **深入淺出、循序漸進**：每章建立在前面章節之上；每個新名詞第一次出現就白話解釋並舉例。深度與廣度兼備：概念講到能自己推導，也補上業界現況與實務細節。
- **自給自足**：不能用「詳見 RFC」取代解釋；RFC 與官方文件是延伸閱讀。
- **以原理為主、現況為輔**：會變動的資訊（瀏覽器支援、部署比例、標準化進度、產品功能）放在標題含「2026 現況」的小節或 `> [!note] 2026 現況` callout，並寫明「截至 2026 年 10 月」。
- 引用本書其他章節寫「第 N 章」。

## 2. 語言與格式

- 繁體中文（台灣用語：網路、封包、伺服器、程式、檔案、設定、預設、憑證、連線）。業界通用的英文術語保留英文（packet、handshake、resolver、header、cookie、token、codec），第一次出現時附中文解釋。
- **中英文之間一定加半形空格**；中文句子用全形標點。
- 段落 3–6 句，一段一件事。主體是有因果的敘事文字；條列、表格、圖是輔助。
- 新名詞第一次出現用粗體並立即白話定義，緊接一個具體例子。
- **視覺化是必要的**：每章至少 4 張 ```` ```text ```` 圖（封包與 header 位元布局、時序圖、狀態機、拓撲圖、流程圖、時間軸），至少 3 張 Markdown 表格。每張圖後要用文字逐步解說。時序圖範例：

```text
 Client                                   Server
   │──────────── SYN  seq=x ───────────────►│
   │◄──────── SYN+ACK seq=y ack=x+1 ────────│
   │──────────── ACK  ack=y+1 ──────────────►│
   │            （連線建立，開始傳資料）        │
```

## 3. 章節固定結構

```markdown
---
chapter: 10
title: TCP 連線：交握、狀態與關閉
part: 2
---

# 第 10 章　TCP 連線：交握、狀態與關閉

> [!abstract] 本章地圖
> **核心問題**：（一句話）
>
> **你會學到**：
> - （3–6 點，讀完能「做到」什麼）
>
> **前置知識**：第 N 章（…）

## 10.1 故事：（聲聲 Live 遇到的問題）
## 10.2 ～ 10.k（核心概念，由淺入深，節與節之間有承接句）
## 10.x 動手做：（主題）
## 10.x 在工作上怎麼用
## 10.x 常見錯誤與除錯
## 10.x 動手練習
## 本章重點整理
## 延伸問答
## 延伸閱讀
```

- 節號格式「## 10.3 標題」，連續編號。第一節必須是「故事」。最後三個 H2 依序固定為「本章重點整理」「延伸問答」「延伸閱讀」。
- 「動手做」「在工作上怎麼用」「常見錯誤與除錯」「動手練習」四節必須存在（標題以這些字開頭，冒號後可加副題）。
- **故事**：用聲聲 Live 的具體問題開場，說清楚「不懂本章的東西，會卡在哪裡」，並在整章中持續使用。
- **核心概念**：每個機制依序講：為什麼需要 → 怎麼運作（原理、header 圖、時序圖、手算或逐步追蹤）→ 在真實系統長什麼樣（實際封包、真實 header、工具輸出）→ 取捨與常見誤解。
- **動手做**：至少一段可執行的 Python，緊接 ```` ```text ```` 區塊貼上**實際執行**的輸出，再逐步解說。
- **在工作上怎麼用**：具體的工作情境（後端、前端、SRE、影音、資安），附工具指令、判斷流程或檢查清單。
- **常見錯誤與除錯**：表格列出 5 項以上：症狀｜原因｜怎麼確認｜怎麼修。
- **動手練習**：4–6 個讀者可以實際做的練習，至少一個延伸本章程式、至少一個用真實工具觀察（dig、curl、tcpdump、DevTools…），並附答案要點或驗證方法。
- **本章重點整理**：8–15 條完整句子。
- **延伸問答**：8 題，格式見第 5 節。
- **延伸閱讀**：3–8 項，只寫名稱與出處（例如「RFC 9293〈Transmission Control Protocol (TCP)〉」），不放 URL。
- 可用 callout：`> [!note]`、`> [!tip]`、`> [!warning] 常見誤解`、`> [!example] 例子`、`> [!note] 2026 現況`、`> [!abstract] 本章地圖`（只用於開頭）、`> [!question]- Qn. …`（只用於延伸問答）。
- 字數：正文（不含延伸問答與程式碼）約 15,000–26,000 可見字元。

設計章（第 33、37、46 章）的核心概念依 system design 流程展開：需求 → 估算 → 架構 → 深入元件 → 擴展與取捨 → 追問。

## 4. 程式碼規則（checker 會執行）

- 只用 Python 3.11+ 與**標準函式庫**（socket、socketserver、selectors、asyncio、http.server、http.client、urllib、wsgiref、ssl、hashlib、hmac、secrets、base64、struct、ipaddress、json、threading）。不能 import 第三方套件。
- 每段 ```` ```python ```` 都會被**單獨執行**（10 秒逾時），所以每段要自給自足：server 與 client 寫在同一段（server 用 thread 或 asyncio task），在 **127.0.0.1** 上用 **port 0** 讓系統分配埠號，結束時關閉 socket 與 thread。
- **不能連外網**、不能需要 root 權限、不能依賴系統上的其他服務。需要外部資源的情境（真實 DNS、真實網站、raw socket、tcpdump）用本機假 server 模擬，或以 `bash` 區塊列出指令並標明「示意輸出」。
- 用 `assert` 驗證行為，並印出結果。需要時間的程式用模擬時鐘；不要 sleep 超過 0.5 秒。
- 示範第三方套件（Werkzeug、Flask、FastAPI、uvicorn、gunicorn、aiortc、PyJWT 等）的程式，第一行寫 `# not-runnable`，checker 會略過；要依官方真實介面撰寫，不確定的參數不要寫。
- ```` ```text ```` 中的執行輸出必須是實際執行得到的；含隨機埠號或時間的輸出，可以在程式中固定格式或說明「每次執行數字不同」。
- 程式長度一般 30–150 行；有意義的命名；註解說「為什麼」。
- 範例網域只用 example.com、example.net、example.org 與 `.example`、`.test`、`.invalid` 等保留名稱；範例 IP 用 192.0.2.0/24、198.51.100.0/24、203.0.113.0/24（文件用位址）、10.0.0.0/8 等私有位址與 127.0.0.1。程式碼中可以出現這些範例 URL，正文不放真實 URL。

## 5. 延伸問答格式（checker 會解析）

```markdown
## 延伸問答

> [!question]- Q1. 為什麼 TIME_WAIT 是在主動關閉的一方？
> 第一段答案……
>
> 第二段答案……
```

- 題號 Q1–Q8 連續。答案至少 150 可見字元，要解釋判斷依據。
- 題型多樣：概念辨析、手算、情境判斷（「你在 production 看到…」）、面試題、看封包或 log 找原因、設計取捨。

## 6. 貫穿案例：聲聲 Live

聲聲 Live 是線上語言家教平台：

```text
 學生／老師瀏覽器 ──HTTPS──► CDN ──► Load Balancer ──► nginx ──► gunicorn ──► Flask（WSGI，Werkzeug）
        │                                                  └──► uvicorn ──► 即時服務（ASGI：WebSocket 聊天、白板）
        │──WebRTC（ICE／STUN／TURN、DTLS-SRTP）──► SFU（一對一與小班課）
 講者的編碼器 ──SRT──► 直播 ingest ──► 轉碼 ──► LL-HLS（CDN）／WHEP 觀看
 登入：密碼＋TOTP、Google／企業 SSO（OIDC）、passkeys；API 用短效 JWT；金流 webhook 用 HMAC 簽章
```

人物：
- **小晴**：剛入職的 junior 後端工程師，熟悉 Python 與 Flask，網路底層只有零碎概念。
- **阿德**：資深平台工程師，經歷過多次網路事故，小晴的 mentor。
- **Joe**：影音工程師，負責 WebRTC 與直播。
- **Rita**：資安工程師，負責驗證、授權與審查。
- 人物一律不用性別代名詞（他／她），用名字或「對方」。

## 7. 準確性重點

- TCP 三向交握 SYN → SYN-ACK → ACK；主動關閉的一方進入 TIME_WAIT（約 2×MSL）；被動關閉方若應用程式沒有 close，會卡在 CLOSE_WAIT。
- IPv4 header 最少 20 bytes，TCP header 最少 20 bytes，UDP header 8 bytes；Ethernet MTU 預設 1500，IPv6 最小 MTU 1280。
- DNS 傳統用 UDP 53，回應過大或 zone transfer 用 TCP；EDNS(0) 擴大 UDP 訊息。
- TLS 1.3 完整交握 1-RTT，resumption 可 0-RTT（0-RTT 資料可能被重放，只適合 idempotent 請求）。
- WebSocket 的 Sec-WebSocket-Accept = base64(SHA-1(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))；client 送往 server 的 frame 必須 mask。
- JWT 驗證必須固定允許的 alg、驗證簽章、exp／nbf、iss、aud；JWT 本身不加密（JWE 才加密）。
- OAuth 2.1 要求 authorization code 流程使用 PKCE，移除 implicit 與 resource owner password credentials。
- WebRTC 媒體一律加密（DTLS-SRTP）；signaling 不在 WebRTC 規格內。
- WSGI 規格是 PEP 3333；Werkzeug 的 debugger 允許執行任意程式碼，絕不能在 production 開啟。
- 不確定的數字或行為就不寫，或標明依實作／版本而定。

## 8. 禁止事項

- 禁止範本化套句與空泛句。
- 禁止中英文黏在一起。
- 禁止在正文放 URL。
- 禁止捏造數據、引言、產品功能、RFC 編號（不確定編號就只寫名稱）。
- 安全相關章節只談成因、偵測與防禦，不提供攻擊操作步驟或可直接使用的攻擊 payload。
- 禁止使用非包容性用語（master/slave、whitelist/blacklist、白名單／黑名單），改用 primary/replica、allowlist/denylist、允許清單／拒絕清單。
- 禁止對人物使用性別代名詞（她、他）；checker 會報錯（「其他」「他們」「他人」不受影響）。
