---
title: 題目關鍵字速查
---

# 附錄 C　題目關鍵字速查

這份速查表把全書各章「考試這樣考」的關鍵字整理成「題目出現 X → 優先考慮 Y（為什麼）→ 第 N 章」的格式，依考試 domain 分節。用法有兩種：

1. **做題時卡住**：把題目裡最具體的那個限制（例如「不能經過 Internet」「超過 15 分鐘」「zone apex」）拿來查，先找到候選答案，再回到題目確認其他限制是否都滿足。
2. **考前複習**：只讀「題目出現」與「優先考慮」兩欄，遮住右邊自我測驗。

「優先考慮」的意思是「在沒有其他限制推翻它時的預設答案」。真實題目常會加一個限制讓預設答案失效，例如「LEAST operational overhead」會把自管方案刷掉、「without modifying the application」會把需要改程式的方案刷掉。最後一節整理這些**最佳化目標字眼**各自的解題傾向。

> [!tip] 考試提示
> 同一個關鍵字可能出現在不同 domain。本表依「這類題目最常被歸在哪個 domain」分節，不代表只會在那裡出現。易混淆服務的完整對照見附錄 A。

---

## SAA Domain 1：設計安全的架構（30%）

| # | 題目出現 | 優先考慮 | 為什麼 | 章 |
|---|---|---|---|---|
| C-1 | 新帳號、保護最高權限身份 | Root user 啟用 MFA、刪除 root access key、日常改用其他身份 | Root 不受 IAM policy 限制，外洩後果最嚴重 | 第 2、12 章 |
| C-2 | EC2 上的程式要存取 S3，不要存放憑證 | IAM role + instance profile | Role 提供自動輪替的臨時憑證，不需要在機器上放 access key | 第 12 章 |
| C-3 | Lambda／ECS 的程式權限 | Execution role／task role | 每個 workload 有自己的 role，符合最小權限 | 第 12、21 章 |
| C-4 | 同時有 Allow 與 Deny，結果是什麼 | Explicit deny 優先 | IAM 評估沒有順序，任何明確 Deny 都會勝出 | 第 12 章 |
| C-5 | 有 AdministratorAccess 仍被拒絕 | SCP、permissions boundary、session policy 或 explicit Deny | 這些機制都會在 identity policy 之上設上限 | 第 12、14 章 |
| C-6 | 能讀物件但不能列出 bucket | `s3:ListBucket` 的 Resource 寫 bucket ARN（不帶 `/*`） | ListBucket 作用在 bucket，GetObject 作用在 object | 第 12、22 章 |
| C-7 | 刪除或終止前必須通過 MFA | Deny + `BoolIfExists` `aws:MultiFactorAuthPresent` = false | 長期 access key 的請求不帶這個 key，用 `Bool` 會漏擋 | 第 12 章 |
| C-8 | 部署失敗：not authorized to perform `iam:PassRole` | 對特定 role 授予 `iam:PassRole`（可加 `iam:PassedToService`） | 把 role 交給服務需要獨立的權限；`Resource: "*"` 會造成提權 | 第 12 章 |
| C-9 | 專案越來越多，不想一直改 policy | ABAC：`aws:PrincipalTag` 比對 `aws:ResourceTag` | 以 tag 授權，新增專案不必新增 policy | 第 12 章 |
| C-10 | 找出被帳號或組織外部存取的資源 | IAM Access Analyzer（external access） | 以 zone of trust 自動分析 resource policy | 第 12 章 |
| C-11 | 依實際使用產生最小權限 policy | Access Analyzer policy generation、last accessed information | 依 CloudTrail 紀錄縮減權限，不用猜 | 第 12 章 |
| C-12 | 帳號 A 的身份要操作帳號 B 的資源 | B 建 role 信任 A，A 允許 `sts:AssumeRole` | 跨帳號 role 需要兩邊都授權 | 第 13 章 |
| C-13 | 第三方廠商要存取我們的帳號、防 confused deputy | 跨帳號 role + `sts:ExternalId` 條件 | External ID 由廠商為每個客戶產生，防止被冒用 | 第 13 章 |
| C-14 | App 使用者註冊、登入、社群登入 | Cognito user pool | 終端使用者不應建成 IAM user；user pool 發 JWT | 第 13 章 |
| C-15 | 行動 App 直接上傳 S3、每人只能存取自己的資料 | Cognito identity pool + `${cognito-identity.amazonaws.com:sub}` | Identity pool 換發臨時 AWS 憑證，policy 變數隔離每人 prefix | 第 13 章 |
| C-16 | 員工用企業帳號登入多個 AWS 帳號 | IAM Identity Center + permission sets | 集中管理 workforce 身份，外部 IdP 用 SCIM 同步 | 第 13 章 |
| C-17 | CI/CD（GitHub Actions）不想存 access key | OIDC identity provider + `AssumeRoleWithWebIdentity`（限定 `sub`） | 以短期 token 換臨時憑證，沒有長期金鑰 | 第 13 章 |
| C-18 | 只允許 ALB 連 app、只允許 app 連 DB，instance 會擴縮 | Security group 參照上游 SG | 以 SG 身份授權，不必維護變動的 IP | 第 6 章 |
| C-19 | 封鎖特定惡意 IP | NACL deny（編號小於 allow） | SG 沒有 deny；NACL 依編號 first match | 第 6 章 |
| C-20 | 資料庫不可被 Internet 存取 | 放在無 IGW／NAT route 的 subnet、不給 public IP | 是否 public 由 route table 決定，不是 subnet 名稱 | 第 5 章 |
| C-21 | Private subnet 呼叫 Secrets Manager、SSM、KMS 不經 Internet | Interface endpoint + private DNS | PrivateLink 讓服務名稱解析成 VPC 內的 private IP | 第 6 章 |
| C-22 | Bucket 只能從特定 VPC 或 endpoint 存取 | Bucket policy `aws:SourceVpce`／`aws:SourceVpc` | 經 endpoint 的請求沒有 public 來源 IP，`aws:SourceIp` 無效 | 第 6、22 章 |
| C-23 | 防止從 VPC 把資料寫到別人的 bucket | Endpoint policy 限制 Resource | Endpoint policy 是出口端的資料邊界 | 第 6 章 |
| C-24 | SQL injection、XSS、OWASP Top 10 | WAF + AWS managed rule groups | WAF 檢查 HTTP 請求內容，Shield 不做這件事 | 第 16 章 |
| C-25 | 同一 IP 大量請求、暴力破解登入 | WAF rate-based rule（scope-down 到登入路徑） | 依來源計數自動封鎖 | 第 16 章 |
| C-26 | DDoS 費用補償、24/7 DDoS 專家 | Shield Advanced | 提供 SRT 與 DDoS cost protection；Standard 已免費內建 | 第 16 章 |
| C-27 | 挖礦、異常 API、外洩 key、最少營運負擔 | GuardDuty（所有 Region 啟用） | 受管威脅偵測，不需自己開 Flow Logs | 第 16 章 |
| C-28 | S3 中的個資、信用卡號 | Macie | 專門掃描 S3 物件中的敏感資料 | 第 16 章 |
| C-29 | CVE、container image 漏洞掃描 | Inspector | 掃描 EC2、ECR image、Lambda 的已知漏洞 | 第 16 章 |
| C-30 | 誰刪了資源、誰改了 security group | CloudTrail | 記錄 API 呼叫者、時間與參數 | 第 16、36 章 |
| C-31 | 資源設定是否合規、自動修正 | Config rules + remediation（SSM Automation） | Config 評估設定並可觸發修正；不是事前阻止 | 第 16、38 章 |
| C-32 | 加密大檔案、超過 KMS 4 KB 限制 | Envelope encryption：`GenerateDataKey` 後本地加密 | KMS 只直接加密小資料，大資料用 data key | 第 15 章 |
| C-33 | 控制誰能解密、稽核每次解密 | Customer managed key + key policy + CloudTrail | AWS managed key 的 policy 不能改 | 第 15 章 |
| C-34 | 自動輪替資料庫密碼 | Secrets Manager rotation | Parameter Store 沒有內建輪替 | 第 15 章 |
| C-35 | 強制 S3 只能 HTTPS | Bucket policy Deny `aws:SecureTransport` = false | 以明確 Deny 擋下所有 HTTP 請求 | 第 15、22 章 |
| C-36 | 確保任何 bucket 都不會被公開 | 帳號層級 Block Public Access（+ SCP） | 預防勝於偵測後修正 | 第 22、38 章 |
| C-37 | 跨帳號上傳的 object 擁有權混亂 | Object Ownership：Bucket owner enforced（ACL disabled） | 停用 ACL，bucket owner 擁有所有 object | 第 22 章 |
| C-38 | S3 bucket 私有、只能經 CloudFront 存取 | OAC + bucket policy（`AWS:SourceArn` 限定 distribution） | OAC 是現行做法；OAI 是舊做法 | 第 11、22 章 |
| C-39 | 沒有 AWS 帳號的使用者限時上傳或下載 | S3 presigned URL | 借用簽章者權限、單一 object、有期限 | 第 22 章 |
| C-40 | 法規要求任何人（含 root）都不能刪除 | S3 Object Lock compliance mode | Governance mode 可被有 bypass 權限者繞過 | 第 23、43 章 |
| C-41 | 分享加密的 EBS snapshot、AMI 給另一帳號 | Customer managed key 重新加密，key policy 授權對方 | `aws/ebs` 的 policy 不能修改，無法分享 | 第 15、17、24 章 |
| C-42 | SSRF、防止竊取 instance 的 IAM 憑證 | 強制 IMDSv2（`HttpTokens=required`） | IMDSv2 需要先取得 session token | 第 17 章 |

## SAA Domain 2：設計有韌性的架構（26%）

| # | 題目出現 | 優先考慮 | 為什麼 | 章 |
|---|---|---|---|---|
| C-43 | highly available、撐過資料中心等級故障 | 跨至少兩個 AZ 部署 | AZ 是 Region 內的故障隔離單位 | 第 2 章 |
| C-44 | decouple components、下游變慢不影響前端 | SQS queue | 前端寫入 queue 即回應，worker 非同步處理 | 第 32 章 |
| C-45 | 一個事件要讓多個系統各自處理 | SNS fan-out 到多個 SQS queue | 每個訂閱者有自己的 queue，彼此獨立重試 | 第 32 章 |
| C-46 | must not lose any orders／messages | 先持久保存（SQS、資料庫）再處理 | Storage-first，處理失敗也能重來 | 第 1、20 章 |
| C-47 | 同一工作偶爾被處理兩次 | 加大 visibility timeout 或 `ChangeMessageVisibility` | 處理時間超過 timeout，訊息重新出現 | 第 32 章 |
| C-48 | 某些訊息一直失敗、卡住 worker | DLQ + `maxReceiveCount`，修正後 redrive | 把毒訊息隔離，不阻擋其他訊息 | 第 32 章 |
| C-49 | 訊息必須依序處理、不能重複 | SQS FIFO（group ID 設為實體 ID） | FIFO 在 group 內保序並去重 5 分鐘內的重送 | 第 32 章 |
| C-50 | 訊息超過 256 KB（題目常用數字） | 存 S3、訊息只帶指標（Extended Client Library） | Claim check pattern；現行上限已提高到 1 MiB | 第 32 章 |
| C-51 | 多步驟流程、分支、錯誤處理、要可視化 | Step Functions Standard | 流程狀態由服務保存，每一步可稽核 | 第 33 章 |
| C-52 | 等待人工核准、不要在 Lambda 中等待 | Step Functions `.waitForTaskToken` | 等待期間不占運算；Lambda 最長 15 分鐘 | 第 33 章 |
| C-53 | 重試造成重複扣款 | Idempotency key（DynamoDB conditional write） | At-least-once 投遞下，consumer 必須冪等 | 第 33 章 |
| C-54 | 重試造成下游過載、同時重試的尖峰 | Exponential backoff + jitter，只在一層重試 | 多層重試會指數放大流量 | 第 33、35 章 |
| C-55 | 跨服務交易，失敗時要撤銷前面步驟 | Saga + 補償交易（Step Functions 編排） | 分散式系統沒有跨服務的 rollback | 第 33 章 |
| C-56 | 資料庫 AZ 故障自動切換、不遺失已 commit 資料 | RDS Multi-AZ | 同步 standby，failover 透過 DNS 切換 | 第 26、34 章 |
| C-57 | 需要可讀的 standby、failover 更快（MySQL／PG） | Multi-AZ DB cluster | 兩台可讀 reader，failover 通常 35 秒內 | 第 26 章 |
| C-58 | 誤刪資料要回到某個時間點 | PITR（建立新 instance） | Replication 會同步錯誤，備份才能回到過去 | 第 4、26 章 |
| C-59 | Aurora MySQL 誤操作，幾分鐘內原地復原 | Backtrack | 只有 Aurora MySQL 支援原地倒轉 | 第 26 章 |
| C-60 | DynamoDB 誤寫要回到某個時間點 | PITR（還原成新 table） | 新 table 不帶 auto scaling、alarm、Streams 設定 | 第 27 章 |
| C-61 | ALB 顯示 unhealthy，但 instance 沒有被替換 | ASG health check type 改為 ELB | ASG 預設只看 EC2 status check | 第 18 章 |
| C-62 | 單台 EC2 故障要自動恢復、成本最低 | ASG min = max = desired = 1 | ASG 自動替換故障 instance | 第 18 章 |
| C-63 | Scale in 後使用者被登出 | Session 外部化到 ElastiCache 或 DynamoDB | Stateless 才能自由擴縮；sticky session 不能撐過 instance 終止 | 第 18、28 章 |
| C-64 | 一個 AZ 故障時容量不能下降 | 每個 AZ 預先配足容量（static stability） | 不依賴故障時才啟動新資源 | 第 18、34 章 |
| C-65 | NAT 要高可用、AZ 故障不影響其他 AZ | 每 AZ 一台 NAT Gateway，各 AZ 獨立 route table | NAT Gateway 是 zonal 資源 | 第 5 章 |
| C-66 | 主 Region 故障時切到備援或靜態維護頁 | Route 53 failover + health check（secondary 可 alias 到 S3 website） | DNS 層主備切換，primary 必須有 health check | 第 9 章 |
| C-67 | Health check 私有 subnet 的資源 | CloudWatch alarm 型 health check | Route 53 health checker 在 Internet 上，看不到 private IP | 第 9 章 |
| C-68 | RTO／RPO 數小時、成本最低 | Backup & restore + 跨 Region copy | 最便宜的 DR 策略 | 第 34 章 |
| C-69 | DR 端只保留資料庫複寫，運算平時關閉 | Pilot light | 資料層持續複寫，運算要先啟動才能接流量 | 第 34 章 |
| C-70 | DR 端有縮小版、隨時能接流量的環境 | Warm standby | 能直接接流量，只需擴展 | 第 34 章 |
| C-71 | 誤刪或覆寫 S3 object 要能復原 | Versioning | 刪除只加 delete marker，舊版本可還原 | 第 22 章 |
| C-72 | 跨 Region 的 S3 DR 副本 | CRR（兩邊都要 versioning） | 非同步複寫新 object；要 SLA 加 RTC | 第 23 章 |
| C-73 | 既有 object 沒有被複寫 | S3 Batch Replication | CRR 只處理規則建立後的新 object | 第 23 章 |
| C-74 | 備份不能被任何人刪除（含 root） | AWS Backup Vault Lock compliance mode | 冷靜期後任何人都不能移除 | 第 34、43 章 |
| C-75 | 部署時進行中的請求被中斷 | Deregistration delay（connection draining） | 讓舊 target 完成進行中的請求再移除 | 第 10 章 |
| C-76 | 被縮減前要上傳 log 或完成工作 | Termination lifecycle hook | 在 instance 終止前暫停並執行收尾 | 第 18 章 |
| C-77 | 處理時間超過 15 分鐘 | ECS／Fargate task、AWS Batch，或 Step Functions 拆步驟 | Lambda 最長 15 分鐘是硬性上限 | 第 19、21 章 |
| C-78 | 非同步呼叫失敗要保留事件與錯誤，成功也要通知 | Lambda destinations | 只適用非同步呼叫；SQS 觸發用 SQS 的 DLQ | 第 19 章 |
| C-79 | 一批 SQS 訊息只有幾筆失敗，不想重做整批 | `ReportBatchItemFailures` | 只讓失敗的訊息重新出現 | 第 19 章 |
| C-80 | 工作需要數分鐘、client 收到 504 | 非同步模式：202 + jobId + 查詢狀態 | API Gateway 整合逾時預設 29 秒 | 第 20、33 章 |

## SAA Domain 3：設計高效能的架構（24%）

| # | 題目出現 | 優先考慮 | 為什麼 | 章 |
|---|---|---|---|---|
| C-81 | 全球使用者靜態內容慢、降低 origin 負載 | CloudFront | Edge 快取縮短距離並減少回源 | 第 11 章 |
| C-82 | UDP、遊戲、VoIP、IoT 的全球加速 | Global Accelerator | CloudFront 不處理 UDP，GA 從最近 edge 進 AWS 骨幹 | 第 11 章 |
| C-83 | 固定 IP 白名單、anycast | Global Accelerator（2 個 static IP） | ALB 與 CloudFront 的 IP 會變 | 第 11 章 |
| C-84 | 多 Region 快速 failover、不受 DNS 快取影響 | Global Accelerator | 封包層切換，入口 IP 不變 | 第 11、42 章 |
| C-85 | 全球使用者上傳大檔到單一 bucket 很慢 | S3 Transfer Acceleration + multipart upload | 從最近 edge 進入 AWS 網路 | 第 11、22 章 |
| C-86 | 命中率低、origin 負載高 | 縮減 cache key（cache policy），其餘值放 origin request policy | Cache key 越多維度，同一內容被切成越多份 | 第 11 章 |
| C-87 | 簡單 header／URL 改寫、每秒大量請求、最低成本 | CloudFront Functions | 輕量、所有 edge 執行、成本低 | 第 11 章 |
| C-88 | 邊緣需要呼叫外部服務、讀 body、依條件選 origin | Lambda@Edge（us-east-1 建立） | CloudFront Functions 沒有網路存取 | 第 11 章 |
| C-89 | 依 URL path 或 host 分流到不同服務 | ALB listener rules（path-pattern、host-header） | ALB 是 L7，看得懂 HTTP | 第 10 章 |
| C-90 | 需要固定 IP、EIP，或 UDP、極低延遲 | NLB | 每 AZ 一個固定 IP，L4 高效能 | 第 10 章 |
| C-91 | 後端必須自己終止 TLS | NLB TCP listener（passthrough） | NLB TLS listener 會終止 TLS | 第 10 章 |
| C-92 | 全球使用者連到延遲最低的 Region | Route 53 latency routing | 依量到的延遲回答 | 第 9、42 章 |
| C-93 | zone apex（root domain）指向 ALB 或 CloudFront | Route 53 alias record | Apex 不能放 CNAME；alias 指向 AWS 資源免費 | 第 9 章 |
| C-94 | 依國家提供不同內容、法規限制國家 | Geolocation routing + default 記錄 | 沒有 default，未對應地區拿不到答案 | 第 9 章 |
| C-95 | VPN 頻寬超過單一 tunnel 上限 | TGW + 多條 VPN + BGP ECMP | VGW 不支援 ECMP | 第 8 章 |
| C-96 | 一致的延遲、大量持續傳輸、不經 Internet | Direct Connect | 私有實體線路，延遲可預期 | 第 8 章 |
| C-97 | 多台 Linux 跨 AZ 共享檔案 | EFS（每 AZ 一個 mount target） | NFS、自動擴縮、Regional | 第 24 章 |
| C-98 | Windows、SMB、NTFS ACL、Active Directory | FSx for Windows File Server | EFS 只支援 NFS | 第 24 章 |
| C-99 | HPC、ML 訓練、資料在 S3、平行檔案系統 | FSx for Lustre | 極高平行 throughput，與 S3 整合 | 第 24 章 |
| C-100 | 關鍵資料庫、持續高 IOPS、最高耐久度 | io2 Block Express | 頂規 SSD，耐久度 99.999% | 第 24 章 |
| C-101 | 暫存、快取、可重建、最高 I/O | Instance store | 本機磁碟，stop／terminate 後消失 | 第 17、24 章 |
| C-102 | 檔案大於 5 GB、上傳常失敗要續傳 | Multipart upload | 分段平行上傳、失敗只重傳該段 | 第 22 章 |
| C-103 | S3 回 503 Slow Down、高請求率 | 分散 prefix、平行化、指數退避 | 請求率限制以 prefix 為單位 | 第 22、35 章 |
| C-104 | 寫入後立即讀取或 LIST 要看到最新資料 | 不需額外機制 | S3 自 2020-12 起提供 strong read-after-write consistency | 第 22 章 |
| C-105 | 相同查詢重複、資料庫 CPU 高、讀多寫少 | ElastiCache + cache-aside | 次毫秒讀取，減少資料庫負載 | 第 28、35 章 |
| C-106 | 報表查詢拖慢交易資料庫 | Read replica 或 Aurora reader endpoint | 各種不同 SQL 用副本承擔 | 第 26、35 章 |
| C-107 | Lambda 大量連線打爆 RDS | RDS Proxy | 連線池化；不解決慢查詢 | 第 19、26 章 |
| C-108 | 讀取量大、快速 failover、跨 Region 秒級 RPO | Aurora | 最多 15 個 replica 共用儲存 | 第 26 章 |
| C-109 | DynamoDB 微秒讀取、最少程式修改 | DAX | 只加速 eventually consistent read | 第 27、28 章 |
| C-110 | DynamoDB 總容量充足但仍被 throttle | 高基數 partition key 或 write sharding | 熱分割，單一 partition 有吞吐上限 | 第 27 章 |
| C-111 | DynamoDB 依另一個屬性查詢、table 已上線 | GSI | LSI 只能建表時建立 | 第 27 章 |
| C-112 | leaderboard、ranking | ElastiCache Valkey／Redis OSS sorted set | Memcached 沒有資料結構 | 第 28 章 |
| C-113 | 全文搜尋、模糊比對、相關度排序 | OpenSearch Service | 搜尋索引；不當唯一資料來源 | 第 29 章 |
| C-114 | 社群網路、朋友的朋友、詐欺環 | Neptune | 多層關係走訪用 graph | 第 29 章 |
| C-115 | MongoDB 相容、遷移既有 MongoDB | DocumentDB | MongoDB API 相容，遷移前要驗證功能 | 第 29 章 |
| C-116 | 即時、多個應用讀同一份資料、可重播 | Kinesis Data Streams | Retention 最長 365 天，每個 consumer 各讀一次 | 第 31 章 |
| C-117 | 近即時把串流存進 S3／Redshift，最少營運 | Data Firehose | 免寫 consumer，有 buffer | 第 31 章 |
| C-118 | 串流 JSON 轉 Parquet、依欄位分區寫入 S3 | Firehose format conversion + dynamic partitioning | Schema 來自 Glue Data Catalog | 第 31、52 章 |
| C-119 | 滑動視窗、即時彙總、有狀態串流運算 | Managed Service for Apache Flink | Lambda 適合無狀態逐筆處理 | 第 31 章 |
| C-120 | 消除 cold start、穩定低延遲 | Provisioned concurrency | Reserved concurrency 不消除 cold start | 第 19 章 |
| C-121 | CPU 密集的 Lambda 太慢 | 增加記憶體 | CPU 依記憶體比例配置，可能也更便宜 | 第 19 章 |
| C-122 | 新 instance 開機要 10 分鐘、擴展太慢 | Golden AMI；再不夠用 warm pool | 縮短開機時間優先於調 scaling | 第 17、18 章 |
| C-123 | 每天或每週固定時間的尖峰 | Scheduled action（提高 min） | 已知時間就預先擴展，不等指標反應 | 第 18、48 章 |
| C-124 | SQS worker 依 queue 長度擴展 | Backlog per instance custom metric + target tracking | 指標需隨機器數成比例下降 | 第 18、32 章 |
| C-125 | HPC、節點間低延遲、MPI | Cluster placement group + EFA | 同一 AZ 緊密放置 | 第 17、21 章 |
| C-126 | 跑 container、不想管伺服器、沒提 Kubernetes | ECS on Fargate | 營運負擔最低的 container 平台 | 第 21 章 |
| C-127 | 已有 Kubernetes、Helm、operator | EKS | 標準 Kubernetes API | 第 21 章 |

## SAA Domain 4：設計成本最佳化的架構（20%）

| # | 題目出現 | 優先考慮 | 為什麼 | 章 |
|---|---|---|---|---|
| C-128 | NAT Gateway 費用高、流量多到 S3／DynamoDB | Gateway VPC endpoint | 免費，流量不經 NAT 處理 | 第 5、6、39 章 |
| C-129 | Private subnet 拉 ECR 映像經 NAT 很貴 | ECR `ecr.api`、`ecr.dkr` interface endpoint + S3 gateway endpoint | Image layer 存在 S3 | 第 21、39 章 |
| C-130 | 全球使用者下載 S3 內容、傳出費用高 | CloudFront | 快取減少回源，origin 到 CloudFront 免費 | 第 39 章 |
| C-131 | 跨 AZ data transfer 費用高 | 每 AZ 一台 NAT、AZ affinity | 不能為省錢犧牲多 AZ | 第 39 章 |
| C-132 | 可中斷的批次、彈性工作、最低成本 | Spot（多 type、多 AZ、`price-capacity-optimized`） | 最高約 90% 折扣，處理 2 分鐘通知 | 第 17、39 章 |
| C-133 | 穩定 baseline、會改 family 或用 Fargate／Lambda | Compute Savings Plans | 涵蓋 EC2、Fargate、Lambda，彈性最高 | 第 17、39 章 |
| C-134 | 穩定使用同一 family、同一 Region，要最大折扣 | EC2 Instance Savings Plans 或 Standard RI | 最高約 72% | 第 39 章 |
| C-135 | 需要保證某 AZ 有容量 | On-Demand Capacity Reservation（或 zonal RI） | Savings Plans 與 Regional RI 不保留容量 | 第 17、39 章 |
| C-136 | 平均 CPU 很低、想縮小規格 | Compute Optimizer（記憶體需 CloudWatch agent） | 先 rightsizing 再買承諾 | 第 35、39 章 |
| C-137 | 降低 stateless web tier 成本、仍要穩定基礎容量 | Mixed instances：On-Demand base + Spot | Base 保底，其餘用 Spot | 第 18 章 |
| C-138 | 改善價格效能、程式是 Java／Python／Node.js | Graviton（arm64） | 同效能更低價格 | 第 17 章 |
| C-139 | 存取模式未知、會變化、不想管理 | S3 Intelligent-Tiering | 自動分層；有監控費，< 128 KB 不分層 | 第 23 章 |
| C-140 | 可重新產生的資料、最低成本、毫秒讀取 | S3 One Zone-IA | 只存一個 AZ | 第 23 章 |
| C-141 | 長期保存、幾乎不讀、可等 12–48 小時 | S3 Glacier Deep Archive | 儲存費最低；最短存放 180 天 | 第 23 章 |
| C-142 | 不常讀、要毫秒、資料不可重建 | Standard-IA（每季以下讀取：Glacier Instant Retrieval） | 跨 AZ 且毫秒讀取 | 第 23 章 |
| C-143 | 自動轉換儲存類別、到期刪除 | S3 lifecycle rules | 注意最短存放天數與 128 KB 最小計費 | 第 23 章 |
| C-144 | 未完成的 multipart upload 占用費用 | Lifecycle `AbortIncompleteMultipartUpload` | 未完成的分段仍計費 | 第 22 章 |
| C-145 | Versioning bucket 舊版本累積成本 | `NoncurrentVersionExpiration` | 定期清除非現行版本 | 第 23 章 |
| C-146 | gp2 volume 成本高、IOPS 需求不大 | 線上改成 gp3 | gp3 IOPS 與容量脫鉤且較便宜 | 第 24、39 章 |
| C-147 | 很少存取的循序資料、最低成本 block | sc1 | 每 GB 最便宜；不能開機 | 第 24 章 |
| C-148 | EBS snapshot 長期保存、極少還原 | EBS Snapshots Archive | 至少 90 天、還原 24–72 小時 | 第 24 章 |
| C-149 | 流量無法預測的 DynamoDB 新應用 | On-demand capacity | 不用規劃容量 | 第 27 章 |
| C-150 | 穩定可預測的 DynamoDB 流量、降低成本 | Provisioned + auto scaling（+ reserved capacity） | 穩定流量下單價較低 | 第 27 章 |
| C-151 | 負載難預測、間歇使用的關聯式資料庫 | Aurora Serverless v2 | 依用量自動調整容量 | 第 26 章 |
| C-152 | Aurora 帳單 I/O 費用占比很高 | Aurora I/O-Optimized | I/O 不另計費 | 第 26、39 章 |
| C-153 | 開發環境只在上班時間使用 | 排程停止 EC2／RDS，或 Aurora Serverless v2 | 不用的時間不付運算費 | 第 39 章 |
| C-154 | 空的 ReceiveMessage 很多、降低 SQS 成本 | Long polling（`ReceiveMessageWaitTimeSeconds` = 20） | 減少空回應的請求數 | 第 32 章 |
| C-155 | Athena 查詢慢又貴 | 轉 Parquet／ORC + 壓縮 + 分區 | 計費依掃描量，`LIMIT` 不省錢 | 第 30 章 |
| C-156 | 只要 JWT 驗證與 Lambda proxy、成本最低 | HTTP API + JWT authorizer | 比 REST API 便宜，功能足夠 | 第 20 章 |
| C-157 | 下載者應負擔流量費 | S3 Requester Pays | 請求者付請求與傳輸費 | 第 22 章 |
| C-158 | 偵測不尋常的支出增加 | Cost Anomaly Detection | 自動找出異常與根因 | 第 39 章 |
| C-159 | 超過預算時自動限制 | Budgets actions（IAM policy、SCP、停止 instance） | Budgets 有資料延遲，不是即時阻擋 | 第 39、43 章 |

## SAP Domain 1：為組織複雜度設計（26%）

| # | 題目出現 | 優先考慮 | 為什麼 | 章 |
|---|---|---|---|---|
| C-160 | 隔離 prod／dev 的權限、帳單、配額與爆炸半徑 | 多帳號 + Organizations OU | 帳號是最強的隔離邊界 | 第 14、40 章 |
| C-161 | LEAST operational overhead 建立多帳號 landing zone | AWS Control Tower | 一次建立帳號基線、guardrail 與 Account Factory | 第 14、40 章 |
| C-162 | Terraform、GitOps、大量帳號自動供應 | Account Factory for Terraform（AFT） | 以 Terraform pipeline 開帳號與客製化 | 第 40 章 |
| C-163 | 防止任何人（含帳號管理員）停用 CloudTrail／GuardDuty | SCP Deny（附加在 root 或 OU） | SCP 影響成員帳號所有 principal，含 root | 第 14 章 |
| C-164 | 限制只能在特定 Region 部署 | SCP + `aws:RequestedRegion` + 全球服務 `NotAction` 例外 | 忘了豁免 IAM、Route 53 等全球服務會把它們擋掉 | 第 14、43、50 章 |
| C-165 | 拒絕組織外身份存取 S3／KMS，即使 bucket policy 寫錯 | RCP + `aws:PrincipalOrgID` | RCP 是資源端的組織護欄 | 第 14、40 章 |
| C-166 | 防止員工把資料複製到組織外的 bucket | SCP 或 endpoint policy + `aws:ResourceOrgID` | 限制 principal 只能寫入組織內資源 | 第 40 章 |
| C-167 | 沒有某個 tag 就不能建立資源 | SCP + `aws:RequestTag` | Tag policy 只規範格式，不強制存在 | 第 14、40、43 章 |
| C-168 | 新 SCP 要先測試、不能影響 production | Policy Staging OU，分階段推出 | 限制錯誤 policy 的影響範圍 | 第 40 章 |
| C-169 | 資安團隊集中管理 GuardDuty、Security Hub，不用 management account | Delegated administrator（Audit 帳號） | Management account 只放組織管理與帳單 | 第 14、40、43 章 |
| C-170 | 新帳號、新 Region 也要立即被 GuardDuty 保護 | 每個 Region 指定 delegated admin 並開啟 auto-enable | GuardDuty 是 Regional 服務 | 第 40 章 |
| C-171 | 所有帳號的 API 活動集中保存、成員不可關閉 | Organization trail → Log Archive 帳號 + SCP | 日誌與產生日誌的帳號分開 | 第 16、40 章 |
| C-172 | 全組織資源設定與合規總覽 | Config organization aggregator（delegated admin） | 集中檢視多帳號多 Region | 第 40、43 章 |
| C-173 | IdP 故障時仍能進入 AWS | 獨立於 IdP 的 break-glass IAM user + 硬體 MFA + 使用告警 | 聯合登入有單點，要有受控的緊急路徑 | 第 40、50 章 |
| C-174 | 數十個 VPC、多帳號，要互連並連地端 | Transit Gateway（Network 帳號擁有、RAM 共享） | Hub-and-spoke，集中路由 | 第 7、41 章 |
| C-175 | prod 與 dev 不可互通，但都要存取 shared services | 不同 TGW route table 控制 association／propagation | 以路由層分段，不靠 SG 或 NACL | 第 7、41 章 |
| C-176 | 減少每個 VPC 的 NAT Gateway、集中控制對外流量 | 集中 egress VPC + TGW default route | 共用出口；spoke 加 blackhole 防意外互通 | 第 41 章 |
| C-177 | 所有 VPC 間與往 Internet 的流量都要經 stateful 檢查 | Inspection VPC + Network Firewall（或 GWLB）+ appliance mode | Appliance mode 避免跨 AZ 不對稱路由 | 第 41 章 |
| C-178 | 減少每個 VPC 的 interface endpoint 費用 | 集中 endpoint VPC + PHZ 關聯到 spoke（或 Route 53 Profiles） | 一組 endpoint 服務所有 VPC | 第 41 章 |
| C-179 | 一組 DX 連到多個 Region 的 TGW | Transit VIF → Direct Connect Gateway → 多個 TGW | DXGW 是全球資源；不在 TGW 之間轉送 | 第 8、41 章 |
| C-180 | 所有帳號都要解析地端網域，不想每個 VPC 建 outbound endpoint | 集中 outbound endpoint + RAM 共享 forwarding rule | DNS 轉送規則可跨帳號共享 | 第 8、41 章 |
| C-181 | 多 Region、宣告式、依 tag 自動分段的全球網路 | AWS Cloud WAN core network policy | Region 多時比 TGW peering 好管理 | 第 41 章 |
| C-182 | 中央團隊管網路、應用團隊不能改路由、降低 attachment 數 | Shared VPC（RAM 共享 subnet） | 多帳號共用同一 VPC | 第 7、41 章 |
| C-183 | 跨帳號共享 data lake 表、不複製資料 | Lake Formation cross-account（RAM + resource link） | 集中權限、資料留在原處 | 第 30 章 |
| C-257 | 所有帳號（含新帳號）都要有一致的備份計畫，成員帳號不能修改 | Organizations backup policy（StackSets 部署它引用的 vault 與 IAM role） | StackSets 部署的 backup plan 成員可改；backup policy 不會建立 vault 與 role | 第 43 章 |
| C-258 | 共用網路帳號的成本依各事業部比例分攤，並看得到未分配成本 | Cost categories + `PROPORTIONAL` split charge rule + `DefaultValue` | Cost allocation tags 只是維度，不會分攤；Billing Conductor 不做比例分攤 | 第 43 章 |
| C-259 | 即將分拆的子公司，RI／Savings Plans 只給自己用 | Management account 對該帳號關閉 discount sharing | 關閉是雙向的：它也不再接收其他帳號的折扣；Billing Conductor 只改呈現 | 第 43 章 |

## SAP Domain 2：設計新解決方案（29%）

| # | 題目出現 | 優先考慮 | 為什麼 | 章 |
|---|---|---|---|---|
| C-184 | 同一份 template 部署到 Organization 所有帳號，新帳號自動套用 | StackSets（service-managed、automatic deployment） | 多帳號多 Region 一次管理 | 第 37、40 章 |
| C-185 | Lambda 先導 10% 流量再全部切換、alarm 時自動退回 | CodeDeploy canary + Lambda alias | 權重在每次呼叫生效，可依 alarm 回退 | 第 37 章 |
| C-186 | 藍綠切換不受 DNS 快取影響 | ALB weighted target groups | Route 53 weighted 受 TTL 影響 | 第 37 章 |
| C-187 | 不重新部署就開關功能、漸進開放 | AppConfig feature flags | 部署與發布分離 | 第 37 章 |
| C-188 | 刪除 stack 或 replacement 時保留資料 | DeletionPolicy／UpdateReplacePolicy：Retain 或 Snapshot | 只設 DeletionPolicy 擋不住更新造成的替換 | 第 37 章 |
| C-189 | 跨 Region 關聯式資料庫、RPO 約 1 秒、RTO 約 1 分鐘 | Aurora Global Database | 儲存層跨 Region 複寫 | 第 26、34、42 章 |
| C-190 | 計畫內 Region 切換且不能遺失資料 | Aurora Global Database switchover | Switchover 的 RPO 為 0；failover 可能遺失複寫延遲內的資料 | 第 34、42、53 章 |
| C-191 | RTO 接近 0、多 Region 同時寫入 | Active-active + DynamoDB global tables | 多 Region 寫入，MREC 以 last writer wins 處理衝突；要跨 Region 強一致、RPO 0 時用 MRSC（剛好三個 Region、不支援 transactions） | 第 34、42、53 章 |
| C-192 | RTO 數分鐘、RPO 秒級、成本要控制 | Warm standby + Aurora Global Database | 剛好滿足數字的最便宜策略 | 第 53 章 |
| C-193 | Failover 不依賴 Route 53 control plane、防誤關所有 Region | ARC routing control + safety rules | Data plane 開關、受控切換 | 第 34、42、53 章 |
| C-194 | DR Region 解密資料、讀取密碼 | KMS multi-Region keys、Secrets Manager 跨 Region 複寫 | 只複寫資料、忘了金鑰與密碼，DR 起得來卻跑不動 | 第 15、42、53 章 |
| C-195 | 地端或 VM 秒級 RPO、分鐘級 RTO、不改架構 | AWS Elastic Disaster Recovery | 整台伺服器持續區塊複寫 | 第 34 章 |
| C-196 | 單一租戶 HSM、客戶獨占控制金鑰 | CloudHSM；要保留服務整合時用 KMS custom key store | AWS 無法存取 HSM 中的金鑰 | 第 15、50 章 |
| C-197 | 金鑰必須放在 AWS 以外 | KMS external key store | 金鑰材料留在外部系統 | 第 50 章 |
| C-198 | 縮小 PCI DSS 稽核範圍 | CDE 獨立帳號／OU、網路分段、tokenization | 範圍只包含處理卡號的元件 | 第 40、50 章 |
| C-199 | 多租戶共用 DynamoDB table、防止跨租戶存取 | `dynamodb:LeadingKeys` + session tag（ABAC） | IAM 層強制，不靠 FilterExpression | 第 49 章 |
| C-200 | 不同方案有不同的 API 請求上限 | API Gateway REST API usage plan + API key | 只有 REST API 有 usage plan；quota 是 best effort | 第 20、49 章 |
| C-201 | 一個租戶的批次工作拖慢所有人 | 獨立函數 + reserved concurrency、SQS 緩衝 | Bulkhead 隔離共享資源 | 第 35、49 章 |
| C-202 | 限制錯誤部署或故障的影響範圍 | Cell-based architecture | 每個 cell 獨立，故障只影響一部分客戶 | 第 35 章 |
| C-203 | 依公司文件回答問題、不想訓練模型 | Bedrock Knowledge Bases（RAG） | 文件更新即可反映，附來源 | 第 47、53 章 |
| C-204 | 遮罩回答中的個資、禁止某些主題 | Bedrock Guardrails | 內容安全過濾；不是授權機制 | 第 47、53 章 |
| C-205 | 稽核所有 prompt 與回應 | Model invocation logging（預設關閉） | CloudTrail 不記錄 prompt 內容 | 第 47 章 |
| C-206 | AI 執行高風險動作前要人核准 | Step Functions Standard + `.waitForTaskToken` | 可等待很久、不占運算 | 第 47、53 章 |
| C-207 | 跨帳號微服務、以 IAM 身份授權、HTTP 路徑路由 | VPC Lattice + auth policy | 應用層服務網路，不需管路由 | 第 7 章 |
| C-260 | 多 Region 都要低延遲寫入、同一筆不能衝突，或個資只能留在某地區 | Home Region 分區：依使用者身份路由寫入，依地區拆分 table | Geolocation 只決定入口；global tables 會複寫整張 table | 第 42 章 |
| C-261 | 兩個 Region 的應用程式用同一個名稱存取 S3，故障時幾分鐘內切換、不重新部署 | S3 Multi-Region Access Point + 複寫規則 + failover controls | MRAP 本身不複製資料；用戶端要用 SigV4A | 第 42 章 |

## SAP Domain 3：持續改善既有方案（25%）

| # | 題目出現 | 優先考慮 | 為什麼 | 章 |
|---|---|---|---|---|
| C-208 | 不開放 inbound port、不使用 bastion、稽核所有登入 | Session Manager + session logging | Agent 主動連出，SG 不需 inbound 規則 | 第 38 章 |
| C-209 | 每週固定時段 patch、需要合規報告 | Patch Manager + Maintenance Window 或 patch policy | Baseline、Scan／Install 與合規報告 | 第 38 章 |
| C-210 | 確保所有（含新建）instance 持續安裝某 agent | State Manager association | 持續套用期望狀態 | 第 38 章 |
| C-211 | 有人修改 security group 就立即反應 | EventBridge（CloudTrail API 事件）→ Lambda／Automation | 事件驅動自動修復 | 第 38 章 |
| C-212 | 系統性審查架構風險並追蹤改善 | Well-Architected Tool（lens、milestone、improvement plan） | Trusted Advisor 只檢查資源設定 | 第 38、46 章 |
| C-213 | 太多 alarm 同時響、要減少誤報 | Composite alarm | 底層 alarm 不通知，只由組合條件通知 | 第 36 章 |
| C-214 | 流量有日夜週期，固定閾值誤報 | Anomaly detection alarm | 依歷史模式動態計算範圍 | 第 36 章 |
| C-215 | 監控正常但使用者失敗、要在客戶之前發現 | 業務 custom metric + Synthetics canary | 基礎指標看不到業務流程失敗 | 第 36、54 章 |
| C-216 | 微服務找出延遲來自哪個下游 | X-Ray／ADOT tracing、service map | 跨服務追蹤單一請求 | 第 36 章 |
| C-217 | 集中檢視多個帳號的指標、日誌、trace | CloudWatch cross-account observability | Monitoring account 集中檢視；不等於不可竄改保存 | 第 36 章 |
| C-218 | 密碼寫在設定檔 | Secrets Manager + 自動輪替 | 消除硬編碼機密 | 第 46 章 |
| C-219 | 非關鍵功能故障導致整頁失敗 | Timeout + fallback、circuit breaker、feature flag | Graceful degradation 保住核心功能 | 第 35 章 |
| C-220 | 提前知道快達到 service quota | Service Quotas 用量 alarm、Trusted Advisor | 事前申請提高，不在事故中才發現 | 第 35 章 |
| C-221 | 所有新帳號都需要較高的 quota | Organizations 的 quota request template | 開帳號時自動申請 | 第 35 章 |
| C-222 | 舊程式 session 存在記憶體、scale in 後使用者被登出 | 外部 session store（ElastiCache／DynamoDB） | Sticky session 只是短期緩解 | 第 10、18 章 |
| C-223 | 自管 RabbitMQ／ActiveMQ，程式不能改 | Amazon MQ | 協定相容，最少程式修改 | 第 32、46 章 |
| C-224 | 資料庫需要 OS 存取又想要受管 | RDS Custom | 保留 OS 存取的受管服務（Oracle、SQL Server） | 第 26、46 章 |
| C-225 | 改善既有系統：選項有「全部重寫成微服務」與「加受管服務或快取」 | 改動較小、能直接解決痛點的選項 | SAP Domain 3 問的是改善，不是重建 | 第 46 章 |
| C-226 | 共用 EKS／ECS 叢集的成本分攤 | Split cost allocation data | 依 task／Pod 用量拆分成本 | 第 39 章 |
| C-227 | Tag 已加但 Cost Explorer 看不到 | 在管理帳號啟用 cost allocation tags | Tag 要啟用後才出現在帳單 | 第 39、43 章 |
| C-228 | 最詳細的帳單資料、用 SQL 分析 | Data Exports（CUR 2.0）→ S3 → Athena | 逐資源逐小時明細 | 第 39、43 章 |
| C-229 | 定期自動驗證備份可還原並量測時間 | AWS Backup restore testing | 證明備份真的能用 | 第 34 章 |
| C-230 | 在正式環境安全地注入故障 | AWS FIS + CloudWatch alarm stop condition | 異常時自動停止實驗 | 第 34 章 |

## SAP Domain 4：加速遷移與現代化（20%）

| # | 題目出現 | 優先考慮 | 為什麼 | 章 |
|---|---|---|---|---|
| C-231 | 資料中心租約即將到期、最短時間、最少變更 | Rehost（MGN） | 先搬再現代化 | 第 44、45 章 |
| C-232 | 收集伺服器的程序與網路連線、畫相依關係 | ADS Discovery Agent（考試答案；ADS 自 2025-11-07 起不開放新客戶） | Agentless Collector 看不到 OS 內的程序與連線 | 第 44、51 章 |
| C-233 | VMware 環境、不允許在 VM 內安裝軟體 | ADS Agentless Collector（vCenter；新客戶改用 AWS Transform） | 收規格與使用率，不需安裝 agent | 第 44、51 章 |
| C-234 | 依地端實際使用率建立 business case、比較授權 | Migration Evaluator | 成本預測與授權比較 | 第 44 章 |
| C-235 | 集中追蹤多個遷移工具的進度 | Migration Hub（考試答案；2025-11-07 起不開放新客戶） | 只追蹤，不執行遷移 | 第 44、51 章 |
| C-236 | 保留 VMware 營運工具、不轉換 VM 格式 | Relocate（VMware Cloud on AWS、Amazon EVS） | 平台層搬遷 | 第 44 章 |
| C-237 | 自管資料庫改受管服務、引擎不變 | Replatform（例如 RDS for Oracle） | 少量改動換取營運負擔下降 | 第 44 章 |
| C-238 | 高頻率同步呼叫的元件 | 同一個 move group、同一 wave | 拆開會造成跨網路延遲與失敗 | 第 44、51 章 |
| C-239 | 既有 Windows Server 授權 BYOL、需要 socket／core 可見性 | Dedicated Hosts（+ License Manager） | Dedicated Instances 沒有 host 可見性 | 第 17、44 章 |
| C-240 | RDS for Oracle 要 Enterprise Edition | BYOL | License Included 只有 SE2 | 第 29、44 章 |
| C-241 | 大量 VM rehost、停機最短、可先測試 | MGN（test launch → cutover → finalize） | Test launch 不影響持續複寫 | 第 45、51 章 |
| C-242 | MGN 複寫流量不得經過 Internet | Replication settings 使用 private IP，經 DX／VPN | 搬遷路徑也要符合網路要求 | 第 45 章 |
| C-243 | 資料庫遷移、停機時間最短 | DMS full load + CDC | 只做 full load 會遺失期間的寫入 | 第 45、51 章 |
| C-244 | Oracle → PostgreSQL、轉換 PL/SQL | DMS Schema Conversion 或 SCT + DMS 搬資料 | SCT 不搬資料，DMS 不轉程式碼 | 第 45 章 |
| C-245 | 遷移後查詢很慢、新增資料主鍵衝突 | 補建 secondary index、重設 sequence | DMS 只建資料表與主鍵 | 第 45 章 |
| C-246 | 證明來源與目標資料一致 | DMS data validation | 只比筆數不夠 | 第 45 章 |
| C-247 | 切換後幾天內仍要能退回、不遺失資料 | 反向 DMS CDC（新目標 → 舊來源） | 保留回退路徑 | 第 45 章 |
| C-248 | 切換時用戶端要快速改連新位址 | 提前降低 DNS TTL | 切換當下才降 TTL 來不及 | 第 3、45 章 |
| C-249 | Windows 檔案伺服器搬到 FSx、保留 NTFS 權限 | DataSync（SMB → FSx for Windows） | DataSync 保留 metadata 並驗證 | 第 25、45 章 |
| C-250 | 數十 TB 到 PB、網路要好幾週、要盡快 | 先算天數；考題常見答案為 Snowball Edge（現況不開放新客戶） | 頻寬 × 時間不夠才考慮離線或加頻寬 | 第 25、45 章 |
| C-251 | DX 還沒好但要立即開始遷移 | 先 Site-to-Site VPN，DX 完成後 VPN 當備援 | 不讓遷移時程被專線卡住 | 第 8、51 章 |
| C-252 | 逐步取代 monolith、降低風險、可回滾 | Strangler fig + ALB path-based routing 或 API Gateway | 漸進替換、價值提早出現 | 第 46 章 |
| C-253 | 舊系統不能修改，但要延伸新功能 | 從資料庫 CDC 或事件延伸（DMS → Kinesis、EventBridge） | 不碰舊程式也能取得變更 | 第 46 章 |
| C-254 | 寫入資料庫並可靠地發事件、不能遺失 | Transactional outbox、DynamoDB Streams、DMS CDC | 直接雙寫中途失敗會不一致 | 第 33、46 章 |
| C-255 | COBOL 大型主機轉 Java | AWS Mainframe Modernization（Blu Age 自動 refactor） | MGN 不能搬大型主機 | 第 45 章 |
| C-256 | 遷移後最快的省錢手段 | 先 rightsizing 再買 Savings Plans；退役閒置資源 | 規格未穩定前不要買三年承諾 | 第 39、51 章 |

---

## 最佳化目標字眼：每個字眼把答案推向哪裡

題目的最後一句通常是一個最佳化目標，它決定「在所有能用的方案中選哪一個」。先用硬性限制（RTO／RPO、合規、不能改程式、時程）刪掉做不到的選項，再用最佳化目標在剩下的選項中挑一個。

| 題目字眼 | 解題傾向 | 通常會淘汰 | 章 |
|---|---|---|---|
| MOST cost-effective／LOWEST cost | 在**滿足所有硬條件**的選項中挑最便宜的；常見答案是合適的計價模式、儲存分層、只在需要時運行、VPC endpoint 取代 NAT | 為尖峰常態超配、過度備援；但也淘汰「便宜卻違反 RTO 或可用性」的選項 | 第 1、39、54 章 |
| LEAST operational overhead／LEAST management effort | 受管服務、serverless、AWS 原生整合（Fargate、DynamoDB、SQS、Control Tower、GuardDuty） | 自建 EC2、需要 patch 的軟體、自寫腳本與 cron | 第 1、21、46、54 章 |
| MOST secure／MOST secure way | 最小權限 IAM role、private 網路與 VPC endpoint、加密與 customer managed key、明確 Deny 與預防控制 | 長期 access key、公開存取、寬鬆規則、只靠單一層控制 | 第 1、12、15、54 章 |
| LEAST privilege | 精確的 Action 與 Resource、條件鍵（`aws:SourceVpce`、`aws:PrincipalOrgID`）、permissions boundary、ABAC | `"*"`、AdministratorAccess、共用身份 | 第 12、13 章 |
| highly available／fault tolerant | 跨至少兩個 AZ、多副本、自動 failover、每 AZ 預留容量 | 單一 instance、單一 AZ、換更大的單台機器 | 第 2、18、34、54 章 |
| MOST resilient／survive a Region failure | 依 RTO／RPO 選 DR 策略；資料層跨 Region 複寫，並備妥金鑰、密碼、AMI 與 quota | 把 Multi-AZ 當 DR；題目沒要求 Region 級容錯時，也淘汰多 Region 方案 | 第 34、53、54 章 |
| minimize data loss／RPO of N | 同步複寫（Multi-AZ）或持續複寫（Aurora Global、DRS）；RPO 寬鬆時用備份 | RPO 不達標的備份週期 | 第 26、34 章 |
| minimize downtime／minimal downtime | 持續複寫後切換：DMS full load + CDC、MGN、blue/green、提前降 TTL | 停機匯出匯入、只做 full load | 第 37、45 章 |
| as quickly as possible／fastest migration | 不需要重新設計的方案（rehost、基礎設施層設定） | Refactor、重寫成微服務 | 第 1、44 章 |
| without modifying the application／minimal code changes | 基礎設施層方案：ALB authenticate、Amazon MQ、DAX、RDS Proxy、Babelfish | 需要改用新 SDK 或重寫邏輯的選項 | 第 1、10、29、46 章 |
| LOWEST latency／best performance | 縮短距離（CloudFront、Global Accelerator、就近 Region）、快取（ElastiCache、DAX）、合適的儲存效能等級 | 只加大頻寬或只換更大的 instance | 第 3、11、28 章 |
| real-time vs near real-time | Real-time → Kinesis Data Streams、Flink；near real-time → Data Firehose（有 buffer） | 把 Firehose 用在毫秒級需求 | 第 31、52 章 |
| scalable／handle unpredictable traffic | 水平擴展且 stateless、on-demand 計價、queue 削峰、serverless | 固定容量、需要預先擴容的單一節點 | 第 18、27、35 章 |
| loosely coupled／decouple | SQS、SNS fan-out、EventBridge、Step Functions | 加長逾時、同步呼叫鏈、同步重試 | 第 32、33、54 章 |
| comply with regulations／data residency | 選定 Region 並以 SCP 限制、Object Lock compliance、Vault Lock、組織層日誌 | 跨境複寫、governance mode、只靠 IAM 限制刪除 | 第 14、40、42、43、50 章 |
| durable／must not lose | 先寫入持久儲存（SQS、資料庫、S3）再處理；MemoryDB 取代純快取 | 把 ElastiCache 或記憶體當唯一存放處 | 第 28、32 章 |
| Choose two／Choose three | 每個選項獨立判斷是否正確；選出的組合要涵蓋題目的每一項需求，不要選兩個解決同一件事的選項 | 互相重複、漏掉某項需求的組合 | 第 1 章 |

### 兩個目標同時出現時

題目常把兩個目標放在一起，例如「highly available and cost-effective」或「most secure with least operational overhead」。處理方式是分主次：

1. **硬性的先滿足**：可用性、RTO／RPO、合規、時程通常是硬條件，不滿足就直接淘汰。
2. **再用另一個目標比較**：在都符合硬條件的選項中，挑最便宜或營運負擔最低的那一個。
3. **安全與營運負擔衝突時**：沒有「必須單一租戶 HSM」這類明確要求時，選受管的安全服務（例如 KMS 優先於 CloudHSM）。
4. **受管與控制權衝突時**：只有題目明確說出受管服務做不到的限制（例如需要 OS 存取），才選自管或 RDS Custom。

> [!warning] 常見誤解
> 「MOST cost-effective 就是選全場最便宜的選項。」不是。最便宜的選項常常違反一個藏在情境中的限制（單一 AZ、RPO 不達標、需要改程式）。先刪掉做不到的，再比價。
