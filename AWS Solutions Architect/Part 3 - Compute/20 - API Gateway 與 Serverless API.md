---
chapter: 20
title: API Gateway 與 Serverless API 設計
part: 3
---

# 第 20 章　API Gateway 與 Serverless API 設計：REST、HTTP、WebSocket 與 AppSync

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚 API Gateway 在一個請求的生命週期裡做了哪些事：驗證身份、限流、驗證格式、轉換、呼叫後端、回應
> - 依需求在 REST API、HTTP API、WebSocket API 與 AppSync 之間做選擇，並說出每個選項「少了什麼功能」
> - 為 API 選對 endpoint type（edge-optimized、regional、private）與授權方式（IAM、Cognito、Lambda authorizer）
> - 用 throttling、usage plans、caching、WAF 保護後端，並知道哪些控制只是「盡力而為」
> - 處理 29 秒整合逾時、10 MB payload 與 CORS 這些最常讓 serverless API 失敗的限制
> - 畫出一個可以上線的 API Gateway + Lambda + DynamoDB 架構
>
> **前置知識**：第 3 章（HTTP、TLS、DNS）、第 13 章（Cognito）、第 19 章（Lambda）
> **考試比重**：SAA ★★★（Domain 1 安全、Domain 2 解耦架構、Domain 3 運算效能）｜SAP ★★☆（Domain 2 新方案設計、Domain 3 既有方案改善）

## 20.1 故事：訂房 API 被一個合作夥伴打掛了

第 19 章裡，Wanderly 把「訂房確認信」與「照片縮圖」改成 Lambda 函式，效果很好。工程師小林於是想把整個訂房 API 也搬到 serverless：手機 App 與網站呼叫 `POST /bookings` 建立訂單、`GET /hotels/{id}` 查旅館資料，背後各是一個 Lambda 函式，資料放在 DynamoDB。

第一版上線很順利，直到一家比價網站成為 Wanderly 的合作夥伴。對方的爬蟲程式寫錯了重試邏輯，每秒對 `GET /hotels/{id}` 送出數千個請求。Lambda 照單全收地擴展，帳號的 Lambda concurrency 被吃光，結果連一般使用者的 `POST /bookings` 也開始失敗。客服電話響個不停，而事後的帳單上還多了一筆可觀的 Lambda 與 DynamoDB 費用。

技術主管在檢討會上列出三個需求：第一，每個合作夥伴要有自己的請求額度，超過就擋在門外，不能拖垮其他人；第二，手機 App 的使用者要登入才能下單，但查旅館資料不需要；第三，同一間旅館的資料一分鐘內不太會變，不應該每次都呼叫 Lambda。另外，行銷部門還想要「房價變動時即時推播到正在瀏覽的使用者畫面」。

這些需求都不是 Lambda 本身該處理的事，它們屬於「API 的門口」。這一章要介紹的 **Amazon API Gateway**，就是 AWS 提供的受管 API 門口。我們會跟著小林，從一個最簡單的 API 開始，逐步加上授權、限流、快取、私有存取與即時推播，最後組成 Wanderly 的正式 serverless API 架構。

## 20.2 API Gateway 是什麼：一個請求在門口經過的每一站

**API（Application Programming Interface，應用程式介面）** 在這裡指的是「程式之間透過 HTTP 呼叫彼此的約定」：用哪個網址、哪個 HTTP method（GET、POST…）、帶什麼參數、會拿到什麼格式的回應。

**Amazon API Gateway** 是一個全受管的服務，讓你建立、發布、保護與監控 API。它站在 client（瀏覽器、手機 App、合作夥伴的程式）與後端（Lambda、EC2 上的服務、其他 AWS 服務）之間，替每個請求做一連串「進門檢查」，再把請求交給後端。你不需要準備或維護任何伺服器，API Gateway 會自動擴展，並按請求數（與資料傳輸量、快取等選用功能）收費。

為什麼不讓 client 直接呼叫 Lambda？因為每個 API 都需要的那些共通工作：驗證身份、限制流量、檢查參數格式、處理跨網域（CORS）、記錄存取日誌、管理版本。如果每個函式都自己寫一遍，既重複又容易出錯。API Gateway 把這些工作集中在門口，讓後端只專心處理商業邏輯。

### 一個 REST API 請求的旅程

```text
 Client（App／瀏覽器／夥伴）
   │ ① HTTPS  GET https://api.wanderly.example/v1/hotels/123
   ▼
 [DNS / custom domain] ── 解析到 API Gateway endpoint
   ▼
 ┌──────────────────────────── API Gateway ────────────────────────────┐
 │ ② TLS 終止（可選 mutual TLS）                                         │
 │ ③ AWS WAF（若有關聯 web ACL）                                         │
 │ ④ Resource policy（REST API：來源 IP、VPC endpoint、帳號）            │
 │ ⑤ 授權：IAM／Cognito authorizer／Lambda authorizer                    │
 │ ⑥ Throttling：帳號 → stage／method → usage plan（API key）            │
 │ ⑦ Request validation（必要參數、JSON schema）                         │
 │ ⑧ Cache 查詢（若啟用；命中則直接回應，不呼叫後端）                    │
 │ ⑨ Integration request：轉換並呼叫後端                                 │
 └──────────────────────────────┬──────────────────────────────────────┘
                                ▼
                 後端：Lambda／HTTP endpoint／AWS service（SQS、DynamoDB…）
                                │ ⑩ 回應
                                ▼
                 Integration response → Method response → Client
```

① Client 只知道一個網址。② API Gateway 以 HTTPS 接收請求，TLS（第 3 章）在這裡結束；若要求 client 也出示憑證，就是 20.12 節的 mutual TLS。③ 若 API 關聯了 **AWS WAF**（Web Application Firewall，第 16 章）的 web ACL，惡意流量或超過 rate-based rule 的來源會在這裡被擋下。④ REST API 可以設定 **resource policy**，在 IAM 層面決定「誰、從哪裡」可以呼叫這個 API。⑤ 確認呼叫者身份。⑥ 確認呼叫者沒有超過速率限制。⑦ 檢查請求格式，不合格就直接回 400，連後端都不用碰。⑧ 若啟用快取且命中，請求在這裡就結束。⑨ 前面都通過了，才轉換成後端需要的格式並呼叫後端。⑩ 回應依原路返回，途中可以再做轉換。

這張圖值得記住，因為考試很多題目其實在問「這個問題應該在第幾站解決」。例如「擋住某個國家的流量」是 ③，「只允許某個 VPC 呼叫」是 ④，「每個夥伴每天最多 10 萬次」是 ⑥，「body 缺少必填欄位不要呼叫 Lambda」是 ⑦。要注意，以上是 REST API 的完整功能；下一節會看到，HTTP API 為了更便宜、更快，拿掉了其中幾站。

## 20.3 三種 API 類型：REST、HTTP、WebSocket

API Gateway 有三種 API 類型。名稱有點誤導：三種都是透過 HTTP 運作，「REST API」與「HTTP API」也都能用來實作 RESTful 風格的介面。它們的差別在於**功能多寡、價格與通訊模式**。

### REST API：功能最完整

**REST API** 是 API Gateway 最早的產品，功能最多。只有它支援：

- **API keys 與 usage plans**：替每個 client 設定請求額度。
- **API caching**：在 stage 層級快取回應。
- **Request validation**：依 JSON schema 驗證 body。
- **Mapping templates**：用 VTL（Velocity Template Language，一種範本語言）改寫請求與回應的內容。
- **AWS WAF 直接關聯**、**resource policy**、**X-Ray tracing**。
- **Private endpoint** 與 **edge-optimized endpoint**（20.4 節）。
- **Canary release**：讓一小部分流量走新版部署。
- **Response streaming**：把後端回應邊產生邊送給 client（20.11 節）。

### HTTP API：便宜、快速、精簡

**HTTP API** 是較新的產品，設計目標是「大多數 API 只需要把請求代理到 Lambda 或 HTTP 後端」。它的每百萬次請求單價明顯低於 REST API、延遲也較低，並且原生支援：

- **JWT authorizer**：直接驗證 OIDC／OAuth 2.0 發出的 JWT（JSON Web Token，一種帶簽章的身份權杖），例如 Cognito user pool 或其他 IdP 發的 token，不需要寫任何程式。
- 內建 **CORS** 設定。
- **自動部署**與 `$default` stage。
- **Private integration**：透過 VPC link 連到 VPC 內的 ALB、NLB 或 AWS Cloud Map 註冊的服務。

代價是它**沒有** API keys／usage plans、caching、request validation、WAF 直接關聯、resource policy、edge-optimized 與 private endpoint。HTTP API 只有 regional endpoint。

### WebSocket API：雙向、長連線

前兩者都是「client 問一次、server 答一次」。**WebSocket API** 則讓 client 與 API Gateway 之間維持一條長時間的雙向連線，server 可以在任何時候主動把訊息推給 client。這正是 Wanderly「房價變動即時推播」的需求，20.13 節會詳細說明。

### 三者比較

| 項目 | REST API | HTTP API | WebSocket API |
|---|---|---|---|
| 通訊模式 | 請求／回應 | 請求／回應 | 雙向長連線 |
| 相對價格 | 較高 | 較低 | 按訊息與連線分鐘數 |
| Endpoint type | edge-optimized、regional、private | regional | regional |
| 授權 | IAM、Cognito authorizer、Lambda authorizer | IAM、JWT authorizer、Lambda authorizer | IAM、Lambda authorizer（在 `$connect`） |
| API keys／usage plans | 有 | 無 | 無 |
| Caching | 有 | 無 | 無 |
| Request validation | 有 | 無 | 有（route 層級，可選） |
| AWS WAF | 有 | 無（可在前面放 CloudFront + WAF） | 無 |
| 整合逾時上限 | 預設 29 秒（regional／private 可申請提高） | 30 秒 | 29 秒 |

> [!tip] 考試提示
> 題目若只要求「JWT 驗證、Lambda proxy、成本最低」，答案是 HTTP API。只要出現 **API keys、usage plans、per-client quota、caching、request validation、WAF、private API、edge-optimized** 任何一個，就必須選 REST API。選型時要問「需求清單裡有沒有 REST 專屬功能」，而不是問「哪個比較進階」。

### 其他可以直接接 Lambda 的方式

API Gateway 不是讓 HTTP 請求進入 Lambda 的唯一方式，考試常拿它們比較：

- **Lambda function URL**（第 19 章）：替單一函式產生一個 HTTPS 網址，支援 IAM 授權或不驗證（`NONE`）。沒有限流、API key、快取、自訂授權器等功能，適合 webhook 或內部工具。
- **ALB 的 Lambda target**（第 10 章）：已經有 ALB 的環境，可以用 listener rule 把某些路徑交給 Lambda。ALB 按小時與 LCU 計費，在持續高流量時可能比按請求計費的 API Gateway 便宜，但沒有 API 管理功能。

## 20.4 Endpoint types 與 custom domain：API 的大門開在哪裡

API 建好後，client 要連到哪裡？API Gateway 會給每個 API 一個預設網址，格式是 `https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`。這個網址背後的「入口形式」稱為 **endpoint type**，REST API 有三種可選。

### Edge-optimized

**Edge-optimized endpoint** 讓請求先進入離 client 最近的 CloudFront edge location（第 11 章），再經 AWS 骨幹網路送到 API 所在的 Region。這是 REST API 的預設類型，適合使用者分散在世界各地的公開 API。

要注意兩點：第一，這個 CloudFront distribution 是 **AWS 代管的**，你看不到、也不能修改它的 cache behavior 或掛自己的 Lambda@Edge；第二，它只加速連線，**不會快取 API 回應**（快取要另外啟用 API caching）。

### Regional

**Regional endpoint** 直接在 Region 內接收請求，不經過 AWS 代管的 CloudFront。適合兩種情況：client 本來就在同一個 Region（例如同 Region 的 EC2 或其他服務呼叫），或你想**自己在前面放一個 CloudFront distribution**，以便完全控制快取、WAF、geo restriction 與 origin 設定。HTTP API 與 WebSocket API 只有這一種。

### Private

**Private endpoint** 只能從 VPC 內部透過 **interface VPC endpoint**（服務名稱 `com.amazonaws.{region}.execute-api`，第 6 章）存取，Internet 上完全連不到。適合只給內部系統使用的 API，例如 Wanderly 的「財務對帳 API」只讓公司內部的批次程式呼叫。

Private API **必須設定 resource policy**，否則沒有人能呼叫它。最常見的寫法是只允許特定 VPC endpoint：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "execute-api:/*",
      "Condition": {
        "StringNotEquals": {
          "aws:SourceVpce": "vpce-0a1b2c3d4e5f67890"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "execute-api:/*"
    }
  ]
}
```

第一段 Deny 擋掉所有「不是從指定 VPC endpoint 進來」的請求，第二段 Allow 放行其他請求。因為 explicit deny 優先（第 12 章），結果就是「只有經過 `vpce-0a1b2c3d4e5f67890` 的請求能進來」。也可以改用 `aws:SourceVpc` 限制來源 VPC。

> [!warning] 常見誤解
> 「讓 private subnet 的 EC2 經過 NAT Gateway 呼叫 API，這個 API 就變成 private 了。」不是。NAT 只是出站路徑，目的地依然是一個 Internet 上任何人都能連的 public endpoint。真正的 private API 是 endpoint type 設為 private，並以 interface endpoint 加 resource policy 限制來源。

### Custom domain name

`abc123.execute-api...` 這種網址不好記，也會在你重建 API 時改變。**Custom domain name** 讓你用 `api.wanderly.example` 這樣的自有網域，再用 **base path mapping**（或 API mapping）把路徑對應到不同的 API 與 stage，例如 `/v1` 對應舊版 API 的 `prod` stage、`/v2` 對應新版 API。

TLS 憑證來自 ACM（AWS Certificate Manager，第 15 章），而憑證要放在哪個 Region 是經典考點：

| Custom domain 類型 | ACM 憑證所在 Region |
|---|---|
| Edge-optimized | **us-east-1**（因為背後是 CloudFront） |
| Regional | **與 API 相同的 Region** |

最後在 Route 53（第 9 章）建立 alias record，把 `api.wanderly.example` 指向 custom domain 提供的目標網域。

## 20.5 Resources、stages 與 deployments：API 的結構與版本

### Resources 與 methods（REST API）

REST API 的結構是一棵**資源樹**。每個 **resource** 是一段路徑，例如 `/hotels`、`/hotels/{id}`（大括號表示路徑參數）；每個 resource 上可以定義多個 **method**（GET、POST、PUT、DELETE…），每個 method 各自設定授權、驗證與後端整合。也可以使用 `{proxy+}` 這種「貪婪路徑參數」加上 `ANY` method，把某個路徑下的所有請求一次交給同一個後端。

HTTP API 用的概念叫 **route**，寫法是「method + 路徑」，例如 `GET /hotels/{id}`，也支援 `$default` route 接住所有未匹配的請求。

### Stage 與 deployment

在 REST API 裡修改 resource 或 method 後，變更**不會立刻生效**。你必須建立一個 **deployment**（當下 API 設定的快照），再把它部署到一個 **stage**。Stage 是 API 的一個具名環境，例如 `dev`、`staging`、`prod`，每個 stage 有自己的網址（`.../dev`、`.../prod`）。

這是新手最常踩的坑：在 console 改完設定，測試卻還是舊行為，原因就是忘了重新 deploy。HTTP API 的 `$default` stage 預設開啟自動部署，比較不會遇到。

每個 stage 可以分別設定：

- **Stage variables**：類似環境變數的鍵值對。例如 `dev` stage 的 `lambdaAlias=dev`、`prod` stage 的 `lambdaAlias=live`，整合設定寫成呼叫 `booking-fn:${stageVariables.lambdaAlias}`，同一份 API 定義就能在不同 stage 指向不同的 Lambda alias（第 19 章）。
- **Throttling** 與 **caching**（20.8、20.9 節）。
- **Access logs 與 execution logs**（寫到 CloudWatch Logs）、X-Ray tracing。
- **Canary settings**：讓指定百分比的流量走新的 deployment，其餘仍走目前版本，觀察指標正常後再 promote。這是 API Gateway 原生的金絲雀發布；更完整的部署策略見第 37 章。

> [!example] 例子：Wanderly 的 API 版本策略
> 舊版手機 App 可能半年都不更新，所以小林不能直接改 `/v1` 的回應格式。他建立新的 API 給 `/v2`，在 custom domain 加一個 base path mapping；`/v1` 繼續對應舊 API 的 `prod` stage。新版先在 `/v2` 的 `prod` stage 用 canary 放 10% 流量，確認錯誤率正常再全量。

## 20.6 Integration types：門口後面接的是誰

**Integration（整合）** 定義 API Gateway 收到請求後要呼叫誰、怎麼呼叫。理解各種整合類型，是設計 serverless API 的核心。

### Lambda proxy integration（`AWS_PROXY`）

最常用的方式。API Gateway 把**整個 HTTP 請求**（路徑、query string、headers、body、授權結果）包成一個 JSON event 交給 Lambda，Lambda 必須回傳特定格式，API Gateway 再原樣轉成 HTTP 回應：

```python
import json

def handler(event, context):
    hotel_id = event["pathParameters"]["id"]
    hotel = {"id": hotel_id, "name": "Wanderly Inn Taipei"}
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "https://www.wanderly.example"
        },
        "body": json.dumps(hotel)
    }
```

優點是簡單：所有邏輯都在程式碼裡，API Gateway 不做轉換。缺點是格式錯了就出事：如果 Lambda 回傳的不是這個結構（例如直接回傳一個 dict 而沒有 `statusCode`，或 `body` 不是字串），API Gateway 會回 **502 Bad Gateway**。這是考試常出的錯誤碼。

### Lambda non-proxy（custom）integration

REST API 也可以用 mapping template 先把請求改寫成 Lambda 需要的格式，Lambda 回傳後再改寫成 HTTP 回應。好處是後端可以和 HTTP 細節解耦，代價是 VTL 範本難寫、難測試。新系統通常選 proxy。

### HTTP integration

後端是一個 HTTP endpoint，例如 EC2 上的舊系統或第三方 API。有 **HTTP proxy**（原樣轉送）與 **HTTP custom**（REST API 可用 mapping template 轉換）兩種。若後端在 VPC 的 private subnet 裡，需要 **private integration**：

- REST API：建立 **VPC link** 指向 VPC 內的 **NLB**，NLB 再把流量送到後端。這是最經典、考題最常見的寫法；AWS 後來也讓 REST API 可以透過 VPC link 直接連到 **ALB**。
- HTTP API：VPC link 可以直接指向 **ALB、NLB 或 Cloud Map** 服務（Cloud Map 只有 HTTP API 支援）。

這讓 API Gateway 成為舊系統的新門口：先把舊系統包在 API Gateway 後面，再逐步把個別路徑改接到 Lambda，這就是第 46 章會詳談的 strangler fig 模式。

### AWS service integration

API Gateway 可以**不經過 Lambda，直接呼叫 AWS 服務的 API**。例如：

- `POST /bookings` 直接呼叫 **SQS `SendMessage`**，把訂單放進 queue。
- `POST /events` 直接呼叫 **EventBridge `PutEvents`** 或 **Kinesis `PutRecord`**。
- `POST /checkout` 直接呼叫 **Step Functions `StartExecution`** 啟動付款流程（第 33 章）。
- `GET /hotels/{id}` 直接呼叫 **DynamoDB `GetItem`**（REST API，用 mapping template 組出請求）。

API Gateway 用你指定的 IAM role 呼叫這些服務。為什麼要這樣做？因為一個只是「把資料原封不動放進 queue」的 Lambda 函式，除了增加延遲、費用、cold start 與一段要維護的程式碼之外，沒有任何價值。REST API 幾乎可以呼叫任何 AWS 服務 action；HTTP API 只支援一組 **first-class integrations**（包括 SQS、EventBridge、Kinesis Data Streams、Step Functions、AppConfig 等的特定 action）。

> [!tip] 考試提示：storage-first 模式
> 題目說「尖峰時不能遺失任何訂單」「後端處理速度跟不上流量」「希望減少 Lambda 程式碼」，答案常是 **API Gateway 直接整合 SQS**：請求一進來就持久化到 queue，立即回 200／202 給 client，後端 Lambda 再以 event source mapping 批次消化（第 19、32 章）。Queue 吸收尖峰，後端不會被壓垮。

### Mock integration

不呼叫任何後端，直接由 API Gateway 回傳固定內容。用於前端先行開發、健康檢查端點，或 REST API 處理 CORS 的 `OPTIONS` 預檢請求。

## 20.7 授權：誰可以呼叫這個 API？

回到小林的第二個需求：下單要登入，查旅館不用。授權是 API Gateway 最重要的功能之一，有四種主要機制，加上一個常被誤用的東西（API key）。

### IAM authorization

把 method 的授權類型設為 `AWS_IAM`，呼叫者必須用 AWS 的 **SigV4 簽章**簽署請求，也就是用 AWS 憑證（access key 或 role 的臨時憑證）計算出一個簽章放在 header 裡。API Gateway 會驗證簽章，再檢查呼叫者的 IAM policy 是否允許 `execute-api:Invoke` 這個 action 與該 API 的 ARN。

適合的呼叫者是「本來就有 AWS 身份的程式」：EC2、Lambda、ECS task，或透過 Cognito identity pool 換到臨時 AWS 憑證的手機 App（第 13 章）。跨帳號呼叫時，REST API 需要**呼叫者的 identity policy 允許**，加上 **API 的 resource policy 允許該帳號或 role**。

### Cognito user pool authorizer（REST）／JWT authorizer（HTTP）

給終端使用者用的 API，最自然的方式是讓使用者先在 **Cognito user pool**（第 13 章）登入，拿到 JWT，之後每個請求都在 `Authorization` header 帶著它：

- REST API 使用 **Cognito user pool authorizer**：API Gateway 驗證 token 的簽章、有效期限與發行者，通過才放行；也可以要求 access token 帶有特定 OAuth scope。
- HTTP API 使用 **JWT authorizer**：設定 issuer（發行者網址）與 audience（允許的 client ID），可以接受 Cognito 或任何符合 OIDC 的 IdP（例如企業的 Okta、Microsoft Entra ID）發的 token。

這兩種都不用寫程式，是「終端使用者登入」題目的標準答案。

### Lambda authorizer

如果身份驗證邏輯是自訂的，例如 token 是舊系統發的不透明字串，必須呼叫舊系統的 introspection endpoint 才知道是誰；或授權要查資料庫裡的方案等級，就用 **Lambda authorizer**（以前叫 custom authorizer）：

1. 請求進來，API Gateway 先呼叫你寫的 authorizer 函式，傳入 token 或請求參數。
2. 函式驗證後回傳一份 **IAM policy**（允許或拒絕 `execute-api:Invoke` 這個 method），還可以附上 context（例如 `tenantId`）傳給後端。
3. API Gateway 依 policy 決定放行或回 403。

REST API 的 Lambda authorizer 有兩種：**TOKEN** 型只拿到一個 header 的值；**REQUEST** 型可以拿到 headers、query string、stage variables、來源 IP 等多項資訊。

**快取**是 Lambda authorizer 的關鍵設定：API Gateway 可以依「identity source」（例如 `Authorization` header 的值）快取授權結果，預設 300 秒、最長 3,600 秒。同一個 token 在快取期間內再次呼叫，不會再觸發 authorizer 函式，大幅降低延遲與對舊系統的壓力。代價是 token 被撤銷後，快取期間內仍可能被放行；另外要注意 policy 若只允許「目前這個 method」，快取後同一 token 呼叫其他 method 可能被誤拒，所以通常回傳涵蓋多個 method 的 policy，或把 method 納入 identity source。

### Resource policy（REST）

前面看過 private API 的 resource policy。它也能用在 public REST API：只允許某些來源 IP 範圍（`aws:SourceIp`）、只允許某些 AWS 帳號、或拒絕特定 VPC 以外的來源。Resource policy 回答的是「從哪裡、哪個帳號可以呼叫」，和上面三種「這個使用者是誰」的授權可以疊加使用。

### API key 不是身份驗證

**API key** 是一串字串，client 放在 `x-api-key` header 裡送出。它的用途是**識別「這是哪一個 client」以便套用 usage plan 計量與限流**（20.8 節）。

AWS 明確說明不應該用 API key 當作授權或身份驗證機制：它沒有過期機制、不代表任何使用者、很容易被寫死在 App 裡被反編譯取出、被分享給別人。正確做法是 API key（計量）搭配 Cognito／IAM／Lambda authorizer（驗證身份）一起使用。

> [!warning] 常見誤解
> 「CORS 可以防止別人呼叫我的 API。」CORS 只是瀏覽器的規則，決定「網頁上的 JavaScript 能不能讀取跨網域的回應」。用 curl、Postman 或後端程式呼叫完全不受 CORS 限制。CORS 不是安全機制，授權才是。

### 授權方式怎麼選

| 情境 | 選擇 |
|---|---|
| 呼叫者是 AWS 內的程式（Lambda、EC2、跨帳號服務） | IAM authorization（SigV4） |
| 終端使用者登入 Cognito user pool | REST：Cognito authorizer；HTTP：JWT authorizer |
| 企業 IdP 發的 OIDC JWT | HTTP API JWT authorizer（或 Lambda authorizer） |
| 不透明 token、要查資料庫、要自訂邏輯 | Lambda authorizer（開啟快取） |
| 限制來源 IP／VPC endpoint／帳號 | Resource policy（REST） |
| 識別合作夥伴以計量與限流 | API key + usage plan（再搭配真正的授權） |

## 20.8 保護後端：throttling、usage plans 與 WAF

現在處理故事裡最痛的問題：一個合作夥伴的錯誤程式拖垮了所有人。

### Throttling 的原理：token bucket

API Gateway 的限流使用 **token bucket（權杖桶）演算法**。想像一個桶子，每秒以固定速率（**rate**，例如每秒 100 個）放入權杖，桶子最多裝 **burst**（例如 200 個）個。每個請求要拿走一個權杖才能通過；桶子空了，請求就被拒絕，回應 **429 Too Many Requests**。

這個設計允許短暫的突發流量（桶子裡累積的權杖可以一次用掉），但長期平均不能超過 rate。Client 收到 429 時，應該以 exponential backoff 重試（第 33、35 章）。

### 限流的層級

API Gateway 的限流由外到內有幾層，請求必須同時通過每一層：

1. **帳號層級（每個 Region）**：所有 API 共用的上限，預設約每秒 10,000 個請求、burst 5,000（預設 quota，可申請提高）。這代表一個失控的 API 可能吃掉同帳號其他 API 的額度，這也是 SAP 建議把重要 API 放在不同帳號的原因之一。
2. **Stage 與 method 層級**：可以為整個 stage 或個別 method 設定較低的上限，例如 `GET /hotels/{id}` 每秒 500 個。
3. **Usage plan 的 per-client 層級**（REST API）：依 API key 為每個 client 設定各自的上限。

HTTP API 也能設定 stage 與 route 層級的限流，但沒有 per-client 的 usage plan。

### Usage plans 與 API keys

**Usage plan** 是 REST API 的「方案」設定，裡面包含：

- **Throttle**：每秒 rate 與 burst。
- **Quota**：每天、每週或每月的總請求數上限。
- 適用於哪些 API 與 stage。

再把一或多個 API key 關聯到 usage plan，並在 method 上勾選「API key required」。小林為合作夥伴設計了三個方案：

| 方案 | Rate／Burst | 每月 Quota | 對象 |
|---|---|---|---|
| Free | 10／20 | 100,000 | 試用中的小型夥伴 |
| Partner | 200／400 | 20,000,000 | 簽約比價網站 |
| Internal | 不另設（受 stage 限制） | 不設 | Wanderly 自己的 App |

這樣比價網站的爬蟲再失控，也只會讓它自己收到 429，其他人不受影響。

> [!warning] 常見誤解
> Usage plan 的 throttle 與 quota 是 **best-effort（盡力而為）**，AWS 文件明確說明請求數可能短暫超過設定值。它適合保護系統與做流量整形，但如果是「付費方案每月最多 100 萬次，多一次都不行」這種帳務上的硬性限制，必須在後端用 DynamoDB 等持久化計數器自己強制執行。

### 保護 Lambda 與下游

API Gateway 的限流擋的是「進門的請求數」，但後端還有自己的瓶頸：Lambda 的 concurrency、資料庫的連線數。完整的保護是多層的：

- API Gateway stage／method throttling：限制進入的速率。
- Lambda **reserved concurrency**（第 19 章）：讓單一函式最多使用固定的 concurrency，既保證它有額度可用，也防止它吃光帳號額度、壓垮資料庫。
- 寫入路徑改用 SQS 緩衝（20.6 節的 storage-first），讓後端以自己的速度處理。

### AWS WAF

Throttling 只看請求數，不看請求內容。要擋 SQL injection、已知惡意 IP、特定國家、或「單一 IP 五分鐘內超過 2,000 次」這類規則，要把 **AWS WAF web ACL** 關聯到 REST API 的 stage（第 16 章）。WAF 的 **rate-based rule** 依來源 IP 或其他 key 計數，比 usage plan 更適合處理「沒有 API key 的匿名濫用者」。

HTTP API 不能直接關聯 WAF。如果需要 HTTP API 的低價又需要 WAF，可以在前面放一個 CloudFront distribution 並在 CloudFront 上掛 WAF，但要另外防止 client 繞過 CloudFront 直接打 HTTP API 的網址：常見做法是由 CloudFront 在轉送給 origin 的請求加上一個秘密的 custom header，再由 Lambda authorizer 或後端程式驗證這個 header，沒有的請求一律拒絕。

## 20.9 Caching：同樣的答案不必問兩次

小林的第三個需求：同一間旅館的資料一分鐘內不會變。**API caching** 是 REST API 的 stage 層級功能：

- 啟用時選擇快取容量，範圍從 0.5 GB 到 237 GB，**按小時計費**（不論命中率）。
- **TTL** 預設 300 秒，可設 0 到 3,600 秒，0 表示停用。
- **Cache key** 決定「哪些請求算同一個」。你要明確指定哪些路徑參數、query string 與 header 要納入 cache key；沒有納入的參數，不同值的請求會被當成同一筆快取。例如 `GET /hotels/{id}?lang=zh-TW`，若沒把 `lang` 納入 cache key，中文使用者可能拿到英文的快取內容；使用 proxy 資源時尤其要確認 `id` 這類路徑參數有在 cache key 裡。
- 可以針對個別 method 覆寫設定，例如 `GET /hotels/{id}` 快取 60 秒，`GET /hotels/{id}/availability`（即時房況）不快取。通常只對 GET 啟用；POST 這類會改變狀態的請求不應快取。
- Client 可以在請求 header 送 `Cache-Control: max-age=0` 要求略過快取，但你應該要求這個動作必須經過授權（需要 `execute-api:InvalidateCache` 權限），否則任何人都能讓快取失效、把流量直接打到後端。

快取命中時，請求在 API Gateway 就結束，不會呼叫 Lambda，也不會讀 DynamoDB。對讀多寫少的 API，這能同時降低延遲與成本。

> [!note] 其他快取層
> API caching 不是唯一選擇。你也可以用 regional endpoint 加上自己的 CloudFront distribution，在 edge 快取 GET 回應（第 11 章），對全球使用者延遲更低，也支援 HTTP API；或在 Lambda 後面放 ElastiCache、在 DynamoDB 前面放 DAX（第 28 章）。選擇依據是「哪一層的資料最適合被快取、失效要多精準」。

## 20.10 Request validation、CORS 與錯誤碼

### Request validation

REST API 可以在 method 上設定 **request validator**，檢查：

- 必要的 query string、header、路徑參數是否存在。
- Request body 是否符合你定義的 **model**（JSON Schema）。例如 `POST /bookings` 的 body 必須有 `hotelId`（字串）與 `nights`（1 到 30 的整數）。

不合格的請求直接回 **400 Bad Request**，不會呼叫後端。這省下 Lambda 執行費用，也讓後端少寫一層防禦性檢查（但後端仍應做商業規則驗證）。

### CORS：瀏覽器為什麼擋住了我的請求

Wanderly 的網站在 `https://www.wanderly.example`，API 在 `https://api.wanderly.example`。對瀏覽器來說這是兩個不同的 **origin（來源，由協定 + 網域 + port 組成）**。瀏覽器的 **same-origin policy** 預設禁止網頁上的 JavaScript 讀取其他 origin 的回應，除非對方的回應明確允許。這套「對方允許」的機制就是 **CORS（Cross-Origin Resource Sharing，跨來源資源共用）**。

運作方式：

1. 對於非簡單請求（例如帶 `Authorization` header、或 `Content-Type: application/json` 的 POST），瀏覽器會先自動送一個 **preflight（預檢）請求**：`OPTIONS /bookings`，詢問「我可以用 POST、帶這些 header 嗎？」
2. API 必須回應 `Access-Control-Allow-Origin`、`Access-Control-Allow-Methods`、`Access-Control-Allow-Headers` 等 header。
3. 預檢通過後，瀏覽器才送出真正的 POST；而真正請求的**回應也必須帶 `Access-Control-Allow-Origin`**，JavaScript 才能讀到內容。

在 API Gateway 上的做法：

- **HTTP API**：在 API 上設定 CORS（允許的 origins、methods、headers），API Gateway 會自動回應 preflight 並在回應加上 header。
- **REST API**：可以用 console 的「Enable CORS」為 resource 建立 `OPTIONS` method（mock integration）。但如果使用 **Lambda proxy integration**，真正請求的回應 header 是 Lambda 產生的，**Lambda 必須自己在回應中加入 `Access-Control-Allow-Origin`**，就像 20.6 節的範例。這是考試最常出的 CORS 陷阱。
- 授權失敗（401／403）或限流（429）這類由 API Gateway 自己產生的錯誤回應，預設不帶 CORS header，瀏覽器會把它顯示成「CORS 錯誤」而遮住真正原因。REST API 可以透過 **gateway responses** 為這些錯誤加上 CORS header。

### 常見錯誤碼與原因

| 狀態碼 | 常見原因 |
|---|---|
| 400 | Request validation 失敗 |
| 401 | 缺少或無效的 token（Cognito／JWT／Lambda authorizer） |
| 403 | 授權被拒、WAF 擋下、resource policy 拒絕；REST API 呼叫不存在的路徑也會回 403 `Missing Authentication Token` |
| 429 | 超過 throttling 或 usage plan quota |
| 502 | Lambda proxy 回傳格式錯誤、Lambda 函式本身拋出未處理錯誤 |
| 504 | 後端超過整合逾時（例如 29 秒） |

用 CloudWatch 指標判斷問題在哪：`Latency` 是 API Gateway 收到請求到回應的總時間，`IntegrationLatency` 是等待後端的時間。如果兩者幾乎相等，瓶頸在後端；如果差距很大，問題可能在 authorizer 或 API Gateway 本身的處理。`4XXError` 與 `5XXError` 分別統計 client 與 server 端錯誤，`CacheHitCount`／`CacheMissCount` 用來評估快取效果。

## 20.11 逾時、payload 上限與長時間工作

### 29 秒整合逾時

REST API 的整合逾時**預設最長 29 秒**：API Gateway 等後端 29 秒還沒回應，就回 504 給 client，即使 Lambda 其實還在執行（Lambda 最長可以跑 15 分鐘）。AWS 自 2024 年起允許 **regional 與 private REST API** 申請把整合逾時提高到 29 秒以上，代價是可能需要降低帳號層級的 throttle quota；edge-optimized API 仍維持 29 秒。HTTP API 的上限是 30 秒。

另一個較新的選項是 REST API 的 **response streaming**：把 proxy integration（Lambda proxy 或 HTTP proxy）的回應傳送模式設為 `STREAM`，API Gateway 一邊收到後端的資料一邊送給 client，最長可串流 15 分鐘、可以超過 10 MB 的回應上限，常用於生成式 AI 聊天逐字輸出。代價是串流時不能使用 API caching 與 VTL 回應轉換，而且仍有閒置逾時（regional／private 5 分鐘、edge-optimized 30 秒）。

考試的重點不是「怎麼調高或串流」，而是「需要很久的工作不該讓 client 一直等」。Wanderly 的「產生年度住宿報表」可能要 3 分鐘，正確設計是**非同步模式**：

```text
 Client                API Gateway            後端
   │ ① POST /reports ──►│──► StartExecution ──► Step Functions（或 SQS → Lambda）
   │ ◄── 202 + jobId ───│                          │ ② 背景執行數分鐘
   │                                               │ ③ 結果寫到 S3，狀態寫到 DynamoDB
   │ ④ GET /reports/{jobId} ──► Lambda 查 DynamoDB 狀態
   │ ◄── {status: DONE, url: presigned S3 URL}
```

① 建立工作的請求立刻回 **202 Accepted** 與工作編號。② 真正的工作在背景執行，不受 29 秒限制。③ 完成後把結果存起來。④ Client 定期查詢狀態（polling），完成後拿到下載網址。若要主動通知，可以改用 WebSocket API 推播，或讓 client 提供 callback URL。

### Payload 上限

- API Gateway 的請求 payload 上限是 **10 MB**。
- Lambda 同步呼叫的 payload 上限是 **6 MB**（第 19 章），所以經過 Lambda proxy 的請求實際上受 6 MB 限制。

Wanderly 的旅館業者要上傳 50 MB 的高解析照片，不應該經過 API。標準做法是：client 呼叫 `POST /uploads` 取得一個 **S3 presigned URL**（帶有時效與簽章的上傳網址，第 22 章），然後**直接上傳到 S3**，S3 事件再觸發縮圖 Lambda。檔案不經過 API Gateway 與 Lambda，既沒有大小限制，也不佔用它們的執行時間與費用。

## 20.12 Mutual TLS 與 private API 的進階用法

### Mutual TLS（mTLS）

一般 HTTPS 只有 server 出示憑證證明自己的身份。**Mutual TLS** 要求 client 也出示憑證，API Gateway 用你提供的 **truststore**（一份信任的 CA 憑證清單，存在 S3）驗證 client 憑證是否由信任的 CA 簽發，沒有有效憑證的連線在 TLS 交握階段就被拒絕。

使用時機：B2B API、金融或 IoT 裝置，合約或法規要求「只有持有我們發出的憑證的系統才能連線」。

設定重點：

- mTLS 設定在 **regional custom domain name** 上（REST API 與 HTTP API 都支援）。
- **要停用 API 的預設 `execute-api` endpoint**，否則 client 可以繞過 custom domain，直接用預設網址呼叫而不需出示憑證。
- 可以把 client 憑證的資訊傳給 Lambda authorizer 做進一步檢查（例如憑證的 subject 是否在允許清單）。

### Private API 的幾個細節

- Private API 的 interface endpoint 若啟用 private DNS，VPC 內所有對 `*.execute-api.{region}.amazonaws.com` 的解析都會指向這個 endpoint。結果是：**這個 VPC 內的程式無法再用預設網址呼叫其他 public 的 regional 或 edge-optimized API**。要呼叫 public API，可以改用它們的 custom domain，或不在這個 VPC 啟用 private DNS 而改用 endpoint 專屬的 DNS 名稱。
- 跨帳號：API 在 A 帳號，呼叫者在 B 帳號的 VPC。B 帳號在自己的 VPC 建立 `execute-api` interface endpoint，A 帳號的 resource policy 用 `aws:SourceVpce` 允許 B 的 endpoint ID。同一個 interface endpoint 可以存取多個帳號的多個 private API。
- 地端系統可以經 VPN 或 Direct Connect（第 8 章）連到 VPC，再透過 interface endpoint 呼叫 private API。

## 20.13 WebSocket API：伺服器主動推播

現在處理行銷部門的需求：使用者正在看某間旅館，房價一變就要即時出現在畫面上。用一般 HTTP API 只能讓 client 每幾秒問一次（polling），浪費請求又不夠即時。

**WebSocket** 是一種建立在 HTTP 之上的協定：client 先送一個 HTTP 升級請求，成功後雙方保持一條長連線，任何一方都可以隨時送訊息。

### WebSocket API 的運作

```text
 瀏覽器                     API Gateway (WebSocket)              後端
   │ ① wss://ws.wanderly... ─► $connect route ──► Lambda：存 connectionId 到 DynamoDB
   │ ② {"action":"watch","hotelId":"123"} ─► "watch" route ──► Lambda：記錄訂閱
   │
   │                         房價更新事件 ──► Lambda（由 EventBridge 觸發）
   │                                          │ ③ 查 DynamoDB：誰在看 hotel 123？
   │ ◄── ④ 推播新房價 ─────── POST @connections/{connectionId} ◄┘
   │
   │ ⑤ 關閉頁面 ─────────────► $disconnect route ──► Lambda：刪除 connectionId
```

① 連線建立時觸發 **`$connect`** route，這是做授權（IAM 或 Lambda authorizer）的地方。API Gateway 給每條連線一個 **connection ID**，後端通常把它存到 DynamoDB。② 連線後 client 送的每個訊息，API Gateway 依 **route selection expression**（例如 `$request.body.action`）決定交給哪個 route；沒有匹配的走 **`$default`**。③④ 後端要推播時，呼叫 API Gateway 提供的 **`@connections` API**（`POST https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/@connections/{connectionId}`），指定 connection ID 把訊息送給那個 client。⑤ 連線結束時觸發 **`$disconnect`**（盡力而為，不保證每次都觸發，所以 DynamoDB 裡的 connection ID 也應設定 TTL 清理）。

重點是：**API Gateway 負責維持連線，Lambda 不需要一直執行**。Lambda 只在有訊息時被呼叫，執行完就結束，所以可以用 serverless 的方式做即時應用。

WebSocket 連線有時間限制：閒置約 10 分鐘會被關閉、單一連線最長 2 小時，client 要實作斷線重連與心跳訊息。

## 20.14 AppSync：GraphQL 與即時資料

Wanderly 的手機 App 首頁要同時顯示：使用者資料（DynamoDB）、推薦旅館（另一個微服務的 REST API）、近期訂單（Aurora）。用 REST 風格的 API，App 要呼叫三次，每次還會拿到很多用不到的欄位；在行動網路上，這些來回很明顯。

**GraphQL** 是一種 API 查詢語言：server 定義一份 **schema**（有哪些型別、欄位與它們的關係），client 在一個請求中精確描述「我要哪些欄位」，server 只回傳這些欄位。GraphQL 有三種操作：**query**（讀取）、**mutation**（寫入）、**subscription**（訂閱即時更新）。

**AWS AppSync** 是 AWS 的受管 GraphQL 服務：

- **Resolver** 定義每個欄位要從哪裡取得資料；**data source** 可以是 DynamoDB、Lambda、Aurora（透過 Data API）、OpenSearch、HTTP endpoint、EventBridge 等。一個 query 可以同時從多個 data source 組合結果。
- **Subscriptions**：client 透過 WebSocket 訂閱某個 mutation，資料一變就即時收到通知，不需要自己管理 connection ID。例如「訂閱 hotel 123 的房價更新」。
- 授權模式：API key、IAM、Cognito user pool、OIDC、Lambda，可以同時啟用多種，並在 schema 的欄位層級控制誰能讀寫。
- 內建伺服器端快取，並可關聯 AWS WAF。
- 搭配 Amplify 的 client 函式庫，支援行動裝置的離線資料與重新連線後同步。

> [!tip] 考試提示
> 題目出現 **GraphQL**、「一次請求從多個資料來源取得資料」「避免 over-fetching」「行動 App 離線同步」「即時訂閱資料變更」，答案通常是 AppSync。只需要即時推播自訂訊息、不需要 GraphQL 的情境，API Gateway WebSocket API 也是合理選擇；兩者的差別在於 AppSync 以「資料變更」為中心、自動處理訂閱分發。

## 20.15 組起來：Wanderly 的上線版 serverless API

把本章所有元件放在一起：

```text
                     使用者（瀏覽器／App）          合作夥伴（比價網站）
                        │                              │ x-api-key + JWT
            ┌───────────┴───────────┐                  │
            ▼                       ▼                  ▼
  ① CloudFront + S3           ② Cognito user pool   ③ api.wanderly.example
     （靜態網站）                （登入取得 JWT）        （REST API，regional，WAF）
                                                       │
           ┌─────────────────┬─────────────────┬───────┴──────────┐
           ▼                 ▼                 ▼                  ▼
   GET /hotels/{id}   POST /bookings     POST /uploads     POST /reports
   （cache 60 秒）    （Cognito 授權、     （回傳 S3          （Step Functions
      │                request validation）  presigned URL）    StartExecution）
      ▼                 ▼                    │                    │
   Lambda ──► DynamoDB  SQS ──► Lambda ──► DynamoDB  ④ S3 ──► 縮圖 Lambda
                        （storage-first）                       ⑤ 結果寫 S3
   ⑥ 房價變更事件 ──► Lambda ──► WebSocket API @connections ──► 正在瀏覽的使用者
```

① 網站本身是靜態檔案，放在 S3，經 CloudFront 提供（第 11、22 章）。② 使用者在 Cognito user pool 登入，拿到 JWT。③ 所有 API 請求進入 regional REST API（因為需要 usage plans、caching、request validation 與 WAF），前面以 custom domain 提供固定網址。讀取旅館資料走快取，命中時不呼叫 Lambda；下單請求經 Cognito authorizer 與 request validation，再直接整合 SQS，由 Lambda 批次寫入 DynamoDB。④ 大檔案上傳不經 API，client 拿 presigned URL 直接上傳 S3。⑤ 長時間報表交給 Step Functions。⑥ 房價變動透過 WebSocket API 推播。

### 用 SAM 描述（節錄）

正式環境應以 IaC 建立（第 37 章）。以下用 **AWS SAM**（Serverless Application Model，CloudFormation 的 serverless 擴充）示範 Wanderly 內部後台使用的 HTTP API，它只需要 JWT 驗證與 Lambda proxy，因此選擇較便宜的 HTTP API：

```yaml
Transform: AWS::Serverless-2016-10-31
Resources:
  AdminApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: prod
      Auth:
        DefaultAuthorizer: CognitoJwt
        Authorizers:
          CognitoJwt:
            IdentitySource: $request.header.Authorization
            JwtConfiguration:
              issuer: !Sub https://cognito-idp.${AWS::Region}.amazonaws.com/${AdminUserPool}
              audience:
                - !Ref AdminUserPoolClient
      CorsConfiguration:
        AllowOrigins:
          - https://admin.wanderly.example
        AllowMethods:
          - GET
          - POST
        AllowHeaders:
          - Authorization
          - Content-Type

  ListBookingsFn:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.12
      Handler: app.list_bookings
      CodeUri: src/
      Timeout: 10
      Policies:
        - DynamoDBReadPolicy:
            TableName: !Ref BookingsTable
      Events:
        List:
          Type: HttpApi
          Properties:
            ApiId: !Ref AdminApi
            Path: /bookings
            Method: GET
```

讀這段 template 時注意三件事：JWT authorizer 的 `issuer` 是 Cognito user pool 的網址、`audience` 是允許的 app client ID，API Gateway 會拒絕其他來源的 token；CORS 只允許後台網站的 origin；Lambda 函式的 Timeout 設為 10 秒，遠低於 HTTP API 的 30 秒整合上限，避免 client 等到 API Gateway 逾時才知道失敗。`AdminUserPool`、`AdminUserPoolClient`、`BookingsTable` 是同一份 template 中其他資源，這裡省略。

## 20.16 比較與選型

### 我該用哪一種 API 入口？

```text
需要 GraphQL、多資料來源組合、資料變更訂閱、行動離線同步？
├─ 是 → AppSync
└─ 否 → 需要 server 主動推播、雙向長連線？
         ├─ 是 → API Gateway WebSocket API
         └─ 否 → 需要以下任一？API keys／usage plans、caching、request validation、
                  WAF 直接關聯、private endpoint、edge-optimized、resource policy、
                  mapping templates、canary release
                  ├─ 是 → REST API
                  └─ 否 → 需要 API 管理（JWT 驗證、限流、CORS、多路由）？
                           ├─ 是 → HTTP API
                           └─ 否 → 單一函式的 webhook → Lambda function URL
                                    已有 ALB、持續高流量的內部 HTTP 服務 → ALB + Lambda／containers
```

### 入口選項對照

| 選項 | 最適合 | 主要限制 |
|---|---|---|
| REST API | 對外公開 API、夥伴方案、需要快取與驗證 | 單價較高；整合逾時預設 29 秒 |
| HTTP API | 一般 Lambda／HTTP proxy、JWT 驗證、成本敏感 | 無 usage plans、caching、WAF、private endpoint |
| WebSocket API | 聊天、即時通知、遊戲、即時儀表板 | 連線閒置與最長時間有限制；要自己管理 connection ID |
| AppSync | GraphQL、行動 App、多資料來源、即時訂閱 | 需要學習 GraphQL 與 resolver 設計 |
| Lambda function URL | 單一函式、webhook、簡單內部工具 | 無限流、API key、自訂授權器、快取 |
| ALB + Lambda | 已有 ALB、與 container 服務共用入口 | 無 API 管理功能；按小時與 LCU 計費 |

### 長時間或大檔案的處理

| 問題 | 錯誤做法 | 正確做法 |
|---|---|---|
| 工作超過 29 秒 | 只調高 Lambda timeout | 非同步：202 + jobId，Step Functions／SQS，polling 或推播 |
| 上傳超過 10 MB | 把檔案轉成 base64 放進 body | S3 presigned URL，直接上傳 S3 |
| 尖峰寫入不能遺失 | 增加 Lambda concurrency | API Gateway 直接整合 SQS（storage-first） |

## 20.17 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 每個 client／夥伴有自己的額度、每月 quota、API key | REST API usage plans + API keys |
| 只要 JWT 驗證與 Lambda proxy、成本最低 | HTTP API + JWT authorizer |
| 使用者已在 Cognito user pool 登入、不寫程式驗證 | Cognito user pool authorizer（REST）／JWT authorizer（HTTP） |
| 自訂 token、呼叫舊系統驗證、要查資料庫決定權限 | Lambda authorizer（開啟結果快取） |
| AWS 內的服務或跨帳號程式呼叫 API | IAM authorization（SigV4）+ resource policy |
| API 只能從 VPC 內部存取、不經 Internet | Private REST API + `execute-api` interface endpoint + resource policy（`aws:SourceVpce`） |
| 全球使用者、公開 API、降低連線延遲 | Edge-optimized endpoint（或 regional + 自己的 CloudFront） |
| Edge-optimized custom domain 的憑證 | ACM 憑證在 us-east-1 |
| 降低重複 GET 的延遲與 Lambda 呼叫 | REST API stage caching（TTL、cache key） |
| Body 格式錯誤時不要呼叫 Lambda | Request validation（model／JSON Schema） |
| 瀏覽器顯示 CORS 錯誤、使用 Lambda proxy | Lambda 回應要帶 `Access-Control-Allow-Origin`；OPTIONS 要處理 preflight |
| 工作需要數分鐘、client 收到 504 | 非同步模式（202 + jobId、Step Functions／SQS） |
| 上傳大檔案（> 10 MB） | S3 presigned URL |
| 尖峰流量、訂單不可遺失、減少 Lambda 程式碼 | API Gateway 直接整合 SQS |
| 伺服器主動推播、聊天室、即時通知 | WebSocket API（`$connect`、`@connections`） |
| GraphQL、多資料來源、離線同步、即時訂閱 | AppSync |
| 合作夥伴必須出示 client 憑證 | Mutual TLS（regional custom domain + truststore，停用預設 endpoint） |
| 擋 SQL injection、單一 IP 過量請求 | AWS WAF（managed rules、rate-based rule）關聯 REST API stage |
| 回應 429／502／504 | 限流／Lambda proxy 格式錯誤／整合逾時 |

**常見陷阱**：

1. 把 API key 當作身份驗證：API key 只用來識別 client 與套用 usage plan，必須搭配真正的授權機制。
2. 選 HTTP API 卻要求 usage plans、caching 或 WAF：這些是 REST API 專屬功能。
3. 以為 edge-optimized endpoint 會快取 API 回應：它只是透過 CloudFront 網路加速連線，快取要另外啟用。
4. 以為把 Lambda timeout 調到 15 分鐘，API 就能等 15 分鐘：API Gateway 有自己的整合逾時。
5. 修改 REST API 後忘了重新 deploy 到 stage：變更不會生效。
6. 以為 CORS 能擋住非瀏覽器的呼叫：CORS 只約束瀏覽器，不是授權機制。
7. 以為 usage plan quota 是精確的硬性上限：它是盡力而為，帳務級硬限制要在後端實作。

## 20.18 SAP 加深：多 Region、多帳號與大規模 API 治理

### 多 Region active-active API

SAP 題目常要求「一個 Region 故障時 API 在幾分鐘內恢復」。API Gateway 是 regional 服務，**不會自動跨 Region 複寫**，所以要在每個 Region 各自部署一份完整的 API 與後端：

1. 每個 Region 部署 **regional** REST 或 HTTP API、Lambda、資料層（例如 DynamoDB global tables，第 27、42 章）。
2. 每個 Region 建立**同名的 regional custom domain**（例如 `api.wanderly.example`），各自使用**該 Region 的 ACM 憑證**。
3. Route 53 以 **latency-based** 或 **failover** routing 把同一個網域導向各 Region 的 custom domain 目標，並搭配 **health check**（最好是檢查真正業務路徑的 `/health`，而非只檢查 API Gateway 是否回應）。
4. 寫入要設計 **idempotency key**（第 33 章），因為切換期間 client 重試可能讓同一筆訂單送到兩個 Region。

這裡不用 edge-optimized，因為 edge-optimized custom domain 背後是單一 Region 的 API，無法用 Route 53 做跨 Region 選路；regional endpoint 才能讓你掌控每個 Region 的入口。

### 多帳號的 API 架構

- **集中入口帳號**：由平台團隊擁有 custom domain、WAF、對外 REST API，透過 HTTP integration 或 private integration 呼叫各業務帳號的後端。好處是入口治理一致，代價是平台帳號的 API Gateway 帳號層級 quota 被所有流量共用。
- **分散擁有**：每個業務帳號擁有自己的 API，只在 custom domain 層用 base path mapping 組合（custom domain 與 API 需在同一帳號），或用 CloudFront 依路徑導向不同帳號的 regional API。好處是爆炸半徑小、quota 獨立。
- 內部 API 之間的呼叫可以用 **private API + 跨帳號 interface endpoint**，或改用 **VPC Lattice**（第 7 章）做服務對服務的連線與 IAM 授權。

### 從單體遷移

既有的 EC2 或地端單體應用要現代化時，常見做法是把 API Gateway 放在最前面：先以 HTTP proxy 把所有路徑轉給舊系統（地端系統可經 VPN／Direct Connect 加上 VPC link 連到 NLB），再一條一條路徑改接到 Lambda 或 containers。Client 看到的網址不變，遷移可以逐步、可回退。這是第 46 章 strangler fig 模式在 API 層的實作。

### 成本思考

- REST 與 HTTP API 的價差在每月數十億次請求時非常明顯；若只用到 proxy 與 JWT，從 REST 換到 HTTP API 是常見的成本最佳化題目。
- API caching 按小時收費，命中率低的 API 開了反而更貴；先看 `CacheHitCount` 再決定。
- 一個只是轉送資料的 Lambda 函式，改成 direct service integration 可以同時省下 Lambda 費用與延遲。
- 對穩定高流量的內部服務，ALB 按 LCU 計費可能比按請求計費的 API Gateway 便宜，但要放棄 API 管理功能。

延伸閱讀：[Choose between REST APIs and HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html)、[API endpoint types](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-endpoint-types.html)、[Usage plans and API keys](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)、[Private REST APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-private-apis.html)、[Lambda authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)。

## 本章重點整理

- API Gateway 是受管的 API 門口：TLS、WAF、resource policy、授權、限流、驗證、快取都在請求到達後端之前完成，後端只處理商業邏輯。
- REST API 功能最完整（usage plans、caching、request validation、WAF、private 與 edge-optimized endpoint）；HTTP API 較便宜、較快，原生支援 JWT authorizer，但沒有那些 REST 專屬功能；WebSocket API 提供雙向長連線。
- Edge-optimized 經 AWS 代管的 CloudFront 加速連線但不快取回應，custom domain 憑證在 us-east-1；regional 憑證在同 Region；private API 只能經 `execute-api` interface endpoint 存取，必須設定 resource policy。
- REST API 的變更要建立 deployment 並部署到 stage 才生效；stage variables 可以讓不同 stage 指向不同的 Lambda alias，stage 也支援 canary release。
- Lambda proxy integration 要求 Lambda 回傳 `statusCode`、`headers`、`body` 格式，格式錯誤會得到 502；AWS service integration 可以不經 Lambda 直接呼叫 SQS、Step Functions、DynamoDB 等服務。
- 授權：AWS 內的呼叫者用 IAM（SigV4）；Cognito 使用者用 Cognito authorizer 或 JWT authorizer；自訂邏輯用 Lambda authorizer 並開啟快取；API key 只用於識別與計量，不是身份驗證。
- 限流使用 token bucket，層級是帳號（每 Region 預設約 10,000 RPS、burst 5,000，可申請提高）→ stage／method → usage plan；超過回 429；usage plan 的限制是盡力而為。
- API caching 是 REST API 的 stage 功能，TTL 預設 300 秒、最長 3,600 秒，按快取容量按小時計費，cache key 要包含會影響回應的參數。
- 使用 Lambda proxy 時，CORS 的 `Access-Control-Allow-Origin` 要由 Lambda 回應帶上；CORS 不是安全機制。
- REST API 整合逾時預設 29 秒（regional／private 可申請提高），HTTP API 為 30 秒；長時間工作應改為非同步（202 + jobId）。
- API Gateway payload 上限 10 MB、Lambda 同步 6 MB；大檔案用 S3 presigned URL 直接上傳。
- Mutual TLS 設定在 regional custom domain 上，需停用預設 endpoint 防止繞過。
- WebSocket API 用 `$connect`、`$disconnect`、`$default` 與自訂 route 處理訊息，後端以 `@connections` API 主動推播。
- AppSync 是受管 GraphQL：一次請求組合多個資料來源、subscription 即時訂閱、多種授權模式、支援離線同步。
- 多 Region API 要在每個 Region 部署 regional API 與同名 custom domain，再以 Route 53 latency／failover routing 與 health check 導流。

## 本章練習題

### 練習 20-1｜SAA｜單選｜REST API 與 HTTP API 選型

Wanderly 要為內部後台建立一組新 API。所有請求都帶有公司 Cognito user pool 發出的 JWT，後端是 Lambda proxy integration。團隊確認不需要 API keys、usage plans、回應快取或 request validation，希望在滿足需求的前提下讓每月的 API 費用最低，並且不想撰寫驗證 token 的程式碼。

應該選擇哪個方案？

- A. REST API 搭配 Cognito user pool authorizer
- B. HTTP API 搭配 JWT authorizer
- C. REST API 搭配 Lambda authorizer 驗證 JWT
- D. Lambda function URL 搭配 `AWS_IAM` 授權

> [!answer]- 答案：B
> **A ✗** REST API 加 Cognito authorizer 技術上可行，也不用寫程式，但 REST API 的請求單價較高，而題目明確不需要任何 REST 專屬功能，不是成本最低的選項。
>
> **B ✓** HTTP API 原生的 JWT authorizer 只要設定 issuer 與 audience 就能驗證 Cognito 發出的 token，完全不需寫程式；它的單價低於 REST API，且題目列出的功能都不需要，正好落在 HTTP API 的能力範圍內。
>
> **C ✗** Lambda authorizer 需要自己撰寫與維護驗證 JWT 的程式，每次未命中快取還要多執行一次 Lambda，違反「不想寫驗證程式」，費用也更高。只有在 token 不是標準 JWT 或需要自訂邏輯時才適合。
>
> **D ✗** Function URL 的 `AWS_IAM` 授權要求呼叫者用 AWS 憑證做 SigV4 簽章，無法直接接受 Cognito user pool 的 JWT；而且每個函式各有一個網址，無法組成一組有多條路由的 API。
>
> **考點**：SAA-4.2、SAA-1.2｜HTTP API 與 JWT authorizer 的適用範圍

### 練習 20-2｜SAA｜單選｜合作夥伴各自的額度

Wanderly 將對 30 家合作夥伴開放旅館查詢 API。商務部門規定：不同等級的夥伴每秒請求數與每月總請求數上限不同，某一家夥伴的流量暴增時不能影響其他夥伴。夥伴呼叫時另外會帶 OAuth token 證明身份。

哪個設計最符合需求？

- A. 使用 HTTP API，並在每條 route 上設定 throttling
- B. 使用 REST API，並把 Lambda 的 reserved concurrency 依夥伴數量平均分配
- C. 使用 REST API，並以 WAF rate-based rule 依來源 IP 限制每家夥伴
- D. 使用 REST API，為每個等級建立 usage plan，設定 throttle 與每月 quota，並為每家夥伴發一把 API key 關聯到對應方案

> [!answer]- 答案：D
> **A ✗** HTTP API 的 route 層級限流是所有呼叫者共用的，無法區分不同夥伴，也沒有每月 quota；一家夥伴暴增仍會吃掉其他人的額度。
>
> **B ✗** Reserved concurrency 設在函式層級，不知道請求來自哪個夥伴；同一個函式的額度仍由所有夥伴共用，也無法表達每月總量。
>
> **C ✗** WAF rate-based rule 能擋單一 IP 的過量請求，但夥伴的來源 IP 可能很多且會變動，也無法設定每月總量或不同等級的方案。
>
> **D ✓** Usage plan 是 REST API 專門用於 per-client 計量與限流的功能：每個方案有 rate、burst 與 quota，每把 API key 關聯到一個方案，超量者只會讓自己收到 429。API key 用於識別夥伴，OAuth token 仍負責驗證身份。
>
> **考點**：SAA-2.1、SAA-1.2｜usage plans 與 API keys

### 練習 20-3｜SAA｜單選｜超過 29 秒的工作

Wanderly 的旅館業者可以在後台點擊「產生年度營收報表」。這個 REST API 背後的 Lambda 函式需要 2 到 5 分鐘才能完成。目前使用者經常在約 30 秒後收到 504 錯誤，但 CloudWatch Logs 顯示 Lambda 最後仍執行成功。團隊希望使用者能可靠地拿到報表，並且不讓 client 長時間占用連線。

最合適的做法是什麼？

- A. 讓 API 收到請求後啟動 Step Functions 執行報表工作並立即回傳 202 與工作編號，client 再以另一個 API 查詢狀態，完成後取得 S3 presigned URL 下載
- B. 把 Lambda 函式的 timeout 調到 15 分鐘，並增加記憶體以加快執行
- C. 把 REST API 改成 HTTP API，以取得較長的整合逾時
- D. 在 API Gateway 啟用 caching，讓第二次請求直接取得快取的報表

> [!answer]- 答案：A
> **A ✓** 長時間工作應改為非同步：建立工作的請求立即回應，真正的運算在 Step Functions 背景執行，不受 API Gateway 整合逾時影響；client 用工作編號輪詢狀態，完成後下載存在 S3 的結果。
>
> **B ✗** 504 來自 API Gateway 的整合逾時，不是 Lambda 的 timeout。Lambda 本來就有執行完，調高它的 timeout 不會讓 API Gateway 等更久；增加記憶體也很難把 5 分鐘縮到 29 秒以內。
>
> **C ✗** HTTP API 的整合逾時上限是 30 秒，只比 REST 多 1 秒，仍遠低於 2 到 5 分鐘。（申請提高 REST 整合逾時或使用 response streaming 雖然可以讓連線撐更久，但都是讓 client 一直等，不符合「不長時間占用連線」。）
>
> **D ✗** 每次產生的報表內容因業者與時間而異，快取無法解決第一次請求就逾時的問題，而且 REST 快取 TTL 最長 3,600 秒，也不適合存放這種結果。
>
> **考點**：SAA-2.1、SAA-3.2｜整合逾時與非同步 API 模式

### 練習 20-4｜SAA｜選兩項｜只能從 VPC 內部呼叫的 API

Wanderly 的財務對帳 API 只給同一帳號內一個 VPC 裡的批次程式呼叫。安全團隊要求這個 API 從 Internet 上完全無法存取，流量也不能經過 Internet 或 NAT Gateway。

哪兩個步驟能滿足需求？（選兩項）

- A. 把 REST API 的 endpoint type 設為 private，並在 VPC 中建立 `execute-api` 的 interface VPC endpoint
- B. 使用 edge-optimized REST API，並要求呼叫時帶 API key
- C. 讓批次程式所在的 private subnet 經 NAT Gateway 呼叫 regional API，並在 security group 限制出站目的地
- D. 為 API 設定 resource policy，拒絕所有 `aws:SourceVpce` 不是該 interface endpoint 的請求
- E. 在 API 上啟用 CORS，只允許批次程式的 origin

> [!answer]- 答案：A、D
> **A ✓** Private endpoint 類型的 REST API 沒有 public 網址，只能經由 `execute-api` interface endpoint 從 VPC 內存取，流量留在 AWS 網路中，不經 Internet 或 NAT。
>
> **B ✗** Edge-optimized API 可從全世界的 Internet 存取；API key 只用於識別與計量，不會關閉 public 入口，也不是身份驗證機制。
>
> **C ✗** 經 NAT Gateway 呼叫的仍是 public endpoint，任何人都能從 Internet 連到它，違反「Internet 完全無法存取」；流量也經過了 NAT。
>
> **D ✓** Private API 必須有 resource policy。用 `aws:SourceVpce` 條件只允許指定的 interface endpoint，可以確保即使其他 VPC 也建立了 endpoint，也無法呼叫這個 API。
>
> **E ✗** CORS 只約束瀏覽器中的 JavaScript，批次程式不是瀏覽器，CORS 對它沒有任何限制作用，更不能阻擋 Internet 存取。
>
> **考點**：SAA-1.2、SAA-3.4｜private REST API 與 resource policy

### 練習 20-5｜SAA｜單選｜CORS 錯誤

Wanderly 的網站 `https://www.wanderly.example` 以 JavaScript 呼叫 `https://api.wanderly.example/bookings`（REST API，Lambda proxy integration），請求帶有 `Authorization` header。工程師已在 console 對 `/bookings` 啟用 CORS，瀏覽器的 `OPTIONS` 預檢請求回應正確，但真正的 `POST` 請求在瀏覽器中仍顯示 CORS 錯誤；用 curl 呼叫同一個 API 則一切正常。

最可能需要修改什麼？

- A. 把 API 改為 edge-optimized endpoint，讓 CloudFront 自動加入 CORS header
- B. 在 resource policy 中允許 `www.wanderly.example` 的來源 IP
- C. 修改 Lambda 函式，讓回應的 headers 包含 `Access-Control-Allow-Origin: https://www.wanderly.example`
- D. 移除 `Authorization` header，改把 token 放在 query string

> [!answer]- 答案：C
> **A ✗** Edge-optimized endpoint 背後的 CloudFront 由 AWS 代管，只做連線加速，不會替你的回應加 CORS header。
>
> **B ✗** CORS 檢查發生在瀏覽器，與來源 IP 無關；curl 呼叫正常也說明 API 授權沒有問題。
>
> **C ✓** 使用 Lambda proxy integration 時，真正請求的回應 header 完全由 Lambda 產生。Console 的「Enable CORS」只處理 OPTIONS 預檢，POST 的回應若沒有 `Access-Control-Allow-Origin`，瀏覽器就不讓 JavaScript 讀取結果。
>
> **D ✗** 把 token 放在 query string 會讓它出現在日誌與瀏覽紀錄中，降低安全性；而且回應缺少 CORS header 的問題依然存在。
>
> **考點**：SAA-1.2｜CORS 與 Lambda proxy integration

### 練習 20-6｜SAA｜單選｜大檔案上傳

Wanderly 的旅館業者需要上傳 20 MB 到 80 MB 的高解析旅館照片，目前的做法是把檔案以 base64 放進 `POST /photos`（REST API + Lambda）的 body，再由 Lambda 寫入 S3，但大檔案一律失敗。團隊希望修改最少、成本最低，並維持只有登入的業者能上傳。

最合適的做法是什麼？

- A. 把 API 改成 HTTP API，以提高 payload 上限
- B. 讓已授權的 API 呼叫回傳一個 S3 presigned URL，client 直接以該 URL 把檔案上傳到 S3
- C. 把 Lambda 的記憶體與 `/tmp` 空間調到 10 GB
- D. 把照片切成 5 MB 的片段，分多次呼叫 API，由 Lambda 在 DynamoDB 中組合

> [!answer]- 答案：B
> **A ✗** HTTP API 的 payload 上限同樣是 10 MB，而且經 Lambda proxy 時還受 Lambda 同步呼叫 6 MB 的限制，換 API 類型解決不了。
>
> **B ✓** API 只負責驗證業者身份並產生有時效、有簽章的 presigned URL，檔案本身直接上傳到 S3，不經過 API Gateway 與 Lambda，沒有它們的大小限制，也不佔用 Lambda 執行時間。S3 事件可以再觸發後續處理。
>
> **C ✗** 限制在 API Gateway 的 10 MB 與 Lambda 同步 payload 的 6 MB，與 Lambda 記憶體或 `/tmp` 無關。
>
> **D ✗** 自己實作分段上傳既複雜又容易出錯；DynamoDB 單一 item 上限 400 KB，也不是存放照片的地方。S3 本身已提供 multipart upload。
>
> **考點**：SAA-3.1、SAA-3.2｜API payload 上限與 S3 presigned URL

### 練習 20-7｜SAA｜單選｜降低重複讀取的成本

Wanderly 的 `GET /hotels/{id}` 每天被呼叫數千萬次，同一間旅館的資料通常一小時才更新一次，偶爾延遲一分鐘顯示新資料可以接受。這個 REST API 背後是 Lambda 讀取 DynamoDB。團隊想同時降低延遲與 Lambda、DynamoDB 費用，並且不修改應用程式碼。

最合適的做法是什麼？

- A. 在 API 的 `prod` stage 啟用 API caching，為這個 method 設定 60 秒 TTL，並確認 cache key 包含 `id` 路徑參數
- B. 為 DynamoDB table 加上 DAX cluster
- C. 為 Lambda 函式設定 provisioned concurrency
- D. 為呼叫者建立 usage plan，限制每秒請求數

> [!answer]- 答案：A
> **A ✓** 快取命中時請求在 API Gateway 就回應，不會呼叫 Lambda，也不會讀 DynamoDB，同時降低延遲與兩者的費用；60 秒 TTL 符合「延遲一分鐘可接受」。路徑參數納入 cache key，不同旅館才不會拿到彼此的資料。
>
> **B ✗** DAX 能降低 DynamoDB 的讀取延遲，但 Lambda 仍然每次都會被呼叫，而且 DAX 需要修改程式使用 DAX client，違反「不修改程式碼」。
>
> **C ✗** Provisioned concurrency 解決 cold start 延遲，但會增加費用，也不會減少 Lambda 呼叫次數與 DynamoDB 讀取。
>
> **D ✗** 限流會拒絕使用者的正常請求，降低的是服務能力而不是重複讀取的成本。
>
> **考點**：SAA-3.2、SAA-4.2｜REST API stage caching

### 練習 20-8｜SAA｜單選｜終端使用者登入的授權

Wanderly 手機 App 的使用者都透過 Amazon Cognito user pool 登入。`POST /bookings`（REST API）必須只允許已登入的使用者呼叫，`GET /hotels/{id}` 則公開。團隊希望以最少的營運負擔完成。

應如何設定？

- A. 為 App 內嵌一把 API key，`POST /bookings` 要求 API key
- B. 撰寫 Lambda authorizer 呼叫 Cognito API 驗證每個 token
- C. 讓 App 使用 IAM user 的 access key 以 SigV4 簽署請求
- D. 建立 Cognito user pool authorizer，套用在 `POST /bookings` method 上，`GET /hotels/{id}` 不設授權

> [!answer]- 答案：D
> **A ✗** 內嵌在 App 中的 API key 很容易被反編譯取出，所有使用者共用同一把 key，它也不代表任何使用者身份，不是授權機制。
>
> **B ✗** Lambda authorizer 可以做到，但需要自己撰寫與維護驗證程式；既然 token 來自 Cognito user pool，原生的 authorizer 營運負擔更低。
>
> **C ✗** 把長期 IAM access key 放進手機 App 是嚴重的安全風險，所有使用者也共用同一組身份。
>
> **D ✓** Cognito user pool authorizer 由 API Gateway 直接驗證 JWT 的簽章與有效期，不需要寫程式；授權是以 method 為單位設定，所以可以只保護 `POST /bookings`，讓查詢 API 保持公開。
>
> **考點**：SAA-1.1、SAA-1.2｜Cognito user pool authorizer

### 練習 20-9｜SAA｜單選｜即時推播房價

Wanderly 希望使用者在瀏覽某間旅館頁面時，若房價變動，畫面能在一秒內自動更新，不需要使用者重新整理。目前做法是前端每 3 秒呼叫一次 `GET /prices`，造成大量無用請求。團隊希望採用 serverless 架構，不想自己管理長時間執行的伺服器。

最合適的做法是什麼？

- A. 把 polling 間隔縮短為每 1 秒，並對 `GET /prices` 啟用 API caching
- B. 在 EC2 Auto Scaling group 上部署自建的 WebSocket 伺服器，前面放 NLB
- C. 建立 API Gateway WebSocket API，在 `$connect` 時把 connection ID 存到 DynamoDB，房價變動時由 Lambda 透過 `@connections` API 推送給正在瀏覽的使用者
- D. 使用 SNS topic，讓瀏覽器直接訂閱房價變動通知

> [!answer]- 答案：C
> **A ✗** 縮短 polling 間隔會讓請求量增加三倍；快取會讓使用者看到最多 TTL 時間前的舊價格，與「一秒內更新」互相矛盾。
>
> **B ✗** 自建 WebSocket 伺服器可行，但需要管理 EC2、擴展與連線狀態，違反 serverless 與不管伺服器的要求。
>
> **C ✓** WebSocket API 由 API Gateway 維持長連線，Lambda 只在有事件時執行。後端以 connection ID 呼叫 `@connections` API，就能主動把訊息推給特定 client，既即時又不需管理伺服器。
>
> **D ✗** SNS 支援 HTTP／HTTPS、email、SMS、SQS、Lambda、行動推播等訂閱，但瀏覽器頁面無法作為 SNS 的訂閱端點直接接收訊息。
>
> **考點**：SAA-2.1、SAA-3.2｜WebSocket API 與 `@connections`

### 練習 20-10｜SAA｜單選｜行動 App 多資料來源

Wanderly 手機 App 的首頁需要同時顯示會員資料（DynamoDB）、近期訂單（Aurora）與推薦旅館（另一個團隊的 HTTP 微服務）。目前 App 要呼叫三個 REST API，在行動網路上載入很慢，而且每個 API 都回傳大量用不到的欄位。產品團隊也希望使用者離線時仍能看到上次的資料，連線恢復後自動同步。

最合適的方案是什麼？

- A. 在 REST API 前面加上 CloudFront，快取三個 API 的回應
- B. 建立 AWS AppSync GraphQL API，以 DynamoDB、Aurora 與 HTTP data source 的 resolver 組合資料，App 搭配支援離線同步的 client 函式庫
- C. 寫一個 Lambda 函式依序呼叫三個 API 並合併結果，透過 HTTP API 提供
- D. 把三種資料全部搬到同一個 DynamoDB table，以單一 REST API 提供

> [!answer]- 答案：B
> **A ✗** CloudFront 能快取 GET 回應，但 App 仍要發三個請求、拿到同樣多的多餘欄位；會員與訂單這類個人化資料也不適合在 edge 共用快取，離線同步更無從實現。
>
> **B ✓** AppSync 讓 App 用一個 GraphQL query 精確指定需要的欄位，由各 resolver 從 DynamoDB、Aurora 與 HTTP 微服務取資料並組合；搭配 Amplify 等 client 函式庫還能提供離線資料與重新連線後同步。
>
> **C ✗** 自己寫聚合 Lambda 可以減少請求次數，但要自行維護組合邏輯、處理欄位挑選，也沒有離線同步能力，營運負擔較高。
>
> **D ✗** 把不同團隊、不同性質的資料硬搬到同一個 table 是大規模重構，Aurora 上的交易資料也未必適合 DynamoDB，而且仍無法解決離線同步。
>
> **考點**：SAA-2.1、SAA-3.2｜AppSync GraphQL 與多資料來源

### 練習 20-11｜SAP｜選兩項｜尖峰訂單不可遺失

Wanderly 在年度促銷時，`POST /bookings` 的流量會在幾分鐘內從每秒 200 次暴增到每秒 8,000 次。目前架構是 REST API → Lambda → Aurora，尖峰時 Lambda 因 Aurora 連線數耗盡而大量失敗，部分訂單遺失。業務要求每一筆訂單請求都必須被持久保存，可以接受訂單在數分鐘內才完成確認；團隊也希望減少需要維護的程式碼。

哪兩個變更組合最合適？（選兩項）

- A. 把 Lambda 的 reserved concurrency 移除，讓它可以擴展到帳號上限
- B. 把 `POST /bookings` 改成 API Gateway 直接整合 SQS `SendMessage`，收到請求後立即回應 202 與訂單編號
- C. 把 REST API 改成 WebSocket API，讓 client 保持連線等待結果
- D. 為 REST API 啟用 caching，讓重複的訂單請求直接回應
- E. 由 Lambda 以 SQS event source mapping 批次消費訊息寫入 Aurora，並以 maximum concurrency 限制同時執行的數量，處理失敗的訊息導向 DLQ

> [!answer]- 答案：B、E
> **A ✗** 移除限制會讓更多 Lambda 同時搶 Aurora 連線，問題只會更嚴重；失敗從 API 層轉移到資料庫層。
>
> **B ✓** 直接整合 SQS 讓請求一進門就被持久化，不需要中間的轉送 Lambda；queue 吸收尖峰，API 立即回應 202，符合「可以數分鐘後確認」。
>
> **C ✗** WebSocket 適合雙向推播，不會改善後端寫入的瓶頸；大量長連線還會增加成本與複雜度。
>
> **D ✗** 建立訂單的 POST 請求每次都不同且會改變狀態，不能快取；快取也不會保存訂單。
>
> **E ✓** 後端以自己能承受的速度從 queue 批次讀取，maximum concurrency 控制同時寫入 Aurora 的數量，保護資料庫連線；失敗訊息進 DLQ 而不會遺失，可以事後重新處理。
>
> **考點**：SAP-2.4、SAP-3.4｜storage-first 與以 queue 削峰

### 練習 20-12｜SAP｜單選｜B2B 夥伴的 client 憑證

Wanderly 與數家航空公司交換訂位資料。合約要求：只有持有 Wanderly 私有 CA 簽發之 client 憑證的系統才能建立 TLS 連線，未持有憑證的連線必須在到達任何應用程式邏輯前就被拒絕。API 目前是 regional REST API，透過預設的 `execute-api` 網址提供給航空公司。

最合適的做法是什麼？

- A. 建立 regional custom domain name，啟用 mutual TLS 並把私有 CA 憑證放在 S3 作為 truststore，讓航空公司改用 custom domain，並停用 API 的預設 endpoint
- B. 在 REST API 上要求 API key，並把 API key 嵌入航空公司系統的憑證欄位中
- C. 撰寫 Lambda authorizer，從 HTTP header 讀取 client 上傳的憑證內容並驗證簽章
- D. 把 API 改成 edge-optimized，並在 us-east-1 匯入私有 CA 憑證到 ACM

> [!answer]- 答案：A
> **A ✓** API Gateway 的 mutual TLS 設定在 regional custom domain 上，以 S3 中的 truststore 驗證 client 憑證，沒有有效憑證的連線在 TLS 交握時就被拒絕。停用預設 endpoint 是必要步驟，否則 client 可以改用預設網址繞過 mTLS。
>
> **B ✗** API key 只是一串字串，與 TLS 憑證驗證無關，無法在 TLS 層拒絕連線，也不是身份驗證機制。
>
> **C ✗** 把憑證內容放在 header 裡只是應用層的資料，TLS 連線已經建立，違反「在到達應用邏輯前拒絕」；而且 header 可以被任意偽造，並不能證明 client 持有對應的私鑰。
>
> **D ✗** Edge-optimized endpoint 不支援 mutual TLS；us-east-1 的 ACM 憑證是給 server 端 custom domain 用的，不是驗證 client 的 truststore。
>
> **考點**：SAP-2.3、SAP-1.2｜API Gateway mutual TLS

### 練習 20-13｜SAP｜單選｜多 Region active-active API

Wanderly 拓展到東南亞後，要求 `api.wanderly.example` 在東京與新加坡兩個 Region 同時提供服務：使用者連到延遲較低的 Region，一個 Region 故障時，流量在數分鐘內自動移到另一個 Region。資料層已改用 DynamoDB global tables。

API 層應如何設計？

- A. 在東京建立一個 edge-optimized REST API，依靠 CloudFront 的全球 edge location 自動在 Region 故障時切換
- B. 在兩個 Region 各建立 REST API，但只在東京建立 custom domain，新加坡的 API 使用預設 `execute-api` 網址作為備援，由 client 程式自行切換
- C. 在兩個 Region 各部署 regional API 與後端，各自建立同名的 regional custom domain 並使用該 Region 的 ACM 憑證，再以 Route 53 latency-based routing 搭配 health check 導流
- D. 在兩個 Region 各部署 regional API，並共用一張 us-east-1 的 ACM 憑證，以 Route 53 weighted routing 各導 50% 流量

> [!answer]- 答案：C
> **A ✗** Edge-optimized 只是讓連線經由 edge 進入，背後仍是東京這一個 Region 的 API；東京故障時沒有其他 Region 可以接手。
>
> **B ✗** 讓 client 自行切換到另一個網址會增加 App 的複雜度與切換時間，且憑證與網域不一致，不符合「自動」與「同一個網域」的需求。
>
> **C ✓** API Gateway 是 regional 服務，必須在每個 Region 各自部署。同名的 regional custom domain 讓兩個 Region 都能接受 `api.wanderly.example` 的請求，Route 53 latency-based routing 把使用者導向較近的 Region，health check 失敗時自動移除故障的 Region。
>
> **D ✗** Regional custom domain 需要與 API 同 Region 的 ACM 憑證，不能共用 us-east-1 的憑證（us-east-1 是 edge-optimized 與 CloudFront 的要求）；weighted 50/50 也不會依延遲選擇最近的 Region。
>
> **考點**：SAP-2.2、SAP-1.3｜多 Region regional API 與 Route 53

### 練習 20-14｜SAP｜單選｜跨帳號私有 API

Wanderly 的支付團隊在 A 帳號提供一個 private REST API，供 B、C 兩個業務帳號 VPC 內的服務呼叫。所有流量必須留在 AWS 私有網路中，A 帳號必須能明確控制哪些呼叫來源被允許，而且新增帳號時不應修改 A 帳號以外的網路架構。

最合適的做法是什麼？

- A. 在 A 帳號的 VPC 建立 `execute-api` interface endpoint，與 B、C 的 VPC 建立 peering，讓它們經 peering 使用 A 帳號的 endpoint
- B. 把 API 改成 regional endpoint，在 resource policy 中只允許 B、C 帳號 NAT Gateway 的 Elastic IP
- C. 在 B、C 帳號各自建立 IAM user 的 access key，讓服務以 SigV4 呼叫 A 帳號的 private API
- D. 由 B、C 帳號在各自 VPC 建立 `execute-api` interface endpoint，A 帳號在 API 的 resource policy 以 `aws:SourceVpce` 列出允許的 endpoint ID

> [!answer]- 答案：D
> **A ✗** Peering 需要額外的網路連線與 CIDR 不重疊的規劃，每增加一個帳號都要修改 A 帳號的網路；而且 private DNS 解析跨 peering 使用 endpoint 需要額外設定，營運負擔較高。
>
> **B ✗** Regional endpoint 是 public 的，流量經 NAT 與 Internet 進入，違反「留在私有網路」；Elastic IP 允許清單也容易隨架構變動而失效。
>
> **C ✗** SigV4 只處理身份驗證，不會讓 private API 可以從沒有 interface endpoint 的 VPC 連到；長期 access key 也不符合最佳實務。
>
> **D ✓** Private API 可以接受來自其他帳號 VPC 的 interface endpoint 流量。各業務帳號在自己的 VPC 建 endpoint，A 帳號只要在 resource policy 列出允許的 `aws:SourceVpce`，就能明確控制來源，新增帳號時只需加一個 endpoint ID。
>
> **考點**：SAP-1.4、SAP-2.3｜跨帳號 private API 與 resource policy

### 練習 20-15｜SAP｜單選｜舊系統 token 的授權效能

Wanderly 併購了一家旅行社，對方有數十萬名企業客戶，使用旅行社舊系統發出的不透明 session token（不是 JWT）。Wanderly 要讓這些客戶直接呼叫新的 REST API，驗證 token 必須呼叫舊系統的 introspection endpoint，而這個 endpoint 每秒只能承受約 300 次請求；API 尖峰為每秒 3,000 次，大多數客戶在一段時間內會連續呼叫多次。安全團隊可以接受 token 撤銷後最多 5 分鐘才失效。

最合適的設計是什麼？

- A. 改用 Cognito user pool authorizer，並把舊系統的 token 匯入 Cognito
- B. 使用 Lambda authorizer 呼叫 introspection endpoint，以 `Authorization` header 作為 identity source 並開啟 300 秒的授權結果快取，回傳涵蓋該客戶可用 method 的 policy
- C. 在每個後端 Lambda 函式中呼叫 introspection endpoint 驗證 token
- D. 改用 HTTP API 的 JWT authorizer，並把 introspection endpoint 設為 issuer

> [!answer]- 答案：B
> **A ✗** Cognito user pool authorizer 只接受 Cognito 自己簽發的 JWT，無法驗證舊系統的不透明 token，token 也無法「匯入」Cognito。
>
> **B ✓** Lambda authorizer 適合自訂驗證邏輯。開啟以 token 為 key 的結果快取後，同一個 token 在 300 秒內的重複請求不會再呼叫 introspection endpoint，把壓力降到它能承受的範圍；300 秒正好符合可接受的撤銷延遲。回傳涵蓋多個 method 的 policy，可避免快取後呼叫其他 method 被誤拒。
>
> **C ✗** 在每個後端函式驗證，每個請求都要打一次 introspection endpoint，尖峰每秒 3,000 次會遠超過它的承受能力；也讓驗證邏輯散落在各函式中。
>
> **D ✗** JWT authorizer 需要可驗證簽章的 JWT 與符合 OIDC 的 issuer（提供公開金鑰），不透明 token 無法以這種方式驗證。
>
> **考點**：SAP-2.3、SAP-2.5｜Lambda authorizer 與授權快取

### 練習 20-16｜SAP｜選兩項｜公開 API 的濫用防護

Wanderly 的公開 REST API（regional）近期遭到大量來自數千個 IP 的爬蟲請求，其中也夾雜 SQL injection 嘗試。這些請求不帶 API key，使得正常使用者的請求出現大量 429，後端 Lambda 也耗盡了帳號的 concurrency，連帶影響其他函式。團隊希望在入口阻擋惡意流量，並確保這個 API 無論如何都不會再拖垮同帳號的其他 Lambda 函式。

哪兩個做法最合適？（選兩項）

- A. 為每位匿名使用者發放 API key，並建立 usage plan
- B. 在 API 上啟用 CORS，只允許 Wanderly 網站的 origin
- C. 在 REST API 的 stage 關聯 AWS WAF web ACL，啟用 SQL injection 的 managed rule group 與依來源 IP 計數的 rate-based rule
- D. 把 API 的 stage throttling 調高到帳號上限，避免正常使用者收到 429
- E. 為這個 API 背後的 Lambda 函式設定 reserved concurrency，限制它最多可使用的 concurrency

> [!answer]- 答案：C、E
> **A ✗** 匿名使用者無法預先發放 API key；爬蟲本來就不帶 key，usage plan 對它們沒有作用，而且 API key 外流後也可以被濫用。
>
> **B ✗** CORS 只約束瀏覽器，爬蟲程式完全不受影響。
>
> **C ✓** WAF 可以直接關聯 REST API stage。Managed rule group 檢查請求內容擋下 SQL injection，rate-based rule 依來源 IP 計數，自動阻擋短時間內請求過多的 IP，在請求到達 throttling 與後端之前就處理掉惡意流量。
>
> **D ✗** 調高 throttling 會讓更多爬蟲請求進入後端，Lambda 與下游更容易被壓垮，也讓這個 API 占用更多帳號層級的額度。
>
> **E ✓** Reserved concurrency 為函式設定上限，即使流量暴增，它最多也只會使用這麼多 concurrency，帳號其餘額度保留給其他函式，避免故障擴散。
>
> **考點**：SAP-2.3、SAP-3.2｜WAF rate-based rule 與 reserved concurrency 的分層保護
