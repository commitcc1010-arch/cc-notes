---
chapter: 18
title: TLS 1.3：交握、憑證與信任
part: 4
---

# 第 18 章　TLS 1.3：交握、憑證與信任

> [!abstract] 本章地圖
> **核心問題**：瀏覽器第一次連上 `api.shengsheng.example`，憑什麼相信對面真的是聲聲 Live，而且接下來的資料只有雙方看得懂？
>
> **你會學到**：
> - 逐步畫出 TLS 1.3 的 1-RTT 交握，說出 ClientHello、ServerHello、EncryptedExtensions、Certificate、CertificateVerify、Finished 各自的任務
> - 逐欄讀懂 TLS record 與 ClientHello 的 bytes，包含 SNI、ALPN、supported_versions 與 key_share 擴充
> - 說明金鑰排程如何從一個共享秘密導出各方向的金鑰，以及為什麼竄改交握一定會被發現
> - 依序執行憑證驗證的每一步（鏈、簽章、效期、用途、名稱、撤銷），包含 wildcard 的比對規則
> - 判斷 session resumption 與 0-RTT 什麼時候能用、什麼時候必須回 425，以及什麼場合該上 mTLS
> - 用 Python `ssl` 檢查預設設定，並在 127.0.0.1 上重現「信任庫沒有這張 CA」「名稱不符」「mTLS 少了 client 憑證」三種錯誤
>
> **前置知識**：第 3 章（`openssl s_client` 的基本用法）、第 10 章（TCP 交握）、第 13 章（QUIC 如何使用 TLS 1.3）、第 17 章（hash、HMAC、AEAD、數位簽章、Diffie-Hellman 與 HKDF）

## 18.1 故事：一行 `_create_unverified_context()`

週四下午，小晴寫好了第一個內部工具：每天凌晨把隔天的課表從內部後台 `ops.shengsheng.example`（10.20.3.17，只開內網）匯出成 CSV，寄給客服團隊。程式在筆電上透過辦公室 VPN 執行，第一次跑就失敗了：`ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate`。小晴搜尋這段錯誤訊息，第一個答案的寫法只有一行：`ssl._create_unverified_context()`。加上去以後，程式順利跑完，小晴把它推上去開了 PR。

半小時後，PR 被 Rita 退回，留言只有兩句：「這一行讓 TLS 只剩下加密，沒有身分驗證。任何能擋在你和 `ops` 中間的人，都可以拿一張自己做的憑證冒充後台，把課表和你的登入 cookie 一起拿走。」同一天的站立會議上還有兩件和 TLS 有關的事：阿德打算在 CDN 上啟用 TLS 的 0-RTT，讓回訪的美國學生（RTT 約 180 ms）少等一個來回；Rita 則希望 `ops` 改成只接受公司配發裝置的連線，提議用 mTLS。

```text
 小晴的筆電 ──VPN──► 辦公室 ──WireGuard──► VPC ──► ops.shengsheng.example（10.20.3.17:443）
 （192.0.2.50）                                            │
     │                                                     └ 憑證由「Shengsheng Internal CA」簽發
     │                                                       （公司自己的私有 CA）
     │
     ├ ① Python 用系統預設信任庫驗證 → 找不到 Internal CA → unable to get local issuer certificate
     ├ ② 錯誤修法：_create_unverified_context() → 不驗證任何憑證，誰都能冒充 ops
     └ ③ 正確修法：把 Internal CA 加進這個 context 的信任錨（cafile），其他驗證一項都不關
```

這張圖是 Rita 在 PR 留言裡補上的。從上往下讀：① 錯誤訊息其實說得很精確，`ops` 的憑證是公司自己的 CA 簽的，而 Python 預設只信任作業系統（或 certifi 這類套件）內建的公開 CA，所以往上找不到可以信任的發行者。② 關掉驗證確實讓錯誤消失，但也讓 TLS 失去了它最重要的保證：確認對面是誰。③ 正確的做法是告訴這支程式「Internal CA 也可以信任」，名稱比對、效期、簽章檢查全部照常。

這一章要讓你看懂這三件事背後的同一套機制。不懂 TLS 交握與憑證驗證，你只能在「錯誤訊息」和「關掉驗證」之間二選一；懂了以後，你會知道每種錯誤對應交握的哪一步、該修 client 還是 server，也能判斷 0-RTT 與 mTLS 的風險。章末的動手做會用一套測試用的 CA，在你的電腦上把故事重現並正確修好。

## 18.2 TLS 解決什麼問題

**TLS**（Transport Layer Security，傳輸層安全）是一個建立在可靠的 byte stream（通常是 TCP）之上的協定，讓兩端在一條可能被偷聽、被竄改、被冒充的網路上，建立一條安全的通道。HTTPS 就是「HTTP 跑在 TLS 上」；IMAPS、SMTP 的 STARTTLS、資料庫的加密連線、gRPC 也都用它。QUIC 則把 TLS 1.3 的交握直接整合進傳輸層（第 13 章），WebRTC 用的 DTLS 是 TLS 的 datagram 版本（第 36 章）。

TLS 提供三個保證，對應第 17 章的三個安全性質。**機密性**：路上的人看不到內容，例如學生的密碼與課程筆記。**完整性**：內容被改一個 bit 都會被發現，例如有人想把付款金額 1,000 改成 10,000。**真實性**（authentication，身分驗證）：client 確認 server 真的是 `api.shengsheng.example`，必要時 server 也確認 client 是誰。三者之中，真實性最容易被忽略，卻最關鍵：如果不確認對方身分，攻擊者可以站在中間，和你建立一條「加密得很好」的連線，再和真正的 server 建立另一條，兩邊轉送並偷看所有內容。這種**中間人攻擊**（man-in-the-middle，MITM）正是故事裡 `_create_unverified_context()` 打開的門。

```text
 沒有驗證身分的「加密」：
   小晴 ══加密══► 攻擊者（拿自製憑證冒充 ops）══加密══► 真正的 ops
          ▲                 │
          │                 └ 兩段都是合法的 TLS；攻擊者在中間解密、偷看、改寫，兩端都察覺不到
          └ client 若不驗證憑證，就無從發現對面換人了

 有驗證身分：
   小晴 ══TLS══► 攻擊者 ──► 憑證不是可信 CA 為 ops.shengsheng.example 簽的 → 交握失敗，連線中止
```

圖的上半部說明「加密」不等於「安全」：兩段連線都加密了，但小晴的金鑰是和攻擊者協商出來的。下半部是 TLS 正常運作的樣子：攻擊者拿不出受信任 CA 為這個名字簽的憑證，也沒有真憑證的私鑰，交握失敗。整章的憑證、CA、簽章，都是為了讓 client 做出這個判斷。

同樣重要的是 TLS **不保護什麼**：IP 位址與 port 在 IP、TCP header 裡一定看得到；封包大小與時間也看得到；SNI 一般是明文（18.8 節）；沒加密的 DNS 查詢也會洩漏你要去哪裡（第 15 章）。server 收到資料之後的事，例如日誌裡印出 token，也不在 TLS 的保護範圍。

TLS 的前身是 Netscape 設計的 SSL，「SSL 憑證」只是沿用下來的說法，今天實際使用的協定都是 TLS：

| 版本 | 年份 | 狀態 | 關鍵差異 |
|---|---|---|---|
| SSL 2.0、3.0 | 1995、1996 | 已禁用，有嚴重弱點 | 協定設計本身有缺陷 |
| TLS 1.0、1.1 | 1999、2006 | RFC 8996 正式棄用，主流瀏覽器已移除 | 仍支援 CBC 模式的舊弱點、SHA-1 |
| TLS 1.2 | 2008 | 仍大量使用，要選對設定才安全 | 完整交握 2-RTT；允許 RSA 金鑰傳輸（沒有前向保密） |
| TLS 1.3 | 2018（RFC 8446） | 現行主流，QUIC 只用它 | 完整交握 1-RTT；只剩 AEAD 與 (EC)DHE；憑證也加密 |

TLS 1.3 是一次大掃除：移除 RSA 金鑰傳輸、靜態 DH、壓縮、renegotiation 與所有非 AEAD 的加密模式，cipher suite 從幾百種縮到五種，被移除的每一項背後幾乎都有一次真實的攻擊。本章以 1.3 為主，遇到 1.2 的差異會特別標出，因為 production 仍會遇到 1.2 的 client。

## 18.3 Record layer：TLS 的封包格式

TLS 跑在 TCP 的 byte stream 上，而 byte stream 沒有訊息邊界（第 11 章），所以 TLS 先定義自己的訊息單位：**record**。每個 record 前面有 5 bytes 的 header，說明內容類型與長度，接收端靠長度欄位把 stream 切回一個個 record。這就是第 11 章介紹的「長度前綴」切分法。

```text
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 ┌───────────────┬───────────────────────────────┬───────────────┐
 │ ContentType(8)│  legacy_record_version (16)   │  Length (16)… │  bytes 0-3
 ├───────────────┼───────────────────────────────┴───────────────┤
 │ …Length       │  fragment（Length bytes，最多 2^14＋256）      │  bytes 4-
 └───────────────┴───────────────────────────────────────────────┘

 TLS 1.3 加密後的 record（外層一律偽裝成 application_data）：
 ┌──────┬────────┬────────┬──────────────────────────────────┬─────────┐
 │ 0x17 │ 0x0303 │ Length │ 密文：真正內容 ‖ 真正類型 ‖ 補 0 │ tag 16B │
 └──────┴────────┴────────┴──────────────────────────────────┴─────────┘
```

上半部是所有 record 共用的 header：**ContentType** 說明 fragment 裝的是哪種訊息；**legacy_record_version** 是歷史欄位，TLS 1.3 固定寫 `0x0303`（第一個 ClientHello 可以寫 `0x0301`），真正的版本另外協商；**Length** 是 fragment 長度，明文最多 2^14（16,384）bytes。下半部是 1.3 的巧思：加密後的 record 外層一律寫 23（application_data），真正的類型藏在密文最後一個 byte，後面還能補 0 隱藏長度，路上的設備分不出哪個 record 是憑證、哪個是 HTTP 回應。

| ContentType | 值 | 用途 | TLS 1.3 中是否明文 |
|---|---|---|---|
| change_cipher_spec | 20 | TLS 1.2 用來宣告切換金鑰；1.3 只為了相容 middlebox 送一個假的 | 是（內容固定 1 byte） |
| alert | 21 | 錯誤或關閉通知，例如 `bad_certificate`、`close_notify` | 交握前段是，之後加密 |
| handshake | 22 | 交握訊息：ClientHello、ServerHello…… | 只有 ClientHello、ServerHello 是明文 |
| application_data | 23 | 應用資料；1.3 也用它當所有加密 record 的外層類型 | 加密 |

在封包裡看到 `16 03 01` 開頭，就是一個 handshake record（0x16＝22）；一長串 `17 03 03` 則是加密資料。這三個 bytes 也是判斷「這個 port 跑的是不是 TLS」最快的方法，例如把 HTTP client 連到 HTTPS port 時，server 收到的第一個 byte 就對不上。

## 18.4 TLS 1.3 完整交握：逐步時序

交握（handshake）要在一個 RTT 內完成四件事：協商參數（版本、cipher suite、金鑰交換的 group、上層協定）、建立只有雙方知道的共享秘密、驗證 server 的身分、確認雙方看到的交握內容完全相同。下圖是學生的瀏覽器第一次連上 `api.shengsheng.example`（API LB 203.0.113.80:443）的完整過程，包含前面的 TCP 交握：

```text
 Client（瀏覽器）                                              Server（203.0.113.80:443）
   │──────────────── TCP SYN ───────────────────────────────────►│
   │◄─────────────── TCP SYN+ACK ────────────────────────────────│   ← 第 1 個 RTT（第 10 章）
   │──────────────── TCP ACK ───────────────────────────────────►│
   │                                                             │
   │  ClientHello                                     （明文）   │
   │    supported_versions=[1.3]  key_share=x25519 公開值        │
   │    server_name=api.shengsheng.example  alpn=[h2, http/1.1]  │
   │────────────────────────────────────────────────────────────►│
   │                                                             │ 選參數、算出共享秘密
   │                                     ServerHello  （明文）   │ → 導出交握金鑰
   │                    supported_versions=1.3  key_share=x25519 │
   │                  {EncryptedExtensions}  alpn=h2             │
   │                  {Certificate}          憑證鏈              │ ← 以下 { } 都用交握金鑰加密
   │                  {CertificateVerify}    用私鑰簽 transcript │
   │                  {Finished}             HMAC(transcript)    │
   │◄────────────────────────────────────────────────────────────│   ← 第 2 個 RTT
   │ 驗證憑證鏈、簽章、Finished                                  │
   │  {Finished}                                                 │
   │  [GET /api/schedule]                     ← 應用資料金鑰加密 │
   │────────────────────────────────────────────────────────────►│
   │◄──────────── [NewSessionTicket]、[HTTP 200 …] ──────────────│   ← 第 3 個 RTT 拿到回應
```

這張圖分三段讀。第一段是 TCP 交握，花一個 RTT。第二段是 TLS：client 一口氣送出 ClientHello，其中已經帶著金鑰交換的公開值；server 的回覆只有 ServerHello 是明文，之後的訊息都已用剛導出的交握金鑰加密。第三段，client 驗證完成後送出自己的 Finished，並且**同一趟**就送出第一個 HTTP 請求。所以 TCP 加 TLS 1.3 共兩個 RTT 才送得出請求；對 RTT 180 ms 的美國學生是 360 ms，TLS 1.2 的完整交握還要再多 180 ms。

1.3 省下的那個 RTT 來自「先猜」。TLS 1.2 的 client 要先收到 server 選定的參數，才知道該送哪一種公開值；1.3 的 client 直接在 ClientHello 附上它認為 server 最可能接受的 group（通常是 x25519）的公開值，猜對了，server 收到 ClientHello 就能算出共享秘密，第一個回覆就能加密。

下表是每個交握訊息的任務摘要，之後逐一細看：

| 訊息 | 方向 | 加密？ | 任務 |
|---|---|---|---|
| ClientHello | C→S | 否 | 提議版本、cipher suites、groups 與公開值、簽章演算法；帶 SNI、ALPN |
| ServerHello | S→C | 否 | 選定版本、cipher suite、回傳 server 的公開值；此後雙方都有交握金鑰 |
| EncryptedExtensions | S→C | 是 | 不影響金鑰的其他協商結果，例如 ALPN 選了 `h2` |
| CertificateRequest | S→C | 是 | 只有 mTLS 才送：要求 client 出示憑證（18.10 節） |
| Certificate | S→C | 是 | server 的憑證鏈：leaf 在前，接著中間憑證 |
| CertificateVerify | S→C | 是 | 用憑證的私鑰對「到目前為止的交握紀錄」簽章，證明持有私鑰 |
| Finished | 雙向 | 是 | 以 HMAC 確認雙方看到的交握內容完全一致 |
| NewSessionTicket | S→C | 是 | 交握之後才送，給下次 resumption 用（18.9 節） |

### ClientHello：一次把所有提議講完

ClientHello 是整個交握中唯一由 client 主動決定內容的明文訊息，也是 middlebox、防火牆、CDN 唯一能「看懂」的部分。它的結構如下（括號內是長度）：

```text
 ClientHello（handshake type 1）
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ msg_type=1 (1)  length (3)           handshake header                    │
 ├──────────────────────────────────────────────────────────────────────────┤
 │ legacy_version = 0x0303 (2)          ← 永遠寫 TLS 1.2，真正版本在擴充裡  │
 │ random (32)                          ← 每次新的 CSPRNG 亂數              │
 │ legacy_session_id (1＋0..32)         ← 1.3 填 32 bytes 亂數（相容用）    │
 │ cipher_suites (2＋2n)                ← 例如 0x1301 0x1302 0x1303         │
 │ legacy_compression_methods (1＋1)    ← 只能是 0（null）                  │
 │ extensions (2＋…)                    ← 真正的協商幾乎都在這裡            │
 └──────────────────────────────────────────────────────────────────────────┘

 每個 extension：┌ type (2) ┬ length (2) ┬ data (length bytes) ┐
```

前五個欄位幾乎都是為了和 TLS 1.2 長得一樣：網路上大量 middlebox 只認得 1.2 的格式，看到陌生的版本號就丟包或斷線，所以 1.3 讓 ClientHello「看起來像 1.2 的 resumption」（Q7 有完整說明）。真正的協商全部在 **extensions**，每個擴充都是「類型、長度、資料」，不認得的類型可以安全略過，協定因此能持續加新功能。

| extension | type | 內容 | 為什麼需要 |
|---|---|---|---|
| server_name（SNI） | 0 | 要連的主機名稱，例如 `api.shengsheng.example` | 同一個 IP 上有很多網站，server 要知道該拿哪張憑證（18.8 節） |
| supported_groups | 10 | 願意用的金鑰交換群組：x25519、secp256r1… | 讓 server 選 group |
| signature_algorithms | 13 | 願意接受的簽章演算法：ECDSA P-256、RSA-PSS… | server 據此挑憑證與 CertificateVerify 的演算法 |
| ALPN | 16 | 想說的上層協定：`h2`、`http/1.1` | 交握完就知道要說 HTTP/2 還是 1.1（18.8 節） |
| supported_versions | 43 | 支援的 TLS 版本，`0x0304` 代表 1.3 | 真正的版本協商；有它才代表 client 會說 1.3 |
| psk_key_exchange_modes | 45 | resumption 時是否要再做一次 DHE | 18.9 節 |
| key_share | 51 | 一個或多個 group 的公開值 | 「先猜」的關鍵，讓交握只要 1-RTT |
| pre_shared_key、early_data | 41、42 | resumption 的票券與 0-RTT 宣告 | 18.9 節；pre_shared_key 必須是最後一個擴充 |

cipher suite 在 1.3 裡的意義也變了。TLS 1.2 的 `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256` 把金鑰交換、簽章、加密、hash 綁成一個組合；1.3 的 `TLS_AES_128_GCM_SHA256` 只指定 AEAD 與 HKDF 的 hash，金鑰交換與簽章分別交給 key_share 與 signature_algorithms 協商，組合少很多，設定錯的機會也少很多。

### ServerHello 與 HelloRetryRequest

server 從 ClientHello 的提議中各選一個：版本（放在 supported_versions，值是 `0x0304`）、cipher suite、group，並在 key_share 回傳自己在同一個 group 的公開值。到這裡，雙方各自用「自己的私密值＋對方的公開值」算出同一個 (EC)DHE 共享秘密（第 17 章），導出交握金鑰。ServerHello 也有一個 32 bytes 的 random；若 server 支援 1.3 卻因為 client 只會 1.2 而協商出 1.2，它會把 random 的最後 8 bytes 設成固定的 `DOWNGRD` 標記，支援 1.3 的 client 看到就知道有人在中間把版本降級了，會中止連線。

如果 client 猜錯了 group，例如只附了 secp256r1 的公開值，而 server 只願意用 x25519，server 會回一個 **HelloRetryRequest**（格式上是一個 random 為特殊固定值的 ServerHello），告訴 client「請用 x25519 再來一次」。client 重送 ClientHello，整個交握多花一個 RTT。這就是為什麼瀏覽器常常一次附兩個 group 的公開值：多送一點 bytes，換取不必重來。

### EncryptedExtensions、Certificate、CertificateVerify、Finished

ServerHello 之後的訊息全部加密。**EncryptedExtensions** 放「不影響金鑰計算」的協商結果，最常見的是 ALPN；1.2 把它放在明文的 ServerHello，1.3 把它藏起來。

**Certificate** 帶著 server 的憑證鏈：第一張是 server 自己的 **leaf 憑證**，後面是簽發它的中間憑證，通常不附 root。1.2 的憑證是明文，1.3 改成加密。但憑證是公開文件，任何人都能複製一份，光送憑證不能證明身分。

**CertificateVerify** 補上這一塊：server 用憑證私鑰對「到目前為止所有交握訊息的 hash」（**transcript hash**）簽章，簽章輸入還加上一段固定字串，避免被挪用到別的情境。client 用憑證裡的公鑰驗證；只有持有私鑰的 server 簽得出來，而 transcript 包含雙方這次的 random 與公開值，舊簽章無法重播。

**Finished** 是交握的封條：雙方各用從交握秘密導出的 finished key 對 transcript hash 算 HMAC（第 17 章）。中間有人刪掉一個 cipher suite 或改了某個擴充，transcript 就不同，Finished 對不上，連線中止。server 送出 Finished 後就可以先送應用資料（0.5-RTT）；client 驗證並送出自己的 Finished 後，交握完成。

> [!warning] 常見誤解
> 「TLS 用憑證的公鑰來加密資料。」TLS 1.3 的資料金鑰完全來自 (EC)DHE 的共享秘密，憑證的金鑰對只用來**簽章**（CertificateVerify）。這正是前向保密的來源：就算 server 的私鑰日後外洩，過去錄下的流量仍然解不開。TLS 1.2 的 RSA 金鑰傳輸模式才是「用憑證公鑰加密秘密」，1.3 已經移除。

## 18.5 金鑰排程：一連串的 HKDF

交握需要好幾把用途不同的金鑰：兩個方向的交握金鑰與應用資料金鑰、兩把 finished key、resumption 與 0-RTT 用的秘密。TLS 1.3 用一個固定流程從少數輸入一層層導出它們，叫**金鑰排程**（key schedule），積木是第 17 章的 HKDF：Extract 把輸入濃縮成均勻的秘密，Expand 依「用途標籤」展開出互不相關的金鑰。

```text
            PSK（沒有就用 32 個 0）
                 │
   0 ──► HKDF-Extract ──► Early Secret ──► binder key、client_early_traffic_secret（0-RTT 用）
                 │
           Derive-Secret(., "derived", "")
                 │
 (EC)DHE ──► HKDF-Extract ──► Handshake Secret ─┬─► "c hs traffic"（client 交握金鑰）
 共享秘密                         │             └─► "s hs traffic"（server 交握金鑰）
                                  │                   ↑ context = hash(ClientHello…ServerHello)
           Derive-Secret(., "derived", "")
                 │
   0 ──► HKDF-Extract ──► Main Secret ─┬─► "c ap traffic"、"s ap traffic"（應用資料金鑰）
                                       ├─► "exp master"（給上層協定匯出金鑰）
                                       └─► "res master" → 下次 resumption 的 PSK
                                               ↑ context = hash(ClientHello…server Finished)

 每個 traffic secret 再展開：key = Expand-Label(secret, "key")、iv = Expand-Label(secret, "iv")
```

從上往下讀，這是三個「階段」，每個階段用一次 HKDF-Extract 混入一種新的輸入。第一階段混入 PSK（resumption 才有；第一次連線沒有，就用全 0），得到 Early Secret，0-RTT 的金鑰從這裡來。第二階段混入 (EC)DHE 的共享秘密，得到 Handshake Secret，再配上「ClientHello 到 ServerHello」的 transcript hash，分別導出 client 與 server 方向的交握金鑰，用來加密 EncryptedExtensions 到 Finished。第三階段沒有新的秘密輸入，得到 Main Secret（RFC 8446 裡的英文名稱是 `master secret`，圖中的 `exp master`、`res master` 是 HKDF 標籤的原文），配上「到 server Finished 為止」的 transcript hash，導出應用資料金鑰與下次 resumption 用的秘密。

這個設計有三個值得記住的性質。第一，**每把金鑰都綁定 transcript**：交握內容差一個 byte，導出的金鑰就完全不同，竄改的結果是雙方根本解不開對方的資料。第二，**兩個方向的金鑰不同**。第三，**前向保密來自第二階段**：(EC)DHE 的私密值用完即丟，事後拿到憑證私鑰或 PSK 也算不出 Handshake Secret；resumption 若選 `psk_ke`、不做 DHE 就失去這個性質，所以實務上都用 `psk_dhe_ke`。

下面用標準函式庫實作 TLS 1.3 的 `HKDF-Expand-Label`，並驗證一個任何實作都必須算出的固定值：沒有 PSK 時的 Early Secret，以及它導出的 "derived" 值。這兩個值出現在 TLS 1.3 的官方測試向量（RFC 8448）中，算對了就代表標籤格式與 HKDF 都寫對了。

```python
import hashlib
import hmac

H = hashlib.sha256
ZERO = bytes(H().digest_size)                  # 32 個 0x00


def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, H).digest()


def hkdf_expand_label(secret: bytes, label: str, context: bytes, length: int) -> bytes:
    """TLS 1.3 的 HKDF-Expand-Label：label 前面一律加上 "tls13 "。"""
    full = b"tls13 " + label.encode()
    info = length.to_bytes(2, "big") + bytes([len(full)]) + full + bytes([len(context)]) + context
    out, block, i = b"", b"", 1
    while len(out) < length:                   # HKDF-Expand（RFC 5869）
        block = hmac.new(secret, block + info + bytes([i]), H).digest()
        out, i = out + block, i + 1
    return out[:length]


def derive_secret(secret: bytes, label: str, transcript: bytes) -> bytes:
    return hkdf_expand_label(secret, label, H(transcript).digest(), H().digest_size)


# 第一階段：沒有 PSK 時，early secret 是固定值，任何實作算出來都一樣
early = hkdf_extract(ZERO, ZERO)
salt1 = derive_secret(early, "derived", b"")
print("early secret      ", early.hex()[:32], "…")
print("derived（給下一階）", salt1.hex()[:32], "…")
assert early.hex().startswith("33ad0a1c607ec03b09e6cd9893680ce2")
assert salt1.hex().startswith("6f2615a108c702c5678f54fc9dbab697")

# 第二階段：混入 (EC)DHE 共享秘密。這裡用假的值示意，真實值來自 key_share 的運算
shared = H(b"pretend (EC)DHE shared secret").digest()
hs_secret = hkdf_extract(salt1, shared)
transcript = b"ClientHello...ServerHello"          # 交握訊息的串接（示意）
c_hs = derive_secret(hs_secret, "c hs traffic", transcript)
s_hs = derive_secret(hs_secret, "s hs traffic", transcript)
key = hkdf_expand_label(s_hs, "key", b"", 16)   # AES-128-GCM 的金鑰
iv = hkdf_expand_label(s_hs, "iv", b"", 12)
print("client hs traffic ", c_hs.hex()[:32], "…")
print("server hs traffic ", s_hs.hex()[:32], "…")
print("server 寫入 key/iv", key.hex(), iv.hex())
assert c_hs != s_hs                            # 兩個方向用不同金鑰

# 第三階段：main secret → application traffic secrets（交握完成後的資料用）
master = hkdf_extract(derive_secret(hs_secret, "derived", b""), ZERO)
full_transcript = transcript + b"...EncryptedExtensions...Certificate...CertificateVerify...Finished"
c_ap = derive_secret(master, "c ap traffic", full_transcript)
print("client ap traffic ", c_ap.hex()[:32], "…")
# 換掉 transcript 的任何一個 byte，導出的金鑰就完全不同：這就是「交握被竄改就對不上」
assert derive_secret(hs_secret, "c hs traffic", transcript + b"!") != c_hs
```

```text
early secret       33ad0a1c607ec03b09e6cd9893680ce2 …
derived（給下一階） 6f2615a108c702c5678f54fc9dbab697 …
client hs traffic  e3896950c9324fa9d9b4c3e75c2ecbb0 …
server hs traffic  a730dbe8e7e76d9f61c33e5444cea102 …
server 寫入 key/iv c9ede9f0cff65624df9859d47d617763 b2600bbe37e0c757e86f1a41
client ap traffic  fd3567263a9b9bc8670654b51639b897 …
```

前兩行的值和 RFC 8448 的測試向量相同，`assert` 通過，說明 label 的格式（長度、`tls13 ` 前綴、context 長度）完全正確；只要差一個 byte，算出來就會是完全不同的值。後面幾行用一個假的共享秘密走完第二、三階段：client 與 server 的交握秘密不同；每個秘密再展開成 AES-128-GCM 需要的 16 bytes 金鑰與 12 bytes IV；最後一個 `assert` 驗證把 transcript 改一個字元，導出的金鑰就完全不同。這裡的金鑰只為了示範結構，正式程式請交給 OpenSSL 這類經過審查的實作，不要自己寫（第 17 章）。

## 18.6 憑證與信任鏈

交握中的 CertificateVerify 證明了「server 持有某把私鑰」，但 client 還要知道「這把公鑰真的屬於 `api.shengsheng.example`」。這就是**憑證**（certificate）的工作：一份由 **CA**（Certificate Authority，憑證頒發機構）簽章的文件，內容是「這把公鑰屬於這些名字，在這段期間有效」。網路上使用的憑證格式是 **X.509**，用 ASN.1 DER 編碼，常以 base64 包成 `-----BEGIN CERTIFICATE-----` 的 PEM 文字檔。

```text
 X.509 v3 憑證（簡化）
 ┌───────────────────────────────────────────────────────────────┐
 │ tbsCertificate（to-be-signed：CA 簽章的範圍）                 │
 │   version            v3                                       │
 │   serialNumber       0x5A01        ← CA 內唯一，撤銷時用它指認│
 │   signature          ecdsa-with-SHA256                        │
 │   issuer             CN=Example Issuing CA 2   ← 誰簽的       │
 │   validity           2026-07-01 ～ 2026-12-28（180 天）       │
 │   subject            CN=api.shengsheng.example ← 這張是誰的   │
 │   subjectPublicKeyInfo  EC P-256 公鑰                         │
 │   extensions                                                  │
 │     subjectAltName      DNS:api.shengsheng.example ← 比對名稱 │
 │     basicConstraints    CA:FALSE   ← 不能拿去簽別的憑證       │
 │     keyUsage            digitalSignature                      │
 │     extKeyUsage         serverAuth ← 用途：TLS server         │
 │     authorityInfoAccess 上層憑證與 OCSP 的位置                │
 │     CRL Distribution Points、SCT 清單（CT，第 19 章）         │
 ├───────────────────────────────────────────────────────────────┤
 │ signatureAlgorithm    ecdsa-with-SHA256                       │
 │ signatureValue        CA 用自己的私鑰對 tbsCertificate 的簽章 │
 └───────────────────────────────────────────────────────────────┘
```

逐欄讀這張圖。**issuer** 指向簽發者，**subject** 是持有者，驗證時靠「這張的 issuer 等於上一張的 subject」串成鏈。**validity** 是有效期間。**subjectAltName**（SAN）列出涵蓋的所有名稱，現代瀏覽器與 Python 只看這裡，不看 CN。**basicConstraints** 說明是否為 CA，`CA:FALSE` 的憑證就算私鑰被拿去簽別人，驗證也會失敗。**extKeyUsage** 限制用途：`serverAuth` 給 TLS server，`clientAuth` 給 mTLS 的 client。簽章涵蓋整個 tbsCertificate，改任何欄位都驗不過。

為什麼不讓 root 直接簽 server 憑證？root 的私鑰是整個信任體系的根，外洩了就得更新全世界的作業系統與瀏覽器，往往要好幾年。所以 root 私鑰通常放在離線的 HSM 裡，只偶爾拿出來簽**中間 CA**（intermediate CA），日常簽發由中間 CA 負責，出事時撤銷它、再簽一個新的就好。

```text
 信任庫（trust store，作業系統或瀏覽器內建）
 ┌───────────────────────────┐
 │ Example Root CA R1（自簽） │ ◄─── 信任錨：不需要再往上驗證，「信任」從這裡開始
 └─────────────┬─────────────┘
               │ 用 Root 的私鑰簽
 ┌─────────────▼─────────────┐
 │ Example Issuing CA 2      │ ◄─── 中間憑證：server 必須在 Certificate 訊息裡一起送
 └─────────────┬─────────────┘
               │ 用 Issuing CA 2 的私鑰簽
 ┌─────────────▼─────────────┐
 │ api.shengsheng.example    │ ◄─── leaf：server 自己的憑證，私鑰在 LB 或 CDN 上
 └───────────────────────────┘
   server 送：leaf ＋ Issuing CA 2         client 自己有：Root CA R1
```

這張圖是一條完整的**憑證鏈**（certificate chain）。client 信任庫裡的 root 是**信任錨**（trust anchor）：自簽、不需要再被驗證，信任它是一種設定，不是計算結果。server 送 leaf 與中間憑證，client 從 leaf 往上，用上一層的公鑰驗下一層的簽章，直到抵達某個 root。server 漏送中間憑證時，有些瀏覽器會用快取或 AIA 自己補上，curl 與 Python 不會，這是第 19 章的頭號部署錯誤。

故事裡的 `ops` 使用的是**私有 CA**：公司自己架的 CA，只在內部被信任。內部服務因此不必向公開 CA 申請憑證，名稱也不會出現在公開的 Certificate Transparency 紀錄（第 19 章）；代價是每個 client 都要額外設定信任這個 root，這正是小晴的程式少做的那一步。至於**自簽憑證**，除了手動釘選的人以外沒有人信任它，只適合本機開發與測試。

## 18.7 憑證驗證：client 實際檢查的七件事

驗證由 client 完成，server 送什麼都只是「聲稱」。下圖是 client 收到 Certificate 之後的檢查順序，Python 的 `ssl`、curl、瀏覽器都做同樣的事：

```text
 收到 server 的憑證鏈（leaf, 中間…）
   │
   ├─① 建鏈：從 leaf 依 issuer 往上找，直到信任庫裡的 root ── 找不到 ─► unable to get local issuer certificate
   ├─② 簽章：每一層都用上一層的公鑰驗過                     ── 不符 ───► certificate signature failure
   ├─③ CA 限制：發行者 basicConstraints=CA:TRUE、pathLen 沒超過 ─ 違反 ─► invalid CA certificate
   ├─④ 效期：now 介於 notBefore 與 notAfter（每一張都要）       ─ 不符 ─► not yet valid／has expired
   ├─⑤ 用途：leaf 的 extKeyUsage 含 serverAuth                ─ 不符 ─► unsupported certificate purpose
   ├─⑥ 名稱：要連的主機名稱符合 leaf 的某個 SAN               ─ 不符 ─► Hostname mismatch
   ├─⑦ 撤銷：leaf（與中間）沒有被 CA 撤銷（CRL、OCSP…）       ─ 被撤銷 ─► certificate revoked
   │
   └─ 全部通過 → 再用 leaf 的公鑰驗證 CertificateVerify 的簽章 → 身分確認
```

一步一步看。① **建鏈**是唯一需要搜尋的步驟：拿 leaf 的 issuer 去找 subject 相同的憑證，候選來自 server 送的中間憑證與本機信任庫。② **簽章**確保每一張真的是上一層簽的，自製的「同名」中間 CA 名字對得上，簽章卻驗不過。③ **CA 限制**擋下「拿 leaf 去簽別人」，pathLen 限制下面還能有幾層 CA。④ **效期**用 client 的時鐘判斷，所以時鐘錯誤的設備會看到所有網站都「尚未生效」。

⑤ **用途**防止只核發給 client 的憑證被拿來當 server。⑥ **名稱**最常被忽略，也是 `_create_unverified_context()` 一併關掉的檢查：一張由公開 CA 合法簽給 `evil.example` 的憑證，鏈、簽章、效期全部通過，只有名稱比對能發現它不是 `ops.shengsheng.example`，所以 Python 把 `check_hostname` 與 `verify_mode` 分成兩個設定、預設都開。⑦ **撤銷**檢查憑證是否在到期前被作廢，它是實務上最弱的一環。

### 名稱比對與 wildcard 的規則

名稱比對看的是 SAN 裡的 DNS 名稱（`dNSName`），比對不分大小寫，結尾的點（`www.shengsheng.example.`）會被忽略。如果連線目標是 IP，例如直接連 `203.0.113.80` 的 443 port，就只能比對 SAN 裡的 IP 位址項目（`iPAddress`），寫在 DNS 名稱裡的 IP 字串不算數；公開 CA 很少簽發 IP 憑證，所以「用 IP 連 HTTPS」幾乎都會名稱不符。

**wildcard 憑證**用 `*` 代表一個 label，例如 `*.shengsheng.example`，一張憑證涵蓋 `www`、`api`、`auth` 等所有子網域。它的規則比直覺嚴格：

| SAN | 連線名稱 | 結果 | 原因 |
|---|---|---|---|
| `*.shengsheng.example` | `www.shengsheng.example` | 符合 | `*` 代表最左邊的一個 label |
| `*.shengsheng.example` | `WWW.Shengsheng.Example.` | 符合 | 不分大小寫，忽略結尾的點 |
| `*.shengsheng.example` | `shengsheng.example` | 不符合 | wildcard 不涵蓋 apex，要另外列一個 SAN |
| `*.shengsheng.example` | `a.b.shengsheng.example` | 不符合 | `*` 只代表恰好一個 label，不能跨點 |
| `*.example` | `shengsheng.example` | 不符合 | 太寬的 wildcard（public suffix 層級）不被接受 |
| `api*.shengsheng.example` | `api1.shengsheng.example` | 依實作而定，視為不符合 | CA/B Forum 規範不允許這種部分 wildcard，公開 CA 不會簽 |

實務上的取捨是：wildcard 方便，但一把私鑰涵蓋所有子網域，任何一台持有它的機器被入侵，所有子網域都可能被冒充。聲聲 Live 的做法是對外的 `www`、`api`、`auth` 各用自己的憑證，wildcard 只用在內部的測試環境。

### 撤銷：最弱的一環

憑證在效期內作廢，叫**撤銷**（revocation）。常見原因是私鑰外洩、網域易主、CA 發現自己簽錯。問題在於 client 怎麼知道：

| 機制 | 怎麼運作 | 優點 | 缺點 |
|---|---|---|---|
| CRL | CA 定期發布「已撤銷序號清單」，client 下載比對 | 簡單、可快取、可離線 | 清單可能很大；更新有延遲 |
| OCSP | client 即時詢問 CA 的 responder「這張還有效嗎」 | 資訊較即時 | 多一次連線、拖慢交握；CA 知道你在連哪個網站；連不上時多半「放行」 |
| OCSP stapling | server 定期向 CA 取回簽過的 OCSP 回應，在交握中附給 client | 不洩漏隱私、不多一次連線 | 要 server 設定；client 多半不強制 |
| 瀏覽器推送的清單 | 瀏覽器廠商彙整撤銷資訊，壓縮後推給瀏覽器 | 快、不洩漏隱私 | 只有瀏覽器有，Python 與 curl 預設不用 |
| 短效憑證 | 效期短到撤銷的意義不大 | 不依賴撤銷基礎設施 | 必須完全自動化更新（第 19 章） |

最大的問題是「連不上就放行」（soft-fail）：OCSP responder 一沒回應就斷線的話，CA 一出狀況全網都會斷，所以多數 client 選擇放行，而能擋在中間的攻擊者也剛好能擋掉 OCSP 查詢。業界因此轉向短效憑證與瀏覽器推送的清單。Python 的 `ssl` 預設不檢查撤銷，私鑰外洩時最重要的是盡快換掉金鑰與憑證。

## 18.8 SNI 與 ALPN：一個 IP 上的多個名字與協定

### SNI：先說你要找誰

聲聲 Live 的 CDN edge 203.0.113.10 同時服務 `www.shengsheng.example` 與其他客戶的網站，API LB 203.0.113.80 後面也不只一個名稱。問題來了：TLS 交握發生在 HTTP 之前，server 還沒看到 `Host` header，怎麼知道該送哪一張憑證？答案是 **SNI**（Server Name Indication）：client 在 ClientHello 的 server_name 擴充裡寫上要連的主機名稱，server 依此選擇憑證與設定。

```text
                         203.0.113.10:443（CDN edge）
 ClientHello                     │
  server_name=www.shengsheng.example ──► 憑證 A：SAN www.shengsheng.example
  server_name=shop.example.com       ──► 憑證 B：SAN shop.example.com
  （沒有 SNI，例如用 IP 連）          ──► 預設憑證：多半名稱不符，或直接拒絕交握
```

這張圖說明 SNI 是「共用 IP」的前提。最後一列是常見的除錯陷阱：用 `openssl s_client` 連 IP 卻不加 `-servername`，或舊程式不送 SNI，server 只能拿預設憑證，你看到的就不是要查的那張（第 3 章）。SNI 只能放 DNS 名稱；用 IP 連線時 client 不送 SNI。

SNI 的代價是隱私：它是明文，路上的人看得到你連哪個網站，有些網路也據此封鎖網站。補上這個洞的是 **ECH**（Encrypted Client Hello）：client 送出兩層 ClientHello，外層只寫一個共用的公開名稱（例如 CDN 自己的名字），真正的 SNI 與 ALPN 放在用 server 公鑰加密的內層。server 的 ECH 公鑰透過 DNS 的 HTTPS record 發布（第 14 章），所以 ECH 要搭配加密的 DNS 才完整（第 15 章）。標準化與部署狀態見 18.11 節。

### ALPN：交握完就知道要說哪種語言

同一個 443 port 上，client 可能想說 HTTP/2 或 HTTP/1.1。**ALPN**（Application-Layer Protocol Negotiation）讓 client 在 ClientHello 列出想說的協定，例如 `h2`、`http/1.1`，server 選一個放在 EncryptedExtensions 回覆。交握結束時雙方就已經知道要說哪一種，不必再多花一個 RTT 升級。gRPC 依賴 `h2`；HTTP/3 的 `h3` 則是在 QUIC 的交握裡協商（第 13、22 章）。依規格，支援 ALPN 的 server 若找不到共同的協定，應送出 `no_application_protocol` alert 中止交握，而不是默默選一個；不支援 ALPN 的 server 則直接忽略這個擴充。

SNI 與 ALPN 一起決定了 CDN 與 LB 的路由：SNI 決定憑證與後端，ALPN 決定 HTTP 版本。舊 client 不送 ALPN 時雙方預設說 HTTP/1.1；gRPC 連到沒有在 ALPN 選 `h2` 的 LB 就會失敗。在哪一層解開 TLS（TLS termination），哪一層才看得到 HTTP，第 19、25 章會繼續討論。

## 18.9 Session resumption 與 0-RTT

### Resumption：用上次的秘密省下憑證驗證

完整交握除了 RTT，還要 CPU：server 每次簽章，client 每次驗整條憑證鏈。**session resumption** 讓 server 在交握後送出 **NewSessionTicket**，裡面是只有 server 解得開的票券，代表從上一次 Main Secret 導出的 **PSK**（pre-shared key，預先共享的金鑰）。下次連線時 client 在 pre_shared_key 擴充附上票券，server 認得它，就跳過 Certificate 與 CertificateVerify。

票券的壽命上限是 7 天，server 通常設得更短；resumption 時仍應做一次新的 (EC)DHE（`psk_dhe_ke`）維持前向保密。resumption 省下的是驗證與簽章的計算，RTT 數仍是一個。

### 0-RTT：在第一個 flight 就送請求

如果 client 拿著票券，而且 server 在票券裡表示願意接受 **early data**，client 可以在 ClientHello 後面**立刻**用 Early Secret 導出的金鑰送出應用資料，不等任何回覆，這就是 **0-RTT**：

```text
 Client（帶著上次的 ticket）                                    Server
   │ ClientHello  + pre_shared_key(ticket) + early_data          │
   │ [0-RTT] GET /api/schedule        ← 用 PSK 導出的 early 金鑰 │
   │────────────────────────────────────────────────────────────►│ 驗 ticket；決定接受或拒絕 early data
   │         ServerHello  {EncryptedExtensions: 接受 early_data} │
   │                {Finished}  [HTTP 200 課表]                  │ ← 回應在第一個 RTT 內就到
   │◄────────────────────────────────────────────────────────────│
   │ {EndOfEarlyData} {Finished}                                 │
   │────────────────────────────────────────────────────────────►│

 攻擊者把第一個 flight 錄下來再送一次 ─────────────────────────►│ server 可能再處理一次同樣的請求
```

時序圖的上半部是正常流程：請求和 ClientHello 一起送出，server 接受 early data 的話，第一個回覆就帶著 HTTP 回應，對 RTT 180 ms 的學生，省下整整一個來回。下半部是代價：0-RTT 資料在 server 提供任何新鮮的亂數之前就送出了，它的金鑰只取決於票券，所以一個錄下這段 bytes 的攻擊者可以原封不動再送一次，server 解得開、也會覺得合法。這叫**重放**（replay）。完整交握沒有這個問題，因為 server random 每次都不同，舊的 bytes 導不出新連線的金鑰。

TLS 層有一些緩解手段（票券只能用一次、記錄看過的 ClientHello、檢查票券年齡），但在全球數百台 CDN edge 之間共享「用過的票券」非常困難，client 自己在網路不穩時也可能重送。所以 0-RTT 只能用在**重放了也沒關係**的請求。聲聲 Live 的規則（第 13、22 章一致）是：**只讓 GET 與 HEAD 走 0-RTT，其他請求若出現在 early data 中，一律回 425 Too Early**。CDN 把 early data 中的請求轉給 origin 時加上 `Early-Data: 1` header；瀏覽器這類 client 收到 425，通常會在交握完成後自動重送一次。

| 請求 | 走 0-RTT？ | 理由 |
|---|---|---|
| `GET /api/schedule`（查課表） | 可以 | 重放只會多查一次，沒有副作用 |
| `HEAD /static/slides.pdf` | 可以 | 只讀 metadata |
| `POST /v1/bookings`（預約課程） | 回 425 | 重放會重複預約、重複扣堂數 |
| `POST /v1/payments`、改密碼、登出 | 回 425 | 有副作用，且是攻擊者最想重放的請求 |
| 帶有一次性 token 的 GET（例如 magic link） | 回 425 | GET 語意上應該安全，但這個實作有副作用，method 規則擋不住，要個別處理 |

表格最後一列提醒：規則以 method 為準，前提是 API 真的遵守 HTTP 語意，GET 沒有副作用（第 20、21 章）。如果有人寫了 `GET /bookings/create`，0-RTT 會讓這個設計錯誤變成安全漏洞。下面用 WSGI 寫一個極簡的 middleware，模擬「同一段 0-RTT 被錄下來重放一次」：

```python
from wsgiref.util import setup_testing_defaults

bookings = []                                  # 預約紀錄：被重放就會多出一筆


def app(environ, start_response):
    """聲聲 Live 後端的簡化版：POST 會建立預約，GET 只讀課表。"""
    if environ["REQUEST_METHOD"] == "POST":
        bookings.append(environ["PATH_INFO"])
        start_response("201 Created", [("Content-Type", "text/plain")])
        return [b"booked"]
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"schedule"]


def early_data_guard(inner):
    """CDN 收到 0-RTT 資料時會加上 Early-Data: 1。只放行 GET／HEAD，其餘回 425。"""
    def wrapped(environ, start_response):
        if environ.get("HTTP_EARLY_DATA") == "1" and environ["REQUEST_METHOD"] not in ("GET", "HEAD"):
            start_response("425 Too Early", [("Content-Type", "text/plain")])
            return [b"retry after handshake"]
        return inner(environ, start_response)
    return wrapped


def send(handler, method, path, early):
    env = {"REQUEST_METHOD": method, "PATH_INFO": path}
    if early:
        env["HTTP_EARLY_DATA"] = "1"
    setup_testing_defaults(env)
    status = []
    handler(env, lambda s, h: status.append(s))
    return status[0]


for name, handler in [("沒有防護", app), ("有 early_data_guard", early_data_guard(app))]:
    bookings.clear()
    # 同一個 0-RTT 封包被錄下來，又被重送一次：server 看到兩個一模一樣的 early data 請求
    results = [send(handler, "POST", "/v1/bookings", early=True) for _ in range(2)]
    if results[0].startswith("425"):           # 正常的 client 收到 425，交握完成後重送一次
        results.append(send(handler, "POST", "/v1/bookings", early=False))
    print(f"{name:<18} 回應 {results}  → 預約筆數 {len(bookings)}")
    print(f"{'':<18} 0-RTT 的 GET /schedule → {send(handler, 'GET', '/schedule', early=True)}")
assert len(bookings) == 1
```

```text
沒有防護               回應 ['201 Created', '201 Created']  → 預約筆數 2
                   0-RTT 的 GET /schedule → 200 OK
有 early_data_guard 回應 ['425 Too Early', '425 Too Early', '201 Created']  → 預約筆數 1
                   0-RTT 的 GET /schedule → 200 OK
```

第一組沒有防護，被重放的兩個 0-RTT POST 都被處理，產生兩筆預約。第二組的兩個 early data POST 都拿到 425，正常的 client 交握完成後重送一次，最後只有一筆；GET 兩組都照常回 200。實務上這段邏輯放在 CDN 或 nginx，後端只相信 `Early-Data` header，但入口必須清掉 client 自帶的同名 header，否則攻擊者可以偽造它。

## 18.10 mTLS：讓 server 也驗證 client

一般的 TLS 只驗證 server，client 的身分交給上層處理：密碼、session cookie、JWT（第 26、27 章）。**mTLS**（mutual TLS，雙向 TLS）讓 server 在交握中也要求 client 出示憑證，並用同樣的七個步驟驗證它。用途是「機器的身分」：service 之間的呼叫、只允許公司配發的裝置連後台、IoT 設備連雲端、金融機構之間的 API。

```text
 Client（小晴的筆電，持有 client 憑證）                       Server（ops.shengsheng.example）
   │ ClientHello ───────────────────────────────────────────────►│
   │◄── ServerHello、{EncryptedExtensions}、{CertificateRequest}、│ ← 多了 CertificateRequest：
   │    {Certificate}、{CertificateVerify}、{Finished}           │   列出可接受的簽章演算法與 CA
   │                                                             │
   │ {Certificate: CN=xiaoqing-laptop ← Internal CA 簽發}        │
   │ {CertificateVerify: 用筆電的私鑰簽 transcript}              │
   │ {Finished} ────────────────────────────────────────────────►│ ① 建鏈到 Internal CA
   │                                                             │ ② EKU 要含 clientAuth
   │                                                             │ ③ 驗 CertificateVerify
   │◄──── 驗證失敗：alert certificate_required／bad_certificate ─│    失敗就送 alert
   │◄──── 驗證成功：[應用資料]，後端拿到 client 的身分 ──────────│
```

時序圖和一般交握只差三處：server 多送 CertificateRequest；client 在 Finished 前多送自己的 Certificate 與 CertificateVerify；server 驗證通過才繼續。實務上很困擾人的細節是：在 TLS 1.3，client 送出 Finished 就認為交握完成，server 的驗證結果要等下一個 record 才以 alert 傳回，所以 client 的錯誤常常出現在「第一次讀資料」而不是 connect，實驗五會重現這個現象。

mTLS 有三個取捨。第一，**憑證的發放與輪替**是主要成本：每台機器都要有憑證並自動更新，通常需要私有 CA 與自動化，service mesh 與 SPIFFE 就是在解決這件事（第 30 章）。第二，**終結的位置**：若 LB 解開 mTLS，就要把驗證過的 client 身分放進 header 交給後端，而且入口要清掉 client 自帶的同名 header。第三，**瀏覽器體驗很差**，所以 mTLS 多用在機器之間或受管理的裝置。Rita 的方案正是後者：公司筆電由 MDM 安裝 client 憑證，沒有憑證的裝置連交握都過不了。

## 18.11 2026 現況：RFC 9846、ECH 與後量子金鑰交換

> [!note] 2026 現況
> 以下依 2026 年 10 月查證，截至 2026 年 10 月：
> - **TLS 1.3 有新版規格**：RFC 9846（2026-07）取代 RFC 8446，版本號仍是 TLS 1.3，與 8446 相容，屬於文件層面的修訂與整併。它在文件上也取代了 TLS 1.2 的 RFC 5246，但網路上仍有大量 TLS 1.2 流量，實作支援不受影響。
> - **ECH 已成為 RFC**：TLS Encrypted Client Hello 為 RFC 9849（2026-03），透過 DNS HTTPS／SVCB record 的 `ech` 參數發布設定的方法為 RFC 9848（2026-03）。依一般了解，Chromium 系與 Firefox 瀏覽器已在一定條件下預設啟用（Firefox 需搭配 DoH），大型 CDN 也已對其代理的網站啟用；各瀏覽器、Apple 平台與 OpenSSL 主線的支援細節本書未逐一查證，導入前請查各實作當期文件。
> - **後量子混合金鑰交換已成為 RFC**：RFC 10024（2026-08）定義 `X25519MLKEM768`（codepoint 0x11EC），把傳統的 X25519 與後量子的 ML-KEM-768 結合，兩者都被破解才會失守。主流瀏覽器與 OpenSSL 3.5 起已預設送出這個 key share，章末實驗一在 OpenSSL 3.6 上就能看到它。它的 client key share 約 1.2 KB，讓 ClientHello 從幾百 bytes 變成約 1.5 KB，可能跨越多個 TCP segment，曾觸發一些只讀第一個封包的 middlebox 出錯。目前後量子保護的是**金鑰交換**（防範「現在錄下、未來解密」），憑證的後量子簽章在 WebPKI 尚未普及。
> - **公開憑證效期縮短**：CA/B Forum Ballot SC-081v3 已通過，2026-03-15 起公開 TLS 憑證最長 200 天，2027-03-15 起 100 天，2029-03-15 起 47 天。自動化更新已經是必要條件（第 19 章）。
> - **撤銷**：Let's Encrypt 已停止 OCSP、改以 CRL 發布撤銷資訊（本項未經本書逐一查證，以 CA 公告為準）。整體趨勢是用短效憑證與瀏覽器推送的清單取代即時 OCSP 查詢。

對日常工作的影響有三點：引用規格時新文件寫 RFC 9846，舊文件的 RFC 8446 指的是同一個協定；ClientHello 變大，防火牆、IDS 與自製的 TLS 解析程式都要能處理跨多個封包的 ClientHello（第 8 章）；憑證效期一年比一年短，靠人工更新憑證的流程都會出事。

## 18.12 動手做：手組 ClientHello、看交握、驗憑證

這一節的五個實驗只用標準函式庫，在 127.0.0.1 或記憶體中執行，不連外網。實驗二與實驗五內嵌了一套**本書專用的測試 PKI**：內部 CA「Shengsheng Internal CA」、`ops.shengsheng.example` 的 server 憑證、小晴筆電的 client 憑證，由下面的 openssl 指令產生（不需要執行；私鑰已公開在書裡，只能拿來練習）：

```bash
# CA：basicConstraints 標成 critical CA:TRUE，pathlen:0 表示下面不能再有中間 CA
openssl ecparam -name prime256v1 -genkey -noout -out ca.key
openssl req -x509 -new -key ca.key -sha256 -subj "/O=Shengsheng Live/CN=Shengsheng Internal CA" \
  -not_before 20260101000000Z -not_after 21251231235959Z \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" -addext "keyUsage=critical,keyCertSign,cRLSign" -out ca.pem
# server 憑證：SAN 只有 ops.shengsheng.example，EKU 是 serverAuth（client 憑證同理，EKU 改 clientAuth）
openssl ecparam -name prime256v1 -genkey -noout | openssl pkcs8 -topk8 -nocrypt -out srv.key
openssl req -new -key srv.key -subj "/CN=ops.shengsheng.example" -out srv.csr
openssl x509 -req -in srv.csr -CA ca.pem -CAkey ca.key -set_serial 0x1801 -sha256 \
  -not_before 20260101000000Z -not_after 21251231235959Z -extfile srv.ext -out srv.pem
```

效期設到 2125 年，只是為了讓範例多年後仍能執行；真實的公開憑證最長 200 天（18.11 節）。`srv.ext` 裡寫的是 `basicConstraints=critical,CA:FALSE`、`keyUsage=critical,digitalSignature`、`extendedKeyUsage=serverAuth`、SAN 與 SKI／AKI；Python 3.13 起預設做嚴格的 X.509 檢查，少了這些欄位的隨手自簽憑證可能被拒絕。

### 實驗一：手組一個 ClientHello，再逐欄解析

第一個實驗用 `struct` 依 18.4 節的格式組出一個最小但完整的 TLS 1.3 ClientHello，含 SNI 與 ALPN，再寫一個解析器把它逐欄讀回來。最後用同一個解析器去讀本機 OpenSSL 真正產生的 ClientHello（透過 `ssl.MemoryBIO`，不需要網路也不需要 server），對照兩者的差別。

```python
import hashlib
import ssl
import struct

# 型別代碼（TLS 1.3 規格與 IANA 登錄）
EXT_NAMES = {0: "server_name", 10: "supported_groups", 11: "ec_point_formats",
             13: "signature_algorithms", 16: "alpn", 22: "encrypt_then_mac",
             23: "extended_master_secret", 35: "session_ticket", 43: "supported_versions",
             45: "psk_key_exchange_modes", 51: "key_share", 65281: "renegotiation_info"}
GROUPS = {0x001D: "x25519", 0x0017: "secp256r1", 0x0018: "secp384r1", 0x0019: "secp521r1",
          0x001E: "x448", 0x0100: "ffdhe2048", 0x0101: "ffdhe3072", 0x11EC: "X25519MLKEM768"}
SUITES = {0x1301: "TLS_AES_128_GCM_SHA256", 0x1302: "TLS_AES_256_GCM_SHA384",
          0x1303: "TLS_CHACHA20_POLY1305_SHA256"}


def vec(data: bytes, len_bytes: int) -> bytes:
    """TLS 的可變長度向量：前面放 1、2 或 3 bytes 的長度。"""
    return len(data).to_bytes(len_bytes, "big") + data


def ext(ext_type: int, body: bytes) -> bytes:
    return struct.pack("!H", ext_type) + vec(body, 2)


def build_client_hello(sni: str, alpn: list[str], key_share: bytes) -> bytes:
    extensions = b"".join([
        ext(0, vec(b"\x00" + vec(sni.encode("ascii"), 2), 2)),         # host_name(0)＋名稱
        ext(10, vec(struct.pack("!2H", 0x001D, 0x0017), 2)),
        ext(13, vec(struct.pack("!3H", 0x0403, 0x0804, 0x0401), 2)),
        ext(16, vec(b"".join(vec(p.encode(), 1) for p in alpn), 2)),
        ext(43, vec(struct.pack("!H", 0x0304), 1)),                     # 只提議 TLS 1.3
        ext(45, vec(b"\x01", 1)),                                        # psk_dhe_ke
        ext(51, vec(struct.pack("!H", 0x001D) + vec(key_share, 2), 2)),
    ])
    body = (struct.pack("!H", 0x0303)          # legacy_version：為了相容，仍寫 TLS 1.2
            + bytes(range(32))                 # random：真實實作必須用 CSPRNG，這裡固定以便對照
            + vec(bytes(range(0xE0, 0x100)), 1)  # legacy_session_id：32 bytes，相容模式
            + vec(struct.pack("!3H", 0x1301, 0x1302, 0x1303), 2)
            + vec(b"\x00", 1)                  # legacy_compression_methods：只能是 null
            + vec(extensions, 2))
    handshake = b"\x01" + vec(body, 3)         # msg_type 1 = client_hello，長度 3 bytes
    return struct.pack("!BHH", 22, 0x0301, len(handshake)) + handshake  # record header


def parse_client_hello(rec: bytes) -> dict:
    ctype, rver, rlen = struct.unpack_from("!BHH", rec, 0)
    print(f"record: type={ctype}(handshake) legacy_version=0x{rver:04x} length={rlen}")
    msg_type, hlen = rec[5], int.from_bytes(rec[6:9], "big")
    print(f"handshake: msg_type={msg_type}(client_hello) length={hlen}")
    p = 9
    ver = struct.unpack_from("!H", rec, p)[0]; p += 2
    p += 32                                    # random
    sid_len = rec[p]; p += 1 + sid_len
    print(f"  legacy_version=0x{ver:04x} random=32 bytes session_id={sid_len} bytes")
    cs_len = struct.unpack_from("!H", rec, p)[0]; p += 2
    suites = struct.unpack_from(f"!{cs_len // 2}H", rec, p); p += cs_len
    tls13 = [SUITES[s] for s in suites if s in SUITES]
    others = len(suites) - len(tls13)
    print(f"  cipher_suites：{tls13}" + (f"＋{others} 個 TLS 1.2 套件" if others else ""))
    p += 1 + rec[p]                            # 跳過 compression methods
    ext_total = struct.unpack_from("!H", rec, p)[0]; p += 2
    end, found = p + ext_total, {}
    print(f"  extensions：共 {ext_total} bytes")
    while p < end:
        etype, elen = struct.unpack_from("!HH", rec, p); p += 4
        data = rec[p:p + elen]; p += elen
        name = EXT_NAMES.get(etype, f"unknown({etype})")
        if etype == 0:                         # server_name_list → 第一個 host_name
            value = data[5:5 + struct.unpack_from("!H", data, 3)[0]].decode()
        elif etype == 16:                      # protocol_name_list
            value, q = [], 2
            while q < len(data):
                value.append(data[q + 1:q + 1 + data[q]].decode()); q += 1 + data[q]
        elif etype == 10:
            value = [GROUPS.get(g, hex(g)) for g in struct.unpack_from(f"!{(elen - 2) // 2}H", data, 2)]
        elif etype == 43:
            value = [f"0x{v:04x}" for v in struct.unpack_from(f"!{data[0] // 2}H", data, 1)]
        elif etype == 51:                      # client_shares：可以同時猜好幾個 group
            value, q = [], 2
            while q < len(data):
                group, klen = struct.unpack_from("!HH", data, q)
                value.append(f"{GROUPS[group]}:{klen}B"); q += 4 + klen
        elif etype == 13:
            algs = struct.unpack_from(f"!{(elen - 2) // 2}H", data, 2)
            value = f"{len(algs)} 種，前三個 " + " ".join(f"0x{a:04x}" for a in algs[:3])
        else:
            value = data.hex()
        found[name] = value
        print(f"    type={etype:<5} len={elen:<4} {name:<22} {value}")
    assert p == end == len(rec)                # 長度欄位全部對得上，沒有多也沒有少
    return found


public = hashlib.sha256(b"demo x25519 key").digest()  # 示意用 32 bytes，不是真的金鑰對
hello = build_client_hello("ops.shengsheng.example", ["h2", "http/1.1"], public)
print(f"共 {len(hello)} bytes，前 16 bytes：{hello[:16].hex(' ')}")
fields = parse_client_hello(hello)
assert fields["server_name"] == "ops.shengsheng.example"
assert fields["key_share"] == ["x25519:32B"]
assert fields["alpn"] == ["h2", "http/1.1"] and fields["supported_versions"] == ["0x0304"]

# 對照：讓本機的 OpenSSL 產生一個真的 ClientHello（MemoryBIO：不需要網路，也不需要 server）
ctx = ssl.create_default_context()
ctx.set_alpn_protocols(["h2", "http/1.1"])
incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
obj = ctx.wrap_bio(incoming, outgoing, server_hostname="ops.shengsheng.example")
try:
    obj.do_handshake()
except ssl.SSLWantReadError:                   # 送出 ClientHello 後在等 server 回覆
    pass
real = outgoing.read()
print(f"\n{ssl.OPENSSL_VERSION.split()[1]} 版 OpenSSL 產生的 ClientHello：{len(real)} bytes")
parsed = parse_client_hello(real)
assert parsed["server_name"] == "ops.shengsheng.example"
```

```text
共 214 bytes，前 16 bytes：16 03 01 00 d1 01 00 00 cd 03 03 00 01 02 03 04
record: type=22(handshake) legacy_version=0x0301 length=209
handshake: msg_type=1(client_hello) length=205
  legacy_version=0x0303 random=32 bytes session_id=32 bytes
  cipher_suites：['TLS_AES_128_GCM_SHA256', 'TLS_AES_256_GCM_SHA384', 'TLS_CHACHA20_POLY1305_SHA256']
  extensions：共 126 bytes
    type=0     len=27   server_name            ops.shengsheng.example
    type=10    len=6    supported_groups       ['x25519', 'secp256r1']
    type=13    len=8    signature_algorithms   3 種，前三個 0x0403 0x0804 0x0401
    type=16    len=14   alpn                   ['h2', 'http/1.1']
    type=43    len=3    supported_versions     ['0x0304']
    type=45    len=2    psk_key_exchange_modes 0101
    type=51    len=38   key_share              ['x25519:32B']

3.6.3 版 OpenSSL 產生的 ClientHello：1545 bytes
record: type=22(handshake) legacy_version=0x0301 length=1540
handshake: msg_type=1(client_hello) length=1536
  legacy_version=0x0303 random=32 bytes session_id=32 bytes
  cipher_suites：['TLS_AES_256_GCM_SHA384', 'TLS_CHACHA20_POLY1305_SHA256', 'TLS_AES_128_GCM_SHA256']＋14 個 TLS 1.2 套件
  extensions：共 1429 bytes
    type=65281 len=1    renegotiation_info     00
    type=0     len=27   server_name            ops.shengsheng.example
    type=11    len=2    ec_point_formats       0100
    type=10    len=18   supported_groups       ['X25519MLKEM768', 'x25519', 'secp256r1', 'x448', 'secp384r1', 'secp521r1', 'ffdhe2048', 'ffdhe3072']
    type=35    len=0    session_ticket         
    type=16    len=14   alpn                   ['h2', 'http/1.1']
    type=22    len=0    encrypt_then_mac       
    type=23    len=0    extended_master_secret 
    type=13    len=54   signature_algorithms   26 種，前三個 0x0905 0x0906 0x0904
    type=43    len=5    supported_versions     ['0x0304', '0x0303']
    type=45    len=2    psk_key_exchange_modes 0101
    type=51    len=1258 key_share              ['X25519MLKEM768:1216B', 'x25519:32B']
```

先看上半部我們自己組的 ClientHello。前 5 bytes `16 03 01 00 d1` 是 record header：類型 0x16（handshake）、legacy 版本 0x0301、長度 209；接著 `01 00 00 cd` 是 handshake header（類型 1、長度 205），再來 `03 03` 就是 legacy_version。SNI 擴充的 27 bytes 是 2 bytes 清單長度、1 byte 類型、2 bytes 名稱長度與 22 bytes 的名稱。最後的 `assert p == end == len(rec)` 確認三層長度（record、handshake、extensions）全部吻合，這是寫 TLS 解析器最容易錯的地方：任何一層算錯，後面全部錯位。

下半部是 OpenSSL 3.6 實際送出的 ClientHello。它有 1,545 bytes，主因是 key_share 裡同時有 1,216 bytes 的 `X25519MLKEM768` 與 32 bytes 的 x25519：client 一次猜兩個 group，避免 HelloRetryRequest（後量子的狀態見 18.11 節）。supported_versions 同時列出 `0x0304` 與 `0x0303`，再加上 14 個 TLS 1.2 套件與 renegotiation_info、extended_master_secret 等 1.2 才用得到的擴充，代表它也願意退回 TLS 1.2。random 每次不同，所以沒有印出；簽章演算法的前三個代碼依 OpenSSL 版本而定，你的機器上可能不同。

### 實驗二：在記憶體裡完成一次交握，看每一趟有哪些 record

第二個實驗讓 Python 的 client 與 server 各用一對 `MemoryBIO` 交握，程式自己扮演「網路」，把一端送出的 bytes 搬到另一端，並在搬的同時把每個 record 的類型與長度印出來。這樣不用 tcpdump，也能看到 18.4 節時序圖裡每一趟真正的內容。

```python
import os
import ssl
import struct
import tempfile

# 測試用 PKI（與 18.12 實驗五相同）：私鑰公開在書裡，只能用來練習
CA_PEM = """\
-----BEGIN CERTIFICATE-----
MIIB3zCCAYagAwIBAgIUaoE8iEfB1CNLQNTAf2oroRN03WowCgYIKoZIzj0EAwIw
OzEYMBYGA1UECgwPU2hlbmdzaGVuZyBMaXZlMR8wHQYDVQQDDBZTaGVuZ3NoZW5n
IEludGVybmFsIENBMCAXDTI2MDEwMTAwMDAwMFoYDzIxMjUxMjMxMjM1OTU5WjA7
MRgwFgYDVQQKDA9TaGVuZ3NoZW5nIExpdmUxHzAdBgNVBAMMFlNoZW5nc2hlbmcg
SW50ZXJuYWwgQ0EwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAATwPZRjZqfOFbOy
fpDUiKYTmwq+miK0OHMXlZvkADJeaDx3OZMqJ1aPunfiMYywn5kbepFGufdrCMIL
f4qvVjsOo2YwZDAdBgNVHQ4EFgQUuWH4ZeBEvV4n6/Wo/Fz9CO3lG1wwHwYDVR0j
BBgwFoAUuWH4ZeBEvV4n6/Wo/Fz9CO3lG1wwEgYDVR0TAQH/BAgwBgEB/wIBADAO
BgNVHQ8BAf8EBAMCAQYwCgYIKoZIzj0EAwIDRwAwRAIgN56KWi5fEKRTbRK02fb9
zFYFGZNME68PMtnaJyd65xkCIC6oWHacJxiShe8GZplVZFaVfLZpQ4tnM4NYHNXJ
gbCZ
-----END CERTIFICATE-----
"""
SERVER_PEM = """\
-----BEGIN CERTIFICATE-----
MIIB6DCCAY6gAwIBAgICGAEwCgYIKoZIzj0EAwIwOzEYMBYGA1UECgwPU2hlbmdz
aGVuZyBMaXZlMR8wHQYDVQQDDBZTaGVuZ3NoZW5nIEludGVybmFsIENBMCAXDTI2
MDEwMTAwMDAwMFoYDzIxMjUxMjMxMjM1OTU5WjAhMR8wHQYDVQQDDBZvcHMuc2hl
bmdzaGVuZy5leGFtcGxlMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEGihwJ4Xd
VdO1fwBlwdzAIg7Vs4/wGTy5JzGa84nkGS9N2bclSrQOISLrHBTSDJnZXR13NpzH
+10F5CXHeVQYmaOBmTCBljAMBgNVHRMBAf8EAjAAMA4GA1UdDwEB/wQEAwIHgDAT
BgNVHSUEDDAKBggrBgEFBQcDATAhBgNVHREEGjAYghZvcHMuc2hlbmdzaGVuZy5l
eGFtcGxlMB0GA1UdDgQWBBTzbUhtoOMMVrggXdQ1b5zc+udv8zAfBgNVHSMEGDAW
gBS5Yfhl4ES9Xifr9aj8XP0I7eUbXDAKBggqhkjOPQQDAgNIADBFAiArfDW7ewfm
OV9lnop0ECH5+Yjb7fZ0clOSNV/NIm8PCgIhALCQMoVT8/MoQd03s/vufhHfgUjm
x2/wTAAF1X84DSmh
-----END CERTIFICATE-----
"""
SERVER_KEY = """\
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg9zjtyOUic/NWRadm
M20RLyLvvkMUX1Fqgq3nBnQWB02hRANCAAQaKHAnhd1V07V/AGXB3MAiDtWzj/AZ
PLknMZrzieQZL03ZtyVKtA4hIuscFNIMmdldHXc2nMf7XQXkJcd5VBiZ
-----END PRIVATE KEY-----
"""

CONTENT = {20: "change_cipher_spec", 21: "alert", 22: "handshake", 23: "application_data"}
HS = {1: "ClientHello", 2: "ServerHello"}


def records(data: bytes):
    """把一段 bytes 切成 TLS record，回傳 (type, length, payload)。"""
    p = 0
    while p < len(data):
        ctype, _ver, length = struct.unpack_from("!BHH", data, p)
        yield ctype, length, data[p + 5:p + 5 + length]
        p += 5 + length


def describe(payload: bytes) -> str:
    """明文的 handshake record：讀出訊息類型；ServerHello 再讀出選定的版本與 group。"""
    name = HS.get(payload[0], f"type {payload[0]}")
    if payload[0] != 2:
        return name
    p = 4 + 2 + 32                             # header、legacy_version、random
    p += 1 + payload[p]                        # legacy_session_id_echo
    suite = struct.unpack_from("!H", payload, p)[0]
    p += 3                                     # cipher_suite＋compression
    end, p, notes = len(payload), p + 2, [f"suite=0x{suite:04x}"]
    while p < end:
        etype, elen = struct.unpack_from("!HH", payload, p)
        if etype == 43:
            notes.append(f"supported_versions=0x{struct.unpack_from('!H', payload, p + 4)[0]:04x}")
        if etype == 51:
            notes.append(f"key_share group=0x{struct.unpack_from('!H', payload, p + 4)[0]:04x}")
        p += 4 + elen
    return f"{name}（{', '.join(notes)}）"


def show(direction: str, data: bytes) -> list[int]:
    types = []
    for ctype, length, payload in records(data):
        label = describe(payload) if ctype == 22 else "（加密，看不出內容）" if ctype == 23 else ""
        print(f"  {direction} record {CONTENT[ctype]:<18} {length:>5} bytes {label}")
        types.append(ctype)
    return types


tmp = tempfile.mkdtemp()
paths = {}
for name, text in [("ca", CA_PEM), ("cert", SERVER_PEM), ("key", SERVER_KEY)]:
    paths[name] = os.path.join(tmp, name + ".pem")
    with open(paths[name], "w") as fh:
        fh.write(text)

sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
sctx.load_cert_chain(paths["cert"], paths["key"])
sctx.set_alpn_protocols(["h2", "http/1.1"])
cctx = ssl.create_default_context(cafile=paths["ca"])
cctx.set_alpn_protocols(["h2", "http/1.1"])

# 兩端各有一對 MemoryBIO；我們自己當「網路」，把一端送出的 bytes 搬到另一端
c_in, c_out, s_in, s_out = (ssl.MemoryBIO() for _ in range(4))
client = cctx.wrap_bio(c_in, c_out, server_hostname="ops.shengsheng.example")
server = sctx.wrap_bio(s_in, s_out, server_side=True)


def step(obj):
    try:
        obj.do_handshake()
        return True
    except ssl.SSLWantReadError:
        return False


flights = []
step(client)
print("第 1 趟 client → server")
flights.append(show("C→S", wire := c_out.read()))
s_in.write(wire)
step(server)
print("第 2 趟 server → client")
flights.append(show("S→C", wire := s_out.read()))
c_in.write(wire)
assert step(client)                            # client 收到 Finished 就完成交握
client.write(b"GET /api/export HTTP/1.1\r\nHost: ops.shengsheng.example\r\n\r\n")
print("第 3 趟 client → server（Finished 與第一個請求一起送）")
flights.append(show("C→S", wire := c_out.read()))
s_in.write(wire)
assert step(server)
request = server.read(4096)
print("第 4 趟 server → client（NewSessionTicket）")
flights.append(show("S→C", s_out.read()))
print("server 解密出的請求：", request.split(b"\r\n")[0].decode())
print("協商結果：", client.version(), client.cipher()[0], "ALPN =", client.selected_alpn_protocol())
assert flights[1][0] == 22 and set(flights[1][1:]) <= {20, 23}   # ServerHello 之後全部加密
```

```text
第 1 趟 client → server
  C→S record handshake           1540 bytes ClientHello
第 2 趟 server → client
  S→C record handshake           1210 bytes ServerHello（suite=0x1302, supported_versions=0x0304, key_share group=0x11ec）
  S→C record change_cipher_spec     1 bytes 
  S→C record application_data      32 bytes （加密，看不出內容）
  S→C record application_data     522 bytes （加密，看不出內容）
  S→C record application_data      97 bytes （加密，看不出內容）
  S→C record application_data      69 bytes （加密，看不出內容）
第 3 趟 client → server（Finished 與第一個請求一起送）
  C→S record change_cipher_spec     1 bytes 
  C→S record application_data      69 bytes （加密，看不出內容）
  C→S record application_data      75 bytes （加密，看不出內容）
第 4 趟 server → client（NewSessionTicket）
  S→C record application_data     250 bytes （加密，看不出內容）
  S→C record application_data     266 bytes （加密，看不出內容）
server 解密出的請求： GET /api/export HTTP/1.1
協商結果： TLSv1.3 TLS_AES_256_GCM_SHA384 ALPN = h2
```

逐趟對照 18.4 節的時序圖。第 1 趟只有 ClientHello。第 2 趟是 server 的整個 flight：明文的 ServerHello（1,210 bytes，大部分是 ML-KEM 的密文；解析出 suite 0x1302、版本 0x0304、group 0x11ec）、1 byte 的假 change_cipher_spec，接著四個外層都是 application_data 的加密 record。從長度可以推出它們依序是 EncryptedExtensions（32 bytes，只有 ALPN）、Certificate（522 bytes，含一張約 490 bytes 的憑證）、CertificateVerify（約 96 bytes，一個 ECDSA 簽章）、Finished（69 bytes：SHA-384 套件的 48 bytes HMAC，加上 4 bytes handshake header、1 byte 真正類型與 16 bytes AEAD tag）。這就是「1.3 的憑證是加密的」的實際樣子：程式只能從長度猜。

第 3 趟，client 送出 change_cipher_spec 與 Finished，並在**同一趟**送出 75 bytes 的加密 HTTP 請求。第 4 趟是交握後的兩張 NewSessionTicket。CertificateVerify 與票券的長度每次可能差幾個 bytes（ECDSA 簽章的 DER 長度不固定），record 的數量與順序則每次相同。

### 實驗三：Python `ssl` 的預設值

寫任何 TLS client 之前，先知道「什麼都不設」時 Python 幫你做了什麼。下面比較三種建立 context 的方式：`create_default_context()`（建議）、`SSLContext(PROTOCOL_TLS_SERVER)`（給 server 用）、`SSLContext(PROTOCOL_TLS_CLIENT)`（不經過 `create_default_context` 的 client）。

```python
import ssl

client = ssl.create_default_context()          # 給「連出去」用的 context
server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)  # 給「接受連線」用的 context
raw = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # 不經 create_default_context 的 client context


def flags(value, enum_cls, names):
    return [n for n in names if value & getattr(enum_cls, n)]


print(ssl.OPENSSL_VERSION)
print(f"{'':18}{'default client':>18}{'TLS_SERVER':>19}{'TLS_CLIENT':>19}")
rows = [
    ("minimum_version", lambda c: c.minimum_version.name),
    ("maximum_version", lambda c: c.maximum_version.name),
    ("verify_mode", lambda c: c.verify_mode.name),
    ("check_hostname", lambda c: str(c.check_hostname)),
    ("CA certs loaded", lambda c: str(c.cert_store_stats()["x509_ca"])),
]
for label, get in rows:
    print(f"{label:<18}{get(client):>19}{get(server):>19}{get(raw):>19}")

print("verify_flags：", flags(client.verify_flags, ssl.VerifyFlags,
      ["VERIFY_X509_STRICT", "VERIFY_X509_PARTIAL_CHAIN", "VERIFY_X509_TRUSTED_FIRST", "VERIFY_CRL_CHECK_LEAF"]))
print("options：", flags(client.options, ssl.Options,
      ["OP_NO_SSLv3", "OP_NO_COMPRESSION", "OP_NO_TICKET", "OP_ENABLE_MIDDLEBOX_COMPAT"]))
tls13 = [c["name"] for c in client.get_ciphers() if c["protocol"] == "TLSv1.3"]
print("TLS 1.3 cipher suites：", tls13)

# 想「暫時關掉驗證」？順序錯了 Python 直接拒絕，提醒你這是兩個獨立的保護
try:
    client.verify_mode = ssl.CERT_NONE
except ValueError as exc:
    print("先關 verify_mode：ValueError:", exc)

# 正確的收緊方式：要求 TLS 1.3，並保留所有驗證
strict = ssl.create_default_context()
strict.minimum_version = ssl.TLSVersion.TLSv1_3
print("收緊後 minimum_version：", strict.minimum_version.name, "| verify_mode：", strict.verify_mode.name)
assert client.verify_mode == ssl.CERT_REQUIRED and client.check_hostname
assert server.verify_mode == ssl.CERT_NONE   # server 預設不要求 client 憑證（不是 mTLS）
```

```text
OpenSSL 3.6.3 9 Jun 2026
                      default client         TLS_SERVER         TLS_CLIENT
minimum_version               TLSv1_2            TLSv1_2            TLSv1_2
maximum_version     MAXIMUM_SUPPORTED  MAXIMUM_SUPPORTED  MAXIMUM_SUPPORTED
verify_mode             CERT_REQUIRED          CERT_NONE      CERT_REQUIRED
check_hostname                   True              False               True
CA certs loaded                   128                  0                  0
verify_flags： ['VERIFY_X509_STRICT', 'VERIFY_X509_PARTIAL_CHAIN', 'VERIFY_X509_TRUSTED_FIRST']
options： ['OP_NO_SSLv3', 'OP_NO_COMPRESSION', 'OP_ENABLE_MIDDLEBOX_COMPAT']
TLS 1.3 cipher suites： ['TLS_AES_256_GCM_SHA384', 'TLS_CHACHA20_POLY1305_SHA256', 'TLS_AES_128_GCM_SHA256']
先關 verify_mode：ValueError: Cannot set verify_mode to CERT_NONE when check_hostname is enabled.
收緊後 minimum_version： TLSv1_3 | verify_mode： CERT_REQUIRED
```

表格的重點有三個。第一，最低版本是 TLS 1.2、最高是本機支援的 1.3，所以會優先協商 1.3、仍接受 1.2。第二，`verify_mode` 與 `check_hostname` 對應 18.7 節的鏈驗證與名稱比對，預設 client 兩者都開；server context 預設 `CERT_NONE`，要做 mTLS 必須自己改成 `CERT_REQUIRED`。第三，`create_default_context()` 載入了系統的 CA（數量依作業系統與 Python 安裝方式而定），直接用 `SSLContext(PROTOCOL_TLS_CLIENT)` 一樣會驗證，信任庫卻是空的，任何連線都會失敗，很多人就是在這裡「為了讓它能跑」而關掉驗證。

`verify_flags` 裡的 `VERIFY_X509_STRICT` 與 `VERIFY_X509_PARTIAL_CHAIN` 是 Python 3.13 起的預設；`OP_ENABLE_MIDDLEBOX_COMPAT` 就是實驗二那個假 change_cipher_spec 的來源。`ValueError` 是刻意的設計：`check_hostname` 還開著時不能把 `verify_mode` 設成 `CERT_NONE`，逼你意識到自己正在一次關掉兩道保護。正確的收緊方向是最後一行：提高最低版本，保留所有驗證。

### 實驗四：用玩具 PKI 模擬憑證驗證

真實的 X.509 解析需要 ASN.1，標準函式庫沒有提供。為了看清楚 18.7 節的七個步驟，這個實驗用 dataclass 表示憑證，用一個只有約 100 bit 的「玩具 RSA」做真正的簽章與驗證（數學和真的一樣，只是金鑰小到毫無安全性），再依序實作建鏈、簽章、CA 限制、效期、用途、名稱與撤銷的檢查，並跑過八種情境與 wildcard 規則。

```python
import hashlib
import ipaddress
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

E = 65537


@dataclass
class ToyKey:
    """玩具 RSA：數學和真的一樣，但金鑰只有約 100 bit，完全不安全，只為了看懂流程。"""
    p: int
    q: int

    @property
    def n(self) -> int:
        return self.p * self.q

    def sign(self, data: bytes) -> int:
        d = pow(E, -1, (self.p - 1) * (self.q - 1))
        return pow(int.from_bytes(hashlib.sha256(data).digest(), "big") % self.n, d, self.n)


def rsa_verify(n: int, data: bytes, sig: int) -> bool:
    return pow(sig, E, n) == int.from_bytes(hashlib.sha256(data).digest(), "big") % n


@dataclass
class Cert:
    subject: str
    issuer: str
    serial: int
    not_before: datetime
    not_after: datetime
    pub_n: int
    is_ca: bool = False
    sans: list = field(default_factory=list)
    eku: tuple = ()
    sig: int = 0

    def tbs(self) -> bytes:                    # to-be-signed：除了簽章以外的所有欄位
        d = {k: v for k, v in self.__dict__.items() if k != "sig"}
        return json.dumps(d, default=str, sort_keys=True).encode()


def issue(key: ToyKey, cert: Cert) -> Cert:
    cert.sig = key.sign(cert.tbs())
    return cert


def name_matches(pattern: str, host: str) -> bool:
    pattern, host = pattern.lower().rstrip("."), host.lower().rstrip(".")
    if pattern.startswith("*."):
        rest = pattern[2:]
        if rest.count(".") < 1:                # 拒絕 *.example 這種過寬的 wildcard
            return False
        label, _, tail = host.partition(".")
        return bool(label) and tail == rest    # * 只代表最左邊「恰好一個」label
    return "*" not in pattern and pattern == host


def check_name(cert: Cert, host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)        # IP 只能比對 IP 型 SAN，不能比 DNS 名稱
        return any(s == f"IP:{ip}" for s in cert.sans)
    except ValueError:
        return any(name_matches(s[4:], host) for s in cert.sans if s.startswith("DNS:"))


def verify(chain_sent: list, host: str, now: datetime, trust: dict, revoked: set) -> str:
    leaf, pool = chain_sent[0], {c.subject: c for c in chain_sent[1:]}
    path = [leaf]
    while path[-1].issuer not in trust:        # 1. 往上找發行者，直到信任錨
        parent = pool.get(path[-1].issuer)
        if parent is None or len(path) > 5:
            return "unable to get local issuer certificate"
        path.append(parent)
    path.append(trust[path[-1].issuer])
    for child, parent in zip(path, path[1:]):  # 2. 每一層的簽章都要用上一層的公鑰驗過
        if not rsa_verify(parent.pub_n, child.tbs(), child.sig):
            return f"certificate signature failure（{child.subject}）"
        if not parent.is_ca:                   # 3. 發行者必須是 CA
            return f"invalid CA certificate（{parent.subject}）"
    for c in path:                             # 4. 每一張都要在效期內
        if now < c.not_before:
            return f"certificate is not yet valid（{c.subject}）"
        if now > c.not_after:
            return f"certificate has expired（{c.subject}）"
    if "serverAuth" not in leaf.eku:           # 5. 用途要對
        return "unsupported certificate purpose"
    if not check_name(leaf, host):             # 6. 名字要對
        return f"Hostname mismatch（{host}）"
    if (leaf.issuer, leaf.serial) in revoked:  # 7. 沒被撤銷（這裡用一份 CRL 集合模擬）
        return "certificate revoked"
    return "OK：" + " → ".join(c.subject for c in path)


utc = lambda *a: datetime(*a, tzinfo=timezone.utc)
root_k, inter_k, evil_k = ToyKey(1000000000000037, 3000000000000037), \
    ToyKey(5000000000000023, 7000000000000037), ToyKey(9000000000000007, 2000000000000021)
root = issue(root_k, Cert("Example Root CA R1", "Example Root CA R1", 1, utc(2020, 1, 1), utc(2045, 1, 1), root_k.n, True))
inter = issue(root_k, Cert("Example Issuing CA 2", "Example Root CA R1", 2, utc(2024, 1, 1), utc(2030, 1, 1), inter_k.n, True))
start = utc(2026, 7, 1)
leaf = issue(inter_k, Cert("api.shengsheng.example", "Example Issuing CA 2", 0x5A01, start,
                           start + timedelta(days=180), 0, sans=["DNS:api.shengsheng.example"], eku=("serverAuth",)))
# leaf 的公鑰（pub_n）在這裡用不到：它只在交握的 CertificateVerify 用來驗證 server 的簽章
fake_inter = issue(evil_k, Cert("Example Issuing CA 2", "Example Root CA R1", 2, utc(2024, 1, 1), utc(2030, 1, 1), evil_k.n, True))
fake_leaf = issue(evil_k, Cert("api.shengsheng.example", "Example Issuing CA 2", 0x5A02, start,
                               start + timedelta(days=180), 0, sans=["DNS:api.shengsheng.example"], eku=("serverAuth",)))
trust, now = {"Example Root CA R1": root}, utc(2026, 10, 2)
cases = [
    ("正常：leaf＋中間憑證", [leaf, inter], "api.shengsheng.example", now, set()),
    ("server 漏送中間憑證", [leaf], "api.shengsheng.example", now, set()),
    ("名字不符", [leaf, inter], "www.shengsheng.example", now, set()),
    ("用 IP 連線", [leaf, inter], "203.0.113.80", now, set()),
    ("client 時鐘停在 2025 年", [leaf, inter], "api.shengsheng.example", utc(2025, 6, 1), set()),
    ("過了 180 天效期", [leaf, inter], "api.shengsheng.example", utc(2027, 1, 15), set()),
    ("偽造的同名中間 CA", [fake_leaf, fake_inter], "api.shengsheng.example", now, set()),
    ("已被撤銷", [leaf, inter], "api.shengsheng.example", now, {("Example Issuing CA 2", 0x5A01)}),
]
for label, chain, host, t, crl in cases:
    print(f"[{label}] {verify(chain, host, t, trust, crl)}")

print("\nwildcard 規則：*.shengsheng.example")
for host in ["www.shengsheng.example", "WWW.Shengsheng.Example.", "shengsheng.example",
             "a.b.shengsheng.example", "evilshengsheng.example"]:
    print(f"  {host:<26} {'符合' if name_matches('*.shengsheng.example', host) else '不符合'}")
print("  *.example 對 shengsheng.example：", "符合" if name_matches("*.example", "shengsheng.example") else "不符合")
assert verify([leaf, inter], "api.shengsheng.example", now, trust, set()).startswith("OK")
assert not name_matches("*.shengsheng.example", "a.b.shengsheng.example")
```

```text
[正常：leaf＋中間憑證] OK：api.shengsheng.example → Example Issuing CA 2 → Example Root CA R1
[server 漏送中間憑證] unable to get local issuer certificate
[名字不符] Hostname mismatch（www.shengsheng.example）
[用 IP 連線] Hostname mismatch（203.0.113.80）
[client 時鐘停在 2025 年] certificate is not yet valid（api.shengsheng.example）
[過了 180 天效期] certificate has expired（api.shengsheng.example）
[偽造的同名中間 CA] certificate signature failure（Example Issuing CA 2）
[已被撤銷] certificate revoked

wildcard 規則：*.shengsheng.example
  www.shengsheng.example     符合
  WWW.Shengsheng.Example.    符合
  shengsheng.example         不符合
  a.b.shengsheng.example     不符合
  evilshengsheng.example     不符合
  *.example 對 shengsheng.example： 不符合
```

八種情境各對應一個檢查步驟。「漏送中間憑證」在第 ① 步就找不到 issuer，錯誤字串和 OpenSSL 一樣，也和故事裡小晴看到的相同：故事中缺的是信任錨，這裡缺的是中間憑證，兩者都是「往上找不到可信任的發行者」。「名字不符」與「用 IP 連線」在第 ⑥ 步失敗，「時鐘停在 2025 年」與「過了效期」在第 ④ 步失敗。

「偽造的同名中間 CA」最值得細看：攻擊者做了一張 subject 也叫 `Example Issuing CA 2` 的憑證，用它簽了 `api.shengsheng.example`。名字全部對得上，leaf 的簽章也對，但偽造的中間 CA 宣稱由 root 簽發，用 root 的公鑰一驗就失敗：信任來自**簽章的數學**，不是名字。下半部的 wildcard 測試對應 18.7 節的表格，`evilshengsheng.example` 這種後綴剛好相同的名字也不會被誤判。這個模擬只為了理解流程，正式程式一律交給 `ssl` 模組驗證。

### 實驗五：在 127.0.0.1 上重現故事，並用正確方式修好

最後一個實驗啟動真正的 TLS server（一般版與 mTLS 版），用內嵌的測試 PKI 重現故事裡的錯誤，並逐一走過正確的修法、名稱不符、session resumption 與 mTLS。

```python
import os
import socket
import ssl
import tempfile
import threading

# 本書專用的測試 PKI：一張內部 CA、ops 的 server 憑證、小晴筆電的 client 憑證。
# 私鑰公開在書裡，所以只能用在 127.0.0.1 的練習；效期設到 2125 年，是為了讓範例多年後還能跑。
CA_PEM = """\
-----BEGIN CERTIFICATE-----
MIIB3zCCAYagAwIBAgIUaoE8iEfB1CNLQNTAf2oroRN03WowCgYIKoZIzj0EAwIw
OzEYMBYGA1UECgwPU2hlbmdzaGVuZyBMaXZlMR8wHQYDVQQDDBZTaGVuZ3NoZW5n
IEludGVybmFsIENBMCAXDTI2MDEwMTAwMDAwMFoYDzIxMjUxMjMxMjM1OTU5WjA7
MRgwFgYDVQQKDA9TaGVuZ3NoZW5nIExpdmUxHzAdBgNVBAMMFlNoZW5nc2hlbmcg
SW50ZXJuYWwgQ0EwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAATwPZRjZqfOFbOy
fpDUiKYTmwq+miK0OHMXlZvkADJeaDx3OZMqJ1aPunfiMYywn5kbepFGufdrCMIL
f4qvVjsOo2YwZDAdBgNVHQ4EFgQUuWH4ZeBEvV4n6/Wo/Fz9CO3lG1wwHwYDVR0j
BBgwFoAUuWH4ZeBEvV4n6/Wo/Fz9CO3lG1wwEgYDVR0TAQH/BAgwBgEB/wIBADAO
BgNVHQ8BAf8EBAMCAQYwCgYIKoZIzj0EAwIDRwAwRAIgN56KWi5fEKRTbRK02fb9
zFYFGZNME68PMtnaJyd65xkCIC6oWHacJxiShe8GZplVZFaVfLZpQ4tnM4NYHNXJ
gbCZ
-----END CERTIFICATE-----
"""
SERVER_PEM = """\
-----BEGIN CERTIFICATE-----
MIIB6DCCAY6gAwIBAgICGAEwCgYIKoZIzj0EAwIwOzEYMBYGA1UECgwPU2hlbmdz
aGVuZyBMaXZlMR8wHQYDVQQDDBZTaGVuZ3NoZW5nIEludGVybmFsIENBMCAXDTI2
MDEwMTAwMDAwMFoYDzIxMjUxMjMxMjM1OTU5WjAhMR8wHQYDVQQDDBZvcHMuc2hl
bmdzaGVuZy5leGFtcGxlMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEGihwJ4Xd
VdO1fwBlwdzAIg7Vs4/wGTy5JzGa84nkGS9N2bclSrQOISLrHBTSDJnZXR13NpzH
+10F5CXHeVQYmaOBmTCBljAMBgNVHRMBAf8EAjAAMA4GA1UdDwEB/wQEAwIHgDAT
BgNVHSUEDDAKBggrBgEFBQcDATAhBgNVHREEGjAYghZvcHMuc2hlbmdzaGVuZy5l
eGFtcGxlMB0GA1UdDgQWBBTzbUhtoOMMVrggXdQ1b5zc+udv8zAfBgNVHSMEGDAW
gBS5Yfhl4ES9Xifr9aj8XP0I7eUbXDAKBggqhkjOPQQDAgNIADBFAiArfDW7ewfm
OV9lnop0ECH5+Yjb7fZ0clOSNV/NIm8PCgIhALCQMoVT8/MoQd03s/vufhHfgUjm
x2/wTAAF1X84DSmh
-----END CERTIFICATE-----
"""
SERVER_KEY = """\
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg9zjtyOUic/NWRadm
M20RLyLvvkMUX1Fqgq3nBnQWB02hRANCAAQaKHAnhd1V07V/AGXB3MAiDtWzj/AZ
PLknMZrzieQZL03ZtyVKtA4hIuscFNIMmdldHXc2nMf7XQXkJcd5VBiZ
-----END PRIVATE KEY-----
"""
CLIENT_PEM = """\
-----BEGIN CERTIFICATE-----
MIIB1jCCAXygAwIBAgICGAIwCgYIKoZIzj0EAwIwOzEYMBYGA1UECgwPU2hlbmdz
aGVuZyBMaXZlMR8wHQYDVQQDDBZTaGVuZ3NoZW5nIEludGVybmFsIENBMCAXDTI2
MDEwMTAwMDAwMFoYDzIxMjUxMjMxMjM1OTU5WjA0MRgwFgYDVQQKDA9TaGVuZ3No
ZW5nIExpdmUxGDAWBgNVBAMMD3hpYW9xaW5nLWxhcHRvcDBZMBMGByqGSM49AgEG
CCqGSM49AwEHA0IABOc27MgTv1/pb5uxcQQ+74FeWT9CCwypcRBxe9CBv/kaxuF1
7uUtCI4xoep3eI/sFZdk4HrDPhGoGQt8CAWcCqKjdTBzMAwGA1UdEwEB/wQCMAAw
DgYDVR0PAQH/BAQDAgeAMBMGA1UdJQQMMAoGCCsGAQUFBwMCMB0GA1UdDgQWBBSP
gQmTuuvvLt1u70lN/9VqqwnplzAfBgNVHSMEGDAWgBS5Yfhl4ES9Xifr9aj8XP0I
7eUbXDAKBggqhkjOPQQDAgNIADBFAiBOGFHXGjkwmFqvTwbuDmZbC5iUGlsDfBRM
bio0jLq1EAIhANKsG/unBjb9I9usPpSr45Htw5XGaPUTvCdnrtvM7rOF
-----END CERTIFICATE-----
"""
CLIENT_KEY = """\
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg8axjvKVpBnPCK52j
FDX+iY8UhQR0nz3782iLRgAeurehRANCAATnNuzIE79f6W+bsXEEPu+BXlk/QgsM
qXEQcXvQgb/5Gsbhde7lLQiOMaHqd3iP7BWXZOB6wz4RqBkLfAgFnAqi
-----END PRIVATE KEY-----
"""
TMP = tempfile.mkdtemp()


def save(name: str, text: str) -> str:
    path = os.path.join(TMP, name)
    with open(path, "w") as fh:
        fh.write(text)
    return path


ca_file = save("ca.pem", CA_PEM)
srv_cert, srv_key = save("srv.pem", SERVER_PEM), save("srv.key", SERVER_KEY)
cli_cert, cli_key = save("cli.pem", CLIENT_PEM), save("cli.key", CLIENT_KEY)


def start_server(require_client_cert: bool):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(srv_cert, srv_key)
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    seen = []                                  # server 看到的 SNI 與 client 憑證

    def on_sni(sslobj, name, _ctx):            # 在 ClientHello 到達時被呼叫，可用來挑憑證
        seen.append(f"SNI={name}")

    ctx.sni_callback = on_sni
    if require_client_cert:                    # mTLS：要求並驗證 client 憑證
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_verify_locations(ca_file)
    lsock = socket.create_server(("127.0.0.1", 0))
    lsock.settimeout(0.1)                      # 定期醒來檢查 stop，讓 thread 能乾淨結束
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            try:
                raw, _ = lsock.accept()
            except TimeoutError:
                continue
            try:
                with ctx.wrap_socket(raw, server_side=True) as tls:
                    peer = tls.getpeercert()
                    if peer:
                        cn = dict(x[0] for x in peer["subject"])["commonName"]
                        seen.append(f"client 憑證 CN={cn}")
                    tls.sendall(f"hello {tls.version()} alpn={tls.selected_alpn_protocol()}".encode())
            except (ssl.SSLError, OSError) as exc:
                seen.append(f"server 端交握失敗：{exc.reason if isinstance(exc, ssl.SSLError) else exc}")

    t = threading.Thread(target=loop, daemon=True)
    t.start()

    def shutdown():
        stop.set()
        t.join()
        lsock.close()

    port = lsock.getsockname()[1]
    return port, shutdown, seen


def call(port, ctx, name, session=None):
    with socket.create_connection(("127.0.0.1", port), timeout=2) as raw:
        with ctx.wrap_socket(raw, server_hostname=name, session=session) as tls:
            body = tls.recv(200).decode()      # 讀資料時，TLS 1.3 的 session ticket 也一起被處理
            info = {"version": tls.version(), "cipher": tls.cipher()[0],
                    "alpn": tls.selected_alpn_protocol(), "reused": tls.session_reused,
                    "san": tls.getpeercert().get("subjectAltName"),
                    "notAfter": tls.getpeercert().get("notAfter")}
            return info, body, tls.session


def client_ctx(trust_internal_ca: bool):
    ctx = ssl.create_default_context(cafile=ca_file if trust_internal_ca else None)
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    return ctx


port, shutdown, seen = start_server(require_client_cert=False)
print("【A】系統預設信任庫，連 ops.shengsheng.example")
try:
    call(port, client_ctx(False), "ops.shengsheng.example")
except ssl.SSLCertVerificationError as exc:
    print("  失敗：", exc.verify_message)

print("【B】改信任內部 CA")
trusted = client_ctx(True)                     # session 只能在同一個 context 裡重用
info, body, sess = call(port, trusted, "ops.shengsheng.example")
print("  成功：", info["version"], info["cipher"], "ALPN =", info["alpn"])
print("  憑證：", info["san"], "到期", info["notAfter"])
print("  server 回覆：", body)

print("【C】名字不對：用同一張憑證連 api.shengsheng.example")
try:
    call(port, trusted, "api.shengsheng.example")
except ssl.SSLCertVerificationError as exc:
    print("  失敗：", exc.verify_message)

print("【D】帶著上次的 session ticket 重連")
info2, _, _ = call(port, trusted, "ops.shengsheng.example", session=sess)
print("  session_reused =", info2["reused"])
assert info["version"] == "TLSv1.3" and info2["reused"]
shutdown()
print("  server 紀錄：", seen)

port, shutdown, seen = start_server(require_client_cert=True)
print("【E】mTLS：client 沒帶憑證")
try:
    call(port, client_ctx(True), "ops.shengsheng.example")
except (ssl.SSLError, ConnectionResetError) as exc:
    print("  client 在讀資料時才失敗：", getattr(exc, "reason", exc))

print("【F】mTLS：client 帶上小晴筆電的憑證")
ctx = client_ctx(True)
ctx.load_cert_chain(cli_cert, cli_key)
_, body, _ = call(port, ctx, "ops.shengsheng.example")
print("  server 回覆：", body)
shutdown()
print("  server 紀錄：", seen)
assert any("CN=xiaoqing-laptop" in s for s in seen)
```

```text
【A】系統預設信任庫，連 ops.shengsheng.example
  失敗： unable to get local issuer certificate
【B】改信任內部 CA
  成功： TLSv1.3 TLS_AES_256_GCM_SHA384 ALPN = h2
  憑證： (('DNS', 'ops.shengsheng.example'),) 到期 Dec 31 23:59:59 2125 GMT
  server 回覆： hello TLSv1.3 alpn=h2
【C】名字不對：用同一張憑證連 api.shengsheng.example
  失敗： Hostname mismatch, certificate is not valid for 'api.shengsheng.example'.
【D】帶著上次的 session ticket 重連
  session_reused = True
  server 紀錄： ['SNI=ops.shengsheng.example', 'server 端交握失敗：TLSV1_ALERT_UNKNOWN_CA', 'SNI=ops.shengsheng.example', 'SNI=api.shengsheng.example', 'server 端交握失敗：SSLV3_ALERT_BAD_CERTIFICATE', 'SNI=ops.shengsheng.example']
【E】mTLS：client 沒帶憑證
  client 在讀資料時才失敗： TLSV13_ALERT_CERTIFICATE_REQUIRED
【F】mTLS：client 帶上小晴筆電的憑證
  server 回覆： hello TLSv1.3 alpn=h2
  server 紀錄： ['SNI=ops.shengsheng.example', 'server 端交握失敗：PEER_DID_NOT_RETURN_A_CERTIFICATE', 'SNI=ops.shengsheng.example', 'client 憑證 CN=xiaoqing-laptop']
```

【A】是故事的重現：預設信任庫裡沒有 Internal CA，錯誤和小晴看到的一樣；server 紀錄同時出現 `TLSV1_ALERT_UNKNOWN_CA`，因為 client 驗證失敗時會送 alert 說明原因，server 端的 log 也能幫你判斷是哪一邊的問題。【B】是正確修法：`cafile=` 只是**多信任一張 CA**，名稱、效期、簽章檢查一項都沒關，協商出 TLS 1.3 與 ALPN `h2`，`getpeercert()` 也拿到 SAN 與到期日。

【C】用同一張憑證連 `api.shengsheng.example`：鏈驗證全部通過，只有名稱比對失敗，這正是 `_create_unverified_context()` 會一併放掉的情況。【D】用【B】的 session 重連，`session_reused = True`，代表沒有重新驗證憑證鏈；Python 要求 session 只能在同一個 context 重用，而且 1.3 的票券在交握後才送，要先讀過一次資料，`tls.session` 才有票券。server 紀錄的 `SNI=…` 來自 sni_callback，真實的 server 會在這裡依名稱挑憑證。

【E】與【F】是 mTLS。【E】沒帶憑證，錯誤不在 `wrap_socket()`，而在之後的 `recv()`：如 18.10 節所說，1.3 的 client 送出 Finished 就認為交握完成，server 驗證失敗後才送 `certificate_required` alert。【F】載入筆電憑證後，server 讀出 `CN=xiaoqing-laptop`，這就是後端可以拿來做授權的機器身分。整個實驗沒有關掉任何驗證，所有錯誤都靠調整信任庫、名稱或憑證來修，這正是 Rita 退回 PR 時想說的話。

## 18.13 在工作上怎麼用

PR 修好之後，Rita 和阿德把這次討論整理成團隊的 TLS 檢查清單，依角色分成幾段。

**後端工程師：寫 TLS client 的三條規則。** 第一，永遠從 `ssl.create_default_context()` 開始（requests、httpx 預設也會驗證），私有 CA 用 `cafile=` 或 `load_verify_locations()` 加上去，絕不使用 `_create_unverified_context()`、`verify=False` 或 `CERT_NONE`。第二，用 `server_hostname` 傳正確的主機名稱，不要拿 IP 去連再關掉名稱檢查。第三，程式碼審查時搜尋上述關鍵字，出現在非測試程式裡就要有書面理由。需要在測試環境解密流量時，用 `SSLContext.keylog_filename`（或 `SSLKEYLOGFILE`）輸出金鑰給 Wireshark，而不是關掉驗證；金鑰檔只留在自己的測試機，用完刪除。

**SRE：用 openssl 在一分鐘內回答「這個端點的 TLS 正常嗎」。** 下面是對本書測試 server（實驗五的憑證，在本機用 `openssl s_server` 啟動）執行的實際輸出，對真實服務把 `-connect` 換成 `api.shengsheng.example:443` 即可：

```bash
# 簡短模式：版本、cipher、憑證主體、驗證結果、協商出的 group
openssl s_client -connect 127.0.0.1:18443 -servername ops.shengsheng.example \
  -CAfile ca.pem -verify_hostname ops.shengsheng.example -alpn h2 -brief </dev/null
```

```text
Connecting to 127.0.0.1
CONNECTION ESTABLISHED
Protocol version: TLSv1.3
Ciphersuite: TLS_AES_256_GCM_SHA384
Peer certificate: CN=ops.shengsheng.example
Hash used: SHA256
Signature type: ecdsa_secp256r1_sha256
Verification: OK
Verified peername: ops.shengsheng.example
Negotiated TLS1.3 group: X25519MLKEM768
DONE
```

每一行都對應本章的概念：`Protocol version` 來自 supported_versions，`Ciphersuite` 是 ServerHello 選的套件，`Signature type` 是 CertificateVerify 的演算法，`Verification: OK` 與 `Verified peername` 代表鏈驗證與名稱比對都通過，`Negotiated TLS1.3 group` 是 key_share 的結果。拿掉 `-CAfile`、或把 `-verify_hostname` 換成別的名字並加上 `-verify_return_error`，會分別看到 `verify error:num=20:unable to get local issuer certificate` 與 `num=62:hostname mismatch`，和 Python 的錯誤一一對應。沒加 `-verify_hostname` 時 s_client 不檢查名稱（第 3 章），這是值班時最容易誤判的地方。

其他常用的組合：`-tls1_2`／`-tls1_3` 測試特定版本，`-showcerts` 看 server 送了幾張憑證（只有一張就是漏了中間憑證），`-status` 看 OCSP stapling，接 `openssl x509 -noout -dates -ext subjectAltName` 只看效期與 SAN。

TLS 連線失敗時，阿德的判斷流程如下：

```text
 TLS 錯誤
   │
   ├─ 連 TCP 都不通？（curl 停在 Trying、connect timeout）──► 不是 TLS 問題：DNS、路由、防火牆（第 3、6、7 章）
   │
   ├─ 交握中收到 alert
   │     ├─ protocol_version／handshake_failure ──► 版本或 cipher 沒有交集：舊 client？server 只開 1.3？
   │     ├─ no_application_protocol ─────────────► ALPN 沒有交集：gRPC 連到不支援 h2 的 LB？
   │     └─ certificate_required／bad_certificate（client 端看到）──► mTLS：沒帶或帶錯 client 憑證
   │
   └─ client 自己驗證失敗（CERTIFICATE_VERIFY_FAILED）
         ├─ unable to get local issuer ──► 用 -showcerts 數憑證張數
         │     ├─ 只有 leaf ──► server 漏送中間憑證（第 19 章）
         │     └─ 鏈完整 ───► client 不信任這個 root：私有 CA？公司的 TLS 檢查 proxy？
         ├─ hostname mismatch ──► 比對 SAN 與連線名稱：用 IP 連？SNI 沒送？wildcard 跨了兩層？
         ├─ expired／not yet valid ──► 先看 client 時鐘，再看憑證 notAfter
         └─ self-signed certificate ──► 測試憑證跑到 production，或 client 沒設定對應的 CA
```

流程圖的第一刀是「是不是 TLS 的問題」：很多「SSL 錯誤」其實是 TCP 根本沒連上。第二刀分開「server 送 alert」與「client 自己驗證失敗」。每個葉節點的修法不同：修 server 的憑證鏈、修 client 的信任庫、修連線名稱或時鐘，沒有一個是關掉驗證。

**前端工程師：看懂瀏覽器的 TLS 錯誤頁。** `NET::ERR_CERT_AUTHORITY_INVALID` 是鏈驗證失敗，`NET::ERR_CERT_COMMON_NAME_INVALID` 是名稱不符，`NET::ERR_CERT_DATE_INVALID` 是效期（也可能是使用者的時鐘錯了），`ERR_SSL_PROTOCOL_ERROR` 是交握本身失敗。不要教使用者「點進階、繼續前往」。

**資安工程師：設定與稽核。** Rita 的要求是：對外端點只開 TLS 1.2 與 1.3，1.2 只用 ECDHE 加 AEAD 的套件；憑證由 ACME 自動更新並監控到期日（第 19 章）；CDN 的 0-RTT 只放行 GET 與 HEAD；`ops` 改為 mTLS，client 憑證效期短並隨裝置管理系統自動輪替。

**影音工程師：TLS 不只在 HTTPS。** WebRTC 用 DTLS 交換 SRTP 金鑰，交握和本章幾乎相同，但憑證是自簽的，身分改由 signaling 交換的指紋確認（第 36 章）；`wss://` 則是 TLS 上的 WebSocket。

## 18.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| Python 或 curl 報 `unable to get local issuer certificate`，瀏覽器卻正常 | server 漏送中間憑證，瀏覽器靠快取或 AIA 補上 | `openssl s_client -showcerts` 只看到一張憑證 | server 設定改用完整的 fullchain（leaf＋中間），第 19 章 |
| 內部服務在所有 client 都報 `unable to get local issuer` | 憑證由私有 CA 簽發，client 信任庫裡沒有它 | 憑證的 issuer 是內部 CA；s_client 加上 `-CAfile` 就成功 | client 用 `cafile=` 加入私有 CA；不要關掉驗證 |
| `Hostname mismatch` | 用 IP 或別名連線、SAN 沒列這個名字、wildcard 跨兩層或用在 apex | `openssl x509 -noout -ext subjectAltName` 對照連線名稱 | 用正確名稱連線並送 SNI；重新簽發含所需 SAN 的憑證 |
| 一台設備連所有網站都 `certificate is not yet valid` 或 expired | 設備時鐘錯誤（沒有 NTP、電池重置） | 看設備時間；同一網站在其他設備正常 | 修 NTP；嵌入式設備開機時先校時再連 TLS |
| 某些企業網路內所有 HTTPS 都報不信任的 CA | 公司的 TLS 檢查 proxy 用自己的 CA 重新簽發每個網站的憑證 | s_client 看到的 issuer 是公司 proxy 的 CA，而非原本的公開 CA | 依公司政策安裝 proxy 的 CA；敏感服務（金流 API）請 IT 設定略過檢查 |
| mTLS 服務的 client 在第一次 `recv()` 才報 `certificate required` | TLS 1.3 的 client 憑證錯誤以交握後的 alert 傳回 | server log 有 `PEER_DID_NOT_RETURN_A_CERTIFICATE` 或驗證失敗 | client 用 `load_cert_chain()` 載入憑證與私鑰；確認 EKU 含 clientAuth、由 server 信任的 CA 簽發 |
| 開了 0-RTT 之後，偶爾出現重複的預約或扣款 | 非 idempotent 請求被放進 early data 並被重放或重送 | 重複請求的時間差很小，request log 帶有 `Early-Data: 1` | 只放行 GET／HEAD，其餘回 425；後端加 idempotency key（第 24 章） |
| 開了 PQ 金鑰交換後，少數企業網路的連線卡在交握 | 約 1.5 KB 的 ClientHello 跨多個封包，舊 middlebox 只讀第一個封包 | 抓包看 ClientHello 被分段；關掉混合 group 後恢復正常 | 升級 middlebox；暫時讓 client 退回 x25519；確認路徑 MTU（第 8 章） |
| gRPC 連線失敗，curl 對同一端點卻正常 | LB 沒有在 ALPN 選 `h2`，gRPC 需要 HTTP/2 | `openssl s_client -alpn h2` 顯示 `ALPN protocol: (none)` 或 http/1.1 | LB 或 server 啟用 HTTP/2 並在 ALPN 宣告 `h2` |

共同的模式是：先判斷是 server 的問題（憑證鏈、SAN、ALPN）還是 client 的問題（信任庫、時鐘、送出的名字），再決定修哪一邊；`openssl s_client` 是兩邊都能用的中立工具。

## 18.15 動手練習

1. **延伸實驗一：讓解析器認得更多擴充**（延伸程式）。在 `build_client_hello` 加上 `early_data`（type 42，空內容）與第二個 key share（secp256r1，65 bytes 的公開值，用 `hashlib` 產生假資料），再修改解析器印出每個 key share 的 group 與長度。
   答案要點：key_share 的資料結構是「2 bytes 總長＋多個（2 bytes group、2 bytes 長度、公開值）」，總長度要重新計算；`assert p == end == len(rec)` 仍要通過。注意真實規格要求 pre_shared_key 是最後一個擴充，如果你也加了它，順序要放對。

2. **用 openssl 觀察真實的交握**（真實工具）。在自己的電腦上執行 `openssl s_client -connect example.com:443 -servername example.com -brief < /dev/null`，再加上 `-tls1_2` 執行一次，比較兩次的 `Protocol version`、`Ciphersuite` 與 group；最後加上 `-msg` 看每個交握訊息的類型。
   答案要點：1.3 的 cipher suite 名稱沒有金鑰交換與簽章的部分（例如 `TLS_AES_256_GCM_SHA384`），1.2 的名稱像 `ECDHE-RSA-AES128-GCM-SHA256`。`-msg` 的輸出可以對照 18.4 節的表格，找出 EncryptedExtensions、Certificate、CertificateVerify、Finished。

3. **用 Wireshark 看 SNI 與加密的憑證**（真實工具）。用 `tcpdump -i any -w tls.pcap 'tcp port 443'` 用 curl 對 `example.com` 發一次 HTTPS 請求，在 Wireshark 用 `tls.handshake.type == 1` 找出 ClientHello，展開 server_name 與 application_layer_protocol_negotiation；再找 ServerHello 之後的 record，確認看不到 Certificate。
   答案要點：SNI 與 ALPN 清單是明文；ServerHello 之後的 record 類型都是 Application Data。若用 `SSLKEYLOGFILE` 讓 curl 輸出金鑰並在 Wireshark 設定，就能解密看到 Certificate，這也說明 keylog 檔必須當作秘密保管。

4. **延伸實驗四：加上 pathLen 與 EKU 的檢查情境**（延伸程式）。在玩具 PKI 加兩個情境：一張 EKU 只有 `clientAuth` 的 leaf，以及中間 CA 底下又多一層 CA（但中間 CA 的 pathLen 是 0）。
   答案要點：第一個情境要在第 ⑤ 步失敗並回 `unsupported certificate purpose`；第二個需要在 `Cert` 加上 `path_len` 欄位，並在建鏈後檢查「發行者底下的 CA 層數不超過它的 pathLen」，失敗時回 `path length constraint exceeded`。

5. **手算：0-RTT 能省多少**。一位 RTT 180 ms 的美國學生打開聲聲 Live app，需要先 `GET /api/schedule`。比較四種情況下，從開始建立連線到收到回應的第一個 byte 需要幾個 RTT、多少毫秒：TCP＋TLS 1.2 完整交握、TCP＋TLS 1.3 完整交握、TCP＋TLS 1.3 0-RTT、QUIC 0-RTT。如果請求改成 `POST /v1/bookings` 呢？
   答案要點：依序為 4 RTT（720 ms）、3 RTT（540 ms）、2 RTT（360 ms，TCP 交握仍要等）、1 RTT（180 ms）。POST 不能走 0-RTT，會收到 425 或由 client 等交握完成才送，所以 TCP＋1.3 是 3 RTT、QUIC 是 2 RTT（第 13 章）。

## 本章重點整理

- TLS 提供機密性、完整性與真實性；不驗證對方身分的加密擋不住中間人，所以關掉憑證驗證等於放棄 TLS 最重要的保證。
- TLS 用 5 bytes 的 record header 切分 TCP byte stream；1.3 加密後的 record 外層一律標成 application_data。
- TLS 1.3 完整交握只要 1 RTT：client 在 ClientHello 先猜 group 並附上 key_share，猜錯時 server 回 HelloRetryRequest，多花一個 RTT。
- ClientHello 的 legacy 欄位是為了相容 middlebox，真正的協商在 extensions：supported_versions 決定版本，key_share 交換公開值，SNI 指出主機，ALPN 協商上層協定。
- ServerHello 之後的訊息全部加密；Certificate 送出憑證鏈，CertificateVerify 用私鑰簽 transcript 證明持有私鑰，Finished 用 HMAC 確認雙方看到相同的交握。
- 金鑰排程用 HKDF 分三階段混入 PSK、(EC)DHE 共享秘密，並把每把金鑰綁定 transcript；資料金鑰來自 (EC)DHE，憑證金鑰只用來簽章，這是前向保密的來源。
- 憑證把公鑰綁定到 SAN 裡的名稱，由 CA 簽章；server 送 leaf 與中間憑證，client 以自己信任庫中的 root 為信任錨往上驗證。
- client 的驗證步驟依序是建鏈、簽章、CA 限制、效期、用途、名稱、撤銷；名稱比對只看 SAN，wildcard 只代表最左邊恰好一個 label，不涵蓋 apex。
- 撤銷檢查（CRL、OCSP）在實務上很弱，業界轉向短效憑證；Python 的 `ssl` 預設不檢查撤銷。
- SNI 讓同一個 IP 服務多個網域但它是明文，ECH 用加密的內層 ClientHello 補上這個洞；ALPN 的結果在 1.3 放在加密的 EncryptedExtensions。
- Resumption 用 NewSessionTicket 帶來的 PSK 省下憑證驗證；0-RTT 可以在第一個 flight 送請求，但可能被重放，聲聲 Live 只放行 GET／HEAD，其他請求回 425 Too Early。
- mTLS 讓 server 驗證 client 憑證，適合機器與受管理裝置；在 TLS 1.3 中，client 憑證被拒的錯誤常在第一次讀資料時才出現。
- Python 寫 TLS client 時從 `create_default_context()` 開始，私有 CA 用 `cafile=` 加入，永遠不使用 `CERT_NONE` 或 `_create_unverified_context()`。

## 延伸問答

> [!question]- Q1. TLS 1.2 的完整交握要 2 RTT，TLS 1.3 為什麼只要 1 RTT？代價是什麼？
> TLS 1.2 的流程是先協商、後交換金鑰：client 送出 ClientHello 列出 cipher suites，要等 server 在 ServerHello 選定（例如 ECDHE 加某條曲線）並送出 ServerKeyExchange 後，client 才知道該用哪個群組產生公開值，第二趟才送 ClientKeyExchange 與 Finished。TLS 1.3 改成「先猜」：client 直接在 ClientHello 的 key_share 附上它認為 server 最可能接受的 group 的公開值，server 收到就能算出共享秘密，第一個回覆就可以加密並帶上 Finished，client 的第二個 flight 就能送應用資料。
>
> 代價有兩個。第一，猜錯 group 時 server 回 HelloRetryRequest，反而多一個 RTT，所以瀏覽器會同時附上兩個 group 的公開值，ClientHello 因此變大，後量子混合 group 更讓它接近 1.5 KB。第二，1.3 為了簡化，移除了許多 1.2 的選項（RSA 金鑰傳輸、靜態 DH、renegotiation），一些依賴這些功能的舊設備（例如靠靜態 RSA 私鑰被動解密流量的監控系統）就不能再用，這是刻意的安全取捨。

> [!question]- Q2. 憑證是公開的，任何人都可以複製一份。為什麼攻擊者拿著 `api.shengsheng.example` 的真憑證，仍然冒充不了 server？
> 因為憑證只證明「這把公鑰屬於這個名字」，並不證明「送憑證的人就是這個名字」。TLS 1.3 用 CertificateVerify 補上後者：server 必須用憑證公鑰對應的私鑰，對這次交握的 transcript hash 簽章，而 transcript 包含雙方這次連線才產生的 random 與 key_share。攻擊者沒有私鑰，簽不出對的簽章；拿以前錄下的簽章重播也沒用，因為 transcript 不同。
>
> 此外，就算攻擊者設法讓簽章通過，資料金鑰也來自 (EC)DHE：client 的 key_share 對應的私密值只在 client 記憶體中，攻擊者不知道它，就算不出共享秘密，Finished 也算不出來。所以真正需要保護的是私鑰，不是憑證本身；私鑰外洩時要立刻撤銷並換一組金鑰與憑證，只換憑證不換私鑰是常見的錯誤。

> [!question]- Q3. 你在 production 看到一個 Python 服務呼叫金流供應商 `pay.example.net` 時報 `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`，但同一台機器用瀏覽器打開沒問題。你會怎麼排查？
> 這個錯誤代表 client 從 leaf 往上建鏈時，找不到可以接到信任錨的發行者。常見的原因有三個，排查順序依可能性排列。第一，供應商的 server 漏送中間憑證：瀏覽器可能已快取該中間憑證或會依 AIA 自己去抓，Python 不會。用 `openssl s_client -connect pay.example.net:443 -servername pay.example.net -showcerts` 數一下送了幾張，只有一張就是這個原因，應通知對方修正 server 設定。第二，Python 用的信任庫和瀏覽器不同：例如容器映像沒有安裝 CA bundle，或程式用的是過舊的 certifi，缺少供應商換用的新 root。
>
> 第三，路徑上有 TLS 檢查 proxy：公司網路的 proxy 用自己的 CA 重新簽發憑證，瀏覽器因為作業系統裝了這個 CA 而正常，但 Python 用的是另一份信任庫。用 s_client 看 issuer 是誰就能分辨。三種情況的修法都不是關掉驗證：分別是請對方送完整的鏈、更新信任庫、或在這支程式的 context 中加入正確的 CA，而金流這種敏感連線，應請 IT 讓它略過 TLS 檢查 proxy。

> [!question]- Q4. 憑證的 SAN 是 `*.shengsheng.example`。下列哪些名稱會通過名稱比對：`shengsheng.example`、`live.shengsheng.example`、`edge.live.shengsheng.example`、`LIVE.SHENGSHENG.EXAMPLE`？如果要讓全部都通過，憑證該怎麼簽？
> 只有 `live.shengsheng.example` 與 `LIVE.SHENGSHENG.EXAMPLE` 會通過。wildcard 的 `*` 只能出現在最左邊的 label，而且只代表恰好一個 label：`shengsheng.example` 少了一層，wildcard 不涵蓋 apex；`edge.live.shengsheng.example` 多了一層，`*` 不能跨過點去匹配 `edge.live`。名稱比對不分大小寫，所以全大寫的版本和小寫結果相同。
>
> 要讓四個名稱都通過，憑證的 SAN 要列出 `shengsheng.example`、`*.shengsheng.example`、`*.live.shengsheng.example` 三項（或把 `edge.live.shengsheng.example` 明確列出）。設計上的考量是：wildcard 越多，同一把私鑰能冒充的名稱就越多，私鑰放在越多機器上，外洩的風險越大。對外的重要服務（登入、API、金流回呼）通常值得用各自的憑證，wildcard 留給大量、同質的子網域。

> [!question]- Q5. 阿德想在 CDN 上啟用 0-RTT。Rita 問：「如果我們只放行 GET 和 HEAD，就完全沒有風險了嗎？」你會怎麼回答？
> 只放行 GET 與 HEAD 處理了最主要的風險，但前提是「GET 真的沒有副作用」。HTTP 語意規定 GET 是 safe 的，可是實際的 API 不一定遵守：例如用 GET 實作的一次性登入連結、追蹤點擊並扣額度的轉址、`GET /bookings/confirm?id=…` 這種設計錯誤，在 0-RTT 下都可能被重放。所以啟用前要盤點這類端點，必要時對它們另外回 425，或把它們改成 POST。
>
> 第二個風險是資訊與時序：重放一個 GET 不會改資料，但攻擊者可以讓 server 重複執行昂貴的查詢，或觀察回應大小推測內容；這比副作用輕微，通常可以接受。第三，0-RTT 資料沒有對 PSK 的前向保密：票券加密金鑰（server 用來加密 ticket 的 STEK）若外洩，錄下的 early data 可以被解開，所以 STEK 要定期輪替。最後，後端要能辨識請求是否來自 early data（`Early-Data: 1`），而且這個 header 只能由 CDN 設定，入口要清掉 client 自帶的同名 header，否則防護可以被繞過。

> [!question]- Q6. 看 log 找原因：一個新的內部服務啟用了 mTLS，client 端的 Python 程式在 `wrap_socket()` 成功，卻在第一次 `recv()` 拋出 `SSLError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED]`。為什麼錯誤出現在這裡？可能的原因有哪些？
> 在 TLS 1.3 中，client 送出自己的 Certificate、CertificateVerify 與 Finished 之後，就認為交握已經完成，`wrap_socket()`（do_handshake）因此成功返回。server 是在收到 client 的這個 flight 之後才驗證 client 憑證，失敗時送出 alert，而 client 要等到下一次讀取 record 才會看到它，所以錯誤出現在第一次 `recv()`。TLS 1.2 的順序不同，這類錯誤多半在交握中就出現，從 1.2 升級到 1.3 的團隊常被這個差異困惑。
>
> `certificate_required` 代表 server 要求了 client 憑證，client 卻送了一個空的 Certificate。可能的原因有：程式沒有呼叫 `load_cert_chain()`；載入了憑證但它不是 server 在 CertificateRequest 中列出的 CA 簽發的，client 函式庫因此選擇不送；憑證與私鑰檔路徑在容器裡不存在。如果錯誤是 `bad_certificate` 或 `unknown_ca`，則是送了憑證但被拒絕，要查 EKU 是否含 clientAuth、是否過期、server 的信任庫是否有簽發它的 CA。server 端的 log 通常會寫出更精確的原因，例如 `PEER_DID_NOT_RETURN_A_CERTIFICATE`。

> [!question]- Q7. 面試題：TLS 1.3 的 ClientHello 為什麼還要寫 `legacy_version = 0x0303`、填一個 32 bytes 的 session_id，server 還要送一個沒有作用的 change_cipher_spec？這不是浪費嗎？
> 這些都是為了通過網路上的 middlebox。TLS 1.3 在部署測試時發現，大量防火牆、負載平衡器、防毒閘道會解析 TLS，看到不認得的版本號或格式就丟包、斷線，或乾脆把連線降級。這種現象叫 protocol ossification（協定僵化，第 13 章也談過）：協定本來可以演進，但路上的設備把「目前長什麼樣」當成規則寫死了。
>
> 解法是讓 1.3 的交握在外觀上像 1.2 的 session resumption：record 與 ClientHello 的版本欄位都寫 1.2，真正的版本放在 supported_versions 擴充；session_id 填亂數，server 照樣回傳；交握中插入一個假的 change_cipher_spec，讓只認得 1.2 的設備以為「接下來要切換到加密了」。這些欄位多了幾十個 bytes，但換來在現實網路上可以部署。這也是 QUIC 選擇幾乎全部加密、只留極少明文欄位的原因：不給 middlebox 解析的機會，未來就不會被它們卡住。

> [!question]- Q8. 設計取捨：`ops` 後台要限制只有公司裝置能連線。方案 A 是 mTLS，方案 B 是只允許辦公室 VPN 的來源 IP，方案 C 是一般的登入加 MFA。你會怎麼選？
> 三個方案回答的是不同的問題。方案 B 驗證的是「封包從哪裡來」，實作最簡單，但它是位置而不是身分：任何能進入 VPN 或辦公室網段的機器（包括被入侵的機器、訪客的筆電）都能連，而且使用者在家沒開 VPN 就無法使用。方案 C 驗證的是「人」，對釣魚攻擊與密碼外洩有一定的防護，卻無法區分公司配發的裝置與個人電腦。方案 A 驗證的是「裝置持有某把私鑰」：只有經 MDM 安裝了 client 憑證的裝置能完成交握，沒有憑證的連線在 TLS 層就被拒絕，應用程式完全看不到它。
>
> 實務上的答案通常是組合：mTLS 確認裝置、登入加 MFA 確認人，網段限制作為額外的一層，而不是唯一的一層。選 mTLS 要先準備好它的營運成本：私有 CA、client 憑證的自動發放與輪替、裝置遺失時的撤銷流程，以及 LB 如何把驗證過的裝置身分安全地交給後端。這正是 Rita 的提案：`ops` 用 mTLS 加 SSO 登入，辦公室與 VPN 網段限制保留為縱深防禦。

## 延伸閱讀

- RFC 8446〈The Transport Layer Security (TLS) Protocol Version 1.3〉：TLS 1.3 的原始規格，交握、金鑰排程與 0-RTT 的定義（新版規格見 18.11 節）
- RFC 8448〈Example Handshake Traces for TLS 1.3〉：完整交握的逐位元組範例與金鑰排程的測試向量
- RFC 5280〈Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile〉：憑證欄位與鏈驗證演算法
- RFC 9525〈Service Identity in TLS〉（取代 RFC 6125）：名稱比對與 wildcard 的規則
- RFC 6066〈TLS Extensions: Extension Definitions〉與 RFC 7301〈TLS Application-Layer Protocol Negotiation Extension〉：SNI 與 ALPN
- RFC 8470〈Using Early Data in HTTP〉：`Early-Data` header 與 425 Too Early
- Python 官方文件：`ssl` 模組（`create_default_context`、`SSLContext`、`MemoryBIO`）
- OpenSSL 文件：`openssl-s_client(1)`、`openssl-x509(1)`
