# 附錄 D　Port 與 Status Code 速查

> [!abstract] 本附錄地圖
> **用途**：值班或讀 log 時，手上只有一個數字或一行錯誤訊息：一個 port、一個 HTTP status code、一個 WebSocket close code、一個 DNS rcode、一個 TLS alert、一個 ICE 錯誤或一個 errno。這份速查告訴你那個數字是什麼意思、通常是**哪一層**產生的、下一步該看哪裡，以及正文哪一章講過它。
>
> **怎麼查**：
> - 先依數字的種類找到小節：port 看 D.1–D.3；HTTP 看 D.4–D.7；WebSocket 看 D.8；DNS 看 D.9；TLS 看 D.10；WebRTC 看 D.11；errno 與 Python 例外看 D.12；只有一行錯誤訊息、不知道屬於哪一類時，從 D.13 的總表開始。
> - 每張表的「誰產生」一欄比「意義」一欄更重要：同一個 502，nginx 產生和 LB 產生的調查方向完全不同（第 20、25、43 章）。
> - 聲聲 Live 的位址與設定值一律沿用正文（全書共用設定），範例中的數字可以直接拿去對照正文的事故。
> - 標示「依實作而定」或「截至 2026 年 10 月」的內容，以你手上版本的文件為準。

## D.1 Port 號的範圍與規則

port 是 16 bit 的整數（0–65535），寫在 TCP 與 UDP header 的前 4 bytes（第 9 章）。同一個號碼在 TCP 與 UDP 是兩個獨立的空間：UDP 443 的 HTTP/3 和 TCP 443 的 HTTPS 互不干擾，防火牆規則也要分開寫。

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────────────────────┬───────────────────────────────┐
 │       Source Port（16）        │     Destination Port（16）     │  ← TCP 與 UDP 都從這 4 bytes 開始
 └───────────────────────────────┴───────────────────────────────┘
  一條連線＝（協定, 來源 IP, 來源 port, 目的 IP, 目的 port）五元組
  例：TCP 198.51.100.23:51514 → 203.0.113.80:443
```

server 端 listen 在固定的 port，client 端的來源 port 通常由作業系統從 **ephemeral port**（臨時 port）範圍挑一個。下表的範圍值與正文一致；「短連線太多、`EADDRNOTAVAIL`」這類問題就是 ephemeral 範圍被 TIME_WAIT 佔滿（第 10 章）。

| 範圍 | 名稱 | 說明 |
|---|---|---|
| 0 | 保留 | `bind(("", 0))` 代表「讓 OS 挑一個空的 port」，不是真的用 port 0 |
| 1–1023 | well-known（系統 port） | 由 IANA 分配給標準服務；Linux 預設要 root 或 `CAP_NET_BIND_SERVICE` 才能 bind（可用 `net.ipv4.ip_unprivileged_port_start` 調整） |
| 1024–49151 | registered（登記 port） | 向 IANA 登記的應用程式，例如 STUN／TURN 3478、PostgreSQL 5432 |
| 49152–65535 | dynamic／private | IANA 建議的 ephemeral 範圍 |
| 32768–60999 | Linux 預設 ephemeral | `sysctl net.ipv4.ip_local_port_range` 查看與調整 |
| 49152–65535 | macOS、Windows 預設 ephemeral | macOS 用 `sysctl net.inet.ip.portrange.first`／`last`；Windows 用 `netsh int ipv4 show dynamicport tcp` |
| 30000–32767 | Kubernetes NodePort 預設範圍 | 每個節點都開同一個 port（第 44 章） |
| 49152–65535 | 常見 TURN relay 範圍 | 聲聲 Live 的 TURN 從這段配 relay port（第 36 章） |

兩個容易誤會的地方。第一，Linux 的 ephemeral 範圍和 NodePort 範圍不重疊，但和 IANA 的 dynamic 範圍部分重疊；自己挑「冷門 port」給服務 listen 時，避開 32768 以上，免得和 client 的來源 port 撞在一起。第二，port 號只是慣例，不是保證：任何服務都可以 listen 在任何 port 上，防火牆看到 TCP 443 也不代表裡面一定是 HTTPS。

## D.2 常見 port：依用途分組

下列各表的「傳輸」欄寫 TCP、UDP 或兩者。標「本書」的是聲聲 Live 的設定，不是業界標準。

### 基礎設施與維運

| Port | 傳輸 | 服務 | 備註 |
|---|---|---|---|
| 22 | TCP | SSH | 只對管理網段開放；雲端改用 session manager 類服務可完全不開 |
| 67／68 | UDP | DHCP（server／client） | 只在同一個廣播網域內，跨網段要 relay |
| 123 | UDP | NTP | 時鐘錯會讓憑證「尚未生效」或 JWT 的 exp 判斷錯誤（第 19、27 章） |
| 161／162 | UDP | SNMP（查詢／trap） | 網路設備監控 |
| 179 | TCP | BGP | 路由器之間的 session（第 6 章） |
| 389／636 | TCP | LDAP／LDAPS | 企業目錄服務 |
| 88 | TCP、UDP | Kerberos | 企業網域登入 |
| 514 | UDP（或 TCP） | syslog | 加密版常見 TCP 6514 |
| 500／4500 | UDP | IPsec IKE／NAT-T | site-to-site VPN |
| 51820 | UDP | WireGuard 常用 port | 本書辦公室到 VPC 的 `wg0`（第 8 章） |
| 1194 | UDP（或 TCP） | OpenVPN 預設 | |
| 80 | TCP | 雲端 instance metadata（169.254.169.254） | link-local 位址；SSRF 防禦的重點目標 |

### Web 與應用程式

| Port | 傳輸 | 服務 | 備註 |
|---|---|---|---|
| 80 | TCP | HTTP | 對外只做 301 轉 HTTPS 與 ACME HTTP-01 驗證（第 19 章） |
| 443 | TCP | HTTPS（HTTP/1.1、HTTP/2） | ALPN 決定 h2 或 http/1.1（第 18、22 章） |
| 443 | UDP | HTTP/3（QUIC） | 企業網路擋 UDP 時瀏覽器退回 TCP（第 13、22 章） |
| 8080、8443 | TCP | 慣例的替代 HTTP／HTTPS port | 本書即時 gateway 的 nginx 用 :8080（第 33 章）、內部課表服務用 :8080（第 10 章） |
| 8000 | TCP | gunicorn 常見綁定 | 本書 app 主機 10.20.3.21:8000（第 41、43 章） |
| 8001 | TCP | 本書 uvicorn | 即時服務綁 `127.0.0.1:8001`（第 31、42 章） |
| 5000 | TCP | `flask run` 開發伺服器預設 | 第 41 章 staging 誤開 debugger 的事故就在 :5000 |
| 3000、5173 | TCP | 常見前端開發伺服器 | 依工具而定，只在本機使用 |
| 50051 | TCP | gRPC 範例慣用 port | 本書 `reco` 在 10.20.4.12:50051（第 24 章） |
| 9090、9100 | TCP | Prometheus、node exporter 預設 | 只開內網 |

### DNS

| Port | 傳輸 | 服務 | 備註 |
|---|---|---|---|
| 53 | UDP | 一般 DNS 查詢 | EDNS(0) 讓 UDP 訊息超過 512 bytes；建議上限 1232（第 8、15 章） |
| 53 | TCP | 截斷（TC=1）後重試、zone transfer、大型回應 | 防火牆只開 UDP 53 會讓大回應失敗（第 14、15 章） |
| 853 | TCP | DoT（DNS over TLS） | 專用 port，網管看得出是加密 DNS（第 15 章） |
| 853 | UDP | DoQ（DNS over QUIC） | |
| 443 | TCP、UDP | DoH（DNS over HTTPS） | 和一般 HTTPS 混在一起（第 15 章） |
| 5353 | UDP | mDNS | 區網內的 `.local` 名稱；WebRTC 用它隱藏 host candidate 的內網位址（第 36 章） |
| 5355 | UDP | LLMNR | Windows 區網名稱解析 |

### 郵件

| Port | 傳輸 | 服務 | 備註 |
|---|---|---|---|
| 25 | TCP | SMTP（伺服器之間） | 很多雲端與 ISP 預設封鎖對外 25 |
| 587 | TCP | Submission（STARTTLS） | 應用程式寄信用這個或 465 |
| 465 | TCP | Submission over TLS（implicit TLS） | |
| 143／993 | TCP | IMAP／IMAPS | |
| 110／995 | TCP | POP3／POP3S | |

### 資料庫與中介軟體

| Port | 傳輸 | 服務 | 備註 |
|---|---|---|---|
| 5432 | TCP | PostgreSQL | 本書 DB 在 data 子網 10.20.17.15:5432 |
| 3306 | TCP | MySQL／MariaDB | |
| 1433 | TCP | SQL Server | |
| 1521 | TCP | Oracle | |
| 6379 | TCP | Redis | 本書 broker primary 10.20.17.21:6379（第 33 章） |
| 11211 | TCP | memcached | 不要對外開放 UDP 11211 |
| 27017 | TCP | MongoDB | |
| 9092 | TCP | Kafka | |
| 2181 | TCP | ZooKeeper | |
| 9200 | TCP | Elasticsearch／OpenSearch HTTP | |

資料庫 port 有一條共同規則：**只開給 app 子網**。security group 寫「來源是 app 子網或 app 的 SG」，而不是 0.0.0.0/0；連線數上限（例如 PostgreSQL `max_connections` 100，第 43 章）也是要一起規劃的資源。

### 影音與即時

| Port | 傳輸 | 服務 | 備註 |
|---|---|---|---|
| 3478 | UDP、TCP | STUN、TURN | 本書 TURN `turn.shengsheng.example`（203.0.113.50）同時開 UDP 與 TCP（第 36、37 章） |
| 5349 | TCP | TURN over TLS 的標準 port（TURNS） | 很多網路只放行 443，所以實務上常把 TLS 版放在 443 |
| 443 | TCP | TURN over TLS（本書） | 只放行 TCP 80／443 的學校與企業靠它連線（第 36、39 章） |
| 49152–65535 | UDP | TURN relay 位址範圍 | coturn 預設；例如 relay 203.0.113.50:49172（第 39 章） |
| 40000 | UDP | 本書 SFU 媒體埠 | 所有參與者共用 203.0.113.60:40000，ICE-lite 加 BUNDLE 多工（第 35、37 章） |
| 隨機 | UDP | 瀏覽器的 host candidate | 從 OS 的 ephemeral 範圍挑；部分瀏覽器可用企業政策限制範圍 |
| 1935 | TCP | RTMP | 推流老協定（第 38 章） |
| 443 | TCP | RTMPS | 部分平台只接受 RTMPS；本書的備援推流 |
| 自選 | UDP | SRT | 沒有 IANA 指定的預設 port，listener 自選一個；本書 ingest 203.0.113.25 用 UDP 9000（第 38 章） |
| 554 | TCP | RTSP | 監視器、IP camera 常見 |
| 443 | TCP | WHIP／WHEP、LL-HLS | 都是 HTTPS（第 38 章） |
| 443 | TCP | WebSocket（`wss://`） | 和 HTTPS 共用 port，靠 Upgrade 切換（第 32 章） |

SRT 的 latency 單位要特別小心：libsrt 的 `SRTO_LATENCY` 是毫秒（預設 120 ms），ffmpeg 的 srt URL 參數 `latency` 是微秒，所以第 38 章遠端講者的 500 ms 在 ffmpeg 裡寫成 `latency=500000`。傳統 RTP 用偶數 port、RTCP 用下一個奇數 port；WebRTC 一律 `rtcp-mux`，RTP 與 RTCP 共用同一個 port。

### 容器與 Kubernetes

| Port | 傳輸 | 服務 | 備註 |
|---|---|---|---|
| 6443 | TCP | Kubernetes API server | |
| 10250 | TCP | kubelet API | 只開給 control plane |
| 2379／2380 | TCP | etcd（client／peer） | |
| 30000–32767 | TCP、UDP | NodePort 預設範圍 | 節點的 security group 要放行（第 44 章） |
| 53 | UDP、TCP | 叢集 DNS | 本書 kube-dns Service IP 10.96.0.10（第 44 章） |
| 2375／2376 | TCP | Docker daemon API（明文／TLS） | 2375 不可對外，等於把主機交出去 |

## D.3 聲聲 Live 的 port 地圖

把正文散落各章的設定集中成一張圖，對照時用。外側是公網位址，內側是 VPC 10.20.0.0/16。

```text
 Internet
   │
   ├─ TCP 443 ─► www CDN edge 203.0.113.10／.11 ──► origin 203.0.113.70（錄影回放、LL-HLS）
   │
   ├─ TCP 443 ─► API LB 203.0.113.80（api、auth，依 SNI 選憑證）
   │               └─► nginx 10.20.3.11 ──► app-a 10.20.3.21:8000、app-b 10.20.3.22:8000（gunicorn）
   │                                         └─► PostgreSQL 10.20.17.15:5432
   │
   ├─ TCP 443 ─► rt L4 LB 203.0.113.40 ──► TLS 終結 nginx 10.20.2.11–.13
   │               └─► gw-41–46 nginx :8080 ─(Unix socket)─► uvicorn ──► Redis 10.20.17.21:6379
   │
   ├─ UDP 40000 ───────► SFU 203.0.113.60（sfu-tpe-1，VPC 10.20.1.15，管理介面 :7070 只開 VPC）
   ├─ UDP／TCP 3478、TCP 443 ─► TURN 203.0.113.50（relay 49152–65535，只轉送到 SFU）
   ├─ UDP 9000（SRT）、TCP 443（WHIP、RTMPS）─► live 203.0.113.25
   └─ UDP／TCP 53 ─► ns1 203.0.113.53

 VPC 內部：reco gRPC 10.20.4.12:50051、presence 10.20.3.41:8090、探針 10.20.3.21:9910（UDP）、
          品質回報 collector 10.20.3.7:5005（UDP）、resolver 10.20.0.2／.3:53
```

這張圖由上往下讀，每一條箭頭都是一條需要 security group 規則的路徑。第一條是唯一走 CDN 的流量；第二、三條都是 TCP 443，但 API 的 LB 會解 TLS、rt 的 L4 LB 不解（第 19 章），所以 rt 的 TLS 憑證在三台 nginx 上。往下三條是 UDP 為主的影音路徑，它們不能放在只懂 HTTP 的 L7 LB 後面（第 25、37、38 章）。最下方的內部 port 只在 VPC 內可達，從辦公室要經過 WireGuard。

## D.4 HTTP status code：家族與「誰產生的」

status code 是 3 位數，第一位決定家族。程式只看數字，不比對 reason phrase（HTTP/2 起根本沒有 reason phrase，第 20 章）。

| 家族 | 意義 | 該找誰 | 能不能自動重試 |
|---|---|---|---|
| 1xx | 資訊性：請求還在進行 | 協定層 | 不適用 |
| 2xx | 成功 | | 不需要 |
| 3xx | 重新導向或「用你的快取」 | 設定、快取 | 照 `Location` 走 |
| 4xx | 請求本身有問題，原封不動重送不會成功 | 呼叫方 | 不行（408、425、429 例外，見下表） |
| 5xx | 處理方或中間的 gateway 失敗 | 服務方與 proxy | 502、503、504 可對 idempotent 請求退避重試 |

看到一個錯誤碼時，第一個問題永遠是：**這個回應是哪一層產生的？** 一個請求在聲聲 Live 會穿過好幾層，每一層都能自己產生回應，而越外層產生的錯誤，越內層的 log 越可能完全沒有紀錄。

```text
 瀏覽器 ─► CDN ─► API LB ─► nginx ─► gunicorn ─► Flask view ─► PostgreSQL
            │       │         │         │            │
            │       │         │         │            └─ 400、401、403、404、409、422、429、500、503（app 自己判斷）
            │       │         │         └─ 400（請求行或 header 超過 limit_request_*）、502 的根因（WORKER TIMEOUT）
            │       │         └─ 400、404、408、413、444、494–499、502、503（limit_req）、504
            │       └─ 502、503（沒有健康 target）、504（idle timeout）、460／463 這類廠商碼
            └─ 403（WAF）、421、429、5xx 與 52x 這類廠商碼（425 由 origin 依 Early-Data 產生）

 讀法：在 log 裡找「最外層有紀錄、而下一層沒有紀錄」的那一層，回應就是它產生的。
```

圖中每一層下方列的是「這一層自己會產生」的碼。nginx 的 access log 記的是它送給 client 的碼，`$upstream_status` 記的是上游回給它的碼；兩者不同時（例如 access log 是 504、`$upstream_status` 是空的），就代表回應是 nginx 自己產生的（第 25、43 章）。全書用 `x-request-id` 串接 nginx 與 Flask 的 log，一筆請求只要在某一層之後就找不到 request id，答案就在那個交界。

## D.5 HTTP status code 完整表

### 1xx、2xx、3xx

| 碼 | 名稱 | 意義 | 常見產生者 | 除錯提示 |
|---|---|---|---|---|
| 100 | Continue | client 送了 `Expect: 100-continue`，server 表示「body 可以送了」 | server、proxy | 大檔上傳前先讓 server 看 header；server 可直接回 413 或 401 拒絕（第 20 章） |
| 101 | Switching Protocols | 同意升級協定，例如 WebSocket | server（uvicorn） | 經過 nginx 時要轉送 `Upgrade` 與 `Connection` header，否則升級失敗（第 32 章） |
| 103 | Early Hints | 主回應前先送 `Link: preload` | server、CDN | 不是所有 proxy 都會轉送（第 22 章） |
| 200 | OK | 成功 | app | 串流回應的 200 在第一批資料送出時就定了，之後出錯只能斷線（第 41 章） |
| 201 | Created | 建立成功，附 `Location` | app | 例如 `POST /v1/payments` 建立 `pay_0001`（第 24 章） |
| 202 | Accepted | 已接受、稍後處理 | app | 要附可查詢進度的資源 |
| 204 | No Content | 成功但沒有 body | app | 不可帶 body；DELETE 常用 |
| 206 | Partial Content | 回傳 `Range` 指定的部分 | nginx、CDN | 拖曳錄影卻回 200 加整份檔案，表示 server 忽略了 Range（第 21 章） |
| 301 | Moved Permanently | 永久搬家 | nginx、app | 會被瀏覽器長期快取；舊圖片網域改版就用 301（第 22 章） |
| 302 | Found | 暫時轉址 | app | 歷史上瀏覽器會把 POST 改成 GET；要保留方法用 307 |
| 303 | See Other | 用 GET 去看另一個資源 | app | 表單送出後轉到結果頁 |
| 304 | Not Modified | 快取仍有效，沒有 body | nginx、CDN、app | 條件請求成功（`If-None-Match`），仍需帶 `ETag`、`Cache-Control`（第 21 章） |
| 307 | Temporary Redirect | 暫時轉址，保留方法與 body | nginx、app | |
| 308 | Permanent Redirect | 永久轉址，保留方法與 body | nginx、app | API 改路徑時比 301 安全 |

### 4xx

| 碼 | 名稱 | 意義 | 常見產生者 | 除錯提示 |
|---|---|---|---|---|
| 400 | Bad Request | 請求語法或格式錯 | **任何一層**：nginx、gunicorn、uvicorn、app | 先看是哪一層：nginx 對缺少或重複 `Host`、CL 與 TE 並存回 400（第 20 章）；gunicorn 在請求行或單一 header 超過 `limit_request_line`／`limit_request_field_size` 時回 400 而不是 414／431；uvicorn 記 `Invalid HTTP request received.`；app 是 JSON 壞掉。升級 server 後某些 client 開始收到 400，多半是 client 本來就不合規 |
| 401 | Unauthorized | **未驗證**：沒帶憑證或憑證無效 | app、API gateway | 必須帶 `WWW-Authenticate`（第 27 章）；preflight 被驗證 middleware 擋下也會變成 401，OPTIONS 不帶 credentials（第 23、45 章）；WebSocket 握手 ticket 無效也回 401（第 32 章） |
| 403 | Forbidden | **已驗證但沒有權限**，或被政策擋下 | app、WAF、CDN | 自家 API 用 `insufficient_scope` 區分（第 27 章）；WebSocket 握手 `Origin` 不在允許清單回 403（第 32 章）；看 response header 判斷是 WAF 還是 app 的頁面 |
| 404 | Not Found | 找不到資源 | app、nginx | 先確認 `Host` 打到正確的虛擬主機（第 20 章）；也常用來隱藏「存在但你無權知道」的資源（第 24 章） |
| 405 | Method Not Allowed | 路由存在但不接受這個 method | app（Werkzeug 自動產生） | 回應必須附 `Allow`；常見於 POST 打到只接受 GET 的路由，或 CORS preflight 的 OPTIONS 沒有路由 |
| 406 | Not Acceptable | 無法提供 `Accept` 要求的格式 | app | 多半是 client 的 `Accept` 寫太窄 |
| 408 | Request Timeout | server 等不到完整的請求 | nginx（`client_header_timeout`、`client_body_timeout`）、自寫 server | 慢速 client 或上傳中斷（第 40 章）；有些 server 關閉閒置 keep-alive 連線時也送 408，client 可安全重試 |
| 409 | Conflict | 和資源目前的狀態衝突 | app | 時段被搶走；同一個 `Idempotency-Key` 正在處理中（第 24 章） |
| 410 | Gone | 資源已永久移除 | app | 可被快取 |
| 412 | Precondition Failed | `If-Match` 等條件不成立 | app | 有人先改過了，避免 lost update（第 21 章） |
| 413 | Content Too Large | body 太大 | **nginx**（`client_max_body_size`，預設 1 MB）、app（Werkzeug `MAX_CONTENT_LENGTH`） | nginx error log 有 `client intended to send too large body`；大檔改走直傳物件儲存（第 20 章） |
| 414 | URI Too Long | 請求網址太長 | nginx（`large_client_header_buffers`） | 把大量參數改用 POST body |
| 415 | Unsupported Media Type | 不支援的 `Content-Type` | app | 新版 Werkzeug 對 `request.get_json()` 收到非 JSON 的 Content-Type 會回 415 |
| 416 | Range Not Satisfiable | `Range` 超出檔案範圍 | nginx、CDN | 播放器記錯檔案長度 |
| 421 | Misdirected Request | 這台 server 不負責這個 Host | server、LB、CDN | HTTP/2 連線重用（coalescing）到不服務該名稱的 server 時出現，client 應換一條連線重試（第 20、22 章） |
| 422 | Unprocessable Content | 格式正確但語意錯 | app | 金額是負數；同一個 `Idempotency-Key` 配不同內容（第 24 章） |
| 425 | Too Early | 不處理可能被重放的 0-RTT 資料 | origin（看到 `Early-Data: 1`） | 聲聲 Live 只放行 GET／HEAD 走 0-RTT，其他回 425，client 等交握完成再送（第 13、18、22 章） |
| 426 | Upgrade Required | 要改用別的協定 | server | WebSocket 版本不對時回 426 並附 `Sec-WebSocket-Version: 13`（第 32 章） |
| 428 | Precondition Required | 要求必須帶條件 | app | 不帶 `If-Match` 的 PUT（第 21 章） |
| 429 | Too Many Requests | 觸發限速 | API gateway、app、CDN | 常附 `Retry-After`；「使用者不多卻全站 429」代表限速器看到的 IP 是 proxy（第 25 章）；注意 nginx `limit_req` 預設回的是 503，要用 `limit_req_status 429` 改 |
| 431 | Request Header Fields Too Large | header 太大 | server、app | cookie 累積過多；nginx 對這種情況回的是 400（log 寫 `Request Header Or Cookie Too Large`），不是 431（第 20、40 章） |
| 451 | Unavailable For Legal Reasons | 因法律原因無法提供 | app、CDN | |

### 5xx

| 碼 | 名稱 | 意義 | 常見產生者 | 除錯提示 |
|---|---|---|---|---|
| 500 | Internal Server Error | 未處理的例外 | **app** | 看 Flask traceback；500 沒帶 CORS header 時，前端只看得到「CORS 錯誤」，先修 500（第 45 章） |
| 501 | Not Implemented | server 不認得這個 method | server | |
| 502 | Bad Gateway | proxy 從上游拿到壞的回應，或連線被拒、被重置、被提早關閉 | **nginx、LB、CDN**（不是 app） | 看 nginx error log 的原因字串（D.7）；gunicorn `WORKER TIMEOUT` 殺掉 worker 也會變成 502（第 43 章）；部署時沒做 graceful shutdown、upstream keep-alive 逾時方向錯都會零星出現（第 20、43、45 章）；**請求可能其實已經成功** |
| 503 | Service Unavailable | 暫時無法服務 | LB（沒有健康的 target）、nginx（`limit_req`／`limit_conn` 預設值）、app（主動降載、`/readyz` 在 drain 時回 503） | 可附 `Retry-After`；第 43 章 timeout 鏈裡由 app 在 10 秒預算內產生的 503 是「好的」503，訊息最精確 |
| 504 | Gateway Timeout | proxy 在逾時內等不到上游的回應 | **nginx、LB、CDN** | 上游太慢或 worker 卡住；Flask log 可能完全沒錯誤，**資料庫裡可能已經有結果**，重送前先查證（第 20 章）；外層逾時必須比內層長（第 43 章） |
| 505 | HTTP Version Not Supported | 不支援的 HTTP 版本 | server | 自寫 client 送了錯的版本字串 |

把 502 與 504 記成一句話：**502 是「上游給了我壞東西或掛了電話」，504 是「上游一直沒回話」**。兩者都是中間那一層產生的，所以修的地方在上游，查的地方卻要從中間那一層的 log 開始。

## D.6 非標準與廠商專屬的碼

下列碼不在 HTTP 標準裡，只出現在特定軟體的 log 或回應中。看到它們時，第一件事是確認「這是哪個元件的私有語意」。

| 碼 | 出處 | 意義 | 除錯提示 |
|---|---|---|---|
| 444 | nginx | 不回應、直接關閉連線 | 本書用 `default_server` 的 `return 444` 擋下未知 Host（第 20 章）；client 看到的是連線被關，不是 status code |
| 494 | nginx（內部） | request header 太大 | 對 client 送出時變成 400，只出現在設定與內部處理 |
| 495 | nginx | client 憑證驗證失敗 | mTLS 的 `ssl_verify_client`（第 18 章） |
| 496 | nginx | 要求 client 憑證但沒有提供 | mTLS 沒帶憑證 |
| 497 | nginx | 對 HTTPS port 送了明文 HTTP | 用 http scheme 打到 443；可在 `error_page 497` 轉址 |
| 499 | nginx | **client 在 nginx 回應前就關閉了連線** | 只出現在 nginx access log，client 不會收到；常見原因是前一層（LB、CDN、瀏覽器）的逾時比 nginx 短：LB idle 60 秒到期時 LB 回 504、nginx 記 499（第 43 章）；也可能是使用者按了重新整理。大量 499 伴隨重複 POST，要檢查 idempotency（第 20 章） |
| 460 | 雲端 ALB 類 LB（以 AWS ALB 為例） | client 在 LB 等待 target 回應時關閉連線 | 和 nginx 的 499 同義，看 client 端的逾時 |
| 463 | 雲端 ALB 類 LB（以 AWS ALB 為例） | `X-Forwarded-For` 帶了太多 IP | 某一層一直附加 XFF 沒有覆寫（第 25 章） |
| 520 | CDN（以 Cloudflare 為例） | origin 回了無法理解的回應 | origin 回空回應或連線被重置 |
| 521 | CDN | origin 拒絕連線 | origin 沒 listen，或防火牆只放行 CDN 回源網段卻漏了新網段 |
| 522 | CDN | 連 origin 的 TCP 逾時 | security group、路由（第 7 章） |
| 523 | CDN | origin 無法到達 | DNS 或路由錯 |
| 524 | CDN | TCP 連上了，但 origin 在時限內沒回 HTTP 回應 | 和 504 類似，看 origin 的慢請求 |
| 525 | CDN | 和 origin 的 TLS 交握失敗 | origin 憑證、SNI、TLS 版本（第 19 章） |
| 526 | CDN | origin 憑證無效 | 嚴格驗證模式下 origin 憑證過期或名稱不符 |

廠商碼的定義與名稱以該廠商的文件為準（截至 2026 年 10 月，上表的語意是 AWS ALB 與 Cloudflare 公開文件的寫法，其他 CDN 與 LB 多半直接回 502／504）。

## D.7 nginx error log 字串對照：502、503、504、499 從哪裡來

nginx 回 5xx 時，access log 只有數字，原因在 error log。下表把最常見的字串對應回 status code 與網路上發生的事。括號裡的 errno 是 Linux 的編號（D.12）。

| error log 的關鍵字 | client 看到 | 網路上發生的事 | 先查 | 章節 |
|---|---|---|---|---|
| `connect() failed (111: Connection refused) while connecting to upstream` | 502 | SYN 換來 RST：upstream 沒人在 listen | `ss -ltnp` 看 listen 位址是否只有 127.0.0.1；服務是否在重啟中 | 第 10、45 章 |
| `upstream timed out (110: Connection timed out) while connecting to upstream` | 504 | SYN 沒有回應 | security group、路由、對方 accept queue 滿 | 第 10、45 章 |
| `upstream timed out (110: Connection timed out) while reading response header from upstream` | 504 | 連上了、請求送了，等不到 header | worker 卡住、event loop 被阻塞、`proxy_read_timeout` | 第 42、43 章 |
| `upstream prematurely closed connection while reading response header from upstream` | 502 | 上游送 FIN 但沒給回應 | gunicorn `WORKER TIMEOUT`、worker 被 OOM 殺掉、上游 keep-alive 比 nginx 短 | 第 20、43 章 |
| `recv() failed (104: Connection reset by peer) while reading response header from upstream` | 502 | 上游送 RST | 上游 crash、對已關閉的 keep-alive 連線送了請求 | 第 10、45 章 |
| `upstream sent too big header while reading response header from upstream` | 502 | 上游的 response header 超過 `proxy_buffer_size` | 上游塞了太大的 cookie 或 header | 第 20 章 |
| `no live upstreams while connecting to upstream` | 502 | 所有 upstream 都被標記為失敗 | 前一波錯誤造成的連鎖；看更早的 log | 第 25 章 |
| `connect() to unix:/run/… failed (2: No such file or directory)` | 502 | Unix socket 檔不存在 | uvicorn 還沒啟動或 socket 路徑錯 | 第 33 章 |
| `connect() to unix:/run/… failed (11: Resource temporarily unavailable)` | 502 | Unix socket 的 backlog 滿了 | worker 處理不過來 | 第 33、42 章 |
| `SSL_do_handshake() failed … while SSL handshaking to upstream` | 502 | 到上游的 TLS 交握失敗 | `proxy_ssl_server_name`、上游憑證 | 第 18、19 章 |
| `limiting requests, excess: …` | 503（預設） | `limit_req` 觸發 | 要回 429 就設 `limit_req_status 429` | 第 25 章 |
| `client intended to send too large body` | 413 | body 超過 `client_max_body_size` | 調整上限或改走直傳 | 第 20 章 |
| access log 的 499 | （client 已離開） | client 先關閉連線 | 前一層的逾時、使用者重新整理 | 第 43 章 |

```text
 同一個問題時而 502、時而 504（第 43 章故事，修正前 gunicorn 與 nginx 都是 30 秒）

 0 s           請求進入 nginx ─► gunicorn worker 開始跑報表（需要 45 s）
 30 s ─┬─ arbiter 先到：SIGABRT 殺 worker ─► nginx 讀到 EOF ─► 502「upstream prematurely closed」
       └─ nginx 先到：proxy_read_timeout ──► 504「upstream timed out … reading response header」
                                             （worker 隨後仍被殺）
 修正：內層先放棄、外層比內層長。app 預算 10 s ＜ gunicorn 30 s ＜ nginx 35 s ＜ LB 60 s ＜ CDN 75 s
```

這張時間軸說明為什麼「看到 502 就去查 502、看到 504 就去查 504」有時行不通：兩個計時器一樣長時，誰先到期是隨機的，同一個根因會輪流以兩個碼出現。修正後的 timeout 鏈（第 43 章）讓最內層的 app 先以 503 結束，log 寫在最了解狀況的那一層。

## D.8 WebSocket close code

close frame（opcode 0x8）的 payload 是 2 bytes 的 close code 加上可選的 UTF-8 reason；控制 frame 的 payload 最多 125 bytes，所以 reason 最多 123 bytes（第 32 章）。

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌─┬─┬─┬─┬───────┬─┬─────────────┬───────────────────────────────┐
 │F│R│R│R│opcode │M│ Payload len │      Close code（16，網路序）   │
 │1│0│0│0│ 1000  │ │  （≤ 125）   │      例：0x03E8 = 1000         │
 ├─┴─┴─┴─┴───────┴─┴─────────────┼───────────────────────────────┤
 │（client 送出時這裡是 4 bytes 的 masking key）                    │
 ├───────────────────────────────────────────────────────────────┤
 │                 Reason（UTF-8，最多 123 bytes）               │
 └───────────────────────────────────────────────────────────────┘
  例：close 1000「下課」的 payload ＝ 03 e8 e4 b8 8b e8 aa b2
```

讀這張圖時只要記住三件事：code 在 payload 的前 2 bytes、用網路序；reason 是 UTF-8，中文一個字 3 bytes，所以「下課」佔 6 bytes；payload 只有 1 byte 是協定錯誤。瀏覽器的 `close` 事件把這些變成 `code`、`reason`、`wasClean` 三個欄位。

| Code | 名稱 | 誰送／何時出現 | 前端該怎麼做 | 章節 |
|---|---|---|---|---|
| 1000 | Normal Closure | 任一方正常結束 | 不重連 | 第 32 章 |
| 1001 | Going Away | server 下線部署、瀏覽器離開頁面 | 退避加抖動後重連 | 第 31、33 章 |
| 1002 | Protocol Error | 違反協定，例如 client frame 沒 mask | 不重連，回報 bug | 第 32 章 |
| 1003 | Unsupported Data | 收到無法處理的資料型別 | 不重連，回報 bug | 第 32 章 |
| 1004 | （保留） | 不可使用 | | |
| 1005 | No Status Received | **保留，不會出現在線上**；收到不帶 code 的 close 時由 API 回報 | 視同正常結束 | 第 32 章 |
| 1006 | Abnormal Closure | **保留，不會出現在線上**；沒收到 close frame 就斷線 | 指數退避後重連；看斷線前閒置秒數 | 第 32、45 章 |
| 1007 | Invalid Frame Payload Data | text 訊息不是合法 UTF-8 | 不重連，回報 bug | 第 32 章 |
| 1008 | Policy Violation | 違反政策，例如 Origin 或權限 | 不重連，提示使用者 | 第 32 章 |
| 1009 | Message Too Big | 訊息超過對方上限（本書聊天 64 KiB、白板 1 MiB） | **不要重送同一則**，改走 HTTP 上傳 | 第 32 章 |
| 1010 | Mandatory Extension | client 要求的 extension 沒被接受 | 修設定 | 第 32 章 |
| 1011 | Internal Error | server 未預期的錯誤 | 退避後重連 | 第 32 章 |
| 1012 | Service Restart | server 重啟 | 退避加隨機抖動後重連，避免重連驚群 | 第 31、33 章 |
| 1013 | Try Again Later | server 暫時過載 | 退避加抖動 | 第 33 章 |
| 1014 | Bad Gateway | gateway 從上游拿到無效回應（IANA 登錄值） | 退避後重連 | |
| 1015 | TLS Handshake | **保留，不會出現在線上**；TLS 交握失敗 | 檢查憑證 | 第 32 章 |
| 3000–3999 | 向 IANA 登錄 | 框架、函式庫 | 依登錄語意 | |
| 4000–4999 | 私有使用 | 應用程式自訂 | 依自訂語意 | |
| 4001 | 聲聲 Live 自訂：授權到期 | 連線滿 15 分鐘 | 換 ticket 重連 | 第 32 章 |
| 4008 | 聲聲 Live 自訂：client 太慢 | 出站佇列放不下必達訊息 | 重連並補發；連續發生改走快照模式 | 第 33 章 |

兩個實務細節。第一，瀏覽器的 `ws.close(code, reason)` 只接受 1000 或 3000–4999，所以應用自訂語意要放在 4000–4999。第二，**握手失敗時根本沒有 close code**：server 對升級請求回 400（不是升級請求）、401（ticket 無效）、403（Origin 不符）或 426（版本不對），但瀏覽器不會把 HTTP 狀態交給 JavaScript，前端只會看到一個 `error` 事件加上 code 1006（第 32 章）。所以「全部都是 1006」時，要到 nginx 的 access log 找 `/ws/` 路徑的 HTTP 狀態。

| 斷線樣態 | 最可能的原因 | 章節 |
|---|---|---|
| 1006，斷線前都剛好閒置約 60 秒 | 心跳停用加 nginx `proxy_read_timeout` 預設 60 秒（本書 `/ws/` 設 75 秒、心跳 25 秒） | 第 32、45 章 |
| 1006，集中在換網路或進隧道 | NAT 清表、行動網路切換；WebSocket 走 TCP，不受 QUIC migration 保護 | 第 7、13、33 章 |
| 1001／1012 集中在部署時間 | 例行部署，處理不好會重連驚群 | 第 31、33 章 |
| 1006 大量、伴隨 health check 失敗 | event loop 被阻塞，節點被移出 LB | 第 42 章 |

## D.9 DNS rcode 與 EDE

rcode 在 DNS header 第 3–4 byte 的最後 4 bit。EDNS(0) 的 OPT record 再借 8 bit 當高位，組成 12 bit 的 extended rcode；EDE 則是 OPT 裡的一個 option，帶著更細的原因。

```text
 DNS header 的旗標（第 14 章）
  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
 ┌──┬───────────┬──┬──┬──┬──┬──┬──┬──┬───────────┐
 │QR│  Opcode   │AA│TC│RD│RA│ Z│AD│CD│   RCODE   │   ← 低 4 bit：0–15
 └──┴───────────┴──┴──┴──┴──┴──┴──┴──┴───────────┘

 OPT record 的 TTL 欄位（32 bit）被重新解讀為：
 ┌────────────────┬────────────────┬──┬─────────────────────────────┐
 │ EXTENDED-RCODE │    VERSION     │DO│             Z               │
 │    （高 8 bit） │   （EDNS 版本） │  │                             │
 └────────────────┴────────────────┴──┴─────────────────────────────┘
  完整 rcode ＝ EXTENDED-RCODE × 16 ＋ header 的 RCODE，例：16 ＝ BADVERS

 EDE option（OPTION-CODE 15）
 ┌────────────────────────┬────────────────────────┐
 │ OPTION-CODE ＝ 15       │ OPTION-LENGTH          │
 ├────────────────────────┼────────────────────────┤
 │ INFO-CODE（16 bit）     │ EXTRA-TEXT（UTF-8，可空）│
 └────────────────────────┴────────────────────────┘
```

讀這三張圖的順序就是讀 `dig` 輸出的順序：先看 `status:`（header 的 RCODE），再看 `flags:` 裡有沒有 `aa`、`ad`、`tc`，最後看 OPT PSEUDOSECTION 裡的 `EDE:` 那一行。EDE 只是補充說明，不改變 rcode 的意義；不是所有 resolver 都會附上（第 15 章）。

| rcode | 名稱 | 意義 | 常見原因 | 章節 |
|---|---|---|---|---|
| 0 | NOERROR | 成功；answer 可能是空的 | answer 為空叫 **NODATA**：名字存在但沒有這個 type（例如 `api` 只有 A 沒有 AAAA） | 第 14、15 章 |
| 1 | FORMERR | 查詢格式錯誤 | 自己組的封包有 bug；中間設備不支援 EDNS | 第 14、15 章 |
| 2 | SERVFAIL | resolver 無法給出可靠答案 | 權威 server 全不回應、DNSSEC 驗證失敗、委派錯誤；看 EDE、用 `dig +cd` 對照 | 第 15 章 |
| 3 | NXDOMAIN | 名字不存在 | 打錯字、還沒建、負面快取（SOA 決定時間）、search domain 加錯後綴 | 第 14–16 章 |
| 4 | NOTIMP | 不支援這個 opcode | 少見 | |
| 5 | REFUSED | 拒絕回答 | 問了不負責該 zone 的權威 server；resolver 不對外開放遞迴 | 第 14、15 章 |
| 6 | YXDOMAIN | 不該存在的名字存在 | DNS dynamic update 的前提不成立 | |
| 7 | YXRRSET | 不該存在的 RRset 存在 | 同上 | |
| 8 | NXRRSET | 該存在的 RRset 不存在 | 同上 | |
| 9 | NOTAUTH | 不是這個 zone 的權威，或 TSIG 驗證失敗 | zone transfer、dynamic update 的金鑰錯 | |
| 10 | NOTZONE | 名字不在 zone 內 | dynamic update | |
| 16 | BADVERS／BADSIG | EDNS 版本不支援；在 TSIG 中表示簽章錯 | 需靠 OPT 的 extended rcode 表達 | |
| 23 | BADCOOKIE | DNS cookie 錯誤 | client 重送時要帶 server cookie | |

| EDE | 名稱 | 白話 | 典型處理 |
|---|---|---|---|
| 0 | Other | 其他，看 EXTRA-TEXT | |
| 1 | Unsupported DNSKEY Algorithm | resolver 不支援 zone 用的簽章演算法 | 視同未簽章 |
| 2 | Unsupported DS Digest Type | 不支援 DS 的雜湊演算法 | |
| 3 | Stale Answer | 用了過期的快取回答（serve-stale） | 權威 server 可能正在故障 |
| 4 | Forged Answer | resolver 刻意回了偽造的答案 | 政策攔截 |
| 5 | DNSSEC Indeterminate | 無法判定 DNSSEC 狀態 | |
| 6 | DNSSEC Bogus | 驗證失敗 | 檢查信任鏈（第 15 章） |
| 7 | Signature Expired | RRSIG 過期 | 重新簽章；`dig +cd` 能拿到答案就是它（第 15 章） |
| 8 | Signature Not Yet Valid | RRSIG 尚未生效 | 簽章端或 resolver 的時鐘 |
| 9 | DNSKEY Missing | 依父區 DS 找不到對應的 DNSKEY | KSK 輪替時先撤舊鑰、DS 還沒換（第 15 章） |
| 10 | RRSIGs Missing | 應有的簽章不見了 | |
| 11 | No Zone Key Bit Set | DNSKEY 沒有 zone key 旗標 | |
| 12 | NSEC Missing | 否定答案缺少證明 | |
| 13 | Cached Error | 回的是快取住的錯誤（例如先前的 SERVFAIL） | 等快取過期或清快取 |
| 14 | Not Ready | resolver 還沒準備好 | 剛啟動 |
| 15 | Blocked | 被營運者的拒絕清單擋下 | |
| 16 | Censored | 因外部要求被擋 | |
| 17 | Filtered | 因 client 自己要求的過濾被擋 | 家長控制類服務 |
| 18 | Prohibited | client 不被允許使用這台 resolver | 存取控制 |
| 19 | Stale NXDOMAIN Answer | 用過期快取回了 NXDOMAIN | |
| 20 | Not Authoritative | 權威 server 收到遞迴查詢但不負責該 zone | 通常伴隨 REFUSED |
| 21 | Not Supported | 不支援請求的操作或查詢類型 | |
| 22 | No Reachable Authority | 所有權威 server 都連不到 | 權威 server、網路或防火牆（第 15 章） |
| 23 | Network Error | 連權威 server 時遇到網路錯誤 | |
| 24 | Invalid Data | 權威 server 回了無效的資料 | |

上表是 Extended DNS Errors 規格（RFC 8914）定義的 0–24；之後陸續有新值登錄到 IANA 的表中，看到不認得的數字時以 IANA 登錄表為準。

## D.10 TLS alert

alert 是 TLS 的錯誤通知，record 的 content type 是 21。在 TLS 1.3，交握完成後的 alert 會被加密，外層看起來是 application_data（23），只有握手早期的 alert 能直接在封包裡讀到（第 18 章）。

```text
 TLS record（明文的 alert）
 ┌──────────────┬───────────────────────┬──────────────────┬────────┬─────────────┐
 │ ContentType  │ legacy_record_version │ length           │ level  │ description │
 │ 21（alert）   │ 0x0303                │ 0x0002（2 bytes） │ 1 或 2 │ 例：48      │
 └──────────────┴───────────────────────┴──────────────────┴────────┴─────────────┘
  level：1 = warning、2 = fatal。TLS 1.3 除了 close_notify 與 user_canceled，所有 alert 都是 fatal
  例：15 03 03 00 02 02 30  ＝ fatal unknown_ca（0x30 = 48）
```

最後一行的 7 bytes 可以直接拿來對照 Wireshark：`15` 是 alert、`03 03` 是版本欄、`00 02` 是長度、`02` 是 fatal、`30` 是十進位 48，也就是 unknown_ca。要判斷「誰不滿意誰」，看 alert 是**誰送的**：送 alert 的一方就是驗證失敗的那一方。

| 編號 | 名稱 | 誰送／何時 | 常見原因 | Python／OpenSSL 看到的字串 |
|---|---|---|---|---|
| 0 | close_notify | 任一方，正常結束 | 正常關閉；沒收到就斷線在 OpenSSL 3 會變成 `UNEXPECTED_EOF_WHILE_READING` | `SSLZeroReturnError`；少了它是 `SSLEOFError` |
| 10 | unexpected_message | 任一方 | 實作錯誤、中間設備改了封包 | |
| 20 | bad_record_mac | 任一方 | 封包在路上被改、金鑰不一致 | |
| 40 | handshake_failure | server 多半 | cipher suite、群組沒有交集 | `SSLV3_ALERT_HANDSHAKE_FAILURE` |
| 42 | bad_certificate | 驗證方 | 憑證格式或簽章有問題；mTLS 帶錯憑證 | `SSLV3_ALERT_BAD_CERTIFICATE` |
| 43 | unsupported_certificate | 驗證方 | 憑證類型不支援 | |
| 44 | certificate_revoked | 驗證方 | 憑證已撤銷 | |
| 45 | certificate_expired | 驗證方 | 對方憑證過期（先看自己的時鐘） | `SSLV3_ALERT_CERTIFICATE_EXPIRED` |
| 46 | certificate_unknown | 驗證方 | 其他驗證問題 | `SSLV3_ALERT_CERTIFICATE_UNKNOWN` |
| 47 | illegal_parameter | 任一方 | 交握欄位值不合法 | |
| 48 | unknown_ca | 驗證方 | 鏈接不到信任的 root：私有 CA、漏送中間憑證 | `TLSV1_ALERT_UNKNOWN_CA`（第 18 章實驗的 server 端紀錄） |
| 49 | access_denied | server | 驗證通過但被存取控制拒絕 | |
| 50 | decode_error | 任一方 | 訊息無法解析 | |
| 51 | decrypt_error | 任一方 | 簽章或 Finished 驗證失敗 | |
| 70 | protocol_version | server 多半 | 版本沒有交集：舊 client 對只開 1.3 的 server | `TLSV1_ALERT_PROTOCOL_VERSION` |
| 71 | insufficient_security | server | 對方提供的參數都太弱 | |
| 80 | internal_error | 任一方 | 對方內部錯誤 | `TLSV1_ALERT_INTERNAL_ERROR` |
| 86 | inappropriate_fallback | server | 降級偵測 | |
| 90 | user_canceled | 任一方 | 使用者中止交握 | |
| 109 | missing_extension | 任一方 | 缺少必要的 extension | |
| 110 | unsupported_extension | client | server 回了 client 沒提出的 extension | |
| 112 | unrecognized_name | server | SNI 名稱這台 server 不認得 | `TLSV1_UNRECOGNIZED_NAME` |
| 113 | bad_certificate_status_response | client | OCSP stapling 的回應無效 | |
| 115 | unknown_psk_identity | server | resumption 的 PSK 不認得 | |
| 116 | certificate_required | server | mTLS 要求 client 憑證卻沒收到；TLS 1.3 的 client 要到第一次 `recv()` 才看到（第 18 章） | `TLSV13_ALERT_CERTIFICATE_REQUIRED` |
| 120 | no_application_protocol | server | ALPN 沒有交集：gRPC 連到不支援 h2 的 LB | `TLSV1_ALERT_NO_APPLICATION_PROTOCOL` |

alert 是「對方送來的」錯誤，另一大類是 client **自己驗證失敗**，它不送 alert 給自己，而是在本機丟出 `ssl.SSLCertVerificationError`（`CERTIFICATE_VERIFY_FAILED`），訊息裡帶著 OpenSSL 的 verify code：

| verify code | 訊息 | 意義 | 先查 | 章節 |
|---|---|---|---|---|
| 9 | certificate is not yet valid | 尚未生效 | client 時鐘 | 第 19 章 |
| 10 | certificate has expired | 已過期 | 先看 client 時鐘，再看 `notAfter`；多副本是否都換了 | 第 19、45 章 |
| 18 | self-signed certificate | leaf 是自簽 | 測試憑證跑到 production | 第 18 章 |
| 19 | self-signed certificate in certificate chain | 鏈上的 root 不被信任 | 私有 CA、公司 TLS 檢查 proxy | 第 18 章 |
| 20 | unable to get local issuer certificate | 找不到簽發者 | 用 `openssl s_client -showcerts` 數張數：只有 leaf 就是漏送中間憑證 | 第 19 章 |
| 62 | hostname mismatch | 名稱不符 | 比對 SAN：用 IP 連？SNI 沒送？wildcard 跨兩層？ | 第 18 章 |

另外兩個常見字串不是 alert：`WRONG_VERSION_NUMBER` 多半是對明文 port 說 TLS（例如用 https scheme 打到 :80 或 :8000），`Connection reset by peer` 發生在交握中則多半是 TCP 層或中間設備的問題，不是憑證問題。瀏覽器的對應是 `NET::ERR_CERT_AUTHORITY_INVALID`（鏈）、`NET::ERR_CERT_COMMON_NAME_INVALID`（名稱）、`NET::ERR_CERT_DATE_INVALID`（效期或時鐘）、`ERR_SSL_PROTOCOL_ERROR`（交握本身失敗）。

## D.11 ICE 與 WebRTC 常見錯誤

WebRTC 的錯誤分散在好幾層：狀態欄位、STUN／TURN 錯誤碼、`icecandidateerror` 事件與 DOM 例外。先從狀態判斷卡在哪一段，再看細節。

```text
 卡在哪一段？（第 36 章的通則）

 gathering ─► 沒有 srflx／relay candidate ─────────► STUN／TURN 伺服器或網路（看 icecandidateerror）
    │
 checking ──► 有 candidate，但 pair 全部 failed ───► NAT 或防火牆擋 UDP（加開 TURN over TLS 443）
    │
 ICE connected ─► connectionState 變 failed ──────► DTLS：fingerprint 被改、setup 角色衝突
    │
 全部 connected ─► 沒畫面或沒聲音 ─────────────────► SDP、SFU、track、播放（第 34、35、39 章）
```

這張圖由上往下，每一站都是一個是非題。前兩站是網路問題，第三站是 SDP 或 signaling 問題，最後一站幾乎和網路無關。聲聲 Live 的單向問題（看得到聽不到）在 BUNDLE 加雙向 consent 的設計下，很少是網路層造成的（第 45 章）。

| 欄位 | 值 | 意義與下一步 |
|---|---|---|
| `iceGatheringState` | new → gathering → complete | 卡在 gathering 很久：有不回應的 STUN／TURN 伺服器；改用 trickle ICE |
| `iceConnectionState` | new、checking、connected、completed、disconnected、failed、closed | disconnected：consent 檢查暫時沒回應，可能自己恢復；failed：所有 pair 失敗或 consent 超過 30 秒沒回應，呼叫 `restartIce()`（第 36 章） |
| `connectionState` | new、connecting、connected、disconnected、failed、closed | 綜合 ICE 與 DTLS；ICE connected 而這裡 failed，幾乎一定是 DTLS（第 36 章） |
| `dtlsState`（getStats 的 transport） | new、connecting、connected、closed、failed | failed：比對雙方 SDP 的 `a=fingerprint` 與 `a=setup` |
| `signalingState` | stable、have-local-offer、have-remote-offer… | 在錯的狀態呼叫 `setRemoteDescription` 會丟 `InvalidStateError`：兩邊同時 offer（glare）或 signaling 把舊 session 的訊息送來 |
| `relayProtocol`（candidate） | udp、tcp、tls | `tls` 代表走 TURN over TLS，RTT 高但丟包低是正常現象（第 39 章） |

STUN 與 TURN 回應用自己的錯誤碼（放在 ERROR-CODE 屬性，第 36 章），數字借用 HTTP 的風格但語意不同：

| 碼 | 名稱 | 何時出現 | 處理 |
|---|---|---|---|
| 300 | Try Alternate | 請改用另一台伺服器 | 依 ALTERNATE-SERVER 重試 |
| 400 | Bad Request | 請求格式錯 | 實作問題 |
| 401 | Unauthorized | 第一次 Allocate 不帶帳密，或帳密錯 | 第一次是正常流程：拿 REALM、NONCE 後重送；持續 401 就是短效帳密錯或過期（本書 TTL 1 小時） |
| 403 | Forbidden | 帳密對，但不允許這個操作 | 對方 IP 不在 TURN 的 `allowed-peer-ip`：新 SFU 節點沒加進去時，走 relay 的使用者全部失敗（第 37、45 章） |
| 420 | Unknown Attribute | 帶了伺服器不懂的必要屬性 | |
| 437 | Allocation Mismatch | allocation 不存在或已存在 | NAT 換了 mapping、allocation 過期（第 36 章） |
| 438 | Stale Nonce | nonce 過期 | 用新的 nonce 重送，屬於正常流程 |
| 440 | Address Family not Supported | 要求的位址家族不支援 | IPv6 relay |
| 441 | Wrong Credentials | 同一個 allocation 換了帳密 | |
| 442 | Unsupported Transport Protocol | 要求的傳輸不支援 | |
| 443 | Peer Address Family Mismatch | 對方位址家族和 relay 不符 | |
| 486 | Allocation Quota Reached | 使用者的 allocation 數超過配額 | 前端重複建立 PeerConnection 沒關閉舊的 |
| 487 | Role Conflict | ICE 雙方都認為自己是 controlling（或都是 controlled） | 依 tie-breaker 交換角色，屬於正常流程 |
| 500 | Server Error | 伺服器暫時錯誤 | 重試 |
| 508 | Insufficient Capacity | TURN 沒有 relay port 可配 | relay 範圍太窄或伺服器滿載（第 37 章） |

`icecandidateerror` 事件的 `errorCode` 除了上表的 STUN 錯誤碼，還有一個 WebRTC 自訂的 **701**：表示連不到該 STUN／TURN 伺服器（沒有任何回應），不在 STUN 錯誤碼範圍內。設定裡留著一台早已下線的 STUN 伺服器時，每次連線都會多等好幾秒並出現 701，監控 701 的比例就能發現（第 36 章）。

| DOM 例外或錯誤 | 出處 | 常見原因 | 章節 |
|---|---|---|---|
| `NotAllowedError` | `getUserMedia()` | 使用者或政策拒絕攝影機／麥克風權限；非安全來源 | 第 39 章 |
| `NotAllowedError` | `<audio>`／`<video>` 的 `play()` | autoplay 政策擋下，使用者還沒和頁面互動；要處理被 reject 的 Promise | 第 39、45 章 |
| `NotFoundError` | `getUserMedia()` | 找不到符合條件的裝置 | |
| `NotReadableError` | `getUserMedia()` | 裝置被其他程式佔用或硬體錯誤 | |
| `OverconstrainedError` | `getUserMedia()` | 解析度或裝置 ID 的限制無法滿足 | |
| `InvalidStateError` | `setRemoteDescription()` 等 | 在錯的 signaling 狀態呼叫 | 第 35 章 |
| `RTCError`（`errorDetail`：`sdp-syntax-error`、`dtls-failure`、`fingerprint-failure` 等） | SDP 與傳輸層 | SDP munging 改壞了內容、DTLS 失敗；欄位支援依瀏覽器實作而定 | 第 35、36 章 |
| SFU 拒絕 m-line（port 0） | SFU 的 answer | 例如只留下 rtx 的 PT 98，SFU 以 `no_primary_codec` 拒絕（第 35 章事故） | 第 35、45 章 |

## D.12 常見 errno 與 Python 例外對照

應用程式看不到 RST、ICMP 這些封包本身，只看到 errno；Python 再把 errno 翻譯成例外類別。errno 的**名稱**跨平台一致，**數字**不一致，所以 log 與程式都應該用名稱（第 10 章）。

| errno | Linux | macOS | Python 例外 | 網路上發生的事 | 第一個該懷疑的方向 | 章節 |
|---|---|---|---|---|---|---|
| `ECONNREFUSED` | 111 | 61 | `ConnectionRefusedError` | SYN 換來 RST；UDP 則是收到 ICMP port unreachable（只有 connect 過的 socket 會收到） | 服務沒啟動、port 打錯、只 listen 在 127.0.0.1、防火牆 REJECT | 第 9、10、45 章 |
| `ETIMEDOUT` | 110 | 60 | `TimeoutError` | SYN 沒有回應，核心重傳到放棄（Linux 預設約 127 秒） | security group、路由、對方 accept queue 滿；一定要自己設 connect timeout | 第 10、45 章 |
| `ECONNRESET` | 104 | 54 | `ConnectionResetError` | 收到 RST | 對方 crash 或重啟、LB／NAT 閒置逾時、對方沒讀完就關、連線池重用死連線 | 第 10、45 章 |
| `EPIPE` | 32 | 32 | `BrokenPipeError` | 對方已關閉，我方還在寫 | 第一次 `send()` 成功不代表對方收到；寫入前沒處理對方的關閉 | 第 10 章 |
| `EADDRINUSE` | 98 | 48 | `OSError` | bind 的位址與 port 已被佔用 | 舊 process 還沒退出、TIME_WAIT 擋住 server 重啟（`SO_REUSEADDR`）、兩個服務設了同一個 port | 第 9、10 章 |
| `EMFILE` | 24 | 24 | `OSError`（`Too many open files`） | process 的 fd 用光 | CLOSE_WAIT 洩漏、`ulimit -n` 太小（本書 presence 服務 fd 上限 4,096） | 第 10、40 章 |
| `EADDRNOTAVAIL` | 99 | 49 | `OSError` | 沒有可用的來源 port，或 bind 了本機沒有的位址 | 對同一目的地短連線太多、TIME_WAIT 佔滿 ephemeral 範圍 | 第 10 章 |
| `ENFILE` | 23 | 23 | `OSError` | 整台主機的 fd 用光 | 系統層級上限 | |
| `EHOSTUNREACH` | 113 | 65 | `OSError` | 收到 ICMP host unreachable，或沒有路由 | 路由、ARP 失敗、防火牆以 ICMP 拒絕 | 第 6、8 章 |
| `ENETUNREACH` | 101 | 51 | `OSError` | 沒有到目的網段的路由 | 沒有 default gateway；IPv6 沒有路由卻拿到 AAAA | 第 6 章 |
| `ECONNABORTED` | 103 | 53 | `ConnectionAbortedError` | 連線在本機被中止 | accept 之前對方就斷了 | |
| `EAGAIN`／`EWOULDBLOCK` | 11 | 35 | `BlockingIOError` | non-blocking socket 現在沒有資料或 buffer 滿 | 正常狀況，交給 selector 或 event loop 等待 | 第 40 章 |
| `EINPROGRESS` | 115 | 36 | `BlockingIOError` | non-blocking connect 進行中 | 正常狀況 | 第 40 章 |
| `EMSGSIZE` | 90 | 40 | `OSError` | UDP datagram 超過上限或超過 MTU（設了 DF） | payload 控制在約 1200 bytes（第 9 章） | 第 8、9 章 |

Windows 用另一套 Winsock 錯誤碼，例如 `WSAECONNRESET` 10054、`WSAECONNREFUSED` 10061、`WSAETIMEDOUT` 10060、`WSAEADDRINUSE` 10048、`WSAEMFILE` 10024；Python 仍會轉成上表同樣的例外類別。

不是 errno、但同樣常見的幾個 Python 例外：

| 例外 | 何時出現 | 和上表的關係 | 章節 |
|---|---|---|---|
| `TimeoutError`，`errno` 為 `None` | `settimeout()` 或 `create_connection(timeout=…)` 自己設的逾時到期 | 和核心的 `ETIMEDOUT` 同一個類別，但 errno 是 `None`；`socket.timeout` 自 3.10 起就是 `TimeoutError`，`asyncio.TimeoutError` 自 3.11 起也是 | 第 10、45 章 |
| `recv()` 回傳 `b""` | 收到 FIN | **不是錯誤**，是正常 EOF，應跳出迴圈並 close | 第 10 章 |
| `socket.gaierror` | `getaddrinfo()` 解析失敗 | DNS 層：`EAI_NONAME`（名字不存在，對應 NXDOMAIN）、`EAI_AGAIN`（暫時失敗，對應 SERVFAIL 或 resolver 逾時）；數字因 OS 而異 | 第 16 章 |
| `ssl.SSLCertVerificationError` | 本機驗證對方憑證失敗 | 看 `verify_code`、`verify_message`（D.10） | 第 18 章 |
| `ssl.SSLError` | 交握失敗、收到 alert | 看 `reason`，例如 `TLSV1_ALERT_UNKNOWN_CA` | 第 18 章 |
| `ssl.SSLEOFError` | 對方沒送 close_notify 就斷線 | TCP 層被關，可能是中間設備或對方 crash | 第 18 章 |
| `http.client.RemoteDisconnected` | 送出請求後對方關閉連線、沒有任何回應 | 是 `ConnectionResetError` 的子類別；最常見於重用了 server 已關閉的 keep-alive 連線 | 第 20、43 章 |
| `asyncio.LimitOverrunError` | `readuntil()` 超過 `StreamReader` 的 limit 還沒看到分隔符號 | 自寫 server 應對應成 431 | 第 40 章 |

下面的程式在本機重現其中五種，並示範「Python 依 errno 自動選擇例外類別」這件事。它只用標準函式庫、只連 127.0.0.1。

```python
import errno, http, socket, threading, time

def name(exc):
    code = getattr(exc, "errno", None)
    return f"{type(exc).__name__}({errno.errorcode.get(code, code)})"

# 1. OSError 依 errno 自動變成子類別：log 裡看到的例外名稱就是 errno 的翻譯
for code in (errno.ECONNREFUSED, errno.ECONNRESET, errno.EPIPE, errno.ETIMEDOUT, errno.EADDRINUSE, errno.EMFILE):
    print(f"OSError({errno.errorcode[code]:>12}) → {type(OSError(code, 'demo')).__name__}")

# 2. ECONNREFUSED：先拿一個空的 port，關掉後再連
probe = socket.socket(); probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]; probe.close()
try:
    socket.create_connection(("127.0.0.1", port), timeout=1)
except OSError as exc:
    refused = name(exc)
print("連到沒人聽的 port：", refused)

# 3. EADDRINUSE：對一個正在 listen 的位址與 port 再 bind 一次
a = socket.socket(); a.bind(("127.0.0.1", 0)); a.listen()
b = socket.socket()
try:
    b.bind(a.getsockname())
except OSError as exc:
    inuse = name(exc)
print("重複 bind：", inuse)

# 4. 讀取逾時：連上了，對方不回應。socket 自己的逾時沒有 errno
conn_side = []
threading.Thread(target=lambda: conn_side.append(a.accept()[0]), daemon=True).start()
c = socket.create_connection(a.getsockname(), timeout=0.2)
try:
    c.recv(1)
except OSError as exc:
    slow = name(exc)
print("連上但不回應：", slow)

# 5. 對方關閉後繼續寫：第一次 send 成功，之後 EPIPE 或 ECONNRESET
time.sleep(0.05); conn_side[0].close(); time.sleep(0.05)
log = []
for _ in range(5):
    try:
        c.send(b"x" * 1024); log.append("ok"); time.sleep(0.05)
    except OSError as exc:
        log.append(name(exc)); break
print("對方已關閉還在寫：", " → ".join(log))
for s in (a, b, c):
    s.close()

# 6. 狀態碼的標準名稱與家族
for code in (421, 425, 429, 431, 502, 504):
    family = "client error" if 400 <= code < 500 else "server error"
    print(code, http.HTTPStatus(code).phrase, "|", family)

assert refused == "ConnectionRefusedError(ECONNREFUSED)"
assert inuse == "OSError(EADDRINUSE)"
assert slow == "TimeoutError(None)"
assert log[0] == "ok" and log[-1] in ("BrokenPipeError(EPIPE)", "ConnectionResetError(ECONNRESET)")
```

在 macOS 上的實際輸出：

```text
OSError(ECONNREFUSED) → ConnectionRefusedError
OSError(  ECONNRESET) → ConnectionResetError
OSError(       EPIPE) → BrokenPipeError
OSError(   ETIMEDOUT) → TimeoutError
OSError(  EADDRINUSE) → OSError
OSError(      EMFILE) → OSError
連到沒人聽的 port： ConnectionRefusedError(ECONNREFUSED)
重複 bind： OSError(EADDRINUSE)
連上但不回應： TimeoutError(None)
對方已關閉還在寫： ok → BrokenPipeError(EPIPE)
421 Misdirected Request | client error
425 Too Early | client error
429 Too Many Requests | client error
431 Request Header Fields Too Large | client error
502 Bad Gateway | server error
504 Gateway Timeout | server error
```

前六行說明 Python 的例外類別是怎麼來的：`OSError` 的建構子看 errno 決定子類別，所以 `ECONNREFUSED` 變成 `ConnectionRefusedError`，而 `EADDRINUSE` 與 `EMFILE` 沒有專屬類別，仍是 `OSError`，要靠 `exc.errno` 區分。第 7 行一個 RTT 內就失敗，是「封包到了、沒人聽」。第 9 行的 errno 是 `None`，因為這是 socket 自己的逾時，不是核心回報的 `ETIMEDOUT`；在 log 裡把兩者分開，就能分辨「連不上」與「連上了等不到回應」。第 10 行是第 10 章那個反直覺的事實：第一次 `send()` 成功只代表核心收下了資料，對方回 RST 之後下一次寫入才失敗。在 Linux 上執行時，第 10 行可能是 `ConnectionResetError(ECONNRESET)`，取決於 RST 抵達的時機。

## D.13 從錯誤訊息到層：總表

只有一行錯誤訊息、不知道該查哪一節時，從這張表開始。它把前面各節的數字壓成「是哪一層、先看什麼」；完整的症狀表在第 45 章 45.12 節。

| 你看到的 | 層 | 先看 | 本附錄 |
|---|---|---|---|
| `NXDOMAIN`、`gaierror`、`Name or service not known` | DNS | `dig`、`dig SOA`、`getent hosts` | D.9、D.12 |
| `SERVFAIL`、`EDE: 7`、`EDE: 9` | DNS（DNSSEC） | `dig +cd` 對照 | D.9 |
| `Connection refused`、111、61 | TCP（對方主機在，沒人聽） | `ss -ltnp`、`nc -vz` | D.7、D.12 |
| `Connection timed out`、110、60 | TCP 或網路（封包沒回應） | 在目標抓 SYN、security group | D.7、D.12 |
| `Connection reset by peer`、104、54、`RemoteDisconnected` | TCP（收到 RST） | 兩端 tcpdump、閒置逾時是否一致 | D.7、D.12 |
| `Too many open files` | 本機資源 | `ss state close-wait`、`lsof -p` | D.12 |
| `CERTIFICATE_VERIFY_FAILED` | TLS（本機驗證） | `openssl s_client -servername … -showcerts` | D.10 |
| `TLSV1_ALERT_…`、`SSLV3_ALERT_…` | TLS（對方送 alert） | 是誰送的 alert | D.10 |
| `WRONG_VERSION_NUMBER` | TLS 打到明文 port | port 與 scheme | D.10 |
| 400、413、431 | HTTP 請求本身 | 哪一層回的：nginx、gunicorn、app | D.5 |
| 401、403、429 | 驗證、授權、限速 | `WWW-Authenticate`、scope、限速器看到的 IP | D.5 |
| 421、425 | 連線重用、0-RTT | 憑證涵蓋範圍、`Early-Data` | D.5 |
| 499 | nginx 的 client 先離開 | 前一層的逾時 | D.6、D.7 |
| 502、504 | proxy 與上游之間 | nginx error log 的原因字串 | D.7 |
| 503 | LB、nginx 限速、app 降載 | 回應 header 與哪一層的 log 有紀錄 | D.5、D.7 |
| 52x | CDN 與 origin 之間 | origin 的可達性與憑證 | D.6 |
| WebSocket 1006 | 路徑上某層切斷 | 斷線前閒置秒數、心跳、`proxy_read_timeout` | D.8 |
| WebSocket 1009 | 應用層訊息上限 | 訊息大小、前端重送邏輯 | D.8 |
| ICE failed、701 | 網路（UDP、TURN） | candidate-pair、relay candidate | D.11 |
| TURN 403 | TURN 政策 | `allowed-peer-ip` | D.11 |
| `connectionState` failed、ICE connected | DTLS | fingerprint、setup | D.11 |
| `play()` 的 `NotAllowedError` | 瀏覽器播放政策 | 前端是否處理 rejection | D.11 |

這張表的順序和封包的旅程相同：名字、連線、加密、HTTP、長連線、影音。值班時沿著這個順序往下問，每一列都是一個能用一個指令回答的是非題；越早排除下面幾層，越不會在 Flask 的 log 裡搜尋一個根本沒有到達 Flask 的請求（第 45 章）。
