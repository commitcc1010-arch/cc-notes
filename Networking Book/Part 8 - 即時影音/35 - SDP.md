---
chapter: 35
title: SDP：媒體協商的語言
part: 8
---

# 第 35 章　SDP：媒體協商的語言

> [!abstract] 本章地圖
> **核心問題**：兩個瀏覽器（或瀏覽器與 SFU）在送出第一個影音封包之前，怎麼用一份文字講好「送什麼、怎麼送、送到哪、怎麼加密」？這份文字壞掉時，要怎麼從裡面看出是誰的錯？
>
> **你會學到**：
> - 逐行讀懂一份完整的 WebRTC offer：session 層的 v、o、s、t、BUNDLE，與每個 media section 的 m、c、mid、ICE 帳密、fingerprint、setup、rtcp-mux、rtpmap、fmtp、rtcp-fb、extmap、方向、msid、ssrc 與 sctp-port
> - 說清楚 payload type（PT）只是一場 session 內的暫時編號，為什麼不能在程式裡寫死 `98 = VP9`
> - 依 offer／answer 規則產生合法的 answer：m 行數量與順序不變、codec 取交集並沿用 PT、DTLS 角色選 active 或 passive、方向反轉、用 port 0 拒絕
> - 把 Unified Plan 的 transceiver 對應到 m 行，理解重新協商時 SDP 怎麼變
> - 判斷什麼時候會想做 SDP munging、它會怎麼壞，以及該改用哪些正式 API
> - 用 Python 標準函式庫寫一個 SDP 解析器、answer 產生器與規則驗證器
>
> **前置知識**：第 9 章（UDP 與 port）、第 17 章（雜湊與憑證指紋的概念）、第 32 章（WebSocket，聲聲 Live 的 signaling 走它）、第 34 章（codec、RTP header 的 PT、SSRC 與 timestamp）

## 35.1 故事：老師畫面上那一格黑框

週四晚上八點十五分，聲聲 Live 的小班會話課（課程 8812）已經開始，老師 `teacher05` 在畫面上看到五個學生的格子，其中兩格是黑的。學生的聲音都聽得到，那兩個學生自己的畫面上也看得到老師，只是自己的鏡頭影像沒有送到 SFU。客服在十分鐘內收到十幾張單，全是「老師說看不到我」，而且幾乎都用同一款瀏覽器的新版本。

小晴先看了前端的錯誤監控，沒有任何例外；signaling（交換連線資訊的訊息通道，聲聲 Live 用 `rt.shengsheng.example` 上的 WebSocket，第 32 章）也很正常，offer 送出、answer 回來，前後不到 200 毫秒。負責 WebRTC 的 Joe 打開台北 SFU `sfu-tpe-1`（203.0.113.60）的 log，搜尋其中一個學生 `student-0457` 的連線，找到一行：

```text
2026-10-01T20:14:52+08:00 sfu-60 session=8812/student-0457 mid=1 kind=video
  offer pts=[98] codecs={98: rtx/90000 apt=97} -> no supported primary codec, rejecting m-line (port 0)
```

這行 log 說，學生的 offer 裡，視訊那一段只列了一個 payload type 98，而 98 在這份 offer 裡代表的是 rtx（重傳用的格式），它指向的 97 卻不在列表裡。SFU 找不到任何能解碼的視訊 codec，只好在 answer 裡把這一段的 port 設成 0，意思是「這一段我拒絕」。學生的瀏覽器收到 answer 之後，乖乖地停掉了這個視訊的傳送，沒有報錯，因為一切都符合規格。

```text
 學生瀏覽器（student-0457）                      rt.shengsheng.example            SFU 203.0.113.60
   │ createOffer()                                  （signaling，WebSocket）
   │ 前端 munging：m=video 只留下 98 ← 以為 98 是 VP9
   │──── offer（m=video 9 UDP/TLS/RTP/SAVPF 98）─────────►│──────────────────────►│
   │                                                      │   98 = rtx，apt=97 不在 m 行
   │                                                      │   → 沒有可用的 codec
   │◄─── answer（m=video 0 UDP/TLS/RTP/SAVPF 98）─────────│◄──────────────────────│
   │ 視訊 transceiver 被停用：鏡頭不送了                                      
   │═══════════ 音訊照常（mid=0 協商成功）══════════════════════════════════════►│ ──► 老師聽得到
   │            視訊沒有送出（mid=1 被拒絕）                                      ──► 老師看到黑框
```

這張圖由上往下讀。前端上週為了在小班課節省頻寬，寫了一段「強制使用 VP9」的程式：在 `createOffer()` 產生的 SDP 送出之前，用 regex 把 `m=video` 那一行的 codec 清單改成只剩 `98`，因為開發者在自己的瀏覽器上看到 `a=rtpmap:98 VP9/90000`。這種「手動改 SDP 文字」的做法叫 **SDP munging**。問題是 98 這個數字沒有任何全域意義：它只是**這一份 SDP 裡**暫時指派給某個 codec 的編號，換一個瀏覽器、甚至同一個瀏覽器換一個版本，98 就可能指向別的東西。那兩位學生用的瀏覽器新版本調整了 codec 清單，98 變成了 H.264 的 rtx。

Joe 把一份正常的 offer 和一份壞掉的 offer 並排貼在頻道裡，對小晴說：「SDP 就是兩邊講好要怎麼傳影音的契約。看得懂它，這種問題五分鐘就能找到；看不懂，就只能猜是網路還是鏡頭。」那一份正常的 offer 有八十多行，小晴第一眼只認得 `VP8` 和 `opus` 兩個字。

這一章就從那份八十多行的 offer 開始，一行一行讀懂它。讀完以後，你會知道 PT 為什麼只能靠 `a=rtpmap` 查、answer 為什麼不能刪掉 m 行、`port 0` 代表什麼、fingerprint 為什麼一定要在，以及前端想「調整 codec」時應該用哪個 API 而不是改字串。章末的動手做會用 Python 寫出 SFU 那一端：解析 offer、依能力產生 answer，再用一組規則驗證它，連故事裡的錯誤也能被抓出來。

## 35.2 SDP 是什麼：一份「我能做什麼」的清單

建立一通視訊通話之前，兩端要先講好一大堆細節：要傳幾路媒體（音訊、鏡頭、分享畫面、資料）、每一路用哪個 codec、codec 的參數（例如 H.264 的 profile）、RTP 封包裡的 payload type 編號各代表什麼、要不要回報丟包、媒體從哪個位址和 port 收送、加密的金鑰怎麼交換、誰當 DTLS 的 client。這些資訊必須在第一個媒體封包之前就交換完，而且雙方要有共同的格式來描述。

**SDP**（Session Description Protocol，會話描述協定）就是這個格式。名字裡雖然有 Protocol，它其實不負責傳輸任何東西，只是一種**文字格式**，用來描述一場多媒體會話；現行規格是 RFC 8866（取代了沿用多年的 RFC 4566）。SDP 最早用在 SIP 網路電話與 RTSP 串流，WebRTC 沿用它，再由 **JSEP**（JavaScript Session Establishment Protocol，RFC 9429）規定瀏覽器要怎麼產生、解讀 SDP。舉例來說，學生的瀏覽器呼叫 `pc.createOffer()`，拿到的 `offer.sdp` 就是一個 SDP 字串；聲聲 Live 的前端把它包成 JSON，經 WebSocket 送到 SFU。

SDP 怎麼送不在 WebRTC 規格內，這件事很重要。第 36 章會再強調一次：**signaling**（信令，交換 SDP 與 ICE candidate 的通道）由應用程式自己決定，可以是 WebSocket、HTTP POST（WHIP、WHEP 就是用 HTTP 送 SDP，第 38 章），甚至複製貼上。SDP 只是被搬運的內容，它的完整性與機密性要靠 signaling 通道保護，35.9 節會說明為什麼。

SDP 的語法非常簡單：每一行是 `<type>=<value>`，type 是一個小寫字母，等號前後不能有空白，行尾是 CRLF（`\r\n`）。整份文件分成兩層：最前面是 **session 層**（session-level，對整場會話都有效的設定），接著是一個以上的 **media section**（媒體段，也叫 m 段），每一段從一行 `m=` 開始，到下一行 `m=` 或文件結尾為止。媒體段裡的屬性只對那一段有效；同一個屬性若同時出現在 session 層與媒體段，以媒體段為準。

```text
 ┌──────────────────────────── SDP 文件 ────────────────────────────┐
 │ v=0                                  ┐                           │
 │ o=- 4962303811422586241 2 IN IP4 …   │  session 層               │
 │ s=-                                  │  （整場會話共用）           │
 │ t=0 0                                │                           │
 │ a=group:BUNDLE 0 1 2                 ┘                           │
 ├──────────────────────────────────────────────────────────────────┤
 │ m=audio 9 UDP/TLS/RTP/SAVPF 111 63 0 8 126   ┐ media section #0   │
 │ c=… a=mid:0 a=rtpmap:111 opus/48000/2 …     ┘ （mid 0，音訊）     │
 ├──────────────────────────────────────────────────────────────────┤
 │ m=video 9 UDP/TLS/RTP/SAVPF 96 97 98 …      ┐ media section #1   │
 │ c=… a=mid:1 a=rtpmap:96 VP8/90000 …         ┘ （mid 1，鏡頭）     │
 ├──────────────────────────────────────────────────────────────────┤
 │ m=application 9 UDP/DTLS/SCTP webrtc-datachannel ┐ section #2     │
 │ c=… a=mid:2 a=sctp-port:5000 …                   ┘ （data channel）│
 └──────────────────────────────────────────────────────────────────┘
```

這張圖是本章的骨架。session 層說明「這是哪一場會話、第幾版」與「哪些媒體段共用同一條傳輸」（BUNDLE）；每個 media section 對應一路媒體，在 WebRTC 裡大致就是一個 transceiver（35.8 節）。媒體段的順序有意義：answer 必須照同樣的順序與數量回覆（35.7 節）。

SDP 規格定義的 type 字母不少，但 WebRTC 只用到其中幾個，而且大部分資訊都塞在 `a=`（attribute，屬性）裡。下表列出規格中的行與它們在 WebRTC 的實際用途：

| 行 | 名稱 | 規格裡的意思 | 在 WebRTC 的用法 |
|---|---|---|---|
| `v=` | version | SDP 版本，永遠是 0 | 固定 `v=0`，必須是第一行 |
| `o=` | origin | 建立者、session id、版本號、位址 | 版本號每次重新協商要遞增；位址無意義 |
| `s=` | session name | 會話名稱 | 固定 `s=-` |
| `i=`、`u=`、`e=`、`p=` | 說明、URI、email、電話 | 給人看的資訊 | 不使用 |
| `c=` | connection | 媒體的網路位址 | 多半是佔位值 `IN IP4 0.0.0.0`，真正的位址看 ICE candidate |
| `b=` | bandwidth | 頻寬上限（`AS` 單位 kbps、`TIAS` 單位 bps） | 可選；常被 munging 用來限速 |
| `t=` | timing | 會話開始與結束時間 | 固定 `t=0 0`（不限時間） |
| `m=` | media | 媒體種類、port、傳輸協定、格式清單 | 每一路媒體一行，開啟一個 media section |
| `a=` | attribute | 各種屬性 | 幾乎所有協商內容都在這裡 |

表中最值得注意的是 `c=` 那一列。傳統 SIP 電話用 `c=` 與 `m=` 的 port 告訴對方「把媒體送到這個位址」，但在 NAT 普遍存在的網路裡，自己知道的位址往往不是對方能連到的位址（第 7 章）。WebRTC 改用 ICE 收集多個候選位址（candidate），一個一個測試（第 36 章），所以 `c=` 與 m 行的 port 在 WebRTC 裡大多只是佔位值，例如 port 9（discard 服務的 port，代表「這裡沒有真正的資料」）與位址 0.0.0.0。

## 35.3 一份完整的 offer：session 層

以下是本章要逐行解讀的 offer。它模仿瀏覽器 `createOffer()` 的輸出，由學生 `student-0457` 的瀏覽器產生，要送給 SFU；為了好讀，刪掉了一些和本章無關的行（例如 `a=rtcp:9 IN IP4 0.0.0.0` 這種舊式的 RTCP 位址行、以 http 開頭的實驗性 header extension），PT 編號與排列也是本書自己的範例，不代表任何特定瀏覽器版本。左邊的行號是為了解說方便加上的，不屬於 SDP。

```text
 1  v=0
 2  o=- 4962303811422586241 2 IN IP4 127.0.0.1
 3  s=-
 4  t=0 0
 5  a=group:BUNDLE 0 1 2
 6  a=extmap-allow-mixed
 7  a=msid-semantic: WMS
 8  m=audio 9 UDP/TLS/RTP/SAVPF 111 63 0 8 126
 9  c=IN IP4 0.0.0.0
10  a=ice-ufrag:Qx7v
11  a=ice-pwd:5KfLr2xT0aJp9wQe3VbN8sYd
12  a=ice-options:trickle
13  a=fingerprint:sha-256 9F:4B:11:5E:E2:C3:21:BF:FF:4F:0D:85:6C:C6:BD:11:1D:F1:91:7F:BB:E6:A0:DF:FE:94:60:49:83:3E:43:37
14  a=setup:actpass
15  a=mid:0
16  a=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level
17  a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid
18  a=sendrecv
19  a=msid:cam-0457 mic-track
20  a=rtcp-mux
21  a=rtpmap:111 opus/48000/2
22  a=rtcp-fb:111 transport-cc
23  a=fmtp:111 minptime=10;useinbandfec=1
24  a=rtpmap:63 red/48000/2
25  a=fmtp:63 111/111
26  a=rtpmap:0 PCMU/8000
27  a=rtpmap:8 PCMA/8000
28  a=rtpmap:126 telephone-event/8000
29  a=ssrc:1711239020 cname:k3VfQm8Zr0aD2xLp
30  m=video 9 UDP/TLS/RTP/SAVPF 96 97 98 99 102 103 45 46
31  c=IN IP4 0.0.0.0
32  a=ice-ufrag:Qx7v
33  a=ice-pwd:5KfLr2xT0aJp9wQe3VbN8sYd
34  a=ice-options:trickle
35  a=fingerprint:sha-256 9F:4B:11:5E:E2:C3:21:BF:FF:4F:0D:85:6C:C6:BD:11:1D:F1:91:7F:BB:E6:A0:DF:FE:94:60:49:83:3E:43:37
36  a=setup:actpass
37  a=mid:1
38  a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid
39  a=extmap:10 urn:ietf:params:rtp-hdrext:sdes:rtp-stream-id
40  a=sendrecv
41  a=msid:cam-0457 cam-track
42  a=rtcp-mux
43  a=rtcp-rsize
44  a=rtpmap:96 VP8/90000
45  a=rtcp-fb:96 transport-cc
46  a=rtcp-fb:96 ccm fir
47  a=rtcp-fb:96 nack
48  a=rtcp-fb:96 nack pli
49  a=rtpmap:97 rtx/90000
50  a=fmtp:97 apt=96
51  a=rtpmap:98 VP9/90000
52  a=rtcp-fb:98 transport-cc
53  a=rtcp-fb:98 ccm fir
54  a=rtcp-fb:98 nack
55  a=rtcp-fb:98 nack pli
56  a=fmtp:98 profile-id=0
57  a=rtpmap:99 rtx/90000
58  a=fmtp:99 apt=98
59  a=rtpmap:102 H264/90000
60  a=rtcp-fb:102 transport-cc
61  a=rtcp-fb:102 ccm fir
62  a=rtcp-fb:102 nack
63  a=rtcp-fb:102 nack pli
64  a=fmtp:102 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f
65  a=rtpmap:103 rtx/90000
66  a=fmtp:103 apt=102
67  a=rtpmap:45 AV1/90000
68  a=rtcp-fb:45 transport-cc
69  a=rtcp-fb:45 ccm fir
70  a=rtcp-fb:45 nack
71  a=rtcp-fb:45 nack pli
72  a=rtpmap:46 rtx/90000
73  a=fmtp:46 apt=45
74  a=ssrc-group:FID 2231627014 3990415873
75  a=ssrc:2231627014 cname:k3VfQm8Zr0aD2xLp
76  a=ssrc:3990415873 cname:k3VfQm8Zr0aD2xLp
77  m=application 9 UDP/DTLS/SCTP webrtc-datachannel
78  c=IN IP4 0.0.0.0
79  a=ice-ufrag:Qx7v
80  a=ice-pwd:5KfLr2xT0aJp9wQe3VbN8sYd
81  a=ice-options:trickle
82  a=fingerprint:sha-256 9F:4B:11:5E:E2:C3:21:BF:FF:4F:0D:85:6C:C6:BD:11:1D:F1:91:7F:BB:E6:A0:DF:FE:94:60:49:83:3E:43:37
83  a=setup:actpass
84  a=mid:2
85  a=sctp-port:5000
86  a=max-message-size:262144
```

這份 offer 有三個 media section：第 8 行開始的音訊（mid 0）、第 30 行開始的鏡頭視訊（mid 1）、第 77 行開始的 data channel（mid 2）。三段裡有許多重複的行（ICE 帳密、fingerprint、setup），這是因為 SDP 允許每一段各自使用不同的傳輸；雖然 BUNDLE 之後它們實際上共用同一條，規格仍要求每段都寫一次。接下來先讀前 7 行的 session 層。

**第 1 行 `v=0`**：SDP 的版本，從 1998 年至今一直是 0。它必須是整份文件的第一行，解析器常用它判斷「這是不是 SDP」。

**第 2 行 `o=`**（origin）：格式是 `o=<username> <sess-id> <sess-version> <nettype> <addrtype> <unicast-address>`。username 用 `-` 表示不提供；`4962303811422586241` 是 **session id**，一場會話從頭到尾不變；`2` 是 **session version**，每次重新協商、SDP 內容有改變時要遞增，對方靠它判斷「這是新的描述，還是重送的舊描述」。`IN IP4 127.0.0.1` 是建立者的位址，瀏覽器為了不洩漏真實 IP，一律填 127.0.0.1 這類無意義的值。故事裡的前端如果在重新協商時重複送出同一份 SDP，版本號不變，對方可以安全地把它當成沒有變化。

**第 3 行 `s=-`**：session name，規格要求一定要有，WebRTC 一律填 `-`。

**第 4 行 `t=0 0`**：會話的開始與結束時間（NTP 秒數），兩個 0 代表「不限時間」，是 SDP 早年公告多播節目時代的痕跡。

**第 5 行 `a=group:BUNDLE 0 1 2`**：這行宣告 mid 0、1、2 三個 media section 要「綁在一起」，共用同一條傳輸（同一組 ICE candidate、同一個 DTLS 連線、同一個 UDP 五元組）。沒有 BUNDLE 的年代，每一路媒體各自要一個 port、各自做 ICE 與 DTLS，一通有音訊、視訊、data channel 的通話要建立三條傳輸；BUNDLE（現行規格 RFC 9143）讓它們只建一條，連線更快、穿越 NAT 的成功率更高、TURN 中繼的配額也只用一份。BUNDLE 群組的第一個 mid 叫 **tagged m 段**，在 answer 裡，這一段的傳輸參數就代表整個群組。

**第 6 行 `a=extmap-allow-mixed`**：允許同一個 RTP 串流混用一 byte 與兩 byte 兩種 header extension 格式（RTP header extension 是附在 RTP header 後面的額外欄位，35.6 節）。一 byte 格式的 ID 只能是 1 到 14，擴充欄位一多就需要兩 byte 格式。

**第 7 行 `a=msid-semantic: WMS`**：WMS 是 WebRTC Media Stream 的縮寫。這行是早期草案留下的遺跡：舊版的 msid 機制要在這裡列出所有 stream id，現行的 msid 規格（RFC 8830）已經不需要它，但瀏覽器為了和舊實作相容仍然會送。解析時可以忽略，產生 answer 時照抄也無妨。

## 35.4 m 行與傳輸參數：媒體要怎麼送、怎麼加密

一個 media section 的前半段多半在描述「傳輸」：用什麼協定、怎麼找到對方、怎麼驗證對方、怎麼加密。這些屬性分別交給 ICE、DTLS 與 RTP 三個元件使用。先看第 8 行的 m 行本身。

**第 8 行 `m=audio 9 UDP/TLS/RTP/SAVPF 111 63 0 8 126`**：格式是 `m=<media> <port> <proto> <fmt> …`。media 是 `audio`、`video` 或 `application`；port 9 是佔位值；proto 是傳輸協定的完整名稱，要從右往左讀：**SAVPF** 是「Secure Audio Video Profile with Feedback」，表示 RTP 用 SRTP 加密（S）並支援 RTCP 回饋訊息（F，例如回報丟包，RFC 4585）；`RTP` 表示媒體用 RTP 封裝；`TLS` 在這裡指 DTLS，表示 SRTP 的金鑰用 DTLS 交握產生（DTLS-SRTP）；最左邊的 `UDP` 是底層傳輸。後面的數字是這一段願意使用的 **payload type** 清單，**順序代表偏好**，第一個最想用，35.5 節會逐一對應。

**第 9 行 `c=IN IP4 0.0.0.0`**：connection data，格式是網路類型（IN 代表 Internet）、位址類型、位址。和 port 9 一樣是佔位值；JSEP 規定還沒收集到 candidate 時就這樣填，真正的位址以 `a=candidate` 為準。

**第 10、11 行 `a=ice-ufrag`、`a=ice-pwd`**：ICE 的使用者名稱片段與密碼。ICE 連線檢查時，每個 STUN binding request 的 USERNAME 欄位由「對方的 ufrag:自己的 ufrag」組成，訊息再用對方的 ice-pwd 計算 HMAC（MESSAGE-INTEGRITY），讓雙方確認回應真的來自這場協商的對象，而不是任何剛好收到封包的主機（第 36 章）。規格要求 ufrag 至少 4 個字元、pwd 至少 22 個字元，並且是隨機產生的。ice-pwd 是一個密鑰，不應該出現在一般 log 或錯誤回報裡。

**第 12 行 `a=ice-options:trickle`**：宣告支援 **trickle ICE**：candidate 可以在 SDP 交換之後一個一個補送，不必等全部收集完。這份 offer 裡一個 `a=candidate` 都沒有，就是因為 candidate 會透過 signaling 另外送。

**第 13 行 `a=fingerprint:sha-256 9F:4B:…`**：本端 DTLS 憑證的 SHA-256 雜湊值。WebRTC 的 DTLS 憑證通常是瀏覽器自己產生的自簽憑證，沒有任何 CA 能證明它屬於誰；信任的根據就是這行指紋：DTLS 交握時，對方會計算收到的憑證的雜湊，和 SDP 裡的 fingerprint 比對，不一致就中止連線。換句話說，「SDP 有沒有被竄改」直接決定了加密是不是能擋住中間人，這也是 signaling 必須走 TLS 而且要驗證身分的原因。

**第 14 行 `a=setup:actpass`**：決定 DTLS 交握裡誰當 client。**active** 表示「我主動送 ClientHello，當 DTLS client」，**passive** 表示「我等對方來，當 DTLS server」，**actpass** 表示「兩者皆可，讓你選」。規則很簡單：offer 必須是 actpass，answer 只能選 active 或 passive。

| offer 的 setup | answer 可以選 | 結果：誰送 ClientHello |
|---|---|---|
| `actpass` | `active` | answerer 當 DTLS client |
| `actpass` | `passive` | offerer 當 DTLS client |
| `active`（部分舊實作） | `passive` | offerer 當 DTLS client |
| `passive` | `active` | answerer 當 DTLS client |
| 任何值 | `actpass` | 不合法，answer 不能把選擇丟回去 |

瀏覽器當 answerer 時預設回 `active`；本章的 SFU 範例則回 `passive`，讓學生的瀏覽器當 DTLS client。兩種都合法，重要的是兩端要一個 active、一個 passive。重新協商時，如果傳輸沒有重建，DTLS 角色應該維持不變；如果 answer 硬把角色對調，等於要求重做 DTLS，實作不一致時就會出現「重新協商後媒體中斷」的問題。

**第 15 行 `a=mid:0`**：media identification，這一段的識別字。mid 是 BUNDLE 群組、transceiver 對應與 RTP 封包分流的依據，在一場會話裡必須唯一；answer 的每一段必須帶著和 offer 相同的 mid。

**第 20 行 `a=rtcp-mux`**：RTP 與 RTCP（RTP 的控制協定，送接收報告、丟包回饋等，第 34 章）共用同一個 port。早期 RTP 規定 RTCP 用「RTP port＋1」，每一路媒體要佔兩個 port、做兩次 ICE；WebRTC 要求 rtcp-mux，瀏覽器預設的 `rtcpMuxPolicy` 就是 `require`。共用 port 之後，接收端要靠封包第二個 byte 的數值範圍分辨 RTP 與 RTCP，這帶來一個限制：RTP 的 PT 不能用 64 到 95，原因在 35.6 節的分流圖。

**第 43 行 `a=rtcp-rsize`**：允許送「精簡版 RTCP」（reduced-size RTCP），也就是單獨送一個回饋訊息，不必每次都附上完整的接收報告。視訊的 NACK、PLI 回饋很頻繁，用精簡格式可以省頻寬。

這些傳輸屬性各自交給不同的元件。下圖把它們分到 WebRTC 堆疊的三層，對照第 36 章的連線流程：

```text
                    SDP 屬性                         交給誰           用來做什麼
 ┌───────────────────────────────────────┐
 │ a=ice-ufrag / a=ice-pwd                │ ──►  ICE agent   ──► STUN 連線檢查的帳號與 HMAC 金鑰
 │ a=ice-options:trickle / a=candidate    │ ──►  ICE agent   ──► 候選位址與補送方式
 ├───────────────────────────────────────┤
 │ a=fingerprint:sha-256 …                │ ──►  DTLS        ──► 驗證對方的自簽憑證
 │ a=setup:actpass|active|passive         │ ──►  DTLS        ──► 決定誰送 ClientHello
 ├───────────────────────────────────────┤
 │ a=group:BUNDLE / a=mid                 │ ──►  RTP 分流器  ──► 一條傳輸上分出各個 m 段
 │ a=rtcp-mux / a=rtcp-rsize              │ ──►  RTP/RTCP    ──► RTCP 與 RTP 共用 port、精簡回饋
 │ a=rtpmap / a=fmtp / a=rtcp-fb / extmap │ ──►  RTP 與 codec ──► 封包怎麼解、codec 怎麼設
 └───────────────────────────────────────┘
          所有三層都建在同一個 UDP 五元組上（BUNDLE 之後）
```

由上往下看：ICE 用 ufrag／pwd 與 candidate 找出一條能通的 UDP 路徑；DTLS 在這條路徑上交握，用 fingerprint 驗證對方、用 setup 決定角色，交握完成後導出 SRTP 金鑰；最後 RTP 層靠 mid 與 BUNDLE 把同一條路徑上的封包分給各個 media section，靠 rtpmap 等屬性決定怎麼解碼。任何一層的屬性缺了或錯了，症狀都不一樣：ICE 帳密錯是「連不上」，fingerprint 錯是「連上了又斷」，rtpmap 錯則是「連上了但沒有畫面」，故事裡的情況屬於最後一種。

## 35.5 Codec 的描述：PT、rtpmap、fmtp 與 rtcp-fb

m 行最後那串數字（第 8 行的 `111 63 0 8 126`）是 **payload type**（PT，酬載型別）。第 34 章看過 RTP header：第二個 byte 的低 7 bit 就是 PT，接收端看到一個 RTP 封包時，只能靠這 7 個 bit 判斷「這是什麼格式的資料、要交給哪個解碼器」。

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───┬─┬─┬───────┬─┬─────────────┬───────────────────────────────┐
 │V=2│P│X│  CC   │M│   PT (7)    │       Sequence Number         │  bytes 0-3
 ├───┴─┴─┴───────┴─┴─────────────┴───────────────────────────────┤
 │                         Timestamp                             │  bytes 4-7
 ├───────────────────────────────────────────────────────────────┤
 │                           SSRC                                │  bytes 8-11
 └───────────────────────────────────────────────────────────────┘
                     ▲
                     │ PT=96 是什麼？RTP header 不知道，要查 SDP：
                     │   a=rtpmap:96 VP8/90000        → 交給 VP8 解碼器，時鐘 90 kHz
                     │   a=rtcp-fb:96 nack pli        → 遺失時可以要求重送、要求關鍵畫面
                     │   a=fmtp:97 apt=96             → PT 97 是 96 的重傳封包
```

這張圖說明了 SDP 與 RTP 的分工。RTP header 只有 7 bit 的 PT，沒有地方寫「VP8」這種名字；名字、時鐘頻率、聲道數與 codec 參數全都放在 SDP 裡，雙方在協商時建立一張「PT 到格式」的對照表，之後每個 RTP 封包只要帶一個小數字。代價是：**這張表只在這一場 session 裡有效**。另一場 session 可以把 96 指給 H.264，完全合法。

PT 分成兩類。0 到 95 之間有一些**靜態 PT**，是 RTP 音視訊 profile（RFC 3551）早年固定指派的，例如 0 是 PCMU、8 是 PCMA、9 是 G.722、13 是 CN（comfort noise，安靜時送的背景雜訊參數）。現代 codec 幾乎都用**動態 PT**：96 到 127 由 SDP 臨時指派；當瀏覽器支援的格式多到 96–127 不夠用時，也會用 35 到 63 這段（它們在 RFC 3551 裡沒有被指派，又避開了 rtcp-mux 會衝突的 64–95），本章 offer 的 AV1 用 45、音訊 RED 用 63 就是這種情況。下表整理這份 offer 裡出現的格式：

| PT | rtpmap | 是什麼 | 備註 |
|---|---|---|---|
| 111 | `opus/48000/2` | Opus 音訊 | Opus 的 RTP 規格規定一律寫 48000 與 2 聲道，不代表實際取樣率或聲道 |
| 63 | `red/48000/2` | RED 冗餘封包 | `fmtp:63 111/111`：每個封包帶兩份 Opus 資料，丟一個還能補 |
| 0、8 | `PCMU/8000`、`PCMA/8000` | G.711 μ-law、A-law | 靜態 PT，和傳統電話網路互通時用 |
| 126 | `telephone-event/8000` | DTMF 按鍵音 | 打電話「按 1 轉客服」的那種訊號 |
| 96、98、102、45 | `VP8`、`VP9`、`H264`、`AV1`（皆 `/90000`） | 視訊 codec | 視訊的 RTP 時鐘一律 90 kHz（第 34 章） |
| 97、99、103、46 | `rtx/90000` | 重傳格式 | `fmtp` 的 `apt` 指出它替哪個 PT 重傳 |

表裡有兩個常讓人困惑的地方。第一，`opus/48000/2` 永遠這樣寫，即使實際只傳單聲道語音，聲道與立體聲的意圖改用 fmtp 的 `stereo` 參數表達；同樣的歷史包袱也出現在 G.722：它的取樣率是 16 kHz，但 SDP 裡寫 `G722/8000`，這是 RFC 3551 留下來、為了相容而不能改的錯誤。第二，**rtx**（RTP retransmission，RFC 4588）不是一個 codec，而是「重送封包」的包裝格式：接收端發現 VP8 的某個封包遺失，用 RTCP NACK 要求重送，發送端就把原封包包成 PT 97 的 rtx 封包，用另一個 SSRC 送出。rtx 本身不能解碼，必須靠 `apt`（associated payload type）找回原本的 codec。故事裡的 offer 只剩一個 rtx 而沒有它的 apt，就是一段「只有重送、沒有本體」的媒體，SFU 理所當然拒絕。

**`a=rtpmap:<pt> <encoding>/<clock rate>[/<channels>]`** 把 PT 對應到格式名稱、RTP 時鐘頻率與聲道數。格式名稱比對時不分大小寫。靜態 PT 理論上可以省略 rtpmap，但 JSEP 要求瀏覽器全部寫出來，解析器也不該假設。

**`a=fmtp:<pt> <參數>`**（format parameters）帶 codec 專屬的參數，內容依 codec 而定，通常是以分號隔開的 `key=value`。第 23 行的 `minptime=10;useinbandfec=1` 表示 Opus 封包最短 10 ms，並啟用 in-band FEC（在下一個封包裡夾帶上一個封包的低品質副本，丟包時用來補）。第 64 行 H.264 的 fmtp 最複雜，也最常造成協商失敗：

- `packetization-mode=1`：H.264 的一個畫面可能大於一個 RTP 封包，mode 1 允許把一個 NAL unit 切成多個封包（FU-A）或把多個小 NAL 合成一個（STAP-A）；mode 0 只能一個 NAL 一個封包。兩端的 mode 必須相同，mode 不同就是不同的格式，瀏覽器常常把同一個 profile 用兩個 PT 各列一次 mode 0 和 mode 1。
- `profile-level-id=42e01f`：三個 byte，依序是 profile_idc、constraint flags、level_idc。profile 決定解碼器要支援哪些工具，必須相容；level 決定解析度與 bitrate 上限。
- `level-asymmetry-allowed=1`：允許兩個方向使用不同的 level，例如手機只能編碼 3.1，但能解碼 4.0。

下面這段程式示範兩件事：同一個 PT 在兩個 session 裡代表不同 codec，以及怎麼把 `profile-level-id` 拆成人看得懂的 profile 與 level。

```python
import struct

# 同一個 PT 編號，在兩個 session 裡可以代表完全不同的 codec：對照表只存在於各自的 SDP
SESSION_A = {96: "VP8/90000", 97: "rtx/90000", 102: "H264/90000", 111: "opus/48000/2"}
SESSION_B = {96: "H264/90000", 97: "rtx/90000", 98: "VP8/90000", 111: "opus/48000/2"}


def rtp_pt(packet: bytes):
    """RTP 第 2 個 byte：最高 1 bit 是 marker，低 7 bit 是 payload type（第 34 章）。"""
    b0, b1, seq, ts, ssrc = struct.unpack("!BBHII", packet[:12])
    assert b0 >> 6 == 2, "不是 RTP version 2"
    return b1 & 0x7F, b1 >> 7, seq, ts, ssrc


def h264_profile(plid: str):
    """profile-level-id = profile_idc、constraint flags（profile-iop）、level_idc 三個 byte。"""
    idc, iop, level = bytes.fromhex(plid)
    names = {66: "Baseline", 77: "Main", 100: "High"}
    name = names.get(idc, f"profile_idc {idc}")
    if idc == 66 and iop & 0x40:  # constraint_set1 打開 = Constrained Baseline
        name = "Constrained Baseline"
    if idc == 100 and iop & 0x0C == 0x0C:  # constraint_set4 與 set5 = Constrained High
        name = "Constrained High"
    return f"{name}，level {level // 10}.{level % 10}"


packet = struct.pack("!BBHII", 0x80, 0x80 | 96, 4711, 3_000_000, 2231627014) + b"\x00" * 20
pt, marker, seq, ts, ssrc = rtp_pt(packet)
print(f"RTP: PT={pt} marker={marker} seq={seq} ts={ts} ssrc={ssrc}")
print(f"  在 session A 解成 {SESSION_A[pt]}，在 session B 解成 {SESSION_B[pt]}")
assert SESSION_A[pt] != SESSION_B[pt]

for plid in ("42e01f", "42001f", "4d001f", "640c1f", "640034"):
    print(f"profile-level-id={plid} → {h264_profile(plid)}")
assert h264_profile("42e01f") == "Constrained Baseline，level 3.1"
assert h264_profile("640c1f") == "Constrained High，level 3.1"

fmtp = "level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f"
params = dict(p.split("=", 1) for p in fmtp.split(";"))
print("fmtp 參數：", params)
assert params["packetization-mode"] == "1"
```

```text
RTP: PT=96 marker=1 seq=4711 ts=3000000 ssrc=2231627014
  在 session A 解成 VP8/90000，在 session B 解成 H264/90000
profile-level-id=42e01f → Constrained Baseline，level 3.1
profile-level-id=42001f → Baseline，level 3.1
profile-level-id=4d001f → Main，level 3.1
profile-level-id=640c1f → Constrained High，level 3.1
profile-level-id=640034 → High，level 5.2
fmtp 參數： {'level-asymmetry-allowed': '1', 'packetization-mode': '1', 'profile-level-id': '42e01f'}
```

第一行從一個手工組出的 RTP 封包裡取出 PT=96 與 marker bit，第二行顯示同一個 96 在 session A 是 VP8、在 session B 是 H.264：RTP 封包本身完全一樣，差別只在雙方協商出的對照表。這就是故事那段 munging 錯在哪裡：它把「某一份 SDP 裡的對照」當成了全世界通用的常數。

後面五行把常見的 `profile-level-id` 解開。`42e01f` 是 profile_idc 0x42（66，Baseline），constraint flags 0xe0 打開了 constraint_set1，所以是 **Constrained Baseline**，level_idc 0x1f（31）就是 level 3.1；瀏覽器之間互通最常用的就是它。`42001f` 少了 constraint flag，是一般 Baseline；`4d` 是 Main、`64` 是 High，`640c1f` 的 0x0c 打開了 constraint_set4 與 set5，是 Constrained High。真實的判斷規則比這段程式複雜（RFC 6184 用一張表列出各種 flag 組合），但核心概念相同：比對 H.264 時，profile 要相容，level 可以依 `level-asymmetry-allowed` 協調，不能只比 `H264` 這個名字。

**`a=rtcp-fb:<pt> <type>`** 宣告這個格式支援哪些 RTCP 回饋（RFC 4585），也就是接收端可以對發送端「抱怨」什麼。視訊幾乎都會列這四到五種：

| rtcp-fb | 意思 | 什麼時候送 | 詳見 |
|---|---|---|---|
| `nack` | 某些序號的封包遺失了，請重送 | 偵測到序號跳號，且來得及等重送 | 第 37 章 |
| `nack pli` | Picture Loss Indication：畫面壞了，請盡快送關鍵畫面 | 遺失太多、解碼器無法繼續 | 第 37 章 |
| `ccm fir` | Full Intra Request：請送一個完整的 I-frame | 新的接收者加入、SFU 切換來源 | 第 34、37 章 |
| `transport-cc` | 回報每個封包的到達時間，供發送端估計頻寬 | 持續回報 | 第 37 章 |
| `goog-remb` | 接收端估計的最大 bitrate（Google 的擴充） | 舊式頻寬估計 | 第 37 章 |

這張表的重點是：rtcp-fb 也要協商。如果 answer 沒有接受 `nack`，發送端就不會為這個格式保留重送用的歷史封包；如果 SFU 不支援 `transport-cc`，瀏覽器的頻寬估計就只能退回較舊的機制。answer 只能保留 offer 裡有、自己也支援的 rtcp-fb。

## 35.6 header extension、方向、身分與 data channel

讀完 codec，media section 剩下的屬性在回答三個問題：RTP 封包上要附帶哪些額外資訊（extmap）、這一段往哪個方向送（sendrecv 等）、這一路媒體屬於哪個 track、用哪個 SSRC（msid、ssrc）。最後的 data channel 段則完全不走 RTP。

**`a=extmap:<id> <uri>`**（第 16、17、38、39 行）宣告 RTP header extension（RFC 8285）：在 RTP header 後面附加小欄位，用一個 1 到 14 的 ID 標記，URI 說明欄位的意思。ID 是這場 session 的臨時編號，和 PT 一樣只在 SDP 裡有意義；answer 若接受某個 extension，要沿用 offer 的 ID。本章 offer 裡的四個：

- `ssrc-audio-level`：每個音訊封包帶一個音量值，SFU 不必解碼就能知道誰在說話，用來決定「發言者」畫面放大或只轉送最大聲的幾路。
- `sdes:mid`：在 RTP 封包裡直接帶 mid 字串。BUNDLE 之後，三個 m 段的封包走同一個五元組，接收端第一次看到某個 SSRC 時，要靠這個 extension 才知道它屬於哪一段。
- `sdes:rtp-stream-id`：simulcast（同一個鏡頭同時送高、中、低三種解析度）時標記是哪一層，搭配 `a=rid` 與 `a=simulcast` 使用，第 37 章會詳談。
- 瀏覽器實際的 offer 還會有 transport-wide sequence number（給 `transport-cc` 用的全連線序號）、abs-send-time 等 extension，它們的 URI 是以 http 開頭的識別字串，本章範例省略。

**`a=sendrecv`**（第 18、40 行）是這一段的**方向**，四個值分別是 `sendrecv`（雙向）、`sendonly`（我只送）、`recvonly`（我只收）、`inactive`（暫時都不送）。方向永遠是從「寫這份 SDP 的人」的角度描述，所以 answer 要把它反過來看：offer 說 `sendonly`，表示 offerer 要送、不收，answer 就只能是 `recvonly` 或 `inactive`。完整的規則在 35.7 節的表格。沒寫方向時預設是 `sendrecv`，data channel 段則不使用方向屬性。

**`a=msid:<stream id> <track id>`**（第 19、41 行）把這一段對應到 JavaScript 裡的 `MediaStream` 與 `MediaStreamTrack`（RFC 8830）。學生的麥克風與鏡頭同屬 stream `cam-0457`，接收端的 `ontrack` 事件會拿到同一個 `MediaStream`，播放端就知道這兩個 track 要對嘴（lip sync）。SFU 轉送時，用自己的 msid 標記「這是老師的影音」。

**`a=ssrc:<ssrc> cname:<cname>`**（第 29、75、76 行）預先宣告這一段會用哪些 **SSRC**（同步來源識別碼，RTP header 裡 32 bit 的串流 ID，第 34 章）。`cname` 是 RTCP 用來把同一個端點的多個 SSRC 歸在一起的名稱，同一個瀏覽器的音訊與視訊用同一個 cname，接收端才能用 RTCP 的時間資訊做音視訊同步。有些瀏覽器還會加上 `a=ssrc:<ssrc> msid:…` 一行，和 m 段層級的 `a=msid` 重複，是為了和舊實作相容。

**`a=ssrc-group:FID 2231627014 3990415873`**（第 74 行）說明兩個 SSRC 的關係。FID 是 flow identification，表示第二個 SSRC 是第一個的重傳串流：VP8 的媒體用 2231627014 送，rtx 重送封包用 3990415873 送。simulcast 的時代還有 `SIM` 群組，但現行做法改用 rid，第 37 章再談。在 Unified Plan 之下，SSRC 宣告其實是可選的：接收端可以靠 `sdes:mid` extension 認出新的 SSRC，所以有些 SFU 的 answer 完全不列 `a=ssrc`。

```text
 BUNDLE 後：一條 UDP 五元組  198.51.100.23:54012 ◄══════► 203.0.113.60:40000
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 收到一個封包                                                            │
 │   ├─ 第一個 byte 0–3？        → STUN（ICE 連線檢查、keepalive）           │
 │   ├─ 第一個 byte 20–63？      → DTLS（交握；SCTP 也包在 DTLS 裡）          │
 │   └─ 第一個 byte 128–191？    → RTP／RTCP（已用 SRTP 加密）               │
 │          ├─ 第二個 byte 192–223 → RTCP                                  │
 │          └─ 其他 → RTP：看 mid extension → 對照 SSRC 表 → 對照 PT        │
 │                 ├─ mid=0 ─► 音訊 transceiver（opus 111）                  │
 │                 └─ mid=1 ─► 視訊 transceiver（VP8 96／rtx 97 …）          │
 │   DTLS 裡的 SCTP ─► mid=2 的 data channel                               │
 └────────────────────────────────────────────────────────────────────────┘
```

這張圖說明 BUNDLE 之後，一個 UDP port 上怎麼分出所有東西。第一刀看第一個 byte：STUN、DTLS 與 RTP 的第一個 byte 落在不重疊的範圍（RFC 7983 整理了這套分流規則），所以它們可以共用一個 port。第二刀分 RTP 與 RTCP，這就是 rtcp-mux 要求 PT 避開 64–95 的原因：RTP 的第二個 byte 是 marker bit 加 7 bit 的 PT，PT 落在 64–95 而 marker 又是 1 時，這個 byte 會落在 192–223，和 RTCP 的封包類型（例如 200 是 Sender Report）無從分辨。第三刀把 RTP 分給各個 m 段，依序看 mid extension、已知的 SSRC、最後才看 PT；PT 只能當最後手段，因為同一個 PT 可能同時出現在多個 m 段。

**第 77 行 `m=application 9 UDP/DTLS/SCTP webrtc-datachannel`** 是 data channel 的段。proto `UDP/DTLS/SCTP` 表示 SCTP 跑在 DTLS 上、DTLS 跑在 UDP 上；格式欄不是 PT，而是固定的 `webrtc-datachannel`。整個 PeerConnection 不管開幾個 data channel，都共用這一個 m 段與一個 SCTP association；只有第一個 data channel 需要協商出這個 m 段，之後新增 data channel 都不必重新協商（第 36 章會講 SCTP 的細節）。

**第 85 行 `a=sctp-port:5000`** 是 SCTP 在 DTLS 之上使用的 port 號，它不是 UDP port，只是 SCTP 協定內部的編號，慣例是 5000。**第 86 行 `a=max-message-size:262144`** 宣告「我能接收的單一訊息最大 256 KiB」；沒寫這行時，規格的預設值是 64 KiB。送出的訊息超過對方宣告的上限，瀏覽器會直接拋錯，所以聲聲 Live 教室的白板如果要用 data channel 傳圖片，應該自己切塊，而不是假設對方收得下任何大小。

## 35.7 Offer／answer 模型：誰先說、怎麼回

SDP 本身只是描述；讓兩端達成協議的是 **offer／answer 模型**（RFC 3264，WebRTC 的細節由 JSEP 補充）。一方產生 **offer**，列出自己能做的事與偏好；另一方依自己的能力產生 **answer**，從 offer 的選項中挑出雙方都能接受的組合。兩份 SDP 都設好之後，協商才算完成，媒體依 answer 的結果開始流動。

```text
 學生瀏覽器（offerer）            signaling（WSS rt.shengsheng.example）         SFU（answerer）
   │ pc.addTrack(mic)、addTrack(cam)、createDataChannel("whiteboard")
   │ offer = await pc.createOffer()
   │ await pc.setLocalDescription(offer)      ── signalingState: have-local-offer
   │──────────────── {"type":"offer","sdp":"v=0…"} ──────────────────────────►│
   │                                                          setRemoteDescription(offer)
   │                                                          依能力產生 answer
   │◄─────────────── {"type":"answer","sdp":"v=0…"} ─────────────────────────│
   │ await pc.setRemoteDescription(answer)    ── signalingState: stable
   │──────────────── {"candidate":"candidate:… 192.168.1.23 …"}（trickle）────►│
   │◄─────────────── answer 裡已帶 SFU 的 candidate（ICE-lite）                  │
   │═══════════ ICE 連線檢查 → DTLS 交握 → SRTP 媒體、SCTP data channel ═══════►│（第 36 章）
```

這張時序圖由上往下讀。學生的瀏覽器先把麥克風、鏡頭與白板的 data channel 加進 PeerConnection，然後 `createOffer()`。`setLocalDescription(offer)` 這一步不只是「記下來」：瀏覽器在這時開始收集 ICE candidate，並把 signaling 狀態切到 `have-local-offer`。offer 經 WebSocket 送到 SFU，SFU 產生 answer 回傳；學生的瀏覽器 `setRemoteDescription(answer)` 之後回到 `stable`。candidate 在這段期間一個一個補送（trickle）。聲聲 Live 的 SFU 是 **ICE-lite** 實作（只回應連線檢查、不主動探測，適合有固定公網位址的伺服器），它的 candidate 直接寫在 answer 裡。

PeerConnection 用 `signalingState` 追蹤協商進度，下圖是它的狀態機（W3C WebRTC 1.0 定義）：

```text
                    setLocalDescription(offer)
          ┌──────────────────────────────────────────────┐
          │                                              ▼
     ┌─────────┐   setRemoteDescription(answer)    ┌──────────────────┐
     │ stable  │◄──────────────────────────────────│ have-local-offer │
     └─────────┘                                   └──────────────────┘
       │     ▲                                       │  setLocalDescription({type:"rollback"})
       │     │ setLocalDescription(answer)           └──────────────► 回到 stable
       │     │
       │   ┌───────────────────┐
       └──►│ have-remote-offer │   ◄── setRemoteDescription(offer)
           └───────────────────┘
       （pranswer 會經過 have-local-pranswer／have-remote-pranswer，WebRTC 很少用；close() 之後是 closed）
```

讀法是：只有在 `stable` 時才能開始新的一輪協商；自己送出 offer 就進入 `have-local-offer`，等對方的 answer；收到對方的 offer 就進入 `have-remote-offer`，要自己產生 answer。最容易出事的情況是 **glare**（撞車）：兩邊在同一時間各自送出 offer，雙方都卡在 `have-local-offer`，又各自收到一份 offer。解法是 **rollback**：其中一方放棄自己的 offer，回到 `stable` 再接受對方的。W3C 文件推薦的「perfect negotiation」模式就是事先指定一方為 polite（撞車時讓步並 rollback）、另一方為 impolite（撞車時忽略對方的 offer）。聲聲 Live 的教室一律由學生端發起 offer、SFU 只當 answerer，從架構上避免了 glare。

answer 要遵守的規則不多，但每一條都不能違反，否則對方的 `setRemoteDescription` 會失敗，或者更糟：成功了，但媒體行為和預期不同。

| 規則 | 內容 | 違反時的症狀 |
|---|---|---|
| m 段數量與順序 | answer 的 m 段數量、順序、種類必須和 offer 完全相同，mid 也相同 | `setRemoteDescription` 失敗 |
| 拒絕用 port 0 | 不想接受某一段時，該段的 port 設成 0，m 行仍要保留；被拒絕的段不能放進 BUNDLE | 刪掉 m 行會讓之後每一段都錯位 |
| codec 取交集 | answer 只能列 offer 裡有的格式；同一個 codec 應沿用 offer 的 PT（RFC 3264 為 SHOULD，瀏覽器實作都這樣做） | 編號不一致時兩邊各用各的對照表，容易解錯 |
| 方向反轉 | offer `sendrecv` → answer 可以是任何方向；`sendonly` → `recvonly` 或 `inactive`；`recvonly` → `sendonly` 或 `inactive`；`inactive` → `inactive` | 方向不相容時協商失敗或沒有媒體 |
| DTLS 角色 | offer 為 `actpass`，answer 選 `active` 或 `passive` | 兩邊同為 client 或同為 server，DTLS 交握不起來 |
| BUNDLE | answer 的群組是 offer 群組的子集，第一個 mid（tagged）必須是被接受的段 | 傳輸無法共用，或整個 BUNDLE 失敗 |
| 版本號 | 同一場 session 內，之後每一份有變動的 SDP，`o=` 的版本號要遞增 | 對方可能誤判為重送的舊 SDP |

這張表裡最常被誤會的是 PT 的方向性。依 RFC 3264，一份 SDP 列出的 PT 是「**我想收到的格式，以及我用來辨識它們的編號**」；也就是說，嚴格來看，送給對方的封包應該使用**對方** SDP 裡的 PT 編號。正因為兩個方向各有一張對照表，規格才強烈建議 answer 對同一個 codec 沿用 offer 的編號，讓兩張表一樣，就不必煩惱「這個方向該用哪一張」。這也是為什麼 answer 的 codec 順序可以和 offer 不同：answer 的順序表達的是 answerer 自己的偏好。

重新協商（renegotiation）用的是同一套模型。學生在課堂中關掉鏡頭、開始分享畫面、或者網路切換需要 ICE restart 時，任何一方都可以在 `stable` 狀態下送出新的 offer。新的 offer 必須包含先前的所有 m 段（數量只能增加、不能減少），順序不能變，`o=` 的版本號加一。瀏覽器觸發 `negotiationneeded` 事件就是在提醒應用程式「需要重新協商了」。

## 35.8 Unified Plan 與 transceiver

前面一直說「一個 m 段大致對應一個 transceiver」，這一節把它講清楚。WebRTC 1.0 採用的 SDP 寫法叫 **Unified Plan**：每一個要送或要收的 media track 各佔一個 m 段。對應到 API 的物件是 **RTCRtpTransceiver**（收發器）：一個 transceiver 包含一個 sender（`RTCRtpSender`，送出本地 track）和一個 receiver（`RTCRtpReceiver`，接收對方的 track），加上一個 `direction`，正好對應一個 m 段的 mid、方向與 codec 設定。

```text
 學生瀏覽器的 RTCPeerConnection                            offer 的 SDP
 ┌───────────────────────────────────────┐
 │ transceiver #0  mid="0"  sendrecv      │ ─────► m=audio …  a=mid:0  a=sendrecv  a=msid:cam-0457 mic-track
 │   sender: mic-track   receiver: (老師)  │
 ├───────────────────────────────────────┤
 │ transceiver #1  mid="1"  sendrecv      │ ─────► m=video …  a=mid:1  a=sendrecv  a=msid:cam-0457 cam-track
 │   sender: cam-track   receiver: (老師)  │
 ├───────────────────────────────────────┤
 │ （SCTP association，不是 transceiver） │ ─────► m=application …  a=mid:2
 └───────────────────────────────────────┘
 關鏡頭： transceiver #1 的 direction = "recvonly"   ─────► 下一份 offer：a=mid:1  a=recvonly（m 段還在）
 停用：   transceiver #1.stop()                      ─────► 下一份 offer：m=video 0 …（port 0，位置保留）
```

這張圖由左往右讀。`pc.addTrack(cam)` 會建立（或重用）一個 transceiver，`createOffer()` 再把每個 transceiver 寫成一個 m 段；data channel 不是 transceiver，但也佔一個 m 段。圖的下半部說明兩種常見操作在 SDP 上的樣子：把方向改成 `recvonly` 只會改變那一段的方向屬性；`stop()` 則讓那一段變成 port 0。m 段的位置永遠保留，因為 offer／answer 規則不允許刪除 m 段。被停用的 m 段之後可以被新的 transceiver「回收」重用，這是 JSEP 允許的，否則一個上了兩小時、反覆開關分享畫面的課，SDP 會越長越大。

Unified Plan 之前，Chrome 用的是 **Plan B**：同一種媒體只有一個 m 段，多個 track 靠多組 `a=ssrc` 區分。Plan B 無法對個別 track 設定方向或 codec，也和其他瀏覽器不相容。網路上的舊文章若在一個 m 段裡塞了多組帶 `msid` 的 `a=ssrc` 行，就是 Plan B 時代的寫法。

Unified Plan 讓 SFU 的設計也清楚了：聲聲 Live 的小班課有五個學生，每個學生的 PeerConnection 上，SFU 要轉送其他四個學生與老師的影音。answer 不能增加 m 段，而聲聲 Live 的 SFU 又只當 answerer，所以做法是：SFU 透過 signaling 通知「有新參與者」，學生端為這位參與者加一組 `recvonly` 的音訊與視訊 transceiver，再送出新一輪的 offer；參與者離開時，對應的 transceiver 停用，m 段變成 port 0，留待下一位參與者重用。所以一個上課中的 PeerConnection，SDP 有十幾個 m 段很正常。

> [!note] 2026 現況
> 依 2026 年 10 月查證，W3C WebRTC 1.0 的最新 Recommendation 日期是 2025-03-13，JSEP 的現行版本是 RFC 9429（取代 RFC 8829），BUNDLE 是 RFC 9143（取代 RFC 8843）。主流瀏覽器都只產生 Unified Plan 的 SDP；Chrome 在 2019 年左右改為預設 Unified Plan，之後移除了 Plan B。`RTCRtpTransceiver.setCodecPreferences()` 在主流瀏覽器都已可用，但各瀏覽器開始支援的版本不同，較舊的瀏覽器版本仍可能沒有，使用前要做功能偵測。

## 35.9 SDP munging 的風險

**SDP munging** 指的是在 `createOffer()`／`createAnswer()` 之後、`setLocalDescription()` 之前，用字串處理修改 SDP；廣義上也包括在 `setRemoteDescription()` 之前修改對方的 SDP。它在 WebRTC 早期很普遍，因為那時 API 很陽春，許多事只能靠改 SDP 做到：調整 codec 偏好、限制 bitrate（加一行 `b=AS:500`）、開啟 Opus 立體聲（改 fmtp 加 `stereo=1`）、關掉某些 header extension。

munging 的根本問題是：SDP 是瀏覽器內部狀態的**序列化結果**，不是設定檔。修改它，等於在瀏覽器背後改了一份它自己以為知道內容的文件。WebRTC 1.0 規格明文要求：`setLocalDescription` 帶入的 offer 若與上一次 `createOffer` 產生的不同，應以 `InvalidModificationError` 拒絕；實際上瀏覽器為了相容舊應用，仍容許不少修改，但容許哪些、修改後的行為是否穩定，沒有規格保證，也可能在某次版本更新後改變。具體的風險有四種：

1. **依賴不穩定的細節**：故事裡的 `98 = VP9` 就是這種。PT 編號、codec 清單的順序、extension 的 ID、甚至 SDP 的行順序，都是瀏覽器實作的選擇，可能隨版本改變。
2. **語法正確、語意錯誤**：regex 很容易做出「每一行都合法，但整體自相矛盾」的 SDP，例如只留下 rtx 卻刪掉它的 apt、刪掉了 rtpmap 卻沒刪 rtcp-fb、刪掉一個 m 段造成 mid 錯位。瀏覽器不一定會報錯，問題延後到對方或媒體層才出現。
3. **狀態不一致**：瀏覽器內部的 transceiver、編碼器設定與修改後的 SDP 不同步，例如 SDP 說只用 VP9，編碼器卻還為 VP8 保留資源，或者 getStats 回報的 codec 和實際送出的不同。
4. **安全**：從 signaling 收到的遠端 SDP 若被竄改（例如換掉 fingerprint），DTLS 驗證的就是攻擊者的憑證，加密形同虛設。SDP 必須透過經過驗證的 TLS 通道傳送，伺服器也要確認「送 offer 的人」確實是這堂課的學生（JWT，第 27 章）。

下面這段程式把故事的 munging 寫法，和「依 codec 名稱調整順序」的寫法，套在兩個 PT 編號不同的瀏覽器上：

```python
import re

# 兩個瀏覽器（或同一個瀏覽器的兩個版本）產生的 video m 段：codec 一樣，PT 編號不一樣
OFFER_X = """m=video 9 UDP/TLS/RTP/SAVPF 96 97 98 99 102 103
a=rtpmap:96 VP8/90000
a=rtpmap:97 rtx/90000
a=fmtp:97 apt=96
a=rtpmap:98 VP9/90000
a=rtpmap:99 rtx/90000
a=fmtp:99 apt=98
a=rtpmap:102 H264/90000
a=rtpmap:103 rtx/90000
a=fmtp:103 apt=102
"""
OFFER_Y = """m=video 9 UDP/TLS/RTP/SAVPF 96 97 98 100 101 102
a=rtpmap:96 VP8/90000
a=rtpmap:97 H264/90000
a=rtpmap:98 rtx/90000
a=fmtp:98 apt=97
a=rtpmap:100 VP9/90000
a=rtpmap:101 rtx/90000
a=fmtp:101 apt=100
a=rtpmap:102 rtx/90000
a=fmtp:102 apt=96
"""


def munge_hardcoded(sdp):
    """故事裡的寫法：假設 VP9 永遠是 98，只留下 98。"""
    return re.sub(r"(?m)^(m=video \d+ \S+) .*$", r"\1 98", sdp)


def prefer_by_name(sdp, mime):
    """比較安全的寫法：依 codec 名稱找 PT，把它與它的 rtx 排到最前面（不刪任何東西）。"""
    rtpmap = dict(re.findall(r"(?m)^a=rtpmap:(\d+) ([^/\s]+)", sdp))
    apt = dict(re.findall(r"(?m)^a=fmtp:(\d+) apt=(\d+)", sdp))
    first = [pt for pt, name in rtpmap.items() if name.upper() == mime.upper()]
    first += [pt for pt, target in apt.items() if target in first]
    mline = re.search(r"(?m)^(m=video \d+ \S+) (.*)$", sdp)
    rest = [pt for pt in mline.group(2).split() if pt not in first]
    return sdp.replace(mline.group(0), f"{mline.group(1)} {' '.join(first + rest)}")


def describe(sdp):
    rtpmap = dict(re.findall(r"(?m)^a=rtpmap:(\d+) ([^/\s]+)", sdp))
    apt = dict(re.findall(r"(?m)^a=fmtp:(\d+) apt=(\d+)", sdp))
    pts = re.search(r"(?m)^m=video \d+ \S+ (.*)$", sdp).group(1).split()
    out = []
    for pt in pts:
        label = rtpmap[pt] + (f"→{apt[pt]}" if pt in apt else "")
        if pt in apt and apt[pt] not in pts:
            label += "（apt 不在 m 行！）"
        out.append(f"{pt}:{label}")
    return " ".join(out)


for name, offer in (("瀏覽器 X", OFFER_X), ("瀏覽器 Y", OFFER_Y)):
    print(f"{name} 硬編 98  → {describe(munge_hardcoded(offer))}")
    print(f"{name} 依名稱排 → {describe(prefer_by_name(offer, 'VP9'))}")

assert describe(munge_hardcoded(OFFER_X)) == "98:VP9"
assert "apt 不在 m 行" in describe(munge_hardcoded(OFFER_Y))
assert describe(prefer_by_name(OFFER_Y, "VP9")).startswith("100:VP9 101:rtx→100")
```

```text
瀏覽器 X 硬編 98  → 98:VP9
瀏覽器 X 依名稱排 → 98:VP9 99:rtx→98 96:VP8 97:rtx→96 102:H264 103:rtx→102
瀏覽器 Y 硬編 98  → 98:rtx→97（apt 不在 m 行！）
瀏覽器 Y 依名稱排 → 100:VP9 101:rtx→100 96:VP8 97:H264 98:rtx→97 102:rtx→96
```

輸出的四行正好重現故事。在瀏覽器 X 上，硬編 98 的寫法「剛好」對了，只剩下 VP9，開發者在自己電腦上測試時就是這個結果；但它也順手刪掉了 VP9 的 rtx，丟包時無法重送，這個副作用在測試時看不出來。在瀏覽器 Y 上，98 是 H.264 的 rtx，硬編寫法留下一個 apt 指向不存在 PT 的重送格式，這就是 SFU log 裡那一行。依名稱排序的寫法在兩個瀏覽器上都得到正確結果：VP9 與它的 rtx 排到最前面，其他 codec 保留在後面當備案，對方不支援 VP9 時還能退回 VP8。

不過「比較安全的 munging」仍然是 munging，正解是使用專門的 API。下表整理常見的 munging 需求與對應的正式做法：

| 想做的事 | munging 的寫法 | 正式 API |
|---|---|---|
| 偏好某個 codec | 重排或刪減 m 行的 PT | `transceiver.setCodecPreferences(codecs)`，codecs 取自 `RTCRtpReceiver.getCapabilities("video").codecs` |
| 限制送出的 bitrate | 加 `b=AS:` 或 `b=TIAS:` | `sender.setParameters()` 設 `encodings[i].maxBitrate` |
| 降解析度或 frame rate | 改 fmtp 或 `b=` | `encodings[i].scaleResolutionDownBy`、`maxFramerate` |
| 暫停送出鏡頭 | 改方向為 `recvonly` | `track.enabled = false`（不必重新協商）或 `sender.replaceTrack(null)`，需要釋放頻寬時才改 `transceiver.direction` |
| simulcast | 手動加 `a=ssrc-group:SIM` | `addTransceiver(track, {sendEncodings: [...]})`（第 37 章） |
| 停用某一路媒體 | 刪掉 m 段 | `transceiver.stop()`，m 段會變成 port 0 |

表中的 API 都是改「物件」而不是改「文字」：瀏覽器知道你要什麼，自己產生一致的 SDP。其中 `setCodecPreferences` 是依 codec 的名稱與參數（`mimeType`、`clockRate`、`sdpFmtpLine`）指定，而不是 PT 編號，正好避開了故事的陷阱。要注意它必須在 `createOffer()` 之前呼叫，影響的是「我希望收到的格式」的順序。

伺服器端重寫 SDP 是另一回事：SFU 或 gateway 等於自己產生一份新的 SDP，只要合乎規則、和自己的實際行為一致即可。聲聲 Live 事後的修正分成兩邊：前端移除 regex，改用 `setCodecPreferences`；SFU 則在收到 offer 時先跑一輪結構驗證，遇到「只有 rtx 沒有主 codec」之類的 offer，回報一個明確的錯誤碼並記錄指標，而不是安靜地回 port 0。

## 35.10 動手做：解析 offer、產生 answer、驗證規則

這一節用 Python 標準函式庫寫出 SFU 那一端的協商邏輯，分成四個部分：

1. `parse()`：把 SDP 切成 session 層與 media section，整理出 rtpmap、fmtp、rtcp-fb、extmap、方向、mid、ICE 與 DTLS 參數。每一行都先檢查是否符合 `<小寫字母>=<值>` 的語法。
2. `negotiate()`：依 SFU 的能力產生 answer。音訊支援 Opus 與 PCMU，視訊支援 VP8 與 H.264 Constrained Baseline（packetization-mode 1），不支援 VP9、AV1、RED、DTMF；codec 取交集、沿用 offer 的 PT、rtx 只在它的 apt 被接受時保留；DTLS 角色選 passive；方向反轉；不支援的段用 port 0 拒絕。
3. `validate()`：拿 offer 與 answer 檢查 35.7 節的規則，傳回每條規則是否通過。
4. 三個情境加一個反例：第一次協商、學生關鏡頭後的重新協商、不支援 data channel 的舊版 SFU 節點，最後故意做一份壞掉的 answer，確認 validator 抓得到。

程式裡的 offer 就是 35.3 節那一份（行尾用 CRLF）。整段約 180 行，可以直接存檔執行。

```python
import re

FP_STUDENT = "sha-256 9F:4B:11:5E:E2:C3:21:BF:FF:4F:0D:85:6C:C6:BD:11:1D:F1:91:7F:BB:E6:A0:DF:FE:94:60:49:83:3E:43:37"
FP_SFU = "sha-256 7E:57:AC:DA:74:1C:75:EF:D3:BB:80:E4:A2:99:45:60:02:2E:90:E6:1C:AF:C4:80:32:92:1B:B7:63:1F:A1:87"
FB = "a=rtcp-fb:{0} transport-cc\na=rtcp-fb:{0} ccm fir\na=rtcp-fb:{0} nack\na=rtcp-fb:{0} nack pli\n"
TRANSPORT = ("c=IN IP4 0.0.0.0\na=ice-ufrag:Qx7v\na=ice-pwd:5KfLr2xT0aJp9wQe3VbN8sYd\n"
             "a=ice-options:trickle\na=fingerprint:" + FP_STUDENT + "\na=setup:actpass\n")
OFFER = ("v=0\no=- 4962303811422586241 2 IN IP4 127.0.0.1\ns=-\nt=0 0\n"
         "a=group:BUNDLE 0 1 2\na=extmap-allow-mixed\na=msid-semantic: WMS\n"
         "m=audio 9 UDP/TLS/RTP/SAVPF 111 63 0 8 126\n" + TRANSPORT +
         "a=mid:0\na=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level\n"
         "a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid\na=sendrecv\n"
         "a=msid:cam-0457 mic-track\na=rtcp-mux\na=rtpmap:111 opus/48000/2\n"
         "a=rtcp-fb:111 transport-cc\na=fmtp:111 minptime=10;useinbandfec=1\n"
         "a=rtpmap:63 red/48000/2\na=fmtp:63 111/111\na=rtpmap:0 PCMU/8000\n"
         "a=rtpmap:8 PCMA/8000\na=rtpmap:126 telephone-event/8000\n"
         "a=ssrc:1711239020 cname:k3VfQm8Zr0aD2xLp\n"
         "m=video 9 UDP/TLS/RTP/SAVPF 96 97 98 99 102 103 45 46\n" + TRANSPORT +
         "a=mid:1\na=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid\n"
         "a=extmap:10 urn:ietf:params:rtp-hdrext:sdes:rtp-stream-id\n"
         "a=sendrecv\na=msid:cam-0457 cam-track\na=rtcp-mux\na=rtcp-rsize\n"
         "a=rtpmap:96 VP8/90000\n" + FB.format(96) + "a=rtpmap:97 rtx/90000\na=fmtp:97 apt=96\n"
         "a=rtpmap:98 VP9/90000\n" + FB.format(98) + "a=fmtp:98 profile-id=0\n"
         "a=rtpmap:99 rtx/90000\na=fmtp:99 apt=98\na=rtpmap:102 H264/90000\n" + FB.format(102) +
         "a=fmtp:102 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f\n"
         "a=rtpmap:103 rtx/90000\na=fmtp:103 apt=102\na=rtpmap:45 AV1/90000\n" + FB.format(45) +
         "a=rtpmap:46 rtx/90000\na=fmtp:46 apt=45\n"
         "a=ssrc-group:FID 2231627014 3990415873\na=ssrc:2231627014 cname:k3VfQm8Zr0aD2xLp\n"
         "a=ssrc:3990415873 cname:k3VfQm8Zr0aD2xLp\n"
         "m=application 9 UDP/DTLS/SCTP webrtc-datachannel\n" + TRANSPORT +
         "a=mid:2\na=sctp-port:5000\na=max-message-size:262144\n").replace("\n", "\r\n")


def parse(sdp):
    """切成 session 與每個 media section；a= 行保留原始順序，並整理出常用欄位。"""
    session, media, cur = {"lines": []}, [], None
    for line in sdp.split("\r\n"):
        if not line:
            continue
        assert re.fullmatch(r"[a-z]=.*", line), f"不合法的 SDP 行：{line!r}"
        key, value = line[0], line[2:]
        if key == "m":
            kind, port, proto, *fmts = value.split()
            cur = {"kind": kind, "port": int(port), "proto": proto, "fmts": fmts, "lines": [],
                   "codecs": {}, "fmtp": {}, "fb": {}, "extmap": {}}
            media.append(cur)
            continue
        (cur or session)["lines"].append((key, value))
        if key == "o":
            session["version"] = int(value.split()[2])
        if cur is None or key != "a":
            continue
        name, _, arg = value.partition(":")
        if name == "rtpmap":
            pt, enc = arg.split(" ", 1)
            cur["codecs"][pt] = enc
        elif name == "fmtp":
            pt, params = arg.split(" ", 1)
            cur["fmtp"][pt] = dict(p.split("=", 1) if "=" in p else (p, "") for p in params.split(";"))
        elif name == "rtcp-fb":
            pt, fb = arg.split(" ", 1)
            cur["fb"].setdefault(pt, []).append(fb)
        elif name == "extmap":
            ext_id, uri = arg.split(" ", 1)
            cur["extmap"][ext_id] = uri
        elif name in ("sendrecv", "sendonly", "recvonly", "inactive"):
            cur["dir"] = name
        elif name in ("mid", "setup", "ice-ufrag", "ice-pwd", "fingerprint", "sctp-port"):
            cur[name] = arg
    session["bundle"] = next((v.split()[1:] for k, v in session["lines"] if v.startswith("group:BUNDLE")), [])
    return session, media


REVERSE = {"sendrecv": "sendrecv", "sendonly": "recvonly", "recvonly": "sendonly", "inactive": "inactive"}
ALLOWED = {"sendrecv": {"sendrecv", "sendonly", "recvonly", "inactive"},  # RFC 3264 的方向規則
           "sendonly": {"recvonly", "inactive"}, "recvonly": {"sendonly", "inactive"}, "inactive": {"inactive"}}
SFU_CAPS = {  # SFU 支援的 codec，依偏好排序；比對 名稱/clock/聲道 與關鍵 fmtp
    "audio": [("opus/48000/2", {}), ("PCMU/8000", {})],
    "video": [("VP8/90000", {}), ("H264/90000", {"packetization-mode": "1", "profile-level-id": "42e0"})],
}
SFU_EXT = {"urn:ietf:params:rtp-hdrext:sdes:mid", "urn:ietf:params:rtp-hdrext:ssrc-audio-level"}
SFU_FB = {"transport-cc", "nack", "nack pli", "ccm fir"}


def codec_ok(m, pt, want, need):
    if m["codecs"].get(pt, "").lower() != want.lower():
        return False
    have = m["fmtp"].get(pt, {})
    # H.264 只比 profile（前 4 個 hex 字元），level 交給 level-asymmetry-allowed 處理
    return all(have.get(k, "")[:len(v)] == v for k, v in need.items())


def answer_media(m, caps, role, ssrc, datachannel):
    out = ["c=IN IP4 0.0.0.0", "a=ice-ufrag:Sf60", "a=ice-pwd:Tz2Wq8LmVb4Nc6Xr1Kd9Hs0P",
           "a=fingerprint:" + FP_SFU, f"a=setup:{role}", f"a=mid:{m['mid']}"]
    if m["kind"] == "application":
        if not datachannel:
            return f"m=application 0 {m['proto']} {' '.join(m['fmts'])}", [f"a=mid:{m['mid']}"]
        return (f"m=application 9 {m['proto']} webrtc-datachannel",
                out + ["a=sctp-port:5000", "a=max-message-size:262144"])
    chosen = []
    for want, need in caps[m["kind"]]:  # 依 answerer 的偏好排，PT 一律沿用 offer 的編號
        chosen += [pt for pt in m["fmts"] if pt not in chosen and codec_ok(m, pt, want, need)]
    rtx = {m["fmtp"][pt]["apt"]: pt for pt in m["fmts"] if m["codecs"].get(pt, "").startswith("rtx/")}
    chosen = [p for pt in chosen for p in (pt, rtx.get(pt)) if p]  # rtx 緊跟在它的 apt 後面
    if not chosen:
        return f"m={m['kind']} 0 {m['proto']} {m['fmts'][0]}", [f"a=mid:{m['mid']}"]
    out += [f"a=extmap:{i} {u}" for i, u in m["extmap"].items() if u in SFU_EXT]
    direction = REVERSE[m.get("dir", "sendrecv")]
    out += [f"a={direction}", "a=rtcp-mux"]
    for pt in chosen:
        out.append(f"a=rtpmap:{pt} {m['codecs'][pt]}")
        out += [f"a=rtcp-fb:{pt} {fb}" for fb in m["fb"].get(pt, []) if fb in SFU_FB]
        if pt in m["fmtp"]:
            out.append(f"a=fmtp:{pt} " + ";".join(f"{k}={v}" if v else k for k, v in m["fmtp"][pt].items()))
    if direction in ("sendrecv", "sendonly"):  # SFU 要轉送老師的媒體給學生
        out += [f"a=msid:teacher-1024 {m['kind']}-fwd", f"a=ssrc:{ssrc} cname:sfu-60"]
    if ssrc == 30000:  # ICE-lite 的 SFU 直接給出 candidate；BUNDLE 後只需放在 tagged m 段
        out += ["a=candidate:1 1 udp 2130706431 203.0.113.60 40000 typ host", "a=end-of-candidates"]
    return f"m={m['kind']} 9 {m['proto']} {' '.join(chosen)}", out


def negotiate(offer_sdp, caps=SFU_CAPS, role="passive", datachannel=True, version=1):
    _, media = parse(offer_sdp)
    sections = [answer_media(m, caps, role, 30000 + i, datachannel) for i, m in enumerate(media)]
    accepted = [m["mid"] for m, (mline, _) in zip(media, sections) if " 0 " not in mline]
    lines = ["v=0", f"o=- 7316420098845511 {version} IN IP4 203.0.113.60", "s=-", "t=0 0",
             "a=ice-lite", "a=group:BUNDLE " + " ".join(accepted), "a=msid-semantic: WMS"]
    for mline, attrs in sections:
        lines += [mline] + attrs
    return "\r\n".join(lines) + "\r\n"


def validate(offer_sdp, answer_sdp):
    (_, om), (asess, am) = parse(offer_sdp), parse(answer_sdp)
    live = [(o, a) for o, a in zip(om, am) if a["port"] != 0]
    checks = {
        "m 行數量與順序不變": [m["kind"] for m in om] == [m["kind"] for m in am],
        "每個 m 段的 mid 一致": [m["mid"] for m in om] == [m["mid"] for m in am],
        "BUNDLE 只含被接受的 mid": asess["bundle"] == [a["mid"] for _, a in live],
        "fingerprint 與 ICE 帳密都在": all(m.get(k) for _, m in live for k in ("fingerprint", "ice-ufrag", "ice-pwd")),
        "offer actpass→answer active/passive": all(o["setup"] == "actpass" and a["setup"] in ("active", "passive") for o, a in live),
        "方向與 offer 相容": all(a["dir"] in ALLOWED[o["dir"]] for o, a in live if "dir" in o),
        "PT 是 offer 的子集且 codec 相同": all(set(a["fmts"]) <= set(o["fmts"]) and all(a["codecs"][p] == o["codecs"][p] for p in a["fmts"]) for o, a in live if o["kind"] != "application"),
        "rtx 的 apt 指向本段的 codec": all(a["fmtp"][p]["apt"] in a["fmts"] for _, a in live for p in a["fmts"] if a["codecs"].get(p, "").startswith("rtx/")),
        "extmap 沿用 offer 的 ID": all(o["extmap"].get(i) == u for o, a in live for i, u in a["extmap"].items()),
    }
    return checks


def summary(offer_sdp, answer_sdp, title):
    print(f"── {title}")
    (_, om), (_, am) = parse(offer_sdp), parse(answer_sdp)
    for o, a in zip(om, am):
        names = [a["codecs"].get(p, "?").split("/")[0] + f"({p})" for p in a["fmts"]]
        if o["kind"] == "application":
            names = [f"SCTP port {a['sctp-port']}"] if a["port"] else []
        if not a["port"]:
            names = ["rejected（port 0）"]
        print(f"  mid={o['mid']} {o['kind']:<11} {o.get('dir', '-'):>8} → {a.get('dir', '-'):<8} {' '.join(names)}")
    checks = validate(offer_sdp, answer_sdp)
    bad = [k for k, ok in checks.items() if not ok]
    print(f"  驗證 {len(checks) - len(bad)}/{len(checks)} 通過" + (f"，失敗：{bad}" if bad else ""))
    assert not bad


answer = negotiate(OFFER)
print(answer.replace("\r\n", "\n"), end="")
summary(OFFER, answer, "情境一：第一次協商")

# 情境二：學生關掉鏡頭，transceiver 改成 recvonly；新的 offer 版本號 +1，m 行一行都不能少
reoffer = OFFER.replace(" 2 IN IP4", " 3 IN IP4").replace("a=sendrecv\r\na=msid:cam-0457 cam-track", "a=recvonly")
reoffer = "".join(l for l in reoffer.splitlines(True) if "2231627014" not in l and "3990415873" not in l)
assert parse(reoffer)[0]["version"] == parse(OFFER)[0]["version"] + 1
summary(reoffer, negotiate(reoffer, version=2), "情境二：重新協商（關鏡頭）")

# 情境三：舊版 SFU 節點不支援 data channel，必須用 port 0 拒絕，而不是把 m 行刪掉
summary(OFFER, negotiate(OFFER, datachannel=False), "情境三：拒絕 data channel")

# 反例：有人「順手」把 answer 裡的 data channel 刪掉、又把 96 標成 VP9，validator 必須抓得到
broken = answer.split("m=application")[0].replace("BUNDLE 0 1 2", "BUNDLE 0 1").replace("96 VP8", "96 VP9")
failed = [k for k, ok in validate(OFFER, broken).items() if not ok]
print("── 反例：壞掉的 answer\n  失敗：", "、".join(failed))
assert failed == ["m 行數量與順序不變", "每個 m 段的 mid 一致", "PT 是 offer 的子集且 codec 相同"]
```

執行後先印出第一次協商產生的完整 answer，再印出各情境的摘要：

```text
v=0
o=- 7316420098845511 1 IN IP4 203.0.113.60
s=-
t=0 0
a=ice-lite
a=group:BUNDLE 0 1 2
a=msid-semantic: WMS
m=audio 9 UDP/TLS/RTP/SAVPF 111 0
c=IN IP4 0.0.0.0
a=ice-ufrag:Sf60
a=ice-pwd:Tz2Wq8LmVb4Nc6Xr1Kd9Hs0P
a=fingerprint:sha-256 7E:57:AC:DA:74:1C:75:EF:D3:BB:80:E4:A2:99:45:60:02:2E:90:E6:1C:AF:C4:80:32:92:1B:B7:63:1F:A1:87
a=setup:passive
a=mid:0
a=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level
a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid
a=sendrecv
a=rtcp-mux
a=rtpmap:111 opus/48000/2
a=rtcp-fb:111 transport-cc
a=fmtp:111 minptime=10;useinbandfec=1
a=rtpmap:0 PCMU/8000
a=msid:teacher-1024 audio-fwd
a=ssrc:30000 cname:sfu-60
a=candidate:1 1 udp 2130706431 203.0.113.60 40000 typ host
a=end-of-candidates
m=video 9 UDP/TLS/RTP/SAVPF 96 97 102 103
c=IN IP4 0.0.0.0
a=ice-ufrag:Sf60
a=ice-pwd:Tz2Wq8LmVb4Nc6Xr1Kd9Hs0P
a=fingerprint:sha-256 7E:57:AC:DA:74:1C:75:EF:D3:BB:80:E4:A2:99:45:60:02:2E:90:E6:1C:AF:C4:80:32:92:1B:B7:63:1F:A1:87
a=setup:passive
a=mid:1
a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid
a=sendrecv
a=rtcp-mux
a=rtpmap:96 VP8/90000
a=rtcp-fb:96 transport-cc
a=rtcp-fb:96 ccm fir
a=rtcp-fb:96 nack
a=rtcp-fb:96 nack pli
a=rtpmap:97 rtx/90000
a=fmtp:97 apt=96
a=rtpmap:102 H264/90000
a=rtcp-fb:102 transport-cc
a=rtcp-fb:102 ccm fir
a=rtcp-fb:102 nack
a=rtcp-fb:102 nack pli
a=fmtp:102 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f
a=rtpmap:103 rtx/90000
a=fmtp:103 apt=102
a=msid:teacher-1024 video-fwd
a=ssrc:30001 cname:sfu-60
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 0.0.0.0
a=ice-ufrag:Sf60
a=ice-pwd:Tz2Wq8LmVb4Nc6Xr1Kd9Hs0P
a=fingerprint:sha-256 7E:57:AC:DA:74:1C:75:EF:D3:BB:80:E4:A2:99:45:60:02:2E:90:E6:1C:AF:C4:80:32:92:1B:B7:63:1F:A1:87
a=setup:passive
a=mid:2
a=sctp-port:5000
a=max-message-size:262144
── 情境一：第一次協商
  mid=0 audio       sendrecv → sendrecv opus(111) PCMU(0)
  mid=1 video       sendrecv → sendrecv VP8(96) rtx(97) H264(102) rtx(103)
  mid=2 application        - → -        SCTP port 5000
  驗證 9/9 通過
── 情境二：重新協商（關鏡頭）
  mid=0 audio       sendrecv → sendrecv opus(111) PCMU(0)
  mid=1 video       recvonly → sendonly VP8(96) rtx(97) H264(102) rtx(103)
  mid=2 application        - → -        SCTP port 5000
  驗證 9/9 通過
── 情境三：拒絕 data channel
  mid=0 audio       sendrecv → sendrecv opus(111) PCMU(0)
  mid=1 video       sendrecv → sendrecv VP8(96) rtx(97) H264(102) rtx(103)
  mid=2 application        - → -        rejected（port 0）
  驗證 9/9 通過
── 反例：壞掉的 answer
  失敗： m 行數量與順序不變、每個 m 段的 mid 一致、PT 是 offer 的子集且 codec 相同
```

先讀 answer 本身。session 層多了一行 `a=ice-lite`，告訴學生的瀏覽器「我是 ICE-lite，由你負責主導連線檢查」；`o=` 的 session id 是 SFU 自己的，和 offer 的不同，因為 offer 與 answer 各自描述自己這一端；BUNDLE 群組是 `0 1 2`，三段全部被接受。

音訊段的 m 行從 offer 的 `111 63 0 8 126` 變成 `111 0`：RED（63）、PCMA（8）與 DTMF（126）被拿掉，因為 SFU 不支援，剩下的兩個沿用 offer 的編號。`a=setup:passive` 表示學生的瀏覽器會是 DTLS client；fingerprint 換成 SFU 自己的憑證指紋；extmap 只保留 SFU 認得的兩個，ID 和 offer 相同。方向是 `sendrecv`，所以 SFU 用 `a=msid:teacher-1024 audio-fwd` 與自己的 SSRC 30000 宣告「我會把老師的聲音送給你」。tagged m 段（mid 0）最後兩行是 SFU 的 candidate 與 `a=end-of-candidates`：位址 203.0.113.60、port 40000、型別 host，priority 2130706431 是 host candidate 的典型值（第 36 章會說明怎麼算）。因為三段 BUNDLE 在一起，candidate 只需要出現在這一段。

視訊段的 m 行是 `96 97 102 103`：VP8 與它的 rtx、H.264 與它的 rtx，VP9（98、99）與 AV1（45、46）被拿掉。這裡有兩個細節。第一，H.264 是靠 fmtp 比對過才留下的：offer 的 `packetization-mode=1` 和 `profile-level-id=42e01f` 的前兩個 byte `42e0` 都符合 SFU 的設定，如果 offer 只有 mode 0 的 H.264，就不會被接受。第二，rtcp-fb 四行原樣保留，是因為 SFU 剛好全部支援；如果 SFU 不支援 `ccm fir`，那一行就會消失，學生的瀏覽器也就不會送 FIR。data channel 段接受了 offer 的 SCTP port 5000，並宣告自己的訊息上限。

接下來是三個情境的摘要，每一列是一個 m 段：offer 的方向、answer 的方向、answer 裡留下的格式。情境一的驗證 9/9 通過。情境二模擬學生關掉鏡頭：程式把 offer 的 mid 1 改成 `recvonly`、拿掉這一段的 msid 與 SSRC，並把 `o=` 的版本號從 2 改成 3（`assert` 確認了版本號遞增）；answer 的 mid 1 隨之變成 `sendonly`，表示「SFU 仍然把老師的畫面送給你，但不期待收到你的」。m 段的數量與順序完全不變，這正是重新協商的規則。情境三用 `datachannel=False` 模擬舊版 SFU 節點：mid 2 被拒絕，m 行以 port 0 保留在原位，BUNDLE 群組變成 `0 1`，validator 同樣全數通過，證明「拒絕」與「刪除」是兩回事。

最後的反例最能說明 validator 的價值。程式拿第一次協商的 answer，把 data channel 段整段刪掉、BUNDLE 改成 `0 1`，再把 `96 VP8` 改成 `96 VP9`。驗證結果有三條失敗：m 行數量與順序、mid 一致性、PT 與 codec 的對應。值得注意的是「BUNDLE 只含被接受的 mid」這一條**通過了**，因為刪段的人很細心地同步修改了 BUNDLE；這說明單條規則都可能被湊過去，必須同時檢查結構與語意。在 SFU 上，這組檢查可以同時用在兩個方向：檢查收到的 offer（故事裡的錯誤會在「rtx 的 apt」或「沒有主 codec」這一關被抓到），也檢查自己產生的 answer，在送出前攔下自己的 bug。

這個實作刻意簡化了：只比對 H.264 profile 的前兩個 byte、不處理 simulcast 的 `a=rid`／`a=simulcast`、不檢查 `b=` 行，也不處理多個 BUNDLE 群組。真實的 SFU 要處理的情況多得多，但核心結構相同：解析成結構、依規則做決定、序列化之後再驗證一次。

## 35.11 在工作上怎麼用

事故檢討後，Joe 和小晴把「看 SDP」整理成團隊的日常工具。不同角色會在不同時機打開 SDP。

**前端工程師：拿到 SDP、讀懂 SDP，然後不要改它。** 在瀏覽器的 DevTools console 可以直接看目前的協商結果，Chrome 的 `chrome://webrtc-internals` 與 Firefox 的 `about:webrtc` 則會記錄每一次 `setLocalDescription`／`setRemoteDescription` 的完整 SDP 與時間：

```bash
# 在 DevTools console 執行（pc 是你的 RTCPeerConnection）
pc.localDescription.sdp          # 本端最後一次設定的 SDP
pc.remoteDescription.sdp         # 對方的 SDP
pc.getTransceivers().map(t => [t.mid, t.direction, t.currentDirection])
RTCRtpReceiver.getCapabilities("video").codecs.map(c => c.mimeType + " " + (c.sdpFmtpLine || ""))
```

最後兩行特別有用。`direction` 是你希望的方向，`currentDirection` 是協商完成後實際的方向：故事裡被拒絕的視訊 transceiver，`currentDirection` 會是 `null` 或 `stopped`，一行就能看出「不是鏡頭壞了，是協商把它關了」。`getCapabilities` 列出這個瀏覽器實際支援的 codec，要用 `setCodecPreferences` 時就從這個清單挑選，而不是自己寫 PT。

**影音工程師：SFU 端記錄協商摘要，而不是只記錄成功或失敗。** Joe 在 SFU 的 log 加了一行結構化摘要：每個 mid 的種類、offer 與 answer 的方向、選中的 codec、被拒絕的原因。完整 SDP 太長，而且含有 ice-pwd，不適合常態寫進 log；摘要則可以直接做成指標，例如「每個瀏覽器版本的視訊被拒絕比例」。這次事故如果有這個指標，前端發版後幾分鐘就會看到某個瀏覽器版本的拒絕比例從 0 跳到 100%。

```bash
# SFU 協商摘要（示意輸出）：每個 m 段一行，方便 grep 與彙總
grep 'session=8812/' sfu.log | grep 'negotiated' | head -3
# mid=0 audio sendrecv→sendrecv codec=opus/111 ua=browser-y/131
# mid=1 video sendrecv→rejected reason=no_primary_codec offered=[98:rtx(apt=97)] ua=browser-y/131
# mid=2 application accepted sctp-port=5000
```

**後端與 SRE：SDP 也是要驗證的輸入。** signaling server 收到的 SDP 是使用者可控制的資料：要限制大小（正常的 offer 幾 KB，小班課重新協商後可能十幾 KB）、只接受已驗證且屬於這堂課的連線，並在轉給 SFU 前做語法檢查，避免畸形的 SDP 打到 SFU 的解析器。

**資安工程師：SDP 裡有兩樣東西要保護。** Rita 在審查時特別看兩點。第一是 fingerprint 與 ice-pwd：它們決定了 DTLS 能不能擋住中間人，所以 signaling 必須是 WSS，伺服器要驗證 JWT，SDP 不能經過任何未驗證的中繼。第二是 candidate 裡的位址：host candidate 可能洩漏使用者的內網 IP（例如 192.168.1.23），瀏覽器在網頁沒有取得鏡頭或麥克風權限時，會用隨機的 `.local` mDNS 名稱取代真實 IP；伺服器端的 log 若要記錄 candidate，也應該遮蔽位址。

遇到「接通了但沒有畫面或沒有聲音」時，可以照下面的流程從 SDP 找原因：

```text
 症狀：連上了（ICE connected），但某一路沒有媒體
   │
   ├─ answer 裡那一段的 port 是 0？
   │     └─ 是 ─► 被拒絕：比對 offer 與 answerer 的 codec 能力；查 munging；看 SFU 的拒絕原因
   │
   ├─ 方向對嗎？（offer 的 a=sendrecv／recvonly 與 answer 的反轉是否符合預期）
   │     └─ 一邊是 recvonly 卻期待它送？ ─► 查 transceiver.direction 與 currentDirection
   │
   ├─ 選中的 codec 兩端都能解嗎？（answer m 行的第一個 PT、H.264 的 profile 與 packetization-mode）
   │     └─ 對不上 ─► getStats 的 codec 統計；檢查硬體解碼器限制（第 39 章）
   │
   ├─ PT 有對應嗎？（每個 m 行的 PT 都有 rtpmap；rtx 的 apt 在同一段）
   │     └─ 缺 ─► 多半是 munging 或手寫 SDP 的錯
   │
   └─ 以上都對 ─► 往下一層查：SRTP 封包有沒有到（第 36 章）、丟包與頻寬（第 37、39 章）
```

流程的順序是由「看 SDP 就能判斷」到「需要看統計數據」：前四個問題只要把 offer 與 answer 並排比對就有結論，故事裡的事故在第一個問題就有答案。

## 35.12 常見錯誤與除錯

下表整理 SDP 與協商相關、在聲聲 Live 與其他 WebRTC 服務最常見的錯誤。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 對方看不到某一路畫面，沒有任何錯誤 | answer 用 port 0 拒絕了那一段（沒有共同 codec、munging 弄壞清單） | 看 answer 的 m 行 port；`transceiver.currentDirection`；SFU 的拒絕原因 | 移除 munging，改用 `setCodecPreferences`；確保雙方至少有一個共同 codec |
| `setRemoteDescription` 失敗，訊息提到 m-line 順序或數量 | answer 刪掉或重排了 m 段，或重新協商的 offer 少了舊的段 | 數兩份 SDP 的 `m=` 行與 mid 順序 | answer 保留所有 m 段，拒絕用 port 0；重新協商只能新增或回收 |
| 硬編 PT 的程式在某些瀏覽器失效 | PT 是每個 session 的動態編號，不同瀏覽器或版本不同 | 比較兩個瀏覽器的 `a=rtpmap` | 依 codec 名稱與 fmtp 比對；用正式 API 指定偏好 |
| H.264 協商失敗或一方黑畫面 | packetization-mode 或 profile 不相容，或硬體解碼器不支援該 profile | 比對兩邊的 fmtp；getStats 看選中的 codec | 列出 Constrained Baseline 與 mode 1；SFU 依 profile 比對而非只看名字 |
| ICE 連上後 DTLS 失敗，連線馬上斷 | fingerprint 與實際憑證不符（SDP 被改或重用舊 SDP），或兩邊 setup 角色相同 | webrtc-internals 看 DTLS 狀態變成 failed；比對 fingerprint 與 setup | 不要快取或拼接舊 SDP；answer 只用 active 或 passive |
| 重新協商後媒體中斷幾秒 | 角色或 ICE 帳密改變導致重建傳輸，或發生 glare | 比對前後兩份 SDP 的 ice-ufrag、setup；看 signalingState 的變化 | 非必要不改 ICE 參數；用 perfect negotiation 處理 glare |
| 白板用 data channel 送大圖片時報錯 | 訊息超過對方的 `max-message-size` | 看對方 SDP 的 `a=max-message-size`（沒寫就是 64 KiB） | 應用層切塊傳送 |
| 音訊與視訊不同步 | 兩個 track 的 msid 不在同一個 stream，或 cname 不同 | 看 `a=msid` 的 stream id 與 `a=ssrc … cname` | 同一個參與者的音訊與視訊用同一個 stream 與 cname |

除錯 SDP 的通則是**並排比對**：offer 與 answer 一起看、正常與異常的一起看、修改前與修改後的一起看。單看一份 SDP 很難看出問題，因為每一行單獨看都是合法的；問題幾乎都出在兩份 SDP 之間的對應關係。

## 35.13 動手練習

1. **讀真實的 SDP**（真實工具）。在兩個不同的瀏覽器各開一個本機頁面，建立 `RTCPeerConnection`，加入一個 audio 與一個 video transceiver（`pc.addTransceiver("audio")`、`pc.addTransceiver("video")`）與一個 data channel，`createOffer()` 後印出 `offer.sdp`。
   答案要點：找出各瀏覽器 VP8、H.264、Opus 的 PT 編號，你會發現同一個 codec 的編號可能不同，codec 的數量與順序也不同；這正是「不能硬編 PT」的直接證據。順便確認 `m=` 行的 proto、`a=setup:actpass` 與 `a=group:BUNDLE`。

2. **延伸動手做：支援 `inactive` 與 `sendonly`**。替 35.10 節的程式加一個情境：學生把 mid 0 的麥克風設為 `inactive`、新增的分享畫面以 `sendonly` 出現在第四個 m 段（mid 3，codec 清單和 mid 1 相同）。修改 `negotiate()` 讓 SFU 依方向決定要不要放 msid 與 SSRC。
   答案要點：mid 0 的 answer 必須是 `inactive`；mid 3 的 answer 是 `recvonly`，而且不該帶 SFU 的 msid 與 SSRC（SFU 不會在這一段送東西）；BUNDLE 群組要變成 `0 1 2 3`，validator 仍應全數通過。

3. **延伸動手做：讓 validator 抓到故事的 offer**。把故事中瀏覽器 Y 被 munging 之後的 video m 段（35.9 節的 `OFFER_Y` 經 `munge_hardcoded`）換進 35.10 節的 offer，加一個 `validate_offer()`，檢查「每個 rtx 的 apt 都在同一段」與「每個 RTP 段至少有一個非 rtx 的 codec」。
   答案要點：兩條都會失敗；SFU 應回傳明確的錯誤（例如在 signaling 回應裡帶 `invalid_offer` 與 mid），而不是只回 port 0。想一想：為什麼規格允許 answerer 用 port 0 拒絕，但在自家系統裡明確報錯對維運更好？

4. **手算 profile-level-id**。不用程式，把 `4d0032` 與 `42c01e` 拆成 profile_idc、constraint flags、level_idc，判斷 profile 與 level。
   答案要點：`4d0032` 是 Main（77），level 0x32＝50，即 5.0；`42c01e` 是 profile_idc 66，constraint flags 0xc0 打開 set0 與 set1，屬於 Constrained Baseline，level 0x1e＝30，即 3.0。再想想：SFU 只支援 `42e01f` 時，能不能接受 `42c01e`？（profile 相容、level 較低，可以。）

5. **觀察重新協商**（真實工具）。在一個有視訊的 WebRTC 測試頁面中，通話建立後呼叫 `pc.getTransceivers()[1].direction = "recvonly"`，觀察 `negotiationneeded` 事件、新的 offer 與 `o=` 行的版本號，再用 `chrome://webrtc-internals` 確認 m 段的數量沒有變。
   答案要點：版本號加一；那一段的方向變成 `recvonly`，`a=msid` 與 `a=ssrc` 消失；ICE 帳密與 fingerprint 不變，所以不需要重新做 ICE 與 DTLS，媒體不中斷。

## 本章重點整理

- SDP 是描述多媒體會話的文字格式（RFC 8866），本身不傳輸任何東西；WebRTC 由 JSEP 規定瀏覽器如何產生與解讀 SDP，SDP 怎麼送則由應用程式的 signaling 決定。
- 一份 SDP 分成 session 層與多個 media section，每個 m 段從 `m=` 開始，對應一路媒體或 data channel；屬性在 m 段內的優先於 session 層。
- `o=` 的 session version 在每次有變動的重新協商時遞增；`c=` 與 m 行的 port 在 WebRTC 裡多半是佔位值，真正的位址由 ICE candidate 提供。
- `a=group:BUNDLE` 讓多個 m 段共用一條傳輸，接收端依序用第一個 byte、RTCP 範圍、mid extension、SSRC 與 PT 分流；rtcp-mux 讓 RTP 與 RTCP 共用 port，代價是 PT 不能用 64–95。
- ice-ufrag／ice-pwd 交給 ICE 做連線檢查的驗證，fingerprint 與 setup 交給 DTLS：前者驗證自簽憑證，後者決定誰當 client；offer 必須是 actpass，answer 只能是 active 或 passive。
- PT 只是單一 session 內的臨時編號，意思完全由 `a=rtpmap` 決定；動態 PT 主要用 96–127，不夠時也用 35–63，程式裡不能寫死任何 PT。
- `a=fmtp` 帶 codec 參數，H.264 的 packetization-mode 必須相同、profile 必須相容；rtx 用 `apt` 指向原本的 codec，沒有 apt 的 rtx 無法使用。
- `a=rtcp-fb` 宣告 NACK、PLI、FIR、transport-cc 等回饋能力，`a=extmap` 宣告 RTP header extension 與它們的 ID；兩者都要協商，answer 只保留雙方都支援的，並沿用 offer 的 ID。
- 方向屬性永遠從寫 SDP 的那一方描述，answer 要反轉：sendonly 對 recvonly、recvonly 對 sendonly，sendrecv 可以回任何方向。
- offer／answer 的核心規則是：answer 的 m 段數量、順序與 mid 不變；拒絕用 port 0，不能刪段；codec 取交集並沿用 offer 的 PT；BUNDLE 只包含被接受的段。
- Unified Plan 讓每個 transceiver 對應一個 m 段；改方向、停用與回收 transceiver 都反映在 m 段上，m 段的數量只增不減。
- signalingState 追蹤協商進度；雙方同時送 offer 會發生 glare，要用 rollback 或 perfect negotiation 處理，或在架構上固定由一方發起。
- SDP munging 依賴不穩定的實作細節，容易產生語法正確、語意錯誤的 SDP；偏好 codec、限制 bitrate、暫停送出、停用媒體都有正式 API 可用。
- SDP 含有決定加密安全的 fingerprint 與 ICE 密碼，也可能含有內網位址；signaling 必須經過驗證的 TLS 通道，伺服器端要把 SDP 當成不可信任的輸入來驗證。

## 延伸問答

> [!question]- Q1. 為什麼 answer 不能直接刪掉不支援的 m 段，一定要用 port 0？
> offer／answer 模型把兩份 SDP 的 m 段**依位置**一一對應：answer 的第 N 個 m 段就是在回答 offer 的第 N 個 m 段。這個設計來自 RFC 3264，早於 mid 屬性存在，所以位置本身就是對應關係。如果 answer 刪掉一段，後面每一段都會往前錯位，音訊的回答可能被當成視訊的回答，瀏覽器會直接拒絕這份 answer。
>
> port 0 在 SDP 裡的意思是「這一段存在，但被拒絕」，保留了位置，也明確表達了結果。被拒絕的段不能放進 BUNDLE 群組，對應的 transceiver 會被停用；之後的重新協商中，這個位置還可以被新的 transceiver 回收重用。這也是本章 validator 第一條就檢查「m 行數量與順序不變」的原因：這條錯了，後面所有比對都沒有意義。

> [!question]- Q2. 手算：offer 的視訊段是 `m=video 9 UDP/TLS/RTP/SAVPF 96 97 98 99`，96 是 VP8、97 是 rtx apt=96、98 是 H264（packetization-mode=0）、99 是 rtx apt=98。answerer 只支援 VP8 與 packetization-mode=1 的 H.264，answer 的 m 行該是什麼？
> 先逐一判斷主 codec：96 VP8 支援，保留；98 是 H.264，但 packetization-mode=0，而 answerer 只支援 mode 1，兩者是不同的格式，不能接受。再判斷 rtx：97 的 apt 是 96，96 被接受了，所以 97 保留；99 的 apt 是 98，98 被拒絕，99 也必須拿掉，否則就會出現一個沒有本體的重送格式。
>
> 所以 answer 的 m 行是 `m=video 9 UDP/TLS/RTP/SAVPF 96 97`，並且帶上 96 的 rtpmap 與 rtcp-fb、97 的 rtpmap 與 `fmtp:97 apt=96`。PT 沿用 offer 的編號，不能把 VP8 改編成 100。如果 answerer 連 VP8 都不支援，這一段就沒有任何共同 codec，必須回 `m=video 0 …` 拒絕整段，而不是回一個空的格式清單（m 行在語法上至少要有一個格式）。

> [!question]- Q3. 面試題：PT 96 在 offer 裡是 VP8，answer 卻寫 `a=rtpmap:96 H264/90000`，這合法嗎？會發生什麼事？
> 依 RFC 3264，每一份 SDP 的 PT 對照表描述的是「我想收到的格式與我用來辨識它們的編號」，所以理論上兩個方向可以有不同的對照表：offerer 收到 PT 96 的封包當成 VP8 解碼，answerer 收到 PT 96 的封包當成 H.264 解碼，各自送封包時使用對方的編號。規格只說 answer「應該」（SHOULD）沿用 offer 的編號，並沒有絕對禁止。
>
> 但實務上這是災難的開始：發送端必須記得「送給對方時要用對方的表」，任何一端把兩張表搞混，就會把 H.264 的位元組丟給 VP8 解碼器，結果是黑畫面或花屏，而且 log 裡不會有明確的錯誤。瀏覽器與主流 SFU 都會沿用 offer 的 PT，本章的 validator 也把「同一個 PT 的 codec 必須相同」當成錯誤。面試時可以補一句：這正是 PT 只是 session 內臨時編號的直接後果。

> [!question]- Q4. 情境判斷：學生關掉鏡頭時，前端用 `transceiver.direction = "recvonly"` 觸發重新協商。同事建議改成 `track.enabled = false`。兩者有什麼差別？
> `direction = "recvonly"` 會改變協商結果：瀏覽器觸發 `negotiationneeded`，送出新的 offer，那一段的方向變成 recvonly，SFU 的 answer 變成 sendonly。好處是編碼器真的停止、上行頻寬完全釋放，SFU 也明確知道這個學生不再送視訊；代價是一輪 signaling 往返，而且重新開鏡頭時還要再協商一次，期間畫面延遲出現，協商若失敗還要處理錯誤。
>
> `track.enabled = false` 不碰 SDP：sender 繼續送，但內容是黑畫面，編碼後的 bitrate 極低，對方幾乎立刻就能看到變化，開回來也是即時的。聲聲 Live 的做法是兩者並用：學生按下關鏡頭時先 `enabled = false`，讓畫面立即變黑；如果持續關閉超過一段時間，再改方向釋放資源。同時提醒一點：`enabled = false` 時 sender 仍在送封包，若需求是「保證不再傳出任何鏡頭內容」，`replaceTrack(null)` 或停用 track 更明確。

> [!question]- Q5. 看 SDP 找原因：ICE 已經 connected，但 DTLS 立刻 failed。offer 是 `a=setup:actpass`，answer 是 `a=setup:actpass`。問題在哪裡？還有什麼可能原因？
> answer 不能是 actpass。actpass 的意思是「我可以當 client 也可以當 server，讓你決定」，offer 用它把選擇權交給 answerer；answer 如果也回 actpass，等於沒有做決定，兩端可能都在等對方送 ClientHello，或都搶著當 client，交握自然失敗。嚴格的實作會在 `setRemoteDescription` 時就拒絕這份 answer，寬鬆的實作則拖到 DTLS 階段才失敗，症狀就是題目描述的樣子。
>
> 另一個常見原因是 fingerprint 不符：answer 裡的 fingerprint 來自另一個憑證，例如 SFU 重啟後換了憑證，卻回傳了快取的舊 SDP，或者某個中間元件拼接了錯的 SDP。確認方法是在 webrtc-internals 看 DTLS 狀態轉換與錯誤，並比對 answer 的 fingerprint 和 SFU 目前憑證的雜湊。這兩種錯誤都不是網路問題，所以 ICE 能 connected；看到「ICE 好、DTLS 壞」，第一步就是檢查 setup 與 fingerprint。

> [!question]- Q6. 設計取捨：SFU 該不該在 answer 裡列 `a=ssrc` 行？不列會有什麼影響？
> 列出 `a=ssrc` 的好處是接收端在第一個封包到達前就知道「SSRC 30001 屬於 mid 1、屬於 track teacher-1024 的視訊」，可以預先建好解碼管線，也能和只看 SSRC 的舊實作相容。代價是 SFU 要預先決定每個轉送串流的 SSRC，參與者的串流換來源（例如切換 simulcast 層、或發言者切換）時，若 SSRC 跟著變，就得重新協商，或在 SFU 內部改寫 SSRC 讓它保持穩定。
>
> 不列 `a=ssrc` 時，接收端靠 RTP 封包裡的 `sdes:mid` header extension 認出新的 SSRC 屬於哪一段，這是 Unified Plan 與 BUNDLE 規格支援的方式，彈性較大，SFU 可以自由使用 SSRC。風險是接收端必須正確實作 mid extension 的分流；如果 offer 沒有接受 mid extension，又沒有 `a=ssrc`，接收端在 BUNDLE 下就只能靠 PT 猜，多個 m 段用同樣的 PT 時會猜錯。所以決策的前提是先確認 mid extension 協商成功。

> [!question]- Q7. 你在 production 看到某個 Android App 版本的視訊協商成功率突然掉到 60%，SFU 的拒絕原因都是 `no_common_h264_profile`。你會怎麼查？
> 先從 SDP 找事實：抽樣幾份被拒絕的 offer，看 H.264 的 `a=fmtp` 列了哪些 `profile-level-id` 與 packetization-mode，再和成功的 offer 並排比較。常見的情況是 App 換了硬體編碼器或更新了 WebRTC 函式庫，H.264 只剩下 High profile（例如 `640c1f`）或只剩 packetization-mode 0，而 SFU 只接受 Constrained Baseline 與 mode 1，名稱都是 `H264`，profile 對不上。同時看這些 offer 是否還列了 VP8：如果有 VP8 卻仍被拒絕，就是 SFU 的 codec 選擇邏輯有 bug，沒有退回下一個共同 codec。
>
> 修正分兩個層次。短期在 SFU 端確認 codec 選擇會依序嘗試所有共同 codec，或者讓 SFU 接受相容的 profile（例如 Constrained Baseline 有多種 constraint flag 寫法）；長期則和 App 團隊確認 codec 偏好的設定方式，改用 `setCodecPreferences` 一類的 API，而不是讓函式庫的預設值決定。最後把「依客戶端版本統計的拒絕原因」做成指標，下一次版本更新造成的協商退化就能在發布初期被發現。

> [!question]- Q8. 為什麼說 SDP 被竄改會讓 DTLS-SRTP 加密失效？WebRTC 加密不是「一律端到端」嗎？
> WebRTC 的媒體一律用 DTLS-SRTP 加密，這點沒錯，但加密只能保證「你和握手的那一方之間的通訊是保密的」，至於「握手的那一方是不是你以為的人」，靠的是 SDP 裡的 fingerprint。DTLS 憑證是自簽的，沒有 CA 背書；瀏覽器接受對方憑證的唯一理由是它的雜湊和遠端 SDP 的 fingerprint 一致。如果攻擊者能修改 signaling 中的 SDP，把 fingerprint 換成自己的，並把 candidate 換成自己的位址，就能分別和兩端完成 DTLS，在中間解密再加密轉送，兩端都看不出異常。
>
> 所以 WebRTC 的安全性有一半在 signaling：要用經過驗證的 TLS（WSS 或 HTTPS），伺服器要驗證使用者身分並確認對方屬於這堂課，SDP 不能經過任何不可信的中繼。另外要釐清「端到端」的範圍：在 SFU 架構中，DTLS 的另一端是 SFU，媒體在 SFU 上是解密的，加密保護的是「學生到 SFU」與「SFU 到老師」兩段；若需要連 SFU 都看不到內容，要在應用層額外加密（例如 insertable streams 一類的機制），這屬於另一個層次的設計。

## 延伸閱讀

- RFC 8866〈SDP: Session Description Protocol〉：SDP 的現行語法與各行定義
- RFC 3264〈An Offer/Answer Model with the Session Description Protocol (SDP)〉：offer／answer 的基本規則、port 0 與方向
- RFC 9429〈JavaScript Session Establishment Protocol (JSEP)〉：瀏覽器如何產生與處理 SDP、transceiver 與 m 段的對應
- RFC 9143〈Negotiating Media Multiplexing Using the Session Description Protocol (SDP)〉：BUNDLE 與分流規則
- RFC 8839〈SDP Offer/Answer Procedures for Interactive Connectivity Establishment (ICE)〉、RFC 8842〈SDP Offer/Answer Considerations for DTLS and TLS〉：ICE 帳密、candidate 與 setup 屬性
- RFC 8841〈SDP Offer/Answer Procedures for SCTP over DTLS Transport〉：data channel 的 m 段、sctp-port 與 max-message-size
- RFC 6184〈RTP Payload Format for H.264 Video〉、RFC 4588〈RTP Retransmission Payload Format〉：H.264 的 fmtp 參數與 rtx
- W3C〈WebRTC: Real-Time Communication in Browsers〉：RTCPeerConnection、signalingState、RTCRtpTransceiver 與 setCodecPreferences
