---
title: "Identity、Security 與 Governance"
part: 2
as_of: 2026-10-01
---

# Part 2　Identity、Security 與 Governance

# 第 21 章　IAM Principal、Role、Policy 與 Least Privilege

每個人與workload都需要可撤銷、可稽核且不依賴長期密鑰的權限。

## 跟著一次授權決定走：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：開發者跨三十個帳號操作，EC2與Lambda需要存取S3與DynamoDB。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：每個人與workload都需要可撤銷、可稽核且不依賴長期密鑰的權限。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：登入像出示員工證，policy像每扇門旁的門禁規則；有證件不代表所有房間都能進。 但請同時記住它的邊界：AWS授權由多層policy共同決定，還要考慮explicit Deny、resource policy與organization guardrail。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS IAM Identity Center，對照角色是IAM。我們選擇「人員用federation/Identity Center，workload用role與temporary credentials，政策只允許必要action/resource/condition。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：開發者跨三十個帳號操作，EC2與Lambda需要存取S3與DynamoDB。

人員登入
  └─ Identity Center / federation ──> temporary role session

Workload執行
  └─ EC2 / Lambda / task role ──────> temporary credentials

每次AWS API request
  principal + action + resource + context
          │
          ▼
IAM policy evaluation ── explicit Deny? ──> DENY
          │ no
          └─ 至少一個有效Allow且未超過SCP/boundary/session上限 ──> ALLOW

CloudTrail保存最後真正使用哪個identity做了什麼。

失敗時先找：將AdministratorAccess當作除錯手段後永久保留，或把access key寫入程式碼。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問AWS IAM Identity Center有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS IAM Identity Center和IAM並不是兩個任意的產品名稱。前者適合本章，是因為「人員用federation/Identity Center，workload用role與temporary credentials，政策只允許必要action/resource/condition。」直接回應了眼前的問題；後者描述的「IAM user仍可支援特殊legacy情境，但需強MFA、rotation與明確淘汰計畫。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將AdministratorAccess當作除錯手段後永久保留，或把access key寫入程式碼。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「identity is the primary security perimeter」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS IAM Identity Center | 集中管理workforce登入多個AWS accounts與business applications。 | 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 |
| IAM | 定義AWS API的principal、authentication與authorization。 | Request帶principal與context；IAM彙整identity/resource/organization/session等policy後產生Allow或Deny。 |
| AWS STS | 簽發有限時效的temporary AWS credentials。 | AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 |

## 把全圖套進一個具體案例

**場景：** 開發者跨三十個帳號操作，EC2與Lambda需要存取S3與DynamoDB。

1. 故事的起點：開發者跨三十個帳號操作，EC2與Lambda需要存取S3與DynamoDB。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS IAM Identity Center負責「集中管理workforce登入多個AWS accounts與business applications。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：IAM、AWS STS各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將AdministratorAccess當作除錯手段後永久保留，或把access key寫入程式碼。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 再往底層走：這一章真正容易混淆的地方

### 先分清 authentication 與 authorization

Authentication回答「你是誰」：例如員工透過Identity Center登入、EC2透過instance profile取得role credentials。Authorization回答「這個已驗證principal現在能做什麼」：IAM會把action、resource、request context拿去比對所有applicable policies。只建立user或role不會自動有權限；只寫policy也必須附到正確identity或resource。

### Role其實有兩道門

Trust policy是第一道門，決定誰能呼叫sts:AssumeRole；permissions policy是第二道門，決定成功扮演後能呼叫哪些API。面試或考試看到cross-account時，必須同時檢查source principal是否可AssumeRole、target role是否信任它，以及session最後是否受SCP、boundary或session policy限制。

### 人與workload不要共用credential模型

Workforce使用Identity Center/federation，取得短期role session；EC2、Lambda、ECS task使用service-integrated role；on-premises workload可用OIDC federation或IAM Roles Anywhere。長期access key只應是不得已的legacy例外，且必須有owner、rotation、monitoring與淘汰日期。

## 需要時再查：四個閱讀支點

### AWS IAM Identity Center

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：每個人與workload都需要可撤銷、可稽核且不依賴長期密鑰的權限。
- **具體例子／邊界：** 在「開發者跨三十個帳號操作，EC2與Lambda需要存取S3與DynamoDB。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### IAM

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：IAM user仍可支援特殊legacy情境，但需強MFA、rotation與明確淘汰計畫。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將AdministratorAccess當作除錯手段後永久保留，或把access key寫入程式碼。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：identity is the primary security perimeter。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### temporary credentials

具有到期時間的access key、secret與session token，通常由STS簽發，比長期key更易限制與輪替。

### least privilege

只授予完成目前工作需要的actions、resources、conditions與時間，而非先給admin再期待人工回收。

### AWS account

AWS中的資源、身份、quota與billing隔離邊界；企業通常用多帳號縮小blast radius，而不是把所有環境塞在同一帳號。

### data plane

實際處理每個packet、request、message、query與資料讀寫的runtime路徑。

### federation

讓外部IdP驗證使用者或workload，再交換AWS temporary role session，而不為每人建立獨立長期AWS密碼。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

## 回到 AWS：Components、功用與責任邊界

### AWS IAM Identity Center

- **功用：** 集中管理workforce登入多個AWS accounts與business applications。
- **底層機制：** 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。
- **關鍵設定：** identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
- **選擇時機：** 企業員工、群組生命週期與多帳號SSO。
- **替換時機：** consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。

### IAM

- **功用：** 定義AWS API的principal、authentication與authorization。
- **底層機制：** Request帶principal與context；IAM彙整identity/resource/organization/session等policy後產生Allow或Deny。
- **關鍵設定：** users/groups/roles、managed/inline policies、MFA、access keys、credential report與Access Analyzer。
- **選擇時機：** 所有AWS control/data plane存取；人員優先federation，workload優先role。
- **替換時機：** 應用程式內部細粒度授權可用Verified Permissions；網路可達性不是IAM替代品。

### AWS STS

- **功用：** 簽發有限時效的temporary AWS credentials。
- **底層機制：** AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。
- **關鍵設定：** role ARN、session name、duration、external ID、source identity、session tags與session policy。
- **選擇時機：** cross-account、federation、workload identity與避免長期access keys。
- **替換時機：** 不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。

## 考前與實作時再查：設定操作手冊

### AWS IAM Identity Center：逐項設定說明

#### `identity source`

- **控制什麼：** `identity source`指定AWS IAM Identity Center讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `permission sets`

- **控制什麼：** `permission sets`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `assignments`

- **控制什麼：** `assignments`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `session duration`

- **控制什麼：** `session duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS IAM Identity Center的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `MFA`

- **控制什麼：** `MFA`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `SCIM`

- **控制什麼：** `SCIM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `delegated administration`

- **控制什麼：** `delegated administration`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

### IAM：逐項設定說明

#### `users/groups/roles`

- **控制什麼：** `users/groups/roles`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `managed/inline policies`

- **控制什麼：** `managed/inline policies`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `MFA`

- **控制什麼：** `MFA`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `access keys`

- **控制什麼：** `access keys`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `credential report`

- **控制什麼：** `credential report`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `Access Analyzer`

- **控制什麼：** `Access Analyzer`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「所有AWS control/data plane存取；人員優先federation，workload優先role。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

### AWS STS：逐項設定說明

#### `role ARN`

- **控制什麼：** `role ARN`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS STS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `session name`

- **控制什麼：** `session name`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `duration`

- **控制什麼：** `duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS STS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `external ID`

- **控制什麼：** `external ID`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `source identity`

- **控制什麼：** `source identity`指定AWS STS讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `session tags`

- **控制什麼：** `session tags`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `session policy`

- **控制什麼：** `session policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS STS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

## 可以直接對照 AWS 的設定範例

### EC2 workload role：誰可以 AssumeRole（trust policy）

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

1. Principal是EC2 service，表示只有EC2 service principal可取得這個role session。
2. Trust policy不包含s3:GetObject；它只控制誰能扮演role。
3. EC2還需instance profile把role掛到instance，application再從metadata endpoint取得temporary credentials。

### 扮演後可以做什麼（permissions policy）

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadOnlyApplicationPrefix",
    "Effect": "Allow",
    "Action": ["s3:GetObject"],
    "Resource": "arn:aws:s3:::acme-prod-artifacts/app/*"
  }]
}
```

1. Identity policy省略Principal，因為principal就是附加此policy的role。
2. GetObject是object-level action，所以Resource必須包含/app/*，不能只寫bucket ARN。
3. 沒有ListBucket仍可讀已知object key；若app需要列舉，再另加bucket ARN與s3:prefix condition。

## 讀到這裡，請用自己的話說一次

1. AWS IAM Identity Center的責任：集中管理workforce登入多個AWS accounts與business applications。
2. 底層機制：連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。
3. 第一個要看的設定：identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
4. 選擇邏輯：人員用federation/Identity Center，workload用role與temporary credentials，政策只允許必要action/resource/condition。
5. 不要混淆：IAM的責任是「定義AWS API的principal、authentication與authorization。」；它不會自動取代AWS IAM Identity Center。
6. 替換訊號：consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。
7. 最常見錯法：將AdministratorAccess當作除錯手段後永久保留，或把access key寫入程式碼。
8. 可移植原則：identity is the primary security perimeter。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS IAM Identity Center | 集中管理workforce登入多個AWS accounts與business applications。 | 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 | 企業員工、群組生命週期與多帳號SSO。 | consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。 |
| IAM | 定義AWS API的principal、authentication與authorization。 | Request帶principal與context；IAM彙整identity/resource/organization/session等policy後產生Allow或Deny。 | 所有AWS control/data plane存取；人員優先federation，workload優先role。 | 應用程式內部細粒度授權可用Verified Permissions；網路可達性不是IAM替代品。 |
| AWS STS | 簽發有限時效的temporary AWS credentials。 | AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 | cross-account、federation、workload identity與避免長期access keys。 | 不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | IAM user仍可支援特殊legacy情境，但需強MFA、rotation與明確淘汰計畫。 | 只有當題目條件明確改變時才可能合理。 | 將AdministratorAccess當作除錯手段後永久保留，或把access key寫入程式碼。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「IAM user仍可支援特殊legacy情境，但需強MFA、rotation與明確淘汰計畫。」之間做選擇。
- 認得常考設定：identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜Human and workload principal separation

一家公司的工程師要從公司 IdP 登入 24 個 AWS 帳號；其中一台 EC2 上的報表程式只需讀取 s3://acme-data/reports/。哪個設計同時避免人員與程式使用長期憑證，且最符合 least privilege？

A. 工程師透過 IAM Identity Center 取得短期 role session；EC2 使用 instance profile 中的專用 role，僅允許 reports/* 的 s3:GetObject
B. 在每個帳號建立同名 IAM user，並把其中一組 access key 放進 EC2 的 Secrets Manager secret
C. 讓 EC2 使用工程師登入後匯出的 temporary credentials，並每天由排程更新
D. 為報表 bucket 開啟 public read，再用 security group 限制 EC2 的來源 IP

**答案：A**

- **A：** 正確。員工由 Identity Center 的 account assignment 取得 workforce role session；EC2 則經 instance profile 與 IMDS credential provider取得自動輪替的 workload credentials。S3 statement只授權 reports/* object ARN，沒有把人的 session借給程式。
- **B：** 不正確。Secrets Manager只是在保存永久 access key，沒有把它轉成 workload identity；每帳號 IAM user也會把入離職、MFA與撤權分散。只有無法支援 role 的短期 legacy migration才可能暫用並嚴格輪替。
- **C：** 不正確。人的 temporary session受互動登入與到期時間控制，借給常駐程式會混淆 CloudTrail attribution並造成不可預期中斷。若題幹是工程師的一次性 CLI工作，才可使用自己的 workforce session。
- **D：** 不正確。S3 bucket不套用EC2 security group；public read也把具名principal的授權邊界移除。只有真正公開的內容才應透過CloudFront或受控public endpoint發布。

**事實查證：** [Assign user or group access to AWS accounts](https://docs.aws.amazon.com/singlesignon/latest/userguide/assignusers.html)、[Manage AWS accounts with permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)、[Use instance profiles for Amazon EC2](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html)、[IMDS credential provider](https://docs.aws.amazon.com/sdkref/latest/guide/feature-imds-credentials.html)、[Actions, resources, and condition keys for Amazon S3](https://docs.aws.amazon.com/service-authorization/latest/reference/list_s3.html)

### 練習題 2｜SAA｜Action and resource granularity

一個 role 必須能列出 acme-data bucket 中 reports/ 下的 keys，並讀取該 prefix 的 objects；其他 prefix 不可見也不可讀。哪組 policy 配置正確？

A. 允許 s3:* 到 bucket 與所有 objects，並依靠應用程式只讀 reports/
B. 將 s3:ListBucket 與 s3:GetObject 都套用到 arn:aws:s3:::acme-data/reports/*
C. 以 bucket ARN 允許 s3:ListBucket 並加 s3:prefix=reports/*；另以 object ARN arn:aws:s3:::acme-data/reports/* 允許 s3:GetObject
D. 將兩個 actions 都套用到 arn:aws:s3:::acme-data，再用 role 名稱作 Condition

**答案：C**

- **A：** 不正確。s3:*包含寫入、刪除與policy相關操作，應用程式自律不是authorization boundary。只有經審核的bucket管理角色才可能需要如此廣的Action與Resource。
- **B：** 不正確。s3:ListBucket 的資源型別是 bucket，object ARN不匹配；因此即使 GetObject可用，列舉仍會 AccessDenied。若只授權object讀取而不需要LIST，才可省略bucket statement。
- **C：** 正確。最小形狀是第一段 Effect Allow、Action s3:ListBucket、Resource arn:aws:s3:::acme-data、Condition StringLike s3:prefix=reports/*；第二段允許 s3:GetObject 到 arn:aws:s3:::acme-data/reports/*。
- **D：** 不正確。Bucket ARN可授權ListBucket，卻不能取代GetObject所需的object ARN；role名稱也不限制key prefix。只有題幹允許列出整個bucket且不讀object時，單一bucket statement才足夠。

**事實查證：** [Actions, resources, and condition keys for Amazon S3](https://docs.aws.amazon.com/service-authorization/latest/reference/list_s3.html)、[Amazon S3 policy condition key examples](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html)

### 練習題 3｜SAA｜Role versus instance profile

團隊已建立 trust policy 信任 ec2.amazonaws.com 的 AppReadRole，也附上正確 S3 permissions policy；但 EC2 內的 AWS SDK 回報找不到 credentials。最可能缺少哪個步驟？

A. 把 role ARN 加進 instance 的 security group outbound rule
B. 建立包含 AppReadRole 的 instance profile，並將它關聯到該 EC2 instance
C. 把 permissions policy 烘焙進 AMI 的 /etc/aws/credentials
D. 使用帳號 root access key 從 instance 呼叫 sts:AssumeRole

**答案：B**

- **A：** 不正確。Security group控制網路封包，不會把IAM role呈現給instance。只有IMDS或AWS endpoint網路真的被阻擋時，才另外排查network path。
- **B：** 正確。EC2使用instance profile作為role容器，instance關聯profile後，SDK的IMDS provider才能取得短期role credentials。一台instance同時只關聯一個instance profile，而該profile依現行IAM模型包含一個role。
- **C：** 不正確。把credentials烘焙進AMI會被所有副本繼承且難以輪替；permissions policy本身也不是credential provider。Legacy軟體仍應透過SDK、credential process或受控broker取得短期憑證。
- **D：** 不正確。Root access key不應交給workload，且EC2服務可直接為已關聯role建立session。Root只保留少數root-only recovery，不是啟動應用程式credential chain的方式。

**事實查證：** [Use instance profiles for Amazon EC2](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html)、[IMDS credential provider](https://docs.aws.amazon.com/sdkref/latest/guide/feature-imds-credentials.html)、[IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)

### 練習題 4｜SAA｜Service role and iam:PassRole

CI operator 有 lambda:CreateFunction，準備讓新函式使用既有 ApprovedLambdaRole。CreateFunction 回傳 AccessDenied；該 role 已正確信任 Lambda service。應最小幅度增加什麼權限？

A. 讓 ApprovedLambdaRole 的 trust policy 信任 CI operator，而不是 Lambda
B. 在 ApprovedLambdaRole 加入 lambda:*，讓 role 能建立自己
C. 授予 CI operator 對所有 roles 的 sts:AssumeRole
D. 授予 CI operator 對 ApprovedLambdaRole 的 iam:PassRole，並可用 iam:PassedToService 限制為 lambda.amazonaws.com

**答案：D**

- **A：** 不正確。Lambda 必須能 assume execution role；把 trust 改成部署者會破壞執行路徑。部署者通常不需要扮演該 role。
- **B：** 不正確。Execution role 的 permissions 決定函式執行後可做什麼，不授權部署者把 role 傳給服務。若函式本身要呼叫 Lambda API，才需相應 action。
- **C：** 不正確。AssumeRole 與 PassRole 是不同 authorization；允許部署者扮演所有 roles 還會擴大 privilege escalation 風險。
- **D：** 正確。PassRole 檢查的是呼叫服務 API 的 principal 是否可把指定 role 交給該服務。限制 role ARN 與 PassedToService 能避免任意傳遞高權限 role。

**事實查證：** [Grant a user permissions to pass a role to an AWS service](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html)、[AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)

### 練習題 5｜SAA｜Policy statement matching and implicit deny

一個 role 的 policy Allow dynamodb:GetItem，但 Resource 寫成 us-east-1、帳號 111122223333 的 table ARN。程式實際讀取 ap-southeast-1、同帳號的同名 table，且沒有其他 Allow。結果為何？

A. 由 statement 在 JSON 中的先後順序決定
B. 被拒絕，因為 Allow 的 Resource 不匹配實際 request，最後仍是 implicit deny
C. 被允許，因為同名 table 會視為同一 logical resource
D. 被允許，因為 Action 匹配時 AWS 會自動修正 Region

**答案：B**

- **A：** 不正確。IAM evaluation 不是 first-match ACL；statement 順序不建立優先權，適用的 explicit Deny 仍會覆蓋 Allow。
- **B：** 正確。Effect、Action、Resource 與 Condition 都必須符合 request；不存在適用的 Allow 時即 implicit deny。修正應使用正確 ARN，而非反覆重試。
- **C：** 不正確。ARN 中的 Region、account 與 resource identifier 都是授權比對的一部分；名稱相同不建立跨區授權。
- **D：** 不正確。IAM 不會推測或改寫 ARN。若 API 本身是區域無關且文件指定特殊 ARN 形式，才依該服務規則撰寫。

**事實查證：** [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 6｜SAA｜MFA-protected sensitive operation

安全團隊要讓管理員平時能管理 EC2，但只有在目前 session 已完成 MFA 時才能呼叫 ec2:TerminateInstances。哪個方法最直接表達此授權條件？

A. 只允許公司 CIDR；來自公司網路即等同 MFA
B. 要求 IAM user 註冊 MFA 裝置，但 policy 不檢查目前 request context
C. 將 EC2 instances 加密，因為加密會阻止 termination
D. 在相關 IAM policy 使用 MFA request context condition（例如 aws:MultiFactorAuthPresent），並測試實際 federation/session context

**答案：D**

- **A：** 不正確。網路來源不是第二因素，遭入侵的公司主機仍可發出 request。Source IP 可作額外條件，不能取代 authentication。
- **B：** 不正確。已註冊裝置不表示這次 session 使用了 MFA；若只要求帳號層註冊，未達成「本次操作」條件。
- **C：** 不正確。Encryption 保護資料機密性，不是 EC2 lifecycle authorization。若需求是防止誤刪，還可搭配 termination protection，但仍需 IAM。
- **D：** 正確。Condition 能讓敏感 action 依當次 request 的 MFA context 判斷；federated identity 的 MFA 資訊與條件可用性必須在選定流程中實測。

**事實查證：** [AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 7｜SAP｜Least privilege from usage evidence

一個 migration role 在專案初期被授予廣泛權限。遷移穩定運行 60 天後，團隊要縮小權限且降低一次性刪錯 action 的風險。最佳流程是什麼？

A. 維持 AdministratorAccess，因為 60 天內沒有事故
B. 每天隨機移除數個 actions，直到 production 失敗再加回
C. 使用 CloudTrail 與 IAM Access Analyzer policy generation/last-accessed evidence 產生候選政策，於測試與分階段 rollout 驗證後收斂
D. 改用所有工程師共用的 IAM user，以便只有一份 policy

**答案：C**

- **A：** 不正確。沒有事故不證明未使用權限是必要的；長期保留廣泛權限增加 credential compromise 的 blast radius。
- **B：** 不正確。Production trial-and-error 缺乏可重現證據，可能在罕見流程才暴露缺權。故障注入可用，但應先在非正式環境與有觀測性的 rollout 執行。
- **C：** 正確。實際 API 使用證據能建立較可靠的候選 policy；仍需涵蓋季節性/災難流程並分階段測試，因為觀測窗不保證看過所有必要 actions。
- **D：** 不正確。共享 user 降低 attribution 並引入永久 credentials，沒有改善 permission scope。集中 policy 可用 managed policy，不需共享 identity。

**事實查證：** [IAM Access Analyzer policy generation](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-generation.html)

### 練習題 8｜SAA｜Service-linked role recognition

啟用某 AWS managed service 後，帳號自動出現 AWSServiceRoleForExample。應如何處理這個 role？

A. 辨識它是由該服務擁有的 service-linked role；不要改作其他用途，刪除前先移除依賴該 role 的服務資源
B. 將它附加到 organization root，作為 SCP 使用
C. 刪除它以減少 role 數量；服務會永遠沿用建立者權限
D. 把它改為公司共用 application role，並加入工程師 principals

**答案：A**

- **A：** 正確。Service-linked role 讓指定 AWS service 代表客戶執行必要動作，通常由服務管理權限並保護依賴關係。
- **B：** 不正確。SCP 是 Organizations policy，不是 IAM role。兩者附加位置與 evaluation 模型不同。
- **C：** 不正確。服務不會繼承建立者的日常權限；AWS 通常會阻止仍有依賴資源時刪除此 role。只有停用相關功能後才評估刪除。
- **D：** 不正確。Service-linked role 的 trust/permissions 與特定服務生命週期綁定，不應承載人員或應用程式權限。

**事實查證：** [IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)

### 練習題 9｜SAA｜IAM group limitations

團隊希望讓 40 名工程師與一組 EC2 instances 共用相同的 read-only policy。哪兩項敘述正確？（選兩項）

A. IAM groups 可以巢狀加入另一個 group，適合反映組織圖
B. EC2 workload 應使用 role/instance profile；需要相同 actions 時可將同一 managed policy 另附到 role
C. Resource-based policy 可以附到 IAM group，並自動成為所有服務的 resource policy
D. 可把 IAM users 放入 group，再將 reusable managed policy 附到 group
E. 可把 EC2 instance profile 加入同一 IAM group

**答案：B、D**

- **A：** 不正確。IAM groups不支援巢狀，因此不能直接複製企業組織圖。需要群組同步與生命週期時，應由外部IdP與Identity Center管理workforce groups。
- **B：** 正確。Managed policy可同時附到group與role，所以能重用actions而不共用principal。人員與EC2仍有不同session、撤權流程與CloudTrail identity。
- **C：** 不正確。Resource-based policy附在支援該機制的S3 bucket、SQS queue等resource上，不能附到IAM group；各服務支援的Principal與Condition也不同。
- **D：** 正確。IAM group只能聚合IAM users；把customer-managed policy附到group可重用權限集合，但每個user仍是獨立principal並保留個別稽核。
- **E：** 不正確。IAM group不能包含roles或instance profiles；EC2必須透過自己的workload role取得credentials。若只是想重用同一組actions，可把同一managed policy另附到role。

**事實查證：** [IAM user groups](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_groups.html)、[Identity-based policies and resource-based policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html)

### 練習題 10｜SAP｜Emergency access without shared permanent credentials

公司的主要外部 IdP 完全中斷時，值班人員仍需在 production 執行少量修復。哪兩項最能建立不依賴該 IdP、可控且可稽核的 break-glass 路徑？（選兩項）

A. 平時關閉 CloudTrail，等啟用緊急身份後再打開以降低成本
B. 把 root access keys 長期放在所有工程師可讀的密碼庫，事故時直接使用
C. 預建由獨立 credential root 啟動的 emergency path，例如受雙人保管、要求硬體 MFA 的少數 IAM emergency identity，只能 assume 權限受限且有短 session 的修復 role
D. 只預建 production emergency role，但仍要求由故障中的同一 IdP federation 才能 assume
E. 建立定期演練的 activation/recovery runbook：雙人核准、即時告警、使用後 revoke sessions、輪替 emergency credentials並完成事後審查；root只用於root-only recovery

**答案：C、E**

- **A：** 不正確。事故期間最需要CloudTrail與告警保留責任歸屬；若成本或容量有壓力，應隔離與保護logging pipeline，而不是在高風險操作前關閉證據。
- **B：** 不正確。共享root key具有organization級blast radius且沒有個人歸屬；root應以硬體MFA嚴格保管，只處理無法委派的root-only工作，不作日常或一般break-glass admin。
- **C：** 正確。第一組可用credentials必須位於與主要IdP不同的故障域；再以MFA、custodian、受限trust policy、短session與最小修復actions縮小暴露面。
- **D：** 不正確。Role本身不是登入起點；若唯一可assume它的credential source仍是故障IdP，事故時仍無法取得STS session。改用獨立emergency identity或另一條獨立federation path才有韌性。
- **E：** 正確。Break-glass不只是一個role，還包括可用的credential bootstrap、啟用條件、監控、回收與重設。定期演練能在真正故障前發現MFA、trust或runbook失效。

**事實查證：** [Set up emergency access to the AWS Management Console](https://docs.aws.amazon.com/singlesignon/latest/userguide/emergency-access.html)、[Revoke IAM role temporary security credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_revoke-sessions.html)、[SAP-C02 Domain 1: Design Solutions for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「人員用federation/Identity Center，workload用role與temporary…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「每個人與workload都需要可撤銷、可稽核且不依賴長期密鑰的權限。」，所以「人員用federation/Identity Center，workload用role與temporary credentials，政策只允許必要action/resource/condition。」能直接滿足它；若constraint改成「IAM user仍可支援特殊legacy情境，但需強MFA、rotation與明確淘汰計畫。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「人員用federation/Identity Center，workload用role與temporary credentials，政策只允許必要action/resource/condition。」。替代方案「IAM user仍可支援特殊legacy情境，但需強MFA、rotation與明確淘汰計畫。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將AdministratorAccess當作除錯手段後永久保留，或把access key寫入程式碼。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「每個人與workload都需要可撤銷、可稽核且不依賴長期密鑰的權限。」，排除會導致「將AdministratorAccess當作除錯手段後永久保留，或把access key寫入程式碼。」的選項，再選「人員用federation/Identity Center，workload用role與temporary credentials，政策只允許必要action/resource/condition。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「人員用federation/Identity Center，workload用role與temporary credentials，政策只允許必要action/resource/condition。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「identity is the primary security perimeter」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 22 章　IAM Policy Evaluation Logic

同一request可能同時受identity、resource、boundary、SCP、session與KMS policy影響。

## 跟著一次授權決定走：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：Role允許kms:Decrypt，但KMS key policy與SCP讓request仍被拒絕。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：同一request可能同時受identity、resource、boundary、SCP、session與KMS policy影響。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，登入像出示員工證，policy像每扇門旁的門禁規則；有證件不代表所有房間都能進。 AWS授權由多層policy共同決定，還要考慮explicit Deny、resource policy與organization guardrail。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看IAM policies如何接手工作，再看Service control policies何時更合適，最後用設定與考題驗證「先確認implicit deny，再找applicable allow，任何explicit deny都勝出，最後檢查交集型邊界。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Role允許kms:Decrypt，但KMS key policy與SCP讓request仍被拒絕。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[IAM policies] ── Allow / Deny ──> protected resource
          │ 用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · Service control policies：在Organizations中設定member account principals的最大權限邊界。
  · Permissions boundaries：限制單一IAM user/role可被identity policies授予的最大權限。
  · AWS KMS：管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。

失敗時先找：只看到identity allow就判斷可存取，漏掉SCP、permissions boundary或key policy deny。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問IAM policies有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，IAM policies和Service control policies並不是兩個任意的產品名稱。前者適合本章，是因為「先確認implicit deny，再找applicable allow，任何explicit deny都勝出，最後檢查交集型邊界。」直接回應了眼前的問題；後者描述的「Policy Simulator可協助，但resource context與某些service-specific policy仍需真實驗證。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只看到identity allow就判斷可存取，漏掉SCP、permissions boundary或key policy deny。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「authorization is an intersection of independent guardrails」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| IAM policies | 用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。 | Statements先匹配action/resource/principal/context；implicit deny為預設，任何applicable explicit deny勝出。 |
| Service control policies | 在Organizations中設定member account principals的最大權限邊界。 | SCP與identity/resource allow形成交集；它不授權，explicit deny可阻止member account root。 |
| Permissions boundaries | 限制單一IAM user/role可被identity policies授予的最大權限。 | Effective identity permissions是identity allow與boundary allow的交集，且仍受SCP與explicit deny。 |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 |

## 把全圖套進一個具體案例

**場景：** Role允許kms:Decrypt，但KMS key policy與SCP讓request仍被拒絕。

1. 故事的起點：Role允許kms:Decrypt，但KMS key policy與SCP讓request仍被拒絕。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：IAM policies負責「用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Statements先匹配action/resource/principal/context；implicit deny為預設，任何applicable explicit deny勝出。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Service control policies、Permissions boundaries、AWS KMS各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只看到identity allow就判斷可存取，漏掉SCP、permissions boundary或key policy deny。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要把「誰可存取」附在S3/KMS/SQS等資源上時使用resource policy。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 再往底層走：這一章真正容易混淆的地方

### Policy不是由上到下執行的程式

AWS會找出所有與request相關的statements。沒有Allow是implicit deny；只要任何一份applicable policy出現explicit Deny，結果立刻是Deny。Identity policy與同帳號resource policy常形成permission union，但boundary、session policy、SCP與RCP通常是限制上限，不能拿來授權。

### Cross-account為何常需要兩邊都設定

來源帳號要允許principal發出action，目標資源或role trust也要接受這個外部principal。例如Account A role讀Account B S3 bucket：A端identity policy允許s3:GetObject，B端bucket policy允許該role principal；任一側缺少或被explicit Deny覆蓋都會失敗。

### 除錯順序

先確認caller identity與resource ARN，再查CloudTrail error context；接著依序檢查identity policy、resource policy、permissions boundary、session policy、SCP/RCP、VPC endpoint policy及service-specific policy（如KMS key policy）。Policy Simulator有幫助，但不能完全取代真實request。

## 需要時再查：四個閱讀支點

### IAM policies

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：同一request可能同時受identity、resource、boundary、SCP、session與KMS policy影響。
- **具體例子／邊界：** 在「Role允許kms:Decrypt，但KMS key policy與SCP讓request仍被拒絕。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Service control policies

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Policy Simulator可協助，但resource context與某些service-specific policy仍需真實驗證。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只看到identity allow就判斷可存取，漏掉SCP、permissions boundary或key policy deny。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：authorization is an intersection of independent guardrails。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### envelope encryption

先用data key加密大量資料，再用KMS key加密較小的data key；避免每個資料block都直接呼叫KMS。

### least privilege

只授予完成目前工作需要的actions、resources、conditions與時間，而非先給admin再期待人工回收。

### explicit Deny

明確拒絕request的policy結果；只要任一applicable policy命中Deny，就會覆蓋Allow。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### data key

實際加密application資料的對稱key；通常只在記憶體中短暫使用，儲存的是被KMS key加密後的副本。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### IAM policies

- **功用：** 用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。
- **底層機制：** Statements先匹配action/resource/principal/context；implicit deny為預設，任何applicable explicit deny勝出。
- **關鍵設定：** Version、Statement、Sid、Effect、Action/NotAction、Resource/NotResource、Principal與Condition。
- **選擇時機：** 可用明確ARN與conditions表達least privilege時。
- **替換時機：** 需要把「誰可存取」附在S3/KMS/SQS等資源上時使用resource policy。

### Service control policies

- **功用：** 在Organizations中設定member account principals的最大權限邊界。
- **底層機制：** SCP與identity/resource allow形成交集；它不授權，explicit deny可阻止member account root。
- **關鍵設定：** target root/OU/account、Allow-list或Deny-list strategy、conditions、NotAction與policy inheritance。
- **選擇時機：** 禁止離開核准Region、關閉audit、使用未核准服務等organization guardrails。
- **替換時機：** 應用角色的日常權限用IAM；資源對外access的中央邊界可用RCP。

### Permissions boundaries

- **功用：** 限制單一IAM user/role可被identity policies授予的最大權限。
- **底層機制：** Effective identity permissions是identity allow與boundary allow的交集，且仍受SCP與explicit deny。
- **關鍵設定：** managed policy ARN、iam:PermissionsBoundary creation condition與防止移除boundary的guardrail。
- **選擇時機：** 平台委派團隊建立roles，但不允許超出安全上限。
- **替換時機：** 跨全組織限制用SCP；對資源本身授權用resource policy。

### AWS KMS

- **功用：** 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
- **底層機制：** Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。
- **關鍵設定：** key policy、grants、aliases、rotation、multi-Region keys、encryption context與key spec/usage。
- **選擇時機：** S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。
- **替換時機：** 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。

## 考前與實作時再查：設定操作手冊

### IAM policies：逐項設定說明

#### `Version`

- **控制什麼：** `Version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「可用明確ARN與conditions表達least privilege時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM policies鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `Statement`

- **控制什麼：** `Statement`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `Sid`

- **控制什麼：** `Sid`是policy statement識別、API action/resource配對，或保護permissions boundary不被委派管理者繞過的設定。
- **何時需要：** 要寫可review的IAM/S3 least-privilege policy，或允許團隊建role但不能突破平台上限時。
- **怎麼設定／驗證：** Sid使用可讀名稱；Action配正確resource ARN。ListBucket使用bucket ARN，GetObject使用object ARN；以condition/SCP拒絕移除核准boundary。
- **常見錯法：** Sid不影響授權；bucket/object ARN配反會AccessDenied。只附boundary卻允許建立者移除它，等於沒有安全上限。

#### `Effect`

- **控制什麼：** `Effect`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `Action/NotAction`

- **控制什麼：** `Action/NotAction`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `Resource/NotResource`

- **控制什麼：** `Resource/NotResource`指定IAM policies讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Principal`

- **控制什麼：** `Principal`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「可用明確ARN與conditions表達least privilege時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM policies明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `Condition`

- **控制什麼：** `Condition`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「可用明確ARN與conditions表達least privilege時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM policies以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

### Service control policies：逐項設定說明

#### `target root/OU/account`

- **控制什麼：** `target root/OU/account`指定Service control policies讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Allow-list或Deny-list strategy`

- **控制什麼：** `Allow-list或Deny-list strategy`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `conditions`

- **控制什麼：** `conditions`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「禁止離開核准Region、關閉audit、使用未核准服務等organization guardrails。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Service control policies以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `NotAction`

- **控制什麼：** `NotAction`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `policy inheritance`

- **控制什麼：** `policy inheritance`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「禁止離開核准Region、關閉audit、使用未核准服務等organization guardrails。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Service control policies明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

### Permissions boundaries：逐項設定說明

#### `managed policy ARN`

- **控制什麼：** `managed policy ARN`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「平台委派團隊建立roles，但不允許超出安全上限。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Permissions boundaries明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `iam:PermissionsBoundary creation condition`

- **控制什麼：** `iam:PermissionsBoundary creation condition`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「平台委派團隊建立roles，但不允許超出安全上限。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Permissions boundaries明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `防止移除boundary的guardrail`

- **控制什麼：** `防止移除boundary的guardrail`是policy statement識別、API action/resource配對，或保護permissions boundary不被委派管理者繞過的設定。
- **何時需要：** 要寫可review的IAM/S3 least-privilege policy，或允許團隊建role但不能突破平台上限時。
- **怎麼設定／驗證：** Sid使用可讀名稱；Action配正確resource ARN。ListBucket使用bucket ARN，GetObject使用object ARN；以condition/SCP拒絕移除核准boundary。
- **常見錯法：** Sid不影響授權；bucket/object ARN配反會AccessDenied。只附boundary卻允許建立者移除它，等於沒有安全上限。

### AWS KMS：逐項設定說明

#### `key policy`

- **控制什麼：** `key policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `grants`

- **控制什麼：** `grants`指定誰能使用、管理或接受AWS KMS的resource/contract，是delegated ownership與authorization的一部分。
- **何時需要：** 跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。
- **怎麼設定／驗證：** 使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。
- **常見錯法：** 信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。

#### `aliases`

- **控制什麼：** `aliases`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `rotation`

- **控制什麼：** `rotation`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `multi-Region keys`

- **控制什麼：** `multi-Region keys`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS KMS前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `encryption context`

- **控制什麼：** `encryption context`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `key spec/usage`

- **控制什麼：** `key spec/usage`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。
- **何時需要：** TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。
- **怎麼設定／驗證：** 選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。
- **常見錯法：** 錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。

## 可以直接對照 AWS 的設定範例

### Permissions boundary：允許開發role，但禁止IAM與Organizations

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "NotAction": ["iam:*", "organizations:*", "account:*"],
      "Resource": "*"
    }
  ]
}
```

1. Boundary本身不授權；role仍需要identity policy Allow。
2. 若identity policy給AdministratorAccess，effective permissions仍只能落在boundary Allow範圍。
3. Production還要防止建立者移除/替換boundary，通常用iam:PermissionsBoundary condition與SCP。

### 把 boundary 實際附到 delegated role（CloudFormation）

```yaml
Resources:
  ApplicationBoundary:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: application-team-boundary
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            NotAction: ["iam:*", "organizations:*", "account:*"]
            Resource: "*"
  ApplicationDeployRole:
    Type: AWS::IAM::Role
    Properties:
      PermissionsBoundary: !Ref ApplicationBoundary
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              AWS: arn:aws:iam::111122223333:role/PlatformPipeline
            Action: sts:AssumeRole

```

1. PermissionsBoundary欄位把managed policy ARN附到role；它限制之後附加的identity policies可以產生的最大權限。
2. Trust policy只允許PlatformPipeline取得session，並沒有授予部署actions；role仍需另外附上精確permissions policy。
3. 委派建立role時還要以iam:PermissionsBoundary condition強制使用核准boundary，並拒絕未授權的移除或替換。

## 讀到這裡，請用自己的話說一次

1. IAM policies的責任：用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。
2. 底層機制：Statements先匹配action/resource/principal/context；implicit deny為預設，任何applicable explicit deny勝出。
3. 第一個要看的設定：Version、Statement、Sid、Effect、Action/NotAction、Resource/NotResource、Principal與Condition。
4. 選擇邏輯：先確認implicit deny，再找applicable allow，任何explicit deny都勝出，最後檢查交集型邊界。
5. 不要混淆：Service control policies的責任是「在Organizations中設定member account principals的最大權限邊界。」；它不會自動取代IAM policies。
6. 替換訊號：需要把「誰可存取」附在S3/KMS/SQS等資源上時使用resource policy。
7. 最常見錯法：只看到identity allow就判斷可存取，漏掉SCP、permissions boundary或key policy deny。
8. 可移植原則：authorization is an intersection of independent guardrails。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| IAM policies | 用JSON描述Effect、Action、Resource與Condition，控制principal可做什麼。 | Statements先匹配action/resource/principal/context；implicit deny為預設，任何applicable explicit deny勝出。 | 可用明確ARN與conditions表達least privilege時。 | 需要把「誰可存取」附在S3/KMS/SQS等資源上時使用resource policy。 |
| Service control policies | 在Organizations中設定member account principals的最大權限邊界。 | SCP與identity/resource allow形成交集；它不授權，explicit deny可阻止member account root。 | 禁止離開核准Region、關閉audit、使用未核准服務等organization guardrails。 | 應用角色的日常權限用IAM；資源對外access的中央邊界可用RCP。 |
| Permissions boundaries | 限制單一IAM user/role可被identity policies授予的最大權限。 | Effective identity permissions是identity allow與boundary allow的交集，且仍受SCP與explicit deny。 | 平台委派團隊建立roles，但不允許超出安全上限。 | 跨全組織限制用SCP；對資源本身授權用resource policy。 |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 | S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。 | 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Policy Simulator可協助，但resource context與某些service-specific policy仍需真實驗證。 | 只有當題目條件明確改變時才可能合理。 | 只看到identity allow就判斷可存取，漏掉SCP、permissions boundary或key policy deny。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Policy Simulator可協助，但resource context與某些service-specific policy仍需真實驗證。」之間做選擇。
- 認得常考設定：Version、Statement、Sid、Effect、Action/NotAction、Resource/NotResource、Principal與Condition。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要把「誰可存取」附在S3/KMS/SQS等資源上時使用resource policy。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜Explicit Deny precedence

Member account 的 DeploymentRole 有 AdministratorAccess，但上層 OU 的 SCP 明確 Deny 在 eu-west-1 呼叫 ec2:RunInstances，且沒有可適用的 SCP 例外。該 role 在 eu-west-1 建立 instance 時會發生什麼？

A. 被拒絕；適用的 SCP explicit Deny 會否決 identity policy 的 Allow，必須由組織管理者調整 guardrail或改到允許的Region
B. 由 EC2 instance profile 的 permissions boundary決定
C. 只要改用 CloudFormation，SCP 就不再參與授權
D. 被允許，因為 AdministratorAccess 的 Allow 比 SCP 更具體

**答案：A**

- **A：** 正確。AdministratorAccess仍受SCP上限限制；這是explicit Deny跨policy類型優先的例子。修復點在OU/SCP scope或部署Region，而不是替role再加一份Allow。
- **B：** 不正確。Instance profile是建立後workload的identity，不決定部署者能否呼叫RunInstances；即使DeploymentRole沒有boundary，SCP Deny仍然成立。
- **C：** 不正確。CloudFormation最終仍代表principal或service role呼叫EC2 API，適用的SCP不會因工具不同而消失；只有改用不受該Deny影響且被允許的principal/scope才可能改變結果。
- **D：** 不正確。IAM不採「較具體Allow勝出」；SCP的適用explicit Deny會在organization ceiling直接否決request。只有SCP條件不匹配或有經設計的例外時，identity Allow才可能生效。

**事實查證：** [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)、[Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)

### 練習題 2｜SAP｜Same-account resource grant to role ARN

同帳號 bucket policy 的 Principal 是 arn:aws:iam::111122223333:role/ReportRole，允許 GetObject；ReportRole 的 identity policy 沒有 S3，permissions boundary 也沒有 s3:GetObject。沒有 explicit Deny。結果為何？

A. 只有把 boundary 改成 explicit Deny 才可能拒絕
B. 拒絕；授權給 role ARN 的同帳號 resource-policy grant 仍受該 role permissions boundary 的 implicit deny 限制
C. 一定允許，因為任何 resource-policy Allow 都能繞過 boundary
D. 一定拒絕，因為 bucket policy 不可指定 role ARN

**答案：B**

- **A：** 不正確。Boundary 是 maximum permissions，缺少 Allow 已足以形成 implicit deny；不必加入 explicit Deny 才有效。
- **B：** 正確。AWS 文件明確區分 role ARN 與 role-session ARN；grant 給 IAM role ARN 時，boundary/session policy 的 implicit deny 仍限制權限。
- **C：** 不正確。是否受 boundary 限制取決於 Principal 是 role ARN、role-session ARN 或其他 principal；不可把 resource Allow 一概視為繞過。
- **D：** 不正確。支援 resource policy 的服務可以指定 role principal；問題在 effective-permission evaluation，而不是 ARN 類型無效。

**事實查證：** [Permissions boundaries for IAM entities](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)、[Identity-based policies and resource-based policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html)

### 練習題 3｜SAP｜Direct grant to role-session ARN

某支援此 Principal 類型的 resource policy 直接允許 arn:aws:sts::111122223333:assumed-role/ReportRole/job-42。ReportRole boundary 未允許該 action，但沒有任何適用的 explicit Deny、SCP 或 RCP。依 IAM evaluation，哪項正確？

A. 直接授權給 role session 的 permission 不受 role identity policy或 boundary 的 implicit deny 限制
B. 所有 boundary omission 都是 explicit Deny，因此必定拒絕
C. 結果與 Principal 寫 role ARN 完全相同
D. STS session ARN 永遠不能出現在 resource policy

**答案：A**

- **A：** 正確。同帳號直接 grant 給 role-session principal 是給 session 本身的權限；但任何適用的 explicit Deny、SCP、RCP 或服務特定控制仍可阻擋。
- **B：** 不正確。Boundary 未允許通常是 implicit deny，不等同 policy 中的 Deny statement；兩者對 session-principal grant 的效果不同。
- **C：** 不正確。Role ARN grant 會受 boundary/session policy 的 implicit deny 限制，正是本題要辨識的 principal-type 差異。
- **D：** 不正確。部分 resource policies 支援 assumed-role session principal；設計時仍應避免脆弱地綁定任意 session name。

**事實查證：** [Permissions boundaries for IAM entities](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)、[Identity-based policies and resource-based policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html)

### 練習題 4｜SAA｜Cross-account assume-role policy pair

Account A 的 DeploymentRole 必須讀取 Account B 私有 bucket 的 reports/*，團隊選擇先 assume B 的 ReportReaderRole，而不是直接把 bucket policy授權給A。哪個最小授權組合正確？

A. 只在 B 的 ReportReaderRole trust policy列出A account root，A role不需 sts:AssumeRole
B. 只在 A 的 DeploymentRole 允許 s3:GetObject 到 B bucket，B 不需任何設定
C. 在 B bucket policy把 Principal設為所有AWS accounts，再靠object prefix命名隔離
D. A 的 DeploymentRole identity policy允許對 B ReportReaderRole呼叫 sts:AssumeRole；B role trust policy明確信任A DeploymentRole並可加條件；B role自己的permissions policy只允許 reports/* 的 s3:GetObject

**答案：D**

- **A：** 不正確。Trust policy只完成「誰可嘗試assume」的一側；A caller仍需identity-based sts:AssumeRole Allow。若信任整個A account，還必須由A管理員再限制哪些principal可使用。
- **B：** 不正確。A不能單方面授權自己跨account讀B的resource；既然題幹選擇assume-role路徑，B必須在role trust中同意A的principal，且B role還要有S3權限。
- **C：** 不正確。Principal wildcard把resource公開給過多AWS principals，prefix命名不是cross-account trust boundary。若選resource-policy direct grant，仍應指定具體role與必要conditions。
- **D：** 正確。Caller permission與target role trust共同允許AssumeRole，取得B account中的session後，再由B role的S3 policy限制object prefix。這與直接bucket-policy grant是不同授權路徑。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[Cross-account policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic-cross-account.html)、[How to use trust policies with IAM roles](https://aws.amazon.com/blogs/security/how-to-use-trust-policies-with-iam-roles/)、[Actions, resources, and condition keys for Amazon S3](https://docs.aws.amazon.com/service-authorization/latest/reference/list_s3.html)

### 練習題 5｜SAA｜Session policy as a ceiling

AnalyticsRole 的 role policy 允許 DynamoDB 與整個 reports bucket；broker 呼叫 AssumeRole 時傳入 session policy，只允許 reports/customer-17/* 的 GetObject。這個 session 能做什麼？

A. Session policy 會永久改寫 AnalyticsRole
B. 仍可使用全部 DynamoDB 與 S3 權限，因為 role policy 優先
C. 只能取得 role policy 與 session policy 交集內的 customer-17 objects；session policy不能擴大 role
D. 取得 session policy 加上 role policy 的聯集

**答案：C**

- **A：** 不正確。Session policy 隨 temporary session 到期，不修改 role resource；要永久變更需更新 role policy。
- **B：** 不正確。傳入有效 session policy 後，未列入的 role permissions 對該 session 不可用；若不傳 policy 才由 role 既有上限決定。
- **C：** 正確。AssumeRole session policies 是 session 的額外 ceiling；effective identity permissions 是 role policy 與 session policy 的交集。
- **D：** 不正確。若採聯集，broker 可用 session policy 擴權，違反 AWS 設計。Session policy 只能縮小。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 6｜SAA｜SCP does not grant

Member account 所在 OU 的 SCP allow list 包含 EC2，但 DeveloperRole 沒有任何 ec2:RunInstances Allow。DeveloperRole 能啟動 instance 嗎？

A. 由 consolidated billing payer 決定
B. 不能；SCP 定義 organization ceiling，不會創造 IAM permission
C. 能；但只限 management account
D. 能；SCP Allow 會下發成每個 role 的 permission

**答案：B**

- **A：** 不正確。Consolidated billing 處理費用彙整，不參與 IAM authorization。
- **B：** 正確。Role 還需要 identity/resource Allow，且該 action 也不能被 SCP/RCP 等 guardrail 排除。
- **C：** 不正確。SCP 不影響 management account users/roles；本題是 member account，且無 IAM Allow。
- **D：** 不正確。SCP 不是 identity policy，不會附加可執行權限。它只限制 member-account principals 可獲得的最大範圍。

**事實查證：** [Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 7｜SAP｜VPC endpoint policy filter

Role policy 與 bucket policy 都允許讀取 two-data bucket。從 internet path 可成功；從某 VPC 的 S3 gateway endpoint 卻只對此 bucket AccessDenied。應優先檢查什麼？

A. Bucket 的 public-read ACL
B. Route table 是否能取代 IAM Allow
C. 該 VPC endpoint policy 的 Principal、Action、Resource 與 conditions 是否允許這個 request
D. 停用 S3 Block Public Access

**答案：C**

- **A：** 不正確。具名 private access 不需要 public ACL；internet path 成功也顯示基礎 bucket authorization 可能正常。
- **B：** 不正確。Route 選擇資料路徑，不授予 API action。Endpoint association/route 可造成連線失敗，但不會以 policy-specific AccessDenied 取代 IAM。
- **C：** 正確。Endpoint policy 是經該 endpoint request 的額外 filter；它不會補足缺少的 IAM Allow，也不影響未經該 endpoint 的 internet requests。
- **D：** 不正確。BPA 與具名 endpoint access不是同一問題；停用它會擴大暴露且掩蓋 endpoint policy 根因。

**事實查證：** [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)、[Control access to VPC endpoints using endpoint policies](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html)

### 練習題 8｜SAA｜KMS service-specific dual authorization

AppRole 有正確 s3:GetObject，能看到 SSE-KMS object，但下載時收到 KMS AccessDenied。最合理的解釋是什麼？

A. KMS alias 必須寫 resource policy，key ARN 不可使用
B. S3 GetObject 自動包含所有 KMS permissions，所以只能是網路故障
C. SSE-KMS object 不再執行 IAM evaluation
D. 讀取資料還需要適用的 kms:Decrypt 授權；key policy/grant、IAM、SCP 與 encryption context 都可能限制它

**答案：D**

- **A：** 不正確。S3 bucket policy不能取代KMS key policy的授權根；兩個服務會各自評估對應resource與action。應分別檢查object ARN與key ARN。
- **B：** 不正確。只授權S3 GetObject仍可能在S3替caller向KMS解開data key時失敗；若object不是SSE-KMS或使用服務管理方式且caller不需額外KMS權限，題幹才會不同。
- **C：** 不正確。只有KMS Decrypt不能讀取S3 object bytes；caller仍須通過S3 identity/resource policy、Block Public Access與其他guardrails的評估。
- **D：** 正確。讀取SSE-KMS object通常需s3:GetObject及對該KMS key的kms:Decrypt；key policy必須直接授權或允許IAM delegation。Cross-account時應使用完整key ARN，encryption context條件只有policy確實要求時才必須匹配。

**事實查證：** [Using server-side encryption with AWS KMS keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html)、[Key policies in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 9｜SAP｜Absent condition keys and safe operators

團隊要在 Deny guardrail 中依 request context 限制操作，但某些服務 requests 不一定包含該 condition key。哪兩個做法最能避免因 key 缺席造成非預期結果？（選兩項）

A. 依需求明確使用 Null 或 ...IfExists operator，並特別檢查 negated operator 與 Deny 的組合
B. 假設所有 global condition keys 在每個 AWS request 都存在
C. 把所有 conditions 移除並授予 AdministratorAccess
D. 只調整 statement 排序，讓較窄規則先出現
E. 查閱該 key 的可用 request contexts，並用正反 request 實測 policy

**答案：A、E**

- **A：** 正確。Null 可檢查 key 是否存在，IfExists 可調整缺席行為；但 negated operator 與 explicit Deny 仍需逐例推導。
- **B：** 不正確。不存在的 key 會依 operator 產生不同結果，這項假設正是常見 guardrail 缺陷來源。
- **C：** 不正確。移除 conditions 消除了要求本身，Admin 也可能仍被 organization explicit Deny 限制。
- **D：** 不正確。IAM 不採 first-match；statement 順序不能修正 condition semantics。
- **E：** 正確。Condition key 是否出現在 context 取決於 service、action 與呼叫方式；官方 availability 與實際 request 測試是必要證據。

**事實查證：** [AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 10｜SAP｜NotAction safety in Region guardrails

平台用 SCP 限制未核准 Regions，statement 為 Effect:Deny、NotAction:[一組 global services]、Condition:StringNotEquals aws:RequestedRegion。哪兩項評估方式正確？（選兩項）

A. 所有 global services 都以相同 Region context 運作，不需測試例外
B. NotAction 永遠代表 Allow，因此這個 Deny statement 無效
C. NotAction 等同 Resource:*，所以不必檢查 Effect 與 Condition
D. 應把 NotAction 解讀為：除列出 actions 外，其餘適用 actions 在 condition 成立時被 Deny
E. 應以官方 global-service/dependency 清單與 staged OU 測試檢查例外，因錯漏可能中斷必要服務

**答案：D、E**

- **A：** 不正確。Global 與 regional service 的 request context/依賴不同，粗略假設會誤阻身份、billing 或支援流程。
- **B：** 不正確。NotAction 的效果由 Effect 決定；它不是 Allow 或 Deny 的同義詞。
- **C：** 不正確。Action 集合、Resource、Effect 與 Condition 必須一起解讀；任何一項都不能被 NotAction 取代。
- **D：** 正確。在 Deny 中，NotAction 定義未被列為例外的 action 集合，再由 Resource 與 Condition 縮小適用 requests。
- **E：** 正確。Region guardrail 是高 blast-radius policy，需 canary OU、CloudTrail 與 recovery path，而不只驗證 JSON syntax。

**事實查證：** [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)、[AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)、[Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先確認implicit deny，再找applicable allow，任何explicit deny都勝…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「同一request可能同時受identity、resource、boundary、SCP、session與KMS policy影響。」，所以「先確認implicit deny，再找applicable allow，任何explicit deny都勝出，最後檢查交集型邊界。」能直接滿足它；若constraint改成「Policy Simulator可協助，但resource context與某些service-specific policy仍需真實驗證。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先確認implicit deny，再找applicable allow，任何explicit deny都勝出，最後檢查交集型邊界。」。替代方案「Policy Simulator可協助，但resource context與某些service-specific policy仍需真實驗證。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只看到identity allow就判斷可存取，漏掉SCP、permissions boundary或key policy deny。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「同一request可能同時受identity、resource、boundary、SCP、session與KMS policy影響。」，排除會導致「只看到identity allow就判斷可存取，漏掉SCP、permissions boundary或key policy deny。」的選項，再選「先確認implicit deny，再找applicable allow，任何explicit deny都勝出，最後檢查交集型邊界。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先確認implicit deny，再找applicable allow，任何explicit deny都勝出，最後檢查交集型邊界。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「authorization is an intersection of independent guardrails」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 23 章　STS、Cross-account 與 Federation

跨帳號與企業身份不應靠複製user或分享長期secret。

## 跟著一次授權決定走：先從故事開始

把鏡頭拉到一個真實的production現場：SaaS供應商需讀客戶帳號資料，內部員工以公司目錄登入多帳號。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：跨帳號與企業身份不應靠複製user或分享長期secret。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：把身份系統想成辦公大樓：登入證明你是誰，門禁規則才決定你能進哪一間房。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。AWS STS是這一章的入口，IAM roles用來畫出邊界；主要方向「以IdP登入後assume role；trust policy決定誰可扮演，permissions policy決定扮演後能做什麼。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：SaaS供應商需讀客戶帳號資料，內部員工以公司目錄登入多帳號。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[AWS STS] ── Allow / Deny ──> protected resource
          │ 簽發有限時效的temporary AWS credentials。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · IAM roles：提供可被人、workload或AWS service扮演的identity，沒有長期credentials。
  · AWS IAM Identity Center：集中管理workforce登入多個AWS accounts與business applications。

失敗時先找：只設定role permissions卻沒有trust，或ExternalId/condition錯誤造成confused deputy。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問AWS STS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS STS和IAM roles並不是兩個任意的產品名稱。前者適合本章，是因為「以IdP登入後assume role；trust policy決定誰可扮演，permissions policy決定扮演後能做什麼。」直接回應了眼前的問題；後者描述的「Resource policy可直接授權某些cross-account access，適合S3/SQS等支援服務。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只設定role permissions卻沒有trust，或ExternalId/condition錯誤造成confused deputy。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「separate who may assume from what the role may do」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS STS | 簽發有限時效的temporary AWS credentials。 | AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 |
| IAM roles | 提供可被人、workload或AWS service扮演的identity，沒有長期credentials。 | Trust policy控制sts:AssumeRole的principal；permissions policies控制session可呼叫的AWS actions。 |
| AWS IAM Identity Center | 集中管理workforce登入多個AWS accounts與business applications。 | 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 |

## 把全圖套進一個具體案例

**場景：** SaaS供應商需讀客戶帳號資料，內部員工以公司目錄登入多帳號。

1. 故事的起點：SaaS供應商需讀客戶帳號資料，內部員工以公司目錄登入多帳號。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS STS負責「簽發有限時效的temporary AWS credentials。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：IAM roles、AWS IAM Identity Center各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只設定role permissions卻沒有trust，或ExternalId/condition錯誤造成confused deputy。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS STS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：跨帳號與企業身份不應靠複製user或分享長期secret。
- **具體例子／邊界：** 在「SaaS供應商需讀客戶帳號資料，內部員工以公司目錄登入多帳號。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### IAM roles

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Resource policy可直接授權某些cross-account access，適合S3/SQS等支援服務。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只設定role permissions卻沒有trust，或ExternalId/condition錯誤造成confused deputy。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：separate who may assume from what the role may do。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### AWS account

AWS中的資源、身份、quota與billing隔離邊界；企業通常用多帳號縮小blast radius，而不是把所有環境塞在同一帳號。

### federation

讓外部IdP驗證使用者或workload，再交換AWS temporary role session，而不為每人建立獨立長期AWS密碼。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### IdP

Identity Provider，保存或驗證使用者身份的系統，例如Entra ID、Okta或企業目錄。

## 回到 AWS：Components、功用與責任邊界

### AWS STS

- **功用：** 簽發有限時效的temporary AWS credentials。
- **底層機制：** AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。
- **關鍵設定：** role ARN、session name、duration、external ID、source identity、session tags與session policy。
- **選擇時機：** cross-account、federation、workload identity與避免長期access keys。
- **替換時機：** 不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。

### IAM roles

- **功用：** 提供可被人、workload或AWS service扮演的identity，沒有長期credentials。
- **底層機制：** Trust policy控制sts:AssumeRole的principal；permissions policies控制session可呼叫的AWS actions。
- **關鍵設定：** trust policy、max session duration、permissions、permissions boundary、tags與instance/task execution integration。
- **選擇時機：** EC2/Lambda/ECS workload、cross-account、federated user與第三方delegate。
- **替換時機：** 固定人員管理應使用Identity Center；不要用shared IAM user模擬role。

### AWS IAM Identity Center

- **功用：** 集中管理workforce登入多個AWS accounts與business applications。
- **底層機制：** 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。
- **關鍵設定：** identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
- **選擇時機：** 企業員工、群組生命週期與多帳號SSO。
- **替換時機：** consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。

## 考前與實作時再查：設定操作手冊

### AWS STS：逐項設定說明

#### `role ARN`

- **控制什麼：** `role ARN`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS STS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `session name`

- **控制什麼：** `session name`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `duration`

- **控制什麼：** `duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS STS的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `external ID`

- **控制什麼：** `external ID`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `source identity`

- **控制什麼：** `source identity`指定AWS STS讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `session tags`

- **控制什麼：** `session tags`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

#### `session policy`

- **控制什麼：** `session policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、federation、workload identity與避免長期access keys。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS STS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

### IAM roles：逐項設定說明

#### `trust policy`

- **控制什麼：** `trust policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「EC2/Lambda/ECS workload、cross-account、federated user與第三方delegate。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM roles明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `max session duration`

- **控制什麼：** `max session duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「EC2/Lambda/ECS workload、cross-account、federated user與第三方delegate。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定IAM roles的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `permissions`

- **控制什麼：** `permissions`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「EC2/Lambda/ECS workload、cross-account、federated user與第三方delegate。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM roles明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `permissions boundary`

- **控制什麼：** `permissions boundary`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「EC2/Lambda/ECS workload、cross-account、federated user與第三方delegate。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM roles明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `tags`

- **控制什麼：** `tags`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「EC2/Lambda/ECS workload、cross-account、federated user與第三方delegate。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM roles建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `instance/task execution integration`

- **控制什麼：** `instance/task execution integration`把IAM roles與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### AWS IAM Identity Center：逐項設定說明

#### `identity source`

- **控制什麼：** `identity source`指定AWS IAM Identity Center讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `permission sets`

- **控制什麼：** `permission sets`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `assignments`

- **控制什麼：** `assignments`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `session duration`

- **控制什麼：** `session duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS IAM Identity Center的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `MFA`

- **控制什麼：** `MFA`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `SCIM`

- **控制什麼：** `SCIM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `delegated administration`

- **控制什麼：** `delegated administration`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

## 可以直接對照 AWS 的設定範例

### Third-party cross-account role trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::444455556666:role/VendorWorker"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"sts:ExternalId": "customer-8f3a91"}
    }
  }]
}
```

1. Principal限制到vendor具名role，不要直接信任整個外部account root後再期待對方自律。
2. ExternalId由服務供應商提供給每個customer，降低confused-deputy風險；它不是密碼。
3. permissions policy仍需限制vendor session實際可讀的resource與actions。

## 讀到這裡，請用自己的話說一次

1. AWS STS的責任：簽發有限時效的temporary AWS credentials。
2. 底層機制：AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。
3. 第一個要看的設定：role ARN、session name、duration、external ID、source identity、session tags與session policy。
4. 選擇邏輯：以IdP登入後assume role；trust policy決定誰可扮演，permissions policy決定扮演後能做什麼。
5. 不要混淆：IAM roles的責任是「提供可被人、workload或AWS service扮演的identity，沒有長期credentials。」；它不會自動取代AWS STS。
6. 替換訊號：不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。
7. 最常見錯法：只設定role permissions卻沒有trust，或ExternalId/condition錯誤造成confused deputy。
8. 可移植原則：separate who may assume from what the role may do。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS STS | 簽發有限時效的temporary AWS credentials。 | AssumeRole驗證trust policy與request conditions，再依role permissions和session policy產生session。 | cross-account、federation、workload identity與避免長期access keys。 | 不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。 |
| IAM roles | 提供可被人、workload或AWS service扮演的identity，沒有長期credentials。 | Trust policy控制sts:AssumeRole的principal；permissions policies控制session可呼叫的AWS actions。 | EC2/Lambda/ECS workload、cross-account、federated user與第三方delegate。 | 固定人員管理應使用Identity Center；不要用shared IAM user模擬role。 |
| AWS IAM Identity Center | 集中管理workforce登入多個AWS accounts與business applications。 | 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 | 企業員工、群組生命週期與多帳號SSO。 | consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Resource policy可直接授權某些cross-account access，適合S3/SQS等支援服務。 | 只有當題目條件明確改變時才可能合理。 | 只設定role permissions卻沒有trust，或ExternalId/condition錯誤造成confused deputy。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Resource policy可直接授權某些cross-account access，適合S3/SQS等支援服務。」之間做選擇。
- 認得常考設定：role ARN、session name、duration、external ID、source identity、session tags與session policy。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：不是權限資料庫；真正可做的action仍由IAM/resource policies與guardrails決定。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements。

## 本章 10 題考題

### 練習題 1｜SAA｜Two gates of cross-account role assumption

Account A 的 DeployRole 要 assume Account B 的 ReleaseRole。B role 已有部署 permissions policy。還必須滿足哪組授權條件？

A. 只需 A 的 DeployRole 擁有 AdministratorAccess，不需 B 表示信任
B. 只需 B role permissions policy 包含 sts:AssumeRole
C. 只需兩個帳號位於同一 OU
D. A 的 DeployRole 允許 sts:AssumeRole 指向 B role，且 B role trust policy 接受 A principal 與所需 conditions

**答案：D**

- **A：** 不正確。A 不能單方面授權自己進入 B；target account 必須接受 principal。
- **B：** 不正確。Role permissions policy 控制 session 取得後可做什麼，不取代 trust policy。Trust policy 是 role 的 resource-based policy。
- **C：** 不正確。OU 只組織 accounts/policies，不建立 cross-account trust。
- **D：** 正確。AssumeRole request 先過來源 principal permission 與 target role trust；成功後的新 session 才以 B role permissions 操作 B 資源。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[Cross-account policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic-cross-account.html)

### 練習題 2｜SAA｜Third-party confused deputy mitigation

監控 SaaS 供應商以同一 vendor account 為數百家客戶 assume roles。客戶要避免供應商把甲客戶的 request 錯套到乙客戶 role。哪個 trust 設計最佳？

A. 把 role ARN 當秘密，只要名稱夠長就不需 Condition
B. 所有客戶共用同一 ExternalId，方便供應商維護
C. 信任指定 vendor principal，並要求供應商為該客戶產生且使用唯一 sts:ExternalId；role permissions 只涵蓋客戶資源
D. 建立 IAM user access key 寄給供應商，避免 STS

**答案：C**

- **A：** 不正確。ARN 不是秘密，知道 ARN 也不等於獲得 authorization。Confused deputy 需要 request 中可區分客戶的條件。
- **B：** 不正確。共用值無法區分客戶，供應商若選錯 role ARN 仍可能成功。 Federation設計必須分清登入來源、role trust與已簽發session；其中任何一層都不能自動取代另一層。
- **C：** 正確。受控 Principal 建立身份邊界，customer-specific ExternalId 綁定委派意圖，least-privilege role 再限制成功 session 的影響。
- **D：** 不正確。長期 key 難撤銷、輪替與區分 sessions；STS role 正是此 cross-account delegation 的標準機制。

**事實查證：** [How to use trust policies with IAM roles](https://aws.amazon.com/blogs/security/how-to-use-trust-policies-with-iam-roles/)、[AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)

### 練習題 3｜SAP｜External ID is not authentication

一份公開 IaC template 包含第三方 role 的 ExternalId。工程師認為值已曝光，必須把 trust policy 改成 Principal:"*" 再把 ExternalId 當密碼。哪項評估正確？

A. ExternalId 必須和 access key 一樣由客戶自行保密，否則 STS 無法使用
B. 只要有 ExternalId，任何 AWS account 都可安全 assume role
C. ExternalId 會加密 STS credentials，曝光後才需 wildcard Principal
D. ExternalId 用於 confused-deputy 關聯，不是 caller authentication；仍須限制 vendor Principal 並維持最小權限

**答案：D**

- **A：** 不正確。它可見於配置，威脅模型不是共享密碼；應由第三方為客戶提供唯一值並搭配受控 principal。
- **B：** 不正確。ExternalId condition 不是獨立 authentication，不能讓任意 principal 變安全。
- **C：** 不正確。ExternalId 不參與 credential encryption，也不合理化 wildcard Principal。
- **D：** 正確。Principal 證明哪個 AWS identity 呼叫，ExternalId 協助第三方把 request 對應正確客戶；兩者與 role permission 缺一不可。

**事實查證：** [How to use trust policies with IAM roles](https://aws.amazon.com/blogs/security/how-to-use-trust-policies-with-iam-roles/)、[AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)

### 練習題 4｜SAP｜Role chaining duration

使用者先以 federation 取得 RoleA credentials，再用 RoleA assume RoleB。RoleB max session duration 設為 12 小時，但呼叫 DurationSeconds=14400。結果為何？

A. AssumeRole 失敗；role chaining 的第二段 session 最長一小時
B. 成功 4 小時，因為小於 RoleB 的 12 小時上限
C. 成功 13 小時，因為兩段 session duration 相加
D. 成功且 credentials 永久有效，直到 RoleA 被刪除

**答案：A**

- **A：** 正確。用 temporary role credentials 再 assume 第二個 role 屬於 chaining；DurationSeconds 超過 3600 會失敗。
- **B：** 不正確。一般 AssumeRole 可受 role max duration 允許較長時間，但 role chaining 有額外一小時限制。
- **C：** 不正確。Session durations 不會相加；每段 credentials 都有自己的到期時間。
- **D：** 不正確。STS credentials 永遠有期限，刪除 role 也不是正常 session-duration 設計。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)

### 練習題 5｜SAP｜Session policy narrowing

一個 tenant broker 使用可讀取所有 tenant prefixes 的 BaseRole，但每次只應發出可讀單一 tenant prefix 的 session。哪個做法能在不建立數千 roles 的前提下縮小每次 session？

A. 把 tenant policy 寫入 BaseRole trust policy 的 Resource
B. 在 AssumeRole 傳入只允許該 tenant prefix 的 session policy，並確保 BaseRole 本身涵蓋該權限
C. 讓 client 在每次 request 自行選擇任意 aws:PrincipalTag
D. 將 policy 附到 STS service principal

**答案：B**

- **A：** 不正確。Trust policy 控制誰能 assume role，不是 session 的 data-resource permission policy。
- **B：** 正確。Session policy 與 role identity policy 取交集，適合由可信 broker 對每次 session 再限縮 resources。
- **C：** 不正確。未受控標籤讓 client 可冒充其他 tenant；session tags 必須由可信 identity flow 管理。
- **D：** 不正確。STS 簽發 credentials，但 tenant resource permission 屬於 role/session，不附在 STS service。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 6｜SAP｜SourceIdentity audit continuity

員工可能依序 assume OperationsRole 與 IncidentRole。SOC 必須在 CloudTrail 中可靠保留最初員工識別，而 session name 由使用者自行輸入。最佳設計是什麼？

A. 在 federation/role trust 流程要求並設定 SourceIdentity，讓它在 role chaining 中傳遞
B. 從 source IP 推測員工，因為 IP 永遠唯一
C. 只要求使用者在 CLI comment 寫姓名
D. 把員工 ID 放在 ExternalId，並允許所有人使用同一值

**答案：A**

- **A：** 正確。SourceIdentity 可由 trust policy 要求，出現在 CloudTrail session context，並能跨 role chaining 保留來源。
- **B：** 不正確。NAT、VPN 與共用設備使 IP 不能作穩定個人身份；它可作輔助訊號。 Federation設計必須分清登入來源、role trust與已簽發session；其中任何一層都不能自動取代另一層。
- **C：** 不正確。任意 comment 不會成為 AWS authorization/audit context，且不可強制。
- **D：** 不正確。ExternalId 解決第三方 confused deputy，不是 workforce audit identity 欄位。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[Monitor and control actions taken with assumed roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_monitor.html)、[CloudTrail record contents](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html)

### 練習題 7｜SAP｜Session tags and ABAC

公司 IdP 提供 department claim；跨帳號 resources 都有 department tag。要以 ABAC 讓 finance session 只能操作 finance resources，最關鍵的設計是什麼？

A. 只依 resource name 包含 finance 判斷，不需 policy condition
B. 由可信 federation 映射 claim 為受控 session tag，以 aws:PrincipalTag 與 resource tag 比對，跨 role 時將必要 tag 設為 transitive
C. 讓每位使用者在 AssumeRole 時自由輸入 department tag
D. ABAC tag 可以覆蓋 SCP explicit Deny，因此不用 organization guardrail

**答案：B**

- **A：** 不正確。命名規則不是 IAM condition，rename 或碰撞會破壞邊界。 Federation設計必須分清登入來源、role trust與已簽發session；其中任何一層都不能自動取代另一層。
- **B：** 正確。可信 attribute source、受控 tag mutation 與 principal/resource tag condition 共同形成 ABAC；transitive tags 保留 chaining context。
- **C：** 不正確。若使用者可自選 tag，就能宣稱屬於其他部門；必須限制 sts:TagSession 與可接受 values。
- **D：** 不正確。Tag-based Allow 仍受 SCP、boundary 與 explicit Deny 限制。

**事實查證：** [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)、[AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)

### 練習題 8｜SAA｜SAML versus OIDC web identity federation

Mobile app 的使用者已從支援 OIDC 的身分提供者取得 ID token；app需要交換短期AWS credentials來存取限定prefix，而不是讓使用者登入AWS access portal。哪個設計正確？

A. 建立SAML workforce permission set，讓mobile app保存長期IAM user key
B. 只建立Cognito user pool；任何user-pool token都會自動變成AWS credentials
C. 使用Cognito identity pool或信任該OIDC provider的web-identity role；trust驗證issuer、audience與必要claims，再由AssumeRoleWithWebIdentity發短期credentials並以role policy限縮prefix
D. 把OIDC token直接當SigV4 access key呼叫S3

**答案：C**

- **A：** 不正確。SAML permission set面向workforce AWS account access；在mobile app內保存IAM access key會產生不可安全輪替的共享秘密。只有企業員工登入console/CLI時才考慮該路徑。
- **B：** 不正確。User pool負責應用程式authentication與token；取得AWS credentials是identity pool或web-identity federation的另一層，必須另外設定role mapping與trust。
- **C：** 正確。AssumeRoleWithWebIdentity依role trust驗證OIDC issuer、audience與claims，發出temporary credentials；Cognito identity pool可代管provider整合與role mapping。Resource policy仍可加上額外邊界。
- **D：** 不正確。OIDC JWT不是AWS access key/secret key，不能直接簽署SigV4 request。它必須先由受信任的federation流程交換成有範圍與到期時間的STS credentials。

**事實查證：** [AssumeRoleWithWebIdentity API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html)、[Create an OIDC identity provider in IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)、[Amazon Cognito identity pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html)

### 練習題 9｜SAA｜Direct resource policy versus assume-role

Account A 的 publisher 只需向 Account B 的單一 SQS queue SendMessage；另一名 platform admin 則需在 B 管理一組 EC2、S3 與 CloudFormation resources。哪兩項設計判斷正確？（選兩項）

A. 只要某服務支援一種 resource policy，就會自動授權 B 帳號所有其他服務
B. 所有 cross-account access 都必須 AssumeRole，resource policy 永遠不可用
C. 對單一 queue action，可由 B 的 SQS resource policy授權 A publisher，並由 A identity policy允許 SendMessage
D. 只在 A 加 AdministratorAccess 即可管理 B，B 不需 trust
E. 對跨多服務的管理 permission set，讓 admin assume B 的管理 role 通常較清楚，CloudTrail 會記錄該 B role session

**答案：C、E**

- **A：** 不正確。Resource policy 只控制其所附 resource 與支援 actions，不能橫向授權其他服務。
- **B：** 不正確。S3、SQS、SNS 等部分服務支援直接 resource-policy sharing；應依服務能力與 attribution 需求選擇。
- **C：** 正確。SQS 支援 queue policy；窄小的 resource-specific cross-account action 可不建立代理 role，但兩側授權與 Deny 仍須成立。
- **D：** 不正確。A 的 admin policy 不能替 B 建立同意；B 必須提供 role trust 或 resource-policy path。
- **E：** 正確。Assumed role 形成 target-account session，適合多 resources/services 的一致 permission set 與 target-side identity。

**事實查證：** [Identity-based policies and resource-based policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html)、[Cross-account policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic-cross-account.html)、[IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)

### 練習題 10｜SAP｜Revocation and temporary-session reality

Incident responder停用了外部IdP中的使用者，但該人可能同時持有Identity Center portal session、permission-set account session與一般STS role session。哪兩項處置與理解正確？（選兩項）

A. 刪除CloudTrail中該使用者的事件可避免credentials再次使用
B. 依session類型執行revoke permission-set sessions或IAM role-session revocation；其常見機制是加入只影響較早session的新explicit Deny，並非IdP刪除STS token
C. 先阻止新登入，並在Identity Center結束active access-portal sessions；這不等同已撤銷所有account role sessions
D. IdP停用會由IdP直接刪除AWS已簽發的所有STS credentials，因此無需AWS端處置
E. 重新命名permission set即可讓所有既有sessions立刻失效

**答案：B、C**

- **A：** 不正確。CloudTrail是不可任意刪除的稽核證據，刪除log也不會改變STS credential validity。正確做法是保留事件、告警並在授權層撤銷。
- **B：** 正確。Identity Center與IAM role都有明確的revocation流程，通常透過time-bounded explicit Deny使先前簽發的session失去權限。仍需逐一盤點直接federation或其他roles。
- **C：** 正確。Portal session控制使用者是否能繼續使用access portal；刪除它可阻止該入口，但已取得的permission-set role credentials有自己的生命週期，必須另外revoke。
- **D：** 不正確。IdP控制後續authentication assertion，卻不擁有AWS已簽發temporary credentials。若只停用IdP，既有session可能持續到到期或被AWS端revocation policy否決。
- **E：** 不正確。名稱變更不是credential revocation control，也不保證更新已provisioned role的effective session。只有執行文件化的session revocation或適用Deny才可可靠阻止request。

**事實查證：** [End active IAM Identity Center user sessions](https://docs.aws.amazon.com/singlesignon/latest/userguide/end-active-sessions.html)、[Revoke IAM Identity Center user permissions and account sessions](https://docs.aws.amazon.com/singlesignon/latest/userguide/revoke-user-permissions.html)、[Revoke IAM role temporary security credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_revoke-sessions.html)、[Temporary security credentials in IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以IdP登入後assume role；trust policy決定誰可扮演，permissions pol…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「跨帳號與企業身份不應靠複製user或分享長期secret。」，所以「以IdP登入後assume role；trust policy決定誰可扮演，permissions policy決定扮演後能做什麼。」能直接滿足它；若constraint改成「Resource policy可直接授權某些cross-account access，適合S3/SQS等支援服務。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以IdP登入後assume role；trust policy決定誰可扮演，permissions policy決定扮演後能做什麼。」。替代方案「Resource policy可直接授權某些cross-account access，適合S3/SQS等支援服務。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只設定role permissions卻沒有trust，或ExternalId/condition錯誤造成confused deputy。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「跨帳號與企業身份不應靠複製user或分享長期secret。」，排除會導致「只設定role permissions卻沒有trust，或ExternalId/condition錯誤造成confused deputy。」的選項，再選「以IdP登入後assume role；trust policy決定誰可扮演，permissions policy決定扮演後能做什麼。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以IdP登入後assume role；trust policy決定誰可扮演，permissions policy決定扮演後能做什麼。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「separate who may assume from what the role may do」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 24 章　IAM Identity Center 與企業身份

企業需要集中人員生命週期、MFA與多帳號權限，而非在每個帳號建立user。

## 跟著一次授權決定走：先從故事開始

如果今天由你值班，收到的需求可能是這樣：跨國企業使用Entra ID，要求依群組存取不同OU帳號並快速撤權。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：企業需要集中人員生命週期、MFA與多帳號權限，而非在每個帳號建立user。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：登入像出示員工證，policy像每扇門旁的門禁規則；有證件不代表所有房間都能進。 這只是起點，因為AWS授權由多層policy共同決定，還要考慮explicit Deny、resource policy與organization guardrail。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由AWS IAM Identity Center承接主要責任，以AWS Directory Service檢查替代條件，並用「整合外部IdP，使用permission sets下發temporary role sessions並集中assignments。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：跨國企業使用Entra ID，要求依群組存取不同OU帳號並快速撤權。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[AWS IAM Identity Center] ── Allow / Deny ──> protected resource
          │ 集中管理workforce登入多個AWS accounts與business applications。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · AWS Directory Service：在AWS提供managed Microsoft AD、AD Connector或Simple AD以支援d…

失敗時先找：離職只停用一個帳號卻遺留各AWS帳號local users與access keys。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問AWS IAM Identity Center有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS IAM Identity Center和AWS Directory Service並不是兩個任意的產品名稱。前者適合本章，是因為「整合外部IdP，使用permission sets下發temporary role sessions並集中assignments。」直接回應了眼前的問題；後者描述的「Directory Service適合需要managed Microsoft AD語意的workload，不等於所有console federation。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：離職只停用一個帳號卻遺留各AWS帳號local users與access keys。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「centralize workforce identity, decentralize workload roles」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS IAM Identity Center | 集中管理workforce登入多個AWS accounts與business applications。 | 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 |
| AWS Directory Service | 在AWS提供managed Microsoft AD、AD Connector或Simple AD以支援domain-aware workloads。 | Managed AD domain controllers跨AZ部署；Connector代理到既有AD而不保存完整directory。 |

## 把全圖套進一個具體案例

**場景：** 跨國企業使用Entra ID，要求依群組存取不同OU帳號並快速撤權。

1. 故事的起點：跨國企業使用Entra ID，要求依群組存取不同OU帳號並快速撤權。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS IAM Identity Center負責「集中管理workforce登入多個AWS accounts與business applications。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Directory Service各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「離職只停用一個帳號卻遺留各AWS帳號local users與access keys。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### Verified Access：不用先進 VPN，也不代表不用驗證

傳統 VPN 常在使用者連上後給一段網路可達性；Verified Access 改成每次進入 application 都重新評估使用者與裝置訊號。它保護的是 application access，不是讓 client 任意掃描 private subnet。

```text
user + managed device
        │ identity/device trust
        ▼
Verified Access endpoint ─ policy evaluation ─> private web application
        │ allow/deny log
        └──────────────────────────────> audit / incident response
```

#### Policy 應描述可驗證的身份與裝置條件

```CEDAR-like policy sketch
permit(principal, action, resource)
when {
  principal.groups.contains("finance") &&
  context.device.trust_level == "high"
};
```

1. Identity provider 說明人是誰，device trust provider 說明裝置狀態；兩者是不同訊號。
2. Endpoint 把 policy 套到一個 application 入口；它不是 TGW、VPN 或任意 L3 connectivity 的替代品。
3. Allow/deny logs 應進入集中稽核，否則『每次驗證』仍無法支持 incident investigation。

**選擇邊界：** 員工存取少數 private web apps、需要 identity/device-aware zero trust 時評估 Verified Access；任意協定、整段網路管理或 site-to-site connectivity 仍比較 Client VPN、VPN、DX、SSM。

**考試範圍：** 此服務是進階／新式 zero-trust 補充。考試先測 responsibility boundary：identity-aware application access 不等於建立 private routed network。

- [AWS：What is AWS Verified Access?](https://docs.aws.amazon.com/verified-access/latest/ug/what-is-verified-access.html)

## 需要時再查：四個閱讀支點

### AWS IAM Identity Center

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：企業需要集中人員生命週期、MFA與多帳號權限，而非在每個帳號建立user。
- **具體例子／邊界：** 在「跨國企業使用Entra ID，要求依群組存取不同OU帳號並快速撤權。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Directory Service

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Directory Service適合需要managed Microsoft AD語意的workload，不等於所有console federation。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：離職只停用一個帳號卻遺留各AWS帳號local users與access keys。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：centralize workforce identity, decentralize workload roles。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### AWS account

AWS中的資源、身份、quota與billing隔離邊界；企業通常用多帳號縮小blast radius，而不是把所有環境塞在同一帳號。

### federation

讓外部IdP驗證使用者或workload，再交換AWS temporary role session，而不為每人建立獨立長期AWS密碼。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### IdP

Identity Provider，保存或驗證使用者身份的系統，例如Entra ID、Okta或企業目錄。

## 回到 AWS：Components、功用與責任邊界

### AWS IAM Identity Center

- **功用：** 集中管理workforce登入多個AWS accounts與business applications。
- **底層機制：** 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。
- **關鍵設定：** identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
- **選擇時機：** 企業員工、群組生命週期與多帳號SSO。
- **替換時機：** consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。

### AWS Directory Service

- **功用：** 在AWS提供managed Microsoft AD、AD Connector或Simple AD以支援domain-aware workloads。
- **底層機制：** Managed AD domain controllers跨AZ部署；Connector代理到既有AD而不保存完整directory。
- **關鍵設定：** directory type/edition、VPC/subnets、trusts、DNS IPs、multi-Region replication與shared directories。
- **選擇時機：** Windows authentication、FSx/RDS/WorkSpaces domain integration與AD trusts。
- **替換時機：** 單純AWS workforce SSO優先IAM Identity Center；consumer identity用Cognito。

## 考前與實作時再查：設定操作手冊

### AWS IAM Identity Center：逐項設定說明

#### `identity source`

- **控制什麼：** `identity source`指定AWS IAM Identity Center讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `permission sets`

- **控制什麼：** `permission sets`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `assignments`

- **控制什麼：** `assignments`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `session duration`

- **控制什麼：** `session duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS IAM Identity Center的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `MFA`

- **控制什麼：** `MFA`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `SCIM`

- **控制什麼：** `SCIM`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `delegated administration`

- **控制什麼：** `delegated administration`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「企業員工、群組生命週期與多帳號SSO。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS IAM Identity Center建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

### AWS Directory Service：逐項設定說明

#### `directory type/edition`

- **控制什麼：** `directory type/edition`選擇AWS Directory Service的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `VPC/subnets`

- **控制什麼：** `VPC/subnets`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「Windows authentication、FSx/RDS/WorkSpaces domain integration與AD trusts。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Directory Service的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `trusts`

- **控制什麼：** `trusts`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「Windows authentication、FSx/RDS/WorkSpaces domain integration與AD trusts。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Directory Service明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `DNS IPs`

- **控制什麼：** `DNS IPs`控制名稱如何被解析或驗證；DNS只把名稱轉成目標資料，不會替代route、network policy或IAM。
- **何時需要：** 當需求符合「Windows authentication、FSx/RDS/WorkSpaces domain integration與AD trusts。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Directory Service的DNS／domain設定中明確指定zone、name、resolver direction或validation方式，並用dig/nslookup從實際來源網路驗證答案。
- **常見錯法：** 只在console看到名稱存在，不代表所有VPC、Region與client都得到同一答案；還要檢查cache TTL、zone association與return path。

#### `multi-Region replication`

- **控制什麼：** `multi-Region replication`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS Directory Service前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `shared directories`

- **控制什麼：** `shared directories`選擇資料/目錄service的availability、分片、節點休眠或managed integration模式。
- **何時需要：** 需要在成本與AZ/Region容錯、scale、Windows domain整合或閒置資源間做取捨時。
- **怎麼設定／驗證：** 明確選擇deployment/cluster/AD mode與AZs，設定failover/replica或auto-pause條件；以dependency failure與喚醒延遲測試。
- **常見錯法：** One Zone不適合不能接受AZ資料損失的state；auto-pause會增加首次連線延遲，目錄分享也仍需DNS/trust/network。

## 讀到這裡，請用自己的話說一次

1. AWS IAM Identity Center的責任：集中管理workforce登入多個AWS accounts與business applications。
2. 底層機制：連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。
3. 第一個要看的設定：identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
4. 選擇邏輯：整合外部IdP，使用permission sets下發temporary role sessions並集中assignments。
5. 不要混淆：AWS Directory Service的責任是「在AWS提供managed Microsoft AD、AD Connector或Simple AD以支援domain-aware workloads。」；它不會自動取代AWS IAM Identity Center。
6. 替換訊號：consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。
7. 最常見錯法：離職只停用一個帳號卻遺留各AWS帳號local users與access keys。
8. 可移植原則：centralize workforce identity, decentralize workload roles。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS IAM Identity Center | 集中管理workforce登入多個AWS accounts與business applications。 | 連接identity source，將permission set佈署成member account roles，使用者取得temporary sessions。 | 企業員工、群組生命週期與多帳號SSO。 | consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。 |
| AWS Directory Service | 在AWS提供managed Microsoft AD、AD Connector或Simple AD以支援domain-aware workloads。 | Managed AD domain controllers跨AZ部署；Connector代理到既有AD而不保存完整directory。 | Windows authentication、FSx/RDS/WorkSpaces domain integration與AD trusts。 | 單純AWS workforce SSO優先IAM Identity Center；consumer identity用Cognito。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Directory Service適合需要managed Microsoft AD語意的workload，不等於所有console federation。 | 只有當題目條件明確改變時才可能合理。 | 離職只停用一個帳號卻遺留各AWS帳號local users與access keys。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Directory Service適合需要managed Microsoft AD語意的workload，不等於所有console federation。」之間做選擇。
- 認得常考設定：identity source、permission sets、assignments、session duration、MFA、SCIM與delegated administration。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：consumer app身份用Cognito；machine-to-machine用IAM role/OIDC federation。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment。

## 本章 10 題考題

### 練習題 1｜SAA｜Workforce SSO across accounts

Entra ID 中的工程、財務群組要依職務登入 80 個 AWS accounts，不得建立 local IAM users。應如何設計？

A. 用 Cognito user pool 管理 AWS console workforce
B. 只部署 AWS Managed Microsoft AD
C. 將外部 IdP 接到 IAM Identity Center，同步 users/groups，建立 permission sets，並以 group+account+permission set 建立 assignments
D. 在每個帳號同步 IAM users 與 passwords

**答案：C**

- **A：** 不正確。Cognito 面向應用程式客戶身份，不是 AWS account workforce access portal。
- **B：** 不正確。Managed AD 可服務 Kerberos/domain workload，但單獨不完成多帳號 permission-set assignments。
- **C：** 正確。Identity Center 將外部身份映射為各帳號受控 roles，登入取得 temporary sessions，且 assignment 明確綁定群組、帳號與權限集。
- **D：** 不正確。Local users 讓離職、MFA 與權限變更分散到 80 個帳號；僅 legacy 例外才考慮。

**事實查證：** [What is IAM Identity Center?](https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html)、[Manage your identity source](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source.html)、[Manage AWS accounts with permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)

### 練習題 2｜SAA｜Permission-set provisioning mechanics

管理員修改 DatabaseAdmin permission set 後，79 個帳號已更新，只有一個帳號仍顯示舊權限。最適當的處理是什麼？

A. 在 user security group 開啟 IAM port
B. 把 permission set 附到 SCP
C. 檢查該帳號 provisioning status，重新 provision/update 對應的 Identity Center-managed IAM role
D. 修改 AWS access portal URL

**答案：C**

- **A：** 不正確。IAM 授權不是 security-group 流量規則。 Identity lifecycle、authentication與AWS session是不同控制面；只有修改題幹所要求的那一層，答案才會翻轉。
- **B：** 不正確。SCP 是 organization ceiling，不承載 permission set 的 job permissions。
- **C：** 正確。Permission set 是模板；assignment 時在目標帳號建立受 Identity Center 管理的 role/policies，異常帳號應檢查佈署狀態。
- **D：** 不正確。Portal URL 只影響入口，不改變目標帳號 role。 Identity lifecycle、authentication與AWS session是不同控制面；只有修改題幹所要求的那一層，答案才會翻轉。

**事實查證：** [Manage AWS accounts with permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)

### 練習題 3｜SAP｜SCIM versus SAML

員工可透過 SAML 登入 Identity Center，但離職者仍出現在 Identity Center directory，群組變更也未同步。缺少哪個能力？

A. SCIM provisioning/deprovisioning；SAML 處理登入 assertion，不同步完整 identity lifecycle
B. Route 53 health check
C. Permission set session duration
D. CloudTrail Lake

**答案：A**

- **A：** 正確。SAML傳遞authentication assertion；SCIM用bearer token建立、更新與停用users/groups。兩者有不同endpoint、token rotation、錯誤處理與故障範圍，必須分別監控。
- **B：** 不正確。Route 53 health check只能判斷endpoint健康，不能建立、更新或停用Identity Center directory objects。只有題幹改成IdP endpoint可用性監控時才是相鄰工具。
- **C：** 不正確。Session duration只控制取得AWS account role後的credential壽命，不會把IdP群組變更同步到Identity Center。若問題是過長既有session，才調整此設定。
- **D：** 不正確。CloudTrail可記錄管理API與SCIM設定變更，卻不執行directory lifecycle。它適合作為稽核證據，不能替代provisioning connector。

**事實查證：** [Automatic provisioning with SCIM](https://docs.aws.amazon.com/singlesignon/latest/userguide/provision-automatically.html)、[Manage your identity source](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source.html)

### 練習題 4｜SAP｜MFA responsibility by identity source

企業以外部 IdP 作 Identity Center identity source，要求所有 workforce 登入使用 phishing-resistant MFA。主要應在哪裡強制？

A. 依 source IP 取代 MFA
B. 在負責 authentication 的外部 IdP 強制 MFA，並協調 Identity Center/AWS session 設定與測試
C. 每個 member account 建 IAM-user MFA
D. 只在 S3 bucket policy 檢查 MFA

**答案：B**

- **A：** 不正確。Source IP只是網路位置，不證明使用者持有第二因素；受入侵的公司設備仍可通過。IP條件可疊加，不能取代MFA。
- **B：** 正確。外部IdP是authoritative authenticator，因此在IdP強制FIDO2/WebAuthn等phishing-resistant MFA；Identity Center負責account assignment與AWS session duration，後者不能替代前者。
- **C：** 不正確。建立member-account IAM users會繞過集中identity lifecycle，且不能把外部IdP的phishing-resistant MFA承諾傳遞成同一登入控制。Legacy break-glass才可能保留極少數local identity。
- **D：** 不正確。S3 policy的MFA condition只影響特定S3 requests，無法保證workforce登入流程使用phishing-resistant factor。只有要對單一敏感API再加step-up條件時才考慮resource policy。

**事實查證：** [MFA with an external identity provider](https://docs.aws.amazon.com/singlesignon/latest/userguide/mfa-types.html)、[Manage your identity source](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source.html)

### 練習題 5｜SAA｜Identity Center versus Directory Service

FSx for Windows 需要 domain join 與 Kerberos；員工還要用同一企業目錄登入 AWS accounts。哪項架構判斷正確？

A. AD Connector 一定會在 AWS 建立新的完整目錄副本
B. Directory Service/Managed Microsoft AD 處理 domain workload；Identity Center 處理 workforce account assignments，兩者可整合而非互相取代
C. Cognito user pool 是 Kerberos directory
D. Permission set 可直接讓 Windows server 加入網域

**答案：B**

- **A：** 不正確。AD Connector 是連接既有 AD 的代理型能力，不等同託管完整目錄。 Identity lifecycle、authentication與AWS session是不同控制面；只有修改題幹所要求的那一層，答案才會翻轉。
- **B：** 正確。Windows domain semantics 與 AWS account authorization 是不同責任，需選擇相符的 directory integration 與 Identity Center assignments。
- **C：** 不正確。Cognito 提供應用 identity tokens，不是 Windows Kerberos domain。
- **D：** 不正確。Permission set 產生 AWS permissions，不提供 AD domain controllers。

**事實查證：** [Manage your identity source](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source.html)、[AWS Directory Service Administration Guide](https://docs.aws.amazon.com/directoryservice/latest/admin-guide/what_is.html)

### 練習題 6｜SAA｜Identity Center versus Cognito

零售網站預期 300 萬名消費者註冊、登入與重設密碼；他們不需要 AWS console。應選哪個 identity 類型？

A. 使用 Amazon Cognito 等 customer identity service；Identity Center 保留給 workforce access
B. 把消費者放進 Organizations OUs
C. 為每人建立 Identity Center workforce user
D. 為每名客戶建立 IAM user

**答案：A**

- **A：** 正確。Consumer authentication/token 與員工 AWS account access 是不同 domain，Cognito 適合前者。
- **B：** 不正確。OU 組織 AWS accounts，不組織網站終端使用者。 Identity lifecycle、authentication與AWS session是不同控制面；只有修改題幹所要求的那一層，答案才會翻轉。
- **C：** 不正確。Identity Center 的對象是 workforce 與 business applications，不是百萬級零售 identities。
- **D：** 不正確。IAM users 是 AWS principals，不是大規模 app customer directory。

**事實查證：** [What is IAM Identity Center?](https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html)、[What is Amazon Cognito?](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html)

### 練習題 7｜SAA｜Least-privilege account assignments

同一 finance group 在 production 只需 billing read-only，在 sandbox 則可管理測試資源。最佳配置是什麼？

A. 在 organization root 給 finance AdministratorAccess
B. 把 production 放到 sandbox OU 即自動授權
C. 讓所有人共用一個 admin role session
D. 建立不同 permission sets，分別對 finance group+production accounts 與 finance group+sandbox accounts assignment

**答案：D**

- **A：** 不正確。Root-level broad access 違反環境差異與 least privilege。
- **B：** 不正確。OU 本身不是 identity permission grant。 Identity lifecycle、authentication與AWS session是不同控制面；只有修改題幹所要求的那一層，答案才會翻轉。
- **C：** 不正確。共享 session 破壞 attribution，且無法表達 account-specific privilege。
- **D：** 正確。Identity Center assignment 可讓同群組在不同帳號取得不同 role，符合工作內容與環境風險。

**事實查證：** [Manage AWS accounts with permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)、[AWS Organizations terminology and concepts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html)

### 練習題 8｜SAP｜Deprovisioning and active sessions

SCIM已停用離職者，但SOC確認他仍可能持有Identity Center portal session與先前取得的permission-set CLI credentials。最完整的處置順序是什麼？

A. 只改permission set名稱，既有credentials會立即失效
B. 刪除CloudTrail事件，避免離職者從log找到session ID
C. 只等待所有sessions自然到期，因為Identity Center沒有任何session處置能力
D. 先在IdP/SCIM阻止新登入與assignment，結束active portal sessions，revoke active permission-set sessions；若仍有其他STS路徑則加適用explicit Deny並監控，最後確認credentials到期

**答案：D**

- **A：** 不正確。重新命名不會改變先前簽發credentials的有效性。必須使用documented revocation流程或授權層Deny，並理解不同session類型。
- **B：** 不正確。CloudTrail事件是調查證據，且log中的session識別資訊不是可重用secret；刪除事件不會撤銷任何AWS credentials。
- **C：** 不正確。自然到期是最後邊界，但Identity Center支援結束portal session與revoke permission-set account sessions。只有低風險且session很短時才可能接受等待。
- **D：** 正確。這個順序分別處理新authentication、portal入口、account role credentials與其他STS例外。Revocation可能以新Deny影響舊session，因此還要監控與驗證實際request已被拒。

**事實查證：** [Automatic provisioning with SCIM](https://docs.aws.amazon.com/singlesignon/latest/userguide/provision-automatically.html)、[End active IAM Identity Center user sessions](https://docs.aws.amazon.com/singlesignon/latest/userguide/end-active-sessions.html)、[Revoke IAM Identity Center user permissions and account sessions](https://docs.aws.amazon.com/singlesignon/latest/userguide/revoke-user-permissions.html)、[Revoke IAM role temporary security credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_revoke-sessions.html)

### 練習題 9｜SAP｜Delegated administration

中央security team保有Identity Center核心與management-account-only設定；platform team只需在核准accounts中管理指定permission sets的assignments。哪兩項最符合least-privilege delegation？（選兩項）

A. 中央團隊保留management-account-only tasks、permission-set邊界與CloudTrail監控，並定期審查delegated administrator的變更
B. 使用Identity Center delegated administrator，並以具名IAM actions/resources與可用的tags/conditions限制可管理的account assignments和permission sets
C. 共用management-account administrator password，但用工單記錄誰借用
D. 讓platform team日常使用management-account root，因為delegation仍需管理組織
E. 在每個member account建立local admin users，讓platform team避開Identity Center限制

**答案：A、B**

- **A：** 正確。部分組織與Identity Center工作仍只屬management account；中央團隊也要保護permission-set模板、記錄CreateAccountAssignment等事件並審查權限擴張。
- **B：** 正確。Delegated administrator把可支援的日常Identity Center工作移出management account；仍應把iam/sso API縮到核准permission sets、accounts與assignment操作，不能授予blanket organization admin。
- **C：** 不正確。共享密碼無法提供個人attribution，且撤權等於影響所有人。工單不能補回authentication、MFA與session層的缺口。
- **D：** 不正確。Root具有最大blast radius且沒有可細分session policy；root只做root-only recovery。Platform日常工作應由delegated admin中的具名role完成。
- **E：** 不正確。Local admins重新引入分散MFA、入離職與credential inventory，並讓集中assignment無法成為單一控制面。只有無法federate的孤立recovery帳號才可能例外。

**事實查證：** [Delegated administration for IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/delegated-admin.html)、[Assign user or group access to AWS accounts](https://docs.aws.amazon.com/singlesignon/latest/userguide/assignusers.html)、[CloudTrail record contents](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html)

### 練習題 10｜SAP｜Identity dependency break-glass

外部IdP與SCIM同時不可用時，公司仍需修復production，但不希望為每位員工保留local admin。哪兩項構成可用的Identity Center resilience方案？（選兩項）

A. 由獨立credential root啟動少數emergency identities：雙人保管、硬體MFA、只能assume受限production recovery role，且不依賴故障IdP
B. 事故時暫時關閉所有MFA，讓任何仍記得密碼的人登入
C. 永久鏡像所有workforce users為每帳號AdministratorAccess IAM users
D. 演練activation與recovery：即時告警、短session、操作記錄、revoke、credential reset與事後審查；root僅處理root-only工作
E. 只建立emergency role，但trust仍只允許故障中的同一IdP

**答案：A、D**

- **A：** 正確。它明確回答第一組AWS credentials從哪裡來，並以custodian、MFA、trust與最小actions把emergency identity的長期風險限制住。
- **B：** 不正確。移除MFA會在身份系統最脆弱時放大account takeover。若原MFA服務也是故障域，應預先準備獨立硬體因素，而不是降低authentication。
- **C：** 不正確。大量永久admin會把break-glass變成日常攻擊面，還要在每個account分別管理離職與keys。應只保留極少數、可審計的independent bootstrap。
- **D：** 正確。未演練的credential、MFA或trust policy可能已失效；使用後revocation與reset避免緊急能力長期暴露，CloudTrail與告警則提供個人責任歸屬。
- **E：** 不正確。Role不是登入起點；唯一trust path依賴故障IdP時仍不可用。必須提供不共用同一故障域的IAM emergency identity或第二federation path。

**事實查證：** [Set up emergency access to the AWS Management Console](https://docs.aws.amazon.com/singlesignon/latest/userguide/emergency-access.html)、[End active IAM Identity Center user sessions](https://docs.aws.amazon.com/singlesignon/latest/userguide/end-active-sessions.html)、[Revoke IAM role temporary security credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_revoke-sessions.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「整合外部IdP，使用permission sets下發temporary role sessions並集中…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「企業需要集中人員生命週期、MFA與多帳號權限，而非在每個帳號建立user。」，所以「整合外部IdP，使用permission sets下發temporary role sessions並集中assignments。」能直接滿足它；若constraint改成「Directory Service適合需要managed Microsoft AD語意的workload，不等於所有console federation。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「整合外部IdP，使用permission sets下發temporary role sessions並集中assignments。」。替代方案「Directory Service適合需要managed Microsoft AD語意的workload，不等於所有console federation。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「離職只停用一個帳號卻遺留各AWS帳號local users與access keys。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「企業需要集中人員生命週期、MFA與多帳號權限，而非在每個帳號建立user。」，排除會導致「離職只停用一個帳號卻遺留各AWS帳號local users與access keys。」的選項，再選「整合外部IdP，使用permission sets下發temporary role sessions並集中assignments。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「整合外部IdP，使用permission sets下發temporary role sessions並集中assignments。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「centralize workforce identity, decentralize workload roles」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 25 章　Organizations、OU、SCP 與 Control Tower

多帳號需要一致guardrails、帳號供應、log與安全基線。

## 跟著一次授權決定走：先從故事開始

故事從一個看似簡單的需求開始：公司快速建立上百個帳號，要求禁止關閉CloudTrail及限制未核准Region。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：多帳號需要一致guardrails、帳號供應、log與安全基線。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把身份系統想成辦公大樓：登入證明你是誰，門禁規則才決定你能進哪一間房。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS Organizations會是本章的主要角色，AWS Control Tower則幫我們看清邊界。方向是「Organizations建立階層，SCP限制最大權限，Control Tower提供landing zone與預防/偵測controls。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：公司快速建立上百個帳號，要求禁止關閉CloudTrail及限制未核准Region。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[AWS Organizations] ── Allow / Deny ──> protected resource
          │ 集中建立accounts、OU、政策與consolidated billing。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · AWS Control Tower：建立與治理符合best practices的multi-account landing zone。
  · Service control policies：在Organizations中設定member account principals的最大權限邊界。

失敗時先找：用SCP寫細粒度應用權限，或測試不足便在root套explicit deny。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問AWS Organizations有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Organizations和AWS Control Tower並不是兩個任意的產品名稱。前者適合本章，是因為「Organizations建立階層，SCP限制最大權限，Control Tower提供landing zone與預防/偵測controls。」直接回應了眼前的問題；後者描述的「SCP不授權且不影響management account；過度集中OU會使例外與blast radius難管理。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：用SCP寫細粒度應用權限，或測試不足便在root套explicit deny。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「govern centrally, operate within bounded accounts」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 |
| AWS Control Tower | 建立與治理符合best practices的multi-account landing zone。 | 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。 |
| Service control policies | 在Organizations中設定member account principals的最大權限邊界。 | SCP與identity/resource allow形成交集；它不授權，explicit deny可阻止member account root。 |

## 把全圖套進一個具體案例

**場景：** 公司快速建立上百個帳號，要求禁止關閉CloudTrail及限制未核准Region。

1. 故事的起點：公司快速建立上百個帳號，要求禁止關閉CloudTrail及限制未核准Region。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Organizations負責「集中建立accounts、OU、政策與consolidated billing。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Control Tower、Service control policies各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「用SCP寫細粒度應用權限，或測試不足便在root套explicit deny。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「單一account內的日常permission仍用IAM；不要在management account執行workloads。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Organizations

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：多帳號需要一致guardrails、帳號供應、log與安全基線。
- **具體例子／邊界：** 在「公司快速建立上百個帳號，要求禁止關閉CloudTrail及限制未核准Region。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Control Tower

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：SCP不授權且不影響management account；過度集中OU會使例外與blast radius難管理。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：用SCP寫細粒度應用權限，或測試不足便在root套explicit deny。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：govern centrally, operate within bounded accounts。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### explicit Deny

明確拒絕request的policy結果；只要任一applicable policy命中Deny，就會覆蓋Allow。

### blast radius

一個故障、bug或錯誤變更最多能影響的使用者、租戶、accounts或Regions範圍。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### drift

實際resource設定與IaC宣告狀態不同，常由console手動修改或外部automation造成。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

## 回到 AWS：Components、功用與責任邊界

### AWS Organizations

- **功用：** 集中建立accounts、OU、政策與consolidated billing。
- **底層機制：** Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
- **關鍵設定：** roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- **選擇時機：** 多團隊、多環境、blast-radius隔離與central governance。
- **替換時機：** 單一account內的日常permission仍用IAM；不要在management account執行workloads。

### AWS Control Tower

- **功用：** 建立與治理符合best practices的multi-account landing zone。
- **底層機制：** 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。
- **關鍵設定：** landing zone Regions、OU、controls、Account Factory/AFT、log archive、audit account與drift repair。
- **選擇時機：** 快速建立一致account vending與preventive/detective/proactive controls。
- **替換時機：** 高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。

### Service control policies

- **功用：** 在Organizations中設定member account principals的最大權限邊界。
- **底層機制：** SCP與identity/resource allow形成交集；它不授權，explicit deny可阻止member account root。
- **關鍵設定：** target root/OU/account、Allow-list或Deny-list strategy、conditions、NotAction與policy inheritance。
- **選擇時機：** 禁止離開核准Region、關閉audit、使用未核准服務等organization guardrails。
- **替換時機：** 應用角色的日常權限用IAM；資源對外access的中央邊界可用RCP。

## 考前與實作時再查：設定操作手冊

### AWS Organizations：逐項設定說明

#### `roots/OUs/accounts`

- **控制什麼：** `roots/OUs/accounts`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `SCP/RCP/tag/backup policies`

- **控制什麼：** `SCP/RCP/tag/backup policies`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `delegated admins`

- **控制什麼：** `delegated admins`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `trusted access`

- **控制什麼：** `trusted access`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `billing sharing`

- **控制什麼：** `billing sharing`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

### AWS Control Tower：逐項設定說明

#### `landing zone Regions`

- **控制什麼：** `landing zone Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS Control Tower前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `OU`

- **控制什麼：** `OU`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `controls`

- **控制什麼：** `controls`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `Account Factory/AFT`

- **控制什麼：** `Account Factory/AFT`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `log archive`

- **控制什麼：** `log archive`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `audit account`

- **控制什麼：** `audit account`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `drift repair`

- **控制什麼：** `drift repair`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「快速建立一致account vending與preventive/detective/proactive controls。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Control Tower設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

### Service control policies：逐項設定說明

#### `target root/OU/account`

- **控制什麼：** `target root/OU/account`指定Service control policies讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Allow-list或Deny-list strategy`

- **控制什麼：** `Allow-list或Deny-list strategy`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `conditions`

- **控制什麼：** `conditions`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「禁止離開核准Region、關閉audit、使用未核准服務等organization guardrails。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Service control policies以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `NotAction`

- **控制什麼：** `NotAction`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

#### `policy inheritance`

- **控制什麼：** `policy inheritance`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「禁止離開核准Region、關閉audit、使用未核准服務等organization guardrails。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Service control policies明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

## 可以直接對照 AWS 的設定範例

### SCP：禁止關閉組織 audit trail

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyDisablingAudit",
    "Effect": "Deny",
    "Action": [
      "cloudtrail:StopLogging",
      "cloudtrail:DeleteTrail",
      "config:StopConfigurationRecorder",
      "config:DeleteConfigurationRecorder"
    ],
    "Resource": "*"
  }]
}
```

1. SCP只設最大權限；即使沒有這份Deny，也不會自動授權任何人操作CloudTrail。
2. 先在sandbox OU驗證，再漸進套用；直接掛organization root可能阻斷break-glass與automation。
3. SCP不影響management account，因此management account不應承載一般workload。

## 讀到這裡，請用自己的話說一次

1. AWS Organizations的責任：集中建立accounts、OU、政策與consolidated billing。
2. 底層機制：Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
3. 第一個要看的設定：roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
4. 選擇邏輯：Organizations建立階層，SCP限制最大權限，Control Tower提供landing zone與預防/偵測controls。
5. 不要混淆：AWS Control Tower的責任是「建立與治理符合best practices的multi-account landing zone。」；它不會自動取代AWS Organizations。
6. 替換訊號：單一account內的日常permission仍用IAM；不要在management account執行workloads。
7. 最常見錯法：用SCP寫細粒度應用權限，或測試不足便在root套explicit deny。
8. 可移植原則：govern centrally, operate within bounded accounts。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 | 多團隊、多環境、blast-radius隔離與central governance。 | 單一account內的日常permission仍用IAM；不要在management account執行workloads。 |
| AWS Control Tower | 建立與治理符合best practices的multi-account landing zone。 | 在Organizations、Identity Center、Config/CloudTrail等之上佈署controls、account baseline與dashboard。 | 快速建立一致account vending與preventive/detective/proactive controls。 | 高度自訂既有Organizations可能需漸進enrollment；Control Tower不是新型hypervisor。 |
| Service control policies | 在Organizations中設定member account principals的最大權限邊界。 | SCP與identity/resource allow形成交集；它不授權，explicit deny可阻止member account root。 | 禁止離開核准Region、關閉audit、使用未核准服務等organization guardrails。 | 應用角色的日常權限用IAM；資源對外access的中央邊界可用RCP。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | SCP不授權且不影響management account；過度集中OU會使例外與blast radius難管理。 | 只有當題目條件明確改變時才可能合理。 | 用SCP寫細粒度應用權限，或測試不足便在root套explicit deny。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「SCP不授權且不影響management account；過度集中OU會使例外與blast radius難管理。」之間做選擇。
- 認得常考設定：roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：單一account內的日常permission仍用IAM；不要在management account執行workloads。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAP｜Account as a security boundary

企業希望 prod、dev、security logs 與 shared services 有獨立 owner、quota 與 blast radius。哪個基礎結構最合適？

A. 依治理目的建立多個 member accounts，再放入政策需求相近的 OUs；management account 不承載日常 workloads
B. 一個 VPC 等同完整 account IAM boundary
C. 全部放單一 account，以 resource name 區分
D. 所有 production workloads 放 management account 方便管理

**答案：A**

- **A：** 正確。Account 是資源、身份、quota 與 billing 的強邊界；OU 用來套用共同 governance。
- **B：** 不正確。VPC 是 network boundary，不隔離 account-level IAM/billing。
- **C：** 不正確。名稱與 tags 不能隔離 root/admin、quotas 或 account compromise。
- **D：** 不正確。Management account 不受 SCP 保護且權限極高，應最小化資源。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。

**事實查證：** [AWS Organizations terminology and concepts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html)、[SAP-C02 Domain 1: Design Solutions for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)

### 練習題 2｜SAA｜Inherited SCP ceiling

OU 的 SCP 允許 s3:*，但 member account 的 AnalystRole 沒有任何 S3 Allow。AnalystRole 能列 bucket 嗎？

A. 只有 management account 會被 SCP 授權
B. 能，若 payer account 開啟 consolidated billing
C. 不能；SCP 只定義最大可用範圍，仍需 IAM/resource Allow
D. 能，SCP Allow 是 inherited identity policy

**答案：C**

- **A：** 不正確。SCP 不影響 management account principals。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。
- **B：** 不正確。Billing 與 authorization 無關。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。
- **C：** 正確。Effective permission 必須在 organization ceiling 內，並由 identity/resource policy真正授權。
- **D：** 不正確。SCP 不附到 role，也不建立 permissions。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。

**事實查證：** [Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 3｜SAP｜Organization trail ownership and adjacent protection

Organization trail由management account建立，workload member-account administrator嘗試呼叫StopLogging或DeleteTrail來停止它。哪項敘述最準確？

A. Organization trail只能由management account或CloudTrail delegated administrator建立、更新與刪除；member account可見但不能修改。SCP仍可保護member本來能改的local trails、Config/EventBridge與logging destinations
B. Member account可直接停止organization trail，因此只能依靠Config事後告警
C. 只要log bucket有Object Lock，member account就能停止trail但不會有影響
D. Allow SCP列出cloudtrail:StopLogging即可阻止member administrator

**答案：A**

- **A：** 正確。Native ownership先回答member能否操作；再用SCP保護local trail與相鄰logging resources，避免把一個原本無權的API誤當成SCP唯一價值。
- **B：** 不正確。題幹指定organization trail，CloudTrail原生ownership已阻止member修改；Config可補充監控，但不是唯一防線。若題幹改成member自建local trail，SCP Deny才是主要preventive guardrail。
- **C：** 不正確。Object Lock保護已寫入的log objects，不能決定誰能管理organization trail；它與trail control plane是不同責任。
- **D：** 不正確。Allow SCP不會產生Deny，而且member本來就不能停止organization trail。若要保護local logging APIs，應用經測試的explicit Deny並保留必要service-role例外。

**事實查證：** [Creating an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)、[Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)

### 練習題 4｜SAP｜Region restriction design

公司只准在 ap-southeast-1 與 us-east-1 建區域資源，但 IAM、Route 53 等 global services 必須正常。哪個 SCP 模式最合理？

A. 刪除其他 Regions 的 route tables
B. 把 Console default Region 設為 ap-southeast-1
C. Deny 所有 actions，完全不設例外
D. 使用 aws:RequestedRegion condition，並以經審查的 NotAction 例外處理必要 global services，先在 canary OU 測試

**答案：D**

- **A：** 不正確。許多 services 不依 VPC routes，且資源仍可被建立。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。
- **B：** 不正確。Console 預設值不限制 API/CLI。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。
- **C：** 不正確。會中斷 global identity、billing 或支援依賴。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。
- **D：** 正確。Region condition 搭配明確 global-service exceptions 才能表達 guardrail，且需 staged rollout 防止大面積鎖死。

**事實查證：** [Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)、[AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)

### 練習題 5｜SAA｜Control Tower control types

公司要分別：(1) 阻止不合規 API；(2) 找出已存在的違規 resource；(3) 在 CloudFormation provisioning 前拒絕 template resource。對應 control 類型為何？

A. 三者都只能由 AWS Config 實作
B. 三者都是 WAF rules
C. Preventive、detective、proactive
D. Detective、preventive、SCP

**答案：C**

- **A：** 不正確。Config 支援多數 detective controls，不承擔所有 preventive/proactive semantics。
- **B：** 不正確。WAF 只處理支援入口的 HTTP(S) requests。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。
- **C：** 正確。Preventive 在 request 層限制，detective 常由 Config 評估現況，proactive 於 CloudFormation provisioning 前檢查。
- **D：** 不正確。Detective 不阻擋原始 API，且第三項是 proactive。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。

**事實查證：** [AWS Control Tower controls reference introduction](https://docs.aws.amazon.com/controltower/latest/controlreference/introduction.html)、[What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)

### 練習題 6｜SAP｜Control Tower relationship to Organizations

既有 AWS Organization 想加入 account vending、landing-zone baselines 與集中 control dashboard。哪項描述最準確？

A. Control Tower 自動遷移所有 workloads
B. Control Tower 在 Organizations、Identity Center、Config、CloudTrail 等能力上編排 landing zone；既有 accounts 需評估 enrollment 與 drift
C. Control Tower 是 packet inspection firewall
D. Control Tower 取代 Organizations

**答案：B**

- **A：** 不正確。Landing zone 不會代替 workload migration planning。
- **B：** 正確。Control Tower 是治理編排層，不抹除底層 services；既有環境需處理 baseline 相容與 drift。
- **C：** 不正確。流量檢查由 WAF/Network Firewall 等 data-plane controls 負責。
- **D：** 不正確。Organizations 仍提供 account hierarchy 與 policies。

**事實查證：** [AWS Control Tower controls reference introduction](https://docs.aws.amazon.com/controltower/latest/controlreference/introduction.html)、[AWS Organizations terminology and concepts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html)

### 練習題 7｜SAP｜GuardDuty and Security Hub CSPM delegated administration

企業要由Security Tooling account集中管理GuardDuty與Security Hub CSPM（舊教材常簡稱Security Hub），並避免在Organizations management account日常操作。應採取什麼？

A. 共享management-account root credentials給SOC值班人員
B. 由management account為每個服務啟用trusted access並指定其支援的delegated administrator；再分別配置GuardDuty與Security Hub CSPM的member enrollment、Region與central configuration
C. 只用Security Hub CSPM invitation把tooling account當一般外部member，不啟用Organizations整合
D. 附加Allow SCP即可自動建立兩個服務的delegated administrator

**答案：B**

- **A：** 不正確。Root沒有日常least-privilege邊界，會把單一credential變成organization級風險。Delegated administrator就是為了把服務操作移出management account。
- **B：** 正確。GuardDuty與Security Hub CSPM是不同服務整合，delegated admin與Regional coverage需分別建立；CSPM的ASFF/controls語意也不能混成新AWS Security Hub的OCSF/exposure模型。
- **C：** 不正確。Invitation模型可連結帳號，但不等於Organizations delegated administration，也不自動涵蓋新accounts與各Region。只有不使用Organizations時才可能採邀請模式。
- **D：** 不正確。SCP只限制maximum permissions，不會呼叫服務API、啟用trusted access或註冊delegated administrator。仍需management account執行各服務的正式整合流程。

**事實查證：** [AWS Organizations terminology and concepts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html)、[GuardDuty organization auto-enable preferences](https://docs.aws.amazon.com/guardduty/latest/ug/set-guardduty-auto-enable-preferences.html)、[Integrating Security Hub CSPM with AWS Organizations](https://docs.aws.amazon.com/securityhub/latest/userguide/designate-orgs-admin-account.html)、[Introduction to AWS Security Hub CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)

### 練習題 8｜SAP｜OU design by policy

Finance 與 Engineering 的一般 workloads 需要相同 controls；regulated workloads 則需更嚴格 data residency 與 logging。OU 應如何設計？

A. 用 OUs 建立 VPC routing
B. 完全照 HR 組織圖，每位主管一個 OU
C. 盡量巢狀十層以自動提高安全
D. 依治理、lifecycle 與 policy inheritance 分組 accounts；regulated accounts 放入較嚴格 OU

**答案：D**

- **A：** 不正確。OU 不建立 network routes。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。
- **B：** 不正確。Reporting hierarchy 常與技術 guardrails 不一致，造成重複與例外。
- **C：** 不正確。深度本身不等於安全，反而增加 inheritance 推理成本。 Organizations治理要區分native ownership、guardrail與實際授權；不能把OU、SCP或billing當成同一種機制。
- **D：** 正確。OU 的主要價值是共同 policies 與 operating model；account 可隨 governance 需求調整位置。

**事實查證：** [AWS Organizations terminology and concepts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html)、[Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)

### 練習題 9｜SAP｜Safe SCP rollout

新的 SCP Deny 可能影響 200 個 production accounts。哪兩個 rollout 做法最安全？（選兩項）

A. 以 sandbox/canary OU 測試，使用 service-last-access 與 CloudTrail 分析實際依賴
B. 只驗證 JSON syntax 即視為完成
C. 分階段擴大 attachment、監控 denied calls，並保留由 organization 管理者執行的 recovery path
D. 先附到 organization root，再看哪些系統故障
E. 在 member accounts 加 AdministratorAccess 作為 SCP bypass

**答案：A、C**

- **A：** 正確。Service/action last-access與CloudTrail能產生候選依賴清單，但「觀測窗內沒用」不代表年度結帳、DR或maintenance永遠不需；因此仍要owner確認與演練。
- **B：** 不正確。JSON語法只證明policy可被解析，不證明effective permissions符合DR、月結或service integration。必須測試語意與真實依賴。
- **C：** 正確。Staged attachment、AccessDenied監控與organization-side rollback可控制blast radius；每一階段仍要驗證business transaction而不只是API成功。
- **D：** 不正確。直接附到root會同時影響所有OUs，若NotAction、Region或service-role例外錯誤，會造成大面積中斷。只有canary與分階段證據足夠後才向上擴大。
- **E：** 不正確。Member account的AdministratorAccess仍受SCP explicit Deny限制，不能作bypass。Recovery必須由有權調整Organizations policy的獨立管理路徑完成。

**事實查證：** [Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)、[Refine permissions using last accessed information](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_last-accessed.html)、[Working with CloudTrail event history](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html)

### 練習題 10｜SAP · ENRICHMENT-CURRENT｜ENRICHMENT-CURRENT: RCP versus SCP

依2026-10-01的現行AWS能力，中央member accounts中的支援資源要拒絕organization外部principals，即使resource owner誤設permissive policy。哪兩項觀念正確？（選兩項）

A. RCP可附到organization root、OU或account，對現行支援服務的resource形成permission ceiling；必須查官方支援清單，不能泛化到所有AWS resources
B. RCP不會影響member account中的resource，也不影響root user request
C. RCP Allow會自行授權外部principal，即使resource policy與identity policy都沒有Allow
D. SCP可直接附到單一bucket ARN，並限制任何外部principal如何使用該bucket
E. RCP不授權；外部principal仍需先有identity/resource Allow。RCP可否決該resource的存取，但不適用management-account resources，service-linked roles與部分列明例外也不受其限制

**答案：A、E**

- **A：** 正確。截至2026-10-01，Organizations官方清單列出62個支援RCP的服務前綴，包含S3、KMS、SQS、Secrets Manager、STS、DynamoDB、CloudFront、CloudWatch Logs、ECR、WAF等；仍須依該action的Resource type逐項確認，不能把服務級支援誤解為所有actions與resources都適用。
- **B：** 不正確。RCP正是限制member-account resources，且可影響包含root在內的request；但management-account resources、service-linked roles與文件列明例外不在其一般範圍。
- **C：** 不正確。RCP與SCP一樣是guardrail而非grant；沒有resource/identity Allow時仍是implicit deny。只有先存在授權路徑，RCP ceiling才決定它是否可生效。
- **D：** 不正確。SCP附到root/OU/account並限制member-account principals，不能附到resource ARN。要限制外部principal對組織內resource的最大權限，才考慮RCP。
- **E：** 正確。這同時交代grant與ceiling、member與management account、一般principal與service-linked role的邊界，避免把RCP誤寫成全服務、全資源的萬用policy。

**事實查證：** [Resource control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Organizations建立階層，SCP限制最大權限，Control Tower提供landing zo…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「多帳號需要一致guardrails、帳號供應、log與安全基線。」，所以「Organizations建立階層，SCP限制最大權限，Control Tower提供landing zone與預防/偵測controls。」能直接滿足它；若constraint改成「SCP不授權且不影響management account；過度集中OU會使例外與blast radius難管理。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Organizations建立階層，SCP限制最大權限，Control Tower提供landing zone與預防/偵測controls。」。替代方案「SCP不授權且不影響management account；過度集中OU會使例外與blast radius難管理。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「用SCP寫細粒度應用權限，或測試不足便在root套explicit deny。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「多帳號需要一致guardrails、帳號供應、log與安全基線。」，排除會導致「用SCP寫細粒度應用權限，或測試不足便在root套explicit deny。」的選項，再選「Organizations建立階層，SCP限制最大權限，Control Tower提供landing zone與預防/偵測controls。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Organizations建立階層，SCP限制最大權限，Control Tower提供landing zone與預防/偵測controls。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「govern centrally, operate within bounded accounts」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 26 章　Resource Policy、Boundary 與 Delegated Administration

平台團隊需要讓應用團隊自行建立role，同時確保不能超過安全上限。

## 跟著一次授權決定走：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：平台允許各團隊建立deployment roles，但不得讀取其他產品資料。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：平台團隊需要讓應用團隊自行建立role，同時確保不能超過安全上限。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：登入像出示員工證，policy像每扇門旁的門禁規則；有證件不代表所有房間都能進。 AWS授權由多層policy共同決定，還要考慮explicit Deny、resource policy與organization guardrail。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。IAM permissions boundaries負責主要工作，Resource policies提醒我們答案不是永遠固定。本章會走向「用permissions boundary限制可委派權限；resource policy授權資源；delegated admin把服務管理移出management account。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：平台允許各團隊建立deployment roles，但不得讀取其他產品資料。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[IAM permissions boundaries] ── Allow / Deny ──> protected resource
          │ 限制單一IAM user/role可被identity policies授予的最大權限。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · Resource policies：把授權規則附在S3 bucket、KMS key、SQS queue等資源上並指定Principal。
  · AWS Organizations：集中建立accounts、OU、政策與consolidated billing。

失敗時先找：允許iam:*後期待開發者自律，或把resource policy Principal寫成無條件星號。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問IAM permissions boundaries有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，IAM permissions boundaries和Resource policies並不是兩個任意的產品名稱。前者適合本章，是因為「用permissions boundary限制可委派權限；resource policy授權資源；delegated admin把服務管理移出management account。」直接回應了眼前的問題；後者描述的「Tag/attribute-based access可減少policy數量，但標籤治理本身必須可信。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：允許iam:*後期待開發者自律，或把resource policy Principal寫成無條件星號。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「delegate capability inside non-bypassable boundaries」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| IAM permissions boundaries | 限制單一IAM user/role可被identity policies授予的最大權限。 | Effective identity permissions是identity allow與boundary allow的交集，且仍受SCP與explicit deny。 |
| Resource policies | 把授權規則附在S3 bucket、KMS key、SQS queue等資源上並指定Principal。 | 資源收到request時同時評估policy；cross-account通常需要target resource allow和source identity allow。 |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 |

## 把全圖套進一個具體案例

**場景：** 平台允許各團隊建立deployment roles，但不得讀取其他產品資料。

1. 故事的起點：平台允許各團隊建立deployment roles，但不得讀取其他產品資料。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：IAM permissions boundaries負責「限制單一IAM user/role可被identity policies授予的最大權限。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Effective identity permissions是identity allow與boundary allow的交集，且仍受SCP與explicit deny。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Resource policies、AWS Organizations各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「允許iam:*後期待開發者自律，或把resource policy Principal寫成無條件星號。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「跨全組織限制用SCP；對資源本身授權用resource policy。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### Verified Permissions：IAM 管 AWS API；應用程式自己的權限要有另一個 policy decision point

IAM 回答的是 principal 能否呼叫 AWS action；你的 SaaS 還會有『Alice 能不能編輯 tenant B 的 invoice』。把後者硬寫在每個 controller 容易產生不一致。Verified Permissions 用 Cedar policy store 集中application authorization，application 每次帶 principal、action、resource 與 context 問 Allow/Deny。

```text
authenticated user
      │ token/claims
      ▼
application ─ IsAuthorized(principal, action, resource, context)
      │                              │
      │                              ▼
      └──────────────────── policy store (Cedar)
                        allow / deny + decision log
```

#### 一條 policy 應表達 business resource，而不是 AWS ARN 清單

```Cedar
permit (
  principal in Group::"support",
  action == Action::"ReadTicket",
  resource
)
when { resource.tenant == principal.tenant };
```

1. principal/action/resource 是應用 domain；不要把它和 IAM Action/Resource 混為同一份 policy。
2. Token 證明登入資訊，但 policy engine 才結合 resource ownership、tenant 與 context 做授權。
3. Policy update 是 control plane；每次 IsAuthorized 是 data path。需要 latency、cache、deny default 與失效策略。

**選擇邊界：** AWS 資源權限用 IAM/resource policy/SCP/boundary；application fine-grained authorization 才評估Verified Permissions。兩者常一起出現，但責任完全不同。

**考試範圍：** SAA 先掌握 authentication/authorization 與 IAM evaluation；Verified Permissions、Cedar schema、policy store rollout 是現代應用安全延伸；在SAP-C03完整考綱發布前，不把它標成正式計分task。

- [AWS：What is Amazon Verified Permissions?](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/what-is-avp.html)

## 需要時再查：四個閱讀支點

### IAM permissions boundaries

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：平台團隊需要讓應用團隊自行建立role，同時確保不能超過安全上限。
- **具體例子／邊界：** 在「平台允許各團隊建立deployment roles，但不得讀取其他產品資料。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Resource policies

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Tag/attribute-based access可減少policy數量，但標籤治理本身必須可信。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：允許iam:*後期待開發者自律，或把resource policy Principal寫成無條件星號。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：delegate capability inside non-bypassable boundaries。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### explicit Deny

明確拒絕request的policy結果；只要任一applicable policy命中Deny，就會覆蓋Allow。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

## 回到 AWS：Components、功用與責任邊界

### IAM permissions boundaries

- **功用：** 限制單一IAM user/role可被identity policies授予的最大權限。
- **底層機制：** Effective identity permissions是identity allow與boundary allow的交集，且仍受SCP與explicit deny。
- **關鍵設定：** managed policy ARN、iam:PermissionsBoundary creation condition與防止移除boundary的guardrail。
- **選擇時機：** 平台委派團隊建立roles，但不允許超出安全上限。
- **替換時機：** 跨全組織限制用SCP；對資源本身授權用resource policy。

### Resource policies

- **功用：** 把授權規則附在S3 bucket、KMS key、SQS queue等資源上並指定Principal。
- **底層機制：** 資源收到request時同時評估policy；cross-account通常需要target resource allow和source identity allow。
- **關鍵設定：** Principal、Action、Resource、Condition、organization/account/service principal與explicit Deny。
- **選擇時機：** cross-account、service delivery、centralized resource ownership或resource-level data perimeter。
- **替換時機：** 只管理一組role/user可做什麼時以identity policy較易重用。

### AWS Organizations

- **功用：** 集中建立accounts、OU、政策與consolidated billing。
- **底層機制：** Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。
- **關鍵設定：** roots/OUs/accounts、SCP/RCP/tag/backup policies、delegated admins、trusted access與billing sharing。
- **選擇時機：** 多團隊、多環境、blast-radius隔離與central governance。
- **替換時機：** 單一account內的日常permission仍用IAM；不要在management account執行workloads。

## 考前與實作時再查：設定操作手冊

### IAM permissions boundaries：逐項設定說明

#### `managed policy ARN`

- **控制什麼：** `managed policy ARN`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「平台委派團隊建立roles，但不允許超出安全上限。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM permissions boundaries明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `iam:PermissionsBoundary creation condition`

- **控制什麼：** `iam:PermissionsBoundary creation condition`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「平台委派團隊建立roles，但不允許超出安全上限。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在IAM permissions boundaries明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `防止移除boundary的guardrail`

- **控制什麼：** `防止移除boundary的guardrail`是policy statement識別、API action/resource配對，或保護permissions boundary不被委派管理者繞過的設定。
- **何時需要：** 要寫可review的IAM/S3 least-privilege policy，或允許團隊建role但不能突破平台上限時。
- **怎麼設定／驗證：** Sid使用可讀名稱；Action配正確resource ARN。ListBucket使用bucket ARN，GetObject使用object ARN；以condition/SCP拒絕移除核准boundary。
- **常見錯法：** Sid不影響授權；bucket/object ARN配反會AccessDenied。只附boundary卻允許建立者移除它，等於沒有安全上限。

### Resource policies：逐項設定說明

#### `Principal`

- **控制什麼：** `Principal`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、service delivery、centralized resource ownership或resource-level data perimeter。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Resource policies明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `Action`

- **控制什麼：** `Action`是policy statement識別、API action/resource配對，或保護permissions boundary不被委派管理者繞過的設定。
- **何時需要：** 要寫可review的IAM/S3 least-privilege policy，或允許團隊建role但不能突破平台上限時。
- **怎麼設定／驗證：** Sid使用可讀名稱；Action配正確resource ARN。ListBucket使用bucket ARN，GetObject使用object ARN；以condition/SCP拒絕移除核准boundary。
- **常見錯法：** Sid不影響授權；bucket/object ARN配反會AccessDenied。只附boundary卻允許建立者移除它，等於沒有安全上限。

#### `Resource`

- **控制什麼：** `Resource`指定Resource policies讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Condition`

- **控制什麼：** `Condition`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「cross-account、service delivery、centralized resource ownership或resource-level data perimeter。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Resource policies以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `organization/account/service principal`

- **控制什麼：** `organization/account/service principal`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「cross-account、service delivery、centralized resource ownership或resource-level data perimeter。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Resource policies明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `explicit Deny`

- **控制什麼：** `explicit Deny`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。
- **何時需要：** 需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。
- **怎麼設定／驗證：** 使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。
- **常見錯法：** NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。

### AWS Organizations：逐項設定說明

#### `roots/OUs/accounts`

- **控制什麼：** `roots/OUs/accounts`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `SCP/RCP/tag/backup policies`

- **控制什麼：** `SCP/RCP/tag/backup policies`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `delegated admins`

- **控制什麼：** `delegated admins`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `trusted access`

- **控制什麼：** `trusted access`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `billing sharing`

- **控制什麼：** `billing sharing`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多團隊、多環境、blast-radius隔離與central governance。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Organizations建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

## 讀到這裡，請用自己的話說一次

1. IAM permissions boundaries的責任：限制單一IAM user/role可被identity policies授予的最大權限。
2. 底層機制：Effective identity permissions是identity allow與boundary allow的交集，且仍受SCP與explicit deny。
3. 第一個要看的設定：managed policy ARN、iam:PermissionsBoundary creation condition與防止移除boundary的guardrail。
4. 選擇邏輯：用permissions boundary限制可委派權限；resource policy授權資源；delegated admin把服務管理移出management account。
5. 不要混淆：Resource policies的責任是「把授權規則附在S3 bucket、KMS key、SQS queue等資源上並指定Principal。」；它不會自動取代IAM permissions boundaries。
6. 替換訊號：跨全組織限制用SCP；對資源本身授權用resource policy。
7. 最常見錯法：允許iam:*後期待開發者自律，或把resource policy Principal寫成無條件星號。
8. 可移植原則：delegate capability inside non-bypassable boundaries。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| IAM permissions boundaries | 限制單一IAM user/role可被identity policies授予的最大權限。 | Effective identity permissions是identity allow與boundary allow的交集，且仍受SCP與explicit deny。 | 平台委派團隊建立roles，但不允許超出安全上限。 | 跨全組織限制用SCP；對資源本身授權用resource policy。 |
| Resource policies | 把授權規則附在S3 bucket、KMS key、SQS queue等資源上並指定Principal。 | 資源收到request時同時評估policy；cross-account通常需要target resource allow和source identity allow。 | cross-account、service delivery、centralized resource ownership或resource-level data perimeter。 | 只管理一組role/user可做什麼時以identity policy較易重用。 |
| AWS Organizations | 集中建立accounts、OU、政策與consolidated billing。 | Management account控制organization metadata；policies繼承到OU/accounts，各account仍是獨立security boundary。 | 多團隊、多環境、blast-radius隔離與central governance。 | 單一account內的日常permission仍用IAM；不要在management account執行workloads。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Tag/attribute-based access可減少policy數量，但標籤治理本身必須可信。 | 只有當題目條件明確改變時才可能合理。 | 允許iam:*後期待開發者自律，或把resource policy Principal寫成無條件星號。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Tag/attribute-based access可減少policy數量，但標籤治理本身必須可信。」之間做選擇。
- 認得常考設定：managed policy ARN、iam:PermissionsBoundary creation condition與防止移除boundary的guardrail。
- 對應官方tasks：SAA-1.1 Design secure access to AWS resources。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：跨全組織限制用SCP；對資源本身授權用resource policy。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements。

## 本章 10 題考題

### 練習題 1｜SAA｜Boundary limits delegated role creation

開發者可建立 application roles，但新 roles 絕不能管理 IAM 或 Organizations。哪個設計最符合 preventive delegation？

A. 只把 boundary 附到開發者自己
B. 用 S3 bucket policy 限制 CreateRole
C. 要求新 role 使用平台管理的 permissions boundary，並將開發者的 IAM actions 限定在採用該 boundary 的 roles
D. 靠 role 名稱前綴 app-

**答案：C**

- **A：** 不正確。Creator 自身 boundary 不會自動成為其建立之 roles 的 boundary。
- **B：** 不正確。Bucket policy只控制 S3 resource，不控制 IAM role creation。
- **C：** 正確。Boundary 限制新 role identity policies 可產生的最大權限；creator policy 也要強制指定核准 boundary。
- **D：** 不正確。名稱不是 authorization ceiling，可被超權 policy 繞過。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。

**事實查證：** [Permissions boundaries for IAM entities](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)

### 練習題 2｜SAP｜Prevent permissions-boundary bypass

DelegatedRoleBuilder 可 CreateRole、PutRolePermissionsBoundary 與 DeleteRolePermissionsBoundary。平台要防止移除或替換 ApprovedBoundary。最佳補強為何？

A. 用 IAM/SCP conditions 與 explicit Deny，限定 Create/Put 使用 ApprovedBoundary 並禁止未授權 Delete/替換
B. Boundary 會自我保護，不需其他 policy
C. 允許移除後由 Config 一週內修復
D. 只靠 CloudTrail 每季檢查

**答案：A**

- **A：** 正確。iam:PermissionsBoundary 等條件與 Deny 保護 boundary lifecycle，讓 delegation 不可自行擴權。
- **B：** 不正確。能管理 boundary 的 creator 可能自行解除 ceiling。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **C：** 不正確。延遲修復不能滿足『絕不能』，Config 也不阻擋原始 API。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **D：** 不正確。Audit 是 detective，暴露窗口已存在。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。

**事實查證：** [Permissions boundaries for IAM entities](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)、[AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)

### 練習題 3｜SAA｜Permissions boundary does not grant

OrdersRole 的 boundary 允許 dynamodb:*，但 role identity policy 只允許 logs:PutLogEvents。它能 GetItem 嗎？

A. Boundary 會取代 identity policy
B. 能，boundary 是額外 Allow
C. 不能；boundary 是 maximum，不會自行授權，identity policy仍需 Allow GetItem
D. 能，但只限同帳號 table

**答案：C**

- **A：** 不正確。兩者共同評估，boundary 不覆寫 policy 文件。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **B：** 不正確。Boundary 與 identity permissions 取交集，不是聯集。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **C：** 正確。DynamoDB 落在 ceiling 內，但缺少實際 Allow，結果仍 implicit deny。
- **D：** 不正確。同帳號不改變 boundary 不授權的事實。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。

**事實查證：** [Permissions boundaries for IAM entities](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 4｜SAP｜Role ARN versus session ARN resource grants

同帳號 resource owner 可將 Principal 寫成 IAM role ARN 或特定 assumed-role session ARN。為何 review 必須區分兩者？

A. Role ARN grant 仍受 boundary/session-policy implicit deny；直接 session-principal grant 的限制模型不同，但 explicit Deny/organization controls 仍適用
B. 兩者永遠完全相同
C. Resource Allow 一律繞過 SCP
D. Session ARN 不是 principal

**答案：A**

- **A：** 正確。Principal 類型改變 grant 是給 IAM role 還是當次 session，不能以『resource policy 都一樣』簡化。
- **B：** 不正確。官方 evaluation 明確區分 role 與 role session。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **C：** 不正確。SCP/RCP explicit Deny 仍可阻擋。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **D：** 不正確。支援的 resource policies 可指定 assumed-role session。

**事實查證：** [Identity-based policies and resource-based policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html)、[Permissions boundaries for IAM entities](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)

### 練習題 5｜SAA｜Service-to-resource confused deputy

CloudTrail要把特定trail的logs寫入中央S3 bucket。哪個bucket policy最接近官方最小且可檢查的trust形狀？

A. 信任organization內所有account root並允許任意prefix的PutObject
B. Principal:*允許s3:*，再以bucket名稱暗示只有CloudTrail會使用
C. 把AdministratorAccess附給CloudTrail service principal，不需要bucket policy
D. 允許Principal cloudtrail.amazonaws.com對bucket執行s3:GetBucketAcl，並對精確AWSLogs/account-id/* object path允許s3:PutObject；PutObject要求s3:x-amz-acl=bucket-owner-full-control，兩段以該trail的aws:SourceArn限制

**答案：D**

- **A：** 不正確。CloudTrail實際request由service principal送出，信任大量account root既不匹配最小service flow又擴大直接寫入。Cross-account trail仍應限制具體trail ARN與path。
- **B：** 不正確。Wildcard Principal與s3:*允許任意讀寫刪除，bucket名稱不是authorization condition。只有真正public resource才可能使用Principal:*，中央audit log不屬此類。
- **C：** 不正確。AWS managed policy不能替resource owner表達S3 bucket信任；CloudTrail delivery仍需bucket policy允許必要actions。Service principal也不應取得帳號級AdministratorAccess。
- **D：** 正確。CloudTrail官方範例分開ACL check與object delivery，Principal為cloudtrail.amazonaws.com，Resource精確到log prefix，並使用aws:SourceArn與ACL condition防止其他來源濫用。

**事實查證：** [Amazon S3 bucket policy for CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html)、[AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)

### 練習題 6｜SAP｜Organization-only resource sharing

中央 SQS queue 要接受 organization 內所有目前與未來 accounts 的 producers。最佳 resource-policy pattern 是什麼？

A. 將 queue 公開
B. 每次新增帳號手動改清單，且 Principal:*
C. 只開 consolidated billing
D. 以支援的 queue policy允許必要 SendMessage，搭配 aws:PrincipalOrgID 與其他必要條件；organization membership 本身不是 Allow

**答案：D**

- **A：** 不正確。Public queue 超出需求。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **B：** 不正確。可行但不可擴展；Principal:* 若無有效組織條件更危險。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **C：** 不正確。Billing 不參與 resource authorization。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **D：** 正確。Org ID condition 縮小 principals 集合，Action/Resource 仍須精確授權。

**事實查證：** [AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)、[Identity-based policies and resource-based policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html)

### 練習題 7｜SAA｜Safe iam:PassRole delegation

CI role 可部署 ECS services，但只能傳遞 ApprovedTaskRole 與 ApprovedExecutionRole。應如何授權？

A. 授予 iam:*
B. 在 CI role 將 iam:PassRole Resource 限定核准 role ARNs，並以 iam:PassedToService 限定 ECS tasks service
C. 只在 target roles 加 iam:PassRole
D. 將 CI role 寫入 task role trust，取代 ecs-tasks.amazonaws.com

**答案：B**

- **A：** 不正確。會容許建立/修改/傳遞高權限 roles。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **B：** 正確。Caller、role resource 與 target service 三者都被限縮，並保留 task role/ execution role 的不同責任。
- **C：** 不正確。PassRole 是 caller 執行部署 API 時的 permission。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **D：** 不正確。Task/execution roles 應信任 ECS task service；CI 通常不需 assume 它們。

**事實查證：** [Grant a user permissions to pass a role to an AWS service](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html)、[AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)

### 練習題 8｜SAP｜ABAC tag-governance boundary

某服務支援resource tags。Policy以aws:PrincipalTag/team等於resource tag授權；哪個治理缺口最可能讓使用者跨team存取？

A. Resource另有不參與policy的cost-center tag
B. Trust policy允許使用者任意傳入team session tag，且建立或標記resource時未限制aws:RequestTag/team、aws:TagKeys與TagResource actions
C. CloudTrail記錄了TagResource事件並送到中央log account
D. Policy存放在customer-managed policy而非inline policy

**答案：B**

- **A：** 不正確。額外cost-center tag只有在policy引用它時才改變authorization。若要求team與cost-center雙重匹配，才需把兩者都納入conditions與tag governance。
- **B：** 正確。ABAC的信任根是誰能設定attribute；若caller可自行使用sts:TagSession或修改resource team tag，就能選擇想冒充的team。必須在role trust與tagging APIs同時限制值與TagKeys。
- **C：** 不正確。CloudTrail提供偵測與追查，但不能在TagResource或AssumeRole request執行前阻止越權。仍需preventive IAM/SCP conditions保護tag mutation。
- **D：** 不正確。Inline或customer-managed只是policy管理方式，不決定PrincipalTag與ResourceTag是否可信；真正邊界在tag setter、session trust與service action支援。

**事實查證：** [Attribute-based access control with tags](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction_attribute-based-access-control.html)、[Pass session tags in AWS STS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html)、[AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)

### 練習題 9｜SAA｜Resource policy versus identity policy

中央 S3 bucket 供多帳號 roles 使用；其中一個 AppRole 也要操作 DynamoDB 與 SQS。哪兩項判斷正確？（選兩項）

A. Identity policy 可單方面授權別帳號的 private bucket
B. Bucket policy適合表達 owner-side/cross-account rules；AppRole identity policy適合表達該 identity 跨服務 permissions
C. Cross-account 場景常需來源 identity Allow 與目的 resource/trust Allow 同時成立
D. Resource policy 可附到 IAM group
E. 所有 AWS services 都支援相同 resource policy

**答案：B、C**

- **A：** 不正確。來源 account 不能替目的 owner 表示同意。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **B：** 正確。兩種 policy 的 attachment point 反映誰管理授權。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **C：** 正確。兩個 account boundaries 各自授權，任一 Deny 仍會阻止。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **D：** 不正確。Resource policy 附在 resource，不附 group。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。
- **E：** 不正確。支援與 policy elements 依服務而異。 Delegation必須限制caller、可建立或傳遞的resource及條件；事後logging不能替代題幹要求的preventive boundary。

**事實查證：** [Identity-based policies and resource-based policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_identity-vs-resource.html)、[Cross-account policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic-cross-account.html)

### 練習題 10｜SAP｜GuardDuty and Security Hub CSPM organization administration

Security Operations要管理organization的GuardDuty與Security Hub CSPM，但不應成為所有accounts的general administrator。哪兩項正確？（選兩項）

A. Delegated administrator是服務範圍的管理能力；仍需逐服務管理Region、auto-enable、standards/protection plans與response roles，不等於任意workload admin
B. 只在SOC roles附permissions boundary，即可自動啟用兩個服務的member coverage
C. 分別為GuardDuty與Security Hub CSPM註冊支援的delegated administrator，並按服務與Region配置organization enrollment或central configuration
D. 授予SOC每個member account的AdministratorAccess，因為delegated administrator本身不提供任何服務管理能力
E. 把所有workloads搬進Organizations management account，讓SOC直接使用root

**答案：A、C**

- **A：** 正確。服務管理權限有明確scope；GuardDuty protection plans與CSPM standards/controls仍要分開設定、監控coverage並把finding交給有owner的response workflow。
- **B：** 不正確。Permissions boundary只限制IAM entity最大權限，不會呼叫Organizations或安全服務API完成註冊、enrollment與central configuration。
- **C：** 正確。GuardDuty與Security Hub CSPM的delegated-admin、Region及organization configuration各自獨立，不能以一個泛稱Security Hub設定假設全部安全服務自動涵蓋。
- **D：** 不正確。每帳號AdministratorAccess超出findings與service configuration需求，也會繞過集中operating model。Delegated admin加上service-specific least privilege才是目的。
- **E：** 不正確。Management account不受SCP限制且具有organization最高權限，不應承載一般workload或SOC日常操作。只有極少數management-only APIs才在該帳號執行。

**事實查證：** [GuardDuty organization auto-enable preferences](https://docs.aws.amazon.com/guardduty/latest/ug/set-guardduty-auto-enable-preferences.html)、[Integrating Security Hub CSPM with AWS Organizations](https://docs.aws.amazon.com/securityhub/latest/userguide/designate-orgs-admin-account.html)、[Introduction to AWS Security Hub CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)、[AWS Organizations terminology and concepts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「用permissions boundary限制可委派權限；resource policy授權資源；dele…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「平台團隊需要讓應用團隊自行建立role，同時確保不能超過安全上限。」，所以「用permissions boundary限制可委派權限；resource policy授權資源；delegated admin把服務管理移出management account。」能直接滿足它；若constraint改成「Tag/attribute-based access可減少policy數量，但標籤治理本身必須可信。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「用permissions boundary限制可委派權限；resource policy授權資源；delegated admin把服務管理移出management account。」。替代方案「Tag/attribute-based access可減少policy數量，但標籤治理本身必須可信。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「允許iam:*後期待開發者自律，或把resource policy Principal寫成無條件星號。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「平台團隊需要讓應用團隊自行建立role，同時確保不能超過安全上限。」，排除會導致「允許iam:*後期待開發者自律，或把resource policy Principal寫成無條件星號。」的選項，再選「用permissions boundary限制可委派權限；resource policy授權資源；delegated admin把服務管理移出management account。」。本章對應的代表task包括：SAA-1.1 Design secure access to AWS resources；SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「用permissions boundary限制可委派權限；resource policy授權資源；delegated admin把服務管理移出management account。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「delegate capability inside non-bypassable boundaries」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 27 章　KMS、Envelope Encryption 與 Key Policy

大量資料需要可擴展加密、集中key control、rotation與audit。

## 跟著一次授權決定走：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：S3、EBS與應用欄位需加密，安全團隊要求集中撤權與CloudTrail稽核。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：大量資料需要可擴展加密、集中key control、rotation與audit。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：登入像出示員工證，policy像每扇門旁的門禁規則；有證件不代表所有房間都能進。 但請同時記住它的邊界：AWS授權由多層policy共同決定，還要考慮explicit Deny、resource policy與organization guardrail。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS KMS，對照角色是AWS CloudHSM。我們選擇「KMS保護data key；資料由data key本地加密，key policy與grants控制誰能使用CMK。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：S3、EBS與應用欄位需加密，安全團隊要求集中撤權與CloudTrail稽核。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[AWS KMS] ── Allow / Deny ──> protected resource
          │ 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · AWS CloudHSM：提供customer-managed、single-tenant HSM cluster與標準crypto…
  · Envelope encryption：使用data key加密大量資料，再以KMS key加密data key，避免每個資料區塊都直接呼叫KMS。

失敗時先找：只給IAM allow卻未被key policy允許，或跨Region複製資料卻未規劃keys。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問AWS KMS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS KMS和AWS CloudHSM並不是兩個任意的產品名稱。前者適合本章，是因為「KMS保護data key；資料由data key本地加密，key policy與grants控制誰能使用CMK。」直接回應了眼前的問題；後者描述的「CloudHSM提供更直接的HSM控制，但營運責任與整合成本較高。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只給IAM allow卻未被key policy允許，或跨Region複製資料卻未規劃keys。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「separate data encryption from key authorization」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 |
| AWS CloudHSM | 提供customer-managed、single-tenant HSM cluster與標準crypto介面。 | HSM跨AZ組cluster，客戶管理users、keys、backup與application integration；AWS管理硬體。 |
| Envelope encryption | 使用data key加密大量資料，再以KMS key加密data key，避免每個資料區塊都直接呼叫KMS。 | 應用呼叫GenerateDataKey取得plaintext與encrypted data key；plaintext只在memory中使用後清除，encrypted data key與ciphertext一起保存。 |

## 把全圖套進一個具體案例

**場景：** S3、EBS與應用欄位需加密，安全團隊要求集中撤權與CloudTrail稽核。

1. 故事的起點：S3、EBS與應用欄位需加密，安全團隊要求集中撤權與CloudTrail稽核。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS KMS負責「管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS CloudHSM、Envelope encryption各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只給IAM allow卻未被key policy允許，或跨Region複製資料卻未規劃keys。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS KMS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：大量資料需要可擴展加密、集中key control、rotation與audit。
- **具體例子／邊界：** 在「S3、EBS與應用欄位需加密，安全團隊要求集中撤權與CloudTrail稽核。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS CloudHSM

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：CloudHSM提供更直接的HSM控制，但營運責任與整合成本較高。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只給IAM allow卻未被key policy允許，或跨Region複製資料卻未規劃keys。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：separate data encryption from key authorization。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### envelope encryption

先用data key加密大量資料，再用KMS key加密較小的data key；避免每個資料block都直接呼叫KMS。

### Multi-Region

把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。

### data key

實際加密application資料的對稱key；通常只在記憶體中短暫使用，儲存的是被KMS key加密後的副本。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

## 回到 AWS：Components、功用與責任邊界

### AWS KMS

- **功用：** 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
- **底層機制：** Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。
- **關鍵設定：** key policy、grants、aliases、rotation、multi-Region keys、encryption context與key spec/usage。
- **選擇時機：** S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。
- **替換時機：** 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。

### AWS CloudHSM

- **功用：** 提供customer-managed、single-tenant HSM cluster與標準crypto介面。
- **底層機制：** HSM跨AZ組cluster，客戶管理users、keys、backup與application integration；AWS管理硬體。
- **關鍵設定：** cluster/subnets、HSM users、key replication、client configuration、backup與quorum。
- **選擇時機：** 法規要求專用HSM、PKCS#11/JCE/CNG或自管key material。
- **替換時機：** 多數AWS服務原生加密與較低營運負擔選KMS。

### Envelope encryption

- **功用：** 使用data key加密大量資料，再以KMS key加密data key，避免每個資料區塊都直接呼叫KMS。
- **底層機制：** 應用呼叫GenerateDataKey取得plaintext與encrypted data key；plaintext只在memory中使用後清除，encrypted data key與ciphertext一起保存。
- **關鍵設定：** KMS key、encryption context、data-key algorithm、key policy、grants、rotation與ciphertext metadata。
- **選擇時機：** 大型object、database field或client-side encryption需要兼顧效能、key audit與集中撤銷時。
- **替換時機：** 小型service-integrated encryption可直接使用服務SSE；envelope encryption不會取代IAM、TLS或資料分類。

## 考前與實作時再查：設定操作手冊

### AWS KMS：逐項設定說明

#### `key policy`

- **控制什麼：** `key policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `grants`

- **控制什麼：** `grants`指定誰能使用、管理或接受AWS KMS的resource/contract，是delegated ownership與authorization的一部分。
- **何時需要：** 跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。
- **怎麼設定／驗證：** 使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。
- **常見錯法：** 信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。

#### `aliases`

- **控制什麼：** `aliases`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `rotation`

- **控制什麼：** `rotation`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `multi-Region keys`

- **控制什麼：** `multi-Region keys`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS KMS前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `encryption context`

- **控制什麼：** `encryption context`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS KMS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `key spec/usage`

- **控制什麼：** `key spec/usage`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。
- **何時需要：** TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。
- **怎麼設定／驗證：** 選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。
- **常見錯法：** 錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。

### AWS CloudHSM：逐項設定說明

#### `cluster/subnets`

- **控制什麼：** `cluster/subnets`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「法規要求專用HSM、PKCS#11/JCE/CNG或自管key material。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudHSM的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `HSM users`

- **控制什麼：** `HSM users`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。
- **何時需要：** TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。
- **怎麼設定／驗證：** 選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。
- **常見錯法：** 錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。

#### `key replication`

- **控制什麼：** `key replication`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「法規要求專用HSM、PKCS#11/JCE/CNG或自管key material。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudHSM依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `client configuration`

- **控制什麼：** `client configuration`是一組可版本化的engine/runtime參數，會改變AWS CloudHSM的實際process行為。
- **何時需要：** 當需求符合「法規要求專用HSM、PKCS#11/JCE/CNG或自管key material。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `backup`

- **控制什麼：** `backup`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「法規要求專用HSM、PKCS#11/JCE/CNG或自管key material。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS CloudHSM依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `quorum`

- **控制什麼：** `quorum`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。
- **何時需要：** TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。
- **怎麼設定／驗證：** 選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。
- **常見錯法：** 錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。

### Envelope encryption：逐項設定說明

#### `KMS key`

- **控制什麼：** `KMS key`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「大型object、database field或client-side encryption需要兼顧效能、key audit與集中撤銷時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Envelope encryption指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `encryption context`

- **控制什麼：** `encryption context`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「大型object、database field或client-side encryption需要兼顧效能、key audit與集中撤銷時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Envelope encryption指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `data-key algorithm`

- **控制什麼：** `data-key algorithm`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。
- **何時需要：** TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。
- **怎麼設定／驗證：** 選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。
- **常見錯法：** 錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。

#### `key policy`

- **控制什麼：** `key policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「大型object、database field或client-side encryption需要兼顧效能、key audit與集中撤銷時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Envelope encryption明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `grants`

- **控制什麼：** `grants`指定誰能使用、管理或接受Envelope encryption的resource/contract，是delegated ownership與authorization的一部分。
- **何時需要：** 跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。
- **怎麼設定／驗證：** 使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。
- **常見錯法：** 信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。

#### `rotation`

- **控制什麼：** `rotation`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「大型object、database field或client-side encryption需要兼顧效能、key audit與集中撤銷時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Envelope encryption指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `ciphertext metadata`

- **控制什麼：** 保存解密所需但不必保密的資訊，包括加密後data key、演算法版本、IV／nonce、authentication tag與必要的encryption-context識別。
- **何時需要：** 應用自行做client-side或field-level envelope encryption，未來需要key rotation、格式升級與跨版本解密時。
- **怎麼設定／驗證：** 定義版本化envelope格式，把encrypted data key與ciphertext一起原子保存；解密時重建完全相同的encryption context並驗證authentication tag。
- **常見錯法：** 遺失metadata會讓仍有KMS權限的資料也無法解密；重用nonce、未驗tag或把plaintext data key寫入metadata都會破壞安全性。

## 可以直接對照 AWS 的設定範例

### KMS key policy：允許application role使用key

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnableAccountAdministration",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111122223333:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "AllowApplicationDataKeyUsage",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111122223333:role/OrdersApp"},
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {"kms:ViaService": "s3.us-east-1.amazonaws.com"}
      }
    }
  ]
}
```

1. KMS key policy是key的resource policy；IAM Allow不一定足夠，key policy也必須建立授權路徑。
2. kms:ViaService把key usage限制在透過指定Region S3，減少role直接任意Decrypt。
3. Resource在KMS key policy通常是*，代表這一把key；不要誤解為帳號所有keys。

## 讀到這裡，請用自己的話說一次

1. AWS KMS的責任：管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。
2. 底層機制：Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。
3. 第一個要看的設定：key policy、grants、aliases、rotation、multi-Region keys、encryption context與key spec/usage。
4. 選擇邏輯：KMS保護data key；資料由data key本地加密，key policy與grants控制誰能使用CMK。
5. 不要混淆：AWS CloudHSM的責任是「提供customer-managed、single-tenant HSM cluster與標準crypto介面。」；它不會自動取代AWS KMS。
6. 替換訊號：需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。
7. 最常見錯法：只給IAM allow卻未被key policy允許，或跨Region複製資料卻未規劃keys。
8. 可移植原則：separate data encryption from key authorization。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS KMS | 管理加密keys與授權，提供encrypt/decrypt/data-key API與audit。 | Envelope encryption用KMS key保護data key；大量資料由data key在service/client端加密。 | S3/EBS/RDS等managed encryption、集中撤權、CloudTrail key-use audit。 | 需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。 |
| AWS CloudHSM | 提供customer-managed、single-tenant HSM cluster與標準crypto介面。 | HSM跨AZ組cluster，客戶管理users、keys、backup與application integration；AWS管理硬體。 | 法規要求專用HSM、PKCS#11/JCE/CNG或自管key material。 | 多數AWS服務原生加密與較低營運負擔選KMS。 |
| Envelope encryption | 使用data key加密大量資料，再以KMS key加密data key，避免每個資料區塊都直接呼叫KMS。 | 應用呼叫GenerateDataKey取得plaintext與encrypted data key；plaintext只在memory中使用後清除，encrypted data key與ciphertext一起保存。 | 大型object、database field或client-side encryption需要兼顧效能、key audit與集中撤銷時。 | 小型service-integrated encryption可直接使用服務SSE；envelope encryption不會取代IAM、TLS或資料分類。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | CloudHSM提供更直接的HSM控制，但營運責任與整合成本較高。 | 只有當題目條件明確改變時才可能合理。 | 只給IAM allow卻未被key policy允許，或跨Region複製資料卻未規劃keys。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「CloudHSM提供更直接的HSM控制，但營運責任與整合成本較高。」之間做選擇。
- 認得常考設定：key policy、grants、aliases、rotation、multi-Region keys、encryption context與key spec/usage。
- 對應官方tasks：SAA-1.3 Determine appropriate data security controls。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要單租戶HSM管理、PKCS#11或更直接key control時用CloudHSM。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜Envelope-encryption data path

應用要 client-side encrypt 5 GB files。哪個 KMS 流程最合適？

A. 呼叫 GenerateDataKey；以 plaintext data key 本地加密，立即清除 plaintext key，儲存 ciphertext 與 encrypted data key；解密時由 KMS 解開 data key
B. 把 plaintext data key 放在 object metadata
C. 用 alias 字串本身作 AES key
D. 把整個 5 GB file 傳給 KMS Encrypt

**答案：A**

- **A：** 正確。Envelope encryption 讓 KMS 保護小型 data key，大量資料由本地對稱加密處理。
- **B：** 不正確。與 ciphertext 同存的應是 encrypted data key，plaintext key 應只短暫存在記憶體。
- **C：** 不正確。Alias 是 key identifier，不是 key material。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **D：** 不正確。KMS cryptographic APIs 不用來傳輸/加密大型 payload。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。

**事實查證：** [Envelope encryption](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#enveloping)

### 練習題 2｜SAA｜Key policy enables IAM delegation

Role identity policy Allow kms:Decrypt，但 customer-managed KMS key policy 未直接授權該 role，也未建立可由 IAM policies 授權的 account statement。結果為何？

A. Decrypt 被拒；key policy 是 KMS 授權根，IAM Allow 只有在 key policy允許相應路徑時才生效
B. SCP Allow KMS 即可
C. S3 permission會自動補足
D. Alias policy會自動授權

**答案：A**

- **A：** 正確。每把 KMS key 都有 key policy；未建立 direct/grant/IAM-enablement path 時，identity Allow 無效。
- **B：** 不正確。SCP 只限制最大權限，不會建立任何 KMS key 使用授權。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **C：** 不正確。資料服務與 KMS authorization 分離。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **D：** 不正確。Alias 沒有獨立 access policy。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。

**事實查證：** [Key policies in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)、[IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

### 練習題 3｜SAP｜Cross-account KMS access

Account A AppRole 要使用 Account B 的 KMS key 解密。哪個配置完整？

A. 只在 A role 加 kms:Decrypt
B. B key policy允許 A principal/account，A identity policy允許對 B key ARN 的 kms:Decrypt，且滿足 context/guardrails
C. 同 Organization 即自動允許
D. 只在 B key policy 加 A account

**答案：B**

- **A：** 不正確。A 不能單方面授權使用 B key。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **B：** 正確。Cross-account KMS 需要 key-owner 與 caller-account 兩側授權，並使用正確 key ARN。
- **C：** 不正確。Organization membership 不是 KMS grant。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **D：** 不正確。B 表示信任後，A principal 還需 identity permission。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。

**事實查證：** [Key policies in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)、[Cross-account policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic-cross-account.html)

### 練習題 4｜SAP｜KMS grants for service integrations

某AWS服務在建立加密資源時，需要被授予對單一KMS key的有限operations，且授權生命週期應與該資源整合而不是長期擴大key policy。哪個機制最適合？

A. 在key policy永久允許該服務帳號中的所有roles執行kms:*
B. 只在呼叫者identity policy增加kms:CreateGrant，不限制grantee、operations或constraints
C. 建立限制grantee、operations與encryption context等constraints的KMS grant；建立者、grantee/retiring principal與key owner依文件分別retire或revoke，必要時使用grant token處理最終一致性
D. 把customer-managed key改成AWS owned key，並假設權限需求完全相同

**答案：C**

- **A：** 不正確。永久kms:*把暫時resource integration擴大成長期帳號級授權，也無法隨resource刪除自動收斂。只有服務確實需要廣泛且持久管理key時才考慮更新key policy。
- **B：** 不正確。CreateGrant本身是敏感權限；未限制grantee、operations與constraints可被用來建立持久擴權。Caller permission與實際grant內容都必須最小化。
- **C：** 正確。Grant能對單一key建立可撤回的細粒度授權；retire通常由grantee或retiring principal依grant條件執行，revoke由key owner等有kms:RevokeGrant權限者執行，grant token可供新grant立即使用。
- **D：** 不正確。AWS owned key會降低客戶對policy、grant與cross-account的控制，不能只為省略grant而替換。若題幹允許服務預設加密且不需自訂控制，才可能合適。

**事實查證：** [Grants in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/grants.html)

### 練習題 5｜SAP｜Encryption context integrity

同一 KMS key 加密多租戶 records；tenant A ciphertext 不可在 tenant B context 解密。最佳控制是什麼？

A. 只在資料庫欄位保存tenant_id，KMS request不傳入任何context
B. 為每筆record建立不同KMS alias，但所有alias仍指向同一key且policy不檢查context
C. 把tenant名稱雜湊後當作自製AES key，繞過KMS授權
D. 加密時提供tenant綁定的encryption context，解密要求相同context，並在key policy或grant condition限制允許的tenant值

**答案：D**

- **A：** 不正確。Application欄位可被錯誤查詢或搬移，若未送入KMS就不參與ciphertext authentication。它可作業務資料，但不能取代encryption context。
- **B：** 不正確。Alias只協助選擇KMS key，不會成為cryptographic integrity input；同一key與無context policy仍無法阻止跨tenant重放。
- **C：** 不正確。Tenant名稱不是高熵secret，自製key derivation也失去KMS policy、audit與rotation控制。若需要per-tenant isolation，應用正式data-key與context設計。
- **D：** 正確。Encryption context是authenticated additional data；ciphertext只能在相同context下成功驗證。Policy或grant再限制context值，能把cryptographic use與tenant authorization連在一起。

**事實查證：** [Envelope encryption](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#enveloping)、[Key policies in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)

### 練習題 6｜SAP｜Multi-Region KMS key semantics

App data 已複製到第二 Region，並建立 related multi-Region KMS replica。哪項敘述正確？

A. Primary policy changes 全部自動同步
B. 普通 single-Region key 可在任意 Region local decrypt
C. 建立 replica key 會自動複製 S3/RDS data
D. Related keys 共享 key ID/material，但各 Region 的 policy、grant、alias、enabled state需獨立管理；data replication與failover另行設計

**答案：D**

- **A：** 不正確。Policies、grants、aliases等不是共享 properties。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **B：** 不正確。Single-Region key 的 KMS API 使用受 Region 限制。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **C：** 不正確。KMS replication只處理 related key properties，不搬應用資料。
- **D：** 正確。Cryptographic interoperability 不等於 global service；regional authorization與data plane仍獨立。

**事實查證：** [Multi-Region keys in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html)

### 練習題 7｜SAA｜KMS key ownership categories

一個 workload 必須自訂 key policy、cross-account grants、rotation與 deletion；另一個只需服務預設加密且優先低操作。如何選？

A. 所有 encrypted services 自動建立 customer-managed key
B. 兩者都一定用 CloudHSM
C. 前者用 customer-managed key；後者可接受服務支援的 AWS owned/managed key，並理解其控制與稽核限制
D. AWS owned key 可由客戶編輯 policy

**答案：C**

- **A：** 不正確。服務預設可能使用 AWS owned/managed key。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **B：** 不正確。CloudHSM 增加 cluster、user 與 integration operations。
- **C：** 正確。Key ownership 應依 control/audit/cross-account 要求選擇，不是加密強度口號。
- **D：** 不正確。AWS owned keys 不由客戶管理 policy/lifecycle。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。

**事實查證：** [AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)

### 練習題 8｜SAA｜Rotation versus data re-encryption

Customer-managed KMS key 啟用 automatic rotation。稽核員問舊 ciphertext 是否會被自動重寫。正確回答為何？

A. Rotation完成後，任何以舊key material加密的ciphertext都立即失效
B. Rotation會保留既有key identifier與舊material供解密；只有之後的加密使用新material，既有資料不會自動重寫
C. 為了完成rotation，應先disable舊key版本直到所有服務改用alias
D. Automatic rotation會在背景掃描並重寫所有S3、EBS與database ciphertext

**答案：B**

- **A：** 不正確。KMS保留舊material以維持既有ciphertext可解密；讓它立即失效會破壞backup與歷史資料。只有disable或delete整把key才會中斷使用。
- **B：** 正確。Rotation改變未來cryptographic operations選用的key material，不改ARN/key ID，也不自動re-encrypt。若合規要求資料換密，必須另行排程與驗證migration。
- **C：** 不正確。Automatic rotation由KMS管理key material版本，不需要客戶disable舊material；任意disable整把key反而會讓現有workload與recovery points失敗。
- **D：** 不正確。KMS不知道所有application ciphertext存放位置，也不執行跨服務資料搬移。只有另建migration job逐筆decrypt/re-encrypt才會重寫資料。

**事實查證：** [Rotating AWS KMS keys](https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html)

### 練習題 9｜SAP｜Safe KMS key deletion

團隊認為一把 key 未使用，準備 schedule deletion。哪兩項最能降低永久資料遺失風險？（選兩項）

A. AWS 可在 deletion 完成後無條件恢復 customer key
B. 相信 snapshots 內含可用 plaintext key
C. 刪除 alias 即等同安全刪 key
D. 先 disable 並監控實際依賴、CloudTrail/服務 inventory，再使用等待期與 cancellation path
E. 盤點 backups、replicas、logs與跨帳號 consumers，驗證替代 key/re-encryption 後才刪除

**答案：D、E**

- **A：** 不正確。完成 deletion 後 key material不可恢復。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **B：** 不正確。Encrypted backups仍依賴 KMS key，不會保存可用 plaintext key。
- **C：** 不正確。Alias 只是名稱，刪除不刪 key。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **D：** 正確。Disable-before-delete 提供可逆觀察窗，等待期保留取消機會。 KMS授權與cryptographic lifecycle需以key policy、grant、context及key state逐層判斷，不能由相鄰服務自動補足。
- **E：** 正確。低頻 DR/retention consumers 常不在近期 usage 中，需主動盤點。

**事實查證：** [Deleting AWS KMS keys](https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html)、[Logging AWS KMS API calls with AWS CloudTrail](https://docs.aws.amazon.com/kms/latest/developerguide/logging-using-cloudtrail.html)

### 練習題 10｜SAP｜Direct CloudHSM use versus KMS custom key store

團隊比較三種模式：一般AWS KMS key、應用直接使用CloudHSM client/PKCS#11、以及以CloudHSM cluster支援KMS custom key store。哪兩項描述正確？（選兩項）

A. 直接CloudHSM模式提供PKCS#11/JCE等介面與較直接的HSM user/key控制，但團隊負責cluster availability、client networking、users、backup與應用加密整合
B. KMS custom key store仍透過KMS API、IAM與key policy整合AWS服務，但key material由客戶CloudHSM cluster支援，團隊承擔額外HSM可用性與操作責任
C. 應用直接使用CloudHSM後，S3與EBS會自動把該HSM key視為所有server-side encryption API的原生KMS key
D. KMS custom key store與一般KMS key在availability、latency、quota與key-material責任上完全相同
E. KMS custom key store會讓應用繞過KMS API，改成直接開啟PKCS#11 session

**答案：A、B**

- **A：** 正確。直接使用CloudHSM把cryptographic API與HSM users交給應用團隊，也把多AZ cluster、client連線、備份與故障處理納入其責任。
- **B：** 正確。它把KMS原生service integration與客戶控制的CloudHSM key material結合，但不是「零操作」方案；cluster不可用會影響cryptographic requests。
- **C：** 不正確。直接CloudHSM key不是KMS key ARN，AWS服務不會自動把它當成原生SSE-KMS整合。應用需自行做client-side encryption，或另選KMS custom key store模式。
- **D：** 不正確。Custom key store依賴客戶CloudHSM cluster，因此可用性、延遲、quota與操作故障模式都比一般KMS key多一層。只有一般KMS服務管理模式才不需客戶營運HSM cluster。
- **E：** 不正確。Custom key store的目的正是保留KMS control/API surface；caller仍呼叫KMS並接受IAM、key policy與grant評估，不直接取得HSM session。

**事實查證：** [AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)、[What is AWS CloudHSM?](https://docs.aws.amazon.com/cloudhsm/latest/userguide/introduction.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「KMS保護data key；資料由data key本地加密，key policy與grants控制誰能使用…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「大量資料需要可擴展加密、集中key control、rotation與audit。」，所以「KMS保護data key；資料由data key本地加密，key policy與grants控制誰能使用CMK。」能直接滿足它；若constraint改成「CloudHSM提供更直接的HSM控制，但營運責任與整合成本較高。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「KMS保護data key；資料由data key本地加密，key policy與grants控制誰能使用CMK。」。替代方案「CloudHSM提供更直接的HSM控制，但營運責任與整合成本較高。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只給IAM allow卻未被key policy允許，或跨Region複製資料卻未規劃keys。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「大量資料需要可擴展加密、集中key control、rotation與audit。」，排除會導致「只給IAM allow卻未被key policy允許，或跨Region複製資料卻未規劃keys。」的選項，再選「KMS保護data key；資料由data key本地加密，key policy與grants控制誰能使用CMK。」。本章對應的代表task包括：SAA-1.3 Determine appropriate data security controls；SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「KMS保護data key；資料由data key本地加密，key policy與grants控制誰能使用CMK。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「separate data encryption from key authorization」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 28 章　Secrets Manager、Parameter Store 與 ACM

密碼、API key與certificate都有生命週期，不能放在AMI、環境檔或repo。

## 跟著一次授權決定走：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：RDS密碼每月rotate，Lambda需無重啟切換，public ALB需自動續期TLS。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：密碼、API key與certificate都有生命週期，不能放在AMI、環境檔或repo。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，把身份系統想成辦公大樓：登入證明你是誰，門禁規則才決定你能進哪一間房。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看AWS Secrets Manager如何接手工作，再看AWS Systems Manager Parameter Store何時更合適，最後用設定與考題驗證「需自動rotation的secret用Secrets Manager；一般設定/secure string可用Parameter Store；certificate用ACM。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：RDS密碼每月rotate，Lambda需無重啟切換，public ALB需自動續期TLS。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[AWS Secrets Manager] ── Allow / Deny ──> protected resource
          │ 安全保存secret並支援版本、fine-grained access與自動rotation。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · AWS Systems Manager Parameter Store：階層化保存configuration與SecureString，整合IAM/KMS。
  · AWS Certificate Manager：申請、保存並自動更新可供整合服務使用的TLS certificates。

失敗時先找：每次request同步讀secret造成延遲與throttling，或rotation後connection pool仍用舊值。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問AWS Secrets Manager有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Secrets Manager和AWS Systems Manager Parameter Store並不是兩個任意的產品名稱。前者適合本章，是因為「需自動rotation的secret用Secrets Manager；一般設定/secure string可用Parameter Store；certificate用ACM。」直接回應了眼前的問題；後者描述的「Runtime retrieval降低靜態洩漏但增加權限、cache、availability與quota考量。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：每次request同步讀secret造成延遲與throttling，或rotation後connection pool仍用舊值。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「credentials are dynamic dependencies, not configuration constants」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Secrets Manager | 安全保存secret並支援版本、fine-grained access與自動rotation。 | Secret有AWSCURRENT/AWSPREVIOUS等version stages；rotation workflow建立、測試並切換新值。 |
| AWS Systems Manager Parameter Store | 階層化保存configuration與SecureString，整合IAM/KMS。 | Application按name/version讀取parameter；SecureString透過KMS解密，沒有Secrets Manager完整rotation workflow。 |
| AWS Certificate Manager | 申請、保存並自動更新可供整合服務使用的TLS certificates。 | DNS/email validation證明domain ownership；ACM-managed certificate在支援服務上自動續期。 |

## 把全圖套進一個具體案例

**場景：** RDS密碼每月rotate，Lambda需無重啟切換，public ALB需自動續期TLS。

1. 故事的起點：RDS密碼每月rotate，Lambda需無重啟切換，public ALB需自動續期TLS。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Secrets Manager負責「安全保存secret並支援版本、fine-grained access與自動rotation。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Secret有AWSCURRENT/AWSPREVIOUS等version stages；rotation workflow建立、測試並切換新值。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Systems Manager Parameter Store、AWS Certificate Manager各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「每次request同步讀secret造成延遲與throttling，或rotation後connection pool仍用舊值。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「一般非敏感設定或較便宜SecureString可用Parameter Store；certificate生命週期用ACM。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Secrets Manager

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：密碼、API key與certificate都有生命週期，不能放在AMI、環境檔或repo。
- **具體例子／邊界：** 在「RDS密碼每月rotate，Lambda需無重啟切換，public ALB需自動續期TLS。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Systems Manager Parameter Store

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Runtime retrieval降低靜態洩漏但增加權限、cache、availability與quota考量。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：每次request同步讀secret造成延遲與throttling，或rotation後connection pool仍用舊值。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：credentials are dynamic dependencies, not configuration constants。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### availability

需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。

### throttling

服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS Secrets Manager

- **功用：** 安全保存secret並支援版本、fine-grained access與自動rotation。
- **底層機制：** Secret有AWSCURRENT/AWSPREVIOUS等version stages；rotation workflow建立、測試並切換新值。
- **關鍵設定：** KMS key、resource policy、rotation Lambda/managed rotation、schedule、replica Regions與cache。
- **選擇時機：** database password、API key或需自動rotation與cross-account policy的secret。
- **替換時機：** 一般非敏感設定或較便宜SecureString可用Parameter Store；certificate生命週期用ACM。

### AWS Systems Manager Parameter Store

- **功用：** 階層化保存configuration與SecureString，整合IAM/KMS。
- **底層機制：** Application按name/version讀取parameter；SecureString透過KMS解密，沒有Secrets Manager完整rotation workflow。
- **關鍵設定：** String/StringList/SecureString、hierarchy、standard/advanced tier、policies、KMS key與version。
- **選擇時機：** feature/config values、較簡單secret、與Systems Manager automation整合。
- **替換時機：** 需要managed rotation、secret replicas或database integration時用Secrets Manager。

### AWS Certificate Manager

- **功用：** 申請、保存並自動更新可供整合服務使用的TLS certificates。
- **底層機制：** DNS/email validation證明domain ownership；ACM-managed certificate在支援服務上自動續期。
- **關鍵設定：** domain/SAN、validation method、key algorithm、exportability、Region與ALB/CloudFront association。
- **選擇時機：** ALB、CloudFront、API Gateway等TLS termination。
- **替換時機：** 需要在EC2自行取private key、特殊CA或device identity時評估Private CA/自管certificate。

## 考前與實作時再查：設定操作手冊

### AWS Secrets Manager：逐項設定說明

#### `KMS key`

- **控制什麼：** `KMS key`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「database password、API key或需自動rotation與cross-account policy的secret。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Secrets Manager指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `resource policy`

- **控制什麼：** `resource policy`指定AWS Secrets Manager讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `rotation Lambda/managed rotation`

- **控制什麼：** `rotation Lambda/managed rotation`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「database password、API key或需自動rotation與cross-account policy的secret。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Secrets Manager指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `schedule`

- **控制什麼：** `schedule`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「database password、API key或需自動rotation與cross-account policy的secret。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Secrets Manager的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `replica Regions`

- **控制什麼：** `replica Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS Secrets Manager前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `cache`

- **控制什麼：** `cache`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。
- **何時需要：** 當需求符合「database password、API key或需自動rotation與cross-account policy的secret。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Secrets Manager依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。
- **常見錯法：** Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。

### AWS Systems Manager Parameter Store：逐項設定說明

#### `String/StringList/SecureString`

- **控制什麼：** `String/StringList/SecureString`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「feature/config values、較簡單secret、與Systems Manager automation整合。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Systems Manager Parameter Store指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `hierarchy`

- **控制什麼：** `hierarchy`建立父子namespace/pool與生命週期規則，讓AWS Systems Manager Parameter Store可以委派、繼承或依路徑管理資源。
- **何時需要：** 多團隊需要分層管理parameters或IP ranges，並避免名稱/CIDR碰撞時。
- **怎麼設定／驗證：** 先建立top-level owner與child boundaries，使用穩定path/CIDR allocation rules；對敏感values加IAM/KMS並監控過期/未使用項目。
- **常見錯法：** Hierarchy只是組織方式，不自動授權；child pool過度切割會浪費地址，parameter policy也不是完整secret rotation。

#### `standard/advanced tier`

- **控制什麼：** `standard/advanced tier`選擇AWS Systems Manager Parameter Store的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `policies`

- **控制什麼：** `policies`建立父子namespace/pool與生命週期規則，讓AWS Systems Manager Parameter Store可以委派、繼承或依路徑管理資源。
- **何時需要：** 多團隊需要分層管理parameters或IP ranges，並避免名稱/CIDR碰撞時。
- **怎麼設定／驗證：** 先建立top-level owner與child boundaries，使用穩定path/CIDR allocation rules；對敏感values加IAM/KMS並監控過期/未使用項目。
- **常見錯法：** Hierarchy只是組織方式，不自動授權；child pool過度切割會浪費地址，parameter policy也不是完整secret rotation。

#### `KMS key`

- **控制什麼：** `KMS key`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「feature/config values、較簡單secret、與Systems Manager automation整合。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Systems Manager Parameter Store指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `version`

- **控制什麼：** `version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「feature/config values、較簡單secret、與Systems Manager automation整合。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Systems Manager Parameter Store鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

### AWS Certificate Manager：逐項設定說明

#### `domain/SAN`

- **控制什麼：** `domain/SAN`控制名稱如何被解析或驗證；DNS只把名稱轉成目標資料，不會替代route、network policy或IAM。
- **何時需要：** 當需求符合「ALB、CloudFront、API Gateway等TLS termination。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Certificate Manager的DNS／domain設定中明確指定zone、name、resolver direction或validation方式，並用dig/nslookup從實際來源網路驗證答案。
- **常見錯法：** 只在console看到名稱存在，不代表所有VPC、Region與client都得到同一答案；還要檢查cache TTL、zone association與return path。

#### `validation method`

- **控制什麼：** `validation method`定義AWS Certificate Manager用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `key algorithm`

- **控制什麼：** `key algorithm`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。
- **何時需要：** TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。
- **怎麼設定／驗證：** 選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。
- **常見錯法：** 錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。

#### `exportability`

- **控制什麼：** `exportability`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「ALB、CloudFront、API Gateway等TLS termination。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Certificate Manager的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `Region`

- **控制什麼：** `Region`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS Certificate Manager前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `ALB/CloudFront association`

- **控制什麼：** `ALB/CloudFront association`控制AWS Certificate Manager的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

## 可以直接對照 AWS 的設定範例

### Secrets Manager secret 與 rotation（CloudFormation）

```yaml
Resources:
  DbSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      KmsKeyId: !Ref SecretsKey
      GenerateSecretString:
        SecretStringTemplate: '{"username":"app_user"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludePunctuation: true
      ReplicaRegions:
        - Region: us-west-2
  RotationSchedule:
    Type: AWS::SecretsManager::RotationSchedule
    Properties:
      SecretId: !Ref DbSecret
      HostedRotationLambda:
        RotationType: PostgreSQLSingleUser
        RotationLambdaName: rotate-orders-db
        VpcSecurityGroupIds: !Ref RotationSecurityGroups
        VpcSubnetIds: !Ref PrivateSubnets
      RotationRules:
        ScheduleExpression: rate(30 days)

```

1. Secret使用KMS加密並跨Region replica；讀取role仍需secretsmanager:GetSecretValue與kms:Decrypt。
2. Rotation Lambda必須能network連到database，並完成create/test/finish等rotation steps。
3. Application要cache secret且在auth failure後重新讀取，避免每request讀取與rotation後長期用舊connection。

## 讀到這裡，請用自己的話說一次

1. AWS Secrets Manager的責任：安全保存secret並支援版本、fine-grained access與自動rotation。
2. 底層機制：Secret有AWSCURRENT/AWSPREVIOUS等version stages；rotation workflow建立、測試並切換新值。
3. 第一個要看的設定：KMS key、resource policy、rotation Lambda/managed rotation、schedule、replica Regions與cache。
4. 選擇邏輯：需自動rotation的secret用Secrets Manager；一般設定/secure string可用Parameter Store；certificate用ACM。
5. 不要混淆：AWS Systems Manager Parameter Store的責任是「階層化保存configuration與SecureString，整合IAM/KMS。」；它不會自動取代AWS Secrets Manager。
6. 替換訊號：一般非敏感設定或較便宜SecureString可用Parameter Store；certificate生命週期用ACM。
7. 最常見錯法：每次request同步讀secret造成延遲與throttling，或rotation後connection pool仍用舊值。
8. 可移植原則：credentials are dynamic dependencies, not configuration constants。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Secrets Manager | 安全保存secret並支援版本、fine-grained access與自動rotation。 | Secret有AWSCURRENT/AWSPREVIOUS等version stages；rotation workflow建立、測試並切換新值。 | database password、API key或需自動rotation與cross-account policy的secret。 | 一般非敏感設定或較便宜SecureString可用Parameter Store；certificate生命週期用ACM。 |
| AWS Systems Manager Parameter Store | 階層化保存configuration與SecureString，整合IAM/KMS。 | Application按name/version讀取parameter；SecureString透過KMS解密，沒有Secrets Manager完整rotation workflow。 | feature/config values、較簡單secret、與Systems Manager automation整合。 | 需要managed rotation、secret replicas或database integration時用Secrets Manager。 |
| AWS Certificate Manager | 申請、保存並自動更新可供整合服務使用的TLS certificates。 | DNS/email validation證明domain ownership；ACM-managed certificate在支援服務上自動續期。 | ALB、CloudFront、API Gateway等TLS termination。 | 需要在EC2自行取private key、特殊CA或device identity時評估Private CA/自管certificate。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Runtime retrieval降低靜態洩漏但增加權限、cache、availability與quota考量。 | 只有當題目條件明確改變時才可能合理。 | 每次request同步讀secret造成延遲與throttling，或rotation後connection pool仍用舊值。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Runtime retrieval降低靜態洩漏但增加權限、cache、availability與quota考量。」之間做選擇。
- 認得常考設定：KMS key、resource policy、rotation Lambda/managed rotation、schedule、replica Regions與cache。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：一般非敏感設定或較便宜SecureString可用Parameter Store；certificate生命週期用ACM。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜Secrets Manager versus Parameter Store

RDS password 要每 30 天自動 rotation；feature flags 只需階層化設定與少量 SecureString。最佳分工為何？

A. RDS password用Secrets Manager並設定rotation；feature flags用Parameter Store的hierarchy與versioning，敏感值才用SecureString
B. Password放EC2 user data，flags放AMI；每30天重建fleet即可
C. 兩者都放Parameter Store，另外自行建立完整database credential rotation與staging-label協調流程
D. 兩者都放Secrets Manager並為每個flag啟用database rotation Lambda

**答案：A**

- **A：** 正確。Secrets Manager提供secret versions、staging labels與rotation workflow；Parameter Store適合階層化configuration。這按生命周期而非「是否為字串」分工。
- **B：** 不正確。User data與AMI會複製長期password，輪替需整個fleet更新且可能留下舊映像。只有非敏感、不可變的啟動設定才適合烘焙。
- **C：** 不正確。Parameter Store能保存SecureString，卻不原生提供Secrets Manager的database rotation contract；題幹要求30天自動換密時，自建整套流程增加風險。
- **D：** 不正確。Secrets Manager可以保存flags，但為一般configuration付出secret rotation與較高操作成本沒有必要。只有flags本身是需輪替的高敏感秘密時才合理。

**事實查證：** [Rotate AWS Secrets Manager secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)、[AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)

### 練習題 2｜SAA｜Secrets Manager four-step rotation

Custom rotation Lambda 偶爾把尚未驗證的新 password 設成目前版本，導致 outage。應如何修正？

A. 每次都覆寫 AWSCURRENT
B. 依 idempotent createSecret、setSecret、testSecret、finishSecret 流程，測試後才把 staging labels 切至 AWSCURRENT
C. 只更新 secret store，不更新 database
D. 先刪 AWSPREVIOUS

**答案：B**

- **A：** 不正確。未測試就發布 AWSCURRENT，會把單一 rotation 錯誤擴大成全面認證故障。
- **B：** 正確。AWSPENDING 經目標系統設定與驗證後才完成 label 切換，且重試必須安全。 此選項只有在rotation、Region、path或certificate lifecycle的constraint改變時才適用；目前沒有滿足題幹的核心責任。
- **C：** 不正確。Stored value 與 target credential 不一致必然失敗。 此選項只有在rotation、Region、path或certificate lifecycle的constraint改變時才適用；目前沒有滿足題幹的核心責任。
- **D：** 不正確。提前刪舊版本會消除 rollback 線索。 此選項只有在rotation、Region、path或certificate lifecycle的constraint改變時才適用；目前沒有滿足題幹的核心責任。

**事實查證：** [Rotate AWS Secrets Manager secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)

### 練習題 3｜SAP｜Client caching across secret rotation

Secret rotation已成功；應用使用connection pool與本地cache，部分instance仍拿舊password而authentication failure。哪個client設計最穩健？

A. 每個業務request都同步呼叫Secrets Manager，完全不做cache
B. 使用有界TTL並加入jitter的client cache；authentication failure時強制重新抓AWSCURRENT、使舊connections失效並安全重建pool，rotation期間保留受控的新舊credential重疊窗口
C. 只在每月maintenance window人工重啟全部instance
D. 永遠讀AWSPREVIOUS，等人工確認數月後再切換

**答案：B**

- **A：** 不正確。每次遠端取secret會增加latency、cost、quota與Secrets Manager短暫不可用的blast radius。Cache應有上限與refresh策略，而不是完全移除。
- **B：** 正確。TTL限制staleness，jitter避免fleet同時刷新；auth failure是提前refresh訊號。只更新cache還不夠，既有database connections也必須淘汰並重建。
- **C：** 不正確。人工重啟延遲、易漏且不能處理非預期rotation。只有無法修改legacy client時，才把受控rolling restart當暫時補救。
- **D：** 不正確。AWSPREVIOUS只適合受控rollback或短暫重疊，永久pin會讓rotation永遠不收斂。Client應以AWSCURRENT為正常來源。

**事實查證：** [Get a cached Secrets Manager secret value](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_cache-ref-secretcache.html)、[Rotate AWS Secrets Manager secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)

### 練習題 4｜SAP｜Cross-account secret access

Account A AppRole 要讀 Account B 的 secret，secret 目前使用 aws/secretsmanager key。完整方案為何？

A. 改用 B 的 customer-managed KMS key；secret resource policy與 A identity policy允許讀取，key policy/IAM允許 A decrypt
B. 只在 secret resource policy Allow A
C. 只在 A 加 GetSecretValue
D. 將 plaintext 複製到 Parameter Store

**答案：A**

- **A：** 正確。Cross-account secret 需要兩側 access policies與可跨帳號授權的 customer-managed key；AWS managed key不適用此模式。
- **B：** 不正確。還缺 caller identity與 KMS authorization。 此選項只有在rotation、Region、path或certificate lifecycle的constraint改變時才適用；目前沒有滿足題幹的核心責任。
- **C：** 不正確。A 不能單方面取得 B secret。 此選項只有在rotation、Region、path或certificate lifecycle的constraint改變時才適用；目前沒有滿足題幹的核心責任。
- **D：** 不正確。只是把 secret 轉移且擴大管理面。 此選項只有在rotation、Region、path或certificate lifecycle的constraint改變時才適用；目前沒有滿足題幹的核心責任。

**事實查證：** [Access secrets from a different account](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html)、[Key policies in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)

### 練習題 5｜SAP｜Regional secret replication

Active-active application 要在兩個 Regions local 讀 secret，避免每次 cross-Region call。應如何設計？

A. 在第二Region建立同名secret並由兩邊各自rotation，假設值永遠一致
B. 只建立KMS multi-Region replica key，Secrets Manager resource與versions就會自動出現在第二Region
C. 設定Secrets Manager replica Regions與各區KMS key；應用依所在Region讀local replica，理解rotation由primary協調，並演練replica promotion與failover
D. 所有Regions永遠cross-Region讀primary，並把primary outage視為可接受

**答案：C**

- **A：** 不正確。獨立rotation會產生不同credentials，database與clients無法同時接受兩套值。只有後端明確支援多組credential且有協調器時才可能。
- **B：** 不正確。KMS multi-Region key只提供related key material，不會複製Secrets Manager resource、versions或staging labels。兩個服務的replication必須分別配置。
- **C：** 正確。Secret replication、regional encryption與application endpoint選擇都需配置；promotion會改變後續管理責任，仍要與完整application failover一起測試。
- **D：** 不正確。這保留cross-Region latency與primary Region故障依賴，違反題幹的local-read與active-active目標。可作簡單單主架構，但不是本情境。

**事實查證：** [Replicate AWS Secrets Manager secrets across Regions](https://docs.aws.amazon.com/secretsmanager/latest/userguide/replicate-secrets.html)

### 練習題 6｜SAA｜Parameter hierarchy and least privilege

Team A只能讀/prod/team-a/* SecureStrings，不能讀/prod/team-b/*。哪個policy設計正確，且避免Parameter Store遞迴路徑的陷阱？

A. 允許arn:aws:ssm:region:acct:parameter/prod並另對/prod/team-b/*寫explicit Deny，然後假設GetParametersByPath recursive永遠尊重child隔離
B. 允許ssm:GetParametersByPath Resource:*，只靠parameter名稱不被猜到
C. 所有teams共用unrestricted kms:Decrypt，SSM path policy只作文件用途
D. 只允許team-a的parameter ARN與必要GetParameter(s)/GetParametersByPath；不要授予/prod父path的recursive讀取，並把kms:Decrypt限制到相應key與encryption context/conditions

**答案：D**

- **A：** 不正確。對父path取得GetParametersByPath recursive存取後，不能期待僅靠child path上的拒絕形成安全分割；官方文件特別警告父層recursive access會暴露其下parameter。
- **B：** 不正確。Parameter名稱不是secret，Resource:*會讓caller列舉其他team路徑。只有完全不含敏感或隔離需求的共享configuration才可能使用廣泛讀取。
- **C：** 不正確。SSM只返回encrypted SecureString仍需KMS解密；unrestricted kms:Decrypt可能讓其他ciphertext被解開。KMS與SSM兩層都要符合least privilege。
- **D：** 正確。Policy的Resource直接縮到parameter/prod/team-a/*，避免授予/prod父層；SecureString還需獨立通過KMS authorization。應實測API是否使用Recursive=true。

**事實查證：** [Restricting access to Parameter Store parameters](https://docs.aws.amazon.com/systems-manager/latest/userguide/ps-retrieval-authorization.html)、[Creating Parameter Store hierarchies](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-hierarchies.html)、[AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)、[Key policies in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)

### 練習題 7｜SAA｜ACM certificate Region

example.com 同時由 CloudFront 與 ap-southeast-1 ALB 提供。ACM certificates應放哪裡？

A. 只在us-east-1放一張certificate，ap-southeast-1 ALB可跨Region直接關聯
B. 在ap-southeast-1建立一張certificate，CloudFront與regional ALB都直接共用該ARN
C. 把certificate PEM存到Secrets Manager，CloudFront與ALB就不需ACM Region association
D. CloudFront viewer certificate放us-east-1；ALB certificate放ALB所在的ap-southeast-1，即使兩張涵蓋相同domain也分別管理

**答案：D**

- **A：** 不正確。CloudFront可用us-east-1 certificate，但regional ALB不能跨Region關聯該ARN。只有把ALB也部署在us-east-1時才可能共用該Region的獨立certificate。
- **B：** 不正確。ALB使用所在Region的certificate，但CloudFront viewer certificate必須位於us-east-1；單一regional ARN不能同時滿足兩者。
- **C：** 不正確。保存PEM不會建立CloudFront或ALB listener association；這些managed services要求ACM/IAM certificate資源並遵守Region規則。
- **D：** 正確。CloudFront與ELB的certificate控制面有不同Region要求；DNS名稱可以相同，certificate資源與renewal monitoring仍是兩份。

**事實查證：** [CloudFront certificate requirements](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html)、[Importing certificates into ACM](https://docs.aws.amazon.com/acm/latest/userguide/import-certificate.html)

### 練習題 8｜SAA｜ACM DNS validation and managed renewal

Public ACM certificate要避免每次到期重新做email驗證。哪個設計最有利於managed renewal，且哪些條件仍需監控？

A. 建立Route 53 health check即可替代domain validation與renewal eligibility
B. 只要certificate尚未到期，無論是否使用或DNS record是否存在都一定自動續期
C. 使用DNS validation並永久保留ACM建立的CNAME；確保certificate仍與符合資格的AWS服務關聯或已export、domain authorization仍有效，監控Renewal eligibility/status與事件
D. 發證後刪除validation CNAME，ACM會把第一次驗證永久記在所有accounts與Regions

**答案：C**

- **A：** 不正確。Health check回答endpoint是否健康，不證明domain所有權，也不改變ACM renewal eligibility。它可用於traffic failover，不能替代validation。
- **B：** 不正確。未使用、未export或缺少validation record的certificate可能不符合managed renewal條件。到期日前仍需告警與人工處置runbook。
- **C：** 正確。DNS CNAME提供持續domain control證明；managed renewal仍取決於ACM文件列出的eligibility與in-use/export狀態。應監控renewal status，而不是假設完全無人值守。
- **D：** 不正確。刪除CNAME可能阻止未來renewal validation，且validation token的reuse有account/Region與DNS條件。只有明確不再需要該certificate時才移除。

**事實查證：** [DNS validation for ACM certificates](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)、[Managed renewal for ACM certificates](https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html)

### 練習題 9｜SAP｜Imported certificate lifecycle

第三方CA certificate匯入ACM並掛到ALB，60天後到期。哪兩項做法與責任正確？（選兩項）

A. 刪除舊certificate再等待ALB自動產生browser-trusted replacement
B. 建立expiration owner與監控，向原CA取得renewed certificate；可reimport至同一certificate ARN以保留支援的service associations，並驗證key、chain與names相容
C. 只要把private key放入Secrets Manager，ACM就會在到期時自動呼叫第三方CA
D. 若建立新的certificate ARN，必須明確更新ALB listener等associations並驗證rollout；它不會因domain相同自動替換
E. Imported certificate一旦在ACM中in use，ACM就會代表任何第三方CA自動續期

**答案：B、D**

- **A：** 不正確。ALB不會自行向public CA申請replacement；先刪除仍在用的certificate可能造成TLS中斷。應先部署與驗證新certificate再移除舊資源。
- **B：** 正確。Reimport同一ARN可保留多數既有association，但匯入者仍負責renewal、private key與chain。變更key type或SANs前要驗證各整合限制。
- **C：** 不正確。Secrets Manager只保存秘密，不具備通用CA enrollment protocol，也不會替ACM觸發第三方簽發。只有自建automation明確整合CA時才可能。
- **D：** 正確。新ARN是一個新resource，load balancer不會按domain自動選它；需要listener change、deployment verification與舊certificate清理。
- **E：** 不正確。ACM無法控制任意第三方CA的issuance流程；managed renewal適用條件與ACM-issued/exportable certificate不同。Imported certificate必須由客戶更新。

**事實查證：** [Importing certificates into ACM](https://docs.aws.amazon.com/acm/latest/userguide/import-certificate.html)、[Reimporting an ACM certificate](https://docs.aws.amazon.com/acm/latest/userguide/import-reimport.html)

### 練習題 10｜SAP｜Private certificates versus public TLS

內部 service mesh需要受控 mTLS identities；公開網站需要一般 browser信任。哪兩項選擇合理？（選兩項）

A. 內部service mesh使用ACM Private CA/private certificates，建立受控trust bundle、issuance policy、revocation與CA lifecycle
B. 公開endpoint使用ACM public certificate並關聯支援的ALB或CloudFront，維持domain validation與renewal監控
C. 公開網站使用自簽root，要求一般瀏覽器忽略certificate warning
D. 讓同一private root CA成為Internet上所有客戶瀏覽器預設信任
E. 用KMS asymmetric key ARN直接當作browser-trusted X.509 certificate，不需CA signature

**答案：A、B**

- **A：** 正確。Private CA適合組織控制的mTLS trust domain，但仍需管理CA hierarchy、issuance、revocation、rotation與成本，不能把「managed」理解為零治理。
- **B：** 正確。Public ACM certificate提供一般browser信任並與managed edge/load balancer整合；CloudFront與regional service仍要遵守各自Region規則。
- **C：** 不正確。一般browser不信任自簽root，要求使用者略過warning會破壞server identity。只有受控測試clients明確安裝trust anchor時才可用。
- **D：** 不正確。Private root不會自動進入全球browser trust stores；它只適用已受控安裝trust bundle的內部clients。公開網站應使用public CA chain。
- **E：** 不正確。KMS signing key是cryptographic key，不含由browser信任CA簽發的subject/SAN與certificate chain。它可簽資料，不能直接取代PKI。

**事實查證：** [AWS Certificate Manager User Guide](https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html)、[AWS Private Certificate Authority User Guide](https://docs.aws.amazon.com/privateca/latest/userguide/PcaWelcome.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「需自動rotation的secret用Secrets Manager；一般設定/secure string…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「密碼、API key與certificate都有生命週期，不能放在AMI、環境檔或repo。」，所以「需自動rotation的secret用Secrets Manager；一般設定/secure string可用Parameter Store；certificate用ACM。」能直接滿足它；若constraint改成「Runtime retrieval降低靜態洩漏但增加權限、cache、availability與quota考量。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「需自動rotation的secret用Secrets Manager；一般設定/secure string可用Parameter Store；certificate用ACM。」。替代方案「Runtime retrieval降低靜態洩漏但增加權限、cache、availability與quota考量。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「每次request同步讀secret造成延遲與throttling，或rotation後connection pool仍用舊值。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「密碼、API key與certificate都有生命週期，不能放在AMI、環境檔或repo。」，排除會導致「每次request同步讀secret造成延遲與throttling，或rotation後connection pool仍用舊值。」的選項，再選「需自動rotation的secret用Secrets Manager；一般設定/secure string可用Parameter Store；certificate用ACM。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-1.3 Determine appropriate data security controls；SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「需自動rotation的secret用Secrets Manager；一般設定/secure string可用Parameter Store；certificate用ACM。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「credentials are dynamic dependencies, not configuration constants」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 29 章　WAF、Shield、Firewall Manager 與 Network Firewall

DDoS、L7惡意請求與網路流量檢查需要不同控制面。

## 跟著一次授權決定走：先從故事開始

把鏡頭拉到一個真實的production現場：全球網站需阻擋bot與SQL injection，並讓所有帳號套用一致WAF policy。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：DDoS、L7惡意請求與網路流量檢查需要不同控制面。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：把身份系統想成辦公大樓：登入證明你是誰，門禁規則才決定你能進哪一間房。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。AWS WAF是這一章的入口，AWS Shield用來畫出邊界；主要方向「WAF處理HTTP規則，Shield處理DDoS保護，Network Firewall檢查VPC流量，Firewall Manager集中下發。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：全球網站需阻擋bot與SQL injection，並讓所有帳號套用一致WAF policy。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[AWS WAF] ── Allow / Deny ──> protected resource
          │ 檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challeng…
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · AWS Shield：保護AWS edge與regional resources免受DDoS。
  · AWS Firewall Manager：跨Organizations accounts集中部署與稽核WAF、Shield、SG、Network F…
  · AWS Network Firewall：在VPC中提供managed stateful/stateless L3–L7 network inspe…

失敗時先找：用NACL阻擋SQL injection，或只部署WAF卻讓origin可被直接繞過。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問AWS WAF有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS WAF和AWS Shield並不是兩個任意的產品名稱。前者適合本章，是因為「WAF處理HTTP規則，Shield處理DDoS保護，Network Firewall檢查VPC流量，Firewall Manager集中下發。」直接回應了眼前的問題；後者描述的「Security Group仍負責資源級allow-list，不能由WAF取代。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：用NACL阻擋SQL injection，或只部署WAF卻讓origin可被直接繞過。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「layer controls by threat model and protocol visibility」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS WAF | 檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challenge。 | Web ACL按priority評估managed/custom rules；可看IP、header、URI、body與rate。 |
| AWS Shield | 保護AWS edge與regional resources免受DDoS。 | Standard自動緩解常見L3/L4攻擊；Advanced增加SRT、visibility、health-based detection與cost protection。 |
| AWS Firewall Manager | 跨Organizations accounts集中部署與稽核WAF、Shield、SG、Network Firewall等policy。 | Delegated admin定義policy與scope，服務持續發現資源並套用或報告noncompliance。 |
| AWS Network Firewall | 在VPC中提供managed stateful/stateless L3–L7 network inspection。 | Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。 |

## 把全圖套進一個具體案例

**場景：** 全球網站需阻擋bot與SQL injection，並讓所有帳號套用一致WAF policy。

1. 故事的起點：全球網站需阻擋bot與SQL injection，並讓所有帳號套用一致WAF policy。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS WAF負責「檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challenge。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Web ACL按priority評估managed/custom rules；可看IP、header、URI、body與rate。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Shield、AWS Firewall Manager、AWS Network Firewall各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「用NACL阻擋SQL injection，或只部署WAF卻讓origin可被直接繞過。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「L3/L4 DDoS使用Shield；任意VPC packet inspection用Network Firewall。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS WAF

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：DDoS、L7惡意請求與網路流量檢查需要不同控制面。
- **具體例子／邊界：** 在「全球網站需阻擋bot與SQL injection，並讓所有帳號套用一致WAF policy。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Shield

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Security Group仍負責資源級allow-list，不能由WAF取代。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：用NACL阻擋SQL injection，或只部署WAF卻讓origin可被直接繞過。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：layer controls by threat model and protocol visibility。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### data plane

實際處理每個packet、request、message、query與資料讀寫的runtime路徑。

### origin

CDN/cache miss時真正取得內容的後端，例如S3、ALB或HTTP server。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### NACL

Network ACL，subnet邊界的stateless ordered allow/deny rules；去回程與ephemeral ports要分開允許。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

## 回到 AWS：Components、功用與責任邊界

### AWS WAF

- **功用：** 檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challenge。
- **底層機制：** Web ACL按priority評估managed/custom rules；可看IP、header、URI、body與rate。
- **關鍵設定：** scope、associated resource、managed rule groups、rate-based rules、IP sets、labels、logging與oversize handling。
- **選擇時機：** SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。
- **替換時機：** L3/L4 DDoS使用Shield；任意VPC packet inspection用Network Firewall。

### AWS Shield

- **功用：** 保護AWS edge與regional resources免受DDoS。
- **底層機制：** Standard自動緩解常見L3/L4攻擊；Advanced增加SRT、visibility、health-based detection與cost protection。
- **關鍵設定：** protected resources、Route 53 health checks、proactive engagement、DRT/SRT contacts與WAF integration。
- **選擇時機：** 公開的CloudFront、Route53、Global Accelerator、ELB或EIP面臨DDoS風險。
- **替換時機：** application payload攻擊仍需WAF；private east-west inspection不由Shield處理。

### AWS Firewall Manager

- **功用：** 跨Organizations accounts集中部署與稽核WAF、Shield、SG、Network Firewall等policy。
- **底層機制：** Delegated admin定義policy與scope，服務持續發現資源並套用或報告noncompliance。
- **關鍵設定：** admin account、organization scope、resource tags/types、remediation與policy type。
- **選擇時機：** 多帳號需要一致security controls與自動套用新資源。
- **替換時機：** 單一帳號少量資源直接設定各服務即可；它不是封包處理data plane。

### AWS Network Firewall

- **功用：** 在VPC中提供managed stateful/stateless L3–L7 network inspection。
- **底層機制：** Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。
- **關鍵設定：** firewall policy、stateless/stateful rule groups、HOME_NET、TLS inspection、logging與route symmetry。
- **選擇時機：** 集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。
- **替換時機：** 只需ENI allow-list用SG；HTTP application attacks用WAF；第三方appliance用GWLB。

## 考前與實作時再查：設定操作手冊

### AWS WAF：逐項設定說明

#### `scope`

- **控制什麼：** `scope`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS WAF建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `associated resource`

- **控制什麼：** `associated resource`指定AWS WAF讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `managed rule groups`

- **控制什麼：** `managed rule groups`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用AWS WAF阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

#### `rate-based rules`

- **控制什麼：** `rate-based rules`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS WAF以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `IP sets`

- **控制什麼：** `IP sets`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用AWS WAF阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

#### `labels`

- **控制什麼：** `labels`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS WAF建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS WAF選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `oversize handling`

- **控制什麼：** `oversize handling`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用AWS WAF阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

### AWS Shield：逐項設定說明

#### `protected resources`

- **控制什麼：** `protected resources`指定AWS Shield讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Route 53 health checks`

- **控制什麼：** `Route 53 health checks`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「公開的CloudFront、Route53、Global Accelerator、ELB或EIP面臨DDoS風險。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Shield的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `proactive engagement`

- **控制什麼：** `proactive engagement`定義重大DDoS或實體device流程中的聯絡人、主動協作、邊緣執行與保管交接證據。
- **何時需要：** Security incident需要AWS支援立即聯絡，或使用Snow device離線搬移敏感資料時。
- **怎麼設定／驗證：** 維護24x7 contacts與runbook，設定engagement前置資料；device每次寄送、接收、unlock、copy與return都保存custody record。
- **常見錯法：** 過期contact會錯過事件；實體device沒有custody/erase驗證，或把edge compute當永久資料中心，都會留下風險。

#### `DRT/SRT contacts`

- **控制什麼：** `DRT/SRT contacts`定義重大DDoS或實體device流程中的聯絡人、主動協作、邊緣執行與保管交接證據。
- **何時需要：** Security incident需要AWS支援立即聯絡，或使用Snow device離線搬移敏感資料時。
- **怎麼設定／驗證：** 維護24x7 contacts與runbook，設定engagement前置資料；device每次寄送、接收、unlock、copy與return都保存custody record。
- **常見錯法：** 過期contact會錯過事件；實體device沒有custody/erase驗證，或把edge compute當永久資料中心，都會留下風險。

#### `WAF integration`

- **控制什麼：** `WAF integration`把AWS Shield與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### AWS Firewall Manager：逐項設定說明

#### `admin account`

- **控制什麼：** `admin account`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多帳號需要一致security controls與自動套用新資源。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Firewall Manager建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `organization scope`

- **控制什麼：** `organization scope`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「多帳號需要一致security controls與自動套用新資源。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Firewall Manager建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `resource tags/types`

- **控制什麼：** `resource tags/types`指定AWS Firewall Manager讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `remediation`

- **控制什麼：** `remediation`把AWS Firewall Manager與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

#### `policy type`

- **控制什麼：** `policy type`選擇AWS Firewall Manager的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

### AWS Network Firewall：逐項設定說明

#### `firewall policy`

- **控制什麼：** `firewall policy`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `stateless/stateful rule groups`

- **控制什麼：** `stateless/stateful rule groups`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `HOME_NET`

- **控制什麼：** `HOME_NET`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `TLS inspection`

- **控制什麼：** `TLS inspection`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `route symmetry`

- **控制什麼：** `route symmetry`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

## 讀到這裡，請用自己的話說一次

1. AWS WAF的責任：檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challenge。
2. 底層機制：Web ACL按priority評估managed/custom rules；可看IP、header、URI、body與rate。
3. 第一個要看的設定：scope、associated resource、managed rule groups、rate-based rules、IP sets、labels、logging與oversize handling。
4. 選擇邏輯：WAF處理HTTP規則，Shield處理DDoS保護，Network Firewall檢查VPC流量，Firewall Manager集中下發。
5. 不要混淆：AWS Shield的責任是「保護AWS edge與regional resources免受DDoS。」；它不會自動取代AWS WAF。
6. 替換訊號：L3/L4 DDoS使用Shield；任意VPC packet inspection用Network Firewall。
7. 最常見錯法：用NACL阻擋SQL injection，或只部署WAF卻讓origin可被直接繞過。
8. 可移植原則：layer controls by threat model and protocol visibility。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS WAF | 檢查HTTP(S) request並依L7規則allow、block、count、CAPTCHA或challenge。 | Web ACL按priority評估managed/custom rules；可看IP、header、URI、body與rate。 | SQL injection、XSS、bots、HTTP flood、geo/IP限制與virtual patch。 | L3/L4 DDoS使用Shield；任意VPC packet inspection用Network Firewall。 |
| AWS Shield | 保護AWS edge與regional resources免受DDoS。 | Standard自動緩解常見L3/L4攻擊；Advanced增加SRT、visibility、health-based detection與cost protection。 | 公開的CloudFront、Route53、Global Accelerator、ELB或EIP面臨DDoS風險。 | application payload攻擊仍需WAF；private east-west inspection不由Shield處理。 |
| AWS Firewall Manager | 跨Organizations accounts集中部署與稽核WAF、Shield、SG、Network Firewall等policy。 | Delegated admin定義policy與scope，服務持續發現資源並套用或報告noncompliance。 | 多帳號需要一致security controls與自動套用新資源。 | 單一帳號少量資源直接設定各服務即可；它不是封包處理data plane。 |
| AWS Network Firewall | 在VPC中提供managed stateful/stateless L3–L7 network inspection。 | Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。 | 集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。 | 只需ENI allow-list用SG；HTTP application attacks用WAF；第三方appliance用GWLB。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Security Group仍負責資源級allow-list，不能由WAF取代。 | 只有當題目條件明確改變時才可能合理。 | 用NACL阻擋SQL injection，或只部署WAF卻讓origin可被直接繞過。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Security Group仍負責資源級allow-list，不能由WAF取代。」之間做選擇。
- 認得常考設定：scope、associated resource、managed rule groups、rate-based rules、IP sets、labels、logging與oversize handling。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：L3/L4 DDoS使用Shield；任意VPC packet inspection用Network Firewall。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜WAF placement for L7 attacks

CloudFront網站遭 SQL injection與 credential stuffing。最佳第一層控制為何？

A. 只啟用Shield Advanced，假設DDoS保護會解析login payload與SQL語法
B. 只在CloudFront cache policy移除query strings，假設所有SQLi與credential stuffing都無法到origin
C. 在CloudFront關聯WAF web ACL，針對SQLi、credential stuffing使用managed/custom、rate-based與bot controls，先Count觀察再enforce，並另外封閉origin bypass
D. 只在ALB security group限制443來源為全Internet，將SQLi偵測交給application logs事後分析

**答案：C**

- **A：** 不正確。Shield處理DDoS resilience，不是HTTP request inspection engine。若題幹只要求容量型攻擊與SRT支援，Shield Advanced才是主要答案。
- **B：** 不正確。SQLi可位於body、headers或保留的URI，credential stuffing也可能是合法格式的POST；cache key設定不能取代security rules。
- **C：** 正確。WAF位於可看見HTTP(S) components的入口，可按rule priority與labels組合檢查；Count有助調整false positive，但origin與application authentication仍要分層保護。
- **D：** 不正確。Security group只控制L3/L4來源與port，application logs又是事後evidence，兩者都不能在edge解析SQLi或對login嘗試計數。

**事實查證：** [AWS WAF web ACLs](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html)、[AWS WAF SQL injection match rule statement](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-sqli-match.html)、[AWS WAF Fraud Control account takeover prevention](https://docs.aws.amazon.com/waf/latest/developerguide/waf-atp.html)、[AWS WAF Bot Control](https://docs.aws.amazon.com/waf/latest/developerguide/waf-bot-control.html)、[AWS Shield features](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html)

### 練習題 2｜SAA｜WAF rule priority and default action

Web ACL先有 Allow partner-IP rule，後有 managed Block rule；同一 request同時匹配。如何判斷？

A. 依 numeric priority順序；terminating action停止後續評估，若無 terminating match才用 default action
B. 所有 rules投票
C. 最新建立 rule獲勝
D. 最具體 rule獲勝

**答案：A**

- **A：** 正確。Priority與 action type決定 flow；Count可繼續並加入 labels，Allow/Block通常終止。
- **B：** 不正確。WAF 不會讓所有匹配規則投票；priority 與 terminating action 決定結果。
- **C：** 不正確。建立時間不決定 evaluation。 Network與edge controls只能處理其可見的protocol與path；若流量不經該control，設定本身就不會產生效果。
- **D：** 不正確。WAF不是 longest-specific-match。 Network與edge controls只能處理其可見的protocol與path；若流量不經該control，設定本身就不會產生效果。

**事實查證：** [AWS WAF rule actions](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-rule-actions.html)

### 練習題 3｜SAP｜WAF body inspection and oversize handling

CloudFront上的WAF body rule只檢查到該resource type的request-body上限；攻擊者把payload放在上限之外。哪個處置最完整？

A. 確認CloudFront目前的預設/可設定body inspection limit與額外費用，為該statement選擇Continue、Match或No match的oversize handling，並在edge/origin限制異常request size及以logs測試
B. 把剩餘bytes交給Shield Standard做application payload inspection
C. 增加rule的WCU就會等比例增加所有resource integrations的body inspection bytes
D. WAF必然完整檢查任意大小body，因此先假設rule engine故障

**答案：A**

- **A：** 正確。CloudFront與多數可調整整合可在官方範圍內提高body inspection limit；oversize action是security decision。Match較fail-closed，Continue或No match需由upstream size controls補足。
- **B：** 不正確。Shield Standard緩解常見DDoS，不解析WAF未檢查的application body。若要檢查完整payload，應在WAF可見範圍外由application/API layer驗證。
- **C：** 不正確。WCU衡量rule processing capacity，不是request body byte quota；提高inspection limit是web ACL/resource設定，且較高body size可能增加費用。
- **D：** 不正確。AWS WAF對body、headers等components有resource-specific inspection limits，超出部分不一定被送入inspection。設計必須明確處理oversize。

**事實查證：** [Oversize web request components in AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/waf-oversize-request-components.html)

### 練習題 4｜SAP｜WAF rate-based scope and forwarded IP

Login API經受控 reverse proxy；要依真正 client限制 /login嘗試。最佳 rule為何？

A. 無條件信任任何 client提供的 X-Forwarded-For
B. Rate-based rule搭配 /login scope-down與正確 aggregation key；只有受控 proxy path才信任 forwarded-IP header並設定 fallback
C. NACL每秒 rate limit
D. 對所有 paths使用單一全球 aggregate

**答案：B**

- **A：** 不正確。Client可偽造 header繞過 per-IP限制。 Network與edge controls只能處理其可見的protocol與path；若流量不經該control，設定本身就不會產生效果。
- **B：** 正確。Rule scope、可信 header chain與 aggregation共同決定 rate counter代表誰。
- **C：** 不正確。NACL沒有 application path/rate semantics。 Network與edge controls只能處理其可見的protocol與path；若流量不經該control，設定本身就不會產生效果。
- **D：** 不正確。會讓其他流量互相影響且不聚焦登入 abuse。 Network與edge controls只能處理其可見的protocol與path；若流量不經該control，設定本身就不會產生效果。

**事實查證：** [AWS WAF rate-based rule statement](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based.html)

### 練習題 5｜SAA｜Shield Standard versus Advanced

營收關鍵 public application需要 DDoS response team支援、enhanced visibility、health-based detection與符合條件的 cost protection。應選？

A. 只購買WAF managed rule group，即自動取得Shield Response Team與DDoS cost protection
B. 使用Network Firewall集中檢查private east-west流量，因此同時獲得Shield Advanced的public DDoS事件支援
C. 只建立CloudFront distribution但不把origin或resource加入Shield Advanced protection，所有Advanced權益仍自動適用
D. 對支援的public resources啟用Shield Advanced，關聯Route 53 health checks並維護SRT contacts/runbooks；Standard仍為所有AWS客戶提供基礎常見網路與傳輸層保護

**答案：D**

- **A：** 不正確。WAF訂閱與Shield Advanced是不同服務與責任；managed rules可處理L7模式，但不自動授予SRT與Advanced cost protection。
- **B：** 不正確。Network Firewall處理routed VPC traffic，不能替代public edge DDoS protection。只有題幹改成east-west/egress inspection時才是主要控制。
- **C：** 不正確。Advanced benefits與protected resource、subscription及配置有關；單純部署CloudFront不代表所有origin與related resources已完成Advanced protection。
- **D：** 正確。題幹明確要求SRT、enhanced visibility、health-based detection與符合條件的cost protection，這些是Advanced operating model；仍需把正確resource納入並做好事件準備。

**事實查證：** [AWS Shield features](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html)

### 練習題 6｜SAP｜Firewall Manager organization control plane

所有現有與未來 accounts的 in-scope ALBs都必須套用核准 WAF policy。最可擴展方案？

A. 在單一Region建立一個web ACL，假設它能跨Region直接關聯所有ALBs與未來accounts
B. 在每個account維護獨立CloudFormation stack，沒有中央scope或drift監控，只靠半年人工盤點
C. 使用Firewall Manager與Organizations delegated administrator，按OU/account與resource tags定義scope，套用WAF policy並選擇identify或auto-remediate noncompliant resources
D. 只用SCP禁止DeleteWebACL，卻不建立、關聯或更新任何WAF policy

**答案：C**

- **A：** 不正確。Regional ALB association受Region與resource scope限制，單一regional web ACL不會跨所有Regions。CloudFront web ACL也有不同scope。
- **B：** 不正確。IaC可部署，但沒有中央inventory、scope與remediation時新accounts與resource drift仍會漏失。小型固定環境可暫用，數百accounts不合題幹。
- **C：** 正確。Firewall Manager是organization security policy control plane，可自動發現in-scope resources並稽核或補救；runtime packets仍由各resource關聯的WAF處理。
- **D：** 不正確。SCP可限制control-plane API，卻不會建立web ACL、選rule groups或把它關聯新ALB；它只能作防竄改的相鄰guardrail。

**事實查證：** [AWS Firewall Manager](https://docs.aws.amazon.com/waf/latest/developerguide/fms-chapter.html)、[AWS Organizations terminology and concepts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html)

### 練習題 7｜SAP｜Network Firewall route insertion

Private subnets的 internet egress必須先通過 Network Firewall再到 NAT/IGW。最重要的 networking設計是什麼？

A. 把NAT gateway改成internet-facing ALB，由ALB轉送所有TCP/UDP egress
B. 只建立firewall policy並attach到firewall，private subnet route tables維持直接指向NAT gateway
C. 讓forward path經firewall endpoint、return path直接回private subnet，以降低hop數
D. 在各使用AZ的inspection subnet建立firewall endpoint；設計private、firewall、NAT/IGW route tables，使forward與return path對稱經同一AZ endpoint並避免cross-AZ繞行

**答案：D**

- **A：** 不正確。ALB不是一般VPC egress router，也不能替代NAT的source translation與Network Firewall的任意protocol inspection。
- **B：** 不正確。Policy只定義看到流量後如何處理；沒有route insertion時packets仍直接到NAT，firewall data plane完全不可見。
- **C：** 不正確。Stateful inspection需要看到雙向flow；asymmetric routing會使connection state不完整並產生drop或繞過。應同時設計回程route。
- **D：** 正確。Endpoint placement與每張route table共同形成inspection path；per-AZ設計可保留對稱性、降低cross-AZ成本，並要處理firewall/NAT故障。

**事實查證：** [AWS Network Firewall architectures](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)

### 練習題 8｜SAP｜Stateless versus stateful firewall processing

已知惡意五元組要立即丟棄；其他 allowed flows需 domain/connection-aware inspection。應如何分工？

A. 只使用security group，並在rule description中貼上Suricata signature讓SG解析payload
B. Stateless rule group先對確定惡意五元組drop，其餘流量依default action送入stateful engine；stateful rules按設定的strict/default order處理domain、flow與Suricata semantics
C. 用WAF檢查所有non-HTTP TCP與UDP egress，Network Firewall只保留DNS logs
D. 把所有traffic先交給stateful engine，但同時設定stateless default action為drop all，假設兩者仍會依序處理

**答案：B**

- **A：** 不正確。Security group是stateful L3/L4 allow-list，不執行Suricata engine或payload signatures。它可限制reachability，但不能完成題幹的domain/connection-aware inspection。
- **B：** 正確。Stateless層適合可由header/tuple決定的高速動作，其他flows再進stateful inspection；default actions與rule order若不一致，可能在到達stateful前就被丟棄。
- **C：** 不正確。WAF只處理支援resource上的HTTP(S) requests，不能觀察任意TCP/UDP egress。Network Firewall才位於routed network path。
- **D：** 不正確。Stateless default drop會讓未匹配traffic在進入stateful engine前消失；若要stateful inspection，default action必須正確forward。

**事實查證：** [AWS Network Firewall architectures](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)

### 練習題 9｜SAA｜Choose controls by protocol visibility

架構同時要阻擋 HTTP SQL injection、限制 VPC outbound domains、只允許 app tier連 database TCP port。哪兩項敘述正確？（選兩項）

A. Security group可限制app security group到database port的stateful reachability，但不能解析SQL injection payload
B. IAM identity policy可取代subnet routes與security group，讓沒有network path的TCP connection仍可建立
C. WAF檢查支援入口的HTTP(S) SQLi；Network Firewall檢查被route導入的VPC egress/domain traffic
D. Shield Advanced負責database user authorization與row-level access policy
E. NACL以statelessCIDR/port rules可同時解析SQL body、建立domain state並識別application user

**答案：A、C**

- **A：** 正確。Security group引用app tier group可表達resource-level port allow-list並自動允許回程，但application payload仍需WAF或應用程式驗證。
- **B：** 不正確。IAM決定AWS API authorization，不能創造IP route或TCP reachability。某些service IAM auth仍建立在可用network path之上。
- **C：** 正確。控制必須放在能看見所需context的位置：WAF有HTTP components，Network Firewall有routed flow/domain state；兩者都不取代database authorization。
- **D：** 不正確。Shield提供DDoS protection與response能力，不知道database帳號或rows。只有題幹是public endpoint容量型攻擊時才適用。
- **E：** 不正確。NACL只能依L3/L4欄位做stateless allow/deny，沒有HTTP body、domain flow state或使用者identity。它可作subnet邊界的粗粒度filter。

**事實查證：** [AWS WAF web ACLs](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html)、[AWS WAF SQL injection match rule statement](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-sqli-match.html)、[AWS Network Firewall architectures](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)

### 練習題 10｜SAP｜Layered CloudFront origin protection

CloudFront已關聯WAF，但攻擊者能直接呼叫internet-facing ALB DNS繞過edge controls。哪兩項形成可部署的修復？（選兩項）

A. 只信任Host header等於公開網域，因為client無法自行設定Host
B. 若架構與限制允許，將ALB改為internal並使用CloudFront VPC origin，移除public direct-origin path，同時驗證VPC origin的protocol與resource限制
C. 只增加CloudFront WAF rules，不改ALB的可達性或listener
D. 若ALB必須internet-facing，將security group來源限到CloudFront origin-facing managed prefix list，並由CloudFront加入定期輪替的secret custom header、ALB listener rule驗證；仍保留application authentication
E. 若ALB必須internet-facing，只要把DNS名稱從文件刪除就可視為不可達

**答案：B、D**

- **A：** 不正確。Client可以設定Host header，且公開ALB仍接受direct TCP/TLS連線。Host可作routing input，不是caller identity或shared secret。
- **B：** 正確。VPC origin可從架構上移除Internet直達ALB，但支援的ALB/NLB/EC2類型、Region、subnet與protocol功能需先確認。它仍不取代application身份。
- **C：** 不正確。Direct request不經CloudFront，因此也不經其web ACL；edge規則再多都無法封閉替代ingress path。
- **D：** 正確。Managed prefix list縮小network來源，secret header/listener rule再限制能否通過application入口；header是shared secret需rotation，且不能取代end-user authorization。
- **E：** 不正確。DNS可由certificate transparency、掃描或歷史記錄發現，隱藏名稱不是access control。只有network path與listener policy真正拒絕direct request才有效。

**事實查證：** [Restrict access to Application Load Balancers from CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html)、[Use VPC origins with CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「WAF處理HTTP規則，Shield處理DDoS保護，Network Firewall檢查VPC流量，Fi…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「DDoS、L7惡意請求與網路流量檢查需要不同控制面。」，所以「WAF處理HTTP規則，Shield處理DDoS保護，Network Firewall檢查VPC流量，Firewall Manager集中下發。」能直接滿足它；若constraint改成「Security Group仍負責資源級allow-list，不能由WAF取代。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「WAF處理HTTP規則，Shield處理DDoS保護，Network Firewall檢查VPC流量，Firewall Manager集中下發。」。替代方案「Security Group仍負責資源級allow-list，不能由WAF取代。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「用NACL阻擋SQL injection，或只部署WAF卻讓origin可被直接繞過。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「DDoS、L7惡意請求與網路流量檢查需要不同控制面。」，排除會導致「用NACL阻擋SQL injection，或只部署WAF卻讓origin可被直接繞過。」的選項，再選「WAF處理HTTP規則，Shield處理DDoS保護，Network Firewall檢查VPC流量，Firewall Manager集中下發。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「WAF處理HTTP規則，Shield處理DDoS保護，Network Firewall檢查VPC流量，Firewall Manager集中下發。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「layer controls by threat model and protocol visibility」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 30 章　GuardDuty、Inspector、Macie、Detective 與 Security Hub

組織需要區分威脅偵測、漏洞、敏感資料與調查聚合。

## 跟著一次授權決定走：先從故事開始

如果今天由你值班，收到的需求可能是這樣：安全中心要集中各帳號finding，判斷憑證外洩、EC2漏洞與S3個資。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：組織需要區分威脅偵測、漏洞、敏感資料與調查聚合。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：把身份系統想成辦公大樓：登入證明你是誰，門禁規則才決定你能進哪一間房。 這只是起點，因為類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon GuardDuty承接主要責任，以Amazon Inspector檢查替代條件，並用「GuardDuty找可疑活動，Inspector掃workload漏洞，Macie找S3敏感資料，Detective協助調查，Security Hub彙整。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：安全中心要集中各帳號finding，判斷憑證外洩、EC2漏洞與S3個資。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[Amazon GuardDuty] ── Allow / Deny ──> protected resource
          │ 從AWS telemetry偵測credential compromise、惡意活動與異常行為。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · Amazon Inspector：持續掃描EC2、container images與Lambda packages的漏洞與暴露。
  · Amazon Macie：發現、分類與保護S3中的敏感資料。
  · Amazon Detective：把security findings相關的entities與時間行為關聯，協助根因調查。
  · AWS Security Hub：集中標準化security findings並執行security standards checks。

失敗時先找：看到Security Hub finding便誤以為它自行掃描所有資源，或沒有owner與response workflow。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問Amazon GuardDuty有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon GuardDuty和Amazon Inspector並不是兩個任意的產品名稱。前者適合本章，是因為「GuardDuty找可疑活動，Inspector掃workload漏洞，Macie找S3敏感資料，Detective協助調查，Security Hub彙整。」直接回應了眼前的問題；後者描述的「Config/Audit Manager偏合規與設定證據，CloudTrail提供API活動原始紀錄。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：看到Security Hub finding便誤以為它自行掃描所有資源，或沒有owner與response workflow。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「detection requires signal ownership and response paths」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon GuardDuty | 從AWS telemetry偵測credential compromise、惡意活動與異常行為。 | Managed detectors分析CloudTrail、VPC Flow/DNS、EKS、S3、runtime等signals並產生findings。 |
| Amazon Inspector | 持續掃描EC2、container images與Lambda packages的漏洞與暴露。 | 比對software inventory/CVEs並結合network reachability與exploitability產生risk findings。 |
| Amazon Macie | 發現、分類與保護S3中的敏感資料。 | 先建立bucket inventory與security posture，再以managed/custom identifiers抽樣或job掃描objects。 |
| Amazon Detective | 把security findings相關的entities與時間行為關聯，協助根因調查。 | 建立behavior graph，彙整CloudTrail、VPC Flow、GuardDuty/EKS等資料供pivot與timeline分析。 |
| AWS Security Hub | 集中標準化security findings並執行security standards checks。 | 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。 |

## 把全圖套進一個具體案例

**場景：** 安全中心要集中各帳號finding，判斷憑證外洩、EC2漏洞與S3個資。

1. 故事的起點：安全中心要集中各帳號finding，判斷憑證外洩、EC2漏洞與S3個資。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon GuardDuty負責「從AWS telemetry偵測credential compromise、惡意活動與異常行為。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Managed detectors分析CloudTrail、VPC Flow/DNS、EKS、S3、runtime等signals並產生findings。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon Inspector、Amazon Macie、Amazon Detective、AWS Security Hub各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「看到Security Hub finding便誤以為它自行掃描所有資源，或沒有owner與response workflow。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「漏洞掃描用Inspector；敏感S3資料發現用Macie；調查關聯用Detective。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon GuardDuty

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：組織需要區分威脅偵測、漏洞、敏感資料與調查聚合。
- **具體例子／邊界：** 在「安全中心要集中各帳號finding，判斷憑證外洩、EC2漏洞與S3個資。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon Inspector

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Config/Audit Manager偏合規與設定證據，CloudTrail提供API活動原始紀錄。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：看到Security Hub finding便誤以為它自行掃描所有資源，或沒有owner與response workflow。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：detection requires signal ownership and response paths。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### discovery

透過agent、hypervisor/CMDB資料與owner訪談蒐集inventory、utilization及network connections；資料需要交叉驗證。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### catalog

描述datasets、schema、partition與location的metadata索引；它不保存原始資料本身。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### Amazon GuardDuty

- **功用：** 從AWS telemetry偵測credential compromise、惡意活動與異常行為。
- **底層機制：** Managed detectors分析CloudTrail、VPC Flow/DNS、EKS、S3、runtime等signals並產生findings。
- **關鍵設定：** detector、protection plans、trusted IP/threat lists、publishing frequency、organization admin與EventBridge response。
- **選擇時機：** 需要managed threat detection與多帳號集中findings。
- **替換時機：** 漏洞掃描用Inspector；敏感S3資料發現用Macie；調查關聯用Detective。

### Amazon Inspector

- **功用：** 持續掃描EC2、container images與Lambda packages的漏洞與暴露。
- **底層機制：** 比對software inventory/CVEs並結合network reachability與exploitability產生risk findings。
- **關鍵設定：** scan types、ECR rescan duration、suppression rules、organization admin與EventBridge/Security Hub integration。
- **選擇時機：** patch prioritization、image pipeline與runtime workload vulnerability management。
- **替換時機：** 可疑行為不是漏洞時用GuardDuty；設定合規用Config。

### Amazon Macie

- **功用：** 發現、分類與保護S3中的敏感資料。
- **底層機制：** 先建立bucket inventory與security posture，再以managed/custom identifiers抽樣或job掃描objects。
- **關鍵設定：** automated discovery、classification jobs、sampling、custom data identifiers、allow lists與organization admin。
- **選擇時機：** PII、financial、credential data盤點與S3 exposure風險。
- **替換時機：** 一般threat detection用GuardDuty；跨服務data catalog/governance用Glue/Lake Formation。

### Amazon Detective

- **功用：** 把security findings相關的entities與時間行為關聯，協助根因調查。
- **底層機制：** 建立behavior graph，彙整CloudTrail、VPC Flow、GuardDuty/EKS等資料供pivot與timeline分析。
- **關鍵設定：** behavior graph、member accounts、data sources、finding groups與investigation scope。
- **選擇時機：** GuardDuty finding後追查user、role、IP、instance與activity關係。
- **替換時機：** 它不主動阻擋或修補；response需EventBridge、SOAR、SSM等。

### AWS Security Hub

- **功用：** 集中標準化security findings並執行security standards checks。
- **底層機制：** 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。
- **關鍵設定：** standards/controls、central configuration、aggregator Region、automation rules與EventBridge。
- **選擇時機：** SOC需要跨帳號單一finding queue與compliance view。
- **替換時機：** 它不取代GuardDuty/Inspector/Macie的偵測引擎，也不等於SIEM的完整log search。

## 考前與實作時再查：設定操作手冊

### Amazon GuardDuty：逐項設定說明

#### `detector`

- **控制什麼：** `detector`選擇Amazon GuardDuty分析哪些telemetry/data，以及如何建立finding或敏感資料分類。
- **何時需要：** 需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。
- **怎麼設定／驗證：** 啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。
- **常見錯法：** Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。

#### `protection plans`

- **控制什麼：** `protection plans`選擇Amazon GuardDuty分析哪些telemetry/data，以及如何建立finding或敏感資料分類。
- **何時需要：** 需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。
- **怎麼設定／驗證：** 啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。
- **常見錯法：** Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。

#### `trusted IP/threat lists`

- **控制什麼：** `trusted IP/threat lists`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用Amazon GuardDuty阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

#### `publishing frequency`

- **控制什麼：** `publishing frequency`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「需要managed threat detection與多帳號集中findings。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon GuardDuty選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `organization admin`

- **控制什麼：** `organization admin`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「需要managed threat detection與多帳號集中findings。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon GuardDuty建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `EventBridge response`

- **控制什麼：** `EventBridge response`把Amazon GuardDuty與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### Amazon Inspector：逐項設定說明

#### `scan types`

- **控制什麼：** `scan types`定義Amazon Inspector用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `ECR rescan duration`

- **控制什麼：** `ECR rescan duration`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「patch prioritization、image pipeline與runtime workload vulnerability management。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon Inspector的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `suppression rules`

- **控制什麼：** `suppression rules`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用Amazon Inspector阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

#### `organization admin`

- **控制什麼：** `organization admin`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「patch prioritization、image pipeline與runtime workload vulnerability management。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Inspector建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `EventBridge/Security Hub integration`

- **控制什麼：** `EventBridge/Security Hub integration`把Amazon Inspector與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### Amazon Macie：逐項設定說明

#### `automated discovery`

- **控制什麼：** `automated discovery`選擇Amazon Macie分析哪些telemetry/data，以及如何建立finding或敏感資料分類。
- **何時需要：** 需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。
- **怎麼設定／驗證：** 啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。
- **常見錯法：** Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。

#### `classification jobs`

- **控制什麼：** `classification jobs`選擇Amazon Macie分析哪些telemetry/data，以及如何建立finding或敏感資料分類。
- **何時需要：** 需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。
- **怎麼設定／驗證：** 啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。
- **常見錯法：** Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。

#### `sampling`

- **控制什麼：** `sampling`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「PII、financial、credential data盤點與S3 exposure風險。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Macie選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `custom data identifiers`

- **控制什麼：** `custom data identifiers`選擇Amazon Macie分析哪些telemetry/data，以及如何建立finding或敏感資料分類。
- **何時需要：** 需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。
- **怎麼設定／驗證：** 啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。
- **常見錯法：** Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。

#### `allow lists`

- **控制什麼：** `allow lists`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。
- **何時需要：** 要用Amazon Macie阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。
- **怎麼設定／驗證：** 先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。
- **常見錯法：** 永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。

#### `organization admin`

- **控制什麼：** `organization admin`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「PII、financial、credential data盤點與S3 exposure風險。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Macie建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

### Amazon Detective：逐項設定說明

#### `behavior graph`

- **控制什麼：** `behavior graph`選擇Amazon Detective分析哪些telemetry/data，以及如何建立finding或敏感資料分類。
- **何時需要：** 需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。
- **怎麼設定／驗證：** 啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。
- **常見錯法：** Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。

#### `member accounts`

- **控制什麼：** `member accounts`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「GuardDuty finding後追查user、role、IP、instance與activity關係。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Detective建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `data sources`

- **控制什麼：** `data sources`指定Amazon Detective讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `finding groups`

- **控制什麼：** `finding groups`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

#### `investigation scope`

- **控制什麼：** `investigation scope`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「GuardDuty finding後追查user、role、IP、instance與activity關係。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Detective建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

### AWS Security Hub：逐項設定說明

#### `standards/controls`

- **控制什麼：** `standards/controls`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「SOC需要跨帳號單一finding queue與compliance view。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Security Hub以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `central configuration`

- **控制什麼：** `central configuration`是一組可版本化的engine/runtime參數，會改變AWS Security Hub的實際process行為。
- **何時需要：** 當需求符合「SOC需要跨帳號單一finding queue與compliance view。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

#### `aggregator Region`

- **控制什麼：** `aggregator Region`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。
- **何時需要：** 多帳號需要一致review、configuration inventory與可追蹤improvement plan時。
- **怎麼設定／驗證：** 指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。
- **常見錯法：** 只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。

#### `automation rules`

- **控制什麼：** `automation rules`把AWS Security Hub與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

#### `EventBridge`

- **控制什麼：** `EventBridge`把AWS Security Hub與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

## 讀到這裡，請用自己的話說一次

1. Amazon GuardDuty的責任：從AWS telemetry偵測credential compromise、惡意活動與異常行為。
2. 底層機制：Managed detectors分析CloudTrail、VPC Flow/DNS、EKS、S3、runtime等signals並產生findings。
3. 第一個要看的設定：detector、protection plans、trusted IP/threat lists、publishing frequency、organization admin與EventBridge response。
4. 選擇邏輯：GuardDuty找可疑活動，Inspector掃workload漏洞，Macie找S3敏感資料，Detective協助調查，Security Hub彙整。
5. 不要混淆：Amazon Inspector的責任是「持續掃描EC2、container images與Lambda packages的漏洞與暴露。」；它不會自動取代Amazon GuardDuty。
6. 替換訊號：漏洞掃描用Inspector；敏感S3資料發現用Macie；調查關聯用Detective。
7. 最常見錯法：看到Security Hub finding便誤以為它自行掃描所有資源，或沒有owner與response workflow。
8. 可移植原則：detection requires signal ownership and response paths。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon GuardDuty | 從AWS telemetry偵測credential compromise、惡意活動與異常行為。 | Managed detectors分析CloudTrail、VPC Flow/DNS、EKS、S3、runtime等signals並產生findings。 | 需要managed threat detection與多帳號集中findings。 | 漏洞掃描用Inspector；敏感S3資料發現用Macie；調查關聯用Detective。 |
| Amazon Inspector | 持續掃描EC2、container images與Lambda packages的漏洞與暴露。 | 比對software inventory/CVEs並結合network reachability與exploitability產生risk findings。 | patch prioritization、image pipeline與runtime workload vulnerability management。 | 可疑行為不是漏洞時用GuardDuty；設定合規用Config。 |
| Amazon Macie | 發現、分類與保護S3中的敏感資料。 | 先建立bucket inventory與security posture，再以managed/custom identifiers抽樣或job掃描objects。 | PII、financial、credential data盤點與S3 exposure風險。 | 一般threat detection用GuardDuty；跨服務data catalog/governance用Glue/Lake Formation。 |
| Amazon Detective | 把security findings相關的entities與時間行為關聯，協助根因調查。 | 建立behavior graph，彙整CloudTrail、VPC Flow、GuardDuty/EKS等資料供pivot與timeline分析。 | GuardDuty finding後追查user、role、IP、instance與activity關係。 | 它不主動阻擋或修補；response需EventBridge、SOAR、SSM等。 |
| AWS Security Hub | 集中標準化security findings並執行security standards checks。 | 從整合服務與partner接收ASFF findings，聚合、關聯、抑制並以automation rules分流。 | SOC需要跨帳號單一finding queue與compliance view。 | 它不取代GuardDuty/Inspector/Macie的偵測引擎，也不等於SIEM的完整log search。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Config/Audit Manager偏合規與設定證據，CloudTrail提供API活動原始紀錄。 | 只有當題目條件明確改變時才可能合理。 | 看到Security Hub finding便誤以為它自行掃描所有資源，或沒有owner與response workflow。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Config/Audit Manager偏合規與設定證據，CloudTrail提供API活動原始紀錄。」之間做選擇。
- 認得常考設定：detector、protection plans、trusted IP/threat lists、publishing frequency、organization admin與EventBridge response。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：漏洞掃描用Inspector；敏感S3資料發現用Macie；調查關聯用Detective。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜Credential-compromise detection

某IAM access key突然從異常ASN與地理位置執行resource discovery APIs。哪個偵測與response path最適合？

A. 只部署current AWS Security Hub，不啟用任何來源detector，並假設它自行觀察所有原始API
B. Amazon Inspector把CloudTrail actor event轉成package CVE並自動輪替access key
C. Macie掃描所有IAM policies來判斷key是否被竊，再刪除S3 objects
D. GuardDuty分析CloudTrail management events等foundational data sources產生credential-access finding，透過EventBridge近即時送到具名containment workflow以停用key、隔離影響並驗證

**答案：D**

- **A：** 不正確。Security Hub彙整與關聯來源security data，不會在沒有data source時憑空偵測所有API。必須先啟用合適detector與logging。
- **B：** 不正確。Inspector掃EC2/ECR/Lambda vulnerabilities，不以異常API行為判定credential compromise。只有題幹是software CVE時才是主要服務。
- **C：** 不正確。Macie聚焦S3 inventory與敏感資料，不是IAM key behavior detector。它可在事件後評估資料暴露，但不取代GuardDuty。
- **D：** 正確。GuardDuty用支援telemetry建立threat finding；EventBridge只負責遞送，response仍需owner、runbook、credential disable與false-positive驗證。

**事實查證：** [Foundational data sources in GuardDuty](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_data-sources.html)、[GuardDuty findings with EventBridge](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_eventbridge.html)

### 練習題 2｜SAP｜GuardDuty protection plans

Organization需要S3 object-level threats、EKS/ECS/EC2 runtime activity、EC2/EBS與container workload malware，以及RDS/Aurora login threats。只啟用base GuardDuty detector是否足夠？

A. 足夠；GuardDuty未來新增的所有protection plans必然在每個member account與Region自動啟用
B. 不足；需求應分別映射到S3 Protection、Runtime Monitoring、Malware Protection與RDS Protection，逐Region確認支援resource、prerequisites、delegated-admin auto-enable mode與既有/新member coverage
C. 只開CloudTrail trail即可取得runtime agent telemetry、malware volume scan與database login analysis
D. 在Security Hub CSPM啟用一個standard會替所有accounts自動打開GuardDuty optional plans

**答案：B**

- **A：** 不正確。Optional plans、service新增與organization auto-enable偏好都需明確治理；base detector不代表每個plan、account與Region已涵蓋。
- **B：** 正確。每個plan有不同telemetry、resource eligibility與啟用方式；例如Runtime Monitoring與Malware Protection不是單純CloudTrail來源。Coverage matrix要記錄例外與成本。
- **C：** 不正確。CloudTrail management events是foundational input之一，卻不提供runtime agent、malware scan或所有database login telemetry。只有API threat部分可能使用它。
- **D：** 不正確。Security Hub CSPM接收findings與評估controls，不替GuardDuty修改detector/protection-plan configuration。必須在GuardDuty delegated admin配置。

**事實查證：** [GuardDuty protection plans](https://docs.aws.amazon.com/guardduty/latest/ug/protection-plans.html)、[GuardDuty organization auto-enable preferences](https://docs.aws.amazon.com/guardduty/latest/ug/set-guardduty-auto-enable-preferences.html)

### 練習題 3｜SAP｜Trusted IP list versus threat list

公司授權的EC2漏洞scanner固定從203.0.113.0/28掃描，造成GuardDuty中由支援IP telemetry產生的PortProbeUnprotectedPort findings；另一組IP是已知惡意command-and-control。如何配置？

A. 把兩組CIDR都放trusted IP list，因為任何已知IP都不需GuardDuty再分析
B. 把scanner加到Inspector exclusion，GuardDuty就會在所有Regions停止所有finding類型
C. 把兩組都做finding suppression，且永遠不保留原始finding或變更紀錄
D. 只在scanner所在Region建立範圍最小的trusted IP list並驗證受影響finding類型；惡意indicators用支援格式放threat list，治理CIDR、quota、版本與blind spot

**答案：D**

- **A：** 不正確。Trusted list會讓GuardDuty不產生部分與該IP相關的findings，把惡意IP加入會刻意製造blind spot。它也不是所有finding類型的全域allow list。
- **B：** 不正確。Inspector與GuardDuty是不同服務，Inspector exclusion不會修改GuardDuty detector或trusted list。只有CVE scanning scope才在Inspector處理。
- **C：** 不正確。Suppression rule作用在finding結果，不是threat-intel語意；永久抑制會掩蓋scope改變。只有已理解且仍保留metrics的已知noise才考慮。
- **D：** 正確。題幹明示受trusted list影響的IP finding；lists是Regional且有數量/格式限制。Threat list提高對惡意indicators的偵測，trusted list必須最小並定期到期審查。

**事實查證：** [GuardDuty trusted IP and threat lists](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_upload-lists.html)

### 練習題 4｜SAA｜Inspector resource coverage

安全團隊要持續找 EC2 packages、ECR images與 Lambda dependencies的 CVEs。應選？

A. Macie
B. GuardDuty
C. 啟用相應 Amazon Inspector scan types，確認 EC2/ECR/Lambda各自 prerequisites與 rescan coverage
D. 一次掃 golden AMI即可永久涵蓋 fleet

**答案：C**

- **A：** 不正確。Macie聚焦 S3 data discovery。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。
- **B：** 不正確。GuardDuty偵測威脅活動，不是主要 CVE scanner。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。
- **C：** 正確。Inspector對不同 resource type有不同 scanning path與 eligibility，finding需依 exploitable context/fix治理。
- **D：** 不正確。新 CVE、running drift與新 images都會使一次掃描過期。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。

**事實查證：** [Scanning resources with Amazon Inspector](https://docs.aws.amazon.com/inspector/latest/user/scanning-resources.html)

### 練習題 5｜SAP｜Immutable image-pipeline remediation

已部署 container image出現 critical Inspector finding。最佳 remediation pattern？

A. 依治理 severity gate停止 promotion，修補 base/dependency後 rebuild image、redeploy immutable workloads並保留 evidence
B. 只 patch running container
C. 全域 suppress finding
D. 啟用 WAF即可修 CVE

**答案：A**

- **A：** 正確。Source-to-image修復避免下一次重建復發，並讓 finding與 deployment evidence可追蹤。
- **B：** 不正確。Running patch會在 reschedule消失且 image仍有漏洞。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。
- **C：** 不正確。Suppression不消除 risk。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。
- **D：** 不正確。WAF可能降低部分 exploit面，但不修 package。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。

**事實查證：** [Scanning resources with Amazon Inspector](https://docs.aws.amazon.com/inspector/latest/user/scanning-resources.html)

### 練習題 6｜SAA｜Macie sensitive-data discovery

公司要在大型 S3 estate找 PII、建立 bucket sensitivity視圖並辨識公開風險。應選？

A. Macie automated discovery或 scoped classification jobs，搭配 managed/custom identifiers、sampling與 allow lists
B. GuardDuty分類 PII
C. Macie直接掃 EBS與任意 database rows
D. Inspector掃所有 objects

**答案：A**

- **A：** 正確。Macie聚焦 S3 inventory、posture與敏感資料分類；job scope與 sampling影響成本/coverage。
- **B：** 不正確。GuardDuty處理 threat findings。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。
- **C：** 不正確。Macie不是通用所有資料庫內容 scanner。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。
- **D：** 不正確。Inspector掃 vulnerabilities，不讀 S3內容分類 PII。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。

**事實查證：** [What is Amazon Macie?](https://docs.aws.amazon.com/macie/latest/user/what-is-macie.html)

### 練習題 7｜SAP｜Detective investigation graph

分析師要把 GuardDuty role-compromise finding連到 IP、API activity、EC2與事件 timeline。哪個服務最合適？

A. Macie
B. Artifact
C. Amazon Detective的 behavior graph/finding groups；它協助調查但不會自動隔離或 patch
D. Config

**答案：C**

- **A：** 不正確。Macie提供 data findings。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。
- **B：** 不正確。Artifact提供 AWS compliance reports。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。
- **C：** 正確。Detective關聯 entities與歷史行為，幫助 root-cause investigation；containment需另外執行。
- **D：** 不正確。Config追蹤 resource configuration。 Detection、aggregation與remediation是三個步驟；選項必須符合資料來源、coverage scope及明確response owner。

**事實查證：** [What is Amazon Detective?](https://docs.aws.amazon.com/detective/latest/userguide/what-is-detective.html)、[How Amazon Detective is used for investigation](https://docs.aws.amazon.com/detective/latest/userguide/detective-investigation-about.html)

### 練習題 8｜SAA · ENRICHMENT-CURRENT｜Current AWS Security Hub OCSF correlation

2026年的SOC要把多個AWS安全資料來源標準化後做跨訊號correlation、exposure與attack-path prioritization。哪項描述正確？

A. Current AWS Security Hub只接受ASFF，核心功能仍等同Security Hub CSPM的standards與controls
B. Current AWS Security Hub使用OCSF正規化security data並提供correlation、exposure與attack-path能力；來源服務仍負責各自偵測，Security Hub CSPM則是另一個以ASFF、standards與controls為主的產品
C. 啟用Current AWS Security Hub後，所有findings都會在沒有runbook與owner的情況下自動完成remediation
D. Current AWS Security Hub自行取代GuardDuty、Inspector與Macie，不需任何來源資料

**答案：B**

- **A：** 不正確。ASFF、standards與controls是Security Hub CSPM的主要語意；current AWS Security Hub採OCSF security data。舊教材的「Security Hub」名稱必須先判斷指哪個產品。
- **B：** 正確。這明確區分兩個current產品：AWS Security Hub以OCSF、correlation與exposure為核心；Security Hub CSPM維持ASFF、controls與posture management。
- **C：** 不正確。Prioritization與automation可觸發workflow，但containment/remediation仍需要權限、owner、驗證與rollback。Managed service不等於無條件自動修復。
- **D：** 不正確。Hub需要GuardDuty、Inspector、Macie等來源信號才能關聯，並不重複實作所有detectors。若來源沒有啟用或coverage有洞，correlation也看不到事件。

**事實查證：** [Introduction to AWS Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub-v2.html)、[OCSF in AWS Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-ocsf.html)、[Introduction to AWS Security Hub CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)

### 練習題 9｜SAP｜Security Hub CSPM controls and AWS Config

Security Hub CSPM中的security control產生FAILED control finding。哪兩項解讀正確？（選兩項）

A. SCP會持續掃描packages與container images，因此可替代CSPM control finding
B. 某control為PASSED即證明resource不存在任何安全風險，其他controls與runtime threats可忽略
C. 許多CSPM controls使用AWS Config記錄的resource configuration；應先確認recorder、resource scope、Region與該control的精確檢查邏輯
D. AWS Config主要回答哪個IAM principal在何時呼叫API，CloudTrail只保存resource snapshot
E. Control finding是某項posture檢查的evidence，不代表API已被preventive阻擋或resource已自動修復；仍需owner、remediation與重新評估

**答案：C、E**

- **A：** 不正確。SCP是authorization ceiling，不執行CVE或configuration scanning。若需求是阻止某些control-plane API，可用SCP作相鄰preventive guardrail。
- **B：** 不正確。PASSED只代表特定時間、特定control條件成立，不涵蓋其他misconfiguration、identity風險或runtime threat。它不是完整安全證明。
- **C：** 正確。Config-backed control沒有正確recording scope時可能出現UNKNOWN、無資料或不完整coverage；還要讀該control的resource、parameter與Region規則。
- **D：** 不正確。Config記錄resource configuration與compliance，CloudTrail記錄API caller與activity；把兩者對調會讓incident evidence與posture history都用錯。
- **E：** 正確。Finding是detective state/evidence；除非另有auto-remediation workflow，它不會自行改resource。修復後還要等待或觸發重新評估確認狀態。

**事實查證：** [Introduction to AWS Security Hub CSPM](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)、[What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)

### 練習題 10｜SAP｜Organization-wide detection operating model

數百accounts與Regions要集中GuardDuty、Amazon Inspector與Security Hub CSPM的管理，但不讓Organizations management account成為SOC工作帳號。哪兩項最重要？（選兩項）

A. 為每個支援服務分別指定delegated administrator並配置組織整合；GuardDuty的detector/protection-plan auto-enable、Inspector resource coverage、CSPM standards/central configuration都逐服務與Region管理
B. 只集中dashboard，不建立severity routing、containment權限或suppression review，因為finding本身已降低風險
C. 建立coverage matrix，至少記錄service、delegated admin、home/aggregation或Region模型、新舊account enrollment、resource eligibility、exceptions與response owner
D. 只在一個Region啟用Security Hub CSPM，便會自動啟用所有Regions的GuardDuty protection plans與Inspector scanning
E. 讓SOC共用management-account root，因為各服務delegated administrator的行為不同

**答案：A、C**

- **A：** 正確。三個服務的organization與Regional行為不完全相同，必須各自配置；「已指定一個delegated admin」不能證明所有plans、resources與Regions都受保護。
- **B：** 不正確。Dashboard只呈現資訊，沒有owner與containment就不會降低risk；suppression若無到期審查還會成為永久blind spot。
- **C：** 正確。Coverage matrix把容易被泛稱「centralize security」遮蔽的差異變成可稽核欄位，並能發現新account、opt-in Region或unsupported resource的空洞。
- **D：** 不正確。CSPM設定不會替GuardDuty或Inspector完成其他Region的服務啟用；各服務都有自己的configuration與coverage。只有單服務的aggregation才按其文件設定。
- **E：** 不正確。Root共享破壞個人attribution並擴大blast radius；差異應用service-specific roles與runbooks管理，不是把日常工作移回最高權限帳號。

**事實查證：** [GuardDuty organization auto-enable preferences](https://docs.aws.amazon.com/guardduty/latest/ug/set-guardduty-auto-enable-preferences.html)、[Scanning resources with Amazon Inspector](https://docs.aws.amazon.com/inspector/latest/user/scanning-resources.html)、[Integrating Security Hub CSPM with AWS Organizations](https://docs.aws.amazon.com/securityhub/latest/userguide/designate-orgs-admin-account.html)、[AWS Organizations terminology and concepts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started_concepts.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「GuardDuty找可疑活動，Inspector掃workload漏洞，Macie找S3敏感資料，Dete…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「組織需要區分威脅偵測、漏洞、敏感資料與調查聚合。」，所以「GuardDuty找可疑活動，Inspector掃workload漏洞，Macie找S3敏感資料，Detective協助調查，Security Hub彙整。」能直接滿足它；若constraint改成「Config/Audit Manager偏合規與設定證據，CloudTrail提供API活動原始紀錄。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「GuardDuty找可疑活動，Inspector掃workload漏洞，Macie找S3敏感資料，Detective協助調查，Security Hub彙整。」。替代方案「Config/Audit Manager偏合規與設定證據，CloudTrail提供API活動原始紀錄。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「看到Security Hub finding便誤以為它自行掃描所有資源，或沒有owner與response workflow。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「組織需要區分威脅偵測、漏洞、敏感資料與調查聚合。」，排除會導致「看到Security Hub finding便誤以為它自行掃描所有資源，或沒有owner與response workflow。」的選項，再選「GuardDuty找可疑活動，Inspector掃workload漏洞，Macie找S3敏感資料，Detective協助調查，Security Hub彙整。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAP-1.2 Prescribe security controls；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「GuardDuty找可疑活動，Inspector掃workload漏洞，Macie找S3敏感資料，Detective協助調查，Security Hub彙整。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「detection requires signal ownership and response paths」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 31 章　資料分類、備份、Retention 與 Compliance

不同資料有不同機密性、保存期限、刪除義務與復原要求。

## 跟著一次授權決定走：先從故事開始

故事從一個看似簡單的需求開始：勒索軟體風險下，財務資料需七年WORM保存且可跨帳號恢復。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：不同資料有不同機密性、保存期限、刪除義務與復原要求。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把身份系統想成辦公大樓：登入證明你是誰，門禁規則才決定你能進哪一間房。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS Backup會是本章的主要角色，Amazon S3 Object Lock則幫我們看清邊界。方向是「先分類，再套encryption、access、lifecycle、Object Lock、Backup Vault Lock與稽核證據。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：勒索軟體風險下，財務資料需七年WORM保存且可跨帳號恢復。

人或workload提出request
          │ ① 取得短期身份／credential
          │ ② 合併identity、resource與organization規則
          ▼
[AWS Backup] ── Allow / Deny ──> protected resource
          │ 以policy集中排程、保存與複製多種AWS resource backups。
          │ ③ 需要時再通過network與KMS邊界
          ▼
[protected data／operation]
證據面：CloudTrail／finding／Config記錄誰在何時做了什麼
本章其他角色：
  · Amazon S3 Object Lock：在versioned S3 bucket上提供WORM retention與legal hold。
  · AWS Artifact：下載AWS合規報告與管理特定agreements。
  · AWS Audit Manager：持續收集AWS使用證據並對照control framework組織assessment。

失敗時先找：只確認備份job成功，從未驗證restore、權限、KMS key與跨帳號隔離。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一次授權決定走」。先不要急著問AWS Backup有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Backup和Amazon S3 Object Lock並不是兩個任意的產品名稱。前者適合本章，是因為「先分類，再套encryption、access、lifecycle、Object Lock、Backup Vault Lock與稽核證據。」直接回應了眼前的問題；後者描述的「Replication改善副本可用性但會複製邏輯刪除；backup提供時間點復原但需測試。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只確認備份job成功，從未驗證restore、權限、KMS key與跨帳號隔離。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「a backup is useful only after a verified restore」。更白話地說：分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 |
| Amazon S3 Object Lock | 在versioned S3 bucket上提供WORM retention與legal hold。 | Retention附在object version；governance可由具特權者繞過，compliance期限內連root也不能刪除。 |
| AWS Artifact | 下載AWS合規報告與管理特定agreements。 | 提供AWS側SOC、ISO、PCI等auditor reports；不掃描customer resources。 |
| AWS Audit Manager | 持續收集AWS使用證據並對照control framework組織assessment。 | Framework controls映射Config、CloudTrail、Security Hub等evidence sources，產生assessment reports。 |

## 把全圖套進一個具體案例

**場景：** 勒索軟體風險下，財務資料需七年WORM保存且可跨帳號恢復。

1. 故事的起點：勒索軟體風險下，財務資料需七年WORM保存且可跨帳號恢復。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Backup負責「以policy集中排程、保存與複製多種AWS resource backups。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon S3 Object Lock、AWS Artifact、AWS Audit Manager各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只確認備份job成功，從未驗證restore、權限、KMS key與跨帳號隔離。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Backup

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：不同資料有不同機密性、保存期限、刪除義務與復原要求。
- **具體例子／邊界：** 在「勒索軟體風險下，財務資料需七年WORM保存且可跨帳號恢復。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon S3 Object Lock

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Replication改善副本可用性但會複製邏輯刪除；backup提供時間點復原但需測試。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只確認備份job成功，從未驗證restore、權限、KMS key與跨帳號隔離。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：a backup is useful only after a verified restore。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### retain

因法規、dependency、時程或business理由暫時保留原環境，並記錄重新評估日期。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RTO

Recovery Time Objective，災難後business service必須在多久內恢復。

## 回到 AWS：Components、功用與責任邊界

### AWS Backup

- **功用：** 以policy集中排程、保存與複製多種AWS resource backups。
- **底層機制：** Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
- **關鍵設定：** backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- **選擇時機：** 多服務一致backup governance、cross-account vault與合規reporting。
- **替換時機：** database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。

### Amazon S3 Object Lock

- **功用：** 在versioned S3 bucket上提供WORM retention與legal hold。
- **底層機制：** Retention附在object version；governance可由具特權者繞過，compliance期限內連root也不能刪除。
- **關鍵設定：** Object Lock enablement、versioning、governance/compliance mode、retain-until date、legal hold與bypass permission。
- **選擇時機：** 法規保存、勒索軟體保護與不可變audit records。
- **替換時機：** 一般誤刪復原只需versioning/backup；compliance mode一旦設定錯誤可能無法撤回。

### AWS Artifact

- **功用：** 下載AWS合規報告與管理特定agreements。
- **底層機制：** 提供AWS側SOC、ISO、PCI等auditor reports；不掃描customer resources。
- **關鍵設定：** report type、agreement、account/organization acceptance與IAM access。
- **選擇時機：** 稽核需要AWS基礎設施證據或合約文件。
- **替換時機：** customer controls與resource evidence使用Audit Manager、Config、CloudTrail。

### AWS Audit Manager

- **功用：** 持續收集AWS使用證據並對照control framework組織assessment。
- **底層機制：** Framework controls映射Config、CloudTrail、Security Hub等evidence sources，產生assessment reports。
- **關鍵設定：** framework、assessment scope、evidence sources、delegation、report destination與organization integration。
- **選擇時機：** PCI/HIPAA/SOC等customer-side audit preparation與evidence automation。
- **替換時機：** 它不自動讓resource合規；preventive controls仍需IAM/SCP/Config remediation。

## 考前與實作時再查：設定操作手冊

### AWS Backup：逐項設定說明

#### `backup plan/rule`

- **控制什麼：** `backup plan/rule`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `schedule`

- **控制什麼：** `schedule`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Backup的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `lifecycle`

- **控制什麼：** `lifecycle`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `vault/KMS`

- **控制什麼：** `vault/KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `resource assignment`

- **控制什麼：** `resource assignment`指定AWS Backup讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `copy action`

- **控制什麼：** `copy action`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `restore testing`

- **控制什麼：** `restore testing`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「多服務一致backup governance、cross-account vault與合規reporting。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Backup設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

### Amazon S3 Object Lock：逐項設定說明

#### `Object Lock enablement`

- **控制什麼：** `Object Lock enablement`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3 Object Lock設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `versioning`

- **控制什麼：** `versioning`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「法規保存、勒索軟體保護與不可變audit records。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3 Object Lock依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `governance/compliance mode`

- **控制什麼：** `governance/compliance mode`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3 Object Lock設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `retain-until date`

- **控制什麼：** `retain-until date`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3 Object Lock設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `legal hold`

- **控制什麼：** `legal hold`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3 Object Lock設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `bypass permission`

- **控制什麼：** `bypass permission`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「法規保存、勒索軟體保護與不可變audit records。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3 Object Lock明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

### AWS Artifact：逐項設定說明

#### `report type`

- **控制什麼：** `report type`定義AWS Artifact用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `agreement`

- **控制什麼：** `agreement`指定誰能使用、管理或接受AWS Artifact的resource/contract，是delegated ownership與authorization的一部分。
- **何時需要：** 跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。
- **怎麼設定／驗證：** 使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。
- **常見錯法：** 信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。

#### `account/organization acceptance`

- **控制什麼：** `account/organization acceptance`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「稽核需要AWS基礎設施證據或合約文件。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Artifact建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `IAM access`

- **控制什麼：** `IAM access`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「稽核需要AWS基礎設施證據或合約文件。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Artifact明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

### AWS Audit Manager：逐項設定說明

#### `framework`

- **控制什麼：** `framework`定義AWS Audit Manager管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `assessment scope`

- **控制什麼：** `assessment scope`定義AWS Audit Manager用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `evidence sources`

- **控制什麼：** `evidence sources`指定AWS Audit Manager讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `delegation`

- **控制什麼：** `delegation`指定誰能使用、管理或接受AWS Audit Manager的resource/contract，是delegated ownership與authorization的一部分。
- **何時需要：** 跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。
- **怎麼設定／驗證：** 使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。
- **常見錯法：** 信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。

#### `report destination`

- **控制什麼：** `report destination`指定AWS Audit Manager讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `organization integration`

- **控制什麼：** `organization integration`把AWS Audit Manager與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

## 讀到這裡，請用自己的話說一次

1. AWS Backup的責任：以policy集中排程、保存與複製多種AWS resource backups。
2. 底層機制：Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。
3. 第一個要看的設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
4. 選擇邏輯：先分類，再套encryption、access、lifecycle、Object Lock、Backup Vault Lock與稽核證據。
5. 不要混淆：Amazon S3 Object Lock的責任是「在versioned S3 bucket上提供WORM retention與legal hold。」；它不會自動取代AWS Backup。
6. 替換訊號：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
7. 最常見錯法：只確認備份job成功，從未驗證restore、權限、KMS key與跨帳號隔離。
8. 可移植原則：a backup is useful only after a verified restore。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Backup | 以policy集中排程、保存與複製多種AWS resource backups。 | Backup plan選resources並寫recovery points到vault；copy rules可跨account/Region。 | 多服務一致backup governance、cross-account vault與合規reporting。 | database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。 |
| Amazon S3 Object Lock | 在versioned S3 bucket上提供WORM retention與legal hold。 | Retention附在object version；governance可由具特權者繞過，compliance期限內連root也不能刪除。 | 法規保存、勒索軟體保護與不可變audit records。 | 一般誤刪復原只需versioning/backup；compliance mode一旦設定錯誤可能無法撤回。 |
| AWS Artifact | 下載AWS合規報告與管理特定agreements。 | 提供AWS側SOC、ISO、PCI等auditor reports；不掃描customer resources。 | 稽核需要AWS基礎設施證據或合約文件。 | customer controls與resource evidence使用Audit Manager、Config、CloudTrail。 |
| AWS Audit Manager | 持續收集AWS使用證據並對照control framework組織assessment。 | Framework controls映射Config、CloudTrail、Security Hub等evidence sources，產生assessment reports。 | PCI/HIPAA/SOC等customer-side audit preparation與evidence automation。 | 它不自動讓resource合規；preventive controls仍需IAM/SCP/Config remediation。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Replication改善副本可用性但會複製邏輯刪除；backup提供時間點復原但需測試。 | 只有當題目條件明確改變時才可能合理。 | 只確認備份job成功，從未驗證restore、權限、KMS key與跨帳號隔離。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Replication改善副本可用性但會複製邏輯刪除；backup提供時間點復原但需測試。」之間做選擇。
- 認得常考設定：backup plan/rule、schedule、lifecycle、vault/KMS、resource assignment、copy action與restore testing。
- 對應官方tasks：SAA-1.3 Determine appropriate data security controls；SAA-4.1 Design cost-optimized storage solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：database-native point-in-time/replication仍有價值；backup成功不等於restore符合RTO。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.2 Design a solution to ensure business continuity；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security；SAP-4.1 Select existing workloads and processes for potential migration。

## 本章 10 題考題

### 練習題 1｜SAA｜Classify data before controls

系統含公開圖片、PII、payment records與可重建 cache。選 storage/security前應先做什麼？

A. 先為公開圖片、PII、payment records與cache分別定義confidentiality、integrity、availability、owner、residency、RPO/RTO、retention與deletion，再映射access、encryption、backup與lifecycle
B. 先統一使用同一customer-managed KMS key；完成加密後即不需資料分類或owner
C. 全部永久保留在immutable storage，以免任何資料被誤刪
D. 先選每GB最低的storage class，之後再依實際事故補上retention與recovery

**答案：A**

- **A：** 正確。分類把業務與法規義務轉成可驗證constraints；例如cache可重建而PII有刪除義務，兩者不應共享同一retention與recovery設計。
- **B：** 不正確。Encryption只處理部分confidentiality，不能回答刪除、residency、availability與ownership。分類完成後才知道是否能共用key與誰可管理。
- **C：** 不正確。永久保存可能違反data minimization與法定刪除，且增加成本。只有明確WORM retention要求的record classes才應不可變保存。
- **D：** 不正確。最低單價可能帶來retrieval latency、minimum duration與不可接受的RTO；成本優化必須在已知資料義務後進行。

**事實查證：** [SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)、[SAP-C02 Domain 1: Design Solutions for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)

### 練習題 2｜SAA｜Backup versus replication

App要承受 AZ failure，且 ransomware後能回到昨天未污染狀態。哪個組合正確？

A. 以 HA/replication處理可用性，另以隔離、版本化 recovery points處理歷史復原，並測試兩者
B. 同步 replica本身就是 immutable backup
C. 只有 backup即可 zero-RTO failover
D. Glacier lifecycle等同 live replica

**答案：A**

- **A：** 正確。Availability與 point-in-time recovery是不同失敗模型。 Availability、historical recovery、immutability與evidence各處理不同failure mode；題幹要求哪一層就必須實際驗證哪一層。
- **B：** 不正確。Replica可能同步 corruption/deletion。 Availability、historical recovery、immutability與evidence各處理不同failure mode；題幹要求哪一層就必須實際驗證哪一層。
- **C：** 不正確。Restore需要時間與 capacity。 Availability、historical recovery、immutability與evidence各處理不同failure mode；題幹要求哪一層就必須實際驗證哪一層。
- **D：** 不正確。Archive是成本/retention tier，不是 serving replica。

**事實查證：** [What is AWS Backup?](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)、[Restore testing with AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

### 練習題 3｜SAA｜AWS Backup plan and assignment

Prod-tagged resources需 daily/weekly retention與 cross-Region copies。AWS Backup應如何配置？

A. 為每個service寫S3 Lifecycle rule，讓所有非S3 resources自動成為backup recovery points
B. 每週複製一張golden AMI，即視為涵蓋databases、EFS與application state
C. 只用AWS Config configuration snapshots，因為它們可直接還原database與volume data
D. 建立AWS Backup plan rules定義schedule、vault、lifecycle與cross-Region copy actions，再用tags或resource selections指派prod resources並逐服務確認feature/Region支援

**答案：D**

- **A：** 不正確。S3 Lifecycle只管理S3 objects，不能備份RDS、EBS、DynamoDB等服務。AWS Backup使用各服務支援的backup API。
- **B：** 不正確。AMI可保護部分EC2映像與volumes，卻不涵蓋外部database、shared filesystem與所有runtime state。只有純immutable/stateless workload才接近此模式。
- **C：** 不正確。Config記錄configuration history，不包含可還原的database rows或EBS blocks。它可協助重建設定，但不是data backup。
- **D：** 正確。Plan描述保護policy，assignment選擇resources；copy/lifecycle與continuous backup依resource type而異。還需監控job與實際restore。

**事實查證：** [What is AWS Backup?](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)

### 練習題 4｜SAP｜Cross-account recovery isolation

Workload account遭ransomware時，其administrators不得刪除隔離的recovery points；公司要能在專用backup account還原。哪個架構最完整？

A. 看到cross-account copy job為COMPLETED，即視為network、restore role、KMS與application dependencies都已驗證
B. 在同一Organization內把支援resource copies送到專用backup account的destination vault；配置source/destination vault access、customer-managed KMS keys與least-privilege restore role，隔離admins並定期實際restore驗證依賴
C. 在同一workload account建立另一vault，仍讓原administrators擁有backup:DeleteRecoveryPoint與KMS管理權限
D. 只附Allow SCP給backup account，假設它會授予destination vault與KMS decrypt權限

**答案：B**

- **A：** 不正確。Copy成功只證明recovery point到達destination；restore仍可能因key、IAM role、subnet、quota或application dependency失敗。必須定期演練。
- **B：** 正確。AWS Backup cross-account copy要求支援的Organizations環境與destination vault policy；加上獨立KMS、restore role與測試，才同時處理隔離及最後一哩recoverability。
- **C：** 不正確。同一admin與KMS boundary可能在credential compromise時同時被攻陷，無法滿足隔離。只有威脅模型不包含account admin時才可能足夠。
- **D：** 不正確。SCP是permission ceiling，不會創造vault policy、identity Allow或KMS key policy。Cross-account copy需要Organizations與兩端resource/identity設定。

**事實查證：** [Creating cross-account backup copies](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)、[Restoring a backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-a-backup.html)、[Key policies in AWS KMS](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)

### 練習題 5｜SAP｜Backup Vault Lock modes

Recovery points不得提前刪除或縮短 retention；正式鎖定後連 root/AWS也不可改 lock。應使用？

A. 使用governance-style可變更設定，卻宣稱正式鎖定後任何人都不能修改
B. 只以vault access policy拒絕DeleteRecoveryPoint，並允許同一admin隨時修改該policy
C. 把S3 Object Lock設定套到vault ARN，假設它會自動保護所有AWS Backup resource types
D. 在測試vault先設定min/max retention與grace time，驗證後使用Backup Vault Lock compliance mode；grace結束後連高權限principals也不能刪除或縮短受保護recovery points

**答案：D**

- **A：** 不正確。若仍可由授權者變更，就不符合題幹「正式鎖定後不可改」；應精確區分可調整的governance與compliance語意。
- **B：** 不正確。可由同一高權限者修改的policy不是不可變控制；它適合least-privilege，不能單獨抵抗admin compromise。
- **C：** 不正確。S3 Object Lock與Backup Vault Lock作用於不同resource model，不能把bucket設定附到vault。S3 backups本身也需依AWS Backup支援方式處理。
- **D：** 正確。Compliance mode在grace期間可驗證，鎖定後提供不可逆WORM語意；錯誤retention也可能造成長期成本，因此必須先測試。

**事實查證：** [AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)

### 練習題 6｜SAA｜S3 Object Lock governance versus compliance

法規 records需七年不可繞過；另一 bucket rollout期允許極少數 admins覆寫。如何選？

A. Governance永不可 bypass
B. Bucket-policy Deny與 Object Lock完全相同
C. Records用 compliance mode；rollout bucket用 governance mode並嚴控 s3:BypassGovernanceRetention；Object Lock作用於 versioned object versions
D. 兩者都 legal hold七年

**答案：C**

- **A：** 不正確。Governance設計上可由特殊 permission bypass。 Availability、historical recovery、immutability與evidence各處理不同failure mode；題幹要求哪一層就必須實際驗證哪一層。
- **B：** 不正確。Policy可被修改；Object Lock提供 WORM semantics。 Availability、historical recovery、immutability與evidence各處理不同failure mode；題幹要求哪一層就必須實際驗證哪一層。
- **C：** 正確。Compliance不可縮短/刪除；governance允許具特權且明示 header的 bypass，適合測試。
- **D：** 不正確。Legal hold無固定到期時間。 Availability、historical recovery、immutability與evidence各處理不同failure mode；題幹要求哪一層就必須實際驗證哪一層。

**事實查證：** [Locking objects with S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)

### 練習題 7｜SAA｜Retention versus legal hold

Object version七年 retention到期，但 litigation要求繼續保存直到律師解除。應使用什麼？

A. 新增delete marker，假設它會移除受保護version並滿足legal hold
B. 建立Lifecycle expiration rule，讓七年到期後自動刪除，即使hold仍存在
C. 對該object version加legal hold；它沒有固定到期日，與time-based retention獨立，直到具權限者依法律事件解除
D. 把retention date無限延長且不記錄litigation case或解除條件

**答案：C**

- **A：** 不正確。Simple delete可能建立delete marker，但受保護的舊version仍存在且不可刪除。Legal hold必須直接套用到該version。
- **B：** 不正確。Lifecycle不能繞過仍有效的legal hold或Object Lock retention；題幹要求繼續保存，expiry policy與需求相反。
- **C：** 正確。Retention按日期，legal hold按事件；同一version可同時受兩者保護，任一仍生效就不能刪除。解除hold應有法律授權與audit。
- **D：** 不正確。盲目延長retention可能違反日後刪除義務，也失去事件型解除流程。只有政策本身要求新的固定retention date時才這樣做。

**事實查證：** [Locking objects with S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)

### 練習題 8｜SAP｜Automated restore testing

Dashboard顯示 backups全部成功，但 auditor要求 recoverability evidence。最佳做法？

A. 只比較recovery point checksum，不建立任何subnet、role、key或application dependency
B. 建立AWS Backup restore testing plan，依selection選代表性recovery points，使用least-privilege restore role還原，執行data/application validation、量測restore time並清理測試resource與保存結果
C. 只看replication lag，將低lag視為歷史backup與restore已驗證
D. 只檢查backup job狀態為COMPLETED，因為寫入成功必然代表application可啟動

**答案：B**

- **A：** 不正確。Checksum只能驗證部分資料完整性，不會證明依賴與application transaction可用。它可作validation的一環，不能單獨滿足RTO。
- **B：** 正確。Restore testing把「有備份」轉成可執行的recoverability evidence；仍要自訂application validation，並治理測試resource成本與資料曝露。
- **C：** 不正確。Replication處理availability且可能同步corruption；它不是隔離歷史recovery point，也沒有執行restore workflow。
- **D：** 不正確。Backup成功可能仍缺restore role、KMS、network、quota或相容版本；只有實際restore才能驗證最後一哩。

**事實查證：** [Restore testing with AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

### 練習題 9｜SAP · CURRENT-SCOPE｜Evidence services and Audit Manager 2026 scope

一家在2026-09新成為AWS客戶的公司需要AWS SOC報告、resource configuration history、API actor history與可匯入外部GRC的客戶控制evidence。哪兩項設計正確？（選兩項）

A. 使用AWS Config保存resource configuration/compliance、CloudTrail保存console/CLI/API caller activity，將所需evidence輸出到受控repository或外部GRC workflow
B. 把Audit Manager當成preventive enforcement，讓它在API執行前阻擋任何不合規變更
C. AWS Artifact取得AWS compliance reports/agreements；它證明AWS側文件，但不掃描客戶resources
D. 只看Security Hub CSPM dashboard即可取代所有CloudTrail actor history與AWS SOC報告
E. 新客戶直接啟用AWS Audit Manager，因為2026-04-30後所有新客戶仍可onboard且沒有服務限制

**答案：A、C**

- **A：** 正確。Config回答resource如何配置與評估，CloudTrail回答誰何時呼叫API；再以retention、chain of custody與GRC mapping形成客戶控制evidence。
- **B：** 不正確。Audit Manager即使對既有客戶可用，也主要組織assessment evidence，不是API authorization guardrail。Preventive blocking需IAM、SCP、RCP或service control。
- **C：** 正確。Artifact提供AWS責任範圍的audit reports與agreements，不代表客戶configuration已合規；shared responsibility下仍需自有evidence。
- **D：** 不正確。CSPM finding只覆蓋特定controls，不包含完整API actor history，也不能提供AWS SOC報告。它可作evidence source之一但不是全部。
- **E：** 不正確。AWS官方公告指出Audit Manager自2026-04-30起不再接受新客戶，既有客戶可繼續使用。新客戶不能把它當成必然可採用的當代架構。

**事實查證：** [What is AWS Artifact?](https://docs.aws.amazon.com/artifact/latest/ug/what-is-aws-artifact.html)、[What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)、[CloudTrail record contents](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html)、[AWS service availability updates](https://aws.amazon.com/about-aws/whats-new/2026/03/aws-service-availability/)

### 練習題 10｜SAP｜Retention-aware migration

On-prem archive移到AWS；record classes有不同刪除義務、legal holds、90天可搜尋window與七年retention。哪兩項是vendor-neutral且可驗證的migration requirements？（選兩項）

A. 把所有bytes永久放入同一immutable tier，不保留class、owner或deletion metadata
B. 以獨立evidence repository記錄hash/manifest、migration events與approvals，實測retrieval、hold、到期刪除、exception與restore；Audit Manager僅可作符合資格既有客戶的可選evidence organizer
C. Replication成功即可證明WORM、authorized deletion與所有compliance evidence都正確
D. 搬移前inventory/classify並保存record class、retention date、hold、owner與chain-of-custody metadata，再映射到lifecycle、Object Lock、backup與access controls
E. 先搬資料，遺失的retention date在稽核時再依object last-modified推測

**答案：B、D**

- **A：** 不正確。永久保存所有資料可能違反minimization與法定刪除，且沒有metadata就無法證明每類record應何時處理。只有明確永久retention類別才可如此。
- **B：** 正確。Requirement不綁單一AWS產品：manifest、retention metadata、實際behavior tests與受控evidence repository才是核心。既有Audit Manager客戶可用它整理evidence，但新客戶不得假設可onboard。
- **C：** 不正確。Replication可改善availability，卻可能同步刪除或corruption，也不提供WORM與chain-of-custody。它只是架構元件，不是compliance結論。
- **D：** 正確。Metadata是policy semantics，不只是附註；它決定何時可刪、誰能解除hold、使用哪個storage tier與recovery要求。搬bytes前必須先保全。
- **E：** 不正確。Last-modified不等於record creation、legal trigger或retention start，事後推測會破壞policy continuity與auditor可驗證性。

**事實查證：** [Locking objects with S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)、[Restore testing with AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)、[AWS service availability updates](https://aws.amazon.com/about-aws/whats-new/2026/03/aws-service-availability/)、[SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「先分類，再套encryption、access、lifecycle、Object Lock、Backup …」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「不同資料有不同機密性、保存期限、刪除義務與復原要求。」，所以「先分類，再套encryption、access、lifecycle、Object Lock、Backup Vault Lock與稽核證據。」能直接滿足它；若constraint改成「Replication改善副本可用性但會複製邏輯刪除；backup提供時間點復原但需測試。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「先分類，再套encryption、access、lifecycle、Object Lock、Backup Vault Lock與稽核證據。」。替代方案「Replication改善副本可用性但會複製邏輯刪除；backup提供時間點復原但需測試。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只確認備份job成功，從未驗證restore、權限、KMS key與跨帳號隔離。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「不同資料有不同機密性、保存期限、刪除義務與復原要求。」，排除會導致「只確認備份job成功，從未驗證restore、權限、KMS key與跨帳號隔離。」的選項，再選「先分類，再套encryption、access、lifecycle、Object Lock、Backup Vault Lock與稽核證據。」。本章對應的代表task包括：SAA-1.3 Determine appropriate data security controls；SAA-4.1 Design cost-optimized storage solutions；SAP-1.2 Prescribe security controls；SAP-2.2 Design a solution to ensure business continuity。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「先分類，再套encryption、access、lifecycle、Object Lock、Backup Vault Lock與稽核證據。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「a backup is useful only after a verified restore」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
