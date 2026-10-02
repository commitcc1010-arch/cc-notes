---
chapter: 38
title: 直播協定：RTMP、SRT、HLS 與 WHIP
part: 8
---

# 第 38 章　直播協定：RTMP、SRT、HLS 與 WHIP

> [!abstract] 本章地圖
> **核心問題**：一場直播從講者的編碼器到上千名觀眾的播放器，中間經過哪些協定？為什麼推流要用 SRT、觀看要用 HLS，而延遲與穩定性又是怎麼在每一段被換來換去的？
>
> **你會學到**：
> - 畫出直播的端到端管線（編碼 → ingest → 轉碼 → 封裝 → CDN → 播放器），並估算每一段貢獻多少延遲
> - 讀懂 RTMP 的 chunk 與 Enhanced RTMP 的改動，說明 RTMP 為什麼在丟包的網路上會崩潰
> - 解釋 SRT 如何在 UDP 上做「有期限的重傳」：序號與 timestamp、NAK、TSBPD、too-late drop，並依 RTT 與丟包率選 latency
> - 設定 SRT 的 caller／listener／rendezvous、passphrase 與 stream ID，並避開 ffmpeg latency 單位的陷阱
> - 逐行讀懂 HLS 的 media playlist，算出傳統 HLS 與 LL-HLS 的延遲，知道 DASH、CMAF、WHIP／WHEP 各自的位置
> - 用 Python 在 127.0.0.1 模擬 SRT 式傳輸與 LL-HLS 的 blocking reload，親手量出 latency 設定與到達率、segment 長度與延遲的關係
>
> **前置知識**：第 9 章（UDP 與 socket）、第 11 章（ACK 與重傳）、第 12 章（擁塞與吞吐量）、第 25 章（CDN 與快取）、第 34 章（frame、GOP、codec 與延遲的組成）、第 36 章（WebRTC 的 ICE 與 DTLS-SRTP）

## 38.1 故事：京都飯店裡的公開講座

聲聲 Live 每個月有一場免費的公開講座，平常由辦公室攝影棚的硬體編碼器（10.30.0.21）用 SRT 推流到雲端的直播 ingest（`live.shengsheng.example`，203.0.113.25，第 4 章）。九月那場特別一點：日文老師美咲人在京都參加研討會，決定直接在飯店房間開講，筆電上裝 OBS（一套免費的直播軟體），照著網路上的教學把推流設定成 RTMP，伺服器填 ingest 的 RTMP 位址、再貼上一串 stream key。

晚上七點半開播，一千八百名觀眾湧入。前十分鐘還算順利，之後聊天室開始洗版：「卡住了」「畫面一直轉圈」「聲音斷斷續續」。OBS 右下角的狀態列顯示「丟棄的 frame（網路）18%」，上傳 bitrate 在 4.5 Mbps 與 1 Mbps 之間大幅跳動。更尷尬的是問答時間：主持人說「有問題請在聊天室發問」，接下來整整二十幾秒聊天室一片安靜，等美咲開始講下一個主題時，問題才一口氣湧進來，美咲只好不停地說「回到剛剛那個問題……」。

隔天的檢討會上，影音工程師 Joe 在白板上畫了整條直播管線，把問題拆成兩半。第一半是**推流**（從講者到 ingest）：飯店 Wi-Fi 到 ingest 的 RTT 約 80 ms、丟包約 3%，RTMP 跑在 TCP 上，丟包讓 TCP 的吞吐量跌到撐不住 4.5 Mbps，OBS 的送出 buffer 塞滿，只好丟 frame。第二半是**觀看**（從 ingest 到觀眾）：轉碼後切成 6 秒一段的 HLS，播放器照規範要落後直播邊緣至少三段，光這一項就是 18 秒，加上編碼、轉碼與 CDN，觀眾看到的畫面比美咲本人晚了二十多秒，問答當然接不上。

```text
 美咲的筆電（OBS）                   聲聲 Live 雲端                                      1,800 名觀眾
 ┌────────────┐  RTMP over TCP       ┌──────────────┐   ┌────────┐   ┌──────────┐   ┌─────┐   ┌──────────┐
 │ 擷取＋編碼 │  ─────────────────►  │    ingest    │──►│  轉碼  │──►│ 封裝 HLS │──►│ CDN │──►│  播放器  │
 │    OBS     │  飯店 Wi-Fi          │ 203.0.113.25 │   │ABR 階梯│   │ 6 秒一段 │   │     │   │落後 3 段 │
 └────────────┘  RTT 80 ms、丟包 3%  └──────────────┘   └────────┘   └──────────┘   └─────┘   └──────────┘

  ① TCP 遇到丟包就降速、整條資料流排隊等重傳          ② 3 × 6 秒 = 18 秒的 hold-back
     → 吞吐量 < 4.5 Mbps → OBS 丟 frame、觀眾卡頓        → 加上其他各段，延遲 20 多秒
```

這張圖要分兩段讀。左半邊的 ① 是「穩定性」問題：推流的那一跳只有一條、跨越品質最差的網路，而 RTMP 的可靠性來自 TCP，TCP 對丟包的反應是降速並讓後面的資料全部等待，所以網路一不穩，整場直播就跟著不穩。右半邊的 ② 是「延遲」問題：HLS 為了讓上千人透過 CDN 穩定觀看，用「切成檔案、預留幾段 buffer」換取穩定，代價是好幾個 segment 長度的延遲。Joe 的結論是：推流改用 SRT，在 UDP 上用有期限的重傳對抗丟包；觀看端改用 LL-HLS，把延遲壓到幾秒；真正需要即時互動的少數人（例如上台提問的學生）則走 WebRTC。

小晴被指派協助這次改版，第一個問題就問倒了自己：同樣是「可靠傳輸」，SRT 跟 TCP 差在哪？SRT 的 latency 設 120 ms 和設 500 ms 有什麼不同？HLS 的 playlist 裡那些 `#EXT-X-` 開頭的行又是什麼意思？這一章就沿著 Joe 畫的這條管線，從推流到觀看一段一段拆開，章末的動手做會用 Python 重現「latency 設定 vs 到達率」與「segment 長度 vs 延遲」這兩個 Joe 用來說服團隊的實驗。

## 38.2 直播的端到端管線

在拆個別協定之前，先把整條管線的分工看清楚。業界習慣把直播分成兩段：**contribution**（貢獻端，也叫 first mile）是從現場把一路高品質訊號送進平台，通常是一對一、量少但品質要求高；**distribution**（分發端，也叫 last mile）是從平台把內容送給大量觀眾，一對多、量大、必須能透過 CDN 擴展。這兩段的需求差異很大，所以幾乎沒有一個協定能同時做好兩件事，這也是直播系統總是「推流一套協定、觀看另一套協定」的根本原因。

```text
  contribution（一對一、少量、要穩）  distribution（一對多、大量、要能擴展）

 ┌──────────┐                  ┌──────────┐   ┌───────────────┐   ┌───────────┐   ┌────────┐   ┌──────────┐
 │  編碼器  │ SRT／RTMP／WHIP  │  ingest  │──►│  轉碼（ABR）  │──►│  封裝器   │──►│ origin │──►│ CDN edge │──► 播放器
 │OBS／硬體 │ ───────────────► │ listener │   │1080p 4.5 Mbps │   │ HLS／DASH │   │        │   │   快取   │    HLS／DASH
 │          │ UDP 或 TCP       │          │   │ 720p 2.5 Mbps │   │ CMAF 片段 │   │        │   │          │
 │          │                  │          │   │ 480p 1.2 Mbps │   │ playlist  │   │        │   │          │
 │          │                  │          │   │ 360p 0.7 Mbps │   │           │   │        │   │          │
 │          │                  │          │   │ 音訊 128 kbps │   │           │   │        │   │          │
 └──────────┘                  └──────────┘   └───────────────┘   └───────────┘   └────────┘   └──────────┘
                                    │                                                                           ▲
                                    └────────────── WebRTC（WHEP，經 SFU）：少數需要 < 1 秒的觀眾 ──────────────┘
```

由左往右讀。**編碼器**把畫面壓縮成 H.264 或 AV1 等 codec，並決定 GOP 與 bitrate（第 34 章）。**ingest** 是平台接收推流的入口，要扛住不穩的網路，並驗證推流者有沒有權限推到這個頻道。**轉碼**把一路 1080p 的來源轉成多個解析度與 bitrate 的版本，叫做 **ABR 階梯**（adaptive bitrate ladder），讓網路差的觀眾自動切到較低的版本。**封裝器**（packager）把轉碼後的資料切成一段一段的檔案（segment），並產生描述它們的清單（playlist 或 manifest）。**origin** 是 CDN 回源的地方，edge 把 segment 快取在靠近觀眾的地方。最下面那條 WebRTC 路線給少數需要極低延遲的觀眾，經過 SFU（第 37 章）而不是 CDN，成本高很多。

每一段都會加上延遲，而且延遲是累加的。下表是聲聲 Live 改版前後的延遲預算，數字是量級而非精確值，實際要以自己的系統量測為準：

| 管線階段 | 延遲從哪來 | 改版前（RTMP＋6 秒 HLS） | 改版後（SRT＋LL-HLS） |
|---|---|---|---|
| 擷取與編碼 | 編碼器的 lookahead、B-frame、rate control buffer | 約 0.5–1 s | 約 0.2–0.5 s（低延遲調校） |
| contribution 傳輸 | RTT、重傳、TCP 排隊或 SRT 的 latency 設定 | 0.1 s 到數秒（不穩） | 固定為 SRT latency，例如 0.5 s |
| 轉碼 | 解碼、縮放、重新編碼 | 約 0.5–1 s | 約 0.5–1 s |
| 封裝 | 要等一個 segment（或 part）完成才能發布 | 6 s | 0.5 s（part） |
| CDN 與下載 | 回源、edge 快取、下載時間 | 約 0.1–0.5 s | 約 0.1–0.5 s |
| 播放器 buffer | 規範要求落後直播邊緣一段距離 | 3 × 6 s = 18 s | 約 3 × 0.5 s = 1.5 s |
| **合計** | | **約 20–27 s** | **約 3–5 s** |

這張表最重要的觀察是：傳統 HLS 的延遲大部分不是網路造成的，而是「segment 長度」被乘了好幾次。封裝要等一個 segment 完成，播放器又要預留三個 segment，所以 segment 從 6 秒縮到 2 秒，延遲就少了十幾秒。另一個觀察是 contribution 那一行：TCP 的延遲是「不固定」的，網路一變差就忽大忽小；SRT 則讓你把它設成一個固定值，用固定的延遲換取可預測的穩定性。這兩件事分別是 38.3–38.9 節與 38.10–38.12 節的主題。

> [!warning] 常見誤解
> 「直播延遲高是因為頻寬不夠」：頻寬不足造成的是卡頓與畫質下降，延遲高的主因通常是協定設計（segment 長度、播放器 buffer）與編碼器設定。把頻寬加倍，6 秒 segment 的 HLS 仍然會有 20 秒左右的延遲。

## 38.3 RTMP：從 Flash 時代留下的推流標準

**RTMP**（Real-Time Messaging Protocol）原本是 Macromedia／Adobe 為 Flash Player 設計的協定，Adobe 在 2012 年公開了規格，但它從來不是 IETF 標準。Flash 早已退場，RTMP 卻一直是推流的「共同語言」：幾乎所有直播軟體、硬體編碼器與直播平台都支援它，OBS 的預設推流方式也是 RTMP。觀看端早就不用 RTMP 了，它現在只活在 contribution 那一段。

RTMP 跑在 TCP 上，預設 port 1935；加上 TLS 的版本叫 **RTMPS**，常見於 443 port，部分平台只接受 RTMPS。推流網址的形式是 `rtmp://主機/應用程式名稱/stream key`，例如 `rtmps://live.shengsheng.example:443/live/` 加上一串 stream key。**stream key** 是一個長字串，同時扮演「頻道名稱」與「密碼」：誰拿到它，誰就能推流到你的頻道，所以它和 API token 一樣要保密、外洩時要能立刻撤銷重發。

一條 RTMP 連線建立的過程如下：

```text
 OBS（client）                                            ingest（server）
   │── TCP 三向交握（第 10 章）──────────────────────────────────►│
   │── C0（版本 1 byte = 3）＋ C1（1536 bytes：時間＋隨機資料）──►│
   │◄─ S0 ＋ S1（1536 bytes）＋ S2（回聲 C1）─────────────────────│
   │── C2（回聲 S1）─────────────────────────────────────────────►│   RTMP handshake 完成
   │── connect（AMF0 指令：app="live"、tcUrl）───────────────────►│
   │◄─ Window Ack Size、Set Peer Bandwidth、_result ──────────────│
   │── Set Chunk Size 4096 ──────────────────────────────────────►│
   │── createStream ─────────────────────────────────────────────►│
   │◄─ _result（message stream id = 1）───────────────────────────│
   │── publish（stream key, "live"）─────────────────────────────►│   ingest 在這裡驗證 stream key
   │◄─ onStatus: NetStream.Publish.Start ─────────────────────────│
   │── @setDataFrame onMetaData（解析度、bitrate…）──────────────►│
   │══ audio（type 8）／video（type 9）message，切成 chunk ══════►│   持續數小時
```

由上往下看，先是 TCP 交握，然後是 RTMP 自己的 handshake：雙方各送一個版本 byte 與 1536 bytes 的隨機資料，再把對方的資料回聲回去。接著是用 **AMF0**（Action Message Format，Flash 時代的二進位序列化格式，類似精簡的 JSON）編碼的指令：`connect` 指定應用程式名稱，`createStream` 建立邏輯上的串流，`publish` 帶著 stream key 宣告「我要推流」，ingest 在這一步驗證 stream key。之後就是持續數小時的音訊與視訊 message。建立連線要好幾個 RTT，但只發生一次，影響不大。

RTMP 的資料單位是 **message**（例如一個視訊 frame），送上網路前會被切成 **chunk**。切 chunk 的目的是**多工**（multiplexing）：一個 keyframe 可能有幾百 KB，如果整個送完才能送音訊，聲音就會斷續，所以 RTMP 把大 message 切成小塊，讓音訊 chunk 可以插在視訊 chunk 之間。每個 chunk 前面有一個 chunk header：

```text
 Basic Header（1 byte，chunk stream id 2–63 時）
  0 1 2 3 4 5 6 7
 ┌───┬───────────┐
 │fmt│   csid    │   fmt：0＝完整 header、1／2＝省略部分欄位、3＝完全沿用上一塊
 └───┴───────────┘   csid：chunk stream id，區分不同的「頻道」（例如音訊、視訊）

 Message Header（fmt=0 時 11 bytes）
 ┌──────────────────┬──────────────────┬────────┬───────────────────────────────┐
 │ timestamp (3 B)  │ message len (3 B)│type (1)│ msg stream id (4 B, 小端序)   │
 └──────────────────┴──────────────────┴────────┴───────────────────────────────┘
   毫秒                 整則 message 的長度    8＝音訊、9＝視訊、18＝metadata、20＝AMF0 指令

 一則 4005 bytes 的視訊 message，chunk size 128：
 [fmt0 header 12 B][128 B] [fmt3 1 B][128 B] [fmt3 1 B][128 B] … 共 32 塊
```

這張圖從上往下讀。basic header 的前 2 bit 是 **fmt**，決定後面的 message header 有多長；fmt 0 是完整的 11 bytes，fmt 3 則完全沒有 message header，表示「和同一個 chunk stream 的上一塊相同」，所以一則大 message 只有第一塊付出完整 header 的成本。message header 裡的 timestamp 單位是毫秒，type 區分音訊、視訊、metadata 與指令；最奇怪的是 message stream id 用小端序（little-endian），其他欄位卻是大端序，這是 Flash 時代留下的歷史包袱，自己寫解析器時很容易踩到。chunk size 預設只有 128 bytes，大多數推流軟體一連上就用 Set Chunk Size 調大（例如 4096），減少 header 數量。

下面用 Python 把一個 4000 bytes 的 keyframe 包成 RTMP 視訊 message，並比較兩種 chunk size。程式同時示範傳統 FLV 視訊 tag 與 Enhanced RTMP 的差別，後者在下一小段說明。

```python
import struct


def chunk_message(csid, ts_ms, type_id, stream_id, body, chunk_size):
    """把一則 RTMP message 切成 chunk：第一塊帶 type 0 header，之後用 type 3 續傳。"""
    first = bytes([(0 << 6) | csid])                         # basic header：fmt=0、chunk stream id
    first += ts_ms.to_bytes(3, "big") + len(body).to_bytes(3, "big") + bytes([type_id])
    first += struct.pack("<I", stream_id)                    # message stream id 是 little-endian（歷史包袱）
    cont = bytes([(3 << 6) | csid])                          # fmt=3：沿用上一塊的所有欄位
    out = []
    for i in range(0, len(body), chunk_size):
        out.append((first if i == 0 else cont) + body[i:i + chunk_size])
    return out


def video_tag_header(codec):
    if codec == "h264":     # 傳統 FLV：高 4 bit 是 frame type（1=keyframe），低 4 bit 是 codec id（7=AVC）
        return bytes([0x17, 0x01]) + b"\x00\x00\x00"         # AVCPacketType=1（NALU）＋ composition time
    if codec == "av1":      # Enhanced RTMP：IsExHeader=1、frame type=1、packet type=1（coded frames）＋ FourCC
        return bytes([0x80 | (1 << 4) | 1]) + b"av01"
    raise ValueError(codec)


frame = bytes(4000)                                          # 假裝是 4000 bytes 的 keyframe
for codec in ("h264", "av1"):
    body = video_tag_header(codec) + frame
    print(f"{codec:>4} video tag 開頭：{body[:5].hex(' ')}  （{body[:5]!r}）")

for size in (128, 4096):
    chunks = chunk_message(csid=6, ts_ms=40, type_id=9, stream_id=1, body=video_tag_header("h264") + frame, chunk_size=size)
    overhead = sum(len(c) for c in chunks) - 4005
    print(f"chunk size {size:>4}：{len(chunks):>2} 塊，第一塊 header {chunks[0][:12].hex(' ')}，header 共 {overhead} bytes")
    assert chunks[0][0] == 0x06 and chunks[0][7] == 9 and all(c[0] == 0xC6 for c in chunks[1:])
```

```text
h264 video tag 開頭：17 01 00 00 00  （b'\x17\x01\x00\x00\x00'）
 av1 video tag 開頭：91 61 76 30 31  （b'\x91av01'）
chunk size  128：32 塊，第一塊 header 06 00 00 28 00 0f a5 09 01 00 00 00，header 共 43 bytes
chunk size 4096： 1 塊，第一塊 header 06 00 00 28 00 0f a5 09 01 00 00 00，header 共 12 bytes
```

第一段輸出是視訊 tag 的開頭。傳統 FLV 用 1 byte 表示「frame 類型＋codec」：`0x17` 的高 4 bit 是 1（keyframe）、低 4 bit 是 7（AVC，也就是 H.264）；codec id 只有 4 bit 且只定義了少數幾種，這就是 RTMP 長期無法推 HEVC、AV1、Opus 的原因。**Enhanced RTMP** 是業界為此做的擴充（版本見本節末的 2026 現況）：最高 bit 設為 1 表示延伸格式，後面接 4 個字元的 **FourCC**（用四個 ASCII 字元表示 codec 的慣例，例如 `av01`、`hvc1`），新版還加入 multitrack 與「請 client 重新連線」的指令。第二段輸出是 chunk 的成本：chunk size 128 時切成 32 塊、header 共 43 bytes，4096 時只要 1 塊。要注意 Enhanced RTMP 解決的是「codec 太舊」，沒有解決「TCP 遇到丟包就卡」。

那麼 RTMP 在丟包網路上到底多糟？第 12 章介紹過 TCP 吞吐量的經驗公式（Mathis 公式）：吞吐量上限約為 MSS／RTT × 1.22／√p，其中 p 是丟包率。把美咲飯店的數字代進去：MSS 1448 bytes、RTT 80 ms、p＝3%，得到 1448 × 8 ÷ 0.08 × 1.22 ÷ 0.173 ≈ 1.0 Mbps。這是 Reno 式擁塞控制的估算，CUBIC 或 BBR 的實際數字會不同（第 12 章），但量級足以說明問題：一條需要 4.5 Mbps 的推流，在 3% 丟包的路徑上，TCP 平均只給得出 1 Mbps 左右。更糟的是 TCP 的**隊頭阻塞**（head-of-line blocking，第 11 章）：一個封包遺失，後面已經到達的資料都要在接收端排隊等它重傳，ingest 收到的是一陣一陣的資料，而不是穩定的串流。

OBS 這一端看到的是：送出 buffer 越堆越多，最後只能丟掉還沒送出的 frame，這就是狀態列上「丟棄的 frame（網路）」的來源。RTMP 沒有「這份資料已經太舊、不用送了」的概念，TCP 會把晚了好幾秒的畫面照樣可靠地送到，還佔著頻寬讓後面的畫面也跟著晚到。

> [!note] 2026 現況
> 依 2026 年 10 月查證：Enhanced RTMP 由 Veovera 軟體組織維護，最新為 V2（版本字串 `v2-2026-01-31-r2`，Release 階段，Apache-2.0 授權）。V2 涵蓋 VP8、VP9、HEVC、AV1、VVC 視訊與 AC-3、E-AC-3、Opus、FLAC 音訊，以及 multitrack、多聲道音訊、`NetConnection.Connect.ReconnectRequest` 與 nanosecond 等級的 timestamp 位移。依知識（未經本次查證），OBS、FFmpeg 與主要平台已支援 E-RTMP v1 的 HEVC／AV1；V2 各項功能的實作程度依軟體版本而定，使用前要確認推流端與 ingest 端都支援。

## 38.4 SRT 的基本想法：UDP 上有期限的重傳

RTMP 的問題可以歸納成一句話：TCP 的可靠性沒有期限。直播需要的是另一種語意：「盡量把每個封包送到，但如果在某個時間點之前送不到，就放棄它，繼續往下播」。**SRT**（Secure Reliable Transport）就是為這個語意設計的協定。它由 Haivision 開發，2017 年以開源函式庫 libsrt 釋出，並由 SRT Alliance 推動成為業界常用的 contribution 協定；它建立在 UDT（一個早期在 UDP 上做可靠傳輸的研究協定）之上，加入了直播需要的延遲控制與加密。

SRT 的設計可以拆成三個零件，本章接下來三節依序展開：

1. **ARQ**（Automatic Repeat reQuest，自動重傳請求）：收方發現缺了哪個序號，就主動用 **NAK**（negative acknowledgment，「我沒收到這幾個」）告訴送方重傳。這和第 11 章 TCP 的 selective repeat 是同一個想法，差別在 SRT 以 NAK 為主，不等計時器逾時。
2. **TSBPD**（Timestamp-Based Packet Delivery，依 timestamp 交付）：每個封包帶著送出時的 timestamp，收方把它固定延遲一段時間（**latency**）後才交給解碼器，讓輸出的節奏和輸入完全一樣，網路的抖動被吸收在這段延遲裡。
3. **too-late drop**：如果一個封包到了該交付的時間還沒到，收方就放棄它，繼續交付後面的封包，不讓一個遺失卡住整條串流。

三個零件合起來就是「有期限的 ARQ」：期限內盡力重傳，期限一到寧可丟掉一個封包，也要讓串流準時前進。TCP 沒有期限，不丟資料但延遲沒有上限；純 UDP 沒有重傳，丟一個算一個。SRT 站在兩者中間，並讓你用 latency 這個參數決定站在哪裡。

SRT 封包的 header 固定 16 bytes，分成資料封包與控制封包兩種，用第一個 bit 區分：

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
```

先看資料封包。第一列是 31 bit 的**序號**，每個封包加一，收方靠它發現跳號。第二列的 **PP** 表示這個封包在一則訊息中的位置（live 模式每個封包都是獨立的一則，PP＝11），**O** 是是否要求依序交付，**KK** 表示加密用的是哪一把金鑰（00 沒加密、01 偶數金鑰、10 奇數金鑰，38.8 節），**R** 標記「這是重傳的封包」，後面是 26 bit 的 message number。第三列 **Timestamp** 是封包相對於連線開始的時間，單位是微秒，TSBPD 就靠它決定交付時間。第四列 **Destination Socket ID** 是收方在 handshake 時分配的連線編號，讓一個 UDP port 可以同時服務很多條 SRT 連線：ingest 不靠來源位址區分推流，而是靠這個 ID。

控制封包的第一列換成 15 bit 的 **Control Type**，常見的類型列在下表。控制封包同樣帶 timestamp 與 socket ID，後面的 Control Information Field 依類型而定。

| Control Type | 名稱 | 用途 |
|---|---|---|
| 0x0000 | HANDSHAKE | 建立連線、協商 latency、交換加密金鑰與 stream ID（38.7 節） |
| 0x0001 | KEEPALIVE | 沒有資料時約每秒送一個，維持 NAT 與防火牆的 UDP 狀態 |
| 0x0002 | ACK | 收方定期回報「到這個序號為止都收到了」，附上 RTT、可用 buffer 等統計 |
| 0x0003 | NAK | 收方回報遺失的序號清單，請送方重傳 |
| 0x0005 | SHUTDOWN | 結束連線 |
| 0x0006 | ACKACK | 送方確認收到 ACK，收方由此量出 RTT |
| 0x0007 | DROPREQ | 送方告訴收方「這些封包我已經丟掉了，不要再要」 |

payload 預設 1316 bytes，是因為 contribution 傳統上傳的是 MPEG-TS（把音訊與視訊交錯放在 188 bytes 小封包裡的 container，第 34 章），1316 剛好是 7 個 TS 封包；整個 IP 封包 1360 bytes，即使經過 MTU 1420 的 WireGuard 隧道也不必分片（第 8 章）。下面這段程式把 SRT 資料封包與 NAK 控制封包組出來再解回去：

```python
import struct

DATA_PP_SOLO = 0b11          # PP=11：這個封包自己就是完整的一則訊息
CTRL_NAK = 0x0003


def pack_data(seq, msgno, ts_us, dst_id, payload, retrans=False, kk=0):
    # word0：F=0（資料封包）＋ 31-bit 序號
    w0 = seq & 0x7FFF_FFFF
    # word1：PP(2) O(1) KK(2) R(1) ＋ 26-bit message number
    w1 = (DATA_PP_SOLO << 30) | (0 << 29) | (kk << 27) | (int(retrans) << 26) | (msgno & 0x03FF_FFFF)
    return struct.pack("!IIII", w0, w1, ts_us, dst_id) + payload


def encode_loss_list(lost):
    """連續遺失的序號壓成一個區間：起點的最高位元設 1，後面接終點。"""
    out, i = [], 0
    lost = sorted(lost)
    while i < len(lost):
        j = i
        while j + 1 < len(lost) and lost[j + 1] == lost[j] + 1:
            j += 1
        if j == i:
            out.append(lost[i])
        else:
            out += [lost[i] | 0x8000_0000, lost[j]]
        i = j + 1
    return out


def pack_nak(lost, ts_us, dst_id):
    w0 = 0x8000_0000 | (CTRL_NAK << 16)          # F=1（控制封包）、type=NAK、subtype=0
    cif = encode_loss_list(lost)
    return struct.pack(f"!IIII{len(cif)}I", w0, 0, ts_us, dst_id, *cif)


def parse(pkt):
    w0, w1, ts, dst = struct.unpack("!IIII", pkt[:16])
    if w0 >> 31 == 0:
        return {"kind": "DATA", "seq": w0 & 0x7FFF_FFFF, "PP": w1 >> 30, "KK": (w1 >> 27) & 3,
                "R": (w1 >> 26) & 1, "msgno": w1 & 0x03FF_FFFF, "ts_us": ts, "dst": dst,
                "payload": len(pkt) - 16}
    ctype = (w0 >> 16) & 0x7FFF
    words = struct.unpack(f"!{(len(pkt) - 16) // 4}I", pkt[16:])
    lost, i = [], 0
    while i < len(words):
        if words[i] >> 31:                      # 區間起點
            lost += range(words[i] & 0x7FFF_FFFF, words[i + 1] + 1)
            i += 2
        else:
            lost.append(words[i])
            i += 1
    return {"kind": f"CTRL type=0x{ctype:04x}", "lost": lost, "ts_us": ts, "dst": dst}


TS_PAYLOAD = bytes(1316)                       # 7 個 188-byte 的 MPEG-TS 封包
d = pack_data(seq=1_000_007, msgno=42, ts_us=1_234_567, dst_id=0x1E2F3A4B, payload=TS_PAYLOAD, retrans=True)
print("data header :", d[:16].hex(" "))
print("data parsed :", {k: (f"0x{v:08x}" if k == "dst" else v) for k, v in parse(d).items()})
print("on the wire :", 20 + 8 + len(d), "bytes = IPv4 20 + UDP 8 + SRT 16 + payload 1316")

n = pack_nak([1_000_010, 1_000_011, 1_000_012, 1_000_013, 1_000_020], ts_us=1_260_000, dst_id=0x0BADCAFE)
print("NAK bytes   :", n.hex(" "))
p = parse(n)
print("NAK parsed  :", p["kind"], "lost =", p["lost"])
assert parse(d)["R"] == 1 and parse(d)["seq"] == 1_000_007 and len(d) == 1332
assert p["lost"] == [1_000_010, 1_000_011, 1_000_012, 1_000_013, 1_000_020] and len(n) == 16 + 12
```

```text
data header : 00 0f 42 47 c4 00 00 2a 00 12 d6 87 1e 2f 3a 4b
data parsed : {'kind': 'DATA', 'seq': 1000007, 'PP': 3, 'KK': 0, 'R': 1, 'msgno': 42, 'ts_us': 1234567, 'dst': '0x1e2f3a4b', 'payload': 1316}
on the wire : 1360 bytes = IPv4 20 + UDP 8 + SRT 16 + payload 1316
NAK bytes   : 80 03 00 00 00 00 00 00 00 13 39 e0 0b ad ca fe 80 0f 42 4a 00 0f 42 4d 00 0f 42 54
NAK parsed  : CTRL type=0x0003 lost = [1000010, 1000011, 1000012, 1000013, 1000020]
```

第一行是資料封包 header。`00 0f 42 47` 是序號 1,000,007，最高 bit 為 0 表示資料封包；`c4` 的二進位是 `11000100`，依序是 PP＝11、O＝0、KK＝00、R＝1，代表「完整訊息、未加密、這是重傳」，`2a` 是 message number 42。NAK 開頭的 `80 03` 表示 F＝1、type＝3；遺失清單只用 3 個欄位就表達了 5 個序號：`80 0f 42 4a` 的最高 bit 是 1，表示區間起點 1,000,010，下一個欄位是區間終點 1,000,013，最後是單獨的 1,000,020。無線網路常連續遺失，區間壓縮讓一個 NAK 能回報幾十個遺失。

## 38.5 ACK、NAK 與重傳：收方主導的修補

TCP 的可靠性主要由送方驅動：送方等 ACK，等不到就逾時重傳，或看到重複 ACK 才快速重傳（第 11 章）。SRT 的 live 模式則把主導權交給收方：收方一看到序號跳號，立刻送出 NAK，送方收到就重傳，整個修補只需要大約一個 RTT。下圖是實際的時間軸，假設 RTT 40 ms、每 5 ms 送一個封包：

```text
 送方（OBS）                                              收方（ingest）
 t=15 │── #3 ──────────╳（遺失）                              │
 t=20 │── #4 ────────────────────────────────────────────────►│ t=40  發現 #3 沒到（跳號）
      │                                                       │       立刻送 NAK [3]
 t=60 │◄────────────────────────────────────────── NAK [3] ───│
 t=60 │── #3（R=1，重傳）────────────────────────────────────►│ t=80  收到 #3，放進 buffer
      │                                                       │
      │                                                       │ t=155 #3 的交付時間到了：
      │                                                       │       15（timestamp）＋20（單向延遲）
      │                                                       │       ＋120（latency）→ 交給解碼器
```

從上往下讀。#3 在 t＝15 ms 送出後遺失；#4 在 t＝40 ms 到達收方，收方看到序號從 2 跳到 4，立刻送出 NAK [3]。NAK 在 t＝60 ms 到達送方，送方從自己的送出 buffer 裡找出 #3，設上 R 旗標重送，t＝80 ms 到達收方。此時離 #3 的交付時間（t＝155 ms）還有 75 ms，所以這次遺失對觀眾完全透明。從遺失到修補完成花了 65 ms，大約是「一個 RTT 加上發現跳號的時間」，這就是為什麼 latency 一定要比 RTT 大好幾倍：期限內要容得下至少一次、最好兩三次的重傳。

只靠「看到跳號就 NAK」不夠，因為 NAK 本身也可能遺失，重傳的封包也可能再遺失。所以 SRT 的收方還會**週期性地**重新送出 NAK（periodic NAK report），把遺失清單中還沒補上的序號再要一次；間隔和 RTT 有關，libsrt 的實作大約是半個 RTT 加上變異量，最少 20 ms。送方為了避免重傳過頭，也會略過剛剛才重傳過的封包。這些細節在不同版本的 libsrt 有所調整，觀念上記住「立即 NAK＋週期 NAK」兩層保險即可。

ACK 在 SRT 裡扮演的角色比較次要，但它帶來兩個重要資訊。第一，收方大約每 10 ms 送一個 ACK，告訴送方「到這個序號為止都收到了」，送方就能把這些封包從送出 buffer 移除。第二，送方收到 ACK 後回一個 **ACKACK**，收方用「送出 ACK 到收到 ACKACK」的時間量出 RTT，這個 RTT 又用來決定週期 NAK 的間隔，也會出現在統計資料裡（`msRTT`），是除錯時判斷 latency 夠不夠的第一個數字。

重傳需要頻寬。libsrt 的 `SRTO_OHEADBW` 預設 25%，允許重傳在輸入 bitrate 之外再多用 25%；所以 4.5 Mbps 的推流，上傳頻寬至少要 4.5 × 1.25 ≈ 5.6 Mbps。如果推流已經吃滿上傳頻寬，重傳沒有空間，遺失的封包只能等著被 too-late drop。

> [!warning] 常見誤解
> 「SRT 有重傳，所以不會掉畫面」：SRT 只在 latency 期限內重傳。期限太短、丟包太多或頻寬不足，封包照樣會被 too-late drop，畫面會出現破格（macroblock）或短暫凍結。SRT 給你的是「可以預測的延遲」與「在期限內盡力修補」，不是保證送達。

## 38.6 latency 與 TSBPD：用固定延遲換取穩定

理解 SRT 最關鍵的一個參數是 **latency**。它不是「網路延遲」，而是收方刻意加上的**交付延遲**：收方收到 timestamp 為 T 的封包後，要等到「T＋基準時間差＋latency」才把它交給上層。這段時間做兩件事：吸收網路抖動，以及留時間給重傳。

```text
 送方送出時間（timestamp）    #1    #2    #3    #4    #5      等距，每 5 ms 一個
                              │     │     │     │     │
 收方實際收到時間               #1     #2           #4  #3' #5    有抖動；#3 遺失，重傳的 #3' 比 #4 還晚到

 收方交付時間（TSBPD）                                            #1    #2    #3    #4    #5    和送出時一樣等距
                              ├──────────── latency ──────────────┤
                              #1 送出                             #1 交付
```

由上往下看三條時間軸。送方等距送出；收方實際收到的時間因抖動忽快忽慢，#3 靠重傳才到，甚至比 #4 還晚；TSBPD 則把每個封包延遲到「送出時間＋固定差距」才交付，所以交付節奏和送出時完全一樣，解碼器看不到抖動，也看不到 #3 曾經遲到。

如果封包到了交付時間還沒到，就是 **too-late drop**（`SRTO_TLPKTDROP`，live 模式預設開啟）：收方跳過它，照時間交付後面的封包，不再要求重傳；它稍後才到也直接丟棄。送方同樣會丟掉老到不可能及時交付的封包，不浪費頻寬。這是 SRT 與 TCP 最本質的差別：遺失只影響那一個封包，而不是整條串流。

latency 要設多少？SRT 社群與廠商文件常見的經驗法則是：latency 至少是 RTT 的 3 到 4 倍，丟包率越高倍數要越大，而且不要低於預設的 120 ms。直覺是「每次重傳大約要花一個 RTT，期限內要容得下幾次重傳」。美咲的飯店路徑 RTT 80 ms，4 倍是 320 ms，Joe 為了應付 Wi-Fi 的叢發丟包選了 500 ms；攝影棚到 ingest 的 RTT 只有 20 ms，維持 120 ms 就很充裕。章末的動手做會用模擬實際驗證這條經驗法則。

latency 是雙方**協商**的：handshake 時，送方提出自己希望的值（`SRTO_PEERLATENCY`），收方也有自己的值（`SRTO_RCVLATENCY`），這個方向實際使用的是兩者中**較大**的那個。`SRTO_LATENCY` 則是一次設定兩者的捷徑，預設 120 ms。這個「取較大值」的規則有一個實務意義：ingest 可以設定一個下限，避免推流端設得太低；反過來說，推流端把 latency 設成 2000 ms，ingest 也只能接受。

| 參數（libsrt） | 預設值 | 意義 | 實務提醒 |
|---|---|---|---|
| `SRTO_LATENCY` | 120 ms | 同時設定收與送兩個方向的 latency | 單位是**毫秒** |
| `SRTO_RCVLATENCY`／`SRTO_PEERLATENCY` | live 模式 120 ms／0 | 分別設定自己收的 latency 與希望對方用的 latency | 實際值取雙方較大者 |
| `SRTO_TLPKTDROP` | live 模式開啟 | 過期封包直接丟棄 | 關掉它等於讓串流卡住等遺失的封包 |
| `SRTO_OHEADBW` | 25% | 重傳可用的額外頻寬比例 | 範圍 5–100 |
| `SRTO_PAYLOADSIZE` | live 模式 1316 bytes | 每個封包的 payload | 7 × 188 TS 封包 |
| `SRTO_PASSPHRASE` | 空（不加密） | 加密用的密語 | 長度 10–80 字元 |
| `SRTO_STREAMID` | 空 | 連線時送給 listener 的字串 | 最長 512 字元 |
| `SRTO_CONNTIMEO` | 3000 ms | 連線逾時 | rendezvous 模式為 10 倍 |

這張表裡最容易出事的是單位。libsrt 的 `SRTO_LATENCY` 和 `srt-live-transmit` 工具的 `latency` URL 參數都是**毫秒**；但 ffmpeg（以及建立在 ffmpeg 上的 OBS 的 SRT 輸出）的 srt URL 參數 `latency` 單位是**微秒**。所以在 ffmpeg 裡要 500 ms，必須寫 `latency=500000`。寫成 `latency=500` 會變成 0.5 ms，ffmpeg 換算成毫秒後等於沒設；因為協商取較大值，實際 latency 會變成 ingest 那一端的設定（例如預設的 120 ms），而不是你以為的 500 ms。這個陷阱幾乎每個直播團隊都踩過。

latency 越大，代價是延遲本身與 buffer 記憶體（4.5 Mbps × 0.5 s ≈ 280 KB，兩端各一份，對伺服器不算什麼）。對於後面接 LL-HLS、整體延遲本來就有好幾秒的直播，contribution 多 0.4 秒換來穩定的畫面，幾乎永遠划算。

## 38.7 連線模式與 handshake：caller、listener、rendezvous

SRT 連線有三種建立方式，對應到 NAT 與防火牆的不同情況（第 7 章）：

- **listener**：在 UDP port 上等待連線，相當於 TCP 的 server。聲聲 Live 的 ingest 就是 listener，在 203.0.113.25 的 UDP 9000 等待推流，必須有公網位址與開好的 security group。
- **caller**：主動發起連線，相當於 TCP 的 client。OBS 與攝影棚的編碼器都是 caller，它的第一個封包會在 NAT 上建立對應，所以躲在飯店路由器後面也沒問題。
- **rendezvous**：雙方同時向對方發起連線，用在兩端都在 NAT 後的情況，原理和第 7 章的 UDP 打洞相同，對 symmetric NAT 不一定成功。

方向與角色是兩件事：caller 可以推流，也可以拉流（例如製作中心從 ingest 拉一路訊號回去），SRT 因此能適應「誰連得到誰」的網路現實。

caller 與 listener 之間的 handshake 分成兩個階段，共兩個 RTT：

```text
 caller（OBS，飯店 NAT 後）                               listener（ingest 203.0.113.25:9000）
   │── HANDSHAKE induction ────────────────────────────────────────────►│
   │     version 4、type=INDUCTION、cookie=0、caller 的 socket ID       │  listener 不建立任何狀態，
   │                                                                    │  只依來源位址與時間算出 cookie
   │◄──────────────────────────────────────── HANDSHAKE induction ──────│
   │     version 5、SRT magic 0x4A17、cookie=0x6C3B…、支援的加密        │
   │                                                                    │
   │── HANDSHAKE conclusion ───────────────────────────────────────────►│
   │     cookie=0x6C3B…（回聲）                                         │  cookie 正確才建立連線狀態
   │     HSREQ：SRT 版本、TSBPD、latency 500 ms                         │  檢查 stream ID 與權限，
   │     KMREQ：用 passphrase 包起來的加密金鑰                          │  用 passphrase 解開金鑰
   │     SID：#!::r=live/talk-1017,m=publish                            │
   │◄─────────────────────────────────────── HANDSHAKE conclusion ──────│
   │     HSRSP：協商後的 latency = max(500, 120) = 500 ms               │
   │     KMRSP：金鑰確認、listener 的 socket ID                         │
   │══ 資料封包（KK=01，AES 加密）═════════════════════════════════════►│
```

第一個來回是 **induction**：caller 送出一個幾乎空白的 handshake，listener 回應一個 **cookie**，這個 cookie 由 listener 依 caller 的位址與時間算出，listener 本身不保存任何狀態。第二個來回是 **conclusion**：caller 必須帶著正確的 cookie 回來，listener 才會建立連線狀態。這和第 10 章 TCP 的 SYN cookie 是同一個防禦思路：偽造來源位址的攻擊者收不到 cookie，也就無法讓 listener 耗盡記憶體。conclusion 裡帶著 SRT 的擴充區塊：**HSREQ** 協商版本、TSBPD 與 latency，**KMREQ** 帶著加密金鑰（38.8 節），**SID** 是 stream ID。listener 回覆的 HSRSP 裡就是協商後的 latency。兩個 RTT 之後，資料就開始流動。

rendezvous 模式的 handshake 不同：雙方都先送 WAVEAHAND 類型的 handshake，等到彼此都收到對方的封包（代表 NAT 上的洞打通了），再交換 conclusion 與 agreement。因為要等兩邊的封包都穿過 NAT，連線逾時是 caller 模式的 10 倍。

這些模式對網路設定有直接的影響。listener 的 security group 必須允許 UDP 9000 進來；SRT 不能放在只懂 HTTP 的 L7 load balancer 後面，第 25 章提過，前面只能用 L4 LB，而且同一條推流的封包必須一直落在同一台 ingest 上（五元組 hash，或每台 ingest 一個獨立 IP）。沒有資料時雙方約每秒互送 keepalive，足以維持絕大多數 NAT 的 UDP 對應（第 7 章）。

## 38.8 加密與 stream ID：誰能推、推到哪裡

RTMP 的 stream key 以明文出現在 TCP 連線裡（除非用 RTMPS），任何能看到流量的人都能偷走它。SRT 把加密內建在協定裡：雙方設定相同的 **passphrase**（10–80 個字元的密語），資料封包的 payload 就會以 AES 加密。

金鑰的管理分兩層：

```text
 passphrase（雙方事先共享）                    隨機產生（每條連線、定期輪替）
        │                                              │
        ▼  PBKDF2（加上 salt）                         ▼
 ┌────────────┐   用來包裝（wrap）  ┌────────────────────────────────────┐
 │    KEK     │ ──────────────────► │    SEK（Stream Encrypting Key）    │
 │金鑰加密金鑰│                     │偶數金鑰（KK=01）／奇數金鑰（KK=10）│──► AES 加密每個封包的 payload
 └────────────┘                     └────────────────────────────────────┘    （header 不加密）
                                                       │
                                                       ▼
                                   包裝後的 SEK 放在 handshake 的 KMREQ 裡送給對方
```

由上往下讀：送方隨機產生真正用來加密資料的 **SEK**（Stream Encrypting Key）；passphrase 則經過 PBKDF2（一種刻意變慢、讓暴力猜測變貴的金鑰衍生函式，第 26 章）加上 salt，衍生出 **KEK**（Key Encrypting Key）。送方用 KEK 把 SEK 包起來，放在 handshake 的 KMREQ 裡送給收方；收方用同一個 passphrase 衍生出同一個 KEK，才能解開 SEK。這樣 passphrase 本身從不在網路上出現。金鑰長度由 `SRTO_PBKEYLEN` 決定，可以是 16、24、32 bytes（AES-128、192、256），雙方都沒設定時是 AES-128。長時間的串流會定期換新的 SEK：header 的 KK 欄位標記目前用的是偶數還是奇數金鑰，新金鑰會事先送達，切換時不中斷。

有三件事要知道。第一，只有 payload 加密，header 是明文，中間的人仍看得到流量的節奏與大小。第二，傳統模式 AES-CTR 只提供機密性、不保護完整性，較新的 libsrt 加入了能偵測竄改的 AES-GCM（見 2026 現況）。第三，passphrase 不對時 libsrt 預設拒絕連線（`SRTO_ENFORCEDENCRYPTION`），log 會顯示類似「bad secret」的原因；關掉這個選項時，症狀會變成「連上了但沒畫面」。

**stream ID** 解決的是另一個問題：一個 listener port 上有很多條推流，ingest 怎麼知道這條連線要推到哪個頻道、推流者是誰？SRT 讓 caller 在 handshake 時送出最多 512 個字元的字串，listener 可以在接受連線之前讀它、決定要不要接受、要用哪個 passphrase。SRT 的存取控制建議格式是以 `#!::` 開頭、逗號分隔的 key=value，例如 `#!::r=live/talk-1017,m=publish,u=misaki`：`r` 是資源名稱，`m` 是模式（`publish` 推流、`request` 拉流），`u` 是使用者。格式只是建議，ingest 軟體可以自行定義，但統一格式能讓不同的編碼器與伺服器互通。

Rita 為 SRT ingest 定了三條規則。第一，每場講座用 `secrets.token_urlsafe` 產生一組新的 passphrase，經 secrets manager 發給講者（第 17 章），講座結束就失效。第二，stream ID 在 handshake 裡是明文，只用來選頻道，不當作秘密；授權靠 passphrase，或在 stream ID 裡放一個短效、可撤銷的 token 由 ingest 驗證。第三，監控被拒絕的 handshake 數量，突然暴增可能是有人在掃描或猜測。

## 38.9 RTMP 與 SRT：在丟包網路上的對照

把前面幾節整理起來，就能回答小晴最初的問題：同樣是「可靠」，RTMP 與 SRT 的差異在於「可靠」的定義不同。

| 面向 | RTMP（over TCP） | SRT（over UDP） |
|---|---|---|
| 可靠性語意 | 全部送達、依序交付，沒有期限 | latency 期限內盡力重傳，過期就丟 |
| 遇到丟包 | 整條資料流等待重傳（隊頭阻塞），擁塞控制降速 | 只有遺失的那個封包要補，其他照常交付；live 模式不因丟包降速 |
| 延遲 | 平常低，網路變差時不斷累積、沒有上限 | 固定為 latency 設定值（例如 120–2000 ms） |
| 抖動處理 | 交給應用程式的 buffer | TSBPD 依 timestamp 還原節奏 |
| 加密 | 需另用 RTMPS（TLS） | 內建 AES，passphrase 設定 |
| codec | 傳統只有 H.264／AAC 等；Enhanced RTMP 擴充 HEVC、AV1、Opus | 不管 codec，payload 通常是 MPEG-TS |
| 穿越網路 | TCP 1935 或 443，幾乎到處都能通 | UDP，企業網路或部分公共 Wi-Fi 可能封鎖 |
| 生態系 | 幾乎所有軟體與平台都支援 | 專業編碼器、OBS、ffmpeg、多數雲端媒體服務支援 |

表格的前三列是改版的核心理由，後兩列是 SRT 的代價：RTMPS 跑在 TCP 443 上幾乎穿得過任何防火牆，SRT 的 UDP 卻可能被企業或飯店網路擋掉，所以 Joe 讓 ingest 同時接受 SRT 與 RTMPS，講者優先用 SRT、連不上時退回 RTMPS。另外，SRT 的 live 模式不做 TCP 式的擁塞控制，上傳頻寬不夠時它不會自動降速，而是大量丟包，要靠編碼器降低 bitrate。

> [!note] 2026 現況
> 依 2026 年 10 月查證：SRT 在 IETF 只有一份 individual draft（`draft-sharabayko-srt-01`，2021 年），目前已過期並封存，**沒有**成為 RFC，規格的實質依據是 libsrt 的開源實作與文件。本章引用的 socket 選項預設值依 libsrt 的 API 文件。依知識（未經本次查證）：libsrt 1.5 系列加入 AES-GCM 加密模式（`SRTO_CRYPTOMODE`）與 connection bonding（socket group，可同時走兩條線路做備援），各家編碼器與 ingest 的支援程度不同，使用前要確認雙方版本。

## 38.10 HLS：把直播切成一個個檔案

講完 contribution，換到 distribution。要把一路直播送給 1,800 人（熱門講座可能上萬人），最省錢、最穩定的方法是借用已經遍布全世界的 HTTP 基礎設施：CDN。**HLS**（HTTP Live Streaming）是 Apple 在 2009 年提出的做法，2017 年以 RFC 8216（Informational）發表。它的想法很簡單：把直播切成一段一段幾秒長的小檔案（**segment**），再用一個文字檔（**playlist**，副檔名 `.m3u8`）列出目前有哪些 segment；播放器反覆下載 playlist，看到新的 segment 就下載來播。對 CDN 來說，這些都只是普通的 HTTP GET，可以用第 21、25 章的快取機制處理，一個 segment 被 edge 快取後，上千個觀眾的請求都不必回源。

HLS 有兩層 playlist。第一層是 **multivariant playlist**（規格的新版本用這個名稱），列出 ABR 階梯裡的所有版本，播放器依頻寬選一個：

```text
#EXTM3U
#EXT-X-INDEPENDENT-SEGMENTS
#EXT-X-STREAM-INF:BANDWIDTH=4800000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",FRAME-RATE=30
1080p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2700000,RESOLUTION=1280x720,CODECS="avc1.64001f,mp4a.40.2",FRAME-RATE=30
720p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1300000,RESOLUTION=854x480,CODECS="avc1.4d401e,mp4a.40.2",FRAME-RATE=30
480p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=850000,RESOLUTION=640x360,CODECS="avc1.4d401e,mp4a.40.2",FRAME-RATE=30
360p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=160000,CODECS="mp4a.40.2"
audio/index.m3u8
```

每個 `#EXT-X-STREAM-INF` 描述下一行那個版本：`BANDWIDTH` 是峰值 bitrate（bits/s，含音訊與 container 開銷，所以比視訊 bitrate 高一些），`RESOLUTION` 與 `FRAME-RATE` 讓播放器排除不適合螢幕的版本，`CODECS` 用 RFC 6381 的字串描述 codec（`avc1.640028` 是 H.264 High profile level 4.0，`mp4a.40.2` 是 AAC-LC），讓播放器在下載前就知道自己能不能解碼。最後一個只有音訊的版本，是給網路極差的觀眾「至少聽得到」的退路。

第二層是每個版本自己的 **media playlist**，列出實際的 segment。下面是九月講座 720p 版本在某一刻的樣子：

```text
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6                          ← 每個 segment 最長 6 秒
#EXT-X-MEDIA-SEQUENCE:301                        ← 清單中第一個 segment 的序號
#EXT-X-PROGRAM-DATE-TIME:2026-09-19T20:00:06.000+08:00   ← 第一個 segment 的真實時間
#EXTINF:6.000,
seg301.ts
#EXTINF:6.000,
seg302.ts
#EXTINF:6.000,
seg303.ts
#EXTINF:6.000,
seg304.ts
#EXTINF:6.000,
seg305.ts                                        ← 直播邊緣（live edge）
（沒有 #EXT-X-ENDLIST：直播還在進行，清單會繼續更新）
```

逐行看。`#EXT-X-TARGETDURATION` 是 segment 長度的上限（每個 `#EXTINF` 四捨五入後不能超過它），播放器用它決定多久重新載入一次清單。`#EXT-X-MEDIA-SEQUENCE` 是清單中第一個 segment 的序號：直播的清單是一個**滑動視窗**，舊 segment 從上面移除、新的從下面加入，序號跟著增加。`#EXT-X-PROGRAM-DATE-TIME` 把第一個 segment 對應到真實時間，量延遲與對齊字幕都靠它。每個 `#EXTINF` 的下一行是 segment 的 URI。沒有 `#EXT-X-ENDLIST` 代表直播還在進行，結束時封裝器才會加上它。

```text
 現場時間 → 20:00:06     20:00:12     20:00:18     20:00:24     20:00:30     20:00:36
                ├── seg301 ──┼── seg302 ──┼── seg303 ──┼── seg304 ──┼── seg305 ──┤
                                          ▲                                      ▲
                                          │                                      │
                                  起播點：seg303 的開頭              live edge（seg305 結尾）
                                  離 live edge 3 × 6 = 18 秒

 封裝器約 2 秒後（20:00:38）發布 seg305，播放器此時下載 playlist
 → 播放器在 20:00:38 播出 20:00:18 的畫面：延遲 20 秒
 → 之後每 6 秒重新下載一次 playlist；若清單沒變，等半個 target duration（3 秒）再試
```

這張時間軸說明了 HLS 延遲的主要來源。封裝器要等一個 segment 完整結束才能把它寫進清單，所以 live edge 本身就比現場晚了編碼、轉碼與發布的時間（圖中約 2 秒），而且越接近下一個 segment 完成，live edge 落後得越多。播放器拿到清單後，規範要求不要從最後一個 segment 開始播，而是至少離結尾三個 target duration，這樣即使下一個 segment 晚了一點、或下載慢了一點，buffer 裡還有十幾秒可以撐住。三個 target duration 的 buffer 就是 HLS 穩定的來源，也正是延遲的來源：6 秒的 segment 光這一項就是 18 秒，加上前面的 2 秒，觀眾看到的是 20 秒前的畫面；若播放器剛好在下一個 segment 快完成時加入，還會再多幾秒。故事裡觀眾晚了二十多秒，就是這樣算出來的。

segment 不能任意切短。第一，每個 segment 必須從 keyframe 開始，所以 segment 長度必須是 GOP 的整數倍（第 34 章）；GOP 2 秒就切 2、4、6 秒。第二，segment 越短，請求數越多，CDN 與 origin 的負擔越大，太短的檔案也用不滿頻寬。業界常見值是 6 秒，追求較低延遲時用 2 秒。

快取設定是 HLS 部署最常出錯的地方。segment 的名稱每次都不同、內容永不改變，可以快取很久；playlist 則每隔幾秒就更新，快取時間必須遠小於 target duration：

| 物件 | 範例 | 建議的 Cache-Control | 原因 |
|---|---|---|---|
| multivariant playlist | `index.m3u8` | `max-age=60` 左右（直播中很少變） | 只列版本，不列 segment |
| media playlist | `720p/index.m3u8` | `max-age=1` 或更短，不超過 target duration 的一半 | 太久的話觀眾會看到舊清單、延遲變大甚至卡住 |
| segment | `720p/seg301.ts` | `max-age=86400` 以上，可設 `immutable` | 名稱唯一、內容不變 |
| 錯誤回應 | 404、503 | 不快取，或只快取 1–2 秒 | 避免把「還沒產生」的 segment 快取成 404 |

最後一列是常見的坑：segment 剛要產生時就被請求，origin 回 404，CDN 若把它快取 60 秒，這一分鐘內所有觀眾都拿不到那個 segment。

## 38.11 DASH 與 CMAF：另一種清單、共用的片段

**MPEG-DASH**（Dynamic Adaptive Streaming over HTTP，ISO/IEC 23009-1）是 MPEG 制定的國際標準，想法和 HLS 一樣：把媒體切成 segment，用一份清單描述它們。差別在清單的格式：DASH 的清單叫 **MPD**（Media Presentation Description），是一份 XML。

```text
 MPD（type="dynamic" 表示直播；availabilityStartTime、minimumUpdatePeriod、suggestedPresentationDelay）
  └─ Period（一段內容，例如正片；插廣告時可以有多個 Period）
      ├─ AdaptationSet  contentType="video"（可以互相切換的一組版本）
      │    ├─ SegmentTemplate  media="video-$RepresentationID$-$Number$.m4s"  duration=2s  startNumber=1
      │    ├─ Representation  id="1080p"  bandwidth=4800000  width=1920  height=1080
      │    ├─ Representation  id="720p"   bandwidth=2700000  width=1280  height=720
      │    └─ Representation  id="480p"   bandwidth=1300000  width=854   height=480
      └─ AdaptationSet  contentType="audio"  lang="ja"
           └─ Representation  id="aac"  bandwidth=128000
```

由外往內讀：**Period** 是時間上的一段，**AdaptationSet** 是一組可以互相切換的版本，**Representation** 是其中一個具體版本，相當於 HLS 的一個 media playlist。最大的不同在 **SegmentTemplate**：DASH 通常不逐一列出 segment，而是給網址樣板，播放器用「現在時間 − availabilityStartTime」自己算出最新的 segment 編號代入 `$Number$`。所以 DASH 的直播清單幾乎不必更新，但非常依賴時鐘同步，時鐘差幾秒，播放器就會去要還不存在的 segment。

HLS 與 DASH 長期並存，過去這代表同一份內容要封裝兩次（HLS 用 MPEG-TS，DASH 用 fMP4），CDN 也要快取兩份。**CMAF**（Common Media Application Format，ISO/IEC 23000-19）解決了這個浪費：它規定一種共用的 segment 格式，基於 **fMP4**（fragmented MP4，把 MP4 切成「一個初始化段＋許多 moof／mdat 片段」的格式），讓同一組 segment 檔案可以同時被 HLS 的 playlist 與 DASH 的 MPD 引用。HLS 用 `#EXT-X-MAP` 指向初始化段，DASH 用 SegmentTemplate 的 `initialization` 屬性，兩邊下載的是同一組檔案。

CMAF 還帶來一個對低延遲很重要的概念：**chunk**。一個 CMAF segment 可以再分成多個 chunk（每個 chunk 是一組 moof＋mdat，例如 0.5 秒），封裝器每產生一個 chunk 就可以送出去，不必等整個 segment 完成。搭配 HTTP 的 chunked transfer encoding（第 20 章），播放器在 segment 還在產生時就開始下載，邊產生邊收。Low-Latency DASH 就是用這個方式降低延遲：MPD 用 `availabilityTimeOffset` 告訴播放器「segment 在完成前多久就可以開始要」，並用 ServiceDescription 宣告目標延遲。LL-HLS 則採用另一種做法，下一節說明。

## 38.12 LL-HLS：partial segment、preload hint 與 blocking reload

**LL-HLS**（Low-Latency HLS）是 Apple 在 2019 年提出、後來併入 HLS 規格新版的擴充，要在不放棄 CDN 快取的前提下把延遲降到幾秒。它保留正常長度的 segment（例如 2 秒），但把每個 segment 再切成更小的 **partial segment**（簡稱 **part**，例如 0.5 秒），讓播放器在 segment 完成前就能下載。它用了四個新機制：

1. **`#EXT-X-PART`**：列出 part。進行中的 segment 在清單上已有前幾個 part，segment 完成後舊的 part 會被移除；長度上限由 `#EXT-X-PART-INF:PART-TARGET` 宣告，`INDEPENDENT=YES` 表示從 keyframe 開始、可以從這裡起播。
2. **`#EXT-X-PRELOAD-HINT`**：預告下一個 part 的網址。播放器提前請求，伺服器先掛著，part 一產生就開始傳，省掉一個 RTT。
3. **blocking playlist reload**：在清單網址加上 `_HLS_msn=17&_HLS_part=2`，意思是「等第 17 個 segment 的第 2 個 part 出現了再給我清單」。這取代了定時輪詢，而且同一時刻所有觀眾送出的是相同網址，CDN 可以合併成一個回源請求。
4. **`#EXT-X-SERVER-CONTROL`**：宣告伺服器能力，例如 `CAN-BLOCK-RELOAD=YES`、`PART-HOLD-BACK=1.5`（起播點離 live edge 的最小距離，至少 2 個、建議 3 個 part target），以及 `CAN-SKIP-UNTIL`（**delta update**：播放器加上 `_HLS_skip=YES`，伺服器用 `#EXT-X-SKIP` 省略清單中舊的部分）。

另外 `#EXT-X-RENDITION-REPORT` 在清單裡附上其他 ABR 版本的最新序號，讓播放器切換版本時不必先多抓一次清單。

```text
 播放器                                         CDN edge                              origin／封裝器
   │── GET 720p.m3u8 ─────────────────────────────────►│── 回源 ───────────────────────────────────►│
   │◄─ playlist：…seg17.part1、PRELOAD-HINT seg17.part2 ────────────────────────────────────────────│
   │                                                   │                                            │
   │── GET 720p.m3u8?_HLS_msn=17&_HLS_part=2 ─────────►│── 同一網址的 1,800 個請求合併成 1 個 ─────►│
   │── GET seg17.part2.mp4（preload hint）────────────►│───────────────────────────────────────────►│
   │                    （兩個請求都被掛著）           │                     part2 還沒產生，先掛著 │
   │                                                   │                                            │ ← 0.5 秒後 part2 完成
   │◄─ seg17.part2.mp4（立刻開始傳）───────────────────│◄───────────────────────────────────────────│
   │◄─ playlist：…seg17.part2、PRELOAD-HINT seg17.part3 ────────────────────────────────────────────│
   │── GET ?_HLS_msn=17&_HLS_part=3 ＋ GET seg17.part3.mp4 ……（每 0.5 秒重複一次）                  │
```

從上往下看，播放器第一次下載清單後就進入一個固定的節奏：每拿到一個 part，就同時送出兩個請求，一個是「等下一個 part 出現再給我清單」的 blocking reload，一個是 preload hint 指向的下一個 part。兩個請求都被掛在伺服器上，part 一產生就同時回應。結果是播放器幾乎在 part 產生的同時就拿到它，延遲主要只剩下 PART-HOLD-BACK（例如 3 × 0.5 = 1.5 秒）加上編碼、轉碼與傳輸。代價則寫在中間那一列：CDN 必須支援「掛住請求」與「合併相同請求」（request collapsing），而且快取鍵必須包含 `_HLS_msn` 與 `_HLS_part` 這些查詢參數，否則不同 part 的請求會拿到同一份快取。

LL-HLS 的取捨很直接：buffer 只剩一兩秒，網路稍有波動就可能卡頓，所以播放器通常會微調播放速度來維持目標延遲。對聲聲 Live 的講座來說，3 到 5 秒的延遲已經足以讓聊天室的問答自然進行，成本仍然是 CDN 的 HTTP 流量。

> [!note] 2026 現況
> 依 2026 年 10 月查證：HLS 的新版規格 `draft-pantos-hls-rfc8216bis-22`（2026-05，描述 protocol version 13）以 Independent Submission 送到 RFC Editor，尚未取得 RFC 編號；LL-HLS 的 `EXT-X-PART`、`EXT-X-PRELOAD-HINT`、blocking reload、`EXT-X-SERVER-CONTROL`、`EXT-X-RENDITION-REPORT` 等機制都在這份文件中（依知識）。MPEG-DASH 的最新版次本書未能確認；CMAF 為 ISO/IEC 23000-19，DASH-IF 另有互通性與低延遲 DASH 的實作指南（依知識）。

## 38.13 WHIP 與 WHEP：用 HTTP 包裝 WebRTC

第 36 章說過，WebRTC 規格刻意不定義 signaling：兩端怎麼交換 SDP offer／answer，由應用程式自己決定。這對視訊通話很合理，但對直播很不方便：每一家平台都用自己的 WebSocket 協定交換 SDP，OBS 或硬體編碼器不可能逐一支援。**WHIP**（WebRTC-HTTP Ingestion Protocol）把推流的 signaling 標準化成最簡單的形式：一個 HTTP POST。**WHEP**（WebRTC-HTTP Egress Protocol）用同樣的方式處理觀看。

```text
 OBS（WHIP client）                                         live.shengsheng.example（WHIP endpoint）
   │── POST /whip/talk-1017 ──────────────────────────────────────────────►│
   │     Authorization: Bearer <短效 token>                                │
   │     Content-Type: application/sdp                                     │
   │     （body：SDP offer，sendonly 的音訊與視訊）                        │
   │◄─ 201 Created ────────────────────────────────────────────────────────│
   │     Location: /whip/talk-1017/session/7c1e                            │  ← 這個 session 的資源網址
   │     Content-Type: application/sdp                                     │
   │     Link: <turn:turn.shengsheng.example>; rel="ice-server"
   │     （body：SDP answer）                                              │
   │                                                                       │
   │══ ICE 連線檢查 → DTLS 交握 → SRTP 媒體（第 36 章）═══════════════════►│
   │                                                                       │
   │── PATCH /whip/talk-1017/session/7c1e（trickle ICE 或 ICE restart）───►│   （選用）
   │── DELETE /whip/talk-1017/session/7c1e ───────────────────────────────►│   結束推流
```

整個流程只有一來一回：client 把 SDP offer 用 POST 送到 WHIP endpoint，用 Bearer token 驗證身分（第 27 章）；server 回 `201 Created`，body 是 SDP answer，`Location` header 指向這個推流 session 的資源網址，`Link` header 可以順便告訴 client 要用哪些 STUN／TURN 伺服器。之後就是標準的 WebRTC：ICE 找路、DTLS 交握、SRTP 加密的媒體（第 36 章）。要追加 ICE candidate 或做 ICE restart 時，對 session 網址送 PATCH；結束時送 DELETE。WHEP 完全對稱：觀眾把一個只收不送（recvonly）的 offer POST 到 WHEP endpoint（聲聲 Live 是 `live.shengsheng.example` 的 `/whep/talk-1017`），拿到 answer 後開始接收。

WHIP 的價值在於「一個網址加一個 token」就能推流，端到端延遲可以壓到 1 秒以內。限制來自 WebRTC 本身：NAT 與防火牆需要 TURN；網路差時 WebRTC 寧可降畫質、丟 frame，而不是像 SRT 用固定的 latency 換穩定，所以專業製作的 contribution 仍多半用 SRT。分發端用 WHEP 則每個觀眾都是一條要由 SFU 轉送的連線（第 37 章），無法靠 CDN 快取，幾千人以上成本明顯較高。

聲聲 Live 的設計是混合式的：所有觀眾預設看 LL-HLS，經 CDN 的 `watch.shengsheng.example` 取得（`live.shengsheng.example` 只是媒體伺服器，負責 ingest 與 WHIP／WHEP，不直接面對大量觀眾）；被主持人邀請「上台」發問的學生，播放器切到 WHEP，延遲降到 1 秒內，問完再切回 LL-HLS。這樣只有同時在台上的少數人需要 SFU 資源。

> [!note] 2026 現況
> 依 2026 年 10 月查證：WHIP 已是 RFC 9725（2025 年 3 月，Standards Track）。WHEP 仍是 IETF WG draft（`draft-ietf-wish-whep-04`，2026 年 6 月），原訂的里程碑已延誤，實作前要確認 server 與 client 依據的版本。依知識（未經本次查證），OBS Studio 30 以後內建 WHIP 輸出。另一個值得追蹤的方向是 **Media over QUIC**（MoQ）：它想在 QUIC（第 13 章）上建立同時適合 contribution 與 distribution 的發布／訂閱媒體傳輸，兼顧低延遲與類似 CDN 的轉送規模；`draft-ietf-moq-transport` 仍是 WG draft，尚未成為標準（版次更新頻繁，本書未查證最新版次）。

## 38.14 延遲與穩定性的取捨

到這裡，可以把整章的協定放在同一張表上比較。下表的延遲是端到端（現場到觀眾畫面）的典型量級，實際數字取決於編碼器設定、轉碼與播放器實作：

| 方案 | 典型端到端延遲 | 網路不穩時的表現 | 規模與成本 | 適合的場景 |
|---|---|---|---|---|
| RTMP 推流 → HLS（6 秒 segment） | 約 15–30 s | 觀看端很穩，推流端怕丟包 | CDN，便宜、可到百萬人 | 不需互動的大型直播、事後回放 |
| SRT 推流 → HLS（2 秒 segment） | 約 6–10 s | 推流端可抗丟包，觀看端仍穩 | CDN | 一般直播 |
| SRT 推流 → LL-HLS／LL-DASH | 約 2–5 s | 觀看端 buffer 小，較容易卡頓 | CDN，但需支援 blocking 請求 | 聊天室互動、講座問答、體育賽事 |
| WHIP 推流 → WHEP 觀看（SFU） | 約 0.3–1 s | 降畫質、丟 frame 以維持即時 | SFU，每位觀眾一條連線，成本高 | 上台發問、拍賣、需要即時回應的少數觀眾 |
| SRT 點對點（不經轉碼） | latency 設定值＋編解碼，約 0.2–2 s | 可依 RTT 調整 latency 換穩定 | 一對一或少數 | 遠端製作、攝影棚之間傳訊號 |

這張表可以讀出一條清楚的規律：**延遲越低，buffer 越小，能吸收的網路波動越少，擴展到大量觀眾的成本越高**。HLS 用十幾秒的 buffer 換來 CDN 的規模與幾乎不卡的觀看；WebRTC 用不到一秒的延遲換來昂貴的 SFU 與「網路差就降畫質」；SRT 則把這個取捨變成一個可以調的參數。沒有一個方案在三個面向都最好，設計時要先問「這個場景真正需要多低的延遲」。

```text
 需要觀眾與講者即時對話（< 1 秒）？
   ├─ 是 ──► 人數少（數十人內）？ ── 是 ──► WebRTC／WHEP 經 SFU（第 37 章）
   │                              └─ 否 ──► 大部分人 LL-HLS，上台的少數人切 WHEP
   └─ 否 ──► 聊天室互動需要跟得上（數秒內）？
               ├─ 是 ──► LL-HLS 或 LL-DASH（CDN 要支援 blocking 請求與快取鍵）
               └─ 否 ──► 傳統 HLS／DASH（2–6 秒 segment），最穩、最便宜

 推流端（contribution）：
   路徑有丟包或 RTT 大？ ── 是 ──► SRT，latency ≈ 3–4 × RTT 起跳；UDP 被擋時退回 RTMPS
                        └─ 否 ──► RTMPS 也可以；要瀏覽器直接推流則用 WHIP
```

這張決策樹把「觀看端」與「推流端」分開決定，因為它們是兩個獨立的取捨：推流端看的是那一條路徑的品質，觀看端看的是觀眾數量與互動需求。聲聲 Live 改版後的組合是：推流 SRT（latency 依講者的 RTT 設定，退路是 RTMPS）、觀看 LL-HLS（2 秒 segment、0.5 秒 part）、上台發問 WHEP。

## 38.15 動手做：模擬 SRT 式傳輸與 LL-HLS 播放器

Joe 要說服團隊兩件事：推流的 latency 要依 RTT 設定，而不是一律用預設值；觀看端的延遲主要由 segment 與 part 的長度決定。這一節用三個實驗重現 Joe 的論證。前兩個實驗模擬 SRT 式的傳輸，第三個實驗模擬 LL-HLS 的封裝器與播放器。

### 實驗一與實驗二：latency 設定與準時到達率

下面的程式實作一個簡化的 SRT 式傳輸：送方每 5 ms 送一個帶序號與 timestamp 的封包；收方看到跳號立刻送 NAK，並每隔一段時間把還沒補上的序號再要一次；送方收到 NAK 就重傳；收方依 TSBPD 在「timestamp＋單向延遲＋latency」交付封包，到時間還沒收到的就 too-late drop。每一個資料封包與 NAK 都真的用 38.4 節的 header 格式編碼，經過 127.0.0.1 上的一對 UDP socket 送出再收回；但「封包何時到達、會不會遺失」由模擬時鐘與亂數決定，這樣才能在一秒內模擬 10 秒的串流，而且每次執行結果相同。

```python
import heapq
import random
import socket
import struct

HDR = struct.Struct("!IIII")          # SRT 式 16-byte header（見 38.4 節）
NAK_TYPE = 0x8003_0000                # F=1、control type 0x0003
PKT_INTERVAL_MS = 5                   # 每 5 ms 一個封包 ≈ 200 pkt/s ≈ 2.1 Mbps


class Wire:
    """封包真的經過 127.0.0.1 的 UDP socket 編解碼；送達時間由模擬時鐘決定。"""

    def __init__(self):
        self.a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.a.bind(("127.0.0.1", 0))
        self.b.bind(("127.0.0.1", 0))
        self.bytes = 0

    def carry(self, src, dst, data):
        src.sendto(data, dst.getsockname())
        got, _ = dst.recvfrom(2048)
        self.bytes += len(got)
        return got

    def close(self):
        self.a.close()
        self.b.close()


def simulate(latency_ms, rtt_ms, loss, n=2000, seed=1, drop_plan=None, burst=False, wire=None, trace=None):
    rng = random.Random(seed)
    owd = rtt_ms / 2                                  # 單向延遲
    events, order = [], 0
    bad = False                                       # Gilbert 模型：目前是否在「壞」狀態

    def lost(kind, seq, attempt):
        nonlocal bad
        if drop_plan is not None:                     # 追蹤模式：照劇本丟包
            return (kind, seq, attempt) in drop_plan
        if burst:                                     # 平均 5% 丟包，但集中成一串一串
            bad = rng.random() < (0.75 if bad else 0.013)
            return bad and rng.random() < 0.8
        return rng.random() < loss

    def push(t, kind, data):
        nonlocal order
        order += 1
        heapq.heappush(events, (t, order, kind, data))

    send_buf = {}                                     # seq -> (timestamp_us, 已重傳次數)
    arrived, loss_list, last_nak = {}, set(), {}
    next_expected, retrans, delivered = 0, 0, 0
    nak_interval = max(20, rtt_ms / 2)               # 週期性 NAK 的間隔（簡化版）
    deadline = lambda seq: seq * PKT_INTERVAL_MS + owd + latency_ms   # TSBPD 的播出時間

    for seq in range(n):
        push(seq * PKT_INTERVAL_MS, "send", seq)
        push(deadline(seq), "play", seq)              # TSBPD：時間到才交給解碼器
    push(nak_interval, "nak_timer", None)

    def transmit(now, seq, attempt):
        ts_us = int(seq * PKT_INTERVAL_MS * 1000)
        pkt = HDR.pack(seq, (0b11 << 30) | (int(attempt > 0) << 26) | seq, ts_us, 0x5A5A) + bytes(1316)
        if wire:
            pkt = wire.carry(wire.a, wire.b, pkt)
        gone = lost("data", seq, attempt)
        if trace is not None and (attempt or gone):
            trace.append(f"{now:7.1f} ms  送出 #{seq}{'（重傳）' if attempt else ''}{' ── 在路上遺失' if gone else ''}")
        if gone:
            return
        push(now + owd, "arrive", pkt)

    def send_nak(now, seqs):
        pkt = struct.pack(f"!IIII{len(seqs)}I", NAK_TYPE, 0, int(now * 1000), 0x5A5A, *seqs)
        if wire:
            pkt = wire.carry(wire.b, wire.a, pkt)
        for s in seqs:
            last_nak[s] = now
        if trace is not None:
            trace.append(f"{now:7.1f} ms  收方送 NAK {list(seqs)}")
        if not lost("nak", seqs[0], 0):
            push(now + owd, "nak", pkt)

    while events:
        now, _, kind, data = heapq.heappop(events)
        if kind == "send":
            send_buf[data] = 0
            transmit(now, data, 0)
        elif kind == "arrive":
            w0, w1, ts_us, _ = HDR.unpack(data[:16])
            seq = w0 & 0x7FFF_FFFF
            on_time = now <= deadline(seq)
            if on_time and seq not in arrived:
                arrived[seq] = now
            if trace is not None and (w1 >> 26 & 1 or not on_time):
                note = "準時，在 buffer 裡等播出" if on_time else "已經過了播出時間，直接丟棄"
                trace.append(f"{now:7.1f} ms  收到 #{seq}{'（重傳）' if w1 >> 26 & 1 else ''}：{note}")
            loss_list.discard(seq)
            if seq > next_expected:                   # 序號跳號 = 中間有封包遺失，立刻回報
                gap = [s for s in range(next_expected, seq) if s not in arrived]
                loss_list.update(gap)
                if gap:
                    send_nak(now, gap)
            next_expected = max(next_expected, seq + 1)
        elif kind == "nak":
            w0, _, _, _ = HDR.unpack(data[:16])
            for (s,) in struct.iter_unpack("!I", data[16:]):
                too_old = now - s * PKT_INTERVAL_MS > 1.25 * latency_ms + rtt_ms  # 送方也會放棄太舊的封包
                if s in send_buf and not too_old:
                    send_buf[s] += 1
                    retrans += 1
                    transmit(now, s, send_buf[s])
        elif kind == "play":
            if data in arrived:
                delivered += 1
                if trace is not None and data in (3, 7):
                    trace.append(f"{now:7.1f} ms  播出 #{data}（timestamp {data * PKT_INTERVAL_MS} ms + {owd:.0f} + latency {latency_ms}）")
            else:
                loss_list.discard(data)               # too-late drop：跳過它，不再要求重傳
                if trace is not None:
                    trace.append(f"{now:7.1f} ms  #{data} 到了播出時間仍沒收到：跳過（too-late drop）")
        elif kind == "nak_timer":
            again = sorted(s for s in loss_list if now - last_nak.get(s, -1e9) > rtt_ms)
            if again:
                send_nak(now, again)
            if now < n * PKT_INTERVAL_MS + latency_ms + rtt_ms:
                push(now + nak_interval, "nak_timer", None)

    return delivered / n, retrans / n


# 實驗一：照劇本丟包，看一次重傳成功與一次「來不及」
trace = []
wire = Wire()
simulate(120, 40, 0, n=12, wire=wire, trace=trace,
         drop_plan={("data", 3, 0), ("data", 7, 0), ("data", 7, 1), ("data", 7, 2)})
print("實驗一：latency 120 ms、RTT 40 ms")
print("\n".join(trace))

# 實驗二：不同 latency × 不同網路
print("\n實驗二：準時到達率（重傳額外頻寬）")
paths = [("棚內光纖 RTT 20, 0.5%", 20, 0.005, False), ("飯店 Wi-Fi RTT 80, 3%", 80, 0.03, False),
         ("4G 叢發 RTT 80, ~5%", 80, 0.05, True), ("跨洲 RTT 250, 3%", 250, 0.03, False)]
lats = [120, 250, 500, 1000]
print(f"{'路徑':<22}" + "".join(f"{f'latency {l}':>18}" for l in lats))
results = {}
for name, rtt, p, burst in paths:
    cells = []
    for lat in lats:
        ok, extra = simulate(lat, rtt, p, burst=burst, wire=wire, seed=1)
        results[(name, lat)] = ok
        cells.append(f"{ok * 100:7.2f}% (+{extra * 100:4.1f}%)")
    print(f"{name:<22}" + "".join(f"{c:>18}" for c in cells))
print(f"\n經過 127.0.0.1 的 UDP bytes：{wire.bytes:,}")
wire.close()
assert results[("跨洲 RTT 250, 3%", 120)] < 0.98 < results[("跨洲 RTT 250, 3%", 1000)]
assert results[("飯店 Wi-Fi RTT 80, 3%", 500)] > 0.999
```

```text
實驗一：latency 120 ms、RTT 40 ms
   15.0 ms  送出 #3 ── 在路上遺失
   35.0 ms  送出 #7 ── 在路上遺失
   40.0 ms  收方送 NAK [3]
   60.0 ms  收方送 NAK [7]
   60.0 ms  送出 #3（重傳）
   80.0 ms  送出 #7（重傳） ── 在路上遺失
   80.0 ms  收到 #3（重傳）：準時，在 buffer 裡等播出
  120.0 ms  收方送 NAK [7]
  140.0 ms  送出 #7（重傳） ── 在路上遺失
  155.0 ms  播出 #3（timestamp 15 ms + 20 + latency 120）
  175.0 ms  #7 到了播出時間仍沒收到：跳過（too-late drop）

實驗二：準時到達率（重傳額外頻寬）
路徑                           latency 120       latency 250       latency 500      latency 1000
棚內光纖 RTT 20, 0.5%       100.00% (+ 0.5%)  100.00% (+ 0.5%)  100.00% (+ 0.5%)  100.00% (+ 0.5%)
飯店 Wi-Fi RTT 80, 3%      99.85% (+ 3.4%)  100.00% (+ 3.4%)  100.00% (+ 3.4%)  100.00% (+ 3.4%)
4G 叢發 RTT 80, ~5%        99.45% (+ 4.0%)  100.00% (+ 4.2%)  100.00% (+ 4.2%)  100.00% (+ 4.2%)
跨洲 RTT 250, 3%           96.70% (+ 3.1%)   96.70% (+ 3.1%)   99.95% (+ 3.5%)  100.00% (+ 3.5%)

經過 127.0.0.1 的 UDP bytes：43,877,688
```

實驗一用劇本指定遺失哪些封包，逐行追蹤兩個遺失的命運。#3 在 15 ms 遺失，40 ms 收方看到 #4 而發現跳號，送出 NAK [3]；60 ms 送方重傳，80 ms 到達，155 ms 準時交付，這和 38.5 節的時序圖一模一樣。#7 的運氣差得多：第一次在 35 ms 遺失，60 ms 的 NAK 換來 80 ms 的重傳又遺失；收方在 120 ms 用週期 NAK 再要一次（距上次 NAK 已超過一個 RTT），140 ms 的第二次重傳還是遺失；下一次週期 NAK 的時間已經超過 #7 的交付時間 175 ms（35＋20＋120），所以收方在 175 ms 跳過 #7。這就是 too-late drop：latency 120 ms、RTT 40 ms，期限內只容得下兩次重傳，第三次就來不及了。

實驗二每一格是一次 10 秒、2,000 個封包的模擬，括號裡是重傳封包佔原始封包的比例。逐列看：

- **棚內光纖**（RTT 20 ms、丟包 0.5%）：預設的 120 ms 已是 RTT 的 6 倍，全部 100%，攝影棚維持預設值即可。
- **飯店 Wi-Fi**（RTT 80 ms、丟包 3%）：120 ms 只有 1.5 倍 RTT，99.85% 看起來很高，但每秒 200 個封包的 0.15% 等於每 3 秒左右丟一個，每一個都可能是一塊破圖；250 ms（約 3 倍）以上才完全修補。
- **4G 叢發**（RTT 80 ms、平均約 5% 但一串一串）：連續遺失時 NAK 與重傳也容易一起遺失，120 ms 只剩 99.45%，比同 RTT 的 Wi-Fi 更差。
- **跨洲**（RTT 250 ms、丟包 3%）：120 與 250 ms 都是 96.70%，重傳全部失敗，因為一次重傳至少要一個 RTT，SRT 退化成純 UDP；500 ms（2 倍）勉強修補一次，1000 ms（4 倍）才完全修補。

把四列合起來看，決定到達率的不是 latency 的絕對值，而是 **latency 與 RTT 的比值**：比值小於 1 完全沒有重傳的機會，2 倍左右能修補大部分，3 到 4 倍以上才能應付重傳又遺失的情況。括號裡的重傳比例也透露了頻寬成本：重傳量大約等於丟包率再多一些（重傳本身也會遺失），叢發丟包的 4G 要多用 4% 左右的頻寬，都還在 `SRTO_OHEADBW` 預設的 25% 之內。這個模擬刻意簡化了幾件事：單向延遲固定、週期 NAK 間隔取 max(20 ms, RTT/2)、送方保留封包的期限取 1.25 × latency＋RTT，這些都是本程式的選擇而不是 libsrt 的精確行為，但「比值決定成敗」的結論與 SRT 社群的經驗法則一致。

### 實驗三：HLS playlist 與播放器延遲

第二個程式在 127.0.0.1 上啟動一個 HTTP server 扮演封裝器與 origin，依模擬時鐘產生 media playlist，支援 LL-HLS 的 part、preload hint 與 blocking reload；client 端用 `http.client` 下載 playlist、自己寫的解析器讀出 segment 與 part，再依規範決定起播點，算出延遲。模擬的時間透過自訂的 `X-Sim-Now` header 在兩端之間傳遞，「blocking」就是 server 把回應的模擬時間推遲到 part 出現的那一刻。

```python
import math
import re
import threading
from datetime import datetime, timedelta
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

T0 = datetime.fromisoformat("2026-10-17T19:30:00.000+08:00")   # 模擬時鐘 0 秒 = 講座開始
PIPELINE = 2.0      # 擷取＋編碼＋SRT latency＋轉碼，媒體到 packager 時已晚 2 秒
FETCH = 0.05        # 每個 HTTP 請求經過 CDN 的往返時間（示意）
CONFIGS = {"hls6": (6, None), "hls2": (2, None), "ll2": (2, 0.5)}   # (segment 秒, part 秒)


def render(now, seg, part, window=5):
    """packager 在模擬時間 now 看到的 media playlist。"""
    media = max(0.0, now - PIPELINE)          # packager 手上已有的媒體時間
    done = int(media // seg)                  # 已完成的 segment 數
    first = max(0, done - window)
    out = ["#EXTM3U", "#EXT-X-VERSION:6", f"#EXT-X-TARGETDURATION:{seg}", f"#EXT-X-MEDIA-SEQUENCE:{first}"]
    if part:
        out += [f"#EXT-X-SERVER-CONTROL:CAN-BLOCK-RELOAD=YES,PART-HOLD-BACK={3 * part:.1f}",
                f"#EXT-X-PART-INF:PART-TARGET={part}"]
    out.append("#EXT-X-PROGRAM-DATE-TIME:" + (T0 + timedelta(seconds=first * seg)).isoformat(timespec="milliseconds"))

    def parts_of(msn, count):
        for j in range(count):
            ind = ",INDEPENDENT=YES" if (j * part) % 1 == 0 else ""     # 每 1 秒一個 keyframe
            out.append(f'#EXT-X-PART:DURATION={part:.3f},URI="seg{msn}.part{j}.mp4"{ind}')

    for msn in range(first, done):
        if part and msn >= done - 1:          # 只保留最近的 part，舊的只留完整 segment
            parts_of(msn, int(seg / part))
        out += [f"#EXTINF:{seg:.3f},", f"seg{msn}.{'mp4' if part else 'ts'}"]
    if part:
        j = int((media - done * seg) // part)  # 正在進行中的 segment 已完成幾個 part
        parts_of(done, j)
        out.append(f'#EXT-X-PRELOAD-HINT:TYPE=PART,URI="seg{done}.part{j}.mp4"')
    return "\n".join(out) + "\n"


class Packager(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        seg, part = CONFIGS[url.path.strip("/").split(".")[0]]
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        now = float(self.headers["X-Sim-Now"])
        if "_HLS_msn" in q:                   # blocking reload：等到指定的 part 出現才回應
            msn, p = int(q["_HLS_msn"]), int(q.get("_HLS_part", 0))
            now = max(now, PIPELINE + msn * seg + (p + 1) * part + 1e-9)
        body = render(now, seg, part).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        self.send_header("X-Sim-Now", f"{now:.6f}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def parse(text):
    assert text.startswith("#EXTM3U")
    pl = {"segments": [], "parts": [], "hold_back": None}
    attrs = lambda s: {k: v.strip('"') for k, v in re.findall(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', s)}
    msn = pending = None
    for line in text.splitlines():
        if line.startswith("#EXT-X-TARGETDURATION:"):
            pl["target"] = int(line.split(":")[1])
        elif line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            msn = int(line.split(":")[1])
        elif line.startswith("#EXT-X-SERVER-CONTROL:"):
            pl["hold_back"] = float(attrs(line)["PART-HOLD-BACK"])
        elif line.startswith("#EXT-X-PART:"):
            a = attrs(line)
            pl["parts"].append((msn, float(a["DURATION"]), a["URI"], "INDEPENDENT" in a))
        elif line.startswith("#EXTINF:"):
            pending = float(line[8:].rstrip(","))
        elif line and not line.startswith("#"):
            pl["segments"].append((msn, pending, line))
            msn += 1
        elif line.startswith("#EXT-X-PRELOAD-HINT:"):
            pl["hint"] = attrs(line)["URI"]
    return pl


def fetch(conn, path, now):
    conn.request("GET", path, headers={"X-Sim-Now": f"{now:.6f}"})
    resp = conn.getresponse()
    text = resp.read().decode()
    return text, float(resp.getheader("X-Sim-Now")) + FETCH


def join(conn, name, t_join):
    """回傳（開始播放時的延遲, 60 秒內的 HTTP 請求數）。"""
    seg, part = CONFIGS[name]
    text, now = fetch(conn, f"/{name}.m3u8", t_join)
    pl = parse(text)
    if part:   # LL-HLS：從 live edge 往回 PART-HOLD-BACK，再對齊到可以獨立解碼的 part
        edge = pl["segments"][-1][0] * seg + seg + sum(p[1] for p in pl["parts"] if p[0] > pl["segments"][-1][0])
        start = math.floor((edge - pl["hold_back"]) + 1e-9)
        requests = 2 * int(60 / part)          # 每個 part：一次 blocking playlist ＋ 一次 part 下載
    else:      # 傳統 HLS：離最後一個 segment 結尾至少 3 個 target duration
        edge = (pl["segments"][-1][0] + 1) * seg
        start = max(m * seg for m, _, _ in pl["segments"] if m * seg <= edge - 3 * pl["target"])
        requests = 2 * int(60 / seg)           # 每個 segment：一次 playlist reload ＋ 一次下載
    play_at = now + FETCH                      # 再下載第一段媒體才開始播
    return play_at - start, requests


server = ThreadingHTTPServer(("127.0.0.1", 0), Packager)
threading.Thread(target=server.serve_forever, daemon=True).start()
conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)

text, _ = fetch(conn, "/ll2.m3u8", 37.3)
print(text)
pl = parse(text)
n_parts = len([p for p in pl["parts"] if p[0] == 17])
print(f"解析：target {pl['target']} s，最後完整 segment {pl['segments'][-1][2]}，"
      f"進行中的 seg17 已有 {n_parts} 個 part，preload hint {pl['hint']}")

held, t = fetch(conn, "/ll2.m3u8?_HLS_msn=17&_HLS_part=2", 37.3)
print(f"37.30 s 送出 blocking reload（_HLS_msn=17&_HLS_part=2），伺服器在 {t - FETCH:.2f} s 才回應，結尾：")
print("\n".join(held.splitlines()[-2:]))
assert held.splitlines()[-2].endswith('INDEPENDENT=YES') and 'seg17.part2' in held.splitlines()[-2] and abs(t - FETCH - 37.5) < 1e-6

print("\n設定                        起播延遲：平均   最小    最大   60 秒內請求數")
labels = {"hls6": "傳統 HLS，6 秒 segment", "hls2": "傳統 HLS，2 秒 segment", "ll2": "LL-HLS，2 秒＋0.5 秒 part"}
summary = {}
for name, label in labels.items():
    lat = [join(conn, name, 30 + i * 0.1)[0] for i in range(120)]   # 在 12 秒內不同時間點加入
    summary[name] = sum(lat) / len(lat)
    print(f"{label:<22}{summary[name]:>10.1f} s {min(lat):>5.1f} s {max(lat):>5.1f} s {join(conn, name, 37.3)[1]:>8}")
conn.close()
server.shutdown()
server.server_close()
assert summary["hls6"] > 20 > summary["hls2"] > summary["ll2"] < 5
```

```text
#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:2
#EXT-X-MEDIA-SEQUENCE:12
#EXT-X-SERVER-CONTROL:CAN-BLOCK-RELOAD=YES,PART-HOLD-BACK=1.5
#EXT-X-PART-INF:PART-TARGET=0.5
#EXT-X-PROGRAM-DATE-TIME:2026-10-17T19:30:24.000+08:00
#EXTINF:2.000,
seg12.mp4
#EXTINF:2.000,
seg13.mp4
#EXTINF:2.000,
seg14.mp4
#EXTINF:2.000,
seg15.mp4
#EXT-X-PART:DURATION=0.500,URI="seg16.part0.mp4",INDEPENDENT=YES
#EXT-X-PART:DURATION=0.500,URI="seg16.part1.mp4"
#EXT-X-PART:DURATION=0.500,URI="seg16.part2.mp4",INDEPENDENT=YES
#EXT-X-PART:DURATION=0.500,URI="seg16.part3.mp4"
#EXTINF:2.000,
seg16.mp4
#EXT-X-PART:DURATION=0.500,URI="seg17.part0.mp4",INDEPENDENT=YES
#EXT-X-PART:DURATION=0.500,URI="seg17.part1.mp4"
#EXT-X-PRELOAD-HINT:TYPE=PART,URI="seg17.part2.mp4"

解析：target 2 s，最後完整 segment seg16.mp4，進行中的 seg17 已有 2 個 part，preload hint seg17.part2.mp4
37.30 s 送出 blocking reload（_HLS_msn=17&_HLS_part=2），伺服器在 37.50 s 才回應，結尾：
#EXT-X-PART:DURATION=0.500,URI="seg17.part2.mp4",INDEPENDENT=YES
#EXT-X-PRELOAD-HINT:TYPE=PART,URI="seg17.part3.mp4"

設定                        起播延遲：平均   最小    最大   60 秒內請求數
傳統 HLS，6 秒 segment          23.0 s  20.1 s  26.0 s       20
傳統 HLS，2 秒 segment           9.0 s   8.1 s  10.0 s       60
LL-HLS，2 秒＋0.5 秒 part        4.0 s   3.6 s   4.5 s      240
```

輸出的第一部分是 37.3 秒時的 LL-HLS playlist。對照 38.12 節逐行看：`TARGETDURATION:2` 與 `PART-INF:PART-TARGET=0.5` 宣告 segment 2 秒、part 0.5 秒；`SERVER-CONTROL` 宣告支援 blocking reload，起播點至少離 live edge 1.5 秒。清單裡 seg12 到 seg15 只列完整 segment，最近完成的 seg16 同時列出 4 個 part 與完整的 segment，進行中的 seg17 只有前兩個 part，最後一行的 preload hint 指向還不存在的 seg17.part2。每隔一個 part 有一個 `INDEPENDENT=YES`，對應每 1 秒一個 keyframe。

第二部分是 blocking reload：播放器在 37.30 秒請求 `_HLS_msn=17&_HLS_part=2`，伺服器等到 37.50 秒 part2 產生才回應，回應的結尾就是剛出現的 part2 與指向 part3 的新 preload hint。37.3 秒時媒體時間是 35.3 秒（扣掉 2 秒的管線延遲），part2 涵蓋 35.0–35.5 秒，要到媒體時間 35.5、也就是模擬時間 37.5 秒才完成，數字完全吻合。

第三部分是三種設定的起播延遲，播放器在 30 到 42 秒之間的 120 個時間點加入。傳統 HLS 6 秒 segment 平均 23.0 秒、範圍 20.1 到 26.0 秒：剛好在新 segment 發布後加入是最好的情況（2 秒管線＋18 秒 hold-back），在下一個 segment 即將發布時加入則再多一個 segment 長度。2 秒 segment 降到 9 秒左右，LL-HLS 再降到 4 秒左右。最後一欄是代價：60 秒內的請求數從 20 個變成 240 個，1,800 名觀眾就是每秒約 7,200 個請求，CDN 能不能合併相同的 blocking 請求，決定了 origin 會不會被打垮。模擬沒有計入網路波動與播放器的追趕策略，實際延遲會略高，但相對關係與 38.2 節的延遲預算一致。

## 38.16 在工作上怎麼用

改版上線前，Joe、小晴與 Rita 把這章的內容整理成各角色的工作清單。

**影音工程師：依 RTT 設定 SRT，並在推流前做一次路徑測試。** 講者開播前一天，Joe 會請講者在現場網路跑一次測試推流，從 ingest 的統計讀出 RTT 與丟包率，再依實驗二的規律決定 latency。下面是常用的指令，注意兩個工具的 latency 單位不同：

```bash
# 講者端：ffmpeg 推流到 ingest（ffmpeg 的 latency 單位是「微秒」：500000 = 500 ms）
ffmpeg -re -i talk.mp4 -c:v libx264 -preset veryfast -tune zerolatency -g 30 -b:v 4500k \
  -c:a aac -b:a 128k -f mpegts \
  "srt://live.shengsheng.example:9000?mode=caller&latency=500000&pkt_size=1316&passphrase=${SRT_PASS}&streamid=#!::r=live/talk-1017,m=publish"

# 測試用 listener：srt-live-transmit（latency 單位是「毫秒」），每 1000 個封包印一次統計
srt-live-transmit "srt://:9000?mode=listener&latency=500" udp://127.0.0.1:5000 -s:1000

# 檢查 segment 是否從 keyframe 開始、keyframe 是否每 1 秒一個
ffprobe -v error -select_streams v -show_entries frame=pict_type,pts_time -of csv seg17.mp4 | grep ',I' | head
```

第一個指令的重點在 URL 參數：`latency=500000` 是 500 ms，`pkt_size=1316` 對齊 TS 封包，passphrase 從環境變數讀取以免留在 shell history；`-g 30` 讓 30 fps 的視訊每 1 秒一個 keyframe，對齊 2 秒的 segment，也讓 LL-HLS 每隔一個 part 就有可以起播的位置（實驗三的設定），`-tune zerolatency` 關掉會增加延遲的 lookahead 與 B-frame。

統計裡要看的欄位不多。`msRTT` 是 SRT 用 ACKACK 量到的 RTT，用來判斷 latency 是否至少有 3 到 4 倍；`pktRcvLoss` 是收方偵測到的遺失數；`pktRetrans` 是送方的重傳數；**`pktRcvDrop` 是最重要的一個**，它是 too-late drop 的數量，也就是觀眾真的會看到破圖的封包數，理想值是 0。`pktRcvLoss` 高但 `pktRcvDrop` 是 0，代表網路不好但 SRT 修補得了；`pktRcvDrop` 持續增加，就要加大 latency 或降低 bitrate。下面是一段示意輸出（欄位依版本略有不同）：

```text
（示意輸出）
msRTT   pktRcvLoss  pktRetrans  pktRcvDrop  mbpsRecvRate  msRcvBuf
 81.2        317         329           0          4.61        498
 83.9        402         415           0          4.58        501
```

這兩行告訴 Joe：RTT 約 80 ms、latency 500 ms 是 6 倍 RTT；遺失不少，但都被重傳補上，`pktRcvDrop` 為 0；`msRcvBuf` 約 500 ms，代表收方 buffer 剛好是 latency 那麼長。這就是可以開播的狀態。

**SRE：把直播拆段監控，並直接量延遲。** 直播出問題時，最常見的浪費是「每個人都盯著播放器」。小晴寫了一份分段檢查流程，由上游往下游查：

```text
 觀眾反映卡頓或延遲大
   │
   ├─ ① ingest：pktRcvDrop 在增加嗎？推流 bitrate 正常嗎？
   │     └─ 是 ─► 推流端問題：講者網路、latency 太小、bitrate 超過上傳頻寬
   ├─ ② 轉碼：輸出 frame rate 跟得上嗎？CPU／GPU 滿載嗎？
   │     └─ 是 ─► 轉碼資源不足或 ABR 階梯太多路
   ├─ ③ 封裝／origin：最新 segment 的 PROGRAM-DATE-TIME 和現在差多少？segment 有準時出現嗎？
   │     └─ 差距變大 ─► 上游延遲累積或封裝器卡住
   ├─ ④ CDN：playlist 的 Age header 多大？segment 的 4xx／5xx 比例？
   │     └─ playlist 被快取太久、404 被快取 ─► 修正快取設定（38.10 節）
   └─ ⑤ 播放器：rebuffer 次數、目前選的 ABR 版本、與 live edge 的距離
         └─ 只有部分觀眾 ─► 觀眾端網路或地區性的 CDN 問題
```

原則是「從上游往下游」：上游一出問題，下游每一段都會跟著異常。第 ③ 步是量延遲最實用的方法：用 `curl` 下載 media playlist，把最後一個 segment 的 PROGRAM-DATE-TIME 加上它的長度，和現在時間相減，就是到封裝器為止的延遲；再和播放器回報的延遲比較，就知道延遲出在封裝之前還是之後。

**後端工程師：推流憑證是一種 API。** 講者按下「準備直播」時，後端產生這場講座專用的 passphrase 與 stream ID（或 RTMPS 的 stream key），經 secrets manager 一次性顯示給講者，講座結束即撤銷；ingest 在 handshake 時查詢 stream ID 對應的頻道與 passphrase，查不到就拒絕。這和第 30 章的 API key 設計一樣：可撤銷、有範圍、有到期時間。

**前端與資安。** 前端的 LL-HLS 播放器要設定合理的目標延遲（設太低，網路一波動就卡頓），並把 rebuffer 次數、目前延遲與選中的 ABR 版本回報給後端，否則上面的第 ⑤ 步沒有資料可看。Rita 則確保 RTMP 只開 RTMPS、stream key 與 passphrase 不出現在 log 與截圖中，付費內容的 segment 用短效簽章網址保護，WHIP／WHEP 端點用短效 Bearer token 驗證。

## 38.17 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 設了 `latency=500` 卻還是破圖，統計顯示 latency 約 120 ms | ffmpeg（或 OBS）的 latency 單位是微秒，500 µs 等於沒設，協商後取了 ingest 的預設值 | ingest 端看協商後的 latency 或 `msRcvBuf`；檢查推流 URL | ffmpeg 寫 `latency=500000`；或在 ingest 設定合理的下限 |
| 推流畫面偶爾出現破圖或短暫凍結 | latency 對 RTT 的比值太小，重傳來不及，too-late drop | 統計中 `pktRcvDrop` 持續增加，`msRTT` 接近或大於 latency 的 1/3 | latency 調到 3–4 倍 RTT 以上；丟包嚴重時更高 |
| SRT 連不上，RTMPS 卻可以 | 講者所在網路或 ingest 的 security group 擋了 UDP | 講者端 caller 一直重試、ingest 完全收不到 handshake；用 `tcpdump -ni any udp port 9000` 確認 | 開放 UDP 9000；講者端網路無法開放時退回 RTMPS |
| SRT 連線被拒絕，log 顯示 bad secret 或類似原因 | 雙方的 passphrase 不一致，或只有一邊設定 | 檢查兩端設定；看 ingest 的拒絕原因 | 重新發放 passphrase，確認推流端完整複製（長度 10–80） |
| 推流 bitrate 很穩，但 SRT 的丟包與 drop 突然暴增 | 推流 bitrate 加上重傳超過上傳頻寬，SRT live 模式不會像 TCP 那樣自動降速 | 比較推流 bitrate 與實測上傳頻寬；重傳率隨時間上升 | 降低編碼 bitrate，留 30–50% 頻寬餘裕；或用能依統計調整 bitrate 的編碼器 |
| 觀眾的延遲比預期多好幾秒，而且不穩定 | media playlist 被 CDN 快取太久 | `curl -sI` 看 playlist 的 `Age` 與 `Cache-Control` | playlist 的 max-age 不超過 target duration 的一半；segment 才快取久 |
| 直播中途大量觀眾同時卡住一兩分鐘 | segment 剛產生前被請求，origin 回 404，CDN 把 404 快取了 | CDN log 中同一個 segment 的 404 集中出現；回應有快取 header | 錯誤回應不快取或只快取 1–2 秒；播放器不要請求超過 live edge 的 segment |
| 播放器報告 segment 長度超過 target duration，或切換版本時卡頓 | 編碼器的 GOP 與 segment 不對齊，或各 ABR 版本的 keyframe 位置不同 | `ffprobe` 看 keyframe 的時間；比對 `#EXTINF` 與 `TARGETDURATION` | 固定 GOP（例如 `-g 60`），關閉場景切換插入 keyframe，所有版本同步切點 |
| LL-HLS 上線後 origin 的請求量暴增 | CDN 沒有合併相同的 blocking 請求，或快取鍵沒有包含 `_HLS_msn`／`_HLS_part` | origin 的 QPS 約等於觀眾數 × 每秒 part 數；不同 part 拿到同一份回應 | 開啟 request collapsing，快取鍵包含這些查詢參數；確認 CDN 支援 LL-HLS |

除錯時先分清楚問題在 contribution 還是 distribution：所有觀眾同時出現的問題（同一秒卡住、同一處破圖）幾乎都在 ingest 之前或封裝；只有部分觀眾的問題才在 CDN 或觀眾端。ingest 的 `pktRcvDrop` 是兩者之間的分界線，先看它，可以省下大半的猜測。

## 38.18 動手練習

1. **找出每條路徑需要的最小 latency**（延伸實驗二）。把實驗二的 latency 改成從 40 ms 到 1200 ms、每 20 ms 一格，對每條路徑找出到達率達到 99.99% 的最小 latency，換算成 RTT 的倍數。再把 4G 叢發模型的 `0.75`（留在壞狀態的機率）調成 0.9，觀察倍數的變化。
   答案要點：飯店 Wi-Fi 與跨洲路徑大約落在 3 倍 RTT 上下；叢發越長倍數越大，因為 NAK 與重傳也會一起遺失，要多等幾輪週期 NAK。

2. **限制重傳頻寬**（延伸實驗二）。仿照 `SRTO_OHEADBW`，在 `simulate()` 裡加一個限制：任何 100 ms 的時間窗內，重傳數不能超過原始封包數的 X%，超過的 NAK 直接忽略。用 4G 叢發路徑比較 X＝25 與 X＝5 的到達率。
   答案要點：叢發時重傳需求集中在短時間內，X 太小就算 latency 夠大也修補不了，所以上傳頻寬要留給重傳。

3. **4 秒 segment 加 1 秒 part**（延伸實驗三）。在 `CONFIGS` 加入 `(4, 1.0)`，並讓 `INDEPENDENT=YES` 只出現在每個 segment 的第一個 part（GOP＝4 秒），比較延遲與請求數。
   答案要點：PART-HOLD-BACK 變成 3 秒，起播點又要往回對齊到 segment 開頭，延遲多出好幾秒，請求數減半；所以 LL-HLS 常搭配較短的 GOP。

4. **用 ffmpeg 產生本機的 HLS 直播**（真實工具）。執行 `ffmpeg -re -f lavfi -i testsrc2=size=1280x720:rate=30 -f lavfi -i sine -c:v libx264 -g 60 -c:a aac -f hls -hls_time 2 -hls_list_size 5 -hls_flags delete_segments /tmp/hls/index.m3u8`，另一個終端執行 `python3 -m http.server 8080 --bind 127.0.0.1 -d /tmp/hls`，再每秒用 `curl -s 127.0.0.1:8080/index.m3u8` 看清單。
   答案要點：`#EXT-X-MEDIA-SEQUENCE` 每 2 秒加一，清單永遠只有 5 個 segment，舊檔案被刪除；`#EXTINF` 約為 2 秒。把 `-g 60` 改成 `-g 150`（5 秒 GOP），segment 會被迫變成 5 秒左右，`TARGETDURATION` 也跟著變大，驗證 segment 必須從 keyframe 開始。

5. **在 Linux 上用 netem 觀察真實的 SRT**（真實工具）。在自己的 Linux 測試機上用 `sudo tc qdisc add dev lo root netem delay 40ms loss 3%` 讓 loopback 有延遲與丟包，用 `srt-live-transmit` 在本機建立一對 caller 與 listener，分別以 latency 100 與 400（毫秒）傳一段 TS 檔，比較統計中的 `msRTT`、`pktRcvLoss` 與 `pktRcvDrop`。做完記得 `sudo tc qdisc del dev lo root`。
   答案要點：netem 對 lo 的兩個方向都加了 40 ms，所以 `msRTT` 約 80 ms；latency 100 時 `pktRcvDrop` 明顯大於 0，400 時接近 0，而 `pktRcvLoss` 兩者差不多，證明「遺失」與「丟棄」是兩回事。

6. **手算推流的頻寬預算**。講者在 RTT 120 ms、丟包 2% 的網路上，想推 6 Mbps 的 1080p。用 Mathis 公式（MSS 1448 bytes）估計 RTMP 的 TCP 吞吐量上限，再估計 SRT 需要的上傳頻寬與 latency。
   答案要點：1448 × 8 ÷ 0.12 × 1.22 ÷ √0.02 ≈ 0.83 Mbps，遠低於 6 Mbps，RTMP 撐不住。SRT 需要約 6 × 1.25 ＝ 7.5 Mbps 以上的上傳頻寬（實務上留到 9–12 Mbps 更安全），latency 至少 3–4 × 120 ＝ 360–480 ms，建議取 500 ms 以上；頻寬不足時應先降 bitrate。

## 本章重點整理

- 直播分成 contribution（講者到平台，一對一、要穩）與 distribution（平台到觀眾，一對多、要能擴展），兩段的需求不同，所以推流與觀看幾乎總是用不同的協定。
- 端到端延遲是管線各段的總和：編碼、contribution 傳輸、轉碼、封裝、CDN 與播放器 buffer；傳統 HLS 的延遲大部分來自 segment 長度乘上 hold-back，而不是網路。
- RTMP 跑在 TCP 上，靠 chunk 多工音訊與視訊；它的可靠性沒有期限，丟包時吞吐量下降、資料排隊，推流端只能丟 frame。Enhanced RTMP 用 FourCC 擴充了 codec，但沒有改變 TCP 的行為。
- SRT 在 UDP 上實作「有期限的 ARQ」：16 bytes 的 header 帶序號、timestamp 與 socket ID，收方用 NAK 主導重傳，TSBPD 依 timestamp 固定延遲交付，過期的封包 too-late drop。
- latency 是收方刻意加上的交付延遲，雙方協商取較大值；它決定期限內能重傳幾次，經驗上至少是 RTT 的 3–4 倍，丟包越多倍數越大，而且不低於預設的 120 ms。
- libsrt 與 srt-live-transmit 的 latency 單位是毫秒，ffmpeg（與 OBS 的 SRT 輸出）的 `latency` 是微秒，寫錯時協商會退回對方的設定；重傳另需頻寬（`SRTO_OHEADBW` 預設 25%），推流 bitrate 要留餘裕。
- caller 主動連線、listener 等待連線、rendezvous 雙方同時發起；handshake 的 induction 階段用 cookie 擋偽造來源，conclusion 階段協商 latency、交換金鑰與 stream ID。
- SRT 用 passphrase 經 PBKDF2 衍生的 KEK 包裝隨機的 SEK，只加密 payload；stream ID 用來選頻道與路由，是明文，不能當作秘密。
- HLS 用 multivariant playlist 列出 ABR 版本、media playlist 列出 segment；播放器依 target duration 重新載入清單，起播點至少離 live edge 三個 target duration。
- playlist 的快取時間要遠短於 target duration，segment 可以長期快取，錯誤回應不能長時間快取；segment 必須從 keyframe 開始，GOP 要與 segment 對齊。
- DASH 用 XML 的 MPD 與網址樣板描述 segment，依賴時鐘同步；CMAF 讓 HLS 與 DASH 共用同一組 fMP4 segment，並以 chunk 支援低延遲。
- LL-HLS 用 partial segment、preload hint、blocking reload 與 delta update，把延遲降到數秒；代價是請求數大增，CDN 必須支援掛住請求、合併相同請求與正確的快取鍵。
- WHIP 用一個 HTTP POST 交換 SDP 完成 WebRTC 推流，WHEP 用同樣的方式觀看；延遲可低於 1 秒，但分發要經過 SFU，成本遠高於 CDN。
- 延遲、穩定性與規模三者互相拉扯：設計時先決定場景真正需要的延遲，再分別為推流端與觀看端選擇協定。

## 延伸問答

> [!question]- Q1. TCP 本來就有重傳，為什麼 SRT 還要在 UDP 上自己做一套？
> 關鍵在「期限」。TCP 保證所有資料依序送達，遺失的封包一定要重傳成功，後面的資料才能交給應用程式；這對檔案與網頁是正確的語意，但對直播來說，一個晚了兩秒的畫面跟遺失一樣沒用，還會讓後面所有畫面一起晚到。而且 TCP 的擁塞控制把丟包解讀成擁塞而降速，在 Wi-Fi 或行動網路這種「有隨機丟包但未必擁塞」的路徑上，吞吐量會被壓到遠低於頻寬。
>
> SRT 在 UDP 上自己做 ARQ，就能加入 TCP 沒有的兩件事：一是 TSBPD 與 too-late drop，讓每個封包有交付期限，過期就放棄，遺失只影響那一個封包；二是 live 模式不因丟包降速，用固定的 bitrate 加上有上限的重傳頻寬。換句話說，SRT 不是「比 TCP 更可靠」，而是提供另一種可靠性的定義：在你指定的延遲內盡力可靠。這和第 13 章 QUIC 在 UDP 上重做傳輸層的理由相同：作業系統的 TCP 很難改，在 user space 用 UDP 才能快速實作新的語意。

> [!question]- Q2. 手算：講者的網路 RTT 150 ms、丟包約 2%，推流 bitrate 5 Mbps。SRT 的 latency 該設多少？收方 buffer 大約要多大？
> 依經驗法則，latency 至少是 RTT 的 3–4 倍，也就是 450–600 ms；丟包 2% 不算嚴重，但如果是無線網路的叢發丟包，建議往上取，例如 600–800 ms。latency 太小的後果可以用實驗二推理：低於 1 倍 RTT（150 ms）完全沒有重傳的機會；2 倍左右只能修補一次，重傳又遺失時就會 too-late drop。
>
> buffer 大小約等於 bitrate × latency：5 Mbps × 0.6 s ＝ 3 Mbit ≈ 375 KB；送方也要保留差不多長度的資料以備重傳。這對伺服器來說很小，真正要算的是頻寬：重傳要用額外頻寬，丟包 2% 時平均約多 2–3%，但叢發時會集中，`SRTO_OHEADBW` 預設允許 25%，所以上傳頻寬至少要 6.25 Mbps，實務上留到 7–10 Mbps 更安全。最後別忘了單位：用 ffmpeg 推流要寫 `latency=600000`。

> [!question]- Q3. 你在 ingest 的 SRT 統計看到 pktRcvLoss 每分鐘增加數百、pktRetrans 也差不多，但 pktRcvDrop 一直是 0。觀眾也反映畫面正常。需要處理嗎？
> 這是 SRT 正常運作的樣子。`pktRcvLoss` 是收方偵測到的遺失，代表路徑確實有丟包；`pktRetrans` 與它相近，代表送方收到 NAK 都重傳了；`pktRcvDrop` 是 0，代表所有遺失的封包都在 latency 期限內補上，沒有任何一個被 too-late drop，所以觀眾看不到任何影響。這正是 SRT 的價值：網路不完美，但修補的成本被固定的 latency 吸收了。
>
> 需要注意的是趨勢與餘裕，而不是立刻處理。第一，看重傳占用的頻寬比例，若接近上傳頻寬的上限，網路再惡化一點就會開始 drop。第二，看 `msRTT` 與 latency 的比值，若比值已經掉到 2 倍左右，叢發丟包時可能來不及。第三，把 `pktRcvDrop` 設為告警指標，它從 0 開始增加，才是觀眾會看到破圖的訊號。如果講者的網路長期如此，可以在下一場前與講者溝通改用有線網路。

> [!question]- Q4. 面試題：為什麼傳統 HLS 的延遲動輒二、三十秒？要降低延遲有哪些方法，各自的代價是什麼？
> 延遲來自幾個相乘的因素。封裝器要等一個 segment 完整結束才能發布，所以 live edge 本身就落後；播放器依規範至少離 live edge 三個 target duration 起播，用這段 buffer 吸收下載變慢或 segment 晚到的情況；再加上編碼、轉碼、CDN 與播放器的下載時間。6 秒 segment 光 hold-back 就是 18 秒，總和自然到 20–30 秒。
>
> 降低延遲的方法依序是：縮短 segment（例如 2 秒），延遲降到 6–10 秒，代價是請求數變多、GOP 必須跟著縮短而壓縮效率下降；改用 LL-HLS 或 LL-DASH，用 part 或 CMAF chunk 讓播放器在 segment 完成前就下載，延遲降到 2–5 秒，代價是 CDN 要支援 blocking 請求與合併，播放器 buffer 小、較容易卡頓；需要 1 秒以內時改用 WebRTC（WHEP），代價是放棄 CDN 快取、每位觀眾都要 SFU 資源。同時也要調整編碼器（關掉 lookahead 與 B-frame）與轉碼，這些在延遲預算中也佔了一到兩秒。

> [!question]- Q5. 看設定找原因：講者端 OBS 的 SRT 網址是 srt://live.shengsheng.example:9000?latency=800&streamid=…，ingest 設定 latency 120。開播後統計顯示協商的 latency 是 120 ms，破圖不斷。發生了什麼事？
> OBS 的 SRT 輸出建立在 ffmpeg 的 srt 協定上，URL 參數 `latency` 的單位是微秒，所以 `latency=800` 是 0.8 ms，而不是 800 ms。ffmpeg 把它換算成毫秒交給 libsrt 後，基本上等於 0。SRT 的 latency 是雙方協商取較大值，講者端提出約 0、ingest 端是 120 ms，結果就是 120 ms。講者的網路 RTT 如果是 80 ms 以上，120 ms 只容得下一次重傳，叢發丟包時就會大量 too-late drop。
>
> 修正方法是把 URL 改成 `latency=800000`。更根本的防護在 ingest 端：依頻道或講者的網路測試結果設定 ingest 的 latency 下限，因為協商取較大值，ingest 的設定可以保護所有推流者不會設得太低。另外，SRT 的文件、libsrt 的 socket 選項與 `srt-live-transmit` 都以毫秒為單位，團隊的操作手冊應該在每個範例旁邊註明單位，這是直播團隊最常見的設定錯誤之一。

> [!question]- Q6. 設計取捨：聲聲 Live 想讓一場 3,000 人的講座「所有觀眾都能即時互動」，產品經理要求全部改成 WebRTC。你會怎麼回應？
> 先釐清「即時互動」的實際需求。聊天室發問與投票，只要觀眾看到的畫面與講者相差幾秒，對話就能自然進行；LL-HLS 的 2–5 秒已經足夠。真正需要 1 秒以內的，是「上台」與講者對話的少數人，因為雙向對話時，幾秒的延遲會讓兩人不斷搶話。所以需求通常可以拆成「所有人低延遲（數秒）」加上「少數人超低延遲（1 秒內）」。
>
> 接著比較成本。3,000 人都走 WebRTC，代表 3,000 條 DTLS-SRTP 連線要由 SFU 轉送，以 2.5 Mbps 計算出口頻寬是 7.5 Gbps，必須部署多台 SFU 並做層級轉送，還要處理 TURN 的流量；LL-HLS 則是 CDN 的 HTTP 流量，edge 快取後回源量很小，成本與維運複雜度都低得多。WebRTC 在網路差時會降畫質，對大量觀眾的觀看品質反而不如 HLS 穩定。建議採混合架構：全部觀眾用 LL-HLS，上台者切到 WHEP，並用量測證明 LL-HLS 的延遲足以支援聊天室互動。

> [!question]- Q7. CDN 上的 HLS 該怎麼設定快取？LL-HLS 又多了哪些要求？
> 傳統 HLS 有三類物件。media playlist 每隔一個 target duration 就更新，快取時間必須遠短於它，常見做法是 max-age 1 秒左右或不超過 target duration 的一半，否則觀眾拿到的清單落後，延遲變大，甚至以為直播卡住。segment 的名稱唯一且內容不變，可以長期快取，並可標記 immutable。錯誤回應（尤其是 404）只能快取極短時間或不快取，否則一個「剛好還沒產生」的 segment 會讓所有觀眾在快取期間都拿不到。multivariant playlist 在直播中很少變，可以快取較久。
>
> LL-HLS 多了三個要求。第一，快取鍵必須包含 `_HLS_msn`、`_HLS_part`、`_HLS_skip` 等查詢參數，因為不同參數代表不同的清單內容。第二，CDN 要能把 blocking 請求掛著直到 origin 回應，並把同一時刻相同網址的大量請求合併成一個回源請求，否則 origin 會承受「觀眾數 × 每秒 part 數」的請求量。第三，preload hint 的 part 請求同樣會被掛著，edge 到 origin 之間的連線與逾時設定要容得下這段等待。選擇 CDN 時要確認它明確支援 LL-HLS。

> [!question]- Q8. 為什麼 SRT ingest 前面不能放一般的 L7 load balancer？要做 ingest 的擴展與備援，你會怎麼設計？
> L7 LB（例如處理 HTTP 的反向代理）理解的是 HTTP 請求，SRT 是 UDP 上的自訂協定，L7 LB 根本無法解析。即使換成 L4 LB，也要確保同一條推流的所有封包落在同一台 ingest：SRT 的連線狀態（序號、buffer、金鑰）只存在那一台機器上，封包被分到別台就會被當成不明連線丟棄。所以 L4 LB 要用五元組 hash，而且要知道 UDP 的「連線」只是 LB 自己的對應表，閒置逾時要長於 SRT keepalive 的間隔。很多團隊乾脆讓每台 ingest 有獨立的 IP，由後端在講者準備直播時分配。
>
> 備援的設計通常是「雙路推流」：講者端同時推到主、備兩台不同區域的 ingest（或使用支援 connection bonding 的 SRT 版本），下游的轉碼器以主路為準，主路中斷時自動切到備路。這比「ingest 掛了再讓講者重連」快得多，因為講者端的重連可能要好幾秒、甚至需要人工介入。此外，DNS 名稱 `live.shengsheng.example` 背後的位址變動要考慮編碼器的 DNS 快取，換 IP 前要提早降低 TTL（第 15 章）。

## 延伸閱讀

- RFC 8216〈HTTP Live Streaming〉：HLS 的規格；新版（含 LL-HLS）見 38.12 節的 2026 現況
- Haivision、SRT Alliance〈SRT Protocol Technical Overview〉與 libsrt 文件〈SRT API Socket Options〉〈SRT Access Control（Stream ID）Guidelines〉
- Adobe〈Real-Time Messaging Protocol (RTMP) Specification〉（2012）；Veovera〈Enhanced RTMP〉
- IETF WISH WG〈WebRTC-HTTP Ingestion Protocol (WHIP)〉與 WHEP 的規格文件（編號與狀態見 38.13 節的 2026 現況）
- ISO/IEC 23009-1（MPEG-DASH）與 ISO/IEC 23000-19（CMAF）；DASH-IF〈Interoperability Points〉與低延遲 DASH 指南
- Apple〈HLS Authoring Specification for Apple Devices〉：segment、GOP 與 ABR 階梯的實務建議
