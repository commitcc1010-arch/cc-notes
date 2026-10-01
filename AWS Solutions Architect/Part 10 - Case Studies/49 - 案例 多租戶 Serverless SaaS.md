---
chapter: 49
title: 案例：多租戶 Serverless SaaS
part: 10
---

# 第 49 章　案例：多租戶 Serverless SaaS

> [!abstract] 本章地圖
> **你會學到**：
> - 用 silo、pool、bridge 三種模型描述多租戶架構，並依租戶等級、合規要求與成本選擇
> - 讓租戶隔離不再依賴「工程師記得加篩選條件」，而是用 IAM 動態 policy 與 ABAC 在 AWS 層強制
> - 設計以 Cognito 為核心的租戶身份、以 DynamoDB partition key 為核心的資料分區
> - 用 API Gateway usage plans、Lambda reserved concurrency 與佇列處理 noisy neighbor，並知道每個機制的極限
> - 在共用資源的 pool 模型中算出每個租戶的成本，並把 SaaS 從 SAA 等級演進到 SAP 等級的多帳號架構
>
> **前置知識**：第 12、13 章（IAM、STS、Cognito）、第 15 章（KMS）、第 19、20 章（Lambda、API Gateway）、第 27 章（DynamoDB）、第 32 章（SQS）、第 40 章（多帳號）
> **考試比重**：SAA ★★☆（Domain 1、2）｜SAP ★★★（Domain 1 安全控制、Domain 2 新解決方案設計）

## 49.1 故事：民宿 A 看到了民宿 B 的訂單

Wanderly 發現，平台上的上千家小型民宿都有同一個困擾：沒有錢買昂貴的旅館管理系統，只能用試算表記房況。於是 Wanderly 推出 **Wanderly Host**：一套月費制的訂房管理 SaaS（Software as a Service，軟體即服務），民宿可以管理房價日曆、接收訂單、在自己的網站嵌入訂房按鈕。每一家使用 Wanderly Host 的民宿，就是一個 **tenant（租戶）**。

第一版由三位工程師在兩個月內用 API Gateway、Lambda 和 DynamoDB 做完，所有租戶共用同一套資源。上線第三個月，花蓮一家民宿的老闆打電話給客服：他的後台「最近訂單」列表裡，出現了台東另一家民宿的客人姓名與電話。原因是某個新 API 在查詢時忘了加上租戶 ID 的篩選條件。這不只是 bug，而是個資外洩事件。

同一個月還發生兩件事。一家擁有 40 間分店的連鎖旅館「櫻花酒店」簽約了，但它的資安團隊要求：資料必須和其他租戶實體分開、用自己控制的加密金鑰、而且要能拿到自己的使用量報表。另外，有一家大型民宿聯盟一次匯入了三年份的歷史訂單，整個平台的 API 因此變慢了二十分鐘，其他一千多家民宿都受影響。

這三件事對應多租戶 SaaS 的三個核心問題：**隔離（isolation）**、**租戶分級（tiering）** 與 **noisy neighbor（吵鬧的鄰居）**。財務團隊還加了第四個：「每家租戶到底花了我們多少錢？基本方案的定價是不是賠本？」這一章依序回答這四個問題。

## 49.2 需求與限制

| 類別 | 需求 | 設計影響 |
|---|---|---|
| 租戶數 | 基本方案 2,000 家民宿、專業方案 200 家、企業方案 5 家（會成長） | 大部分租戶必須共用資源，否則成本與營運都撐不住 |
| 隔離 | 任何租戶都不能讀寫其他租戶的資料，即使程式有 bug | 隔離要在 AWS 層強制，不能只靠應用程式 |
| 企業方案 | 資料實體分離、客戶自己的 KMS key、獨立的使用量報表 | 企業租戶需要專屬資源，甚至專屬帳號 |
| 效能 | 一個租戶的大量操作不得影響其他租戶 | 每個租戶與每個等級要有用量上限 |
| 成本 | 能算出每個租戶的成本，驗證定價 | 共用資源要有可歸屬的用量數據 |
| 上線速度 | 新租戶從註冊到可以使用在 5 分鐘內，不需要人工 | Onboarding 完全自動化 |
| 團隊 | 8 位工程師，不想管伺服器 | 以 serverless 為主 |

在動手前先釐清兩個名詞。**Control plane（控制平面）** 是管理「租戶本身」的那一套系統：註冊、方案、計費、onboarding、租戶設定。**Application plane（應用平面）** 是租戶實際使用的功能：房價、訂單、日曆。兩者分開設計，因為 control plane 只有一套、通常是所有租戶共用；application plane 才需要依租戶等級決定共用或專屬。

## 49.3 三種多租戶模型：silo、pool、bridge

多租戶架構最根本的問題是：一個資源要給一個租戶專用，還是讓很多租戶共用？

- **Silo（筒倉）模型**：每個租戶有自己專屬的一套資源，可以是專屬的 DynamoDB table、專屬的 Lambda 函數，甚至專屬的 AWS 帳號。隔離最強，但成本與營運負擔隨租戶數線性成長。
- **Pool（池）模型**：所有租戶共用同一套資源，資料用租戶 ID 區分。成本效率最高，但隔離完全依賴設計，而且一個租戶的用量會影響所有人。
- **Bridge（橋接）模型**：同一個系統裡，某些層共用、某些層專屬；或某些等級的租戶用 pool、某些用 silo。這是大多數真實 SaaS 的樣子。

| 比較 | Silo | Pool | Bridge |
|---|---|---|---|
| 隔離強度 | 最強，資源邊界即租戶邊界 | 需要靠 IAM 與資料分區強制 | 依層與等級而定 |
| 每租戶成本 | 高，閒置資源也要付費（serverless 可降低） | 最低 | 中間 |
| Noisy neighbor | 天然避免 | 必須主動限制 | 大租戶放 silo 即可緩解 |
| 部署與維運 | 每次更新要部署到 N 套環境 | 一次部署 | 需要能處理兩種模式的工具 |
| 成本歸屬 | 直接用 tag 或帳號 | 需要用量計量 | 混合 |
| 適合 | 企業客戶、強合規需求 | 大量小型租戶 | 有多個方案等級的 SaaS |

Wanderly Host 的選擇是 bridge：基本與專業方案的租戶放在 pool；企業方案的租戶放在 silo。Control plane、API Gateway 與 Cognito 是所有租戶共用的；但即使在 pool 模型裡，**隔離也不是可選的**，下一節就要處理這個問題。

> [!warning] 常見誤解
> 「Silo 一定很貴。」在 serverless 架構下，一張沒有流量的 on-demand DynamoDB table 和一個沒有被呼叫的 Lambda 函數幾乎不產生費用，所以 serverless 讓 silo 的成本比 EC2 時代低很多。真正的成本是營運：每個 silo 都要部署、監控、升級。

## 49.4 SAA 等級解法：pool 模型的第一版

先看修正隔離問題之前的基本架構，它在 SAA 的範圍內就是一個標準的 serverless API（第 19、20 章）：

```text
民宿後台（瀏覽器）
   │ ① 登入
   ▼
[Cognito user pool] ── ② 回傳 JWT（含 custom:tenant_id、custom:tier）
   │
   │ ③ 呼叫 API，Authorization: Bearer <JWT>
   ▼
[API Gateway REST API]
   │ ④ Lambda authorizer 驗證 JWT，取出 tenant_id 與 tier
   │    依 tier 對應 usage plan（API key 來源：authorizer）
   ▼
[Lambda：bookings / rates / calendar]
   │ ⑤ 以 tenant_id 作為 partition key 存取
   ▼
[DynamoDB：Bookings table（pool）]      [S3：租戶上傳的房間照片，prefix = tenant_id/]
```

① ② 民宿員工在 Cognito 登入，取得 **JWT（JSON Web Token）**：一段經 Cognito 簽章、包含使用者屬性的字串。租戶 ID 存在 user pool 的自訂屬性 `custom:tenant_id`，方案等級存在 `custom:tier`。

③ ④ 每個 API 請求都帶著 JWT。Lambda authorizer 驗證簽章與有效期限，從中取出 tenant_id。**這是整個系統裡唯一可以信任的租戶身份來源**：任何來自 URL、query string 或 request body 的 tenant_id 都可能被竄改，絕對不能拿來決定要存取哪個租戶的資料。

⑤ 業務 Lambda 用 tenant_id 作為 DynamoDB 的 partition key 存取資料，S3 的照片也以 tenant_id 作為 prefix。

這個版本的弱點正是那次事故：tenant_id 的篩選是**應用程式碼的責任**。只要有一個工程師在一個查詢裡忘了，或某個 API 誤用了 request body 裡的 tenant_id，資料就會跨租戶外洩。Lambda 的執行角色對整張 Bookings table 有完整權限，IAM 層完全沒有擋。

## 49.5 讓 IAM 強制租戶隔離：動態 policy 與 ABAC

要讓「忘了加篩選條件」也不會外洩，就要讓 Lambda 在存取資料時使用的身份**本身就只能碰到一個租戶的資料**。做法是 **token vending machine（憑證販賣機）** 模式：Lambda 在每次請求中，根據已驗證的 tenant_id 向 STS 換一組只對該租戶有效的臨時憑證，再用這組憑證存取 DynamoDB 與 S3。

```text
[Lambda 執行角色]（只有 sts:AssumeRole 與 sts:TagSession 權限，碰不到資料）
   │ ① AssumeRole(TenantDataRole, Tags: TenantId=t-0042)
   ▼
[STS] ── ② 回傳臨時憑證，session 帶有 principal tag TenantId=t-0042
   │
[Lambda 用臨時憑證] ── ③ Query Bookings, pk = "t-0042"   → 允許
                     └─ ④ Query Bookings, pk = "t-0077"   → AccessDenied
```

① Lambda 的執行角色本身只能 assume 一個 `TenantDataRole`，並在 assume 時帶上 **session tag（工作階段標籤）** `TenantId=t-0042`。這個值來自 authorizer 驗證過的 JWT，不是來自使用者輸入。`TenantDataRole` 的 trust policy 必須允許 `sts:TagSession`，否則帶 tag 的 AssumeRole 會失敗（第 13 章）。

② 拿到的臨時憑證帶有 principal tag。`TenantDataRole` 的權限 policy 用這個 tag 限制可存取的資料：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TenantScopedDynamoDB",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-northeast-1:111122223333:table/Bookings",
        "arn:aws:dynamodb:ap-northeast-1:111122223333:table/Bookings/index/*"
      ],
      "Condition": {
        "ForAllValues:StringEquals": {
          "dynamodb:LeadingKeys": ["${aws:PrincipalTag/TenantId}"]
        }
      }
    },
    {
      "Sid": "TenantScopedS3",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::wanderly-host-media/${aws:PrincipalTag/TenantId}/*"
    }
  ]
}
```

`dynamodb:LeadingKeys` 是 DynamoDB 專用的 condition key，代表請求所存取 item 的 partition key 值。這條 policy 的意思是：「只能存取 partition key 等於你的 TenantId tag 的 item」。注意 policy 裡沒有 `dynamodb:Scan`：Scan 會讀整張表，請求中沒有指定任何 partition key 值，而 `ForAllValues` 遇到「沒有任何值」時會視為條件成立，等於完全不受限制，所以租戶範圍的角色絕對不能擁有它。

③ ④ 即使程式碼有 bug、查了別的租戶的 partition key，DynamoDB 也會回傳 AccessDenied。隔離從「靠人記得」變成「靠 IAM 保證」。

這就是 **ABAC（Attribute-Based Access Control，以屬性為基礎的存取控制）**：權限由身份的屬性（tag）和資源的屬性比對決定，而不是為每個租戶寫一個角色。2,000 個租戶共用同一個 `TenantDataRole` 與同一份 policy，新增租戶不需要修改任何 IAM 設定（第 12 章）。

另一種做法是**動態產生 session policy**：AssumeRole 時傳入一份即時產生、把租戶 ID 寫死在 Resource 或 Condition 中的 inline session policy。臨時憑證的有效權限是「角色 policy」與「session policy」的交集，所以 session policy 只能縮小權限、不能擴大。兩種做法效果相近；session tag 的好處是 policy 固定、可以預先審查，動態 policy 的好處是可以表達更複雜的條件。考試兩種說法都可能出現，關鍵字是「每個請求取得租戶範圍的臨時憑證」。

> [!tip] 考試提示
> 題目說「多租戶、共用 DynamoDB table、要防止程式錯誤造成跨租戶存取」，答案通常是 `dynamodb:LeadingKeys` 加上 session tag 或 session policy。只在應用程式加 `FilterExpression` 或「code review 加強檢查」的選項都不是 AWS 層的強制控制。

這個設計有一個要付出的代價：partition key 必須**正好等於**租戶 ID，才能用 `StringEquals` 比對。下一節會看到，這會影響大型租戶的資料分區方式。

## 49.6 租戶身份：Cognito 的設計細節

整個隔離機制的根是 JWT 裡的 tenant_id，所以 Cognito 的設定必須確保這個值不能被使用者竄改。

**自訂屬性設為唯讀。** Cognito user pool 的 app client 可以分別設定哪些屬性可讀、哪些可寫。`custom:tenant_id` 與 `custom:tier` 必須設為 app client **不可寫入**，只能由後端的 control plane 以管理員 API 設定。否則使用者可以呼叫 `UpdateUserAttributes` 把自己的 tenant_id 改成別人的，前面所有的 IAM 防護都會被繞過。另外，自訂屬性建立後不能刪除或改名，命名時要想清楚。

**共用 user pool 或每租戶一個 user pool？**

| 做法 | 優點 | 缺點 | 適合 |
|---|---|---|---|
| 所有租戶共用一個 user pool，以自訂屬性與 group 區分 | 管理簡單，一套登入頁面 | 所有租戶共用密碼政策與 MFA 設定；同一個 email 難以屬於兩個租戶 | 基本與專業方案 |
| 每個企業租戶一個 user pool | 可以各自設定密碼政策、MFA，並串接該企業自己的 SAML／OIDC IdP | 要依租戶決定使用哪個 user pool；user pool 數量有 quota | 企業方案 |

櫻花酒店要求員工用公司的 Microsoft Entra ID 登入。Wanderly 為它建立專屬 user pool，設定 SAML identity provider 聯合登入（第 13 章）；登入頁面依網域（例如 `sakura.host.wanderly.com`）決定導向哪個 user pool。Authorizer 也必須知道每個 user pool 的簽章金鑰，才能驗證來自不同 pool 的 JWT。

**角色與權限。** 同一個租戶內還有「老闆」和「櫃台」的差別，這是租戶內的授權，用 Cognito group 表示並寫在 JWT 中，由應用程式判斷。要注意分清楚兩層：**租戶之間的隔離由 IAM 強制；租戶內的角色權限由應用程式判斷**。

如果需要在 token 中加入不在 user pool 屬性裡的資訊（例如從 control plane 查到的方案到期日），可以使用 Cognito 的 **pre token generation Lambda trigger**，在發出 token 前修改 claims。

## 49.7 資料分區：DynamoDB 的 key 設計

Pool 模型的 Bookings table 設計如下：

| 屬性 | 範例 | 說明 |
|---|---|---|
| `pk`（partition key） | `t-0042` | 租戶 ID，與 IAM `LeadingKeys` 比對 |
| `sk`（sort key） | `BOOKING#2026-10-01#B-88123` | 實體類型 + 日期 + ID，支援依日期範圍查詢 |
| GSI1 pk／sk | `t-0042`／`GUEST#0912xxxxxx#B-88123` | 依客人查詢；GSI 的 partition key 同樣是租戶 ID |

這個設計讓「某租戶某段日期的訂單」成為一次 Query，而且每個請求天生就帶著租戶範圍。GSI 的 partition key 也刻意設成租戶 ID，查詢客人時用 sort key 的 `begins_with("GUEST#0912xxxxxx")`。這樣不論查詢的是 table 還是 index，請求中的 partition key 值都等於租戶 ID，`LeadingKeys` 條件都能套用；前面的 policy 也因此把 index ARN（`table/Bookings/index/*`）一起列入 Resource。若 GSI 的 partition key 是「租戶 ID + 其他值」的組合字串，精確比對就會失效，這類設計要特別小心，並用負向測試驗證。

**大租戶的熱分割問題。** 第 27 章提過，DynamoDB 單一 partition key 的吞吐有上限（每秒約 3,000 RCU、1,000 WCU）。一家小民宿永遠碰不到；但民宿聯盟一次匯入三年份訂單時，所有寫入都打在同一個 partition key `t-0900` 上，就會被 throttle。常見的解法是把 partition key 改成 `t-0900#3` 這種加上分片號碼的形式，但這樣就破壞了 `LeadingKeys` 的精確比對。

Wanderly 的取捨是：**大到需要分片的租戶，就是該搬到 silo 的租戶**。企業方案的租戶有自己的 table，可以自由設計分片；pool 裡的租戶都夠小，partition key 等於租戶 ID 就足夠。這也是 bridge 模型的一個實際好處：不需要為少數大租戶犧牲多數小租戶的簡單隔離設計。

Pool table 使用 on-demand capacity mode，因為上千個小租戶加總起來的流量難以預測，on-demand 不需要規劃容量（第 27 章）。

## 49.8 Noisy neighbor：每個租戶都要有上限

民宿聯盟的大量匯入讓整個平台變慢，是因為在 pool 模型裡，所有租戶共用同一組上限：API Gateway 的帳號層級 throttling、Lambda 的帳號併發數（預設每個 Region 1,000，可申請提高）、DynamoDB table 的吞吐。一個租戶用掉了，其他人就沒有了。對策是在每一層為每個租戶或每個等級設定上限：

**API 層：usage plan。** API Gateway REST API 的 **usage plan** 可以為每個 API key 設定 throttling（每秒請求數與 burst）與 quota（每天或每月的請求總數）。Wanderly 為三個方案各建立一個 usage plan：基本方案每秒 20 個請求、專業方案每秒 100 個；每個租戶有自己的 API key，關聯到對應方案的 usage plan。因為使用者是用 JWT 而不是 API key 呼叫 API，所以把 API key 來源設為 **AUTHORIZER**：Lambda authorizer 驗證 JWT 後，在回應中帶回這個租戶對應的 API key，API Gateway 就依它計算用量。

> [!warning] 常見誤解
> 兩個關於 usage plan 的重點：第一，usage plan 與 API key 是 **REST API** 的功能，HTTP API 沒有；第二，AWS 明確說明 usage plan 的 throttling 與 quota 是**盡力而為（best effort）**，不保證精確，而且 **API key 不是授權機制**，不能拿來決定誰可以存取哪些資料。它適合做方案分級與保護後端，不適合做計費依據或安全控制。

**運算層：reserved concurrency。** Lambda 的 **reserved concurrency** 同時做兩件事：保證這個函數至少能用到這麼多併發，也限制它最多只能用這麼多。Wanderly 把「大量匯入」從即時 API 拆出來，成為獨立的 import 函數，設定 reserved concurrency 為 50。不論多少租戶同時匯入，它最多只會用掉 50 個併發，即時的 bookings API 永遠有剩下的容量可用（第 19 章）。

**非同步層：佇列。** 匯入請求先進 SQS，由 import 函數依上限慢慢處理（SQS 的基本行為見第 32 章）。若擔心一個大租戶的大量訊息排在前面，讓其他租戶的匯入要等很久，可以依等級拆成不同的 queue，或使用 SQS 在 2025 年推出的 **fair queues（公平佇列）**：producer 在送進 standard queue 的訊息上設定 `MessageGroupId` 作為租戶識別，SQS 發現某個租戶處理中的訊息數明顯偏多時，會優先把其他租戶的訊息交給 consumer，讓安靜的租戶不必排在吵鬧租戶的積壓後面。它不需要修改 consumer 程式，也不像 FIFO queue 那樣有吞吐上限或保證順序；standard queue 上的 `MessageGroupId` 只用來識別租戶。

**帳號層：silo 的真正價值。** Lambda 併發、API Gateway throttling 等 quota 都是**以帳號與 Region 為單位**計算的。企業租戶放在自己的 AWS 帳號裡，就有自己的一整套 quota，pool 裡的任何流量都碰不到它。這是第 40 章「帳號是最強的隔離邊界」在 SaaS 中的應用。

## 49.9 演進到 SAP 等級：bridge 模型與帳號級 silo

第一年結束時，Wanderly Host 有 2,500 個 pool 租戶和 12 個企業租戶。系統要演進的是四件事：企業租戶的帳號級隔離、全自動 onboarding、跨租戶的安全部署，以及租戶的金鑰與資料生命週期。

**1. 企業租戶一個帳號。** 每個企業租戶在 Organizations 的 `SaaS-Silo` OU 下擁有一個專屬帳號，由 Control Tower 的 Account Factory 建立，套用和其他 workload 帳號相同的 SCP 與 baseline（第 14、40 章）。帳號內部署的是和 pool 完全相同的程式碼，只是設定指向專屬的 DynamoDB table 與 KMS key。共用的 API Gateway 依 JWT 中的 tier 與 tenant_id 把請求路由到 pool 的 Lambda，或透過專屬帳號的 API 轉送到 silo 環境。

**2. 自動化 onboarding。** 註冊流程由 control plane 中的 Step Functions 編排（第 33 章）：

1. 在 control plane 的 Tenants table 建立租戶紀錄，狀態 `PROVISIONING`。
2. 在 Cognito 建立管理員使用者，設定唯讀的 `custom:tenant_id`。
3. 建立 API key 並關聯到對應方案的 usage plan。
4. 企業方案額外執行：透過 Account Factory 建立帳號、以 CloudFormation StackSets 部署 silo 資源、建立專屬 KMS key。
5. 寫入預設資料（房型範本），把狀態改為 `ACTIVE`，寄送歡迎信。

每一步都必須是**冪等**的：Step Functions 的某一步失敗重試時，「建立使用者」若使用者已存在就視為成功，而不是報錯或建立第二個。這讓整個 onboarding 可以從任何失敗點安全地重跑，達成「5 分鐘內、不需人工」的需求。

**3. 跨租戶的部署。** 在 pool 模型中，一次部署就影響所有租戶；在 silo 模型中，一個版本要部署到幾十個帳號。Wanderly 的 pipeline 依「波次（wave）」推出：先部署到內部測試租戶，再到 pool（用 Lambda alias 的加權流量做 canary，第 37 章），觀察錯誤率無異常後，才以 StackSets 分批推到 silo 帳號。所有租戶跑同一個版本，是 SaaS 營運效率的關鍵；如果每個企業客戶都有自己的客製版本，就退化成了「代管軟體」。

**4. 金鑰與資料生命週期。** 企業租戶使用專屬的 customer managed KMS key，key policy 讓租戶的資安團隊可以檢視金鑰使用紀錄（CloudTrail），並在合約約定下停用金鑰。Pool 租戶共用一把 KMS key，但每次加密都帶上 **encryption context** `tenantId=t-0042`：encryption context 會被記錄在 CloudTrail 中，讓稽核可以追蹤每次解密屬於哪個租戶，key policy 也能用 `kms:EncryptionContext:tenantId` 條件加以限制（第 15 章）。租戶解約時，pool 租戶的資料以 partition key 刪除、S3 prefix 以 lifecycle 規則清除；silo 租戶則可以排程刪除 KMS key，讓殘留的備份也無法解密（crypto-shredding）。

**5. Pool 到 silo 的升級遷移。** 民宿聯盟升級到企業方案時，資料要從 pool table 搬到新的 silo table。做法是：建立 silo 環境、以 DynamoDB export to S3 或依 partition key 查詢的批次工作複製歷史資料、短暫把該租戶設為唯讀、同步最後的增量、把 control plane 中的路由切到 silo、驗證後再刪除 pool 中的舊資料。整個過程中，**路由由 control plane 的租戶紀錄決定**，所以切換只需要改一筆資料，不用改程式。

## 49.10 完整架構圖

```text
                         民宿員工／訂房網站訪客
                                  │
                [CloudFront + WAF] ── 前端靜態檔（S3）
                                  │
        ┌──────────── SaaS 共用帳號（ap-northeast-1）────────────┐
        │ [Cognito：共用 pool + 企業專屬 pools（SAML 聯合）]      │
        │                  │ JWT（tenant_id、tier）               │
        │ [API Gateway REST] ─ Lambda authorizer ─ usage plans    │
        │        │ 依 control plane 的路由表                      │
        │        ├───────────────► pool 應用平面                  │
        │        │   Lambda（bookings/rates）→ STS（session tag） │
        │        │      → DynamoDB pool table（LeadingKeys 限制） │
        │        │      → S3（tenant prefix）                     │
        │        │   SQS import queue → import Lambda（reserved） │
        │        │                                                │
        │ Control plane：Tenants table、Step Functions onboarding │
        │   計量：EMF 指標、消耗容量紀錄 → S3 → Athena 成本報表    │
        └────────┼────────────────────────────────────────────────┘
                 │ 企業租戶
                 ▼
        ┌──── 企業租戶專屬帳號（每家一個，SaaS-Silo OU）────┐
        │ API → Lambda → 專屬 DynamoDB table（客製分區）    │
        │ 專屬 KMS key、帳號層級 quota、Cost Explorer 直接歸屬│
        └──────────────────────────────────────────────────┘
```

沿兩條路徑讀這張圖。**Pool 租戶的請求**：JWT 經 authorizer 驗證，usage plan 依方案限流，Lambda 用 session tag 換到只對該租戶有效的憑證，再存取 DynamoDB 與 S3；即使程式錯誤，IAM 也會擋下跨租戶存取。**企業租戶的請求**：同樣在共用的入口驗證身份，但依 control plane 的路由表轉到專屬帳號，資料、金鑰、quota 與帳單都和其他租戶分開。

共用帳號下方的計量路徑是下一節成本分析的基礎。

## 49.11 設計決策紀錄：為何選 A 不選 B

| 決策 | 選擇 A | 不選 B | 理由 |
|---|---|---|---|
| 租戶模型 | Bridge（小租戶 pool、企業 silo） | 全部 silo | 2,000 個以上的 silo 環境部署、監控、升級的營運負擔無法承受 |
| 租戶模型 | Bridge | 全部 pool | 企業客戶要求實體分離與專屬金鑰；大租戶需要自己的 quota 與分區設計 |
| 隔離手段 | Session tag + `LeadingKeys`（ABAC） | 應用程式加 `FilterExpression` | Filter 是讀出來之後才過濾，而且依賴每個工程師都記得；IAM 在 AWS 層強制 |
| 隔離手段 | 一個 `TenantDataRole` 搭配 tag | 每個租戶一個 IAM role | IAM role 數量有 quota，數千個角色難以管理；ABAC 新增租戶不需要修改 IAM |
| 租戶身份來源 | 驗證過的 JWT 中的唯讀屬性 | Request 中的 header 或 body | 使用者可以任意修改 request 內容 |
| API 類型 | REST API | HTTP API | 需要 usage plan 與 API key 做方案分級，這是 REST API 的功能 |
| 企業 silo 邊界 | 專屬 AWS 帳號 | 共用帳號內的專屬 table | 帳號提供獨立 quota、帳單與爆炸半徑；企業客戶的合規審查也較容易通過 |
| 大量匯入 | SQS + reserved concurrency 的獨立函數 | 在即時 API 中同步處理 | 批次工作與即時請求共用併發，會拖慢所有租戶 |
| 成本歸屬（pool） | 依請求計量的用量資料 | 依租戶數平均分攤 | 平均分攤會掩蓋少數重度租戶造成的虧損 |

## 49.12 故障演練

| 情境 | 預期行為 | 要確認的事 |
|---|---|---|
| 新 API 的查詢誤用了別的租戶 ID | DynamoDB 回傳 AccessDenied，請求失敗並產生告警 | 整合測試中包含「租戶 A 的 token 嘗試讀租戶 B」的負向測試，每次部署都執行 |
| 使用者嘗試修改自己的 `custom:tenant_id` | Cognito 拒絕，因為 app client 對該屬性沒有寫入權限 | 定期以 Config 或自動化腳本檢查 app client 的屬性權限設定 |
| 某租戶短時間大量呼叫 API | 超過 usage plan 上限的請求收到 429，其他租戶不受影響 | 用戶端有退避重試；告警通知客服與租戶 |
| 大量匯入塞滿 import queue | Import 函數維持 reserved concurrency 上限，即時 API 不受影響 | 監控 queue 的最舊訊息年齡，提供租戶預估完成時間 |
| Onboarding 在第 4 步失敗 | Step Functions 依 retry 設定重試，失敗則進入人工處理狀態 | 每一步都冪等，重跑不會建立重複的帳號或使用者 |
| 有缺陷的版本部署到 pool | Canary 階段錯誤率上升，CodeDeploy 自動把 Lambda alias 切回舊版 | Silo 帳號的部署在 pool 驗證通過前不會開始 |
| 一個企業租戶的 silo 帳號誤設 SCP | 只有該租戶受影響 | 爆炸半徑正好就是一個租戶，這是帳號級 silo 的設計目的 |

第一列是最重要的：**隔離必須被測試**。如果沒有一個自動化測試持續證明「跨租戶存取會失敗」，某次重構把 Lambda 改回使用執行角色直接存取 DynamoDB，就會悄悄回到事故前的狀態。

## 49.13 成本思路：每個租戶花多少錢

財務的問題「每個租戶花多少錢」在 silo 和 pool 中有完全不同的答案。

**Silo 租戶**最簡單：專屬帳號的費用就是這個租戶的費用，在 Cost Explorer 中依帳號篩選即可。若 silo 是在共用帳號中的專屬資源，則為資源加上 `TenantId` tag，並在 Billing console 啟用為 **cost allocation tag**，之後的帳單資料就能依租戶分組（使用者自訂的 tag 必須先啟用，且只對啟用之後的費用生效，第 39 章）。

**Pool 租戶**的費用混在同一張 DynamoDB table、同一組 Lambda 函數裡，AWS 帳單無法拆分。做法是自己**計量（metering）**：

1. Lambda 每次處理請求時，以 CloudWatch **Embedded Metric Format（EMF）** 寫出一筆結構化日誌，包含 tenant_id、執行時間、記憶體設定。
2. 對 DynamoDB 的每次讀寫加上 `ReturnConsumedCapacity` 參數，把實際消耗的 RCU／WCU 和 tenant_id 一起記錄下來。
3. 這些紀錄匯入 S3，以 Athena 每天彙總每個租戶的用量占比。
4. 把當月 pool 資源的實際帳單（來自 Cost and Usage Report／Data Exports）依用量占比分攤到每個租戶。

結果很有啟發性：80% 的基本方案租戶每月成本不到月費的一成，但有 30 家重度使用的基本方案租戶成本超過月費。Wanderly 據此調整方案：基本方案加上每月訂單數上限，超過的租戶建議升級。**沒有租戶層級的成本資料，定價就只能靠猜。**

其他成本槓桿：

- Lambda 改用 Graviton（arm64）架構，通常有更好的價格效能比；用 Compute Savings Plans 涵蓋穩定的 Lambda 用量。
- Pool table 流量穩定後，可評估從 on-demand 改為 provisioned 加 auto scaling；企業 silo 的小 table 維持 on-demand，避免為閒置容量付費。
- CloudWatch Logs 是 serverless 帳單中常被忽略的大項：為日誌群組設定保存期限，把除錯等級的日誌只在需要時開啟。
- 每個 silo 帳號都有固定的基礎成本（例如 Config、CloudTrail 資料事件、GuardDuty 等 baseline 服務），定價時企業方案要涵蓋這部分。

## 49.14 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 多租戶共用 DynamoDB table、防止跨租戶存取 | `dynamodb:LeadingKeys` + session tag（ABAC）或 session policy |
| 每個請求依租戶取得最小權限憑證 | STS AssumeRole（token vending machine）；trust policy 允許 `sts:TagSession` |
| 多租戶共用 S3 bucket | Resource 使用 `${aws:PrincipalTag/TenantId}/*` 限制 prefix |
| 租戶 ID 從哪裡來 | 驗證過的 JWT；Cognito 自訂屬性設為 app client 不可寫 |
| 不同方案有不同的 API 請求上限 | API Gateway REST API usage plan + API key（best effort） |
| 一個租戶的批次工作拖慢所有人 | 拆出獨立函數 + reserved concurrency；SQS 緩衝 |
| 企業客戶要求資料實體分離、專屬金鑰 | Silo（專屬 table 或專屬帳號）+ customer managed KMS key |
| 大量小租戶、成本敏感 | Pool 模型 |
| 部分 pool、部分 silo | Bridge 模型 |
| 每個租戶的成本（pool） | 依請求計量：EMF、ReturnConsumedCapacity、Athena 彙總 |
| 每個租戶的成本（silo） | 帳號或 cost allocation tag |
| 租戶 onboarding 自動化、可重跑 | Step Functions + 冪等步驟 |
| 企業租戶用自己的 IdP 登入 | 專屬 Cognito user pool + SAML／OIDC 聯合 |

**常見陷阱**：

1. 把 API key 當作授權機制：API key 只用於 usage plan 識別與計量，授權要靠 authorizer 與 IAM。
2. 以為 HTTP API 也有 usage plan：只有 REST API 有。
3. 用 `FilterExpression` 或 Scan 加條件實現租戶隔離：Filter 在讀取之後才套用，也不是 IAM 層的強制。
4. 為每個租戶建立一個 IAM role：數千個租戶會撞到 IAM quota，也難以管理；應該用 ABAC。
5. 讓租戶 ID 來自 request 參數：使用者可以竄改，必須來自驗證過的 token。
6. 以為 reserved concurrency 只是「保證」：它同時也是上限，設太低會讓該函數自己被 throttle。

## 本章重點整理

- 多租戶 SaaS 的四個核心問題是租戶隔離、租戶分級、noisy neighbor 與每租戶成本。
- Silo 隔離最強但營運成本高，pool 成本最低但隔離與限流都要主動設計，bridge 依等級或依層混合兩者，是最常見的實務選擇。
- Control plane 管理租戶本身（註冊、方案、onboarding、路由），application plane 提供租戶使用的功能。
- 租戶身份只能來自驗證過的 JWT；Cognito 的 `custom:tenant_id` 必須設為 app client 不可寫入。
- 用 token vending machine 模式，在每個請求中以 session tag 或 session policy 換取租戶範圍的臨時憑證，讓 IAM 強制隔離。
- `dynamodb:LeadingKeys` 限制可存取的 partition key 值；租戶範圍的角色不應擁有 Scan 權限。
- ABAC 讓所有租戶共用一個角色與一份 policy，新增租戶不需要修改 IAM。
- Partition key 等於租戶 ID 時隔離最簡單；需要分片的大租戶適合搬到 silo。
- API Gateway usage plan 只適用 REST API，throttling 與 quota 是 best effort，API key 不是授權機制。
- Lambda reserved concurrency 同時是保證與上限；把批次工作拆出並限制併發，可以保護即時 API。
- Quota 以帳號與 Region 計算，帳號級 silo 讓企業租戶擁有獨立的 quota、帳單與爆炸半徑。
- Onboarding 用 Step Functions 編排冪等的步驟，讓流程可以從任何失敗點重跑。
- Pool 租戶的成本要靠自行計量（EMF、ReturnConsumedCapacity）再依占比分攤；silo 租戶用帳號或 cost allocation tag。
- 隔離必須有自動化的負向測試持續證明跨租戶存取會失敗。

## 本章練習題

### 練習 49-1｜SAA｜單選｜共用 DynamoDB table 的租戶隔離

一家 SaaS 公司讓所有租戶共用一張 DynamoDB table，partition key 是租戶 ID。Lambda 函數的執行角色對整張 table 有完整的讀寫權限，租戶篩選由程式碼負責。最近一次程式錯誤讓某個租戶讀到了其他租戶的資料。公司要求即使程式有錯誤，AWS 層也必須阻止跨租戶存取，並希望新增租戶時不必修改 IAM 設定。

最合適的做法是什麼？

- A. 在所有查詢中加上 `FilterExpression`，只回傳屬於目前租戶的 item
- B. 為每個租戶建立一個 IAM role，role policy 中寫死該租戶的 partition key
- C. 為 table 啟用以租戶為單位的 KMS key，讓不同租戶的資料使用不同金鑰加密
- D. Lambda 依驗證過的租戶 ID 以 session tag assume 一個共用角色，角色 policy 用 `dynamodb:LeadingKeys` 限制 partition key 必須等於 `${aws:PrincipalTag/TenantId}`

> [!answer]- 答案：D
> **A ✗** `FilterExpression` 在讀出資料之後才過濾，仍然依賴每段程式都正確撰寫，不是 AWS 層的強制控制。
>
> **B ✗** 每個租戶一個角色可以達到隔離，但新增租戶都要建立角色，數千個租戶會撞到 IAM 的 quota，違反「不必修改 IAM」的需求。
>
> **C ✗** DynamoDB table 的加密是 table 層級的設定，無法依 item 使用不同金鑰；而且 Lambda 若有解密權限，加密也擋不住程式錯誤造成的跨租戶讀取。
>
> **D ✓** Session tag 讓臨時憑證帶有租戶屬性，`LeadingKeys` 條件讓 DynamoDB 拒絕任何其他 partition key 的存取。所有租戶共用一份 policy，是 ABAC 的典型做法。
>
> **考點**：SAA-1.1、SAA-1.3｜ABAC 與 dynamodb:LeadingKeys

### 練習 49-2｜SAA｜單選｜租戶身份的可信來源

一個多租戶 API 使用 Cognito user pool 驗證使用者，並在 user pool 中以自訂屬性 `custom:tenant_id` 儲存租戶 ID。安全審查發現，前端在呼叫 API 時會在 request body 中帶上 `tenantId` 欄位，後端直接使用它來決定存取哪個租戶的資料。

應如何修正？

- A. 後端只從經 authorizer 驗證過的 JWT 中取得 tenant_id，並把 `custom:tenant_id` 設為 app client 不可寫入
- B. 在 request body 的 `tenantId` 欄位加上 HMAC 簽章，後端驗證簽章後再使用
- C. 在 API Gateway 啟用 API key，要求每個請求同時帶上 API key 與 tenantId
- D. 把 `tenantId` 從 request body 移到 HTTP header 中傳送

> [!answer]- 答案：A
> **A ✓** JWT 由 Cognito 簽章，驗證後內容可信；把自訂屬性設為 app client 不可寫，使用者就無法透過 UpdateUserAttributes 自行修改租戶 ID。這兩點一起才能確保租戶身份不可偽造。
>
> **B ✗** 簽章金鑰若放在前端就會外洩，若放在後端則等於重新發明一次 JWT；Cognito 已經提供可信的簽章 token，不需要另外設計。
>
> **C ✗** API key 是用於 usage plan 識別與計量的，不是授權機制；使用者仍然可以在請求中填入別人的 tenantId。
>
> **D ✗** Header 和 body 一樣由用戶端控制，可以任意修改，換位置沒有改變可信度。
>
> **考點**：SAA-1.1、SAA-1.2｜JWT 與 Cognito 自訂屬性權限

### 練習 49-3｜SAA｜單選｜依方案限制 API 請求量

一家 SaaS 公司提供基本與專業兩種方案，希望基本方案的租戶每秒最多 20 個 API 請求、每月最多 50 萬次，專業方案則更高。API 目前以 API Gateway HTTP API 實作，並使用 JWT authorizer。

最合適的做法是什麼？

- A. 在 HTTP API 上為每個方案建立 usage plan，依 JWT 中的方案等級套用
- B. 改用 REST API，為每個方案建立 usage plan，為每個租戶建立 API key 並關聯到對應方案
- C. 為每個租戶建立一個獨立的 Lambda 函數，並以 reserved concurrency 限制每秒請求數
- D. 在 WAF 為每個租戶建立 rate-based rule，以租戶的來源 IP 作為限制依據

> [!answer]- 答案：B
> **A ✗** Usage plan 與 API key 是 REST API 的功能，HTTP API 沒有 usage plan。
>
> **B ✓** REST API 的 usage plan 可以同時設定 throttling（每秒請求與 burst）與 quota（每月總量），租戶的 API key 關聯到對應方案即可。注意 usage plan 是 best effort，適合做方案分級，不適合做精確計費。
>
> **C ✗** Reserved concurrency 限制的是同時執行數，不是每秒請求數，也無法設定每月總量；每個租戶一個函數在上千個租戶時難以管理。
>
> **D ✗** 同一個租戶的員工可能來自不同 IP，不同租戶也可能共用同一個 NAT IP；以 IP 作為租戶識別不可靠，也無法設定每月 quota。
>
> **考點**：SAA-2.1、SAA-1.2｜API Gateway usage plan 與 API 類型

### 練習 49-4｜SAA｜單選｜批次工作造成的 noisy neighbor

一個多租戶 serverless 平台的即時 API 與「歷史訂單匯入」功能使用同一個 Lambda 函數。某個大租戶一次匯入大量資料時，函數的併發數用光了帳號的 Lambda 併發上限，其他租戶的即時 API 請求開始被 throttle。

哪個做法最能保護即時 API？

- A. 申請提高帳號的 Lambda 併發 quota，讓匯入與 API 都有足夠的併發
- B. 為現有函數設定 provisioned concurrency，讓它的冷啟動時間縮短
- C. 把匯入拆成獨立的 Lambda 函數，由 SQS 觸發，並為它設定 reserved concurrency 作為上限
- D. 把匯入函數的記憶體從 512 MB 提高到 4,096 MB，讓每次執行更快完成

> [!answer]- 答案：C
> **A ✗** 提高 quota 只是延後問題：下次更大的匯入或多個租戶同時匯入時，仍然會用光共用的併發。
>
> **B ✗** Provisioned concurrency 處理的是冷啟動延遲，不會限制匯入工作占用的併發數。
>
> **C ✓** 把批次工作拆出來，用 SQS 緩衝並以 reserved concurrency 設定上限，匯入工作最多只能用到固定的併發數，剩下的容量永遠留給即時 API。
>
> **D ✗** 提高記憶體會讓單次執行變快，但匯入的總併發仍然沒有上限，同時增加成本。
>
> **考點**：SAA-3.2、SAA-2.1｜reserved concurrency 與工作隔離

### 練習 49-5｜SAA｜單選｜共用 S3 bucket 的租戶範圍

一個 SaaS 應用程式讓所有租戶把房間照片存在同一個 S3 bucket，每個租戶使用自己的 prefix（例如 `t-0042/`）。Lambda 在處理請求時已經透過 STS 取得帶有 session tag `TenantId` 的臨時憑證。團隊希望用一份 policy 讓每個租戶只能讀寫自己的 prefix。

哪個 policy 設計最合適？

- A. Bucket policy 中對每個租戶各寫一條 statement，列出租戶的 IAM role ARN 與 prefix
- B. 角色 policy 允許 `s3:GetObject` 與 `s3:PutObject`，Resource 為 `arn:aws:s3:::bucket-name/${aws:PrincipalTag/TenantId}/*`
- C. 為每個租戶建立一個 S3 Access Point，並把 Access Point 的名稱寫在程式碼的設定檔中
- D. 啟用 S3 Object Lock，防止租戶修改其他租戶的物件

> [!answer]- 答案：B
> **A ✗** 每個租戶一條 statement，bucket policy 很快會超過大小上限，也要在每次新增租戶時修改。
>
> **B ✓** Policy variable 在評估時會被替換成 session 的 TenantId tag 值，一份 policy 就能讓每個租戶只存取自己的 prefix，新增租戶不需要修改任何設定。
>
> **C ✗** Access Point 可以為不同用途建立不同的存取政策，但每個租戶一個 Access Point 在數千租戶時管理成本高，且仍需要另外確保程式選對 Access Point。
>
> **D ✗** Object Lock 防止物件在保留期間被刪除或覆寫，不是存取控制，無法阻止跨租戶讀取。
>
> **考點**：SAA-1.1、SAA-1.3｜IAM policy variable 與 S3 prefix 隔離

### 練習 49-6｜SAA｜選兩項｜Pool 租戶的成本歸屬

一家 SaaS 公司的 2,000 個基本方案租戶共用同一組 Lambda 函數與一張 DynamoDB table。財務團隊想知道每個租戶的實際成本，以驗證定價。目前每月帳單只能看到這些共用資源的總額。

哪兩個做法能提供可靠的每租戶成本資料？（選兩項）

- A. Lambda 處理每個請求時，以 CloudWatch Embedded Metric Format 記錄租戶 ID 與執行時間
- B. 為共用的 DynamoDB table 加上 `TenantId` cost allocation tag
- C. 對 DynamoDB 的讀寫請求加上 `ReturnConsumedCapacity`，把消耗的容量與租戶 ID 一起記錄，再依用量占比分攤帳單
- D. 把共用資源的月費依租戶數平均分攤
- E. 為每個租戶建立一個 AWS Budgets 預算

> [!answer]- 答案：A、C
> **A ✓** EMF 讓 Lambda 以結構化日誌寫出含租戶 ID 的指標，可以彙總每個租戶的運算用量，作為分攤 Lambda 費用的依據。
>
> **B ✗** 同一個 tag key 在一個資源上只能有一個值，共用 table 無法同時標記為 2,000 個租戶；cost allocation tag 適合 silo 資源。
>
> **C ✓** `ReturnConsumedCapacity` 會在回應中提供實際消耗的 RCU／WCU，與租戶 ID 一起記錄後，就能依用量占比分攤 DynamoDB 的費用。
>
> **D ✗** 平均分攤會掩蓋少數重度租戶造成的成本，正是無法驗證定價的原因。
>
> **E ✗** Budgets 依據帳單資料的維度追蹤，帳單資料本身無法拆分到 pool 中的租戶，所以無法提供每租戶的成本。
>
> **考點**：SAA-4.2、SAA-4.3｜pool 模型的用量計量與成本分攤

### 練習 49-7｜SAA｜單選｜大租戶的熱分割

一個多租戶系統的 DynamoDB pool table 以租戶 ID 作為 partition key，並以 IAM 的 `dynamodb:LeadingKeys` 條件強制租戶隔離。某個大租戶的寫入量越來越大，經常收到 throttling 錯誤，其他小租戶則完全正常。團隊不希望犧牲現有的隔離設計。

最合適的做法是什麼？

- A. 把該租戶搬到專屬的 DynamoDB table（silo），並在該 table 中依需要設計分片的 partition key
- B. 把整張 pool table 的 partition key 改成「租戶 ID + 隨機分片號碼」
- C. 把 pool table 改成 provisioned 模式，並把 WCU 提高十倍
- D. 在 pool table 前面加上 DAX 叢集，吸收該租戶的寫入

> [!answer]- 答案：A
> **A ✓** 熱分割的原因是單一 partition key 的吞吐上限。大租戶搬到 silo 後，可以自由使用分片的 key 設計，而 pool 中小租戶的「partition key 等於租戶 ID」隔離設計不受影響。
>
> **B ✗** 加上分片號碼後，partition key 不再等於租戶 ID，`LeadingKeys` 的精確比對就無法使用，等於犧牲了隔離設計。
>
> **C ✗** 單一 partition key 的吞吐上限與 table 總容量無關，提高整張表的 WCU 無法解決單一 key 的熱點，反而增加成本。
>
> **D ✗** DAX 是讀取快取，寫入仍然會直接寫到 DynamoDB，無法解決寫入的熱分割。
>
> **考點**：SAA-3.3｜DynamoDB 熱分割與 bridge 模型

### 練習 49-8｜SAP｜單選｜企業租戶的隔離邊界

一家 SaaS 公司的企業客戶要求：資料與其他租戶實體分離、使用客戶可以稽核的專屬加密金鑰、不受其他租戶流量影響（包括 Lambda 併發與 API throttling 等帳號層級上限），並能拿到獨立的費用報表。公司已經使用 AWS Organizations 與 Control Tower。

最合適的設計是什麼？

- A. 在共用帳號中為企業客戶建立專屬 DynamoDB table 與專屬 Lambda 函數，並加上 cost allocation tag
- B. 在 pool table 中為企業客戶加上 KMS encryption context，並設定較高的 usage plan
- C. 透過 Account Factory 為每個企業客戶建立專屬帳號，部署與 pool 相同的程式碼、專屬 table 與 customer managed KMS key
- D. 為企業客戶在另一個 Region 建立專屬環境，與 pool 租戶分開

> [!answer]- 答案：C
> **A ✗** 專屬 table 與函數提供了資料分離與成本歸屬，但 Lambda 併發與 API Gateway throttling 等 quota 是以帳號為單位計算的，仍會被同帳號中的其他租戶影響。
>
> **B ✗** Encryption context 能幫助稽核每次解密屬於哪個租戶，但資料仍在共用 table、使用共用金鑰，不符合實體分離與專屬金鑰的要求。
>
> **C ✓** 專屬帳號提供獨立的 quota、帳單與爆炸半徑；透過 Account Factory 建立可以自動套用組織的 SCP 與 baseline；部署相同程式碼讓所有租戶維持同一個版本。
>
> **D ✗** 換 Region 雖然 quota 也分開，但同帳號中的權限、帳單與爆炸半徑仍然共用，而且可能違反客戶對資料位置的要求。
>
> **考點**：SAP-1.4、SAP-2.3｜帳號級 silo 與企業租戶需求

### 練習 49-9｜SAP｜單選｜可重跑的租戶 onboarding

一家 SaaS 公司的租戶 onboarding 由一支 Lambda 依序呼叫 Cognito、API Gateway、CloudFormation 等 API 完成。若中途任何一步失敗，工程師要手動檢查哪些資源已經建立、刪除重複的部分再重跑，平均每週花費 10 小時。公司要求新租戶在 5 分鐘內自動完成上線，失敗時可以自動恢復。

最合適的改善是什麼？

- A. 把 Lambda 的 timeout 提高到 15 分鐘，並在失敗時自動從頭重跑整支 Lambda
- B. 以 Step Functions 編排 onboarding，每一步設計成冪等（資源已存在即視為成功），並設定 retry 與失敗時進入人工處理的狀態
- C. 改用 SQS FIFO queue，讓每個 onboarding 步驟依序執行且不會重複
- D. 把 onboarding 改成每天一次的批次工作，由工程師集中檢查失敗項目

> [!answer]- 答案：B
> **A ✗** 從頭重跑非冪等的步驟會再建立一次已存在的資源，產生重複使用者或錯誤，正是目前要手動清理的原因。
>
> **B ✓** Step Functions 記錄每一步的執行狀態，失敗時只重試失敗的步驟；步驟冪等讓重試不會建立重複資源。真正無法自動恢復時才進入人工處理狀態，大幅降低人工負擔。
>
> **C ✗** FIFO 能保證訊息順序與短期去重，但不會追蹤多步驟流程的狀態，也無法讓非冪等的 API 呼叫變得可以安全重試。
>
> **D ✗** 每天一次的批次違反「5 分鐘內自動上線」的需求，也沒有減少人工處理。
>
> **考點**：SAP-3.1、SAP-2.1｜Step Functions 編排與冪等的自動化流程

### 練習 49-10｜SAP｜選兩項｜租戶身份與企業 IdP

一家 SaaS 公司目前所有租戶共用一個 Cognito user pool，以唯讀的 `custom:tenant_id` 區分租戶。一家新的企業客戶要求：員工必須用公司自己的 SAML IdP 登入，並套用與其他租戶不同、更嚴格的 MFA 政策。其他租戶維持現狀。

哪兩個做法最合適？（選兩項）

- A. 修改共用 user pool 的 MFA 政策為最嚴格的設定，讓所有租戶都適用
- B. 為該企業客戶建立專屬的 Cognito user pool，設定 SAML identity provider 與它需要的 MFA 政策
- C. 讓企業員工在共用 user pool 中以 email 自行註冊，再由客服手動設定 tenant_id
- D. 讓登入流程依租戶網域導向對應的 user pool，並讓 API 的 authorizer 能驗證來自每個 user pool 的 JWT
- E. 把企業客戶的員工建立成 IAM user，直接以 SigV4 簽章呼叫 API

> [!answer]- 答案：B、D
> **A ✗** 修改共用 user pool 的政策會影響所有其他租戶，違反「其他租戶維持現狀」。
>
> **B ✓** 專屬 user pool 可以獨立設定 MFA 與密碼政策，並串接企業自己的 SAML IdP 做聯合登入，是企業方案常見的做法。
>
> **C ✗** 自行註冊沒有使用企業 IdP，人工設定 tenant_id 也容易出錯，不符合需求。
>
> **D ✓** 使用多個 user pool 時，入口必須知道使用者屬於哪個 pool（例如依子網域），authorizer 也必須信任每個 pool 的簽章金鑰，才能正確驗證 token 並取出租戶 ID。
>
> **E ✗** 為外部客戶的員工建立 IAM user 會產生大量長期憑證，管理與安全負擔都很高，也不是面向終端使用者的身份方案。
>
> **考點**：SAP-2.3、SAP-1.2｜Cognito 多 user pool 與 SAML 聯合

### 練習 49-11｜SAP｜單選｜Pool 租戶的加密稽核

一家 SaaS 公司的 pool 租戶資料存放在共用的 DynamoDB table 與 S3 bucket 中，敏感欄位在應用程式中以 KMS 加密後再寫入。稽核人員要求能證明每次解密操作屬於哪個租戶，並希望在 KMS 層防止某個租戶的請求解密其他租戶的資料。公司不想為 2,000 個租戶各建立一把 KMS key。

最合適的做法是什麼？

- A. 為每個租戶建立 KMS key alias，指向同一把 KMS key
- B. 啟用 KMS key 的自動輪換，讓每個租戶的資料使用不同版本的金鑰
- C. 改用 CloudHSM，並為每個租戶建立一個 HSM 使用者
- D. 加密時帶上 encryption context `tenantId`，並在 key policy 或角色 policy 中以 `kms:EncryptionContext:tenantId` 條件比對 `${aws:PrincipalTag/TenantId}`

> [!answer]- 答案：D
> **A ✗** Alias 只是指向同一把金鑰的名稱，不提供任何存取限制，CloudTrail 中也無法區分是哪個租戶的資料。
>
> **B ✗** 自動輪換會產生新的金鑰材料，但不是依租戶分開，也無法區分或限制租戶。
>
> **C ✗** CloudHSM 需要自行管理叢集、使用者與高可用，營運負擔遠高於 KMS，也不是解決稽核需求的必要條件。
>
> **D ✓** Encryption context 會被記錄在 CloudTrail 中，可以證明每次解密屬於哪個租戶；解密時必須提供相同的 context，搭配 IAM 條件比對 session 的租戶 tag，就能在 KMS 層防止跨租戶解密。
>
> **考點**：SAP-2.3、SAP-1.2｜KMS encryption context 與 ABAC

### 練習 49-12｜SAP｜單選｜從 pool 升級到 silo 的遷移

一個大型租戶要從 pool 升級到企業方案的專屬帳號。它在共用 DynamoDB table 中有約 2,000 萬筆 item。公司要求遷移期間只能有短暫的唯讀時間，不能遺失任何資料，切換後若發現問題要能快速回到 pool，而且整個過程不需要修改應用程式碼。路由目前由 control plane 的 Tenants table 決定。

最合適的做法是什麼？

- A. 在專屬帳號建立 silo 環境，以批次工作依 partition key 複製歷史資料，短暫設為唯讀後同步最後的增量，再修改 Tenants table 中的路由，驗證後才刪除 pool 中的舊資料
- B. 直接修改 Tenants table 的路由指向新帳號，再開始複製資料
- C. 對整張 pool table 執行 export to S3，再整份匯入新帳號的 table
- D. 先刪除 pool 中該租戶的資料，再從最近一次的 PITR 備份還原到新帳號

> [!answer]- 答案：A
> **A ✓** 先複製、再短暫唯讀同步增量、最後只改一筆路由資料，滿足短暫唯讀與不遺失資料；切換由 control plane 決定，不必改程式；保留 pool 中的資料到驗證完成，失敗時只要把路由改回即可。
>
> **B ✗** 先切路由再複製資料，切換後的一段時間內新環境沒有歷史資料，租戶會看到資料不見，也可能寫入衝突。
>
> **C ✗** 匯出整張 pool table 會把其他 1,999 個租戶的資料一起搬到客戶專屬帳號，造成跨租戶資料外洩。
>
> **D ✗** 先刪除再還原，PITR 備份之後的資料會遺失，而且刪除後就無法快速回到 pool。
>
> **考點**：SAP-4.2、SAP-2.4｜租戶遷移與可回復的切換
