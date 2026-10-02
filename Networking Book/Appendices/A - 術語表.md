# 附錄 A　術語表

> [!abstract] 本附錄地圖
> **用途**：讀到一個想不起來的名詞、在 log 或規格裡看到一個縮寫，或要向別人解釋一個概念時，先在這裡找到一句話的精確定義，再依「首次出現 → 主要深入」欄回到正文。定義都以正文的說法為準，數值與範例沿用聲聲 Live 的全書共用設定。
>
> **怎麼查**：
> - 依主題找小節：A.1–A.4 由下往上是分層、鏈結層與 IP、路由與 NAT、傳輸層；A.5–A.8 是 DNS、密碼學與 TLS、HTTP、瀏覽器安全；A.9–A.13 是驗證與授權、即時通訊、即時影音、Python Web 堆疊、雲端與營運；A.14 是聲聲 Live 的人物、網域、位址與事故。
> - 每節依英文字母排序（數字開頭的排最前），英文術語欄的括號是完整拼寫；「中文」欄是「—」代表業界直接使用英文。
> - 「首次出現 → 主要深入」：前者是名詞第一次被定義的章，後者是完整講解機制的章；兩者相同時只寫一章。
> - 同名不同義的詞（TTL、MAC、frame、gateway）分別列在各自的主題，定義中會註明另一個意思在哪一節。
> - 標示「截至 2026 年 10 月」的內容會隨標準與產品演進而變，以正文的 2026 現況小節為準。

```text
 一個請求會碰到的層                      本附錄的小節
 ┌────────────────────────────────────┐
 │ 應用：Flask、WSGI／ASGI            │  A.12 Python Web 堆疊
 │       驗證與授權、即時、影音       │  A.9 驗證　A.10 即時　A.11 影音
 │       HTTP、瀏覽器安全             │  A.7 HTTP　A.8 瀏覽器安全
 │       TLS、DNS                     │  A.6 TLS　A.5 DNS
 ├────────────────────────────────────┤
 │ 傳輸：TCP、UDP、QUIC               │  A.4 傳輸層與 QUIC
 ├────────────────────────────────────┤
 │ 網路：IP、路由、NAT、ICMP          │  A.2 IP　A.3 路由與 NAT
 ├────────────────────────────────────┤
 │ 鏈結：Ethernet、ARP、VLAN、Wi-Fi   │  A.2 鏈結層
 └────────────────────────────────────┘
   橫跨各層：分層與工具 A.1；雲端、容器與營運 A.13；聲聲 Live 專有名詞 A.14
```

這張圖把小節對應到第 2 章的分層。由下往上讀，越下面的名詞越接近線路上的 bytes，越上面的越接近程式碼；除錯時遇到不認得的名詞，先判斷它屬於哪一層，就知道該翻哪一節、該看哪一層的工具輸出。


## A.1 網路基礎與分層

分層、封裝與量測工具的基本詞彙；延遲的三種來源與 RTT 是全書估算效能的單位（第 1–3 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| big-endian | 大端序 | 多 byte 數值把最高位的 byte 放在最前面，網路協定的 header 一律採用，又稱 network byte order；x86 與 ARM 記憶體慣用的 little-endian 正好相反，直接寫進封包就是 byte order bug。 | 第 2 章 |
| curl | — | 命令列 HTTP client；`-v` 看交握與 header、`-w` 印出 DNS、連線、TLS、首 byte 各階段的累計時間。 | 第 3 章 |
| demultiplexing | 解多工 | 依 header 欄位（EtherType、Protocol、port）決定把收到的資料交給哪個上層協定或哪個 socket。 | 第 2 章 → 第 9 章 |
| DevTools | 瀏覽器開發者工具 | 瀏覽器內建的除錯工具；Network 面板的 Timing 把一個請求拆成排隊、DNS、連線、TLS、等待首 byte 與下載。 | 第 3 章 |
| dig | — | DNS 查詢工具，直接印出 header 旗標、各 section 與剩餘 TTL；`+trace` 從 root 開始逐層追。 | 第 3 章 → 第 14 章 |
| encapsulation | 封裝 | 每一層把上一層交下來的資料當成 payload，在前面加上自己的 header（有時加 trailer）再交給下一層；接收端由下往上逐層拆掉，稱為解封裝。 | 第 2 章 |
| header | 標頭 | 每一層加在 payload 前面、給對等層讀的控制資訊，例如位址、長度、序號與 checksum。 | 第 2 章 |
| Internet checksum | 網際網路校驗和 | 以 16 bit 一補數相加後取反的錯誤偵測值，IPv4、ICMP、TCP、UDP 都用；只能抓傳輸錯誤，防不了竄改。 | 第 2 章 → 第 8 章 |
| jitter | 延遲抖動 | 封包延遲的變動量；即時影音用 jitter buffer 吸收，RTCP 回報的是 interarrival jitter。 | 第 3 章 → 第 34 章 |
| layering | 分層 | 把通訊拆成各自負責一件事的層，每層只透過介面使用下一層的服務、只和對端的同一層對話。 | 第 2 章 |
| OSI model | OSI 模型 | 七層參考模型（實體、鏈結、網路、傳輸、會議、表現、應用）；業界常用的「L4」「L7」等稱呼來自它。 | 第 2 章 |
| packet | 封包 | 網路傳送的基本資料單位；嚴格說 L3 的 PDU 是 packet，L2 是 frame、TCP 是 segment、UDP 是 datagram。 | 第 1 章 → 第 2 章 |
| payload | 酬載 | 一個 PDU 中 header 之後、真正要交付給上一層的資料。 | 第 2 章 |
| ping | — | 送 ICMP echo request 量 RTT 與丟包的工具；沒回應不代表主機掛了，可能只是 ICMP 被擋或限速。 | 第 3 章 → 第 8 章 |
| propagation delay | 傳播延遲 | 訊號在介質中跑完距離的時間，由距離決定；是物理下限，加頻寬也縮不短，只能減少往返或把伺服器移近使用者。 | 第 1 章 |
| queuing delay | 排隊延遲 | 封包在路由器或主機佇列裡等待送出的時間；隨負載變化，是 bufferbloat 的來源。 | 第 1 章 → 第 12 章 |
| RFC（Request for Comments） | — | IETF 發布的技術文件系列；發布後內容永遠不改，錯誤另外登記 errata，改行為則發布新 RFC 並標明 Updates 或 Obsoletes 舊編號。 | 第 2 章 |
| RTT（round-trip time） | 往返時間 | 封包從送出到收到回應的時間；連線建立、TLS 交握與擁塞控制的速度都以 RTT 為單位。 | 第 1 章 → 第 12 章 |
| ss | — | Linux 的 socket 統計工具；`ss -tanp` 看 TCP 狀態與所屬 process，`-ti` 看 cwnd、RTT 與重傳。 | 第 3 章 → 第 10 章 |
| tcpdump | — | 命令列抓包工具，用 BPF 過濾、可寫成 pcap 給 Wireshark 讀；需要權限，在 production 要限制抓取範圍。 | 第 3 章 |
| TCP/IP model | TCP/IP 模型 | 網際網路實際採用的四層模型（鏈結、網路、傳輸、應用）。 | 第 2 章 |
| traceroute | — | 逐步加大 TTL（Hop Limit），利用每一跳回的 ICMP Time Exceeded 畫出路徑；只看得到去程，回程可能不同。 | 第 3 章 → 第 6 章 |
| transmission delay | 傳輸延遲 | 把一個封包的所有 bit 推上線路所需的時間＝封包大小 ÷ 鏈路頻寬。 | 第 1 章 |
| TTFB（Time To First Byte） | 首 byte 時間 | 從送出請求到收到回應第一個 byte 的時間，包含網路往返與伺服器處理。 | 第 1 章 → 第 46 章 |
| Wireshark | — | 圖形化封包分析工具，能解碼數百種協定，並標出重傳、dup ACK 等 TCP 異常。 | 第 3 章 |

## A.2 鏈結層與 IP

同一個網段內怎麼送到下一台設備（Ethernet、ARP、VLAN），以及 IP 位址、子網、分片與 MTU（第 4、5、8 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| ARP（Address Resolution Protocol） | 位址解析協定 | 在同一個廣播網域裡廣播詢問某個 IPv4 位址的 MAC；問的永遠是下一跳的 IP，不是最終目的地。 | 第 1 章 → 第 4 章 |
| ARP cache | ARP 快取 | 主機記住「IP → MAC」對應的表，Linux 稱為 neighbor table，`ip neigh` 查看；項目有狀態與逾時。 | 第 4 章 |
| ARP spoofing | ARP 欺騙 | 因為 ARP 沒有驗證，任何主機都能回假答案把流量引到自己；交換器端用 DHCP snooping 與 Dynamic ARP Inspection 防禦。 | 第 4 章 |
| broadcast domain | 廣播網域 | 一個廣播 frame 能到達的範圍；交換器不切割它，路由器與 VLAN 才會。 | 第 4 章 |
| CIDR（Classless Inter-Domain Routing） | 無類別網域間路由 | 用「位址／前綴長度」表示網段（例如 10.20.0.0/16），取代舊的 A／B／C 類別劃分。 | 第 5 章 |
| CSMA/CA | 載波偵測多重存取／碰撞避免 | Wi-Fi 的媒介存取方式：先聽通道是否空閒、隨機退避後才送，並靠 ACK 確認，因為無線電無法邊送邊偵測碰撞。 | 第 4 章 |
| DF（Don't Fragment） | 不可分片旗標 | IPv4 header 的旗標；設了 DF 的封包太大時路由器丟棄並回 ICMP「需要分片」，是 Path MTU Discovery 的基礎。 | 第 8 章 |
| DHCP | 動態主機設定協定 | 主機開機時向 DHCP server 租用 IPv4 位址、遮罩、預設閘道與 DNS server。 | 第 5 章 |
| dual stack | 雙協定堆疊 | 主機與服務同時支援 IPv4 與 IPv6，DNS 同時有 A 與 AAAA；client 用 Happy Eyeballs 避免被壞的一邊拖累。 | 第 5 章 |
| Ethernet | 乙太網路 | 最普遍的有線區域網路技術；frame 含目的與來源 MAC、EtherType、payload 與 FCS，預設 MTU 1500。 | 第 4 章 |
| FCS（Frame Check Sequence） | 訊框檢查序列 | Ethernet frame 尾端的 CRC-32；錯誤的 frame 直接丟棄、不會通知任何人。 | 第 4 章 |
| fragmentation | 分片 | IP 封包超過鏈路 MTU 時切成多片、到終點再重組；只有第一片有 L4 header，任一片遺失整個封包作廢。IPv6 路由器永遠不分片。 | 第 2 章 → 第 8 章 |
| frame | 訊框 | 鏈結層的 PDU，例如一個 Ethernet frame；影音領域的 frame 指一張畫面或一段音訊，見 A.11。 | 第 4 章 |
| Happy Eyeballs | — | dual stack client 錯開時間並行嘗試 IPv6 與 IPv4 連線、誰先成功用誰的演算法，廣泛實作的是第二版（RFC 8305）。 | 第 5 章 |
| ICMP | 網際網路控制訊息協定 | IP 層的錯誤回報與查詢協定（Destination Unreachable、Time Exceeded、echo）；擋光 ICMP 會弄壞 PMTUD。 | 第 3 章 → 第 8 章 |
| IPv6 | — | 128 bit 位址的新版 IP；header 固定 40 bytes、路由器不分片、最小 MTU 1280，LAN 子網固定為 /64。 | 第 5 章 |
| link-local address | 鏈路本地位址 | 只在同一條鏈路有效、不能被路由的位址：IPv4 的 169.254.0.0/16、IPv6 的 fe80::/10；IPv6 使用時要加 zone ID。 | 第 5 章 |
| MAC address | MAC 位址 | 48 bit 的鏈結層位址，寫成 6 組十六進位；前 3 bytes 為廠商代碼（OUI），`02:` 開頭為本地管理位址。密碼學的 MAC 見 A.6。 | 第 1 章 → 第 4 章 |
| MAC address table | MAC 位址表 | 交換器學到的「MAC → 埠（與 VLAN）」對應，靠讀取 frame 的來源 MAC 學習。 | 第 4 章 |
| MSS（Maximum Segment Size） | 最大區段長度 | TCP 在 SYN 中宣告的單一 segment 最大 payload；IPv4 乙太網路為 1460，含 timestamp 選項時實際約 1448。 | 第 2 章 → 第 8 章 |
| MSS clamping | MSS 夾限 | 隧道端點在轉送 SYN／SYN-ACK 時把 MSS 改小，讓 TCP 一開始就送夠小的 segment，不依賴 ICMP；只對 TCP 有效。 | 第 8 章 |
| MTU（Maximum Transmission Unit） | 最大傳輸單元 | 一條鏈路一次能承載的最大 IP 封包，Ethernet 預設 1500、IPv6 最小 1280；路徑上所有鏈路的最小值稱為 Path MTU，隧道與 overlay 會讓它變小。 | 第 2 章 → 第 8 章 |
| NDP（Neighbor Discovery Protocol） | 鄰居探索協定 | IPv6 以 ICMPv6 的 NS／NA／RS／RA 訊息取代 ARP，並負責路由器探索與 DAD。 | 第 5 章 |
| Packet Too Big | 封包太大 | ICMPv6 Type 2，帶下一跳 MTU；IPv6 PMTUD 完全依賴它，因此絕對不能擋。 | 第 8 章 |
| PMTUD（Path MTU Discovery） | 路徑 MTU 探索 | 送設了 DF 的封包，靠路由器回的 ICMP 得知路徑 MTU；ICMP 被擋時就成了黑洞，症狀是「小請求正常、大回應卡住」。 | 第 8 章 |
| prefix length | 前綴長度 | CIDR 斜線後的數字，表示位址前幾個 bit 是網路部分；/26 有 64 個位址，不是 26 個。 | 第 5 章 |
| SLAAC（Stateless Address Autoconfiguration） | 無狀態位址自動設定 | IPv6 主機從 RA 拿到 /64 前綴，自己產生介面 ID 組成位址，不需要 DHCP server。 | 第 5 章 |
| STP（Spanning Tree Protocol） | 生成樹協定 | 交換器之間協商出一棵沒有迴圈的樹、阻擋多餘的連線；沒有它，迴圈會造成廣播風暴，因為 Ethernet frame 沒有 TTL。 | 第 4 章 |
| subnet | 子網 | 共用同一個前綴的一段位址；同子網直接用 ARP／NDP 送達，跨子網要交給路由器。 | 第 5 章 |
| subnet mask | 子網遮罩 | 以連續的 1 標出網路部分的 32 bit 值，例如 /24 為 255.255.255.0；判斷「同網段」看的是送出端自己的遮罩。 | 第 4 章 → 第 5 章 |
| switch | 交換器 | 讀 frame 的 MAC、學習位址並只轉送到正確埠的鏈結層設備；不切割廣播網域。 | 第 4 章 |
| VLAN（Virtual LAN） | 虛擬區域網路 | 在同一台交換器上切出彼此隔離的廣播網域；trunk 埠以 802.1Q tag 承載多個 VLAN，VLAN 之間互通要經過路由。聲聲 Live 攝影棚為 VLAN 10、辦公室為 VLAN 20。 | 第 4 章 |
| VLSM（Variable Length Subnet Mask） | 可變長度子網遮罩 | 同一個大網段內依需求切出不同大小的子網，由大到小放置以免重疊。 | 第 5 章 |

## A.3 路由與 NAT

跨網段時誰決定下一跳、網際網路之間怎麼交換路由，以及 NAT 與防火牆怎麼改寫與過濾封包（第 6、7 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| anycast | 任播 | 多個地點用 BGP 宣告同一個前綴，封包由路由選到「最近」的一個；CDN 與公共 DNS 常用。 | 第 1 章 → 第 6 章 |
| AS（Autonomous System） | 自治系統 | 由單一組織管理、對外有一致路由政策的網路，以 ASN 識別；聲聲 Live 是 AS64500。 | 第 1 章 → 第 6 章 |
| BGP（Border Gateway Protocol） | 邊界閘道協定 | AS 之間交換路由的協定（BGP-4），跑在 TCP 179 上；每個 prefix 各自依政策選路。 | 第 1 章 → 第 6 章 |
| CGNAT（Carrier-Grade NAT） | 電信級 NAT | 電信業者用大型 NAT 讓許多用戶共用公網 IPv4，內部使用 RFC 6598 的共享位址空間 100.64.0.0/10；同一個公網 IP 後面可能是一整區的用戶。 | 第 5 章 → 第 7 章 |
| connection tracking table | 連線追蹤表 | NAT 與 stateful 防火牆記錄每條連線五元組與翻譯結果的表，Linux 稱 conntrack；表滿時新連線被丟棄。 | 第 7 章 |
| control plane | 控制平面 | 決定「該怎麼走」的部分：執行路由協定、算出路由（RIB）；對照實際搬封包的資料平面。 | 第 6 章 |
| default gateway | 預設閘道 | routing table 中 `0.0.0.0/0` 那條路由的下一跳；目的地不在任何更具體的網段時交給它。 | 第 6 章 |
| DNAT（Destination NAT） | 目的位址轉換 | 改寫進入封包的目的位址與 port，port forwarding、LB 與 Kubernetes Service 都靠它。 | 第 7 章 → 第 44 章 |
| ECMP（Equal-Cost Multi-Path） | 等價多路徑 | 到同一目的地有多條成本相同的路徑時，依五元組雜湊分流，同一條連線固定走同一條路。 | 第 6 章 |
| filtering behavior | filtering 行為 | 對外 port 已有 mapping 後，NAT 允許誰從外面送封包進來：任何人、只限曾送過的 IP，或只限 IP 加 port。 | 第 7 章 |
| hairpinning | 髮夾轉送 | 內部主機連 NAT 自己的公網位址時，NAT 把封包轉回內部；又稱 NAT loopback，很多 NAT 不支援。 | 第 7 章 |
| hole punching | 打洞 | 兩端經 signaling 交換 server-reflexive 位址後同時向對方送封包，讓雙方 NAT 都留下 mapping 以建立 P2P 路徑。 | 第 7 章 |
| IXP（Internet Exchange Point） | 網際網路交換中心 | 許多 AS 接上同一組交換器、以低成本互相 peering 的中立機房，常附 route server。 | 第 6 章 |
| longest prefix match | 最長前綴匹配 | 路由查表時，在所有涵蓋目的地的路由中挑前綴最長（最具體）的一條，不是由上往下找第一條。 | 第 6 章 |
| mapping behavior | mapping 行為 | 同一個內部位址與 port 送往不同目的地時，NAT 是否沿用同一個對外 port（RFC 4787 分為三級）。 | 第 7 章 |
| NAPT（Network Address and Port Translation） | 位址與埠轉換 | 同時改寫位址與 port，讓多台內部主機共用一個公網 IP；日常說的 NAT 多半是它。 | 第 7 章 |
| NAT（Network Address Translation） | 網路位址轉換 | 在封包經過時改寫位址（與 port）並記錄對應；擋住外部主動連線只是副作用，NAT 不是防火牆。 | 第 1 章 → 第 7 章 |
| private address | 私有位址 | RFC 1918 保留的 10.0.0.0/8、172.16.0.0/12、192.168.0.0/16，不在網際網路上路由，出網要經 NAT。 | 第 1 章 → 第 5 章 |
| RIB（Routing Information Base） | 路由資訊庫 | 控制平面從各來源學到的所有路由；挑出的最佳路由寫進資料平面的 FIB（轉送表）供高速查詢。 | 第 6 章 |
| route leak | 路由洩漏 | AS 把從某處學到的路由違反商業政策地轉宣告出去，讓大量流量繞經不該經過的網路。 | 第 6 章 |
| routing table | 路由表 | 「目的網段 → 下一跳／出口介面」的清單，用最長前綴匹配查詢；Linux 用 `ip route` 查看。 | 第 1 章 → 第 6 章 |
| ROV（Route Origin Validation） | 路由起源驗證 | 收到 BGP 宣告時對照 ROA（經簽章的「某前綴只能由某 AS 宣告」聲明）判為 Valid、Invalid 或 NotFound；只驗證 origin AS，不驗證整條路徑。 | 第 6 章 |
| rp_filter（reverse path filter） | 反向路徑過濾 | Linux 檢查「回覆來源會不會從同一張介面出去」，否則丟棄；多網卡、非對稱路由時會讓合法流量無聲消失。 | 第 6 章 |
| RPKI（Resource Public Key Infrastructure） | 資源公鑰基礎設施 | 把 IP 位址與 ASN 的分配用憑證簽起來的體系，供 ROA 與 ROV 使用。 | 第 6 章 |
| server-reflexive address | 伺服器反射位址 | 從 NAT 外面（STUN server）看到的公網位址與 port。 | 第 7 章 → 第 36 章 |
| SNAT（Source NAT） | 來源位址轉換 | 改寫外出封包的來源位址（與 port），讓內部主機共用對外位址。 | 第 7 章 |
| stateful firewall | 有狀態防火牆 | 依連線追蹤表判斷進來的封包是既有連線的回程（ESTABLISHED）還是陌生的新連線（NEW），只要寫「誰可以主動連進來」。 | 第 7 章 |
| transit／peering | 轉接／互連 | transit 是付費讓上游代轉到整個網際網路；peering 是雙方免費交換彼此（與客戶）的流量。 | 第 6 章 |
| TTL（Time To Live） | 存活時間 | IPv4 header 的跳數計數（IPv6 為 Hop Limit），每台路由器減 1，到 0 丟棄並回 ICMP Time Exceeded；traceroute 靠它運作。DNS 的 TTL 是另一回事，見 A.5。 | 第 6 章 |

## A.4 傳輸層與 QUIC

UDP、TCP 的連線、可靠傳輸與擁塞控制，以及把這些搬到 UDP 上重做的 QUIC（第 9–13 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| 0-RTT | 零往返資料 | 用先前連線留下的 session ticket／PSK，在第一趟就送出應用資料；可能被重放，只能放行 idempotent 請求（聲聲 Live 只放行 GET／HEAD，其他回 425）。 | 第 13 章 → 第 18 章 |
| accept queue | 已完成佇列 | 已完成三向交握、等應用程式 `accept()` 取走的連線；長度上限由 backlog 決定，滿了新連線會被丟棄。 | 第 10 章 |
| ACK（acknowledgment） | 確認 | TCP 以累積確認回報「下一個期待的序號」；QUIC 的 ACK frame 用多段範圍回報，比 SACK 更完整。 | 第 9 章 → 第 11 章 |
| backlog | — | `listen()` 的參數，限制 accept queue 長度（Linux 另受 `somaxconn` 限制）；聲聲 Live 教室入口 API 設為 2048。 | 第 10 章 |
| BBR | — | 以估計的瓶頸頻寬與最小 RTT 控制送出速率的擁塞控制，靠 pacing 平滑送出，不把丟包當主要訊號。 | 第 12 章 |
| BDP（bandwidth-delay product） | 頻寬延遲乘積 | 頻寬 × RTT，代表把管線填滿所需的在途資料量；視窗小於 BDP 時吞吐量受限。 | 第 12 章 |
| bufferbloat | 緩衝膨脹 | 網路設備的佇列過大，壅塞時封包不被丟而是長時間排隊，造成數百毫秒的延遲；AQM 是解法。 | 第 12 章 |
| byte stream | 位元組串流 | TCP 的抽象：只有一長串連續 bytes、不保留 `send()` 的邊界，應用層必須自己做 framing。 | 第 9 章 → 第 11 章 |
| CLOSE_WAIT | — | 被動關閉方收到 FIN 後、應用程式還沒 `close()` 前的狀態；長時間堆積幾乎一定是本機程式的 bug。 | 第 10 章 |
| CoDel／FQ-CoDel | — | 依封包在佇列停留時間決定丟包的 AQM（預設目標 5 ms）；FQ-CoDel 再讓每條流有自己的小佇列輪流送。 | 第 12 章 |
| congestion control | 擁塞控制 | 傳送端依網路狀況（遺失、延遲）調整在途資料量，避免壓垮瓶頸；對照只保護接收端的流量控制。 | 第 12 章 |
| connection ID | 連線 ID | QUIC 用來識別連線的值（DCID／SCID）；NAT rebinding 或換網路使四元組改變時，連線仍能找到。 | 第 13 章 |
| connection migration | 連線遷移 | QUIC client 換了網路（Wi-Fi 換 4G）後以同一個 connection ID 繼續連線，並以 PATH_CHALLENGE／PATH_RESPONSE 驗證新路徑。 | 第 13 章 |
| CUBIC | — | Linux 預設的擁塞控制，cwnd 依距上次遺失的時間以三次函數成長，長肥管線上比 Reno 更快回到原速率。 | 第 12 章 |
| cwnd（congestion window） | 擁塞視窗 | 傳送端自己估計的「網路能承受的在途資料量」；實際可送量是 min(cwnd, rwnd)。 | 第 12 章 |
| Delayed ACK | 延遲確認 | 接收端等一小段時間再回 ACK，以便合併或搭便車；Linux 最小約 40 ms，和 Nagle 疊加會造成固定延遲。 | 第 11 章 |
| ephemeral port | 臨時埠 | client 端由作業系統自動挑選的來源 port；Linux 預設 32768–60999，macOS／Windows 49152–65535。 | 第 9 章 |
| fast retransmit | 快速重傳 | 收到 3 個重複 ACK（dupACK）就判定遺失、不等 RTO 立刻重傳。 | 第 11 章 |
| file descriptor | 檔案描述符 | 作業系統代表開啟的檔案或 socket 的整數；每條連線佔一個，超過上限得到 `EMFILE`。 | 第 9 章 → 第 40 章 |
| five-tuple | 五元組 | （協定, 來源 IP, 來源 port, 目的 IP, 目的 port），唯一識別一條連線或流。 | 第 9 章 |
| flow control | 流量控制 | 接收端以 rwnd（TCP header 的 Window 欄位）告訴傳送端自己還能收多少，保護接收端緩衝區；不管網路壅塞。 | 第 11 章 |
| framing | 訊息切割 | 在 byte stream 上標出訊息邊界的方式：長度前綴、分隔符號或固定長度。 | 第 9 章 → 第 11 章 |
| half-open connection | 半開連線 | 一端已經消失（斷電、斷網）而另一端仍以為連線存在；靠 keepalive 或應用層心跳偵測。 | 第 10 章 |
| head-of-line blocking | 隊頭阻塞 | 前面一個單位遺失或卡住，後面已到的資料也只能等；有 HTTP 層（HTTP/1.1）與 TCP 層（HTTP/2）兩種，QUIC 消除後者。 | 第 1 章 → 第 12 章 |
| ISN（Initial Sequence Number） | 起始序號 | SYN 中選定的第一個序號，依時鐘加上四元組與秘密值的雜湊產生，避免舊連線干擾與被猜中。 | 第 10 章 |
| keepalive（TCP keepalive） | 存活探測 | 連線閒置一段時間後由核心送探測 segment，多次沒回應就判定死亡；預設數小時，通常要自行調短或用應用層心跳。 | 第 11 章 |
| Nagle's algorithm | Nagle 演算法 | 有未確認資料時把小資料留著合併再送；互動式小訊息用 `TCP_NODELAY` 關閉。 | 第 11 章 |
| ossification | 協定僵化 | 中間設備依賴協定的可見欄位，使新功能（新 option、新旗標）難以部署；QUIC 以加密 header 對抗。 | 第 13 章 |
| QUIC | — | 跑在 UDP 上、內建 TLS 1.3 的傳輸協定（RFC 9000）：多 stream 無 TCP 層 HOL、1-RTT 建連、connection migration，幾乎整個 header 加密；驗證 client 位址前送出量不得超過收到的 3 倍。 | 第 1 章 → 第 13 章 |
| RST | 重設 | 立即中止連線的 TCP 旗標；送到沒人 listen 的 port、或程式在有未讀資料時關閉都會產生。 | 第 10 章 |
| RTO（retransmission timeout） | 重傳逾時 | 超過這個時間沒收到 ACK 就重傳；依 SRTT 與 RTTVAR 動態計算，連續逾時會指數退避。 | 第 11 章 |
| SACK（Selective ACK） | 選擇性確認 | 接收端回報已收到的不連續區段，讓傳送端只重傳缺口；需在 SYN 中協商 SACK-Permitted。 | 第 11 章 |
| sliding window | 滑動視窗 | 允許多個 segment 同時在途而不必逐一等待 ACK；吞吐量約等於視窗 ÷ RTT。 | 第 11 章 |
| slow start | 慢啟動 | 連線初期每收到一個 ACK 讓 cwnd 增加一個 MSS，約每 RTT 翻倍，直到遺失或達 ssthresh；短連線大多在這個階段結束。 | 第 1 章 → 第 12 章 |
| stream（QUIC） | 串流 | QUIC 連線中的獨立有序位元組流；一條 stream 遺失不影響其他 stream。 | 第 13 章 |
| SYN cookies | — | SYN queue 滿時核心不保存狀態，把必要資訊編進回應的 ISN，收到合法 ACK 再建立連線，用來抵抗 SYN flood。 | 第 10 章 |
| SYN queue | 半連線佇列 | 收到 SYN、已回 SYN+ACK、等待第三個 ACK 的連線。 | 第 10 章 |
| TCP | 傳輸控制協定 | 在 IP 上提供可靠、有序、不重複的 byte stream 與擁塞控制的傳輸協定（RFC 9293）。 | 第 1 章 → 第 10 章 |
| TCP Fast Open | — | 重複連線的 client 在 SYN 中夾帶資料以省一個 RTT；因中間設備相容性問題，實務部署有限。 | 第 10 章 |
| three-way handshake | 三向交握 | SYN → SYN+ACK → ACK，雙方確認彼此能收送並交換起始序號；client 的 `connect()` 約耗時一個 RTT。 | 第 1 章 → 第 10 章 |
| TIME_WAIT | — | 主動關閉方送出最後一個 ACK 後等待約 2×MSL 的狀態，確保最後的 ACK 送達並讓舊 segment 消失。 | 第 10 章 |
| UDP | 使用者資料包協定 | 只加 port 與 checksum 的無連線傳輸協定，header 8 bytes，保留訊息邊界、不保證送達與順序。 | 第 9 章 |
| Window Scale | 視窗縮放選項 | 在 SYN 中協商的位移量，讓 16 bit 的 Window 欄位能表示超過 64 KB 的視窗。 | 第 11 章 |
| zero window | 零視窗 | 接收端緩衝區已滿、宣告 rwnd=0；傳送端暫停，以 persist timer 定期送 zero window probe。 | 第 11 章 |

## A.5 DNS

名稱怎麼被解析、快取多久、在系統與 Kubernetes 裡走哪條路（第 14–16 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| A／AAAA record | A／AAAA 紀錄 | 名稱對應 IPv4／IPv6 位址的紀錄。 | 第 3 章 → 第 14 章 |
| apex（zone apex） | 區域頂點 | zone 的最上層名稱（例如 `shengsheng.example` 本身），必須有 SOA 與 NS，所以不能放 CNAME；供應商以 ALIAS／ANAME／CNAME flattening 變通。 | 第 14 章 → 第 15 章 |
| authoritative server | 權威伺服器 | 某個 zone 的資料來源，只回答自己 zone 的資料或給出授權的 referral；回應帶 AA 旗標。 | 第 1 章 → 第 14 章 |
| cache poisoning | 快取投毒 | 讓 resolver 快取偽造的答案；防禦有來源 port 隨機化、0x20 大小寫隨機化、bailiwick 檢查、DNS Cookies 與 DNSSEC。 | 第 14 章 → 第 15 章 |
| CNAME | 別名紀錄 | 把一個名稱指向另一個名稱；有 CNAME 的名稱不能再有其他任何紀錄。 | 第 1 章 → 第 15 章 |
| CoreDNS | — | Kubernetes 叢集內預設的 DNS server，以 kube-dns Service（聲聲 Live 為 10.96.0.10）提供 Service 名稱解析。 | 第 16 章 |
| dangling CNAME | 懸空別名 | CNAME 指向的外部資源已被刪除、紀錄卻還在，可能讓他人搶註同名資源造成 subdomain takeover。 | 第 15 章 |
| delegation | 授權 | 上層 zone 以 NS 紀錄把子網域交給另一組權威伺服器管理。 | 第 14 章 |
| DNS（Domain Name System） | 網域名稱系統 | 以階層式命名、分散式授權與大量快取，把名稱對應到位址等資料的分散式資料庫。 | 第 1 章 → 第 14 章 |
| DNSSEC（DNS Security Extensions） | DNS 安全擴充 | 以 DNSKEY（公鑰）、RRSIG（簽章）與父區的 DS 建立從 root trust anchor 開始的信任鏈，保證答案的完整性與來源真實性；驗證失敗回 SERVFAIL，不提供機密性。 | 第 15 章 |
| DoT／DoH／DoQ | 加密 DNS | 把 DNS 查詢放進 TLS（DoT，TCP 853）、HTTPS（DoH）或 QUIC（DoQ）中傳送，保護 client 到 resolver 這一段的機密性。 | 第 15 章 |
| EDNS(0) | — | 以 OPT pseudo-RR 擴充 DNS，宣告可接收的 UDP 回應大小與 DO 等旗標；建議值 1232 bytes 以避免分片。 | 第 14 章 |
| /etc/resolv.conf | — | 設定 nameserver、search 與 options（ndots、timeout）的檔案；用 systemd-resolved 時只會看到 127.0.0.53。 | 第 16 章 |
| FQDN（Fully Qualified Domain Name） | 完整網域名稱 | 從主機一路寫到 root 的完整名稱；結尾加點（`pay.example.net.`）表示絕對名稱，不套 search。 | 第 14 章 |
| GeoDNS | 地理 DNS | 依查詢來源的位置回不同答案；權威端看到的是 resolver 的位址而不是使用者的，ECS 擴充可附上使用者 IP 前綴，代價是隱私。 | 第 15 章 |
| getaddrinfo | — | 應用程式解析名稱的標準函式，依 nsswitch、hosts 與 resolv.conf 查詢，回傳排序後的位址清單；不看 TTL。 | 第 16 章 |
| glue record | 黏附紀錄 | 上層 zone 在 referral（「去問這些 NS」）中一併給出子區 NS 主機的位址，解決 NS 名稱在自己 zone 裡的雞生蛋問題。 | 第 14 章 |
| HTTPS／SVCB record | — | 告訴 client 服務端點與參數（`alpn="h2,h3"`、位址提示、ECH 設定）的紀錄；priority 0 為 AliasMode，可放在 apex。 | 第 14 章 |
| iterative query | 迭代查詢 | resolver 依 referral 一層一層向 root、TLD、權威伺服器查詢；stub 對 resolver 則是遞迴查詢。 | 第 14 章 |
| ndots | — | resolv.conf 選項：名稱中的點少於 ndots 時先套 search domain；Kubernetes 預設 5，外部名稱會先查好幾次失敗。 | 第 16 章 |
| negative caching | 負面快取 | resolver 把 NXDOMAIN 與 NODATA 也快取一段時間，長度由 SOA 決定。 | 第 14 章 → 第 15 章 |
| NXDOMAIN／NODATA | — | NXDOMAIN（rcode 3）表示名稱不存在；NODATA 是 NOERROR 但 answer 為空，代表名稱存在、沒有該 type。 | 第 15 章 |
| rcode | 回應碼 | DNS header 中的結果代碼：0 NOERROR、2 SERVFAIL、3 NXDOMAIN、5 REFUSED 等。 | 第 14 章 → 第 15 章 |
| recursive resolver | 遞迴 resolver | 替 client 從 root 開始查到答案並快取的伺服器（ISP、公共 DNS、VPC resolver）。 | 第 14 章 |
| resource record（RR） | 資源紀錄 | DNS 的資料單位：名稱、type、class、TTL 與資料；同名同 type 的一組稱 RRset。 | 第 14 章 |
| search domain | 搜尋網域 | resolv.conf 的 search 清單，讓短名稱自動補上網域後綴再查詢。 | 第 16 章 |
| SERVFAIL | — | rcode 2，resolver 無法取得可信答案，包括 DNSSEC 驗證為 bogus、權威伺服器全部無回應。 | 第 15 章 |
| service discovery | 服務發現 | 呼叫方找到服務實例的方式：client-side（自己拿清單挑）或 server-side（交給 LB 或 ClusterIP 挑）。 | 第 16 章 |
| split-horizon DNS | 分割視野 DNS | 同一個名稱依查詢者在內網或外網回不同答案，例如 `api` 在 VPC 內解析成 10.20.16.5。 | 第 15 章 → 第 44 章 |
| stub resolver | 存根解析器 | 作業系統內只負責把查詢送給遞迴 resolver 的元件，RD 旗標設為 1。 | 第 1 章 → 第 16 章 |
| subdomain takeover | 子網域接管 | dangling CNAME 指向的資源被他人重建，對方得以用你的子網域提供內容。 | 第 15 章 |
| systemd-resolved | — | Linux 的本機 stub resolver 與快取，在 127.0.0.53 提供服務；用 `resolvectl` 查看真正的上游。 | 第 16 章 |
| TLD（Top-Level Domain） | 頂級網域 | root 之下的第一層，例如 `com`、`tw` 與本書範例用的 `example`。 | 第 14 章 |
| TTL（DNS） | 存活時間 | 紀錄可被快取的秒數；resolver 回給 client 的是剩下的秒數，改紀錄前要先把 TTL 調低並等舊 TTL 過去。IP header 的 TTL 是跳數，見 A.3。 | 第 1 章 → 第 15 章 |
| zone | 區域 | 由同一組權威伺服器管理的一段名稱空間，以 delegation 為邊界。 | 第 14 章 |

## A.6 密碼學與 TLS

雜湊、MAC、加密、簽章與金鑰交換，以及 TLS 1.3、憑證與 HTTPS 部署（第 17–19 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| ACME | 自動化憑證管理環境 | CA 與 client 自動申請、驗證、更新憑證的協定；每個請求都以帳號金鑰做 JWS 簽章，網域驗證用 HTTP-01、DNS-01 或 TLS-ALPN-01。 | 第 16 章 → 第 19 章 |
| AEAD（Authenticated Encryption with Associated Data） | 鑑別加密 | 一次提供機密性與完整性的加密，附加資料只驗證不加密；驗證失敗時不吐出任何明文，例如 AES-GCM、ChaCha20-Poly1305。 | 第 17 章 |
| ALPN（Application-Layer Protocol Negotiation） | 應用層協定協商 | TLS 擴充，在交握時協商之後要說 h2、http/1.1 或 h3。 | 第 1 章 → 第 18 章 |
| asymmetric cryptography | 非對稱密碼 | 公鑰公開、私鑰自留的密碼學：公鑰加密或驗章、私鑰解密或簽章，例如 RSA、ECC。 | 第 17 章 |
| CA（Certificate Authority） | 憑證機構 | 驗證申請者後以自己的私鑰簽發憑證的機構；瀏覽器與作業系統內建受信任的 root CA。 | 第 17 章 → 第 18 章 |
| certificate | 憑證 | 把公鑰綁定到名稱並由 CA 簽章的文件，格式為 X.509；包含 subject、issuer、效期、SAN 與用途。 | 第 17 章 → 第 18 章 |
| certificate chain | 憑證鏈 | leaf 憑證 → 中間 CA → root CA 的簽章序列；server 必須送出中間憑證，缺了就是鏈不完整。 | 第 18 章 |
| Certificate Transparency（CT） | 憑證透明度 | CA 把每張公開憑證登錄到可公開稽核的 log，瀏覽器要求憑證帶有 SCT；網域擁有者可監控是否有人替自己的網域簽發憑證。 | 第 19 章 |
| ClientHello | — | TLS 交握第一個訊息，帶 SNI、ALPN、支援的密碼套件與金鑰交換公開值。 | 第 1 章 → 第 18 章 |
| CRL／OCSP | 憑證撤銷清單／線上憑證狀態協定 | 兩種查詢憑證是否被撤銷的機制；OCSP stapling 由 server 在交握時附上 CA 簽過的狀態。截至 2026 年 10 月，業界正從 OCSP 轉向 CRL。 | 第 19 章 |
| CSPRNG | 密碼學安全亂數產生器 | 看過所有先前輸出也無法預測下一個的亂數源；Python 用 `secrets` 或 `os.urandom()`，不能用 `random`。 | 第 17 章 |
| Diffie-Hellman key exchange | DH 金鑰交換 | 雙方只交換公開值就算出同一個共享秘密，竊聽者無法推得；但它不驗證對方是誰，需要簽章防中間人。 | 第 17 章 |
| digital signature | 數位簽章 | 以私鑰對訊息摘要簽章、任何人用公鑰驗證，提供完整性、真實性與不可否認性。 | 第 17 章 |
| DNS-01／HTTP-01／TLS-ALPN-01 | ACME 驗證方式 | 分別以 DNS TXT 紀錄、port 80 上的檔案、port 443 上特殊 ALPN 的臨時憑證證明控制網域；只有 DNS-01 能申請 wildcard。 | 第 16 章 → 第 19 章 |
| ECH（Encrypted Client Hello） | 加密 ClientHello | 把真正的 SNI 與 ALPN 放進以 server 公鑰加密的內層 ClientHello，公鑰透過 DNS HTTPS record 發布。 | 第 18 章 |
| ephemeral DH（ECDHE） | 短暫 DH | 每次連線產生新的、用完即丟的 DH 金鑰對，提供前向保密。 | 第 17 章 |
| forward secrecy | 前向保密 | 長期私鑰日後外洩也解不開過去錄下的流量，來自每次連線用完即丟的 (EC)DHE；TLS 1.3 已移除沒有此性質的 RSA 金鑰傳輸。 | 第 17 章 → 第 18 章 |
| hash function（cryptographic） | 密碼學雜湊函數 | 把任意輸入變成固定長度摘要的函數，要求抗原像、抗第二原像與抗碰撞，並有雪崩效應。 | 第 17 章 |
| HKDF | — | 以 HMAC 為基礎的金鑰衍生函數：Extract 濃縮秘密、Expand 依用途標籤展開多把金鑰；TLS 1.3 金鑰排程由它構成。 | 第 17 章 |
| HMAC | — | 以雜湊函數與金鑰計算的 MAC，不受 length extension 影響；比較 tag 必須用常數時間函式（`hmac.compare_digest`）。 | 第 17 章 |
| HSTS（HTTP Strict Transport Security） | — | 以 `Strict-Transport-Security` header 要求瀏覽器在 max-age 內只用 HTTPS、憑證錯誤時不讓使用者略過，用來防 SSL stripping；可加入 preload list。 | 第 1 章 → 第 19 章 |
| key schedule | 金鑰排程 | TLS 1.3 以一連串 HKDF 從 PSK、(EC)DHE 共享秘密與 transcript 導出各階段、各方向金鑰的過程。 | 第 18 章 |
| length extension | 長度延伸攻擊 | Merkle–Damgård 結構的雜湊（SHA-256、SHA-1、MD5）可在不知道秘密的情況下延長 `hash(secret + msg)`；所以要用 HMAC。 | 第 17 章 |
| MAC（Message Authentication Code） | 訊息鑑別碼 | 以共享金鑰計算的 tag，驗證訊息未被竄改且來自持有金鑰的一方；和網卡的 MAC 位址同名不同義。 | 第 17 章 |
| man-in-the-middle attack | 中間人攻擊 | 攻擊者分別和兩端建立連線、在中間轉送並讀取或竄改資料；未驗證身分的 DH 擋不住。 | 第 17 章 |
| mTLS（mutual TLS） | 雙向 TLS | client 也出示憑證、server 驗證 client 身分的 TLS；聲聲 Live 的 `ops` 後台採 mTLS 加 SSO。 | 第 18 章 → 第 30 章 |
| nonce | 一次性數值 | 只能使用一次的值；同一把金鑰下 nonce 永遠不能重複，否則串流加密與 AES-GCM 的保護會被破壞。 | 第 17 章 |
| PSK（pre-shared key） | 預先共享金鑰 | TLS 1.3 resumption 用 session ticket 換得的金鑰，可略過憑證驗證並啟用 0-RTT。 | 第 18 章 |
| SAN（subjectAltName） | 主體別名 | 憑證中列出它適用的名稱（DNS 名稱、IP、URI）的擴充；瀏覽器只看 SAN、不看 CN。 | 第 3 章 → 第 18 章 |
| self-signed certificate | 自簽憑證 | issuer 等於 subject、自己簽自己的憑證；除了手動釘選者沒有人信任，只適合開發測試。WebRTC 的 DTLS 則刻意使用自簽憑證加指紋。 | 第 18 章 |
| session resumption | 連線恢復 | 用先前連線的 ticket／PSK 跳過憑證交換，加速重複連線，並可用 0-RTT。 | 第 1 章 → 第 18 章 |
| SNI（Server Name Indication） | 伺服器名稱指示 | ClientHello 中的明文主機名稱，讓同一個 IP 依名稱選憑證；聲聲 Live 的 `auth` 與 `api` 共用 LB 就靠它。 | 第 1 章 → 第 18 章 |
| symmetric encryption | 對稱加密 | 加解密用同一把金鑰，速度快；問題在於如何安全地交換金鑰。 | 第 17 章 |
| TLS（Transport Layer Security） | 傳輸層安全 | 在可靠傳輸上提供機密性、完整性與 server 身分驗證的協定；TLS 1.3 完整交握為 1-RTT。 | 第 1 章 → 第 18 章 |
| TLS termination | TLS 終結 | 解開 TLS、看到明文 HTTP 的位置（CDN、LB 或 nginx）；決定私鑰放哪、憑證在哪更新、client IP 怎麼往後傳。 | 第 19 章 |
| transcript hash | 交握紀錄雜湊 | 到目前為止所有交握訊息的雜湊；CertificateVerify 與 Finished 都綁定它，竄改任一訊息都會失敗。 | 第 18 章 |
| wildcard certificate | 萬用字元憑證 | SAN 用 `*` 代表恰好一個 label，例如 `*.shengsheng.example` 不涵蓋 apex，也不涵蓋兩層子網域。 | 第 16 章 → 第 18 章 |
| X.509 | — | 憑證的標準格式，含 issuer、subject、validity、subjectAltName、basicConstraints、extKeyUsage 等欄位。 | 第 18 章 |

## A.7 HTTP 與 Web

HTTP 語意與快取、HTTP/1.1 到 HTTP/3、API 風格，以及 proxy、LB 與 CDN（第 20–22、24、25 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| 103 Early Hints | — | server 在主回應算好前先送的 1xx 回應，帶 `Link` header 讓瀏覽器提早預載資源；client 收到後要繼續讀真正的回應。 | 第 20 章 → 第 46 章 |
| 425 Too Early | — | server 拒絕在 0-RTT early data 中處理的請求；聲聲 Live 對 GET／HEAD 以外的 early data 一律回 425。 | 第 18 章 → 第 22 章 |
| Alt-Svc | 替代服務 | 回應 header，告訴瀏覽器同一服務也能在別的協定與 port 存取（例如 UDP 443 的 h3），`ma` 為有效秒數。 | 第 13 章 |
| Cache-Control | — | 宣告快取規則的 header：`max-age`、`s-maxage`、`private`、`no-store`、`immutable`、`stale-while-revalidate` 等；沒寫不等於不快取。 | 第 21 章 |
| CDN（Content Delivery Network） | 內容傳遞網路 | 在全球 PoP 放置 edge 快取並代為回源的服務，縮短 RTT、分擔 origin 負載；不能快取的請求也能經由 edge 到 origin 的較佳路徑加速。 | 第 1 章 → 第 25 章 |
| chunked transfer coding | 分塊傳輸 | HTTP/1.1 不知道總長度時，把 body 切成「長度＋內容」的區塊，以長度 0 的 last-chunk 結束。 | 第 20 章 |
| conditional request | 條件請求 | 帶 `If-None-Match` 或 `If-Modified-Since`（讀取）與 `If-Match`（寫入）的請求，讓 server 依版本決定回 304、412 或照常處理。 | 第 21 章 |
| connection coalescing | 連線合併 | 瀏覽器把另一個 origin 的請求送到既有的 HTTP/2／3 連線上，條件是 IP 相符且憑證涵蓋該名稱。 | 第 22 章 |
| Consistent hashing | 一致性雜湊 | 把後端與 key 映到同一個環上，增減後端時只有少數 key 換位置；變形有虛擬節點、Maglev 與 bounded loads。 | 第 25 章 |
| content negotiation | 內容協商 | 依 `Accept`、`Accept-Language`、`Accept-Encoding` 等選擇回應的表示法；回應要以 `Vary` 標明依據。 | 第 21 章 |
| cursor pagination | 游標分頁 | 記住上一頁最後一筆的排序鍵、從其後繼續讀（keyset 分頁）；深頁一樣快，插入資料也不錯位。 | 第 24 章 |
| deadline | 截止時刻 | 整個操作必須完成的時刻，隨請求往下游傳遞並逐層扣除已花時間；聲聲 Live 內部用 `x-deadline-ms` 傳遞。 | 第 24 章 |
| domain sharding | 網域分片 | 把資源分散到多個網域讓 HTTP/1.1 多開連線；在 HTTP/2 下反而多出 DNS 與交握。 | 第 22 章 |
| ETag | 實體標籤 | 代表某個表示法版本的 validator；強 ETag 要求逐 byte 相同，弱 ETag（`W/`）只要求語意相同。 | 第 21 章 |
| freshness | 新鮮度 | 快取回應在新鮮期內可直接使用；年齡超過新鮮期後要先重新驗證。 | 第 21 章 |
| GraphQL | — | client 用查詢語言指定要的欄位、由單一端點回應的 API 風格；解決 over／under-fetching，但 HTTP 快取幾乎失效、要防 N+1 與高成本查詢。 | 第 24 章 |
| gRPC | — | 以 HTTP/2 為傳輸、Protocol Buffers 為格式的 RPC 框架；結果放在 trailers 的 `grpc-status`，支援四種串流模式。 | 第 24 章 |
| health check（active／passive） | 健康檢查 | LB 主動定期探測後端（active），或依實際請求的失敗判斷（passive）；聲聲 Live 的 `/readyz` 間隔 5 秒、fall 2、rise 3。 | 第 25 章 |
| Host header | — | HTTP/1.1 必填的 header，讓同一個 IP 上的多個虛擬主機分辨請求；未經驗證就用來組網址會造成 Host header 攻擊。 | 第 20 章 |
| HPACK | — | HTTP/2 的 header 壓縮：靜態表、動態表與 Huffman 編碼；為避開 CRIME 類攻擊而不用通用壓縮。 | 第 22 章 |
| HTTP/1.1 | — | 以文字起始行與 header、CRLF 分隔的 HTTP 線路格式（RFC 9112）；預設保持連線，但同一連線上回應必須依序。 | 第 20 章 |
| HTTP/2 | — | 在一條 TCP 連線上以二進位 frame 多工多個 stream 的 HTTP（RFC 9113），消除 HTTP 層 HOL，但仍有 TCP 層 HOL。 | 第 22 章 |
| HTTP/3 | — | 跑在 QUIC 上的 HTTP，stream 由 QUIC 提供，header 壓縮改用 QPACK。 | 第 13 章 → 第 22 章 |
| HTTP request smuggling | 請求走私 | 前後兩層對同一段 bytes 的訊息邊界判斷不一致，使一部分被當成下一個請求；防禦是邊緣嚴格解析並正規化。 | 第 20 章 |
| idempotency key | 冪等鍵 | client 為一次操作產生的唯一值，server 據此辨認重試並回傳原結果；聲聲 Live 付款綁定 `(student_id, key)`、保存 24 小時。 | 第 20 章 → 第 24 章 |
| idempotent | 冪等 | 同一個請求做一次或多次，預期效果相同：PUT、DELETE 與所有 safe method（GET、HEAD、OPTIONS，語意上不改變狀態）；POST 要靠 idempotency key 才能安全重試。 | 第 20 章 |
| keep-alive（persistent connection） | 持久連線 | 同一條 TCP 連線上連續送多個請求；兩端閒置逾時不一致時，client 可能在 server 關閉的瞬間送出請求。 | 第 20 章 |
| L4／L7 load balancer | 四層／七層負載平衡器 | L4 只看位址與 port 轉送連線、不讀內容；L7 終結 HTTP、可依路徑與 header 路由並改寫。 | 第 25 章 |
| origin shield | 源站屏蔽層 | 所有 edge 的 miss 先匯集到一個指定的中間層 PoP，再由它回源，降低 origin 負載。 | 第 25 章 |
| Problem Details | 問題細節 | RFC 9457 的統一 JSON 錯誤格式（`application/problem+json`），以 `type` 給程式判斷。 | 第 24 章 |
| Protocol Buffers | — | 以欄位編號與 wire type 編碼的二進位序列化格式，用 `.proto` IDL 定義 schema；整數用 varint。 | 第 24 章 |
| PROXY protocol | — | L4 LB 在每條 TCP 連線開頭先送一段描述原始 client 位址的資料；後端只能接受來自 LB 的 PROXY header。 | 第 25 章 |
| purge | 清除快取 | 主動讓 CDN 上的快取失效；粒度從單一 URL、tag 到全站，全站 purge 會讓 origin 瞬間承受全部流量。 | 第 25 章 |
| QPACK | — | HTTP/3 的 header 壓縮；以 encoder／decoder stream 同步動態表，只有用到尚未到達的表項的 stream 才需要等待（blocked）。 | 第 22 章 |
| Range request | 範圍請求 | 以 `Range` header 要求部分內容，server 回 206 Partial Content；用於續傳與影片拖曳。 | 第 21 章 |
| redirect | 重新導向 | 3xx 回應以 `Location` 指示新位址；301／308 為永久、可被快取，302／303／307 為暫時。 | 第 21 章 |
| request collapsing | 請求合併 | 同一 key 正在回源時，後到的請求等待第一個請求的結果，避免同時回源（nginx 的 `proxy_cache_lock`）。 | 第 25 章 |
| REST | — | 以資源為中心、透過統一介面（HTTP method、status code）操作表現的 API 風格。 | 第 24 章 |
| reverse proxy | 反向代理 | 代表 server 接收請求再轉給後端的 proxy，例如 nginx；client 不知道它存在。 | 第 1 章 → 第 25 章 |
| Server push | 伺服器推送 | HTTP/2 server 以 PUSH_PROMISE 主動送資源的功能；實測效果很小甚至負面，Chrome 自 2022 年起預設停用，本書視為已退場，提早載入改用 103 Early Hints。 | 第 22 章 |
| shared cache／private cache | 共享快取／私有快取 | CDN、proxy 是多人共用的快取，瀏覽器是個人快取；含個人資料的回應必須標 `private`。 | 第 21 章 |
| sticky session | 黏性連線 | LB 讓同一個 client 固定送到同一台後端；後端掛掉時該 client 的狀態一併消失。 | 第 25 章 |
| URL | 網址 | scheme、host、port、path、query、fragment 組成的資源位置；非 ASCII 字元以 percent-encoding 表示（例如 `/teachers/美咲`），fragment 不會送到 server。 | 第 1 章 |
| Vary | — | 回應 header，列出 cache key（預設為 method 加 URL）要額外納入的請求 header，例如 `Origin`、`Accept-Encoding`。 | 第 21 章 |
| X-Forwarded-For／Forwarded | — | proxy 記錄 client 位址鏈的 header；面對 internet 的那一層覆寫、內部各層附加，後端從右往左跳過可信網段。 | 第 25 章 |

## A.8 瀏覽器安全

瀏覽器替使用者執行的安全規則：origin 與 site、CORS、cookie 屬性、CSRF、XSS 與 CSP（第 21、23 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| ambient authority | 環境權限 | 瀏覽器自動替請求附上 cookie 等憑證，使任何頁面發出的請求都可能帶著使用者的身分；SOP、CORS 與 CSRF 防禦都從這裡出發。 | 第 23 章 |
| Clickjacking | 點擊劫持 | 外站用透明 iframe 疊住目標頁，誘導使用者點到底下的按鈕；以 CSP `frame-ancestors` 防禦。 | 第 23 章 |
| cookie | — | server 以 `Set-Cookie` 交給瀏覽器、之後自動附在符合範圍的請求上的小資料；server 收到時看不到屬性。 | 第 21 章 |
| cookie prefix | cookie 前綴 | `__Secure-` 與 `__Host-` 開頭的名稱，瀏覽器保證對應屬性；`__Host-` 必須 Secure、Path=/、不設 Domain，因此是只送回原 host 的 host-only cookie。 | 第 21 章 → 第 23 章 |
| CORS（Cross-Origin Resource Sharing） | 跨來源資源共用 | server 以 `Access-Control-Allow-*` header 允許指定 origin 的 JavaScript 讀取回應；只會放寬 SOP，不是 server 的存取控制，也不是 CSRF 防禦。 | 第 1 章 → 第 23 章 |
| credentialed request | 帶憑證的請求 | 附帶 cookie 或 HTTP 驗證的跨源請求；回應必須寫明確的 origin 而非 `*`，並有 `Access-Control-Allow-Credentials: true`。 | 第 23 章 |
| CSP（Content Security Policy） | 內容安全政策 | 以 header 宣告頁面可以載入與執行哪些來源的腳本、可被誰嵌入；是 XSS 的第二道防線。 | 第 23 章 |
| CSRF（Cross-Site Request Forgery） | 跨站請求偽造 | 外站利用瀏覽器自動帶 cookie，讓使用者在不知情時送出改變狀態的請求；以 SameSite、CSRF token 與 Fetch Metadata 防禦。 | 第 23 章 |
| double-submit cookie | 雙重提交 cookie | 同一個 token 同時放在 cookie 與請求 header／表單中，server 比對兩者；signed 版本用 HMAC 綁定 session。 | 第 23 章 |
| Fetch Metadata | — | 瀏覽器附在請求上的 `Sec-Fetch-Site`、`Sec-Fetch-Mode`、`Sec-Fetch-Dest` header，讓 server 知道請求來源與用途。 | 第 23 章 |
| HttpOnly | — | cookie 屬性，禁止 JavaScript 讀取，降低 XSS 偷走 session 的風險。 | 第 23 章 |
| Login CSRF | 登入 CSRF | 讓受害者登入攻擊者的帳號，之後輸入的資料都進了攻擊者帳號；登入表單也要有 CSRF 保護並輪替 session ID。 | 第 23 章 |
| nonce-based strict CSP | — | `script-src` 只允許帶本次回應隨機 nonce 的腳本，搭配 `'strict-dynamic'` 讓它們載入的腳本也被信任。 | 第 23 章 |
| origin | 來源 | scheme、host、port 三者的組合；三者完全相同才是 same-origin。 | 第 1 章 → 第 23 章 |
| preflight | 預檢請求 | 非簡單的跨源請求前，瀏覽器先送 `OPTIONS` 詢問允許的 method 與 header；preflight 本身不帶 cookie。 | 第 23 章 |
| registrable domain（eTLD+1） | 可註冊網域 | public suffix 再往左多一段的網域，例如 `shengsheng.example`；site 由 scheme 加上它組成。 | 第 23 章 |
| Same-origin policy（SOP） | 同源政策 | 瀏覽器禁止一個 origin 的腳本讀取另一個 origin 的回應；送出請求與嵌入資源則多半不受限。 | 第 23 章 |
| SameSite | — | cookie 屬性：`Strict` 只在同站請求送出、`Lax` 另允許跨站的頂層 GET 導覽、`None` 都送但必須 Secure；每個 cookie 都應明確寫出。 | 第 23 章 |
| Secure | — | cookie 屬性，只在 HTTPS 請求送出，也不能被 http 頁面覆寫。 | 第 23 章 |
| simple request | 簡單請求 | 只用 GET／HEAD／POST 與少數允許的 header 和 Content-Type 的跨源請求，瀏覽器直接送出再檢查回應，不先 preflight。 | 第 23 章 |
| site | 站點 | scheme 加 registrable domain；`www` 與 `api.shengsheng.example` 是跨 origin、但同 site，所以 CORS 要管、SameSite 不擋。 | 第 23 章 |
| XSS（Cross-Site Scripting） | 跨站腳本 | 不受信任的資料被瀏覽器當成 HTML、JavaScript 或 URL 解讀並執行；主要防禦是依情境輸出編碼，CSP 為第二道防線。 | 第 23 章 |

## A.9 驗證與授權

密碼、session、JWT、OAuth、OIDC、passkeys 與服務之間的身分（第 26–30 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| access token | 存取權杖 | 代表一次授權、讓 client 呼叫 API 的憑證，可以是 opaque 或 JWT；聲聲 Live 自家 API 的 JWT 有效 5 分鐘。 | 第 28 章 |
| algorithm confusion | 演算法混淆 | 驗證端依 token header 的 `alg` 決定怎麼驗，被誘導把 RSA 公鑰當成 HMAC secret；防法是由驗證端固定允許的演算法並把 kid 綁定演算法。 | 第 27 章 |
| API key | API 金鑰 | server 發給 client 的長期隨機字串，語意是 bearer；DB 只存雜湊、帶前綴與 checksum 方便掃描，權限遵守最小權限。 | 第 30 章 |
| Authentication | 驗證 | 確認「你是誰」；session 是這次驗證事件的記憶。 | 第 26 章 |
| Authorization | 授權 | 決定「你能做什麼」；403 是授權失敗，401 是缺少或無效的驗證。 | 第 26 章 → 第 28 章 |
| authorization code | 授權碼 | OAuth 中 AS 透過 front channel 交給 client 的一次性短效代碼，client 再經 back channel 換 token；聲聲 Live 設定 60 秒、一次性。 | 第 28 章 |
| authorization server（AS） | 授權伺服器 | 驗證使用者、取得同意並簽發 token 的服務。 | 第 28 章 |
| back channel／front channel | 後端通道／前端通道 | front channel 經瀏覽器 redirect 傳遞、容易外洩，只放用完即作廢的東西；back channel 是 client 直連 AS 的 HTTPS，值錢的 token 走這裡。 | 第 28 章 |
| bearer token | 持有者權杖 | 誰拿到就能用的 token，不需證明身分；因此不能放在 URL，傳輸必須加密。 | 第 27 章 → 第 28 章 |
| BFF（Backend for Frontend） | 前端專屬後端 | 由 server 端替 SPA 保存 token、瀏覽器只持有 session cookie 的架構；聲聲 Live 的 Web 前端與老師後台採用。 | 第 24 章 → 第 28 章 |
| claims | 聲明 | JWT payload 中的欄位；註冊 claims 有 iss、sub、aud、exp、nbf、iat、jti。 | 第 27 章 |
| client credentials | 用戶端憑證授權 | 沒有使用者參與、client 以自己的身分取得 token 的 grant；聲聲 Live 的 `reco` 以此取得 `lessons:read`。 | 第 28 章 |
| confidential client／public client | 機密／公開用戶端 | 能安全保存 client secret 的 server 端程式，對照無法保存秘密的 SPA 與原生 App；後者必須用 PKCE。 | 第 28 章 |
| credential stuffing | 撞庫 | 拿其他網站外洩的帳密清單逐一嘗試登入；密碼本身是對的，防禦靠限速、外洩密碼檢查與 MFA。 | 第 26 章 |
| DPoP（Demonstrating Proof of Possession） | 持有證明 | client 以裝置上的私鑰對每個請求簽一個 DPoP proof，token 綁定該公鑰，偷走 token 也無法使用。 | 第 28 章 |
| ES256／RS256／HS256 | — | JWT 的簽章演算法：ECDSA P-256、RSA 與 HMAC-SHA256；HS256 能驗證的人就能簽發，對外發布的 token 用非對稱演算法。 | 第 27 章 |
| HMAC request signing | HMAC 請求簽章 | client 以共享 secret 對標準化的請求內容（method、路徑、header、timestamp、nonce）算 HMAC 放進 header，server 重算比對並限制時間窗。 | 第 30 章 |
| HOTP／TOTP | — | 以 HMAC 與計數器（HOTP）或 30 秒時間步（TOTP）算出 6 位數一次性密碼；server 必須能取回金鑰原值，驗證要限速並防重放。 | 第 1 章 → 第 26 章 |
| IdP（Identity Provider） | 身分提供者 | 負責驗證使用者並簽發身分證明的系統（OIDC 稱 OpenID Provider）；依賴它的應用稱為 Relying Party（RP）。 | 第 29 章 |
| ID token | 身分權杖 | OIDC 中 IdP 簽發給 client 的 JWT，說明「是誰、給誰」；client 必須驗 iss、aud、exp、nonce 與簽章，不能拿去呼叫 API。 | 第 29 章 |
| JWKS（JSON Web Key Set） | — | 發行者公開的一組 JWK 公鑰，驗證端依 token header 的 `kid` 挑選；輪替時新舊金鑰並存。 | 第 27 章 |
| JWT（JSON Web Token） | — | header.payload.signature 三段 base64url 組成的 self-contained token；本身不加密（JWE 才加密），驗證必須固定 alg、驗簽章、exp／nbf、iss 與 aud。 | 第 1 章 → 第 27 章 |
| MFA（Multi-Factor Authentication） | 多因子驗證 | 結合兩種以上不同類型的因子（知道的、擁有的、本身的）驗證身分。 | 第 26 章 |
| OAuth 2.0 | — | 委派授權框架（RFC 6749）：資源擁有者同意後，由 authorization server 發 token 給第三方 client 呼叫 resource server，不必交出密碼；它不是登入協定。 | 第 28 章 |
| OAuth 2.1 | — | 整合十年最佳實務的 OAuth 修訂：code 流程必須 PKCE，移除 implicit 與 resource owner password credentials；截至 2026 年 10 月仍是草案。 | 第 28 章 |
| opaque token | 不透明權杖 | 本身不帶資訊的隨機字串，server 要查表或呼叫 introspection endpoint 才知道代表什麼；撤銷即時。 | 第 27 章 |
| OpenID Connect（OIDC） | — | 建在 OAuth 2.0 上的身分層，增加 ID token、UserInfo endpoint 與 Discovery，用於登入與 SSO。 | 第 29 章 |
| open redirect | 開放重新導向 | 網站把使用者導向參數指定的任意網址；在 OAuth 中會讓授權碼外洩，redirect URI 必須精確字串比對。 | 第 28 章 |
| passkey | 通行密鑰 | 可用於 WebAuthn、通常能跨裝置同步的 credential；server 只存公鑰，簽章綁定 origin，在假網站取得的簽章對真網站無效，因此抗釣魚。 | 第 29 章 |
| pepper | 胡椒值 | 全站共用、不存在資料庫裡的秘密，先以 HMAC 和密碼混合再雜湊；只偷到資料庫的攻擊者無法嘗試。 | 第 26 章 |
| PKCE（Proof Key for Code Exchange） | — | client 先送 `code_challenge`（`code_verifier` 的 SHA-256），換 token 時出示 verifier，讓被攔截的授權碼無法使用。 | 第 28 章 |
| refresh token | 更新權杖 | 用來換新 access token 的長效憑證；聲聲 Live 為 14 天、opaque、雜湊儲存、每次使用即輪替並做重用偵測。 | 第 27 章 |
| salt | 鹽 | 每個密碼各自獨立的隨機值，明文存在雜湊旁邊，讓相同密碼產生不同雜湊、預先算好的彩虹表失效。 | 第 26 章 |
| SAML 2.0 | — | 以簽章 XML 斷言傳遞身分的企業 SSO 標準；容易出現 XML signature wrapping，不要自己解析。 | 第 29 章 |
| scope | 權限範圍 | client 要求、AS 記在 token 上的權限清單；聲聲 Live 對外開放 `vocab:read`、`vocab:write`、`schedule:read`、`profile:read`。 | 第 28 章 |
| session fixation | session 固定攻擊 | 攻擊者讓受害者帶著已知的 session ID 登入；登入成功時一律產生新 ID 並讓舊的失效。 | 第 26 章 |
| session ID | — | server-side session 中交給瀏覽器的隨機識別，本身沒有意義，資料存在 server。 | 第 26 章 |
| SPIFFE／SVID | — | 服務身分的標準：SPIFFE ID 形如 `spiffe://shengsheng.example/ns/live/sa/api`，以短效 X.509-SVID 或 JWT-SVID 呈現並自動輪替。 | 第 30 章 |
| SSO（Single Sign-On） | 單一登入 | 在 IdP 登入一次即可進入多個 RP；每個 RP 仍有自己的 session，登出要另外設計。 | 第 29 章 |
| state | 狀態參數 | OAuth client 產生、綁定瀏覽器 session 的隨機值，回呼時比對以防 CSRF 與注入授權回應。 | 第 28 章 |
| token bucket | 權杖桶 | 容量決定可容忍的爆量、補充速率決定長期上限的限速演算法；聲聲 Live 以 (帳號, IP)、IP、帳號三個維度限速。 | 第 26 章 |
| WebAuthn | — | W3C 的公鑰驗證規格：註冊時裝置為網站產生金鑰對，登入時對 challenge 簽章，瀏覽器把 origin 寫進 clientDataJSON；credential 綁定 RP ID（聲聲 Live 為 `shengsheng.example`）。 | 第 29 章 |
| workload identity | 工作負載身分 | 由平台依可驗證的執行環境發給服務短效身分文件，程式不持有長期秘密。 | 第 30 章 |
| zero trust | 零信任 | 網路位置不代表身分，每一次呼叫都要驗證是誰、能做什麼。 | 第 30 章 |

## A.10 即時通訊

server 主動推送的各種做法、WebSocket 的細節，以及多台 gateway 的即時系統設計（第 31–33 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| at-most-once／at-least-once | 最多一次／至少一次 | 投遞語意：前者可能遺失但不重複（Redis Pub/Sub），後者可能重複但不遺失，需搭配冪等處理與去重。 | 第 33 章 |
| backpressure | 背壓 | 接收端跟不上時讓送出端放慢或停下的機制；廣播時要替每條連線設上限，不能讓慢 client 拖住所有人。 | 第 32 章 |
| broker | 訊息中介 | 把訊息送到所有有該房間成員的 gateway 的元件；聲聲 Live 用 Redis（primary 10.20.17.21）。 | 第 33 章 |
| close code | 關閉代碼 | WebSocket close frame 中的 2 bytes 原因碼：1000 正常、1009 訊息太大、1006 表示沒收到 close frame 就斷（保留值，不會出現在線路上）、4000–4999 由應用自訂（聲聲 Live 用 4001 授權到期、4008 client 太慢）。 | 第 32 章 |
| connection draining | 連線排空 | 部署或縮容時先讓健康檢查失敗、停止新連線，再有計畫地請既有連線分批離開，而不是讓它們全部變成 RST。 | 第 33 章 |
| CSWSH（Cross-Site WebSocket Hijacking） | 跨站 WebSocket 劫持 | WebSocket 握手不受 CORS 保護、會帶 cookie，外站可開連線冒用使用者；以 Origin 允許清單與一次性 ticket 防禦。 | 第 32 章 |
| EventSource | — | 瀏覽器的 SSE API，自動重連並在重連時帶 `Last-Event-ID`；不能自訂 header。 | 第 31 章 |
| fan-out | 扇出 | 一則訊息要複製成幾份送出；投遞量＝發言速率 × 房間人數，大房間的成本是平方級。 | 第 33 章 |
| full jitter | 完全抖動 | 重試等待時間在 0 到退避上限之間完全隨機，讓同時斷線的大量 client 被均勻打散。 | 第 33 章 |
| gateway（即時服務） | 即時閘道 | 只負責維持連線、收發 frame、盡量不存業務狀態的節點；聲聲 Live 擴充後為 gw-41–46 六台。和雲端的 NAT gateway、Internet gateway（A.13）不是同一種東西。 | 第 33 章 |
| heartbeat | 心跳 | 定期在連線上送少量資料（SSE 註解、WebSocket ping），讓中間設備的閒置計時器重設並偵測死掉的對端；間隔要短於路徑上最短的閒置逾時。 | 第 31 章 |
| Last-Event-ID | — | SSE 重連時瀏覽器自動帶的 header，server 依它從事件紀錄補發之後的事件；補不回來時送 reset。 | 第 31 章 |
| long polling | 長輪詢 | server 收到請求後先不回應，等到有事件或逾時才回，client 再立刻發下一個；早期稱 Comet。 | 第 31 章 |
| masking | 遮罩 | client 送往 server 的每個 WebSocket frame 都以隨機 4 bytes masking key 做 XOR，讓惡意頁面無法精確控制線路上的 bytes、誘導不懂 WebSocket 的透明 proxy 快取偽造回應；不是加密，server 送出的 frame 不能 mask。 | 第 32 章 |
| ping／pong | — | WebSocket 的控制 frame，收到 ping 必須回 pong；瀏覽器 JavaScript 沒有 API 主動送 ping，只能由 server 發。 | 第 32 章 |
| presence | 在線狀態 | 誰在線上的資訊；大房間只送聚合人數，並以 TTL 讓斷線者自動消失（聲聲 Live 為 60 秒）。 | 第 33 章 |
| pub/sub | 發布／訂閱 | 發布者把訊息送到 topic、broker 轉給所有訂閱者，發布者不必知道有誰在聽；聲聲 Live 的 topic 為 `room:<id>`。 | 第 33 章 |
| sequencer | 序號產生器 | 為同一房間的每則訊息配發遞增序號（聲聲 Live 用 Redis `INCR`），讓 client 依序號排序、偵測缺口與補發。 | 第 33 章 |
| short polling | 短輪詢 | client 每隔固定時間發請求問有沒有新事件，延遲與請求數都由間隔決定。 | 第 31 章 |
| SSE（Server-Sent Events） | 伺服器傳送事件 | 以一個永不結束的 `text/event-stream` HTTP 回應單向推送事件，內建重連與 `Last-Event-ID`；每條 SSE 佔一條連線。 | 第 31 章 |
| subprotocol | 子協定 | WebSocket 握手時以 `Sec-WebSocket-Protocol` 協商的應用層協定與版本，例如 `ss-chat.v1`。 | 第 32 章 |
| thundering herd | 驚群 | 一大群等待者被同一事件同時喚醒或同時重連，瞬間壓垮後端；以隨機抖動與排空打散。 | 第 31 章 |
| WebSocket | — | 以 HTTP Upgrade 握手（server 回 101 Switching Protocols）、之後在同一條 TCP 連線上雙向傳送 frame 的協定（RFC 6455）；`Sec-WebSocket-Accept` = base64(SHA-1(key＋固定 GUID))。 | 第 1 章 → 第 32 章 |
| WebTransport | — | 在 HTTP/3 session 中同時提供多條可靠 stream 與不可靠 datagram 的新 API 與協定。 | 第 13 章 → 第 32 章 |
| X-Accel-Buffering | — | 回應 header `X-Accel-Buffering: no` 讓 nginx 不緩衝這個回應，SSE 與串流回應才能一段段即時送出。 | 第 31 章 |

## A.11 即時影音

媒體的編碼與 RTP、SDP 與 ICE、SFU 規模化、直播協定與品質指標（第 34–39 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| ABR ladder（adaptive bitrate ladder） | ABR 階梯 | 把一路來源轉成多個解析度與 bitrate 的版本，播放器依頻寬自動切換；聲聲 Live 直播為 1080p 4.5 Mbps 到 360p 0.7 Mbps。 | 第 38 章 |
| bandwidth estimation | 頻寬估計 | WebRTC 送端依延遲變化與丟包估計可用頻寬並調整編碼 bitrate，例如 GCC 搭配 TWCC 回饋。 | 第 37 章 |
| BUNDLE | — | SDP 的 `a=group:BUNDLE`，讓音訊、視訊與 data channel 共用同一條 ICE／DTLS 傳輸與同一個 5-tuple。 | 第 35 章 |
| candidate | 候選位址 | ICE 中一個可能可用的位址與 port：host（本機）、srflx（NAT 外的位址）、relay（TURN 配的位址）、prflx（檢查時才發現）；本地與遠端各取一個組成 candidate pair。 | 第 36 章 |
| codec | 編解碼器 | 壓縮與解壓縮媒體的演算法，例如 Opus、H.264、AV1；和裝載它的 container 是兩回事。 | 第 34 章 |
| connectivity check | 連通檢查 | ICE 以 STUN Binding 請求逐對測試 candidate pair，成功的成為 valid pair。 | 第 36 章 |
| consent freshness | 同意新鮮度 | 連線建立後 ICE 持續送 STUN 檢查確認對方仍同意接收，30 秒沒有回應就必須停止送媒體。 | 第 36 章 |
| data channel | 資料通道 | WebRTC 上以 SCTP over DTLS 傳送任意資料的通道，可設定有序與部分可靠。 | 第 36 章 |
| DTLS | 資料包 TLS | 能在會遺失、亂序的 datagram 上運作的 TLS；WebRTC 用它交握並驗證 SDP 中的憑證指紋。 | 第 35 章 → 第 36 章 |
| DTLS-SRTP | — | 以 DTLS 交握匯出 SRTP 金鑰的機制；WebRTC 媒體一律加密，安全性等於 signaling 的安全性。 | 第 36 章 |
| FEC（Forward Error Correction） | 前向錯誤更正 | 多送冗餘資料讓收方不必重傳就能補回遺失；格式有 ULPFEC、FlexFEC，音訊用 Opus in-band FEC。 | 第 34 章 → 第 37 章 |
| frame（媒體） | 影格／音框 | 一張畫面（video frame）或一段固定長度的音訊樣本（audio frame，Opus 常用 20 ms）。 | 第 34 章 |
| glass-to-glass latency | 端到端延遲 | 從攝影機鏡頭到觀眾螢幕的總延遲，包含擷取、編碼、網路、jitter buffer、解碼與顯示。 | 第 34 章 |
| GOP（Group of Pictures） | 畫面群組 | 從一個 keyframe 到下一個 keyframe 之間的 frame；聲聲 Live 直播 GOP 為 1 秒。 | 第 34 章 |
| HLS（HTTP Live Streaming） | — | 把影音切成 segment、以 playlist 描述、透過一般 HTTP 與 CDN 分發的串流協定；傳統設定下延遲可達二十秒以上。 | 第 38 章 |
| ICE（Interactive Connectivity Establishment） | 互動式連線建立 | 收集 candidate、交換、逐對檢查並提名最佳路徑的 NAT 穿越框架。 | 第 35 章 → 第 36 章 |
| ICE-lite | — | 只有 host candidate、只回應檢查不主動探測的簡化 ICE 實作，適合有公網位址的 SFU；對方的完整實作必定擔任負責提名的 controlling 端。聲聲 Live 的 SFU 採用。 | 第 35 章 → 第 36 章 |
| ingest | 推流入口 | 平台接收推流的端點，要扛住不穩的網路並驗證推流權限；聲聲 Live 為 `live.shengsheng.example`（SRT UDP 9000）。 | 第 38 章 |
| I／P／B frame | — | I frame 可獨立解碼（keyframe）；P frame 參考前面的畫面；B frame 參考前後畫面，會增加延遲。 | 第 34 章 |
| jitter buffer | 抖動緩衝 | 收端暫存封包、依 timestamp 排定播放時刻以吸收延遲變動；多等延遲增加，少等晚到等於遺失。 | 第 34 章 |
| keyframe | 關鍵影格 | 不參考其他畫面、可單獨解碼的 frame；最大最貴，收端遺失時以 PLI 或 FIR 要求。 | 第 34 章 → 第 37 章 |
| LL-HLS（Low-Latency HLS） | 低延遲 HLS | 以 partial segment、preload hint、blocking playlist reload 與 delta update 把 HLS 延遲降到數秒；聲聲 Live part 為 0.5 秒。 | 第 38 章 |
| MCU（Multipoint Control Unit） | 多點控制單元 | 把所有人的影像解碼、合成、重新編碼成一路送給每個人的伺服器，CPU 成本高。 | 第 37 章 |
| mesh | 網狀架構 | 每位參與者直接和其他每個人建立 P2P 連線，上行頻寬隨人數線性成長。 | 第 37 章 |
| MOS（Mean Opinion Score） | 平均意見分數 | 受測者對通話品質打 1–5 分的平均（ITU-T P.800）；實務上由 E-model 等客觀模型從延遲與丟包估算。 | 第 39 章 |
| NACK | 否定確認 | RTCP 回饋訊息，請送端重送特定序號的 RTP 封包；重送以另一個 payload type 與 SSRC 的 RTX 格式送出。 | 第 34 章 → 第 37 章 |
| offer／answer | 提議／回答 | 一方送出 SDP offer 列出想要的媒體與格式，另一方回 answer 選定交集；聲聲 Live 一律由學生端 offer、SFU 只當 answerer。 | 第 35 章 |
| Opus | — | WebRTC 的主要音訊 codec，低延遲，內建 PLC 與 in-band FEC；聲聲 Live 範例中 PT 為 111。 | 第 34 章 |
| payload type（PT） | 酬載類型 | RTP header 中 7 bit 的格式編號；動態 PT（96–127）只在該份 SDP 中有意義，寫死會出事。 | 第 35 章 |
| PLC（Packet Loss Concealment） | 封包遺失隱藏 | 封包遺失時用前後的聲音推估出一段補上。 | 第 34 章 |
| PLI（Picture Loss Indication） | 畫面遺失指示 | RTCP 回饋，請送端立刻產生 keyframe；大房間要防止 PLI storm。 | 第 34 章 → 第 37 章 |
| RTCP | RTP 控制協定 | 和 RTP 搭配的控制訊息：SR／RR 回報丟包、jitter 與 RTT 所需的時間戳記，以及 NACK、PLI 等回饋；rtcp-mux 讓它與 RTP 共用 port。 | 第 34 章 |
| RTMP／RTMPS | — | 基於 TCP 的傳統推流協定，以 stream key 驗證；RTMPS 是加上 TLS 的版本，聲聲 Live 作為 SRT 的備援。 | 第 38 章 |
| RTP（Real-time Transport Protocol） | 即時傳輸協定 | 在 UDP 上搬運媒體的協定，header 帶 payload type、序號、timestamp 與 SSRC；本身不加密。 | 第 34 章 |
| SDP（Session Description Protocol） | 會話描述協定 | 描述媒體、codec、傳輸位址、ICE 帳密與 DTLS 指紋的文字格式；WebRTC 以 offer／answer 交換它。 | 第 1 章 → 第 35 章 |
| SDP munging | SDP 改寫 | 在 setLocalDescription 前手動修改 SDP 字串；依賴不穩定的細節，容易在瀏覽器更新後壞掉。 | 第 35 章 |
| SFU（Selective Forwarding Unit） | 選擇性轉送單元 | 接收每位參與者的串流、不重新編碼，依需要轉送給其他人的媒體伺服器；聲聲 Live 一對一與小班課都走 SFU。 | 第 35 章 → 第 37 章 |
| signaling | 信令 | 交換 SDP 與 candidate 的管道；不在 WebRTC 規格內，聲聲 Live 用 WebSocket。 | 第 7 章 → 第 36 章 |
| Simulcast | 同步多路廣播 | 送端同時編出數個獨立的解析度版本（以 RID 區分），SFU 為每個收端挑一層；聲聲 Live 為 720p、360p、180p 三層。 | 第 37 章 |
| SRT（Secure Reliable Transport） | — | 基於 UDP、以 ARQ 加 TSBPD 在固定延遲內可靠傳送的推流協定；libsrt 的 `SRTO_LATENCY` 單位是毫秒（預設 120 ms），ffmpeg 的 `latency` 參數單位是微秒。 | 第 1 章 → 第 38 章 |
| SRTP | 安全 RTP | 加密與驗證 RTP payload 的 profile；header 仍可被中間設備看到。 | 第 34 章 → 第 36 章 |
| SSRC | 同步來源識別碼 | RTP header 中 32 bit 的串流識別，一條串流一個值。 | 第 34 章 |
| STUN | — | 讓 client 得知自己在 NAT 外的位址（Binding）並用於 ICE 連通檢查的協定；訊息含固定的 Magic Cookie `0x2112A442`。 | 第 36 章 |
| trickle ICE | 漸進式 ICE | candidate 一收集到就透過 signaling 送出，收集與檢查同時進行，縮短連線時間。 | 第 35 章 → 第 36 章 |
| TSBPD（Timestamp-Based Packet Delivery） | 依時間戳記交付 | SRT 收方把每個封包固定延遲 latency 後才交付，讓輸出節奏和輸入一致；到期仍沒到的封包 too-late drop。 | 第 38 章 |
| TURN | — | 在無法直連時，由公網 relay 伺服器代轉媒體的協定；聲聲 Live 的 TURN 在 203.0.113.50，提供 UDP／TCP 3478 與 TLS 443。 | 第 1 章 → 第 36 章 |
| WebRTC | — | 瀏覽器內建的即時影音與資料通道技術，由 ICE、DTLS-SRTP、RTP／RTCP、SCTP 與 SDP offer／answer 組成。 | 第 1 章 → 第 36 章 |
| WHIP／WHEP | — | 以單一 HTTP POST 交換 SDP 的 WebRTC 推流（WHIP）與觀看（WHEP）signaling 標準。 | 第 38 章 |

## A.12 Python Web 堆疊

從 socket 寫起的 server 模型、WSGI 與 Werkzeug、ASGI 與 async，以及 gunicorn 部署（第 40–43 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| 499 | — | nginx 自訂的狀態碼，表示 client 在回應前先關閉連線；大量出現常代表外層的逾時比內層短。 | 第 43 章 |
| application server | 應用伺服器 | 執行 Python 應用、管理 worker 的伺服器，例如 gunicorn 與 uvicorn；前面通常再放 nginx 這類 reverse proxy。 | 第 43 章 |
| arbiter | 仲裁者 | gunicorn 的主 process，不處理請求，只維持 worker 數量、以心跳檔監控 worker、處理訊號。 | 第 43 章 |
| ASGI | — | Python 非同步伺服器與應用之間的介面：`async def app(scope, receive, send)`，以事件表達 HTTP、WebSocket 與 lifespan。 | 第 42 章 |
| cooperative multitasking | 合作式多工 | task 只在 `await` 時自願交出控制權；任何一段同步阻塞呼叫都會讓整個 loop 停住。 | 第 42 章 |
| debugger（Werkzeug） | 互動式除錯器 | 出錯時在瀏覽器提供可執行任意 Python 的 console，以 PIN 保護；只能在開發者自己的電腦上、只聽 127.0.0.1，絕不能在 production 開啟。 | 第 41 章 |
| edge-triggered／level-triggered | 邊緣觸發／水平觸發 | 事件通知的兩種語意：level 只要還有資料就一直回報（`selectors` 的預設），edge 只在狀態改變時回報一次、必須讀到 `EAGAIN`。 | 第 40 章 |
| environ | — | WSGI 傳給應用的 dict，含 CGI 風格的請求變數（`REQUEST_METHOD`、`PATH_INFO`、`HTTP_*`）與 `wsgi.*` 鍵。 | 第 41 章 |
| event loop | 事件迴圈 | 單一 thread 以非阻塞 I/O 等待多個 socket 的就緒事件、只對準備好的連線動作的迴圈；Python 標準函式庫的實作是 asyncio。 | 第 40 章 |
| Flask | — | 建在 Werkzeug 之上的 WSGI 框架；`request` 等全域物件是 context-local proxy。 | 第 1 章 → 第 41 章 |
| free-threaded Python | 無 GIL 建置 | 移除 GIL 的 CPython 建置（PEP 703）；3.13 起實驗推出、3.14 起官方支援，但截至 2026 年 10 月仍不是預設。 | 第 40 章 |
| GIL（Global Interpreter Lock） | 全域直譯器鎖 | 同一時刻只有一條 thread 執行 Python bytecode；thread 只在等 I/O 時真正平行。 | 第 40 章 |
| graceful shutdown | 優雅關機 | 先讓 readiness 失敗、等 LB 停送新請求（drain），再停止接受連線，最後等進行中的請求做完；聲聲 Live 的 `graceful_timeout` 25 秒、`TimeoutStopSec` 40 秒。 | 第 43 章 |
| gthread | — | gunicorn 在每個 process 內開 thread pool 的 worker class，支援 keep-alive；聲聲 Live API 為 8 workers × 7 threads。 | 第 43 章 |
| gunicorn | — | pre-fork 模型的 Python application server；傳統上以 WSGI 為主，新版也支援 ASGI。 | 第 1 章 → 第 43 章 |
| lifespan | — | ASGI 的生命週期 scope，app 在 `lifespan.startup` 完成初始化後 server 才開始接受連線。 | 第 42 章 |
| lingering close | 延遲關閉 | server 送完錯誤回應後先關閉寫入方向並讀掉剩餘資料再關閉，避免 client 因 RST 收不到回應。 | 第 40 章 |
| Little's law | Little 定律 | 系統內平均同時處理的請求數＝每秒到達數 × 每個請求停留時間；用來估算需要多少 worker。 | 第 42 章 |
| liveness／readiness | 存活檢查／就緒檢查 | liveness 回答「需不需要被重啟」，readiness 回答「現在願不願意接新請求」；兩者要分開，否則 drain 期間會被誤殺。 | 第 43 章 |
| loop lag | 事件迴圈延遲 | 背景 task 量測實際醒來比預期晚多少；被阻塞時跳到阻塞的長度，是 async 服務的關鍵監控指標。 | 第 42 章 |
| middleware | 中介層 | 同時是 server 端也是應用端的元件，包住內層 app 處理請求與回應，形成洋蔥模型。 | 第 41 章 |
| pre-fork | 預先分叉 | 主 process 先 listen 再 fork 出固定數量的 worker，所有 worker 從同一個 accept queue 取連線。 | 第 40 章 |
| ProxyFix | — | Werkzeug middleware，依設定的可信 proxy 層數從右邊取 `X-Forwarded-*` 改寫 environ；聲聲 Live 用 `ProxyFix(x_for=1, x_proto=1)`。 | 第 41 章 → 第 43 章 |
| slowloris | 慢速攻擊 | 以極慢的速度送 header，讓「每次讀取的逾時」不斷歸零而長期佔住資源；防法是整體期限與前置 proxy 緩衝。 | 第 40 章 |
| sync worker | 同步 worker | gunicorn 預設的 worker class，一個 process 一次只處理一個請求、不支援 keep-alive，必須放在會緩衝的 proxy 後面。 | 第 40 章 → 第 43 章 |
| timeout chain | 逾時鏈 | 請求路徑上每一層計時器合起來的行為；外層必須比內層長，聲聲 Live 修正後由瀏覽器 90 秒一路遞減到 PostgreSQL 5 秒。 | 第 43 章 |
| uvicorn | — | ASGI server，可選 h11 或 httptools 解析 HTTP、asyncio 或 uvloop 做 event loop。 | 第 42 章 |
| Werkzeug | — | WSGI 工具庫：Request／Response、routing（Map、Rule、converter）、開發伺服器、reloader 與 debugger；Flask 建在它上面。 | 第 1 章 → 第 41 章 |
| worker class | — | gunicorn 處理請求的模型（sync、gthread、uvicorn 等），決定並行方式與 keep-alive 行為。 | 第 43 章 |
| WSGI | — | Python 同步 Web 伺服器與應用之間的標準介面（PEP 3333）：應用是 `app(environ, start_response)`、回傳 bytes 的 iterable；解決框架與 server 的 N×M 問題。 | 第 1 章 → 第 41 章 |
| X-Accel-Redirect | — | 應用回應這個 header，讓 nginx 直接從 internal location 送出檔案；聲聲 Live 用於錄影檔。 | 第 43 章 |

## A.13 雲端、容器與營運

VPC、Kubernetes 網路、除錯方法與效能設計的詞彙（第 44–46 章）。

| 英文術語 | 中文 | 一句話定義 | 首次出現 → 主要深入 |
|---|---|---|---|
| AZ（Availability Zone） | 可用區 | 同一區域內電力、冷卻與網路彼此獨立的機房群，彼此延遲通常在一兩毫秒內；一個 subnet 只能屬於一個 AZ。 | 第 5 章 → 第 44 章 |
| bisection | 分半法 | 在可疑路徑的中點找觀察點（例如 `curl --resolve` 繞過 CDN），判斷問題在上游或下游，每次把範圍砍半。 | 第 45 章 |
| CNI（Container Network Interface） | 容器網路介面 | 容器執行環境與網路外掛之間的規格；Pod 的網路在應用容器啟動前就由 CNI 設定好，NetworkPolicy 也由它執行。 | 第 44 章 |
| critical path | 關鍵路徑 | 一串彼此依賴、必須依序完成的步驟中最長的那一條；只有縮短它，總時間才會變短。 | 第 46 章 |
| game day | 故障演練 | 在 staging 刻意重現過去的事故，讓值班者只拿到使用者的原話、自己走到根因的演練。 | 第 45 章 |
| Gateway API | — | Kubernetes 下一代入口 API，依角色拆成 GatewayClass、Gateway、HTTPRoute、GRPCRoute 與 ReferenceGrant。 | 第 44 章 |
| Ingress／ingress controller | — | Ingress 是描述 host 與路徑轉給哪個 Service 的物件，必須由 ingress controller（實際的 proxy）讀取才會生效。 | 第 44 章 |
| Internet gateway（IGW） | 網際網路閘道 | VPC 與網際網路之間的出入口，替有公網 IP 的網路介面做一對一 NAT（例如 10.20.16.5 ↔ 203.0.113.80）。 | 第 44 章 |
| kube-proxy | — | 每個節點上監看 Service 與 EndpointSlice、把 ClusterIP 的新連線 DNAT 到某個 Pod 的元件；DNAT 發生在來源 Pod 所在的節點。 | 第 44 章 |
| Kubernetes Service／ClusterIP | — | 以 label selector 選出一組 Pod、提供穩定名稱與虛擬 IP；ClusterIP 不存在於任何網路介面上，ping 不通但能連。 | 第 44 章 |
| latency budget | 延遲預算 | 把一個總延遲目標分配給每一段（DNS、連線、處理、下載、渲染），任何一段超支就要從別處省回來；「找老師」頁的目標是美東學生 p75 在 2.5 秒內看到完整清單。 | 第 46 章 |
| NAT gateway | NAT 閘道 | 雲端代管的 SNAT 設備，放在 public 子網並綁 Elastic IP，讓 private 子網能主動對外連線；對方看到的是 NAT gateway 的位址。 | 第 44 章 |
| network ACL（NACL） | 網路存取控制清單 | 掛在子網上、stateless、依編號由小到大比對且第一條符合即決定的規則；回程的 ephemeral port 必須自己開。 | 第 44 章 |
| network namespace | 網路命名空間 | 核心中互相隔離的網路堆疊，各有自己的介面、路由表與 port 空間；每個容器（Pod）各有一個。 | 第 44 章 |
| NetworkPolicy | — | Kubernetes 以 label 描述 Pod 之間誰可以連誰的 API；被選中後該方向預設拒絕，CNI 不支援時建立了也不生效。 | 第 44 章 |
| NodePort／LoadBalancer | — | NodePort 在每個節點開同一個 port（預設 30000–32767）並 DNAT 到 Pod；LoadBalancer 在其上由雲端建立負載平衡器。 | 第 44 章 |
| overlay network | 覆蓋網路 | 在既有網路（underlay）上用隧道再建一層虛擬網路；封裝開銷讓 Pod MTU 變小（聲聲 Live 為 1450）。 | 第 44 章 |
| PrivateLink | — | 不打通兩個 VPC 的網路，只把一個服務以 interface endpoint（本地私有 IP）暴露給另一個 VPC；CIDR 可以重疊。 | 第 44 章 |
| resource hint | 資源提示 | HTML 中提示瀏覽器提前動作的標記：`preconnect` 預先建連線、`dns-prefetch` 只做 DNS、`preload` 預先下載資源。 | 第 46 章 |
| route table（VPC） | 路由表 | 關聯到 subnet、決定流量去向的表；`local` 路由讓 VPC 內任意位址互通，0.0.0.0/0 指向 IGW 的是 public 子網、指向 NAT gateway 的是 private 子網。 | 第 44 章 |
| security group | 安全群組 | 掛在網路介面上、只有允許規則、stateful 的雲端防火牆；來源可以寫另一個 security group。 | 第 44 章 |
| service mesh | 服務網格 | 每個服務旁放 proxy（資料平面）接管流量，由控制平面下發設定與 mTLS 憑證。 | 第 44 章 |
| Transit gateway | 轉運閘道 | 區域內的路由中樞，VPC、VPN、專線 attach 上去後依它的路由表互通，路由可以傳遞。 | 第 44 章 |
| veth pair | 虛擬乙太網路對 | 成對的虛擬網卡，一端在容器裡（`eth0`）、一端接到主機的 Linux bridge。 | 第 44 章 |
| VPC（Virtual Private Cloud） | 虛擬私有雲 | 雲端上自己的私有網路，由 subnet、route table、閘道與防火牆組成；沒有真的 L2，聲聲 Live 為 10.20.0.0/16。 | 第 1 章 → 第 44 章 |
| VPC flow log | VPC 流量紀錄 | 記錄每張網路介面上每條流的五元組與 ACCEPT／REJECT，用來區分被 SG、NACL 擋下或根本無路可走。 | 第 44 章 |
| VPC peering | VPC 對等連線 | 兩個 VPC 之間的私有連線，CIDR 不能重疊，而且不可傳遞。 | 第 44 章 |
| VXLAN | — | 把整個 Ethernet frame 包在 UDP（4789）裡的 overlay 封裝，以 VTEP 封裝與解封裝、VNI 區分網段。 | 第 44 章 |

## A.14 聲聲 Live 專有名詞

貫穿全書的案例「聲聲 Live」用到的人物、網域、位址與事故名稱都是虛構的，網域與 IP 一律使用文件保留名稱與保留位址。下面四張表依全書共用設定整理；同一個位址在不同章節出現時，用途以這裡為準。

### A.14.1 人物

| 名稱 | 身分 | 首次出現 → 主要章節 |
|---|---|---|
| 小晴 | 剛入職的 junior 後端工程師，熟悉 Python 與 Flask，網路底層只有零碎概念；全書的主角 | 第 1 章 → 全書 |
| 阿德 | 資深平台工程師，經歷過多次網路事故，小晴的 mentor | 第 1 章 → 全書 |
| Joe | 影音工程師，負責 WebRTC、SFU 與直播 | 第 1 章 → 第 34–39 章 |
| Rita | 資安工程師，負責驗證、授權與審查；訂下 ICMP 與防火牆政策 | 第 1 章 → 第 17、23、26–30 章 |
| 美咲 | 日文老師（ID `t_misaki`、帳號 `teacher05`），在日本授課；九月講座在京都飯店直播 | 第 1 章 → 第 34、38、39 章 |
| 敏俊 | 韓文老師（ID `t_minjun`） | 第 24 章 |
| 小安 | 學生（session sid=A），在第 34 章以 4G 上課 | 第 21 章 → 第 34 章 |
| 阿哲 | 學生（session sid=B），在高鐵上用 4G 上小班課 | 第 21 章 → 第 37 章 |
| 小芸 | 學生，用宿舍 Wi-Fi 上課 | 第 37 章 |
| 小林 | 企業客戶北辰物流的員工，辦公室出口只放行 TCP 443 | 第 39 章 |
| 北辰物流 | 企業客戶，IdP 為 `login.beichen.example`，以 OIDC 接入 SSO | 第 29 章 → 第 29、39 章 |
| 詞卡島 | 合作 App（`cards.example.net`，`client_id` 為 `cards`），以 OAuth 讀取學生生字 | 第 28 章 |

### A.14.2 網域

| 網域 | 用途 | 首次出現 → 主要章節 |
|---|---|---|
| `shengsheng.example` | 對外主網域；HSTS 設 `includeSubDomains; preload`，也是 passkey 的 RP ID | 第 1 章 → 第 14、19 章 |
| `www.shengsheng.example` | 網站，CNAME 到 CDN 的 edge（203.0.113.10、.11） | 第 1 章 → 第 15、21 章 |
| `api.shengsheng.example` | API，指向 API LB 203.0.113.80；跨 origin 呼叫需要 CORS | 第 1 章 → 第 23、24 章 |
| `auth.shengsheng.example` | 登入與 OAuth／OIDC，和 `api` 共用 LB、依 SNI 選憑證 | 第 1 章 → 第 19、29 章 |
| `rt.shengsheng.example` | 即時服務（SSE、WebSocket、signaling），L4 LB 203.0.113.40 | 第 1 章 → 第 31–33 章 |
| `live.shengsheng.example` | 直播媒體伺服器 203.0.113.25：SRT ingest UDP 9000、WHIP／WHEP | 第 1 章 → 第 38 章 |
| `watch.shengsheng.example` | 觀眾觀看 LL-HLS 的 CDN 網域 | 第 1 章 → 第 38 章 |
| `turn.shengsheng.example` | TURN／STUN 203.0.113.50，提供 UDP／TCP 3478 與 TLS 443 | 第 1 章 → 第 36、37 章 |
| `teach.shengsheng.example` | 老師後台，在 API 的 CORS 允許清單中 | 第 23 章 |
| `ops.shengsheng.example` | 內部後台，只開內網，採 mTLS 加 SSO | 第 8 章 → 第 18 章 |
| `promo.shengsheng.example` | 行銷子網域，dangling CNAME 與 cookie 範圍的反例 | 第 15 章 → 第 23 章 |
| `ns1.shengsheng.example` | 權威 DNS（203.0.113.53） | 第 14 章 |
| `internal.shengsheng.example` | VPC 的 private zone（例如資料庫的內部名稱） | 第 16 章 → 第 44 章 |
| `ss.cdnedge.test` | 舊 CDN 給的名稱（198.51.100.7、.8），換 CDN 事故的主角 | 第 14 章 → 第 15 章 |
| `pay.example.net` | 外部金流供應商，webhook 來源 `198.51.100.64/26` | 第 16 章 → 第 17、30 章 |

### A.14.3 主機與位址

| 位址 | 用途 | 主要章節 |
|---|---|---|
| 203.0.113.10、.11 | `www` 的 CDN edge（IPv6 `2001:db8:5::10`） | 第 1、15 章 |
| 203.0.113.20 → 203.0.113.80 | API 搬遷前的舊 IP → 搬遷後的 API LB（VPC 內為 10.20.16.5） | 第 14、25 章 |
| 203.0.113.40 | `rt` 的 L4 LB，不解密；TLS 終結在 nginx 10.20.2.11–.13 | 第 19、32、33 章 |
| 203.0.113.25 | 直播 ingest `live` | 第 4、38 章 |
| 203.0.113.50 | TURN（明年擴充為 .50–.52） | 第 36、37、46 章 |
| 203.0.113.53 | 權威 DNS `ns1` | 第 14 章 |
| 203.0.113.60 | SFU `sfu-tpe-1`，媒體埠 UDP 40000；VPC 內管理介面 10.20.1.15 | 第 35、37、44 章 |
| 203.0.113.70 | 錄影回放與 LL-HLS 的 origin（位於 CDN 後方） | 第 12、46 章 |
| 198.51.100.23 | 範例學生家用路由器的對外位址（內網 192.168.1.0/24） | 第 1、7、13 章 |
| 10.20.0.0/16 | 雲端 VPC；resolver 10.20.0.2、10.20.0.3 | 第 5、44 章 |
| 10.20.3.11 | nginx（API 路徑上的 reverse proxy） | 第 25、43 章 |
| 10.20.3.21、10.20.3.22 | app-a、app-b 的 gunicorn（:8000）；app-a 也跑網路體檢探針 UDP :9910 | 第 9、43 章 |
| 10.20.17.15 | PostgreSQL（:5432，data 子網） | 第 43、44 章 |
| 10.20.17.21 | Redis primary（即時服務的 broker 與房間狀態） | 第 33 章 |
| 10.20.1.40 | 擴充前的即時服務單機（uvicorn :8001） | 第 31、32 章 |
| 10.20.1.41–.43、10.20.65.44–.46 | 擴充後的即時 gateway gw-41–46 | 第 33、42 章 |
| 10.20.4.12:50051 | 推薦服務 `reco` 的 gRPC（K8s ClusterIP 10.96.40.12） | 第 24、44 章 |
| 10.96.0.10 | Kubernetes 的 kube-dns Service（叢集網域 `cluster.local`、namespace `live`） | 第 16、44 章 |
| 10.244.0.0/16 | Pod CIDR（每個節點一個 /24），VXLAN 的 Pod MTU 1450 | 第 44 章 |
| 10.30.0.0/24、10.40.0.0/24 | 攝影棚 LAN（VLAN 10）、辦公室網段（VLAN 20） | 第 4、8 章 |
| AS64500 | 聲聲 Live 的 ASN，機房網段 203.0.113.0/24 | 第 6 章 |

### A.14.4 事故名稱

| 事故 | 一句話：症狀 → 根因 | 章節 |
|---|---|---|
| 首頁要等三秒 | 美國學生開首頁要三秒、Flask 只花 30 ms → 時間花在跨洋 RTT 的多次往返 | 第 1 章 |
| RTT 兩萬兩千毫秒的教室 | 品質回報面板顯示 22272 ms → Python 改寫時用了錯的 byte order | 第 2 章 |
| 備用編碼器連不上 | 換上同 IP 的備用編碼器後 NAS 連不到 → ARP 快取還指向舊機器的 MAC | 第 4 章 |
| 海線電信的學生連不上 | 只有一家 ISP 的使用者連不上 → 別的 AS 宣告了更具體的前綴 | 第 6 章 |
| VPN 上只有大東西會消失 | 小請求正常、大回應卡住 → network ACL 擋了 ICMP，造成 PMTUD 黑洞 | 第 8 章 |
| CLOSE_WAIT 連線池事故 | 晚上八點教室入口 API 5xx 30% → 自寫連線池不關閉被對方關掉的連線 | 第 10 章 → 第 43、45 章 |
| 捷運上卡住的投影片 | 手機換網路後頁面停住 → 四元組改變，TCP 連線無法延續 | 第 13 章 |
| API 搬遷事故 | 改了 A 紀錄仍有七成使用者連到舊 IP → 舊答案還在 resolver 快取裡（TTL 3600） | 第 14 章 → 第 45 章 |
| 換 CDN 後連到舊 edge | 先降 TTL 卻只等了十分鐘 → 降 TTL 本身也要等舊 TTL 86400 過期 | 第 15 章 |
| 登入憑證過期 | 2026-10-01 台灣早上八點登入頁變紅 → 手動匯入的 OV 憑證這次只有 199 天效期，提醒卻照舊設在隔年 | 第 19 章 → 第 45 章 |
| 首頁快取事故 | 首頁顯示別人的名字 → 個人化回應被標成 `public` 而被 CDN 快取；21:58 起十二分鐘內止血 | 第 21 章 → 第 25 章 |
| 預約按鈕被 CORS 擋下 | 部署到 staging 後按鈕沒反應 → preflight 沒有通過 CORS 檢查，帶憑證的請求又不能用 `*` | 第 23 章 → 第 45 章 |
| 重複扣款 | 只按一次被扣兩次 → client 逾時重試，付款 API 沒有 idempotency key | 第 24 章 |
| 講座開場前的 purge | 全站 purge 後回源暴增、504 與 429 → health check 只看 TCP、限速看到的是 nginx 位址 | 第 25 章 |
| 撞庫事故 | 約 2,700 個 IP、21 萬次嘗試、186 個帳號被登入 → 使用者在別處外洩的密碼 | 第 26 章 |
| 停權後仍能改課表 | 停權三小時後 App 仍能改課 → JWT 有效七天且 API 從不查撤銷 | 第 27 章 |
| 開賣夜重複加點事故 | 21:02–21:41 webhook 驗章失敗與重送，37 人點數重複 → middleware 改寫了原始 body、hotfix 跳過驗章 | 第 30 章 |
| 部署時重連驚群 | 部署時數千條連線同一秒斷線又同時重連 → 沒有連線排空與重連抖動 | 第 31–33 章 |
| 開學夜聊天室裂成兩半 | 同教室的人看不到彼此訊息 → 加了第二台即時服務卻沒有 broker | 第 33 章 |
| 低延遲模式事故 | 老師聲音像機器人，丟包只有 0.3% → jitter buffer 上限被壓到 20 ms，補洞樣本約 11% | 第 34 章 → 第 37、39 章 |
| PT 98 munging 事故 | 老師畫面上的黑框 → 前端寫死 PT 98 改 SDP，SFU 以 `no_primary_codec` 拒絕視訊 | 第 35 章 → 第 39、45 章 |
| 京都飯店的講座 | 推流掉 frame、問答接不上 → 飯店 Wi-Fi 上的 RTMP（TCP）遇丟包；觀看端是 6 秒一段的 HLS，延遲二十多秒 | 第 38 章 |
| staging 誤開 debugger 事故 | staging 主機 10.21.3.21:5000 的 Werkzeug debugger 從辦公室 VPN 連得到 | 第 41 章 |
| 三百人講座讓網站停擺 | 18 個 sync worker 全被 long polling 佔住 → WSGI 的等待也佔一個 worker | 第 42 章 |
| 每次部署一波 502 | 重啟時約四十秒的 502 → 沒有 graceful shutdown，keep-alive 與逾時鏈不一致 | 第 43 章 |
| 新節點群組上線後的星期一 | 新節點上的 Pod 呼叫金流逾時、資料庫新連線約六成失敗 → 新子網的 route table 少了往 NAT gateway 的路由；新的 stateless network ACL 只放行 49152–65535 的回程，Linux 的 ephemeral port 是 32768–60999 | 第 44 章 |
