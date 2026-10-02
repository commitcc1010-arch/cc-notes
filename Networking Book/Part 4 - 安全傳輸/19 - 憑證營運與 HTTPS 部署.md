---
chapter: 19
title: 憑證營運與 HTTPS 部署
part: 4
---

# 第 19 章　憑證營運與 HTTPS 部署

> [!abstract] 本章地圖
> **核心問題**：TLS 的原理再正確，只要一張憑證過期、少送一張中間憑證、某台副本沒換到新檔案，使用者看到的就是一整頁紅色警告。要怎麼讓憑證在效期越來越短的時代，自己申請、自己更新、自己被監控？
>
> **你會學到**：
> - 畫出 ACME 從建立帳號、下訂單、完成 challenge 到下載憑證的完整時序，說清楚 HTTP-01、DNS-01、TLS-ALPN-01 各自適合的場景與限制
> - 依 2026 年的效期規則（最長 200 天，逐步縮到 47 天）設計更新節奏與告警門檻，知道為什麼「剩 30 天就告警」在短效期下會失靈
> - 在多副本、CDN 與 load balancer 並存的架構裡安全地輪替憑證與私鑰，並驗證每一台都真的換上了
> - 正確部署 HSTS 與 preload，理解 Certificate Transparency 怎麼讓誤發的憑證無所遁形
> - 比較 TLS 終結在 CDN、LB 或應用程式的取捨
> - 用錯誤訊息快速分辨缺中間憑證、名稱不符、時鐘錯誤、過期與 OCSP stapling 問題，並用 Python 寫出到期監控器、ACME 模擬與 HSTS 解析器
>
> **前置知識**：第 3 章（openssl s_client 與 curl -v）、第 14 章（CAA 與 TXT record）、第 16 章（DNS-01 的 TXT 值怎麼算）、第 18 章（憑證鏈、CA 與驗證步驟）

## 19.1 故事：早上八點，登入頁變成紅色警告

2026 年 10 月 1 日星期四早上 8 點 03 分，聲聲 Live 的客服頻道一口氣湧進幾十則訊息：「登入頁打不開」「瀏覽器說連線不安全」「App 一直轉圈」。這時間正好是上班族學生上早課前的尖峰。小晴打開自己的瀏覽器連 `auth.shengsheng.example`，看到 `NET::ERR_CERT_DATE_INVALID`，而且頁面上沒有「仍要繼續」的按鈕。內部服務的 log 也在同一分鐘開始出現 `ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired`。

阿德用 `openssl s_client` 看了一眼：`notAfter=Oct  1 00:00:00 2026 GMT`。UTC 的午夜，就是台灣的早上 8 點。這張憑證不是自動申請的：登入網域的憑證是向商業 CA 購買的 OV 憑證，手動上傳到 API 的 load balancer（203.0.113.80，同一台 LB 依 SNI 替 `api` 與 `auth` 選擇不同憑證）。過去幾年，負責的同事每年換一次，換完就在行事曆上設「明年三月初提醒」。今年 3 月 16 日也照做了，卻沒注意到 CA 這次只發了 199 天：從 2026 年 3 月 15 日起，公開信任憑證的最長效期已經從 398 天縮成 200 天。

緊急處理也不順利。Rita 在 40 分鐘內向 CA 重新簽發並上傳，桌面版 Chrome 恢復了，但 Android App 和用 Python 呼叫登入 API 的內部服務仍然失敗，錯誤變成 `unable to get local issuer certificate`。原來緊急上傳時只貼了 CA 寄來的伺服器憑證，漏了中間憑證。補上以後，又有一位學生回報「憑證尚未生效」，截圖裡電腦右下角的日期是 2020 年。同一個早上，阿德順手巡了一遍其他網域，發現即時服務 `rt.shengsheng.example` 的三台 nginx 裡，有一台送出的還是兩個月前的舊憑證，再過 9 天就會過期。

```text
 2026-03-15  CA/B Forum 規則生效：最長效期 398 天 → 200 天
 2026-03-16  手動購買 auth 憑證（199 天），行事曆提醒設在 2027-03-01
     │                         ……（沒有任何監控看著「送出的」憑證）……
 2026-10-01 00:00 UTC（台灣 08:00）  auth 憑證過期
     08:03  客服湧入；瀏覽器 ERR_CERT_DATE_INVALID，HSTS 讓使用者無法略過
     08:43  緊急重新簽發並上傳 ── 只上傳 leaf，漏了中間憑證
     08:50  桌面 Chrome 恢復；Android App、curl、Python 仍失敗
     09:20  補上 fullchain，全部恢復
     09:35  學生回報「尚未生效」：本機時鐘停在 2020 年
     10:10  巡檢發現 rt 的 10.20.2.13 沒有 reload，還在送 7 月的舊憑證
```

這條時間軸是事後檢討時整理的。第一段說明根因不是技術失誤，而是**流程假設**過時：「一年換一次」在 398 天的時代勉強可行，在 200 天的時代必然失敗，到 2029 年效期剩 47 天時更不可能靠人。第二段的三個問題各自代表一種常見錯誤：憑證鏈不完整、client 時鐘錯誤、多副本沒有同步。最後一段則暴露出監控的盲點：團隊有監控 `certbot renew` 這個排程有沒有成功，卻沒有人從外面看「每一個端點此刻實際送出的憑證」。

阿德在檢討會上說：「第 18 章教的是 TLS 怎麼驗證一張憑證；這一章要學的是怎麼讓憑證永遠通過驗證。」這一章會從憑證的一生講起，拆解 ACME 這個讓機器自己申請憑證的協定，再討論效期縮短後的更新節奏、監控、輪替、HSTS、Certificate Transparency 與 TLS 終結位置，最後用 Python 把到期監控、ACME challenge 與 HSTS 判斷各做一次。

## 19.2 憑證的一生：營運者要管的五個階段

第 18 章從驗證者的角度看憑證：client 拿到一條憑證鏈，檢查名稱、期限、簽章與撤銷狀態。營運者看的是另一面：這張憑證從哪裡來、放在哪裡、什麼時候要換、換的時候會不會中斷服務。把這些事情排成時間順序，就是憑證的**生命週期**（lifecycle）。

```text
  ① 產生金鑰與 CSR        ② 驗證網域並簽發          ③ 部署
  ┌──────────────┐       ┌──────────────────┐      ┌──────────────────────┐
  │ 私鑰（留在本機）│──CSR─►│ CA 檢查你控制網域  │─憑證─►│ CDN／LB／nginx 載入   │
  │ 公鑰＋名稱     │       │ 寫入 CT log、簽發  │  ＋鏈 │ leaf＋中間憑證＋私鑰  │
  └──────────────┘       └──────────────────┘      └──────────┬───────────┘
          ▲                                                    │
          │                 ⑤ 更新或撤銷                ④ 監控 ▼
          └─── 在效期用掉約 2/3 時重來一次 ◄──────── 從外部檢查每個端點送出的憑證
               私鑰外洩時立刻撤銷並換新                 到期日、名稱、鏈、序號是否一致
```

這張圖從左上角開始讀。① **CSR**（Certificate Signing Request，憑證簽署請求）是一份由申請者用私鑰簽過的小文件，裡面放著公鑰與想要的名稱，例如 `auth.shengsheng.example`；私鑰本身從不離開申請者的機器。② CA 先確認申請者真的控制這個網域，這一步叫 **DCV**（Domain Control Validation，網域控制驗證），通過後把預備憑證送進 Certificate Transparency log（19.10 節）再正式簽發。③ 部署時要把伺服器憑證（leaf）、中間憑證與私鑰一起交給終結 TLS 的元件。④ 監控必須從外部觀察實際送出的憑證，故事裡的事故就是缺了這一環。⑤ 更新是整個循環的重來，撤銷則是私鑰外洩或資訊錯誤時的緊急出口。

每一張憑證都帶著一組營運者天天要看的欄位。下表列出最重要的幾個，以及它們在營運上的意義；欄位的密碼學意義在第 18 章。

| 欄位 | 範例值 | 營運上的意義 |
|---|---|---|
| Subject Alternative Name（SAN） | `DNS:auth.shengsheng.example` | 憑證涵蓋哪些名稱；瀏覽器只看這裡，不看 CN |
| notBefore／notAfter | `Mar 16 00:00:00 2026 GMT`／`Oct  1 00:00:00 2026 GMT` | 有效期間，時間一律是 UTC；兩者相減就是效期 |
| Issuer | `O=Example OV CA` | 由哪一張中間憑證簽發，決定要附哪一條鏈 |
| Serial Number | `7C03…` | 同一個 CA 下的唯一編號；用來確認副本是否送出同一張 |
| Authority Information Access | CA Issuers、（可能有）OCSP | 中間憑證與 OCSP 的位置；有些 client 會用它補鏈 |
| CRL Distribution Points | CRL 的位置 | 撤銷資訊從哪裡取得 |
| Signed Certificate Timestamps（SCT） | 兩到三個 log 的簽章 | 證明這張憑證已登錄 CT；瀏覽器會檢查 |

表中最常被忽略的是 notAfter 的時區。憑證裡的時間是 UTC，故事裡的 `00:00:00 GMT` 在台灣是早上 8 點，在美國西岸是前一天下午 5 點。手動管理憑證時，人們常把它當成本地時間，算錯幾個小時；自動化程式則應該全程用 UTC 計算。

> [!warning] 常見誤解
> 「憑證過期只影響瀏覽器。」實際上，伺服器之間的 HTTPS 呼叫、行動 App、webhook 接收端、資料庫的 TLS 連線都會一起失敗，而且往往比瀏覽器更不寬容：瀏覽器有時會自己補上缺漏的中間憑證，Python、curl 與多數 App 不會。

## 19.3 ACME：讓機器自己申請憑證

如果每張憑證都要人去 CA 的網站填表、收信、下載、上傳，效期縮短只會讓事故更頻繁。**ACME**（Automatic Certificate Management Environment，RFC 8555）把整個流程變成一組 HTTPS API：ACME client（例如 certbot、acme.sh、lego、Kubernetes 的 cert-manager，或內建 ACME 的 Caddy）負責產生金鑰、證明網域控制權、取得憑證並安裝；CA 這一端稱為 ACME server。Let's Encrypt 讓 ACME 普及，現在許多商業 CA 也提供 ACME 端點，常搭配 **EAB**（External Account Binding，把 ACME 帳號綁到既有的付費帳號）。

### 帳號金鑰與每一個請求的簽章

ACME 的第一個設計重點是：**每一個請求都要用帳號金鑰簽章**。帳號金鑰（account key）是 ACME client 第一次使用時產生的一把非對稱金鑰，用來代表「這個 ACME 帳號」，和憑證本身的私鑰是兩把不同的金鑰，不能共用。請求的格式是 **JWS**（JSON Web Signature，一種把 JSON 內容與簽章包在一起的格式，第 27 章講 JWT 時會再遇到它）：protected header 裡放著簽章演算法、這次請求的 URL、一個 nonce，以及帳號的識別（第一次註冊時放公鑰本身，之後放 CA 指派的帳號 URL，稱為 `kid`）。

**Nonce**（number used once）是 CA 發的一次性亂數，每個請求都要帶一個新的，CA 收到後就作廢。這是為了防止**重放**（replay）：就算有人錄下 client 送出的某個合法請求，原封不動再送一次，CA 也會因為 nonce 已用過而回 `badNonce`。CA 在每個回應的 `Replay-Nonce` header 附上下一個可用的 nonce，所以正常流程不需要額外多問一次。連「讀取訂單狀態」這種讀取動作也要簽章，ACME 稱為 **POST-as-GET**：用 POST 送出一個 payload 為空的 JWS，讓 CA 確認讀取者就是帳號擁有者。

### 從訂單到憑證的完整流程

下面是 ACME client 替 `auth.shengsheng.example` 申請憑證的完整時序。ACME 的所有端點都列在一個 **directory**（目錄）物件裡，client 只需要知道 directory 的位址，其他網址都從回應裡取得。

```text
 ACME client                                                   ACME server（CA）
   │──── GET directory ──────────────────────────────────────────►│
   │◄─── {newNonce, newAccount, newOrder, revokeCert, …} ─────────│
   │──── HEAD newNonce ──────────────────────────────────────────►│
   │◄─── Replay-Nonce: n1 ─────────────────────────────────────────│
   │──── POST newAccount  JWS{jwk=帳號公鑰, nonce=n1} ───────────►│
   │◄─── 201  Location: 帳號 URL（kid）  Replay-Nonce: n2 ─────────│
   │──── POST newOrder  JWS{kid, n2, identifiers:[auth…]} ──────►│
   │◄─── 201  order{status:pending, authorizations:[…], finalize}─│
   │──── POST-as-GET authorization ──────────────────────────────►│
   │◄─── challenges:[http-01 token=T, dns-01 token=T, …] ─────────│
   │       （client 依選擇的 challenge 放好驗證內容）              │
   │──── POST challenge URL  {} ─────────────────────────────────►│  「我準備好了」
   │                                   CA 從多個網路位置驗證 ──────┤
   │──── POST-as-GET authorization（輪詢） ───────────────────────►│
   │◄─── status: valid；order 變成 ready ──────────────────────────│
   │──── POST finalize  {csr: base64url(CSR)} ────────────────────►│
   │◄─── order{status:processing → valid, certificate: URL} ──────│
   │──── POST-as-GET certificate ────────────────────────────────►│
   │◄─── PEM：leaf＋中間憑證（完整鏈） ────────────────────────────│
```

這張時序圖可以分成四段讀。第一段（前兩行）只做一次：取得 directory 與第一個 nonce。第二段註冊帳號，帳號公鑰就在這個請求裡交給 CA，之後的請求都用 `kid` 指名帳號。第三段是核心：client 下一張**訂單**（order），列出想要的名稱；CA 為每個名稱建立一個**授權**（authorization），每個授權附上幾種可選的 **challenge**（挑戰），client 只要完成其中一種。client 放好驗證內容後，對 challenge URL 送出空物件 `{}`，意思是「請來驗證」，CA 就會自己去檢查。第四段，所有授權都通過後，client 才送出 CSR 給 finalize URL，CA 簽發後提供下載網址。下載回來的 PEM 檔已經包含中間憑證，這正是 certbot 會產生 `fullchain.pem` 的原因。

訂單在這個過程中有明確的狀態，ACME client 就是依狀態決定下一步：

```text
                 所有 authorization 都 valid           送出 finalize（CSR）
   ┌─────────┐ ─────────────────────────► ┌───────┐ ─────────────────► ┌────────────┐
   │ pending │                             │ ready │                    │ processing │
   └────┬────┘                             └───┬───┘                    └─────┬──────┘
        │ 任何 authorization 失敗、             │ 逾時未 finalize               │ CA 簽發完成
        │ 或訂單過期                            ▼                              ▼
        └──────────────────────────────► ┌─────────┐                    ┌─────────┐
                                         │ invalid │                    │  valid  │──► 下載憑證
                                         └─────────┘                    └─────────┘
```

狀態機的重點是 `invalid` 是終點：只要一個名稱的驗證失敗，整張訂單就作廢，client 必須重新下單。這解釋了一個常見現象：一張憑證同時包含十個名稱，其中一個名稱的 DNS 已經改指別處，整張憑證就更新失敗。名稱越多，單點失敗的機率越高，所以把不相關的服務拆成不同憑證，通常比一張塞滿名稱的大憑證好維護。另外，授權在一段時間內可以重用（例如同一個帳號幾天後再申請同一個名稱，可能直接是 valid），這就是 19.5 節 DCV 重用期限要管的事。

## 19.4 三種 challenge：HTTP-01、DNS-01 與 TLS-ALPN-01

challenge 的共同核心是 **key authorization**：CA 給一個隨機的 token，client 把它和帳號公鑰的 **thumbprint**（依 RFC 7638 把 JWK 正規化後取 SHA-256 再 base64url）接成 `token.thumbprint`。這個值同時綁定了「這次挑戰」與「這個帳號」：就算有人在網路上看到 token，用自己的帳號也算不出相同的值，CA 驗證時就能確認放置內容的人和下訂單的人是同一個帳號。三種 challenge 的差別只在於「把這個值放到哪裡讓 CA 看到」。

### HTTP-01：在網站上放一個檔案

**HTTP-01** 要求 client 讓網域上的 `/.well-known/acme-challenge/<token>` 這個路徑回傳 key authorization 的原文。CA 一定從 **port 80** 用明文 HTTP 發起驗證，因為這是「控制網域指向的伺服器」最直接的證明。

```text
 ACME client（在 nginx 主機上）     nginx（port 80）           CA 的驗證節點（多個地點）
   │── 寫入檔案 webroot/.well-known/acme-challenge/T ──►│                    │
   │── POST challenge URL {} ───────────────────────────────────────────────►│
   │                                   │◄── 查 DNS：A rt… → 203.0.113.40 ────│
   │                                   │◄── GET /.well-known/acme-challenge/T │
   │                                   │      Host: rt.shengsheng.example     │
   │                                   │── 200  "T.thumbprint" ─────────────►│
   │                                   │      （每個地點都要得到相同內容）     │
   │◄── authorization valid ────────────────────────────────────────────────│
   │── 刪除檔案 ──────────────────────►│                                     │
```

這張圖有三個實務細節。第一，CA 透過公開 DNS 找到網域的位址，所以驗證請求會走和使用者一樣的路徑：經過 CDN、LB、再到某一台副本。如果驗證檔只寫在其中一台副本，而 LB 把 CA 的請求分到另一台，就會得到 404；公開信任的 CA 現在被要求從多個網路位置交叉驗證（**MPIC**，multi-perspective issuance corroboration），請求會打到更多台，失敗機率更高，19.12 節的實驗會重現這件事。第二，CA 會跟隨 redirect（例如 Let's Encrypt 只跟隨到 80 或 443 port），所以 port 80 統一轉到 HTTPS 沒有問題，但 HTTPS 那邊必須能正確回應，不能因為憑證過期就整個壞掉；實務上建議讓 `/.well-known/acme-challenge/` 在 port 80 直接回應、不做轉址。第三，HTTP-01 **不能申請 wildcard**（`*.shengsheng.example`），因為「控制某一台主機」不能證明「控制整個網域底下所有名稱」。

### DNS-01：在 DNS 放一筆 TXT

**DNS-01** 要求在 `_acme-challenge.<網域>` 放一筆 TXT record，值是 `base64url(SHA-256(key authorization))`。第 16 章已經手算過這個值，並討論了傳播延遲、split-horizon 與 DNS API 權限的陷阱，這裡只補上營運的取捨：DNS-01 是唯一能申請 wildcard 的方式，也不需要對外開放任何 port，適合內部主機與 L4 LB 後面的服務；代價是 ACME client 必須握有一把能修改 DNS 的 API 憑證，這把憑證外洩的衝擊遠大於一張網站憑證。常見做法是把 `_acme-challenge` 用 CNAME 委派到一個專門的驗證 zone，ACME client 只拿那個小 zone 的權限。

### TLS-ALPN-01：在 443 port 上用特殊的 TLS 交握回答

**TLS-ALPN-01**（RFC 8737）讓驗證完全在 port 443 上完成。CA 對網域的 443 port 發起 TLS 交握，SNI 是要驗證的名稱，ALPN（第 18 章，交握時協商應用層協定的擴充）只提供一個特殊值 `acme-tls/1`。伺服器看到這個 ALPN，就改送一張臨時產生的自簽憑證：SAN 是那個網域，並帶一個標成 critical 的 `acmeIdentifier` 擴充，內容是 key authorization 的 SHA-256。CA 檢查完就中止交握，不會傳送任何 HTTP。

```text
 CA 驗證節點                                         終結 TLS 的伺服器（port 443）
   │── ClientHello  SNI=rt.shengsheng.example  ALPN=[acme-tls/1] ──►│
   │                         看到 acme-tls/1：不用正式憑證，改用驗證專用憑證 │
   │◄── ServerHello  ALPN=acme-tls/1                                   │
   │◄── Certificate：自簽，SAN=rt.shengsheng.example，                 │
   │                 acmeIdentifier = SHA-256(key authz)（critical）    │
   │── 比對雜湊，中止交握（不送任何應用資料） ────────────────────────►│
```

TLS-ALPN-01 的好處是不需要 port 80，也不需要 DNS 權限，適合「本來就終結 TLS 的元件自己申請憑證」，例如內建 ACME 的反向代理或 edge 節點。限制是它必須由真正終結 TLS 的那個元件實作，若 443 前面還有一層會終結 TLS 的 CDN 或 LB，CA 的交握會停在那一層；它同樣不能申請 wildcard。

下表整理三種 challenge 的取捨，聲聲 Live 在事故後的選擇也列在最後一欄。

| 項目 | HTTP-01 | DNS-01 | TLS-ALPN-01 |
|---|---|---|---|
| CA 去哪裡驗證 | 網域的 port 80，固定路徑 | `_acme-challenge` 的 TXT record | 網域的 port 443，特殊 ALPN 交握 |
| 能否申請 wildcard | 不能 | 能 | 不能 |
| 需要對外開的 port | 80 | 不需要 | 443 |
| ACME client 需要的權限 | 寫入網站的驗證路徑 | 修改 DNS 的 API 憑證 | 控制 TLS 終結元件 |
| 多副本的難處 | 驗證請求可能打到沒有檔案的副本 | 傳播到所有 authoritative server 需要時間 | 每台副本都要能回應 acme-tls/1 |
| 常見失敗原因 | CDN／WAF 擋住或快取路徑、port 80 被關 | 傳播未完成、split-horizon、CAA | 前面有一層 TLS 終結元件 |
| 聲聲 Live 的用法 | `api`（LB 統一回應驗證路徑） | `*.shengsheng.example`、內部主機、`rt` | 暫不使用 |

> [!tip] 不論用哪一種 challenge，都先檢查 CAA
> 第 14 章提過，CAA record 宣告「哪些 CA 可以替這個網域發憑證」。CA 簽發前一定會查，查到不包含自己就拒絕，而且錯誤常常出現在訂單的最後一步。換 CA、啟用 CDN 代管憑證或新增一家備援 CA 時，都要先更新 CAA。

## 19.5 效期越來越短：2026 年的更新節奏

為什麼 CA/Browser Forum（CA 與瀏覽器廠商共同制定公開憑證規則的組織）要一再縮短效期？原因有兩個。第一，撤銷機制在實務上並不可靠（19.8 節），一張私鑰外洩或資訊錯誤的憑證，最可靠的「撤銷」就是讓它早點過期。第二，網域會易主，憑證上的驗證結果也會過時：一個網域賣給別人以後，前任擁有者手上那張憑證在到期前都還能用。效期越短，錯誤狀態能持續的時間就越短；代價是更新次數變多，逼著所有人自動化。

> [!note] 2026 現況
> 截至 2026 年 10 月，CA/Browser Forum 的 Ballot SC-081v3（2025 年 4 月通過）已進入第一階段（依 2026 年 10 月查證）：
>
> | 生效日 | 最長憑證效期 | 網域驗證結果可重用期限 |
> |---|---|---|
> | 至 2026-03-14 | 398 天 | 398 天 |
> | 2026-03-15 起 | 200 天 | 200 天 |
> | 2027-03-15 起 | 100 天 | 100 天 |
> | 2029-03-15 起 | 47 天 | 10 天 |
>
> 同一份規則也把 OV／EV 憑證的組織身分資訊重用期限從 825 天降為 398 天。Let's Encrypt 的預設效期仍是 90 天，並已提供短效憑證（約 6 天）的選項，也宣布了逐步縮短預設效期的計畫，具體時程以官方公告為準。ACME 也有了標準化的更新時機建議：**ARI**（ACME Renewal Information，RFC 9773），CA 透過 `renewalInfo` 端點告訴 client 每張憑證建議的更新時間窗。

這個時程對營運的衝擊可以直接算出來。下面的程式假設在「效期用掉三分之二」時更新，算出每個階段多久要換一次、一年換幾次，以及更新時能不能沿用上一次的網域驗證；最後重算故事裡那張 199 天憑證與行事曆提醒的落差。

```python
import datetime as dt

# CA/B Forum SC-081v3 的階段（依 2026 年 10 月查證）：生效日、最長效期、網域驗證可重用天數
PHASES = [("～2026-03-14", 398, 398), ("2026-03-15", 200, 200),
          ("2027-03-15", 100, 100), ("2029-03-15", 47, 10)]

print("階段          最長效期  每隔幾天更新  每年更新次數  更新時的網域驗證")
for label, life, dcv in PHASES:
    interval = life * 2 / 3                     # 在用掉三分之二時更新，留三分之一當緩衝
    renewals = 365 / interval
    reuse = "可沿用上次結果" if dcv > interval else "每次都要重新驗證"
    print(f"{label:<12}  {life:>6}d  {interval:>10.1f}d  {renewals:>10.1f}  {reuse}")

# 用「一年一次、手動」的習慣管理 200 天憑證會怎樣？
issued = dt.date(2026, 3, 16)
expires = issued + dt.timedelta(days=199)
reminder = dt.date(2027, 3, 1)                  # 沿用 398 天時代的行事曆提醒
print(f"\n{issued} 簽發的 199 天憑證在 {expires} 到期；提醒設在 {reminder}，晚了 {(reminder - expires).days} 天")
assert expires == dt.date(2026, 10, 1)
assert 47 * 2 / 3 > 10                          # 2029 年後，驗證結果撐不到下一次更新
```

```text
階段          最長效期  每隔幾天更新  每年更新次數  更新時的網域驗證
～2026-03-14      398d       265.3d         1.4  可沿用上次結果
2026-03-15       200d       133.3d         2.7  可沿用上次結果
2027-03-15       100d        66.7d         5.5  可沿用上次結果
2029-03-15        47d        31.3d        11.6  每次都要重新驗證

2026-03-16 簽發的 199 天憑證在 2026-10-01 到期；提醒設在 2027-03-01，晚了 151 天
```

從輸出可以讀出三件事。第一，在 200 天的階段，每 133 天就要更新一次，一年將近三次，「一年一次」的手動流程已經不成立；到 47 天的階段，一年要更新將近 12 次。第二，2029 年以後網域驗證只能重用 10 天，比更新間隔（31 天）短得多，所以**每一次更新都要重新驗證網域**。這代表 HTTP-01 的路徑、DNS-01 的 API 權限、CAA 設定，每個月都要真的能用一次，任何一個設定壞掉，一個月內就會變成事故。第三，故事裡的行事曆提醒晚了 151 天，這不是個人疏失，而是流程本身與新規則不相容。

### 更新策略：什麼時候換、失敗了怎麼辦

**什麼時候換**。常見的經驗法則是在剩下約三分之一效期時更新，例如 90 天的憑證在剩 30 天時換。這留下足夠的時間重試：就算 CA 暫時故障、DNS API 出錯，還有好幾週可以補救。有 ARI 的 CA 會直接給出建議時間窗，client 在窗內隨機挑一個時間點更新；這讓 CA 能把大量 client 的更新時間分散開來，在需要大規模換發（例如 CA 發現自己誤發了一批憑證）時，也能通知 client 提早更新。如果所有 client 都在整點跑 cron，CA 每到整點就會被打爆，所以即使沒有 ARI，也應該加上隨機延遲。

**失敗了怎麼辦**。更新失敗要用指數退避重試，而不是每分鐘狂打；公開 CA 都有頻率限制（rate limit），例如對同一組名稱在一段期間內可以簽發的次數設上限。設定錯誤時盲目重試，很快就會撞上限制，到了真正修好的時候反而不能申請。測試新設定時應該先用 CA 提供的 staging 環境。最重要的是：更新失敗要**告警**，而且告警要在還有充裕時間時發出，19.6 節會討論門檻怎麼設。

**要不要每次換新私鑰**。每次更新都產生新私鑰，可以限制單一私鑰外洩的影響期間，多數 ACME client 預設就這麼做。例外是有人做了 **key pinning**（把公鑰雜湊寫死在 App 裡），換私鑰就會讓 App 連不上；這也是為什麼行動 App 的 pinning 應該盡量避免，非用不可時要事先準備好備用金鑰並固定在 CA 或中間憑證層級。瀏覽器的 HTTP Public Key Pinning（HPKP）正是因為太容易讓網站把自己鎖死，已經被移除。

## 19.6 自動更新之後：監控與告警

故事裡的 `rt` 副本問題，說明「自動更新」和「使用者拿到新憑證」之間還隔著好幾步。阿德在白板上把它拆成一條鏈，每一環都可能斷：

```text
  更新排程         憑證存放處            載入 TLS 的 process         對外端點                 使用者
 ┌─────────┐  寫入 ┌──────────────┐ reload ┌──────────────────┐ 送出 ┌──────────────┐ 驗證 ┌───────┐
 │ certbot │─────►│ 檔案／Secret  │──────►│ nginx、LB、CDN    │────►│ 203.0.113.40  │────►│ 瀏覽器│
 │ cron    │      │ 新憑證＋私鑰  │       │ 記憶體裡的憑證     │     │ 10.20.2.11~13 │     │ App   │
 └─────────┘      └──────────────┘       └──────────────────┘     └──────────────┘     └───────┘
  ✓ 排程成功        ✓ 檔案是新的           ✗ 10.20.2.13 沒 reload    ✗ 1/3 的連線拿到舊憑證
  （團隊原本只監控這裡）                                            （應該監控這裡：從外部看）
```

這張圖從左往右是憑證流動的方向。團隊原本只監控最左邊：排程有沒有成功結束。但排程成功只代表檔案換了；nginx 要收到 reload 才會把新憑證載入記憶體，而 10.20.2.13 那一台的 deploy hook 因為權限問題靜悄悄地失敗了。更隱蔽的是，前面的 L4 LB 會把連線分到三台副本，所以從外部只連一次，三分之二的機率會看到新憑證，監控以為一切正常。正確的監控點在右邊：**從外部連到每一個端點、每一台副本，讀出實際送出的憑證**。

一個好的憑證監控至少檢查五件事：剩餘效期、SAN 是否涵蓋這個主機名稱、是否送出完整的鏈、同一個名稱的所有副本是否送出同一張憑證（比對序號或指紋），以及憑證是否「該換卻沒換」。最後一項是效期縮短後最重要的訊號：自動化正常時，憑證應該在用掉三分之二時就被換掉；如果超過那個時間點還是同一張，代表自動化壞了，這時離過期還有一段時間，正是最適合修的時候。

告警門檻也要跟著效期調整。傳統的「剩 30 天告警」是為了一年期憑證設計的；套用在 47 天的憑證上，每張新憑證簽發 17 天後就開始響，團隊很快會學會忽略它；套用在 6 天的短效憑證上，憑證一發下來就「快過期」。比較好的方式是用**效期的比例**：超過預定更新時間點一段寬限期後發 WARNING，剩不到效期的一成時發 CRITICAL。19.12 節的實驗一會把這兩種規則並排比較。

> [!example] 例子
> 在 shell 裡看某個端點實際送出的憑證，要用 `-servername` 指定 SNI，並直接連到每一台副本的位址：
>
> ```bash
> for ip in 10.20.2.11 10.20.2.12 10.20.2.13; do
>   echo | openssl s_client -connect "$ip:443" -servername rt.shengsheng.example 2>/dev/null \
>     | openssl x509 -noout -serial -enddate
> done
> ```
>
> 三行輸出的 serial 應該一模一樣；不一樣，就是有副本沒換上新憑證。

## 19.7 輪替與多副本部署

**輪替**（rotation）指的是用新憑證（通常連同新私鑰）取代舊憑證，而且過程中服務不中斷。因為新舊憑證的有效期間是重疊的，只要新憑證在舊憑證到期前部署完畢，client 看到哪一張都能通過驗證，這讓輪替可以從容地一台一台進行。真正需要小心的是三件事：新憑證要送到每一台副本、每一台都要重新載入、私鑰在傳送與存放過程中不能外洩。

重新載入的方式依元件而不同。nginx 的 `reload` 會讓新的 worker 載入新設定與新憑證，舊 worker 處理完手上的連線才結束，屬於不中斷的換法；certbot 這類 client 可以設定 deploy hook，在更新成功後自動執行 reload。直接用 Python 的 `ssl` 模組終結 TLS 的程式，憑證是在 `SSLContext.load_cert_chain()` 時讀進記憶體的，檔案換了也不會自動生效，要建立新的 `SSLContext` 給之後的新連線使用。gunicorn 直接終結 TLS 時，也要讓 worker 重新載入才會換上新憑證。雲端 LB 與 CDN 的受管憑證通常由供應商自動處理，但**自行匯入**的憑證多半不會自動更新，故事裡的 auth 就是這一類。

多副本的部署有兩種基本模式：

```text
 模式 A：每台副本各自申請                     模式 B：集中申請、統一分發
 ┌──────────┐ ┌──────────┐ ┌──────────┐      ┌───────────────────────┐
 │ nginx #1 │ │ nginx #2 │ │ nginx #3 │      │ 憑證控制器（ACME client）│── DNS-01 ──► CA
 │ certbot  │ │ certbot  │ │ certbot  │      └───────────┬───────────┘
 └────┬─────┘ └────┬─────┘ └────┬─────┘                  │ 寫入（加密存放、限制讀取者）
      └────────────┼────────────┘                 ┌──────▼──────┐
          各自對 CA 申請、各自驗證                  │ Secret 存放處 │
   ✗ 3 倍的簽發次數，容易撞頻率限制               └──┬────┬────┬─┘
   ✗ HTTP-01 驗證請求可能打到別台                    ▼    ▼    ▼   各副本讀取並 reload
   ✗ 三張不同的憑證，除錯困難                     #1   #2   #3   ✓ 同一張憑證、同一個序號
```

聲聲 Live 在事故前的 `rt` 用的是模式 A，三台 nginx 各自跑 certbot 與 HTTP-01，結果每隔幾次更新就有一台因為驗證請求被分到別台而失敗，失敗的那台就默默留著舊憑證。事故後改成模式 B：由一個憑證控制器（在 Kubernetes 上通常是 cert-manager，把結果寫成 Secret）用 DNS-01 統一申請，結果放進存取受限的 Secret 存放處，各副本讀取後 reload。模式 B 的代價是私鑰要從控制器搬到副本，存放處的存取權限、傳輸加密與稽核紀錄就成了安全重點，Rita 要求只有 `rt` 的 nginx 能讀這把私鑰（第 30 章會談 secrets 管理）。

| 做法 | 適合的情境 | 主要風險 | 怎麼驗證換好了 |
|---|---|---|---|
| 每台副本自行申請（模式 A） | 單台或少量主機、各自有獨立名稱 | 頻率限制、HTTP-01 打到別台、憑證不一致 | 逐台比對到期日 |
| 集中申請、分發（模式 B） | 多副本服務、wildcard、Kubernetes | Secret 存放處的權限與外洩 | 逐台比對序號一致 |
| CDN／雲端 LB 受管憑證 | 對外網站與 API | CAA 未包含供應商的 CA、DNS 驗證記錄被刪 | 從外部檢查到期日；看供應商的更新狀態 |
| 自行匯入到 LB | 必須用特定 CA（例如 OV） | 不會自動更新，完全靠人 | 監控到期日，並為匯入流程寫 runbook |

這張表的最後一列，就是聲聲 Live 決定把 auth 從手動匯入改成 LB 受管憑證的原因；保留 OV 的理由經過討論後並不成立，因為瀏覽器早就不再對 OV 顯示任何不同的介面。

## 19.8 撤銷與 OCSP stapling

輪替處理的是「正常換新」，撤銷處理的是「這張憑證不該再被信任」，例如私鑰外洩、名稱被錯誤簽發，或者網域已經轉手。撤銷的傳統機制有兩種：**CRL**（Certificate Revocation List）是 CA 定期發布的「已撤銷序號清單」；**OCSP**（Online Certificate Status Protocol）讓 client 即時向 CA 詢問某一張憑證的狀態。OCSP 的問題是每次連線都多一次查詢，拖慢交握，還讓 CA 知道使用者正在連哪些網站。

**OCSP stapling** 是為此設計的改良：由伺服器定期向 CA 取得帶有 CA 簽章的 OCSP 回應，在 TLS 交握時「釘」在憑證後面一起送給 client，client 就不必自己去查。伺服器端的常見問題是：伺服器取不到 OCSP 回應（例如防火牆擋住對外連線、nginx 沒有設定可用的 DNS resolver），或者送出過期的 OCSP 回應。如果憑證帶有 **Must-Staple** 擴充，瀏覽器沒收到有效的 stapled 回應就會拒絕連線，stapling 的任何故障都會變成全面中斷。

> [!note] 2026 現況
> 截至 2026 年 10 月，撤銷機制正在從 OCSP 轉向 CRL。CA/Browser Forum 的規則已讓 CRL 成為必要、OCSP 成為選用；Let's Encrypt 已在 2025 年停止 OCSP 服務，新憑證不再帶 OCSP 網址（細節以 Let's Encrypt 公告為準）。主流瀏覽器也大多不在每次連線時線上查 OCSP，而是由瀏覽器廠商彙整 CRL 後推送壓縮過的撤銷資料（例如 Chrome 的 CRLSets、Firefox 的 CRLite）。對營運者的實際影響是：使用沒有 OCSP 網址的憑證時，nginx 的 `ssl_stapling` 設定只會在 log 留下警告（例如 `"ssl_stapling" ignored, no OCSP responder URL in the certificate`），不會造成故障；不要申請 Must-Staple 憑證；撤銷之後仍要假設部分 client 一段時間內看不到撤銷結果，所以「換掉私鑰並部署新憑證」才是真正的處置。

撤銷不可靠，正是 19.5 節效期縮短的理由之一，兩件事要一起理解：短效期讓「錯誤的憑證」自然消失，撤銷只是加速這個過程。私鑰外洩時的正確順序是：先產生新私鑰並簽發新憑證、部署到所有端點，再撤銷舊憑證，最後查 CT log（19.10 節）確認沒有其他未預期的憑證。

## 19.9 HSTS 與 preload：第一個請求的保護

憑證保護的是 HTTPS 連線本身，但使用者第一次輸入 `www.shengsheng.example` 時，瀏覽器可能先用明文 HTTP 連線，再被 301 轉到 HTTPS。那一個明文請求就是破口：在公共 Wi-Fi 上，能控制網路的人可以攔下這個請求，讓使用者一直停在 HTTP 版本，這類攻擊稱為 **SSL stripping**。防禦的方法是讓瀏覽器記住「這個網站只能用 HTTPS」，這就是 **HSTS**（HTTP Strict Transport Security，RFC 6797）。

網站在 HTTPS 回應中加上 `Strict-Transport-Security` header，瀏覽器就把這個主機記為 **known HSTS host**，在 `max-age` 秒內：所有對這個主機的 HTTP 請求都在瀏覽器內部直接改寫成 HTTPS，明文請求根本不會送出；遇到任何憑證錯誤時，不再提供「仍要繼續」的選項。故事裡學生無法略過錯誤頁，就是因為 `shengsheng.example` 啟用了 HSTS 與 includeSubDomains；這讓事故更顯眼，但也正是 HSTS 的設計目的，因為「讓使用者點過去」正是攻擊者希望的事。

```text
 第一次造訪（沒有 HSTS 紀錄）                     之後的造訪（已記住，max-age 內）
 瀏覽器                      www                  瀏覽器                         www
   │── GET http://www… ──────►│  ← 明文，可被攔截     │ 使用者輸入 http://www…
   │◄── 301 → https://www… ───│                       │ 查 HSTS 清單：命中
   │── TLS 交握＋GET ─────────►│                       │ 內部改寫成 https（307 Internal Redirect）
   │◄── 200                    │                       │── TLS 交握＋GET ─────────────►│
   │    Strict-Transport-Security: max-age=31536000;   │◄── 200 ───────────────────────│
   │    includeSubDomains; preload                     │    （明文請求從未出門）
   │  記住：shengsheng 系列只能走 HTTPS                │
```

左半邊說明 HSTS 的弱點：第一次造訪的那個明文請求仍然沒有保護，這叫做「首次使用信任」（trust on first use）。右半邊是記住以後的行為，DevTools 會把這次改寫顯示成 `307 Internal Redirect`，這不是伺服器回的 307，而是瀏覽器自己做的。要補上第一次的破口，就要用 **HSTS preload list**：瀏覽器內建的一份清單，列在上面的網域從安裝瀏覽器的那一刻就只走 HTTPS。這份清單由 Chromium 專案維護，其他主流瀏覽器也使用它。

| directive | 意思 | 注意事項 |
|---|---|---|
| `max-age=<秒>` | 記住多久；必填 | 0 表示刪除紀錄；preload 要求至少 31536000（一年） |
| `includeSubDomains` | 所有子網域都適用 | 內部只有 HTTP 的子網域會被一起擋掉 |
| `preload` | 表示同意被加入 preload list | 不是 RFC 6797 的一部分；瀏覽器收到 header 時忽略它，只給清單審核看 |

HSTS 的規則有幾個細節會影響部署。第一，瀏覽器只理會 **HTTPS 回應**中的 HSTS header，HTTP 回應裡的會被忽略，因為明文回應可能被竄改。第二，directive 名稱不分大小寫，但同一個 directive 出現兩次會讓整個 header 無效；`max-age` 的值必須是十進位整數，寫成 `1y` 也會讓整個 header 被忽略。第三，HSTS 只認主機名稱，不能對 IP 位址生效。第四，`includeSubDomains` 涵蓋所有層級的子網域：聲聲 Live 的內部後台 `ops.shengsheng.example` 只開在內網，如果它還沒有 HTTPS，加上 includeSubDomains 以後，曾經造訪過主網域的員工就再也打不開它。

申請 preload 的條件是：憑證有效、port 80 把同一個主機轉到 HTTPS、所有子網域都支援 HTTPS，以及主網域的 HTTPS 回應帶有 `max-age` 至少一年、`includeSubDomains` 與 `preload` 的 header。加入清單要等瀏覽器發新版才生效，**移除也一樣**，可能要好幾個月，所以 preload 幾乎是單向的決定。阿德建議的導入方式是逐步拉長 max-age：

1. 先盤點所有子網域，確認每一個都能用 HTTPS 正常服務，包括內部後台與舊的行銷頁面。
2. 用 `max-age=300` 上線，觀察一週錯誤率；出問題時把 max-age 改成 0 就能在五分鐘內解除。
3. 加上 `includeSubDomains`，依序拉長到一週、一個月，每一步都觀察一段時間。
4. 拉長到一年（`max-age=31536000`）並穩定運作後，才加上 `preload` 並提出申請。

## 19.10 Certificate Transparency：讓每一張憑證攤在陽光下

整個 WebPKI 的弱點是：任何一家受信任的 CA，都能替任何網域簽發憑證。如果某家 CA 被入侵或作業出錯，替 `auth.shengsheng.example` 發了一張不屬於聲聲 Live 的憑證，聲聲 Live 怎麼會知道？**Certificate Transparency**（CT，RFC 6962）的答案是：要求所有公開信任的憑證都登錄在公開、只能附加（append-only）的 log 裡，任何人都能查詢與監控。CT 不會阻止誤發，但讓誤發無法隱藏。

```text
  CA                          CT log（多個，由不同組織營運）           瀏覽器
   │── ① 預備憑證（precert）──►│                                       │
   │◄── ② SCT（log 的簽章承諾：│ 會在期限內把它加進 Merkle tree）       │
   │── ③ 把多個 SCT 放進正式憑證並簽發 ──► 網站部署 ──── TLS 交握 ─────►│
   │                           │                       ④ 檢查 SCT 數量與 log 是否受信任
   │                           │◄── ⑤ monitor（Rita 的監控、CA、研究者）持續下載新項目
   │                           │       發現 *.shengsheng.example 出現陌生的 issuer → 告警
```

這張圖的 ① 到 ③ 發生在簽發時：CA 先把一份「預備憑證」送進多個 log，每個 log 回傳一個 **SCT**（Signed Certificate Timestamp，log 對「我會收錄這張憑證」的簽章承諾），CA 再把這些 SCT 寫進正式憑證。④ 瀏覽器在交握時檢查憑證是否帶有足夠數量、來自受信任 log 的 SCT，沒有的話就拒絕，所以「不登錄 CT 的公開憑證」實際上不能用。⑤ 是 CT 真正發揮作用的地方：monitor 持續讀取 log 的新項目，網域擁有者可以用公開的 CT 搜尋服務或自建的監控，在自家網域出現非預期的憑證時收到通知。

log 的「只能附加」是用 **Merkle tree**（雜湊樹）保證的：每一筆項目是一片葉子，兩兩雜湊成上一層，最後得到一個代表整個 log 的 tree head。log 定期簽署 tree head，任何人都能用少量雜湊驗證「某筆憑證確實在樹裡」（inclusion proof），或驗證「新的樹包含舊的樹」（consistency proof，證明 log 沒有偷偷改寫歷史）。下面的程式依 RFC 6962 的規則建出一棵 7 筆的樹，並驗證其中一筆：

```python
import hashlib


def leaf_hash(entry: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + entry).digest()   # 0x00 前綴：葉節點


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()  # 0x01 前綴：內部節點


def split(n):  # 小於 n 的最大 2 的冪次（RFC 6962 的切法）
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def mth(entries):
    if len(entries) == 1:
        return leaf_hash(entries[0])
    k = split(len(entries))
    return node_hash(mth(entries[:k]), mth(entries[k:]))


def audit_path(m, entries):
    """證明第 m 筆在樹裡所需的兄弟節點雜湊（由下往上）。"""
    if len(entries) == 1:
        return []
    k = split(len(entries))
    if m < k:
        return audit_path(m, entries[:k]) + [("R", mth(entries[k:]))]
    return audit_path(m - k, entries[k:]) + [("L", mth(entries[:k]))]


def verify(entry, path, root):
    h = leaf_hash(entry)
    for side, sibling in path:
        h = node_hash(h, sibling) if side == "R" else node_hash(sibling, h)
    return h == root


log = [f"precert:{name}".encode() for name in
       ["www.shengsheng.example", "auth.shengsheng.example", "rt.shengsheng.example",
        "api.shengsheng.example", "shop.example.org", "news.example.net", "auth.shengsheng.example#2"]]
root = mth(log)
path = audit_path(1, log)
print(f"log 有 {len(log)} 筆，tree head = {root.hex()[:16]}…")
print(f"證明第 1 筆（auth）只需要 {len(path)} 個雜湊：{[side for side, _ in path]}")
print("驗證 auth 在 log 裡：", verify(log[1], path, root))
print("拿同一條路徑驗證偽造的項目：", verify(b"precert:auth.attacker.example", path, root))
assert verify(log[1], path, root) and len(path) == 3
assert all(verify(e, audit_path(i, log), root) for i, e in enumerate(log))
```

```text
log 有 7 筆，tree head = 4244877e8bf36850…
證明第 1 筆（auth）只需要 3 個雜湊：['L', 'R', 'R']
驗證 auth 在 log 裡： True
拿同一條路徑驗證偽造的項目： False
```

輸出的第二行是重點：7 筆資料的樹，證明其中一筆只需要 3 個雜湊，一般而言是 log₂(n) 個，所以即使 log 有數十億筆，證明也只有幾十個雜湊。葉子與內部節點用不同的前綴（0x00 與 0x01）雜湊，是為了防止有人把內部節點冒充成葉子。最後一行說明偽造的項目無法通過同一條路徑的驗證。

CT 對營運者有兩個實際影響。第一是**監控**：Rita 在事故後把 `shengsheng.example` 加進 CT 監控，任何新憑證出現時都比對 issuer 與預期的 CA 清單，順便也成了「憑證有沒有如期更新」的旁證。第二是**資訊外露**：所有公開憑證的名稱都會出現在 CT log 上，替 `ops.shengsheng.example` 這種內部主機申請公開憑證，等於公告了它的存在。內部主機可以改用 wildcard 憑證，或用內部私有 CA（第 18、30 章），私有 CA 簽發的憑證不需要登錄 CT。

> [!note] 2026 現況
> 截至 2026 年 10 月，CT 仍以 RFC 6962 的機制為主，瀏覽器對 SCT 數量與 log 的要求依各自的 CT 政策而定，並會隨效期縮短而調整。CT log 的營運方式也在演進，出現以靜態檔案形式提供資料、降低營運成本的新型 log。對網站營運者來說重點不變：CA 會替你登錄，你要做的是監控。

## 19.11 TLS 要在哪裡終結：CDN、LB 還是應用

**TLS 終結**（TLS termination）指的是在哪一個元件解開 TLS、看到明文 HTTP。這個位置決定了私鑰放在哪裡、誰能看到請求內容、client IP 怎麼往後傳，也決定了憑證要在哪裡更新。聲聲 Live 剛好三種都有：

```text
 ① 終結在 CDN（www）
   瀏覽器 ══TLS══► CDN edge 203.0.113.10 ──TLS（重新加密）──► 源站 LB ──► nginx
                   憑證：CDN 受管          憑證：源站自己的（只需 CDN 信任）

 ② 終結在 L7 LB（api、auth）
   App／瀏覽器 ══TLS══► LB 203.0.113.80（依 SNI 選憑證）──HTTP 或 TLS──► nginx ──► gunicorn
                        X-Forwarded-For／X-Forwarded-Proto 帶給後端

 ③ 穿透 L4 LB，終結在 nginx（rt）
   瀏覽器 ══TLS══► L4 LB 203.0.113.40（只轉 TCP，不解密）══TLS══► nginx 10.20.2.11~13 ──► uvicorn
                   看不到 HTTP；client IP 用 PROXY protocol 傳遞
```

① 讓 CDN 在離使用者最近的地方完成交握，對遠方的使用者而言，交握所需的往返不必橫越大洋（第 1 章的美國學生範例 RTT 是 180 ms），而且 CDN 要看得到明文才能快取。代價是 CDN 握有能代表 `www` 的憑證，請求內容在 CDN 上是明文；CDN 到源站的那一段也應該重新加密，否則等於讓明文在網際網路上跑。② 是最常見的 API 架構：LB 統一管理憑證、做 HTTP 路由、加上 `X-Forwarded-For` 讓後端知道原始 client IP（第 25 章會談信任邊界）。③ 用在 WebSocket 這類長連線，或需要後端自己看到 client 憑證（mTLS，第 18 章）的情境，LB 只轉 TCP，憑證與私鑰要放在每一台 nginx 上，這正是 19.7 節多副本分發的由來。

| 終結位置 | 優點 | 代價與風險 | 憑證放在哪裡 |
|---|---|---|---|
| CDN edge | 交握離使用者最近、可快取、可擋 DDoS | CDN 看得到明文；CAA 要包含 CDN 的 CA；源站段要另外加密 | CDN 受管或上傳給 CDN |
| L7 LB | 集中管理憑證、HTTP 路由、WAF | LB 到後端若是明文，內網要能信任；client IP 靠 header 傳遞 | LB（受管或匯入） |
| L4 穿透到應用層 | 端到端加密、後端可做 mTLS、LB 不碰私鑰 | 每台副本都要有憑證與私鑰；LB 不能看 HTTP | 每台 nginx／應用程式 |
| 應用程式本身（gunicorn、uvicorn 直接開 TLS） | 架構最簡單，適合內部服務 | 交握 CPU 與憑證輪替都落在應用程式；reload 要自己處理 | 應用程式主機 |

選擇時可以問三個問題。第一，誰需要看到明文？要快取或做 L7 路由，就必須在那一層終結。第二，私鑰可以放在誰手上？法規或合約要求私鑰不出自家環境時，CDN 的選項就受限。第三，後端需要知道什麼？需要 client 憑證或真實 client IP，就要設計好 mTLS 的位置或 PROXY protocol。現實中多半是組合：外面一層終結在 CDN 或 LB，內部服務之間再用 mTLS（第 30 章）。

## 19.12 動手做：到期監控、ACME challenge 與 HSTS

這一節有三個實驗，都可以離線執行。實驗一的憑證資料是模擬的，但格式與 Python `ssl` 模組真實回傳的一樣；實驗二在 127.0.0.1 上起兩台 HTTP 伺服器當副本，讓模擬的 CA 真的透過 HTTP 去驗證；實驗三實作 HSTS header 的解析與瀏覽器端的判斷。

### 實驗一：從外部看每個端點的憑證到期監控器

連上一個 TLS 伺服器後，`SSLSocket.getpeercert()` 會回傳一個 dict，裡面有 `subject`、`issuer`、`subjectAltName`、`notBefore`、`notAfter`、`serialNumber` 等欄位，時間格式是 `Oct  1 00:00:00 2026 GMT`，可以用標準函式庫的 `ssl.cert_time_to_seconds()` 轉成時間戳。真正的監控器會逐一連線到每個「名稱＋位址」，這裡直接把巡檢結果寫成同樣格式的 dict，專心處理判斷邏輯：依效期比例判斷是否該換卻沒換、名稱是否相符、鏈是否完整，以及同一名稱的副本是否送出不同的憑證。

```python
import datetime as dt
import hashlib
import ssl

UTC = dt.timezone.utc


def peer(cn, sans, not_before, not_after, issuer, chain_len, serial):
    """模擬 SSLSocket.getpeercert() 回傳的 dict（欄位名稱與日期格式照真實的寫）。"""
    return {
        "subject": ((("commonName", cn),),),
        "issuer": ((("organizationName", issuer),),),
        "subjectAltName": tuple(("DNS", s) for s in sans),
        "notBefore": not_before,
        "notAfter": not_after,
        "serialNumber": serial,
        "_chain_len": chain_len,  # 真實情況要另外取得 server 送出的整條鏈，這裡直接給數字
    }


# (主機名稱, 連到的位址) → 該位址送出的憑證；同一個名稱可能有多個副本
OBSERVED = {
    ("www.shengsheng.example", "203.0.113.10"): peer(
        "www.shengsheng.example", ["www.shengsheng.example", "shengsheng.example"],
        "Aug 30 00:00:00 2026 GMT", "Nov 28 00:00:00 2026 GMT", "CDN Managed CA", 2, "0A11"),
    ("auth.shengsheng.example", "203.0.113.80"): peer(
        "auth.shengsheng.example", ["auth.shengsheng.example"],
        "Mar 16 00:00:00 2026 GMT", "Oct  1 00:00:00 2026 GMT", "Example OV CA", 2, "7C03"),
    ("rt.shengsheng.example", "10.20.2.11"): peer(
        "rt.shengsheng.example", ["rt.shengsheng.example"],
        "Sep 10 00:00:00 2026 GMT", "Dec  9 00:00:00 2026 GMT", "Example ACME CA", 2, "B2F1"),
    ("rt.shengsheng.example", "10.20.2.12"): peer(
        "rt.shengsheng.example", ["rt.shengsheng.example"],
        "Sep 10 00:00:00 2026 GMT", "Dec  9 00:00:00 2026 GMT", "Example ACME CA", 2, "B2F1"),
    ("rt.shengsheng.example", "10.20.2.13"): peer(  # 這台沒有 reload，還在送舊憑證
        "rt.shengsheng.example", ["rt.shengsheng.example"],
        "Jul 12 00:00:00 2026 GMT", "Oct 10 00:00:00 2026 GMT", "Example ACME CA", 2, "91D4"),
    ("api.shengsheng.example", "203.0.113.80"): peer(
        "api.shengsheng.example", ["api.shengsheng.example", "api-lb.shengsheng.example"],
        "Jul  1 00:00:00 2026 GMT", "Dec 28 00:00:00 2026 GMT", "Example Issuing CA 2", 1, "5A01"),
}


def ts(text):  # ssl.cert_time_to_seconds 是標準函式庫解析憑證時間格式的工具
    return dt.datetime.fromtimestamp(ssl.cert_time_to_seconds(text), UTC)


def evaluate(host, addr, cert, now):
    nb, na = ts(cert["notBefore"]), ts(cert["notAfter"])
    lifetime = (na - nb).total_seconds() / 86400
    left = (na - now).total_seconds() / 86400
    renew_at = nb + (na - nb) * 2 / 3           # 預期在用掉三分之二效期時更新
    overdue = (now - renew_at).total_seconds() / 86400
    problems = []
    if host not in [v for k, v in cert["subjectAltName"] if k == "DNS"]:
        problems.append("名稱不符")
    if cert["_chain_len"] < 2:
        problems.append("缺中間憑證")
    if left <= 0:
        level = "EXPIRED"
    elif left < max(lifetime * 0.10, 1):        # 依效期比例，而不是固定 30 天
        level = "CRITICAL"
    elif overdue > max(lifetime * 0.05, 1):     # 該更新卻沒換：自動化壞了的訊號
        level = "WARNING"
    else:
        level = "OK"
    if problems and level == "OK":
        level = "WARNING"
    return level, lifetime, left, renew_at, problems


def run(now):
    print(f"巡檢時間 {now:%Y-%m-%d %H:%M} UTC")
    print(f"{'host':<24}{'addr':<14}{'life':>5}{'left':>7}  {'renew_by':<11}{'status':<9}note")
    serials, results = {}, {}
    for (host, addr), cert in OBSERVED.items():
        level, life, left, renew_at, problems = evaluate(host, addr, cert, now)
        serials.setdefault(host, set()).add(cert["serialNumber"])
        results[(host, addr)] = level
        print(f"{host:<24}{addr:<14}{life:>4.0f}d{left:>6.1f}d  {renew_at:%Y-%m-%d} {level:<9}{'、'.join(problems)}")
    for host, s in serials.items():
        if len(s) > 1:  # 同一個名稱的副本送出不同憑證：有副本沒拿到或沒載入新憑證
            print(f"!! {host} 的副本送出 {len(s)} 張不同憑證（serial {sorted(s)}）")
    return results


def first_alert_day(lifetime, rule):
    """新憑證簽發後第幾天第一次告警（假設自動更新壞了，一直沒換）。"""
    day = 0.0
    while day <= lifetime:
        left = lifetime - day
        if rule == "fixed30" and left < 30:
            return day
        if rule == "ratio" and day > lifetime * 2 / 3 + max(lifetime * 0.05, 1):
            return day
        day += 0.25
    return None


result = run(dt.datetime(2026, 9, 24, 1, 0, tzinfo=UTC))
auth = OBSERVED[("auth.shengsheng.example", "203.0.113.80")]
nb, na = ts(auth["notBefore"]), ts(auth["notAfter"])
for probe in (nb + dt.timedelta(days=d) for d in range(0, 200)):
    if evaluate("auth.shengsheng.example", "", auth, probe)[0] != "OK":
        print(f"回放：auth 的憑證若早有這個監控，{probe:%Y-%m-%d} 就會第一次告警（距到期 {(na - probe).days} 天）")
        break
print()
print("lifetime  fixed-30d 規則第幾天響  比例規則第幾天響  比例規則響時剩幾天")
for life in (199, 90, 47, 6):
    f, r = first_alert_day(life, "fixed30"), first_alert_day(life, "ratio")
    print(f"{life:>6}d  {f:>18.1f}  {r:>16.1f}  {life - r:>16.1f}")
assert result[("auth.shengsheng.example", "203.0.113.80")] == "CRITICAL"
assert result[("rt.shengsheng.example", "10.20.2.13")] == "WARNING"
assert result[("api.shengsheng.example", "203.0.113.80")] == "WARNING"
assert first_alert_day(6, "fixed30") == 0   # 6 天憑證一簽發就「快過期」：固定門檻全是噪音
```

```text
巡檢時間 2026-09-24 01:00 UTC
host                    addr           life   left  renew_by   status   note
www.shengsheng.example  203.0.113.10    90d  65.0d  2026-10-29 OK       
auth.shengsheng.example 203.0.113.80   199d   7.0d  2026-07-26 CRITICAL 
rt.shengsheng.example   10.20.2.11      90d  76.0d  2026-11-09 OK       
rt.shengsheng.example   10.20.2.12      90d  76.0d  2026-11-09 OK       
rt.shengsheng.example   10.20.2.13      90d  16.0d  2026-09-10 WARNING  
api.shengsheng.example  203.0.113.80   180d  95.0d  2026-10-29 WARNING  缺中間憑證
!! rt.shengsheng.example 的副本送出 2 張不同憑證（serial ['91D4', 'B2F1']）
回放：auth 的憑證若早有這個監控，2026-08-06 就會第一次告警（距到期 56 天）

lifetime  fixed-30d 規則第幾天響  比例規則第幾天響  比例規則響時剩幾天
   199d               169.2             142.8              56.2
    90d                60.2              64.8              25.2
    47d                17.2              33.8              13.2
     6d                 0.0               5.2               0.8
```

這份輸出模擬的是事故前一週（9 月 24 日）的巡檢，逐行解讀：

1. `www` 由 CDN 代管，90 天效期還剩 65 天，應更新日在 10 月 29 日，狀態 OK。
2. `auth` 的效期是 199 天，剩 7 天，已經低於效期的一成（19.9 天），所以是 CRITICAL。如果這個監控早就存在，事故前一週會有人被叫醒。
3. `rt` 的三台副本中，10.20.2.11 與 .12 送出 9 月 10 日的新憑證，10.20.2.13 還是 7 月的舊憑證：它的應更新日 9 月 10 日已經過了 14 天，超過寬限期（效期的 5%，4.5 天），所以是 WARNING，代表「自動化壞了」。最後一行「副本送出 2 張不同憑證」直接點出根因。
4. `api` 的效期與剩餘天數都正常，但只送出 leaf 一張，被標成「缺中間憑證」。桌面瀏覽器常常不會報錯，所以這種問題可以潛伏很久，直到某個 App 或伺服器端的 client 失敗。
5. 「回放」那一行把 auth 的憑證從簽發日逐日回放：用比例規則，8 月 6 日就會第一次告警，距離到期還有 56 天，有充裕的時間處理。

最後的表格比較兩種告警規則在不同效期下的表現，假設自動更新一直壞著。固定 30 天的規則在 199 天的憑證上要到第 169 天才響，只剩 30 天；在 47 天的憑證上，第 17 天就響，那時根本還沒到該更新的時間，是噪音；在 6 天的短效憑證上，第 0 天就響，完全不能用。比例規則則在每一種效期下都在「該換卻沒換」的時候響，而且都還保留效期約四分之一以上的處理時間（6 天憑證保留約 0.8 天）。要把這個程式變成真的監控器，只要把 `OBSERVED` 換成實際連線：用 `ssl.create_default_context()` 建立 context、`create_connection((addr, 443))` 連到每一台副本、`wrap_socket(sock, server_hostname=host)` 帶上 SNI，再呼叫 `getpeercert()`。

### 實驗二：模擬 ACME 與 HTTP-01 驗證（含多副本陷阱）

這個實驗用 Python 實作一個極簡的 ACME server 與 client：帳號註冊、nonce、簽章、下訂單、HTTP-01 驗證、finalize。為了只用標準函式庫，帳號金鑰用 HMAC 代替：真實的 ACME 帳號金鑰是非對稱金鑰（例如 ES256 或 RSA），CA 只保存公鑰，任何人都無法冒用帳號簽章；這裡的 HMAC 需要 CA 與 client 共享 secret，在現實中是不安全的，只是用來示範「每個請求都簽章並帶一次性 nonce」的結構。兩台副本是兩個在 127.0.0.1 上的 HTTP 伺服器，模擬的 LB 輪流把 CA 的驗證請求分給它們；CA 對同一個 challenge 驗證三次，代表從多個網路位置交叉驗證。

```python
import base64
import hashlib
import hmac
import http.client
import itertools
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class Account:
    """ACME 帳號。真實 ACME 用非對稱金鑰（例如 ES256）簽 JWS，CA 只保存公鑰；
    這裡用 HMAC 代替簽章，CA 與 client 共享 secret，只是為了只用標準函式庫就能跑。"""

    def __init__(self):
        self.secret = secrets.token_bytes(32)
        self.kid = None

    def thumbprint(self) -> str:  # RFC 7638：JWK 必要欄位依字母排序、無空白，再 SHA-256
        jwk = json.dumps({"k": b64u(self.secret), "kty": "oct"}, sort_keys=True, separators=(",", ":"))
        return b64u(hashlib.sha256(jwk.encode()).digest())

    def jws(self, url, nonce, payload):
        protected = b64u(json.dumps({"alg": "HS256", "nonce": nonce, "url": url, "kid": self.kid}).encode())
        body = b64u(json.dumps(payload).encode()) if payload is not None else ""  # None = POST-as-GET
        sig = hmac.new(self.secret, f"{protected}.{body}".encode(), hashlib.sha256).digest()
        return {"protected": protected, "payload": body, "signature": b64u(sig)}


class FakeCA:
    def __init__(self, resolve):
        self.resolve, self.nonces, self.accounts, self.orders = resolve, set(), {}, {}

    def new_nonce(self):
        n = secrets.token_urlsafe(12)
        self.nonces.add(n)
        return n

    def _verify(self, url, msg):
        hdr = json.loads(base64.urlsafe_b64decode(msg["protected"] + "=="))
        if hdr["nonce"] not in self.nonces:          # 每個 nonce 只能用一次：擋重放
            raise ValueError("urn:ietf:params:acme:error:badNonce")
        self.nonces.discard(hdr["nonce"])
        if hdr["url"] != url:
            raise ValueError("unauthorized: url mismatch")
        secret = self.accounts[hdr["kid"]]
        expect = hmac.new(secret, f"{msg['protected']}.{msg['payload']}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(b64u(expect), msg["signature"]):
            raise ValueError("unauthorized: bad signature")
        return json.loads(base64.urlsafe_b64decode(msg["payload"] + "==")) if msg["payload"] else None

    def new_account(self, secret):
        kid = f"acct/{len(self.accounts) + 1}"
        self.accounts[kid] = secret
        return kid

    def new_order(self, msg):
        names = self._verify("newOrder", msg)["identifiers"]
        oid = f"order/{len(self.orders) + 1}"
        self.orders[oid] = {"status": "pending", "names": names, "token": secrets.token_urlsafe(16), "thumb": None}
        return oid, self.orders[oid]["token"]

    def respond_challenge(self, oid, msg, thumbprint, perspectives=3):
        self._verify(f"chall/{oid}", msg)          # client 說「我放好了，請來驗」
        order = self.orders[oid]
        expected = f"{order['token']}.{thumbprint}"
        results = []
        for _ in range(perspectives):             # 從多個網路位置各驗一次（MPIC 的概念）
            host, port = self.resolve(order["names"][0])
            conn = http.client.HTTPConnection(host, port, timeout=2)
            conn.request("GET", f"/.well-known/acme-challenge/{order['token']}",
                         headers={"Host": order["names"][0]})
            resp = conn.getresponse()
            results.append((resp.status, resp.read().decode() == expected))
            conn.close()
        order["status"] = "ready" if all(ok for _, ok in results) else "invalid"
        return results

    def finalize(self, oid, msg):
        csr = self._verify(f"finalize/{oid}", msg)
        order = self.orders[oid]
        if order["status"] != "ready" or sorted(csr["names"]) != sorted(order["names"]):
            raise ValueError("urn:ietf:params:acme:error:orderNotReady")
        order["status"] = "valid"                  # 真實流程中間還有 processing
        return {"names": csr["names"], "lifetime_days": 90}


def replica(store):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            token = self.path.rsplit("/", 1)[-1]
            body = store.get(token)
            self.send_response(200 if body else 404)
            self.end_headers()
            self.wfile.write((body or "not found").encode())

        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def issue(shared_store):
    store_a, store_b = {}, {}
    if shared_store:
        store_b = store_a                          # 兩台副本讀同一個 challenge 儲存
    replicas = [replica(store_a), replica(store_b)]
    rr = itertools.cycle(replicas)                 # LB 輪流分配，模擬 DNS 指向 LB
    ca = FakeCA(lambda name: next(rr).server_address)
    acct = Account()
    acct.kid = ca.new_account(acct.secret)
    oid, token = ca.new_order(acct.jws("newOrder", ca.new_nonce(), {"identifiers": ["rt.shengsheng.example"]}))
    store_a[token] = f"{token}.{acct.thumbprint()}"  # ACME client 只寫進它所在的副本 A
    results = ca.respond_challenge(oid, acct.jws(f"chall/{oid}", ca.new_nonce(), {}), acct.thumbprint())
    print(f"shared_store={shared_store!s:<5} 驗證結果 {results} → order {ca.orders[oid]['status']}")
    if ca.orders[oid]["status"] == "ready":
        cert = ca.finalize(oid, acct.jws(f"finalize/{oid}", ca.new_nonce(), {"names": ["rt.shengsheng.example"]}))
        print(f"  簽發：{cert}，order {ca.orders[oid]['status']}")
    for r in replicas:
        r.shutdown(); r.server_close()
    return ca, acct, token


issue(shared_store=False)
ca, acct, token = issue(shared_store=True)
assert ca.orders["order/1"]["status"] == "valid"

key_authz = f"{token}.{acct.thumbprint()}"
digest = hashlib.sha256(key_authz.encode()).digest()
print("HTTP-01  回應內容 = key authorization（token.thumbprint）")
print(f"DNS-01   TXT 值   = base64url(SHA-256(key authz))，{len(b64u(digest))} 個字元")
print(f"TLS-ALPN-01 憑證的 acmeIdentifier 擴充 = SHA-256(key authz) 原始 {len(digest)} bytes")
assert key_authz.split(".")[1] == acct.thumbprint() and len(b64u(digest)) == 43

replay = acct.jws("newOrder", ca.new_nonce(), {"identifiers": ["www.shengsheng.example"]})
ca.new_order(replay)
try:
    ca.new_order(replay)                           # 同一個 JWS 再送一次
except ValueError as e:
    print("重放同一個請求：", e)
    assert "badNonce" in str(e)
```

```text
shared_store=False 驗證結果 [(200, True), (404, False), (200, True)] → order invalid
shared_store=True  驗證結果 [(200, True), (200, True), (200, True)] → order ready
  簽發：{'names': ['rt.shengsheng.example'], 'lifetime_days': 90}，order valid
HTTP-01  回應內容 = key authorization（token.thumbprint）
DNS-01   TXT 值   = base64url(SHA-256(key authz))，43 個字元
TLS-ALPN-01 憑證的 acmeIdentifier 擴充 = SHA-256(key authz) 原始 32 bytes
重放同一個請求： urn:ietf:params:acme:error:badNonce
```

逐行解讀：

1. 第一次執行時，ACME client 只把驗證內容寫在自己所在的副本 A。CA 的三次驗證被 LB 輪流分到 A、B、A，B 回 404，整個 authorization 失敗，訂單變成 invalid。這就是 `rt` 在事故前每隔幾次更新就失敗一次的原因：只要有一次驗證請求打到沒有檔案的副本，整張訂單就作廢。
2. 第二次讓兩台副本共用同一個 challenge 儲存（實務上可以是共用的儲存空間，或讓 LB 把 `/.well-known/acme-challenge/` 統一導到一個地方），三次驗證都成功，訂單依序經過 ready、finalize，最後變成 valid 並簽發。
3. 接下來三行對照三種 challenge 的內容：HTTP-01 直接回傳 key authorization 原文；DNS-01 放的是它的 SHA-256 經 base64url 編碼，固定是 43 個字元；TLS-ALPN-01 則把同一個 SHA-256 的原始 32 bytes 放進驗證用憑證的擴充欄位。三者的源頭都是同一個 `token.thumbprint`。
4. 最後一行把同一個已簽章的請求重送一次：簽章本身完全合法，但 nonce 已經用過，CA 回 `badNonce`。這說明 nonce 擋的是「重放」，而簽章擋的是「偽造」，兩者缺一不可。

### 實驗三：解析 HSTS header 並模擬瀏覽器的判斷

這個實驗依 RFC 6797 的語法解析 `Strict-Transport-Security`，模擬瀏覽器收到回應時的決定，並檢查是否符合 preload 的條件；後半段模擬瀏覽器的 HSTS 紀錄，判斷一個 `http` 網址會不會在送出前被改寫成 HTTPS。

```python
import ipaddress
import re

TOKEN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
PRELOAD_MIN = 31_536_000  # preload 清單要求至少一年


def parse_sts(value: str) -> dict:
    """依 RFC 6797 的語法解析 Strict-Transport-Security；任何違規都讓整個 header 無效。"""
    seen = {}
    for raw in value.split(";"):
        part = raw.strip()
        if not part:
            continue                                  # 允許空的 directive（例如結尾多一個分號）
        name, sep, val = part.partition("=")
        name, val = name.strip().lower(), val.strip()  # directive 名稱不分大小寫
        if not TOKEN.match(name):
            raise ValueError(f"directive 名稱不合法：{name!r}")
        if val.startswith('"') and val.endswith('"') and len(val) >= 2:
            val = val[1:-1]                           # 值可以是 quoted-string
        if name in seen:
            raise ValueError(f"directive 重複：{name}")  # 每個 directive 最多出現一次
        seen[name] = val if sep else None
    if "max-age" not in seen:
        raise ValueError("缺少 max-age")
    if seen["max-age"] is None or not seen["max-age"].isdigit():
        raise ValueError(f"max-age 必須是十進位整數：{seen['max-age']!r}")
    return {"max_age": int(seen["max-age"]),
            "include_subdomains": "includesubdomains" in seen,
            "preload": "preload" in seen}


def evaluate(header, scheme, host):
    """模擬瀏覽器收到這個回應時的決定。"""
    try:
        ipaddress.ip_address(host)
        return "忽略：IP 位址不能成為 HSTS host"
    except ValueError:
        pass
    if scheme != "https":
        return "忽略：HTTP 回應中的 STS header 不算數（可能被竄改）"
    try:
        sts = parse_sts(header)
    except ValueError as e:
        return f"忽略：header 無效（{e}）"
    if sts["max_age"] == 0:
        return "刪除這個 host 的 HSTS 紀錄"
    age = sts["max_age"]
    verdict = (f"記住 {age // 86400} 天" if age >= 86400 else f"記住 {age} 秒") + ("，含子網域" if sts["include_subdomains"] else "")
    gaps = []
    if sts["max_age"] < PRELOAD_MIN:
        gaps.append("max-age 不足一年")
    if not sts["include_subdomains"]:
        gaps.append("缺 includeSubDomains")
    if not sts["preload"]:
        gaps.append("缺 preload")
    return verdict + ("；可申請 preload" if not gaps else f"；preload 不合格：{'、'.join(gaps)}")


CASES = [
    ("https", "www.shengsheng.example", "max-age=31536000; includeSubDomains; preload"),
    ("https", "www.shengsheng.example", 'MAX-AGE="63072000";includesubdomains;preload;'),
    ("https", "www.shengsheng.example", "max-age=300"),
    ("https", "www.shengsheng.example", "max-age=86400; max-age=31536000"),
    ("https", "www.shengsheng.example", "includeSubDomains; preload"),
    ("https", "www.shengsheng.example", "max-age=1y; includeSubDomains"),
    ("http", "www.shengsheng.example", "max-age=31536000"),
    ("https", "203.0.113.10", "max-age=31536000"),
    ("https", "www.shengsheng.example", "max-age=0"),
]
results = []
for scheme, host, header in CASES:
    out = evaluate(header, scheme, host)
    results.append(out)
    print(f"{scheme:<5} {header:<48} → {out}")

assert results[0].endswith("可申請 preload") and results[1].endswith("可申請 preload")
assert "重複" in results[3] and "缺少 max-age" in results[4] and "十進位" in results[5]
assert results[6].startswith("忽略") and results[7].startswith("忽略") and results[8].startswith("刪除")


def known(store, host, now):
    """瀏覽器發請求前的判斷：這個 host（或它的上層網域）是不是已知 HSTS host？"""
    labels = host.split(".")
    for i in range(len(labels)):
        cand = ".".join(labels[i:])
        entry = store.get(cand)
        if entry and now < entry["expires"] and (i == 0 or entry["include_subdomains"]):
            return cand
    return None


store = {"shengsheng.example": {"expires": 31_536_000, "include_subdomains": True},
         "pay.example.net": {"expires": 300, "include_subdomains": False}}
for host, now in [("shengsheng.example", 10), ("auth.shengsheng.example", 10),
                  ("legacy.ops.shengsheng.example", 10), ("cdn.pay.example.net", 10),
                  ("pay.example.net", 10), ("pay.example.net", 301)]:
    hit = known(store, host, now)
    print(f"t={now:>3}s  http://{host:<32} → {'改寫成 https（依 ' + hit + '）' if hit else '照原樣送出'}")
assert known(store, "legacy.ops.shengsheng.example", 10) == "shengsheng.example"
assert known(store, "pay.example.net", 301) is None
```

```text
https max-age=31536000; includeSubDomains; preload     → 記住 365 天，含子網域；可申請 preload
https MAX-AGE="63072000";includesubdomains;preload;    → 記住 730 天，含子網域；可申請 preload
https max-age=300                                      → 記住 300 秒；preload 不合格：max-age 不足一年、缺 includeSubDomains、缺 preload
https max-age=86400; max-age=31536000                  → 忽略：header 無效（directive 重複：max-age）
https includeSubDomains; preload                       → 忽略：header 無效（缺少 max-age）
https max-age=1y; includeSubDomains                    → 忽略：header 無效（max-age 必須是十進位整數：'1y'）
http  max-age=31536000                                 → 忽略：HTTP 回應中的 STS header 不算數（可能被竄改）
https max-age=31536000                                 → 忽略：IP 位址不能成為 HSTS host
https max-age=0                                        → 刪除這個 host 的 HSTS 紀錄
t= 10s  http://shengsheng.example               → 改寫成 https（依 shengsheng.example）
t= 10s  http://auth.shengsheng.example          → 改寫成 https（依 shengsheng.example）
t= 10s  http://legacy.ops.shengsheng.example    → 改寫成 https（依 shengsheng.example）
t= 10s  http://cdn.pay.example.net              → 照原樣送出
t= 10s  http://pay.example.net                  → 改寫成 https（依 pay.example.net）
t=301s  http://pay.example.net                  → 照原樣送出
```

逐行解讀上半段的九個案例：

1. 標準的 preload 設定，記住 365 天、含子網域，符合 preload 條件。
2. 大小寫混用、值加上引號、結尾多一個分號，全部合法，這說明解析器不能用字串完全比對。
3. `max-age=300` 合法，是 19.9 節導入流程的第一步；離 preload 條件還差三項。
4. `max-age` 出現兩次，整個 header 無效。這常發生在應用程式和 nginx 各加了一次 header，再被 LB 合併。
5. 缺 `max-age`、第 6 行寫成 `1y`，都讓整個 header 被忽略。注意瀏覽器不會報錯，網站只是「以為」自己有 HSTS。
6. 第 7 行是 HTTP 回應，第 8 行的主機是 IP 位址，兩者都被忽略。
7. 第 9 行的 `max-age=0` 會刪除紀錄，這是緊急關閉 HSTS 的唯一方法，但只對「之後還會連上 HTTPS 收到這個回應」的瀏覽器有效，對 preload list 無效。

下半段模擬瀏覽器記住 `shengsheng.example`（含子網域，一年）與 `pay.example.net`（不含子網域，300 秒）之後的行為：`auth` 與多層的 `legacy.ops` 都被 `shengsheng.example` 的 includeSubDomains 涵蓋而改寫，這正是內部只開 HTTP 的後台會突然打不開的原因；`cdn.pay.example.net` 不受影響，因為那筆紀錄沒有 includeSubDomains；`pay.example.net` 的紀錄在 301 秒後過期，請求又照原樣送出。

## 19.13 在工作上怎麼用

事故後，阿德和小晴把這次學到的東西整理成依角色分工的清單。

**SRE：把「從外部看」變成例行監控，並準備好一組查證指令。** 每個對外名稱、每台副本都要納入實驗一那種監控；告警用效期比例，而不是固定天數。出事時，先用下面這組指令在幾分鐘內確認實際送出的憑證：

```bash
# 看送出的整條鏈（-showcerts）、名稱與期限；-servername 指定 SNI
echo | openssl s_client -connect 203.0.113.80:443 -servername auth.shengsheng.example -showcerts 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
# 只看驗證結果：0 (ok)、10 已過期、9 尚未生效、20/21 鏈不完整、62 名稱不符
echo | openssl s_client -connect 203.0.113.80:443 -servername auth.shengsheng.example \
  -verify_hostname auth.shengsheng.example 2>&1 | grep 'Verify return code'
# 檢查 OCSP stapling：看到 "OCSP response: no response sent" 代表沒有 staple
echo | openssl s_client -connect 203.0.113.80:443 -servername auth.shengsheng.example -status 2>/dev/null | grep -A2 'OCSP'
# 確認私鑰與憑證是同一對：兩個雜湊必須相同
openssl x509 -noout -pubkey -in fullchain.pem | openssl sha256
openssl pkey -pubout -in privkey.pem | openssl sha256
# HTTP 是否轉到 HTTPS、HSTS header 是否只出現一次
curl -sI http://www.shengsheng.example/ | grep -i '^location'
curl -sI https://www.shengsheng.example/ | grep -ci '^strict-transport-security'
```

這組指令依「憑證本身 → 驗證結果 → 撤銷資訊 → 檔案配對 → HTTP 層」的順序排列。第二條的 `-verify_hostname` 很重要，因為第 3 章提過，`s_client` 預設不檢查名稱，名稱不符時仍可能顯示 `0 (ok)`。最後一條數出 HSTS header 的行數，結果應該是 1，大於 1 就要回頭檢查實驗三的「directive 重複」問題。

**後端工程師：讀懂錯誤訊息，不要關掉驗證。** client 端遇到憑證錯誤時，下表能把不同工具的訊息對應回同一個原因：

| 原因 | 瀏覽器（Chrome） | curl | Python `ssl` |
|---|---|---|---|
| 已過期 | `NET::ERR_CERT_DATE_INVALID` | `certificate has expired` | `certificate verify failed: certificate has expired` |
| 尚未生效（多半是 client 時鐘錯） | `NET::ERR_CERT_DATE_INVALID` | `certificate is not yet valid` | `certificate verify failed: certificate is not yet valid` |
| 缺中間憑證 | 常常不報錯（會自行補鏈） | `unable to get local issuer certificate` | `certificate verify failed: unable to get local issuer certificate` |
| 名稱不符 | `NET::ERR_CERT_COMMON_NAME_INVALID` | `no alternative certificate subject name matches target host name` | `certificate verify failed: Hostname mismatch, certificate is not valid for …` |
| 不受信任的 CA（自簽、私有 CA） | `NET::ERR_CERT_AUTHORITY_INVALID` | `self-signed certificate in certificate chain` 等 | `certificate verify failed: self-signed certificate in certificate chain` 等 |

這張表最重要的一列是「缺中間憑證」：瀏覽器常常不報錯，是因為瀏覽器可能已經快取了那張中間憑證，或者會依憑證裡的 AIA 欄位自己去下載，但 curl、Python 與多數 App 不會。所以「我用瀏覽器打開正常」不能證明部署正確。另一個原則是：遇到驗證錯誤時，永遠不要用 `verify=False` 或 `ssl._create_unverified_context()` 繞過，那等於把 TLS 的身分驗證整個關掉；內部私有 CA 的情境，正確做法是用 `cafile` 指定信任的 CA。

**判斷流程。** 收到「憑證錯誤」的回報時，阿德的判斷順序是：

```text
 回報：憑證錯誤
   │
   ├─ 所有人都壞？ ── 是 ─► openssl s_client 看 notAfter ─► 過期：緊急更新＋查自動化為何沒換
   │       │                                            └► 沒過期：看 Verify return code（鏈、名稱）
   │       └ 否
   ├─ 只有部分 client 壞？
   │     ├─► 只有 App／curl／Python：缺中間憑證（-showcerts 只看到一張）
   │     ├─► 只有舊裝置：鏈或根憑證太新、不支援的 TLS 版本或演算法
   │     └─► 只有部分連線：某台副本送舊憑證（逐台比對 serial）
   └─ 只有單一使用者壞？
         ├─► 「尚未生效」或日期錯：client 時鐘（看截圖或裝置的系統時間）
         └─► 企業網路、防毒軟體做 TLS 攔截：看 issuer 是不是陌生的 CA
```

這個流程的第一刀是「影響範圍」：全部壞通常是伺服器端的憑證本身；部分壞通常是鏈、副本或 client 差異；單一使用者壞則幾乎都在 client 端。故事裡的三個問題，剛好各落在三個分支。

**前端與 App 工程師。** 使用者回報「連線不安全」時，請對方截下完整的錯誤代碼與裝置時間；不要在 App 裡寫死憑證或公鑰（pinning），除非有完整的備用金鑰與更新計畫。網頁混用 HTTP 資源（mixed content）會被瀏覽器擋下，上線前用 DevTools 的 Console 檢查。

**資安工程師。** Rita 的清單包括：CT 監控 `shengsheng.example` 的所有新憑證並比對 issuer；CAA 只列出實際使用的 CA，並在換 CA 前先更新；DNS-01 的 API 憑證只限 `_acme-challenge` 的驗證 zone；私鑰只存在需要的元件中，Secret 存放處的讀取要有稽核紀錄；HSTS 的 includeSubDomains 與 preload 變更要經過子網域盤點。

**影音工程師。** Joe 負責的服務也有憑證：WebRTC 的 signaling 走 `rt` 的 WebSocket（wss），TURN 若提供 TLS 版本（例如在 443 port 上跑 TURN over TLS，讓企業網路裡的學生也能連上），`turn.shengsheng.example` 也需要一張會自動更新的憑證，而且 TURN 伺服器通常要重新啟動或收到訊號才會載入新憑證。直播的 WHEP 觀看端點同樣是 HTTPS。這些都要列進到期監控，不能只監控網站。

## 19.14 常見錯誤與除錯

先用一小段程式釐清最常被誤解的「名稱比對」規則：瀏覽器只看 SAN，萬用字元 `*` 只能代表最左邊的**一整個** label，所以 `*.shengsheng.example` 不涵蓋 `shengsheng.example` 本身，也不涵蓋兩層的 `v2.api.shengsheng.example`。比對不分大小寫。程式的最後兩行也提醒：client 端要從 `ssl.create_default_context()` 開始，它預設就會檢查名稱並要求驗證憑證鏈。

```python
import ssl


def san_matches(pattern: str, host: str) -> bool:
    """簡化版的憑證名稱比對：只看 SAN 的 DNS 名稱，萬用字元只能占最左邊一整個 label。"""
    p, h = pattern.lower().rstrip(".").split("."), host.lower().rstrip(".").split(".")
    if len(p) != len(h):
        return False                             # *.a.example 不涵蓋 a.example，也不涵蓋 x.y.a.example
    if p[0] == "*":
        return len(p) >= 3 and p[1:] == h[1:]    # 不允許 *.example 這種涵蓋整個 TLD 的寫法
    return p == h


SANS = ["*.shengsheng.example", "shengsheng.example"]
for host in ["api.shengsheng.example", "shengsheng.example", "v2.api.shengsheng.example",
             "API.ShengSheng.example", "shengsheng.example.test"]:
    ok = any(san_matches(s, host) for s in SANS)
    print(f"{host:<28} {'符合' if ok else '名稱不符'}")
assert not san_matches("*.shengsheng.example", "v2.api.shengsheng.example")

ctx = ssl.create_default_context()               # client 端正確的起點
print("check_hostname =", ctx.check_hostname, "| verify_mode =", ctx.verify_mode.name,
      "| minimum_version =", ctx.minimum_version.name)
assert ctx.check_hostname and ctx.verify_mode == ssl.CERT_REQUIRED
```

```text
api.shengsheng.example       符合
shengsheng.example           符合
v2.api.shengsheng.example    名稱不符
API.ShengSheng.example       符合
shengsheng.example.test      名稱不符
check_hostname = True | verify_mode = CERT_REQUIRED | minimum_version = TLSv1_2
```

前五行輸出說明 wildcard 的範圍：`api` 符合 `*.shengsheng.example`，主網域靠第二個 SAN 才符合，兩層的 `v2.api` 不符合，大小寫不同仍然符合，而 `shengsheng.example.test` 雖然以 `shengsheng.example` 開頭，卻是完全不同的網域。如果 `v2.api` 也要用 HTTPS，就要另外申請 `*.api.shengsheng.example` 或把名稱直接列進 SAN。最後一行顯示預設 context 的設定；`minimum_version` 的實際值依 Python 與 OpenSSL 的版本而定。

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 所有 client 都報過期，`ERR_CERT_DATE_INVALID` | 憑證過期；自動更新失敗或根本沒有自動化 | `openssl s_client … \| openssl x509 -noout -enddate` | 緊急更新；改用 ACME 或受管憑證；加上依效期比例的外部監控 |
| 瀏覽器正常，App、curl、Python 報 `unable to get local issuer certificate` | 伺服器只送 leaf，沒送中間憑證 | `-showcerts` 只看到一張憑證；`Verify return code: 21` | 改用完整鏈（例如 `fullchain.pem`），順序是 leaf 在前、中間憑證在後，不需附根憑證 |
| `ERR_CERT_COMMON_NAME_INVALID` 或 `Hostname mismatch` | SAN 沒有這個名稱；wildcard 只涵蓋一層；SNI 沒帶或選錯憑證 | `openssl x509 -noout -ext subjectAltName`；用 `-servername` 與不帶 SNI 各連一次比較 | 把名稱加進 SAN；檢查 LB 的 SNI 對應；client 連線時使用名稱而不是 IP |
| 個別使用者看到「尚未生效」或日期錯誤 | client 時鐘錯誤（電池沒電、虛擬機時間漂移）；少數情況是伺服器剛換上 notBefore 在未來的憑證 | 看錯誤截圖的系統時間；伺服器端用 `date -u` 與 NTP 狀態確認 | 請使用者校正時間；伺服器與容器啟用 NTP；不要部署 notBefore 還沒到的憑證 |
| 部分連線拿到舊憑證，錯誤時有時無 | 某台副本沒有 reload，或沒拿到新檔案 | 逐台連線比對 serial | deploy hook 失敗要告警；集中分發後逐台驗證序號 |
| nginx 無法啟動，log 有 `key values mismatch` | 私鑰與憑證不是同一對（換憑證時用錯檔案） | 比對 `openssl x509 -pubkey` 與 `openssl pkey -pubout` 的雜湊 | 換成對應的私鑰；把憑證與私鑰當成一組同時部署 |
| ACME HTTP-01 驗證失敗，回 404 或逾時 | 驗證請求被分到沒有檔案的副本；CDN／WAF 擋住或快取了路徑；port 80 被關閉 | 從外部 `curl` 驗證路徑；看各副本與 CDN 的 log | 共用 challenge 儲存或統一導向；CDN 放行驗證路徑；必要時改用 DNS-01 |
| 驗證成功但訂單最後被 CA 拒絕 | CAA 不包含這家 CA（例如新啟用的 CDN 受管憑證） | `dig CAA shengsheng.example +short` | 在 CAA 加入要用的 CA，等 TTL 過後重試 |
| nginx log 出現 stapling 相關警告，或 Must-Staple 憑證讓部分瀏覽器連不上 | 憑證沒有 OCSP 網址；伺服器連不到 OCSP responder；沒有設定 resolver | `openssl s_client -status` 看有沒有 OCSP response | 沒有 OCSP 網址時關閉 stapling；不要申請 Must-Staple；修正對外連線與 resolver |
| 加上 HSTS 後，內部後台打不開 | includeSubDomains 涵蓋了只有 HTTP 的子網域 | DevTools 看到 `307 Internal Redirect` 後連線失敗 | 先替子網域部署 HTTPS；導入時從小 max-age 開始；必要時送 `max-age=0` |
| 更新排程反覆失敗後，修好了也無法申請 | 撞到 CA 的頻率限制 | ACME 錯誤類型為 `rateLimited`，回應附有可重試時間 | 等限制解除；之後用 staging 測試、失敗時指數退避 |

這張表依「全部壞 → 部分壞 → 單一使用者壞 → 部署與自動化流程」的順序排列，和 19.13 節的判斷流程一致。除錯憑證問題時，最有效的習慣是**永遠從外部、帶著正確的 SNI、對每一台副本各看一次**，而不是登入伺服器看檔案：檔案是新的，不代表 process 載入了它；process 載入了，不代表每一台都載入了。

## 19.15 動手練習

1. **用真實工具看一條鏈**（真實工具）。對任意一個你常用的 HTTPS 網站執行 `openssl s_client -connect <網站>:443 -servername <網站> -showcerts < /dev/null`，數出伺服器送了幾張憑證，並用 `openssl x509 -noout -subject -issuer -dates` 看每一張的 subject 與 issuer。
   答案要點：通常會看到 2 到 3 張，第一張的 issuer 等於第二張的 subject，一路接到某個根憑證的名稱為止；根憑證本身通常不會被送出，因為 client 必須自己擁有它才算信任。算一下 leaf 的 notAfter 減 notBefore，對照 19.5 節的效期規則。

2. **延伸實驗一：加上 ARI 時間窗**（延伸程式）。替 `OBSERVED` 的每張憑證加一個欄位 `ari_window`（開始與結束時間），改寫 `evaluate()`：有時間窗時，以時間窗的結束時間作為「應更新日」，沒有時才用三分之二規則。再加上一張「CA 要求提早更新」的憑證（時間窗落在過去），確認它會被標成 WARNING。
   驗證方法：用 assert 檢查提早更新的那張在巡檢時是 WARNING，其他沒有時間窗的憑證結果不變。思考：為什麼 ARI 建議 client 在時間窗內隨機選時間，而不是窗一開就更新？

3. **延伸實驗二：改成 DNS-01**（延伸程式）。把實驗二的副本換成一個 dict 形式的「DNS zone」，ACME client 把 `base64url(SHA-256(key authorization))` 寫到 `_acme-challenge.rt.shengsheng.example`，CA 改成查這個 dict。再模擬兩台 authoritative server，只有一台更新了 record，觀察多點驗證的結果。
   答案要點：只要有一台 authoritative server 還沒更新，多點驗證就可能失敗，這和 HTTP-01 的多副本問題本質相同，都是「CA 看到的不一定是你剛寫入的那一份」。好的 ACME client 會先自己查遍每一台 NS，確認都看得到再通知 CA（第 16 章）。

4. **用瀏覽器觀察 HSTS**（真實工具）。在 Chromium 系列瀏覽器打開內部的 net-internals 頁面中的 HSTS 查詢功能，查詢幾個大型網站，看它們是否在 preload list 上；再在 DevTools 的 Network 面板輸入某個已啟用 HSTS 的網站的 `http` 網址，觀察 `307 Internal Redirect`。
   答案要點：307 Internal Redirect 的回應沒有經過網路，Timing 幾乎為 0；查詢結果裡的 `static` 項目代表 preload，`dynamic` 項目代表從 header 學到的紀錄。對照實驗三的 `known()`，理解 includeSubDomains 怎麼影響子網域。

5. **寫一份憑證盤點表**（工作練習）。列出你負責的系統裡所有會用到 TLS 憑證的地方：網站、API、內部服務、資料庫、訊息佇列、webhook 接收端、TURN、行動 App 的 pinning 設定。每一項寫下：誰簽發、效期、怎麼更新、終結在哪裡、誰監控。
   答案要點：多數團隊第一次做都會發現至少一張「沒有人知道怎麼更新」的憑證，通常是手動匯入到某個 LB 或設備上的那一張。把它們列為優先改成自動化的項目，並確認每一張都在實驗一那種外部監控之下。

## 本章重點整理

- 憑證營運是一個循環：產生金鑰與 CSR、驗證網域並簽發、部署完整的鏈、從外部監控、在效期用掉約三分之二時更新；私鑰外洩時先換新再撤銷。
- ACME（RFC 8555）把申請流程變成 API：每個請求都是用帳號金鑰簽章的 JWS，並帶一次性的 nonce 防止重放；訂單依 pending、ready、processing、valid 前進，任何一個名稱驗證失敗就變成 invalid。
- 三種 challenge 都建立在 key authorization（token 加帳號金鑰 thumbprint）上：HTTP-01 用 port 80 的固定路徑，DNS-01 用 `_acme-challenge` 的 TXT，TLS-ALPN-01 用 443 port 上的 `acme-tls/1` 交握；只有 DNS-01 能申請 wildcard。
- 多副本環境中，HTTP-01 的驗證請求可能打到沒有驗證內容的副本，CA 的多點驗證讓這個問題更常見；集中申請、統一分發並逐台驗證序號是較可靠的做法。
- 截至 2026 年 10 月，公開憑證最長效期已是 200 天，並將在 2027 年降到 100 天、2029 年降到 47 天，屆時網域驗證只能重用 10 天，每次更新都要重新驗證，人工流程不再可行。
- 更新時機用效期比例或 ARI 的建議時間窗，並加上隨機延遲；失敗要指數退避，避免撞上 CA 的頻率限制，測試時用 staging 環境。
- 監控要從外部看每一個端點、每一台副本實際送出的憑證，檢查剩餘效期、名稱、鏈與序號一致性；告警門檻用效期比例，固定 30 天的規則在短效期下不是太晚就是噪音。
- 輪替依賴新舊憑證的效期重疊；檔案換了不代表 process 載入了，nginx 要 reload，Python 要建立新的 `SSLContext`，自行匯入 LB 的憑證通常不會自動更新。
- 撤銷正從 OCSP 轉向 CRL，OCSP stapling 與 Must-Staple 的重要性下降；短效期本身就是最可靠的撤銷機制。
- HSTS 讓瀏覽器在 max-age 內只用 HTTPS 並禁止略過憑證錯誤；只在 HTTPS 回應中有效，directive 重複或 max-age 格式錯會讓整個 header 被忽略；includeSubDomains 與 preload 要先盤點子網域並逐步導入，preload 的移除可能要好幾個月。
- Certificate Transparency 要求公開憑證登錄在只能附加的 Merkle tree log 中，瀏覽器檢查 SCT；網域擁有者應監控 CT，並注意公開憑證會公告主機名稱。
- TLS 終結在 CDN、L7 LB 或應用程式各有取捨，核心問題是誰需要看到明文、私鑰可以放在誰手上、後端需要知道 client 的什麼資訊。
- 憑證錯誤先看影響範圍：全部壞多半是過期或名稱，部分壞多半是缺中間憑證或副本不一致，單一使用者壞多半是 client 時鐘或 TLS 攔截；不要用關閉驗證來「解決」錯誤。

## 延伸問答

> [!question]- Q1. 為什麼 ACME 的每個請求都要帶 nonce？有了帳號金鑰的簽章還不夠嗎？
> 簽章證明的是「這個請求確實出自帳號擁有者、內容沒被改過」，但它無法分辨「同一個合法請求被送了第二次」。假設有人錄下了 client 送出的撤銷請求或下訂單請求，原封不動地再送一次，簽章仍然完全正確，CA 無從判斷這是不是擁有者的本意。nonce 是 CA 發出、只能用一次的亂數，被放進簽章保護的 protected header 裡，所以既不能被拿掉，也不能被換掉；CA 收到後就把它作廢，第二次送來就回 `badNonce`。
>
> 同樣的道理，protected header 裡還有請求的 URL，防止有人把一個發給 A 端點的簽章請求，轉送到 B 端點去用。本章實驗二的最後一段就是這個情境：同一個 JWS 第二次送出時簽章依然合法，卻因為 nonce 已用過而被拒絕。這種「簽章擋偽造、nonce 擋重放、URL 擋轉用」的組合，在第 17 章的 webhook 簽章與第 30 章的服務間簽章裡也會再出現，只是 webhook 通常用時間戳記與事件 ID 取代 nonce。

> [!question]- Q2. 情境判斷：`rt.shengsheng.example` 前面是 L4 LB，後面三台 nginx。你會選哪一種 ACME challenge？
> 先排除 TLS-ALPN-01 以外的限制：L4 LB 不終結 TLS，CA 的 443 交握會直接到某一台 nginx，所以 TLS-ALPN-01 技術上可行，但三台都必須能回應 `acme-tls/1`，而且 CA 的多點驗證會打到不同台，等於每台都要有同一份驗證憑證，複雜度不低。HTTP-01 也有同樣的問題：驗證請求被分到哪一台無法控制，除非共用 challenge 儲存，否則容易像實驗二那樣失敗。
>
> 最合適的是 DNS-01 搭配集中申請：由一個憑證控制器用 DNS-01 申請，驗證完全不經過 LB 與 nginx，結果寫入受保護的 Secret 存放處，三台 nginx 讀取同一份憑證並 reload，監控再逐台比對序號。DNS-01 的代價是 DNS API 權限，要用 CNAME 委派到專用驗證 zone 來限縮。這也是聲聲 Live 事故後實際採用的方案。

> [!question]- Q3. 手算：2029 年以後一張 47 天的憑證，若在用掉三分之二時更新，一年要更新幾次？網域驗證能沿用嗎？
> 47 × 2/3 ≈ 31.3 天更新一次，365 ÷ 31.3 ≈ 11.6，也就是一年大約 12 次，幾乎每個月一次。網域驗證結果在這個階段只能重用 10 天，而兩次更新相隔約 31 天，上一次的驗證早就過期，所以每一次更新都要重新完成 challenge。
>
> 這個結果有兩個營運上的推論。第一，任何會讓 challenge 失敗的設定錯誤（CAA 漏了 CA、DNS API 憑證過期、CDN 把驗證路徑擋掉）最多一個月內就會變成實際的更新失敗，而且失敗後剩下的緩衝只有約 16 天。第二，監控必須在「該換卻沒換」的第一時間告警，用本章的比例規則，47 天的憑證在第 34 天左右就會響，還剩 13 天可以處理；如果還用固定 30 天，就會在第 17 天開始產生每張憑證都有的噪音，真正的問題反而被淹沒。

> [!question]- Q4. 你在 production 看到：桌面 Chrome 打開 `api.shengsheng.example` 完全正常，但 Android App 與後端的 Python 服務都報 `unable to get local issuer certificate`。原因和修法？
> 這是缺中間憑證的典型症狀。伺服器只送了 leaf，client 要自己找到簽發 leaf 的那張中間憑證，才能一路驗證到信任的根憑證。桌面瀏覽器常常能自己補上：可能之前在別的網站看過同一張中間憑證而快取了，或依 leaf 裡的 AIA 欄位去下載；但 Python 的 `ssl`、curl 與許多 App 只使用伺服器送來的鏈與本機的根憑證，找不到就失敗，訊息正是 `unable to get local issuer certificate`。
>
> 確認方法是 `openssl s_client -showcerts`：如果只看到一張憑證，`Verify return code` 是 21，就確定了。修法是在 LB 或 nginx 設定完整鏈，順序是 leaf 在前、中間憑證在後，例如 certbot 產生的 `fullchain.pem` 而不是 `cert.pem`；根憑證不需要附上。修完後要從外部再驗證一次，並把「鏈的長度」加進到期監控，就像實驗一的 `缺中間憑證` 檢查，避免下次手動上傳時再犯。

> [!question]- Q5. 面試題：HSTS 已經會讓瀏覽器強制使用 HTTPS，伺服器的 port 80 還需要做 301 轉址嗎？preload 又解決了什麼？
> 需要。HSTS 只在瀏覽器「已經記住」這個網站後才生效，而它只會從 HTTPS 回應學到 HSTS；一個從沒來過的使用者輸入網址，瀏覽器仍可能先發 HTTP 請求，這時要靠 port 80 的 301 把使用者帶到 HTTPS，才有機會收到 HSTS header。此外，不支援 HSTS 的 client（例如某些命令列工具或嵌入式裝置）也只能依賴轉址。preload 的申請條件本身就要求 port 80 轉到同一個主機的 HTTPS。
>
> preload 解決的是「第一次造訪」的破口：瀏覽器出廠時就內建清單，連第一個請求都不會用明文送出，SSL stripping 失去了下手的機會。代價是幾乎不可逆：加入與移除都要等瀏覽器發新版，而且清單要求 includeSubDomains，所有子網域都被永久要求 HTTPS。所以面試時完整的答案是：轉址負責把人帶上 HTTPS，HSTS 負責讓瀏覽器記住，preload 負責保護第一次，三者是層層補強而不是互相取代。

> [!question]- Q6. 看 log 找原因：nginx 的 error log 出現 `"ssl_stapling" ignored, no OCSP responder URL in the certificate`。要緊急處理嗎？
> 不需要緊急處理，這通常只是警告。它表示 nginx 設定了 `ssl_stapling on`，但憑證裡沒有 OCSP 網址，所以 nginx 無從取得 OCSP 回應來 staple。截至 2026 年，這越來越常見：撤銷機制正在從 OCSP 轉向 CRL，一些 CA（例如 Let's Encrypt）已停止 OCSP 服務，新憑證不再帶 OCSP 網址。TLS 交握本身不受影響，client 只是收不到 stapled 回應，而主流瀏覽器多半也不依賴線上 OCSP 查詢。
>
> 要確認的是兩件事。第一，這張憑證沒有 Must-Staple 擴充；如果有，缺少 staple 會讓支援 Must-Staple 的瀏覽器直接拒絕連線，那才是需要立刻處理的故障。第二，如果憑證其實有 OCSP 網址卻仍取不到回應，就要查 nginx 的 `resolver` 設定與對外連線是否被防火牆擋住。確認無誤後，可以在沒有 OCSP 網址的站台關閉 stapling，讓 log 保持乾淨，真正的警告才不會被淹沒。

> [!question]- Q7. 設計取捨：聲聲 Live 想把 API 的 TLS 從 LB 改成穿透到每台 gunicorn 直接終結，以達成「端到端加密」。你會怎麼評估？
> 先問清楚動機要達成什麼。如果目的是「LB 到後端這一段不要是明文」，更簡單的做法是讓 LB 終結對外 TLS 後，再用另一條 TLS（或 mTLS）連到後端，LB 仍能做 HTTP 路由、WAF 與統一的憑證管理。真正需要穿透的情境，是後端必須自己驗證 client 憑證、或者合約規定 LB 不能看到明文。
>
> 如果真的要穿透，代價要算清楚：每台 gunicorn 都需要對外名稱的憑證與私鑰，私鑰分散在更多機器上；憑證輪替要讓 worker 重新載入，並逐台驗證序號；TLS 交握的 CPU 落到應用主機；L4 LB 看不到 HTTP，無法依路徑路由，也不能加 `X-Forwarded-For`，要改用 PROXY protocol 傳遞 client IP。比較務實的組合通常是：對外在 LB 終結，LB 到後端用內部 CA 簽發的短效憑證做 mTLS（第 30 章），兼顧可管理性與傳輸加密。

> [!question]- Q8. Rita 的 CT 監控在半夜通報：`*.shengsheng.example` 出現一張 issuer 是陌生 CA 的新憑證。下一步怎麼做？
> 第一步是確認它是不是自己人申請的。陌生的 issuer 很常見的解釋是：某個團隊啟用了 CDN 或 SaaS 服務的代管憑證，供應商用自己合作的 CA 替你的名稱簽發；或者有人在測試環境用了別的 ACME CA。查 CT 項目裡的 SAN、簽發時間，再對照近期的變更紀錄、DNS 變更與 CAA 設定（理論上 CAA 不允許的 CA 不應簽發）。如果能對應到合法的變更，就把該 CA 正式加進允許清單與 CAA，並補上流程紀錄。
>
> 如果查不到任何合法來源，就當成安全事件處理：檢查 DNS 與網站是否被入侵（攻擊者要通過 DCV，代表曾控制過 DNS 或網站內容）、DNS API 憑證是否外洩；聯絡簽發的 CA 要求撤銷，並提供 CT 項目作為證據；收緊 CAA，必要時用 CAA 的擴充限定帳號與驗證方式。撤銷的效果在 client 端並不即時，所以同時要修補入侵路徑、輪替相關的憑證與金鑰。這正是 CT 的價值：沒有 CT，這張憑證可能在被拿來攻擊之前都沒有人知道。

## 延伸閱讀

- RFC 8555〈Automatic Certificate Management Environment (ACME)〉：ACME 的帳號、訂單、challenge 與 JWS 請求格式
- RFC 8737〈Automated Certificate Management Environment (ACME) TLS Application-Layer Protocol Negotiation (ALPN) Challenge Extension〉：TLS-ALPN-01
- RFC 6797〈HTTP Strict Transport Security (HSTS)〉：HSTS 的語法與瀏覽器行為
- RFC 6962〈Certificate Transparency〉：CT log、SCT 與 Merkle tree 的定義
- RFC 8659〈DNS Certification Authority Authorization (CAA) Resource Record〉：CAA record
- RFC 5280〈Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile〉：憑證與 CRL 的欄位
- CA/Browser Forum〈Baseline Requirements for the Issuance and Management of Publicly-Trusted TLS Server Certificates〉與 Ballot SC-081v3：效期與網域驗證規則
- Ivan Ristić《Bulletproof TLS and PKI》：TLS 部署與憑證營運的實務
