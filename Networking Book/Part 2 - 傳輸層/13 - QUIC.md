---
chapter: 13
title: QUIC：建在 UDP 上的新傳輸層
part: 2
---

# 第 13 章　QUIC：建在 UDP 上的新傳輸層

> [!abstract] 本章地圖
> **核心問題**：TCP 用了四十多年、很難再改，QUIC 怎麼在 UDP 上重做一層傳輸，解決 head-of-line blocking、交握太慢與換網路就斷線的問題？
>
> **你會學到**：
> - 說清楚 TCP 為什麼難以演進（ossification），以及 QUIC 為什麼選擇 UDP、選擇在 user space 實作
> - 讀懂 QUIC 的 variable-length integer、long header 與 short header，並用 Python 編解碼
> - 畫出 QUIC 與 TLS 1.3 整合後的 1-RTT 交握與 0-RTT 流程，知道 0-RTT 的重放風險與位址驗證
> - 解釋 stream 如何消除 TCP 層的 head-of-line blocking，以及 stream 內仍然保序
> - 理解 packet number、ACK range、PTO 等 loss recovery 機制，和 TCP 的差異
> - 用 connection ID 解釋 connection migration、NAT rebinding 與路徑驗證，並排查「UDP 被擋」時的 fallback
>
> **前置知識**：第 9 章（UDP 與 socket）、第 10–12 章（TCP 連線、可靠傳輸、擁塞控制與 HOL blocking）。第 18 章會再深入 TLS 1.3，第 22 章會講建在 QUIC 上的 HTTP/3。

## 13.1 故事：捷運上卡住的投影片

週四晚上八點是聲聲 Live 的尖峰時段。客服轉來一串抱怨：學生在捷運上用手機上課，列車一進站，教室頁面的投影片就停住、聊天訊息要好幾秒才出現，有時乾脆整頁轉圈圈重新載入。監控圖上，每到下班時段，`api.shengsheng.example` 的「連線中斷後重新建立」次數就明顯上升。

小晴先看了 nginx 的 access log，請求本身都很快，大多數不到 50 ms 就回完。慢的是「請求送到之前」。阿德把一位學生的手機抓包結果投影出來：這位學生邊出門邊上課，手機離開家裡的 Wi-Fi、切到 4G 的那一刻，來源 IP 從 `198.51.100.23`（家用路由器的對外位址）變成 `198.51.100.140`；捷運進出站時手機在 Wi-Fi 與 4G 之間切換，也是同一回事。對 server 來說，這是一個完全陌生的四元組，舊連線上的封包再也送不到手機，新位址送來的封包又不屬於任何連線，只能回 RST。手機端得重新做 DNS、TCP 三向交握、TLS 交握，才能把剛才沒載完的投影片再要一次。

另一張圖更讓小晴困惑。在訊號很差的隧道裡，手機沒有換網路，但教室頁面同時載入的投影片、聊天記錄和白板快照，會「一起」停住。Joe 指著抓包說：「一個封包掉了，後面十幾個封包明明都到了，卻全部卡在 kernel 裡等它重傳。」這就是第 12 章講過的 TCP 層 head-of-line blocking：HTTP/2 把多個請求多工在同一條 TCP 連線上，TCP 只認得一條 byte stream，不知道裡面其實是三份互不相干的資料。

阿德的建議是：在 CDN 與 load balancer 上啟用 HTTP/3，讓支援的瀏覽器改走 **QUIC**。QUIC 是一個建在 UDP 上的傳輸協定，可以把它想成「把 TCP 的可靠傳輸、擁塞控制，加上 TLS 1.3 的加密，重新設計成一層」。小晴的第一個反應是：「UDP 不是不可靠嗎？為什麼要拿不可靠的東西來做可靠傳輸？」Rita 則補了一個現實問題：「我們有幾個企業客戶的公司網路會擋 UDP，開了 HTTP/3 會不會讓他們連不上？」

這一章就跟著小晴回答這三個問題：為什麼不直接改 TCP、QUIC 怎麼在 UDP 上做出可靠且加密的連線、換網路與丟包時 QUIC 到底改善了什麼，以及 UDP 被擋時會發生什麼事。最後一節的工作清單，就是小晴替聲聲 Live 啟用 HTTP/3 時實際用到的檢查步驟。

## 13.2 為什麼不直接改 TCP：協定僵化

要回答「為什麼不改 TCP」，得先看 TCP 封包在網際網路上會經過哪些東西。理論上，路由器只看 IP header，TCP header 只有兩端在看。實際上，路上有大量 **middlebox**（中間設備）：NAT、stateful 防火牆、負載平衡器、企業的流量檢查設備、電信業者的效能加速器。它們為了做事，會讀、甚至改寫 TCP header。

```text
 手機 ── Wi-Fi AP ── 家用 NAT ── ISP 的 CGNAT ── 企業防火牆 ── LB ── server
           │            │             │              │          │
           └─ 各自看得懂「它們出廠時的 TCP」：認得的 option 才放行，
              不認得的 flag 可能被清掉，seq 可能被改寫，異常封包可能被丟棄

 新功能要能用，必須「整條路徑上每一台」都不搗亂
 → 兩端升級了，中間某一台舊設備不認得 → 新功能失效，甚至連線失敗
```

這張圖說明了問題的核心。第一，middlebox 的數量龐大而且分散在不同的組織手上，沒有人能統一升級。第二，middlebox 往往只認得「出廠時常見的 TCP 長相」：看到不認得的 TCP option，有的設備會刪掉 option，有的會直接丟掉整個封包。第三，兩端無法事先知道路上有哪些設備，只能送出去碰運氣。這種「協定因為被太多實作依賴某種長相，而變得無法再改」的現象叫 **協定僵化（ossification）**，像骨頭鈣化一樣定型了。

真實的例子很多。**TCP Fast Open** 讓 client 在 SYN 裡就帶資料，省掉一個 RTT，但它需要一個新的 TCP option，部署時發現部分網路會丟掉帶這個 option 的 SYN，瀏覽器只好退回或乾脆不啟用。**Multipath TCP** 為了讓一條連線同時用 Wi-Fi 與行動網路，也得設計成「option 被刪掉就自動退回一般 TCP」。ECN（Explicit Congestion Notification，擁塞時由路由器在 IP header 上做記號）也曾因為部分設備處理錯誤，花了很多年才敢預設開啟。

第二個難處在作業系統。TCP 實作在 kernel 裡，應用程式想要新的擁塞控制或新的重傳策略，得等使用者的作業系統更新。伺服器端還好，自己能升級 kernel；但手機、筆電、企業電腦的作業系統更新週期以年計，新功能從標準化到普及要非常久。

第三個難處是「明文」。TCP header 沒有加密，middlebox 才能讀、才能依賴它。只要 header 是明文，就一定有人會依賴它的某個欄位，日後就不能再改這個欄位。

QUIC 的設計者對這三點的回答分別是：

| TCP 的問題 | QUIC 的做法 | 代價 |
|---|---|---|
| middlebox 依賴 TCP header 的長相 | 外層用 UDP，middlebox 只看得到 UDP header；傳輸層資訊幾乎全部加密 | 有些網路會擋或限速 UDP；營運者看不到傳輸層細節 |
| kernel 實作，升級慢 | 在 user space 實作，跟著瀏覽器、app、server 程式一起更新 | 每個應用程式各自帶一套實作，CPU 成本通常比 kernel TCP 高 |
| TLS 疊在 TCP 上，交握要分兩段 | TLS 1.3 的交握直接內建在 QUIC 交握裡 | 不能只用「傳輸層」而不加密，QUIC 一定加密 |
| 一條連線就是一條 byte stream | 一條連線裡有多個獨立 stream | 實作複雜度高很多 |
| 連線用四元組識別 | 連線用 connection ID 識別 | load balancer 要懂 connection ID 才能正確轉送 |

表格裡最關鍵的取捨是「加密幾乎所有東西」。QUIC 不只加密 payload，連 packet number 都用 **header protection** 遮起來，ACK 資訊、stream 編號、流量控制視窗全部在加密的 payload 裡。路上的設備只能看到 UDP 的 port、QUIC 少數幾個不加密的欄位（版本、connection ID、第一個 byte 的少數位元）。看不到，就無從依賴；無從依賴，日後就能改。這是用加密來對抗僵化的設計。

> [!warning] 常見誤解
> 「QUIC 建在 UDP 上，所以 QUIC 不可靠。」UDP 只是 QUIC 的「信封」：它提供 port 與 checksum，讓封包能穿過現有網路。可靠傳輸、順序、流量控制、擁塞控制都由 QUIC 自己實作，可靠程度和 TCP 同一個等級。第 9 章說「UDP 不可靠」，指的是 UDP 這一層不做這些事，上層可以自己做。

為什麼不乾脆在 IP 上定義一個新的傳輸協定（新的 IP protocol number）？因為 NAT 與防火牆只認得 TCP 與 UDP，看到陌生的 protocol number 多半直接丟掉。UDP 是唯一一個「幾乎到處都放行、又幾乎不帶語意」的選擇。

## 13.3 QUIC 的全貌：在 UDP 上重做傳輸層

先把 QUIC 放回分層圖裡，和 HTTP/2 的堆疊對照：

```text
   HTTP/2 的堆疊                     HTTP/3 的堆疊
 ┌─────────────────┐            ┌─────────────────┐
 │ HTTP/2          │            │ HTTP/3          │  ← 第 22 章
 │ （frame、stream）│            ├─────────────────┤
 ├─────────────────┤            │ QUIC            │  ← 本章
 │ TLS 1.2 / 1.3   │            │ ・stream、流量控制│
 ├─────────────────┤            │ ・可靠傳輸、擁塞控制│
 │ TCP             │            │ ・TLS 1.3 交握與加密│
 │ （kernel 實作）  │            │ （user space 實作）│
 ├─────────────────┤            ├─────────────────┤
 │ IP              │            │ UDP             │
 └─────────────────┘            ├─────────────────┤
                                │ IP              │
                                └─────────────────┘
```

左邊是三層各自獨立的設計：TCP 負責可靠的 byte stream，TLS 在上面加密，HTTP/2 再在加密的 byte stream 上自己切 frame、做多工。右邊把「可靠傳輸、加密、多工」合併成 QUIC 一層：QUIC 自己就有 stream，HTTP/3 只要把每個請求放進一條 stream。這樣合併的好處是各個機制可以互相配合，例如交握與加密一起完成、遺失只影響單一 stream；壞處是 QUIC 成了一個很大、很複雜的協定。

QUIC 的核心規格在 2021 年由 IETF 發布為一組 RFC：RFC 9000 是傳輸協定本身，RFC 9001 講 QUIC 怎麼使用 TLS，RFC 9002 講遺失偵測與擁塞控制，RFC 8999 定義「不論哪個版本的 QUIC 都不會變」的少數特性。HTTP/3 是 RFC 9114。早年 Google 有一個自家版本，常被稱為 gQUIC，IETF 標準化的 QUIC 和它已經不相容；本書說的 QUIC 一律指 IETF 的版本。

接下來會反覆出現四個名詞，先把它們的包含關係講清楚：

```text
 UDP datagram（一次 sendto 送出去的東西，≤ 路徑 MTU）
 ┌──────────────────────────────────────────────────────────┐
 │ UDP header 8 bytes                                        │
 │ ┌──────────────────────────┐ ┌──────────────────────────┐ │
 │ │ QUIC packet #1（Initial） │ │ QUIC packet #2（Handshake）│ │ ← 交握時可以把幾個
 │ │ header │ 加密的 payload   │ │ header │ 加密的 payload   │ │   packet 串在一個
 │ │        │ ┌─────┐┌───────┐│ │        │ ┌──────┐┌─────┐  │ │   datagram 裡
 │ │        │ │ ACK ││CRYPTO ││ │        │ │CRYPTO││ PAD │  │ │
 │ │        │ └─────┘└───────┘│ │        │ └──────┘└─────┘  │ │
 │ └──────────────────────────┘ └──────────────────────────┘ │
 └──────────────────────────────────────────────────────────┘
   frame 是最小的語意單位；STREAM frame 裡帶著某條 stream 的一段資料
```

由外往內讀：最外層是 **UDP datagram**，也就是一次 `sendto` 送出、網路上看到的一個 UDP 封包。一個 datagram 裡可以有一個或多個 **QUIC packet**（交握期間常把不同加密層級的 packet 串在一起，叫 coalescing）。每個 QUIC packet 有自己的 header 與加密 payload，payload 解密後是一串 **frame**：ACK frame 回報收到了什麼，CRYPTO frame 帶 TLS 交握訊息，STREAM frame 帶應用程式資料，PADDING frame 把封包撐大。**stream** 則不是封包裡的東西，而是一條邏輯上的有序資料流，它的資料被切成很多段，分散在很多個 STREAM frame 裡送。

這個分層讓 QUIC 和 TCP 有一個根本差異：TCP 的序號編的是「資料的 byte」，重傳時送的是同一段序號；QUIC 的 packet number 編的是「封包」，每個封包號碼只用一次，遺失的資料會被放進一個新號碼的封包重送。13.8 節會看到這個設計怎麼讓 RTT 量測與遺失判斷變簡單。

## 13.4 QUIC 封包的長相：varint、long header 與 short header

### Variable-length integer：QUIC 的整數編碼

QUIC 裡幾乎每個長度、offset、stream ID、frame type 都用同一種整數編碼：**variable-length integer**（變長整數，常簡稱 varint）。它的想法是「小數字用少 byte，大數字用多 byte」，而長度寫在第一個 byte 的最高兩個 bit：

```text
 第一個 byte
  7 6 5 4 3 2 1 0
 ┌───┬───────────┐
 │ L │  值的最高位 │   L = 00 → 共 1 byte，值有 6 bit
 └───┴───────────┘   L = 01 → 共 2 bytes，值有 14 bit
                     L = 10 → 共 4 bytes，值有 30 bit
                     L = 11 → 共 8 bytes，值有 62 bit

 例：0x7bbd = 0111 1011  1011 1101
              └┘ L=01 → 2 bytes
                └─────────────────┘ 剩下 14 bit = 0x3bbd = 15293
```

解碼時先看第一個 byte 的最高兩位決定總長度，把這兩位清掉，剩下的 bit 和後面的 byte 依 network byte order（big-endian，第 2 章）接起來，就是數值。圖下半部的手算例子：`0x7bbd` 的前兩位是 `01`，所以總共 2 bytes；把它們清掉後是 `0x3bbd`，十進位是 15293。編碼時則選「能裝下這個值的最短長度」，不過規格也允許用比較長的編碼，例如 37 可以編成 1 byte 的 `0x25`，也可以編成 2 bytes 的 `0x4025`。

| 前綴 | 總長度 | 有效 bit | 最大值 | 常見用途 |
|---|---|---|---|---|
| `00` | 1 byte | 6 | 63 | frame type、小的 stream ID、短長度 |
| `01` | 2 bytes | 14 | 16,383 | 封包長度（一般 MTU 內都放得下） |
| `10` | 4 bytes | 30 | 1,073,741,823 | 較大的 offset、流量控制上限 |
| `11` | 8 bytes | 62 | 4,611,686,018,427,387,903 | 超大 offset、極大視窗 |

和 TCP 固定 32 bit 的序號相比，varint 的好處是「不會不夠用」：stream offset 最大可到 2^62 − 1，一條連線傳再多資料也不必像 TCP 那樣處理序號繞回。代價是解析時要逐欄位讀、不能用固定 offset 直接取值，這也是 QUIC 解析程式比 TCP 複雜的原因之一。13.12 節會完整實作編碼與解碼。

### Long header：交握期間用的封包

QUIC 有兩種 header。連線建立期間用 **long header**，它帶著版本號與雙方的 connection ID，因為此時雙方還在協商、需要完整資訊。以下是 RFC 9000 定義的 v1 long header 位元布局（以 Initial packet 為例）：

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌─┬─┬───┬───┬───┬───────────────────────────────────────────────┐
 │1│1│T T│R R│P P│               Version (32)                    │
 ├─┴─┴───┴───┴───┼───────────────┬───────────────────────────────┤
 │    ...Version │ DCID Len (8)  │ Destination Connection ID     │
 ├───────────────┴───────────────┘        (0..160 bit)  ...      │
 │ SCID Len (8)  │ Source Connection ID (0..160 bit) ...         │
 ├───────────────┴───────────────────────────────────────────────┤
 │ Token Length (varint) │ Token ...                             │  ← 只有 Initial 有
 ├───────────────────────┴───────────────────────────────────────┤
 │ Length (varint)：packet number + payload 的長度                 │
 ├───────────────────────────────────────────────────────────────┤
 │ Packet Number (8/16/24/32 bit，長度由 PP 決定)                  │
 ├───────────────────────────────────────────────────────────────┤
 │ Payload（加密的 frame）...                                      │
 └───────────────────────────────────────────────────────────────┘
  第 0 bit：Header Form，1 = long header
  第 1 bit：Fixed Bit，v1 固定為 1
  TT：Long Packet Type  00 Initial｜01 0-RTT｜10 Handshake｜11 Retry
  RR：Reserved bits（受 header protection 保護）
  PP：Packet Number Length − 1（受 header protection 保護）
```

逐欄位讀：第一個 byte 最高位是 **Header Form**，1 代表 long header；下一位是 **Fixed Bit**，v1 規定為 1，讓 QUIC 和同一個 port 上其他 UDP 協定比較好區分。接著兩位是封包類型，後四位在 Initial、0-RTT、Handshake 裡是兩個保留位元與 packet number 長度。之後是 32 bit 的 **Version**，v1 是 `0x00000001`。再來是兩組「長度＋connection ID」：**DCID**（Destination Connection ID，收件端用來辨識連線的 ID）與 **SCID**（Source Connection ID，送件端希望對方之後填在 DCID 的 ID），長度最多 20 bytes。Initial 封包還有 token 欄位，用在位址驗證（13.6 節）。**Length** 是一個 varint，說明後面 packet number 加 payload 有多長，所以接收端才能在一個 datagram 裡切出好幾個串在一起的 packet。

| Long packet type | v1 編碼 | 用途 | 加密金鑰 |
|---|---|---|---|
| Initial | `00` | 帶 ClientHello／ServerHello | 從 client 選的 DCID 推導，任何人都算得出來 |
| 0-RTT | `01` | client 在交握完成前先送的應用資料 | 上一次連線留下的 resumption 秘密 |
| Handshake | `10` | 帶 TLS 交握的其餘訊息 | TLS 交握導出的 handshake 金鑰 |
| Retry | `11` | server 要求 client 帶 token 重來 | 不加密，只有完整性標籤 |
| Version Negotiation | Version 欄位為 0 | server 不支援 client 的版本時回覆 | 不加密 |

這張表有一個值得停下來想的地方：Initial packet 的金鑰是「從公開資訊推導」的，路上任何人看到 DCID 都能解開。這看似沒意義，其實它的目的不是保密，而是「防止 middlebox 隨意讀寫與依賴內容」，同時讓偽造的 Initial 必須至少看過 client 的封包才做得出來。真正的保密從 Handshake 金鑰開始。

### Short header：連線建立後用的封包

交握完成後，所有應用資料都用 **short header**（也叫 1-RTT packet）。它省掉了版本與長度欄位，只留下最少的資訊：

```text
  0 1 2 3 4 5 6 7
 ┌─┬─┬─┬───┬─┬───┐
 │0│1│S│R R│K│P P│   ← 第一個 byte
 └─┴─┴─┴───┴─┴───┘
 ┌──────────────────────────────────────────┐
 │ Destination Connection ID（0..160 bit）   │  ← 沒有長度欄位！
 ├──────────────────────────────────────────┤
 │ Packet Number（8/16/24/32 bit）           │
 ├──────────────────────────────────────────┤
 │ Payload（加密的 frame）...                 │
 └──────────────────────────────────────────┘
  0：Header Form = short     1：Fixed Bit
  S：Spin bit（可選，讓路上設備被動量 RTT）
  RR：Reserved     K：Key Phase（金鑰更新時翻轉）     PP：Packet Number Length − 1
```

和 long header 相比，最特別的是 **DCID 沒有長度欄位**。接收端解析時，必須自己知道「我當初發給對方的 connection ID 有多長」。這是刻意的：每個封包省下幾個 byte，而且 server 可以自由決定 connection ID 的長度與內部結構（例如把後端機器編號編進去，13.9 節會用到）。**Spin bit** 是一個可選的位元，client 與 server 讓它每經過一個 RTT 翻轉一次，路上的設備觀察它的翻轉週期就能估計 RTT，這是在「全部加密」之後，特意留給網路營運者的一點可觀測性；實作可以選擇不啟用。**Key Phase** 用在連線中途更換金鑰：TLS 1.3 原本用 KeyUpdate 訊息做這件事，QUIC 改成翻轉這一個位元。

Packet number 只送低位的 1 到 4 bytes，接收端依據「目前收過的最大 packet number」還原完整的 62 bit 數值，就像時鐘只顯示分鐘，你仍知道現在是幾點。真實封包裡，第一個 byte 的低位元與 packet number 都經過 header protection：用一部分加密後的 payload 當取樣，算出一個遮罩與它們 XOR。所以用 Wireshark 看沒有金鑰的 QUIC 封包，packet number 一欄是看不到的。

## 13.5 交握：QUIC 與 TLS 1.3 的整合

TCP 上的 HTTPS 要先做 TCP 三向交握（1 RTT），再做 TLS 1.3 交握（1 RTT），第三個 RTT 才拿得到回應的第一個 byte。QUIC 把兩件事合併：TLS 1.3 的交握訊息直接放在 QUIC 的 CRYPTO frame 裡，傳輸參數的協商也夾帶在 TLS 的擴充欄位裡，一次來回就同時完成「建立連線」與「建立加密」。

```text
 Client                                                    Server
   │ Initial[CRYPTO: ClientHello（含 key_share、ALPN=h3、       │
   │         quic_transport_parameters）, PADDING 到 ≥1200 B]  │
   │─────────────────────────────────────────────────────────►│
   │                                                          │ 算出共享秘密
   │   Initial[ACK, CRYPTO: ServerHello]                      │
   │   Handshake[CRYPTO: EncryptedExtensions, Certificate,     │
   │             CertificateVerify, Finished]                 │
   │   1-RTT[STREAM: 可選的 0.5-RTT 資料]                       │
   │◄─────────────────────────────────────────────────────────│
   │ 驗證憑證與 Finished                                         │
   │ Initial[ACK] Handshake[ACK, CRYPTO: Finished]            │
   │ 1-RTT[STREAM 0: GET /slides/42]          ← 第 1 個 RTT 結束就送出請求
   │─────────────────────────────────────────────────────────►│
   │   1-RTT[HANDSHAKE_DONE, STREAM 0: 200 OK + 投影片資料]      │
   │◄─────────────────────────────────────────────────────────│

 對照 TCP + TLS 1.3：SYN → SYN-ACK → ACK＋ClientHello → ServerHello… → Finished＋請求
                    請求最早在第 2 個 RTT 結束時送出
```

逐步看這張時序圖。第一步，client 送出 Initial packet，裡面的 CRYPTO frame 帶著 TLS 1.3 的 ClientHello：key_share 是 Diffie-Hellman 的公開值（第 17 章），ALPN 宣告要說 `h3`，`quic_transport_parameters` 擴充欄位帶著 QUIC 的初始流量控制上限、idle timeout 等參數。這個 datagram 必須用 PADDING 撐到至少 1200 bytes，理由在 13.6 節。第二步，server 回覆的 datagram 裡串了三個 packet：Initial 帶 ServerHello，Handshake 帶憑證與 Finished，必要時還能用 1-RTT 金鑰先送一點資料（稱為 0.5-RTT）。第三步，client 驗證憑證與 Finished 之後，回 Handshake 層級的 Finished，並且**同一趟**就把 HTTP 請求放在 1-RTT packet 裡送出。最後 server 送 HANDSHAKE_DONE 確認交握完成。

整合之後，QUIC 在 TLS 1.3 之上做了幾個調整，值得記住：

| 項目 | TLS over TCP | QUIC 裡的 TLS 1.3 |
|---|---|---|
| 交握訊息怎麼送 | TLS record 包起來，放在 TCP byte stream | 放在 CRYPTO frame，依加密層級放進不同類型的 packet |
| 資料怎麼加密 | TLS record layer 的 AEAD | QUIC 自己的 packet protection，金鑰由 TLS 導出 |
| 支援的版本 | TLS 1.2、1.3 都可能 | 只能用 TLS 1.3 |
| 中途換金鑰 | KeyUpdate 訊息 | short header 的 Key Phase 位元 |
| ALPN | 可選 | 必須協商（例如 `h3`） |
| 傳輸參數 | 不適用 | 放在 TLS 擴充，受交握完整性保護 |

最後一列特別重要。QUIC 的傳輸參數（例如初始視窗、可開幾條 stream、connection ID 的長度上限）都放在 TLS 擴充裡，會被 TLS 交握的 Finished 驗證。這代表路上的人無法偷改這些參數，不像 TCP 的 window scale option 是明文、可以被 middlebox 改寫。

QUIC 把加密分成幾個**加密層級**（encryption level）：Initial、0-RTT、Handshake、1-RTT。交握過程就是「逐級拿到新金鑰、換到下一級」的過程。和加密層級相對的是 **packet number space**，ACK 與遺失偵測在每個 space 各自進行：

```text
 時間 ─────────────────────────────────────────────────────────►

 Initial space      [pn 0, 1, 2 …]  ClientHello / ServerHello ──┐ 交握完成後丟棄金鑰
 Handshake space          [pn 0, 1 …]  憑證、Finished ──────────┤
 Application space   0-RTT [pn 0…] ─┐                           │
                     1-RTT         [pn …, 持續到連線結束]  ◄─────┘
                     （0-RTT 與 1-RTT 共用同一個 packet number space）
```

每個 space 的 packet number 都從 0 開始。為什麼不全部共用一組號碼？因為不同層級的封包用不同金鑰，對方可能暫時只解得開其中一種；如果混在一起計數，ACK 就會包含對方根本無法處理的號碼，遺失判斷也會被干擾。分開之後，Initial 與 Handshake 的金鑰在交握完成後就可以丟掉，之後只剩 application space。

> [!tip] 最低的 1200 bytes
> QUIC 要求整條路徑至少能送 1200 bytes 的 UDP payload，client 第一個 Initial datagram 也要撐到這個大小。如果某段 VPN 或隧道的 MTU 小到連 1200 都送不過（第 8 章），QUIC 交握就會失敗，瀏覽器會退回 TCP。之後 QUIC 可以用 DPLPMTUD（用自己送的探測封包找出更大的可用大小）往上調。

## 13.6 0-RTT 與位址驗證：快的代價

### 0-RTT：在第一個封包就送請求

如果 client 之前連過同一個 server，TLS 1.3 會留下 **session ticket**（resumption 用的票券）。下次連線時，client 可以用 ticket 導出的金鑰，在第一個 datagram 裡就附上應用資料，這就是 **0-RTT**：

```text
 Client（手上有上次的 ticket）                                Server
   │ Initial[CRYPTO: ClientHello + pre_shared_key + early_data]   │
   │ 0-RTT[STREAM 0: GET /api/schedule]   ← 和 ClientHello 同一趟   │
   │─────────────────────────────────────────────────────────────►│
   │                                       檢查 ticket；決定接受或拒絕 0-RTT
   │   Initial[ServerHello]  Handshake[…, Finished]                │
   │   1-RTT[STREAM 0: 200 OK（課表）]   ← 0 個 RTT 就開始拿到回應     │
   │◄─────────────────────────────────────────────────────────────│
   │ Handshake[Finished] 1-RTT[後續請求] …                          │

 若 server 拒絕 0-RTT：0-RTT 封包被丟棄，client 交握完成後用 1-RTT 重送
```

0-RTT 的好處很直接：對一個 RTT 100 ms 的行動網路使用者，打開聲聲 Live app 時查課表的請求可以早 100 ms 送到。但它有一個無法消除的風險：**重放（replay）**。0-RTT 資料在 server 回覆之前就送出了，server 還沒機會給出「這次連線專屬」的新鮮值，所以路上的攻擊者如果把這個 datagram 錄下來再送一次，server 可能會再處理一次同樣的請求。TLS 層有一些緩解手段（例如 ticket 只能用一次、檢查時間窗），但在多台 server 分散部署時很難做到完全防重放。

所以實務規則是：**0-RTT 只能送 idempotent、沒有副作用的請求**。查課表、拿投影片可以；預約課程、付款、改密碼絕對不行。HTTP 有一個專門的狀態碼 425 Too Early，server 收到「不該在 early data 裡處理」的請求時可以回 425，叫 client 交握完成後再送一次。聲聲 Live 在 CDN 上的設定是：只對 GET 與 HEAD 接受 0-RTT，並且讓後端看得到「這個請求是否來自 early data」的標記，這部分第 18 章會從 TLS 的角度再談一次。

> [!warning] 常見誤解
> 「QUIC 每次連線都是 0-RTT。」第一次連線一定是 1-RTT，只有 resumption 才可能 0-RTT，而且 server 可以拒絕。另外，0-RTT 省掉的是「交握的等待」，不是「資料傳輸的時間」：回應很大的請求，傳輸本身仍受頻寬與擁塞控制限制。

### 位址驗證與防放大

UDP 沒有三向交握，來源 IP 可以偽造。如果 QUIC server 收到一個小小的 Initial 就回一大串憑證，攻擊者就能偽造受害者的 IP 發 Initial，讓 server 把大量資料砸向受害者，這叫**放大攻擊**（amplification attack）。QUIC 的防禦有兩層：

第一層是 **anti-amplification limit**：在確認 client 位址之前，server 送出的 bytes 不能超過從這個位址收到的 3 倍。這就是為什麼 client 的 Initial 要撐到 1200 bytes：server 至少能回 3600 bytes。如果 server 的憑證鏈很長，第一趟裝不下，就得等 client 再送封包（例如 ACK）來增加額度，交握因此多出一個 RTT。這是部署時的實際考量：憑證鏈精簡、使用 ECDSA 憑證（簽章與公鑰比 RSA 小）、啟用憑證壓縮，都能讓 QUIC 交握維持在 1-RTT。

第二層是 **Retry**：server 覺得可疑或負載過高時，可以不建立任何狀態，直接回一個 Retry packet，裡面帶著用 server 自己的秘密簽過的 token。client 必須在新的 Initial 裡帶回 token，證明「我真的收得到送到這個 IP 的封包」。代價是多一個 RTT，所以通常只在受攻擊時啟用。server 也可以在連線中用 NEW_TOKEN frame 先發 token，讓 client 下次連線時直接帶上，跳過驗證的等待。

## 13.7 Stream 與流量控制：把 HOL 拆開

回到故事裡的隧道問題。HTTP/2 在一條 TCP 連線上多工了投影片、聊天記錄和白板快照，但 TCP 只保證「整條 byte stream 依序交付」。第 12 章說過，只要一個 segment 遺失，後面所有已到達的資料都得在 kernel 的接收緩衝區裡等，即使它們屬於完全不同的請求。

QUIC 的 **stream** 是連線內一條獨立、有序的資料流。每條 stream 有自己的 offset 空間，接收端依 offset 重組；某條 stream 的資料遺失，只會讓**那一條** stream 停下來等重傳，其他 stream 已到達的資料可以立刻交給應用程式。

```text
 送出順序（每格一個 packet，每 5 ms 一個）
 pn:      0      1      2      3      4      5      6      7      8
 stream:  chat   board  slide  chat   board  slide  chat   board  slide
 結果:    ✓      ✓      ✗遺失  ✓      ✓      ✓      ✓      ✓      ✓
                          └──── 約 1 個 RTT 後以新 pn 重傳

 TCP（一條 byte stream）:   pn 0,1 交付 │ pn 2 之後全部卡住 ………… │ 重傳到達 → 一次全部交付
 QUIC（各 stream 各自排序）: chat  ──✓──────✓──────✓──  不受影響
                            board ──✓──────✓──────✓──  不受影響
                            slide ──✗ 等重傳 ……………… ✓✓✓ 只有它在等
```

這張圖是 13.12 節模擬程式的縮小版。上半部是送出的封包：三條 stream 輪流送，pn 2 屬於投影片，在路上遺失。下半部比較交付給應用程式的時間：TCP 不知道哪些 byte 屬於哪個請求，只能把 pn 2 之後的所有資料都扣著；QUIC 收到 pn 3（chat）時，看到 chat 這條 stream 沒有缺口，就立刻交付。只有 slide 這條 stream 要等重傳。對聲聲 Live 的教室頁面來說，聊天訊息和白板筆跡不再被一張大圖拖住。

但有兩點要說清楚。第一，**stream 內仍然保序**：投影片自己的資料還是得等缺口補上，QUIC 消除的是「不同 stream 之間」的 HOL，不是 stream 內的。如果應用程式把所有東西都塞在同一條 stream，就等於回到 TCP。第二，HTTP/3 的 header 壓縮（QPACK，第 22 章）為了避免跨 stream 的依賴，特別設計成可以選擇「不參照尚未確認的表格內容」，否則 header 壓縮本身會重新引入 HOL。

### Stream ID 與 STREAM frame

每條 stream 用一個 62 bit 的 **stream ID** 識別，最低兩個 bit 編碼了它的類型：

```python
# Stream ID 的最低兩個 bit 決定「誰開的」與「單向或雙向」
KINDS = {0b00: "client 開、雙向", 0b01: "server 開、雙向",
         0b10: "client 開、單向", 0b11: "server 開、單向"}
for sid in [0, 4, 8, 1, 2, 3, 6, 7]:
    print(f"stream {sid:>2}  bits={sid & 0b11:02b}  {KINDS[sid & 0b11]:<10}  同類第 {sid >> 2} 條")
assert [s for s in range(16) if s & 0b11 == 0][:3] == [0, 4, 8]  # HTTP/3 的請求 stream
```

```text
stream  0  bits=00  client 開、雙向  同類第 0 條
stream  4  bits=00  client 開、雙向  同類第 1 條
stream  8  bits=00  client 開、雙向  同類第 2 條
stream  1  bits=01  server 開、雙向  同類第 0 條
stream  2  bits=10  client 開、單向  同類第 0 條
stream  3  bits=11  server 開、單向  同類第 0 條
stream  6  bits=10  client 開、單向  同類第 1 條
stream  7  bits=11  server 開、單向  同類第 1 條
```

最低位表示誰開的（0 是 client、1 是 server），次低位表示單向或雙向（0 是雙向、1 是單向）。所以 client 開的雙向 stream 是 0、4、8、12……，HTTP/3 的每個請求就各用一條；單向 stream 則用在 HTTP/3 的控制訊息與 QPACK 的表格更新。雙方各自往上編號，不需要協商，也不會撞號。

資料放在 **STREAM frame** 裡，frame type 是 0x08 到 0x0f，低三位是三個旗標：OFF（有沒有 offset 欄位）、LEN（有沒有長度欄位）、FIN（這是不是 stream 的最後一段）。接下來依序是 stream ID、offset、長度與資料，全部是 varint。以下是本章會遇到的主要 frame：

| Frame | type | 作用 |
|---|---|---|
| PADDING | 0x00 | 撐大封包（例如 Initial 撐到 1200 bytes） |
| PING | 0x01 | 要求對方回 ACK，也可當 keepalive |
| ACK | 0x02–0x03 | 回報收到的 packet number 範圍與 ack delay（0x03 多帶 ECN 計數） |
| RESET_STREAM／STOP_SENDING | 0x04／0x05 | 中止單一 stream，不影響其他 stream |
| CRYPTO | 0x06 | 帶 TLS 交握訊息 |
| NEW_TOKEN | 0x07 | 發給 client 下次連線用的位址驗證 token |
| STREAM | 0x08–0x0f | 應用資料 |
| MAX_DATA／MAX_STREAM_DATA／MAX_STREAMS | 0x10／0x11／0x12–0x13 | 流量控制：放寬連線、stream 的上限與可開 stream 數 |
| NEW_CONNECTION_ID／RETIRE_CONNECTION_ID | 0x18／0x19 | 發放與回收 connection ID |
| PATH_CHALLENGE／PATH_RESPONSE | 0x1a／0x1b | 驗證新路徑 |
| CONNECTION_CLOSE | 0x1c–0x1d | 關閉連線（傳輸層錯誤或應用層錯誤） |
| HANDSHAKE_DONE | 0x1e | server 確認交握完成 |

RESET_STREAM 是 HTTP/3 的一個實用能力：學生快速翻頁時，瀏覽器可以取消還沒載完的上一張投影片，只重設那條 stream，連線與其他請求都不受影響。在 HTTP/1.1 上，取消一個傳到一半的回應往往只能關掉整條連線。

### 兩層流量控制

和 TCP 的接收視窗（第 11 章）一樣，QUIC 也要防止送得比對方處理得快。不同的是它有兩層：**stream 層**限制每條 stream 最多能送到哪個 offset（MAX_STREAM_DATA），**連線層**限制所有 stream 合計的總量（MAX_DATA）。另外用 MAX_STREAMS 限制對方能同時開幾條 stream，防止對方開出幾萬條 stream 耗盡記憶體。初始值都放在交握時的傳輸參數裡，之後接收端每消化一部分資料，就送 MAX_* frame 把上限往後推。

為什麼要兩層？如果只有連線層，一條讀得很慢的 stream（例如應用程式暫時沒去讀的大檔案下載）可能吃光整條連線的額度，讓其他 stream 都送不了，等於在流量控制層重新製造 HOL。只有 stream 層又不夠，因為接收端的總記憶體有限。送端被卡住時會送 DATA_BLOCKED 或 STREAM_DATA_BLOCKED 告知對方，這些 frame 在除錯時很有用：在 qlog 裡看到大量 BLOCKED，通常代表接收端的視窗設得太小，而不是網路太慢。

## 13.8 Loss recovery：packet number 永不重用

QUIC 的遺失偵測與擁塞控制在 RFC 9002，整體概念和 TCP 很像（第 11、12 章），但有幾個設計刻意修掉了 TCP 的老問題。

**第一，packet number 嚴格遞增、永不重用。** TCP 重傳時送的是同一段序號，收到 ACK 時無法分辨它是在回應原始封包還是重傳的封包，這叫 retransmission ambiguity，所以 TCP 的 RTT 估計得排除重傳過的樣本（Karn 演算法）。QUIC 的重傳是把遺失的 **frame** 放進一個新號碼的 packet，每個 ACK 都明確對應一個送出時間，每次都能拿到乾淨的 RTT 樣本。

```text
 TCP：                                      QUIC：
  seq 1000 送出 ──✗                          pn 7  [STREAM 8 off=2400] ──✗
  seq 1000 重傳 ────►                         pn 12 [STREAM 8 off=2400] ────►   ← 同樣的資料、新的號碼
  ◄── ACK 1460                              ◄── ACK 12
  這個 ACK 回應的是第一次還是第二次？無法分辨     確定是 pn 12，RTT = now − send_time(12)
```

左邊的 TCP 收到 ACK 時，不知道該拿哪一次送出的時間來算 RTT。右邊的 QUIC，遺失的是 pn 7，裡面的 STREAM frame（stream 8、offset 2400 的那段投影片資料）被放進 pn 12 重送，ACK 12 只可能對應那一次送出。13.12 節的 HOL 模擬裡，被遺失的 pn 2 也是以 pn 12 重傳。也因為 ACK 的對象是封包而不是資料，ACK frame 本身不會被重傳；需要重送的只有「真正需要可靠送達」的 frame，例如 STREAM、CRYPTO、MAX_DATA。

**第二，ACK frame 比 TCP 的 SACK 更完整。** ACK frame 可以列出很多段收到的範圍（ACK range），不像 TCP 的 SACK option 受限於 40 bytes 的 option 空間只能放幾段。它還帶 **ack delay**：接收端從收到封包到送出 ACK 之間刻意延遲了多久，送端可以把這段時間從 RTT 樣本扣掉。QUIC 的 ACK 也不能「反悔」：TCP 允許接收端在 SACK 之後丟掉已回報的資料（reneging），QUIC 一旦 ACK 就代表確實收下。

**第三，遺失判斷有兩個門檻。** 某個 packet 被判定遺失，條件是「比它晚送的 packet 已經被 ACK」，再加上下列其中一項：比它晚至少 3 個號碼的 packet 已被確認（packet threshold，類似 TCP 的三個重複 ACK），或它送出後已經超過 9/8 倍 RTT（time threshold）。

**第四，用 PTO 取代 RTO。** 如果遲遲收不到任何 ACK（例如連最後幾個封包都遺失了，沒有「比它晚」的封包可以觸發判斷），送端在 **PTO**（probe timeout）到期時送一兩個探測封包，逼對方回 ACK，而不是像 TCP 的 RTO 那樣直接把 cwnd 砍到最小。PTO 的計算方式如下：

```python
# RFC 9002 的 RTT 估計與 PTO（probe timeout）計算，單位 ms
GRANULARITY, MAX_ACK_DELAY = 1, 25
samples = [(120, 0), (100, 10), (300, 5), (110, 20)]  # (量到的 RTT, 對方回報的 ack delay)
smoothed = rttvar = min_rtt = None
for latest, ack_delay in samples:
    if smoothed is None:  # 第一個樣本直接當基準
        smoothed, rttvar, min_rtt = latest, latest / 2, latest
    else:
        min_rtt = min(min_rtt, latest)
        # 扣掉對方刻意延遲回 ACK 的時間，但不能扣到比 min_rtt 還小
        adjusted = latest - ack_delay if latest - ack_delay >= min_rtt else latest
        rttvar = 0.75 * rttvar + 0.25 * abs(smoothed - adjusted)
        smoothed = 0.875 * smoothed + 0.125 * adjusted
    pto = smoothed + max(4 * rttvar, GRANULARITY) + MAX_ACK_DELAY
    loss_delay = 9 / 8 * max(smoothed, latest)  # time threshold
    print(f"sample={latest:>3}  srtt={smoothed:6.1f}  rttvar={rttvar:5.1f}  PTO={pto:6.1f}  loss_delay={loss_delay:6.1f}")
assert 100 < smoothed < 200
```

```text
sample=120  srtt= 120.0  rttvar= 60.0  PTO= 385.0  loss_delay= 135.0
sample=100  srtt= 117.5  rttvar= 50.0  PTO= 342.5  loss_delay= 132.2
sample=300  srtt= 139.7  rttvar= 81.9  PTO= 492.2  loss_delay= 337.5
sample=110  srtt= 136.0  rttvar= 68.8  PTO= 436.3  loss_delay= 153.0
```

這段程式模擬四個 RTT 樣本。第一個樣本直接當成平滑 RTT（srtt），變異量（rttvar）取它的一半。第二個樣本 100 ms、對方回報 ack delay 10 ms，但扣掉之後的 90 ms 會小於目前看過的最小 RTT，所以不扣，避免把 RTT 估得比實際還小。第三個樣本突然跳到 300 ms，srtt 只溫和地上升到 139.7，rttvar 則明顯變大，PTO 跟著拉長到約 492 ms，這是為了在網路抖動時不要太早誤判。`loss_delay` 是 time threshold，9/8 倍的 max(srtt, 最新 RTT)。PTO 公式是 srtt + max(4 × rttvar, 1 ms) + max_ack_delay；Initial 與 Handshake 層級不加 max_ack_delay，因為對方在交握期間應該立刻回 ACK。PTO 連續觸發時每次加倍，和 TCP 的 RTO 退避一樣。

**擁塞控制**方面，RFC 9002 描述的預設演算法類似 NewReno（slow start、congestion avoidance、遺失時減半），但規格明確允許實作改用 CUBIC 或 BBR（第 12 章）。因為 QUIC 在 user space，換演算法只要更新程式，不必等 kernel，這正是當初設計的目的之一。QUIC 也定義了 **persistent congestion**：一段時間內連續遺失的封包跨越夠長的時間，就把 cwnd 降到最小，相當於 TCP 的 RTO 處理。

## 13.9 Connection ID 與 connection migration

### 為什麼 TCP 換網路就斷

TCP 用四元組（來源 IP、來源 port、目的 IP、目的 port）識別連線。這在第 9 章看起來理所當然，但對手機來說是個大問題：從 Wi-Fi 換到 4G，來源 IP 變了；甚至在同一個 Wi-Fi 下，NAT 對應表逾時重建，對外的來源 port 也可能改變（**NAT rebinding**，第 7 章）。四元組一變，server 的 kernel 查不到這條連線，只能回 RST。故事裡捷運上的斷線，就是這個原因。

### Connection ID：連線的名字

QUIC 不用四元組，而是用 **connection ID** 識別連線：每個 packet 的 DCID 欄位就是「收件端替這條連線取的名字」。雙方各自選自己的 connection ID，交給對方使用：client 在 Initial 的 SCID 裡告訴 server「之後寄給我時填這個」，server 在回覆的 SCID 裡也一樣。交握之後，server 還會用 NEW_CONNECTION_ID frame 多發幾個備用的 ID 給 client，每個都附上一組 **stateless reset token**：server 遺失連線狀態（例如重啟）時，可以送一個結尾帶這個 token 的封包，讓 client 立刻知道連線已經不存在，13.14 節的除錯表會遇到它。

這樣一來，server 收到 short header 封包時，先依 DCID 找連線，再用連線金鑰解密；來源位址只是「目前的回信地址」，不是連線的身分。

```text
 Client（手機）                                       Server（203.0.113.80:443）
  家中 Wi-Fi 198.51.100.23:50000
   │── 1-RTT [DCID=f067…] STREAM 8: 投影片請求 ────────────────►│ 依 DCID 找到連線 A
   │◄─────────────────────────────── 1-RTT [資料] ──────────────│
   │
   ▼ 走出家門，換到 4G：來源變成 198.51.100.140:41234
   │── 1-RTT [DCID=5b1e…（新的 ID）] STREAM 8 … ───────────────►│ 新位址，但 DCID 屬於連線 A
   │                                                            │ 資料照收；限制送量 ≤ 3 倍
   │◄──────────── 1-RTT [PATH_CHALLENGE data=8 bytes 亂數] ─────│
   │── 1-RTT [PATH_RESPONSE 同一組 8 bytes] ───────────────────►│ 驗證通過 → 改用新路徑
   │◄────────────── 1-RTT [投影片剩下的資料] ────────────────────│ 擁塞控制狀態重新估計

 TCP 的同一情境：新四元組查不到連線 → RST → 重新 DNS、TCP、TLS 交握、重送請求
```

逐步解說這個遷移流程。第一段，手機在 Wi-Fi 上用 DCID `f067…` 送封包，server 依 DCID 找到連線 A。第二段，手機換到 4G，主動選用一個 server 之前發的**新** connection ID `5b1e…` 送下一個封包。server 查表發現它也屬於連線 A，就照常解密、收下資料，但由於這個新位址還沒被驗證，回送的量受 3 倍的防放大限制。第三段，server 送出 **PATH_CHALLENGE**，帶 8 bytes 亂數；只有真的能在新位址收到封包的一方，才能用 **PATH_RESPONSE** 原樣回傳。驗證通過後，server 改用新路徑，並且把擁塞控制與 RTT 估計重設，因為 4G 和 Wi-Fi 的頻寬與延遲完全不同，沿用舊的 cwnd 可能一下子塞爆新路徑。

### 為什麼要換新的 connection ID

如果手機換網路後還用同一個 connection ID，路上的觀察者就能把「Wi-Fi 上的這個人」和「4G 上的那個人」串起來，知道是同一個使用者。所以規格要求：client 主動從新的本地位址送封包時，要換用新的 connection ID；server 發的多個 ID 之間也不能看出關聯。NAT rebinding 則是例外：client 根本不知道自己的對外位址變了，自然沿用同一個 ID，這種情況 server 一樣靠 DCID 找到連線，再做路徑驗證。13.12 節的程式兩種情況都會示範。

QUIC v1 只允許 client 主動遷移；server 不能任意換位址，只能在交握時透過 `preferred_address` 傳輸參數建議 client 改連另一個位址。server 也可以用 `disable_active_migration` 參數告訴 client「不要主動遷移」，例如 server 前面的負載平衡器還不支援依 connection ID 轉送時。另外，交握完成之前不能遷移。

### Connection ID 與負載平衡

遷移帶來一個營運問題：聲聲 Live 的 L4 load balancer 原本用四元組雜湊決定把封包送到哪一台後端。手機換網路後四元組改變，雜湊結果也變了，封包被送到另一台沒有這條連線狀態的機器，遷移就失敗了。解法是讓 load balancer 看 DCID：server 產生 connection ID 時，把「後端編號」用只有 load balancer 解得開的方式編進 ID 裡，load balancer 讀 DCID 就知道該送去哪台。這也是 short header 不帶 DCID 長度、讓 server 自訂 ID 結構的原因之一。

> [!note] 遷移的邊界
> Connection migration 只能讓「同一條 QUIC 連線」繼續活下去。聲聲 Live 教室裡的 WebSocket 目前多半仍走 TCP（第 32 章），換網路時照樣會斷；即時服務的重連、補發與去重仍然要自己設計（第 33 章）。WebRTC 的媒體走的是 UDP 上的 SRTP，不是 QUIC，它有自己的 ICE restart 機制（第 36 章）。

## 13.10 UDP 被擋怎麼辦：發現、競速與 fallback

Rita 擔心的企業客戶問題，答案是：**瀏覽器會自動退回 TCP**，前提是 server 端同時保留 HTTP/2 或 HTTP/1.1。理解這個流程，要先知道瀏覽器怎麼「發現」一個網站支援 HTTP/3。

```text
 瀏覽器要連 https://www.shengsheng.example
        │
        ├─ DNS 查詢：A／AAAA，以及 HTTPS record（alpn="h3,h2"）？
        │        └─ 有 h3 → 可以第一次就試 QUIC
        │
        ├─ 沒有 HTTPS record → 先用 TCP + TLS（HTTP/2）連線
        │        └─ 回應 header：Alt-Svc: h3=":443"; ma=86400
        │                 └─ 記住「這個來源在 443 有 h3，24 小時有效」
        │
        ├─ 之後的連線：嘗試 QUIC（UDP 443）
        │        ├─ 交握成功 → 用 HTTP/3
        │        └─ 逾時／被擋 → 改用 TCP（通常會同時或稍後發起 TCP 當備援）
        │                 └─ 記住「QUIC 對這個來源暫時不通」，一段時間內不再試
        ▼
     使用者只感覺到「沒有比較快」，而不是「連不上」
```

這張流程圖有三個關鍵。第一，**發現**：瀏覽器第一次造訪通常不知道網站支援 HTTP/3，只能先走 TCP；回應裡的 **Alt-Svc** header 告訴瀏覽器「同一個服務也可以在 UDP 443 用 h3 連」，`ma` 是這個資訊的有效秒數。DNS 的 **HTTPS record**（第 14 章）可以讓瀏覽器在第一次連線前就知道，省掉這一輪 TCP。第二，**競速**：瀏覽器嘗試 QUIC 時，通常會在短時間內也發起 TCP 連線，哪個先成功用哪個，避免 UDP 被擋時白等一個逾時；具體策略依瀏覽器實作而定。第三，**記憶**：QUIC 失敗後，瀏覽器會在一段時間內直接走 TCP，不會每次都重試。

所以「UDP 被擋」通常不會讓網站壞掉，真正麻煩的是**半通**的情況：

- 防火牆放行 UDP 443 的前幾個封包，卻在一段時間後丟棄（例如 UDP 對應表逾時太短），QUIC 連線建好後突然沒有回應，瀏覽器要等 idle timeout 或 PTO 才發現。
- 路徑 MTU 小於 1200 bytes 的 VPN，交握封包永遠送不過去。
- 某些網路會對 UDP 限速，QUIC 能連上但比 TCP 慢。
- 不是瀏覽器的 client（自己寫的 app、SDK、server 對 server 的呼叫）不一定有自動 fallback，要看使用的函式庫。

NAT 對 UDP 的對應表逾時通常比 TCP 短很多（第 7 章），所以 QUIC 連線在閒置時，實作會定期送 PING frame 保持 NAT 對應不被清掉。QUIC 本身也有 **idle timeout**（交握時協商 `max_idle_timeout`），超過時間沒有任何封包就安靜地關閉連線，不送任何東西。

| 比較項目 | TCP + TLS 1.3（HTTP/2） | QUIC（HTTP/3） |
|---|---|---|
| 新連線到送出請求 | 2 RTT | 1 RTT |
| resumption | 1 RTT（TCP 交握仍要等）＋可選 TLS early data | 可 0-RTT |
| 單一封包遺失 | 整條連線所有 stream 等待 | 只有所屬 stream 等待 |
| 換 IP／port | 連線中斷 | 透過 connection ID 遷移 |
| header 可見性 | TCP header 明文 | 幾乎全部加密 |
| 實作位置 | kernel | user space（隨應用程式更新） |
| CPU 成本 | 低，有成熟的硬體 offload | 通常較高，依賴 UDP GSO／GRO 等最佳化 |
| 網路相容性 | 幾乎到處可用 | UDP 可能被擋、限速，需要 fallback |

最後兩列是 QUIC 的實際代價。kernel 的 TCP 有數十年的最佳化與網卡 offload（例如讓網卡幫忙切 segment），QUIC 每個封包都要在 user space 加解密、經過系統呼叫，同樣的流量通常吃更多 CPU。Linux 的 UDP GSO（一次系統呼叫送出多個 datagram）與 GRO（接收時合併）大幅縮小了差距，但大流量的伺服器仍要把 CPU 成本算進容量規劃。

## 13.11 2026 現況：部署與正在發展的標準

> [!note] 2026 現況
> 以下截至 2026 年 10 月，依 `tools/.network_survey.md` 的整理；標示「依知識」的項目未經本次網路查證。
>
> - **核心規格穩定**：RFC 8999、9000、9001、9002 自 2021 年發布後是 QUIC v1 的基礎；HTTP/3 是 RFC 9114、QPACK 是 RFC 9204（依知識）。
> - **後續擴充**（依知識）：QUIC v2 是 RFC 9369，和 v1 功能相同，但換了版本號（`0x6b3343cf`）、Initial 的 salt 與 long header 的類型編碼，目的是防止 middlebox 把 v1 的長相當成唯一正確的 QUIC；Compatible Version Negotiation 是 RFC 9368；不可靠的 DATAGRAM 擴充是 RFC 9221。
> - **TLS**：依 2026 年 10 月查證，TLS 1.3 有新版 RFC 9846（2026-07，obsoletes RFC 8446，版本號仍是 1.3），QUIC 使用 TLS 1.3 的方式不受影響。
> - **部署**（依知識）：Chrome、Edge、Firefox、Safari 都支援 HTTP/3；Cloudflare、Google、Meta、Akamai、Fastly 等大型 CDN 已廣泛部署。client 主要靠 Alt-Svc 或 DNS HTTPS record 發現 h3。HTTP/3 在 CDN 流量中的占比本書不提供數字，請以 Cloudflare Radar 或 HTTP Archive Web Almanac 的最新資料為準。
> - **Media over QUIC（MoQ）**：依 2026 年 10 月查證，`draft-ietf-moq-transport` 仍是 IETF WG draft（最新為 -22），尚未成為標準，第 38 章會在直播的脈絡下簡短介紹。
> - **WebTransport over HTTP/3**：依 2026 年 10 月查證，仍在 IETF 最後審查階段，尚未成為 RFC。
> - 依 connection ID 做負載平衡的通用編碼方式，IETF 有一份 QUIC-LB 草案在處理，標準化狀態本次未查證。

常見的 QUIC 實作，在讀 log 或選型時會遇到：Google 的 Chromium QUIC、Cloudflare 的 quiche、Microsoft 的 MsQuic、ngtcp2（curl 的 HTTP/3 後端之一）、quic-go、Meta 的 mvfst、AWS 的 s2n-quic、Rust 的 quinn，以及 Python 的 aioquic。它們都是 user space 函式庫，互通性靠 IETF 的互通測試持續驗證。

## 13.12 動手做：編解碼 varint、解析 header、模擬 HOL 與遷移

這一節的四段程式都只用標準函式庫、在本機離線執行。第一段實作 varint；第二段解析手組的 long header 與 short header；第三段用模擬時鐘比較 TCP 與 QUIC 的 HOL；第四段用真的 UDP socket 在 127.0.0.1 上模擬 connection migration。

### 練習一：variable-length integer 編解碼

```python
# QUIC variable-length integer（RFC 9000 第 16 節）：前 2 bit 決定總長度
PREFIX_LEN = {0b00: 1, 0b01: 2, 0b10: 4, 0b11: 8}
LIMITS = [(63, 0b00, 1), (16383, 0b01, 2), (1073741823, 0b10, 4), (4611686018427387903, 0b11, 8)]


def encode_varint(value: int) -> bytes:
    """用能裝下 value 的最短長度編碼。"""
    for limit, prefix, length in LIMITS:
        if 0 <= value <= limit:
            raw = value.to_bytes(length, "big")
            # 把 2-bit 前綴塞進第一個 byte 的最高兩位
            return bytes([raw[0] | (prefix << 6)]) + raw[1:]
    raise ValueError(f"{value} 超出 62 bit")


def decode_varint(buf: bytes, pos: int = 0) -> tuple[int, int]:
    """回傳 (數值, 讀完後的位置)。"""
    first = buf[pos]
    length = PREFIX_LEN[first >> 6]
    if pos + length > len(buf):
        raise ValueError("資料不足，varint 被截斷")
    value = first & 0x3F  # 去掉前綴，只留 6 個有效 bit
    for b in buf[pos + 1:pos + length]:
        value = (value << 8) | b
    return value, pos + length


# RFC 9000 附錄 A.1 的範例
samples = {
    "c2197c5eff14e88c": 151288809941952652,
    "9d7f3e7d": 494878333,
    "7bbd": 15293,
    "25": 37,
    "4025": 37,  # 非最短編碼也合法，解出來一樣是 37
}
for hexstr, expect in samples.items():
    value, end = decode_varint(bytes.fromhex(hexstr))
    assert value == expect and end == len(hexstr) // 2
    print(f"decode {hexstr:<16} -> {value:>20}  ({end} bytes)")

print()
for v in [0, 63, 64, 16383, 16384, 1073741823, 1073741824, 2**62 - 1]:
    enc = encode_varint(v)
    assert decode_varint(enc) == (v, len(enc))
    print(f"encode {v:>19} -> {enc.hex():<16} prefix={enc[0] >> 6:02b} len={len(enc)}")

# 連續讀多個 varint：QUIC frame 就是這樣一個欄位接一個欄位讀
stream = encode_varint(4) + encode_varint(1200) + encode_varint(70000)
pos, fields = 0, []
while pos < len(stream):
    v, pos = decode_varint(stream, pos)
    fields.append(v)
print("\n連續解碼", stream.hex(), "->", fields)
assert fields == [4, 1200, 70000]
try:
    decode_varint(bytes.fromhex("9d7f"))
except ValueError as exc:
    print("截斷的輸入:", exc)
```

```text
decode c2197c5eff14e88c ->   151288809941952652  (8 bytes)
decode 9d7f3e7d         ->            494878333  (4 bytes)
decode 7bbd             ->                15293  (2 bytes)
decode 25               ->                   37  (1 bytes)
decode 4025             ->                   37  (2 bytes)

encode                   0 -> 00               prefix=00 len=1
encode                  63 -> 3f               prefix=00 len=1
encode                  64 -> 4040             prefix=01 len=2
encode               16383 -> 7fff             prefix=01 len=2
encode               16384 -> 80004000         prefix=10 len=4
encode          1073741823 -> bfffffff         prefix=10 len=4
encode          1073741824 -> c000000040000000 prefix=11 len=8
encode 4611686018427387903 -> ffffffffffffffff prefix=11 len=8

連續解碼 0444b080011170 -> [4, 1200, 70000]
截斷的輸入: 資料不足，varint 被截斷
```

逐段解說輸出。前五行用 RFC 9000 附錄給的範例驗證解碼：`c2197c5eff14e88c` 的前兩位是 `11`，所以讀 8 bytes；`9d7f3e7d` 的前兩位是 `10`，讀 4 bytes。最後兩行說明同一個數字 37 有兩種合法編碼，解碼程式不能假設「一定是最短編碼」。

中間八行是邊界測試：63 是 1 byte 的上限，64 就要用 2 bytes 的 `4040`；16383 與 16384、1073741823 與 1073741824 也都剛好跨過邊界。`prefix` 那一欄印出第一個 byte 的最高兩位，可以對照 13.4 節的表格。最後兩段示範實際解析 frame 的方式：欄位一個接一個，用上一個 varint 結束的位置當下一個的起點；輸入被截斷時要報錯，而不是讀到緩衝區外，處理網路輸入時這是基本要求。

### 練習二：解析 long header 與 short header

```python
# 解析 QUIC v1 的 long header 與 short header（RFC 9000 第 17 節）
# 注意：真實封包的 first byte 低位元與 packet number 有 header protection，
# 這裡用的是「去掉保護之後」的 bytes，才能直接讀。
LONG_TYPES = {0: "Initial", 1: "0-RTT", 2: "Handshake", 3: "Retry"}


def varint(buf, pos):
    length = 1 << (buf[pos] >> 6)
    value = buf[pos] & 0x3F
    for b in buf[pos + 1:pos + length]:
        value = (value << 8) | b
    return value, pos + length


def parse_packet(buf: bytes, local_cid_len: int) -> dict:
    first = buf[0]
    if first & 0x80:  # Header Form = 1：long header
        version = int.from_bytes(buf[1:5], "big")
        pos = 5
        dcid_len = buf[pos]; dcid = buf[pos + 1:pos + 1 + dcid_len]; pos += 1 + dcid_len
        scid_len = buf[pos]; scid = buf[pos + 1:pos + 1 + scid_len]; pos += 1 + scid_len
        if version == 0:
            versions = [buf[i:i + 4].hex() for i in range(pos, len(buf), 4)]
            return {"form": "long", "type": "Version Negotiation", "dcid": dcid.hex() or "(empty)",
                    "scid": scid.hex(), "supported": versions}
        info = {"form": "long", "fixed_bit": (first >> 6) & 1,
                "type": LONG_TYPES[(first >> 4) & 0x3], "version": f"0x{version:08x}",
                "dcid": dcid.hex() or "(empty)", "scid": scid.hex() or "(empty)"}
        if info["type"] == "Initial":
            token_len, pos = varint(buf, pos)
            info["token_len"] = token_len
            pos += token_len
        length, pos = varint(buf, pos)        # 之後 packet number + payload 的長度
        pn_len = (first & 0x03) + 1
        info.update(length=length, pn_len=pn_len,
                    packet_number=int.from_bytes(buf[pos:pos + pn_len], "big"),
                    header_bytes=pos + pn_len)
        return info
    # Header Form = 0：short header（1-RTT）。DCID 長度不在封包裡，
    # 接收端必須自己知道「我發出去的 connection ID 有多長」。
    pn_len = (first & 0x03) + 1
    dcid = buf[1:1 + local_cid_len]
    pos = 1 + local_cid_len
    return {"form": "short", "fixed_bit": (first >> 6) & 1, "spin_bit": (first >> 5) & 1,
            "key_phase": (first >> 2) & 1, "dcid": dcid.hex(), "pn_len": pn_len,
            "packet_number": int.from_bytes(buf[pos:pos + pn_len], "big"),
            "header_bytes": pos + pn_len}


# 1) RFC 9001 附錄 A.2 client Initial 的「未保護」header
initial = bytes.fromhex("c300000001088394c8f03e5157080000449e00000002")
# 2) 手組 Handshake：server 回給 client。DCID 填 client 的 SCID（上面是空的），
#    SCID 是 server 自己選的 connection ID，之後 client 都用它當 DCID
handshake = bytes.fromhex("e1" "00000001" "00" "08" "f067a5502a4262b5" "4016" "0001")
# 3) 手組 1-RTT short header：0x41 = 0100 0001
short = bytes.fromhex("41" "f067a5502a4262b5" "1a2b") + b"<encrypted payload>"
# 4) Version Negotiation：version 欄位是 0
vn = bytes.fromhex("80" "00000000" "00" "08" "8394c8f03e515708" "00000001" "6b3343cf")

for name, pkt in [("Initial", initial), ("Handshake", handshake), ("1-RTT", short), ("VN", vn)]:
    print(f"--- {name}: first byte {pkt[0]:08b}")
    for k, v in parse_packet(pkt, local_cid_len=8).items():
        print(f"    {k:<14}{v}")

p = parse_packet(initial, 8)
assert (p["type"], p["dcid"], p["length"], p["packet_number"]) == ("Initial", "8394c8f03e515708", 1182, 2)
assert parse_packet(handshake, 8)["scid"] == "f067a5502a4262b5"
assert parse_packet(vn, 8)["supported"] == ["00000001", "6b3343cf"]
s = parse_packet(short, 8)
assert s["form"] == "short" and s["packet_number"] == 0x1a2b and s["header_bytes"] == 11
```

```text
--- Initial: first byte 11000011
    form          long
    fixed_bit     1
    type          Initial
    version       0x00000001
    dcid          8394c8f03e515708
    scid          (empty)
    token_len     0
    length        1182
    pn_len        4
    packet_number 2
    header_bytes  22
--- Handshake: first byte 11100001
    form          long
    fixed_bit     1
    type          Handshake
    version       0x00000001
    dcid          (empty)
    scid          f067a5502a4262b5
    length        22
    pn_len        2
    packet_number 1
    header_bytes  19
--- 1-RTT: first byte 01000001
    form          short
    fixed_bit     1
    spin_bit      0
    key_phase     0
    dcid          f067a5502a4262b5
    pn_len        2
    packet_number 6699
    header_bytes  11
--- VN: first byte 10000000
    form          long
    type          Version Negotiation
    dcid          (empty)
    scid          8394c8f03e515708
    supported     ['00000001', '6b3343cf']
```

第一個封包是 RFC 9001 附錄 A 範例中 client Initial 去掉 header protection 後的 header。第一個 byte `11000011` 拆開來是：long header、fixed bit 為 1、類型 `00`（Initial）、保留位元 `00`、packet number 長度 `11`（4 bytes）。DCID 是 client 隨機選的 8 bytes `8394c8f03e515708`，SCID 是空的，token 長度 0，Length 是 varint `449e`，也就是 1182 bytes，packet number 是 2。從第一個 byte 到 Length 欄位為止是 18 bytes，Length 的 1182 bytes 涵蓋 packet number 與 payload，合計正好 1200 bytes，符合 client Initial 的最小大小；`header_bytes` 的 22 是把 4 bytes 的 packet number 也算進去。

第二個封包是手組的 Handshake：server 回給 client，DCID 填 client 的 SCID（空的），SCID 填 server 自己選的 `f067a5502a4262b5`。從這一刻起，client 寄給 server 的封包都會用這個 ID 當 DCID，所以第三個封包，也就是 short header，DCID 就是 `f067…`。注意 short header 的解析函式需要 `local_cid_len=8` 這個參數：封包裡沒有長度欄位，是 server 自己知道自己發的 ID 有 8 bytes。第四個封包是 Version Negotiation：Version 欄位為 0，後面列出 server 支援的版本，這裡是 v1 與 v2。

### 練習三：同一連線多個 stream，其中一個丟包

```python
# 同一條連線上有三個 stream，其中一個封包遺失：
# 比較 TCP（單一 byte stream）與 QUIC（每個 stream 各自排序）交給應用程式的時間。
ONE_WAY = 50       # ms，單程延遲；RTT = 100 ms
GAP = 5            # ms，每 5 ms 送一個封包
LOST_INDEX = 2     # 第 3 個封包在路上遺失
STREAMS = ["chat", "board", "slide"]

# 依序送 12 個封包，三個 stream 輪流；slide 是投影片圖片，資料最多
sends = []  # (送出時間, packet number, stream 名稱, 這個 stream 裡的第幾塊)
chunk_no = {s: 0 for s in STREAMS}
for i in range(12):
    stream = STREAMS[i % 3]
    sends.append((i * GAP, i, stream, chunk_no[stream]))
    chunk_no[stream] += 1

# 計算每個封包「抵達接收端」的時間
arrivals = []
for t, pn, stream, chunk in sends:
    if pn == LOST_INDEX:
        # 送端收到後面 3 個封包的 ACK 才判定遺失（packet threshold = 3）：
        # 第 pn+3 個封包送出 + RTT 之後重傳，再過單程抵達
        detect = sends[pn + 3][0] + 2 * ONE_WAY
        new_pn = len(sends)  # QUIC 重傳用「新的」packet number，TCP 則重送同一段序號
        arrivals.append((detect + ONE_WAY, pn, new_pn, stream, chunk))
    else:
        arrivals.append((t + ONE_WAY, pn, pn, stream, chunk))

# TCP：所有 stream 的資料塞在同一個 byte stream，必須「整條」依序交付
tcp_deliver, last = {}, 0
for arrive, pn, _, _, _ in sorted(arrivals, key=lambda a: a[1]):  # 依原始順序
    last = max(last, arrive)
    tcp_deliver[pn] = last

# QUIC：每個 stream 自己依 offset 排序，只等「同一個 stream」裡前面的資料
quic_deliver, last_by_stream = {}, {s: 0 for s in STREAMS}
for arrive, pn, _, stream, _ in sorted(arrivals, key=lambda a: a[1]):
    last_by_stream[stream] = max(last_by_stream[stream], arrive)
    quic_deliver[pn] = last_by_stream[stream]

print(" pn  stream chunk  arrive   tcp_at   quic_at  note")
for arrive, pn, wire_pn, stream, chunk in sorted(arrivals, key=lambda a: a[1]):
    note = f"遺失，重傳為 pn={wire_pn}" if pn != wire_pn else ""
    print(f"{pn:>3}  {stream:<6}{chunk:>5}{arrive:>8}{tcp_deliver[pn]:>9}{quic_deliver[pn]:>10}  {note}")

print("\n每個 stream 因為遺失而多等的時間（交付 - 抵達，取最大值）：")
for s in STREAMS:
    rows = [a for a in arrivals if a[3] == s]
    tcp_wait = max(tcp_deliver[a[1]] - a[0] for a in rows)
    quic_wait = max(quic_deliver[a[1]] - a[0] for a in rows)
    print(f"  {s:<6} TCP {tcp_wait:>3} ms   QUIC {quic_wait:>3} ms")
    if s != "slide":
        assert quic_wait == 0 and tcp_wait > 0  # 別的 stream 在 QUIC 不受影響
assert all(quic_deliver[pn] <= tcp_deliver[pn] for pn in tcp_deliver)
```

```text
 pn  stream chunk  arrive   tcp_at   quic_at  note
  0  chat      0      50       50        50  
  1  board     0      55       55        55  
  2  slide     0     175      175       175  遺失，重傳為 pn=12
  3  chat      1      65      175        65  
  4  board     1      70      175        70  
  5  slide     1      75      175       175  
  6  chat      2      80      175        80  
  7  board     2      85      175        85  
  8  slide     2      90      175       175  
  9  chat      3      95      175        95  
 10  board     3     100      175       100  
 11  slide     3     105      175       175  

每個 stream 因為遺失而多等的時間（交付 - 抵達，取最大值）：
  chat   TCP 110 ms   QUIC   0 ms
  board  TCP 105 ms   QUIC   0 ms
  slide  TCP 100 ms   QUIC 100 ms
```

表格每一列是一個封包。pn 2 屬於 slide，在路上遺失；送端在收到 pn 5 的 ACK 時（晚了 3 個號碼，達到 packet threshold）判定遺失，以新的 pn 12 重傳，在 175 ms 抵達。`arrive` 是封包到達接收端的時間，`tcp_at` 與 `quic_at` 是交給應用程式的時間。

TCP 那一欄從 pn 2 之後全部變成 175：pn 3 的聊天訊息 65 ms 就到了，卻要等到 175 ms 才交給瀏覽器，多等了 110 ms。QUIC 那一欄只有 slide（pn 2、5、8、11）是 175，chat 與 board 都在抵達的當下就交付。最後的摘要把差異量化：chat 與 board 在 QUIC 下的額外等待是 0，slide 兩種協定都要等約一個 RTT，因為 stream 內仍然保序。這段模擬刻意簡化了擁塞控制與 ACK 的細節，但呈現了 HOL 差異的本質：差別不在「重傳得比較快」，而在「沒有遺失的 stream 不必陪著等」。

### 練習四：connection migration

```python
# Connection migration：client 的位址改變（這裡用「換一個 UDP socket、拿到新的來源 port」模擬），
# server 不看四元組，而是用 connection ID 找到同一條連線。HMAC 代替 AEAD，
# 模擬「只有握有連線金鑰的人，才造得出 server 會接受的封包」。
import hashlib, hmac, os, socket

KEY = os.urandom(32)                       # 假裝是 TLS 交握導出的 1-RTT 金鑰
CID_1 = bytes.fromhex("f067a5502a4262b5")  # 交握時 server 給的 connection ID
CID_2 = bytes.fromhex("5b1e0c7d9a3f2e61")  # 之後用 NEW_CONNECTION_ID 多給的一個


def seal(cid, kind, data):
    body = cid + kind + data
    return body + hmac.new(KEY, body, hashlib.sha256).digest()[:16]


def unseal(pkt):
    body, tag = pkt[:-16], pkt[-16:]
    if not hmac.compare_digest(hmac.new(KEY, body, hashlib.sha256).digest()[:16], tag):
        return None
    return body[:8], body[8:9], body[9:]


server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(("127.0.0.1", 0)); server.settimeout(1)
SERVER = server.getsockname()
conn = {"path": None, "pending": {}, "data": []}
quic_table = {CID_1: conn, CID_2: conn}    # 兩個 CID 指向同一條連線
tcp_key = None                             # TCP 會用「交握時的四元組」當 key
names = {}


def label(addr):  # 埠號每次執行都不同，用代號顯示
    return names.setdefault(addr, f"addr#{len(names) + 1}")


def server_step():
    global tcp_key
    pkt, addr = server.recvfrom(2048)
    opened = unseal(pkt)
    if opened is None:
        return f"丟棄 {label(addr)} 的封包：驗證失敗，連線狀態不變"
    cid, kind, data = opened
    c = quic_table[cid]
    if c["path"] is None:
        c["path"], tcp_key = addr, addr
    if kind == b"R":  # PATH_RESPONSE
        if c["pending"].pop(addr, None) == data:
            c["path"] = addr
            return f"PATH_RESPONSE 正確 → 路徑改為 {label(addr)}"
        return "PATH_RESPONSE 不符，忽略"
    c["data"].append(data.decode())        # 新路徑上的資料照收，不必重傳
    if addr != c["path"]:
        challenge = os.urandom(8)
        c["pending"][addr] = challenge
        server.sendto(seal(cid, b"C", challenge), addr)
        tcp = "命中" if addr == tcp_key else "查無連線 → 回 RST"
        return (f"CID {cid.hex()[:4]}… 從新位址 {label(addr)} 收到 {data.decode()!r}；"
                f"送 PATH_CHALLENGE，驗證前最多回 {3 * len(pkt)} bytes（TCP：{tcp}）")
    server.sendto(seal(cid, b"D", b"ack " + data), addr)
    return f"CID {cid.hex()[:4]}… 在 {label(addr)} 收到 {data.decode()!r}"


def client_migrate(sock, cid, text):
    sock.sendto(seal(cid, b"D", text), SERVER)
    print("  ", server_step())
    _, kind, challenge = unseal(sock.recvfrom(2048)[0])
    assert kind == b"C"
    sock.sendto(seal(cid, b"R", challenge), SERVER)  # 原樣回傳 8 bytes
    print("  ", server_step())


def new_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0)); s.settimeout(1)
    return s


print("1. 交握完成，在 Wi-Fi 上傳資料")
wifi = new_socket()
wifi.sendto(seal(CID_1, b"D", b"chat: hello"), SERVER)
print("  ", server_step())
wifi.recvfrom(2048)

print("2. NAT rebinding：client 不知道自己的對外 port 變了，沿用同一個 CID")
rebound = new_socket(); wifi.close()
client_migrate(rebound, CID_1, b"board: stroke#42")

print("3. 主動遷移到 4G：client 換用新的 CID，避免被旁人把兩段路徑串起來")
lte = new_socket(); rebound.close()
client_migrate(lte, CID_2, b"board: stroke#43")

print("4. 沒有金鑰的第三方拿 CID 從別處送假封包")
attacker = new_socket()
attacker.sendto(CID_1 + b"D" + b"fake" + bytes(16), SERVER)
print("  ", server_step())

assert conn["path"] == lte.getsockname() and len(set(map(id, quic_table.values()))) == 1
assert conn["data"] == ["chat: hello", "board: stroke#42", "board: stroke#43"]
print("\n同一條連線收到的資料:", conn["data"])
for s in (lte, attacker, server):
    s.close()
```

```text
1. 交握完成，在 Wi-Fi 上傳資料
   CID f067… 在 addr#1 收到 'chat: hello'
2. NAT rebinding：client 不知道自己的對外 port 變了，沿用同一個 CID
   CID f067… 從新位址 addr#2 收到 'board: stroke#42'；送 PATH_CHALLENGE，驗證前最多回 123 bytes（TCP：查無連線 → 回 RST）
   PATH_RESPONSE 正確 → 路徑改為 addr#2
3. 主動遷移到 4G：client 換用新的 CID，避免被旁人把兩段路徑串起來
   CID 5b1e… 從新位址 addr#3 收到 'board: stroke#43'；送 PATH_CHALLENGE，驗證前最多回 123 bytes（TCP：查無連線 → 回 RST）
   PATH_RESPONSE 正確 → 路徑改為 addr#3
4. 沒有金鑰的第三方拿 CID 從別處送假封包
   丟棄 addr#4 的封包：驗證失敗，連線狀態不變

同一條連線收到的資料: ['chat: hello', 'board: stroke#42', 'board: stroke#43']
```

這段程式用真的 UDP socket：server 綁在 127.0.0.1 的隨機 port，client 每「換一次網路」就關掉舊 socket、開一個新 socket，系統會分配不同的來源 port，對 server 來說就是一個新的來源位址。因為 port 每次執行都不同，輸出用 `addr#1`、`addr#2` 這種代號表示。HMAC 在這裡扮演 AEAD 的角色：只有知道連線金鑰的一方，才能產生 server 會接受的封包。

第 1 步是正常傳輸。第 2 步模擬 NAT rebinding：client 沿用 `f067…`，server 從新位址收到它，依 CID 找到同一條連線、照收資料，並送出 PATH_CHALLENGE；括號裡的 TCP 查表結果說明了同一情境下 TCP 會失敗。第 3 步模擬手機主動切到 4G，client 換用備用的 `5b1e…`，server 的查表把兩個 ID 指向同一條連線，流程一樣是先收資料、再驗證路徑。輸出裡的「驗證前最多回 123 bytes」是 3 倍防放大限制的計算（client 這個封包 41 bytes）。第 4 步，沒有金鑰的第三方拿 `f067…` 從別的位址送假封包，驗證失敗就直接丟棄，連線路徑不會被搶走。最後的 assert 確認三筆資料都在同一條連線上收到，路徑停在最新的 4G 位址。

## 13.13 在工作上怎麼用

### 情境一：替聲聲 Live 啟用 HTTP/3

小晴的上線清單如下，順序本身就是判斷流程：

1. **確認 UDP 443 一路暢通**：CDN、load balancer 的 security group（第 7 章）與 listener 都要開 UDP 443，不只是 TCP 443。
2. **保留 HTTP/2 與 HTTP/1.1**：HTTP/3 是加速選項，不是替代；fallback 靠的就是 TCP 那一條路。
3. **送出 Alt-Svc**：在 HTTP/2 回應加上 `Alt-Svc: h3=":443"; ma=86400`；若 DNS 供應商支援，加上 HTTPS record 宣告 `alpn="h3,h2"`。
4. **檢查憑證鏈大小**：讓 server 第一趟回覆在 3 倍防放大限制內，避免交握多一個 RTT。
5. **0-RTT 只放行 idempotent 請求**：在 CDN 上限制 0-RTT 的 method，必要時讓後端回 425。
6. **load balancer 要能依 connection ID 轉送**，否則就關閉主動遷移，或至少接受遷移失敗時的重連。
7. **觀察指標**：依協定分組的錯誤率、TTFB、連線遷移次數，以及「嘗試 h3 但退回 h2」的比例。

在 nginx 上，HTTP/3 的設定大致長這樣（指令依版本而定，以官方文件為準）：

```bash
# 示意設定片段，放在 nginx 的 server 區塊（需要支援 HTTP/3 的 nginx 版本）
#   listen 443 quic reuseport;
#   listen 443 ssl;
#   http2 on;
#   add_header Alt-Svc 'h3=":443"; ma=86400';
nginx -t && nginx -s reload
```

### 情境二：確認某個請求到底走了哪個協定

```bash
# 用 curl 強制 HTTP/3（curl 需以支援 HTTP/3 的方式編譯）
curl -sv --http3-only -o /dev/null https://www.shengsheng.example/ 2>&1 | grep -iE "HTTP/3|alt-svc|connect"
# 先試 h3、失敗退回 TCP 的行為
curl -sv --http3 -o /dev/null https://www.shengsheng.example/
# 看回應是否宣告 h3
curl -sI https://www.shengsheng.example/ | grep -i alt-svc
# 查 DNS 的 HTTPS record（type 65）
dig +short www.shengsheng.example HTTPS
```

瀏覽器端最快的方法是開 DevTools 的 Network 面板，右鍵欄位標題打開 Protocol 欄，`h3` 是 HTTP/3、`h2` 是 HTTP/2。第一次載入常看到 `h2`，重新整理後變成 `h3`，這正是 Alt-Svc 的發現流程。Chrome 的 `chrome://net-export` 可以錄下 netlog，看 QUIC 交握失敗與退回 TCP 的細節。

### 情境三：抓包分析 QUIC

QUIC 幾乎全加密，tcpdump 只看得到 UDP。要看內容，得讓 client 輸出 TLS 金鑰：

```bash
# 讓瀏覽器或 curl 把 TLS 金鑰寫到檔案（只在自己的測試機上做，檔案要妥善刪除）
export SSLKEYLOGFILE=/tmp/keys.log
sudo tcpdump -i any -w /tmp/quic.pcap 'udp port 443'
# Wireshark：Preferences → Protocols → TLS → (Pre)-Master-Secret log filename 指向 keys.log
# 顯示過濾：quic   或   quic.long.packet_type == 0（只看 Initial）
```

沒有金鑰時，Wireshark 仍能解出 long header 的版本與 connection ID，甚至能解開 Initial（因為金鑰可由 DCID 推導），看得到 ClientHello 的 SNI 與 ALPN；Handshake 與 1-RTT 就只是密文。另一個重要工具是 **qlog**：許多 QUIC 實作能把每個連線的事件（送出、收到、遺失判斷、cwnd 變化）輸出成結構化 log，搭配 qvis 這類視覺化工具，比抓包更容易看出「是遺失、流量控制還是擁塞控制」造成的慢。

### 情境四：SRE 判斷「HTTP/3 上線後變慢」

如果上線後某些使用者反而變慢，依序檢查：是否集中在特定網路（企業、某電信業者）→ 這些網路是否對 UDP 限速或半通 → server CPU 是否因 QUIC 加解密升高 → 憑證鏈是否讓交握多了一個 RTT → load balancer 是否因為依四元組轉送，讓遷移後的封包送錯後端。不能確定時，先對受影響的網路關閉 Alt-Svc 或縮短 `ma`，讓它們回到 HTTP/2，再慢慢查。

## 13.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 開了 HTTP/3，DevTools 永遠顯示 `h2` | UDP 443 沒開，或沒有送 Alt-Svc／HTTPS record | `curl -sI` 看 Alt-Svc；`curl --http3-only` 是否逾時；檢查 security group 的 UDP 規則 | 開放 UDP 443；在回應加 Alt-Svc |
| 部分企業使用者偶爾整頁卡住十幾秒才恢復 | 防火牆讓 QUIC 交握通過，之後丟棄 UDP；或 UDP 對應表逾時太短 | netlog／qlog 看到 QUIC 連線閒置後無回應、PTO 一再觸發；同網路改用 `--http2` 正常 | 縮短 keepalive PING 間隔；對該網路關閉 h3；請客戶放行 UDP 443 |
| 走 VPN 的使用者完全連不上 h3，但 h2 正常 | 路徑 MTU 小於 1200，Initial 送不過去 | 用 `ping -M do -s 1200` 一類方式測 MTU（第 8 章）；qlog 只看到 Initial 一直重送 | 依賴瀏覽器 fallback；VPN 端調大 MTU |
| 0-RTT 開啟後出現重複的預約紀錄 | 非 idempotent 請求被放進 early data，遭到重放或重送 | 後端 log 中重複請求帶有 early data 標記、間隔極短 | 只允許 GET／HEAD 走 0-RTT；其他請求回 425；寫入 API 用 idempotency key（第 24 章） |
| 手機換網路後 QUIC 連線仍然斷掉 | L4 LB 依四元組雜湊，遷移後送到別台後端；或後端回 stateless reset | 後端 log 出現未知 connection ID；抓包看到 stateless reset | LB 改為依 connection ID 轉送；或設 `disable_active_migration` 並接受重連 |
| QUIC 交握多花一個 RTT | 憑證鏈太大，超過 3 倍防放大限制；或 server 在啟用 Retry | qlog 看到 server 停在 amplification limit；或出現 Retry packet | 精簡憑證鏈、改 ECDSA、啟用憑證壓縮；只在受攻擊時啟用 Retry |
| 上線後 server CPU 明顯上升 | QUIC 在 user space 加解密、每個 datagram 一次系統呼叫 | 依協定比較每 Gbps 的 CPU；`perf` 看到大量 sendmsg | 啟用 UDP GSO／GRO；選擇有最佳化的實作；容量規劃納入 CPU |
| 下載大檔時速度上不去，qlog 有大量 BLOCKED | 接收端的流量控制視窗太小 | qlog 中 DATA_BLOCKED／STREAM_DATA_BLOCKED 頻繁 | 調大 initial_max_data／initial_max_stream_data 等傳輸參數 |

除錯 QUIC 時，最常犯的思考錯誤是「拿 TCP 的工具直接套」：`ss -t` 看不到 QUIC 連線（它們是 UDP socket，在 `ss -u` 裡，而且一個 socket 可能承載很多連線）；tcpdump 看不到序號與 ACK；中間的防火牆 log 也只有 UDP 流量。要把可觀測性放回應用程式：開 qlog、輸出 connection ID、在 access log 記錄協定版本與是否 0-RTT。

## 13.15 動手練習

1. **延伸 varint 程式**：寫一個 `encode_varint_min_len(value, min_len)`，強制用至少 `min_len` bytes 編碼（例如 37 編成 4 bytes `80000025`），並確認原本的 `decode_varint` 解得回來。
   *答案要點*：只要把 LIMITS 中長度小於 `min_len` 的項目略過即可；解碼不受影響，因為長度由前綴決定。

2. **延伸 header 解析器**：在練習二的 short header payload 後面接一個未加密的 STREAM frame（type `0x0e`，即 OFF 與 LEN 皆設、FIN 未設），內容是 stream ID 4、offset 1200、長度 5、資料 `hello`，寫出解析函式。
   *答案要點*：frame bytes 是 `0e 04 44b0 05 68656c6c6f`；依序用 varint 讀 stream ID、offset、length，再取 length bytes 資料。把 type 改成 `0x0f` 時應解出 FIN。

3. **改 HOL 模擬的參數**：把 `LOST_INDEX` 改成 0、3，並把 ONE_WAY 改成 150（模擬衛星或跨洲連線），觀察 chat 在 TCP 下的最大等待如何變化。再把三個 stream 都塞進同一個 stream 名稱，確認 QUIC 的優勢消失。
   *驗證方法*：TCP 的額外等待約等於「偵測時間＋單程延遲 − 抵達時間差」，會隨 RTT 線性增加；全部同一 stream 時 QUIC 欄位會和 TCP 一模一樣。

4. **延伸遷移程式**：加一個「server 驗證路徑之前，只能送 3 倍 bytes」的計數器，讓 server 在新路徑上想回一大段資料時被擋下，驗證通過後才放行；另外加一個情境：client 用一個 server 從沒發過的 CID 送封包，server 應回 stateless reset 或直接丟棄。
   *答案要點*：每個未驗證位址維護 `received` 與 `sent` 兩個計數，`sent + len(new) > 3 * received` 時延後送出。

5. **用真實工具觀察**：在自己的電腦上用 DevTools 打開一個大型網站，打開 Protocol 欄，記錄第一次載入與重新整理後的協定；再用 `curl -sI` 看 Alt-Svc。如果手邊有支援 HTTP/3 的 curl，分別用 `--http3-only` 與 `--http2` 加上 `-w '%{time_appconnect}\n'`，比較「加密連線建立完成」的時間。
   *驗證方法*：先用 `ping` 量出大約的 RTT；h2 的 `time_appconnect` 約為 2 個 RTT（TCP 加 TLS），h3 約為 1 個 RTT，差距應接近一個 RTT。多跑幾次取中位數，避免單次抖動誤導。

6. **用 Wireshark 看 Initial**：設定 SSLKEYLOGFILE 後抓一次 HTTP/3 連線，找到 client 的第一個 Initial，確認 UDP payload 至少 1200 bytes、DCID 長度、CRYPTO frame 裡的 SNI 與 ALPN（`h3`），以及 server 回覆裡串在同一個 datagram 的 Initial 與 Handshake。
   *答案要點*：Wireshark 的 QUIC 解析會在一個 UDP 封包下列出多個 QUIC packet；Initial 不需要 key log 也能解開，Handshake 與 1-RTT 需要。

## 本章重點整理

- TCP 難以演進的原因是協定僵化：大量 middlebox 依賴明文 TCP header 的長相，kernel 實作更新又慢，TCP Fast Open、MPTCP 等新功能都受到阻礙。
- QUIC 選擇 UDP 當外層，是因為 UDP 幾乎到處放行、又不帶多餘語意；可靠傳輸、順序、流量控制與擁塞控制都由 QUIC 自己做，在 user space 實作並隨應用程式更新。
- QUIC 幾乎加密所有傳輸層資訊，連 packet number 都受 header protection 保護，用「看不到就無從依賴」來防止再次僵化，代價是營運者失去部分可觀測性。
- 一個 UDP datagram 可以裝多個 QUIC packet，每個 packet 的加密 payload 是一串 frame，stream 則是由很多 STREAM frame 組成的邏輯資料流。
- Variable-length integer 用第一個 byte 的最高兩位表示 1、2、4、8 bytes 的長度，最大可表示 2^62 − 1，是 QUIC 幾乎所有欄位的編碼方式。
- Long header 帶版本號與兩個 connection ID，用在交握；short header 只帶 DCID 與 packet number，而且 DCID 沒有長度欄位，接收端必須自己知道長度。
- QUIC 把 TLS 1.3 的交握放進 CRYPTO frame，傳輸參數放進 TLS 擴充，新連線 1 RTT 就能送出請求，比 TCP 加 TLS 少一個 RTT。
- 0-RTT 只在 resumption 時可用，資料可能被重放，只能用在 idempotent 請求；server 可以拒絕 0-RTT 或回 425 Too Early。
- 位址驗證前 server 最多只能送收到 bytes 的 3 倍，所以 client 的 Initial 要撐到 1200 bytes；憑證鏈太大會讓交握多一個 RTT。
- Stream 讓一個封包的遺失只影響所屬 stream，消除了 TCP 層的 head-of-line blocking，但 stream 內仍然保序。
- QUIC 的 packet number 永不重用，重傳的是 frame 而不是 packet，RTT 量測沒有 TCP 的重傳歧義；遺失判斷用 packet threshold 與 time threshold，逾時用 PTO 探測。
- Connection ID 讓連線不再綁定四元組，client 換 IP 或 port 後，server 依 DCID 找到連線，再用 PATH_CHALLENGE／PATH_RESPONSE 驗證新路徑；主動遷移時要換用新的 connection ID 以保護隱私。
- 瀏覽器透過 Alt-Svc 或 DNS HTTPS record 發現 HTTP/3，QUIC 失敗時退回 TCP；真正難查的是 UDP 半通、MTU 太小與 UDP 限速。
- 部署 QUIC 要同時考慮 UDP 443 的開放、load balancer 依 connection ID 轉送、CPU 成本，以及用 qlog 與 key log 補回可觀測性。

## 延伸問答

> [!question]- Q1. 既然 UDP 不可靠，為什麼說 QUIC 和 TCP 一樣可靠？
> 「可靠」是指資料不會遺失、不會重複、依序交付給應用程式。這些性質可以在任何一層實作：TCP 是在 IP 之上實作，QUIC 是在 UDP 之上實作。UDP 只提供 port 與 checksum，等於一個「信封」，QUIC 在信封裡放自己的 packet number、ACK frame、重傳邏輯、流量控制與擁塞控制。
>
> 判斷依據是看機制，而不是看底層協定：QUIC 有 ACK range 回報收到的封包、有 packet threshold 與 time threshold 判斷遺失、有 PTO 處理尾端遺失，每條 stream 依 offset 重組並保證順序，這些都和 TCP 的可靠傳輸同等級。差別在於 QUIC 的順序保證是「每條 stream 各自」，而不是整條連線一條 byte stream。

> [!question]- Q2. 手算：varint `0x9d7f3e7d` 代表多少？數值 300 要怎麼編碼？
> `0x9d` 是 `1001 1101`，前兩位 `10` 代表總長 4 bytes。把前兩位清掉後第一個 byte 是 `0x1d`，四個 byte 接起來是 `0x1d7f3e7d`，十進位是 494,878,333，和 RFC 9000 附錄的範例相符。
>
> 300 大於 63、小於 16383，所以用 2 bytes。300 的十六進位是 `0x012c`，把第一個 byte 的最高兩位設成 `01`，也就是 `0x01 | 0x40 = 0x41`，得到 `0x412c`。驗算：`0x41` 清掉前綴是 `0x01`，接上 `0x2c` 是 `0x012c` = 300。也可以用 4 bytes 編成 `0x8000012c`，同樣合法，只是浪費 2 bytes。

> [!question]- Q3. 你在 production 看到：HTTP/3 上線後，某家企業客戶的使用者頁面偶爾整頁卡住 10 秒以上，其他使用者正常。最可能的原因是什麼，怎麼確認？
> 這個模式強烈指向「UDP 半通」。如果 UDP 443 被完全擋住，瀏覽器的 QUIC 交握會失敗並快速退回 TCP，使用者頂多感覺不到加速。但如果防火牆讓交握通過、之後卻因為 UDP 對應表逾時或流量檢查而丟棄封包，已經建立的 QUIC 連線會突然沒有回應，瀏覽器得等 PTO 多次退避或 idle timeout 才發現，然後才改走 TCP，造成十幾秒的卡頓。
>
> 確認方法：請受影響使用者錄 `chrome://net-export` 的 netlog，或在 server 端的 qlog 裡找這個網段的連線，看是否在閒置一段時間後只剩單向封包；同一台電腦用 `curl --http2` 正常、`--http3-only` 時好時壞也是佐證。短期處理是對這個網段停止宣告 Alt-Svc，或縮短 QUIC keepalive 間隔；長期是請客戶放行 UDP 443 並調長 UDP 逾時。

> [!question]- Q4. 為什麼 QUIC 的 short header 不放 connection ID 的長度？這不是讓解析變困難嗎？
> 因為只有「發出這個 ID 的一方」需要解析它。每個端點的 DCID 是自己當初發給對方的，長度自己最清楚，不需要在每個封包裡重複告訴自己。省下長度欄位，每個 1-RTT 封包少一個 byte，在大量小封包的連線上累積起來不算少。
>
> 更重要的是，這讓 server 可以自由設計 connection ID 的內部結構：例如前幾個 byte 編碼後端機器編號，讓 load balancer 依 DCID 轉送，達成 connection migration；或依不同叢集使用不同長度。如果規格把長度寫死在封包裡，路上的設備就會開始依賴它，又回到僵化的老路。代價是通用的被動分析工具無法在不知道長度的情況下切出 DCID，這也是刻意的取捨。

> [!question]- Q5. 面試題：QUIC 解決了 head-of-line blocking 嗎？請說清楚範圍。
> 只解決了「傳輸層、跨 stream」的 HOL。TCP 只有一條 byte stream，一個 segment 遺失會讓後面所有資料等待；QUIC 讓每條 stream 各自依 offset 重組，一個封包遺失只會讓它所屬的 stream 等待，其他 stream 照常交付。本章的模擬裡，chat 與 board 在 QUIC 下等待 0 ms，在 TCP 下等待超過 100 ms。
>
> 但有三個範圍外的情況：第一，stream 內仍保序，投影片自己還是要等重傳；第二，如果應用程式把所有資料放在同一條 stream，就沒有好處；第三，應用層若有跨 stream 的依賴（例如 header 壓縮共用的動態表），可能重新引入阻塞，所以 HTTP/3 的 QPACK 特別設計成可以避免這種依賴。另外，所有 stream 共用同一個擁塞控制，遺失導致的降速仍會影響整條連線。

> [!question]- Q6. 看封包找原因：qlog 顯示 server 送完 ServerHello 和一部分 Certificate 後就停下來，直到 client 送來 ACK 才繼續，交握花了 2 個 RTT。為什麼？
> 這是 anti-amplification limit 在作用。位址驗證完成前，server 送出的 bytes 不能超過從 client 收到的 3 倍。client 的第一個 Initial 約 1200 bytes，server 的額度就是約 3600 bytes。如果 server 的 ServerHello、EncryptedExtensions、憑證鏈與 CertificateVerify 加起來超過這個量，server 只能先送一部分，等 client 再送封包（例如 ACK）增加額度後才能送完，交握因此多出一個 RTT。
>
> 判斷依據是 qlog 裡 server 停下的時間點剛好在累計送出量接近 3 倍處。修法是縮小第一趟的資料量：移除不必要的中間憑證、改用 ECDSA 憑證（公鑰與簽章都比 RSA 小）、啟用 TLS 憑證壓縮。client 端也可以把 Initial 撐大一點，但這會增加每次連線的成本。

> [!question]- Q7. 設計取捨：聲聲 Live 的 L4 load balancer 依四元組雜湊轉送 UDP。啟用 HTTP/3 之後，應該怎麼處理 connection migration？
> 有三個選項。第一，讓 load balancer 依 DCID 轉送：server 產生 connection ID 時把後端編號編進去（必要時加密，避免外人讀出拓撲），load balancer 讀 DCID 決定後端。這能讓遷移真正生效，但需要 load balancer 支援，且 server 與 load balancer 要共享編碼規則。
>
> 第二，維持四元組雜湊，但在傳輸參數裡設 `disable_active_migration`，告訴 client 不要主動遷移。NAT rebinding 仍可能發生，這時封包會被送到錯的後端，後端查不到連線，可能回 stateless reset，client 重連。第三，什麼都不做，接受遷移失敗時的重連。對聲聲 Live 這種大量行動使用者的服務，第一個選項最值得投資；在 load balancer 還不支援前，第二個選項至少讓行為可預期。不論哪種，都要監控「未知 connection ID」的次數。

> [!question]- Q8. 概念辨析：TLS 1.3 本身就支援 0-RTT，為什麼「TCP + TLS 1.3」通常無法真正做到 0-RTT，QUIC 卻可以？
> TLS 1.3 的 0-RTT 是指「在 TLS 交握完成前送應用資料」，但它跑在 TCP 之上，TLS 的 ClientHello 必須等 TCP 三向交握完成才能送出。所以 TCP + TLS 1.3 early data 最快也要 1 個 RTT（TCP 交握）才能把請求送出去。要再省這 1 RTT，得靠 TCP Fast Open 在 SYN 裡帶資料，但 TFO 正是受協定僵化影響、部署困難的例子。
>
> QUIC 把傳輸層交握與 TLS 交握合併，client 的第一個 datagram 同時是「建立連線」和「ClientHello」，0-RTT 資料可以直接串在同一個 datagram 裡，真正做到第一個封包就帶請求。兩者的重放風險相同：不論在 TCP 還是 QUIC 上，0-RTT 資料都可能被重放，只能用於 idempotent 請求。

## 延伸閱讀

- RFC 9000〈QUIC: A UDP-Based Multiplexed and Secure Transport〉
- RFC 9001〈Using TLS to Secure QUIC〉
- RFC 9002〈QUIC Loss Detection and Congestion Control〉
- RFC 8999〈Version-Independent Properties of QUIC〉
- RFC 9114〈HTTP/3〉
- RFC 9312〈Manageability of the QUIC Transport Protocol〉
- RFC 9308〈Applicability of the QUIC Transport Protocol〉
