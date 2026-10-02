---
chapter: 4
title: Ethernet、MAC、ARP 與交換器
part: 1
---

# 第 4 章　Ethernet、MAC、ARP 與交換器

> [!abstract] 本章地圖
> **核心問題**：封包已經寫好了目的 IP，為什麼還需要 MAC 位址、ARP 與交換器，才能真的送到隔壁那台機器？
>
> **你會學到**：
> - 畫出 Ethernet frame 的欄位布局，看懂 tcpdump 的 `-e` 輸出與 EtherType
> - 從一個 MAC 位址判斷它是單播、群播、全球唯一還是本地管理
> - 說明交換器如何學習、轉送、過濾與 flood，並推演 MAC 表的變化
> - 逐步追蹤 ARP 請求與回應、ARP 快取的逾時，以及 gratuitous ARP 的用途
> - 判斷一個封包該直接送給目的主機還是交給 gateway，並解釋為什麼 IP 不變、MAC 每一跳都換
> - 理解廣播網域與 VLAN，並說出 Wi-Fi 和有線 Ethernet 在連結層的差異
>
> **前置知識**：第 2 章（分層與封裝、header 與 byte order）、第 3 章（tcpdump 與 ping 的基本用法）

## 4.1 故事：週五講座前二十分鐘，備用編碼器「連不上」

聲聲 Live 每個月有一場熱門公開講座，由辦公室裡的小型攝影棚直播。攝影棚有自己的一段區域網路 10.30.0.0/24：一台硬體編碼器（10.30.0.21）把畫面用 SRT 推到雲端的直播 ingest（`live.shengsheng.example`，203.0.113.25），一台 NAS（10.30.0.31）同時在本地錄一份備份，路由器（10.30.0.1）是這段網路的出口。所有設備都插在同一台 24 埠的交換器上。

週五晚上七點四十分，編碼器的風扇壞了，畫面開始掉格。Joe 立刻換上備用機：把網路設定照抄一份，IP 一樣是 10.30.0.21，接在交換器的另一個埠。備用機開機後，前面板顯示推流成功，雲端也收到了畫面；但 NAS 上的錄影程式卻一直顯示「encoder unreachable」，從 NAS ping 10.30.0.21 完全沒有回應。過了一兩分鐘，錄影又自己恢復了。

同一時間，小晴在幫忙設定一台新的監看電腦。那台電腦可以 ping 到同網段的 NAS，卻打不開任何外部網站。小晴檢查了 DNS、檢查了防火牆，最後才發現 gateway 欄位填成了 10.30.0.254，一個根本不存在的位址。

講座結束後，阿德把兩件事放在一起講：「這兩個問題都不在 IP 層，也不在 TCP。它們發生在 IP 下面那一層：誰的 MAC 位址是多少、交換器記得誰在哪個埠、封包出網段時要先交給誰。」NAS 那一兩分鐘的空白，是因為 NAS 的 **ARP 快取**還記得舊編碼器的 MAC 位址，封包一直送給一台已經當機的機器。監看電腦的問題，則是要出網段的封包必須先送到 gateway，而 gateway 的 MAC 位址根本問不到。

這一章就從這兩個問題出發，往下打開「同一條網路線上」到底發生了什麼。讀完之後，你會知道 NAS 為什麼會自己恢復、Joe 換機器時可以做什麼讓它立刻恢復，以及小晴那台電腦送出去的封包是在哪一步卡住的。

## 4.2 IP 位址還不夠：連結層要解決的問題

第 2 章說過，網路是分層的：IP 負責「從來源主機到目的主機」的端到端定址，而 IP 下面的**連結層（link layer）**負責「在同一段實體網路上，從這一台送到下一台」。這兩件事聽起來很像，實際上回答的是不同問題。IP 回答「最後要到哪裡」，連結層回答「現在這一步要交給誰」。

用寄包裹來比喻：IP 位址像收件人的地址，寫在包裹上，從頭到尾不會改；連結層位址像每一段運送時貨車司機拿到的「下一站交給誰」的便條，每經過一個轉運站就換一張。從台北寄到高雄，包裹上的地址一直是高雄，但第一段的便條寫的是「交給台北轉運站」，第二段寫的是「交給台中轉運站」。

為什麼不能只用 IP？原因有三個。第一，實體網路只認得自己的位址：網卡接收電訊號時，只能用硬體層級的位址判斷「這個 frame 是不是給我的」，網卡不懂 IP。第二，IP 位址是可以重新設定、可以搬家的邏輯位址，而連結層需要一個在這段網路上能直接分辨每張網卡的識別碼。第三，IP 下面不只 Ethernet，還有 Wi-Fi、行動網路、光纖鏈路，各種連結層技術各有自己的位址與格式；IP 只要求「把這個封包送到下一跳」，具體怎麼送交給連結層。

```text
 encoder (10.30.0.21)     路由器 (10.30.0.1)        ……        ingest (203.0.113.25)
       │                         │                                    │
       │  第 1 跳 frame                                                │
       │  MAC：encoder → 路由器                                        │
       │  IP ：10.30.0.21 → 203.0.113.25                              │
       │────────────────────────►│                                    │
       │                         │  第 2 跳 frame                      │
       │                         │  MAC：路由器 → ISP 設備（換新的）     │
       │                         │  IP ：10.30.0.21 → 203.0.113.25（不變，NAT 見第 7 章）
       │                         │──────────► …… ────────────────────►│
```

這張圖是本章最重要的一張圖。第一跳時，encoder 把 IP 封包包進一個 Ethernet frame，frame 的目的 MAC 位址是路由器，不是 ingest。路由器收到後拆掉這個 frame，看 IP header 決定下一跳，再包進一個新的 frame，換上新的來源與目的 MAC。IP header 裡的目的地從頭到尾都是 203.0.113.25（中途若經過 NAT，來源 IP 會被改寫，這是第 7 章的主題）。小晴的監看電腦卡住的位置，就是第一跳：封包要交給 gateway，但 gateway 的 MAC 問不到，frame 根本組不出來。

## 4.3 Ethernet frame：連結層的信封

**Ethernet** 是今天有線區域網路幾乎唯一的技術，規格由 IEEE 802.3 定義。Ethernet 傳送的單位叫 **frame**：一段有固定開頭與結尾的 bytes，裡面裝著上一層（通常是 IP）的封包。例如 NAS 送一個 ping 給編碼器時，ICMP 包在 IP 封包裡，IP 封包再包在一個 Ethernet frame 裡。

```text
 在線路上（網卡負責，tcpdump 通常看不到）
 ┌──────────────────────┬─────┐
 │ Preamble 7 bytes      │ SFD │   10101010 × 7 ＋ 10101011：讓接收端對準時脈、找到 frame 開頭
 └──────────────────────┴─────┘
 Frame 本體（從這裡開始算 frame 長度）
  0                   6                   12      14                         14+N     +4
 ┌───────────────────┬───────────────────┬───────┬──────────────────────────┬───────┐
 │ 目的 MAC 6 bytes   │ 來源 MAC 6 bytes   │ Type  │ Payload 46–1500 bytes     │  FCS  │
 │ Destination        │ Source             │ 2 B   │（IP 封包、ARP…，不足補 0）  │ 4 B   │
 └───────────────────┴───────────────────┴───────┴──────────────────────────┴───────┘
  最小 64 bytes（14 + 46 + 4），最大 1518 bytes（14 + 1500 + 4）；之後至少 12 bytes 的 interframe gap
```

逐欄來看。**Preamble** 與 **SFD（Start Frame Delimiter）**是給硬體對時用的固定位元樣式，網卡收完就丟掉，所以 tcpdump 和 Wireshark 通常看不到。**目的 MAC** 放在最前面是刻意的設計：網卡讀到前 6 bytes，就能決定這個 frame 要不要收下，不必等整個 frame 到齊。**來源 MAC** 讓接收端知道是誰送的，交換器也靠這個欄位學習。

**Type** 欄位兩個 bytes，叫 **EtherType**，告訴接收端 payload 是什麼協定，作用就像第 2 章 IP header 裡的 protocol 欄位。值大於等於 0x0600（十進位 1536）時是 EtherType；小於等於 1500 時，在舊的 802.3 格式裡表示 payload 長度。今天網路上看到的 IP、ARP 流量幾乎全是 EtherType 格式，這種格式常被稱為 Ethernet II。

**Payload** 最少 46 bytes、最多 1500 bytes。上限 1500 就是常聽到的 **MTU（Maximum Transmission Unit）**：一個 frame 能裝的最大上層封包大小。第 2 章說過 IPv4 header 最少 20 bytes、TCP header 最少 20 bytes，所以一個 1500 bytes 的 IP 封包最多帶 1460 bytes 的 TCP 資料；MTU 不一致造成的問題留到第 8 章。下限 46 bytes 來自早期共享線路偵測碰撞的需要，payload 不夠長時要補 0（**padding**），所以一個只有 28 bytes 的 ARP 訊息，在線路上會被補到 46 bytes。

**FCS（Frame Check Sequence）**是整個 frame（從目的 MAC 到 payload）的 CRC-32 檢查碼。接收端重算一次，不符就直接丟棄，**不會通知任何人**。這一點很關鍵：Ethernet 只負責偵測錯誤，不負責重傳；壞掉的 frame 消失了，要靠上層（例如 TCP，第 11 章）發現資料沒到而重送。網路線接觸不良時，交換器埠的 CRC error 計數會上升，這是除錯時很有用的線索。

| EtherType | 協定 | 在哪裡會看到 |
|---|---|---|
| 0x0800 | IPv4 | 幾乎所有一般流量 |
| 0x0806 | ARP | 本章 4.7 節：用 IP 問 MAC |
| 0x86DD | IPv6 | 雙堆疊網路（第 5 章） |
| 0x8100 | 802.1Q VLAN tag | trunk 線路上的 frame（本章 4.9 節） |
| 0x88A8 | 802.1ad（QinQ）外層 tag | 電信業者的網路，一個 VLAN 再包一層 |
| 0x88CC | LLDP | 交換器與設備互相宣告身分，用來查「這條線接到哪」 |

下面這段程式用 `struct` 組出一個完整的 ARP 請求 frame，印出每個 byte，再解析回來並驗證 FCS。ARP 的欄位意義在 4.7 節解釋，這裡先看 frame 的外框。

```python
import struct
import zlib


def mac_bytes(text):
    return bytes.fromhex(text.replace(":", ""))


def mac_text(raw):
    return ":".join(f"{b:02x}" for b in raw)


def arp_request(sender_mac, sender_ip, target_ip):
    # ARP 本體 28 bytes：硬體類型 1（Ethernet）、協定類型 0x0800（IPv4）、長度 6 與 4、op 1（request）
    arp = struct.pack("!HHBBH6s4s6s4s", 1, 0x0800, 6, 4, 1,
                      mac_bytes(sender_mac), bytes(map(int, sender_ip.split("."))),
                      bytes(6), bytes(map(int, target_ip.split("."))))
    header = mac_bytes("ff:ff:ff:ff:ff:ff") + mac_bytes(sender_mac) + struct.pack("!H", 0x0806)
    body = header + arp
    body += bytes(max(0, 60 - len(body)))      # 補到最小 60 bytes（不含 FCS）
    fcs = struct.pack("<I", zlib.crc32(body))  # FCS 是 CRC-32，依慣例低位元組先送
    return body + fcs


frame = arp_request("02:00:00:00:00:31", "10.30.0.31", "10.30.0.21")
for off in range(0, len(frame), 16):
    chunk = frame[off:off + 16]
    print(f"{off:04x}  {chunk.hex(' ')}")

dst, src, etype = struct.unpack("!6s6sH", frame[:14])
htype, ptype, hlen, plen, op, sha, spa, tha, tpa = struct.unpack("!HHBBH6s4s6s4s", frame[14:42])
print(f"dst={mac_text(dst)} src={mac_text(src)} ethertype=0x{etype:04x}")
print(f"op={op} sender={mac_text(sha)}/{'.'.join(map(str, spa))} target={mac_text(tha)}/{'.'.join(map(str, tpa))}")
print(f"總長 {len(frame)} bytes（header 14 + ARP 28 + padding {60 - 42} + FCS 4）")

# 接收端驗證：重算 CRC 與尾端 FCS 比對；位元翻轉一個就會失敗
assert struct.pack("<I", zlib.crc32(frame[:-4])) == frame[-4:]
broken = bytearray(frame)
broken[20] ^= 0x01
assert struct.pack("<I", zlib.crc32(bytes(broken[:-4]))) != bytes(broken[-4:])
print("FCS 正確；翻轉 1 個 bit 後 FCS 不符，網卡會直接丟棄")
```

```text
0000  ff ff ff ff ff ff 02 00 00 00 00 31 08 06 00 01
0010  08 00 06 04 00 01 02 00 00 00 00 31 0a 1e 00 1f
0020  00 00 00 00 00 00 0a 1e 00 15 00 00 00 00 00 00
0030  00 00 00 00 00 00 00 00 00 00 00 00 e4 80 e3 fc
dst=ff:ff:ff:ff:ff:ff src=02:00:00:00:00:31 ethertype=0x0806
op=1 sender=02:00:00:00:00:31/10.30.0.31 target=00:00:00:00:00:00/10.30.0.21
總長 64 bytes（header 14 + ARP 28 + padding 18 + FCS 4）
FCS 正確；翻轉 1 個 bit 後 FCS 不符，網卡會直接丟棄
```

輸出第一行的前 6 bytes `ff ff ff ff ff ff` 是目的 MAC（廣播），接著 6 bytes `02 00 00 00 00 31` 是 NAS 的 MAC，然後 `08 06` 是 EtherType，表示後面是 ARP。從 0x000e 開始的 28 bytes 是 ARP 本體，其中可以讀到 `0a 1e 00 1f`，也就是 10.30.0.31（0x0a=10、0x1e=30、0x1f=31）。ARP 只有 28 bytes，加上 header 14 bytes 只有 42 bytes，所以補了 18 個 0，最後 4 bytes 是 FCS，總長剛好是最小的 64 bytes。最後的 assert 示範了 CRC 的作用：只翻轉一個 bit，重算出來的檢查碼就不同。

實際用 tcpdump 抓封包時，看到的長度常是 42 而不是 64：送出端的 padding 與 FCS 通常由網卡硬體加上，作業系統抓到的是加上之前的樣子。不要因為抓到 42 bytes 的 ARP 就以為 frame 太短。

> [!warning] 常見誤解
> 「MTU 1500 指的是 frame 大小 1500 bytes。」不對。MTU 是 payload 的上限，也就是 IP 封包最大 1500 bytes；整個 frame 加上 header 與 FCS 是 1518 bytes，帶 VLAN tag 時是 1522 bytes。資料中心常用的 **jumbo frame** 把 MTU 拉到 9000 左右，但必須整條路徑上的每台設備都設定一致，否則大封包會在中途被丟掉。

## 4.4 MAC 位址：網卡的名字

**MAC 位址（Media Access Control address）**是連結層的位址，長度 48 bits，通常寫成 6 組十六進位數字，例如 `00:1b:21:3a:4f:10`（Windows 習慣用 `-` 分隔，Cisco 設備常寫成 `001b.213a.4f10`，三種寫法是同一個位址）。每張網卡出廠時燒錄一個 MAC，作業系統也可以改寫。

48 bits 不是一串隨機數字，第一個 byte 的最低兩個 bit 有特殊意義：

```text
 第 1 個 byte（以 0x02 為例）                       後面 5 bytes
  bit 7  6  5  4  3  2  1  0
 ┌──┬──┬──┬──┬──┬──┬──┬──┐ ┌──────┬──────┐ ┌──────┬──────┬──────┐
 │ 0│ 0│ 0│ 0│ 0│ 0│ 1│ 0│ │ 0x00 │ 0x00 │ │ 0x00 │ 0x00 │ 0x31 │
 └──┴──┴──┴──┴──┴──┴──┴──┘ └──────┴──────┘ └──────┴──────┴──────┘
                      │  │  ◄──── 前 3 bytes：OUI ───►  ◄─ 後 3 bytes：廠商自行編號 ─►
                      │  └─ bit 0：I/G，0 = 單播（individual），1 = 群組（multicast／broadcast）
                      └──── bit 1：U/L，0 = 全球唯一（廠商配發），1 = 本地管理（自行指定）
```

**I/G bit**（Individual/Group）決定這是單播還是群組位址。單播位址指向一張網卡；群組位址可以同時被很多張網卡接收。全部 48 bits 都是 1 的 `ff:ff:ff:ff:ff:ff` 是**廣播位址**，同一段網路上的每張網卡都要收下。**U/L bit**（Universal/Local）為 0 時，前 3 bytes 是 IEEE 配發給廠商的 **OUI（Organizationally Unique Identifier）**，後 3 bytes 由廠商自行編號，理論上全球唯一；為 1 時表示這是本地管理的位址，例如虛擬機、容器或手機的隨機 MAC。本章所有範例都用 `02:` 開頭的位址，就是因為它的 U/L bit 是 1，不會撞到任何真實廠商的位址。

```python
import ipaddress


def describe(mac):
    first = int(mac.split(":")[0], 16)
    kind = "群播／廣播（I/G=1）" if first & 0b01 else "單播（I/G=0）"
    if first & 0b01:
        scope = "群組位址，一張網卡可以同時收很多個"
    else:
        scope = "本地管理（U/L=1）" if first & 0b10 else "全球唯一（U/L=0，前 3 bytes 是 OUI）"
    return f"{mac}  {kind}   {scope}"


def ipv4_multicast_mac(group):
    # IPv4 群播對應 MAC：固定前綴 01:00:5e，再放 IP 的低 23 bits
    low23 = int(ipaddress.IPv4Address(group)) & 0x7FFFFF
    return "01:00:5e:" + ":".join(f"{(low23 >> s) & 0xFF:02x}" for s in (16, 8, 0))


for m in ("00:1b:21:3a:4f:10", "02:00:00:00:00:31", "ff:ff:ff:ff:ff:ff", "33:33:00:00:00:01"):
    print(describe(m))

for g in ("239.1.1.1", "224.0.0.251", "239.129.1.1"):
    print(f"群播 {g:<12} → {ipv4_multicast_mac(g)}")

# 低 23 bits 相同的兩個群組會撞到同一個 MAC，網卡收下後要靠 IP 層再過濾
assert ipv4_multicast_mac("239.1.1.1") == ipv4_multicast_mac("239.129.1.1")
assert describe("ff:ff:ff:ff:ff:ff").count("群播") == 1
print("239.1.1.1 與 239.129.1.1 共用同一個 MAC")
```

```text
00:1b:21:3a:4f:10  單播（I/G=0）   全球唯一（U/L=0，前 3 bytes 是 OUI）
02:00:00:00:00:31  單播（I/G=0）   本地管理（U/L=1）
ff:ff:ff:ff:ff:ff  群播／廣播（I/G=1）   群組位址，一張網卡可以同時收很多個
33:33:00:00:00:01  群播／廣播（I/G=1）   群組位址，一張網卡可以同時收很多個
群播 239.1.1.1    → 01:00:5e:01:01:01
群播 224.0.0.251  → 01:00:5e:00:00:fb
群播 239.129.1.1  → 01:00:5e:01:01:01
239.1.1.1 與 239.129.1.1 共用同一個 MAC
```

前四行分別是：一個全球唯一的單播位址（前 3 bytes 是某家廠商的 OUI）、本書範例使用的本地管理位址、廣播位址，以及 `33:33:` 開頭的 IPv6 群播位址。後半段示範 IPv4 群播（例如區網內的 mDNS 用 224.0.0.251）如何對應到 MAC：固定前綴 `01:00:5e`，再放 IP 位址的低 23 bits。IPv4 群播位址有 28 bits 可變，只放得下 23 bits，所以 32 個群組會共用一個 MAC，網卡收下後要由 IP 層再過濾一次，assert 驗證了 239.1.1.1 和 239.129.1.1 撞在一起。

| 位址種類 | 範例 | 誰會收下 | 典型用途 |
|---|---|---|---|
| 單播 | `02:00:00:00:00:21` | 只有那張網卡 | 一般資料傳輸 |
| 廣播 | `ff:ff:ff:ff:ff:ff` | 同一廣播網域的所有網卡 | ARP 請求、DHCP 探索 |
| IPv4 群播 | `01:00:5e:00:00:fb` | 加入該群組的網卡 | mDNS、IPTV、影音群播 |
| IPv6 群播 | `33:33:00:00:00:01` | 加入該群組的網卡 | IPv6 鄰居探索（第 5 章） |

MAC 位址有幾個常見的誤解。第一，MAC 位址只在同一段連結層網路內有意義，出了路由器就被換掉，所以網站伺服器看不到使用者的 MAC。第二，MAC 位址可以被軟體改寫，不能當成身分驗證的依據；只靠「MAC 允許清單」保護 Wi-Fi，擋不住會改 MAC 的人。第三，今天的手機與筆電大多預設對不同 Wi-Fi 網路使用隨機的 MAC 位址以保護隱私，所以「用 MAC 辨識同一台裝置」在無線網路上越來越不可靠，DHCP 保留位址或網路存取控制若依賴 MAC，要把這件事列入考慮。

## 4.5 交換器：會自己學習的轉送裝置

有了 frame 和 MAC 位址，接下來的問題是：很多台機器接在一起時，frame 要怎麼送到正確的那一台？

最早的 Ethernet 是一條共用的同軸電纜，後來變成 **hub（集線器）**：hub 把從任何一個埠收到的電訊號原封不動地複製到所有其他埠。每張網卡都收到所有 frame，再自己看目的 MAC 決定要不要。這樣做很簡單，但有兩個大問題：所有人共用同一份頻寬，而且兩台機器同時送就會**碰撞（collision）**，雙方都要退避重送。會互相碰撞的範圍叫**碰撞網域（collision domain）**，接在同一個 hub 上的所有機器都在同一個碰撞網域裡。

**交換器（switch）**解決了這兩個問題。交換器會讀每個 frame 的 MAC 位址，只把 frame 送到需要的埠；每個埠和接在上面的機器之間是一條獨立的全雙工線路，可以同時收與送，碰撞從此消失。交換器靠一張 **MAC 位址表**（也叫 CAM table 或 FDB，forwarding database）做決定，表裡記錄「哪個 MAC 位址在哪個埠」。神奇的是，這張表不需要人設定，交換器會自己學。

```text
              frame 從 port P 進來（來源 S、目的 D）
                              │
                              ▼
            ┌────────────────────────────────────┐
            │ 學習：MAC 表記下「S 在 port P」，     │
            │       並更新最後看到的時間            │
            └────────────────────────────────────┘
                              │
                              ▼
                  D 是廣播或群播位址嗎？ ──是──► flood：送到 P 以外的所有埠
                              │否
                              ▼
                  D 在 MAC 表裡嗎？ ──否──► flood（未知單播）：送到 P 以外的所有埠
                              │是
                              ▼
                  D 所在的埠就是 P 嗎？ ──是──► filter：丟棄（對方本來就收得到）
                              │否
                              ▼
                     forward：只送到 D 所在的那一個埠
```

這張流程圖就是交換器的全部邏輯，可以分成四個動作。**學習（learning）**：每個進來的 frame，交換器都看它的來源 MAC，記下「這個位址在這個埠」；這是被動的，只要機器送過任何東西，交換器就知道它在哪。**轉送（forwarding）**：目的 MAC 已經在表裡，就只送到那個埠。**flood**：目的是廣播，或目的 MAC 還沒學到（叫**未知單播 unknown unicast**），交換器不知道要送去哪，就送到除了來源以外的每一個埠，讓正確的那台自己收下。**過濾（filtering）**：目的就在來源同一個埠（例如那個埠後面又接了一台小交換器），就不必送了。

MAC 表的每一筆都有壽命，叫 **aging time**，常見的預設是 300 秒：超過這段時間沒再看到某個來源 MAC，交換器就把它刪掉。這是為了處理機器搬家或關機，否則表會一直指向錯的埠。機器還在、只是安靜了五分鐘，下一個送給它的 frame 會被 flood 一次，等它回話就又學回來了。另外，埠的連結中斷（拔線、對端關機）時，交換器通常會立即清掉那個埠學到的位址。

| 動作 | 觸發條件 | 交換器做什麼 | 對網路的影響 |
|---|---|---|---|
| 學習 | 任何 frame 進來 | 記下來源 MAC → 進入埠 | 無額外流量 |
| 轉送 | 目的 MAC 已知，在別的埠 | 只送一個埠 | 最理想，頻寬不浪費 |
| flood | 廣播、群播或未知單播 | 送到所有其他埠 | 每台機器都要處理 |
| 過濾 | 目的 MAC 就在進入埠 | 丟棄 | 避免重複 |
| aging | 超過 aging time 沒看到 | 刪除表項 | 下次會再 flood 一次 |

真實系統裡還有幾件事值得知道。交換器轉送的方式有 **store-and-forward**（整個 frame 收完、驗過 FCS 才送出，壞 frame 不會擴散）與 **cut-through**（讀到目的 MAC 就開始送，延遲更低，但壞 frame 也會送出去）。MAC 表容量有限，塞滿之後新的位址學不進去，只好 flood，所以交換器常提供 **port security**，限制每個埠能學幾個 MAC。

最危險的是**迴圈（loop）**。如果兩台交換器之間接了兩條線，一個廣播 frame 會在兩條線之間無限繞圈，而且每經過一台交換器就被複製一次；Ethernet frame 沒有像 IP 那樣的 TTL 欄位，不會自己消失。幾秒鐘內整個網路就被**廣播風暴（broadcast storm）**塞滿，MAC 表也因為同一個來源 MAC 一下出現在這個埠、一下出現在那個埠而不停跳動（MAC flapping）。**STP（Spanning Tree Protocol，生成樹協定）**與它的快速版 RSTP 就是為了解決這件事：交換器之間互相交換訊息，選出一棵沒有迴圈的樹，把多餘的線路暫時封鎖，主線斷掉時再打開備援線。辦公室裡「有人把一條線的兩頭都插進同一台交換器，整層樓斷網」的故事，就是 STP 沒開或被關掉的結果。

## 4.6 廣播網域：一個廣播會傳多遠

交換器會把廣播 flood 到所有埠；如果它上面還接著別的交換器，那台也會繼續 flood。一個廣播 frame 能到達的所有機器，合起來叫做**廣播網域（broadcast domain）**。交換器不會擋廣播，路由器會：路由器處理的是 IP 封包，不會把連結層的廣播轉送到另一個介面。

```text
                     廣播網域 A（10.30.0.0/24）                │   廣播網域 B（10.40.0.0/24）
                                                              │
  encoder ─┐                                                  │                ┌─ 辦公室 PC
  nas ─────┼── 交換器 1 ───── 交換器 2 ─┬─ 監看電腦             │  交換器 3 ─────┼─ 印表機
  NAS 2 ───┘                          └─ 路由器 eth0 ═════════╪═ 路由器 eth1    └─ 會議室螢幕
                                       （廣播到此為止）         │
  一個 ARP 廣播：交換器 1、交換器 2 都會 flood，所有左側機器都收到；路由器不轉送到右側
```

左邊兩台交換器串在一起，仍然是同一個廣播網域：encoder 送出的 ARP 廣播，交換器 1 會送給 nas、NAS 2 和交換器 2，交換器 2 再送給監看電腦和路由器。路由器的 eth0 收到後，只有在問的是自己的 IP 時才回應，絕不會把這個廣播再送到 eth1。所以一個廣播網域通常對應一個 IP 子網：同一個子網裡的機器靠 ARP 直接找到彼此，要到另一個子網就得經過路由器，這就是 4.8 節的主題。

廣播網域不能太大。每個廣播 frame 都會讓網域內的每台機器中斷一下 CPU 去處理；網域裡有幾千台機器時，光是 ARP、DHCP 與各種服務探索的廣播就會造成可觀的負擔，而一台故障的網卡狂送廣播，整個網域都會受害。這也是為什麼企業網路會把不同部門、不同用途切成不同子網，並用 VLAN（4.9 節）在同一批交換器上隔出多個廣播網域。

## 4.7 ARP：用 IP 問出 MAC

現在回到 NAS 的問題。NAS 要送封包給 10.30.0.21，它知道目的 IP，但組 Ethernet frame 需要目的 MAC。這中間的翻譯工作由 **ARP（Address Resolution Protocol，位址解析協定）**負責，規格是 RFC 826。ARP 的想法很直接：在廣播網域裡大聲問「誰是 10.30.0.21？請告訴 10.30.0.31」，擁有這個 IP 的機器回答「10.30.0.21 是我，我的 MAC 是 …」。

ARP 訊息直接放在 Ethernet frame 裡（EtherType 0x0806），不經過 IP。它的格式設計成可以用在不同的連結層與網路層，所以前面有描述位址長度的欄位：

```text
  byte 偏移
  0      ┌───────────────────────────────┬───────────────────────────────┐
         │ Hardware Type = 1（Ethernet）  │ Protocol Type = 0x0800（IPv4） │
  4      ├───────────────┬───────────────┼───────────────────────────────┤
         │ HLEN = 6      │ PLEN = 4      │ Operation：1=request，2=reply  │
  8      ├───────────────┴───────────────┴───────────────────────────────┤
         │ Sender Hardware Address（SHA）6 bytes：送出者的 MAC             │
  14     ├───────────────────────────────────────────────────────────────┤
         │ Sender Protocol Address（SPA）4 bytes：送出者的 IP              │
  18     ├───────────────────────────────────────────────────────────────┤
         │ Target Hardware Address（THA）6 bytes：目標的 MAC（請求時填 0）  │
  24     ├───────────────────────────────────────────────────────────────┤
         │ Target Protocol Address（TPA）4 bytes：要問的 IP                │
  28     └───────────────────────────────────────────────────────────────┘
  共 8 + 6 + 4 + 6 + 4 = 28 bytes
```

前 8 bytes 是固定的描述：硬體類型 1 代表 Ethernet，協定類型 0x0800 代表要解析的是 IPv4 位址，HLEN 和 PLEN 是兩種位址的長度（6 與 4）。Operation 是 1 表示請求、2 表示回應。後面 20 bytes 是兩組「MAC＋IP」：送出者的（SHA、SPA）與目標的（THA、TPA）。請求時目標 MAC 還不知道，填 0；回應時兩組對調，目標變成原本的提問者。對照 4.3 節程式的 hex 輸出，0x0016 開始的 `02 00 00 00 00 31` 就是 SHA，後面的 `0a 1e 00 1f` 是 SPA。

一次完整的 ARP 交換長這樣：

```text
   nas 10.30.0.31                     交換器                    encoder 10.30.0.21        gw 10.30.0.1
   02:..:31                                                       02:..:21                 02:..:01
     │  ① Ethernet dst=ff:ff:ff:ff:ff:ff                             │                        │
     │     ARP request：who-has 10.30.0.21 tell 10.30.0.31          │                        │
     │──────────────────────────►│（學到 :31 在 port 2，flood）        │                        │
     │                           │─────────────────────────────────►│                        │
     │                           │──────────────────────────────────────────────────────────►│
     │                           │                ② encoder：問的是我；順便記下 10.30.0.31=:31  │
     │                           │                                  │     gw：不是問我，丟棄   │
     │  ③ Ethernet dst=02:..:31（單播）                               │                        │
     │     ARP reply：10.30.0.21 is-at 02:..:21                     │                        │
     │◄──────────────────────────│◄─────────────────────────────────│（學到 :21 在 port 1）    │
     │  ④ nas 的 ARP 快取：10.30.0.21 = 02:..:21                     │                        │
     │  ⑤ 排隊中的 IP 封包送出：dst=02:..:21                           │                        │
     │──────────────────────────►│─────────────────────────────────►│（只送 port 1）           │
```

一步一步看。① NAS 的快取裡沒有 10.30.0.21，於是送出 ARP 請求，Ethernet 目的位址是廣播；原本要送的 IP 封包先放進佇列等待。交換器從這個 frame 學到 NAS 在 port 2，因為是廣播就 flood 給其他所有埠。② 每台機器都收到這個請求，但只有 IP 是 10.30.0.21 的 encoder 回應。encoder 也順手記下 NAS 的 IP 與 MAC，因為 NAS 既然在找自己，接下來多半要通訊，這樣回話時就不必反問。③ ARP 回應是單播，直接送給 NAS 的 MAC；交換器在這一步學到 encoder 在 port 1。④ NAS 把答案存進 **ARP 快取**。⑤ 佇列裡的 IP 封包終於可以組成 frame 送出，而且這次交換器已經知道 encoder 在哪，只送 port 1。

**ARP 快取（ARP cache，Linux 稱為 neighbor table）**讓同一個 IP 不必每次都問。快取有壽命，原因和交換器的 aging 一樣：機器可能換了網卡、換了 IP，舊答案會過期。具體壽命依作業系統而定，各家差異很大，從幾十秒到幾十分鐘都有。Linux 的實作不是單純的倒數計時，而是一個狀態機：

| Linux 狀態 | 意義 | 接下來會怎樣 |
|---|---|---|
| INCOMPLETE | 已送出 ARP 請求，還沒收到回應 | 收到回應變 REACHABLE；重試數次失敗變 FAILED |
| REACHABLE | 最近確認過對方可達 | 一段時間（預設約 30 秒上下隨機）後變 STALE |
| STALE | 還有記錄，但不確定是否仍正確 | 仍可使用；一旦有流量要送，變 DELAY |
| DELAY | 用舊記錄送出了封包，等上層（如 TCP ACK）證明對方還在 | 幾秒內有證明就回 REACHABLE，否則變 PROBE |
| PROBE | 主動送單播 ARP 確認 | 有回應回 REACHABLE，沒有變 FAILED |
| FAILED | 問不到 | 送往該 IP 的封包被丟棄，應用程式看到 host unreachable |

這張表解釋了 NAS 那一兩分鐘的空白：舊編碼器的 MAC 在 NAS 的快取裡，NAS 繼續用它送封包，交換器也乖乖把 frame 送到舊編碼器的埠，但那台機器已經不會回應。要等快取走完 STALE、DELAY、PROBE，確認舊位址失效後重新廣播請求，才會問到備用機的新 MAC。在 Linux 上可以用 `ip neigh` 看這張表：

```bash
ip neigh show dev eth0
```

```text
（示意輸出）
10.30.0.1 lladdr 02:00:00:00:00:01 REACHABLE
10.30.0.21 lladdr 02:00:00:00:00:21 STALE
10.30.0.99  FAILED
```

第一行是 gateway，剛確認過。第二行是編碼器，記錄還在但已經是 STALE，下次送封包時才會驗證。第三行 FAILED 表示問過但沒有人回答：這台機器不存在、沒開機，或不在這個廣播網域。macOS 與 Windows 用 `arp -a` 看類似的資訊。

要讓別人立刻更新，可以用 **gratuitous ARP**：一台機器主動廣播一個關於自己的 ARP，例如「10.30.0.21 is-at 02:00:00:00:00:22」，沒有人問也照樣送。它有兩個用途。第一是**宣告**：新上線或換了網卡的機器告訴大家新的對應關係，收到的機器若快取裡已有這個 IP，就會更新（Linux 預設只更新已存在的記錄，不會因此新增）。第二是**衝突偵測**：開機設定 IP 前，先送一個詢問自己 IP 的 ARP probe，如果有人回答，就代表 IP 已被占用，作業系統會跳出「IP 位址衝突」的警告。這些行為在 RFC 5227〈IPv4 Address Conflict Detection〉裡有詳細定義。高可用架構的 **VIP（virtual IP）**切換也靠這招：主機故障時，備援機接手同一個 IP，立刻送出 gratuitous ARP，讓 gateway 與其他機器在一兩秒內改送給自己。

ARP 也有安全上的弱點：協定本身完全沒有驗證，任何機器都可以宣稱自己擁有某個 IP，這叫 **ARP spoofing**，常被用來在區域網路內攔截流量。防禦方式包括在交換器上啟用 **DHCP snooping** 與 **Dynamic ARP Inspection**（交換器記下 DHCP 實際配發的 IP 與 MAC 對應，丟棄不符的 ARP）、對重要設備設定靜態 ARP 記錄，以及最根本的一點：在應用層一律加密與驗證身分（TLS，第 18 章），就算流量被導走，攻擊者也讀不到、改不了內容。IPv6 不用 ARP，改用 ICMPv6 的鄰居探索（Neighbor Discovery），概念相同，第 5 章會介紹。

## 4.8 同網段與跨網段：下一跳交給誰

現在可以回答小晴那台監看電腦的問題了。主機每送一個 IP 封包，都要先做一個判斷：目的 IP 跟我在同一個網段嗎？判斷依據是自己的 IP 位址與**子網遮罩（subnet mask）**，例如 10.30.0.21/24 表示前 24 bits 是網路部分，所以 10.30.0.0 到 10.30.0.255 都是「同網段」。子網的計算方法是第 5 章的主題，這裡只需要知道結果。

```text
                     要送 IP 封包給 D
                            │
                            ▼
              D 與自己同網段？（D AND mask == 自己 AND mask）
                 │是                         │否
                 ▼                           ▼
           下一跳 = D 本身               下一跳 = default gateway
                 │                           │（真實系統是查路由表，第 6 章）
                 └─────────────┬─────────────┘
                               ▼
                 ARP 快取裡有「下一跳的 MAC」嗎？
                    │有                    │沒有
                    ▼                      ▼
             組 frame：               廣播 ARP 問下一跳的 MAC
             dst MAC = 下一跳         （封包先排隊；問不到就丟棄，
             dst IP  = D（不變）        回報 host unreachable）
```

這張圖的關鍵在第二格：**ARP 問的永遠是下一跳的 IP，不是最終目的地的 IP。**送往同網段的 NAS 時，ARP 問的是 NAS；送往 203.0.113.25 時，主機根本不會為 203.0.113.25 送 ARP（它不在這個廣播網域，問了也沒人答），而是問 gateway 10.30.0.1 的 MAC，然後把目的 MAC 設成 gateway、目的 IP 保持 203.0.113.25。gateway 收到後，看到目的 IP 不是自己，就查路由表往下一跳送，重複同樣的過程。

小晴的監看電腦設定的 gateway 是 10.30.0.254，這個 IP 沒有任何機器使用。電腦每次要上網，都廣播「who-has 10.30.0.254」，永遠沒有回應，ARP 記錄停在 INCOMPLETE 再變 FAILED，封包在離開網卡之前就被丟掉了。這種問題在 IP 層的工具看起來很奇怪：ping 同網段一切正常，ping 外部位址卻顯示「Destination Host Unreachable」，而且回報這個錯誤的是自己的 IP（因為是本機發現下一跳不可達）。用 `ip neigh` 看到 gateway 是 FAILED，就能一眼確認。

| 情境 | 判斷結果 | ARP 問誰 | frame 的目的 MAC | IP header 的目的 |
|---|---|---|---|---|
| NAS → encoder（10.30.0.21） | 同網段 | 10.30.0.21 | encoder | 10.30.0.21 |
| encoder → ingest（203.0.113.25） | 跨網段 | 10.30.0.1 | 路由器 | 203.0.113.25 |
| 監看電腦 → 外部網站（gateway 填錯） | 跨網段 | 10.30.0.254 | 問不到，frame 送不出 | — |
| 遮罩誤設為 /16 的機器 → 10.30.5.8 | 誤判為同網段 | 10.30.5.8 | 問不到（對方不在這個廣播網域） | — |
| 遮罩誤設為 /27 的 NAS（10.30.0.31）→ 10.30.0.50 | 誤判為跨網段 | 10.30.0.1 | 路由器（多繞一圈，或被擋） | 10.30.0.50 |

表的後兩列是子網遮罩設錯的兩種方向。遮罩太大（/16），機器會把其實在別的網段的位址當成鄰居，直接 ARP，永遠問不到。遮罩太小（NAS 設成 /27，只涵蓋 10.30.0.0 到 10.30.0.31），機器會把真正的鄰居（例如小晴那台 10.30.0.50 的監看電腦）當成外人交給路由器；有些路由器會轉回同一個介面並送出 ICMP redirect，通訊勉強能通但路徑怪異，有些則直接丟棄。少數網路設備會開啟 **proxy ARP**，替別的網段的位址代答 ARP，讓設錯遮罩的機器「剛好能通」，這會把設定錯誤藏起來，排查時要記得這個可能。

> [!tip]
> 判斷「同網段還是跨網段」的是**送出端自己的設定**，不是網路拓撲。兩台機器實際插在同一台交換器、同一個廣播網域，只要其中一台的遮罩設錯，它就會用錯的方式送封包。排查連線問題時，先看兩端的 `ip addr` 與 `ip route`，確認雙方對「誰是鄰居」的認知一致。

## 4.9 VLAN：在同一台交換器上切出多個網路

聲聲 Live 的辦公室後來要把攝影棚網路和一般辦公室網路分開：攝影棚的推流流量不該被員工電腦的大檔下載影響，訪客 Wi-Fi 更不該看得到 NAS。最直覺的做法是買兩套交換器、拉兩套線，但這很浪費。**VLAN（Virtual LAN，虛擬區域網路）**讓一台實體交換器在邏輯上分成多台：每個埠被指定屬於某個 VLAN，不同 VLAN 之間的廣播與單播都不會互通，就像接在不同的交換器上。

VLAN 的規格是 IEEE 802.1Q。當 frame 要在兩台交換器之間傳遞、而那條線同時承載多個 VLAN 時，交換器會在 frame 裡插入一個 4 bytes 的 **VLAN tag**，標明這個 frame 屬於哪個 VLAN：

```text
 一般 frame： │ 目的 MAC 6 │ 來源 MAC 6 │ EtherType 2 │ Payload … │ FCS 4 │

 802.1Q frame：│ 目的 MAC 6 │ 來源 MAC 6 │ TPID 0x8100 │  TCI  │ EtherType 2 │ Payload … │ FCS 4 │
                                         └──── 4 bytes 的 VLAN tag ────┘
 TCI（16 bits）：
  15 14 13  12  11                                   0
 ┌─────────┬───┬───────────────────────────────────────┐
 │ PCP (3) │DEI│              VID (12 bits)             │
 └─────────┴───┴───────────────────────────────────────┘
  PCP：優先權 0–7（QoS）   DEI：壅塞時可優先丟棄   VID：VLAN 編號 1–4094（0 與 4095 保留）
```

tag 插在來源 MAC 和原本的 EtherType 之間。前 2 bytes 是 **TPID（Tag Protocol Identifier）**，固定為 0x8100，放在原本 EtherType 的位置；舊設備讀到 0x8100 就知道「這是有 tag 的 frame，真正的 EtherType 在後面 4 bytes」。後 2 bytes 是 **TCI**：3 bits 的 PCP 是優先權，可以讓攝影棚的推流流量在壅塞時優先通過；1 bit 的 DEI 標記可丟棄；12 bits 的 VID 是 VLAN 編號，所以最多 4094 個可用 VLAN。因為多了 4 bytes，帶 tag 的 frame 最大是 1522 bytes。

```python
import struct


def tag(frame, vid, pcp=0):
    # 802.1Q：在來源 MAC 後面插入 4 bytes：TPID 0x8100 + TCI（PCP 3 bits、DEI 1 bit、VID 12 bits）
    tci = (pcp << 13) | (vid & 0x0FFF)
    return frame[:12] + struct.pack("!HH", 0x8100, tci) + frame[12:]


def parse(frame):
    etype = struct.unpack("!H", frame[12:14])[0]
    if etype != 0x8100:
        return None, etype
    tci, inner = struct.unpack("!HH", frame[14:18])
    return {"pcp": tci >> 13, "dei": (tci >> 12) & 1, "vid": tci & 0x0FFF}, inner


untagged = bytes.fromhex("020000000021" "020000000031" "0800") + b"payload"
tagged = tag(untagged, vid=10, pcp=5)   # 攝影棚 VLAN 10，推流給高優先權
print("untagged:", untagged[:14].hex(" "))
print("tagged:  ", tagged[:18].hex(" "))
info, inner = parse(tagged)
print(f"VLAN {info['vid']}、優先權 PCP={info['pcp']}、內層 EtherType 0x{inner:04x}")
assert len(tagged) == len(untagged) + 4 and info["vid"] == 10
assert parse(untagged) == (None, 0x0800)
```

```text
untagged: 02 00 00 00 00 21 02 00 00 00 00 31 08 00
tagged:   02 00 00 00 00 21 02 00 00 00 00 31 81 00 a0 0a 08 00
VLAN 10、優先權 PCP=5、內層 EtherType 0x0800
```

程式在 frame 的第 12 個 byte 之後插入 `81 00 a0 0a`：`81 00` 是 TPID，`a0 0a` 是 TCI，二進位 1010 0000 0000 1010，前 3 bits 是 101（PCP=5），接著 1 bit 的 DEI 是 0，最後 12 bits 是 0x00a（VID=10，也就是攝影棚的 VLAN）。原本的 EtherType `08 00` 被往後推了 4 bytes。

交換器的埠分成兩種角色。**access port** 接一般主機，只屬於一個 VLAN，進出的 frame 都不帶 tag，主機完全不知道 VLAN 的存在。**trunk port** 接另一台交換器、路由器或虛擬化主機，同時承載多個 VLAN，frame 帶著 tag 傳送，到對面再依 tag 分流。trunk 上通常有一個 **native VLAN**，它的 frame 不帶 tag；兩端 native VLAN 設定不一致，是 VLAN 流量「漏」到錯的網路的常見原因。

```python
# 一台交換器切成兩個 VLAN：廣播只在同一個 VLAN 內 flood，MAC 表以 (VLAN, MAC) 為 key
access = {1: 10, 2: 10, 3: 20, 4: 20, 5: 20}   # port → VLAN（access port）
trunk = {24}                                    # trunk port 帶 802.1Q tag，所有 VLAN 都走
table = {}


def receive(in_port, src, dst, vlan=None):
    vlan = access.get(in_port, vlan)              # access port 進來的 frame 由交換器指派 VLAN
    table[(vlan, src)] = in_port
    if dst != "ff:ff:ff:ff:ff:ff" and (vlan, dst) in table:
        out = [table[(vlan, dst)]]
    else:
        out = [p for p, v in access.items() if v == vlan and p != in_port]
        out += [p for p in trunk if p != in_port]
    tagged = [f"{p}(tag {vlan})" if p in trunk else str(p) for p in out]
    print(f"VLAN {vlan}: {src} → {dst} 從 port {in_port} 進，送往 {', '.join(tagged)}")
    return out


a = receive(1, "02:00:00:00:00:21", "ff:ff:ff:ff:ff:ff")      # 攝影棚 VLAN 10 的廣播
b = receive(3, "02:00:00:00:00:51", "ff:ff:ff:ff:ff:ff")      # 辦公室 VLAN 20 的廣播
c = receive(2, "02:00:00:00:00:31", "02:00:00:00:00:21")      # 同 VLAN 已知單播
d = receive(4, "02:00:00:00:00:52", "02:00:00:00:00:21")      # 不同 VLAN：查不到，只在 VLAN 20 flood
assert 3 not in a and 1 not in b and c == [1] and 1 not in d
print("廣播與未知單播都沒有越過 VLAN 邊界")
```

```text
VLAN 10: 02:00:00:00:00:21 → ff:ff:ff:ff:ff:ff 從 port 1 進，送往 2, 24(tag 10)
VLAN 20: 02:00:00:00:00:51 → ff:ff:ff:ff:ff:ff 從 port 3 進，送往 4, 5, 24(tag 20)
VLAN 10: 02:00:00:00:00:31 → 02:00:00:00:00:21 從 port 2 進，送往 1
VLAN 20: 02:00:00:00:00:52 → 02:00:00:00:00:21 從 port 4 進，送往 3, 5, 24(tag 20)
廣播與未知單播都沒有越過 VLAN 邊界
```

這段程式模擬一台切成 VLAN 10（攝影棚，port 1–2）與 VLAN 20（辦公室，port 3–5）的交換器，port 24 是 trunk。關鍵在 MAC 表的 key 是「VLAN＋MAC」：同一個 MAC 在不同 VLAN 被視為不同的表項。第一行攝影棚的廣播只送到 port 2 和 trunk（帶 tag 10）；第二行辦公室的廣播只送到 port 4、5 和 trunk（帶 tag 20）。第四行最有意思：辦公室的機器想直接送給攝影棚 encoder 的 MAC，但在 VLAN 20 的表裡查不到這個位址，只能在 VLAN 20 內 flood，永遠到不了 port 1。

不同 VLAN 就是不同的廣播網域，通常也對應不同的 IP 子網（例如攝影棚 10.30.0.0/24、辦公室 10.40.0.0/24）。它們之間要通訊，必須經過路由器或具備路由功能的 **L3 交換器**，這叫 **inter-VLAN routing**。這正好提供了一個控管點：可以在路由器上設定規則，只允許辦公室電腦連 NAS 的檔案分享埠，其他一律擋掉（防火牆是第 7 章的主題）。

## 4.10 Wi-Fi 與有線 Ethernet 的差異

聲聲 Live 的老師大多在家用 Wi-Fi 上課，所以了解無線網路在連結層的特性很重要。Wi-Fi 的規格是 IEEE 802.11，從 IP 的角度看，它和 Ethernet 一樣提供「把 frame 送到同一網路上另一台機器」的服務，也使用同一套 48 bits 的 MAC 位址，ARP 運作方式也一樣。但在這層抽象底下，兩者的運作方式差很多。

```text
 有線（交換式 Ethernet）                         無線（802.11，一個 AP）

   PC1 ══ 全雙工 ══╗                              PC1 )))
   PC2 ══ 全雙工 ══╬══ 交換器                      PC2 )))      ((( AP ══ 有線 ══ 交換器 ── 路由器
   PC3 ══ 全雙工 ══╝                              手機 )))
                                               所有裝置與 AP 共用同一個頻道：
  每個埠獨立、同時收送、沒有碰撞                   同一時間只有一個人能說話（半雙工），
                                               先聽再說（CSMA/CA），每個單播 frame 都要 ACK
```

最根本的差別是**媒介是共用的**。有線網路每個埠是一條獨立的全雙工線路；Wi-Fi 的所有裝置和 **AP（Access Point，無線基地台）**共用同一個無線頻道，同一時間只能有一方發送。無線裝置無法像早期 Ethernet 那樣「邊送邊偵測碰撞」，所以改用 **CSMA/CA（Carrier Sense Multiple Access with Collision Avoidance）**：送之前先聽頻道是否空閒，再隨機等一小段時間，盡量避免碰撞。

第二個差別是**連結層自己會重傳**。無線電波容易受干擾，所以 802.11 的每個單播 frame 都要求接收方回一個連結層的 ACK，沒收到就重送。這讓上層看到的丟包率降低，代價是延遲變得不穩定：訊號差時同一個 frame 可能重送好幾次，這正是視訊通話中 jitter 的常見來源（第 34、39 章）。廣播與群播 frame 則沒有 ACK，而且常以最低的基本速率送出，會占用不成比例的空中時間，這也是在 Wi-Fi 上大量群播影音效果很差的原因。

第三個差別是 **frame 格式與位址數量**。802.11 的資料 frame 最多有 4 個位址欄位，除了來源與目的，還要記錄經過的 AP（BSSID）。AP 本質上是一座**橋接器**：把無線 frame 轉成 Ethernet frame 送進有線網路，反方向亦然；所以從有線那一側看，手機就像接在 AP 所在交換器埠後面的一台主機，交換器會在那個埠學到很多個 MAC。第四，Wi-Fi 在送資料之前還要先**關聯（association）**與驗證（例如 WPA2／WPA3 的金鑰交換），連結層本身就有加密；有線 Ethernet 預設不加密，需要時另外使用 802.1X 認證或 MACsec 加密。

| 面向 | 有線 Ethernet（交換式） | Wi-Fi（802.11） |
|---|---|---|
| 媒介 | 每埠獨立線路，全雙工 | 共用無線頻道，半雙工 |
| 存取控制 | 無碰撞，不需要 | CSMA/CA，先聽再送、隨機退避 |
| 連結層可靠性 | 錯誤 frame 直接丟棄，不重傳 | 單播 frame 要 ACK，失敗會重傳 |
| 延遲特性 | 穩定、低 | 受訊號、干擾、同頻道裝置數影響，波動大 |
| 位址欄位 | 2 個（來源、目的） | 最多 4 個（含 AP 的 BSSID） |
| 連結層加密 | 預設沒有（可加 MACsec） | WPA2／WPA3 |
| 廣播與群播 | 和單播一樣快 | 無 ACK、常用低速率，成本高 |

這些差異直接影響產品決策。Joe 對講師的建議是：上直播課時盡量用有線網路，因為有線的延遲穩定，SRT 與 WebRTC 的重傳機制不必一直對抗 Wi-Fi 的波動；一定要用 Wi-Fi 時，靠近 AP、選擇較不擁擠的頻段，並避免同一個 AP 上有人在大量下載。而在除錯時要記得：學生回報「網路很慢」，若對方是 Wi-Fi，連結層重傳與空中時間競爭是很可能的原因，這在 IP 層的 ping 只會表現為忽高忽低的 RTT。

## 4.11 雲端裡的連結層：看不見但仍然存在

聲聲 Live 的後端跑在雲端 VPC（10.20.0.0/16）。在雲端虛擬機裡執行 `ip neigh`，一樣看得到 gateway 與其他機器的 MAC，作業系統照樣會送 ARP。但多數公有雲的 VPC 並不是一個真的 Ethernet 廣播網域：虛擬化層會攔下 ARP 請求，直接用它掌握的對應表代答，廣播與群播通常也不支援（具體行為依雲端供應商而定）。

這帶來兩個實務影響。第一，本章介紹的很多 L2 故障，例如 ARP spoofing、廣播風暴，在雲端 VPC 裡基本上不會以同樣的形式出現。第二，依賴 gratuitous ARP 來切換 VIP 的傳統高可用做法，在雲端通常無效，必須改用雲端提供的 API 移動 IP 或改用 load balancer。容器網路則常在一台主機內用 Linux bridge 模擬一台小交換器（`docker0` 就是一例），每個容器透過 veth 介面接上去，那裡的 ARP 與 MAC 學習就和本章完全一樣。這些留到第 44 章詳談。

## 4.12 動手做：模擬一個會學習的交換器與 ARP

現在把本章的所有機制放進一個模擬：攝影棚網路有 encoder（port 1）、nas（port 2）、gw 路由器（port 3），之後再接上備用編碼器 spare（port 4）。程式用模擬時鐘推進時間，ARP 快取壽命設為 60 秒，交換器 aging time 設為 300 秒，然後重演週五晚上的事件：先正常通訊，再送往外部，接著舊編碼器當機、備用機以同 IP 上線，最後讓時間跑過所有逾時。

為了讓輸出好讀，frame 用 dict 表示而不是 bytes（bytes 的格式在 4.3 節已經示範過）。每一行 `[t=…]` 是一個 frame 被送出，縮排的行是交換器或主機對這個 frame 的反應。

```python
import ipaddress

BCAST = "ff:ff:ff:ff:ff:ff"
ZERO = "00:00:00:00:00:00"


class Clock:
    """模擬時鐘：讓「逾時」可以在一瞬間跑完，不必真的等。"""
    now = 0.0


class Switch:
    def __init__(self, aging=300.0):
        self.ports, self.table, self.aging = {}, {}, aging  # table: mac -> (port, last_seen)

    def plug(self, port, nic):
        self.ports[port] = nic
        nic.port = port

    def age_out(self):
        for mac, (port, seen) in list(self.table.items()):
            if Clock.now - seen > self.aging:
                del self.table[mac]
                print(f"    switch: MAC 表項逾時移除 {mac}（port {port}）")

    def receive(self, in_port, frame):
        self.age_out()
        src, dst = frame["src"], frame["dst"]
        old = self.table.get(src)
        self.table[src] = (in_port, Clock.now)          # 學習：來源 MAC 在這個 port
        if old is None or old[0] != in_port:
            print(f"    switch: 學到 {src} 在 port {in_port}" + (f"（原本在 port {old[0]}）" if old else ""))
        if dst != BCAST and dst in self.table:
            out = [self.table[dst][0]]
            note = "已知單播，只送 port"
        else:
            out = [p for p in self.ports if p != in_port]  # 廣播或未知單播：flood
            note = "廣播" if dst == BCAST else "未知單播"
            note += "，flood 到 port"
        out = [p for p in out if p != in_port]             # 永遠不送回來源 port（filter）
        print(f"    switch: {note} {out}")
        for p in out:
            self.ports[p].on_frame(frame)

    def dump(self):
        rows = sorted(self.table.items(), key=lambda kv: kv[1][0])
        print("    MAC 表：" + "；".join(f"{m}→port {p}" for m, (p, _) in rows))


class Host:
    def __init__(self, name, mac, ip, prefix, gateway, switch, arp_timeout=60.0):
        self.name, self.mac, self.switch = name, mac, switch
        self.iface = ipaddress.ip_interface(f"{ip}/{prefix}")
        self.gateway = ipaddress.ip_address(gateway) if gateway else None
        self.arp, self.arp_timeout, self.pending, self.port = {}, arp_timeout, [], None
        self.online = True

    def tx(self, frame):
        p = frame["payload"]
        if frame["type"] == "IPv4":
            desc = f"IPv4 {p['src']} → {p['dst']} 「{p['data']}」"
        elif p["op"] == "request":
            desc = f"ARP who-has {p['tpa']} tell {p['spa']}"
        else:
            desc = f"ARP {p['op']} {p['spa']} is-at {p['sha']}"
        print(f"[t={Clock.now:5.0f}] {self.name} 送出 {self.mac} → {frame['dst']}  {desc}")
        self.switch.receive(self.port, frame)

    def lookup(self, ip):
        hit = self.arp.get(ip)
        if hit and Clock.now < hit[1]:
            return hit[0]
        if hit:
            print(f"    {self.name}: ARP 快取 {ip} 已逾時，重新查詢")
            del self.arp[ip]
        return None

    def send_ip(self, dst, data):
        dst = ipaddress.ip_address(dst)
        # 關鍵判斷：目的地在不在自己的網段？在就直接找它，不在就交給 gateway。
        nexthop = dst if dst in self.iface.network else self.gateway
        print(f"  {self.name}: {dst} " + ("同網段，直接送" if nexthop == dst else f"不同網段，下一跳是 gateway {nexthop}"))
        packet = {"src": str(self.iface.ip), "dst": str(dst), "data": data}
        mac = self.lookup(str(nexthop))
        if mac is None:                       # 快取沒有：先排隊，廣播 ARP 請求
            self.pending.append((str(nexthop), packet))
            self.tx({"dst": BCAST, "src": self.mac, "type": "ARP",
                     "payload": {"op": "request", "spa": str(self.iface.ip), "sha": self.mac,
                                 "tpa": str(nexthop), "tha": ZERO}})
        else:
            self.tx({"dst": mac, "src": self.mac, "type": "IPv4", "payload": packet})

    def learn(self, ip, mac, why):
        old = self.arp.get(ip)
        self.arp[ip] = (mac, Clock.now + self.arp_timeout)
        if old is None or old[0] != mac:
            print(f"    {self.name}: ARP 快取 {ip} = {mac}（{why}）")
        for nh, pkt in [x for x in self.pending if x[0] == ip]:   # 補送排隊中的封包
            self.pending.remove((nh, pkt))
            self.tx({"dst": mac, "src": self.mac, "type": "IPv4", "payload": pkt})

    def gratuitous_arp(self):
        ip = str(self.iface.ip)
        self.tx({"dst": BCAST, "src": self.mac, "type": "ARP",
                 "payload": {"op": "announce", "spa": ip, "sha": self.mac, "tpa": ip, "tha": ZERO}})

    def on_frame(self, f):
        if not self.online:
            print(f"    {self.name}: 已當機，frame 無聲消失")
            return
        if f["dst"] not in (self.mac, BCAST):
            return                                   # 網卡丟掉不是給自己的 frame
        p, me = f["payload"], str(self.iface.ip)
        if f["type"] == "ARP":
            if p["op"] == "announce" and p["spa"] in self.arp:
                self.learn(p["spa"], p["sha"], "收到 gratuitous ARP，更新")
            elif p["op"] == "request" and p["tpa"] == me:
                self.learn(p["spa"], p["sha"], "從請求順便學到對方")
                self.tx({"dst": p["sha"], "src": self.mac, "type": "ARP",
                         "payload": {"op": "reply", "spa": me, "sha": self.mac,
                                     "tpa": p["spa"], "tha": p["sha"]}})
            elif p["op"] == "reply" and p["tpa"] == me:
                self.learn(p["spa"], p["sha"], "收到回應")
        elif p["dst"] == me:
            print(f"    {self.name}: 收到「{p['data']}」，來自 {p['src']}")
        elif self.name == "gw":
            print(f"    gw: 目的 {p['dst']} 不是自己，查路由表轉送到其他網段（第 6 章）")


sw = Switch(aging=300)
enc = Host("encoder", "02:00:00:00:00:21", "10.30.0.21", 24, "10.30.0.1", sw)
nas = Host("nas", "02:00:00:00:00:31", "10.30.0.31", 24, "10.30.0.1", sw)
gw = Host("gw", "02:00:00:00:00:01", "10.30.0.1", 24, None, sw)
for port, h in ((1, enc), (2, nas), (3, gw)):
    sw.plug(port, h)

print("== 1. 同網段第一次通訊：ARP 請求廣播、回應單播 ==")
nas.send_ip("10.30.0.21", "錄影開始")
sw.dump()
print("== 2. 十秒後再送：ARP 快取命中，不再廣播 ==")
Clock.now = 10
nas.send_ip("10.30.0.21", "心跳")
print("== 3. 送往其他網段：IP 目的地不變，MAC 目的地換成 gateway ==")
Clock.now = 20
enc.send_ip("203.0.113.25", "SRT 推流")
sw.dump()
print("== 4. 舊編碼器當機（線還插著），備用機同 IP、新 MAC、接 port 4 ==")
Clock.now = 40
enc.online = False
spare = Host("spare", "02:00:00:00:00:22", "10.30.0.21", 24, "10.30.0.1", sw)
sw.plug(4, spare)
nas.send_ip("10.30.0.21", "還在嗎")
print("== 5. 備用機送出 gratuitous ARP，大家立刻更新 ==")
Clock.now = 45
spare.gratuitous_arp()
nas.send_ip("10.30.0.21", "還在嗎")
sw.dump()
print("== 6. 400 秒後：ARP 快取與 MAC 表都逾時 ==")
Clock.now = 400
nas.send_ip("10.30.0.21", "下一場")
sw.dump()
assert nas.arp["10.30.0.21"][0] == spare.mac
assert sw.table["02:00:00:00:00:22"][0] == 4 and "02:00:00:00:00:21" not in sw.table
print("assert 通過：nas 指向備用機，交換器忘掉舊編碼器")
```

```text
== 1. 同網段第一次通訊：ARP 請求廣播、回應單播 ==
  nas: 10.30.0.21 同網段，直接送
[t=    0] nas 送出 02:00:00:00:00:31 → ff:ff:ff:ff:ff:ff  ARP who-has 10.30.0.21 tell 10.30.0.31
    switch: 學到 02:00:00:00:00:31 在 port 2
    switch: 廣播，flood 到 port [1, 3]
    encoder: ARP 快取 10.30.0.31 = 02:00:00:00:00:31（從請求順便學到對方）
[t=    0] encoder 送出 02:00:00:00:00:21 → 02:00:00:00:00:31  ARP reply 10.30.0.21 is-at 02:00:00:00:00:21
    switch: 學到 02:00:00:00:00:21 在 port 1
    switch: 已知單播，只送 port [2]
    nas: ARP 快取 10.30.0.21 = 02:00:00:00:00:21（收到回應）
[t=    0] nas 送出 02:00:00:00:00:31 → 02:00:00:00:00:21  IPv4 10.30.0.31 → 10.30.0.21 「錄影開始」
    switch: 已知單播，只送 port [1]
    encoder: 收到「錄影開始」，來自 10.30.0.31
    MAC 表：02:00:00:00:00:21→port 1；02:00:00:00:00:31→port 2
== 2. 十秒後再送：ARP 快取命中，不再廣播 ==
  nas: 10.30.0.21 同網段，直接送
[t=   10] nas 送出 02:00:00:00:00:31 → 02:00:00:00:00:21  IPv4 10.30.0.31 → 10.30.0.21 「心跳」
    switch: 已知單播，只送 port [1]
    encoder: 收到「心跳」，來自 10.30.0.31
== 3. 送往其他網段：IP 目的地不變，MAC 目的地換成 gateway ==
  encoder: 203.0.113.25 不同網段，下一跳是 gateway 10.30.0.1
[t=   20] encoder 送出 02:00:00:00:00:21 → ff:ff:ff:ff:ff:ff  ARP who-has 10.30.0.1 tell 10.30.0.21
    switch: 廣播，flood 到 port [2, 3]
    gw: ARP 快取 10.30.0.21 = 02:00:00:00:00:21（從請求順便學到對方）
[t=   20] gw 送出 02:00:00:00:00:01 → 02:00:00:00:00:21  ARP reply 10.30.0.1 is-at 02:00:00:00:00:01
    switch: 學到 02:00:00:00:00:01 在 port 3
    switch: 已知單播，只送 port [1]
    encoder: ARP 快取 10.30.0.1 = 02:00:00:00:00:01（收到回應）
[t=   20] encoder 送出 02:00:00:00:00:21 → 02:00:00:00:00:01  IPv4 10.30.0.21 → 203.0.113.25 「SRT 推流」
    switch: 已知單播，只送 port [3]
    gw: 目的 203.0.113.25 不是自己，查路由表轉送到其他網段（第 6 章）
    MAC 表：02:00:00:00:00:21→port 1；02:00:00:00:00:31→port 2；02:00:00:00:00:01→port 3
== 4. 舊編碼器當機（線還插著），備用機同 IP、新 MAC、接 port 4 ==
  nas: 10.30.0.21 同網段，直接送
[t=   40] nas 送出 02:00:00:00:00:31 → 02:00:00:00:00:21  IPv4 10.30.0.31 → 10.30.0.21 「還在嗎」
    switch: 已知單播，只送 port [1]
    encoder: 已當機，frame 無聲消失
== 5. 備用機送出 gratuitous ARP，大家立刻更新 ==
[t=   45] spare 送出 02:00:00:00:00:22 → ff:ff:ff:ff:ff:ff  ARP announce 10.30.0.21 is-at 02:00:00:00:00:22
    switch: 學到 02:00:00:00:00:22 在 port 4
    switch: 廣播，flood 到 port [1, 2, 3]
    encoder: 已當機，frame 無聲消失
    nas: ARP 快取 10.30.0.21 = 02:00:00:00:00:22（收到 gratuitous ARP，更新）
    gw: ARP 快取 10.30.0.21 = 02:00:00:00:00:22（收到 gratuitous ARP，更新）
  nas: 10.30.0.21 同網段，直接送
[t=   45] nas 送出 02:00:00:00:00:31 → 02:00:00:00:00:22  IPv4 10.30.0.31 → 10.30.0.21 「還在嗎」
    switch: 已知單播，只送 port [4]
    spare: 收到「還在嗎」，來自 10.30.0.31
    MAC 表：02:00:00:00:00:21→port 1；02:00:00:00:00:31→port 2；02:00:00:00:00:01→port 3；02:00:00:00:00:22→port 4
== 6. 400 秒後：ARP 快取與 MAC 表都逾時 ==
  nas: 10.30.0.21 同網段，直接送
    nas: ARP 快取 10.30.0.21 已逾時，重新查詢
[t=  400] nas 送出 02:00:00:00:00:31 → ff:ff:ff:ff:ff:ff  ARP who-has 10.30.0.21 tell 10.30.0.31
    switch: MAC 表項逾時移除 02:00:00:00:00:31（port 2）
    switch: MAC 表項逾時移除 02:00:00:00:00:21（port 1）
    switch: MAC 表項逾時移除 02:00:00:00:00:01（port 3）
    switch: MAC 表項逾時移除 02:00:00:00:00:22（port 4）
    switch: 學到 02:00:00:00:00:31 在 port 2
    switch: 廣播，flood 到 port [1, 3, 4]
    encoder: 已當機，frame 無聲消失
    spare: ARP 快取 10.30.0.31 = 02:00:00:00:00:31（從請求順便學到對方）
[t=  400] spare 送出 02:00:00:00:00:22 → 02:00:00:00:00:31  ARP reply 10.30.0.21 is-at 02:00:00:00:00:22
    switch: 學到 02:00:00:00:00:22 在 port 4
    switch: 已知單播，只送 port [2]
    nas: ARP 快取 10.30.0.21 = 02:00:00:00:00:22（收到回應）
[t=  400] nas 送出 02:00:00:00:00:31 → 02:00:00:00:00:22  IPv4 10.30.0.31 → 10.30.0.21 「下一場」
    switch: 已知單播，只送 port [4]
    spare: 收到「下一場」，來自 10.30.0.31
    MAC 表：02:00:00:00:00:31→port 2；02:00:00:00:00:22→port 4
assert 通過：nas 指向備用機，交換器忘掉舊編碼器
```

**第 1 段**：nas 判斷 10.30.0.21 是同網段，快取沒有記錄，於是送出 ARP 廣播。交換器第一次看到 nas 的 MAC，學到它在 port 2，因為目的是廣播而 flood 到 port 1 與 3。encoder 回應的同時也記下了 nas；gw 不是被問的對象，什麼都沒做。ARP 回應是單播，交換器學到 encoder 在 port 1，而且已經知道 nas 在 port 2，所以只送 port 2。最後排隊中的「錄影開始」送出時，交換器只送 port 1。三個 frame 走完，MAC 表就有兩筆記錄。

**第 2 段**：十秒後再送，nas 的 ARP 快取命中，直接組出單播 frame，不再有任何廣播。這就是快取存在的意義：同一段時間內反覆通訊的兩台機器，只有第一次需要 ARP。

**第 3 段**：encoder 要推流到 203.0.113.25，判斷結果是「不同網段，下一跳是 gateway」。注意 ARP 問的是 10.30.0.1，不是 203.0.113.25。問到 gw 的 MAC 後，送出的 frame 目的 MAC 是 gw（`02:00:00:00:00:01`），IP 目的地仍是 203.0.113.25。gw 收到後發現 IP 不是給自己的，交給路由功能處理。這個段落就是 4.2 節那張「MAC 每跳換、IP 不變」圖的第一跳。另外，交換器在這段才第一次學到 gw 的位置，因為 gw 在此之前從沒送過任何 frame。

**第 4 段**：重現 Joe 遇到的狀況。nas 的快取裡 10.30.0.21 仍指向舊 encoder 的 MAC（還沒過 60 秒），交換器的 MAC 表也還記得舊 MAC 在 port 1，於是 frame 被精準地送到一台已經當機的機器，無聲消失。nas 不會收到任何錯誤訊息，上層只會看到逾時。如果舊機的線被拔掉，交換器會清掉 port 1 的記錄，這個 frame 就變成未知單播被 flood，但備用機的網卡看到目的 MAC 不是自己，一樣會丟掉；結果相同。

**第 5 段**：備用機送出 gratuitous ARP。交換器從這個 frame 學到備用機在 port 4；nas 與 gw 的快取裡原本就有 10.30.0.21，於是立刻更新成新 MAC。接下來 nas 的封包直接送到 port 4。這就是 Joe 下次換機器時應該做的事：很多設備在介面啟用時會自動送 gratuitous ARP，若沒有，可以在備用機上手動觸發（Linux 的 `arping` 工具有對應選項，需要管理員權限），或者乾脆在換機後清掉 NAS 上那一筆 ARP 記錄。注意此時 MAC 表仍保留舊 encoder 在 port 1 的記錄，它要等 aging 才會消失，在這之前不會造成問題，因為已經沒有人送往那個 MAC。

**第 6 段**：時間跳到 400 秒。nas 的 ARP 記錄早已過期，重新查詢；交換器在處理這個 frame 時發現四筆記錄都超過 300 秒沒更新，全部刪除，然後重新學到 nas。這次 ARP 請求 flood 到 port 1、3、4，只有備用機回應。最後兩個 assert 確認 nas 指向備用機、交換器已經忘掉舊 encoder。

這個模擬刻意簡化了幾件事：真實的 ARP 快取有 4.7 節表中的多個狀態，問不到時會重試數次；真實交換器會在連結中斷時清除表項；ARP 請求的佇列也有長度上限，超過就丟棄。但核心邏輯，包括學習來源、依目的轉送或 flood、快取命中與逾時、下一跳的選擇，都和真實系統一致。

## 4.13 在工作上怎麼用

**情境一：新設備「同網段通、出不去」。**這是小晴遇到的典型狀況，照順序檢查四件事。第一，`ip addr`（或 macOS 的 `ifconfig`、Windows 的 `ipconfig`）確認 IP 與遮罩正確。第二，`ip route` 確認 default route 指向正確的 gateway。第三，`ping` gateway 的 IP。第四，`ip neigh` 看 gateway 的 ARP 狀態：REACHABLE 表示 L2 沒問題，問題在更上層（路由、NAT、防火牆、DNS）；FAILED 或 INCOMPLETE 表示連 gateway 的 MAC 都問不到，回頭檢查 gateway 位址、VLAN 與實體連線。

```bash
ip addr show dev eth0
ip route show default
ping -c 3 10.30.0.1
ip neigh show 10.30.0.1
```

**情境二：換了機器或網卡，有些人連得到、有些人連不到。**這幾乎一定是 ARP 快取或交換器 MAC 表的舊記錄。在連不到的機器上用 `ip neigh` 看那個 IP 對應的 MAC，和新機器實際的 MAC（`ip link`）比對。修法是讓新機送出 gratuitous ARP，或在受影響的機器上刪除那筆記錄（Linux 的 `ip neigh flush`、macOS 的 `arp -d`，都需要管理員權限）。規劃備援時，把「換機後送 gratuitous ARP」寫進 SOP。

**情境三：懷疑 IP 衝突。**症狀是連線時好時壞、ARP 表裡同一個 IP 的 MAC 一直在兩個值之間跳，或作業系統跳出衝突警告。用 tcpdump 抓 ARP 就能看清楚是哪兩張網卡在搶：

```bash
sudo tcpdump -n -e -i eth0 arp
```

```text
（示意輸出）
19:42:01.120 02:00:00:00:00:31 > ff:ff:ff:ff:ff:ff, ethertype ARP (0x0806), length 42: Request who-has 10.30.0.21 tell 10.30.0.31, length 28
19:42:01.121 02:00:00:00:00:21 > 02:00:00:00:00:31, ethertype ARP (0x0806), length 42: Reply 10.30.0.21 is-at 02:00:00:00:00:21, length 28
19:42:01.121 02:00:00:00:00:22 > 02:00:00:00:00:31, ethertype ARP (0x0806), length 42: Reply 10.30.0.21 is-at 02:00:00:00:00:22, length 28
```

`-e` 讓 tcpdump 印出 Ethernet header（來源與目的 MAC、EtherType），`-n` 不做名稱反查。前兩行是正常的一問一答，第三行是另一張網卡也回答了同一個 IP：這就是衝突的鐵證。後到的回應通常會覆蓋快取，所以 NAS 會隨機連到其中一台。注意 length 是 42，正是 4.3 節說的「沒有 padding 與 FCS」的大小。

**情境四：查「這台機器到底插在哪個埠」。**在受管理的交換器上，可以查 MAC 表（各廠牌指令不同，常見名稱是 `show mac address-table`）找到某個 MAC 所在的埠；Linux bridge 用 `bridge fdb show`。如果一個埠上學到很多個 MAC，通常代表那裡接了另一台交換器或 AP。設備支援 LLDP 時，也能直接看到對端設備的名稱與埠號。

**情境五：網路突然整片變慢、交換器燈號狂閃。**先懷疑迴圈與廣播風暴：查交換器 log 有沒有 MAC flapping 或 STP 拓撲變化的訊息，看哪個埠的廣播流量異常；最近有沒有人接了新線、加了小交換器。斷開可疑的那條線通常能立刻恢復，之後要確認 STP 在所有交換器上都啟用，並在接一般主機的埠開啟廣播抑制與 BPDU 保護之類的功能。

## 4.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 同網段能 ping，外部全部不通 | gateway 位址填錯或 gateway 不在同一個 VLAN | `ip route` 看 default gateway；`ip neigh` 看該 IP 是否 FAILED | 修正 gateway；確認埠的 VLAN 與 gateway 介面相同 |
| 換機或換網卡後，部分機器數十秒到數分鐘連不到 | 對方的 ARP 快取仍指向舊 MAC | 在連不到的機器上 `ip neigh` 比對 MAC | 新機送 gratuitous ARP；或清除舊 ARP 記錄 |
| 連線時好時壞，ARP 表中 MAC 跳動 | IP 位址衝突（兩台設成同一個靜態 IP，或靜態 IP 落在 DHCP 範圍內） | `tcpdump -e arp` 看同一 IP 有兩個 MAC 回應 | 找出重複設定的設備，改用 DHCP 保留或調整範圍 |
| 某些位址連不到，另一些可以 | 子網遮罩設錯，把鄰居當外人或把外人當鄰居 | 兩端比對 `ip addr` 的 prefix；看是否對遠端位址直接送 ARP | 修正遮罩，讓同一廣播網域的機器設定一致 |
| 整個網路突然極慢、CPU 飆高 | 交換器迴圈造成廣播風暴 | 交換器 log 的 MAC flapping、STP 變化；廣播計數暴增 | 拔掉造成迴圈的線；啟用 STP 與廣播抑制 |
| 埠很慢、TCP 重傳很多但 ping 偶爾正常 | 網路線或接頭不良、速率與雙工協商失敗 | 交換器埠的 CRC error、input error 計數上升 | 換線、換埠，確認兩端都設為自動協商 |
| 大檔傳輸卡住、小請求正常 | 路徑上 jumbo frame 或 MTU 設定不一致 | 用不同大小、禁止分片的 ping 測試（第 8 章） | 整條路徑統一 MTU |
| 跨交換器後某個 VLAN 不通 | trunk 沒有允許該 VLAN，或兩端 native VLAN 不一致 | 查 trunk 允許的 VLAN 清單與 native VLAN 設定 | 在 trunk 兩端加入該 VLAN，統一 native VLAN |

除錯時要記得一個原則：連結層的錯誤幾乎都是**無聲的**。FCS 錯誤的 frame 被丟棄、ARP 問不到的封包被丟棄、送到錯誤 MAC 的 frame 被對方網卡忽略，沒有任何一方會送出錯誤訊息。上層看到的只有逾時與重傳。所以當你在 TCP 或應用層看到「說不出原因的逾時」，又確認過 DNS 與防火牆時，就該往下看 ARP 表、交換器埠的錯誤計數，以及 tcpdump `-e` 輸出裡的 MAC 位址是否符合預期。

## 4.15 動手練習

1. **延伸模擬：加入 IP 衝突。**在 4.12 節的程式最後，讓舊 encoder 重新上線（`enc.online = True`），然後讓 nas 的快取逾時再送一次。觀察兩台機器都回應 ARP 時，nas 的快取最後指向誰。答案要點：兩個回應依序到達，後到的覆蓋先到的；在這個模擬中，flood 的順序決定誰「贏」，真實網路則取決於誰回得快，所以會時好時壞。
2. **延伸模擬：MAC 表容量。**為 `Switch` 加上 `capacity` 參數，表滿時不再學習新位址。接上十台主機，capacity 設為 4，觀察後來的主機的單播 frame 如何變成 flood。驗證方法：計算每台主機收到「不是給自己的 frame」的次數，應該明顯上升。
3. **延伸模擬：ARP 請求重試與 FAILED。**讓 nas 送往一個不存在的 10.30.0.99，加上重試 3 次的邏輯，失敗時清空佇列並印出「host unreachable」。對照 4.7 節的狀態表，說明真實系統中這段等待會讓應用程式在哪一步卡住。
4. **用真實工具觀察 ARP。**在自己的電腦上執行 `arp -a`（macOS／Windows）或 `ip neigh`（Linux），找出 gateway 的 MAC；用 4.4 節的程式判斷它的 I/G 與 U/L bit。接著用 `sudo tcpdump -n -e -i <介面> arp` 抓封包，再從另一個終端機 ping 一個同網段但還沒通訊過的位址，觀察 request 與 reply。驗證方法：request 的目的 MAC 是 `ff:ff:ff:ff:ff:ff`，reply 是單播。
5. **手算 frame。**一個帶 802.1Q tag 的 frame 承載 1500 bytes 的 IP 封包，計算 frame 長度（不含 preamble）；再計算一個 64 bytes 的最小 frame 在 1 Gbps 線路上實際占用多少 bytes 的線路時間（含 preamble、SFD 與 interframe gap）。答案要點：14 + 4 + 1500 + 4 = 1522 bytes；64 + 8 + 12 = 84 bytes。
6. **觀察 Wi-Fi 與有線的差異。**在同一個地點分別用 Wi-Fi 與有線網路對 gateway 執行 `ping -c 50`，比較 RTT 的最小值、平均值與標準差（ping 結尾的 mdev 或 stddev）。答案要點：Wi-Fi 的平均值與波動通常明顯較大，對應 4.10 節的共用媒介與連結層重傳。

## 本章重點整理

- IP 位址決定封包最終要到哪裡，MAC 位址決定這一跳要交給誰；封包每經過一台路由器，Ethernet header 就換一次，IP 目的位址不變。
- Ethernet frame 由目的 MAC、來源 MAC、EtherType、payload 與 FCS 組成，最小 64 bytes、最大 1518 bytes；MTU 1500 指的是 payload 上限。
- FCS 只用來偵測錯誤，壞掉的 frame 會被無聲丟棄，重傳要靠上層協定。
- MAC 位址是 48 bits，第一個 byte 的 I/G bit 區分單播與群組，U/L bit 區分廠商配發與本地管理；MAC 可被改寫，不能當成身分驗證。
- 交換器從每個 frame 的來源 MAC 學習位址所在的埠，依目的 MAC 轉送；目的是廣播或未知單播時 flood，表項超過 aging time 會被刪除。
- Ethernet frame 沒有 TTL，交換器迴圈會造成廣播風暴，STP 透過封鎖多餘線路避免迴圈。
- 一個廣播能到達的範圍是廣播網域；交換器會擴大廣播網域，路由器會切開它，一個廣播網域通常對應一個 IP 子網。
- ARP 用廣播請求、單播回應，把下一跳的 IP 翻譯成 MAC，結果存在有壽命的 ARP 快取中；Linux 用 REACHABLE、STALE、DELAY、PROBE 等狀態管理快取。
- gratuitous ARP 讓機器主動宣告自己的 IP 與 MAC，用於換機後立即更新他人快取、VIP 切換與 IP 衝突偵測。
- 主機依自己的 IP 與遮罩判斷目的地是否同網段：同網段就 ARP 目的主機，跨網段就 ARP gateway，ARP 永遠問的是下一跳。
- 子網遮罩或 gateway 設錯時，問題出在連結層的下一跳選擇，症狀常是「同網段通、外部不通」或「部分位址不通」。
- VLAN 用 802.1Q 的 4 bytes tag 在同一批交換器上切出多個廣播網域；access port 不帶 tag，trunk port 帶 tag，VLAN 之間要靠路由器互通。
- Wi-Fi 共用無線媒介、半雙工、使用 CSMA/CA，並在連結層重傳單播 frame，所以延遲波動比有線大；廣播與群播在 Wi-Fi 上特別昂貴。
- 連結層錯誤幾乎都不會產生錯誤訊息；上層看到原因不明的逾時，要往下檢查 ARP 表、MAC 位址與交換器埠的錯誤計數。

## 延伸問答

> [!question]- Q1. 既然每台機器都有 IP，為什麼不直接用 IP 在區域網路內送資料，還要多一層 MAC？
> 因為網卡與交換器工作在 IP 下面一層，它們只處理 frame，判斷「要不要收、要往哪個埠送」只能看連結層位址。IP 是可以重新設定、可以跨越各種實體網路的邏輯位址；而 Ethernet、Wi-Fi 各有自己的 frame 格式與位址，IP 需要一個與實體網路無關的抽象，才能在 Ethernet、Wi-Fi、行動網路之間一路轉送。
>
> 分層的好處是各自獨立演進：Ethernet 從 10 Mbps 走到 400 Gbps，IP 完全不用改；IPv6 取代 IPv4 時，Ethernet 也只是多了一個 EtherType。代價就是兩層之間需要一個翻譯機制，也就是 ARP（IPv6 是鄰居探索）。

> [!question]- Q2. 面試題：從 10.30.0.21 ping 203.0.113.25，在 10.30.0.0/24 這段網路上抓到的 ICMP 封包，Ethernet 與 IP 的來源、目的各是什麼？
> IP header 的來源是 10.30.0.21、目的是 203.0.113.25，因為 IP 位址代表端到端的兩端。Ethernet header 的來源是 encoder 自己的 MAC，目的卻是 gateway 10.30.0.1 的 MAC，因為 203.0.113.25 不在同網段，這一跳要交給 gateway。
>
> 在這之前，如果 encoder 的快取裡沒有 gateway 的記錄，還會先抓到一組 ARP：請求問的是 10.30.0.1，不是 203.0.113.25。回程的 ICMP echo reply 則是來源 MAC 為 gateway、目的 MAC 為 encoder，IP 來源 203.0.113.25、目的 10.30.0.21。若中途經過 NAT，在外側抓到的來源 IP 會不同，這是第 7 章的內容。

> [!question]- Q3. 交換器收到一個目的 MAC 不在表裡的單播 frame，為什麼選擇 flood，而不是丟掉或回報錯誤？
> 交換器的設計目標是「接上就能用、不需要設定」。目的 MAC 不在表裡，只代表這台機器最近沒送過 frame，不代表它不存在；剛開機、安靜超過 aging time 或剛搬埠的機器都會這樣。如果丟掉，這些機器就永遠收不到第一個 frame，也就永遠不會回話讓交換器學習。
>
> flood 讓正確的機器一定收得到，其他機器的網卡看到目的 MAC 不是自己就丟掉，代價只是一點頻寬。等目的機器回應，交換器從回應的來源 MAC 學到位置，後續就變成精準轉送。Ethernet 本來就沒有回報錯誤的機制，錯誤處理一律交給上層。

> [!question]- Q4. 你在 production 看到：VIP 從主機切到備援機後，同網段的應用伺服器有大約一分鐘連不上 VIP，但其他網段的使用者幾乎立刻恢復。原因可能是什麼？
> 其他網段的使用者是經過 gateway 進來的，真正需要更新 ARP 的只有 gateway 一台，它很可能收到了 gratuitous ARP 或很快重新查詢。同網段的應用伺服器則是直接 ARP VIP 的，它們的快取裡 VIP 仍指向舊主機的 MAC，在快取走完 STALE、PROBE 並確認失效之前，封包都送往舊主機。
>
> 要確認，可以在應用伺服器上切換後立刻看 `ip neigh` 中 VIP 對應的 MAC，同時用 tcpdump 檢查切換時是否真的有 gratuitous ARP 送出。修法是確認 HA 軟體在接手時送出 gratuitous ARP，並注意若某些機器的快取裡原本沒有 VIP 記錄，Linux 預設不會因為 gratuitous ARP 新增記錄，這通常無害；若送出了卻沒被接受，要檢查網路設備是否有過濾 gratuitous ARP 的安全設定。

> [!question]- Q5. 手算：一台 48 埠交換器，aging time 300 秒。某台印表機每 10 分鐘才送一次狀態封包，但大家隨時可能送列印工作給它。這會造成什麼現象？
> 印表機每 600 秒才送一次 frame，而 MAC 表項 300 秒沒更新就會被刪除，所以每個週期大約有一半時間，交換器的表裡沒有印表機的記錄。這段期間送給印表機的第一個 frame 會變成未知單播被 flood 到 47 個埠，直到印表機回應才重新學到。
>
> 這通常不會讓列印失敗，只是多了一些 flood 流量；但送出端的 ARP 快取也可能同時過期，那就會再多一次 ARP 廣播。若在大型網路上很多安靜的設備都這樣，未知單播 flood 會累積成可觀的背景流量，此時可以考慮調整 aging time 或為這類設備設定靜態 MAC 表項。

> [!question]- Q6. 為什麼 ARP 的目標設備在回應請求時，要順便記下請求者的 IP 與 MAC？這樣做有什麼風險？
> 因為有人來問「誰是我」，代表對方接下來很可能要和我通訊，而我回應之後通常也要回傳資料給對方。既然請求裡已經帶著對方的 IP 與 MAC，直接記下來就能省掉一次反方向的 ARP 廣播，減少延遲與網路負擔。
>
> 風險在於 ARP 完全沒有驗證，任何人都可以在請求或回應中填入假的對應關係，讓收到的機器把流量送錯地方，這就是 ARP spoofing 的基礎。作業系統因此對「主動接受未請求資訊」比較保守，例如 Linux 預設不因 gratuitous ARP 新增記錄。網路端的防禦是 DHCP snooping 與 Dynamic ARP Inspection，應用端的防禦則是全面使用 TLS，讓流量即使被導走也無法被讀取或竄改。

> [!question]- Q7. 看 log 找原因：小晴的機器 ping 10.30.5.8 時顯示「From 10.30.0.50 icmp_seq=1 Destination Host Unreachable」，而 10.30.0.50 是小晴自己的 IP。這代表什麼？
> 回報錯誤的是自己的 IP，代表封包根本沒有離開這台機器，是本機的網路堆疊發現「下一跳的 MAC 問不到」。若錯誤來自路由器，ICMP 的來源會是路由器的 IP。所以問題在本機與第一跳之間。
>
> 接下來看是哪一種下一跳。若小晴的遮罩是 /16，10.30.5.8 會被判斷為同網段，機器直接 ARP 10.30.5.8，但對方其實在另一個廣播網域，永遠沒有回應；這時 `ip neigh` 會看到 10.30.5.8 是 FAILED，修法是把遮罩改回 /24。若遮罩正確，則下一跳是 gateway，`ip neigh` 會看到 gateway FAILED，要檢查 gateway 位址、VLAN 與實體連線。

> [!question]- Q8. 設計取捨：攝影棚、辦公室、訪客 Wi-Fi 要不要放在同一個大網段（例如一個 /16），讓設定比較簡單？
> 放在同一個廣播網域確實簡單：不需要路由器之間的規則，所有設備都能直接互通。但代價很明顯。廣播網域越大，ARP、DHCP 與各種探索廣播越多，每台機器都要處理；一台故障網卡或一個迴圈就會影響所有人；訪客的設備可以直接 ARP 到 NAS 與編碼器，ARP spoofing 也能波及攝影棚的推流。
>
> 比較好的做法是依用途切成多個 VLAN 與子網，例如攝影棚、辦公室、訪客各一個，由路由器或 L3 交換器做 inter-VLAN routing，並在那裡設定只允許必要的流量（訪客只能出網際網路，辦公室只能存取 NAS 的特定服務）。攝影棚 VLAN 的流量還可以設定較高的 PCP 優先權。多出來的管理成本，換到的是故障隔離、安全邊界與效能的可預期性。

## 延伸閱讀

- IEEE 802.3〈Ethernet〉
- IEEE 802.1Q〈Bridges and Bridged Networks〉（VLAN 與交換器的學習、轉送、生成樹）
- RFC 826〈An Ethernet Address Resolution Protocol〉
- RFC 5227〈IPv4 Address Conflict Detection〉
- RFC 1112〈Host Extensions for IP Multicasting〉（IPv4 群播與 MAC 位址的對應）
- Linux man page ip-neighbour(8) 與核心文件中 neighbour 子系統與 arp 相關的 sysctl 說明
- Charles M. Kozierok《The TCP/IP Guide》連結層與 ARP 相關章節
