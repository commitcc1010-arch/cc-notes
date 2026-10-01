---
chapter: 10
title: Elastic Load Balancing
part: 1
---

# 第 10 章　Elastic Load Balancing：ALB、NLB 與 GWLB

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚 load balancer 解決什麼問題，以及 listener、rule、target group、health check 四個物件各自負責哪一段
> - 用 ALB 的 host／path／header 規則把一個網域拆給多個後端，並設定 HTTPS、redirect、登入驗證與 sticky session
> - 判斷什麼時候必須用 NLB：固定 IP、非 HTTP 協定、TLS passthrough、保留 client IP、PrivateLink
> - 理解 GWLB 如何用 GENEVE 把流量透明地送進防火牆設備，以及它和 ALB／NLB 的根本差異
> - 正確設定 cross-zone load balancing、deregistration delay、SNI、X-Forwarded-For 與 Proxy Protocol，並在考題中選出對的 load balancer
>
> **前置知識**：第 3 章（TCP、TLS、L4 與 L7）、第 5 章（public／private subnet）、第 6 章（security group）
> **考試比重**：SAA ★★★（Domain 2 高可用、Domain 3 網路效能）｜SAP ★★☆（Domain 1 網路與安全、Domain 2 部署策略）

## 10.1 故事：促銷當晚，唯一的那台網站伺服器倒了

第 5 章結束時，Wanderly 已經有一個像樣的 VPC：public、private、isolated 三層 subnet，跨兩個 AZ。但網站本身仍然只有一台 EC2，DNS 直接指向它的 Elastic IP。平常這樣還撐得住。

暑假促銷那天晚上八點，行銷寄出電子報，十分鐘內湧進平常二十倍的使用者。那台 EC2 的 CPU 衝到 100%，回應時間從 200 毫秒變成 30 秒，接著 web server 程序被作業系統的記憶體保護機制砍掉。整整四十分鐘，網站完全打不開。工程師小林手忙腳亂地從 AMI 多開了三台機器，卻發現一個尷尬的事實：**DNS 只指向第一台的 IP，新開的機器根本收不到任何流量。**

事後檢討會上列出了三個問題：第一，使用者的入口綁死在一台機器上，那台機器就是單點故障；第二，即使多開機器，也沒有一個元件負責「把請求平均分出去」；第三，沒有任何東西會自動發現「某台機器壞了」並停止把流量送給它。

技術主管的結論是：Wanderly 需要一個 **load balancer（負載平衡器）**。而且討論很快延伸出更多需求：訂房 API 和網站前端想拆成不同服務、合作旅行社要求「給我們固定 IP 才能加入防火牆白名單」、資安團隊希望所有對外流量都經過一台第三方防火牆檢查。這三個需求，剛好對應到 AWS 的三種 load balancer。本章就從最基本的問題開始：load balancer 到底在做什麼。

## 10.2 Load balancer 在做什麼

**Load balancer** 是一個站在使用者與後端伺服器之間的元件：使用者只連到它，它再把每個連線或請求轉給後面某一台健康的伺服器。它一次解決三件事：

1. **分散負載**：十台伺服器一起分擔流量，而不是全部壓在一台上。
2. **隔離故障**：持續檢查每台伺服器是否健康，壞掉的就不再送流量過去，使用者不會察覺。
3. **穩定的入口**：使用者只需要知道 load balancer 的位址；後端伺服器可以隨時增加、減少、替換，入口不變。這也是第 18 章 Auto Scaling 能運作的前提。

AWS 把受管的 load balancer 服務統稱為 **Elastic Load Balancing（ELB）**。「受管」的意思是：你不需要自己安裝 HAProxy 或 Nginx、不需要替 load balancer 本身做備援或擴容，AWS 會依流量自動擴展它的節點，並讓它跨多個 AZ 運作。

### L4 與 L7：看得懂多少，決定能做多少

第 3 章介紹過網路分層。對 load balancer 而言，最重要的區別是它在哪一層做決策：

- **L4（傳輸層）load balancer** 只看 IP 位址、port 與協定（TCP／UDP）。它把一整條 TCP 連線轉給某台後端，但不知道連線裡的內容是 HTTP 還是資料庫協定，更看不到 URL。
- **L7（應用層）load balancer** 會把 HTTP 請求完整解析出來，看得到網域名稱（Host header）、路徑（`/api/orders`）、header、cookie、query string，因此可以「依內容」決定送往哪裡。代價是它必須終止連線、解析協定，所以只支援 HTTP 系列協定。

這個差別直接決定了 AWS 三種 load balancer 的分工：

| 類型 | 層級 | 一句話 |
|---|---|---|
| **Application Load Balancer（ALB）** | L7 | 看得懂 HTTP／HTTPS／gRPC，依內容路由 |
| **Network Load Balancer（NLB）** | L4 | 轉送 TCP／UDP／TLS 連線，固定 IP、極低延遲 |
| **Gateway Load Balancer（GWLB）** | L3 | 把封包原封不動送進防火牆等網路設備 |

還有一個上一代的 **Classic Load Balancer（CLB）**，同時有部分 L4 與 L7 功能，但不支援 path routing、SNI 多憑證等功能。它仍可使用，但新架構不應選它；考題中出現 CLB，通常是「要遷移到 ALB 或 NLB」的情境。

### 對外與對內：scheme

每個 load balancer 建立時要選擇 **scheme**：

- **Internet-facing**：節點有 public IP，放在 public subnet，讓 Internet 上的使用者連進來。
- **Internal**：節點只有 private IP，只能從 VPC 內部（或透過 peering、VPN 等連進 VPC 的網路）存取，常用在「前端服務呼叫後端服務」的中間層。

重點是：**internet-facing load balancer 的節點在 public subnet，但它後面的伺服器可以（也應該）在 private subnet**。後端伺服器不需要 public IP，只需要 security group 允許來自 load balancer 的流量。這正是第 5 章三層架構中 public subnet 只放 ALB 節點的原因。

## 10.3 四個核心物件：listener、rule、target group、health check

無論哪一種 ELB，設定都由同一組物件構成。初學者最常把它們混在一起，所以先把每個物件的責任講清楚。

**Listener（監聽器）** 是 load balancer 上「等待連線的 port 與協定」，例如「HTTPS 443」或「TCP 5000」。一個 load balancer 可以有多個 listener。HTTPS 或 TLS listener 上會掛 **憑證（certificate）**，由 load balancer 負責 TLS 解密，這稱為 **TLS termination（TLS 終止）**。

**Rule（規則）** 屬於 listener，決定「符合什麼條件的請求，執行什麼動作」。ALB 的規則可以很豐富（依路徑、網域等）；NLB 的 listener 只有一個預設動作：轉給某個 target group。

**Target group（目標群組）** 是一組可以接收流量的後端，以及「怎麼送給它們」的設定：後端用什麼協定和 port 接收、健康檢查怎麼做、要不要 sticky session、移除時等多久。後端成員稱為 **target**，可以是 EC2 instance、IP 位址、Lambda 函式，或另一個 ALB（依 load balancer 類型而定）。

**Health check（健康檢查）** 設定在 target group 上。Load balancer 會定期對每個 target 發出檢查（例如 `GET /health` 期待 HTTP 200），連續成功達到門檻才算 healthy，連續失敗達到門檻就標為 unhealthy 並停止送新流量。

```text
使用者
  │ https://www.wanderly.com/api/orders
  ▼
┌──────────────────────── ALB ────────────────────────┐
│ ① Listener  HTTPS:443（憑證 *.wanderly.com）        │
│     │                                               │
│ ② Rules（依 priority 由小到大評估）                │
│     ├─ priority 10  path = /api/*  → tg-api         │
│     ├─ priority 20  host = admin.* → tg-admin       │
│     └─ default                      → tg-web        │
└─────┬───────────────────────┬───────────────────────┘
      │ ③ 選出 target group    │
      ▼                        ▼
 ┌─ tg-api ───────────┐   ┌─ tg-web ───────────┐
 │ HTTP:8080          │   │ HTTP:80            │
 │ ④ health: /health  │   │ health: /          │
 │ [EC2-a1] [EC2-c1]  │   │ [EC2-a2] [EC2-c2]  │
 └────────────────────┘   └────────────────────┘
```

① 使用者的 HTTPS 連線在 listener 終止，ALB 用掛在 listener 上的憑證完成 TLS handshake 並解密。② 解密後 ALB 看得到完整 HTTP 請求，依規則的 priority 由小到大比對；`/api/orders` 符合 priority 10。③ 動作是轉給 `tg-api`，ALB 從這個 target group 裡挑一台 healthy target。④ 每個 target group 有自己的健康檢查與後端 port，所以 API 服務可以聽 8080、網站聽 80，互不影響。

### 健康檢查的幾個細節

- 健康檢查的參數包括 protocol、path、port、interval（間隔）、timeout、healthy／unhealthy threshold（連續幾次成功或失敗才改變狀態），以及 ALB 可設定的 success codes（例如 `200-299`）。
- **健康檢查的 path 要能代表「真的可以服務」**。只檢查 process 是否存活的端點，可能在資料庫連線還沒建立時就回 200，讓流量太早進來。但也不要讓 `/health` 依賴太多下游服務，否則一個共用資料庫的短暫延遲，會讓所有 target 同時被判定為 unhealthy。
- **Fail open**：如果一個 target group 裡**所有** target 都 unhealthy，ALB 與 NLB 會把流量送給所有 target，而不是全部拒絕。設計理由是「健康檢查本身設錯」比「所有伺服器同時壞掉」更常見。
- 健康檢查失敗最常見的原因不是應用程式壞了，而是 **target 的 security group 沒有允許來自 load balancer 的流量**，或健康檢查打的 port 和應用程式聽的 port 不一致。

> [!tip] 考試提示
> 第 18 章的 Auto Scaling group 可以選擇使用 ELB health check。這樣「EC2 還在跑但應用程式已經不回應」的 instance，也會被 ASG 判定為不健康並替換。題目問「instance 狀態正常但網站錯誤，如何自動替換」，答案就是讓 ASG 使用 ELB health check。

### 移除 target 時不要切斷進行中的請求：deregistration delay

部署新版本或縮減機器時，target 會從 target group 被移除（deregister）。如果立刻切斷，正在處理中的請求（例如使用者剛送出的訂單）就會失敗。

**Deregistration delay** 是 target group 的設定：target 被移除後進入 `draining` 狀態，load balancer **不再送新請求**給它，但給既有連線一段時間完成，時間到才真正切斷。預設 300 秒，可設定 0 到 3,600 秒。在 Classic Load Balancer 上，同一功能叫 **connection draining**，考試兩個名詞都會出現。

請求都很短的 API 可以把它調小（例如 30 秒）以加快部署；有長時間上傳或下載的服務則要調大。

## 10.4 Application Load Balancer：看得懂 HTTP 的路由器

有了這四個物件的概念，接下來看 Wanderly 最先導入的 ALB。小林的需求是：`www.wanderly.com` 給網站前端、`www.wanderly.com/api/*` 給訂房 API、`partner.wanderly.com` 給合作夥伴後台，全部共用一個入口與一張憑證管理方式。

### 規則的條件與動作

ALB listener rule 由「條件（conditions）」和「動作（actions）」組成。可用的條件：

| 條件 | 例子 |
|---|---|
| `host-header` | `partner.wanderly.com`、`*.wanderly.com` |
| `path-pattern` | `/api/*`、`/images/*.jpg` |
| `http-header` | `User-Agent` 包含 `Mobile` |
| `http-request-method` | `POST` |
| `query-string` | `?version=beta` |
| `source-ip` | 來源在 `203.0.113.0/24` |

可用的動作：

- **forward**：轉給一個 target group；也可以轉給**多個加權的 target group**（例如 90% 舊版、10% 新版），這是做 canary 與 blue/green 部署的基礎。
- **redirect**：回傳 HTTP 301／302 讓瀏覽器轉址。最常見的是在 HTTP 80 listener 上設定「全部 redirect 到 HTTPS 443」。
- **fixed-response**：ALB 直接回應固定的狀態碼與內容，不碰後端。例如維護期間回 503 與維護頁面，或對 `/robots.txt` 直接回應。
- **authenticate-cognito／authenticate-oidc**：在轉給後端之前，先要求使用者登入（見下文）。

**規則依 priority 數字由小到大評估，第一個符合的規則生效，後面的不再看。** 每個 listener 還有一個不能刪除、永遠最後評估的 **default rule**。這和第 5 章 route table 的 longest prefix match 不同：ALB 不會自動挑「比較精確」的規則。如果把 `/*` 設成 priority 10、`/admin/*` 設成 priority 20，所有 `/admin` 請求都會被 priority 10 吃掉。

### Target type：instance、ip、lambda

ALB target group 有三種 target type，建立後不能更改：

- **instance**：以 instance ID 註冊，流量送到該 instance 主要網卡的 private IP。最傳統的 EC2 用法。
- **ip**：以 IP 位址註冊。用於 **ECS Fargate 或 awsvpc 網路模式的 container**（每個 task 有自己的 ENI 與 IP，沒有可註冊的 EC2 instance）、同一台 EC2 上多個不同 port 的服務，以及**地端或 peered VPC 中的伺服器**（只要 IP 可經 Direct Connect／VPN／peering 路由到達）。
- **lambda**：把 HTTP 請求轉成 JSON 事件呼叫 Lambda 函式，再把函式回傳的物件轉回 HTTP 回應。一個 lambda target group 只能註冊一個函式，且請求 body 與函式回傳的 JSON 各最大 1 MB、不支援 WebSocket。適合把少數低流量端點做成 serverless，而不必另外架 API Gateway（第 19、20 章會比較兩者）。

### HTTPS、SNI 與多張憑證

ALB 的 HTTPS listener 需要一張 **預設憑證**，通常來自 **AWS Certificate Manager（ACM）**：ACM 免費簽發公開憑證並自動更新（第 15 章）。給 ALB 用的 ACM 憑證要和 ALB **在同一個 Region**。

一個 ALB 經常要服務多個網域，例如 `www.wanderly.com`、`partner.wanderly.com`、併購來的 `travelco.jp`。這要靠 **SNI（Server Name Indication）**：client 在 TLS handshake 的第一個訊息（ClientHello）就告訴 server「我要連的是哪個網域」，server 才能挑出對應的憑證回應。ALB 的 HTTPS listener 可以掛一張預設憑證加上一份憑證清單，依 SNI 自動選擇；client 若沒有送 SNI，就使用預設憑證。所以**一個 ALB、一個 443 listener 就能服務多個使用不同憑證的網域**。Classic Load Balancer 不支援 SNI，這是它被淘汰的原因之一。

Listener 還要選一個 **security policy**，決定允許的 TLS 版本與加密套件。合規要求「只允許 TLS 1.2 以上」時，改的就是這裡。

ALB 解密後，轉給後端可以用 HTTP（後端不必處理憑證），也可以用 HTTPS 重新加密。如果合規要求「傳輸全程加密」，就讓 target group 使用 HTTPS；ALB 不會驗證後端憑證是否由公開 CA 簽發，所以後端可以用自簽憑證。

### 讓後端知道真正的使用者：X-Forwarded 系列 header

ALB 終止了使用者的連線，再另外開一條連線到後端。所以後端看到的 TCP 來源 IP 是 **ALB 節點的 private IP**，不是使用者的 IP。這會讓存取紀錄、地區判斷、詐騙偵測全部失準。

ALB 會在轉送的 HTTP 請求中加上三個 header：

- **`X-Forwarded-For`**：原始 client IP。如果請求在到達 ALB 前已經經過其他代理（例如 CloudFront），會是一串以逗號分隔的 IP，最左邊通常是最原始的 client。
- **`X-Forwarded-Proto`**：使用者連 ALB 時用的是 `http` 還是 `https`。後端若要強制 HTTPS 轉址，應看這個 header，而不是看自己收到的協定（永遠是 ALB 用的協定）。
- **`X-Forwarded-Port`**：使用者連的 port。

後端只需要調整 web server 的 log 格式或框架設定，從 `X-Forwarded-For` 取 client IP 即可。要注意這個 header 可以被 client 偽造，所以後端應只信任「經 ALB 加上的那一段」，且不能讓使用者繞過 ALB 直接連到後端。

### Sticky sessions：相容舊程式的權宜之計

Wanderly 的舊會員系統把登入狀態存在伺服器記憶體裡。有了 ALB 之後，使用者第一個請求到 A 機器登入，下一個請求被分到 B 機器，B 不認得他，於是被登出。

**Sticky session（session affinity，黏著連線）** 讓 ALB 用 cookie 記住「這個使用者上次去哪台」，之後的請求盡量送回同一台。ALB 有兩種：

- **Duration-based**：ALB 自己產生 cookie（名稱 `AWSALB`），你設定有效時間。
- **Application-based**：使用應用程式自己的 cookie，ALB 再搭配產生的 cookie 追蹤。

但 sticky session 只是讓舊程式能先跑起來的權宜之計：它會造成負載不均（熱門使用者黏在少數機器上），而且那台機器一被替換或縮減，上面的 session 一樣消失。**長期正解是把 session 存到外部，例如 ElastiCache 或 DynamoDB（第 18、27、28 章），讓 web tier 變成 stateless。** 考題問「最少變更讓使用者不被登出」選 stickiness；問「可擴展且 instance 替換時不遺失 session」選外部 session store。

### 在 ALB 上直接做登入驗證

Wanderly 有一個內部營運後台，原本沒有登入功能，只靠「不公開網址」保護。ALB 的 **authenticate action** 可以在請求轉給後端前，先把使用者導去登入：

- **authenticate-oidc**：對接任何支援 OpenID Connect 的身份提供者（Okta、Google、Azure AD／Entra ID 等）。
- **authenticate-cognito**：對接 Amazon Cognito user pool（第 13 章），Cognito 再可以聯合到社群登入或 SAML。

登入成功後，ALB 設定 session cookie，並把使用者的身份資訊放在 header（例如 `x-amzn-oidc-identity`、`x-amzn-oidc-data`）中傳給後端。後端程式完全不用實作登入流程。這個功能**只能用在 HTTPS listener**。

如果需求不是「人登入」，而是「只允許持有公司簽發憑證的裝置或合作夥伴系統連線」，ALB 也支援 **mutual TLS（mTLS）**：在 TLS handshake 時要求 client 也出示憑證，由 ALB 依你上傳的 **trust store**（信任的 CA 憑證，可搭配撤銷清單）驗證（verify 模式），或把憑證原樣轉給後端自行驗證（passthrough 模式）。

### ALB 的其他重要特性

- **至少要選兩個 AZ 的 subnet**。ALB 會在每個啟用的 AZ 放置節點；每個 subnet 建議至少 /27，並保留足夠空閒 IP，因為 ALB 擴展時會增加節點。
- **ALB 的 IP 會變動**。ALB 對外提供的是一個 DNS 名稱（例如 `wanderly-alb-123.ap-northeast-1.elb.amazonaws.com`），背後的 IP 會隨擴展與維護改變。所以 DNS 要用 Route 53 **alias record** 指向 ALB（第 9 章），也**不能為 ALB 綁定 Elastic IP**。需要固定 IP 時，見 10.5 節與第 11 章。
- **ALB 有 security group**。標準設定是：ALB 的 SG 允許 Internet 的 443；後端 target 的 SG 只允許「來源為 ALB 的 SG」的流量（第 6 章提過 SG 可以參照另一個 SG）。
- 支援 **HTTP/2、gRPC、WebSocket**。
- **Idle timeout**：連線在沒有資料傳輸時保持多久，預設 60 秒。長輪詢或慢速匯出若超過這個時間沒有任何位元組傳輸，會被 ALB 切斷，需要調高 idle timeout 或讓應用程式定期送資料。
- **Routing algorithm**：預設 round robin；請求處理時間差異大時可改 **least outstanding requests**，把新請求送給「手上未完成請求最少」的 target。**Slow start** 可以讓新加入的 target 在一段時間內逐步增加流量，給它暖機（例如 JIT 編譯、快取載入）的時間。
- **Access logs** 可寫到 S3，記錄每個請求的 client IP、延遲、狀態碼與 target，是除錯 5xx 的第一手資料。
- 可以掛 **AWS WAF** 擋 SQL injection、惡意 bot 與限制速率（第 16 章）。

> [!warning] 常見誤解
> 「ALB 回 502／503／504，一定是 ALB 壞了。」通常不是。502 多半是 target 回了 ALB 無法解析的回應或主動關閉連線；503 常見於 target group 沒有任何已註冊的 target；504 是 target 在 idle timeout 內沒有回應。這些都指向後端或設定問題，第一步看 ALB access log 與 target health。

## 10.5 Network Load Balancer：L4 的高效轉送器

ALB 上線兩週後，兩個新需求來了，ALB 都做不到：

1. 合作旅行社的 B2B 系統用一個自訂的 TCP 協定（不是 HTTP）即時推送房價，而且他們的防火牆只能用**固定 IP**加入白名單。
2. 支付合作商要求「TLS 必須由 Wanderly 的支付伺服器自己終止」，中間的任何設備都不能解密。

這就是 **Network Load Balancer（NLB）** 的領域。NLB 工作在 L4：它不解析 HTTP，只依 IP、port 與協定轉送連線，因此可以承載任何 TCP 或 UDP 協定，並且每秒處理數百萬個請求，延遲極低。

### NLB 的 listener 與 target

- Listener 協定：**TCP、UDP、TCP_UDP**（同一個 port 同時接 TCP 與 UDP，例如 DNS）與 **TLS**。
- Target type：**instance、ip，以及 alb**（把 ALB 當成 NLB 的 target）。
- Health check 可用 TCP、HTTP 或 HTTPS。即使 listener 是 UDP，健康檢查也必須用 TCP 或 HTTP 類協定，因此 target 要開一個可被檢查的 TCP port。
- NLB 也支援 security group，但**必須在建立時就附加**；建立時沒有附加 SG 的 NLB，之後無法再加上（建立時有附加的，之後可以隨時更換）。沒有附加 SG 的 NLB 會接受所有 client 流量，所以建議一律在建立時附加。

### 固定 IP：每個 AZ 一個

NLB 在每個啟用的 AZ 都有一個**固定的 IP 位址**，在 NLB 的生命週期內不會改變。Internet-facing NLB 可以為每個 AZ 指定一個你擁有的 **Elastic IP**；internal NLB 可以為每個 AZ 指定 subnet 內的 private IP。所以 Wanderly 跨兩個 AZ 的 NLB，就有兩個固定 IP 可以交給合作夥伴加入白名單。

如果同時需要「固定 IP」和「ALB 的 path routing」怎麼辦？可以讓 **NLB 的 target 是一個 ALB**：外面看到的是 NLB 的固定 IP，NLB 把 TCP 連線轉給 ALB，ALB 再做 L7 路由。另一個做法是在 ALB 前面放 Global Accelerator（第 11 章），它提供兩個 anycast 固定 IP。

### TLS：passthrough 還是 termination

這是考試很愛考的細節，取決於 listener 協定：

- **TCP listener（例如 TCP 443）**：NLB 不解密，加密的位元組原封不動送到後端，由後端自己做 TLS handshake 與憑證管理。這就是 **TLS passthrough**，滿足支付合作商「中間不能解密」的要求，也是需要 client 憑證驗證但不想讓 LB 處理時的做法。
- **TLS listener**：NLB 用 ACM 憑證終止 TLS，再以 TCP 或 TLS 轉給後端。好處是把憑證管理與加解密運算集中到 NLB；同樣支援 SNI 多憑證。

### 保留 client IP 與 Proxy Protocol v2

NLB 不終止 TCP 連線的語意比 ALB 更「透明」，但後端看到的來源 IP 是否為原始 client IP，取決於設定：

- **Client IP preservation（保留 client IP）** 是 target group 屬性。Target type 為 **instance** 時預設開啟；target type 為 **ip** 且協定為 TCP／TLS 時預設關閉，可以手動開啟；UDP 與 TCP_UDP 的 target group 一律保留。
- 開啟 client IP preservation 時，回程封包必須經過 NLB 才能正確送回，而且**後端 security group 看到的來源是真正的 client IP**，所以 SG 要允許 client 的 IP 範圍，而不只是 NLB 的位址。這是「換成 NLB 後健康檢查正常、使用者卻連不上」的常見原因。
- 某些情況下無法保留來源 IP，最典型的是**流量經由 PrivateLink（interface endpoint）進來**，以及某些跨網路的 ip target。這時可以開啟 **Proxy Protocol v2**：NLB 在每條 TCP 連線開頭加上一段二進位 header，裡面寫著原始來源與目的 IP、port，以及 PrivateLink 的 endpoint ID。**後端程式必須支援解析這段 header**（Nginx、HAProxy 等都支援），否則會把它當成應用資料而出錯。

一句話對照：**HTTP 世界用 `X-Forwarded-For`（ALB），TCP 世界用 Proxy Protocol v2 或 client IP preservation（NLB）**。

### NLB 與 PrivateLink

第 7 章介紹過 **PrivateLink**：服務提供者把服務放在 NLB（或 GWLB）後面，建立 **endpoint service**；使用者在自己的 VPC 建立 **interface endpoint**，就能用私有 IP 存取，不需要 VPC peering，兩邊 CIDR 重疊也沒關係。所以「把 SaaS 服務私有地提供給數百個客戶 VPC」這類題目，答案的前半一定是「服務放在 NLB 後面」。ALB 不能直接作為 endpoint service 的前端；若服務本身需要 L7 路由，就用 NLB 加 alb target 的組合。

### 其他 NLB 特性

- **可以只放在一個 AZ**（ALB 至少兩個），但正式環境仍應跨多 AZ。
- **Sticky sessions** 依來源 IP（不是 cookie，因為 NLB 看不到 HTTP）。
- 每條 TCP 連線固定送到同一個 target（依 flow hash），所以長連線的負載分布取決於連線數量而不是請求數量。
- 若 NLB 前面接的 client 只解析一次 DNS 就一直用同一個 IP，會只打到一個 AZ 的節點；這時 cross-zone 設定格外重要，見下一節。

## 10.6 跨 AZ 怎麼分：cross-zone load balancing

NLB 接上之後，Wanderly 遇到一個奇怪現象：AZ-a 有 2 台 target、AZ-c 有 8 台，AZ-a 的兩台卻 CPU 滿載，AZ-c 的八台幾乎閒著。原因是 cross-zone load balancing 的設定。

先理解 load balancer 的結構：它在每個 AZ 都有節點，DNS 會回應所有 AZ 節點的 IP，client 隨機挑一個。所以**流量先被大致平均地分到各 AZ 的節點**，接下來的問題是：每個節點只能把流量送給自己 AZ 的 target，還是可以送給所有 AZ 的 target？

```text
             client 流量（DNS 平均分到兩個節點）
                 50%                  50%
                  │                    │
           [節點 AZ-a]           [節點 AZ-c]
                  │                    │
  cross-zone 關閉：
     50% ÷ 2 台 = 每台 25%     50% ÷ 8 台 = 每台 6.25%
     [a1][a2]                  [c1][c2]...[c8]

  cross-zone 開啟：
     每個節點都把流量平均分給全部 10 台 → 每台 10%
```

關閉時，AZ-a 兩台各吃 25% 流量，AZ-c 八台各只有 6.25%，正是 Wanderly 看到的狀況。開啟後，每個節點都可以送給所有 AZ 的 target，每台平均 10%。

不同 load balancer 的預設與費用不同，這是考試重點：

| | ALB | NLB | GWLB |
|---|---|---|---|
| Cross-zone 預設 | 開啟（可在 target group 層級關閉） | 關閉 | 關閉 |
| 開啟後跨 AZ 資料傳輸費 | 不收 | 收 | 收 |

所以 NLB 的選擇是取捨：開啟 cross-zone 讓負載平均，但要付跨 AZ 傳輸費並讓一個 AZ 的流量依賴另一個 AZ；關閉則要自己確保各 AZ 的 target 數量相近（例如讓 Auto Scaling group 在各 AZ 平衡分布）。注意 cross-zone **不會增加總容量**，也不會修好壞掉的 target，它只改變分配範圍。

## 10.7 Gateway Load Balancer：把流量送進防火牆

最後一個需求來自資安團隊：所有進出 Internet 的流量都要經過他們選定的第三方次世代防火牆（例如 Palo Alto、Fortinet 的虛擬設備）檢查，而且防火牆要能水平擴展、壞一台自動切換。

### 為什麼 ALB、NLB 都不適合

防火牆、入侵偵測系統（IDS/IPS）、深度封包檢查這類 **network appliance（網路設備）** 有兩個特殊需求：

1. 它們要看到**原始的封包**，包含原本的來源與目的 IP。ALB 會終止連線並另開新連線，NLB 雖然轉送連線，但都是「流量以 load balancer 為目的地」的模型。防火牆要的是「流量本來要去別的地方，順路經過我」，業界稱為 **bump-in-the-wire（線上插入）**。
2. **同一條連線的去程與回程必須經過同一台設備**，因為 stateful 防火牆要追蹤連線狀態；回程走到另一台，就會被當成不明流量丟棄。

過去的做法是在 route table 把流量指向一台防火牆 instance 的 ENI，但那台 instance 就成了單點故障，擴展也困難。

### GWLB 的運作方式

**Gateway Load Balancer（GWLB）** 工作在 L3，專為這個場景設計。它由兩個元件組成：

- **GWLB 本體**：放在安全團隊的 inspection VPC，後面的 target group 是一群防火牆設備。GWLB 只有一種 listener 形式：接收所有 IP 封包、所有 port。
- **Gateway Load Balancer endpoint（GWLBe）**：放在需要被保護的 VPC（或 inspection VPC 本身的特定 subnet），在 route table 中成為 target。它是透過 PrivateLink 技術連到 GWLB 的。

GWLB 用 **GENEVE 協定（UDP port 6081）** 把原始封包整個包起來送給防火牆設備。設備解開後看到完整的原始封包，檢查完再包回 GENEVE 送回 GWLB，GWLB 解開後讓封包繼續原本的旅程。整個過程中**原始封包的來源與目的 IP 都沒有改變**，對 client 與應用程式完全透明。

```text
Internet
   │
[IGW] ── ingress route table：10.20.16.0/20 → gwlbe-a
   │
   ▼ ①
[GWLBe-a]（app VPC 的 firewall subnet）
   │ ② 經 PrivateLink 到 inspection VPC
   ▼
[GWLB] ── ③ GENEVE(UDP 6081) 包裝原始封包
   │
   ├─▶ [防火牆設備 1]   ④ 檢查、允許或丟棄
   └─▶ [防火牆設備 2]
   │ ⑤ 送回 GWLB → GWLBe-a
   ▼
[app subnet route table：0.0.0.0/0 → gwlbe-a]
   ▼ ⑥
[App ALB / EC2]
```

① IGW 上關聯了一張 **ingress routing** 的 route table（第 5 章提過 route table 可以關聯到 IGW），把目的地是 app subnet 的流量導向 GWLBe。② GWLBe 把封包送到 inspection VPC 的 GWLB。③ GWLB 依 flow 選一台防火牆，用 GENEVE 包裝送出。④ 防火牆檢查後送回。⑤⑥ 封包回到 GWLBe，再依 subnet 的 route table 送到真正目的地。回程時，app subnet 的 default route 也指向同一個 GWLBe，確保來回對稱。

### GWLB 的關鍵特性

- **Flow stickiness**：GWLB 依 5-tuple（來源 IP、來源 port、目的 IP、目的 port、協定）把同一條 flow 固定送到同一台設備，去程與回程都一樣，滿足 stateful 檢查的需求（也可改為 3-tuple 或 2-tuple）。
- **健康檢查**：設備壞了，GWLB 把新 flow 送到其他健康設備。
- **擴展**：設備放在 Auto Scaling group 裡，依流量增減。
- **集中檢查多個 VPC**：搭配 Transit Gateway 時，TGW 要對 inspection VPC 的 attachment 開啟 **appliance mode**，確保同一條 flow 的去程與回程都進到同一個 AZ 的設備（第 7 章）。
- GWLB 不終止 TLS、不看 HTTP 內容，它只是把封包可靠地送進設備並帶回來。如果只需要 AWS 受管的防火牆規則而不需要第三方設備，**AWS Network Firewall**（第 16 章）是營運負擔更低的選擇，它底層同樣使用 GWLB 技術。

> [!sap] SAP 加深
> 集中式 inspection 架構有兩種常見拓撲：**分散式**（每個 VPC 有自己的 GWLBe，流量在各 VPC 內被導入檢查）與**集中式**（所有 VPC 經 Transit Gateway 到一個 inspection VPC）。分散式的路由簡單、故障範圍小；集中式只要一套設備與規則，但要處理 TGW appliance mode 與對稱路由。題目若強調「東西向流量（VPC 之間）也要檢查」，通常是集中式 + TGW；若強調「只檢查 Internet 進出且各 VPC 獨立」，分散式 GWLBe 較簡單。

## 10.8 把 Wanderly 的入口組起來

三種 load balancer 各就各位後，Wanderly 的入口架構如下：

```text
          使用者（瀏覽器、App）            合作旅行社（固定 IP 白名單）
                 │ HTTPS                         │ 自訂 TCP 協定 + TLS
                 ▼                               ▼
     Route 53 alias：www.wanderly.com    feed.wanderly.com → 2 個 EIP
                 │                               │
       ┌─────────▼──────────┐          ┌─────────▼──────────┐
       │ ALB（public subnet）│          │ NLB（public subnet）│
       │ 443：SNI 多憑證     │          │ TCP 7443 passthrough│
       │ 80 ：redirect 443   │          │ 每 AZ 一個 EIP      │
       └──┬─────────┬───────┘          └─────────┬──────────┘
          │/api/*   │default                     │
          ▼         ▼                            ▼
      tg-api     tg-web                    tg-feed（instance）
     (ip, ECS)  (instance, ASG)          房價推播伺服器（自己終止 TLS）
          │
          ▼
      isolated subnet：RDS
```

這張圖把本章的決策串在一起：給人用的 HTTP 流量走 ALB，享受 path routing、HTTPS 終止與登入整合；需要固定 IP、非 HTTP 協定與端到端加密的 B2B 流量走 NLB；兩者的後端都在 private subnet，只接受來自各自 load balancer 的流量。資安團隊的 GWLB 則插在 IGW 與這兩個 load balancer 之間（10.7 節的 ingress routing），不改變上面任何一個元件的設定。

下面是 ALB 部分的 CloudFormation 節錄，包含 HTTP 轉 HTTPS 與 path 規則：

```yaml
Resources:
  AlbSg:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: ALB ingress from Internet
      VpcId: !Ref Vpc
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0

  Alb:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Type: application
      Scheme: internet-facing
      Subnets: [!Ref PublicA, !Ref PublicC]
      SecurityGroups: [!Ref AlbSg]

  ApiTg:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      VpcId: !Ref Vpc
      TargetType: ip                 # ECS Fargate task 以 IP 註冊
      Protocol: HTTP
      Port: 8080
      HealthCheckPath: /health
      TargetGroupAttributes:
        - Key: deregistration_delay.timeout_seconds
          Value: "30"

  HttpListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref Alb
      Port: 80
      Protocol: HTTP
      DefaultActions:
        - Type: redirect
          RedirectConfig:
            Protocol: HTTPS
            Port: "443"
            StatusCode: HTTP_301

  HttpsListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref Alb
      Port: 443
      Protocol: HTTPS
      SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
      Certificates:
        - CertificateArn: !Ref WwwCertArn
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref WebTg

  ApiRule:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      ListenerArn: !Ref HttpsListener
      Priority: 10
      Conditions:
        - Field: path-pattern
          PathPatternConfig:
            Values: ["/api/*"]
      Actions:
        - Type: forward
          TargetGroupArn: !Ref ApiTg
```

讀這段 template 時注意：ALB 的 `Subnets` 跨兩個 AZ；HTTP listener 只做 redirect，不轉給任何後端；`SslPolicy` 限制 TLS 版本；API target group 用 `ip` type 給 Fargate，並把 deregistration delay 調短以加快部署。其他網域的憑證可以用 `AWS::ElasticLoadBalancingV2::ListenerCertificate` 加到同一個 HTTPS listener 上。

### 費用怎麼算

三種 ELB 都是「每小時固定費用 + 容量單位費用」：ALB 用 **LCU（Load Balancer Capacity Unit）**，依新連線數、活躍連線數、處理的流量與規則評估次數中**最高的那一項**計費；NLB 與 GWLB 也有各自的容量單位（NLCU、GLCU）。實務上要注意兩件事：每個 ALB 都有固定的小時費，十個小服務各開一個 ALB 不如共用一個 ALB 用 host／path 規則分流；NLB 開啟 cross-zone 後會產生跨 AZ 傳輸費。

## 10.9 比較與選型

### 三種 load balancer 對照

| 項目 | ALB | NLB | GWLB |
|---|---|---|---|
| 層級 | L7 | L4 | L3 |
| 協定 | HTTP、HTTPS、gRPC、WebSocket | TCP、UDP、TCP_UDP、TLS | 所有 IP 流量（GENEVE 6081 送設備） |
| 路由依據 | host、path、header、method、query、source IP | IP + port（flow hash） | flow（5-tuple） |
| Target type | instance、ip、lambda | instance、ip、alb | instance、ip（設備） |
| 固定 IP | 無（用 DNS 名稱） | 每 AZ 一個，可綁 EIP | 不適用 |
| TLS | 終止，SNI 多憑證，mTLS | TLS listener 終止或 TCP passthrough | 不處理 |
| Client IP | `X-Forwarded-For` | client IP preservation／Proxy Protocol v2 | 封包不變 |
| Security group | 有 | 有（建立時附加） | 無 |
| Cross-zone 預設 | 開（不收跨 AZ 費） | 關（開啟收費） | 關（開啟收費） |
| 登入驗證 | Cognito、OIDC | 無 | 無 |
| PrivateLink 前端 | 否（可放在 NLB 後） | 是 | 是（GWLBe） |
| 典型用途 | 網站、REST API、微服務、containers | 非 HTTP、固定 IP、極高效能、PrivateLink | 第三方防火牆、IDS/IPS |

### 選型流程

```text
要把流量送進防火牆／檢查設備，且保持原始封包？
├─ 是 → GWLB + GWLBe（只要受管規則 → AWS Network Firewall）
└─ 否 → 協定是 HTTP/HTTPS/gRPC，且需要依內容路由、登入、WAF？
         ├─ 是 → 需要固定 IP 或作為 PrivateLink 服務？
         │        ├─ 是 → NLB（alb target）→ ALB，或 Global Accelerator → ALB
         │        └─ 否 → ALB
         └─ 否（TCP/UDP、自訂協定、TLS passthrough、
                 每秒數百萬連線、需要 EIP）→ NLB
```

## 10.10 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 依 URL path 或網域分流到不同服務、微服務共用一個入口 | ALB listener rules（path-pattern、host-header） |
| HTTP 自動轉 HTTPS | ALB HTTP 80 listener 的 redirect action |
| 一個入口服務多個網域、多張憑證 | ALB／NLB TLS listener + SNI 憑證清單 |
| 不改程式就加上登入 | ALB authenticate-oidc／authenticate-cognito（HTTPS listener） |
| ECS Fargate／awsvpc task 註冊到 LB | target type `ip` |
| 地端伺服器也要放進同一個 target group | target type `ip`（經 DX／VPN 可路由） |
| 需要固定 IP、Elastic IP、防火牆白名單 | NLB（每 AZ 一個 EIP）；要 L7 時 NLB → ALB，或 Global Accelerator |
| UDP、自訂 TCP 協定、極低延遲、每秒數百萬請求 | NLB |
| 後端必須自己終止 TLS、中間不可解密 | NLB TCP listener（TLS passthrough） |
| 後端要看到 client IP（HTTP） | `X-Forwarded-For` |
| 後端要看到 client IP（TCP、PrivateLink） | Client IP preservation 或 Proxy Protocol v2 |
| 把服務私有地提供給其他 VPC／帳號 | NLB + PrivateLink endpoint service |
| 第三方防火牆設備、透明檢查、GENEVE | GWLB + GWLB endpoint |
| 部署時進行中的請求被中斷 | Deregistration delay（connection draining） |
| 舊程式 session 存在記憶體、使用者被登出 | Sticky session（短期）；外部 session store（長期） |
| 各 AZ target 數量不同導致負載不均 | Cross-zone load balancing |
| 金絲雀發布、按比例切流量 | ALB forward 到多個加權 target group |

**常見陷阱**：

1. 以為 ALB 可以綁 Elastic IP 或有固定 IP：ALB 只有 DNS 名稱，IP 會變。需要固定 IP 就要 NLB 或 Global Accelerator。
2. 以為 ALB 規則會自動選「最精確」的 path：規則依 priority 由小到大評估，第一個符合就生效。
3. 以為 NLB 的 TLS listener 是 passthrough：TLS listener 會終止 TLS；passthrough 要用 TCP listener。
4. 換成 NLB 並開啟 client IP preservation 後，後端 SG 只允許 NLB 位址：SG 看到的是 client IP，必須允許 client 來源範圍。
5. 把 GWLB 當成一般的應用程式 load balancer，或以為 WAF 能取代第三方 L3/L4 防火牆：WAF 只看 HTTP 請求，且只能掛在 CloudFront、ALB、API Gateway 等服務上。
6. 以為 sticky session 能在 instance 故障時保留 session：stickiness 只影響路由，不複製任何資料。

## 10.11 SAP 加深：遷移、多帳號與大規模入口

SAA 問的是「這個 workload 該用哪個 load balancer」，SAP 會把它放進遷移、多帳號與營運的情境。

**用 ALB 做漸進式遷移。** Wanderly 併購的旅行社有一套地端訂房系統，透過 Direct Connect 連到 AWS。遷移時可以建立一個 ALB，兩個 target group：一個用 `ip` target type 註冊地端伺服器的 IP，另一個註冊 AWS 上的新版服務。Listener rule 用加權 forward 從 100/0 開始，逐步調整到 0/100，出問題時立刻調回。這讓 DNS 從第一天就指向 ALB，切換不受 DNS TTL 快取影響。注意加權 forward 時若要讓同一使用者固定在同一版本，要開啟 **target group 層級的 stickiness**。

**多帳號共享入口。** 大型組織常把 internet-facing ALB 放在一個網路或入口帳號，後端服務在各自的應用帳號。做法有幾種：入口帳號的 ALB 以 `ip` target 指向經 Transit Gateway 可路由的後端；或後端帳號以 PrivateLink（NLB）發布服務，入口帳號建立 interface endpoint 後再以 IP target 註冊。後者適合 CIDR 重疊或希望最小暴露的情況。

**跨帳號的 SaaS 服務與 client 身份。** 以 NLB 發布 PrivateLink endpoint service 時，provider 看到的來源 IP 不是客戶的真實 IP；要知道是哪個客戶的哪個 endpoint，就開啟 Proxy Protocol v2，從中讀取 VPC endpoint ID 來對應客戶。Endpoint service 可以設定「需要接受」並以 allowed principals 限制哪些帳號可以建立連線。

**AZ 故障演練。** ALB 與 NLB 支援 Amazon Application Recovery Controller 的 **zonal shift**：當某個 AZ 出現灰色故障（健康檢查還過得了，但錯誤率升高）時，可以暫時把 load balancer 在該 AZ 的流量移走。這要求其他 AZ 有足夠容量，所以 SAP 題目常把「每個 AZ 預留可承受另一個 AZ 失效的容量」和 zonal shift 一起出現（第 34 章）。

**大型活動前的容量。** ELB 會自動擴展，但擴展需要時間。對於可預期、瞬間暴增的流量（例如整點開賣），可以預先保留容量單位（LCU reservation），或搭配 CloudFront 把大部分靜態請求擋在邊緣（第 11 章）。

## 本章重點整理

- Load balancer 提供分散負載、隔離故障與穩定入口三種能力；ELB 由 AWS 管理、自動擴展並跨多 AZ。
- Listener 決定接收的 port 與協定，rule 決定請求去哪個 target group，target group 定義後端與健康檢查；四者分工要分清楚。
- Internet-facing load balancer 的節點在 public subnet，後端應放在 private subnet，並只允許來自 load balancer SG 的流量。
- ALB 是 L7，可依 host、path、header、method、query string、source IP 路由，動作包括 forward（可加權）、redirect、fixed-response 與 Cognito／OIDC 登入。
- ALB 規則依 priority 由小到大評估，第一個符合即生效；default rule 永遠最後。
- ALB target type 有 instance、ip（Fargate、地端 IP）與 lambda；ALB 沒有固定 IP，不能綁 EIP，DNS 要用 alias record。
- SNI 讓一個 HTTPS／TLS listener 依 client 要求的網域挑選憑證；ALB 與 NLB 都支援，CLB 不支援。
- ALB 以 `X-Forwarded-For`、`X-Forwarded-Proto` 把原始 client IP 與協定告訴後端；sticky session 只是相容舊程式的手段，長期應外部化 session。
- NLB 是 L4，支援 TCP、UDP、TLS，每 AZ 一個固定 IP（可綁 EIP），延遲極低，是 PrivateLink endpoint service 的前端。
- NLB 的 TCP listener 是 TLS passthrough，TLS listener 是 TLS termination；client IP 靠 client IP preservation 或 Proxy Protocol v2。
- GWLB 是 L3，以 GENEVE（UDP 6081）把原始封包送進第三方設備，透過 GWLB endpoint 與 route table 導流，並以 flow stickiness 保持對稱。
- Cross-zone load balancing 在 ALB 預設開啟且不收跨 AZ 費；NLB 與 GWLB 預設關閉，開啟後收跨 AZ 費。
- Deregistration delay（CLB 稱 connection draining）讓被移除的 target 完成進行中的請求，預設 300 秒。
- 需要「固定 IP + L7 路由」時，用 NLB 搭配 alb target，或在 ALB 前加 Global Accelerator。

## 本章練習題

### 練習 10-1｜SAA｜單選｜ALB host 與 path 路由

Wanderly 有三個服務：網站前端、訂房 API、合作夥伴後台。團隊希望 `www.wanderly.com/*` 送到前端、`www.wanderly.com/api/*` 送到訂房 API、`partner.wanderly.com/*` 送到夥伴後台，三者都使用 HTTPS，並以最低成本與最少營運負擔管理入口。

最合適的做法是什麼？

- A. 為三個服務各建立一個 ALB，再用 Route 53 weighted record 依路徑分流
- B. 建立一個 ALB，在 HTTPS listener 上設定 host-header 與 path-pattern 規則，分別轉送到三個 target group
- C. 建立一個 NLB，在 TLS listener 上依 URL path 選擇不同 target group
- D. 建立一個 Gateway Load Balancer，依 Host header 把流量送到三組 EC2

> [!answer]- 答案：B
> **A ✗** 三個 ALB 都要付固定小時費，管理也較多；更關鍵的是 Route 53 只處理 DNS 查詢，看不到 HTTP 路徑，weighted record 無法依 `/api/*` 分流。
>
> **B ✓** ALB 在 L7 終止 TLS 後看得到 Host header 與路徑，一個 listener 的多條規則就能把不同網域與路徑送到不同 target group。兩個網域的憑證可以用 SNI 掛在同一個 listener 上，一個 ALB 即可滿足需求。
>
> **C ✗** NLB 工作在 L4，只依 IP 與 port 轉送連線；即使 TLS listener 解密了流量，NLB 也不提供依 HTTP 路徑路由的規則。
>
> **D ✗** GWLB 用來把封包透明送進防火牆設備，不解析 HTTP，也不是應用程式入口。
>
> **考點**：SAA-3.4、SAA-4.4｜ALB host／path-based routing

### 練習 10-2｜SAA｜單選｜Listener rule priority

一個 ALB HTTPS listener 有以下規則：priority 10 條件 `path-pattern /*` 轉送 `tg-web`；priority 20 條件 `path-pattern /admin/*` 轉送 `tg-admin`；default rule 回傳 404。工程師發現 `/admin/users` 的請求一直出現在 `tg-web` 的日誌中。

應如何修正？

- A. 把 `/admin/*` 改成 `/admin*`，讓 ALB 依 longest match 自動優先
- B. 刪除 default rule，讓 ALB 自動選擇比較精確的規則
- C. 在 `tg-admin` 開啟 sticky session，讓 admin 使用者固定到 admin target
- D. 把 `/admin/*` 規則的 priority 改成比 `/*` 小的數字（例如 5）

> [!answer]- 答案：D
> **A ✗** ALB 不使用 longest match；改寫 pattern 不改變「priority 10 的 `/*` 先被評估且已經符合」這個事實。
>
> **B ✗** Default rule 無法刪除，它只在所有規則都不符合時才生效，與這個問題無關。
>
> **C ✗** Stickiness 只在同一個 target group 內決定送往哪台 target，不會改變規則選中哪個 target group。
>
> **D ✓** ALB 依 priority 數字由小到大評估，第一個符合的規則生效。讓較具體的 `/admin/*` 先被評估，它才有機會符合；寬鬆的 `/*` 應放在後面。
>
> **考點**：SAA-3.4｜ALB rule priority 評估順序

### 練習 10-3｜SAP｜單選｜固定 IP 與 L7 路由並存

Wanderly 的夥伴 API 目前在 ALB 後面，使用 path-based routing 分到五個微服務。三家大型企業客戶要求提供固定的 IPv4 位址加入他們的出站防火牆白名單，且位址在未來數年不能改變。團隊不希望改寫路由邏輯，也不希望增加需要自行維護的伺服器，流量只來自同一個 Region 附近的企業網路。

最合適的做法是什麼？

- A. 建立 internet-facing NLB，每個 AZ 指定一個 Elastic IP，target group 使用 `alb` target type 指向既有 ALB
- B. 為 ALB 的每個 AZ 節點各綁定一個 Elastic IP
- C. 把 Route 53 record 的 TTL 設為 7 天，並把當下解析到的 ALB IP 提供給客戶
- D. 以 NLB 取代 ALB，並在 NLB listener 上重新設定五條 path 規則

> [!answer]- 答案：A
> **A ✓** NLB 每個 AZ 有固定 IP，且可指定自己的 EIP；以 ALB 作為 NLB 的 target，客戶看到的是 NLB 的固定位址，L7 路由仍由既有 ALB 處理，不需要自管伺服器。若客戶分布全球、還需要邊緣加速，Global Accelerator 也是常見選擇。
>
> **B ✗** ALB 不支援綁定 Elastic IP，它的節點 IP 由 AWS 管理並會變動。
>
> **C ✗** TTL 只控制 DNS 快取時間，ALB 背後的 IP 仍會因擴展或維護改變，提供給客戶的 IP 隨時可能失效。
>
> **D ✗** NLB 不解析 HTTP，無法依 path 路由；把 ALB 換掉就失去現有的路由能力。
>
> **考點**：SAP-2.5、SAP-1.1｜NLB 固定 IP 搭配 ALB target

### 練習 10-4｜SAA｜單選｜TLS passthrough

支付合作商要求 Wanderly 的支付閘道伺服器必須自己持有私鑰並終止 TLS，任何中間的負載平衡設備都不得解密流量。支付協定是自訂的 TCP 協定，伺服器需跨兩個 AZ 高可用。

應該使用哪種設定？

- A. ALB HTTPS listener，target group 使用 HTTPS 重新加密到伺服器
- B. NLB TLS listener 搭配 ACM 憑證，target group 使用 TLS
- C. NLB TCP listener（port 443），target group 使用 TCP，讓伺服器自行完成 TLS handshake
- D. Gateway Load Balancer，由第三方設備終止 TLS 後再送給伺服器

> [!answer]- 答案：C
> **A ✗** ALB 一定會在 listener 解密 TLS，即使之後重新加密，中間仍有一段明文；而且 ALB 只支援 HTTP 系列協定，不支援自訂 TCP 協定。
>
> **B ✗** NLB 的 TLS listener 會在 NLB 終止 TLS，違反「中間不得解密」。重新加密到後端不改變 NLB 曾經解密這件事。
>
> **C ✓** NLB 的 TCP listener 只轉送加密的位元組，不解密；TLS handshake 在 client 與支付伺服器之間完成，私鑰只存在伺服器上，這就是 TLS passthrough。NLB 跨兩個 AZ 也滿足高可用。
>
> **D ✗** GWLB 不終止 TLS，而且讓第三方設備解密同樣違反要求。
>
> **考點**：SAA-1.2、SAA-3.4｜NLB TCP listener 的 TLS passthrough

### 練習 10-5｜SAA｜單選｜後端取得 client IP

Wanderly 把網站伺服器放到 ALB 後面後，風控系統發現所有訂單的來源 IP 都變成 `10.20.0.x` 這類 VPC 內部位址，無法依地區判斷異常登入。團隊希望以最小的變更恢復正確的使用者 IP。

應如何處理？

- A. 把網站伺服器移到 public subnet 並配置 Elastic IP
- B. 修改應用程式與 web server 日誌設定，改從 `X-Forwarded-For` header 取得 client IP
- C. 在 target group 開啟 Proxy Protocol v2
- D. 把 ALB 換成 NLB，並在 NLB 上設定 `X-Forwarded-For`

> [!answer]- 答案：B
> **A ✗** 使用者連的仍是 ALB，ALB 另開連線到後端，後端看到的來源依然是 ALB 節點；移到 public subnet 只會增加暴露面。
>
> **B ✓** ALB 終止使用者連線後，會把原始 client IP 放在 `X-Forwarded-For` header 中轉給後端。只要應用程式與日誌改讀這個 header，就能取得真實 IP，不需要改架構。
>
> **C ✗** Proxy Protocol v2 是 NLB target group 的功能，用於 TCP 層傳遞來源資訊；ALB 使用的是 HTTP header。
>
> **D ✗** NLB 不解析也不修改 HTTP 內容，不會加 `X-Forwarded-For`；為了一個 header 更換 load balancer 也遠非最小變更。
>
> **考點**：SAA-3.4｜ALB X-Forwarded-For

### 練習 10-6｜SAA｜單選｜部署時請求被中斷

Wanderly 用 Auto Scaling group 搭配 ALB 執行滾動部署。每次部署時，少數使用者在上傳旅館照片（約需 2 分鐘）時收到錯誤。調查發現，上傳到一半的 instance 被移出 target group 後，連線立刻被切斷。Target group 的 deregistration delay 目前設為 10 秒。

最合適的修正是什麼？

- A. 啟用 sticky session，讓上傳中的使用者固定在同一台 instance
- B. 把 ALB 的 idle timeout 調為 10 秒，讓連線更快釋放
- C. 把 deregistration delay 調高到足以涵蓋最長上傳時間（例如 180 秒）
- D. 關閉 target group 的健康檢查，避免 instance 被移除

> [!answer]- 答案：C
> **A ✗** Stickiness 只影響新請求送往哪台；instance 被移除後一樣會被切斷，不能保護進行中的連線。
>
> **B ✗** 縮短 idle timeout 只會讓連線更容易被切斷，與 deregistration 無關，甚至會讓慢速上傳更容易失敗。
>
> **C ✓** Deregistration delay 讓被移除的 target 進入 draining 狀態：不再收新請求，但允許既有連線在設定時間內完成。設成大於最長請求時間，就能讓上傳在部署中正常結束。
>
> **D ✗** 關閉健康檢查不能阻止部署流程移除 instance，還會讓真正壞掉的 instance 繼續接收流量。
>
> **考點**：SAA-2.2｜Deregistration delay／connection draining

### 練習 10-7｜SAA｜選兩項｜Fargate 服務註冊失敗

Wanderly 把訂房 API 遷移到 ECS Fargate，task 使用 awsvpc 網路模式並跑在 private subnet，容器聽 8080 port。工程師建立了 target group，但 ECS 服務無法註冊 task，或 task 註冊後一直顯示 unhealthy。ALB 的 security group 為 `sg-alb`。

哪兩項是正確的設定？（選兩項）

- A. Target group 使用 `instance` target type，註冊 Fargate 底層主機
- B. Target group 使用 `ip` target type，port 設為 8080
- C. 把 task 移到 public subnet，讓 ALB 透過 public IP 連線
- D. 把 ALB 的 cross-zone load balancing 關閉，讓每個 AZ 只檢查自己的 task
- E. Task 的 security group 允許來源為 `sg-alb` 的 TCP 8080

> [!answer]- 答案：B、E
> **A ✗** Fargate 不提供可由客戶註冊的底層 EC2 instance，awsvpc 模式的 task 有自己的 ENI 與 IP，無法用 instance type 註冊。
>
> **B ✓** awsvpc 模式下每個 task 有獨立 IP，必須使用 `ip` target type，並以容器實際監聽的 8080 作為 target port。
>
> **C ✗** ALB 透過 VPC 內的 private IP 連到 target，task 放在 private subnet 才是正確的安全架構，不需要 public IP。
>
> **D ✗** Cross-zone 只影響流量分配，與註冊失敗或健康檢查失敗無關。
>
> **E ✓** 健康檢查與正式流量都從 ALB 節點發出；task 的 SG 參照 `sg-alb` 允許 8080，是最精確的放行方式。SG 沒有放行是 unhealthy 最常見的原因。
>
> **考點**：SAA-2.2、SAA-1.2｜ip target type 與 SG 參照

### 練習 10-8｜SAA｜選兩項｜Session 存在伺服器記憶體

Wanderly 的舊會員系統把登入 session 存在每台 web server 的記憶體中。導入 ALB 與 Auto Scaling 後，使用者經常在頁面切換時被登出；縮減 instance 時，被移除那台上的使用者也全部被登出。團隊希望先在本週內止血，再於下個季度提出可擴展的長期方案。

哪兩項分別是合適的短期與長期做法？（選兩項）

- A. 短期：在 target group 開啟 duration-based sticky session
- B. 短期：把 ALB 換成 NLB，依來源 IP 固定連線
- C. 長期：把 deregistration delay 調到 3,600 秒，避免 session 消失
- D. 長期：把 session 改存到 ElastiCache 或 DynamoDB，讓 web tier 成為 stateless
- E. 長期：關閉 Auto Scaling 的縮減動作，固定 instance 數量

> [!answer]- 答案：A、D
> **A ✓** 開啟 stickiness 只需改 target group 屬性，ALB 用 cookie 把同一使用者送回同一台 instance，能立即減少頁面切換時的登出。它不處理 instance 被移除的情況，所以只是短期方案。
>
> **B ✗** 換 load balancer 的變更遠大於開一個屬性；依來源 IP 的黏著在使用者共用 NAT 出口（例如公司網路）時分布更差，也失去 ALB 的 L7 功能。
>
> **C ✗** 拉長 draining 時間只延後 instance 被移除，instance 最終仍會終止，session 還是會消失，還拖慢每次縮減與部署。
>
> **D ✓** 把 session 外部化後，任何 instance 都能處理任何使用者的請求，instance 的新增、移除、替換都不影響登入狀態，這是可擴展的長期解法。
>
> **E ✗** 關閉縮減會浪費成本、失去彈性，而且 instance 故障替換時仍會遺失 session。
>
> **考點**：SAA-2.1、SAA-2.2｜sticky session 與 stateless 設計

### 練習 10-9｜SAA｜單選｜一個 listener 多個網域

Wanderly 併購了日本旅遊網站 `travelco.jp`，決定讓它和 `www.wanderly.com`、`partner.wanderly.com` 共用同一個 ALB 與 443 listener。三個網域各有自己的 ACM 憑證。團隊希望不增加 load balancer 數量，也不使用涵蓋所有網域的單一憑證。

應如何設定？

- A. 為每個網域在同一個 ALB 上各建立一個 443 listener
- B. 把三個網域合併成一個 wildcard 憑證 `*.com`
- C. 把 ALB 換成 Classic Load Balancer，因為它支援多憑證
- D. 在 HTTPS listener 設定一張預設憑證，並把其他兩張憑證加入 listener 的憑證清單，由 SNI 依網域選擇

> [!answer]- 答案：D
> **A ✗** 同一個 load balancer 的同一個 port 只能有一個 listener，不能為每個網域建立三個 443 listener。
>
> **B ✗** Wildcard 憑證只能涵蓋同一個網域下的一層子網域（例如 `*.wanderly.com`），不存在 `*.com` 這種可用憑證，而且題目要求各自使用自己的憑證。
>
> **C ✗** Classic Load Balancer 不支援 SNI，一個 listener 只能掛一張憑證，正好做不到這件事。
>
> **D ✓** ALB 的 HTTPS listener 支援一張預設憑證加上憑證清單。Client 在 TLS ClientHello 中以 SNI 告知要連的網域，ALB 自動選對應憑證；沒有送 SNI 的 client 會拿到預設憑證。
>
> **考點**：SAA-1.2、SAA-3.4｜SNI 多憑證

### 練習 10-10｜SAA｜單選｜不改程式加上登入

Wanderly 的內部營運後台位於 ALB 後面，目前沒有任何登入機制。公司使用一個支援 OpenID Connect 的企業身份提供者管理員工帳號。團隊希望只有員工能存取後台，且不修改後台程式碼。

最合適的做法是什麼？

- A. 在 ALB 的 security group 只允許公司辦公室的 IP 範圍
- B. 在後台前面加一個 NLB，並在 NLB 上設定 OIDC
- C. 在 ALB HTTPS listener 的規則加入 `authenticate-oidc` 動作，驗證成功後再 forward 到後台的 target group
- D. 在後台 EC2 上安裝 OIDC 函式庫並修改登入頁面

> [!answer]- 答案：C
> **A ✗** IP 限制無法識別「誰」在存取，員工在家或出差時也無法使用；它不是身份驗證。
>
> **B ✗** NLB 工作在 L4，不處理 HTTP 重導向與 cookie，沒有登入驗證功能。
>
> **C ✓** ALB 的 authenticate-oidc 動作會把未登入的使用者導向 IdP，登入成功後設定 session cookie，並把使用者身份以 header 傳給後端。後端程式不需任何變更。這個動作只能用在 HTTPS listener。
>
> **D ✗** 修改程式能達成目的，但違反「不修改程式碼」的限制，營運負擔也比較高。
>
> **考點**：SAA-1.1、SAA-1.2｜ALB 內建身份驗證

### 練習 10-11｜SAP｜單選｜第三方防火牆透明檢查

Wanderly 的資安政策要求所有從 Internet 進入 production VPC 的流量都要經過公司已採購授權的第三方次世代防火牆檢查。防火牆是一組虛擬設備，必須看到原始的來源與目的 IP，同一條連線的去程與回程要經過同一台設備，設備需要依流量自動擴展並在故障時自動切換。

最合適的設計是什麼？

- A. 在 ALB 掛 AWS WAF，並以 managed rule groups 取代第三方防火牆
- B. 在 inspection VPC 建立 Gateway Load Balancer，把防火牆設備放在 Auto Scaling group 並註冊為 target；在 production VPC 建立 GWLB endpoint，以 IGW ingress route table 與 subnet route table 把流量導入 endpoint
- C. 建立 NLB，把防火牆設備註冊為 target，並在 route table 中把 `0.0.0.0/0` 指向 NLB
- D. 在 route table 中把流量指向一台防火牆 instance 的 ENI，並以 CloudWatch alarm 在故障時手動切換

> [!answer]- 答案：B
> **A ✗** WAF 只檢查 HTTP(S) 請求，不能做 L3/L4 檢查；題目也明確要求使用已採購的第三方設備。
>
> **B ✓** GWLB 以 GENEVE 把原始封包送進設備、保留來源與目的 IP，並以 flow stickiness 讓同一條連線的雙向流量經過同一台設備；健康檢查與 Auto Scaling 處理故障與擴展。GWLB endpoint 搭配 IGW ingress routing 與 subnet route table，把流量透明地導入檢查路徑。
>
> **C ✗** NLB 不能作為 route table 的 target，也不是為了透明插入網路設備而設計，無法保證對稱與保留原始封包。
>
> **D ✗** 單一設備 ENI 是單點故障，手動切換無法滿足自動擴展與自動容錯，是 GWLB 出現前的舊做法。
>
> **考點**：SAP-1.2、SAP-1.1｜GWLB 與 GWLB endpoint 透明檢查

### 練習 10-12｜SAP｜單選｜NLB 跨 AZ 負載不均

Wanderly 的即時房價推播服務使用 internal NLB，後端是長時間保持的 TCP 連線。因為某個 instance type 在 AZ-a 容量不足，目前 AZ-a 有 3 台 target、AZ-c 有 9 台。監控顯示 AZ-a 的 target CPU 經常超過 85%，AZ-c 的 target 只有 30%。團隊希望盡快讓負載平均，並了解這個決定的成本影響。

最合適的做法與正確的成本理解是什麼？

- A. 在 NLB 啟用 sticky session，讓連線平均分到所有 target；不會產生額外費用
- B. 把 NLB 換成 ALB，因為 ALB 預設開啟 cross-zone；兩者費用模型相同
- C. 提高 AZ-a target 的健康檢查門檻，讓它們較少被判定為 healthy；不會產生額外費用
- D. 在 NLB 啟用 cross-zone load balancing，讓每個節點把流量平均分到兩個 AZ 的所有 target；跨 AZ 的流量會產生資料傳輸費

> [!answer]- 答案：D
> **A ✗** NLB 的 stickiness 依來源 IP 把 client 固定到同一個 target，不會改變「每個節點只能送給同 AZ target」的限制。
>
> **B ✗** ALB 只支援 HTTP 系列協定，無法承載自訂的 TCP 推播協定；而且 ALB 與 NLB 的計費單位不同。
>
> **C ✗** 讓健康的 target 被誤判為 unhealthy 只會減少可用容量，使 AZ-a 剩下的 target 更忙，甚至觸發 fail open。
>
> **D ✓** NLB 的 cross-zone 預設關閉，每個 AZ 節點只把流量平均分給同 AZ 的 target，所以 AZ-a 的 3 台分到一半流量。啟用後所有 12 台平均分擔；代價是 NLB 跨 AZ 傳送的資料要收費。長期也可以讓各 AZ 的 target 數量平衡。
>
> **考點**：SAP-2.4、SAP-1.5｜NLB cross-zone 與跨 AZ 費用

### 練習 10-13｜SAP｜單選｜PrivateLink 服務辨識客戶

Wanderly 把房價查詢 API 做成 SaaS，以 NLB 後面的 endpoint service 透過 PrivateLink 提供給 200 家旅行社的 VPC 使用。很多旅行社的 VPC CIDR 彼此重疊。計費與稽核需要知道每個 TCP 連線來自哪一家客戶的哪個 VPC endpoint，後端伺服器使用支援 Proxy Protocol 的 Nginx。

最合適的做法是什麼？

- A. 在 NLB target group 開啟 Proxy Protocol v2，並設定 Nginx 解析 header，從中讀取 VPC endpoint ID 對應客戶
- B. 在 NLB target group 開啟 client IP preservation，以客戶的來源 IP 判斷是哪一家
- C. 把 NLB 換成 ALB，從 `X-Forwarded-For` 讀取客戶 VPC ID
- D. 要求每家旅行社使用不同的目的 port，以 port 區分客戶

> [!answer]- 答案：A
> **A ✓** 經由 PrivateLink 進來的連線無法保留客戶的來源 IP；Proxy Protocol v2 header 會帶上原始連線資訊與 VPC endpoint ID，後端解析後即可對應到客戶，即使客戶 CIDR 重疊也能分辨。
>
> **B ✗** PrivateLink 流量不支援保留來源 IP；即使能拿到 IP，客戶 CIDR 重疊也讓 IP 無法唯一識別客戶。
>
> **C ✗** ALB 不能直接作為 endpoint service 的前端；`X-Forwarded-For` 也只包含 IP，不包含 VPC endpoint ID。
>
> **D ✗** 200 家客戶各用不同 port 需要 200 個 listener，管理負擔極高，也無法區分同一客戶的多個 endpoint。
>
> **考點**：SAP-1.2、SAP-2.3｜NLB Proxy Protocol v2 與 PrivateLink

### 練習 10-14｜SAP｜選兩項｜漸進式遷移地端應用

Wanderly 併購的旅行社有一套地端訂房網站，已透過 Direct Connect 連到 Wanderly 的 VPC，地端伺服器 IP 可從 VPC 路由到達。團隊已在 AWS 上完成新版，希望在接下來四週內把流量從 0% 逐步提高到 100%，任何階段發現問題都能在一分鐘內切回，且不受使用者端 DNS 快取影響。

哪兩個步驟最合適？（選兩項）

- A. 在 Route 53 建立 weighted record，分別指向地端與 AWS 的入口，以調整權重控制比例
- B. 用 Global Accelerator 的 traffic dial 控制地端與 AWS 的比例
- C. 建立一個 ALB，兩個 target group：一個以 `ip` target type 註冊地端伺服器 IP，另一個註冊 AWS 上的新版服務
- D. 在 ALB 上建立 GWLB endpoint，讓地端流量透明轉送
- E. 在 listener rule 使用加權 forward 動作，逐步調整兩個 target group 的權重，並視需要開啟 target group 層級的 stickiness

> [!answer]- 答案：C、E
> **A ✗** Weighted record 能分流，但比例調整與回退都受 resolver 與 client 的 DNS 快取影響，無法保證一分鐘內生效。
>
> **B ✗** Traffic dial 調整的是各 Region endpoint group 的流量比例，endpoint 必須是 ALB、NLB、EC2 或 EIP 等 AWS 資源，不能直接把地端伺服器當成 endpoint；權重比例也不是在同一個 ALB 內控制兩版服務。
>
> **C ✓** ALB 的 `ip` target type 可以註冊 VPC 可路由到達的地端 IP（經 Direct Connect 或 VPN），讓同一個 ALB 同時涵蓋新舊兩套系統。
>
> **D ✗** GWLB endpoint 用於把流量導入檢查設備，不能掛在 ALB 上，也不是遷移分流工具。
>
> **E ✓** 加權 forward 讓 ALB 依比例把請求分到兩個 target group，調整權重立即生效，不受 DNS 快取影響；開啟 target group stickiness 可避免同一位使用者在新舊版本之間來回切換。
>
> **考點**：SAP-4.2、SAP-2.1｜ALB 加權 target group 與 IP target 遷移

### 練習 10-15｜SAP｜單選｜B2B 裝置憑證驗證

Wanderly 提供一個 HTTPS API 給 500 家合作飯店的櫃台系統，用來即時回報空房。資安團隊要求只有持有 Wanderly 私有 CA 簽發之 client 憑證的系統才能建立連線，憑證被撤銷後要立即失效，並希望由 load balancer 集中處理驗證，後端只負責依憑證中的飯店代碼做授權。API 需要依 path 路由到三個服務。

最合適的做法是什麼？

- A. 使用 NLB TCP listener，讓三個後端服務各自實作 client 憑證驗證
- B. 在 ALB 前掛 AWS WAF，以 IP set 只允許 500 家飯店的來源 IP
- C. 在 ALB HTTPS listener 啟用 mutual TLS 的 verify 模式，上傳私有 CA 的 trust store 與撤銷清單，後端從 ALB 傳入的憑證資訊 header 取得飯店代碼
- D. 在 ALB 上設定 authenticate-cognito，讓每家飯店建立 Cognito 帳號

> [!answer]- 答案：C
> **A ✗** TCP passthrough 會讓三個服務各自重複實作憑證驗證，也失去 ALB 的 path routing，不符合「集中由 load balancer 處理」。
>
> **B ✗** 來源 IP 不代表身份，飯店網路的出口 IP 也可能變動或共用；它無法驗證 client 憑證。
>
> **C ✓** ALB 的 mTLS verify 模式在 TLS handshake 時依 trust store 驗證 client 憑證鏈並可檢查撤銷清單，驗證失敗的連線不會到達後端；通過後 ALB 以 header 把憑證資訊傳給後端做授權，同時保留 L7 path routing。
>
> **D ✗** Cognito 登入是給人互動式登入的流程（瀏覽器重導向），不適合機器對機器的 API，也不符合「以 client 憑證驗證」的要求。
>
> **考點**：SAP-1.2、SAP-2.3｜ALB mutual TLS 與 trust store

### 練習 10-16｜SAA｜單選｜為既有 ALB 加上 Lambda 端點

Wanderly 的網站在 ALB 後面運作。團隊要新增一個 `/reports/export` 端點，每天只被呼叫數十次，每次執行約 20 秒產生一份約 200 KB 的 CSV。團隊希望不新增或管理任何伺服器，並沿用既有的網域與 ALB 憑證，營運負擔最低。

最合適的做法是什麼？

- A. 建立 `lambda` target type 的 target group 註冊一個 Lambda 函式，並在 ALB 新增 `path-pattern /reports/export` 規則轉送到它
- B. 新開一台 EC2 執行匯出程式，註冊到新的 instance target group
- C. 為 Lambda 建立 function URL，並在 ALB 規則中 redirect 到 function URL
- D. 建立 NLB 並以 Lambda 作為 NLB 的 target

> [!answer]- 答案：A
> **A ✓** ALB 支援 lambda target type，把 HTTP 請求轉成事件呼叫函式並將結果轉回 HTTP 回應。沿用既有 listener、網域與憑證，只新增一條規則，沒有伺服器需要管理，低流量時成本也最低。回應約 200 KB，在 ALB 對 Lambda 回應 1 MB 的上限之內；若檔案會超過 1 MB，就應改為把 CSV 寫到 S3 再回傳 presigned URL。
>
> **B ✗** 為每天數十次的呼叫維護一台常駐 EC2，增加管理與成本負擔，違反「不管理伺服器」。
>
> **C ✗** Redirect 會讓瀏覽器改連另一個網址，等於暴露另一個入口、不再沿用 ALB 的網域與憑證，也繞過了 ALB 上的 WAF 等控制。
>
> **D ✗** NLB 不支援 Lambda 作為 target，只支援 instance、ip 與 alb。
>
> **考點**：SAA-3.2、SAA-2.1｜ALB Lambda target
