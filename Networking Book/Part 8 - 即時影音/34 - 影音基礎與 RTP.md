---
chapter: 34
title: 影音基礎：Codec、延遲與 RTP
part: 8
---

# 第 34 章　影音基礎：Codec、延遲與 RTP

> [!abstract] 本章地圖
> **核心問題**：聲音和畫面怎麼變成一串 UDP 封包、在不可靠的網路上準時抵達另一端，並且播得又順又不延遲？
>
> **你會學到**：
> - 用取樣率、frame、解析度與 frame rate 算出原始 bitrate，說明 codec 為什麼能把它壓小上百倍
> - 分辨 I、P、B frame 與 GOP，解釋「掉一個封包、花屏好幾秒」與「即時通話不用 B frame」的原因
> - 說清楚 codec 與 container 的差別，認得 H.264、VP8／VP9、AV1、Opus、AAC 各自用在哪裡
> - 把一段 glass-to-glass 延遲拆成擷取、編碼、網路、jitter buffer、解碼與播放，估出每段的量級
> - 逐位元讀懂 RTP header（V、P、X、CC、M、PT、sequence、timestamp、SSRC、CSRC）與 RTCP 的 SR／RR
> - 用 Python 組出並解析 RTP 封包、在 127.0.0.1 上用 UDP 傳一串 RTP，實作 jitter buffer 並計算 RFC 3550 的 interarrival jitter
>
> **前置知識**：第 2 章（header 與 byte order、`struct`）、第 9 章（UDP 與 socket）、第 11 章（重傳與 head-of-line blocking）、第 12 章（排隊延遲）

## 34.1 故事：「老師的聲音像機器人」

週四晚上八點，日文老師美咲在日本的家裡開課，學生小安在台北的捷運上用手機的 4G 網路（對外位址 198.51.100.140）連進教室。兩邊的影音都經過聲聲 Live 位於台北區域的 SFU `sfu-tpe-1`（公網 203.0.113.60），由它把美咲的聲音與畫面轉送給小安。下課後，客服收到小安的抱怨：「老師的聲音一下一下斷掉，有時候像機器人，畫面偶爾也會停住。」同一週，類似的回報累積了四十多則，幾乎都來自用 App、走行動網路的學生。

小晴被分到這張工單。打開第 2 章那套品質回報協定的儀表板，SFU 節點每秒回報的數字看起來很健康：丟包千分比 3（也就是 0.3%）、RTT 70 ms。小晴的直覺是「頻寬不夠」，提議把視訊從 720p 降到 360p。影音工程師 Joe 看了一眼說：「降解析度救不了聲音。你看的丟包是『根本沒到』的封包；小安聽到的斷音，多半是封包**到了、但太晚到**，被播放端丟掉。上週 App 新版的『低延遲模式』把音訊的 jitter buffer 上限壓到 20 ms，晚上捷運上的 4G 抖得比這大多了。」

小晴愣住了：封包到了為什麼還要丟？jitter buffer 是什麼？為什麼儀表板上看不到「遲到」？Joe 在白板上畫了一張圖：

```text
 美咲的筆電                                     SFU 203.0.113.60（台北）            小安的手機 198.51.100.140（4G）
 ┌──────────────────────────┐                  ┌─────────────────┐               ┌────────────────────────────────┐
 │ 麥克風 → 取樣 48 kHz      │  RTP over UDP    │                 │  RTP over UDP │ jitter buffer → 解碼 → 喇叭     │
 │ → Opus 編碼（20 ms 一包） │ ═══(SRTP)══════► │ 轉送（不解碼）  │ ═════════════►│   ▲                            │
 │ 攝影機 → H.264 編碼       │                  │ ① 量 RTCP：     │  ② 4G 排隊：   │   │ ③ 上限 20 ms：             │
 └──────────────────────────┘                  │   丟包 0.3%     │   延遲忽快忽慢 │   │   晚到的封包 = 丟掉         │
                                               │   RTT 70 ms     │               │   │   → 補洞 → 機器人聲         │
                                               └─────────────────┘               └───┴────────────────────────────┘
       儀表板只看得到 ①，看不到 ② 造成的 ③
```

這張圖要從左到右讀。美咲的聲音每 20 ms 被打成一個封包，用 RTP 包好、加密後透過 UDP 送到 SFU。① SFU 依據 RTCP（RTP 的控制協定）統計丟包與 RTT，這就是儀表板的資料來源，它只知道「封包有沒有到」。② 從 SFU 到小安手機的最後一段是 4G，基地台排程與排隊讓每個封包的延遲忽快忽慢，這種「延遲的變動」叫 **jitter**（抖動）。③ 手機上的 jitter buffer 負責吸收抖動：先把封包存一下再依序播放，但它的上限只有 20 ms，比 20 ms 更晚到的封包趕不上播放時刻，只能丟掉，播放器用「猜」的補上那 20 ms 的聲音，聽起來就像機器人。

這一章從零開始講影音：聲音與畫面怎麼變成數字、codec 怎麼壓縮、延遲從哪裡來，然後逐位元拆解 RTP 與 RTCP，最後在本機重現小安那一晚：用 UDP 送一串 RTP、模擬 4G 的抖動，看不同深度的 jitter buffer 在延遲與卡頓之間怎麼取捨。讀完你會知道儀表板該補上哪些指標，以及「低延遲模式」該怎麼做才不會把聲音弄壞。

## 34.2 從聲波與畫面到數字：取樣、frame 與原始 bitrate

網路只能送 bytes，所以第一步是把連續的聲波與畫面變成數字。這一步叫**數位化**，它決定了後面所有東西的「原始份量」，也決定了 RTP timestamp 的單位。

### 聲音：取樣率、位元深度與聲道

麥克風輸出的是連續變化的電壓。**取樣**（sampling）是每隔固定時間量一次電壓，記下一個數字；每秒量幾次叫**取樣率**（sample rate）。例如 48 kHz 代表每秒 48,000 個樣本，每個樣本相隔約 20.8 微秒。每個樣本用幾個 bit 表示叫**位元深度**（bit depth），常見 16 bit；同時記錄幾路聲音叫**聲道**（channel），單聲道是 1、立體聲是 2。

```text
 電壓
  ▲        ●  ●                             取樣率 48 kHz：每 1/48000 秒量一次
  │     ●        ●                          位元深度 16 bit：每次量到的值存成 -32768～32767
  │   ●            ●                 ●      
  │──●──────────────●──────────────●───────► 時間
  │                   ●          ●          
  │                     ●  ●  ●             20 ms 的聲音 = 48000 × 0.020 = 960 個樣本
  │                                         = 一個 Opus「音訊 frame」= 一個 RTP 封包
```

圖裡每個黑點是一個樣本。取樣率要多高，由**取樣定理**（Nyquist–Shannon）決定：取樣率至少要是訊號最高頻率的兩倍，才能還原原本的波形。人耳聽得到約 20 kHz，所以音樂常用 44.1 kHz 或 48 kHz；傳統電話只保留 3.4 kHz 以下的人聲，用 8 kHz 就夠，這也是電話聲音「悶悶的」原因。圖下方的換算很重要：codec 不是一個樣本一個樣本處理，而是把一段時間的樣本打包成一個**音訊 frame**（audio frame，例如 20 ms 的 960 個樣本）一起壓縮，這也正是 RTP timestamp 每包加 960 的由來。

未壓縮的聲音叫 **PCM**（Pulse-Code Modulation，直接記錄樣本值）。它的 bitrate（每秒多少 bit）很好算：取樣率 × 位元深度 × 聲道數。48 kHz、16 bit、單聲道是 768 kbps；CD 音質（44.1 kHz、16 bit、立體聲）是 1,411.2 kbps。

### 畫面：解析度、frame rate 與色彩取樣

影片是一張張靜止的圖片快速播放。每一張叫一個 **video frame**（視訊畫格）；每秒幾張叫 **frame rate**（fps），視訊通話常用 30 fps，運動直播常用 60 fps。每張圖由像素組成，寬乘高叫**解析度**（resolution），例如 720p 是 1280×720、1080p 是 1920×1080。

每個像素要存顏色。視訊幾乎不用 RGB，而是用 **YUV**：Y 是亮度，U、V 是兩個色度分量。人眼對亮度敏感、對顏色細節遲鈍，所以可以把色度的解析度砍掉，這叫**色度取樣**（chroma subsampling）。最常見的 **4:2:0** 讓每 2×2 個像素共用一組 U、V，於是 8 bit 的畫面平均每像素只要 8＋2＝12 bit（1.5 bytes），比 RGB 的 24 bit 少一半，而且肉眼幾乎看不出差別。

把這些數字乘起來，就知道為什麼一定要壓縮：

```python
def raw_video_bps(width, height, fps, bits_per_pixel=12):
    """YUV 4:2:0、8 bit：每個像素平均 12 bit（亮度 8 bit，色度兩個分量各 1/4 解析度）。"""
    return width * height * bits_per_pixel * fps


def raw_audio_bps(rate, bits, channels):
    return rate * bits * channels


rows = [
    ("視訊 720p30", raw_video_bps(1280, 720, 30), 1_500_000),     # 一對一課的 H.264 典型值（示意）
    ("視訊 1080p30", raw_video_bps(1920, 1080, 30), 4_000_000),   # 直播講座的典型值（示意）
    ("語音 48 kHz 單聲道", raw_audio_bps(48_000, 16, 1), 32_000),  # Opus 講話
]
print(f"{'訊號':<14}{'原始 bitrate':>14}{'壓縮後':>12}{'壓縮比':>8}")
for name, raw, coded in rows:
    print(f"{name:<14}{raw / 1e6:>10.1f} Mbps{coded / 1e6:>8.3f} Mbps{raw / coded:>7.0f}x")

# 每個 20 ms 的 Opus 封包：80 bytes 音訊 + 12 RTP + 8 UDP + 20 IPv4
payload = 32_000 * 0.020 / 8
on_ip = payload + 12 + 8 + 20
print(f"\nOpus 20 ms：payload {payload:.0f} bytes，IP 封包 {on_ip:.0f} bytes，"
      f"每秒 {1 / 0.020:.0f} 包 → IP 層 {on_ip * 8 * 50 / 1000:.0f} kbps")
frame_bits = 1_500_000 / 30
print(f"720p30 @1.5 Mbps：平均每個 frame {frame_bits / 8 / 1000:.1f} KB，"
      f"每像素 {1_500_000 / (1280 * 720 * 30):.3f} bit，約每秒 {1_500_000 / 8 / 1200:.0f} 個 1200-byte 封包")
assert raw_video_bps(1280, 720, 30) == 331_776_000 and on_ip == 120
```

```text
訊號                原始 bitrate         壓縮後     壓縮比
視訊 720p30          331.8 Mbps   1.500 Mbps    221x
視訊 1080p30         746.5 Mbps   4.000 Mbps    187x
語音 48 kHz 單聲道        0.8 Mbps   0.032 Mbps     24x

Opus 20 ms：payload 80 bytes，IP 封包 120 bytes，每秒 50 包 → IP 層 48 kbps
720p30 @1.5 Mbps：平均每個 frame 6.2 KB，每像素 0.054 bit，約每秒 156 個 1200-byte 封包
```

第一個表格說明壓縮的必要：720p30 的原始畫面是 331.8 Mbps，美咲家 20 Mbps 的上傳線路連一路都送不了；壓縮到 1.5 Mbps 是兩百多倍。聲音的壓縮比只有 24 倍，因為聲音本來就小。第二段把「封包的開銷」算出來：Opus 每 20 ms 只產生 80 bytes 的音訊，加上 RTP、UDP、IPv4 header 共 40 bytes，IP 層的 bitrate 從 32 kbps 變成 48 kbps，header 佔了三分之一，這就是語音封包不能切得太碎的原因（第 2 章的動手練習算過同一件事）。最後一行的「每像素 0.054 bit」很驚人：平均每 20 個像素才分到 1 個 bit，codec 能做到這件事，靠的是下一節的預測。

## 34.3 壓縮的原理：I、P、B frame 與 GOP

### 兩種多餘：空間與時間

影片裡有大量重複的資訊。**空間上的多餘**：同一張畫面中，美咲背後的白牆幾百個像素幾乎一樣。**時間上的多餘**：相鄰兩張畫面之間，牆、書櫃、桌子都沒動，只有嘴和手在動。現代視訊 codec（**codec** 是 coder-decoder 的縮寫，指「把原始訊號壓縮成 bitstream、再解回來」的演算法與格式）就是同時利用這兩種多餘。

壓縮的流程大致是：把畫面切成區塊（H.264 叫 macroblock，16×16 像素；新的 codec 用可變大小的區塊）；每個區塊先**預測**，可以用同一張畫面裡已經編好的鄰居預測（intra prediction），也可以到前一張畫面找一塊長得最像的區域，記下它的位移，這個位移叫**運動向量**（motion vector）；預測和實際內容的差叫**殘差**（residual），把殘差做頻率轉換後**量化**（quantization，把精細的數值四捨五入成粗一點的等級，這是唯一真正丟資訊的步驟，也是 bitrate 的主要調整旋鈕）；最後用熵編碼把結果壓成最短的 bit。解碼端反著做，用同樣的預測加上殘差把畫面重建出來。

### 三種 frame

依照「可以參考誰」，壓縮後的畫面分成三種：

| frame 類型 | 參考對象 | 相對大小 | 能不能單獨解碼 | 用途 |
|---|---|---|---|---|
| **I frame**（intra） | 不參考其他 frame，只用自己畫面內的預測 | 最大，常是 P frame 的數倍到十倍以上 | 可以 | 開頭、切換場景、新觀眾加入、錯誤後的恢復點 |
| **P frame**（predicted） | 參考之前已解碼的 frame | 中 | 不行，參考的 frame 必須先到 | 一般的連續畫面 |
| **B frame**（bi-directional） | 同時參考之前與**之後**的 frame | 最小 | 不行，而且要等「之後」的 frame 先到 | 隨選影片、直播的轉碼輸出 |

可以單獨解碼、讓解碼器從這裡開始的 I frame 也叫 **keyframe**（關鍵畫格）。H.264 裡最嚴格的 keyframe 叫 IDR frame：它之後的 frame 不能參考它之前的任何 frame，所以解碼器可以把舊的參考畫面全部清掉，從這裡重新開始。

### GOP 與「解碼順序 ≠ 播放順序」

從一個 keyframe 到下一個 keyframe 之前的這一組 frame，叫 **GOP**（Group of Pictures）。GOP 的長度通常用 frame 數或秒數表示，例如 30 fps 下 GOP 為 60 代表每 2 秒一個 keyframe。B frame 會讓情況變複雜，因為它要參考「之後」的畫面：

```text
 播放順序（顯示時間）： I0   B1   B2   P3   B4   B5   P6   ...  I60
                        │    │    │    ▲    │    │    ▲
                        │    └────┴────┤    └────┴────┤      B 同時參考前後兩張
                        └──────────────┘──────────────┘      P 只參考前一張 I／P
 解碼順序（傳送順序）： I0   P3   B1   B2   P6   B4   B5   ...
                        ◄─────────── 一個 GOP（例如 60 frame = 2 秒）──────────►

 即時通話的設定：      I0   P1   P2   P3   P4   P5   P6   ...  （沒有 B，順序一致）
```

上半部是有 B frame 的 GOP。B1、B2 要參考 I0 與 P3，所以編碼器必須先等 P3 拍完、編完，才能編 B1，傳送與解碼也必須先送 P3 再送 B1、B2。這帶來兩個後果。第一，**多出至少一到數個 frame 的延遲**：30 fps 下每多一張重排就多 33 ms，編碼端和解碼端各自都要等。第二，送出的順序和顯示的順序不同，所以 container 要分別記錄 **DTS**（Decoding Time Stamp，什麼時候解）與 **PTS**（Presentation Time Stamp，什麼時候顯示）。

下半部是即時通話的設定：不用 B frame，每張 P frame 只參考前一張，編好就能送、到了就能播。這就是 WebRTC 的編碼器通常不開 B frame 的原因：省下的 bitrate 不值得多出來的延遲。相反地，隨選影片與 HLS 直播的轉碼輸出常開 B frame，因為觀眾本來就落後好幾秒，多 100 ms 無所謂，省下的 bitrate 卻很實在。

### 為什麼掉一個封包會花屏好幾秒

P frame 參考前一張，前一張又參考更前一張，形成一條**參考鏈**。只要鏈上任何一張 frame 的任何一個封包遺失，解碼器重建出來的畫面就有一塊是錯的，而且錯誤會被後面每一張 P frame 沿用、隨運動向量擴散，直到下一個 keyframe 才完全清乾淨。這就是看視訊時偶爾出現綠塊、馬賽克拖影的原因。

GOP 長度因此是一個取捨：keyframe 越密，錯誤恢復越快、新觀眾越快看到畫面、HLS 越容易在 keyframe 上切 segment（第 38 章），但 I frame 很大，bitrate 和瞬間的封包突發都會增加。即時通話的做法是 keyframe 不固定週期，而是「需要時才要」：接收端發現畫面壞了，就用 RTCP 送 **PLI**（Picture Loss Indication）請送出端立刻產生一個 keyframe；遺失的封包如果還來得及，就先用 **NACK** 要求重送（兩者都在第 37 章詳談）。直播則通常固定 1 到 2 秒一個 keyframe，讓每個 segment 都能獨立開始播放。

> [!warning] 常見誤解
> 「畫質差就是 bitrate 不夠」只說對一半。同樣 1.5 Mbps，畫面靜止的講課和鏡頭晃動的戶外直播，畫質差很多，因為後者時間上的多餘少、殘差大。另外，I frame 的突發可能比平均 bitrate 高好幾倍，在上傳頻寬只剩一點餘裕的線路上，每次 keyframe 都可能造成短暫排隊與 jitter。

## 34.4 Codec 家族：H.264、VP8／VP9、AV1、Opus、AAC

codec 的壓縮效率、運算成本、授權與硬體支援各不相同，選擇 codec 往往不是「哪個最好」，而是「兩端都支援哪個、裝置有沒有硬體加速」。下表整理本書會遇到的 codec：

| codec | 種類 | 誰定義 | 授權特性 | 特點 | 聲聲 Live 用在哪 |
|---|---|---|---|---|---|
| H.264／AVC | 視訊 | ITU-T 與 ISO／IEC 共同制定（2003） | 需專利授權（多數瀏覽器與 OS 已內建） | 硬體編解碼最普及，相容性最好 | WebRTC 備選、直播 ingest 與 HLS |
| H.265／HEVC | 視訊 | ITU-T 與 ISO／IEC（2013） | 授權較複雜 | 相同畫質下 bitrate 明顯低於 H.264（依內容而定） | 部分直播編碼器輸出 |
| VP8 | 視訊 | Google 開放（2010） | 免授權金 | 與 H.264 同一世代 | WebRTC 預設之一 |
| VP9 | 視訊 | Google 開放（2013） | 免授權金 | 比 VP8 有效率，支援 SVC（可分層的編碼） | WebRTC 小班課（第 37 章） |
| AV1 | 視訊 | AOMedia（2018） | 以免授權金為目標 | 壓縮效率高，軟體編碼耗運算 | 錄影回放、新裝置 |
| Opus | 音訊 | IETF（RFC 6716，2012） | 免授權金 | 6～510 kbps，frame 2.5～60 ms，語音與音樂通吃，低延遲 | 所有 WebRTC 音訊 |
| AAC | 音訊 | MPEG | 需專利授權 | 每個 frame 1024 個樣本，延遲較高，播放端相容性好 | 直播與 HLS 的音訊 |
| G.711 | 音訊 | ITU-T | 免授權金（年代久遠） | 8 kHz、64 kbps、幾乎不壓縮 | 和電話網路互通 |

幾個細節值得補充。**H.264 的 profile 與 level**：profile 決定能用哪些壓縮工具，例如 Constrained Baseline（不用 B frame，適合即時通話）、Main、High；level 決定解析度與 bitrate 的上限，例如 3.1 大約到 720p30。SDP 裡常見的 `profile-level-id=42e01f`，`42` 是 Baseline、`e0` 是限制旗標（合起來是 Constrained Baseline）、`1f` 是十進位 31，即 level 3.1；第 35 章會用到。

**Opus 的延遲**：Opus 在 20 ms frame 下的演算法延遲（編碼器需要先看到多少未來的樣本）約 26.5 ms，選更短的 frame 可以降到 5 ms 左右，但 header 開銷變大。Opus 還內建兩個對網路很重要的功能：**PLC**（Packet Loss Concealment，封包遺失時用前後的聲音推估出一段），以及 **in-band FEC**（在下一個封包裡夾帶上一個封包的低品質備份）。**AAC** 一個 frame 1024 個樣本，48 kHz 下約 21.3 ms，演算法延遲比 Opus 高得多，所以適合直播與檔案，不適合對話。

> [!note] 2026 現況
> 截至 2026 年 10 月（依 caniuse 查證）：`<video>` 播放 AV1，Chrome 70+、Firefox 67+、Edge 121+ 支援，Safari 17.0+ 為部分支援，需要 AV1 硬體解碼的裝置。HEVC 在 Safari 13+、iOS 11+ 完整支援；Chrome 107+、Edge、Firefox 137+ 為部分支援，依賴硬體或作業系統的解碼器。「部分支援」的意思是同一個瀏覽器版本在不同裝置上結果不同，所以一定要在 runtime 偵測：播放用 `MediaCapabilities.decodingInfo()` 或 `MediaSource.isTypeSupported()`，WebRTC 用 `RTCRtpSender.getCapabilities('video')` 列出實際可用的 codec。
>
> WebRTC 的 codec 支援和 `<video>` 播放是兩回事。規格面穩定的部分是：瀏覽器必須同時支援 VP8 與 H.264 Constrained Baseline 視訊，以及 Opus 與 G.711 音訊。VP9 與 AV1 在主流瀏覽器的 WebRTC 中已相當普遍，H.265 用於 WebRTC 也有進展，但各瀏覽器的細節本書未逐一查證，部署前請以 `getCapabilities` 在目標裝置上實測。

## 34.5 Codec、container 與 payload format

小晴在錄影系統的 log 裡看過 `lesson-0815.mp4`、`.webm`、`.ts`，一直以為它們是三種「影片格式」。其實副檔名說的是 **container**（容器格式），裡面裝的壓縮資料才是 codec 的產物。兩者的分工是：

- **codec** 決定「一張畫面、一段聲音怎麼壓縮」，產出的是一連串壓縮後的 frame（bitstream）。
- **container** 決定「怎麼把多條 bitstream（視訊、音訊、字幕）和時間資訊一起裝進一個檔案或串流」：每個 frame 的 PTS／DTS、哪些是 keyframe、codec 的初始化參數、怎麼快速跳到第 10 分鐘。

```text
 codec 層      H.264 bitstream：[SPS][PPS][IDR][P][P][P]...      Opus bitstream：[20ms][20ms][20ms]...
                      │                                                 │
          ┌───────────┼──────────────────────────┬──────────────────────┼─────────────┐
          ▼           ▼                          ▼                      ▼             ▼
 封裝層   MP4／fMP4（檔案、HLS／DASH segment）   MPEG-TS（廣播、SRT、傳統 HLS）   RTP payload format
          box：moov、moof、mdat                   188-byte 封包＋PID              RFC 6184（H.264）、RFC 7587（Opus）
          時間：timescale、PTS／DTS               時間：90 kHz PTS／DTS          時間：RTP timestamp
          │                                       │                               │
 傳輸層   HTTP（TCP／QUIC）                        UDP（SRT 在其上做重傳）          UDP（WebRTC 用 SRTP 加密）
```

由上往下讀。同一段 H.264 bitstream 可以被裝進不同的封裝：存成檔案或 HLS／DASH 的 segment 時用 MP4（更精確地說是 ISO Base Media File Format，切成小段的版本叫 fragmented MP4，fMP4）；廣播電視與 SRT 直播常用 **MPEG-TS**，它把資料切成固定 188 bytes 的小封包，適合在可能遺失的線路上傳；即時通話則不用 container，而是由 **RTP payload format** 規定怎麼把 frame 切進 RTP 封包。RTP payload format 扮演的角色和 container 類似，都是「把 codec 的輸出包起來、附上時間」，但它是為封包網路設計的：每個封包都要能被獨立辨認，而且掉了一個也不能讓整條串流解不開。

| 封裝 | 常裝的 codec | 用在哪 | 一個常見的坑 |
|---|---|---|---|
| MP4／fMP4 | H.264、HEVC、AV1；AAC、Opus | 檔案下載、HLS 與 DASH 的 CMAF segment | `moov` 放在檔尾時，邊下載邊播放要先拿到檔尾（需要 faststart 處理） |
| MPEG-TS | H.264、HEVC；AAC | 廣播、SRT 傳輸、傳統 HLS | 每個 188-byte 封包都有 header，開銷比 fMP4 高 |
| WebM（Matroska 的子集） | VP8、VP9、AV1；Opus、Vorbis | 瀏覽器的 `MediaRecorder` 錄影輸出常見 | 不是所有播放器都支援，尤其是部分行動裝置 |
| FLV | H.264；AAC | RTMP 推流（第 38 章） | 傳統 FLV 只定義少數 codec，新 codec 要靠 Enhanced RTMP |
| RTP payload format | 幾乎所有即時 codec | WebRTC、VoIP、SFU | 每種 codec 有自己的切包規則，不能直接把檔案裡的 bytes 塞進 RTP |

表格最後一欄的坑，最典型的例子就是 H.264 的兩種寫法。H.264 的 bitstream 由一個個 **NAL unit**（Network Abstraction Layer unit）組成，SPS、PPS 是解碼需要的參數，IDR 與一般 slice 是畫面資料。MPEG-TS 和原始的 `.h264` 檔用 **Annex B** 格式：每個 NAL unit 前面放起始碼 `00 00 00 01` 當分隔。MP4 則用 **AVCC** 格式：每個 NAL unit 前面放 4 bytes 的長度，SPS 與 PPS 存在檔頭的 `avcC` box，而不在 bitstream 裡。RTP（RFC 6184）兩種都不用：一個 NAL unit 小就整個放進一個封包，太大就用 FU-A 切成好幾個 fragment，好幾個小的（例如 SPS＋PPS）也可以用 STAP-A 合併。自己寫轉封裝程式時，最常見的 bug 就是把 AVCC 的長度前綴當成資料送出去，或忘了在 keyframe 前補上 SPS／PPS，結果接收端永遠解不出第一張畫面。

> [!tip] 用 codec string 說清楚你要什麼
> 瀏覽器 API 與 HLS playlist 用 codec string 精確描述 codec 與 profile，例如 `avc1.42e01f`（H.264 Constrained Baseline level 3.1）、`vp09.00.10.08`（VP9 profile 0、level 1.0、8 bit）、`opus`。和前端討論相容性時，說「這支 MP4 是 `avc1.640028`＋`mp4a.40.2`」，比說「這是 MP4」精確得多：後者只描述了 container。

## 34.6 Bitrate、解析度與 frame rate 的取捨

**Bitrate** 是每秒用多少 bit 表示這段媒體，它直接等於網路要提供的頻寬。解析度和 frame rate 決定「要描述多少像素」，bitrate 決定「每個像素能分到多少 bit」。三者之間的取捨可以用一句話概括：**頻寬固定時，解析度與 frame rate 越高，每個像素分到的 bit 越少，量化越粗，畫面越糊。**

所以「720p」本身不代表畫質。720p 在 300 kbps 下可能比 360p 在同一個 bitrate 下還糊，因為編碼器被迫把細節全部量化掉。WebRTC 的編碼器會依頻寬估計（第 37 章）動態調整：頻寬下降時先降 bitrate，降到一定程度就自動降解析度或 frame rate，讓每個像素保有足夠的 bit。下表是 H.264 在常見解析度下的經驗範圍，只是示意，實際值依 codec、內容複雜度與編碼器設定差異很大：

| 解析度與 frame rate | 視訊通話（示意） | 直播輸出（示意） | 說明 |
|---|---|---|---|
| 360p30（640×360） | 300～600 kbps | 600 kbps～1 Mbps | 手機小視窗、網路差時的退路 |
| 720p30（1280×720） | 1～2 Mbps | 2～4 Mbps | 一對一課的主力 |
| 1080p30（1920×1080） | 2.5～4 Mbps | 4～6 Mbps | 講座直播、分享螢幕 |
| 語音（Opus） | 16～40 kbps | 64～128 kbps（AAC 或 Opus 立體聲） | 語音遠比視訊省 |

編碼器怎麼控制 bitrate 也有兩大類。**CBR**（Constant Bitrate）盡量讓每秒的輸出固定，網路好規劃，但複雜畫面會糊；**VBR**（Variable Bitrate）讓複雜畫面多用一點、簡單畫面少用一點，品質較平均，但瞬間 bitrate 起伏大。即時通話通常用「有上限的 VBR」並由頻寬估計即時調整目標值；直播 ingest 常要求接近 CBR，避免突發撐爆上傳線路。

回到故事，小晴想把 720p 降到 360p，能省下約 1 Mbps，但小安的問題是**延遲變動**而不是頻寬不足。分辨兩者要看症狀：頻寬不足時，排隊延遲持續上升、接著大量丟包，WebRTC 會主動降 bitrate 與解析度；jitter 大但頻寬夠時，平均延遲與丟包都還好，只是延遲分布有長尾，必須靠 jitter buffer 處理。

## 34.7 延遲從哪裡來：glass-to-glass 的延遲預算

對即時對話來說，最重要的延遲是**單向延遲**：從美咲開口，到小安聽見。視訊的對應說法是 **glass-to-glass latency**，從攝影機的鏡頭玻璃到觀眾螢幕玻璃。這段時間不是只有「網路延遲」，而是一條很長的管線，每一段都在加：

```text
 0 ms            美咲開口                                                         小安聽到  ≈ 120 ms ＋ d
 │ 擷取 10 │前處理 10│ 編碼 27 │打包 1│ 上行 20 │SFU 2│ SFU→台北 4G 35~ │ jitter buffer d │解碼 2│ 播放 15 │
 │◄──────►│◄──────►│◄───────►│◄───►│◄──────►│◄───►│◄──────────────►│◄──────────────►│◄────►│◄──────►│
  音訊驅動   回音消除   Opus 20 ms     RTP    美咲家→    轉送    傳播＋4G 排隊     等晚到的封包      PLC／    音效卡
  的緩衝     降噪      frame＋        加密   台北                 （會抖動）        （本章主角）      解碼     輸出緩衝
                       lookahead
```

這是音訊的延遲預算，數字是示意，用來看量級。從左往右：**擷取**，作業系統的音訊驅動每次交給程式一小段樣本（例如 10 ms），這段要先湊滿；**前處理**，回音消除（AEC）、降噪、自動增益都需要一點緩衝；**編碼**，Opus 要湊滿 20 ms 的 frame 再加上 lookahead，約 26.5 ms；**打包與加密**，RTP 加 SRTP 幾乎不花時間；**網路**分成美咲家（日本）到台北 SFU、SFU 轉送、SFU 到小安的 4G 三段，第一段約是美咲到 SFU 基本 RTT 40 ms 的一半，其中只有最後一段明顯抖動；**jitter buffer**，接收端刻意多等一段時間 d；**解碼**，Opus 解碼很快，遺失時 PLC 也在這一步；**播放**，音效卡的輸出緩衝。

把固定的部分加起來大約 120 ms，再加上 jitter buffer 的 d。這是一個重要的觀察：**在一條路徑已經固定的通話裡，jitter buffer 是延遲預算中唯一能大幅調整的一段**，也是唯一刻意加進去的延遲。所以「低延遲模式」第一個想動的就是它，而它也是最容易被調壞的。視訊的預算類似，但擷取一張畫面最多要等一個 frame 間隔（30 fps 是 33 ms），編碼與解碼較久，大的 I frame 還要切成很多封包，由 **pacer**（平滑發送器）分散送出以免瞬間塞爆路徑，最後還要等螢幕的刷新（60 Hz 每 16.7 ms 一次）。

延遲多少才算夠低？ITU-T G.114 是電話網路規劃常引用的建議：單向延遲在 150 ms 以內，絕大多數對話都不受影響；超過 400 ms 一般就不適合互動對話。超過 250 ms 左右，雙方就會開始搶話、尷尬地停頓。不同的影音服務落在完全不同的量級：

| 服務型態 | 典型單向延遲（示意） | 延遲主要花在哪 | 本書章節 |
|---|---|---|---|
| WebRTC 一對一、小班課 | 100～400 ms | 編碼、網路、jitter buffer | 第 34～37 章 |
| SRT 推流（講者到 ingest） | 約 0.1 秒到數秒 | SRT 的 latency 視窗（重傳緩衝） | 第 38 章 |
| LL-HLS、WHEP 觀看 | WHEP 低於 1 秒；LL-HLS 通常數秒 | partial segment 的長度、播放器緩衝 | 第 38 章 |
| 傳統 HLS／DASH | 十秒到數十秒 | segment 長度 × 播放器預先緩衝的 segment 數 | 第 38 章 |

聲音和畫面是兩條獨立的 RTP 串流，各自經歷不同的延遲，接收端還要讓它們同步，這叫 **lip sync**（唇音同步）。人對不同步的容忍度不對稱：聲音比畫面早到很容易被察覺，晚到則寬容一些（ITU-R BT.1359 常被引用的可察覺門檻約是聲音超前 45 ms、落後 125 ms）。接收端靠 RTCP 的 SR 把兩條串流對齊到同一個牆上時鐘，34.9 節會算一次。

## 34.8 RTP：在 UDP 上搬運媒體

### 為什麼不用 TCP

第 11 章講過，TCP 保證依序、不遺失：一個 segment 遺失，後面所有已經到達的資料都要在核心裡等它重傳成功，才能交給應用程式，這叫 **head-of-line blocking**。對檔案下載這很合理，但對即時語音是災難：遺失一個 20 ms 的封包，重傳至少要再等一個 RTT 加上偵測遺失的時間，這段期間後面的聲音全部卡住；等重傳到了，它的播放時刻早就過了，結果是「本來只會補洞 20 ms，變成停住好幾百毫秒再一口氣播出來」。

即時媒體需要的語意剛好相反：**晚到的資料沒有用，寧可跳過也不要等**。所以它跑在 UDP 上（第 9 章），由應用程式自己決定哪些要補救：聲音用 PLC 或 FEC 補，視訊的參考 frame 若時間還夠就用 NACK 要求重送，不夠就請送出端產生新的 keyframe。但 UDP 只給你「一個個獨立的 datagram」，接收端想做這些事，至少需要知道四件事：這個封包是第幾個（偵測遺失與亂序）、它屬於媒體時間的哪一刻（決定什麼時候播）、它是哪個 codec（怎麼解）、它來自哪一條串流（同一個 port 上可能有好幾路）。**RTP**（Real-time Transport Protocol，RFC 3550）就是把這四件事標準化的那層 header。

RTP 刻意只定義「標記」，不定義行為：它不重傳、不保證送達、不做擁塞控制，也不保證順序。這些都交給應用程式依 codec 與情境決定。它的搭檔 **RTCP**（RTP Control Protocol）則負責回報統計，讓兩端知道路徑的狀況。

### RTP header 的位元布局

RTP 固定 header 是 12 bytes，後面可以接 0 到 15 個 CSRC，以及可選的 header extension：

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
 │  若 X=1：profile (16)，例 0xBEDE│  length (16，單位 32-bit word) │
 ├───────────────────────────────┴───────────────────────────────┤
 │          header extension 資料（例如音量、傳輸序號、mid）     │
 ├───────────────────────────────────────────────────────────────┤
 │          payload（codec 資料，依 payload format 切好）        │
 │                              ……若 P=1，結尾有 padding，最後一個 byte 是 padding 長度 │
 └───────────────────────────────────────────────────────────────┘
```

逐欄解說，第一個 byte 擠了四個欄位。**V**（version）2 bit，永遠是 2；在同一個 port 上同時跑 STUN、DTLS 與 RTP 時（第 36 章），接收端就是靠第一個 byte 的範圍把它們分開的。**P**（padding）表示結尾有補齊用的 bytes，最後一個 byte 記錄補了幾個，加密演算法需要固定區塊長度、或想隱藏封包大小時會用到。**X**（extension）表示固定 header 和 CSRC 後面接著一段 header extension。**CC**（CSRC count）4 bit，表示後面有幾個 CSRC。

第二個 byte 是 **M**（marker）與 **PT**（payload type）。M 的意義由 payload format 決定：視訊通常標在**一個 frame 的最後一個封包**，告訴接收端「這張畫面的封包到齊了，可以開始解碼」；音訊則標在**一段靜音之後的第一個封包**（talkspurt 的開頭），提示接收端可以趁機調整 jitter buffer 的深度。PT 7 bit，表示 payload 是哪種格式：0～95 有一部分是 RFC 3551 指定的固定值（例如 0 是 PCMU、8 是 PCMA），96～127 是**動態**的，由 SDP 的 `a=rtpmap` 臨時指定，例如 `a=rtpmap:111 opus/48000/2`（第 35 章）。所以光看 PT 111 不能斷定是 Opus，要看這次通話協商的結果。

**Sequence Number** 16 bit，每送一個 RTP 封包加 1，用來偵測遺失與亂序。它只有 65,536 種值，一路視訊每秒 150 個封包，七分多鐘就繞一圈，所以接收端要維護「繞了幾圈」，組成**延伸序號**（extended sequence number，圈數 × 65536 ＋ 序號）。初始值應該是隨機的，讓加密後的串流更難被已知明文分析。

**Timestamp** 32 bit，表示這個封包第一個樣本的**媒體取樣時刻**，單位是 codec 的**時鐘頻率**（clock rate），不是毫秒。音訊通常等於取樣率，Opus 規定一律用 48 kHz（即使實際取樣率較低）；視訊一律用 90 kHz，這個數字能被 24、25、30、50、60 整除，各種 frame rate 都能用整數表示。於是 Opus 20 ms 一包時 timestamp 每包加 960，30 fps 的視訊每個 frame 加 3000。同一個 frame 切成好幾個封包時，這些封包的 timestamp **完全相同**，sequence 則逐一遞增。timestamp 的初始值也是隨機的，它和牆上時間沒有直接關係，要靠 RTCP SR 才能換算。

**SSRC** 32 bit，是這條串流的隨機識別碼。同一個 RTP session 裡，每一路媒體（美咲的麥克風、美咲的攝影機）都有自己的 SSRC；接收端靠它分辨封包屬於哪一路，RTCP 回報也用它指名。兩個來源剛好選到同一個 SSRC 的機率很低，但規格仍定義了衝突偵測：發現衝突的一方要換一個新的。**CSRC** 只有在 **mixer**（混音器，把多路聲音混成一路的設備，例如 MCU）出現時才會用到：混出來的封包 SSRC 是 mixer 自己，CSRC list 列出「這包聲音是哪些人的混合」，讓接收端仍能顯示誰在講話。SFU 只轉送不混音，所以通常不用 CSRC。

| 欄位 | 位元數 | 每個封包怎麼變 | 接收端用它做什麼 |
|---|---|---|---|
| V | 2 | 固定 2 | 和同 port 上的 STUN、DTLS 分流 |
| P、X、CC | 1、1、4 | 依需要 | 找出 payload 從哪裡開始、到哪裡結束 |
| M | 1 | 視訊：frame 的最後一包；音訊：靜音後第一包 | 判斷 frame 到齊、調整 jitter buffer |
| PT | 7 | 同一串流通常固定 | 依 SDP 對應到 codec，選解碼器 |
| Sequence | 16 | 每包加 1，會回繞 | 偵測遺失、亂序、重複；排序 |
| Timestamp | 32 | 依媒體時間前進，同一 frame 相同 | 決定播放時刻、計算 jitter、唇音同步 |
| SSRC | 32 | 同一串流固定 | 分辨串流、對應 RTCP 回報 |
| CSRC | 0～15 × 32 | mixer 才填 | 顯示混音裡有哪些講者 |

### Header extension 與加密

固定 header 很早就定案了，WebRTC 需要的新資訊都塞在 **header extension** 裡。RFC 8285 定義了通用的寫法：profile 欄位填 `0xBEDE` 表示「one-byte header」格式，後面每個元素是 1 byte（4 bit 的 id ＋ 4 bit 的長度減一）加上資料。id 對應什麼由 SDP 的 `a=extmap` 協商（第 35 章），常見的有音量等級（讓 SFU 不解碼就知道誰在講話）、傳輸層序號（給 TWCC 頻寬估計用，第 37 章）、`mid`（BUNDLE 時分辨這個封包屬於哪個 media section，第 35 章）。

WebRTC 的媒體一律用 **SRTP**（Secure RTP）加密：payload 被加密，整個封包（含 header）被認證，但 RTP header **本身不加密**，因為網路中的 SFU 與接收端需要先讀 SSRC 和序號，才知道該用哪把金鑰解密、怎麼防重放。這對除錯很有用：即使抓到的是加密後的 WebRTC 流量，Wireshark 仍能分析序號與 timestamp，算出遺失與 jitter。代價是 SRTP 在每個封包尾端加上認證標籤（大小依加密套件而定，常見 10 或 16 bytes），語音封包的開銷又多了一點。

### 一個 frame 怎麼變成一串封包

把上面的欄位放在一起，看美咲的攝影機送出兩張畫面時，封包長什麼樣：

```text
 frame #1（I frame，6200 bytes）                         frame #2（P frame，1500 bytes）
 ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────┐   ┌──────────┬──────┐
 │ seq 65533│ seq 65534│ seq 65535│ seq 0    │ seq 1    │seq 2 │   │ seq 3    │seq 4 │
 │ ts T     │ ts T     │ ts T     │ ts T     │ ts T     │ts T  │   │ ts T+3000│ts T+3000
 │ M=0 1200B│ M=0 1200B│ M=0 1200B│ M=0 1200B│ M=0 1200B│M=1   │   │ M=0 1200B│M=1   │
 └──────────┴──────────┴──────────┴──────────┴──────────┴200B──┘   └──────────┴300B──┘
       sequence 每包 +1（65535 之後回繞成 0）                         timestamp 每個 frame +3000（90 kHz ÷ 30 fps）
```

I frame 有 6200 bytes，超過單一封包的安全大小（本書用 1200 bytes，第 8、9 章），所以被切成 6 個封包，序號 65533 到 2，中間繞回 0；它們的 timestamp 全部是 T，只有最後一個 M=1。接收端的視訊 jitter buffer 收集「timestamp 相同、序號連續、直到 M=1」的封包，才把一整個 frame 交給解碼器。下一張 P frame 的 timestamp 是 T＋3000，代表它在媒體時間上晚 1/30 秒。注意 timestamp 跟封包數無關：一張 frame 切成幾包都一樣，這和音訊「一包就是一個 frame」不同。34.11 節的實驗一會用程式產生這張圖的每一個封包。

## 34.9 RTCP：回報接收品質、對齊時鐘

RTP 只負責搬運，送出端完全不知道對方收得怎麼樣。**RTCP** 讓參與者定期互相報告：送出端報告「我送了多少、我的媒體時鐘對應到哪個牆上時間」，接收端報告「我收到多少、丟了多少、抖動多大」。傳統上 RTCP 用 RTP port ＋ 1，WebRTC 則用 **rtcp-mux** 讓兩者共用同一個 port（第 35 章）。

### RTCP 封包種類

| PT | 名稱 | 誰送 | 內容與用途 |
|---|---|---|---|
| 200 | SR（Sender Report） | 有在送媒體的參與者 | NTP 與 RTP timestamp 的對應、送出的封包數與 bytes；也可附帶 report block |
| 201 | RR（Receiver Report） | 只收不送的參與者 | 每個來源一個 report block：遺失、延伸序號、jitter、LSR／DLSR |
| 202 | SDES（Source Description） | 所有參與者 | 最重要的是 CNAME：同一個參與者的音訊與視訊 SSRC 共用一個 CNAME，接收端才知道要對齊誰 |
| 203 | BYE | 要離開的來源 | 「這個 SSRC 不再送了」 |
| 205、206 | RTPFB、PSFB（回饋訊息） | 接收端 | NACK、TWCC、PLI、FIR 等即時回饋（第 37 章） |

RTCP 封包和 RTP 一樣以 V=2 開頭，第二個 byte 是 PT。如果 RTP 和 RTCP 共用一個 port，接收端就看第二個 byte：200～206 是 RTCP；而 RTP 的第二個 byte 是 M 加上 PT，只要 RTP 不使用 64～95 的 payload type，兩者的值域就不會重疊（M=1 時 PT 72～76 會撞上 200～204），這就是 rtcp-mux 下 RTP 不能用 64～95 這段 PT 的原因。規格還要求 RTCP 通常以**複合封包**（compound packet）送出，例如 SR 或 RR 後面緊跟 SDES；RTCP 佔用的頻寬建議不超過 session 頻寬的 5%，間隔還會隨機化，避免所有參與者同時送。WebRTC 使用支援即時回饋的 profile（AVPF），NACK、PLI 等回饋可以不等例行的間隔立刻送出。

### SR 與 report block 的位元布局

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───┬─┬─────────┬───────────────┬───────────────────────────────┐
 │V=2│P│ RC (5)  │  PT=200 (SR)  │     length（32-bit word 數 - 1）│  header
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
 │       interarrival jitter (32，單位：timestamp tick)           │
 │       last SR timestamp：LSR (32，NTP 的中間 32 bit)           │
 │       delay since last SR：DLSR (32，單位 1/65536 秒)          │
 └───────────────────────────────────────────────────────────────┘
```

上半部是 SR 特有的 **sender info**。NTP timestamp 是 64 bit 的牆上時間（從 1900 年起算的秒數加上小數），緊接的 RTP timestamp 是**同一瞬間**的媒體時鐘讀數，這一對數字就是「媒體時間 ↔ 牆上時間」的對照點。packet count 與 octet count 讓接收端估計送出端的實際 bitrate。

下半部是 **report block**，RR 只有 header 加上這些 block（RC 欄位記錄有幾個）。**fraction lost** 是「上次報告以來」遺失的比例，以 8 bit 定點數表示（遺失數 ÷ 預期數 × 256）；**cumulative lost** 是從頭累計的遺失數，24 bit 有號數，因為重複的封包會被算進「收到」，累計值可能變成負的。**extended highest sequence number** 是延伸序號：高 16 bit 是繞了幾圈，低 16 bit 是目前最大的序號。**interarrival jitter** 是下面要講的抖動估計值。**LSR** 與 **DLSR** 用來算 RTT。

### Interarrival jitter：RFC 3550 的公式

jitter 是「延遲的變動」。但接收端不知道封包真正的單向延遲，因為兩端時鐘沒有同步，RTP timestamp 也只是媒體時間。RFC 3550 的巧妙之處是只看**差值**：設封包 i 的 RTP timestamp 是 Sᵢ、抵達時間（換成同樣的 tick 單位）是 Rᵢ，則**相對傳輸時間** Rᵢ − Sᵢ 包含一個未知的常數（兩邊時鐘的差），但兩個封包的相對傳輸時間相減，常數就消掉了：

```text
 D(i, j) = (Rj − Ri) − (Sj − Si) = (Rj − Sj) − (Ri − Si)     ← 兩個封包「傳輸時間」的差
 J ← J + ( |D(i−1, i)| − J ) / 16                             ← 每收到一個封包更新一次

 手算：Opus 20 ms 一包，假設第一包的相對傳輸時間是 50 ms
 封包   送出（媒體時間）  抵達     相對傳輸時間   |D|     J（ms）
  0         0 ms          50 ms       50 ms         -      0
  1        20 ms          72 ms       52 ms        2 ms    0 + (2 − 0)/16      = 0.125
  2        40 ms          88 ms       48 ms        4 ms    0.125 + (4 − 0.125)/16 ≈ 0.367
  3        60 ms         111 ms       51 ms        3 ms    0.367 + (3 − 0.367)/16 ≈ 0.531
```

第一行是定義：兩個封包抵達的間隔，減去它們在媒體時間上的間隔，就是「後一個比前一個多花了多少傳輸時間」。第二行是平滑：每次只朝新的 |D| 移動 1/16，等於一個指數移動平均，可以濾掉單一封包的雜訊。表格逐步算了三個封包：傳輸時間在 48～52 ms 之間跳動，J 從 0 慢慢爬升。真實實作用 timestamp tick 計算（48 kHz 下 1 ms＝48 tick），報告時也是 tick，換算成毫秒要除以時鐘頻率，**用錯時鐘頻率**是自製分析工具最常見的錯誤之一。

這個公式有兩個重要的限制，也是故事的關鍵。第一，它衡量的是**相鄰封包之間**的平均變動，對偶爾出現的大尖峰反應很遲鈍：一次 100 ms 的尖峰只讓 J 增加約 6 ms。第二，它是一個平滑後的「平均」，而 jitter buffer 要擋住的是**尾端**：只要有 3% 的封包晚到，聲音就會一直斷。所以 jitter buffer 的深度通常要是 RFC 3550 jitter 的好幾倍，34.11 節的實驗會用數字證明這件事。

### 用 SR 對齊時鐘、用 LSR／DLSR 算 RTT

SR 的 NTP 與 RTP 對照點有兩個用途。第一是**唇音同步**：音訊與視訊用不同的時鐘頻率與隨機的起始值，兩條串流的 timestamp 數值完全無法直接比較；但各自的 SR 把它們對到同一個牆上時鐘，接收端就能算出「這個音訊封包和那張畫面是不是同一時刻拍的」。第二是 **RTT**：

```text
 美咲（送出端）                                            SFU（接收端）
   │── SR：NTP = T₁ ───────────────────────────────────────►│ 收到，記下 LSR = T₁ 的中間 32 bit
   │                                                         │ 等了 DLSR = 250 ms 才送 RR
   │◄──────────────────────────────── RR：LSR、DLSR ────────│
   │ 收到時間 A
   │ RTT = A − LSR − DLSR       （單位：1/65536 秒）
```

美咲送出 SR 時記下時刻 T₁；SFU 收到後，把 T₁ 的中間 32 bit 當成 LSR，並記錄「收到 SR 之後過了多久才送出 RR」當成 DLSR；美咲收到 RR 的時刻是 A。A 減去 T₁ 是「來回的總時間」，再減去 SFU 刻意等的 DLSR，剩下的就是純粹花在網路上的往返時間。整個計算只用美咲自己的時鐘，所以兩端時鐘不需要同步。故事裡儀表板上的 RTT 70 ms，就是 SFU 用同樣的方法量出來的。

下面的程式組出 SR 與 RR，解析回來，並示範這兩個計算：

```python
import struct
from datetime import datetime, timezone

NTP_EPOCH_OFFSET = 2_208_988_800               # 1900-01-01 到 1970-01-01 的秒數


def to_ntp(unix_s: float) -> int:
    """64-bit NTP 時間：高 32 bit 是秒、低 32 bit 是秒的小數（單位 1/2^32 秒）。"""
    return int((unix_s + NTP_EPOCH_OFFSET) * 2**32)


def mid32(ntp64: int) -> int:
    return (ntp64 >> 16) & 0xFFFFFFFF            # LSR 用的「中間 32 bit」：單位 1/65536 秒


def build_sr(ssrc, ntp64, rtp_ts, packets, octets):
    header = struct.pack("!BBHI", 0x80, 200, 7 - 1, ssrc)       # RC=0，長度 = 32-bit word 數 - 1
    return header + struct.pack("!QIII", ntp64, rtp_ts, packets, octets)


def build_rr(reporter, source, fraction, cum_lost, ext_max, jitter, lsr, dlsr):
    header = struct.pack("!BBHI", 0x81, 201, 8 - 1, reporter)   # RC=1：帶一個 report block
    block = struct.pack("!IB3sIIII", source, fraction, (cum_lost & 0xFFFFFF).to_bytes(3, "big"),
                        ext_max, jitter, lsr, dlsr)
    return header + block


def parse_rtcp(pkt):
    b0, pt, length, ssrc = struct.unpack("!BBHI", pkt[:8])
    assert b0 >> 6 == 2 and len(pkt) == (length + 1) * 4
    out = {"PT": pt, "count": b0 & 0x1F, "ssrc": ssrc}
    if pt == 200:
        out["ntp"], out["rtp_ts"], out["packets"], out["octets"] = struct.unpack("!QIII", pkt[8:28])
    if pt == 201 and out["count"]:
        src, frac, lost3, ext_max, jit, lsr, dlsr = struct.unpack("!IB3sIIII", pkt[8:32])
        lost = int.from_bytes(lost3, "big", signed=True)        # 24-bit 有號數，重複封包可讓它變負
        out.update(source=src, fraction=frac, lost=lost, ext_max=ext_max,
                   jitter=jit, lsr=lsr, dlsr=dlsr)
    return out


AUDIO, VIDEO, SFU = 0x5EED0034, 0x1A2B3C4D, 0x0000C0DE
t0 = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc).timestamp()   # 台北晚上八點

# ① 美咲的瀏覽器送出音訊與視訊的 SR：把各自的 RTP 時鐘對到同一個 NTP 牆上時間
sr_a = parse_rtcp(build_sr(AUDIO, to_ntp(t0), 3_000_000_000, 250, 23_000))
sr_v = parse_rtcp(build_sr(VIDEO, to_ntp(t0 + 0.010), 1_450_000_000, 900, 980_000))
print(f"SR 音訊：NTP={sr_a['ntp'] >> 32}.{(sr_a['ntp'] & 0xFFFFFFFF) * 1000 >> 32:03d}s "
      f"↔ RTP {sr_a['rtp_ts']}（48 kHz）")
print(f"SR 視訊：NTP={sr_v['ntp'] >> 32}.{(sr_v['ntp'] & 0xFFFFFFFF) * 1000 >> 32:03d}s "
      f"↔ RTP {sr_v['rtp_ts']}（90 kHz）")


def wallclock(sr, rtp_ts, clock):
    """把某個 RTP timestamp 換成送出端的牆上時間：SR 提供了兩者的對應點。"""
    return sr["ntp"] / 2**32 + ((rtp_ts - sr["rtp_ts"]) & 0xFFFFFFFF) / clock


a_pkt, v_frame = 3_000_000_000 + 960 * 25, 1_450_000_000 + 3000 * 15
gap = (wallclock(sr_v, v_frame, 90_000) - wallclock(sr_a, a_pkt, 48_000)) * 1000
print(f"音訊 ts={a_pkt} 與視訊 ts={v_frame} 的擷取時間差 = {gap:+.1f} ms → 播放時要對齊")

# ② SFU 收到音訊 SR 後 250 ms 回 RR；美咲在 t0 + 0.322 s 收到這個 RR
lost, expected = 3, 250
rr = parse_rtcp(build_rr(SFU, AUDIO, lost * 256 // expected, 8, (1 << 16) + 613,
                         int(20.8 * 48), mid32(sr_a["ntp"]), int(0.250 * 65536)))
arrive = mid32(to_ntp(t0 + 0.322))
rtt = (arrive - rr["lsr"] - rr["dlsr"]) / 65536
print(f"RR：fraction lost={rr['fraction']}/256（{rr['fraction'] / 256:.1%}），cumulative lost={rr['lost']}，"
      f"ext highest seq={rr['ext_max']}（第 {rr['ext_max'] >> 16} 圈的 {rr['ext_max'] & 0xFFFF}）")
print(f"    jitter={rr['jitter']} tick = {rr['jitter'] / 48:.1f} ms，LSR={rr['lsr']:#010x}，"
      f"DLSR={rr['dlsr'] / 65536 * 1000:.0f} ms")
print(f"RTT = A - LSR - DLSR = {rtt * 1000:.1f} ms")

assert abs(gap - 10) < 0.01 and abs(rtt - 0.072) < 0.001
neg = parse_rtcp(build_rr(SFU, AUDIO, 0, -2, 0, 0, 0, 0))
assert neg["lost"] == -2                           # 重複封包多於遺失時，累計遺失可以是負的
```

```text
SR 音訊：NTP=3999931200.000s ↔ RTP 3000000000（48 kHz）
SR 視訊：NTP=3999931200.010s ↔ RTP 1450000000（90 kHz）
音訊 ts=3000024000 與視訊 ts=1450045000 的擷取時間差 = +10.0 ms → 播放時要對齊
RR：fraction lost=3/256（1.2%），cumulative lost=8，ext highest seq=66149（第 1 圈的 613）
    jitter=998 tick = 20.8 ms，LSR=0x1b400000，DLSR=250 ms
RTT = A - LSR - DLSR = 72.0 ms
```

前兩行是兩個 SR：音訊的 RTP 3000000000 與視訊的 RTP 1450000000 數值天差地遠，但透過 NTP 欄位，我們知道它們分別對應晚上八點整與八點整又 10 ms。第三行用這兩個對照點換算：音訊封包比它的 SR 晚 24000 tick（48 kHz 下 0.5 秒），視訊 frame 比它的 SR 晚 45000 tick（90 kHz 下 0.5 秒），兩者的牆上時間差 10 ms，接收端播放時應該讓這張畫面比這段聲音晚 10 ms 出現。沒有 SR，接收端只能用「抵達時間」對齊，而音訊與視訊的網路延遲本來就不同，嘴型就會對不上。

後三行是 RR。fraction lost 3/256 約 1.2%；延伸序號 66149 拆開是「第 1 圈的 613」，代表序號已經繞過一次；jitter 998 tick 除以 48 是 20.8 ms，這裡刻意用了 34.11 節實驗二量到的最高值。最後一行：美咲在 t0＋322 ms 收到 RR，減去 SFU 等待的 250 ms，RTT 是 72 ms。最後一個 assert 驗證了累計遺失可以是負數，自製工具若把它當成無號數，會在重複封包多的網路上報出四百萬的遺失。

## 34.10 Jitter buffer：用一點延遲換流暢

### 為什麼需要

美咲每 20 ms 送出一包，但封包抵達小安手機的間隔可能是 15、35、5、60 ms。如果收到就播，播放器會一下沒東西可播、一下同時湧來好幾包，聲音忽斷忽快；亂序抵達的封包更會讓聲音前後顛倒。**Jitter buffer**（抖動緩衝區）的做法是：收到的封包先放進緩衝區，依 sequence 排好，再依 **timestamp 排定的時刻**一個一個拿出來播。只要封包在它的播放時刻之前到達，抖動與亂序就被完全吸收。

```text
 送出時刻（每 20 ms）   0      20      40      60      80     100     120 ms
 美咲送出               #1     #2      #3      #4      #5      #6      #7
                         ╲       ╲       ╲        ╲       ╲       ╲       ╲
 抵達（延遲 45～110 ms）  #1@47  #2@68   #4@108  #3@112  #5@127  #6@146  #7@232（尖峰）
                         ▼                                                  
 播放時刻 = 第一包抵達 ＋ d ＋ 20 ms × k
   d = 20 ms：  #1@67  #2@87  #3@107✗ #4@127  #5@147  #6@167  #7@187✗
                              ↑#3 在 112 才到，晚了 5 ms → 丟掉、補洞
   d = 80 ms：  #1@127 #2@147 #3@167✓ #4@187  #5@207  #6@227  #7@247✓
                              全部趕上，但每個聲音都晚 60 ms 才播出
```

這張圖把故事的機制畫出來。上半部，封包 #3 在路上耽擱，比 #4 還晚到（亂序）；#7 遇上 4G 的排隊尖峰，晚了一百多毫秒。下半部比較兩個深度。d＝20 ms 時，播放器在 107 ms 要播 #3，它卻 112 ms 才到，只好用 PLC 補洞，之後 #3 到了也沒用；#7 同理。d＝80 ms 時，每個封包都有 80 ms 的寬限，#3 與 #7 都趕上了，代價是所有聲音都晚 60 ms 播放。jitter buffer 的本質就是這個取捨：**多等一點，晚到的封包就變少；少等一點，延遲就降低，但晚到等於遺失。**

這也回答了小晴的疑問：為什麼儀表板看不到問題？RTCP 的遺失是「預期收到數減實際收到數」，晚到的 #3 確實收到了，在 RR 裡不算遺失；但對小安的耳朵來說，它和遺失一模一樣。WebRTC 的 `getStats()` 另外提供 jitter buffer 的平均延遲與「被補洞的樣本數」等指標（第 39 章），那才是使用者感受的指標。

### 固定與自適應

**固定深度**的 jitter buffer 最簡單：從第一個封包開始，每個封包都在「抵達基準 ＋ d」時播放。它的問題是網路狀況會變：捷運進站時 4G 很穩，出站時大塞車，固定的 d 不是在穩定時浪費延遲，就是在壅塞時不夠用。**自適應**（adaptive）jitter buffer 持續觀察最近封包的延遲分布，把目標深度設在「足以涵蓋大部分封包」的位置（例如某個高百分位，或最近幾秒最慢的封包），網路變差時加深，變好時慢慢變淺。

改變深度不能讓聲音跳一下，所以音訊的自適應 jitter buffer 要搭配**時間伸縮**（time stretching）：要變淺時把聲音播快一點點（例如把幾個 20 ms 壓成 18 ms，挑在靜音或穩定的母音處做），要變深時播慢一點或延長一段。libwebrtc 的音訊 jitter buffer 叫 **NetEq**，就是結合了自適應深度、時間伸縮與 PLC 的實作。音訊 M 位元標示的「靜音後第一包」也有用處：在靜音時調整深度，使用者完全聽不出來。

自適應還能順便處理**時鐘漂移**（clock drift）。美咲電腦的音效卡標稱 48 kHz，實際可能是 48,002 Hz；小安手機的可能是 47,998 Hz。差異只有百萬分之幾十，但一堂一小時的課累積下來可能差到上百毫秒：送得比播得快，緩衝區會慢慢變滿、延遲越來越大；反過來則會慢慢見底、開始補洞。固定深度的 buffer 對此無能為力，自適應的會把它當成網路變化一起吸收。

### 視訊的 jitter buffer

視訊的 jitter buffer 以 **frame** 為單位：收集同一個 timestamp 的所有封包，等到 M=1 且序號連續，再檢查這張 frame 參考的畫面是否都已解碼，才交給解碼器。它比音訊多一個選擇：如果 RTT 夠短，遺失的封包可以用 NACK 請送出端重送，只要重送在播放時刻前到達就好。所以視訊的深度要考慮 RTT：同一個機房內 RTT 幾毫秒，重送幾乎免費；台北到歐洲 250 ms，重送一次就超過整個延遲預算，只能請求 keyframe。音訊與視訊的 jitter buffer 各自運作，但播放時要依 34.9 節的 SR 對照點對齊，通常讓比較早準備好的那一路等另一路。

| 深度設定 | 延遲 | 晚到丟棄 | 適合的情境 |
|---|---|---|---|
| 很淺固定（約 20 ms） | 最低 | 在行動網路上很多 | 有線、同機房、jitter 極小的環境 |
| 中等固定（約 60～100 ms） | 中 | 少 | 網路穩定、可預測的專線 |
| 很深固定（數百 ms 以上） | 高，對話不自然 | 幾乎沒有 | 單向收聽、可以容忍延遲的場合 |
| 自適應（NetEq 一類） | 隨網路變化 | 少，變化剛開始時會有一些 | 一般的即時通話，幾乎都用這種 |

## 34.11 動手做：RTP 打包、UDP 傳送與 jitter buffer

這一節用兩段程式重現本章的核心機制。實驗一用 `struct` 組出並解析 RTP 封包，觀察 marker 與 timestamp 在視訊與音訊上的不同規則；實驗二在 127.0.0.1 上用 UDP 送出 15 秒的語音 RTP，模擬一段會變壞的手機網路，在接收端計算 RFC 3550 的統計，再讓六種 jitter buffer 播放同一份抵達紀錄。兩段程式都只用標準函式庫，以下是在 macOS 上實際執行的輸出。

### 實驗一：組出並解析 RTP 封包

程式提供 `build_rtp()` 與 `parse_rtp()`，支援 CSRC、RFC 8285 的 one-byte header extension 與 padding。視訊部分模擬 30 fps 的 H.264：一張 6200 bytes 的 I frame 加三張 P frame，每個封包最多 1200 bytes。刻意選了接近上限的初始序號與 timestamp，觀察回繞。音訊部分模擬 Opus 20 ms 一包，中間有 80 ms 靜音不送封包（DTX，discontinuous transmission），每個封包帶一個音量等級的 header extension。

```python
import struct

RTP_VERSION = 2


def build_rtp(pt, seq, ts, ssrc, payload, marker=False, csrcs=(), ext=None):
    """組一個 RTP 封包。ext 是 [(id, bytes)]，用 RFC 8285 的 one-byte header extension。"""
    x = 1 if ext else 0
    byte0 = (RTP_VERSION << 6) | (0 << 5) | (x << 4) | len(csrcs)   # V=2, P=0, X, CC
    byte1 = (int(marker) << 7) | pt                                  # M + 7-bit PT
    header = struct.pack("!BBHII", byte0, byte1, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc)
    header += b"".join(struct.pack("!I", c) for c in csrcs)
    if ext:
        body = b"".join(bytes([(eid << 4) | (len(val) - 1)]) + val for eid, val in ext)
        body += b"\x00" * (-len(body) % 4)                           # 補齊到 32-bit 邊界
        header += struct.pack("!HH", 0xBEDE, len(body) // 4) + body
    return header + payload


def parse_rtp(data):
    if len(data) < 12:
        raise ValueError("比 RTP 固定 header 還短")
    b0, b1, seq, ts, ssrc = struct.unpack("!BBHII", data[:12])
    if b0 >> 6 != 2:
        raise ValueError(f"version={b0 >> 6}，不是 RTP")
    cc, x, p = b0 & 0x0F, (b0 >> 4) & 1, (b0 >> 5) & 1
    off = 12 + 4 * cc
    csrcs = list(struct.unpack(f"!{cc}I", data[12:off]))
    ext = []
    if x:
        profile, words = struct.unpack("!HH", data[off:off + 4])
        body = data[off + 4:off + 4 + 4 * words]
        off += 4 + 4 * words
        i = 0
        while profile == 0xBEDE and i < len(body):
            if body[i] == 0:                     # padding byte
                i += 1
                continue
            eid, length = body[i] >> 4, (body[i] & 0x0F) + 1
            ext.append((eid, body[i + 1:i + 1 + length]))
            i += 1 + length
    end = len(data) - (data[-1] if p else 0)     # P=1 時最後一個 byte 是 padding 長度
    return {"M": b1 >> 7, "PT": b1 & 0x7F, "seq": seq, "ts": ts, "ssrc": ssrc,
            "csrcs": csrcs, "ext": ext, "payload": data[off:end]}


# ── 視訊：H.264 風格，90 kHz 時鐘，30 fps → 每個 frame 的 timestamp 加 3000 ──
VIDEO_PT, VIDEO_SSRC, MAX_PAYLOAD = 96, 0x1A2B3C4D, 1200
frame_sizes = [6200, 1500, 900, 1300]           # 第一個是 I frame，後面是 P frame
seq, ts = 65533, 4294964000                     # 刻意選接近上限的值，示範回繞
video = []
for size in frame_sizes:
    chunks = [b"v" * min(MAX_PAYLOAD, size - i) for i in range(0, size, MAX_PAYLOAD)]
    for k, chunk in enumerate(chunks):
        video.append(build_rtp(VIDEO_PT, seq, ts, VIDEO_SSRC, chunk, marker=(k == len(chunks) - 1)))
        seq = (seq + 1) & 0xFFFF
    ts = (ts + 90000 // 30) & 0xFFFFFFFF

print("視訊：frame 大小", frame_sizes, "bytes")
print(" seq    timestamp   M  payload")
for pkt in video:
    h = parse_rtp(pkt)
    print(f"{h['seq']:>5} {h['ts']:>11}  {h['M']}  {len(h['payload']):>5}")

# ── 音訊：Opus，RTP 時鐘固定 48 kHz，20 ms 一包 → timestamp 每包加 960 ──
AUDIO_PT, AUDIO_SSRC = 111, 0x5EED0034
talk = [True, True, True, False, False, False, False, True, True]   # False = 靜音（DTX 不送）
seq, ts, silent_before, audio = 20000, 160000, False, []
for speaking in talk:
    if speaking:
        level = bytes([0x80 | 30])               # audio level 擴充：V=1（有聲）、-30 dBov
        audio.append(build_rtp(AUDIO_PT, seq, ts, AUDIO_SSRC, b"o" * 80,
                               marker=silent_before, ext=[(1, level)]))
        seq += 1                                 # 序號只在真的送出時才加
    silent_before = not speaking
    ts += 960                                    # 時間照樣前進，靜音也算在媒體時間裡

print("\n音訊：每 20 ms 一包，中間 80 ms 靜音沒有送")
print(" seq  timestamp  M  Δts   ext")
prev = None
for pkt in audio:
    h = parse_rtp(pkt)
    delta = "-" if prev is None else h["ts"] - prev
    print(f"{h['seq']:>5} {h['ts']:>9}  {h['M']}  {delta!s:>4}  id={h['ext'][0][0]} level=-{h['ext'][0][1][0] & 0x7F} dBov")
    prev = h["ts"]

first = audio[0]
print("\n第一個音訊封包的 header（含擴充）:", first[:20].hex(" "))
hv = parse_rtp(video[0])
assert hv["seq"] == 65533 and parse_rtp(video[3])["seq"] == 0           # 序號回繞
assert parse_rtp(video[6])["ts"] == (4294964000 + 3000) % 2**32        # timestamp 回繞
assert [parse_rtp(p)["M"] for p in audio] == [0, 0, 0, 1, 0]
mixed = build_rtp(AUDIO_PT, 1, 2, 3, b"x", csrcs=[0xA, 0xB])
assert parse_rtp(mixed)["csrcs"] == [0xA, 0xB] and len(mixed) == 12 + 8 + 1
```

```text
視訊：frame 大小 [6200, 1500, 900, 1300] bytes
 seq    timestamp   M  payload
65533  4294964000  0   1200
65534  4294964000  0   1200
65535  4294964000  0   1200
    0  4294964000  0   1200
    1  4294964000  0   1200
    2  4294964000  1    200
    3  4294967000  0   1200
    4  4294967000  1    300
    5        2704  1    900
    6        5704  0   1200
    7        5704  1    100

音訊：每 20 ms 一包，中間 80 ms 靜音沒有送
 seq  timestamp  M  Δts   ext
20000    160000  0     -  id=1 level=-30 dBov
20001    160960  0   960  id=1 level=-30 dBov
20002    161920  0   960  id=1 level=-30 dBov
20003    166720  1  4800  id=1 level=-30 dBov
20004    167680  0   960  id=1 level=-30 dBov

第一個音訊封包的 header（含擴充）: 90 6f 4e 20 00 02 71 00 5e ed 00 34 be de 00 01 10 9e 00 00
```

先看視訊表格，它正是 34.8 節最後那張圖。I frame 切成 6 個封包，序號從 65533 經過 65535 回繞到 0、1、2，timestamp 全部是 4294964000，只有最後一包（payload 只剩 200 bytes）M=1。下一張 P frame 的 timestamp 加 3000；再下一張（900 bytes，只要一包）的 timestamp 變成 2704，因為 4294967000＋3000 超過 2³²，繞回了小數字。一個天真的接收端如果用 `ts_new > ts_old` 判斷先後，就會在這裡把新畫面當成很久以前的舊畫面，必須和第 10 章的 TCP 序號一樣用「差值落在前半圈」比較。

再看音訊表格，這是新手最常誤判的情況。序號 20000 到 20004 完全連續，代表**沒有遺失**；但 20002 到 20003 之間 timestamp 跳了 4800（5 個 frame 的時間），而且 20003 的 M=1。合起來的意思是：中間有 80 ms 靜音，送出端依 DTX 不送封包，序號只在真的送出時才加，媒體時間則照樣前進。接收端看到這個組合，應該播放靜音或舒適噪音，而不是啟動 PLC。如果你的分析工具用 timestamp 的跳躍來算遺失，會把每一段停頓都算成丟包；反過來，序號跳號才是真的遺失。

最後一行是第一個音訊封包的前 20 bytes，可以和位元布局圖逐格對照：`90` 是二進位 1001 0000，V=2、P=0、X=1、CC=0；`6f` 是 M=0、PT=111；`4e 20` 是序號 20000；`00 02 71 00` 是 timestamp 160000；`5e ed 00 34` 是 SSRC。接著 `be de 00 01` 表示 one-byte header extension、長度 1 個 word；`10` 的高 4 bit 是 id 1、低 4 bit 是 0（長度減一，所以資料 1 byte）；`9e` 是 0x80（有聲）加上 30（-30 dBov）；最後兩個 `00` 是補齊到 4 bytes 的 padding。

### 實驗二：UDP 送一串 RTP，接收端實作 jitter buffer

這段程式是故事的縮小版。送出端 thread 產生 15 秒、750 個 Opus 封包；`network()` 模擬小安的手機網路：前 5 秒穩定（基本延遲 45 ms 加上一點小抖動），中間 5 秒基地台壅塞（不定時出現 60～120 ms 的排隊尖峰，接下來幾個封包慢慢消退），最後 5 秒恢復，全程 1% 隨機遺失、偶爾重複。送出端依「模擬抵達時間」的順序把封包真的用 UDP 送到 127.0.0.1，所以接收端會看到真實的亂序與重複，最後送一個 RTCP BYE 結束。

有一個實驗設計要先說明：真實的接收端用自己的時鐘記錄抵達時間，但那樣每次執行的結果都不同，也需要真的等 15 秒。所以這裡由模擬網路在每個 datagram 前面附上 8 bytes 的「模擬抵達時間」，接收端讀出後剝掉，其餘全部是標準的 RTP 處理。接收端做兩件事：`ReceiverStats` 依 RFC 3550 附錄 A 的演算法維護延伸序號、遺失與 interarrival jitter；`playout()` 依模擬時鐘每 20 ms 向 buffer 要一個 frame，比較五種固定深度與一種自適應策略。

```python
import random
import socket
import struct
import threading

CLOCK, FRAME_MS, N = 48000, 20, 750             # Opus：48 kHz 時鐘、20 ms 一包、送 15 秒
TS_STEP = CLOCK * FRAME_MS // 1000              # 每包 timestamp 加 960
SSRC, PT, SEQ0, TS0 = 0x5EED0034, 111, 65400, 3_000_000_000   # 序號會在中途回繞
LAB = struct.Struct("!d")                       # 實驗用：模擬網路附上的「抵達時間」(ms)
BUSY = range(250, 500)                          # 第 5～10 秒：基地台壅塞


def network(seed=34):
    """模擬手機上行：前後各 5 秒穩定，中間 5 秒出現排隊尖峰；1% 遺失，偶有重複。"""
    rng, spike, out = random.Random(seed), 0.0, []
    for i in range(N):
        busy = i in BUSY
        if busy and rng.random() < 0.06:
            spike = rng.uniform(60, 120)        # 排隊造成的延遲尖峰
        spike *= 0.8                            # 接下來幾個封包慢慢消退
        delay = 45 + rng.expovariate(1 / (8 if busy else 2)) + spike
        if rng.random() < 0.01:
            continue
        out.append((FRAME_MS * i + delay, i))
        if rng.random() < 0.004:
            out.append((FRAME_MS * i + delay + 3, i))
    return sorted(out)                          # 依抵達時間送出，亂序自然出現


def sender(addr, schedule):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for arrival, i in schedule:
            pkt = struct.pack("!BBHII", 0x80, PT, (SEQ0 + i) & 0xFFFF,
                              (TS0 + i * TS_STEP) & 0xFFFFFFFF, SSRC) + b"o" * 80
            s.sendto(LAB.pack(arrival) + pkt, addr)
        s.sendto(LAB.pack(-1) + struct.pack("!BBHI", 0x81, 203, 1, SSRC), addr)  # RTCP BYE


class ReceiverStats:
    """RFC 3550 附錄 A 的接收端統計：延伸序號、預期與遺失數、interarrival jitter。"""
    def __init__(self):
        self.base = self.max_seq = self.transit = None
        self.cycles = self.received = self.reordered = 0
        self.jitter = self.jitter_peak = 0.0    # 單位：timestamp tick（1/48000 秒）

    def update(self, seq, ts, arrival_ms):
        if self.base is None:
            self.base = self.max_seq = seq
        delta = (seq - self.max_seq) & 0xFFFF
        if 0 < delta < 0x8000:                  # 往前走；數值變小代表回繞了一圈
            if seq < self.max_seq:
                self.cycles += 1 << 16
            self.max_seq = seq
        elif delta:
            self.reordered += 1                 # 比目前最大序號舊：亂序（或重複）
        self.received += 1
        transit = arrival_ms * CLOCK / 1000 - ts   # 兩邊時鐘不同步也沒關係，只看差值
        if self.transit is not None:
            self.jitter += (abs(transit - self.transit) - self.jitter) / 16
            self.jitter_peak = max(self.jitter_peak, self.jitter)
        self.transit = transit

    def ms(self, ticks):
        return ticks * 1000 / CLOCK


def playout(arrivals, depth_ms=None):
    """depth_ms=None 為自適應。回傳播放延遲與補洞統計（模擬時鐘，單位 ms）。"""
    buffer, seen, recent, late, holes, glitches, run, held = {}, set(), [], 0, 0, 0, 0, 0
    transit0 = arrivals[0][0] - (arrivals[0][1] - SEQ0) * FRAME_MS
    offset = transit0 + (depth_ms if depth_ms is not None else 40)
    delays, j = {"calm": [], "busy": []}, 0
    for k in range(N):                          # 每 20 ms 播放器要一個 frame
        if depth_ms is None and recent:         # 目標：最近 3 秒最慢的封包也來得及
            target = max(recent[-150:]) + 5
            offset += max(-0.5, min(5.0, target - offset))  # 縮短要慢（加速播放），拉長可以快
        play_at = k * FRAME_MS + offset
        while j < len(arrivals) and arrivals[j][0] <= play_at:
            arr, seq = arrivals[j]
            j += 1
            if seq in seen:
                continue                        # 重複封包直接丟
            seen.add(seq)
            recent.append(arr - (seq - SEQ0) * FRAME_MS)
            if seq - SEQ0 < k:
                late += 1                       # 它的播放時刻已過：晚到等於遺失
            else:
                buffer[seq] = arr               # 亂序到的先放著，依序號取用
        held = max(held, len(buffer))
        if buffer.pop(SEQ0 + k, None) is None:
            holes += 1                          # 播放器只好補洞（PLC）
            run += 1
        else:
            glitches += run >= 3                # 連續補洞 ≥ 60 ms，人耳明顯聽得出來
            run = 0
        delays["busy" if k in BUSY else "calm"].append(offset)
    avg = {p: sum(v) / len(v) for p, v in delays.items()}
    return avg, late, holes, glitches, held


rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
rx.bind(("127.0.0.1", 0))
rx.settimeout(2)
t = threading.Thread(target=sender, args=(rx.getsockname(), network()))
t.start()
stats, arrivals = ReceiverStats(), []
while True:
    data, _ = rx.recvfrom(2048)
    arrival, pkt = LAB.unpack(data[:8])[0], data[8:]
    if 200 <= pkt[1] <= 204:                    # rtcp-mux：第二個 byte 落在 RTCP 的 PT 範圍
        print(f"收到 RTCP BYE（PT={pkt[1]}），SSRC={struct.unpack('!I', pkt[4:8])[0]:#x}")
        break
    _, _, seq, ts, _ = struct.unpack("!BBHII", pkt[:12])
    stats.update(seq, ts, arrival)
    arrivals.append((arrival, SEQ0 + ((seq - SEQ0) & 0xFFFF)))  # 本實驗不超過一圈
t.join()
rx.close()

expected = stats.cycles + stats.max_seq - stats.base + 1
unique = len({s for _, s in arrivals})
print(f"seq {stats.base} → {stats.max_seq}（回繞 {stats.cycles >> 16} 次），expected={expected}")
print(f"received={stats.received}（不重複 {unique}），RFC 3550 lost={expected - stats.received}，"
      f"實際沒到={expected - unique}，亂序或重複={stats.reordered}")
print(f"interarrival jitter：結束時 {stats.ms(stats.jitter):.1f} ms，過程中最高 {stats.ms(stats.jitter_peak):.1f} ms")
print("\n策略         平靜時延遲 壅塞時延遲  晚到丟棄  補洞比例  卡頓  buffer 最多")
results = {}
for depth in (20, 40, 60, 100, 160, None):
    avg, late, holes, glitches, held = results[depth] = playout(arrivals, depth)
    name = "自適應" if depth is None else f"固定 {depth} ms"
    print(f"{name:<9}  {avg['calm']:>7.0f} ms {avg['busy']:>7.0f} ms {late:>7} {holes / N:>9.1%} "
          f"{glitches:>5} {held:>7}")

assert expected == N and stats.cycles == 1 << 16
assert results[20][1] > results[60][1] > results[160][1] == 0     # 越淺越多晚到
adaptive = results[None]
assert adaptive[0]["calm"] < results[100][0]["calm"] and adaptive[1] < results[60][1]
```

```text
收到 RTCP BYE（PT=203），SSRC=0x5eed0034
seq 65400 → 613（回繞 1 次），expected=750
received=742（不重複 740），RFC 3550 lost=8，實際沒到=10，亂序或重複=11
interarrival jitter：結束時 2.0 ms，過程中最高 20.8 ms

策略         平靜時延遲 壅塞時延遲  晚到丟棄  補洞比例  卡頓  buffer 最多
固定 20 ms        67 ms      67 ms      82     12.3%     9       2
固定 40 ms        87 ms      87 ms      44      7.2%     8       3
固定 60 ms       107 ms     107 ms      16      3.5%     3       4
固定 100 ms      147 ms     147 ms       1      1.5%     0       6
固定 160 ms      207 ms     207 ms       0      1.3%     0       9
自適應             84 ms     149 ms       9      2.5%     1       6
```

先看接收端統計的前三行。第一行：接收端靠第二個 byte 是 203 認出最後那個 datagram 是 RTCP BYE，這就是 rtcp-mux 的分流法。第二行：序號從 65400 一路走到 613，中間回繞一次，延伸序號算出預期 750 個，和送出數一致；沒有處理回繞的話，`613 - 65400` 會得到一個荒謬的負數。第三行很有教育意義：收到 742 個，但其中 2 個是重複，真正不重複的是 740 個；RFC 3550 的遺失定義是「預期數減收到數」，重複封包被算進收到，所以報告的遺失是 8，實際沒到的是 10。這就是 cumulative lost 被定義成有號數的原因，也提醒你 RTCP 的遺失只是近似值。亂序或重複共 11 次，代表 4G 的抖動確實讓封包的抵達順序顛倒。

第四行是本實驗最重要的觀察之一：interarrival jitter 在壅塞時最高只有 20.8 ms，結束時（網路恢復後）是 2.0 ms。對照下面的表格，固定 20 ms 的 buffer 有 12.3% 的時間在補洞，固定 40 ms 也還有 7.2%，要到 100 ms 才幾乎沒有晚到。也就是說，**jitter 數值 20 ms，需要的 buffer 卻是 100 ms 左右**。原因就是 34.9 節講的：RFC 3550 jitter 是相鄰封包差值的平滑平均，尖峰被 1/16 稀釋了，而 buffer 要擋的是尾端。小晴如果只看儀表板的 jitter 數字來決定 buffer 大小，就會重蹈「低延遲模式」的覆轍。

再看表格的各列。「平靜時延遲」與「壅塞時延遲」是從送出到播放的單向延遲（這裡用模擬的真值計算，真實系統只知道相對值），固定深度的兩欄當然一樣，都等於第一個封包的網路延遲約 47 ms 加上深度。「晚到丟棄」是抵達時已經錯過播放時刻的封包數；「補洞比例」是晚到加上真的遺失；「卡頓」是連續補洞 60 ms 以上的次數，人耳一定聽得到。

固定 20 ms 正是故事裡的「低延遲模式」：延遲只有 67 ms，但壅塞時段有 82 個封包晚到，補洞 12.3%，出現 9 次明顯卡頓，這就是小安聽到的機器人聲。固定 100 ms 幾乎完美，補洞 1.5% 中的 1.3% 是真的遺失（10 個），但平靜時也要承受 147 ms 的延遲；160 ms 完全沒有晚到，卻在平靜時白白多等 60 ms。自適應的那列最有意思：平靜時平均 84 ms，壅塞時自動加深到 149 ms，晚到 9 個、只卡頓 1 次。它的晚到集中在壅塞剛開始的時候：buffer 還沒看到尖峰，來不及加深；它在平靜時的延遲也比 67 ms 高，因為壅塞結束後 buffer 只能慢慢縮（每 20 ms 最多縮 0.5 ms，相當於加速 2.5% 播放，避免聲音變調）。最後一欄顯示 buffer 裡同時最多放了幾個封包：深度越大，要存的封包越多。

這個表格就是阿德和 Joe 後來寫進設計文件的結論：沒有一個固定深度能同時在穩定與壅塞時都好；「低延遲模式」應該改成「自適應，但把目標深度的下限設低一點」，而不是把上限壓死。

## 34.12 在工作上怎麼用

工單結案後，Joe 和小晴把排查過程整理成影音團隊的工作手冊。

**後端與 SRE：品質儀表板要分開「遺失」與「晚到」。** RTCP RR 的遺失與 jitter 只描述網路，使用者聽到的品質要看接收端的播放統計。WebRTC 的 `getStats()` 在 `inbound-rtp` 報告裡提供 `packetsLost`、`jitter`，以及 jitter buffer 的累計延遲與輸出樣本數（兩者相除就是平均 jitter buffer 延遲）、被補洞的樣本數（`concealedSamples`）等欄位；聲聲 Live 的教室頁每 5 秒把精簡過的這些數字經教室 WebSocket 送回 collector（第 39 章）。小安那晚的數據顯示：`packetsLost` 只有 0.3%，但被補洞的樣本佔 11%，平均 jitter buffer 延遲只有 21 ms。這組數字一出來，根因就清楚了。第 39 章會完整解讀這些欄位。

**影音工程師：用 Wireshark 或 tshark 分析 RTP 串流。** 即使是 SRTP 加密的 WebRTC 流量，header 仍是明文，可以在 SFU 上抓包分析。Wireshark 預設不會把任意 UDP port 解成 RTP，要用「Decode As」指定，或啟用 RTP 的 heuristic 解析；之後 Telephony 選單的 RTP Streams 與 Stream Analysis 會列出每個 SSRC 的遺失、序號錯誤、最大間隔與 jitter。命令列版本如下（示意輸出）：

```bash
# 在 sfu-tpe-1（VPC 內位址 10.20.1.15）上抓 30 秒，只抓往小安手機的流量（需要 root）
sudo tcpdump -ni eth0 -w class-8812.pcap 'udp and host 198.51.100.140' -G 30 -W 1

# 把 SFU 的媒體埠 UDP 40000 解成 RTP，列出每條串流的統計
tshark -r class-8812.pcap -d udp.port==40000,rtp -q -z rtp,streams
# ↓ 示意輸出（欄位依 tshark 版本略有不同）
#  Src IP addr  Port   Dest IP addr     Port  SSRC        Payload  Pkts  Lost      Max Delta(ms)  Max Jitter(ms)  Mean Jitter(ms)
#  10.20.1.15   40000  198.51.100.140   41234 0x5eed0034  111      1497  4 (0.3%)  118.6          21.4            6.2
#  10.20.1.15   40000  198.51.100.140   41234 0x1a2b3c4d  96       4310  9 (0.2%)  141.0          18.9            5.1
```

先釐清埠號：所有參與者的媒體都送到 SFU 的同一個 UDP 40000（第 35 章 SDP 裡的 candidate `203.0.113.60:40000`），抓包看到的來源是 SFU 的 VPC 位址 10.20.1.15；第 2 章品質回報用的 `10.20.1.15:50000` 是另一條送往 collector 的流量，不要拿來解 RTP。讀這份輸出時要注意三件事。第一，Payload 欄顯示的是 PT 數字，111 與 96 是動態 payload type，要對照這次通話的 SDP 才知道是 Opus 與 H.264（tshark 若沒看到 SDP 只能顯示數字）。第二，Max Delta 118.6 ms 代表兩個連續音訊封包的抵達間隔最長達到 118.6 ms，而正常應是 20 ms，這就是 4G 尖峰；它比 Mean Jitter 6.2 ms 更直接地告訴你 jitter buffer 至少要多深。第三，這裡抓的是 SFU 送出端，看不到最後一段 4G 的抖動；要量使用者感受到的，還是要靠接收端的統計。

**錄影與直播：用 ffprobe 分清 codec、container 與 GOP。** 錄影檔 `/recordings/lesson-0815.*` 出問題時，第一步是確認裡面到底裝了什麼（示意輸出）：

```bash
ffprobe -v error -show_entries format=format_name:stream=codec_type,codec_name,profile,width,height,r_frame_rate,sample_rate \
        -of compact lesson-0815.mp4
# ↓ 示意輸出
# format|format_name=mov,mp4,m4a,3gp,3g2,mj2
# stream|codec_type=video|codec_name=h264|profile=Constrained Baseline|width=1280|height=720|r_frame_rate=30/1
# stream|codec_type=audio|codec_name=opus|sample_rate=48000

# 看 GOP：列出前 120 個 frame 的類型，數一數 I frame 的間隔
ffprobe -v error -select_streams v:0 -show_entries frame=pict_type -of csv=p=0 -read_intervals %+#120 lesson-0815.mp4 \
  | tr -d '\n' ; echo
# ↓ 示意輸出：WebRTC 錄下來的檔案沒有 B frame，keyframe 只在需要時才出現
# IPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
```

第一段告訴你 container 是 MP4（ffprobe 把 MP4 家族列在一起）、視訊是 H.264 Constrained Baseline 720p30、音訊是 Opus；某些舊播放器不支援 MP4 裡的 Opus，就會有畫面沒聲音（延伸問答 Q1）。第二段只有開頭一個 I、後面全是 P，是即時通話錄影的典型樣子；要切成 HLS 回放，就得重新編碼成每 2 秒一個 keyframe。

**排查「聲音斷斷續續」的判斷流程**：

```text
 症狀：聲音斷續／機器人聲／畫面卡住
   │
   ├─ 接收端 packetsLost 高？ ── 是 ─► 網路真的在丟：看路徑、頻寬估計、是否該開 FEC／NACK（第 37 章）
   │
   ├─ packetsLost 低、補洞比例高？ ── 是 ─► 晚到：看 jitter buffer 平均延遲是否被壓得太低
   │        └─► 有人改過 buffer 上限或「低延遲」設定嗎？改回自適應，只調下限
   │
   ├─ jitter buffer 延遲一路變大？ ─► 時鐘漂移或 buffer 不會縮：確認自適應有生效
   │
   ├─ 只有視訊花屏、聲音正常？ ─► 參考 frame 遺失：看 PLI／NACK 次數與 keyframe 是否送得出來
   │
   └─ 嘴型對不上？ ─► 音訊與視訊是否同一個 CNAME、SR 是否正常送出；自製播放器是否用抵達時間對齊
```

這個流程的第一刀就是本章的核心區分：真的遺失與晚到。兩者在使用者耳中相同，處理方式卻完全不同：前者要靠 FEC、重送或降 bitrate，後者靠 jitter buffer。混淆兩者是「降解析度救聲音」這類無效修補的來源。

**前端與資安：協商與偵測。** 前端不要假設某個瀏覽器「一定能播」某個 codec，而是用 `MediaCapabilities` 與 `RTCRtpSender.getCapabilities()` 偵測後再選。Rita 審查時確認兩件事：所有媒體都走 SRTP，沒有「為了除錯而關閉加密」的設定；RTP header 與 extension 是明文，音量等級能透露誰在講話，所以不要在 extension 裡放任何使用者識別資料。

## 34.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 聲音斷續、像機器人，但 RTCP 遺失很低 | jitter buffer 太淺，晚到的封包被丟棄 | `getStats` 補洞樣本比例高、平均 jitter buffer 延遲很低；抓包看 Max Delta 遠大於 20 ms | 改回自適應 jitter buffer，只調低目標下限，不要壓死上限 |
| 通話越久延遲越大 | 送出端與接收端時鐘漂移，或 buffer 只會加深不會縮 | 平均 jitter buffer 延遲隨時間單調上升，網路指標卻穩定 | 使用支援時間伸縮的自適應 buffer；自製播放器要處理漂移 |
| 掉幾個封包後畫面花屏好幾秒 | 參考鏈上的 frame 壞了，要等下一個 keyframe | 接收端 PLI 次數、keyframe 間隔；ffprobe 看 GOP | 確認 PLI／NACK 有被處理；直播固定 1～2 秒 keyframe；送出端不要忽略 PLI |
| 自製分析工具跑一陣子後報出大量遺失 | 沒處理 16 bit 序號或 32 bit timestamp 的回繞 | 問題出現的時刻剛好是序號從 65535 繞回 0 | 維護延伸序號（圈數 × 65536 ＋ 序號），比較時用差值落在前半圈 |
| 分析工具把每次停頓都算成丟包 | 用 timestamp 跳躍判斷遺失，誤把 DTX 靜音當成遺失 | 序號連續但 timestamp 跳躍，且跳躍後的封包 M=1 | 遺失只看序號；timestamp 跳躍配合 M 位元判斷為靜音 |
| jitter 數字大得離譜或小得離譜 | 換算時用錯時鐘頻率（例如視訊用 48 kHz） | 對照 SDP 的 `a=rtpmap`，視訊應為 90000 | 依 payload type 對應的 clock rate 換算 |
| 從 MP4 取出的 H.264 送進 RTP 後解不出畫面 | 把 AVCC 的長度前綴當資料送出，或 keyframe 前沒有 SPS／PPS | 看 payload 前幾個 bytes 是不是 4 bytes 長度；檢查第一個 IDR 前有沒有 SPS／PPS | 依 RFC 6184 改用 NAL unit 切包（FU-A、STAP-A），keyframe 前補上參數集 |
| Wireshark 只看到 UDP，看不到 RTP 欄位 | 動態 port 沒有被自動辨識為 RTP | 封包內容第一個 byte 是 0x80 或 0x90 | 用 Decode As 指定 RTP，或啟用 RTP heuristic 解析 |
| 共用 port 時，部分 RTP 被當成 RTCP 丟掉 | rtcp-mux 下用了 64～95 的 payload type，M=1 時第二個 byte 落進 RTCP 範圍 | 被誤判的封包 M=1 且 PT 落在 72～76 | payload type 改用 96～127 |
| 嘴型對不上 | 音訊與視訊沒有用 SR 對齊，或兩條串流的 CNAME 不同 | 檢查 SDES CNAME 是否一致、SR 是否定期送出 | 依 SR 的 NTP／RTP 對照點同步；自製混流不要用抵達時間對齊 |

除錯影音問題的通則是：**先分清是哪一層壞了**。網路層看遺失、RTT、Max Delta；RTP 層看序號、timestamp、SSRC 是否合理；播放層看補洞、jitter buffer 延遲、frame 解碼數與凍結。三層的數字分開看，才不會把「晚到」當成「頻寬不夠」，把「DTX 靜音」當成「丟包」。

## 34.14 動手練習

1. **延伸實驗一：支援 padding**（延伸程式）。修改 `build_rtp()`，加入參數 `pad`，讓封包總長補齊到 `pad` 的倍數（設定 P=1，最後一個 byte 寫入補了幾個 byte），並用 `parse_rtp()` 驗證 payload 能正確取回。
   答案要點：補齊的 bytes 數是 `-(len(packet)) % pad`，但至少要 1 個 byte（用來存長度），所以剛好整除時要補一整組 `pad` 個。解析端已經處理 `P=1` 的情況，`payload` 應該和原始資料相同；可以額外 assert 「padding 長度大於 payload 時視為壞封包」。

2. **延伸實驗二：加入時鐘漂移**（延伸程式）。在 `network()` 中讓送出端的時鐘比接收端快 1000 ppm（每個封包的實際送出間隔是 19.98 ms），把 N 改為 3000（一分鐘），比較固定 100 ms 與自適應 buffer 的「buffer 最多」與延遲變化。
   答案要點：送出端每分鐘多送約 60 ms 的媒體，固定深度的 buffer 會越積越多，延遲逐漸增加（若實作上限，就會開始丟棄）；自適應的會以每 20 ms 最多縮 0.5 ms 的速度追上。真實的音效卡漂移通常在數十 ppm 量級，一小時累積下來就有上百毫秒，這就是需要時間伸縮的原因。

3. **手算 RTCP**（手算）。某次 RR 報告：上次報告以來預期 400 個封包、收到 391 個；fraction lost 是多少？如果送出端在 NTP 時刻 0x0000_5A00.8000_0000 送出 SR，接收端報告 DLSR＝0x0000_4000，送出端在 0x0000_5A01.0000_0000 收到 RR，RTT 是多少？
   答案要點：fraction lost＝floor(9 × 256 ÷ 400)＝5，約 2%。LSR 取 SR 時刻的中間 32 bit：0x5A00_8000；收到時刻的中間 32 bit：0x5A01_0000；兩者相差 0x8000＝32768，即 0.5 秒；DLSR 0x4000＝16384，即 0.25 秒；RTT＝0.5 − 0.25＝0.25 秒，也就是 250 ms。

4. **用 ffprobe 看 GOP**（真實工具）。找一段手機錄的影片與一段從串流平台下載的影片，用 34.12 節的 `ffprobe -show_entries frame=pict_type` 指令列出前 300 個 frame 的類型，數出 GOP 長度與是否有 B frame。
   答案要點：手機錄影通常沒有或很少 B frame、keyframe 間隔約 1 秒；串流平台的轉碼輸出多半有 B frame（看到 `IBBP…` 的樣式），keyframe 間隔固定（例如每 2 秒），方便切 segment。同時看 `format_name` 與 `codec_name`，練習分清 container 與 codec。

5. **觀察真實通話的 jitter buffer**（真實工具）。和朋友用瀏覽器開一通 WebRTC 視訊（例如任何以 WebRTC 實作的視訊會議網頁），打開 `chrome://webrtc-internals`，找到音訊的 `inbound-rtp`，觀察 `jitter`、jitter buffer 延遲與補洞樣本數的圖表；然後把其中一方從 Wi-Fi 切到手機熱點，再觀察一次。
   答案要點：在穩定的 Wi-Fi 上，jitter 通常只有個位數毫秒，jitter buffer 延遲維持在數十毫秒；換到行動網路後 jitter 變大，jitter buffer 延遲會在幾秒內上升，補洞樣本數在切換的瞬間會跳一下。這就是自適應 buffer 實際運作的樣子，和實驗二的「自適應」一列吻合。

## 本章重點整理

- 聲音以取樣率、位元深度與聲道數字化，48 kHz、16 bit 單聲道的 PCM 是 768 kbps；codec 一次壓縮一個音訊 frame（例如 20 ms 的 960 個樣本），這也是 RTP timestamp 每包加 960 的由來。
- 視訊以解析度、frame rate 與 YUV 4:2:0 色度取樣描述，720p30 的原始畫面約 332 Mbps，壓縮到 1.5 Mbps 靠的是空間與時間上的預測加上量化。
- I frame 可單獨解碼、P frame 參考之前、B frame 參考前後；B frame 省 bitrate 但增加延遲，所以即時通話不用。從一個 keyframe 到下一個是 GOP，參考鏈上的 frame 遺失會讓錯誤延續到下一個 keyframe。
- codec 決定怎麼壓縮，container 決定怎麼把多條串流與時間資訊包在一起；同一段 H.264 可以裝進 MP4、MPEG-TS 或依 RTP payload format 切成封包，Annex B 與 AVCC 的差別是轉封裝最常見的坑。
- WebRTC 瀏覽器必須支援 VP8、H.264 Constrained Baseline、Opus 與 G.711；AV1、HEVC 等的支援依瀏覽器與硬體而定，必須在 runtime 偵測。
- Bitrate 是頻寬，解析度與 frame rate 決定每個像素分到多少 bit；頻寬不足與 jitter 太大是兩種不同的問題，降解析度救不了 jitter。
- 單向延遲由擷取、前處理、編碼、打包、網路、jitter buffer、解碼與播放組成；在路徑固定時，jitter buffer 是唯一能大幅調整、也是刻意加入的延遲。
- 即時媒體跑在 UDP 上，因為晚到的資料沒有用；RTP 只負責標記序號、媒體時間、payload type 與來源，不重傳也不保證順序。
- RTP header 固定 12 bytes：V、P、X、CC、M、PT、16 bit sequence、32 bit timestamp、SSRC，以及 mixer 才用的 CSRC；視訊的 M 標示 frame 的最後一包，音訊的 M 標示靜音後的第一包。
- Timestamp 的單位是 codec 的時鐘頻率（視訊 90 kHz、Opus 48 kHz），同一 frame 的封包 timestamp 相同；序號與 timestamp 都會回繞，比較時要用差值，遺失只看序號。
- RTCP SR 提供 NTP 與 RTP timestamp 的對照點，用於唇音同步與計算 RTT（A − LSR − DLSR）；RR 的 report block 報告 fraction lost、cumulative lost、延伸序號與 interarrival jitter。
- RFC 3550 的 interarrival jitter 是相鄰封包傳輸時間差的 1/16 平滑平均，對尖峰不敏感；jitter buffer 的深度要看延遲分布的尾端，通常是 jitter 數值的好幾倍。
- Jitter buffer 用延遲換流暢：晚於播放時刻抵達的封包等同遺失，而且不會出現在 RTCP 的遺失統計裡；自適應 buffer 搭配時間伸縮，能同時應付網路變化與時鐘漂移。

## 延伸問答

> [!question]- Q1. 同事說：「這個 .mp4 在舊播放器上有畫面沒聲音，檔案一定壞了。」你會怎麼判斷？
> 先分清 container 與 codec。`.mp4` 只說明了 container 是 ISO BMFF 家族，裡面的音訊可能是 AAC，也可能是 Opus、AC-3 或其他 codec。舊播放器能解析 MP4 的結構、找到視訊軌並播放 H.264，卻不認得音訊軌的 codec 時，就會出現「有畫面沒聲音」，檔案本身完全正常。WebRTC 錄下來的檔案常見這種情況，因為 WebRTC 的音訊幾乎都是 Opus。
>
> 確認方法是用 ffprobe 列出每條 stream 的 `codec_name`，或在瀏覽器用 `MediaSource.isTypeSupported('audio/mp4; codecs="opus"')` 測試。修法依目標而定：若要給最多播放器播，轉碼成 AAC；若主要在瀏覽器播放，可以改用 WebM 封裝。這個判斷流程的重點是：副檔名只描述 container，codec 要看檔案內部的資訊，相容性問題多半出在 codec 而不是 container。

> [!question]- Q2. 手算：Opus 20 ms 一包，四個封包的抵達時間依序是 100、121、139、162 ms（以第一包的送出為 0 起算），計算每一步的 RFC 3550 interarrival jitter（以毫秒表示）。
> 送出時刻依序是 0、20、40、60 ms，相對傳輸時間是抵達減送出：100、101、99、102 ms。相鄰差值的絕對值是 |101 − 100|＝1、|99 − 101|＝2、|102 − 99|＝3。
>
> 依公式 J ← J ＋ (|D| − J)／16：第一包之後 J＝0；第二包 J＝0 ＋ (1 − 0)／16＝0.0625；第三包 J＝0.0625 ＋ (2 − 0.0625)／16≈0.184；第四包 J＝0.184 ＋ (3 − 0.184)／16≈0.36 ms。真實的 RR 會用 tick 回報：0.36 ms × 48≈17 tick。這題也說明了 jitter 的特性：雖然每次的變動有 1～3 ms，J 只緩慢上升，需要相當多的封包才會收斂到變動的平均水準；遇到單次 100 ms 的尖峰，J 也只會跳約 6 ms，所以不能直接拿它決定 buffer 深度。

> [!question]- Q3. 你在 production 看到某堂課的 RTCP 遺失只有 0.2%、RTT 60 ms，但學生抱怨聲音一直斷。你會從哪裡查起？
> 這組數字說明「封包幾乎都到了，路徑也不遠」，所以先懷疑「到了但太晚到」。RTCP 的遺失是預期數減收到數，晚到後被 jitter buffer 丟棄的封包算在收到裡，所以不會出現在遺失統計。第一步是看接收端的播放統計：`getStats()` 的補洞樣本比例與平均 jitter buffer 延遲。如果補洞比例遠高於 0.2%，而 buffer 延遲又很低（例如二十幾毫秒），就是 buffer 太淺。
>
> 第二步是確認有沒有人改過設定：例如 App 的「低延遲模式」、jitter buffer 上限、或某個實驗旗標。第三步是看網路的延遲分布，例如抓包看 Max Delta，或接收端的 jitter 曲線，確認學生的網路是不是行動網路、在特定時段抖動。修法是讓 jitter buffer 恢復自適應，只調整目標下限。不要先降解析度：聲音封包很小，頻寬不是問題；降解析度只會讓畫面變差而聲音照樣斷。

> [!question]- Q4. 面試題：RTP 已經有 sequence number，為什麼還需要 timestamp？反過來，只有 timestamp 夠不夠？
> 兩者回答不同的問題。sequence number 描述「傳輸順序」：每送一個封包加 1，用來偵測遺失、亂序與重複，並在 jitter buffer 中排序。timestamp 描述「媒體時間」：這個封包的內容屬於哪一個取樣時刻，用來決定什麼時候播放、計算 jitter，並透過 RTCP SR 和其他串流同步。
>
> 只有 timestamp 不夠，因為同一張視訊 frame 切成好幾個封包時 timestamp 完全相同，沒辦法知道其中哪一包遺失；音訊在 DTX 靜音期間 timestamp 會跳躍，沒辦法分辨「跳躍是靜音還是遺失」。只有 sequence 也不夠，因為封包與媒體時間沒有固定對應：一包可能是 20 ms 的聲音，也可能是一張 frame 的六分之一，靜音時更是完全不送，接收端無從得知何時該播。所以兩個欄位缺一不可：序號管「有沒有到齊」，timestamp 管「何時該播」。

> [!question]- Q5. 為什麼 WebRTC 通常不用 B frame，HLS 直播的轉碼輸出卻常用？
> B frame 同時參考前面與後面的畫面，編碼器必須先拍好並編好「後面」那張 P frame，才能編中間的 B frame，解碼端也要先收到後面的畫面才能解碼並顯示 B。所以每用一張 B frame，編解碼兩端都要多等至少一個 frame 間隔，30 fps 下就是 33 ms 以上，而且傳送順序與顯示順序不同，需要 PTS／DTS 分開記錄。好處是 B frame 很小，同畫質下能省下可觀的 bitrate。
>
> 對 WebRTC 來說，整個單向延遲預算只有一兩百毫秒，多出幾十毫秒的延遲很昂貴，而且 B frame 讓遺失恢復更複雜；用 Constrained Baseline 或關掉 B frame 是合理的選擇。HLS 直播的觀眾本來就落後好幾秒，多 100 ms 毫無感覺，但面對上千名觀眾，每省 10% bitrate 就是 CDN 費用與弱網觀眾體驗的實質改善。這是同一個機制在不同延遲預算下得到相反結論的典型例子。

> [!question]- Q6. 看封包：一條音訊串流連續五個封包的序號是 812、813、814、815、816，timestamp 依序是 0、960、1920、13440、14400，第四個封包 M=1。發生了什麼？
> 序號完全連續，所以沒有任何封包遺失。timestamp 在 814 到 815 之間從 1920 跳到 13440，差了 11520 tick，以 48 kHz 換算是 240 ms，扣掉正常的 20 ms，代表中間有 220 ms 的媒體時間沒有送任何封包。第四個封包 M=1，依音訊的慣例代表「一段靜音之後的第一個封包」。合起來的解讀是：講者停頓了約 220 ms，送出端開啟了 DTX，靜音期間不送封包，恢復說話時標記 M。
>
> 接收端的正確處理是：播放靜音或舒適噪音，不啟動 PLC，並可以趁這段靜音調整 jitter buffer 深度。分析工具若用 timestamp 跳躍計算遺失，會誤報 11 個封包遺失；正確做法是遺失只看序號。反過來，如果序號跳號而 timestamp 正常前進，才是真正的遺失。

> [!question]- Q7. 設計取捨：聲聲 Live 的一對一課與千人講座，jitter buffer 策略應該一樣嗎？
> 不應該，因為兩者的延遲預算差了一個數量級。一對一課是雙向對話，單向延遲超過約 250 ms 就會搶話，所以 jitter buffer 要盡量淺，並使用自適應策略隨網路變化；寧可偶爾補洞，也不能讓延遲變大。視訊還要考慮 RTT：同區域的學生 NACK 重送來得及，可以稍微加深視訊的 buffer 等重送；遠方的學生則以 PLI 請求 keyframe 為主。
>
> 千人講座是單向收看，觀眾能接受數秒延遲，第 38 章的 LL-HLS 播放器緩衝數秒是正常的；即使用 WHEP 觀看，也可以讓 buffer 比對話時深得多，換取幾乎不卡頓，並有時間做重傳。另一個差別是規模：講座的觀眾網路千差萬別，buffer 策略必須在每個觀眾端自行調整，伺服器端無法一體適用。結論是：同一套 jitter buffer 元件，依「互動或單向」設定不同的目標延遲下限與上限。

> [!question]- Q8. 學生所在的公司網路擋掉 UDP，WebRTC 只能透過 TURN over TCP 連線。jitter buffer 會看到什麼變化？
> 媒體仍是 RTP，但承載它的 TCP 會依序、可靠地遞送，遺失的 segment 要重傳成功後，後面的資料才能交給應用程式。對 jitter buffer 來說，這代表兩件事：第一，「遺失」幾乎消失了，因為 TCP 會把每個封包都補回來；第二，每次遺失都變成一段延遲尖峰，重傳期間後面所有封包卡在核心裡，重傳完成後一口氣湧出，抵達時間呈現「停頓後爆量」的樣子。
>
> 所以 interarrival jitter 與延遲尾端會明顯變大，自適應 buffer 會被迫加深，延遲上升；若 buffer 不夠深，那些「最終送達但太晚」的封包照樣被丟棄，RTCP 看起來零遺失，使用者卻聽到斷續。這正是本章「晚到等於遺失」的極端版本，也是即時媒體不用 TCP 的理由：TCP 用延遲換可靠，而即時媒體寧可用遺失換延遲。實務上，TURN over TCP 或 TLS 是讓通話「能通」的最後手段，ICE 會優先選 UDP（第 36 章）。

## 延伸閱讀

- RFC 3550〈RTP: A Transport Protocol for Real-Time Applications〉：RTP 與 RTCP 的規格，附錄 A 有延伸序號、遺失與 jitter 計算的參考程式
- RFC 3551〈RTP Profile for Audio and Video Conferences with Minimal Control〉：靜態 payload type 與音訊 marker 的慣例
- RFC 7587〈RTP Payload Format for the Opus Speech and Audio Codec〉與 RFC 6184〈RTP Payload Format for H.264 Video〉：兩個最常用 codec 的切包規則
- RFC 8285〈A General Mechanism for RTP Header Extensions〉：one-byte 與 two-byte header extension
- RFC 7742〈WebRTC Video Processing and Codec Requirements〉與 RFC 7874〈WebRTC Audio Codec and Processing Requirements〉：WebRTC 必須支援的 codec
- ITU-T G.114〈One-way transmission time〉：對話延遲的規劃建議
- W3C〈Identifiers for WebRTC's Statistics API〉：`getStats()` 中 inbound-rtp 等統計欄位的定義
- Iain E. Richardson《The H.264 Advanced Video Compression Standard》（第二版）：預測、量化與 GOP 結構的入門
