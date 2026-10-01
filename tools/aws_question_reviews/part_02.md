# R02 獨立實質審查：part_02（第 21–31 章）

審查日期：2026-10-01
Reviewer：R02（非本題庫作者）
範圍：`tools/aws_question_banks/part_02.json` 全部 110 題

## 結論摘要

- 題數與 intent：11 章 × 每章 10 題；每章 intent 1–10 各一次，結構完整。
- 題型：88 題單選、22 題複選；每題的答案 index、選項數與逐選項解析數量一致。
- 實質答案：72 題的核心答案集合可保留；38 題有事實、scope、來源精度、自足性或舊題重疊問題。
- 重複檢查：part_02 內沒有相同或 0.65 以上的近似題幹；與目前其餘 1,050 題比較也沒有 0.80 以上近似題幹。
- 舊題比較：`ch022-q01`、`ch022-q04` 與舊版 chapter 22 fallback 題的情境、推理與答案形狀高度近似，沒有完成「取代舊五題」。
- 第三方措辭：把 110 題的 prompt、choices、explanations 與 7 個 Jayendra 頁面全文比較，未發現連續 8 個以上實質 token 的相同片段，沒有直接照抄證據。
- 來源 provenance：110 題全部引用至少一個 Jayendra 頁面作 inspiration；這些頁面的 practice section 明載題目是「collected from Internet」，並警告題目可能未隨 AWS 更新。來源鏈不能證明題目不是 recalled/live-exam material，與本題庫的來源契約不相容。
- 答案位置：雖通過「同一位置不超過 4 次」的弱檢查，但幾乎每章都把 q01–q08 排成 A/B/C/D/A/B/C/D，q09–q10 再使用固定 pair。題號可預測答案，必須重排。
- 解析品質：54 題、72 個選項解析短於專案 checker 的 32 字最低要求；其中多數只說服務不相關，沒有交代錯在哪個 constraint、何時會翻成正解。
- Current-service scope：2026 年的 AWS Security Hub 與 Security Hub CSPM 已是不同產品／文件語意；題庫仍把 ASFF、controls、automation rules 和新 Security Hub 混稱。AWS Audit Manager 自 2026-05-20 起不再提供給新客戶，題庫沒有 scope note。RCP 是 current enrichment，不應無標示地當成 SAP-C02 baseline。

整體判定為 **REVISE**。在修訂 provenance、答案位置與解析之前，即使核心答案正確也不能發布。

## 110 題逐題覆核矩陣

下表只表示「核心答案集合與主要技術判斷」是否可保留；所有題目仍受後文的全域 provenance 與答案位置 blocker 影響。

| 章 | 核心答案可保留 | 必須實質修訂 |
|---|---|---|
| 21 | `ch021-q04`–`ch021-q08` | `ch021-q01`–`ch021-q03`, `ch021-q09`, `ch021-q10` |
| 22 | `ch022-q02`, `ch022-q03`, `ch022-q05`–`ch022-q07`, `ch022-q09`, `ch022-q10` | `ch022-q01`, `ch022-q04`, `ch022-q08` |
| 23 | `ch023-q01`–`ch023-q07`, `ch023-q09` | `ch023-q08`, `ch023-q10` |
| 24 | `ch024-q01`, `ch024-q02`, `ch024-q05`–`ch024-q07` | `ch024-q03`, `ch024-q04`, `ch024-q08`–`ch024-q10` |
| 25 | `ch025-q01`, `ch025-q02`, `ch025-q04`–`ch025-q06`, `ch025-q08` | `ch025-q03`, `ch025-q07`, `ch025-q09`, `ch025-q10` |
| 26 | `ch026-q01`–`ch026-q04`, `ch026-q06`, `ch026-q07`, `ch026-q09` | `ch026-q05`, `ch026-q08`, `ch026-q10` |
| 27 | `ch027-q01`–`ch027-q10` | 無核心事實錯誤；仍須處理全域 blockers |
| 28 | `ch028-q01`, `ch028-q02`, `ch028-q04`, `ch028-q05`, `ch028-q10` | `ch028-q03`, `ch028-q06`–`ch028-q09` |
| 29 | `ch029-q01`, `ch029-q02`, `ch029-q04`–`ch029-q09` | `ch029-q03`, `ch029-q10` |
| 30 | `ch030-q04`–`ch030-q07` | `ch030-q01`–`ch030-q03`, `ch030-q08`–`ch030-q10` |
| 31 | `ch031-q01`–`ch031-q03`, `ch031-q05`–`ch031-q08` | `ch031-q04`, `ch031-q09`, `ch031-q10` |

## 全域 release blockers

### 1. 全部 110 題的 community provenance 不符合契約

受影響範圍：`ch021-q01`–`ch031-q10`。

每題都有 `inspiration_ids`，且只指向以下七個 Jayendra 頁面：

- `jayendra-iam`
- `jayendra-identity-center`
- `jayendra-organizations`
- `jayendra-control-tower`
- `jayendra-kms`
- `jayendra-security-services`
- `jayendra-multi-account`

其中 IAM、Identity Center、Organizations、Control Tower、KMS 頁面明載 practice questions 是從 Internet 蒐集，並提醒舊考題可能沒有隨服務更新；其餘頁面也包含未交代原始作者或取得方式的 practice-question section。這不代表目前題目已被證明是 dump，但代表 provenance 無法通過「不使用 recalled/live-exam items 或來源不明題庫」的契約。

修訂動作：

1. 從全部 110 題移除這七個 `inspiration_ids`，或換成可證明為作者原創、沒有宣稱 actual/recalled questions、沒有來源不明題庫區段的教學來源。
2. Jayendra 的正文仍可作人工 topic inventory，但不得作為單題 question provenance；事實一律由精確的 AWS 官方頁面支持。
3. 保留「沒有 8-token 以上照抄」的檢查結果，但不要把「沒有找到照抄」誤寫成「來源已安全」。

### 2. 全部章節的答案位置可由題號預測

受影響範圍：`ch021-q01`–`ch031-q10`。

典型排列是：

```text
q01=A, q02=B, q03=C, q04=D,
q05=A, q06=B, q07=C, q08=D,
q09=A+E 或 A+D, q10=B+E
```

第 22、24、26 章只有少量偏移，仍看得出同一生成模板。這會讓學生不理解內容也能猜答案，且不符合正式模擬題的答案分布。

修訂動作：

1. 每章獨立重排 choices，answers 與 explanations 必須同步 remap。
2. 不只檢查每個字母總數，還要禁止跨章重複的 q-index pattern。
3. 重排後重新檢查 multi-answer 組合；同一章不應反覆出現同一 pair。

### 3. 54 題的逐選項解析未通過專案 checker

下列 choice explanation 少於 32 字；括號是需要擴寫的選項：

```text
ch024-q04(C)
ch024-q10(C,D)
ch025-q02(C)
ch025-q04(A)
ch025-q07(D)
ch025-q08(B)
ch025-q09(B)
ch026-q02(C)
ch026-q03(B)
ch026-q04(B)
ch026-q06(C)
ch026-q07(A)
ch026-q09(D)
ch026-q10(B)
ch027-q02(A,C)
ch027-q03(A)
ch027-q04(B)
ch027-q05(B,C)
ch027-q08(A,C)
ch027-q09(C)
ch027-q10(D,E)
ch028-q02(A)
ch028-q03(B)
ch028-q04(A,C)
ch028-q05(C)
ch028-q06(A)
ch028-q08(B)
ch028-q09(B,C)
ch028-q10(A)
ch029-q01(B,D)
ch029-q02(C)
ch029-q03(A,D)
ch029-q04(B)
ch029-q06(A,D)
ch029-q07(A)
ch029-q08(C)
ch029-q09(B,C,D)
ch029-q10(E)
ch030-q01(C)
ch030-q02(A)
ch030-q04(B)
ch030-q05(C)
ch030-q06(D)
ch030-q07(A)
ch030-q09(B)
ch030-q10(D)
ch031-q01(D)
ch031-q02(C)
ch031-q03(A,D)
ch031-q04(A,B)
ch031-q06(A)
ch031-q07(A,B)
ch031-q08(B,C)
ch031-q09(B,D,E)
```

修訂動作：每個解析至少說明一個具體 violated constraint，或明確說明哪種題幹改動會讓該選項成為正解。不要只補同義贅字以通過長度檢查。

### 4. 多題 distractor 過於荒謬

以下題目至少有兩個選項可在不懂本章內容時立即排除，例如用 Route 53 解 SCIM、用 security group 開 IAM port、用 DNS TTL 做 legal hold、用 SCP 解析 HTTP：

`ch024-q02`, `ch024-q03`, `ch024-q10`,
`ch025-q01`, `ch025-q02`, `ch025-q05`–`ch025-q08`,
`ch026-q01`, `ch026-q03`, `ch026-q05`, `ch026-q06`, `ch026-q10`,
`ch027-q04`, `ch027-q05`, `ch027-q08`,
`ch028-q01`, `ch028-q05`, `ch028-q07`–`ch028-q10`,
`ch029-q01`, `ch029-q05`–`ch029-q09`,
`ch030-q10`,
`ch031-q01`, `ch031-q03`, `ch031-q05`, `ch031-q07`, `ch031-q08`。

修訂動作：每題保留至多一個「明顯錯」的 teaching distractor，其餘改成相鄰但違反一個 constraint 的方案，例如：

- 正確服務但錯 Region、錯 policy attachment point、錯 principal 或錯 retention mode；
- 可行但操作成本較高；
- 能處理 availability，卻不能處理 historical recovery；
- 能偵測，卻不能 preventive block；
- 適合單帳號，卻不適合 organization-scale rollout。

## 必須實質修訂的題目與精確動作

### 第 21 章

#### `ch021-q01` — Identity Center 與 S3 權限缺少直接證據

答案 A 可保留，但來源只有 exam domain、IAM role 與 STS temporary credentials，沒有支持 Identity Center account assignments，也沒有支持 `s3:GetObject` object ARN/prefix。

修訂動作：

1. 加入 Identity Center permission-set/account-assignment 官方頁面。
2. 加入 S3 policy actions/resources 官方頁面。
3. 解析明確區分 workforce session、EC2 instance profile、object ARN；不要用一個 broad IAM source 支持三種不同機制。

#### `ch021-q02` — S3 `ListBucket`/`GetObject` 規則來源不精確

答案 B 正確，但 `iam-resource-policies` 沒有直接證明 S3 bucket ARN、object ARN 與 `s3:prefix` 的配對。

修訂動作：加入 S3 policy actions、resource types 與 `ListBucket` prefix condition 的精確官方頁面；解析給出兩段 statement 的最小 JSON 形狀。

#### `ch021-q03` — Instance profile 與 IMDS/SDK 來源不足

答案 C 正確，但一般 IAM roles 首頁不足以支持「instance profile 關聯」與「SDK 從 instance metadata 取得 credentials」的完整 data path。

修訂動作：加入 IAM roles for EC2、instance profile 與 IMDS credential provider 的直接來源；解析補充一台 EC2 一次只能關聯一個 instance profile，但 profile 可包含的 role 數量限制應依現行文件敘述。

#### `ch021-q09` — 沒有 IAM group 的直接來源

答案 A、D 正確，但目前來源沒有直接支持「group 只能包含 users、不能包含 roles、不能巢狀」。

修訂動作：加入 IAM user groups 官方頁面；解析分開說明「重用 managed policy」與「共用同一 principal」不是同一件事。

#### `ch021-q10` — IdP 故障時 role 本身不是登入起點

答案 B、E 的方向合理，但「emergency identities/roles」太模糊。若所有 credential source 都依賴故障中的 IdP，預建 role 仍無法被 assume。

修訂動作：

1. 明示獨立 credential root，例如受嚴格保管的 emergency IAM identity 以 MFA 取得受限 role，或另一個不共用同一故障域的 federation path。
2. 說明 root user 只保留 root-only recovery，不作日常 break-glass admin。
3. 加入 AWS management-account/emergency-access 官方 guidance，不以 CloudTrail 首頁代替。

### 第 22 章

#### `ch022-q01` — 與舊 fallback 題高度近似

新舊題都使用 `s3:GetObject` Allow、`aws:SecureTransport=false` explicit Deny、HTTP 被拒的同一推理形狀。增加 HTTPS 第二步不足以構成新題。

修訂動作：改用不同 policy interaction，例如 VPC endpoint policy、KMS key policy或 session policy，重寫 scenario、全部 choices 與 explanations。

#### `ch022-q04` — 與舊 fallback cross-account 題高度近似

新舊題都是 Account A identity Allow、Account B bucket policy缺失、答案為 cross-account 兩側都須授權。

修訂動作：改考 role trust、resource-based direct grant 與 assumed-role 三條路徑的差異，並要求選出一個具體最小 policy pair；不可只換帳號或 bucket 名稱。

#### `ch022-q08` — SSE-KMS dual authorization 的來源不完整

答案 D 正確，但來源只解釋 KMS key policy與一般 IAM evaluation，沒有直接支持 S3 讀取 SSE-KMS object 所需的 KMS action與 service flow。

修訂動作：加入 S3 SSE-KMS permissions 官方頁面；說明 `kms:Decrypt`、key policy/IAM delegation、cross-account key ARN與 encryption context 的適用條件，不要暗示每次失敗都一定是缺 `kms:Decrypt`。

### 第 23 章

#### `ch023-q08` — OIDC/web identity 來源缺失

答案 D 正確，但 `sts-temp` 與 Identity Center overview 沒有直接支持 mobile OIDC/web-identity trust、issuer/audience/claim validation。

修訂動作：加入 `AssumeRoleWithWebIdentity`、IAM OIDC provider 或 Cognito identity pools 的精確官方頁面；說明 user-pool token 與取得 AWS credentials 不是同一層。

#### `ch023-q10` — 「停用 IdP 後的 session」需要區分與可執行 revocation

目前只說 session 可能持續到到期或套用 controls，對 incident responder 不夠可執行。

修訂動作：

1. 區分 IdP session、Identity Center access-portal session、permission-set role session與一般 STS role session。
2. 加入 IAM revoke role sessions／Identity Center revoke permission-set sessions 的現行官方頁面。
3. 說明 revocation通常以新 Deny 影響既有 sessions，不是由 IdP「刪除 STS credentials」。

### 第 24 章

#### `ch024-q03` — SCIM 事實正確，但來源只到 identity-source overview

修訂動作：加入 Identity Center SCIM automatic provisioning 與 deprovisioning 的直接頁面；解析說明 SAML是 authentication assertion，SCIM是 directory lifecycle，兩者故障與 token rotation不同。

#### `ch024-q04` — 外部 IdP MFA責任需精確來源

答案 D 可保留，但需引用「external identity provider authentication/MFA」的直接頁面。解析應說 phishing-resistant MFA由 authoritative IdP執行，AWS assignment與permission-set session duration不能替代它。

#### `ch024-q08` — 停用使用者不等於所有 session只有等待到期

答案 D 過度籠統。現行 Identity Center提供刪除 active access-portal sessions與撤銷 active permission-set sessions的程序；不同 session類型的效果不同。

修訂動作：重寫答案與解析，列出「阻止新登入、刪除 portal sessions、revoke permission-set sessions、必要時加 explicit Deny」的先後與限制。

#### `ch024-q09` — Delegated administration 來源與可委派範圍不明

方向正確，但目前 sources沒有 delegated administration頁面；「細粒度 IAM permissions」也沒有說哪些 actions/resources可被限制。

修訂動作：加入 Identity Center delegated administration、IAM best-practices delegation與 service-authorization reference；把「限定範圍」具體化為可管理的 account assignments、permission sets或 tags/condition，而非泛稱 fine-grained。

#### `ch024-q10` — Break-glass 路徑仍缺 credential bootstrapping

與 `ch021-q10` 相同，答案 B必須說明 IdP故障時第一組可用 credentials從哪裡來；加入獨立 MFA emergency identity、custodian、activation、recovery與 post-incident reset 的具體流程。

### 第 25 章

#### `ch025-q03` — Organization trail 的 native ownership 使答案不唯一

題幹說 workload-account admins 要停止 organization trail。依 CloudTrail現行文件，organization trail只能由 management account或 CloudTrail delegated administrator建立、更新與刪除；member account可見但不能修改。因此在這個精確情境下，不需要靠 member OU的 SCP才阻止 `StopLogging`。

修訂動作二選一：

1. 若要考 organization trail ownership：把 native management/delegated-admin限制設為正解，再用 SCP保護 member-account local trails與相鄰 logging resources作補充。
2. 若要考 SCP：把題幹改成 member admins本來有權修改的 local trail、Config recorder、EventBridge rule或 logging destination，列出要 Deny 的具體 APIs與必要例外。

#### `ch025-q07` — 2026 年的 Security Hub產品名稱含糊

GuardDuty delegated administrator部分正確；「Security Hub」需說清楚是新 AWS Security Hub，還是 Security Hub CSPM。現有 source `what-is-securityhub.html`實際描述 CSPM，不應用來支持新 Security Hub。

修訂動作：依真正要考的產品改名、換來源並列出 enrollment/configuration行為；若考 SAP-C02歷史語意，標明「Security Hub CSPM（舊教材常稱 AWS Security Hub）」。

#### `ch025-q09` — `service-last-access` 沒有來源

答案 C、E 可保留，但 CloudTrail並不等同 IAM service-last-access data。

修訂動作：加入 IAM Organizations service last accessed data或 Access Advisor官方頁面；解析說明歷史沒有呼叫不代表 DR、年度結帳或 maintenance action永遠不需要。

#### `ch025-q10` — RCP 是 current enrichment，不能無標示冒充 SAP-C02 baseline

RCP目前可用且答案 B、E正確；但它是 SAP-C02發表後出現的新 organization policy。題目應把 current production guidance與原始 blueprint baseline分開。

修訂動作：

1. 在 `level`、`tested`或解析標記 `ENRICHMENT-CURRENT`。
2. 明列目前支援的 resource types/services，不能泛化成所有 AWS resources。
3. 解釋 RCP不授權、management account resources也受RCP影響，以及外部 principal仍須先有 resource-policy Allow才談得上 ceiling。

### 第 26 章

#### `ch026-q05` — CloudTrail bucket policy 被寫成模糊的 `SourceArn/SourceAccount`

CloudTrail寫S3的官方 policy有精確的 service principal、`s3:GetBucketAcl`、`s3:PutObject` path、ACL condition與 `aws:SourceArn`模式。現題的「SourceArn/SourceAccount等」會讓讀者以為兩者可任意互換。

修訂動作：改成可檢查的最小 bucket-policy片段，依官方範例使用實際支援的 condition；加入 CloudTrail create-S3-bucket-policy官方頁面。

#### `ch026-q08` — ABAC只有 global-condition來源

答案 A正確，但不同服務支援哪些 resource tags、request tags與 tag-on-create actions並不相同。

修訂動作：加入 IAM ABAC官方頁面與題目中選定服務的 service-authorization reference；明示誰可設定 principal/session tag、誰可改 resource tag，以及 `sts:TagSession`/transitive tags的信任邊界。

#### `ch026-q10` — Security Hub delegated admin語意需更新

與 `ch025-q07`相同，須把 GuardDuty、Security Hub與Security Hub CSPM分開；不要用一個舊 CSPM overview支援所有 current organization integration行為。

### 第 27 章

第 27 章的十個核心答案集合均可保留。修訂代理仍須：

1. 重排固定答案位置。
2. 擴寫前述 checker未通過的解析。
3. 把 `ch027-q04` 的 retire/revoke權限主體說清楚：grantee、retiring principal與key owner的能力不同。
4. 在 `ch027-q10` 說明「CloudHSM direct use」與「KMS custom key store backed by CloudHSM」不是同一整合模式。

### 第 28 章

#### `ch028-q03` — Client caching行為沒有直接來源

答案 C是合理 production pattern，但 rotation overview不足以支持 Secrets Manager client-side caching與refresh-on-auth-failure。

修訂動作：加入 Secrets Manager caching元件／SDK文件；說明 TTL、jitter、auth failure refresh、connection-pool rebuild及舊新credentials重疊窗口。

#### `ch028-q06` — Parameter Store recursive path風險寫得太抽象

答案 B方向正確，但「限制 recursive access」沒有告訴讀者實際錯法。Parameter Store對父path的遞迴讀取有特殊權限風險。

修訂動作：給出具體 ARN/path policy，明說不要把 `/prod`父path的 `GetParametersByPath`授給 Team A後再期待 child explicit Deny可靠隔離；加入 Parameter Store hierarchy權限的直接來源。

#### `ch028-q07` — ACM overview不足以支持 CloudFront Region規則

加入 CloudFront viewer certificate必須在 `us-east-1`以及ALB certificate須在負載平衡器Region的官方頁面。

#### `ch028-q08` — Managed renewal條件需要精確來源

加入 ACM DNS validation與managed renewal頁面；解析列出保留CNAME、certificate仍被合格AWS service使用、domain validation與renewal status，而不是只說「可續期狀態」。

#### `ch028-q09` — Imported certificate lifecycle需要精確來源

加入 ACM import/reimport與expiration monitoring頁面；解析說明重新匯入同一ARN與建立新certificate再替換association的差異。

### 第 29 章

#### `ch029-q03` — 官方 source URL 已退化成 WAF文件首頁

`waf-oversize`目前導向WAF Developer Guide首頁，不能直接支持 integration-specific body limits與 Continue/Match/No match。

修訂動作：換成現行 oversize request components精確頁面，並在解析列出受保護resource type、inspection limit、可調上限與費用影響；WCU不是body-size quota。

#### `ch029-q10` — Origin protection答案太泛，沒有形成可部署方案

答案 B、D方向正確，但 B把 custom header、application validation與 network controls混成一句，沒有說 public ALB是否必須保留。

修訂動作：

1. 明示 constraint：若ALB可改為internal，納入CloudFront VPC origin比較；若必須internet-facing，才要求CloudFront managed prefix list、安全群組、secret header/listener rule等具體組合。
2. 說明 custom header是shared secret，需要rotation且不能取代application authorization。
3. 避免用「支援的 controls」作不可驗證答案。

### 第 30 章

#### `ch030-q01` — GuardDuty來源退化且缺EventBridge response來源

`guardduty`目前只落到User Guide首頁；CloudTrail首頁也不能直接支持特定finding與EventBridge flow。

修訂動作：加入GuardDuty foundational data sources、IAM credential findings與EventBridge findings的精確官方頁面。

#### `ch030-q02` — Protection plans需使用現行名稱與逐項來源

答案 B方向正確，但「S3 data、EKS runtime/audit、malware、database login」混合多個不同plans。Base detector、EKS Protection、Runtime Monitoring、Malware Protection與RDS Protection的啟用方式不應混成一個模糊集合。

修訂動作：列出每個需求對應的current protection plan、resource/Region support、organization auto-enable選項；新增服務或plans只作current enrichment。

#### `ch030-q03` — Trusted IP list並不適用所有GuardDuty findings

題幹只說scanner造成findings，沒有說finding是否由支援trusted-list比對的IP telemetry產生。若是某些runtime、malware或其他finding，加入trusted list不一定會產生題目宣稱的效果。

修訂動作：明示一個受trusted IP list影響的finding/data source，並說明list的Region、數量、CIDR與blind-spot限制；threat list也要使用受支援的indicator格式。

#### `ch030-q08` — 把2026 AWS Security Hub與Security Hub CSPM混為一談

ASFF normalization、standards/controls與既有automation rule語意屬於Security Hub CSPM。2026年的AWS Security Hub以OCSF資料、correlation與exposure為核心。現題用「Security Hub」泛稱舊CSPM行為，會教錯新讀者。

修訂動作二選一：

1. 改題名與答案為「Security Hub CSPM」，保留ASFF/partner findings語意並標註舊教材常用名稱。
2. 若要考current AWS Security Hub，重寫成OCSF、security data sources、correlation與exposure，不能再把ASFF當其主要schema。

#### `ch030-q09` — `NON_COMPLIANT control` 明確屬於Security Hub CSPM

將題幹、tested與sources全部改為Security Hub CSPM；再解釋AWS Config recorder、control finding與preventive control的責任差異。

#### `ch030-q10` — 混合不同服務的 delegated admin與Region模型

GuardDuty、Inspector、Macie、Security Hub及Security Hub CSPM的delegated admin、home/aggregation Region與organization auto-enable並不完全相同。

修訂動作：不可再用一個泛稱選項涵蓋所有服務；改成具體兩至三個服務，列出各自current organization設定，或把正解改成「逐服務建立coverage matrix」並提供可驗證欄位。

### 第 31 章

#### `ch031-q04` — Cross-account AWS Backup只引用overview

答案 D合理，但一般Backup overview與KMS key policy不足以支持cross-account copy、destination vault policy、Organizations prerequisite、KMS key與restore role。

修訂動作：加入AWS Backup cross-account copy與restore的精確官方頁面；說明copy成功不代表destination account一定有完整restore dependencies。

#### `ch031-q09` — Audit Manager在審查日已不對新客戶開放

AWS Audit Manager官方文件註明自2026-05-20起不再提供給新客戶，既有客戶可繼續使用。題目把它寫成任何公司都可新採用的當代答案，缺少重要scope。

修訂動作：

1. 標記為existing-customer／legacy exam knowledge。
2. 若情境是新客戶，改問Artifact、Config、CloudTrail、Security Hub CSPM與外部GRC/evidence workflow的責任分工。
3. 不得把Audit Manager寫成preventive enforcement；現有這點解析正確。

#### `ch031-q10` — Migration題引用Audit Manager但沒有availability策略

答案 B、E不必依賴Audit Manager，可保留其核心；但source與解析應移除「新客戶一定可用Audit Manager」的暗示。

修訂動作：把chain-of-custody、retention metadata、retrieval/deletion test與evidence repository寫成vendor-neutral requirements；Audit Manager只列為符合資格的既有客戶選項並加scope note。

## Source provenance與精度修正清單

| Source或缺口 | 影響題目 | 必要動作 |
|---|---|---|
| 七個 `jayendra-*` inspiration sources含來源不明的Internet-collected practice sections | 全部110題 | 移除單題inspiration引用或換成乾淨、可追溯的原創教學來源。 |
| `waf`, `waf-oversize`目前導向WAF guide首頁 | `ch029-q01`–`ch029-q03`, `ch029-q09` | 換成web ACL evaluation、oversize components與resource-specific limits精確頁面。 |
| `guardduty`目前導向GuardDuty guide首頁 | `ch025-q07`, `ch026-q10`, `ch030-q01`–`ch030-q03`, `ch030-q07`, `ch030-q10` | 依finding、protection plan、trusted list及organization management拆成精確頁面。 |
| `security-hub`其實是Security Hub CSPM overview | `ch025-q07`, `ch026-q10`, `ch030-q05`, `ch030-q08`–`ch030-q10` | 先決定要考Security Hub或Security Hub CSPM，再使用相應current docs。 |
| `acm`只是產品overview | `ch028-q07`–`ch028-q09` | 換成CloudFront Region、DNS validation/managed renewal、import/reimport精確頁面。 |
| `cloudtrail`是整本User Guide入口 | `ch021-q07`, `ch021-q10`, `ch023-q06`, `ch024-q08`–`ch024-q10`, `ch025-q03`, `ch025-q09`, `ch026-q05`, `ch027-q09`, `ch030-q01`, `ch031-q09` | 依API evidence、SourceIdentity、session revocation、organization trail、S3 policy等換成直接頁面。 |
| Identity Center active-session與delegated-admin docs缺失 | `ch024-q08`–`ch024-q10`, `ch023-q10` | 加入delete active user sessions、revoke permission-set sessions與delegated administration頁面。 |
| S3 action/resource、SSE-KMS docs缺失 | `ch021-q01`, `ch021-q02`, `ch022-q08` | 加入S3 policy actions/resources與SSE-KMS permissions頁面。 |
| Audit Manager availability note缺失 | `ch031-q09`, `ch031-q10` | 標明2026-05-20新客戶限制與替代責任分工。 |

## 核對時使用的關鍵AWS官方文件

- [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- [Permissions boundaries for IAM entities](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
- [Revoke IAM role temporary security credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_revoke-sessions.html)
- [Revoke IAM Identity Center user permissions and active account sessions](https://docs.aws.amazon.com/singlesignon/latest/userguide/revoke-user-permissions.html)
- [End active IAM Identity Center user sessions](https://docs.aws.amazon.com/singlesignon/latest/userguide/end-active-sessions.html)
- [Creating an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)
- [CloudTrail S3 bucket policy](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html)
- [AWS Security Hub overview](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub-v2.html)
- [Security Hub OCSF schema](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-ocsf.html)
- [Security Hub CSPM overview](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
- [AWS Audit Manager overview and new-customer availability notice](https://docs.aws.amazon.com/audit-manager/latest/userguide/what-is.html)
- [WAF oversize request components](https://docs.aws.amazon.com/waf/latest/developerguide/waf-oversize-request-components.html)
- [GuardDuty protection plans](https://docs.aws.amazon.com/guardduty/latest/ug/protection-plans.html)
- [GuardDuty trusted and threat IP lists](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_upload-lists.html)
- [ACM certificate requirements for CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html)
- [ACM managed certificate renewal](https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html)
- [Cross-account backup copies](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)

## Revision gate

Revision agent必須先完成三個全域動作：

1. 移除或替換全部110題的不安全community provenance；
2. 重排全部110題的固定答案位置並重新驗證answer/explanation mapping；
3. 擴寫列出的54題、72個過短解析。

之後再處理下列38個實質修訂ID：

`ch021-q01`, `ch021-q02`, `ch021-q03`, `ch021-q09`, `ch021-q10`,
`ch022-q01`, `ch022-q04`, `ch022-q08`,
`ch023-q08`, `ch023-q10`,
`ch024-q03`, `ch024-q04`, `ch024-q08`, `ch024-q09`, `ch024-q10`,
`ch025-q03`, `ch025-q07`, `ch025-q09`, `ch025-q10`,
`ch026-q05`, `ch026-q08`, `ch026-q10`,
`ch028-q03`, `ch028-q06`, `ch028-q07`, `ch028-q08`, `ch028-q09`,
`ch029-q03`, `ch029-q10`,
`ch030-q01`, `ch030-q02`, `ch030-q03`, `ch030-q08`, `ch030-q09`, `ch030-q10`,
`ch031-q04`, `ch031-q09`, `ch031-q10`。

修訂後必須由非P02-A、非本次revision agent的reviewer重新逐題核可。最終判定：**REVISE**。

## Verification

重新驗證日期：2026-10-01
驗證範圍：修訂後的 `tools/aws_question_banks/part_02.json` 全部 110 題、原列 38 題、101 個 source records、舊 fallback 與目前其他 parts 的 1,050 題。

### 已通過

- Part-specific schema通過：11章、每章10題、intent 1–10完整；88題單選、22題複選；每題答案與逐選項解析一一對應。
- 危險community provenance已完全移除：101個sources全部標為official，110題的`inspiration_ids`全部為空，沒有Jayendra、ExamTopics、dump、recalled或來源不明題庫metadata。
- 答案位置已重排：11章沒有相同的完整answer pattern，每章單一字母出現次數不超過4次，兩道複選也沒有重複answer pair；已無原本的A/B/C/D/A/B/C/D固定循環。
- 解析長度已修正：part_02沒有任何choice explanation低於checker的32字門檻。
- 跨題重複通過：part_02內沒有0.80以上近似題幹；與其他1,050題比較沒有0.80以上近似題幹；與舊chapter 21–31 fallback比較也沒有原先`ch022-q01`、`ch022-q04`的重疊。
- 原列38題的答案集合與技術內容均已按action重寫或補強。Security Hub相關題已明確區分current AWS Security Hub的OCSF/correlation/exposure與Security Hub CSPM的ASFF/standards/controls：
  - `ch025-q07`, `ch026-q10`使用Security Hub CSPM organization/delegated-admin語意。
  - `ch030-q08`標示`ENRICHMENT-CURRENT`並考current AWS Security Hub。
  - `ch030-q09`, `ch030-q10`明確考Security Hub CSPM與逐服務Regional coverage。
- Audit Manager 2026 scope已修正：`ch031-q09`, `ch031-q10`正確使用AWS官方2026-03-18公告；Audit Manager自2026-04-30起不接受新客戶，既有客戶可繼續使用。原review中的2026-05-20日期應以此現行官方公告為準。
- RCP已正確標為current enrichment：`ch025-q10`不再冒充SAP-C02 baseline，並正確說明RCP不授權、不適用management-account resources、可影響member-account root requests、service-linked roles有例外。截至驗證日，Organizations官方頁面列出62個支援RCP的service prefixes，與題目解析一致。
- 其餘原列修訂，包括Identity Center session revocation、organization trail ownership、CloudTrail bucket policy、GuardDuty plans/lists、Parameter Store父path風險、CloudFront VPC origin、cross-account backup與ACM lifecycle，核心答案均有唯一可辯護集合。

### 尚未通過：5個source IDs不是精確deep links

101個official sources中仍有5個URL會導向文件首頁或舊slug。這違反本次要求的「精確官方deep links」，影響10題：

1. `s3-service-auth`目前的`.../list_amazons3.html`導向Service Authorization Reference首頁。
   - 影響：`ch021-q01`, `ch021-q02`, `ch022-q04`
   - 必須改為現行S3 service-authorization頁：`https://docs.aws.amazon.com/service-authorization/latest/reference/list_s3.html`

2. `iam-last-access`目前使用舊slug並redirect。
   - 影響：`ch025-q09`
   - 必須直接改為：`https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_last-accessed.html`

3. `parameter-hierarchy`目前的`.../sysman-paramstore-su-organize.html`導向Systems Manager User Guide首頁。
   - 影響：`ch028-q06`
   - 父path遞迴授權陷阱應直接引用：`https://docs.aws.amazon.com/systems-manager/latest/userguide/ps-retrieval-authorization.html`
   - 若同時需要hierarchy建立語意，可再引用：`https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-hierarchies.html`

4. `acm-reimport`目前的`.../reimport-certificate.html`導向ACM User Guide首頁。
   - 影響：`ch028-q09`
   - 必須直接改為：`https://docs.aws.amazon.com/acm/latest/userguide/import-reimport.html`

5. `waf`目前的`.../web-acl-rules.html`導向WAF Developer Guide首頁。
   - 影響：`ch029-q01`, `ch029-q02`, `ch029-q09`, `ch029-q10`
   - `ch029-q01`應引用current web ACL與SQLi statement頁，例如`web-acl.html`及`waf-rule-statement-type-sqli-match.html`。
   - `ch029-q02`應引用`web-acl-rule-actions.html`，直接支持numeric priority與terminating action。
   - `ch029-q09`應引用`web-acl.html`或相應current request-inspection頁。
   - `ch029-q10`已有兩個精確origin sources，可移除退化的`waf`引用，或換成與該題實際claim對應的current deep link。

### 驗證結論

原38題的內容修訂、provenance、答案位置、current-service scope與重複檢查均已通過；但上述10題仍引用5個退化或舊slug的官方sources。修正URL並重新確認不redirect後，才可標為VERIFIED。

REVISE

## Final Verification

最終驗證日期：2026-10-01

本輪只讀`tools/aws_question_banks/part_02.json`，逐一核對上一輪5組退化或舊slug來源及其題目綁定。

### 已通過

- `s3-service-auth`已改為現行精確頁`list_s3.html`；`ch021-q01`、`ch021-q02`、`ch022-q04`均已引用。
- `iam-last-access`已改為現行精確頁`access_policies_last-accessed.html`；`ch025-q09`已引用。
- Parameter Store已分別引用授權頁`ps-retrieval-authorization.html`與階層頁`sysman-paramstore-hierarchies.html`；`ch028-q06`已涵蓋父path遞迴授權與hierarchy語意。
- `acm-reimport`已改為現行精確頁`import-reimport.html`；`ch028-q09`已引用。
- 舊`waf` source ID與退化的`web-acl-rules.html`已移除。`ch029-q02`、`ch029-q09`、`ch029-q10`目前的來源皆為現行且與各題claim直接對應的官方deep links。

### 尚未通過

- `ch029-q01`題幹明確包含credential stuffing，答案也明確主張bot rules；但目前只綁定`waf-web-acl`、`waf-sqli-match`與`shield`。前兩者分別支持一般Web ACL與SQL injection，`shield`支持錯誤選項辨析，沒有任何來源直接支持credential-stuffing／bot-control claim。
- 請為`ch029-q01`補上與實際敘述對應的現行官方來源，例如AWS WAF Fraud Control account takeover prevention的`waf-atp.html`及／或Bot Control的`waf-bot-control.html`。在此claim-level provenance缺口修正前，不能標為VERIFIED。

本輪未修改題庫。

REVISE

## Final Verification 2

最終驗證日期：2026-10-01

本輪只讀`tools/aws_question_banks/part_02.json`，重新核對`ch029-q01`的題目claim、source records與`source_ids`綁定。

### 驗證結果

- `ch029-q01`的`source_ids`已包含`waf-atp`與`waf-bot-control`，並保留`waf-web-acl`、`waf-sqli-match`及支持錯誤選項辨析的`shield`。
- `waf-atp`指向現行AWS官方deep link `https://docs.aws.amazon.com/waf/latest/developerguide/waf-atp.html`。該頁直接說明AWS WAF Fraud Control account takeover prevention會檢查登入請求、被竊取的憑證與異常登入嘗試，因此直接支持題目的credential-stuffing／ATP claim。
- `waf-bot-control`指向現行AWS官方deep link `https://docs.aws.amazon.com/waf/latest/developerguide/waf-bot-control.html`。該頁直接說明Bot Control可監控、封鎖或rate-limit bot traffic，因此直接支持答案中的bot controls claim。
- 題目敘述、正確答案與上述claim-level來源一致；上一輪唯一缺口已修正。

本輪未修改題庫。

VERIFIED
