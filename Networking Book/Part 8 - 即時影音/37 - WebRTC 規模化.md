---
chapter: 37
title: WebRTC 規模化：Mesh、SFU 與 MCU
part: 8
---

# 第 37 章　WebRTC 規模化：Mesh、SFU 與 MCU

> [!abstract] 本章地圖
> **核心問題**：兩個人視訊靠 P2P 就夠了；當教室變成六個人、上千間同時開課、每個人的網路又好壞不一時，媒體該怎麼走、伺服器要多大、網路變差時誰來調整？
>
> **你會學到**：
> - 用公式算出 mesh、SFU、MCU 在 N 人時每人的上下行頻寬、編解碼數量與伺服器負載，並說清楚各自適合的場景
> - 解釋 simulcast 與 SVC 的差別，以及 SFU 怎麼依每位接收者的頻寬與版面選層、為什麼切層要等 keyframe
> - 看懂 WebRTC 的頻寬估計：GCC 的延遲梯度概念、REMB 與 TWCC 的封包格式與分工
> - 依 RTT 與丟包型態選擇 NACK 重送、PLI／FIR、ULPFEC／FlexFEC 與 Opus in-band FEC
> - 估算 TURN 的頻寬成本、規劃 TURN 與 SFU 的部署、水平擴展與 cascading
> - 用 getStats 的關鍵指標判斷「卡」是頻寬、CPU、丟包還是 keyframe 造成的
>
> **前置知識**：第 7 章（NAT 與打洞）、第 12 章（擁塞控制與 bufferbloat）、第 34 章（codec、GOP、RTP／RTCP）、第 35 章（SDP）、第 36 章（ICE、STUN、TURN、DTLS-SRTP）

## 37.1 故事：六人小班課的第一個星期四

聲聲 Live 的一對一視訊課已經上線一年。它的做法很直接：老師和學生的瀏覽器各開一個 `RTCPeerConnection`，透過 `rt.shengsheng.example` 的 WebSocket 交換 SDP 與 ICE candidate（第 35、36 章），能直連就 P2P，不能就經由 TURN（`turn.shengsheng.example`，203.0.113.50）中繼。產品團隊想推出「六人會話小班」：一位老師帶五位學生，價格是一對一的一半。為了趕在月底上線，前端把一對一的程式改成「每個人對其他五個人各開一條 PeerConnection」，這種做法叫 **mesh**（網狀），測試時三個工程師在辦公室裡連得很順。

第一個星期四晚上八點，日文老師美咲開了第一堂小班課。十分鐘內客服收到四則回報：「老師的畫面一直卡」「我看得到同學，但同學說看不到我」「老師說筆電風扇狂轉」「影像變成馬賽克」。影音工程師 Joe 請美咲打開 `chrome://webrtc-internals`（Chrome 內建的 WebRTC 偵錯頁），看到五條送出的影像串流全都標著 `qualityLimitationReason: cpu`，每條只剩 11 fps；在高鐵上用 4G 的學生阿哲，送出的五條串流則標著 `bandwidth`，解析度被壓到 180p，其他人看到的阿哲幾乎是一格一格的照片。

```text
                     美咲（老師）
           上行 20 Mbps，但要同時編 5 路 720p ── CPU 滿載 → 11 fps
                ▲   ▲   ▲   ▲   ▲
       ┌────────┘   │   │   │   └────────┐        每一條線＝一條 PeerConnection
       │       ┌────┘   │   └────┐       │        每一條都雙向送 1.54 Mbps
       ▼       ▼        ▼        ▼       ▼
     小安 ◄──► 小芸 ◄──► 阿哲 ◄──► 學生 D ◄──► 學生 E     （學生之間也兩兩相連）
                         │
              4G 上行約 2 Mbps，卻要送 5 × 1.54 ＝ 7.7 Mbps
              → 頻寬估計把每條壓到 180p，其他人看到「照片」
```

這張圖是 Joe 在事後檢討會上畫的。六個人兩兩相連，共有 15 條 PeerConnection；每個人都要把自己的影像「各送一份」給其他五個人，所以上行需求是一對一的五倍。美咲的上傳線路有 20 Mbps，頻寬沒問題，卡在 CPU：瀏覽器替每條 PeerConnection 各跑一個 encoder，五個 720p 的編碼器同時跑，一般筆電撐不住。阿哲剛好相反，CPU 夠，但 4G 上行只有約 2 Mbps，要塞進 7.7 Mbps 的需求，WebRTC 的頻寬估計只好把每一條都壓到最低。

阿德在檢討會最後說：「mesh 沒有錯，它只是不適合六個人。我們不要急著換技術，先照 system design 的流程走一遍：需求、估算、架構、深入元件、擴展。」小晴被指派和 Joe 一起寫設計文件。這一章就是那份文件：從一對一與六人小班的需求開始，用公式比較 mesh、SFU、MCU，然後一路深入到 simulcast、頻寬估計、丟包恢復、TURN 與 SFU 的擴展，最後回到那天晚上 `webrtc-internals` 上的指標。不懂這些，你只能看到「卡」這一個字；懂了以後，你能說出卡在哪一段、該由誰調整。

## 37.2 需求：一對一與六人小班課

設計的第一步是把「要做什麼」寫成可以檢查的句子。小晴先列出功能需求：一對一課是老師與學生互看大畫面；小班課是一位老師加最多五位學生，學生畫面上老師是大格、同學是小格，老師畫面上五位學生平均分配；兩種課都可以分享螢幕，小班課預設錄影（給請假的學生補看），一對一由老師決定是否錄影。

非功能需求才是架構的真正來源。延遲方面，ITU-T G.114 建議單向的嘴到耳延遲在 150 ms 內最理想、超過 400 ms 對話就明顯不自然；聲聲 Live 的語言課需要大量你來我往的口說練習，所以把目標定在台灣境內單向 300 ms 以內，其中網路段（含 jitter buffer）分到約 150 ms。規模方面，從營運資料推估晚上八點尖峰同時有 2,000 間一對一與 300 間小班課。網路方面，學生有三成用手機，包含行動網路與學校、公司的 Wi-Fi；有些企業網路封鎖 UDP。可靠度方面，媒體伺服器掛掉時，教室要在 10 秒內自動恢復，不需要使用者重新整理。

| 項目 | 一對一 | 六人小班 | 對架構的影響 |
|---|---|---|---|
| 人數 | 2 | 老師 1＋學生 ≤ 5 | 決定 mesh 是否可行 |
| 畫面 | 對方大格 720p | 老師大格 720p、同學小格 180p | 每位接收者要的畫質不同 → simulcast |
| 尖峰數量 | 2,000 間 | 300 間 | 伺服器頻寬與節點數 |
| 延遲 | 單向 ≤ 300 ms | 單向 ≤ 300 ms | 不能用直播式的秒級緩衝（第 38 章） |
| 錄影 | 可選 | 預設開 | 伺服器要能拿到媒體 |
| 網路 | 行動網路、封鎖 UDP 的企業網路 | 同左 | TURN／TCP 後備 |
| 故障恢復 | 10 秒內 | 10 秒內 | 節點狀態可重建、client 自動重連 |

這張表的最後一欄是小晴特別加的：每一列需求都要對應到一個架構決定，沒有對應的需求等於沒寫。例如「同學小格 180p」直接否定了「每個人都收 720p」的天真設計；「錄影」意味著媒體一定要經過伺服器，純 P2P 做不到；「封鎖 UDP」則注定要有 TCP 或 TLS 443 的後備路徑。

## 37.3 估算：Mesh、SFU、MCU 的頻寬與 CPU

在畫架構圖之前，先把三種拓撲的成本寫成公式。設教室有 N 個人，每個人送一路影像，碼率是 b（bitrate，每秒送多少 bits）。聲聲 Live 的編碼設定是：720p 的影像 1,500 kbps、360p 500 kbps、180p 150 kbps，Opus 音訊含封包開銷粗估 40 kbps；所以「一路 720p 影音」是 1.54 Mbps。這些數字是聲聲 Live 自己的設定，不是標準值，換成你的服務要用你的碼率重算。

```text
   Mesh（網狀）                 SFU（選擇性轉送）                MCU（多點控制／混流）

   A ◄───► B                    A ──┐        ┌──► B            A ──┐        ┌──► A'（不含 A 的合成）
   ▲ ╲   ╱ ▲                    B ──┤  SFU   ├──► C            B ──┤  MCU   ├──► B'
   │  ╲ ╱  │                    C ──┤ 只轉送 ├──► D            C ──┤ 解碼→  ├──► C'
   │  ╱ ╲  │                    D ──┘ 不解碼 └──► A            D ──┘ 合成→  └──► D'
   ▼ ╱   ╲ ▼                                                         編碼
   C ◄───► D                    每人送 1 份（或 simulcast 3 層）     每人送 1 份、收 1 份
   每人送 N−1 份、收 N−1 份      每人收 N−1 份（可選不同層）         伺服器：N 解碼＋N 編碼
   伺服器：無                   伺服器：收 N 份、送 N(N−1) 份
```

三種拓撲由左到右，是把工作從使用者端搬到伺服器端的過程。**Mesh** 沒有媒體伺服器，每個人直接把影像送給其他每個人，成本全部落在使用者身上。**SFU**（Selective Forwarding Unit，選擇性轉送單元）是一台只轉送、不解碼的伺服器：每個人只上傳一份，SFU 再複製給其他人；「選擇性」指的是 SFU 可以替每位接收者決定要轉哪些串流、哪一層畫質。**MCU**（Multipoint Control Unit，多點控制單元）則把所有人的影像解碼、拼成一個畫面、再重新編碼，每個人只收一路合成後的影像。

把成本寫成公式：

| 項目 | Mesh | SFU | MCU |
|---|---|---|---|
| 每人上行 | (N−1)·b | b（simulcast 時是各層總和） | b |
| 每人下行 | (N−1)·b | 依選層，最多 (N−1)·b | 1 路合成，約 b |
| 每人編碼器數 | N−1 | 1；simulcast 時 3 個（各層各編一次，低層解析度小） | 1 |
| 每人解碼器數 | N−1 | N−1 | 1 |
| 伺服器收 | 0 | N·b | N·b |
| 伺服器送 | 0 | 最多 N·(N−1)·b | N·b |
| 伺服器 CPU | 無 | 每個封包解密一次、對每位接收者加密一次 | N 路解碼＋合成＋最多 N 路編碼 |
| 端到端延遲 | 最低（直連） | 多一跳轉送，約幾毫秒 | 多一次解碼、合成與編碼，常見數十到上百毫秒 |
| 伺服器看得到媒體 | 否 | 是（SRTP 在 SFU 解開） | 是 |

代入 N＝6 手算一次。Mesh 的每人上行是 5 × 1.54＝7.7 Mbps，這就是阿哲那台 4G 手機的死因；每人要同時跑 5 個 encoder 與 5 個 decoder，這是美咲筆電的死因。整間教室有 6 × 5 ÷ 2＝15 條 PeerConnection，人數翻倍到 12 人時是 66 條，連線數以 N² 成長。SFU 的每人上行與人數無關：不開 simulcast 是 1.54 Mbps，開三層 simulcast 是 1.5＋0.5＋0.15＋0.04＝2.19 Mbps；每人下行若全部收 720p 仍是 7.7 Mbps，但 SFU 可以依版面只給同學的 180p，下行就降到 2.3 Mbps（37.13 節的程式會算出這個數字）。MCU 的每人上下行都只有 1.54 Mbps，代價是伺服器要解 6 路、編 6 路：每個人看到的合成畫面不應該包含自己，所以要替每個人各編一次；如果所有人接受同一個版面（包含自己），可以只編一次，但仍然要解碼全部的人。

從公式可以讀出各自的甜蜜點。Mesh 在 N＝2 時和 P2P 一模一樣，沒有伺服器成本、延遲最低；N＝3 勉強可行；N 再大就被使用者的上行頻寬與 CPU 擋住。SFU 把上行固定成常數，把 N² 的複製工作搬到資料中心的大頻寬網卡上，而且不碰 codec，所以單台能服務的人數遠大於 MCU，是今天多人視訊的主流。MCU 適合使用者端最弱的場景：只能解一路影像的舊設備、電話撥入（把聲音混成一路）、或需要「一個合成畫面」的錄影與轉播；它的伺服器成本最高，延遲也最大。

> [!warning] 常見誤解
> 「SFU 的伺服器頻寬是 N²，所以人多了一定比 MCU 貴。」這只說對了一半。SFU 的出口頻寬確實隨 N(N−1) 成長，但它的 CPU 工作只是加解密與複製封包，便宜又容易水平擴展；MCU 的頻寬是線性的，但每一路都要即時轉碼，一台伺服器能撐的教室數通常少很多。實務上，小班課（十人以內）SFU 幾乎總是比較划算；真正幾百人以上的場景，答案通常不是 MCU，而是改成「少數人上台、多數人觀看」的直播架構（37.12 節與第 38 章）。

最後估算尖峰總量。一對一的課不需要 simulcast（只有一位接收者，SFU 不必選層），每間教室 SFU 收 2 × 1.54＝3.08 Mbps、送 3.08 Mbps；2,000 間就是收送各約 6.2 Gbps。小班課每間收 6 × 2.19＝13.14 Mbps；送出依版面計算，五位學生各收 2.3 Mbps、老師收五位學生的 360p 共 2.7 Mbps，合計 14.2 Mbps；300 間就是收 3.9 Gbps、送 4.3 Gbps。兩者相加，尖峰時 SFU 群要收約 10.1 Gbps、送約 10.4 Gbps。如果壓測得出單台 SFU 的安全上限是 3 Gbps（這是聲聲 Live 的假設，實際要看機型、網卡、封包率與軟體），至少需要 4 台，再加上一台故障時的餘裕（N+1）與部署時排空用的一台，規劃 6 台。

## 37.4 架構：聲聲 Live 的媒體平面

估算完，小晴和 Joe 討論一對一要不要也改走 SFU。留在 P2P 的理由很實在：P2P 不花伺服器頻寬，2,000 間一對一可以省下約 6 Gbps；直連的延遲也最低。但改走 SFU 的理由更多。第一，錄影需要伺服器拿得到媒體。第二，P2P 時學生會在 ICE candidate 裡看到老師家的公網 IP（第 36 章），老師們對此有疑慮；走 SFU 時雙方只看到 SFU 的位址。第三，SFU 有固定的公網位址，client 對它的連線成功率比兩個 NAT 互打高得多，需要 TURN 的比例因此下降。第四，兩種課共用同一條媒體管線，品質監控、除錯工具與 SFU 端的丟包恢復只要做一次；一對一課臨時加入一位旁聽的督導老師，也不必中途切換架構。最後的決定是：**一對一與小班課都走 SFU**，P2P 只保留在內部測試工具裡。

```text
  學生／老師瀏覽器
     │ ① wss://rt.shengsheng.example（203.0.113.40，L4 LB → nginx 10.20.2.11–.13 → uvicorn）
     │    加入教室、交換 SDP 與 ICE candidate、收到「你的 SFU 是哪一台」
     ▼
  ┌──────────────┐   ② 查詢／指派 room → SFU 節點   ┌────────────────────────┐
  │ 即時服務      │ ───────────────────────────────► │ room 註冊表（Redis 類）  │
  │（signaling）  │ ◄─────────────────────────────── │ room 8812 → sfu-tpe-1   │
  └──────────────┘                                   └────────────────────────┘
     │ ③ 把 SFU 的 SDP answer 轉回瀏覽器
     ▼
  瀏覽器 ══ ④ ICE／DTLS-SRTP（UDP 40000）══► sfu-tpe-1  公網 203.0.113.60／VPC 10.20.1.15
     ║                                          │  │
     ║ ⑤ UDP 被封鎖時：TURN over TLS 443         │  └─ ⑦ 品質回報 UDP → collector 10.20.3.7:5005（第 2 章）
     ╚═════► turn 203.0.113.50 ═══(VPC 內)══════╝
                                                └─ ⑥ 錄製服務 10.20.1.5 以「隱形參與者」訂閱
```

這張圖把**控制平面**與**媒體平面**分開畫。① 瀏覽器先用 WebSocket 連到即時服務，這條路走的是第 33 章設計的 `rt` 叢集，只傳 JSON 訊息，量很小。② 即時服務查 room 註冊表：教室 8812 若還沒有節點，就挑一台負載最低的 SFU 並寫進註冊表，之後加入的人都被導到同一台。③ 瀏覽器對 SFU 做 offer／answer，SFU 回的 SDP 裡帶著自己的 candidate：`203.0.113.60` 的 UDP 40000（第 35 章 SDP 裡的那個 candidate）。④ 媒體直接在瀏覽器與 SFU 之間走 DTLS-SRTP，不經過 nginx 或 LB。⑤ 當 UDP 被封鎖，瀏覽器改經 TURN over TLS 443 連到 TURN，TURN 再在 VPC 內把封包轉給 SFU。⑥ 錄製服務像一位不出聲、不出畫面的參與者一樣訂閱所有串流，在 SFU 之外做合成。⑦ 每台 SFU 每秒把各教室的 RTT 與丟包送到 collector，就是第 2 章那個 12 bytes 的品質回報。

幾個細節值得說明。SFU 用 **ICE-lite**：它有固定公網位址，不需要收集 srflx 或 relay candidate，只回應 client 的連線檢查，實作與狀態都比較簡單。所有參與者共用一個 UDP port（40000），SFU 靠 STUN 訊息裡的 ICE username fragment 與五元組分辨封包屬於哪一條連線，好處是防火牆與 security group 只要開一個 port。SFU 不放在 L4 LB 後面：LB 對 UDP 的「連線」只能靠五元組與逾時猜，NAT 重新綁定或手機換網路時封包可能被送到另一台 SFU，那台 SFU 沒有這條 DTLS 連線的金鑰。所以每台 SFU 都有自己的公網 IP，由 signaling 告訴 client 要連哪一台；這和第 25 章「LB 把請求分到任一台後端」的模式不同，是有狀態服務的典型做法。

## 37.5 深入 SFU：轉送、改寫與 RTCP 終結

SFU 常被說成「只是轉送封包」，但一個好 SFU 做的事比轉送多得多。理解它內部的管線，才能理解後面每一節的機制落在哪裡。

```text
  publisher（美咲）                       SFU                                   subscriber（小安）
 ┌───────────┐  SRTP  ┌─────────────────────────────────────────────────┐  SRTP  ┌───────────┐
 │ encoder   │═══════►│ ① DTLS-SRTP 解密（每個 publisher 一把金鑰）       │═══════►│ decoder   │
 │ l／m／h 三層│        │ ② 解析 RTP header 與 extension：SSRC、seq、ts、   │        │           │
 └───────────┘        │    rid、TWCC 序號、audio level                     │        └───────────┘
      ▲               │ ③ 存進重送 buffer（每路保留最近約 1 秒）           │              │
      │               │ ④ 依每位 subscriber 的頻寬與版面選層               │              │
      │               │ ⑤ 改寫 SSRC／seq／timestamp，讓換層看起來連續       │              │
      │               │ ⑥ 用 subscriber 的金鑰重新加密、pacing 後送出      │              │
      │               └─────────────────────────────────────────────────┘              │
      │                    ▲ RTCP 在 SFU 終結，不直接轉給 publisher                       │
      └── PLI（合併、限速後才轉）◄──┴── NACK 由 SFU 從 buffer 直接重送 ◄── NACK／PLI／TWCC ┘
```

由上往下讀這條管線。① 每一條 PeerConnection 都在 SFU 終結 DTLS，所以 SFU 拿得到 SRTP 金鑰、看得到 RTP 明文；這是它能選層、能錄影的前提，也意味著它不是端到端加密（37.12 節會談 E2EE）。② SFU 只解析 RTP header 與 header extension，不碰 payload 裡的影像資料：`rid` 告訴它這個封包屬於 simulcast 的哪一層，TWCC 序號用於頻寬估計，audio level 讓它知道誰在說話。③ 每路串流保留最近約一秒的封包，用來服務 NACK。④ 選層是 SFU 的核心邏輯，37.6 節與 37.13 節的實驗二會詳細模擬。⑤ 是最容易被忽略的一步：三層 simulcast 是三條獨立的 RTP 串流，各有自己的 SSRC、序號與 timestamp；如果 SFU 直接把封包轉出去，接收端在換層的那一刻會看到 SSRC 改變、序號跳號，以為掉了幾千個封包。所以 SFU 對每位 subscriber 維持一條「虛擬串流」，把來源封包的序號與 timestamp 平移成連續的值。⑥ 用 subscriber 那條連線的金鑰重新加密，並以 pacing（把封包平均分散送出，第 12 章）避免一次把 keyframe 的幾十個封包灌進對方的佇列。

序號改寫可以手算一次。假設小安目前收的是 m 層，SFU 送出的最後一個封包序號是 5000，對應 m 層的來源序號 31200，所以 offset＝5000 − 31200。現在要切到 h 層，h 層的 keyframe 從來源序號 870 開始；SFU 把新的 offset 設成 5001 − 870，於是 870 變成 5001、871 變成 5002，小安的瀏覽器看到的是一條沒有斷號的串流。序號是 16 bit，運算都要 mod 65536；timestamp 也要做同樣的平移，否則 jitter buffer 會以為時間倒退或跳躍。

RTCP 的處理方式是另一個關鍵。SFU **終結** RTCP：小安送來的 NACK 由 SFU 從自己的 buffer 重送，不轉給美咲，因為 SFU 到小安這一段的丟包與美咲無關；小安的頻寬估計回饋也只用來決定 SFU 給小安哪一層，不轉給美咲，否則一個網路差的接收者會拖垮整間教室。只有「需要新的 keyframe」這件事 SFU 自己做不到，必須轉 PLI 給美咲；但五位學生可能在同一秒都要 keyframe，SFU 會把同一層的請求合併，並限制轉給 publisher 的頻率。37.8 節會看到，keyframe 是最貴的封包，不加限制的 PLI 轉發是多人教室卡頓的常見原因。

音訊另外處理。Opus 的碼率很低，六人教室直接把五路音訊全部轉給每個人即可；大型會議則常用「last-N」：SFU 依 RTP header extension 裡的 audio level（RFC 6464，送出端在 header 裡標示這個封包的音量）挑出最近說話最大聲的幾個人，只轉他們的音訊與影像。混音交給接收端的瀏覽器做，所以 SFU 仍然不必解碼。

MCU 在這套架構中並沒有消失，而是換了位置。聲聲 Live 的錄製服務訂閱所有串流後，在 VPC 內把它們解碼、依版面合成、編成一個檔案，這正是 MCU 做的事，只是不在即時路徑上，延遲與 CPU 成本不影響上課。如果未來要接電話撥入（讓學生用市話聽課），也會用一個 MCU 式的元件把教室的聲音混成一路。把「合成」放在需要的地方，而不是讓每個人都付出合成的延遲，是現代架構的共同取捨。

## 37.6 Simulcast 與 SVC：一份上傳，多種畫質

SFU 不解碼，卻要讓光纖上的小安看 720p、高鐵上的阿哲看 180p，畫質從哪裡來？答案是讓**送出端**一次準備好多種畫質，SFU 只負責挑。做法有兩種。

**Simulcast**（同步多路廣播）是送出端同時編出幾個獨立的版本，例如 720p、360p、180p 各一路，每一路都是完整、可以單獨解碼的串流。在 WebRTC 裡，三層用 **RID**（RTP stream identifier）區分，寫在 SDP 與每個 RTP 封包的 header extension 裡。聲聲 Live 的老師端這樣建立送出的 transceiver：

```javascript
// 瀏覽器端（示意）：一個鏡頭來源，編出三層 simulcast
pc.addTransceiver(cameraTrack, {
  direction: "sendonly",
  sendEncodings: [
    { rid: "l", scaleResolutionDownBy: 4, maxBitrate: 150_000 },
    { rid: "m", scaleResolutionDownBy: 2, maxBitrate: 500_000 },
    { rid: "h", scaleResolutionDownBy: 1, maxBitrate: 1_500_000 },
  ],
});
```

對應到 offer 裡的 media section，會多出這幾行（只節錄與本章有關的部分，第 35 章逐行解讀過其他欄位）：

```text
m=video 9 UDP/TLS/RTP/SAVPF 96 97
a=mid:1
a=extmap:3 …/draft-holmer-rmcat-transport-wide-cc-extensions-01
a=extmap:4 urn:ietf:params:rtp-hdrext:sdes:rtp-stream-id
a=extmap:5 urn:ietf:params:rtp-hdrext:sdes:repaired-rtp-stream-id
a=rtpmap:96 VP8/90000
a=rtcp-fb:96 goog-remb
a=rtcp-fb:96 transport-cc
a=rtcp-fb:96 ccm fir
a=rtcp-fb:96 nack
a=rtcp-fb:96 nack pli
a=rtpmap:97 rtx/90000
a=fmtp:97 apt=96
a=rid:l send
a=rid:m send
a=rid:h send
a=simulcast:send l;m;h
```

逐行對照。`a=rid` 三行宣告三層，`a=simulcast:send l;m;h` 說「我會同時送這三層」。`rtp-stream-id` extension 讓每個 RTP 封包標明自己屬於哪個 rid，`repaired-rtp-stream-id` 用在重送封包上。`rtcp-fb` 這五行是這條串流支援的回饋機制：`goog-remb` 與 `transport-cc` 是兩種頻寬估計回饋（37.7 節），`ccm fir`、`nack`、`nack pli` 是丟包恢復與 keyframe 請求（37.8 節）。`rtx/90000` 搭配 `apt=96` 宣告一個專門用來重送的 payload type。第 3 行的 extension URI 很長，這裡用「…」省略了前段。

**SVC**（Scalable Video Coding，可分層編碼）則只編**一路**串流，但這路串流內部分層：base layer 可以單獨解碼，enhancement layer 疊加在上面提升畫質。分層的維度有兩種：**temporal**（時間層，提升 frame rate）與 **spatial**（空間層，提升解析度）。WebRTC 用 `scalabilityMode` 字串描述結構，例如 `L1T3` 是 1 個空間層、3 個時間層；`L3T3` 是 3 個空間層、各 3 個時間層。

```text
 temporal 分層（L1T3，30 fps）：箭頭指向「解碼時依賴的 frame」

 T2 ─────────┐   ●───┐       ●───┐       ●───┐       ●        T0＋T1＋T2：30 fps
             │   │   │       │   │       │   │       │
 T1 ─────────┤   │   ●───────┼───┼───────●   │       │        T0＋T1：15 fps
             │   │   │       │   │       │   │       │
 T0 ─────────┴►  ●◄──┴───────●◄──┴───────●◄──┴───────●        只有 T0：7.5 fps
   frame 編號    0   1   2   3   4   5   6   7   8 …
                 （T0 只依賴前一個 T0；T1 依賴 T0；T2 依賴 T0 或 T1）
```

這張圖說明 temporal 分層為什麼能「直接丟」。frame 0、4、8 是 T0，只依賴前一個 T0；frame 2、6 是 T1，依賴 T0；奇數 frame 是 T2，沒有人依賴它們。所以 SFU 想替某位接收者省頻寬時，可以把所有 T2 封包丟掉，對方仍然能正常解碼，只是 frame rate 從 30 降到 15；再丟掉 T1 就剩 7.5 fps。這個動作不需要 keyframe、不需要通知送出端，下一個封包就生效，是 SFU 手上最快的降速手段。VP8 的 simulcast 每一層裡也可以有 temporal 分層，所以兩種技術常常一起出現。

| 比較 | Simulcast | SVC |
|---|---|---|
| 送出端產出 | 多路獨立串流（各有 SSRC） | 一路分層串流 |
| 上行成本 | 各層總和，例如 1.5＋0.5＋0.15 Mbps | 比 simulcast 少，分層本身約有一成到三成的編碼開銷（依 codec 與內容） |
| 送出端 CPU | 編多次（低層解析度小，成本較低） | 編一次，但編碼器較複雜 |
| SFU 降 spatial 層 | 換到另一路串流，要等該路的 keyframe | 丟掉上層封包即可，通常不必等 keyframe |
| SFU 升 spatial 層 | 要等目標層的 keyframe（送 PLI） | 要等該層的切換點（依結構而定） |
| codec 支援 | VP8、H.264、VP9、AV1 等都常見 | 主要是 VP9、AV1（H.264 的 SVC 在 WebRTC 很少見） |
| SFU 需要懂的事 | 看 rid、改寫序號與 timestamp | 要解析 codec 的分層資訊（例如 AV1 的 dependency descriptor） |

選擇的依據通常是相容性。Simulcast 對接收端完全透明：每位接收者收到的都是一條普通的單層串流，任何能解這個 codec 的瀏覽器都能看；SVC 則要求接收端能解分層串流，SFU 也必須懂 codec 的分層格式。聲聲 Live 的學生裝置五花八門，所以第一版用 VP8 三層 simulcast，每層內含 temporal 分層；SVC 列為之後的最佳化。

> [!note] 2026 現況
> 截至 2026 年 10 月，Chromium 系瀏覽器支援以 `scalabilityMode` 設定 VP9、AV1 的 SVC，Safari 與 Firefox 的支援範圍各有差異（本書未逐一查證）。部署前應以 `RTCRtpSender.getCapabilities("video")` 查詢 codec 與 `scalabilityModes`，並在目標裝置上實測硬體編碼器是否支援所選的模式；AV1 的 WebRTC 支援也和第 34 章談的 `<video>` 播放支援分開判斷。

無論 simulcast 還是 SVC，SFU 都要決定每位接收者拿哪一層。聲聲 Live 的規則有兩個輸入：**版面**（小格最多 180p，大格最多 720p，看不到的就不送）與**頻寬**（SFU 估出的、到這位接收者的可用頻寬）。分配時先保證所有人的音訊，再給每路影像最低層，最後依優先順序（老師優先）往上升。升層要有 hysteresis（遲滯）：頻寬連續兩秒都夠才升，避免在邊界來回跳；降層則立刻發起。這個策略在 37.13 節的實驗二會完整跑一次。

## 37.7 頻寬估計：GCC、REMB 與 TWCC

SFU 選層需要知道「到這位接收者還能送多少」，送出端調整碼率也需要知道「上行還能送多少」。TCP 有擁塞控制（第 12 章），但 WebRTC 的媒體走 UDP 上的 RTP，沒有人替它做這件事，所以 WebRTC 要自己估計頻寬，這是 **bandwidth estimation**（BWE，頻寬估計）。即時影音的估計比 TCP 更難：TCP 塞車時多等一下沒關係，視訊塞車一秒，畫面就凍結一秒；所以 WebRTC 的目標不是「把管子塞滿」，而是在佇列開始變長之前就減速。

最廣為人知的演算法是 Google 提出的 **GCC**（Google Congestion Control），描述在 IETF RMCAT 工作小組的 draft 中（這份 draft 沒有成為 RFC，但 libwebrtc 的實作就是從它演進來的）。GCC 由兩個控制器組成。**延遲型控制器**觀察封包的到達時間：如果一組封包送出的間隔是 20 ms，到達的間隔卻變成 25 ms，代表它們在路上某個佇列裡多等了 5 ms，佇列正在變長。GCC 計算「到達間隔減去送出間隔」並累積起來，再求它的趨勢（早期實作用 Kalman filter，後來的實作改用線性迴歸求斜率，稱為 trendline）。斜率超過門檻就判定 **overuse**（過度使用），把目標碼率降到「目前實際收到的速率 × 0.85」；斜率接近零是 normal，碼率每秒最多乘上約 1.08 慢慢加；斜率為負是 underuse，代表佇列正在排空，先維持不動。這個計算只用到兩個時間的「差值」，所以不需要兩端時鐘同步。

**丟包型控制器**則看 RTCP 回報的丟包率：丟包率高於 10% 時把碼率乘上（1 − 0.5 × 丟包率），低於 2% 時每次提高 5%，介於兩者之間維持不變。最後送出端取兩個控制器的較小值。延遲型負責在 bufferbloat（第 12 章）發生前就退讓，丟包型負責處理淺 buffer 或無線網路的隨機丟包。下面的程式用一串預先寫好的到達間隔，示範延遲型控制器的判斷：

```python
# 簡化版的 GCC 延遲型估計：看「到達間隔 − 送出間隔」的趨勢判斷佇列是否在變長
SEND_GAP = 20.0                      # 每 20 ms 送出一組封包（一個 frame）
# 每組的到達間隔（ms）：前 6 組正常；接著瓶頸塞住、佇列變長；減速一個 RTT 後佇列排空
ARRIVAL_GAPS = [20, 21, 19, 20, 20, 21, 24, 25, 26, 25, 17, 15, 16, 17, 19, 20, 20, 20, 21, 20]
WINDOW = 6                           # 用最近 6 組做線性迴歸求斜率
THRESHOLD = 1.0                      # 斜率（ms／組）超過它就判定 overuse；真實實作會自適應調整

rate = 1500.0                        # 目前的目標碼率 kbps
acc, history, state_log, prev = 0.0, [], [], "normal"
for i, gap in enumerate(ARRIVAL_GAPS):
    acc += gap - SEND_GAP            # 累積的單向延遲變化（不需要兩端時鐘同步）
    history.append(acc)
    pts = history[-WINDOW:]
    n = len(pts)
    mean_x, mean_y = (n - 1) / 2, sum(pts) / n
    var = sum((x - mean_x) ** 2 for x in range(n)) or 1
    slope = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(pts)) / var
    if slope > THRESHOLD:
        state = "overuse"
        if prev != "overuse":                     # 真實實作也會限制減速頻率（約一個 RTT 一次）
            received = 1500 * SEND_GAP / gap      # 對方實際收到的速率 ≈ 瓶頸頻寬
            rate = 0.85 * received                # GCC 的乘法減少：β = 0.85
    elif slope < -THRESHOLD:
        state = "underuse"                        # 佇列在排空：先別加速，等它排乾淨
    else:
        state = "normal"
        rate *= 1.08 ** (SEND_GAP / 1000)         # 每秒最多約 +8%（乘法增加）
    state_log.append(state)
    prev = state
    print(f"組 {i:>2}  到達間隔 {gap:>2} ms  累積延遲 {acc:>+5.1f} ms  斜率 {slope:>+5.2f}"
          f"  {state:<8}  目標碼率 {rate:7.1f} kbps")

assert "overuse" in state_log and state_log[0] == "normal"
assert 1000 < rate < 1100                         # 降到瓶頸的 85% 附近，然後緩慢回升
```

```text
組  0  到達間隔 20 ms  累積延遲  +0.0 ms  斜率 +0.00  normal    目標碼率  1502.3 kbps
組  1  到達間隔 21 ms  累積延遲  +1.0 ms  斜率 +1.00  normal    目標碼率  1504.6 kbps
組  2  到達間隔 19 ms  累積延遲  +0.0 ms  斜率 +0.00  normal    目標碼率  1506.9 kbps
組  3  到達間隔 20 ms  累積延遲  +0.0 ms  斜率 -0.10  normal    目標碼率  1509.3 kbps
組  4  到達間隔 20 ms  累積延遲  +0.0 ms  斜率 -0.10  normal    目標碼率  1511.6 kbps
組  5  到達間隔 21 ms  累積延遲  +1.0 ms  斜率 +0.06  normal    目標碼率  1513.9 kbps
組  6  到達間隔 24 ms  累積延遲  +5.0 ms  斜率 +0.66  normal    目標碼率  1516.2 kbps
組  7  到達間隔 25 ms  累積延遲 +10.0 ms  斜率 +1.89  overuse   目標碼率  1020.0 kbps
組  8  到達間隔 26 ms  累積延遲 +16.0 ms  斜率 +3.26  overuse   目標碼率  1020.0 kbps
組  9  到達間隔 25 ms  累積延遲 +21.0 ms  斜率 +4.43  overuse   目標碼率  1020.0 kbps
組 10  到達間隔 17 ms  累積延遲 +18.0 ms  斜率 +3.97  overuse   目標碼率  1020.0 kbps
組 11  到達間隔 15 ms  累積延遲 +13.0 ms  斜率 +1.97  overuse   目標碼率  1020.0 kbps
組 12  到達間隔 16 ms  累積延遲  +9.0 ms  斜率 -0.49  normal    目標碼率  1021.6 kbps
組 13  到達間隔 17 ms  累積延遲  +6.0 ms  斜率 -2.60  underuse  目標碼率  1021.6 kbps
組 14  到達間隔 19 ms  累積延遲  +5.0 ms  斜率 -3.43  underuse  目標碼率  1021.6 kbps
組 15  到達間隔 20 ms  累積延遲  +5.0 ms  斜率 -2.63  underuse  目標碼率  1021.6 kbps
組 16  到達間隔 20 ms  累積延遲  +5.0 ms  斜率 -1.51  underuse  目標碼率  1021.6 kbps
組 17  到達間隔 20 ms  累積延遲  +5.0 ms  斜率 -0.66  normal    目標碼率  1023.1 kbps
組 18  到達間隔 21 ms  累積延遲  +6.0 ms  斜率 +0.00  normal    目標碼率  1024.7 kbps
組 19  到達間隔 20 ms  累積延遲  +6.0 ms  斜率 +0.23  normal    目標碼率  1026.3 kbps
```

逐段讀輸出。組 0 到 5 的到達間隔在 19 到 21 ms 之間抖動，累積延遲在 0 附近，斜率很小，狀態是 normal，碼率每組增加約 0.15%（每秒約 8%）。組 6 開始到達間隔變成 24、25、26 ms，代表瓶頸的速率比送出速率低，封包在佇列裡越排越久；累積延遲從 1 ms 爬到 21 ms，斜率在組 7 超過門檻，判定 overuse，目標碼率立刻降到 1500 × 20 ÷ 25 × 0.85＝1020 kbps，也就是瓶頸頻寬 1200 kbps 的 85%。注意此時還沒有任何封包遺失：延遲型控制器在佇列只多了 10 ms 時就退讓了，loss-based 的 TCP 要等到佇列滿才會反應。

組 8、9 的到達間隔仍然很大，因為減速前送出的封包還在路上，這是「回饋晚一個 RTT」的必然結果；程式和真實實作一樣，不在同一段 overuse 期間重複減速。組 10 之後到達間隔小於 20 ms，因為送出速率已經低於瓶頸，佇列開始排空；斜率轉為負值，狀態變成 underuse，碼率維持不動，等佇列排乾淨。組 17 回到 normal 後才重新緩慢加速。整個過程中累積延遲最多只多了 21 ms 左右就被控制住，這正是即時影音需要的行為。

GCC 的計算放在哪一端，決定了要用哪一種回饋。早期的做法是**接收端估計**：接收端自己跑延遲型控制器，把估出來的頻寬用 **REMB**（Receiver Estimated Maximum Bitrate）RTCP 訊息告訴送出端。REMB 是一個 Google 提出的 draft，沒有成為 RFC，但被廣泛實作：

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───┬─┬─────────┬───────────────┬───────────────────────────────┐
 │V=2│P│ FMT=15  │    PT=206     │            length             │  RTCP header（PSFB）
 ├───┴─┴─────────┴───────────────┴───────────────────────────────┤
 │                     SSRC of packet sender                     │
 ├───────────────────────────────────────────────────────────────┤
 │                SSRC of media source（固定為 0）                │
 ├───────────────┬───────────────┬───────────────┬───────────────┤
 │      'R'      │      'E'      │      'M'      │      'B'      │  識別字串
 ├───────────────┼───────────┬───┴───────────────┴───────────────┤
 │   Num SSRC    │ BR Exp(6) │        BR Mantissa（18 bits）       │  頻寬 = mantissa × 2^exp
 ├───────────────┴───────────┴───────────────────────────────────┤
 │                  SSRC feedback（Num SSRC 個）                  │
 └───────────────────────────────────────────────────────────────┘
```

REMB 用指數與尾數表示頻寬，18 bit 的尾數最大是 262,143。手算 1,020,000 bps：除以 2² 得到 255,000，小於 262,143，所以 exp＝2、mantissa＝255,000，還原回來剛好是 1,020,000 bps。PT＝206 代表 payload-specific feedback，FMT＝15 是「application layer feedback」，靠後面的 'REMB' 四個字元辨認。

後來 libwebrtc 把估計搬到**送出端**，改用 **TWCC**（Transport-wide Congestion Control）。送出端在每個 RTP 封包的 header extension 裡加一個 16 bit 的 transport-wide 序號，這個序號橫跨同一條 transport 上的所有串流（BUNDLE 後音訊、各層影像共用一個 5-tuple，第 35 章），接收端只負責回報「每個序號的封包在什麼時間到達」，送出端自己對照送出時間來估計。回報的 RTCP 格式是 PT＝205（transport-layer feedback）、FMT＝15，內容包含 base sequence number、封包狀態數量、以 64 ms 為單位的參考時間、用 run-length 或 bit vector 壓縮的「有沒有收到」，以及以 250 µs 為單位的到達時間差。

| 比較 | REMB | TWCC |
|---|---|---|
| 誰跑估計演算法 | 接收端 | 送出端 |
| 回饋內容 | 一個數字：建議的最大碼率 | 每個封包的到達時間 |
| 涵蓋範圍 | 指定的 SSRC | 整條 transport 的所有封包（含重送與 padding） |
| 演算法升級 | 要改接收端 | 只改送出端 |
| 回饋頻寬 | 很小 | 較大（每 50–100 ms 左右回報一次，依實作） |
| 標準化 | Google draft，未成為 RFC | Google draft；IETF 另有 RFC 8888 的通用回饋格式 |
| SDP | `a=rtcp-fb:96 goog-remb` | `a=rtcp-fb:96 transport-cc`＋extmap |

TWCC 勝出的理由是「送出端知道最多」：只有送出端知道每個封包送出的確切時間、大小、是不是重送或探測用的 padding，演算法改進也只需要更新送出端。對 SFU 的意義是：SFU 送給每位接收者的那一段，SFU 自己就是送出端，它用 TWCC 估出「到小安還能送多少、到阿哲還能送多少」，作為選層的輸入；美咲上傳到 SFU 的那一段，美咲的瀏覽器是送出端，根據 SFU 回的 TWCC 回饋調整三層的碼率。兩段的估計完全獨立，這就是阿哲的 4G 不會拖垮小安的原因。

估計值往上爬需要證據：如果目前只送 500 kbps，送出端不知道路徑能不能撐 1.5 Mbps。所以送出端（或 SFU）會**探測**（probing）：短時間內用 padding 或重送封包把速率拉高，看延遲有沒有上升。SFU 在把某位接收者從 m 層升到 h 層之前先探測，確認頻寬真的夠，才送 PLI 要 h 層的 keyframe；否則升上去馬上塞車，又要降回來，白白浪費一個 keyframe。

## 37.8 丟包恢復：NACK、PLI／FIR 與 FEC

頻寬估計處理的是「送太多」，丟包恢復處理的是「送了卻沒到」。影像的壓縮依賴前後 frame（第 34 章的 GOP 與 P frame），一個封包遺失，不只那個 frame 壞掉，之後依賴它的每一個 frame 都會出現馬賽克，直到下一個 keyframe。即時影音有三種補救方式：重送、要求新的 keyframe、事先加上冗餘。它們的成本與適用條件完全不同。

**NACK**（Negative Acknowledgement，否定確認）是接收端發現序號有缺口時，主動告訴送出端「這幾號沒收到」。WebRTC 用的是 RFC 4585 定義的 Generic NACK，封包格式是：

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───┬─┬─────────┬───────────────┬───────────────────────────────┐
 │V=2│P│  FMT=1  │    PT=205     │            length             │  RTCP header（RTPFB）
 ├───┴─┴─────────┴───────────────┴───────────────────────────────┤
 │                     SSRC of packet sender                     │
 ├───────────────────────────────────────────────────────────────┤
 │                     SSRC of media source                      │  哪一條串流掉了封包
 ├───────────────────────────────┬───────────────────────────────┤
 │           PID（16）            │           BLP（16）            │  FCI，可重複多組
 └───────────────────────────────┴───────────────────────────────┘
   PID：第一個遺失的序號；BLP：bit i＝1 代表 PID+i+1 也遺失
```

每組 FCI（feedback control information）用 4 bytes 描述最多 17 個序號：PID 是第一個遺失的序號，BLP 的 16 個 bit 分別代表後面 16 個序號是否也遺失。下面的程式把一串遺失序號壓成 NACK 封包再解回來：

```python
import struct


def nack_fci(lost):
    """把遺失的序號壓成 Generic NACK 的 (PID, BLP) 組：每組最多涵蓋 17 個連續序號。"""
    pairs, todo = [], sorted(set(lost))
    while todo:
        pid, blp = todo.pop(0), 0
        while todo and (todo[0] - pid) % 65536 <= 16:
            blp |= 1 << ((todo.pop(0) - pid) % 65536 - 1)   # bit i 代表 PID+i+1
        pairs.append((pid, blp))
    return pairs


def build_nack(sender_ssrc, media_ssrc, lost):
    fci = b"".join(struct.pack("!HH", pid, blp) for pid, blp in nack_fci(lost))
    length = (8 + len(fci)) // 4          # RTCP length：32-bit word 數減 1（header 4 bytes 不算）
    header = struct.pack("!BBH", 0x80 | 1, 205, length)   # V=2、FMT=1、PT=205（RTPFB）
    return header + struct.pack("!II", sender_ssrc, media_ssrc) + fci


def parse_nack(pkt):
    first, pt, length = struct.unpack("!BBH", pkt[:4])
    assert first >> 6 == 2 and first & 0x1F == 1 and pt == 205
    lost = []
    for off in range(12, 4 + length * 4, 4):
        pid, blp = struct.unpack("!HH", pkt[off:off + 4])
        lost.append(pid)
        lost += [(pid + i + 1) % 65536 for i in range(16) if blp >> i & 1]
    return lost


lost = [1000, 1001, 1003, 1016, 1017, 1030]
pkt = build_nack(0x5F3A0001, 0x1A2B3C4D, lost)
print("FCI 組：", [(pid, f"{blp:016b}") for pid, blp in nack_fci(lost)])
print("封包  ：", pkt.hex(" "))
print("解回來：", parse_nack(pkt))
assert parse_nack(pkt) == lost and len(pkt) == 20
```

```text
FCI 組： [(1000, '1000000000000101'), (1017, '0001000000000000')]
封包  ： 81 cd 00 04 5f 3a 00 01 1a 2b 3c 4d 03 e8 80 05 03 f9 10 00
解回來： [1000, 1001, 1003, 1016, 1017, 1030]
```

六個遺失序號被壓成兩組 FCI。第一組 PID＝1000，BLP 的 bit 0（1001）、bit 2（1003）、bit 15（1016）為 1，印出來由高位到低位是 `1000000000000101`；1017 距離 1000 有 17，超出一組能涵蓋的範圍，所以開第二組，1030 是 1017＋13，落在 bit 12。封包的第一個 byte `81` 是 V＝2、P＝0、FMT＝1，第二個 byte `cd` 是 205；length＝4 代表整個封包有 5 個 32 bit word，也就是 20 bytes。

送出端收到 NACK 後，用 **RTX**（RFC 4588 的重送格式）把封包重送：重送封包用另一個 payload type（前面 SDP 的 97）與另一個 SSRC，payload 開頭加上 2 bytes 的原始序號。分開成另一條串流，是為了讓接收端與統計不會把重送和原始封包混在一起，頻寬估計也能把重送算進去。SFU 對每位接收者自己服務 NACK，因為它手上有最近一秒的封包。

NACK 的限制是時間。從封包遺失到重送抵達，至少要經過「發現缺口的時間＋一個 RTT」；如果這段時間超過 jitter buffer 願意等的時間，重送的封包到了也沒用。台北的學生到台北的 SFU RTT 約 10 到 40 ms，重送通常趕得上；第 1 章那位美國東岸的學生，到台北的 RTT 約 180 ms，在 120 ms 左右的等待預算下，重送一定遲到。37.13 節的實驗三會量化這件事。

```text
 送出端（SFU）                                          接收端（阿哲）
   │── seq 1000 ───────────────────────────────X  遺失
   │── seq 1001 ─────────────────────────────────────►│  發現 1000 沒到
   │◄─────────────────────────── NACK PID=1000 ───────│
   │── RTX（OSN=1000）───────────────────────────────►│  趕在播放期限前到 → 修好
   │                                                  │
   │   ……連續遺失太多、或重送也趕不上……                 │
   │◄─────────────────────────── PLI ─────────────────│  「我解不下去了」
   │── keyframe（數十個封包，平常 frame 的數倍大）──────►│  畫面從這裡重新開始
```

圖的上半是 NACK 成功的情況：接收端在收到 1001 時發現 1000 沒到，送 NACK，重送的封包在播放期限前抵達。下半是 NACK 救不回來的情況：接收端已經無法正確解碼，只好送 **PLI**（Picture Loss Indication，RFC 4585，PSFB 的 FMT＝1），意思是「我的畫面壞了，請給我一個 keyframe」。另一個類似的訊息是 **FIR**（Full Intra Request，RFC 5104，FMT＝4），語意是「命令」送出端產生 intra frame，帶有序號以便去重，常用在新的接收者加入、或 SFU 切換串流的時候。瀏覽器對兩者的反應實務上都是產生 keyframe。

Keyframe 是最貴的 frame：它不參照任何其他 frame，大小常是一般 P frame 的好幾倍。在六人教室裡，如果五位學生在同一秒各送一次 PLI、SFU 原封不動轉給美咲，美咲就要在一秒內產生五個 keyframe，上行瞬間暴增，反而造成新的塞車與丟包，接著又引發更多 PLI，這叫 **PLI storm**。所以 SFU 要合併同一層的請求、限制轉發頻率，新加入的學生先給低層（低層的 keyframe 小），等穩定後再升層。

**FEC**（Forward Error Correction，前向錯誤更正）的思路完全不同：不等丟了再補，而是事先多送一些冗餘資料，讓接收端自己把遺失的封包算回來。最簡單的形式是 XOR parity：

```text
  媒體封包：  P1        P2        P3        P4        P5
             1011 0010 0110 1100 1110 0001 0100 1111 0001 1010
  parity  ： F = P1 ⊕ P2 ⊕ P3 ⊕ P4 ⊕ P5（每個 bit 做 XOR）

  P3 遺失 → P3 = F ⊕ P1 ⊕ P2 ⊕ P4 ⊕ P5   （任何一個遺失都能算回來）
  P2、P3 都遺失 → 一個方程式兩個未知數，救不回來
```

這張圖說明 FEC 的能力與極限。每 5 個媒體封包加 1 個 parity，額外頻寬是 20%；同一組裡只要掉一個（含 parity 本身），都能用 XOR 算回來，而且不需要等任何 RTT，延遲成本只有「等這一組到齊」的時間。但同一組掉兩個就無能為力，所以 FEC 怕的是**突發丟包**（burst loss，連續好幾個封包一起掉，Wi-Fi 干擾、手機切換基地台時很常見）。

WebRTC 裡的 FEC 有三種常見形式。**ULPFEC**（RFC 5109）是 RTP 的通用 FEC 格式，WebRTC 中通常包在 **RED**（RFC 2198，冗餘封裝）裡一起送，SDP 會出現 `red/90000` 與 `ulpfec/90000`。**FlexFEC**（RFC 8627）是較新的格式，可以用一維或二維（row 與 column）的方式組 parity，二維的組法能對付一定長度的突發丟包。音訊則用 **Opus in-band FEC**：Opus 編碼器可以在每個封包裡夾帶「前一個 frame 的低碼率版本」（稱為 LBRR），如果前一個封包掉了，接收端用下一個封包裡的備份解出一個品質較低但連續的聲音；SDP 的 `a=fmtp:111 minptime=10;useinbandfec=1` 就是宣告接收端能利用這種 FEC。它的效果取決於編碼器知道目前的丟包率（由 RTCP 回報），而且只能補「單一」遺失的封包。

| 機制 | 怎麼運作 | 額外成本 | 適合 | 不適合 |
|---|---|---|---|---|
| NACK＋RTX | 接收端回報缺號，送出端重送 | 只在丟包時付出，約等於丟包率 | RTT 短（遠小於播放期限）、影像 | RTT 長、大量丟包時重送也會掉 |
| PLI／FIR | 要求新的 keyframe | 一次 keyframe，可能引發突波 | 無法修復時重新開始、新加入者 | 頻繁使用（PLI storm） |
| ULPFEC／FlexFEC | 事先送 parity，接收端 XOR 回來 | 固定開銷（例如 20%） | RTT 長、隨機丟包 | 突發丟包（一維）、頻寬已不足時 |
| Opus in-band FEC | 每包夾帶前一 frame 的低碼率版本 | 音訊碼率增加一些 | 音訊的單一遺失 | 連續遺失 |
| Audio RED | 每包重複夾帶前幾個 frame | 音訊碼率倍增（音訊本身很小） | 對抗音訊的突發丟包 | 頻寬極度受限 |

實務上的組合是：影像以 NACK 為主，在 RTT 長或觀察到隨機丟包時加開 FEC；音訊開 Opus in-band FEC，必要時加 RED；PLI 作為最後手段並加以節流。SFU 讓這個組合更有效：它把一條長路徑切成兩段，每段都有自己的 NACK 迴圈，37.10 節的 cascading 會把這個想法推到跨國場景。

> [!note] 2026 現況
> 截至 2026 年 10 月，瀏覽器對 FlexFEC、audio RED 的預設啟用狀態依瀏覽器與版本而定（本書未逐一查證），要以實際的 SDP offer 與 getStats 的 `fecPacketsReceived` 等欄位確認。IETF 的 RFC 8888 定義了通用的擁塞控制回饋格式，但目前 WebRTC 部署中最常見的仍是 TWCC。

## 37.9 TURN：成本與部署

改走 SFU 之後，Joe 一度以為 TURN 可以拿掉了：SFU 有公網位址，client 對它直接連就好。但 37.2 節的需求表寫著「封鎖 UDP 的企業網路」，這些網路只允許經由 proxy 或只開 TCP 443 對外，對 SFU 的 UDP 40000 根本出不去。這時 client 需要 **TURN**（第 36 章）：一台公網上的中繼伺服器，client 用 TCP 或 TLS 連到它，再由它用 UDP 把封包轉給 SFU。聲聲 Live 的 TURN 在 `turn.shengsheng.example`（203.0.113.50），同時提供 UDP 3478、TCP 3478 與 TLS 443。

TURN 的成本結構和 SFU 不同。每一個 byte 都要「進來一次、出去一次」，所以 TURN 的網卡流量是被中繼流量的兩倍；如果 TURN 和 SFU 在不同地區，TURN 到 SFU 這一段也走 internet，雲端的出口流量費要付兩次。估算一次：尖峰時有 2,000 × 2＋300 × 6＝5,800 位參與者，假設其中 8% 需要 TURN（這是聲聲 Live 從自家 getStats 統計得出的假設值，不同服務差異很大），就是 464 人。一對一的參與者每人上下行合計約 3.08 Mbps，小班課約 4.56 Mbps，加權平均約 3.54 Mbps，所以經過 TURN 的媒體約 1.64 Gbps，TURN 的網卡要處理收送合計約 3.3 Gbps。

```text
                       internet（計費）                      VPC 內（不計出口費）
 企業網路的學生 ═══ TLS 443 ═══► turn 203.0.113.50 ═══ UDP ═══► sfu-tpe-1 10.20.1.15
   （只能出 443）                │  10.20.16.x（public-a）
                                │
   限制：denied-peer-ip 先拒絕所有目的地，allowed-peer-ip 只放行 SFU 節點

 對照：P2P 一對一經 TURN
 學生 ═══► TURN ═══► 老師        兩段都走 internet，出口費付兩次
```

這張圖是聲聲 Live 的部署選擇。TURN 與 SFU 放在同一個 VPC、同一個地區，client 到 TURN 這一段走 internet，TURN 到 SFU 這一段走 VPC 內部，只付一次出口費，也只多一跳極短的延遲。對照下半部的 P2P 一對一：兩端都在 internet 上，TURN 收進來、送出去都是 internet 流量，這是許多 P2P 服務 TURN 帳單偏高的原因。

TURN 的安全設定是 Rita 審查的重點。TURN 本質上是一個「幫任何持有帳密的人，把 UDP 封包轉送到任意位址」的服務；如果不加限制，攻擊者拿到一組帳密，就能請 TURN 把封包送到 VPC 內部的服務（例如 resolver 10.20.0.2 的 UDP 53）或雲端的 metadata 位址；若 TURN 還開了 TCP 中繼（RFC 6062），連資料庫 10.20.17.15:5432 都可能被觸及。這是一種 SSRF（server-side request forgery，讓伺服器替攻擊者連線到內部資源）。聲聲 Live 的 TURN 只服務 SFU，所以政策很簡單：只允許中繼到 SFU 的網段，其他一律拒絕。

```ini
# coturn 設定（示意；選項名稱依 coturn 版本確認，TLS 的 cert／pkey 路徑省略）
listening-port=3478
tls-listening-port=443
realm=shengsheng.example
# 短效帳密：即時服務與 TURN 共用金鑰，以 HMAC 簽出
use-auth-secret
static-auth-secret=<從 secrets manager 注入>
no-multicast-peers
# 先拒絕所有目的地（含 VPC 私有網段、loopback、metadata 位址與整個 internet）
denied-peer-ip=0.0.0.0-255.255.255.255
denied-peer-ip=::-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
# 再只放行 SFU 節點（6 台）；allowed 的範圍優先於 denied
allowed-peer-ip=10.20.1.15-10.20.1.20
```

帳密也不能寫死在前端。常見的做法是即時服務在使用者加入教室時，簽發一組短效帳密：username 是「到期的 unix 時間:使用者 ID」，password 是用 TURN 與即時服務共享的金鑰，對 username 做 HMAC-SHA1 再 base64。TURN 收到請求時用同一把金鑰重算比對，並檢查時間是否過期，不需要查資料庫。這個慣例來自一份 IETF individual draft（常稱為 TURN REST API），被 coturn 等實作採用：

```python
import base64
import hashlib
import hmac

SECRET = b"demo-turn-secret"        # 實際放在 secrets manager，即時服務與 TURN 共用


def issue(user_id, now, ttl=3600):
    username = f"{now + ttl}:{user_id}"
    password = base64.b64encode(hmac.new(SECRET, username.encode(), hashlib.sha1).digest()).decode()
    return username, password


def turn_accepts(username, password, now):
    expiry = int(username.split(":", 1)[0])
    expected = base64.b64encode(hmac.new(SECRET, username.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(expected, password) and now < expiry


now = 1_790_000_000
user, pw = issue("student-0457", now)
print("username:", user)
print("password:", pw)
print("一小時內：", turn_accepts(user, pw, now + 600))
print("過期後  ：", turn_accepts(user, pw, now + 3601))
print("改 ID   ：", turn_accepts(user.replace("0457", "0458"), pw, now))
assert turn_accepts(user, pw, now + 600) and not turn_accepts(user, pw, now + 3601)
```

```text
username: 1790003600:student-0457
password: QbG3YqEMPAuFWnIL9DiiMkL3KA8=
一小時內： True
過期後  ： False
改 ID   ： False
```

輸出的三行驗證說明了這個設計的性質。一小時內帳密有效；過期後即使 password 正確也被拒絕，所以前端外洩的帳密很快就沒用；把 username 裡的使用者 ID 改掉，HMAC 對不上，所以使用者無法冒用別人的身分或自行延長期限。用 `hmac.compare_digest` 比較是為了避免時間差洩漏（第 30 章）。這組帳密在 WebRTC 中以 `iceServers` 的 `username` 與 `credential` 傳給瀏覽器。

最後是 TURN 的延遲代價。TURN over TLS 443 把媒體塞進 TCP，TCP 的重傳與 head-of-line blocking（第 12 章）會讓一個遺失的封包卡住後面所有封包，延遲抖動明顯變大；它是「能用總比不能用好」的後備，不是預設路徑。ICE 會依 candidate 的優先順序先試 UDP，所以只有 UDP 真的不通時才會落到 TLS。

## 37.10 擴展：SFU 的水平擴展與 cascading

單台 SFU 的上限不只是頻寬。每個封包都要解密一次、對每位接收者加密一次並送出，所以真正的限制常常是**每秒封包數**（pps）與 CPU：一台送出 3 Gbps、平均封包 1,100 bytes 的 SFU，每秒要送出約 34 萬個封包。聲聲 Live 用壓測決定單台的安全上限，並把「收送頻寬、pps、CPU」三者合成一個負載分數，room 註冊表依分數選節點。

| 擴展問題 | 聲聲 Live 的做法 | 取捨 |
|---|---|---|
| 新教室放哪台 | 第一位參與者加入時，選負載分數最低的節點，寫入 room 註冊表 | 教室的人數會變，分配時要預留空間 |
| 同一間教室的人 | 一律導到同一台 | 單間教室不能超過單台容量 |
| 節點位址 | 每台有自己的公網 IP（sfu-tpe-1 是 203.0.113.60，之後的節點依序配發），由 signaling 告知 | 不能用 L4 LB 隱藏節點 |
| 部署新版本 | 節點標為 draining：不再接新教室，等現有課程結束（最長 50 分鐘）後才停機 | 部署變慢，需要多一台的餘裕 |
| 節點故障 | client 偵測 ICE 斷線後回報 signaling，被指派到新節點並重新 publish | 有數秒的中斷；目標 10 秒內恢復 |
| 跨地區學生 | edge SFU 就近接入，再 cascading 回教室所在的節點 | 多一跳，系統更複雜 |

這張表的前兩列說明 SFU 叢集的基本形狀：**一間教室在一台節點上**，叢集的容量來自「很多間教室分散在很多台」。這對小班課很自然，因為六個人的教室遠小於單台容量。故障恢復依賴「SFU 的狀態可以重建」：教室有哪些人、誰訂閱誰，都存在即時服務與註冊表裡，SFU 本身只有轉送的即時狀態；節點掛掉時，client 的 ICE 會在幾秒內進入 disconnected，signaling 把教室改指派到另一台，每位參與者重新做 offer／answer。這個過程中的影音中斷無法避免，但不需要使用者重新整理。

**Cascading**（級聯）是讓多台 SFU 合作服務同一間教室。動機有兩個：教室太大，單台撐不住；或參與者分散在不同地區，全部連到同一台會讓遠方的人吃到長 RTT。聲聲 Live 遇到的是第二種：美咲在日本授課、連到台北的 sfu-tpe-1（RTT 約 40 ms），班上有一位在美國東岸的學生，到台北 RTT 約 180 ms。37.8 節說過，180 ms 的 RTT 讓 NACK 幾乎無效。

```text
            台北區域                                          美東（edge）
 美咲 ══ RTT 40 ms ══► sfu-tpe-1 ════ SFU 間 relay ═════════► edge SFU ══ RTT 20 ms ══► 美東學生
 小安 ══ RTT 15 ms ══►     │         每路串流只跨洋一次          │
                           │         RTT 約 180 ms               │
                           │         （這一段可開 FEC）           │
                           ▼                                    ▼
             NACK 迴圈 ①：15–40 ms        NACK 迴圈 ②：SFU 之間     NACK 迴圈 ③：20 ms
```

這張圖把一條 180 ms 的長路徑切成三段。① 美咲到台北 SFU、③ edge SFU 到美東學生，都是 RTT 相對短（數十毫秒以內）的「最後一哩」，丟包最常發生在這裡（家用 Wi-Fi、行動網路），短 RTT 讓 NACK 很有效。② 兩台 SFU 之間是雲端骨幹或專線，丟包率低，可以穩定地加開 FEC，或依延遲預算允許少量重送。另一個好處是頻寬：如果有三位美東學生，每路串流只跨洋一次，再由 edge SFU 複製三份，而不是跨洋三次。代價是多一跳的處理延遲、跨節點的訂閱狀態要同步、故障情境變多；所以 cascading 只在跨地區或大型教室才啟用，一般的台灣小班課仍然是一間教室一台節點。

## 37.11 觀測：getStats 的關鍵指標

架構上線後，「卡不卡」要靠數據回答。瀏覽器的 `RTCPeerConnection.getStats()` 回傳一組統計物件，每個物件有 `type` 欄位；SFU 自己也會產出類似的統計。下面的程式片段每秒取一次，計算差值並送到後端（示意；欄位名稱依 W3C WebRTC Statistics 規格）：

```javascript
// 瀏覽器端（示意）：每秒取 getStats，累計型欄位要算差值才有意義
let prev = new Map();
setInterval(async () => {
  const report = await pc.getStats();
  report.forEach((s) => {
    if (s.type === "outbound-rtp" && s.kind === "video") {
      const p = prev.get(s.id);
      const kbps = p ? ((s.bytesSent - p.bytesSent) * 8) / (s.timestamp - p.timestamp) : 0;
      console.log(s.rid, kbps.toFixed(0), "kbps", s.frameWidth, "x", s.frameHeight,
                  s.framesPerSecond, "fps", s.qualityLimitationReason);
    }
  });
  prev = new Map([...report].map(([id, s]) => [id, s]));
}, 1000);
```

注意大部分欄位是**累計值**（從連線開始到現在的總數），例如 `bytesSent`、`packetsLost`、`nackCount`；要除以時間差才是速率，直接畫累計值只會看到一條往上的線。下表是聲聲 Live 監控面板上的指標，依「從哪個物件取、代表什麼、看到什麼值要警覺」整理：

| 物件 type | 欄位 | 意義 | 警訊 |
|---|---|---|---|
| `outbound-rtp` | `qualityLimitationReason`、`qualityLimitationDurations` | 送出畫質被什麼限制：`none`、`cpu`、`bandwidth`、`other` | 長時間 `cpu`：裝置撐不住；`bandwidth`：上行不足 |
| `outbound-rtp` | `rid`、`frameWidth`、`framesPerSecond`、`targetBitrate` | 每層實際送出的解析度、fps 與目標碼率 | h 層長期只有低 fps 或被停用 |
| `outbound-rtp` | `nackCount`、`pliCount`、`firCount`、`retransmittedBytesSent` | 收到的 NACK、keyframe 請求、重送量 | `pliCount` 每分鐘數十次：PLI storm |
| `inbound-rtp` | `packetsLost`、`jitter` | 遺失封包數、到達時間抖動（秒） | 遺失率持續高於幾個百分點 |
| `inbound-rtp` | `freezeCount`、`totalFreezesDuration`、`framesDropped` | 畫面凍結次數與總時長、丟棄的 frame | 使用者說「卡」最直接的指標 |
| `inbound-rtp` | `jitterBufferDelay` ÷ `jitterBufferEmittedCount` | 平均 jitter buffer 延遲 | 持續上升：網路抖動變大，延遲被拉長 |
| `inbound-rtp`（音訊） | `concealedSamples` ÷ `totalSamplesReceived` | 被「補出來」的音訊樣本比例 | 比例高：聲音斷續 |
| `inbound-rtp` | `fecPacketsReceived`、`fecPacketsDiscarded` | 收到與沒用上的 FEC 封包 | 收到很多卻幾乎都沒用上：FEC 開太多 |
| `remote-inbound-rtp` | `roundTripTime`、`fractionLost` | 對方（SFU）回報的 RTT 與丟包 | RTT 大於約 150 ms：NACK 開始失效 |
| `candidate-pair`（選中的那組） | `currentRoundTripTime`、`availableOutgoingBitrate` | ICE 量到的 RTT、頻寬估計值 | 估計值遠低於 simulcast 各層總和 |
| `local-candidate` | `candidateType`、`protocol`、`relayProtocol` | 走 host／srflx／relay，UDP 或 TCP／TLS | `relay`＋`tls`：延遲與抖動必然較大 |

回到故事那天晚上。美咲的 `qualityLimitationReason` 是 `cpu`，這是 mesh 讓五個 encoder 同時跑的直接證據；阿哲的是 `bandwidth`，五條 PeerConnection 的 `availableOutgoingBitrate` 各只有約 400 kbps，加起來剛好是 4G 上行的極限。換成 SFU 與 simulcast 後，美咲只編一個來源的三層，阿哲只上傳一份，兩個指標都回到 `none`。指標的解讀與完整的除錯流程，第 39 章會用一次真實的上課卡頓事件走一遍。

## 37.12 追問：設計討論會繼續問的事

設計文件送審時，阿德與 Rita 各提了幾個追問。這一節把它們和回答記下來，因為這些也是 system design 面試最常接著問的方向。

**「如果講座有 500 人互動呢？」** SFU 的出口頻寬隨 N(N−1) 成長，500 人每人都看全部是不可能的。正確的做法是改變需求的形狀：只有台上的少數人（講者、被點名發問的學生）是 publisher，其他人只是 subscriber；subscriber 數量很大時再分兩層，延遲要求高的少數人透過 cascading 的 SFU 收看，其他人改用直播的分發方式（第 38 章的 LL-HLS 或 WHEP），接受數秒的延遲換取 CDN 的規模。發問時再把該學生「升格」成 publisher。

**「SFU 看得到所有人的影像，能不能做端到端加密？」** 可以，做法是在瀏覽器的編碼之後、送出之前，再用只有參與者知道的金鑰加密一次影像資料（W3C 的 Encoded Transform 介面讓網頁能插入這一步），RTP header 與 SFU 需要的 extension 保持明文，SFU 照樣能選層與轉送。代價是金鑰要由應用自己分發與輪替，錄影與伺服器端的處理（例如字幕）就做不到了。聲聲 Live 的課程需要錄影，所以 Rita 的結論是：先確保 SFU 與錄製服務的存取控制與稽核，不做 E2EE。

**「signaling 斷了，媒體會斷嗎？」** 不會立刻斷。媒體在瀏覽器與 SFU 之間直接流動，signaling 只在加入、離開、換層協商、ICE restart 時才需要。這也是要把兩個平面分開的原因：`rt` 叢集部署新版本時，WebSocket 會重連（第 33 章），但正在上課的影音不受影響。

> [!note] 2026 現況
> 截至 2026 年 10 月，以 WebRTC 推流的 WHIP 已是 RFC 9725，觀看端的 WHEP 仍是 IETF draft（依 2026 年 10 月查證），兩者讓 SFU 也能直接當作直播的 ingest 與分發節點，第 38 章會詳細介紹。媒體層的端到端加密格式 SFrame 已由 IETF 發布為 RFC（編號與瀏覽器支援狀況請以當時的規格與實作為準）。開源 SFU 有 mediasoup、Janus、Jitsi Videobridge、LiveKit、Pion 等，功能範圍各不相同，選用前要對照自己的需求逐項驗證。

## 37.13 動手做：容量計算器、選層與丟包恢復模擬

設計文件裡的每個數字都應該能重算。這一節的三個實驗都只用標準函式庫、不碰網路，直接用 `python3` 執行：實驗一把 37.3 節的公式寫成計算器，實驗二模擬 SFU 依每位接收者的頻寬選 simulcast 層，實驗三比較 NACK 與 FEC 在不同丟包率與丟包型態下的恢復率。

### 實驗一：N 人教室的頻寬與連線數計算器

程式把三種拓撲寫成三個函式，各自回傳每人上下行、編解碼數、伺服器收送與連線數；接著用聲聲 Live 的真實版面算六人小班的下行，最後估算晚上八點尖峰的總頻寬與節點數。`cell()` 只是為了讓中文欄位在終端機裡對齊：中文字在等寬字型中佔兩格。

```python
import unicodedata
from dataclasses import dataclass

# 聲聲 Live 的編碼設定（kbps）：simulcast 三層與 Opus 音訊（含 RTP/SRTP 開銷的粗估）
LAYERS = {"h": 1500, "m": 500, "l": 150}   # 720p／360p／180p
AUDIO = 40


@dataclass
class Load:
    up: float          # 每人上行 kbps
    down: float        # 每人下行 kbps
    encodes: int       # 每人要同時跑幾個 video encoder
    decodes: int       # 每人要同時解幾路 video
    srv_in: float      # 伺服器總收 kbps
    srv_out: float     # 伺服器總送 kbps
    srv_codec: str     # 伺服器的轉碼工作
    links: int         # 媒體連線（PeerConnection）總數


def mesh(n):
    peers = n - 1
    per = LAYERS["h"] + AUDIO
    # 每條 PeerConnection 有自己的頻寬估計，所以瀏覽器替每個對象各編一次
    return Load(peers * per, peers * per, peers, peers, 0, 0, "無", n * (n - 1) // 2)


def sfu(n, simulcast=True, recv_kbps=None):
    up = (sum(LAYERS.values()) if simulcast else LAYERS["h"]) + AUDIO
    # 收端預設：每人收其他人的 h 層；可以傳入自訂的下行（例如依版面選層）
    down = recv_kbps if recv_kbps is not None else (n - 1) * (LAYERS["h"] + AUDIO)
    return Load(up, down, 3 if simulcast else 1, n - 1, n * up, n * down, "只轉送", n)


def mcu(n):
    per = LAYERS["h"] + AUDIO
    # 每人看到「除了自己以外」的合成畫面，所以 MCU 要為每個人各編一次
    return Load(per, per, 1, 1, n * per, n * per, f"解 {n} 路＋編 {n} 路", n)


def mbps(kbps):
    return f"{kbps / 1000:.2f}"


def cell(text, width):
    """中文字在等寬字型裡佔兩格，補空白時要算進去。"""
    used = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(text))
    return " " * (width - used) + str(text)


COLS = [("N", 3), ("拓撲", 6), ("每人上行", 10), ("每人下行", 10), ("編碼", 6), ("解碼", 6),
        ("伺服器收", 10), ("伺服器送", 10), ("連線", 6)]
print("頻寬單位：Mbps；「連線」是整間教室的媒體連線數")
print("".join(cell(name, w) for name, w in COLS) + "  伺服器轉碼")
for n in (2, 3, 6, 12):
    for name, ld in (("mesh", mesh(n)), ("SFU", sfu(n)), ("MCU", mcu(n))):
        row = [n, name, mbps(ld.up), mbps(ld.down), ld.encodes, ld.decodes,
               mbps(ld.srv_in), mbps(ld.srv_out), ld.links]
        print("".join(cell(v, w) for v, (_, w) in zip(row, COLS)) + "  " + ld.srv_codec)

# 六人小班課的實際版面：老師是大格（h），其他學生是小格（l）；老師看學生用 m
student_down = (LAYERS["h"] + AUDIO) + 4 * (LAYERS["l"] + AUDIO)
teacher_down = 5 * (LAYERS["m"] + AUDIO)
room = sfu(6, recv_kbps=0)
room.srv_out = 5 * student_down + teacher_down
print(f"\n六人小班（依版面選層）：學生下行 {mbps(student_down)} Mbps、老師下行 {mbps(teacher_down)} Mbps")
print(f"  每間教室：SFU 收 {mbps(room.srv_in)} Mbps、送 {mbps(room.srv_out)} Mbps")

# 晚上八點尖峰：2,000 間一對一（不開 simulcast）＋ 300 間六人小班
one = sfu(2, simulcast=False, recv_kbps=LAYERS["h"] + AUDIO)
peak_in = 2000 * one.srv_in + 300 * room.srv_in
peak_out = 2000 * one.srv_out + 300 * room.srv_out
print(f"尖峰總量：SFU 收 {peak_in / 1e6:.2f} Gbps、送 {peak_out / 1e6:.2f} Gbps")
node_cap = 3_000_000   # 假設：壓測得到的單節點安全上限 3 Gbps（收送取大者）
nodes = -(-max(peak_in, peak_out) // node_cap)
print(f"單節點上限 3 Gbps → 至少 {int(nodes)} 台，加上 N+1 與排空餘裕 → 規劃 {int(nodes) + 2} 台")

assert mesh(6).up == 5 * 1540 and mesh(6).links == 15
assert sfu(6).srv_out == 6 * 5 * 1540
assert mcu(12).down == mcu(2).down          # MCU 的下行與人數無關
```

```text
頻寬單位：Mbps；「連線」是整間教室的媒體連線數
  N  拓撲  每人上行  每人下行  編碼  解碼  伺服器收  伺服器送  連線  伺服器轉碼
  2  mesh      1.54      1.54     1     1      0.00      0.00     1  無
  2   SFU      2.19      1.54     3     1      4.38      3.08     2  只轉送
  2   MCU      1.54      1.54     1     1      3.08      3.08     2  解 2 路＋編 2 路
  3  mesh      3.08      3.08     2     2      0.00      0.00     3  無
  3   SFU      2.19      3.08     3     2      6.57      9.24     3  只轉送
  3   MCU      1.54      1.54     1     1      4.62      4.62     3  解 3 路＋編 3 路
  6  mesh      7.70      7.70     5     5      0.00      0.00    15  無
  6   SFU      2.19      7.70     3     5     13.14     46.20     6  只轉送
  6   MCU      1.54      1.54     1     1      9.24      9.24     6  解 6 路＋編 6 路
 12  mesh     16.94     16.94    11    11      0.00      0.00    66  無
 12   SFU      2.19     16.94     3    11     26.28    203.28    12  只轉送
 12   MCU      1.54      1.54     1     1     18.48     18.48    12  解 12 路＋編 12 路

六人小班（依版面選層）：學生下行 2.30 Mbps、老師下行 2.70 Mbps
  每間教室：SFU 收 13.14 Mbps、送 14.20 Mbps
尖峰總量：SFU 收 10.10 Gbps、送 10.42 Gbps
單節點上限 3 Gbps → 至少 4 台，加上 N+1 與排空餘裕 → 規劃 6 台
```

先看上半部的表。Mesh 的每人上行與下行都隨 N 線性成長，連線數則是 1、3、15、66，以 N(N−1)/2 成長；N＝6 時的 7.70 Mbps 上行與 5 個 encoder，就是故事裡阿哲與美咲各自卡住的地方。SFU 的每人上行固定在 2.19 Mbps，不論 2 人還是 12 人；它的「編碼 3」代表 simulcast 的三層各編一次，但低層的解析度只有 1/2 與 1/4，CPU 成本遠低於 mesh 的 5 個 720p encoder。SFU 這一列的下行與伺服器送出是「每個人都收全部人的 720p」的最壞情況：12 人時伺服器要送 203 Mbps，是收進來的近 8 倍，這就是 N(N−1) 的威力。MCU 的每人上下行永遠是 1.54 Mbps，但伺服器轉碼工作隨 N 線性成長，而且每一路都是即時解碼與編碼。

N＝2 那一列有個值得注意的細節：SFU 的上行 2.19 Mbps 比 mesh 的 1.54 Mbps 還高，因為計算器預設開 simulcast。一對一的教室只有一位接收者，SFU 不需要選層，所以聲聲 Live 的一對一不開 simulcast，尖峰估算裡的 `one` 也是用 `simulcast=False` 算的。這提醒我們：simulcast 是用上行頻寬與送出端 CPU 換取「接收端的多樣性」，接收端只有一個時就是純浪費。

下半部是依版面計算的結果。學生收老師的 h 層加四位同學的 l 層，共 2.30 Mbps；老師收五位學生的 m 層，共 2.70 Mbps；每間教室 SFU 送 14.20 Mbps，只有「全收 720p」的 46.20 Mbps 的三成。尖峰總量約收 10.10 Gbps、送 10.42 Gbps，以單台 3 Gbps 的假設上限，至少要 4 台，加上故障餘裕與排空用的節點，規劃 6 台。這個數字的不確定性主要來自兩個假設：單台上限要靠壓測，選層後的實際下行要看真實的版面與網路分布。

### 實驗二：SFU 依每位接收者的頻寬選 simulcast 層

這個實驗模擬小班課裡的三位學生在 10 秒內收看老師的影像。每位學生每秒有一個頻寬估計值（實務上來自 SFU 對這位學生的 TWCC 估計）：小安在家用光纖上穩定 6 Mbps，阿哲在高鐵上從 2.4 Mbps 掉到 450 kbps 再回升，小芸的宿舍 Wi-Fi 中途掉到 1.1 Mbps。SFU 依 37.6 節的規則分配：只用估計值的 90%，先給五路音訊，再給每路影像最低層，最後依優先順序（老師優先）往上升；降層立刻發起，升層要連續兩秒都夠；切換一律要等目標層的 keyframe，同一秒、同一層的 PLI 只送一次。

```python
LAYERS = {"l": 150, "m": 500, "h": 1500}   # 每個 publisher 的 simulcast 三層（kbps）
ORDER = ["off", "l", "m", "h"]
AUDIO = 40
HEADROOM = 0.9      # 只用估計值的 90%，留給 RTX 與估計誤差
UP_HOLD = 2         # 預算連續 2 秒足夠才升層（hysteresis，避免來回跳）

# 每位接收者想看的版面：老師是大格（最多 h），其他四位同學是小格（最多 l）
WANT = [("teacher", "h")] + [(f"s{i}", "l") for i in range(1, 5)]

# 每秒的頻寬估計（kbps），來自 SFU 對每位接收者的 TWCC 頻寬估計
BWE = {
    "小安": [6000] * 10,                                             # 家用光纖
    "阿哲": [2400, 2300, 900, 600, 450, 700, 1300, 2200, 2400, 2400],  # 高鐵上的 4G
    "小芸": [1900, 1900, 1800, 1100, 1100, 1900, 1900, 1900, 1900, 1900],  # 宿舍 Wi-Fi
}


def allocate(budget):
    """依優先順序分配：先音訊，再每路影像的最低層，最後把老師、同學往上升。"""
    budget -= AUDIO * len(WANT)
    plan = {name: "off" for name, _ in WANT}
    for name, _ in WANT:                         # 第一輪：每路先給 l
        if budget >= LAYERS["l"]:
            plan[name], budget = "l", budget - LAYERS["l"]
    for name, cap in WANT:                       # 第二輪：依優先順序往上升到想要的層
        for layer in ORDER[ORDER.index(plan[name]) + 1: ORDER.index(cap) + 1]:
            extra = LAYERS[layer] - LAYERS.get(plan[name], 0)
            if plan[name] == "off" or extra > budget:
                break
            plan[name], budget = layer, budget - extra
    return plan


class Receiver:
    def __init__(self, name):
        self.name, self.current, self.ok_ticks, self.pending = name, None, 0, None

    def tick(self, bwe, pli_sent):
        want = allocate(bwe * HEADROOM)["teacher"]
        events = []
        if self.pending:                         # 上一秒要的 keyframe 到了，正式切換
            self.current, self.pending = self.pending, None
            events.append(f"切到 {self.current}")
        cur = self.current or "off"
        if self.current is None:
            self.pending = want
        elif ORDER.index(want) < ORDER.index(cur):
            self.pending, self.ok_ticks = want, 0          # 降層：馬上要 keyframe
        elif ORDER.index(want) > ORDER.index(cur):
            self.ok_ticks += 1
            if self.ok_ticks >= UP_HOLD:                   # 升層：要穩定一段時間
                self.pending, self.ok_ticks = want, 0
        else:
            self.ok_ticks = 0
        if self.pending and self.pending != "off":
            key = ("teacher", self.pending)
            if key in pli_sent:
                events.append(f"等 {self.pending} 的 keyframe（PLI 已合併）")
            else:
                pli_sent.add(key)
                events.append(f"送 PLI 要 {self.pending}")
        return self.current or "-", events


receivers = [Receiver(n) for n in BWE]
pli_total = 0
print(" t  " + "".join(f"{r.name:<9}" for r in receivers) + "事件")
for t in range(10):
    pli_sent = set()                             # 同一秒內，同一層的 PLI 只送一次
    cells, notes = [], []
    for r in receivers:
        layer, ev = r.tick(BWE[r.name][t], pli_sent)
        cells.append(f"{BWE[r.name][t]:>4}→{layer:<4}")
        notes += [f"{r.name}{e}" for e in ev]
    pli_total += len(pli_sent)
    print(f"{t:>2}   " + " ".join(cells) + "；".join(notes))

print(f"\n10 秒內送給老師的 PLI：{pli_total} 次")
print("阿哲在 450 kbps 時的完整分配：", allocate(450 * HEADROOM))

# 對照組：沒有 simulcast，SFU 把所有人的頻寬估計取最小值回報給老師（舊式 REMB 轉送）
worst = [min(BWE[n][t] for n in BWE) * HEADROOM - AUDIO * 5 for t in range(10)]
best = [max(BWE[n][t] for n in BWE) * HEADROOM - AUDIO * 5 for t in range(10)]
print("沒有 simulcast：老師只能用", [int(w) for w in worst], "kbps 編碼")
print(f"光纖的小安平均只用到自己預算的 {sum(worst) / sum(best):.0%}")
assert allocate(6000 * HEADROOM)["teacher"] == "h"
assert allocate(450 * HEADROOM)["teacher"] == "l"
```

```text
 t  小安       阿哲       小芸       事件
 0   6000→-    2400→-    1900→-   小安送 PLI 要 h；阿哲送 PLI 要 m；小芸等 m 的 keyframe（PLI 已合併）
 1   6000→h    2300→m    1900→m   小安切到 h；阿哲切到 m；小芸切到 m
 2   6000→h     900→m    1800→m   阿哲送 PLI 要 l
 3   6000→h     600→l    1100→m   阿哲切到 l；小芸送 PLI 要 l
 4   6000→h     450→l    1100→l   小芸切到 l
 5   6000→h     700→l    1900→l   
 6   6000→h    1300→l    1900→l   小芸送 PLI 要 m
 7   6000→h    2200→l    1900→m   小芸切到 m
 8   6000→h    2400→l    1900→m   阿哲送 PLI 要 m
 9   6000→h    2400→m    1900→m   阿哲切到 m

10 秒內送給老師的 PLI：6 次
阿哲在 450 kbps 時的完整分配： {'teacher': 'l', 's1': 'off', 's2': 'off', 's3': 'off', 's4': 'off'}
沒有 simulcast：老師只能用 [1510, 1510, 610, 340, 205, 430, 970, 1510, 1510, 1510] kbps 編碼
光纖的小安平均只用到自己預算的 19%
```

逐秒讀這張表，箭頭左邊是頻寬估計（kbps），右邊是這一秒實際轉送的老師畫質。第 0 秒三人剛加入，還沒有任何畫面（`-`）；SFU 依頻寬決定小安要 h、阿哲與小芸要 m，向老師送兩個 PLI。注意小芸那一格：阿哲已經在這一秒要過 m 層的 keyframe，SFU 把小芸的請求合併，老師只需要產生一個 m 層 keyframe。第 1 秒 keyframe 到了，三人各自切到自己的層。這就是 simulcast 加 SFU 的核心價值：同一份上傳，三個人看到三種畫質，彼此不影響。

第 2 秒阿哲的頻寬掉到 900 kbps，SFU 立刻送 PLI 要 l 層，但切換要等 keyframe，所以這一秒仍在送 m 層；真實的 SFU 會在等待期間先丟掉 m 層裡的 temporal 上層（37.6 節），讓 frame rate 降低、碼率先降下來。第 3 秒阿哲切到 l；同一秒小芸的頻寬掉到 1,100 kbps，也要求降到 l。第 4 秒阿哲的頻寬只剩 450 kbps，程式最後一行印出這時的完整分配：老師的 l 層保住了，四位同學的小格全部 `off`，只剩音訊。這是刻意的優先順序：語言課可以看不到同學，但不能看不到老師、更不能聽不到聲音。

第 5 秒起頻寬回升，但升層有遲滯。小芸在第 5 秒回到 1,900 kbps，第 6 秒才確認「連續兩秒夠」並送 PLI，第 7 秒切到 m；阿哲在第 7、8 秒都有 2,200 kbps 以上，第 8 秒送 PLI，第 9 秒才回到 m。遲滯讓升層慢了一兩秒，但換來的是穩定：如果每次頻寬一回升就升層，阿哲在第 5 到 6 秒之間可能會升上去又掉下來，每次來回都要一個 keyframe。10 秒內老師總共收到 6 個 PLI，在可接受的範圍內。

最後兩行是對照組：如果不開 simulcast，老師只能編一路，SFU 只好取所有接收者中最差的頻寬（舊式做法是把最小的 REMB 轉給送出端），老師的碼率跟著當下最差的接收者在 205 到 1,510 kbps 之間上下跳，光纖上的小安平均只用到自己可用頻寬的 19%。一個人的網路差，全班的畫質跟著差，這正是 simulcast 要解決的問題。

### 實驗三：NACK 與 FEC 在不同丟包率下的恢復率

最後一個實驗量化 37.8 節的取捨。程式產生 30,000 個媒體封包（約 1.5 Mbps、每 6.4 ms 一個），套用兩種丟包模型：**隨機**丟包，每個封包獨立以機率 p 遺失；**突發**丟包，用 Gilbert-Elliott 模型（在「好」與「壞」兩個狀態之間切換，壞狀態時封包都會掉），平均一次連續掉 4 個，長期丟包率同樣是 p。每個封包要在送出後 120 ms 內抵達才有用。NACK 的模型是：收到下一個有到的封包才發現缺號，重送要一個 RTT 才回來，重送本身也可能遺失，期限內可以再試；FEC 是每 5 個媒體封包加 1 個 XOR parity。

```python
import random
import unicodedata

N_PACKETS = 30_000
INTERVAL = 6.4        # ms；1.5 Mbps、每包約 1,200 bytes ≈ 每秒 156 包
DEADLINE = 120        # ms；封包送出後要在這段時間內到，否則 jitter buffer 已經放棄它
FEC_GROUP = 5         # 每 5 個媒體封包加 1 個 XOR parity（20% 額外頻寬）


def loss_pattern(n, p, burst, rng):
    """burst=1：獨立隨機丟包；burst>1：Gilbert-Elliott 兩態模型，平均連續丟 burst 個。"""
    if burst == 1:
        return [rng.random() < p for _ in range(n)]
    leave_bad = 1 / burst                         # 在「壞」狀態平均待 burst 個封包
    enter_bad = p * leave_bad / (1 - p)           # 讓長期平均丟包率等於 p
    lost, bad = [], False
    for _ in range(n):
        bad = (rng.random() >= leave_bad) if bad else (rng.random() < enter_bad)
        lost.append(bad)
    return lost


def fec_recover(lost):
    """每組 5 個媒體封包＋1 個 parity；整組（含 parity）只掉一個時可以 XOR 回來。"""
    recovered = list(lost)
    step = FEC_GROUP + 1
    for g in range(0, len(lost) - step + 1, step):
        group = lost[g:g + step]
        if sum(group) == 1:
            recovered[g:g + step] = [False] * step
    # 只回傳媒體封包（每組最後一個是 parity）
    return [x for i, x in enumerate(recovered) if i % step != FEC_GROUP]


def nack_recover(lost, rtt, p, rng):
    """收到下一個封包才發現缺號，送 NACK；重送要 RTT 才回來，也可能再掉一次。"""
    still, sent = list(lost), 0
    for i, gone in enumerate(lost):
        if not gone:
            continue
        j = i + 1
        while j < len(lost) and lost[j]:          # 連續丟包時，要等到下一個「有到」的封包
            j += 1
        detect = (j - i) * INTERVAL               # 從原封包應到時間算起
        t = detect + rtt
        while t <= DEADLINE:
            sent += 1
            if rng.random() >= p:                 # 重送的封包也可能遺失
                still[i] = False
                break
            t += rtt                              # 沒等到就再 NACK 一次
    return still, sent


def media_of(lost):
    step = FEC_GROUP + 1
    return [x for i, x in enumerate(lost) if i % step != FEC_GROUP]


def rate(before, after):
    return 1 - sum(after) / sum(before) if sum(before) else 1.0


def cell(text, width):
    """中文字在等寬字型裡佔兩格，補空白時要算進去。"""
    used = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    return " " * (width - used) + text


COLS = [("丟包模型", 10), ("原始丟包", 10), ("NACK@40", 9), ("重送量", 8),
        ("NACK@180", 10), ("FEC", 8), ("FEC+NACK", 10)]
print("".join(cell(name, w) for name, w in COLS))
for burst, label in ((1, "隨機"), (4, "突發4")):
    for p in (0.01, 0.03, 0.05, 0.10, 0.20):
        rng = random.Random(37)
        # 同一條線上的丟包序列同時套用各種策略；FEC 的序列多了 parity 的位置
        wire = loss_pattern(N_PACKETS // FEC_GROUP * (FEC_GROUP + 1), p, burst, rng)
        media = media_of(wire)
        left40, sent40 = nack_recover(media, 40, p, rng)
        left180, _ = nack_recover(media, 180, p, rng)
        fec = fec_recover(wire)
        both, _ = nack_recover(fec, 40, p, rng)
        row = [label, f"{sum(media) / len(media):.2%}", f"{rate(media, left40):.1%}",
               f"{sent40 / len(media):.1%}", f"{rate(media, left180):.1%}",
               f"{rate(media, fec):.1%}", f"{rate(media, both):.1%}"]
        print("".join(cell(v, w) for v, (_, w) in zip(row, COLS)))
print("（NACK@40 等欄位是恢復率；重送量是重送封包數占媒體封包數的比例；FEC 固定多 20%）")

# 健全性：RTT 大於期限時，NACK 完全救不回來
rng = random.Random(1)
sample = loss_pattern(10_000, 0.05, 1, rng)
assert nack_recover(sample, 180, 0.05, rng) == (sample, 0)
assert sum(fec_recover([False] * 6)) == 0 and sum(fec_recover([True, True] + [False] * 4)) == 2
```

```text
  丟包模型  原始丟包  NACK@40  重送量  NACK@180     FEC  FEC+NACK
      隨機     1.03%   100.0%    1.0%      0.0%   93.5%    100.0%
      隨機     2.92%   100.0%    3.0%      0.0%   86.2%    100.0%
      隨機     4.87%    99.8%    5.1%      0.0%   78.2%    100.0%
      隨機     9.77%    99.1%   10.8%      0.0%   60.1%     99.7%
      隨機    19.69%    96.2%   23.6%      0.0%   33.3%     96.8%
     突發4     1.05%   100.0%    1.1%      0.0%    9.2%    100.0%
     突發4     2.94%    98.1%    3.0%      0.0%   10.1%     97.4%
     突發4     5.04%    96.8%    5.1%      0.0%    9.7%     97.0%
     突發4     9.57%    96.7%   10.4%      0.0%    9.5%     96.3%
     突發4    18.95%    93.0%   22.0%      0.0%    8.7%     92.6%
（NACK@40 等欄位是恢復率；重送量是重送封包數占媒體封包數的比例；FEC 固定多 20%）
```

先看隨機丟包的上半部。RTT 40 ms 時，NACK 在 1% 到 10% 的丟包率下都能恢復 99% 以上，重送量大約等於丟包率，也就是「掉多少補多少」，很省頻寬；到 20% 時恢復率仍有 96%，但重送量升到 23.6%，因為重送本身也會掉。RTT 180 ms 那一欄全部是 0：發現缺號加上一個 RTT 已經超過 120 ms 的期限，重送永遠遲到，這就是美東學生直連台北 SFU 時的處境，再怎麼 NACK 都沒用。FEC 不依賴 RTT，1% 時能恢復 93.5%，但恢復率隨丟包率快速下降：5% 時 78%，20% 時只剩 33%，因為同一組 6 個封包裡掉兩個以上的機率越來越高。

突發丟包的下半部讓 FEC 現出原形。同樣 1% 的平均丟包率，FEC 只恢復 9.2%：封包總是幾個一起掉，同一組裡掉兩個以上是常態，一維 XOR 救不回來，20% 的額外頻寬幾乎白花。NACK 在突發丟包下仍然有效（RTT 40 ms 時 93% 到 100%），只是發現缺號要等到突發結束，恢復率比隨機時略低。最右欄的 FEC＋NACK 在隨機丟包時把殘餘的少數遺失也補上，在突發丟包時與單用 NACK 相差在統計誤差內，因為 FEC 幾乎沒有貢獻。

這張表的工作結論是三句話。第一，RTT 短的路徑用 NACK，便宜又有效。第二，RTT 長、無法重送的路徑，FEC 是唯一的工具，但只對隨機丟包有效；突發丟包要用二維的 FlexFEC 或交錯（interleaving），或從架構上縮短 RTT。第三，最好的解法往往是架構而不是參數：用 37.10 節的 edge SFU 把美東學生的最後一哩縮短到 20 ms，NACK 就重新有效。

## 37.14 在工作上怎麼用

設計通過後，小晴和 Joe 把落地需要的檢查整理成各角色的清單。

**後端工程師：signaling 與 room 指派是你的服務。** 即時服務要處理三件事：加入教室時查或建立 room → SFU 的對應（建立要是原子操作，否則兩個人同時加入可能被分到兩台）；把 SFU 的 SDP answer 與 TURN 短效帳密回給瀏覽器；SFU 節點故障或 draining 時，主動通知教室裡的每個人重新連線到新節點。room 註冊表的項目要有 TTL，由 SFU 定期續約，節點掛掉後項目自然過期。這些都不碰媒體，但寫錯了，教室就會被拆成兩半，一半的人看不到另一半。

**影音工程師：上線前用數字驗證每一層。** Joe 的檢查清單如下：

```bash
# 1. 確認 offer 裡有 simulcast 與需要的回饋機制（在瀏覽器 console 印出 localDescription.sdp 後檢查）
grep -E 'a=(rid|simulcast|rtcp-fb|extmap|fmtp:111)' offer.sdp
# 2. 確認 SFU 節點的 UDP port 對外可達（從外部測試機）
nc -vzu 203.0.113.60 40000          # UDP 只能確認「沒有被立即拒絕」，最終以 ICE 是否成功為準
# 3. 確認 TURN 的三種入口都可用（TLS 443 是企業網路學生的生命線）
openssl s_client -connect turn.shengsheng.example:443 -servername turn.shengsheng.example </dev/null | head -5
# 4. 在 SFU 上看單一教室的轉送狀況（示意：依 SFU 軟體的管理介面而定）
curl -s http://10.20.1.15:7070/rooms/8812/stats | python3 -m json.tool | head -40
```

第 1 行確認 SDP 的協商結果，少了 `a=simulcast` 或 `transport-cc`，後面的選層與頻寬估計就不會運作。第 2 行提醒 UDP 檢查的局限（第 3 章）。第 3 行確認 TURN 的 TLS 憑證有效，憑證過期會讓所有企業網路的學生同時斷線（第 19 章）。第 4 行的管理介面因 SFU 軟體而不同，重點是能看到每位接收者目前收哪一層、估計頻寬多少、PLI 次數多少。

**SRE：容量與排空。** SFU 的容量告警要看三個量：出口頻寬、pps、CPU，任何一個超過壓測上限的 70% 就該擴容；新節點加入後，room 指派才會把新教室分過去，舊教室不會自動搬移。部署採 draining：先把節點標為不接新教室，等現有教室自然結束（聲聲 Live 的課最長 50 分鐘）再更新，所以一次滾動部署至少要一節課的時間。TURN 要監控同時 allocation 數、中繼頻寬與認證失敗率，認證失敗突增常常是時鐘不同步（短效帳密依賴時間）或金鑰輪替沒有同步。

**前端工程師：把 getStats 送回來。** 每 5 到 10 秒把 37.11 節表格裡的關鍵欄位彙整後送到後端，至少包含選中的 candidate 類型、RTT、各層的送出碼率與 `qualityLimitationReason`、收到的 `freezeCount` 與遺失率。客服收到「卡」的回報時，工程師能直接查那堂課那位學生的時間序列，而不是請使用者重現。版面改變時（學生把老師的畫面縮小、切到分享螢幕）要通知 SFU 新的期望解析度，否則 SFU 會繼續送用不到的 720p。

**資安工程師：審查媒體平面的暴露面。** Rita 的清單：SFU 只開 UDP 40000 與必要的 TCP 後備，管理介面只在 VPC 內；TURN 的 `allowed-peer-ip` 只包含 SFU 網段、短效帳密的 TTL 不超過一小時、共享金鑰放在 secrets manager 並定期輪替；signaling 驗證 JWT（第 27 章，audience 是 `rt.shengsheng.example`）後才簽發 TURN 帳密與指派 SFU；錄製服務的存取要有稽核紀錄，因為它看得到所有課程內容。

## 37.15 常見錯誤與除錯

下表收錄從 P2P 走向 SFU 的過程中最常見的問題。每一列的「怎麼確認」都可以用 getStats、SFU 的統計或本章的工具在幾分鐘內完成。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 小班課一人網路差，全班畫質一起下降 | 沒開 simulcast，或 SFU 把接收端的頻寬回饋取最小值轉給送出端 | 送出端 `outbound-rtp` 只有一個 rid；碼率跟著最差的接收者起伏 | 開 simulcast（或 SVC），SFU 終結頻寬回饋、依每位接收者選層 |
| 有人加入或換層時全班畫面卡一下 | PLI storm：每個請求都轉給送出端，keyframe 造成上行突波 | 送出端 `pliCount`、`keyFramesEncoded` 在加入事件時跳升 | SFU 合併同層 PLI 並限速；新加入者先給低層 |
| 老師說筆電很燙、送出只有 10 fps 左右 | 編碼負擔過重：mesh 多路編碼、或最高層解析度太高 | `qualityLimitationReason` 為 `cpu`，`qualityLimitationDurations.cpu` 持續增加 | 改用 SFU；降低最高層解析度或 fps；確認有用到硬體編碼器 |
| 畫質在兩層之間每幾秒來回跳 | 升層沒有遲滯，或沒先探測就升層 | SFU log 的換層事件頻繁、每次都伴隨 PLI；接收端 `freezeCount` 增加 | 升層要求頻寬連續數秒足夠，升層前先 probing |
| 遠方學生丟包率只有 3%，畫面卻常馬賽克或凍結 | RTT 太長，NACK 重送趕不上播放期限 | `remote-inbound-rtp` 的 RTT 約 180 ms；`nackCount` 高但 `freezeCount` 也高 | 就近的 edge SFU 加 cascading；長路徑開 FEC；評估調整 jitter buffer 目標 |
| 聲音斷斷續續，影像正常 | 音訊沒有 NACK，也沒開 Opus in-band FEC 或 RED | `concealedSamples` 比例高；SDP 缺 `useinbandfec=1` | 啟用 Opus FEC、必要時 RED；檢查 Wi-Fi 是否有突發丟包 |
| 企業網路的學生完全連不上視訊 | UDP 被封鎖，又沒有 TURN over TLS 443 | ICE 狀態 `failed`；candidate-pair 全部失敗，沒有 relay candidate | 提供 TURN TLS 443（憑證要自動更新），或 SFU 提供 ICE-TCP |
| TURN 流量費用暴增 | 強制所有人 relay，或 TURN 與 SFU 不在同一地區 | 統計選中 candidate 的 `candidateType` 為 relay 的比例；看 TURN 到 SFU 的流量是否走 internet | 只在必要時 relay；TURN 與 SFU 同區部署並走內部網路 |
| 部署 SFU 新版本時，正在上課的教室全部斷線 | 直接重啟節點，沒有 draining | 斷線時間與部署時間吻合；client 端 ICE 同時 `disconnected` | 節點先 draining，等教室結束再更新；故障時讓 client 自動遷移 |

除錯時的通則是先分段，再分層。先分段：問題出在「publisher 到 SFU」還是「SFU 到 subscriber」？送出端的 `qualityLimitationReason` 與接收端的 `freezeCount` 會告訴你是哪一段。再分層：是頻寬不夠（BWE 低）、丟包恢復失敗（NACK 多、凍結多）、keyframe 問題（PLI 多），還是裝置撐不住（CPU）？每一種都有不同的負責人與不同的修法。

## 37.16 動手練習

1. **延伸實驗一：加上螢幕分享。** 小班課的老師分享螢幕時，多送一路 1080p、5 fps 的畫面，碼率 1,000 kbps，不開 simulcast，所有學生都要收。修改計算器，算出分享時每位學生的下行、每間教室 SFU 的送出量，以及尖峰（假設三成小班課同時在分享）時是否仍在 6 台的容量內。
   答案要點：每位學生下行增加 1 Mbps 到約 3.3 Mbps，每間教室 SFU 多收 1 Mbps、多送 5 Mbps；90 間教室同時分享時尖峰送出增加約 0.45 Gbps，仍在容量內，但要注意螢幕畫面在切換投影片時的 keyframe 突波。

2. **延伸實驗二：先丟 temporal 層再換 spatial 層。** 修改 `Receiver.tick()`，在等待降層 keyframe 的那一秒，先把目前這層的碼率降為原本的 60%（模擬丟掉 T2 層），並統計 10 秒內「實際送出碼率超過頻寬估計」的秒數，比較修改前後。
   答案要點：沒有 temporal 降速時，阿哲在第 2 秒以 m 層 500 kbps 加上同學的小格，超出 900 kbps 估計值的 90%；加上 temporal 降速後超出量明顯變小。這說明 temporal 分層是 SFU 在 keyframe 到來前的「止血」手段。

3. **延伸實驗三：找出 FEC 的臨界點。** 把 `FEC_GROUP` 改成 10（10% 開銷）與 2（50% 開銷），並把 RTT 改成 100 ms，觀察在隨機丟包下，FEC 與 NACK 誰的恢復率較高；再把突發長度改成 2，看一維 FEC 是否還有用。
   答案要點：RTT 100 ms 時，發現缺號加一個 RTT 仍在 120 ms 期限內，但只夠試一次，NACK 的恢復率約等於（1 − p）；FEC 的組越小越能扛高丟包率，但開銷越高。突發長度 2 時一維 FEC 的效果介於隨機與突發 4 之間。

4. **用 `chrome://webrtc-internals` 觀察真實的 simulcast**（真實工具）。在聲聲 Live 的 staging 教室（或任何支援 simulcast 的 WebRTC 視訊頁面）開一場三人通話，打開 `chrome://webrtc-internals`，找到 `outbound-rtp` 的三個 rid，記錄各層的 `frameWidth`、`framesPerSecond`、送出碼率；接著用作業系統或 DevTools 的網路節流把上行限制到 1 Mbps，觀察哪一層先被停用、`qualityLimitationReason` 怎麼變。
   答案要點：上行受限時，送出端的頻寬估計下降，最高層通常最先被降速或停用，`qualityLimitationReason` 變成 `bandwidth`；接收端如果原本收 h 層，SFU 會把它切到較低的層，接收端的 `frameWidth` 跟著改變。

5. **手算：十人小班可行嗎？** 產品想把小班課擴大到一位老師加九位學生，版面不變（老師大格 h、同學小格 l；老師看學生 m）。手算每位學生與老師的下行、每間教室 SFU 的收送，並判斷老師端的下行是否會成為問題。
   答案要點：學生下行＝1.54＋8 × 0.19＝3.06 Mbps；老師下行＝9 × 0.54＝4.86 Mbps；SFU 收 10 × 2.19＝21.9 Mbps、送 9 × 3.06＋4.86＝32.4 Mbps。老師下行接近 5 Mbps，在家用網路尚可，但老師同時還要上傳 2.19 Mbps；可以考慮讓老師看學生用 l 層、只在學生發言時升到 m。

## 本章重點整理

- Mesh 讓每個人送 N−1 份、收 N−1 份，連線數以 N(N−1)/2 成長；它在兩三人時最省、延遲最低，六人以上就被使用者的上行頻寬與編碼 CPU 擋住。
- SFU 只轉送不解碼，每人上行與人數無關，複製工作搬到資料中心；伺服器出口最多是 N(N−1) 份串流，但成本主要是加解密與封包處理，容易水平擴展，是多人視訊的主流。
- MCU 解碼、合成再編碼，每人只收一路，適合弱裝置、電話撥入與合成錄影；伺服器轉碼成本最高、延遲最大，現代架構通常只把它用在即時路徑之外。
- SFU 終結 DTLS-SRTP 與 RTCP：自己服務 NACK、對每段連線獨立估計頻寬、合併並節流 PLI，並改寫 SSRC、序號與 timestamp，讓換層對接收端看起來是一條連續的串流。
- Simulcast 是送出端編出多路獨立串流，對接收端透明、相容性最好；SVC 是一路分層串流，上行較省，temporal 層可以直接丟棄，但需要 codec 與 SFU 支援分層。
- SFU 依版面與頻寬替每位接收者選層：先保音訊、再保每路最低層、依優先順序升層；升層要遲滯與探測，simulcast 的換層要等目標層的 keyframe。
- GCC 用「到達間隔減送出間隔」的趨勢偵測佇列變長，在丟包前就把碼率降到收到速率的 0.85 倍；丟包型控制器在丟包率超過 10% 時降速、低於 2% 時加速。
- REMB 由接收端估計後回報一個碼率；TWCC 讓接收端回報每個封包的到達時間、由送出端估計，演算法升級只需改送出端，是目前主流。
- NACK＋RTX 只在丟包時付出成本，但必須在「發現缺號＋一個 RTT」內趕上播放期限；RTT 長時 NACK 失效。
- FEC 用固定開銷換取不依賴 RTT 的恢復，對隨機丟包有效、對突發丟包效果很差；音訊用 Opus in-band FEC 或 RED 補單一或少量遺失。
- PLI／FIR 請求 keyframe 是最後手段，keyframe 很大，不加節流的 PLI 會在多人教室引發 PLI storm。
- TURN 的流量要進出各一次，與 SFU 同區部署可以只付一次出口費；TURN 必須用短效帳密，並限制只能中繼到允許的位址，避免成為 SSRF 跳板。
- SFU 叢集以「一間教室一台節點」為基本單位，每台有自己的公網位址、由 signaling 指派；部署靠 draining，故障靠 client 重連與狀態重建；跨地區用 edge SFU 與 cascading 縮短最後一哩的 RTT。
- getStats 的 `qualityLimitationReason`、`freezeCount`、`pliCount`、`nackCount`、RTT、`availableOutgoingBitrate` 與選中的 candidate 類型，能把「卡」拆成頻寬、CPU、丟包或 keyframe 問題；累計欄位要計算差值。

## 延伸問答

> [!question]- Q1. SFU 不做轉碼，為什麼還能讓光纖與 4G 的學生看到不同畫質？
> 因為畫質的多樣性是送出端事先準備好的。開 simulcast 時，老師的瀏覽器同時編出 720p、360p、180p 三路獨立串流，以 RID 區分；SFU 只是替每位接收者挑一路轉送，並改寫 SSRC、序號與 timestamp，讓接收端看到的是一條連續的單層串流。開 SVC 時，送出端只編一路分層串流，SFU 依接收者的頻寬丟掉上層的封包。
>
> 兩種方式的共同點是 SFU 從不碰影像內容，所以單台能服務很多人。代價落在送出端：simulcast 的上行是各層總和，編碼要做多次；SVC 的編碼器更複雜，接收端與 SFU 也要支援分層格式。所以「SFU 不轉碼」並不是免費的，只是把成本放到了最便宜、最分散的地方。

> [!question]- Q2. 手算：八人小班，每路影音 1.54 Mbps。用 mesh 時每人上行多少？用 SFU（三層 simulcast 合計 2.19 Mbps）且每人都收其他人的 720p 時，伺服器送出多少？
> Mesh 的每人上行是 (N−1) × b＝7 × 1.54＝10.78 Mbps，下行也是 10.78 Mbps，每人要同時跑 7 個 encoder 與 7 個 decoder，整間教室有 8 × 7 ÷ 2＝28 條 PeerConnection。即使使用者的頻寬夠，一般筆電也很難同時編 7 路 720p。
>
> SFU 的每人上行固定 2.19 Mbps；伺服器收 8 × 2.19＝17.52 Mbps，送出是每人收 7 路 720p，也就是 8 × 7 × 1.54＝86.24 Mbps。這是最壞情況；依版面讓學生的小格只收 180p 時，每位學生下行降到 1.54＋6 × 0.19＝2.68 Mbps，老師收七位學生的 360p 共 7 × 0.54＝3.78 Mbps，伺服器送出約 7 × 2.68＋3.78＝22.5 Mbps。這題要說明的是：SFU 的 N² 成本可以靠選層大幅降低，而 mesh 的 N 倍上行與編碼成本無法靠任何設定省掉。

> [!question]- Q3. 學生回報「畫面每隔幾秒就卡一下」，getStats 顯示丟包率很低，但 `pliCount` 與 `freezeCount` 都持續增加。你會怎麼查？
> 丟包率低卻一直要 keyframe，表示問題多半不在網路丟包，而在換層。最常見的原因是 SFU 的選層邏輯在兩層之間來回跳：頻寬估計在某一層的門檻附近抖動，SFU 每次都立刻升層或降層，simulcast 換層要等目標層的 keyframe，等待期間與 keyframe 抵達時都可能造成短暫凍結。要查 SFU 的換層 log，看這位接收者的換層頻率與頻寬估計的時間序列是否吻合。
>
> 另一個可能是 PLI storm：其他接收者頻繁要求 keyframe，送出端的上行被 keyframe 突波塞爆，所有人都受影響；這時送出端的 `pliCount` 與 `keyFramesEncoded` 會一起跳。修法分別是：選層加上遲滯與升層前的探測；SFU 合併並限制同一層的 PLI 轉發頻率。實驗二的程式就是前者的最小模型。

> [!question]- Q4. 面試題：設計一個 1,000 人參加、講者與觀眾可以互動問答的線上講座，媒體架構要怎麼選？
> 先釐清互動的形狀：同一時間真正需要被看見、被聽見的通常只有講者與少數發問者，其他人只是觀看。所以 publisher 只有幾位，用 SFU；觀眾才是規模的主體。若所有觀眾都直接訂閱 SFU，出口是 1,000 路，加上跨地區分布，需要多台 SFU 以 cascading 分擔，每路串流在節點之間只傳一次，觀眾就近連 edge SFU，延遲可以維持在一秒以內。
>
> 如果可以接受幾秒的延遲，更便宜的做法是把 SFU 上的講者畫面轉成直播（第 38 章的 LL-HLS，或以 WHEP 分發），交給 CDN 擴展；觀眾要發問時，再把該觀眾「升格」為 SFU 上的 publisher。MCU 在這裡只適合用來產生一個合成畫面給直播或錄影，不適合讓 1,000 人各自連線。答題時要先算頻寬，再說明延遲與成本的取捨，最後談故障與擴展。

> [!question]- Q5. SFU 能看到所有人的影像嗎？如果要端到端加密，SFU 還能運作嗎？
> 一般部署中可以看到。每條 PeerConnection 的 DTLS-SRTP 都在 SFU 終結，SFU 解密後才能讀 RTP header、選層、改寫序號，再用接收者的金鑰重新加密；影像內容在 SFU 的記憶體裡是明文。所以 WebRTC 的「媒體一律加密」指的是每一段傳輸都加密，不等於端到端加密。
>
> 要做端到端加密，可以在瀏覽器編碼之後、送出之前，對影像 payload 再加密一層（W3C 的 Encoded Transform 提供插入點，IETF 的 SFrame 定義格式），RTP header 與 SFU 需要的 extension 保持明文，SFU 照常選層與轉送。代價是金鑰管理要由應用自己處理（成員加入或離開時要換金鑰），而錄影、伺服器端轉錄與內容審核都需要明文，因此做不到或必須讓特定伺服器成為「金鑰持有者」。這是需求取捨，不是技術做不到。

> [!question]- Q6. 你負責的視訊服務要同時服務台灣與美東的使用者，應該優先調 NACK 還是 FEC？
> 要先看 RTT 與丟包型態，而不是直接選一個。NACK 只有在「發現缺號＋一個 RTT」小於播放期限時才有用；台灣使用者到台北節點的 RTT 只有十幾到幾十毫秒，NACK 幾乎能補回所有隨機丟包，成本只有丟包率那麼多。美東使用者直連台北的 RTT 約 180 ms，在 120 ms 左右的期限下重送永遠遲到，只能靠 FEC；但 FEC 對 Wi-Fi 常見的突發丟包效果很差，實驗三中平均 1% 的突發丟包，一維 FEC 只恢復約一成。
>
> 所以最有效的不是參數，而是架構：在美東放一台 edge SFU，讓使用者的最後一哩 RTT 降到幾十毫秒，NACK 重新有效；跨洋的 SFU 之間丟包率低，可以穩定開 FEC。參數層面再搭配 Opus in-band FEC 保護音訊、以 getStats 的 `nackCount`、`fecPacketsDiscarded`、`freezeCount` 驗證效果。

> [!question]- Q7. Rita 為什麼堅持 TURN 要設定可中繼的位址範圍？帳密已經是短效的了。
> 短效帳密解決的是「誰能用 TURN」，但沒有限制「TURN 能把封包送到哪裡」。TURN 的本質是替 client 從伺服器所在的網路發出 UDP 封包；如果允許任意目的地，持有合法帳密的使用者（或從前端程式拿到帳密的攻擊者）就能請 TURN 把封包送到 VPC 內部的資料庫、管理介面或雲端 metadata 位址，這是一種 SSRF，TURN 的位置剛好在防火牆內側。
>
> 聲聲 Live 的 TURN 只服務 SFU，所以最小權限的設定是只允許中繼到 SFU 節點的位址，其他目的地一律拒絕（包含私有網段、loopback 與 link-local）。這和短效帳密是兩道獨立的防線：帳密外洩的影響被時間限制，中繼目標被位址限制。審查時還要確認 TURN 的管理介面不對外、共享金鑰定期輪替。

> [!question]- Q8. 為什麼 WebRTC 從 REMB 轉向 TWCC？在 SFU 架構裡兩者各由誰送給誰？
> REMB 讓接收端跑估計演算法，只回報一個建議碼率；問題是接收端不知道每個封包送出的確切時間、是不是重送或 padding，而且每次改進演算法都要更新所有接收端。TWCC 改由接收端回報每個封包的到達時間、送出端自己估計，送出端掌握最多資訊，演算法升級也只要改送出端；transport-wide 序號橫跨同一條 transport 的所有串流，估計的是整條路徑的容量。
>
> 在 SFU 架構中，回饋是一段一段的。老師上傳到 SFU 那一段，SFU 是接收端，回 TWCC 回饋給老師的瀏覽器，由老師端估計上行並調整三層碼率；SFU 送給每位學生那一段，SFU 是送出端，學生的瀏覽器回 TWCC 回饋給 SFU，由 SFU 估計到這位學生的頻寬並據以選層。SFU 不會把學生的回饋轉給老師，否則就回到「一人網路差，全班跟著差」的問題。

## 延伸閱讀

- RFC 7667〈RTP Topologies〉：mesh、SFU（文中稱 selective forwarding middlebox）、MCU 等拓撲的正式描述
- RFC 4585〈Extended RTP Profile for RTCP-Based Feedback (RTP/AVPF)〉與 RFC 5104〈Codec Control Messages in the RTP Audio-Visual Profile with Feedback (AVPF)〉：NACK、PLI、FIR
- RFC 4588〈RTP Retransmission Payload Format〉、RFC 5109〈RTP Payload Format for Generic Forward Error Correction〉、RFC 8627〈RTP Payload Format for Flexible Forward Error Correction (FEC)〉
- RFC 8853〈Using Simulcast in Session Description Protocol (SDP) and RTP Sessions〉與 RFC 8851〈RTP Payload Format Restrictions〉
- IETF RMCAT 工作小組的 draft〈A Google Congestion Control Algorithm for Real-Time Communication〉與〈RTP Extensions for Transport-wide Congestion Control〉；RFC 8888〈RTP Control Protocol (RTCP) Feedback for Congestion Control〉
- RFC 8656〈Traversal Using Relays around NAT (TURN)〉
- W3C〈Identifiers for WebRTC's Statistics API〉與〈Scalable Video Coding (SVC) Extension for WebRTC〉
