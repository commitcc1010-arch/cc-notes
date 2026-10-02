# 《從封包到即時影音：工程師的網路全書》章節大綱

每一列：章｜檔名｜標題｜類型｜Q&A 數｜必須涵蓋。

貫穿案例 **聲聲 Live**：一個線上語言家教平台。學生在網頁上預約、付款、和老師即時視訊上課（WebRTC），教室裡有聊天與白板（WebSocket），熱門講座用專業設備推流直播給上千人（SRT → 轉封裝 → LL-HLS／WebRTC）。後端是 Python（Flask／Werkzeug 的 WSGI 服務，加上 ASGI 的即時服務），部署在雲端，前面有 CDN、load balancer 與 nginx。人物：剛入職的 junior 後端工程師小晴（會寫 Python 與 Flask，但沒碰過網路底層）、資深網路／平台工程師阿德（mentor）、負責影音的工程師 Joe、資安工程師 Rita。每章從聲聲 Live 遇到的一個真實問題開場。

全書程式碼：Python 3.11+、只用標準函式庫，在 localhost 上可離線執行（socket、asyncio、http.server、wsgiref、ssl、hmac、hashlib、struct）；第三方套件（Werkzeug、Flask、aiortc 等）與需要真實網路或 root 權限的指令，以 `# not-runnable` 或「示意輸出」標記。

## Part 0　起點（`Part 0 - 起點/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 1 | 01 - 打開一個網頁發生了什麼.md | 打開一個網頁發生了什麼：全書地圖 | concept | 8 | 從輸入 URL 到畫面出現的完整旅程（URL 解析、DNS、TCP、TLS、HTTP、伺服器處理、回應、渲染、後續請求）；每一站對應的章節；延遲從哪裡來的第一張時間軸；聲聲 Live 的系統全貌與人物；全書讀法 |
| 2 | 02 - 分層與封包.md | 分層與封包：網路是怎麼疊起來的 | concept | 8 | 為什麼要分層；OSI 七層與 TCP/IP 四層；封裝與解封裝；frame／packet／segment／message 的名稱；header 長什麼樣（用 Python 組出並解析一個 IPv4＋UDP 封包的 bytes）；byte order；MTU 與 payload；協定、規格與 RFC 怎麼讀 |
| 3 | 03 - 網路工程師工具箱.md | 網路工程師的工具箱 | concept | 8 | ping、traceroute／mtr、dig／nslookup、curl（-v、--resolve、-w timing）、nc、ss／netstat、lsof、tcpdump 與 Wireshark（過濾語法、讀一次 TCP 交握）、openssl s_client、瀏覽器 DevTools Network 面板與 HAR；每個工具回答什麼問題；判斷流程 |

## Part 1　從網卡到路由（`Part 1 - 網卡到路由/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 4 | 04 - Ethernet ARP 與交換器.md | Ethernet、MAC、ARP 與交換器 | concept | 8 | Ethernet frame 結構；MAC 位址；交換器的學習與轉送；廣播網域；ARP 流程與快取；VLAN；Wi-Fi 與有線的差異（概念層級）；同網段與跨網段通訊的差別 |
| 5 | 05 - IP 位址與子網.md | IP 位址、子網與 CIDR | concept | 8 | IPv4 位址結構；子網遮罩與 CIDR 計算（手算算例）；私有位址；特殊位址（loopback、link-local、broadcast）；IPv6 位址格式、縮寫、SLAAC、dual stack；用 Python ipaddress 模組計算 |
| 6 | 06 - 路由.md | 路由：封包怎麼找到路 | concept | 8 | routing table 與 longest prefix match；default gateway；靜態與動態路由；網際網路的結構（AS、ISP、IXP）；BGP 的概念與事故案例；anycast；traceroute 的原理與解讀 |
| 7 | 07 - NAT 與防火牆.md | NAT、Port Forwarding 與防火牆 | concept | 8 | 為什麼需要 NAT；SNAT／DNAT；連線追蹤表；NAT 類型（full cone、restricted、symmetric）與 P2P 的關係（為第 36 章鋪路）；CGNAT；port forwarding；stateful 防火牆；security group 的概念 |
| 8 | 08 - ICMP MTU 與分片.md | ICMP、MTU 與分片 | concept | 8 | ICMP 訊息類型；ping 的原理；MTU、分片與重組；Path MTU Discovery 與黑洞；MSS clamping；VPN／隧道造成的 MTU 問題；聲聲 Live 大封包消失的事故 |

## Part 2　傳輸層（`Part 2 - 傳輸層/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 9 | 09 - UDP 與 Socket.md | Port、UDP 與 Socket API | build | 8 | port 與五元組；UDP header 與語意（無連線、不可靠、保留訊息邊界）；Berkeley socket API（socket、bind、sendto、recvfrom）；用 Python 寫 UDP echo 與丟包模擬；UDP 適合的場景（DNS、影音、遊戲、QUIC） |
| 10 | 10 - TCP 連線.md | TCP 連線：交握、狀態與關閉 | build | 8 | TCP header；三向交握與 ISN；狀態機（LISTEN、SYN_SENT、ESTABLISHED、FIN_WAIT、TIME_WAIT、CLOSE_WAIT）；四次揮手與 RST；backlog、accept queue；TIME_WAIT 與 CLOSE_WAIT 堆積的成因；用 Python 寫 TCP server／client 並用 ss 觀察狀態 |
| 11 | 11 - TCP 可靠傳輸.md | TCP 可靠傳輸：序號、重傳與視窗 | build | 8 | byte stream 與訊息邊界（framing）；序號與 ACK；重傳（RTO、fast retransmit、SACK）；滑動視窗與流量控制；Nagle 與 delayed ACK；keepalive；用 Python 模擬 Go-Back-N 與 selective repeat |
| 12 | 12 - 擁塞控制.md | 擁塞控制與 Head-of-Line Blocking | build | 8 | 為什麼需要擁塞控制；slow start、congestion avoidance、AIMD；Reno、CUBIC、BBR 的概念；bufferbloat；bandwidth-delay product；head-of-line blocking 在 TCP 與 HTTP 的兩種形式；用 Python 模擬 cwnd 變化 |
| 13 | 13 - QUIC.md | QUIC：建在 UDP 上的新傳輸層 | concept | 8 | 為什麼 TCP 難以演進（ossification）；QUIC 的 stream、connection ID、加密內建、1-RTT 與 0-RTT、connection migration、loss recovery；QUIC 與 TLS 1.3 的整合；UDP 被封鎖時的 fallback；部署現況（2026） |

## Part 3　名稱解析（`Part 3 - DNS/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 14 | 14 - DNS 基礎.md | DNS 基礎：從網域名稱到 IP | build | 8 | DNS 的階層（root、TLD、authoritative）；stub resolver、recursive resolver；遞迴與迭代查詢的完整流程圖；record types（A、AAAA、CNAME、MX、TXT、NS、SOA、SRV、CAA、HTTPS／SVCB）；TTL 與快取；DNS 訊息格式；用 Python 手組 DNS query 並解析回應（對本機假的 DNS server） |
| 15 | 15 - DNS 進階與故障.md | DNS 進階：負載、安全與常見故障 | concept | 8 | CNAME 限制與 apex／ALIAS；DNS 負載分散、GeoDNS、health check；DNS 改變的傳播與 TTL 策略；negative caching；DNSSEC 原理；DoH、DoT；split-horizon DNS；DNS 劫持與 cache poisoning 的防禦；常見故障（NXDOMAIN、SERVFAIL、搬家後還連舊 IP） |
| 16 | 16 - 系統內的名稱解析.md | 系統內的名稱解析與服務發現 | concept | 8 | /etc/hosts、resolv.conf、nsswitch、search domain 與 ndots；應用程式與語言 runtime 的 DNS 快取；容器與 Kubernetes 的 DNS（CoreDNS、service 名稱）；服務發現模式；DNS 驗證網域所有權（ACME DNS-01、TXT 驗證） |

## Part 4　安全傳輸（`Part 4 - 安全傳輸/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 17 | 17 - 密碼學基礎.md | 給工程師的密碼學基礎 | build | 8 | 機密性、完整性、真實性；對稱加密（AES-GCM 概念）、非對稱（RSA、ECC）、hash、HMAC、數位簽章、金鑰交換（Diffie-Hellman 手算小例子）、隨機數；不要自己發明密碼學；用 Python hashlib／hmac／secrets 示範 |
| 18 | 18 - TLS.md | TLS 1.3：交握、憑證與信任 | build | 8 | TLS 解決什麼問題；TLS 1.3 交握逐步解析；憑證、憑證鏈與 CA；憑證驗證步驟（名稱、期限、簽章、撤銷）；SNI、ALPN；session resumption 與 0-RTT 的風險；mTLS；ECH 現況；用 openssl s_client 與 Python ssl 檢查憑證 |
| 19 | 19 - 憑證營運與 HTTPS 部署.md | 憑證營運與 HTTPS 部署 | concept | 8 | ACME 與 Let's Encrypt（HTTP-01、DNS-01）；憑證自動更新與到期事故；憑證輪替；HSTS 與 preload；Certificate Transparency；TLS 終結的位置（CDN、LB、應用）；常見錯誤（中間憑證缺漏、名稱不符、時鐘錯誤）與除錯 |

## Part 5　HTTP 與 Web（`Part 5 - HTTP 與 Web/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 20 | 20 - HTTP 1.1.md | HTTP/1.1：請求與回應 | build | 8 | 請求行、header、body；method 語意（safe、idempotent）；status code 家族；Host header；keep-alive 與連線重用；Content-Length 與 chunked；用 Python socket 手寫一個 HTTP 請求並解析回應；用 http.server 觀察 |
| 21 | 21 - HTTP 快取與語意.md | HTTP 快取、Cookie 與內容協商 | build | 8 | Cache-Control、ETag、Last-Modified、條件請求、304；private／shared cache；Vary；content negotiation；壓縮（gzip、br）；Range 請求；cookie 的語法與屬性；redirect 種類；用 Python 實作條件請求的 server |
| 22 | 22 - HTTP2 與 HTTP3.md | HTTP/2 與 HTTP/3 | concept | 8 | HTTP/1.1 的效能限制與 workaround；HTTP/2 的 binary framing、stream、multiplexing、HPACK、flow control、server push 的退場；HTTP/3 over QUIC 與 QPACK；連線合併；何時升級有效、何時沒差；用 Python 解析 HTTP/2 frame header |
| 23 | 23 - 瀏覽器安全模型.md | 瀏覽器安全模型：Same-Origin、CORS 與 CSP | build | 8 | origin 的定義；same-origin policy；CORS（simple 與 preflight 請求、credentials）的完整流程；cookie 的 SameSite、Secure、HttpOnly、Domain、Path；CSRF 與防禦；XSS 類型與 CSP；clickjacking 與 frame-ancestors；只談防禦；用 Python 寫一個 CORS 正確的 API server |
| 24 | 24 - API 風格.md | API 風格：REST、gRPC 與 GraphQL | concept | 8 | REST 的資源與語意設計、版本化、分頁、錯誤格式；idempotency key；gRPC 與 protobuf（建在 HTTP/2 上、streaming、deadline）；GraphQL 的取捨；webhook；選型比較表 |
| 25 | 25 - Proxy LB 與 CDN.md | Proxy、Load Balancer 與 CDN | build | 8 | forward 與 reverse proxy；L4 與 L7 load balancer；負載分散演算法；health check；sticky session；X-Forwarded-For／Forwarded 與信任邊界；CDN 的運作（edge、cache key、purge、origin shield）；API gateway；用 Python asyncio 寫一個簡單的 L7 reverse proxy |

## Part 6　身分驗證與授權（`Part 6 - 驗證與授權/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 26 | 26 - Authentication 基礎.md | Authentication 基礎：密碼、Session 與 MFA | build | 8 | authentication 與 authorization 的差別；密碼儲存（salt、bcrypt、scrypt、argon2；用 hashlib.scrypt 示範）；server-side session 與 session cookie；session fixation 與輪替；登入限速與帳號鎖定；MFA（TOTP 原理與 Python 實作、WebAuthn 預告）；忘記密碼流程 |
| 27 | 27 - JWT.md | Token 與 JWT | build | 8 | opaque token vs self-contained token；JWT 結構（header、payload、signature）與 base64url；HS256 vs RS256／ES256；驗證步驟清單（alg、簽章、exp、nbf、iss、aud）；JWKS 與金鑰輪替；撤銷與短效 token＋refresh token；JWT 放在 cookie 還是 header；常見錯誤（alg none、混淆、沒驗 aud）與防禦；用 Python 標準函式庫實作 HS256 簽發與驗證 |
| 28 | 28 - OAuth 2.md | OAuth 2.0 與 2.1 | build | 8 | OAuth 解決什麼問題（委派授權）；角色（resource owner、client、authorization server、resource server）；authorization code＋PKCE 完整流程圖；client credentials；refresh token 與輪替；scope 與 consent；redirect URI 驗證；state 參數；2.1 移除的流程；用 Python 模擬完整的 PKCE 流程 |
| 29 | 29 - OIDC SSO 與 Passkeys.md | OpenID Connect、SSO 與 Passkeys | build | 8 | OIDC 在 OAuth 上加了什麼（ID token、userinfo、discovery）；SSO 的運作；SAML 概念對照；企業 IdP 整合；logout 的難題；passkeys／WebAuthn 的原理（公私鑰、challenge、origin 綁定）與流程；用 Python 模擬 ID token 驗證 |
| 30 | 30 - Service 之間的驗證.md | Service 之間的驗證與簽章 | build | 8 | API key 的設計與輪替；HMAC 請求簽章與 webhook 驗證（timestamp、replay 防護）；mTLS 與 service mesh；workload identity（SPIFFE 概念、雲端 IAM role）；secrets 管理；用 Python 實作 webhook 簽章與驗證 |

## Part 7　即時通訊（`Part 7 - 即時通訊/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 31 | 31 - 從 Polling 到 SSE.md | 從 Polling 到 Server-Sent Events | build | 8 | short polling、long polling、SSE 的原理與比較；SSE 的格式、重連與 Last-Event-ID；HTTP/2 對 SSE 的影響；proxy 緩衝問題；用 Python 寫 SSE server |
| 32 | 32 - WebSocket.md | WebSocket 深入 | build | 8 | upgrade handshake（Sec-WebSocket-Key／Accept 的計算）；frame 格式（FIN、opcode、mask、payload length）；masking 的理由；ping／pong、close code；subprotocol 與 extension；認證方式；用 Python asyncio 從零實作 WebSocket server 與 client（含 frame 編解碼） |
| 33 | 33 - 即時系統設計.md | 即時系統設計：規模化 WebSocket | design | 8 | 連線數與記憶體估算；sticky session 與 LB 設定（timeout、upgrade）；pub/sub fan-out（Redis 等概念）；presence；訊息順序、去重與 at-least-once；重連與補發；backpressure；聲聲 Live 教室聊天的架構設計 |

## Part 8　即時影音（`Part 8 - 即時影音/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 34 | 34 - 影音基礎與 RTP.md | 影音基礎：Codec、延遲與 RTP | build | 8 | 取樣、frame、GOP、I／P／B frame；codec（H.264、VP8／VP9、AV1、Opus、AAC）與 container；bitrate 與解析度；延遲的組成（擷取、編碼、網路、jitter buffer、解碼）；RTP／RTCP header 與 sequence、timestamp、SSRC；用 Python 組 RTP 封包並模擬 jitter buffer |
| 35 | 35 - SDP.md | SDP：媒體協商的語言 | build | 8 | SDP 的結構（session 與 media section）；逐行解讀 v、o、s、c、t、m、a 行；rtpmap、fmtp、ssrc、mid、bundle、rtcp-mux、ice-ufrag、fingerprint、setup；offer／answer 模型；codec 協商；Unified Plan；用 Python 解析真實的 WebRTC SDP 並協商出共同 codec |
| 36 | 36 - WebRTC 連線.md | WebRTC 連線：ICE、STUN、TURN 與 DTLS-SRTP | build | 8 | 為什麼 P2P 很難（NAT 類型，接第 7 章）；signaling 不在 WebRTC 規格內；ICE candidates（host、srflx、relay）；STUN 原理與訊息格式；TURN 中繼；ICE 連線檢查與 trickle ICE；DTLS 交握與 SRTP；data channel（SCTP）；完整建立流程時序圖；用 Python 實作 STUN binding request 的編解碼（對本機假 server） |
| 37 | 37 - WebRTC 規模化.md | WebRTC 規模化：Mesh、SFU 與 MCU | design | 8 | mesh、SFU、MCU 的架構與成本比較；simulcast 與 SVC；頻寬估計與 congestion control（GCC 概念、TWCC）；NACK、PLI、FEC；TURN 的成本與部署；聲聲 Live 一對一與小班課的架構；getStats 的關鍵指標 |
| 38 | 38 - 直播協定與 SRT.md | 直播協定：RTMP、SRT、HLS 與 WHIP | build | 8 | 直播的端到端管線（ingest、轉碼、封裝、分發）；RTMP；SRT 原理（UDP 上的 ARQ、latency 參數與重傳視窗、caller／listener／rendezvous、AES 加密、stream ID）；HLS 與 DASH（segment、playlist）、LL-HLS；WHIP／WHEP；延遲與穩定性的取捨表；用 Python 模擬 SRT 式的 ARQ 與 latency 視窗 |
| 39 | 39 - 影音品質與除錯.md | 影音品質與除錯 | concept | 8 | 品質指標（丟包、jitter、RTT、frame rate、freeze）；常見問題（單向無聲、黑畫面、卡頓、回音）與根因；chrome://webrtc-internals 與 getStats 解讀；TURN 與防火牆問題；直播卡頓的分段排查；聲聲 Live 一次上課卡頓的除錯紀錄 |

## Part 9　Python 的 Web 伺服器堆疊（`Part 9 - Python Web 堆疊/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 40 | 40 - 從 Socket 寫 HTTP Server.md | 從 Socket 寫一個 HTTP Server | build | 8 | 用 socket 從零寫 HTTP server（解析 request、產生 response、keep-alive）；並行模型（iterative、thread、process、select／epoll、asyncio）的比較與實作；C10K 問題；timeout 與資源限制 |
| 41 | 41 - WSGI 與 Werkzeug.md | WSGI 與 Werkzeug | build | 8 | WSGI 為什麼存在；規格（environ、start_response、iterable、PEP 3333）；用 wsgiref 寫 WSGI app 與 middleware；Werkzeug 的角色（Request／Response 包裝、routing、dev server、reloader、interactive debugger 與為何不能上 production）；Flask 如何建在 Werkzeug 上；一個請求從 socket 到 Flask view 的完整路徑 |
| 42 | 42 - ASGI 與 Async 伺服器.md | ASGI 與 Async 伺服器 | build | 8 | WSGI 的限制（長連線、WebSocket）；ASGI 規格（scope、receive、send、lifespan）；uvicorn、Starlette、FastAPI 的分層；WebSocket over ASGI；用 asyncio 實作一個最小 ASGI server 與 app |
| 43 | 43 - 部署與 Application Server.md | 部署：Gunicorn、Uvicorn 與 Nginx | concept | 8 | application server 與 reverse proxy 的分工；gunicorn 的 worker 模型（sync、gthread、uvicorn worker）與數量估算；timeout 鏈（client、LB、nginx、gunicorn、app）；keep-alive 設定；X-Forwarded-* 與 ProxyFix；graceful shutdown 與 zero-downtime deploy；靜態檔案；常見部署錯誤 |

## Part 10　雲端、營運與整合（`Part 10 - 營運與整合/`）

| 章 | 檔名 | 標題 | 類型 | Q&A | 必須涵蓋 |
|---|---|---|---|---|---|
| 44 | 44 - 雲端與容器網路.md | 雲端與容器網路 | concept | 8 | VPC、subnet、route table、internet／NAT gateway、security group 與 NACL；private link；容器網路（bridge、veth、overlay）；Kubernetes 網路模型（Pod IP、Service、kube-proxy、Ingress、Gateway API）；service mesh 概念；聲聲 Live 的雲端網路圖 |
| 45 | 45 - 網路除錯實戰.md | 網路除錯實戰：從症狀到根因 | concept | 8 | 分層排查法；八個事故案例（DNS 解析失敗、TLS 憑證錯誤、連線逾時 vs 被拒、間歇性 reset、慢、CORS 錯誤、WebSocket 斷線、視訊單向）的診斷流程圖與工具；症狀到章節對照表 |
| 46 | 46 - 網路效能與系統設計.md | 網路效能與系統設計整合 | design | 8 | 延遲預算與 critical path；連線重用、預連線、CDN、壓縮、HTTP/2／3；容量估算；把全書串起來：完整設計聲聲 Live 的網路架構（web、API、auth、即時聊天、視訊、直播、雲端），以 system design interview 形式走一遍；常見網路面試題 |

## 附錄（`Appendices/`）

| 檔名 | 內容 |
|---|---|
| A - 術語表.md | 全書術語（英文、中文、一句話定義、首次出現章） |
| B - 工具指令速查.md | dig、curl、openssl、tcpdump、ss、nc、traceroute、Wireshark 過濾、瀏覽器工具等常用指令與情境 |
| C - 協定格式速查.md | IPv4／IPv6、TCP、UDP、DNS、TLS record、HTTP/2 frame、WebSocket frame、RTP、STUN 的 header 圖；JWT claims；SDP 常見行；WSGI environ 與 ASGI scope 欄位 |
| D - Port 與 Status Code 速查.md | 常見 port、HTTP status code、WebSocket close code、DNS rcode、TLS alert |
| E - 學習路線.md | 依角色（後端、前端、SRE、影音、資安）與目標（面試、工作）的讀法與練習 |
| F - 延伸閱讀.md | 重要 RFC 與規格清單、經典書籍與官方文件，依主題整理（只列名稱與編號，不放 URL） |
