---
chapter: 9
title: Route 53：DNS 與流量管理
part: 1
---

# 第 9 章　Route 53：DNS 與流量管理

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚 Route 53 的四個角色：網域註冊、權威 DNS（hosted zone）、health check 與 VPC 內的 Resolver
> - 為 zone apex 選對 alias 與 CNAME，並理解 TTL 如何影響切換速度
> - 依需求選擇 8 種 routing policy（simple、weighted、latency、failover、geolocation、geoproximity、multivalue answer、IP-based），並把它們組合成多層的流量政策
> - 設計 health check（endpoint、calculated、CloudWatch alarm），做出 active-passive 與 active-active 的 DNS failover
> - 管理 private hosted zone、跨帳號 VPC 關聯、split-horizon DNS 與 DNSSEC
>
> **前置知識**：第 3 章（DNS 解析流程、TTL、A／AAAA／CNAME）、第 5 章（VPC DNS 屬性）、第 8 章（Resolver endpoints）
> **考試比重**：SAA ★★★（Domain 2 高可用、Domain 3 網路效能）｜SAP ★★☆（Domain 1 可靠架構、Domain 2 業務持續）

## 9.1 故事：wanderly.com 指不到 Load Balancer

Wanderly 創業時在一家本地網域商註冊了 `wanderly.com`，DNS 也交給網域商代管。那時網站只有一台 EC2，小林在網域商的後台加了一筆 A 記錄：`wanderly.com → 54.10.20.30`（那台 EC2 的 Elastic IP），一切都很簡單。

第 5 章之後，網站改放在 Application Load Balancer 後面。ALB 沒有固定 IP，它的節點會隨流量增減，AWS 只給一個 DNS 名稱，例如 `wanderly-alb-123456.ap-northeast-1.elb.amazonaws.com`。小林想把 `wanderly.com` 指過去，卻發現網域商的後台不允許在 `wanderly.com` 本身（沒有 `www` 的那個名稱）建立 CNAME。他只好讓 `wanderly.com` 繼續指向舊 EC2，再由那台機器把使用者轉址到 `www.wanderly.com`，等於留下了一台不能關的機器與一個單點故障。

接下來的需求更複雜：產品團隊想讓新版本先接 10% 流量；新加坡 Region 的環境建好後，要讓東南亞使用者連到較近的那一邊；東京整個 Region 出事時，要自動把使用者導到新加坡，最差也要顯示一個維護頁面；第 8 章建立的 `aws.wanderly.internal` 只能讓公司內部解析。

這些都是 DNS 層的流量管理問題。本章先釐清 Route 53 是什麼、記錄怎麼寫，再一個一個介紹 routing policy 與 health check，最後談私有 DNS 與 DNSSEC。

## 9.2 Route 53 的四個角色

**Amazon Route 53** 是 AWS 的 DNS 服務，名字來自 DNS 使用的 port 53。它其實同時扮演四個角色，考試常把它們混在一起問：

| 角色 | 做什麼 | 對應的 Route 53 功能 |
|---|---|---|
| **網域註冊商（registrar）** | 幫你向 `.com`、`.tw` 等頂級網域註冊名稱、續約 | Registered domains |
| **權威 DNS（authoritative DNS）** | 保存網域的記錄，回答「這個名稱對應什麼」 | Hosted zones |
| **健康檢查** | 定期探測 endpoint，決定 DNS 要不要回答它 | Health checks |
| **遞迴解析（recursive resolver）** | VPC 內機器查名稱時替它們四處詢問 | Route 53 Resolver（第 5、8 章） |

這四個角色彼此獨立：網域可以在別家註冊、DNS 由 Route 53 代管；也可以在 Route 53 註冊、DNS 交給別家。第 3 章介紹過解析流程，這裡用 Route 53 的名詞再走一次：

```text
使用者瀏覽器
   │ ① www.wanderly.com 的 IP 是？
   ▼
[遞迴 resolver]（ISP 或 8.8.8.8；在 VPC 裡則是 Route 53 Resolver）
   │ ② 問 root：.com 誰管？ → ③ 問 .com：wanderly.com 誰管？
   │    .com 回答：ns-123.awsdns-15.com 等 4 台（registrar 設定的 NS）
   ▼
[Route 53 權威 name server]（hosted zone：wanderly.com）
   │ ④ 依 routing policy 與 health check 選出答案，例如 ALB 的 IP，附上 TTL
   ▼
[遞迴 resolver] ── ⑤ 依 TTL 快取答案，回給瀏覽器
   ▼
瀏覽器直接連到 ALB（之後的 HTTP 流量完全不經過 Route 53）
```

① 使用者的電腦不會自己四處問，而是交給遞迴 resolver。②③ Resolver 從 root 一路問下來，`.com` 的伺服器告訴它 `wanderly.com` 由哪 4 台 Route 53 name server 負責，這份資訊來自你在網域商設定的 **NS 記錄**。④ Route 53 根據 hosted zone 裡的記錄與 routing policy 選出答案。⑤ Resolver 依 TTL 快取答案。

最重要的一句話寫在圖的最後一行：**Route 53 只回答「去哪裡」，不轉送任何應用程式流量。** 它不是 load balancer，也不是 proxy。所有 routing policy 的效果都受「resolver 快取多久」與「用戶端什麼時候重新查詢」影響，這是本章所有設計取捨的根源。

## 9.3 Hosted zone 與記錄

### Public 與 private hosted zone

**Hosted zone** 是一個網域（以及它的子網域）所有記錄的容器。

- **Public hosted zone**：回答來自 Internet 的查詢，例如 `wanderly.com`。建立時 Route 53 會自動產生一筆 **NS 記錄**（列出負責這個 zone 的 4 台 name server，分散在不同頂級網域以提高可用性）與一筆 **SOA 記錄**（zone 的管理資訊，例如負面快取的時間）。
- **Private hosted zone**：只回答來自 **已關聯 VPC** 內部的查詢，例如第 8 章的 `aws.wanderly.internal`。Internet 上的任何人都查不到（9.9 節）。

Hosted zone 每月有固定費用，查詢依數量計費。要把子網域交給另一個團隊或帳號管理，可以為 `api.wanderly.com` 建立獨立的 hosted zone，再在 `wanderly.com` 的 zone 加入一筆指向新 zone name server 的 NS 記錄，這個動作稱為 **delegation（委派）**。

### 常用記錄類型

| 類型 | 用途 | 例子 |
|---|---|---|
| **A** | 名稱 → IPv4 位址 | `www.wanderly.com → 203.0.113.10` |
| **AAAA** | 名稱 → IPv6 位址 | `www.wanderly.com → 2001:db8::10` |
| **CNAME** | 名稱 → 另一個名稱（別名） | `blog.wanderly.com → wanderly.blogservice.example` |
| **MX** | 收信的郵件伺服器與優先順序 | `10 mail.wanderly.com` |
| **TXT** | 任意文字，常用於網域驗證、SPF、DKIM | `"v=spf1 include:amazonses.com ~all"` |
| **NS** | 這個 zone 或子網域由哪些 name server 負責 | 委派子網域 |
| **SOA** | Zone 的起始授權資訊 | 自動建立 |
| **CAA** | 限制哪些憑證機構可以為這個網域簽發憑證 | `0 issue "amazon.com"` |
| **SRV**、**PTR** | 服務位置、反查（IP → 名稱） | 內部服務、郵件伺服器反查 |
| **DS** | DNSSEC 信任鏈中，父網域指向子網域的金鑰摘要 | 9.10 節 |

### TTL：答案能被快取多久

**TTL（Time To Live）** 是每筆記錄附帶的秒數，告訴 resolver「這個答案可以快取多久」。它決定了兩件互相拉扯的事：

- TTL 長（例如 86400 秒）：resolver 很少回來問，查詢費用低、解析快；但改了記錄，使用者可能一天後才看到新答案。
- TTL 短（例如 60 秒）：改記錄後很快生效，failover 也較快；但查詢量與費用增加。

> [!warning] 常見誤解
> 「切換前一刻把 TTL 從 3600 改成 60，就能馬上切換。」已經快取舊答案的 resolver 仍會保留到原本的 3600 秒到期。正確做法是 **至少提前一個舊 TTL 的時間** 先把 TTL 調低，等舊快取都過期後再切換。另外，部分用戶端與 resolver 不完全遵守 TTL，已建立的 TCP 連線也不會因 DNS 改變而中斷，所以 DNS 切換永遠不是瞬間的。

## 9.4 Alias 與 CNAME：zone apex 的解法

回到小林的問題。**Zone apex**（又稱 root domain、naked domain）是 hosted zone 的最上層名稱，例如 `wanderly.com` 本身。DNS 標準規定：**CNAME 不能和同名稱的其他記錄共存**，而 apex 一定有 NS 與 SOA 記錄，所以 **apex 不能放 CNAME**。這不是網域商的限制，而是 DNS 協定本身的規則。

Route 53 的解法是 **alias record**：一種 Route 53 特有的擴充記錄。你建立的仍是 A 或 AAAA 類型的記錄，但值不是寫死的 IP，而是「指向某個 AWS 資源」。Route 53 在回答查詢時，會即時查出該資源目前的 IP，直接以 A／AAAA 的形式回給 resolver。對外界來說，它看起來就是一筆普通的 A 記錄，所以可以放在 apex。

| 比較 | Alias | CNAME |
|---|---|---|
| 能否放在 zone apex | 可以 | 不行 |
| 指向 | 特定 AWS 資源，或同一 hosted zone 的另一筆記錄 | 任何 DNS 名稱 |
| 回給 resolver 的是 | 目標的 IP（A／AAAA） | 另一個名稱，resolver 要再查一次 |
| 查詢費用 | 指向 AWS 資源的 alias 查詢 **免費** | 一般查詢費用 |
| TTL | 不能自訂，由目標決定（例如指向 ELB 時為 60 秒） | 自行設定 |
| 目標健康 | 可開啟 **Evaluate target health**，跟隨目標的健康狀態 | 要另外設定 health check |
| Route 53 以外是否支援 | Route 53 專屬 | DNS 標準，各家都支援 |

Alias 可以指向的 AWS 資源包括：Elastic Load Balancing（ALB、NLB、CLB）、CloudFront distribution、API Gateway 的自訂網域、Elastic Beanstalk environment、設定為 **靜態網站 endpoint** 的 S3 bucket（bucket 名稱必須與記錄名稱相同）、Global Accelerator、VPC interface endpoint，以及同一 hosted zone 中的其他記錄。

**不能** 當 alias 目標的常見選項有：EC2 instance 的 public DNS 名稱、RDS endpoint。RDS 要用 CNAME 指向它的 endpoint 名稱，因為 failover 時 RDS 會更新 endpoint 背後的 IP（第 26 章）。

小林的做法是把 DNS 搬到 Route 53，然後建立兩筆 alias：`wanderly.com`（A，alias 到 ALB）與 `www.wanderly.com`（A，alias 到 ALB）。那台只負責轉址的舊 EC2 終於可以關掉了。

> [!tip] 考試提示
> 題目只要出現「zone apex」「root domain」「naked domain」再加上 ELB、CloudFront、S3 website，答案就是 **alias record**。若選項同時有「CNAME」與「alias」且目標是 AWS 資源，選 alias 幾乎不會錯，因為它還免費且自動跟隨 IP 變化。

## 9.5 網域註冊與搬家

### 在 Route 53 註冊網域

在 Route 53 註冊網域時，它會自動建立同名的 public hosted zone，並把網域的 NS 設定為這個 zone 的 4 台 name server。可以開啟 **auto-renew（自動續約）**、**transfer lock（防止網域被惡意轉出）**，以及在支援的頂級網域上隱藏聯絡人資訊。網域費用按年計，與 hosted zone 的月費分開。

### 把 DNS 代管搬到 Route 53，不中斷服務

Wanderly 的網域仍在原網域商註冊，只想把 DNS 代管搬到 Route 53。步驟如下：

1. 在 Route 53 建立 `wanderly.com` 的 public hosted zone，把原本的所有記錄（A、MX、TXT 等）完整建立起來，apex 改用 alias 指向 ALB。
2. 在 **原 DNS 服務商** 把 NS 記錄的 TTL 調低（例如 15 分鐘），並等待舊 TTL 過期。
3. 到 **網域商後台** 把 name server 改成 Route 53 hosted zone 的 4 台 name server。
4. 觀察一段時間（頂級網域本身的 NS 快取可能長達一到兩天），確認流量都由 Route 53 回答後，再停用原 DNS 服務。

順序很重要：如果先改 NS、後補記錄，在記錄補齊之前查詢會得到 NXDOMAIN，網站與郵件都會中斷。之後若要把網域註冊本身也轉到 Route 53，是另一個獨立流程（解除 transfer lock、取得授權碼），不影響 DNS 解析。

## 9.6 Routing policy：DNS 怎麼挑答案

搬家完成後，就可以處理流量管理需求了。**Routing policy（路由政策）** 決定 Route 53 收到查詢時，從同名的多筆記錄中回答哪一筆。除了 simple 之外，同名同類型的多筆記錄要各自設定唯一的 **Set ID（record identifier）** 來區分。

### Simple：最單純的一對一

**Simple routing** 是預設政策：一個名稱只有一筆記錄，但這筆記錄可以包含多個值（例如三個 IP）。Route 53 會把所有值以隨機順序全部回給 resolver，由用戶端自己挑。Simple routing **不能搭配 health check**，某個 IP 掛了，它照樣會被回答。適合只有一個 endpoint（例如 alias 到單一 ALB）的情況。

### Weighted：依比例分配

**Weighted routing** 讓多筆同名記錄各有一個權重（0–255），Route 53 依「該筆權重 ÷ 總權重」的機率選擇回答。用途：

- **Canary（金絲雀）部署**：先把一小部分真實流量放給新版本，確認沒問題再放大。例如舊版 ALB 權重 90、新版 ALB 權重 10，約 10% 的 DNS 回答會指向新版；出問題就把新版權重改回 0。相近的 **藍綠（blue/green）部署** 則是準備兩套完整環境，一次把權重整批從舊版切到新版（第 37 章）。
- **逐步搬遷**：把流量從舊環境以 10%、50%、100% 的節奏移到新環境。
- 某筆權重設為 0 就不會被回答（除非所有記錄的權重都是 0，此時平均分配）。

注意這是「DNS 回答」的比例，不是「請求」的比例。一個大型企業的 resolver 快取了一次答案，背後可能是幾千個使用者的請求，所以實際流量比例只會大致接近設定值。

### Latency：連到延遲最低的 Region

**Latency-based routing** 讓每筆記錄標示所在的 AWS Region。Route 53 依據 AWS 持續量測的「各網路位置到各 Region 的延遲」，回答對查詢者延遲最低的那一筆。Wanderly 在東京與新加坡各有一個 ALB，就可以建立兩筆 latency 記錄，讓台灣、日本的使用者多半連到東京，東南亞的使用者連到新加坡。

要注意兩點：延遲最低不等於地理距離最近；而且延遲會變動，同一個使用者在不同時間可能拿到不同 Region。所以它適合「效能優先」，不適合「資料必須留在某國」的需求。

### Failover：主備切換

**Failover routing** 只有兩種角色：**primary** 與 **secondary**。Primary 健康時只回答 primary；primary 被判定不健康時，改回答 secondary。Primary 必須有 health check（或是 alias 並開啟 evaluate target health）：沒有 health check 的記錄會被 Route 53 一律視為健康，primary 永遠不會被判定故障，也就永遠不會切換。經典用法是 **active-passive DR**：東京是 primary，新加坡（或一個放在 S3 的靜態維護頁面）是 secondary。

### Geolocation：依使用者所在地

**Geolocation routing** 依查詢來源的地理位置選擇記錄，可以設定到洲、國家，在美國（以及少數其他國家）還可以細到州或行政區。比對時越精確的位置越優先：州 > 國家 > 洲 > **default**。

Geolocation 最常見的錯誤是忘了建立 **default 記錄**：若只建了「日本」與「台灣」兩筆，來自其他國家的查詢找不到相符記錄，Route 53 會回覆「沒有答案」，那些使用者就連不上。適合的需求是「依國家顯示不同語言或價格」「依法規限制某些國家的使用者只能連到特定 Region」「依授權限制內容發佈範圍」。

### Geoproximity：依距離並可調整範圍

**Geoproximity routing** 也看地理位置，但概念是「連到最近的資源」，並可用 **bias（偏移值）** 擴大或縮小某個資源負責的地理範圍：正的 bias 讓它吸收更多周邊地區的流量，負的則縮小。資源位置可以用 AWS Region 或 Local Zone group 表示，也可以用經緯度表示（例如地端資料中心）。Bias 的範圍是 −99 到 +99，Route 53 以「實際距離 ×（1 − bias／100）」計算調整後的距離，例如 bias +50 會把距離當成一半。Geoproximity 記錄可以直接在 hosted zone 中建立，也可以用 **Route 53 Traffic Flow**（視覺化的流量政策編輯器）設定，後者能在地圖上看到調整 bias 後各資源負責的範圍。適合「新加坡環境容量較大，想讓它多分擔一些鄰近國家流量」這種需求。

### Multivalue answer：簡易的健康過濾

**Multivalue answer routing** 讓你建立多筆同名記錄，每筆可以各自有 health check。Route 53 每次最多回答 **8 筆健康的記錄**（沒有關聯 health check 的記錄一律視為健康）。和 simple 的差別在於：不健康的值會被排除。另外要記得 **multivalue answer 記錄不能是 alias**，值只能是寫死的 IP 等內容，所以不適合指向 IP 會變動的 ELB。它能提供基本的 DNS 層負載分散與可用性，但 **不是 load balancer 的替代品**：它沒有連線層級的分配、沒有 TLS 終止，也無法處理 connection draining。

### IP-based：依使用者的來源網段

**IP-based routing** 讓你上傳一組 **CIDR collection**，把已知的 IP 網段對應到不同的「位置」，再讓記錄依位置回答。比對依據是 resolver 的 IP，或在支援時由 resolver 帶上的用戶端網段資訊（EDNS Client Subnet）。適合「你比 AWS 更清楚使用者在哪」的情況：例如 Wanderly 與某家電信商合作，知道該電信商用戶的網段，想把他們導向與該電信商直連的 endpoint。

### 八種政策一覽

| Policy | 依據 | 可搭配 health check | 典型用途 |
|---|---|---|---|
| Simple | 無（全部回答） | 否 | 單一 endpoint |
| Weighted | 權重比例 | 是 | Canary、逐步搬遷 |
| Latency | AWS 量測的延遲 | 是 | 多 Region 效能優先 |
| Failover | primary 是否健康 | 是（primary 必須） | Active-passive DR |
| Geolocation | 洲／國家／州 | 是 | 在地化、法規、授權 |
| Geoproximity | 地理距離 + bias | 是 | 依距離分流並調整比例 |
| Multivalue answer | 隨機回答最多 8 筆健康值 | 是 | 無 LB 的簡易分散 |
| IP-based | 來源 CIDR | 是 | 依已知網段（ISP、企業網路）分流 |

## 9.7 Health check：Route 53 怎麼知道誰壞了

除了 simple 以外的政策都能和 health check 搭配，而 failover 少了它就完全沒有意義。

### 三種 health check

1. **監控 endpoint**：Route 53 從全球多個地點的 **health checker** 對一個 IP 或網域名稱發起 HTTP、HTTPS 或 TCP 檢查。可以設定 port、路徑（例如 `/health`）、檢查間隔（標準 30 秒或快速 10 秒）、**failure threshold**（連續失敗幾次才判定不健康，預設 3 次），以及 **string matching**（回應本文的前段必須包含某個字串）。HTTP／HTTPS 檢查要在時限內收到 2xx 或 3xx 狀態碼才算成功。當回報健康的 checker 比例超過約 18% 時，Route 53 就視該 endpoint 為健康，這是為了避免單一地點的網路問題誤判。
2. **Calculated health check**：把多個子 health check 組合起來，例如「三個子檢查中至少兩個健康才算健康」，或任一、全部。適合表達「整個 Region 的服務是否健康」這種由多個元件組成的判斷。
3. **監控 CloudWatch alarm**：health check 的狀態跟隨某個 CloudWatch alarm。這是 **私有資源** 唯一實用的做法：health checker 位於 Internet，連不到 private subnet 裡沒有 public IP 的資源，但你可以用 VPC 內部的監控（例如 Lambda 定期探測，或應用程式的錯誤率指標）建立 alarm，再讓 health check 監控這個 alarm。

### Evaluate target health

當記錄是 alias 且指向 ELB 等 AWS 資源時，可以開啟 **Evaluate target health**，不必另外建立 health check：例如 ALB 後面的所有 target 都不健康時，Route 53 就視這筆 alias 為不健康。這是多 Region ALB 架構中營運負擔最低的做法。

### 實務細節

- **放行 health checker**：endpoint 的 security group 或防火牆要允許 Route 53 health checker 的 IP 範圍（AWS 在公開的 `ip-ranges.json` 中以 `ROUTE53_HEALTHCHECKS` 標示）。只允許 CloudFront 或 ALB 來源的 web server，會讓 health check 永遠失敗。
- **健康檢查路徑要能匿名存取**：`/health` 若需要登入而回 401，就會被判定為不健康。
- **檢查該檢查的東西**：只檢查「web server 有回應」可能漏掉資料庫已經掛掉；但檢查太多下游，任何一個非關鍵元件故障都會觸發整個 Region 的 failover。常見做法是 health 頁面檢查關鍵依賴，再搭配 calculated health check 做判斷。
- **通知**：health check 的狀態以 CloudWatch 指標提供（位於 `us-east-1`），可以據此建立 alarm 並透過 SNS 通知。

### 全部都不健康時：fail open

如果一組記錄中的所有記錄都被判定為不健康，Route 53 不會回覆「沒有答案」，而是 **把它們當作全部健康** 來回答。這稱為 **fail open**：與其讓所有使用者都連不上，不如讓他們試試看。Failover 政策中，若 primary 與 secondary 都不健康，Route 53 會回答 primary。

## 9.8 組合政策：active-active 與 active-passive

現在回到 Wanderly 的完整需求：東京與新加坡同時服務（active-active），依延遲分流；每個 Region 內新版本先接 10%；兩個 Region 都不健康時顯示維護頁面。單一 routing policy 做不到，要把記錄 **組成一棵樹**：上層 alias 指向下層記錄。

```text
wanderly.com（Failover）
├─ ① PRIMARY：alias → app.wanderly.com（Latency）
│     ├─ ② 東京（ap-northeast-1）：alias → tokyo.wanderly.com（Weighted）
│     │      ├─ ③ blue  權重 90：alias → ALB-tokyo-blue   [evaluate target health]
│     │      └─ ③ green 權重 10：alias → ALB-tokyo-green  [evaluate target health]
│     └─ ② 新加坡（ap-southeast-1）：alias → ALB-singapore [evaluate target health]
└─ ④ SECONDARY：alias → S3 靜態網站（維護頁面，或經 CloudFront）
```

① 最上層是 failover：平時回答 primary，也就是整個 active-active 結構。② 第二層依延遲在兩個 Region 之間選擇；每筆 latency 記錄都 alias 到下一層並開啟 evaluate target health，若東京整棵子樹都不健康，所有使用者都會拿到新加坡。③ 東京內部用 weighted 做 canary，綠色版本出問題時，只要把權重改成 0。④ 兩個 Region 都不健康時，primary 整體不健康，Route 53 改回答維護頁面。

每一層只負責一種決策，測試與回滾都比較清楚。這種樹也可以用 **Traffic Flow** 以圖形化方式建立並保存版本，不過 Traffic Flow 的流量政策記錄另外按月收費。

### Active-active 與 active-passive 的取捨

| 比較 | Active-active | Active-passive |
|---|---|---|
| 平時 | 所有 Region 同時接流量 | 只有 primary 接流量 |
| Route 53 政策 | Latency、weighted、geolocation 等，搭配 health check | Failover |
| 故障時 | 健康的 Region 自動吸收全部流量，所以每個 Region 都要預留足夠容量 | 切到 secondary，secondary 要能在 RTO 內擴到足夠容量 |
| 資料層 | 需要多 Region 可寫入或明確的寫入路由 | 單一寫入點，複製到備援 |
| 成本 | 較高 | 較低（備援可以縮小規模） |

DNS 只是切換流量的一環。Secondary 能不能真正接手，還取決於資料是否已經複製、資料庫寫入點是否已經切換（第 34 章），以及用戶端快取了多久的舊答案。

## 9.9 Private hosted zone：只在 VPC 裡看得到的名字

第 8 章建立的 `aws.wanderly.internal` 就是一個 private hosted zone。它的規則如下：

- 必須 **關聯（associate）至少一個 VPC**，只有這些 VPC 裡的查詢（以及經由 Resolver inbound endpoint 進入這些 VPC 的查詢）能看到它的記錄。可以關聯多個 VPC，也可以跨 Region。
- VPC 必須開啟 `enableDnsSupport` 與 `enableDnsHostnames`（第 5 章）。
- 支援 simple、failover、multivalue answer、weighted、latency、geolocation 與 geoproximity，**不支援 IP-based routing**；要檢查私有資源的健康，要用 CloudWatch alarm 型的 health check（9.7 節）。

### Split-horizon DNS

**Split-horizon DNS** 是指同一個名稱，內部與外部查到不同答案。例如同時有 public hosted zone `wanderly.com` 與關聯到 VPC 的 private hosted zone `wanderly.com`：Internet 上的使用者查 `api.wanderly.com` 拿到 public ALB，VPC 內部查到的則是 internal ALB 的位址，內部流量不必繞出 Internet。

> [!warning] 常見誤解
> 「Private zone 找不到的記錄，Resolver 會自動去 public zone 找。」不會。當查詢名稱符合某個已關聯的 private hosted zone，而 zone 裡沒有這筆記錄時，Resolver 直接回答 **NXDOMAIN（名稱不存在）**，不會回頭查 public zone。所以採用 split-horizon 時，內部會用到的每個名稱都要在 private zone 裡建立，包括只是指向 public 資源的那些。

若多個 private hosted zone 的命名空間重疊（例如 `wanderly.internal` 與 `aws.wanderly.internal` 都關聯到同一個 VPC），Resolver 會選擇 **最精確相符** 的 zone。若同時還有 Resolver forwarding rule（第 8 章）也符合，forwarding rule 會優先於 private hosted zone。

### 跨帳號關聯 VPC

多帳號環境中，常見的設計是由網路或 shared services 帳號擁有 private hosted zone，再讓應用帳號的 VPC 解析它。Console 無法直接關聯其他帳號的 VPC，要用 CLI 或 API 完成兩步授權：

```bash
aws route53 create-vpc-association-authorization \
  --hosted-zone-id Z0123456789ABCDEFGHIJ \
  --vpc VPCRegion=ap-northeast-1,VPCId=vpc-0app2222

aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id Z0123456789ABCDEFGHIJ \
  --vpc VPCRegion=ap-northeast-1,VPCId=vpc-0app2222

aws route53 delete-vpc-association-authorization \
  --hosted-zone-id Z0123456789ABCDEFGHIJ \
  --vpc VPCRegion=ap-northeast-1,VPCId=vpc-0app2222
```

第一個指令在 **擁有 hosted zone 的帳號** 執行，授權某個外部 VPC 關聯；第二個指令在 **擁有 VPC 的帳號** 執行，真正完成關聯；第三個指令回到 zone 擁有者帳號刪除授權。刪除授權不會影響已完成的關聯，只是避免授權被重複使用，是建議的清理步驟。VPC 很多時，第 8 章提到的 Route 53 Profiles 可以把 private hosted zone 的關聯一併打包共享，減少逐一授權的工作。

## 9.10 DNSSEC：確認答案沒有被竄改

DNS 最初的設計沒有驗證機制：resolver 收到一個答案，無法確認它真的來自權威伺服器。攻擊者若能偽造回應並讓 resolver 快取（稱為 **cache poisoning，快取下毒**），就能把使用者導到假的網站。

**DNSSEC（DNS Security Extensions）** 用數位簽章解決這個問題：權威伺服器對記錄簽章，resolver 用公鑰驗證，而公鑰本身又由上一層網域簽章，一路串到 root，形成 **chain of trust（信任鏈）**。DNSSEC 保證的是 **答案的完整性與來源**，不加密查詢內容，也不能取代 TLS。

### 在 Route 53 啟用 DNSSEC signing

1. 為 public hosted zone 啟用 DNSSEC signing，並建立 **KSK（Key Signing Key，金鑰簽署金鑰）**。KSK 以你在 KMS 中的 **customer managed key** 為基礎，這把 KMS key 必須是 **非對稱、`ECC_NIST_P256` 規格，而且位於 `us-east-1`**。
2. Route 53 自動管理 **ZSK（Zone Signing Key，區域簽署金鑰）**，用它對記錄簽章；你負責的是 KSK。
3. **建立信任鏈**：把 KSK 對應的 **DS 記錄** 加到父網域。網域在 Route 53 註冊的話，在 Registered domains 中加入；在別家註冊的話，到該網域商後台加入。少了這一步，簽章存在但沒有人能驗證。
4. 為 DNSSEC 相關的 CloudWatch 指標建立 alarm（例如 KSK 需要處理的狀態），因為簽章出錯時，啟用驗證的 resolver 會直接拒絕回答，整個網域等於下線。

Private hosted zone 不支援 DNSSEC signing。反方向，VPC 內的 Route 53 Resolver 可以啟用 **DNSSEC validation**，驗證它查到的 public 答案。

> [!tip] 考試提示
> 題目出現「防止 DNS spoofing／cache poisoning」「驗證 DNS 回應的真實性」→ DNSSEC。看到 DNSSEC 就聯想「KMS 非對稱 key、`us-east-1`、DS 記錄加到父網域」這三個關鍵字。

## 9.11 比較與選型

### Routing policy 選擇流程

```text
同一個名稱只有一個 endpoint？
├─ 是 → Simple（AWS 資源用 alias；需要跟隨健康狀態則開 evaluate target health）
└─ 否 → 主要目標是什麼？
     ├─ 主備切換（DR） ───────────────→ Failover（primary 必須有 health check）
     ├─ 依比例分流（canary、搬遷） ─────→ Weighted
     ├─ 效能：連到最快的 Region ────────→ Latency
     ├─ 依國家／洲（法規、語言、授權） ──→ Geolocation（一定要有 default）
     ├─ 依距離並想調整各區範圍 ─────────→ Geoproximity（bias）
     ├─ 依已知的來源網段 ───────────────→ IP-based（CIDR collection）
     └─ 沒有 LB，只想回答多個健康 IP ───→ Multivalue answer（最多 8 筆）
需求同時有兩種以上 → 用 alias 把政策疊成樹，每層一種決策
```

### DNS 層 vs 其他層的流量管理

| 需求 | Route 53 | 其他選擇 |
|---|---|---|
| 跨 Region 選擇 endpoint | 可以，但受 DNS 快取影響 | Global Accelerator：固定 anycast IP、網路層快速 failover（第 11 章） |
| 單一 Region 內分散請求 | 不適合 | ELB（第 10 章） |
| 快取靜態內容、靠近使用者 | 不提供 | CloudFront（第 11 章） |
| 秒級、不受用戶端快取影響的切換 | 做不到 | Global Accelerator |
| 依 HTTP 路徑或標頭分流 | 做不到 | ALB、CloudFront |

## 9.12 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| zone apex／root domain 指向 ALB、CloudFront、S3 website | Alias A／AAAA 記錄 |
| 指向 AWS 資源且要降低 DNS 查詢費用 | Alias（查詢免費） |
| 10% 流量給新版本、逐步搬遷 | Weighted |
| 全球使用者連到延遲最低的 Region | Latency |
| 主 Region 故障時切到備援、靜態維護頁面 | Failover + health check（secondary 可 alias 到 S3 website） |
| 依國家提供不同內容、法規限制國家 | Geolocation + default 記錄 |
| 讓某個 Region 多吸收周邊流量 | Geoproximity + bias |
| 不用 LB，DNS 回答多個健康 IP | Multivalue answer |
| 依 ISP 或企業網段分流 | IP-based routing |
| Health check 私有 subnet 的資源 | CloudWatch alarm 型 health check |
| 多個元件共同決定是否健康 | Calculated health check |
| Alias 指向 ALB，不想另建 health check | Evaluate target health |
| 改記錄後很久才生效 | TTL；應提前降低 TTL |
| 防止 DNS spoofing | DNSSEC（KMS 非對稱 key 在 us-east-1，DS 記錄） |
| 其他帳號的 VPC 要解析 private hosted zone | create-vpc-association-authorization + associate-vpc-with-hosted-zone |
| 內外部同名不同答案 | Split-horizon：public + private hosted zone |

**常見陷阱**：

1. 在 zone apex 建 CNAME：DNS 協定不允許，要用 alias。
2. 以為 simple routing 會排除不健康的 IP：simple 不支援 health check，要用 multivalue answer 或 failover。
3. Geolocation 沒有 default 記錄：未對應位置的使用者拿不到答案。
4. 以為 latency routing 等於地理最近，或能保證資料留在某國：要法規邊界就用 geolocation，再搭配應用層控制。
5. 以為 Route 53 health checker 能直接檢查 private IP：它在 Internet 上，私有資源要用 CloudWatch alarm。
6. 以為 weighted 的比例是精確的請求比例：它是 DNS 回答的機率，受 resolver 快取影響。
7. 以為 Route 53 是 load balancer：它只回答 DNS，不轉送流量，也沒有 connection draining。
8. 以為 private hosted zone 找不到記錄時會回頭查 public zone：會直接回 NXDOMAIN。

## 9.13 SAP 加深：DNS 層的韌性與治理

### Control plane 與 data plane

第 2 章介紹過 control plane（建立與修改資源的 API）與 data plane（實際提供服務的部分）。Route 53 的 data plane（回答 DNS 查詢、執行 health check）分散在全球，可用性非常高；但 **control plane（建立、修改記錄與 health check 的 API）集中在 `us-east-1`**。

這對 DR 設計有直接影響：如果你的 failover 計畫是「災難發生時，由工程師或腳本呼叫 API 把記錄改到備援 Region」，那它依賴的是 control plane，而大範圍事故時 control plane 可能受影響或被大量請求擠爆。較穩健的做法是讓 failover **只依賴 data plane**：事先建好 failover 或 latency 記錄與 health check，災難時由 health check 狀態自動決定答案。

### Route 53 Application Recovery Controller

若需要「人工決定、但不依賴 control plane」的切換，可以使用 **Route 53 Application Recovery Controller（ARC）** 的 **routing control**：它本質上是一個由你開關的 health check，狀態存放在跨 5 個 Region 的高可用叢集中，透過叢集的 data plane endpoint 切換，再由 Route 53 的 failover 記錄依其狀態回答。配合 **safety rule** 可以防止誤操作（例如「至少要有一個 Region 是開啟的」）。ARC 也提供 **zonal shift**，讓支援的 load balancer 暫時避開單一 AZ 的流量。這類設計常出現在 SAP 的業務持續題目中，第 34 章會再結合 DR 策略說明。

### 多帳號 DNS 治理

企業規模的常見做法：

- **Public DNS**：apex 網域的 hosted zone 放在網路或 DNS 專用帳號，各產品的子網域透過 NS 委派給產品帳號自己的 hosted zone。這樣產品團隊能自行管理記錄，又不能動到 apex。
- **Private DNS**：private hosted zone 集中在 shared services 帳號，以跨帳號關聯或 Route 53 Profiles 分發到應用 VPC；搭配第 8 章的 Resolver endpoint 與共享 rule，讓地端也能解析。
- **稽核與防護**：public hosted zone 可以啟用 **query logging**（送到 `us-east-1` 的 CloudWatch Logs），VPC 內則用 Resolver query logging；要阻擋 VPC 內的機器解析惡意網域，可以用 **Route 53 Resolver DNS Firewall**（第 16 章）。

### 長 TTL 與 Global Accelerator 的取捨

DNS failover 的實際切換時間大約是「health check 偵測時間（間隔 × failure threshold）+ TTL + 用戶端行為」。若要求切換在數十秒內完成、且不能依賴用戶端遵守 TTL，DNS 不是正確的工具，應考慮 Global Accelerator 這類以固定 anycast IP 在網路層切換的方案（第 11 章）。

## 本章重點整理

- Route 53 有四個獨立角色：網域註冊、權威 DNS（hosted zone）、health check，以及 VPC 內的 Resolver；它只回答 DNS，不轉送應用流量。
- Public hosted zone 回答 Internet 查詢，private hosted zone 只回答已關聯 VPC 的查詢；子網域可以用 NS 記錄委派給另一個 hosted zone。
- TTL 決定答案的快取時間；要快速切換，必須至少提前一個舊 TTL 先調低 TTL。
- Zone apex 不能放 CNAME；alias 記錄可以放在 apex、指向 ELB、CloudFront、S3 website、API Gateway 等 AWS 資源，查詢免費且自動跟隨 IP 變化。
- Simple 不支援 health check；multivalue answer 最多回答 8 筆健康記錄，但不是 load balancer。
- Weighted 依權重比例回答，適合 canary 與逐步搬遷；比例是 DNS 回答的機率，不是精確的請求比例。
- Latency 依 AWS 量測的延遲選 Region；geolocation 依洲、國家或州選擇，必須建立 default 記錄；geoproximity 依距離並以 bias 調整範圍；IP-based 依 CIDR collection 分流。
- Failover 政策做 active-passive，primary 必須有 health check 或 evaluate target health；全部記錄不健康時 Route 53 會 fail open。
- Health check 有三種：監控 endpoint、calculated、監控 CloudWatch alarm；私有資源只能透過 CloudWatch alarm 間接檢查。
- Endpoint health check 需要放行 Route 53 health checker 的 IP 範圍，且檢查路徑要能匿名存取並回 2xx 或 3xx。
- 複雜需求用 alias 把多種政策組成樹，每層只做一種決策，例如 failover → latency → weighted。
- Private hosted zone 需要 VPC 開啟 enableDnsSupport 與 enableDnsHostnames；名稱符合 private zone 但找不到記錄時直接回 NXDOMAIN，不會回查 public zone。
- 跨帳號關聯 private hosted zone 要用 CLI／API：zone 擁有者建立授權、VPC 擁有者執行關聯，最後刪除授權。
- DNSSEC signing 驗證答案完整性：KSK 使用 `us-east-1` 的非對稱 `ECC_NIST_P256` customer managed KMS key，ZSK 由 Route 53 管理，並要在父網域加入 DS 記錄。
- Route 53 的 control plane 在 `us-east-1`；DR 的 failover 應依賴 health check 或 ARC routing control 這類 data plane 機制，而不是災難當下呼叫 API 修改記錄。

## 本章練習題

### 練習 9-1｜SAA｜單選｜Zone apex 指向 ALB

Wanderly 已經把 `wanderly.com` 的 DNS 代管搬到 Route 53。網站位於一個 Application Load Balancer 後面，ALB 的 IP 會隨時間變動。團隊希望使用者輸入 `wanderly.com`（不含 `www`）時直接連到 ALB，不需要額外的轉址伺服器，且 DNS 查詢成本越低越好。

應建立哪一種記錄？

- A. 在 `wanderly.com` 建立 CNAME 記錄，值為 ALB 的 DNS 名稱
- B. 查出 ALB 目前的 IP，在 `wanderly.com` 建立含這些 IP 的 A 記錄，並把 TTL 設為 60 秒
- C. 在 `wanderly.com` 建立 alias A 記錄，目標選擇該 ALB
- D. 在 `wanderly.com` 建立 NS 記錄，把 apex 委派給 ALB

> [!answer]- 答案：C
> **A ✗** Zone apex 一定有 NS 與 SOA 記錄，而 DNS 協定規定 CNAME 不能和同名的其他記錄共存，所以 apex 不能建立 CNAME。
>
> **B ✗** ALB 的 IP 會變動，寫死 IP 遲早會指向不屬於你的位址；縮短 TTL 也無法解決 IP 改變的問題。
>
> **C ✓** Alias 是 Route 53 的擴充記錄，可以放在 apex，回答時即時解析 ALB 目前的 IP 並以 A 記錄回給 resolver；指向 AWS 資源的 alias 查詢不收費。
>
> **D ✗** NS 記錄用來把子網域委派給另一組 name server；ALB 不是 DNS server，無法回答委派過去的查詢。
>
> **考點**：SAA-3.4、SAA-4.4｜Alias 記錄與 zone apex

### 練習 9-2｜SAA｜單選｜DNS 代管搬家不中斷

Wanderly 的網域在一家本地網域商註冊，DNS 也由該網域商代管，裡面有網站、郵件（MX）與多筆 TXT 驗證記錄，NS 記錄的 TTL 是 2 天。公司要把 DNS 代管搬到 Route 53，但網域註冊暫時不轉移，搬遷期間網站與郵件都不能中斷。

哪個步驟順序最合適？

- A. 在 Route 53 建立 public hosted zone 並建立所有現有記錄；在原 DNS 服務商調低 NS 記錄的 TTL 並等待舊 TTL 過期；再到網域商把 name server 改成 Route 53 的 4 台 name server，確認生效後才停用舊服務
- B. 先到網域商把 name server 改成 Route 53，再依使用者回報逐一補上缺少的記錄
- C. 先把網域註冊轉移到 Route 53，轉移完成後 Route 53 會自動複製原服務商的所有記錄
- D. 在 Route 53 建立 private hosted zone 並複製所有記錄，再把它關聯到網站所在的 VPC

> [!answer]- 答案：A
> **A ✓** 先在 Route 53 準備好完整的記錄，再縮短 NS 的 TTL，讓之後的切換能較快生效；改 name server 後，新舊兩邊回答的內容一致，不論 resolver 快取了哪一邊都能正常解析，確認全面生效後才關閉舊服務。
>
> **B ✗** 先改 NS 再補記錄，會讓查詢在記錄補齊前得到 NXDOMAIN，網站與郵件都會中斷。
>
> **C ✗** 網域註冊轉移和 DNS 代管是兩件事，轉移註冊不會自動複製原服務商的 DNS 記錄；而且題目要求暫不轉移註冊。
>
> **D ✗** Private hosted zone 只回答已關聯 VPC 內的查詢，Internet 上的使用者與郵件伺服器都查不到。
>
> **考點**：SAA-2.2｜DNS 代管遷移與 TTL

### 練習 9-3｜SAA｜單選｜新版本先接 10% 流量

Wanderly 在東京 Region 準備了新版本的訂房網站，部署在一個新的 ALB 後面，舊版本仍在原本的 ALB。產品團隊希望先讓約 10% 的使用者使用新版本，觀察一天後再逐步提高比例，有問題時能迅速把新版本的流量降為零，而且不想修改應用程式。

最合適的 Route 53 設定是什麼？

- A. 建立兩筆 latency 記錄，把新版本 ALB 的 TTL 設得比較短
- B. 建立 failover 記錄，新版本設為 primary、舊版本設為 secondary
- C. 建立一筆 simple 記錄，同時包含兩個 ALB 的 IP 位址
- D. 建立兩筆同名的 weighted alias 記錄，分別指向兩個 ALB，權重設為 90 與 10；要回滾時把新版本的權重改為 0

> [!answer]- 答案：D
> **A ✗** Latency routing 依 AWS 量測的延遲選擇 Region，兩個 ALB 都在東京時無法控制比例；TTL 長短也不會改變分配比例。
>
> **B ✗** Failover 平時只回答 primary，會讓 100% 流量直接進到新版本，與「先 10%」相反。
>
> **C ✗** Simple 記錄會把所有值都回答給用戶端，比例不可控，也不支援 health check；ALB 的 IP 也會變動，不適合寫死。
>
> **D ✓** Weighted routing 依權重比例回答，90／10 約讓 10% 的 DNS 回答指向新版本，之後逐步調整權重即可；權重改為 0 就不再回答新版本。實際請求比例會受 resolver 快取影響而只是大致接近 10%。
>
> **考點**：SAA-2.1、SAA-3.4｜Weighted routing 與 canary 發佈

### 練習 9-4｜SAA｜單選｜多 Region 效能優先

Wanderly 在東京（ap-northeast-1）與新加坡（ap-southeast-1）各有一套完整的網站，前面各有一個 ALB，資料已能在兩地同步。使用者遍布台灣、日本與東南亞。團隊希望每位使用者通常連到回應速度最快的那個 Region，且某個 Region 的 ALB 沒有健康的 target 時，自動只回答另一個 Region。

最合適的設定是什麼？

- A. 建立兩筆 geolocation 記錄，日本與台灣指向東京，其他國家指向新加坡
- B. 建立兩筆 latency alias 記錄，分別標示東京與新加坡 Region 並指向各自的 ALB，並開啟 evaluate target health
- C. 建立兩筆 weighted 記錄，權重各 50
- D. 建立一筆 multivalue answer 記錄，包含兩個 ALB 的 DNS 名稱

> [!answer]- 答案：B
> **A ✗** Geolocation 依國家分流，不一定對應最快的路徑，例如網路條件改變時無法跟著調整；它適合法規或在地化需求，而不是效能優先。
>
> **B ✓** Latency routing 依 AWS 量測的延遲，為每個查詢回答延遲較低的 Region。Alias 指向 ALB 並開啟 evaluate target health，當某個 ALB 沒有健康 target 時，Route 53 只回答另一個 Region，不需另建 health check。
>
> **C ✗** Weighted 50／50 只是平均分配，不考慮使用者到哪個 Region 比較快。
>
> **D ✗** Multivalue answer 記錄不能是 alias，而 ALB 的 IP 會變動、無法寫死成記錄值；它也不會依延遲選擇。
>
> **考點**：SAA-3.4、SAA-2.2｜Latency routing 與 evaluate target health

### 練習 9-5｜SAA｜單選｜依國家分流與預設記錄

Wanderly 要進入歐洲市場。法務部門要求來自歐盟國家的使用者必須連到法蘭克福 Region 的環境，以符合當地個資規範；日本使用者連到東京的日文版網站；其他所有國家的使用者連到東京的國際版網站。上線前測試發現，某些國家的使用者完全解析不到網站。

最合適的設計是什麼？

- A. 為每個歐盟國家各建立一筆 geolocation 記錄指向法蘭克福、日本（國家）指向日文版，並建立一筆 default 記錄指向國際版
- B. 建立 latency 記錄，分別標示法蘭克福與東京 Region
- C. 建立 geoproximity 記錄，並把法蘭克福的 bias 設為最大值
- D. 只建立歐洲與日本兩筆 geolocation 記錄，Route 53 會自動把其他國家導向最近的記錄

> [!answer]- 答案：A
> **A ✓** Geolocation 依查詢來源位置回答，可以精確到國家。法規只涵蓋歐盟國家，所以要逐一以國家設定，而不是用整個「歐洲」洲（那會把英國、瑞士等非歐盟國家也導到法蘭克福）。少了 default 記錄時，不符合任何已設定位置的查詢會得不到答案，這正是測試中某些國家解析不到的原因；加上 default 記錄後，其他國家都會拿到國際版。應用層也應搭配其他控制，因為 DNS 判斷位置依據的是 resolver（或 EDNS Client Subnet）的 IP，不是使用者本人。
>
> **B ✗** Latency routing 依延遲選擇，歐洲使用者在網路狀況改變時可能被導向東京，無法滿足「必須連到法蘭克福」的法規需求。
>
> **C ✗** Geoproximity 依距離與 bias 分流，邊界是相對的，不是以國家為準，無法準確滿足法規要求的國家邊界。
>
> **D ✗** Geolocation 沒有「自動找最近」的行為，沒有 default 記錄時，不符合位置的查詢會得不到答案。
>
> **考點**：SAA-1.2、SAA-3.4｜Geolocation 與 default 記錄

### 練習 9-6｜SAA｜單選｜故障時顯示維護頁面

Wanderly 的網站只部署在東京 Region 的 ALB 後面。管理層要求：當整個網站不可用時，使用者至少要看到一個「系統維護中」的靜態頁面，而不是瀏覽器錯誤；維護頁面的成本要極低，並且自動切換。

最合適的做法是什麼？

- A. 在 ALB 設定 fixed response 規則，ALB 故障時回傳維護頁面
- B. 建立兩筆 weighted 記錄，ALB 權重 99、維護頁面權重 1
- C. 建立 failover 記錄：primary alias 到 ALB 並開啟 evaluate target health，secondary alias 到一個設定為靜態網站的 S3 bucket，內容是維護頁面
- D. 在另一個 Region 部署一套完整的網站，並以 simple 記錄同時回答兩個 Region

> [!answer]- 答案：C
> **A ✗** Fixed response 由 ALB 本身產生；如果故障的是 ALB 所在的整個環境或 Region，ALB 自己也無法回應。
>
> **B ✗** Weighted 會讓約 1% 的使用者平時就看到維護頁面，故障時也不會自動把全部流量切過去。
>
> **C ✓** Failover routing 平時只回答 primary；當 ALB 沒有健康的 target 時，Route 53 改回答 secondary。S3 靜態網站可以作為 alias 目標（bucket 名稱要與記錄名稱相同），成本極低且與 ALB 環境無關。若需要 HTTPS，可以在 S3 前面放 CloudFront 再 alias 到 CloudFront。
>
> **D ✗** 部署完整的第二套網站成本高，超出「極低成本的維護頁面」需求；simple 記錄也不支援 health check，無法自動排除故障的 Region。
>
> **考點**：SAA-2.2、SAA-4.1｜Failover routing 與 S3 靜態網站

### 練習 9-7｜SAA｜單選｜沒有 Load Balancer 的健康過濾

一個內部工具服務由 4 台 EC2 組成，每台都有 Elastic IP，直接以 HTTPS 對外。團隊不想為這個低流量服務增加 load balancer 的成本，但希望 DNS 只回答健康的機器，讓用戶端在其中隨機選擇。目前使用一筆 simple 記錄包含 4 個 IP，有一台故障時仍會被回答。

應如何修改？

- A. 為 simple 記錄設定 health check，Route 53 會自動移除不健康的值
- B. 改用 latency 記錄，並把 4 台機器標示為不同的 Region
- C. 改用 failover 記錄，把 4 台設為 4 個 primary
- D. 改用 4 筆 multivalue answer 記錄，每筆一個 IP 並各自關聯一個 health check

> [!answer]- 答案：D
> **A ✗** Simple routing 不支援 health check，一筆記錄中的多個值無法各自判斷健康。
>
> **B ✗** Latency 記錄依 Region 延遲選擇，4 台機器都在同一個 Region，標示成不同 Region 是錯誤的設定，也不會依健康狀態過濾。
>
> **C ✗** Failover 只有一個 primary 與一個 secondary，無法表達 4 台平行的機器。
>
> **D ✓** Multivalue answer 讓每筆記錄各自關聯 health check，每次最多回答 8 筆健康的值，用戶端從中選擇。它提供 DNS 層的簡易可用性，雖然不是 load balancer 的替代品，但符合這個低流量、不想用 LB 的需求。
>
> **考點**：SAA-2.2、SAA-4.4｜Multivalue answer 與 health check

### 練習 9-8｜SAA｜選兩項｜Private hosted zone 解析失敗

小林在自建 VPC 中建立了 private hosted zone `aws.wanderly.internal`，新增了 `orders-db.aws.wanderly.internal` 的記錄。但 VPC 內的 EC2 查詢這個名稱時，得到的是 NXDOMAIN 或來自 Internet 的錯誤回應。EC2 使用 Amazon-provided DNS，security group 與 NACL 都沒有阻擋 DNS。

應檢查哪兩項設定？（選兩項）

- A. Private hosted zone 是否已關聯到這個 VPC
- B. VPC 的 `enableDnsSupport` 與 `enableDnsHostnames` 是否都已開啟
- C. 是否為 private hosted zone 啟用了 DNSSEC signing
- D. VPC 是否附加了 Internet Gateway
- E. 記錄是否設定了 health check

> [!answer]- 答案：A、B
> **A ✓** Private hosted zone 只回答已關聯 VPC 內的查詢；建立 zone 時若沒有關聯這個 VPC，Resolver 不會使用它，查詢會被當成一般 public 名稱處理。
>
> **B ✓** 使用 private hosted zone 需要 VPC 同時開啟 `enableDnsSupport` 與 `enableDnsHostnames`；自建 VPC 預設 `enableDnsHostnames` 是關閉的。
>
> **C ✗** Private hosted zone 不支援 DNSSEC signing，DNSSEC 也不是解析 private zone 的必要條件。
>
> **D ✗** Private hosted zone 的解析由 VPC 內的 Resolver 完成，不需要 Internet Gateway。
>
> **E ✗** 沒有 health check 的記錄一樣會被回答；health check 只在 routing policy 需要判斷健康時才相關。
>
> **考點**：SAA-3.4｜Private hosted zone 的 VPC 關聯與 DNS 屬性

### 練習 9-9｜SAA｜單選｜檢查私有 subnet 的資源

Wanderly 的內部 API 位於 private subnet，前面是一個 internal ALB，沒有 public IP。Private hosted zone 中有兩筆 failover 記錄分別指向東京與新加坡的 internal ALB。團隊希望東京 API 的錯誤率超過門檻時自動切換到新加坡，並發現建立指向 internal ALB IP 的 endpoint health check 總是顯示不健康。

最合適的做法是什麼？

- A. 為 internal ALB 加上 Elastic IP，讓 Route 53 health checker 能從 Internet 連入
- B. 以 ALB 的 5xx 錯誤率或自訂指標建立 CloudWatch alarm，再建立監控該 alarm 的 Route 53 health check，並關聯到 primary 記錄
- C. 把 failover 記錄的 TTL 改為 0，讓用戶端每次都重新查詢
- D. 在 internal ALB 的 security group 中允許 Route 53 health checker 的 IP 範圍

> [!answer]- 答案：B
> **A ✗** Internal ALB 無法加上 Elastic IP；把內部 API 暴露到 Internet 也違反原本的私有設計。
>
> **B ✓** Route 53 health checker 位於 Internet，連不到私有位址。以 CloudWatch alarm 監控錯誤率或其他指標，再讓 health check 跟隨 alarm 狀態，是檢查私有資源的標準做法，而且能直接表達「錯誤率超過門檻」的條件。
>
> **C ✗** TTL 只影響快取時間，不會讓 Route 53 知道東京的 API 已經不健康。
>
> **D ✗** 問題不在 security group，而是 health checker 根本沒有通往私有位址的路徑；放行 IP 範圍也無法讓 Internet 上的 checker 到達 private subnet。
>
> **考點**：SAA-2.2｜CloudWatch alarm 型 health check

### 練習 9-10｜SAA｜選兩項｜Health check 誤判不健康

Wanderly 的網站 EC2 位於 public subnet，以 HTTPS 提供服務，使用者都能正常存取。團隊為它建立了 Route 53 endpoint health check，檢查路徑為 `/admin/status`，但 health check 一直顯示不健康，導致 failover 記錄把流量切到備援環境。EC2 的 security group 只允許公司辦公室的 IP 與 CloudFront 的來源範圍連入 443。`/admin/status` 需要登入，未登入時回傳 401。

哪兩個修正最合適？（選兩項）

- A. 在 security group 中允許 Route 53 health checker 的 IP 範圍連入 443
- B. 把 health check 的 failure threshold 調到最大值，讓它比較不容易判定不健康
- C. 把 health check 改成 TCP 檢查 port 22
- D. 改用 calculated health check，並把唯一的子檢查反向
- E. 提供一個不需登入、回傳 2xx 的健康檢查路徑（例如 `/health`），並讓 health check 使用它

> [!answer]- 答案：A、E
> **A ✓** Route 53 health checker 來自 AWS 公布的特定 IP 範圍，security group 沒有放行時，它們的連線會被丟棄，health check 就永遠失敗。
>
> **B ✗** 調高 failure threshold 只會延後判定時間；連線一直被擋、路徑一直回 401，最終仍會判定不健康，也讓真正的故障更晚被發現。
>
> **C ✗** Port 22 是 SSH，檢查它無法反映網站是否正常；開放 SSH 給外部也增加攻擊面。
>
> **D ✗** 把檢查結果反向會讓真正故障時顯示健康，完全失去 health check 的意義。
>
> **E ✓** HTTP／HTTPS health check 需要收到 2xx 或 3xx 才算成功，需要登入的路徑會回 401。提供一個匿名、輕量並能反映關鍵依賴的健康檢查路徑，才能得到正確判斷。
>
> **考點**：SAA-2.2、SAA-1.2｜Health check 的網路放行與檢查路徑

### 練習 9-11｜SAP｜單選｜跨帳號關聯 private hosted zone

Wanderly 的 shared services 帳號擁有 private hosted zone `aws.wanderly.internal`。新成立的資料分析團隊在另一個帳號建立了 VPC，需要解析這個 zone 中的記錄。網路團隊在 console 中嘗試把該 VPC 加入 hosted zone，但下拉選單中看不到其他帳號的 VPC。公司不想複製 zone 或建立額外的 DNS server。

應如何完成？

- A. 在 shared services 帳號以 CLI 執行 `create-vpc-association-authorization`，在分析團隊帳號執行 `associate-vpc-with-hosted-zone`，完成後在 shared services 帳號刪除授權
- B. 在分析團隊帳號建立同名的 private hosted zone，並定期從 shared services 帳號同步記錄
- C. 在兩個 VPC 之間建立 VPC peering，peering 建立後 private hosted zone 會自動對另一個 VPC 生效
- D. 把 private hosted zone 改成 public hosted zone，讓所有帳號都能查詢

> [!answer]- 答案：A
> **A ✓** 跨帳號關聯需要兩步：zone 擁有者授權特定 VPC，VPC 擁有者再執行關聯。這只能用 CLI、SDK 或 API 完成，console 不支援。關聯完成後刪除授權是建議的清理步驟，不影響已建立的關聯。
>
> **B ✗** 複製 zone 會產生兩份需要同步的資料，容易不一致，題目也明確不想複製。
>
> **C ✗** VPC peering 只提供網路連通，不會讓 private hosted zone 自動對另一個 VPC 生效；private zone 一定要明確關聯 VPC。
>
> **D ✗** 改成 public hosted zone 會把內部名稱與私有位址公開到 Internet。
>
> **考點**：SAP-1.4、SAP-1.1｜Private hosted zone 跨帳號 VPC 關聯

### 練習 9-12｜SAP｜單選｜多層流量政策

Wanderly 在東京與新加坡採 active-active 架構，使用者應依延遲連到較快的 Region。東京 Region 內，新版本要先接該 Region 約 20% 的流量。兩個 Region 都不健康時，所有使用者要看到放在 CloudFront 上的靜態維護頁面。團隊希望每層的設定都容易理解與回滾，且不要自行撰寫切換程式。

哪個設計最合適？

- A. 在 `wanderly.com` 建立一筆同時啟用 latency、weighted 與 failover 的記錄
- B. 建立三筆 weighted 記錄：東京舊版 40、東京新版 10、新加坡 50，並把 TTL 設為 1 秒
- C. 在東京與新加坡的 ALB 前面各加一個 Global Accelerator，再用 simple 記錄同時回答兩個 accelerator
- D. 以 alias 組成記錄樹：最上層 failover（primary alias 到 latency 記錄、secondary alias 到 CloudFront）；latency 記錄分別指向東京的 weighted 記錄與新加坡 ALB；東京的 weighted 記錄以 80／20 指向新舊 ALB；每層都開啟 evaluate target health

> [!answer]- 答案：D
> **A ✗** 一筆記錄只能有一種 routing policy，無法同時啟用三種。
>
> **B ✗** 固定權重不考慮使用者到哪個 Region 較快，不符合 latency 需求；TTL 設得極短不會產生延遲選擇，也無法表達「兩個 Region 都不健康時改回答維護頁面」。
>
> **C ✗** Simple 記錄不依延遲選擇、也不支援 health check；同時回答兩個 accelerator 無法滿足延遲分流、Region 內 20% 分流與維護頁面需求。
>
> **D ✓** 用 alias 把政策疊成樹，每層只做一種決策：failover 決定是否顯示維護頁面，latency 決定 Region，weighted 決定東京內部的新舊版本比例。Evaluate target health 讓健康狀態由下往上傳遞，整個切換由 Route 53 自動完成。
>
> **考點**：SAP-1.3、SAP-2.1｜以 alias 組合多層 routing policy

### 練習 9-13｜SAP｜單選｜不依賴 control plane 的 DR 切換

一家公司以 Route 53 管理全球入口，主要環境在 `us-east-1`，備援在 `us-west-2`。現行 DR runbook 是：災難發生時，由值班工程師執行腳本呼叫 Route 53 API，把 A 記錄改指向備援 Region。稽核指出這個流程在大範圍事故中可能失效。公司希望保留「由人決定何時切換」的能力，同時讓切換只依賴高可用的 data plane。

最合適的改善是什麼？

- A. 把腳本改為在 `us-west-2` 的 EC2 上執行，就不會受到 `us-east-1` 事故影響
- B. 把記錄的 TTL 從 300 秒降為 10 秒，讓修改記錄後更快生效
- C. 事先建立 failover 記錄，並使用 Route 53 Application Recovery Controller 的 routing control 作為 health check；災難時透過 ARC 叢集的 data plane endpoint 切換 routing control 狀態，並以 safety rule 防止兩邊同時關閉
- D. 改為 weighted 記錄，災難時把 `us-east-1` 記錄的權重改為 0

> [!answer]- 答案：C
> **A ✗** 腳本在哪裡執行並不重要，它呼叫的仍是 Route 53 的 control plane API，而 control plane 集中在 `us-east-1`。
>
> **B ✗** 縮短 TTL 只讓修改後的記錄較快生效，修改這個動作仍依賴 control plane。
>
> **C ✓** Routing control 本質上是一個由人開關的 health check，狀態存放在跨多個 Region 的 ARC 叢集，透過 data plane endpoint 切換；failover 記錄事先建好，切換時不需要修改任何 Route 53 記錄。Safety rule 可以防止誤把所有 Region 都關閉。
>
> **D ✗** 修改權重同樣是呼叫 control plane API 修改記錄，與原本的流程有相同風險。
>
> **考點**：SAP-2.2、SAP-1.3｜Route 53 data plane 與 ARC routing control

### 練習 9-14｜SAP｜單選｜依合作電信商網段分流

Wanderly 與一家大型電信商合作，該電信商的行動用戶使用一組已知的 IP 網段，而 Wanderly 在電信商的機房附近部署了一套專屬的前端環境，並透過專線連回 AWS。公司希望來自這些網段的使用者連到專屬環境，其他使用者照常依延遲連到東京或新加坡。電信商會定期提供更新後的網段清單。

最合適的做法是什麼？

- A. 使用 geolocation routing，把電信商所在的國家指向專屬環境
- B. 建立 CIDR collection 存放電信商的網段，以 IP-based routing 把這些網段指向專屬環境，其他位置的記錄 alias 到既有的 latency 記錄
- C. 使用 geoproximity routing，把專屬環境的 bias 設為最大值
- D. 在 ALB 上依來源 IP 設定 listener rule，把電信商用戶轉送到專屬環境

> [!answer]- 答案：B
> **A ✗** 以國家分流會把該國所有使用者都導到專屬環境，而不只是這家電信商的用戶。
>
> **B ✓** IP-based routing 讓你依已知的來源網段決定答案，正適合「你比 AWS 更清楚使用者網路」的情境。網段放在 CIDR collection 中，電信商更新清單時只要更新 collection；預設位置的記錄可以 alias 到既有的 latency 記錄，其他使用者的行為不變。
>
> **C ✗** Geoproximity 依地理距離與 bias 分流，無法精準對應某家電信商的網段，bias 調大還會吸走附近其他使用者。
>
> **D ✗** ALB listener rule 是在流量已經到達 AWS 的 ALB 之後才判斷，使用者仍要先連到 ALB，無法讓他們一開始就直接連到電信商機房附近的專屬環境。
>
> **考點**：SAP-3.3、SAP-1.1｜IP-based routing 與 CIDR collection

### 練習 9-15｜SAP｜選兩項｜啟用 DNSSEC signing

一家旅遊支付公司因合規要求，必須為其 public 網域 `pay.example.com` 啟用 DNSSEC，以防止 DNS 回應被偽造。網域的 DNS 代管在 Route 53，網域註冊則在另一家網域商。資安團隊要求簽署金鑰由公司自己的 KMS key 控制，並在簽章異常時收到通知。

哪兩個步驟是必要的？（選兩項）

- A. 在 `ap-northeast-1` 建立一把對稱的 KMS customer managed key 作為 KSK 的基礎
- B. 在 `us-east-1` 建立一把非對稱、`ECC_NIST_P256` 規格的 KMS customer managed key，用它在 Route 53 為 hosted zone 建立 KSK 並啟用 DNSSEC signing
- C. 自行產生 ZSK 並每月手動上傳到 Route 53
- D. 為 hosted zone 建立 private hosted zone 副本，並在副本上啟用 DNSSEC
- E. 把 KSK 對應的 DS 記錄加到父網域（在網域商後台設定），以建立信任鏈

> [!answer]- 答案：B、E
> **A ✗** Route 53 的 KSK 必須使用非對稱、`ECC_NIST_P256` 規格且位於 `us-east-1` 的 KMS key，對稱 key 或其他 Region 的 key 都不能使用。
>
> **B ✓** 這是 Route 53 DNSSEC signing 對 KSK 的要求。使用 customer managed key 讓公司以 KMS 的 key policy 控制誰能使用簽署金鑰，並可搭配 DNSSEC 相關的 CloudWatch 指標建立 alarm 通知異常。
>
> **C ✗** ZSK 由 Route 53 自動管理與輪替，不需要也不能自行上傳。
>
> **D ✗** Private hosted zone 不支援 DNSSEC signing，而且合規要求的是 public 網域的回應。
>
> **E ✓** 簽章只有在父網域存放了對應的 DS 記錄時才能被驗證。網域在別家網域商註冊，就要到該網域商加入 DS 記錄，否則信任鏈不完整，DNSSEC 無法生效。
>
> **考點**：SAP-2.3、SAP-1.2｜Route 53 DNSSEC signing 與信任鏈

### 練習 9-16｜SAP｜單選｜Split-horizon 與 NXDOMAIN

Wanderly 有 public hosted zone `wanderly.com`，其中 `www`、`api` 與 `status` 都指向 public 資源。為了讓 VPC 內部呼叫 `api.wanderly.com` 時走 internal ALB，團隊建立了同名的 private hosted zone `wanderly.com` 並關聯到 production VPC，只在裡面放了 `api` 一筆記錄。上線後，VPC 內的監控程式呼叫 `status.wanderly.com` 時開始失敗，錯誤是名稱不存在。辦公室經 Resolver inbound endpoint 查詢時也出現相同問題。

最合適的修正是什麼？

- A. 在 public hosted zone 把 `status` 的 TTL 調低，讓 Resolver 重新查詢
- B. 建立一條 Resolver forwarding rule，把 `wanderly.com` 轉送到 public hosted zone 的 name server
- C. 把 private hosted zone 從 VPC 取消關聯，改在 VPC 的 hosts 檔中寫入 internal ALB 的 IP
- D. 在 private hosted zone 中補上 VPC 內部會使用的其他名稱（例如 `status`、`www`），內容與 public zone 一致或指向內部資源

> [!answer]- 答案：D
> **A ✗** 問題不是快取，而是 Resolver 根本不會去查 public zone，調整 public zone 的 TTL 沒有幫助。
>
> **B ✗** 轉送整個 `wanderly.com` 會讓 forwarding rule 優先於 private hosted zone，使 `api` 也改由 public zone 回答，失去 split-horizon 的目的，還讓內部解析多了一個外部依賴。
>
> **C ✗** Hosts 檔要在每台機器上維護，無法隨 ALB IP 變動，也無法套用到經 inbound endpoint 查詢的地端用戶。
>
> **D ✓** 查詢名稱符合已關聯的 private hosted zone 時，Resolver 只在 private zone 中尋找，找不到就回 NXDOMAIN，不會回頭查 public zone。經 inbound endpoint 進入 VPC 的查詢也遵循同一規則。所以 split-horizon 時，內部會用到的每個名稱都必須在 private zone 中建立。
>
> **考點**：SAP-3.4、SAP-1.1｜Split-horizon DNS 與 private zone 的 NXDOMAIN 行為
