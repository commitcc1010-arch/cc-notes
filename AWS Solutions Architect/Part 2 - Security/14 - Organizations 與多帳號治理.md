---
chapter: 14
title: Organizations、SCP 與 Control Tower
part: 2
---

# 第 14 章　Organizations、SCP 與 Control Tower：多帳號治理

> [!abstract] 本章地圖
> **你會學到**：
> - 說明為什麼「帳號」是 AWS 上最強的隔離邊界，並為一家公司規劃 OU 結構
> - 正確推論 SCP 的效果：它只設上限、不授權，不影響 management account，卻能限制成員帳號的 root user
> - 寫出可以實際使用的 SCP 與 RCP（限制 Region、保護稽核設定、建立資料邊界），並知道怎麼安全上線
> - 分辨 SCP、RCP、permission boundary、tag policy、Control Tower controls 各自管什麼
> - 用 Control Tower 建立 landing zone，並用 Account Factory 自動開出符合規範的新帳號
> - 用 permission boundary 讓開發者自己建立 IAM role，又不會藉此提升權限
>
> **前置知識**：第 12 章（IAM policy 結構與評估邏輯）、第 13 章（AssumeRole 與 IAM Identity Center）
> **考試比重**：SAA ★★☆（Domain 1 安全存取）｜SAP ★★★（Domain 1 組織複雜度、Domain 3 改善既有架構）

## 14.1 故事：一個帳號裝不下 Wanderly

Wanderly 從第一台 EC2 開始，所有東西都放在同一個 AWS 帳號裡：production 的訂房網站、staging 環境、工程師自己試東西的 sandbox、資料團隊的分析叢集。帳號只有一個，大家用 IAM role 區分權限，看起來也算井然有序。

第一次出事是在一個週五晚上。效能測試團隊對 staging 的 Lambda 做壓力測試，把整個帳號在這個 Region 的 Lambda **concurrency（同時執行數）配額**吃光，production 的付款 Lambda 開始被 throttle（節流，請求被拒絕）。staging 和 production 明明是不同系統，卻因為住在同一個帳號，共用同一份配額而互相拖累。

第二次是帳單。財務長想知道「資料團隊每個月花多少錢」，結果發現很多資源沒有貼 tag，只能估算。第三次是稽核：Wanderly 開始接受信用卡付款，PCI DSS（支付卡產業資料安全標準）稽核員問：「哪些系統屬於持卡人資料環境？」答案是「整個帳號」，因為帳號內任何有足夠權限的人都可能碰到付款資料。稽核範圍一下子變成整間公司。

技術主管決定改成多帳號架構，並交代三個目標：

1. 每個環境、每個重要 workload 有自己的帳號，故障、配額與帳單互不影響。
2. 有一套「誰都不能違反」的規則：例如只能用東京與新加坡 Region、任何人都不能關掉 CloudTrail。
3. 新帳號要能在一小時內開好，而且一開出來就自動符合上述規則，不靠人工檢查。

這一章就跟著 Wanderly 的平台團隊，從 AWS Organizations 的結構開始，一路談到 SCP、RCP、Control Tower 與 permission boundary。每一種機制我們都會問：它管的是「誰」、管的是「哪一層」、它能不能授權？

## 14.2 為什麼要多帳號：帳號是最強的隔離邊界

在第 12 章，我們用 IAM policy 控制「某個 principal（身份）能不能對某個資源做某個動作」。IAM 很細緻，但它有個根本限制：**同一個帳號裡，總有人擁有管理整個帳號的權限**。只要那個人的憑證外洩、或是一條寫錯的 policy 給了 `*`，帳號裡所有資源都暴露在同一個風險下。

**AWS 帳號（account）** 是資源、身份、配額與帳單的容器。不同帳號之間預設完全隔離：帳號 A 的 IAM role 無法存取帳號 B 的任何資源，除非帳號 B 明確授權（第 13 章的跨帳號存取）。這種「預設不互通」的特性，讓帳號成為 AWS 上最清楚、最難被意外打破的邊界。

把不同 workload 放在不同帳號，可以得到這些具體好處：

- **安全隔離與爆炸半徑（blast radius）**：一個帳號被入侵，攻擊者拿到的只是那個帳號的資源。
- **配額隔離**：大多數 service quota 是「每個帳號、每個 Region」計算，staging 壓測不會再吃掉 production 的 Lambda concurrency。
- **帳單清楚**：每個帳號的費用天生分開，不靠 tag 也能知道誰花了多少。
- **合規範圍縮小**：PCI 稽核只需涵蓋處理付款的那幾個帳號。
- **權限模型簡單**：dev 帳號可以給工程師較大的權限，production 帳號則嚴格控管，不用在同一個帳號裡寫複雜的條件。

| 隔離手段 | 能隔離什麼 | 不能隔離什麼 |
|---|---|---|
| 不同帳號 | IAM、資源、配額、帳單、root user | 需要跨帳號存取時要另外設計 |
| 同帳號不同 VPC | 網路流量 | IAM 權限、配額、帳單 |
| 同帳號 IAM 條件 | 特定 principal 對特定資源的動作 | 帳號管理員、配額、寫錯 policy 的風險 |
| Tag | 分類與成本歸屬（需搭配 policy 才有控制力） | 本身不提供任何隔離 |

> [!warning] 常見誤解
> 「用不同 VPC 就等於隔離了。」VPC 只隔離網路流量。同一個帳號裡的 IAM 管理員依然能刪除任何 VPC 裡的資源，所有 VPC 也共用同一份 API 配額。題目若要求「隔離權限、配額或帳單」，答案是多帳號，不是多 VPC。

帳號多了之後，新的問題立刻出現：二十個帳號要怎麼統一付款？怎麼確保每個帳號都開著 CloudTrail？怎麼防止某個帳號的管理員去用沒有核准的 Region？這就是 AWS Organizations 要解決的事。

## 14.3 AWS Organizations：把帳號組成一棵樹

**AWS Organizations** 是把多個 AWS 帳號集中管理的服務。它本身免費，提供三大能力：統一帳單、帳號的階層式分組、以及組織層級的政策。

### 組成元素

- **Management account（管理帳號）**：建立 organization 的那個帳號，負責付款、建立與邀請帳號、管理政策。帳單相關文件中也稱為 payer account（付款帳號）。每個 organization 只有一個，而且不能更換成別的帳號（要換只能重建 organization）。
- **Member account（成員帳號）**：organization 裡其他所有帳號。一個帳號同一時間只能屬於一個 organization。
- **Root**：整棵樹的最頂層容器。附加在 root 的政策會影響整個 organization 的所有成員帳號。這裡的 root 和帳號的 root user 是兩回事，只是名字相同。
- **OU（Organizational Unit，組織單位）**：帳號的分組資料夾。OU 可以巢狀，root 之下最多 5 層。每個帳號或 OU 只能有一個 parent。

政策可以附加在 root、OU 或單一帳號上，並且**往下繼承**。所以 OU 的設計原則不是照公司組織圖，而是照「哪些帳號需要相同的規則」。

### Wanderly 的 organization

```text
Root  ← ① 附加：DenyLeaveOrg、ProtectAuditBaseline
 │
 ├─ OU: Security ← ② 只有資安團隊能登入
 │    ├─ log-archive        （集中保存 CloudTrail、Config 日誌）
 │    └─ security-tooling   （GuardDuty、Security Hub 的 delegated admin）
 │
 ├─ OU: Infrastructure
 │    ├─ network            （Transit Gateway、DNS、集中 egress）
 │    └─ shared-services    （CI/CD、golden AMI）
 │
 ├─ OU: Workloads ← ③ 附加：RestrictRegions（東京、新加坡）
 │    ├─ OU: Prod  ← ④ 附加：DenyDeleteProdBackups
 │    │    ├─ booking-prod
 │    │    └─ payments-prod   （PCI 範圍只到這裡）
 │    └─ OU: NonProd
 │         ├─ booking-staging
 │         └─ booking-dev
 │
 ├─ OU: Sandbox ← ⑤ 附加：預算上限、禁止建立大型 instance
 │    └─ sandbox-alice、sandbox-bob
 │
 └─ OU: Suspended ← ⑥ 附加：DenyAll（待關閉的帳號）

Management account：只負責帳單與 organization 管理，不跑任何 workload
```

① 附加在 root 的政策影響所有成員帳號，適合放「全公司都不能違反」的規則。② Security OU 把日誌與資安工具集中在少數帳號，一般工程師無法登入。③ Region 限制放在 Workloads OU，Prod 與 NonProd 都會繼承。④ Prod OU 再加更嚴格的規則，`payments-prod` 同時受到 ①③④ 的限制。⑤ Sandbox 給工程師自由實驗，但用政策限制成本風險。⑥ 要關閉或調查中的帳號先移到 Suspended OU，一個 deny-all 政策就讓帳號裡的人什麼都做不了。

### 兩種功能模式

Organization 有兩種 feature set：

| 模式 | 提供什麼 |
|---|---|
| Consolidated billing only | 只有統一帳單 |
| All features（預設、建議） | 統一帳單 + SCP、RCP、tag policy 等政策 + 與其他 AWS 服務整合 |

只開 consolidated billing 的 organization 可以升級成 all features；升級時每個被邀請加入的成員帳號都要同意。考題若要求使用 SCP，前提就是 organization 啟用了 all features。

### 建立帳號 vs 邀請帳號

把帳號放進 organization 有兩種方式，差別在考試很常出現：

- **由 organization 建立新帳號**：Organizations 會在新帳號裡自動建立一個名為 **`OrganizationAccountAccessRole`** 的 IAM role，信任 management account，並附有管理員權限。management account 的管理員可以直接 AssumeRole 進去管理。
- **邀請既有帳號加入**：既有帳號接受邀請後成為成員，但**不會自動建立這個 role**。若 management account 需要管理權限，必須在成員帳號裡手動建立一個信任 management account 的 role。

帳號也可以離開 organization，但它必須先具備獨立帳號所需的資訊（付款方式、聯絡資訊等）。要把帳號從一個 organization 搬到另一個 organization 時，自 2025 年 11 月起 Organizations 支援 **direct account transfer（直接移轉）**：由新 organization 的 management account 發出邀請、帳號接受後就直接移過去，不必先離開原 organization、當一段時間的獨立帳號（舊的「先離開再接受邀請」流程仍可使用）。在 Wanderly 這種要統一治理的環境，平台團隊會用 SCP 禁止成員帳號自己呼叫 `organizations:LeaveOrganization`。

### Management account 要盡量空

**SCP 不會限制 management account 裡的任何身份**（14.5 節會詳細說明）。這代表 management account 是整個 organization 裡權限最大、又最不受 guardrail（護欄）約束的地方。最佳做法：

- 不在 management account 跑任何 workload，只用它做帳單與 organization 管理。
- 嚴格保護它的 root user（MFA、不建立 access key），只讓極少數人能登入。
- 把 GuardDuty、Security Hub、IAM Identity Center 等服務的日常管理交給 delegated administrator 帳號（14.10 節）。

> [!tip] 考試提示
> 選項中出現「把 production workload 放在 management account 方便集中管理」，幾乎一定是錯的。題目問「哪個帳號不受 SCP 影響」，答案是 management account。

## 14.4 Consolidated billing：統一付款與共享折扣

組織建好之後，最先感受到的好處是帳單。**Consolidated billing（合併帳單）** 讓 management account 支付所有成員帳號的費用，同時保留每個帳號各自的費用明細。這項功能不另外收費。

合併帳單有幾個實際效果：

- **用量合併計算階梯價**：S3、資料傳輸等服務用量越大單價越低，organization 會把所有帳號的用量加總，一起享受較低的價格階梯。
- **Reserved Instances 與 Savings Plans 共享**：一個帳號買的 RI 或 Savings Plans，如果自己沒用完，會自動套用到 organization 裡其他帳號符合條件的用量。這個共享可以由 management account 對個別帳號關閉，例如某個子公司要求自己買的折扣只給自己用（第 39、43 章）。
- **單一付款與發票**：財務只需要處理一張帳單。

合併帳單只是「誰付錢」與「怎麼算折扣」，它**和權限完全無關**。題目若說「開啟 consolidated billing 後，管理帳號就能存取成員帳號的 S3」，那是錯的；跨帳號存取一樣要靠 IAM role 與 resource policy。

帳單解決了，接下來是更重要的問題：怎麼讓二十個帳號都遵守同一套規則？

## 14.5 SCP：組織層的權限上限

### 為什麼 IAM 不夠

假設 Wanderly 規定「任何人都不能停用 CloudTrail」。在單一帳號裡，你可以在每個 IAM policy 加上 deny；但每個成員帳號都有自己的管理員，他們可以修改自己帳號的 IAM policy，甚至用帳號的 root user 登入。只靠成員帳號自己的 IAM，無法做出「帳號管理員也不能違反」的規則。

**SCP（Service Control Policy，服務控制政策）** 就是為這件事設計的：它從 organization 的層級，為成員帳號設定**權限的最大範圍**。即使成員帳號的管理員擁有 `AdministratorAccess`，只要 SCP 不允許，那個動作就會被拒絕。

### SCP 怎麼參與評估

第 12 章介紹過，一個 API 請求要成功，必須在所有適用的政策層都被允許，而且沒有任何一層明確拒絕。SCP 是其中一層：

```text
成員帳號裡的 role 發出請求：cloudtrail:StopLogging
          │
          ▼
 ① 任何一層有明確 Deny？ ──── 是 ──► 拒絕（explicit deny 永遠優先）
          │ 否
          ▼
 ② SCP：從 root → 各層 OU → 帳號，每一層都允許這個動作？
          │ 否 ──► 拒絕（被 SCP 擋住）
          │ 是
          ▼
 ③ RCP（若資源支援）：每一層都允許？
          │ 否 ──► 拒絕
          │ 是
          ▼
 ④ IAM identity policy 或 resource policy 有 Allow？
          │ 否 ──► 拒絕（隱含拒絕，implicit deny）
          │ 是
          ▼
 ⑤ Permission boundary、session policy（若有）也允許？
          │ 否 ──► 拒絕
          │ 是
          ▼
        允許
```

① 任何一層的明確 Deny 都會直接拒絕，不論其他層怎麼寫。② SCP 必須「每一層」都允許：root、請求者所在帳號的每一層祖先 OU、帳號本身。③ RCP 是資源端的上限（14.8 節）。④ 這是最容易被忽略的一點：**SCP 本身不授予任何權限**。就算 SCP 允許 `s3:*`，如果 role 自己沒有任何 S3 的 Allow，請求仍然被拒絕。⑤ 其他上限機制也要放行。這個圖是簡化版，完整的評估邏輯在第 12 章。

最終的有效權限，可以想成多個集合的**交集**：

> 有效權限 = SCP 允許的範圍 ∩（RCP 允許的範圍）∩ IAM 授予的權限 ∩（permission boundary）∩（session policy）

### SCP 一定要記住的規則

| 規則 | 說明 |
|---|---|
| 不授權 | 只限制最大範圍；實際權限仍要靠 IAM 或 resource policy 授予 |
| 不影響 management account | management account 裡的所有身份（包括它的 root user）都不受 SCP 限制，即使 SCP 附加在 root |
| 會影響成員帳號的 root user | 這是 SCP 和 IAM 最大的差別：成員帳號的 root user 也受 SCP 限制 |
| 不影響 service-linked role | AWS 服務代替你運作的 service-linked role 不受 SCP 限制，以免 SCP 弄壞服務本身 |
| 只限制成員帳號裡的 principal | 組織外的帳號透過 resource policy 存取你的資源時，SCP 管不到（這是 RCP 的用途） |
| 繼承且需層層允許 | Allow 必須在每一層都存在；Deny 出現在任何一層就對下層全部生效 |

SCP 有幾個硬性限制要知道：每個 root、OU 或帳號最多附加 5 個 SCP，單一 SCP 文件大小上限為 5,120 個字元。這兩個數字讓你不能無限堆疊政策，需要把相關規則整合在同一份 SCP 裡。

> [!warning] 常見誤解
> 「SCP 附加在 root，就能限制所有帳號。」除了 management account 之外是對的。所以題目若說「要限制 management account 的管理員」，SCP 不是答案；正確方向是把 workload 移出 management account，並嚴格管理能登入它的人。

### 預設的 FullAWSAccess

啟用 SCP 時，AWS 會把一個名為 **`FullAWSAccess`** 的 AWS 受管 SCP 附加到 root、每個 OU 和每個帳號。它的內容就是「允許所有動作」：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
```

因為 SCP 要「每一層都允許」，如果有人把某個 OU 上的 `FullAWSAccess` 拿掉、又沒有附加其他 Allow 型 SCP，這個 OU 下的所有帳號會立刻失去所有權限（service-linked role 例外）。這是 SCP 最常見的事故來源之一，也引出下一節的兩種策略。

## 14.6 Deny list 與 allow list：兩種 SCP 策略

### Deny list（拒絕清單）策略

保留每一層的 `FullAWSAccess`，再額外附加 Deny 型 SCP，列出「不准做的事」。

- 優點：新推出的 AWS 服務預設可以使用，維護量低；每條 Deny 意圖清楚。
- 缺點：沒有被列出來的危險動作就會被允許。
- 這是 AWS 建議的預設做法，也是大多數企業採用的方式。

### Allow list（允許清單）策略

把 `FullAWSAccess` 移除，改附加只列出「允許服務」的 Allow 型 SCP。

- 優點：只有明確核准的服務能用，適合高度受管制的環境，例如只允許十幾個經過資安審查的服務。
- 缺點：每次要用新服務都得修改 SCP；而且 Allow 必須在路徑上**每一層**都存在，任何一層漏掉都會被拒絕，推論複雜。

舉例來說，Wanderly 的 `payments-prod` 帳號位於 Root → Workloads → Prod。若採 allow list 只允許 EC2、RDS、S3，那麼 Root、Workloads、Prod、帳號本身四層附加的 SCP 都必須允許這三個服務；只要 Workloads OU 的 SCP 沒有列 RDS，這個帳號就不能用 RDS，即使 Prod OU 的 SCP 允許。

| 比較 | Deny list | Allow list |
|---|---|---|
| `FullAWSAccess` | 保留 | 移除 |
| 預設行為 | 沒禁止的都可以 | 沒允許的都不行 |
| 新服務 | 自動可用 | 要更新 SCP 才能用 |
| 維護成本 | 低 | 高 |
| 適用 | 大多數組織 | 極高度管制、服務清單固定 |

> [!tip] 考試提示
> 題目說「某帳號的管理員有 AdministratorAccess，卻無法使用某服務」，先檢查路徑上每一層 SCP 是否允許、有沒有任何一層明確 Deny。題目說「要禁止一小組動作且營運負擔最低」，答案是 deny list。

## 14.7 常用 SCP 範例與安全上線

這一節是 Wanderly 實際使用的 SCP。每一份都是合法的 JSON，可以直接在 Organizations 建立。

### 範例一：只允許核准的 Region

Wanderly 的資料主權要求所有 workload 只能在東京與新加坡。直覺的寫法是「Region 不在清單內就 Deny 全部」，但這會弄壞**全球服務**：IAM、Organizations、Route 53、CloudFront、Support 等服務的 API 端點在 `us-east-1`，請求會被當成 `us-east-1` 的請求而被擋掉。所以要用 `NotAction` 把這些全球服務排除在外：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyOutsideApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*",
        "organizations:*",
        "account:*",
        "sts:*",
        "route53:*",
        "route53domains:*",
        "cloudfront:*",
        "globalaccelerator:*",
        "waf:*",
        "wafv2:*",
        "shield:*",
        "support:*",
        "budgets:*",
        "ce:*",
        "health:*",
        "trustedadvisor:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "ap-northeast-1",
            "ap-southeast-1"
          ]
        },
        "ArnNotLike": {
          "aws:PrincipalARN": [
            "arn:aws:iam::*:role/PlatformBreakGlass"
          ]
        }
      }
    }
  ]
}
```

讀這份 SCP 的方式：

- `Effect: Deny` 搭配 `NotAction`：意思是「除了列出的這些全球服務動作之外，其他動作都在條件成立時拒絕」。`NotAction` 在 Deny 裡是「排除清單」，不是「允許清單」。
- `aws:RequestedRegion`：請求要送往的 Region。不在東京、新加坡的請求就符合條件。
- 同一個 `Condition` 區塊裡的多個條件是 **AND**：Region 不在清單內，**而且**呼叫者不是 `PlatformBreakGlass` role，才會被拒絕。這保留了一條緊急通道，例如需要在 `us-east-1` 處理特殊事件時使用。
- `wafv2:*` 排除的原因是 CloudFront 用的 WAF web ACL 必須在 `us-east-1` 管理（第 16 章）；ACM 憑證若要給 CloudFront 用也必須在 `us-east-1`（第 15 章），Wanderly 讓平台團隊用 break-glass role 處理這種少數情況。

> [!note] Control Tower 的 Region deny
> 使用 Control Tower 時，可以直接啟用它內建的 Region deny control，由 Control Tower 維護全球服務的例外清單，不必自己寫這份 SCP（14.11 節）。

### 範例二：保護稽核與安全基線

Wanderly 用 organization trail 與 AWS Config 做稽核（第 16 章）。這份 SCP 防止成員帳號裡任何人（包括帳號管理員與 root user）關閉或刪除這些設定，只有平台團隊的自動化 role 例外：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ProtectAuditBaseline",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "cloudtrail:UpdateTrail",
        "cloudtrail:PutEventSelectors",
        "config:StopConfigurationRecorder",
        "config:DeleteConfigurationRecorder",
        "config:DeleteDeliveryChannel",
        "guardduty:DeleteDetector",
        "guardduty:DisassociateFromAdministratorAccount",
        "securityhub:DisableSecurityHub"
      ],
      "Resource": "*",
      "Condition": {
        "ArnNotLike": {
          "aws:PrincipalARN": "arn:aws:iam::*:role/PlatformAutomation"
        }
      }
    },
    {
      "Sid": "DenyLeaveOrganization",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*"
    }
  ]
}
```

注意 `aws:PrincipalARN` 比對的是 **role 的 ARN**（`arn:aws:iam::帳號:role/名稱`），不是 AssumeRole 後的 session ARN（`arn:aws:sts::帳號:assumed-role/名稱/session`）。這是寫例外條件時最常見的錯誤：用 `aws:userid` 或 session ARN 比對，結果例外永遠不生效。

### 範例三：限制成員帳號的 root user、強制 IMDSv2

成員帳號的 root user 幾乎不需要日常使用，Wanderly 用 SCP 禁止它做任何事；同時要求所有新 EC2 都使用 IMDSv2（第 17 章），降低 SSRF 攻擊偷取 instance 憑證的風險：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyMemberRootUser",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:PrincipalArn": "arn:aws:iam::*:root"
        }
      }
    },
    {
      "Sid": "RequireImdsV2",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringNotEquals": {
          "ec2:MetadataHttpTokens": "required"
        }
      }
    }
  ]
}
```

第一段之所以有效，正是因為「SCP 會影響成員帳號的 root user」。少數只有 root user 能做的工作，可以暫時把帳號移到沒有這條政策的 OU 處理。更徹底的做法是搭配 IAM 的**集中 root 存取管理（centralized root access）**：由 management account 或 IAM 的 delegated administrator 直接刪除成員帳號 root user 的密碼、access key 與 MFA，讓「root 密碼外洩」這個風險從根本消失；之後若需要 root 等級的操作，再呼叫 `sts:AssumeRoot` 開啟一個短暫、只限特定任務的特權 session。這種 session 目前只支援少數任務，例如刪除一個把所有人都鎖在外面的 S3 bucket policy 或 SQS queue policy、刪除或恢復成員帳號的 root 憑證。

第二段只針對 `instance` 資源類型：`RunInstances` 一次會涉及 instance、volume、network interface 等多種資源，而 `ec2:MetadataHttpTokens` 只存在於 instance 的請求內容中，把 Resource 限縮到 instance 才不會誤擋。

### 安全上線：SCP 寫錯的代價很大

SCP 一旦附加就立即生效，而且影響整個 OU 底下的所有帳號。Wanderly 的上線流程：

1. **先查實際用量**：IAM 的 **service last accessed data**（上次存取資訊）可以在 OU 或帳號層級顯示「哪些服務最近被用過」，用來判斷 Deny 或 allow list 會不會擋到正在使用的服務。
2. **在測試 OU 驗證**：建立一個 Policy Staging OU，放入代表性的測試帳號，先在那裡附加新 SCP 並跑一輪部署與日常操作。
3. **分階段擴大**：Sandbox → NonProd → Prod，每一步觀察 CloudTrail 中被拒絕的請求（`errorCode` 為 `AccessDenied`，錯誤訊息會指出是被 service control policy 擋住）。
4. **保留恢復路徑**：SCP 不影響 management account，所以即使某個 SCP 把成員帳號鎖死，management account 仍可以修改或移除它。這也是不要把 management account 權限隨便發出去的另一個理由。

到這裡，SCP 管住了「成員帳號裡的人能做什麼」。但還有一個漏洞：如果某個工程師在 bucket policy 裡寫了 `"Principal": "*"`，組織外面的人來讀資料，SCP 管不到他們。下一節的 RCP 就是補這個洞。

## 14.8 RCP：從資源端畫出組織的資料邊界

### SCP 看不到的請求

SCP 限制的是「發出請求的 principal 在哪個帳號」。當一個**組織外的** principal 透過 resource-based policy 存取 Wanderly 成員帳號裡的 S3 bucket 時，這個 principal 不在 Wanderly 的 organization 裡，Wanderly 的 SCP 根本不會被評估。

**RCP（Resource Control Policy，資源控制政策）** 是 2024 年底推出的另一種 Organizations 授權政策：它附加在 root、OU 或帳號上，為**成員帳號裡的資源**設定可被存取的最大範圍。不論請求來自組織內還是組織外，只要目標資源屬於受 RCP 約束的帳號，RCP 就會參與評估。

| 比較 | SCP | RCP |
|---|---|---|
| 限制的對象 | 成員帳號裡的 principal（身份） | 成員帳號裡的 resource（資源） |
| 典型問題 | 「我們的人能做什麼？」 | 「誰能存取我們的資源？」 |
| 能否管住組織外的 principal | 不能 | 能 |
| 授予權限 | 不會 | 不會 |
| 支援範圍 | 所有服務的 API | 只有支援 RCP 的服務（2024 年推出時是 S3、STS、KMS、SQS、Secrets Manager，之後已擴充到 DynamoDB、ECR、CloudWatch Logs 等數十個服務） |
| 預設政策 | `FullAWSAccess`（可移除） | `RCPFullAWSAccess`（自動附加，不能移除） |
| 自訂政策的 Effect | Allow 或 Deny | 只能寫 Deny |
| 不受影響 | management account、service-linked role | management account 的資源、service-linked role、AWS managed KMS keys |

### 資料邊界（data perimeter）

RCP 最常見的用途是建立 **data perimeter（資料邊界）**：讓「只有我們組織的身份，才能存取我們組織的資源」。AWS 把資料邊界分成三個面向：

- **身份邊界**：只有可信任的身份（組織內的 principal、AWS 服務）能存取我的資源 → 用 RCP 搭配 `aws:PrincipalOrgID`。
- **資源邊界**：我的身份只能存取可信任的資源（組織內的資源）→ 用 SCP 搭配 `aws:ResourceOrgID`。
- **網路邊界**：只能從預期的網路（公司 VPC、特定 VPC endpoint）存取 → 用 `aws:SourceVpce`、`aws:SourceIp` 等條件（第 6 章）。

Wanderly 的 RCP 範例：拒絕組織外的身份存取任何成員帳號的 S3 物件，但不擋 AWS 服務本身（例如 CloudTrail 寫入日誌 bucket）：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceOrgIdentitiesForS3",
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

- RCP 的 statement 必須寫 `"Principal": "*"`，因為它描述的是「任何人存取這些資源」。
- `StringNotEqualsIfExists`：請求者不屬於組織 `o-a1b2c3d4e5` 時符合條件。
- `BoolIfExists` 的 `aws:PrincipalIsAWSService` 為 `false`：排除 AWS 服務以服務 principal 身份發出的請求，避免擋掉 CloudTrail、S3 replication 等服務。
- 兩個條件 AND：「不是本組織的身份，也不是 AWS 服務」才拒絕。

如果某個 bucket 確實需要分享給合作夥伴帳號，可以在條件中加入例外（例如用 `aws:PrincipalAccount` 列出夥伴帳號），或把那個帳號放在不套用這條 RCP 的 OU。

> [!warning] 常見誤解
> 「RCP 可以授權外部帳號存取我的 bucket。」不行。RCP 和 SCP 一樣只設上限，自訂 RCP 甚至只能寫 Deny。外部帳號要存取，仍然需要 bucket policy 的 Allow（第 13、22 章）。

## 14.9 其他 Organizations 政策：tag、backup 與更多

SCP 與 RCP 屬於**授權政策（authorization policies）**，直接影響請求能否成功。Organizations 還有一類**管理政策（management policies）**，用來在多帳號間統一設定某項服務的行為：

| 政策類型 | 做什麼 | 要注意 |
|---|---|---|
| Tag policy | 規範 tag key 的大小寫、允許的 value；可對指定資源類型「強制」，拒絕不合規的 tag 操作 | 它**不會要求資源一定要有 tag**；要強制「建立時必須帶某個 tag」，用 SCP 搭配 `aws:RequestTag` 條件，或用 Config rule 偵測 |
| Backup policy | 在組織層定義 AWS Backup 的備份計畫，自動套用到各帳號 | 搭配 AWS Backup 的跨帳號管理功能（第 34、43 章） |
| AI services opt-out policy | 選擇不讓 AWS AI 服務使用你的內容改進服務 | 一次套用到整個組織 |
| Declarative policy | 以宣告方式強制某些服務的設定狀態，例如封鎖 EC2 的公開 AMI 分享、強制 IMDSv2 預設值 | 較新的政策類型，支援的服務與屬性有限 |

Tag policy 的經典考題：「公司要求所有資源的 `CostCenter` tag 統一使用 `CostCenter` 這個大小寫，且值必須是指定清單之一。」這是 tag policy。但若題目要求「建立 EC2 時若沒有 `CostCenter` tag 就拒絕」，tag policy 做不到，正解是 SCP：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequireCostCenterTagOnInstances",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "Null": {
          "aws:RequestTag/CostCenter": "true"
        }
      }
    }
  ]
}
```

`Null` 條件為 `true` 的意思是「請求中沒有這個 key」。所以只要 `RunInstances` 請求沒有帶 `CostCenter` tag，就會被拒絕。

政策解決了「規則」，但還有一個問題：資安團隊要在每個帳號、每個 Region 啟用 GuardDuty，總不能每次都登入 management account 操作。這就是 delegated administrator 的用途。

## 14.10 Trusted access 與 delegated administrator

很多 AWS 服務可以和 Organizations 整合，在所有成員帳號上一次啟用或集中管理。這需要兩個步驟：

1. **Trusted access（受信任存取）**：由 management account 允許某個服務存取 organization 的結構資訊並在成員帳號中運作。啟用時，該服務通常會在成員帳號建立需要的 service-linked role。
2. **Delegated administrator（委派管理員）**：由 management account 指定一個成員帳號，代為管理該服務在整個 organization 的設定。

Wanderly 的做法是把 `security-tooling` 帳號註冊為 GuardDuty、Security Hub、Amazon Inspector、Macie、AWS Config（aggregator）、Firewall Manager 的 delegated administrator；把 `network` 帳號註冊為 IPAM 的 delegated administrator（第 5 章）；把 `shared-services` 帳號註冊為 CloudFormation StackSets 的 delegated administrator。IAM Identity Center 也可以委派給專用帳號管理日常的使用者與 permission set（第 13 章）。

這樣做的好處很具體：

- 資安團隊每天登入的是 `security-tooling`，而不是 management account，management account 的登入次數降到最低。
- 新帳號加入 organization 時，許多服務可以設定「自動為新帳號啟用」，例如 GuardDuty 的 auto-enable。
- 出問題時，影響範圍限定在 delegated administrator 帳號，而且它仍然受 SCP 約束（它是成員帳號）。

**CloudFormation StackSets** 搭配 Organizations 的 service-managed permissions，可以把一份 CloudFormation template 部署到某個 OU 的所有帳號與指定 Region，並在新帳號加入該 OU 時**自動部署**。這是「新帳號一開出來就具備基線設定」的基本工具（第 37 章）。

> [!tip] 考試提示
> 題目要求「集中管理 GuardDuty／Security Hub，但不要在 management account 日常操作」，答案是 trusted access + delegated administrator。題目要求「新帳號加入 OU 時自動部署 IAM role 或 Config rule」，想到 StackSets 的 automatic deployment，或下一節的 Control Tower。

到目前為止，平台團隊用 Organizations 加上 SCP、StackSets、delegated admin，手動拼出了一套治理環境。這很有彈性，但要自己維護很多零件。AWS 把這些最佳實務打包成一個服務：Control Tower。

## 14.11 Control Tower：一鍵建立有治理的 landing zone

### Landing zone 是什麼

**Landing zone（著陸區）** 是一個依最佳實務預先設定好的多帳號環境：有固定的 OU 結構、集中的日誌帳號、稽核帳號、統一的登入方式，以及一組預設的 guardrail。之後所有新 workload 都「降落」在這個環境裡，自動繼承這些設定。

**AWS Control Tower** 是建立與維運 landing zone 的受管服務。它不是 Organizations 的替代品，而是建立在 Organizations、IAM Identity Center、CloudTrail、AWS Config、Service Catalog、CloudFormation StackSets 等服務之上的編排層。

```text
                  Management account
          （Control Tower 主控台、Organizations）
                          │
        ┌─────────────────┼──────────────────────┐
        │                 │                      │
  OU: Security      OU: Sandbox（可選）     其他已註冊的 OU
   ├─ Log Archive ◄──┐                       （Workloads…）
   │   ① 集中日誌     │ CloudTrail／Config        │
   └─ Audit           │ 日誌                     │
       ② 跨帳號稽核   │                          │
         與通知       └──────────────────────────┤
                                                 │
  ③ Controls：SCP／RCP（preventive）             │
              Config rules（detective）         ─┤
              CloudFormation hooks（proactive） │
                                                 │
  ④ Account Factory ─── 開出新帳號 ──────────────┘
     （Service Catalog／AFT）  自動套用 baseline 與 controls
  ⑤ IAM Identity Center：所有帳號的統一登入
```

① **Log Archive 帳號**：集中保存所有帳號的 CloudTrail 與 Config 日誌，一般人無法修改。② **Audit 帳號**：資安團隊用來跨帳號唯讀稽核、接收合規通知（SNS）。③ **Controls**：套用在 OU 上的規則，下一段詳述。④ **Account Factory**：標準化開帳號的流程。⑤ 透過 IAM Identity Center 讓使用者以單一登入進入各帳號（第 13 章）。

### Controls：三種行為

Control Tower 把 guardrail 稱為 **controls**（早期文件稱 guardrails），依「何時起作用」分成三種：

| 行為 | 在什麼時候起作用 | 怎麼實作 | 例子 |
|---|---|---|---|
| Preventive（預防性） | API 請求發生時直接拒絕 | SCP、RCP（以及部分 declarative policy） | 禁止刪除 Log Archive 的 bucket、禁止在未核准 Region 建資源 |
| Detective（偵測性） | 資源已存在後持續評估，發現違規就回報 | AWS Config rules | 偵測 S3 bucket 是否允許公開讀取、EBS 是否未加密 |
| Proactive（主動性） | 用 CloudFormation 建立資源**之前**檢查 template | CloudFormation hooks | 拒絕建立未啟用加密的 RDS template |

三者的差別用「Wanderly 要求所有 S3 bucket 必須封鎖公開存取」來看：preventive control 讓修改 Block Public Access 的 API 直接失敗；detective control 會找出已經存在的違規 bucket 並標記為不合規，但不會阻止；proactive control 會在 CloudFormation 部署前就擋下違規的 template，但對直接呼叫 API 或在主控台手動建立的資源沒有作用。

Controls 依「強制程度」又分成 **mandatory（必要，一定啟用、不能關）**、**strongly recommended（強烈建議）**、**elective（可選）**。Mandatory controls 主要用來保護 Control Tower 自己建立的資源，例如禁止修改 Log Archive 帳號的日誌設定。

### Account Factory：標準化開帳號

**Account Factory** 讓平台團隊或被授權的使用者，填寫帳號名稱、email、要放在哪個 OU、要給哪個 Identity Center 使用者存取，就能開出一個已經註冊到 Control Tower、套用好 controls 與 baseline 的新帳號。它底層使用 Service Catalog 的產品。

需要更多客製化時有幾種延伸：

- **Account Factory for Terraform（AFT）**：用 Terraform 與 GitOps 流程開帳號，並在開帳號時執行自訂的 Terraform 模組（第 40 章）。
- **Account Factory Customization（AFC）**：在開帳號時套用以 CloudFormation 或 Terraform 寫好的 blueprint。
- **Customizations for AWS Control Tower（CfCT）**：一個 AWS 解決方案，用 CloudFormation template 與 SCP 在帳號生命週期事件時自動套用自訂設定。

### Drift 與既有環境

**Drift（偏移）** 指 Control Tower 管理的設定被人在 Control Tower 之外修改，例如有人直接在 Organizations 主控台把帳號移到未註冊的 OU、或修改了 Control Tower 附加的 SCP。Control Tower 會偵測並在主控台顯示，多數情況可以透過「repair landing zone」或重新註冊 OU 修復。實務上的規則是：**由 Control Tower 管的東西，就透過 Control Tower 修改**。

已經有 Organizations 的公司也可以導入 Control Tower：在既有 organization 上設定 landing zone，再把既有 OU **註冊（register）**、既有帳號**登錄（enroll）**進 Control Tower。登錄前要確認帳號裡沒有和 Control Tower baseline 衝突的設定（例如已存在的 Config recorder），否則登錄可能失敗。

> [!note] 為什麼 Wanderly 最後選 Control Tower
> 平台團隊只有三個人。自己用 StackSets、SCP、Config 拼 landing zone 雖然彈性最大，但每次 AWS 推出新的最佳實務都要自己更新。Control Tower 讓他們用最少的營運負擔得到標準化的 landing zone，需要客製化的部分再用 AFT 補上。考試中「LEAST operational overhead 建立多帳號治理環境」幾乎都指向 Control Tower。

Organizations、SCP 與 Control Tower 都是從帳號與 OU 的層級管理。可是在單一帳號裡，還有一個常見難題：開發者要建立 Lambda 的 execution role，平台團隊又不想把 IAM 管理權限整個交出去。

## 14.12 Permission boundary：讓開發者自己建 role，又不能提權

### 問題：建 role 等於能給自己任何權限

Wanderly 的開發者在 `booking-dev` 帳號裡用 SAM 部署 Lambda（第 19 章），每個函式都需要自己的 IAM role。如果每次都要找平台團隊建 role，開發速度會被拖慢；但如果直接給開發者 `iam:CreateRole` 與 `iam:AttachRolePolicy`，他們就可以建一個附有 `AdministratorAccess` 的 role，再讓 Lambda（或自己）使用它，等於繞過了所有權限控制。這種手法稱為**權限提升（privilege escalation）**。

### Permission boundary 怎麼運作

**Permission boundary（權限邊界）** 是一個附加在 IAM user 或 role 上的 managed policy，定義這個身份**最多能擁有的權限**。和 SCP 一樣，它本身不授予任何權限；有效權限是 identity policy 與 boundary 的交集。

| 情況 | Identity policy | Permission boundary | 結果 |
|---|---|---|---|
| 兩者都允許 | 允許 `s3:GetObject` | 允許 `s3:*` | 允許 |
| 只有 boundary 允許 | 沒有 S3 權限 | 允許 `s3:*` | 拒絕（boundary 不授權） |
| 只有 identity 允許 | 允許 `iam:*` | 不含 IAM | 拒絕（超出邊界） |

委派模式的關鍵是：**允許開發者建立 role，但條件是新 role 必須掛上指定的 boundary**。這樣不論開發者給新 role 附加什麼 policy，它的有效權限都不會超出 boundary。

### Wanderly 的委派政策

平台團隊先建立一個名為 `AppBoundary` 的 managed policy，內容只允許應用程式需要的服務（例如 DynamoDB、S3、SQS、CloudWatch Logs），不包含 IAM、Organizations 等管理服務。然後給開發者 role 這份 identity policy：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ManageAppRolesOnlyWithBoundary",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePermissionsBoundary"
      ],
      "Resource": "arn:aws:iam::111122223333:role/app/*",
      "Condition": {
        "StringEquals": {
          "iam:PermissionsBoundary": "arn:aws:iam::111122223333:policy/AppBoundary"
        }
      }
    },
    {
      "Sid": "ReadAndDeleteAppRoles",
      "Effect": "Allow",
      "Action": [
        "iam:GetRole",
        "iam:ListRoles",
        "iam:ListAttachedRolePolicies",
        "iam:DeleteRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassOnlyAppRolesToLambda",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::111122223333:role/app/*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "lambda.amazonaws.com"
        }
      }
    },
    {
      "Sid": "DenyBoundaryTampering",
      "Effect": "Deny",
      "Action": [
        "iam:DeleteRolePermissionsBoundary",
        "iam:CreatePolicyVersion",
        "iam:DeletePolicy",
        "iam:DeletePolicyVersion",
        "iam:SetDefaultPolicyVersion"
      ],
      "Resource": [
        "arn:aws:iam::111122223333:role/*",
        "arn:aws:iam::111122223333:policy/AppBoundary"
      ]
    }
  ]
}
```

逐段說明這份政策堵住了哪些漏洞：

1. **`ManageAppRolesOnlyWithBoundary`**：只能在 `/app/` 路徑下建立與修改 role，而且條件 `iam:PermissionsBoundary` 要求該 role 的 boundary 必須是 `AppBoundary`。建立 role 時沒帶 boundary，或帶了別的 boundary，請求就失敗。
2. **`ReadAndDeleteAppRoles`**：允許查看與刪除 role，方便部署工具運作。實務上可以再把 `DeleteRole` 限縮到 `/app/` 路徑。
3. **`PassOnlyAppRolesToLambda`**：`iam:PassRole` 是「把 role 交給 AWS 服務使用」的權限。限制只能把 `/app/` 下的 role 交給 Lambda，避免開發者把現有的高權限 role 交給 EC2 或 Lambda 使用。
4. **`DenyBoundaryTampering`**：禁止移除 role 上的 boundary，也禁止修改 `AppBoundary` 本身。少了這段，開發者可以先建好 role，再把 boundary 拿掉或把 boundary 改寬。

開發者自己的 role 通常也會掛上同一個或更嚴格的 boundary，讓他們本身也不會超出應用範圍。

### SCP 與 permission boundary 的分工

兩者都是「上限」，但作用範圍不同：

- **SCP**：作用在整個帳號（或整個 OU）的所有 principal，由 organization 層級管理，成員帳號管理員改不了。
- **Permission boundary**：作用在單一 IAM user 或 role，由帳號內的管理員設定，用來在帳號內委派 IAM 管理權。

Wanderly 同時使用兩者：SCP 保證「任何人都不能關掉 CloudTrail、不能離開核准 Region」；permission boundary 保證「開發者建立的 role 不能碰 IAM 與資安服務」。

## 14.13 比較與選型

### 這麼多「上限」，各管什麼？

| 機制 | 管理層級 | 限制對象 | 授予權限 | 影響 root user | 典型用途 |
|---|---|---|---|---|---|
| IAM identity policy | 帳號內 | 附加的 user／role／group | 會 | 不適用（root 不受 IAM policy 限制） | 日常授權 |
| Resource-based policy | 帳號內 | 存取該資源的 principal | 會 | 可透過條件影響 | 跨帳號分享 bucket、key、queue |
| Permission boundary | 帳號內 | 單一 user／role | 不會 | 不能 | 委派開發者建立 role |
| SCP | Organization | 成員帳號裡的 principal | 不會 | 會（成員帳號） | Region 限制、保護稽核、禁止高風險動作 |
| RCP | Organization | 成員帳號裡的資源 | 不會 | 會（存取資源的任何人） | 資料邊界：拒絕組織外身份存取 |
| Tag policy | Organization | tag 的格式與值 | 不適用 | 不適用 | tag 命名標準化 |
| Control Tower controls | Organization（OU） | 依實作：SCP／RCP、Config、hooks | 不會 | 依實作 | 一次套用打包好的 guardrail |
| AWS Config rules | 帳號／組織 | 已存在的資源設定 | 不適用 | 不適用 | 偵測與自動修復違規（第 16、38 章） |

### 選型決策

```text
要解決的是什麼？
├─ 隔離權限、配額、帳單、合規範圍 → 拆成多個帳號，用 Organizations 管理
├─ 「組織裡任何人（含帳號管理員、root）都不准做 X」
│    ├─ X 是成員帳號裡身份的動作 → SCP（deny list）
│    └─ X 是「組織外的人存取我們的資源」→ RCP（搭配 aws:PrincipalOrgID）
├─ 帳號內把建 role 的權力交給開發者 → permission boundary + iam:PermissionsBoundary 條件
├─ 找出已經存在的違規資源 → Config rules（或 Control Tower detective controls）
├─ 部署前就擋下不合規的 IaC → CloudFormation hooks（Control Tower proactive controls）
├─ tag 拼寫與值統一 → tag policy；要求「必須有 tag」→ SCP 的 aws:RequestTag 條件
└─ 用最少營運負擔建立整套多帳號基線與開帳號流程 → Control Tower + Account Factory（客製化用 AFT）
```

## 14.14 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 隔離 production 與 dev 的權限、配額、帳單 | 多帳號 + Organizations OU |
| 防止任何人（包括帳號管理員）停用 CloudTrail／GuardDuty | SCP Deny（附加在 root 或 OU） |
| SCP 允許了，但使用者還是沒權限 | SCP 不授權，還需要 IAM Allow |
| 管理員有 AdministratorAccess 卻不能用某服務 | 路徑上某層 SCP 未允許或明確 Deny |
| 哪個帳號不受 SCP 限制 | Management account |
| 限制只能在特定 Region 部署 | SCP + `aws:RequestedRegion` + 全球服務 `NotAction` 例外（或 Control Tower Region deny） |
| 拒絕組織外的身份存取任何成員帳號的 S3／KMS 資源 | RCP + `aws:PrincipalOrgID` |
| 只允許與組織內的帳號分享資源 | `aws:PrincipalOrgID` 條件（resource policy 或 RCP） |
| 被邀請加入的帳號，管理帳號無法 AssumeRole 進去 | 手動建立信任 management account 的 role（自動建立的 `OrganizationAccountAccessRole` 只存在於由 Organizations 建立的帳號） |
| RI／Savings Plans 折扣不要分享給某帳號 | 在 management account 關閉該帳號的折扣共享 |
| 集中管理 GuardDuty、Security Hub，不用 management account | Trusted access + delegated administrator |
| LEAST operational overhead 建立多帳號 landing zone | AWS Control Tower |
| 新帳號自動符合規範、用 Terraform 開帳號 | Account Factory／Account Factory for Terraform |
| 部署前檢查 CloudFormation template | Proactive control（CloudFormation hooks） |
| 已存在資源的合規偵測 | Detective control（Config rules） |
| 開發者可自建 Lambda role 但不能提權 | Permission boundary + `iam:PermissionsBoundary` 條件 + 禁止移除 boundary |
| tag key 大小寫不一致 | Tag policy |

**常見陷阱**：

1. 以為 SCP 會授予權限，或以為 SCP Allow 可以補足 IAM 缺少的權限。兩者是交集，不是聯集。
2. 以為 SCP 能限制 management account。它不能，所以 management account 不該放 workload。
3. 以為 SCP 不影響 root user。它不影響 management account 的 root user，但**會**影響成員帳號的 root user。
4. 拿掉 OU 上的 `FullAWSAccess` 卻沒有附加替代的 Allow SCP，造成整個 OU 的帳號失去所有權限。
5. 用 tag policy 「強制資源必須有 tag」。Tag policy 只規範格式，強制存在要用 SCP 條件或 Config。
6. 寫 Region 限制 SCP 時沒有排除 IAM、Route 53、CloudFront 等全球服務，結果把這些服務全擋了。

## 14.15 SAP 加深：OU 設計、併購與大規模治理

SAA 只要求你理解 SCP 的效果；SAP 會給你一家有上百個帳號、剛併購另一家公司、還要通過金融法規的企業，問你怎麼設計整個治理模型。

### 依政策設計 OU，而不是依組織圖

AWS 建議的 OU 結構以「治理需求」為主軸，常見的頂層 OU：

| OU | 用途 |
|---|---|
| Security | Log Archive、Security Tooling（Audit）等資安帳號 |
| Infrastructure | 網路、共享服務 |
| Workloads（下分 Prod／NonProd） | 業務系統；Prod 套用較嚴格政策 |
| Sandbox | 個人實驗，搭配預算與自動清理 |
| Policy Staging | 測試新 SCP 的帳號 |
| Exceptions | 確有理由需要例外政策的帳號，集中管理便於稽核 |
| Suspended | 待關閉帳號，套用 deny-all |
| Deployments | CI/CD 管線帳號 |

如果按部門（財務、行銷、工程）切 OU，同樣是 production 的帳號會散落在不同 OU，相同的 SCP 要附加很多次，而且「每個節點最多 5 個 SCP」的限制很快就會用完。依「環境與合規等級」分組，才能讓一份政策在一個節點上涵蓋所有需要它的帳號。

### 併購另一家公司的帳號

Part 8 的情境是 Wanderly 併購一家已經有自己 organization 的旅行社。帳號不能同時屬於兩個 organization，但可以用 direct account transfer 直接從旅行社的 organization 移到 Wanderly 的 organization，所以搬遷流程是：

1. 先在 Wanderly 的 organization 裡建立一個過渡 OU，附加與旅行社現行規則相容的寬鬆 SCP，避免一搬進來就壞掉。
2. 在旅行社的 organization 裡做移轉前準備：取消帳號的 delegated administrator 註冊、匯出組織層級的帳單報表、確認沒有 SCP 或 IAM policy 擋住移轉。
3. 由 Wanderly 的 management account 發出邀請，帳號接受後直接移轉（不必先離開原 organization）。移入的帳號會先落在 Wanderly organization 的 root，再由平台團隊移到過渡 OU。
4. 在帳號裡建立信任 Wanderly management account（或平台自動化帳號）的管理 role，因為邀請加入的帳號沒有 `OrganizationAccountAccessRole`。
5. 若使用 Control Tower，評估後把帳號 enroll，並逐步移到正式的 Workloads OU，接受完整的 controls。

搬遷時要注意：RI 與 Savings Plans 的折扣共享範圍會改變；原本依賴 `aws:PrincipalOrgID` 的 resource policy 會因為 organization ID 改變而失效，必須先更新；原 organization 的 organization trail 不再記錄這些帳號。

### Break-glass 與恢復設計

再嚴密的 guardrail 也要有緊急通道。Wanderly 的 break-glass 設計：

- SCP 的例外只針對一個名稱固定的 `PlatformBreakGlass` role，這個 role 的使用會觸發 EventBridge 規則通知資安團隊。
- Break-glass 的登入方式不依賴 IAM Identity Center（以免 IdP 故障時也進不去），憑證以實體保管並要求 MFA。
- 因為 management account 不受 SCP 限制，它是最終的恢復路徑；它的 root 憑證與 MFA 裝置分開保管。

### 大規模 SCP 管理

當 organization 有數百個帳號時，SCP 的變更要當成程式碼管理：存放在版本控制、透過 pipeline 部署到 Policy Staging OU 測試、再推到正式 OU。IAM Access Analyzer 的 policy validation 可以在部署前檢查 SCP 的語法與常見錯誤。Control Tower 本身也會使用 SCP 名額來實作 preventive controls，規劃時要把這部分的配額算進去。

更多 landing zone 的帳號策略、集中日誌與 break-glass 細節在第 40 章；組織層的備份政策、成本可視化與 tag 治理在第 43 章。

## 本章重點整理

- 帳號是 AWS 上最強的隔離邊界，能隔離 IAM、資源、配額、帳單與合規範圍；多個 VPC 只隔離網路。
- AWS Organizations 以 root、OU（最多 5 層）與帳號組成一棵樹，政策往下繼承；OU 應依治理需求而不是組織圖設計。
- Management account 負責帳單與組織管理，不受 SCP 限制，因此不應放任何 workload，日常服務管理應交給 delegated administrator。
- 由 Organizations 建立的帳號會自動有 `OrganizationAccountAccessRole`，被邀請加入的帳號則需要手動建立管理 role。
- Consolidated billing 合併計算用量階梯並共享 RI／Savings Plans 折扣（可對個別帳號關閉），但和權限無關。
- SCP 只設定成員帳號 principal 的權限上限，不授予權限；有效權限是 SCP、IAM 與其他上限的交集。
- SCP 不影響 management account 與 service-linked role，但會限制成員帳號的 root user。
- SCP 的 Allow 必須在 root 到帳號路徑上的每一層都存在，Deny 出現在任何一層就生效；預設附加 `FullAWSAccess`。
- Deny list 策略維護成本低，是預設建議；allow list 策略要移除 `FullAWSAccess` 並在每一層列出允許的服務。
- Region 限制 SCP 使用 `aws:RequestedRegion`，並以 `NotAction` 排除 IAM、Route 53、CloudFront 等全球服務。
- RCP 從資源端限制成員帳號裡的資源可被誰存取，能管住組織外的 principal，常搭配 `aws:PrincipalOrgID` 建立資料邊界。
- Tag policy 只規範 tag 的格式與值，要求資源「必須有 tag」要用 SCP 的 `aws:RequestTag` 條件或 Config rule。
- Control Tower 建立在 Organizations 等服務之上，提供 landing zone、Log Archive 與 Audit 帳號、Account Factory，以及 preventive（SCP／RCP）、detective（Config）、proactive（CloudFormation hooks）三種 controls。
- Permission boundary 是單一 user／role 的權限上限，配合 `iam:PermissionsBoundary` 條件與禁止移除 boundary 的 Deny，可安全地讓開發者自建 role。

## 本章練習題

### 練習 14-1｜SAA｜單選｜帳號作為隔離邊界

Wanderly 目前把 production、staging 與工程師的實驗環境放在同一個 AWS 帳號的三個不同 VPC 中。最近 staging 的壓力測試用光了該 Region 的 Lambda concurrency，導致 production 的付款函式被 throttle；財務部門也抱怨無法準確區分各環境的費用。公司希望用最少的長期管理負擔解決這兩個問題。

最合適的做法是什麼？

- A. 為每個環境建立獨立的 VPC endpoint，並在 production 的 Lambda 設定 reserved concurrency
- B. 為每個環境建立獨立的 AWS 帳號，並以 AWS Organizations 集中管理與合併帳單
- C. 對所有資源貼上 `Environment` tag，並用 IAM 條件限制 staging 的 role 只能操作 staging 資源
- D. 把 staging 移到另一個 Region，並為 production 申請提高 Lambda concurrency 配額

> [!answer]- 答案：B
> **A ✗** Reserved concurrency 可以保護 production 函式不被擠壓，但無法解決帳單歸屬問題；VPC endpoint 與配額或帳單無關。
>
> **B ✓** 大多數 service quota 以帳號為單位計算，獨立帳號讓 staging 的用量不再影響 production；帳號的費用天生分開，Organizations 的 consolidated billing 讓公司仍只需處理一張帳單。這是從結構上同時解決兩個問題。
>
> **C ✗** Tag 能幫助成本歸屬，但需要每個資源都正確貼上，也無法隔離同帳號共用的配額。IAM 條件同樣管不到配額。
>
> **D ✗** 換 Region 可以暫時分開配額，但環境仍在同一個帳號，帳單問題沒解決，也造成 staging 與 production 架構不一致。
>
> **考點**：SAA-1.1｜多帳號隔離配額、權限與帳單

### 練習 14-2｜SAA｜單選｜SCP 不授予權限

Wanderly 的 Workloads OU 附加了一個 SCP，允許 `s3:*` 與 `dynamodb:*`。`booking-dev` 帳號位於這個 OU 之下，帳號裡的 `AnalystRole` 只附加了一份允許 `dynamodb:Query` 的 IAM policy。一位分析師使用 `AnalystRole` 嘗試列出帳號中的 S3 bucket。

結果會是什麼？

- A. 成功，因為 SCP 允許 `s3:*`，且 SCP 會繼承到帳號中的所有 role
- B. 成功，但只能列出由 Workloads OU 建立的 bucket
- C. 失敗，因為 SCP 只設定權限上限，`AnalystRole` 沒有任何 S3 的 IAM Allow
- D. 失敗，因為 SCP 只能限制 root user，必須另外在 IAM 中撤銷權限

> [!answer]- 答案：C
> **A ✗** SCP 不會附加到 role，也不會授予任何權限。它只決定「最多能有哪些權限」，實際權限仍須由 IAM 或 resource policy 授予。
>
> **B ✗** OU 不會建立 bucket，也沒有「由 OU 建立的 bucket」這種概念；SCP 也不會依資源建立者過濾。
>
> **C ✓** 有效權限是 SCP 允許範圍與 IAM 授予權限的交集。SCP 允許 S3，但 IAM 只允許 `dynamodb:Query`，交集中沒有 `s3:ListAllMyBuckets`，所以被隱含拒絕。
>
> **D ✗** SCP 限制成員帳號中的所有 principal（包括 root user 與一般 role），不是只限制 root user。
>
> **考點**：SAA-1.1｜SCP 只設上限、不授權

### 練習 14-3｜SAA｜單選｜不受 SCP 影響的帳號

一位資安工程師在 organization 的 root 附加了一個 SCP，拒絕所有 `ec2:RunInstances` 請求，作為緊急止血措施。幾分鐘後，他發現仍有一個帳號可以成功啟動 EC2 instance。

這個帳號最可能是哪一個？

- A. Management account
- B. 剛從其他 organization 邀請加入的成員帳號
- C. 位於 Suspended OU 的成員帳號
- D. 由 Control Tower Account Factory 建立的成員帳號

> [!answer]- 答案：A
> **A ✓** SCP 不會影響 management account 中的任何身份，即使 SCP 附加在 root。這也是 management account 不應放 workload 的主要原因。
>
> **B ✗** 帳號一旦加入 organization 就是成員帳號，不論是建立還是邀請加入，都會受附加在 root 的 SCP 限制。
>
> **C ✗** Suspended OU 位於 root 之下，同樣繼承 root 上的 Deny，而且通常還有更嚴格的 deny-all 政策。
>
> **D ✗** Account Factory 建立的帳號是一般成員帳號，受 SCP 限制。
>
> **考點**：SAA-1.1｜SCP 不影響 management account

### 練習 14-4｜SAA｜單選｜限制 Region 的 SCP

Wanderly 依資料主權要求，所有成員帳號只能在 `ap-northeast-1` 與 `ap-southeast-1` 建立資源。平台團隊寫了一個 SCP：當 `aws:RequestedRegion` 不在這兩個 Region 時拒絕 `"Action": "*"`。附加後，工程師回報無法建立 IAM role，也無法修改 Route 53 記錄。

應如何修正，同時維持 Region 限制？

- A. 把 SCP 從 Workloads OU 改附加到 management account，讓它只限制管理人員
- B. 把 Effect 改成 Allow，並把 Condition 改為 `StringEquals`，讓兩個 Region 被允許
- C. 在每個帳號的 IAM policy 中加入 `iam:*` 與 `route53:*` 的 Allow，以覆蓋 SCP 的 Deny
- D. 把 `Action` 改為 `NotAction`，排除 IAM、Route 53、CloudFront 等全球服務的動作，讓 Deny 只套用到 Regional 服務

> [!answer]- 答案：D
> **A ✗** SCP 不影響 management account，附加在那裡等於完全沒有限制，Region 要求就失效了。
>
> **B ✗** 改成 Allow 型 SCP 並不會擋住其他 Region：預設的 `FullAWSAccess` 仍然允許所有動作，除非改用 allow list 策略並移除它；而且全球服務的請求被視為 `us-east-1`，同樣會出問題。
>
> **C ✗** Explicit Deny 永遠優先，IAM 的 Allow 無法覆蓋 SCP 的 Deny。
>
> **D ✓** IAM、Route 53、CloudFront 等全球服務的請求會被當作 `us-east-1` 的請求。用 `Deny` 搭配 `NotAction` 把它們排除，其他動作在 Region 不符時仍被拒絕，就能同時達成 Region 限制與全球服務正常運作。
>
> **考點**：SAA-1.1、SAP-1.2｜`aws:RequestedRegion` 與全球服務例外

### 練習 14-5｜SAA｜單選｜成員帳號的 root user

稽核員要求 Wanderly 確保所有 workload 帳號的 root user 即使密碼外洩，也無法刪除資源或修改設定。這些帳號都是 organization 的成員帳號。公司希望以集中、可稽核的方式實施。

哪個做法最合適？

- A. 在每個成員帳號建立 IAM policy，拒絕 root user 的所有動作
- B. 在 Workloads OU 附加 SCP，當 `aws:PrincipalArn` 符合 `arn:aws:iam::*:root` 時拒絕所有動作
- C. 用 permission boundary 附加到每個成員帳號的 root user
- D. 開啟 consolidated billing，讓 root user 的權限轉移到 management account

> [!answer]- 答案：B
> **A ✗** IAM policy 無法附加到 root user，也無法限制 root user；root user 不受帳號內 IAM policy 的約束。
>
> **B ✓** SCP 會影響成員帳號的 root user，這是它和帳號內 IAM 最大的差別。在 OU 附加這份 SCP 可以集中管理、統一套用，變更也會記錄在 CloudTrail。需要 root 才能做的少數工作，可以改用集中 root 存取管理或暫時移出 OU 處理。
>
> **C ✗** Permission boundary 只能附加在 IAM user 或 role，不能附加在 root user。
>
> **D ✗** Consolidated billing 只處理付款與折扣，不轉移、也不限制任何權限。
>
> **考點**：SAA-1.1｜SCP 會限制成員帳號 root user

### 練習 14-6｜SAA｜單選｜邀請加入的帳號無法管理

Wanderly 邀請一個既有的 AWS 帳號加入 organization。加入後，平台團隊從 management account 嘗試 AssumeRole 到該帳號的 `OrganizationAccountAccessRole`，結果失敗。由 Organizations 直接建立的其他帳號則都能正常 AssumeRole。

最可能的原因與修正方式是什麼？

- A. 被邀請的帳號不會自動建立 `OrganizationAccountAccessRole`；需在該帳號手動建立一個信任 management account 的管理 role
- B. 被邀請的帳號必須等 24 小時讓 SCP 生效後，role 才會出現
- C. 該帳號沒有啟用 consolidated billing，需在帳號內開啟後重試
- D. Management account 需要在 SCP 中允許 `sts:AssumeRole`，因為 SCP 預設會限制 management account

> [!answer]- 答案：A
> **A ✓** 只有透過 Organizations 建立的帳號會自動產生 `OrganizationAccountAccessRole`。被邀請的帳號原本就存在，Organizations 不會修改它的 IAM，必須由該帳號管理員手動建立 role 並設定 trust policy 信任 management account。
>
> **B ✗** SCP 不會建立任何 role，也沒有這種等待期；role 不存在的原因與時間無關。
>
> **C ✗** 加入 organization 就自動納入合併帳單，而且帳單與能否 AssumeRole 無關。
>
> **D ✗** SCP 不影響 management account；而且 AssumeRole 失敗的原因是目標 role 不存在。
>
> **考點**：SAA-1.1、SAP-1.4｜建立 vs 邀請帳號的差異

### 練習 14-7｜SAA｜單選｜Control Tower 的 control 類型

Wanderly 用 Control Tower 治理多帳號環境，有三個需求：(1) 任何人都不能刪除 Log Archive 帳號中的日誌 bucket；(2) 找出已經存在、但未啟用加密的 EBS volume；(3) 用 CloudFormation 部署前，就拒絕沒有啟用加密的 RDS template。

這三個需求依序對應哪一種 control 行為？

- A. Detective、preventive、proactive
- B. Preventive、proactive、detective
- C. Preventive、detective、proactive
- D. Proactive、detective、preventive

> [!answer]- 答案：C
> **A ✗** 刪除 bucket 必須在 API 請求當下就被阻止，detective control 只會事後回報，不能阻止。
>
> **B ✗** 找出「已存在」的違規資源是 detective control（由 Config rules 實作），proactive control 只在 CloudFormation 建立資源前檢查。
>
> **C ✓** Preventive control 以 SCP／RCP 在請求時直接拒絕；detective control 以 AWS Config rules 評估既有資源；proactive control 以 CloudFormation hooks 在部署前檢查 template。
>
> **D ✗** 順序完全相反。Proactive 不能保護已存在的 bucket 不被直接 API 刪除，preventive 也不會檢查 CloudFormation template 內容。
>
> **考點**：SAA-1.1、SAP-1.4｜preventive／detective／proactive controls

### 練習 14-8｜SAA｜選兩項｜開發者自建 role 不提權

Wanderly 的開發者需要在 `booking-dev` 帳號中自行為 Lambda 建立 execution role，平台團隊要確保開發者無法藉此取得超出應用範圍的權限（例如 IAM 或 Organizations 權限）。平台團隊已經建立一個名為 `AppBoundary` 的 managed policy。

哪兩項設定是必要的？（選兩項）

- A. 允許開發者 `iam:CreateRole` 與 `iam:AttachRolePolicy`，並以條件 `iam:PermissionsBoundary` 要求新 role 必須使用 `AppBoundary`
- B. 在 Workloads OU 附加 SCP 允許 `iam:CreateRole`，讓開發者取得建立 role 的權限
- C. 給開發者 `iam:*`，並在 CloudTrail 中監控是否建立了高權限 role
- D. 以明確 Deny 禁止開發者呼叫 `iam:DeleteRolePermissionsBoundary`，以及修改 `AppBoundary` 本身（例如 `iam:CreatePolicyVersion`）
- E. 把 `AppBoundary` 設定為開發者 role 的 trust policy

> [!answer]- 答案：A、D
> **A ✓** 這是委派模式的核心：開發者能建立 role，但只有在新 role 掛上 `AppBoundary` 時請求才會成功。不論之後附加什麼 policy，新 role 的有效權限都不會超出 boundary。
>
> **B ✗** SCP 不授予權限，允許型 SCP 不會讓開發者多出任何能力；而且 SCP 作用在整個帳號，無法區分「必須帶 boundary」這種條件。
>
> **C ✗** `iam:*` 讓開發者能建立任意權限的 role，CloudTrail 只能事後發現，無法預防提權。
>
> **D ✓** 少了這條，開發者可以建立 role 後移除 boundary，或把 `AppBoundary` 改寬，等於繞過限制。保護 boundary 本身是必要的一環。
>
> **E ✗** Trust policy 決定「誰可以 assume 這個 role」，和權限上限無關；boundary 必須以 permissions boundary 的方式附加。
>
> **考點**：SAA-1.1、SAP-2.3｜permission boundary 委派 IAM 管理

### 練習 14-9｜SAA｜單選｜Tag policy 的能力範圍

Wanderly 的財務團隊要求：所有 EC2 instance 在建立時必須帶有 `CostCenter` tag，沒有這個 tag 的建立請求應該直接失敗。平台團隊希望在所有 workload 帳號集中實施。

哪個做法能滿足需求？

- A. 在 Workloads OU 附加 SCP，當 `ec2:RunInstances` 請求中的 `aws:RequestTag/CostCenter` 為 Null 時拒絕
- B. 建立 tag policy 定義 `CostCenter` 的大小寫與允許值，附加到 Workloads OU
- C. 在 Cost Explorer 啟用 `CostCenter` 作為 cost allocation tag
- D. 建立 AWS Config rule `required-tags`，在各帳號偵測缺少 tag 的 instance

> [!answer]- 答案：A
> **A ✓** `Null` 條件為 true 表示請求中沒有該 tag key。把 Deny 套用在 instance 資源的 `RunInstances` 上，沒帶 `CostCenter` 的建立請求就會在當下失敗，而且 SCP 可在 OU 集中套用。
>
> **B ✗** Tag policy 規範 tag 的拼寫與允許值，強制模式只會拒絕「不合規的 tag 值」，不會要求資源必須帶有 tag。只用它的話，完全不帶 tag 的 instance 仍能建立。
>
> **C ✗** Cost allocation tag 只決定帳單報表中能否依 tag 分類，不會影響建立請求。
>
> **D ✗** Config rule 是偵測性控制，只能在 instance 建立後標記為不合規，無法讓建立請求失敗。若需求改成「找出既有違規資源」，它才是合適答案。
>
> **考點**：SAA-1.1、SAP-1.2｜tag policy vs SCP `aws:RequestTag`

### 練習 14-10｜SAP｜單選｜建立組織資料邊界

Wanderly 有 80 個成員帳號。資安團隊發現某個團隊在 bucket policy 裡誤用了 `"Principal": "*"`，讓組織外的任何人都能讀取 bucket。團隊要建立一層集中保護：即使未來某個資源擁有者寫錯 resource policy，組織外的身份也無法存取任何成員帳號中的 S3 物件，但 CloudTrail、S3 replication 等 AWS 服務的正常運作不能受影響。

最合適的做法是什麼？

- A. 在 root 附加 SCP，拒絕 `aws:PrincipalOrgID` 不等於本組織 ID 的 `s3:*` 請求
- B. 在 root 附加 RCP，對 `s3:*` 拒絕 `aws:PrincipalOrgID` 不等於本組織 ID 的請求，並以 `aws:PrincipalIsAWSService` 排除 AWS 服務
- C. 在每個帳號啟用 S3 Block Public Access，並以 AWS Config 偵測違規的 bucket policy
- D. 在 root 附加 tag policy，要求所有 bucket 帶有 `DataClassification` tag

> [!answer]- 答案：B
> **A ✗** SCP 只限制成員帳號裡的 principal。組織外的 principal 發出的請求不會評估 Wanderly 的 SCP，所以這份 SCP 擋不住外部存取。
>
> **B ✓** RCP 在資源端為成員帳號的資源設定上限，不論請求來自何處都會評估。以 `aws:PrincipalOrgID` 拒絕組織外身份，並用 `BoolIfExists` 的 `aws:PrincipalIsAWSService` 排除服務 principal，就能建立集中的身份邊界而不影響 AWS 服務。
>
> **C ✗** Block Public Access 能擋住公開存取，但無法擋住「特定外部帳號」的授權（那不算公開）；Config 是事後偵測。兩者都是好習慣，但不是題目要求的集中預防邊界。
>
> **D ✗** Tag policy 只規範 tag 格式，與存取控制無關。
>
> **考點**：SAP-1.2、SAP-1.4｜RCP 與 data perimeter

### 練習 14-11｜SAP｜單選｜集中管理資安服務

Wanderly 要在所有 80 個帳號、兩個 Region 啟用 GuardDuty 與 Security Hub，新帳號加入時也要自動啟用。公司的政策規定 management account 只能用於帳單與 organization 管理，資安團隊不得在其中進行日常操作。

哪個做法最合適？

- A. 在每個帳號用 CloudFormation StackSets 個別啟用 GuardDuty，並把所有 findings 寄送到資安團隊的 email
- B. 讓資安團隊使用 management account 的 IAM role 管理 GuardDuty 與 Security Hub，並以 SCP 限制該 role 的權限
- C. 從 management account 為兩個服務啟用 trusted access，並把 `security-tooling` 帳號註冊為 delegated administrator，再由該帳號設定自動為新帳號啟用
- D. 在每個成員帳號以邀請方式把 `security-tooling` 加為 GuardDuty 管理員，不使用 Organizations 整合

> [!answer]- 答案：C
> **A ✗** StackSets 可以部署設定，但各帳號的 findings 無法集中在一個管理視角中檢視與處理，也沒有利用服務原生的組織整合，營運負擔較高。
>
> **B ✗** SCP 不影響 management account，所以「用 SCP 限制 management account 的 role」根本無效；也違反不在 management account 日常操作的政策。
>
> **C ✓** Trusted access 讓服務能和 Organizations 整合，delegated administrator 讓成員帳號代管服務的組織層設定。GuardDuty 與 Security Hub 都支援由 delegated administrator 設定新帳號自動啟用，資安團隊的日常工作完全不需進入 management account。
>
> **D ✗** 邀請模式需要逐一處理每個帳號，新帳號不會自動納入，適用於沒有使用 Organizations 的情況。
>
> **考點**：SAP-1.4、SAP-1.2｜trusted access 與 delegated administrator

### 練習 14-12｜SAP｜單選｜以最少負擔建立 landing zone

Wanderly 的平台團隊只有三人，需要在兩個月內建立多帳號環境：集中保存所有帳號的 CloudTrail 與 Config 日誌、一個供資安團隊跨帳號稽核的帳號、所有使用者以單一登入進入各帳號，並讓產品團隊能自助申請新帳號，新帳號建立時自動套用 Region 限制與加密偵測規則。公司偏好 LEAST operational overhead。

哪個方案最合適？

- A. 自行以 AWS Organizations、CloudFormation StackSets、SCP 與 AWS Config 組合 landing zone，並撰寫 Lambda 處理新帳號的建立流程
- B. 部署 AWS Control Tower 建立 landing zone，使用 Log Archive 與 Audit 帳號、IAM Identity Center，啟用 Region deny 與所需的 detective controls，並以 Account Factory 讓團隊申請帳號
- C. 建立一個大型共用帳號，以 IAM Identity Center 的 permission sets 區分各產品團隊的權限
- D. 使用 AWS Service Catalog 發布一個建立 VPC 的產品，讓各團隊在既有帳號中自助建立環境

> [!answer]- 答案：B
> **A ✗** 技術上可行，彈性也最大，但所有元件與帳號建立流程都要自己開發與維護，對三人團隊的營運負擔最大。如果公司有 Control Tower 無法滿足的特殊需求，才會考慮這條路。
>
> **B ✓** Control Tower 直接提供集中日誌（Log Archive）、稽核帳號（Audit）、IAM Identity Center 整合、Region deny 與 detective controls，以及標準化的 Account Factory，正是以最少營運負擔建立 landing zone 的服務。
>
> **C ✗** 單一帳號無法提供帳號層級的隔離，也不符合「申請新帳號」的需求。
>
> **D ✗** Service Catalog 可以標準化建立資源，但不會建立帳號、集中日誌或組織層的 guardrail。
>
> **考點**：SAP-1.4、SAP-1.2｜Control Tower landing zone 與 Account Factory

### 練習 14-13｜SAP｜選兩項｜安全推出新的 SCP

Wanderly 計畫在 Workloads OU 附加一份新的 Deny 型 SCP，禁止一組被資安團隊認為高風險的服務。這個 OU 底下有 60 個 production 與 non-production 帳號，其中部分帳號的使用情況沒有完整文件。團隊希望在不中斷正式服務的前提下推出。

哪兩個做法最合適？（選兩項）

- A. 使用 IAM 的 service last accessed data 檢視 OU 與帳號最近使用過哪些服務，並在 Policy Staging OU 的代表性帳號先附加新 SCP 測試
- B. 直接把 SCP 附加到 organization root，因為 management account 可以隨時移除它
- C. 依 Sandbox、NonProd、Prod 的順序分階段附加，每階段檢查 CloudTrail 中因 SCP 造成的 AccessDenied 事件
- D. 在每個 production 帳號的管理 role 附加 AdministratorAccess，以在 SCP 擋住時繞過限制
- E. 只用 JSON 驗證工具確認政策語法正確後，就直接套用到整個 Workloads OU

> [!answer]- 答案：A、C
> **A ✓** Service last accessed data 能顯示實際依賴的服務，找出 Deny 會影響的對象；在 Policy Staging OU 先測試，可以在不影響正式帳號的情況下驗證效果。
>
> **B ✗** 附加在 root 會一次影響所有成員帳號，範圍比需求更大。Management account 確實能移除 SCP，但服務中斷已經發生。
>
> **C ✓** 分階段推出把每次的影響範圍限制在較低風險的環境，並用 CloudTrail 的拒絕事件找出遺漏的依賴，再決定是否調整政策。
>
> **D ✗** SCP 的 Deny 優先於任何 IAM Allow，AdministratorAccess 無法繞過 SCP。
>
> **E ✗** 語法正確只代表政策能被解析，不代表語意符合各帳號的實際依賴。
>
> **考點**：SAP-3.2、SAP-1.4｜SCP 的安全上線流程

### 練習 14-14｜SAP｜單選｜Allow list 策略的繼承

一家受金融法規管制的公司採用 SCP allow list 策略：已從所有節點移除 `FullAWSAccess`。Root 附加了允許 EC2、S3、RDS、CloudWatch 的 SCP；Regulated OU 附加了允許 EC2、S3、CloudWatch 的 SCP；帳號 `ledger-prod` 位於 Regulated OU 之下，帳號本身附加了允許 EC2、S3、RDS、CloudWatch 的 SCP。`ledger-prod` 的管理員擁有 AdministratorAccess，但無法建立 RDS 資料庫。

最可能的原因是什麼？

- A. AdministratorAccess 不包含 RDS 權限，需另外附加 `AmazonRDSFullAccess`
- B. 帳號層級的 SCP 會覆蓋 OU 層級的 SCP，問題出在 RDS 服務本身的配額
- C. RDS 使用 service-linked role，而 service-linked role 會受 SCP 限制，因此必須在 root 允許 `iam:CreateServiceLinkedRole`
- D. Regulated OU 的 SCP 沒有允許 RDS；allow list 策略下，路徑上每一層都必須允許該動作

> [!answer]- 答案：D
> **A ✗** AdministratorAccess 允許所有動作，包含 RDS；問題不在 IAM。
>
> **B ✗** SCP 沒有「下層覆蓋上層」的機制。有效範圍是 root、各層 OU 與帳號 SCP 的交集。
>
> **C ✗** Service-linked role 本身不受 SCP 限制；而且題目中的拒絕來自路徑上缺少 RDS 的 Allow。
>
> **D ✓** 移除 `FullAWSAccess` 後，請求必須在 root、每一層 OU 與帳號的 SCP 都被允許。Regulated OU 沒有列出 RDS，即使 root 與帳號都允許，交集中仍沒有 RDS。修正方式是在 Regulated OU 的 SCP 加入 RDS，或重新檢討這個帳號是否應該使用 RDS。
>
> **考點**：SAP-1.2、SAP-1.4｜allow list 策略與 SCP 繼承

### 練習 14-15｜SAP｜選兩項｜併購帳號移入組織

Wanderly 併購了一家旅行社，對方有自己的 AWS organization 與 12 個成員帳號，其中幾個帳號的 S3 bucket policy 使用 `aws:PrincipalOrgID` 只允許原組織的身份存取。Wanderly 希望把這 12 個帳號移入自己的 organization，納入 Control Tower 治理，並避免搬遷時中斷服務。

哪兩個做法最合適？（選兩項）

- A. 搬遷前先盤點並更新使用 `aws:PrincipalOrgID` 的 resource policy，讓新舊組織 ID 在過渡期都被允許
- B. 讓這些帳號同時屬於兩個 organization，直到所有服務驗證完成
- C. 由 Wanderly 發出邀請、帳號接受後直接移轉到 Wanderly 的 organization，先放入政策相容的過渡 OU，在帳號內建立信任 Wanderly 管理帳號的 role，評估後再 enroll 到 Control Tower 並移入正式 OU
- D. 直接把帳號放入 Prod OU，讓 Control Tower 自動修正所有不合規設定
- E. 刪除這些帳號後，由 Wanderly 的 Account Factory 重新建立同名帳號並還原資料

> [!answer]- 答案：A、C
> **A ✓** 帳號換到新 organization 後，organization ID 改變，原本以 `aws:PrincipalOrgID` 授權的請求會被拒絕。先讓新舊 ID 在過渡期都被允許，搬完再移除舊 ID，可以避免中斷。
>
> **B ✗** 一個帳號同一時間只能屬於一個 organization。
>
> **C ✓** 自 2025 年 11 月起，帳號接受新 organization 的邀請即可直接移轉，不必先離開原 organization。邀請加入的帳號不會自動建立 `OrganizationAccountAccessRole`，需要手動建立管理 role。先放在過渡 OU 避免嚴格 SCP 立刻造成中斷，確認沒有與 Control Tower baseline 衝突的設定後再 enroll，是風險最低的路徑。
>
> **D ✗** Prod OU 的嚴格 SCP 可能立即擋住現有工作負載；Control Tower 的 detective controls 只回報不合規，不會自動修正所有設定。
>
> **E ✗** 重建帳號需要搬遷所有資源，停機時間與風險都遠高於直接移轉帳號。
>
> **考點**：SAP-1.4、SAP-4.2｜併購時的帳號移轉

### 練習 14-16｜SAP｜單選｜OU 結構設計

一家企業有 120 個 AWS 帳號，目前的 OU 依部門劃分（財務、行銷、工程、客服），每個部門 OU 下都同時有 production 與 development 帳號。資安團隊要對所有 production 帳號套用相同的嚴格 SCP，結果發現要在四個 OU 重複附加，而且有些 OU 已經接近每個節點 5 個 SCP 的上限。

最合適的改善方向是什麼？

- A. 把所有 SCP 合併成一份大型 SCP 附加到 root，並用 `aws:PrincipalTag` 區分 production 與 development
- B. 依治理需求重新設計 OU：建立 Workloads OU 並在其下分為 Prod 與 NonProd，將帳號依環境移入，把 production 的 SCP 附加在 Prod OU 一次
- C. 在每個 production 帳號的 IAM role 附加 permission boundary，取代 SCP
- D. 為每個部門建立獨立的 organization，讓各部門自行管理 SCP

> [!answer]- 答案：B
> **A ✗** 單一 SCP 有 5,120 字元的大小限制，難以容納所有規則；依 principal tag 區分也讓任何能改 tag 的人有機會繞過，治理變得脆弱。
>
> **B ✓** OU 應該依「需要相同政策的帳號」來分組。把 production 帳號集中在 Prod OU，嚴格 SCP 只需附加一次，也釋放了 SCP 名額，帳號仍可用 tag 或帳號名稱保留部門資訊供帳單使用。
>
> **C ✗** Permission boundary 要附加到每個 role，帳號管理員也能修改它；它無法提供 SCP 那種帳號管理員也無法違反的集中控制。
>
> **D ✗** 拆成多個 organization 會失去統一治理、統一帳單與折扣共享，讓問題更嚴重。
>
> **考點**：SAP-1.4、SAP-3.1｜依治理需求設計 OU
