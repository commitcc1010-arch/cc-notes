---
chapter: 9
title: Port、UDP 與 Socket API
part: 2
---

# 第 9 章　Port、UDP 與 Socket API

> [!abstract] 本章地圖
> **核心問題**：一台主機上同時跑著幾百個程式，封包怎麼找到正確的程式？如果傳輸層什麼保證都不給，應用程式要自己負責哪些事？
>
> **你會學到**：
> - 用 port 與五元組解釋「封包怎麼交給正確的 socket」，並看懂 ss、lsof 列出來的位址
> - 畫出 UDP header 的 8 bytes，手算一次 checksum，知道 pseudo header 為什麼存在
> - 說清楚 UDP 的三個語意：無連線、不可靠、保留訊息邊界，並和 TCP 的 byte stream 對比
> - 用 Berkeley socket API（socket、bind、sendto、recvfrom、connect）寫 UDP server／client，處理 timeout、ICMP 錯誤、SO_REUSEADDR 與 ephemeral port
> - 在應用層用序號、ACK、逾時重送與重排緩衝，把不可靠的 datagram 變成可靠、有序的訊息
> - 判斷什麼場景該選 UDP（DNS、影音、遊戲、QUIC），以及選了之後要自己補哪些功能
>
> **前置知識**：第 2 章（分層、封裝與 byte order）、第 5 章（IP 位址）、第 7 章（NAT 與防火牆）、第 8 章（MTU 與分片）

## 9.1 故事：會「卡死」的網路體檢

聲聲 Live 的老師上課前常抱怨：「每次都是上課五分鐘後才發現自己的網路很爛。」Joe 想在講師端的桌面程式加一個「網路體檢」：開課前十秒，程式每 100 毫秒送一個小探針到媒體伺服器所在的區域，伺服器原樣回傳，程式統計來回時間（RTT）和丟包率，太差就提醒老師換網路。因為真正的視訊走 UDP，探針也要走 UDP 才量得準。Joe 把伺服器端交給小晴：「很簡單，一個 UDP echo server，部署在 `10.20.3.21` 的 9910 port。」

小晴寫過不少 Flask，但從沒直接碰過 socket。第一版在本機測得很順，上了 staging 卻接連出事。第一個問題：有些老師的程式在體檢畫面「卡死」，一直轉圈圈。原因是 client 呼叫 `recvfrom` 等回應，而探針在路上掉了，這個呼叫就永遠等下去。第二個問題：伺服器 log 裡偶爾出現 JSON 解析失敗，因為小晴把接收緩衝設成 512 bytes，比較長的體檢報告被截斷了，而且被截掉的部分再也讀不到。

第三個問題發生在重新部署時。新版程式啟動失敗，log 寫著 `OSError: [Errno 98] Address already in use`。有人在聊天室建議：「加一行 SO_REUSEADDR 就好。」小晴照做，在 Linux 上確實啟動成功了，但接下來半小時有一部分老師的探針完全沒有回應，最後才發現舊的 process 根本沒停，兩個程式綁在同一個 port 上搶封包。第四個問題最單純也最難找：security group 只開了 TCP 9910，UDP 的探針全被擋掉，而 UDP 被擋時不會有任何錯誤訊息，client 只會等到逾時。

阿德聽完，在白板上寫了三行：「UDP 不保證送到。UDP 一次送一個完整訊息。UDP 沒有連線，所以沒有人會告訴你對方不在。」接著說：「你的 bug 全部來自把 UDP 當成 TCP 在用。這一章我們從 port 開始，一路走到 socket API，最後你自己在 UDP 上做一個會重送的小協定，就知道 TCP 替你做了多少事，也知道哪些時候不需要它。」

## 9.2 Port 與五元組：封包怎麼找到正確的程式

### 為什麼需要 port

第 5 章和第 6 章講的 IP 位址，只能把封包送到「某一台主機」。可是一台主機上同時跑著瀏覽器、Slack、Python 程式、DNS 快取服務，封包到了主機之後還要再決定交給誰。**port** 就是這個「主機內的門牌號碼」：一個 16-bit 的整數（0 到 65535），由傳輸層（UDP 或 TCP）的 header 攜帶。例如聲聲 Live 的探針伺服器在 `10.20.3.21` 上 bind 了 UDP port 9910，作業系統收到目的 port 為 9910 的 UDP 封包，就交給那個程式開的 socket。

把封包依 header 欄位分派給正確接收者的動作叫做 **demultiplexing（解多工）**；反過來，多個程式的資料共用同一張網卡送出去叫 **multiplexing（多工）**。分層的每一層都在做這件事：Ethernet 用 EtherType 決定交給 IPv4 還是 IPv6，IP 用 protocol 欄位決定交給 TCP（6）還是 UDP（17），傳輸層再用 port 決定交給哪個 socket。

```text
                       網卡收到 frame
                            │
                 EtherType 0x0800 → IPv4
                            │
             IP protocol 欄位：6 → TCP，17 → UDP
                 ┌──────────┴───────────┐
                 ▼                      ▼
            TCP 模組                 UDP 模組
                 │                      │
   查 (src ip, src port,          查 (dst ip, dst port)
       dst ip, dst port)          （connect 過的 socket 也比對來源）
                 │                      │
     ┌───────────┼─────────┐      ┌─────┴──────┬────────────┐
     ▼           ▼         ▼      ▼            ▼            ▼
  nginx:443  gunicorn   ssh:22  探針:9910   DNS 快取:53   找不到 socket
             :8000                                         → 回 ICMP
                                                             port unreachable
```

這張圖從上往下讀。第一步，網卡收到 frame，第 4 章的 EtherType 告訴 kernel 這是 IPv4。第二步，IPv4 header 的 protocol 欄位是 17，於是交給 UDP 模組。第三步，UDP 模組用目的位址與目的 port 查表，找到探針程式的 socket，把資料放進它的接收佇列。最右邊那條路很重要：如果沒有任何 socket 綁在這個 port 上，kernel 通常會回一個 ICMP「port unreachable」（第 8 章的 ICMP type 3 code 3），這是 9.6 節「connect 過的 UDP socket 會收到 ConnectionRefusedError」的來源。

### Port 的分段與 ephemeral port

port 號碼雖然只是整數，但 IANA（管理網際網路號碼的機構）把它分成三段，作業系統也有自己的慣例。下表整理常見的分段：

| 範圍 | IANA 名稱 | 用途 | 例子 |
|---|---|---|---|
| 0 | 保留 | 不能真的用來收送；bind 時填 0 代表「請系統幫我選一個」 | 本書所有程式都 bind port 0 |
| 1–1023 | System ports（well-known） | 標準服務；Linux 傳統上需要 root 或 CAP_NET_BIND_SERVICE 才能 bind | DNS 53、NTP 123、HTTPS 443 |
| 1024–49151 | User ports（registered） | 向 IANA 登記的應用程式 port | STUN／TURN 3478、mDNS 5353 |
| 49152–65535 | Dynamic／private | 臨時使用，不登記 | macOS 與 Windows 預設的 ephemeral 範圍 |

**ephemeral port（臨時 port）** 是 client 沒有指定 port 時，作業系統臨時分配的號碼。例如老師的桌面程式開一個 UDP socket 直接 `sendto` 到 9910，kernel 會在送出第一個封包前自動挑一個像 54329 這樣的號碼當來源 port。分配範圍依作業系統而定：Linux 預設是 32768–60999（看 `net.ipv4.ip_local_port_range`），macOS 預設是 49152–65535（看 `sysctl net.inet.ip.portrange`）。在系統上同時有大量對外連線時，這個範圍會被用完，第 10 章會講 TCP 的 ephemeral port 耗盡問題。

> [!warning] 常見誤解
> 「port 小於 1024 才是正式服務，大於 1024 的都是 client。」這只是慣例。gunicorn 預設聽 8000，很多內部服務聽 9000 以上；而 client 的來源 port 也可能落在 1024–49151 之間（Linux 的範圍就從 32768 開始）。判斷誰是 server，要看誰在 bind 後等待，而不是看號碼大小。

### 五元組：一個通訊流的身分證

只看目的 port 還不夠區分「誰在跟誰說話」。一百位老師同時打到 `10.20.3.21:9910`，目的端完全相同，差別在來源 IP 和來源 port。網路上用 **五元組（5-tuple）** 來識別一個通訊流：`(協定, 來源 IP, 來源 port, 目的 IP, 目的 port)`。例如 `(UDP, 198.51.100.150, 54329, 10.20.3.21, 9910)` 就是某位老師的探針流。第 7 章的 NAT 連線追蹤表、第 25 章的 L4 load balancer、security group 的規則，全都以五元組為單位運作。

下面這段程式讓三個 client 打到同一個 server socket，印出 server 看到的五元組，並示範 connect 過的 UDP socket 會擋掉陌生來源：

```python
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(("127.0.0.1", 0))
server.settimeout(1.0)
srv_ip, srv_port = server.getsockname()

# 三個「學生」各開一個 socket，都送往同一個 server port
students = []
for name in ("amy", "ben", "cat"):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((srv_ip, srv_port))     # UDP 的 connect 只是記住對端，不送任何封包
    s.send(f"hi from {name}".encode())
    students.append(s)

print(f"server 只有一個 socket：{srv_ip}:{srv_port}")
seen = set()
for _ in students:
    data, (cli_ip, cli_port) = server.recvfrom(2048)
    five_tuple = ("UDP", cli_ip, cli_port, srv_ip, srv_port)
    seen.add(five_tuple)
    print(f"  {data.decode():12} 五元組 = {five_tuple}")
assert len(seen) == 3                  # 目的端相同，靠來源 port 區分

# connect 過的 socket 會過濾來源：陌生人送來的 datagram 不會交給它
stranger = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
stranger.bind(("127.0.0.1", 0))
stranger.sendto(b"spoof?", students[0].getsockname())
server.sendto(b"welcome", students[0].getsockname())
students[0].settimeout(1.0)
got = students[0].recv(2048)
print("amy 的 socket 收到：", got)
students[0].setblocking(False)
try:
    students[0].recv(2048)
    leaked = True
except BlockingIOError:                # 佇列是空的：陌生人那個 datagram 被 kernel 擋掉了
    leaked = False
print("陌生人的 datagram 有沒有漏進來：", leaked)
assert got == b"welcome" and not leaked

for s in students + [server, stranger]:
    s.close()
```

執行結果（port 號碼每次執行都不同）：

```text
server 只有一個 socket：127.0.0.1:62518
  hi from amy  五元組 = ('UDP', '127.0.0.1', 62896, '127.0.0.1', 62518)
  hi from ben  五元組 = ('UDP', '127.0.0.1', 61730, '127.0.0.1', 62518)
  hi from cat  五元組 = ('UDP', '127.0.0.1', 58886, '127.0.0.1', 62518)
amy 的 socket 收到： b'welcome'
陌生人的 datagram 有沒有漏進來： False
```

逐行看輸出。第一，server 只開了一個 socket，三位學生的訊息都從同一個 `recvfrom` 進來，每次回傳的 `(cli_ip, cli_port)` 告訴 server 這個 datagram 是誰送的。UDP 沒有 TCP 的 `accept`，也沒有「每個 client 一個連線 socket」，server 想回覆誰，就把對方的位址帶給 `sendto`。第二，三個五元組只有來源 port 不同，這就足以區分三個通訊流。第三，amy 的 socket 呼叫過 `connect`，kernel 只會把來自 server 位址的 datagram 交給它，陌生人從另一個 port 送來的 `spoof?` 被 kernel 丟掉了（kernel 在這個例子中還會回 ICMP 給陌生人）。這種過濾只看位址，不是安全機制：攻擊者如果能偽造來源位址，照樣能通過，9.9 節會再談。

## 9.3 UDP header：8 bytes 的極簡主義

### 位元布局

UDP 的規格 RFC 768 只有三頁，header 只有 4 個欄位、共 8 bytes。對比第 10 章至少 20 bytes 的 TCP header，可以看出 UDP 的設計哲學：只做「把 port 加上去」和「檢查資料有沒有壞」，其他一律交給應用程式。

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-------------------------------+-------------------------------+
|        Source Port (16)       |     Destination Port (16)     |
+-------------------------------+-------------------------------+
|          Length (16)          |         Checksum (16)         |
+-------------------------------+-------------------------------+
|                    Payload（0 到 65507 bytes，IPv4）            |
+---------------------------------------------------------------+
  例：c9 3b | 00 35 | 00 12 | 0a 0a | 73 68 65 6e 67 ...
      51515    53      18    checksum  "sheng..."
```

逐欄解說。**Source Port** 是送出端的 port，回覆時要送回這裡；在 IPv4 上它其實可以填 0，表示「不需要回覆」，但實務上幾乎沒人這樣做。**Destination Port** 是 9.2 節 demultiplexing 用的欄位。**Length** 是 header 加 payload 的總長度，以 byte 為單位，最小值是 8（空 payload）；因為欄位是 16-bit，理論上限是 65535。**Checksum** 用來偵測傳輸中的位元錯誤。最下面那一行是下一段程式產生的真實 bytes：`c9 3b` 是 51515，`00 35` 是 53，`00 12` 是 18，全部依第 2 章講的 network byte order（big-endian）排列。

UDP header 裡**沒有**的欄位同樣值得注意：沒有序號，所以接收端不知道有沒有漏掉；沒有 ACK，所以送出端不知道對方收到沒；沒有視窗，所以沒有流量控制；沒有旗標，所以沒有建立和關閉連線的概念。這四個「沒有」，就是 9.4 節三個語意的根源。

### Checksum 與 pseudo header

UDP checksum 的算法叫 **Internet checksum**：把資料切成 16-bit 一組，用「1 的補數加法」加起來（超過 16 bit 的進位繞回低位加），最後把結果取反。接收端把所有資料連同 checksum 一起再加一次，結果取反應該是 0；不是 0 就代表資料壞了，kernel 直接丟掉這個 datagram，應用程式完全不會知道它來過。

特別的是，計算時還要在前面加上一段 **pseudo header（虛擬 header）**：來源 IP、目的 IP、一個 0 byte、協定號 17、UDP 長度。這段資料不會被送出去，只參與計算。為什麼要這樣做？因為如果 IP 位址在路上被弄錯，封包可能被送到錯的主機；把位址納入 checksum，錯的主機就會因為驗算失敗而丟棄它。代價是 checksum 和 IP 層綁在一起，所以第 7 章的 NAT 改了位址之後，也得重算 UDP checksum。

```python
import ipaddress
import struct

def checksum16(data: bytes) -> int:
    """Internet checksum：16-bit 一組做 1 的補數加法，最後取反。"""
    if len(data) % 2:
        data += b"\x00"                       # 奇數長度補一個 0 byte 再算
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:                        # 進位繞回低 16 位（end-around carry）
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF

def build_udp(src_ip, dst_ip, src_port, dst_port, payload: bytes) -> tuple[bytes, bytes]:
    length = 8 + len(payload)
    header = struct.pack("!HHHH", src_port, dst_port, length, 0)
    # pseudo header 不會被送出去，只是讓 checksum 也涵蓋 IP 位址與協定號
    pseudo = (ipaddress.ip_address(src_ip).packed + ipaddress.ip_address(dst_ip).packed
              + struct.pack("!BBH", 0, 17, length))
    csum = checksum16(pseudo + header + payload) or 0xFFFF   # 算出 0 要改送 0xFFFF
    return struct.pack("!HHHH", src_port, dst_port, length, csum) + payload, pseudo

segment, pseudo = build_udp("10.20.1.15", "10.20.0.2", 51515, 53, b"shengsheng")
print("UDP bytes :", segment.hex(" "))
src, dst, length, csum = struct.unpack("!HHHH", segment[:8])
print(f"src port  = {src}\ndst port  = {dst}\nlength    = {length} (8 header + {length - 8} payload)")
print(f"checksum  = 0x{csum:04x}")
assert checksum16(pseudo + segment) == 0      # 接收端驗算：連 checksum 一起加，結果應為 0

tampered = segment[:8] + b"Shengsheng"        # 中途改了一個字元
print("竄改後驗算 =", hex(checksum16(pseudo + tampered)), "（不是 0，丟棄）")
assert checksum16(pseudo + tampered) != 0
```

```text
UDP bytes : c9 3b 00 35 00 12 0a 0a 73 68 65 6e 67 73 68 65 6e 67
src port  = 51515
dst port  = 53
length    = 18 (8 header + 10 payload)
checksum  = 0x0a0a
竄改後驗算 = 0x2000 （不是 0，丟棄）
```

輸出的第一行就是上面位元布局圖最後一行的 bytes。程式的 `checksum16` 依序做三件事：奇數長度補 0、每兩個 byte 當一個 16-bit 數字加總、把超過 16 bit 的進位繞回來，最後取反。`assert checksum16(pseudo + segment) == 0` 示範接收端的驗算：連同 checksum 欄位一起算，結果是 0 就通過。最後一行把 `s` 改成 `S`，只差一個位元，驗算結果立刻不是 0。程式裡的 `or 0xFFFF` 對應一個規格細節：在 IPv4 上 checksum 欄位填 0 代表「我沒算 checksum」，所以如果真的算出 0，要改送等價的 0xFFFF（在 1 的補數裡，0x0000 與 0xFFFF 都代表零）。

| 項目 | IPv4 上的 UDP | IPv6 上的 UDP |
|---|---|---|
| Checksum | 可省略（填 0），但一般都有算 | 原則上必須計算，只有少數隧道情境的例外 |
| Pseudo header 內容 | 32-bit 位址、協定號、長度 | 128-bit 位址、next header、長度 |
| 單一 datagram 最大 payload | 65535 − 20 − 8 = 65507 bytes | 65535 − 8 = 65527 bytes（不使用 jumbogram 時） |
| 不分片的安全大小（常見假設） | 乙太網路 1500 − 20 − 8 = 1472 bytes | 最小 MTU 1280 − 40 − 8 = 1232 bytes |

這張表的第二列解釋了 IPv6 為什麼強制 checksum：IPv6 header 自己沒有 checksum（IPv4 header 有），如果 UDP 再省略，位址錯誤就完全沒有人能發現。最後一列的數字在第 8 章出現過：超過路徑 MTU 的 datagram 會被分片，而任何一片遺失整個 datagram 就沒了，所以實務上的 UDP 協定都刻意讓單一 datagram 小於 1200–1400 bytes。

> [!tip] 在 tcpdump 看到「bad udp cksum」先別緊張
> 在送出端的機器上抓封包，常常看到自己送出的 UDP 封包 checksum 錯誤。這通常是 **checksum offload**：作業系統把 checksum 留給網卡計算，tcpdump 抓到的是交給網卡之前的版本，欄位還沒填。接收端抓到的版本才準。

## 9.4 UDP 的三個語意：無連線、不可靠、保留訊息邊界

### 無連線

**無連線（connectionless）** 的意思是：送第一個 datagram 之前，雙方不需要任何交握，也不會在兩端建立共享的狀態。老師的程式想送探針，直接 `sendto` 就出去了，伺服器收到時才第一次知道有這個 client 存在。第 10 章會看到 TCP 要先花一個 RTT 做三向交握，連線結束還有四次揮手和 TIME_WAIT；UDP 這些全都沒有。

無連線帶來兩個直接後果。好處是第一個位元組可以立刻送出，伺服器也不必為每個 client 維護連線表，一個 socket 就能服務成千上萬個 client，DNS 伺服器就是這樣運作的。壞處是沒有人會告訴你「對方不在」：TCP 連到沒人聽的 port 會立刻收到 RST，而 UDP 的 datagram 送出去就算數，對方是否存在、是否還活著，應用程式得自己用逾時或心跳判斷。故事裡 security group 擋掉 UDP 時沒有任何錯誤，就是這個原因。

### 不可靠

**不可靠（unreliable）** 不是指「常常壞掉」，而是指 UDP **不做任何保證**：datagram 可能遺失、可能重複、可能亂序到達，UDP 都不會偵測或修正。遺失可能發生在路上任何一段：路由器佇列滿了丟包、Wi-Fi 干擾、防火牆擋掉，或者接收端的 socket 接收緩衝區滿了，kernel 直接丟棄新來的 datagram。最後這一種最容易被忽略：即使在 127.0.0.1 上，如果 server 處理太慢，datagram 也會被丟，而且只會在 kernel 的計數器裡留下紀錄。

```text
 老師的程式                 網路                    探針伺服器
   │── #1 ──────────────────────────────────────────►│ 收到 #1
   │── #2 ───────────────────X （路由器佇列滿，丟掉）    │
   │── #3 ───────────┐                                │
   │── #4 ───────────┼──────────────────────────────►│ 收到 #4
   │                 └──────────────────────────────►│ 收到 #3（走較慢的路徑，亂序）
   │── #5 ──────────────────────────────────────────►│ 收到 #5
   │                    （某段鏈路重送）     ─────────►│ 又收到 #5（重複）
   │                                                  │
   │    UDP 不會告訴任何一方：#2 不見了、#3 晚到、#5 重複   │
```

這張時序圖展示 UDP 會遇到的三種異常。#2 在路由器被丟掉，伺服器根本不知道有 #2；#3 和 #4 走了不同路徑（例如 ECMP 負載分散或無線重傳），到達順序對調；#5 因為下層鏈路的重送而出現兩次。對 UDP 來說，這些都是「正常」行為，它只負責把收到的 datagram 原樣交上去。應用程式如果在意，就要像 9.7 節那樣自己加上序號。

### 保留訊息邊界

第三個語意最常被忽略，卻最影響程式怎麼寫：**UDP 保留訊息邊界（message boundary）**。送出端呼叫一次 `sendto` 送出 10 bytes，接收端的一次 `recvfrom` 就拿到完整的那 10 bytes，不會多、不會少，也不會和下一個 datagram 黏在一起。每個 datagram 是一個不可分割的單位，要嘛整個到，要嘛整個不到。

TCP 正好相反。TCP 提供的是 **byte stream（位元組串流）**：送出端呼叫三次 `send`，接收端可能一次 `recv` 就拿到三段黏在一起的資料，也可能分成五次才拿完。TCP 只保證位元組的順序和完整，不保證「一次 send 對應一次 recv」，所以在 TCP 上傳訊息，一定要自己定義 **framing（訊息切割方式）**，例如長度前綴或換行分隔，第 11 章會詳細展開。9.8 節的動手做會實際對比這兩種行為。

邊界保留也有它的陷阱。如果接收緩衝比 datagram 小，多出來的部分會被截掉並丟棄，而不是留給下一次讀取，這就是故事中 512 bytes 緩衝造成 JSON 解析失敗的原因。另外，單一 datagram 的大小有上限：

```python
import errno
import socket

rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.bind(("127.0.0.1", 0))
rx.settimeout(0.5)
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tx.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 17)   # macOS 預設送出緩衝較小

# 1) 緩衝區太小：多出來的部分被截掉，而且不會留給下一次 recv
tx.sendto(b"0123456789", rx.getsockname())
tx.sendto(b"ABC", rx.getsockname())
first = rx.recv(4)
second = rx.recv(4)
print("recv(4) 第一次：", first, "第二次：", second)
assert first == b"0123" and second == b"ABC"       # 4567 89 永遠消失了

# 2) IPv4 上一個 UDP datagram 的 payload 最多 65535 - 20 - 8 = 65507 bytes
tx.sendto(b"x" * 65507, rx.getsockname())
big = rx.recv(65535)
print("65507 bytes：送出並收到", len(big), "bytes")
try:
    tx.sendto(b"x" * 65508, rx.getsockname())
except OSError as exc:
    print("65508 bytes：", errno.errorcode[exc.errno])
    assert exc.errno == errno.EMSGSIZE

# 3) 空的 datagram 也是一個合法訊息
tx.sendto(b"", rx.getsockname())
print("空 datagram：", rx.recvfrom(16)[0])
for s in (rx, tx):
    s.close()
```

```text
recv(4) 第一次： b'0123' 第二次： b'ABC'
65507 bytes：送出並收到 65507 bytes
65508 bytes： EMSGSIZE
空 datagram： b''
```

第一行輸出說明截斷行為：第一個 datagram 有 10 bytes，`recv(4)` 只拿到 `0123`，剩下的 `456789` 永遠消失，第二次 `recv(4)` 拿到的是下一個 datagram `ABC`。Linux 可以用 `MSG_TRUNC` 旗標得知原本的長度，但最簡單的做法是把接收緩衝設成協定允許的最大值。第二、三行是 IPv4 的硬上限 65507 bytes，再多一個 byte 就得到 `EMSGSIZE`（訊息太長）。程式特別把 `SO_SNDBUF` 調大，因為 macOS 對 UDP 的預設送出緩衝較小，不調整的話 9 KB 左右就會失敗，這也是「依作業系統而定」的典型例子。最後一行說明空 datagram 是合法訊息：`recvfrom` 回傳 `b''` 不代表連線關閉（UDP 沒有連線可以關），這點和 TCP 的 `recv` 回傳空 bytes 代表對方關閉完全不同。

| 特性 | UDP | TCP（第 10–12 章） |
|---|---|---|
| 建立連線 | 不需要，第一個 datagram 立刻送出 | 三向交握，多一個 RTT |
| 送達保證 | 無，可能遺失 | 有，遺失會重傳 |
| 順序 | 不保證 | 保證 |
| 重複 | 可能 | 自動去除 |
| 訊息邊界 | 保留，一次 sendto 對一次 recvfrom | 不保留，是 byte stream |
| 流量與擁塞控制 | 無，應用程式自己負責 | 內建 |
| header 大小 | 8 bytes | 至少 20 bytes |
| 一個 server socket 服務多個 client | 可以，靠 recvfrom 的來源位址區分 | 每個連線一個 accept 出來的 socket |
| 對方不存在時 | 通常沒有任何回應，只能靠逾時 | 收到 RST，立刻 ConnectionRefusedError |

> [!warning] 常見誤解
> 「UDP 比 TCP 快。」UDP 少了交握和重傳等待，所以**延遲可以更低**，但它本身不會讓頻寬變大；而且沒有擁塞控制的 UDP 程式如果送太快，會塞爆路徑上的佇列，反而丟更多包。正確的說法是：UDP 讓應用程式可以自己決定「遺失時要不要等」，對即時影音來說，不等待晚到的資料就是最大的好處。

## 9.5 Berkeley socket API：程式和網路之間的那道門

### Socket 是什麼

**socket** 是作業系統提供給程式的「網路端點」抽象：程式拿到一個 socket，就像拿到一個檔案，可以讀、寫、關閉，背後由 kernel 負責所有協定細節。在 Unix 系統上，socket 本身就是一個 **file descriptor（檔案描述符）**，也就是 kernel 發給 process 的一個小整數，和開檔得到的編號共用同一套機制，所以 `lsof` 能同時列出開啟的檔案和 socket。這套 API 最早出現在 1983 年的 4.2BSD Unix，稱為 **Berkeley sockets**，後來被 POSIX 標準化，Linux、macOS、Windows（Winsock）都沿用相同的函式名稱與語意。Python 的 `socket` 模組幾乎是這套 C API 的一對一包裝。

```text
       UDP server                                 UDP client
  socket(AF_INET, SOCK_DGRAM)               socket(AF_INET, SOCK_DGRAM)
            │                                          │
  bind(("10.20.3.21", 9910))                 （可省略 bind：第一次 sendto
            │                                  時系統自動分配 ephemeral port）
            ▼                                          │
  recvfrom() ◄───────── datagram ────────── sendto(data, server_addr)
  （阻塞等待，回傳 data 與來源位址）                   │
            │                                          │
  sendto(reply, client_addr) ─── datagram ──► recvfrom()
            │                                  （一定要設 timeout）
            ▼                                          ▼
     回到 recvfrom 等下一個                          close()

  對比 TCP server：socket → bind → listen → accept（每個 client 一個新 socket）→ recv／send
```

這張圖是 UDP 程式的骨架。server 端只有四步：建立 socket、bind 到固定位址、用 `recvfrom` 等待、用 `sendto` 回覆，然後回到 `recvfrom`。client 端可以不 bind，第一次 `sendto` 時 kernel 會自動選一個 ephemeral port 和適合的來源 IP。最下面一行是 TCP 的對照：TCP 多了 `listen` 和 `accept`，每個 client 連進來都會產生一個新的 socket，第 10 章會完整走一遍。UDP 的 server 從頭到尾只有一個 socket。

| C API | Python | 做什麼 | UDP 上要注意的事 |
|---|---|---|---|
| `socket()` | `socket.socket(AF_INET, SOCK_DGRAM)` | 建立端點，拿到 file descriptor | `SOCK_DGRAM` 代表 datagram；IPv6 用 `AF_INET6` |
| `bind()` | `sock.bind((ip, port))` | 決定本地位址與 port | port 0 由系統選；`0.0.0.0` 代表所有介面 |
| `sendto()` | `sock.sendto(data, addr)` | 送一個 datagram 到指定位址 | 回傳成功只代表交給了 kernel，不代表對方收到 |
| `recvfrom()` | `sock.recvfrom(bufsize)` | 收一個 datagram，並得到來源位址 | `bufsize` 太小會截斷；預設會一直阻塞 |
| `connect()` | `sock.connect(addr)` | 記住預設對端，過濾來源，啟用錯誤回報 | 不送任何封包；之後可用 `send`／`recv` |
| `setsockopt()` | `sock.setsockopt(level, opt, value)` | 調整行為 | 常用 SO_RCVBUF、SO_REUSEADDR、SO_REUSEPORT |
| `getsockname()` | `sock.getsockname()` | 查本地位址與 port | 看 ephemeral port 被分配到多少 |
| `close()` | `sock.close()` | 釋放 file descriptor | UDP 沒有揮手，關了就沒了 |

表格第四欄是寫 UDP 程式最容易出錯的地方。尤其 `sendto` 那一列：它的回傳值是「交給 kernel 的 byte 數」，就算對方主機根本不存在，`sendto` 也照樣成功。想知道對方收到沒，只能等對方回覆。

### 一個 datagram 在 kernel 裡的旅程

把 socket API 和 kernel 內部連起來看，比較容易理解「丟包可能發生在自己主機上」這件事：

```text
  送出端 process                                   接收端 process
  sendto(b"probe#7")                               recvfrom(2048)
        │ 複製到 kernel                                 ▲ 從佇列取出一個 datagram
        ▼                                               │
  ┌───────────────┐                           ┌───────────────────────────┐
  │ socket 送出緩衝 │                           │ socket 接收佇列（SO_RCVBUF）│
  │ (SO_SNDBUF)   │                           │ [#5][#6][#7] ← 滿了就丟新的 │
  └──────┬────────┘                           └─────────────▲─────────────┘
         ▼                                                  │
  UDP：加 8 bytes header、算 checksum              UDP：驗 checksum、查 port
         ▼                                                  │
  IP：加 IP header、必要時分片                      IP：重組分片
         ▼                                                  │
  網卡佇列 ──────────────── 網路 ─────────────────────► 網卡
```

左半邊是送出：`sendto` 把資料複製進 kernel，UDP 加上 header 與 checksum，IP 加上 IP header，最後放進網卡佇列。右半邊是接收：IP 重組分片，UDP 驗 checksum 並依 port 找到 socket，把 datagram 排進那個 socket 的接收佇列，等程式呼叫 `recvfrom` 取走。佇列的大小由 `SO_RCVBUF` 決定，如果程式處理太慢、佇列滿了，新到的 datagram 直接被丟棄。在 Linux 上可以用 `netstat -su` 的「receive buffer errors」或 `/proc/net/snmp` 的 `RcvbufErrors` 計數器確認，`ss -uampn` 則能看到每個 socket 目前佇列裡有多少資料。影音伺服器常把 `SO_RCVBUF` 調大，就是為了吸收瞬間湧入的封包。

### Python 的高階介面：asyncio

真實的 Python 服務很少用阻塞式的 `recvfrom` 迴圈，而是用 asyncio 的 `create_datagram_endpoint`。它的概念跟 socket API 一樣，只是把「收到一個 datagram」變成 callback：

```python
import asyncio

class EchoServer(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport            # UDP 沒有連線，這裡拿到的是「這個 socket」

    def datagram_received(self, data, addr):
        self.transport.sendto(data[::-1], addr)   # 每個 datagram 觸發一次，邊界天然保留

class Client(asyncio.DatagramProtocol):
    def __init__(self):
        self.replies = asyncio.Queue()

    def datagram_received(self, data, addr):
        self.replies.put_nowait(data)

    def error_received(self, exc):            # ICMP 錯誤（例如 port unreachable）從這裡進來
        print("error_received:", exc)

async def main():
    loop = asyncio.get_running_loop()
    srv, _ = await loop.create_datagram_endpoint(EchoServer, local_addr=("127.0.0.1", 0))
    addr = srv.get_extra_info("sockname")
    cli, proto = await loop.create_datagram_endpoint(Client, remote_addr=addr)
    for word in (b"ni hao", b"konnichiwa"):
        cli.sendto(word)
        reply = await asyncio.wait_for(proto.replies.get(), timeout=1.0)
        print(word, "->", reply)
        assert reply == word[::-1]
    cli.close()
    srv.close()

asyncio.run(main())
```

```text
b'ni hao' -> b'oah in'
b'konnichiwa' -> b'awihcinnok'
```

這段程式值得注意三件事。第一，`datagram_received` 每收到一個 datagram 就被呼叫一次，參數 `data` 就是完整的一個訊息，邊界由 UDP 保證，不需要像 TCP 的 `data_received` 那樣自己處理半包。第二，client 端用 `remote_addr` 建立 endpoint，等於對 socket 做了 `connect`，所以 `sendto` 可以不帶位址。第三，`error_received` 是 asyncio 傳遞 ICMP 錯誤的管道，下一節會解釋這些錯誤從哪裡來。聲聲 Live 的探針伺服器最後就是用這種寫法，搭配一個每秒清理過期 client 統計的背景 task。

## 9.6 Timeout、ICMP 錯誤與 socket 選項

### 一定要有 timeout

故事中的第一個 bug 就出在這裡：預設的 socket 是 **blocking（阻塞）** 模式，`recvfrom` 在收到資料之前會讓整個 thread 停住。UDP 的回應可能永遠不會來，所以每個等回應的 `recvfrom` 都必須有上限。Python 有三種做法：`sock.settimeout(0.3)` 讓等待最多 0.3 秒，逾時拋出 `TimeoutError`（Python 3.10 起 `socket.timeout` 就是它的別名）；`sock.setblocking(False)` 讓呼叫立刻回傳，沒資料就拋 `BlockingIOError`，通常搭配 `selectors` 使用；或者像上一節一樣交給 asyncio，用 `asyncio.wait_for` 控制等待時間。

timeout 該設多少，取決於你對 RTT 的預期。探針的目的就是量 RTT，Joe 最後定的規則是：超過 1 秒沒回應就算遺失，因為對即時視訊來說，1 秒的延遲已經不能用了。DNS client 常見的做法是幾秒逾時、重試幾次並換下一台伺服器（細節依實作與設定而定，第 16 章會看 resolv.conf 的設定）。

### ICMP port unreachable 與 connected UDP

前面提過，datagram 送到沒有 socket 在聽的 port 時，對方 kernel 通常會回 ICMP port unreachable。問題是，這個 ICMP 錯誤要交給誰？對**沒有 connect** 的 UDP socket 來說，它可能在跟很多對象通訊，kernel 預設不會把這個錯誤交給它（Linux 上要另外開 `IP_RECVERR` 才能取得）。但對 **connect 過** 的 socket，kernel 知道它只跟一個對象說話，就會把錯誤轉成 `ECONNREFUSED`，在下一次 `recv` 或 `send` 時拋出 `ConnectionRefusedError`。

```text
  client（已 connect 到 :9910）              server 主機（9910 沒有程式在聽）
     │── UDP datagram "ping" ───────────────────►│
     │                                           │ UDP：查不到 socket
     │◄── ICMP type 3 code 3 port unreachable ───│ （附上原始 IP＋UDP header 前段）
     │                                           │
  kernel 用 ICMP 裡附帶的原始 header 找到對應的 socket
     │
  recv() → ConnectionRefusedError（沒 connect 的 socket：什麼都沒有，等到逾時）
```

這個流程的關鍵在第三行：ICMP 錯誤訊息會附上觸發錯誤的原始 IP header 和 UDP header 前 8 bytes，送出端的 kernel 才能從中找回五元組，對應到正確的 socket。注意這個機制不可靠：很多防火牆會丟掉 ICMP，或者乾脆不回，所以「沒收到 ConnectionRefusedError」不代表對方有在聽。另外，Windows 的行為不同，沒有 connect 的 UDP socket 也可能在 `recvfrom` 收到 connection reset 錯誤，跨平台程式要記得處理。

### SO_REUSEADDR 與 SO_REUSEPORT

正常情況下，同一個位址與 port 只能被一個 socket bind，第二個會得到 `EADDRINUSE`（故事裡的 Errno 98 是 Linux 的編號，macOS 是 48）。兩個 socket 選項可以改變這條規則，但它們在 TCP 和 UDP、在不同作業系統上的意義都不一樣，這正是「加一行 SO_REUSEADDR 就好」危險的地方。

| 選項 | TCP 上的主要用途 | UDP 上的行為 | 平台差異 |
|---|---|---|---|
| `SO_REUSEADDR` | 讓 server 重啟時能 bind 仍有 TIME_WAIT 連線的 port（第 10 章） | Linux：所有 socket 都設定時允許重複 bind，但 unicast 只會交給其中一個；BSD／macOS：主要用於 multicast 位址 | Windows 的語意更寬鬆，可能讓其他程式搶走 port，Windows 另有 `SO_EXCLUSIVEADDRUSE` |
| `SO_REUSEPORT` | 多個 process 各自 listen 同一個 port，由 kernel 分散連線 | 多個 socket 共用 port；Linux 依五元組 hash 分散 datagram，且要求同一個使用者 | Linux 3.9 起支援；BSD 系很早就有，但分散方式不同 |

這張表的重點是：在 UDP 上，這兩個選項的效果是「允許多個 socket 同時收同一個 port」，而不是「讓舊的 socket 讓位」。故事中小晴在 Linux 加了 `SO_REUSEADDR`，舊 process 也設了同樣的選項，於是新舊兩個程式同時綁著 9910，有一部分探針被交給了正在關閉、已經不回覆的舊程式。正確的修法是讓部署流程真的停掉舊 process，或者有意識地用 `SO_REUSEPORT` 做零停機切換，並確定舊程式在退場前把佇列裡的 datagram 處理完。

> [!note] 為什麼 UDP server 重啟很少需要 SO_REUSEADDR
> TCP 需要 `SO_REUSEADDR` 是因為 TIME_WAIT：連線關閉後，port 還會被舊連線的狀態佔住一段時間。UDP 沒有連線，也沒有 TIME_WAIT，process 結束、socket 關閉後，port 立刻就能再用。所以 UDP server 重啟時出現 `Address already in use`，幾乎都代表「真的還有另一個程式在用這個 port」，該做的是用 `ss -uapn` 或 `lsof -iUDP:9910` 找出它，而不是加選項把錯誤蓋掉。

### Ephemeral port 是什麼時候分配的

client socket 的 ephemeral port 在三個時機之一被分配：明確 `bind(("0.0.0.0", 0))` 時、第一次 `sendto` 時、或者 `connect` 時。`connect` 的情況還會一併選好來源 IP：kernel 依第 6 章的路由表決定要從哪張網卡出去，就用那張網卡的位址。這是一個實用的小技巧：對目標位址做一次 UDP `connect` 再呼叫 `getsockname()`，就能得知「往那個目的地時，本機會用哪個來源 IP」，而且不會送出任何封包。9.8 節的程式會實際觀察這三種時機。

## 9.7 在 UDP 上補回可靠性：序號、ACK 與重送

### 為什麼要自己做

如果應用程式需要可靠、有序的訊息，最直接的答案是改用 TCP。但有些情況 TCP 不適合：只有部分資料需要可靠（影音的關鍵畫面要重送，舊的音訊封包晚到不如不要）；需要訊息邊界和多個獨立的串流，不希望一個遺失卡住全部（第 12 章的 head-of-line blocking）；或者想在 user space 快速演進協定，不想等所有作業系統更新 TCP 實作（第 13 章 QUIC 的動機）。這時候就要在 UDP 上自己補回需要的部分。第 38 章的 SRT、第 37 章 WebRTC 的 NACK、第 13 章的 QUIC，本質上都是這件事的不同版本。

### 四個基本零件

在 UDP 上做可靠傳輸，最少需要四個零件。**序號（sequence number）**：每個訊息帶一個遞增的編號，接收端才能發現遺失、重複和亂序。**ACK（acknowledgment，確認）**：接收端回報「我收到第幾號」，送出端才知道哪些可以從待確認清單移除。**逾時重送（retransmission timeout）**：送出端為還沒確認的訊息設定期限，期限到了就重送。**重排緩衝（reorder buffer）**：接收端先暫存提早到達的訊息，等缺口補上再依序交給應用程式。

```text
 sender                                                      receiver（expected=0）
   │── DATA seq=0 ─────────────────────────────────────────►│ 交付 [0]，expected=1
   │◄────────────────────────────────────────── ACK seq=0 ──│
   │── DATA seq=1 ──────────X（遺失）                         │
   │── DATA seq=2 ─────────────────────────────────────────►│ 暫存 {2}，等 1
   │◄────────────────────────────────────────── ACK seq=2 ──│
   │       ⋮                                                │
   │   ┌─ 逾時：seq=1 還沒有 ACK ─┐                           │
   │── DATA seq=1（重送）─────────────────────────────────►│ 交付 [1, 2]，expected=3
   │◄────────────────────────────────────────── ACK seq=1 ──│
   │── DATA seq=2（若 ACK 2 也遺失而重送）──────────────────►│ seq < expected：重複，丟棄
   │◄────────────────────────────────────────── ACK seq=2 ──│ 但仍回 ACK
```

這張時序圖是 9.8 節程式的縮小版。seq=0 正常送達並交付。seq=1 遺失，seq=2 先到，接收端不能把 2 交給應用程式（那會破壞順序），只能先暫存並回 ACK 2，讓送出端知道 2 不必重送。送出端等到逾時，發現 1 還沒確認，就重送 1；接收端收到後補上缺口，一次交付 1 和 2。最後兩行處理一個容易漏掉的情況：如果 ACK 本身遺失，送出端會重送一個接收端早就收過的訊息，接收端必須認出這是重複並丟掉，但**仍然要回 ACK**，否則送出端會永遠重送下去。

這裡的 ACK 是「每個訊息各自確認」，稱為 **selective ACK**；TCP 的基本 ACK 則是**累積確認**（「我已經收到第 N 個 byte 之前的全部」），兩者的取捨和 Go-Back-N、selective repeat 等演算法，第 11 章會用模擬程式完整比較。

### 逾時該設多少、重送要多快

逾時太短，網路只是慢了一點就重送，浪費頻寬又加重擁塞；逾時太長，真的遺失時要等很久才補。成熟的協定會根據量到的 RTT 動態調整逾時（TCP 的 RTO 計算，第 11 章），並在連續逾時時採用 **exponential backoff（指數退避）**：每次重試的等待時間加倍，避免在網路已經壅塞時雪上加霜。很多 client 還會加上隨機的 **jitter**，讓大量 client 不會在同一瞬間一起重試。這些細節正是「自己在 UDP 上做可靠傳輸」比想像中難的原因：寫一個能動的版本只要一百行，寫一個在真實網路上公平、穩定、不會打垮伺服器的版本，需要多年的工程累積。

> [!warning] 常見誤解
> 「我在 UDP 上加了序號和重送，就等於自己寫了一個 TCP。」還差得遠。TCP 還包含流量控制（不要淹沒接收端，第 11 章）、擁塞控制（不要淹沒網路，第 12 章）、連線建立與關閉的狀態機（第 10 章），以及數十年處理各種邊界情況的經驗。除非你有 TCP 無法滿足的明確需求，否則優先用 TCP 或現成的 QUIC 函式庫。

## 9.8 動手做：UDP echo、訊息邊界、丟包重送與 socket 選項

這一節有三段程式，全部在 127.0.0.1 上執行、使用 port 0，不需要任何外部服務。第一段是 UDP echo server 與 client，並和 TCP 對比訊息邊界；第二段在應用層模擬丟包與亂序，實作 9.7 節的序號與重送；第三段示範 timeout、ICMP 錯誤、SO_REUSEADDR 與 ephemeral port。

### 第一段：UDP echo 與訊息邊界

```python
import socket
import threading
import time

def udp_echo_server(sock: socket.socket, stop: threading.Event) -> None:
    # 一個 socket 服務所有 client：每個 datagram 自帶來源位址
    sock.settimeout(0.05)
    while not stop.is_set():
        try:
            data, addr = sock.recvfrom(2048)
        except TimeoutError:
            continue
        sock.sendto(data.upper(), addr)

def tcp_sink_server(listener: socket.socket, chunks: list) -> None:
    conn, _ = listener.accept()
    with conn:
        time.sleep(0.2)              # 故意晚一點讀，讓三次 send 都進到接收緩衝區
        while data := conn.recv(2048):
            chunks.append(data)

stop = threading.Event()
udp_srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_srv.bind(("127.0.0.1", 0))
threading.Thread(target=udp_echo_server, args=(udp_srv, stop), daemon=True).start()

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.settimeout(1.0)
messages = [b"hello", b"teacher-42", b"bye"]
for m in messages:
    client.sendto(m, udp_srv.getsockname())
udp_replies = []
for _ in messages:
    data, addr = client.recvfrom(2048)
    udp_replies.append(data)
print("UDP server   :", udp_srv.getsockname())
print("UDP client   :", client.getsockname(), "(系統自動分配的 ephemeral port)")
for m, r in zip(messages, udp_replies):
    print(f"  sendto {m!r:14} -> recvfrom {r!r}")
assert udp_replies == [m.upper() for m in messages]   # 一次 sendto 對一次 recvfrom

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(("127.0.0.1", 0))
listener.listen()
chunks: list = []
t = threading.Thread(target=tcp_sink_server, args=(listener, chunks))
t.start()
tcp = socket.create_connection(listener.getsockname())
for m in messages:
    tcp.sendall(m)
tcp.close()
t.join()
print("TCP 送出 3 次 sendall，server 的 recv 拿到", len(chunks), "塊：", chunks)
assert b"".join(chunks) == b"".join(messages)        # bytes 一個不少
assert len(chunks) < len(messages)                     # 但原本的邊界不見了

stop.set()
for s in (udp_srv, client, listener):
    s.close()
```

```text
UDP server   : ('127.0.0.1', 52127)
UDP client   : ('0.0.0.0', 64329) (系統自動分配的 ephemeral port)
  sendto b'hello'       -> recvfrom b'HELLO'
  sendto b'teacher-42'  -> recvfrom b'TEACHER-42'
  sendto b'bye'         -> recvfrom b'BYE'
TCP 送出 3 次 sendall，server 的 recv 拿到 1 塊： [b'helloteacher-42bye']
```

逐步解說（port 號碼每次執行都不同）：

1. server 在 thread 裡跑一個 `recvfrom` 迴圈，把收到的資料轉大寫後用 `sendto` 回給 `addr`。它設了 0.05 秒的 timeout，不是為了等 client，而是讓迴圈能定期檢查 `stop`，程式結束時 thread 才能乾淨退出。
2. client 沒有呼叫 `bind`，第一次 `sendto` 時 kernel 自動分配了 ephemeral port，所以 `getsockname()` 顯示 `0.0.0.0` 加上一個臨時號碼；`0.0.0.0` 代表這個 socket 沒有綁定特定介面。
3. client 連續送出三個 datagram，再連續收三次。三次 `recvfrom` 剛好拿到三個完整的回覆，`assert` 證明一次 `sendto` 對應一次 `recvfrom`，就算三個訊息幾乎同時在佇列裡，UDP 也不會把它們黏在一起。
4. TCP 那一半做同樣的事：連續三次 `sendall`，server 故意晚 0.2 秒才讀。結果 `recv` 一次拿到 `helloteacher-42bye`，三個訊息的界線完全消失。第一個 `assert` 證明 bytes 一個不少（TCP 保證完整與順序），第二個 `assert` 證明原本的邊界不見了（byte stream 不保留邊界）。
5. 在 loopback 上，TCP 的結果通常是 1 塊，但這不是保證：在真實網路上可能是 2 塊、3 塊，甚至把 `teacher-42` 切成兩半。第 11 章會用長度前綴解決這個問題。

### 第二段：模擬丟包與亂序，實作序號與重送

127.0.0.1 幾乎不會丟包，所以我們在應用層加一個 `LossyLink`，依照固定計畫丟掉或延後某些 datagram。用固定計畫而不是隨機數，是為了讓每次執行的結果都一樣，方便對照解說。

```python
import socket
import struct
import threading

DATA, ACK = 0, 1
HDR = struct.Struct("!BI")          # 1 byte 類型 + 4 bytes 序號

class LossyLink:
    """在應用層假裝網路很差：照計畫丟掉或延後某幾個 datagram。"""
    def __init__(self, sock, plan, name, log):
        self.sock, self.plan, self.name, self.log = sock, plan, name, log
        self.count = 0
        self.held = None

    def send(self, data, addr):
        idx, self.count = self.count, self.count + 1
        kind, seq = HDR.unpack_from(data)
        label = f"{'DATA' if kind == DATA else 'ACK'} seq={seq}"
        action = self.plan.get(idx, "ok")
        if action == "drop":
            self.log.append(f"  [{self.name}] 丟掉 {label}")
            return
        if action == "hold":                  # 先扣住，等下一個送出後再送 → 亂序
            self.log.append(f"  [{self.name}] 延後 {label}")
            self.held = (data, addr)
            return
        self.sock.sendto(data, addr)
        if self.held:
            self.sock.sendto(*self.held)
            self.held = None

def receiver(sock, link, delivered, log, stop):
    expected, buffer = 0, {}
    sock.settimeout(0.05)
    while not stop.is_set():
        try:
            pkt, addr = sock.recvfrom(2048)
        except TimeoutError:
            continue
        _, seq = HDR.unpack_from(pkt)
        if seq < expected or seq in buffer:
            log.append(f"收到 seq={seq}：重複，丟棄（仍回 ACK）")
        else:
            buffer[seq] = pkt[HDR.size:]
            ready = []
            while expected in buffer:        # 依序號交給應用程式
                delivered.append(buffer.pop(expected))
                ready.append(expected)
                expected += 1
            note = f"交付 {ready}" if ready else f"先暫存，等 seq={expected}"
            log.append(f"收到 seq={seq}：{note}")
        link.send(HDR.pack(ACK, seq), addr)   # 重複的也要回 ACK：上一個 ACK 可能丟了

recv_log, send_log, delivered = [], [], []
stop = threading.Event()
rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.bind(("127.0.0.1", 0))
ack_link = LossyLink(rx, {2: "drop"}, "ACK 方向", recv_log)
t = threading.Thread(target=receiver, args=(rx, ack_link, delivered, recv_log, stop))
t.start()

tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tx.settimeout(0.15)                          # 等 ACK 最多 150 ms，逾時就重送
data_link = LossyLink(tx, {1: "drop", 3: "hold"}, "DATA 方向", send_log)
lines = [f"line-{i}".encode() for i in range(6)]
unacked = set(range(len(lines)))
to_send = sorted(unacked)
rounds = 0
while unacked:
    rounds += 1
    send_log.append(f"第 {rounds} 輪送出 seq={to_send}")
    for seq in to_send:
        data_link.send(HDR.pack(DATA, seq) + lines[seq], rx.getsockname())
    try:
        while unacked:
            pkt, _ = tx.recvfrom(2048)
            unacked.discard(HDR.unpack_from(pkt)[1])
    except TimeoutError:
        to_send = sorted(unacked)
        send_log.append(f"  逾時，尚未確認 seq={to_send}")
stop.set()
t.join()
print("== sender ==", *send_log, sep="\n")
print("== receiver ==", *recv_log, sep="\n")
print("應用程式拿到：", [d.decode() for d in delivered])
assert delivered == lines
assert rounds == 2
for s in (tx, rx):
    s.close()
```

```text
== sender ==
第 1 輪送出 seq=[0, 1, 2, 3, 4, 5]
  [DATA 方向] 丟掉 DATA seq=1
  [DATA 方向] 延後 DATA seq=3
  逾時，尚未確認 seq=[1, 4]
第 2 輪送出 seq=[1, 4]
== receiver ==
收到 seq=0：交付 [0]
收到 seq=2：先暫存，等 seq=1
收到 seq=4：先暫存，等 seq=1
  [ACK 方向] 丟掉 ACK seq=4
收到 seq=3：先暫存，等 seq=1
收到 seq=5：先暫存，等 seq=1
收到 seq=1：交付 [1, 2, 3, 4, 5]
收到 seq=4：重複，丟棄（仍回 ACK）
應用程式拿到： ['line-0', 'line-1', 'line-2', 'line-3', 'line-4', 'line-5']
```

這段輸出可以和 9.7 節的時序圖逐行對照：

1. **第 1 輪**：sender 一次送出 seq 0–5。`LossyLink` 的計畫是：DATA 方向第 1 個送出的（seq=1）丟掉，第 3 個（seq=3）先扣住，等下一個送出後才送，於是接收端看到的順序是 0、2、4、3、5。
2. **receiver 端**：收到 0 立刻交付；收到 2、4、3、5 時 expected 還停在 1，只能暫存。注意它對每個收到的 datagram 都回了 ACK，所以 sender 知道 2、3、5 不用重送。
3. **ACK 也會丟**：ACK 方向第 2 個送出的 ACK（確認 seq=4 的那個）被丟掉了。這模擬了真實網路中「資料到了，但確認沒回來」的情況。
4. **逾時**：sender 等了 0.15 秒，還沒確認的有 seq=1（真的遺失）和 seq=4（ACK 遺失），於是第 2 輪重送這兩個。sender 無法分辨這兩種遺失，只能都重送，這是所有 ARQ（Automatic Repeat reQuest，自動重送請求）協定的本質限制。
5. **補上缺口**：seq=1 到達，receiver 一次交付 1、2、3、4、5，重排緩衝清空。
6. **去重**：重送的 seq=4 已經交付過，receiver 判定為重複並丟棄，但仍回 ACK，sender 才能停止重送。最後 `assert` 確認應用程式拿到的六行內容完整且有序，而且只花了 2 輪。

### 第三段：timeout、ICMP 錯誤、SO_REUSEADDR 與 ephemeral port

```python
import errno
import socket
import sys
import time

def udp():
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 1) 一個保證沒人在聽的 port：先 bind 拿到號碼，再關掉
probe = udp()
probe.bind(("127.0.0.1", 0))
dead_port = probe.getsockname()[1]
probe.close()

# 2) 沒有 connect 的 socket：送出去石沉大海，只能靠 timeout 發現
s = udp()
s.settimeout(0.3)
s.sendto(b"ping", ("127.0.0.1", dead_port))
start = time.monotonic()
try:
    s.recvfrom(2048)
except TimeoutError:
    print(f"未 connect：等了 {time.monotonic() - start:.1f} 秒後 TimeoutError")
print("  sendto 之前沒有 bind，系統自動綁到", s.getsockname())
s.close()

# 3) connect 過的 UDP socket：kernel 會把 ICMP port unreachable 轉成錯誤
c = udp()
c.settimeout(0.3)
c.connect(("127.0.0.1", dead_port))      # 不送任何封包，只是記住對端位址
print("connect 之後 local =", c.getsockname(), "peer =", c.getpeername())
c.send(b"ping")
try:
    c.recv(2048)
except ConnectionRefusedError as exc:
    print("已 connect：立刻收到", type(exc).__name__, f"(errno {exc.errno})")
c.close()

# 4) 兩個 socket 綁同一個 port
first = udp()
first.bind(("127.0.0.1", 0))
port = first.getsockname()[1]
second = udp()
try:
    second.bind(("127.0.0.1", port))
except OSError as exc:
    print("不設任何選項 bind 同一個 port：", errno.errorcode[exc.errno])
    assert exc.errno == errno.EADDRINUSE
first.close(); second.close()

a, b = udp(), udp()
for sock in (a, b):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
a.bind(("127.0.0.1", 0))
try:
    b.bind(a.getsockname())
    result = "成功"
except OSError as exc:
    result = errno.errorcode[exc.errno]
print(f"兩邊都設 SO_REUSEADDR（{sys.platform}）：", result)
a.close(); b.close()

if hasattr(socket, "SO_REUSEPORT"):
    a, b = udp(), udp()
    for sock in (a, b):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    a.bind(("127.0.0.1", 0))
    b.bind(a.getsockname())                  # Linux 與 BSD 系都允許
    print("兩邊都設 SO_REUSEPORT：成功，兩個 socket 共用", a.getsockname()[1])
    a.close(); b.close()

# 5) ephemeral port：每個沒 bind 的 socket 都拿到不同的臨時 port
clients = [udp() for _ in range(5)]
for e in clients:
    e.connect(("127.0.0.1", dead_port))      # connect 時就會分配 local port
ports = [e.getsockname()[1] for e in clients]
print("5 個 client socket 的 ephemeral port：", ports)
assert len(set(ports)) == 5 and all(p > 1023 for p in ports)
for e in clients:
    e.close()
```

以下是在 macOS 上的實際輸出（port 號碼每次執行都不同）：

```text
未 connect：等了 0.3 秒後 TimeoutError
  sendto 之前沒有 bind，系統自動綁到 ('0.0.0.0', 55832)
connect 之後 local = ('127.0.0.1', 60720) peer = ('127.0.0.1', 57548)
已 connect：立刻收到 ConnectionRefusedError (errno 61)
不設任何選項 bind 同一個 port： EADDRINUSE
兩邊都設 SO_REUSEADDR（darwin）： EADDRINUSE
兩邊都設 SO_REUSEPORT：成功，兩個 socket 共用 57954
5 個 client socket 的 ephemeral port： [56815, 61904, 58330, 62295, 53847]
```

逐段解說：

1. **沒有 connect 的 socket**：datagram 送往一個保證沒人在聽的 port。對方的 kernel 回了 ICMP port unreachable，但因為 socket 沒有 connect，錯誤沒有交給程式，`recvfrom` 只能等滿 0.3 秒然後 `TimeoutError`。這就是故事裡「卡死」的原因，只是小晴的版本沒有 timeout，所以永遠等下去。同一段也看到 `sendto` 之前沒有 bind，系統自動綁到 `0.0.0.0` 加一個 ephemeral port。
2. **connect 過的 socket**：`connect` 本身沒有送出任何封包，但已經決定了本地位址：來源 IP 變成 `127.0.0.1`（依路由選出），port 也分配好了。送出 `ping` 之後，ICMP 錯誤被轉成 `ConnectionRefusedError`，程式立刻知道對方不在。errno 61 是 macOS 的 `ECONNREFUSED`，Linux 上是 111。
3. **重複 bind**：不設任何選項時，第二個 socket bind 同一個 port 得到 `EADDRINUSE`，這在所有平台都一樣，`assert` 也只檢查這個行為。
4. **SO_REUSEADDR**：macOS（BSD 系）上，兩個 socket 都設 `SO_REUSEADDR` 仍然不能共用 unicast 的 UDP port；同一段程式在 Linux 上會印出「成功」。這行輸出刻意不寫 `assert`，因為它就是 9.6 節表格說的平台差異。
5. **SO_REUSEPORT**：兩個 socket 都設 `SO_REUSEPORT` 後可以共用同一個 port，Linux 和 macOS 都允許。至於 datagram 會交給哪一個 socket，依作業系統的實作而定。
6. **ephemeral port**：五個 client socket 在 `connect` 時各自分到不同的臨時 port，全都大於 1023，在 macOS 上落在 49152–65535 之間。

## 9.9 在工作上怎麼用

### 後端：寫 UDP 服務的檢查清單

小晴把探針伺服器重寫之後，整理了一份檢查清單，後來成為聲聲 Live 內部 UDP 服務的 code review 標準：

1. **每個等待回應的地方都有 timeout**，並且定義逾時後要做什麼（重試幾次、間隔多久、最後回報什麼錯誤）。
2. **接收緩衝設成協定允許的最大 datagram**，不要用 512 或 1024 這種憑感覺的數字；能用 `MSG_TRUNC` 或長度欄位偵測截斷更好。
3. **單一 datagram 控制在 1200 bytes 左右以內**，避免第 8 章的分片問題；需要送更大的資料，就在應用層切塊並加序號。
4. **訊息裡帶序號和時間戳**，就算不做重送，也能統計遺失、亂序與 RTT。探針的格式最後定為 `{seq, client_send_ms}`，server 原樣回傳。
5. **不要信任來源位址**：UDP 的來源位址可以偽造，任何驗證都要在應用層用 token 或簽章完成（第 30 章）。
6. **回應不要比請求大太多**，避免被利用來做放大攻擊（見下方 SRE 小節）。
7. **監控 kernel 的丟包計數器**，因為接收緩衝溢出時應用程式完全不會知道。

### SRE：確認 UDP 服務活著、封包有沒有到

UDP 沒有連線，所以 `curl` 和 `telnet` 這類「連得上就是活著」的檢查方法都不適用。阿德教小晴的排查順序是：先看 server 有沒有在聽，再看封包有沒有到，最後看 kernel 有沒有丟。

```bash
# 1. server 有沒有綁在正確的位址與 port（-u UDP、-a 全部、-p 顯示 process、-n 不反查）
ss -uapn 'sport = :9910'
lsof -nP -iUDP:9910

# 2. 從 client 端手動送一個 datagram（nc 的 -u 代表 UDP，-w 是等待秒數）
echo '{"seq":1}' | nc -u -w 1 10.20.3.21 9910

# 3. 在 server 上看封包有沒有進來、回應有沒有出去
sudo tcpdump -ni any udp port 9910

# 4. 看 kernel 有沒有因為緩衝區滿而丟包（Linux）
netstat -su | grep -i -E 'errors|receive buffer'
```

這組指令的判斷邏輯是由內往外。第 1 步確認程式確實綁在 `0.0.0.0:9910` 或正確的介面位址上，常見錯誤是只綁了 `127.0.0.1`，外面當然連不到。第 2 步用 `nc` 送一個測試訊息，有回應就代表整條路徑通。如果沒回應，第 3 步在 server 端抓封包：完全沒看到進來的封包，問題在路上（security group、防火牆、NAT、路由）；看到進來但沒有回應出去，問題在程式。第 4 步的計數器如果持續上升，代表程式讀得不夠快，要調大 `SO_RCVBUF` 或增加處理能力。

> [!tip] nc 沒回應不一定代表不通
> `nc -u` 送完就算數，沒有收到回應時不會顯示任何錯誤。如果 server 不是 echo 類型的服務（例如只收不回的 metrics collector），就只能靠第 3 步的 tcpdump 確認封包有到。

### SRE 與資安：UDP 放大攻擊的防禦

因為 UDP 沒有交握，攻擊者可以偽造來源位址，送一個小請求給某個 UDP 服務，讓服務把大很多倍的回應打到受害者身上，這叫 **反射放大攻擊（reflection amplification）**。歷史上被濫用過的包括開放的 DNS resolver、NTP、memcached 與 SSDP。防禦的方向有三個：服務端不要讓未經驗證的請求得到比請求本身大很多的回應（QUIC 規定在驗證 client 位址之前，server 送出的資料不能超過收到的三倍）；對每個來源限速，並且不要把內部 UDP 服務暴露到網際網路；網路業者在邊界做來源位址驗證（BCP 38），讓偽造位址的封包出不去。聲聲 Live 的探針伺服器只接受固定大小的請求、回應與請求一樣大，並且只在 security group 開放給講師端程式使用的位址範圍。

### 影音與前端：UDP 在哪裡、被擋了會怎樣

瀏覽器不讓網頁直接開 UDP socket，但 UDP 其實無所不在：HTTP/3 走 UDP 443（第 13、22 章），WebRTC 的媒體走 UDP（第 36 章），DNS 查詢大多走 UDP 53（第 14 章）。當企業網路擋掉 UDP 時，瀏覽器會退回 HTTP/2 over TCP，WebRTC 會退到 TURN over TCP 或 TLS，功能還能用但延遲變高。Joe 在處理「某公司的老師視訊特別卡」的客訴時，第一個問的就是「那間公司是不是擋了 UDP」。

| 場景 | 為什麼選 UDP | 要自己補的功能 | 本書章節 |
|---|---|---|---|
| DNS 查詢 | 一問一答，交握的成本比查詢本身還高 | 逾時重試、ID 比對；回應過大時改用 TCP | 第 14、15 章 |
| 即時語音與視訊 | 晚到的封包沒用，不想等重傳 | 序號、時間戳、jitter buffer、選擇性重送（NACK）、FEC、擁塞控制 | 第 34、36、37 章 |
| 多人連線遊戲 | 最新狀態比舊狀態重要，舊的丟了就算 | 序號、狀態快照、只對重要事件做可靠傳送 | 本章練習 |
| QUIC／HTTP/3 | 在 user space 實作新傳輸層，避開中間設備對 TCP 的限制 | 全部：加密、可靠、多 stream、擁塞控制，都由 QUIC 完成 | 第 13、22 章 |
| 直播 ingest（SRT） | 在有限延遲內重送，超過期限就放棄 | ARQ、latency 視窗、加密 | 第 38 章 |
| NTP、DHCP、syslog、metrics | 簡單、小封包、偶爾遺失可以接受 | 依協定而定，通常只有逾時重試 | — |

這張表最後一欄告訴你哪一章會深入。共通的模式是：選 UDP 從來不是因為「不需要可靠」，而是因為「需要的可靠性和 TCP 給的不一樣」，所以每個場景都在應用層補上剛好需要的那一部分。

### 雲端與 NAT：UDP 的「連線」會被忘記

UDP 沒有連線，但第 7 章的 NAT 和 stateful 防火牆仍然會為 UDP 流建立一筆追蹤紀錄，靠的是五元組和「最近一次看到封包的時間」。因為沒有 FIN 可以判斷結束，設備只能用閒置逾時清除紀錄，而這個逾時往往比 TCP 短很多。RFC 4787 建議 UDP mapping 的閒置逾時不短於 2 分鐘，但實際設備常常更短，依設備與設定而定。後果是：一個長時間不說話的 UDP 流，對方的回應可能被 NAT 擋掉。所以 WebRTC、VPN、遊戲都會定期送小小的 **keepalive** 封包，維持 NAT 上的紀錄。

> [!note] 2026 現況
> 截至 2026 年 10 月，Chrome、Edge、Firefox、Safari 等主要瀏覽器都支援 HTTP/3，大型 CDN 也已廣泛部署，所以「UDP 443 的流量」已經是正常網頁流量的一部分。各家統計的 HTTP/3 流量占比差異很大，本書不引用具體數字。企業防火牆擋 UDP 時瀏覽器會自動退回 HTTP/2，因此排查「某些使用者特別慢」時，值得確認對方是否只能走 TCP。另外，在 QUIC 上傳輸即時媒體的 Media over QUIC（MoQ）依 2026 年 10 月查證仍是 IETF 工作小組草案，尚未成為標準。

## 9.10 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| client 卡在 `recvfrom` 永遠不回來 | 沒有設 timeout，請求或回應遺失 | 用 `py-spy dump` 或加 log 看卡在哪一行；tcpdump 看回應有沒有回來 | `settimeout` 或 asyncio `wait_for`，並定義重試策略 |
| 偶爾收到不完整的訊息，JSON 解析失敗 | 接收緩衝小於 datagram，多餘部分被丟棄 | 比對送出端的訊息長度與 `recvfrom` 的 bufsize | bufsize 設成協定最大值；訊息裡帶長度欄位驗證 |
| 本機測試正常，上線後完全沒回應，也沒有錯誤 | security group、防火牆或 NAT 擋掉 UDP，或只開了 TCP | server 端 tcpdump 看不到進來的封包；檢查規則的協定欄位 | 開放正確的 UDP port 與來源範圍 |
| server 綁好了，但只有本機連得到 | bind 在 `127.0.0.1` 而不是 `0.0.0.0` 或對外介面 | `ss -uapn` 看 Local Address | bind 到正確的介面位址 |
| 重啟時 `Address already in use` | 舊 process 還在，或另一個程式佔用了 port | `ss -uapn`、`lsof -iUDP:<port>` 找出佔用者 | 停掉舊 process；確定需要時才用 `SO_REUSEPORT` |
| 加了 `SO_REUSEADDR` 後一部分請求沒回應 | 新舊兩個 socket 同時綁著同一個 port，封包被分給已不處理的那個 | `ss -uapn` 看到兩個 process 綁著同一個 port | 移除選項，修正部署流程確實停掉舊 process |
| 高峰時段丟包率上升，網路設備卻沒有丟包 | socket 接收緩衝滿了，kernel 丟包 | `netstat -su` 的 receive buffer errors、`/proc/net/snmp` 的 `RcvbufErrors` 持續增加 | 調大 `SO_RCVBUF`（以及系統上限）、加快處理、多個 socket 搭配 `SO_REUSEPORT` |
| 大訊息在某些網路上消失，小訊息正常 | datagram 超過路徑 MTU 被分片，分片被丟或被防火牆擋 | tcpdump 看到分片（`frag`）；縮小訊息後恢復正常 | 單一 datagram 控制在 1200 bytes 左右，應用層自己切塊 |
| 閒置一陣子後收不到對方的訊息 | NAT 或防火牆的 UDP 追蹤紀錄逾時被清除 | 閒置時間與失效時間相關；縮短間隔後恢復 | 定期送 keepalive，間隔小於最短的 NAT 逾時 |
| 在送出端 tcpdump 看到 `bad udp cksum` | checksum offload，網卡才計算 checksum | 在接收端抓封包，checksum 正確 | 不需要修；分析時以接收端的封包為準 |

這張表的前三列對應故事裡小晴遇到的問題，也是 UDP 新手最常犯的三類錯誤：以為一定有回應、以為讀多少都可以、以為沒有錯誤就代表送到了。排查 UDP 問題時，最有用的一個習慣是「兩端同時抓封包」：client 端看得到送出、server 端看不到進來，問題就在中間；兩端都看得到，問題就在程式。

## 9.11 動手練習

1. **延伸 echo server：量 RTT 與丟包率**。修改 9.8 節第一段程式，讓 client 每 20 毫秒送一個帶序號與 `time.monotonic_ns()` 的探針，共 50 個，server 原樣回傳，並在 server 端用 `random.Random(7)` 隨機丟掉約 10% 的回應。client 統計平均 RTT、最大 RTT 與丟包率。驗證方法：丟包率應接近 10%，而且每次執行結果相同（因為固定了亂數種子）；RTT 在 loopback 上應遠小於 1 毫秒。
2. **延伸重送程式：加上 exponential backoff 與重試上限**。修改 9.8 節第二段，讓每一輪逾時時間加倍（0.05、0.1、0.2、0.4 秒），最多等 4 輪，超過就放棄並回報哪些序號失敗。把 `LossyLink` 的計畫改成「seq=1 每次都丟」，確認程式會在第 4 輪後放棄，而且總等待時間符合 0.05 + 0.1 + 0.2 + 0.4 秒的預期。答案要點：放棄時必須讓上層知道，而不是默默丟掉。
3. **用真實工具觀察 UDP**。在自己的電腦上用 `nc -u -l 9999` 開一個 UDP listener，另一個終端機用 `nc -u 127.0.0.1 9999` 送幾行文字，同時用 `sudo tcpdump -ni lo0 udp port 9999 -X`（Linux 用 `-i lo`）觀察。驗證方法：每按一次 Enter 對應一個 UDP 封包，tcpdump 顯示的 length 等於該行文字長度加上換行字元；試著關掉 listener 再送，看看 tcpdump 是否出現 ICMP port unreachable。
4. **觀察 DNS 的 UDP 與 TCP**。執行 `dig example.com` 與 `dig +tcp example.com`，比較輸出最後的 `SERVER` 行與 `Query time`，再用 tcpdump 同時抓 `port 53`。驗證方法：第一個查詢只看到兩個 UDP 封包（一問一答），第二個會看到 TCP 三向交握、查詢、回應與關閉，封包數多很多。思考：為什麼 DNS 預設用 UDP？
5. **思考題：設計一個簡單的遊戲同步協定**。聲聲 Live 想做一個「單字搶答」小遊戲，每位學生每秒回報 20 次游標位置，並偶爾送出「搶答」事件。請說明哪些訊息可以遺失、哪些必須可靠，並設計 datagram 格式（欄位與大小）。答案要點：游標位置只要最新的，帶序號讓接收端丟棄舊的即可；搶答事件要 ACK 與重送，並帶唯一 ID 讓 server 去重，避免重送造成重複計分。

## 本章重點整理

- port 是 16-bit 的主機內門牌，傳輸層靠它把封包交給正確的 socket；port 0 不能用來通訊，bind 時填 0 代表請系統分配。
- 五元組（協定、來源 IP、來源 port、目的 IP、目的 port）唯一識別一個通訊流，NAT、load balancer 與防火牆都以它為單位運作。
- client 沒有指定 port 時，系統會在 bind、第一次 sendto 或 connect 時分配 ephemeral port，範圍依作業系統而定（Linux 預設 32768–60999，macOS 預設 49152–65535）。
- UDP header 只有 8 bytes：來源 port、目的 port、長度、checksum；checksum 涵蓋 pseudo header 裡的 IP 位址，在 IPv6 上原則上必須計算。
- UDP 是無連線的：不需要交握，也沒有人會告訴你對方不在，所以每個等待回應的 recvfrom 都必須設 timeout。
- UDP 是不可靠的：datagram 可能遺失、重複、亂序，接收緩衝滿了 kernel 也會丟，應用程式要自己用序號偵測。
- UDP 保留訊息邊界：一次 sendto 對應一次 recvfrom；TCP 是 byte stream，必須自己做 framing。
- 接收緩衝小於 datagram 時，多餘的資料會被丟棄而不是留到下一次讀；空 datagram 是合法訊息，不代表關閉。
- 單一 datagram 最好控制在 1200 bytes 左右，避免分片；IPv4 的硬上限是 65507 bytes。
- connect 過的 UDP socket 會過濾來源，並把 ICMP port unreachable 轉成 ConnectionRefusedError；但 ICMP 可能被擋，不能當成存活檢查。
- SO_REUSEADDR 與 SO_REUSEPORT 在 UDP 上代表「允許多個 socket 共用 port」，行為隨平台而異；UDP 沒有 TIME_WAIT，重啟時 port 被佔用通常代表真的還有程式在用。
- 在 UDP 上補回可靠性需要序號、ACK、逾時重送與重排緩衝，接收端對重複的訊息也要回 ACK；真實協定還要加上 RTT 估計、指數退避與擁塞控制。
- 選 UDP 的理由是「需要的可靠性和 TCP 不同」：DNS 要低成本的一問一答，影音與遊戲不想等晚到的資料，QUIC 要在 user space 演進傳輸層。
- 排查 UDP 問題時，兩端同時抓封包、檢查 socket 綁定位址、監控 kernel 的接收緩衝丟包計數器，是最有效的三個動作。

## 延伸問答

> [!question]- Q1. UDP 是「無連線」的，那為什麼 UDP socket 也有 connect()？它和 TCP 的 connect() 有什麼不同？
> TCP 的 connect 會送出 SYN、完成三向交握，在兩端都建立連線狀態，失敗時（例如對方回 RST）會立刻得知。UDP 的 connect 完全不送封包，只是在本機 kernel 記住「這個 socket 的預設對端」，所以就算對方主機不存在，UDP 的 connect 也會成功。
>
> 記住對端之後有四個效果：之後可以用 send／recv 而不必每次帶位址；kernel 只把來自該對端的 datagram 交給這個 socket；ICMP 錯誤（如 port unreachable）會轉成 ConnectionRefusedError 交給程式；connect 當下就會依路由選好來源 IP 與 ephemeral port。所以 client 只跟一個 server 說話時，建議一律 connect；server 要服務多個 client，則保持不 connect。

> [!question]- Q2. 手算：一個 IPv4 UDP datagram 的 payload 是 1200 bytes，UDP 的 Length 欄位、IP 封包總長度、乙太網路 frame 的大小各是多少？會不會被分片？
> UDP Length 包含 header 與 payload：8 + 1200 = 1208 bytes。IPv4 header 在沒有 options 時是 20 bytes，所以 IP 封包總長度是 1228 bytes，小於乙太網路 MTU 1500，不會被分片。IPv4 上 UDP payload 不分片的上限是 1500 − 20 − 8 = 1472 bytes。
>
> 乙太網路 frame 再加上 14 bytes 的 Ethernet header 與 4 bytes 的 FCS，是 1246 bytes（不含 preamble 與 frame 間隔）。如果走 IPv6，header 是 40 bytes，總長度 1248 bytes，仍低於 IPv6 最小 MTU 1280，所以在任何合規的 IPv6 路徑上都不需要分片。這就是 QUIC 把 1200 bytes 當成基準大小的原因：它在 IPv4 與 IPv6、加上一些隧道開銷後，都還有餘裕。

> [!question]- Q3. 你在 production 看到 UDP 服務的 log 顯示每秒處理量正常，但 client 回報丟包率 5%。網路團隊說交換器與路由器都沒有丟包。你會怎麼查？
> 先懷疑最容易被忽略的一段：server 主機自己的 socket 接收緩衝。datagram 到了主機，但程式讀得不夠快、佇列滿了，kernel 會直接丟棄，應用程式的 log 完全看不到，網路設備的計數器也不會增加。在 Linux 上看 `netstat -su` 的 receive buffer errors 或 `/proc/net/snmp` 的 RcvbufErrors，如果持續上升就是這個原因；`ss -uampn` 可以看到該 socket 佇列的使用量。
>
> 確認之後的修法依序是：調大 SO_RCVBUF（注意系統上限 net.core.rmem_max）、把耗時的處理移出收包迴圈、用多個 socket 搭配 SO_REUSEPORT 分散到多個 CPU。如果計數器沒有增加，再往外查：主機網卡的 drop 計數、雲端的 security group 或流量限制，最後兩端同時 tcpdump 比對序號，找出封包在哪一段消失。

> [!question]- Q4. 面試題：為什麼 DNS 主要用 UDP，而不是 TCP？什麼時候 DNS 會改用 TCP？
> DNS 查詢多半是一個小請求加一個小回應，用 UDP 只要一個 RTT 就完成，伺服器也不必為每個 client 維護連線狀態，一台 resolver 就能服務大量 client。如果用 TCP，光是三向交握就多一個 RTT，再加上連線狀態的記憶體與關閉的成本，對這種一問一答的流量來說很不划算。遺失的問題由 client 用逾時重試處理，查詢本身是 idempotent 的，重送沒有副作用。
>
> 改用 TCP 的情況有：回應太大，伺服器在 UDP 回應中設定 TC（truncated）旗標，client 改用 TCP 重問；zone transfer（AXFR／IXFR）傳輸大量資料；以及加密的 DNS over TLS 與部分 DNS over HTTPS。EDNS(0) 讓 UDP 能攜帶更大的回應，但為了避免分片，業界建議的 EDNS 緩衝大小約 1232 bytes，正好對應 IPv6 最小 MTU 扣掉 header。細節在第 14、15 章。

> [!question]- Q5. 看 log 找原因：同事的 UDP client 在 Linux 上偶爾拋出 ConnectionRefusedError，但 server 明明一直在跑。可能是什麼原因？
> ConnectionRefusedError 在 UDP 上來自 ICMP port unreachable，而且只有 connect 過的 socket 會收到。所以首先確認：client 是否 connect 到了一個「某些時候沒有 socket 在聽」的位址。常見情境是 server 正在重啟，在舊 process 關閉、新 process bind 之前的那一瞬間，送達的 datagram 觸發了 ICMP；或者 DNS 回了多個 IP，其中一台主機上服務沒在跑；或者 load balancer 把流量導到一台還沒準備好的後端。
>
> 另一個容易誤會的地方是，這個錯誤可能是「上一個」datagram 造成的：ICMP 是非同步回來的，kernel 在下一次 send 或 recv 才把錯誤交給程式，所以 log 中出錯的那一次呼叫，未必是觸發它的那一次。修法是把它當成可重試的暫時錯誤，搭配退避重試，並檢查部署流程是否讓新舊 process 之間出現空窗。

> [!question]- Q6. 概念辨析：UDP 保留訊息邊界、TCP 是 byte stream。那在 TCP 上送 JSON 訊息和在 UDP 上送 JSON 訊息，接收端的程式各要怎麼寫？
> UDP 上，每次 recvfrom 拿到的就是一個完整的 datagram，只要 bufsize 夠大，直接 json.loads 即可，不需要處理半個訊息或兩個訊息黏在一起。要注意的是訊息必須小到能放進一個 datagram（實務上 1200 bytes 左右），而且接收端要能容忍遺失、重複與亂序，例如用訊息中的序號或 ID 去重。
>
> TCP 上，一次 recv 可能拿到半個 JSON，也可能拿到一個半，所以送出端必須定義 framing，例如每則訊息前面加 4 bytes 的長度，或用換行分隔且保證 JSON 本身不含換行。接收端維護一個緩衝區，不斷 recv 並附加進去，每湊滿一則完整訊息就切出來解析，剩下的留給下一輪。TCP 保證不遺失、不重複、不亂序，所以不需要序號，但需要 framing；UDP 剛好相反。第 11 章會實作 TCP 的長度前綴 framing。

> [!question]- Q7. 設計取捨：聲聲 Live 的「網路體檢」探針要不要做重送？如果要量丟包率，重送會造成什麼問題？
> 不應該重送。探針的目的就是量測網路本身的遺失率與 RTT，如果遺失時自動重送，丟包就被藏起來了，量到的丟包率會偏低，RTT 也會因為重送的等待而失真。正確的做法是每個探針帶唯一序號與送出時間，server 原樣回傳，client 在固定的逾時（例如 1 秒）內沒收到就記為遺失，晚到的回應則另外記為「晚到」而不重複計算。
>
> 這個例子說明了選 UDP 的真正理由：應用程式能精確控制遺失時的行為。TCP 會自動重傳，應用程式看到的永遠是「慢了一點但完整」的資料，無法區分網路丟包與單純的延遲。視訊本身也是同樣的道理，晚到的畫面不如跳過，所以 WebRTC 只對少數重要封包做選擇性重送，而不是全部重送（第 37 章）。

> [!question]- Q8. 你要讓 UDP server 零停機更新版本，同事提議「新舊 process 都設 SO_REUSEPORT，新的起來後再關舊的」。這個方案有什麼要注意的地方？
> 方向是對的，但有幾個細節。第一，在 Linux 上 SO_REUSEPORT 會依五元組 hash 把 datagram 分給所有綁著該 port 的 socket，所以新舊並存的期間，部分 client 仍會打到舊 process，舊 process 必須持續正常服務，直到它關閉 socket 為止；不能先停止處理、卻保留 socket，否則那部分 client 的封包會被丟進沒人讀的佇列。第二，socket 數量改變時，hash 分配也會改變，同一個 client 可能從一個 process 換到另一個，如果 server 有每個 client 的狀態（例如統計或 session），要能容忍這種切換或把狀態放在共享的地方。
>
> 第三，舊 process 關閉 socket 時，它佇列裡還沒讀的 datagram 會被丟掉，所以應該先停止接新工作、把佇列讀完再關。第四，Linux 要求所有共用 port 的 socket 屬於同一個使用者，避免其他程式劫持；macOS 等 BSD 系統的分配方式不同，要另外測試。最後，這只解決「port 交接」，client 端仍要有逾時與重試，才能吸收切換瞬間的少量遺失。

## 延伸閱讀

- RFC 768〈User Datagram Protocol〉
- RFC 8085〈UDP Usage Guidelines〉
- RFC 6335〈Internet Assigned Numbers Authority (IANA) Procedures for the Management of the Service Name and Transport Protocol Port Number Registry〉
- RFC 4787〈Network Address Translation (NAT) Behavioral Requirements for Unicast UDP〉
- RFC 1071〈Computing the Internet Checksum〉
- W. Richard Stevens、Bill Fenner、Andrew M. Rudoff，《UNIX Network Programming, Volume 1: The Sockets Networking API》
- Python 官方文件〈socket — Low-level networking interface〉與〈asyncio — Transports and Protocols〉
