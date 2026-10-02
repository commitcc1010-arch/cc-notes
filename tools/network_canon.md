# 全書共用設定（canon）

撰寫任何章節時，以下設定必須和這裡一致。若你的章節需要新的全書共用設定，寫在完成回報裡，由主編加進本檔。

## 聲聲 Live 的網域與位址（範例用保留名稱）

- 對外網域：`shengsheng.example`；網站 `www.shengsheng.example`、API `api.shengsheng.example`、即時服務 `rt.shengsheng.example`、直播 `live.shengsheng.example`、TURN `turn.shengsheng.example`、登入 `auth.shengsheng.example`。
- 公網範例 IP：203.0.113.0/24（聲聲 Live 的 LB 與 edge）、198.51.100.0/24（使用者與第三方）、192.0.2.0/24（其他範例）。
- 內部網段：10.20.0.0/16（雲端 VPC）。

## 人物

小晴（junior 後端）、阿德（資深平台工程師、mentor）、Joe（影音工程師）、Rita（資安工程師）。一律不用性別代名詞。

## 規格引用方式（依 `tools/.network_survey.md`，2026-10 查證）

- 正文引用穩定、廣為人知的編號（TCP RFC 9293、HTTP 語意 RFC 9110、QUIC RFC 9000、WebSocket RFC 6455、JWT RFC 7519、PKCE RFC 7636、OAuth 2.0 RFC 6749）。
- 2025–2026 年才發布或仍在草案的規格（例如 survey 所列的 TLS 1.3 新版 RFC、ECH、PQ 混合金鑰交換、OAuth 2.1、6265bis、WHEP、SRT draft），編號與狀態只放在「2026 現況」區塊，並寫「依 2026 年 10 月查證」。
- SRT latency：libsrt 的 `SRTO_LATENCY` 單位是毫秒（預設 120 ms）；ffmpeg 的 srt URL 參數 `latency` 單位是微秒。提到時要註明單位。
- gunicorn 新版已內建 ASGI worker；不要寫「gunicorn 只能跑 WSGI」，改寫為「傳統上以 WSGI 為主，新版也支援 ASGI（見 2026 現況）」。

## 第 1 章定下的範例數值

- `www.shengsheng.example` 解析到 CDN edge `203.0.113.10`，TTL 300。
- 範例學生在家用 NAT 後：私有位址 `192.168.1.23`、閘道 `192.168.1.1`、對外位址 `198.51.100.23`。
- 範例老師「美咲」（日文老師），路徑 `/teachers/美咲`。
- 首頁的 Flask view 約 30 ms；美國學生的範例 RTT 180 ms。
- `api.shengsheng.example` 需要 CORS；靜態資源走 CDN；個人化首頁 `Cache-Control: private`。

## 位址分配表（避免各章衝突）

| 用途 | 位址 |
|---|---|
| `www` 的 CDN edge（`web.shengsheng.example`） | 203.0.113.10、.11；IPv6 `2001:db8:5::10` |
| 權威 DNS `ns1.shengsheng.example` | 203.0.113.53 |
| CDN 範例名稱 `ss.cdnedge.test` | 198.51.100.7、.8 |
| VPC 內 resolver | 10.20.0.2 |
| 直播 ingest `live.shengsheng.example`（SRT） | 203.0.113.25 |
| API 舊 IP（第 14 章搬遷事故前） | 203.0.113.20 |
| API 新 LB（搬遷後） | 203.0.113.80 |
| 即時服務 `rt` 的 LB | 203.0.113.40 |
| TURN `turn.shengsheng.example` | 203.0.113.50 |
| SFU | 203.0.113.60 |
| 攝影棚 LAN | 10.30.0.0/24（gateway .1、編碼器 .21、NAS .31），VLAN 10 |
| 辦公室網段 | 10.40.0.0/24，VLAN 20 |
| 雲端 VPC | 10.20.0.0/16 |
| 範例 MAC | `02:` 開頭的本地管理位址，例如 `02:00:00:00:00:21` |

## 其他共用數值

- 網路體檢探針服務（第 9 章）：UDP `10.20.3.21:9910`，訊息 `{seq, client_send_ms}`，逾時 1 秒算遺失。
- UDP 安全 payload 約 1200 bytes（對照 IPv4 乙太網路 1472、IPv6 最小 MTU 下 1232）。
- ephemeral port 範圍：Linux 32768–60999；macOS／Windows 49152–65535。
- 本書範例程式在 macOS 上執行並貼出輸出；平台差異（errno、socket 選項）要在文中註明 Linux 的不同。
- 品質回報協定（第 2 章）：SFU 節點 `10.20.1.15:50000` 每秒以 UDP 送 12 bytes 到 collector `10.20.3.7:5005`，格式 `!2sBBIHH`（magic "SL"、版本、旗標、uint32 序號、uint16 RTT ms、uint16 丟包千分比）。SFU 與 collector 在 10.20.0.0/20。
- ASN（第 6 章，文件用範圍 64496–64511）：聲聲 Live AS64500；transit T1 AS64497、T2 AS64499；學生 ISP A AS64496；虛構 ISP「海線電信」AS64498；誤宣告者 AS64510。聲聲 Live 機房網段 203.0.113.0/24，邊界路由器 203.0.113.1；向兩家 transit 購買頻寬並在 IXP peering。
- 小晴筆電（第 6 章）：192.0.2.50/24、gateway 192.0.2.1；VPN tun0 走 10.0.0.0/8 並推送 staging 子網 10.20.30.0/24；本機 Docker 網路 10.20.0.0/16 與 VPN／VPC 網段重疊（衝突範例，第 44 章可沿用）。
- VPC 子網配置（第 5 章）：每個 AZ 一塊 /18（a `10.20.0.0/18`、b `10.20.64.0/18`、c `10.20.128.0/18`、`10.20.192.0/18` 保留）；每塊依序 app /20、public /24、data /24（例如 app-a `10.20.0.0/20`、public-a `10.20.16.0/24`、data-a `10.20.17.0/24`）。辦公室 VPN `10.8.0.0/16`、staging VPC `10.21.0.0/16`、analytics VPC `10.22.0.0/16`。
- IPv6 前綴：站點 `2001:db8:5a5a::/48`、VPC `2001:db8:5a5a:100::/56`；API 範例 IPv6 `2001:db8:5a5a::443`（API IPv4 為新 LB 203.0.113.80）。
- 金流供應商 webhook 來源：`198.51.100.64/26`、`2001:db8:beef::/48`。
- 辦公室路由器 10.40.0.1；辦公室與 VPC 之間 WireGuard site-to-site，`wg0` MTU 1420，VPC 端 gateway 10.20.0.10；內部後台 `ops.shengsheng.example` = 10.20.3.17（只開內網；早期寫 10.20.3.15 的作廢）；VPC network ACL 為 stateless。
- Rita 的 ICMP 政策：放行 Type 3、11、12，echo 限速而非全擋；IPv6 依 RFC 4890。第 8 章已講 EDNS 1232 與 DNS Flag Day 2020。

## 衝突裁定（主編，審閱時依此修正）

- API／應用的 LB 一律是 **203.0.113.80**（`api.shengsheng.example`；`api-lb.shengsheng.example` 是其 CNAME 目標）；203.0.113.10／.11 只屬於 `www` 的 CDN edge。第 3 章寫成 .10 的要改。
- **學生家用路由器 WAN = 198.51.100.23**（第 1、7、13 章；家用內網 192.168.1.0/24、路由器 192.168.1.1、筆電 192.168.1.20 或 .23 皆可但同章一致）；第 3 章「某高中」的使用者改為 198.51.100.77；第 13 章手機 Wi-Fi 即家中 Wi-Fi，用 198.51.100.23（前面寫 .46 的那條作廢）。
- 主機：gunicorn app 主機 10.20.3.21（:8000；同一主機也跑第 9 章的探針 :9910）；內部後台 `ops` 10.20.3.17；**資料庫在 data 子網 10.20.17.15:5432**（第 3 章寫 10.20.3.15 的要改）；第 16 章的內部測試機改用 10.20.3.16。
- VPC resolver：10.20.0.2、10.20.0.3。
- Kubernetes：叢集網域 `cluster.local`、namespace `live`、kube-dns Service IP `10.96.0.10`；雲端內部 search domain `compute.internal.example`。
- 外部金流供應商 `pay.example.net`（198.51.100.20、2001:db8::20），webhook 來源 `198.51.100.64/26`。服務名稱：推薦 `reco`、聊天 `chat`。
- 回應 header 用 `x-request-id` 串接 nginx 與 Flask 的 log。
- 第 13 章學生手機：Wi-Fi 對外 198.51.100.23（家中）、4G 198.51.100.140；範例 connection ID `f067a5502a4262b5`、備用 `5b1e0c7d9a3f2e61`；第 13 章的「主要 LB 203.0.113.10:443」應改為 `www` 的 CDN edge 或 API LB 203.0.113.80（依情境）。
- 0-RTT 規則：只放行 GET／HEAD，其他請求回 425 Too Early（第 13、18、22 章一致）。
- WebSocket 多半仍走 TCP，不受 QUIC migration 保護（第 13、32、33 章一致）。
- Linux delayed ACK 最小約 40 ms（第 11、12、20、43 章口徑一致）；課堂錄製服務在 VPC 內，範例 TCP 連線 `10.20.1.5:8000` ↔ `10.20.3.7:51514`。
- 電信 CGNAT（第 7 章）：內部 100.72.18.9、出口 198.51.100.200；範例 STUN server 192.0.2.1:3478（正式的 TURN／STUN 是 `turn.shengsheng.example` 203.0.113.50）；打洞範例另一端 NAT 公網用 198.51.100.201（第 7 章寫 203.0.113.200 的要改）。
- 第 10 章：內部課表服務 `10.20.3.15:8080`（閒置 60 秒主動關閉）；**內部後台 ops 改為 10.20.3.17**（第 8 章寫 10.20.3.15 的要改）；教室入口 API 主機改為 **10.20.1.25**（gunicorn :8000，backlog 2048；第 10 章寫 10.20.1.15 的要改，10.20.1.15 保留給第 2 章的 SFU 節點）；第三方推播閘道 198.51.100.50:443。
- TCP 狀態名稱：正文用底線寫法（SYN_RECV、FIN_WAIT_1、TIME_WAIT），引用 ss 或規格原文時才用連字號。
- 「CLOSE_WAIT 連線池事故」（第 10 章）可在第 43、45 章引用。
- 路徑 RTT 示意值（第 1、12 章）：台北 → 東京 edge 約 35 ms、台北 → 美西約 150 ms、台北 → 美東（第 1 章的美國學生）約 180 ms、台北 → 歐洲約 250 ms。老師家上傳線路 20 Mbps、基本 RTT 40 ms。MSS 預設以 1448 bytes 計算（含 timestamp 選項）。回放下載的 origin 屬於 CDN 後方的 origin，用 203.0.113.70（第 12 章寫 203.0.113.10 的要改）。
- 金流 webhook（第 17 章定義，第 30 章沿用）：header `Pay-Signature: t=<unix 秒>,v1=<hex>`，HMAC-SHA256 計算 `"{t}." + 原始 body`，容許 300 秒；端點 `api.shengsheng.example/v1/webhooks/pay`；事件 id 形如 `evt_8812`、訂單 `A1024`、金額 1200；金鑰 k2（現行）、k1（輪替中）。驗證一律用原始 body（Flask 的 `request.get_data()`）。
- 範例學生帳號 `student-0457`、課程編號 8812。
- Cookie（第 21 章）：session `__Host-sid`（`Path=/; Secure; HttpOnly; SameSite=Lax`，不設 Domain）；語言偏好 `lang`（`Domain=shengsheng.example`，Max-Age 一年）。範例學生「小安」（sid=A）、「阿哲」（sid=B）。
- 快取策略（第 21 章）：匿名首頁 `public, max-age=0, s-maxage=60, stale-while-revalidate=30`；個人化頁面 `private, max-age=0`；帶 hash 的靜態檔（例如 `app.3f9c.js`）`public, max-age=31536000, immutable`；CDN 對帶登入 cookie 的請求 bypass。首頁快取事故發生在 21:58、十二分鐘內止血（第 25 章談 purge 時沿用）。錄影檔 `/recordings/lesson-0815.*` 由 nginx 直接服務並支援 Range。
- 帳號與登入政策（第 26 章）：範例帳號 `student23`、`student77`（學生）、`teacher05`（老師）；範例密碼 `Kyoto-Matcha-2026`；範例攻擊來源 192.0.2.100–.202。session 閒置逾時 30 分鐘、絕對逾時 12 小時，敏感操作超過 10 分鐘要重新驗證；重設 token 有效 30 分鐘；限速：(帳號, IP) 5 次後每 5 分鐘補 1 次、IP 每小時約 60 次、帳號每小時約 20 次失敗後改為要求額外驗證。撞庫事故：約 2,700 個 IP、21 萬次嘗試、186 個帳號被登入（第 27–30 章可沿用）。
- 第 20 章：合成監測主機 10.20.3.30；範例 idempotency key `7f3c-b2`、預約 ID 從 1001 起；nginx `keepalive_timeout` 75 秒、gunicorn keep-alive 2 秒（第 43 章 timeout 鏈沿用）；未知 Host 由 nginx `default_server` 的 `return 444` 擋下。
- 憑證（第 19 章）：`auth` 與 `api` 共用 API LB 203.0.113.80，依 SNI 選憑證；`auth` 原本是手動匯入的 OV 憑證（2026-03-16 簽發、2026-10-01 00:00 UTC 到期，199 天），事故後改為 LB 受管憑證。`rt.shengsheng.example`：L4 LB 203.0.113.40 不解密，TLS 終結在三台 nginx 10.20.2.11、.12、.13，事故後改用 DNS-01 集中申請分發。`www` 用 CDN 受管憑證（90 天）。HSTS：`shengsheng.example` 設 `max-age=31536000; includeSubDomains; preload`（內部後台 `ops` 受 includeSubDomains 影響）。
- OIDC／SSO（第 29 章）：企業客戶「北辰物流」，IdP `login.beichen.example`；聲聲 Live 的 client_id `shengsheng-live`、北辰報帳系統 `beichen-expense`；範例員工 `sub` `e-20931`、email `mei.lin@beichen.example`。OIDC callback `auth.shengsheng.example/callback`；passkey RP ID `shengsheng.example`；釣魚網站 `shengsheng-login.example`、仿冒 IdP `login.beichen-sso.example`；JWKS kid 依第 27 章（ES256 `es-2026-09`、`es-2026-10`）。access token 依第 27 章為 5 分鐘（第 29 章寫 10 分鐘的要改）。RP session 沿用第 26 章：閒置 30 分鐘、絕對 12 小時（第 29 章寫閒置 2 小時的要改）。
- 第 22 章：舊 domain sharding 圖片網域 `img1`／`img2.shengsheng.example`（CNAME 到 `ss.cdnedge.test`，獨立憑證），改版後收回 `www.shengsheng.example/avatars/`，舊網址 301。「找老師」頁 `/teachers`：80 張大頭照（各約 6 KB）、`app.css` 40 KB、`app.js` 120 KB、HTML 30 KB。0-RTT 經 CDN 轉給 origin 時帶 `Early-Data: 1`，後端據此回 425。
- JWT（第 27 章）：issuer `https://auth.shengsheng.example`；audience `api.shengsheng.example`、`rt.shengsheng.example`；access token `typ: at+jwt`、ES256、有效 5 分鐘（政策上限 15 分鐘）、時鐘容許 60 秒；refresh token 14 天、opaque、雜湊儲存、每次使用即輪替；教學用 HS256 kid `k2026-09`／`k2026-10`。Web 前端（BFF）沿用 session cookie `__Host-sid`（第 27 章寫 `__Host-ss_sid` 的要改）；App 用 Bearer header。範例老師 `teacher:1024`、課程 7781、`PUT /v1/classes/7781/schedule`。401（缺少或無效 token，帶 `WWW-Authenticate`）／403（`insufficient_scope`）。
- Proxy／LB（第 25 章）：nginx 10.20.3.11；app-a 10.20.3.21:8000、app-b 10.20.3.22:8000；API LB 在 VPC 內的位址 10.20.16.5（public-a）；CDN 回源出口網段 198.51.100.224/27（範例出口 .230）；繞過 CDN 的攻擊者範例 198.51.100.99、偽造 XFF 值 192.0.2.66。信任清單 = 10.20.0.0/16 ＋ CDN 回源網段；面對 internet 的那一層覆寫 XFF、內部各層附加、後端從右往左解析並跳過可信網段（第 43 章 ProxyFix 沿用）。LB health check `/readyz`：interval 5 秒、timeout 2 秒、fall 2、rise 3。
- OAuth（第 28 章）：合作 App「詞卡島」`cards.example.net`（198.51.100.120），`client_id` `cards`，callback `/oauth/callback`；範例學生內部 ID `stu_1024`（第 28 章寫 `stu-1024` 的要改）（登入帳號為第 26 章的 `student23` 等）；對外 scope `vocab:read`、`vocab:write`、`schedule:read`、`profile:read`（付款與帳號設定不開放）。授權碼 60 秒、一次性；給第三方的 access token 為 opaque、10 分鐘（自家 API 的 JWT 仍是第 27 章的 5 分鐘）；`reco` 走 client credentials、scope `lessons:read`、token 300 秒；老師後台 SPA 採 BFF。
- API 風格（第 24 章）：ID 一律用「前綴_編號」：學生 `stu_1024`、課程 `les_004`、付款 `pay_0001`、事件 `evt_8812`；老師 `t_misaki`（美咲，日語）、`t_minjun`（敏俊，韓語）。`reco` gRPC 位址 `10.20.4.12:50051`，package `shengsheng.reco.v1`（`GetRecommendations`、`WatchAudience`）。付款 `POST /v1/payments` 必帶 `Idempotency-Key`，綁定 `(student_id, key)`、保存 24 小時，重播加 `Idempotent-Replayed: true`，處理中 409、同 key 不同內容 422。錯誤格式 `application/problem+json`，`type` 前綴 `https://api.shengsheng.example/problems/<slug>`。內部用 `x-deadline-ms` 傳遞 deadline。優惠包 NT$12,000；課程頁 API 預算 800 ms。金流 webhook 路徑統一為 `/v1/webhooks/pay`（第 17 章寫 `/webhooks/pay` 的要改）。
- 瀏覽器安全（第 23 章）：老師後台 `teach.shengsheng.example`；行銷子網域 `promo.shengsheng.example`；外部範例 `phish.example`、`partner.example`（iframe 嵌入白板）、`mail.example`、`pages.example`。API CORS 允許清單為 `www` 與 `teach`，preflight `Max-Age: 600`，允許 `authorization`、`content-type`、`x-csrf-token`，`Access-Control-Expose-Headers: x-request-id`。Cookie：`__Host-sid`、`__Host-refresh`（Secure、HttpOnly、SameSite=Lax、14 天）、`__Host-csrf`。Endpoint：`/v1/bookings`、`/v1/session/refresh`、`/v1/me`、`/v1/courses`（公開、可快取）。教室頁 CSP：`script-src 'nonce-…' 'strict-dynamic'; object-src 'none'; base-uri 'none'; frame-ancestors 'self' <partner>`；登入與付款頁 `frame-ancestors 'none'`。
- 即時（第 31 章）：等候室舊 polling API `GET /api/rooms/7/status`；SSE 端點 `rt.shengsheng.example/rooms/7/events`；晚上八點全站約 6,000 名學生在等候室；SSE 心跳 15 秒、`retry: 3000`；補不回來時送 `event: reset`，前端改打 `/api/rooms/7/state`。即時服務的 uvicorn 在擴充前單機（10.20.1.40）綁 `0.0.0.0:8001`，所以在主機上用 `127.0.0.1:8001` 測試、nginx 從其他主機連 `10.20.1.40:8001` 都成立；擴充後（第 33 章）改經本機 nginx :8080 與 Unix socket（gunicorn 為 :8000）。「部署時重連驚群」與「共用事件紀錄才能跨實例補發」為第 31–33 章共同口徑。
- TLS（第 18 章）：測試 PKI（內嵌於第 18 章程式，只供練習）："Shengsheng Internal CA"、`ops` server 憑證 serial 0x1801、client 憑證 CN `xiaoqing-laptop`；公開 CA 鏈範例 "Example Root CA R1" → "Example Issuing CA 2"；`api` 範例憑證效期 2026-07-01 至 2026-12-28（180 天）。0-RTT 標記 `Early-Data: 1` 由 CDN 設定、入口清掉 client 自帶的同名 header。`ops` 採 mTLS＋SSO，client 憑證由 MDM 安裝。金鑰排程的 secret 名稱用「Main Secret」等寫法（包容性用語）。
- Service 驗證（第 30 章）：API key 格式 `ssk_<live|test>_<8 hex key id>_<43 字元 base62 secret><6 字元 checksum>`，DB 存 HMAC-SHA256(pepper, key)；範例 owner `school_hsinchu`、scope `courses:read`。內部 HMAC 簽章 `Authorization: SS-HMAC-SHA256 keyId=api-2026q4,ts=…,nonce=…,signedHeaders=…,signature=…`（±300 秒），目標 `reco.live.svc.cluster.local`。服務身分 `spiffe://shengsheng.example/ns/live/sa/api`；Pod IAM role `live-api-recordings`。金流 webhook 部署 3 台 × 4 個 gunicorn worker；去重表 `webhook_events(event_id PRIMARY KEY)` 在 DB 10.20.17.15、與入帳同交易；開賣夜重複加點事故 21:02–21:41、37 人。
- WebSocket（第 32 章）：即時服務 uvicorn 節點 10.20.1.40（綁 :8001），前面是 rt 的 nginx 10.20.2.11–.13 與 L4 LB 203.0.113.40。心跳：server 每 25 秒 ping、20 秒內沒 pong 即關閉；`/ws/` 的 nginx `proxy_read_timeout` 75 秒；LB idle timeout 120 秒。訊息上限：聊天 64 KiB、白板 1 MiB，大型資料走 HTTP 上傳、WebSocket 只送參照。Origin 允許清單 `https://www.shengsheng.example`（老師後台 `https://teach.shengsheng.example` 亦可）；`POST /rt/tickets` 簽發一次性 ticket（30 秒、只存 SHA-256、綁 user／room／origin）；連線授權 15 分鐘到期以 close code 4001 關閉、前端換票重連。subprotocol `ss-chat.v1`／`v2`／`v3`；範例教室 8812（與第 17 章課程編號相同），學生 ID 用 `stu_1024`（第 32 章寫 `student-1024` 的要改）。
- SDP／SFU（第 35 章）：SFU 為 ICE-lite，candidate `203.0.113.60:40000`（udp、host），DTLS `setup:passive`，ICE ufrag `Sf60`；學生端媒體位址範例 `198.51.100.23:54012`；SDP 識別字：學生 stream id `cam-0457`、SFU 轉送老師的 msid `teacher-1024`（老師帳號仍是 `teacher05`／ID `t_misaki`）、SSRC 從 30000 起、cname `sfu-60`。教室一律由學生端發 offer、SFU 只當 answerer；新參與者加入時 SFU 經 signaling 通知、學生端加 `recvonly` transceiver 後重新 offer。第 35 章事故（寫死 PT 98 的 munging，SFU 以 `no_primary_codec` 拒絕）可在第 39、45 章引用。
- 影音（第 34 章）：SFU 203.0.113.60（`sfu-tpe-1`，位於台北區域；第 34 章寫「東京」的要改）（內部節點 10.20.1.15，媒體 UDP 50000）；美咲老師在日本授課；學生小安以 4G 上課（對外 198.51.100.140）；抓包檔 `class-8812.pcap`；美咲的音訊 SSRC `0x5EED0034`（Opus，PT 111）、視訊 SSRC `0x1A2B3C4D`（H.264，PT 96）。「低延遲模式」事故：App 把音訊 jitter buffer 上限壓到 20 ms，儀表板丟包 0.3%、RTT 70 ms，但補洞樣本約 11%；修正為改回自適應、只調低下限（第 37、39 章沿用）。延遲預算：固定部分約 120 ms＋jitter buffer。
- **SFU 媒體埠裁定**：所有參與者共用 SFU 的 **UDP 40000**（依第 35 章 SDP 的 candidate `203.0.113.60:40000`）。第 2 章的 `10.20.1.15:50000` 是品質回報的來源 port，不是媒體埠；第 34 章寫「媒體 UDP 50000」、第 37 章寫「媒體 UDP 10000」的要改成 40000。
- SFU 叢集（第 37 章）：sfu-tpe-1 公網 203.0.113.60／VPC 10.20.1.15，後續節點 203.0.113.61 起、10.20.1.16–.20，共規劃 6 台；ICE-lite、不放在 L4 LB 後面；管理介面 `10.20.1.15:7070`（只開 VPC 內）。simulcast 三層 720p 1,500 kbps、360p 500 kbps、180p 150 kbps，Opus 約 40 kbps。尖峰：2,000 間一對一＋300 間六人小班，SFU 收約 10.1 Gbps、送約 10.4 Gbps；尖峰約 8% 參與者需要 TURN；單台 SFU 安全上限 3 Gbps（假設）。
- TURN（第 37 章）：203.0.113.50 提供 UDP／TCP 3478 與 TLS 443，與 SFU 同區；`allowed-peer-ip` 只放行 10.20.1.15–.20；短效帳密 `到期時間:使用者ID`、TTL 1 小時。錄製服務 10.20.1.5，以隱形參與者訂閱教室串流。學生「小芸」用宿舍 Wi-Fi；阿哲在高鐵上用 4G。
- ASGI（第 42 章）：即時服務的 uvicorn 跑在第 33 章的 gateway 上（第 42 章寫 10.20.2.21／.22 的要改成 gw-41 10.20.1.41、gw-42 10.20.1.42；第 32 章的 10.20.1.40 是擴充前的單機，保留）；app-a、app-b 的 gunicorn sync workers 每台 9 個、共 18 個。教室 WebSocket 路徑 `/ws/classroom/{course_id}`；subprotocol 統一用第 32 章的 `ss-chat.v1`（第 42 章寫 `chat.v1` 的要改）。內容審核呼叫約 80 ms；講座尖峰約每秒 30 則訊息；「loop lag」列入 SRE 監控清單。
- presence 服務（第 40 章）：10.20.3.41:8090；學生每 15 秒 `POST /presence` 心跳；彩排模擬 2,000 名學生＋Rita 的 3,000 條慢速連線；fd 上限 4,096；第一版 `HTTPServer`（iterative、backlog 5）、第二版 `ThreadingHTTPServer`，結論是放在 nginx 後面並改用 asyncio 模型（第 42、43 章沿用）。
- 影音除錯（第 39 章）：美咲家對外 198.51.100.201（restricted cone NAT，即第 7 章打洞範例的另一端）、筆電 192.168.0.31（第 39 章寫 .36／192.168.0.12 的要改），到台北 SFU 基本 RTT 40 ms（第 37 章寫 10 ms 的要改）。北辰物流辦公室出口 198.51.100.180（只放行 TCP 443），員工小林筆電 172.16.20.44。TURN 三種傳輸：UDP 3478、TCP 3478、TLS 443；範例 relay 位址 203.0.113.50:49172。教室頁每 5 秒把精簡 getStats 經教室 WebSocket 送回 collector。課程 8812 卡頓事件：手機雲端備份 20:10–20:18、虛擬背景 CPU 不足 20:20–20:31、TURN over TLS 遇辦公室壅塞 20:15–20:25。SFU 媒體埠依裁定為 UDP 40000（第 39 章寫 10000 的要改）。
- 即時 gateway（第 33 章，裁定版）：擴充前單機 10.20.1.40；擴充後 gw-41–43 = 10.20.1.41–.43（AZ a）、gw-44–46 = 10.20.65.44–.46（AZ b），每台 nginx :8080 經 Unix socket 接 uvicorn；前方是 rt 的 TLS 終結 nginx 10.20.2.11–.13 與 L4 LB 203.0.113.40。Redis（broker 與房間狀態）primary 10.20.17.21:6379、replica 10.20.81.21。心跳 25 秒、presence TTL 60 秒、正常關閉後寬限 8 秒；自訂 close code 4008＝client 太慢（4001＝授權到期）。房間 topic `room:<id>`，envelope 帶每房間序號。容量：6 台 gateway 共 69,000 連線、每台 11,500。
- 部署（第 43 章）：修正後 timeout 鏈：瀏覽器 90 s ＞ CDN 回源 75 s ＞ LB idle 60 s ＞ nginx `proxy_read_timeout` 35 s ＞ gunicorn timeout 30 s ＞ app 請求預算 10 s ＞ PostgreSQL `statement_timeout` 5 s。keep-alive：server 端 75 s、client 端 60 s 以下（gunicorn `keepalive` 由 2 s 改為 75 s、nginx upstream `keepalive_timeout` 60 s、uvicorn `--timeout-keep-alive` 75 s）。API 主機 8 vCPU、gthread 8 workers × 7 threads、`graceful_timeout` 25 s、systemd `TimeoutStopSec` 40 s；PostgreSQL `max_connections` 100。nginx 以 realip 解析後用單一值覆寫 XFF，Flask `ProxyFix(x_for=1, x_proto=1)`，gunicorn `forwarded_allow_ips = "10.20.3.11"`。錄影檔走 `X-Accel-Redirect` 到 `/internal/recordings/`。第 43 章寫 rt uvicorn 在 10.20.2.21／.22 的要依第 33 章裁定改為 gw-41／gw-42（10.20.1.41／.42）。
- 直播（第 38 章）：`live.shengsheng.example`（203.0.113.25）是直播媒體伺服器（SRT ingest UDP 9000、WHIP `/whip/talk-1017`、WHEP `/whep/talk-1017`）；**觀眾看的 LL-HLS 走 CDN 的 `watch.shengsheng.example`**（第 1 章若把 `live` 寫成觀看網址的要改）。SRT latency：攝影棚 120 ms、遠端講者 500 ms（依 RTT 設定），RTMPS 為備援。講座 `talk-1017`，stream ID `#!::r=live/talk-1017,m=publish`。碼率階梯 1080p 4.5 Mbps、720p 2.5 Mbps、480p 1.2 Mbps、360p 0.7 Mbps、音訊 128 kbps。LL-HLS：segment 2 秒、part 0.5 秒、PART-HOLD-BACK 1.5 秒、GOP 1 秒。九月講座 2026-09-19（美咲在京都飯店）；改版後講座 2026-10-17 19:30。
- ICE（第 36 章）：某高中 198.51.100.77，內網 172.16.8.0/24，擋所有 UDP、只放行 TCP 80／443。TURN relay port 49152–65535（範例：學生 :49152、老師 :49154）。ICE 範例值：學生 ufrag `s7Kq`、pwd `aV3b9XkLmP0qRsT2uVwXyZ`，老師 ufrag `m1Sk`；host port 54400、srflx :50000、symmetric NAT 新配的 port :50007。TURN 短效帳密 username「到期時間:<使用者>」、TTL 1 小時，由 `/v1/lessons/{id}/ice-servers` 簽發。一對一課早期 P2P 優先（走 TURN 比例假設 15%），之後改走 SFU（第 37 章）。
- WSGI（第 41 章）：老師月報匯出 `/teachers/reports/<YYYY-MM>.csv` 以串流＋`call_on_close` 歸還連線，報表服務用 gunicorn gthread worker；報表服務（整個服務）的資料庫連線池共 40 條（不是每 worker）；第 41 章的 nginx `proxy_read_timeout 30s` 是第 43 章修正前的狀態（修正後 35 s）。staging 誤開 debugger 事故：主機 10.21.3.21:5000，辦公室 VPN 10.8.0.0/16 連得到。範例 request id `7f3c9a2e`；middleware 放進 environ 的自訂鍵用 `shengsheng.` 前綴。
- 除錯（第 45 章）：API LB 閒置逾時 60 秒，必須短於 nginx `keepalive_timeout` 75 秒（與第 43 章 keep-alive 規則一致）。「故障演練日」八場事故對照見第 45 章 45.1（第 46 章可沿用）。ISP resolver 範例 198.51.100.53（第 15 章）。rt 的 10.20.2.13 舊憑證到期日 2026-10-10。
- 明年擴充（第 46 章）：尖峰 60,000 人在線，4,000 間一對一＋600 間小班（11,600 人在視訊），6,000 位 LL-HLS 觀眾；規模為 14 台 app 主機（110 workers）、6 台即時 gateway、9 台 SFU（203.0.113.60–.68、VPC 10.20.1.15–.23，TURN `allowed-peer-ip` 同步放寬）、3 台 TURN（203.0.113.50–.52；.53 是 ns1）。LL-HLS 媒體 origin 與錄影回放共用 203.0.113.70。模型假設：美東學生到鄰近 edge 約 15 ms、edge 到 origin 約 170 ms。第 33 章「9,000 間教室」與第 37 章「2,000 間一對一＋300 間小班」口徑不同：第 33 章的教室數是含聊天的所有房間（含課後討論與講座），審閱時要在第 33 章明確說明口徑。
- 其他已分配的範例位址：198.51.100.150（第 9 章五元組範例中的老師）、198.51.100.88（第 12 章德國學生）、198.51.100.60（第 14 章 `ns.cdnedge.test`）。
- 雲端與 K8s（第 44 章）：Pod CIDR 10.244.0.0/16（每節點一個 /24：node-a1 .1、a2 .2、b1 .3、b2 .4、c1 .5、c2 .6）；節點 IP node-a1/a2 10.20.5.11/.12、node-b1/b2 10.20.69.11/.12、node-c1/c2 10.20.133.11/.12；Service CIDR 10.96.0.0/12（kube-dns 10.96.0.10、reco ClusterIP 10.96.40.12:50051）；VXLAN UDP 4789、VNI 4096、Pod MTU 1450；Gateway API 內部 LB 10.20.6.80（HTTP 80，TLS 已在 203.0.113.80 終結）。NAT gateway：nat-a 10.20.16.10／203.0.113.90、nat-b 203.0.113.91、nat-c 10.20.144.10／203.0.113.92（三個 EIP 登記到金流供應商允許清單）。private zone `internal.shengsheng.example`；PrivateLink endpoint 範例 10.20.9.44。
- **SFU 網路介面裁定**：SFU 的 VPC 位址 10.20.1.15 是 app 子網的管理／內部介面；媒體走位於 public 子網、綁公網 203.0.113.60 的另一張網路介面，主機用 policy routing 讓回應從同一張介面出去（第 44 章定義，第 34、37 章引用時一致）。
- 第 1–7 章審閱後新增：辦公室 IPv6 前綴 `2001:db8:5a5a:10::/64`；辦公室工作站 10.40.0.15；某高中教室電腦 172.16.8.23、內網閘道 172.16.8.1（以 198.51.100.77 做 NAT）。VPC 規劃練習網段 10.24.0.0/18。
- 第 15 章：`www` 由舊 CDN `ss.cdnedge.test`（198.51.100.7、.8）換到新 CDN `ss.newedge.test`（edge 203.0.113.10、.11），`www` 的 CNAME TTL 86400；內部 view 的 `api` 是 VPC 內 LB 10.20.16.5；`live` 只有 A record（無 AAAA）。
