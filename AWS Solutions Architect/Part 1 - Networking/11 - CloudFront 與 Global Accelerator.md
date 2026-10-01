---
chapter: 11
title: CloudFront 與 Global Accelerator
part: 1
---

# 第 11 章　邊緣加速：CloudFront 與 Global Accelerator

> [!abstract] 本章地圖
> **你會學到**：
> - 解釋 CDN 為什麼能讓遠方使用者變快，以及 edge location、regional edge cache 與 origin 的關係
> - 設計一個 CloudFront distribution：多個 origin、依路徑的 cache behavior、cache policy 與 origin request policy、TTL 與 invalidation
> - 讓 S3 bucket 保持私有、只能經 CloudFront 存取（OAC），並用 signed URL／signed cookie、geo restriction、field-level encryption 保護內容
> - 分辨 CloudFront Functions 與 Lambda@Edge 的能力邊界，設定 origin failover 與 HTTPS 憑證（ACM us-east-1）
> - 說明 Global Accelerator 的 anycast 固定 IP、TCP/UDP 支援與快速 failover，並在 CloudFront 與 Global Accelerator 之間正確選型
>
> **前置知識**：第 3 章（DNS、TCP、TLS、HTTP）、第 9 章（Route 53）、第 10 章（ALB、NLB）
> **考試比重**：SAA ★★★（Domain 1 安全、Domain 3 網路效能、Domain 4 網路成本）｜SAP ★★☆（Domain 1 網路、Domain 2 效能與業務連續性）

## 11.1 故事：東京很快，洛杉磯很慢

到了第 10 章結束，Wanderly 的網站已經跑在東京 Region 的 ALB 後面，跨兩個 AZ、可以撐住促銷尖峰。台灣與日本的使用者很滿意，首頁大約 1 秒就載入完成。

但 Wanderly 開始拓展美國與歐洲市場後，客服收到一連串抱怨：「網站好慢」「旅館照片一張一張慢慢出現」。小林從洛杉磯的測試機量測，首頁要 6 秒，每張旅館照片 800 毫秒以上。他打開瀏覽器的開發者工具，發現首頁需要下載 80 個檔案：JavaScript、CSS、圖示、幾十張照片。每個檔案都要橫跨太平洋往返東京，一次往返大約 120 毫秒，TCP 與 TLS 的 handshake 又要多跑好幾趟。**問題不是東京的伺服器慢，而是距離太遠。**

同時還有兩個問題。第一，旅館照片放在 S3 bucket 裡，為了讓網站能顯示，當初把 bucket 設成公開讀取，資安稽核要求改成私有。第二，歐洲的合作旅行社要接收 Wanderly 的即時房價推播，這是一個自訂的 TCP 協定，他們抱怨連線經過公共 Internet 時延遲忽高忽低，並且要求「固定 IP，才能加進防火牆白名單」。

這一章的兩個主角剛好對應這兩類問題：**CloudFront** 把內容快取到離使用者最近的地方，解決網站與照片的速度與存取控制；**Global Accelerator** 讓 TCP/UDP 流量從離使用者最近的入口就進入 AWS 的骨幹網路，並提供固定的 anycast IP。

## 11.2 CDN 原理：把內容搬到使用者旁邊

### 延遲來自距離與往返次數

第 3 章介紹過 latency 與 bandwidth 的差別。光在光纖中的速度是有限的，台北到洛杉磯的實體距離決定了一次往返至少要一百多毫秒，這是買再多頻寬都改善不了的。更糟的是，一個 HTTPS 請求在傳第一個位元組之前，還要先完成 TCP 三向交握與 TLS handshake，每一步都是一次或多次跨洋往返。

**CDN（Content Delivery Network，內容傳遞網路）** 的解法是：在全球很多城市放置伺服器，讓使用者連到離自己最近的那一台。這台伺服器做兩件事：

1. **快取（cache）**：如果使用者要的檔案它已經有了（例如昨天別人看過同一張照片），直接回應，完全不用回到東京。這稱為 **cache hit**；沒有的話稱為 **cache miss**，才向源頭取得並存一份。
2. **就近終止連線**：即使內容不能快取（例如查詢空房的 API），使用者的 TCP 與 TLS handshake 也只需要和附近的伺服器完成，再由 CDN 透過預先建立、持續重用的連線，走品質穩定的骨幹網路回到源頭。往返距離大幅縮短。

提供內容的源頭稱為 **origin（源站）**，例如存放照片的 S3 bucket，或第 10 章的 ALB。

### CloudFront 的全球架構

**Amazon CloudFront** 是 AWS 的 CDN。它的節點分成兩層：

- **Edge location（邊緣節點）**：分布在全球數百個地點（第 2 章介紹過，它們不是 Region，也不是 AZ），直接面對使用者，負責終止連線與快取熱門內容。
- **Regional edge cache（區域邊緣快取）**：數量較少、容量較大，位於 edge location 與 origin 之間。Edge location 快取不到的內容（例如較冷門的照片），會先到 regional edge cache 找，還沒有才回 origin。這讓長尾內容的命中率提高，origin 的負擔降低。

如果 origin 的負載仍然太高，或有多個 Region 的使用者都在打同一個 origin，還可以開啟 **Origin Shield**：指定一個 Region 作為最後一層集中快取，所有 cache miss 都先匯集到這裡，origin 只會收到一次請求。

CloudFront 是**全球服務**，不屬於任何一個 Region。它和 AWS Shield Standard 自動整合，具備基本的 DDoS 防護，也可以掛 AWS WAF（第 16 章）。從 AWS origin 到 CloudFront 的資料傳輸不收費，CloudFront 送給使用者的流量通常比從 Region 直接送出更便宜，所以它同時是**效能**與**成本**的工具。

## 11.3 Distribution、origin 與 behavior

### Distribution：一個 CloudFront 入口

在 CloudFront 上的設定單位稱為 **distribution**。建立後你會拿到一個網域名稱，例如 `d111111abcdef8.cloudfront.net`。要讓使用者用 `www.wanderly.com` 存取，需要：

1. 在 distribution 設定 **alternate domain name（CNAME）**：`www.wanderly.com`。
2. 提供涵蓋這個網域的憑證（11.7 節）。
3. 在 Route 53 建立 alias record，指向 distribution（第 9 章）。

**Price class** 決定 distribution 使用哪些地區的 edge location。選 All 效能最好；若使用者主要在北美與歐洲，可選較小的 price class 降低成本，代價是其他地區的使用者會被導到較遠的節點。

### Origin：內容從哪裡來

一個 distribution 可以有多個 origin：

| Origin 類型 | 例子 | 說明 |
|---|---|---|
| S3 bucket（REST endpoint） | 旅館照片、前端靜態檔 | 搭配 OAC 讓 bucket 保持私有（11.5 節） |
| S3 static website endpoint | 舊式靜態網站 | 視為 custom origin，**不支援 OAC**，bucket 需公開讀取 |
| Custom origin | ALB、EC2、API Gateway、地端伺服器 | 任何可經 HTTP/HTTPS 存取的伺服器 |
| VPC origin | private subnet 中的 internal ALB、NLB 或 EC2 | origin 不需要任何 public 入口（11.6 節） |

### Cache behavior：依路徑決定怎麼處理

**Cache behavior（快取行為）** 是 distribution 的路由規則：每個 behavior 有一個 **path pattern**，以及一組設定。CloudFront 依 behavior 的**排列順序**比對請求路徑，第一個符合的 behavior 生效；最後永遠有一個 `*` 的 **default behavior**。

每個 behavior 的主要設定：

- 送往哪個 **origin**。
- **Viewer protocol policy**：允許 HTTP 與 HTTPS、把 HTTP 轉址到 HTTPS，或只允許 HTTPS。
- **Allowed methods**：只允許 `GET`／`HEAD`，或也允許 `POST`、`PUT`、`DELETE` 等（API 需要）。
- **Cache policy** 與 **origin request policy**（下一節）。
- **Response headers policy**：在回應中加上 CORS、HSTS 等安全 header。
- 是否要求 **signed URL／signed cookie**（11.5 節）、要執行哪些 **edge function**（11.8 節）。

```text
使用者（洛杉磯）
   │ ① https://www.wanderly.com/images/hotel-123.jpg
   ▼
[Edge location：洛杉磯]
   │ ② 比對 behaviors（依順序）
   │    /api/*     → origin: ALB（東京），CachingDisabled
   │    /images/*  → origin: S3 照片 bucket，快取 7 天   ← 符合
   │    * (default)→ origin: S3 前端 bucket，快取 1 天
   │ ③ 依 cache key 查快取
   │    ├─ hit  → 直接回應（數十毫秒）
   │    └─ miss ▼
[Regional edge cache：美西]
   │ ④ 再查一次；仍 miss ▼
[Origin：S3 bucket（東京），經 OAC 簽章存取]
   │ ⑤ 回應 + Cache-Control: max-age=604800
   ▼
沿路存入快取，回應使用者
```

① 使用者的 DNS 查詢會被導向最近的 edge location，TCP 與 TLS handshake 在洛杉磯完成。② Edge 依序比對 behavior，`/images/*` 符合，決定 origin 與快取規則。③ 用 cache key 查詢本地快取，命中就直接回應。④ 未命中時先問 regional edge cache。⑤ 都沒有才回東京的 S3 取得，回應沿路被快取，下一位美國使用者就會命中。`/api/*` 雖然不快取，但仍享有就近終止連線與骨幹網路的好處。

## 11.4 快取怎麼判斷「是同一份內容」：cache key、policy 與 TTL

CDN 最重要也最容易設錯的就是快取規則。快取太少，origin 被打爆；快取太多或區分錯誤，使用者會看到錯的內容，甚至看到別人的資料。

### Cache key

**Cache key（快取鍵）** 是 CloudFront 用來判斷「兩個請求要的是不是同一份內容」的依據。預設只包含網域與 URL 路徑，例如 `www.wanderly.com/images/hotel-123.jpg`。如果同一個路徑會因為某個參數回應不同內容，就必須把那個參數加入 cache key：

- 照片 API 依 `?width=400` 回傳不同尺寸 → query string `width` 要加入 cache key。
- 頁面依 `Accept-Language` 回傳中文或英文 → 這個 header 要加入 cache key。

但加入 cache key 的東西越多，同一份內容就會被拆成越多份快取，**cache hit ratio（命中率）**下降。最典型的錯誤是「把所有 header、cookie、query string 都加入 cache key」：每位使用者的 cookie 都不同，等於每個人都有一份自己的快取，CDN 形同虛設。

### Cache policy 與 origin request policy

CloudFront 用兩種 policy 把這兩件事分開：

- **Cache policy**：決定哪些 header、cookie、query string **納入 cache key**，以及 TTL 設定。被納入 cache key 的值，也會自動轉送給 origin。
- **Origin request policy**：決定**額外轉送給 origin、但不納入 cache key** 的值。例如 origin 需要 `User-Agent` 做記錄、需要 `X-Request-Id` 追蹤，但內容不會因此不同，就放在這裡。

設計原則是：**只有「會改變回應內容」的值才進 cache policy；origin 需要但不改變內容的值放 origin request policy。** AWS 提供常用的 managed policy，例如 `CachingOptimized`（靜態內容）、`CachingDisabled`（API），以及 `AllViewer`（把 viewer 的所有 header、cookie、query string 轉給 origin 的 origin request policy）。

### TTL：快取多久

**TTL（Time To Live）** 決定物件在快取中保持多久才需要回 origin 確認。Cache policy 有三個值：

- **Default TTL**：origin 沒有給任何快取指示時使用。
- **Minimum TTL** 與 **Maximum TTL**：限制 origin 指示的範圍。

Origin 透過 HTTP header 告訴 CDN 怎麼快取：`Cache-Control: max-age=604800`（可快取 7 天）、`s-maxage`（只針對共用快取）、`no-cache`、`no-store`、`private`，或舊式的 `Expires`。CloudFront 會以 origin 的指示為主，但夾在 minimum 與 maximum 之間。

> [!warning] 常見誤解
> 「origin 回 `Cache-Control: no-store`，CloudFront 就一定不會快取。」如果 cache policy 的 Minimum TTL 大於 0，CloudFront 會至少快取到 minimum TTL，忽略 origin 的 `no-store`／`no-cache`／`private`。含有個人資料的回應，一定要用 Minimum TTL 為 0 或 `CachingDisabled` 的 policy，不能只靠 origin header。

### 內容更新了怎麼辦：invalidation 與版本化檔名

Wanderly 部署新版前端後，使用者仍然拿到舊的 `app.js`，因為快取還沒過期。有兩種做法：

1. **Invalidation（失效）**：要求 CloudFront 立刻把指定路徑的快取清掉，例如 `/app.js` 或 `/static/*`。每月前 1,000 個路徑免費，之後依路徑數收費；一個萬用字元路徑算一個路徑。清除需要一點時間傳播到所有節點。
2. **版本化檔名（versioning）**：每次部署產生新檔名，例如 `app.3f9a1c.js`，HTML 改為引用新檔名。新檔案從沒被快取過，使用者第一次請求就拿到新版；舊檔案自然過期。這讓靜態檔可以設很長的 TTL，又不需要 invalidation。

實務上兩者搭配：HTML 這種入口檔案設短 TTL（或部署時 invalidate），JS、CSS、圖片用版本化檔名加長 TTL。考題問「頻繁部署、要使用者立即看到新版、又要避免 invalidation 費用與延遲」，答案是版本化檔名。

## 11.5 保護內容：OAC、signed URL／cookie、geo restriction 與 field-level encryption

速度解決了，接著處理稽核的要求：照片 bucket 要私有，付費內容只給付費會員，部分國家因授權限制不能提供某些內容，信用卡號要在邊緣就加密。

### OAC：讓 S3 只認 CloudFront

如果 S3 bucket 是公開的，使用者可以繞過 CloudFront 直接下載，WAF、geo restriction、signed URL 等所有邊緣控制全部失效。正確做法是讓 bucket 保持私有（S3 預設的 Block Public Access 保持開啟，第 22 章），只允許「這個 distribution」讀取。

**Origin Access Control（OAC）** 讓 CloudFront 用 AWS 的簽章機制（SigV4）簽署送往 S3 的每個請求。Bucket policy 再允許 CloudFront 服務主體讀取，並用條件鎖定到特定 distribution：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontOACRead",
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::wanderly-hotel-photos/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/E2QWRUHEXAMPLE"
        }
      }
    }
  ]
}
```

這份 policy 有三個重點：`Principal` 是 CloudFront 服務，不是任何人（`*`）；`AWS:SourceArn` 把權限限制在一個 distribution，其他人的 distribution 即使也指向這個 bucket 也讀不到；`Resource` 用 `/*` 因為 `GetObject` 是物件層級的動作。

如果 bucket 使用 **SSE-KMS** 加密（第 15 章），還要在 **KMS key policy** 允許 `cloudfront.amazonaws.com` 對該 key 執行 `kms:Decrypt`（同樣以 SourceArn 限制），否則 CloudFront 能通過 bucket policy，卻無法解密物件。

在 OAC 之前的舊做法叫 **Origin Access Identity（OAI）**。OAI 不支援 SSE-KMS、不支援所有新 Region、功能較少，AWS 建議新設定一律使用 OAC，既有的 OAI 也應遷移。另外記得：**S3 static website endpoint 不支援 OAC**，要私有化就改用 REST endpoint 作為 origin。

### Signed URL 與 signed cookie：只給付費會員

Wanderly 推出「旅遊達人影片」付費內容，只有訂閱會員能觀看。CloudFront 的做法是在 behavior 上要求簽章，並設定 **trusted key group**（你上傳的公鑰）。應用程式驗證使用者是會員後，用對應的私鑰產生簽章，CloudFront 在邊緣驗證簽章與到期時間。

| | Signed URL | Signed cookie |
|---|---|---|
| 簽章放在哪 | URL query string | Cookie |
| 適合 | **單一檔案**，例如一份 PDF 行程、一個下載連結 | **多個檔案**，例如影片串流（HLS 會有數百個片段檔）、整個會員專區 |
| 是否改變 URL | 是 | 否（原本的 URL 不用改） |
| 不支援 cookie 的 client | 可用 | 不可用 |

簽章政策分為 **canned policy**（只限制到期時間）與 **custom policy**（還可限制開始時間、來源 IP 範圍、用萬用字元涵蓋多個路徑）。

不要和 **S3 presigned URL** 混淆：presigned URL 是用 IAM 身份直接對 S3 簽發的臨時存取連結，流量不經過 CloudFront；CloudFront signed URL 則是在邊緣驗證，享有快取與邊緣控制。內容透過 CloudFront 提供時，用 CloudFront signed URL／cookie。

> [!note] 舊做法：CloudFront key pair
> 早期 signed URL 要用 root user 建立的 CloudFront key pair。現在建議使用 trusted key group：由 IAM 權限管理、不需要 root user，也能輪替多把金鑰。

### Geo restriction：依國家允許或封鎖

某些旅遊影片的授權只限亞洲地區。**Geo restriction（地理限制）** 可以設定國家的 allow list 或 block list，CloudFront 依使用者 IP 判斷國家，被拒絕的請求回 HTTP 403。它套用在整個 distribution。如果需要更細的規則（例如只限制某些路徑、搭配其他條件），可用 AWS WAF 的 geo match 規則，或在 edge function 中處理。

### Field-level encryption：在邊緣就加密敏感欄位

訂房表單包含信用卡號。即使全程 HTTPS，資料在 CloudFront 與 ALB 解密後，後端每個經手的服務（日誌、訂單服務、推薦系統）都看得到明文。**Field-level encryption（欄位層級加密）** 讓 CloudFront 在邊緣用你提供的 **公鑰** 加密 POST 表單中指定的欄位（最多 10 個），之後整條鏈路上只有持有 **私鑰** 的支付服務能解密。它是 HTTPS 之外的額外一層保護，常出現在 PCI DSS 相關的考題。

## 11.6 動態內容與 ALB origin：不要讓人繞過 CloudFront

`/api/*` 送往東京的 ALB。這裡有一個和 S3 一樣的問題：如果 ALB 是 internet-facing，攻擊者查到它的 DNS 名稱後就能直接連，繞過 CloudFront 上的 WAF 與 geo restriction。保護方式由強到弱：

1. **VPC origin**：把 ALB 改成 **internal**，放在 private subnet，建立 CloudFront VPC origin。ALB 沒有任何 Internet 入口，只有 CloudFront 能連到它，再用 ALB 的 security group 限制來源。這是隔離最強的做法。
2. **Managed prefix list + 自訂 header**：ALB 維持 internet-facing，但 security group 只允許 AWS 提供的 CloudFront origin-facing managed prefix list（`com.amazonaws.global.cloudfront.origin-facing`），把其他來源擋掉；再讓 CloudFront 對 origin 加上一個只有你知道的 **custom header**（例如 `X-Origin-Verify: <隨機值>`），ALB listener rule 只轉送帶有正確值的請求，其餘回 403。Prefix list 確保流量來自 CloudFront，custom header 確保來自**你的** distribution。

對動態內容，CloudFront 的價值在於：就近終止 TCP／TLS、對 origin 重用長連線、走 AWS 骨幹網路，同時把 WAF、DDoS 防護放在邊緣。API 的 behavior 通常用 `CachingDisabled` cache policy，再用 origin request policy 轉送 API 需要的 header、cookie 與 query string。

## 11.7 HTTPS：兩段連線、兩個憑證位置

CloudFront 架構中有兩段 TLS 連線，各自設定：

- **Viewer → CloudFront**：由 viewer protocol policy 決定是否強制 HTTPS，security policy 決定最低 TLS 版本。使用 `*.cloudfront.net` 網域時可以直接用 CloudFront 的預設憑證；使用自己的網域（`www.wanderly.com`）時，**憑證必須放在 us-east-1（N. Virginia）的 ACM**，不論 origin 在哪個 Region。這是最常考的單一事實，因為 CloudFront 是全球服務，它從 us-east-1 讀取憑證並分發到所有 edge。
- **CloudFront → origin**：由 origin protocol policy 決定用 HTTP、HTTPS 或與 viewer 相同。Origin 若是東京的 ALB，ALB 的憑證要放在 **東京 Region 的 ACM**（第 10 章）；S3 REST endpoint 本身就支援 HTTPS。若 origin 用 HTTPS，origin 的憑證必須是公開 CA 簽發、且涵蓋 CloudFront 連線時使用的 origin 網域。

自訂網域的 HTTPS 預設使用 **SNI**（第 10 章）提供，不額外收費。只有極舊、不支援 SNI 的 client 才需要「dedicated IP」方式，費用很高，考試中通常不是答案。

> [!tip] 考試提示
> 題目說「在 ap-northeast-1 的 ACM 申請了憑證，但建立 CloudFront distribution 時選不到」，答案就是到 us-east-1 重新申請或匯入憑證。同一個網域可以在 us-east-1（給 CloudFront）與東京（給 ALB）各有一張 ACM 憑證。

## 11.8 在邊緣執行程式：CloudFront Functions 與 Lambda@Edge

有些邏輯放在邊緣執行最有效率：把 `/hotel/123` 改寫成 `/hotel/123/index.html`、依裝置類型導向不同版本、檢查 **JWT（JSON Web Token，一段帶簽章的登入憑證，驗證簽章就能知道是誰、有沒有過期）**、加入安全 header、做 A/B 測試。CloudFront 提供兩種 edge function。

### 四個觸發點

一個請求經過 CloudFront 有四個可以插入程式的時間點：

```text
Viewer ──①viewer request──▶ [CloudFront 快取] ──③origin request──▶ Origin
Viewer ◀─②viewer response── [CloudFront 快取] ◀─④origin response── Origin
```

① **Viewer request**：CloudFront 收到使用者請求後、查快取之前，每個請求都會執行。② **Viewer response**：回應給使用者之前，每個請求都會執行。③ **Origin request**：只在 cache miss、要回 origin 時執行。④ **Origin response**：origin 回應後、存入快取之前執行。③④ 的執行次數遠少於 ①②，因為快取命中時不會觸發。

### 兩種 function 的差別

| | CloudFront Functions | Lambda@Edge |
|---|---|---|
| 語言 | JavaScript | Node.js、Python |
| 觸發點 | 只有 viewer request／viewer response | 四個都可以 |
| 執行時間 | 極短（毫秒以下等級） | 最長 30 秒（舊資料常寫 viewer 觸發 5 秒，AWS 現行文件已統一為 30 秒） |
| 記憶體與回應大小 | 函式記憶體 2 MB | viewer 觸發 128 MB、產生的回應最大 40 KB；origin 觸發最高 10 GB、回應最大 1 MB |
| 網路存取 | 不行 | 可以（呼叫外部 API、讀 DynamoDB 等） |
| 讀取 request body | 不行 | 可以（origin 觸發可選擇包含 body） |
| 執行位置 | 所有 edge location | 較少的 regional edge cache 位置 |
| 規模與成本 | 每秒數百萬次，成本約為 Lambda@Edge 的幾分之一 | 較高 |
| 部署 | 直接在 CloudFront 建立 | 必須在 **us-east-1** 建立，並以已發布的版本號關聯，CloudFront 會複製到各地 |

選擇原則：**簡單、每個請求都要做、不需要網路的轉換（header 改寫、URL 改寫、轉址、簡單 token 驗證、cache key 正規化）用 CloudFront Functions**；需要呼叫外部服務、讀取 body、較長的運算或在 origin 觸發點動態選擇 origin，用 **Lambda@Edge**。CloudFront Functions 還可以搭配 **CloudFront KeyValueStore** 讀取小型的鍵值資料（例如轉址對照表），不需要網路存取。

> [!example] 例子
> Wanderly 要把舊網址 `/hotels.php?id=123` 永久轉址到 `/hotel/123`：用 CloudFront Functions 的 viewer request，直接回 301。要依使用者 cookie 裡的會員等級，查詢 DynamoDB 後決定送往一般或 VIP 的 origin：用 Lambda@Edge 的 origin request。

## 11.9 Origin failover：origin 掛了還能回應

東京 Region 的 S3 若出現問題，所有 cache miss 都會失敗。CloudFront 的 **origin group** 可以設定一個 **primary origin** 與一個 **secondary origin**（例如另一個 Region 的 S3 bucket，以 S3 Cross-Region Replication 保持同步，第 23 章）。當 primary 回應你指定的錯誤狀態碼（可選 400、403、404、416、429、500、502、503、504 的任意組合），或連不上、回應逾時（分別在勾選 503、504 時生效），CloudFront 會對同一個請求改向 secondary 取得內容。

要注意兩個限制：**origin failover 只適用於 `GET`、`HEAD`、`OPTIONS` 請求**，所以它適合靜態內容與讀取，不適合寫入 API；它是每個請求各自重試，而不是「整個 distribution 切換」，primary 恢復後請求自然回到 primary。寫入型 API 的跨 Region 容錯，要用 Route 53 failover（第 9 章）或 Global Accelerator（下一節）在更前面的層次處理。

另外，CloudFront 預設對 primary 最多嘗試連線 3 次、每次等 10 秒，也就是最長約 30 秒才 failover；可以把 connection timeout（1–10 秒）與 connection attempts（1–3 次）調小，讓 failover 更快觸發；也可以設定 **custom error response**，在 origin 錯誤時回傳一個快取的友善錯誤頁面。

## 11.10 Global Accelerator：給 TCP/UDP 的全球入口

回到歐洲旅行社的房價推播。這是長連線的自訂 TCP 協定，內容每秒都在變，**沒有任何東西可以快取**，而且 CloudFront 只處理 HTTP(S)。他們要的是兩件事：連線品質穩定、入口 IP 固定。

### 公共 Internet 的問題

沒有任何加速時，歐洲旅行社的封包要經過多家電信業者的網路一路轉送到東京，每一段的壅塞與路由變動都會造成延遲抖動與封包遺失。**AWS Global Accelerator** 的做法是：讓流量在離使用者最近的 AWS edge location 就進入 AWS 的全球骨幹網路，之後全程走 AWS 自己的線路到達目標 Region。

### Anycast 固定 IP

建立一個 accelerator 後，你會得到 **兩個固定的 IPv4 位址**（也可以使用自己的位址 BYOIP；dual-stack accelerator 另外提供 IPv6 位址）。這兩個 IP 是 **anycast** 位址：同一個 IP 同時從全球所有 edge location 對外宣告，使用者的封包會被 Internet 路由自然帶到「網路上最近」的那個 edge。

這和 DNS 型的就近導流有本質差異：

- IP 永遠不變，合作夥伴可以放心加入防火牆白名單，客戶端也可以把 IP 寫死。
- 後端 Region 或 endpoint 的切換發生在 AWS 內部，**不依賴 DNS，不受 client 的 DNS 快取或 TTL 影響**。
- 兩個 IP 來自獨立的網路區段，一個出問題時 client 仍可使用另一個。

### 結構：listener、endpoint group、endpoint

```text
歐洲旅行社
   │ ① 連 75.2.x.x:7443（anycast 固定 IP）
   ▼
[AWS edge：法蘭克福] ── ② 進入 AWS 骨幹網路
   │
[Listener：TCP 7443，client affinity = SOURCE_IP]
   │ ③ 依 endpoint group 的 traffic dial 與健康狀態選 Region
   ├─▶ [Endpoint group：ap-northeast-1，traffic dial 100%]
   │      ├─ NLB-tokyo   weight 200
   │      └─ NLB-tokyo-2 weight 55
   └─▶ [Endpoint group：eu-central-1，traffic dial 100%]
          └─ NLB-frankfurt weight 255
   │ ④ endpoint 不健康 → 自動改送其他健康 endpoint／Region
   ▼
房價推播伺服器
```

① 旅行社連的是 anycast 固定 IP。② 封包在法蘭克福的 edge 進入 AWS 網路。③ **Listener** 定義接收的協定（**TCP 或 UDP**）與 port；每個 listener 有一或多個 **endpoint group**，每個 group 對應一個 Region。Global Accelerator 預設把流量送到離使用者最近、且有健康 endpoint 的 Region。④ **Endpoint** 可以是 ALB、NLB、EC2 instance 或 Elastic IP。Global Accelerator 持續做健康檢查（ALB／NLB endpoint 使用它們自身的 target 健康狀態），endpoint 或整個 Region 不健康時，新流量會被導到下一個健康的目標。切換速度取決於健康檢查的間隔與門檻，但因為 IP 不變、不需要等待 client 端的 DNS 快取過期，通常遠快於 DNS 型 failover。

### 兩個控制比例的旋鈕

- **Traffic dial**：設在 endpoint group 上，0–100%，控制「本來會送到這個 Region 的流量」實際送多少。設成 0% 就是把這個 Region 下線維護；新 Region 上線時可以從 10% 開始逐步調高，做 blue/green 或 canary。
- **Endpoint weight**：設在 group 內的每個 endpoint 上，0–255，控制同一 Region 內各 endpoint 分到的相對比例。設成 0 就是暫停送新流量到該 endpoint。

兩者分層：traffic dial 管 Region 之間，weight 管 Region 內部。

### 其他重要特性

- **Client affinity**：預設為 None，依 5-tuple 分配，同一 client 的不同連線可能到不同 endpoint；設為 **Source IP** 時，同一來源 IP 的連線盡量送到同一個 endpoint，適合有狀態的應用。它只是傾向，endpoint 故障時仍會切換，所以應用程式狀態仍要能恢復。
- **Client IP preservation**：ALB、EC2 instance，以及「有附加 security group 的 NLB」endpoint 可以看到原始 client IP；沒有 security group 的 NLB 與 Elastic IP endpoint 不支援。
- **Custom routing accelerator**：標準 accelerator 由 AWS 選擇 endpoint；custom routing accelerator 讓你把 accelerator 的 port 確定性地對應到 VPC subnet 中特定 EC2 的 IP 與 port。用於多人遊戲的配對服務：配對系統決定玩家要進哪台遊戲伺服器，再把對應的 port 告訴玩家。
- **費用**：每個 accelerator 有固定的小時費，加上依流量計算的 data transfer premium。
- **防護**：和 CloudFront 一樣有 Shield Standard，也可以用 Shield Advanced 保護（第 16 章）。
- **不快取任何內容**，也不理解 HTTP。即使 endpoint 是 ALB，Global Accelerator 只負責把 TCP 連線送到 ALB，HTTP 路由仍由 ALB 處理。

## 11.11 比較與選型

### CloudFront vs Global Accelerator

兩者都使用 AWS 的 edge location 與骨幹網路，所以常被搞混。關鍵在「看不看得懂 HTTP」與「有沒有快取」。

| 項目 | CloudFront | Global Accelerator |
|---|---|---|
| 本質 | CDN（反向代理 + 快取） | 網路層的全球入口 |
| 協定 | HTTP、HTTPS、WebSocket | TCP、UDP |
| 快取 | 有，可快取靜態與部分動態內容 | 無 |
| 入口位址 | DNS 名稱（`*.cloudfront.net`），IP 會變 | 2 個固定 anycast IP |
| 就近導流 | DNS 導向最近 edge | Anycast 路由到最近 edge |
| 後端切換 | Origin group（每個 GET/HEAD/OPTIONS 請求重試） | Endpoint／Region 健康檢查，快速切換，不受 DNS 快取影響 |
| 終止連線 | 在 edge 終止 TCP 與 TLS | 在 edge 終止 TCP，TLS 交給 endpoint |
| 內容控制 | Behavior、cache policy、signed URL、geo restriction、edge functions、WAF | 只有 listener、traffic dial、weight、affinity |
| 典型場景 | 網站、圖片、影片、API 加速、S3 私有內容 | 遊戲（UDP）、IoT、VoIP、非 HTTP 協定、固定 IP 白名單、多 Region 快速 failover |

> [!note] 關於 CloudFront 的固定 IP
> AWS 近年另外提供 CloudFront anycast static IP 功能，給有特殊需求（例如需要固定 IP 的電信合作）的客戶申請使用。但在一般考題中，「需要固定 IP」的標準答案仍是 Global Accelerator，或第 10 章的 NLB。

### 和其他「加速」功能的區分

- **S3 Transfer Acceleration**：讓使用者**上傳**到 S3 時從最近的 edge 進入 AWS 網路，適合全球使用者上傳大檔到單一 bucket（第 22 章）。下載與快取要用 CloudFront。
- **Route 53 latency-based routing**（第 9 章）：用 DNS 把使用者導到延遲最低的 Region，但封包仍走公共 Internet，切換受 DNS 快取影響。Global Accelerator 是封包層的版本。

### 選型流程

```text
流量是 HTTP/HTTPS 嗎？
├─ 是 → 內容可以快取，或需要邊緣安全控制（WAF、signed URL、geo、OAC）？
│        ├─ 是 → CloudFront
│        └─ 否（純動態、但要固定 IP 或多 Region 快速切換）
│                 → Global Accelerator → ALB（也可以兩者並用於不同網域）
└─ 否（TCP/UDP、自訂協定、遊戲、VoIP、IoT）
         → 需要全球加速、固定 IP、多 Region failover？
              ├─ 是 → Global Accelerator → NLB / EC2
              └─ 否，單一 Region 即可 → NLB（每 AZ 固定 IP，第 10 章）
```

## 11.12 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 全球使用者、靜態內容慢、降低 origin 負載 | CloudFront |
| S3 bucket 要私有、只能經 CloudFront 存取 | OAC + bucket policy（`AWS:SourceArn` 限定 distribution） |
| OAI | 舊做法，改用 OAC |
| S3 用 SSE-KMS，CloudFront 回 403 | KMS key policy 允許 CloudFront 服務主體解密 |
| 只給付費使用者下載單一檔案 | CloudFront signed URL |
| 影片串流、多個檔案、不想改 URL | CloudFront signed cookie |
| 依國家封鎖內容 | Geo restriction（細緻規則用 WAF） |
| 信用卡號等敏感欄位，只有特定後端能解密 | Field-level encryption |
| CloudFront 自訂網域的憑證 | ACM 憑證必須在 us-east-1 |
| 頻繁部署、要立即生效、避免 invalidation 成本 | 版本化檔名（必要時 invalidation） |
| 命中率低、origin 負載高 | 縮減 cache key（cache policy），其餘值改用 origin request policy；考慮 Origin Shield |
| 簡單 header／URL 改寫、每秒大量請求、最低成本 | CloudFront Functions |
| 需要呼叫外部服務、讀 body、依條件選 origin | Lambda@Edge（us-east-1 建立） |
| 靜態內容 origin 故障時自動改用另一個 Region | Origin group（origin failover） |
| 防止使用者繞過 CloudFront 直接連 ALB | VPC origin；或 origin-facing prefix list + custom header |
| UDP、遊戲、VoIP、IoT、非 HTTP 協定的全球加速 | Global Accelerator |
| 固定 IP 白名單、anycast | Global Accelerator（2 個 static IP） |
| 多 Region 快速 failover、不受 DNS 快取影響 | Global Accelerator |
| 逐步把流量移到新 Region | Global Accelerator traffic dial |
| 全球使用者上傳大檔到 S3 | S3 Transfer Acceleration |

**常見陷阱**：

1. 在 origin 所在 Region 申請 ACM 憑證給 CloudFront：CloudFront 只讀 us-east-1 的 ACM 憑證。
2. 用 S3 website endpoint 搭配 OAC：website endpoint 是 custom origin，不支援 OAC。
3. 以為 Global Accelerator 會快取內容，或以為 CloudFront 能代理 UDP：兩者能力不重疊。
4. 以為 origin `no-store` 一定有效：Minimum TTL 大於 0 時 CloudFront 仍會快取。
5. 以為 origin failover 能保護寫入 API：它只對 GET、HEAD、OPTIONS 生效。
6. 把 S3 presigned URL 當成 CloudFront signed URL：前者繞過 CloudFront，沒有邊緣快取與控制。

## 11.13 SAP 加深：多 Region、遷移與治理

**多 Region active-active 的入口。** Wanderly 進入全球化階段後（第 42 章），會在東京與法蘭克福各有一套完整的應用。HTTP 流量可以用 CloudFront 搭配兩個 Region 的 origin（以 Lambda@Edge 或 Route 53 latency record 作為 origin 網域決定 Region）；需要固定 IP 與快速、不受 DNS 快取影響之 failover 的 API，則用 Global Accelerator 的兩個 endpoint group。SAP 題目若同時要求「不受 DNS 快取影響的 failover」與「固定 IP」，答案指向 Global Accelerator；若要求「快取、WAF、內容保護」，CloudFront 不可少。兩者也常常同時存在於同一個架構，分別服務不同網域或不同流量類型。

**用 traffic dial 做 Region 遷移。** 從單一 Region 遷移到新 Region，或做 Region 層級的 blue/green 時，先把新 Region 的 endpoint group 加入 accelerator，traffic dial 設 0%，確認健康後逐步提高到 10%、50%、100%，再把舊 Region 降為 0%。Client 端完全不用改 IP，回退只要調整 dial。

**集中治理 edge 安全。** 多帳號環境中，WAF web ACL 可以由 **AWS Firewall Manager**（第 16 章）統一套用到所有帳號的 CloudFront distribution；CloudFront 的 WAF web ACL 必須建立在 global scope（在 us-east-1 管理）。CloudFront 的 standard logs 可以集中寫到日誌帳號的 S3，real-time logs 則送到 Kinesis Data Streams 做即時分析（第 31 章）。

**Origin 的進階隔離與成本。** 大量 Region 的使用者共用一個 origin 時，Origin Shield 可以把 cache miss 匯集成一份，減少跨 Region 傳輸與 origin 運算；多個 CloudFront distribution 指向同一個 S3 bucket 時，bucket policy 可以列出多個 distribution ARN。SAP 題目若提到「CloudFront 前面有 WAF，但安全稽核發現 origin 仍可從 Internet 直接存取」，最強的答案是 VPC origin 讓 ALB 變成 internal。

## 本章重點整理

- CDN 靠「快取」與「就近終止連線」降低延遲；CloudFront 由 edge location、regional edge cache 與可選的 Origin Shield 組成，是全球服務。
- Distribution 是 CloudFront 的設定單位，可以有多個 origin；cache behavior 依排列順序比對路徑，最後是 `*` default behavior。
- Cache key 只應包含會改變回應內容的值；cache policy 決定 cache key 與 TTL，origin request policy 決定額外轉送給 origin、但不影響快取的值。
- TTL 以 origin 的 `Cache-Control` 為主，受 cache policy 的 minimum／maximum 限制；Minimum TTL 大於 0 會覆蓋 origin 的 no-store。
- 內容更新可用 invalidation（每月前 1,000 個路徑免費）或版本化檔名；頻繁部署時版本化檔名較好。
- 私有 S3 origin 用 OAC，bucket policy 允許 `cloudfront.amazonaws.com` 並以 `AWS:SourceArn` 限定 distribution；SSE-KMS 還要修改 key policy；OAI 是舊做法，website endpoint 不支援 OAC。
- Signed URL 適合單一檔案，signed cookie 適合多個檔案或不想改 URL；建議使用 trusted key group。
- Geo restriction 依國家允許或封鎖整個 distribution；field-level encryption 在邊緣以公鑰加密指定欄位，只有持私鑰的後端能解密。
- 防止繞過 CloudFront：S3 用 OAC；ALB 用 VPC origin，或 origin-facing prefix list 加 custom header。
- CloudFront 自訂網域的 ACM 憑證必須在 us-east-1；ALB origin 的憑證則在 ALB 所在 Region。
- CloudFront Functions 只能在 viewer 觸發、無網路、極低成本；Lambda@Edge 支援四個觸發點、可存取網路與 body，必須在 us-east-1 建立。
- Origin group 在 primary 回應指定錯誤或逾時時改用 secondary，只適用 GET、HEAD、OPTIONS。
- Global Accelerator 提供 2 個固定 anycast IP，支援 TCP/UDP，endpoint 可為 ALB、NLB、EC2、EIP，故障切換不受 DNS 快取影響。
- Traffic dial（0–100%）控制 Region 層級的流量比例，endpoint weight（0–255）控制 Region 內 endpoint 的比例。
- CloudFront 用於可快取或需要邊緣控制的 HTTP 內容；Global Accelerator 用於 TCP/UDP、固定 IP 與多 Region 快速 failover；兩者不互相取代。

## 本章練習題

### 練習 11-1｜SAA｜單選｜私有 S3 origin

Wanderly 把旅館照片存在 `wanderly-hotel-photos` bucket，目前 bucket 設為公開讀取，網站透過 CloudFront distribution `E2QWRUHEXAMPLE` 提供照片。資安稽核要求 bucket 必須私有，且只有這個 distribution 能讀取物件，使用者無法直接用 S3 URL 下載。

最合適的做法是什麼？

- A. 把 origin 改成 S3 static website endpoint，並在 bucket policy 允許 `cloudfront.amazonaws.com`
- B. 保持 bucket 公開讀取，但把 S3 URL 改成難以猜測的隨機前綴
- C. 為 S3 REST endpoint origin 設定 OAC，開啟 Block Public Access，並在 bucket policy 允許 `cloudfront.amazonaws.com` 執行 `s3:GetObject`，以 `AWS:SourceArn` 限定為該 distribution
- D. 改由應用程式為每張照片產生 S3 presigned URL，讓瀏覽器直接向 S3 下載

> [!answer]- 答案：C
> **A ✗** S3 website endpoint 在 CloudFront 中屬於 custom origin，不支援 OAC，通常需要公開讀取，無法滿足「bucket 私有」。
>
> **B ✗** 隱藏 URL 不是存取控制；只要有人取得網址，就能繞過 CloudFront 直接下載，也違反私有要求。
>
> **C ✓** OAC 讓 CloudFront 以 SigV4 簽署對 S3 REST endpoint 的請求；bucket policy 只允許 CloudFront 服務主體，並以 `AWS:SourceArn` 綁定單一 distribution。Block Public Access 保持開啟，使用者無法直接從 S3 取得物件。
>
> **D ✗** Presigned URL 讓流量繞過 CloudFront，失去邊緣快取帶來的速度與成本優勢，也無法套用 CloudFront 上的邊緣控制。
>
> **考點**：SAA-1.2、SAA-1.3｜OAC 與 bucket policy

### 練習 11-2｜SAA｜單選｜依路徑分到不同 origin

Wanderly 希望 `www.wanderly.com` 的所有流量都經過同一個 CloudFront distribution：前端靜態檔放在 S3，可以快取一天；`/api/*` 送到東京的 ALB，不可快取，且需要支援 POST。團隊希望以最少的元件達成。

應如何設定？

- A. 建立兩個 origin（S3 與 ALB）；新增 path pattern 為 `/api/*` 的 cache behavior 指向 ALB，使用 CachingDisabled cache policy 並允許所有 HTTP 方法；default behavior 指向 S3 並使用快取 policy
- B. 建立兩個 distribution，用 Route 53 依 URL path 把請求導到不同 distribution
- C. 只設定 default behavior 指向 ALB，再由 ALB 把靜態檔請求 redirect 到 S3
- D. 把 default TTL 設為 0，讓所有內容都不快取，以避免 API 回應被快取

> [!answer]- 答案：A
> **A ✓** 一個 distribution 可以有多個 origin，cache behavior 依路徑把請求送到不同 origin，並套用各自的 cache policy 與允許的方法。API 用 CachingDisabled，靜態檔用長 TTL，一個入口即可滿足。
>
> **B ✗** DNS 查詢只包含網域名稱，Route 53 看不到 URL 路徑，無法依 `/api/*` 分流。
>
> **C ✗** 讓所有請求都先到東京的 ALB 再 redirect，靜態檔失去邊緣快取，還多一次往返，也讓 S3 必須公開。
>
> **D ✗** 全部不快取雖然避免 API 被快取，但靜態檔也失去 CDN 的效益，origin 負載與延遲都會上升。
>
> **考點**：SAA-3.4｜CloudFront cache behavior 與多 origin

### 練習 11-3｜SAA｜單選｜付費影片串流

Wanderly 推出付費旅遊影片，以 HLS 格式提供，每支影片由一個播放清單與數百個片段檔組成，全部透過 CloudFront 提供。只有登入的訂閱會員能觀看，團隊不希望修改播放器載入片段檔的 URL 格式。

最合適的做法是什麼？

- A. 為每個片段檔產生 CloudFront signed URL
- B. 會員登入後由應用程式設定 CloudFront signed cookie，在影片路徑的 behavior 要求 trusted key group 簽章
- C. 使用 geo restriction 只允許會員所在國家
- D. 為每個片段檔產生 S3 presigned URL，讓播放器直接向 S3 下載

> [!answer]- 答案：B
> **A ✗** Signed URL 適合單一檔案；數百個片段檔都要改寫 URL，違反不修改 URL 格式的要求，也增加播放器與應用程式的複雜度。
>
> **B ✓** Signed cookie 一次授權多個檔案，原本的 URL 不需改變；CloudFront 在邊緣驗證 cookie 中的簽章與到期時間，適合影片串流與會員專區。
>
> **C ✗** Geo restriction 依國家而不是依會員身份控制，同一國家的非會員一樣能觀看。
>
> **D ✗** Presigned URL 讓流量繞過 CloudFront，失去快取效益，數百個片段也都要改 URL。
>
> **考點**：SAA-1.2｜signed URL vs signed cookie

### 練習 11-4｜SAA｜單選｜CloudFront 自訂網域憑證

工程師在 `ap-northeast-1` 的 ACM 為 `www.wanderly.com` 申請並驗證了一張公開憑證，給東京的 ALB 使用。接著建立 CloudFront distribution 並加入 alternate domain name `www.wanderly.com`，卻在憑證選單中找不到這張憑證。

應如何解決？

- A. 在 distribution 中改用 dedicated IP 的 SSL 方式，才能選擇其他 Region 的憑證
- B. 把 distribution 的 price class 改為只包含亞洲地區
- C. 把 ALB 的憑證匯出後上傳到 IAM 憑證存放區，再讓 CloudFront 從 IAM 讀取
- D. 在 `us-east-1` 的 ACM 為 `www.wanderly.com` 申請憑證，並在 distribution 選擇它；東京的憑證繼續給 ALB 使用

> [!answer]- 答案：D
> **A ✗** Dedicated IP 只是給不支援 SNI 的舊 client 使用的提供方式，不會改變 CloudFront 只讀取 us-east-1 ACM 憑證的限制，費用還很高。
>
> **B ✗** Price class 只決定使用哪些地區的 edge location，與憑證所在 Region 無關。
>
> **C ✗** ACM 簽發的公開憑證無法匯出私鑰；即使可行，也失去 ACM 自動更新的好處。
>
> **D ✓** CloudFront 是全球服務，只能使用 us-east-1 ACM 中的憑證。同一個網域可以在 us-east-1 與 ap-northeast-1 各有一張 ACM 憑證，分別給 CloudFront 與 ALB 使用，兩者都會自動更新。
>
> **考點**：SAA-1.3｜CloudFront 的 ACM 憑證必須在 us-east-1

### 練習 11-5｜SAA｜單選｜頻繁部署的快取更新

Wanderly 的前端每天部署 10 次以上，包含數百個 JS、CSS 檔。團隊希望這些靜態檔在 CloudFront 上快取一年以降低 origin 負載，但每次部署後使用者必須立即拿到新版，並避免持續產生 invalidation 費用與等待傳播時間。

最合適的做法是什麼？

- A. 在建置流程為 JS、CSS 檔名加入內容雜湊（例如 `app.3f9a1c.js`），HTML 以短 TTL 快取並引用新檔名
- B. 每次部署後對 `/*` 建立 invalidation
- C. 把所有靜態檔的 cache policy 改為 CachingDisabled
- D. 把 Minimum TTL 設為 0，並要求使用者在部署後清除瀏覽器快取

> [!answer]- 答案：A
> **A ✓** 版本化檔名讓每次部署的新檔案都是從未被快取過的新 URL，使用者立即取得新版；舊檔名自然過期，靜態檔仍可設很長的 TTL。只有引用它們的 HTML 需要短 TTL，不需要每次 invalidation。
>
> **B ✗** Invalidation 能清掉快取，但每天多次、跨大量節點傳播需要時間，且清除後所有請求都會回 origin，與「降低 origin 負載」的目標衝突。
>
> **C ✗** 完全不快取等於放棄 CDN，origin 負載與延遲大增。
>
> **D ✗** Minimum TTL 不會讓已快取的舊檔立即失效；要求使用者清除快取也不是可行的設計。
>
> **考點**：SAA-3.4、SAA-4.4｜版本化檔名 vs invalidation

### 練習 11-6｜SAA｜選兩項｜提高快取命中率

Wanderly 的照片 behavior 命中率只有 8%，S3 的請求量和沒有 CloudFront 時幾乎一樣。調查發現 cache policy 把所有 header、所有 cookie 與所有 query string 都納入 cache key。照片內容只會因 `width` query string 而不同；origin 端的記錄需要收到 `User-Agent` header，但它不影響回應內容。

哪兩項變更最合適？（選兩項）

- A. 把 Maximum TTL 縮短到 60 秒，讓快取更快更新
- B. 修改 cache policy，讓 cache key 只包含 `width` query string，不包含 cookie 與其他 header
- C. 改用 S3 Transfer Acceleration 加速 origin 回應
- D. 使用 origin request policy 把 `User-Agent` 轉送給 origin，但不把它納入 cache key
- E. 每小時對照片路徑建立 invalidation，強制重新快取

> [!answer]- 答案：B、D
> **A ✗** 縮短 TTL 會讓物件更快過期、更常回 origin，命中率只會更低。
>
> **B ✓** 只有會改變回應內容的值才應納入 cache key。每位使用者的 cookie 都不同，把它們納入 cache key 會把同一張照片拆成無數份快取；只保留 `width` 後，同尺寸的請求就能共用快取。
>
> **C ✗** Transfer Acceleration 用於加速上傳到 S3，不解決 CloudFront 快取被切碎的問題。
>
> **D ✓** Origin request policy 讓 origin 收到記錄所需的 `User-Agent`，同時不增加快取變體，命中率不受影響。
>
> **E ✗** 定期 invalidation 會清掉已快取的物件，讓命中率更差，也增加費用。
>
> **考點**：SAA-3.4、SAA-4.4｜cache policy 與 origin request policy

### 練習 11-7｜SAA｜單選｜依國家限制內容

Wanderly 與一家影片製作公司簽約，部分旅遊紀錄片只取得台灣、日本與新加坡的播放授權。這些影片放在一個專用的 CloudFront distribution 上。團隊希望以最少的開發工作阻擋其他國家的使用者。

最合適的做法是什麼？

- A. 在 S3 bucket policy 中以 `aws:SourceIp` 列出三個國家的所有 IP 範圍
- B. 在應用程式登入時要求使用者填寫所在國家
- C. 在 distribution 啟用 geo restriction，設定只允許台灣、日本與新加坡
- D. 使用 Global Accelerator 只在亞洲 Region 建立 endpoint group

> [!answer]- 答案：C
> **A ✗** 國家的 IP 範圍龐大且經常變動，手動維護不可行；而且經 CloudFront 存取時，S3 看到的來源是 CloudFront，不是使用者。
>
> **B ✗** 使用者自行填寫的國家無法驗證，不能作為授權控制。
>
> **C ✓** Geo restriction 依使用者 IP 判斷國家，allow list 以外的請求在邊緣直接回 403，不需要開發，正好符合整個 distribution 的授權限制。
>
> **D ✗** Endpoint group 的 Region 決定流量送往哪裡處理，不會阻擋其他國家的使用者連線；GA 也不提供影片快取。
>
> **考點**：SAA-1.2｜CloudFront geo restriction

### 練習 11-8｜SAA｜單選｜邊緣 URL 轉址

Wanderly 改版後，舊網址 `/hotels.php?id=123` 要以 301 永久轉址到 `/hotel/123`。網站每天有數千萬次請求，轉址邏輯簡單，不需要查詢任何外部資料，團隊希望延遲最低、成本最低。

最合適的做法是什麼？

- A. 在 origin request 觸發點部署 Lambda@Edge 函式產生 301 回應
- B. 在東京 ALB 上為每個舊網址建立 redirect 規則
- C. 使用 Global Accelerator 的 listener 改寫 URL
- D. 在 viewer request 觸發點部署 CloudFront Functions，直接回傳 301 與新網址

> [!answer]- 答案：D
> **A ✗** Lambda@Edge 能做到，但成本較高；而且 origin request 只在 cache miss 時執行，轉址邏輯放在這裡也不是最直接的位置。
>
> **B ✗** 每個請求都要回到東京才轉址，延遲高；ALB 規則數量也有上限，不適合大量網址對照。
>
> **C ✗** Global Accelerator 工作在 TCP/UDP 層，看不到 HTTP URL，無法改寫或轉址。
>
> **D ✓** CloudFront Functions 在每個 edge location 的 viewer request 階段執行，適合簡單、無網路存取、每個請求都要做的轉換，延遲與成本都最低。對照表較大時還可搭配 CloudFront KeyValueStore。
>
> **考點**：SAA-3.4、SAA-4.4｜CloudFront Functions vs Lambda@Edge

### 練習 11-9｜SAA｜單選｜UDP 遊戲的全球入口

Wanderly 的子公司推出一款旅遊主題的多人手機遊戲，使用 UDP 協定，伺服器部署在東京與法蘭克福的 NLB 後面。全球玩家抱怨延遲抖動，且部分企業網路要求把遊戲伺服器 IP 加入白名單。團隊也希望某個 Region 故障時，玩家能在不更新 DNS 的情況下自動連到另一個 Region。

最合適的做法是什麼？

- A. 建立 CloudFront distribution，以兩個 NLB 為 origin group
- B. 建立 Global Accelerator，設定 UDP listener，東京與法蘭克福各一個 endpoint group，endpoint 為各自的 NLB
- C. 使用 Route 53 latency-based routing 指向兩個 NLB，並把 TTL 設為 0
- D. 在兩個 Region 的 NLB 各綁 Elastic IP，讓玩家 app 內建四個 IP 並自行重試

> [!answer]- 答案：B
> **A ✗** CloudFront 只處理 HTTP(S)，無法代理 UDP 遊戲流量；origin group 也只適用於 GET、HEAD、OPTIONS 請求。
>
> **B ✓** Global Accelerator 支援 UDP，提供兩個固定 anycast IP 方便白名單，讓玩家從最近的 edge 進入 AWS 骨幹網路以降低抖動；endpoint group 健康檢查失敗時自動改送另一個 Region，不依賴 DNS。
>
> **C ✗** Latency routing 仍走公共 Internet，不改善抖動；許多 resolver 與 client 不會完全遵守極低 TTL，failover 受 DNS 快取影響，IP 也不固定。
>
> **D ✗** 讓 client 自行管理多組 IP 與重試，營運與開發負擔高，也沒有骨幹網路加速。
>
> **考點**：SAA-3.4、SAA-2.2｜Global Accelerator 的 UDP 與 anycast IP

### 練習 11-10｜SAA｜單選｜靜態內容的跨 Region 容錯

Wanderly 的前端靜態檔放在東京的 S3 bucket，透過 CloudFront 提供，並已用 S3 Cross-Region Replication 複製到新加坡的 bucket。團隊希望東京 bucket 無法回應時，CloudFront 能自動改從新加坡取得內容，不需要人工介入或修改 DNS。

最合適的做法是什麼？

- A. 建立第二個 distribution 指向新加坡 bucket，以 Route 53 failover record 切換兩個 distribution
- B. 在 cache policy 中把 Maximum TTL 設為一年，讓 edge 一直保留舊內容
- C. 建立 origin group，以東京 bucket 為 primary、新加坡 bucket 為 secondary，設定在 5xx 與 403/404 等狀態碼時 failover，並讓 default behavior 使用這個 origin group
- D. 使用 Global Accelerator，把兩個 S3 bucket 設為不同 Region 的 endpoint

> [!answer]- 答案：C
> **A ✗** 能達成容錯，但多一個 distribution 與 DNS 切換，受 DNS 快取影響，營運負擔也較高，違反「不修改 DNS」的意圖。
>
> **B ✗** 長 TTL 只能讓已快取的物件繼續提供，cache miss 時仍會失敗，不是容錯設計。
>
> **C ✓** Origin group 讓 CloudFront 在 primary 回應指定錯誤碼或逾時時，對同一個請求改向 secondary 取得內容。靜態內容只使用 GET 與 HEAD，正好符合 origin failover 的適用範圍。
>
> **D ✗** S3 bucket 不能作為 Global Accelerator 的 endpoint，GA 也不提供內容快取。
>
> **考點**：SAA-2.2｜CloudFront origin group failover

### 練習 11-11｜SAP｜單選｜邊緣加密信用卡欄位

Wanderly 的訂房表單以 HTTPS POST 經 CloudFront 送到 ALB，後端有日誌、訂單、推薦等多個服務會經手請求內容。為縮小 PCI DSS 稽核範圍，安全團隊要求信用卡號從離開使用者附近的 edge 開始，就只有支付服務能解密，其他服務即使讀到請求內容也只能看到密文。團隊希望不修改前端表單。

最合適的做法是什麼？

- A. 把 ALB 與後端之間改用 HTTPS，並在每個服務啟用 SSE-KMS
- B. 在 CloudFront 上設定 field-level encryption，上傳支付服務的公鑰並指定信用卡號欄位；只有持有對應私鑰的支付服務能解密
- C. 在 CloudFront 前掛 AWS WAF，以規則遮罩請求中的信用卡號
- D. 使用 Lambda@Edge 在 viewer request 將信用卡號以 KMS 加密，所有後端服務共用解密權限

> [!answer]- 答案：B
> **A ✗** 傳輸加密只保護網路上的資料，每個服務收到後仍是明文；SSE-KMS 是儲存加密，也不能限制哪個服務看得到欄位內容。
>
> **B ✓** Field-level encryption 在 CloudFront 邊緣用公鑰加密指定的 POST 欄位，之後的整條鏈路上都只是密文，只有持私鑰的支付服務能解密；前端表單不用修改，正好縮小 PCI 範圍。
>
> **C ✗** WAF 依規則允許或封鎖請求，不提供加密或改寫欄位內容的功能。
>
> **D ✗** 自行開發加密邏輯營運負擔高，而且讓所有後端共用解密權限，等於沒有縮小可讀取明文的範圍。
>
> **考點**：SAP-1.2、SAP-2.3｜CloudFront field-level encryption

### 練習 11-12｜SAP｜選兩項｜防止繞過 CloudFront 存取 ALB

Wanderly 的 API 經 CloudFront 提供，distribution 掛有 WAF。稽核發現 origin 是 internet-facing ALB，攻擊者可以直接連 ALB 的 DNS 名稱繞過 WAF。因為 ALB 同時被一個依賴其 public 位址的舊系統使用，本季無法改成 internal ALB 或使用 VPC origin。團隊要確保只有來自 Wanderly 這個 distribution 的請求能被 ALB 處理。

哪兩個步驟組合起來最合適？（選兩項）

- A. 把 Route 53 中 ALB 的 TTL 調低，讓攻擊者較快失去 ALB 位址
- B. 在 ALB 的 security group 中，HTTPS 入站來源只允許 CloudFront origin-facing managed prefix list
- C. 在 CloudFront 啟用 geo restriction，封鎖攻擊者所在國家
- D. 讓 CloudFront 對 origin 加上含有秘密值的 custom header，並在 ALB listener rule 只轉送帶有正確 header 的請求，其餘以 fixed-response 回 403
- E. 在 ALB 上啟用 sticky session，讓只有 CloudFront 建立的 session 能存取

> [!answer]- 答案：B、D
> **A ✗** TTL 只影響 DNS 快取時間，攻擊者已知的 ALB 位址仍可直接連線，不是存取控制。
>
> **B ✓** Origin-facing prefix list 包含 CloudFront 對 origin 發出請求的位址，SG 只允許它，能擋下絕大多數直接連線。但所有客戶的 CloudFront 都使用這些位址，所以還需要搭配下一個步驟。
>
> **C ✗** Geo restriction 只作用在經過 CloudFront 的請求，攻擊者直接連 ALB 時根本不經過 CloudFront。
>
> **D ✓** 只有 Wanderly 的 distribution 會加上這個秘密 header；ALB 規則驗證 header，可擋下「透過別人的 CloudFront distribution 打過來」的請求。秘密值應定期輪替（可存放在 Secrets Manager）。
>
> **E ✗** Stickiness 只影響請求送往哪個 target，不驗證來源，任何 client 都能取得 cookie。
>
> **考點**：SAP-1.2、SAP-3.2｜CloudFront origin 保護：prefix list 與 custom header

### 練習 11-13｜SAP｜單選｜Region 遷移的流量轉移

Wanderly 的即時房價 API 使用 Global Accelerator，目前唯一的 endpoint group 在東京，endpoint 是 NLB。公司決定把服務遷移到新加坡 Region，要求逐步轉移流量、每個階段觀察錯誤率，出問題時能在一分鐘內回退，而且數百家合作夥伴設定的白名單 IP 不能改變。

最合適的做法是什麼？

- A. 為新加坡建立新的 accelerator，完成驗證後通知合作夥伴更新白名單 IP
- B. 在既有 accelerator 的 listener 加入新加坡 endpoint group，traffic dial 從低比例開始，逐步提高新加坡並降低東京的 traffic dial，出問題時調回
- C. 使用 Route 53 weighted record 在兩個 Region 的 NLB 之間分配比例
- D. 把東京 NLB 的 endpoint weight 調為 0，讓所有流量一次切換到新加坡

> [!answer]- 答案：B
> **A ✗** 新的 accelerator 會有不同的 anycast IP，違反白名單 IP 不能改變的要求。
>
> **B ✓** 在同一個 accelerator 內新增 endpoint group，IP 完全不變；traffic dial 在 AWS 網路內立即生效，可以分階段調整並快速回退，不受 DNS 快取影響。
>
> **C ✗** 合作夥伴連的是 GA 的固定 IP，不經過 Route 53；改用 DNS 分流還會讓 IP 變動並受快取影響。
>
> **D ✗** 一次全部切換不符合「逐步轉移、觀察錯誤率」的要求；如果新加坡有問題，所有流量同時受影響。
>
> **考點**：SAP-2.1、SAP-4.2｜Global Accelerator traffic dial 遷移

### 練習 11-14｜SAP｜選兩項｜同一產品的兩種流量

Wanderly 為合作旅行社提供兩項服務：一是可下載的每日房價報表與飯店圖片包（HTTP，同一份檔案會被數百家旅行社下載），二是自訂 TCP 協定的即時房價推播（長連線、不可快取）。旅行社分布在亞洲、歐洲與北美，推播服務要求固定入口 IP 與 Region 故障時自動切換。團隊希望每種流量都使用最適合的服務，並控制成本。

哪兩項設計最合適？（選兩項）

- A. 報表與圖片包透過 CloudFront 提供，origin 為 S3 並使用 OAC，讓重複下載在邊緣快取
- B. 所有流量都先進 Global Accelerator，再由 GA 轉給 CloudFront 處理快取
- C. 讓 CloudFront 以 custom origin 代理即時 TCP 推播協定
- D. 報表與圖片包也透過 Global Accelerator 提供，因為 GA 會在 edge 快取熱門檔案
- E. 即時推播透過 Global Accelerator 的 TCP listener，endpoint group 指向各 Region 的 NLB

> [!answer]- 答案：A、E
> **A ✓** 同一份檔案被大量重複下載，最適合 CDN 快取，能大幅減少 origin 流量與跨 Region 傳輸成本；OAC 讓 S3 保持私有。
>
> **B ✗** CloudFront distribution 不能作為 Global Accelerator 的 endpoint；兩者是獨立的入口，不需要串接。
>
> **C ✗** CloudFront 只處理 HTTP(S)，無法代理自訂的 TCP 協定。
>
> **D ✗** Global Accelerator 不快取任何內容，大量重複下載每次都要回 origin，成本與 origin 負載都較高。
>
> **E ✓** Global Accelerator 支援 TCP，提供固定 anycast IP 與跨 Region 健康切換，NLB 適合承載長連線的自訂協定。
>
> **考點**：SAP-2.5、SAP-1.1｜CloudFront 與 Global Accelerator 分工

### 練習 11-15｜SAP｜單選｜依會員等級動態選擇 origin

Wanderly 在 CloudFront 後面有兩個 origin：一般會員使用的 ALB 與 VIP 會員專屬、容量保留的 ALB。使用者的會員 ID 存在 cookie 中，會員等級必須即時查詢一個 DynamoDB global table 才能確定（等級可能隨時升級）。團隊希望在邊緣完成判斷，避免所有請求都先到一般 ALB 再轉送。

最合適的做法是什麼？

- A. 在 viewer request 觸發點使用 CloudFront Functions 查詢 DynamoDB，再改寫 origin
- B. 建立兩個 cache behavior，依 cookie 名稱的 path pattern 選擇 origin
- C. 在 origin request 觸發點使用 Lambda@Edge，讀取 cookie 查詢 DynamoDB 後改寫請求的 origin，並把會員等級納入快取區分
- D. 在一般 ALB 設定 listener rule，依 cookie 把 VIP 請求 redirect 到 VIP ALB 的網址

> [!answer]- 答案：C
> **A ✗** CloudFront Functions 沒有網路存取能力，無法查詢 DynamoDB，也不能在 origin 相關的觸發點執行。
>
> **B ✗** Cache behavior 只依 URL 路徑比對，不能依 cookie 內容選擇 origin。
>
> **C ✓** Lambda@Edge 可以存取網路並在 origin request 階段修改請求的 origin，適合需要查詢外部資料再決定路由的情境。若回應會因會員等級不同而不同，cache key 也必須能區分，避免 VIP 內容被快取給一般會員。
>
> **D ✗** 所有請求仍先到一般 ALB，違反「在邊緣完成判斷」；ALB 也不能查 DynamoDB 判斷即時會員等級，redirect 還暴露另一個入口。
>
> **考點**：SAP-2.5、SAP-3.3｜Lambda@Edge origin request 動態路由

### 練習 11-16｜SAP｜單選｜SSE-KMS bucket 與 OAC

Wanderly 的合規團隊要求行程文件 bucket 改用 customer managed KMS key 的 SSE-KMS 加密。改完後，透過 CloudFront（已設定 OAC、bucket policy 也允許該 distribution 的 `s3:GetObject`）下載新上傳的文件時，使用者收到 403 錯誤；改加密前上傳的舊文件仍能正常下載。

最可能的原因與修正是什麼？

- A. OAC 不支援 SSE-KMS，必須改回 OAI
- B. 在 bucket policy 中把 Principal 改為 `*`，讓 CloudFront 能讀取加密物件
- C. CloudFront 的 cache policy 必須把 `x-amz-server-side-encryption` header 納入 cache key
- D. KMS key policy 沒有允許 CloudFront 使用該 key；在 key policy 加入允許 `cloudfront.amazonaws.com` 執行 `kms:Decrypt`，並以 `AWS:SourceArn` 限定為該 distribution

> [!answer]- 答案：D
> **A ✗** 正好相反，OAC 支援 SSE-KMS，OAI 才不支援；改回 OAI 無法解決問題。
>
> **B ✗** 把 Principal 改為 `*` 會讓物件公開（若未被 Block Public Access 擋下），且仍然沒有授予 KMS 解密權限。
>
> **C ✗** Cache key 只影響快取區分，與 S3 是否能為 CloudFront 解密物件無關。
>
> **D ✓** SSE-KMS 物件的讀取需要 S3 權限與 KMS 解密權限兩者兼具。Bucket policy 已允許讀取，但 customer managed key 的 key policy 也必須允許 CloudFront 服務主體執行 `kms:Decrypt`，並用 SourceArn 限縮到這個 distribution。舊文件未用這把 key 加密，所以不受影響。
>
> **考點**：SAP-1.2、SAP-3.2｜OAC 搭配 SSE-KMS 的 key policy
