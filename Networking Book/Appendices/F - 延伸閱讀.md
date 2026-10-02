# 附錄 F　延伸閱讀

> [!abstract] 本附錄地圖
> **用途**：本書正文已經把每個機制講到能自己推導；這份附錄告訴你「想再往下挖時，權威的原文在哪裡」。它彙整全書 46 章「延伸閱讀」節列過的 RFC、W3C／WHATWG 規格、官方文件、論文與書籍，依主題分類，並標出每一項對應的章節。
>
> **怎麼查**：
> - 依主題找小節：F.2–F.15 是主題清單，F.16 是經典書籍，F.17 是 RFC 速查表（只有編號、名稱與章節，最適合「看到一個 RFC 編號想知道是什麼」），F.18 是仍在變動的規格狀態，F.19 是建議閱讀順序。
> - 每張表的欄位固定為：名稱｜編號｜作者或機構｜年份｜為何值得讀｜章節。RFC 的「作者或機構」一律寫發布的組織（IETF 或 Independent Submission），不列個人作者。
> - 年份只寫有把握的；空白（—）代表本書不確定或該文件持續更新。編號不確定的項目只寫名稱並標「編號待核對」。
> - 本附錄**不放網址**：RFC 用編號就能在 RFC Editor 或 IETF datatracker 找到，其他文件用名稱加機構搜尋即可。
> - 標示「截至 2026 年 10 月」的狀態會隨時間改變，引用前請再確認一次。

## F.1 先認識文件的種類

讀延伸資料之前，先分清楚手上的文件屬於哪一種，因為它們的「權威程度」與「會不會變」差很多。**RFC**（Request for Comments）是 IETF 等組織發布的編號文件，一旦發布內容就不再修改；要修正只能發一份新的 RFC，並在新文件上標註 **obsoletes**（完全取代舊文件）或 **updates**（修改舊文件的一部分）。例如 TCP 的現行規格是 RFC 9293，它 obsoletes 了 1981 年的 RFC 793；讀到舊部落格引用 RFC 793 時，要知道規格已經整併到新文件裡（第 10 章）。

**Internet-Draft**（草案）是還在討論中的文件，名稱像 `draft-ietf-oauth-v2-1-16`，最後的數字是修訂版次，草案大約六個月沒更新就會過期。草案可以拿來理解趨勢，但不能當成定案的標準，也不要預測它會拿到哪個 RFC 編號。**Living standard**（持續更新的標準）是 WHATWG 的做法，例如 Fetch Standard 與 HTML Standard，沒有版本號，引用時要寫存取日期。W3C 的規格則有明確的成熟度階段，最終階段是 **Recommendation**。

| 文件類型 | 例子 | 會不會變 | 引用方式 | 本書用到的章節 |
|---|---|---|---|---|
| RFC（Standards Track） | RFC 9293 TCP | 發布後不變，靠新 RFC 取代 | 「RFC 9293〈Transmission Control Protocol (TCP)〉」 | 全書 |
| BCP（Best Current Practice） | BCP 14（RFC 2119 + RFC 8174） | BCP 編號固定，內容可換成新 RFC | 寫 RFC 編號，必要時加 BCP 編號 | 第 2、15、27、28 章 |
| Informational RFC | RFC 8216 HLS | 同 RFC | 同 RFC，注意它不是標準 | 第 38 章 |
| Internet-Draft | draft-ietf-oauth-v2-1 | 持續修訂，可能過期 | 寫 draft 名稱與版次，加「截至某年某月」 | 第 27、28、32、38 章 |
| W3C Recommendation | WebRTC 1.0、WebAuthn Level 3 | 有版本日期，可發布修訂版 | 寫規格名稱與等級 | 第 29、35、36 章 |
| WHATWG living standard | Fetch、HTML（SSE）、WebSockets | 隨時更新 | 寫名稱與存取日期 | 第 23、31、32 章 |
| ISO／ITU-T／IEEE 標準 | ISO/IEC 23009-1、ITU-T G.114、IEEE 802.3 | 依版次發布 | 寫標準編號與名稱 | 第 2、4、34、38、39 章 |
| 開源專案文件 | libsrt、gunicorn、Werkzeug | 隨版本更新 | 寫專案名稱與文件標題，標版本 | 第 38、41–43 章 |

RFC 裡大寫的 MUST、SHOULD、MAY 有精確意義，定義在 RFC 2119 與 RFC 8174（合稱 BCP 14，第 2 章）：MUST 是不做就不符合規格，SHOULD 是「除非有充分理由，否則要做」，MAY 是可選。讀規格時先找這些字，就能快速分辨「一定要實作」與「建議」。

```text
 一份規格的生命週期（以 IETF 為例）

 individual draft ──► WG draft ──► WG Last Call ──► IESG 審查 ──► RFC Editor queue ──► RFC（取得編號）
  draft-某人-主題      draft-ietf-wg-主題    （WGLC）                                     │
       │                    │                                                            └─► 之後可能被新 RFC
       └── 沒人推動就過期     └── 每次修訂版次 +1（-00、-01 …）                                  obsoletes／updates

 例：SRT 停在最左邊（individual draft 已過期）；OAuth 2.1 在 WG draft；
     6265bis 在 RFC Editor queue；RFC 9846 已發布並取代 RFC 8446（狀態截至 2026 年 10 月）
```

這張圖從左到右是一份 IETF 文件正常的路徑。最左邊的 individual draft 由個人提出，沒有工作小組（WG）採納就停在這裡，SRT 的草案就是這種情況。被 WG 採納後改名為 `draft-ietf-…`，經過多次修訂與 Last Call，再送 IESG 審查，核准後進 RFC Editor queue 排版，最後才取得編號。圖下方標出本書提到的幾份文件各自停在哪一步，F.18 有完整的狀態表。

## F.2 分層與封包

這一組文件是全書的地基：IP、UDP、ICMP 的原始規格篇幅都不長，配合第 2 章的位元布局圖讀，很快就能讀完。RFC 791 雖然是 1981 年的文件，IPv4 header 的定義至今沒變。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| Internet Protocol | RFC 791 | IETF | 1981 | IPv4 header 每個欄位的原始定義，篇幅短、圖清楚 | 第 2、5 章 |
| User Datagram Protocol | RFC 768 | IETF | 1980 | 只有三頁，整個 UDP 就是 8 bytes 的 header | 第 2、9 章 |
| Internet Protocol, Version 6 (IPv6) Specification | RFC 8200 | IETF | 2017 | IPv6 固定 40 bytes header、extension header 與最小 MTU 1280 | 第 2、5 章 |
| Computing the Internet Checksum | RFC 1071 | IETF | 1988 | 一補數加總的推導與實作技巧，第 2 章程式的依據 | 第 2、8、9 章 |
| Key words for use in RFCs to Indicate Requirement Levels | RFC 2119、RFC 8174（BCP 14） | IETF | 1997、2017 | 讀懂所有 RFC 裡 MUST／SHOULD／MAY 的精確意義 | 第 2 章 |
| Uniform Resource Identifier (URI): Generic Syntax | RFC 3986 | IETF | 2005 | URL 各部分（scheme、authority、path、query）的正式語法 | 第 1 章 |
| Happy Eyeballs Version 2: Better Connectivity Using Concurrency | RFC 8305 | IETF | 2017 | IPv4／IPv6 同時嘗試連線的演算法，解釋「為什麼有時連得慢」 | 第 1、5、16 章 |
| On Holy Wars and a Plea for Peace | IEN 137 | Danny Cohen | 1980 | big-endian 與 little-endian 名稱的出處，理解 network byte order | 第 2 章 |
| Populating the page: how browsers work | — | MDN Web Docs | — | 從輸入網址到畫面出現的瀏覽器端流程 | 第 1 章 |
| struct — Interpret bytes as packed binary data | — | Python 官方文件 | — | 用 `struct` 打包與解析 header 的格式字元 | 第 2 章 |

## F.3 鏈結層、IP 位址與 MTU

鏈結層的權威文件是 IEEE 標準而不是 RFC，篇幅龐大，一般工程師只需要讀到 frame 格式與 VLAN 的概念；ARP、位址規劃與 MTU 的 RFC 才是日常除錯最常翻的。RFC 8900 與 RFC 4890 特別值得讀，前者解釋為什麼應該避免 IP 分片，後者說明 ICMPv6 不能全擋。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| Ethernet | IEEE 802.3 | IEEE | — | Ethernet frame、MAC 位址與實體層的正式標準 | 第 2、4 章 |
| Bridges and Bridged Networks | IEEE 802.1Q | IEEE | — | VLAN tag、交換器學習與轉送、生成樹 | 第 4 章 |
| An Ethernet Address Resolution Protocol | RFC 826 | IETF | 1982 | ARP 的原始設計，理解 IP 到 MAC 的對應 | 第 4 章 |
| IPv4 Address Conflict Detection | RFC 5227 | IETF | 2008 | gratuitous ARP 與位址衝突偵測 | 第 4 章 |
| Host Extensions for IP Multicasting | RFC 1112 | IETF | 1989 | IPv4 群播位址如何對應到 MAC 位址 | 第 4 章 |
| Classless Inter-domain Routing (CIDR) | RFC 4632 | IETF | 2006 | `/24` 這種寫法與路由彙總的由來 | 第 5 章 |
| Address Allocation for Private Internets | RFC 1918 | IETF | 1996 | 10/8、172.16/12、192.168/16 私有位址的定義 | 第 5、7 章 |
| Special-Purpose IP Address Registries | RFC 6890 | IETF | 2013 | 所有特殊用途位址（loopback、文件用位址等）的總表 | 第 5 章 |
| IP Version 6 Addressing Architecture | RFC 4291 | IETF | 2006 | IPv6 位址種類、link-local 與 interface ID | 第 5 章 |
| A Recommendation for IPv6 Address Text Representation | RFC 5952 | IETF | 2010 | IPv6 位址的標準寫法（小寫、`::` 怎麼縮） | 第 5 章 |
| Neighbor Discovery for IP version 6 | RFC 4861 | IETF | 2007 | IPv6 用來取代 ARP 的 NDP | 第 5 章 |
| IPv6 Stateless Address Autoconfiguration | RFC 4862 | IETF | 2007 | SLAAC：主機如何自己產生 IPv6 位址 | 第 5 章 |
| Internet Control Message Protocol | RFC 792 | IETF | 1981 | ping、traceroute 與 Fragmentation Needed 的訊息格式 | 第 3、6、8 章 |
| ICMPv6 for the IPv6 Specification | RFC 4443 | IETF | 2006 | Packet Too Big 等 ICMPv6 訊息 | 第 8 章 |
| Path MTU Discovery | RFC 1191 | IETF | 1990 | IPv4 的 PMTUD 與 DF bit | 第 8 章 |
| Path MTU Discovery for IP version 6 | RFC 8201 | IETF | 2017 | IPv6 的 PMTUD（IPv6 路由器不分片） | 第 8 章 |
| Packetization Layer Path MTU Discovery | RFC 4821 | IETF | 2007 | 不依賴 ICMP 的 PLPMTUD，解決 black hole | 第 8 章 |
| Packetization Layer Path MTU Discovery for Datagram Transports | RFC 8899 | IETF | 2020 | 把 PLPMTUD 用在 UDP 類協定（QUIC 的基礎之一） | 第 8、13 章 |
| TCP Problems with Path MTU Discovery | RFC 2923 | IETF | 2000 | PMTUD black hole 的經典整理 | 第 8 章 |
| IP Fragmentation Considered Fragile | RFC 8900 | IETF | 2020 | 為什麼應該避免依賴 IP 分片 | 第 8 章 |
| Recommendations for Filtering ICMPv6 Messages in Firewalls | RFC 4890 | IETF | 2007 | 哪些 ICMPv6 一定要放行，Rita 的防火牆政策依據 | 第 8 章 |
| ipaddress — IPv4/IPv6 manipulation library | — | Python 官方文件 | — | 用標準函式庫計算子網、判斷私有位址 | 第 5 章 |
| ip-neighbour(8) 與核心 neighbour／arp sysctl 文件 | — | Linux man-pages、Linux kernel 文件 | — | 查看與調整 ARP／NDP 快取的實際工具 | 第 4 章 |

## F.4 路由與 NAT

路由這一組的重點是 BGP 與路由安全：RFC 4271 定義協定本身，RFC 6811 與 RFC 7908 談 origin 驗證與 route leak，是理解「為什麼某天半個網際網路連不到某服務」的入口。NAT 的行為要求（RFC 4787、RFC 5382）則直接決定第 36 章 WebRTC 的 ICE 能不能打洞成功。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| A Border Gateway Protocol 4 (BGP-4) | RFC 4271 | IETF | 2006 | 網際網路之間交換路由的協定，path attribute 與選路 | 第 6 章 |
| Requirements for IP Version 4 Routers | RFC 1812 | IETF | 1995 | 路由器轉送、TTL 遞減與 ICMP 產生的要求 | 第 6 章 |
| BGP Prefix Origin Validation | RFC 6811 | IETF | 2013 | RPKI ROV：驗證「這個 prefix 該由誰宣告」 | 第 6 章 |
| Problem Definition and Classification of BGP Route Leaks | RFC 7908 | IETF | 2016 | route leak 的分類，讀懂事故報告的詞彙 | 第 6 章 |
| MANRS 網路業者實務指南 | — | MANRS（Mutually Agreed Norms for Routing Security） | — | 路由安全的業界實務：過濾、反偽造、協調 | 第 6 章 |
| Traditional IP Network Address Translator | RFC 3022 | IETF | 2001 | NAT 與 NAPT 的基本運作 | 第 7 章 |
| NAT Behavioral Requirements for Unicast UDP | RFC 4787 | IETF | 2007 | mapping 與 filtering 行為的分類，P2P 能否打洞的關鍵 | 第 7、9、36 章 |
| NAT Behavioral Requirements for TCP | RFC 5382 | IETF | 2008 | TCP 經過 NAT 的要求，包含閒置逾時的下限 | 第 7 章 |
| State of Peer-to-Peer (P2P) Communication across NATs | RFC 5128 | IETF | 2008 | hole punching 技術的整理，ICE 的背景知識 | 第 7、36 章 |
| Common Requirements for Carrier-Grade NATs (CGNs) | RFC 6888 | IETF | 2013 | 電信業者大型 NAT 的要求 | 第 7 章 |
| IANA-Reserved IPv4 Prefix for Shared Address Space | RFC 6598 | IETF | 2012 | 100.64.0.0/10 的由來 | 第 7 章 |
| Logging Recommendations for Internet-Facing Servers | RFC 6302 | IETF | 2011 | 在 NAT 後面為什麼 log 一定要記來源 port 與精確時間 | 第 7 章 |
| nftables wiki 與 conntrack-tools 手冊 | — | netfilter 專案 | — | Linux 防火牆與連線追蹤的實際設定 | 第 7 章 |

## F.5 TCP、UDP 與 QUIC

傳輸層的文件最多，建議以 RFC 9293 為主軸，其他 RFC 當成「某個機制的完整版」查。擁塞控制有三篇必讀論文：Van Jacobson 1988 年的論文奠定了 slow start 與 congestion avoidance，BBR 與 Bufferbloat 兩篇則解釋了現代網路為什麼「頻寬夠卻很慢」。QUIC 的四份核心 RFC 在 2021 年一起發布，RFC 9000 是主體。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| UDP Usage Guidelines | RFC 8085 | IETF | 2017 | 在 UDP 上自己設計協定時要負起的責任（擁塞、MTU、keepalive） | 第 9 章 |
| IANA Procedures for the Management of the Service Name and Transport Protocol Port Number Registry | RFC 6335 | IETF | 2011 | port 範圍（system、user、dynamic）的正式定義 | 第 9 章 |
| Transmission Control Protocol (TCP) | RFC 9293 | IETF | 2022 | TCP 的現行規格，整併 RFC 793 與多份更新，含狀態機與 MSL | 第 1、3、10、11 章 |
| Defending against Sequence Number Attacks | RFC 6528 | IETF | 2012 | ISN 為什麼要不可預測、怎麼產生 | 第 10 章 |
| TCP SYN Flooding Attacks and Common Mitigations | RFC 4987 | IETF | 2007 | SYN flood 與 SYN cookies 的防禦整理 | 第 10 章 |
| Improving TCP's Robustness to Blind In-Window Attacks | RFC 5961 | IETF | 2010 | challenge ACK 機制，解釋某些「奇怪的 ACK」 | 第 10 章 |
| TCP Extensions for High Performance | RFC 7323 | IETF | 2014 | Window Scale、Timestamps 與 PAWS | 第 10、11 章 |
| Computing TCP's Retransmission Timer | RFC 6298 | IETF | 2011 | SRTT、RTTVAR、RTO 的計算與退避 | 第 11 章 |
| TCP Congestion Control | RFC 5681 | IETF | 2009 | slow start、congestion avoidance、fast retransmit／recovery | 第 11、12 章 |
| TCP Selective Acknowledgment Options | RFC 2018 | IETF | 1996 | SACK 選項的格式 | 第 11 章 |
| An Extension to the SACK Option for TCP | RFC 2883 | IETF | 2000 | D-SACK：回報重複收到的資料 | 第 11 章 |
| The RACK-TLP Loss Detection Algorithm for TCP | RFC 8985 | IETF | 2021 | 以時間而非重複 ACK 數判斷遺失的現代做法 | 第 11 章 |
| Congestion Control in IP/TCP Internetworks | RFC 896 | IETF | 1984 | Nagle 演算法的原始文件 | 第 11 章 |
| Requirements for Internet Hosts -- Communication Layers | RFC 1122 | IETF | 1989 | delayed ACK、keepalive 等主機端要求 | 第 11 章 |
| CUBIC for Fast and Long-Distance Networks | RFC 9438 | IETF | 2023 | Linux 預設的擁塞控制演算法 | 第 12 章 |
| Increasing TCP's Initial Window | RFC 6928 | IETF | 2013 | 初始壅塞視窗 10 個 segment 的依據 | 第 12、46 章 |
| Controlled Delay Active Queue Management | RFC 8289 | IETF | 2018 | CoDel：用排隊時間而非佇列長度做 AQM | 第 12 章 |
| The Flow Queue CoDel Packet Scheduler and AQM Algorithm | RFC 8290 | IETF | 2018 | FQ-CoDel，許多 Linux 系統的預設排程器 | 第 12 章 |
| The Addition of Explicit Congestion Notification (ECN) to IP | RFC 3168 | IETF | 2001 | 不丟封包也能通知擁塞的 ECN | 第 12 章 |
| Congestion Avoidance and Control | — | Van Jacobson（SIGCOMM） | 1988 | TCP 擁塞控制的起點，解釋 1986 年的網路崩潰 | 第 12 章 |
| BBR: Congestion-Based Congestion Control | — | Neal Cardwell 等（ACM Queue） | 2016 | 以頻寬與 RTT 建模、不以丟包為訊號的擁塞控制 | 第 12 章 |
| Bufferbloat: Dark Buffers in the Internet | — | Jim Gettys、Kathleen Nichols（ACM Queue） | 2011 | 過大的緩衝區為什麼讓延遲暴增 | 第 12 章 |
| Version-Independent Properties of QUIC | RFC 8999 | IETF | 2021 | 所有 QUIC 版本都不變的部分（中間設備能依賴什麼） | 第 13 章 |
| QUIC: A UDP-Based Multiplexed and Secure Transport | RFC 9000 | IETF | 2021 | QUIC 主規格：connection ID、stream、流量控制、遷移 | 第 13 章 |
| Using TLS to Secure QUIC | RFC 9001 | IETF | 2021 | QUIC 如何把 TLS 1.3 交握整合進傳輸層 | 第 13 章 |
| QUIC Loss Detection and Congestion Control | RFC 9002 | IETF | 2021 | QUIC 的遺失偵測與 PTO | 第 13 章 |
| An Unreliable Datagram Extension to QUIC | RFC 9221 | IETF | 2022 | 在 QUIC 上送不重傳的 datagram | 第 13 章 |
| Applicability of the QUIC Transport Protocol | RFC 9308 | IETF | 2022 | 應用程式何時、如何使用 QUIC | 第 13 章 |
| Manageability of the QUIC Transport Protocol | RFC 9312 | IETF | 2022 | 營運者在 QUIC 加密後還能觀察到什麼 | 第 13 章 |
| socket 與 asyncio Transports and Protocols | — | Python 官方文件 | — | 標準函式庫的 socket API 與非同步介面 | 第 9、40 章 |
| tcp(7)、socket(7)、listen(2)、ss(8) | — | Linux man-pages | — | backlog、socket 選項與 `ss` 欄位的權威說明 | 第 10 章 |

## F.6 DNS

DNS 的兩份原始規格（RFC 1034、RFC 1035）至今仍是基礎，但很多細節已被後續 RFC 修改，所以建議先讀 RFC 9499 的術語，再回頭讀原始規格。負快取（RFC 2308）與 EDNS(0)（RFC 6891）是除錯時最常用到的兩份。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| Domain Names - Concepts and Facilities | RFC 1034 | IETF | 1987 | DNS 的階層、zone、delegation 與 resolver 概念 | 第 14 章 |
| Domain Names - Implementation and Specification | RFC 1035 | IETF | 1987 | DNS 訊息格式、名稱壓縮與 record 格式 | 第 14 章 |
| DNS Terminology | RFC 9499 | IETF | 2024 | 統一各種 DNS 名詞，讀其他 DNS RFC 前的字典 | 第 14 章 |
| Extension Mechanisms for DNS (EDNS(0)) | RFC 6891 | IETF | 2013 | 擴大 UDP 訊息、OPT record 與 DO bit | 第 14、15 章 |
| DNS Transport over TCP - Implementation Requirements | RFC 7766 | IETF | 2016 | DNS over TCP 為什麼是必要功能而非選配 | 第 14 章 |
| Negative Caching of DNS Queries (DNS NCACHE) | RFC 2308 | IETF | 1998 | NXDOMAIN 會被快取多久（SOA minimum） | 第 14、15 章 |
| Service Binding and Parameter Specification via the DNS (SVCB and HTTPS RRs) | RFC 9460 | IETF | 2023 | HTTPS record：在 DNS 裡宣告 h3、ECH 等參數 | 第 14、15 章 |
| DNSSEC 導論、資源紀錄與協定修改 | RFC 4033、RFC 4034、RFC 4035 | IETF | 2005 | DNSSEC 的信任鏈、DNSKEY、RRSIG、DS | 第 15 章 |
| DNS Security Extensions (DNSSEC)（BCP 237） | RFC 9364 | IETF | 2023 | DNSSEC 相關 RFC 的導覽 | 第 15 章 |
| Client Subnet in DNS Queries | RFC 7871 | IETF | 2016 | ECS：CDN 如何依使用者位置回答 | 第 15 章 |
| DNS Queries over HTTPS (DoH) | RFC 8484 | IETF | 2018 | 用 HTTPS 送 DNS 查詢 | 第 15 章 |
| Specification for DNS over Transport Layer Security (TLS) | RFC 7858 | IETF | 2016 | DoT，Android Private DNS 使用的協定 | 第 15 章 |
| DNS over Dedicated QUIC Connections | RFC 9250 | IETF | 2022 | DoQ | 第 15 章 |
| Extended DNS Errors | RFC 8914 | IETF | 2020 | SERVFAIL 背後的細部原因碼 | 第 15 章 |
| Basic Socket Interface Extensions for IPv6 | RFC 3493 | IETF | 2003 | `getaddrinfo` 介面的定義 | 第 16 章 |
| Default Address Selection for IPv6 | RFC 6724 | IETF | 2012 | 有多個位址時作業系統怎麼排序 | 第 16 章 |
| A DNS RR for specifying the location of services (DNS SRV) | RFC 2782 | IETF | 2000 | SRV record，Kubernetes 也會產生 | 第 16 章 |
| resolv.conf(5) 與 nsswitch.conf(5) | — | Linux man-pages | — | `ndots`、`search`、查詢順序的權威說明 | 第 16 章 |
| DNS for Services and Pods；Using NodeLocal DNSCache | — | Kubernetes 官方文件 | — | 叢集內 DNS 名稱與快取的設定 | 第 16、44 章 |

## F.7 密碼學與 TLS

密碼學這一組不必從數學讀起：RFC 2104（HMAC）與 RFC 5869（HKDF）都很短，而且附有測試向量，可以直接拿來驗證第 17 章的程式。TLS 的部分建議搭配 RFC 8448 讀，它把一次完整交握的每個位元組與每把金鑰都列出來，是理解金鑰排程最快的方法。憑證營運的文件則集中在第 19 章。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| HMAC: Keyed-Hashing for Message Authentication | RFC 2104 | IETF | 1997 | HMAC 的定義與為什麼不能用 hash(key + msg) | 第 17、30 章 |
| HMAC-based Extract-and-Expand Key Derivation Function (HKDF) | RFC 5869 | IETF | 2010 | TLS 1.3 金鑰排程的基礎，附測試向量 | 第 17 章 |
| An Interface and Algorithms for Authenticated Encryption | RFC 5116 | IETF | 2008 | AEAD 介面：key、nonce、plaintext、associated data | 第 17 章 |
| Galois/Counter Mode (GCM) and GMAC | NIST SP 800-38D | NIST | 2007 | AES-GCM 的規格與 nonce 不可重複的限制 | 第 17 章 |
| Recommendation for Key Management, Part 1 | NIST SP 800-57 Part 1 | NIST | — | 各演算法金鑰長度與安全強度對照 | 第 17 章 |
| Module-Lattice-Based Key-Encapsulation Mechanism Standard（ML-KEM） | FIPS 203 | NIST | 2024 | 後量子金鑰封裝，TLS 混合金鑰交換的一半 | 第 17、18 章 |
| Module-Lattice-Based Digital Signature Standard（ML-DSA） | FIPS 204 | NIST | 2024 | 後量子簽章標準 | 第 17 章 |
| The Transport Layer Security (TLS) Protocol Version 1.3 | RFC 8446 | IETF | 2018 | TLS 1.3 的原始規格；新版見 F.18 | 第 1、18 章 |
| Example Handshake Traces for TLS 1.3 | RFC 8448 | IETF | 2019 | 逐位元組的交握範例與金鑰排程測試向量 | 第 18 章 |
| Internet X.509 PKI Certificate and CRL Profile | RFC 5280 | IETF | 2008 | 憑證欄位、extension 與鏈驗證演算法 | 第 18、19 章 |
| Service Identity in TLS | RFC 9525 | IETF | 2023 | 主機名稱比對與 wildcard 規則（取代 RFC 6125） | 第 18 章 |
| TLS Extensions: Extension Definitions | RFC 6066 | IETF | 2011 | SNI 等擴充 | 第 18 章 |
| TLS Application-Layer Protocol Negotiation Extension | RFC 7301 | IETF | 2014 | ALPN：在交握中決定 h2 或 http/1.1 | 第 18、22 章 |
| Using Early Data in HTTP | RFC 8470 | IETF | 2018 | 0-RTT 的重放風險、`Early-Data` header 與 425 | 第 18 章 |
| Automatic Certificate Management Environment (ACME) | RFC 8555 | IETF | 2019 | 自動簽發憑證的協定，憑證效期縮短後的必要工具 | 第 16、19 章 |
| ACME TLS-ALPN Challenge Extension | RFC 8737 | IETF | 2020 | TLS-ALPN-01 驗證方式 | 第 19 章 |
| ACME Renewal Information（ARI） | RFC 9773 | IETF | — | CA 告訴 client 建議的更新時間窗 | 第 19 章 |
| HTTP Strict Transport Security (HSTS) | RFC 6797 | IETF | 2012 | 強制瀏覽器只用 HTTPS 連線 | 第 19 章 |
| Certificate Transparency | RFC 6962 | IETF | 2013 | CT log、SCT 與 Merkle tree，發現誤發憑證 | 第 19 章 |
| DNS Certification Authority Authorization (CAA) Resource Record | RFC 8659 | IETF | 2019 | 用 DNS 限定哪些 CA 能為網域簽發 | 第 19 章 |
| JSON Web Key (JWK) Thumbprint | RFC 7638 | IETF | 2015 | ACME 帳號金鑰的指紋計算 | 第 16 章 |
| Baseline Requirements for Publicly-Trusted TLS Server Certificates；Ballot SC-081v3 | — | CA/Browser Forum | 2025（SC-081v3 通過） | 憑證效期與網域驗證規則的源頭 | 第 19 章 |
| ssl 模組；hashlib、hmac、secrets 模組 | — | Python 官方文件 | — | `create_default_context`、`compare_digest` 等正確用法 | 第 17、18 章 |
| openssl-s_client(1)、openssl-x509(1) | — | OpenSSL 專案 | — | 檢查交握與憑證的指令參數 | 第 3、18 章 |

> [!note] 2026 現況
> 截至 2026 年 10 月（依 2026 年 10 月查證）：TLS 1.3 有新版規格 RFC 9846（2026-07，取代 RFC 8446，版本號仍是 1.3）；ECH 為 RFC 9849，HTTPS／SVCB 的 `ech` 參數為 RFC 9848（皆 2026-03）；後量子混合金鑰交換 `X25519MLKEM768` 由 RFC 10024（2026-08）定義。公開憑證最長效期自 2026-03-15 起為 200 天，2027-03-15 降為 100 天，2029-03-15 降為 47 天（CA/B Forum SC-081v3）。這些內容的解說在第 18 章 18.11 節與第 19 章。

## F.8 HTTP

2022 年 IETF 把 HTTP 規格重新整理成「語意」與「各版本的傳輸格式」兩層：RFC 9110 定義 method、status code、header 的意義，對所有版本都成立；RFC 9112、9113、9114 分別定義 HTTP/1.1、HTTP/2、HTTP/3 怎麼把這些語意放上線路。讀 HTTP 規格時先讀 RFC 9110，遇到「某版本怎麼編碼」再查對應的 RFC。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| HTTP Semantics | RFC 9110 | IETF | 2022 | method 的 safe／idempotent、status code、條件請求、proxy 角色 | 第 1、20、21、24、25、31、45、46 章 |
| HTTP Caching | RFC 9111 | IETF | 2022 | 新鮮度、驗證、`Cache-Control` 與共享快取 | 第 21、25、46 章 |
| HTTP/1.1 | RFC 9112 | IETF | 2022 | 訊息格式、body 長度判斷、chunked、smuggling 的安全考量 | 第 20、31、40 章 |
| HTTP/2 | RFC 9113 | IETF | 2022 | stream、frame、流量控制（取代 RFC 7540） | 第 22、31、46 章 |
| HPACK: Header Compression for HTTP/2 | RFC 7541 | IETF | 2015 | 靜態表、動態表與 Huffman 編碼 | 第 22 章 |
| HTTP/3 | RFC 9114 | IETF | 2022 | HTTP 語意對應到 QUIC stream | 第 13、22、46 章 |
| QPACK: Field Compression for HTTP/3 | RFC 9204 | IETF | 2022 | 為了避免 head-of-line blocking 而改設計的 header 壓縮 | 第 22 章 |
| Extensible Prioritization Scheme for HTTP | RFC 9218 | IETF | 2022 | `Priority` header，取代 HTTP/2 原本的優先順序樹 | 第 22 章 |
| The ORIGIN HTTP/2 Frame | RFC 8336 | IETF | 2018 | 連線重用（coalescing）的範圍控制 | 第 22 章 |
| An HTTP Status Code for Indicating Hints | RFC 8297 | IETF | 2017 | 103 Early Hints | 第 20、22、46 章 |
| PATCH Method for HTTP | RFC 5789 | IETF | 2010 | PATCH 的定義與非 idempotent | 第 20 章 |
| Additional HTTP Status Codes | RFC 6585 | IETF | 2012 | 428、429、431 等 status code | 第 40 章 |
| HTTP Cache-Control Extensions for Stale Content | RFC 5861 | IETF | 2010 | `stale-while-revalidate`、`stale-if-error` | 第 21、25 章 |
| HTTP Immutable Responses | RFC 8246 | IETF | 2017 | `immutable` 指令 | 第 21 章 |
| Targeted HTTP Cache Control | RFC 9213 | IETF | 2022 | 只給 CDN 看的 `CDN-Cache-Control` 類 header | 第 25 章 |
| GZIP file format specification version 4.3 | RFC 1952 | IETF | 1996 | gzip header 與 trailer | 第 21 章 |
| Problem Details for HTTP APIs | RFC 9457 | IETF | 2023 | API 錯誤回應的統一格式（取代 RFC 7807） | 第 24 章 |
| Web Linking | RFC 8288 | IETF | 2017 | `Link` header 與 `rel="next"` 分頁 | 第 24 章 |
| HTTP Message Signatures | RFC 9421 | IETF | 2024 | 標準化的 HTTP 請求簽章 | 第 30 章 |
| Forwarded HTTP Extension | RFC 7239 | IETF | 2014 | `Forwarded` header，`X-Forwarded-For` 的標準版本 | 第 25 章 |
| Use of the Content-Disposition Header Field in HTTP | RFC 6266 | IETF | 2011 | 下載檔名的 header | 第 41 章 |
| Indicating Character Encoding and Language for HTTP Header Field Parameters | RFC 8187 | IETF | 2017 | 非 ASCII 檔名的 `filename*=` 編碼 | 第 41 章 |
| The PROXY protocol Versions 1 & 2 | — | HAProxy | — | L4 LB 把原始 client 位址傳給後端 | 第 25 章 |
| Architectural Styles and the Design of Network-based Software Architectures | — | Roy T. Fielding（博士論文） | 2000 | REST 的原始定義，重點在第 5 章 | 第 24 章 |
| Protocol Buffers〈Encoding〉〈Language Guide (proto3)〉 | — | Google（Protocol Buffers 官方文件） | — | wire format 與欄位相容性規則 | 第 24 章 |
| gRPC over HTTP2（PROTOCOL-HTTP2）與〈Deadlines〉 | — | gRPC 專案 | — | gRPC 如何對應到 HTTP/2、`grpc-timeout` | 第 24 章 |
| GraphQL Specification | — | GraphQL Foundation | — | GraphQL 的查詢語言與執行語意 | 第 24 章 |
| API Improvement Proposals（AIP） | — | Google | — | 大型組織的資源導向 API 設計規範 | 第 24 章 |
| Consistent Hashing and Random Trees | — | David Karger 等（STOC） | 1997 | consistent hashing 的原始論文 | 第 25 章 |
| Maglev: A Fast and Reliable Software Network Load Balancer | — | Daniel E. Eisenbud 等（NSDI） | 2016 | 軟體 L4 LB 與 Maglev hashing | 第 25 章 |
| The Power of Two Choices in Randomized Load Balancing | — | Michael Mitzenmacher | — | P2C 負載平衡的理論基礎 | 第 25 章 |
| ngx_http_core_module、ngx_http_upstream_module、ngx_http_proxy_module | — | nginx 官方文件 | — | keepalive、buffering、timeout 等設定的權威說明 | 第 20、31、43 章 |
| MDN HTTP 指南（Messages、Methods、Status codes、Caching、Conditional requests） | — | MDN Web Docs | — | 從瀏覽器角度看 HTTP，例子多 | 第 20、21 章 |

## F.9 瀏覽器安全

瀏覽器安全的權威規格分散在 IETF、W3C 與 WHATWG 三個組織：origin 的定義在 RFC 6454，cookie 在 RFC 6265，CORS 在 WHATWG Fetch Standard，CSP 在 W3C。OWASP 的 cheat sheet 不是規格，但把防禦實務整理成檢查清單，適合在 code review 時對照。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| The Web Origin Concept | RFC 6454 | IETF | 2011 | origin 的定義與序列化，同源政策的基礎 | 第 23 章 |
| HTTP State Management Mechanism | RFC 6265 | IETF | 2011 | cookie 的語法、屬性與儲存規則（將由 6265bis 取代） | 第 21、23、26 章 |
| Cookies: HTTP State Management Mechanism（6265bis） | draft-ietf-httpbis-rfc6265bis | IETF httpbis WG | — | `SameSite`、`__Host-`／`__Secure-` 前綴；截至 2026 年 10 月在 RFC Editor queue，尚無 RFC 編號 | 第 21、23 章 |
| Fetch Standard | — | WHATWG（living standard） | — | CORS、preflight、safelisted header 的權威定義（2026 年 10 月存取） | 第 23、45 章 |
| Content Security Policy Level 3 | — | W3C | — | directive、nonce、hash 與 `'strict-dynamic'` | 第 23 章 |
| Fetch Metadata Request Headers | — | W3C | — | `Sec-Fetch-Site` 等 header，伺服器端的跨站判斷 | 第 23 章 |
| Cross-Site Request Forgery Prevention Cheat Sheet；Cross Site Scripting Prevention Cheat Sheet | — | OWASP | — | CSRF 與 XSS 防禦的檢查清單 | 第 23 章 |
| CORS、CSP、Set-Cookie 文件 | — | MDN Web Docs | — | 各瀏覽器實際行為的整理與範例 | 第 23 章 |

## F.10 驗證與授權

這一組是全書規格最密集、也最容易讀錯的部分。建議的順序是：先讀 RFC 6749 了解 OAuth 的角色與 grant，再讀 RFC 9700 的安全最佳實務，因為很多 RFC 6749 允許的做法現在已不建議使用；JWT 則先讀 RFC 7519，再立刻讀 RFC 8725，後者列出了 alg 混淆等常見漏洞的成因與防禦。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| HOTP: An HMAC-Based One-Time Password Algorithm | RFC 4226 | IETF | 2005 | 動態截斷演算法與附錄 D 的測試向量 | 第 26 章 |
| TOTP: Time-Based One-Time Password Algorithm | RFC 6238 | IETF | 2011 | 時間步、時鐘誤差與重放的建議 | 第 26 章 |
| The scrypt Password-Based Key Derivation Function | RFC 7914 | IETF | 2016 | scrypt 參數 N、r、p 的意義 | 第 26 章 |
| Argon2 Memory-Hard Function for Password Hashing and Proof-of-Work Applications | RFC 9106 | IETF | 2021 | Argon2id 的規格 | 第 26 章 |
| Digital Identity Guidelines: Authentication and Lifecycle Management | NIST SP 800-63B | NIST | — | 密碼政策、MFA 與 session 的政府級指引 | 第 26 章 |
| Password Storage、Session Management、Authentication、Forgot Password Cheat Sheets | — | OWASP | — | 帳號系統的實作檢查清單 | 第 26、27 章 |
| JSON Web Token (JWT) | RFC 7519 | IETF | 2015 | JWT 格式與註冊 claims（`iss`、`aud`、`exp`…） | 第 27、29 章 |
| JSON Web Signature (JWS) | RFC 7515 | IETF | 2015 | 簽章格式與 compact serialization | 第 27 章 |
| JSON Web Algorithms (JWA) | RFC 7518 | IETF | 2015 | `HS256`、`RS256`、`ES256` 等演算法識別字 | 第 27 章 |
| JSON Web Key (JWK) | RFC 7517 | IETF | 2015 | JWK 與 JWKS 格式，金鑰輪替的基礎 | 第 27、29 章 |
| JSON Web Token Best Current Practices | RFC 8725 | IETF | 2020 | 固定 alg、驗證 aud 等安全要求；更新版 8725bis 截至 2026 年 10 月尚無編號 | 第 27 章 |
| JWT Profile for OAuth 2.0 Access Tokens | RFC 9068 | IETF | 2021 | access token 的 claims 與 `at+jwt` 型別 | 第 27 章 |
| JSON Web Token Cheat Sheet | — | OWASP | — | JWT 實作檢查清單 | 第 27 章 |
| The OAuth 2.0 Authorization Framework | RFC 6749 | IETF | 2012 | OAuth 2.0 主規格：角色、grant、endpoint | 第 28 章 |
| The OAuth 2.0 Authorization Framework: Bearer Token Usage | RFC 6750 | IETF | 2012 | Bearer token 的出示方式與 `WWW-Authenticate` 錯誤碼 | 第 27、28 章 |
| Proof Key for Code Exchange by OAuth Public Clients（PKCE） | RFC 7636 | IETF | 2015 | `code_verifier` 與 `code_challenge`，附錄有範例值 | 第 28 章 |
| OAuth 2.0 Security Best Current Practice | RFC 9700 | IETF | 2025 | redirect URI 精確比對、PKCE、refresh token 保護 | 第 27、28 章 |
| OAuth 2.0 for Native Apps | RFC 8252 | IETF | 2017 | 手機與桌面 App 該怎麼做 OAuth | 第 28 章 |
| OAuth 2.0 for Browser-Based Applications（BCP 212） | RFC 10017 | IETF | 2026 | SPA 的威脅模型與 BFF 模式 | 第 27、28、29 章 |
| The OAuth 2.1 Authorization Framework | draft-ietf-oauth-v2-1 | IETF OAuth WG | — | 整合 OAuth 2.0 與後續最佳實務；截至 2026 年 10 月為 draft-16，尚非 RFC | 第 28 章 |
| OAuth 2.0 Demonstrating Proof of Possession (DPoP) | RFC 9449 | IETF | 2023 | 把 token 綁定到 client 金鑰，防止被偷後重用 | 第 28 章 |
| OAuth 2.0 Authorization Server Issuer Identification | RFC 9207 | IETF | 2022 | 用 `iss` 參數防止 mix-up attack | 第 29 章 |
| OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access Tokens | RFC 8705 | IETF | 2020 | 用 mTLS 驗證 client 並綁定 token | 第 30 章 |
| OpenID Connect Core 1.0 | — | OpenID Foundation | 2014 | ID token、claims 與驗證步驟 | 第 29 章 |
| OpenID Connect Discovery 1.0；RP-Initiated、Front-Channel、Back-Channel Logout 1.0 | — | OpenID Foundation | — | metadata 自動探索與各種登出流程 | 第 29 章 |
| Web Authentication: An API for accessing Public Key Credentials Level 3 | — | W3C | 2026（Recommendation） | passkeys 的註冊、驗證與資料結構 | 第 29 章 |
| FIDO Alliance passkeys 技術文件與部署指南 | — | FIDO Alliance | — | passkeys 的產品化與使用者體驗建議 | 第 29 章 |
| System for Cross-domain Identity Management: Core Schema；SCIM: Protocol | RFC 7643、RFC 7644 | IETF | 2015 | 企業 SSO 的帳號自動佈建 | 第 29 章 |
| Assertions and Protocols for the OASIS SAML V2.0 | — | OASIS | 2005 | 企業 SSO 的舊主流協定，整合時仍常遇到 | 第 29 章 |
| SPIFFE ID、X509-SVID、JWT-SVID、Workload API | — | SPIFFE 專案（CNCF） | — | 工作負載身分的格式與取得方式 | 第 30 章 |
| Signature Version 4 signing process；Use IMDSv2 | — | AWS 官方文件 | — | 真實世界的請求簽章與 metadata 服務防護 | 第 30 章 |
| Service Account Token Volume Projection | — | Kubernetes 官方文件 | — | 有 audience 與效期的 service account token | 第 30 章 |
| Secrets Management Cheat Sheet | — | OWASP | — | 秘密的存放、交付、輪替與外洩應變 | 第 30 章 |

## F.11 即時通訊

即時通訊的規格不多，但每一份都直接對應到線上的故障：SSE 的重連規則在 WHATWG HTML Standard，WebSocket 的握手、masking 與 close code 在 RFC 6455。「Talking to Yourself for Fun and Profit」這篇研究解釋了 WebSocket 為什麼要求 client 必須 mask，讀完會理解規格裡看似多餘的設計其實是為了防禦透明 proxy 的快取污染。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| HTML Living Standard：Server-sent events 一節 | — | WHATWG（living standard） | — | `text/event-stream` 格式、解析演算法與重連規則 | 第 31 章 |
| Known Issues and Best Practices for the Use of Long Polling and Streaming in Bidirectional HTTP | RFC 6202 | IETF | 2011 | long polling 與 HTTP streaming 的問題整理 | 第 31 章 |
| The WebSocket Protocol | RFC 6455 | IETF | 2011 | 握手、frame 格式、masking、close code（7.4 節） | 第 32、33、42、45 章 |
| Compression Extensions for WebSocket | RFC 7692 | IETF | 2015 | permessage-deflate 的協商與 RSV1 | 第 32 章 |
| Bootstrapping WebSockets with HTTP/2 | RFC 8441 | IETF | 2018 | Extended CONNECT 與 `:protocol` | 第 32、33 章 |
| Bootstrapping WebSockets with HTTP/3 | RFC 9220 | IETF | 2022 | 把 RFC 8441 的機制搬到 HTTP/3 | 第 32、33 章 |
| WebSocket Protocol Registries | — | IANA | — | close code（含 1012、1013）、subprotocol 與 extension 登錄表 | 第 32、33 章 |
| WebSockets Standard | — | WHATWG（living standard） | — | 瀏覽器 API：`close()` 的 code 限制、`bufferedAmount` | 第 32 章 |
| WebTransport（API）與 WebTransport over HTTP/3（協定） | draft-ietf-webtrans-http3 | W3C、IETF WebTrans WG | — | 下一代雙向傳輸；截至 2026 年 10 月協定在 WG Last Call、API 為 Working Draft | 第 32 章 |
| Talking to Yourself for Fun and Profit | — | Lin-Shung Huang、Eric Y. Chen、Adam Barth、Eric Rescorla、Collin Jackson | — | WebSocket masking 設計背後的透明 proxy 快取污染研究 | 第 32 章 |
| WebSocket proxying；ngx_http_proxy_module | — | nginx 官方文件 | — | Upgrade 轉送、`proxy_buffering` 與 `X-Accel-Buffering` | 第 31、33 章 |
| Redis Pub/Sub；Redis Streams | — | Redis 官方文件 | — | 多台即時伺服器之間廣播與補發的投遞語意 | 第 33 章 |
| Timeouts, retries, and backoff with jitter | — | Marc Brooker（Amazon Builders' Library） | — | 為什麼重連要加 jitter，避免同時湧回 | 第 33 章 |
| Using server-sent events；EventSource | — | MDN Web Docs | — | 瀏覽器端 API 與 DevTools 的觀察方式 | 第 31 章 |

## F.12 即時影音

影音的規格可以分成三層來讀：媒體封包（RTP／RTCP，RFC 3550）、協商（SDP 與 JSEP，RFC 8866、RFC 9429）、連線與加密（ICE、STUN、TURN、DTLS-SRTP）。W3C 的〈Identifiers for WebRTC's Statistics API〉雖然不起眼，卻是第 39 章除錯時最常查的文件，`getStats()` 每個欄位的精確定義都在裡面。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| RTP: A Transport Protocol for Real-Time Applications | RFC 3550 | IETF | 2003 | RTP／RTCP 規格，附錄 A 有序號、遺失與 jitter 的參考程式 | 第 34、39 章 |
| RTP Profile for Audio and Video Conferences with Minimal Control | RFC 3551 | IETF | 2003 | 靜態 payload type 與 marker 慣例 | 第 34 章 |
| RTP Payload Format for the Opus Speech and Audio Codec | RFC 7587 | IETF | 2015 | Opus 的 RTP 封裝 | 第 34 章 |
| RTP Payload Format for H.264 Video | RFC 6184 | IETF | 2011 | NAL unit 的切包（FU-A、STAP-A）與 fmtp 參數 | 第 34、35 章 |
| A General Mechanism for RTP Header Extensions | RFC 8285 | IETF | 2017 | one-byte 與 two-byte header extension | 第 34 章 |
| WebRTC Video Processing and Codec Requirements | RFC 7742 | IETF | 2016 | WebRTC 必須支援的視訊 codec | 第 34 章 |
| WebRTC Audio Codec and Processing Requirements | RFC 7874 | IETF | 2016 | WebRTC 必須支援的音訊 codec | 第 34 章 |
| SDP: Session Description Protocol | RFC 8866 | IETF | 2021 | SDP 現行語法（取代 RFC 4566） | 第 35 章 |
| An Offer/Answer Model with SDP | RFC 3264 | IETF | 2002 | offer／answer 的基本規則、port 0 與方向屬性 | 第 35 章 |
| JavaScript Session Establishment Protocol (JSEP) | RFC 9429 | IETF | 2024 | 瀏覽器如何產生與處理 SDP（取代 RFC 8829） | 第 35、36 章 |
| Negotiating Media Multiplexing Using SDP（BUNDLE） | RFC 9143 | IETF | 2022 | 多個 m 段共用一條傳輸（取代 RFC 8843） | 第 35 章 |
| SDP Offer/Answer Procedures for ICE | RFC 8839 | IETF | 2021 | `ice-ufrag`、`ice-pwd` 與 candidate 屬性 | 第 35 章 |
| SDP Offer/Answer Procedures for SCTP over DTLS Transport | RFC 8841 | IETF | 2021 | data channel 的 m 段與 `max-message-size` | 第 35 章 |
| SDP Offer/Answer Considerations for DTLS and TLS | RFC 8842 | IETF | 2021 | `setup` 與 `fingerprint` 屬性 | 第 35 章 |
| RTP Retransmission Payload Format | RFC 4588 | IETF | 2006 | rtx：重傳封包的封裝 | 第 35、37 章 |
| Interactive Connectivity Establishment (ICE) | RFC 8445 | IETF | 2018 | candidate、優先序公式、連線檢查與提名 | 第 36 章 |
| Trickle ICE | RFC 8838 | IETF | 2021 | 邊收集邊送 candidate，縮短建立時間 | 第 36 章 |
| STUN Usage for Consent Freshness | RFC 7675 | IETF | 2015 | 連線中持續確認對方仍同意接收 | 第 36 章 |
| Session Traversal Utilities for NAT (STUN) | RFC 8489 | IETF | 2020 | STUN 訊息格式與屬性 | 第 36 章 |
| Test Vectors for STUN | RFC 5769 | IETF | 2010 | 第 36 章程式用來驗證的測試向量 | 第 36 章 |
| Traversal Using Relays around NAT (TURN) | RFC 8656 | IETF | 2020 | allocation、permission、channel 與錯誤碼 | 第 36、37、39 章 |
| DTLS Extension to Establish Keys for SRTP | RFC 5764 | IETF | 2010 | DTLS-SRTP：用 DTLS 交握產生 SRTP 金鑰 | 第 36 章 |
| The Secure Real-time Transport Protocol (SRTP) | RFC 3711 | IETF | 2004 | 媒體封包的加密與驗證 | 第 36 章 |
| WebRTC Data Channels；WebRTC Data Channel Establishment Protocol | RFC 8831、RFC 8832 | IETF | 2021 | SCTP over DTLS 與 DCEP | 第 36 章 |
| WebRTC Security Architecture | RFC 8827 | IETF | 2021 | signaling、fingerprint 與信任模型 | 第 36 章 |
| RTP Topologies | RFC 7667 | IETF | 2015 | mesh、SFU、MCU 等拓撲的正式描述 | 第 37 章 |
| Extended RTP Profile for RTCP-Based Feedback (RTP/AVPF) | RFC 4585 | IETF | 2006 | NACK、PLI 等回饋訊息 | 第 37 章 |
| Codec Control Messages in AVPF | RFC 5104 | IETF | 2008 | FIR 等 codec 控制訊息 | 第 37 章 |
| RTP Payload Format for Generic Forward Error Correction | RFC 5109 | IETF | 2007 | ULPFEC | 第 37 章 |
| RTP Payload Format for Flexible Forward Error Correction (FEC) | RFC 8627 | IETF | 2019 | FlexFEC | 第 37 章 |
| Using Simulcast in SDP and RTP Sessions | RFC 8853 | IETF | 2021 | simulcast 的 SDP 寫法 | 第 37 章 |
| RTP Payload Format Restrictions | RFC 8851 | IETF | 2021 | `rid` 與編碼限制 | 第 37 章 |
| RTCP Feedback for Congestion Control | RFC 8888 | IETF | 2021 | 標準化的擁塞控制回饋格式 | 第 37 章 |
| A Google Congestion Control Algorithm for Real-Time Communication；RTP Extensions for Transport-wide Congestion Control | 草案（編號待核對） | IETF RMCAT WG（草案） | — | GCC 與 transport-wide CC，瀏覽器實際使用的頻寬估計 | 第 37 章 |
| WebRTC: Real-Time Communication in Browsers | — | W3C | 2025（最新版本日期 2025-03-13） | RTCPeerConnection、transceiver、getStats 等 API | 第 35、36、39 章 |
| Identifiers for WebRTC's Statistics API | — | W3C | — | `getStats()` 每個欄位的定義，影音除錯必查 | 第 34、37、39、45 章 |
| Scalable Video Coding (SVC) Extension for WebRTC | — | W3C | — | `scalabilityMode` 與 SVC 的 API | 第 37 章 |
| One-way transmission time | ITU-T G.114 | ITU-T | — | 對話延遲的規劃建議 | 第 34、39 章 |
| The E-model: a computational model for use in transmission planning | ITU-T G.107 | ITU-T | — | R 值與 MOS 的換算 | 第 39 章 |
| Methods for subjective determination of transmission quality | ITU-T P.800 | ITU-T | — | MOS 主觀測試方法 | 第 39 章 |
| HTTP Live Streaming | RFC 8216 | Apple（Independent Submission，Informational） | 2017 | HLS playlist 與 segment 的規格；新版見 F.18 | 第 38 章 |
| HLS Authoring Specification for Apple Devices | — | Apple | — | segment 長度、GOP 與 ABR 階梯的實務建議 | 第 38 章 |
| WebRTC-HTTP Ingestion Protocol (WHIP) | RFC 9725 | IETF | 2025 | 用 HTTP POST 交換 SDP 的 WebRTC 推流 | 第 36、37、38 章 |
| WebRTC-HTTP Egress Protocol (WHEP) | draft-ietf-wish-whep | IETF WISH WG | — | WebRTC 觀看端；截至 2026 年 10 月為 draft-04，尚非 RFC | 第 38 章 |
| SRT Protocol Technical Overview；SRT API Socket Options；SRT Access Control（Stream ID）Guidelines | — | Haivision、SRT Alliance（libsrt 文件） | — | SRT 的實質規格與所有選項的預設值 | 第 38、39 章 |
| Real-Time Messaging Protocol (RTMP) Specification | — | Adobe | 2012 | RTMP 的公開規格 | 第 38 章 |
| Enhanced RTMP | — | Veovera | — | 讓 RTMP 支援 HEVC、AV1、Opus 等新 codec | 第 38 章 |
| MPEG-DASH | ISO/IEC 23009-1 | ISO/IEC | — | DASH 的 MPD 與 segment 格式 | 第 38 章 |
| CMAF（Common Media Application Format） | ISO/IEC 23000-19 | ISO/IEC | — | HLS 與 DASH 共用的 fMP4 segment | 第 38 章 |
| Interoperability Points；低延遲 DASH 指南 | — | DASH-IF | — | DASH 的實作互通指南 | 第 38 章 |

## F.13 Python Web 堆疊

Python 這一組以 PEP 與官方文件為主。PEP 3333 篇幅不長，每個做 Flask 的工程師都值得讀一遍，讀完會明白 `environ`、`start_response` 與 iterable 的每個規則從哪裡來；ASGI 規格則要分開讀 core 規格與〈HTTP & WebSocket ASGI Message Format〉。gunicorn 與 uvicorn 的文件要對照你手上的版本，因為兩者近兩年變動很大（見 F.18）。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| Python Web Server Gateway Interface v1.0.1 | PEP 3333 | Python（PEP） | 2010 | WSGI 現行規格：environ、`start_response`、bytes 規則 | 第 41、42、43 章 |
| Python Web Server Gateway Interface v1.0 | PEP 333 | Python（PEP） | 2003 | 原始版本，Rationale 一節說明設計動機 | 第 41 章 |
| The Common Gateway Interface (CGI) Version 1.1 | RFC 3875 | IETF | 2004 | `REQUEST_METHOD`、`QUERY_STRING` 等 environ 名稱的來源 | 第 41 章 |
| Coroutines with async and await syntax | PEP 492 | Python（PEP） | 2015 | `async`／`await` 語法的由來 | 第 42 章 |
| ASGI Specification（core 3.0）；HTTP & WebSocket ASGI Message Format（2.5）；Lifespan Protocol | — | ASGI 專案 | — | scope、receive、send 與各種事件的定義 | 第 42 章 |
| wsgiref；socket、selectors、socketserver；asyncio | — | Python 官方文件 | — | 標準函式庫的 WSGI 參考實作與 I/O 模型 | 第 40、41、42 章 |
| The C10K problem | — | Dan Kegel | — | 同時服務上萬 client 的 I/O 模型整理，event loop 架構的起點 | 第 40 章 |
| epoll(7)、accept(2)、listen(2)、getrlimit(2) | — | Linux man-pages | — | event loop 與檔案描述子上限的底層 | 第 40 章 |
| Werkzeug 官方文件（Request／Response、Routing、Debugging、Behind a Proxy、Test Utilities） | — | Pallets 專案 | — | Flask 底下那一層；debugger 絕不可在 production 開啟 | 第 41、43 章 |
| Flask 官方文件（Application Structure and Lifecycle、Request Context、Streaming、Deploying to Production） | — | Pallets 專案 | — | 請求生命週期與正式部署的建議 | 第 41 章 |
| gunicorn 官方文件（Design、Settings、Signal Handling、Deploying） | — | gunicorn 專案 | — | prefork 架構、所有設定的預設值與訊號 | 第 40、43 章 |
| uvicorn 官方文件（Settings、Deployment） | — | uvicorn 專案 | — | workers、keep-alive、proxy headers 與 graceful shutdown | 第 42、43 章 |
| Starlette（Middleware、Lifespan、Thread Pool）；FastAPI（Concurrency and async／await） | — | Starlette、FastAPI 專案 | — | sync 函式如何被放進 thread pool | 第 42 章 |
| A Proof for the Queuing Formula: L = λW | — | John D. C. Little（Operations Research） | 1961 | Little's Law，估算 worker 數與並行量的基礎 | 第 43 章 |

## F.14 雲端與容器

雲端網路的權威資料以官方文件為主，RFC 只有 overlay 封裝相關的幾份。Kubernetes 的網路文件要分清楚「模型」（每個 Pod 一個 IP、Pod 之間可直接互通）與「實作」（CNI 外掛與 kube-proxy 模式），讀文件時先找它在談哪一層。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| Virtual eXtensible Local Area Network (VXLAN) | RFC 7348 | IETF（Informational） | 2014 | VXLAN 封包格式、VTEP 與 UDP 4789 | 第 44 章 |
| Geneve: Generic Network Virtualization Encapsulation | RFC 8926 | IETF | 2020 | 可擴充選項的新一代 overlay 封裝 | 第 44 章 |
| Cluster Networking；Services, Load Balancing, and Networking；Network Policies | — | Kubernetes 官方文件 | — | 網路模型、Service 類型、kube-proxy 與 NetworkPolicy | 第 44 章 |
| Gateway API 官方文件 | — | Kubernetes SIG Network | — | GatewayClass、Gateway、HTTPRoute 的角色模型；截至 2026 年 10 月最新為 v1.6 系列 | 第 44 章 |
| CNI 規格 | — | CNCF containernetworking 專案 | — | 外掛介面與 ADD／DEL／CHECK | 第 44 章 |
| Pod Lifecycle；container lifecycle hooks（preStop） | — | Kubernetes 官方文件 | — | Pod 終止流程與優雅關閉 | 第 43 章 |
| Amazon VPC User Guide | — | AWS 官方文件 | — | subnet、route table、gateway、security group、NACL、PrivateLink（其他雲端有對應文件） | 第 5、44 章 |
| ip-netns(8)、veth(4)、ip-link(8) | — | Linux man-pages | — | network namespace、veth、bridge 與 vxlan 介面的指令 | 第 44 章 |

## F.15 除錯與效能

除錯的資料偏重工具文件：curl、tcpdump、Wireshark、OpenSSL 的官方文件把每個選項的精確意義都寫清楚了，遇到「這個欄位到底怎麼算」時直接查原文最快。效能方面，W3C 的 Resource Hints 與 HTML Standard 定義了 `preconnect`、`preload` 等提示，第 46 章的前端優化就以這些為準。

| 名稱 | 編號 | 作者或機構 | 年份 | 為何值得讀 | 章節 |
|---|---|---|---|---|---|
| Everything curl；write-out 文件 | — | curl 專案 | — | `-v`、`--resolve`、`-w` 時間變數的精確定義 | 第 3、45 章 |
| pcap-filter(7) | — | tcpdump／libpcap 專案 | — | BPF capture filter 的完整語法 | 第 3 章 |
| Wireshark User's Guide 與 display filter 參考 | — | Wireshark 專案 | — | 欄位名稱、運算子與 TCP 分析功能 | 第 3、45 章 |
| openssl-s_client | — | OpenSSL 專案 | — | 交握與憑證驗證的除錯參數 | 第 3 章 |
| Resource Hints；HTML Living Standard 的 link 類型 | — | W3C、WHATWG | — | `preconnect`、`dns-prefetch`、`preload` 的定義 | 第 46 章 |
| Identifiers for WebRTC's Statistics API | — | W3C | — | 從 candidate-pair 與 inbound-rtp 判斷影音問題 | 第 45 章 |
| Fetch Standard | — | WHATWG（living standard） | — | CORS 錯誤的判斷規則（2026 年 10 月存取） | 第 45 章 |

## F.16 經典書籍

正文各章已經涵蓋了這些書的核心內容，但它們提供了更多例子與不同的切入角度。下表依「建議先讀到後讀」排列，年份只寫有把握的版次。

| 書名 | 作者 | 年份與版次 | 為何值得讀 | 對應章節 |
|---|---|---|---|---|
| High Performance Browser Networking | Ilya Grigorik（O'Reilly） | 2013 | 延遲、TCP、TLS、HTTP 與瀏覽器網路效能的整體視角，最適合本書讀者的第二本書 | 第 1、22、46 章 |
| Computer Networking: A Top-Down Approach | James Kurose、Keith Ross | 版次多 | 大學網路課最常用的教科書，從應用層往下講，習題多 | 第 2、11 章 |
| Computer Networks: A Systems Approach | Larry L. Peterson、Bruce S. Davie | 版次多 | 以系統設計的角度講網路，路由與互連章節特別好 | 第 6 章 |
| TCP/IP Illustrated, Volume 1: The Protocols | Kevin R. Fall、W. Richard Stevens | 2011（第二版） | 用 tcpdump 輸出逐一解說各協定，學看封包的經典 | 第 3、10、11 章 |
| The TCP/IP Guide | Charles M. Kozierok | 2005 | 百科全書式的協定參考，查細節方便 | 第 4 章 |
| UNIX Network Programming, Volume 1: The Sockets Networking API | W. Richard Stevens、Bill Fenner、Andrew M. Rudoff | 2003（第三版） | socket API 與各種 server 設計的權威 | 第 9、40 章 |
| DNS and BIND | Cricket Liu、Paul Albitz（O'Reilly） | 2006（第五版） | DNS 營運與 zone 設計的經典 | 第 14、15 章 |
| Serious Cryptography | Jean-Philippe Aumasson（No Starch Press） | 2024（第二版） | 給工程師的現代密碼學，不需要數學背景 | 第 17 章 |
| Bulletproof TLS and PKI | Ivan Ristić | 第二版 | TLS 部署、設定與憑證營運的實務 | 第 19 章 |
| OAuth 2.0 Simplified | Aaron Parecki | — | 以實作者角度解說各種 grant | 第 28 章 |
| The H.264 Advanced Video Compression Standard | Iain E. Richardson | 2010（第二版） | 預測、量化與 GOP 的入門，理解 keyframe 為什麼重要 | 第 34 章 |
| Site Reliability Engineering: How Google Runs Production Systems | Betsy Beyer 等編（O'Reilly） | 2016 | 〈Effective Troubleshooting〉與〈Emergency Response〉兩章是事故處理的基本功 | 第 45 章 |
| Systems Performance: Enterprise and the Cloud | Brendan Gregg | 2020（第二版） | USE 方法與網路效能分析 | 第 45 章 |
| Designing Data-Intensive Applications | Martin Kleppmann（O'Reilly） | 2017（第一版） | 複製、分區、訊息系統與投遞語意的取捨 | 第 33、46 章 |
| System Design Interview: An Insider's Guide | Alex Xu | 2020 | system design 面試的流程與常見題型 | 第 46 章 |

## F.17 RFC 速查表

這張表只列本書最常引用的 RFC，依主題排列。看到 log、文件或面試題提到某個 RFC 編號時，先在這裡找到它屬於哪個主題，再回到對應章節。「取代」欄寫的是該 RFC 宣告 obsoletes 的舊文件，讀舊資料時能對得上。

| 主題 | RFC | 名稱 | 取代 | 章節 |
|---|---|---|---|---|
| 規格用語 | 2119、8174 | Key words for use in RFCs（BCP 14） | — | 第 2 章 |
| IP | 791 | Internet Protocol（IPv4） | — | 第 2、5 章 |
| IP | 8200 | IPv6 Specification | 2460 | 第 2、5 章 |
| IP | 4632 | CIDR | 1519 | 第 5 章 |
| IP | 1918 | Address Allocation for Private Internets | — | 第 5、7 章 |
| IP | 6890 | Special-Purpose IP Address Registries | — | 第 5 章 |
| IP | 4291 | IPv6 Addressing Architecture | — | 第 5 章 |
| 鏈結層 | 826 | ARP | — | 第 4 章 |
| ICMP／MTU | 792 | ICMP | — | 第 3、6、8 章 |
| ICMP／MTU | 4443 | ICMPv6 | — | 第 8 章 |
| ICMP／MTU | 1191、8201 | Path MTU Discovery（IPv4、IPv6） | — | 第 8 章 |
| ICMP／MTU | 8899 | PLPMTUD for Datagram Transports | — | 第 8 章 |
| 路由 | 4271 | BGP-4 | — | 第 6 章 |
| 路由 | 6811 | BGP Prefix Origin Validation | — | 第 6 章 |
| NAT | 4787 | NAT Behavioral Requirements for Unicast UDP | — | 第 7、36 章 |
| NAT | 6598 | Shared Address Space（100.64.0.0/10） | — | 第 7 章 |
| UDP | 768 | User Datagram Protocol | — | 第 2、9 章 |
| UDP | 8085 | UDP Usage Guidelines | — | 第 9 章 |
| TCP | 9293 | Transmission Control Protocol | 793 等 | 第 10、11 章 |
| TCP | 7323 | TCP Extensions for High Performance | 1323 | 第 10、11 章 |
| TCP | 6298 | Computing TCP's Retransmission Timer | — | 第 11 章 |
| TCP | 5681 | TCP Congestion Control | — | 第 11、12 章 |
| TCP | 2018 | SACK | — | 第 11 章 |
| TCP | 9438 | CUBIC | — | 第 12 章 |
| TCP | 6928 | Increasing TCP's Initial Window | — | 第 12、46 章 |
| QUIC | 9000 | QUIC Transport | — | 第 13 章 |
| QUIC | 9001 | Using TLS to Secure QUIC | — | 第 13 章 |
| QUIC | 9002 | QUIC Loss Detection and Congestion Control | — | 第 13 章 |
| DNS | 1034、1035 | Domain Names | — | 第 14 章 |
| DNS | 6891 | EDNS(0) | — | 第 14、15 章 |
| DNS | 2308 | Negative Caching | — | 第 14、15 章 |
| DNS | 9460 | SVCB and HTTPS RRs | — | 第 14、15 章 |
| DNS | 4033–4035 | DNSSEC | — | 第 15 章 |
| DNS | 8484、7858、9250 | DoH、DoT、DoQ | — | 第 15 章 |
| 密碼學 | 2104 | HMAC | — | 第 17、30 章 |
| 密碼學 | 5869 | HKDF | — | 第 17 章 |
| TLS | 8446 | TLS 1.3（新版 RFC 9846 見 F.18） | 5246 等 | 第 18 章 |
| TLS | 5280 | X.509 PKI Certificate and CRL Profile | — | 第 18、19 章 |
| TLS | 6066、7301 | SNI 等 TLS 擴充、ALPN | — | 第 18 章 |
| 憑證 | 8555 | ACME | — | 第 19 章 |
| 憑證 | 6797 | HSTS | — | 第 19 章 |
| 憑證 | 6962 | Certificate Transparency | — | 第 19 章 |
| HTTP | 9110 | HTTP Semantics | 7231 等 | 第 20、21、24 章 |
| HTTP | 9111 | HTTP Caching | 7234 | 第 21、25 章 |
| HTTP | 9112 | HTTP/1.1 | 7230 | 第 20、40 章 |
| HTTP | 9113 | HTTP/2 | 7540 | 第 22 章 |
| HTTP | 9114 | HTTP/3 | — | 第 22 章 |
| HTTP | 7541、9204 | HPACK、QPACK | — | 第 22 章 |
| HTTP | 9457 | Problem Details for HTTP APIs | 7807 | 第 24 章 |
| HTTP | 7239 | Forwarded HTTP Extension | — | 第 25 章 |
| 瀏覽器 | 6454 | The Web Origin Concept | — | 第 23 章 |
| 瀏覽器 | 6265 | HTTP State Management Mechanism（cookie） | 2965 | 第 21、23、26 章 |
| 驗證 | 4226、6238 | HOTP、TOTP | — | 第 26 章 |
| 驗證 | 7519 | JWT | — | 第 27 章 |
| 驗證 | 7515、7517、7518 | JWS、JWK、JWA | — | 第 27 章 |
| 驗證 | 8725 | JWT Best Current Practices | — | 第 27 章 |
| 授權 | 6749 | OAuth 2.0 Authorization Framework | 5849 | 第 28 章 |
| 授權 | 6750 | Bearer Token Usage | — | 第 27、28 章 |
| 授權 | 7636 | PKCE | — | 第 28 章 |
| 授權 | 9700 | OAuth 2.0 Security BCP | — | 第 27、28 章 |
| 授權 | 9449 | DPoP | — | 第 28 章 |
| 服務間驗證 | 9421 | HTTP Message Signatures | — | 第 30 章 |
| 服務間驗證 | 8705 | OAuth 2.0 Mutual-TLS | — | 第 30 章 |
| 即時通訊 | 6455 | The WebSocket Protocol | — | 第 32、33 章 |
| 即時通訊 | 8441、9220 | WebSocket over HTTP/2、HTTP/3 | — | 第 32 章 |
| 影音 | 3550 | RTP | 1889 | 第 34、39 章 |
| 影音 | 8866 | SDP | 4566 | 第 35 章 |
| 影音 | 3264 | SDP Offer/Answer | — | 第 35 章 |
| 影音 | 9429 | JSEP | 8829 | 第 35 章 |
| 影音 | 9143 | BUNDLE | 8843 | 第 35 章 |
| 影音 | 8445 | ICE | 5245 | 第 36 章 |
| 影音 | 8489 | STUN | 5389 | 第 36 章 |
| 影音 | 8656 | TURN | 5766 | 第 36、37 章 |
| 影音 | 5764、3711 | DTLS-SRTP、SRTP | — | 第 36 章 |
| 影音 | 8831 | WebRTC Data Channels | — | 第 36 章 |
| 影音 | 4585 | RTP/AVPF（NACK、PLI） | — | 第 37 章 |
| 影音 | 8216 | HTTP Live Streaming | — | 第 38 章 |
| 影音 | 9725 | WHIP | — | 第 38 章 |
| Python | 3875 | CGI 1.1（WSGI environ 的來源） | — | 第 41 章 |
| 雲端 | 7348 | VXLAN | — | 第 44 章 |
| 雲端 | 8926 | Geneve | — | 第 44 章 |

「取代」欄只列本書有把握的取代關係；標「等」代表同時取代多份文件（例如 RFC 9110 與 9111、9112 一起取代了 RFC 7230–7235）。表中沒有列的取代關係，不代表沒有，查 RFC 本文第一頁的 Obsoletes 欄位即可確認。

## F.18 2026 現況：仍在變動的規格

> [!note] 2026 現況
> 下表依 2026 年 10 月查證整理，狀態截至 2026 年 10 月。草案的版次與 RFC 編號會改變，引用前請以 IETF datatracker 或 RFC Editor 的當期狀態為準；尚未成為 RFC 的文件，本書不預測編號。

| 文件 | 截至 2026 年 10 月的狀態 | 對讀者的意義 | 章節 |
|---|---|---|---|
| TLS 1.3 新版（rfc8446bis） | 已發布為 RFC 9846（2026-07），取代 RFC 8446，版本號仍是 1.3 | 新文件引用 RFC 9846；協定行為不變 | 第 13、18 章 |
| TLS Encrypted Client Hello | 已發布為 RFC 9849（2026-03）；DNS 引導用的 `ech` 參數為 RFC 9848 | SNI 可以被加密，實務上多半搭配 DoH | 第 14、15、18 章 |
| PQ／T 混合金鑰交換（draft-ietf-tls-ecdhe-mlkem） | 已發布為 RFC 10024（2026-08），含 `X25519MLKEM768`（0x11EC） | ClientHello 變大，可能跨多個封包 | 第 17、18 章 |
| OAuth 2.0 for Browser-Based Applications | 已發布為 RFC 10017（BCP 212，2026-08） | SPA 首選 BFF 模式 | 第 27、28、29 章 |
| WebAuthn Level 3 | W3C Recommendation（2026-08-25） | passkeys 相關 API 有正式規格可依 | 第 29 章 |
| OAuth 2.1（draft-ietf-oauth-v2-1） | WG draft，最新為 draft-16（2026-09），尚非 RFC | 內容（PKCE 必要、移除 implicit 與 password grant）可以先照做 | 第 28 章 |
| Cookies（draft-ietf-httpbis-rfc6265bis） | draft-22，在 RFC Editor queue，尚無 RFC 編號 | 目前引用 RFC 6265（將由 6265bis 取代） | 第 21、23、26 章 |
| JWT BCP 更新版（draft-ietf-oauth-rfc8725bis） | IESG 已核准，在 RFC Editor queue，尚無 RFC 編號 | 目前引用 RFC 8725 | 第 27 章 |
| HLS 新版（draft-pantos-hls-rfc8216bis） | draft-22（2026-05），已送 RFC Editor，尚無 RFC 編號；LL-HLS 機制在其中 | 目前引用 RFC 8216，LL-HLS 細節看 bis 草案 | 第 38 章 |
| WHEP（draft-ietf-wish-whep） | draft-04（2026-06），仍是草案 | 觀看端的 WebRTC 標準尚未定案；推流端 WHIP 已是 RFC 9725 | 第 36、37、38 章 |
| SRT（draft-sharabayko-srt） | individual draft（2021）已過期並封存，沒有成為 RFC | SRT 的實質規格是 libsrt 的開源實作與文件 | 第 38 章 |
| WebTransport over HTTP/3（draft-ietf-webtrans-http3） | WG Last Call，尚非 RFC；W3C API 為 Working Draft | 可以實驗，正式產品要準備退回 WebSocket | 第 32 章 |
| Media over QUIC（draft-ietf-moq-transport） | WG draft（draft-22，2026-10），尚非 RFC | 只當未來趨勢 | 第 13、46 章 |
| WebRTC 1.0 | W3C Recommendation，最新版本日期 2025-03-13 | API 已穩定 | 第 35、36 章 |
| CA/B Forum SC-081v3 | 已生效第一階段：2026-03-15 起憑證最長 200 天 | 憑證更新必須全面自動化 | 第 19 章 |
| Kubernetes Gateway API | 最新為 v1.6 系列；ingress-nginx 已於 2026-03 封存 | 新的 Kubernetes 入口設計以 Gateway API 為主 | 第 44 章 |

這張表的用法是「引用前先查一次」。已經發布為 RFC 的文件，編號從此不會再變，只會在未來被新 RFC 取代；草案則可能改版、改名甚至放棄。寫設計文件時，依賴草案的部分要標出版次，並準備一條不依賴它的退路，例如 WebTransport 不可用時退回 WebSocket（第 32 章）。

## F.19 建議閱讀順序

延伸資料很多，不必全部讀，也不必依編號順序讀。下面的路徑以本書的章節順序為骨架，每一站只挑「讀了立刻有用」的文件；讀 RFC 時先讀 Introduction 與 Overview，再跳到自己關心的段落，不要逐字從頭讀到尾。

```text
 第一站：建立全景（讀完第 1–3 章後）
   High Performance Browser Networking ──► TCP/IP Illustrated Vol. 1（邊抓封包邊讀）
        │
 第二站：讀最短的原始規格（第 2、9 章）
   RFC 768（UDP）──► RFC 791（IPv4）──► RFC 2119／8174（讀懂 MUST／SHOULD）
        │
 第三站：每天都會用到的四份主規格
   RFC 9293（TCP）──► RFC 1034／1035（DNS）──► RFC 8446 或 9846（TLS 1.3）＋ RFC 8448 ──► RFC 9110（HTTP 語意）
        │
        ├──► 後端與 API：RFC 9111 ──► RFC 9112 ──► RFC 9457 ──► PEP 3333 ──► ASGI 規格
        ├──► 前端與瀏覽器：RFC 6454 ──► RFC 6265 ──► Fetch Standard（CORS）──► CSP Level 3
        ├──► 資安與驗證：RFC 7519 ──► RFC 8725 ──► RFC 6749 ──► RFC 9700 ──► RFC 7636 ──► OIDC Core ──► WebAuthn L3
        ├──► 即時通訊：WHATWG SSE ──► RFC 6455 ──► Brooker〈Timeouts, retries, and backoff with jitter〉
        ├──► 影音：RFC 3550 ──► RFC 8866 ──► RFC 9429 ──► RFC 8445 ──► RFC 8656 ──► webrtc-stats ──► RFC 8216
        └──► SRE 與平台：RFC 5681 ──► RFC 8900 ──► SRE 書〈Effective Troubleshooting〉──► Systems Performance
        │
 第四站：深入與取捨
   RFC 9000（QUIC）──► BBR 與 Bufferbloat 論文 ──► Designing Data-Intensive Applications
```

第一站的兩本書提供全景，讓之後讀到的每一份規格都能放回正確的位置。第二站刻意選最短的 RFC：RFC 768 只有三頁，讀完會發現 RFC 並不可怕，同時學會 RFC 2119 的用語。第三站的四份文件是所有角色共通的核心，其中 TLS 建議搭配 RFC 8448 的逐位元組範例一起讀，比單讀規格容易得多。

讀完第三站之後依角色分岔。後端工程師從 HTTP 快取與訊息格式一路讀到 WSGI 與 ASGI，正好對應第 20–25 章與第 40–43 章；前端工程師聚焦在瀏覽器的 origin、cookie 與 CORS（第 23 章）；資安路徑的順序很重要，RFC 8725 要緊接在 RFC 7519 之後讀，RFC 9700 要緊接在 RFC 6749 之後讀，因為原始規格允許的部分做法現在已不建議使用。影音路徑依「封包 → 協商 → 連線 → 統計 → 直播」的順序，對應第 34–39 章；SRE 路徑則補上擁塞控制、MTU 與事故處理的方法論。

第四站是想往更深處走的讀者：QUIC 把前面學過的 TCP、TLS 與擁塞控制重新組合，讀它等於複習整個傳輸層；BBR 與 Bufferbloat 兩篇論文說明「為什麼頻寬夠卻很慢」；最後用 DDIA 把網路放回分散式系統的整體取捨中，這也是第 46 章系統設計討論的延伸。附錄 E 另有依角色與目標（面試、工作）安排的完整學習路線，可以和本節搭配使用。

| 你現在的狀況 | 先讀 | 再讀 | 對應章節 |
|---|---|---|---|
| 剛讀完本書，想建立更完整的全景 | High Performance Browser Networking | TCP/IP Illustrated Vol. 1 | 第 1–3 章 |
| 要準備 system design 面試 | System Design Interview | Designing Data-Intensive Applications、RFC 9110 | 第 46 章 |
| 要接手驗證或 SSO 系統 | RFC 9700、RFC 8725 | OIDC Core、RFC 10017、WebAuthn Level 3 | 第 26–29 章 |
| 要排查影音品質問題 | Identifiers for WebRTC's Statistics API | RFC 3550、RFC 8656 | 第 39 章 |
| 要做 TLS 或憑證營運 | RFC 8448、RFC 8555 | Bulletproof TLS and PKI、CA/B Forum Baseline Requirements | 第 18、19 章 |
| 要調校 Python 服務的部署 | PEP 3333、gunicorn〈Design〉 | ASGI 規格、uvicorn〈Deployment〉、Little's Law 論文 | 第 40–43 章 |
| 要設計 Kubernetes 上的網路 | Kubernetes〈Cluster Networking〉 | Gateway API 文件、RFC 7348 | 第 44 章 |
