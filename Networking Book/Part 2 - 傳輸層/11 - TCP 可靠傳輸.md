---
chapter: 11
title: TCP 可靠傳輸：序號、重傳與視窗
part: 2
---

# 第 11 章　TCP 可靠傳輸：序號、重傳與視窗

> [!abstract] 本章地圖
> **核心問題**：底下的 IP 會丟包、亂序、重複，TCP 怎麼在上面做出一條「可靠、有序的 byte stream」，而這條 stream 又會在哪些地方讓應用程式踩雷？
>
> **你會學到**：
> - 說清楚 byte stream 沒有訊息邊界的意思，並用 length-prefix 等方式在 TCP 上正確切出訊息（framing）
> - 用序號與 ACK 手動追蹤一段資料傳輸，看懂 tcpdump 裡的 seq、ack、win 與 SACK 欄位
> - 解釋 RTO 怎麼從 RTT 算出來、fast retransmit 與 SACK 為什麼比等逾時快
> - 用模擬比較 stop-and-wait、Go-Back-N、selective repeat 的吞吐與重傳數，並算出「吞吐約等於視窗除以 RTT」
> - 分辨流量控制（receive window）與擁塞控制，觀察 zero window
> - 判斷什麼時候該開 TCP_NODELAY、該不該用 TCP keepalive
>
> **前置知識**：第 9 章（port、socket API、UDP 的不可靠語意）、第 10 章（TCP header、三向交握、ISN 與連線狀態）

## 11.1 故事：黏在一起的白板事件，和固定慢 40 ms 的請求

聲聲 Live 的教室裡有一塊共享白板。老師畫一筆，瀏覽器透過 WebSocket 送到即時服務（第 32 章），即時服務再把每一筆事件轉送給後端一支「課堂錄製服務」，讓課後可以重播整堂課。這段轉送是內部流量，小晴為了省事，沒有用 HTTP，直接開一條 TCP 連線，每筆事件 `json.dumps()` 之後 `sock.send()` 出去；錄製服務那邊則是 `data = conn.recv(4096)` 再 `json.loads(data)`。

在小晴的筆電上測了十幾次都正常。上線第一天下午，錄製服務的 log 開始出現 `json.decoder.JSONDecodeError: Extra data`，偶爾還有 `Unterminated string`。小晴把出錯的 `data` 印出來，看到兩筆事件黏在一起：`{"type":"stroke",...}{"type":"stroke",...}`；另一種錯誤則是一筆事件只收到前半段。小晴的第一反應是「TCP 不是可靠的嗎？怎麼會收到一半？」

阿德看了一眼程式就笑了：「TCP 很可靠，你送出的每一個 byte 它都會按順序交給對方，一個不少。可是它從來沒答應過『你 send 一次，對方就 recv 一次』。TCP 給你的是一條水管，不是一疊信封。」

第二個問題在修好第一個之後才浮現。小晴改了協定：先送 4 bytes 的長度，再送 JSON 本體，兩次 `send()`。錯誤消失了，可是錄製服務回 ACK 的延遲在 Linux 機器上固定多了大約 40 ms，在小晴的 Mac 上卻幾乎看不出來。第三個問題來自 Joe：一位在國外上課的學生，Wi-Fi 很不穩，上傳作業檔案時常常整整卡住好幾秒才繼續，`ss` 顯示那條連線的 `rto` 值一路往上跳。

這三個症狀分別對應 TCP 可靠傳輸的三個核心：byte stream 沒有訊息邊界、Nagle 演算法與 delayed ACK 的交互作用、以及重傳逾時的計算與退避。第 10 章我們看了連線怎麼建立與關閉；這一章看連線建立之後，資料到底是怎麼被可靠地送過去的。讀完這章，小晴遇到的三個問題你都能自己解釋並修好。

## 11.2 TCP 承諾了什麼：可靠、有序的 byte stream

第 9 章看過 UDP：每個 datagram 是一個獨立的包裹，可能丟、可能亂序、可能重複，但包裹的邊界一定保留，送 3 個就最多收到 3 個。TCP 正好相反：它保證資料不丟、不亂序、不重複，代價是**不保留邊界**。**byte stream**（位元組串流）的意思是：TCP 眼中只有一長串連續的 bytes，應用程式每次 `send()` 只是把一段 bytes 倒進傳送端的緩衝區，TCP 自己決定怎麼切成 **segment**（TCP 的傳輸單位，一個 segment 放在一個 IP 封包裡）送出；接收端每次 `recv()` 則是從接收緩衝區撈出「目前有的、最多 N 個」bytes。例如送端連續 `send(b"AB")`、`send(b"CD")`，收端可能一次 `recv()` 拿到 `b"ABCD"`，也可能先拿到 `b"A"` 再拿到 `b"BCD"`。

```text
 應用程式 send()        TCP 傳送緩衝區         網路上的 segment           應用程式 recv()
 ─────────────         ──────────────         ────────────────          ─────────────
 send("JOIN")  ──┐
 send("CHAT")  ──┼──►  JOINCHATBYE...  ──►  [JOINCH] [ATBYE...]  ──►  recv() → "JOINCHA"
 send("BYE")   ──┘     （只有 bytes，     （切法由 TCP 決定：      recv() → "TBYE"
                        沒有邊界記號）      MSS、Nagle、視窗…）     （切法又由接收時機決定）
```

這張圖從左到右分成四欄。第一欄是應用程式的三次 `send()`，看起來是三則訊息。第二欄是傳送緩衝區，三段 bytes 被接在一起，中間沒有任何分隔記號。第三欄是真正上網路的 segment，切點由 TCP 依 **MSS**（maximum segment size，一個 segment 最多能裝的資料量，Ethernet 上常見 1460 bytes）、Nagle 演算法、對方視窗等因素決定，和應用程式的 send 次數無關。第四欄是接收端的 `recv()`，它拿到多少取決於呼叫當下緩衝區裡累積了多少，跟網路上的切法也不必相同。所以「一次 send 對應一次 recv」在三個地方都可能被打破。

在小晴的筆電上測不出問題，是因為測試時事件間隔很長、資料很小，每次 recv 剛好只撈到一筆。上線後事件密集，錄製服務稍微忙一下，緩衝區裡就累積了兩三筆；反過來，事件大到超過一個 segment，或接收端剛好在半途讀，就會只拿到半筆。網路上常把這種現象叫「黏包」與「拆包」，但它不是 TCP 的 bug，而是 byte stream 的定義。

| 性質 | UDP（第 9 章） | TCP | 對應用程式的意義 |
|---|---|---|---|
| 送達 | 不保證，丟了就丟了 | 保證，丟了會重傳 | TCP 不用自己做重送，但會出現等待重傳的延遲 |
| 順序 | 不保證 | 保證按送出順序交付 | 一個 byte 卡住，後面的都要等（第 12 章的 head-of-line blocking） |
| 重複 | 可能重複 | 自動去重 | 不用自己處理重複的 bytes |
| 訊息邊界 | 保留，一個 datagram 一則 | 不保留，只有 byte stream | 應用層必須自己做 framing |
| 「對方已處理」 | 不保證 | 也不保證 | ACK 只表示對方核心收到，不代表對方程式處理完 |

表格最後一列是常被忽略的一點：TCP 的 ACK 是由對方的作業系統核心發出的，表示「這些 bytes 已經進了我的接收緩衝區」，不表示對方的應用程式讀了、更不表示寫進資料庫了。如果錄製服務在讀出資料前就當機，TCP 層面一切正常，資料還是不見了。這就是為什麼很多應用協定（例如訊息佇列的 consumer ack）還要在應用層再做一次確認，這個想法在系統設計裡叫 end-to-end argument：可靠性最終只能由兩端的應用自己保證。

### Framing：在 byte stream 上切出訊息

**framing**（訊框化）就是在 byte stream 上約定「一則訊息從哪裡開始、到哪裡結束」。常見做法有四種，你在本書後面會一再看到它們：

| 做法 | 怎麼運作 | 例子 | 優點 | 缺點與陷阱 |
|---|---|---|---|---|
| 分隔符號 | 用特殊 byte 標記結尾，例如 `\n` | Redis 的部分指令、SMTP、NDJSON、SSE（第 31 章） | 人眼可讀、好用 nc 除錯 | 內容本身含分隔符號時要跳脫；要逐 byte 掃描 |
| 長度前綴（length-prefix） | 先送固定長度的「長度」欄位，再送內容 | gRPC 訊息、TLS record（第 18 章）、Kafka 協定 | 不用掃描、二進位安全 | 必須限制最大長度，否則惡意長度會吃光記憶體 |
| 固定長度 | 每則訊息一樣長 | 某些硬體與金融協定 | 最簡單 | 浪費空間，難以擴充 |
| 自描述 header | header 裡說明 body 怎麼結束 | HTTP/1.1 的 Content-Length 與 chunked（第 20 章）、WebSocket frame（第 32 章）、HTTP/2 frame（第 22 章） | 彈性大 | 解析器複雜，兩端理解不一致時會有 request smuggling 一類問題 |

不管選哪一種，接收端的寫法都一樣：把收到的 bytes 累積進自己的緩衝區，每次檢查「是否已經湊滿一則完整訊息」，湊滿就切出來處理，剩下的留著等下一次 recv。Python 裡 `asyncio.StreamReader` 的 `readexactly(n)` 與 `readuntil(b"\n")`，或 `socket.makefile()` 之後的 `readline()`，都是幫你做這件事。11.9 節會用真的 TCP 連線把黏包重現出來，再用 length-prefix 修好。

> [!warning] 常見誤解
> 「開了 TCP_NODELAY 或設 PSH 旗標就不會黏包。」不對。TCP_NODELAY 只影響傳送端何時把資料送出（11.8 節），PSH 旗標只是提示接收端「可以把資料交給應用程式了」，兩者都不會在 byte stream 裡留下邊界。接收端只要晚一點讀，緩衝區裡照樣會有好幾則訊息。framing 是應用協定的責任，不能交給傳輸層。

## 11.3 序號與 ACK：替每一個 byte 編號

要在會丟、會亂的網路上做出不丟、不亂的 stream，第一步是讓兩端能討論「哪些資料到了、哪些還沒到」。TCP 的做法是替 stream 裡的**每一個 byte**編號。**序號**（sequence number）是 32 位元的數字，segment header 裡的 Sequence Number 欄位寫的是「這個 segment 第一個資料 byte 的編號」。第 10 章講過，交握時雙方各自隨機選一個 **ISN**（initial sequence number），SYN 本身佔用一個序號，所以第一個資料 byte 的編號是 ISN+1；FIN 也同樣佔用一個序號。

**ACK**（acknowledgment）欄位寫的是「我期待收到的下一個 byte 的編號」，也就是「這個編號之前的全部都收到了」。這種確認方式叫**累積確認**（cumulative ACK）。例如對方回 `ack=3001`，意思是 1～3000 號都到了，不需要逐個 segment 確認。累積確認的好處是 ACK 掉了不要緊，下一個 ACK 會把之前的資訊一起帶上；壞處是它只能描述「連續收到到哪裡」，中間有洞時說不出洞後面還收到了什麼，這個缺口要靠 11.4 節的 SACK 補。

再看一次第 10 章出現過的 TCP header，這次把本章會用到的欄位標出來：

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |          Source Port          |       Destination Port        |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                        Sequence Number                        | ◄ 本 segment 第一個 byte 的編號
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    Acknowledgment Number                      | ◄ 期待的下一個 byte（ACK 旗標為 1 時有效）
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |  Data |       |C|E|U|A|P|R|S|F|                               |
 | Offset| Rsrvd |W|C|R|C|S|S|Y|I|            Window             | ◄ 接收端還能收多少 bytes（流量控制）
 |       |       |R|E|G|K|H|T|N|N|                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |           Checksum            |         Urgent Pointer        |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                 Options（0～40 bytes，4 的倍數）               | ◄ MSS、Window Scale、SACK、Timestamps
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                             Data                              |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

固定部分 20 bytes，和第 10 章一致。本章的主角是第 2、3 列的 Sequence Number 與 Acknowledgment Number（各 32 位元）、第 4 列的 16 位元 Window，以及 Options 區。注意 Window 只有 16 位元，最大 65535，這在高速長距離連線上不夠用，11.7 節會講 Window Scale 選項怎麼把它放大。Data Offset 以 4 bytes 為單位標出 header 長度，所以 header 最長 60 bytes，Options 最多 40 bytes，這個空間限制會影響 SACK 一次能報告幾個區塊。

下面是一段資料傳輸的時序。假設 client 的 ISN 是 1000，交握後要送 3000 bytes，MSS 是 1000：

```text
 Client（seq 從 1001 開始）                               Server
   │── seq=1001 len=1000（bytes 1001～2000）──────────────►│
   │── seq=2001 len=1000（bytes 2001～3000）──────────────►│
   │◄──────────────────────────────── ack=3001 win=64000 ──│  一次確認兩個 segment
   │── seq=3001 len=1000（bytes 3001～4000）──────────────►│
   │◄────────── seq=5001 len=200 ack=4001 win=64000 ───────│  回應資料順便帶 ACK
   │── ack=5201 ──────────────────────────────────────────►│  （piggyback）
```

逐步看：client 連續送出兩個 segment，seq 分別是 1001 與 2001，各帶 1000 bytes。server 不必每個都回，一個 `ack=3001` 就表示 1001～3000 全收到，`win=64000` 表示 server 的接收緩衝區還有 64000 bytes 的空間。接著 client 送第三段，server 這次有回應資料要送（假設 server 的序號空間目前到 5001），就把 `ack=4001` 放在自己的資料 segment 裡一起送，這叫 **piggyback**（搭便車）；ACK 不是獨立的封包類型，只是 header 裡的一個欄位，任何 segment 都可以帶。最後 client 確認 server 的 200 bytes，回 `ack=5201`。兩個方向的序號各自獨立，這也是為什麼 TCP 是全雙工的。

### 序號會繞回：32 位元的比較方式

32 位元的序號最多到 4,294,967,295，之後繞回 0。ISN 是隨機的，可能一開始就接近上限，所以 TCP 實作不能用一般的大於小於比較序號，而是看兩數的差落在「前半圈」還是「後半圈」。下面這段程式示範這種比較，並算出不同速度下多久會跑完一整圈：

```python
MOD = 1 << 32                            # TCP 序號是 32 位元，會繞回 0


def seq_lt(a, b):
    """a 是否在 b「之前」：看差值落在前半圈還是後半圈（RFC 1982 式比較）。"""
    return a != b and ((b - a) % MOD) < (1 << 31)


isn = 4_294_967_000                      # ISN 接近上限，送 1000 bytes 就會繞回
after = (isn + 1000) % MOD
print("ISN =", isn, "→ 送 1000 bytes 後 =", after)
print("單純比大小 isn < after：", isn < after)
print("序號空間比較 seq_lt(isn, after)：", seq_lt(isn, after))
assert seq_lt(isn, after) and not seq_lt(after, isn)

for gbps in (0.1, 1, 10, 100):
    secs = MOD / (gbps * 1e9 / 8)
    print(f"{gbps:>5g} Gbps 跑完整個序號空間：{secs:8.2f} 秒")
```

```text
ISN = 4294967000 → 送 1000 bytes 後 = 704
單純比大小 isn < after： False
序號空間比較 seq_lt(isn, after)： True
  0.1 Gbps 跑完整個序號空間：  343.60 秒
    1 Gbps 跑完整個序號空間：   34.36 秒
   10 Gbps 跑完整個序號空間：    3.44 秒
  100 Gbps 跑完整個序號空間：    0.34 秒
```

第一部分：ISN 是 4,294,967,000，送 1000 bytes 之後序號變成 704。單純比大小會得出「後送的比較小」的錯誤結論；`seq_lt` 用模 2^32 的差值判斷，正確地認出 704 在 4,294,967,000「之後」。Linux 核心裡的 `before()`、`after()` 巨集就是同樣的想法。第二部分的數字更值得注意：在 10 Gbps 下，3.44 秒就跑完一圈。如果一個舊 segment 在網路上繞了幾秒才到，它的序號可能剛好落在新一圈的有效範圍內，被誤當成新資料。為了防止這種事，TCP 有 **Timestamps 選項**：每個 segment 帶一個單調遞增的時間戳記，接收端看到時間戳記比最近的舊，就丟掉，這個機制叫 **PAWS**（Protection Against Wrapped Sequences）。Timestamps 也讓 RTT 量測更準，下一節會用到。

## 11.4 重傳：怎麼知道資料不見了

接收端只會說「我收到哪裡」，不會說「我沒收到什麼」，因為它根本不知道有東西被送出來。所以偵測丟包是傳送端的責任，靠的是兩種訊號：等太久沒有 ACK（逾時），以及收到的 ACK 透露出「中間有洞」（重複 ACK 與 SACK）。

### 逾時重傳與 RTO 的計算

最基本的機制是**逾時重傳**：每送出資料就啟動計時器，計時器到期還沒被確認，就重送。這個等待時間叫 **RTO**（retransmission timeout）。RTO 的難處在於設多少：設太短，ACK 只是晚到也會被當成遺失，造成不必要的重傳（**spurious retransmission**），浪費頻寬還可能誤觸擁塞控制；設太長，真的掉了要白等很久。而 RTT 本身會變：同一條連線上，Wi-Fi 搶不到通道、路由器佇列變長，都會讓 RTT 忽大忽小。

RFC 6298 的做法是持續量測 **RTT**（round-trip time，送出到收到對應 ACK 的時間），維護兩個值：平滑後的平均 **SRTT**，以及平均偏差 **RTTVAR**。每個新樣本 R 進來時：

- RTTVAR ← (1 − 1/4) × RTTVAR + 1/4 × |SRTT − R|
- SRTT ← (1 − 1/8) × SRTT + 1/8 × R
- RTO ← SRTT + 4 × RTTVAR（再套上下限）

用平均加四倍偏差，是因為 RTT 的分布有長尾，只用平均會常常誤判；變異大的連線就該等久一點。下面用一位跨洋上課學生的 RTT 樣本跑一次：

```python
# RFC 6298 的 RTO 計算：用 RTT 平均值 + 4 倍變異量當逾時門檻
ALPHA, BETA, MIN_RTO = 1 / 8, 1 / 4, 0.200   # RFC 建議下限 1 s；這裡用 200 ms 方便觀察


def rto_trace(samples):
    srtt = rttvar = None
    for r in samples:
        if srtt is None:                       # 第一個樣本
            srtt, rttvar = r, r / 2
        else:                                  # 先更新變異量，再更新平均
            rttvar = (1 - BETA) * rttvar + BETA * abs(srtt - r)
            srtt = (1 - ALPHA) * srtt + ALPHA * r
        rto = max(MIN_RTO, srtt + 4 * rttvar)
        yield r, srtt, rttvar, rto


# 跨洋上課的學生：平常 RTT 約 150 ms，第 5 個樣本遇到 Wi-Fi 抖動
samples = [0.150, 0.155, 0.148, 0.152, 0.400, 0.160, 0.150, 0.151, 0.149, 0.150]
print(" 樣本RTT    SRTT  RTTVAR     RTO")
for r, srtt, var, rto in rto_trace(samples):
    print(f"{r*1000:7.0f}{srtt*1000:8.1f}{var*1000:8.1f}{rto*1000:8.0f}  ms")

# 逾時後指數退避：每次重傳等待時間加倍（上限依實作，常見 60 秒以上）
rto, waits = 0.2, []
for _ in range(6):
    waits.append(rto)
    rto = min(rto * 2, 120)
print("連續逾時的等待：" + " → ".join(f"{w:g}s" for w in waits) + f"，累計 {sum(waits):g} s")
assert waits[-1] == 6.4
```

```text
 樣本RTT    SRTT  RTTVAR     RTO
    150   150.0    75.0     450  ms
    155   150.6    57.5     381  ms
    148   150.3    43.8     325  ms
    152   150.5    33.3     284  ms
    400   181.7    87.3     531  ms
    160   179.0    70.9     463  ms
    150   175.4    60.4     417  ms
    151   172.3    51.4     378  ms
    149   169.4    44.4     347  ms
    150   167.0    38.1     320  ms
連續逾時的等待：0.2s → 0.4s → 0.8s → 1.6s → 3.2s → 6.4s，累計 12.6 s
```

逐列看：第一個樣本 150 ms 時，RFC 規定 SRTT 直接等於樣本、RTTVAR 取樣本的一半，所以 RTO 是 150 + 4 × 75 = 450 ms，一開始對網路不了解，保守一點。接下來三個樣本都很穩定，RTTVAR 從 75 降到 33.3，RTO 跟著收斂到 284 ms。第五個樣本突然是 400 ms，SRTT 只被拉高到 181.7（因為新樣本只佔 1/8 權重），但 RTTVAR 跳到 87.3，RTO 立刻放寬到 531 ms，這就是「偏差大就多等一點」。之後 RTT 回穩，RTO 又慢慢降回 320 ms。最後一行是**指數退避**（exponential backoff）：同一段資料連續逾時，每次 RTO 加倍，因為連續逾時通常表示網路嚴重擁塞或斷線，再急著重送只會更糟。從 200 ms 開始退避六次就累計 12.6 秒，這正是 Joe 那位學生上傳卡住好幾秒的原因：Wi-Fi 連續掉了幾次包，RTO 一路翻倍。

真實系統還有幾個細節。第一，RFC 6298 建議 RTO 下限 1 秒，但 Linux 的下限約 200 ms，計算方式也略有不同（把下限套在變異量那一項），實務上 Linux 的 RTO 大約是 RTT 再加 200 ms 左右。第二，**Karn 演算法**：重傳過的 segment 收到 ACK 時，無法分辨這個 ACK 是回應原本那份還是重傳那份，所以不拿來更新 RTT；有了 Timestamps 選項，ACK 會回傳對應 segment 的時間戳記，就能消除這種模糊。第三，Linux 上一條已建立的連線，資料持續逾時要重傳很多次才會放棄（由 `net.ipv4.tcp_retries2` 控制，預設值換算下來大約 15 分鐘量級），所以拔掉網路線後，應用程式的 `send()` 可能長時間不報錯，這也是 11.10 節要談的問題。

### Fast retransmit：三個重複 ACK

逾時重傳最少要等一個 RTO，通常是 RTT 的好幾倍。如果傳送端手上還有後續資料在飛，其實有更快的線索。接收端收到亂序的 segment 時，會立刻回一個 ACK，ack 值仍然停在洞的位置；傳送端連續看到同一個 ack 值，叫**重複 ACK**（duplicate ACK）。RFC 5681 規定收到三個重複 ACK 時，不等 RTO，立刻重傳洞所在的那個 segment，這叫 **fast retransmit**（快速重傳）。

```text
 Sender                                                  Receiver
   │── seq=1001 ─────────────────────────────────────────►│  收到，期待 2001
   │◄───────────────────────────────────────── ack=2001 ──│
   │── seq=2001 ─────────────────X（遺失）                 │
   │── seq=3001 ─────────────────────────────────────────►│  有洞！仍期待 2001
   │◄───────────────────────────── ack=2001（dup #1） ────│
   │── seq=4001 ─────────────────────────────────────────►│
   │◄───────────────────────────── ack=2001（dup #2） ────│
   │── seq=5001 ─────────────────────────────────────────►│
   │◄───────────────────────────── ack=2001（dup #3） ────│
   │  三個重複 ACK → 不等 RTO，立刻重傳 2001                │
   │── seq=2001（重傳）───────────────────────────────────►│  洞補上，3001～6000 早已在緩衝區
   │◄───────────────────────────────────────── ack=6001 ──│  一次跳到 6001
```

這張圖的關鍵在中段：2001 那段掉了，後面 3001、4001、5001 陸續到達，接收端每收到一個都回 `ack=2001`，等於一直喊「我還在等 2001」。傳送端數到第三個重複 ACK 就重傳 2001。接收端把洞補上後，因為 3001～6000 早就收在緩衝區裡，ack 直接跳到 6001。為什麼是三個而不是一個？因為網路偶爾會亂序：一個 segment 走了比較慢的路徑，晚一點到，也會造成一兩個重複 ACK。門檻設成三是在「反應速度」與「誤把亂序當遺失」之間取的折衷。fast retransmit 有一個前提：後面要有足夠的資料在飛，才會產生重複 ACK。如果丟的是一批資料的最後一個 segment（tail loss），後面沒有東西了，就只能等 RTO，這個弱點後來由 RACK-TLP 補強（見本節最後）。

### SACK：告訴對方洞後面收到了什麼

累積 ACK 只能說「連續收到哪裡」。如果一個視窗裡掉了兩個不相鄰的 segment，傳送端靠重複 ACK 只能知道第一個洞，補完第一個洞才發現第二個，每個洞要花一個 RTT。**SACK**（selective acknowledgment，選擇性確認，RFC 2018）讓接收端在 ACK 裡額外列出「洞後面我已經收到的區塊」，傳送端就能一次看見所有的洞，只重傳真正缺的部分。

SACK 要在交握時協商：雙方在 SYN 裡放 **SACK-Permitted** 選項（kind=4，長度 2 bytes），都有放才啟用。之後的 ACK 可以帶 SACK 選項：

```text
 SACK 選項（kind=5）
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
                                 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                                 |  Kind = 5     | Length = 8n+2 |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                 Left Edge of 1st Block（區塊起點）              |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                 Right Edge of 1st Block（區塊終點的下一個）       |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                              ...                              |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                 Left Edge / Right Edge of nth Block           |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

每個區塊用兩個 32 位元序號描述：左邊界是區塊的第一個 byte，右邊界是區塊最後一個 byte 的下一個編號，和 ACK 的「下一個」語意一致。選項本身 2 bytes，加上每個區塊 8 bytes，所以 Length = 8n + 2。Options 最多 40 bytes，最多放 4 個區塊；實務上大多數連線同時開了 Timestamps（10 bytes，加上對齊用的 NOP 共 12 bytes），剩下的空間只夠 3 個區塊。這就是 header 空間限制影響協定能力的一個具體例子。

假設上面的時序圖裡掉的是 2001 與 4001 兩段，接收端收到 3001 與 5001 之後回的 ACK 會長這樣（tcpdump 的顯示格式，示意輸出）：

```text
 IP 10.20.1.5.8000 > 10.20.3.7.51514: Flags [.], ack 2001, win 501, options [nop,nop,sack 1 {3001:4001}], length 0
 IP 10.20.1.5.8000 > 10.20.3.7.51514: Flags [.], ack 2001, win 501, options [nop,nop,sack 2 {5001:6001}{3001:4001}], length 0
```

第一行：ack 仍是 2001，但 SACK 告訴傳送端「3001～4000 我有了」。第二行：又收到 5001～6000，SACK 列出兩個區塊（最新收到的區塊放第一個）。傳送端由此推得 2001～3000 與 4001～5000 是洞，可以在同一個 RTT 內把兩段都補上。`win 501` 是還沒乘上 window scale 的原始值，11.7 節會解釋。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流作業系統的 TCP 預設都會協商 SACK 與 Timestamps。Linux 除了傳統的重複 ACK 門檻，也預設採用 **RACK-TLP**（RFC 8985）偵測遺失：RACK 改用「比某個已確認 segment 早送出、且超過一小段時間還沒被確認」來判斷遺失，對亂序比較有容忍度；TLP（tail loss probe）在一批資料尾端遲遲沒有 ACK 時，提早送一個探測 segment，引出 SACK 資訊，避免 tail loss 只能乾等 RTO。實際行為依核心版本與 sysctl 設定而定（例如 `net.ipv4.tcp_recovery`）。另外有 **D-SACK**（RFC 2883），接收端用 SACK 回報「這段我收到兩次了」，讓傳送端發現自己做了不必要的重傳。

## 11.5 滑動視窗：一次可以送多少

知道怎麼確認、怎麼重傳之後，最簡單的可靠協定是 **stop-and-wait**：送一個 segment，等它的 ACK，再送下一個。它一定正確，但慢得驚人。每個 RTT 只能送一個 segment，吞吐量上限是「segment 大小 ÷ RTT」。以 RTT 150 ms、segment 1448 bytes 計算：1448 × 8 ÷ 0.15 ≈ 77 kbps，連一通語音通話都撐不起來，不論底下的鏈路有多快。

解法是允許一次有多個 segment「在路上」，不必等前一個被確認。**滑動視窗**（sliding window）規定傳送端最多可以有 W bytes 已送出但未確認；每收到 ACK，視窗左緣往右滑，就能再送新的資料。這樣每個 RTT 可以送 W bytes，**吞吐量 ≈ W ÷ RTT**。這條式子是本章最重要的一個關係，第 12 章的 bandwidth-delay product 也是從這裡出發。

```text
 傳送端看到的序號空間
                 SND.UNA                    SND.NXT            SND.UNA + W
                    │                          │                    │
 ───────────────────┼──────────────────────────┼────────────────────┼─────────────────►
  已送出且已確認     │   已送出、尚未確認         │   可以立刻送         │   不能送（超出視窗）
  （可以從緩衝區丟掉）│  （要保留，可能要重傳）     │  （視窗內還有空間）   │
                    └──────────── 視窗 W ─────────────────────────────┘
 收到 ack 往前推 → SND.UNA 右移 → 整個視窗往右「滑」，右緣露出新的可送空間
```

圖上有三條關鍵界線。**SND.UNA**（send unacknowledged）是最舊的未確認 byte，它左邊的資料都已被確認，可以從傳送緩衝區釋放。**SND.NXT**（send next）是下一個要送的新 byte，SND.UNA 到 SND.NXT 之間是「在路上」的資料，必須留著以防重傳。從 SND.UNA 算起 W 的範圍是視窗，SND.NXT 到視窗右緣之間是還能立刻送的額度。ACK 進來讓 SND.UNA 右移，右緣跟著右移，視窗就像在序號軸上滑動。W 由兩個東西決定：接收端在 Window 欄位宣告的空間（流量控制，11.7 節）與傳送端自己估計的網路容量（擁塞視窗，第 12 章），取兩者較小的一個。

有了視窗之後，丟包時要重傳多少就有了不同策略。教科書上有兩種經典設計，TCP 是兩者的混合：

| 設計 | 接收端行為 | ACK 方式 | 丟包時傳送端重傳 | 優點 | 缺點 |
|---|---|---|---|---|---|
| Stop-and-wait | 一次只收一個 | 逐個確認 | 那一個 | 最簡單，緩衝區只要一格 | 吞吐量 = 一個 segment ÷ RTT |
| Go-Back-N | 只收按順序的，亂序的直接丟掉 | 累積 ACK | 從遺失處起整個視窗重送 | 接收端不需要緩衝亂序資料 | 一個洞造成大量重複傳送；亂序也會觸發重送 |
| Selective repeat | 亂序的先存起來 | 逐個確認（或累積 ACK＋SACK） | 只重送真正遺失的 | 重傳最少 | 接收端要有緩衝區，兩端狀態較複雜 |
| 現代 TCP | 亂序的先存起來 | 累積 ACK＋SACK | 依 SACK 找出的洞；逾時則從 SND.UNA 開始 | 兼顧 ACK 遺失的容忍與精準重傳 | 實作複雜，細節很多 |

Go-Back-N 的名字很直白：發現某段沒到，就「退回 N 步」從那裡全部重來，因為接收端把洞之後收到的都丟了。selective repeat 則是哪個缺補哪個。TCP 的接收端一直都會暫存亂序的資料，早期沒有 SACK 時，傳送端的行為比較接近 Go-Back-N（逾時後常常從 SND.UNA 一路重送）；有了 SACK，才真正做到 selective repeat。下一節用模擬把這些差異量化。

## 11.6 動手做：模擬 stop-and-wait、Go-Back-N 與 selective repeat

這段程式用**離散事件模擬**（discrete-event simulation：不真的等待，而是把「某時刻會發生什麼」排進一個依時間排序的佇列，一件一件處理）建出一條通道：單程延遲 50～60 ms、鏈路每 1 ms 只能送出一個封包、3% 的封包會走慢路徑而被後面的超車（亂序）、並依參數隨機丟包，兩個方向都會丟。上面跑四種協定，各送 300 個封包，視窗 32，RTO 固定 200 ms。stop-and-wait 直接用視窗為 1 的 Go-Back-N 表示，因為兩者在視窗為 1 時行為完全相同。

```python
import heapq
import random

N_PKTS, RTO, LINK_GAP = 300, 200.0, 1.0   # 封包數、逾時（ms）、每個封包佔用鏈路 1 ms


class Channel:
    """離散事件模擬：會丟包、延遲抖動、偶爾亂序的單向通道。"""

    def __init__(self, loss, seed):
        self.rng, self.loss = random.Random(seed), loss
        self.events, self.count, self.now, self.link_free = [], 0, 0.0, 0.0
        self.last_arrival = {True: 0.0, False: 0.0}  # 每個方向各自 FIFO

    def at(self, t, fn, *args):
        self.count += 1
        heapq.heappush(self.events, (t, self.count, fn, args))

    def send(self, fn, pkt, paced=False):
        depart = self.now
        if paced:  # 資料方向有頻寬上限：一次只能送出一個封包
            depart = max(self.now, self.link_free)
            self.link_free = depart + LINK_GAP
        if self.rng.random() < self.loss:
            return                                   # 丟包：封包就此消失
        arrive = depart + 50 + self.rng.uniform(0, 10)   # 單程 50～60 ms
        if self.rng.random() < 0.03:
            arrive += 30                     # 3% 走了慢路徑，被後面的封包超車
        else:                                # 其餘照排隊順序抵達，不會互相超車
            arrive = self.last_arrival[paced] = max(arrive, self.last_arrival[paced])
        self.at(arrive, fn, pkt)

    def run(self, done):
        while self.events and not done():
            t, _, fn, args = heapq.heappop(self.events)
            self.now = t
            fn(*args)


class GoBackN:
    """視窗 1 時就是 stop-and-wait。接收端只收按順序的封包。"""

    def __init__(self, ch, window):
        self.ch, self.w = ch, window
        self.base = self.nxt = self.expected = 0
        self.timer_gen = self.retx = self.dup_rx = 0

    def start(self):
        self.fill()

    def fill(self):
        while self.nxt < min(self.base + self.w, N_PKTS):
            self.ch.send(self.on_data, self.nxt, paced=True)
            if self.base == self.nxt:
                self.arm()
            self.nxt += 1

    def arm(self):  # 整個視窗只有一個 timer，掛在最舊的未確認封包上
        self.timer_gen += 1
        self.ch.at(self.ch.now + RTO, self.on_timeout, self.timer_gen)

    def on_data(self, seq):
        if seq == self.expected:
            self.expected += 1
        else:
            self.dup_rx += 1                         # 亂序或重複：直接丟掉
        self.ch.send(self.on_ack, self.expected)     # 累積 ACK：「下一個要 expected」

    def on_ack(self, ack):
        if ack > self.base:
            self.base = ack
            if self.base < self.nxt:
                self.arm()
            else:
                self.timer_gen += 1                  # 全部確認，取消 timer
            self.fill()

    def on_timeout(self, gen):
        if gen != self.timer_gen:
            return
        for seq in range(self.base, self.nxt):       # Go-Back-N：整個視窗重送
            self.ch.send(self.on_data, seq, paced=True)
            self.retx += 1
        self.arm()


class SelectiveRepeat:
    """累積 ACK + SACK；每個封包各自計時；可選 fast retransmit。"""

    def __init__(self, ch, window, fast):
        self.ch, self.w, self.fast = ch, window, fast
        self.base = self.nxt = self.expected = 0
        self.got, self.sacked, self.timers = set(), set(), {}
        self.retx = self.dup_rx = self.dupacks = 0

    def start(self):
        self.fill()

    def xmit(self, seq):
        self.ch.send(self.on_data, seq, paced=True)
        self.timers[seq] = self.timers.get(seq, 0) + 1
        self.ch.at(self.ch.now + RTO, self.on_timeout, seq, self.timers[seq])

    def fill(self):
        while self.nxt < min(self.base + self.w, N_PKTS):
            self.xmit(self.nxt)
            self.nxt += 1

    def on_data(self, seq):
        if seq in self.got or seq < self.expected:
            self.dup_rx += 1
        self.got.add(seq)                            # 亂序的也先存起來
        while self.expected in self.got:
            self.expected += 1
        sack = sorted(s for s in self.got if s > self.expected)
        self.ch.send(self.on_ack, (self.expected, sack))

    def on_ack(self, msg):
        ack, sack = msg
        self.sacked.update(sack)
        if ack > self.base:
            self.base, self.dupacks = ack, 0
            self.fill()
        elif self.base < self.nxt:
            self.dupacks += 1
            if self.fast and self.dupacks == 3 and self.base not in self.sacked:
                self.xmit(self.base)                 # 三個重複 ACK：不等 RTO 先補洞
                self.retx += 1

    def on_timeout(self, seq, gen):
        if self.timers.get(seq) != gen or seq < self.base or seq in self.sacked:
            return
        self.xmit(seq)                               # 只重送這一個
        self.retx += 1


def run(name, make, loss):
    ch = Channel(loss, seed=11)
    proto = make(ch)
    ch.at(0.0, proto.start)
    ch.run(lambda: proto.expected >= N_PKTS)
    secs = ch.now / 1000
    return f"{name:<22}{loss:>5.0%}{ch.now:>9.0f}{N_PKTS / secs:>9.0f}{proto.retx:>7}{proto.dup_rx:>7}"


print(f"{'協定':<20}{'丟包':>4}{'耗時ms':>7}{'pkt/s':>9}{'重傳':>5}{'浪費':>5}")
for loss in (0.0, 0.02, 0.10):
    print(run("stop-and-wait", lambda c: GoBackN(c, 1), loss))
    print(run("Go-Back-N (W=32)", lambda c: GoBackN(c, 32), loss))
    print(run("SR+SACK (W=32)", lambda c: SelectiveRepeat(c, 32, False), loss))
    print(run("SR+SACK+fast retx", lambda c: SelectiveRepeat(c, 32, True), loss))
```

```text
協定                    丟包   耗時ms    pkt/s   重傳   浪費
stop-and-wait            0%    33405        9      0      0
Go-Back-N (W=32)         0%     3773       80    265    265
SR+SACK (W=32)           0%     1133      265      0      0
SR+SACK+fast retx        0%     1139      263      4      3
stop-and-wait            2%    34907        9      7      4
Go-Back-N (W=32)         2%     5286       57    448    435
SR+SACK (W=32)           2%     1766      170      4      0
SR+SACK+fast retx        2%     1522      197      7      2
stop-and-wait           10%    47339        6     69     32
Go-Back-N (W=32)        10%    17066       18   1646   1435
SR+SACK (W=32)          10%     2694      111     29      1
SR+SACK+fast retx       10%     2653      113     37      4
```

先看 0% 丟包的四列，這時差異只來自視窗與亂序。stop-and-wait 花了 33 秒，每秒 9 個封包，正好是「每個 RTT（約 111 ms）一個封包」。SR+SACK 每秒 265 個，套公式：視窗 32 ÷ RTT 約 0.12 秒 ≈ 270，吻合；鏈路本身每秒能送 1000 個，所以這時瓶頸是視窗不是頻寬，把視窗加大吞吐量就會上升。Go-Back-N 在完全不丟包時竟然有 265 次重傳：3% 的亂序封包晚到，接收端把洞後面先到的封包全部丟掉，傳送端只能等逾時再整窗重送。這說明了為什麼「接收端暫存亂序資料」是現代 TCP 的基本功。最後一列 fast retransmit 在 0% 丟包時出現 4 次重傳、3 次浪費：亂序的封包晚到 30 ms，期間有三十幾個封包超車，產生了三個以上重複 ACK，被誤判為遺失。這就是 11.4 節說的「重複 ACK 門檻在亂序時會誤判」，也是 RACK 想改善的問題。

再看 2% 與 10% 丟包。stop-and-wait 的「浪費」欄不是 0，是因為 ACK 也會掉：資料其實到了，ACK 沒回來，傳送端只好重送，接收端收到重複的。Go-Back-N 在 10% 丟包時重傳了 1646 次，是總封包數的五倍多，耗時 17 秒，每一個洞都讓整個視窗重來。SR+SACK 只重傳 29 次，和「300 × 10% ≈ 30」幾乎一樣，表示重傳非常精準；累積 ACK 加上 SACK 讓 ACK 遺失幾乎沒有代價，因為下一個 ACK 會帶上同樣的資訊。加上 fast retransmit 後，2% 丟包時耗時從 1766 ms 降到 1522 ms，因為不必每個洞都等 200 ms 的 RTO；10% 時改善變小，因為洞太多，很多時候湊不滿三個重複 ACK。

> [!tip] 這個模擬沒有的東西
> 真實 TCP 的視窗不是固定的 32，而是由擁塞控制動態調整：丟包會讓擁塞視窗縮小（第 12 章）。所以在真實網路上，10% 丟包對 TCP 吞吐量的傷害遠比這張表嚴重，不只是重傳的成本，而是傳送端會主動慢下來。這也是第 12 章用 Python 模擬 cwnd 的動機。

## 11.7 流量控制：接收端的 window

滑動視窗還有另一個用途：保護接收端。假設錄製服務忙著寫磁碟，讀資料的速度跟不上即時服務送資料的速度，接收緩衝區會被塞滿。如果傳送端不知道，繼續送，多出來的資料只能被丟掉，再由重傳補回，白白浪費頻寬。**流量控制**（flow control）就是接收端在每個 segment 的 Window 欄位宣告「我的緩衝區還剩多少空間」，這個值叫 **rwnd**（receive window），傳送端在路上的資料不能超過它。

要特別分清楚兩個名字很像的機制：流量控制保護的是**接收端**，問題是「對方的應用程式讀得不夠快」；擁塞控制保護的是**網路**，問題是「路上的路由器佇列快滿了」（第 12 章）。前者有明確的訊號（rwnd 欄位），後者只能從丟包、延遲變化去猜。傳送端實際能送的量是兩者中較小的一個。

### Zero window 與 persist timer

接收端的應用程式完全不讀時，緩衝區滿了，就宣告 `win=0`，叫 **zero window**。傳送端必須停下來。這裡有一個潛在的死結：接收端的應用程式之後讀走了資料，會送出一個 **window update**（視窗更新，一個 win 變大的 ACK），但這個 ACK 不帶資料，掉了不會被重傳。如果它真的掉了，接收端以為已經通知過，傳送端還在等，雙方就會永遠僵住。所以傳送端在收到 zero window 後會啟動 **persist timer**，定期送一個很小的 **zero window probe**，逼對方回報目前的視窗。

```text
 Sender                                                  Receiver（應用程式沒在讀）
   │── seq=1  len=32768 ─────────────────────────────────►│  緩衝區 32K/64K
   │── seq=32769 len=32768 ──────────────────────────────►│  緩衝區滿了
   │◄─────────────────────────────── ack=65537 win=0 ─────│  zero window：先別送
   │  （停止送資料，啟動 persist timer）                     │
   │── zero window probe ────────────────────────────────►│
   │◄─────────────────────────────── ack=65537 win=0 ─────│  還是滿的
   │                                                      │  應用程式讀走 48K
   │◄─────────────────────────── ack=65537 win=49152 ─────│  window update
   │── seq=65537 len=32768 ──────────────────────────────►│  恢復傳送
```

時序從上往下：前兩個 segment 把接收端 64K 的緩衝區填滿，接收端回 `win=0`。傳送端停止送資料，但 persist timer 讓它每隔一段時間（同樣指數退避）送 probe，接收端每次都老實回報目前視窗。等應用程式讀走 48K，接收端主動送 window update，傳送端恢復。就算這個 update 掉了，下一個 probe 也會拿到新的視窗值。在 tcpdump 或 Wireshark 裡看到一連串 `win 0`，幾乎可以確定是**接收端的應用程式**讀太慢，不是網路的問題，這是很有用的除錯線索。

接收端還要避免一個病態情況：緩衝區只空出幾個 byte 就宣告小視窗，傳送端就送幾個 byte 的小 segment，header 比資料還大，這叫 **silly window syndrome**。對策是接收端要等空出相當大的空間（例如一個 MSS 或緩衝區的一半）才宣告視窗變大，傳送端也盡量避免送很小的 segment，後者和 11.8 節的 Nagle 演算法是同一個想法。

### Window Scale：16 位元不夠用

Window 欄位只有 16 位元，最多 65535 bytes。由 11.5 節的公式，RTT 150 ms 時最多 65535 × 8 ÷ 0.15 ≈ 3.5 Mbps，跨洋傳大檔案根本跑不快。**Window Scale 選項**（RFC 7323，kind=3）在 SYN 裡協商一個位移量 shift（0～14），之後 Window 欄位的值要乘以 2^shift 才是真正的視窗。shift 最大 14，所以視窗最大約 1 GiB。前面 tcpdump 範例裡的 `win 501`，若協商的 shift 是 7，實際視窗就是 501 × 128 = 64128 bytes。

Window Scale 只在 SYN 交換時出現，所以如果你從連線中途才開始抓封包，Wireshark 不知道 shift 是多少，會顯示「window size scaling factor: -1 (unknown)」，看到的視窗值偏小，不要因此誤判。另一個真實的陷阱是某些老舊的 middlebox（防火牆、負載平衡器）會改寫或剝掉這個選項，結果連線只能用 64 KB 視窗，在長距離連線上吞吐量被卡死，症狀是「同機房很快、跨區很慢，而且頻寬怎麼加都沒用」。

用一段真的 TCP 程式看流量控制的效果：接收端只建立連線、不讀資料，傳送端用非阻塞模式一直塞，直到核心說塞不下：

```python
import socket
import time

# 接收端「只連線、不讀」：看傳送端能塞多少 bytes 進去才被擋住
lsock = socket.create_server(("127.0.0.1", 0))
sender = socket.create_connection(lsock.getsockname())
receiver, _ = lsock.accept()
sender.setblocking(False)                 # 不阻塞：塞不進去就丟 BlockingIOError

def fill(sock):
    total, chunk = 0, b"v" * 16384
    while True:
        try:
            total += sock.send(chunk)
        except BlockingIOError:           # 對方視窗歸零＋自己的送出緩衝也滿了
            return total

first = fill(sender)
print("SO_SNDBUF =", sender.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
      " SO_RCVBUF =", receiver.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
print(f"接收端不讀：傳送端塞了 {first:,} bytes 後被擋住")

drained = 0
receiver.setblocking(False)
for _ in range(8):                        # 應用程式讀走一部分 → 核心會發 window update
    try:
        drained += len(receiver.recv(16384))
    except BlockingIOError:
        break
time.sleep(0.05)                          # 給 window update 一點時間送到傳送端
second = fill(sender)
print(f"接收端讀走 {drained:,} bytes 後：傳送端又能塞 {second:,} bytes")
assert first > 0 and drained > 0
for s in (sender, receiver, lsock):
    s.close()
```

```text
SO_SNDBUF = 384556  SO_RCVBUF = 408300
接收端不讀：傳送端塞了 417,324 bytes 後被擋住
接收端讀走 114,688 bytes 後：傳送端又能塞 908,792 bytes
```

（每次執行的數字不同，也會因作業系統而異。）第一行是兩端 socket 緩衝區的大小。第二行是重點：接收端一個 byte 都沒讀，傳送端塞了幾十萬 bytes 之後，`send()` 拋出 `BlockingIOError`；如果是阻塞模式，`send()` 就會停在那裡不回來。這些資料一部分填進對方的接收緩衝區（直到宣告 zero window），其餘堆在自己的送出緩衝區，所以塞進去的量和兩端緩衝區大小是同一個量級；確切數字受核心的記帳方式影響，不會剛好等於兩者相加。第三行是接收端讀走一部分之後，傳送端又能塞了，中間發生的就是 window update。你可能注意到「又能塞的量」不一定等於讀走的量：現代作業系統會**自動調整**（autotuning）緩衝區大小，連線活躍時把緩衝區調大，所以數字不會剛好對上。這個實驗也說明了一個實務現象：對方不讀時，你的 `send()` 會被阻塞，如果整個服務只有一個 thread 在送，一個慢的 client 就能拖住所有人，這是第 33 章 backpressure 要處理的問題。

## 11.8 Nagle 與 delayed ACK：小封包的取捨

前面的機制都在處理大量資料。互動式流量的問題剛好相反：資料很小、很頻繁。早年 telnet 每按一個鍵就送一個 segment，1 byte 的資料配上 20 bytes 的 IP header 和 20 bytes 的 TCP header，效率只有 1/41，大量這種小封包曾經讓網路擁塞。兩個機制因此誕生，一個在傳送端，一個在接收端，各自都合理，合在一起卻會出事。

**Nagle 演算法**（RFC 896）在傳送端：如果還有已送出但未確認的資料，新的小資料（不滿一個 MSS）先留在緩衝區，等 ACK 回來或湊滿一個 MSS 再送。這樣每個 RTT 最多只會有一個小 segment 在路上，按鍵在等待期間自動合併。**Delayed ACK**（延遲確認，RFC 1122）在接收端：收到資料後不立刻回 ACK，等一小段時間，看看自己有沒有回應資料可以搭便車，或者再收到一個 segment 一起確認。RFC 1122 規定延遲不能超過 500 ms，且每收到兩個完整大小的 segment 至少要回一個 ACK；實際的延遲時間依作業系統而定，Linux 的最小值約 40 ms，Windows 預設常見 200 ms。

```text
 Client（Nagle 開啟）                                      Server（delayed ACK）
   │── send("HDR:") → 沒有未確認資料，立刻送 ────────────────►│  收到 4 bytes，請求還不完整
   │   send("body") → 有未確認資料，Nagle 扣住                  │  沒有回應可以搭便車
   │                                                        │  → 等 delayed ACK timer
   │                    （雙方互相等待）                       │
   │                                                        │  … 約 40 ms（Linux）…
   │◄───────────────────────────────────────────── ACK ─────│  timer 到期，送出 ACK
   │── 收到 ACK，放行 "body" ────────────────────────────────►│  請求完整了
   │◄──────────────────────────────────────────── "K" ──────│  回應
   │   每個請求都固定多了一個 delayed ACK 的時間                 │
```

這就是小晴遇到的第二個問題。client 的第一次 `send()` 因為沒有未確認的資料，立刻送出；第二次 `send()` 時，第一段還沒被確認，Nagle 把它扣住。server 收到 4 bytes 的長度欄位，請求還不完整，應用程式不會回應，所以沒有資料能讓 ACK 搭便車，核心就依 delayed ACK 的規則等待。雙方都在等對方：client 等 ACK 才放行第二段，server 等第二段才會回應。打破僵局的是 server 的 delayed ACK timer，所以每個請求都固定多出一個 timer 的時間。這種「write-write-read」的寫法是 Nagle 加 delayed ACK 最經典的陷阱，症狀是延遲穩穩地多出 40 ms 或 200 ms 的整數倍，而不是隨機抖動。

修法有三種，偏好順序如下。最好的是**在應用層先組好再一次寫出**：把長度和內容拼成一個 bytes 再 `sendall()`，或用 `socket.sendmsg()` 一次送多段，這樣既不會觸發這個陷阱，也省下系統呼叫。其次是設 **TCP_NODELAY** 關掉 Nagle，適合本來就是「一次寫一則完整訊息」的互動協定；很多 RPC 框架與資料庫 driver 預設就會開，Go 語言的 net 套件建立的 TCP 連線預設也是 TCP_NODELAY。不建議的做法是去調 delayed ACK（Linux 有 `TCP_QUICKACK`，但它不是永久設定，用法很容易出錯）。

| 選項 | 作用的一端 | 效果 | 適合 | 注意 |
|---|---|---|---|---|
| Nagle（預設開） | 傳送端 | 有未確認資料時合併小資料 | 大量小寫入、不在意幾十 ms 延遲 | 遇到 write-write-read 會卡 delayed ACK |
| `TCP_NODELAY` | 傳送端 | 關閉 Nagle，資料立刻送 | 互動式協定、RPC、遊戲、即時訊息 | 程式若大量小寫入，會產生大量小封包 |
| `TCP_CORK`（Linux）／`MSG_MORE` | 傳送端 | 主動塞住，湊滿再送 | 先送 header 再送檔案內容 | 忘了拔塞子資料會延遲；非跨平台 |
| Delayed ACK（預設開） | 接收端 | 延遲 ACK 以便合併或搭便車 | 一般流量，減少純 ACK 封包 | 延遲時間依作業系統而定 |
| `TCP_QUICKACK`（Linux） | 接收端 | 暫時立刻回 ACK | 特殊調校 | 不是永久狀態，核心會自動切回 |

## 11.9 動手做：黏包、length-prefix framing 與 TCP_NODELAY

這一節在 127.0.0.1 上用真的 TCP 連線，把 11.2 節與 11.8 節的現象做出來。第一段程式重現黏包，再用 length-prefix 修好，最後看一次大量的 `sendall()` 會被拆成幾次 `recv()`：

```python
import socket
import struct
import threading
import time

MESSAGES = [b"JOIN room=42", b"CHAT hello", b"CHAT \xe8\x80\x81\xe5\xb8\xab\xe5\xa5\xbd"]


def naive_receiver(lsock, out):
    conn, _ = lsock.accept()
    with conn:
        time.sleep(0.1)                  # 模擬應用程式忙了一下才來讀
        out.append(conn.recv(4096))      # 錯誤假設：一次 recv = 一則訊息


def recv_exact(conn, n):
    """TCP 只保證 bytes 的順序，不保證一次 recv 拿到多少，所以要自己湊滿。"""
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError(f"對方在第 {len(buf)}/{n} byte 時關閉連線")
        buf += chunk
    return bytes(buf)


def framed_receiver(lsock, out):
    conn, _ = lsock.accept()
    with conn:
        time.sleep(0.1)
        while True:
            try:
                header = recv_exact(conn, 4)
            except ConnectionError:
                return                    # 在訊息邊界上關閉，屬於正常結束
            (length,) = struct.unpack("!I", header)   # 4 bytes、network byte order
            if length > 1 << 20:
                raise ValueError("訊息太大，拒絕處理")  # 防止惡意長度吃光記憶體
            out.append(recv_exact(conn, length))


def run(receiver, encode):
    lsock = socket.create_server(("127.0.0.1", 0))
    got = []
    t = threading.Thread(target=receiver, args=(lsock, got))
    t.start()
    with socket.create_connection(lsock.getsockname()) as c:
        for m in MESSAGES:
            c.sendall(encode(m))          # 三次獨立的 send
    t.join()
    lsock.close()
    return got


got = run(naive_receiver, lambda m: m)
print("沒有 framing：", len(MESSAGES), "次 send →", len(got), "次 recv")
print("  收到：", got[0])
assert b"".join(got) == b"".join(MESSAGES)   # bytes 一個不少，但邊界不見了

got = run(framed_receiver, lambda m: struct.pack("!I", len(m)) + m)
print("length-prefix：", len(got), "則訊息")
for m in got:
    print("  ", len(m), "bytes →", m.decode())
assert got == MESSAGES

# 反過來：一次 send 的大資料，也可能被拆成很多次 recv
lsock = socket.create_server(("127.0.0.1", 0))
sizes = []
def bulk_reader():
    conn, _ = lsock.accept()
    with conn:
        while (chunk := conn.recv(1 << 20)):
            sizes.append(len(chunk))
t = threading.Thread(target=bulk_reader)
t.start()
with socket.create_connection(lsock.getsockname()) as c:
    c.sendall(b"x" * 4_000_000)          # 一次 sendall 4 MB
t.join()
lsock.close()
print("一次 sendall 4,000,000 bytes →", len(sizes), "次 recv，最大一次", max(sizes), "bytes")
assert sum(sizes) == 4_000_000
```

```text
沒有 framing： 3 次 send → 1 次 recv
  收到： b'JOIN room=42CHAT helloCHAT \xe8\x80\x81\xe5\xb8\xab\xe5\xa5\xbd'
length-prefix： 3 則訊息
   12 bytes → JOIN room=42
   10 bytes → CHAT hello
   14 bytes → CHAT 老師好
一次 sendall 4,000,000 bytes → 82 次 recv，最大一次 459376 bytes
```

第一行：client 做了三次 `send()`，接收端因為先「忙」了 0.1 秒，一次 `recv()` 就把三則訊息全部拿到，第二行印出的 bytes 正是三則黏在一起的樣子，這就是小晴在 log 裡看到的 `Extra data`。注意 `assert b"".join(got) == b"".join(MESSAGES)` 通過了：一個 byte 都沒少、順序也對，TCP 完全履行了承諾，只是邊界不見了。第三到六行是 length-prefix 版本：每則訊息前面加上 `struct.pack("!I", len(m))`，也就是 4 bytes、network byte order（第 2 章）的長度。接收端先 `recv_exact(4)` 讀長度，再 `recv_exact(length)` 讀內容，三則訊息完整切開，連 UTF-8 中文「老師好」也是以 14 bytes 正確還原。`recv_exact` 的迴圈是整個方法的核心：`recv(n)` 只保證最多回傳 n bytes，所以要反覆呼叫直到湊滿；回傳空 bytes 代表對方關閉連線，必須當成錯誤處理，否則會變成無窮迴圈。程式也檢查了長度上限，避免一個惡意或錯誤的長度欄位讓服務嘗試配置幾 GB 的記憶體。

最後一行是反方向的現象：一次 `sendall()` 4 MB，接收端用 `recv(1 << 20)` 一次最多讀 1 MB，結果分成幾十到上百次才讀完（每次執行數字不同），最大一次也遠小於 1 MB。一次 send 會被拆成多次 recv，一次 recv 也可能包含多次 send，兩個方向都要處理。這也順帶說明了 `send()` 與 `sendall()` 的差別：`send()` 回傳實際塞進緩衝區的 bytes 數，可能小於你給的長度，`sendall()` 才會重複呼叫直到全部送出。

第二段程式觀察 Nagle。第一部分做 5000 次 1-byte 的 `send()`，數接收端看到幾次 `recv()`；第二部分重現 11.8 節的 write-write-read，分別在 Nagle 開啟、TCP_NODELAY、以及「一次寫完」三種情況下量來回延遲：

```python
import socket
import statistics
import threading
import time


def start_server(handler):
    lsock = socket.create_server(("127.0.0.1", 0))
    result = {}
    def run():
        conn, _ = lsock.accept()
        with conn:
            handler(conn, result)
    t = threading.Thread(target=run)
    t.start()
    return lsock, t, result


def count_chunks(conn, result):
    result["recvs"] = 0
    while conn.recv(65536):
        result["recvs"] += 1


def request_reply(conn, result):
    buf = b""
    while True:
        while len(buf) < 8:                  # 一個請求 = 4 bytes header + 4 bytes body
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf += chunk
        buf = buf[8:]
        conn.sendall(b"K")                   # 收齊整個請求才回應


def tiny_writes(nodelay):
    """5000 次 1-byte send：Nagle 會把等待 ACK 期間的小資料合併起來送。"""
    lsock, t, result = start_server(count_chunks)
    c = socket.create_connection(lsock.getsockname())
    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, int(nodelay))
    for _ in range(5000):
        c.send(b"x")
    c.close(); t.join(); lsock.close()
    return result["recvs"]


def write_write_read(nodelay, split, rounds=20):
    lsock, t, _ = start_server(request_reply)
    c = socket.create_connection(lsock.getsockname())
    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, int(nodelay))
    samples = []
    for _ in range(rounds):
        start = time.perf_counter()
        if split:
            c.send(b"HDR:")                  # 第一次小寫入
            c.send(b"body")                  # 第二次小寫入：Nagle 會扣住它，等第一段的 ACK
        else:
            c.sendall(b"HDR:body")           # 應用層先組好，一次寫出
        assert c.recv(1) == b"K"
        samples.append((time.perf_counter() - start) * 1000)
    c.close(); t.join(); lsock.close()
    return statistics.median(samples), max(samples)


print("(1) 5000 次 1-byte send，接收端看到幾次 recv：")
for nodelay in (False, True):
    print(f"    TCP_NODELAY={int(nodelay)} → {tiny_writes(nodelay):5d} 次")

print("(2) write-write-read 的來回延遲（20 次）：")
for label, nodelay, split in [("Nagle 開，分兩次寫", False, True),
                              ("TCP_NODELAY，分兩次寫", True, True),
                              ("Nagle 開，一次寫完", False, False)]:
    med, worst = write_write_read(nodelay, split)
    print(f"    {label:<16} 中位數 {med:7.2f} ms，最慢 {worst:7.2f} ms")
```

```text
(1) 5000 次 1-byte send，接收端看到幾次 recv：
    TCP_NODELAY=0 →  1121 次
    TCP_NODELAY=1 →  3855 次
(2) write-write-read 的來回延遲（20 次）：
    Nagle 開，分兩次寫     中位數    0.08 ms，最慢    0.12 ms
    TCP_NODELAY，分兩次寫 中位數    0.07 ms，最慢    0.13 ms
    Nagle 開，一次寫完     中位數    0.06 ms，最慢    0.08 ms
```

這是在一台 macOS 筆電上的實際輸出，你的機器上數字會不同。第一部分很穩定地呈現 Nagle 的合併效果：Nagle 開啟時，5000 次 send 被合併成一千多次 recv；關掉 Nagle 後變成四千次上下，因為每個 byte 幾乎都獨立送出。這裡數的是 recv 次數而不是封包數，兩者不完全相同，但趨勢一致；想看真正的封包數，可以照 11.13 節的練習用 tcpdump 觀察 loopback 介面。

第二部分在 macOS 的 loopback 上，三種寫法都在 0.1 ms 上下，看不出 40 ms 的停頓，因為這台機器在 loopback 上幾乎立刻回 ACK，Nagle 扣住第二段的時間只有一個極短的本機往返。同一段程式拿到 Linux 上跑，「Nagle 開，分兩次寫」那一列常見的結果是中位數約 40 ms，正好是 Linux delayed ACK 的最小值，另外兩列仍在 1 ms 以下。這就是小晴「Linux 上固定慢 40 ms、自己的 Mac 上看不出來」的原因：bug 一直在程式裡，只是不同作業系統的 delayed ACK 行為讓它在某些機器上才現形。這提醒我們，延遲相關的行為一定要在接近 production 的環境量測。小晴最後的修法是把長度與內容組成一個 bytes 一次 `sendall()`，同時對這條內部連線設 TCP_NODELAY。

## 11.10 Keepalive 與「看起來還活著」的連線

最後一個機制處理的是沒有資料的時候。TCP 連線本身沒有心跳：兩端都不送資料時，網路上完全沒有封包。如果對方機器斷電、網路線被拔、或中間的 NAT 裝置把這條連線的對應表項目清掉（第 7 章），活著的一方不會收到任何通知，它的連線狀態仍是 ESTABLISHED，這叫 **half-open connection**（半開連線）。直到它下次送資料，才會開始重傳、最後逾時，或收到對方回的 RST（如果對方重開機了）。只收不送的一方，例如一個靜靜等待推播的 client，可能永遠都不知道連線已經死了。

**TCP keepalive** 是核心內建的探測：連線閒置超過一段時間後，送一個不帶新資料的探測 segment，對方的核心會回 ACK；連續多次沒有回應就判定連線死亡，讓應用程式的 `recv()` 回報錯誤。它由三個參數控制：

| 參數 | Linux sysctl（預設） | 意義 | 每個 socket 的覆寫選項 |
|---|---|---|---|
| 閒置多久開始探測 | `net.ipv4.tcp_keepalive_time`（7200 秒） | 最後一次有資料往來後，等多久送第一個探測 | `TCP_KEEPIDLE`（macOS 為 `TCP_KEEPALIVE`） |
| 探測間隔 | `net.ipv4.tcp_keepalive_intvl`（75 秒） | 沒回應時，隔多久再送下一個 | `TCP_KEEPINTVL` |
| 探測次數 | `net.ipv4.tcp_keepalive_probes`（9 次） | 連續幾次沒回應就判定死亡 | `TCP_KEEPCNT` |
| 開關 | 無（每個 socket 自己開） | keepalive 預設關閉 | `SO_KEEPALIVE` |

預設值非常保守：閒置兩小時才開始探測，再加 9 × 75 秒，大約要兩小時又十一分鐘才發現對方死了。而且 keepalive 預設是關的，要每個 socket 自己開。更麻煩的是，雲端 load balancer、NAT gateway、防火牆通常有自己的閒置逾時（各家預設值不同，常見是幾分鐘等級），遠短於兩小時，所以只靠預設 keepalive，連線往往在第一個探測送出前就已經被中間設備默默清掉了。下面示範在 Python 裡把參數調短：

```python
import socket
import sys

lsock = socket.create_server(("127.0.0.1", 0))
c = socket.create_connection(lsock.getsockname())
conn, _ = lsock.accept()

c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)       # 開關：預設關閉
# 「閒置多久開始探測」的選項名稱各平台不同：Linux 是 TCP_KEEPIDLE，macOS 是 TCP_KEEPALIVE
idle_opt = getattr(socket, "TCP_KEEPIDLE", None) or getattr(socket, "TCP_KEEPALIVE", None)
settings = {"idle": (idle_opt, 60)}
for name, value in (("TCP_KEEPINTVL", 10), ("TCP_KEEPCNT", 3)):
    if hasattr(socket, name):
        settings[name] = (getattr(socket, name), value)
for label, (opt, value) in settings.items():
    if opt is not None:
        c.setsockopt(socket.IPPROTO_TCP, opt, value)
        print(f"{label:<14}= {c.getsockopt(socket.IPPROTO_TCP, opt)}")
print("SO_KEEPALIVE  =", c.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE) != 0)
print(f"最慢偵測到斷線：60 + 10 × 3 = {60 + 10 * 3} 秒（平台：{sys.platform}）")
assert c.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE) != 0
for s in (c, conn, lsock):
    s.close()
```

```text
idle          = 60
TCP_KEEPINTVL = 10
TCP_KEEPCNT   = 3
SO_KEEPALIVE  = True
最慢偵測到斷線：60 + 10 × 3 = 90 秒（平台：darwin）
```

程式先用 `SO_KEEPALIVE` 開啟 keepalive，再把閒置時間設為 60 秒、間隔 10 秒、3 次，最壞情況 90 秒內就能發現連線死亡。「閒置多久」這個選項在 Linux 叫 `TCP_KEEPIDLE`，在 macOS 叫 `TCP_KEEPALIVE`，所以程式用 `getattr` 依平台選擇，這也是寫跨平台網路程式時常見的小麻煩。輸出的 `getsockopt` 值確認設定已生效。在真實服務裡，閒置時間要設得比路徑上最短的中間設備閒置逾時還短，這樣探測封包本身就能讓 NAT 與 load balancer 的表項目保持新鮮。

TCP keepalive 只能證明「對方的核心還在」，不能證明「對方的應用程式還正常」：一個卡死在無窮迴圈的程式，它的核心照樣會回 keepalive 的 ACK。所以面向使用者的長連線協定多半在應用層做心跳，例如 WebSocket 的 ping／pong（第 32 章）、HTTP/2 的 PING frame（第 22 章）、gRPC 的 keepalive。另一個常被搭配使用的是 Linux 的 `TCP_USER_TIMEOUT`，它限制「送出的資料最多可以多久沒被確認」，可以讓正在傳資料的連線在網路斷掉時更快失敗，而不是等上 11.4 節提到的十幾分鐘。

## 11.11 在工作上怎麼用

**設計內部 TCP 協定時（後端）**：先問自己是不是真的需要自訂協定，HTTP、gRPC、WebSocket 都已經解決了 framing、逾時與錯誤處理。如果真的要自己來，檢查清單如下：framing 方式明確寫進協定文件；長度欄位有上限；接收端用緩衝區累積並以迴圈切訊息，不假設一次 recv 等於一則訊息；寫入時一次組好完整訊息再 `sendall()`；互動式請求回應設 TCP_NODELAY；每個讀寫都有逾時；連線斷掉時能區分「訊息邊界上的正常關閉」與「訊息讀到一半就斷」。

**延遲固定多出 40 ms 或 200 ms（後端、SRE）**：看到延遲分布在 40 ms 或 200 ms 附近有一個尖峰，而不是平滑的長尾，第一個懷疑對象就是 Nagle 加 delayed ACK。確認方法是對那條連線抓封包，看是否有「小 segment → 等待約 40 ms → 純 ACK → 下一個小 segment」的節奏，再檢查程式是否分多次寫入一個請求。

```bash
# 在 Linux 上觀察某個 port 的連線細節（示意輸出）
ss -tin 'sport = :8000'
#   ESTAB 0 0 10.20.1.5:8000 10.20.3.7:51514
#     cubic wscale:7,7 rto:204 rtt:2.1/0.8 ato:40 mss:1448 cwnd:10
#     bytes_acked:52133 bytes_received:8812 retrans:0/3 rcv_space:14480
# rto：目前的 RTO（ms）；rtt：SRTT/RTTVAR；ato：delayed ACK timeout；
# retrans：目前未確認的重傳數 / 累計重傳數；wscale：雙方的 window scale

# 全機的重傳統計，隔一段時間看兩次比較差值
nstat -az TcpRetransSegs TcpOutSegs
```

**監控重傳率（SRE）**：重傳率（重傳 segment 數 ÷ 送出 segment 數）是網路健康的重要指標，在資料中心內通常很低，突然上升代表路徑上有丟包、壅塞或設備故障。用 `nstat` 或 node exporter 一類工具收集 `TcpRetransSegs` 與 `TcpOutSegs`，依目的地或 availability zone 分組看，比單一全機數字更能定位問題。`ss -ti` 裡單一連線的 `retrans` 與 `rto` 則適合追查特定使用者的抱怨，例如 Joe 那位學生的 rto 一路翻倍。

**跨區傳大檔案很慢（後端、SRE）**：先算一下視窗需求：目標頻寬 × RTT。如果需要的視窗超過 64 KB，確認 window scale 有協商成功（看 SYN 或 `ss` 的 `wscale`），以及 `net.ipv4.tcp_rmem`、`tcp_wmem` 的上限夠大，應用程式也沒有自己把 `SO_RCVBUF` 設得很小（手動設定會關掉該 socket 的 autotuning）。視窗夠大還是慢，再往第 12 章的擁塞控制方向查。

**用 Wireshark 讀重傳（所有角色）**：Wireshark 會自動分析 TCP 並標記異常，常用的顯示過濾條件有 `tcp.analysis.retransmission`、`tcp.analysis.fast_retransmission`、`tcp.analysis.duplicate_ack`、`tcp.analysis.zero_window`、`tcp.analysis.out_of_order`。判斷流程：先看重傳集中在哪個方向；有大量 zero window 就去查接收端應用程式；重傳伴隨 SACK 區塊表示中間有丟包；只有逾時重傳、沒有重複 ACK，常是 tail loss 或整段路徑斷掉。

**長連線的存活（即時服務、影音）**：聲聲 Live 的教室聊天走 WebSocket，經過 CDN、load balancer、nginx 好幾層，每層都有閒置逾時。應用層心跳的間隔要短於路徑上最短的那個逾時，並且 client 要能偵測心跳逾時後重連（第 33 章）。影音媒體則不走 TCP：一個遺失的封包會讓後面所有資料都等重傳，對即時影音來說，晚到的畫面等於沒用，所以 WebRTC 用 UDP 上的 RTP，自己選擇性地做 NACK 重傳（第 34、37 章）；SRT 則在 UDP 上做了一套有延遲上限的 ARQ，概念和本章的 selective repeat 相同（第 38 章）。

## 11.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| JSON 解析出現 `Extra data` 或內容被截斷，本機測不出來 | 把 TCP 當成訊息導向，假設一次 recv 等於一則訊息 | 印出每次 recv 的長度與內容，加大負載或在接收端加延遲重現 | 實作 framing（length-prefix 或分隔符號），接收端用緩衝區累積後切訊息 |
| 請求延遲固定多出約 40 ms（Linux）或 200 ms | Nagle 加 delayed ACK，程式分多次小寫入一個請求 | 抓封包看小 segment 之後是否等待一個固定時間才有 ACK；檢查是否 write-write-read | 組好完整訊息一次 `sendall()`；互動式協定設 TCP_NODELAY |
| 傳輸偶爾卡住好幾秒才繼續 | 連續丟包觸發 RTO 指數退避，或 tail loss 只能等 RTO | `ss -ti` 看 rto 與 retrans；Wireshark 看是否只有逾時重傳、沒有重複 ACK | 查路徑丟包來源（Wi-Fi、壅塞的鏈路）；確認 SACK、RACK-TLP 沒被關掉 |
| 跨區傳輸吞吐量卡在幾 Mbps，加頻寬沒用 | 視窗太小：window scale 被 middlebox 剝掉，或 SO_RCVBUF 設太小 | 抓 SYN 看 wscale 選項；用 W ÷ RTT 對照實際吞吐量 | 修正 middlebox 設定；不要手動設小 buffer，讓 autotuning 運作；調整 tcp_rmem 上限 |
| 封包分析看到大量 `win 0`，傳輸斷斷續續 | 接收端應用程式讀得太慢，緩衝區滿了 | Wireshark 過濾 `tcp.analysis.zero_window`；看接收端 CPU、磁碟與 thread 是否阻塞 | 接收端改用非同步讀取或加快處理；加 backpressure 機制（第 33 章） |
| 服務 thread 卡在 `send()` 不回來 | 對方不讀，雙方緩衝區都滿了，阻塞式 send 等待 | 用 py-spy 或 thread dump 看卡住的位置；`ss` 看 Send-Q 是否很大 | 設寫入逾時；用非阻塞或 asyncio；慢 client 要能被斷開 |
| 拔網路線或對方當機後，連線很久才報錯，或永遠不報錯 | TCP 沒有心跳；keepalive 預設關閉且預設時間長達兩小時 | `ss -to` 看 timer 欄位；檢查是否有開 SO_KEEPALIVE | 開 keepalive 並調短參數，或實作應用層心跳；需要時用 TCP_USER_TIMEOUT |
| 閒置一段時間的連線，下一次請求失敗或收到 RST | 中間的 NAT、LB、防火牆閒置逾時清掉了連線 | 比對失敗前的閒置時間與各層的 idle timeout 設定 | keepalive 或心跳間隔短於最短的閒置逾時；client 對連線池中的閒置連線做重試 |

## 11.13 動手練習

1. **延伸模擬：自適應 RTO。** 把 11.6 節程式的固定 `RTO = 200.0` 改成依 RFC 6298 計算（可以直接用 11.4 節的公式），用每個封包送出到收到 ACK 的時間當樣本，並遵守 Karn 演算法（重傳過的封包不取樣）。觀察 SR+SACK 在 10% 丟包時的耗時是否改變。驗證方法：印出最終的 SRTT，應該接近 110～120 ms；RTO 應落在 SRTT 之上一段距離，而不是固定 200。

2. **驗證「吞吐 ≈ W ÷ RTT」。** 在 11.6 節的程式中，以 0% 丟包、SR+SACK，分別跑視窗 4、8、16、32、64、128。答案要點：視窗小時吞吐量幾乎與 W 成正比（每秒約 W ÷ 0.115 個封包）；視窗大到一定程度後，吞吐量會停在鏈路上限每秒 1000 個附近，這時瓶頸從視窗變成頻寬。這個轉折點就是第 12 章的 bandwidth-delay product。

3. **改用分隔符號 framing。** 把 11.9 節的 length-prefix 改成以 `\n` 分隔，接收端用 `conn.makefile("rb").readline()` 讀取。再送一則內容含有換行字元的訊息，觀察會發生什麼，並設計一種跳脫方式解決。答案要點：含換行的訊息會被切成兩則；常見解法是先把內容做 JSON 編碼（JSON 字串裡的換行會變成 `\n` 兩個字元），這正是 NDJSON 的做法。

4. **用 tcpdump 看 loopback 上的 Nagle。** 把 11.9 節第二段程式的 port 固定（例如改成 `("127.0.0.1", 18080)`），在另一個終端機執行 `sudo tcpdump -i lo0 -nn 'tcp port 18080'`（Linux 介面名稱是 `lo`）。比較 TCP_NODELAY 開與關時，每個封包的 `length` 欄位。驗證方法：Nagle 開啟時會看到 length 大於 1 的 segment（多個 byte 被合併），關閉時大多是 length 1。若你有 Linux 機器，也觀察 write-write-read 那段，量出 ACK 前的等待時間。

5. **觀察 zero window。** 修改 11.7 節的程式，讓傳送端改用阻塞模式在另一個 thread 一直送，接收端每秒只讀 4 KB。執行時用 `ss -tn` 觀察兩端的 Recv-Q 與 Send-Q，並用 tcpdump 抓 `win 0` 的封包。答案要點：接收端 Recv-Q 接近接收緩衝區大小、傳送端 Send-Q 持續很大；封包中會看到 zero window 與週期性的 probe。

6. **追蹤一段序號。** 用 `curl -v` 對本機 `python3 -m http.server --bind 127.0.0.1` 下載一個約 1 MB 的檔案，同時用 tcpdump 加 `-S`（顯示絕對序號）抓封包。從 SYN 的 ISN 開始，手算第一個資料 segment 的 seq，以及 server 第一次回應的 ack 值。驗證方法：第一個資料 byte 的序號應該是 ISN+1，client 的 HTTP 請求長度加上 ISN+1 應等於 server 回應中的 ack 值。

## 本章重點整理

- TCP 提供可靠、有序、不重複的 byte stream，但不保留訊息邊界；一次 send 可能被拆成多次 recv，多次 send 也可能被一次 recv 讀到。
- 在 TCP 上傳訊息一定要有 framing，常見做法是分隔符號、length-prefix 與自描述 header；接收端必須累積 bytes、以迴圈湊滿完整訊息，並限制最大長度。
- TCP 替每個 byte 編上 32 位元序號，ACK 寫的是期待的下一個 byte（累積確認）；SYN 與 FIN 各佔一個序號，序號比較要用模 2^32 的方式。
- TCP 的 ACK 只代表對方核心收到資料，不代表對方應用程式處理完畢，需要時要在應用層再做確認。
- RTO 由 SRTT 加四倍 RTTVAR 計算，連續逾時會指數退避；Karn 演算法與 Timestamps 選項解決重傳時 RTT 樣本的模糊。
- 三個重複 ACK 觸發 fast retransmit，不必等 RTO；SACK 讓接收端回報洞後面收到的區塊，傳送端能一次補上多個洞，現代 Linux 另用 RACK-TLP 改善亂序與 tail loss。
- 滑動視窗讓多個 segment 同時在路上，吞吐量約等於視窗除以 RTT；stop-and-wait 就是視窗為 1 的特例。
- Go-Back-N 在丟包或亂序時會整窗重送，selective repeat 只重送真正遺失的；現代 TCP 採累積 ACK 加 SACK 的混合設計。
- 流量控制以 rwnd 保護接收端，擁塞控制保護網路，實際可送量取兩者較小值；看到大量 zero window 代表接收端應用程式讀太慢。
- Window 欄位只有 16 位元，要靠 SYN 協商的 Window Scale 才能超過 64 KB，否則長距離連線的吞吐量會被卡死。
- Nagle 演算法與 delayed ACK 遇到 write-write-read 會造成固定約 40 ms 或 200 ms 的延遲；最好的修法是一次寫出完整訊息，互動式協定再加 TCP_NODELAY。
- TCP 連線閒置時沒有任何封包，對方消失時可能長時間無法察覺；keepalive 預設關閉且時間很長，長連線應調短 keepalive 或在應用層做心跳，間隔要短於中間設備的閒置逾時。

## 延伸問答

> [!question]- Q1. 「黏包」是 TCP 的缺陷嗎？用 UDP 是不是就沒有這個問題？
> 不是缺陷，而是 byte stream 的定義。TCP 的設計目標是讓應用程式像讀寫檔案一樣使用網路：檔案也沒有「一次 write 對應一次 read」的保證，TCP 同樣沒有。正因為不需要保留邊界，TCP 才能自由地合併小資料（Nagle）、依 MSS 切大資料、在重傳時重新切分，這些都讓傳輸更有效率。所以問題出在應用程式把 TCP 當成訊息導向在用。
>
> UDP 確實保留邊界，一個 datagram 就是一則訊息，不會黏在一起。但你同時失去了可靠與有序，還要自己處理訊息超過 MTU 時的分片問題（第 8 章）。如果你需要的是「可靠的訊息」，正確答案通常是在 TCP 上加 framing，或直接用已經做好 framing 的協定，例如 WebSocket、gRPC；而 QUIC（第 13 章）提供多條獨立的 stream，每條 stream 本身仍是 byte stream，還是需要 framing。

> [!question]- Q2. 手算：RTT 150 ms、segment 1448 bytes，stop-and-wait 的吞吐量是多少？要跑滿 50 Mbps，視窗至少要多大？
> stop-and-wait 每個 RTT 只能送一個 segment：1448 bytes × 8 ÷ 0.15 秒 ≈ 77,227 bps，約 77 kbps。這與鏈路頻寬無關，就算是 10 Gbps 的線路也一樣，瓶頸完全在等待。
>
> 要跑滿 50 Mbps，由「吞吐量 ≈ W ÷ RTT」得 W ≈ 50,000,000 bps × 0.15 秒 ÷ 8 ≈ 937,500 bytes，大約 916 KiB，相當於約 648 個 segment 同時在路上。這遠超過 Window 欄位的 65535 上限，必須依賴 Window Scale：shift 至少要 4（65535 × 16 ≈ 1 MB）。同時接收端的緩衝區要能容納這麼多資料、傳送端的擁塞視窗也要長到這麼大（第 12 章）。這個「頻寬 × RTT」的量就是 bandwidth-delay product，它告訴你一條路徑上需要有多少資料在飛，才能把管子填滿。

> [!question]- Q3. 你在 production 看到某個內部服務的 p50 延遲是 41 ms，但同機房 ping 只要 0.3 ms，服務本身處理時間不到 1 ms。你會怎麼查？
> 這組數字很可疑：延遲遠大於網路 RTT 與處理時間的總和，而且接近 40 ms 這個整數，第一個假設就是 Nagle 加 delayed ACK。Linux 的 delayed ACK 最小約 40 ms，write-write-read 的寫法會讓每個請求固定多出這段時間。
>
> 確認方法：先檢查 client 程式是否把一個請求分成多次寫入（例如先寫 header、再寫 body，或用沒有緩衝的 writer 逐欄寫入）。再用 tcpdump 抓一段流量，看是否出現「client 送一個小 segment → server 約 40 ms 後才回純 ACK → client 才送下一段」的節奏。如果確認，修法是在 client 端把完整請求組好一次送出，並為這條連線設 TCP_NODELAY；修完後延遲應該直接掉到 1 ms 左右。如果延遲分布不是集中在 40 ms，而是寬廣的長尾，就要改查重傳（`ss -ti` 的 retrans）或服務端的排隊。

> [!question]- Q4. tcpdump 中看到傳送端連續收到 `ack 52001` 四次，其中第二次之後帶有 `sack 1 {53449:56345}`，接著傳送端重送了 `seq 52001`。請解讀發生了什麼事。
> `ack 52001` 重複出現，表示接收端一直在等序號 52001 開始的資料，也就是那裡有一個洞。SACK 區塊 `{53449:56345}` 說明 53449 到 56344 這段已經收到，所以洞的範圍是 52001～53448，正好 1448 bytes，也就是一個 MSS 大小的 segment 掉了。後面的 segment 照常到達，每到一個就產生一個重複 ACK。
>
> 傳送端在累積到三個重複 ACK 時觸發 fast retransmit，不等 RTO 就重送 52001。有 SACK 資訊時，傳送端也能確認 53449 之後的資料不必重送，只補這一個洞。如果 SACK 區塊後來繼續增長、但 ack 值一直不動，表示重傳的那份也可能掉了，最後會退回 RTO 逾時。在 Wireshark 裡這段會被標記為 duplicate ACK 與 fast retransmission，判斷時也要看重傳發生在哪個方向，才能推斷丟包發生在哪一段路徑。

> [!question]- Q5. 為什麼 TCP 用累積 ACK，而不是像教科書的 selective repeat 一樣逐個確認每個 segment？
> 累積 ACK 最大的好處是「ACK 遺失沒有代價」。每個累積 ACK 都包含之前所有 ACK 的資訊，就算中間掉了幾個，下一個到達的 ACK 就能把進度補上，傳送端不需要為了 ACK 遺失而重傳資料。逐個確認的設計則必須小心處理 ACK 遺失：某個 segment 的 ACK 掉了，傳送端會誤以為資料沒到而重送。
>
> 累積 ACK 也讓 ACK 很精簡、可以延遲合併（delayed ACK 一次確認兩個 segment），並且在 TCP 的 byte stream 模型裡很自然：只要一個數字就描述了「連續收到到哪裡」。它的弱點是無法描述洞後面的情況，所以後來加了 SACK 作為補充資訊，而不是取代累積 ACK。現代 TCP 的設計可以理解為：累積 ACK 是可靠的主幹，SACK 是幫助快速、精準重傳的提示。11.6 節的模擬也顯示，SR+SACK 的重傳數幾乎等於實際丟失的資料封包數，ACK 遺失幾乎沒有造成額外重傳。

> [!question]- Q6. 面試題：TCP 既然保證可靠傳輸，為什麼訊息佇列、支付 API 還需要應用層的 ACK 或 idempotency key？
> 因為 TCP 的可靠只涵蓋「兩個核心的緩衝區之間」。TCP ACK 由接收端核心送出，表示資料已進入接收緩衝區，此時應用程式可能還沒讀，讀了也可能在處理到一半時當機。對寄件方來說，收到 TCP ACK 並不代表「訊息已被處理」。此外，連線斷掉時，傳送端無法得知最後一段資料是否已被對方處理：可能請求到了、處理了，只是回應在路上掉了。
>
> 這就是 end-to-end argument：可靠性必須由兩端的應用自己確認。訊息佇列用 consumer ack，處理完才確認，沒確認就重新投遞；支付 API 讓 client 在重試時帶同一個 idempotency key（第 24 章），server 看到重複的 key 就回傳上次的結果而不重複扣款。TCP 的可靠性讓這些應用層機制少處理很多情況，但無法取代它們。

> [!question]- Q7. 聲聲 Live 的即時服務要偵測斷線的學生，應該用 TCP keepalive 還是應用層心跳？
> 對這個情境，應用層心跳比較適合，TCP keepalive 可以當補充。理由有三。第一，TCP keepalive 只能確認對方核心還活著，學生的瀏覽器分頁卡住、或 JavaScript 迴圈當掉時，核心仍會回應 keepalive，伺服器偵測不到。第二，瀏覽器的 JavaScript 無法設定 TCP socket 選項，client 端不能自己開 keepalive，而且中間經過 CDN、load balancer、nginx 好幾層，伺服器那端的 TCP 連線其實是連到 proxy，不是學生本人。第三，應用層心跳可以帶上應用資訊，例如最後收到的訊息編號，順便用於重連後補發（第 33 章）。
>
> 實作上，WebSocket 已有 ping／pong frame（第 32 章），伺服器定期送 ping，超過幾次沒有 pong 就判定離線並更新 presence。心跳間隔要短於路徑上最短的閒置逾時，以免連線先被中間設備清掉。至於伺服器與內部服務之間的長連線（例如連到資料庫或錄製服務），開 TCP keepalive 並調短參數仍然是低成本、值得做的保護。

> [!question]- Q8. 既然逾時越短越快發現丟包，為什麼不把 RTO 固定設成 10 ms？
> 因為 RTO 小於實際 RTT 時，每個 segment 在 ACK 回來前就會逾時，造成大量不必要的重傳。這些重傳不只浪費頻寬，還會讓傳送端誤以為網路擁塞而縮小擁塞視窗，吞吐量反而大跌；極端情況下，網路被重複資料塞滿，造成更多延遲與逾時，形成惡性循環，這正是 1980 年代網際網路曾發生的 congestion collapse 的成因之一。跨洋連線的 RTT 常在 100 ms 以上，Wi-Fi 上的 RTT 也會短暫飆高，固定 10 ms 在這些路徑上一定會出問題。
>
> 所以 RTO 必須依每條連線量測到的 RTT 動態計算，並加上反映抖動的安全邊際（4 × RTTVAR），同時保留一個下限。真正需要「快速發現丟包」的時候，TCP 用的是另一條路：fast retransmit、SACK 與 RACK-TLP，從 ACK 的內容推斷遺失，通常在大約一個 RTT 內就能反應，而不需要冒險縮短 RTO。

## 延伸閱讀

- RFC 9293〈Transmission Control Protocol (TCP)〉：TCP 主規格，序號、ACK、視窗與 header 欄位的權威定義。
- RFC 6298〈Computing TCP's Retransmission Timer〉：SRTT、RTTVAR、RTO 計算與退避規則。
- RFC 5681〈TCP Congestion Control〉：包含重複 ACK 與 fast retransmit／fast recovery 的定義，也是第 12 章的基礎。
- RFC 2018〈TCP Selective Acknowledgment Options〉與 RFC 2883〈An Extension to the Selective Acknowledgement (SACK) Option for TCP〉（D-SACK）。
- RFC 8985〈The RACK-TLP Loss Detection Algorithm for TCP〉。
- RFC 7323〈TCP Extensions for High Performance〉：Window Scale、Timestamps 與 PAWS。
- RFC 896〈Congestion Control in IP/TCP Internetworks〉（Nagle 演算法）與 RFC 1122〈Requirements for Internet Hosts -- Communication Layers〉（delayed ACK、keepalive 的要求）。
- Kevin R. Fall、W. Richard Stevens《TCP/IP Illustrated, Volume 1》第二版；James Kurose、Keith Ross《Computer Networking: A Top-Down Approach》中 Go-Back-N 與 selective repeat 的章節。
