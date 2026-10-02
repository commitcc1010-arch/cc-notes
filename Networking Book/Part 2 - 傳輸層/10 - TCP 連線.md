---
chapter: 10
title: TCP 連線：交握、狀態與關閉
part: 2
---

# 第 10 章　TCP 連線：交握、狀態與關閉

> [!abstract] 本章地圖
> **核心問題**：一條 TCP 連線從誕生到消失，兩端的核心各自經歷了哪些狀態？出事時，怎麼從這些狀態看出是誰的錯？
>
> **你會學到**：
> - 逐欄讀懂 TCP header，看懂 tcpdump 裡的 `Flags [S.]`、seq、ack 與 options
> - 說清楚三向交握為什麼是三次、ISN 為什麼要隨機，以及 connect 被拒絕和逾時的差別
> - 解釋 `listen()` 的 backlog、SYN queue 與 accept queue，並用 `ss -ltn` 判斷 accept queue 是否爆了
> - 畫出四次揮手與完整狀態機，分辨 TIME_WAIT（正常的保險）與 CLOSE_WAIT（應用程式的 bug）
> - 知道 RST 在什麼情況出現，把 `ECONNREFUSED`、`ECONNRESET`、`EPIPE`、逾時對應回網路上發生的事
> - 用 Python 在 127.0.0.1 上重現半關閉、RST、accept queue 滿、CLOSE_WAIT 堆積與 TIME_WAIT 擋住重啟，並寫出修正版
>
> **前置知識**：第 2 章（封裝與 header）、第 3 章（ss、tcpdump 的基本用法）、第 9 章（port、五元組與 socket API）

## 10.1 故事：晚上八點的「進入教室」按鈕

聲聲 Live 的課程多半排在晚上八點整開始。七點五十八分，上千名學生幾乎同時按下「進入教室」，瀏覽器呼叫 `api.shengsheng.example` 的教室入口 API；這支 Flask 程式跑在 gunicorn 上，每次都要向內部的課表服務（10.20.3.15:8080）確認這堂課的老師與教室編號。上週，為了省下每次重新連線的時間，團隊替課表服務的呼叫加了一個自己寫的連線池（connection pool，把用過的連線留著給下一個請求重用）。

這週二晚上八點零一分，告警響了：教室入口 API 的 5xx 比例衝到 30%。小晴剛入職三週，第一次值班，打開 log 看到兩種錯誤混在一起：nginx 寫著 `upstream timed out (110: Connection timed out) while connecting to upstream`，gunicorn 的 worker 則印出 `OSError: [Errno 24] Too many open files`。小晴的第一個念頭是「課表服務掛了」，但課表服務的儀表板一切正常，CPU 只有 15%。

資深平台工程師阿德遠端加入，沒有先看程式，而是登進 API 主機打了兩行指令：`ss -ltn` 和 `ss -tan state close-wait | wc -l`。第一行顯示 gunicorn 的 listening socket 的 `Recv-Q` 是 2049、`Send-Q` 是 2048；第二行印出 3,812。阿德說：「accept queue 滿了，而且有將近四千條連線卡在 CLOSE_WAIT。課表服務沒掛，是我們自己沒把連線關掉。」小晴聽得一頭霧水：TCP 連線不是 connect 一下、close 一下就好了嗎？什麼是 accept queue？CLOSE_WAIT 又是誰的狀態？

```text
 學生瀏覽器 ──HTTPS──► LB ──► nginx ──► gunicorn（Flask：教室入口 API）──► 課表服務 10.20.3.15:8080
                              │         │                                  │
                              │         │ ① listening socket：             │ ③ 連線閒置 60 秒
                              │         │   Recv-Q 2049／Send-Q 2048       │   就主動 close()
                              │         │   （accept queue 滿了）          │
                              │         │ ② 連線池裡 3,812 條 CLOSE_WAIT   │
                              │         │   → fd 用光 → accept() 失敗      │
                              ▼
                     ④ nginx 連不上 upstream → 回 504 給學生
```

這張圖是阿德在事後檢討會上畫的因果鏈，要從右往左讀。③ 課表服務對閒置超過 60 秒的連線主動關閉，這是完全正常的行為。② 我們的連線池沒有發現對方已經關閉，也沒有呼叫 `close()`，於是每條連線都停在 CLOSE_WAIT，佔著一個檔案描述符（file descriptor，簡稱 fd，作業系統給每個開啟的檔案或 socket 的編號）。fd 用到上限後，gunicorn 連 `accept()` 都失敗，① 已經完成交握的新連線只能在 accept queue 裡排隊，佇列滿了以後新的連線請求被丟掉。④ 最後 nginx 等不到交握完成，只好回 504。

這一章就是要讓你看懂這張圖裡的每一個名詞。不懂 TCP 連線的狀態，你只能看到「逾時」和「開太多檔案」兩個看似無關的錯誤，然後去重開服務；懂了以後，你會知道 CLOSE_WAIT 永遠指向「本機的應用程式沒有 close」，accept queue 滿永遠指向「應用程式來不及 accept」，而 TIME_WAIT 多半只是正常現象。章末的動手做會在你的電腦上把這場事故縮小重現一次，再把它修好。

## 10.2 TCP 連線到底是什麼

在第 9 章我們用過 UDP：每個 datagram 獨立送出，送了就不管。TCP 則提供一條**連線**（connection）：兩端在傳資料之前先互相確認、約定好起始序號，之後的資料保證**依序、不重複、不遺失**地交給對方的應用程式，兩個方向還能同時傳（**全雙工**，full duplex，例如教室聊天時學生在送訊息的同時也在收老師的訊息）。

一個常見的誤解是「連線是一條從 client 拉到 server 的線路」。實際上，中間的路由器、交換器完全不知道有這條連線存在，它們只看到一個個獨立的 IP 封包。所謂的連線，其實是**兩端的核心各自保存的一份狀態**：TCP 規格稱它為 **TCB**（Transmission Control Block，傳輸控制區塊），裡面記著目前的狀態（例如 ESTABLISHED）、自己送到第幾號 byte、對方送到第幾號 byte、收送 buffer、各種計時器。核心用**四元組**（來源 IP、來源 port、目的 IP、目的 port）找到某個封包屬於哪一個 TCB；例如 `10.20.1.25:51514 → 10.20.3.15:8080` 就是一條連線，同一台機器換一個來源 port 51515 就是另一條。

這個「狀態只存在兩端」的設計帶來三個後果，本章會反覆遇到。第一，兩端的狀態可能不一致：一端以為連線還在，另一端早就重開機忘了它，這叫**半開連線**（half-open connection）。第二，因為狀態要建立、也要拆除，所以開與關都需要交換封包，這就是交握與揮手。第三，狀態拆除要靠應用程式配合：核心不會替你決定什麼時候 close，應用程式忘了，狀態就一直留著，這正是故事裡 CLOSE_WAIT 的成因。

應用程式不會直接看到 TCP segment（TCP 把資料切成的一段一段，加上 TCP header 的單位，叫 **segment**），而是透過 socket API 操作。下表把第 9 章學過的 socket 呼叫，對應到核心在 TCP 層做的事，之後每一節都會回來對照。

| socket 呼叫 | 核心做的事 | 網路上看到的 segment | 本機狀態變化 |
|---|---|---|---|
| `listen(backlog)` | 建立 SYN queue 與 accept queue | 無 | CLOSED → LISTEN |
| `connect()` | 選 ISN、送 SYN、等待回應 | SYN →、← SYN+ACK、ACK → | CLOSED → SYN_SENT → ESTABLISHED |
| `accept()` | 從 accept queue 取出一條已完成交握的連線 | 無（交握早就做完了） | 無，只是交給應用程式 |
| `send()`／`recv()` | 把資料放進送出 buffer／從接收 buffer 取出 | 資料 segment 與 ACK | 不變 |
| `shutdown(SHUT_WR)` | 送 FIN，表示「我不再送資料」 | FIN → | ESTABLISHED → FIN_WAIT_1 |
| `close()` | 釋放 fd；若是最後一個參考，送 FIN（或 RST） | FIN → 或 RST → | 依情況進入 FIN_WAIT_1 或 LAST_ACK |

這張表裡最值得注意的是 `accept()` 那一列：它**不會**觸發任何封包。交握是核心自己完成的，應用程式呼叫 `accept()` 時只是把「已經建好的連線」從佇列領走。這一點是理解 backlog 與故事裡 accept queue 爆掉的關鍵，10.5 節會詳細拆解。

## 10.3 TCP header：每一個欄位都有用途

要讀懂交握與揮手，先要看懂每個 segment 帶著什麼資訊。TCP header 固定部分是 20 bytes，後面可以接最多 40 bytes 的 options，所以整個 header 介於 20 到 60 bytes 之間。下圖以 32 bit 為一列，最上方的數字是 bit 編號：

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
```

從上往下讀。第一列是兩個 16 bit 的 port，和 IP header 裡的位址合起來就是四元組。第二列 **Sequence Number**（序號）表示這個 segment 的第一個資料 byte 在整條資料流中的編號；第三列 **Acknowledgment Number**（確認號）表示「我已經收齊你到這個編號之前的所有 byte，下一個請送這號」，只有 ACK 旗標打開時才有意義。第四列開頭的 **Data Offset** 用 4 bit 記錄 header 有幾個 32 bit word，所以最小值 5 代表 20 bytes、最大值 15 代表 60 bytes；接著是保留位元與 8 個旗標，最後是 **Window**，告訴對方「我的接收 buffer 還有多少空間」，這是第 11 章流量控制的主角。第五列的 **Checksum** 涵蓋 header、資料和一段由 IP 位址組成的「pseudo-header」，用來偵測傳輸中的損壞；**Urgent Pointer** 搭配 URG 旗標使用，現代應用程式幾乎不用。

旗標（flags）是交握與揮手的語言。下表列出八個旗標，tcpdump 輸出中方括號裡的字母就是它們的縮寫：

| 旗標 | tcpdump 寫法 | 意思 | 本章出現的場合 |
|---|---|---|---|
| SYN | `S` | synchronize，請求同步起始序號 | 交握的第一、二個 segment |
| ACK | `.` | ack 欄位有效 | 除了第一個 SYN 以外，幾乎每個 segment 都有 |
| FIN | `F` | 我這個方向的資料送完了 | 揮手 |
| RST | `R` | 立刻中止這條連線（或「這裡沒有這條連線」） | 連到沒人聽的 port、異常中止 |
| PSH | `P` | 請盡快把資料交給應用程式 | 一般的資料 segment |
| URG | `U` | Urgent Pointer 有效 | 極少見 |
| ECE、CWR | `E`、`W` | 顯式擁塞通知（ECN）相關 | 第 12 章 |

所以 tcpdump 的 `Flags [S]` 是 SYN、`[S.]` 是 SYN+ACK、`[.]` 是純 ACK、`[P.]` 是帶資料的 PSH+ACK、`[F.]` 是 FIN+ACK、`[R]` 是 RST。看到 `[R.]` 則代表 RST 同時帶著 ACK，通常是「你連的 port 沒人在聽」的回應。

**Options**（選項）讓 TCP 在不改 header 格式的情況下擴充功能，大多數選項只能在 SYN 與 SYN+ACK 上協商，交握結束後就定案了。每個選項的格式是「kind（1 byte）＋ length（1 byte）＋ 值」，只有 NOP（kind 1，用來補齊對齊）與 End of Option List（kind 0）只有 1 byte。

| 選項 | kind | 長度 | 用途 | 詳見 |
|---|---|---|---|---|
| MSS | 2 | 4 | 告訴對方「每個 segment 的資料最多送我幾 bytes」，例如 1460 | 第 8 章 |
| Window Scale | 3 | 3 | Window 欄位只有 16 bit（最多 65,535），用位移倍數放大 | 第 11 章 |
| SACK Permitted | 4 | 2 | 雙方同意之後可以用 SACK 回報「收到哪些不連續的區塊」 | 第 11 章 |
| Timestamps | 8 | 10 | 量 RTT、防止序號回繞造成誤判（PAWS） | 第 11 章 |

光看圖不夠，下面用 Python 的 `struct` 組出一個真實長相的 SYN header，再把它解析回來。程式也實作了網際網路校驗和（Internet checksum）：把資料切成 16 bit 加總、把溢位的進位加回去，最後取一補數。接收方把收到的 segment 連同 checksum 再算一次，結果為 0 就代表沒被改動。

```python
import ipaddress
import struct

FLAG_NAMES = ["FIN", "SYN", "RST", "PSH", "ACK", "URG", "ECE", "CWR"]  # bit 0 → bit 7


def checksum16(data: bytes) -> int:
    """網際網路校驗和：16-bit 一補數加總再取反（IPv4、TCP、UDP 共用）。"""
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:  # 把溢位的進位加回低 16 bit
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def pseudo_header(src: str, dst: str, tcp_len: int) -> bytes:
    # TCP checksum 也涵蓋來源／目的 IP，避免封包被送錯主機卻沒被發現
    return (ipaddress.IPv4Address(src).packed + ipaddress.IPv4Address(dst).packed
            + struct.pack("!BBH", 0, 6, tcp_len))


def build_syn(src, dst, sport, dport, isn):
    options = (struct.pack("!BBH", 2, 4, 1460)          # MSS = 1460
               + struct.pack("!BB", 4, 2)               # SACK permitted
               + struct.pack("!BBII", 8, 10, 123456, 0)  # Timestamps
               + struct.pack("!B", 1)                   # NOP（補齊對齊）
               + struct.pack("!BBB", 3, 3, 7))          # Window scale = 7
    offset_words = (20 + len(options)) // 4
    flags = 0b0000_0010                                  # 只有 SYN
    header = struct.pack("!HHIIBBHHH", sport, dport, isn, 0,
                         offset_words << 4, flags, 64240, 0, 0) + options
    csum = checksum16(pseudo_header(src, dst, len(header)) + header)
    return header[:16] + struct.pack("!H", csum) + header[18:]


def parse(segment: bytes, src: str, dst: str):
    sport, dport, seq, ack, off_byte, flags, window, csum, urg = struct.unpack("!HHIIBBHHH", segment[:20])
    header_len = (off_byte >> 4) * 4
    names = [n for i, n in enumerate(FLAG_NAMES) if flags >> i & 1]
    print(f"ports      {sport} -> {dport}")
    print(f"seq/ack    {seq} / {ack}")
    print(f"header     {header_len} bytes（data offset = {off_byte >> 4} 個 32-bit word）")
    print(f"flags      {flags:08b} = {'+'.join(names)}")
    print(f"window     {window}（SYN 的 window 永遠不套 window scale）")
    print(f"checksum   0x{csum:04x}，重算驗證結果 = {checksum16(pseudo_header(src, dst, len(segment)) + segment):#06x}")
    i, opts = 20, []
    while i < header_len:
        kind = segment[i]
        if kind == 1:
            opts.append("NOP"); i += 1; continue
        length = segment[i + 1]
        value = segment[i + 2:i + length]
        label = {2: "MSS", 3: "WScale", 4: "SACK-Perm", 8: "TS"}.get(kind, f"kind{kind}")
        if kind == 2:
            label += f"={int.from_bytes(value, 'big')}"
        elif kind == 3:
            label += f"={value[0]}"
        elif kind == 8:
            label += f"={struct.unpack('!II', value)}"
        opts.append(label); i += length
    print(f"options    {', '.join(opts)}")
    return header_len, names


src, dst = "198.51.100.23", "203.0.113.10"
syn = build_syn(src, dst, 51514, 443, isn=2_874_105_310)
print(syn[:20].hex(" "))
header_len, names = parse(syn, src, dst)
assert header_len == len(syn) == 40 and names == ["SYN"]
assert checksum16(pseudo_header(src, dst, len(syn)) + syn) == 0
```

```text
c9 3a 01 bb ab 4f 5d de 00 00 00 00 a0 02 fa f0 30 54 00 00
ports      51514 -> 443
seq/ack    2874105310 / 0
header     40 bytes（data offset = 10 個 32-bit word）
flags      00000010 = SYN
window     64240（SYN 的 window 永遠不套 window scale）
checksum   0x3054，重算驗證結果 = 0x0000
options    MSS=1460, SACK-Perm, TS=(123456, 0), NOP, WScale=7
```

第一行是固定 20 bytes 的十六進位，可以和位元圖逐格對照：`c9 3a` 是 51514、`01 bb` 是 443，接著四個 byte 是序號，再四個 `00` 是確認號（SYN 還沒有東西可以確認）。第 13 個 byte `a0` 的高 4 bit 是 `a`，也就是 data offset 10，代表 header 40 bytes；第 14 個 byte `02` 只有 SYN 位元打開。`fa f0` 是 window 64240，`30 54` 是 checksum。

解析結果的 options 順序（MSS、SACK、Timestamps、NOP、Window Scale）正是 Linux 送出 SYN 時常見的排列，恰好 20 bytes，讓 header 對齊到 4 的倍數。最後一行驗證很重要：把整個 segment 連同 checksum 再算一次得到 0，這就是接收端判斷「沒有位元被翻轉」的方法。真實系統中，checksum 常常交給網卡計算（checksum offload），所以你在送出端用 tcpdump 抓到的封包可能顯示「checksum incorrect」，那多半不是錯誤，而是網卡還沒填上。

## 10.4 三向交握：為什麼要三次

TCP 要保證「依序、不遺失」，靠的是替每個 byte 編號。但編號要從哪裡開始？兩端必須先互相告知自己的**起始序號**（ISN，Initial Sequence Number），並且確認對方真的收到了。每個方向都需要「告知＋確認」，加起來是四個動作，而 server 的「確認 client 的 ISN」和「告知自己的 ISN」可以合併在同一個 segment，於是變成三次：這就是**三向交握**（three-way handshake）。

```text
 Client（10.20.1.25:51514）                          Server（10.20.3.15:8080）
 CLOSED                                                          LISTEN
   │                                                               │
   │──── ① SYN  seq=2874105310（client ISN）──────────────────────►│
 SYN_SENT                                                      SYN_RECV
   │                                                               │
   │◄─── ② SYN+ACK  seq=1093822211（server ISN） ack=2874105311 ───│
 ESTABLISHED                                                       │
   │                                                               │
   │──── ③ ACK  seq=2874105311  ack=1093822212 ───────────────────►│
   │                                                          ESTABLISHED
   │──── ④ 第一個資料 segment  seq=2874105311  len=120 ───────────►│
```

逐步看。① client 選一個 ISN，送出只有 SYN 旗標的 segment，進入 SYN_SENT。② server 收到後回 SYN+ACK：SYN 代表「這是我的 ISN 1093822211」，ACK 的確認號 2874105311 代表「你的 ISN 我收到了，下一個請從這號開始」。注意確認號是 ISN 加 1，因為 **SYN 本身佔用一個序號**，雖然它不帶任何資料。③ client 回 ACK，確認號是 server 的 ISN 加 1，client 在送出這個 ACK 時就認定連線建立；server 收到它才進入 ESTABLISHED。④ 第一個資料 byte 的序號是 ISN＋1，不是 ISN。

從應用程式角度看，client 的 `connect()` 在收到 ② 並送出 ③ 時返回，所以 **connect 的耗時大約是一個 RTT**（round-trip time，封包來回一趟的時間）。這解釋了第 1 章那張延遲時間軸：從台北連到美國西岸的 server，光是 TCP 交握就要花上一百多毫秒，之後 TLS 還要再加一到兩個 RTT（第 18 章）。這也是為什麼連線重用那麼重要。

在真實系統中，用 tcpdump 抓這三個 segment 會長這樣（示意輸出，數字為示意）：

```bash
sudo tcpdump -ni eth0 -c 3 'tcp port 8080'
# ↓ 示意輸出
20:00:01.000100 IP 10.20.1.25.51514 > 10.20.3.15.8080: Flags [S], seq 2874105310, win 64240, options [mss 1460,sackOK,TS val 123456 ecr 0,nop,wscale 7], length 0
20:00:01.000180 IP 10.20.3.15.8080 > 10.20.1.25.51514: Flags [S.], seq 1093822211, ack 2874105311, win 65160, options [mss 1460,sackOK,TS val 998877 ecr 123456,nop,wscale 7], length 0
20:00:01.000210 IP 10.20.1.25.51514 > 10.20.3.15.8080: Flags [.], ack 1, win 502, options [nop,nop,TS val 123457 ecr 998877], length 0
```

第三行的 `ack 1` 不是真的確認號 1，而是 tcpdump 預設把交握之後的序號改成**相對序號**（減掉 ISN），方便人類閱讀；加上 `-S` 參數才會顯示絕對值。Wireshark 也有同樣的預設。`win 502` 也不是只有 502 bytes 的 buffer：交握時雙方協商了 `wscale 7`，實際 window 是 502×2⁷＝64,256 bytes。這兩個「看起來很怪的數字」是新手讀封包最常卡住的地方。

### 為什麼不能兩次就好

如果只有兩次（client 送 SYN，server 回 SYN+ACK 就算建立），server 沒辦法知道自己的 ISN 有沒有被 client 收到，也就無法確定反方向的序號同步了。更實際的問題是**延遲的舊 SYN**：網路上的封包可能在某個路由器的佇列裡耽擱很久才抵達。TCP 規格指出，三向交握的主要理由就是避免舊的連線請求造成混亂。

```text
 Client                                                        Server
   │── SYN seq=90（很久以前的舊 SYN，在網路裡迷路）···┐          │
   │── SYN seq=200（這次真正的連線請求）··········┐   │          │
   │                                              │   └─────────►│ 先收到舊 SYN
   │◄────────────── SYN+ACK seq=500 ack=91 ───────│──────────────│
   │  ack=91 不是我要的（我送的是 200）           │              │
   │─────────────── RST seq=91 ───────────────────│─────────────►│ 丟掉這個半成品
   │                                              └─────────────►│ 收到真正的 SYN
   │◄────────────── SYN+ACK seq=800 ack=201 ─────────────────────│
   │─────────────── ACK ack=801 ────────────────────────────────►│ 建立正確的連線
```

舊 SYN 先抵達，server 回了 SYN+ACK，確認號是 91。client 知道自己這次的 ISN 是 200，一看確認號不對，就回 RST 叫 server 丟掉這個半成品。如果只有兩次交握，server 在回完 SYN+ACK 就會認定連線成立，為一個根本不存在的 client 配置資源，甚至把資料送過去。第三個 ACK 讓 client 有機會說「是我、而且是這一次」。

### ISN 為什麼要隨機

ISN 如果每次都從 0 開始，同一個四元組的上一條連線殘留在網路上的舊 segment，序號可能剛好落在新連線的接收範圍裡，被誤當成新資料。早期實作讓 ISN 隨時間穩定遞增來避開這個問題，但可預測的 ISN 帶來安全風險：不在路徑上的攻擊者只要猜中序號，就可能偽造 segment 塞進別人的連線。現代做法（RFC 6528）是 **ISN ＝ M ＋ F(四元組, secret)**：M 是每 4 微秒加 1 的計時器，F 是對四元組和一個開機時產生的秘密值做的雜湊。同一個四元組的 ISN 仍隨時間前進，不同四元組之間則無法互相推算。

下面的程式用 HMAC-SHA256 模擬這個公式，並示範序號比較為什麼不能用普通的 `<`：序號只有 32 bit，傳超過 4 GiB 就會繞回 0。

```python
import hashlib
import hmac

SECRET = b"boot-time-random-secret"  # 真實核心在開機時用隨機數產生，外界拿不到
MOD = 2 ** 32


def isn(four_tuple: tuple, clock_us: int) -> int:
    """RFC 6528 的做法：ISN = M + F(四元組, secret)。M 是每 4 微秒加 1 的計時器。"""
    m = clock_us // 4
    digest = hmac.new(SECRET, repr(four_tuple).encode(), hashlib.sha256).digest()
    f = int.from_bytes(digest[:4], "big")
    return (m + f) % MOD


def seq_lt(a: int, b: int) -> bool:
    """序號比較要考慮回繞：a 在 b「之前」代表 (b - a) mod 2^32 落在前半圈。"""
    return a != b and (b - a) % MOD < 2 ** 31


student = ("198.51.100.23", 51514, "203.0.113.10", 443)
teacher = ("198.51.100.77", 60001, "203.0.113.10", 443)

t0 = 1_000_000                                  # 模擬時鐘（微秒）
a0, a1 = isn(student, t0), isn(student, t0 + 400)
b0 = isn(teacher, t0)
print(f"同一個四元組，t0      ISN = {a0:>10}")
print(f"同一個四元組，t0+400us ISN = {a1:>10}（差 {(a1 - a0) % MOD}）")
print(f"另一個四元組，t0      ISN = {b0:>10}")
assert (a1 - a0) % MOD == 100                   # 同一條連線的 ISN 隨時間單調前進
assert seq_lt(a0, a1)

near_wrap = MOD - 10                            # 快要繞回 0 的序號
after_wrap = (near_wrap + 25) % MOD             # 再送 25 bytes 之後
print(f"回繞：{near_wrap} + 25 = {after_wrap}，seq_lt = {seq_lt(near_wrap, after_wrap)}")
print(f"天真比較 {near_wrap} < {after_wrap} = {near_wrap < after_wrap}")
assert seq_lt(near_wrap, after_wrap) and not near_wrap < after_wrap
```

```text
同一個四元組，t0      ISN = 2184482929
同一個四元組，t0+400us ISN = 2184483029（差 100）
另一個四元組，t0      ISN = 3853716791
回繞：4294967286 + 25 = 15，seq_lt = True
天真比較 4294967286 < 15 = False
```

前兩行顯示同一個四元組過了 400 微秒，ISN 恰好前進 100（400 除以 4），所以同一對端點的新舊連線序號不會倒退。第三行換了一個四元組，ISN 完全不同，外人無法從自己連線的 ISN 推出別人的。最後兩行是序號回繞：4294967286 再送 25 bytes 變成 15，數值上變小了，但用「差值落在前半圈」的比較方式仍正確判斷 15 在後面。核心比較序號時用的就是這種寫法；你自己寫封包分析工具時也要記得。

### SYN 沒有回應時：逾時與重傳

如果 SYN 送出後沒有任何回應（server 主機不在、防火牆默默丟包、accept queue 滿了），client 會以指數退避重傳 SYN。在 Linux 上，初始重傳逾時是 1 秒，`net.ipv4.tcp_syn_retries` 預設 6 次，時間軸如下：

```text
 經過時間（秒） 0       1       3       7       15      31      63      127
                │       │       │       │       │       │       │       │
 送出           SYN     SYN     SYN     SYN     SYN     SYN     SYN     放棄
                首次    重傳1   重傳2   重傳3   重傳4   重傳5   重傳6   ETIMEDOUT
 距上一次       -       1s      2s      4s      8s      16s     32s     64s
```

每次等待時間加倍：1、2、4、8、16、32、64 秒，加總 127 秒後 `connect()` 才回報 `ETIMEDOUT`。也就是說，一個沒有設定 connect timeout 的 Python 程式，遇到一台被防火牆丟包的主機，會整整卡住兩分鐘。macOS 與其他作業系統的次數與間隔不同，但「很久」這個結論相同。所以呼叫任何網路服務時，都要明確設定連線逾時，例如 `socket.create_connection(addr, timeout=3)`。

和逾時完全不同的是**被拒絕**：如果 server 主機在線，但那個 port 沒有程式在 listen，對方核心會立刻回 RST，`connect()` 在一個 RTT 內就失敗並得到 `ECONNREFUSED`。這個差別是除錯的第一條線索：「refused」代表封包到了對方主機，只是沒人在聽；「timed out」代表封包在路上被丟、對方主機不在、或對方忙到連交握都完成不了。

> [!warning] 常見誤解
> 「連得上 port 就代表服務正常」是錯的。交握是核心完成的，應用程式就算卡死、根本沒在呼叫 `accept()`，只要 accept queue 還有空位，`connect()` 照樣成功。用 `nc -z` 或 TCP health check 只能證明「核心在聽」，要證明應用程式活著，必須送一個真正的請求並收到回應。

最後補充兩個很少見但值得知道的情況。**同時開啟**（simultaneous open）是兩端同時向對方送 SYN，雙方都從 SYN_SENT 進入 SYN_RECV 再進入 ESTABLISHED；它在 TCP 打洞穿越 NAT 時會用到（第 7、36 章）。**TCP Fast Open**（TFO）則讓重複連線的 client 在 SYN 裡就夾帶資料，省掉一個 RTT，但需要兩端與中間設備都支援，實務部署有限；QUIC 用另一種方式解決了同樣的問題（第 13 章）。

## 10.5 listen、backlog 與 accept queue

故事裡的 `Recv-Q 2049／Send-Q 2048` 是什麼意思？要回答這個問題，得先知道 server 端在交握期間把連線放在哪裡。呼叫 `listen(backlog)` 之後，Linux 核心會為這個 listening socket 維護兩個佇列：

```text
                         listening socket 10.20.1.25:8000（gunicorn）
                      ┌─────────────────────────────────────────────────┐
  ① SYN ────────────► │  SYN queue（半連線佇列）                        │
                      │  狀態 SYN_RECV：已回 SYN+ACK，等 client 的 ACK  │
  ② ◄──── SYN+ACK ─── │  [conn A] [conn B] [conn C] ...                 │
                      │      │  上限：tcp_max_syn_backlog 等參數        │
  ③ ACK ────────────► │      ▼                                          │
                      │  accept queue（全連線佇列）                     │
                      │  狀態 ESTABLISHED：交握完成，等應用程式領走     │
                      │  [conn X] [conn Y] [conn Z] ...                 │
                      │      │  上限：min(backlog, net.core.somaxconn)  │
                      └──────┼──────────────────────────────────────────┘
                             ▼
                 ④ 應用程式呼叫 accept() 取走一條 → 拿到新的 socket fd
```

① client 的 SYN 抵達，核心回 SYN+ACK，把這條半成品連線放進 **SYN queue**（也有人叫半連線佇列），狀態是 SYN_RECV。② 與 ③ 是交握的後兩步；收到 client 的 ACK 之後，核心把連線移到 **accept queue**（全連線佇列），狀態變成 ESTABLISHED。這一切都發生在核心裡，應用程式完全沒參與。④ 只有當應用程式呼叫 `accept()`，連線才離開佇列，變成一個應用程式可以讀寫的 socket。`listen()` 的 **backlog** 參數，在 Linux 上決定的是 accept queue 的上限，而且會被系統參數 `net.core.somaxconn` 截斷，實際上限是兩者取小。

accept queue 滿了會怎樣？在 Linux 預設設定下，核心不會回 RST 拒絕，而是**默默丟掉**：新進來的 SYN 被丟掉，client 只好重傳；已經在 SYN queue、送來第三個 ACK 的連線也可能被丟掉那個 ACK，server 端稍後重傳 SYN+ACK。從 client 看，症狀是 `connect()` 變慢或逾時，而不是被拒絕。這個設計是刻意的：佇列滿往往只是短暫尖峰，讓 client 重傳一次也許就排進去了；若改成直接回 RST（`net.ipv4.tcp_abort_on_overflow=1`），client 會立刻失敗。

在 Linux 上，`ss -ltn` 對 LISTEN 狀態的 socket 會把兩個欄位挪作其他用途：`Recv-Q` 是 accept queue **目前**的長度，`Send-Q` 是它的**上限**。下面是故事當晚 API 主機的輸出（示意輸出）：

```bash
ss -ltn 'sport = :8000'
# ↓ 示意輸出
State   Recv-Q  Send-Q   Local Address:Port   Peer Address:Port
LISTEN  2049    2048     10.20.1.25:8000      0.0.0.0:*

nstat -az TcpExtListenOverflows TcpExtListenDrops
# ↓ 示意輸出（累計值，隔幾秒再看一次，看增加速度）
TcpExtListenOverflows           184327             0.0
TcpExtListenDrops               184327             0.0
```

`Send-Q 2048` 是 gunicorn 預設的 backlog；`Recv-Q 2049` 比上限還多 1，是因為 Linux 的判斷條件是「目前長度大於上限才算滿」，所以實際能容納 backlog＋1 條。`TcpExtListenOverflows` 是「accept queue 滿而丟棄」的累計次數，只要它在增加，就代表有使用者的連線正在被丟。重點來了：佇列滿的原因幾乎從來不是 backlog 太小，而是**應用程式 accept 得太慢**。故事中 gunicorn 因為 fd 用光，每次 `accept()` 都失敗，佇列當然只進不出；這時把 backlog 調大，只是讓更多連線排在一個不會前進的隊伍裡。

下表整理工作上常遇到的預設 backlog。實際生效的值都還要和 `somaxconn` 取小，Linux 5.4 起 `somaxconn` 預設是 4096，更早的核心是 128。

| 軟體 | 預設 backlog | 備註 |
|---|---|---|
| Python `socket.listen()` 不帶參數 | min(SOMAXCONN, 128) | 依平台的 SOMAXCONN 常數而定 |
| Python `socketserver.TCPServer` | 5 | `request_queue_size` 屬性，教學用 server 常見瓶頸 |
| gunicorn | 2048 | `--backlog` |
| nginx `listen` | Linux 上 511 | `listen ... backlog=N`；macOS 與 FreeBSD 上預設 -1 |
| Linux `net.core.somaxconn` | 4096（5.4 起） | 所有 backlog 的天花板 |

### SYN flood 與 SYN cookies

SYN queue 有上限，這讓它成為攻擊目標：**SYN flood** 是攻擊者偽造大量來源位址送 SYN，卻永遠不完成第三步，把 SYN queue 塞滿，讓正常使用者的 SYN 進不來。主要防禦是 **SYN cookies**：當 SYN queue 滿了，核心不再為每個 SYN 保存狀態，而是把連線的必要資訊（MSS 等）用帶秘密值的雜湊編進自己回應的 ISN 裡；等合法 client 送回第三個 ACK，核心從確認號反推出 cookie 並驗證，再當場建立連線。偽造來源位址的攻擊者收不到 SYN+ACK，也就送不出正確的 ACK。Linux 的 `net.ipv4.tcp_syncookies` 預設為 1，表示「SYN queue 溢位時才啟用」。代價是 cookie 能編入的資訊有限，部分 TCP 選項可能無法保留（依實作而定）。在 `dmesg` 看到「Possible SYN flooding on port 8000. Sending cookies.」不一定是攻擊，也可能只是正常尖峰把 SYN queue 撐滿，要搭配流量來源判斷；大規模攻擊則需要在網路邊緣（雲端 DDoS 防護、LB）處理。

## 10.6 關閉連線：FIN、半關閉與四次揮手

建立連線要同步序號，關閉連線則要確保「兩個方向的資料都送完了」。因為 TCP 是全雙工，兩個方向是獨立的：我說「我送完了」，不代表你也送完了。所以每個方向各自用一個 **FIN** 宣告結束、各自需要對方 ACK，正常情況下總共四個 segment，俗稱**四次揮手**。先送 FIN 的一方叫**主動關閉方**（active closer），另一方叫**被動關閉方**（passive closer）；誰是主動方和誰是 client 無關，只看誰先 close。

```text
 主動關閉方（例如課表服務）                               被動關閉方（例如 API 的連線池）
 ESTABLISHED                                                    ESTABLISHED
   │ close()                                                         │
   │──── ① FIN  seq=u ──────────────────────────────────────────────►│
 FIN_WAIT_1                                                      CLOSE_WAIT
   │◄─── ② ACK  ack=u+1 ─────────────────────────────────────────────│ recv() 回傳 b""（EOF）
 FIN_WAIT_2                                                          │ 應用程式還可以繼續送資料
   │◄─── （可能還有資料 segment）────────────────────────────────────│
   │                                                                 │ 應用程式呼叫 close()
   │◄─── ③ FIN  seq=v ───────────────────────────────────────────────│
 TIME_WAIT                                                        LAST_ACK
   │──── ④ ACK  ack=v+1 ────────────────────────────────────────────►│
   │                                                              CLOSED
   │  等待 2×MSL（Linux 為 60 秒）
 CLOSED
```

① 主動方呼叫 `close()`，核心送出 FIN，進入 FIN_WAIT_1。和 SYN 一樣，**FIN 也佔用一個序號**，所以對方的確認號是 u＋1。② 被動方的核心立刻回 ACK，並進入 CLOSE_WAIT；同時，被動方應用程式的 `recv()` 會回傳空的 bytes（EOF），這是應用程式唯一能得知「對方關了」的訊號。主動方收到 ACK 後進入 FIN_WAIT_2，繼續等對方的 FIN。

關鍵在 ② 和 ③ 之間：被動方停在 CLOSE_WAIT，**一直到應用程式自己呼叫 `close()` 為止**，核心才會送出 ③ 的 FIN 並進入 LAST_ACK。核心不會替應用程式決定，因為對方只是說「我不送了」，被動方也許還有回應要送。④ 主動方回最後一個 ACK 後進入 **TIME_WAIT**，等待一段時間才真正釋放；被動方收到 ACK 就直接 CLOSED。這張圖同時回答了兩個故事裡的謎題：TIME_WAIT 出現在主動關閉方（課表服務），CLOSE_WAIT 出現在被動關閉方（我們的連線池）。

在真實封包中你常常只看到三個 segment：如果被動方的應用程式在收到 FIN 時剛好也要關，核心會把 ② 的 ACK 和 ③ 的 FIN 合併成一個 `Flags [F.]`。另一個少見的情況是**同時關閉**（simultaneous close）：兩端同時送 FIN，雙方都從 FIN_WAIT_1 進入 **CLOSING**，收到 ACK 後雙方都進入 TIME_WAIT。

### 半關閉：shutdown 與 close 不一樣

「我送完了，但我還要聽你說」這種狀態叫**半關閉**（half-close），用 `shutdown(SHUT_WR)` 達成。一個具體例子：聲聲 Live 的錄影上傳工具把整份課程字幕送給轉錄服務，送完後呼叫 `shutdown(SHUT_WR)`，轉錄服務讀到 EOF 就知道「請求完整了」，開始處理並把結果寫回，上傳工具繼續 `recv()` 直到對方也關閉。不用另外設計「請求結束」的標記，EOF 本身就是訊號。

```text
 上傳工具                                                     轉錄服務
   │──── 資料 1..N ─────────────────────────────────────────────►│
   │ shutdown(SHUT_WR)                                           │
   │──── FIN ───────────────────────────────────────────────────►│ recv() == b""：請求完整
 FIN_WAIT_2  ◄──── ACK ──────────────────────────────────────────│ CLOSE_WAIT（正常、短暫）
   │                                                             │ 處理中……
   │◄─── 轉錄結果 1..M ──────────────────────────────────────────│ 半關閉後反方向照常傳
   │◄─── FIN ────────────────────────────────────────────────────│ close()
 TIME_WAIT ──── ACK ────────────────────────────────────────────►│ LAST_ACK → CLOSED
```

上傳工具在 `shutdown` 之後進入 FIN_WAIT_2，但 socket 仍可讀；轉錄服務在 CLOSE_WAIT 期間照常送出結果，這時 CLOSE_WAIT 是完全正常的，因為應用程式「正在做事」，做完就會 close。CLOSE_WAIT 只有在**長時間不消失、數量持續增加**時才是 bug。下表比較四種結束方式，動手做會一一實驗：

| 呼叫 | 送出 | 自己還能讀 | 自己還能寫 | 典型用途 |
|---|---|---|---|---|
| `shutdown(SHUT_WR)` | FIN | 可以 | 不行 | 送完請求，等回應（半關閉） |
| `shutdown(SHUT_RD)` | 不送任何東西 | 不行 | 可以 | 少用；之後收到的資料行為依平台而定 |
| `close()`（一般情況） | FIN | 不行（fd 已釋放） | 不行 | 正常結束 |
| `close()`，接收 buffer 還有沒讀的資料 | RST | 不行 | 不行 | 通常是 bug：對方的資料被丟棄 |
| `SO_LINGER(on, 0)` 後 `close()` | RST | 不行 | 不行 | 刻意中止、跳過 TIME_WAIT（有風險） |

還有一個 Python 特有的細節：`close()` 釋放的是 fd，只有在**最後一個**參考這條連線的 fd 被關掉時，核心才送 FIN。如果你用 `os.fork()` 或 `socket.dup()` 讓兩個 fd 指向同一條連線，只關一個不會送 FIN；`shutdown()` 則不管有幾個 fd，立刻作用在連線本身。在 CPython 裡，socket 物件被垃圾回收時也會自動關閉，所以真正的洩漏往往是「物件還被某個 list、dict 或連線池引用著」。

## 10.7 TIME_WAIT：主動關閉方的保險

TIME_WAIT 是最常被誤會的狀態。很多人在 `ss` 裡看到幾千條 TIME_WAIT 就以為出事了，急著調核心參數。其實 TIME_WAIT 是協定刻意設計的保險，它解決兩個問題。

第一，**確保最後一個 ACK 送達**。如果主動方送出的 ④ ACK 在路上遺失，被動方會在 LAST_ACK 等不到 ACK，於是重傳 FIN。這時主動方必須還記得這條連線，才能再回一次 ACK；如果它已經徹底忘了，就只能回 RST，被動方的應用程式會看到一個莫名其妙的錯誤。

```text
 主動關閉方                                                       被動關閉方
 TIME_WAIT                                                        LAST_ACK
   │──── ④ ACK ───────────────────────────────╳（遺失）             │
   │                                                                │ 等不到 ACK，逾時
   │◄─── ③' 重傳 FIN ───────────────────────────────────────────────│
   │ 還在 TIME_WAIT，認得這條連線                                   │
   │──── ④' 再回 ACK（並重新計時）─────────────────────────────────►│
   │                                                              CLOSED
   │ 如果已經 CLOSED：收到不認識的 FIN → 只能回 RST → 對方看到錯誤
```

第二，**讓舊連線的迷途 segment 死在網路裡**。假設同一個四元組立刻建立了新連線，上一條連線某個延遲很久的資料 segment 才抵達，若序號剛好落在新連線的視窗內，就會被當成新資料，造成無聲的資料損壞。**MSL**（Maximum Segment Lifetime）是規格假設一個 segment 在網路上能存活的最長時間；等滿 2×MSL，可以保證兩個方向的舊 segment 都已消失。規格建議 MSL 為 2 分鐘，但實作通常更短：

| 系統 | TIME_WAIT 時間 | 能否調整 |
|---|---|---|
| TCP 規格 | 2×MSL，MSL 建議 2 分鐘 | 由實作決定 |
| Linux | 60 秒 | 長期以來是核心常數；`tcp_fin_timeout` 管的是 FIN_WAIT_2，不是 TIME_WAIT |
| macOS | 2×`net.inet.tcp.msl`，預設 msl 為 15000 毫秒，即 30 秒 | sysctl 可調 |
| Windows | 依版本與登錄設定而定 | 登錄機碼 |

### TIME_WAIT 真正的成本

TIME_WAIT 本身很便宜：Linux 用一個精簡的結構保存它，不佔 fd，也不佔應用程式的記憶體，幾萬條只用掉幾 MB。真正的成本是**佔住四元組**。主動關閉的一方如果也是發起連線的 client，它的來源 port 在 60 秒內不能用來連同一個目的地。

手算一次。Linux 預設的臨時 port（ephemeral port，connect 時系統自動分配的來源 port）範圍是 32768–60999，共 28,232 個。如果某台 API 主機對**同一個**目的地（例如課表服務 10.20.3.15:8080）每個請求都開新連線、用完由 client 主動關閉，那麼每秒最多只能開 28,232 ÷ 60 ≈ 470 條新連線，超過就會在 `connect()` 得到 `EADDRNOTAVAIL`（Cannot assign requested address）。注意限制是「每個目的地」：Linux 在 connect 時會考慮完整四元組，連到不同目的地的連線可以共用同一個來源 port。

這個計算也指出正確的解法順序：

| 做法 | 解決什麼 | 代價與注意事項 |
|---|---|---|
| 連線重用（HTTP keep-alive、連線池） | 根本不產生大量 TIME_WAIT | 要處理對方關閉閒置連線的問題（10.8 節） |
| 讓 server 端主動關閉 | TIME_WAIT 落在 server，server 的四元組來自眾多 client，不會耗盡 | 要看協定與上游行為 |
| server 設 `SO_REUSEADDR` | 重啟時能立刻 bind 有 TIME_WAIT 殘留的 port | 幾乎所有 server 框架預設都開；不會讓兩個程式同時 listen |
| `net.ipv4.tcp_tw_reuse` | client 端在時間戳記證明安全時，重用 TIME_WAIT 的四元組 | 只影響 outgoing 連線，依賴 TCP timestamps；預設值依核心版本而定 |
| 擴大 `ip_local_port_range` | 多一些來源 port | 治標 |
| `SO_LINGER(on, 0)` 用 RST 關閉 | 完全跳過 TIME_WAIT | 丟失未送出的資料、失去 TIME_WAIT 的保護，一般不建議 |

> [!warning] 常見誤解
> 網路上流傳的「打開 `net.ipv4.tcp_tw_recycle`」在 Linux 4.12 已經被移除，因為它會讓位於同一個 NAT 後方的多個 client 連線失敗。另一個常見錯誤是調低 `net.ipv4.tcp_fin_timeout` 想縮短 TIME_WAIT，但它控制的是孤兒連線停在 FIN_WAIT_2 的時間，對 TIME_WAIT 沒有作用。

`SO_REUSEADDR` 和 `SO_REUSEPORT` 也常被混淆。前者在 Linux 上的主要作用是：即使這個 port 還有 TIME_WAIT 的連線殘留，新的 listening socket 也能 bind 上去；它不允許兩個程式同時在同一個位址 listen。後者則允許多個 socket 同時 listen 同一個 port，由核心把新連線分散給它們，是另一種用途（第 40 章談並行模型時會用到）。Python 的 `http.server.HTTPServer` 與 asyncio 的 `create_server` 在 Unix 上都預設開啟 `SO_REUSEADDR`，而 `socketserver.TCPServer` 預設不開，這就是有些教學程式重啟時會看到「Address already in use」的原因。

## 10.8 CLOSE_WAIT：被動關閉方忘了 close

回到四次揮手的圖：被動方收到 FIN 後進入 CLOSE_WAIT，要等應用程式呼叫 `close()` 才會離開。TCP 規格沒有為 CLOSE_WAIT 定義任何計時器，Linux 也不會主動把它清掉，因為核心無從得知應用程式是「還在處理」還是「忘了」。所以 **CLOSE_WAIT 長時間堆積，幾乎一定是本機應用程式的 bug**，和網路、對方、核心參數都無關。這一點非常有用：看到 CLOSE_WAIT 數量持續增加，你不需要懷疑任何外部系統，直接找本機哪個程式、對哪個遠端的連線沒有關。

CLOSE_WAIT 的代價比 TIME_WAIT 高得多。它仍然是一條應用程式持有的連線，佔著一個 fd、核心的 socket 結構與 buffer。fd 有上限（`ulimit -n`，常見預設 1024），用光之後，這個 process 連開檔案、`accept()` 新連線都會失敗，得到 `EMFILE`（Too many open files），故事裡的 gunicorn 就是這樣倒下的。

常見的成因有三種，都是「程式還持有 socket 物件，卻沒有在對方關閉後處理它」：

- **連線池不檢查連線是否還活著**。上游 server 的閒置逾時（例如 gunicorn 的 keep-alive 預設 2 秒、nginx 的 `keepalive_timeout` 預設 75 秒）比 client 端連線池的閒置時間短，上游先把連線關了，池子裡的連線全部變成 CLOSE_WAIT。下一個請求拿到它，`send()` 還會成功，`recv()` 卻立刻得到 EOF，於是應用程式看到「Remote end closed connection without response」之類的錯誤。故事中的連線池正是這個 bug。
- **錯誤處理路徑沒有 close**。正常路徑記得關，但例外發生時提早 return 或 raise，socket 被留在某個全域的 dict 裡。用 `with` 或 `try/finally` 可以根除這類問題。
- **讀到 EOF 卻不認得它**。迴圈裡 `recv()` 回傳 `b""` 時沒有跳出並關閉，有些程式甚至在 EOF 上無限迴圈，同時吃掉一顆 CPU。

找出兇手的指令如下（示意輸出）。`ss` 的 `-p` 會顯示持有 socket 的 process，`lsof` 則能從 process 的角度列出所有 CLOSE_WAIT：

```bash
ss -tanp state close-wait | head -4
# ↓ 示意輸出
Recv-Q  Send-Q  Local Address:Port    Peer Address:Port   Process
1       0       10.20.1.25:51514      10.20.3.15:8080     users:(("gunicorn",pid=8123,fd=37))
1       0       10.20.1.25:51520      10.20.3.15:8080     users:(("gunicorn",pid=8123,fd=41))
1       0       10.20.1.25:51533      10.20.3.15:8080     users:(("gunicorn",pid=8125,fd=29))

ss -tan state close-wait | awk 'NR>1 {print $4}' | sort | uniq -c | sort -rn | head -3
# ↓ 示意輸出：依遠端位址分組，一眼看出是對哪個服務的連線沒關
   3812 10.20.3.15:8080
```

每一列的 `Recv-Q 1` 很有意思：那 1 就是對方的 FIN。FIN 佔一個序號，應用程式還沒讀到這個 EOF，核心就把它算成 1 個未讀單位。依遠端分組之後，3,812 條全部連向課表服務，加上 process 名稱是 gunicorn，嫌疑就收斂到「教室入口 API 呼叫課表服務的那段程式碼」，也就是新加的連線池。修正方式是讓連線池在重用前偵測 EOF 並 close，同時讓 client 端的閒置上限比上游的 keep-alive timeout 短，動手做會實際示範。

## 10.9 RST：不講道理的結束

FIN 是禮貌的道別：「我送完了，你慢慢來」。**RST**（reset）則是「這條連線立刻作廢」：收到 RST 的一方直接丟棄連線狀態與 buffer 裡還沒處理的資料，不需要也不會回 ACK，應用程式下一次讀寫會得到錯誤。RST 出現的情況可以歸成四類：

```text
 (a) 連到沒人 listen 的 port               (b) 收到不屬於任何連線的 segment（半開連線）
 Client              Server                Client               Server（剛重開機，已忘了這條連線）
   │── SYN ──────────►│                       │── 資料 ───────────►│
   │◄──── RST+ACK ────│ ECONNREFUSED          │◄──── RST ──────────│ ECONNRESET
                                               
 (c) 應用程式中止連線                        (d) 中間設備送的 RST
 Client              Server                Client      LB／防火牆           Server
   │── 請求資料 ─────►│ 沒讀就 close()         │── 資料 ───►│ 閒置太久，連線追蹤       │
   │                  │ 或 SO_LINGER=0         │            │ 表已經刪掉這條           │
   │◄──── RST ────────│ ECONNRESET             │◄── RST ────│ ECONNRESET               │
```

(a) 是最常見也最無害的：主機在線但 port 沒人聽，核心回 RST，client 立刻得到 `ECONNREFUSED`。(b) 是半開連線：server 重開機或 process 被殺掉後，client 還以為連線活著，送出的資料抵達一個沒有對應 TCB 的主機，對方回 RST。(c) 是應用程式自己造成的：關閉時接收 buffer 還有沒讀的資料，或刻意設了 `SO_LINGER` 為 0，核心改送 RST 而不是 FIN。(d) 是中間設備：load balancer、NAT 或防火牆的連線追蹤表（第 7 章）有閒置逾時，條目被刪掉後再有封包經過，有些設備會回 RST，有些則默默丟包，後者會讓連線「看起來還在，其實已經死了」。

聲聲 Live 的 WebSocket 聊天（第 32 章）就踩過 (d)：教室裡沒人說話超過 LB 的閒置逾時，連線被 LB 中止，學生下一則訊息才發現斷線。解法是應用層的 ping／pong 心跳，間隔要短於路徑上所有設備的閒置逾時；TCP 自己的 keepalive 則在第 11 章介紹。

由於 RST 能直接殺掉連線，偽造 RST 一直是攻擊者感興趣的手法。現代 TCP 實作（RFC 5961）要求 RST 的序號必須**恰好**等於期待的下一個序號才立即生效；只是落在視窗內的 RST，核心會回一個 challenge ACK 請對方確認，讓不在路徑上的攻擊者很難靠猜測序號中止別人的連線。

應用程式看不到 RST 本身，只看到 errno。下表把 Python 的例外對應回網路上發生的事，這張表在讀 log 時非常好用：

| Python 例外 | errno | 網路上發生的事 | 第一個該懷疑的方向 |
|---|---|---|---|
| `ConnectionRefusedError` | `ECONNREFUSED` | SYN 換來 RST | 服務沒啟動、port 打錯、listen 在 127.0.0.1 而非 0.0.0.0 |
| `TimeoutError`（connect 時） | `ETIMEDOUT` 或應用程式自設的逾時 | SYN 沒有回應 | 防火牆、security group、路由、對方 accept queue 滿 |
| `ConnectionResetError` | `ECONNRESET` | 收到 RST | 對方 crash 或重啟、LB 閒置逾時、對方沒讀完就關 |
| `BrokenPipeError` | `EPIPE` | 對方已關閉，我方還在寫 | 寫之前沒檢查對方是否已關閉；連線池重用了死連線 |
| `recv()` 回傳 `b""` | 無（不是錯誤） | 收到 FIN | 正常 EOF，應該跳出迴圈並 close |
| `OSError` | `EADDRNOTAVAIL` | 沒有可用的來源 port | 對同一目的地短連線太多，TIME_WAIT 佔滿 port |
| `OSError` | `EMFILE` | process 的 fd 用光 | CLOSE_WAIT 洩漏或其他 fd 洩漏 |

## 10.10 把所有狀態串起來：完整狀態機

前面各節分別看了開與關的片段，現在把它們合成一張完整的狀態機。左半邊是主動開啟（client 的 `connect()`）與被動開啟（server 的 `listen()`），下半部左邊是主動關閉的路徑，右邊是被動關閉的路徑。

```text
                            ┌────────────┐
                            │   CLOSED   │
                            └────────────┘
         passive open:            │  │       active open:
         listen()                 │  │       connect(), send SYN
              ┌───────────────────┘  └───────────────────┐
              ▼                                          ▼
       ┌────────────┐                             ┌────────────┐
       │   LISTEN   │                             │  SYN_SENT  │
       └────────────┘                             └────────────┘
              │ recv SYN, send SYN+ACK                   │ recv SYN+ACK
              ▼                                          │ send ACK
       ┌────────────┐                                    │
       │  SYN_RECV  │                                    │
       └────────────┘                                    │
              │ recv ACK                                 │
              ▼                                          ▼
       ┌──────────────────────────────────────────────────────┐
       │                     ESTABLISHED                      │
       └──────────────────────────────────────────────────────┘
              │ close()                                  │ recv FIN
              │ send FIN                                 │ send ACK
              ▼                                          ▼
       ┌────────────┐                             ┌────────────┐
       │ FIN_WAIT_1 │                             │ CLOSE_WAIT │  no timer:
       └────────────┘                             └────────────┘  waits for close()
        │          │ recv FIN                            │ close()
        │ recv ACK │ send ACK                            │ send FIN
        ▼          ▼                                     ▼
 ┌────────────┐ ┌────────────┐                    ┌────────────┐
 │ FIN_WAIT_2 │ │  CLOSING   │                    │  LAST_ACK  │
 └────────────┘ └────────────┘                    └────────────┘
        │          │                                     │ recv ACK
        │ recv FIN │ recv ACK                            │
        │ send ACK │                                     ▼
        ▼          ▼                              ┌────────────┐
       ┌────────────┐      2 x MSL timeout        │   CLOSED   │
       │ TIME_WAIT  │────────────────────────────►│            │
       └────────────┘                             └────────────┘
```

從上往下走兩條典型路徑。**client 的一生**：CLOSED →（connect，送 SYN）→ SYN_SENT →（收 SYN+ACK，回 ACK）→ ESTABLISHED；若 client 先關，就走左下：FIN_WAIT_1 → FIN_WAIT_2 → TIME_WAIT → CLOSED。**server 的一生**：listening socket 停在 LISTEN；每個 SYN 會產生一條新連線，從 SYN_RECV 進入 ESTABLISHED；若 client 先關，server 的連線走右下：CLOSE_WAIT →（應用程式 close）→ LAST_ACK → CLOSED。

圖中有兩個地方值得特別標記。第一，LISTEN 本身不會變成 ESTABLISHED：listening socket 永遠停在 LISTEN，每條新連線是另外生出來的 socket，這就是 `accept()` 回傳一個**新的** socket 的原因。第二，整張圖中只有 CLOSE_WAIT 的出口完全依賴應用程式，其他狀態的出口都由封包或計時器驅動。下表把每個狀態的意義和「在 production 看到很多時代表什麼」整理在一起：

| 狀態 | 誰會進入 | 怎麼離開 | 大量出現代表 |
|---|---|---|---|
| LISTEN | server 的 listening socket | 應用程式關閉它 | 正常；每個服務一條 |
| SYN_SENT | 主動開啟的一方 | 收到 SYN+ACK，或重傳到放棄 | 對方不回應：防火牆丟包、路由問題、對方 accept queue 滿 |
| SYN_RECV | 被動開啟的連線 | 收到 ACK，或 SYN+ACK 重傳到放棄 | SYN flood，或 client 的 ACK 回不來 |
| ESTABLISHED | 雙方 | 收到或送出 FIN／RST | 通常正常；比預期多可能是連線沒重用或洩漏 |
| FIN_WAIT_1 | 主動關閉方 | 收到 ACK（或 FIN） | 對方不回 ACK，可能對方已消失或接收視窗為 0 |
| FIN_WAIT_2 | 主動關閉方 | 收到對方的 FIN | 對方停在 CLOSE_WAIT（對方的 bug）；孤兒連線由 `tcp_fin_timeout` 清除 |
| CLOSE_WAIT | 被動關閉方 | 應用程式 close() | **本機應用程式沒有 close**，持續增加就是洩漏 |
| LAST_ACK | 被動關閉方 | 收到最後的 ACK | 短暫；大量存在可能是對方已消失 |
| CLOSING | 同時關閉的雙方 | 收到 ACK | 罕見 |
| TIME_WAIT | 主動關閉方 | 2×MSL 計時器到期 | 通常正常；只有在耗盡來源 port 時才需處理 |

不同工具對狀態的寫法不同，搜尋 log 時要注意：規格寫成 `SYN-RECEIVED`、`FIN-WAIT-1`、`TIME-WAIT`；`netstat` 寫成 `SYN_RECV`、`FIN_WAIT1`、`TIME_WAIT`；`ss` 寫成 `SYN-RECV`、`FIN-WAIT-1`、`TIME-WAIT`，並把 ESTABLISHED 縮寫成 `ESTAB`。本書正文統一用底線寫法。

## 10.11 動手做：在 127.0.0.1 上觀察 TCP 的一生

這一節用五段程式把前面的理論變成可以觀察的事實：狀態轉移與半關閉、accept queue 滿、RST、CLOSE_WAIT 洩漏的重現與修正，以及 TIME_WAIT 擋住重啟。每段程式只用標準函式庫，在 127.0.0.1 上用 port 0 讓系統分配埠號。

讀取 TCP 狀態需要一點平台相關的技巧：Linux 的 `TCP_INFO` 與 macOS 的 `TCP_CONNECTION_INFO` 這兩個 socket 選項，回傳結構的第一個 byte 都是核心裡的狀態碼，只是兩邊的編號不同。程式裡的 `tcp_state()` 把它翻成名稱，讓我們不用 root、不用 `ss`，就能從程式裡直接看到狀態。以下輸出都是在 macOS 上實際執行的結果；在 Linux 上狀態名稱相同。

### 實驗一：一條連線的一生與半關閉

這段程式刻意寫成單執行緒，讓每一步的先後完全由我們控制：先 listen、再 connect，**還沒 accept 就讀 client 狀態**；接著 client 送出請求後半關閉，server 讀到 EOF 才回應並關閉。

```python
import socket
import sys
import time

# 核心狀態碼 → 名稱。Linux 用 TCP_INFO，macOS 用 TCP_CONNECTION_INFO，第一個 byte 都是狀態
LINUX = {1: "ESTABLISHED", 2: "SYN_SENT", 3: "SYN_RECV", 4: "FIN_WAIT_1", 5: "FIN_WAIT_2",
         6: "TIME_WAIT", 7: "CLOSED", 8: "CLOSE_WAIT", 9: "LAST_ACK", 10: "LISTEN", 11: "CLOSING"}
BSD = {0: "CLOSED", 1: "LISTEN", 2: "SYN_SENT", 3: "SYN_RECV", 4: "ESTABLISHED", 5: "CLOSE_WAIT",
       6: "FIN_WAIT_1", 7: "CLOSING", 8: "LAST_ACK", 9: "FIN_WAIT_2", 10: "TIME_WAIT"}


def tcp_state(sock: socket.socket) -> str:
    if sys.platform.startswith("linux"):
        return LINUX[sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, 1)[0]]
    if sys.platform == "darwin":
        opt = getattr(socket, "TCP_CONNECTION_INFO", 0x106)
        return BSD[sock.getsockopt(socket.IPPROTO_TCP, opt, 1)[0]]
    return "UNKNOWN"


def settle():
    time.sleep(0.05)  # 讓 loopback 上的 FIN／ACK 有時間送達，再讀狀態


def show(step, **socks):
    states = ", ".join(f"{name}={tcp_state(s)}" for name, s in socks.items())
    print(f"{step} → {states}")


listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen(8)
show("1. listen()", listener=listener)

client = socket.create_connection(listener.getsockname())
show("2. connect() 回傳", client=client)        # 交握已完成，server 還沒 accept

server, _ = listener.accept()
show("3. accept() 取出連線", client=client, server=server)

client.sendall(b"GET /schedule/today\n")
client.shutdown(socket.SHUT_WR)              # 半關閉：我送完了，但還要收回應
settle()
show("4. client shutdown(WR)", client=client, server=server)

request = b""
while chunk := server.recv(1024):             # 讀到 b"" 代表收到 FIN（EOF）
    request += chunk
print(f"   server 讀到 EOF，完整請求 = {request!r}")
server.sendall(b"200 OK 3 classes\n")          # 半關閉後，反方向照樣能傳資料
server.close()
settle()
show("5. server close()", client=client)

reply = b""
while chunk := client.recv(1024):
    reply += chunk
print(f"   client 收到回應 = {reply!r}")
show("6. client 讀完", client=client)

assert request == b"GET /schedule/today\n" and reply == b"200 OK 3 classes\n"
client.close()                                # fd 關了，但核心裡的 TIME_WAIT 還在
listener.close()
```

```text
1. listen() → listener=LISTEN
2. connect() 回傳 → client=ESTABLISHED
3. accept() 取出連線 → client=ESTABLISHED, server=ESTABLISHED
4. client shutdown(WR) → client=FIN_WAIT_2, server=CLOSE_WAIT
   server 讀到 EOF，完整請求 = b'GET /schedule/today\n'
5. server close() → client=TIME_WAIT
   client 收到回應 = b'200 OK 3 classes\n'
6. client 讀完 → client=TIME_WAIT
```

逐行對照狀態機。第 2 行是本章最重要的觀察：server 根本還沒呼叫 `accept()`，client 已經是 ESTABLISHED，證明交握由核心完成，連線此刻正躺在 accept queue 裡。第 4 行，client 半關閉後進入 FIN_WAIT_2（FIN_WAIT_1 在 loopback 上只存在一瞬間，ACK 幾乎立刻回來），server 端則進入 CLOSE_WAIT；這時的 CLOSE_WAIT 是正常的，因為 server 程式正要讀取並回應。

接著 server 讀到 EOF，知道請求完整，送出回應後 close。第 5 行 client 已經進入 TIME_WAIT，但這時 client 還沒讀回應，資料仍安全地放在接收 buffer 裡，TIME_WAIT 並不影響讀取已經收到的資料。第 6 行讀完後狀態仍是 TIME_WAIT；最後的 `client.close()` 只是釋放 fd，核心會繼續保留 TIME_WAIT 直到計時器到期。如果你在 Linux 上執行完立刻打 `ss -tan state time-wait`，就能看到這條連線還在。

### 實驗二：accept queue 滿了會怎樣

這段程式重現故事中的 ①：listening socket 的 backlog 設為 2，然後**故意不呼叫 `accept()`**，模擬 gunicorn 的 worker 全部在忙。我們連續發起 5 個連線，每個 connect 只等 200 毫秒。

```python
import socket
import sys
import time

BACKLOG = 2

listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen(BACKLOG)                 # 之後故意不呼叫 accept()，模擬 worker 全部在忙
addr = listener.getsockname()

connected, results = [], []
for i in range(5):
    c = socket.socket()
    c.settimeout(0.2)                     # 正常的 connect 預設會等到 SYN 重傳放棄（Linux 上約兩分鐘）
    start = time.perf_counter()
    try:
        c.connect(addr)
        c.sendall(f"hello from client {i}\n".encode())  # 還沒被 accept，資料也收得進去
        connected.append(c)
        results.append(f"client {i}: connected in {(time.perf_counter() - start) * 1000:.1f} ms")
    except TimeoutError:
        c.close()                         # 立刻放棄，避免 SYN 重傳在之後又擠進佇列
        results.append(f"client {i}: connect timed out after 200 ms")

print(f"platform={sys.platform}, backlog={BACKLOG}")
for line in results:
    print(" ", line)

# 現在 worker 有空了：把 accept queue 裡已完成交握的連線一次取出
listener.settimeout(0.1)
accepted = []
try:
    while True:
        conn, _ = listener.accept()
        accepted.append(conn)
except TimeoutError:
    pass
for conn in accepted:
    print("  accept() 拿到，buffer 裡已有：", conn.recv(100).decode().strip())

assert len(connected) == len(accepted) >= BACKLOG
assert len(connected) < 5                # 佇列滿了以後的 SYN 被丟掉，不是被拒絕
for s in connected + accepted + [listener]:
    s.close()
```

```text
platform=darwin, backlog=2
  client 0: connected in 0.3 ms
  client 1: connected in 0.2 ms
  client 2: connect timed out after 200 ms
  client 3: connect timed out after 200 ms
  client 4: connect timed out after 200 ms
  accept() 拿到，buffer 裡已有： hello from client 0
  accept() 拿到，buffer 裡已有： hello from client 1
```

毫秒數每次執行都不同，但模式固定。前兩個 client 在不到 1 毫秒內就連上，還順利送出資料，即使 server 從來沒 accept；它們填滿了大小為 2 的 accept queue。從第三個開始，connect 不是被拒絕，而是**逾時**：核心默默丟掉 SYN，client 只能等待重傳。這正是故事裡 nginx 看到「upstream timed out while connecting」而不是「connection refused」的原因。在 Linux 上執行，你通常會看到 3 個 client 連上（backlog＋1），其餘逾時。

後半段模擬 worker 恢復：`accept()` 一口氣拿到兩條連線，而且 buffer 裡早就有 client 送來的資料。這說明另一個實務現象：client 以為請求已經送出，其實請求只是躺在 server 核心的 buffer 裡，要等應用程式有空才會被處理；如果排隊時間超過 client 的讀取逾時，client 會放棄，server 卻還是會處理這個已經沒人等的請求。

### 實驗三：四種 RST 與對應的 Python 例外

這段程式依序重現 10.9 節的情境 (a) 與 (c)，以及「對方已關閉還繼續寫」，並把例外與 errno 名稱印出來。errno 的數字在 Linux 和 macOS 上不同（例如 ECONNRESET 在 Linux 是 104、在 macOS 是 54），所以程式只印名稱。

```python
import errno
import socket
import struct
import time


def name(exc: OSError) -> str:
    return f"{type(exc).__name__}({errno.errorcode[exc.errno]})"  # errno 數字因 OS 而異，名稱一致


def pair(listener):
    c = socket.create_connection(listener.getsockname())
    s, _ = listener.accept()
    return c, s


listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen()

# 情境 1：連到沒人 listen 的 port → 對方核心直接回 RST
probe = socket.socket()
probe.bind(("127.0.0.1", 0))
dead_port = probe.getsockname()[1]
probe.close()                            # 拿到一個「確定沒人在聽」的 port
try:
    socket.create_connection(("127.0.0.1", dead_port), timeout=1)
except OSError as exc:
    case1 = name(exc)
print("1. connect 到沒人聽的 port →", case1)

# 情境 2：SO_LINGER(on, 0) 的 close → 送 RST 而不是 FIN，對方未送出的資料也一起丟掉
c, s = pair(listener)
s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
s.close()
time.sleep(0.05)
try:
    c.recv(100)
except OSError as exc:
    case2 = name(exc)
print("2. 對方 SO_LINGER=0 後 close →", case2)

# 情境 3：接收 buffer 還有沒讀的資料就 close → 核心改送 RST，提醒對方「你的資料我沒處理」
c, s = pair(listener)
c.sendall(b"POST /payment/notify ...")
time.sleep(0.05)
s.close()                                # 沒讀就關
time.sleep(0.05)
try:
    c.recv(100)
except OSError as exc:
    case3 = name(exc)
print("3. 對方沒讀完資料就 close →", case3)

# 情境 4：對方已 close，我方還在寫 → 第一次 send 成功（只是進了 buffer），對方回 RST，下一次才失敗
c, s = pair(listener)
s.close()
time.sleep(0.05)
log = []
for attempt in range(3):
    try:
        c.send(b"x")
        log.append(f"send#{attempt} ok")
    except OSError as exc:
        log.append(f"send#{attempt} {name(exc)}")
        break
    time.sleep(0.05)
print("4. 對方 close 後繼續寫 →", ", ".join(log))

assert "ECONNREFUSED" in case1
assert "ECONNRESET" in case2 and "ECONNRESET" in case3
assert log[0] == "send#0 ok" and ("EPIPE" in log[-1] or "ECONNRESET" in log[-1])
listener.close()
```

```text
1. connect 到沒人聽的 port → ConnectionRefusedError(ECONNREFUSED)
2. 對方 SO_LINGER=0 後 close → ConnectionResetError(ECONNRESET)
3. 對方沒讀完資料就 close → ConnectionResetError(ECONNRESET)
4. 對方 close 後繼續寫 → send#0 ok, send#1 BrokenPipeError(EPIPE)
```

第 1 行在 1 秒的逾時設定內立刻失敗，因為 RST 在一個 RTT 內就回來了，和實驗二的逾時形成強烈對比。第 2 行是刻意的中止：server 用 `SO_LINGER` 為 0 關閉，client 的 `recv()` 收到的不是 EOF，而是錯誤。第 3 行最容易在真實系統裡踩到：server 沒讀完請求就關閉連線（例如請求太大，程式直接回錯誤並 close），核心會送 RST，client 可能連 server 已經送出的錯誤回應都還沒讀到就被重置。這也是為什麼 HTTP server 在提早回應時，常會先讀掉（drain）剩餘的請求內容再關閉。

第 4 行展示一個反直覺的事實：對方已經關閉，第一次 `send()` 仍然**成功**，因為它只是把資料放進本機的送出 buffer。資料送到對方後，對方核心回 RST，第二次 `send()` 才失敗並得到 `EPIPE`。也就是說，「send 成功」從來不代表「對方收到了」，只代表「核心收下了」。要知道對方是否處理了請求，只能靠應用層的回應。

### 實驗四：重現並修正 CLOSE_WAIT 洩漏

這是故事事故的縮小版。課表服務（上游）對閒置超過 0.15 秒的連線主動關閉；教室入口 API 用連線池呼叫它。`LeakyPool` 是事故當時的寫法：歸還的連線直接放回去，從不檢查。`SafePool` 是修正版：重用前用 `MSG_PEEK` 偷看一眼，如果讀到 EOF 就 close 掉，另外提供 `reap()` 讓背景工作定期清理。

```python
import socket
import sys
import threading
import time

LINUX = {1: "ESTABLISHED", 6: "TIME_WAIT", 7: "CLOSED", 8: "CLOSE_WAIT"}
BSD = {0: "CLOSED", 4: "ESTABLISHED", 5: "CLOSE_WAIT", 10: "TIME_WAIT"}


def tcp_state(sock):
    if sys.platform.startswith("linux"):
        code = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, 1)[0]
        return LINUX.get(code, f"state{code}")
    code = sock.getsockopt(socket.IPPROTO_TCP, getattr(socket, "TCP_CONNECTION_INFO", 0x106), 1)[0]
    return BSD.get(code, f"state{code}")


UPSTREAM_IDLE = 0.15  # 課表服務：閒置超過 0.15 秒就主動關閉連線（真實系統常見 60 秒）


def schedule_service(listener):
    """上游服務：一條連線可以問很多次；閒置太久就 close()。"""
    def handle(conn):
        conn.settimeout(UPSTREAM_IDLE)
        with conn:
            try:
                while data := conn.recv(1024):
                    conn.sendall(b"OK " + data)
            except (TimeoutError, OSError):
                pass                      # 閒置逾時：離開 with，送出 FIN
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


class LeakyPool:
    """有 bug 的連線池：歸還的連線直接放回去，從不檢查對方是否已經關閉。"""
    def __init__(self, addr):
        self.addr, self.idle = addr, []

    def get(self):
        return self.idle.pop() if self.idle else socket.create_connection(self.addr)

    def put(self, conn):
        self.idle.append(conn)


class SafePool(LeakyPool):
    """修正版：取出前先偷看一眼，收到 FIN（recv 回 b""）的連線就 close 掉再換新的。"""
    def get(self):
        while self.idle:
            conn = self.idle.pop()
            if self._alive(conn):
                return conn
            conn.close()                  # 關鍵的一行：離開 CLOSE_WAIT
        return socket.create_connection(self.addr)

    def reap(self):
        """背景定期清理：把已被對方關閉的閒置連線 close 掉，回傳清掉幾條。"""
        alive = [c for c in self.idle if self._alive(c)]
        dead = [c for c in self.idle if c not in alive]
        for c in dead:
            c.close()
        self.idle = alive
        return len(dead)

    @staticmethod
    def _alive(conn):
        conn.setblocking(False)
        try:
            return conn.recv(1, socket.MSG_PEEK) != b""   # b"" 代表對方送過 FIN
        except BlockingIOError:
            return True                   # 沒資料也沒 FIN：連線還活著
        except OSError:
            return False                  # 例如已經被 RST
        finally:
            conn.setblocking(True)


def call(pool, path):
    conn = pool.get()
    conn.sendall(path.encode())
    try:
        reply = conn.recv(1024)
    except ConnectionResetError:
        reply = b"<RST>"                  # 依時序也可能先收到上游回的 RST
    pool.put(conn)
    return reply


listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen()
threading.Thread(target=schedule_service, args=(listener,), daemon=True).start()
addr = listener.getsockname()

for pool in (LeakyPool(addr), SafePool(addr)):
    label = type(pool).__name__
    held = [pool.get() for _ in range(4)]  # 晚上八點：4 個請求同時要連線
    for conn in held:
        pool.put(conn)
    time.sleep(UPSTREAM_IDLE + 0.1)        # 尖峰過後，上游把閒置連線關掉
    if label == "SafePool":
        print(f"{label}: reap() 關掉 {pool.reap()} 條已被上游關閉的連線")
    states = [tcp_state(c) for c in pool.idle]
    print(f"{label}: pool 裡 {len(states)} 條連線，狀態 {states}")
    reply = call(pool, "/schedule/today")
    print(f"{label}: 下一個請求拿到 {reply!r}")
    if label == "LeakyPool":
        assert states.count("CLOSE_WAIT") == 4 and reply in (b"", b"<RST>")
    else:
        assert "CLOSE_WAIT" not in states and reply == b"OK /schedule/today"
    for conn in pool.idle:
        conn.close()
listener.close()
```

```text
LeakyPool: pool 裡 4 條連線，狀態 ['CLOSE_WAIT', 'CLOSE_WAIT', 'CLOSE_WAIT', 'CLOSE_WAIT']
LeakyPool: 下一個請求拿到 b''
SafePool: reap() 關掉 4 條已被上游關閉的連線
SafePool: pool 裡 0 條連線，狀態 []
SafePool: 下一個請求拿到 b'OK /schedule/today'
```

第 1 行就是事故現場：尖峰時開的 4 條連線被歸還後閒置，上游逾時關閉，4 條全部停在 CLOSE_WAIT，而且只要 pool 還引用著它們，就永遠不會消失。真實系統裡每次尖峰都會多開一批，日積月累就是故事裡的 3,812 條。第 2 行是另一個症狀：下一個請求拿到死連線，`sendall()` 成功（實驗三第 4 行的現象），`recv()` 卻立刻回傳 `b""`，應用程式看到的是「上游回了空回應」，很容易被誤判為上游的 bug。

修正版的第 3 行說明 `reap()` 找到並關閉了 4 條死連線，於是第 4 行池子是空的，第 5 行的請求開了新連線並拿到正確回應。偵測的原理是 `recv(1, MSG_PEEK)`：用非阻塞模式偷看接收 buffer，不會把資料取走；回傳 `b""` 表示 FIN 已經抵達，丟出 `BlockingIOError` 表示沒資料也沒 FIN，連線還活著。成熟的 HTTP client 函式庫的連線池也做類似的檢查，但「檢查」和「送出請求」之間仍可能被上游關閉，所以第二道防線是把 client 端的閒置上限設得比上游的 keep-alive timeout 短，第三道防線是對 idempotent 請求在拿到死連線時重試一次。

### 實驗五：TIME_WAIT 擋住了重啟

最後一個實驗模擬「server 重啟後立刻 bind 同一個 port」，分別讓 server 或 client 先關閉連線，並比較有沒有設 `SO_REUSEADDR`。

```python
import errno
import socket
import time


def restart_trial(who_closes_first: str, reuse: bool) -> str:
    """模擬 server 重啟：舊 process 關閉後，新 process 立刻 bind 同一個 port。"""
    old = socket.socket()
    old.bind(("127.0.0.1", 0))
    old.listen()
    port = old.getsockname()[1]
    client = socket.create_connection(("127.0.0.1", port))
    conn, _ = old.accept()
    first, second = (conn, client) if who_closes_first == "server" else (client, conn)
    first.close()                          # 先 close 的一方是「主動關閉方」，之後進 TIME_WAIT
    time.sleep(0.02)
    second.close()
    time.sleep(0.05)
    old.close()                            # 舊 listener 也關了，port 上只剩可能的 TIME_WAIT

    new = socket.socket()
    if reuse:
        new.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        new.bind(("127.0.0.1", port))
        new.listen()
        return "bind ok"
    except OSError as exc:
        return f"{type(exc).__name__}({errno.errorcode[exc.errno]})"
    finally:
        new.close()


results = {}
for who in ("server", "client"):
    for reuse in (False, True):
        results[who, reuse] = restart_trial(who, reuse)
        print(f"先關的是 {who:<6}  SO_REUSEADDR={str(reuse):<5} → {results[who, reuse]}")

assert results["server", False].endswith("(EADDRINUSE)")   # server 端有 TIME_WAIT 擋住
assert results["server", True] == "bind ok"
assert results["client", False] == "bind ok"               # TIME_WAIT 在 client 那邊
```

```text
先關的是 server  SO_REUSEADDR=False → OSError(EADDRINUSE)
先關的是 server  SO_REUSEADDR=True  → bind ok
先關的是 client  SO_REUSEADDR=False → bind ok
先關的是 client  SO_REUSEADDR=True  → bind ok
```

第 1 行是很多人第一次寫 server 就遇到的「Address already in use」：server 先關閉連線，成為主動關閉方，那條連線的 TIME_WAIT 佔著 server 的 port，新 process 沒設 `SO_REUSEADDR` 就 bind 不上。第 2 行設了 `SO_REUSEADDR` 立即成功，這就是幾乎所有 server 框架預設開啟它的原因。第 3、4 行由 client 先關，TIME_WAIT 落在 client 的臨時 port 上，server 的 port 很乾淨，有沒有設都能 bind。這四行用一個實驗驗證了「TIME_WAIT 屬於主動關閉方」，也說明 `SO_REUSEADDR` 解決的是重啟問題，與 client 端耗盡來源 port 是兩回事。

## 10.12 在工作上怎麼用

事故隔天，阿德和小晴把這次學到的東西依角色整理成團隊的檢查清單。

**後端工程師：呼叫任何下游服務都要想清楚三件事。** 第一，連線逾時與讀取逾時分開設定，連線逾時通常 1 到 3 秒就夠（同一個機房內交握只要不到 1 毫秒），讀取逾時依下游的 p99 延遲決定；不設的話，SYN 被丟包時會卡兩分鐘。第二，重用連線，並確認連線池的閒置上限比下游 keep-alive timeout 短，重用前會偵測死連線。第三，所有 socket 都用 `with` 或 `try/finally` 關閉，連錯誤路徑也是。程式碼審查時看到裸的 `socket.socket()` 卻沒有對應的 close，就該提問。

**SRE：用一組固定指令快速判斷 TCP 層的健康度。** 下面這組指令可以在一分鐘內回答「連線狀態正不正常」：

```bash
ss -s                                    # 總覽：各狀態數量、TIME_WAIT 與 orphan 數
ss -ltn                                  # 每個 listening socket 的 accept queue：Recv-Q 接近 Send-Q 就危險
ss -tan state close-wait | wc -l         # 持續增加 = 本機程式沒 close
ss -tan state syn-sent                   # 本機連不出去的目標
nstat -az TcpExtListenOverflows TcpExtListenDrops TcpExtTCPSynRetrans   # 隔幾秒看增量
ls /proc/<pid>/fd | wc -l ; grep 'open files' /proc/<pid>/limits          # fd 用量與上限
lsof -nP -iTCP -sTCP:CLOSE_WAIT          # macOS 與 Linux 都可用，依 process 列出 CLOSE_WAIT
```

這組指令裡，`ss -s` 給你全貌；`ss -ltn` 的 Recv-Q 只要經常不是 0，就表示應用程式 accept 的速度跟不上；CLOSE_WAIT 用 `wc -l` 每分鐘記一次，畫成時間序列，斜率大於 0 就是洩漏。把 `TcpExtListenOverflows` 與 CLOSE_WAIT 數量納入監控與告警，故事裡的事故就能在學生受影響前幾天被發現，因為 CLOSE_WAIT 是一天一天累積上去的。

判斷流程可以畫成這樣：

```text
 症狀：連不上／很慢／被斷線
   │
   ├─ connect 立刻失敗（ECONNREFUSED）
   │     └─► 服務沒起來？port 對嗎？listen 在 127.0.0.1 還是 0.0.0.0？（ss -ltn）
   │
   ├─ connect 逾時（ETIMEDOUT）
   │     ├─► 對方 ss -ltn 的 Recv-Q 接近 Send-Q？ ── 是 ─► 應用程式 accept 太慢：看 fd、worker、CPU
   │     └─► 否：tcpdump 看 SYN 有沒有到對方 ─► 沒到：防火牆、security group、路由（第 6、7 章）
   │
   ├─ 傳到一半 ECONNRESET
   │     └─► 對方重啟或 crash？LB／NAT 閒置逾時？對方沒讀完就 close？（tcpdump 'tcp[tcpflags] & tcp-rst != 0'）
   │
   └─ EMFILE／EADDRNOTAVAIL
         ├─► EMFILE：數 CLOSE_WAIT 與 fd，找洩漏的程式碼
         └─► EADDRNOTAVAIL：數連向同一目的地的 TIME_WAIT，改用連線重用
```

這張流程圖的第一刀，就是 10.4 節區分的「被拒絕」與「逾時」，兩者的成因幾乎不重疊。逾時那一支再用對方的 `ss -ltn` 一分為二：accept queue 滿代表問題在應用程式，沒滿才往網路設備找。

**前端工程師：讀懂瀏覽器的錯誤分類。** DevTools 的 Network 面板顯示請求失敗時，`ERR_CONNECTION_REFUSED`、`ERR_CONNECTION_TIMED_OUT`、`ERR_CONNECTION_RESET` 都是 TCP 層的問題，請求根本沒有得到 HTTP 回應，不要去後端 log 找 4xx、5xx；`ERR_EMPTY_RESPONSE` 則表示連線建立了，但 server 沒回任何資料就關閉，常見於後端 worker 在處理中被殺掉。回報問題時附上錯誤名稱，能讓後端少猜一輪。

**影音工程師：長連線要對抗所有中間設備的閒置逾時。** Joe 負責的 WebSocket 教室與 WHEP 觀看端都是長時間的連線，路徑上的 LB、NAT、防火牆各有自己的閒置逾時，連線被默默丟棄時兩端都不知道。做法是應用層心跳的間隔短於路徑上最短的閒置逾時，並在 client 實作「斷線就重連並補發」的邏輯（第 33 章）。部署新版本時，要讓舊 process 優雅地送 FIN 或 close frame，而不是被直接殺掉造成大量 RST。

**資安工程師：從 TCP 行為看異常。** Rita 會監控 SYN_RECV 數量與 `Possible SYN flooding` 的核心訊息，確認 SYN cookies 開啟；對外服務的 security group 只開必要的 port，因為對關閉的 port，主機回 RST 等於告訴掃描者「這台主機在線」，而防火牆直接丟包則什麼都不透露。這也是為什麼對外掃描時「filtered」（沒有回應）和「closed」（回 RST）是兩種不同的結果。

## 10.13 常見錯誤與除錯

下表收錄與 TCP 連線生命週期相關、在聲聲 Live 與一般團隊最常見的錯誤。每一列都可以用本章的工具在幾分鐘內確認。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| `Too many open files`，同時有大量 CLOSE_WAIT | 程式沒有 close 被對方關閉的連線（連線池不檢查、錯誤路徑沒關） | `ss -tanp state close-wait` 依遠端分組；`lsof -p <pid>` 數 fd | 用 `with`／`try/finally`；連線池重用前檢查 EOF；閒置上限短於上游 keep-alive |
| 尖峰時 connect 逾時，對方 CPU 卻不高 | accept queue 滿：應用程式 accept 太慢（worker 被阻塞、fd 用光） | 對方 `ss -ltn` 的 Recv-Q 接近 Send-Q；`TcpExtListenOverflows` 增加 | 修正讓 accept 變慢的根因；必要時增加 worker；backlog 只用來吸收短暫尖峰 |
| 重啟 server 出現 `Address already in use` | 舊連線的 TIME_WAIT 佔住 port，新 socket 沒設 `SO_REUSEADDR` | `ss -tan state time-wait '( sport = :8000 )'` | bind 前設 `SO_REUSEADDR`；或確認真的沒有舊 process 還在 listen |
| 壓測或批次工作出現 `Cannot assign requested address` | 對同一目的地大量短連線，來源 port 被 TIME_WAIT 佔滿 | `ss -tan state time-wait dst 10.20.3.15 \| wc -l` 接近 port 範圍大小 | 改用 keep-alive／連線池；必要時擴大 port 範圍或評估 `tcp_tw_reuse` |
| 偶發「Remote end closed connection without response」或空回應 | 連線池拿到已被上游關閉的閒置連線 | 對照錯誤時間點與上游 keep-alive timeout；tcpdump 看上游先送 FIN | 重用前檢查；閒置上限短於上游；對 idempotent 請求重試一次 |
| 長連線閒置後第一個請求得到 `ECONNRESET` 或卡住 | LB、NAT、防火牆的閒置逾時刪除了連線狀態 | 抓包看閒置後的第一個封包是否換來 RST 或沒有回應；查設備的 idle timeout | 應用層心跳或 TCP keepalive 間隔短於 idle timeout；client 自動重連 |
| client 收到 `ECONNRESET`，但 server 明明送了錯誤回應 | server 沒讀完請求就 close，核心送 RST 蓋掉回應 | tcpdump 看到 server 回應後緊接 RST；server 接收 buffer 有剩餘資料 | 提早回應前先讀掉剩餘 body 或用 `shutdown(SHUT_WR)` 後再等一下 |
| 呼叫某服務偶爾卡住兩分鐘才報錯 | 沒設連線逾時，SYN 被防火牆丟包後重傳到放棄 | `ss -tan state syn-sent` 看到卡住的連線；log 中的錯誤時間差約 127 秒 | 設定 connect timeout（例如 `create_connection(addr, timeout=3)`），修防火牆規則 |
| health check 通過，但使用者請求全部逾時 | health check 只做 TCP 連線，交握由核心完成，應用程式其實卡死 | 用 curl 打真正的 HTTP 端點；看 accept queue 是否堆積 | health check 改為 HTTP 層並檢查回應內容 |

除錯時的通則是：**先看狀態，再看程式**。CLOSE_WAIT 指向本機程式，大量 FIN_WAIT_2 指向對方程式停在 CLOSE_WAIT，SYN_SENT 堆積指向路徑或對方的 accept queue，TIME_WAIT 多半不用管。有了方向再讀程式碼，比從程式碼猜網路問題快得多。

## 10.14 動手練習

1. **觀察 TIME_WAIT 真的還在**（真實工具）。在 Linux 上執行 10.11 節的實驗一，程式結束後立刻執行 `ss -tan state time-wait | grep 127.0.0.1`，然後每 10 秒再看一次。
   答案要點：你會看到 client 那一端的四元組停在 TIME-WAIT，約 60 秒後消失（macOS 用 `netstat -an -p tcp | grep TIME_WAIT`，約 30 秒）。如果把程式改成 server 先關，TIME_WAIT 的本地 port 會變成 server 的 port。

2. **用 tcpdump 看交握與揮手**（真實工具）。在一個終端執行 `sudo tcpdump -ni lo0 -S 'tcp port 8765'`（Linux 用 `-i lo`），另一個終端執行 `python3 -m http.server 8765 --bind 127.0.0.1`，再用 `curl -s 127.0.0.1:8765/ > /dev/null` 發一個請求。
   答案要點：數出 SYN、SYN+ACK、ACK 三個 segment；用 `-S` 看到的絕對序號驗證「SYN 佔一個序號」；觀察結尾是誰先送 `[F.]`。http.server 回應後由 server 先關閉（HTTP/1.0 行為），所以 TIME_WAIT 落在 server 端，可以用 `ss` 或 `netstat` 驗證。

3. **延伸實驗二：讓 accept 慢下來**。改寫實驗二，讓一個 thread 每 100 毫秒才 `accept()` 一次，同時有 20 個 client 以 5 秒的 connect timeout 連線，統計成功數與每個 connect 的耗時分布。
   答案要點：當 accept 速度低於連線到達速度，佇列滿後的 client 會經歷 SYN 重傳，connect 耗時不是平滑增加，而是群聚在重傳的時間點附近（Linux 上約 1 秒、3 秒）。這是在 production 看到 connect 延遲的 p99 剛好卡在 1 秒或 3 秒附近時的典型原因：有 SYN 被丟掉了。

4. **延伸實驗四：加上重試**。替 `LeakyPool` 的 `call()` 加上「拿到 `b""` 或 `ConnectionResetError` 時，丟掉這條連線、開新連線重試一次」，觀察是否能在不檢查連線的情況下讓請求成功，並思考這個做法對 `POST /payment` 這種請求是否安全。
   答案要點：重試能讓讀取類請求成功，但死連線仍會在池中，CLOSE_WAIT 數量不會下降，必須同時 close。對非 idempotent 請求，「送出後沒收到回應」可能代表上游已經處理了，盲目重試可能造成重複扣款，要搭配 idempotency key（第 24 章）。

5. **手算來源 port 上限**。聲聲 Live 的通知服務每秒要對同一個推播閘道（198.51.100.50:443）送 900 個請求，每個請求一條新連線，由 client 主動關閉，Linux 預設 port 範圍與 TIME_WAIT 時間。會不會出問題？有哪些解法？
   答案要點：28,232 ÷ 60 ≈ 470 條／秒，900 條／秒遠超過上限，大約 31 秒後就會開始出現 `EADDRNOTAVAIL`。首選解法是 keep-alive 連線重用（幾十條長連線就夠）；其次是增加來源 IP 或擴大 port 範圍；`tcp_tw_reuse` 只是補強。

## 本章重點整理

- TCP 連線不是一條實體線路，而是兩端核心各自保存的狀態（TCB），以四元組識別；中間的路由器完全不知道連線存在。
- TCP header 固定 20 bytes、最多 60 bytes；SYN、ACK、FIN、RST 四個旗標構成連線生命週期的語言，tcpdump 用 `S`、`.`、`F`、`R` 表示它們。
- 三向交握用三個 segment 讓雙方交換並確認 ISN；SYN 與 FIN 都佔用一個序號，`connect()` 大約花一個 RTT。
- ISN 依 RFC 6528 由計時器加上四元組的秘密雜湊產生，既避免新舊連線的序號混淆，也讓外人難以猜測；序號比較必須考慮 32 bit 回繞。
- 交握由核心完成，`accept()` 只是從 accept queue 領走已建立的連線；listen 的 backlog 決定 accept queue 上限，並受 `somaxconn` 限制。
- accept queue 滿時 Linux 預設丟掉 SYN 而不是回 RST，client 看到的是逾時；根因幾乎都是應用程式 accept 太慢，而不是 backlog 太小。
- 「被拒絕」（RST，立即失敗）與「逾時」（沒有回應，Linux 預設約 127 秒）是兩種不同的問題，是除錯時的第一個分岔點。
- 四次揮手中兩個方向各自用 FIN 結束；`shutdown(SHUT_WR)` 可以半關閉，讓對方讀到 EOF 後仍能回應。
- TIME_WAIT 屬於主動關閉方，持續 2×MSL（Linux 60 秒），用來保證最後的 ACK 能重送並讓舊 segment 消失；它的成本是佔住四元組，正解是連線重用。
- CLOSE_WAIT 屬於被動關閉方，沒有計時器，只有應用程式 close 才會離開；持續增加就是本機程式的洩漏，最後以 `EMFILE` 爆發。
- RST 代表連線立即作廢，出現在連到沒人聽的 port、半開連線、應用程式中止與中間設備逾時；`send()` 成功只代表核心收下資料，不代表對方收到。
- `ss -ltn` 的 Recv-Q／Send-Q、`ss -tan state …` 與 `nstat` 的 ListenOverflows 計數器，是在 production 判斷 TCP 連線健康度的核心工具。

## 延伸問答

> [!question]- Q1. 為什麼 TIME_WAIT 是在主動關閉的一方，而不是被動關閉的一方？
> TIME_WAIT 的兩個目的都和「最後一個 segment」有關。四次揮手的最後一個 segment 是主動關閉方送出的 ACK；如果它遺失，被動方會重傳 FIN，而只有主動方需要記得這條連線才能再回一次 ACK。被動方送出 FIN 之後收到 ACK 就確定一切完成，沒有任何東西需要再等，所以可以直接進入 CLOSED。
>
> 第二個目的是讓舊 segment 在網路上消失，避免同一個四元組的新連線收到它們。這件事只需要一方擋住四元組的重用就夠了，而主動方剛好是最後一個知道「一切結束」的一方，由它負責最自然。實務上的推論是：如果你希望 TIME_WAIT 落在哪一邊，就讓那一邊先關。例如讓 server 主動關閉，TIME_WAIT 分散在 server 的眾多四元組上，就不會耗盡 client 的來源 port。

> [!question]- Q2. 你在 production 主機上看到 12,000 條 TIME_WAIT 與 3 條 CLOSE_WAIT，同事建議立刻調整核心參數。你會怎麼判斷？
> 先判斷 TIME_WAIT 是否造成實際問題。TIME_WAIT 不佔 fd 和應用程式記憶體，Linux 上幾萬條也只用幾 MB；它唯一會造成的故障是本機當 client 時，對同一個目的地的來源 port 被佔滿，症狀是 `EADDRNOTAVAIL`。所以要看 TIME_WAIT 的四元組是否集中在同一個遠端位址，以及 log 中有沒有 `Cannot assign requested address`。如果它們分散在大量 client 位址上（主機是 server 且主動關閉），這只是正常現象，不需要處理。
>
> 3 條 CLOSE_WAIT 在數量上很少，但它比 TIME_WAIT 更值得追：要觀察它是否持續增加。如果每次看都是不同的連線、數量穩定在個位數，多半是應用程式正在處理中的正常短暫狀態；如果數量隨時間單調上升，就是洩漏，最終會耗盡 fd。結論是不要急著調參數，尤其不要去找已經被移除的 `tcp_tw_recycle`，而是先確認症狀，再決定是改用連線重用還是修程式。

> [!question]- Q3. 手算：client ISN 是 4294967290，它在 SYN 之後送出 10 bytes 資料，然後送 FIN。server 對這個 FIN 的 ACK，確認號是多少？
> SYN 佔用一個序號，所以第一個資料 byte 的序號是 ISN＋1＝4294967291。10 bytes 資料佔用 4294967291 到 4294967300，但序號只有 32 bit，必須對 2³² 取餘數：4294967296 回繞成 0，所以這 10 個 byte 的序號依序是 4294967291 到 4294967295，再接 0 到 4。
>
> FIN 的序號是下一個號碼 5，FIN 本身也佔用一個序號，所以 server 確認 FIN 時，確認號是 6。這題同時考了三件事：SYN 佔一個號、FIN 佔一個號、序號運算要 mod 2³²。實作封包分析工具時，如果直接用整數大小比較，會在回繞的那一刻把新資料誤判成舊資料，這就是本章程式裡 `seq_lt` 要用差值判斷的原因。

> [!question]- Q4. 面試題：listen 的 backlog 是什麼？把它從 128 調到 65535 能解決連線逾時嗎？
> 在 Linux 上，backlog 是 accept queue 的上限：已經完成三向交握、等待應用程式 `accept()` 的連線最多能排幾條，而且實際值會被 `net.core.somaxconn` 截斷。另有一個 SYN queue 存放還在交握中的連線，受 `tcp_max_syn_backlog` 等參數影響。佇列滿時，Linux 預設丟棄 SYN，所以 client 看到的是 connect 逾時而不是被拒絕。
>
> 調大 backlog 只能吸收「短暫」的尖峰：如果應用程式的 accept 速度平均而言跟得上到達速度，只是瞬間湧入，較大的佇列能避免丟包。但如果應用程式長期 accept 太慢（worker 被阻塞、fd 用光、CPU 滿載），佇列再大也會被填滿，而且排在佇列裡的請求等待時間更長，可能在被處理前就超過 client 的逾時，讓 server 白做工。所以要先用 `ss -ltn` 和 `TcpExtListenOverflows` 確認佇列滿，再找出 accept 變慢的根因。

> [!question]- Q5. 看 log 找原因：nginx 的 error log 同時出現大量「upstream prematurely closed connection while reading response header from upstream」，但 gunicorn 沒有任何錯誤。可能是什麼？
> 這個訊息表示 nginx 在等回應 header 時，upstream 那一端送來 FIN 關閉了連線；如果收到的是 RST，nginx 記的會是「recv() failed (104: Connection reset by peer)」。gunicorn 沒有錯誤 log，代表應用程式層沒有拋出例外，問題可能出在連線的生命週期。最常見的成因是 keep-alive 的時序：nginx 對 upstream 啟用了連線重用，而 gunicorn 的 keep-alive timeout 較短（預設 2 秒），gunicorn 剛好在 nginx 送出新請求的同一時刻關閉閒置連線，nginx 就把請求送進一條正在關閉的連線。
>
> 另一個可能是 worker 被殺掉：gunicorn 的 worker 處理超過 `--timeout` 被 arbiter 終止，或被 OOM killer 殺掉，連線隨 process 結束而關閉，這時 gunicorn 的 arbiter log 會有 worker timeout 或退出的紀錄，要分開查。確認方法是在 nginx 與 gunicorn 之間 tcpdump，看 FIN 是誰先送、與請求的時間差。修正方向是讓 upstream 端的 keep-alive timeout 長於 nginx 對 upstream 的閒置時間，並檢查 worker 是否異常結束。

> [!question]- Q6. 設計取捨：server 想快速釋放連線，用 SO_LINGER 設 0 關閉可以完全避開 TIME_WAIT，為什麼一般不建議？
> `SO_LINGER(on, 0)` 讓 `close()` 送出 RST 而不是 FIN。好處是連線立刻消失、不留 TIME_WAIT。代價有三個：第一，送出 buffer 裡還沒送完的資料會被直接丟掉，對方可能收不到完整的回應；第二，對方應用程式看到的是 `ECONNRESET` 錯誤，而不是正常的 EOF，很多 client 會把它記成失敗並重試；第三，失去 TIME_WAIT 的保護，同一個四元組很快建立新連線時，舊連線的迷途 segment 可能混進來。
>
> 因此它只適合確定要中止的情況，例如偵測到惡意或協定錯誤的 client、或者測試中刻意模擬 RST。若真正的問題是 TIME_WAIT 太多，應先檢查 TIME_WAIT 落在哪一端、是否真的造成來源 port 耗盡；server 端的 TIME_WAIT 通常無害，client 端的則用連線重用解決。用 RST 換取乾淨的 `ss` 輸出，是用正確性換外觀。

> [!question]- Q7. 你的服務對外只開 443。安全掃描報告說某台主機的 22 port「closed」而不是「filtered」，這兩者在 TCP 層有什麼差別？哪個比較好？
> 掃描工具送出 SYN 後，如果收到 RST，代表主機在線、封包抵達了主機，只是那個 port 沒人 listen，報告為「closed」；如果完全沒有回應（或收到 ICMP 不可達），代表封包在路上被防火牆丟掉，報告為「filtered」。這和本章的「被拒絕 vs 逾時」是同一件事，只是從掃描者的角度看。
>
> 從防禦角度，「closed」本身不代表有漏洞，但它透露了兩個資訊：主機存在，而且封包能穿過前面的網路設備抵達主機。對外的主機通常希望由 security group 或防火牆在主機之前就丟棄不需要的流量，讓不該開放的 port 呈現 filtered，減少暴露的資訊，也避免主機自己處理掃描流量。對內部服務，回 RST 反而能讓呼叫方快速失敗，不必等逾時，所以要依位置決定策略。

> [!question]- Q8. 實驗一中，client 在 shutdown(SHUT_WR) 之後處於 FIN_WAIT_2。如果 server 程式永遠不 close，client 會永遠停在 FIN_WAIT_2 嗎？
> 不一定，要看 client 的 socket 是否還被應用程式持有。如果 client 只是 `shutdown(SHUT_WR)`，fd 還開著，連線仍屬於應用程式，而對方確實可能還會送資料過來，Linux 不會擅自結束它，client 可以一直在 FIN_WAIT_2 等待，對方則一直在 CLOSE_WAIT。這時兩端的問題都出在 server 程式沒有 close。
>
> 如果 client 已經呼叫 `close()`，連線就成為沒有 fd 對應的「孤兒」（orphan）。Linux 不會讓孤兒在 FIN_WAIT_2 永遠存在，`net.ipv4.tcp_fin_timeout`（預設 60 秒）就是用來限制這段時間的，到期後直接釋放。這也是許多人誤以為 `tcp_fin_timeout` 控制 TIME_WAIT 的來源。實務上，看到大量 FIN_WAIT_2 時，要去對端主機找 CLOSE_WAIT，兇手通常在那裡。

## 延伸閱讀

- RFC 9293〈Transmission Control Protocol (TCP)〉：TCP 的現行規格，含 header 格式、狀態機與 MSL 的定義
- RFC 6528〈Defending against Sequence Number Attacks〉：ISN 的產生方式
- RFC 4987〈TCP SYN Flooding Attacks and Common Mitigations〉：SYN flood 與 SYN cookies 等防禦的整理
- RFC 5961〈Improving TCP's Robustness to Blind In-Window Attacks〉：RST 與 SYN 的 challenge ACK 機制
- RFC 7323〈TCP Extensions for High Performance〉：Window Scale 與 Timestamps 選項
- W. Richard Stevens、Kevin R. Fall《TCP/IP Illustrated, Volume 1: The Protocols》（第二版）：TCP 連線管理的章節
- Linux man-pages：tcp(7)、listen(2)、socket(7)、ss(8)
