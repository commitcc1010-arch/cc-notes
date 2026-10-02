---
chapter: 36
title: WebRTC 連線：ICE、STUN、TURN 與 DTLS-SRTP
part: 8
---

# 第 36 章　WebRTC 連線：ICE、STUN、TURN 與 DTLS-SRTP

> [!abstract] 本章地圖
> **核心問題**：兩個都躲在 NAT 後面、彼此不知道對方位址的瀏覽器，怎麼在一兩秒內找到一條能通的路，並在這條路上建立只有雙方解得開的加密媒體通道？
>
> **你會學到**：
> - 畫出一次 WebRTC 連線從 signaling、trickle ICE、candidate gathering、connectivity check、nomination、DTLS 交握到 SRTP 開始的完整時序，並說出每一段卡住時的症狀
> - 逐 byte 讀懂 STUN 訊息：header、magic cookie、transaction ID、XOR-MAPPED-ADDRESS、MESSAGE-INTEGRITY 與 FINGERPRINT，並用 RFC 5769 的測試向量驗證自己的實作
> - 用公式算出 host、srflx、prflx、relay candidate 與 candidate pair 的優先序，推論 ICE 最後會選哪一條路
> - 說清楚 TURN 的 allocation、permission、channel 與生命週期，估算中繼的頻寬成本，並設計短效憑證與防濫用設定
> - 解釋 DTLS-SRTP 為什麼用自簽憑證也安全：fingerprint 怎麼把金鑰綁在 signaling 上，以及 signaling 被攻破時會發生什麼事
> - 知道 data channel 是 SCTP over DTLS，會選可靠、不保證順序或有限重傳的通道
>
> **前置知識**：第 7 章（NAT 的 mapping 與 filtering、打洞）、第 9 章（UDP 與 socket）、第 17、18 章（HMAC、金鑰交換、TLS 交握）、第 34 章（RTP）、第 35 章（SDP 與 offer／answer）

## 36.1 故事：晚上八點的轉圈圈

第 7 章那張 Joe 的工單還沒關：「行動網路上的學生，視訊課幾乎都走 TURN；有幾所學校完全連不上。」聲聲 Live 的一對一課目前採「P2P 優先」：學生和老師的瀏覽器直接傳影音，打不通才經過 TURN 伺服器 `turn.shengsheng.example`（203.0.113.50）轉送；小班課則經過 SFU（第 37 章）。Joe 的儀表板顯示，晚上八點尖峰時，從按下「進入教室」到看到老師，中位數要 6.8 秒；4.1% 的課最後「無法連線」，console 裡只有一行 `ICE failed`。

小晴被拉進來，因為 signaling 服務（在雙方之間轉送連線資訊的 WebSocket，跑在 `rt.shengsheng.example`）是後端寫的。log 顯示每則訊息都在幾十毫秒內送達。小晴問：「訊息都送到了，剩下的六秒在做什麼？『ICE failed』是誰失敗了？」Joe 打開 `chrome://webrtc-internals`，滿畫面的 candidate pair，小晴一個字都看不懂。

阿德把事情拆成三條線。**慢**：三年前的前端 SDK 等所有候選位址收集完才送 offer，設定裡還列著一台早就不回應的舊 STUN 伺服器。**連不上**：失敗集中在幾所學校與公司，例如來源 198.51.100.77 的某高中，只放行 TCP 80 與 443，而 TURN 只開 UDP 3478。第三條是 Rita 提的：前端寫死了一組永久有效的 TURN 帳密，任何人打開 DevTools 就能把公司的 TURN 當免費中繼。

```text
                         rt.shengsheng.example（signaling，WebSocket）
                      ┌──────────── 203.0.113.40 ────────────┐
                      │ ① offer／answer／candidate（只有資訊）│
                      ▼                                      ▼
  學生筆電 192.168.1.23                                老師筆電（美咲）192.168.0.31
     │                                                        │
  家用 NAT 198.51.100.23                               家用 NAT 198.51.100.201
     │                                                        │
     ├──────────── ② 直接 P2P（srflx ↔ srflx）？──────────────┤
     │                                                        │
     └──► ③ turn.shengsheng.example 203.0.113.50 ◄────────────┘
            UDP 3478（現況）／TLS 443（缺少）

  某高中 198.51.100.77：只放行 TCP 80／443 → ② 與 UDP 的 ③ 全部不通 → ICE failed
```

① signaling 只交換「我是誰、在哪裡、支援什麼」，媒體不經過它，所以 signaling 快不代表通話快。② 是最理想的路徑：雙方 NAT 允許打洞時直接傳，延遲最低、公司不付頻寬。③ 是退路：雙方連向 TURN 由它轉送，一定通但要付錢。某高中擋掉所有 UDP，② 和 UDP 版的 ③ 都不可能，唯一出路是讓 TURN 在 TCP 443 上提供 TLS。

WebRTC 的連線建立靠一組協定合作：**ICE** 負責找路，**STUN** 是找路時用的探測訊息，**TURN** 是最後的中繼，**DTLS-SRTP** 負責加密。不懂它們，你只會看到「轉圈圈」和「ICE failed」；懂了以後，你能從 webrtc-internals 讀出卡在哪一段，也知道為什麼一行 TURN 設定就能救回那 4% 的課。章末的動手做會寫一個 STUN server 與 client，並模擬 ICE 在各種 NAT 組合下選出的路徑。

## 36.2 為什麼 P2P 很難：WebRTC 要解決的四件事

第 7 章講過 NAT 對 P2P 的三重阻礙：外面的人不知道 NAT 後主機的公網位址；filtering 只放行「內部聯絡過的對象」；symmetric NAT 的 mapping 隨目的地改變，透過第三方學到的位址對別人無效。打洞矩陣中有兩格打不通，只能靠中繼。

放進「兩個瀏覽器要視訊」的情境，WebRTC 要同時解決四件事。第一，**交換資訊**：codec、媒體流、憑證指紋與所有可能的位址，寫在 SDP 裡（第 35 章），但規格不規定怎麼送，這就是 signaling。第二，**找路**：列出所有可能的位址，兩兩配對、逐一測試，挑出最好的一條，這是 ICE。第三，**保持路通**：NAT mapping 會逾時、網路會切換，要定期確認路徑還活著。第四，**加密**：UDP 上不能直接用 TLS，雙方也沒有 CA 簽發的憑證，要有不靠 CA 又能防中間人的方法，這是 DTLS-SRTP。

| 要解決的問題 | WebRTC 的做法 | 規格 | 本章章節 |
|---|---|---|---|
| 交換能力與位址 | SDP offer／answer，透過應用自己的 signaling 傳送 | JSEP、SDP（第 35 章） | 36.4 |
| 知道自己在 NAT 外的位址 | 問 STUN server「你看到我是誰」 | STUN | 36.6 |
| 打不通時的退路 | 由 TURN server 中繼 | TURN | 36.7 |
| 從所有可能的路徑中挑一條 | 收集 candidate、配對、連線檢查、提名 | ICE、Trickle ICE | 36.5、36.8 |
| 保持路徑存活、偵測斷線 | 每隔幾秒送 STUN consent check；必要時 ICE restart | Consent Freshness | 36.8 |
| 在 UDP 上加密、驗證身分 | DTLS 交握，以 SDP 中的 fingerprint 驗證自簽憑證，匯出金鑰給 SRTP | DTLS-SRTP | 36.9 |
| 傳送任意資料 | SCTP 跑在同一條 DTLS 上 | Data channel、DCEP | 36.10 |

瀏覽器裡的 `RTCPeerConnection` 就是把這些協定組裝起來的引擎：應用程式只給它 signaling 訊息與 STUN／TURN 清單，其餘自動完成。難處在於任何環節出錯，表面上都是同一個症狀「連不上」，所以要知道每個環節的輸入與輸出。

> [!warning] 常見誤解
> 「WebRTC 是 P2P，所以不需要伺服器。」實際上一次 WebRTC 通話至少需要 signaling 伺服器（交換 SDP）；要穿越 NAT，幾乎一定需要 STUN；要保證連得上，必須準備 TURN。P2P 指的是「媒體在可能的時候直接走」，不是「沒有伺服器」。

## 36.3 全景：一次連線建立的完整時序

在拆解每個協定之前，先把整個過程走一遍。下圖是聲聲 Live 一對一課修好之後的流程：學生的瀏覽器先送 offer，所以是 **offerer**；老師是 **answerer**。圖中假設雙方都在家用 NAT 後面，最後選中 srflx 對 srflx 的路徑。

```text
 學生瀏覽器（offerer）     rt（signaling）      TURN／STUN 203.0.113.50        老師瀏覽器（answerer）
      │                        │                        │                              │
  ①  │ createOffer → setLocalDescription：開始 gathering                              │
      │── offer（ice-ufrag／pwd、fingerprint、setup:actpass）►│─────────── 轉送 ──────────►│ ②
      │── STUN Binding request ───────────────────────────►│                              │
      │── TURN Allocate ──────────────────────────────────►│                              │
      │── candidate：host（立刻有）──►│────────────────────────────────────────────────►│
      │◄─ Binding success：XOR-MAPPED-ADDRESS = srflx ─────│                              │
      │── candidate：srflx ─────────►│────────────────────────────────────────────────►│
      │◄─ Allocate success：XOR-RELAYED-ADDRESS = relay ───│                              │
      │── candidate：relay ─────────►│────────────────────────────────────────────────►│
      │◄─ answer（setup:active）＋老師的 candidate ─────────│◄──────────────────────────────│ ③
      │── end-of-candidates ────────►│────────────────────────────────────────────────►│
      │                                                                                  │
  ④  │◄═══ connectivity checks：STUN Binding（USERNAME、PRIORITY、MESSAGE-INTEGRITY）══►│
  ⑤  │════ nomination：帶 USE-CANDIDATE 的檢查，成功即選定 pair ══════════════════════►│
  ⑥  │◄═══ DTLS 交握（老師是 DTLS client）：交換憑證、比對 fingerprint、匯出 SRTP 金鑰 ═══│
  ⑦  │◄═══ SRTP 影音、SCTP data channel；每 4～6 秒一次 consent check ═══════════════►│
```

逐步看。① `setLocalDescription()` 的那一刻，瀏覽器開始**收集 candidate**（candidate gathering）：列出本機網卡位址，同時向 STUN 問公網位址、向 TURN 要中繼位址。② offer 立刻送出，不等 gathering 結束；每收集到一個 candidate 就再送一則訊息，這叫 **trickle ICE**（像水一滴一滴流過去）。③ 老師端回 answer，自己的 candidate 也一個一個送來，最後以 end-of-candidates 表示「沒有別的位址了」。

④ 雙方把本地與遠端 candidate 兩兩配對，依優先序對每一對送 STUN Binding request，這是 **connectivity check**（連線檢查）；檢查封包本身就是打洞封包。⑤ controlling 端（學生）從成功的 pair 中挑一個，送一次帶 `USE-CANDIDATE` 的檢查，這叫 **nomination**（提名），之後所有封包都走這一對。⑥ 在選中的路徑上跑 DTLS 交握，用 SDP 裡的 fingerprint 驗證對方的自簽憑證，並匯出 SRTP 金鑰。⑦ 影音以 SRTP 傳送，data channel 是同一條 DTLS 上的 SCTP；ICE 仍每隔幾秒送一次 STUN 檢查（consent freshness），也順便讓 NAT mapping 不逾時。

各段耗時加起來就是使用者看到的轉圈圈（之後還要等第一個 I-frame，第 34 章）。下表假設各段 RTT 約 40 ms：

| 階段 | 主要耗時 | 理想情況 | 常見的拖慢原因 |
|---|---|---|---|
| signaling（offer → answer） | 約 2 個 RTT（學生 → rt → 老師 → rt → 學生） | 約 100 ms | 對方頁面還沒準備好、WebSocket 重連 |
| gathering | host 立即；srflx 1 個 RTT；relay 2 個 RTT 以上（含 401 挑戰，TLS 再加交握） | 與 signaling 平行 | 非 trickle 時要等最慢的伺服器；伺服器不回應就等到逾時 |
| connectivity checks | 每個檢查 1 個 RTT，依 Ta（預設 50 ms）節奏送出 | 100～300 ms | 打不通的 pair 要等重傳逾時；remote candidate 太晚到 |
| nomination | 再 1 個 RTT | 40 ms | controlling 端為了等更好的 pair 而延後 |
| DTLS 1.2 交握 | 2 個 RTT（若用 HelloVerifyRequest cookie 再加 1 個） | 80 ms | 封包遺失時的重傳計時器以秒計；憑證太大被切片 |

這張表解釋了故事裡的 6.8 秒：舊 SDK 等 gathering 完成才送 offer，把第二列從「平行」變成「串行」，而那台不回應的 STUN 伺服器讓 gathering 等到逾時才結束。改成 trickle ICE 並刪掉它，連線時間就回到一秒以內。

### 一個 UDP port 上跑四種協定

圖中 ④ 到 ⑦ 的封包通常走**同一個** UDP 五元組：`bundlePolicy: "max-bundle"` 讓音訊、視訊與 data channel 共用一組 ICE 與 DTLS（BUNDLE，第 35 章），RTP 與 RTCP 也共用 port（rtcp-mux）。只需打一個洞，代價是接收端要在同一個 socket 上分辨四種封包。

```text
 ┌───────────────────────────────────────────────────────────────────┐
 │  音訊、視訊（RTP／RTCP）            data channel（任意訊息）       │
 │          │                                  │                     │
 │        SRTP／SRTCP                         SCTP                   │
 │          │  金鑰由 DTLS 匯出                │                     │
 │          │                                DTLS                    │
 │   STUN（ICE 檢查、consent）                 │                     │
 │          └───────────────┬──────────────────┘                     │
 │                  ICE 選出的 candidate pair                        │
 │              UDP（或 TURN 中繼；必要時 TCP／TLS）                  │
 │                         IP                                        │
 └───────────────────────────────────────────────────────────────────┘
```

由下往上讀：ICE 決定 UDP 封包從哪個本地位址送到哪個遠端位址，必要時經過 TURN。往上分三支：STUN 直接跑在 UDP 上；DTLS 負責交握產生金鑰交給 SRTP，並把 SCTP 封包加密裝進 application data 記錄；SRTP 用 DTLS 匯出的金鑰自己加密，影音**沒有**被包進 DTLS 記錄（原因見 36.9 節）。接收端只看第一個 byte 就能分流。

## 36.4 Signaling：WebRTC 刻意留白的那一段

**Signaling** 是在通話雙方之間傳遞控制訊息的管道：offer、answer、candidate、掛斷、重新協商。W3C 的 API 與 IETF 的 JSEP 定義了瀏覽器**產生與接受**哪些訊息，卻刻意不規定怎麼送，因為每個應用的身分系統與房間模型都不同：WebSocket、HTTP、SIP 都可以，甚至複製貼上也行。安全性則由應用負責。

聲聲 Live 的 signaling 跑在第 32、33 章的即時服務上：`wss://rt.shengsheng.example/signal`，連線時帶第 27 章的短效 JWT（audience 為 `rt.shengsheng.example`），伺服器確認這個人確實屬於這堂課才讓對方加入。訊息是 JSON，類型只有幾種：

```json
{"type": "offer",     "lesson": 8812, "sdp": "v=0\r\no=- 4611731400430051336 2 IN IP4 127.0.0.1\r\n..."}
{"type": "answer",    "lesson": 8812, "sdp": "v=0\r\n..."}
{"type": "candidate", "lesson": 8812, "candidate": "candidate:2499406306 1 udp 1694498815 198.51.100.23 50000 typ srflx raddr 0.0.0.0 rport 0", "sdpMid": "0", "usernameFragment": "s7Kq"}
{"type": "candidate", "lesson": 8812, "candidate": null}
{"type": "bye",       "lesson": 8812, "reason": "teacher-left"}
```

`candidate` 為 `null` 的那則就是 end-of-candidates。signaling 伺服器不必看懂 SDP，只要轉送給同一堂課的另一方；但它是安全模型的基石，原因在 SDP 裡。下面是學生 offer 中與本章有關的幾行（逐行解讀見第 35 章）：

```text
a=group:BUNDLE 0 1 2
a=ice-options:trickle
m=audio 9 UDP/TLS/RTP/SAVPF 111
c=IN IP4 0.0.0.0
a=mid:0
a=ice-ufrag:s7Kq
a=ice-pwd:aV3b9XkLmP0qRsT2uVwXyZ
a=fingerprint:sha-256 7B:21:…（共 32 組十六進位）
a=setup:actpass
a=rtcp-mux
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
a=sctp-port:5000
a=max-message-size:262144
```

`ice-ufrag` 與 `ice-pwd` 是 ICE 的短期帳號密碼：連線檢查時對方要用這組密碼替 STUN 訊息算 MESSAGE-INTEGRITY（36.6 節），規格要求 ufrag 至少 4 個字元、pwd 至少 22 個字元。`fingerprint` 是這次通話 DTLS 憑證的 SHA-256 雜湊，`setup:actpass` 表示「DTLS 的 client 或 server 都可以當」（36.9 節）。port 9 與 0.0.0.0 是佔位值，真正的位址都在之後的 candidate 訊息裡。

因為 fingerprint 和 ice-pwd 都靠 signaling 傳遞，**能竄改 signaling 的人，就能把自己的憑證指紋換進去**，當中間人解開所有媒體。所以 signaling 一定要走 `wss://`，伺服器要驗證身分與授權。Rita 審查時的第一個問題就是：「伺服器會不會把 A 房間的 SDP 轉給 B 房間的人？」

> [!tip] 兩邊同時送 offer 怎麼辦
> 雙方同時發起協商時，兩份 offer 會交錯，這叫 **glare**。W3C 規格範例中的「perfect negotiation」模式事先約定一方 polite（衝突時 rollback 自己的 offer）、另一方 impolite（忽略對方的 offer）。聲聲 Live 約定老師端是 polite。

## 36.5 ICE candidate：host、srflx、prflx 與 relay

**Candidate**（候選位址）是「對方可能用來聯絡我的一個傳輸位址」：IP、port 與傳輸協定。**ICE**（Interactive Connectivity Establishment）的核心想法是不猜 NAT 類型，而是列出所有可能的位址讓雙方實際測試。每個 candidate 都有一個 **base**：真正送出封包的本地 socket；各類型的差別在於「這個位址是從哪裡看出來的」。

```text
 學生筆電                      家用 NAT                          網際網路
 ┌──────────────────────┐   ┌──────────────────┐
 │ socket 192.168.1.23  │   │                  │        STUN／TURN 203.0.113.50
 │        :54400        │──►│ 198.51.100.23    │──────► ┌────────────────────────────┐
 │  ① host              │   │  :50000          │        │ Binding：「我看到你是       │
 └──────────────────────┘   │  ② srflx         │◄────── │  198.51.100.23:50000」     │
                            └──────────────────┘        │ Allocate：「給你中繼位址    │
                                                        │  203.0.113.50:49152」③ relay│
                                                        └────────────────────────────┘
  ④ prflx：連線檢查時，對方從封包來源看到的、事先沒列出的位址（例如 symmetric NAT 新配的 :50007）
```

① **host candidate** 是本機網卡的位址 192.168.1.23:54400。② **server-reflexive（srflx）candidate** 是 NAT 外看到的位址：從 host socket 問 STUN server，回應裡的 198.51.100.23:50000；base 仍是 host socket。③ **relayed（relay）candidate** 是 TURN 替瀏覽器保留的中繼位址 203.0.113.50:49152。④ **peer-reflexive（prflx）candidate** 是連線檢查時才學到的：對方發現檢查封包的來源不在我宣告過的 candidate 裡，就把它當成新的 candidate，也就是第 7 章打洞模擬中「改回覆實際看到的來源」。

| 類型 | SDP 寫法 | 從哪裡來 | 什麼情況能用 | 代價 |
|---|---|---|---|---|
| host | `typ host` | 本機網卡 | 同一個 LAN、對方能直接路由到這個位址、或沒有 NAT | 暴露內網位址（瀏覽器多半以 mDNS 名稱遮蔽） |
| srflx | `typ srflx raddr … rport …` | STUN Binding 回應的 XOR-MAPPED-ADDRESS | NAT 是 endpoint-independent mapping，對方能打洞進來 | 需要一台 STUN server，查詢 1 個 RTT |
| prflx | `typ prflx` | 連線檢查時從封包來源學到 | symmetric NAT 對上 filtering 較寬鬆的一方 | 無法事先預測，只能在檢查中發現 |
| relay | `typ relay raddr … rport …` | TURN Allocate 回應的 XOR-RELAYED-ADDRESS | 幾乎都能用（只要連得上 TURN） | 延遲增加、TURN 的頻寬與運算成本 |

SDP 裡的 candidate 是一行文字，格式固定。以學生的 srflx 為例：

```text
a=candidate:2499406306 1 udp 1694498815 198.51.100.23 50000 typ srflx raddr 192.168.1.23 rport 54400
            │          │ │   │          │             │     │         │                  │
            foundation │ │   priority   位址          port  類型      related address    related port
                       │ transport
                       component（1＝RTP；rtcp-mux 下只有 1）
```

**foundation** 是識別字串：類型、base IP、STUN／TURN server 與傳輸協定都相同的 candidate 共用 foundation，表示它們「很可能一起成功或一起失敗」（36.8 節的 frozen 演算法）。**component** 在 rtcp-mux 下都是 1。**priority** 是 32 bit 整數，36.8 節用公式算出。`raddr`／`rport` 只是除錯資訊，瀏覽器為了隱私常寫成 `0.0.0.0 0`。

### Gathering 在真實瀏覽器裡長什麼樣

瀏覽器先列出所有網卡（Wi-Fi、有線、VPN、IPv4、IPv6）的 host candidate，再從每個 host socket 問 STUN、對 TURN 送 Allocate。Allocate 的回應也帶著「TURN 看到的你」，所以同時產生 srflx，這是很多部署只設定 TURN 的原因。瀏覽器也會收集 TCP 的 host candidate（ICE-TCP），讓只開 TCP 的 SFU 也能被連上，但 P2P 之間的 TCP 打洞很少成功（第 7 章）。

> [!note] mDNS 遮蔽 host 位址
> host candidate 會洩漏內網位址。現代瀏覽器在網頁沒有取得攝影機或麥克風權限時，把 host IP 換成隨機的 `.local` 名稱（例如 `4f3c2b1a-….local`），同一個 LAN 的對方要用 mDNS 解析；取得權限後是否仍遮蔽依瀏覽器而定。若網路擋掉 mDNS，同一個 LAN 內的 host 對 host 也會失敗。

`iceTransportPolicy: "relay"` 讓瀏覽器只收集 relay candidate：成本增加，但不暴露使用者 IP，也是除錯時強迫走 TURN 的方法。`iceCandidatePoolSize` 讓瀏覽器提前收集，省下 gathering 時間，代價是多佔用 TURN allocation。

## 36.6 STUN：訊息格式與「你看到我是誰」

**STUN**（Session Traversal Utilities for NAT）是一個很小的請求／回應協定，回答第 7 章那個問題：「從你那邊看，我的位址和 port 是什麼？」在 WebRTC 裡，ICE 的連線檢查與 consent 也都是 STUN Binding，TURN 則是在 STUN 格式上擴充出來的，所以讀懂 STUN 等於讀懂三個協定的封包。

STUN 通常跑在 UDP 3478，也可走 TCP 3478 或 TLS（預設 5349）。在 UDP 上 STUN 自己重傳，RTO（重傳逾時）每次加倍；依規格預設值（初始 500 ms、最多送 7 次），完全沒有回應的請求約 39.5 秒才宣告失敗。這就是那台舊 STUN 伺服器的殺傷力：不回應不會立刻失敗，而是讓瀏覽器一直重送。

### Header：20 bytes

每個 STUN 訊息都以固定 20 bytes 的 header 開始，後面接零個以上的屬性（attribute）：

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───┬───────────────────────────┬───────────────────────────────┐
 │0 0│   STUN Message Type (14)  │      Message Length (16)      │  bytes 0-3
 ├───┴───────────────────────────┴───────────────────────────────┤
 │              Magic Cookie (32) ＝ 0x2112A442                  │  bytes 4-7
 ├───────────────────────────────────────────────────────────────┤
 │                                                               │
 │                     Transaction ID (96)                       │  bytes 8-19
 │                                                               │
 ├───────────────────────────────────────────────────────────────┤
 │       Attributes（TLV，每個都補齊到 4 bytes 的倍數）            │  bytes 20-
 └───────────────────────────────────────────────────────────────┘
```

最前面兩個 bit 永遠是 0：同一個 port 上的 DTLS 與 SRTP 第一個 byte 一定大於 3，這兩個 bit 本身就能把 STUN 分出來。14 bit 的 **Message Type** 同時編碼 method（做什麼）與 class（請求、回應或通知）。**Message Length** 不含 header 的 20 bytes，且因屬性都補齊到 4 的倍數，最後兩個 bit 一定是 0，可當快速檢查。

**Magic Cookie** 固定為 0x2112A442：標示新版 STUN（舊版 RFC 3489 在此放 transaction ID）、讓多工接收端多一道判斷，也是 XOR-MAPPED-ADDRESS 的 XOR 金鑰。**Transaction ID** 是 96 bit 隨機數，用來配對請求與回應；它必須用密碼學安全的亂數產生，否則路徑外的攻擊者可以猜中並偽造回應，塞給你一個錯誤的公網位址。

Message Type 的 14 個 bit 是交錯編排的，class 的兩個 bit 插在 method 的中間：

```text
   13  12  11  10   9   8   7   6   5   4   3   2   1   0
 ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
 │M11│M10│M9 │M8 │M7 │C1 │M6 │M5 │M4 │C0 │M3 │M2 │M1 │M0 │
 └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
   C1 C0：00＝request　01＝indication　10＝success response　11＝error response
   Binding（method 0x001）：request 0x0001、success 0x0101、error 0x0111
```

這種排法是為了相容舊版的 0x0001 與 0x0101。實務上只要記得：**class 決定 0x0010 與 0x0100 這兩個 bit**，method 填在其餘位置。**indication** 是不需要回應的單向訊息，TURN 的 Send／Data 就是。本章會遇到的訊息如下：

| method | 值 | request | success | error | indication | 用在哪裡 |
|---|---|---|---|---|---|---|
| Binding | 0x001 | 0x0001 | 0x0101 | 0x0111 | 0x0011 | 問公網位址、ICE 連線檢查、consent、keepalive |
| Allocate | 0x003 | 0x0003 | 0x0103 | 0x0113 | 無 | TURN：要一個中繼位址 |
| Refresh | 0x004 | 0x0004 | 0x0104 | 0x0114 | 無 | TURN：延長或刪除 allocation |
| Send | 0x006 | 無 | 無 | 無 | 0x0016 | TURN：client 請 TURN 轉送一個封包 |
| Data | 0x007 | 無 | 無 | 無 | 0x0017 | TURN：TURN 把收到的封包交給 client |
| CreatePermission | 0x008 | 0x0008 | 0x0108 | 0x0118 | 無 | TURN：允許某個 peer IP |
| ChannelBind | 0x009 | 0x0009 | 0x0109 | 0x0119 | 無 | TURN：把 peer 綁到一個 4 bytes 的 channel |

### 屬性：TLV 與「看不懂可不可以略過」

屬性都是 **TLV**：2 bytes type、2 bytes length（不含補齊）、value，再補 0 到 4 的倍數。type 本身帶語意：0x0000–0x7FFF 是 **comprehension-required**（看不懂就拒絕，回 420 Unknown Attribute），0x8000–0xFFFF 是 **comprehension-optional**（看不懂就略過），讓協定能安全擴充。

| 屬性 | type | 用途 |
|---|---|---|
| XOR-MAPPED-ADDRESS | 0x0020 | 伺服器看到的請求來源位址（XOR 編碼） |
| USERNAME | 0x0006 | 帳號；ICE 中是「對方 ufrag:自己 ufrag」 |
| MESSAGE-INTEGRITY | 0x0008 | HMAC-SHA1，證明訊息出自知道密碼的人、沒有被改過 |
| FINGERPRINT | 0x8028 | CRC-32，幫多工的接收端確認「這真的是 STUN」 |
| ERROR-CODE | 0x0009 | 錯誤碼與原因，例如 401、438、487 |
| REALM、NONCE | 0x0014、0x0015 | TURN 的長期憑證挑戰 |
| PRIORITY、USE-CANDIDATE | 0x0024、0x0025 | ICE：prflx 的優先序、提名旗標 |
| ICE-CONTROLLED、ICE-CONTROLLING | 0x8029、0x802A | ICE：角色與 64 bit tie-breaker |

### XOR-MAPPED-ADDRESS：為什麼要 XOR

舊的 MAPPED-ADDRESS 直接寫位址，但有些 NAT 的 ALG（第 7 章）看到「長得像自己公網 IP 的 4 bytes」就改寫成內網位址，把回應改壞。XOR 之後，ALG 就認不出來了。

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────────────────────┬───────────────────────────────┐
 │     Type ＝ 0x0020            │     Length ＝ 8（IPv6 為 20） │
 ├───────────────┬───────────────┼───────────────────────────────┤
 │ Reserved（0） │ Family 01／02 │  X-Port ＝ port ⊕ 0x2112      │
 ├───────────────┴───────────────┴───────────────────────────────┤
 │ X-Address：IPv4 ＝ 位址 ⊕ 0x2112A442                          │
 │            IPv6 ＝ 位址 ⊕（magic cookie ‖ transaction ID）    │
 └───────────────────────────────────────────────────────────────┘
```

X-Port 是 port 與 magic cookie 的**高 16 bit**（0x2112）XOR；IPv4 位址與整個 magic cookie XOR；IPv6 的 16 bytes 則與「magic cookie 接 transaction ID」XOR，所以解 IPv6 一定要知道 transaction ID。手算：198.51.100.23 是 `c6 33 64 17`，XOR `21 12 a4 42` 得 `e7 21 c0 55`；port 50000（0xc350）XOR 0x2112 得 0xe242，動手做的程式會印出相同的 bytes。

### MESSAGE-INTEGRITY 與 FINGERPRINT：一個防偽造、一個防認錯

**MESSAGE-INTEGRITY** 是 20 bytes 的 HMAC-SHA1（第 17 章）。ICE 檢查用**短期憑證**，金鑰就是對方 SDP 中的 `ice-pwd`；TURN 用**長期憑證**，金鑰是 MD5(username ":" realm ":" password)。只有知道密碼的人算得出來，所以它證明來源、防止竄改。（新版另有 MESSAGE-INTEGRITY-SHA256，但 ICE 檢查仍以 SHA-1 版為主。）

**FINGERPRINT** 是 CRC-32 再 XOR 0x5354554E（ASCII 的 "STUN"），必須是最後一個屬性。CRC 誰都算得出來，所以它**沒有安全性**，只是讓多工的接收端多一道確認，避免把恰好長得像 STUN 的 RTP 或 DTLS 誤認成 STUN。

計算時有個容易錯的細節：header 的 Message Length 要**假裝已經包含這個屬性本身**。算 MESSAGE-INTEGRITY 時長度算到它結束為止（不含後面的 FINGERPRINT），HMAC 涵蓋它之前的所有 bytes；算 FINGERPRINT 時長度包含它自己，CRC 涵蓋之前的所有 bytes。所以順序固定：其他屬性 → MESSAGE-INTEGRITY → FINGERPRINT。

自己實作協定最怕「我以為對了」。RFC 5769 提供了 STUN 的官方測試向量。下面的程式重建它第 2.1 節的範例請求（一個 ICE 連線檢查），驗證 bytes 和 RFC 公布的一致，再示範竄改時兩個屬性各自的反應：

```python
import binascii
import hashlib
import hmac
import struct

MAGIC, FP_XOR = 0x2112A442, 0x5354554E
SOFTWARE, PRIORITY, ICE_CONTROLLED, USERNAME = 0x8022, 0x0024, 0x8029, 0x0006
MESSAGE_INTEGRITY, FINGERPRINT = 0x0008, 0x8028


def attr(atype, value, pad=b"\x00"):
    return struct.pack("!HH", atype, len(value)) + value + pad * (-len(value) % 4)


def finish(msg_type, txid, body, password):
    """依序附加 MESSAGE-INTEGRITY 與 FINGERPRINT；兩者計算時，長度欄位都要「假裝自己已經在裡面」。"""
    head = struct.pack("!HHI", msg_type, len(body) + 24, MAGIC) + txid      # +24：MI 的 4＋20 bytes
    mac = hmac.new(password, head + body, hashlib.sha1).digest()           # ICE 短期憑證：key 就是 ice-pwd
    body += attr(MESSAGE_INTEGRITY, mac)
    head = struct.pack("!HHI", msg_type, len(body) + 8, MAGIC) + txid       # +8：FINGERPRINT 的 4＋4 bytes
    crc = (binascii.crc32(head + body) ^ FP_XOR) & 0xFFFFFFFF
    return head + body + attr(FINGERPRINT, struct.pack("!I", crc))


def verify(msg, password):
    """回傳 (fingerprint 是否正確, integrity 是否正確)。假設 MI 與 FINGERPRINT 是最後兩個屬性。"""
    fp_at, mi_at = len(msg) - 8, len(msg) - 32
    fp_ok = struct.unpack("!I", msg[-4:])[0] == (binascii.crc32(msg[:fp_at]) ^ FP_XOR) & 0xFFFFFFFF
    head = msg[:2] + struct.pack("!H", mi_at + 24 - 20) + msg[4:20]        # 長度改成「到 MI 為止」
    mac = hmac.new(password, head + msg[20:mi_at], hashlib.sha1).digest()
    return fp_ok, hmac.compare_digest(mac, msg[mi_at + 4:fp_at])


# RFC 5769 §2.1 的範例請求：ICE 連線檢查（controlled 端送出）
txid = bytes.fromhex("b7e7a701bc34d686fa87dfae")
password = b"VOkJxbRl1RmTxUk/WvJxBt"
body = (attr(SOFTWARE, b"STUN test client")
        + attr(PRIORITY, struct.pack("!I", 0x6E0001FF))
        + attr(ICE_CONTROLLED, bytes.fromhex("932ff9b151263b36"))
        + attr(USERNAME, b"evtj:h6vY", pad=b" "))             # 這份測試向量刻意用空白補齊，證明補齊內容不重要
msg = finish(0x0001, txid, body, password)
for off in range(0, len(msg), 16):
    print(f"{off:04x}  {msg[off:off + 16].hex(' ')}")
assert msg[-28:-8].hex() == "9aeaa70cbfd8cb56781ef2b5b2d3f249c1b571a2"   # RFC 5769 公布的 HMAC
assert msg[-4:].hex() == "e57a3bcf"                                        # RFC 5769 公布的 CRC
print("MESSAGE-INTEGRITY 與 FINGERPRINT 都和 RFC 5769 的測試向量一致")
print("原始訊息                  ", verify(msg, password))
print("用錯的 ice-pwd 驗證        ", verify(msg, b"wrong-password-0000000"))

forged = bytearray(msg)
forged[44:48] = struct.pack("!I", 0x7E0001FF)            # 竄改 PRIORITY 的值（offset 0x2c）
print("竄改 PRIORITY              ", verify(bytes(forged), password))
crc = (binascii.crc32(bytes(forged[:-8])) ^ FP_XOR) & 0xFFFFFFFF
forged[-4:] = struct.pack("!I", crc)                     # 攻擊者重算 CRC：任何人都算得出來
print("竄改後再重算 FINGERPRINT   ", verify(bytes(forged), password))
assert verify(msg, password) == (True, True) and verify(bytes(forged), password) == (True, False)
```

輸出：

```text
0000  00 01 00 58 21 12 a4 42 b7 e7 a7 01 bc 34 d6 86
0010  fa 87 df ae 80 22 00 10 53 54 55 4e 20 74 65 73
0020  74 20 63 6c 69 65 6e 74 00 24 00 04 6e 00 01 ff
0030  80 29 00 08 93 2f f9 b1 51 26 3b 36 00 06 00 09
0040  65 76 74 6a 3a 68 36 76 59 20 20 20 00 08 00 14
0050  9a ea a7 0c bf d8 cb 56 78 1e f2 b5 b2 d3 f2 49
0060  c1 b5 71 a2 80 28 00 04 e5 7a 3b cf
MESSAGE-INTEGRITY 與 FINGERPRINT 都和 RFC 5769 的測試向量一致
原始訊息                   (True, True)
用錯的 ice-pwd 驗證         (True, False)
竄改 PRIORITY               (False, False)
竄改後再重算 FINGERPRINT    (True, False)
```

hex dump 可以和位元圖逐格對照：`00 01` 是 Binding request、`00 58` 是長度 88，接著 magic cookie 與 transaction ID；`80 22` 是 SOFTWARE、`00 24` 是 PRIORITY、`80 29` 是 ICE-CONTROLLED、`00 06 00 09` 是 9 bytes 的 USERNAME，後面三個 `20` 是補齊的空白；最後是 MESSAGE-INTEGRITY 與 FINGERPRINT，兩者都和 RFC 5769 一致，代表「假裝包含」的處理正確。

下半段四行是重點。用錯的 ice-pwd 驗證時，FINGERPRINT 仍正確（CRC 不依賴密碼），MESSAGE-INTEGRITY 失敗；竄改 PRIORITY 後兩者都失敗；攻擊者竄改後**重算 CRC**，FINGERPRINT 又正確了，但 MESSAGE-INTEGRITY 依然失敗。FINGERPRINT 回答「這是不是 STUN」，MESSAGE-INTEGRITY 回答「是不是對的人送的、有沒有被改過」。

## 36.7 TURN：allocation、permission、channel 與成本

**TURN**（Traversal Using Relays around NAT）是 ICE 的最後一張牌：client 在公網伺服器上「租」一個位址，送到這裡的封包由伺服器轉給 client，client 的封包也由它代送。client 是主動連向 TURN 的，對 NAT 而言只是普通的對外連線，所以幾乎一定成功。

### Allocation：租一個中繼位址

```text
 學生瀏覽器 192.168.1.23:54400    NAT 198.51.100.23   TURN 203.0.113.50:3478        老師 198.51.100.201:50000
   │── ① Allocate（REQUESTED-TRANSPORT＝UDP，沒有帳密）───────►│                               │
   │◄─ ② 401 Unauthorized（REALM、NONCE）────────────────────────│                               │
   │── ③ Allocate＋USERNAME、REALM、NONCE、MESSAGE-INTEGRITY ──►│ 驗證帳密，配出 relay port      │
   │◄─ ④ success：XOR-RELAYED-ADDRESS 203.0.113.50:49152 ───────│                               │
   │       XOR-MAPPED-ADDRESS 198.51.100.23:50000、LIFETIME 600 │                               │
   │── ⑤ CreatePermission（XOR-PEER-ADDRESS 198.51.100.201）──►│ 記下：允許這個 IP              │
   │◄─ success ──────────────────────────────────────────────────│                               │
   │── ⑥ Send indication（peer＋DATA＝一個 ICE 檢查）──────────►│── 從 :49152 送出 UDP ────────►│
   │                                                              │◄── 回應送到 :49152 ──────────│
   │◄─ ⑦ Data indication（XOR-PEER-ADDRESS＋DATA）──────────────│ 來源 IP 有 permission：轉交   │
   │── ⑧ ChannelBind（0x4000 ↔ 198.51.100.201:50000）─────────►│                               │
   │══ ⑨ ChannelData 0x4000（只多 4 bytes）═════════════════════►│══════════════════════════════►│
   │── ⑩ Refresh（LIFETIME 600）：在到期前續租 ─────────────────►│                               │
```

① 第一個 Allocate 不帶帳密，② 伺服器回 401，附上 realm（認證範圍）與 nonce（一次性亂數，防重放）。③ client 用長期憑證算 MESSAGE-INTEGRITY 重送。④ 成功回應帶回 **XOR-RELAYED-ADDRESS**（relay candidate）、XOR-MAPPED-ADDRESS（順便成為 srflx）與 **LIFETIME**（預設 600 秒）。伺服器以 client 到 TURN 的五元組辨認 allocation。

⑤ TURN 預設不轉送任何外來封包，client 要為每個對方 IP 建立 **permission**（效期 300 秒）。permission 只比對 IP、不比對 port，這是刻意的：對方若在 symmetric NAT 後面，port 可能每次不同，比對 IP 才能讓 prflx 運作。⑥⑦ 最基本的傳送方式是 Send／Data indication：封包放在 DATA 屬性裡，以 XOR-PEER-ADDRESS 指定對方；TURN 收到對方的封包時確認來源 IP 有 permission，才包成 Data indication 交給 client。

⑧ 每個封包多 36 bytes，對每秒幾百個的影音封包太重。**ChannelBind** 把對方位址（IP 加 port）綁到一個 channel number（0x4000–0x4FFF，效期 600 秒，同時更新 permission），之後用 ⑨ **ChannelData** 傳送，只多 4 bytes。⑩ allocation 到期前送 Refresh 續租，LIFETIME 為 0 則是主動釋放。

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────────────────────┬───────────────────────────────┐
 │  Channel Number（0x4000–0x4FFF）│        Length（資料長度）      │
 ├───────────────────────────────┴───────────────────────────────┤
 │             Application Data（例如一個 SRTP 封包）            │
 │             在 TCP／TLS 上要補齊到 4 bytes 的倍數              │
 └───────────────────────────────────────────────────────────────┘
```

channel number 的範圍讓第一個 byte 落在 64–79，和 STUN、DTLS、RTP 都不重疊，可以用第一個 byte 分流。TCP／TLS 是沒有訊息邊界的 byte stream（第 11 章），接收方靠 Length 切訊息，所以要補齊。

| 狀態 | 預設效期 | 怎麼延長 | 過期的後果 |
|---|---|---|---|
| allocation | 600 秒（可在請求中要求不同值，伺服器決定上限） | Refresh | relay 位址消失，所有經過它的 pair 失效 |
| permission | 300 秒 | 再送 CreatePermission，或 ChannelBind | 對方送來的封包被 TURN 默默丟棄 |
| channel 綁定 | 600 秒 | 再送 ChannelBind | 改回 Send／Data indication，或通訊中斷 |
| nonce | 由伺服器決定 | 收到 438 Stale Nonce 時用新的 nonce 重送 | 請求被拒，需重新計算 MESSAGE-INTEGRITY |
| client 到 TURN 的 NAT mapping | 依 NAT 而定（UDP 可能只有 30 秒） | 定期有封包經過（Refresh、consent、媒體） | client 換了對外 port，TURN 認不出 allocation |

最後一列最常被忽略：學生的 NAT 若因閒置換了 mapping，TURN 看到陌生的五元組，舊的 allocation 等於失聯。通話中持續有媒體與 consent，通常沒事；gathering 後閒置太久才開始通話就可能遇到。

### 傳輸方式：UDP、TCP 與 TLS 443

client 到 TURN 可以走 UDP、TCP 或 TLS，TURN 到對方仍是 UDP。設定用 URL 表示：`turn:turn.shengsheng.example:3478?transport=udp`、`?transport=tcp`，以及 `turns:turn.shengsheng.example:443?transport=tcp`（`turns` 代表 TLS）。某高中只放行 TCP 443，很多防火牆還會檢查 443 上是不是 TLS，所以 TURN 要在 443 跑真正的 TLS，憑證要自動更新（第 19 章）。

走 TCP 的代價是 head-of-line blocking（第 12 章）：一個封包遺失，後面的影音都要等，畫面就會卡。所以 UDP 的 relay 優先序高於 TCP／TLS 的 relay。修正方案因此是保留 UDP 3478 給大多數人，加開 TLS 443 給被封鎖的網路。

### 短效憑證：不要把 TURN 帳密寫死在前端

TURN 帳密必須交給瀏覽器，等於公開，所以永久有效的固定帳密一外洩，任何人都能用你的 TURN。常見做法（來自 TURN REST API 草案，沒有成為 RFC，但多數實作支援）是後端與 TURN 共用秘密金鑰，每次通話前產生帶到期時間的帳密：username 是「到期時間:使用者 ID」，password 是對 username 算的 HMAC。這和第 30 章「讓憑證帶著到期時間並由 server 簽章」是同一個原則。

```python
import base64
import hashlib
import hmac
import struct

SHARED_SECRET = b"turn-secret-2026-10"        # 只存在 rt 後端與 TURN server，絕不下發到瀏覽器


def issue(user_id, now, ttl=3600):
    # 常見的「TURN REST API」慣例：username = 到期時間:使用者，password = base64(HMAC-SHA1(secret, username))
    username = f"{int(now) + ttl}:{user_id}"
    password = base64.b64encode(hmac.new(SHARED_SECRET, username.encode(), hashlib.sha1).digest()).decode()
    return username, password


def turn_accepts(username, password, now):
    expiry = int(username.split(":", 1)[0])
    expect = base64.b64encode(hmac.new(SHARED_SECRET, username.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(expect, password) and now < expiry


now = 1_790_000_000                            # 固定時間讓輸出可重現；真實程式用 time.time()
user, pwd = issue("student-0457", now)
print("iceServers 下發：", {"urls": ["turns:turn.shengsheng.example:443?transport=tcp"], "username": user, "credential": pwd})
print("一小時內使用：", turn_accepts(user, pwd, now + 600))
print("過期後使用：  ", turn_accepts(user, pwd, now + 3601))
print("竄改 username 延長期限：", turn_accepts(f"{now + 86400}:student-0457", pwd, now + 600))
assert turn_accepts(user, pwd, now + 600) and not turn_accepts(user, pwd, now + 3601)

# 中繼的封裝成本：Send indication 與 ChannelData
payload = 1200                                  # 一個 SRTP 封包
send_ind = 20 + (4 + 8) + 4                     # STUN header＋XOR-PEER-ADDRESS（IPv4）＋DATA 屬性 header
channel_data = struct.pack("!HH", 0x4000, payload)
print(f"\nSend indication 額外 {send_ind} bytes；ChannelData 只有 {len(channel_data)} bytes，首 byte 0x{channel_data[0]:02x}")

# 一堂一對一課的 TURN 流量（雙向各 1.54 Mbps、50 分鐘，碼率沿用第 37 章的估算；兩個方向都穿過 TURN）
mbps, minutes = 1.54, 50
per_direction_gb = mbps * 1e6 * minutes * 60 / 8 / 1e9
egress_gb = 2 * per_direction_gb               # TURN 收進一份、送出一份：兩個方向各送出一次
print(f"每堂課 TURN 送出 {egress_gb:.2f} GB；尖峰同時 2,000 堂、15% 走 TURN → 一節課約 {2000 * 0.15 * egress_gb:.0f} GB")
```

輸出：

```text
iceServers 下發： {'urls': ['turns:turn.shengsheng.example:443?transport=tcp'], 'username': '1790003600:student-0457', 'credential': 'ydm1TDGA980uWAtyIawqYAgEX4c='}
一小時內使用： True
過期後使用：   False
竄改 username 延長期限： False

Send indication 額外 36 bytes；ChannelData 只有 4 bytes，首 byte 0x40
每堂課 TURN 送出 1.16 GB；尖峰同時 2,000 堂、15% 走 TURN → 一節課約 346 GB
```

前四行是憑證的生命週期：username 前半是到期時間；一小時內通過、過期被拒；把到期時間改成一天後也會失敗，因為 HMAC 涵蓋整個 username。TURN 不必查資料庫，有共享金鑰就能驗證，可以水平擴展。

後兩行是成本。Send indication 每個封包多 36 bytes（20 header＋12 XOR-PEER-ADDRESS＋4 DATA header），ChannelData 只多 4 bytes。一堂 50 分鐘、雙向各 1.54 Mbps 的課走 TURN，伺服器要送出約 1.16 GB；晚上八點尖峰同時有約 2,000 堂一對一（第 37 章的估算），假設 15% 走 TURN（聲聲 Live 的假設值），一節課就要送出約 346 GB。單價依雲端而定，但數量級說明了 Joe 為什麼在意 relay 比例，也說明外洩的固定帳密有多危險。

> [!warning] TURN 也是一個 SSRF 入口
> TURN 會把封包送到「client 指定的任何 IP」。若 TURN 在 VPC 裡又不限制 peer，攻擊者拿合法帳密就能把 UDP 送進 10.20.0.0/16 的內部服務，甚至雲端 metadata 位址 169.254.169.254。Rita 要求拒絕所有私有、loopback、link-local 與 VPC 網段作為 peer。這和第 25 章 proxy 的開放轉送是同一類風險。

這些限制落實在 TURN 的設定檔裡：短效憑證的共享金鑰、relay port 範圍（security group 必須對外開放整段 UDP，否則 relay candidate 收得到卻永遠收不到封包）、peer 拒絕清單。TURN 的 relay 位址屬於某一台特定的機器，不能放在隨機分流的 LB 後面；具體的 coturn 設定、多台與多區域部署留到第 37 章。

## 36.8 ICE 連線檢查：優先序、配對與提名

有了雙方的 candidate，ICE 要回答三個問題：先測哪一對？怎麼測？選哪一對？答案來自兩個公式和一個狀態機。

### Candidate 的優先序公式

每個 candidate 的 priority 是一個 32 bit 整數：

```text
 priority ＝ 2^24 × type preference ＋ 2^8 × local preference ＋ 2^0 × (256 − component ID)

  bit:  31          24 23                           8 7            0
       ┌──────────────┬──────────────────────────────┬──────────────┐
       │type pref (8) │      local preference (16)   │ 256−comp (8) │
       │host 126      │ 同類型之間的偏好：           │ RTP＝1 → 255 │
       │prflx 110     │ 網卡、IPv4／IPv6、          │ RTCP＝2 → 254│
       │srflx 100     │ relay 的傳輸方式…           │              │
       │relay 0       │ 只有一張網卡時用 65535       │              │
       └──────────────┴──────────────────────────────┴──────────────┘
```

公式把三個欄位拼成一個整數，最高 8 bit 最重要。**type preference** 的建議值是 host 126、prflx 110、srflx 100、relay 0，所以任何非 relay 都比 relay 優先；prflx 高於 srflx，因為它是從真實檢查封包學到的。中間 16 bit 的 **local preference** 區分同類型的 candidate，例如偏好 Wi-Fi 勝過 VPN、UDP 的 relay 勝過 TLS 的 relay。最低 8 bit 讓 RTP（component 1）優先。只有一張網卡時：host 是 126×2²⁴＋65535×2⁸＋255＝2130706431，srflx 是 1694498815，relay 是 16777215。真實瀏覽器的 local preference 會納入網路類型等因素，所以 Chrome 的 host 常是 2122260223 這類值，最高 byte 仍是 126。

### Pair 的優先序：兩端必須算出同一個順序

一個 **candidate pair** 是「本地 candidate 加遠端 candidate」。雙方各自維護一份 pair 清單（**check list**），如果雙方排序不同，可能各自測了不同的路、各自選了不同的 pair。所以 pair 的優先序公式不看「本地／遠端」，而看「controlling／controlled」：

```text
 pair priority ＝ 2^32 × MIN(G, D) ＋ 2 × MAX(G, D) ＋ (G > D ? 1 : 0)
   G ＝ controlling 端那個 candidate 的 priority
   D ＝ controlled 端那個 candidate 的 priority
```

老師看「老師 host 對學生 srflx」時，G 仍是學生的 srflx，所以兩端算出相同的值。**MIN 放在最高位**是因為路徑品質由較差的一端決定：只要一端是 relay 就要經過 TURN，所以任何含 relay 的 pair 都排在最後。MAX 用來打破平手，最後一項讓兩個方向不會同分。

組 check list 還有一步常被忽略：**剪枝**。本地 srflx 沒有自己的 socket，封包一定從 base 送出，所以「本地 srflx 對 X」等於「本地 host 對 X」。ICE 把本地 srflx 換成 base 後刪掉重複的 pair；srflx 是**給對方用的**位址。

### 檢查怎麼送：一個帶密碼的 STUN Binding

**Connectivity check** 是從本地 base 對遠端 candidate 送的 STUN Binding request，最後同樣附上 FINGERPRINT，其餘屬性如下：

| 屬性 | 學生送給老師的值 | 用途 |
|---|---|---|
| USERNAME | `m1Sk:s7Kq`（老師的 ufrag：學生的 ufrag） | 讓老師確認這是給這次通話的檢查 |
| MESSAGE-INTEGRITY | 用**老師的** ice-pwd 算 HMAC-SHA1 | 證明送的人拿到了老師的 SDP |
| PRIORITY | 如果這個檢查讓對方學到 prflx，就用這個 priority | 讓 prflx 有正確的優先序 |
| ICE-CONTROLLING | 64 bit 隨機 tie-breaker | 宣告角色；雙方都自稱 controlling 時比大小 |
| USE-CANDIDATE | 只在提名時出現 | controlling 端說「就用這一對」 |

老師驗證 MESSAGE-INTEGRITY 後回 Binding success，XOR-MAPPED-ADDRESS 寫的是老師**看到**的來源，同樣以老師的 ice-pwd 算 MESSAGE-INTEGRITY。學生要確認回應來自當初送往的位址、抵達當初送出的 base（**對稱性檢查**）。若 XOR-MAPPED-ADDRESS 不在已知的本地 candidate 中，學生就學到本地 prflx；成功的結果記為 **valid pair**。

```text
 學生（controlling，symmetric NAT）                          老師（controlled，restricted cone NAT）
 base 100.72.18.9:54400 → NAT 198.51.100.200                 base 192.168.0.31:54400 → NAT 198.51.100.201
   │                                                                      │
   │── ① 檢查 → 老師 srflx 198.51.100.201:50000（從新 port :50007 出去）─►│ 老師的 NAT 還沒送過給學生：丟棄
   │                                                                      │
   │◄─ ② 老師的檢查 → 學生 srflx 198.51.100.200:50000 ─────────────────────│ NAT 會記下「送過給 198.51.100.200」
   │   學生的 NAT 是 APDF，:50000 只對 STUN server 送過：丟棄             │
   │                                                                      │
   │── ③ 重送 ① ────────────────────────────────────────────────────────►│ 這次 IP 符合（ADF 只看 IP）：放行
   │                                                                      │ 來源 :50007 不在學生的 candidate 裡
   │                                                                      │ → 學到遠端 prflx 198.51.100.200:50007
   │◄─ ④ Binding success（XOR-MAPPED-ADDRESS＝198.51.100.200:50007）───────│ → 立刻排一個 triggered check
   │   學生學到本地 prflx；valid pair：prflx ↔ 老師 srflx                 │
   │◄─ ⑤ triggered check → 198.51.100.200:50007 ───────────────────────────│ 學生的 NAT 有「:50007 送過給老師」：放行
   │── ⑥ Binding success ────────────────────────────────────────────────►│ 老師端也得到 valid pair
   │── ⑦ 提名：再送一次帶 USE-CANDIDATE 的檢查 ─────────────────────────►│ 雙方選定這一對
```

這是第 7 章「symmetric 對 restricted 打洞」的 ICE 版本。③ 讓老師學到**遠端 prflx**，④ 讓學生學到**本地 prflx**。⑤ 是 **triggered check**：收到檢查時，ICE 立刻把反方向的同一對排到佇列最前面。對方的封包剛在你的 NAT 留下紀錄，立刻回送，打洞最快也最容易成功。

### Check list 的狀態與 frozen 演算法

pair 的狀態有 **Frozen**（還不准測）、**Waiting**、**In-Progress**、**Succeeded**、**Failed**。ICE 每隔 **Ta**（RFC 8445 建議預設 50 ms）從 Waiting 中挑優先序最高的送一個檢查，避免一次湧出大量封包；沒有回應就依 RTO 重送，到上限才 Failed。**frozen 演算法**一開始每個 foundation 只放一個 pair 進 Waiting，成功後才解凍同 foundation 的其他 pair，因為它們通常一起成功或一起失敗。在 BUNDLE 下它的效果有限，但這是 webrtc-internals 中出現 Frozen 的原因。

### 角色、提名與選定

**controlling** 端負責提名，**controlled** 端接受，否則雙方可能各選各的。兩端都是完整實作時，送 offer 的一方是 controlling；若一方是 **ICE-lite**（只有 host candidate、只回應不主動檢查的簡化實作，有公網位址的 SFU 常用），完整實作的一方一定是 controlling。雙方都自稱 controlling 時，比較檢查中 64 bit 的 tie-breaker，數字小的一方改當 controlled（必要時以 487 Role Conflict 回應，通知對方換角色）。

RFC 8445 只保留 **regular nomination**：檢查照常進行，controlling 端認為「夠好了」，就對某個 valid pair 送帶 USE-CANDIDATE 的檢查，成功後成為 **selected pair**。「夠好了」由實作決定：等越久越可能等到更好的 pair，但使用者也多看一刻轉圈圈，動手做的模擬會呈現這個取捨。

> [!note] 選定之後 ICE 還在工作
> 選定後，ICE 每隔約 4～6 秒在選定路徑上送 Binding request，這是 **consent freshness**：確認對方仍同意接收。30 秒沒有回應就必須停止送媒體，避免對一個可能已換人使用的位址狂送；在那之前 `iceConnectionState` 會先變成 `disconnected`。這些封包也讓 NAT mapping 保持活著（第 7 章）。網路改變（Wi-Fi 換 4G）時舊 candidate 全部失效，要呼叫 `restartIce()` 做 **ICE restart**：新的 ufrag／pwd、重新收集與檢查。

### Trickle ICE 與 end-of-candidates

**Trickle ICE** 讓收集與檢查同時進行；「vanilla ICE」則等 gathering 完成才把所有 candidate 寫進 SDP，舊 SDK 的六秒多半耗在這裡。trickle 有兩個細節：candidate 可能比 SDP 先到，要先暫存，`setRemoteDescription()` 之後再 `addIceCandidate()`；對方要知道「沒有更多 candidate 了」才能放心宣告失敗，這就是 end-of-candidates（API 中 `icecandidate` 事件的 candidate 為 `null`）。

## 36.9 DTLS-SRTP：用指紋把金鑰綁在 signaling 上

WebRTC 規定媒體一定加密，沒有關閉的選項。但媒體跑在 UDP 上，不能直接用 TLS，兩個瀏覽器也沒有 CA 簽發的憑證。解法是 **DTLS-SRTP**：用 DTLS 交換金鑰，用 SDP 裡的 fingerprint 驗證對方憑證，再把匯出的金鑰交給 SRTP 加密媒體。

### DTLS：UDP 上的 TLS

**DTLS**（Datagram TLS）是能在會遺失、亂序的 datagram 上運作的 TLS。TCP 提供的保證得自己補上：記錄帶明確序號，handshake 訊息可切片，遺失時由計時器重送整個 flight（一組同方向的交握訊息），並可用 cookie 防止偽造來源的放大攻擊。

```text
  DTLS 1.2 記錄 header（13 bytes）
  ┌──────────────┬─────────────────┬──────────┬──────────────────────────────┬────────────┐
  │ Content Type │ Version         │ Epoch    │ Sequence Number              │ Length     │
  │ 1 byte       │ 2 bytes         │ 2 bytes  │ 6 bytes                      │ 2 bytes    │
  │ 20～23       │ 0xFEFD＝DTLS 1.2│ 每換一次 │ 每筆記錄遞增，接收端用來     │ 記錄內容   │
  │（22＝交握）  │                 │ 金鑰 +1  │ 偵測重放與排序               │ 的長度     │
  └──────────────┴─────────────────┴──────────┴──────────────────────────────┴────────────┘
```

和 TLS 的 5 bytes 記錄 header 相比，DTLS 多了 epoch 與 6 bytes 序號：TLS 的序號隱含在 TCP 的順序裡，DTLS 的記錄可能亂序，序號必須寫出來，接收端才能用滑動視窗丟棄重放。epoch 在切換金鑰時加一。

```text
 老師（DTLS client，setup:active）                           學生（DTLS server，setup:actpass）
   │── ClientHello（use_srtp：支援的 SRTP profile 清單）──────────────►│
   │◄─ ServerHello（選一個 profile）、Certificate（學生的自簽憑證）、   │
   │   ServerKeyExchange（ECDHE 公鑰）、CertificateRequest、ServerHelloDone
   │   → 比對學生憑證的 SHA-256 與 SDP 裡學生的 a=fingerprint           │
   │── Certificate（老師的自簽憑證）、ClientKeyExchange、CertificateVerify、
   │   ChangeCipherSpec、Finished ──────────────────────────────────────►│ → 比對老師憑證與老師的 a=fingerprint
   │◄─ ChangeCipherSpec、Finished ────────────────────────────────────────│
   │   雙方用 exporter 匯出 SRTP 金鑰，開始送 SRTP                        │
```

這是 DTLS 1.2 的完整交握，兩個 RTT。和第 18 章的 HTTPS 相比有三個差異：**雙向都出示憑證**，client 也要送 Certificate 與 CertificateVerify（用私鑰簽章證明持有）；憑證是**自簽**的，驗證方式是比對雜湊與 SDP 的 fingerprint；ClientHello 帶 **use_srtp** 擴充列出 SRTP 保護方式，ServerHello 選一個。開頭的 HelloVerifyRequest cookie 交換在 WebRTC 中是否出現依實作而定，因為 ICE 檢查已證明對方能收到封包。

DTLS 的角色由 `a=setup` 決定：offer 寫 `actpass`，answer 寫 `active`（當 client）或 `passive`。瀏覽器的 answer 通常是 `active`，所以老師是 DTLS client。這和 ICE 角色無關：學生是 ICE 的 controlling，卻是 DTLS 的 server，除錯時要分開記。

### Fingerprint：信任從哪裡來

自簽憑證誰都能產生，WebRTC 的安全性不靠憑證本身，而靠一條信任鏈：

```text
 ① 使用者登入聲聲 Live（第 26～29 章）
        │  HTTPS／WSS：伺服器憑證由 CA 驗證，JWT 證明身分
        ▼
 ② signaling 把老師的 SDP（含 a=fingerprint）完整送到學生端，且只送給這堂課的學生
        │
        ▼
 ③ DTLS 交握中，對方出示的憑證，其 SHA-256 必須等於 ② 收到的 fingerprint
        │  CertificateVerify 證明對方持有這張憑證的私鑰
        ▼
 ④ 交握結果匯出的 SRTP 金鑰，只有這兩端知道 → 媒體只有這兩端解得開
```

① ② 是 Web 的既有機制：TLS 保護 signaling，身分與授權保證 SDP 只在正確的兩人之間交換。③ 把信任接到媒體路徑：fingerprint 沒被換掉，攔截 UDP 的中間人就無法通過比對。④ 是 ECDHE 的結果，具前向保密（第 17 章）。結論：**DTLS-SRTP 的安全性等於 signaling 的安全性**。signaling 被入侵或把 SDP 轉錯人，攻擊者就能換掉 fingerprint，和雙方各建一條 DTLS 在中間轉送。

下面的程式計算老師自簽憑證的 SDP fingerprint，在「交握」時比對老師與中間人的憑證，再用 TLS 1.2 的 PRF 實作 DTLS-SRTP 的 exporter。

```python
import hashlib
import hmac
import ssl

# 老師瀏覽器產生的自簽 ECDSA P-256 憑證（每次建立 RTCPeerConnection 都可能是新的）
TEACHER_PEM = """-----BEGIN CERTIFICATE-----
MIIBdjCCAR2gAwIBAgIUYwYtDj1Gx1IN+Gqvrr0hxtA1cIQwCgYIKoZIzj0EAwIw
ETEPMA0GA1UEAwwGV2ViUlRDMB4XDTI2MTAwMjE0MDQzNloXDTI2MTEwMTE0MDQz
NlowETEPMA0GA1UEAwwGV2ViUlRDMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE
FjaSzYQqDMNQwehanegSaHVU7PokrV332chHLJIloZIccxylA/SKc4gs0OkPT/MQ
6KH5LmInxV9whHxPbMLOgqNTMFEwHQYDVR0OBBYEFEsfCAAIwLeAOFXDy6AIwoag
6Bg2MB8GA1UdIwQYMBaAFEsfCAAIwLeAOFXDy6AIwoag6Bg2MA8GA1UdEwEB/wQF
MAMBAf8wCgYIKoZIzj0EAwIDRwAwRAIgHKiykm2ngNFqpI3fqfshmDXbCdeO2wYn
pV8y/J1I+BcCIB9JDpd/PKxq7B2Vslvd1QhYMa7Iu9aG50nCitji7gDM
-----END CERTIFICATE-----"""
# 中間人自己產生的另一張憑證：一樣自簽、一樣 CN=WebRTC，外觀上毫無破綻
ATTACKER_PEM = """-----BEGIN CERTIFICATE-----
MIIBdzCCAR2gAwIBAgIUd7dvrPcYFFlnFOOsogh8aUa61WAwCgYIKoZIzj0EAwIw
ETEPMA0GA1UEAwwGV2ViUlRDMB4XDTI2MTAwMjE0MDQ0NFoXDTI2MTEwMTE0MDQ0
NFowETEPMA0GA1UEAwwGV2ViUlRDMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE
CrXfnQ3HM04iOdb3u6W+8XT83dEQ3e0+A6mzqiBltYeVWvlvKcrTEahDjYMogQkE
baEjDLWJN67WD1omGoO4NaNTMFEwHQYDVR0OBBYEFOrM1sbFPfB7PKkxmgmFwClq
bzFcMB8GA1UdIwQYMBaAFOrM1sbFPfB7PKkxmgmFwClqbzFcMA8GA1UdEwEB/wQF
MAMBAf8wCgYIKoZIzj0EAwIDSAAwRQIgBUezZgHSJyqvhxsylXoygKS22c0pB9tK
Zok7flFxdWQCIQCRusQ1G/Xf+fKbpKXbJiigKzglv2HNsENdKOeQS7tybw==
-----END CERTIFICATE-----"""


def sdp_fingerprint(pem):
    der = ssl.PEM_cert_to_DER_cert(pem)
    digest = hashlib.sha256(der).hexdigest().upper()
    return len(der), "a=fingerprint:sha-256 " + ":".join(digest[i:i + 2] for i in range(0, 64, 2))


der_len, line_in_answer = sdp_fingerprint(TEACHER_PEM)    # 經由 signaling（wss）送到學生端
print(f"憑證 DER {der_len} bytes")
print(line_in_answer)


def dtls_peer_ok(presented_pem, expected_line):
    """學生端在 DTLS 交握收到對方 Certificate 後做的檢查：不看 CA，只比對指紋。"""
    return hmac.compare_digest(sdp_fingerprint(presented_pem)[1], expected_line)


print("交握出示老師的憑證：", dtls_peer_ok(TEACHER_PEM, line_in_answer))
print("交握出示中間人的憑證：", dtls_peer_ok(ATTACKER_PEM, line_in_answer))
assert dtls_peer_ok(TEACHER_PEM, line_in_answer) and not dtls_peer_ok(ATTACKER_PEM, line_in_answer)


def p_sha256(secret, seed, length):
    # TLS 1.2 PRF（RFC 5246 §5）：A(i) = HMAC(secret, A(i-1))，輸出 = HMAC(secret, A(i) + seed) 串接
    out, a = b"", seed
    while len(out) < length:
        a = hmac.new(secret, a, hashlib.sha256).digest()
        out += hmac.new(secret, a + seed, hashlib.sha256).digest()
    return out[:length]


# 交握完成後，雙方都持有相同的 master secret 與兩個 random（這裡用固定值示意）
master_secret = bytes(range(48))
client_random, server_random = b"\x11" * 32, b"\x22" * 32
for profile, key_len, salt_len in [("SRTP_AES128_CM_HMAC_SHA1_80", 16, 14), ("SRTP_AEAD_AES_128_GCM", 16, 12)]:
    km = p_sha256(master_secret, b"EXTRACTOR-dtls_srtp" + client_random + server_random, 2 * (key_len + salt_len))
    ck, sk = km[:key_len], km[key_len:2 * key_len]
    cs, ss = km[2 * key_len:2 * key_len + salt_len], km[2 * key_len + salt_len:]
    print(f"{profile}: 共 {len(km)} bytes → client key {ck[:4].hex()}… salt {len(cs)} B｜server key {sk[:4].hex()}… salt {len(ss)} B")
    assert len(km) == 2 * (key_len + salt_len) and ck != sk
```

輸出：

```text
憑證 DER 378 bytes
a=fingerprint:sha-256 43:C4:8C:5E:89:02:9B:9C:06:01:1A:0F:3C:14:28:AE:BA:FB:EF:DC:56:3F:AE:02:14:C4:29:3A:EE:77:73:75
交握出示老師的憑證： True
交握出示中間人的憑證： False
SRTP_AES128_CM_HMAC_SHA1_80: 共 60 bytes → client key 41840565… salt 14 B｜server key 49397dfa… salt 14 B
SRTP_AEAD_AES_128_GCM: 共 56 bytes → client key 41840565… salt 12 B｜server key 49397dfa… salt 12 B
```

這張 ECDSA P-256 憑證只有 378 bytes，第二行就是寫進 SDP 的 fingerprint。兩張憑證都是自簽、都叫 `CN=WebRTC`，唯一能區分的就是雜湊，所以中間人的憑證比對失敗。

後兩行是金鑰匯出：交握後雙方有同一個主密鑰（TLS 1.2 的 `master_secret`），exporter 以標籤 `EXTRACTOR-dtls_srtp` 加上雙方 random 算出金鑰材料，依序切成 client 主金鑰、server 主金鑰、client salt、server salt。AES-CM 需要 16＋14 bytes，共 60；AES-GCM 需要 16＋12 bytes，共 56；前 16 bytes 相同是因為 PRF 輸出同一串、只是切法不同。老師（DTLS client）用 client key 加密送出的媒體，反方向用 server key。

### SRTP：只加密 payload 的 RTP

**SRTP**（Secure RTP）在 RTP 封包上加密與驗證。它沒有把 RTP 包進 DTLS 記錄，而是直接改造 RTP 封包本身：

```text
 ┌──────────────────────────────────────────────┐ ◄─┐
 │ RTP header（12 bytes 起）：V、PT、sequence、  │   │
 │ timestamp、SSRC、header extension（明文）     │   │ 驗證範圍
 ├──────────────────────────────────────────────┤   │（auth tag 涵蓋）
 │ RTP payload（加密）                           │ ◄─┤ 加密範圍
 │ 例如一個 Opus frame 或一段 H.264 NAL          │   │
 ├──────────────────────────────────────────────┤ ◄─┘
 │ authentication tag                            │
 │ HMAC-SHA1-80：10 bytes；AES-GCM：16 bytes      │
 └──────────────────────────────────────────────┘
```

header 明文、payload 加密、整個封包由 tag 保護，理由有三。**省頻寬**：每個封包只多 10 或 16 bytes。**可獨立解密**：IV 由 SSRC 與 48 bit 的封包 index（sequence 加 rollover counter）推導，掉封包不影響後續。**中間設備看得到 header**：SFU 要讀 sequence、timestamp、SSRC 才能轉發（第 37 章）。代價是中繼資料外露，例如 audio level extension 會透露誰在說話（可選擇加密 header extension）。SFU 會解密再加密，所以這是逐段加密而非端到端，要做到端到端需在應用層再加一層（例如 SFrame，第 37 章）。RTCP 對應 SRTCP；接收端也要記住最近的 index 以丟棄重放。

> [!note] 2026 現況
> 截至 2026 年 10 月（依 2026 年 10 月查證）：WebRTC 1.0 是 W3C Recommendation，最新版本日期 2025-03-13；JSEP 現行版本是 RFC 9429（2024 年，取代 RFC 8829）；推流的 WHIP 已是 RFC 9725（2025 年），沿用本章的 ICE 與 DTLS-SRTP、signaling 換成 HTTP POST（第 38 章），WHEP 仍是 draft。DTLS 1.3 可把交握縮短為一個 RTT，但 WebRTC 部署仍以 DTLS 1.2 為主，各瀏覽器的導入進度本書未逐一查證；請以 `getStats()` 中 transport 的 `tlsVersion`、`dtlsCipher`、`srtpCipher` 確認。

### 憑證大小與 MTU

WebRTC 把封包控制在約 1200 bytes（第 8 章），過大的 handshake 訊息由 DTLS 自己切片；任何一片遺失，整個 flight 要等計時器到期重送，規格建議的初始值是 1 秒（實作可更短）。上面的 ECDSA 憑證 378 bytes，同樣內容的 RSA 2048 約 775 bytes，交握封包越少，在丟包網路上越快完成，這是瀏覽器預設用 ECDSA 的原因之一。

### 同一個 port 上的四種封包

36.3 節提過，STUN、DTLS、TURN ChannelData 與 SRTP 共用同一個 UDP port。接收端依第一個 byte 分流，各範圍由規格事先劃分好，彼此不重疊：

```python
import struct

def classify(packet):
    """同一個 UDP port 上同時跑 STUN、DTLS、TURN ChannelData、SRTP：只看第一個 byte 就分得開。"""
    b = packet[0]
    if b <= 3:
        return "STUN（ICE 檢查、consent）"
    if 20 <= b <= 63:
        return "DTLS（交握，或 SCTP data channel）"
    if 64 <= b <= 79:
        return "TURN ChannelData"
    if 128 <= b <= 191:
        return "RTCP（SRTCP）" if 192 <= packet[1] <= 223 else "RTP（SRTP）"
    return "不認得：丟棄"

samples = {
    "Binding request": struct.pack("!HHI", 0x0001, 0, 0x2112A442) + bytes(12),
    "DTLS ClientHello": bytes([22, 0xFE, 0xFD]) + bytes(10),         # content type 22＝handshake，版本 DTLS 1.2
    "DTLS application_data": bytes([23, 0xFE, 0xFD]) + bytes(10),    # data channel 的 SCTP 封包包在這裡面
    "ChannelData": struct.pack("!HH", 0x4000, 4) + b"ping",
    "SRTP（Opus，PT 111）": bytes([0x80, 111]) + bytes(10),
    "SRTCP（Receiver Report）": bytes([0x81, 201]) + bytes(6),
}
for name, pkt in samples.items():
    print(f"首 byte {pkt[0]:>3}（0x{pkt[0]:02x}）{name:<24} → {classify(pkt)}")
assert classify(samples["SRTCP（Receiver Report）"]).startswith("RTCP")
```

輸出：

```text
首 byte   0（0x00）Binding request          → STUN（ICE 檢查、consent）
首 byte  22（0x16）DTLS ClientHello         → DTLS（交握，或 SCTP data channel）
首 byte  23（0x17）DTLS application_data    → DTLS（交握，或 SCTP data channel）
首 byte  64（0x40）ChannelData              → TURN ChannelData
首 byte 128（0x80）SRTP（Opus，PT 111）        → RTP（SRTP）
首 byte 129（0x81）SRTCP（Receiver Report）   → RTCP（SRTCP）
```

STUN 前兩個 bit 是 0（0–3）；DTLS 的 content type 是 20–23（範圍保留到 63）；ChannelData 是 64–79；RTP 版本為 2，第一個 byte 在 128–191。rtcp-mux 時再看第二個 byte：RTCP 的 packet type 是 192–223，RTP 的 payload type 刻意避開這個範圍（第 34 章）。data channel 在外面看起來就是 DTLS 的 application_data（23）。

## 36.10 Data channel：SCTP over DTLS

**data channel** 讓 WebRTC 在同一條連線上傳送任意資料。API 很像 WebSocket（`send()`、`onmessage`），底下卻是 **SCTP**（Stream Control Transmission Protocol）跑在 DTLS 上、DTLS 跑在 ICE 選出的 UDP 路徑上。

選 SCTP 是因為它剛好具備所需的特性：以**訊息**為單位；一個 association 裡有多條**獨立的 stream**，一條掉封包不會擋住其他條；支援**部分可靠**（限制重送次數或存活時間）；內建擁塞控制。SCTP 直接跑在 IP 上時很多 NAT 不認得，包在 DTLS 與 UDP 裡就能走任何 ICE 打通的路徑；瀏覽器在使用者空間實作它。

### DCEP：開一條 data channel

SDP 只協商一個 SCTP association（`a=sctp-port:5000`），不協商個別 channel。呼叫 `createDataChannel()` 時，瀏覽器挑一條 stream，送 **DCEP**（Data Channel Establishment Protocol）的 DATA_CHANNEL_OPEN 告知名稱與可靠性設定，對方回 DATA_CHANNEL_ACK。DTLS client 只用偶數 stream ID、server 只用奇數，避免撞號；事先約定（`negotiated: true` 加固定 `id`）則可跳過 DCEP。

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────┬───────────────┬───────────────────────────────┐
 │ Message Type  │ Channel Type  │           Priority            │
 │ 0x03＝OPEN    │ 最高位元＝不保證順序                           │
 ├───────────────┴───────────────┴───────────────────────────────┤
 │      Reliability Parameter（重送次數，或存活毫秒數）          │
 ├───────────────────────────────┬───────────────────────────────┤
 │         Label Length          │        Protocol Length        │
 ├───────────────────────────────┴───────────────────────────────┤
 │           Label（channel 名稱）＋ Protocol（子協定名稱）        │
 └───────────────────────────────────────────────────────────────┘
```

Channel Type 的低位元決定可靠性（0x00 可靠、0x01 限制重送次數、0x02 限制存活時間），最高位元 0x80 代表不保證順序；Reliability Parameter 依類型解讀為次數或毫秒。Protocol 是可選的子協定名稱，概念同 WebSocket 的 subprotocol（第 32 章）。DCEP 用 SCTP 的 PPID（payload protocol identifier）50 標示，文字訊息 51、二進位 53，接收端據此決定給字串還是 ArrayBuffer。

```python
import struct

OPEN, ACK = 0x03, 0x02
PPID = {"DCEP": 50, "string": 51, "binary": 53}       # SCTP payload protocol identifier
CHANNEL_TYPES = {0x00: "reliable", 0x80: "reliable, unordered",
                 0x01: "maxRetransmits", 0x81: "maxRetransmits, unordered",
                 0x02: "maxPacketLifeTime", 0x82: "maxPacketLifeTime, unordered"}


def dcep_open(label, protocol="", ordered=True, max_retransmits=None, max_life_ms=None, priority=256):
    ctype, param = 0x00, 0
    if max_retransmits is not None:
        ctype, param = 0x01, max_retransmits
    elif max_life_ms is not None:
        ctype, param = 0x02, max_life_ms
    if not ordered:
        ctype |= 0x80                                  # 最高位元＝不保證順序
    lab, proto = label.encode(), protocol.encode()
    return struct.pack("!BBHIHH", OPEN, ctype, priority, param, len(lab), len(proto)) + lab + proto


def parse(msg):
    mtype, ctype, prio, param, llen, plen = struct.unpack("!BBHIHH", msg[:12])
    assert mtype == OPEN
    label = msg[12:12 + llen].decode()
    return {"label": label, "type": CHANNEL_TYPES[ctype], "param": param, "priority": prio,
            "protocol": msg[12 + llen:12 + llen + plen].decode()}


# 瀏覽器端的 createDataChannel("cursor", {ordered: false, maxRetransmits: 0}) 大致會送出這樣的訊息
for msg in (dcep_open("cursor", ordered=False, max_retransmits=0),
            dcep_open("chat", protocol="ss-chat.v1"),
            dcep_open("handout", max_life_ms=3000)):
    print(f"{msg.hex(' '):<64} → {parse(msg)}")
assert parse(dcep_open("cursor", ordered=False, max_retransmits=0))["type"] == "maxRetransmits, unordered"
print("ACK 只有 1 byte：", bytes([ACK]).hex(), f"；DCEP 用 PPID {PPID['DCEP']}，文字訊息 {PPID['string']}，二進位 {PPID['binary']}")
```

輸出：

```text
03 81 01 00 00 00 00 00 00 06 00 00 63 75 72 73 6f 72            → {'label': 'cursor', 'type': 'maxRetransmits, unordered', 'param': 0, 'priority': 256, 'protocol': ''}
03 00 01 00 00 00 00 00 00 04 00 0a 63 68 61 74 73 73 2d 63 68 61 74 2e 76 31 → {'label': 'chat', 'type': 'reliable', 'param': 0, 'priority': 256, 'protocol': 'ss-chat.v1'}
03 02 01 00 00 00 0b b8 00 07 00 00 68 61 6e 64 6f 75 74         → {'label': 'handout', 'type': 'maxPacketLifeTime', 'param': 3000, 'priority': 256, 'protocol': ''}
ACK 只有 1 byte： 02 ；DCEP 用 PPID 50，文字訊息 51，二進位 53
```

第一個訊息的 channel type `0x81` 是「限制重送次數、不保證順序」，次數 0 代表送一次就算；第二個是預設的可靠有序 channel；第三個存活 3000 毫秒（`00 00 0b b8`）。

| 用途 | 設定 | 為什麼 |
|---|---|---|
| 白板游標、遊戲狀態 | `ordered: false, maxRetransmits: 0` | 只在乎最新的位置，舊的重送到了也沒用 |
| 聊天、檔案傳輸 | 預設（可靠、有序） | 一個字都不能少，順序也要對 |
| 即時字幕、短時效提示 | `maxPacketLifeTime: 3000` | 晚於幾秒就失去意義，但能到的盡量到 |
| 大量資料（講義檔） | 可靠、有序，應用層切成 16 KiB 左右的區塊，看 `bufferedAmount` 控制送出速度 | 避免單一訊息過大與送出 buffer 爆掉 |

最後一列的兩個細節：`a=max-message-size` 宣告對方能收的上限，超過時 `send()` 直接拋錯，跨瀏覽器的保守做法是切成 16 KiB 左右；`send()` 只是放進送出 buffer，要用 `bufferedAmountLowThreshold` 與 `bufferedamountlow` 事件做 backpressure（同第 33 章）。`maxRetransmits` 與 `maxPacketLifeTime` 只能二選一。

聲聲 Live 的聊天與白板仍走 WebSocket（第 32、33 章），因為要經過伺服器紀錄、審核與 fan-out；P2P 的 data channel 不經伺服器，適合只有兩端在乎、要求低延遲的資料，例如老師的游標。低延遲換來的是伺服器看不到、記錄不到。

## 36.11 動手做：STUN server、candidate 優先序與 ICE 模擬

三段程式都只用標準函式庫、只在 127.0.0.1 上執行：一個真的 STUN server 與 client、一對一課的 candidate 與 check list，以及把第 7 章 NAT 模型接上 ICE 的模擬。

### 程式一：STUN Binding 的 server 與 client

server 驗證 FINGERPRINT 後，把 `recvfrom()` 看到的來源位址以 XOR-MAPPED-ADDRESS 寫進回應。client 先送一個 CRC 被弄壞的請求，再送正確的請求。127.0.0.1 上沒有 NAT，server 看到的就是 client 自己的位址，正好用來驗證編解碼。

```python
import binascii
import ipaddress
import socket
import struct
import threading

MAGIC = 0x2112A442
BINDING_REQUEST, BINDING_SUCCESS = 0x0001, 0x0101
XOR_MAPPED_ADDRESS, SOFTWARE, FINGERPRINT = 0x0020, 0x8022, 0x8028
FP_XOR = 0x5354554E                      # ASCII 的 "STUN"


def attr(atype, value):
    return struct.pack("!HH", atype, len(value)) + value + b"\x00" * (-len(value) % 4)


def build(msg_type, txid, attrs):
    body = b"".join(attr(t, v) for t, v in attrs)
    # FINGERPRINT 要最後一個：先把長度欄位算進它自己的 8 bytes，再對前面所有內容算 CRC-32
    head = struct.pack("!HHI", msg_type, len(body) + 8, MAGIC) + txid
    crc = (binascii.crc32(head + body) ^ FP_XOR) & 0xFFFFFFFF
    return head + body + attr(FINGERPRINT, struct.pack("!I", crc))


def parse(data):
    if len(data) < 20 or data[0] & 0xC0:             # 前兩個 bit 必須是 0
        raise ValueError("不是 STUN 訊息")
    msg_type, length, cookie = struct.unpack("!HHI", data[:8])
    if cookie != MAGIC or length % 4 or 20 + length != len(data):
        raise ValueError("magic cookie 或長度不對")
    attrs, i = {}, 20
    while i < len(data):
        atype, alen = struct.unpack("!HH", data[i:i + 4])
        value = data[i + 4:i + 4 + alen]
        if atype == FINGERPRINT:
            expect = (binascii.crc32(data[:i]) ^ FP_XOR) & 0xFFFFFFFF
            if i + 8 != len(data) or struct.unpack("!I", value)[0] != expect:
                raise ValueError("FINGERPRINT 不符")
        attrs[atype] = value
        i += 4 + alen + (-alen % 4)
    return msg_type, data[8:20], attrs


def xor_address(ip, port, txid):
    addr = ipaddress.ip_address(ip)
    key = struct.pack("!I", MAGIC) + (txid if addr.version == 6 else b"")   # IPv6 連 transaction ID 一起 XOR
    xaddr = bytes(a ^ k for a, k in zip(addr.packed, key))
    return struct.pack("!BBH", 0, 1 if addr.version == 4 else 2, port ^ (MAGIC >> 16)) + xaddr


def unxor_address(value, txid):
    _, family, xport = struct.unpack("!BBH", value[:4])
    key = struct.pack("!I", MAGIC) + (txid if family == 2 else b"")
    raw = bytes(a ^ k for a, k in zip(value[4:], key))
    return str(ipaddress.ip_address(raw)), xport ^ (MAGIC >> 16)


def stun_server(sock, log):
    while True:
        data, addr = sock.recvfrom(2048)
        if data == b"bye":
            return
        try:
            msg_type, txid, _ = parse(data)
        except ValueError as exc:
            log.append(f"server 丟棄來自 {addr[1]} 的封包：{exc}")   # 不回錯誤，避免被當成反射放大器
            continue
        if msg_type == BINDING_REQUEST:
            reply = build(BINDING_SUCCESS, txid, [(XOR_MAPPED_ADDRESS, xor_address(*addr, txid)),
                                                  (SOFTWARE, b"shengsheng-stun")])
            sock.sendto(reply, addr)


srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
srv.bind(("127.0.0.1", 0))
log = []
t = threading.Thread(target=stun_server, args=(srv, log))
t.start()

cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cli.bind(("127.0.0.1", 0))
cli.settimeout(0.3)
txid = bytes.fromhex("5a5a0457c0ffee0000008812")  # 為了讓輸出固定才寫死；真實程式必須用 os.urandom(12)
request = build(BINDING_REQUEST, txid, [])
bad = bytearray(request); bad[-1] ^= 0xFF          # 弄壞 CRC：模擬傳輸中被改動
cli.sendto(bytes(bad), srv.getsockname())
cli.sendto(request, srv.getsockname())
reply, _ = cli.recvfrom(2048)
msg_type, rtxid, attrs = parse(reply)
assert msg_type == BINDING_SUCCESS and rtxid == txid      # 用 transaction ID 配對請求與回應
mapped = unxor_address(attrs[XOR_MAPPED_ADDRESS], txid)
assert mapped == cli.getsockname()

print("request ", request[:4].hex(" "), "|", request[4:8].hex(" "), "|", "txid(12)", "|", request[20:].hex(" "))
print("response", reply[:4].hex(" "), "|", reply[4:8].hex(" "), "|", "txid(12)", "|", reply[20:32].hex(" "), "| ...")
print("XOR-MAPPED-ADDRESS 解出", mapped, "＝ client 的 getsockname()")
print("SOFTWARE", attrs[SOFTWARE].decode())
print(*log, sep="\n")

# 不經網路，驗證 IPv6 與第 7 章的公網位址也能正確來回
for ip, port in [("198.51.100.23", 50000), ("2001:db8:23::23", 50000)]:
    enc = xor_address(ip, port, txid)
    assert unxor_address(enc, txid) == (ip, port)
    print(f"{'[' + ip + ']' if ':' in ip else ip:>17}:{port} → 線上的 bytes {enc[4:8].hex(' ')}{' ...' if len(enc) > 8 else ''}（port 欄 {enc[2:4].hex(' ')}）")

cli.sendto(b"bye", srv.getsockname())
t.join(); srv.close(); cli.close()
```

輸出（client 的 port 由系統分配，每次執行不同，第二行 XOR 過的 port 與第三、五行的 port 也會跟著變）：

```text
request  00 01 00 08 | 21 12 a4 42 | txid(12) | 80 28 00 04 25 12 56 00
response 01 01 00 28 | 21 12 a4 42 | txid(12) | 00 20 00 08 00 01 d6 ac 5e 12 a4 43 | ...
XOR-MAPPED-ADDRESS 解出 ('127.0.0.1', 63422) ＝ client 的 getsockname()
SOFTWARE shengsheng-stun
server 丟棄來自 63422 的封包：FINGERPRINT 不符
    198.51.100.23:50000 → 線上的 bytes e7 21 c0 55（port 欄 e2 42）
[2001:db8:23::23]:50000 → 線上的 bytes 01 13 a9 fa ...（port 欄 e2 42）
```

第一行的請求只有 28 bytes：Binding request，長度 8 只含 FINGERPRINT，瀏覽器問 STUN server 時送的差不多就是這樣。第二行的回應長度 0x28＝40 bytes：XOR-MAPPED-ADDRESS（12）、SOFTWARE（15 補齊到 16，加 header 共 20）、FINGERPRINT（8）；`5e 12 a4 43` 是 127.0.0.1（`7f 00 00 01`）XOR magic cookie。第三行證明解碼結果等於 client 的 `getsockname()`。

第五行顯示壞掉的封包被丟棄。server 刻意**不回應**錯誤：UDP 來源可以偽造，對每個爛封包都回應，會讓 STUN server 變成反射攻擊的幫兇。最後兩行驗證 36.6 節的手算；IPv6 位址的後 12 bytes 和 transaction ID XOR，所以會隨 transaction ID 改變。程式寫死 transaction ID 只為讓輸出可重現，真實實作必須用 `os.urandom(12)`。

### 程式二：candidate 與 check list 的優先序

第二段替學生與老師各產生三個 candidate，印出學生的 candidate 行，再組出學生端的 check list。

```python
import binascii

TYPE_PREF = {"host": 126, "prflx": 110, "srflx": 100, "relay": 0}   # RFC 8445 建議值


def priority(kind, local_pref=65535, component=1):
    # 2^24 × type preference ＋ 2^8 × local preference ＋ (256 − component ID)
    return (TYPE_PREF[kind] << 24) + (local_pref << 8) + (256 - component)


def pair_priority(g, d):
    # G：controlling 端的 candidate priority；D：controlled 端。兩端算出來的值一模一樣
    return (1 << 32) * min(g, d) + 2 * max(g, d) + (1 if g > d else 0)


def foundation(kind, base_ip, server=""):
    # 同類型、同 base、同一台 STUN/TURN server → 同 foundation（示意：用 CRC32 產生短字串）
    return str(binascii.crc32(f"{kind}|{base_ip}|{server}|udp".encode()))


def candidate_line(kind, ip, port, base=None, server="", rel=None):
    p = priority(kind)
    line = f"a=candidate:{foundation(kind, base or ip, server)} 1 udp {p} {ip} {port} typ {kind}"
    return line + (f" raddr {rel[0]} rport {rel[1]}" if rel else ""), p


TURN = "turn.shengsheng.example"
student = [("host", "192.168.1.23", 54400, None, "", None),
           ("srflx", "198.51.100.23", 50000, "192.168.1.23", TURN, ("192.168.1.23", 54400)),
           ("relay", "203.0.113.50", 49152, "192.168.1.23", TURN, ("198.51.100.23", 50000))]
teacher = [("host", "192.168.0.31", 54400, None, "", None),
           ("srflx", "198.51.100.201", 50000, "192.168.0.31", TURN, ("192.168.0.31", 54400)),
           ("relay", "203.0.113.50", 49154, "192.168.0.31", TURN, ("198.51.100.201", 50000))]

print("學生（controlling）送出的 candidate：")
s_cands = []
for c in student:
    line, p = candidate_line(*c)
    s_cands.append((c[0], f"{c[1]}:{c[2]}", p))
    print(" ", line)
t_cands = [(c[0], f"{c[1]}:{c[2]}", candidate_line(*c)[1]) for c in teacher]

for kind in TYPE_PREF:
    p = priority(kind)
    print(f"{kind:>5}: {TYPE_PREF[kind]:>3}×2^24 + 65535×2^8 + 255 = {p:>10}  (0x{p:08x})")
assert priority("host") == 2130706431 and priority("relay") == 16777215

raw = [(pair_priority(s[2], t[2]), s, t) for s in s_cands for t in t_cands]
# 剪枝：本地 srflx 的封包其實從 base（host）送出，換成 base 後與 host 的 pair 重複，只留優先序高的
pairs, seen = [], set()
for pp, s, t in sorted(raw, reverse=True):
    s = s_cands[0] if s[0] == "srflx" else s
    if (s[1], t[1]) not in seen:
        seen.add((s[1], t[1]))
        pairs.append((pp, s, t))
print(f"\n學生端的 check list（{len(raw)} 個 pair 剪枝後剩 {len(pairs)} 個，依 pair priority 由高到低）：")
for rank, (pp, s, t) in enumerate(pairs, 1):
    print(f"{rank}. {pp:>20}  {s[0]:>5} {s[1]:<20} → {t[0]:<5} {t[1]}")

# 老師端（controlled）用同一個公式、把 G/D 對調填入，排序完全相同：兩端才會朝同一個 pair 收斂
teacher_view = sorted((pair_priority(s[2], t[2]) for s in s_cands for t in t_cands), reverse=True)
assert teacher_view == sorted((p[0] for p in raw), reverse=True)
# 「min 優先」：只要有一端是 relay，pair 就排在所有不含 relay 的 pair 之後
kinds = [(s[0], t[0]) for _, s, t in pairs]
assert kinds.index(("host", "srflx")) < kinds.index(("host", "relay")) and len(pairs) == 6
print("\n兩端排序一致；任何含 relay 的 pair 都排在不含 relay 的 pair 之後")
```

輸出：

```text
學生（controlling）送出的 candidate：
  a=candidate:1010154577 1 udp 2130706431 192.168.1.23 54400 typ host
  a=candidate:2499406306 1 udp 1694498815 198.51.100.23 50000 typ srflx raddr 192.168.1.23 rport 54400
  a=candidate:2760156015 1 udp 16777215 203.0.113.50 49152 typ relay raddr 198.51.100.23 rport 50000
 host: 126×2^24 + 65535×2^8 + 255 = 2130706431  (0x7effffff)
prflx: 110×2^24 + 65535×2^8 + 255 = 1862270975  (0x6effffff)
srflx: 100×2^24 + 65535×2^8 + 255 = 1694498815  (0x64ffffff)
relay:   0×2^24 + 65535×2^8 + 255 =   16777215  (0x00ffffff)

學生端的 check list（9 個 pair 剪枝後剩 6 個，依 pair priority 由高到低）：
1.  9151314442783293438   host 192.168.1.23:54400   → host  192.168.0.31:54400
2.  7277816997797167103   host 192.168.1.23:54400   → srflx 198.51.100.201:50000
3.    72057594004373503   host 192.168.1.23:54400   → relay 203.0.113.50:49154
4.    72057594004373502  relay 203.0.113.50:49152   → host  192.168.0.31:54400
5.    72057593131958270  relay 203.0.113.50:49152   → srflx 198.51.100.201:50000
6.    72057589776515070  relay 203.0.113.50:49152   → relay 203.0.113.50:49154

兩端排序一致；任何含 relay 的 pair 都排在不含 relay 的 pair 之後
```

foundation 在這裡用 CRC32 示意（瀏覽器的算法不同，規則相同）。四行公式顯示，priority 換成十六進位後最高 byte 就是 type preference（0x7e、0x6e、0x64、0x00），這是在 SDP 中一眼看出類型的技巧。

九個 pair 剪枝後剩六個，消失的都是「學生 srflx 對 X」。第 1 名 host 對 host 在不同的家裡一定失敗，但 ICE 事先不知道，照樣會測；第 2 名「學生 host 對老師 srflx」成功時，學生從回應學到的本地位址就是自己的 srflx；第 3 名以後全部含 relay。assert 也確認老師端算出的值完全相同。

### 程式三：ICE 在不同 NAT 組合下選出的路

第三段把第 7 章的 NAT、TURN 的 permission、check list、triggered check、prflx 與 regular nomination 放在一起，用模擬時鐘（每 tick 為 Ta＝50 ms）跑完連線檢查。這是簡化模型：檢查不會隨機遺失，回應一定沿原路回去，重送間隔 500 ms、最多 4 次。

```python
import ipaddress

TURN_IP, STUN_ADDR = "203.0.113.50", ("203.0.113.50", 3478)
PRIVATE = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")]
TYPE_PREF = {"host": 126, "prflx": 110, "srflx": 100, "relay": 0}
RTO_TICKS, MAX_TX = 10, 4      # 每 tick = Ta 50 ms；10 tick（500 ms）沒回應就重送，最多送 4 次


def is_lan(ip):                 # 不用 is_private：文件範例位址 203.0.113.x 也會被它當成 private（第 7 章）
    return any(ipaddress.ip_address(ip) in n for n in PRIVATE)


def prio(kind, local_pref=65535, component=1):
    return (TYPE_PREF[kind] << 24) + (local_pref << 8) + (256 - component)


def pair_prio(g, d):            # g＝controlling 端 candidate 的 priority，d＝controlled 端
    return (1 << 32) * min(g, d) + 2 * max(g, d) + (1 if g > d else 0)


class Nat:
    """沿用第 7 章：mapping 決定對外 port，filtering 決定誰能打進來。"""
    def __init__(self, ip, kind):
        self.ip = ip
        self.mapping, self.filtering = {"restricted": ("EI", "AD"), "port restricted": ("EI", "APD"),
                                        "symmetric": ("APD", "APD")}[kind]
        self.maps, self.sent_to, self.next_port = {}, set(), 50000

    def send(self, dst):
        key = () if self.mapping == "EI" else (dst,)
        if key not in self.maps:
            self.maps[key], self.next_port = self.next_port, self.next_port + 7
        self.sent_to.add((self.maps[key], dst))
        return (self.ip, self.maps[key])

    def accept(self, src, port):
        if port not in self.maps.values():
            return False
        if self.filtering == "AD":
            return any(p == port and d[0] == src[0] for p, d in self.sent_to)
        return (port, src) in self.sent_to


class Agent:
    def __init__(self, name, ip, nat, block_udp=False, turn_tls=False):
        self.name, self.base, self.nat, self.block_udp, self.turn_tls = name, (ip, 54400), nat, block_udp, turn_tls
        self.cands = [("host", self.base, prio("host"))]

    def send_from_base(self, dst):  # 從 host base 送出 UDP，回傳外面看到的來源；送不出去回傳 None
        if is_lan(dst[0]):
            return self.base
        return None if self.block_udp else self.nat.send(dst)

    def gather(self, relay_port):
        srflx = self.send_from_base(STUN_ADDR)
        if srflx:
            self.cands.append(("srflx", srflx, prio("srflx")))
        if not self.block_udp or self.turn_tls:       # UDP 被擋時，只有 TURN over TLS 443 拿得到 relay
            lp = 65534 if self.block_udp else 65535   # 經 TLS 的 relay，local preference 比 UDP 低
            self.cands.append(("relay", (TURN_IP, relay_port), prio("relay", lp)))


def deliver(sender, local, dst, agents):
    """模擬一個 STUN 檢查從 local 送往 dst：回傳 (收件者, 收件的本地 candidate, 收件者看到的來源) 或 None。"""
    if local[0] == "relay":
        if dst[0] not in sender.perms:              # TURN 只替有 permission 的 IP 轉送
            return None
        src = local[1]
    else:
        src = sender.send_from_base(dst)
        if src is None:
            return None
    for ag in agents:
        for c in ag.cands:
            if c[0] == "relay" and c[1] == dst:     # 送到某人的 relay：TURN 查 permission 後轉給那個人
                return (ag, c, src) if src[0] in ag.perms else None
        if ag.base == dst and is_lan(dst[0]):       # 私有位址：只有同一台 NAT 後面的人送得到
            return (ag, ag.cands[0], src) if ag.nat is sender.nat else None
        if ag.nat.ip == dst[0]:
            return (ag, ag.cands[0], src) if ag.nat.accept(src, dst[1]) else None
    return None


def add_pair(ag, local, remote):
    g, d = (local[2], remote[2]) if ag.controlling else (remote[2], local[2])
    ag.pairs.setdefault((local, remote), {"prio": pair_prio(g, d), "tx": 0, "next": 0, "state": "Waiting"})


def run_ice(a, b, patience_ms=None):
    agents, first_valid = [a, b], None
    a.controlling, b.controlling = True, False      # 送 offer 的學生端是 controlling
    for i, ag in enumerate(agents):
        ag.gather(49152 + 2 * i)
    for ag, peer in ((a, b), (b, a)):
        ag.perms = {c[1][0] for c in peer.cands}    # 對每個遠端 candidate 的 IP 建立 TURN permission
        ag.pairs, ag.triggered, ag.valid = {}, [], []
        for lc in ag.cands:
            if lc[0] == "srflx":                    # 本地 srflx 從 base 送出，與 host 的 pair 重複：剪掉
                continue
            for rc in peer.cands:
                add_pair(ag, lc, rc)
    for tick in range(300):
        for ag, peer in ((a, b), (b, a)):
            ready = [k for k, p in ag.pairs.items() if p["state"] in ("Waiting", "InProgress") and p["next"] <= tick]
            key = ag.triggered.pop(0) if ag.triggered else max(ready, key=lambda k: ag.pairs[k]["prio"], default=None)
            if key is None:
                continue
            p = ag.pairs[key]
            p["tx"], p["next"], p["state"] = p["tx"] + 1, tick + RTO_TICKS, "InProgress"
            got = deliver(ag, key[0], key[1][1], agents)
            if not got:
                p["state"] = "Failed" if p["tx"] >= MAX_TX else "InProgress"
                continue
            _, r_local, src = got
            remote = next((c for c in peer.pairs if c[0] == r_local and c[1][1] == src), None)
            if remote is None:                      # 來源不在已知的 candidate 裡：學到 peer-reflexive
                add_pair(peer, r_local, ("prflx", src, prio("prflx")))
                remote = (r_local, ("prflx", src, prio("prflx")))
            if peer.pairs[remote]["state"] != "Succeeded" and remote not in peer.triggered:
                peer.triggered.append(remote)       # triggered check：收到檢查就立刻反方向回測
            p["state"] = "Succeeded"
            mapped = src                            # 回應裡的 XOR-MAPPED-ADDRESS
            local = next((c for c in ag.cands if c[1] == mapped), ("prflx", mapped, prio("prflx")))
            g, d = (local[2], key[1][2]) if ag.controlling else (key[1][2], local[2])
            ag.valid.append((pair_prio(g, d), local, key[1]))   # valid pair 用「回應揭露的」本地 candidate
        if a.valid:                                 # controlling 端決定何時提名（regular nomination）
            best, first_valid = max(a.valid), tick if first_valid is None else first_valid
            waiting_better = any(p["state"] in ("Waiting", "InProgress") and p["prio"] > best[0] for p in a.pairs.values())
            if not waiting_better or (patience_ms is not None and (tick - first_valid) * 50 >= patience_ms):
                return best, (tick + 2) * 50, sum(p["tx"] for p in a.pairs.values()) + sum(p["tx"] for p in b.pairs.values())
    return None, None, None


teacher = lambda kind: Agent("老師", "192.168.0.31", Nat("198.51.100.201", kind))
home = Nat("198.51.100.23", "port restricted")
scenarios = [
    ("① 同一個家裡", Agent("學生", "192.168.1.23", home), Agent("老師", "192.168.1.40", home)),
    ("② 家用 PR ↔ 家用 R", Agent("學生", "192.168.1.23", Nat("198.51.100.23", "port restricted")), teacher("restricted")),
    ("③ CGNAT SYM ↔ 家用 R", Agent("學生", "100.72.18.9", Nat("198.51.100.200", "symmetric")), teacher("restricted")),
    ("④ CGNAT SYM ↔ 家用 PR", Agent("學生", "100.72.18.9", Nat("198.51.100.200", "symmetric")), teacher("port restricted")),
    ("⑤ 學校擋 UDP，只有 UDP TURN", Agent("學生", "172.16.8.23", Nat("198.51.100.77", "symmetric"), True), teacher("restricted")),
    ("⑥ 學校擋 UDP，加開 TURN TLS", Agent("學生", "172.16.8.23", Nat("198.51.100.77", "symmetric"), True, True), teacher("restricted")),
]
results = {}
for title, a, b in scenarios:
    best, ms, sent = run_ice(a, b)
    if best is None:
        print(f"{title:<22} ICE failed（{len(a.cands)} 個本地 candidate，全部檢查失敗）")
        results[title[0]] = None
        continue
    _, lc, rc = best
    results[title[0]] = (lc[0], rc[0])
    print(f"{title:<22} {lc[0]:>5} {lc[1][0]}:{lc[1][1]:<5} ↔ {rc[0]:<5} {rc[1][0]}:{rc[1][1]:<5} {ms:>5} ms，共 {sent} 個檢查")
assert results == {"①": ("host", "host"), "②": ("srflx", "srflx"), "③": ("prflx", "srflx"),
                   "④": ("prflx", "relay"), "⑤": None, "⑥": ("relay", "srflx")}
best, ms, _ = run_ice(Agent("學生", "192.168.1.23", Nat("198.51.100.23", "port restricted")), teacher("restricted"), patience_ms=200)
print(f"② 改成「第一個成功後最多再等 200 ms」：{best[1][0]} ↔ {best[2][0]}，{ms} ms")
assert ms < 1000
```

輸出：

```text
① 同一個家裡                 host 192.168.1.23:54400 ↔ host  192.168.1.40:54400   100 ms，共 2 個檢查
② 家用 PR ↔ 家用 R         srflx 198.51.100.23:50000 ↔ srflx 198.51.100.201:50000  1600 ms，共 23 個檢查
③ CGNAT SYM ↔ 家用 R     prflx 198.51.100.200:50007 ↔ srflx 198.51.100.201:50000  1600 ms，共 29 個檢查
④ CGNAT SYM ↔ 家用 PR    prflx 198.51.100.200:50014 ↔ relay 203.0.113.50:49154  1750 ms，共 34 個檢查
⑤ 學校擋 UDP，只有 UDP TURN  ICE failed（1 個本地 candidate，全部檢查失敗）
⑥ 學校擋 UDP，加開 TURN TLS  relay 203.0.113.50:49152 ↔ srflx 198.51.100.201:50000  1850 ms，共 28 個檢查
② 改成「第一個成功後最多再等 200 ms」：srflx ↔ srflx，400 ms
```

① 同一個家裡，host 對 host 第一個檢查就成功，100 ms 完成提名（真實世界還取決於 mDNS 能否解析）。② 家用 NAT 互打成功，選中 srflx 對 srflx，卻花了 1600 ms：優先序最高的 host 對 host 根本到不了，ICE 要等它重送 4 次逾時，才能確定沒有更好的。最後一行改成「第一個成功後最多再等 200 ms」，同樣結果只要 400 ms，這就是 36.8 節的提名取捨。

③ CGNAT（symmetric）對 restricted：選中學生的 **prflx** :50007 對老師的 srflx，正是 36.8 節時序圖的結果。④ 把老師換成 port restricted，打洞不可能，選中學生 prflx 對**老師的 relay**：只要一端用 relay 就夠，TURN 的 permission 只比對 IP，symmetric NAT 換 port 也不影響。這就是 Joe 觀察到「CGNAT 學生常落在 TURN」的原因。

⑤ 學校擋 UDP、TURN 只開 UDP：學生只有一個私有位址的 host candidate，ICE failed，這就是故事裡的 4.1%。⑥ 加開 TURN over TLS 443，學生拿到 relay candidate，選中學生 relay 對老師 srflx。修正不必動學校的網路，只要 TURN 多開一個 port。

## 36.12 在工作上怎麼用

**前端工程師：把 RTCPeerConnection 設定對。** 修正後的前端核心程式如下（瀏覽器的 JavaScript）：iceServers 由後端產生短效帳密、同時提供 UDP 與 TLS 443、trickle ICE、remote description 設定前先暫存 candidate。

```javascript
// 每次進教室前向後端要一組新的 iceServers（短效 TURN 帳密，1 小時）
const { iceServers } = await api.get(`/v1/lessons/${lessonId}/ice-servers`);
const pc = new RTCPeerConnection({ iceServers, bundlePolicy: "max-bundle" });
// iceServers 範例：
// [{ urls: ["turn:turn.shengsheng.example:3478?transport=udp",
//           "turns:turn.shengsheng.example:443?transport=tcp"],
//    username: "1790003600:student-0457", credential: "..." }]

pc.onicecandidate = ({ candidate }) => signal.send({ type: "candidate", candidate }); // null＝end-of-candidates
pc.onicecandidateerror = (e) => log("ice-error", e.url, e.errorCode, e.errorText);  // 701＝連不到該伺服器

const pending = [];
signal.on("candidate", async ({ candidate }) => {
  if (!pc.remoteDescription) { pending.push(candidate); return; }  // 太早到的 candidate 先暫存
  await pc.addIceCandidate(candidate);
});
signal.on("answer", async ({ sdp }) => {
  await pc.setRemoteDescription({ type: "answer", sdp });
  for (const c of pending.splice(0)) await pc.addIceCandidate(c);
});
pc.oniceconnectionstatechange = () => {
  if (pc.iceConnectionState === "failed") pc.restartIce();         // 換網路後重新找路
};
```

`onicecandidateerror` 的 `errorCode` 701 專門表示「連不到伺服器」；把它送回後端 log，那台不回應的舊 STUN 伺服器早就會被發現。

**後端工程師：signaling 與 iceServers API 是安全邊界。** signaling 用 JWT 驗證身分並確認屬於這堂課，訊息只轉給同一堂課的另一方；`/ice-servers` 每次產生新的短效帳密，TTL 與課程時間相當。log 不記完整 SDP（`ice-pwd` 外洩能讓人偽造 ICE 檢查）；每則訊息帶課程編號與序號，方便對齊雙方的時間線。

**影音工程師：從 getStats 讀出選中的路。** Joe 在通話建立後 5 秒與結束時各收集一次：

```javascript
const stats = await pc.getStats();
let transport, pair;
stats.forEach((r) => { if (r.type === "transport") transport = r; });
const sel = stats.get(transport.selectedCandidatePairId);
const local = stats.get(sel.localCandidateId), remote = stats.get(sel.remoteCandidateId);
report({
  path: `${local.candidateType}/${remote.candidateType}`,   // 例如 "srflx/srflx"、"relay/srflx"
  relayProtocol: local.relayProtocol,                       // "udp"、"tcp" 或 "tls"（只在 relay 時有）
  rttMs: sel.currentRoundTripTime * 1000,                   // 由 consent／STUN 檢查量到的 RTT
  dtls: transport.dtlsState, tls: transport.tlsVersion, srtp: transport.srtpCipher,
});
```

儀表板因此能畫出各路徑類型與「relay 中 tls」的比例：relay 比例突然上升，先看是否某個 ISP 或學校的網路變了；tls 比例上升，代表更多網路擋 UDP，品質會受 head-of-line blocking 影響（第 39 章）。

**SRE：TURN 是要監控的生產服務。**

```bash
# 從外面確認 TURN 的三種入口都活著（示意：用 nc 測 port，真正的功能測試要用 TURN client 工具）
nc -vzu turn.shengsheng.example 3478          # UDP（nc 對 UDP 的結果只能參考）
nc -vz  turn.shengsheng.example 3478          # TCP
openssl s_client -connect turn.shengsheng.example:443 -servername turn.shengsheng.example </dev/null \
  | openssl x509 -noout -enddate              # TLS 憑證到期日（第 19 章）
# 在 TURN 主機上觀察 STUN／TURN 流量
sudo tcpdump -ni eth0 -c 20 'udp port 3478 or tcp port 443'
sudo tcpdump -ni eth0 -c 20 'udp portrange 49152-65535'   # relay port：有 allocation 卻沒有流量要查 security group
```

指標包括 allocation 數、relay 頻寬、401 以外的錯誤率（441 上升通常是金鑰不同步或時鐘偏差）、TLS 憑證剩餘天數、UDP buffer 丟包。TURN 若在 NAT 後面，`external-ip` 設錯會讓 relay candidate 帶著私有位址，永遠收不到封包。

**資安工程師：審查清單。** signaling 走 WSS 並驗證授權；TURN 帳密短效、金鑰放 secrets manager；peer 拒絕清單涵蓋私有、loopback、link-local 與 metadata 位址；P2P 時雙方會在 candidate 中看到彼此的家用 IP，有隱私需求時用 `iceTransportPolicy: "relay"`；前端不得修改 SDP 的 fingerprint 與 setup 行。

## 36.13 常見錯誤與除錯

不同的根因都長成同一個症狀「連不上」。下表依卡住的階段整理，每一列都能用 webrtc-internals、getStats 或 tcpdump 確認。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 每次連線都要好幾秒，最後仍成功 | 等 gathering 完成才送 SDP（非 trickle），設定中有不回應的 STUN／TURN 伺服器 | webrtc-internals 的時間線：offer 在 gathering complete 之後才送；`icecandidateerror` 出現 701 | 改用 trickle ICE；刪除失效的伺服器；監控 701 |
| 只有特定學校或公司 ICE failed | 網路擋掉 UDP，TURN 只提供 UDP | 失敗連線的本地 candidate 只有 host（或 TCP host）；用 `iceTransportPolicy: "relay"` 在該網路測試 | TURN 加開 `turns:…:443?transport=tcp`，並確認憑證有效 |
| 有 relay candidate，卻還是連不上或只有單向 | TURN 的 relay port 範圍沒在 security group 開放；`external-ip` 設錯，relay 位址是私有 IP | relay candidate 的位址是 10.x；在 TURN 主機上 tcpdump relay port 只有出沒有進 | 開放 relay port 範圍；設定正確的公網位址 |
| TURN 一直回 401 或 441 | 帳密過期、金鑰不同步、時鐘偏差 | TURN log；比對 username 的到期時間與伺服器時間 | 每次通話重新取得帳密；同步金鑰；校時 |
| console 出現 `addIceCandidate` 的 InvalidStateError，偶爾連不上 | candidate 比 answer 先到，在 `setRemoteDescription` 之前就加入 | 前端 log 中錯誤時間早於 answer 到達的時間 | 暫存 candidate，設定 remote description 後再加入 |
| ICE 已 connected，`connectionState` 卻變成 failed | DTLS 交握失敗：SDP 的 fingerprint 被前端改寫、signaling 把不同 session 的 SDP 混在一起、雙方都宣告 `setup:active` | webrtc-internals 的 `dtlsState` 為 failed；比對雙方 SDP 的 fingerprint 與 setup 行 | 不要修改 fingerprint／setup；每次協商用同一個 RTCPeerConnection 產生的 SDP |
| 學生從 Wi-Fi 換到 4G 後畫面凍結，不會自己恢復 | 舊 candidate 全部失效，沒有做 ICE restart | `iceConnectionState` 先 disconnected 再 failed，之後沒有新的協商 | 在 failed（或 disconnected 超過數秒）時呼叫 `restartIce()` 重新協商 |
| relay 比例異常高、TURN 費用暴增 | 除錯用的 `iceTransportPolicy: "relay"` 留在正式版；TURN 帳密外洩被濫用 | 統計 relay 比例的變化時間點與版本發布；TURN 上依 username 統計流量 | 移除設定；改用短效帳密；依使用者限流 |

通則是先問卡在哪一段：沒有 srflx 或 relay，是伺服器或網路；有 candidate 但 pair 全 failed，是 NAT 或防火牆；ICE connected 但 DTLS failed，是 SDP 或 signaling；全部成功卻沒畫面，往第 34、35、39 章找。

## 36.14 動手練習

1. **延伸程式一：回應錯誤**。讓 STUN server 收到含不認識的 comprehension-required 屬性（例如 type 0x7F00）的請求時，回 error response（0x0111），帶 ERROR-CODE 420 與列出該 type 的 UNKNOWN-ATTRIBUTES（0x000A）；不認識的 0x8000 以上屬性則照常回應。
   答案要點：ERROR-CODE 的 value 是 2 bytes 保留、1 byte class（4）、1 byte number（20），再接 UTF-8 原因字串；用 assert 驗證 0x8000 以上的未知屬性不觸發錯誤。

2. **延伸程式三：加入 full cone 與 ICE-lite**。加入 full cone（EIM＋EIF），並把老師換成公網上的 ICE-lite SFU（203.0.113.60，只有 host candidate、不主動檢查）。
   答案要點：ICE-lite 時學生一定是 controlling，選中的是學生 srflx 或 prflx 對 SFU 的 host；學生就算在 symmetric NAT 後面也能成功，因為 SFU 沒有 NAT 擋。

3. **用 webrtc-internals 觀察 ICE**（真實工具）。在 Chrome 的兩個分頁執行任一 WebRTC 範例，打開 `chrome://webrtc-internals` 找出選中的 pair；再改成 `iceTransportPolicy: "relay"` 並提供 TURN，比較 pair 與 RTT。
   答案要點：同一台電腦通常是 host 對 host（priority 最高 byte 0x7e）；強迫 relay 後兩端都是 relay，RTT 變成「到 TURN 來回兩次」的量級，`relayProtocol` 顯示實際的傳輸方式。

4. **用 Wireshark 看連線建立**（真實工具）。過濾 `stun || dtls`，找出一個 Binding request 的 USERNAME 與 PRIORITY、帶 USE-CANDIDATE 的檢查、ClientHello 中的 use_srtp，以及之後的 SRTP。
   答案要點：USERNAME 冒號前是**對方**的 ufrag；USE-CANDIDATE 只出現在 controlling 端的檢查；ClientHello 由 `setup:active` 的一方送出；SRTP 要用「Decode As」設為 RTP 才看得到 header，payload 是亂碼。

5. **手算優先序**。priority 1677730047 是什麼類型？local preference 與 component 是多少？controlling 端用它、controlled 端用 priority 16777215 的 relay 時，pair priority 是多少？
   答案要點：十六進位 0x640020ff，type preference 100（srflx），local preference 32，component 1。G＞D，所以 pair priority＝2³²×16777215＋2×1677730047＋1＝72057593098420735。

## 本章重點整理

- WebRTC 的連線建立由多個協定合作：signaling 交換 SDP 與 candidate，ICE 找路，STUN 是探測訊息，TURN 是中繼，DTLS 交換金鑰並驗證身分，SRTP 加密媒體，SCTP 承載 data channel。
- signaling 不在 WebRTC 規格內，但它承載 fingerprint 與 ice-pwd，是安全模型的基石：必須走 TLS 並驗證授權，DTLS-SRTP 的安全性等於 signaling 的安全性。
- candidate 分為 host、srflx（STUN 看到的 NAT 外位址）、prflx（檢查時才學到的位址）與 relay（TURN 的中繼位址）；本地 srflx 從 base 送出，組 check list 時會被剪枝。
- candidate priority＝2²⁴×type preference＋2⁸×local preference＋(256−component)，建議值 host 126、prflx 110、srflx 100、relay 0；換成十六進位看最高 byte 就知道類型。
- pair priority＝2³²×MIN(G,D)＋2×MAX(G,D)＋(G>D?1:0)，G、D 依 controlling／controlled 決定，所以兩端排序一致，且任何含 relay 的 pair 都排在最後。
- STUN header 固定 20 bytes：前兩 bit 為 0、class 交錯在 method 中的 message type、不含 header 的長度、magic cookie 0x2112A442 與 96 bit 隨機 transaction ID；屬性是補齊到 4 bytes 的 TLV。
- XOR-MAPPED-ADDRESS 以 magic cookie（IPv6 再加 transaction ID）XOR 位址以避開 ALG；MESSAGE-INTEGRITY 是 HMAC-SHA1，防偽造；FINGERPRINT 是 CRC-32 XOR 0x5354554E，只用於多工辨識。
- 連線檢查是帶 USERNAME、PRIORITY、角色屬性與 MESSAGE-INTEGRITY 的 Binding request；triggered check 讓打洞即時完成，controlling 端以 USE-CANDIDATE 提名，選定後每 4～6 秒做 consent check，30 秒無回應即停止。
- TURN 的 allocation 預設 600 秒、permission 300 秒且只比對 IP、channel 600 秒；ChannelData 只多 4 bytes；要同時提供 UDP 與 TLS 443，並用 HMAC 短效帳密與 peer 拒絕清單防止濫用與 SSRF。
- DTLS-SRTP 用自簽憑證，信任來自 fingerprint 比對；`a=setup` 決定 DTLS 角色，與 ICE 角色無關；SRTP 只加密 payload，透過 SFU 時是逐段加密而非端到端。
- data channel 是 SCTP over DTLS，以 DCEP 開啟，可選可靠有序、不保證順序、限制重送次數或存活時間；大量資料要切塊並以 bufferedAmount 做 backpressure。

## 延伸問答

> [!question]- Q1. WebRTC 的媒體一律加密，為什麼 Rita 還說「signaling 被攻破，媒體就不安全」？加密不是在兩個瀏覽器之間做的嗎？
> 加密確實只在兩個瀏覽器之間做，SRTP 金鑰也只有兩端知道，但「兩端是誰」是由 signaling 決定的。DTLS 用的是自簽憑證，不經過 CA，瀏覽器判斷「對方是不是對的人」的唯一依據，是 DTLS 交握中對方憑證的雜湊等於 SDP 裡的 `a=fingerprint`。而 SDP 是經由 signaling 送來的。
>
> 如果攻擊者能竄改 signaling（例如入侵 signaling 伺服器，或伺服器把 SDP 轉給了錯誤的房間），就能把雙方 SDP 裡的 fingerprint 換成自己的憑證，再分別和學生、老師各建一條 DTLS。兩條交握都會「成功」，雙方看到的都是綠燈，攻擊者在中間解密、記錄、再加密轉送。所以 WebRTC 的安全性等於 signaling 的安全性：signaling 必須走 TLS、驗證每個連線者的身分與房間授權，伺服器本身也要被當成高價值目標保護。

> [!question]- Q2. 手算：SDP 中有一行 `a=candidate:3 1 udp 1694498815 198.51.100.23 50000 typ srflx`，對方的 relay candidate priority 是 16777215。若你是 controlled 端，你的 srflx 和對方 relay 組成的 pair priority 是多少？
> 先拆 priority：1694498815 換成十六進位是 0x64ffffff，type preference 0x64＝100，確實是 srflx；local preference 0xffff＝65535，最低 byte 0xff＝255，component 1。對方的 relay 是 0x00ffffff，type preference 0。
>
> 你是 controlled 端，所以 D＝1694498815（你的），G＝16777215（對方 controlling 的）。pair priority＝2³²×MIN(G,D)＋2×MAX(G,D)＋(G>D?1:0)＝4294967296×16777215＋2×1694498815＋0＝72057589742960640＋3388997630＝72057593131958270。對方用同一個公式、同樣的 G 與 D，會算出相同的值，這正是公式用角色而不用本地／遠端的原因。若換成你是 controlling，G 與 D 對調，最後一項變成 1，結果是 72057593131958271，只差 1。

> [!question]- Q3. 你在 webrtc-internals 看到選中的 pair 是 local relay（relayProtocol 為 tls）對 remote srflx，currentRoundTripTime 約 0.18 秒，學生抱怨老師的聲音一卡一卡。可能的原因與改善方向是什麼？
> relayProtocol 為 tls 代表學生到 TURN 這一段走的是 TCP 上的 TLS，通常是因為學生的網路擋掉了 UDP，UDP 版本的 relay 也失敗了。在 TCP 上傳即時影音，任何一個封包遺失都要等 TCP 重傳，後面已經到達的封包只能在 buffer 裡等待（head-of-line blocking，第 12 章），表現出來就是聲音一卡一卡、延遲忽高忽低。180 ms 的 RTT 則說明路徑繞得遠，可能是 TURN 離學生或老師很遠。
>
> 改善方向依序是：確認學生的網路是否真的擋 UDP（如果只擋 3478，可以讓 TURN 在 UDP 443 也提供服務）；讓 TURN 部署在離使用者近的區域，縮短 RTT（第 37 章）；在品質上，對 TCP 路徑降低 bitrate、加大 jitter buffer。對這所學校，長期解法是請網管放行到 TURN 的 UDP。這個問題不會出現在 ICE failed 的統計裡，因為連線是成功的，所以 Joe 的儀表板要另外追蹤 relayProtocol 的比例。

> [!question]- Q4. 面試題：STUN 已經有 MESSAGE-INTEGRITY 了，為什麼還需要 FINGERPRINT？反過來，能不能只用 FINGERPRINT 保護訊息？
> 兩者解決不同的問題。FINGERPRINT 是 CRC-32 再 XOR 一個常數，它的目的是**分辨**：WebRTC 在同一個 UDP port 上同時收 STUN、DTLS、SRTP，光靠「前兩個 bit 是 0」與 magic cookie，仍有極小的機率把別的協定誤認成 STUN；多一個 CRC 檢查，誤判機率就降到可以忽略。而且分辨必須在知道密碼之前就能做，所以它不能依賴任何金鑰。
>
> 正因為 CRC 不用金鑰，任何人竄改內容後都能重新算出正確的 CRC，所以它完全不能防竄改，也不能證明來源。防偽造要靠 MESSAGE-INTEGRITY：它是用 ice-pwd（或 TURN 的長期金鑰）算的 HMAC，沒有密碼就算不出來。36.6 節的程式示範了這一點：竄改後重算 CRC，FINGERPRINT 通過，MESSAGE-INTEGRITY 失敗。

> [!question]- Q5. TURN 的 permission 只比對對方的 IP、不比對 port。這是不是安全漏洞？為什麼這樣設計？
> 這是刻意的取捨。ICE 會透過 TURN 學到 peer-reflexive 位址：對方若在 symmetric NAT 後面，送到 relay 的封包可能來自一個 client 事先不知道的 port。如果 permission 要比對 IP 加 port，這些封包會被 TURN 丟掉，prflx 就無法運作，很多原本能透過「一端 relay」成功的組合（本章程式三的 ④）會失敗。
>
> 它的安全影響有限：要通過 permission，封包的來源 IP 必須是 client 主動允許過的，也就是通話對方的公網 IP，陌生人無法利用。剩下的風險是「同一個 IP 後面的其他人」，例如同一個 CGNAT 出口後的其他用戶可以往這個 relay port 送封包；但他們得先知道 relay 位址與 port，而且 WebRTC 的媒體還有 ICE 檢查與 DTLS-SRTP 保護，偽造的封包會在驗證時被丟棄。所以這個設計是用一點點過濾的精確度，換取 NAT 穿越的成功率。

> [!question]- Q6. 兩位老師在聲聲 Live 的同一間辦公室（同一個 NAT 後面）互相測試視訊，選中的 pair 卻是 relay。為什麼不是 host 對 host？
> 理論上同一個 LAN 內 host 對 host 應該成功，但有兩個常見的阻礙。第一，瀏覽器以 mDNS 名稱遮蔽 host 位址，對方要用 mDNS 解析 `xxxx.local` 才知道真正的 IP；很多企業網路的交換器或 Wi-Fi 會隔離用戶端、擋掉 multicast，mDNS 解析失敗，host pair 就測不起來。第二，雙方的 srflx 是同一個公網 IP，srflx 對 srflx 要求 NAT 支援 **hairpinning**（內部主機送往 NAT 自己的公網位址時，NAT 要把封包轉回內部），很多 NAT 不支援。
>
> 兩條路都失敗，就只剩 relay。確認方法是看 webrtc-internals：host candidate 是否為 `.local` 名稱、host pair 的狀態是否 failed、雙方 srflx 的 IP 是否相同。解法看情境：允許辦公室網路的 mDNS 與用戶端互通，或讓 NAT 支援 hairpinning；如果這只是內部測試，接受走 relay 也可以，但要知道這會讓「內部測試很順」和「真實使用者的路徑」不同。

> [!question]- Q7. 你看到 `iceConnectionState` 已經是 connected，但 `connectionState` 隨後變成 failed，畫面一直是黑的。可能卡在哪裡？怎麼查？
> `iceConnectionState` 只代表 ICE 層有一個可用的 pair；`connectionState` 綜合了 ICE 與 DTLS 的狀態。ICE connected 而整體 failed，幾乎可以確定是 DTLS 交握失敗。常見原因有三：一是有人在前端「SDP munging」時改壞了 `a=fingerprint`，或 signaling 把舊 session 的 SDP 送了過來，導致憑證雜湊對不上；二是 `a=setup` 角色衝突，例如雙方都是 active，兩邊都送 ClientHello，或都是 passive，誰也不送；三是 DTLS 封包在路徑上被丟（例如中間設備擋掉了大的 UDP 封包，Certificate 的切片一直遺失）。
>
> 查法是打開 webrtc-internals 的 transport 統計看 `dtlsState`，比對雙方 SDP 的 fingerprint 是否等於對方實際憑證的雜湊、setup 是否一個 active 一個 actpass／passive；如果懷疑是丟包，用 Wireshark 過濾 `dtls` 看 ClientHello 之後的 flight 是否一直重送。修正方向是：不要修改 fingerprint 與 setup 行；每次協商都使用同一個 RTCPeerConnection 產生的最新 SDP；檢查路徑上的 MTU 問題（第 8 章）。

> [!question]- Q8. 設計取捨：有人提議聲聲 Live 所有一對一課都用 `iceTransportPolicy: "relay"`，理由是「隱私更好、路徑可預測、除錯簡單」。你怎麼評估？
> 這個提議的優點是真的：relay-only 時，雙方只看到 TURN 的位址，不會知道彼此的家用 IP，對保護學生與老師的隱私有幫助；所有流量都經過自家的 TURN，路徑可預測、可以統一量測品質，也不會遇到各種 NAT 組合的奇怪行為。對某些客戶（例如要求不暴露員工 IP 的企業）甚至是必要條件。
>
> 代價也很明確。第一是成本：本章的粗估中，一堂課走 TURN 要送出約 1.16 GB，把 15% 的 relay 比例提高到 100%，TURN 的頻寬要增加六倍以上。第二是延遲：原本可以直連的兩個人，現在要繞到 TURN 再回來，若 TURN 不在附近，RTT 可能加倍。第三是可用性：TURN 成為所有一對一課的單點，必須多區域部署與容量規劃（第 37 章）。比較合理的折衷是預設 `all`，只對有隱私需求的課程或客戶啟用 relay-only，並持續監控 relay 比例與 TURN 容量。

## 延伸閱讀

- RFC 8445〈Interactive Connectivity Establishment (ICE): A Protocol for Network Address Translator (NAT) Traversal〉：candidate、優先序公式、連線檢查與提名
- RFC 8838〈Trickle ICE: Incremental Provisioning of Candidates for the Interactive Connectivity Establishment (ICE) Protocol〉與 RFC 7675〈Session Traversal Utilities for NAT (STUN) Usage for Consent Freshness〉
- RFC 8489〈Session Traversal Utilities for NAT (STUN)〉與 RFC 5769〈Test Vectors for Session Traversal Utilities for NAT (STUN)〉：訊息格式與 36.6 節程式用的測試向量
- RFC 8656〈Traversal Using Relays around NAT (TURN): Relay Extensions to Session Traversal Utilities for NAT (STUN)〉：allocation、permission、channel 與生命週期
- RFC 5764〈Datagram Transport Layer Security (DTLS) Extension to Establish Keys for the Secure Real-time Transport Protocol (SRTP)〉與 RFC 3711〈The Secure Real-time Transport Protocol (SRTP)〉
- RFC 8831〈WebRTC Data Channels〉與 RFC 8832〈WebRTC Data Channel Establishment Protocol〉
- RFC 8827〈WebRTC Security Architecture〉：signaling、fingerprint 與信任模型
- W3C〈WebRTC: Real-Time Communication in Browsers〉：RTCPeerConnection、getStats 與 ICE 相關 API
