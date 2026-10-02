# 附錄 E　學習路線

> [!abstract] 本附錄地圖
> **用途**：把全書 46 章排成可以照著走的路線。你可以依角色（後端、前端、SRE／平台、影音與即時互動、資安）挑一條路線，也可以依眼前的目標（四週入門、兩週面試衝刺、上線前檢查與值班準備）挑一份計畫；讀完一段之後，用 E.4 的實作專案把知識變成作品，用 E.5 的題組確認自己真的會了。
>
> **怎麼查**：
> - 第一次打開本附錄，先讀 E.1，它說明表格裡「精讀」「略讀」「必做」的意思，以及時間怎麼估。
> - 有明確的職務，看 E.2 對應的路線；有明確的期限，看 E.3；想做一個能放進作品集的東西，看 E.4。
> - 每讀完一個 Part，做 E.5 該 Part 的 5 題；答不出來的題目後面都標了章節，回去重讀那一節即可。
> - 路線與導讀的「怎麼讀」一致，面試題對應第 46 章 46.18 節，症狀對照對應第 45 章 45.12 節；本附錄只負責排順序與定驗收標準，不重複正文的解釋。

## E.1 如何使用

這本書的前四個 Part（第 1–19 章）是地基，Part 5（第 20–25 章）把地基組成 Web，後面的 Part 則依工作內容分岔。導讀已經給了一句話版本的讀法；本附錄把那幾句話展開成可以排進行事曆的表格：每一章讀到什麼程度、哪一段動手做一定要自己跑、花多少時間、讀完要能做到什麼。

```text
                         ┌──────────── 共同地基 ────────────┐
                         │ Part 0  起點（1–3）               │
                         │ Part 1  網卡到路由（4–8）          │
                         │ Part 2  傳輸層（9–13）             │
                         │ Part 3  DNS（14–16）               │
                         │ Part 4  安全傳輸（17–19）          │
                         │ Part 5  HTTP 與 Web（20–25）       │
                         └───────────────┬──────────────────┘
          ┌──────────────┬───────────────┼────────────────┬──────────────┐
          ▼              ▼               ▼                ▼              ▼
     後端（E.2.1）   前端（E.2.2）   SRE／平台（E.2.3） 影音（E.2.4）   資安（E.2.5）
     Part 6、9       第 23、26–29、   Part 1–4 讀熟     第 7、9、12、13 第 17–19、23、
     第 44、45 章    31、32 章        第 25、43–46 章   Part 7、Part 8  26–30、44 章
          └──────────────┴───────────────┼────────────────┴──────────────┘
                                         ▼
                         第 45 章（除錯實戰）→ 第 46 章（系統設計）
```

這張圖由上往下讀。上方的方框是所有路線共用的地基，不同路線只差在哪些章精讀、哪些章略讀；中間五條分支是 E.2 的五條角色路線，每條都會再回到第 45 章與第 46 章，因為除錯與系統設計是每個角色都要面對的工作。前端與影音路線允許跳過部分地基章節，代價是遇到相關事故時要回頭補讀，這一點在各路線的表格中都會註明。

表格中的幾個用語意思如下：

| 用語 | 意思 | 預估時間（每章） |
|---|---|---|
| 精讀 | 從故事讀到延伸問答，每張圖跟著文字走一遍，跑動手做並改一個參數，做至少兩題動手練習（其中一題用真實工具） | 3–5 小時 |
| 略讀 | 讀本章地圖、故事、各節開頭與「常見錯誤與除錯」表，看懂本章重點整理的每一句 | 約 1 小時 |
| 必做 | 指名的動手做小節，一定要在自己的電腦上執行一次，並能說出輸出的每一行代表什麼 | 已含在精讀時間內 |
| 能力檢核 | 讀完路線後應該能獨立完成的事，以「能做到」的句子描述，可以直接拿來自評或讓 mentor 驗收 | — |

時間是參考值，假設讀者符合導讀描述的背景：會寫 Python、用過 Flask、對網路底層只有零碎概念。build 類章節（動手做較長）偏向上限，concept 類章節偏向下限；第一次接觸密碼學、影音或 Kubernetes 的人，第 17、34、44 章請多抓一點時間。每章的動手做只用標準函式庫，全部在 127.0.0.1 上離線執行，所以通勤或出差時也能照表進行；需要真實網路的觀察（dig、curl、tcpdump、DevTools）則留到有網路的時候集中做。

讀路線時有三個習慣值得養成。第一，每章開頭的「前置知識」比本附錄的順序更權威：如果路線跳過某章，而你讀的那一章把它列為前置，就先補那一章的略讀。第二，每章的「常見錯誤與除錯」表要特別留意，它是第 45 章大表的原料，也是值班時最先翻的地方。第三，讀完一個 Part 立刻做 E.5 的題組，隔一週再做一次；第二次還答不出來的題目，才是真正需要重讀的地方。

## E.2 依角色的路線

### E.2.1 後端工程師

後端工程師是本書的預設讀者，路線最長，也最接近照順序讀。依導讀的建議：Part 0–5 之後，優先讀 Part 6（驗證與授權）與 Part 9（Python Web 堆疊），再讀第 44、45 章。Part 0–5 裡和後端日常最相關的章節精讀，其餘略讀。

| 階段 | 章 | 程度 | 本章重點 | 必做的動手做 | 時間 |
|---|---|---|---|---|---|
| 地基 | 1 | 精讀 | 九站旅程、每站的 RTT、應用程式 log 只看得到最後一層 | 1.14 用 Python 手動打開一個網頁 | 3 h |
| 地基 | 2 | 略讀 | 封裝、header 長度、big-endian 與 `struct` 的 `!` | — | 1 h |
| 地基 | 3 | 精讀 | 每個工具替哪一層作證；`curl -w`、`--resolve`、`ss`、tcpdump | 3.12 迷你 curl -w 與 TCP port 檢查器 | 4 h |
| 地基 | 4–8 | 略讀 | ARP 問下一跳、CIDR、longest prefix match、NAT 與 security group、PMTUD 黑洞 | — | 5 h |
| 地基 | 9 | 略讀 | UDP 無連線、保留訊息邊界、每個 recvfrom 都要 timeout | — | 1 h |
| 地基 | 10 | 精讀 | 三向交握、accept queue、TIME_WAIT 與 CLOSE_WAIT、refused 與 timeout | 10.11 在 127.0.0.1 上觀察 TCP 的一生 | 5 h |
| 地基 | 11 | 精讀 | byte stream 沒有訊息邊界、framing、Nagle 與 delayed ACK 的 40 ms | 11.9 黏包、length-prefix framing 與 TCP_NODELAY | 4 h |
| 地基 | 12、13 | 略讀 | BDP、slow start、兩種 HOL；QUIC 的 1-RTT、0-RTT 與 migration | — | 2 h |
| 地基 | 14 | 精讀 | 遞迴與迭代、record types、TTL 與搬遷、RCODE | 14.10 假的權威 DNS server、手組 client 與 TTL 快取 | 4 h |
| 地基 | 15 | 略讀 | 負面快取、apex 與 CNAME、DNSSEC 與 DoH 的分工 | — | 1 h |
| 地基 | 16 | 精讀 | `getaddrinfo`、resolv.conf、ndots、長連線不會重新解析 | 16.10 數 ndots 造成的請求、修正長連線 | 3 h |
| 地基 | 17 | 略讀 | HMAC 對原始 bytes、`compare_digest`、`secrets` | — | 1 h |
| 地基 | 18 | 精讀 | TLS 1.3 交握、憑證驗證步驟、SNI、0-RTT 規則 | 18.12 手組 ClientHello、看交握、驗憑證 | 5 h |
| 地基 | 19 | 精讀 | ACME、到期監控、逐台副本驗證、HSTS | 19.12 到期監控、ACME challenge 與 HSTS | 3 h |
| 地基 | 20 | 精讀 | method 語意、body 長度規則、keep-alive 競態、smuggling 防禦 | 20.10 用 socket 手寫 HTTP/1.1 client | 4 h |
| 地基 | 21 | 精讀 | private 與 shared cache、條件請求、`Vary`、cookie 屬性 | 21.11 條件請求、shared cache 與事故重現 | 4 h |
| 地基 | 22 | 略讀 | HTTP/2 frame 與多工、HTTP/3 在何時有效 | — | 1 h |
| 地基 | 23 | 精讀 | origin、CORS 與 preflight、SameSite、CSRF、CSP | 23.11 在 127.0.0.1 上實作瀏覽器的安全規則 | 4 h |
| 地基 | 24 | 精讀 | REST 語意、idempotency key、Problem Details、deadline | 24.11 付款 API、手工 protobuf 與 N+1 | 4 h |
| 地基 | 25 | 精讀 | L4 與 L7、health check、XFF 信任邊界、CDN cache key | 25.10 用 asyncio 寫一個 L7 reverse proxy | 5 h |
| 驗證 | 26–30 | 精讀 | 密碼雜湊與 session、JWT 驗證清單、PKCE、OIDC、webhook 簽章與去重 | 26.10、27.10、28.15、30.9 | 20 h |
| Python 堆疊 | 40–43 | 精讀 | 並行模型、WSGI 規格與 Werkzeug、ASGI、timeout 鏈與優雅關機 | 40.10、41.16、42.11、43.11 | 16 h |
| 營運 | 44、45 | 精讀 | VPC、security group、Kubernetes Service；分層排查與八個案例 | 44.15、45.13 | 8 h |
| 選讀 | 31–33、46 | 略讀 | 即時推送的選型、WebSocket 擴展、延遲預算與容量估算 | — | 4 h |

全程約 110–120 小時。以每週 10 小時計，大約三個月；以每週 15 小時計，大約兩個月。驗證與 Python 堆疊兩段最值得投資，因為後端的大部分事故（連線池、timeout、502、token 驗證漏洞）都發生在這裡。

讀完後端路線，應該能做到：

- 用 `curl -w` 把一個慢請求切成 DNS、交握、TLS、TTFB、下載五段，並說出每段可能的原因與對應章節。
- 看 `ss -tan` 的輸出判斷 CLOSE_WAIT 是哪一端的程式沒有 close，並在 Python 程式中修好。
- 為一個 API 設計 status code、錯誤格式、idempotency key 與分頁，並說明哪些請求可以自動重試。
- 寫出 JWT 的完整驗證清單，說明 5 分鐘 access token 加 14 天可輪替 refresh token 的理由。
- 從頭說出一個請求從 nginx、gunicorn、WSGI 到 Flask view 的路徑，並設定一條外長內短的 timeout 鏈。
- 用 `curl --resolve` 繞過 CDN 直打 LB，分辨問題在 CDN 之前還是之後。

### E.2.2 前端工程師

前端工程師最常碰到的網路問題都在瀏覽器裡發生：CORS 錯誤、cookie 沒帶上、快取沒更新、登入迴圈、即時連線斷線。導讀列出的核心章節是第 1、3、14、18、20–23、26–29、31、32 章，本路線依這個清單排順序，並把 DevTools 的練習放在最前面。

| 階段 | 章 | 程度 | 本章重點 | 必做的動手做 | 時間 |
|---|---|---|---|---|---|
| 地圖 | 1 | 精讀 | 頁面載入的依賴鏈、每個新網域都要重新握手 | 1.14 | 3 h |
| 工具 | 3 | 精讀 | DevTools Timing 與 `curl -w` 一一對應、HAR 要去敏感化 | 3.12 | 3 h |
| 名稱 | 14 | 精讀 | TTL 與快取、CNAME、為什麼改了 DNS 有人還在舊站 | 14.10 | 3 h |
| 安全傳輸 | 18 | 精讀 | 憑證錯誤的種類、SNI 與 ALPN、0-RTT 的限制 | 18.12 | 3 h |
| HTTP | 20 | 精讀 | method 語意、status code 家族、keep-alive | 20.10 | 4 h |
| HTTP | 21 | 精讀 | `Cache-Control`、ETag 與 304、帶雜湊檔名的長期快取、cookie 屬性、redirect 種類 | 21.11 | 4 h |
| HTTP | 22 | 精讀 | HTTP/2 下 domain sharding 與合併檔案變成負擔、preload 與 103 Early Hints | 22.15 frame、HPACK、載入模擬 | 4 h |
| 瀏覽器 | 23 | 精讀 | same-origin、CORS 與 preflight、SameSite、CSRF、XSS 與 CSP、clickjacking | 23.11 | 5 h |
| 驗證 | 26 | 略讀 | 401 與 403、session cookie、MFA | — | 1 h |
| 驗證 | 27 | 精讀 | JWT 不加密、token 放 cookie 還是 header、BFF | 27.10 | 4 h |
| 驗證 | 28 | 精讀 | authorization code＋PKCE、state、SPA 優先採 BFF | 28.15 | 4 h |
| 驗證 | 29 | 精讀 | OIDC 的 ID token、SSO 與 logout 的難題、passkeys 為什麼防釣魚 | 29.13 | 4 h |
| 即時 | 31 | 精讀 | polling、long polling、SSE、EventSource 的重連與 Last-Event-ID | 31.12 | 3 h |
| 即時 | 32 | 精讀 | Upgrade 握手、close code 與重連策略、Origin 檢查與 ticket | 32.13 | 5 h |
| 選讀 | 24、25、46 | 略讀 | API 錯誤格式與分頁、CDN 與快取鍵、延遲預算與 critical path | — | 3 h |

全程約 50–55 小時，是五條路線中最短的。省下的時間建議用在 E.4 的專案四（OAuth＋PKCE 登入）與專案五（WebSocket 聊天室），這兩個專案的前端部分正好就是前端工程師的日常工作。跳過的 Part 1、Part 2 會在第 23 章以後偶爾被引用；遇到「閒置逾時」「RST」這類詞時，回頭略讀第 7、10 章即可。

讀完前端路線，應該能做到：

- 看到 Console 的 CORS 錯誤時，先在 Network 面板確認真正的 status，再判斷是 preflight 被擋、缺 header、credentials 配 `*` 還是缺 `Vary: Origin`。
- 設計一套靜態資源的快取策略：HTML 短快取或重新驗證，帶雜湊檔名的 JS 與 CSS 一年加 `immutable`。
- 在 DevTools 的 Cookies 分頁說出某個 cookie 沒被送出的原因（SameSite、Secure、Domain、Path、第三方 cookie 政策）。
- 說明 SPA 為什麼優先採 BFF、token 放在 JavaScript 可讀的位置有什麼風險。
- 依 close code 寫出 WebSocket 的重連邏輯：哪些情況不重連、哪些用指數退避加 jitter。
- 用 `preconnect` 與資源合併的取捨，替一個頁面縮短 critical path。

### E.2.3 SRE 與平台工程師

SRE 與平台工程師要能在任何一層找出問題，所以導讀要求 Part 1–4 要讀熟，再讀第 25、43、44、45、46 章。「讀熟」的意思是能不看書回答 E.5 中 Part 1–4 的所有題目，並能在真實環境用工具驗證自己的回答。

| 階段 | 章 | 程度 | 本章重點 | 必做的動手做 | 時間 |
|---|---|---|---|---|---|
| 起點 | 1–3 | 精讀 | 九站旅程、分層與封裝、整套工具箱與判斷流程 | 2.10、3.12 | 10 h |
| 連結層 | 4 | 精讀 | 交換器學習、ARP 快取狀態、gratuitous ARP、VLAN | 4.12 模擬會學習的交換器與 ARP | 3 h |
| 位址 | 5 | 精讀 | CIDR 手算、對齊、VPC 子網規劃、Happy Eyeballs | 5.10 子網計算器與 VPC 子網切分工具 | 4 h |
| 路由 | 6 | 精讀 | longest prefix match、BGP 與 RPKI、anycast、traceroute 解讀 | 6.12 routing table 與 traceroute | 4 h |
| 邊界 | 7 | 精讀 | conntrack、NAT 類型、stateful 與 stateless、security group 與 NACL | 7.10 NAT 轉換表與防火牆規則引擎 | 4 h |
| MTU | 8 | 精讀 | PMTUD 黑洞的指紋、隧道的 MTU 開銷、MSS clamping、ICMP 政策 | 8.12 編解碼 ICMP、模擬分片與 PMTUD 黑洞 | 4 h |
| 傳輸 | 9–11 | 精讀 | UDP 語意、TCP 狀態機與 accept queue、重傳與視窗、keepalive | 9.8、10.11、11.6 | 13 h |
| 傳輸 | 12 | 精讀 | BDP、CUBIC 與 BBR、bufferbloat、用 `ss -ti` 分辨三種受限 | 12.10 在一個瓶頸上重現 cwnd 的一生 | 4 h |
| 傳輸 | 13 | 精讀 | QUIC 的 connection ID 與 LB、UDP 443、fallback 與可觀測性 | 13.12 | 4 h |
| DNS | 14–16 | 精讀 | 授權鏈、TTL 與搬遷、DNSSEC 事故、ndots 與 Kubernetes DNS | 14.11、15.12、16.10 | 12 h |
| 安全傳輸 | 17–19 | 精讀 | AEAD 與 HMAC、TLS 1.3、憑證驗證、ACME 與到期監控、TLS 終結位置 | 17.12、18.12、19.12 | 12 h |
| 入口 | 25 | 精讀 | L4 與 L7、負載演算法、health check 參數、draining、XFF、purge 與 origin shield | 25.10 | 5 h |
| 部署 | 43 | 精讀 | prefork、worker 數量估算、timeout 鏈與 keep-alive 方向、graceful shutdown | 43.11 | 4 h |
| 雲端 | 44 | 精讀 | VPC 路由、NAT gateway、PrivateLink、VXLAN 與 Pod MTU、Service 與 NetworkPolicy | 44.15 | 5 h |
| 除錯 | 45 | 精讀 | 分層排查、八個案例、症狀對照大表 | 45.13 寫一個網路診斷小工具 | 5 h |
| 設計 | 46 | 精讀 | 延遲預算、容量估算、失效模式與降級、安全邊界 | 46.14 頁面載入模型與容量估算器 | 5 h |
| 選讀 | 20–22、33、37 | 略讀 | HTTP 語意與 keep-alive、即時系統與 SFU 的容量與部署 | — | 5 h |

全程約 100–110 小時。這條路線的特色是 Part 1–4 一章都不略讀；這些章節講的機制（ARP、路由、conntrack、MTU、TCP 狀態、DNS 快取、憑證）幾乎不出現在應用程式的 log 裡，卻是 SRE 值班時最常追到的根因。

讀完 SRE 路線，應該能做到：

- 不查資料手算任意 IPv4 CIDR 的網路位址、廣播位址與可用主機數，並規劃不重疊的多 AZ VPC 網段。
- 在一台主機上用 `ip route get`、`ss -ltnp`、`nstat`、tcpdump 判斷封包停在哪一層。
- 從 tcpdump 的輸出讀出交握 RTT、MSS、視窗選項、誰送了 RST，並判斷是否為 PMTUD 黑洞。
- 寫出 DNS 搬遷的完整順序與等待時間，並說明 Kubernetes 上 5 秒 DNS 延遲的成因與緩解。
- 對每台副本逐一檢查憑證序號與剩餘效期，並依效期比例設定告警門檻。
- 為一條 CDN → LB → nginx → gunicorn → app → DB 的路徑寫出 timeout 鏈與 keep-alive 設定，並解釋每個數字。
- 主持一場故障演練（第 45 章 45.1），並把結果寫成值班手冊。

### E.2.4 影音與即時互動工程師

影音工程師的問題幾乎都在 UDP、NAT 與壅塞上，所以導讀的建議是第 7、9、12、13 章之後直接進 Part 7 與 Part 8。第 1–3 章仍建議快速讀過，因為後面的除錯都會用到它們的工具與時間軸。

| 階段 | 章 | 程度 | 本章重點 | 必做的動手做 | 時間 |
|---|---|---|---|---|---|
| 起點 | 1–3 | 略讀 | 全書地圖、封裝與 header、tcpdump 與 Wireshark | — | 3 h |
| NAT | 7 | 精讀 | mapping 與 filtering、symmetric NAT、hole punching、CGNAT | 7.10 NAT 轉換表與打洞模擬 | 4 h |
| MTU | 8 | 略讀 | 為什麼 UDP 協定保守地維持在約 1200 bytes | — | 1 h |
| UDP | 9 | 精讀 | UDP 語意、訊息邊界、socket 選項、在 UDP 上補可靠性 | 9.8 | 4 h |
| 壅塞 | 12 | 精讀 | BDP、bufferbloat 與排隊延遲、BBR、為什麼即時媒體怕長佇列 | 12.10 | 4 h |
| QUIC | 13 | 精讀 | stream 與 HOL、connection migration、UDP 被封鎖時的 fallback | 13.12 | 4 h |
| 即時通訊 | 31 | 略讀 | SSE、心跳與 proxy 緩衝 | — | 1 h |
| 即時通訊 | 32 | 精讀 | WebSocket 握手與 frame，signaling 通常就跑在它上面 | 32.13 | 5 h |
| 即時通訊 | 33 | 精讀 | 序號、補發、backpressure、部署時的重連驚群 | 33.14 | 4 h |
| 影音 | 34 | 精讀 | 取樣、GOP、codec 與 container、RTP／RTCP、jitter buffer | 34.11 RTP 打包、UDP 傳送與 jitter buffer | 5 h |
| 影音 | 35 | 精讀 | SDP 逐行解讀、offer／answer 規則、PT 不能寫死、Unified Plan | 35.10 解析 offer、產生 answer、驗證規則 | 5 h |
| 影音 | 36 | 精讀 | ICE candidate 與優先序、STUN 格式、TURN、DTLS-SRTP、data channel | 36.11 STUN server、candidate 優先序與 ICE 模擬 | 5 h |
| 影音 | 37 | 精讀 | mesh、SFU、MCU；simulcast 與 SVC；GCC 與 TWCC；NACK、FEC、PLI | 37.13 容量計算器、選層與丟包恢復模擬 | 5 h |
| 影音 | 38 | 精讀 | contribution 與 distribution、SRT 的 latency 與單位、HLS 與 LL-HLS、WHIP／WHEP | 38.15 模擬 SRT 式傳輸與 LL-HLS 播放器 | 5 h |
| 影音 | 39 | 精讀 | 品質指標、getStats 差值、單向無聲與黑畫面的排查、直播卡頓分段 | 39.10 分析 getStats 時間序列與症狀決策樹 | 4 h |
| 收尾 | 45、46 | 略讀 | 45.10、45.11 兩個案例；46.9 的視訊與直播元件、46.10 的降級階梯 | — | 3 h |

全程約 60–70 小時。Part 8 的六章是一個整體：第 34 章的 RTP 欄位會出現在第 35 章的 SDP、第 37 章的 SFU 改寫與第 39 章的 getStats 裡，建議連續讀完，中間不要插入其他 Part。

讀完影音路線，應該能做到：

- 逐行解讀一份真實的 WebRTC SDP，指出每個 m 段的 codec、方向、BUNDLE、fingerprint 與 setup，並判斷一份 answer 是否合法。
- 從 webrtc-internals 或 getStats 判斷選中的 candidate pair 類型、是否走 TURN、走哪一種傳輸。
- 用 candidate-pair 的雙向 bytes 先排除網路，再沿 SDP、送端、SFU、收端、播放逐站排查單向無聲或黑畫面。
- 估算一間六人小班在 mesh 與 SFU 下的上下行頻寬，說明 simulcast 的分層與選層原則。
- 依 RTT 與丟包率設定 SRT latency，並分清 libsrt（毫秒）與 ffmpeg URL 參數（微秒）的單位。
- 說明傳統 HLS、LL-HLS 與 WebRTC 觀看的延遲來源與成本，並為一個直播場景做選擇。

### E.2.5 資安工程師

導讀沒有獨立列出資安路線；本路線依各章的防禦內容整理。資安工程師需要的不是攻擊手法，而是知道每一層的信任邊界在哪裡、哪些設定一錯就會讓邊界失效、事故時怎麼從 log 與封包證明發生了什麼。全書安全相關內容只談成因、偵測與防禦，本路線也一樣。

| 階段 | 章 | 程度 | 本章重點 | 必做的動手做 | 時間 |
|---|---|---|---|---|---|
| 起點 | 1–3 | 略讀 | 系統全貌、工具箱、HAR 含有 cookie 與 token | — | 3 h |
| 網路邊界 | 6 | 略讀 | BGP 預設信任鄰居、RPKI 的能與不能 | — | 1 h |
| 網路邊界 | 7 | 精讀 | NAT 不是安全機制、stateful 防火牆規則順序、CGNAT 下 IP 不等於人 | 7.10 | 4 h |
| 網路邊界 | 8 | 略讀 | ICMP 要依類型過濾，全擋會讓網路以難察覺的方式壞掉 | — | 1 h |
| DNS | 15 | 精讀 | cache poisoning 的防禦、DNSSEC、DoH 與企業 resolver、dangling CNAME | 15.12 | 4 h |
| DNS | 16 | 略讀 | DNS-01 的權限限縮與 CNAME 委派 | — | 1 h |
| 密碼學 | 17 | 精讀 | 三種保證、HMAC、AEAD 與 nonce、不要自己發明密碼學 | 17.12 用標準函式庫驗證金流 webhook | 5 h |
| TLS | 18 | 精讀 | 關掉驗證等於放棄 TLS、憑證驗證步驟、0-RTT 重放、mTLS | 18.12 | 5 h |
| 憑證 | 19 | 精讀 | 短效憑證、CT 監控、HSTS preload 的導入與風險 | 19.12 | 3 h |
| HTTP | 20 | 略讀 | request smuggling 的成因與「整條路徑只有一種解讀」的防禦 | — | 1 h |
| HTTP | 21 | 精讀 | 個人化回應被共用快取、cookie 的 `Domain` 與 `__Host-` | 21.11 | 4 h |
| 瀏覽器 | 23 | 精讀 | SOP、CORS 不是存取控制、CSRF 分層防禦、CSP、frame-ancestors | 23.11 | 5 h |
| 信任邊界 | 25 | 精讀 | XFF 從右往左解析、origin 只接受 CDN 與 LB、API gateway 的邊界 | 25.10 | 4 h |
| 驗證授權 | 26–30 | 精讀 | 密碼儲存與限速、JWT 驗證與撤銷、OAuth 的 redirect URI 與 state、passkeys、HMAC 簽章與 workload identity | 26.10、27.10、28.15、29.13、30.9 | 22 h |
| 即時 | 32 | 略讀 | WebSocket 不受 CORS 管制、Origin 允許清單、一次性 ticket、訊息大小上限 | — | 2 h |
| 影音 | 35、36 | 略讀 | signaling 的安全等於 DTLS-SRTP 的安全、SDP 是不可信輸入、TURN 的 peer 限制 | — | 3 h |
| 堆疊 | 41、43 | 略讀 | Werkzeug debugger 絕不上 production、`forwarded_allow_ips` 不能是 `*` | — | 2 h |
| 雲端 | 44 | 精讀 | security group 與 NACL、PrivateLink、NetworkPolicy 預設全通、service mesh 的 mTLS | 44.15 | 5 h |
| 設計 | 46 | 略讀 | 46.11 安全邊界：每穿過一條邊界就有一次驗證 | — | 1 h |

全程約 75–85 小時。Part 6 是這條路線的重心，五章要連續精讀；第 23、25 章是 Part 6 的前提，因為 cookie、CORS 與信任邊界的規則決定了 token 能不能被偷、偷了能不能用。

讀完資安路線，應該能做到：

- 審查一段 Python TLS client 程式，指出任何停用驗證或漏掉名稱檢查的寫法，並給出正確版本。
- 審查一份 JWT 驗證程式，對照清單逐項檢查 alg、簽章、exp、nbf、iss、aud、typ 與 kid 的處理。
- 審查一個 OAuth 整合：redirect URI 是否精確比對、state 是否綁 session、是否使用 S256 的 PKCE、refresh token 是否輪替。
- 判斷一組 CORS 與 cookie 設定是否會讓其他網站以使用者身分讀取回應，並寫出修正後的 header。
- 檢查 proxy 鏈的 `X-Forwarded-For` 處理，說明限速與稽核 log 拿到的 client IP 是否可信。
- 為 webhook 接收端訂出驗證規則：原始 bytes 驗簽、timestamp 容許範圍、event id 去重與交易邊界。
- 檢查雲端與叢集的網路邊界：security group、NACL、NetworkPolicy、TURN 的允許中繼範圍。

## E.3 依目標的計畫

### E.3.1 四週入門計畫

導讀說，第一次系統性學網路的人照順序讀 Part 0 到 Part 5，讀完就有一張完整的網路地圖。四週讀完 25 章需要取捨：本計畫假設每週 12–15 小時（例如平日每天 2 小時、週末 3–5 小時），每週精讀約 4 章、其餘略讀，週末做一次驗收。四週後再依 E.2 的角色路線補上略讀的章節。

```text
 第 1 週          第 2 週           第 3 週              第 4 週
 起點與 IP        傳輸層             DNS 與 TLS            HTTP 與 Web
 ├ 1、2、3 精讀   ├ 9、10、11 精讀   ├ 14、16 精讀          ├ 20、21、23、25 精讀
 ├ 5 精讀         ├ 12、13 略讀      ├ 15 略讀             ├ 22、24 略讀
 └ 4、6、7、8 略讀 └ 驗收：TCP 狀態   ├ 17 略讀、18、19 精讀 └ 驗收：E.4 專案三
   驗收：子網手算                      └ 驗收：搬遷與憑證       的第一版
```

這條時間軸由左往右讀，每一週的最下面是週末的驗收。第一、二週建立「封包怎麼走、連線怎麼活」的直覺，第三週學會名稱與信任，第四週把前三週組成一個完整的 HTTP 請求；第四週的驗收刻意用一個專案而不是題目，因為 Part 5 的知識要在寫 server 與 proxy 時才會互相碰撞。

| 週 | 精讀與必做 | 略讀 | 週末驗收 |
|---|---|---|---|
| 1 | 第 1 章（1.14）、第 2 章（2.10）、第 3 章（3.12）、第 5 章（5.10） | 第 4、6、7、8 章 | 手算 3 組 CIDR；用 `curl -w` 切開一個你常用網站的五段時間；做 E.5 的 Part 0、Part 1 |
| 2 | 第 9 章（9.8）、第 10 章（10.11）、第 11 章（11.6、11.9） | 第 12、13 章 | 在本機重現 CLOSE_WAIT 堆積並用 `ss` 看到它，再修好程式；做 E.5 的 Part 2 |
| 3 | 第 14 章（14.10、14.11）、第 16 章（16.10）、第 18 章（18.12）、第 19 章（19.12） | 第 15、17 章 | 寫一份 DNS 搬遷計畫（含 TTL 與等待時間）；用 `openssl s_client` 檢查一個網站的憑證鏈；做 E.5 的 Part 3、Part 4 |
| 4 | 第 20 章（20.10）、第 21 章（21.11）、第 23 章（23.11）、第 25 章（25.10） | 第 22、24 章 | 完成 E.4 專案三的第一版（server 支援 keep-alive 與 Content-Length，proxy 能轉送並寫 XFF）；做 E.5 的 Part 5 |

四週後你應該能把第 1 章的九站旅程每一站都講到機制層級，並且知道每一站壞掉時用哪個工具確認。如果某一週的驗收做不完，寧可把計畫延長一週，也不要跳過驗收直接往下讀；後面每一週都建立在前一週的直覺上。

### E.3.2 面試準備：兩週衝刺

導讀建議準備面試的人讀第 1 章與第 46 章的系統設計與面試題，搭配本附錄。第 46 章 46.18 節收錄 15 題常見網路面試題，並依角色標出重點：後端多半集中在第 1、2、5、7、8、10 題；前端加上第 9 與第 4 題；SRE 再加上第 3 與第 13 題；影音職缺則是第 14、15 題。本計畫以這個分組為骨架，假設每天 2–3 小時，已經讀過或略讀過 Part 0–5。

| 天 | 主題 | 讀什麼 | 產出 |
|---|---|---|---|
| 1 | 全程旅程 | 第 1 章；第 46 章 46.18 第 1 題 | 不看書講一次「輸入網址之後發生什麼」，錄音計時，目標 5 分鐘內講完並帶出每站 RTT |
| 2 | TCP | 第 10 章 10.2–10.9、第 11 章重點整理；46.18 第 2 題 | 畫出 TCP 狀態機；說明 TIME_WAIT 與 CLOSE_WAIT 的差別與各自的處置 |
| 3 | TCP 與 UDP、HOL | 第 9、12、13 章重點整理；46.18 第 3、4 題 | 一張比較表：TCP、UDP、QUIC 的可靠性、順序、HOL 與交握 RTT |
| 4 | DNS | 第 14、15 章；46.18 第 5 題 | 解析流程圖與搬遷時間線（含 TTL） |
| 5 | TLS 與憑證 | 第 18、19 章；46.18 第 6 題 | 不看書寫出 TLS 1.3 交握時序與憑證驗證步驟 |
| 6 | HTTP 快取與 CDN | 第 21、25 章；46.18 第 7 題 | 個人化頁面的兩道防線；一組完整的 `Cache-Control` 策略 |
| 7 | LB 與 proxy | 第 25 章；46.18 第 8 題 | L4 與 L7 比較；health check 參數與最壞偵測時間的算式 |
| 8 | 瀏覽器安全 | 第 23 章；46.18 第 9 題 | CORS 與 CSRF 的關係，用一張時序圖說明 preflight |
| 9 | 驗證與授權 | 第 26–29 章重點整理；46.18 第 10、11 題 | session 與 JWT 的選擇；PKCE 流程圖；OAuth 與 OIDC 的差別 |
| 10 | 即時系統 | 第 31–33 章；46.18 第 12、13 題 | WebSocket 擴展到數萬連線的架構圖與估算 |
| 11 | 影音（影音職缺必做，其他職缺略讀） | 第 36–38 章；46.18 第 14、15 題 | ICE 流程與 SFU 選擇的理由；直播延遲的組成 |
| 12 | 設計流程 | 第 46 章 46.1–46.8 | 依 46.6 的 45 分鐘時間軸，練習需求與估算兩段，寫出可量測的非功能需求表 |
| 13 | 模擬面試 | 第 46 章 46.9–46.13 | 找人當面試官，完整走一次「設計聲聲 Live」；結束後列出被追問卻答不好的地方 |
| 14 | 補洞與除錯題 | 第 45 章 45.2、45.3、45.12；E.5 全部題組 | 依第 13 天的清單重讀；用 45.12 的大表練習「聽到症狀先講哪一層」 |

衝刺期間有兩個原則。第一，每一題都照第 46 章的答題模式回答：先講結論，再講機制，最後講實務上的取捨或你遇過的例子；設計題則是「決定、理由、代價、何時重新考慮」。第二，數字要背到能用：RTT 的量級、TLS 1.3 的 1-RTT、IPv4 與 TCP header 最少 20 bytes、Ethernet MTU 1500、TIME_WAIT 約 2×MSL；能把答案連回一個真實系統並給出數字，比背定義有說服力得多（第 46 章 46.18）。

### E.3.3 上線前檢查與值班準備

這份計畫給即將負責一個服務上線、或第一次輪值 on-call 的人。它分成兩半：上線前逐項檢查設定，值班前練習判斷流程。每一項都標出對應章節，檢查方法優先選「一分鐘內能執行、只有兩種結果」的指令，與第 45 章大表的精神一致。

上線前檢查：

| 項目 | 檢查什麼 | 怎麼驗證 | 章節 |
|---|---|---|---|
| DNS | 紀錄指向正確、TTL 符合變更計畫、沒有 dangling CNAME、內外 zone 一致 | 對權威 server `dig +norecurse`；對多台 resolver 比對答案 | 第 14–16 章 |
| 憑證 | 名稱涵蓋所有網域、鏈完整、自動更新會觸發 reload、每台副本一致 | `openssl s_client -servername` 逐一連到每個後端；檢查序號與剩餘效期 | 第 18、19 章 |
| HSTS | 已盤點子網域再加 `includeSubDomains`，max-age 格式正確 | `curl -sI` 看 `Strict-Transport-Security` | 第 19 章 |
| timeout 鏈 | 外層比內層長，最內層先放棄並回有意義的錯誤 | 列出 CDN、LB、nginx、gunicorn、app、DB 的逾時值並排序 | 第 43 章 |
| keep-alive | 每一段 server 端的閒置上限比 client 端長 | 列出 LB idle、nginx、gunicorn、uvicorn 的值並兩兩比較 | 第 20、43、45 章 |
| health check | 打真正的應用路徑（例如 `/readyz`），參數算過最壞偵測時間 | interval × fall ＋ timeout；停掉一個依賴看 readiness 是否變化 | 第 25 章 |
| 部署 | readiness 先失敗、drain、關 listening socket、等請求做完 | 部署期間持續送請求，統計失敗數必須為 0 | 第 25、43 章 |
| client IP | 面對 internet 的那層覆寫 XFF，後端只信固定的可信網段 | 從外部帶偽造的 XFF 打 API，確認 log 記到的是真實位址 | 第 25、43 章 |
| 快取 | 個人化回應標 `private`、CDN 對帶登入 cookie 的請求 bypass | 用兩個帳號各打一次，比對 `Cache-Control`、`Age` 與內容 | 第 21、25 章 |
| CORS 與 cookie | 允許清單逐字比對、錯誤回應也帶 `Vary: Origin`；session cookie 屬性正確 | curl 模擬 preflight；DevTools 的 Cookies 分頁 | 第 21、23、26 章 |
| token | 驗證端固定 alg，檢查 exp、nbf、iss、aud；401 與 403 分開 | 送錯 aud、過期、未知 kid 的 token，確認各自被拒 | 第 27、28 章 |
| webhook | 對原始 bytes 驗簽、timestamp 容許範圍、event id 唯一約束 | 重送同一事件兩次，確認只入帳一次 | 第 30 章 |
| 即時連線 | 心跳短於路徑上最短的 idle timeout、訊息大小上限、Origin 允許清單 | 開一條閒置連線放超過最長 idle timeout，確認不斷線 | 第 32、33 章 |
| 影音 | TURN 提供 UDP 與 TLS 443、短效帳密、只允許中繼到 SFU 位址 | 在只開 TCP 443 的網路測試，webrtc-internals 看選中的 relay | 第 36、37、39 章 |
| 雲端網路 | 子網的 default route、security group 最小開放、NACL 回程 ephemeral port、NAT gateway 位址已登記到第三方 | 從每個子網對外與對內各測一次連線 | 第 44 章 |
| MTU | 隧道與 overlay 的 MTU 設定一致、ICMP Type 3 未被全擋 | 帶 DF 的 `ping -s` 測路徑；大回應實測 | 第 8、44 章 |
| 開發工具 | Werkzeug debugger 與開發伺服器沒有出現在任何可被連到的環境 | 檢查啟動指令與環境變數；從其他主機掃描應用 port | 第 41 章 |

值班準備的重點不是背更多知識，而是讓第一個動作正確。建議依序做四件事：

1. **讀方法**：第 45 章 45.2 與 45.3。記住「先決定是哪一層，再決定去看誰的 log」，以及由下而上、由上而下、分半法各自適合的情境。
2. **背大表**：第 45 章 45.12 的症狀對照表。練習的方式是請同事唸出使用者的原話，你在 30 秒內說出第一個要執行的指令和它要回答的是非題。
3. **準備工具**：把附錄 B 的常用指令整理成自己的值班筆記，確認在 bastion 或除錯容器裡都裝好了 dig、curl、ss、tcpdump、openssl；確認自己有讀取 LB、CDN 與 DNS 設定的權限，並優先使用唯讀的權限。
4. **做演練**：在 staging 環境辦一場第 45 章 45.1 的故障演練，或至少重現其中三個案例。只在測試環境注入故障，並事先寫好復原步驟。

值班時有三條紀律值得寫在筆記第一頁：動手之前先寫下影響範圍、開始時間與最近的變更；止血之前先保留 `ss` 輸出與 log 等證據；一次只改一個變數（第 45 章）。

## E.4 實作專案練習

讀書會讓你看懂機制，做專案才會讓你遇到書裡寫的每一個坑。本節的 8 個專案由淺入深排列，每個都列出需求、用到的章節、驗收標準與延伸方向。專案一到五只用 Python 標準函式庫，可以完全在 127.0.0.1 上完成，並且大量重用各章動手做的程式；專案六、七需要瀏覽器與 ffmpeg 等外部工具；專案八需要一個你自己的雲端測試帳號。

| # | 專案 | 難度 | 預估時間 | 主要章節 | 建議先完成 |
|---|---|---|---|---|---|
| 1 | 封包解析器與迷你工具箱 | ★ | 8–12 h | 2、3、4、9、10、11 | — |
| 2 | 自己的 DNS resolver | ★★ | 12–16 h | 9、14、15、16 | 1 |
| 3 | HTTP/1.1 server＋反向代理 | ★★ | 16–24 h | 10、11、20、21、25、40、43 | 1 |
| 4 | OAuth＋PKCE 登入 | ★★★ | 16–24 h | 17、21、23、26–29 | 3 |
| 5 | WebSocket 聊天室含重連補發 | ★★★ | 20–28 h | 11、31、32、33、42 | 3 |
| 6 | WebRTC 一對一（瀏覽器） | ★★★★ | 20–30 h | 7、34、35、36、37、39 | 5 |
| 7 | SRT → HLS 直播管線 | ★★★★ | 16–24 h | 21、34、38、39 | 3 |
| 8 | 雲端部署與故障演練 | ★★★★★ | 24–40 h | 5、7、16、19、25、43、44、45、46 | 3、4、5 |

```text
 專案 1 ──► 專案 2
    │
    └────► 專案 3 ──┬──► 專案 4 ──┐
                   ├──► 專案 5 ──┼──► 專案 8（把 3、4、5 部署上雲並演練）
                   │      │      │
                   │      └──► 專案 6（signaling 沿用專案 5）
                   └──► 專案 7（用專案 3 的 server 發布 HLS）
```

這張相依圖說明專案之間如何重用：專案三的 HTTP server 會成為專案四的授權伺服器、專案五的握手入口與專案七的 HLS 發布端；專案五的 WebSocket 會成為專案六的 signaling 通道；專案八則把前面的作品部署到雲端，作為故障演練的靶場。照箭頭順序做，每個專案都能少寫一半的程式。

每個專案共同的要求：程式放在版本控制裡；每個驗收標準都有一個可以重複執行的測試（Python 的 `assert` 或一段 shell 指令）；README 寫下設計決定與它對應的章節；任何會連到真實網路或第三方服務的測試，只對你自己擁有或明確允許測試的目標執行。

### E.4.1 專案一：封包解析器與迷你工具箱

**需求**：寫一個讀取 tcpdump 輸出的 pcap 檔（經典 pcap 格式：24 bytes 的檔案標頭，每筆封包前有 16 bytes 的紀錄標頭）的解析器，逐層解開 Ethernet、IPv4／IPv6、TCP、UDP，印出類似 `tcpdump -n` 的一行摘要；依五元組把封包分成 flow，對每條 TCP flow 算出交握 RTT、雙方宣告的 MSS 與 window scale、相對序號、是否出現 RST 與重傳。再加一個 `portcheck` 指令，對一組主機與 port 分辨 open、refused 與 timeout。

**用到的章節**：第 2 章（header 布局與 `struct`、checksum）、第 3 章（tcpdump 與 3.12 的 port 檢查器）、第 4 章（Ethernet frame 與 EtherType）、第 9 章（UDP 與五元組）、第 10 章（TCP header、旗標與狀態）、第 11 章（序號與重傳）。各欄位的位元布局可以對照附錄 C。

**驗收標準**：

| # | 標準 | 怎麼驗證 |
|---|---|---|
| 1 | 對一個本機 `curl` 到 `http.server` 的抓包檔，每個封包的五元組、旗標、長度與 Wireshark 一致 | 在 Wireshark 開同一個檔案逐筆比對前 20 個封包 |
| 2 | IPv4 header checksum 與 UDP checksum 驗證結果正確，故意改壞 1 byte 後能偵測 | 寫一個測試竄改 bytes |
| 3 | 交握 RTT 等於 SYN 與 SYN-ACK 的時間差，MSS 與 window scale 從 SYN 的 option 正確解出 | 和 Wireshark 的 TCP 分析欄位比對 |
| 4 | 不認得的 link type、截斷的封包、長度欄位不合理時給出明確錯誤，不會丟例外或無窮迴圈 | 用截斷的檔案與隨機 bytes 測試 |
| 5 | `portcheck` 對關閉的 port 在約一個 RTT 內回 refused，對被丟包的目標在設定的 timeout 後回 timeout | 本機起一個 listener 與一個不存在的 port 測試 |

**延伸**：macOS 的 lo0 與 Linux 的 any 介面不是 Ethernet 封裝，讓解析器依 pcap 標頭的 link type 處理不同的鏈結層；加上 DNS 訊息的解碼（為專案二鋪路）；偵測三個重複 ACK 與 fast retransmit，並標出疑似 PMTUD 黑洞的模式（同大小的滿載 segment 反覆重傳，第 8 章）。

### E.4.2 專案二：自己的 DNS resolver

**需求**：實作一個迭代式 recursive resolver。它從 root 開始依 referral 問到 authoritative，處理 glue、CNAME 鏈、NXDOMAIN 與 NODATA、TC=1 時改用 TCP 重問、EDNS(0) 的 OPT（宣告 1232 bytes），並有遵守 TTL 的快取與負面快取。測試環境沿用第 14 章 14.11 的做法：在 127.0.0.1 上啟動多個假的 root、TLD 與權威 server，所有 zone 用 `.example`、`.test` 等保留名稱。最後讓 resolver 本身也聽一個 UDP port，能被 `dig @127.0.0.1 -p <port>` 查詢。

**用到的章節**：第 9 章（UDP socket 與 timeout）、第 14 章（訊息格式、name compression、遞迴與迭代、TTL）、第 15 章（負面快取、CNAME 限制、cache poisoning 的防禦）、第 16 章（stub resolver、search domain 與 ndots）。

**驗收標準**：

| # | 標準 | 怎麼驗證 |
|---|---|---|
| 1 | 對測試 zone 的 A、AAAA、CNAME、MX、TXT 查詢，答案與 `dig` 直接問權威 server 的結果相同 | 自動化比對每一種 type |
| 2 | 快取命中時回傳的 TTL 隨時間遞減，過期後重新查詢 | 用模擬時鐘測試，不要真的等待 |
| 3 | NXDOMAIN 與 NODATA 分開處理，負面快取時間為 SOA TTL 與 MINIMUM 的較小值 | 查不存在的名稱與不存在的 type |
| 4 | 每個查詢用隨機 ID 與隨機來源 port；回應的 ID、問題段與來源不符時丟棄；只接受 bailiwick 內的資料 | 讓假 server 回錯 ID 或回 bailiwick 外的紀錄 |
| 5 | name compression 指標迴圈、超長名稱與截斷封包不會讓 resolver 當掉 | 用手工組出的惡意格式回應測試 |
| 6 | 第一台 NS 不回應時在 timeout 後改問下一台，總查詢時間有上限 | 讓其中一台假 server 不回應 |

**延伸**：加上 DNSSEC 驗證的簡化版（沿用第 15 章 15.12 的模擬，驗證 DS → DNSKEY → RRSIG 的鏈）；實作一個 DoT client，用第 18 章的測試 CA 對本機 TLS server 查詢；模擬 Kubernetes 的 `ndots:5` 與四個 search domain，數出一次外部名稱查詢實際送出幾個請求（第 16 章）。

### E.4.3 專案三：HTTP/1.1 server＋反向代理

**需求**：用 asyncio 寫一個 HTTP/1.1 server 與一個 L7 反向代理。server 支援 keep-alive、`Content-Length` 與 chunked、`HEAD`、條件請求（ETag 與 304）、靜態檔與 Range；對 header 大小、body 大小與每條連線的總期限設上限。反向代理維持到後端的連線池，支援兩台以上後端、`/readyz` 主動健康檢查與被動失敗偵測、least connections、只對 idempotent 請求重試，正確處理 `X-Forwarded-For`（面對 client 的一層覆寫）與 hop-by-hop header，並支援 draining。

**用到的章節**：第 10 章（accept queue、CLOSE_WAIT）、第 11 章（framing）、第 20 章（訊息格式、body 長度規則、keep-alive、smuggling 防禦）、第 21 章（快取與條件請求、Range）、第 25 章（反向代理、health check、負載演算法、XFF）、第 40 章（並行模型、期限與大小上限）、第 43 章（timeout 鏈與 keep-alive 方向、graceful shutdown）。

**驗收標準**：

| # | 標準 | 怎麼驗證 |
|---|---|---|
| 1 | `curl -v` 連續請求兩個 URL 時重用同一條連線 | curl 輸出中的連線重用訊息；`ss -tn` 只看到一條連線 |
| 2 | 同時帶 `Content-Length` 與 `Transfer-Encoding`、重複的 `Content-Length`、缺少 `Host` 的請求回 400 並關閉連線 | 用 `nc` 送手寫的請求 |
| 3 | header 超過上限回 431，宣告的 body 超過上限直接回 413，不先讀 body | 同上 |
| 4 | 每秒只送 1 byte 的慢速 client 在總期限到期時被關閉，不會佔住 server | 寫一個慢速 client 測試，並觀察 server 的連線數 |
| 5 | 停掉一台後端後，在 interval × fall ＋ timeout 內被移出，期間的 GET 透過重試成功、POST 不被重試 | 持續送混合請求並統計結果 |
| 6 | 後端看到的 `X-Forwarded-For` 只有 proxy 寫入的真實對端，client 自帶的值被覆寫 | 帶偽造 XFF 發請求並看後端 log |
| 7 | draining 期間進行中的請求做完、新請求轉到其他後端，失敗數為 0 | 在負載下執行 draining |

**延伸**：讓 server 支援 WSGI 介面，能跑 `wsgiref` 寫的 app（第 41 章）；在 proxy 前加一層共用快取，並重現第 21 章的「首頁寫著別人的名字」事故再修好；用第 22 章的 frame 解析程式支援 h2c 的連線前言與 SETTINGS。

### E.4.4 專案四：OAuth＋PKCE 登入

**需求**：在 127.0.0.1 上用不同 port 跑四個角色：authorization server（AS）、使用 BFF 模式的網頁 client、resource server（RS）、以及模擬使用者的瀏覽器腳本。AS 提供登入（密碼用 `hashlib.scrypt` 雜湊，可加上 TOTP）、授權端點（redirect URI 精確比對、`state`、只接受 S256 的 PKCE）、token 端點（授權碼 60 秒且一次性、access token 為 HS256 JWT 有效 5 分鐘、refresh token 為 opaque 並每次使用即輪替）。BFF 只把 session cookie 交給瀏覽器，token 留在伺服器端。RS 依清單驗證 JWT，並依 scope 授權。

**用到的章節**：第 17 章（HMAC、`secrets`、`compare_digest`）、第 21 章（cookie 屬性）、第 23 章（SameSite、CSRF）、第 26 章（密碼雜湊、session 與輪替、TOTP）、第 27 章（JWT 簽發與驗證、refresh token 家族撤銷）、第 28 章（authorization code＋PKCE、state、redirect URI）、第 29 章（OIDC 與 ID token）。

**驗收標準**：

| # | 標準 | 怎麼驗證 |
|---|---|---|
| 1 | 正常流程跑完：登入、同意、拿到授權碼、以 code verifier 換 token、呼叫 RS 成功 | 端到端測試腳本 |
| 2 | code verifier 錯誤回 `invalid_grant`；同一個授權碼兌換第二次被拒，且已發出的 token 被撤銷 | 負向測試 |
| 3 | redirect URI 與登記值有任何差異時，AS 顯示錯誤頁而不是導回 | 測試多出路徑、改 port、改大小寫 |
| 4 | 回呼的 `state` 缺少或不符時，client 拒絕並不送出 token 請求 | 負向測試 |
| 5 | RS 對 alg 不在允許清單、簽章錯、過期、iss 或 aud 不符的 token 回 401 並帶 `WWW-Authenticate`；scope 不足回 403 `insufficient_scope` | 逐項構造 token 測試 |
| 6 | 已使用過的 refresh token 再次出現時，整個 token 家族被撤銷並記錄告警 | 模擬 refresh token 被複製 |
| 7 | 瀏覽器端看不到任何 token；session cookie 帶 `Secure`、`HttpOnly`、`SameSite`，登入後 session ID 已輪替 | 檢查回應的 `Set-Cookie` 與登入前後的 session ID |

本機測試 `__Host-` 前綴與 `Secure` cookie 時，可以用第 18 章的測試 CA 讓各角色跑在 HTTPS 上，讓 cookie 的條件與 production 相同。

**延伸**：在 token 回應中加上 OIDC 的 ID token，client 依第 29 章的步驟驗證 iss、aud、exp、nonce，並以 `(iss, sub)` 作為帳號主鍵；加上 client credentials 給沒有使用者的 service；把 JWT 改成非對稱簽章並發布 JWKS，練習第 27 章的金鑰輪替順序（標準函式庫沒有 ECDSA，這部分需要第三方套件，以 `# not-runnable` 的方式記錄設計即可）。

### E.4.5 專案五：WebSocket 聊天室含重連補發

**需求**：用 asyncio 從零實作 WebSocket server 與 client（握手、frame 編解碼、client 端 masking、ping／pong、close handshake），在其上做一個多房間聊天室。每個房間由單一序號產生器替訊息編號；client 送出的每則訊息帶 `client_msg_id` 供去重；server 保留每個房間最近的訊息作為補發緩衝。client 斷線後以指數退避加 jitter 重連，帶上最後收到的序號，server 補發缺口，缺口超出緩衝時改送完整快照。至少跑兩個 gateway process，透過一個簡單的 pub/sub broker 互相轉送房間訊息。

**用到的章節**：第 11 章（framing、keepalive）、第 31 章（SSE 的重連與 Last-Event-ID，作為對照）、第 32 章（握手、frame、masking、close code、Origin 與 ticket）、第 33 章（序號、去重、補發、backpressure、presence、部署時的重連）、第 42 章（ASGI 的 WebSocket 事件，作為延伸）。

**驗收標準**：

| # | 標準 | 怎麼驗證 |
|---|---|---|
| 1 | 以 RFC 範例 key `dGhlIHNhbXBsZSBub25jZQ==` 算出 `s3pPLMBiTxaQ9kYGzzhZRbK+xOo=` | 單元測試 |
| 2 | 瀏覽器的 `WebSocket` API 能連上並收發訊息；server 拒絕未 mask 的 client frame 與不在允許清單的 Origin | 在 DevTools Console 測試；用自己的 client 送錯誤 frame |
| 3 | 超過訊息上限（例如聊天 64 KiB）時以 1009 關閉，且 server 在讀 payload 之前就依宣告長度判斷 | 送一個宣告長度過大的 frame |
| 4 | 在聊天進行中殺掉一個 gateway，所有 client 重連後收到的序號連續、沒有重複也沒有遺漏 | 每個 client 記錄收到的序號並檢查 |
| 5 | 一個刻意不讀資料的慢 client 不會拖慢同房間其他人；出站佇列超過上限時以自訂 close code（例如 4008）關閉 | 量測其他 client 的訊息延遲 |
| 6 | 連線閒置超過路徑上最長的 idle timeout 也不會斷，因為心跳間隔較短 | 在專案三的 proxy 後面設短的 idle timeout 測試 |
| 7 | 部署時 server 送 1012，client 在 jitter 視窗內分散重連，而不是同一秒全部湧入 | 統計每秒新連線數 |

**延伸**：把 server 改寫成 ASGI app，用第 42 章的最小 ASGI server 執行；加上 presence（心跳延長 TTL、重新整理的寬限期）；為只能用 HTTP 的環境加一條 SSE 下行加 POST 上行的備援路徑（第 31 章）。

### E.4.6 專案六：WebRTC 一對一（以瀏覽器實作）

**需求**：做一個兩人視訊頁面。媒體由瀏覽器的 WebRTC API 處理（`getUserMedia`、`RTCPeerConnection`、data channel），你負責 signaling 與營運面：用專案五的 WebSocket 或 HTTP 做 signaling 伺服器，轉送 SDP 與 trickle ICE candidate，並驗證雙方身分與房間權限；固定由一方發 offer 或實作 perfect negotiation 處理 glare；設定 STUN 與 TURN（TURN 可用開源實作），TURN 使用短效帳密（格式「到期時間:使用者 ID」、HMAC 產生密碼）。頁面上顯示一個即時統計面板：選中的 candidate pair 類型與傳輸方式、RTT、丟包、jitter、送出解析度與 `qualityLimitationReason`。

**用到的章節**：第 7 章（NAT 類型與打洞）、第 34 章（codec、RTP 欄位）、第 35 章（SDP 與 offer／answer）、第 36 章（signaling 的安全、ICE、STUN、TURN、DTLS-SRTP、data channel）、第 37 章（TURN 的部署與限制、getStats 指標）、第 39 章（webrtc-internals 與 getStats 解讀、單向問題的排查）。

注意兩個瀏覽器的前提：`getUserMedia` 只在 secure context 可用，`localhost` 算 secure context，但從另一台裝置連過來時頁面必須走 HTTPS；TURN over TLS 443 需要有效的憑證。這兩點正好是第 18、19 章的練習。

**驗收標準**：

| # | 標準 | 怎麼驗證 |
|---|---|---|
| 1 | 同一台電腦的兩個分頁與同一個區網的兩台裝置都能建立雙向影音 | webrtc-internals 看到 connected 與雙向的 bytes |
| 2 | 在 client 設定只用 relay 時仍能連線，統計面板顯示 relay 與 TURN 的傳輸方式 | 設定 `iceTransportPolicy` 為 relay |
| 3 | 封鎖 UDP 的網路環境下，透過 TURN over TLS 443 連線成功 | 在測試網路或防火牆規則下驗證 |
| 4 | TURN 帳密過期後無法建立新的 allocation；TURN 只允許中繼到你設定的範圍 | 用過期帳密測試；檢查 TURN 設定 |
| 5 | signaling 拒絕未驗證的連線與不屬於該房間的使用者；SDP 在伺服器端被當成不可信輸入做基本驗證 | 負向測試 |
| 6 | 關掉一方的鏡頭 track 時，另一方顯示對應狀態而不是黑畫面卡住；能用 39 章的流程解釋一次刻意製造的單向無聲 | 手動測試並寫下排查紀錄 |

**延伸**：用第 35 章 35.10 的解析程式在 signaling 伺服器上檢查 answer 是否符合 offer／answer 規則；把自己在第 36 章 36.11 寫的 STUN server 設成瀏覽器的 STUN server，觀察 srflx candidate（在同一台機器上 srflx 會和 host 相同，要從另一個網路測試才有意義）；接上一個開源 SFU，開啟 simulcast，觀察三層的碼率與選層（第 37 章）。

### E.4.7 專案七：SRT → HLS 直播管線

**需求**：在自己的電腦上組一條完整的直播管線：編碼端以 SRT caller 推流到本機的 SRT listener，收端轉碼成至少兩層的 ABR 階梯，封裝成 HLS（segment 2 秒、GOP 與 segment 對齊），由專案三的 HTTP server 或 `http.server` 發布，播放器在瀏覽器播放。為 playlist 與 segment 設定不同的快取 header，並量測端到端延遲（在畫面上燒入時鐘，與牆上時間比較）。

**用到的章節**：第 21 章（快取 header 與 Range）、第 34 章（GOP、codec、container、bitrate）、第 38 章（contribution 與 distribution、SRT 的 latency 與 caller／listener、HLS 的 playlist 與 segment、LL-HLS）、第 39 章（SRT 統計與直播卡頓的分段排查）。

以下是 ffmpeg 的示意指令（需要支援 libsrt 的版本；參數名稱請依你手上版本的文件確認）。注意 ffmpeg 的 SRT URL 參數 `latency` 單位是微秒，120000 代表 120 ms；libsrt 與 srt-live-transmit 的 latency 則以毫秒計（第 38 章）。

```bash
# 收端（listener）：收 SRT、轉碼、封裝成 HLS（示意）
ffmpeg -i "srt://127.0.0.1:9000?mode=listener&latency=120000" \
  -c:v libx264 -preset veryfast -g 30 -keyint_min 30 -sc_threshold 0 \
  -c:a aac -b:a 128k \
  -f hls -hls_time 2 -hls_list_size 6 -hls_flags delete_segments out/index.m3u8

# 推流端（caller）：用測試畫面與測試音模擬編碼器（示意）
ffmpeg -re -f lavfi -i testsrc2=size=1280x720:rate=30 -f lavfi -i sine=frequency=440 \
  -c:v libx264 -preset veryfast -tune zerolatency -g 30 -pix_fmt yuv420p \
  -c:a aac -f mpegts "srt://127.0.0.1:9000?mode=caller&latency=120000"
```

這兩段指令先啟動收端再啟動推流端。`-g 30` 在 30 fps 下代表 1 秒一個 keyframe，與 2 秒的 segment 對齊；`-sc_threshold 0` 避免轉場時插入額外的 keyframe 打亂對齊。上例只有一層輸出，ABR 的多層階梯要再加上縮放與多個輸出，留給你依第 38 章的碼率階梯完成。

**驗收標準**：

| # | 標準 | 怎麼驗證 |
|---|---|---|
| 1 | 播放器能連續播放 10 分鐘，並在兩層之間切換 | 在播放器或 DevTools 看請求的 playlist 與 segment |
| 2 | 每個 segment 都從 keyframe 開始，長度穩定在 2 秒左右 | 用 ffprobe 檢查 segment 的第一個 frame 與時長 |
| 3 | media playlist 的快取時間遠短於 target duration，segment 可以長期快取，錯誤回應不會被長時間快取 | `curl -sI` 檢查 header |
| 4 | 量到的端到端延遲能用「編碼＋傳輸＋segment 長度×播放器 hold-back＋下載」解釋，誤差在一個 segment 以內 | 寫下各段的估計值並與實測比較 |
| 5 | 在推流路徑注入丟包時，latency 足夠時 `pktRcvDrop` 維持為 0；把 latency 調得比數個 RTT 還小時開始出現 drop | 讀 SRT 的統計；丟包注入只在自己的測試機上進行 |

在 Linux 上注入丟包與延遲通常用 `tc netem`，需要系統管理權限，請只在自己的測試機上操作；沒有權限時，改用第 38 章 38.15 的模擬程式理解 latency 視窗與重傳次數的關係。

**延伸**：改用支援 partial segment 的封裝工具做 LL-HLS，量測延遲下降多少、請求數增加多少（第 38 章）；加上 WHIP 推流與 WHEP 觀看的路徑，比較延遲與每位觀眾的伺服器成本；把 segment 改成 CMAF（fMP4），讓 HLS 與 DASH 共用。

### E.4.8 專案八：雲端部署與故障演練

**需求**：在你自己的雲端測試帳號裡，部署一個縮小版的聲聲 Live：兩個 AZ 各一組 public 與 private 子網、NAT gateway、對外的 LB（使用受管憑證）、private 子網裡的 nginx＋gunicorn（跑專案三或一個 Flask app）與 uvicorn（跑專案五），一個 DNS 名稱（TTL 先設低）。所有服務的 log 用 `x-request-id` 串接。部署完成後，依第 45 章 45.1 的故障演練日，在這個環境裡重現至少五個案例，每個案例由一人注入故障、另一人只拿到「使用者的原話」來排查。

**用到的章節**：第 5 章（VPC 子網規劃）、第 7 章（security group 與 NACL）、第 16 章（雲端與容器的名稱解析）、第 19 章（受管憑證、到期監控）、第 25 章（LB、health check、draining、XFF）、第 43 章（timeout 鏈、keep-alive、graceful shutdown）、第 44 章（VPC、route table、NAT gateway、security group）、第 45 章（八個案例與症狀大表）、第 46 章（容量估算、失效模式與降級）。

建議的演練題目（全部只在這個測試環境注入，並事先寫好復原步驟）：

| 演練 | 注入的故障 | 給值班者的原話 | 預期的診斷路徑 | 章節 |
|---|---|---|---|---|
| A | DNS 改指新 LB，但測試機的程式自己快取了舊 IP | 「有些人連到的版本是舊的」 | 多台 resolver 比對、`curl -w '%{remote_ip}'`、`ss -tn` | 第 14–16 章、45.4 |
| B | 移除 app 的 security group 規則；另一次只停掉 gunicorn | 「API 一直轉圈」與「API 馬上失敗」 | timeout 與 refused 的時間特徵、`nc -vz`、目標端抓 SYN | 第 7、10、44 章、45.6 |
| C | 把 gunicorn keep-alive 設得比 nginx upstream 的閒置上限短 | 「偶爾跳出 502」 | nginx error log 的訊息、兩端抓 FIN 與 RST | 第 43 章、45.7 |
| D | 移除 private 子網 route table 的 default route | 「付款 webhook 回呼失敗、外部 API 逾時」 | 從主機對外測試、檢查 route table 與 NAT gateway | 第 44 章 |
| E | nginx 的 `proxy_read_timeout` 短於 WebSocket 心跳間隔 | 「安靜的教室每分鐘斷一次」 | close code 1006 與距上一則訊息的秒數、nginx 設定 | 第 32、33 章、45.10 |
| F | 讓 API 的錯誤回應不帶 CORS header | 「預約按鈕沒反應」 | Network 面板的 status、curl 模擬 preflight | 第 23 章、45.9 |

這張表的第三欄刻意不提任何技術詞彙，和第 45 章的演練一樣只給症狀不給層。第四欄是評分的依據：看的是第一個正確的是非題用了多久，而不只是最後有沒有找到根因。

**驗收標準**：

| # | 標準 | 怎麼驗證 |
|---|---|---|
| 1 | 整套環境可以用程式碼或腳本重建，不靠手動點選 | 刪掉後重建一次，行為相同 |
| 2 | 在持續負載下做一次滾動部署，失敗請求數為 0 | 用一個簡單的負載腳本統計 |
| 3 | timeout 鏈與 keep-alive 設定整理成一張表，每個數字都說得出理由 | 與第 43 章的規則比對 |
| 4 | 從外部監控憑證剩餘效期與每個端點的序號 | 讓監控在測試網域上觸發一次告警 |
| 5 | 每個演練都寫成一頁值班手冊：症狀、證據、工具輸出、根因、修正、偵測所花的時間 | 交給沒參與的人照手冊重做一次 |
| 6 | 依第 46 章的方法估算這套環境的容量上限，並用負載測試驗證估算的量級 | 估算值與實測值的差距寫進 README |

雲端資源會持續計費，演練結束後依清單移除測試帳號中的資源；這份清單本身也是驗收的一部分。不要在 production 環境注入任何未經核准的故障。

**延伸**：把 app 搬進 Kubernetes，重現 Pod MTU 與 VXLAN 的問題（第 44 章）以及 `ndots:5` 造成的 DNS 查詢放大（第 16 章）；加上 TURN 與專案六，演練「企業網路只開 TCP 443」的情境（第 39 章）；依第 46 章 46.10 為每個元件寫出降級狀態，並演練自動進入降級。

## E.5 自我檢核題組

每個 Part 5 題，涵蓋該 Part 最核心、也最常在工作與面試中出現的判斷。先遮住右邊兩欄自己回答，答完再對照答案要點；答案要點只列出必須講到的關鍵，完整解釋在標示的章節。答錯兩題以上的 Part，建議回到該 Part 的「本章重點整理」重讀一次。

### Part 0　起點（第 1–3 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 0-1 | 一條全新的 HTTPS 連線，在 TCP＋TLS 1.3 下要經過幾個 RTT 才能送出第一個請求？HTTP/3 呢？重用連線呢？ | TCP 交握 1 RTT＋TLS 1.3 交握 1 RTT，共 2 RTT；QUIC 把傳輸與加密交握合併成 1 RTT；重用既有連線則省掉全部交握。距離造成的 RTT 無法靠協定消除，只能減少往返次數或縮短距離 | 第 1、13、18 章 |
| 0-2 | `curl -w` 的 `time_starttransfer` 減 `time_pretransfer` 大約代表什麼？`time_connect` 本身就是 TCP 交握的時間嗎？ | `-w` 的時間欄位都從開始累計，相鄰欄位相減才是各段長度；starttransfer 減 pretransfer 大約是伺服器處理時間（TTFB 中扣掉交握的部分）；connect 減 namelookup 才是 TCP 交握 | 第 3 章 |
| 0-3 | 為什麼解析網路封包時，Python 的 `struct` 格式字串要以 `!` 開頭？ | 網路協定的多 byte 數值一律是 big-endian 的 network byte order；`!` 同時指定 big-endian 與不自動對齊，避免原生 byte order 與 padding 造成欄位錯位 | 第 2 章 |
| 0-4 | ping 得通，但 API 連不上，代表什麼？下一步用什麼工具？ | ping 只證明 ICMP 在 IP 層可達，不代表 port 有開或服務健康；用 `nc -vz` 或 `curl -v` 檢查 TCP 與 HTTP，refused 代表封包到了但沒人 listen，timeout 代表封包被丟或到不了 | 第 3 章 |
| 0-5 | Ethernet MTU 1500 時，IPv4 上 UDP payload 最多多少 bytes？TCP 的 MSS 通常是多少？抓包為什麼常看到 1448？ | 1500 − 20（IPv4）− 8（UDP）＝ 1472；MSS ＝ 1500 − 20 − 20 ＝ 1460；timestamps option 佔 12 bytes，所以實際每個 segment 的資料常是 1448 | 第 2、8 章 |

### Part 1　網卡到路由（第 4–8 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 1-1 | 192.0.2.77/26 所在網段的網路位址、廣播位址與可用主機數是多少？ | /26 的區塊大小是 64，77 落在 64–127；網路位址 192.0.2.64，廣播位址 192.0.2.127，可用主機 64 − 2 ＝ 62 個 | 第 5 章 |
| 1-2 | 筆電的 routing table 同時有 VPN 推送的 10.0.0.0/8 與 Docker 的 10.20.0.0/16，往 10.20.30.5 的封包走哪裡？ | longest prefix match 先比 prefix 長度，/16 比 /8 更具體，所以走 Docker 的 bridge，到不了 VPN 後面的 staging；用 `ip route get` 或 `route -n get` 確認，修法是改掉重疊的網段 | 第 6 章 |
| 1-3 | 主機要送封包給不同網段的目的地時，ARP 問的是誰的 MAC？封包經過路由器時哪些位址會變？ | ARP 永遠問下一跳，跨網段時問 default gateway 的 MAC；每經過一台路由器，Ethernet header 的 MAC 就換一次，IP 的來源與目的位址不變（NAT 例外） | 第 4 章 |
| 1-4 | 為什麼 symmetric NAT 會讓 hole punching 失敗？WebRTC 怎麼處理？ | symmetric NAT 的 mapping 會隨目的地改變，STUN 學到的對外位址與 port 對另一端無效；若對方的 filtering 又檢查 port，打洞就失敗，只能透過 TURN 中繼 | 第 7、36 章 |
| 1-5 | 「連線能建立、小請求正常、大回應卡住」最可能是什麼？怎麼確認與修正？ | PMTUD 黑洞：路徑 MTU 變小（例如 VPN 或隧道），而 ICMP Type 3 Code 4（IPv6 是 Packet Too Big）被擋，傳送端反覆重傳同樣大小的滿載 segment；用帶 DF 的 `ping -s` 與 tcpdump 確認，修法是放行必要的 ICMP、在隧道端做 MSS clamping 或調整 MTU | 第 8 章 |

### Part 2　傳輸層（第 9–13 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 2-1 | TIME_WAIT 與 CLOSE_WAIT 各出現在哪一方？大量出現時各代表什麼？ | TIME_WAIT 在主動關閉方，持續約 2×MSL，確保最後的 ACK 能重送、舊 segment 消失，通常無害，正解是連線重用；CLOSE_WAIT 在被動關閉方，只有應用程式 close 才會離開，持續增加就是本機程式洩漏，最後以 `EMFILE` 爆發 | 第 10 章 |
| 2-2 | `Connection refused` 與 `Connection timed out` 的時間特徵與成因有什麼不同？accept queue 滿時 client 看到哪一種？ | refused 在約一個 RTT 內收到 RST，代表封包到了但沒人 listen；timeout 是 SYN 沒有回應（Linux 預設約 127 秒），代表被丟包或目標不存在；accept queue 滿時 Linux 預設丟掉 SYN，client 看到的是逾時 | 第 10 章、第 45 章 45.6 |
| 2-3 | 白板事件在 server 端「黏在一起」或被拆成兩半，原因是什麼？怎麼修？ | TCP 是 byte stream，不保留訊息邊界；一次 send 可能被拆成多次 recv，多次 send 也可能被一次讀到；要在應用層做 framing，例如 length-prefix，接收端累積 bytes 湊滿完整訊息並限制最大長度 | 第 11 章 |
| 2-4 | 台北到美東 RTT 180 ms，若 TCP 視窗卡在 64 KiB（沒有 window scale），單條連線的吞吐量上限約多少？要跑滿 100 Mbps 需要多大的視窗？ | 吞吐量上限約為視窗 ÷ RTT：65,536 bytes ÷ 0.18 s ≈ 364 KB/s ≈ 2.9 Mbps；BDP ＝ 100 Mbps × 0.18 s ＝ 18 Mbit ≈ 2.25 MB，需要 window scale 與足夠大的 socket buffer | 第 11、12 章 |
| 2-5 | HTTP/2 已經多工了，為什麼還需要 HTTP/3？QUIC 的 0-RTT 有什麼限制？ | HTTP/2 解決了 HTTP 層的 HOL，但所有 stream 共用一條 TCP，一個封包遺失會讓全部 stream 一起等；QUIC 讓每個 stream 獨立恢復，消除 TCP 層的 HOL，並以 connection ID 支援換網路。0-RTT 資料可能被重放，只能用於 idempotent 請求 | 第 12、13、22 章 |

### Part 3　DNS（第 14–16 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 3-1 | API 要換到新 IP，DNS 的正確搬遷順序是什麼？最壞要等多久？ | 至少提前一個舊 TTL 把 TTL 調低並等它過完、切換紀錄、保留舊服務直到實際流量歸零、再把 TTL 調回；最壞情況是「改動時間＋舊 TTL」，另外要考慮程式自己的快取與不會重新解析的長連線 | 第 14、15、16 章 |
| 3-2 | NXDOMAIN 與 NODATA 有什麼不同？負面快取會保留多久？ | NXDOMAIN 是名稱不存在；NODATA 是 RCODE 為 NOERROR 但沒有該 type 的答案；兩者都會被負面快取，時間取 SOA 本身的 TTL 與 MINIMUM 欄位的較小值 | 第 14、15 章 |
| 3-3 | `dig` 查到的答案正確，程式卻連到別的位址，可能是什麼原因？怎麼看程式真正拿到什麼？ | `dig` 直接問 nameserver，不讀 `/etc/hosts`、不走 nsswitch、預設不套 search；程式透過 `getaddrinfo` 可能命中 hosts 檔的遺留覆寫、search domain 或 runtime 快取；用 `getent ahosts` 重現程式看到的答案 | 第 16 章 |
| 3-4 | Kubernetes 的 Pod 解析一個外部名稱時，為什麼可能送出 10 個 DNS 請求？怎麼減少？ | `ndots:5` 讓點數少於 5 的名稱先套四個 search domain，加上本身共 5 個候選，每個都問 A 與 AAAA，共 10 個請求，其中 8 個是 NXDOMAIN；用結尾帶點的絕對名稱、調低 ndots 或使用 NodeLocal DNSCache | 第 16 章 |
| 3-5 | DNSSEC 與 DoH 各保護什麼？DNSSEC 驗證失敗時使用者看到什麼？ | DNSSEC 以 DS → DNSKEY → RRSIG 的信任鏈保護資料的完整性與來源，不提供機密性；DoH、DoT 加密 stub 到 resolver 這一段；驗證失敗時 resolver 回 SERVFAIL，用 `dig +cd` 對照可快速判斷 | 第 15 章 |

### Part 4　安全傳輸（第 17–19 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 4-1 | 驗證金流 webhook 時，為什麼不能用 `sha256(secret + body)`，也不能用 `==` 比較？ | 單純 hash 有 length extension 問題，帶金鑰的驗證一律用 HMAC；`==` 在第一個不同的 byte 停下，比較時間會洩漏資訊，要用 `hmac.compare_digest`；而且必須對收到的原始 bytes 驗證，不能先解析再序列化 JSON | 第 17、30 章 |
| 4-2 | TLS 1.3 如何在 1 RTT 內完成交握？什麼情況會多一個 RTT？ | client 在 ClientHello 先猜 group 並附上 key_share，server 在 ServerHello 回自己的 key_share 後即可導出金鑰，之後的訊息全部加密；猜錯 group 時 server 回 HelloRetryRequest，多花一個 RTT；憑證鏈太大也可能讓 QUIC 交握多一個 RTT | 第 13、18 章 |
| 4-3 | client 驗證憑證時檢查哪些項目？`*.shengsheng.example` 涵蓋 `shengsheng.example` 與 `a.b.shengsheng.example` 嗎？ | 建鏈到受信任的 root、簽章、CA 限制、效期、用途、名稱（只看 SAN）、撤銷；wildcard 只代表最左邊恰好一個 label，兩者都不涵蓋 | 第 18 章 |
| 4-4 | 只有部分使用者或部分時間看到憑證錯誤，可能是什麼？怎麼確認？ | 部分壞多半是缺中間憑證或多副本沒有同步更新，單一使用者壞多半是 client 時鐘或 TLS 攔截；用 `openssl s_client -servername` 逐一連到每個後端 IP，加 `-showcerts` 看鏈並比對序號；不能用關閉驗證來「解決」 | 第 19 章、第 45 章 45.5 |
| 4-5 | 聲聲 Live 對 TLS 0-RTT 的請求採什麼規則？為什麼？ | 0-RTT 資料可能被重放，所以只放行 GET 與 HEAD，其他請求回 425 Too Early；CDN 轉給 origin 時標記 `Early-Data: 1`，入口要清掉 client 自帶的同名 header | 第 13、18、22 章 |

### Part 5　HTTP 與 Web（第 20–25 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 5-1 | 哪些 method 是 idempotent？付款的 POST 逾時了，client 可以自動重試嗎？ | GET、HEAD、OPTIONS、PUT、DELETE 是 idempotent，POST 與 PATCH 不是；送出卻沒收到回應時無法判斷是否已處理，POST 要重試必須帶 `Idempotency-Key`，server 原子地佔住 key、存下回應並比對請求內容 | 第 20、24 章 |
| 5-2 | 首頁出現別人的名字，正確的修法是什麼？ | 兩道防線：origin 對個人化回應標 `Cache-Control: private`，CDN 對帶登入 cookie 的請求 bypass；只做一半不是外洩就是讓使用者看起來被登出；cache key 與 `Vary` 要包含所有會改變回應的因素 | 第 21、25 章 |
| 5-3 | CORS 擋的是什麼？為什麼它不是 CSRF 防禦？帶 credentials 時有什麼限制？ | 同源政策擋的是跨源「讀取回應」，CORS 是 server 放寬讀取的協議，請求仍會被送出，所以防 CSRF 要靠 SameSite、CSRF token 與 Origin 檢查；帶 credentials 時 ACAO 不能是 `*`，要逐字比對允許清單後回寫並加 `Vary: Origin` | 第 23 章 |
| 5-4 | gRPC 服務放在 L4 load balancer 後面，為什麼負載會嚴重不均？ | L4 以連線為單位分配，gRPC 與 HTTP/2 的長連線把大量請求多工在少數幾條連線上，新增的後端分不到流量；要改用以 stream 為單位分配的 L7 LB 或 client 端負載分散 | 第 22、24、25 章 |
| 5-5 | 後端怎麼從 `X-Forwarded-For` 取得可信的 client IP？ | 每一段都是寫下它的 proxy 看到的對端；面對 internet 的那一層覆寫、內部各層附加；後端從 TCP 對端開始從右往左跳過可信網段，遇到第一個不可信的位址就停；origin 還要鎖成只接受 CDN 與自家 LB 的連線 | 第 25、43 章 |

### Part 6　驗證與授權（第 26–30 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 6-1 | 密碼為什麼不能用 SHA-256 存？登入成功後為什麼要換 session ID？ | 快速 hash 讓資料庫外洩後的離線猜測太快，要用 scrypt 或 Argon2id 這類 memory-hard 雜湊加上每帳號獨立的 salt；登入與權限提升時輪替 session ID，是防止 session fixation 的根本做法 | 第 26 章 |
| 6-2 | JWT 的驗證清單有哪些？token 無效與權限不足分別回什麼？ | 格式、alg（只來自驗證端的允許清單，none 永遠不允許）、typ、kid（只當查表的 key）、簽章、exp／nbf 加時鐘容許、iss、aud，最後才是應用程式的授權判斷；token 缺少或無效回 401 並帶 `WWW-Authenticate`，scope 不足回 403 `insufficient_scope` | 第 27 章 |
| 6-3 | 停權的老師為什麼還能用 7 天的 JWT 改課表？聲聲 Live 怎麼改？ | self-contained token 簽出後在過期前難以撤銷；改為 5 分鐘的 access token 加 14 天、opaque、雜湊儲存、每次使用即輪替的 refresh token，已使用的 refresh token 再次出現就撤銷整個家族 | 第 27 章 |
| 6-4 | PKCE 與 `state` 各防什麼？code challenge 怎麼算？ | PKCE 讓兌換授權碼的人證明自己就是發起者，擋下授權碼被攔截後換 token，`code_challenge = BASE64URL(SHA256(code_verifier))`，只該用 S256；`state` 把回呼綁回發起授權的 session，擋下把攻擊者帳號塞給受害者的 CSRF。OAuth 2.1（截至 2026 年 10 月仍是草案）要求所有 client 使用 PKCE | 第 28 章 |
| 6-5 | 金流 webhook 重送造成學生被多加點數，正確的接收端要做哪些事？ | 對原始 body 驗 HMAC 簽章、檢查 timestamp 在容許範圍（例如 300 秒）內；webhook 是至少一次投遞，重試帶新簽章但相同 event id，用 event id 的唯一約束去重，並與入帳放在同一個交易；快速回 2xx、背景處理 | 第 24、30 章 |

### Part 7　即時通訊（第 31–33 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 7-1 | 「老師已上線」的通知該用 short polling、SSE 還是 WebSocket？判斷依據是什麼？ | 看方向、即時性與中間設備：只需要 server 往 client 推送、要即時，用 SSE（一般 HTTP、內建重連與 Last-Event-ID）；晚幾秒沒關係且資料共用可以 short polling；雙向高頻或二進位才用 WebSocket | 第 31、32 章 |
| 7-2 | SSE 事件總是「一批一批到」，最可能的原因與排查方法是什麼？ | 緩衝：nginx 預設的 `proxy_buffering`、壓縮、應用程式沒 flush、CDN；回 `X-Accel-Buffering: no` 或關掉該路徑的緩衝與壓縮，並用 `curl -N` 從後端一段一段往前測，找出是哪一層在緩衝 | 第 31 章 |
| 7-3 | `Sec-WebSocket-Accept` 怎麼算？它是認證嗎？client frame 為什麼要 mask？ | base64(SHA-1(key＋"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))，只用來確認對方理解 WebSocket，不是認證；client 送出的每個 frame 都要用隨機 key mask，防止惡意網頁控制線上 bytes 污染不懂 WebSocket 的中間設備，不是加密 | 第 32 章 |
| 7-4 | 安靜的教室每隔固定秒數就斷線，前端看到 1006，最可能是什麼？ | 心跳停用或間隔比路徑上某一層的 idle timeout 長（例如 nginx `proxy_read_timeout`、LB idle timeout）；聲聲 Live 的設定是 server 每 25 秒 ping、nginx 75 秒、LB 120 秒；先看 close code 決定是誰關的，再看距上一則訊息的秒數 | 第 32、33 章、第 45 章 45.10 |
| 7-5 | 重連時怎麼做到不漏也不重複？ | 網路上沒有真正的 exactly-once，要靠 at-least-once 加冪等：每個房間單一序號產生器編號，上行依 `client_msg_id` 去重、下行依序號去重；重連時先訂閱即時串流再讀補發緩衝，缺口太大改送快照；重連時機用指數退避加 jitter | 第 33 章 |

### Part 8　即時影音（第 34–39 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 8-1 | Opus 以 20 ms 為一個 frame 時，RTP timestamp 每個封包增加多少？視訊的 timestamp 用什麼時鐘？ | Opus 的 RTP 時鐘是 48 kHz，20 ms 是 960 個樣本，所以每包加 960；視訊用 90 kHz，同一個 frame 的封包 timestamp 相同；序號與 timestamp 都會回繞，遺失只看序號 | 第 34 章 |
| 8-2 | 程式把 H.264 的 payload type 寫死成 98，為什麼會讓視訊變黑？answer 必須遵守哪些規則？ | PT 只是單一 session 內的臨時編號，意思完全由 `a=rtpmap` 決定，不能寫死；answer 的 m 段數量、順序與 mid 不變，拒絕用 port 0 而不刪段，codec 取交集並沿用 offer 的 PT | 第 35 章 |
| 8-3 | ICE 的 host、srflx、relay candidate 分別是什麼？在只放行 TCP 443 的企業網路裡，視訊怎麼連上？代價是什麼？ | host 是本機位址，srflx 是 STUN 看到的 NAT 外位址，relay 是 TURN 配的中繼位址；UDP 被擋時只能走 TURN over TLS 443，能穿過多數防火牆，但 TCP 會把丟包轉成延遲尖峰 | 第 36、39 章 |
| 8-4 | 六人小班為什麼不用 mesh？SFU 的 simulcast 怎麼幫助接收者？ | mesh 每人要上傳 N−1＝5 份、編碼負擔也隨人數成長，被上行頻寬與 CPU 擋住；SFU 讓每人只上傳一份，伺服器只轉送不解碼；simulcast 讓送端同時編出多層，SFU 依每位接收者的版面與頻寬選層 | 第 37 章 |
| 8-5 | SRT 的 latency 該怎麼設？`pktRcvDrop` 大於 0 代表什麼？ffmpeg 與 libsrt 的單位有什麼差別？ | latency 是收方刻意加上的交付延遲，決定期限內能重傳幾次，經驗上至少是 RTT 的 3–4 倍，丟包越多倍數越大，且不低於預設 120 ms；重傳補回是正常的，`pktRcvDrop` 大於 0 才代表視窗不夠；libsrt 用毫秒，ffmpeg 的 URL 參數用微秒 | 第 38、39 章 |

### Part 9　Python Web 堆疊（第 40–43 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 9-1 | WSGI app 的介面是什麼？webhook 驗簽時為什麼要先 `request.get_data()`？ | `app(environ, start_response)` 回傳 bytes 的 iterable；`wsgi.input` 只能讀一次，也只能讀 `CONTENT_LENGTH` 那麼多，驗簽需要原始 body，要先取得並快取，之後才能解析 | 第 41 章 |
| 9-2 | 為什麼 Werkzeug 的 interactive debugger 絕不能出現在 production？ | debugger 讓網頁使用者執行任意 Python 程式，PIN 只是最後一道防線；debugger 與開發伺服器只能在開發者自己的電腦上、只聽 127.0.0.1 | 第 41 章 |
| 9-3 | uvicorn 服務上「連不做事的 health check 端點都很慢」，最可能是什麼？怎麼修？ | event loop 被阻塞：合作式多工只在 `await` 切換，同步網路 I/O、`time.sleep`、CPU 密集計算會讓整個 process 的所有連線停住；換 async 函式庫、用 `asyncio.to_thread` 或 executor，CPU 重活用 process pool；用 loop lag 監控發現 | 第 42 章 |
| 9-4 | timeout 鏈與 keep-alive 的方向規則各是什麼？違反時的典型症狀？ | 請求逾時外層比內層長，最內層先放棄並回有意義的錯誤；keep-alive 方向相反，每一段 server 端的閒置上限都要比重用連線的 client 端長；gunicorn keep-alive 比 nginx upstream 短時，nginx 會把請求送進已關閉的連線而回 502 | 第 43 章 |
| 9-5 | zero-downtime deploy 的 graceful shutdown 順序是什麼？ | readiness 先回 503、等上游停止送流量（drain）、關閉 listening socket、等進行中的請求做完，最後才是 SIGKILL 的保險；gunicorn 本身不會做 drain，Kubernetes 與 LB 的寬限時間要比排空流程長 | 第 25、43 章 |

### Part 10　營運與整合（第 44–46 章）

| # | 題目 | 答案要點 | 章節 |
|---|---|---|---|
| 10-1 | 新建的 private 子網裡的機器連外一律逾時，最先檢查什麼？security group 與 network ACL 的差別？ | 先查 route table 有沒有指向 NAT gateway 的 default route，雲端路由查不到時默默丟棄，client 只看到逾時；security group 是 stateful、掛在網路介面、只有允許規則，NACL 是 stateless、掛在子網、依編號比對，回程要放行 ephemeral port | 第 44 章 |
| 10-2 | 叢集用 VXLAN overlay 時，為什麼 Pod 的 MTU 是 1450？設錯會怎樣？ | VXLAN 把整個 Ethernet frame 包進 UDP 4789，IPv4 外層總負擔 50 bytes，1500 的底層只剩 1450 給 Pod；設錯的症狀是小請求正常、大回應卡住，和 PMTUD 黑洞一樣 | 第 8、44 章 |
| 10-3 | 由下而上、由上而下與分半法各適合什麼情境？分半法最常用的中點是什麼？ | 由下而上適合完全不通與新環境；由上而下適合手上有明確錯誤訊息；分半法適合路徑長又沒有線索；`curl --resolve` 繞過 CDN 直打 LB 是最常用的中點 | 第 45 章 |
| 10-4 | 學生說「看不到老師、也聽不到」，排查順序是什麼？ | WebRTC 媒體共用同一組雙向驗證的 candidate pair，純網路造成的單向問題很少見；先看 candidate-pair 的雙向 bytes 排除網路，再沿 SDP（是否被拒絕或方向錯）、送端、SFU、收端、播放（autoplay）逐站確認第一個「上游有、這裡沒有」的地方 | 第 39 章、第 45 章 45.11 |
| 10-5 | 例題：尖峰每秒 1,200 個 API 請求、平均處理 0.15 秒，同時在忙的請求約多少？目標使用率 70% 時至少要準備多少個 worker 容量？ | Little's law：L ＝ λ × W ＝ 1,200 × 0.15 ＝ 180；除以 0.7 約 258 個 worker（或 thread）容量，再用 CPU、記憶體與下游資料庫連線數驗證，並加上 N+1 的餘裕 | 第 43、46 章 |

做完 55 題之後，可以回到第 46 章 46.18 的 15 題面試題做最後的整合練習：那 15 題每一題都橫跨好幾個 Part，正好檢驗你能不能把分散在各章的機制串成一個完整的回答。
