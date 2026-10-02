---
chapter: 8
title: ICMP、MTU 與分片
part: 1
---

# 第 8 章　ICMP、MTU 與分片

> [!abstract] 本章地圖
> **核心問題**：為什麼一條「ping 得通、小請求也正常」的連線，會在傳大東西時無聲無息地卡死？
>
> **你會學到**：
> - 看懂 ICMP 的 header 與常見訊息類型，知道哪些 ICMP 絕對不能擋
> - 說清楚 ping 的運作方式，手算 Internet checksum
> - 計算 MTU、MSS 與各種隧道封裝的額外負擔，手算 IPv4 分片的 offset 與 MF flag
> - 畫出 Path MTU Discovery 的時序，判斷 PMTUD 黑洞並用 tcpdump、ping、tracepath 證明它
> - 用 MSS clamping、MTU probing 與正確的防火牆規則修好 VPN 與隧道的 MTU 問題
>
> **前置知識**：第 2 章（封裝與 IPv4 header）、第 4 章（Ethernet frame）、第 6 章（路由與 traceroute）、第 7 章（防火牆與 security group）

## 8.1 故事：辦公室 VPN 上「只有大東西會消失」

聲聲 Live 的教研與客服團隊搬進新辦公室。為了讓同事安全地使用只開放在內網的營運後台 `ops.shengsheng.example`，阿德在辦公室路由器和雲端 VPC 之間架了一條 WireGuard site-to-site VPN：辦公室網段 10.40.0.0/24 的流量，經過加密隧道進入 VPC 的 10.20.0.0/16。啟用的第一個早上，客服群組就湧進一串奇怪的回報。

「後台登入頁可以開，搜尋學生也正常，可是『匯出本月課表』一直轉圈。」「老師的上課紀錄頁面，上半部出來了，下半部永遠在載入。」「我 ssh 進那台 server 可以登入，打 `ls` 也有反應，但 `cat` 一個大一點的 log 檔，終端機就整個凍住。」最讓人困惑的是：大家用 `ping` 測後台主機，每一個封包都有回應；從家裡、不走 VPN 連進來的同事，一切正常；上傳教材 PDF 到後台也沒問題，只有「下載大東西」會壞。

小晴被指派去查。第一個直覺是後台程式有 bug，可是同一個 API 從家裡打就是好的。第二個直覺是頻寬不夠，可是小請求很快，而且大請求不是「慢」，是「完全不動」。小晴打開瀏覽器 DevTools，看到請求停在 waiting 狀態，沒有錯誤、沒有 timeout 訊息，就只是卡著。這種「網路通、但只有大的東西會消失」的症狀，是本章的主角：**Path MTU Discovery 黑洞**（PMTUD black hole）。

阿德聽完描述，先問了一句：「最近除了 VPN，網路還改了什麼？」Rita 想了想：「上週五我把 VPC 子網的 network ACL 收緊了，只留 443 和 22，順手把 ICMP 全擋了，因為掃描器老是用 ping 探測我們的主機。」阿德點點頭：「兩個改變各自都沒錯，但合在一起就出事了。」要聽懂這句話，我們得從頭認識三件事：ICMP 是什麼、MTU 和分片怎麼運作、以及 TCP 怎麼靠 ICMP 找出一條路能走多大的封包。

```text
  辦公室 10.40.0.0/24                網際網路                    VPC 10.20.0.0/16
 ┌──────────────┐  MTU 1500  ┌────────────┐  WireGuard 隧道  ┌────────────┐  MTU 1500  ┌──────────────┐
 │ 客服電腦       │──────────►│ 辦公室路由器 │═══ wg0 MTU 1420 ═│ VPN gateway │──────────►│ 後台 server    │
 │ 10.40.0.23    │◄──────────│ (wg peer)   │══════════════════│ 10.20.0.10  │◄────╳─────│ 10.20.3.17    │
 └──────────────┘            └────────────┘                  └────────────┘   ICMP     └──────────────┘
                                                                                被 network ACL 擋掉
   上傳（電腦→server）：正常        下載小回應：正常        下載大回應（1500 bytes 封包）：卡死
```

這張拓撲圖是整章會反覆回來看的地圖。從左到右讀：辦公室電腦接在一般 Ethernet 上，網卡 MTU 是 1500；辦公室路由器把要去 VPC 的封包塞進 WireGuard 隧道，隧道介面 `wg0` 的 MTU 只有 1420，因為加密與外層 header 要占掉空間；VPC 那端的 VPN gateway 解開隧道，再用 1500 的 MTU 把封包交給後台 server。圖中標了一個「╳」：當 gateway 想告訴 server「你的封包太大」時，那則 ICMP 訊息被 Rita 新加的 ACL 規則丟掉了。最下面一行是症狀的對照：問題只出現在「server 往辦公室送大封包」這個方向，本章最後你會知道為什麼方向這麼重要。

## 8.2 ICMP：網路層的回報信差

IP 本身只負責「盡力而為」地把封包往目的地送，路上任何一台路由器都可以因為各種原因丟掉封包：找不到路由、TTL 用完、封包太大不能切。如果丟了卻什麼都不說，傳送端只能乾等。**ICMP**（Internet Control Message Protocol，網際網路控制訊息協定）就是 IP 的回報機制：路由器或主機在處理封包出問題時，回一則小訊息給原始傳送端，說明發生了什麼事。例如你連一台不存在的內網 IP，最後一台路由器可能回你一則「Destination Unreachable」，你的程式才會很快得到「No route to host」而不是等到逾時。

ICMP 雖然常被說成「第三層的協定」，但它其實是裝在 IP 封包裡的：IPv4 header 的 protocol 欄位填 1 就代表 payload 是 ICMP（TCP 是 6、UDP 是 17）。它沒有 port，因為它不是給應用程式彼此對話用的，而是給 IP 層自己用的控制管道。IPv4 的 ICMP 定義在 RFC 792，IPv6 有自己的版本 ICMPv6（RFC 4443），IPv6 header 的 next header 欄位填 58。

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────┬───────────────┬───────────────────────────────┐
 │   Type (8)    │   Code (8)    │         Checksum (16)         │  ← 所有 ICMP 都一樣
 ├───────────────┴───────────────┴───────────────────────────────┤
 │                 Rest of Header（4 bytes，依 Type 而定）         │
 │   echo：      Identifier (16)        │  Sequence Number (16)  │
 │   Type 3/4：  Unused (16) = 0        │  Next-Hop MTU (16)     │
 ├───────────────────────────────────────────────────────────────┤
 │ Data：                                                        │
 │   echo  → 任意 payload（ping 通常放時間戳記與填充）              │
 │   錯誤訊息 → 引發錯誤的原始 IP header ＋ 原始 payload 前 8 bytes 以上 │
 └───────────────────────────────────────────────────────────────┘
```

這是 ICMP 的位元布局。前 4 bytes 所有 ICMP 都相同：**Type** 說明是哪一類訊息，**Code** 在同一類裡再細分原因，**Checksum** 涵蓋整個 ICMP 訊息（IPv4 版只算 ICMP 本身，不像 TCP／UDP 要加 pseudo-header；ICMPv6 則要加）。接下來 4 bytes 的意義依 Type 而定：echo 用來放 identifier 與 sequence number，「需要分片」錯誤則在後 16 bits 放下一跳的 MTU，這個欄位是本章的關鍵。最後的 Data 區：如果是錯誤訊息，一定要附上**引發錯誤的原始 IP header 加上至少前 8 bytes 的 payload**。前 8 bytes 剛好涵蓋 TCP 或 UDP 的來源與目的 port，所以收到錯誤的主機能比對出「這是我哪一條連線的哪個封包出事」。RFC 1812 讓路由器在不超過 576 bytes 的前提下盡量多附原始內容，Linux 實際上也會附更多。

ICMP 訊息分成兩大類。**查詢訊息**（query）是一問一答，例如 echo request 與 echo reply；**錯誤訊息**（error）是對某個封包的回報，例如目的地不可達、TTL 逾時。錯誤訊息有幾條重要的自我約束，目的是避免 ICMP 自己引起風暴：不會對 ICMP 錯誤訊息再產生錯誤訊息、只對分片中的第一片產生錯誤、不對廣播或多播位址的封包產生錯誤。路由器也普遍對 ICMP 的產生做**限速**（rate limiting），因為產生 ICMP 要動用路由器的 CPU，而不是硬體的快速轉送路徑。這一點在第 6 章的 traceroute 已經見過：中間某一跳顯示 `* * *`，常常只是那台路由器懶得回，不代表封包到不了。

| Type | Code | 名稱 | 誰會送、什麼時候 | 能不能擋 |
|---|---|---|---|---|
| 0 | 0 | Echo Reply | 主機回應 ping | 可依政策限制 |
| 3 | 0／1 | Net／Host Unreachable | 路由器找不到網路或主機 | 不建議擋，否則連線失敗要等逾時 |
| 3 | 3 | Port Unreachable | 主機的該 UDP port 沒人在聽 | 不建議擋，traceroute（UDP 版）靠它結束 |
| 3 | 4 | Fragmentation Needed and DF Set | 路由器遇到太大又不准切的封包 | **絕對不能擋**，PMTUD 靠它 |
| 3 | 13 | Communication Administratively Prohibited | 防火牆依規則拒絕 | 可依政策 |
| 5 | 0–3 | Redirect | 路由器建議改走同網段另一個 gateway | 主機通常應忽略（有被誤導的風險） |
| 8 | 0 | Echo Request | ping 送出 | 可依政策限制或限速 |
| 11 | 0 | Time Exceeded in Transit | TTL 減到 0 | 不建議擋，traceroute 靠它 |
| 11 | 1 | Fragment Reassembly Time Exceeded | 分片沒在時限內收齊 | 不建議擋 |
| 12 | 0 | Parameter Problem | header 欄位有問題 | 不建議擋 |

這張表是你日後寫防火牆規則時的參考。注意 Type 3 是一個大家族，Code 4 是其中最不能少的成員；早期的 Type 4（Source Quench，要求傳送端慢一點）已被 RFC 6633 正式廢棄，現代系統不會送也不會理它。

IPv6 對 ICMP 的依賴更深。ICMPv6 除了 Destination Unreachable（Type 1）、**Packet Too Big**（Type 2，等同 IPv4 的「需要分片」，帶 32 bits 的 MTU 欄位）、Time Exceeded（Type 3）、Parameter Problem（Type 4）與 echo（Type 128／129），還承擔了 IPv4 裡 ARP 的工作：**Neighbor Discovery**（鄰居探索，Type 133–137）用 ICMPv6 找同網段鄰居的 MAC 位址、發現路由器、取得 SLAAC 的 prefix（第 5 章）。所以「把 ICMPv6 全擋」不是讓 IPv6 少一點功能，而是讓 IPv6 整個不能用。RFC 4890 專門整理了 ICMPv6 在防火牆上該放行與可以過濾的類型，Rita 後來把它列進了資安審查清單。

> [!warning] 常見誤解
> 「擋掉 ICMP 比較安全」是網路界流傳最久的誤解之一。確實有一些 ICMP 值得限制，例如對外回應 echo（減少被掃描時的資訊）或接受 redirect（避免路由被誤導）。但 Type 3（特別是 Code 4）與 Type 11 是網路正常運作的一部分，擋掉它們不會讓攻擊者更難入侵，只會讓你自己的連線在特定條件下壞掉，而且壞得很難查。正確的作法是「依類型精細過濾、並對允許的類型限速」，而不是一刀切。

## 8.3 ping 的原理與 Internet checksum

**ping** 是每個工程師最先學會的網路工具，原理只有一句話：送一個 ICMP echo request，等對方回 echo reply，量兩者之間的時間。echo request 的 rest-of-header 放 **identifier**（區分同一台機器上不同的 ping 程序）與 **sequence number**（每送一個加一，用來配對回應、發現遺失與亂序），payload 通常放送出時的時間戳記，方便計算往返時間。對方的 IP 層收到後，把 Type 從 8 改成 0、重算 checksum，其餘原封不動地送回來，所以 ping 不需要對方跑任何應用程式。

```text
 客服電腦 10.40.0.23                                       後台 server 10.20.3.17
   │── Echo Request  type=8 id=0x5a5a seq=1  (ICMP 64 bytes，IP 84 bytes) ──►│
   │                                                                     │ 核心直接處理：
   │                                                                     │ type 8→0、重算 checksum
   │◄─ Echo Reply    type=0 id=0x5a5a seq=1  payload 原樣帶回 ───────────────│
   │   RTT = 收到時間 − payload 裡的送出時間                                  │
   │── Echo Request  seq=2 ───────────────────────────────────────────────►│
   │◄─ Echo Reply    seq=2 ────────────────────────────────────────────────│
```

這張時序圖展示一次 ping 的來回。第一步，電腦送出 type 8 的 request，Linux 的 ping 預設 payload 是 56 bytes，加上 8 bytes 的 ICMP header 成為 64 bytes，再加 20 bytes 的 IPv4 header，線上的 IP 封包是 84 bytes，這就是 ping 輸出裡「64 bytes from」的由來。第二步，server 的作業系統核心直接處理，不經過任何使用者程式。第三步，reply 帶著同樣的 id 與 seq 回來，ping 用 seq 配對並算出 RTT。回應封包的 TTL 也會被印出來，從 TTL 可以粗估封包經過了幾跳：Linux 預設初始 TTL 是 64，如果你收到 ttl=61，大約是經過了 3 個路由器。

ping 要讀懂它的限制。第一，ping 不通不代表主機掛了，可能只是對方或中間的防火牆不回 echo，許多雲端的預設 security group 就不放行 ICMP。第二，ping 通也不代表服務正常，它只證明 IP 層可達，不證明 TCP 443 有人在聽，更不證明大封包過得去。故事裡的同事「ping 都通」正是落入第二個陷阱：預設的 84 bytes 封包遠小於 1420，當然暢行無阻。第三，ICMP 在某些網路上會被排在較低的優先順序或被限速，所以 ping 的 RTT 只能當參考，量應用程式的延遲要看應用程式自己的指標。

傳統上送 ICMP 要開 raw socket，需要 root 權限，所以 `ping` 執行檔過去都是 setuid root。現在的 Linux 提供「ICMP datagram socket」（`socket(AF_INET, SOCK_DGRAM, IPPROTO_ICMP)`），允許 `net.ipv4.ping_group_range` 範圍內的群組不用 root 就能送 echo，核心會幫你填 identifier；macOS 也有類似的機制。本書的程式不能用 root、也不連外網，所以下面只做編解碼，不真的送出。

ICMP、IPv4 header、TCP、UDP 用的是同一套 **Internet checksum**（RFC 1071）：把資料切成 16 bits 的字，用一補數（one's complement）相加，溢出最高位的進位要加回最低位，最後整個取反。接收端把含 checksum 在內的整段再算一次，結果是 0 就代表沒被改壞。它不是密碼學雜湊，攻擊者可以輕易偽造，它只用來抓傳輸中的隨機位元錯誤。我們用一個最小的 echo request 手算一次：

```python
import struct

def internet_checksum(data: bytes) -> int:
    """RFC 1071：16-bit 一補數加總再取反。"""
    if len(data) % 2:
        data += b"\x00"                      # 奇數長度補一個 0 byte 再算
    total = 0
    for (word,) in struct.iter_unpack("!H", data):
        total += word
        total = (total & 0xFFFF) + (total >> 16)   # 溢位的進位加回最低位（end-around carry）
    return ~total & 0xFFFF

# 一個最小的 echo request：type=8, code=0, checksum 先填 0, id=0x1234, seq=1, payload "hi"
msg = struct.pack("!BBHHH", 8, 0, 0, 0x1234, 1) + b"hi"
words = [f"{w:04x}" for (w,) in struct.iter_unpack("!H", msg)]
print("16-bit words:", " + ".join(words))
csum = internet_checksum(msg)
print(f"checksum = 0x{csum:04x}")

filled = msg[:2] + struct.pack("!H", csum) + msg[4:]
print(f"重算整個訊息（含 checksum）= 0x{internet_checksum(filled):04x}")
assert internet_checksum(filled) == 0       # 接收端驗證：結果為 0 才算正確
```

```text
16-bit words: 0800 + 0000 + 1234 + 0001 + 6869
checksum = 0x7d61
重算整個訊息（含 checksum）= 0x0000
```

逐步解讀。這則訊息被切成 5 個 16 bits 的字：`0800` 是 type 8、code 0；`0000` 是先填 0 的 checksum；`1234` 是 identifier；`0001` 是 sequence；`6869` 是 ASCII 的 "hi"。手算總和：0x0800 + 0x1234 = 0x1A34，加 0x0001 得 0x1A35，再加 0x6869 得 0x829E，這次沒有溢位，所以不必加回進位。取反（每個 bit 翻轉）得到 0x7D61，就是要填進去的 checksum。最後一行是接收端的驗證：把 0x7D61 填回去再算一次，總和變成 0xFFFF，取反得到 0，代表訊息完整。這個「整段重算得 0」的性質，讓路由器在只改 TTL 時還能用增量方式更新 IPv4 header checksum，不必整段重算。

## 8.4 MTU：每段鏈路的尺寸上限

**MTU**（Maximum Transmission Unit，最大傳輸單位）是一段鏈路一次能送的最大 IP 封包大小，單位是 bytes，算的是 IP 封包（含 IP header），不含鏈路層自己的 header。最常見的例子是 Ethernet：MTU 1500 表示一個 Ethernet frame 的 payload 最多 1500 bytes，再加上 14 bytes 的 Ethernet header 與 4 bytes 的 FCS，整個 frame 是 1518 bytes（帶 VLAN tag 再多 4 bytes）。第 4 章說過 frame 有大小上限，MTU 就是這個上限在 IP 層看到的樣子。

為什麼不能無限大？因為鏈路層的硬體、錯誤偵測的強度、以及「一個大 frame 占住線路時其他人要等多久」都有取捨。1500 是早期 Ethernet 留下來的數字，一直沿用到今天。不同的鏈路有不同 MTU：資料中心內常開 **jumbo frame**（約 9000 bytes）來降低每個封包的處理成本；家用光纖或 DSL 常用 PPPoE，因為 PPPoE 本身要占 8 bytes，MTU 變成 1492；各種隧道與 VPN 則因為外層 header 而更小。IPv4 規定每條鏈路至少要能送 68 bytes，而每台主機至少要能重組 576 bytes 的封包；IPv6 把最小 MTU 拉高到 1280 bytes，任何 IPv6 鏈路都必須至少支援這個大小。

| 鏈路或環境 | 常見 MTU | 由來 |
|---|---|---|
| Ethernet（預設） | 1500 | 早期 Ethernet 規格沿用至今 |
| Jumbo frame（資料中心、部分雲端 VPC 內部） | 約 9000（依設備與雲端而定） | 降低每個封包的處理成本 |
| PPPoE（家用寬頻） | 1492 | PPPoE 與 PPP header 占 8 bytes |
| WireGuard 隧道（wg-quick 常見值） | 1420 | 1500 減去外層 IPv6＋UDP＋WireGuard 的 80 bytes |
| VXLAN overlay（例如部分 Kubernetes CNI） | 1450 | 外層 IPv4＋UDP＋VXLAN＋內層 Ethernet 共 50 bytes |
| IPv6 最小值 | 1280 | IPv6 規格保證每條鏈路都能送 |
| IPv4 最小值 | 68（主機至少要能重組 576） | IPv4 規格的下限 |

一條端到端的路徑由很多段鏈路串成，整條路能通過的最大封包，取決於其中最小的那一段，這叫 **Path MTU**（路徑 MTU，簡稱 PMTU）。故事裡從 server 到客服電腦經過三段：VPC 內 1500、隧道 1420、辦公室 1500，所以 PMTU 是 1420。麻煩在於：server 只知道自己網卡的 MTU 是 1500，並不知道千里之外有一段只有 1420。

和 MTU 密切相關的是 TCP 的 **MSS**（Maximum Segment Size，最大區段大小）：一個 TCP segment 最多能帶多少 bytes 的「資料」，不含 IP 與 TCP header。IPv4 加 TCP 的 header 最少 40 bytes，所以在 MTU 1500 的 Ethernet 上，MSS 是 1500 − 40 = 1460；IPv6 的 header 是 40 bytes，加 TCP 20 bytes，MSS 是 1440。TCP 在三向交握時，雙方會在 SYN 與 SYN-ACK 裡用 **MSS option** 告訴對方「我最多收得下多大的 segment」，各自根據自己網卡的 MTU 計算。如果 SYN 裡沒帶 MSS option，規格要求假設 IPv4 是 536、IPv6 是 1220。

```text
 ◄──────────────────────── Ethernet frame 1518 bytes ────────────────────────►
 ┌──────────────┬───────────────────────────────────────────────────┬───────┐
 │ Ethernet hdr │              IP 封包 ＝ MTU 1500                    │  FCS  │
 │   14 bytes   │ ┌──────────┬──────────┬───────────────────────────┐ │4 bytes│
 │              │ │ IPv4 hdr │ TCP hdr  │   TCP payload ＝ MSS 1460  │ │       │
 │              │ │ 20 bytes │ 20 bytes │                           │ │       │
 │              │ └──────────┴──────────┴───────────────────────────┘ │       │
 └──────────────┴───────────────────────────────────────────────────┴───────┘
   實際抓包常看到 payload 1448：TCP timestamps option 再占 12 bytes，封包仍是 1500
```

這張圖是 MTU 與 MSS 的套疊關係，從外往內讀：最外層是 1518 bytes 的 Ethernet frame；扣掉 Ethernet header 與 FCS，中間 1500 bytes 是 IP 封包，也就是 MTU 管的範圍；IP 封包裡扣掉 20 bytes 的 IPv4 header 與 20 bytes 的 TCP header，剩下的 1460 bytes 才是應用程式資料。最下面那行是實務提醒：現代 TCP 幾乎都開著 timestamps option（第 11 章會講它的用途），每個 segment 的 TCP header 變成 32 bytes，所以你在 tcpdump 裡看到的滿載 segment 常常是 `length 1448`，但 IP 封包總長仍然是 1500。阿德之後在 server 上抓到的，就是一個個 `length 1448` 的封包在重傳。

## 8.5 IPv4 分片與重組

如果一個封包比下一段鏈路的 MTU 還大，IPv4 給了第一種解法：**分片**（fragmentation），也就是把一個 IP 封包切成幾片，每片各自帶一份 IP header，到目的地再拼回來。這個設計來自 1980 年代，當時各種鏈路的 MTU 差異很大，讓路由器在中途切割，可以讓傳送端不必知道整條路徑的細節。分片可以發生在傳送端，也可以發生在中途任何一台路由器；但**重組**（reassembly）只在最終目的地進行，中途的路由器不會把分片拼回來。

分片需要的資訊都在 IPv4 header 的第二個 32 bits 字裡。下面是 IPv4 header 的完整位元布局，與分片有關的欄位特別標出來：

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────┬───────┬───────────┬───┬───────────────────────────────┐
 │Version│  IHL  │   DSCP    │ECN│     Total Length (16)          │
 ├───────┴───────┴───────────┴───┼─────┬─────────────────────────┤
 │      ★ Identification (16)    │★Flag│ ★ Fragment Offset (13)  │
 │                               │0 D M│   單位：8 bytes           │
 ├───────────────┬───────────────┼─────┴─────────────────────────┤
 │   TTL (8)     │ Protocol (8)  │     Header Checksum (16)       │
 ├───────────────┴───────────────┴───────────────────────────────┤
 │                     Source Address (32)                       │
 ├───────────────────────────────────────────────────────────────┤
 │                   Destination Address (32)                    │
 └───────────────────────────────────────────────────────────────┘
   Flags 三個 bit：0＝保留（必須為 0）  D＝DF（Don't Fragment）  M＝MF（More Fragments）
```

逐欄說明打星號的三個欄位。**Identification** 是 16 bits 的編號，同一個原始封包切出來的所有分片帶相同的值，接收端用（來源位址、目的位址、protocol、identification）四者當 key，把屬於同一個封包的分片歸在一起。**Flags** 有三個 bit：第一個保留不用；**DF**（Don't Fragment）設為 1 表示「這個封包不准切」，路由器遇到太大的 DF 封包只能丟掉並回 ICMP Type 3 Code 4；**MF**（More Fragments）設為 1 表示「後面還有分片」，最後一片的 MF 是 0。**Fragment Offset** 是 13 bits，表示這片的資料在原始 payload 裡從第幾個位置開始，單位是 8 bytes，所以除了最後一片，每片的資料長度都必須是 8 的倍數。13 bits 最大是 8191，乘以 8 是 65528，剛好涵蓋 IPv4 封包的最大長度 65535。

手算一個例子。一個總長 4000 bytes 的 IPv4 封包（20 bytes header 加 3980 bytes payload），要經過 MTU 1500 的鏈路。每片能放的 payload 是 1500 − 20 = 1480，而 1480 剛好是 8 的倍數（185 × 8）。所以第一片帶 payload 的第 0–1479 byte，offset 欄位是 0，MF=1；第二片帶 1480–2959，offset 欄位是 1480 ÷ 8 = 185，MF=1；第三片帶剩下的 1020 bytes，offset 欄位是 2960 ÷ 8 = 370，MF=0。三片的總長分別是 1500、1500、1040，加起來比原本多了 40 bytes，因為多出了兩份 IP header。下面的程式把這個計算寫成函式，順便算 MTU 1420 的情況：

```python
IP_HEADER = 20   # 不帶 options 的 IPv4 header

def plan(total_len: int, mtu: int):
    """回傳每個分片的 (offset bytes, offset 欄位值, payload 長度, MF)。"""
    payload = total_len - IP_HEADER
    per_frag = (mtu - IP_HEADER) // 8 * 8    # 非最後一片的 payload 必須是 8 的倍數
    frags, offset = [], 0
    while offset < payload:
        size = min(per_frag, payload - offset)
        more = offset + size < payload
        frags.append((offset, offset // 8, size, int(more)))
        offset += size
    return frags

for mtu in (1500, 1420):
    print(f"總長 4000 bytes 的 datagram 經過 MTU {mtu}：")
    for off, field, size, mf in plan(4000, mtu):
        print(f"  offset={off:5d} (欄位值 {field:3d})  payload={size:4d}  MF={mf}  封包總長={size + IP_HEADER}")
    assert sum(f[2] for f in plan(4000, mtu)) == 4000 - IP_HEADER
```

```text
總長 4000 bytes 的 datagram 經過 MTU 1500：
  offset=    0 (欄位值   0)  payload=1480  MF=1  封包總長=1500
  offset= 1480 (欄位值 185)  payload=1480  MF=1  封包總長=1500
  offset= 2960 (欄位值 370)  payload=1020  MF=0  封包總長=1040
總長 4000 bytes 的 datagram 經過 MTU 1420：
  offset=    0 (欄位值   0)  payload=1400  MF=1  封包總長=1420
  offset= 1400 (欄位值 175)  payload=1400  MF=1  封包總長=1420
  offset= 2800 (欄位值 350)  payload=1180  MF=0  封包總長=1200
```

輸出的上半段和手算一致：offset 欄位 0、185、370，MF 是 1、1、0。下半段換成隧道的 MTU 1420：每片 payload 是 1400（175 × 8），offset 欄位變成 0、175、350，最後一片只剩 1180 bytes。注意 `per_frag` 那行用 `// 8 * 8` 向下取到 8 的倍數：如果 MTU 是 1492（PPPoE），1492 − 20 = 1472 剛好是 8 的倍數；但若某段鏈路的 MTU 讓 payload 不是 8 的倍數，就得往下取，浪費幾個 bytes。

接收端的重組流程是這樣的：收到一個 MF=1 或 offset 不為 0 的封包，就知道它是分片，用四元組 key 找到對應的緩衝區，把資料放到 offset × 8 的位置；收到 MF=0 的那片就知道總長度；所有位置都填滿時，交給上層的 TCP 或 UDP。分片可能亂序到達，所以重組不能假設順序。如果在時限內沒收齊（Linux 的 `net.ipv4.ipfrag_time` 預設 30 秒），整組丟棄，並且若收過第一片，會回一則 ICMP Type 11 Code 1。

```text
 server                VPN gateway (wg0 MTU 1420)                    辦公室電腦
   │── IP id=0x1f2e 總長 4000, DF=0 ──►│                                  │
   │                                  │── 片 1：offset 0,   MF=1, 1420 ──►│ 放進緩衝區 [0,1400)
   │                                  │── 片 2：offset 175, MF=1, 1420 ──╳ 在隧道裡遺失
   │                                  │── 片 3：offset 350, MF=0, 1200 ──►│ 放進 [2800,3980)，知道總長
   │                                  │                                  │ 等 [1400,2800) ……
   │                                  │                                  │ 30 秒後逾時，整組丟棄
   │◄────────────── ICMP Type 11 Code 1（Fragment Reassembly Time Exceeded）──│
```

這張時序圖說明分片最大的弱點。server 送出一個不帶 DF 的 4000 bytes 封包，gateway 依 MTU 1420 切成三片。第一片和第三片到了，第二片在隧道裡遺失。接收端已經知道總長，但中間有一個洞，只能等；30 秒後放棄，三片全部作廢，還回一則 Time Exceeded 告訴傳送端。重點是：IP 層不會只補送遺失的那片，因為分片沒有自己的重傳機制，要靠上層（TCP 重傳整個 segment，或 UDP 應用自己處理）重來一次。

## 8.6 為什麼大家都想避開分片

分片聽起來是個優雅的通用解法，但幾十年的實務經驗累積出一長串問題，IETF 甚至在 RFC 8900 把結論寫成標題：「IP 分片很脆弱」（IP Fragmentation Considered Fragile）。理解這些問題，你才會明白為什麼現代 TCP 幾乎都設 DF、為什麼 IPv6 不讓路由器切封包。

第一個問題是**丟包被放大**。一個切成 n 片的封包，任何一片遺失就整個作廢。在丟包率 1% 的網路上，不分片的封包有 99% 機率到達；切成 3 片時只剩 97%；切成 6 片時剩 94.1%。更糟的是，已經到達的分片白白占用了頻寬與接收端的記憶體。第二個問題是**只有第一片有 L4 header**：TCP 或 UDP 的 port 只在第一片裡，後面的分片只有 IP header。這讓所有需要看 port 的設備都很為難：stateful 防火牆要判斷要不要放行、NAT 要改 port（第 7 章）、load balancer 與 ECMP 路由要用五元組雜湊來決定往哪送。有些設備會為了分片暫存並重組，有些乾脆丟掉非第一片，有些把不同分片雜湊到不同路徑，結果在接收端永遠湊不齊。

第三個問題是 **identification 只有 16 bits**。同一對位址、同一個 protocol 之間只有 65536 個編號可用，而重組緩衝區要等 30 秒。算一下：以 1 Gbps 送 1500 bytes 的分片封包，每秒約 83,000 個封包，不到一秒就把 65536 個編號用完一輪。如果舊的分片還留在緩衝區，新封包的分片可能被拼進舊封包裡，產生一個 checksum 碰巧對上、內容卻是錯的資料（RFC 4963 專門討論了這種錯誤組合）。第四個問題是**安全**：歷史上許多攻擊利用重疊分片、極小分片或大量不完整分片來繞過檢查或耗盡重組記憶體。現代作業系統的防禦是丟棄重疊的分片、限制重組緩衝區的總記憶體、並讓防火牆在分片重組後再做檢查；IPv6 更在 RFC 5722 明文規定，遇到重疊分片必須丟棄整個封包。

因為這些問題，業界的共識是「讓傳送端從一開始就送不需要切的封包」。TCP 在 Linux、macOS、Windows 上預設都會設 DF，並靠下一節的 Path MTU Discovery 找出合適的大小。DNS 社群在 2020 年的 DNS Flag Day 建議把 EDNS 的 UDP 緩衝大小設為 1232 bytes，正是為了避免大回應在 UDP 上被分片（第 14、15 章會再談 EDNS）。

**IPv6 的作法更激進：路由器永遠不分片。** IPv6 header 裡沒有 identification、flags、offset 這些欄位，只有傳送端可以在必要時加上 **Fragment extension header** 自己切。路由器遇到太大的封包，一律丟棄並回 ICMPv6 Packet Too Big。這讓路由器的轉送路徑更簡單，但也代表 IPv6 完全依賴 Packet Too Big 能夠送回傳送端，擋掉它的後果比 IPv4 更嚴重。

| 比較項目 | IPv4 | IPv6 |
|---|---|---|
| 誰可以分片 | 傳送端與中途路由器 | 只有傳送端（Fragment extension header） |
| 不准切的標記 | header 的 DF bit | 不需要，路由器本來就不切 |
| 太大時的回報 | ICMP Type 3 Code 4，帶 16 bits next-hop MTU | ICMPv6 Type 2 Packet Too Big，帶 32 bits MTU |
| identification 大小 | 16 bits（在 header 裡） | 32 bits（在 Fragment extension header 裡） |
| 最小 MTU | 68（主機至少重組 576） | 1280 |
| 擋掉回報訊息的後果 | DF 封包變成黑洞 | 所有超過 PMTU 的封包都變成黑洞 |

這張表把兩個版本並排比較。最後一列最值得記住：在 IPv4，至少還有「不設 DF 讓路由器去切」這個退路，雖然很少用；在 IPv6，Packet Too Big 是唯一的回報管道。

## 8.7 Path MTU Discovery

既然不想分片，傳送端就得知道整條路徑的 PMTU。**Path MTU Discovery**（PMTUD，路徑 MTU 探索）的作法非常直接：先假設 PMTU 等於自己網卡的 MTU，送出的封包都設 DF；如果路上有一段太小，那裡的路由器會丟掉封包並回 ICMP Type 3 Code 4，告訴你下一跳的 MTU；傳送端把這個值記下來，之後送往同一個目的地的封包就改用這個大小。IPv4 的作法定義在 RFC 1191，IPv6 版本在 RFC 8201，用的是 Packet Too Big。

```text
 後台 server 10.20.3.17        VPN gateway 10.20.0.10              辦公室電腦 10.40.0.23
   │◄══════════ TCP 三向交握（SYN 裡 MSS=1460，雙方都以為能送 1500）══════════════►│
   │── 1500 bytes, DF=1 ────────►│ 下一跳 wg0 MTU 1420，太大又不准切 → 丟棄            │
   │◄─ ICMP Type 3 Code 4 ───────│   next-hop MTU=1420，附上原始 IP header + TCP port │
   │ 核心：比對出是哪條連線                                                         │
   │ PMTU 快取 10.40.0.23 → 1420，該連線 MSS 改 1380                                 │
   │── 1420 bytes, DF=1（重傳同一段資料）─►│═══════ 隧道 ═══════►│── 1420 bytes ──►│
   │◄──────────────────────────────────── ACK ──────────────────────────────────│
   │ 之後的 segment 都用 1420 bytes 的封包                                         │
```

這張時序圖是 PMTUD 正常運作時的樣子，也是故事裡如果 ICMP 沒被擋，本來會發生的事。第一步，交握時客服電腦宣告 MSS 1460，因為它的網卡 MTU 是 1500，它並不知道封包離開辦公室後要進隧道。第二步，server 送出第一個滿載的 1500 bytes segment，DF=1。第三步，VPN gateway 要把它送進 `wg0`，發現 1500 > 1420，又不准切，於是丟掉並回 ICMP，next-hop MTU 欄位填 1420，Data 區附上原始封包的 IP header 與前 8 bytes。第四步，server 的核心從附帶的 header 裡讀出來源 port 443、目的 port 52114，找到對應的 TCP 連線，把到 10.40.0.23 的 PMTU 記成 1420，並把這條連線的有效 MSS 降到 1380。第五步，TCP 立刻用較小的 segment 重傳剛才那段資料，之後一切順利。整個修正只多花了一個 RTT，使用者根本感覺不到。

這個 PMTU 會被記在作業系統的路由快取裡，有到期時間。Linux 預設 `net.ipv4.route.mtu_expires` 是 600 秒，到期後會再嘗試較大的封包，看看路徑是不是變好了。你可以用 `ip route get 10.40.0.23` 看到類似 `cache expires 587sec mtu 1420` 的資訊。PMTU 是以「目的地」為單位記錄的，同一台機器連往不同目的地，可能有不同的 PMTU。

PMTUD 有一個隱含的前提：**ICMP 必須能從出問題的那台路由器一路回到傳送端**。這個前提在網際網路早期理所當然，但在今天到處是防火牆、ACL、NAT 與隧道的網路裡，它很脆弱。路由器送出的 ICMP 來源位址是路由器自己的介面位址，可能是私有位址；回程路上可能有防火牆把所有 ICMP 丟掉；路由器本身可能因為限速而沒有送；NAT 設備必須正確地把 ICMP 裡附帶的原始 header 也一起轉換，才能讓內部主機比對得上。任何一環出錯，傳送端就收不到回報。

## 8.8 PMTUD 黑洞

當 DF 封包被丟掉、而回報的 ICMP 又到不了傳送端，就形成 **PMTUD 黑洞**（PMTUD black hole）：大封包掉進去，什麼聲音都沒有。RFC 2923 早在 2000 年就把它列為 TCP 最常見的問題之一。回到故事，Rita 在 VPC 子網的 network ACL 擋了所有 ICMP，而 network ACL 是 **stateless**（無狀態）的，它不會記得「這則 ICMP 是某條已放行連線的相關回報」，只看規則逐條比對（第 7 章介紹過 stateful 與 stateless 的差別，第 44 章會講雲端的 network ACL 與 security group）。

```text
 後台 server                    VPN gateway                       辦公室電腦
   │◄════════════ 交握成功（封包都很小）══════════════════════════════►│
   │◄── GET /export?month=10 ───────────────────────────────────────│  小請求，正常
   │── HTTP 回應 header 與前幾百 bytes（小封包）────────────────────────►│  畫面出現一半
   │── 1500 bytes DF=1 ─────────►│ 丟棄                               │
   │      ╳◄── ICMP mtu=1420 ────│ 被 network ACL 丟掉                 │
   │ （等 RTO）                                                       │
   │── 1500 bytes 重傳 ─────────►│ 丟棄，ICMP 又被擋                     │
   │ （RTO 加倍）                                                     │
   │── 1500 bytes 重傳 ─────────►│ 丟棄 ……                             │  瀏覽器一直轉圈
   │  重傳數分鐘到十幾分鐘後放棄，連線被 reset                                │
```

這張時序圖就是故事的真相。前三行一切正常：交握的 SYN、SYN-ACK、ACK 都很小；客服電腦送出的 GET 請求很小；server 回的 HTTP header 和前一小段內容也可能不到 1420 bytes，所以頁面「出現一半」。第四行開始，server 送出第一個滿載的 1500 bytes segment，gateway 丟掉並老實地回了 ICMP，但 ICMP 在進入 server 所在子網時被 ACL 丟掉。server 什麼都沒收到，只能當作一般的丟包處理：等待重傳逾時（RTO，第 11 章會詳細講），然後用**同樣大小**重傳，又被丟，RTO 加倍再等。TCP 不會因為重傳失敗就自動縮小封包，因為從它的角度看，這和網路壅塞造成的丟包無法區分。Linux 預設的 `tcp_retries2` 讓這種重傳持續十幾分鐘，使用者早就關掉分頁了。

黑洞的症狀非常有特徵，值得背下來：TCP 連線能建立；小的請求與回應正常；大的回應卡住、沒有錯誤訊息；ssh 能登入但大量輸出時凍住；TLS 交握可能卡在 Client Hello 之後，因為 server 送回的憑證鏈常常有好幾 KB，需要滿載的 segment；問題有方向性，只有「送大封包的那一側」受害。故事裡上傳 PDF 正常，因為上傳時是客服電腦送大封包，辦公室路由器回的 ICMP 在辦公室 LAN 裡沒被擋，電腦的 PMTUD 正常運作。

為什麼要等 Rita 擋 ICMP 和阿德加 VPN 兩件事同時發生才出事？在 VPN 上線前，辦公室走一般網際網路連到公開的 LB，路徑 MTU 一路都是 1500，DF 封包從來不需要被丟，自然不需要 ICMP；在 Rita 改 ACL 之前，就算有隧道，ICMP 也能回來，PMTUD 會自動修正。只有「路徑上有較小 MTU」與「回報被擋」同時成立，黑洞才出現。這也是 MTU 問題難查的原因：觸發條件分散在不同團隊、不同時間的變更裡。

| 黑洞的成因 | 例子 | 怎麼避免 |
|---|---|---|
| 防火牆或 ACL 擋掉所有 ICMP | 故事中的 network ACL；主機上 `iptables -p icmp -j DROP` 排在 RELATED 規則前面 | 放行 Type 3（至少 Code 4）、Type 11；IPv6 放行 Type 1–4 與 NDP |
| 路由器沒有送 ICMP | 設備被設定成不產生 unreachable，或 ICMP 產生被限速 | 調整設備設定；在隧道端做 MSS clamping |
| ICMP 來源位址被過濾 | 路由器用私有位址當來源，回程被 bogon 過濾或 uRPF 擋掉 | 讓路由器用可路由的位址送 ICMP |
| NAT 沒有轉換 ICMP 內附的原始 header | 內部主機收到 ICMP 卻比對不到連線 | 使用支援 ICMP 錯誤轉換的 NAT 實作 |
| 同一網段 MTU 不一致 | 一台主機開了 jumbo frame，交換器或對方沒開 | 同一個 L2 網段的 MTU 必須一致（這種情況根本沒有 ICMP 可回） |
| 隧道內層看不到外層的 ICMP | 外層路徑變小，ICMP 回到隧道端點卻沒被轉成內層的回報 | 隧道 MTU 設保守值、做 MSS clamping |

表格的倒數第二列值得特別注意：同一個 L2 網段上的兩台主機 MTU 不一致時，大 frame 會在交換器或接收端網卡被直接丟棄，中間沒有任何路由器，所以根本不會有 ICMP。症狀和黑洞一模一樣，但修法是把 MTU 設一致，而不是放行 ICMP。

既然 ICMP 這麼不可靠，有沒有不依賴 ICMP 的方法？有：**Packetization Layer PMTUD**（PLPMTUD，RFC 4821；給 UDP 等 datagram 協定用的版本是 RFC 8899 的 DPLPMTUD）。它的想法是由傳輸層自己探測：送一個比目前大小更大的探測封包，如果被確認收到，就代表這個大小可行；如果遺失，就保守地退回，而且探測封包的遺失不會被當成壅塞。Linux 的 TCP 有實作，用 `net.ipv4.tcp_mtu_probing` 控制：0 是關閉；1 是平常不探測，但偵測到疑似黑洞（例如滿載 segment 反覆逾時）時，把 MSS 退到 `tcp_base_mss`（新版核心預設 1024）再往上探；2 是一直開啟。設成 1 是一個成本很低的保險。

## 8.9 隧道與 VPN 的 MTU 帳

**隧道**（tunnel）是把一個完整的封包當成資料，裝進另一個封包裡傳送的技術：VPN、GRE、VXLAN、IPsec、Kubernetes 的 overlay 網路都是這樣。外層封包要有自己的 IP header，可能還有 UDP header、隧道協定的 header、加密的認證標籤，這些都要占 MTU。外層鏈路的 MTU 通常是 1500，所以內層能用的空間一定小於 1500。故事裡的 WireGuard 就是典型：一個內層封包被加密後，前面加上 WireGuard 的 16 bytes header（訊息類型、接收端索引、計數器）、後面加上 16 bytes 的認證標籤，再包上 UDP 與外層 IP header。

```text
 外層鏈路 MTU 1500
 ┌──────────┬────────┬──────────────┬──────────────────────────────────────┬──────────┐
 │ 外層 IPv4 │  UDP   │ WireGuard hdr │      加密後的內層封包（≤ 1440 bytes）     │ auth tag │
 │ 20 bytes │8 bytes │  16 bytes     │ ┌─────────┬─────────┬──────────────┐ │ 16 bytes │
 │ 辦公室公網 │ port   │ type, index,  │ │ 內層 IPv4 │ 內層 TCP │ 資料 ≤ 1400   │ │ (Poly1305)│
 │ → VPC 公網│ 51820  │ counter       │ │ 10.40→10.20│         │              │ │          │
 │          │        │               │ └─────────┴─────────┴──────────────┘ │          │
 └──────────┴────────┴──────────────┴──────────────────────────────────────┴──────────┘
   外層額外負擔：IPv4 時 20+8+16+16 = 60 bytes；外層若是 IPv6 則 40+8+16+16 = 80 bytes
   wg-quick 常見的預設 MTU 1420 ＝ 1500 − 80，外層 IPv4 或 IPv6 都裝得下
```

這張圖把一個 WireGuard 封包從外往內拆開。最外面是走在網際網路上的外層 IPv4 header，來源與目的是兩端 VPN 設備的公網位址；接著是 UDP header（WireGuard 常用 51820 port）；然後是 WireGuard 自己的 16 bytes header；中間是被加密的內層封包，裡面才是 10.40.0.23 到 10.20.3.17 的原始 IP 與 TCP；最後是 16 bytes 的認證標籤，用來驗證封包沒被竄改。加總起來，外層是 IPv4 時多 60 bytes，外層是 IPv6 時多 80 bytes。很多設定工具為了兩種情況都安全，直接用 1500 − 80 = 1420 當隧道 MTU，阿德的設定就是這樣。

不同封裝的額外負擔各不相同，下面的程式把常見的幾種列出來，並算出內層可用的 MTU 與 TCP MSS（MSS(v6) 一欄是「內層跑 IPv6 時」的值，因為 IPv6 header 比 IPv4 多 20 bytes）：

```python
LINK_MTU = 1500
# 每種封裝在外層多吃掉的 bytes（外層 IPv4，除非另外註明）
overheads = {
    "直接走 Ethernet": 0,
    "PPPoE": 8,                        # PPPoE 6 + PPP 2
    "IP-in-IP": 20,                    # 再包一層 IPv4 header
    "GRE": 24,                         # IPv4 20 + GRE 4
    "VXLAN": 50,                       # IPv4 20 + UDP 8 + VXLAN 8 + 內層 Ethernet 14
    "WireGuard（外層 IPv4）": 60,      # IPv4 20 + UDP 8 + WG header 16 + auth tag 16
    "WireGuard（外層 IPv6）": 80,      # IPv6 40 + UDP 8 + 16 + 16
}
print("內層MTU  MSS(v4)  MSS(v6)  封裝")
for name, extra in overheads.items():
    inner = LINK_MTU - extra
    mss4, mss6 = inner - 40, inner - 60          # IPv4+TCP = 40；IPv6+TCP = 60
    print(f"{inner:>7}  {mss4:>7}  {mss6:>7}  {name}")
assert LINK_MTU - overheads["WireGuard（外層 IPv6）"] == 1420   # wg-quick 常見預設值的由來
```

```text
內層MTU  MSS(v4)  MSS(v6)  封裝
   1500     1460     1440  直接走 Ethernet
   1492     1452     1432  PPPoE
   1480     1440     1420  IP-in-IP
   1476     1436     1416  GRE
   1450     1410     1390  VXLAN
   1440     1400     1380  WireGuard（外層 IPv4）
   1420     1380     1360  WireGuard（外層 IPv6）
```

讀這張表時，記得每一列都是「外層鏈路 MTU 1500」的前提下算的。PPPoE 只吃 8 bytes，所以家用寬頻的 MSS 常是 1452；GRE 吃 24 bytes；VXLAN 要把整個內層 Ethernet frame 包進去，所以連內層的 14 bytes Ethernet header 也算進負擔，共 50 bytes，這是 Kubernetes 用 VXLAN overlay 時 Pod 網卡 MTU 常被設為 1450 的原因（第 44 章）。IPsec 沒有列在表裡，因為它的負擔取決於加密演算法、是否有 NAT traversal 的 UDP 封裝、以及對齊的 padding，常見在 50 到 80 多 bytes 之間，所以 IPsec VPN 上常看到保守的 MSS 1360 或 MTU 1400。隧道還會疊加：如果辦公室本身走 PPPoE（1492），上面再跑 WireGuard（外層 IPv4 再扣 60），內層只剩 1432，比預設的 1420 大，安全；但若是 PPPoE 上跑 IPv6 外層的 WireGuard，就剩 1412，比 1420 小，隧道自己的封包就會被切或丟。

> [!note] 2026 現況
> 截至 2026 年 10 月，主要雲端的 VPC 內部普遍支援大於 1500 的 MTU，但離開 VPC（例如經過 internet gateway、跨區連線或 VPN）時通常回到 1500 或更小，具體數字依各雲端廠商的文件而定，而且會隨服務更新。設計跨環境的連線時，不要假設兩端的 MTU 相同，部署前用本章 8.13 的方法實測。

隧道還有一個額外的陷阱：**外層路徑的 PMTU 問題，內層看不到**。假設隧道的外層路徑上有一段 MTU 只有 1400，外層封包（1420 + 60）被丟，ICMP 會回到隧道的端點設備，而不是內層的 server。端點設備如果沒有把它轉換成內層的「需要分片」回報，server 永遠不會知道。所以隧道的 MTU 寧可設得保守一點，並且一定要搭配下一節的 MSS clamping。

## 8.10 MSS clamping

PMTUD 依賴 ICMP，PLPMTUD 依賴端點的設定，兩者都要「別人」配合。有沒有辦法在網路設備上一勞永逸地解決 TCP 的問題？有，而且非常普遍：**MSS clamping**（MSS 夾限）。想法是：既然 TCP 雙方會在 SYN 裡宣告 MSS，那就讓隧道端點在轉送 SYN 與 SYN-ACK 時，把裡面的 MSS 改成「不超過隧道 MTU − 40」。雙方因此一開始就送夠小的 segment，大封包根本不會出現，自然不需要任何 ICMP。

```text
 辦公室電腦                    辦公室路由器（clamp 到 1380）                 後台 server
   │── SYN  MSS=1460 ─────────►│ 改寫成 MSS=1380，修正 TCP checksum                    │
   │                           │── SYN  MSS=1380 ═══════ 隧道 ═══════════════════════►│
   │                           │◄═ SYN-ACK MSS=1460 ══════════════════════════════════│
   │◄─ SYN-ACK MSS=1380 ───────│ 回程方向也改寫                                         │
   │── ACK ────────────────────────────────────────────────────────────────────────►│
   │ 電腦送 ≤1380 bytes 資料              server 記住對方只收 1380，送出的封包 ≤1420 bytes │
   │◄═══════════════ 資料封包 1420 bytes，順利通過 wg0，不需要 ICMP ══════════════════════│
```

這張時序圖展示 clamping 怎麼介入交握。第一步，客服電腦依自己的網卡宣告 MSS 1460。第二步，辦公室路由器看到這是一個要進隧道的 SYN，把 MSS option 從 1460 改成 1380，並重新計算 TCP checksum（因為內容變了）。第三步，server 回 SYN-ACK，宣告自己的 1460，路由器在回程方向也改成 1380。第四步之後，雙方都以為對方只能收 1380 bytes 的 segment，送出的 IP 封包最大是 1380 + 40 = 1420，剛好塞進隧道。整個過程沒有任何 ICMP，即使 Rita 的 ACL 擋著，下載也會正常。

在 Linux 上，MSS clamping 用一行 iptables 規則就能做到，`--clamp-mss-to-pmtu` 會依照輸出介面（例如 `wg0`）的 MTU 自動計算：

```bash
# Linux iptables：轉送中的 SYN 封包，MSS 改成不超過出口介面 MTU - 40
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu

# nftables 的寫法（依路由查到的 MTU 改寫）
nft add rule inet filter forward tcp flags syn tcp option maxseg size set rt mtu

# 許多商用路由器在介面上設定固定值，例如 Cisco IOS：
#   interface Tunnel0
#    ip tcp adjust-mss 1380
```

規則裡的 `--tcp-flags SYN,RST SYN` 表示「只看 SYN 有設、RST 沒設的封包」，也就是交握的前兩個封包，不會去碰一般的資料封包，所以效能影響很小。clamping 要放在隧道兩端：辦公室端改寫往 VPC 去的 SYN 與回來的 SYN-ACK，雲端端也做同樣的事，這樣不論連線由哪一側發起都受保護。

MSS clamping 很好用，但要清楚它的邊界。第一，它**只對 TCP 有效**：UDP 沒有交握、沒有 MSS，DNS、QUIC、WebRTC、SRT 都不受保護。第二，它只能保護「經過這台設備的連線」，而且設備必須能讀到 TCP header；如果 TCP 被包在另一層加密裡（例如在隧道的另一邊才解開），中間設備看不到也改不了。第三，它把問題「藏起來」而不是「修好」：如果路徑上還有另一段更小的 MTU 而 ICMP 又被擋，clamping 到 1380 也救不了。所以阿德最後的修法是三管齊下：Rita 在 ACL 上放行 ICMP Type 3、Type 11 與 Type 12（並對 echo 做限速而不是全擋）；隧道兩端加 MSS clamping；server 打開 `tcp_mtu_probing=1` 當最後的保險。

## 8.11 UDP、QUIC 與即時影音怎麼面對 MTU

Joe 聽完這次事故，第一個反應是：「那 WebRTC 跟直播怎麼辦？它們都是 UDP。」這正是 MSS clamping 管不到的地方。UDP 是一個 datagram 一個 IP 封包（第 9 章），應用程式送多大，IP 層就送多大；超過 PMTU 時，若設了 DF 就被丟掉，若沒設就被分片，分片又帶來 8.6 節的所有問題。所以基於 UDP 的協定，幾乎都選擇**自己控制封包大小，保守地低於常見的 PMTU**。

**QUIC**（第 13 章）規定 Initial 封包所在的 UDP datagram 至少要有 1200 bytes，這同時保證了路徑至少支援 1200 bytes 的封包，因為 IPv6 最小 MTU 是 1280，扣掉 IPv6 與 UDP header 剛好留下足夠空間。QUIC 封包一律設 DF，之後可以用 DPLPMTUD 自己探測更大的大小。**WebRTC**（第 36 章）的大多數實作把 RTP 封包控制在約 1200 bytes 上下，視訊的一個 frame 再大，也是由 packetizer 切成許多個 RTP 封包，而不是交給 IP 去分片；DTLS 交握的憑證訊息也會在 DTLS 層自己切片。**SRT**（第 38 章）的 live 模式預設每個封包帶 1316 bytes 的 payload（7 個 188 bytes 的 MPEG-TS 封包），加上 SRT、UDP 與 IP header 仍在 1500 以內，但在 MTU 較小的隧道上就要調低 payload 大小。**DNS** 如 8.6 節所說，建議 EDNS 緩衝不超過 1232 bytes，更大的回應改用 TCP。

| 協定 | 典型封包大小策略 | 遇到過小的 PMTU 時 |
|---|---|---|
| TCP | MSS 協商＋PMTUD，可加 MSS clamping 與 MTU probing | 有 ICMP 或 probing 就自動修正 |
| QUIC | 最小 1200 bytes 起步，DF=1，DPLPMTUD 往上探 | 探測失敗就停在較小的大小 |
| WebRTC（RTP） | 多數實作約 1200 bytes 上下 | 通常已在多數隧道的 PMTU 以下 |
| SRT（live 模式） | 預設 payload 1316 bytes | 需手動調低 payload 大小 |
| DNS over UDP | EDNS 緩衝建議 1232 bytes | 回應被截斷（TC bit）後改用 TCP |

這張表的共同模式是：UDP 上的協定把 PMTU 當成設計參數，而不是交給網路處理。對你寫應用程式的意義是，若你要自己設計 UDP 協定（例如遊戲同步或遙測），就把單一 datagram 控制在 1200 bytes 左右，需要更大的資料就在應用層切片並自己處理遺失。

## 8.12 動手做：編解碼 ICMP、模擬分片與 PMTUD 黑洞

本節用三段程式把整章串起來。所有程式都只在記憶體裡組 bytes 與做模擬，不開 raw socket、不送出任何封包，所以不需要 root，也不連外網。第一段組出完整的 ICMP echo 與「需要分片」錯誤訊息並解析；第二段模擬 IPv4 分片與重組；第三段模擬 PMTUD、黑洞、MTU probing 與 MSS clamping 的差別。

### 程式一：ICMP 封包的編碼與解碼

這段程式做四件事：組一個和 Linux ping 一樣大小的 echo request（包含 IPv4 header）；把它解析回來並產生 echo reply；模擬 VPN gateway 對一個 1500 bytes 的 TCP 封包回 Type 3 Code 4，並像作業系統核心一樣從錯誤訊息裡讀出 MTU 與原始連線；最後故意翻轉一個 bit，看 checksum 是否抓得到。

```python
import ipaddress
import struct

def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = sum(w for (w,) in struct.iter_unpack("!H", data))
    while total >> 16:                        # 把所有進位折回低 16 位
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF

def ipv4_header(src, dst, proto, payload_len, ident=0, df=True, ttl=64):
    flags_frag = (0x4000 if df else 0)        # DF 是 flags 的中間那個 bit
    hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + payload_len, ident, flags_frag,
                      ttl, proto, 0, ipaddress.IPv4Address(src).packed,
                      ipaddress.IPv4Address(dst).packed)
    return hdr[:10] + struct.pack("!H", checksum(hdr)) + hdr[12:]

def icmp(type_, code, rest: bytes, body: bytes) -> bytes:
    """ICMP = type(1) code(1) checksum(2) rest-of-header(4) + data；checksum 只涵蓋 ICMP 本身。"""
    raw = struct.pack("!BBH", type_, code, 0) + rest + body
    return raw[:2] + struct.pack("!H", checksum(raw)) + raw[4:]

def parse_icmp(packet: bytes) -> dict:
    ihl = (packet[0] & 0x0F) * 4
    assert checksum(packet[:ihl]) == 0, "IPv4 header checksum 錯誤"
    msg = packet[ihl:]
    assert checksum(msg) == 0, "ICMP checksum 錯誤"
    t, c = msg[0], msg[1]
    out = {"src": str(ipaddress.IPv4Address(packet[12:16])), "type": t, "code": c}
    if t in (0, 8):                           # echo reply / echo request
        out["id"], out["seq"] = struct.unpack("!HH", msg[4:8])
        out["payload"] = msg[8:]
    elif t == 3 and c == 4:                   # Fragmentation Needed：後 2 bytes 是 next-hop MTU
        out["mtu"] = struct.unpack("!H", msg[6:8])[0]
        inner = msg[8:]                       # 原始 IP header + 至少前 8 bytes
        inner_ihl = (inner[0] & 0x0F) * 4
        sport, dport = struct.unpack("!HH", inner[inner_ihl:inner_ihl + 4])
        out["orig"] = (str(ipaddress.IPv4Address(inner[12:16])), sport,
                       str(ipaddress.IPv4Address(inner[16:20])), dport, inner[9])
    return out

SERVER, OFFICE_PC, VPN_GW = "10.20.3.17", "10.40.0.23", "10.20.0.10"

# 1) 組一個 ping：56 bytes payload，與 Linux ping 預設相同
payload = bytes(range(56))
echo = icmp(8, 0, struct.pack("!HH", 0x5a5a, 1), payload)
pkt = ipv4_header(OFFICE_PC, SERVER, 1, len(echo)) + echo
print(f"echo request：IP 總長 {len(pkt)} bytes，ICMP {len(echo)} bytes")
print("  前 28 bytes:", pkt[:28].hex(" "))
req = parse_icmp(pkt)
print(f"  解析：type={req['type']} id=0x{req['id']:04x} seq={req['seq']}")

# 2) server 收到後只改 type 與 checksum 就能回 echo reply
reply = icmp(0, 0, struct.pack("!HH", req["id"], req["seq"]), req["payload"])
rep = parse_icmp(ipv4_header(SERVER, OFFICE_PC, 1, len(reply)) + reply)
assert (rep["type"], rep["id"], rep["seq"], rep["payload"]) == (0, 0x5a5a, 1, payload)
print(f"echo reply：type={rep['type']} id 與 seq 原樣帶回，payload 相同={rep['payload'] == payload}")

# 3) 一個 1500 bytes、DF=1 的 TCP 封包（server:443 → 辦公室電腦:52114）
tcp_head = struct.pack("!HHIIBBHHH", 443, 52114, 1000, 2000, 0x50, 0x18, 501, 0, 0)
big = ipv4_header(SERVER, OFFICE_PC, 6, 1480, ident=7) + tcp_head + b"x" * 1460
# VPN gateway 發現下一跳 wg0 的 MTU 只有 1420，回報 Type 3 Code 4
quote = big[:20 + 8]                          # RFC 792：原始 header + 前 8 bytes
err = icmp(3, 4, struct.pack("!HH", 0, 1420), quote)
err_pkt = ipv4_header(VPN_GW, SERVER, 1, len(err)) + err
info = parse_icmp(err_pkt)
print(f"ICMP 錯誤：來自 {info['src']} type={info['type']} code={info['code']} next-hop MTU={info['mtu']}")
print(f"  引用的原始封包：{info['orig'][0]}:{info['orig'][1]} → {info['orig'][2]}:{info['orig'][3]} proto={info['orig'][4]}")
assert info["mtu"] == 1420 and info["orig"][1] == 443

# 4) 封包在路上壞了一個 bit，checksum 就抓得到
broken = bytearray(err_pkt)
broken[-1] ^= 0x01
try:
    parse_icmp(bytes(broken))
except AssertionError as exc:
    print("翻轉 1 個 bit 後：", exc)
```

```text
echo request：IP 總長 84 bytes，ICMP 64 bytes
  前 28 bytes: 45 00 00 54 00 00 40 00 40 01 23 46 0a 28 00 17 0a 14 03 11 08 00 a6 91 5a 5a 00 01
  解析：type=8 id=0x5a5a seq=1
echo reply：type=0 id 與 seq 原樣帶回，payload 相同=True
ICMP 錯誤：來自 10.20.0.10 type=3 code=4 next-hop MTU=1420
  引用的原始封包：10.20.3.17:443 → 10.40.0.23:52114 proto=6
翻轉 1 個 bit 後： ICMP checksum 錯誤
```

逐段解讀輸出。第一行：IP 總長 84 bytes、ICMP 64 bytes，與 8.3 節說的 ping 預設大小一致。第二行是前 28 bytes 的 hex，我們逐個欄位對照：`45` 是 version 4、IHL 5（5 × 4 = 20 bytes header）；`00` 是 DSCP／ECN；`00 54` 是總長 84；`00 00` 是 identification；`40 00` 是 flags 與 offset，0x4000 就是 DF=1、offset 0；`40` 是 TTL 64；`01` 是 protocol 1（ICMP）；`23 46` 是 header checksum；接著 `0a 28 00 17` 是 10.40.0.23，`0a 14 03 11` 是 10.20.3.17。第 21 byte 起是 ICMP：`08 00` 是 type 8 code 0，`a6 91` 是 checksum，`5a 5a 00 01` 是 identifier 0x5a5a 與 sequence 1。

第四行是 echo reply：只改 type 與 checksum，id、seq、payload 原樣帶回，這正是 ping 能配對請求與回應的原因。第五、六行是重點：程式從 ICMP 錯誤訊息的 rest-of-header 讀出 next-hop MTU 1420，再從 Data 區附帶的原始 IP header 與前 8 bytes，解出 10.20.3.17:443 → 10.40.0.23:52114、protocol 6。這就是 server 核心收到 ICMP 後找到對應 TCP 連線的方法，也說明了為什麼規格要求至少附上 8 bytes：少了它，就看不到 port。最後一行顯示，封包最後一個 bit 被翻轉後，ICMP checksum 驗證失敗，核心會直接丟掉這則訊息。

### 程式二：IPv4 分片與重組

這段程式把一個 3980 bytes 的 UDP datagram（例如某個自製遙測協定的大訊息）切成符合 MTU 1420 的分片，再用一個簡化的重組器測試四種情境：亂序到達、遺失一片、重疊分片、以及設了 DF 的封包。

```python
import random
import struct
from dataclasses import dataclass

@dataclass
class Fragment:
    ident: int
    mf: bool
    offset: int          # 欄位值，單位 8 bytes
    data: bytes
    df: bool = False

    def header_word(self) -> int:
        """IPv4 header 第 7–8 byte：3 個 flag bit + 13 bit offset。"""
        return (0x4000 if self.df else 0) | (0x2000 if self.mf else 0) | self.offset

def fragment(ident: int, payload: bytes, mtu: int, df: bool = False):
    if 20 + len(payload) <= mtu:
        return [Fragment(ident, False, 0, payload, df)]
    if df:
        raise ValueError(f"DF=1 且 {20 + len(payload)} > MTU {mtu}：丟棄並回 ICMP Type 3 Code 4")
    step = (mtu - 20) // 8 * 8
    return [Fragment(ident, pos + step < len(payload), pos // 8, payload[pos:pos + step])
            for pos in range(0, len(payload), step)]

class Reassembler:
    """以 (src, dst, proto, id) 為 key 收集分片；這裡簡化成只用 id。"""
    def __init__(self, timeout=30.0):
        self.buf, self.first_seen, self.timeout = {}, {}, timeout

    def receive(self, frag: Fragment, now: float):
        parts = self.buf.setdefault(frag.ident, {})
        self.first_seen.setdefault(frag.ident, now)
        start = frag.offset * 8
        for s, f in parts.items():           # 重疊的分片一律丟棄整組（RFC 5722 對 IPv6 的作法）
            if s != start and start < s + len(f.data) and s < start + len(frag.data):
                del self.buf[frag.ident]
                return "overlap: 整組丟棄"
        parts[start] = frag
        last = [f for f in parts.values() if not f.mf]
        if not last:
            return None
        total = last[0].offset * 8 + len(last[0].data)
        if sum(len(f.data) for f in parts.values()) != total:
            return None                       # 還有洞
        del self.buf[frag.ident], self.first_seen[frag.ident]
        return b"".join(parts[s].data for s in sorted(parts))

    def expire(self, now: float):
        dead = [i for i, t in self.first_seen.items() if now - t > self.timeout]
        for i in dead:
            self.buf.pop(i, None)
            del self.first_seen[i]
        return dead

random.seed(8)
udp = struct.pack("!HHHH", 5004, 5004, 8 + 3972, 0) + bytes(random.randrange(256) for _ in range(3972))
frags = fragment(0x1f2e, udp, mtu=1420)
print("分片結果（MTU 1420）：")
for f in frags:
    print(f"  id=0x{f.ident:04x} MF={int(f.mf)} offset 欄位={f.offset:3d} (byte {f.offset * 8:4d})"
          f" 長度={len(f.data):4d} flags+offset=0x{f.header_word():04x}")
print("  只有第一片帶 UDP header：", [f.offset == 0 for f in frags])

# 情境 A：亂序到達也能重組
r = Reassembler()
shuffled = frags[:]
random.shuffle(shuffled)
print("到達順序（offset）：", [f.offset for f in shuffled])
results = [r.receive(f, now=0.0) for f in shuffled]
assert results[-1] == udp
print("情境 A：亂序到達 → 重組成功，長度", len(results[-1]))

# 情境 B：丟一片 → 整個 datagram 都沒了，其他分片白送
r = Reassembler()
for f in frags[:1] + frags[2:]:
    assert r.receive(f, now=1.0) is None
print("情境 B：中間那片遺失 → 等待中的 id：", [hex(i) for i in r.buf])
print("         30 秒後逾時清除：", [hex(i) for i in r.expire(now=31.5)])

# 情境 C：重疊分片（常見於攻擊或錯誤實作）→ 拒收
r = Reassembler()
r.receive(frags[0], now=2.0)
bad = Fragment(0x1f2e, True, 100, b"\x00" * 400)   # byte 800 起，與第一片重疊
print("情境 C：", r.receive(bad, now=2.0))

# 情境 D：DF=1 時不能切
try:
    fragment(0x1f2f, udp, mtu=1420, df=True)
except ValueError as exc:
    print("情境 D：", exc)

# 丟包率 p 時，n 片全到的機率是 (1-p)^n
for n in (1, 3, 6):
    print(f"  丟包率 1%、{n} 片：整包成功率 {(0.99 ** n) * 100:.1f}%")
```

```text
分片結果（MTU 1420）：
  id=0x1f2e MF=1 offset 欄位=  0 (byte    0) 長度=1400 flags+offset=0x2000
  id=0x1f2e MF=1 offset 欄位=175 (byte 1400) 長度=1400 flags+offset=0x20af
  id=0x1f2e MF=0 offset 欄位=350 (byte 2800) 長度=1180 flags+offset=0x015e
  只有第一片帶 UDP header： [True, False, False]
到達順序（offset）： [350, 0, 175]
情境 A：亂序到達 → 重組成功，長度 3980
情境 B：中間那片遺失 → 等待中的 id： ['0x1f2e']
         30 秒後逾時清除： ['0x1f2e']
情境 C： overlap: 整組丟棄
情境 D： DF=1 且 4000 > MTU 1420：丟棄並回 ICMP Type 3 Code 4
  丟包率 1%、1 片：整包成功率 99.0%
  丟包率 1%、3 片：整包成功率 97.0%
  丟包率 1%、6 片：整包成功率 94.1%
```

逐段解讀。前四行列出三個分片：offset 欄位 0、175、350，MF 是 1、1、0，和 8.5 節的手算一致。`flags+offset` 欄是 header 裡實際的 16 bits：第一片 0x2000 代表 MF=1、offset 0；第二片 0x20af 是 MF 的 0x2000 加上 175（0xaf）；第三片 0x015e 是 MF=0、offset 350（0x15e）。下一行提醒：只有 offset 為 0 的第一片帶著 UDP header，後兩片在防火牆眼中只是「某個 id 的一段 bytes」。

情境 A 把到達順序打亂成 350、0、175，重組器依 offset 放進正確位置，最後一片到達時發現沒有洞，交出完整的 3980 bytes。情境 B 丟掉中間那片，重組器拿著另外兩片乾等，模擬時鐘走過 30 秒後整組清除，已經到達的 2580 bytes 白送了。情境 C 送進一片從 byte 800 開始的偽造分片，和第一片的 [0, 1400) 重疊，重組器丟棄整組，這是現代作業系統對重疊分片的標準防禦。情境 D 顯示設了 DF 的封包不會被切，而是丟棄並回 ICMP，也就是 PMTUD 的起點。最後三行用 (1 − p)^n 算出丟包率 1% 時，切越多片整包成功率越低，量化了 8.6 節的「丟包被放大」。

### 程式三：PMTUD、黑洞、MTU probing 與 MSS clamping

最後一段把故事整個重演一次。模擬一條 server → VPC 路由器 → VPN gateway（MTU 1420）→ 辦公室電腦的路徑，server 要送 6000 bytes 的匯出檔，所有 TCP 封包都帶 DF。為了讓輸出好讀，模型做了簡化：一次只送一個 segment、RTO 從 0.2 秒起跳每次加倍，探測只模擬「找到能過的大小」的二分搜尋，不模擬壅塞控制。

```python
from dataclasses import dataclass, field

HEADERS = 40                       # IPv4 20 + TCP 20（不含 options）
RTT = 0.030                        # server ↔ 辦公室的往返時間 30 ms

@dataclass
class Path:
    """server → VPC 路由器 → VPN gateway（wg0 MTU 1420）→ 辦公室電腦"""
    links: list = field(default_factory=lambda: [("vpc-router", 1500), ("vpn-gw", 1420), ("office", 1500)])
    icmp_reaches_sender: bool = True
    clamp_mss: bool = False

    def mtu(self):
        return min(m for _, m in self.links)

    def forward(self, size):
        """回傳 ("ok", None) 或 ("drop", (路由器名稱, 下一跳 MTU))。所有 TCP 封包都帶 DF=1。"""
        for name, mtu in self.links:
            if size > mtu:
                return "drop", (name, mtu)
        return "ok", None

    def syn(self, announced_mss):
        """SYN 經過 gateway；開啟 clamping 時把 MSS 改成不超過 MTU-40。"""
        return min(announced_mss, self.mtu() - HEADERS) if self.clamp_mss else announced_mss

def transfer(path, total=6000, probing=False, label=""):
    print(f"--- {label}")
    mss = min(1460, path.syn(1460))            # 辦公室電腦宣告 1460（它的網卡 MTU 是 1500）
    print(f"  SYN 裡的 MSS：電腦宣告 1460，server 收到 {mss}")
    clock, sent, rto, timeouts, log = 0.0, 0, 0.2, 0, []
    while sent < total:
        seg = min(mss, total - sent)
        verdict, info = path.forward(seg + HEADERS)
        if verdict == "ok":
            sent += seg
            clock += RTT
            rto, timeouts = 0.2, 0
            continue
        router, next_mtu = info
        if path.icmp_reaches_sender:
            clock += RTT                         # ICMP 很快回來
            mss = next_mtu - HEADERS
            log.append(f"t={clock:6.3f}s {seg + HEADERS} bytes 被 {router} 丟棄，收到 ICMP mtu={next_mtu} → MSS 改為 {mss}")
            continue
        clock += rto                             # 沒有 ICMP，只能等逾時
        timeouts += 1
        log.append(f"t={clock:6.3f}s 第 {timeouts} 次逾時重傳 {seg + HEADERS} bytes（RTO {rto:.1f}s）")
        rto = min(rto * 2, 120)
        if probing and timeouts == 2:            # 類似 Linux tcp_mtu_probing=1：疑似黑洞就退到 base MSS
            mss = 1024
            log.append(f"t={clock:6.3f}s 判定可能是 PMTU 黑洞 → MSS 退到 {mss}，之後再往上探測")
        if timeouts >= 8:
            log.append(f"t={clock:6.3f}s 放棄觀察：使用者看到的是「一直轉圈」")
            break
    for line in log:
        print("  " + line)
    done = sent >= total
    print(f"  結果：{'完成' if done else '卡住'}，送出 {sent}/{total} bytes，耗時 {clock:.3f}s")
    return done, mss

def probe_up(path, low=1024, high=1460):
    """PLPMTUD 的精神：用不影響資料的探測封包二分搜尋可用大小。"""
    steps = []
    while low < high:
        mid = (low + high + 1) // 2
        ok = path.forward(mid + HEADERS)[0] == "ok"
        steps.append(f"{mid}{'✓' if ok else '✗'}")
        low, high = (mid, high) if ok else (low, mid - 1)
    return low, steps

ok_a, mss_a = transfer(Path(), label="A. ICMP 正常：PMTUD 一次就修正")
ok_b, _ = transfer(Path(icmp_reaches_sender=False), label="B. ICMP 被 ACL 擋掉：PMTUD 黑洞")
ok_c, _ = transfer(Path(icmp_reaches_sender=False), probing=True, label="C. 開啟 MTU probing：慢但會好")
best, steps = probe_up(Path(icmp_reaches_sender=False))
print(f"  之後的探測：{' '.join(steps)} → 找到 MSS {best}")
ok_d, mss_d = transfer(Path(icmp_reaches_sender=False, clamp_mss=True), label="D. gateway 做 MSS clamping")

assert ok_a and mss_a == 1380 and not ok_b and ok_c and best == 1380 and ok_d and mss_d == 1380

# MSS clamping 只改 TCP SYN；UDP 不受影響
for size in (1200, 1472):
    verdict, info = Path(clamp_mss=True).forward(size + 28)   # IPv4 20 + UDP 8
    print(f"UDP payload {size}：{verdict}{'' if info is None else f'（{info[0]} MTU {info[1]}）'}")
```

```text
--- A. ICMP 正常：PMTUD 一次就修正
  SYN 裡的 MSS：電腦宣告 1460，server 收到 1460
  t= 0.030s 1500 bytes 被 vpn-gw 丟棄，收到 ICMP mtu=1420 → MSS 改為 1380
  結果：完成，送出 6000/6000 bytes，耗時 0.180s
--- B. ICMP 被 ACL 擋掉：PMTUD 黑洞
  SYN 裡的 MSS：電腦宣告 1460，server 收到 1460
  t= 0.200s 第 1 次逾時重傳 1500 bytes（RTO 0.2s）
  t= 0.600s 第 2 次逾時重傳 1500 bytes（RTO 0.4s）
  t= 1.400s 第 3 次逾時重傳 1500 bytes（RTO 0.8s）
  t= 3.000s 第 4 次逾時重傳 1500 bytes（RTO 1.6s）
  t= 6.200s 第 5 次逾時重傳 1500 bytes（RTO 3.2s）
  t=12.600s 第 6 次逾時重傳 1500 bytes（RTO 6.4s）
  t=25.400s 第 7 次逾時重傳 1500 bytes（RTO 12.8s）
  t=51.000s 第 8 次逾時重傳 1500 bytes（RTO 25.6s）
  t=51.000s 放棄觀察：使用者看到的是「一直轉圈」
  結果：卡住，送出 0/6000 bytes，耗時 51.000s
--- C. 開啟 MTU probing：慢但會好
  SYN 裡的 MSS：電腦宣告 1460，server 收到 1460
  t= 0.200s 第 1 次逾時重傳 1500 bytes（RTO 0.2s）
  t= 0.600s 第 2 次逾時重傳 1500 bytes（RTO 0.4s）
  t= 0.600s 判定可能是 PMTU 黑洞 → MSS 退到 1024，之後再往上探測
  結果：完成，送出 6000/6000 bytes，耗時 0.780s
  之後的探測：1242✓ 1351✓ 1406✗ 1378✓ 1392✗ 1385✗ 1381✗ 1379✓ 1380✓ → 找到 MSS 1380
--- D. gateway 做 MSS clamping
  SYN 裡的 MSS：電腦宣告 1460，server 收到 1380
  結果：完成，送出 6000/6000 bytes，耗時 0.150s
UDP payload 1200：ok
UDP payload 1472：drop（vpn-gw MTU 1420）
```

逐段解讀四個情境。**情境 A** 是正常的 PMTUD：第一個 1500 bytes 封包被 gateway 丟掉，一個 RTT 後 ICMP 回來說 MTU 1420，MSS 立刻改成 1380，6000 bytes 在 0.18 秒內送完。**情境 B** 就是故事中的黑洞：每次都送 1500 bytes、每次都被丟、ICMP 永遠到不了，RTO 從 0.2、0.4、0.8 一路加倍，51 秒後一個 byte 都沒送出去。真實的 Linux 會持續重傳到十幾分鐘，但對使用者來說，第 3 秒就已經是「壞了」。

**情境 C** 打開了類似 `tcp_mtu_probing=1` 的行為：連續兩次滿載 segment 逾時後，TCP 懷疑是黑洞，把 MSS 退到 1024，傳輸在 0.78 秒內完成。下一行模擬之後的往上探測：在 1024 到 1460 之間二分搜尋，打勾的大小通過、打叉的被丟，最後收斂到 1380，和情境 A 透過 ICMP 得到的答案相同，只是付出了多次探測的代價。**情境 D** 讓 gateway 做 MSS clamping：server 在 SYN 裡收到的 MSS 已經是 1380，從第一個資料封包就是 1420 bytes，即使 ICMP 仍然被擋，傳輸也在 0.15 秒內完成，是四個情境裡最快的，因為根本沒有封包被丟。

最後兩行提醒 clamping 的邊界：同一條路徑上，1200 bytes payload 的 UDP 封包順利通過；1472 bytes payload（加上 28 bytes header 剛好 1500）的 UDP 封包仍被 gateway 丟掉，因為 MSS clamping 只改寫 TCP 的 SYN，對 UDP 毫無作用。這就是 8.11 節說 UDP 協定必須自己控制封包大小的原因。

## 8.13 在工作上怎麼用

### 判斷流程：懷疑是 MTU 問題時

```text
 症狀：連線能建立、小請求正常、大回應卡住（或 TLS 卡在交握中段）
   │
   ├─► 1. 用 DF ping 二分搜尋 PMTU：1472 不通、1392 通？ ──► 路徑上有小 MTU
   │
   ├─► 2. 在「送大封包的一側」抓包：同樣大小的封包反覆重傳？ ──► 大封包被丟
   │
   ├─► 3. 在中途設備（隧道端點）抓 ICMP：有送出 Type 3 Code 4 嗎？
   │        ├─ 有送出，但傳送端沒收到 ──► 回程被擋：查 ACL／防火牆／security group
   │        └─ 沒送出 ──► 設備不產生 ICMP 或被限速：改用 MSS clamping
   │
   └─► 4. 修正後驗證：ss -tin 看 mss／pmtu、ip route get 看 PMTU 快取、重跑大下載
```

這張流程圖是小晴最後整理進 runbook 的版本。第一步用不准分片的 ping 確認路徑上真的有比 1500 小的 MTU；第二步在送大封包的那一側抓包，確認是「同樣大小的封包反覆重傳」而不是應用程式慢；第三步分辨 ICMP 是「有送沒到」還是「根本沒送」，前者修防火牆規則，後者在隧道端做 MSS clamping；第四步用系統工具驗證修正確實生效。

### 用 ping 找出 PMTU

ping 的 payload 大小不含 8 bytes 的 ICMP header 與 20 bytes 的 IPv4 header，所以要測 1500 bytes 的封包，payload 要填 1472。不同作業系統設定 DF 的參數不同：

```bash
# Linux：-M do 表示設 DF 且不在本機分片；-s 是 ICMP payload 大小
ping -c 3 -M do -s 1472 10.20.3.17      # 封包 1500 bytes
ping -c 3 -M do -s 1392 10.20.3.17      # 封包 1420 bytes

# macOS：-D 設 DF
ping -c 3 -D -s 1472 10.20.3.17

# Windows：-f 設 DF，-l 是 payload 大小
ping -n 3 -f -l 1472 10.20.3.17

# tracepath（Linux）：逐跳顯示 PMTU，不需要 root
tracepath -n 10.20.3.17
```

示意輸出（Linux，辦公室電腦往 server，ICMP 在辦公室端沒被擋時）：

```text
$ ping -c 2 -M do -s 1472 10.20.3.17
PING 10.20.3.17 (10.20.3.17) 1472(1500) bytes of data.
From 10.40.0.1 icmp_seq=1 Frag needed and DF set (mtu = 1420)
ping: local error: message too long, mtu=1420

$ ping -c 1 -M do -s 1392 10.20.3.17
PING 10.20.3.17 (10.20.3.17) 1392(1420) bytes of data.
1400 bytes from 10.20.3.17: icmp_seq=1 ttl=62 time=8.71 ms
```

第一個指令送了兩個封包，兩行錯誤的來源不同。第一行 `From 10.40.0.1 ... Frag needed and DF set (mtu = 1420)` 是辦公室路由器（10.40.0.1）回的 ICMP Type 3 Code 4：封包要進 `wg0` 時太大，被丟掉並回報。電腦的核心因此把往 10.20.3.17 的 PMTU 記成 1420，所以第二個封包根本沒送出去，直接在本機得到 `local error: message too long`。如果你看到的既不是遠端回報、也不是本機錯誤，而是單純逾時，那就是黑洞的徵兆。第二個指令用 1392 bytes payload 剛好組出 1420 bytes 的封包，順利收到回應。用二分搜尋調整 `-s`，就能找出路徑的 PMTU。

### 用 tcpdump 證明黑洞

黑洞需要兩邊的證據：中途設備「有送出 ICMP」，傳送端「沒收到 ICMP，而且在重傳大封包」。阿德在兩台機器上同時抓包：

```bash
# 在 VPN gateway：看自己送出的「需要分片」ICMP
tcpdump -ni any 'icmp[icmptype] == icmp-unreach and icmp[icmpcode] == 4'

# 在後台 server：看有沒有收到 ICMP，以及往辦公室的大封包
tcpdump -ni eth0 'icmp or (tcp and dst net 10.40.0.0/24 and greater 1400)'

# IPv6 的 Packet Too Big（ICMPv6 type 2）
tcpdump -ni any 'icmp6 and ip6[40] == 2'
```

示意輸出（server 端，ICMP 被 ACL 擋時）：

```text
10:02:11.402 IP 10.20.3.17.443 > 10.40.0.23.52114: Flags [.], seq 2897:4345, ack 518, length 1448
10:02:11.633 IP 10.20.3.17.443 > 10.40.0.23.52114: Flags [.], seq 2897:4345, ack 518, length 1448
10:02:12.091 IP 10.20.3.17.443 > 10.40.0.23.52114: Flags [.], seq 2897:4345, ack 518, length 1448
10:02:13.003 IP 10.20.3.17.443 > 10.40.0.23.52114: Flags [.], seq 2897:4345, ack 518, length 1448
```

這四行是黑洞的指紋：同一段 `seq 2897:4345`、同樣的 `length 1448`（滿載的 segment，加上 timestamps option 與 header 正好 1500 bytes），間隔越拉越長，而且中間沒有任何 ICMP。同一時間 gateway 的 tcpdump 顯示它每次都送出了 `ICMP 10.40.0.23 unreachable - need to frag (mtu 1420)`。兩份證據放在一起，就能確定問題在 gateway 到 server 之間的回程路徑上。

### 修正與驗證

```bash
# 隧道介面明確設定 MTU（不要依賴自動推算）
ip link set dev wg0 mtu 1420

# 隧道兩端：MSS clamping
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu

# server：疑似黑洞時自動退讓並探測
sysctl -w net.ipv4.tcp_mtu_probing=1

# 驗證：連線實際使用的 MSS 與 PMTU、核心記住的 PMTU
ss -tin dst 10.40.0.23
ip route get 10.40.0.23
```

`ss -tin` 的輸出裡會有 `mss:1368 pmtu:1420` 之類的欄位（mss 已扣掉 timestamps option），`ip route get` 則顯示 `cache expires ... mtu 1420`。修正後再跑一次匯出，應該立刻完成。

### 不同角色的檢查清單

- **後端工程師**：「小請求正常、大回應卡住」時，先想到 MTU，不要急著改應用程式的 timeout；用 `curl -o /dev/null -w '%{size_download}'` 搭配不同大小的回應，找出卡住的門檻是否在 1.4 KB 附近。
- **SRE／平台工程師**：每新增一條隧道（VPN、GRE、overlay），在變更單上寫明隧道 MTU、MSS clamping 規則與驗證方式；監控上可以觀察 TCP 重傳率與 `tcp_mtu_probing` 觸發次數（`nstat` 裡的 `TcpExtTCPMTUPFail`、`TcpExtTCPMTUPSuccess` 等計數器，依核心版本而定）。
- **資安工程師**：防火牆與 ACL 的 ICMP 規則依類型設定：放行 Type 3、Type 11 與 Type 12，對 Type 8 依政策限速或限制來源；IPv6 依 RFC 4890 放行 Type 1–4 與 NDP。stateless ACL 要特別注意回程方向。
- **影音工程師**：自己設定 SRT 或其他 UDP 協定的封包大小時，以最小可能的 PMTU 為準；在 VPN 或企業網路上推流出問題時，先試著把 payload 調小，看症狀是否消失。

## 8.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 連線建立、小請求正常，大回應卡住無錯誤 | PMTUD 黑洞：DF 大封包被丟、ICMP 被擋 | 傳送端 tcpdump 看到同一 seq 的 1448 bytes 反覆重傳；中途設備有送 ICMP Type 3 Code 4 | 放行 ICMP Type 3 Code 4；隧道端 MSS clamping；開 `tcp_mtu_probing=1` |
| TLS 交握卡在 Client Hello 之後 | server 的憑證鏈需要滿載 segment，被黑洞吞掉 | `openssl s_client` 卡住；抓包看到 Server Hello 那段重傳 | 同上；也可檢查憑證鏈是否過長 |
| ssh 能登入，大量輸出時凍住 | 同為黑洞，只是 ssh 的互動封包都很小 | 在 ssh 裡 `cat` 大檔案即可重現；DF ping 測 PMTU | 同上 |
| ping 都通，但應用程式不通 | ping 預設封包只有 84 bytes，不代表大封包過得去 | 用 `ping -M do -s 1472` 測大封包 | 依測得的 PMTU 調整隧道 MTU 或 MSS |
| IPv6 偶發完全不通、IPv4 正常 | ICMPv6 被全擋，NDP 或 Packet Too Big 失效 | 檢查防火牆的 ICMPv6 規則；`ip -6 neigh` 看鄰居狀態 | 依 RFC 4890 放行 ICMPv6 必要類型 |
| 開了 jumbo frame 後同網段某些主機間時好時壞 | 同一 L2 網段 MTU 不一致，大 frame 被交換器或網卡丟棄（沒有 ICMP） | 兩端 `ip link` 比對 MTU；同網段 DF ping 8972 bytes | 同網段所有設備（含交換器）設一致的 MTU |
| DNS 大回應（DNSSEC、很多記錄）查詢逾時 | UDP 回應被分片，分片被防火牆丟棄 | `dig +bufsize=4096` 逾時、`+bufsize=1232` 正常（回 TC 後走 TCP） | EDNS 緩衝設 1232；確保 TCP 53 可用 |
| VPN 上推流（SRT）畫面頻繁破碎 | UDP 封包超過隧道 PMTU，被切或被丟 | 抓包看外層封包是否分片；調小 payload 後是否改善 | 依隧道 PMTU 調小 SRT payload 大小 |
| 隧道本身頻繁斷線或吞吐量很差 | 隧道外層封包超過外層路徑 MTU（例如 PPPoE 上跑 IPv6 外層的 WireGuard） | 在外層介面抓包看分片；DF ping 測外層路徑 | 降低隧道 MTU，搭配 MSS clamping |

這張表的前三列其實是同一個根因的不同面貌，所以遇到其中一個症狀，就順手檢查另外兩個能不能重現，能重現就幾乎可以確定是黑洞。倒數第二列與最後一列提醒：UDP 與隧道本身也會受 MTU 影響，修法不同。

## 8.15 動手練習

1. **延伸程式一：ICMPv6 checksum。** 把 8.12 節的程式一改成 ICMPv6 Packet Too Big（Type 2），記得 ICMPv6 的 checksum 要涵蓋 IPv6 pseudo-header（來源位址、目的位址、上層長度、next header 58）。驗證方法：用 `ipaddress.IPv6Address` 組位址，整段（含 pseudo-header 與已填入的 checksum）重算應得 0。
2. **延伸程式二：分片重組的記憶體上限。** 為 `Reassembler` 加上「緩衝區總 bytes 上限」，超過時丟棄最舊的未完成封包，並寫一個測試送入大量只有第一片的不完整封包，確認記憶體不會無限成長。答案要點：這就是作業系統防禦分片耗盡攻擊的方式，Linux 對應的設定是 `net.ipv4.ipfrag_high_thresh`。
3. **延伸程式三：tcp_mtu_probing=2。** 修改 `transfer`，讓 probing 模式一開始就用 1024 起步並往上探，與情境 A、C、D 比較總耗時。答案要點：一開始就探測不必等逾時，但在路徑正常時會多花探測成本，這是 Linux 預設不用 2 的原因之一。
4. **用真實工具觀察 PMTU。** 在自己的電腦上，對一台允許 ping 的內網主機或家用路由器執行 DF ping，從 `-s 1472` 開始向下二分搜尋，找出能通過的最大值。如果你在家用 PPPoE 網路或連著公司 VPN，比較開關 VPN 時的結果。驗證方法：最大 payload 加 28 應等於你推算的 PMTU。
5. **用 tcpdump 看 MSS option。** 在本機執行 `tcpdump -ni lo0 'tcp[tcpflags] & tcp-syn != 0'`（Linux 用 `lo`），再用 `curl` 連一個本機 server，觀察 SYN 裡的 `mss` 值。答案要點：loopback 的 MTU 通常是 16384 或 65536，所以 MSS 會遠大於 1460，這也說明 MSS 是依「自己的網卡」計算的。
6. **寫防火牆規則（紙上練習）。** 為一台只提供 HTTPS 的 server 寫出 IPv4 與 IPv6 的入站規則清單，要求：對外不回 ping、但 PMTUD 與 traceroute 正常、IPv6 能正常運作。答案要點：放行 TCP 443；ICMP 放行 Type 3、Type 11，Type 8 拒絕；ICMPv6 放行 Type 1–4 與 133–136（NDP），Type 128 依政策。

## 本章重點整理

- ICMP 是 IP 層的回報與診斷機制，裝在 IP 封包裡（IPv4 protocol 1、IPv6 next header 58），分成查詢訊息與錯誤訊息兩類。
- ICMP 錯誤訊息會附上原始封包的 IP header 與至少前 8 bytes 的 payload，讓傳送端能比對出是哪一條連線出事。
- ping 用 echo request／reply 量測可達性與 RTT，但 ping 通只證明小封包可達，不代表服務正常或大封包過得去。
- Internet checksum 是 16 bits 一補數加總後取反，接收端整段重算得 0 代表完整；它只能抓隨機錯誤，不防偽造。
- MTU 是一段鏈路能送的最大 IP 封包；Ethernet 預設 1500，IPv6 最小 1280；整條路徑的 PMTU 由最小的那段決定。
- TCP 的 MSS 是 segment 的資料上限，IPv4 下等於 MTU 減 40，雙方在 SYN 裡宣告；實際抓包常看到 1448，因為 timestamps option 占 12 bytes。
- IPv4 分片靠 identification、DF／MF flag 與以 8 bytes 為單位的 fragment offset；重組只在目的地進行，任何一片遺失整個封包作廢。
- 分片會放大丟包、讓防火牆與 load balancer 看不到 port、有 identification 重複與安全風險，所以現代 TCP 預設設 DF，IPv6 路由器完全不分片。
- PMTUD 靠路由器回報 ICMP Type 3 Code 4（IPv6 是 Packet Too Big）讓傳送端降低封包大小；回報被擋就形成黑洞。
- PMTUD 黑洞的指紋是：連線能建立、小請求正常、大回應卡住，傳送端反覆重傳同樣大小的滿載 segment，且問題有方向性。
- 隧道與 VPN 會因外層 header 縮小內層 MTU：WireGuard 60 或 80 bytes、VXLAN 50 bytes、GRE 24 bytes、PPPoE 8 bytes。
- MSS clamping 在隧道端改寫 SYN 裡的 MSS，讓 TCP 從一開始就送夠小的封包，不依賴 ICMP；但它只對 TCP 有效。
- UDP 上的協定（QUIC、WebRTC、SRT、DNS）都自己控制封包大小，通常保守地維持在約 1200 bytes 左右或依路徑調整。
- 防火牆對 ICMP 要依類型精細過濾：Type 3 與 Type 11 必須放行，IPv6 還要放行 NDP；「全擋 ICMP」會讓網路以難以察覺的方式壞掉。

## 延伸問答

> [!question]- Q1. ping 得通，為什麼還可能是網路問題？
> ping 預設送的是 84 bytes 的 IP 封包（56 bytes payload 加 8 bytes ICMP header 加 20 bytes IPv4 header），它只證明「小的 ICMP 封包」能來回。真實的應用程式流量可能用 TCP 443、可能需要 1500 bytes 的封包、可能經過只對特定 port 做處理的設備，這些 ping 都沒有測到。
>
> 判斷依據是把「可達性」拆成幾層：IP 層小封包可達（ping）、特定 port 可達（`nc -vz` 或 `curl`）、大封包可達（DF ping 帶 1472 payload）、應用層正常（實際請求）。故事裡的情況是前兩層都正常、第三層失敗。反過來，ping 不通也不代表主機掛了，雲端主機常常預設不回 echo。所以 ping 的結果只能當作排查的起點，不能當結論。

> [!question]- Q2. 手算：一個總長 3000 bytes 的 IPv4 封包經過 MTU 1006 的鏈路，會切成幾片？各片的 offset 欄位與 MF 是多少？
> 每片能放的 payload 是 1006 − 20 = 986 bytes，但非最後一片的 payload 必須是 8 的倍數，986 ÷ 8 = 123.25，向下取到 123 × 8 = 984 bytes。原始 payload 是 3000 − 20 = 2980 bytes。
>
> 第一片放 byte 0–983，offset 欄位 0，MF=1，總長 1004；第二片放 984–1967，offset 欄位 984 ÷ 8 = 123，MF=1，總長 1004；第三片放 1968–2951，offset 欄位 246，MF=1，總長 1004；第四片放剩下的 28 bytes（2952–2979），offset 欄位 369，MF=0，總長 48。共 4 片。這個例子說明 MTU 若不是「8 的倍數加 20」，每片都會浪費幾個 bytes，而且最後可能出現一個很小的尾片。

> [!question]- Q3. 你在 production 看到：某企業客戶反映 TLS 連線偶爾卡在交握，其他客戶都正常。怎麼判斷是不是 MTU 問題？
> TLS 交握中，server 要送 Server Hello、憑證鏈與其他訊息，憑證鏈常常有好幾 KB，一定會用滿載的 TCP segment；而 Client Hello 通常比較小（加了後量子金鑰交換後也可能變大）。如果某段路徑有較小的 MTU 且 ICMP 被擋，最先受害的就是這個方向的滿載 segment，症狀正是「卡在交握」。只影響單一企業客戶，暗示問題在該客戶的網路（企業 VPN、代理或防火牆），而不是你的 server。
>
> 確認方式：請客戶在受影響的網路上用 DF ping 測到你的 PMTU；在你的 server 抓包，過濾該客戶的 IP，看是否有同一 seq 的滿載 segment 反覆重傳；比對該客戶 SYN 裡宣告的 MSS。若確認是黑洞而對方網路短期內改不了，可以在你的 LB 或 server 端對該客戶的流量降低 MSS，或開啟 `tcp_mtu_probing=1`，讓問題在你這端就被吸收。

> [!question]- Q4. 面試題：為什麼 IPv6 不讓路由器分片？代價是什麼？
> 路由器分片有幾個成本：要在轉送路徑上處理例外情況（切割、複製 header、重算 checksum），拖慢硬體轉送；分片帶來的丟包放大、L4 資訊只在第一片、identification 重複等問題，在 IPv4 的經驗裡已經證明代價很高。IPv6 因此把分片的責任完全交給傳送端：路由器遇到太大的封包一律丟棄並回 Packet Too Big，傳送端用 PMTUD 找出合適大小，真的需要時才自己加 Fragment extension header。
>
> 代價是 IPv6 完全依賴 ICMPv6 Packet Too Big 能回到傳送端。在 IPv4，傳送端還可以選擇不設 DF，讓路由器代勞；在 IPv6 沒有這個退路，擋掉 Packet Too Big 會讓所有超過 PMTU 的封包都變成黑洞。另外 IPv6 把最小 MTU 拉到 1280，讓協定設計者有一個可以依賴的下限，QUIC 的 1200 bytes 下限就是建立在這個保證上。

> [!question]- Q5. 看封包找原因：VPN gateway 上的 tcpdump 顯示不停送出 `ICMP ... unreachable - need to frag (mtu 1420)`，但 server 上抓不到任何 ICMP。問題出在哪？有幾種可能？
> 這組證據說明「中途設備有在回報，但回報沒到傳送端」，問題在 gateway 到 server 之間的回程路徑。可能的位置包括：子網邊界的 stateless network ACL 擋了 ICMP（故事中的情況）；server 的 security group 或主機防火牆沒有放行這類 ICMP；中間某台設備做了 uRPF 或來源位址過濾，因為 gateway 用來送 ICMP 的來源位址不在預期範圍；路徑上有 NAT 沒有正確轉換 ICMP。
>
> 排查方法是沿著回程路徑逐點抓包，找出 ICMP 在哪一點消失；同時檢查每一層的過濾規則。修法依位置而定：放行 ICMP Type 3 Code 4（至少來自 VPN gateway 的網段），或在 gateway 做 MSS clamping 讓問題不再依賴 ICMP。兩者都做最穩。

> [!question]- Q6. 設計取捨：隧道的 MTU 該設保守一點（例如 1380）還是盡量大（例如 1440）？
> 設得大的好處是每個封包能帶更多資料，header 比例較低，吞吐量略好；但前提是外層路徑真的能承受，例如外層是 IPv4 且整條路都是 1500。設得保守的好處是容錯：外層可能是 IPv6（多 20 bytes）、可能經過 PPPoE（少 8 bytes）、可能有其他封裝疊加，保守的 MTU 能讓隧道本身的封包在大多數路徑上都不必分片。
>
> 以 1380 和 1440 比較，每個封包少帶 60 bytes，對 1460 左右的 payload 來說約是 4% 的效率差異，大多數業務流量感受不到；但隧道外層被分片或被丟造成的問題，卻是「間歇性、難以查」的故障。所以多數實務選擇保守值，再搭配 MSS clamping。若是在完全受控的環境（例如同一雲端區域內），可以實測後設大一點。關鍵是把選擇和理由寫進設定檔與變更紀錄，而不是依賴工具的自動推算。

> [!question]- Q7. 為什麼 MSS clamping 救不了 QUIC 或 WebRTC？這些協定怎麼自保？
> MSS clamping 的原理是改寫 TCP SYN 裡的 MSS option。QUIC 與 WebRTC 都跑在 UDP 上，UDP 沒有交握、沒有 MSS，中途設備沒有欄位可以改；而且 QUIC 的封包內容是加密的，即使有類似的參數，中途設備也讀不到、改不了。
>
> 所以這些協定在設計時就把 PMTU 當成自己的責任。QUIC 規定第一批封包所在的 datagram 至少 1200 bytes 並設 DF，若路徑連這個大小都過不去，連線就建立不起來，瀏覽器會退回 TCP 上的 HTTP/2；之後再用 DPLPMTUD 用探測封包往上找更大的大小。WebRTC 的實作把 RTP 封包維持在約 1200 bytes 上下，大的視訊 frame 在應用層切成多個封包。這種「保守的起點加上自己探測」的模式，是 UDP 協定面對 MTU 的標準作法。

> [!question]- Q8. Rita 問：既然 ICMP 這麼重要，為什麼還有人建議限制它？資安上怎麼取捨？
> 限制 ICMP 的理由確實存在：對外回應 echo 讓掃描器更容易找出存活主機；ICMP redirect 若被接受，可能讓主機的路由被誤導；大量 ICMP 可能被用來消耗頻寬或 CPU；某些 ICMP 回應可能透露內部網路結構。但這些風險都能用「依類型處理」解決，而不需要全擋。
>
> 合理的政策是：Type 3（特別是 Code 4）、Type 11、Type 12 放行，因為它們是網路正常運作與除錯所需；Type 5 redirect 在主機上忽略；Type 8 echo 依環境決定是否對外回應，並對所有允許的 ICMP 做限速。IPv6 依 RFC 4890 放行 Type 1–4 與 NDP 必要的類型。判斷依據是：一條規則若擋掉的東西「攻擊者用不太到、但自己的連線一定需要」，它降低的是可用性而不是風險。故事裡的 ACL 規則就是這種情況，Rita 後來把「ICMP 全擋」列入審查時要退回的設定。

## 延伸閱讀

- RFC 792〈Internet Control Message Protocol〉
- RFC 4443〈Internet Control Message Protocol (ICMPv6) for the Internet Protocol Version 6 (IPv6) Specification〉
- RFC 1191〈Path MTU Discovery〉與 RFC 8201〈Path MTU Discovery for IP version 6〉
- RFC 4821〈Packetization Layer Path MTU Discovery〉與 RFC 8899〈Packetization Layer Path MTU Discovery for Datagram Transports〉
- RFC 2923〈TCP Problems with Path MTU Discovery〉
- RFC 8900〈IP Fragmentation Considered Fragile〉
- RFC 4890〈Recommendations for Filtering ICMPv6 Messages in Firewalls〉
- RFC 1071〈Computing the Internet Checksum〉
