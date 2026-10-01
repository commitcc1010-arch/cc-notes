---
chapter: 40
title: Landing Zone 與多帳號架構設計
part: 8
---

# 第 40 章　Landing Zone 與多帳號架構設計

> [!abstract] 本章地圖
> **你會學到**：
> - 說得出一個帳號同時是安全、service quotas、帳單與爆炸半徑四種邊界，並據此畫出完整的帳號地圖：哪些是 foundational 帳號、哪些是 workload 帳號，各自為什麼存在
> - 依「政策與生命週期」而不是組織圖設計 OU，並安排 Sandbox、Policy Staging、Suspended 等特殊 OU
> - 選擇 Control Tower 的帳號供應方式（Account Factory、Account Factory Customization、AFT、CfCT），並安全地推出新 control
> - 設計不可竄改的集中化日誌、以 delegated administrator 為核心的集中安全架構，以及用 SCP、RCP 與 endpoint policy 圍出的 data perimeter
> - 為人、pipeline、服務三種角色選對跨帳號授權模式，並設計 root 與 break-glass 緊急存取
> - 讓新帳號一建立就自動套上 baseline，包含 tag 治理與帳號層級的安全預設值
>
> **前置知識**：第 12–14 章（IAM、跨帳號存取、Organizations 與 SCP、Control Tower 基礎）、第 16 章（CloudTrail、Config、GuardDuty、Security Hub）
> **考試比重**：SAA ★☆☆（Domain 1）｜SAP ★★★（Domain 1 多帳號環境與安全控制、Domain 3 營運卓越）

## 40.1 故事：併購之後，沒有人說得清楚有幾個帳號

Wanderly 完成了併購：對方是一家經營二十年的旅行社，有一座自己的資料中心、300 台 VM、Oracle 資料庫和一排 Windows 檔案伺服器。董事會給技術團隊十八個月，把旅行社的系統搬上 AWS，並讓整個集團通過支付卡產業的 PCI DSS 稽核。

雲端平台負責人阿哲在啟動會議上先做了一件事：盤點 AWS 帳號。結果讓所有人沉默。Wanderly 這幾年陸續開了 14 個帳號，有些在 Organization 裡、有些是工程師用公司信用卡自己開的；旅行社那邊早已有 6 個帳號在做實驗。有兩個帳號的 root 密碼只有一位已離職的工程師知道，三個帳號沒有開 CloudTrail，還有一個帳號裡同時跑著 production 訂單服務和實習生的練習專案。

稽核顧問的問題很直接：「誰能證明 production 的日誌沒有被改過？誰能在半夜三點進入任何一個帳號處理事故？新的帳號怎麼確定一開始就符合規範？」這三個問題，沒有一個有答案。

阿哲知道，在搬任何一台 VM 之前，必須先把地基打好。這個地基在 AWS 的術語裡叫做 **landing zone（著陸區）**：一個預先規劃好帳號結構、身份、日誌、安全、網路與治理規則的多帳號環境，讓之後每一個 workload 都能「降落」在已經合規的位置上。第 39 章結束在一個沒有答案的問題上：帳單翻了三倍，卻沒有人說得出是哪個團隊花的。成本歸屬最可靠的工具從來不是 tag，是帳號，因為每個帳號的費用天然就是分開的。Part 8 從這一章開始處理這一類企業規模的問題（多帳號、企業網路、多 Region、治理、遷移、現代化），考試比重也從 SAA 轉向 SAP；只考 SAA 的讀者可以略過 Part 8 的其他章，但本章 40.2 到 40.4 節的帳號與 OU 觀念 SAA 也會考。

第 14 章介紹了 Organizations、SCP 與 Control Tower 的運作原理；這一章要回答的是更難的設計問題：帳號要怎麼切、誰住在哪裡、怎麼讓幾十個帳號像一個整體一樣被治理。

## 40.2 帳號要切到多細：從四種邊界到切分原則

第 14 章說明了帳號為什麼是 AWS 上最強的隔離邊界。畫帳號地圖之前，先把那個結論變成可以操作的切分規則：帳號同時是四種邊界，而 tag、VPC 或 IAM policy 一次只能提供其中一種。

| 邊界 | 帳號提供的效果 | 只用 tag 或 VPC 切分時 |
|---|---|---|
| 安全邊界 | 預設情況下，一個帳號的 principal 完全碰不到另一個帳號的資源；跨帳號必須雙方都明確授權 | 同帳號內任何有寬鬆 IAM 權限的人都能碰到所有資源，靠 policy 條件維持隔離，容易漏 |
| 配額邊界 | Service quotas（例如 Lambda 並行數、EC2 vCPU）以帳號為單位計算 | 實驗專案把 Lambda 並行數用光，production 跟著被 throttle |
| 帳單邊界 | 每個帳號的費用天然分開，不需要 tag 就能 chargeback | 未打 tag 的資源費用無法歸屬 |
| 爆炸半徑（blast radius） | 帳號被入侵或誤操作，影響範圍限於該帳號 | 一把外洩的 access key 可能波及整個公司 |

**Blast radius（爆炸半徑）** 指的是一個錯誤或事故最多能波及的範圍。把 production 與開發放在不同帳號，等於在兩者之間砌了一道防火牆：開發人員就算在自己的帳號擁有 AdministratorAccess，也無法刪除 production 的資料庫。

這也是為什麼 AWS 的建議不是「一個環境一個帳號」，而是**「一個 workload 的一個環境一個帳號」**：訂單服務的 production、訂單服務的 staging、搜尋服務的 production……各自獨立。帳號數量因此會快速成長到數十甚至數百個，這正是後面幾節要解決的問題：帳號多了以後，要怎麼不失控。

> [!warning] 常見誤解
> 「帳號越多越安全，所以每個微服務都開帳號。」帳號是邊界，也是管理成本：每個帳號都要有 owner、預算、身份指派、日誌與網路連線。帳號切分的依據是**有沒有不同的安全需求、法規範圍、owner 或生命週期**，而不是程式碼怎麼拆。兩個由同一團隊維護、資料分類相同、一起部署的服務，放在同一個帳號通常更合理。

## 40.3 帳號地圖：foundational 帳號與 workload 帳號

阿哲把帳號分成兩大類。**Foundational 帳號（基礎帳號）** 提供整個組織共用的能力，數量少、變動少、由平台或資安團隊管理；**workload 帳號（工作負載帳號）** 放真正的應用程式，數量多、由應用團隊使用。

### Foundational 帳號

| 帳號 | 放什麼 | 誰能進來 | 為什麼要獨立 |
|---|---|---|---|
| Management（管理帳號） | Organization 本身、consolidated billing、Control Tower、IAM Identity Center（若未委派） | 極少數平台管理員 | SCP 對它無效，權限極大；裡面東西越少，被入侵的影響越可控 |
| Log Archive（日誌封存） | 組織所有 CloudTrail、Config、VPC Flow Logs 等日誌的 S3 bucket | 幾乎沒人；資安只讀 | 證據必須放在「被調查對象碰不到」的地方 |
| Audit／Security Tooling（稽核／安全工具） | GuardDuty、Security Hub、Config aggregator、Inspector、Macie 的 delegated administrator | 資安團隊 | 集中看全組織的安全狀態，且與 management account 分離 |
| Network（網路） | Transit Gateway、Direct Connect、集中 egress 與 inspection VPC、IPAM、Route 53 Resolver | 網路團隊 | 網路是共用的關鍵路徑，變更權限要集中（第 41 章） |
| Shared Services（共用服務） | Active Directory、CI 工具、共用 artifact repository、監控平台 | 平台團隊 | 多個 workload 都依賴的服務，有自己的 owner 與生命週期 |
| Deployments／CI-CD | 跨帳號部署的 pipeline | Pipeline 與平台團隊 | 讓「能部署到 production 的身份」集中在一處並受嚴格保護 |
| Backup（選用） | 跨帳號 AWS Backup vault | 備份管理員 | 勒索軟體攻擊來源帳號時，備份仍安全（第 43 章） |

其中 Log Archive 與 Audit 是 Control Tower 建立 landing zone 時預設就會建立的兩個帳號，放在名為 **Security** 的 OU 中。其餘帳號由你依需求補上。

### Workload 帳號

Workload 帳號依「workload × 環境」切：`booking-prod`、`booking-staging`、`booking-dev`、`search-prod`……。旅行社遷移過來的系統另外依資料敏感度切分：處理信用卡資料的支付系統獨立成 `payments-prod`，讓 **PCI DSS 的稽核範圍（cardholder data environment，持卡人資料環境）** 盡量只涵蓋這一個帳號，其他帳號不必接受同等級的稽核。

> [!tip] 考試提示
> 題目出現「縮小合規稽核範圍」「隔離受管制資料」時，答案通常是**把受管制的 workload 放到獨立帳號（與獨立 OU）**，再對該 OU 套用更嚴格的 SCP 與 controls，而不是在共用帳號中用 tag 區分。

### Sandbox 帳號

工程師需要一個可以自由嘗試新服務的地方。**Sandbox 帳號**和公司內部網路完全斷開（不接 Transit Gateway、不共享 Resolver rule），有嚴格的預算上限與自動清理機制。Sandbox 解決的是「沒有地方玩，只好在 dev 帳號裡玩」的問題，讓 dev 帳號保持乾淨。

## 40.4 OU 設計：依政策分組，不是照組織圖畫

有了帳號地圖，下一步是把帳號放進 **OU（Organizational Unit，組織單位）**。第 14 章說過，SCP 與其他 organization policies 可以掛在 OU 上，並被底下所有帳號繼承。這帶出 OU 設計的第一原則：**OU 是「政策的容器」，把需要相同政策與控制的帳號放在一起。**

許多公司第一次設計 OU 時會照著組織圖：「旅遊事業部 OU」「會員事業部 OU」「財務 OU」。問題是政策幾乎從來不是按部門區分的，「production 不能關閉 CloudTrail」「sandbox 不能建立 VPN」這類規則是按**環境與用途**區分的。照組織圖設計，同一條 production SCP 就要在每個部門 OU 底下各掛一次；組織改組時，還得大搬帳號。

### Wanderly 的 OU 結構

```text
Root
├── Security                    ← Control Tower 建立
│   ├── log-archive
│   └── audit
├── Infrastructure
│   ├── network-prod
│   ├── network-nonprod
│   └── shared-services
├── Workloads
│   ├── Prod                    ← 最嚴格：禁止關閉日誌、限制 Region、禁止 IAM user
│   │   ├── booking-prod
│   │   ├── search-prod
│   │   └── PCI                 ← 更嚴格：只允許核准服務、強制加密
│   │       └── payments-prod
│   └── NonProd
│       ├── booking-staging
│       ├── booking-dev
│       └── payments-staging
├── Deployments
│   └── cicd
├── Sandbox                     ← 不連公司網路、預算上限
│   └── sandbox-alice …
├── Policy Staging              ← 新 SCP／control 先在這裡測試
│   └── policy-test-01
├── Exceptions                  ← 有核准例外的帳號，定期檢討
└── Suspended                   ← 待關閉帳號：Deny All
```

逐層解說：

1. **Security 與 Infrastructure** 是 foundational OU，放第 40.3 節的基礎帳號。它們的政策側重「保護這些帳號不被修改」。
2. **Workloads** 底下先依環境分成 **Prod** 與 **NonProd**，因為兩者的政策差異最大。PCI 是 Prod 底下的子 OU，繼承 Prod 的全部限制，再疊加支付卡相關的限制。注意 `payments-staging` 放在 NonProd：如果 staging 只用測試卡號、不接觸真實持卡人資料，就不需要進入 PCI 範圍。
3. **Deployments** 放 CI/CD 帳號。它能部署到 production，是最有價值的攻擊目標之一，所以獨立出來。
4. **Policy Staging** 是測試新政策的地方，40.5 節會詳細說明。
5. **Exceptions** 放「因為合理原因需要例外」的帳號，例如某個帳號暫時需要使用尚未核准 Region 的服務。集中放置讓例外看得見、可以定期檢討，而不是散落在各處的 SCP 條件裡。
6. **Suspended** 放準備關閉的帳號，掛一條拒絕所有動作的 SCP。帳號關閉後會進入一段 post-closure 期間（約 90 天）才會永久刪除，這段期間仍可聯繫 AWS Support 救回。

### OU 設計的幾條規則

- **深度要節制。** Organizations 允許 OU 巢狀到 5 層，但層數越多，「這個帳號到底被哪些 SCP 影響」就越難推理。實務上 2–3 層足夠。
- **SCP 是交集，越往下只能越嚴。** 子 OU 不能「放寬」父 OU 的 deny。這正是 PCI 放在 Prod 底下的原因：自然繼承 Prod 的全部限制。
- **帳號移動 OU 會立刻改變它的權限上限。** 把帳號從 NonProd 移到 Prod 時，原本能用的動作可能立刻被擋下，需要事前驗證。
- **不要把 OU 當成網路邊界。** OU 管的是政策，與網路連通性無關。Prod 和 NonProd 帳號能不能互相連線，取決於第 41 章的 Transit Gateway route table 設計，不取決於它們在哪個 OU。

> [!warning] 常見誤解
> 「把 workload 直接放在 management account，反正它權限最大，最方便。」Management account 不受任何 SCP 限制，裡面的 workload 等於躲開了你為 Prod 設計的所有防護；一旦它被入侵，攻擊者可以修改整個 Organization。AWS 的建議是 management account **只放組織管理與帳單相關的東西**，安全工具也委派到 Audit 帳號。

## 40.5 Control Tower 進階：landing zone、controls 與帳號供應

第 14 章介紹過 **AWS Control Tower** 是建立在 Organizations 之上的 landing zone 服務。這一節進一步看 SAP 會考的部分：它到底幫你建了什麼、controls 怎麼安全地推出、既有的 Organization 怎麼納管、帳號供應有哪幾種方式。

### Landing zone 建立時發生了什麼

在 management account 啟用 Control Tower 並建立 landing zone 時，它會：

1. 建立（或讓你指定既有的）**Log Archive** 與 **Audit** 帳號，放進 Security OU。
2. 建立一條 **organization trail**，把所有已納管帳號的 CloudTrail 事件送到 Log Archive 帳號的 S3 bucket。
3. 在納管帳號啟用 **AWS Config** 的記錄，並在 Audit 帳號建立彙整視圖。
4. 可選擇設定 **IAM Identity Center**（第 13 章），作為人員登入所有帳號的入口。
5. 在 governed Regions（你選擇要治理的 Region）套用 mandatory controls，並可以啟用 **Region deny** 設定，拒絕在未治理 Region 中的大部分動作。
6. 提供 dashboard，顯示每個帳號與 OU 的 control 合規狀態。

### Controls 的三種行為與三種指引層級

**Control（控制，舊稱 guardrail）** 是 Control Tower 套用在 OU 上的一條治理規則。依照「什麼時候生效」分三種：

| 行為 | 底層實作 | 時機 | 例子 |
|---|---|---|---|
| Preventive（預防） | SCP（以及較新的 RCP 等 organization policies） | 動作發生時直接拒絕 | 禁止刪除 Log Archive 的 bucket |
| Detective（偵測） | AWS Config rules | 資源建立後發現不合規並回報 | 偵測未加密的 EBS volume |
| Proactive（主動） | CloudFormation hooks | 透過 CloudFormation 建立資源**之前**檢查 template | 拒絕部署沒有啟用 versioning 的 S3 bucket |

依「是否必須啟用」分為 **mandatory（必要，無法關閉，用來保護 landing zone 本身）**、**strongly recommended（強烈建議）** 與 **elective（選用）**。

三種行為的取捨值得記住：preventive 最強但最粗，只能看到 API 呼叫本身；detective 能檢查資源最終的完整設定，但只能事後發現；proactive 介於兩者之間，但只能攔住透過 CloudFormation 的部署，從 console 或 CLI 直接建立的資源它看不到。成熟的 landing zone 會**三種併用**。

### 安全地推出新 control：Policy Staging OU

資安團隊想在 Prod OU 加一條 SCP：「拒絕在 `ap-northeast-1` 與 `ap-southeast-1` 以外的 Region 建立資源」。這條 SCP 寫錯一個字，可能讓所有 production 服務的 IAM 或 CloudFront 操作失敗（這些 global 服務的 API 端點在 `us-east-1`）。

正確的推出流程是：

1. 在 **Policy Staging OU** 放一個與 Prod 設定相似的測試帳號，先把 SCP 套在這個 OU。
2. 在測試帳號中執行真實的部署 pipeline 與營運腳本，觀察 CloudTrail 中的 `AccessDenied` 事件。
3. 確認沒有誤擋後，套用到 NonProd，觀察一段時間，最後才套用到 Prod。
4. 用 IaC 管理 SCP（第 37 章），每次變更都有 review 與回復路徑。

這和應用程式的 canary deployment 是同一個想法：**治理規則也是會出錯的程式碼**，要分階段推出。

### 把既有帳號納入治理

旅行社那 6 個帳號原本不在 Control Tower 管理下。Control Tower 提供兩個動作：

- **Register OU（註冊 OU）**：把 Organization 中一個既有 OU 納入治理，Control Tower 會對 OU 內的帳號逐一 enroll，並套用該 OU 的 controls。
- **Enroll account（納管帳號）**：把單一帳號納入，Control Tower 會在帳號中部署 baseline（例如建立 `AWSControlTowerExecution` role、Config 記錄）。

要納管的帳號必須先處理衝突，例如帳號中已經有自己的 Config recorder 或 delivery channel，就要先移除或調整。最穩健的做法是先在一個非關鍵帳號試做，確認不會影響既有 workload 再擴大。

> [!warning] 常見誤解
> 「既有的 Organization 要用 Control Tower，就必須建立一個新的 Organization 再把帳號搬過去。」不需要。Control Tower 可以在既有 Organization 中建立 landing zone，再以 register OU、enroll account 的方式逐步納管。重新建立 Organization 反而要處理帳單、RI 共享、帳號邀請等大量遷移工作。

### Drift：治理狀態被改壞了

**Drift（漂移）** 是指 Control Tower 建立的資源或設定被人從外部修改，例如有人直接在 Organizations console 把帳號移到未註冊的 OU、修改了 Control Tower 管理的 SCP、或刪除了 Log Archive 帳號中的必要資源。Control Tower 會在 dashboard 顯示 drift，修復方式依類型而定：landing zone 層級的 drift 用 **reset／repair landing zone**，OU 或帳號層級的通常是重新 register OU 或重新 enroll 帳號。預防 drift 的根本方法是：**只透過 Control Tower 修改它管理的東西**，並用 SCP 限制其他人修改。

### 帳號供應的四種方式

Control Tower 建立新帳號的入口叫 **Account Factory**。在它之上，AWS 提供了不同程度的自訂方式：

| 方式 | 怎麼運作 | 適合 |
|---|---|---|
| Account Factory（console／Service Catalog） | 填寫帳號名稱、email、OU、SSO 使用者，透過 Service Catalog product 建立並套用 baseline | 帳號數量少、手動申請可接受 |
| Account Factory Customization（AFC） | 把一個 CloudFormation（或 Terraform）**blueprint** 登記成 **hub 帳號**（存放 blueprint 的帳號，通常就是平台團隊的 Shared Services 帳號）裡的 Service Catalog product，建立帳號時選擇 blueprint，帳號建好就套上 | 少數幾種標準帳號範本，想要在 console 一鍵完成 |
| Account Factory for Terraform（AFT） | 在獨立的 AFT management 帳號部署一組 Terraform pipeline；在 Git repository 新增一個帳號請求檔案，pipeline 就會建立帳號並執行 global 與 account-specific customizations | 團隊以 Terraform 為主、需要 GitOps 與大量帳號 |
| Customizations for Control Tower（CfCT） | 用一個 manifest 檔描述要部署到哪些 OU／帳號的 CloudFormation StackSets 與 SCP，由 pipeline 依 Control Tower lifecycle event 自動部署 | 團隊以 CloudFormation 為主，要讓所有帳號持續套用一致的資源 |

AFT 的 Git 結構是考試偶爾會問的細節：它使用四個 repository，分別是**帳號請求（account request）**、**所有帳號共用的 global customizations**、**特定帳號的 account customizations**，以及**帳號供應階段的 provisioning customizations**。帳號請求本身就是一段 Terraform：

```hcl
module "payments_prod" {
  source = "./modules/aft-account-request"

  control_tower_parameters = {
    AccountEmail              = "aws+payments-prod@wanderly.example"
    AccountName               = "payments-prod"
    ManagedOrganizationalUnit = "PCI (ou-a1b2-c3d4e5f6)" # 巢狀 OU 要寫成「名稱 (OU ID)」
    SSOUserEmail              = "platform-admin@wanderly.example"
    SSOUserFirstName          = "Platform"
    SSOUserLastName           = "Admin"
  }

  account_tags = {
    "cost-center"         = "CC-1042"
    "data-classification" = "pci"
    "owner"               = "payments-team"
  }

  change_management_parameters = {
    change_requested_by = "platform-team"
    change_reason       = "Migrate travel agency payment system"
  }

  account_customizations_name = "pci-baseline"
}
```

`ManagedOrganizationalUnit` 可以只寫 OU 名稱，但 PCI 是 Workloads/Prod 底下的巢狀 OU，AFT 要求巢狀 OU 必須寫成 `OU 名稱 (OU ID)` 的格式，才不會因為同名 OU 而放錯位置。

這段宣告把三件事綁在帳號誕生的那一刻：**它在哪個 OU（決定政策）**、**它的 owner 與成本中心（決定誰負責、帳單歸誰）**、**它要套哪一組 customizations（決定 baseline）**。事後補這些資訊幾乎一定會漏。

> [!note] 版本控制服務的選擇
> AFT 與 CfCT 早期的範例常用 AWS CodeCommit 作為 Git 來源。CodeCommit 曾在 2024 年 7 月停止開放新客戶，但 AWS 已於 2025 年 11 月宣布它恢復全面可用、重新開放新客戶。AFT 也支援 GitHub、GitLab、Bitbucket 等外部 Git 服務（透過 AWS CodeConnections 連線），CfCT 則可以使用 CodeCommit 或 S3 作為設定來源；依團隊既有的 Git 平台選擇即可。

## 40.6 集中化日誌：把證據放在嫌疑人碰不到的地方

回到稽核顧問的第一個問題：「誰能證明 production 的日誌沒有被改過？」如果日誌存在 production 帳號自己的 S3 bucket，答案是「沒有人能證明」：入侵 production 帳號的攻擊者，可以順手刪掉記錄自己行為的日誌。

集中化日誌的核心原則只有一句：**日誌的寫入權在產生日誌的帳號，日誌的刪改權不屬於任何 workload 帳號。**

### 日誌流向

```text
 workload 帳號（booking-prod、payments-prod …）        Log Archive 帳號
┌───────────────────────────────────┐            ┌───────────────────────────────┐
│ ① API 呼叫 ─────────────────────┐ │            │  S3: org-cloudtrail-logs      │
│                                 │ │  organization trail（由 management    │
│                                 └─┼──────────►│   或 delegated admin 建立）     │
│ ② Config recorder ──────────────┼─┼──────────►│  S3: org-config-history       │
│ ③ VPC Flow Logs ────────────────┼─┼──────────►│  S3: org-vpc-flowlogs         │
│ ④ 應用程式 log（CloudWatch Logs） │ │            │  ┌─────────────────────────┐  │
│     └ subscription filter ──────┼─┼──────────►│  │ Object Lock（compliance）│  │
└───────────────────────────────────┘  Firehose  │  │ SSE-KMS（金鑰在本帳號）    │  │
                                                 │  │ Lifecycle → Glacier      │  │
                                                 │  └─────────────────────────┘  │
 Audit 帳號                                       └──────────────┬────────────────┘
┌───────────────────────────────────┐                           │ ⑥ 唯讀查詢
│ ⑤ Config aggregator（全組織視圖）    │◄──────────────────────────┘ （Athena／Security Lake）
│   GuardDuty／Security Hub admin    │
└───────────────────────────────────┘
```

逐步解說：

1. **CloudTrail organization trail**：在 management account（或 CloudTrail 的 delegated administrator 帳號）建立一條 organization trail，就會自動涵蓋組織內所有帳號與 Region，包含之後新加入的帳號。成員帳號看得到這條 trail，但**無法停止、修改或刪除它**。日誌會依 `AWSLogs/<organization-id>/<account-id>/` 的路徑存到 Log Archive 的 bucket。
2. **AWS Config**：每個帳號的 configuration recorder 記錄資源設定的變化，delivery channel 把設定歷史與快照送到 Log Archive 的 bucket。
3. **VPC Flow Logs**：各 VPC 的 flow logs 直接以 Log Archive 的 S3 bucket 為目的地。
4. **應用程式日誌**：留在各帳號的 CloudWatch Logs 方便即時除錯；需要長期保存或集中分析的，用 **subscription filter** 送到中央帳號的 Kinesis Data Streams 或 Data Firehose，再寫入 S3（第 36 章）。
5. **Config aggregator** 放在 Audit 帳號，彙整全組織、全 Region 的資源設定與合規狀態，讓資安團隊不用逐一登入帳號。
6. 查詢時，資安團隊以唯讀身份使用 Athena 查 S3 中的日誌，或使用 **Amazon Security Lake** 把 CloudTrail、VPC Flow Logs、Route 53 Resolver query logs 等來源轉成標準的 OCSF 格式集中儲存。

### 讓 Log Archive 真的不可竄改

把日誌放在另一個帳號只是第一步。阿哲又加了四層保護：

1. **S3 Object Lock（compliance mode）**：bucket 啟用 versioning 與 Object Lock，設定預設保存期（例如一年）。Compliance mode 下，保存期內**任何人（包括 Log Archive 帳號的 root user）都無法刪除或覆寫物件版本**，也無法縮短保存期。法規只要求「防止一般使用者刪除」時，可以用允許特定權限繞過的 governance mode（第 23 章）。
2. **CloudTrail log file integrity validation（日誌檔完整性驗證）**：CloudTrail 每小時產生一個 digest 檔，包含該時段每個日誌檔的 SHA-256 雜湊並以私鑰簽章。稽核時可以用 CLI 驗證「日誌檔沒有被修改、刪除或偽造」。Object Lock 防止刪改，integrity validation 證明沒有被刪改，兩者回答的是不同問題。
3. **SSE-KMS 加密且金鑰放在 Log Archive 帳號**：key policy 只允許 CloudTrail 與 Config 服務用它加密、只允許資安的唯讀 role 解密（第 15 章）。
4. **SCP 防止從源頭停掉日誌**：日誌送不出來，再安全的 bucket 也沒用。在 Workloads 與 Infrastructure OU 掛上這條 SCP：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ProtectAuditTrail",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "cloudtrail:UpdateTrail",
        "cloudtrail:PutEventSelectors",
        "config:StopConfigurationRecorder",
        "config:DeleteConfigurationRecorder",
        "config:DeleteDeliveryChannel",
        "ec2:DeleteFlowLogs"
      ],
      "Resource": "*",
      "Condition": {
        "ArnNotLike": {
          "aws:PrincipalArn": [
            "arn:aws:iam::*:role/AWSControlTowerExecution",
            "arn:aws:iam::*:role/platform-logging-admin"
          ]
        }
      }
    }
  ]
}
```

這條 SCP 拒絕所有人停止或修改日誌設定，只放行 Control Tower 的執行 role 與平台團隊專用的 role。Organization trail 本身成員帳號就改不了，SCP 裡的 CloudTrail 動作保護的是各帳號另外建立的 trail，屬於縱深防禦；真正補上缺口的是 Config 與 flow logs 那幾個動作：沒有這條 SCP，workload 帳號的管理員可以直接停掉自己帳號的 Config recorder 或刪除 flow logs。有了它，即使某個 workload 帳號的管理員被入侵，攻擊者也關不掉這些記錄。

> [!tip] 考試提示
> 「日誌必須保存 N 年且不可刪除，連管理員也不行」→ **S3 Object Lock compliance mode**。「要能證明日誌沒被修改」→ **CloudTrail log file integrity validation**。「所有帳號、包含未來新帳號都要記錄」→ **organization trail**。三個關鍵字常常一起出現在選項裡，要分清楚各自解決什麼。

### 日誌的成本控制

CloudTrail 的 management events 第一份副本不收費，但 **data events**（例如每一次 S3 `GetObject`、Lambda `Invoke`）量非常大，對所有 bucket 全開可能產生可觀費用。常見做法是只對存放敏感資料的 bucket 與關鍵 Lambda 開啟 data events，並使用 advanced event selectors 篩選。S3 中的日誌則用 lifecycle 轉到 Glacier 類別，保存期滿再刪除（第 23 章）。

## 40.7 集中安全：delegated administrator 模式

日誌回答了「發生過什麼」，但資安團隊還需要「現在有什麼威脅、哪些設定不合規」。第 16 章介紹過 GuardDuty、Security Hub、Inspector、Macie 等服務；在多帳號環境中，關鍵問題是：**這些服務的管理者帳號要放在哪裡？**

### 為什麼不放在 management account

大多數安全服務都能和 Organizations 整合，由一個「管理者帳號」統一啟用、設定並查看所有成員帳號的 findings。最直覺的選擇是 management account，但這違反了 40.4 節的原則：資安團隊每天要登入查看 findings，等於要給他們 management account 的存取權。

**Delegated administrator（委派管理員）** 解決了這個問題：management account 只做一次動作，「把某個服務的管理權委派給 Audit 帳號」，之後資安團隊只需要 Audit 帳號的權限。

| 服務 | 委派後 Audit 帳號能做什麼 | 要注意的細節 |
|---|---|---|
| GuardDuty | 為所有成員帳號啟用偵測、設定 protection plans、查看所有 findings | **Regional 服務**：每個 Region 都要指定 delegated admin 並設定 auto-enable |
| Security Hub | 彙整所有帳號的 findings 與合規標準檢查結果 | 可用 central configuration 從一個 home Region 管理所有帳號與 linked Regions 的設定 |
| AWS Config | 建立 organization aggregator、部署 organization rules 與 conformance packs | Recorder 仍要在每個帳號、每個 Region 啟用 |
| IAM Access Analyzer | 以整個 Organization 為 **zone of trust（信任區）**，找出被組織外部存取的資源 | 只有組織外的存取才會產生 external access finding |
| Inspector、Macie、Detective | 對全組織掃描弱點、敏感資料、調查事件 | 同樣多為 Regional，需逐 Region 設定 |
| Firewall Manager | 對全組織部署 WAF、Shield Advanced、security group、Network Firewall 政策 | 需要指定 Firewall Manager administrator 帳號，且成員帳號要啟用 Config |

> [!note] Security Hub 的新版本
> 2025 年起，原本的 Security Hub 改稱 **Security Hub CSPM**（專注於安全標準與設定合規檢查），AWS 另外推出整合更多偵測來源的新版 Security Hub。考試題目通常只要求你知道「Security Hub 是集中彙整 findings 與執行合規標準檢查的地方，並以 delegated admin 跨帳號管理」。

### Auto-enable：新帳號不能有空窗期

稽核最在意的不是「現在所有帳號都開了 GuardDuty」，而是「**下一個新帳號建立的那一刻**，GuardDuty 也已經開了」。GuardDuty、Security Hub、Inspector、Macie 等服務的 delegated admin 都可以設定 **auto-enable**：新加入組織的帳號自動被啟用。GuardDuty 還可以選擇只對新帳號自動啟用，或對所有既有帳號一併啟用。

GuardDuty 是 Regional 這件事是考試最常設的陷阱：Wanderly 在東京設定好 delegated admin 與 auto-enable，新加坡的帳號仍然沒有被保護。正確做法是**在每個使用中的 Region 都指定同一個 delegated admin 帳號**，並在每個 Region 設定 auto-enable；未使用的 Region 則用 Control Tower 的 Region deny 擋住，減少需要保護的面積。

### 從 finding 到處置

Findings 集中後，下一步是自動處置：Security Hub 或 GuardDuty 的 findings 都會送到 EventBridge，可以在 Audit 帳號設定 rule，觸發 Lambda 或 Systems Manager Automation，例如自動隔離被判定為挖礦的 EC2（第 38 章）。自動處置的 role 需要跨帳號 assume 到目標帳號，這就帶到下一節：跨帳號授權要怎麼設計。

## 40.8 跨帳號授權模式：人、pipeline 與服務

帳號切開之後，「誰可以進入哪個帳號、做什麼」成為整個 landing zone 最核心的設計。第 13 章介紹過 AssumeRole、trust policy 與 IAM Identity Center 的機制；在企業層級，要把存取需求分成三類，每一類有不同的標準答案。

### 第一類：人員存取用 IAM Identity Center

所有人員都透過 **IAM Identity Center** 登入，身份來源接公司的 IdP（例如 Microsoft Entra ID 或 Okta，以 SCIM 自動同步使用者與群組）。管理員定義 **permission set（權限集）**，再把「群組 × permission set × 帳號」做 assignment，Identity Center 會在每個被指派的帳號自動建立對應的 role。

設計重點：

- **指派給群組，不指派給個人。** 員工換部門時，只需在 IdP 調整群組成員。
- **Permission set 依職務設計**，例如 `ReadOnly`、`Developer`（只限 NonProd）、`ProdOperator`（Prod 的有限操作）、`SecurityAudit`。
- **把 Identity Center 委派給一個成員帳號管理**，避免日常的權限維護需要登入 management account。注意：指派到 management account 本身的 permission set 仍只能由 management account 管理。
- **組織中不應存在長期 IAM user 與 access key**，可用 SCP 拒絕 `iam:CreateUser` 與 `iam:CreateAccessKey`（break-glass 帳號除外）。

### 第二類：pipeline 用集中的部署 role

Wanderly 的部署 pipeline 位於 `cicd` 帳號。每個 workload 帳號都有一個 `deploy` role，trust policy 只信任 pipeline 的 role：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111122223333:role/pipeline-booking"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalOrgID": "o-a1b2c3d4e5"
        }
      }
    }
  ]
}
```

這個設計讓「能變更 production 的身份」只有一個地方需要保護。`deploy` role 的權限再搭配 permission boundary（第 14 章），即使 pipeline 被注入惡意步驟，也只能建立受限的資源。CloudFormation **StackSets** 的 service-managed 模式則是另一種 pipeline 形態：由 management 或 delegated admin 帳號對整個 OU 部署 stack，StackSets 自動處理跨帳號 role。

### 第三類：服務對服務用 resource policy 加組織條件

Workload 帳號的 Lambda 要讀取 `shared-services` 帳號的 S3 bucket，可以讓 Lambda assume 跨帳號 role，也可以在 bucket policy 中直接授權對方的 role。企業環境中，resource policy 常加上**組織層級的條件鍵**：

- `aws:PrincipalOrgID`：呼叫者必須屬於我們的 Organization。
- `aws:PrincipalOrgPaths`：呼叫者必須屬於特定 OU 路徑，例如只允許 Prod OU 底下的帳號。
- `aws:ResourceOrgID`：被存取的資源必須屬於我們的 Organization，常用在 SCP 或 endpoint policy，防止員工把資料寫到外部帳號的 bucket。

### Data perimeter：用三種政策圍出組織邊界

把以上條件鍵系統化，就是 **data perimeter（資料邊界）** 的概念：確保「只有我信任的身份，從我預期的網路，存取我信任的資源」。

| 邊界 | 要防止什麼 | 主要工具 |
|---|---|---|
| 身份邊界 | 組織外的身份存取我的資源 | **RCP（resource control policy）** 搭配 `aws:PrincipalOrgID`；resource policy |
| 資源邊界 | 我的身份把資料送到組織外的資源 | SCP 搭配 `aws:ResourceOrgID`；VPC endpoint policy |
| 網路邊界 | 憑證外洩後從公司網路以外使用 | `aws:SourceVpc`、`aws:SourceIp` 條件；VPC endpoint |

**RCP** 是第 14 章提過的、掛在 OU 上但作用在「資源」的 organization policy。SCP 限制的是「我的 principal 能做什麼」，管不到外部帳號的身份；RCP 則限制「我的資源最多能被誰存取」，支援 S3、STS、KMS、SQS、Secrets Manager 等服務。即使某個開發者寫了一條允許 `"Principal": "*"` 的 bucket policy，RCP 中「拒絕組織外 principal」的規則仍然有效，因為 RCP 和 resource policy 是取交集。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceOrgIdentities",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "*",
      "Condition": {
        "StringNotEqualsIfExists": {
          "aws:PrincipalOrgID": "o-a1b2c3d4e5"
        },
        "BoolIfExists": {
          "aws:PrincipalIsAWSService": "false"
        }
      }
    }
  ]
}
```

第二個條件 `aws:PrincipalIsAWSService` 很重要：CloudTrail、Config 等 AWS 服務寫入 bucket 時，呼叫者是服務本身而不屬於任何 Organization，必須排除它們，否則 40.6 節的日誌會寫不進去。真實部署前，一樣要先在 Policy Staging OU 驗證。

### 一個要特別注意的預設 role

透過 Organizations 建立的帳號，會自動有一個 **`OrganizationAccountAccessRole`**，擁有 AdministratorAccess，並信任 management account。它方便初期設定，但等於「management account 的任何管理員都是所有成員帳號的管理員」。成熟的 landing zone 會限制誰能在 management account 中 assume 這個 role，或在帳號 baseline 完成後收緊它的 trust policy。邀請加入的既有帳號則不會自動有這個 role。

## 40.9 Root user 與 break-glass：最後一道門

稽核顧問的第二個問題是：「誰能在半夜三點進入任何一個帳號處理事故？」這其實包含兩個子問題：每個帳號的 root user 怎麼管，以及平常的登入機制壞掉時怎麼辦。

### 集中管理成員帳號的 root

20 個帳號就有 20 組 root 密碼與 MFA 要保管，這正是 Wanderly 「只有離職工程師知道密碼」的問題來源。AWS 在 2024 年底推出 **centralized root access（集中 root 存取管理）**：在 IAM 啟用這項 Organizations 功能後，management account（或其委派的帳號）可以：

- **移除成員帳號的 root 憑證**（密碼、access key、MFA 裝置），之後新建立的成員帳號也預設沒有 root 憑證。
- 需要執行只有 root 能做的少數動作時（例如刪除一條把所有人都鎖在外面的 S3 bucket policy 或 SQS queue policy），從中央帳號以 `sts:AssumeRoot` 取得**僅限該任務、短期有效**的 root session，所有操作都記錄在 CloudTrail。

這把「保管幾十組 root 密碼」變成「保護一個中央帳號的少數權限」。Management account 本身的 root 仍然存在，要用硬體 MFA 保護並嚴格保管。

### Break-glass：IdP 掛掉的那一天

**Break-glass（破窗）存取** 是指在正常登入流程失效時使用的緊急存取路徑，名稱來自「打破玻璃才能拉的火警開關」。Wanderly 所有人都透過 Identity Center 與外部 IdP 登入；如果 IdP 服務中斷、SCIM 同步錯誤刪光了群組，或 Identity Center 所在 Region 有問題，所有人都進不了 AWS，偏偏這時可能正是需要處理事故的時刻。

阿哲的 break-glass 設計：

1. **不依賴 IdP**：在一個專用帳號（或 management account）中建立 2 個 break-glass IAM user，各自使用硬體 MFA。密碼分成兩半由不同主管保管，存放在實體保險箱。
2. **最小但足夠的權限**：break-glass user 本身只能 assume 每個帳號中的 `break-glass` role；該 role 的 trust policy 只信任這兩個 user，並被 SCP 排除在「禁止 IAM user」的規則之外。
3. **使用即告警**：EventBridge rule 監聽 break-glass user 的 `ConsoleLogin` 與 `AssumeRole` 事件，立刻通知資安與主管。正常情況下這個告警永遠不應響起。
4. **定期演練**：每季實際演練一次，確認密碼、MFA、權限都還有效，演練後輪替密碼。

> [!warning] 常見誤解
> 「break-glass 就是把 root 密碼寫在 wiki 上給值班人員。」Break-glass 的重點是**獨立於日常機制、存取受控、使用即被發現、定期驗證**。存放在 wiki 的密碼違反了每一點。另外，break-glass 路徑不能依賴它要備援的那個系統：如果 break-glass 也要透過同一個 IdP 登入，IdP 掛掉時它一樣無效。

## 40.10 Tag 治理：讓每個資源出生就帶著身分證

稽核顧問的第三個問題延伸到資源層級：「這台 EC2 是誰的？屬於哪個成本中心？處理什麼等級的資料？」帳號邊界回答了一部分，但同一個帳號裡仍有很多資源，需要 **tag（標籤）**。

### 四種工具，各管一段

| 工具 | 能做什麼 | 不能做什麼 |
|---|---|---|
| Tag policy（Organizations） | 規定 tag key 的大小寫與允許的 value；對指定資源類型開啟 enforcement 後，**拒絕把不合規的值寫進 tag**；較新的 required tags（`report_required_tag_for`）可回報缺少必要 tag 的資源，並讓已設定的 IaC 工具（CloudFormation hook、Terraform、Pulumi）在部署前擋下 | **無法在 API 層阻止建立「完全沒有 tag」的資源**：從 console、CLI 或 SDK 直接呼叫 `RunInstances` 不會被擋 |
| SCP + `aws:RequestTag` 條件 | 建立資源的 API 呼叫若沒帶必要 tag 就拒絕 | 只對支援在建立時加 tag 的 API 有效；寫錯會擋住正常部署 |
| Config rule `required-tags` | 偵測既有資源缺少哪些 tag，可搭配自動修復 | 事後偵測，不會阻止建立 |
| Cost allocation tags | 在帳單與 Cost Explorer 中依 tag 分攤費用 | 必須在 management（payer）帳號**啟用**後才生效；預設只從啟用後開始，需要歷史資料時可申請 backfill（最多回溯 12 個月） |

最常見的考題陷阱就是第一列：tag policy 名字聽起來像是「強制 tag」，但它的 enforcement 強制的是「如果你加了這個 tag，值必須合規」，不是「你一定要加」。AWS 後來加入的 required tags 功能也只在 IaC 工具的部署流程中檢查，不會擋下直接的 API 呼叫。要做到「不論從哪裡呼叫，沒有 `cost-center` tag 就不能啟動 EC2」，需要 SCP：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequireCostCenterOnRunInstances",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "Null": {
          "aws:RequestTag/cost-center": "true"
        }
      }
    }
  ]
}
```

`Null` 條件為 `true` 表示「request 中不存在這個 tag」，此時拒絕。注意 `Resource` 只列 instance：`RunInstances` 同時會涉及 volume、subnet、security group、AMI 等資源，這些資源在呼叫中多半不會帶新 tag，若把 `Resource` 寫成 `*`，所有啟動都會被擋。

### 帳號層級的 tag

除了資源 tag，Organizations 也能對**帳號本身**加 tag（例如 40.5 節 AFT 範例中的 `cost-center`、`data-classification`）。帳號 tag 有三個用途：一是**成本分攤**，帳號 tag 啟用為 cost allocation tag 後，帳號內所有用量（包括無法打 tag 的費用）都會自動帶上它；二是**管理權限**，在 IAM policy 中以帳號 tag 作為 Organizations API 的條件，例如只允許平台團隊移動 `data-classification` 為 `pci` 的帳號；三是**自動化的輸入**，baseline pipeline 可以讀取帳號 tag 決定要套用哪一組設定。注意帳號 tag 不會自動變成帳號內資源的 tag，要限制資源存取仍要靠 OU、SCP 與資源 tag。依 tag 做成本可視化與 chargeback 的細節在第 43 章。

## 40.11 新帳號 baseline 自動化

前面每一節都在說「新帳號一建立就要……」：要進對 OU、要有 owner tag、要被 GuardDuty 保護、要送日誌、要接上網路。如果這些靠工程師照 runbook 手動做，帳號多到第 30 個時一定會漏。**Baseline（基準設定）** 就是每個新帳號都必須具備的一組設定，而且必須自動完成。

### 自動化流程

```text
① 申請：在 Git 提交帳號請求（AFT）或從 Service Catalog 申請
        │
② 建立：Control Tower Account Factory 建立帳號、放進指定 OU、
        │   部署 Control Tower baseline（organization trail、Config 記錄、controls）
        │
③ 事件：Control Tower 在 management account 發出
        │   CreateManagedAccount lifecycle event（經 EventBridge）
        ├──────────────► ④a StackSets（service-managed，auto-deployment 到 OU）
        │                   部署 IAM roles、帳號安全預設值
        ├──────────────► ④b CfCT／AFT customizations
        │                   部署 OU 或帳號專屬的資源
        └──────────────► ④c Step Functions／Lambda
                            呼叫網路帳號：從 IPAM 取 CIDR、建 VPC、接 TGW（第 41 章）
                            建立 Budgets、登記 CMDB、通知 owner
        │
⑤ 自動生效（不需動作）：GuardDuty／Security Hub／Inspector 的 auto-enable、
                        Identity Center 群組 assignment、tag policy 與 SCP 繼承
```

逐步解說：

1. 申請入口只有一個，申請內容包含 OU、owner、成本中心與資料分類，缺一不可。
2. Control Tower 負責帳號本身與 landing zone 必要的 baseline。
3. **Lifecycle event** 是串接其他自動化的關鍵：Control Tower 完成帳號建立時會產生 `CreateManagedAccount` 事件，下游自動化以它為觸發點，而不是用排程輪詢。
4. 依性質選擇工具：
   - 「每個 OU 底下的帳號都要有」的資源，用 **StackSets service-managed 搭配 automatic deployment**：帳號加入目標 OU 時自動部署，帳號移出時可自動移除。
   - 依 OU 或個別帳號而異的客製化，用 CfCT 或 AFT 的 customizations。
   - 需要跨帳號協調、呼叫外部系統的步驟，用 Step Functions 編排。
5. 凡是能用 Organizations 層級「繼承」或「auto-enable」達成的，就不必再寫程式：SCP 與 tag policy 隨 OU 繼承，安全服務靠 auto-enable 涵蓋新帳號。

### Wanderly 的 baseline 清單

| 類別 | 項目 | 實作方式 |
|---|---|---|
| 身份 | 依 OU 指派 Identity Center 群組與 permission set；建立 `break-glass`、`deploy`、`security-audit` role | Identity Center assignment 自動化、StackSets |
| 日誌 | Organization trail、Config recorder、VPC Flow Logs 送往 Log Archive | Control Tower baseline、customizations |
| 安全服務 | GuardDuty、Security Hub、Inspector、Macie | Delegated admin auto-enable |
| 帳號安全預設 | 帳號層級 S3 Block Public Access、EBS 預設加密、EC2 預設要求 IMDSv2、IAM Access Analyzer | StackSets（注意 EBS 預設加密與 IMDS 預設是逐 Region 設定） |
| 網路 | 刪除每個 Region 的 default VPC；從 IPAM 取得 CIDR 建立 VPC 並接上 Transit Gateway（Sandbox 除外） | AFT 功能選項或 Step Functions |
| 成本 | AWS Budgets 預算與告警、cost allocation tags | Customizations |
| 文件 | 帳號 owner、聯絡人（security／billing／operations alternate contacts） | Organizations API（可從 management account 集中設定） |

這張表就是稽核顧問第三個問題的答案：「新的帳號怎麼確定一開始就符合規範？」因為帳號在交給應用團隊之前，baseline 已經由程式全部套用完成，而 detective controls 會持續確認它們沒有被改掉。

## 40.12 比較與選型

### 帳號供應與客製化工具

| 需求 | 選擇 |
|---|---|
| 少量帳號，手動在 console 申請即可 | Control Tower Account Factory |
| 幾種固定帳號範本，想在 console 建立時一併套用 | Account Factory Customization（blueprint） |
| Terraform 團隊、GitOps、大量帳號 | Account Factory for Terraform（AFT） |
| CloudFormation 團隊，所有 OU 持續套用一致資源與 SCP | Customizations for Control Tower（CfCT） |
| 只需把一組 CloudFormation 資源自動部署到 OU 的所有帳號 | StackSets service-managed + automatic deployment |
| 不使用 Control Tower，自建 landing zone | Organizations + StackSets + 自建 pipeline（營運負擔最高） |

### 治理工具對照

| 想做到 | 工具 | 時機 |
|---|---|---|
| 限制帳號內的身份最多能做什麼 | SCP | 預防 |
| 限制資源最多能被誰存取（包含組織外） | RCP | 預防 |
| 透過 CloudFormation 部署前擋下不合規設定 | Control Tower proactive control（CloudFormation hooks） | 部署前 |
| 發現既有資源不合規 | Config rules／Control Tower detective control | 事後 |
| 統一 tag key 與值 | Tag policy | 寫入 tag 時 |
| 強制建立資源時必須帶 tag | SCP + `aws:RequestTag` | 預防 |
| 找出被組織外部存取的資源 | IAM Access Analyzer（zone of trust = organization） | 持續分析 |

### 「這個東西放哪個帳號？」決策流程

```text
它是組織管理或帳單本身嗎？
├─ 是 → Management account（只放這些）
└─ 否 → 它是日誌或稽核證據的儲存嗎？
         ├─ 是 → Log Archive
         └─ 否 → 它是安全服務的集中管理或調查工具嗎？
                  ├─ 是 → Audit／Security Tooling（delegated admin）
                  └─ 否 → 它是多個 workload 共用的網路元件嗎？
                           ├─ 是 → Network 帳號
                           └─ 否 → 它是多個 workload 共用的平台服務嗎？
                                    ├─ 是 → Shared Services／Deployments
                                    └─ 否 → 該 workload 該環境自己的帳號
```

## 40.13 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 隔離 prod／dev 的權限、帳單、配額與爆炸半徑 | 分開的 AWS 帳號，依環境分 OU |
| 縮小 PCI／合規稽核範圍 | 受管制 workload 放獨立帳號與子 OU，套更嚴格的 SCP |
| 快速建立符合最佳實務的多帳號環境，營運負擔最低 | AWS Control Tower landing zone |
| Terraform、GitOps、大量帳號自動供應 | Account Factory for Terraform（AFT） |
| 新 SCP 要先測試，不能影響 production | Policy Staging OU，分階段推出 |
| 既有 Organization 導入 Control Tower | 在既有 Organization 建立 landing zone，register OU／enroll account |
| 所有帳號（含未來新帳號）的 API 活動集中保存 | CloudTrail organization trail → Log Archive 帳號 |
| 日誌在保存期內任何人都不能刪除 | S3 Object Lock compliance mode |
| 證明日誌未被竄改 | CloudTrail log file integrity validation |
| 資安團隊集中管理 GuardDuty／Security Hub，不要用 management account | Delegated administrator（Audit 帳號） |
| 新帳號、新 Region 也要立即被 GuardDuty 保護 | 每個 Region 指定 delegated admin 並開啟 auto-enable |
| 全組織資源設定與合規總覽 | Config organization aggregator（delegated admin 帳號） |
| 防止組織外的身份存取我們的 S3／KMS，即使 bucket policy 寫錯 | RCP + `aws:PrincipalOrgID` |
| 防止員工把資料複製到組織外的 bucket | SCP 或 endpoint policy + `aws:ResourceOrgID` |
| 成員帳號 root 密碼難以保管 | Centralized root access：移除成員 root 憑證、`sts:AssumeRoot` |
| IdP 故障時仍能進入 AWS | 獨立於 IdP 的 break-glass IAM user + 硬體 MFA + 使用告警 |
| 沒有某個 tag 就不能建立資源 | SCP + `aws:RequestTag`（不是 tag policy） |
| 新帳號自動部署標準 role 與設定 | StackSets service-managed automatic deployment、CfCT、lifecycle event |

**常見陷阱**：

1. 以為 SCP 可以保護 management account 裡的 workload：SCP 對 management account 無效，workload 本來就不該放那裡。
2. 以為 tag policy 可以阻止建立沒有 tag 的資源：它只管已加上的 tag 值是否合規。
3. 以為在一個 Region 設定 GuardDuty delegated admin 就涵蓋全球：GuardDuty、Inspector、Macie 等都是 Regional。
4. 把日誌存在產生日誌的帳號、只靠 IAM 限制刪除：帳號管理員被入侵時就失效；要放到 Log Archive 並加上 Object Lock。
5. 把 Object Lock 與 log file integrity validation 混為一談：前者防止刪改，後者證明沒被刪改。
6. 寫 RCP 拒絕組織外 principal 卻忘了排除 AWS 服務，導致 CloudTrail、Config 寫不進日誌 bucket。

## 本章重點整理

- 帳號同時是安全、配額、帳單與爆炸半徑四種邊界，建議以「一個 workload 的一個環境一個帳號」切分，並把受管制資料獨立以縮小稽核範圍。
- Foundational 帳號包括 management、Log Archive、Audit（安全工具）、Network、Shared Services 與 Deployments；management account 只放組織管理與帳單。
- OU 是政策的容器，應依環境與政策需求設計（Security、Infrastructure、Workloads/Prod、Workloads/NonProd、Sandbox、Policy Staging、Exceptions、Suspended），而不是照組織圖。
- SCP 只能往下越來越嚴；把需要額外限制的帳號放在繼承父 OU 限制的子 OU，帳號換 OU 會立即改變它的權限上限。
- Control Tower 建立 Log Archive 與 Audit 帳號、organization trail、Config 記錄與 controls；controls 分 preventive（SCP/RCP）、detective（Config）、proactive（CloudFormation hooks）。
- 新 control 先在 Policy Staging OU 驗證，再依 NonProd、Prod 分階段推出；既有 Organization 以 register OU 與 enroll account 逐步納管。
- 帳號供應依團隊工具選擇 Account Factory、AFC blueprint、AFT（Terraform GitOps）或 CfCT（CloudFormation manifest）。
- 集中化日誌把 organization trail、Config、flow logs 送到 Log Archive，並以 Object Lock compliance mode、integrity validation、SSE-KMS 與保護日誌設定的 SCP 確保不可竄改。
- 安全服務以 delegated administrator 委派給 Audit 帳號，搭配 auto-enable；GuardDuty 等 Regional 服務要逐 Region 設定。
- 人員存取走 IAM Identity Center（群組 × permission set × 帳號），pipeline 走集中部署 role，服務對服務用 resource policy 加上 `aws:PrincipalOrgID` 等組織條件。
- RCP 限制資源能被誰存取，可在 bucket policy 寫錯時仍阻擋組織外 principal；與 SCP、endpoint policy 一起構成 data perimeter。
- Centralized root access 可移除成員帳號的 root 憑證並以 `sts:AssumeRoot` 執行少數 root 任務；break-glass 路徑必須獨立於 IdP、使用即告警並定期演練。
- Tag policy 規範 tag 值（required tags 只在 IaC 部署時檢查），要在 API 層強制「必須有 tag」得用 SCP 的 `aws:RequestTag`；cost allocation tags 要在 payer 帳號啟用。
- 新帳號 baseline 以 lifecycle event、StackSets automatic deployment、customizations 與 auto-enable 自動完成，帳號交付前就已合規。

## 本章練習題

### 練習 40-1｜SAA｜單選｜多帳號隔離的基本選擇

Wanderly 的 production 與開發環境目前都在同一個 AWS 帳號中，以 tag 區分。上個月一位開發人員的測試腳本用光了帳號的 Lambda 並行數配額，導致 production API 被 throttle；財務也抱怨無法準確分攤未打 tag 的資源費用。公司希望用最少的營運負擔建立長期可擴充的隔離方式。

最合適的做法是什麼？

- A. 在同一帳號中為開發人員建立 permission boundary，並為 production Lambda 設定 reserved concurrency
- B. 使用 AWS Control Tower 建立 landing zone，把 production 與開發分別放在不同 OU 下的不同帳號
- C. 為 production 與開發各建立一個 VPC，並以 security group 限制兩者之間的流量
- D. 在帳號中啟用 tag policy，強制所有資源都必須帶有 environment tag

> [!answer]- 答案：B
> **A ✗** Permission boundary 與 reserved concurrency 可以緩解單一症狀，但配額、帳單與爆炸半徑仍然共用；隨著團隊增加，要維護的例外會越來越多。在只有單一 workload、短期內無法拆帳號時，它是合理的暫時措施。
>
> **B ✓** 帳號同時隔離權限、service quotas 與帳單。Control Tower 以最少營運負擔建立含 log archive、audit 帳號與 controls 的多帳號環境，未來新增帳號也有一致的 baseline。
>
> **C ✗** VPC 只是網路邊界，Lambda 並行數配額與帳單仍以帳號計算，IAM 權限也沒有被隔開。
>
> **D ✗** Tag policy 只規範 tag 值的格式，無法強制資源一定要有 tag，也完全不影響配額共用的問題。
>
> **考點**：SAA-1.1｜帳號作為安全、配額與帳單邊界

### 練習 40-2｜SAP｜單選｜OU 結構設計

Wanderly 目前的 OU 依事業部劃分：旅遊事業部、會員事業部、財務部，每個 OU 底下同時有 production 與開發帳號。資安團隊要求所有 production 帳號禁止停用 CloudTrail、只能使用兩個核准 Region，開發帳號則允許較多實驗。目前每條 production SCP 都必須在三個事業部 OU 中以條件判斷帳號是否為 production，維護困難且已發生漏套。公司明年還會再改組事業部。

應如何重新設計 OU？

- A. 保留事業部 OU，在每個帳號直接附加 production SCP，不再掛在 OU 上
- B. 在每個事業部 OU 底下再建立 Prod 與 NonProd 子 OU，把 production SCP 分別掛在三個 Prod 子 OU 上
- C. 把所有帳號移到 Root 底下，用 SCP 中的 `aws:PrincipalTag/environment` 條件區分 production 與開發
- D. 建立 Workloads OU，底下依環境分為 Prod 與 NonProd 子 OU，把 production SCP 只掛在 Prod OU；事業部歸屬改以帳號 tag 記錄

> [!answer]- 答案：D
> **A ✗** 直接掛在帳號上仍要為每個新 production 帳號記得附加 SCP，漏套的風險沒有消除；Organizations 也有每個目標可附加的 SCP 數量限制。
>
> **B ✗** 能運作，但同一條 SCP 要維護三份，改組時還要搬移帳號。OU 應依政策需求分組，事業部只是 metadata。
>
> **C ✗** Principal tag 由各帳號的管理員控制，帳號管理員可以修改自己 role 的 tag 來繞過限制；把所有帳號放在 Root 也失去依 OU 繼承政策的能力。
>
> **D ✓** OU 是政策的容器。依環境分 OU 後，production 政策只要掛一次，新帳號放進 Prod OU 就自動繼承；事業部歸屬改成帳號 tag，改組時不需要搬帳號、也不影響政策。
>
> **考點**：SAP-1.4｜依政策與生命週期設計 OU

### 練習 40-3｜SAP｜選兩項｜不可竄改的集中日誌

Wanderly 準備接受 PCI DSS 稽核。稽核要求：組織內所有帳號（包括未來新增的帳號）的 API 活動都必須記錄，日誌需保存一年，保存期內任何人（包括帳號管理員與 root user）都不能刪除或修改；此外，workload 帳號的管理員不能停止各自帳號的 AWS Config 記錄，也不能刪除 VPC Flow Logs。

哪兩個做法組合起來最能滿足需求？（選兩項）

- A. 建立 CloudTrail organization trail，把日誌送到 Log Archive 帳號中啟用 S3 Object Lock compliance mode、預設保存一年的 bucket
- B. 在每個帳號各自建立 trail，把日誌存到該帳號自己的 S3 bucket，並以 IAM policy 拒絕刪除
- C. 把 CloudTrail 日誌只送到各帳號的 CloudWatch Logs，設定 retention 為一年
- D. 在 Workloads OU 掛上 SCP，拒絕 `config:StopConfigurationRecorder`、`config:DeleteDeliveryChannel`、`ec2:DeleteFlowLogs` 等停用記錄的動作，只放行平台團隊的 role
- E. 在 Log Archive bucket 使用 Object Lock governance mode，讓資安主管必要時可以刪除錯誤日誌

> [!answer]- 答案：A、D
> **A ✓** Organization trail 自動涵蓋所有成員帳號與新加入的帳號，成員帳號無法停止、修改或刪除它。Log Archive 帳號與 workload 帳號分離，Object Lock compliance mode 讓保存期內任何人都無法刪除或覆寫物件。
>
> **B ✗** 日誌存在產生日誌的帳號內，帳號管理員或攻擊者可以修改 IAM policy 後刪除日誌；新帳號也需要另外設定，容易漏。
>
> **C ✗** CloudWatch Logs 的 retention 只決定多久後自動刪除，帳號管理員仍可刪除 log group，也不是集中於獨立帳號。
>
> **D ✓** Organization trail 成員帳號本來就停不掉，但 Config recorder 與 flow logs 是各帳號自己的資源，帳號管理員預設可以停用或刪除。SCP 對成員帳號中的所有身份（包括帳號管理員與 root user）都有效，能從源頭防止這些記錄被關掉。
>
> **E ✗** Governance mode 允許擁有特定權限的身份繞過保存期刪除物件，不符合「任何人都不能刪除」的要求。若法規只要求防止一般使用者誤刪，governance mode 才是合適選擇。
>
> **考點**：SAP-1.2、SAP-1.4｜organization trail、Log Archive 與 Object Lock

### 練習 40-4｜SAP｜單選｜GuardDuty 的 Region 範圍

Wanderly 已在 `ap-northeast-1` 從 management account 把 GuardDuty 的 delegated administrator 指定為 Audit 帳號，並開啟對所有成員帳號的 auto-enable。最近公司在 `ap-southeast-1` 上線了新服務。資安團隊在 Audit 帳號中查看 findings 時，發現完全看不到新加坡帳號的任何資料。

最可能的原因與正確修正是什麼？

- A. GuardDuty 是 Regional 服務；需要在 `ap-southeast-1` 也指定同一個 delegated administrator 並設定 auto-enable
- B. GuardDuty findings 只會送到 management account，需要改由 management account 查看
- C. Auto-enable 只對既有帳號生效，新加坡的帳號需要手動加入 Audit 帳號
- D. 需要在 Audit 帳號中建立一條跨 Region 的 organization trail，GuardDuty 才能讀取新加坡的事件

> [!answer]- 答案：A
> **A ✓** GuardDuty 的 detector、delegated administrator 與 auto-enable 都是以 Region 為單位設定。只在東京設定，新加坡就沒有任何 detector。正確做法是在每個使用中的 Region 指定同一個 delegated admin，並用 Region deny 擋住未使用的 Region。
>
> **B ✗** 委派後 findings 由 delegated administrator 帳號彙整查看，這正是不用 management account 的目的。
>
> **C ✗** Auto-enable 的設計就是讓新加入的帳號自動啟用；問題不在帳號，而在新加坡這個 Region 根本沒有設定。
>
> **D ✗** GuardDuty 直接分析 CloudTrail、VPC Flow Logs 與 DNS 等資料來源，不需要你建立 trail；跨 Region trail 也無法替代每個 Region 的 detector。
>
> **考點**：SAP-1.2、SAP-3.2｜GuardDuty delegated admin 是 Regional

### 練習 40-5｜SAP｜單選｜集中彙整安全 findings

Wanderly 有 45 個帳號，分布在兩個 Region。資安團隊要在單一位置查看所有帳號、兩個 Region 的安全 findings 與 CIS／PCI 等標準的合規檢查結果，並希望用一套設定統一決定每個 OU 要啟用哪些標準。團隊不希望日常登入 management account。

最合適的做法是什麼？

- A. 在每個帳號啟用 Security Hub，由資安團隊透過 Identity Center 逐一登入查看
- B. 在 management account 啟用 Security Hub 並作為管理者帳號，資安團隊獲得 management account 的 ReadOnly 權限
- C. 把 Security Hub 的 delegated administrator 指定為 Audit 帳號，使用 central configuration 設定 home Region 與 linked Region，並以 configuration policy 套用到各 OU
- D. 用 Config aggregator 彙整所有帳號的資源設定，取代 Security Hub 的 findings 彙整

> [!answer]- 答案：C
> **A ✗** 45 個帳號 × 2 個 Region 逐一查看不切實際，也無法統一設定標準。
>
> **B ✗** 能彙整 findings，但違反「不要日常使用 management account」的要求；management account 權限極大且不受 SCP 限制，應盡量減少使用者。
>
> **C ✓** Delegated administrator 讓 Audit 帳號管理全組織的 Security Hub；central configuration 從 home Region 管理所有 linked Region 的設定，並可用 configuration policy 依 OU 決定啟用的標準與 controls，findings 也彙整到 home Region。
>
> **D ✗** Config aggregator 彙整資源設定與 Config rules 的合規狀態，但不彙整 GuardDuty、Inspector 等服務的 findings，也不提供 Security Hub 的標準檢查。兩者常一起使用，而不是互相取代。
>
> **考點**：SAP-1.2、SAP-1.4｜Security Hub delegated admin 與 central configuration

### 練習 40-6｜SAP｜單選｜大量帳號的 GitOps 供應

Wanderly 的平台團隊全面使用 Terraform 管理基礎設施。遷移旅行社系統的計畫預計一年內新增約 120 個帳號。團隊要求帳號申請必須透過 Git pull request 審核、帳號建立後自動套用全組織共用與帳號專屬的 Terraform 設定，且帳號必須受 Control Tower 治理。

最合適的方案是什麼？

- A. 部署 Account Factory for Terraform（AFT），以帳號請求 repository 觸發帳號建立，並以 global 與 account customizations repository 套用設定
- B. 由平台工程師在 Control Tower console 使用 Account Factory 逐一建立帳號，再手動執行 Terraform
- C. 使用 Organizations 的 `CreateAccount` API 寫一支 Terraform 腳本建立帳號，再用 StackSets 部署設定
- D. 使用 Customizations for Control Tower，在 manifest 中列出 120 個帳號並撰寫 CloudFormation template

> [!answer]- 答案：A
> **A ✓** AFT 專為 Terraform 團隊設計：帳號請求本身是 Git 中的 Terraform 檔案，經 PR 審核後由 pipeline 透過 Control Tower Account Factory 建立帳號，接著自動執行 global 與 account-specific customizations，完整符合 GitOps 與治理需求。
>
> **B ✗** 120 個帳號逐一手動建立再手動執行 Terraform，營運負擔高、沒有 PR 審核，也容易漏掉步驟。
>
> **C ✗** 直接呼叫 Organizations API 建立的帳號不會自動受 Control Tower 治理，還要另外 enroll；整套流程都要自行開發與維護。
>
> **D ✗** CfCT 以 CloudFormation 與 manifest 為核心，主要負責在帳號建立後部署資源，並不負責以 Git 請求建立帳號；對 Terraform 團隊也不是自然的選擇。
>
> **考點**：SAP-1.4、SAP-3.1｜Account Factory for Terraform

### 練習 40-7｜SAP｜單選｜既有 Organization 導入 Control Tower

旅行社在併購前已有一個 AWS Organization，裡面有 40 個帳號、自訂的 OU 與 SCP，部分帳號已經自行設定 AWS Config。Wanderly 決定讓這個 Organization 改由 Control Tower 治理，要求不能中斷既有 workload，並把遷移風險降到最低。

最合適的做法是什麼？

- A. 建立一個新的 Organization 並啟用 Control Tower，再把 40 個帳號逐一退出舊 Organization、邀請加入新 Organization
- B. 在既有 Organization 啟用 Control Tower 後，一次 register 所有 OU，讓 Control Tower 覆寫所有帳號的 Config 設定
- C. 刪除所有既有 SCP 與 Config 設定，避免與 Control Tower 衝突，再建立 landing zone
- D. 在既有 Organization 的 management account 建立 landing zone，先處理一個非關鍵帳號的 Config recorder 衝突並試做 enroll，驗證後再逐批 register OU

> [!answer]- 答案：D
> **A ✗** Control Tower 可以在既有 Organization 中建立 landing zone。重建 Organization 要處理帳單、RI 與 Savings Plans 共享、邀請流程等大量工作，風險反而更高。
>
> **B ✗** 一次納管所有 OU 會讓尚未處理的 Config recorder 衝突同時爆發，也缺乏驗證階段，不符合「風險最低」。
>
> **C ✗** 先刪除所有 SCP 與 Config 會讓環境在過渡期間完全失去防護與記錄，違反合規要求。
>
> **D ✓** 在既有 Organization 建立 landing zone，再以 enroll account 和 register OU 逐步納管。先在非關鍵帳號處理既有 Config recorder 與 delivery channel 的衝突，驗證 baseline 不影響 workload 後再擴大，是風險最低的路徑。
>
> **考點**：SAP-2.1、SAP-3.1｜既有 Organization 的 Control Tower 納管

### 練習 40-8｜SAP｜單選｜安全推出新的 SCP

資安團隊寫了一條新的 SCP，拒絕在兩個核准 Region 以外建立資源，準備套用到 Workloads OU（包含 Prod 與 NonProd）。上次另一條 SCP 直接套用到 Prod 後，因為漏排除 IAM 與 CloudFront 等 global 服務，造成部署 pipeline 中斷兩小時。團隊希望這次降低風險。

最合適的推出方式是什麼？

- A. 先把 SCP 掛在 Root，因為 management account 不受影響，可以觀察成員帳號的反應
- B. 建立 Policy Staging OU 並放入設定與 production 相似的測試帳號，先在該 OU 套用 SCP 並執行實際 pipeline，分析 CloudTrail 中的 AccessDenied 事件後，依序擴大到 NonProd 與 Prod
- C. 把 SCP 改成只拒絕 `ec2:RunInstances`，降低影響範圍
- D. 在 IAM policy simulator 中模擬 SCP 後，直接套用到 Workloads OU

> [!answer]- 答案：B
> **A ✗** 掛在 Root 會立即影響所有成員帳號，包括 production，是影響最大的選擇。
>
> **B ✓** 治理政策也要分階段推出。Policy Staging OU 讓新 SCP 先在不影響正式 workload 的環境中接受真實 pipeline 與營運腳本的考驗，從 CloudTrail 的 AccessDenied 找出誤擋，再逐步擴大範圍。
>
> **C ✗** 縮減 SCP 範圍會讓它無法達成「限制 Region」的目的，資源仍可透過其他 API 在未核准 Region 建立。
>
> **D ✗** 模擬工具能協助檢查個別動作，但無法涵蓋 pipeline 與服務實際呼叫的所有 API 與 Region 組合；直接套用到含 Prod 的 OU 仍有很大風險。
>
> **考點**：SAP-1.2、SAP-2.1｜Policy Staging OU 與分階段推出

### 練習 40-9｜SAP｜選兩項｜IdP 故障時的緊急存取

Wanderly 所有人員都透過 IAM Identity Center 搭配外部 IdP 登入 AWS，組織已用 SCP 禁止建立 IAM user。上週 IdP 的 SCIM 同步錯誤刪除了所有群組，工程師兩小時內無法進入任何帳號，正好遇上 production 事故。公司要建立緊急存取機制，並確保它不會被濫用。

哪兩個做法最合適？（選兩項）

- A. 在專用帳號建立少數 break-glass IAM user，使用硬體 MFA、密碼分持保管；各帳號的 break-glass role 只信任這些 user，並在 SCP 的 IAM user 禁令中排除它們
- B. 在 Identity Center 中建立一個 break-glass permission set，指派給值班工程師群組
- C. 以 EventBridge 監聽 break-glass user 的 ConsoleLogin 與 AssumeRole 事件並即時通知資安團隊，且每季演練一次並在演練後輪替憑證
- D. 把 management account 的 root 密碼存在團隊 wiki，讓值班人員在緊急時使用
- E. 在每個 workload 帳號為值班工程師建立長期 access key，存在他們的筆電中

> [!answer]- 答案：A、C
> **A ✓** Break-glass 路徑必須獨立於它要備援的 IdP 與 Identity Center。少數 IAM user 搭配硬體 MFA、分持保管與只能 assume 指定 role 的設計，提供可用但受控的緊急存取。
>
> **B ✗** 這個 permission set 仍然依賴 IdP 與 Identity Center 登入；本次事故中群組被刪除，它一樣無法使用。
>
> **C ✓** 緊急存取必須「使用即被發現」並定期驗證可用性。即時告警防止濫用，定期演練確保真正需要時密碼、MFA 與權限都有效。
>
> **D ✗** 存放在 wiki 的 root 密碼任何能看 wiki 的人都能用，無法控管、無法即時發現，也違反 root 保護原則。
>
> **E ✗** 長期 access key 存在個人筆電是高風險憑證，違反組織禁止 IAM user 的政策，也與 break-glass 的「平常不用」本質相反。
>
> **考點**：SAP-1.2、SAP-2.3｜break-glass 存取設計

### 練習 40-10｜SAP｜單選｜成員帳號的 root 管理

Wanderly 的組織有 80 個成員帳號，每個帳號都有 root user 密碼與 MFA 需要保管。稽核發現其中 5 個帳號的 root MFA 裝置下落不明。另外，某個帳號的 S3 bucket policy 被錯誤設定為拒絕所有 principal，連帳號管理員都無法修改。公司希望大幅減少需要保管的 root 憑證，並仍能處理這類只有 root 能做的修復。

最合適的做法是什麼？

- A. 為 80 個帳號重新設定 root 密碼與新的硬體 MFA，集中存放在保險箱
- B. 刪除所有成員帳號，改用 IAM Identity Center 的 permission set 取代 root
- C. 在 IAM 啟用 Organizations 的 centralized root access，移除成員帳號的 root 憑證；需要修復 bucket policy 時，由 management account 或委派帳號以 `sts:AssumeRoot` 取得限定該任務的短期 root session
- D. 用 SCP 允許成員帳號的 root user 只能修改 S3 bucket policy

> [!answer]- 答案：C
> **A ✗** 能補救 MFA 遺失，但仍要長期保管 80 組 root 憑證，問題沒有減少。
>
> **B ✗** 刪除帳號會摧毀其中的 workload，permission set 也無法執行只有 root 能做的動作（例如刪除鎖住所有人的 bucket policy）。
>
> **C ✓** Centralized root access 讓中央帳號移除成員帳號的 root 憑證，新帳號也預設不建立 root 憑證；需要 root 才能執行的少數任務（如刪除錯誤的 S3 或 SQS 資源政策）可透過 `sts:AssumeRoot` 取得限定範圍的短期 session，並留下 CloudTrail 紀錄。
>
> **D ✗** SCP 只能限制、不能授予權限；而且問題在於 root 憑證的保管，不在 root 能做什麼。
>
> **考點**：SAP-1.2、SAP-3.2｜centralized root access 與 `sts:AssumeRoot`

### 練習 40-11｜SAP｜單選｜集中部署 pipeline 的跨帳號授權

Wanderly 的 CI/CD pipeline 位於 Deployments OU 的 `cicd` 帳號，需要部署到 30 個 workload 帳號。目前做法是在 `cicd` 帳號存放每個 workload 帳號的 IAM user access key。資安團隊要求移除所有長期憑證，讓「能部署到 production 的身份」集中且可稽核，並防止組織外的帳號冒用。

最合適的做法是什麼？

- A. 在每個 workload 帳號建立 `deploy` role，trust policy 只信任 `cicd` 帳號中的 pipeline role 並加上 `aws:PrincipalOrgID` 條件，pipeline 以 AssumeRole 取得短期憑證部署
- B. 在 `cicd` 帳號建立一個擁有 AdministratorAccess 的 IAM user，所有帳號都信任這個 user
- C. 讓 pipeline 使用每個帳號的 `OrganizationAccountAccessRole` 部署，因為它已經存在
- D. 把 access key 移到 Secrets Manager 並啟用自動輪替，pipeline 執行時取用

> [!answer]- 答案：A
> **A ✓** AssumeRole 只發出短期憑證；trust policy 精確指定 pipeline role，加上組織條件防止外部冒用。所有部署都經由少數 pipeline role，CloudTrail 能清楚稽核誰在何時部署到哪個帳號。
>
> **B ✗** 仍使用長期憑證，而且一個 user 擁有所有帳號的管理權，外洩時爆炸半徑涵蓋整個組織。
>
> **C ✗** `OrganizationAccountAccessRole` 只信任 management account 且擁有 AdministratorAccess，讓 pipeline 從 management account 執行等於擴大最敏感帳號的使用範圍，也違反最小權限。
>
> **D ✗** Secrets Manager 可以讓長期憑證的保管與輪替更安全，在必須使用長期 key 的第三方整合中是合理做法；但需求是「移除長期憑證」，跨帳號部署應改用 role。
>
> **考點**：SAP-1.4、SAP-2.3｜集中部署 role 與跨帳號 trust

### 練習 40-12｜SAP｜單選｜防止組織外部存取資源

Wanderly 有數百個 S3 bucket 分布在 60 個帳號。資安團隊擔心開發人員撰寫錯誤的 bucket policy（例如 `"Principal": "*"`），讓組織外的 AWS 帳號讀到資料。他們要一個集中、無法被各帳號管理員繞過的控制，同時不能影響 CloudTrail 與 Config 寫入日誌 bucket。

最合適的做法是什麼？

- A. 在所有帳號掛上 SCP，拒絕 `s3:PutBucketPolicy`
- B. 使用 IAM Access Analyzer 以 organization 作為 zone of trust，每週檢討 findings 並手動修正
- C. 在每個 bucket policy 中加入拒絕組織外 principal 的敘述，並由各團隊自行維護
- D. 在 Root 掛上 RCP，對 `s3:*` 拒絕 `aws:PrincipalOrgID` 不等於本組織的 principal，並以 `aws:PrincipalIsAWSService` 條件排除 AWS 服務主體

> [!answer]- 答案：D
> **A ✗** 完全禁止修改 bucket policy 會讓所有團隊無法設定合法的跨帳號存取，而且 SCP 限制的是組織內的身份，無法限制「誰可以存取我的資源」。
>
> **B ✗** Access Analyzer 能找出被外部存取的資源，是很好的偵測工具，但它是事後發現，不能在資料外洩前阻擋。
>
> **C ✗** 各團隊自行維護會有遺漏，帳號管理員也可以移除這條敘述。
>
> **D ✓** RCP 作用在資源上，與 resource policy 取交集；即使 bucket policy 允許 `*`，組織外的 principal 仍被 RCP 拒絕，各帳號管理員無法移除它。排除 AWS 服務主體可讓 CloudTrail、Config 等服務繼續寫入日誌 bucket。
>
> **考點**：SAP-1.2、SAP-3.2｜RCP 與 data perimeter

### 練習 40-13｜SAA｜單選｜強制建立資源時帶 tag

Wanderly 的財務要求所有新啟動的 EC2 instance 都必須帶有 `cost-center` tag，沒有這個 tag 的啟動請求應該直接失敗。平台團隊已經建立 tag policy，規定 `cost-center` 的值只能是核准的成本中心代碼並開啟 enforcement，但仍然發現有人啟動了完全沒有 tag 的 instance。

應如何補強？

- A. 在 tag policy 中把 enforcement 擴大到所有資源類型
- B. 在 Workloads OU 掛上 SCP，對 `ec2:RunInstances` 的 instance 資源，在 `aws:RequestTag/cost-center` 為 Null 時拒絕
- C. 啟用 Config rule `required-tags`，偵測沒有 tag 的 instance
- D. 在 management account 啟用 `cost-center` 為 cost allocation tag

> [!answer]- 答案：B
> **A ✗** Tag policy 的 enforcement 只阻止「寫入不合規的 tag 值」，不會阻止建立完全沒有 tag 的資源，擴大資源類型也一樣。即使改用 tag policy 的 required tags 功能，也只有在 IaC 工具部署時才會檢查，從 console 或 CLI 直接啟動仍不會失敗。
>
> **B ✓** SCP 在 API 呼叫時檢查 request 中是否帶有 tag；`Null` 條件為 true 代表沒有帶 `cost-center`，就拒絕啟動。只針對 instance 資源，避免誤擋 subnet、security group 等不會帶新 tag 的資源。搭配既有 tag policy，可以同時確保「一定要有」與「值要合規」。
>
> **C ✗** Config rule 是事後偵測，資源已經建立，不符合「啟動請求直接失敗」。它適合作為補充的持續監控。
>
> **D ✗** Cost allocation tag 只決定帳單報表能否依 tag 分攤，與能不能建立資源無關。
>
> **考點**：SAA-1.1｜SCP `aws:RequestTag` 與 tag policy 的差異

### 練習 40-14｜SAP｜單選｜全組織的設定合規視圖

稽核要求 Wanderly 提供一個視圖，顯示 60 個帳號、兩個 Region 中所有 EBS volume 是否加密、security group 是否對 `0.0.0.0/0` 開放 SSH，以及每項資源的設定變更歷史。資安團隊不希望為此登入 management account，也不想在每個帳號逐一查詢。

最合適的做法是什麼？

- A. 在 Log Archive 帳號用 Athena 查詢 CloudTrail 日誌，推算每個資源目前的設定
- B. 在每個帳號啟用 Trusted Advisor，並把報告寄給資安團隊
- C. 把 Audit 帳號註冊為 AWS Config 的 delegated administrator，建立 organization aggregator，並部署 organization Config rules 檢查加密與 security group 設定
- D. 在 management account 建立 Config aggregator，並給資安團隊 management account 的 ReadOnly 權限

> [!answer]- 答案：C
> **A ✗** CloudTrail 記錄的是 API 呼叫，從事件推算資源的最終設定既困難又容易出錯；Config 本身就記錄設定與變更歷史。
>
> **B ✗** Trusted Advisor 提供部分最佳實務檢查，但不提供每個資源的設定變更歷史，也不是集中的組織視圖。
>
> **C ✓** Config 的 delegated administrator 可在 Audit 帳號建立 organization aggregator，彙整所有帳號與 Region 的設定與合規狀態；organization Config rules 則一次部署到所有成員帳號。
>
> **D ✗** 功能上可行，但需要資安團隊日常使用 management account，違反最小化 management account 使用的原則。
>
> **考點**：SAP-1.2、SAP-3.1｜Config delegated admin 與 organization aggregator

### 練習 40-15｜SAP｜選兩項｜新帳號 baseline 自動化

Wanderly 透過 Control Tower Account Factory 建立帳號。每個新帳號都必須立即具備：標準的 `security-audit` 與 `deploy` IAM role、帳號層級 S3 Block Public Access，以及由網路帳號從 IPAM 配置 CIDR 並接上 Transit Gateway 的 VPC。目前這些步驟由工程師照 runbook 手動完成，常有遺漏。團隊希望完全自動化，並避免以排程輪詢偵測新帳號。

哪兩個做法組合起來最合適？（選兩項）

- A. 使用 CloudFormation StackSets 的 service-managed 權限並啟用 automatic deployment，目標設為相關 OU，部署 IAM role 與帳號安全設定
- B. 每小時執行一個 Lambda 呼叫 Organizations `ListAccounts`，比對新帳號後執行設定
- C. 以 Control Tower 的 `CreateManagedAccount` lifecycle event 透過 EventBridge 觸發 Step Functions，呼叫網路帳號完成 IPAM 配置、建立 VPC 與 TGW attachment
- D. 為每個新帳號建立一個包含所有設定的 golden AMI
- E. 要求應用團隊在收到帳號後自行執行 baseline Terraform

> [!answer]- 答案：A、C
> **A ✓** Service-managed StackSets 的 automatic deployment 會在帳號加入目標 OU 時自動部署 stack，適合「每個帳號都要有」的 IAM role 與帳號層級設定，不需撰寫任何偵測邏輯。
>
> **B ✗** 輪詢可以運作，但有延遲、需要自行維護狀態，也違反「避免排程輪詢」的要求。
>
> **C ✓** Lifecycle event 在帳號建立完成時立即觸發，Step Functions 適合編排跨帳號、多步驟的網路配置流程。
>
> **D ✗** AMI 是 EC2 的映像檔，無法建立 IAM role、帳號設定或 VPC。
>
> **E ✗** 把 baseline 交給應用團隊執行，正是目前遺漏的根源；帳號交付前就必須完成。
>
> **考點**：SAP-1.4、SAP-3.1｜StackSets automatic deployment 與 lifecycle event

### 練習 40-16｜SAA｜單選｜Management account 的用途

Wanderly 的一位工程師提議把新的報表服務部署在 Organization 的 management account，理由是「那裡權限最大，設定最方便」。資安團隊反對。

下列哪一項是反對的最主要理由？

- A. Management account 無法建立 EC2 與 RDS 等資源
- B. Management account 的費用不會出現在 consolidated billing 中
- C. Management account 只能存在於 `us-east-1`
- D. SCP 不會限制 management account，部署在其中的 workload 不受組織防護，且該帳號被入侵時可能影響整個 Organization

> [!answer]- 答案：D
> **A ✗** Management account 技術上可以建立任何資源，問題不在能不能，而在應不應該。
>
> **B ✗** Management account 本身的費用也包含在 consolidated billing 中。
>
> **C ✗** AWS 帳號不屬於任何 Region；management account 可以在任何 Region 建立資源。
>
> **D ✓** SCP 對 management account 無效，你為 Prod 設計的限制在這裡都不適用；management account 又能管理整個 Organization，任何 workload 弱點都可能成為控制全組織的入口。因此它應只用於組織管理與帳單。
>
> **考點**：SAA-1.1｜management account 最小化使用
