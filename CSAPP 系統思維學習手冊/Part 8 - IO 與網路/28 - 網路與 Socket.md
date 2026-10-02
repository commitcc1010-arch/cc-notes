---
chapter: 28
title: 網路與 Socket
part: 8
---

# 第 28 章　網路程式設計：Socket 與 Client-Server 模型

> [!abstract] 本章地圖
> **核心問題**：兩台機器上的兩個 process，怎麼透過網路交換資料？從程式的角度看，「網路連線」到底是什麼，又有哪些行為和讀寫本機檔案不一樣？
>
> **你會學到**：
> - 用 client-server 模型描述一次網路互動，並說出 IP 位址、port、連線之間的關係
> - 手算 IPv4 位址與 port 的二進位、十六進位與 network byte order 表示
> - 用 `getaddrinfo` 寫出同時支援 IPv4 與 IPv6 的 client 與 server，並說出 `socket`、`bind`、`listen`、`accept`、`connect` 各自的角色
> - 解釋為什麼 TCP 是 byte stream、為什麼「一次 write 不等於一次 read」，並設計訊息的 framing
> - 理解 backlog、TIME_WAIT、`Address already in use`、`Connection refused` 的成因，並用 `ss`、`nc`、`tcpdump` 診斷
>
> **前置知識**：第 3 章（byte order）、第 21 章（fork）、第 27 章（file descriptor 與 short count）
>
> **對應 CS:APP 3e**：第 11 章 11.1–11.4 節

## 28.1 故事：只在 production 壞掉的健康檢查

拾光相簿的 `thumbd` 除了接收 nginx 轉過來的 HTTP 請求，還開了一個內部用的「管理 port」：SRE 的監控程式連上去，送一行 `STATS\n`，`thumbd` 回一段 JSON，裡面有快取命中率、佇列長度這些數字。這個功能是小安寫的第一個 C 網路程式，在筆電上測了幾百次都沒問題。

上線第二天，SRE 阿哲回報：監控每隔一陣子就說「JSON 格式錯誤」，抓下來一看，收到的 JSON 只有前半段。小安看了自己的程式，client 端只寫了一行：`n = read(fd, buf, sizeof buf);`，然後把 `buf` 交給 JSON parser。「server 是一次 `write` 把整段 JSON 送出去的，為什麼 client 會只讀到一半？」

同一週還有第二件事。阿哲為了套用新設定重啟 `thumbd`，結果新的 process 起不來，log 裡只有一行：`bind: Address already in use`。舊的 process 明明已經結束了，`ps` 裡也找不到，為什麼 port 還被佔著？等了大約一分鐘再啟動，又好了。

老周聽完，在白板上畫了兩條線：「你把 socket 想成檔案，這個方向是對的，第 27 章學的 file descriptor 和 short count 在這裡全部適用。但網路多了兩件檔案沒有的事：資料是被切成封包、經過很多台機器送過來的；而且連線的兩端各有自己的狀態，關掉一條連線不是一瞬間的事。」這一章就沿著這兩條線，從網路的基本結構講到 socket API，最後回來修好這兩個問題。

## 28.2 Client-server 模型：網路程式的基本形狀

幾乎所有網路應用都是 **client-server 模型**（主從式模型）：一個 **server**（伺服器）process 管理某種資源，並等待別人來要；一個或多個 **client**（用戶端）process 主動送出請求。例如瀏覽器是 client、nginx 是 server；nginx 轉發請求給 `thumbd` 時，nginx 變成 client、`thumbd` 是 server。所以「client」和「server」說的是 process 在一次互動中的角色，不是指機器：同一台機器上可以同時跑 client 與 server，同一個 process 也可以同時扮演兩種角色。

一次完整的互動叫一個 **transaction**（交易），由四個步驟組成：

```text
   client process                                 server process
 ┌──────────────┐  ① 送出請求（request）       ┌──────────────┐
 │              │ ───────────────────────────▶ │              │
 │   瀏覽器、   │                              │ ② 處理請求： │
 │   監控程式   │                              │   讀檔、查表、│
 │              │  ③ 送回回應（response）      │   產生縮圖    │
 │ ④ 處理回應   │ ◀─────────────────────────── │              │
 └──────────────┘                              └──────────────┘
                                                  管理資源：
                                                  原圖、快取、設定
```

① client 需要服務時送出請求，例如「給我 `cat.jpg` 寬 200 的縮圖」。② server 收到後解讀請求，操作自己管理的資源。③ server 把結果送回去。④ client 拿到回應後做自己的事，例如把圖片顯示出來。

這裡的「transaction」和資料庫的交易不同，沒有 commit 或 rollback 的意思，只是「一次請求與回應」。這四步看起來理所當然，但每一步都可能失敗：請求可能送不到、server 可能處理到一半當掉、回應可能遺失。網路程式的難處大多來自「中間那條線不可靠，而且兩端看不到對方的狀態」。

## 28.3 網路是怎麼把 bytes 送到另一台機器的

在寫 socket 之前，需要一個夠用的網路圖像。對主機來說，網路只是另一種 I/O 裝置：網路卡（NIC，network interface card）接在 I/O 匯流排上，從網路收到的資料經過網路卡、透過 DMA 複製到記憶體，送出時反過來。真正複雜的是「網路」本身。

### 從一條線到全世界

最小的網路是 **LAN**（local area network，區域網路），例如一棟辦公室裡用 Ethernet 連起來的機器。每台主機有一張網路卡，網路卡有一個 48-bit 的硬體位址（MAC address），同一個 LAN 裡的資料以 **frame**（訊框）為單位傳送，frame 的 header 寫著目的地的 MAC 位址。

多個 LAN 用 **router**（路由器）連接起來，形成 **internet**（小寫，泛指互連的網路）；全球最大、使用 TCP/IP 協定的那一個就是大寫的 **Internet**。問題在於：不同 LAN 可能用完全不同的技術（Ethernet、Wi-Fi、行動網路），frame 格式與位址格式都不一樣。要讓資料跨越它們，需要一層「大家都懂」的協定，這就是 **IP**（Internet Protocol）：

- 它定義一套統一的主機位址（IP 位址），不管底下是什麼網路技術。
- 它定義統一的資料單位 **packet**（封包，IP 的術語叫 datagram）：一個 header 加上資料（payload）。

### 封裝：每一層加上自己的 header

`thumbd` 回傳一段資料給 client 時，這段資料會一層一層被包起來：

```text
 應用程式的資料（例如 HTTP 回應的一部分）
                              ┌───────────────────┐
                              │      payload      │
                              └───────────────────┘
 TCP 加上 TCP header（port、序號、確認號）
                   ┌──────────┬───────────────────┐
                   │ TCP hdr  │      payload      │   ← segment
                   └──────────┴───────────────────┘
 IP 加上 IP header（來源與目的 IP 位址）
         ┌─────────┬──────────┬───────────────────┐
         │ IP hdr  │ TCP hdr  │      payload      │   ← packet
         └─────────┴──────────┴───────────────────┘
 網路卡加上 frame header（這一段 LAN 的下一站 MAC 位址）
 ┌───────┬─────────┬──────────┬───────────────────┐
 │ frame │ IP hdr  │ TCP hdr  │      payload      │   ← frame
 └───────┴─────────┴──────────┴───────────────────┘
```

每一層只看自己的 header：router 收到 frame，拆掉 frame header，看 IP header 決定下一站，再包上新 LAN 的 frame header 送出；IP header 從頭到尾不變（除了存活時間等少數欄位）。到了目的主機，kernel 一層一層拆開，最後把 payload 交給正確的 process。這種「每層加 header、每層只處理自己那一層」的設計叫 **協定分層**（protocol layering）。

### TCP/IP 協定家族

Internet 上的程式主要用到三個協定：

| 協定 | 層 | 提供什麼 | 不提供什麼 | 例子 |
|---|---|---|---|---|
| IP | 網路層 | 把 packet 從一台主機送到另一台主機（盡力而為） | 不保證送到、不保證順序、可能重複 | 所有 Internet 流量的底層 |
| UDP | 傳輸層 | 在 IP 上加上 port，讓資料送到某台主機上的某個 process | 和 IP 一樣不可靠，但保留每則訊息的邊界 | DNS 查詢、影音串流、QUIC |
| TCP | 傳輸層 | 可靠、有序、雙向的 **byte stream** 連線 | 不保留訊息邊界、不保證延遲 | HTTP/1.1、HTTP/2、SSH、資料庫連線 |

TCP 怎麼在不可靠的 IP 上做出可靠的連線？它給每個 byte 編序號，接收端回報「我收到第幾號以前的所有資料」（acknowledgment），送出端在一段時間沒收到確認時重送；接收端依序號把亂序的資料排好，丟掉重複的。這些全部由 kernel 完成，應用程式看到的只是一條「寫進去的 bytes 會依序、不重複地從另一端讀出來」的管子。

這條管子有一個重要的特性：**它只保證 bytes 的順序，不知道你的「訊息」從哪裡開始、到哪裡結束。** 28.1 節的 JSON 被切成兩半，根源就在這裡，28.8 節會詳細說明。

> [!note] 不必背 OSI 七層
> 教科書常畫 OSI 七層模型。寫網路程式時，夠用的模型是四件事：應用程式資料、TCP（或 UDP）、IP、底層網路。只要知道每一層加什麼 header、解決什麼問題，就能讀懂 `tcpdump` 的輸出和大部分錯誤訊息。

## 28.4 IP 位址、port 與網域名稱

### IPv4 位址與 dotted-decimal

**IPv4 位址**是一個 32-bit 的 unsigned 整數。人類讀寫時用 **dotted-decimal**（點分十進位）表示法：把 32 bits 分成 4 個 byte，每個 byte 寫成 0–255 的十進位數，中間用點隔開。

手算一次：把 `140.112.8.116` 轉成十六進位與在 network byte order 下的記憶體內容。

| byte | 十進位 | 二進位 | 十六進位 |
|---|---|---|---|
| 第 1 個 | 140 | 1000 1100 | 0x8c |
| 第 2 個 | 112 | 0111 0000 | 0x70 |
| 第 3 個 | 8 | 0000 1000 | 0x08 |
| 第 4 個 | 116 | 0111 0100 | 0x74 |

所以這個位址的 32-bit 值是 `0x8c700874`。反過來，看到 `0x7f000001`，切成 `7f 00 00 01`，就是 `127.0.0.1`。

TCP/IP 規定所有寫進 header 的多 byte 整數都用 **network byte order**，也就是 big endian（第 3 章）：最高位的 byte 放在最低位址。x86-64 與 ARM64（一般設定）都是 little endian，所以程式在主機格式與網路格式之間要轉換：

```text
 值 0x8c700874（140.112.8.116）在記憶體中：

 位址          a     a+1   a+2   a+3
 network order 8c    70    08    74     ← 寫進 IP header、struct in_addr 的樣子
 little endian 74    08    70    8c     ← 這台機器上 uint32_t 變數的樣子

 htonl(x)：host to network long（32-bit）    ntohl(x)：反方向
 htons(x)：host to network short（16-bit）   ntohs(x)：反方向
```

在 big endian 機器上這四個函式什麼都不做；在 little endian 機器上它們會反轉 byte 順序。寫程式時一律呼叫它們，不要自己判斷平台。更好的做法是用 `inet_pton`（presentation to network，文字轉二進位）與 `inet_ntop`（反方向），它們同時支援 IPv4 與 IPv6，結果直接就是 network byte order。

幾個特殊位址要認得：`127.0.0.1` 是 **loopback**（回送位址），封包不會離開這台機器，本章的範例都用它；`0.0.0.0` 用在 server 時表示「這台機器的所有介面」；`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16` 是私有位址，常見於公司內網與雲端的 VPC。

### IPv6

IPv4 只有約 43 億個位址，早已不夠分配。**IPv6** 把位址擴大到 128 bits，寫成 8 組十六進位、用冒號隔開，連續的 0 可以縮寫成 `::`。例如 loopback 是 `::1`，等於 `0000:0000:0000:0000:0000:0000:0000:0001`。

| 項目 | IPv4 | IPv6 |
|---|---|---|
| 位址長度 | 32 bits | 128 bits |
| 文字表示 | `127.0.0.1` | `::1`、`2001:db8::10` |
| C 結構 | `struct sockaddr_in`（16 bytes） | `struct sockaddr_in6`（28 bytes） |
| address family 常數 | `AF_INET` | `AF_INET6` |
| loopback | `127.0.0.1` | `::1` |
| 「所有介面」 | `0.0.0.0` | `::` |
| 和 port 一起寫 | `127.0.0.1:8080` | `[::1]:8080`（要加中括號） |

對寫程式的人來說，最重要的結論是：**不要在程式裡假設位址一定是 4 bytes**。用 28.6 節的 `getaddrinfo`，同一份程式就能同時支援兩種位址。

### Port：一台機器上的哪一個 process

IP 位址只能把資料送到某一台主機。主機上可能同時跑著 nginx、`thumbd`、資料庫，kernel 要靠 **port**（埠號）決定交給誰。port 是 16-bit 的 unsigned 整數，範圍 0–65535。

- **well-known port**（知名埠）：0–1023，給標準服務用，例如 HTTP 80、HTTPS 443、SSH 22。在 Linux 上，一般使用者的程式預設不能 bind 這些 port。
- **ephemeral port**（臨時埠）：client 呼叫 `connect` 時，kernel 自動挑一個沒在用的 port 當 client 端的 port。範圍依平台而定：Linux 預設是 32768–60999（`/proc/sys/net/ipv4/ip_local_port_range`），macOS 預設是 49152–65535。

port 也要用 network byte order 存。手算 `8080`：8080 = 0x1F90，network order 的兩個 byte 是 `1f 90`。在 little endian 主機上，`unsigned short p = 8080;` 在記憶體中是 `90 1f`，`htons(8080)` 的結果在記憶體中才是 `1f 90`。28.10 節的程式會實際印出來。

### 連線就是一組四元組

一條 TCP **連線**（connection）由兩端的「位址：port」唯一決定，這一組叫 **socket pair**，常說成 **四元組**（4-tuple）：

```text
 (client IP : client port ,  server IP : server port)

 例：監控程式連到 thumbd 的管理 port
 (10.0.3.17 : 51234      ,  10.0.1.5  : 9100)
   └ ephemeral port，         └ thumbd 固定 listen
     kernel 自動挑               的 well-known（自訂）port

 同一個監控程式再開第二條連線：
 (10.0.3.17 : 51235      ,  10.0.1.5  : 9100)   ← 只有 client port 不同，是另一條連線
```

這個觀念解答了一個常見疑問：「server 只用一個 port，為什麼能同時服務上萬條連線？」因為 kernel 是用整組四元組來區分連線的，server 那一半一樣也沒關係。反過來，從同一台 client 主機連到同一個 server IP 與 port 的連線數，會受限於 client 能用的 ephemeral port 數量，這是高流量反向代理常遇到的問題（28.12 節）。

### 網域名稱與 DNS

人類不想記 `140.112.8.116`，所以有 **網域名稱**（domain name），例如 `photos.example.com`。名稱與位址的對照由 **DNS**（Domain Name System）這個分散式資料庫維護。對應關係不一定是一對一：

| 情況 | 例子 | 對程式的意義 |
|---|---|---|
| 一個名稱對一個位址 | 內部服務 `thumbd-1.internal` → `10.0.1.5` | 最單純 |
| 一個名稱對多個位址 | 大型網站回傳好幾個 IP，或同時有 IPv4 與 IPv6 | client 要逐一嘗試，第一個連不上就試下一個 |
| 多個名稱對同一個位址 | 同一台主機上的多個虛擬主機 | server 要靠 HTTP 的 `Host` header 區分（第 29 章） |
| 名稱沒有對應位址 | 打錯字、內部名稱在外網查不到 | `getaddrinfo` 回傳錯誤，要處理 |

`localhost` 是一個特別的名稱，通常在 `/etc/hosts` 裡設定成 `127.0.0.1` 與 `::1`。這帶來一個實務上很常見的坑：client 連 `localhost` 時，系統可能先回傳 `::1`；如果 server 只 bind 了 `127.0.0.1`，第一次嘗試就會被拒絕。寫得好的 client 會接著試下一個位址，寫得不好的 client 就直接報錯。

## 28.5 Socket 介面：連線兩端的 file descriptor

**Socket** 是 kernel 提供給程式的網路通訊端點。從 Linux 程式的角度看，socket 就是一個 file descriptor（第 27 章）：建立好連線之後，可以用 `read` 和 `write` 收送資料，用 `close` 關閉。這是 Unix「一切都是檔案」設計的延伸，也是為什麼第 27 章的 short count 處理在這裡完全適用。

差別在於建立連線的過程。client 與 server 要各自呼叫一串函式，才能讓兩個 socket 連起來：

```text
        client                                       server
                                              getaddrinfo（找出要 bind 的位址）
                                                      │
                                                   socket()
                                                      │
                                                    bind()      ← 綁定本機位址與 port
                                                      │
                                                   listen()     ← 變成 listening socket
                                                      │
 getaddrinfo（查 server 的位址）                   accept()     ← 等待連線（阻塞）
        │                                             │
     socket()                                         │
        │          TCP 三次握手（kernel 完成）        │
    connect() ─────── SYN ──────────────────────▶     │
        │     ◀────── SYN+ACK ──────────────────      │
        │     ──────── ACK ─────────────────────▶     │
        │                                     accept 回傳 connected socket
        ▼                                             ▼
  write / read ◀════════ 雙向 byte stream ═══════▶ read / write
        │                                             │
     close()   ────────── FIN ──────────────▶   read 回傳 0（EOF）
                                                   close()
                                              回到 accept 等下一個
```

逐一看每個函式：

- **`socket(domain, type, protocol)`**：建立一個 socket，回傳 descriptor。`AF_INET`／`AF_INET6` 選位址家族，`SOCK_STREAM` 表示 TCP，`SOCK_DGRAM` 表示 UDP。剛建立的 socket 還沒有位址、也沒有連到任何地方，只是一個「半成品」。
- **`connect(fd, addr, len)`**（client）：要求 kernel 和 `addr` 建立連線。kernel 會替這個 socket 挑一個 ephemeral port，送出 SYN，完成 **三次握手**（three-way handshake）後才回傳 0。如果對方主機在、但那個 port 沒有程式在 listen，對方會回一個 RST，`connect` 回傳 −1、`errno` 是 `ECONNREFUSED`；如果封包被防火牆丟掉，`connect` 會等到逾時。
- **`bind(fd, addr, len)`**（server）：把 socket 綁定到本機的某個位址與 port，告訴 kernel「送到這個位址：port 的連線請求交給我」。
- **`listen(fd, backlog)`**（server）：把 socket 從「主動去連別人」的預設狀態，轉成「被動等人連」的 **listening socket**。`backlog` 是 kernel 替你排隊的已完成連線數上限的提示，28.9 節細談。
- **`accept(listenfd, addr, len)`**（server）：從排隊的連線中取出一條，回傳一個**新的** descriptor，叫 **connected socket**；同時把 client 的位址填進 `addr`。如果沒有排隊的連線，`accept` 會阻塞等待。

> [!warning] 常見誤解
> 「server 用 listening socket 和 client 通訊。」不是。listening socket 只負責接收新的連線請求，它在 server 的整個生命週期都存在；每次 `accept` 會產生一個新的 connected socket，專門用來和那一個 client 交換資料，服務結束就關掉。把兩者分開，server 才能一邊服務現有的 client、一邊接受新連線（第 30 章的並行 server 就靠這點）。

### Socket 位址結構

這些函式都接受 `struct sockaddr *` 型別的位址參數。這是 C 在還沒有 `void *` 的年代做出的「泛型」：各種位址家族有各自的結構，呼叫時一律轉型成 `struct sockaddr *`，kernel 再看結構開頭的 family 欄位決定怎麼解讀。

```text
 struct sockaddr_in（IPv4，16 bytes）       struct sockaddr_in6（IPv6，28 bytes）
 ┌──────────────────────────────┐          ┌──────────────────────────────┐
 │ sin_family  = AF_INET        │          │ sin6_family = AF_INET6       │
 │ sin_port    （network order）│          │ sin6_port   （network order）│
 │ sin_addr    （4 bytes）      │          │ sin6_flowinfo                │
 │ sin_zero[8] （填 0）         │          │ sin6_addr   （16 bytes）     │
 └──────────────────────────────┘          │ sin6_scope_id                │
                                           └──────────────────────────────┘
 struct sockaddr_storage：夠大、對齊夠嚴，能裝下任何一種位址
                          → accept 時不知道對方是 IPv4 還是 IPv6，就用它
```

（macOS 等 BSD 系統的結構開頭還多一個長度欄位，但只要用 `getaddrinfo` 填位址，就不必在意這種差異。）程式裡手動填 `sockaddr_in` 是很多舊範例的寫法，但它把程式綁死在 IPv4。下一節的 `getaddrinfo` 會替我們填好正確的結構。

## 28.6 getaddrinfo：把名稱變成可以連線的位址

**`getaddrinfo`** 是現代網路程式的入口。它接受一個主機（名稱或位址字串）和一個服務（port 號或服務名稱），回傳一串可以直接交給 `socket`、`connect`、`bind` 的位址結構：

```c
#include <netdb.h>
int getaddrinfo(const char *host, const char *service,
                const struct addrinfo *hints, struct addrinfo **result);
void freeaddrinfo(struct addrinfo *result);
const char *gai_strerror(int errcode);
```

回傳值 0 表示成功，非 0 是錯誤碼，要用 `gai_strerror` 而不是 `strerror` 轉成文字（這是新手很常寫錯的地方，因為它不設定 `errno`）。結果是一條 linked list：

```text
 result
   │
   ▼
 ┌─────────────────┐     ┌─────────────────┐
 │ struct addrinfo │     │ struct addrinfo │
 │ ai_family=INET6 │     │ ai_family=INET  │
 │ ai_socktype     │     │ ai_socktype     │
 │ ai_protocol     │     │ ai_protocol     │
 │ ai_addrlen      │     │ ai_addrlen      │
 │ ai_addr ──────────▶ sockaddr_in6 [::1]:8080
 │ ai_next ────────────▶ ai_addr ──────────▶ sockaddr_in 127.0.0.1:8080
 └─────────────────┘     │ ai_next = NULL  │
                         └─────────────────┘
```

每個節點裡的 `ai_family`、`ai_socktype`、`ai_protocol` 剛好是 `socket()` 的三個參數，`ai_addr` 與 `ai_addrlen` 剛好是 `connect()`／`bind()` 的後兩個參數。所以標準用法就是「走訪 list，一個一個試，成功就停」。

`hints` 用來限縮結果，常用的欄位與旗標：

| 設定 | 效果 | 什麼時候用 |
|---|---|---|
| `ai_family = AF_UNSPEC` | IPv4、IPv6 都要 | 預設選擇，讓程式不綁定版本 |
| `ai_family = AF_INET` | 只要 IPv4 | 明確只支援 IPv4 時 |
| `ai_socktype = SOCK_STREAM` | 只要 TCP | 幾乎總是要設，否則同一個位址會因為 TCP、UDP 等不同 socket type 重複出現 |
| `AI_PASSIVE` | host 為 NULL 時回傳「所有介面」的位址（`0.0.0.0`／`::`） | server 準備 `bind` 時 |
| `AI_NUMERICSERV` | service 一定是數字 port，不去查服務名稱表 | 設定檔給的是 port 號時 |
| `AI_ADDRCONFIG` | 本機有設定 IPv4 位址才回傳 IPv4、有 IPv6 才回傳 IPv6 | client 避免嘗試本機根本不能用的位址家族 |

反方向的函式是 **`getnameinfo`**：給它一個 socket 位址結構，它把主機與 port 轉回字串；加上 `NI_NUMERICHOST | NI_NUMERICSERV` 就只轉成數字形式，不做反向 DNS 查詢。server 記錄「client 從哪裡來」時用它，而且通常要加 `NI_NUMERICHOST`，否則每條連線都觸發一次 DNS 查詢，會讓 server 莫名變慢。

`getaddrinfo` 還有一個常被忽略的特性：查 DNS 名稱時它是**阻塞**的，而且可能花上好幾秒（DNS server 沒回應時要等逾時）。在事件驅動的 server 裡直接呼叫它，會卡住整個 event loop。這是為什麼 nginx 這類程式有自己的非同步 DNS resolver。

## 28.7 open_clientfd 與 open_listenfd：把樣板包起來

建立 client 與 server socket 的步驟每次都一樣，CS:APP 把它們包成兩個輔助函式：**`open_clientfd(host, port)`** 回傳一個已經連上 server 的 descriptor；**`open_listenfd(port)`** 回傳一個已經在 listen 的 descriptor。概念如下：

```text
 open_clientfd(host, port)                 open_listenfd(port)
 ─────────────────────────                 ───────────────────
 getaddrinfo(host, port,                   getaddrinfo(NULL, port,
   SOCK_STREAM,                              SOCK_STREAM,
   AI_NUMERICSERV|AI_ADDRCONFIG)             AI_PASSIVE|AI_ADDRCONFIG|AI_NUMERICSERV)
 for 每個候選位址 p:                         for 每個候選位址 p:
   fd = socket(p 的三個參數)                   fd = socket(p 的三個參數)
   if connect(fd, p) 成功 → 跳出               setsockopt(SO_REUSEADDR)
   close(fd)，試下一個                         if bind(fd, p) 成功 → 跳出
 freeaddrinfo                                  close(fd)，試下一個
 回傳 fd（全部失敗回傳 −1）                 freeaddrinfo
                                            listen(fd, backlog)
                                            回傳 fd
```

兩個細節值得注意。第一，**失敗時要 `close` 再試下一個**：一個 `connect` 失敗的 socket 狀態是不確定的，不能拿來重試，而且不關會洩漏 descriptor。第二，server 在 `bind` 之前設定 `SO_REUSEADDR`，這正是 28.1 節 `Address already in use` 的解法，28.9 節會解釋原因。本章的範例程式會寫出自己的簡化版本，形狀和這個流程一樣。

## 28.8 TCP 是 byte stream：訊息邊界要自己定

回到 28.1 節的第一個問題。server 一次 `write` 送出一段 4 KB 的 JSON，client 一次 `read` 為什麼只拿到一半？

因為 **TCP 不記得你呼叫了幾次 `write`**。`write` 只是把 bytes 複製到 kernel 的 send buffer；kernel 依照網路狀況、對方的接收窗口與 **MSS**（maximum segment size，每個 TCP segment 能攜帶的最大 payload）把它們切成 segment 送出。接收端的 kernel 把收到的 bytes 依序放進 receive buffer，`read` 被呼叫時，**有多少就先給多少**，不會等湊滿你要求的大小，也不知道哪幾個 bytes 原本是同一次 `write`。

### 手算：一張縮圖要幾個 segment

假設網路是一般 Ethernet，MTU（一個 frame 能攜帶的最大 IP packet）是 1500 bytes，IPv4 header 與 TCP header 沒有額外選項時各 20 bytes：

```text
MSS = MTU − IP header − TCP header
    = 1500 − 20 − 20 = 1460 bytes

200 KiB 的縮圖 = 204,800 bytes
segment 數 = ⌈204,800 ÷ 1460⌉ = ⌈140.27⌉ = 141 個
            （前 140 個各 1460 bytes，最後一個 204,800 − 140 × 1460 = 400 bytes）
```

實際上 TCP header 常帶 timestamp 等選項，segment 會小一點；loopback 介面的 MTU 也大得多（例如 Linux 上常見 65536），所以本機測試時資料幾乎總是「一次就到」。這正是小安的程式在筆電上永遠正常、到了真實網路才出錯的原因：**在 loopback 上測不出 short read**。

接收端的 `read` 可能看到任何一種切法：

| 送出端做了什麼 | 接收端的 `read` 可能看到 | 原因 |
|---|---|---|
| 一次 `write` 4 KB | 先 1460、再 2636；或 1460、1460、1176 | 資料分成多個 segment 陸續到達 |
| 兩次 `write`：`"STATS\n"`、`"PING\n"` | 一次讀到 `"STATS\nPING\n"` | 兩次寫入在 receive buffer 裡合在一起 |
| 一次 `write` `"hello\n"` | 先 `"hel"`、再 `"lo\n"` | 送出端或網路中途被拆開 |
| 對方 `close` | `read` 回傳 0 | EOF：對方不會再送資料了 |
| 連線被重設 | `read` 回傳 −1，`errno` 為 `ECONNRESET` | 對方 crash 或送出 RST |

### Framing：在 byte stream 上切出訊息

既然 TCP 不保留邊界，應用程式的協定就要自己定義「一則訊息到哪裡結束」，這叫 **framing**（訊框化）。常見做法有三種：

1. **分隔符號**：每則訊息以特定字元結束，例如換行。HTTP 的 header、SMTP、Redis 的部分協定都是這樣。接收端要持續累積 bytes，直到看到分隔符號；也要限制一行的最大長度，否則惡意的 client 可以送一個永不結束的行把記憶體塞滿。
2. **長度前綴**：先送一個固定大小的長度欄位（例如 4 bytes、network byte order），再送那麼多 bytes 的內容。gRPC（建立在 HTTP/2 上）、資料庫協定常用這種方式。接收端先讀滿 4 bytes，**先檢查長度是否合理**再配置緩衝區，否則一個 `0xFFFFFFFF` 就能讓 server 嘗試配置 4 GB（第 5 章的整數溢位問題也常出現在這裡）。
3. **一條連線只送一則訊息**：送完就關閉寫入方向，接收端讀到 EOF 就知道結束了。HTTP/1.0 預設就是這樣（第 29 章）。

小安的修法因此很明確：client 不能「讀一次就當作完整」，而要在迴圈裡持續讀到 framing 規則說訊息結束為止。管理 port 的協定改成「`thumbd` 回應完就關閉連線」，client 讀到 EOF 才把累積的資料交給 JSON parser。這和第 27 章處理 short count 的 `rio_readn` 是同一個道理，只是在網路上，short count 從「偶爾」變成「家常便飯」。

## 28.9 連線的生命週期：backlog、關閉與 TIME_WAIT

### 握手與 backlog

`connect` 回傳成功時，server 程式可能還沒呼叫 `accept`。三次握手完全由 kernel 處理：server 的 kernel 收到 SYN，回覆 SYN+ACK，收到最後的 ACK 後，把這條**已完成的連線**放進 listening socket 的 **accept queue**（接受佇列），等程式來 `accept` 取走。`listen` 的 `backlog` 參數就是這個佇列長度的上限（kernel 可能再調整它）。

```text
 client ──SYN──▶ ┌──────────────────────────┐
        ◀SYN+ACK │ server kernel            │
        ──ACK──▶ │  半完成連線（SYN 已收到） │
                 │        │ 握手完成          │
                 │        ▼                   │
                 │  accept queue  [c1][c2][c3]│ ← 長度上限 ≈ backlog
                 └────────┬──────────────────┘
                          │ accept() 取出一條
                          ▼
                   server 程式（可能正忙著處理別的請求）
```

佇列滿了會怎樣？POSIX 只說 client 可能收到 `ECONNREFUSED`，或者請求被忽略、讓之後的重送成功，細節依平台而定。Linux 在預設設定（`net.ipv4.tcp_abort_on_overflow = 0`）下不回 RST，而是直接丟掉封包：新的 SYN 被丟掉時，client 的 kernel 過約 1 秒、再 2 秒、再 4 秒……重送 SYN，client 看到的是 `connect` 變慢；如果被丟掉的是握手最後的 ACK，client 端以為已經連上了，server 端則稍後重送 SYN+ACK，等佇列有空位才真正完成。所以 server 處理得太慢時，症狀往往不是「連不上」，而是「連線要好幾秒才建立」或「連上了卻等不到回應」。Linux 上 `backlog` 還會被 `net.core.somaxconn` 默默截斷，它的預設值從 kernel 5.4 起是 4096（更舊的版本是 128）；還沒完成握手的連線則另有 `net.ipv4.tcp_max_syn_backlog` 限制。

backlog 不是效能旋鈕。把它調大只能吸收短暫的尖峰；如果 server 的處理速度長期跟不上請求速度，佇列再長也會滿，只是讓每個請求等得更久。真正的解法是第 30 章的並行模型，以及在過載時主動拒絕（回 503）而不是無限排隊。

### 關閉連線：EOF、半關閉與 RST

TCP 連線是雙向的，兩個方向可以分別關閉。一端呼叫 `close`（或 `shutdown(fd, SHUT_WR)`）時，kernel 把 send buffer 剩下的資料送完，再送一個 **FIN**；對方的 `read` 在讀完所有資料後回傳 0，這就是網路上的 EOF。`shutdown(fd, SHUT_WR)` 的特別之處是只關閉「我這邊的寫入」，仍然可以繼續讀對方的回應，這叫 **半關閉**（half-close），本章範例的 client 就用它通知 server「請求送完了」。

如果連線被**異常**中止，送出的是 **RST**（reset）而不是 FIN。常見原因有：連到沒有程式 listen 的 port；process crash 或被殺掉；程式在 receive buffer 裡還有沒讀的資料時就 `close`。最後一種在 Linux 上會讓 kernel 送 RST，對方可能因此丟失還沒讀到的回應，第 29 章的 web server 會遇到這個問題。

對一個已經被對方關閉的連線繼續 `write`，kernel 會對 process 送出 **SIGPIPE**（精確地說：對方關閉後的第一次 `write` 通常還會成功，但對方的 kernel 會回 RST；之後再寫才觸發 SIGPIPE），預設動作是終止 process（第 22 章）。網路 server 幾乎都要在啟動時 `signal(SIGPIPE, SIG_IGN)` 忽略它，改成讓 `write` 回傳 −1、`errno` 為 `EPIPE`，再由程式關閉這條連線。否則一個中途斷線的 client 就能讓整個 `thumbd` 結束。

### TIME_WAIT 與 Address already in use

主動關閉連線的那一端，在送完最後的 ACK 之後不會立刻把連線忘掉，而是進入 **TIME_WAIT** 狀態，停留一段時間（理論上是 2×MSL，maximum segment lifetime；Linux 固定是 60 秒，其他系統依平台而定）。原因有兩個：如果最後的 ACK 遺失，對方會重送 FIN，這一端還要能回應；也要確保網路上殘留的舊封包過期，不會被誤認成之後用同一組四元組建立的新連線。

```text
 主動關閉的一端                         被動關閉的一端
   ESTABLISHED                           ESTABLISHED
       │ close() ──── FIN ───────────▶        │
   FIN_WAIT_1   ◀──── ACK ────────────   CLOSE_WAIT  ← 程式還沒 close
   FIN_WAIT_2                                 │ close()
       │       ◀──── FIN ────────────     LAST_ACK
   TIME_WAIT   ──── ACK ─────────────▶    CLOSED
       │ 等待 2×MSL（Linux：60 秒）
   CLOSED
```

這張圖解釋了 28.1 節的第二個問題。`thumbd` 重啟時，舊 process 主動關閉了它的連線，那些連線在 kernel 裡停在 TIME_WAIT，它們的本機位址正是 `thumbd` 的 port。新 process 呼叫 `bind` 時，kernel 預設拒絕綁定一個「還有連線殘留」的位址，於是回傳 `EADDRINUSE`。等 TIME_WAIT 結束（大約一分鐘），`bind` 就成功了，和阿哲觀察到的一致。

解法是在 `bind` 之前設定 **`SO_REUSEADDR`**：它允許綁定一個仍有 TIME_WAIT 連線的位址。在 Linux 上它**不會**讓兩個 process 同時 listen 同一個 port（那是另一個選項 `SO_REUSEPORT`，語意依平台而定），所以幾乎所有 server 都應該設定它。`socket(7)` 還提到一個 Linux 特有的細節：先前綁定這個 port 的程式與新的程式**都**設了 `SO_REUSEADDR`，重用才會被允許（FreeBSD 只要求後者），所以修正版要部署過一輪之後，下一次重啟才完全不受影響。另外，圖中的 **CLOSE_WAIT** 也值得記住：它表示「對方已經關閉，但我方程式還沒呼叫 `close`」。如果 `ss` 顯示大量 CLOSE_WAIT 而且一直不減少，幾乎可以確定是程式漏了 `close`，這是 descriptor 洩漏。

## 28.10 動手做：同一支程式裡的 client 與 server

下面三段程式都在一個 process（或 `fork` 出來的父子行程）內完成 client 與 server 的互動，使用 loopback，幾秒內自己結束，不需要另外開終端機。三段都在 macOS arm64（Apple clang 21.0.0）上以 `cc -std=c17 -O1 -Wall -Wextra` 編譯執行；開頭的 `#define _DEFAULT_SOURCE` 是為了讓同一份程式在 Linux（glibc）的 `-std=c17` 下也能看到 `struct addrinfo`、`usleep` 等宣告。

### 程式一：getaddrinfo 給了什麼

```c
#define _DEFAULT_SOURCE   /* Linux 的 -std=c17 預設隱藏 POSIX 與 BSD 宣告（getaddrinfo、usleep）；macOS 忽略它 */
#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>

/* 列出 getaddrinfo 對 (host, service) 給出的每一個候選位址。 */
static void show(const char *host, const char *service) {
    struct addrinfo hints, *list, *p;
    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;          /* IPv4 與 IPv6 都要 */
    hints.ai_socktype = SOCK_STREAM;      /* 只要 TCP，避免同一位址重複出現三次 */
    hints.ai_flags = AI_NUMERICSERV;      /* service 是數字 port，不查服務名稱表 */
    int rc = getaddrinfo(host, service, &hints, &list);
    if (rc != 0) {
        printf("%s:%s → 錯誤：%s\n", host, service, gai_strerror(rc));
        return;
    }
    for (p = list; p != NULL; p = p->ai_next) {
        char ip[INET6_ADDRSTRLEN];
        unsigned short port_net;
        if (p->ai_family == AF_INET) {
            struct sockaddr_in *a = (struct sockaddr_in *)p->ai_addr;
            inet_ntop(AF_INET, &a->sin_addr, ip, sizeof ip);
            port_net = a->sin_port;
        } else {
            struct sockaddr_in6 *a = (struct sockaddr_in6 *)p->ai_addr;
            inet_ntop(AF_INET6, &a->sin6_addr, ip, sizeof ip);
            port_net = a->sin6_port;
        }
        unsigned char *b = (unsigned char *)&port_net;   /* 看 port 在記憶體裡的兩個 byte */
        printf("%s:%s → %-5s %-15s port %u（記憶體中 %02x %02x）\n", host, service,
               p->ai_family == AF_INET ? "IPv4" : "IPv6", ip, ntohs(port_net), b[0], b[1]);
    }
    freeaddrinfo(list);
}

int main(void) {
    show("localhost", "8080");
    show("127.0.0.1", "443");
    show("::1", "8080");
    show("no-such-host.invalid", "80");
    return 0;
}
```

在 macOS arm64（Apple clang 21）上執行：

```text
localhost:8080 → IPv6  ::1             port 8080（記憶體中 1f 90）
localhost:8080 → IPv4  127.0.0.1       port 8080（記憶體中 1f 90）
127.0.0.1:443 → IPv4  127.0.0.1       port 443（記憶體中 01 bb）
::1:8080 → IPv6  ::1             port 8080（記憶體中 1f 90）
no-such-host.invalid:80 → 錯誤：nodename nor servname provided, or not known
```

逐行看：

1. `localhost` 有兩個候選位址，而且 **IPv6 的 `::1` 排在前面**。這就是 28.4 節的坑：只 bind `127.0.0.1` 的 server，會讓「只試第一個位址」的 client 連線失敗。
2. port 8080 在記憶體中是 `1f 90`，443 是 `01 bb`（443 = 0x01BB），和手算一致：`sin_port` 存的是 network byte order，印成數字之前必須 `ntohs`。如果直接印 `port_net`，在 little endian 機器上會看到 `0x901F` = 36895，這是很常見的 bug。
3. 給數字形式的位址（`127.0.0.1`、`::1`）時，`getaddrinfo` 不查 DNS，直接解析成結構，所以同一套程式碼可以處理名稱與位址。
4. 查不到的名稱回傳錯誤碼，訊息文字依平台而定（Linux glibc 通常是 `Name or service not known`）。`.invalid` 是保留給「保證不存在」的網域，適合用來測試錯誤處理。

### 程式二：echo server 與 client，觀察 byte stream

這段程式先建立 listening socket（port 傳 `"0"` 讓 kernel 挑一個空閒的 port，避免和機器上其他程式衝突），然後 `fork`：子行程當 client，父行程當 **echo server**（把收到的資料原樣送回）。client 故意把一則訊息分兩次送，再把兩則訊息合成一次送。

```c
#define _DEFAULT_SOURCE   /* Linux 的 -std=c17 預設隱藏 POSIX 與 BSD 宣告（getaddrinfo、usleep）；macOS 忽略它 */
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

/* 建立 listening socket；port 傳 "0" 代表讓 kernel 挑一個空閒的 port。 */
static int open_listenfd(const char *port) {
    struct addrinfo hints = {0}, *list, *p;
    int fd = -1, one = 1;
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_NUMERICSERV;
    /* 只 bind loopback；要接受所有介面的連線，host 改傳 NULL 並加上 AI_PASSIVE */
    if (getaddrinfo("127.0.0.1", port, &hints, &list) != 0) return -1;
    for (p = list; p; p = p->ai_next) {
        if ((fd = socket(p->ai_family, p->ai_socktype, p->ai_protocol)) < 0) continue;
        setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
        if (bind(fd, p->ai_addr, p->ai_addrlen) == 0 && listen(fd, 16) == 0) break;
        close(fd);
        fd = -1;
    }
    freeaddrinfo(list);
    return fd;
}

static int open_clientfd(const char *host, const char *port) {
    struct addrinfo hints = {0}, *list, *p;
    int fd = -1;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_NUMERICSERV;
    if (getaddrinfo(host, port, &hints, &list) != 0) return -1;
    for (p = list; p; p = p->ai_next) {              /* 逐一嘗試每個候選位址 */
        if ((fd = socket(p->ai_family, p->ai_socktype, p->ai_protocol)) < 0) continue;
        if (connect(fd, p->ai_addr, p->ai_addrlen) == 0) break;
        close(fd);
        fd = -1;
    }
    freeaddrinfo(list);
    return fd;
}

/* 寫滿 n 個 bytes 才回傳；write 可能只寫一部分（short count，第 27 章）。 */
static int writen(int fd, const char *p, size_t n) {
    while (n > 0) {
        ssize_t k = write(fd, p, n);
        if (k <= 0) return -1;
        p += k;
        n -= (size_t)k;
    }
    return 0;
}

int main(void) {
    int listenfd = open_listenfd("0");
    struct sockaddr_storage local;
    socklen_t len = sizeof local;
    char host[64], port[16];
    getsockname(listenfd, (struct sockaddr *)&local, &len);
    getnameinfo((struct sockaddr *)&local, len, host, sizeof host, port, sizeof port,
                NI_NUMERICHOST | NI_NUMERICSERV);
    printf("server 在 %s:%s 等待連線\n", host, port);
    fflush(stdout);                                  /* fork 前清空，避免輸出被印兩次 */

    if (fork() == 0) {                               /* 子程序：client */
        close(listenfd);
        int fd = open_clientfd("127.0.0.1", port);
        writen(fd, "hel", 3);                        /* 一則訊息分兩次送 */
        usleep(100 * 1000);
        writen(fd, "lo\n", 3);
        usleep(100 * 1000);
        writen(fd, "ping\npong\n", 10);              /* 兩則訊息一次送 */
        shutdown(fd, SHUT_WR);                       /* 告訴 server：我不會再送了 */
        char buf[64];
        ssize_t n, total = 0;
        while ((n = read(fd, buf, sizeof buf)) > 0) total += n;
        printf("[client] 收回 %zd bytes 的回聲\n", total);
        fflush(stdout);                              /* _exit 不會替我們清空 stdio buffer */
        close(fd);
        _exit(0);
    }

    struct sockaddr_storage peer;                    /* 父程序：iterative echo server */
    socklen_t plen = sizeof peer;
    int connfd = accept(listenfd, (struct sockaddr *)&peer, &plen);
    getnameinfo((struct sockaddr *)&peer, plen, host, sizeof host, port, sizeof port,
                NI_NUMERICHOST | NI_NUMERICSERV);
    printf("[server] accept：client 來自 %s:%s\n", host, port);
    char buf[64], line[256];
    size_t used = 0;                                 /* line[] 裡累積、還沒切出的 bytes */
    ssize_t n;
    int calls = 0;
    while ((n = read(connfd, buf, sizeof buf)) > 0) {
        printf("[server] read #%d 回傳 %zd bytes\n", ++calls, n);
        writen(connfd, buf, (size_t)n);              /* echo：原樣送回 */
        for (ssize_t i = 0; i < n && used < sizeof line - 1; i++) {
            line[used++] = buf[i];
            if (buf[i] == '\n') {                    /* framing：遇到換行才算一則訊息 */
                line[used - 1] = '\0';
                printf("[server]   完整訊息：\"%s\"\n", line);
                used = 0;
            }
        }
    }
    printf("[server] read 回傳 0：client 關閉了寫入方向（EOF）\n");
    fflush(stdout);
    close(connfd);
    wait(NULL);
    close(listenfd);
    return 0;
}
```

在 macOS arm64 上執行（port 號每次不同）：

```text
server 在 127.0.0.1:54665 等待連線
[server] accept：client 來自 127.0.0.1:54666
[server] read #1 回傳 3 bytes
[server] read #2 回傳 3 bytes
[server]   完整訊息："hello"
[server] read #3 回傳 10 bytes
[server]   完整訊息："ping"
[server]   完整訊息："pong"
[server] read 回傳 0：client 關閉了寫入方向（EOF）
[client] 收回 16 bytes 的回聲
```

逐段解說：

1. **port 0 與 `getsockname`**：`bind` 到 port 0 時 kernel 會挑一個空閒的 port，程式再用 `getsockname` 查出實際是哪一個。測試程式用這招可以避免「port 被佔用」的隨機失敗。client 的 port（54666）是 kernel 在 `connect` 時挑的 ephemeral port，落在 macOS 的 49152–65535 範圍內。
2. **`read` 的次數和 `write` 的次數沒有對應關係**：`"hello\n"` 這一則訊息花了兩次 `read`（因為 client 中間睡了 100 ms，資料分兩批到）；`"ping\npong\n"` 兩則訊息只花了一次 `read`。這裡用 `usleep` 是為了讓現象穩定出現；在真實網路上，不需要任何 sleep，延遲、封包切割與重送就會自然造成同樣的效果。
3. **framing 讓訊息重新出現**：server 不管 `read` 怎麼切，都把 bytes 累積到 `line[]`，看到換行才印出「完整訊息」。三則訊息都被正確還原，這就是 28.8 節分隔符號 framing 的最小實作。
4. **EOF 與半關閉**：client 呼叫 `shutdown(fd, SHUT_WR)` 後，server 的 `read` 回傳 0，跳出迴圈；但 client 自己仍然能繼續讀，最後收回全部 16 bytes 的回聲。如果 client 改成直接 `close`，就收不到回聲了。
5. **`writen`**：每一次寫入都經過迴圈，處理 `write` 寫不完的情況。對 socket 來說，send buffer 滿時 `write` 可能只寫一部分（例如 socket 是 nonblocking，或 blocking 寫入被 signal 中斷），所以這個迴圈不能省。

### 程式三：還沒 accept，connect 就成功了

```c
#define _DEFAULT_SOURCE   /* Linux 的 -std=c17 預設隱藏 POSIX 與 BSD 宣告（getaddrinfo、usleep）；macOS 忽略它 */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

/* 不呼叫 accept，看看 client 的 connect 會不會成功。全部在同一個 process 內完成。 */
int main(void) {
    int lfd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);   /* 127.0.0.1，轉成 network byte order */
    addr.sin_port = htons(0);                        /* 0：讓 kernel 挑 port */
    if (bind(lfd, (struct sockaddr *)&addr, sizeof addr) < 0) { perror("bind"); return 1; }
    listen(lfd, 8);
    socklen_t len = sizeof addr;
    getsockname(lfd, (struct sockaddr *)&addr, &len);
    printf("listening on 127.0.0.1:%u（還沒呼叫 accept）\n", ntohs(addr.sin_port));

    int cfd[3];
    for (int i = 0; i < 3; i++) {
        cfd[i] = socket(AF_INET, SOCK_STREAM, 0);
        int rc = connect(cfd[i], (struct sockaddr *)&addr, sizeof addr);
        char msg[32];
        int m = snprintf(msg, sizeof msg, "req-%d\n", i);
        ssize_t w = write(cfd[i], msg, (size_t)m);   /* 連 server 都還沒 accept，就能寫 */
        printf("client %d：connect 回傳 %d，write 回傳 %zd\n", i, rc, w);
    }
    for (int i = 0; i < 3; i++) {                    /* 現在才從 accept queue 取出連線 */
        int fd = accept(lfd, NULL, NULL);
        char buf[32];
        ssize_t n = read(fd, buf, sizeof buf - 1);
        buf[n > 0 ? n : 0] = '\0';
        printf("accept 第 %d 條連線，讀到 %zd bytes：%s", i, n, buf);
        close(fd);
        close(cfd[i]);
    }
    close(lfd);
    return 0;
}
```

在 macOS arm64 上執行：

```text
listening on 127.0.0.1:51538（還沒呼叫 accept）
client 0：connect 回傳 0，write 回傳 6
client 1：connect 回傳 0，write 回傳 6
client 2：connect 回傳 0，write 回傳 6
accept 第 0 條連線，讀到 6 bytes：req-0
accept 第 1 條連線，讀到 6 bytes：req-1
accept 第 2 條連線，讀到 6 bytes：req-2
```

這支程式只有一個 process、一個 thread，卻能讓三個 `connect` 都成功，因為握手是 kernel 完成的，不需要 server 程式參與。三條連線排在 accept queue 裡，client 寫入的資料也已經躺在各自的 receive buffer 裡。之後 `accept` 依建立順序取出它們，資料一個 byte 都沒少。

這對工作上的判斷很重要：**「connect 成功」只代表 kernel 接受了連線，不代表 server 程式正在處理你。** 一個卡住的 server，client 看起來依然「連得上」，只是送出請求後一直等不到回應。這就是為什麼健康檢查應該送一個真正的請求並檢查回應內容，而不是只檢查 port 能不能連。

## 28.11 IPv4 與 IPv6 並存

現在的網路是 **dual-stack**（雙堆疊）的：同一台機器同時有 IPv4 與 IPv6 位址，名稱查詢可能同時回傳兩種。對程式的影響整理如下：

- **client**：用 `getaddrinfo` 加 `AF_UNSPEC`，依序嘗試每個位址。對延遲敏感的 client（例如瀏覽器）會用「Happy Eyeballs」的做法：同時或交錯嘗試 IPv6 與 IPv4，哪個先連上就用哪個，避免某一種網路壞掉時要等完整個逾時。
- **server**：有兩種常見做法。一是開兩個 listening socket，分別 bind `0.0.0.0` 與 `::`；二是只開一個 IPv6 socket bind `::`，並關閉 `IPV6_V6ONLY` 選項，讓 IPv4 client 以「IPv4-mapped IPv6 位址」（例如 `::ffff:10.0.3.17`）的形式連進來。第二種的預設行為依平台而定（Linux 由 `net.ipv6.bindv6only` 決定，預設允許），所以要明確設定。
- **記錄與比對位址**：log 裡同一個 client 可能出現 `10.0.3.17` 或 `::ffff:10.0.3.17` 兩種寫法，做 IP allowlist 或 rate limit 時要先正規化。
- **存位址的欄位**：資料庫或 struct 裡放 IP 的欄位要能放得下 IPv6 的文字形式（`INET6_ADDRSTRLEN` 是 46，含結尾的 `\0`）。

`thumbd` 的管理 port 原本寫死 `sockaddr_in`、bind `127.0.0.1`。小安改用 `getaddrinfo` 之後，同一份程式碼在只有 IPv6 的測試環境裡也能直接運作，這是改寫中最不起眼、但最省事的收穫。

## 28.12 在工作上怎麼用

### 用 ss 看連線狀態

Linux 上 `ss`（socket statistics）是 `netstat` 的現代替代品。幾個最常用的指令：

```bash
ss -ltnp                       # 所有 TCP listening socket（l），數字顯示（n），附 process（p，需權限）
ss -tn state established '( sport = :9100 )'   # 連到 thumbd 管理 port 的連線
ss -tan state time-wait | wc -l                # TIME_WAIT 的數量
ss -tan state close-wait                       # CLOSE_WAIT：對方關了、我方還沒 close
ss -s                                          # 各狀態的總數摘要
```

`ss -ltn` 對 listening socket 顯示的 `Recv-Q` 是目前 accept queue 裡等待的連線數，`Send-Q` 是 backlog 上限。示意輸出：

```text
State   Recv-Q  Send-Q  Local Address:Port   Peer Address:Port
LISTEN  0       4096          0.0.0.0:8080        0.0.0.0:*
LISTEN  129     128         127.0.0.1:9100        0.0.0.0:*
```

第二行的 `Recv-Q` 129 比上限 128 還多 1，這在 Linux 上就代表 accept queue 已經滿了（Linux 的判斷是「超過 backlog」才算滿，所以最多能排 backlog + 1 條）：程式 `accept` 得太慢，新連線正在被丟棄或延遲。這時要查的是 server 為什麼沒在 `accept`（卡在某個請求、thread 全部忙碌），而不是先調大 backlog。

### 連線問題的判斷流程

```text
症狀：client 連不上或請求卡住
  │
  ├─ connect 立刻失敗，ECONNREFUSED
  │    └─ 對方主機在，但那個 IP:port 沒有程式 listen
  │       → ss -ltn 確認 server bind 的位址（127.0.0.1？0.0.0.0？::？）與 port
  │       → 注意 localhost 是否被解析成 ::1
  │
  ├─ connect 等很久才逾時（ETIMEDOUT）
  │    └─ 封包被丟掉：防火牆、security group、路由問題，或 accept queue 滿了
  │       → tcpdump 看 SYN 有沒有出去、有沒有回應
  │
  ├─ connect 成功，但送出請求後沒有回應
  │    └─ server 程式卡住或很忙；或雙方都在等對方先送（協定 framing 不一致）
  │       → server 端 ss 看 Recv-Q 是否堆積；strace -p 看它卡在哪個 system call
  │
  └─ 回應只收到一部分或格式錯
       └─ client 假設一次 read 就是完整訊息
          → 檢查讀取迴圈與 framing
```

### 用 nc 與 tcpdump 動手觀察

**`nc`**（netcat）可以當作萬用的 client 或 server，用來確認「是程式的問題還是網路的問題」：

```bash
nc -v 10.0.1.5 9100            # 手動連到 thumbd 管理 port，輸入 STATS 後按 Enter
printf 'STATS\n' | nc 10.0.1.5 9100    # 用腳本送一個請求
nc -l 9100                     # 在本機開一個臨時 server，看 client 實際送了什麼（選項依版本不同）
```

**`tcpdump`** 直接看封包，是判斷「封包有沒有到」的終極工具：

```bash
sudo tcpdump -i any -nn 'tcp port 9100'         # 看握手、資料與 FIN／RST
sudo tcpdump -i any -nn 'tcp[tcpflags] & tcp-rst != 0'   # 只看 RST
```

看到 `Flags [S]` 是 SYN、`[S.]` 是 SYN+ACK、`[F.]` 是 FIN、`[R]` 是 RST。小安用 tcpdump 看監控程式的連線時，清楚看到 `thumbd` 的 JSON 回應被分成好幾個 segment 送出，這是說服自己「TCP 真的不保留邊界」最直接的證據。

### 高流量下的 TIME_WAIT 與 port 耗盡

TIME_WAIT 本身不是錯誤，但在「每個請求都開新連線」的架構裡會大量累積。一個常見情境：nginx 每次轉發請求給 `thumbd` 都新建連線，並由 nginx 主動關閉。nginx 這台機器上的 TIME_WAIT 連線佔用的是它的 ephemeral port；四元組的 server 端固定（`thumbd` 的 IP 與 port），client 端能變化的只有 port，而 Linux 預設範圍 32768–60999 大約 28,000 個。如果每個 port 要在 TIME_WAIT 停 60 秒，那麼對同一個 upstream 的新連線速率上限大約是：

```text
28,232 個 port ÷ 60 秒 ≈ 470 條新連線／秒
```

超過這個速率，`connect` 就會因為找不到可用的 port 而失敗（`EADDRNOTAVAIL`）。正確的解法是**重用連線**：讓 nginx 對 upstream 開啟 keep-alive（第 29 章），一條連線服務很多個請求，而不是去調整 kernel 參數把 TIME_WAIT 縮短。

> [!warning] 常見誤解
> 「把 `net.ipv4.tcp_fin_timeout` 調小就能縮短 TIME_WAIT。」不能。依 `tcp(7)`，`tcp_fin_timeout`（預設 60 秒）控制的是等待對方最後一個 FIN 的時間，也就是 FIN_WAIT_2 狀態；Linux 的 TIME_WAIT 長度是寫死在 kernel 裡的 60 秒，沒有對應的 sysctl。`net.ipv4.tcp_tw_reuse` 允許 client 端在協定上安全時重用 TIME_WAIT 的 port，但 man page 也提醒不要在沒有專家建議時更動它。

### 網路程式的檢查清單

| 檢查項目 | 為什麼 |
|---|---|
| 所有 `read` 都在迴圈裡，依 framing 規則判斷訊息結束 | TCP 不保留邊界 |
| 所有 `write` 都處理 short count | send buffer 可能只收一部分 |
| 長度欄位與行長度有上限 | 避免惡意輸入耗盡記憶體 |
| 啟動時忽略 SIGPIPE | 避免對方斷線時 process 被終止 |
| server 設定 `SO_REUSEADDR` | 重啟時不被 TIME_WAIT 擋住 |
| 用 `getaddrinfo`，不寫死 `sockaddr_in` | 同時支援 IPv4 與 IPv6 |
| 每條連線的 descriptor 在所有路徑上都會 `close` | 避免 CLOSE_WAIT 累積與 descriptor 耗盡 |
| 讀寫都有逾時（`SO_RCVTIMEO` 或 `poll`） | 避免一個不說話的 client 佔住資源 |

## 28.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 本機測試正常，上線後訊息偶爾不完整 | 假設一次 `read` 等於一則訊息 | tcpdump 看資料被分成多個 segment；在 client 印出每次 `read` 的長度 | 依 framing 規則在迴圈中累積到完整訊息 |
| 重啟後 `bind: Address already in use` | 舊連線停在 TIME_WAIT，或舊 process 其實還活著 | `ss -tan state time-wait '( sport = :PORT )'`；`ss -ltnp` 看誰在 listen | `bind` 前設 `SO_REUSEADDR`；若真有舊 process 在跑就先停掉它 |
| `connect: Connection refused` | 沒有程式在那個 IP:port listen；常見是 server 只 bind `127.0.0.1`，或 `localhost` 被解析成 `::1` | `ss -ltn` 看 bind 的位址；用 `getaddrinfo` 列出候選位址 | server bind 正確的介面；client 逐一嘗試所有位址 |
| 對方斷線後整個 server 消失，沒有任何 log | 寫入已關閉的連線收到 SIGPIPE | `strace` 看到 `--- SIGPIPE ---`；shell 的結束碼是 141（128 + 13） | `signal(SIGPIPE, SIG_IGN)`，處理 `EPIPE` |
| CLOSE_WAIT 連線越來越多 | 程式讀到 EOF 後沒有 `close`，或錯誤路徑漏了 `close` | `ss -tan state close-wait`；`ls /proc/PID/fd | wc -l` 持續上升 | 檢查每個分支都會關閉 descriptor |
| port 號印出來是奇怪的數字（例如 36895） | 忘了 `ntohs`，把 network byte order 直接當主機整數 | 把值換成十六進位，看是不是兩個 byte 對調 | 讀出時 `ntohs`，填入時 `htons`，或改用 `getnameinfo` |
| 錯誤訊息是 `Undefined error` 或不相干的文字 | 對 `getaddrinfo` 的回傳值用了 `strerror(errno)` | 看程式是否用 `gai_strerror` | 用 `gai_strerror(rc)` |

> [!tip] strace 一眼看出網路程式在做什麼
> 在 Linux 上執行 `strace -f -e trace=network,read,write ./thumbd`，可以看到每一次 `socket`、`bind`、`connect`、`accept` 的參數與回傳值，以及每次 `read` 實際拿到多少 bytes。這是驗證「short read 真的發生了」和「程式卡在哪個 `accept`／`read`」最快的方法。

## 28.14 動手練習

1. **手算**：把 `10.0.1.5` 轉成 32-bit 十六進位，寫出它在 network byte order 與 little endian 主機記憶體中的 4 個 bytes；再把 port 9100 轉成十六進位與 network byte order 的兩個 bytes。（驗證方法：把 `show("10.0.1.5", "9100")` 加進程式一執行，並用 `inet_pton` 印出 `sin_addr` 的四個 bytes。）
2. **手算**：MTU 9000（jumbo frame）的網路上，IPv4 與 TCP header 各 20 bytes，傳一個 1 MiB 的原圖需要幾個 segment？和 MTU 1500 相比少了幾個？（答案：MSS 8960，需要 ⌈1,048,576 ÷ 8960⌉ = 118 個；MTU 1500 時要 ⌈1,048,576 ÷ 1460⌉ = 719 個，少了 601 個。）
3. 修改程式二，把 framing 改成「4-byte 長度前綴（network byte order）＋內容」：client 用 `htonl` 寫長度，server 先讀滿 4 bytes、`ntohl` 取得長度、檢查不超過 1024，再讀滿內容。故意讓 client 送一個長度 100000 的訊息，確認 server 會拒絕。
4. 程式二的 server 在 `line[]` 滿的時候會靜靜地丟掉多出來的字元。把它改成：一行超過 255 bytes 時回傳一行錯誤訊息並關閉連線。這是 HTTP server 處理「header 過長」的雛形（第 29 章）。
5. 修改程式三，把 `listen` 的 backlog 改成 1，再讓 client 迴圈連 20 次並在每次 `connect` 前後記錄時間。在 Linux 與 macOS 上分別觀察：超過佇列長度的 `connect` 是立即失敗、還是變慢？（結果依平台而定，記錄下你看到的行為。）
6. 在 Linux 上用 `nc -l 9100` 開一個 server，用另一個終端機連上後，先關閉 client 的那一端，再用 `ss -tan` 觀察兩端分別處於什麼狀態；改成先關閉 server 端再觀察一次，找出 TIME_WAIT 出現在哪一端。

## 本章重點整理

- client-server 模型中，client 與 server 是 process 在一次互動中的角色；一次 transaction 包含請求、處理、回應、處理回應四步。
- 網路以分層封裝運作：應用資料被 TCP、IP 與底層網路依序加上 header，router 只看 IP header 決定下一站。
- IP 提供盡力而為的主機到主機傳遞；UDP 加上 port 並保留訊息邊界；TCP 提供可靠、有序、雙向的 byte stream，但不保留訊息邊界。
- IPv4 位址是 32-bit 整數，IPv6 是 128-bit；寫進 header 與 socket 位址結構的位址和 port 都用 network byte order（big endian），要用 `htons`／`ntohs` 等函式或 `inet_pton`／`inet_ntop` 轉換。
- 一條 TCP 連線由四元組（client IP、client port、server IP、server port）唯一決定，所以 server 用一個 port 就能服務大量連線。
- server 依序呼叫 `socket`、`bind`、`listen`、`accept`；client 呼叫 `socket`、`connect`。`accept` 回傳新的 connected socket，listening socket 繼續接受新連線。
- `getaddrinfo` 把名稱與服務轉成一串可直接使用的位址結構，讓程式同時支援 IPv4 與 IPv6；錯誤要用 `gai_strerror` 解讀。
- 一次 `write` 不等於一次 `read`；應用協定要用分隔符號、長度前綴或「一條連線一則訊息」來 framing，並限制訊息大小。
- 在 loopback 上幾乎測不出 short read，所以網路程式一定要以「每次 `read` 可能只拿到任意長度」為前提撰寫。
- 三次握手由 kernel 完成，已完成的連線排在 accept queue；`connect` 成功不代表 server 程式正在處理請求。
- 主動關閉連線的一端會停在 TIME_WAIT（Linux 60 秒）；server 在 `bind` 前設定 `SO_REUSEADDR` 才能立即重啟。
- 大量 CLOSE_WAIT 代表程式漏了 `close`；寫入已關閉的連線會觸發 SIGPIPE，server 要忽略它並處理 `EPIPE`。
- `ss`、`nc`、`tcpdump`、`strace` 分別能看連線狀態、手動送請求、看封包、看 system call，是診斷網路問題的基本工具組。

## 延伸問答

> [!question]- Q1. 為什麼說 TCP 是「byte stream」而不是「訊息」？這對寫程式有什麼影響？
> TCP 只保證送出端寫進去的 bytes 會依原本順序、不重複地出現在接收端，但它不記錄每次 `write` 的界線。kernel 會依 MSS、接收窗口與網路狀況任意切割或合併資料，接收端的 `read` 也是「目前有多少就給多少」。所以一次 `write` 可能需要多次 `read`，多次 `write` 也可能被一次 `read` 讀完。
>
> 影響是：應用協定必須自己定義訊息邊界（換行、長度前綴、或用連線結束當作邊界），接收端必須在迴圈中累積資料，直到 framing 規則判斷出一則完整訊息。只呼叫一次 `read` 就交給 parser 的程式，在 loopback 上可能永遠正常，在真實網路上就會隨機出錯。UDP 則相反，每個 datagram 就是一則訊息，但不保證送達與順序。

> [!question]- Q2. 手算題：`sin_port` 的值在 little endian 機器上直接用 `printf("%u")` 印出是 20480，原本的 port 是多少？
> 20480 = 0x5000。這個數字是把記憶體中的兩個 bytes 以 little endian 解讀得到的，所以記憶體裡依序是 `00 50`。`sin_port` 存的是 network byte order（big endian），把 `00 50` 以 big endian 解讀就是 0x0050 = 80。
>
> 所以原本的 port 是 80（HTTP）。正確寫法是 `ntohs(sin_port)`，它在 little endian 機器上會交換兩個 bytes，得到 80；在 big endian 機器上則什麼都不做。看到 port 號「怪怪的」，第一個要檢查的就是 byte order。

> [!question]- Q3. server 已經 listen 一個 port，為什麼還能同時和上萬個 client 通訊而不混淆？
> kernel 用完整的四元組（client IP、client port、server IP、server port）辨識一條 TCP 連線，而不是只看 server 的 port。每個 client 連進來時，它的 IP 或 ephemeral port 至少有一個不同，所以每條連線的四元組都唯一。
>
> 在程式裡，listening socket 只負責接新連線；每次 `accept` 都會產生一個新的 connected socket descriptor，對應到一條特定的連線。server 對這個 descriptor `read`／`write`，kernel 就知道是哪條連線。真正限制連線數的是 descriptor 上限（`ulimit -n`）、記憶體與 server 的並行模型，而不是 port。

> [!question]- Q4. 你在 production 看到 `thumbd` 重啟後 `bind: Address already in use`，但 `ps` 找不到舊 process。發生了什麼？怎麼修？
> 舊 process 結束時主動關閉了它所有的連線，這些連線在 kernel 裡進入 TIME_WAIT，會停留一段時間（Linux 是 60 秒），以處理遺失的 ACK 並讓舊封包過期。它們的本機位址正是 `thumbd` 的 port，而 kernel 預設拒絕 `bind` 一個仍有連線殘留的位址，所以新 process 得到 `EADDRINUSE`。可以用 `ss -tan state time-wait '( sport = :8080 )'` 確認。
>
> 修法是在 `bind` 之前呼叫 `setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, ...)`。它只允許在 TIME_WAIT 存在時重新 bind，不會讓兩個 process 同時 listen 同一個 port，所以是安全的標準做法。也要排除另一種可能：舊 process 其實還活著（例如在另一個 container 或 namespace），這時 `ss -ltnp` 會顯示它仍在 listen。

> [!question]- Q5. 程式找錯：下面的 client 有什麼問題？`fd = socket(AF_INET, SOCK_STREAM, 0); connect(fd, ...); write(fd, req, strlen(req)); n = read(fd, buf, sizeof buf); buf[n] = 0; parse(buf);`
> 至少有四個問題。第一，沒有檢查 `connect` 與 `write` 的回傳值，連線失敗或寫入不完整都不會被發現。第二，`write` 可能只寫一部分，要用迴圈寫滿。第三，`read` 只呼叫一次，可能只拿到回應的一部分，應依協定的 framing 在迴圈中讀到完整訊息。第四，如果 `read` 讀滿 `sizeof buf` 個 bytes，`buf[n] = 0` 會寫到陣列外；如果 `read` 回傳 −1，`buf[-1]` 也是越界。
>
> 另外它寫死 `AF_INET`，不支援 IPv6；沒有設定逾時，server 不回應時會永遠卡住；錯誤路徑沒有 `close(fd)`。修正版應該用 `getaddrinfo` 逐一嘗試位址、用 `writen` 寫入、用迴圈與 framing 讀取、讀取長度最多 `sizeof buf - 1`，並設定讀寫逾時。

> [!question]- Q6. `connect` 回傳成功，代表 server 程式已經開始處理我的請求了嗎？
> 不代表。TCP 三次握手完全由 server 端的 kernel 完成，握手結束後連線被放進 listening socket 的 accept queue，等 server 程式呼叫 `accept` 才會取出。所以即使 server 程式卡在處理別的請求、完全沒有呼叫 `accept`，client 的 `connect` 依然會成功，甚至可以把請求寫進去，本章程式三就示範了這一點。
>
> 實務上的意義是：只檢查「port 能不能連」的健康檢查，無法發現卡住的 server。健康檢查應該送一個真正的請求，在逾時內收到正確的回應才算健康。而 accept queue 長期堆積（`ss -ltn` 的 `Recv-Q` 很高）表示 server 處理速度跟不上，需要並行化或在過載時主動拒絕。

> [!question]- Q7. 什麼是 CLOSE_WAIT？為什麼大量 CLOSE_WAIT 幾乎一定是程式的 bug？
> 當對方先關閉連線（送出 FIN），我方的 kernel 回覆 ACK 後，這條連線進入 CLOSE_WAIT，意思是「對方說完了，等我方程式也 `close`」。只要程式呼叫 `close`，kernel 就會送出 FIN 並進入 LAST_ACK，很快結束。CLOSE_WAIT 的長度完全取決於程式什麼時候 `close`，kernel 不會替你逾時清除。
>
> 所以 CLOSE_WAIT 大量累積、而且不會自己消失，代表程式在讀到 EOF（`read` 回傳 0）或遇到錯誤之後沒有關閉 descriptor。常見原因是錯誤處理分支漏了 `close`，或連線物件被遺忘在某個資料結構中。它最後會耗盡 descriptor，導致 `accept` 失敗（`EMFILE`）。用 `ss -tanp state close-wait` 找出是哪個 process，再檢查它的連線關閉路徑。

> [!question]- Q8. 面試題：client 連 `localhost:8080` 失敗，但連 `127.0.0.1:8080` 成功，可能的原因是什麼？
> 最常見的原因是 IPv4 與 IPv6 的差異。`localhost` 在許多系統上同時對應 `::1` 與 `127.0.0.1`，而且 `getaddrinfo` 可能把 `::1` 排在前面。如果 server 只 bind 了 `127.0.0.1`（IPv4），連 `::1` 就會被拒絕；如果 client 只嘗試第一個位址就放棄，使用者看到的就是「localhost 連不上」。
>
> 確認方法是用 `getaddrinfo` 或 `getent ahosts localhost` 看候選位址的順序，再用 `ss -ltn` 看 server bind 了哪些位址。修法有兩個方向：server 同時 listen IPv4 與 IPv6（bind `::` 並允許 IPv4-mapped，或開兩個 socket）；client 走訪 `getaddrinfo` 回傳的所有位址，一個失敗就試下一個。另外也要檢查 `/etc/hosts` 是否被改過。

## 延伸閱讀

- [CS:APP 3e 官方網站](https://csapp.cs.cmu.edu/)：原書第 11 章與 `csapp.c` 中 `open_clientfd`、`open_listenfd` 的完整程式。
- [CS:APP 3e 學生資源](https://csapp.cs.cmu.edu/3e/students.html)：書中程式碼與相關教材。
- [Linux man pages](https://man7.org/linux/man-pages/)：`socket(7)`、`tcp(7)`、`ip(7)`、`ipv6(7)`、`getaddrinfo(3)`、`ss(8)`，其中 `tcp(7)` 說明了 TIME_WAIT、backlog 相關的 kernel 參數。
- [POSIX 規格（The Open Group Base Specifications）](https://pubs.opengroup.org/onlinepubs/9799919799/)：`socket`、`bind`、`listen`、`accept`、`connect`、`getaddrinfo` 的標準定義，寫可移植程式時以它為準。
