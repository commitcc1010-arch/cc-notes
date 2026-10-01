---
title: 易混淆服務對照
---

# 附錄 A　易混淆服務對照

考試裡最花時間的，往往不是完全陌生的服務，而是「兩個都聽過、看起來都能用」的選項。本附錄把全書各章「比較與選型」中最常互相混淆的服務與概念集中整理成對照卡，每一組都包含四個部分：

- **一句話差異**：考前只記這一句也能刪掉一半選項。
- **比較表**：只列真正會決定答案的 3–6 個維度。
- **題目看到什麼選哪個**：把題目中的訊號直接對應到答案。
- **出處**：完整原理與例子在哪一章，忘記時回去讀。

使用方式：做錯題時，先找出你把哪兩個服務搞混，再到這裡讀對應的卡片；考前一週可以只讀每組的「一句話差異」與「題目看到什麼」。本附錄只整理對照，數字與限制的完整清單見附錄 B，題目關鍵字的反查見附錄 C。

> [!warning] 服務現況
> 部分服務已不開放新客戶或已停止（例如 Snowball Edge、App Runner、QLDB、S3 Select、Timestream for LiveAnalytics、Migration Hub、Audit Manager 的新帳號設定）。考題可能仍以它們為答案，本附錄在相關卡片註明現況；實務上請先確認帳號是否可用。

---

## Networking：網路

### A-1　Security group vs Network ACL

**一句話差異**：Security group 是掛在 ENI 上、會記住連線的「只允許」清單；NACL 是掛在 subnet 邊界、不記連線、依編號逐條比對的「允許＋拒絕」清單。

| 維度 | Security group | Network ACL |
|---|---|---|
| 套用位置 | ENI（instance 層級） | Subnet 邊界 |
| 狀態 | Stateful，回應自動放行 | Stateless，回程要另開規則（ephemeral ports 1024–65535） |
| 規則類型 | 只有 allow | Allow 與 deny |
| 評估方式 | 所有規則合併，任一允許即通過 | 依規則號碼由小到大，第一條符合者決定 |
| 來源可寫 | CIDR、其他 SG、prefix list | 只能寫 CIDR |
| 預設 | 新 SG：入站全拒、出站全開 | Default NACL 全開；custom NACL 全拒 |

**題目看到什麼選哪個**

- 「只允許 ALB 連 app、只允許 app 連 DB，instance 會擴縮」→ SG 參照上游 SG。
- 「封鎖特定惡意 IP」→ NACL deny（編號要小於 allow）；大量或 HTTP 層 → WAF。
- 「SG 已允許，連線仍 timeout」→ 檢查 NACL 的回程 ephemeral ports。
- 選項寫「在 SG 加 deny 規則」→ 錯，SG 沒有 deny。

**出處**：第 6 章

### A-2　Gateway endpoint vs Interface endpoint

**一句話差異**：Gateway endpoint 是 route table 裡的一條免費路由，只服務 S3 與 DynamoDB、只對本 VPC 有效；interface endpoint 是放在 subnet 裡的收費 ENI（PrivateLink），支援大多數服務，地端與其他 VPC 也能用。

| 維度 | Gateway endpoint | Interface endpoint |
|---|---|---|
| 支援服務 | 只有 S3、DynamoDB | 大多數 AWS 服務、自家與 SaaS 服務 |
| 機制 | Route table 中的 prefix list route | Subnet 中的 ENI，private DNS 解析到 private IP |
| 地端／其他 VPC 可用 | 不能 | 能（需路由與 DNS 配合） |
| Security group | 無 | 有，套在 endpoint ENI |
| 費用 | 免費 | 每 AZ 每小時 + 每 GB |

**題目看到什麼選哪個**

- 「private subnet 大量存取 S3／DynamoDB，降低 NAT 費用」→ Gateway endpoint。
- 「地端經 DX／VPN 私有存取 S3」→ S3 interface endpoint。
- 「其他 VPC 經 TGW 共用 S3 gateway endpoint」→ 不可行，每個 VPC 各建 gateway endpoint，或改用 interface endpoint。
- 「呼叫 Secrets Manager、SSM、KMS 不經 Internet」→ Interface endpoint + private DNS。
- 「DNS 解析到 endpoint IP 但 timeout」→ Endpoint ENI 的 SG 沒開 443。

**出處**：第 6 章、第 41 章

### A-3　Internet Gateway vs NAT Gateway vs Egress-only Internet Gateway

**一句話差異**：IGW 讓有 public IP 的資源雙向上網；NAT Gateway 讓 private subnet 的 IPv4 流量「只出不進」；egress-only IGW 是 IPv6 版本的「只出不進」。

| 維度 | Internet Gateway | NAT Gateway | Egress-only IGW |
|---|---|---|---|
| 範圍 | VPC（跨 AZ） | 單一 AZ（zonal） | VPC（跨 AZ） |
| 方向 | IPv4／IPv6 雙向 | IPv4 只出不進 | IPv6 只出不進 |
| 高可用 | AWS 內建，一個 VPC 只能一個 | 每個 AZ 一台，各 AZ private route table 指向自己的 NAT | AWS 內建 |
| 收費 | 免費 | 每小時 + 每 GB 處理費 | 無處理費 |

**題目看到什麼選哪個**

- 「private instance 要下載 patch、呼叫外部 API」→ NAT Gateway（放 public subnet）+ `0.0.0.0/0 → NAT`。
- 「NAT 要高可用、AZ 故障不影響其他 AZ」→ 每 AZ 一台 NAT Gateway。
- 「外部夥伴要把我們的來源 IP 加入允許清單」→ NAT Gateway 的 Elastic IP。
- 「IPv6 只允許出站」→ Egress-only IGW（IPv6 不用 NAT）。
- 選項「部署兩個 IGW 做備援」或「用 NAT 讓 Internet 連進來」→ 錯。

**出處**：第 5 章

### A-4　VPC peering vs Transit Gateway vs PrivateLink vs VPC Lattice

**一句話差異**：Peering 是兩個 VPC 之間的點對點網路線；TGW 是可遞移的中央路由器；PrivateLink 只暴露「一個服務」且單向；VPC Lattice 是以 IAM 身份授權的應用層服務網路。

| 維度 | VPC peering | Transit Gateway | PrivateLink | VPC Lattice |
|---|---|---|---|---|
| 層級 | 網路（L3） | 網路（L3） | 服務（L4） | 應用（L7 為主） |
| 遞移性 | 無 | 有（依 TGW route table） | 不適用 | 不適用 |
| CIDR 重疊 | 不允許 | 同一路由域內不行 | 可以 | 可以 |
| 方向 | 雙向 | 雙向 | 單向（consumer → provider） | 用戶端 → 服務 |
| 主要費用 | 只有跨 AZ／跨 Region 傳輸 | 每 attachment 小時 + 每 GB 處理 | Endpoint 每 AZ 小時 + 每 GB | 每服務小時 + 每 GB + 每請求 |

**題目看到什麼選哪個**

- 「兩三個 VPC、CIDR 不重疊、最便宜」→ VPC peering。
- 「A–B、B–C 已 peering，A 要連 C」→ 再建 A–C peering 或改 TGW（peering 不遞移）。
- 「數十到數百個 VPC 加地端、集中隔離」→ Transit Gateway。
- 「把服務提供給其他帳號或客戶，不暴露整個 VPC；CIDR 重疊」→ PrivateLink endpoint service（NLB 前端）。
- 「跨帳號微服務、以 IAM 身份授權、HTTP 路徑路由」→ VPC Lattice。
- 「中央團隊管網路，應用團隊在共享 subnet 部署」→ VPC sharing（AWS RAM）。

**出處**：第 7 章、第 41 章

### A-5　Site-to-Site VPN vs Accelerated VPN vs Client VPN vs Direct Connect

**一句話差異**：Site-to-Site VPN 是幾天內就能接通的 Internet 加密隧道；Accelerated VPN 讓隧道改走 AWS 骨幹；Client VPN 給個別使用者的筆電；Direct Connect 是數週到數月才能建好、延遲穩定但預設不加密的實體專線。

| 維度 | Site-to-Site VPN | Accelerated VPN | Client VPN | Direct Connect |
|---|---|---|---|---|
| 連接對象 | 整個站點 | 整個站點（遠距） | 個別使用者裝置 | 整個站點 |
| 路徑 | 公共 Internet | Edge location + AWS 骨幹 | 公共 Internet | 私有實體線路 |
| 加密 | IPsec | IPsec | TLS | 預設不加密（MACsec／IPsec 另加） |
| 建置時間 | 數小時到數天 | 數小時到數天 | 數小時 | 數週到數月 |
| AWS 端終點 | VGW 或 TGW | 只能 TGW | Client VPN endpoint | VGW、DXGW、TGW（經 DXGW） |

**題目看到什麼選哪個**

- 「盡快建立加密連線、中等流量」→ Site-to-Site VPN。
- 「一致的延遲、大量持續傳輸、不經 Internet」→ Direct Connect。
- 「下週就要上線，但長期需要穩定頻寬」→ 先 VPN，DX 完成後 VPN 留作備援。
- 「VPN 頻寬超過單一 tunnel（考試常用約 1.25 Gbps）」→ TGW + 多條 VPN + BGP ECMP（VGW 不支援 ECMP）。
- 「海外分公司 Internet 品質差」→ Accelerated VPN（需 TGW）。
- 「遠端員工筆電、SAML／AD 登入」→ Client VPN。

**出處**：第 8 章

### A-6　Dedicated connection vs Hosted connection（Direct Connect）

**一句話差異**：Dedicated 是直接向 AWS 申請的實體 port，可多個 VIF、可 MACsec；hosted 是 Direct Connect Partner 切給你的一段頻寬，每條只有一個 VIF。

| 維度 | Dedicated connection | Hosted connection |
|---|---|---|
| 向誰申請 | AWS（實體 port） | AWS Direct Connect Partner |
| 速度 | 1、10、100 Gbps（部分地點更高） | 從 50 Mbps 起，依夥伴提供 |
| VIF 數量 | 可建立多個 | 每條只有一個 |
| MACsec | 支援（特定速度與地點） | 不支援 |
| 機房設備 | 需在 DX location 有路由器（或由夥伴代管） | 由夥伴處理 |

**題目看到什麼選哪個**

- 「頻寬小於 1 Gbps、不想自管機房設備」→ Hosted connection。
- 「需要多個 VIF、MACsec、大頻寬」→ Dedicated connection。
- 選項「在 hosted connection 上建立多個 VIF」→ 錯，要多條 hosted connection。

**出處**：第 8 章

### A-7　Private VIF vs Public VIF vs Transit VIF

**一句話差異**：Private VIF 連到 VPC 的 private IP；public VIF 連到 AWS 服務的 public endpoint；transit VIF 經 DX Gateway 連到 Transit Gateway，一次接大量 VPC。

| 維度 | Private VIF | Public VIF | Transit VIF |
|---|---|---|---|
| 連到 | VGW 或 DX Gateway | AWS public 網路 | DX Gateway → TGW |
| 可存取 | VPC 內 private IP 資源 | S3、DynamoDB、各服務 API 的 public endpoint | 透過 TGW 連到的所有 VPC |
| 位址 | Private IP | 需要 public IP | Private IP |
| 典型規模 | 單一或少數 VPC（多 Region 加 DXGW） | 大量存取 AWS public 服務 | 數十個 VPC 且要隔離 |

**題目看到什麼選哪個**

- 「地端經 DX 存取 S3 public endpoint」→ Public VIF；不想引入 Amazon public 路由 → private VIF + S3 interface endpoint。
- 「一條 DX 連到多個 Region 的 VPC」→ Direct Connect Gateway。
- 「地端經 DX 連數十個 VPC 並做隔離」→ Transit VIF + DXGW + TGW route tables。
- 選項「VPC 關聯同一個 DXGW 後就能互通」→ 錯，DXGW 不在 VPC 之間轉送。

**出處**：第 8 章、第 41 章

### A-8　Route 53 Resolver inbound endpoint vs outbound endpoint

**一句話差異**：Inbound 讓「外面（地端）的查詢進來」解析 AWS 的名稱；outbound 讓「VPC 內的查詢出去」解析地端的名稱。

| 維度 | Inbound endpoint | Outbound endpoint |
|---|---|---|
| 查詢方向 | 地端 → VPC | VPC → 地端 |
| 要搭配 | 地端 DNS 的 conditional forwarder | Resolver forwarding rule |
| 解決的問題 | 地端解析 private hosted zone | VPC 內程式解析地端網域 |
| 多帳號做法 | 集中一組，所有 PHZ 關聯到 DNS VPC | 集中一組，用 RAM 共享 forwarding rule（或 Route 53 Profiles） |

**題目看到什麼選哪個**

- 「VPC 內的程式要解析 `corp.example.local`」→ Outbound endpoint + forwarding rule。
- 「地端要解析 private hosted zone」→ Inbound endpoint + 地端 conditional forwarder。
- 選項「地端直接查 VPC 的 +2 resolver」→ 錯，它只接受 VPC 內的查詢。

**出處**：第 8 章、第 41 章

### A-9　Alias record vs CNAME

**一句話差異**：Alias 是 Route 53 專屬、可放在 zone apex、指向 AWS 資源時查詢免費的 A／AAAA 記錄；CNAME 是 DNS 標準、不能放在 apex、指向任何名稱。

| 維度 | Alias | CNAME |
|---|---|---|
| 能否放 zone apex | 可以 | 不行（DNS 協定規定） |
| 指向 | 特定 AWS 資源或同 zone 的記錄 | 任何 DNS 名稱 |
| 查詢費用 | 指向 AWS 資源時免費 | 一般查詢費用 |
| TTL | 由目標決定，不能自訂 | 自行設定 |
| 健康狀態 | 可開 Evaluate target health | 需另設 health check |

**題目看到什麼選哪個**

- 「`example.com`（root／naked domain）指向 ALB、CloudFront、S3 website」→ Alias。
- 「指向 AWS 資源且要降低 DNS 查詢費」→ Alias。
- 「指向 RDS endpoint」→ CNAME（RDS 不能當 alias 目標）。

**出處**：第 9 章

### A-10　Latency vs Geolocation vs Geoproximity vs IP-based routing

**一句話差異**：Latency 依「量到的延遲」挑最快的 Region；geolocation 依「使用者所在國家／洲」；geoproximity 依「距離」並可用 bias 調整範圍；IP-based 依「來源網段」。

| 維度 | Latency | Geolocation | Geoproximity | IP-based |
|---|---|---|---|---|
| 判斷依據 | 使用者到 Region 的網路延遲 | 國家、洲、州 | 地理距離 + bias | CIDR collection |
| 需要 default 記錄 | 否 | 是，否則未對應地區拿不到答案 | 否 | 建議設定 |
| 典型用途 | 效能 | 法規、語言、授權 | 讓某 Region 多吸收周邊流量 | 依 ISP 或企業網段分流 |
| 常見誤解 | 不等於地理最近，也不保證資料留在某國 | 只決定 DNS 答案，資料主權仍要應用層控制 | — | — |

**題目看到什麼選哪個**

- 「全球使用者連到延遲最低的 Region」→ Latency。
- 「依國家提供不同內容、法規限制國家」→ Geolocation + default。
- 「讓某個 Region 多吸收周邊流量」→ Geoproximity + bias。
- 「依 ISP 或企業網段分流」→ IP-based。

**出處**：第 9 章、第 42 章

### A-11　Simple vs Multivalue answer vs Failover vs Weighted routing

**一句話差異**：Simple 不做健康檢查；multivalue 回答最多 8 個健康 IP；failover 是主備切換；weighted 依比例分配 DNS 回答。

| 維度 | Simple | Multivalue answer | Failover | Weighted |
|---|---|---|---|---|
| Health check | 不支援 | 支援，只回健康的 | primary 必須有 | 支援 |
| 回答 | 一筆記錄的所有值 | 最多 8 筆健康記錄 | primary，不健康時改 secondary | 依權重機率回答 |
| 典型用途 | 單一 endpoint | 沒有 LB 的簡易分散 | DR、靜態維護頁 | Canary、逐步搬遷 |

**題目看到什麼選哪個**

- 「不用 LB，DNS 回答多個健康 IP」→ Multivalue answer。
- 「主 Region 故障時切到備援或 S3 靜態維護頁」→ Failover + health check。
- 「10% 流量給新版本」→ Weighted（是 DNS 回答機率，受快取影響）。
- 「health check 私有 subnet 的資源」→ CloudWatch alarm 型 health check。

**出處**：第 9 章

### A-12　ALB vs NLB vs GWLB

**一句話差異**：ALB 看得懂 HTTP，用路徑與標頭分流；NLB 處理 TCP／UDP、每 AZ 有固定 IP、延遲極低；GWLB 用 GENEVE 把所有流量透明地送進第三方防火牆。

| 維度 | ALB | NLB | GWLB |
|---|---|---|---|
| 層級／協定 | L7：HTTP、HTTPS、gRPC、WebSocket | L4：TCP、UDP、TLS | L3：所有 IP 流量 |
| 固定 IP | 無（只有 DNS 名稱） | 每 AZ 一個，可綁 EIP | 不適用 |
| TLS | 終止，SNI 多憑證 | TLS listener 終止，或 TCP listener passthrough | 不處理 |
| Client IP | `X-Forwarded-For` | Client IP preservation／Proxy Protocol v2 | 封包不變 |
| 典型用途 | 網站、API、微服務、containers | 非 HTTP、固定 IP、PrivateLink 前端 | 第三方防火牆、IDS／IPS |

**題目看到什麼選哪個**

- 「依 URL path 或 host 分流到不同服務」→ ALB listener rules。
- 「不改程式就加上登入」→ ALB authenticate-oidc／cognito。
- 「需要固定 IP、防火牆白名單」→ NLB；同時要 L7 → NLB（alb target）→ ALB，或 Global Accelerator → ALB。
- 「UDP、自訂 TCP、每秒數百萬請求」→ NLB。
- 「後端自己終止 TLS」→ NLB TCP listener（TLS listener 會終止 TLS）。
- 「第三方防火牆設備、透明檢查」→ GWLB + GWLB endpoint。

**出處**：第 10 章

### A-13　CloudFront vs Global Accelerator

**一句話差異**：CloudFront 是看得懂 HTTP、會快取的 CDN；Global Accelerator 是不快取、提供 2 個固定 anycast IP、支援 TCP／UDP 的全球網路入口。

| 維度 | CloudFront | Global Accelerator |
|---|---|---|
| 協定 | HTTP、HTTPS、WebSocket | TCP、UDP |
| 快取 | 有 | 無 |
| 入口位址 | DNS 名稱，IP 會變 | 2 個固定 anycast IP |
| 後端切換 | Origin group（只對 GET、HEAD、OPTIONS） | Endpoint 健康檢查，快速切換，不受 DNS 快取影響 |
| 內容控制 | Behavior、signed URL、geo restriction、edge functions、WAF | Listener、traffic dial、weight、affinity |

**題目看到什麼選哪個**

- 「全球使用者靜態內容慢、降低 origin 負載」→ CloudFront。
- 「UDP、遊戲、VoIP、IoT」→ Global Accelerator。
- 「固定 IP 白名單、anycast」→ Global Accelerator。
- 「多 Region 快速 failover、不受 DNS 快取影響」→ Global Accelerator。
- 「逐步把流量移到新 Region」→ Global Accelerator traffic dial。

**出處**：第 11 章、第 42 章

### A-14　Route 53 latency／failover routing vs Global Accelerator

**一句話差異**：Route 53 在 DNS 層挑 endpoint，封包仍走公共 Internet、切換受用戶端快取影響；Global Accelerator 在封包層導流，入口 IP 固定、切換不受 DNS 快取影響。

| 維度 | Route 53 | Global Accelerator |
|---|---|---|
| 運作層 | DNS 回答 | 網路層 anycast |
| 切換速度 | 受 TTL 與 resolver 快取影響 | 秒級，不受 DNS 快取影響 |
| 封包路徑 | 公共 Internet | 從最近 edge 進入 AWS 骨幹 |
| 固定 IP | 無 | 2 個 static IP |
| 用途定位 | 一般 DNS 層主備與就近導流 | 要固定 IP 或秒級切換時才值得 |

**題目看到什麼選哪個**

- 「主備切換、成本敏感、可接受數分鐘」→ Route 53 failover。
- 「秒級、不受用戶端快取影響的切換」→ Global Accelerator。
- 「單一 Region 內分散請求」→ 都不是，用 ELB。

**出處**：第 9 章、第 11 章、第 42 章

### A-15　CloudFront signed URL vs signed cookie vs S3 presigned URL

**一句話差異**：CloudFront signed URL 保護「單一檔案」、signed cookie 保護「一批檔案」，兩者都經過 CloudFront 快取；S3 presigned URL 直接連 S3，繞過 CloudFront。

| 維度 | CloudFront signed URL | CloudFront signed cookie | S3 presigned URL |
|---|---|---|---|
| 保護範圍 | 單一檔案 | 多個檔案（例如整個影片串流） | 單一 object、單一動作 |
| 是否改 URL | 是 | 否 | 是 |
| 經過 CloudFront | 是（有快取與邊緣控制） | 是 | 否 |
| 權限來源 | Trusted key group（公鑰） | Trusted key group（公鑰） | 簽章者的 IAM 權限（不能擴大權限） |

**題目看到什麼選哪個**

- 「只給付費使用者下載單一檔案」→ CloudFront signed URL。
- 「影片串流、多個檔案、不想改 URL」→ Signed cookie。
- 「沒有 AWS 帳號的使用者限時上傳到 S3」「上傳大檔不經應用程式伺服器」→ S3 presigned URL。

**出處**：第 11 章、第 22 章

### A-16　CloudFront Functions vs Lambda@Edge

**一句話差異**：CloudFront Functions 做每個請求都要的極輕量改寫，沒有網路存取；Lambda@Edge 能呼叫外部服務、讀 body、在 origin 觸發點動態選 origin，但較貴、要在 us-east-1 建立。

| 維度 | CloudFront Functions | Lambda@Edge |
|---|---|---|
| 觸發點 | 只有 viewer request／response | 四個都可以 |
| 網路存取 | 不行 | 可以 |
| 讀 request body | 不行 | 可以（origin 觸發） |
| 規模與成本 | 每秒數百萬次，成本低 | 較高 |
| 部署 | 直接在 CloudFront 建立 | 在 us-east-1 建立並關聯版本 |

**題目看到什麼選哪個**

- 「header／URL 改寫、轉址、cache key 正規化、最低成本」→ CloudFront Functions。
- 「依 cookie 查 DynamoDB 後決定 origin」「需要呼叫外部 API」→ Lambda@Edge。

**出處**：第 11 章

### A-17　OAC vs OAI（CloudFront 存取 S3）

**一句話差異**：OAC 是現行做法，支援 SSE-KMS 等新功能；OAI 是舊做法。兩者都只能用在 S3 REST endpoint，不能用在 S3 website endpoint。

| 維度 | OAC | OAI |
|---|---|---|
| 定位 | 現行建議 | 舊做法 |
| Bucket policy 寫法 | 授權 CloudFront 服務主體，以 `AWS:SourceArn` 限定 distribution | 授權 OAI 身份 |
| SSE-KMS 物件 | 支援（KMS key policy 允許 CloudFront 服務主體解密） | 不支援 |
| S3 website endpoint | 不支援（website 是 custom origin） | 不支援 |

**題目看到什麼選哪個**

- 「S3 bucket 要私有、只能經 CloudFront 存取」→ OAC + bucket policy。
- 「題目提到 OAI」→ 改用 OAC。
- 「用 SSE-KMS 後 CloudFront 回 403」→ KMS key policy 允許 CloudFront 服務主體。
- 選項「為了讓 CloudFront 讀取而關閉 Block Public Access」→ 錯。

**出處**：第 11 章、第 22 章

### A-18　S3 Transfer Acceleration vs CloudFront

**一句話差異**：Transfer Acceleration 加速「遠距離使用者上傳到單一 bucket」；CloudFront 加速「下載」並快取。

| 維度 | S3 Transfer Acceleration | CloudFront |
|---|---|---|
| 主要方向 | 上傳（也可下載，但不快取） | 下載與快取 |
| 快取 | 無 | 有 |
| 適用對象 | 遠距離的 Internet 用戶端 | 全球讀者 |
| 對 Region 內或 EC2 的傳輸 | 沒有效果 | 不適用 |

**題目看到什麼選哪個**

- 「全球各地上傳大檔到單一 Region 的 bucket 很慢」→ Transfer Acceleration + multipart upload。
- 「全球使用者下載 S3 內容、降低傳出費」→ CloudFront。

**出處**：第 11 章、第 22 章、第 25 章

---

## Security：安全與身份

### A-19　IAM user vs IAM role vs IAM Identity Center

**一句話差異**：IAM user 有長期憑證，只在別無選擇時使用；role 發臨時憑證，給 AWS 上的程式、跨帳號與聯合身份；Identity Center 讓員工用企業帳號登入組織內所有帳號。

| 維度 | IAM user | IAM role | IAM Identity Center |
|---|---|---|---|
| 憑證 | 長期（密碼、access key） | 臨時（STS） | 各帳號 role 的臨時憑證 |
| 典型對象 | 無法聯合的外部程式 | EC2、Lambda、ECS、跨帳號、CI/CD | 員工（workforce） |
| 規模 | 單一帳號 | 單一帳號（可被跨帳號 assume） | 組織內所有帳號 |
| 管理 | 每帳號各自建立 | Trust policy + permissions policy | Permission sets + assignments，SCIM 同步 |

**題目看到什麼選哪個**

- 「EC2 上的程式要存取 S3，不要存憑證」→ IAM role（instance profile）。
- 「員工用企業帳號登入多個 AWS 帳號」→ Identity Center。
- 「GitHub Actions 不想存 access key」→ OIDC identity provider + role。
- 「地端伺服器呼叫 AWS 不想用 access key」→ IAM Roles Anywhere。
- 「網站終端使用者」→ 都不是，用 Cognito。

**出處**：第 12 章、第 13 章

### A-20　Identity-based policy vs Resource-based policy

**一句話差異**：Identity-based policy 掛在 user／role 上、沒有 Principal，說「我能做什麼」；resource-based policy 掛在資源上、有 Principal，說「誰能動我」，是跨帳號分享的主要工具。

| 維度 | Identity-based | Resource-based |
|---|---|---|
| 附加在 | User、group、role | Bucket、queue、key、role trust policy 等 |
| Principal 欄位 | 沒有 | 有 |
| 跨帳號 | 要對方資源也授權（或 assume role） | 可直接授權對方帳號的 principal |
| 典型用途 | 日常權限 | 跨帳號、指定 AWS 服務能寫入 |

**題目看到什麼選哪個**

- 「從帳號 A 的 bucket 複製到帳號 B，保留 A 的權限」→ B 的 bucket policy 授權 A 的身份。
- 「整個組織都能讀一個 bucket」→ `Principal: "*"` + `aws:PrincipalOrgID`。
- 「S3／SNS 無法觸發 Lambda」→ Function 的 resource-based policy。
- 選項「把 group 寫進 bucket policy 的 Principal」→ 錯，group 不是 principal。

**出處**：第 12 章、第 13 章

### A-21　SCP vs RCP vs Permissions boundary vs Session policy

**一句話差異**：四者都「只設上限、不授權」；SCP 限制組織成員帳號裡的身份，RCP 限制組織成員帳號裡的資源，permissions boundary 限制單一 user／role，session policy 限制單次 session。

| 維度 | SCP | RCP | Permissions boundary | Session policy |
|---|---|---|---|---|
| 管理層級 | Organization（root／OU／帳號） | Organization | 帳號內 | 單次 session |
| 限制對象 | 成員帳號裡的 principal | 成員帳號裡的資源 | 單一 user／role | 該次 assume 的權限 |
| 影響成員帳號 root | 會 | 會 | 不能 | 不適用 |
| 影響 management account | 不會 | 不會 | 不適用 | 不適用 |
| 典型用途 | Region 限制、保護 CloudTrail | 拒絕組織外身份存取資源 | 委派開發者建 role 不能提權 | 臨時縮小權限 |

**題目看到什麼選哪個**

- 「任何人（含帳號管理員）都不准停用 CloudTrail」→ SCP Deny。
- 「拒絕組織外身份存取 S3／KMS，即使 bucket policy 寫錯」→ RCP + `aws:PrincipalOrgID`。
- 「開發者可自建 Lambda role 但不能提權」→ Permissions boundary + `iam:PermissionsBoundary` 條件。
- 「有 AdministratorAccess 仍被拒」→ 某層 SCP、boundary、session policy 或 explicit Deny。
- 選項「SCP Allow 可以補足 IAM 缺少的權限」→ 錯，兩者是交集。

**出處**：第 12 章、第 14 章、第 40 章、第 43 章

### A-22　Tag policy vs SCP `aws:RequestTag` vs Config rule

**一句話差異**：Tag policy 只規範 tag 的格式與值；要「沒有 tag 就不能建立」用 SCP 的 `aws:RequestTag`；要找出已存在的不合規資源用 Config。

| 維度 | Tag policy | SCP + `aws:RequestTag` | Config rule |
|---|---|---|---|
| 時機 | 寫入 tag 時檢查格式 | 建立資源時預防 | 事後偵測 |
| 能否強制 tag 存在 | 不能 | 能 | 只能發現與修正 |
| 典型用途 | 大小寫、允許值統一 | 必須帶 CostCenter 才能建立 | 稽核既有資源 |

**題目看到什麼選哪個**

- 「tag key 大小寫不一致」→ Tag policy。
- 「沒有某個 tag 就不能建立資源」→ SCP + `aws:RequestTag`。
- 「找出已經存在、缺少 tag 的資源」→ Config rule。

**出處**：第 14 章、第 40 章、第 43 章

### A-23　跨帳號 role（AssumeRole）vs Resource-based policy

**一句話差異**：AssumeRole 讓呼叫者「換成對方帳號的身份」，放棄自己的權限；resource-based policy 讓呼叫者「用自己的身份直接存取」，保留自己帳號的權限。

| 維度 | 跨帳號 role | Resource-based policy |
|---|---|---|
| 呼叫者身份 | 變成目標帳號的 role | 保留原身份 |
| 同時存取兩邊資源 | 不方便（一次只有一個身份） | 方便（例如跨帳號複製） |
| 適用服務 | 所有服務 | 只限支援 resource policy 的資源 |
| 第三方廠商 | 加 `sts:ExternalId` 防 confused deputy | 較少用 |

**題目看到什麼選哪個**

- 「帳號 A 要操作帳號 B 的多種資源」→ B 建 role 信任 A，A 的 identity policy 允許 `sts:AssumeRole`。
- 「第三方 SaaS 要存取我們的帳號」→ 跨帳號 role + external ID。
- 「從 A 的 bucket 複製到 B 的 bucket」→ Resource-based policy（bucket policy）。

**出處**：第 13 章

### A-24　Cognito user pool vs identity pool

**一句話差異**：User pool 負責「登入」，發 JWT；identity pool 負責「換 AWS 臨時憑證」，讓 App 直接存取 AWS 服務。

| 維度 | User pool | Identity pool |
|---|---|---|
| 輸出 | JWT（ID、access、refresh token） | 臨時 AWS 憑證 |
| 功能 | 註冊、登入、MFA、社群登入、SAML／OIDC 聯合 | 已驗證或訪客身份對應到 IAM role |
| 典型搭配 | API Gateway Cognito authorizer、ALB authenticate | App 直接上傳 S3、讀 DynamoDB |
| 每人隔離 | 由後端依 JWT 授權 | Policy 變數 `${cognito-identity.amazonaws.com:sub}` |

**題目看到什麼選哪個**

- 「App 使用者註冊、登入、社群登入」→ User pool。
- 「行動 App 直接上傳 S3、每人只能存取自己的資料」→ Identity pool。
- 「API Gateway 驗證使用者 JWT」→ User pool authorizer。

**出處**：第 13 章

### A-25　AWS Managed Microsoft AD vs AD Connector vs Simple AD

**一句話差異**：Managed AD 是 AWS 上真正的 AD，可與地端建立 trust、地端斷線仍能驗證；AD Connector 只是代理，不存目錄；Simple AD 是小型的 Samba 相容目錄。

| 維度 | Managed Microsoft AD | AD Connector | Simple AD |
|---|---|---|---|
| 本質 | AWS 託管的完整 AD | 轉送驗證到地端 AD 的代理 | Samba 相容目錄 |
| 雲端存目錄 | 是 | 否 | 是 |
| 與地端 trust | 支援 | 不適用 | 不支援 |
| 地端斷線 | 仍可驗證 | 無法驗證 | 不依賴地端 |
| 典型用途 | FSx for Windows、SQL Server Windows 驗證 | 沿用地端 AD 登入 AWS 服務 | 小型、基本功能 |

**題目看到什麼選哪個**

- 「地端 AD 帳號登入 AWS，不想在雲端存目錄」→ AD Connector。
- 「AWS 上需要完整 AD 並信任地端」→ Managed Microsoft AD + trust。
- 選項「AD Connector 會快取目錄，地端斷線也能登入」→ 錯。

**出處**：第 13 章

### A-26　KMS vs CloudHSM

**一句話差異**：KMS 是多租戶受管金鑰服務，與 AWS 服務深度整合、營運負擔低；CloudHSM 是單一租戶 HSM，客戶獨占控制金鑰、AWS 無法存取，但營運負擔較高。

| 維度 | KMS | CloudHSM |
|---|---|---|
| 租戶 | 多租戶 | 單一租戶 |
| 誰控制金鑰 | 你透過 key policy 控制；AWS 管理基礎設施 | 你管理 HSM 使用者與金鑰，AWS 只管硬體 |
| 介面 | AWS API | PKCS #11、JCE、CNG 等標準介面 |
| AWS 服務整合 | 原生 | 透過 KMS custom key store |
| 典型用途 | 一般靜態加密、envelope encryption | Oracle TDE、TLS offload、法規要求專屬 HSM |

**題目看到什麼選哪個**

- 「控制誰能解密、稽核每次解密」→ KMS customer managed key + CloudTrail。
- 「單一租戶 HSM、PKCS #11、AWS 不能存取金鑰」→ CloudHSM。
- 「要專屬 HSM，又要 S3、EBS 等服務原生整合」→ KMS custom key store（CloudHSM）。
- 「金鑰必須放在 AWS 以外」→ KMS external key store。
- 沒有明確的單一租戶要求時，KMS 優先於 CloudHSM。

**出處**：第 15 章、第 50 章

### A-27　AWS managed key vs Customer managed key

**一句話差異**：AWS managed key（例如 `aws/s3`、`aws/ebs`）由 AWS 管理 policy 與輪替，不能跨帳號；customer managed key 由你控制 key policy、輪替與刪除，可以跨帳號與職責分離。

| 維度 | AWS managed key | Customer managed key |
|---|---|---|
| Key policy | 不能修改 | 自行定義 |
| 跨帳號分享 | 不能 | 可以 |
| 輪替 | AWS 自動 | 可開啟自動輪替或依需求 |
| 職責分離 | 無法設定 | 可分開 key 管理者與使用者 |

**題目看到什麼選哪個**

- 「分享加密的 EBS snapshot、AMI 或 RDS snapshot 給其他帳號失敗」→ 改用 customer managed key 重新加密並授權對方帳號。
- 「SNS／EventBridge 送不進加密的 SQS」→ 改用 customer managed key 並授權服務 principal。
- 「管理 key 的人不能解密資料」→ Customer managed key 的 key policy 職責分離。

**出處**：第 15 章、第 17 章、第 26 章、第 32 章、第 43 章

### A-28　Secrets Manager vs Parameter Store

**一句話差異**：Secrets Manager 專為機密設計，內建自動輪替、跨 Region replica 與跨帳號分享；Parameter Store 是階層式設定，Standard 免費，SecureString 可放簡單機密但沒有內建輪替。

| 維度 | Secrets Manager | Parameter Store |
|---|---|---|
| 自動輪替 | 內建（資料庫密碼等） | 無 |
| 跨 Region | Replica secrets | 需自行處理 |
| 費用 | 每 secret 每月 + API 呼叫 | Standard 免費 |
| 典型用途 | 資料庫密碼、API key | 階層式設定值、feature 參數 |

**題目看到什麼選哪個**

- 「自動輪替資料庫密碼」→ Secrets Manager（RDS 可直接託管 master 密碼）。
- 「階層式設定、免費」→ Parameter Store Standard。
- 「DR Region 也要讀到密碼」→ Secrets Manager 跨 Region 複寫。
- 選項「用 Parameter Store 內建輪替」→ 錯。

**出處**：第 15 章、第 38 章、第 42 章

### A-29　SSE-S3 vs SSE-KMS vs SSE-C vs Client-side encryption

**一句話差異**：SSE-S3 由 S3 全權處理、新 bucket 預設；SSE-KMS 讓你用 KMS 控制解密權限並稽核；SSE-C 由你每次提供金鑰；client-side 在上傳前就加密，AWS 永遠看不到明文。

| 維度 | SSE-S3 | SSE-KMS | SSE-C | Client-side |
|---|---|---|---|---|
| 金鑰管理 | S3 | KMS（AWS managed 或 customer managed） | 客戶每次請求提供 | 客戶（可用 Encryption SDK + KMS） |
| 控制誰能解密 | 只靠 S3 權限 | 另需 KMS 權限 | 持有金鑰者 | 持有金鑰者 |
| 稽核解密 | 無獨立紀錄 | CloudTrail 記錄 KMS 呼叫 | 無 | 依實作 |
| 注意 | 新 bucket 預設 | 大量請求可能被 KMS throttle → S3 Bucket Key | 必須 HTTPS；新 bucket 預設封鎖 | 應用程式要自己處理 |

**題目看到什麼選哪個**

- 「沒有特別要求」→ 預設 SSE-S3。
- 「控制誰能解密、職責分離、跨帳號」→ SSE-KMS + customer managed key。
- 「SSE-KMS 被 throttle、KMS 費用高」→ S3 Bucket Key。
- 「AWS 永遠不能看到明文」→ Client-side encryption。
- 選項「修改預設加密會重新加密既有物件」→ 錯，要重新複製。

**出處**：第 15 章、第 22 章

### A-30　ACM 簽發憑證 vs 匯入憑證 vs AWS Private CA

**一句話差異**：ACM 簽發的公開憑證會自動續約；匯入的外部憑證不會續約；Private CA 用來簽發內部服務與 mTLS 的私有憑證。

| 維度 | ACM 簽發（public） | 匯入 ACM | AWS Private CA |
|---|---|---|---|
| 自動續約 | 會（DNS validation 最順） | 不會 | 依設定 |
| 用途 | ALB、CloudFront、API Gateway 的公開網站 | 公司政策指定外部 CA | 內部服務、mTLS |
| 私鑰匯出 | 不能 | 你本來就持有 | 可以 |
| 到期提醒 | 不需要 | EventBridge 事件／Config rule | 依設定 |

**題目看到什麼選哪個**

- 「CloudFront 自訂網域 HTTPS」→ ACM 憑證在 us-east-1。
- 「憑證自動續約」→ ACM 簽發 + DNS validation。
- 「匯入的憑證快到期」→ EventBridge／Config 提醒並重新匯入。
- 「內部微服務 mTLS」→ AWS Private CA。

**出處**：第 15 章、第 11 章

### A-31　WAF vs Shield Standard vs Shield Advanced

**一句話差異**：WAF 檢查 HTTP 請求內容（SQLi、XSS、rate limit、bot）；Shield Standard 是免費自動的 L3／L4 DDoS 防護；Shield Advanced 加上 SRT 專家支援、DDoS 費用保護與進階偵測。

| 維度 | WAF | Shield Standard | Shield Advanced |
|---|---|---|---|
| 防護對象 | L7 HTTP 請求內容 | 常見 L3／L4 DDoS | DDoS（含 L7 自動緩解） |
| 費用 | 依 web ACL、規則、請求 | 免費、自動 | 訂閱制 |
| 掛載位置 | CloudFront、ALB、API Gateway REST、AppSync、Cognito 等 | 所有客戶自動 | 指定的 CloudFront、Route 53 hosted zone、Global Accelerator、ALB、CLB、Elastic IP（EC2、NLB 經 EIP 間接保護） |
| 專家與補償 | 無 | 無 | SRT（需 Business／Enterprise Support）、費用保護 |

**題目看到什麼選哪個**

- 「SQL injection、XSS、OWASP Top 10」→ WAF managed rule groups。
- 「同一 IP 大量請求、暴力破解登入」→ WAF rate-based rule。
- 「DDoS 費用補償、24/7 DDoS 專家」→ Shield Advanced。
- 「入口是 NLB 或 EC2，要擋 HTTP 攻擊」→ 前面加 CloudFront 或改 ALB（WAF 不能掛 NLB）。
- 選項「Shield Advanced 會檢查 SQL injection」→ 錯。

**出處**：第 16 章

### A-32　Network Firewall vs GWLB + 第三方 appliance vs Route 53 Resolver DNS Firewall

**一句話差異**：Network Firewall 是 AWS 受管的 stateful 防火牆（網域清單、Suricata）；GWLB 讓你沿用既有第三方防火牆並水平擴展；DNS Firewall 只擋「查詢」惡意網域的 DNS 請求。

| 維度 | Network Firewall | GWLB + appliance | DNS Firewall |
|---|---|---|---|
| 檢查內容 | 封包、TLS SNI、HTTP Host、Suricata 規則 | 依廠商功能 | DNS 查詢 |
| 營運負擔 | 低（受管） | 較高（自管 appliance fleet） | 低 |
| 導入方式 | 路由導入 firewall endpoint | 路由導入 GWLB endpoint | 關聯到 VPC |
| 典型用途 | 出站網域允許清單、IPS | 公司指定廠商防火牆 | 擋惡意網域解析 |

**題目看到什麼選哪個**

- 「出站只允許特定網域、IPS」→ Network Firewall stateful domain list；DNS Firewall 作輔助。
- 「使用既有第三方防火牆、要能水平擴展」→ GWLB + GWLB endpoint。
- 「擋掉查詢惡意網域的 DNS」→ DNS Firewall。
- 「集中 inspection 後跨 AZ 流量間歇失敗」→ Inspection VPC 的 TGW attachment 開 appliance mode。

**出處**：第 16 章、第 41 章

### A-33　GuardDuty vs Inspector vs Macie vs Detective vs Security Hub

**一句話差異**：GuardDuty 偵測「正在發生的威脅」；Inspector 找「已知漏洞」；Macie 找「S3 裡的敏感資料」；Detective 做「調查與關聯分析」；Security Hub「彙整 findings 並跑標準檢查」。

| 服務 | 回答的問題 | 資料來源 | 典型關鍵字 |
|---|---|---|---|
| GuardDuty | 有沒有入侵、異常行為？ | CloudTrail、VPC Flow Logs、DNS 等（不需自己開 Flow Logs） | 挖礦、異常 API、憑證外洩 |
| Inspector | 有哪些 CVE？ | EC2、container image、Lambda | 漏洞掃描、ECR 映像 |
| Macie | S3 裡有沒有個資？ | S3 物件 | PII、信用卡號 |
| Detective | 這個 finding 的根因與關聯？ | GuardDuty 等 findings 與日誌 | 視覺化調查 |
| Security Hub | 多帳號安全狀態總覽？ | 各服務 findings、Config | CIS、FSBP 標準 |

**題目看到什麼選哪個**

- 「挖礦、異常 API、外洩 key、最少營運負擔」→ GuardDuty（所有 Region 啟用）。
- 「CVE、container image 掃描」→ Inspector。
- 「S3 中的個資、信用卡號」→ Macie。
- 「調查根因」→ Detective。
- 「集中檢視 findings、CIS benchmark」→ Security Hub（需先啟用 Config）。
- 選項「GuardDuty 會自動阻擋攻擊」→ 錯，它只偵測。

**出處**：第 16 章、第 43 章

### A-34　CloudTrail vs AWS Config vs CloudWatch

**一句話差異**：CloudTrail 回答「誰在什麼時候呼叫了哪個 API」；Config 回答「資源設定長什麼樣、何時改過、是否合規」；CloudWatch 回答「系統現在好不好」。

| 維度 | CloudTrail | AWS Config | CloudWatch |
|---|---|---|---|
| 記錄對象 | API 呼叫事件 | 資源設定快照與歷史 | Metrics、logs、alarms |
| 典型問題 | 誰刪了資源？誰讀了 S3 物件（data events）？ | Security group 何時被打開？是否合規？ | CPU、延遲、錯誤率 |
| 自動處理 | 經 EventBridge 觸發 | Rules + remediation（SSM Automation） | Alarm 動作 |
| 時機 | 事後稽核 | 事後偵測與修正 | 即時監控 |

**題目看到什麼選哪個**

- 「誰刪了資源、API 稽核」→ CloudTrail（長期保存要建 trail）。
- 「誰讀了 S3 物件」→ CloudTrail data events。
- 「資源設定歷史、合規檢查、自動修正」→ Config rules + remediation。
- 「EC2 記憶體使用率告警」→ CloudWatch（需 agent）。
- 選項「Config 能事前阻止違規」→ 錯，事前阻止要 IAM／SCP。

**出處**：第 16 章、第 36 章

### A-35　Object Lock compliance vs governance vs legal hold vs MFA Delete vs Vault Lock

**一句話差異**：Compliance mode 期限內任何人（含 root）都不能刪；governance mode 有 bypass 權限者可刪；legal hold 沒有期限、要人工解除；MFA Delete 只是永久刪除版本時多一道 MFA；Backup Vault Lock 是 AWS Backup 版本的不可刪除鎖。

| 機制 | 誰能刪 | 期限 | 典型用途 |
|---|---|---|---|
| Object Lock compliance | 期限內任何人都不能 | 固定保存期 | 法規 WORM、日誌保存 |
| Object Lock governance | 有 `s3:BypassGovernanceRetention` 者 | 固定保存期 | 防誤刪但保留例外 |
| Legal hold | 解除 hold 後才可刪 | 無期限 | 調查期間保全 |
| MFA Delete | 擁有 root MFA 者 | 不適用 | 永久刪除版本需額外驗證 |
| Backup Vault Lock compliance | 冷靜期後任何人都不能移除 | 依 vault 設定 | 防勒索、備份不可刪 |

**題目看到什麼選哪個**

- 「法規要求任何人（含 root）都不能刪除」→ Object Lock compliance（需 versioning）。
- 「調查期間保留、期限不明」→ Legal hold。
- 「備份不能被任何人刪除」→ AWS Backup Vault Lock compliance mode。
- 「之後可能要調整保存期限」→ governance mode。

**出處**：第 23 章、第 16 章、第 34 章、第 50 章、第 43 章

### A-36　Object Lock vs CloudTrail log file integrity validation

**一句話差異**：Object Lock「防止」日誌被刪改；log file integrity validation「證明」日誌沒被刪改。兩者常一起使用，但解決的是不同問題。

| 維度 | Object Lock | Log file integrity validation |
|---|---|---|
| 作用 | 防止刪除與覆寫 | 用 digest 檔驗證是否被竄改 |
| 套用在 | S3 bucket（log archive） | CloudTrail trail |
| 回答的問題 | 能不能刪？ | 有沒有被改過？ |

**題目看到什麼選哪個**

- 「日誌在保存期內任何人都不能刪除」→ Object Lock compliance mode。
- 「證明 CloudTrail 日誌沒有被竄改」→ Log file integrity validation（`validate-logs`）。

**出處**：第 40 章、第 50 章

### A-37　AWS Artifact vs AWS Audit Manager

**一句話差異**：Artifact 下載「AWS 自己」的合規報告（SOC、PCI）與協議；Audit Manager 收集「客戶自己這一側」的證據並對應到框架。

| 維度 | AWS Artifact | AWS Audit Manager |
|---|---|---|
| 證明的範圍 | AWS 負責的部分 | 客戶負責的部分 |
| 輸出 | SOC 2、PCI 等報告、BAA 等協議 | 依框架整理的持續證據 |
| 資料來源 | AWS | Config、Security Hub、CloudTrail 等 |
| 現況 | 一般可用 | 已進入維護模式，新帳號自 2026-04-30 起無法再設定（第 16 章） |

**題目看到什麼選哪個**

- 「取得 AWS 的 SOC 2 或 PCI 報告」→ Artifact。
- 「持續收集合規證據、產生稽核報告」→ 題目答案常為 Audit Manager；實務上新帳號改以 Config conformance packs、Security Hub 標準等組合。
- 選項「用 Artifact 證明自己的系統合規」→ 錯。

**出處**：第 16 章、第 50 章、第 43 章

### A-38　Control Tower vs Organizations + StackSets（自建）；AFT vs CfCT

**一句話差異**：Control Tower 用最少營運負擔建立多帳號 landing zone 與 guardrail；自建則用 Organizations + StackSets，彈性高但負擔最大。開帳號客製化方面，AFT 給 Terraform 團隊，CfCT 給 CloudFormation 團隊。

| 需求 | 選擇 |
|---|---|
| 最少營運負擔建立多帳號基線 | Control Tower + Account Factory |
| Terraform、GitOps、大量帳號 | Account Factory for Terraform（AFT） |
| CloudFormation 團隊，所有 OU 持續套用一致資源與 SCP | Customizations for Control Tower（CfCT） |
| 只需把一組資源自動部署到 OU 的所有帳號 | StackSets service-managed + automatic deployment |
| 部署前擋下不合規的 CloudFormation | Proactive control（CloudFormation hooks） |

**題目看到什麼選哪個**

- 「LEAST operational overhead 建立 landing zone」→ Control Tower。
- 「既有 Organization 導入 Control Tower」→ 在既有 Organization 建 landing zone，register OU／enroll account。
- 「被邀請加入的帳號，管理帳號無法 AssumeRole 進去」→ 手動建立信任 management account 的 role。

**出處**：第 14 章、第 40 章

---

## Compute：運算

### A-39　On-Demand vs Savings Plans／RI vs Spot vs On-Demand Capacity Reservation

**一句話差異**：Savings Plans 與 RI 是「折扣」不保留容量；Spot 最便宜但可被收回；Capacity Reservation 保證容量但沒有折扣。

| 維度 | On-Demand | Savings Plans／Regional RI | Spot | Capacity Reservation |
|---|---|---|---|---|
| 承諾 | 無 | 1／3 年 | 無 | 無（future-dated 有最短承諾） |
| 折扣 | 無 | 高 | 最高約 90% | 無（可搭配 SP／Regional RI） |
| 保留容量 | 否 | 否（只有 zonal RI 有） | 否 | 是 |
| 中斷風險 | 無 | 無 | 2 分鐘通知後收回 | 無 |

**題目看到什麼選哪個**

- 「可中斷的批次、彈性工作、最低成本」→ Spot（多 type、多 AZ、`price-capacity-optimized`）。
- 「指定 AZ 必須保證容量」→ On-Demand Capacity Reservation（或 zonal RI）。
- 「穩定 baseline 一年以上」→ Savings Plans（先 rightsizing）。
- 選項「設很高的 Spot 價格就不會被中斷」→ 錯。

**出處**：第 17 章、第 39 章

### A-40　Compute Savings Plans vs EC2 Instance Savings Plans vs Standard RI vs Convertible RI

**一句話差異**：Compute SP 最有彈性，涵蓋 Fargate 與 Lambda；EC2 Instance SP 與 Standard RI 折扣最高但綁 family 與 Region；Convertible RI 可 exchange、折扣較低。

| 維度 | Compute SP | EC2 Instance SP | Standard RI | Convertible RI |
|---|---|---|---|---|
| 最高折扣 | 約 66% | 約 72% | 約 72% | 約 66% |
| 涵蓋 | 任何 family、Region、Fargate、Lambda | 指定 family 與 Region 的 EC2 | 指定屬性 | 可 exchange 成其他屬性 |
| 彈性 | 最高 | 中 | 低（可在 Marketplace 轉賣） | 中高 |
| 容量保證 | 無 | 無 | 僅 zonal RI | 僅 zonal RI |

**題目看到什麼選哪個**

- 「會換 instance family、換 Region，或也用 Fargate／Lambda」→ Compute Savings Plans。
- 「穩定使用同一 family、同一 Region，要最大折扣」→ EC2 Instance SP 或 Standard RI。
- 「持續使用 Lambda 想降費用」→ Compute Savings Plans（EC2 Instance SP 與 RI 不涵蓋 Lambda）。

**出處**：第 17 章、第 39 章、第 19 章、第 43 章

### A-41　Dedicated Hosts vs Dedicated Instances

**一句話差異**：Dedicated Hosts 給你整台實體主機與 socket／core 可見性，解決 BYOL 授權；Dedicated Instances 只保證硬體不與其他帳號共用，沒有 host 可見性。

| 維度 | Dedicated Hosts | Dedicated Instances |
|---|---|---|
| 單位 | 整台實體主機 | Instance |
| Socket／core 可見性 | 有 | 無 |
| Host affinity | 有 | 無 |
| 典型用途 | 依 socket／core 計費的 BYOL（Windows Server 無 SA、Oracle 等） | 法規要求硬體不共用，無授權需求 |

**題目看到什麼選哪個**

- 「以 socket／core 計費的授權、BYOL」→ Dedicated Hosts（+ License Manager）。
- 「法規要求不與其他帳號共用硬體、無授權需求」→ Dedicated Instances。
- 選項「Dedicated Instances 解決 socket 授權」→ 錯。

**出處**：第 17 章、第 44 章

### A-42　Cluster vs Spread vs Partition placement group

**一句話差異**：Cluster 把機器擠在一起換最低延遲；spread 把少數關鍵機器分散在不同硬體；partition 把大型分散式系統依機架分組。

| 維度 | Cluster | Spread | Partition |
|---|---|---|---|
| 目的 | 節點間最低延遲、最高頻寬 | 少數關鍵 instance 不同時故障 | 大型分散式系統機架感知 |
| 範圍 | 單一 AZ | 可跨 AZ，每 AZ 最多 7 台 | 可跨 AZ，每 AZ 最多 7 個 partition |
| 可用性 | 故障範圍更大 | 最高 | 分組隔離 |
| 典型工作 | HPC、MPI（+ EFA） | 小型關鍵叢集 | Kafka、HDFS、Cassandra |

**題目看到什麼選哪個**

- 「HPC、節點間低延遲」→ Cluster + EFA。
- 「Kafka、HDFS 機架感知」→ Partition。
- 「少量關鍵 instance 不能同時故障」→ Spread。
- 選項「cluster placement group 提升可用性」→ 錯。

**出處**：第 17 章

### A-43　Target tracking vs Step vs Simple vs Scheduled vs Predictive scaling

**一句話差異**：Target tracking 維持一個與容量成比例的指標；step 依超標程度分段；simple 有 cooldown、反應慢；scheduled 對已知時間的尖峰；predictive 依歷史週期提前擴展。

| 政策 | 適用 | 注意 |
|---|---|---|
| Target tracking | 不可預測流量的首選 | Metric 必須隨機器數成比例下降（CPU、每台請求數、每台 backlog） |
| Step scaling | 劇烈飆升要加大力道 | 要自己定義分段 |
| Simple scaling | 很少是最佳答案 | Cooldown 期間不再擴展 |
| Scheduled action | 已知時間的活動、開賣 | 要提高 min，不只是 desired |
| Predictive scaling | 有規律週期與足夠歷史、開機慢 | 先用 forecast only 驗證 |

**題目看到什麼選哪個**

- 「每天／每週固定時間的尖峰」→ Scheduled action（提高 min）。
- 「規律週期、開機慢、要提前準備」→ Predictive scaling。
- 「維持平均 CPU 在 50%」→ Target tracking。
- 「SQS worker 依 queue 長度擴展」→ Backlog per instance custom metric + target tracking。

**出處**：第 18 章

### A-44　Health check grace period vs Default warmup vs Lifecycle hook vs Scale-in protection vs Standby

**一句話差異**：Grace period 讓新機器暫不被判不健康；warmup 讓新機器的指標暫不計入；lifecycle hook 在開機後或終止前做事；scale-in protection 讓忙碌的機器不被縮掉；standby 暫時把機器移出服務。

| 需求 | 工具 |
|---|---|
| 新機器開機後一直被判不健康而反覆替換 | 延長 health check grace period |
| 新機器的 metric 還不穩定，別算進 scaling | Default instance warmup |
| 開機前要做準備、被關前要上傳 log | Launch／termination lifecycle hook |
| 正在做長工作的機器不要被縮掉 | Instance scale-in protection |
| 暫時把一台拿出來除錯 | Standby |

**題目看到什麼選哪個**

- 「ALB 顯示 unhealthy，但 instance 沒被替換」→ ASG health check type 改為 ELB（這不是以上任何一項）。
- 「被縮減前要完成工作」→ Termination lifecycle hook。
- 「更新 AMI 並滾動替換整個機群」→ Instance refresh。

**出處**：第 18 章

### A-45　Lambda reserved concurrency vs provisioned concurrency vs SnapStart

**一句話差異**：Reserved concurrency 是「保留額度也是上限」，不消除 cold start；provisioned concurrency 預先初始化環境，消除 cold start；SnapStart 用快照縮短（Java 等）初始化時間，成本較低。

| 維度 | Reserved concurrency | Provisioned concurrency | SnapStart |
|---|---|---|---|
| 作用 | 保證可用額度並設上限 | 預先暖好的執行環境 | 從快照還原初始化狀態 |
| 消除 cold start | 不會 | 會 | 縮短 |
| 額外費用 | 不另外收費 | 有 | — |
| 典型用途 | Bulkhead、保護下游資料庫 | 穩定低延遲 API | Java function cold start 長 |

**題目看到什麼選哪個**

- 「重要 function 不被其他 function 搶走容量」→ Reserved concurrency。
- 「限制同時執行數以保護資料庫」→ Reserved concurrency 或 SQS ESM maximum concurrency；加 RDS Proxy。
- 「消除 cold start、穩定低延遲」→ Provisioned concurrency（設在 version／alias）。
- 「Java cold start 長、想低成本改善」→ SnapStart。

**出處**：第 19 章、第 33 章、第 35 章

### A-46　Lambda destinations vs Lambda 非同步 DLQ vs SQS redrive（DLQ）

**一句話差異**：Destinations 與非同步 DLQ 只適用於「非同步呼叫」；SQS 觸發的 function 是 event source mapping，失敗訊息要由 SQS 自己的 redrive policy 送到 DLQ。

| 維度 | Lambda destinations | Lambda 非同步 DLQ | SQS redrive policy |
|---|---|---|---|
| 適用呼叫方式 | 非同步（S3、SNS、EventBridge 觸發） | 非同步 | Event source mapping（SQS） |
| 成功也通知 | 可以（on-success） | 不行 | 不適用 |
| 保存內容 | 事件 + 錯誤資訊 | 事件 | 原始訊息 |
| 設定位置 | Function | Function | Source queue |

**題目看到什麼選哪個**

- 「非同步呼叫失敗要保留事件與錯誤，成功也要通知」→ Destinations。
- 「SQS 觸發的 function 失敗訊息要保留」→ SQS 的 DLQ（`maxReceiveCount`）。
- 「一批 SQS 訊息只有幾筆失敗」→ `ReportBatchItemFailures`。
- 「Kinesis 一筆壞資料卡住 shard」→ Bisect batch、maximum retry、on-failure destination。

**出處**：第 19 章、第 32 章

### A-47　API Gateway REST API vs HTTP API vs WebSocket API vs AppSync vs Lambda function URL

**一句話差異**：REST API 功能最完整（usage plan、快取、WAF、private endpoint）；HTTP API 便宜、適合 JWT + Lambda proxy；WebSocket API 做雙向推播；AppSync 做 GraphQL；function URL 只是單一函式的 HTTPS 端點。

| 選項 | 最適合 | 缺少 |
|---|---|---|
| REST API | 對外 API、夥伴額度、快取、request validation、private API | 單價較高；整合逾時預設 29 秒 |
| HTTP API | 一般 Lambda／HTTP proxy、JWT 驗證、成本敏感 | Usage plans、caching、WAF、private endpoint |
| WebSocket API | 聊天、即時通知、server 主動推播 | 要自行管理 connection ID |
| AppSync | GraphQL、多資料來源、即時訂閱、離線同步 | 需學 GraphQL 與 resolver |
| Function URL | 單一函式 webhook、內部工具 | 限流、API key、自訂授權器、快取 |

**題目看到什麼選哪個**

- 「每個夥伴有自己的額度、API key」→ REST API usage plans。
- 「只要 JWT 驗證與 Lambda proxy、成本最低」→ HTTP API + JWT authorizer。
- 「API 只能從 VPC 內部存取」→ Private REST API + `execute-api` interface endpoint。
- 「伺服器主動推播、聊天室」→ WebSocket API。
- 「GraphQL、即時訂閱」→ AppSync。
- 選項「HTTP API 加上 usage plan 或 WAF」→ 錯。

**出處**：第 20 章、第 49 章

### A-48　IAM authorizer vs Cognito authorizer vs Lambda authorizer vs API key

**一句話差異**：IAM（SigV4）給 AWS 內的程式；Cognito／JWT authorizer 給已登入的使用者；Lambda authorizer 給自訂 token 或要查資料庫決定權限；API key 只用來識別 client 與套用 usage plan，不是授權。

| 機制 | 驗證對象 | 需要寫程式 | 典型用途 |
|---|---|---|---|
| IAM authorization | AWS principal（SigV4） | 否 | 服務對服務、跨帳號 |
| Cognito user pool／JWT authorizer | 使用者 JWT | 否 | 已在 Cognito 登入的 App |
| Lambda authorizer | 任意 token | 是（可快取結果） | 自訂 token、呼叫舊系統驗證 |
| API key | Client 識別 | 否 | Usage plan 計量與限流 |

**題目看到什麼選哪個**

- 「使用者已在 Cognito 登入、不寫程式驗證」→ Cognito authorizer（REST）／JWT authorizer（HTTP）。
- 「自訂 token、要查資料庫決定權限」→ Lambda authorizer。
- 「AWS 內的服務或跨帳號程式呼叫 API」→ IAM authorization + resource policy。
- 選項「用 API key 當身份驗證」→ 錯。

**出處**：第 20 章、第 49 章

### A-49　ECS vs EKS

**一句話差異**：ECS 是 AWS 專有、較簡單、control plane 免費；EKS 是標準 Kubernetes，適合已有 K8s 工具鏈或需要可移植性，但營運負擔較高。

| 維度 | ECS | EKS |
|---|---|---|
| Orchestrator | AWS 專有 | Kubernetes |
| Control plane 費用 | 免費 | 每 cluster 按小時 |
| 營運負擔 | 較低 | 較高（版本升級、附加元件） |
| 應用程式身份 | Task role | IRSA 或 EKS Pod Identity |
| 節點擴展 | Capacity provider + managed scaling | Cluster Autoscaler 或 Karpenter |

**題目看到什麼選哪個**

- 「跑 container、不想管伺服器、沒提 Kubernetes」→ ECS on Fargate。
- 「已有 Kubernetes、Helm、operator、跨雲可移植」→ EKS。
- 「EKS 節點擴展慢、想自動選 Spot 與多規格」→ Karpenter。

**出處**：第 21 章、第 46 章

### A-50　Fargate vs EC2 launch type

**一句話差異**：Fargate 不用管節點、每個 task 獨立隔離；EC2 launch type 自管節點，可用 GPU、privileged container、DaemonSet，高利用率時可能更便宜。

| 維度 | Fargate | EC2（ECS／EKS 節點） |
|---|---|---|
| 管理伺服器 | 不需要 | 需要（AMI、patch、擴展） |
| GPU、privileged、DaemonSet | 不支援 | 支援 |
| 計費 | Task 的 vCPU／記憶體秒數 | 依 instance，可提高裝箱密度 |
| 折扣 | Fargate Spot、Compute SP | Spot、RI、SP |

**題目看到什麼選哪個**

- 「LEAST operational overhead」→ Fargate。
- 「GPU、privileged container、每台主機一個 agent」→ EC2 launch type。
- 「可中斷的 worker、降低 container 成本」→ Fargate Spot。
- 選項「Fargate 是獨立的 orchestrator」→ 錯，它是 ECS／EKS 的運算選項。

**出處**：第 21 章、第 46 章

### A-51　ECS task role vs task execution role

**一句話差異**：Task role 是「應用程式」呼叫 AWS 服務用的權限；execution role 是「ECS agent」拉 image、取 secret、寫 log 用的權限。

| 維度 | Task role | Execution role |
|---|---|---|
| 給誰用 | Container 裡的應用程式 | ECS agent／Fargate 平台 |
| 典型權限 | 讀 S3、寫 DynamoDB | 拉 ECR image、讀 Secrets Manager、寫 CloudWatch Logs |
| 錯誤症狀 | 程式呼叫 AWS API 被拒 | `CannotPullContainerError`、無法取得 secret、無法寫 log |

**題目看到什麼選哪個**

- 「Container 內的程式呼叫 AWS 服務的權限」→ Task role（EKS 用 IRSA 或 Pod Identity）。
- 「無法拉 image、無法取得 secret」→ Execution role（並檢查網路：ECR `ecr.api`、`ecr.dkr` interface endpoint + S3 gateway endpoint）。
- 選項「把應用程式權限放在 execution role 或節點 instance role」→ 錯。

**出處**：第 21 章

### A-52　Lambda vs Fargate vs AWS Batch vs Elastic Beanstalk

**一句話差異**：Lambda 給 15 分鐘內的事件驅動工作；Fargate 給長時間執行的 container 服務；Batch 給大量獨立批次工作的排隊與重試；Beanstalk 給上傳程式碼就部署的傳統 web 應用。

| 維度 | Lambda | Fargate（ECS） | AWS Batch | Elastic Beanstalk |
|---|---|---|---|---|
| 執行時間 | 最長 15 分鐘 | 不限 | 不限 | 不限 |
| 抽象層級 | Function | Container task | 批次 job | 應用程式環境 |
| 擴展 | 依事件自動 | Service auto scaling | 依佇列自動配置 compute environment | 自動建 ELB 與 ASG |
| 典型用途 | S3 事件、API、輕量處理 | 微服務、長時間 worker | 大量獨立運算、搭配 Spot | 不想管基礎設施的 web 應用 |

**題目看到什麼選哪個**

- 「上傳到 S3 後自動處理、流量不規則」→ Lambda。
- 「處理時間超過 15 分鐘」→ Fargate task、Batch，或 Step Functions 拆步驟。
- 「大量獨立批次、Spot、自動排隊與重試」→ AWS Batch。
- 「上傳程式碼就部署、自動建 ELB 與 ASG」→ Elastic Beanstalk。
- App Runner 已不接受新客戶，不要當成新專案的推薦方案。

**出處**：第 19 章、第 21 章

---

## Storage：儲存

### A-53　EBS vs EFS vs S3

**一句話差異**：EBS 是掛在單台 EC2、綁定單一 AZ 的 block 磁碟；EFS 是多台 Linux 跨 AZ 共享的 NFS 檔案系統；S3 是用 HTTP API 存取、容量無上限的物件儲存。

| 維度 | EBS | EFS | S3 |
|---|---|---|---|
| 介面 | Block | NFS v4 | HTTP API |
| 共享 | 否（Multi-Attach 例外） | 數千台 Linux | 任何程式 |
| 範圍 | 單一 AZ | Regional 或 One Zone | Regional |
| 容量 | 預先配置 | 自動擴縮 | 無上限 |
| 典型用途 | 開機磁碟、單機資料庫 | 網站共享內容、containers、Lambda | 圖片、影片、備份、data lake |

**題目看到什麼選哪個**

- 「多台 Linux 伺服器共用檔案、用檔案路徑存取」→ EFS。
- 「資料庫或開機磁碟、低延遲」→ EBS。
- 「大量圖片／影片、容量無上限」→ S3。
- 選項「EBS 可以跨 AZ 掛載」→ 錯，跨 AZ 要用 snapshot。

**出處**：第 4 章、第 24 章

### A-54　EBS vs Instance store

**一句話差異**：EBS 是持久的網路磁碟，stop 後資料還在；instance store 是主機上的本機磁碟，I/O 最高但 stop／terminate 後資料消失。

| 維度 | EBS | Instance store |
|---|---|---|
| 持久性 | 持久，獨立於 instance 生命週期 | Ephemeral |
| 效能 | 依 volume type | 最高本機 I/O |
| Snapshot | 支援 | 不支援 |
| 典型用途 | 不可遺失的資料 | 暫存、快取、可重建資料 |

**題目看到什麼選哪個**

- 「暫存、快取、可重建、最高 IOPS」→ Instance store。
- 「Stop／start 後本機資料不見了」→ 用的是 instance store。
- 選項「把唯一一份資料放在 instance store」→ 錯。

**出處**：第 17 章、第 24 章

### A-55　gp3 vs gp2 vs io2 Block Express vs st1 vs sc1

**一句話差異**：gp3 是預設首選、IOPS 與 throughput 可獨立調；io2 是關鍵資料庫的頂規 SSD；st1 是便宜的大量循序 HDD；sc1 是最便宜的冷資料 HDD；gp2 的 IOPS 綁容量，建議改 gp3。

| 類型 | 介質 | 特性 | 可開機 | 適合 |
|---|---|---|---|---|
| gp3 | SSD | 基準 3,000 IOPS、125 MiB/s，與容量無關，可另調 | 可 | 多數應用、中型資料庫 |
| gp2 | SSD | 每 GiB 3 IOPS，小 volume 靠 burst | 可 | 既有環境，建議遷移 |
| io2 Block Express | SSD | 最高 IOPS、低延遲、耐久度 99.999% | 可 | 核心交易資料庫 |
| st1 | HDD | 以 throughput 計，隨機小 I/O 很差 | 不可 | 日誌、ETL、大型循序 |
| sc1 | HDD | 每 GB 最便宜 | 不可 | 很少存取的冷資料 |

**題目看到什麼選哪個**

- 「一般 SSD、要獨立調 IOPS、比 gp2 便宜」→ gp3（Elastic Volumes 線上修改）。
- 「關鍵資料庫、持續高 IOPS、最高耐久度」→ io2 Block Express。
- 「大量循序讀取、要便宜」→ st1。
- 「很少存取、最低成本 block」→ sc1。
- 選項「st1／sc1 當開機磁碟」→ 錯。

**出處**：第 24 章、第 39 章

### A-56　EFS vs FSx for Windows vs FSx for Lustre vs FSx for ONTAP vs FSx for OpenZFS

**一句話差異**：依「協定與既有系統」選：Linux NFS 共享選 EFS；SMB／AD 選 FSx for Windows；HPC 平行檔案系統選 Lustre；NetApp 或多協定選 ONTAP；ZFS 或極低延遲 NFS 選 OpenZFS。

| 服務 | 協定 | 可用範圍 | 代表特色 |
|---|---|---|---|
| EFS | NFS v4 | Regional 或 One Zone | 自動擴縮、lifecycle、access point |
| FSx for Windows File Server | SMB | Single-AZ 或 Multi-AZ | AD、NTFS ACL、DFS |
| FSx for Lustre | Lustre | 單一 AZ | S3 整合、極高平行 throughput |
| FSx for NetApp ONTAP | NFS、SMB、iSCSI | Single-AZ 或 Multi-AZ | SnapMirror、FlexClone、多協定 |
| FSx for OpenZFS | NFS | Single-AZ 或 Multi-AZ | 超低延遲、ZFS snapshot／clone |

**題目看到什麼選哪個**

- 「Windows、SMB、NTFS ACL、Active Directory」→ FSx for Windows（Multi-AZ 高可用）。
- 「HPC、ML 訓練、資料在 S3」→ FSx for Lustre。
- 「NetApp、SnapMirror、NFS 與 SMB 同時」→ FSx for ONTAP。
- 「多台 Linux、跨 AZ、免容量規劃」→ EFS。
- 選項「EFS 給 Windows 使用」或「FSx for Lustre 是多 AZ」→ 錯。

**出處**：第 24 章

### A-57　S3 Standard-IA vs One Zone-IA vs Glacier Instant Retrieval vs Intelligent-Tiering

**一句話差異**：四者都能毫秒讀取；Standard-IA 給約每月一次讀取，One Zone-IA 只存一個 AZ、給可重建資料，Glacier IR 給每季或更少讀取，Intelligent-Tiering 給存取模式未知的資料。

| 類別 | 存放 AZ | 最短存放 | 最小計費大小 | 適合 |
|---|---|---|---|---|
| Standard-IA | ≥ 3 | 30 天 | 128 KB | 不常讀、不可重建 |
| One Zone-IA | 1 | 30 天 | 128 KB | 可重新產生的資料 |
| Glacier Instant Retrieval | ≥ 3 | 90 天 | 128 KB | 每季或更少讀取、仍要毫秒 |
| Intelligent-Tiering | ≥ 3 | 無 | 無（< 128 KB 不自動分層） | 存取模式未知或會變；有監控費 |

**題目看到什麼選哪個**

- 「存取模式未知、會變化、不想管理」→ Intelligent-Tiering。
- 「不常讀、要毫秒、不可重建」→ Standard-IA（每季以下讀：Glacier IR）。
- 「可重新產生、最低成本、毫秒讀取」→ One Zone-IA。
- 「短期存放或頻繁讀取」→ 留在 Standard，IA 類別可能更貴。

**出處**：第 23 章

### A-58　Glacier Instant Retrieval vs Glacier Flexible Retrieval vs Glacier Deep Archive

**一句話差異**：Instant Retrieval 毫秒讀取；Flexible Retrieval 要 restore，分鐘到小時；Deep Archive 最便宜，要等 12 到 48 小時。

| 維度 | Glacier IR | Glacier Flexible Retrieval | Glacier Deep Archive |
|---|---|---|---|
| 取得時間 | 毫秒 | Expedited 1–5 分鐘、Standard 3–5 小時、Bulk 5–12 小時 | Standard 12 小時內、Bulk 48 小時內 |
| 最短存放 | 90 天 | 90 天 | 180 天 |
| 相對儲存費 | 低 | 很低 | 最低 |
| 適合 | 每季讀取、要立即可用 | 每年一兩次、可等 | 法規長期保存、幾乎不讀 |

**題目看到什麼選哪個**

- 「長期保存、幾乎不讀、可等 12–48 小時、最低成本」→ Deep Archive。
- 「封存資料偶爾要在數分鐘內取回」→ Flexible Retrieval + Expedited。
- 「每季查詢一次，仍要毫秒」→ Glacier IR。
- 「raw 資料放 Deep Archive 後要用 Athena 直接查」→ 不行，要先 restore。

**出處**：第 23 章、第 52 章

### A-59　Versioning vs S3 Replication（CRR／SRR）vs AWS Backup

**一句話差異**：Versioning 讓你在同一個 bucket 復原誤刪與覆寫；replication 在另一個 bucket（可跨 Region、跨帳號）建立非同步副本；AWS Backup 提供跨服務的集中備份政策與保存期限。

| 維度 | Versioning | CRR／SRR | AWS Backup |
|---|---|---|---|
| 防誤刪 | 可以 | 不一定（指定版本刪除不複寫；delete marker 預設不複寫） | 可以 |
| 防 Region 災難 | 不能 | CRR 可以（非同步，不是零 RPO） | 跨 Region copy 可以 |
| 防帳號被入侵 | 不能 | 跨帳號複寫 + 目的地 Object Lock | 跨帳號 copy + Vault Lock |
| 既有物件 | 不適用 | 不會自動複寫，用 Batch Replication | 依備份計畫 |

**題目看到什麼選哪個**

- 「誤刪或誤覆寫要能復原」→ Versioning。
- 「跨 Region DR 副本」→ CRR（兩邊都要 versioning）；要 15 分鐘 SLA → Replication Time Control。
- 「既有 object 沒被複寫」→ S3 Batch Replication。
- 「集中備份政策、跨服務、跨帳號」→ AWS Backup。

**出處**：第 22 章、第 23 章、第 34 章

### A-60　S3 Storage Lens vs Storage Class Analysis vs S3 Inventory vs Batch Operations

**一句話差異**：Storage Lens 看「整個組織」的使用趨勢與建議；Storage Class Analysis 告訴你「某 prefix 何時該轉 IA」；Inventory 列出「具體有哪些 object」；Batch Operations 對「數百萬個 object 執行同一件事」。

| 工具 | 回答的問題 | 輸出 |
|---|---|---|
| Storage Lens | 組織哪裡在長、哪裡有風險 | 儀表板、指標、建議 |
| Storage Class Analysis | 這個 prefix 何時該轉 IA | 轉換建議 |
| S3 Inventory | 有哪些 object、它們的狀態 | 每日／每週清單檔 |
| Batch Operations | 對大量 object 執行同一動作 | 作業 + completion report |

**題目看到什麼選哪個**

- 「找出所有未加密或複寫失敗的 object」→ Inventory + Athena。
- 「對數百萬個 object restore、複製、改 tag」→ Batch Operations（manifest 用 Inventory）。
- 「整個組織的 S3 使用與最佳化建議」→ Storage Lens。

**出處**：第 23 章

### A-61　Bucket policy vs IAM policy vs ACL vs S3 Access Points

**一句話差異**：IAM policy 說「這個身份能做什麼」；bucket policy 說「誰能存取這個 bucket」，是跨帳號與強制條件的主要工具；ACL 是舊機制，新 bucket 預設停用；Access Points 把一個大 bucket 拆成多個有各自 policy 的入口。

| 機制 | 控制對象 | 能拒絕 | 適合 |
|---|---|---|---|
| IAM policy | User／role 能做什麼 | 能 | 同帳號存取 |
| Bucket policy | 誰能存取 bucket | 能 | 跨帳號、強制 HTTPS／VPC、CloudFront OAC |
| ACL | 個別 bucket／object | 不能 | 舊系統相容，建議停用（Bucket owner enforced） |
| Access Points | 經由某入口的存取 | 能 | 多團隊共用 bucket、VPC-only 入口 |

**題目看到什麼選哪個**

- 「強制 HTTPS」→ Bucket policy Deny `aws:SecureTransport = false`。
- 「跨帳號上傳的 object 擁有權混亂」→ Object Ownership：Bucket owner enforced。
- 「多團隊共用 bucket、policy 太大」→ Access Points。
- 「只能從 VPC 內存取」→ Gateway endpoint + `aws:SourceVpce`，或 VPC-only Access Point。

**出處**：第 22 章

### A-62　S3 File Gateway vs Volume Gateway（cached／stored）vs Tape Gateway

**一句話差異**：File Gateway 讓地端用 NFS／SMB 寫成 S3 物件；Volume Gateway 提供 iSCSI 磁碟（cached 本體在雲端、stored 本體在地端）；Tape Gateway 讓備份軟體把虛擬磁帶寫到 S3 與 Glacier。

| 類型 | 地端介面 | AWS 端儲存 | 本體在哪 |
|---|---|---|---|
| S3 File Gateway | NFS、SMB | S3（一檔案一物件） | S3，地端快取 |
| Volume Gateway cached | iSCSI | AWS 儲存 + EBS snapshot | 雲端，常用資料快取在地端 |
| Volume Gateway stored | iSCSI | EBS snapshot | 地端，非同步備份到 AWS |
| Tape Gateway | iSCSI VTL | S3 → Glacier／Deep Archive | 雲端 |

**題目看到什麼選哪個**

- 「地端應用用 NFS／SMB，資料要變成 S3 物件」→ S3 File Gateway。
- 「iSCSI、地端空間不足」→ Volume Gateway cached。
- 「iSCSI、地端要低延遲存取整份資料」→ Volume Gateway stored。
- 「既有備份軟體、實體磁帶、長期封存」→ Tape Gateway + Deep Archive。
- 選項「用 S3 API 讀 Volume Gateway 的資料」→ 錯。

**出處**：第 25 章

### A-63　DataSync vs Storage Gateway vs Transfer Family vs Snowball Edge

**一句話差異**：DataSync 做一次性搬遷或排程同步；Storage Gateway 做長期混合存取；Transfer Family 讓外部夥伴用 SFTP／FTPS／FTP／AS2 交換檔案；Snowball Edge 是網路不夠時的離線搬運（不開放新客戶）。

| 維度 | DataSync | Storage Gateway | Transfer Family | Snowball Edge |
|---|---|---|---|---|
| 目的 | 搬遷、定期同步 | 長期 hybrid 存取 | 夥伴檔案交換 | 離線大量搬運 |
| 地端介面 | Agent 讀 NFS／SMB／HDFS／物件儲存 | NFS、SMB、iSCSI | SFTP、FTPS、FTP、AS2 | 裝置 |
| AWS 端 | S3、EFS、FSx | S3、EBS snapshot、Glacier | S3、EFS | S3（不能直接匯入 Glacier） |
| 現況 | 一般可用 | 一般可用 | 一般可用 | 不再提供給新客戶 |

**題目看到什麼選哪個**

- 「NFS／SMB 大量檔案搬到 S3／EFS／FSx，要排程、增量、驗證」→ DataSync。
- 「Windows 檔案伺服器搬到 FSx、保留 NTFS 權限」→ DataSync。
- 「夥伴用 SFTP 上傳到 S3、不想管伺服器」→ Transfer Family。
- 「數十 TB 到 PB、網路要好幾週」→ 先算天數；考題常見答案為 Snowball Edge。
- 「資料庫線上搬遷」→ 都不是，用 DMS。

**出處**：第 25 章、第 45 章

---

## Database：資料庫與分析

### A-64　RDS Multi-AZ DB instance vs Multi-AZ DB cluster vs Read replica

**一句話差異**：Multi-AZ DB instance 是不可讀的同步 standby，用來高可用；Multi-AZ DB cluster 有兩台可讀 reader、failover 更快；read replica 是非同步、可讀、要手動 promote，用來擴展讀取或跨 Region。

| 維度 | Multi-AZ DB instance | Multi-AZ DB cluster | Read replica |
|---|---|---|---|
| 複寫 | 同步 | 半同步（至少一台 reader 確認） | 非同步 |
| Standby 可讀 | 否 | 是（reader endpoint） | 是 |
| Failover | 自動，通常 60–120 秒 | 自動，通常 35 秒以內 | 手動 promote |
| 引擎 | 所有 RDS 引擎 | MySQL、PostgreSQL | 依引擎 |
| 用途 | 高可用 | 高可用 + 讀取 | 讀取擴展、跨 Region DR |

**題目看到什麼選哪個**

- 「AZ 故障自動切換、不遺失已 commit 資料」→ Multi-AZ。
- 「報表拖慢主資料庫、可接受稍舊資料」→ Read replica。
- 「需要可讀 standby 且 failover 更快（MySQL／PG）」→ Multi-AZ DB cluster。
- 選項「Multi-AZ standby 分擔讀取」或「read replica 自動 failover」→ 錯。

**出處**：第 26 章、第 34 章

### A-65　RDS vs Aurora vs RDS Custom vs EC2 自建

**一句話差異**：RDS 給標準引擎與成本敏感；Aurora 給高讀取、快速 failover、跨 Region；RDS Custom 給需要 OS 存取的 Oracle／SQL Server；EC2 自建只在受管服務做不到時才選。

| 維度 | RDS | Aurora | RDS Custom | EC2 自建 |
|---|---|---|---|---|
| 引擎 | 多種 | MySQL／PostgreSQL 相容 | Oracle、SQL Server | 任何 |
| OS 存取 | 無 | 無 | 有 | 完全控制 |
| 讀取擴展 | Read replica | 最多 15 個 replica、共用儲存 | 依引擎 | 自己架 |
| 跨 Region | Cross-Region read replica | Global Database | 依引擎 | 自己做 |
| 營運負擔 | 低 | 最低 | 中 | 最高 |

**題目看到什麼選哪個**

- 「大量讀取擴展、秒級 failover、跨 Region 秒級 RPO」→ Aurora。
- 「負載難預測、間歇使用」→ Aurora Serverless v2。
- 「需要在資料庫主機安裝 agent（Oracle／SQL Server）」→ RDS Custom。
- 「Oracle EE」→ RDS for Oracle BYOL（License Included 只有 SE2）。
- 選項「Aurora 另外開啟 Multi-AZ standby」→ 錯，Aurora 高可用就是其他 AZ 的 replica。

**出處**：第 26 章、第 29 章、第 46 章

### A-66　Aurora Global Database vs Cross-Region read replica vs DynamoDB global tables

**一句話差異**：Aurora Global Database 在儲存層跨 Region 複寫、RPO 秒級、只有一個寫入 Region；cross-Region read replica 是引擎層非同步複寫、較便宜；DynamoDB global tables 是多 Region 都能寫入的 active-active。

| 維度 | Aurora Global Database | Cross-Region read replica | DynamoDB global tables |
|---|---|---|---|
| 寫入 Region | 一個 | 一個 | 多個（MREC；強一致評估 MRSC） |
| 典型 RPO／RTO | RPO 約 1 秒、RTO 約 1 分鐘 | 分鐘級 promote + 切換 | 多 Region 同時服務 |
| 計畫內切換 | Switchover（RPO 0） | 手動 | 不需要 |
| 衝突 | 無（單一 writer） | 無 | 預設 last writer wins |

**題目看到什麼選哪個**

- 「跨 Region 關聯式資料庫、RPO 秒級、RTO 約一分鐘」→ Aurora Global Database。
- 「計畫內 Region 切換且不能遺失資料」→ Aurora Global switchover。
- 「多 Region active-active、兩邊都要寫」→ DynamoDB global tables。
- 「限量庫存不可超賣」→ 不要用 global tables 雙寫，要單一 writer 的原子更新。
- 「多 Region 都要寫入、跨 Region 強一致、RPO 0 的 key-value 資料」→ DynamoDB MRSC（剛好三個 Region、不支援 transactions）。

**出處**：第 26 章、第 27 章、第 34 章、第 48 章、第 42 章

### A-67　RDS PITR vs Aurora Backtrack vs Manual snapshot

**一句話差異**：PITR 把資料庫還原到某個時間點，但建立的是新 instance；Backtrack 是 Aurora MySQL 專屬的原地倒轉；manual snapshot 用於超過 35 天的長期保存。

| 維度 | PITR | Backtrack | Manual snapshot |
|---|---|---|---|
| 還原方式 | 建立新 instance／cluster | 原地倒轉 | 從 snapshot 建立新 instance |
| 適用 | RDS 與 Aurora | 只有 Aurora MySQL | RDS 與 Aurora |
| 保存期 | Automated backup 保留期（最長 35 天） | 依 backtrack window | 手動刪除前一直保留 |

**題目看到什麼選哪個**

- 「誤刪資料，回到某個時間點」→ PITR（應用程式要改連線）。
- 「Aurora MySQL 誤操作，幾分鐘內原地復原」→ Backtrack。
- 「資料要保存超過 35 天」→ Manual snapshot 或 AWS Backup。

**出處**：第 26 章

### A-68　DynamoDB vs RDS／Aurora

**一句話差異**：DynamoDB 給存取模式固定、以 key 查詢、規模極大且要穩定低延遲的工作；RDS／Aurora 給需要 JOIN、臨時查詢與完整 ACID 交易的工作。

| 維度 | DynamoDB | RDS／Aurora |
|---|---|---|
| 查詢 | 以 key 為主；臨時查詢與 JOIN 不適合 | 任意 SQL、JOIN |
| 擴展 | 幾乎無限，on-demand 吸收暴增 | 要預先擴容，連線數受限 |
| Lambda 大量並行 | 無連線問題 | 需要 RDS Proxy |
| 單筆大小 | 400 KB（大物件放 S3） | 較大 |
| 交易 | TransactWriteItems 最多 100 個動作 | 完整 ACID |

**題目看到什麼選哪個**

- 「購物車、session、流量可能瞬間放大百倍」→ DynamoDB。
- 「複雜 JOIN、報表、外鍵約束」→ RDS／Aurora。
- 「物件大於 400 KB」→ 存 S3，DynamoDB 存指標。

**出處**：第 26 章、第 27 章

### A-69　DynamoDB LSI vs GSI

**一句話差異**：LSI 與 table 共用 partition key、支援 strongly consistent、只能建表時建立；GSI 可用完全不同的 key、可事後新增，但只支援 eventually consistent。

| 維度 | LSI | GSI |
|---|---|---|
| Partition key | 與 table 相同 | 可不同 |
| 建立時機 | 只能建表時 | 隨時可新增 |
| 讀取一致性 | 支援 strongly consistent | 只有 eventually consistent |
| 容量 | 共用 table 容量 | 有自己的容量 |

**題目看到什麼選哪個**

- 「依另一個屬性查詢、table 已上線」→ GSI。
- 「同 partition key 不同排序、需要 strongly consistent」→ LSI（建表時）。
- 選項「對 GSI 做 strongly consistent read」或「事後新增 LSI」→ 錯。

**出處**：第 27 章

### A-70　DynamoDB on-demand vs provisioned capacity

**一句話差異**：On-demand 不用規劃容量，適合無法預測的流量；provisioned + auto scaling 適合穩定可預測的流量，搭配 reserved capacity 更便宜。

| 維度 | On-demand | Provisioned + auto scaling |
|---|---|---|
| 容量規劃 | 不需要 | 設定 RCU／WCU 與範圍 |
| 適合流量 | 新應用、尖峰暴增、不可預測 | 穩定、可預測 |
| 成本 | 單價較高 | 穩定時較低，可買 reserved capacity |
| Throttle | 熱分割或瞬間超過先前尖峰兩倍仍可能 | 超過設定容量 |

**題目看到什麼選哪個**

- 「流量無法預測、新應用」→ On-demand。
- 「穩定可預測的流量、降低成本」→ Provisioned + auto scaling。
- 「總容量充足但仍被 throttle」→ 熱分割，改高基數 partition key 或 write sharding（與模式無關）。

**出處**：第 27 章

### A-71　ElastiCache（Valkey／Redis OSS）vs Memcached vs MemoryDB vs DAX

**一句話差異**：Valkey／Redis OSS 是有資料結構、replica 與 failover 的快取；Memcached 是最簡單、多執行緒、沒有 failover 的快取；MemoryDB 是 Redis 相容的耐久主資料庫；DAX 是 DynamoDB 專用的微秒快取。

| 維度 | Valkey／Redis OSS | Memcached | MemoryDB | DAX |
|---|---|---|---|---|
| 本質 | In-memory 資料結構快取 | 簡單 key-value 快取 | 耐久 in-memory 資料庫 | DynamoDB 專用快取 |
| 耐久性 | 非同步複寫 + snapshot | 無 | 跨 AZ 交易日誌 | 不是真相來源 |
| 高可用 | Multi-AZ 自動 failover | 無 failover | Multi-AZ | 多節點跨 AZ |
| 典型用途 | Session、排行榜、查詢快取 | 簡單物件快取 | 以 Redis 結構當主資料庫 | DynamoDB 微秒讀取 |

**題目看到什麼選哪個**

- 「leaderboard、sorted sets」→ Valkey／Redis OSS。
- 「多執行緒、最簡單、資料可遺失」→ Memcached。
- 「Redis 相容且需要耐久、作為主要資料庫」→ MemoryDB。
- 「DynamoDB 微秒讀取、最少程式改動」→ DAX（只加速 eventually consistent read）。
- 選項「Memcached 提供 failover 或備份」→ 錯。
- 「其他 Region 要就近讀取同一份快取、只有一個 Region 寫入」→ ElastiCache Global Datastore（Valkey／Redis OSS，最多兩個 secondary Region）。

**出處**：第 28 章、第 29 章、第 42 章

### A-72　Read replica vs Cache

**一句話差異**：Cache 適合「同樣的查詢重複很多次」、要次毫秒；read replica 適合「各種不同的 SQL 查詢」、不想改應用程式的查詢邏輯。

| 維度 | ElastiCache | Read replica |
|---|---|---|
| 延遲 | 次毫秒 | 一般資料庫延遲 |
| 查詢彈性 | 只存你放進去的結果 | 可跑任意 SQL |
| 程式修改 | 需實作 cache-aside 等 | 只需改讀取 endpoint |
| 一致性 | 依 TTL 與失效策略 | 有複寫延遲 |

**題目看到什麼選哪個**

- 「相同查詢重複、資料庫 CPU 高、讀多寫少」→ ElastiCache + cache-aside。
- 「報表查詢拖慢交易資料庫」→ Read replica 或 Aurora reader endpoint。
- 「寫入壓垮資料庫」→ 兩者都不是，考慮 SQS 削峰或 scale up。

**出處**：第 28 章、第 35 章

### A-73　DocumentDB vs Neptune vs Keyspaces vs OpenSearch Service vs Timestream

**一句話差異**：依存取模式選：巢狀 JSON 文件與 MongoDB API 選 DocumentDB；多層關係走訪選 Neptune；Cassandra／CQL 選 Keyspaces；全文搜尋與日誌分析選 OpenSearch；時間範圍聚合選 Timestream。

| 服務 | 資料模型 | 介面 | 題目關鍵字 | 不適合 |
|---|---|---|---|---|
| DocumentDB | Document | MongoDB API | MongoDB 遷移、JSON | 需要完整 MongoDB 功能 |
| Neptune | Graph | Gremlin、openCypher、SPARQL | 朋友的朋友、詐欺環、推薦 | 一般 CRUD |
| Keyspaces | Wide-column | Cassandra CQL | 既有 Cassandra、serverless | JOIN、臨時查詢 |
| OpenSearch Service | 搜尋索引 | OpenSearch API | 全文、模糊比對、日誌、向量 | 作為唯一資料來源 |
| Timestream for InfluxDB | Time series | InfluxDB API | IoT、指標 | 交易資料 |

**題目看到什麼選哪個**

- 「MongoDB 相容、遷移既有 MongoDB」→ DocumentDB。
- 「社群網路、詐欺環、知識圖譜」→ Neptune。
- 「全文搜尋、相關度排序」→ OpenSearch。
- 「IoT 時間序列」→ Timestream（LiveAnalytics 已不開放新客戶，新工作負載用 Timestream for InfluxDB）。
- 「不可竄改的變更歷史」→ 舊題答案是 QLDB（已終止）；新架構用 Aurora PostgreSQL append-only + S3 Object Lock。

**出處**：第 29 章

### A-74　Athena vs Redshift vs EMR vs Glue ETL

**一句話差異**：Athena 是按掃描量計費的 serverless SQL，適合臨時查詢；Redshift 是高併發 BI 的資料倉儲；EMR 是可完全控制的 Spark／Hadoop；Glue ETL 是整合 Data Catalog 的 serverless ETL。

| 維度 | Athena | Redshift | EMR | Glue ETL |
|---|---|---|---|---|
| 類型 | Serverless SQL on S3 | MPP data warehouse（provisioned 或 Serverless） | 受管 Hadoop／Spark | Serverless ETL |
| 計費 | 每次查詢掃描量 | 節點小時或 RPU 秒 | EC2 + EMR 費用 | DPU 秒 |
| 最適合 | 臨時查詢、log 分析 | 穩定高併發 BI、複雜 JOIN | 遷移既有 Spark、控制框架版本 | 排程 ETL、只處理新資料 |
| 營運負擔 | 最低 | 中（Serverless 低） | 較高 | 低 |

**題目看到什麼選哪個**

- 「S3 上的資料、臨時 SQL、不想管基礎設施」→ Athena。
- 「PB 級、高併發 BI」→ Redshift；查 S3 冷資料 → Redshift Spectrum。
- 「分析負載不穩定、不想管 cluster」→ Redshift Serverless。
- 「既有 Hadoop／Spark 遷移」→ EMR（task node 用 Spot）。
- 「Serverless ETL、只處理新資料」→ Glue ETL + job bookmark。

**出處**：第 30 章

### A-75　Glue crawler vs Glue ETL job vs Glue DataBrew

**一句話差異**：Crawler 只探索 schema、寫 metadata，不轉換資料；ETL job 用程式轉換資料；DataBrew 讓業務分析師用視覺化介面清理資料。

| 維度 | Glue crawler | Glue ETL job | Glue DataBrew |
|---|---|---|---|
| 做什麼 | 探索 schema、發現分區 | 轉換格式、清理、合併 | 視覺化資料準備 |
| 是否改資料 | 否 | 是 | 是 |
| 使用者 | 資料工程師 | 資料工程師 | 不寫程式的分析師 |

**題目看到什麼選哪個**

- 「自動探索 schema、發現新分區」→ Crawler。
- 「CSV 轉 Parquet」→ ETL job（或串流時用 Firehose format conversion）。
- 「業務分析師清理資料、不寫程式」→ DataBrew。
- 選項「crawler 會轉換格式」→ 錯。

**出處**：第 30 章

### A-76　Lake Formation vs IAM／bucket policy vs Redshift data sharing

**一句話差異**：IAM／bucket policy 控制 bucket 與 prefix；Lake Formation 控制表、欄位、資料列層級權限並跨帳號共享 data lake；Redshift data sharing 在 Redshift 之間共享即時資料。三者都能做到「不複製資料」的共享，但層級不同。

| 需求 | 機制 |
|---|---|
| 控制誰能讀某個 bucket 或 prefix | IAM policy、bucket policy |
| 欄位、資料列、cell 層級權限，跨引擎一致 | Lake Formation（data filter、LF-Tags） |
| 跨帳號共享 data lake 表 | Lake Formation cross-account（RAM + resource link） |
| 跨帳號或跨 cluster 共享 warehouse 表 | Redshift data sharing |
| 儀表板依使用者顯示不同資料 | QuickSight row-level security |

**題目看到什麼選哪個**

- 「欄位層級、資料列層級權限、集中治理 data lake」→ Lake Formation。
- 「不複製資料，讓其他帳號的 Redshift 查詢」→ Redshift data sharing。
- 設好 Lake Formation 卻沒移除使用者直接讀 S3 的 IAM 權限 → 可被繞過。

**出處**：第 30 章、第 52 章

---

## Integration：整合與事件

### A-77　SQS vs SNS vs EventBridge vs Kinesis Data Streams vs Amazon MQ

**一句話差異**：SQS 把一份工作交給一個 worker；SNS 把一則訊息推給所有訂閱者；EventBridge 依內容把事件路由到目標；Kinesis 是可重讀的有序串流；Amazon MQ 是相容 JMS／AMQP／MQTT 的 broker。

| 維度 | SQS | SNS | EventBridge | Kinesis Data Streams | Amazon MQ |
|---|---|---|---|---|---|
| 模型 | Queue（pull） | Pub/sub（push） | Event bus + rules | Stream（pull，可重讀） | Broker |
| 一則訊息給 | 一個 consumer | 所有訂閱者 | 所有符合 rule 的 target | 每個 consumer 各讀一次 | 依 queue／topic |
| 保存 | 最多 14 天，處理後刪除 | 不保存 | 不保存，可 archive | 24 小時起，最長 365 天 | 依 broker |
| 典型用途 | 工作佇列、削峰 | 簡單 fan-out、SMS／email | 跨服務／跨帳號路由、SaaS 事件 | 點擊流、需要重播 | 遷移既有 JMS／AMQP 應用 |

**題目看到什麼選哪個**

- 「解耦、吸收流量尖峰」→ SQS。
- 「一個事件讓多個系統各自處理」→ SNS fan-out 到多個 SQS。
- 「SaaS 夥伴事件、AWS 服務事件、跨帳號」→ EventBridge。
- 「多個 consumer 讀同一份資料、可重播」→ Kinesis。
- 「既有 JMS／AMQP、不改程式」→ Amazon MQ。

**出處**：第 32 章、第 31 章

### A-78　SNS vs EventBridge

**一句話差異**：SNS 擅長高吞吐、低延遲地把同一則訊息推給很多訂閱者，並能直接送 SMS、email、推播；EventBridge 擅長依內容路由各種事件，並有 schema、archive／replay、SaaS 整合與跨帳號匯流。

| 維度 | SNS | EventBridge |
|---|---|---|
| 過濾 | Subscription filter policy | Event pattern（最豐富） |
| 事件來源 | 你的應用程式 | 你的應用、AWS 服務事件、SaaS partner |
| Replay | FIFO topic 可封存 | Archive + replay |
| 直接通知人 | SMS、email、行動推播 | 需經其他服務 |
| 排程 | 無 | EventBridge Scheduler |

**題目看到什麼選哪個**

- 「簡單 fan-out 或要送 SMS／email」→ SNS。
- 「依內容路由、SaaS 事件、修正 bug 後重新處理過去事件」→ EventBridge（archive + replay）。
- 「每筆資料在未來特定時間觸發」→ EventBridge Scheduler。
- 「從 DynamoDB Streams／SQS 過濾後送目標，不寫膠水 Lambda」→ EventBridge Pipes。

**出處**：第 32 章

### A-79　SQS Standard queue vs FIFO queue

**一句話差異**：Standard 吞吐幾乎無上限，但可能重複、不保證順序；FIFO 在同一個 message group 內保序，並對 5 分鐘內 producer 的重送去重，吞吐較受限。

| 維度 | Standard | FIFO |
|---|---|---|
| 順序 | 不保證 | 同一 message group 內有序 |
| 重複 | At-least-once | 5 分鐘去重視窗（只涵蓋 producer 重送） |
| 吞吐 | 幾乎無上限 | 受限，可用多個 group、batch、high throughput mode |
| 轉換 | — | 不能把 Standard 改成 FIFO，要新建 |

**題目看到什麼選哪個**

- 「訊息必須依序處理、不能重複」→ FIFO，group ID 設為需保序的實體 ID。
- 「FIFO 吞吐量不足」→ 增加 message group 數量、batch、high throughput mode。
- 選項「FIFO 保證 exactly-once，consumer 不需冪等」→ 錯。

**出處**：第 32 章、第 33 章

### A-80　SQS visibility timeout vs delay queue vs long polling vs retention period

**一句話差異**：Visibility timeout 決定「被取走的訊息多久後重新出現」；delay queue 決定「新訊息多久後才能被取」；long polling 減少空的 ReceiveMessage；retention 決定「訊息最多保存多久」。

| 設定 | 解決的問題 | 預設與範圍 |
|---|---|---|
| Visibility timeout | 同一工作被處理兩次 | 預設 30 秒，最長 12 小時 |
| Delay queue | 新訊息要延後才能處理 | 依設定 |
| Long polling | 空回應多、成本高 | `ReceiveMessageWaitTimeSeconds` 最多 20 秒 |
| Retention period | 訊息保存期限 | 1 分鐘到 14 天，預設 4 天 |

**題目看到什麼選哪個**

- 「同一工作偶爾被處理兩次、處理時間超過設定」→ 加大 visibility timeout 或 `ChangeMessageVisibility`。
- 「空的 ReceiveMessage 很多」→ Long polling。
- 「Lambda timeout 比 visibility timeout 長」→ 訊息會在處理中重新出現，要調整。
- 選項「用 delay queue 或 retention 解決重複處理」→ 錯。

**出處**：第 32 章、第 19 章

### A-81　Kinesis Data Streams vs Data Firehose vs Managed Service for Apache Flink

**一句話差異**：KDS 是毫秒到秒級、多 consumer、可重播的串流；Firehose 是不用寫 consumer、有 buffer 的 near real-time 投遞服務，沒有 retention；Flink 做視窗、有狀態的串流運算。

| 維度 | Kinesis Data Streams | Data Firehose | Managed Service for Apache Flink |
|---|---|---|---|
| 延遲 | 毫秒到秒 | Near real-time（有 buffer） | 即時 |
| 多 consumer／重播 | 可以（retention 最長 365 天） | 不行 | 作為 KDS／MSK 的 consumer |
| 程式 | 自己寫 consumer（KCL、Lambda） | 免寫程式，可轉 Parquet、動態分區 | Flink 應用程式或串流 SQL |
| 目的地 | 任意 consumer | S3、Redshift、OpenSearch、Splunk 等 | 任意 |

**題目看到什麼選哪個**

- 「即時、多個應用程式讀同一份資料、可重播」→ KDS。
- 「近即時把串流存進 S3／Redshift，最少營運」→ Firehose。
- 「串流 JSON 轉 Parquet、依欄位分區」→ Firehose format conversion + dynamic partitioning。
- 「滑動視窗、即時彙總、有狀態運算」→ Flink。
- 選項「Firehose 可重播或多方讀取」→ 錯。

**出處**：第 31 章、第 52 章

### A-82　Kinesis Data Streams vs Amazon MSK

**一句話差異**：KDS 是 AWS 原生、營運負擔低的串流；MSK 是受管 Kafka，給既有 Kafka 程式與工具要求 Kafka API 相容的情境。

| 維度 | Kinesis Data Streams | Amazon MSK |
|---|---|---|
| API | Kinesis API | Kafka API |
| 擴展單位 | Shard（或 on-demand） | Partition 與 broker（或 Serverless） |
| 營運負擔 | 低 | Provisioned 中、Serverless 低 |
| 順序 | 每 shard 內 | 每 partition 內 |
| 選它的理由 | AWS 原生即時串流 | 既有 Kafka、需要 Kafka 生態系 |

**題目看到什麼選哪個**

- 「既有 Kafka 遷移、不改程式」→ MSK。
- 「Kafka 相容但不想管 broker」→ MSK Serverless。
- 「AWS 原生、流量無法預測、不管 shard」→ KDS on-demand。
- 「增加 consumer 數量提高平行度」→ 超過 shard／partition 數的 consumer 會閒置。

**出處**：第 31 章

### A-83　Step Functions Standard vs Express

**一句話差異**：Standard 可執行最長 1 年、exactly-once、支援等待回呼與人工核准；Express 最長 5 分鐘、依執行計費、適合高頻短流程，不支援 callback。

| 維度 | Standard | Express |
|---|---|---|
| 最長執行時間 | 1 年 | 5 分鐘 |
| 執行語意 | Exactly-once | 非同步 at-least-once；同步 at-most-once |
| `.sync`、`.waitForTaskToken` | 支援 | 不支援 |
| 計費 | 依狀態轉換次數 | 依執行次數、時間與記憶體 |
| 適合 | 付款、訂單、人工核准 | 高頻事件處理、資料轉換 |

**題目看到什麼選哪個**

- 「多步驟流程、分支、錯誤處理、稽核每一步」→ Standard。
- 「等待人工核准、等待外部系統回覆」→ Standard + `.waitForTaskToken`。
- 「高頻率、短時間、成本敏感」→ Express。
- 「對 S3 中數百萬個物件平行處理」→ Distributed Map。

**出處**：第 33 章、第 47 章

### A-84　SQS vs Amazon MQ

**一句話差異**：SQS 是雲原生、近乎無限擴展、營運最少，但要改用 SDK；Amazon MQ 相容 AMQP、MQTT、JMS 等協定，遷移時程式改動最少，但要選 broker 大小與規劃高可用。

| 維度 | SQS | Amazon MQ |
|---|---|---|
| 協定 | AWS API／SDK | ActiveMQ、RabbitMQ 相容協定 |
| 擴展 | 自動、幾乎無上限 | 依 broker 大小 |
| 營運負擔 | 最低 | 較高 |
| 程式修改 | 需改寫 | 最少 |

**題目看到什麼選哪個**

- 「自管 RabbitMQ／ActiveMQ，程式不能改」→ Amazon MQ。
- 「全新開發、最大擴展、最少營運」→ SQS／SNS。

**出處**：第 32 章、第 46 章

---

## Operations：監控、部署、韌性與成本

### A-85　EC2 basic vs detailed monitoring vs CloudWatch agent vs high-resolution metric

**一句話差異**：Detailed monitoring 只把內建指標從 5 分鐘改成 1 分鐘；記憶體、磁碟空間要靠 CloudWatch agent；秒級偵測要 high-resolution custom metric。

| 需求 | 做法 |
|---|---|
| EC2 CPU、網路、磁碟 I/O、status check | 內建（basic 5 分鐘） |
| 1 分鐘粒度讓 scaling 更快反應 | Detailed monitoring |
| 記憶體、磁碟空間、process | CloudWatch agent |
| 秒級指標、10 秒內告警 | High-resolution metric + high-resolution alarm |
| ECS／EKS task、Pod 層級 | Container Insights |

**題目看到什麼選哪個**

- 「EC2 memory utilization」→ CloudWatch agent。
- 「Compute Optimizer 建議要考慮記憶體」→ 安裝 CloudWatch agent。
- 選項「開啟 detailed monitoring 取得記憶體指標」→ 錯。

**出處**：第 36 章、第 35 章

### A-86　Metric filter vs Subscription filter vs Export task vs Logs Insights

**一句話差異**：Metric filter 把日誌事件變成可告警的 metric；subscription filter 把日誌持續串流出去；export task 一次性批次匯出；Logs Insights 做互動式臨時查詢。

| 需求 | 做法 | 即時性 |
|---|---|---|
| 日誌中特定錯誤的計數告警 | Metric filter + alarm（不回溯舊資料） | 近即時 |
| 持續送到 S3／OpenSearch／第三方 | Subscription filter → Firehose | 近即時 |
| 即時自訂處理或跨帳號匯集 | Subscription filter → KDS／Lambda | 即時 |
| 一次性搬歷史日誌到 S3 | Export task | 批次 |
| 臨時找原因、最慢的請求 | Logs Insights | 互動式 |

**題目看到什麼選哪個**

- 「從日誌錯誤字串產生告警」→ Metric filter。
- 「日誌近即時送到 S3／Splunk」→ Subscription filter → Firehose。
- 「日誌費用持續上升」→ 設定 retention（預設永不過期）。
- 選項「用 export task 滿足持續或即時需求」→ 錯。

**出處**：第 36 章

### A-87　CloudWatch Synthetics vs CloudWatch RUM vs X-Ray

**一句話差異**：Synthetics 用模擬流量在「沒有使用者時」偵測故障；RUM 收集「真實使用者」的前端體驗；X-Ray 追蹤一個請求「跨多個服務」的延遲在哪一段。

| 維度 | Synthetics canary | RUM | X-Ray／ADOT |
|---|---|---|---|
| 資料來源 | 排程執行的腳本 | 真實使用者瀏覽器 | 應用程式 tracing |
| 回答的問題 | 關鍵流程現在能不能用？ | 哪些地區、裝置體驗差？ | 延遲來自哪個下游？ |
| 典型關鍵字 | 在客戶之前發現 | 頁面載入時間、JS 錯誤 | service map、microservices |

**題目看到什麼選哪個**

- 「沒有使用者時也要偵測網站或 API 故障」→ Synthetics canary。
- 「真實使用者頁面載入時間」→ RUM。
- 「微服務找出延遲來自哪個下游」→ X-Ray。

**出處**：第 36 章

### A-88　Trusted Advisor vs Well-Architected Tool vs Compute Optimizer vs AWS Health

**一句話差異**：Trusted Advisor 自動掃描帳號資源的最佳實務；Well-Architected Tool 是以 workload 為單位的架構審查問卷；Compute Optimizer 給 rightsizing 建議；AWS Health 告訴你 AWS 端的事件與維護。

| 工具 | 回答的問題 | 單位 |
|---|---|---|
| Trusted Advisor | 有沒有閒置資源、開放 port、接近 quota？ | 帳號（完整檢查需 Business 以上 Support） |
| Well-Architected Tool | 這個 workload 的架構風險是什麼？ | Workload（lens、HRI、milestone） |
| Compute Optimizer | EC2、EBS、Lambda、Fargate 規格合適嗎？ | 資源（記憶體需 agent） |
| AWS Health | AWS 排定維護、服務事件影響我嗎？ | 帳號與資源 |

**題目看到什麼選哪個**

- 「系統性審查架構風險並追蹤改善」→ Well-Architected Tool。
- 「自動找出閒置資源、接近 quota」→ Trusted Advisor。
- 「規格過大或不足」→ Compute Optimizer。
- 「instance scheduled retirement 自動處理」→ Health 事件 → EventBridge → Automation。

**出處**：第 38 章、第 46 章、第 39 章

### A-89　Session Manager vs Bastion + SSH vs EC2 Instance Connect Endpoint

**一句話差異**：Session Manager 不需 inbound port、以 IAM 授權、可記錄 session 內容；bastion 需要開 22 port 並自管主機；EC2 Instance Connect Endpoint 提供原生 SSH／RDP 而不需 bastion，但不記錄 session 內容。

| 維度 | Bastion + SSH | Session Manager | EC2 Instance Connect Endpoint |
|---|---|---|---|
| Inbound port | 需要（22） | 不需要 | 不需對外開放 |
| 憑證 | SSH key | IAM | IAM + 暫時 SSH key |
| Session 內容紀錄 | 自行處理 | 支援 | 不提供 |
| 營運負擔 | 高 | 低 | 低 |

**題目看到什麼選哪個**

- 「不開 inbound port、不用 bastion、稽核所有登入」→ Session Manager + session logging。
- 「private subnet 無 NAT，instance 不出現在 Systems Manager」→ 檢查 instance profile 與 `ssm`、`ssmmessages`、`ec2messages` interface endpoints。
- 「必須用原生 SSH、不想有 bastion、不需錄製」→ EC2 Instance Connect Endpoint。

**出處**：第 38 章

### A-90　Run Command vs State Manager vs Automation vs Patch Manager

**一句話差異**：Run Command 一次性對一群機器執行指令；State Manager 持續維持期望狀態；Automation 執行多步驟、主要呼叫 AWS API 的流程；Patch Manager 定義、安裝與回報 OS patch。

| 功能 | 觸發方式 | 典型用途 |
|---|---|---|
| Run Command | 人員或程式，一次性 | 緊急重啟服務、收集診斷資料（rate control） |
| State Manager | 排程反覆套用 | 確保所有（含新建）instance 都裝了 agent |
| Automation | 人員、EventBridge、Config、排程 | 事故處理、remediation、需核准的步驟 |
| Patch Manager | Maintenance Window 或 patch policy | OS 修補與合規報告 |

**題目看到什麼選哪個**

- 「對數百台機器執行指令並控制失敗擴散」→ Run Command + max-concurrency／max-errors。
- 「確保新建 instance 持續安裝某 agent」→ State Manager association。
- 「破壞性修復前需要人確認」→ Automation `aws:approve`。
- 「整個 Organization 統一 patch」→ Quick Setup patch policy。
- 「ASG 中無狀態 instance 要 patch」→ 更新 AMI + instance refresh，不是 in-place patch。

**出處**：第 38 章

### A-91　Config rule remediation vs EventBridge 事件驅動修復 vs 預防控制（SCP、Block Public Access）

**一句話差異**：Config remediation 處理「資源設定不合規」；EventBridge rule 對「某個 API 動作或服務事件」立即反應；能從源頭預防的問題，優先用 SCP、Block Public Access 等預防控制。

| 維度 | Config rule + remediation | EventBridge rule → Lambda／Automation | 預防控制 |
|---|---|---|---|
| 觸發 | 設定評估結果 | CloudTrail API 事件、服務事件 | 請求當下 |
| 時機 | 事後偵測與修正 | 事後即時反應 | 事前阻止 |
| 典型用途 | Security group 開放 22 自動關閉 | 有人修改 SG 立即通知與回復 | 帳號層 Block Public Access、SCP Deny |

**題目看到什麼選哪個**

- 「不合規資源自動修正」→ Config rule + automatic remediation。
- 「有人修改 security group 就立即反應」→ EventBridge（CloudTrail 事件）。
- 「確保任何 bucket 都不會被公開」→ 帳號層級 Block Public Access（+ SCP），比偵測後關閉更好。

**出處**：第 38 章、第 14 章、第 22 章

### A-92　CloudFormation vs CDK vs SAM vs Terraform

**一句話差異**：CloudFormation 是 AWS 原生的 YAML／JSON IaC；CDK 用程式語言寫、synth 成 CloudFormation；SAM 是簡化 serverless 的 CloudFormation 擴充；Terraform 適合多雲或已有 Terraform 投資。

| 工具 | 撰寫方式 | 底層 | 最適合 |
|---|---|---|---|
| CloudFormation | YAML／JSON | 原生 | 通用 AWS 基礎設施 |
| CDK | TypeScript、Python 等 | CloudFormation（需 `cdk bootstrap`） | 需要抽象與重用的團隊 |
| SAM | 簡化的 YAML | CloudFormation | Lambda、API Gateway、DynamoDB；內建 Lambda canary |
| Terraform | HCL | Terraform 自身 | 多雲一致工具 |

**題目看到什麼選哪個**

- 「用 TypeScript／Python 寫基礎設施」→ CDK。
- 「Serverless 應用簡化 template、Lambda canary」→ SAM（`AutoPublishAlias` + `DeploymentPreference`）。
- 「Terraform 團隊大量開帳號」→ AFT（A-38）。

**出處**：第 37 章

### A-93　StackSets vs Nested stacks vs Export／ImportValue vs Custom resource

**一句話差異**：StackSets 把同一份 template 部署到多帳號多 Region；nested stacks 重用元件；Export／ImportValue 在獨立生命週期的 stack 之間傳值；custom resource 處理 CloudFormation 不支援的資源或動作。

| 需求 | 選擇 |
|---|---|
| 同一份基線部署到 Organization 所有帳號，新帳號自動套用 | StackSets（service-managed、automatic deployment） |
| 可重複使用的元件 | Nested stacks |
| 網路 stack 的 VPC ID 給多個應用 stack | Outputs Export + `Fn::ImportValue` |
| CloudFormation 不支援的資源或要呼叫外部 API | Custom resource（Lambda-backed） |
| 讓其他團隊自助部署核准的架構，不給底層權限 | Service Catalog + launch constraint |

**題目看到什麼選哪個**：直接對照上表；「多帳號、多 Region、新帳號自動」三個字眼同時出現時，答案幾乎都是 StackSets service-managed。

**出處**：第 37 章、第 40 章

### A-94　Change set vs Drift detection vs Stack policy vs DeletionPolicy／UpdateReplacePolicy vs Termination protection

**一句話差異**：Change set 預覽「將要做什麼」；drift detection 找出「手動改過什麼」；stack policy 防止「更新時」替換資源；DeletionPolicy／UpdateReplacePolicy 決定「刪除或替換時」資料去留；termination protection 防止「整個 stack」被誤刪。

| 需求 | 工具 |
|---|---|
| 更新前先看會不會替換資料庫 | Change set（看 Replacement） |
| 找出有人在 console 手動改過的設定 | Drift detection（只回報，不修正） |
| 防止某資源在 stack 更新中被替換或刪除 | Stack policy |
| 刪除 stack 或替換資源時保留資料 | DeletionPolicy／UpdateReplacePolicy：Retain 或 Snapshot |
| 防止整個 stack 被誤刪 | Termination protection |

**題目看到什麼選哪個**

- 「部署後 alarm 觸發就退回」→ CloudFormation rollback triggers。
- 「`UPDATE_ROLLBACK_FAILED`」→ 修正原因後 continue update rollback。
- 選項「只設 DeletionPolicy 就能防止更新造成的替換」→ 錯，還要 UpdateReplacePolicy。

**出處**：第 37 章

### A-95　All-at-once vs Rolling vs Rolling with additional batch vs Immutable vs Blue/green vs Canary

**一句話差異**：All-at-once 最快但會中斷；rolling 省錢但容量會暫降；rolling with additional batch 不降容量；immutable 在新機器上部署、退回最乾淨；blue/green 幾乎即時退回但要兩套環境；canary 先給少量流量並依指標自動退回。

| 策略 | 容量下降 | 新舊並存 | 退回速度 | 成本 |
|---|---|---|---|---|
| All-at-once | 是（中斷） | 否 | 慢（重新部署） | 最低 |
| Rolling | 是 | 是 | 慢 | 低 |
| Rolling with additional batch | 否 | 是 | 慢 | 中 |
| Immutable | 否 | 短暫 | 快、乾淨 | 中 |
| Blue/green | 否 | 依切換方式 | 幾乎即時 | 高（兩套環境） |
| Canary／Linear | 否 | 是 | 自動依 alarm | 中 |

**題目看到什麼選哪個**

- 「Dev 環境、最快」→ All-at-once。
- 「不降容量、退回最乾淨（Beanstalk）」→ Immutable。
- 「Lambda 先導 10% 再全部切換、alarm 時自動退回」→ CodeDeploy canary + Lambda alias。
- 「不重新部署就開關功能」→ AppConfig feature flags。

**出處**：第 37 章、第 21 章

### A-96　ALB weighted target groups vs Route 53 weighted records vs Lambda alias 權重

**一句話差異**：ALB 權重與 Lambda alias 權重在每個請求生效、立即切換；Route 53 weighted 在 DNS 層生效，受 TTL 與快取影響，但能跨 Region、跨端點。

| 機制 | 粒度 | 生效速度 | 適用 |
|---|---|---|---|
| Lambda alias 權重 | 每次呼叫 | 立即 | Lambda 版本切換 |
| ALB weighted target groups | 每個請求 | 立即 | 同一 ALB 後的 EC2／ECS |
| Route 53 weighted | DNS 查詢 | 受 TTL 與快取影響 | 跨 Region、整個環境 |
| API Gateway canary | 每個請求 | 立即 | REST API stage |

**題目看到什麼選哪個**

- 「藍綠切換不受 DNS 快取影響、要能立即退回」→ ALB weighted target groups。
- 「跨 Region 逐步搬遷流量」→ Route 53 weighted 或 Global Accelerator traffic dial。

**出處**：第 37 章、第 10 章、第 46 章

### A-97　Backup & restore vs Pilot light vs Warm standby vs Multi-site active-active

**一句話差異**：判斷點是「DR 端平時有什麼、能不能直接接流量」：backup & restore 只有備份；pilot light 只有運作中的資料層、運算要先啟動；warm standby 有縮小但可接流量的完整環境；active-active 本來就在服務流量。

| 維度 | Backup & Restore | Pilot Light | Warm Standby | Active-Active |
|---|---|---|---|---|
| DR 端平時 | 只有備份 | 運作中的資料層 + 預建基礎 | 縮小但完整的環境 | 完整環境並服務流量 |
| 能否立即接流量 | 否 | 否 | 能，但容量小 | 能 |
| 典型 RTO | 數小時 | 數十分鐘到數小時（依自動化程度） | 數分鐘 | 接近 0 |
| 典型 RPO | 數小時 | 秒到分鐘 | 秒 | 接近 0 到秒 |
| 成本 | $ | $$ | $$$ | $$$$ |

**題目看到什麼選哪個**

- 「RTO／RPO 數小時、成本最低」→ Backup & restore + 跨 Region copy。
- 「DR 端只保留資料庫複寫，運算平時關閉」→ Pilot light。
- 「RTO 數分鐘、RPO 秒級、成本要控制」→ Warm standby + Aurora Global Database。
- 「RTO 接近 0、多 Region 同時服務」→ Active-active（處理寫入衝突）。
- 不論哪種都要另備 point-in-time backup 處理邏輯損毀。

**出處**：第 34 章、第 53 章、第 42 章

### A-98　AWS Backup vs Elastic Disaster Recovery（DRS）vs Application Migration Service（MGN）

**一句話差異**：AWS Backup 做原生資源的排程備份與保存政策；DRS 對整台伺服器做持續區塊複寫，提供長期 DR 與 failback；MGN 用類似技術做一次性遷移。判斷關鍵是「來源之後還會存在嗎」。

| 維度 | AWS Backup | DRS | MGN |
|---|---|---|---|
| 目的 | 排程備份、保存政策 | 長期 DR 保護 | 一次性遷移 |
| 單位 | AWS 原生資源 | 整台伺服器 | 整台伺服器 |
| 典型 RPO | 依備份頻率 | 秒級（RTO 分鐘級） | 不適用 |
| 來源之後 | 繼續存在 | 繼續存在，可 failback | 遷移後退役 |

**題目看到什麼選哪個**

- 「地端／VM 秒級 RPO、分鐘級 RTO、不改架構」→ DRS。
- 「大量伺服器 rehost 到 EC2、最小停機」→ MGN。
- 「集中備份政策、跨帳號 copy、Vault Lock」→ AWS Backup。

**出處**：第 34 章、第 45 章

### A-99　Route 53 failover vs ARC routing control vs Zonal shift／Zonal autoshift

**一句話差異**：Route 53 failover 依 health check 自動切換；ARC routing control 是不依賴 control plane、帶 safety rules 的高可靠手動開關；zonal shift 是你主動把流量移離某個 AZ，zonal autoshift 則由 AWS 偵測後替你移。

| 維度 | Route 53 failover | ARC routing control | Zonal shift | Zonal autoshift |
|---|---|---|---|---|
| 範圍 | Region／endpoint | Region／cell | 單一 AZ | 單一 AZ |
| 觸發 | Health check 自動 | 人為或流程 | 你主動 | AWS 偵測 |
| 防誤判 | 低 | Safety rules | — | — |
| 典型用途 | 一般主備切換 | 跨 Region 資料庫需受控切換 | AZ gray failure | 讓 AWS 自動處理 AZ 事件 |

**題目看到什麼選哪個**

- 「Failover 不依賴 Route 53 control plane、防止誤關所有 Region」→ ARC routing control + safety rules。
- 「AZ 表現異常但未完全故障」→ Zonal shift。
- 「預先定義跨 Region 切換步驟並從復原 Region 執行」→ ARC Region switch。
- 事故中的 Region 撤離不要依賴修改 Route 53 記錄或調整 Global Accelerator traffic dial（兩者都是 control plane 變更）；traffic dial 適合計畫內維護。

**出處**：第 34 章、第 53 章、第 9 章、第 42 章

### A-100　AWS FIS vs AWS Resilience Hub

**一句話差異**：FIS「實際注入故障」來驗證；Resilience Hub「評估架構」是否達到 RTO／RPO 政策並找出缺口。

| 維度 | FIS | Resilience Hub |
|---|---|---|
| 做什麼 | 注入故障（停 instance、加延遲等） | 評估應用程式的韌性政策 |
| 安全機制 | CloudWatch alarm stop condition | 不影響正式環境 |
| 回答的問題 | 真的撐得住嗎？ | 設計上達得到 RTO／RPO 嗎？ |

**題目看到什麼選哪個**

- 「在正式環境安全地注入故障，異常時自動停止」→ FIS。
- 「評估應用程式是否達到 RTO／RPO 目標」→ Resilience Hub。

**出處**：第 34 章

### A-101　Cost Explorer vs Budgets vs Cost Anomaly Detection vs Data Exports（CUR 2.0）vs Billing Conductor

**一句話差異**：Cost Explorer 看過去與趨勢、給承諾建議；Budgets 對預算告警並可觸發動作；Anomaly Detection 抓不尋常的支出；Data Exports 給最詳細的逐資源逐小時明細；Billing Conductor 產生自訂價格的 pro forma 帳單。

| 工具 | 回答的問題 | 輸出 |
|---|---|---|
| Cost Explorer | 錢花在哪？該買多少承諾？ | 圖表、預測、SP／RI 建議 |
| Budgets | 是否超過或即將超過預算？ | 告警、自動 actions |
| Cost Anomaly Detection | 有沒有異常支出？ | 異常告警與根因 |
| Data Exports（CUR 2.0） | 每個資源每小時的完整明細？ | S3 資料檔（搭配 Athena） |
| Billing Conductor | 如何呈現自訂價格的帳單？ | Pro forma 帳單 |

**題目看到什麼選哪個**

- 「超過預算時自動限制」→ Budgets actions（IAM policy、SCP、停止 instance）。
- 「最詳細的帳單資料、用 SQL 分析」→ Data Exports → S3 → Athena。
- 「Tag 已加但 Cost Explorer 看不到」→ 在管理帳號啟用 cost allocation tags。
- 選項「Budgets 能即時阻止支出」→ 錯，帳單資料有延遲。
- 「共用網路帳號的成本依比例分攤給各事業部」→ Cost categories + split charge rules（A-120）。

**出處**：第 39 章、第 43 章

---

## Migration：遷移與現代化

### A-102　7Rs：Retire、Retain、Relocate、Rehost、Replatform、Repurchase、Refactor

**一句話差異**：越往 refactor 改動越大、越慢、長期雲端效益越高；題目有硬性截止日時先 rehost，再逐步現代化。

| 策略 | 變動程度 | 速度 | 典型 AWS 目標 | 考題關鍵字 |
|---|---|---|---|---|
| Retire／Retain | 無 | 最快／不搬 | 封存到 S3／經 DX 互通 | 沒人使用／法規、硬體依賴 |
| Relocate | 平台層 | 很快 | VMware Cloud on AWS、Amazon EVS | 保留 VMware 工具、不轉換 VM |
| Rehost | 基礎設施 | 快 | EC2（MGN） | 最短時間、最少變更、機房到期 |
| Replatform | 少量 | 中 | RDS、FSx、MSK、Beanstalk | 降低營運負擔、不改程式核心 |
| Repurchase | 換產品 | 中 | SaaS | 改用商業 SaaS |
| Refactor | 大 | 慢 | Lambda、containers、DynamoDB | 雲端原生、彈性、敏捷 |

**題目看到什麼選哪個**

- 「資料中心租約即將到期、最短時間」→ Rehost（MGN）。
- 「自管資料庫改受管服務、引擎不變」→ Replatform（例如 RDS for Oracle）。
- 「Windows 檔案伺服器改受管」→ Replatform → FSx for Windows。
- 以「應用程式」而不是單台伺服器作為分類與 wave 的單位。

**出處**：第 44 章、第 51 章

### A-103　ADS Agentless Collector vs ADS Discovery Agent vs Migration Evaluator vs Migration Hub

**一句話差異**：Agentless Collector 從 vCenter 收規格與使用率；Discovery Agent 裝在每台伺服器，額外收程序與網路連線，才能畫相依圖；Migration Evaluator 做成本與 business case；Migration Hub 只追蹤進度，不搬東西。

| 工具 | 回答的問題 | 需要在 VM 內安裝 | 產出 |
|---|---|---|---|
| ADS Agentless Collector | 有哪些 VM、規格與使用率？ | 否（vCenter） | 規格、效能 |
| ADS Discovery Agent | 伺服器之間誰連誰？ | 是 | 規格、效能、程序、網路連線 |
| Migration Evaluator | 搬上雲要多少錢？ | 依收集方式 | 規格建議、成本預測、授權比較 |
| Migration Hub | 遷移進度到哪了？ | 否 | 集中儀表板 |

**題目看到什麼選哪個**

- 「收集程序與網路連線、畫相依關係」→ Discovery Agent。
- 「VMware、不允許在 VM 內安裝軟體」→ Agentless Collector。
- 「依地端實際使用率建立 business case」→ Migration Evaluator。
- 「集中追蹤多個遷移工具的進度」→ Migration Hub。
- 現況：Migration Hub 與 ADS 自 2025-11-07 起不再對新客戶開放，既有客戶可繼續使用（第 44 章）。

**出處**：第 44 章、第 51 章

### A-104　MGN vs DMS vs DataSync vs Storage Gateway

**一句話差異**：依「要搬的是什麼」選：整台伺服器用 MGN；資料庫進 RDS／Aurora 用 DMS；一次性檔案搬遷用 DataSync；長期 hybrid 檔案存取用 Storage Gateway。

| 要搬的 | 工具 | 目標 | 不要選 |
|---|---|---|---|
| 整台伺服器 | MGN | EC2 | SMS（已停止） |
| 資料庫，最小停機 | DMS full load + CDC | RDS、Aurora 等 | MGN（目標是受管服務時無法使用） |
| NFS／SMB 檔案，一次性 | DataSync | S3、EFS、FSx | Storage Gateway |
| 檔案，長期 hybrid | Storage Gateway | S3 等 | DataSync |
| COBOL 大型主機 | AWS Mainframe Modernization | — | MGN |

**題目看到什麼選哪個**

- 「大量實體或虛擬伺服器 rehost 到 EC2」→ MGN（test launch → cutover → finalize）。
- 「資料庫遷移、停機時間最短」→ DMS full load + CDC。
- 「SMB 檔案伺服器 → FSx、保留 NTFS 權限」→ DataSync。
- 選項「用 MGN 把資料庫搬進 RDS」→ 錯。

**出處**：第 45 章、第 25 章

### A-105　DMS vs SCT／DMS Schema Conversion

**一句話差異**：DMS 搬「資料」（只建資料表與主鍵）；SCT 與 DMS Schema Conversion 轉「schema 與程式碼」（PL/SQL、預存程序），不搬資料。異質遷移兩者都需要。

| 維度 | DMS | SCT／DMS Schema Conversion |
|---|---|---|
| 處理對象 | 資料（full load、CDC） | Schema、檢視、預存程序 |
| 會建立 | 資料表與主鍵 | 完整目標 schema（需人工修正部分程式碼） |
| 不處理 | Secondary index、外鍵、sequence、預存程序 | 資料 |
| 同質遷移 | 可搭配原生工具 | 通常不需要 |

**題目看到什麼選哪個**

- 「Oracle → PostgreSQL、轉換 PL/SQL」→ SCT 或 DMS Schema Conversion + DMS。
- 「遷移後查詢很慢／新增資料主鍵衝突」→ DMS 不建 secondary index、不搬 sequence 目前值。
- 「證明來源與目標資料一致」→ DMS data validation。

**出處**：第 45 章、第 29 章

### A-106　DMS full load vs Full load + CDC vs CDC only

**一句話差異**：Full load 只搬一次快照，期間來源的寫入會遺失；full load + CDC 搬完後持續同步，停機最短；CDC only 搭配原生工具做初始載入，適合大型同質資料庫。

| 模式 | 停機時間 | 適用 |
|---|---|---|
| Full load only | 長（要停寫入） | 可接受停機的小型資料庫 |
| Full load + CDC | 最短 | 大多數最小停機遷移 |
| CDC only | 最短 | 原生工具（Data Pump 等）做初始載入後補增量 |
| 反向 CDC（新目標 → 舊來源） | — | 切換後仍要能退回 |

**題目看到什麼選哪個**

- 「資料庫遷移、停機時間最短」→ Full load + CDC。
- 「Oracle 來源的 CDC 沒有變更」→ ARCHIVELOG 與 supplemental logging。
- 「切換後幾天內仍要能退回、不遺失資料」→ 反向 DMS CDC。
- 選項「只做 full load 就切換」→ 錯。

**出處**：第 45 章、第 51 章

### A-107　Strangler fig vs Big-bang rewrite

**一句話差異**：Strangler fig 用路由門面逐一拆出業務能力，可回滾、價值提早出現；big-bang 一次切換，風險集中。

| 維度 | Strangler fig | Big-bang rewrite |
|---|---|---|
| 切換方式 | 漸進 | 一次 |
| 回滾 | 容易（路由切回） | 困難 |
| 價值出現 | 提早 | 最後 |
| AWS 實作 | ALB path-based routing、API Gateway | — |

**題目看到什麼選哪個**

- 「逐步取代 monolith、降低風險、可回滾」→ Strangler fig。
- 「新服務不想被舊系統的資料模型影響」→ Anti-corruption layer。
- 「拆成多個服務但繼續共用同一資料庫」→ 分散式 monolith，不是好答案。

**出處**：第 46 章

### A-108　Transactional outbox vs 直接雙寫 vs Saga

**一句話差異**：Outbox 在同一個資料庫交易內寫入資料與事件，保證不遺失；直接雙寫中途失敗會不一致；saga 處理跨多個服務的流程，失敗時用補償交易撤銷。

| 維度 | Transactional outbox | 直接雙寫 | Saga |
|---|---|---|---|
| 解決的問題 | 寫資料庫與發事件一致 | — | 跨服務流程的失敗回復 |
| 一致性 | 保證（最終一致） | 中途失敗會不一致 | 透過補償達成 |
| AWS 實作 | Outbox table + CDC、DynamoDB Streams + Pipes | — | Step Functions 編排補償 |

**題目看到什麼選哪個**

- 「寫入資料庫並可靠地發事件，不能遺失」→ Outbox、DynamoDB Streams、DMS CDC。
- 「跨服務交易，失敗時撤銷前面步驟」→ Saga + Step Functions。
- 選項「用分散式交易同時提交資料庫與 SQS」→ 錯，SQS、SNS、EventBridge 不參與分散式交易。

**出處**：第 33 章、第 46 章

---

## AI：生成式 AI 與機器學習

### A-109　Amazon Bedrock vs SageMaker AI

**一句話差異**：Bedrock 用 API 使用 foundation models，免管基礎設施；SageMaker AI 讓你自己訓練、部署並控制模型與基礎設施。

| 維度 | Bedrock | SageMaker AI |
|---|---|---|
| 主要用途 | 使用 FM 生成、RAG、agent | 用自己的資料訓練專屬模型 |
| 基礎設施 | 全受管 | 你選 instance 與部署方式 |
| 客製化 | Prompt、Knowledge Bases、fine-tuning | 完整訓練程式與框架 |
| 營運負擔 | 低 | 較高 |

**題目看到什麼選哪個**

- 「使用生成式 AI、不想管理基礎設施」→ Bedrock。
- 「自己的資料訓練專屬預測模型、自訂訓練程式」→ SageMaker AI。
- 「常見特定任務（看圖、讀文件、轉文字）」→ 先考慮對應的 AI 服務（A-113）。

**出處**：第 47 章

### A-110　RAG（Knowledge Bases）vs Fine-tuning

**一句話差異**：RAG 在回答時即時檢索最新資料並可引用來源；fine-tuning 改變模型的行為、語氣與格式。事實會變用 RAG，風格與格式用 fine-tuning。

| 維度 | RAG | Fine-tuning |
|---|---|---|
| 解決的問題 | 依公司最新文件回答 | 特定語氣、格式、任務行為 |
| 資料更新 | 更新文件即可 | 要重新訓練 |
| 引用來源 | 可以 | 不行 |
| AWS 實作 | Bedrock Knowledge Bases | Bedrock 或 SageMaker 的 fine-tuning |

**題目看到什麼選哪個**

- 「LLM 依公司最新文件回答並附來源、不想訓練模型」→ Knowledge Bases。
- 「需要特定語氣或格式，prompt 做不到」→ Fine-tuning。
- 選項「用 fine-tuning 解決資料即時性」→ 錯。

**出處**：第 47 章、第 53 章

### A-111　Amazon Kendra vs Bedrock Knowledge Bases

**一句話差異**：Kendra 是企業搜尋，依使用者權限回傳相關文件段落；Knowledge Bases 是受管 RAG，產生附引用的答案。

| 維度 | Kendra | Knowledge Bases |
|---|---|---|
| 輸出 | 搜尋結果（文件段落） | 生成的答案 + 引用 |
| 權限過濾 | 依文件 ACL | 依 metadata 篩選與實作 |
| 關鍵字 | 「搜尋」 | 「生成答案」 |

**題目看到什麼選哪個**

- 「企業內部文件智慧搜尋、依權限過濾」→ Kendra。
- 「依文件產生答案並附來源」→ Knowledge Bases。

**出處**：第 47 章

### A-112　Amazon Lex vs Bedrock agent

**一句話差異**：Lex 處理固定流程、意圖與參數明確的對話；Bedrock agent 處理開放式問題、多步推理與工具選擇。

| 維度 | Lex | Bedrock agent |
|---|---|---|
| 對話型態 | 意圖 + slot，流程固定 | 開放式、多步推理 |
| 工具呼叫 | 透過 fulfillment Lambda | Agent 自行選擇工具 |
| 典型整合 | Amazon Connect 客服中心 | 後端 API、Step Functions |
| 授權 | 由後端處理 | 必須在工具執行層強制，不能靠 prompt |

**題目看到什麼選哪個**

- 「簡單訂位機器人、與 Connect 整合」→ Lex。
- 「AI 需要呼叫系統完成動作」→ Bedrock agent + 工具授權 + 人工核准（Step Functions `.waitForTaskToken`）。
- 現況：原本的 Bedrock Agents 已更名為 Agents Classic 並進入維護模式，自 2026-07-30 起不再對新客戶開放；新開發的 agent 用 Bedrock AgentCore 建置（第 47 章）。

**出處**：第 47 章、第 53 章

### A-113　Textract vs Rekognition vs Comprehend vs Transcribe

**一句話差異**：Textract 讀「文件結構」（表單、表格、發票）；Rekognition 看「圖片與影片」（含招牌、車牌上的文字）；Comprehend 分析「文字」的情緒、實體與 PII；Transcribe 把「語音」轉成文字。

| 服務 | 輸入 | 輸出 | 題目關鍵字 |
|---|---|---|---|
| Textract | 掃描文件、PDF | 文字、表單、表格 | 發票、表單擷取 |
| Rekognition | 圖片、影片 | 物件、人臉、不當內容、場景文字 | 內容審核 |
| Comprehend | 文字 | 情緒、實體、PII、自訂分類 | 文字分析 |
| Transcribe | 語音 | 文字 | 通話錄音轉文字 |

**題目看到什麼選哪個**

- 「從掃描文件、發票擷取表單與表格」→ Textract（多頁 PDF 用非同步 API + SNS）。
- 「偵測使用者上傳圖片中的不當內容」→ Rekognition。
- 「通話錄音分析情緒」→ Transcribe → Comprehend。
- 「文字轉語音」→ Polly；「翻譯」→ Translate；「推薦」→ Personalize。Forecast 已不開放新客戶。

**出處**：第 47 章

### A-114　SageMaker real-time vs serverless vs asynchronous inference vs batch transform

**一句話差異**：依序問：要不要即時回應（不要 → batch transform）、輸入是否很大或處理很久（是 → async）、流量是否間歇且能容忍冷啟動（是 → serverless，否 → real-time）。

| 方式 | 適合 | 不適合 |
|---|---|---|
| Real-time | 低延遲、常駐、高流量（搭配 auto scaling） | 長時間閒置 |
| Serverless | 間歇流量、可容忍冷啟動 | 即時且高流量 |
| Asynchronous | 大型輸入、處理數分鐘、間歇請求 | 需要立即結果 |
| Batch transform | 整批離線推論 | 即時需求 |

**題目看到什麼選哪個**

- 「大型輸入、處理數分鐘」→ Asynchronous inference。
- 「每晚對整份資料集推論」→ Batch transform（或 Bedrock batch inference）。
- 「即時又高流量」→ Real-time endpoint + auto scaling。

**出處**：第 47 章

### A-115　Bedrock Guardrails vs Comprehend PII vs IAM；CloudTrail vs Model invocation logging

**一句話差異**：Guardrails 在模型輸入輸出時即時過濾內容與遮蔽 PII；Comprehend 在資料處理管線中分析 PII；兩者都不是授權，誰能操作哪筆資料要靠 IAM 與工具層。稽核方面，CloudTrail 記錄「誰呼叫了 API」，invocation logging 才記錄 prompt 與回應內容。

| 需求 | 機制 |
|---|---|
| LLM 對話中擋特定主題、遮蔽 PII、偵測提示注入 | Bedrock Guardrails |
| 回答必須有文件依據 | Guardrails contextual grounding check |
| 資料管線中偵測 PII | Comprehend |
| Agent 只能操作使用者自己的資料 | 以使用者身份呼叫工具，後端授權 |
| 稽核所有 prompt 與回應 | Model invocation logging（預設關閉）→ S3／CloudWatch Logs |
| 誰呼叫了 Bedrock API | CloudTrail |

**題目看到什麼選哪個**

- 「稽核對話內容」→ Model invocation logging，不是 CloudTrail。
- 「不經 Internet 呼叫 Bedrock」→ Interface VPC endpoint。
- 選項「把 Guardrails 當作授權」或「靠 system prompt 限制 agent 權限」→ 錯。

**出處**：第 47 章、第 53 章

---

## Enterprise：多 Region、治理與成本可視化

### A-116　DynamoDB global tables MREC vs MRSC vs Home Region 分區

**一句話差異**：MREC 每個 Region 都能寫、非同步複寫、衝突以 last writer wins 解決；MRSC 寫入同步確認、跨 Region 強一致、RPO 0，但限制多；home Region 分區讓每筆資料只有一個寫入點，用路由避免衝突，也能滿足資料主權。

| 維度 | MREC（預設） | MRSC | Home Region 分區 |
|---|---|---|---|
| 寫入 | 任何 Region，本地確認 | 任何 replica，同步確認後才回應 | 只在該筆資料的 owner Region |
| 跨 Region 讀取 | 可能讀到舊資料 | Strongly consistent read 讀到最新 | 讀 owner Region 才保證最新 |
| 衝突 | Last writer wins，被覆蓋的修改消失 | 同時寫同一 item 時一方收到 `ReplicatedWriteConflictException` 並重試 | 不會發生 |
| Region 數 | 任意 | 剛好三個（3 replica 或 2 replica + witness） | 依分區設計 |
| 限制 | Transactions 只在發起的 Region 內有 ACID | 不支援 transactions、TTL、LSI；建立後不能加 replica | 切換 owner 時要先圍欄舊 owner |
| 資料主權 | 整張 table 都會複寫 | 整張 table 都會複寫 | 依地區拆 table，天然滿足 |

**題目看到什麼選哪個**

- 「購物車、偏好設定，偶爾覆蓋可接受，各 Region 都要低延遲寫」→ MREC。
- 「跨 Region 強一致、RPO 為零，三個 Region 都要能扣庫存」→ MRSC，並把 `TransactWriteItems` 改成單一 item 的條件更新。
- 「同一筆不能遺失修改、大多數寫入要在本地完成」→ Home Region 分區。
- 「歐洲個資只能在歐盟」→ 依地區拆成不同 global table，不是對同一張 table 加 IAM 限制或加密。
- 選項「MREC 改用 strongly consistent read 就能避免衝突」→ 錯，它只保證本 Region 最新。

**出處**：第 27 章、第 42 章

### A-117　S3 Cross-Region Replication vs Multi-Region Access Points vs CloudFront origin group

**一句話差異**：CRR 只負責把物件複製到另一個 Region 的 bucket；Multi-Region Access Point（MRAP）提供一個全球名稱與 active／passive failover controls，但本身不複製資料；CloudFront origin group 只對讀取（GET、HEAD、OPTIONS）做 origin failover。

| 維度 | CRR | MRAP | CloudFront origin group |
|---|---|---|---|
| 解決的問題 | 資料有第二份 | 應用程式用同一個名稱存取多個 bucket、可切換 | 讀取型內容的 origin 備援 |
| 會不會複製資料 | 會（非同步，RTC 可給 15 分鐘 SLA） | 不會，要另外設定複寫規則 | 不會 |
| 寫入可否切換 | 不適用（應用程式寫死 bucket） | 可以，改 failover controls 即可 | 不行，只有 GET／HEAD／OPTIONS |
| 用戶端要求 | 無 | SigV4A 簽章 | 一般 HTTP |
| 額外費用 | 複寫與跨 Region 傳輸 | 資料路由費 + 跨 Region 傳輸 | CloudFront 費用 |

**題目看到什麼選哪個**

- 「DR 副本、平時沒有應用程式讀取」→ CRR（需要可預期時間時加 RTC）。
- 「兩個 Region 的應用程式用同一個名稱讀寫，故障時幾分鐘內切到另一個 Region，不重新部署」→ MRAP + 雙向複寫 + failover controls。
- 「全球使用者讀取圖片，主要 bucket 故障時改讀備援 bucket」→ CloudFront origin group。
- 選項「MRAP 會自動同步兩個 bucket」→ 錯。

**出處**：第 23 章、第 42 章

### A-118　單 Region KMS key vs Multi-Region KMS key；Secrets Manager replica vs Parameter Store

**一句話差異**：資料由 AWS 服務在目的 Region 重新加密（S3 CRR、Aurora Global Database、DynamoDB global tables、Backup copy）時，單 Region key 就夠；只有應用程式自己解密跨 Region 複寫過去的密文時，才需要 multi-Region key。機密方面，Secrets Manager 有內建 replica secret，Parameter Store 沒有跨 Region 複寫。

| 需求 | 選擇 | 注意 |
|---|---|---|
| 應用層（欄位）加密的資料要在 DR Region 解密 | Multi-Region key（primary + replica） | 既有單 Region key 不能轉換，要建立新 key 並重新包裝 data key；key policy、alias、grant 不同步 |
| 服務端加密的資料跨 Region 複寫 | 目的 Region 的一般 key | 不需要 multi-Region key |
| 資料庫密碼在每個 Region 都讀得到 | Secrets Manager replica secret | 只在 primary 輪替，replica 唯讀；可提升為獨立 secret |
| 功能設定在每個 Region 都要有 | 由 IaC／pipeline 在每個 Region 寫入 Parameter Store，或用各 Region 的 AppConfig | 隨程式一起分波部署 |

**題目看到什麼選哪個**

- 「failover 後讀得到資料，但解不開應用層加密的欄位」→ Multi-Region key。
- 「DR Region 讀不到資料庫密碼」→ Secrets Manager replica secret。
- 選項「所有跨 Region 複寫都要先改用 multi-Region key」→ 錯。
- 選項「開啟 Parameter Store 的跨 Region 複寫」→ 錯，沒有這個功能。

**出處**：第 15 章、第 42 章

### A-119　Organizations backup policy vs StackSets 部署 backup plan vs Backup Audit Manager

**一句話差異**：Backup policy 由中央把 backup plan 派送到每個帳號與 Region，成員帳號不能修改；StackSets 能自動部署 backup plan，但部署出來的 plan 成員帳號可以改或刪；Backup Audit Manager 只檢查與報告備份是否合規，不建立備份。

| 維度 | Backup policy | StackSets 部署 backup plan | Backup Audit Manager |
|---|---|---|---|
| 作用 | 建立並鎖住 backup plan | 建立一般的帳號內資源 | 偵測與報告 |
| 成員帳號能否修改 | 不能 | 能 | 不適用 |
| 新帳號自動套用 | 加入 OU 即套用 | Automatic deployment 可做到 | 依 framework 範圍 |
| 是否建立 vault、IAM role | 不會，要事先存在 | 會（template 中定義的話） | 不會 |

**題目看到什麼選哪個**

- 「所有帳號（含未來新帳號）一致的備份計畫，成員不能修改」→ Backup policy，並用 StackSets 部署它引用的 vault 與 IAM role。
- 「附加了 backup policy 卻沒有任何 recovery point」→ 檢查 vault、IAM role 與 resource type opt-in 是否存在。
- 「向稽核員證明每個資源都有備份、保存期正確」→ Backup Audit Manager 報告。
- 「歐洲備份不能 copy 到歐盟以外」→ 讓 Europe OU 不繼承指向其他地區的政策，另附加 copy 目的地在歐盟的 backup policy。

**出處**：第 34 章、第 43 章

### A-120　Cost allocation tags vs Cost categories（split charges）vs Billing Conductor vs 關閉 discount sharing

**一句話差異**：Cost allocation tags 讓 tag 成為帳單中的分組維度；cost categories 用規則把帳號、tag 映射成業務類別，並能以 split charges 分攤共用成本；Billing Conductor 只產生自訂價格的 pro forma 帳單，不改變實際折扣；關閉 discount sharing 才會改變 RI／Savings Plans 實際套用到哪些帳號。

| 需求 | 選擇 | 不會做的事 |
|---|---|---|
| Tag 出現在 Cost Explorer、CUR | 在 management account 啟用 cost allocation tag（需要時 backfill 最多 12 個月） | 不會分攤成本 |
| 依事業部分類、未分配成本可見 | Cost categories（規則依序評估、`DefaultValue`） | 不改寫 CUR 原始每一列 |
| 共用帳號成本依比例分給各事業部 | Split charge rules（`PROPORTIONAL`、`EVEN`、`FIXED`） | 不改變實際付款 |
| 子公司要依自己的價格表看帳單 | Billing Conductor billing group + pricing rule | 不改變 AWS 實際套用折扣的方式 |
| 子公司的 RI／SP 只給自己用 | 對該帳號關閉 discount sharing | 關閉後它也不再接收別人的折扣 |

**題目看到什麼選哪個**

- 「tag 已加但 Cost Explorer 看不到，還要看過去幾個月」→ 啟用 cost allocation tag + backfill。
- 「Network 帳號的費用依各事業部成本比例分攤」→ Cost categories + `PROPORTIONAL` split charge。
- 「即將分拆的子公司，RI 不要被其他帳號用掉」→ 關閉 discount sharing，不是 Billing Conductor 或 SCP。
- 「每筆訂房的雲端成本、與業務資料 JOIN」→ CUR 2.0 + Athena（A-101）。

**出處**：第 39 章、第 43 章
