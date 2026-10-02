# 附錄 C　協定格式速查

> [!abstract] 本附錄地圖
> **用途**：抓封包、讀 log、寫解析程式或除錯時，快速確認「這個 byte 是哪個欄位、這個值代表什麼」。每個格式都附位元布局圖、欄位表與「詳見第 N 章」，圖與表的欄位名稱和正文一致；需要原理、時序與取捨時，回到對應章節。
>
> **怎麼查**：
> - 手上有一段 hex dump，不知道是什麼協定：先看 C.1 的「怎麼認出它」總表，再依序往內層拆（Ethernet → IP → TCP／UDP → 應用層）。
> - 已知協定、要查某個欄位：直接跳到該小節，先看圖找位置，再看欄位表查意義與常見值。
> - 要寫或驗證自己的解析程式：C.23 用 `struct` 列出每個固定 header 的格式字串與長度，並拿正文出現過的範例 bytes 對拍。
> - 文字類格式（HTTP/1.1、JWT、SDP）與 Python 介面（WSGI environ、ASGI scope 與事件）在 C.12、C.19–C.22，用表格整理。
>
> **前置知識**：第 2 章（位元布局圖的讀法、network byte order）。port 號、status code、close code、DNS rcode 與 TLS alert 的完整代碼表在附錄 D，本附錄只列和格式有關的值。

## C.1 怎麼讀這些圖：慣例與總表

本附錄的位元布局圖沿用第 2 章的畫法：每列 32 bits（4 bytes），最上方的尺標是 bit 編號，從 0 開始，左邊是最先送出、也是最高位的 bit。欄位名稱後的括號是位元數，例如 `Length (16)`；右側的 `bytes 4-7` 是該列在 header 裡的 byte 偏移。所有多 byte 的整數都是 **network byte order**（big-endian，高位 byte 先送），唯一的例外是 Ethernet FCS 依慣例低位元組先送（第 4 章的程式用 `"<I"`）。

```text
  bit  0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      ┌───────────────┬───────────────┬───────────────────────────────┐
  0   │ 1 byte 的欄位 │ 1 byte 的欄位 │       2 bytes 的欄位          │  ← 一列 = 4 bytes
      ├───────────────┴───────────────┴───────────────────────────────┤
  4   │                     4 bytes 的欄位                            │
      └───────────────────────────────────────────────────────────────┘
   尺標上的 0、1、2、3 是「第幾個 byte 開頭」，下一行的 0–9 循環是 bit 編號的個位數
   欄位跨越格線時，以數格子的方式算出它從第幾個 bit 開始、佔幾個 bit
```

讀圖的方法是數格子：一格 1 bit，8 格是 1 byte。例如 IPv4 第一個 byte 的前 4 格是 Version、後 4 格是 IHL，所以 `0x45` 代表版本 4、header 5 個 32-bit word。把一個欄位從 bytes 取出來時，先用 `struct` 以 `!` 開頭的格式字串拆出整數，再用位移與遮罩取出子欄位，例如 `b0 >> 4` 與 `b0 & 0x0F`。

下面的總表是「手上有一段 bytes，怎麼認出它」的起點：固定部分有多長、哪幾個 byte 最有辨識度，以及在哪一章詳細說明。

| 格式 | 固定部分 | 怎麼認出它（常見開頭或特徵值） | 本附錄 | 詳見 |
|---|---|---|---|---|
| Ethernet II | 14 bytes＋FCS 4 | 偏移 12–13 是 EtherType：`08 00` IPv4、`08 06` ARP、`86 dd` IPv6、`81 00` VLAN | C.2 | 第 2、4 章 |
| ARP | 28 bytes（Ethernet／IPv4） | `00 01 08 00 06 04` 開頭 | C.3 | 第 4 章 |
| IPv4 | 20–60 bytes | 第一個 byte 幾乎總是 `45` | C.4 | 第 2、5、8 章 |
| IPv6 | 40 bytes | 第一個 nibble 是 `6` | C.5 | 第 2、5、8 章 |
| ICMP／ICMPv6 | 8 bytes 起 | IPv4 protocol 1；IPv6 next header 58 | C.6 | 第 8 章 |
| UDP | 8 bytes | IPv4 protocol／IPv6 next header 17 | C.7 | 第 2、9 章 |
| TCP | 20–60 bytes | protocol 6；第 13 個 byte（偏移 12）高 4 bits 是 data offset | C.8 | 第 10、11 章 |
| DNS | header 12 bytes | UDP／TCP port 53；TCP 上多 2 bytes 長度前綴 | C.9 | 第 14、15 章 |
| TLS record | 5 bytes | `16 03 01`／`16 03 03` 交握、`17 03 03` 加密資料 | C.10 | 第 18 章 |
| QUIC | 不固定 | UDP 443；第一個 byte 的最高兩位：`11` long header、`01` short header | C.11 | 第 13 章 |
| HTTP/1.1 | 文字 | `GET ␠`、`POST ␠`、`HTTP/1.1 ␠` 開頭，以 CRLF 分行 | C.12 | 第 20、21 章 |
| HTTP/2 | frame header 9 bytes | 連線開頭的 24 bytes preface `PRI * HTTP/2.0…` | C.13 | 第 22 章 |
| WebSocket | 2–14 bytes | `101 Switching Protocols` 之後；server 的 text frame 常以 `81` 開頭 | C.14 | 第 32 章 |
| RTP | 12 bytes 起 | 第一個 byte 128–191（V=2），第二個 byte 不在 192–223 | C.15 | 第 34 章 |
| RTCP | 4 bytes 起 | 第一個 byte 128–191，第二個 byte 200–206 | C.16 | 第 34 章 |
| STUN | 20 bytes | 第一個 byte 0–3；byte 4–7 是 `21 12 a4 42` | C.17 | 第 36 章 |
| SRT | 16 bytes | 第一個 bit：0 資料、1 控制；常見 UDP 9000（依部署而定） | C.18 | 第 38 章 |

> [!tip] 同一個 port 上的分流
> WebRTC 把 STUN、DTLS、TURN ChannelData 與 SRTP／SRTCP 放在同一個 UDP 五元組上，接收端只看第一個 byte 就分得開：0–3 是 STUN、20–63 是 DTLS、64–79 是 TURN ChannelData、128–191 是 RTP 或 RTCP（再看第二個 byte，192–223 是 RTCP）。這套範圍見第 35、36 章，C.15–C.17 的圖都會標出第一個 byte 的特徵。

## C.2 Ethernet frame 與 802.1Q VLAN tag

```text
 在線路上（網卡負責，tcpdump 通常看不到）
 ┌──────────────────────┬─────┐
 │ Preamble 7 bytes     │ SFD │   10101010 × 7 ＋ 10101011
 └──────────────────────┴─────┘
 Frame 本體（從這裡開始算 frame 長度）
  0                   6                   12      14                         14+N     +4
 ┌───────────────────┬───────────────────┬───────┬──────────────────────────┬───────┐
 │ Destination MAC   │ Source MAC        │ Ether │ Payload 46–1500 bytes    │  FCS  │
 │ 6 bytes           │ 6 bytes           │ Type 2│（IP 封包、ARP…，不足補 0）│ 4 B   │
 └───────────────────┴───────────────────┴───────┴──────────────────────────┴───────┘
  最小 64 bytes（14 + 46 + 4），最大 1518 bytes（14 + 1500 + 4）；帶 VLAN tag 時最大 1522

 802.1Q frame：│ 目的 MAC 6 │ 來源 MAC 6 │ TPID 0x8100 │  TCI  │ EtherType 2 │ Payload … │ FCS 4 │
                                        └──── 4 bytes 的 VLAN tag ────┘
 TCI（16 bits）：
  15 14 13  12  11                                   0
 ┌─────────┬───┬───────────────────────────────────────┐
 │ PCP (3) │DEI│              VID (12 bits)            │
 └─────────┴───┴───────────────────────────────────────┘
```

上圖是 Ethernet II frame。目的 MAC 放在最前面，交換器讀完前 6 bytes 就能決定往哪裡轉送。Payload 上限 1500 bytes 就是 MTU，指的是 IP 封包的上限，不是整個 frame。VLAN tag 插在來源 MAC 與原本的 EtherType 之間，TPID `0x8100` 佔住原本 EtherType 的位置，真正的 EtherType 被往後推 4 bytes。

| 欄位 | 大小 | 意義與常見值 |
|---|---|---|
| Destination MAC | 6 bytes | `ff:ff:ff:ff:ff:ff` 是廣播；第一個 byte 最低位為 1 是多播；第二低位為 1 是本地管理位址（本書範例用 `02:` 開頭） |
| Source MAC | 6 bytes | 送出網卡的位址，交換器靠它學習 MAC 表 |
| EtherType | 2 bytes | 值 ≥ 0x0600 是協定編號；≤ 1500 時在舊 802.3 格式裡表示長度 |
| Payload | 46–1500 bytes | 不足 46 bytes 補 0；padding 不屬於 IP 封包，要用 IP 的長度欄位切掉 |
| FCS | 4 bytes | CRC-32，涵蓋目的 MAC 到 payload；錯了就丟棄、不通知任何人 |
| TPID（802.1Q） | 2 bytes | `0x8100`；QinQ 外層用 `0x88A8` |
| PCP／DEI／VID | 3／1／12 bits | 優先權 0–7／壅塞時可優先丟棄／VLAN 編號 1–4094（0 與 4095 保留） |

| EtherType | 協定 | 詳見 |
|---|---|---|
| 0x0800 | IPv4 | 第 2、5 章 |
| 0x0806 | ARP | 第 4 章 |
| 0x86DD | IPv6 | 第 5 章 |
| 0x8100 | 802.1Q VLAN tag | 第 4 章 |
| 0x88A8 | 802.1ad（QinQ）外層 tag | 第 4 章 |
| 0x88CC | LLDP | 第 4 章 |

## C.3 ARP（Ethernet 上解析 IPv4）

```text
  byte 偏移
  0      ┌───────────────────────────────┬───────────────────────────────┐
         │ Hardware Type = 1（Ethernet） │ Protocol Type = 0x0800（IPv4）│
  4      ├───────────────┬───────────────┼───────────────────────────────┤
         │ HLEN = 6      │ PLEN = 4      │ Operation：1=request，2=reply │
  8      ├───────────────┴───────────────┴───────────────────────────────┤
         │ Sender Hardware Address（SHA）6 bytes：送出者的 MAC           │
  14     ├───────────────────────────────────────────────────────────────┤
         │ Sender Protocol Address（SPA）4 bytes：送出者的 IP            │
  18     ├───────────────────────────────────────────────────────────────┤
         │ Target Hardware Address（THA）6 bytes：目標的 MAC（請求時填 0）│
  24     ├───────────────────────────────────────────────────────────────┤
         │ Target Protocol Address（TPA）4 bytes：要問的 IP              │
  28     └───────────────────────────────────────────────────────────────┘
```

ARP 直接放在 Ethernet frame 裡（EtherType 0x0806），不經過 IP。前 8 bytes 描述位址的種類與長度，後 20 bytes 是兩組「MAC＋IP」。請求的 Ethernet 目的位址是廣播、THA 填 0；回應是單播，兩組位址對調。28 bytes 加上 14 bytes 的 Ethernet header 只有 42 bytes，線路上會補到 60 bytes 再加 FCS，所以 tcpdump 在送出端常看到 42 bytes，這不是錯誤。

| 欄位 | 大小 | 常見值 | 備註 |
|---|---|---|---|
| Hardware Type | 2 bytes | 1 | Ethernet |
| Protocol Type | 2 bytes | 0x0800 | 要解析的是 IPv4 位址，借用 EtherType 的編號 |
| HLEN／PLEN | 1＋1 byte | 6／4 | MAC 與 IPv4 位址長度 |
| Operation | 2 bytes | 1 request、2 reply | gratuitous ARP 也是 request 或 reply，只是 SPA 與 TPA 都是自己的 IP |
| SHA／SPA | 6＋4 bytes | 送出者 | 收到請求的一方會順便記下這組對應 |
| THA／TPA | 6＋4 bytes | 目標 | 請求時 THA 全 0 |

IPv6 不用 ARP，改用 ICMPv6 的 Neighbor Discovery（Type 135／136，見 C.6）。

## C.4 IPv4

```text
  bit  0               1               2               3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      ┌───────┬───────┬───────────┬───┬───────────────────────────────┐
  0   │Version│  IHL  │   DSCP    │ECN│         Total Length          │
      ├───────┴───────┴───────────┴───┼─────┬─────────────────────────┤
  4   │        Identification         │Flags│     Fragment Offset     │
      ├───────────────┬───────────────┼─────┴─────────────────────────┤
  8   │      TTL      │   Protocol    │        Header Checksum        │
      ├───────────────┴───────────────┴───────────────────────────────┤
  12  │                       Source Address                          │
      ├───────────────────────────────────────────────────────────────┤
  16  │                     Destination Address                       │
      ├───────────────────────────────────────────────────────────────┤
  20  │           Options（IHL > 5 時才有，最多 40 bytes）            │
      └───────────────────────────────────────────────────────────────┘
   Flags 三個 bit：0＝保留（必須為 0）  D＝DF（Don't Fragment）  M＝MF（More Fragments）
   第 2 章範例：45 00 0028 b2a0 4000 40 11 6fe7 0a14010f 0a140307
```

IPv4 header 最少 20 bytes，IHL 以 4 bytes 為單位，所以 IHL＝5 就是沒有 options 的 20 bytes，最大 15 即 60 bytes。圖下方的範例 bytes 來自第 2 章：品質回報封包從 10.20.1.15 送往 10.20.3.7，DF＝1、TTL 64、protocol 17，checksum 為 `0x6fe7`，C.23 的程式會重算一次。

| 欄位 | 大小 | 意義與常見值 | 詳見 |
|---|---|---|---|
| Version＋IHL | 4＋4 bits | 4；5（20 bytes） | 第 2 章 |
| DSCP＋ECN | 6＋2 bits | 服務等級；ECN 壅塞標記 | 第 2、12 章 |
| Total Length | 16 bits | header＋payload，最大 65535；用來切掉 Ethernet padding | 第 2 章 |
| Identification | 16 bits | 同一原始封包的分片共用同一個值 | 第 8 章 |
| Flags＋Fragment Offset | 3＋13 bits | `0x4000` 只有 DF；offset 以 8 bytes 為單位 | 第 8 章 |
| TTL | 8 bits | 每經過一台路由器減 1，歸零即丟棄並回 ICMP Type 11；初始值常見 64 或 128 | 第 2、6 章 |
| Protocol | 8 bits | 1 ICMP、6 TCP、17 UDP、50 ESP | 第 2 章 |
| Header Checksum | 16 bits | 一補數加總後取反，只保護 header；每一跳改 TTL 後要更新 | 第 2、6 章 |
| Source／Destination | 32 bits 各一 | 端到端的起點與終點；NAT 會改寫（第 7 章） | 第 5 章 |

## C.5 IPv6

```text
  bit  0               1               2               3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      ┌───────┬───────────────┬───────────────────────────────────────┐
  0   │Version│ Traffic Class │              Flow Label (20)          │
      ├───────┴───────────────┴───────┬───────────────┬───────────────┤
  4   │       Payload Length (16)     │ Next Header   │  Hop Limit    │
      ├───────────────────────────────┴───────────────┴───────────────┤
  8   │                                                               │
      │                 Source Address（128 bits）                    │  bytes 8-23
      │                                                               │
      ├───────────────────────────────────────────────────────────────┤
  24  │                                                               │
      │               Destination Address（128 bits）                 │  bytes 24-39
      │                                                               │
      └───────────────────────────────────────────────────────────────┘
   之後可以接零到多個 extension header，每個都以 Next Header 串到下一個
```

IPv6 固定 header 是 40 bytes，沒有 IHL、沒有 checksum，也沒有分片欄位。第 2 章練習 1 用 `ipaddress.IPv6Address(...).packed` 組出位址，第 5 章講位址格式與 SLAAC，第 8 章說明 IPv6 的路由器永遠不分片：太大的封包一律丟棄並回 ICMPv6 Packet Too Big，只有傳送端可以加 Fragment extension header 自己切。最小 MTU 是 1280 bytes。

| 欄位 | 大小 | 意義與常見值 |
|---|---|---|
| Version | 4 bits | 6 |
| Traffic Class | 8 bits | 和 IPv4 的 DSCP＋ECN 相同的用途 |
| Flow Label | 20 bits | 標記同一個 flow，讓路徑上的設備做負載平衡時不必看上層 port |
| Payload Length | 16 bits | 不含這 40 bytes 的固定 header（和 IPv4 的 Total Length 不同） |
| Next Header | 8 bits | 6 TCP、17 UDP、58 ICMPv6、0 Hop-by-Hop、43 Routing、44 Fragment、60 Destination Options |
| Hop Limit | 8 bits | 等同 IPv4 的 TTL |
| Source／Destination | 128 bits 各一 | 文件用前綴 `2001:db8::/32`（本書範例用 `2001:db8:5a5a::/48`） |

## C.6 ICMP 與 ICMPv6

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────┬───────────────┬───────────────────────────────┐
 │   Type (8)    │   Code (8)    │         Checksum (16)         │  ← 所有 ICMP 都一樣
 ├───────────────┴───────────────┴───────────────────────────────┤
 │                 Rest of Header（4 bytes，依 Type 而定）       │
 │   echo：      Identifier (16)        │  Sequence Number (16)  │
 │   Type 3/4：  Unused (16) = 0        │  Next-Hop MTU (16)     │
 ├───────────────────────────────────────────────────────────────┤
 │ Data：                                                        │
 │   echo  → 任意 payload（ping 通常放時間戳記與填充）           │
 │   錯誤訊息 → 引發錯誤的原始 IP header ＋ 原始 payload 前 8 bytes 以上 │
 └───────────────────────────────────────────────────────────────┘
```

前 4 bytes 所有 ICMP 都相同，接下來 4 bytes 依 Type 而定。錯誤訊息一定附上原始 IP header 與至少 8 bytes 的原始 payload，剛好涵蓋 TCP／UDP 的兩個 port，收到的主機才能找出是哪一條連線出事。IPv4 的 ICMP checksum 只算 ICMP 本身；ICMPv6 要加 pseudo-header。ICMPv6 的 Packet Too Big 把 MTU 放在 32 bits 的欄位裡。

| 協定 | Type | Code | 名稱 | 防火牆政策（第 8 章） |
|---|---|---|---|---|
| ICMP | 0／8 | 0 | Echo Reply／Echo Request | 可限速，不建議全擋 |
| ICMP | 3 | 0／1／3 | Net／Host／Port Unreachable | 不建議擋 |
| ICMP | 3 | 4 | Fragmentation Needed and DF Set（帶 Next-Hop MTU） | 絕對不能擋，PMTUD 靠它 |
| ICMP | 3 | 13 | Communication Administratively Prohibited | 依政策 |
| ICMP | 5 | 0–3 | Redirect | 主機通常應忽略 |
| ICMP | 11 | 0／1 | Time Exceeded（TTL 歸零／重組逾時） | 不建議擋，traceroute 靠它 |
| ICMP | 12 | 0 | Parameter Problem | 不建議擋 |
| ICMPv6 | 1 | 0–6 | Destination Unreachable | 不建議擋 |
| ICMPv6 | 2 | 0 | Packet Too Big（32 bits MTU） | 絕對不能擋 |
| ICMPv6 | 3／4 | — | Time Exceeded／Parameter Problem | 不建議擋 |
| ICMPv6 | 128／129 | 0 | Echo Request／Echo Reply | 可限速 |
| ICMPv6 | 133–137 | 0 | Neighbor Discovery（RS、RA、NS、NA、Redirect） | 擋了 IPv6 就不能用（RFC 4890） |

## C.7 UDP

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-------------------------------+-------------------------------+
|        Source Port (16)       |     Destination Port (16)     |
+-------------------------------+-------------------------------+
|          Length (16)          |         Checksum (16)         |
+-------------------------------+-------------------------------+
|                    Payload（0 到 65507 bytes，IPv4）          |
+---------------------------------------------------------------+

 計算 checksum 時前面接的 pseudo-header（不會送出）：
 IPv4：│ Source Address 4 │ Destination Address 4 │ zero 1 │ Protocol 17 (1) │ UDP Length 2 │
 IPv6：│ Source Address 16 │ Destination Address 16 │ UDP Length 4 │ zero 3 │ Next Header 17 (1) │
```

UDP header 只有 8 bytes，沒有序號、ACK、視窗與旗標，這四個「沒有」是第 9 章三個語意（無連線、不可靠、保留訊息邊界）的根源。Length 包含 header，最小值是 8。checksum 涵蓋 pseudo-header、UDP header 與 payload，所以 NAT 改寫位址時也要重算。

| 欄位 | 大小 | 意義 | 詳見 |
|---|---|---|---|
| Source Port | 16 bits | 回覆送回這裡；通常是 ephemeral port（Linux 32768–60999） | 第 9 章 |
| Destination Port | 16 bits | 解多工到正確的 socket | 第 9 章 |
| Length | 16 bits | header＋payload；IPv4 上 payload 理論上限 65507 | 第 2、9 章 |
| Checksum | 16 bits | IPv4 上填 0 代表沒算，算出 0 時改送 `0xffff`；IPv6 上原則上必須計算 | 第 2、9 章 |

本書的 UDP 安全 payload 約 1200 bytes：IPv4 乙太網路最多 1472（1500 − 20 − 8），IPv6 最小 MTU 下是 1232（1280 − 40 − 8）。

## C.8 TCP 與常見選項

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────────────────────┬───────────────────────────────┐
 │       Source Port (16)        │     Destination Port (16)     │  bytes 0-3
 ├───────────────────────────────┴───────────────────────────────┤
 │                     Sequence Number (32)                      │  bytes 4-7
 ├───────────────────────────────────────────────────────────────┤
 │                  Acknowledgment Number (32)                   │  bytes 8-11
 ├───────┬───────┬─┬─┬─┬─┬─┬─┬─┬─┬───────────────────────────────┤
 │ Data  │ Rsrvd │C│E│U│A│P│R│S│F│                               │
 │Offset │       │W│C│R│C│S│S│Y│I│          Window (16)          │  bytes 12-15
 │  (4)  │  (4)  │R│E│G│K│H│T│N│N│                               │
 ├───────┴───────┴─┴─┴─┴─┴─┴─┴─┴─┼───────────────────────────────┤
 │          Checksum (16)        │      Urgent Pointer (16)      │  bytes 16-19
 ├───────────────────────────────┴───────────────────────────────┤
 │             Options（0～40 bytes，長度是 4 的倍數）           │  bytes 20-
 ├───────────────────────────────────────────────────────────────┤
 │                     Data（應用程式的資料）                    │
 └───────────────────────────────────────────────────────────────┘
   第 14 個 byte（偏移 13）的 8 個 bit 由高到低：CWR ECE URG ACK PSH RST SYN FIN
```

TCP header 固定 20 bytes，加上 options 最多 60 bytes。Data Offset 以 4 bytes 為單位，第 10 章的 SYN 範例是 `a0`，即 10 個 word、40 bytes。旗標在第 14 個 byte（偏移 13），SYN 是 `0x02`、SYN+ACK 是 `0x12`、純 ACK 是 `0x10`、FIN+ACK 是 `0x11`、RST 是 `0x04`。

| 欄位 | 大小 | 意義 | 詳見 |
|---|---|---|---|
| Source／Destination Port | 16＋16 bits | 和 IP 位址合起來是四元組 | 第 9、10 章 |
| Sequence Number | 32 bits | 這個 segment 第一個資料 byte 的編號；SYN 帶 ISN（隨機） | 第 10、11 章 |
| Acknowledgment Number | 32 bits | 期待收到的下一個 byte 編號，ACK 旗標打開才有效 | 第 11 章 |
| Data Offset | 4 bits | header 長度，5–15 個 32-bit word | 第 10 章 |
| Reserved | 4 bits | 必須為 0 | 第 10 章 |
| Flags | 8 bits | 見下表 | 第 10 章 |
| Window | 16 bits | 接收 buffer 剩餘空間；交握後要乘上 2^shift（Window Scale），SYN 本身不套用 | 第 11 章 |
| Checksum | 16 bits | 涵蓋 pseudo-header（protocol 6）、header 與資料；送出端抓包看到錯誤多半是 checksum offload | 第 10 章 |
| Urgent Pointer | 16 bits | URG 打開才有效，現代應用幾乎不用 | 第 10 章 |

| 旗標 | bit 值 | tcpdump | 意思 |
|---|---|---|---|
| FIN | 0x01 | `F` | 這個方向的資料送完了 |
| SYN | 0x02 | `S` | 同步起始序號（交握） |
| RST | 0x04 | `R` | 立刻中止，或「這裡沒有這條連線」 |
| PSH | 0x08 | `P` | 請盡快交給應用程式 |
| ACK | 0x10 | `.` | ack 欄位有效 |
| URG | 0x20 | `U` | Urgent Pointer 有效 |
| ECE | 0x40 | `E` | ECN Echo（第 12 章） |
| CWR | 0x80 | `W` | Congestion Window Reduced（第 12 章） |

每個選項的格式是 kind（1 byte）＋ length（1 byte，含這兩個 byte）＋ 值；只有 End of Option List 與 NOP 是單一 byte。下表的前五個只能在 SYN 與 SYN+ACK 上協商。

```text
 MSS        │ kind=2 │ len=4  │ MSS (16)                   │
 WScale     │ kind=3 │ len=3  │ shift (8)，0–14            │
 SACK-Perm  │ kind=4 │ len=2  │
 Timestamps │ kind=8 │ len=10 │ TSval (32) │ TSecr (32)    │
 SACK       │ kind=5 │ len=2+8n │ Left Edge 1 (32) │ Right Edge 1 (32) │ … 最多 n 個區塊
 第 10 章 Linux SYN 常見排列：MSS、SACK-Perm、Timestamps、NOP、WScale ＝ 20 bytes
```

| 選項 | kind | 長度 | 用途 | 詳見 |
|---|---|---|---|---|
| End of Option List | 0 | 1 | 選項到此結束 | 第 10 章 |
| NOP | 1 | 1 | 補齊對齊 | 第 10 章 |
| MSS | 2 | 4 | 每個 segment 最多收幾 bytes 資料，例如 1460；MSS clamping 改的就是它 | 第 8、10 章 |
| Window Scale | 3 | 3 | Window 的位移倍數，shift 最大 14 | 第 11 章 |
| SACK Permitted | 4 | 2 | 同意之後可用 SACK | 第 11 章 |
| SACK | 5 | 2＋8n | 回報收到的不連續區塊；和 Timestamps 共存時通常最多 3 個區塊 | 第 11 章 |
| Timestamps | 8 | 10 | 量 RTT、PAWS 防序號回繞；佔用 12 bytes 後 MSS 實際可用 1448 | 第 11、12 章 |

## C.9 DNS message 與 resource record

```text
 ┌──────────────────────────────┐
 │ Header（固定 12 bytes）      │  ID、旗標、四個區段各有幾筆
 ├──────────────────────────────┤
 │ Question                     │  QNAME、QTYPE、QCLASS（通常 1 筆）
 ├──────────────────────────────┤
 │ Answer                       │  直接回答問題的 RR（含 CNAME 鏈）
 ├──────────────────────────────┤
 │ Authority                    │  referral 時放 NS；NXDOMAIN 時放 SOA
 ├──────────────────────────────┤
 │ Additional                   │  glue 的 A／AAAA、EDNS 的 OPT
 └──────────────────────────────┘

 Header（每列 16 bits）：
  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
 ┌───────────────────────────────────────────────┐
 │                      ID                       │  bytes 0-1
 ├──┬───────────┬──┬──┬──┬──┬──┬──┬──┬───────────┤
 │QR│  Opcode   │AA│TC│RD│RA│Z │AD│CD│   RCODE   │  bytes 2-3（flags）
 ├──┴───────────┴──┴──┴──┴──┴──┴──┴──┴───────────┤
 │                   QDCOUNT                     │  bytes 4-5
 │                   ANCOUNT                     │  bytes 6-7
 │                   NSCOUNT                     │  bytes 8-9
 │                   ARCOUNT                     │  bytes 10-11
 └───────────────────────────────────────────────┘
```

DNS 查詢與回應共用一種格式。查詢通常只有 header 與 question；回應把 question 原樣帶回，再加上三個 RR 區段。走 UDP 時一個 datagram 就是一個訊息；走 TCP 時每個訊息前面多 2 bytes 的長度欄位，因為 TCP 沒有訊息邊界。第 14 章的查詢範例 header 是 `1a 2b 01 00 00 01 00 00 00 00 00 00`：只有 RD＝1、QDCOUNT＝1。

| flag／欄位 | 位元數 | 查詢時 | 回應時 | 詳見 |
|---|---|---|---|---|
| ID | 16 | 隨機（用 `secrets` 產生） | 原樣帶回 | 第 14 章 |
| QR | 1 | 0 | 1 | 第 14 章 |
| Opcode | 4 | 0（QUERY） | 複製查詢的值 | 第 14 章 |
| AA | 1 | 0 | 權威回答時為 1 | 第 14 章 |
| TC | 1 | 0 | 被截斷時為 1，client 改用 TCP 重問 | 第 14 章 |
| RD／RA | 1／1 | stub 設 RD＝1 | recursive resolver 設 RA＝1 | 第 14 章 |
| Z | 1 | 0 | 0 | 第 14 章 |
| AD／CD | 1／1 | CD＝1 要求先別驗證 | AD＝1 表示 DNSSEC 驗證通過 | 第 15 章 |
| RCODE | 4 | 0 | 0 NOERROR、1 FORMERR、2 SERVFAIL、3 NXDOMAIN、5 REFUSED（完整表見附錄 D） | 第 14 章 |

```text
 Question：│ QNAME（label 串，以 00 結尾）│ QTYPE (16) │ QCLASS (16) │

 Resource record：
 ┌──────────────────────────────────────────────┐
 │ NAME（label 串或 2 bytes 壓縮指標）          │
 ├────────────────────────┬─────────────────────┤
 │ TYPE (16)              │ CLASS (16)，IN = 1  │
 ├────────────────────────┴─────────────────────┤
 │ TTL (32，無號，秒)                           │
 ├────────────────────────┬─────────────────────┤
 │ RDLENGTH (16)          │ RDATA（RDLENGTH bytes）…
 └────────────────────────┴─────────────────────┘

 名字的編碼：03 'www' 0a 'shengsheng' 07 'example' 00
 一般 label： │0│0│ 長度 6 bits（1–63）│ 後接文字
 壓縮指標：   │1│1│ offset 14 bits（從訊息開頭算）│  共 2 bytes，例 c0 0c → offset 12
```

名字在封包裡不是點分隔字串，而是「長度＋內容」的 label 串，最後以長度 0 的 root 結尾。長度 byte 的最高兩位是 `11` 時，這兩個 byte 是壓縮指標；指標一定在名字結尾，解析器要防範指標互相指成迴圈。

| TYPE | 編號 | RDATA 格式 | 詳見 |
|---|---|---|---|
| A | 1 | 4 bytes IPv4 位址 | 第 14 章 |
| NS | 2 | 一個名字 | 第 14 章 |
| CNAME | 5 | 一個名字；同名不能有其他類型 | 第 14、15 章 |
| SOA | 6 | 兩個名字＋serial、refresh、retry、expire、minimum（各 32 bits） | 第 14、15 章 |
| PTR | 12 | 一個名字（`in-addr.arpa`／`ip6.arpa` 樹下） | 第 14 章 |
| MX | 15 | preference (16)＋名字 | 第 14 章 |
| TXT | 16 | 一到多個「1 byte 長度＋最多 255 bytes 文字」 | 第 14 章 |
| AAAA | 28 | 16 bytes IPv6 位址 | 第 14 章 |
| SRV | 33 | priority、weight、port（各 16 bits）＋目標名字 | 第 14 章 |
| OPT | 41 | EDNS(0) pseudo-RR，見下圖 | 第 14、15 章 |
| SVCB／HTTPS | 64／65 | priority (16)＋目標名字＋key=value 參數（`alpn`、`ipv4hint`、`ech`…） | 第 14、15 章 |
| CAA | 257 | flags (8)＋tag 長度＋tag＋value，例如 `0 issue "ca.example.net"` | 第 14、19 章 |

```text
 EDNS(0) 的 OPT pseudo-RR（放在 Additional 區段）
 ┌───────────────┬─────────────┬───────────────────────────────┐
 │ NAME = 00     │ TYPE = 41   │ CLASS = 可接收的 UDP 大小，例 1232 │
 ├───────────────┴─────────────┴───────────────────────────────┤
 │ TTL 欄位改作其他用途：Extended RCODE (8) │ Version (8) = 0 │ DO (1) │ Z (15) │
 ├─────────────────────────────────────────────────────────────┤
 │ RDLENGTH (16)  │ RDATA：零到多個 { option-code (16)、option-length (16)、data } │
 └─────────────────────────────────────────────────────────────┘
```

OPT 借用 RR 的格式攜帶擴充資訊：CLASS 欄位變成「我能接收多大的 UDP 回應」，建議值 1232 讓回應放得進 IPv6 最小 MTU；TTL 欄位拆成延伸 RCODE、版本與 DO 位元（DO＝1 表示要 DNSSEC 紀錄）。

## C.10 TLS record 與 handshake header

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────┬───────────────────────────────┬───────────────┐
 │ ContentType(8)│  legacy_record_version (16)   │  Length (16)… │  bytes 0-3
 ├───────────────┼───────────────────────────────┴───────────────┤
 │ …Length       │  fragment（Length bytes，最多 2^14＋256）     │  bytes 4-
 └───────────────┴───────────────────────────────────────────────┘

 TLS 1.3 加密後的 record（外層一律偽裝成 application_data）：
 ┌──────┬────────┬────────┬──────────────────────────────────┬─────────┐
 │ 0x17 │ 0x0303 │ Length │ 密文：真正內容 ‖ 真正類型 ‖ 補 0 │ tag 16B │
 └──────┴────────┴────────┴──────────────────────────────────┴─────────┘

 handshake 訊息（放在 ContentType 22 的 fragment 裡，可跨 record）：
 ┌──────────────┬──────────────────────────┬───────────────────────────┐
 │ msg_type (8) │ length (24)              │ body（length bytes）      │
 └──────────────┴──────────────────────────┴───────────────────────────┘
```

record header 固定 5 bytes，接收端靠 Length 把 TCP byte stream 切回一個個 record。明文 fragment 最多 2^14 bytes，加密後可再多 256 bytes。TLS 1.3 的 legacy_record_version 固定寫 `0x0303`（第一個 ClientHello 可寫 `0x0301`），真正的版本由 supported_versions 擴充協商。handshake header 是 1 byte 類型加 3 bytes 長度，所以 handshake 訊息的頭 4 bytes 和 record 的頭 5 bytes 合起來，抓包時常看到 `16 03 01 xx xx 01 00 xx xx`：一個裝著 ClientHello 的 handshake record。

| ContentType | 值 | 用途 | TLS 1.3 中是否明文 |
|---|---|---|---|
| change_cipher_spec | 20 | 1.3 只為相容 middlebox 送一個假的 | 是（內容固定 1 byte） |
| alert | 21 | 2 bytes：level＋description（代碼見附錄 D） | 交握前段是，之後加密 |
| handshake | 22 | 交握訊息 | 只有 ClientHello、ServerHello 是明文 |
| application_data | 23 | 應用資料；也是所有加密 record 的外層類型 | 加密 |

| msg_type | 值 | 方向 | 詳見 |
|---|---|---|---|
| client_hello | 1 | C→S | 第 18 章 |
| server_hello | 2 | S→C（HelloRetryRequest 也用這個類型，random 為固定特殊值） | 第 18 章 |
| new_session_ticket | 4 | S→C，交握之後 | 第 18 章 |
| end_of_early_data | 5 | C→S，0-RTT 結束 | 第 18 章 |
| encrypted_extensions | 8 | S→C | 第 18 章 |
| certificate | 11 | 雙向（mTLS 時 client 也送） | 第 18 章 |
| certificate_request | 13 | S→C，只有 mTLS | 第 18 章 |
| certificate_verify | 15 | 雙向 | 第 18 章 |
| finished | 20 | 雙向 | 第 18 章 |
| key_update | 24 | 雙向 | 第 18 章 |

```text
 ClientHello body
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ legacy_version = 0x0303 (2)          ← 永遠寫 TLS 1.2，真正版本在擴充裡  │
 │ random (32)                          ← 每次新的 CSPRNG 亂數              │
 │ legacy_session_id (1＋0..32)         ← 1.3 填 32 bytes 亂數（相容用）    │
 │ cipher_suites (2＋2n)                ← 例如 0x1301 0x1302 0x1303         │
 │ legacy_compression_methods (1＋1)    ← 只能是 0（null）                  │
 │ extensions (2＋…)                    ← 每個：type (2)、length (2)、data  │
 └──────────────────────────────────────────────────────────────────────────┘
```

| extension | type | 內容 | 詳見 |
|---|---|---|---|
| server_name（SNI） | 0 | 主機名稱，例如 `api.shengsheng.example` | 第 18 章 18.8 節 |
| supported_groups | 10 | x25519、secp256r1… | 第 18 章 |
| signature_algorithms | 13 | ECDSA P-256、RSA-PSS… | 第 18 章 |
| ALPN | 16 | `h2`、`http/1.1`；QUIC 上是 `h3` | 第 18、22 章 |
| pre_shared_key | 41 | resumption 票券；必須是最後一個擴充 | 第 18 章 18.9 節 |
| early_data | 42 | 宣告要送 0-RTT | 第 18 章 18.9 節 |
| supported_versions | 43 | `0x0304` 代表 1.3 | 第 18 章 |
| psk_key_exchange_modes | 45 | resumption 時是否再做 DHE | 第 18 章 |
| key_share | 51 | 一到多個 group 的公開值 | 第 18 章 |

| cipher suite | 值 | AEAD 與 HKDF hash |
|---|---|---|
| TLS_AES_128_GCM_SHA256 | 0x1301 | AES-128-GCM、SHA-256 |
| TLS_AES_256_GCM_SHA384 | 0x1302 | AES-256-GCM、SHA-384 |
| TLS_CHACHA20_POLY1305_SHA256 | 0x1303 | ChaCha20-Poly1305、SHA-256 |

> [!note] 2026 現況
> 截至 2026 年 10 月，依 2026 年 10 月查證，TLS 1.3 的規格有新版 RFC 9846（原 RFC 8446），版本號仍是 1.3，本節的 record 與 handshake 格式不變。ECH 與後量子混合金鑰交換的狀態見第 18 章 18.11 節。

## C.11 QUIC：varint、long header 與 short header

```text
 Variable-length integer（第一個 byte 的最高兩位 L 決定總長度）
  7 6 5 4 3 2 1 0
 ┌───┬───────────┐
 │ L │ 值的最高位│   L = 00 → 1 byte，6 bit　　L = 01 → 2 bytes，14 bit
 └───┴───────────┘   L = 10 → 4 bytes，30 bit　L = 11 → 8 bytes，62 bit
 例：0x7bbd → L=01，2 bytes；清掉前兩位得 0x3bbd = 15293
```

| 前綴 | 總長度 | 有效 bit | 最大值 | 常見用途 |
|---|---|---|---|---|
| `00` | 1 byte | 6 | 63 | frame type、小的 stream ID |
| `01` | 2 bytes | 14 | 16,383 | 封包長度 |
| `10` | 4 bytes | 30 | 1,073,741,823 | 較大的 offset、流量控制上限 |
| `11` | 8 bytes | 62 | 4,611,686,018,427,387,903 | 超大 offset |

```text
 Long header（交握期間：Initial、0-RTT、Handshake、Retry）
 byte 0     ┌─┬─┬───┬───┬───┐
            │1│1│T T│R R│P P│   Header Form=1、Fixed Bit=1、Long Packet Type、Reserved、PN Length−1
            └─┴─┴───┴───┴───┘
 bytes 1-4  │ Version (32)：v1 = 0x00000001；0 = Version Negotiation │
            │ DCID Len (8) │ Destination Connection ID（0–20 bytes） │
            │ SCID Len (8) │ Source Connection ID（0–20 bytes）      │
            │ Token Length (varint) │ Token …                        │  ← 只有 Initial 有
            │ Length (varint)：packet number＋payload 的長度         │
            │ Packet Number（1–4 bytes，長度由 PP 決定）             │
            │ Payload（加密的 frame）…                               │

 Short header（1-RTT，交握完成後）
 byte 0     ┌─┬─┬─┬───┬─┬───┐
            │0│1│S│R R│K│P P│   Header Form=0、Fixed Bit=1、Spin、Reserved、Key Phase、PN Length−1
            └─┴─┴─┴───┴─┴───┘
            │ Destination Connection ID（長度由接收端自己知道，沒有長度欄位）│
            │ Packet Number（1–4 bytes）                             │
            │ Payload（加密的 frame）…                               │
   第一個 byte 的低位元與 packet number 受 header protection 保護，沒有金鑰看不到
```

QUIC 跑在 UDP 上，一個 datagram 裡可以串好幾個 long header packet，接收端靠 Length 切開；short header 沒有 Length，一定是 datagram 裡的最後一個。short header 的 DCID 沒有長度欄位，server 可以自由決定 connection ID 的長度與結構，例如把後端編號編進去（第 13 章 13.9 節）。client 送出含 Initial 的 datagram 要撐到至少 1200 bytes，用來防放大攻擊並確認路徑至少能承載這個大小。

| Long packet type | TT | 用途 | 加密金鑰 |
|---|---|---|---|
| Initial | `00` | ClientHello／ServerHello | 由 client 選的 DCID 推導，路上任何人都算得出來 |
| 0-RTT | `01` | 交握完成前的應用資料 | 上次連線的 resumption 秘密 |
| Handshake | `10` | TLS 交握的其餘訊息 | handshake 金鑰 |
| Retry | `11` | 要求 client 帶 token 重來 | 不加密，只有完整性標籤 |
| Version Negotiation | Version＝0 | server 不支援 client 的版本 | 不加密 |

| Frame | type | 作用 |
|---|---|---|
| PADDING／PING | 0x00／0x01 | 撐大封包／要求回 ACK |
| ACK | 0x02–0x03 | 回報收到的 packet number 範圍（0x03 多帶 ECN 計數） |
| RESET_STREAM／STOP_SENDING | 0x04／0x05 | 中止單一 stream |
| CRYPTO | 0x06 | 帶 TLS 交握訊息 |
| NEW_TOKEN | 0x07 | 下次連線用的位址驗證 token |
| STREAM | 0x08–0x0f | 應用資料；低三位是 OFF、LEN、FIN |
| MAX_DATA／MAX_STREAM_DATA／MAX_STREAMS | 0x10／0x11／0x12–0x13 | 流量控制 |
| NEW_CONNECTION_ID／RETIRE_CONNECTION_ID | 0x18／0x19 | 發放與回收 connection ID |
| PATH_CHALLENGE／PATH_RESPONSE | 0x1a／0x1b | 驗證新路徑（migration） |
| CONNECTION_CLOSE | 0x1c–0x1d | 關閉連線 |
| HANDSHAKE_DONE | 0x1e | server 確認交握完成 |

stream ID 的最低兩位編碼發起者與方向：`00` client 雙向（0、4、8…，HTTP/3 的請求）、`01` server 雙向、`10` client 單向、`11` server 單向。詳見第 13 章 13.7 節。

## C.12 HTTP/1.1 訊息

```text
 請求
 ┌──────────────────────────────────────────────────────────────┐
 │ method ␠ request-target ␠ HTTP-version ␍␊                    │  ← request line，各用一個空格隔開
 │ field-name ":" OWS field-value OWS ␍␊                        │  ← 零到多個 header
 │ …                                                            │
 │ ␍␊                                                           │  ← 空行：header 結束
 │ body（長度由 Content-Length 或 chunked 決定）                │
 └──────────────────────────────────────────────────────────────┘
 例：POST /bookings?src=web HTTP/1.1␍␊ Host: api.shengsheng.example␍␊
     Content-Type: application/json␍␊ Content-Length: 19␍␊ ␍␊ {"lesson":"ja-101"}

 回應
 │ HTTP-version ␠ status-code ␠ reason-phrase ␍␊ │ header … │ ␍␊ │ body │
 例：HTTP/1.1 404 Not Found␍␊

 chunked body
 │ chunk-size（十六進位）[;extension] ␍␊ │ 資料（chunk-size bytes）␍␊ │ … │ 0␍␊ │ trailer … │ ␍␊ │
 （␠ = 空格 0x20，␍␊ = CRLF 0x0D 0x0A，OWS = 可有可無的空白）
```

HTTP/1.1 是文字協定：起始行、header、空行、body。header 名稱不分大小寫，名稱與冒號之間不准有空白；obs-fold（續行）已廢止。body 長度依 RFC 9112 的優先順序決定，判斷錯了就是第 20 章故事裡「卡 75 秒」的探針，或 20.9 節的 request smuggling。

| request-target 形式 | 例子 | 使用場合 |
|---|---|---|
| origin-form | `GET /bookings?src=web HTTP/1.1` | 一般請求（最常見） |
| absolute-form | `GET` 後接含 scheme 與主機的完整 URI | 送給 forward proxy（第 25 章） |
| authority-form | `CONNECT api.shengsheng.example:443 HTTP/1.1` | 只用於 CONNECT |
| asterisk-form | `OPTIONS * HTTP/1.1` | 只用於 OPTIONS |

| body 長度規則（依序，第一個成立的決定） | 結果 |
|---|---|
| HEAD 的回應，或 status 是 1xx、204、304 | 沒有 body，即使有 Content-Length |
| Transfer-Encoding 最後一個 coding 是 chunked | 依 chunked 讀到 last-chunk（優先於 Content-Length） |
| 有 Transfer-Encoding 但最後不是 chunked | 回應：讀到連線關閉；請求：回 400 |
| 有合法的 Content-Length | 剛好讀 N bytes；值不合法時請求回 400、proxy 回 502 |
| 都沒有 | 請求：body 長度 0；回應：讀到連線關閉（連線不能重用） |

| header | 為什麼要特別記 | 詳見 |
|---|---|---|
| `Host` | HTTP/1.1 請求必備，只能一個；虛擬主機靠它 | 第 20 章 20.6 節 |
| `Content-Length` | 只能一個值；byte 數不是字元數 | 第 20 章 |
| `Transfer-Encoding` | hop-by-hop；HTTP/2 與 HTTP/3 裡出現是錯誤 | 第 20、22 章 |
| `Connection` | hop-by-hop 清單；`keep-alive`、`close`、`Upgrade` | 第 20、32 章 |
| `Upgrade` | 換協定，例如 `websocket`，成功回 101 | 第 32 章 |
| `Expect: 100-continue` | 先送 header，等 100 再送 body | 第 20 章 |
| `Set-Cookie` | 不能用逗號合併，每個 cookie 一行 | 第 21 章 |

## C.13 HTTP/2 frame 與 HTTP/3 frame

```text
 byte   0        1        2        3        4        5        6        7        8
     ┌────────┬────────┬────────┬────────┬────────┬─┬───────┬────────┬────────┬────────┐
     │      Length（24 bits）     │  Type  │ Flags  │R│   Stream Identifier（31 bits）     │
     └────────┴────────┴────────┴────────┴────────┴─┴───────┴────────┴────────┴────────┘
     ┌──────────────────────────────────────────────────────────────────────────────┐
     │                    Frame Payload（Length 個 bytes）                          │
     └──────────────────────────────────────────────────────────────────────────────┘
 例：00 00 1b │ 01 │ 05 │ 00 00 00 01  → 長度 27、HEADERS、END_STREAM|END_HEADERS、stream 1

 連線開頭：client preface = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"（24 bytes）＋ SETTINGS frame
 SETTINGS payload：重複的 { Identifier (16) │ Value (32) }，每項 6 bytes
```

每個 HTTP/2 frame 都從固定 9 bytes 開始。Length 不含這 9 bytes，預設上限 16,384，要收更大的 frame 須以 SETTINGS_MAX_FRAME_SIZE 宣告。R 位元必須為 0；stream 0 代表整條連線，用於 SETTINGS、PING、GOAWAY。client 開的 stream 用奇數。

| Type | 名稱 | stream | 常用 flags |
|---|---|---|---|
| 0x0 | DATA | 某條 stream | END_STREAM 0x1、PADDED 0x8 |
| 0x1 | HEADERS | 某條 stream | END_STREAM 0x1、END_HEADERS 0x4、PADDED 0x8、PRIORITY 0x20 |
| 0x2 | PRIORITY | 某條 stream | 已標為 deprecated |
| 0x3 | RST_STREAM | 某條 stream | payload 是 32 bits 錯誤碼 |
| 0x4 | SETTINGS | 0 | ACK 0x1（ACK 的 payload 必須為空） |
| 0x5 | PUSH_PROMISE | 某條 stream | server push 已退場 |
| 0x6 | PING | 0 | ACK 0x1；payload 固定 8 bytes |
| 0x7 | GOAWAY | 0 | payload：last-stream-id (31)＋錯誤碼 (32)＋除錯資料 |
| 0x8 | WINDOW_UPDATE | 0 或某條 stream | payload：31 bits 增量 |
| 0x9 | CONTINUATION | 某條 stream | END_HEADERS 0x4 |

| SETTINGS ID | 名稱 | 預設值 |
|---|---|---|
| 0x1 | HEADER_TABLE_SIZE | 4,096 |
| 0x2 | ENABLE_PUSH | 1（瀏覽器普遍設 0） |
| 0x3 | MAX_CONCURRENT_STREAMS | 無上限（建議至少 100） |
| 0x4 | INITIAL_WINDOW_SIZE | 65,535 |
| 0x5 | MAX_FRAME_SIZE | 16,384（最大 2^24 − 1） |
| 0x6 | MAX_HEADER_LIST_SIZE | 無上限（server 應該設） |
| 0x8 | ENABLE_CONNECT_PROTOCOL | WebSocket over HTTP/2 用（第 32 章） |

| 錯誤碼 | 名稱 | 常見場合 |
|---|---|---|
| 0x0 | NO_ERROR | GOAWAY 優雅關閉 |
| 0x1 | PROTOCOL_ERROR | 對方違反協定 |
| 0x3 | FLOW_CONTROL_ERROR | 超出視窗 |
| 0x6 | FRAME_SIZE_ERROR | frame 超過 MAX_FRAME_SIZE |
| 0x7 | REFUSED_STREAM | 保證請求完全沒被處理，可安全重送 |
| 0x8 | CANCEL | client 取消請求 |
| 0xb | ENHANCE_YOUR_CALM | 對方行為像濫用（第 22 章 22.10 節） |

```text
 HTTP/3 frame（放在 QUIC stream 上，沒有 stream ID）
 ┌──────────────┬────────────────┬───────────────────────┐
 │ Type (varint)│ Length (varint)│ Payload（Length bytes）│
 └──────────────┴────────────────┴───────────────────────┘
 例：01 03 00 00 d1 → HEADERS、長度 3、QPACK：field section prefix 00 00 ＋ static #17（:method: GET）
```

| 種類 | 名稱 | 值 |
|---|---|---|
| frame type | DATA／HEADERS | 0x00／0x01 |
| frame type | CANCEL_PUSH／SETTINGS／PUSH_PROMISE | 0x03／0x04／0x05 |
| frame type | GOAWAY／MAX_PUSH_ID | 0x07／0x0d |
| 單向 stream type | control／push | 0x00／0x01 |
| 單向 stream type | QPACK encoder／QPACK decoder | 0x02／0x03 |

HTTP/3 的請求結束由 QUIC 的 FIN 表示，不需要 END_STREAM；PING、WINDOW_UPDATE、RST_STREAM 都交給 QUIC 的 frame。詳見第 22 章 22.11、22.12 節。

## C.14 WebSocket frame

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌─┬─┬─┬─┬───────┬─┬─────────────┬───────────────────────────────┐
 │F│R│R│R│opcode │M│ Payload len │   Extended payload length     │
 │I│S│S│S│  (4)  │A│     (7)     │  (16 bits，若 len == 126)     │
 │N│V│V│V│       │S│             │  (64 bits，若 len == 127)     │
 │ │1│2│3│       │K│             │                               │
 ├─┴─┴─┴─┴───────┴─┴─────────────┴ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
 │   Extended payload length（64-bit 時的後 32 bits）            │
 ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┬───────────────────────────────┤
 │                               │  Masking-key（MASK=1 時才有） │
 ├───────────────────────────────┼───────────────────────────────┤
 │  Masking-key（續，共 32 bits）│         Payload Data          │
 ├───────────────────────────────┘                               │
 │                Payload Data（長度由上面的欄位決定）           │
 └───────────────────────────────────────────────────────────────┘
 例：81 05 48 65 6c 6c 6f           server→client 文字 "Hello"
     81 85 37 fa 21 3d 7f 9f 4d 51 58  client→server 同一句話（MASK=1，key 37fa213d）
```

FIN 表示這是一則訊息的最後一個 frame；RSV1–3 沒協商 extension 時必須為 0（`permessage-deflate` 使用 RSV1）。client 送往 server 的 frame 必須 MASK＝1，payload 的第 i 個 byte 與 key 的第 i mod 4 個 byte XOR；server 送出的 frame 不 mask。長度必須用最短編碼。

| Payload len 7-bit 值 | 實際長度在哪裡 | header 長度（不含 / 含 masking key） |
|---|---|---|
| 0–125 | 就是這個值 | 2 / 6 bytes |
| 126 | 後面 2 bytes（16-bit 無號） | 4 / 8 bytes |
| 127 | 後面 8 bytes（64-bit，最高位必須是 0） | 10 / 14 bytes |

| opcode | 名稱 | 類別 | 說明 |
|---|---|---|---|
| 0x0 | continuation | 資料 | 分片訊息的後續 frame |
| 0x1 | text | 資料 | 整則訊息必須是合法 UTF-8 |
| 0x2 | binary | 資料 | 任意 bytes |
| 0x3–0x7 | 保留 | 資料 | 收到就是協定錯誤 |
| 0x8 | close | 控制 | payload：close code (16)＋UTF-8 reason，code 見附錄 D |
| 0x9 | ping | 控制 | 要求對方回 pong（payload 原樣帶回） |
| 0xA | pong | 控制 | 回應 ping，或當單向心跳 |
| 0xB–0xF | 保留 | 控制 | 收到就是協定錯誤 |

控制 frame 的 payload 最多 125 bytes、不能分片，但可以插在一則分片訊息的中間。握手的關鍵 header：client 送 `Sec-WebSocket-Key`（base64 的 16 bytes 隨機數）與 `Sec-WebSocket-Version: 13`，server 回 101 並帶 `Sec-WebSocket-Accept`：

```text
 Sec-WebSocket-Accept = base64( SHA-1( Sec-WebSocket-Key ＋ "258EAFA5-E914-47DA-95CA-C5AB0DC85B11" ) )
 例：key dGhlIHNhbXBsZSBub25jZQ== → accept s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

聲聲 Live 的 subprotocol 是 `ss-chat.v1`／`v2`／`v3`，聊天訊息上限 64 KiB、白板 1 MiB；詳見第 32 章。

## C.15 RTP

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───┬─┬─┬───────┬─┬─────────────┬───────────────────────────────┐
 │ V │P│X│  CC   │M│     PT      │       Sequence Number (16)    │  bytes 0-3
 │(2)│ │ │  (4)  │ │     (7)     │                               │
 ├───┴─┴─┴───────┴─┴─────────────┴───────────────────────────────┤
 │                        Timestamp (32)                         │  bytes 4-7
 ├───────────────────────────────────────────────────────────────┤
 │          SSRC：Synchronization Source identifier (32)         │  bytes 8-11
 ├───────────────────────────────────────────────────────────────┤
 │          CSRC list：0～15 個，每個 32 bit（CC 決定個數）      │  bytes 12-
 ├───────────────────────────────┬───────────────────────────────┤
 │ 若 X=1：profile (16)，例 0xBEDE│ length (16，單位 32-bit word) │
 ├───────────────────────────────┴───────────────────────────────┤
 │          header extension 資料（例如音量、傳輸序號、mid）     │
 ├───────────────────────────────────────────────────────────────┤
 │          payload（codec 資料，依 payload format 切好）        │
 │          若 P=1，結尾有 padding，最後一個 byte 是 padding 長度 │
 └───────────────────────────────────────────────────────────────┘
 one-byte header extension 元素（profile 0xBEDE）：│ ID (4) │ L (4) = 長度−1 │ 資料 L+1 bytes │
```

RTP 固定 header 12 bytes。V 永遠是 2，所以第一個 byte 落在 128–191。WebRTC 用 SRTP：payload 加密、整個封包被認證，但 header 本身不加密，所以抓到加密的流量仍能分析序號、timestamp 與 SSRC。

| 欄位 | 位元數 | 每個封包怎麼變 | 接收端用它做什麼 | 詳見 |
|---|---|---|---|---|
| V | 2 | 固定 2 | 和同 port 上的 STUN、DTLS 分流 | 第 34、36 章 |
| P、X、CC | 1、1、4 | 依需要 | 找出 payload 的起點與終點 | 第 34 章 |
| M | 1 | 視訊：frame 的最後一包；音訊：靜音後第一包 | 判斷 frame 到齊、調整 jitter buffer | 第 34 章 |
| PT | 7 | 同一串流通常固定 | 依 SDP 的 `a=rtpmap` 對應 codec | 第 34、35 章 |
| Sequence | 16 | 每包加 1，初始值隨機，會回繞 | 偵測遺失、亂序；延伸序號＝圈數 × 65536＋序號 | 第 34 章 |
| Timestamp | 32 | 依媒體時鐘前進，同一 frame 相同 | 播放時刻、jitter、唇音同步 | 第 34 章 |
| SSRC | 32 | 同一串流固定，隨機產生 | 分辨串流、對應 RTCP 回報 | 第 34、35 章 |
| CSRC | 0～15 × 32 | mixer 才填 | 顯示混音裡有哪些講者 | 第 34 章 |

| 媒體 | clock rate | 每包或每 frame 的 timestamp 增量 | PT（本書範例） |
|---|---|---|---|
| Opus | 一律 48,000（`opus/48000/2`） | 20 ms 一包 → 960 | 111（動態） |
| G.711 μ-law／A-law | 8,000 | 20 ms 一包 → 160 | 0／8（靜態） |
| 視訊（VP8、VP9、H.264、AV1） | 一律 90,000 | 30 fps → 3000 | 96、98、102、45（動態） |

PT 96–127 是動態編號，每場 session 由 SDP 決定，不能寫死。rtcp-mux 下 RTP 不能用 64–95 的 PT，原因是 M＝1 時第二個 byte 會和 RTCP 的 200–204 撞在一起（C.16）。

## C.16 RTCP Sender Report

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───┬─┬─────────┬───────────────┬───────────────────────────────┐
 │V=2│P│ RC (5)  │  PT=200 (SR)  │   length（32-bit word 數 - 1）│  header
 ├───┴─┴─────────┴───────────────┴───────────────────────────────┤
 │                     SSRC of sender (32)                       │
 ╞═══════════════════════════════════════════════════════════════╡
 │            NTP timestamp, most significant word（秒）         │  sender info
 │            NTP timestamp, least significant word（秒的小數）  │  （20 bytes）
 │            RTP timestamp（與上面的 NTP 是同一瞬間）           │
 │            sender's packet count (32)                         │
 │            sender's octet count (32，只算 payload)            │
 ╞═══════════════════════════════════════════════════════════════╡
 │            SSRC_1（這個 block 在報告哪一條串流）              │  report block
 ├───────────────┬───────────────────────────────────────────────┤  （每個 24 bytes，
 │ fraction lost │      cumulative number of packets lost (24)   │    RR 也用同一格式）
 │      (8)      │      （有號數）                               │
 ├───────────────┴───────────────────────────────────────────────┤
 │       extended highest sequence number received (32)          │
 │       interarrival jitter (32，單位：timestamp tick)          │
 │       last SR timestamp：LSR (32，NTP 的中間 32 bit)          │
 │       delay since last SR：DLSR (32，單位 1/65536 秒)         │
 └───────────────────────────────────────────────────────────────┘
   SR 長度 = 28 bytes ＋ 24 × RC；length 欄位 = 總長 ÷ 4 − 1（例：RC=1 → 52 bytes → length 12）
```

SR 是有在送媒體的參與者送的，上半部的 sender info 給出「NTP 牆上時間 ↔ RTP 媒體時間」的對照點，接收端靠它做唇音同步。report block 是對某一條串流的接收品質報告，RR（PT 201）只有 header 加這些 block。RTCP 通常以複合封包送出，例如 SR 後面緊接 SDES。

| 欄位 | 意義與計算 | 詳見 |
|---|---|---|
| RC | 後面有幾個 report block（0–31） | 第 34 章 |
| fraction lost | 上次報告以來的遺失比例 × 256（8 bit 定點數） | 第 34 章 |
| cumulative lost | 從頭累計的遺失數，24 bit 有號（重複封包可讓它變負） | 第 34 章 |
| extended highest seq | 高 16 bit 是回繞圈數，低 16 bit 是最大序號 | 第 34 章 |
| interarrival jitter | J ← J ＋ (\|D\| − J) / 16，單位是 timestamp tick | 第 34 章 34.9 節 |
| LSR／DLSR | RTT ＝ 收到 RR 的時刻 − LSR − DLSR | 第 34 章 34.9 節 |

| PT | 名稱 | 內容 | 詳見 |
|---|---|---|---|
| 200 | SR | sender info＋report blocks | 第 34 章 |
| 201 | RR | report blocks | 第 34 章 |
| 202 | SDES | CNAME：同一參與者的音訊與視訊共用 | 第 34、35 章 |
| 203 | BYE | 這個 SSRC 不再送了 | 第 34 章 |
| 205／206 | RTPFB／PSFB | NACK、TWCC／PLI、FIR 等即時回饋 | 第 37 章 |

## C.17 STUN

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───┬───────────────────────────┬───────────────────────────────┐
 │0 0│   STUN Message Type (14)  │      Message Length (16)      │  bytes 0-3
 ├───┴───────────────────────────┴───────────────────────────────┤
 │              Magic Cookie (32) ＝ 0x2112A442                  │  bytes 4-7
 ├───────────────────────────────────────────────────────────────┤
 │                     Transaction ID (96)                       │  bytes 8-19
 ├───────────────────────────────────────────────────────────────┤
 │       Attributes（TLV，每個都補齊到 4 bytes 的倍數）          │  bytes 20-
 └───────────────────────────────────────────────────────────────┘

 Message Type 的 14 bits（class 的兩個 bit 插在 method 中間）：
   13  12  11  10   9   8   7   6   5   4   3   2   1   0
 ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
 │M11│M10│M9 │M8 │M7 │C1 │M6 │M5 │M4 │C0 │M3 │M2 │M1 │M0 │
 └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
   C1 C0：00 request　01 indication　10 success response　11 error response

 屬性 TLV：│ Type (16) │ Length (16，不含補齊) │ Value … │ 補 0 到 4 的倍數 │

 XOR-MAPPED-ADDRESS（type 0x0020）：
 │ Reserved 0 (8) │ Family (8)：01 IPv4、02 IPv6 │ X-Port (16) = port ⊕ 0x2112 │
 │ X-Address：IPv4 = 位址 ⊕ 0x2112A442；IPv6 = 位址 ⊕（magic cookie ‖ transaction ID）│
 例：198.51.100.23:50000 → X-Port e2 42、X-Address e7 21 c0 55
```

STUN header 固定 20 bytes，最前面兩個 bit 永遠是 0，所以第一個 byte 是 0–3。Message Length 不含 header，最後兩個 bit 一定是 0。Transaction ID 必須用密碼學安全的亂數產生。UDP 上 STUN 自己重傳，依規格預設值（初始 RTO 500 ms、最多送 7 次）約 39.5 秒才宣告失敗。STUN 與 TURN 常用 UDP／TCP 3478，TLS 預設 5349（聲聲 Live 的 TURN 另開 TLS 443）。

| method | 值 | request | success | error | indication | 用在哪裡 |
|---|---|---|---|---|---|---|
| Binding | 0x001 | 0x0001 | 0x0101 | 0x0111 | 0x0011 | 問公網位址、ICE 連線檢查、consent |
| Allocate | 0x003 | 0x0003 | 0x0103 | 0x0113 | 無 | TURN：要中繼位址 |
| Refresh | 0x004 | 0x0004 | 0x0104 | 0x0114 | 無 | TURN：延長或刪除 allocation |
| Send／Data | 0x006／0x007 | 無 | 無 | 無 | 0x0016／0x0017 | TURN：轉送封包 |
| CreatePermission | 0x008 | 0x0008 | 0x0108 | 0x0118 | 無 | TURN：允許某個 peer IP |
| ChannelBind | 0x009 | 0x0009 | 0x0109 | 0x0119 | 無 | TURN：綁定 4 bytes 的 channel |

| 屬性 | type | 用途 |
|---|---|---|
| USERNAME | 0x0006 | ICE 中是「對方 ufrag:自己 ufrag」 |
| MESSAGE-INTEGRITY | 0x0008 | 20 bytes HMAC-SHA1；ICE 金鑰是對方的 `ice-pwd` |
| ERROR-CODE | 0x0009 | 例如 401、438、487 |
| REALM／NONCE | 0x0014／0x0015 | TURN 長期憑證挑戰 |
| XOR-MAPPED-ADDRESS | 0x0020 | 伺服器看到的來源位址 |
| PRIORITY／USE-CANDIDATE | 0x0024／0x0025 | ICE：prflx 優先序／提名 |
| FINGERPRINT | 0x8028 | CRC-32 ⊕ 0x5354554E，必須是最後一個屬性 |
| ICE-CONTROLLED／ICE-CONTROLLING | 0x8029／0x802A | ICE 角色與 64 bit tie-breaker |

type 0x0000–0x7FFF 是 comprehension-required（看不懂回 420），0x8000–0xFFFF 可略過。屬性順序固定：其他屬性 → MESSAGE-INTEGRITY → FINGERPRINT，計算兩者時 Message Length 都要假裝已包含該屬性。TURN 的 ChannelData 不是 STUN 格式，而是 `channel number (16)＋length (16)＋data`，channel number 在 0x4000–0x4FFF，所以第一個 byte 是 64–79。詳見第 36 章。

## C.18 SRT data 與 control packet

```text
 資料封包（F=0）
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌─┬─────────────────────────────────────────────────────────────┐
 │0│              Packet Sequence Number (31)                    │  bytes 0-3
 ├─┴─┬─┬───┬─┬───────────────────────────────────────────────────┤
 │PP │O│KK │R│              Message Number (26)                  │  bytes 4-7
 ├───┴─┴───┴─┴───────────────────────────────────────────────────┤
 │                       Timestamp (32, µs)                      │  bytes 8-11
 ├───────────────────────────────────────────────────────────────┤
 │                 Destination SRT Socket ID (32)                │  bytes 12-15
 ├───────────────────────────────────────────────────────────────┤
 │  Payload（live 模式預設 1316 bytes = 7 個 188-byte TS 封包）  │
 └───────────────────────────────────────────────────────────────┘

 控制封包（F=1）
 ┌─┬─────────────────────────────┬───────────────────────────────┐
 │1│    Control Type (15)        │          Subtype (16)         │  bytes 0-3
 ├─┴─────────────────────────────┴───────────────────────────────┤
 │                 Type-specific Information (32)                │  bytes 4-7
 ├───────────────────────────────────────────────────────────────┤
 │                       Timestamp (32, µs)                      │  bytes 8-11
 ├───────────────────────────────────────────────────────────────┤
 │                 Destination SRT Socket ID (32)                │  bytes 12-15
 ├───────────────────────────────────────────────────────────────┤
 │       Control Information Field（例如 NAK 的遺失清單）        │
 └───────────────────────────────────────────────────────────────┘
 NAK 遺失清單：單一序號直接寫；連續區間寫成「起點 | 0x80000000」接「終點」
```

SRT 跑在 UDP 上，header 固定 16 bytes，第一個 bit 區分資料與控制。Destination Socket ID 是收方在 handshake 時分配的連線編號，讓一個 UDP port（聲聲 Live 的 ingest 用 9000）同時服務多條推流。1316 bytes 的 payload 加上 16＋8＋20 bytes 的 header，整個 IPv4 封包 1360 bytes，經過 MTU 1420 的 WireGuard 隧道也不必分片。

| 欄位 | 大小 | 值與意義 |
|---|---|---|
| Packet Sequence Number | 31 bits | 每個資料封包加 1，收方靠它發現跳號 |
| PP | 2 bits | 封包在訊息中的位置：10 第一個、00 中間、01 最後、11 獨立一則（live 模式） |
| O | 1 bit | 是否要求依序交付 |
| KK | 2 bits | 00 沒加密、01 偶數金鑰、10 奇數金鑰（金鑰輪替） |
| R | 1 bit | 重傳的封包 |
| Message Number | 26 bits | 訊息編號 |
| Timestamp | 32 bits | 相對於連線開始的微秒數，TSBPD 依此決定交付時間 |
| Destination Socket ID | 32 bits | 收方的連線編號 |

| Control Type | 名稱 | 用途 |
|---|---|---|
| 0x0000 | HANDSHAKE | 建立連線、協商 latency、交換金鑰與 stream ID |
| 0x0001 | KEEPALIVE | 沒有資料時約每秒一個，維持 NAT 狀態 |
| 0x0002 | ACK | 收方回報收到的序號，附 RTT 與可用 buffer |
| 0x0003 | NAK | 收方回報遺失清單，請送方重傳 |
| 0x0005 | SHUTDOWN | 結束連線 |
| 0x0006 | ACKACK | 送方確認收到 ACK，收方由此量出 RTT |
| 0x0007 | DROPREQ | 送方通知「這些封包已丟掉，不要再要」 |

設定 latency 時注意單位：libsrt 的 `SRTO_LATENCY` 是毫秒（預設 120 ms），ffmpeg srt URL 的 `latency` 參數是微秒。stream ID 的範例是 `#!::r=live/talk-1017,m=publish`。詳見第 38 章。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 2026 年 10 月查證，SRT 在 IETF 只有一份已過期的 individual draft，沒有 RFC；格式以 libsrt 的實作與其文件為準。

## C.19 JWT：header 與 claims

```text
 base64url(header JSON) . base64url(payload JSON) . base64url(signature)
 └──────────────── signing input ────────────────┘
 header 與 payload 都以 eyJ 開頭（'{"' 的 base64）；base64url：+ → -、/ → _、省略結尾的 =

 第 27 章的 access token（payload 解碼後）：
 {"alg":"ES256","typ":"at+jwt","kid":"es-2026-10"}
 {"iss":"https://auth.shengsheng.example","sub":"teacher:1024","aud":"api.shengsheng.example",
  "iat":1790000000,"exp":1790000300,"scope":"schedule:write"}
```

JWT 是 JWS 的 compact 格式：三段 base64url，以句點分隔，簽章保護前兩段的**文字**。payload 任何人都能解開，JWT 本身不加密；需要保密要用 JWE（五段）或改用 opaque token。驗證的固定順序是第 27 章 27.5 節的 ① 到 ⑩：先只讀 header 去比對設定，簽章通過之後才讀 payload。

| header 參數 | 意義 | 驗證端怎麼對待 |
|---|---|---|
| `alg` | 簽章演算法，例如 `ES256`、`RS256`、`HS256` | 只能和設定的允許清單比對（聲聲 Live 只允許 ES256）；`none` 一律拒絕 |
| `typ` | token 種類 | access token 必須是 `at+jwt`，擋下拿 ID token 冒充 |
| `kid` | 用哪一把金鑰 | 只在目前的金鑰集合（JWKS）裡查表，不拿去組路徑或網址 |
| `cty` | 內容型別 | 巢狀 JWT 才會用到，一般不接受 |
| `crit` | 必須理解的擴充參數 | 有不認得的項目就拒絕 |
| `jku`、`jwk`、`x5u`、`x5c` | 金鑰網址或直接附上的金鑰／憑證 | 不信任；金鑰只從自己設定的來源取得 |

| claim | 全名 | 意思 | 驗證者要做什麼 |
|---|---|---|---|
| `iss` | issuer | 誰簽發的 | 和設定值精確比對（聲聲 Live 是 `auth.shengsheng.example` 的 https 網址） |
| `sub` | subject | 這個 token 代表誰，例如 `teacher:1024` | 在 iss 範圍內唯一；授權判斷的主體 |
| `aud` | audience | 給誰用，字串或陣列 | 必須包含自己，例如 `api.shengsheng.example`、`rt.shengsheng.example` |
| `exp` | expiration time | 這個時間點（含）之後不得接受 | 目前時間 ≥ exp＋leeway 即拒絕（leeway 60 秒） |
| `nbf` | not before | 這個時間點之前不得接受 | 目前時間＋leeway 仍早於 nbf 即拒絕 |
| `iat` | issued at | 簽發時間 | 算 token 年齡；政策上 `exp − iat` 不超過 15 分鐘 |
| `jti` | JWT ID | 唯一編號 | 撤銷清單與防重放 |
| `scope` | （OAuth） | 以空白分隔的權限 | 步驟 ⑩ 的授權判斷，不足回 403 `insufficient_scope` |
| `client_id` | （OAuth） | 哪個 client 取得的 token | 稽核與依 client 限制 |
| `nonce`、`auth_time`、`azp`、`amr` | （OIDC ID token） | 綁定登入請求、登入時間、授權方、驗證方式 | 只在驗 ID token 時使用（第 29 章） |

| 演算法 | 類型 | 簽章大小 | 適合 |
|---|---|---|---|
| HS256 | HMAC-SHA256（對稱） | 32 bytes | 發行者與驗證者是同一個服務（本書教學用 kid `k2026-09`／`k2026-10`） |
| RS256 | RSA（2048 bit 以上） | 256 bytes（2048 bit） | 多個 API 共用發行者、與舊系統相容 |
| ES256 | ECDSA P-256 | 64 bytes | 同上，token 更短（聲聲 Live 的 access token） |

時間類 claims 的值是 NumericDate：從 1970-01-01 UTC 起算的秒數。聲聲 Live 的 access token 有效 5 分鐘、refresh token 14 天且為 opaque；token 無效回 401 並帶 `WWW-Authenticate`，權限不足回 403。

## C.20 SDP 常見行

```text
 session 層（第一個 m= 之前）          media section（每個 m= 開啟一段）
 v=0                                   m=audio 9 UDP/TLS/RTP/SAVPF 111 63 0 8 126
 o=- <sess-id> <sess-version> IN IP4 127.0.0.1   c=IN IP4 0.0.0.0
 s=-                                   a=mid:0 、a=ice-ufrag 、a=fingerprint 、a=setup …
 t=0 0                                 a=rtpmap:111 opus/48000/2 、a=fmtp:111 … 、a=rtcp-fb:111 …
 a=group:BUNDLE 0 1 2                  m=video … 、m=application 9 UDP/DTLS/SCTP webrtc-datachannel

 m 行：m=<media> <port> <proto> <fmt> …
 candidate：a=candidate:<foundation> <component> <transport> <priority> <address> <port> typ <type> [raddr <a> rport <p>]
 例（SFU，ICE-lite）：a=candidate:1 1 udp 2130706431 203.0.113.60 40000 typ host
```

SDP 是一行一個 `<type>=<value>` 的文字格式，`v=` 必須是第一行。session 層描述整場會話，每個 `m=` 開啟一個 media section，直到下一個 `m=` 為止。WebRTC 的 `c=` 與 port 9 都是佔位值，真正的位址看 ICE candidate。屬性的方向永遠是從「寫這份 SDP 的人」的角度描述。

| 行 | 層級 | 意思 | 在 WebRTC 的用法 | 詳見 |
|---|---|---|---|---|
| `v=0` | session | SDP 版本 | 固定 0，必須第一行 | 第 35 章 |
| `o=` | session | username、session id、session version、位址 | 重新協商時 version 要遞增 | 第 35 章 |
| `s=`、`t=` | session | 會話名稱、時間 | 固定 `s=-`、`t=0 0` | 第 35 章 |
| `c=` | 兩者皆可 | 連線位址 | 佔位值 `IN IP4 0.0.0.0` | 第 35 章 |
| `b=AS:`／`b=TIAS:` | 兩者皆可 | 頻寬上限（kbps／bps） | 可選；改用 `setParameters` 比 munging 好 | 第 35 章 |
| `m=` | media | 媒體、port、proto、格式清單 | proto `UDP/TLS/RTP/SAVPF` 或 `UDP/DTLS/SCTP` | 第 35 章 |
| `a=group:BUNDLE` | session | 哪些 mid 共用一條傳輸 | 第一個 mid 是 tagged | 第 35 章 |
| `a=mid:` | media | 這一段的識別字 | answer 必須沿用 offer 的 mid | 第 35 章 |
| `a=ice-ufrag:`／`a=ice-pwd:` | 兩者皆可 | ICE 帳密（至少 4／22 字元） | STUN 檢查的 USERNAME 與 HMAC 金鑰 | 第 35、36 章 |
| `a=ice-options:trickle` | 兩者皆可 | 支援 trickle ICE | candidate 之後經 signaling 補送 | 第 35、36 章 |
| `a=ice-lite` | session | 只做 ICE-lite | 聲聲 Live 的 SFU | 第 35、37 章 |
| `a=candidate:`／`a=end-of-candidates` | media | 候選位址／收集完畢 | type 為 host、srflx、prflx、relay | 第 36 章 |
| `a=fingerprint:sha-256` | 兩者皆可 | DTLS 憑證雜湊 | 信任的根據；SDP 被改就擋不住中間人 | 第 35、36 章 |
| `a=setup:` | 兩者皆可 | DTLS 角色 | offer 為 `actpass`，answer 選 `active` 或 `passive`（SFU 回 `passive`） | 第 35 章 |
| `a=rtcp-mux`／`a=rtcp-rsize` | media | RTP 與 RTCP 共用 port／精簡 RTCP | WebRTC 要求 rtcp-mux | 第 34、35 章 |
| `a=rtpmap:<pt> <codec>/<clock>[/<ch>]` | media | PT 對應的 codec | 例：`111 opus/48000/2`、`96 VP8/90000` | 第 35 章 |
| `a=fmtp:<pt> …` | media | codec 參數 | 例：`apt=96`（rtx）、`packetization-mode=1` | 第 35 章 |
| `a=rtcp-fb:<pt> …` | media | 支援的 RTCP 回饋 | `nack`、`nack pli`、`ccm fir`、`transport-cc` | 第 35、37 章 |
| `a=extmap:<id> <uri>` | media | RTP header extension 的 ID | 例：`ssrc-audio-level`、`sdes:mid` | 第 34、35 章 |
| `a=sendrecv`／`sendonly`／`recvonly`／`inactive` | media | 方向 | 沒寫時預設 sendrecv | 第 35 章 |
| `a=msid:<stream> <track>` | media | 對應 MediaStream 與 track | 學生 `cam-0457`、SFU 轉送老師用 `teacher-1024` | 第 35 章 |
| `a=ssrc:<ssrc> cname:<cname>` | media | 預告 SSRC 與 CNAME | SFU 的 SSRC 從 30000 起、cname `sfu-60` | 第 35 章 |
| `a=ssrc-group:FID` | media | 媒體 SSRC 與重傳 SSRC 的配對 | rtx 串流 | 第 35 章 |
| `a=rid:`／`a=simulcast:` | media | simulcast 各層 | 720p／360p／180p 三層 | 第 37 章 |
| `a=sctp-port:`／`a=max-message-size:` | media | data channel 的 SCTP port／單一訊息上限 | 慣例 5000；沒寫時上限 64 KiB | 第 35、36 章 |

## C.21 WSGI environ 必要鍵

```text
 POST /teachers/%E7%BE%8E%E5%92%B2/reviews?lang=ja HTTP/1.1
   │      │                                 │       └──► SERVER_PROTOCOL = "HTTP/1.1"
   │      │                                 └──────────► QUERY_STRING    = "lang=ja"（未解碼）
   │      └────────────────────────────────────────────► PATH_INFO       = 已 percent-decode（latin-1 字串）
   └───────────────────────────────────────────────────► REQUEST_METHOD  = "POST"
 Host: api.shengsheng.example ──────────────────────────► HTTP_HOST
 Content-Type／Content-Length ──────────────────────────► CONTENT_TYPE／CONTENT_LENGTH（沒有 HTTP_ 前綴）
 X-Request-Id: 7f3c9a2e ────────────────────────────────► HTTP_X_REQUEST_ID（轉大寫、- 變 _）
 body ──────────────────────────────────────────────────► wsgi.input（只能讀 CONTENT_LENGTH 個 bytes）
 TCP 對端 ──────────────────────────────────────────────► REMOTE_ADDR（CGI 變數，PEP 3333 未強制）
```

WSGI（PEP 3333）的 environ 沿用 CGI 的變數名稱，再加上 `wsgi.*` 鍵。下表是 PEP 3333 規定必須（或允許為空字串時應該）存在的鍵。所有 CGI 變數與 `HTTP_*` 的值都是 native `str`，由原始 bytes 以 latin-1 解碼；body 一律是 bytes。

| 鍵 | 例子 | 說明 |
|---|---|---|
| `REQUEST_METHOD` | `"POST"` | 一定存在、不得為空 |
| `SCRIPT_NAME` | `""` 或 `"/ops"` | app 的掛載前綴；掛在根目錄時為空字串 |
| `PATH_INFO` | `"/teachers/…"` | 掛載點之後的路徑，已 percent-decode；可為空 |
| `QUERY_STRING` | `"lang=ja&lang=en"` | `?` 之後的原始字串；可為空或不存在 |
| `CONTENT_TYPE`、`CONTENT_LENGTH` | `"application/json"`、`"12"` | 可為空或不存在；沒有 `HTTP_` 前綴 |
| `SERVER_NAME`、`SERVER_PORT` | `"api.shengsheng.example"`、`"8000"` | 一定存在；組 URL 時以 `HTTP_HOST` 優先 |
| `SERVER_PROTOCOL` | `"HTTP/1.1"` | client 使用的協定版本 |
| `HTTP_*` | `HTTP_COOKIE`、`HTTP_X_REQUEST_ID` | 其他所有 request header |
| `wsgi.version` | `(1, 0)` | PEP 3333 仍是 `(1, 0)` |
| `wsgi.url_scheme` | `"http"` 或 `"https"` | 這一跳的 scheme；TLS 在 LB 終結時是 `http`（要靠 ProxyFix） |
| `wsgi.input` | 類檔案物件 | request body，只讀 bytes、只能讀一次 |
| `wsgi.errors` | 文字串流 | 錯誤訊息，通常接到 server 的 error log |
| `wsgi.multithread`、`wsgi.multiprocess` | `True`／`False` | 同一個 app 物件是否可能被多個 thread／process 同時呼叫 |
| `wsgi.run_once` | `False` | 是否每個 process 只處理一個請求 |

選用的鍵：`wsgi.file_wrapper`（server 提供的高效送檔，第 41 章 41.6 節）、`REMOTE_ADDR`（在 nginx 後面永遠是 nginx 的位址）。middleware 放進 environ 的自訂鍵要加前綴，聲聲 Live 用 `shengsheng.`。`start_response(status, headers)` 的 status 是 `"200 OK"` 這樣的字串，headers 是 `(name, value)` 的 list，不能放 `Connection`、`Transfer-Encoding` 這類 hop-by-hop header。

## C.22 ASGI scope 與事件

```text
 async def app(scope, receive, send):
     │         │      │        └─ await send(event)：app 把事件交給 server
     │         │      └────────── await receive()：向 server 要下一個事件
     │         └───────────────── dict：這條連線或這個請求的靜態資訊，type 決定其餘欄位
     └─────────────────────────── 每一個新的連線範圍呼叫一次

 http：     receive → http.request(body, more_body)… │ send → http.response.start → http.response.body…
 websocket：receive → websocket.connect │ send → websocket.accept │ receive／send 訊息 … │ websocket.disconnect
 lifespan： receive → lifespan.startup │ send → lifespan.startup.complete … lifespan.shutdown … .complete
```

ASGI（core 3.0）把 app 定義成 async callable。scope 是靜態資訊，事件是動態的對話；所有事件都是帶 `type` 鍵的 dict。和 WSGI 最大的差別是 header 與 query 以 bytes 保留原樣，並有 `http.disconnect`、WebSocket 與 lifespan。

| scope type | 一次呼叫涵蓋的範圍 | receive 收到 | send 送出 |
|---|---|---|---|
| `http` | 一個 HTTP 請求與回應 | `http.request`、`http.disconnect` | `http.response.start`、`http.response.body` |
| `websocket` | 一條 WebSocket 連線 | `websocket.connect`、`websocket.receive`、`websocket.disconnect` | `websocket.accept`、`websocket.send`、`websocket.close` |
| `lifespan` | 一個 server process 的一生 | `lifespan.startup`、`lifespan.shutdown` | `lifespan.startup.complete`／`.failed`、`lifespan.shutdown.complete`／`.failed` |

| http scope 欄位 | 型別與範例 | 對應的 WSGI environ | 注意事項 |
|---|---|---|---|
| `type` | `"http"` | 無 | 決定其餘欄位 |
| `http_version` | `"1.1"`、`"2"` | `SERVER_PROTOCOL` | 不含 `HTTP/` 前綴 |
| `method` | `"POST"` | `REQUEST_METHOD` | 大寫 |
| `scheme` | `"https"` | `wsgi.url_scheme` | 經過 proxy 時看 server 是否信任 `X-Forwarded-Proto` |
| `path` | `"/teachers/美咲"` | `PATH_INFO` | 已 percent-decode 並以 UTF-8 解碼 |
| `raw_path` | `b"/teachers/%E7%BE%8E%E5%92%B2"` | 無 | 原始 bytes |
| `query_string` | `b"lang=ja&page=2"` | `QUERY_STRING` | bytes，不解碼、不含 `?` |
| `root_path` | `"/rt"` | `SCRIPT_NAME` | 掛在子路徑下時使用 |
| `headers` | `[(b"host", b"rt.shengsheng.example"), ...]` | `HTTP_*` | bytes 二元組 list，保留順序與重複，名稱小寫 |
| `client`／`server` | `("198.51.100.23", 51514)` | `REMOTE_ADDR`、`SERVER_NAME` | 在 proxy 後面時是 proxy 的位址 |
| `state` | dict | 無 | lifespan 放進去的共享資源的淺複本 |

websocket scope 有和 http 相同的 `path`、`query_string`、`headers`、`client` 等欄位，另有 `subprotocols`：client 在 `Sec-WebSocket-Protocol` 列出的候選清單，例如 `["ss-chat.v1"]`。

| 事件 type | 方向 | 欄位 | 規則 |
|---|---|---|---|
| `http.request` | server → app | `body`（bytes）、`more_body`（bool） | 預設 `b""`、`False`；body 可分多次到 |
| `http.disconnect` | server → app | 無 | client 斷線，或回應送完後再 receive |
| `http.response.start` | app → server | `status`（int）、`headers`、`trailers`（bool） | 必須第一個送；header 名稱小寫 |
| `http.response.body` | app → server | `body`、`more_body` | 可多次；`more_body: False` 代表結束 |
| `websocket.connect` | server → app | 無 | 交握請求到了，app 在這裡檢查 Origin 與 ticket |
| `websocket.accept` | app → server | `subprotocol`、`headers` | server 收到才回 101 |
| `websocket.receive` | server → app | `text` 或 `bytes`（恰一個有值） | 一則完整訊息，分片已重組 |
| `websocket.send` | app → server | `text` 或 `bytes` | 必須在 accept 之後 |
| `websocket.close` | app → server | `code`（預設 1000）、`reason` | accept 前送出等於拒絕，server 回 HTTP 403 |
| `websocket.disconnect` | server → app | `code`、`reason` | client 沒給 code 時填 1005；之後再 send 應拋錯 |
| `lifespan.startup`／`lifespan.shutdown` | server → app | 無 | 建立與釋放連線池等共享資源 |
| `lifespan.*.complete`／`.failed` | app → server | `.failed` 帶 `message` | production 用 `--lifespan on`，失敗就讓 server 啟動失敗 |

> [!note] 2026 現況
> 截至 2026 年 10 月，依 2026 年 10 月查證，ASGI core 版本是 3.0，HTTP 與 WebSocket spec 版本是 2.5：2.1 起 `websocket.accept` 可帶 `headers`、2.3 起 `websocket.close` 帶 `reason`、2.4 起在已關閉的連線上送資料應拋錯、2.5 起 `websocket.disconnect` 帶 `reason`。第 42 章的事件表依此版本。

## C.23 用 struct 驗證 header 長度

自己寫解析程式時，第一個要對的是長度與偏移。下面的程式把本附錄每個固定 header 寫成 `struct` 格式字串，用 `struct.calcsize` 驗證長度；再拿正文出現過的範例值組出 bytes，確認和各章印出的一致。`"!"` 表示 network byte order 且不做對齊補齊；24-bit 的欄位（HTTP/2 的 Length、TLS handshake 的 length）`struct` 沒有對應的整數格式，先用 `3s` 佔位，再以 `int.from_bytes` 轉換。

```python
import ipaddress
import struct

# 每個格式的固定部分，用 struct 格式字串描述；"!" = network byte order、不補齊
LAYOUTS = {
    "Ethernet header":       ("!6s6sH", 14),
    "802.1Q tag":            ("!HH", 4),
    "ARP (Ethernet/IPv4)":   ("!HHBBH6s4s6s4s", 28),
    "IPv4 (no options)":     ("!BBHHHBBH4s4s", 20),
    "IPv6 fixed header":     ("!IHBB16s16s", 40),
    "ICMP header":           ("!BBHHH", 8),
    "UDP header":            ("!HHHH", 8),
    "TCP (no options)":      ("!HHIIBBHHH", 20),
    "DNS header":            ("!HHHHHH", 12),
    "TLS record header":     ("!BHH", 5),
    "TLS handshake header":  ("!B3s", 4),
    "HTTP/2 frame header":   ("!3sBBI", 9),
    "RTP fixed header":      ("!BBHII", 12),
    "RTCP SR (no blocks)":   ("!BBHI5I", 28),
    "RTCP report block":     ("!IB3s4I", 24),
    "STUN header":           ("!HHI12s", 20),
    "SRT header":            ("!4I", 16),
}
for name, (fmt, expected) in LAYOUTS.items():
    size = struct.calcsize(fmt)
    assert size == expected, (name, size)
    print(f"{name:<22}{fmt:<17}{size:>3} bytes")


def csum16(data: bytes) -> int:
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


# 1. 第 2 章的 IPv4 header：checksum 應為 0x6fe7
ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 40, 0xB2A0, 0x4000, 64, 17, 0,
                 ipaddress.IPv4Address("10.20.1.15").packed,
                 ipaddress.IPv4Address("10.20.3.7").packed)
ip = ip[:10] + struct.pack("!H", csum16(ip)) + ip[12:]
ver_ihl, *_ = struct.unpack("!B", ip[:1])
print("IPv4    ", ip.hex(" "), f"→ version {ver_ihl >> 4}、IHL {ver_ihl & 15}×4 = {(ver_ihl & 15) * 4} bytes")
assert ip[10:12] == b"\x6f\xe7" and csum16(ip) == 0

# 2. 第 22 章的 HTTP/2 frame header：長度 27、HEADERS、END_STREAM|END_HEADERS、stream 1
h2 = struct.pack("!3sBBI", (27).to_bytes(3, "big"), 0x1, 0x1 | 0x4, 1 & 0x7FFF_FFFF)
length, ftype, flags, sid = int.from_bytes(h2[:3], "big"), h2[3], h2[4], struct.unpack("!I", h2[5:])[0]
print("HTTP/2  ", h2.hex(" "), f"→ len {length}、type {ftype}、flags 0x{flags:02x}、stream {sid & 0x7FFF_FFFF}")
assert h2.hex() == "00001b010500000001"

# 3. 第 32 章的 WebSocket frame：server 送出 FIN=1 text "Hello"
ws = bytes([0x80 | 0x1, len(b"Hello")]) + b"Hello"
print("WS      ", ws.hex(" "), f"→ FIN {ws[0] >> 7}、opcode {ws[0] & 15}、MASK {ws[1] >> 7}、len {ws[1] & 127}")
assert ws.hex() == "810548656c6c6f"


# 4. 第 13 章的 QUIC varint：0x7bbd → 15293；37 的最短編碼是 0x25
def varint_decode(buf: bytes) -> tuple[int, int]:
    n = 1 << (buf[0] >> 6)
    return int.from_bytes(bytes([buf[0] & 0x3F]) + buf[1:n], "big"), n


print("varint   7b bd       →", varint_decode(bytes.fromhex("7bbd")), "（值、bytes 數）")
assert varint_decode(bytes.fromhex("7bbd")) == (15293, 2) and varint_decode(b"\x25") == (37, 1)

# 5. 第 34 章美咲的 Opus 封包：V=2、PT 111、SSRC 0x5EED0034
rtp = struct.pack("!BBHII", 2 << 6, 111, 4660, 960 * 10, 0x5EED0034)
b0, b1 = rtp[0], rtp[1]
print("RTP     ", rtp.hex(" "), f"→ V {b0 >> 6}、M {b1 >> 7}、PT {b1 & 127}")
assert b0 >> 6 == 2 and b1 & 127 == 111

# 6. 第 36 章 STUN Binding success 的 XOR-MAPPED-ADDRESS：198.51.100.23:50000
MAGIC = 0x2112A442
addr = int(ipaddress.IPv4Address("198.51.100.23"))
xattr = struct.pack("!HHBBHI", 0x0020, 8, 0, 0x01, 50000 ^ (MAGIC >> 16), addr ^ MAGIC)
stun = struct.pack("!HHI12s", 0x0101, len(xattr), MAGIC, bytes(range(12))) + xattr
print("STUN    ", stun[:4].hex(" "), "…", xattr.hex(" "))
assert stun[0] >> 6 == 0 and xattr[-4:].hex() == "e721c055" and xattr[6:8].hex() == "e242"

# 7. 第 38 章 SRT 資料封包：F=0、PP=11（獨立訊息）、KK=00、payload 1316 bytes
srt = struct.pack("!4I", 1001 & 0x7FFF_FFFF, (0b11 << 30) | 1, 20_000, 0x1F2E3D4C) + bytes(1316)
w0, w1 = struct.unpack("!II", srt[:8])
print("SRT     ", srt[:16].hex(" "), f"→ F {w0 >> 31}、seq {w0 & 0x7FFF_FFFF}、PP {w1 >> 30:02b}，共 {len(srt)} bytes")
assert w0 >> 31 == 0 and len(srt) + 8 + 20 == 1360   # 加 UDP 與 IPv4 header 正好是第 38 章的 1360
```

```text
Ethernet header       !6s6sH            14 bytes
802.1Q tag            !HH                4 bytes
ARP (Ethernet/IPv4)   !HHBBH6s4s6s4s    28 bytes
IPv4 (no options)     !BBHHHBBH4s4s     20 bytes
IPv6 fixed header     !IHBB16s16s       40 bytes
ICMP header           !BBHHH             8 bytes
UDP header            !HHHH              8 bytes
TCP (no options)      !HHIIBBHHH        20 bytes
DNS header            !HHHHHH           12 bytes
TLS record header     !BHH               5 bytes
TLS handshake header  !B3s               4 bytes
HTTP/2 frame header   !3sBBI             9 bytes
RTP fixed header      !BBHII            12 bytes
RTCP SR (no blocks)   !BBHI5I           28 bytes
RTCP report block     !IB3s4I           24 bytes
STUN header           !HHI12s           20 bytes
SRT header            !4I               16 bytes
IPv4     45 00 00 28 b2 a0 40 00 40 11 6f e7 0a 14 01 0f 0a 14 03 07 → version 4、IHL 5×4 = 20 bytes
HTTP/2   00 00 1b 01 05 00 00 00 01 → len 27、type 1、flags 0x05、stream 1
WS       81 05 48 65 6c 6c 6f → FIN 1、opcode 1、MASK 0、len 5
varint   7b bd       → (15293, 2) （值、bytes 數）
RTP      80 6f 12 34 00 00 25 80 5e ed 00 34 → V 2、M 0、PT 111
STUN     01 01 00 0c … 00 20 00 08 00 01 e2 42 e7 21 c0 55
SRT      00 00 03 e9 c0 00 00 01 00 00 4e 20 1f 2e 3d 4c → F 0、seq 1001、PP 11，共 1332 bytes
```

前 17 行是長度表：每個格式字串的 `calcsize` 都等於本附錄圖中的固定長度，其中 RTCP report block 的 `B3s` 正是 fraction lost（8 bits）加 cumulative lost（24 bits）。後 7 行逐一對拍：IPv4 的 checksum 算出 `6f e7`，和第 2 章的 dump 相同；HTTP/2 的 9 bytes 與第 22 章範例一致；WebSocket 的 `81 05` 加上 "Hello" 和第 32 章引用的 RFC 6455 範例相同；varint `7b bd` 解出 15293；RTP 的第一個 byte `80` 落在 128–191、第二個 byte `6f` 是 PT 111；STUN 的 XOR-MAPPED-ADDRESS 算出第 36 章手算的 `e2 42` 與 `e7 21 c0 55`；SRT 資料封包 16＋1316＝1332 bytes，加上 UDP 與 IPv4 header 正好是第 38 章說的 1360 bytes。要延伸這段程式，可以把 C.8 的 TCP 選項或 C.9 的 DNS 名稱壓縮加進來，用第 10、14 章印出的 bytes 當作期望值。
