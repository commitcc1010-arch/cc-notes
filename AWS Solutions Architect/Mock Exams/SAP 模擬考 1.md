---
title: SAP 模擬考 1
exam: SAP-C02
---

# SAP 模擬考 1

> [!abstract] 作答說明
> **題數**：75 題（D1 20 題、D2 22 題、D3 19 題、D4 14 題），題型與比重對齊 SAP-C02。真實考試 75 題中有 10 題不計分，但你無法分辨是哪 10 題，所以每題都要認真作答。
> **建議時間**：180 分鐘，一次坐完，中間不休息。平均每題約 2 分 20 秒；題幹長的題目先讀最後一句「問什麼」與最佳化目標（MOST cost-effective、LEAST operational overhead…），再回頭讀限制。
> **及格參考**：真實考試以 100–1000 分計，750 分及格，分數經過等化，不等於答對率。自我評估時，答對 56 題（約 75%）以上可視為接近及格，答對 63 題以上表示準備充足。
> **作答方式**：先在紙上或試算表寫下 75 題的答案，全部作答完才展開 `答案` 區塊對答案。多選題必須全部選對才算分。
> **錯題記錄**：每錯一題，記下「題號、我選的答案、正確答案、我忽略的關鍵限制、對應章節」。最後用「答案速查與 Domain 分析」的表格找出錯題集中的 domain 與章節，優先複習。
> **情境說明**：本回情境以金融保險、零售、製造與媒體產業為主，所有公司皆為虛構。

## 題目

### 第 1 題｜SAP｜單選｜D1 兩個 IdP 的集中登入

一家保險集團旗下有壽險與產險兩家子公司，共用一個 AWS Organization，裡面有 120 個帳號。壽險員工的身份在 Microsoft Entra ID，產險員工的身份在 Okta；目前兩邊各自用 IAM SAML federation 直接登入每一個帳號，每個帳號都要維護 SAML provider 與一組 IAM role。集團資安要求：所有員工使用同一個 AWS 登入入口、以群組統一指派各帳號權限、使用者與群組要自動佈建（provisioning），員工在原本 IdP 被停用後就不能再取得任何帳號的新 session。兩個 IdP 的整併計畫要兩年後才會啟動，在那之前兩邊員工仍要用各自原本的 IdP 認證。

哪個方案能以最少的營運負擔滿足需求？

- A. 在 management account 啟用 IAM Identity Center 的 organization instance，同時把 Entra ID 與 Okta 設為兩個 external identity provider，分別以 SCIM 同步使用者與群組，再以 permission set 指派各帳號權限
- B. 在 IAM Identity Center 的 organization instance 中把 Okta 設為唯一的 external identity provider 並啟用 SCIM；在 Okta 設定以 Entra ID 為上游 IdP 的 inbound federation，並把壽險員工同步進 Okta，再以群組指派 permission set
- C. 為壽險與產險各啟用一個 IAM Identity Center account instance，各自連接自己的 IdP 並以 SCIM 同步，再在每個 account instance 中建立 permission set 指派到對應子公司的帳號
- D. 保留 IAM SAML federation，改用 CloudFormation StackSets 把兩個 SAML provider 與標準化 role 自動部署到所有帳號，並在兩個 IdP 中各自建立對應 role 的群組

> [!answer]- 答案：B
> **A ✗** IAM Identity Center 的 organization instance 一次只能連接一個 identity source（Identity Center directory、Active Directory 或一個 external IdP 三選一），無法同時接兩個 external IdP。這是本題最常被誤選的選項。
>
> **B ✓** 既然 identity source 只能有一個，標準做法是選一個 IdP 當「樞紐」，讓另一個 IdP 透過 inbound federation 接到它。壽險員工仍在 Entra ID 輸入密碼與 MFA，但對 AWS 而言所有人都來自 Okta，SCIM 自動佈建與 permission set 的群組指派都只要管一套。員工在 Entra ID 被停用後無法再完成認證，也就無法取得新的 session。
>
> **C ✗** Account instance 是給單一帳號內的應用程式（例如某些 AWS 受管應用）使用的，不能用來指派多帳號的 AWS account access；permission set 指派多帳號只能在 organization instance 做。
>
> **D ✗** StackSets 能減少部署工作，但仍然是每個帳號各自一套 SAML 信任，沒有統一入口、沒有 SCIM 自動佈建，權限變更要改 role 與 IdP 群組兩邊。若公司因故不能使用 Identity Center，這會是退而求其次的做法。
>
> **考點**：SAP-1.4｜Identity Center 只能有一個 identity source，多 IdP 要先在 IdP 層整合｜延伸閱讀：第 13、40 章

### 第 2 題｜SAP｜單選｜D2 Serverless API 的自動回滾部署

一家產物保險公司的理賠 API 由 API Gateway REST API 與 40 個 Lambda function 組成，以 AWS SAM 管理，每週部署約 30 次。上個月一次有 bug 的部署讓理賠查詢錯誤率飆升，值班工程師花了 20 分鐘才手動回滾。管理層要求：新版本先只承接一小部分流量，觀察一段時間後再全量；若錯誤率或延遲異常要自動回滾，不能靠人判斷；不要複製一整套基礎設施，也不要增加 DNS 層的變更。

哪個做法最能滿足需求？

- A. 在 API Gateway stage 啟用 canary release，把 10% 流量導到新部署，由值班工程師觀察 CloudWatch dashboard 後手動 promote 或刪除 canary
- B. 每次部署都建立一套新的 green stack，以 Route 53 weighted record 先導 10% 流量到新 stack，觀察一小時後再調整權重
- C. 以部署腳本把 Lambda alias 的 weighted routing 設為新版本 10%，同時建立 CloudWatch alarm，在錯誤率超標時發 SNS 通知值班工程師回滾
- D. 在 SAM template 為每個 function 設定 `AutoPublishAlias` 與 `DeploymentPreference`（例如 `Canary10Percent10Minutes`），並把錯誤率與延遲的 CloudWatch alarm 列入 `Alarms`，必要時加上 pre-traffic hook 做煙霧測試

> [!answer]- 答案：D
> **A ✗** API Gateway canary 能分流，但升級與回滾都是手動，違反「不能靠人判斷」。若團隊只想在 API 層做簡單的分流驗證、可接受手動決策，它才合適。
>
> **B ✗** 每次都建一整套 green stack 違反「不要複製基礎設施」，而且 DNS 權重受 resolver 快取影響，分流比例與回滾速度都不精確。
>
> **C ✗** Alias weighted routing 本身就是 Lambda canary 的機制，但這裡的回滾仍靠人收到通知後處理，沒有自動化。
>
> **D ✓** SAM 的 `DeploymentPreference` 會讓 CodeDeploy 管理 Lambda alias 的流量移轉：先把 10% 流量給新版本，等待 10 分鐘，期間任一列出的 alarm 進入 ALARM 就自動把 alias 指回舊版本。pre-traffic hook 還能在導流前先跑驗證。全程不需要新基礎設施也不需要 DNS 變更。
>
> **考點**：SAP-2.1｜CodeDeploy 管理 Lambda alias 的 canary 與 alarm 自動回滾｜延伸閱讀：第 19、37 章

### 第 3 題｜SAP｜單選｜D4 機房到期前的應用組合決策

一家連鎖零售商的資料中心租約 10 個月後到期，無法延長。盤點結果有 420 個應用程式：60 個近 6 個月沒有任何登入紀錄；35 個是商用套裝軟體，原廠已宣布明年停止支援地端版本、只提供 SaaS 版；約 200 個是標準的 Linux／Windows 三層式應用；另外有一套跑在 IBM i（AS/400）上的庫存核心系統，公司已核准一個 3 年的現代化專案來改寫它。CIO 要求準時撤出機房、降低遷移風險，且不能讓任何遷移工作卡在長期改寫專案上。

哪個處置方案最合適？

- A. 退役 60 個閒置應用、35 個改買 SaaS；200 個三層式應用先在地端容器化並重構成微服務再搬上 AWS，避免搬兩次；IBM i 系統移到託管機房
- B. 退役 60 個閒置應用、35 個改買 SaaS；其餘 200 個應用與 IBM i 庫存系統全部以 AWS Application Migration Service（MGN）rehost 到 EC2
- C. 與業主確認後退役 60 個閒置應用、35 個改買 SaaS 版本；200 個三層式應用以 MGN 分 wave rehost，上雲後再逐步最佳化；IBM i 系統移到具備 Direct Connect 的託管機房保留運作，直到現代化專案完成
- D. 退役 60 個閒置應用、35 個改買 SaaS；200 個三層式應用全部 replatform 到 Elastic Beanstalk；IBM i 系統因為無法遷移，直接退役並以 SaaS 庫存系統取代

> [!answer]- 答案：C
> **A ✗** 在 10 個月內把 200 個應用重構成微服務，時程與風險都不可行；「先重構再搬」正是讓機房撤出卡在長期專案上的典型錯誤。
>
> **B ✗** MGN 複寫的是 x86 伺服器（Windows／Linux）的區塊層資料，IBM i 跑在 Power 架構上，無法用 MGN rehost 到 EC2。
>
> **C ✓** 每類應用各配一個合適的 R：閒置系統 retire（先和業主確認，避免誤殺）、原廠只剩 SaaS 的 repurchase、標準應用 rehost 以最快速度撤出機房，之後再最佳化；IBM i 無法短期上雲，就 retain：搬到具備 Direct Connect 的託管機房繼續運作並以 hybrid 網路連回 AWS，由現代化專案自己的時程處理。注意 7Rs 中的 relocate 指的是把 VMware 等虛擬化環境整批搬到雲端（例如 VMware Cloud on AWS），不是搬到另一個機房。
>
> **D ✗** 把 200 個應用全部 replatform 到 Beanstalk 需要逐一調整部署方式，工作量遠大於 rehost；而且直接退役核心庫存系統、臨時改用 SaaS 會造成重大業務風險，和已核准的現代化專案也衝突。
>
> **考點**：SAP-4.1｜依限制選擇 7Rs：retire、repurchase、rehost、retain｜延伸閱讀：第 44 章

### 第 4 題｜SAP｜選兩項｜D3 全組織的危險 security group 自動修正

一家銀行在 AWS Organizations 中有 85 個帳號，使用 3 個 Region。稽核發現各團隊反覆建立允許 `0.0.0.0/0` 存取 TCP 22 與 3389 的 security group 規則；目前資安團隊每週用自寫腳本掃描一次，再開工單要求團隊修正，常常拖上好幾天。新要求：所有帳號與 Region 中這類規則要在數分鐘內被偵測並自動移除；資安團隊要在 Security 帳號看到全組織的合規狀態；盡量不寫自訂程式碼。

哪兩個步驟組合起來能滿足需求？

- A. 從擔任 AWS Config delegated administrator 的 Security 帳號部署 organization conformance pack，內含 `restricted-ssh` 與 `restricted-common-ports` 等 managed rule，並設定以 SSM Automation runbook `AWS-DisablePublicAccessForSecurityGroup` 做自動修正
- B. 在組織 root 掛一個 SCP，拒絕所有帳號呼叫 `ec2:AuthorizeSecurityGroupIngress`，只有資安團隊的 role 例外
- C. 在所有帳號啟用 Amazon GuardDuty，並以 EventBridge 規則接收「security group 對外開放」的 finding，觸發 Lambda 刪除規則
- D. 在 Security 帳號建立涵蓋整個組織與所有 Region 的 AWS Config aggregator，集中檢視各帳號的規則合規狀態
- E. 建立 organization trail 並把 CloudTrail 日誌送到 S3，每週以 Athena 查詢 `AuthorizeSecurityGroupIngress` 事件並產生報表

> [!answer]- 答案：A、D
> **A ✓** Config managed rule 在 security group 變更時觸發評估，幾分鐘內就能標記為 NONCOMPLIANT；conformance pack 可以連同 remediation 設定一起部署到整個組織。AWS 提供的 `AWS-DisablePublicAccessForSecurityGroup` runbook 會移除對 0.0.0.0/0 開放 22 與 3389 的規則，不需要自寫程式。
>
> **B ✗** SCP 沒有能檢查 ingress 規則 CIDR 的 condition key，只能整個拒絕 API，會讓所有團隊都無法管理自己的 security group，業務無法運作。
>
> **C ✗** GuardDuty 偵測的是威脅行為（例如可疑 API 呼叫、惡意 IP 通訊），不是設定是否合規，它不會為「security group 開放 22」產生 finding。
>
> **D ✓** Aggregator 把所有帳號、所有 Region 的 Config 評估結果彙整到 Security 帳號，滿足「集中看到全組織合規狀態」。
>
> **E ✗** 每週查詢 CloudTrail 只能事後產生報表，偵測延遲與現況相同，也沒有自動修正。若需求是「調查誰在何時建立了規則」，CloudTrail 才是正確工具。
>
> **考點**：SAP-3.1｜Config rule + SSM Automation 自動修正，aggregator 集中合規視圖｜延伸閱讀：第 38、40 章

### 第 5 題｜SAP｜單選｜D1 把 SD-WAN 延伸進 AWS

一家汽車零件製造商有 45 座工廠，全部以某家廠商的 SD-WAN 設備連到兩個區域 hub；兩個 hub 各有一條 10 Gbps Direct Connect，經 transit VIF、Direct Connect gateway 接到 us-east-1 的 Transit Gateway，後面接了 30 個 VPC。目前做法是在一個 transit VPC 跑 SD-WAN 虛擬設備，再從每台設備建 Site-to-Site VPN 到 Transit Gateway；IPsec 每條 tunnel 的頻寬上限讓大流量工廠必須維護大量 tunnel 與 ECMP。網路團隊希望：讓 SD-WAN 網路以 BGP 動態交換路由到 Transit Gateway、單一設備可用的頻寬高於 IPsec tunnel、不必再管理大量 VPN tunnel。

哪個方案最合適？

- A. 保留 transit VPC 中的 SD-WAN 虛擬設備，在 Transit Gateway 建立以該 VPC attachment 為傳輸層的 Transit Gateway Connect attachment，讓設備與 Transit Gateway 之間以 GRE tunnel 加 BGP 交換路由
- B. 把所有 VPN 改成 accelerated Site-to-Site VPN，並在每台 SD-WAN 設備增加 tunnel 數量，以 ECMP 聚合頻寬
- C. 把 transit VPC 與 30 個 VPC 建立 VPC peering，在每個 VPC 的 route table 把工廠網段指向 SD-WAN 設備的 ENI
- D. 在 transit VPC 部署 Gateway Load Balancer，把 SD-WAN 設備註冊為 target，再於 30 個 VPC 建立 GWLB endpoint 導流

> [!answer]- 答案：A
> **A ✓** Transit Gateway Connect 是為 SD-WAN 設備設計的 attachment 類型：它建立在既有的 VPC 或 Direct Connect attachment 之上，用 GRE 封裝搭配 BGP 動態路由，不需要 IPsec，所以單一 Connect peer 的頻寬比 VPN tunnel 高，也不必維護大量 tunnel。
>
> **B ✗** Accelerated VPN 改善的是經 Internet 的路徑品質，仍是 IPsec tunnel，每條 tunnel 頻寬上限不變，tunnel 數量反而更多，正好違反需求。
>
> **C ✗** VPC peering 不支援 transitive routing，其他 VPC 不能經由 peering 再透過 transit VPC 的設備轉送到工廠，而且 30 條 peering 與靜態路由的維護負擔很大。
>
> **D ✗** GWLB 用來把流量透明地送進檢查設備（防火牆、IDS），不和設備交換 BGP 路由，無法讓 SD-WAN 把工廠路由動態帶進 AWS。
>
> **考點**：SAP-1.1｜Transit Gateway Connect：GRE + BGP 整合 SD-WAN｜延伸閱讀：第 7、41 章

### 第 6 題｜SAP｜單選｜D2 跨 Region DR 的策略選擇

一家線上零售商的購物網站在 us-east-1 執行：ALB 後面是 12 台 EC2 組成的 Auto Scaling group，資料庫是 8 TB 的 Aurora MySQL。一次 Region 等級事件後，董事會要求 Region 故障時 RPO 不超過 1 分鐘、RTO 不超過 30 分鐘，DR Region 為 us-west-2。財務要求 DR 成本盡量低；維運團隊不想自己維護資料複寫腳本。

哪個方案以最低成本滿足需求？

- A. 在 us-west-2 建立完整的 active-active 環境，Aurora 使用 Global Database 並啟用 write forwarding，兩個 Region 都維持 12 台 EC2，以 Route 53 latency routing 分流
- B. 以 AWS Backup 每小時把 Aurora snapshot 與 AMI 複製到 us-west-2，災難時用 CloudFormation 建立 VPC、ALB、Auto Scaling group 並從 snapshot 還原資料庫
- C. 為 Aurora 建立 Global Database，在 us-west-2 的 secondary cluster 保留一個較小的 instance；預先以 IaC 建好 us-west-2 的網路、ALB 與 desired capacity 為 0 的 Auto Scaling group，並複製 AMI；災難時 failover Global Database、擴充 Auto Scaling group，再切換 Route 53 failover record
- D. 在 us-west-2 建立 AWS DMS replication instance，以 CDC 把 Aurora 持續複寫到一個 RDS for MySQL，災難時再把 RDS for MySQL 遷移到 Aurora，並以 CloudFormation 建立應用層

> [!answer]- 答案：C
> **A ✗** Active-active 當然能滿足 RPO／RTO，但兩邊都跑全量運算與資料庫，是最貴的選項，超出需求。若需求是 RTO 接近 0 或要就近服務兩地使用者，才值得這樣做。
>
> **B ✗** 每小時一次的 snapshot 代表 RPO 最壞約 1 小時；從 8 TB snapshot 還原 Aurora 加上建立整個環境，也很難在 30 分鐘內完成。
>
> **C ✓** Aurora Global Database 以儲存層複寫到 secondary Region，延遲通常在 1 秒內，滿足 RPO 1 分鐘，且不需要自己維護複寫。應用層只預先部署便宜的部分（網路、ALB、AMI、容量為 0 的 ASG），災難時擴充即可，介於 pilot light 與 warm standby 之間，是成本與 RTO 的平衡點。
>
> **D ✗** DMS 需要維運 replication instance 與 task，違反「不想維護複寫」；災難當下才把 RDS for MySQL 轉成 Aurora 會讓 RTO 遠超過 30 分鐘。
>
> **考點**：SAP-2.2｜依 RPO／RTO 與成本選 DR 策略，Aurora Global Database｜延伸閱讀：第 26、34 章

### 第 7 題｜SAP｜單選｜D3 報表查詢拖慢線上讀取

一家電商的 Aurora PostgreSQL cluster 有 1 個 writer 與 4 個相同規格的 Aurora Replica，購物網站的商品與訂單查詢都透過 reader endpoint。商品企劃團隊上班時間會跑大量長時間的分析報表，同樣連到 reader endpoint，導致結帳頁面的讀取延遲在白天出現尖峰。報表 SQL 大量使用 PostgreSQL extension，今年預算不允許導入新的分析平台或 ETL 管線，團隊希望用最少的變更隔離兩種工作負載。

哪個做法最合適？

- A. 把 writer instance 升級到更大的規格，並讓報表改連 cluster（writer）endpoint，以 writer 的剩餘資源執行報表
- B. 新增兩個記憶體較大的 Aurora Replica 並把 failover priority 設為最低，建立只包含這兩個 replica 的 custom endpoint 給報表使用，另建一個只包含原本 4 個 replica 的 custom endpoint 給購物網站
- C. 為 Aurora Replica 啟用 Aurora Auto Scaling，以 reader 的平均 CPU 為目標值自動增加 replica，讓報表與線上查詢共用更多 reader
- D. 建立 Aurora 到 Amazon Redshift 的 zero-ETL integration，把報表改寫到 Redshift 執行，Aurora reader 只服務線上查詢

> [!answer]- 答案：B
> **A ✗** 把重報表丟給 writer 會和線上寫入（下單、付款）搶資源，風險比現在更高。
>
> **B ✓** Custom endpoint 讓你自訂一組 instance 做為連線目標，可以把報表與線上流量分到不同的 replica 群組。購物網站也必須改用不含報表 replica 的 custom endpoint，因為預設 reader endpoint 會把連線分散到所有 replica。報表 replica 的 failover priority 設低，避免 writer 故障時被升級成 writer。
>
> **C ✗** Auto Scaling 增加的 replica 仍在同一個 reader endpoint 後面，報表照樣會打到線上用的 replica，只是被稀釋，沒有隔離。
>
> **D ✗** zero-ETL 不需要自己維護管線，但需要新增 Redshift，違反「不導入新分析平台」；報表依賴 PostgreSQL extension，搬到 Redshift 也要改寫。若預算允許且分析量持續成長，D 會是長期較好的方向。
>
> **考點**：SAP-3.3｜Aurora custom endpoint 隔離分析與線上讀取｜延伸閱讀：第 26 章

### 第 8 題｜SAP｜單選｜D2 金鑰必須留在自家機房

一家歐洲銀行要把客戶資料系統搬到 AWS，資料存放於 S3、EBS 與 RDS。主管機關要求：加密客戶資料的金鑰必須在銀行自有、位於自家資料中心的 HSM 中產生與保存，金鑰材料不得存在雲端供應商的環境中；銀行必須能隨時切斷雲端服務對金鑰的使用。同時，應用團隊希望繼續使用各 AWS 服務原生整合的 server-side encryption，不想自行在應用層加解密。

哪個方案能滿足需求？

- A. 建立 AWS KMS external key store（XKS），透過銀行部署的 XKS proxy 連接自家資料中心的外部金鑰管理器，在其中建立 KMS key，並在 S3、EBS 與 RDS 指定使用這些 key
- B. 建立 AWS CloudHSM cluster 並設定為 KMS custom key store，在其中建立 KMS key，供 S3、EBS 與 RDS 加密使用
- C. 在自家 HSM 產生金鑰材料後匯入（import）KMS，建立 key material origin 為 EXTERNAL 的 KMS key，需要切斷時刪除匯入的金鑰材料
- D. 在應用程式中使用銀行 HSM 的 SDK 做 client-side encryption，資料加密後再寫入 S3、EBS 與 RDS

> [!answer]- 答案：A
> **A ✓** XKS 讓 KMS key 的金鑰材料留在 AWS 之外由客戶管理的金鑰管理器中，KMS 每次加解密都要透過 XKS proxy 向外部系統請求，因此銀行切斷 proxy 後，KMS 就無法再解密任何以這些 key 保護的資料金鑰（少數服務會短暫快取 data key，例如已掛載的 EBS volume，要等資源停用或快取過期才會失效）。各服務照常透過 KMS 整合，不需要改應用。代價是延遲與可用性取決於銀行自己的 proxy 與連線，必須做好高可用。
>
> **B ✗** CloudHSM 是位於 AWS 內、由客戶獨占的 HSM，金鑰材料仍在 AWS 環境中，不符合「必須在自家資料中心」。若法規只要求單一租戶、FIPS 140 Level 3 的 HSM 與客戶獨占控制，B 才會是答案。
>
> **C ✗** BYOK 匯入後，金鑰材料的副本會存在 KMS 內，只是產生在外部；不符合「不得存在雲端環境」。它適合只要求「金鑰由自己產生、能立即刪除」的情境。
>
> **D ✗** Client-side encryption 能讓金鑰留在地端，但 EBS 與 RDS 的儲存加密無法由應用層取代，而且違反「不想自行加解密」。
>
> **考點**：SAP-2.3｜KMS external key store、custom key store 與 BYOK 的差異｜延伸閱讀：第 15 章

### 第 9 題｜SAP｜單選｜D1 防止 snapshot 與 AMI 被公開分享

一家保險公司在 AWS Organizations 中有 200 個帳號，分布在 4 個 Region，且每月持續新增帳號。過去一年發生兩次工程師為了分享給外部廠商，把含有保戶資料的 EBS snapshot 與 AMI 設成公開的事件。資安要求：所有帳號與 Region（包含未來新增的帳號）都不能公開分享 snapshot 與 AMI，成員帳號的管理員也不能自行關閉這項保護；但分享給特定廠商帳號 ID 仍必須可行；持續維護的負擔要最低。

哪個方案最合適？

- A. 在組織 root 掛 SCP，拒絕 `ec2:ModifySnapshotAttribute` 與 `ec2:ModifyImageAttribute`，只允許資安團隊的 role 例外
- B. 以 organization conformance pack 部署 `ebs-snapshot-public-restorable-check` 等 Config rule，偵測到公開時以 SSM Automation 自動把權限改回私有
- C. 以 CloudFormation StackSets 在每個帳號、每個 Region 啟用 EBS snapshot block public access 與 AMI block public access，並設定自動部署到新帳號
- D. 在組織 root 掛一個 EC2 的 declarative policy，設定 snapshot block public access 為封鎖所有公開分享，並啟用 image block public access

> [!answer]- 答案：D
> **A ✗** 拒絕這兩個 API 會連「分享給特定帳號 ID」也一起擋掉，違反仍需分享給廠商的需求，且每次分享都要找資安團隊代勞。
>
> **B ✗** Config 是偵測後修正，從公開到被修正之間仍有暴露時間窗；對含個資的 snapshot 來說，幾分鐘的公開就可能被複製。
>
> **C ✗** 帳號層級的 block public access 設定可以達到效果，但它是成員帳號自己可以修改的設定，管理員能再關掉；每個 Region 都要個別管理，維護負擔也較高。
>
> **D ✓** Declarative policy 是 Organizations 的政策類型，可以在組織、OU 或帳號層級宣告 EC2 等服務的設定狀態（例如 snapshot 與 AMI 的 block public access、IMDS 預設值），由服務本身強制執行，成員帳號無法覆寫，新帳號與新 Region 也自動套用。它只封鎖「公開」，分享給指定帳號 ID 不受影響。
>
> **考點**：SAP-1.2｜Organizations declarative policy 強制 EC2 服務設定｜延伸閱讀：第 14、16 章

### 第 10 題｜SAP｜選兩項｜D4 Oracle 到 Aurora PostgreSQL 的最小停機遷移

一家銀行要把地端 Oracle 19c 的貸款服務資料庫（12 TB，OLTP，包含約 300 個 PL/SQL package）遷移到 Aurora PostgreSQL，以擺脫 Oracle 授權。業務只核准週日凌晨 2 小時的切換窗口；地端與 AWS 之間有 10 Gbps Direct Connect。DBA 團隊熟悉 Oracle，但沒有大規模轉換 PL/SQL 的經驗。

哪兩個步驟是這次遷移必要的做法？

- A. 以 AWS DMS 的 full load 任務在切換窗口開始時停止應用程式，重新完整載入 12 TB 資料後切換
- B. 以 AWS DMS Schema Conversion（或 AWS SCT）轉換 schema 與 PL/SQL，檢視評估報告中無法自動轉換的項目，在資料遷移前由開發人員改寫並測試
- C. 以 Oracle Data Pump 匯出資料，經 Direct Connect 傳到 S3，再以 Data Pump 匯入 Aurora PostgreSQL
- D. 以 AWS Application Migration Service 複寫 Oracle 伺服器到 EC2，切換後再於 EC2 上把 Oracle 升級為 PostgreSQL
- E. 在來源 Oracle 啟用 ARCHIVELOG 與 supplemental logging，建立 DMS full load 加 CDC 的任務並啟用資料驗證，等複寫延遲接近 0 時在窗口內切換

> [!answer]- 答案：B、E
> **A ✗** 在 2 小時內完整載入 12 TB 並建立索引不切實際，而且應用停機期間無法回退。
>
> **B ✓** 異質遷移（Oracle → PostgreSQL）最大的工作量在 schema 與程式碼轉換。DMS Schema Conversion／SCT 會自動轉換大部分物件，並列出需要人工處理的 action item；這必須在資料遷移之前完成並測試。
>
> **C ✗** Data Pump 是 Oracle 專用格式，PostgreSQL 無法匯入。它只適用於 Oracle 到 Oracle（例如 RDS for Oracle）的同質遷移。
>
> **D ✗** MGN 是 rehost 工具，只會把 Oracle 原樣搬到 EC2，不能把 Oracle「升級」成 PostgreSQL，也沒有擺脫授權。
>
> **E ✓** DMS 的 CDC 從 Oracle redo／archive log 讀取變更，因此必須啟用 ARCHIVELOG 與 supplemental logging。先 full load、再持續 CDC，切換時只要停寫、等最後的變更追上、驗證後切換連線，停機時間可以壓在窗口內。
>
> **考點**：SAP-4.2｜異質資料庫遷移：schema 轉換 + DMS full load 與 CDC｜延伸閱讀：第 45 章

### 第 11 題｜SAP｜單選｜D3 單一 AZ 的舊系統改造

一家保險公司的業務員入口網站已 rehost 到 AWS：兩台 EC2 位於同一個 AZ、放在 ALB 後面並啟用 sticky session，session 存在 web server 記憶體；MySQL 自行安裝在第三台 EC2 上，每晚以 mysqldump 備份到 S3。最近一次 AZ 事件造成 6 小時停擺。新要求：單一 AZ 故障時自動恢復服務、資料 RPO 接近 0、任一台 web server 故障時業務員不會被登出；6 週內完成，盡量少改程式，也不增加日常維運。

哪個方案最合適？

- A. 以現有 web server 建立 AMI，建立跨兩個 AZ 的 Auto Scaling group（最少 2 台）；MySQL 維持在 EC2 上，改為每小時建立 EBS snapshot 並複製到另一個 AZ
- B. 把資料庫遷移到單一 instance 的 Aurora MySQL Serverless v2；web 層改成跨兩個 AZ 的 Auto Scaling group，並保留 ALB sticky session 與記憶體內 session
- C. 把資料庫遷移到 RDS for MySQL Multi-AZ；web 層改成跨至少兩個 AZ 的 Auto Scaling group，並把 session 改存到 Multi-AZ 的 ElastiCache，利用應用框架既有的 session provider 設定切換
- D. 在第二個 Region 複製一套相同的兩台 EC2 與 MySQL 環境，以 Route 53 failover routing 在主 Region 故障時切換

> [!answer]- 答案：C
> **A ✗** Web 層變成跨 AZ，但資料庫仍是單一 AZ 的單點，每小時 snapshot 代表 RPO 最壞 1 小時，不符合接近 0。
>
> **B ✗** 單一 instance 的 Aurora 儲存層跨 3 AZ 很耐久，但 compute 沒有待命 replica，故障時要重建 instance，恢復較慢；而記憶體內 session 在 web server 故障時會遺失，業務員會被登出。
>
> **C ✓** RDS Multi-AZ 以同步複寫到另一個 AZ 的 standby，故障時自動 failover，RPO 接近 0；web 層跨 AZ 由 Auto Scaling 自動補機；session 外部化到 ElastiCache 後任何一台 web server 都能接手，業務員不會被登出。多數框架只要改 session provider 設定，程式改動很小。
>
> **D ✗** 跨 Region 的做法超出需求、成本高，而且每個 Region 內仍是單一 AZ 架構，自建 MySQL 的跨 Region 複寫也要自己維運。
>
> **考點**：SAP-3.4｜消除單點：RDS Multi-AZ、跨 AZ Auto Scaling、外部化 session｜延伸閱讀：第 18、26 章

### 第 12 題｜SAP｜選兩項｜D2 限時搶購壓垮資料庫連線

一家零售品牌的訂單 API 架構為 API Gateway → Lambda → Aurora MySQL（provisioned）。每次限時搶購，Lambda 並行數會在幾秒內衝到約 3,000，Aurora 出現 `Too many connections`，大量訂單失敗。業務可接受訂單在 2 分鐘內非同步確認，但任何已送出的訂單都不能遺失；本季預算不允許把資料庫升級到更大的規格。

哪兩個變更組合起來最能滿足需求？

- A. 讓 API Gateway 以服務整合直接把訂單寫入 SQS 並回傳 202，處理訂單的 Lambda 改由 SQS event source mapping 觸發，並設定 maximum concurrency 限制同時寫入資料庫的數量
- B. 調高 Aurora 的 `max_connections` 參數到 10,000，讓所有 Lambda 都能取得連線
- C. 在 Lambda 與 Aurora 之間加入 RDS Proxy，讓 function 共用並重複使用資料庫連線
- D. 為訂單 Lambda 設定 3,000 的 provisioned concurrency，避免冷啟動造成的連線延遲
- E. 在 Aurora 前面加一個 DynamoDB table 當寫入快取，以 TTL 定期把訂單批次寫回 Aurora

> [!answer]- 答案：A、C
> **A ✓** SQS 把瞬間尖峰轉成可控制速度的佇列：API 只負責收單並持久化到 SQS，訂單不會遺失；event source mapping 的 maximum concurrency 讓消費端以資料庫能承受的速度處理，正好符合「2 分鐘內非同步確認」。
>
> **B ✗** 每個連線都會佔用資料庫記憶體，在不升級規格的前提下硬調高 `max_connections` 會造成記憶體壓力與效能崩潰，問題只是換個形式出現。
>
> **C ✓** RDS Proxy 維護一組連線池，讓大量短命的 Lambda 共用少數資料庫連線，並能在 failover 時保持應用連線，直接解決連線數爆量。
>
> **D ✗** Provisioned concurrency 解決冷啟動，但讓 3,000 個執行環境同時存在，只會讓連線數更高。
>
> **E ✗** 自建「DynamoDB 寫入快取再回寫」需要大量自訂程式，還要處理一致性與失敗重試；SQS 已經提供持久化緩衝。
>
> **考點**：SAP-2.4｜以佇列削峰與連線池保護資料庫｜延伸閱讀：第 26、32 章

### 第 13 題｜SAP｜選三項｜D1 交易事件不可遺失的 Kafka 設定

一家證券公司以 Amazon MSK（provisioned）承載交易事件，叢集有 6 個 broker 平均分布在 3 個 AZ。目前 topic 的 replication factor 為 2、`min.insync.replicas` 為 1，producer 使用 `acks=1`。風控要求：producer 收到確認的訊息，即使整個 AZ 故障也不能遺失；單一 broker 維護或故障時 producer 仍能持續寫入；同一帳戶的事件必須維持順序。

哪三個變更組合起來能滿足需求？

- A. 把每個 topic 的 partition 數量增加為目前的三倍，分散寫入負載
- B. 把 topic 的 replication factor 設為 3，讓 MSK 把副本分布在 3 個 AZ 的 broker 上
- C. 啟用 `unclean.leader.election.enable=true`，讓 leader 故障時能更快選出新 leader
- D. 把 `min.insync.replicas` 設為 2
- E. 為叢集啟用 tiered storage，把舊資料移到較便宜的儲存層
- F. Producer 改用 `acks=all` 並啟用 idempotent producer，且以帳戶 ID 作為訊息 key

> [!answer]- 答案：B、D、F
> **A ✗** Partition 數量影響平行度與吞吐量，與「已確認訊息是否會遺失」無關；而且改變 partition 數量會改變 key 對應的 partition，反而可能打亂順序。
>
> **B ✓** Replication factor 3 讓每個 partition 在 3 個 AZ 各有一份副本，任一 AZ 故障仍有兩份。
>
> **C ✗** Unclean leader election 允許不在 ISR（in-sync replicas）中的落後副本成為 leader，會遺失已確認的訊息，正好違反需求。Kafka 預設是關閉的。
>
> **D ✓** `min.insync.replicas=2` 搭配 `acks=all` 表示至少兩份副本寫入成功才確認；RF 3 時，一個 broker（或一個 AZ）不可用仍有兩份 in-sync，producer 可以繼續寫入。
>
> **E ✗** Tiered storage 降低長期保存成本，不影響寫入確認的耐久性。
>
> **F ✓** `acks=all` 讓 producer 等所有 in-sync 副本確認；idempotent producer 避免重試造成重複或亂序；以帳戶 ID 當 key 讓同帳戶事件進入同一個 partition，保持順序。
>
> **考點**：SAP-1.3｜Kafka 耐久性三件組：RF 3、min.insync.replicas 2、acks=all｜延伸閱讀：第 31 章

### 第 14 題｜SAP｜單選｜D2 風險運算網格上雲

一家銀行每晚在地端以約 3,000 個核心執行 Monte Carlo 風險值（VaR）計算，現在要搬到 AWS。輸入的市場資料共 40 TB，放在 S3；每個計算任務都會反覆讀取同一批檔案，需要很高的總讀取吞吐量。整批計算必須在 4 小時窗口內完成；任務彼此獨立、失敗可以重跑。財務希望運算成本盡量低。

哪個架構最合適？

- A. 把市場資料複製到 Amazon EFS（General Purpose、Bursting throughput），以 On-Demand EC2 叢集掛載 EFS 執行計算
- B. 建立連結 S3 資料儲存庫的 Amazon FSx for Lustre 檔案系統，以 AWS Batch 或 AWS ParallelCluster 在多種 instance type 的 EC2 Spot 上執行計算並掛載該檔案系統
- C. 每台計算 instance 開機時把整份 40 TB 市場資料從 S3 下載到本機 gp3 EBS，以 On-Demand instance 確保計算期間不中斷
- D. 建立 EBS io2 Block Express volume 並啟用 Multi-Attach，讓所有計算 instance 同時掛載這個 volume 讀取市場資料

> [!answer]- 答案：B
> **A ✗** EFS 能共享，但 Bursting 模式的吞吐量隨儲存量與 burst credit 變化，數千核心同時大量讀取時容易成為瓶頸；On-Demand 也沒有利用任務可重跑的特性降低成本。
>
> **B ✓** FSx for Lustre 是為 HPC 設計的平行檔案系統，可提供極高的總吞吐量與低延遲；連結 S3 後可以延遲載入（lazy load）資料，不必事先完整複製。任務獨立可重跑，非常適合多 instance type 分散的 Spot，大幅降低成本。
>
> **C ✗** 每台 instance 都下載 40 TB 會耗費大量時間與本機儲存，計算還沒開始窗口就用掉了。
>
> **D ✗** EBS Multi-Attach 只能掛到同一個 AZ 內最多 16 台 Nitro instance，而且需要叢集感知的檔案系統才能安全共用，無法支撐數千核心。
>
> **考點**：SAP-2.5｜HPC：FSx for Lustre + S3 data repository + Spot｜延伸閱讀：第 17、24 章

### 第 15 題｜SAP｜單選｜D3 地端伺服器的長期金鑰

一家精密零件製造商在各工廠有 150 台地端 Linux 伺服器，負責把品檢影像上傳到 S3 並傳送訊息到 SQS。這些伺服器目前使用 IAM user 的 access key，寫在設定檔裡，從未輪替；上個月有一組 key 隨著 USB 隨身碟外流。公司已有內部 PKI，每台伺服器都有由內部 CA 簽發的裝置憑證。資安要求：消除長期憑證、改用短期憑證、能個別撤銷某台伺服器的存取，且應用程式改動要最小。

哪個方案最合適？

- A. 設定 IAM Roles Anywhere，把內部 CA 註冊為 trust anchor，建立 profile 與只允許必要 S3／SQS 動作的 IAM role；伺服器以 credential helper 透過 `credential_process` 用裝置憑證換取臨時憑證，撤銷時以 CRL 撤銷該伺服器的憑證
- B. 把 access key 存進 Secrets Manager 並啟用 30 天自動輪替，伺服器每天以排程從 Secrets Manager 取回最新的 key
- C. 在每台伺服器以 hybrid activation 安裝 SSM Agent，讓應用程式直接使用 SSM Agent 取得的 service role 憑證存取 S3 與 SQS
- D. 為每台伺服器建立一個 Cognito user pool 的 app client，以 client secret 取得 token 後再呼叫 S3 與 SQS

> [!answer]- 答案：A
> **A ✓** IAM Roles Anywhere 讓 AWS 以外的工作負載用 X.509 憑證換取 STS 臨時憑證，正好可以重用公司既有的 PKI。AWS SDK 透過 `credential_process` 自動取得與更新憑證，應用程式幾乎不用改；撤銷某台伺服器只要撤銷它的憑證。
>
> **B ✗** 輪替縮短了 key 的有效期，但伺服器上仍保存長期 access key，Secrets Manager 的讀取權限本身又需要憑證，問題沒有消失。
>
> **C ✗** Hybrid activation 的憑證是給 SSM Agent 管理該節點用的，讓應用程式共用這組權限違反最小權限，也不是設計用途。若目標是遠端管理與 patch 地端伺服器，SSM hybrid activation 才是正解。
>
> **D ✗** Cognito user pool 的 token 不能直接呼叫 S3／SQS，還需要 identity pool；client secret 本身又是一組長期秘密。Cognito 是為終端使用者設計的，不是伺服器對伺服器的身份方案。
>
> **考點**：SAP-3.2｜IAM Roles Anywhere 以既有 PKI 取代地端長期 access key｜延伸閱讀：第 13 章

### 第 16 題｜SAP｜單選｜D1 共用平台成本的 showback

一家零售集團旗下有 3 個品牌，共 70 個 AWS 帳號。各品牌有自己的帳號，但集團平台帳號中有數個共用的 Amazon EKS cluster 與一個共用資料湖，三個品牌都在使用。財務要求每月依品牌呈現完整成本（showback），共用平台的費用要依實際用量分攤到品牌；分析團隊需要可用 SQL 查詢的明細資料與儀表板；平台團隊不想維護自訂的成本 ETL 程式。

哪個方案最合適？

- A. 每月從 Cost Explorer 依 linked account 篩選匯出 CSV，平台帳號的費用以人工依各品牌的 namespace 數量分攤
- B. 為每個品牌建立 AWS Budgets，以品牌 tag 篩選費用，並把 budget 通知寄給各品牌的財務窗口
- C. 啟用 AWS Billing Conductor，為每個品牌建立 billing group 與 pricing plan，以 pro forma 帳單呈現各品牌的成本
- D. 以 Data Exports 建立 CUR 2.0 輸出到 S3 並以 Athena 查詢；啟用 EKS 的 split cost allocation data 取得 pod 層級成本；以 cost categories 把帳號與 tag 對應到品牌，並用 split charge rule 分攤其餘共用費用；以 QuickSight 建立儀表板

> [!answer]- 答案：D
> **A ✗** 人工分攤不是依實際用量，namespace 數量和實際消耗的 CPU、記憶體沒有直接關係，且每月都要手動處理。
>
> **B ✗** Budgets 是預算追蹤與警示工具，不會把共用資源的費用分攤給不同品牌。
>
> **C ✗** Billing Conductor 用來自訂費率與產生 pro forma 帳單（例如轉售或內部計價），billing group 以帳號為單位，無法把同一個 EKS cluster 的費用依 pod 用量拆給不同品牌。
>
> **D ✓** CUR 2.0 提供最細的計費明細並能直接用 Athena 查詢；split cost allocation data 依 pod 的實際 CPU 與記憶體用量把 EKS 節點成本拆開；cost categories 把帳號、tag 歸類到品牌，split charge rule 則能把剩下的共用費用依比例分攤。全部是受管功能，不需要自訂 ETL。
>
> **考點**：SAP-1.5｜CUR 2.0、split cost allocation data 與 cost categories 做 showback｜延伸閱讀：第 39、43 章

### 第 17 題｜SAP｜單選｜D4 企業客戶的 SFTP 檔案交換

一家商業銀行有 300 家企業客戶每天以 SFTP 上傳付款檔到地端兩台 OpenSSH 伺服器。客戶端的防火牆已把銀行的兩個公有 IP 列入允許清單；客戶以 SSH 金鑰登入，金鑰存放在銀行既有的客戶資料庫中。檔案上傳後必須先以 PGP 解密，再放到處理區供後端批次使用。銀行要把這套服務搬到 AWS，短期內無法要求客戶修改任何連線設定，並希望不再維運 SFTP 伺服器。

哪個方案最合適？

- A. 在 Auto Scaling group 中執行 OpenSSH 伺服器並掛載 EFS，前面放一個 NLB 並綁定銀行的公有 IP，以 cron 執行 PGP 解密腳本
- B. 把銀行的公有 IP 以 BYOIP 帶到 AWS 並配置為 Elastic IP；建立 VPC 型、internet-facing 的 AWS Transfer Family SFTP 端點並綁定這些 Elastic IP；以 Lambda 作為 custom identity provider 查詢既有客戶資料庫中的金鑰；後端用 S3，並以 Transfer Family managed workflow 執行 PGP 解密與搬移
- C. 建立 public endpoint 類型的 AWS Transfer Family SFTP server，以 service-managed users 匯入所有客戶的 SSH 公鑰，並請客戶改用新的 Transfer Family 主機名稱
- D. 開發一個網頁上傳入口，讓客戶以 S3 presigned URL 上傳付款檔，再以 S3 event 觸發 Lambda 執行 PGP 解密

> [!answer]- 答案：B
> **A ✗** 能保留 IP，但仍要自己維運 SFTP 伺服器、修補與擴展，違反「不再維運伺服器」。
>
> **B ✓** Transfer Family 是受管 SFTP 服務；VPC 型 internet-facing 端點可以綁定 Elastic IP（包含以 BYOIP 帶入的位址），客戶的允許清單不必修改。Custom identity provider 讓認證沿用既有資料庫，managed workflow 內建 PGP 解密等後處理步驟，最後檔案落在 S3 供批次使用。
>
> **C ✗** Public endpoint 類型不能綁定固定 IP，位址由 AWS 管理且可能變動，客戶必須改主機名稱與防火牆設定，違反限制；手動匯入 300 家客戶的金鑰也增加管理工作。
>
> **D ✗** 改成網頁上傳等於要求所有企業客戶改變作業流程與自動化腳本，短期內不可行。
>
> **考點**：SAP-4.3｜Transfer Family：固定 IP、custom identity provider 與 managed workflow｜延伸閱讀：第 25 章

### 第 18 題｜SAP｜單選｜D2 會變動的運算組合如何承諾用量

一家保險公司在 us-east-1 有穩定的 EC2 用量，每月約 8 萬美元，目前全是 m5 系列；未來 12 個月會把大部分工作負載改到 Graviton（m7g），並把部分服務搬到 ECS on Fargate；另有每月約 1 萬美元的 Lambda 費用；明年還會在 eu-west-1 啟用第二個 Region。財務已核准 3 年期承諾，希望在架構持續變動的情況下仍能獲得最大且持續有效的折扣。

哪個購買策略最合適？

- A. 購買 3 年期 EC2 Instance Savings Plans，承諾 us-east-1 m5 系列的穩定用量
- B. 購買 3 年期、All Upfront 的 m5 Standard Reserved Instances，涵蓋目前所有 m5 instance
- C. 依未來穩定的基準用量購買 3 年期 Compute Savings Plans，自動套用到不同 instance family、Region、Fargate 與 Lambda
- D. 購買 3 年期 Convertible Reserved Instances，需要時再轉換成 m7g；Lambda 則改用 provisioned concurrency 降低費用

> [!answer]- 答案：C
> **A ✗** EC2 Instance Savings Plans 綁定單一 Region 的單一 instance family，改用 m7g、Fargate 或新 Region 後折扣就失效。它的折扣率較高，適合確定不會換 family 的工作負載。
>
> **B ✗** Standard RI 綁得更死，無法轉換 family，也不涵蓋 Fargate 與 Lambda；搬遷後會留下用不到的承諾。
>
> **C ✓** Compute Savings Plans 以每小時的金額承諾計算，自動套用到任何 instance family、大小、Region、OS 的 EC2，也涵蓋 Fargate 與 Lambda，正好跟得上 Graviton 轉換、Fargate 化與新 Region。承諾額度應以轉換後的穩定基準估算，避免買超。
>
> **D ✗** Convertible RI 只能轉換 EC2 instance，仍不涵蓋 Fargate 與 Lambda；provisioned concurrency 是降低冷啟動的功能，會增加費用而不是省錢。
>
> **考點**：SAP-2.6｜Compute Savings Plans 的彈性範圍｜延伸閱讀：第 39 章

### 第 19 題｜SAP｜單選｜D1 三個 Region 的分段全球網路

一家媒體集團在 us-east-1、eu-west-1、ap-northeast-1 三個 Region 共有 60 個帳號、150 個 VPC。目前每個 Region 一個 Transit Gateway，三個 Transit Gateway 之間以 peering 全互連，跨 Region 路由全靠手動維護的靜態路由，常常出錯。資安要求把網路分成 production、non-production、shared services 三個區段：production 與 non-production 都能存取 shared services，但彼此不能互通。網路團隊希望以集中的政策定義全球網路，跨 Region 的路由自動傳播，新 VPC 依 tag 自動加入正確區段。

哪個方案最合適？

- A. 建立 AWS Cloud WAN core network，在三個 Region 設定 edge location，定義 production、non-production、shared 三個 segment；以 attachment policy 依 tag 把 VPC 對應到 segment，並以 segment action 讓 shared segment 分享給另外兩個 segment
- B. 保留現有 Transit Gateway 架構，在每個 Transit Gateway 增加三張 route table 做區段隔離，並以 Network Manager 視覺化全球拓樸
- C. 移除 Transit Gateway，改為 150 個 VPC 之間依需求建立 VPC peering，並以 security group 隔離 production 與 non-production
- D. 在 us-east-1 建立一個 Transit Gateway，把三個 Region 的所有 VPC 都 attach 到它，再以三張 route table 實作區段隔離

> [!answer]- 答案：A
> **A ✓** Cloud WAN 以一份 core network policy 宣告全球網路：segment 提供區段隔離，跨 Region 的路由在同一 segment 內自動傳播，attachment policy 依 tag 自動把新 VPC 放進正確 segment，shared services 以 segment sharing 對兩邊開放。這正是「政策驅動、集中管理的全球網路」。
>
> **B ✗** Route table 能做區段隔離，但 Transit Gateway peering 不支援動態路由傳播，跨 Region 仍要手動維護靜態路由，核心問題沒有解決；Network Manager 只是視覺化與監控。
>
> **C ✗** 150 個 VPC 的 peering 數量龐大，peering 不支援 transitive routing，且無法以 segment 概念集中管理。
>
> **D ✗** Transit Gateway 是 Regional 資源，只能 attach 同一 Region 的 VPC，跨 Region 必須用 peering。
>
> **考點**：SAP-1.1｜Cloud WAN segment 與政策驅動的全球網路｜延伸閱讀：第 41 章

### 第 20 題｜SAP｜選三項｜D3 影音素材 bucket 的儲存成本

一家串流影音公司把所有節目的原始檔與轉檔後版本放在一個啟用 versioning 的 S3 bucket，總量 3.2 PB。新節目上架後的前 30 天存取頻繁，之後的存取模式無法預測，舊節目常因社群話題突然爆紅。S3 Storage Lens 顯示有 180 TB 是未完成的 multipart upload，另有 900 TB 是重新轉檔後留下的 noncurrent version。物件大多大於 100 MB；任何素材被要求時都必須在毫秒等級內可讀取。

哪三個動作能在符合需求下降低最多儲存成本？

- A. 建立 lifecycle rule，把 current version 在上架 30 天後轉到 S3 Intelligent-Tiering
- B. 建立 lifecycle rule，把 current version 在 90 天後轉到 S3 Glacier Deep Archive
- C. 建立 lifecycle rule，在 7 天後中止（abort）未完成的 multipart upload
- D. 停用這個 bucket 的 versioning，讓既有的 noncurrent version 自動消失
- E. 建立 lifecycle rule，讓 noncurrent version 在變成 noncurrent 30 天後過期，並以 `NewerNoncurrentVersions` 保留最近的少數版本
- F. 建立 lifecycle rule，把 current version 在 30 天後轉到 S3 One Zone-IA

> [!answer]- 答案：A、C、E
> **A ✓** 存取模式不可預測又要求毫秒讀取，正是 Intelligent-Tiering 的使用情境：它依實際存取自動在 Frequent、Infrequent、Archive Instant Access 層之間移動，沒有取回費；物件大，每個物件的監控費相對可忽略。
>
> **B ✗** Deep Archive 取回需要數小時，違反毫秒讀取需求。
>
> **C ✓** 未完成的 multipart upload 的 part 會持續計費卻看不到完整物件；`AbortIncompleteMultipartUpload` 會清掉它們，180 TB 直接省下。
>
> **D ✗** 已啟用 versioning 的 bucket 只能「暫停」不能停用，既有 noncurrent version 也不會自動消失；而且會失去誤刪保護。
>
> **E ✓** `NoncurrentVersionExpiration` 清除舊版本，`NewerNoncurrentVersions` 保留最近幾個版本作為回復保障，兼顧成本與保護。
>
> **F ✗** One Zone-IA 只存在單一 AZ，不適合作為唯一的素材主副本；對於不可預測、可能突然大量讀取的物件，IA 類別的取回費也會讓成本難以控制。
>
> **考點**：SAP-3.5｜S3 lifecycle：Intelligent-Tiering、abort multipart upload、noncurrent version 過期｜延伸閱讀：第 23 章

### 第 21 題｜SAP｜單選｜D2 Global Database 的演練與真實故障

一家壽險公司的保單系統使用 Aurora PostgreSQL Global Database，primary 位於 eu-central-1，secondary 位於 eu-west-1。DR 程序需要涵蓋兩種情境：第一，每季的 DR 演練與計畫性的 Region 輪替，必須零資料遺失，演練後仍保留 Global Database 拓樸；第二，primary Region 真的發生故障、primary cluster 無法存取時，要盡快在 eu-west-1 恢復寫入。

哪個程序最合適？

- A. 兩種情境都把 eu-west-1 的 secondary cluster 從 Global Database 移除（detach）並升級為獨立 cluster，事後再重新建立 Global Database
- B. 演練時以 failover（允許資料遺失）切換到 eu-west-1；真實故障時使用 switchover，確保所有資料同步後才切換
- C. 兩種情境都使用 switchover，因為 switchover 會先同步資料，能保證零資料遺失
- D. 演練與計畫輪替時使用 switchover，它會等 secondary 完全同步後才切換並保留拓樸；真實故障時對 eu-west-1 執行 failover 並允許資料遺失，RPO 約等於當時的複寫延遲，舊 primary 恢復後再加回成為 secondary

> [!answer]- 答案：D
> **A ✗** Detach 後要重建 Global Database，對每季演練來說負擔太大；而且 detach 不會先等資料同步，演練時可能遺失資料。
>
> **B ✗** 兩者用反了。Switchover 需要 primary 健康才能協調同步，primary 無法存取時做不到；在演練時刻意允許資料遺失則違反零遺失要求。
>
> **C ✗** Switchover 依賴 primary 可用，真實的 Region 故障時無法使用。
>
> **D ✓** Switchover（計畫性切換）會停止 primary 寫入、等待 secondary 追上再交換角色，RPO 為 0 且保留 Global Database。Failover（非計畫性）在 primary 不可用時直接把 secondary 升為 primary，可能遺失尚未複寫的少量資料。DR 手冊要清楚區分兩者。
>
> **考點**：SAP-2.2｜Aurora Global Database switchover 與 failover 的差異｜延伸閱讀：第 26、42 章

### 第 22 題｜SAP｜選兩項｜D1 出售事業單位時移交帳號

一家媒體公司把旗下 podcast 事業單位出售給另一家公司。該事業單位的 12 個帳號都在 Organization 的 `Podcast` OU 下，正在運行的服務不能中斷，也不能重建資源。買方有自己的 AWS Organization，交割後會套用自己的 SCP 與治理機制。雙方約定在 30 天內完成移交。

哪兩個步驟是移交帳號的正確做法？

- A. 在買方 Organization 建立 12 個新帳號，以 AWS Backup 把所有資源備份後跨帳號還原到新帳號
- B. 把 12 個帳號的 root email 改成買方網域的信箱，帳號就會自動移轉到買方的 Organization
- C. 移交前取消這些帳號在賣方組織中的 delegated administrator 身份、把 root user 的 email 與 MFA 交由買方控制，並盤點與移除對賣方組織的依賴，例如 organization trail、以 `aws:PrincipalOrgID` 授權的 resource policy、RAM 組織共享，以及透過賣方 IAM Identity Center 的登入方式
- D. 由買方 management account 對這 12 個帳號發出邀請，各帳號接受後直接移轉（direct account transfer）到買方的 Organization；買方先把它們放進 onboarding OU 驗證 SCP 的影響，再移到正式 OU
- E. 在買方 Organization 為每個帳號建立新帳號，以 AWS Application Migration Service 把 EC2 工作負載複寫過去後關閉舊帳號

> [!answer]- 答案：C、D
> **A ✗** 備份還原等於重建資源，違反限制，而且很多資源（IAM、網路設定、第三方整合）無法用 AWS Backup 搬移。
>
> **B ✗** 修改 root email 只改變帳號的聯絡信箱，不會改變帳號所屬的 Organization。
>
> **C ✓** Delegated administrator 帳號必須先取消註冊才能移轉；root user 的 email 與 MFA 交給買方，買方才能真正控制帳號。更重要的是事先找出依賴原組織的設定，否則一移出就可能失去登入方式（Identity Center）、跨帳號存取（PrincipalOrgID）或共享資源（RAM），導致服務中斷。
>
> **D ✓** 自 2025 年 11 月起，Organizations 支援 direct account transfer：新組織發出邀請、帳號接受即可直接移轉，不必先離開原組織成為獨立帳號（舊流程「先離開、再接受邀請」仍可使用，但帳號離開後要先具備付款方式等獨立帳號資訊）。帳號內的資源完全不動。移入的帳號會先位於新組織的 root，買方再把它們放進 onboarding OU 逐步驗證 SCP 的影響，避免新政策一套用就打斷運行中的服務。
>
> **E ✗** 用 MGN 搬遷等於重建，只涵蓋 EC2，也遠比移交帳號複雜。
>
> **考點**：SAP-1.4｜帳號在組織間移轉的前置作業與流程｜延伸閱讀：第 14、40 章

### 第 23 題｜SAP｜單選｜D4 第一波遷移與工廠核心系統

一家家電製造商有 3 座工廠與一個總部資料中心，共 180 個工作負載。每座工廠的製造執行系統（MES）直接控制產線設備，與 PLC 之間需要小於 5 毫秒的延遲，且工廠對外網路中斷時必須繼續運作。總部資料中心則有 ERP 與大量內部 web 應用。CIO 希望 6 週內完成第一波遷移，用來建立團隊經驗與管理層信心，同時不能影響生產。

第一波遷移應如何規劃？

- A. 第一波就遷移 3 座工廠的 MES，因為它的業務價值最高，能最快證明雲端效益
- B. 第一波挑選 10–15 個總部的低複雜度、相依少、非關鍵的應用（例如內部 web 與開發測試環境）以 rehost 方式遷移；MES 先標記為 retain，留在工廠，日後再評估 Outposts 或邊緣方案
- C. 第一波遷移 ERP 資料庫，因為授權即將續約，搬到 AWS 能立刻省下最多費用
- D. 把 180 個工作負載全部排在同一個週末一次切換，縮短新舊環境並存的時間

> [!answer]- 答案：B
> **A ✗** MES 有嚴格的本地延遲與離線運作需求，放到 Region 會破壞這兩項需求；把最關鍵、最難的系統放在第一波，與「建立經驗、不影響生產」完全相反。
>
> **B ✓** 第一波的目的是驗證流程（landing zone、網路、遷移工具、切換手冊）並累積經驗，應挑選低風險、相依少的應用。MES 的延遲與離線需求本來就不適合搬到 Region，標記為 retain，日後再看 Outposts 等能在廠內提供 AWS 基礎設施的方案。
>
> **C ✗** ERP 資料庫相依多、風險高，不適合當第一波；授權壓力應透過 wave 規劃排在團隊有經驗之後。
>
> **D ✗** Big-bang 切換一旦出問題影響面極大，也無法從前面的 wave 學習改進。
>
> **考點**：SAP-4.1｜第一波遷移的選擇與 retain 的判斷｜延伸閱讀：第 44 章

### 第 24 題｜SAP｜單選｜D3 新聞網站的快取命中率

一家新聞媒體的網站以 CloudFront 為前端，origin 是 ALB 後面的 EC2。CloudFront 的 cache hit ratio 只有 18%，突發新聞時 origin 經常過載，亞洲讀者的 TTFB 也偏高。調查發現 cache behavior 使用舊式設定，把所有 header、所有 cookie（包含每位讀者都不同的分析 cookie）與所有 query string（包含 `utm_*` 追蹤參數）都轉送並列入快取鍵；實際上頁面內容只會依 `page` query string 與裝置類型（手機或桌機）不同而改變，個人化內容由前端另外呼叫 API 取得。

哪個做法能最有效改善快取命中率與 origin 負載？

- A. 擴充 origin 的 Auto Scaling 上限，並啟用 Origin Shield，讓 origin 能承受更多回源請求
- B. 把 cache behavior 的 Minimum TTL 設為 0，並讓 origin 對所有頁面回傳 `Cache-Control: no-cache`，確保讀者看到最新內容
- C. 建立 cache policy，快取鍵只包含 `page` query string 與 `CloudFront-Is-Mobile-Viewer` header，不包含 cookie；以 origin request policy 轉送 origin 仍需要的其他值但不列入快取鍵；並在靠近 origin 的 Region 啟用 Origin Shield
- D. 以 Lambda@Edge 在 viewer request 階段為每個 URL 加上隨機參數，確保不同讀者取得各自的快取版本

> [!answer]- 答案：C
> **A ✗** 能暫時撐住 origin，但快取鍵包含每位讀者都不同的 cookie 與追蹤參數，命中率依然很低，治標不治本。Origin Shield 本身是有用的，只是不能單獨解決問題。
>
> **B ✗** 這會讓幾乎所有請求都回源，命中率更低，origin 更容易過載。
>
> **C ✓** 快取鍵只包含真正影響內容的值，同一篇文章的所有讀者就會共用同一份快取；origin request policy 把轉送給 origin 的值和快取鍵分開管理。Origin Shield 再多一層集中快取，進一步減少回源次數。
>
> **D ✗** 加隨機參數會讓每個請求都變成不同的快取鍵，等於關閉快取。
>
> **考點**：SAP-3.3｜CloudFront cache policy 精簡快取鍵與 Origin Shield｜延伸閱讀：第 11 章

### 第 25 題｜SAP｜單選｜D2 隔離網段中的密碼輪替

一家零售商的支付對帳服務部署在只有 local route 的 isolated subnet 中，沒有 NAT Gateway 也沒有 Internet Gateway，這是 PCI DSS 網段隔離的要求。服務連線到 RDS for PostgreSQL，資料庫密碼目前放在 Parameter Store 的 SecureString，每年由 DBA 手動更換一次。稽核要求改為每 30 天自動輪替、輪替時服務不能中斷，而且不能為了輪替而新增任何對外網路路徑。

哪個方案最合適？

- A. 把憑證改存到 Secrets Manager 並啟用自動輪替（alternating users 策略），rotation Lambda 部署在同一個 VPC；為 Secrets Manager 建立 interface VPC endpoint，讓 rotation function 與應用程式都透過 endpoint 存取，應用程式每次建立連線時取得最新的 secret 並在本地快取
- B. 保留 Parameter Store，以 EventBridge Scheduler 每 30 天觸發一個自訂 Lambda 修改資料庫密碼並更新 parameter，應用程式在下次重啟時讀取新密碼
- C. 把憑證改存到 Secrets Manager 並啟用自動輪替，rotation Lambda 不放進 VPC，以便直接呼叫 Secrets Manager API 與 RDS 的公開端點
- D. 改用 IAM database authentication，並在 isolated subnet 加入 NAT Gateway，讓應用程式能連到 STS 取得產生 token 所需的憑證

> [!answer]- 答案：A
> **A ✓** Secrets Manager 內建 RDS 的輪替範本；alternating users 策略輪流更新兩個資料庫使用者，輪替當下舊連線仍可使用，不會中斷。Interface endpoint 讓 VPC 內的 rotation Lambda 與應用程式在不經過 Internet 的情況下呼叫 Secrets Manager。
>
> **B ✗** 要自己寫並維護輪替邏輯；應用程式要重啟才讀到新密碼，輪替當下就會連線失敗，違反不中斷要求。
>
> **C ✗** VPC 外的 Lambda 連不到 isolated subnet 中的私有 RDS，而讓 RDS 有公開端點違反 PCI 網段隔離。
>
> **D ✗** 新增 NAT Gateway 正是被禁止的對外路徑。其實 IAM 資料庫認證的 token 是用 SigV4 在本地簽出的，不需要連網，但 IAM 認證有新連線速率的建議上限，且 NAT 這一步已直接違反限制。
>
> **考點**：SAP-2.3｜Secrets Manager 輪替、alternating users 與 VPC endpoint｜延伸閱讀：第 15 章

### 第 26 題｜SAP｜單選｜D1 低速率的撞庫攻擊

一家電商的網站以 CloudFront 搭配 ALB 提供服務，登入 API 為 `POST /api/login`。最近攻擊者從數千個住宅 IP 進行撞庫（credential stuffing），每個 IP 的請求頻率都很低，現有的 rate-based rule 完全沒有作用，客服接到多起帳號被盜用的申訴。資安要求一個受管方案，能辨識外洩的帳號密碼組合與異常的登入失敗模式，並對可疑請求封鎖或要求 CAPTCHA，應用程式改動要最少。

哪個方案最合適？

- A. 把 rate-based rule 的門檻從每 5 分鐘 2,000 次降到 20 次，並以 IP 為彙總鍵
- B. 在 CloudFront 的 web ACL 加入 AWS WAF Fraud Control account takeover prevention（ATP）managed rule group，設定登入路徑與 username／password 欄位，並啟用回應檢查以辨識登入失敗；對可疑請求採取 Block 或 CAPTCHA
- C. 訂閱 AWS Shield Advanced，啟用自動應用層 DDoS 緩解，讓 Shield Response Team 協助處理攻擊
- D. 在所有帳號啟用 Amazon GuardDuty，並以 EventBridge 規則在偵測到可疑登入時觸發 Lambda 把來源 IP 加入 WAF IP set

> [!answer]- 答案：B
> **A ✗** 攻擊分散在數千個 IP、每個 IP 頻率都很低，再低的單 IP 門檻也會誤傷正常使用者，同時仍抓不到分散的攻擊。
>
> **B ✓** ATP 是專門對付帳號接管的受管規則：它檢查登入請求中的帳密是否出現在已知外洩憑證資料庫，並透過回應檢查追蹤同一 IP 或同一 client session 的登入失敗比例。注意回應檢查（response inspection）只在保護 CloudFront distribution 的 web ACL 中提供，本題的 web ACL 掛在 CloudFront 上，正好適用；若 web ACL 只掛在 ALB，就只能做請求檢查。只要設定登入路徑與欄位，不用修改應用程式。
>
> **C ✗** Shield Advanced 處理的是 DDoS；低速率撞庫的流量很小，不會觸發 DDoS 緩解。
>
> **D ✗** GuardDuty 分析的是 AWS 帳號與資源層級的活動（CloudTrail、VPC Flow Logs、DNS 等），看不到應用程式的登入結果，也無法辨識撞庫。
>
> **考點**：SAP-1.2｜WAF Fraud Control ATP 防撞庫｜延伸閱讀：第 16 章

### 第 27 題｜SAP｜單選｜D2 不換引擎的高可用 PostgreSQL

一家產險公司的報價服務使用 Single-AZ 的 RDS for PostgreSQL。新的可靠性目標是：已 commit 的交易在一個 AZ 故障時不能遺失、failover 時間盡量短（目標約 1 分鐘內）、報價查詢能分散到可讀的備援節點。報價程式大量使用 PostgreSQL extension；採購程序讓團隊今年不能導入 Aurora，必須留在 RDS for PostgreSQL。

哪個部署方式最合適？

- A. 改為 RDS Multi-AZ DB instance deployment，並另外建立兩個 read replica 分擔報價查詢
- B. 把資料庫遷移到 Aurora PostgreSQL，利用 Aurora Replica 分擔查詢並取得更快的 failover
- C. 在另一個 Region 建立 cross-Region read replica，主 Region 故障時手動升級
- D. 改為 RDS Multi-AZ DB cluster deployment：一個 writer 與兩個分布在不同 AZ、可讀取的 standby，報價查詢改連 reader endpoint

> [!answer]- 答案：D
> **A ✗** Multi-AZ DB instance 的 standby 不能讀取，failover 時間通常也比 DB cluster 長；另外建立的 read replica 是非同步複寫，與 HA 是兩套機制。若只需要 HA、不需要讀取擴展，這是較便宜的選擇。
>
> **B ✗** Aurora 技術上很合適，但違反「今年不能導入 Aurora」的限制。
>
> **C ✗** Cross-Region replica 是非同步複寫的 DR 手段，手動升級不能滿足快速 failover，也無法保證已 commit 的交易不遺失。
>
> **D ✓** Multi-AZ DB cluster（支援 MySQL 與 PostgreSQL）有一個 writer 與兩個可讀 standby，跨 3 個 AZ；寫入至少要有一個 standby 確認才算 commit，failover 通常在 35 秒內完成，reader endpoint 也能分擔查詢。
>
> **考點**：SAP-2.4｜RDS Multi-AZ DB cluster 與 Multi-AZ DB instance 的差異｜延伸閱讀：第 26 章

### 第 28 題｜SAP｜單選｜D3 把手動建立的環境納入 IaC

一家影音平台公司的正式環境分布在 4 個帳號，過去 3 年都是工程師在 console 手動建立的，包含 VPC、ALB、ECS service、RDS 等約 900 個資源。新的維運政策要求所有正式環境的變更都必須經由 CloudFormation 與 pipeline 進行，並能偵測 drift；但不能刪除或重建任何現有資源，也不能有停機。

哪個做法最合適？

- A. 由工程師依現況手寫 CloudFormation template，在維護窗口刪除現有資源後以 template 重新部署
- B. 使用 CloudFormer 掃描帳號產生 template，再以新 stack 重新建立資源並切換流量
- C. 使用 CloudFormation IaC generator 掃描各帳號的資源，為選定的資源產生 template，再以 resource import 把現有資源匯入新的 stack；之後所有變更都經由 pipeline 更新 stack，並定期執行 drift detection
- D. 啟用 AWS Config 記錄所有資源設定，有變更需求時以 Config remediation 套用新設定

> [!answer]- 答案：C
> **A ✗** 刪除再重建違反「不能重建、不能停機」，RDS 等有狀態資源風險尤其高。
>
> **B ✗** CloudFormer 是已停止提供的舊工具，而且這個選項是「重新建立」而不是納管現有資源。
>
> **C ✓** IaC generator 掃描帳號中的既有資源並產生 template，搭配 resource import 可以讓現有資源直接成為 stack 的一部分，不重建、不停機。納管後就能用 change set、pipeline 與 drift detection 管理。
>
> **D ✗** Config 是記錄與評估設定的工具，不是 IaC；用 remediation 管理變更沒有版本控制、審查與回滾。
>
> **考點**：SAP-3.1｜IaC generator 與 resource import 納管既有資源｜延伸閱讀：第 37 章

### 第 29 題｜SAP｜單選｜D1 直播 origin 的自動切換

一家體育串流平台以 AWS Elemental MediaLive 編碼直播訊號，MediaPackage 打包成 HLS，作為 CloudFront 的 origin，全部部署在 us-east-1。過去一次 us-east-1 的 MediaPackage 問題造成 25 分鐘的黑畫面。新的要求是：segment 請求失敗時，要在數秒內自動改向備援 origin 取得內容；不能修改播放器；也不能依賴 DNS 變更來切換。

哪個方案最合適？

- A. 在 us-west-2 以相同的訊號源建立第二套 MediaLive 與 MediaPackage；在 CloudFront 建立 origin group，以 us-east-1 的 MediaPackage 為 primary、us-west-2 為 secondary，並在 5xx、404 與連線逾時時 failover
- B. 在 us-west-2 建立第二套 MediaPackage，並以 Route 53 failover record 搭配 health check 讓 origin 主機名稱在故障時解析到 us-west-2
- C. 在 MediaPackage 前面放 AWS Global Accelerator，以 endpoint group 的健康檢查在兩個 Region 之間切換
- D. 把 CloudFront 對 HLS segment 的 TTL 延長到 1 小時，origin 故障時由 edge 快取繼續提供內容

> [!answer]- 答案：A
> **A ✓** CloudFront origin group 對每個請求即時判斷：primary 回傳指定的錯誤碼或連線失敗時，同一個請求立刻改向 secondary，切換在 CloudFront 內完成，播放器與 DNS 都不用變。直播的 segment 請求都是 GET，正好適用 origin failover。
>
> **B ✗** DNS failover 需要 health check 判定加上 TTL 過期，通常要數十秒到數分鐘，且違反「不依賴 DNS 變更」。
>
> **C ✗** Global Accelerator 的 endpoint 只能是 ALB、NLB、EC2 instance 或 Elastic IP，不能直接指向 MediaPackage。
>
> **D ✗** 直播 segment 不斷產生新的內容，快取舊 segment 無法提供新的畫面；延長 manifest 的 TTL 還會讓播放器拿不到最新的 segment 清單。
>
> **考點**：SAP-1.3｜CloudFront origin group 的請求層級 failover｜延伸閱讀：第 11、34 章

### 第 30 題｜SAP｜單選｜D4 2 PB 影音典藏搬到 S3

一家電視台要把地端 NAS 上 2 PB 的影音典藏（NFS 共享）在 45 天內搬到 S3。公司有一條 10 Gbps 的 Direct Connect，扣除日常業務後約有 7 Gbps 可用；Internet 出口只有 1 Gbps，且資安政策禁止典藏資料經過 Internet。遷移期間仍會有少量檔案新增或修改；搬遷完成後需要驗證資料完整性，並在切換前做最後一次增量同步。

哪個方案最合適？

- A. 在一台地端伺服器掛載 NAS，以 AWS CLI 的 `aws s3 sync` 經由 Internet 上傳到 S3，完成後再執行一次 sync 做增量
- B. 在地端部署多個 AWS DataSync agent，透過 Direct Connect 經由 DataSync 的 interface VPC endpoint 傳輸；以多個 task 平行處理不同目錄，設定白天的頻寬上限，啟用資料完整性驗證，並排程增量 task，切換前執行最後一次同步
- C. 在地端部署 S3 File Gateway，把它掛載為 NFS 共享後，以 `rsync` 從 NAS 複製所有檔案到 gateway，由 gateway 上傳到 S3
- D. 建立 AWS Transfer Family 的 SFTP 端點，由 NAS 管理員以 SFTP 用戶端把檔案分批上傳到 S3

> [!answer]- 答案：B
> **A ✗** 違反禁止經過 Internet 的政策；以 1 Gbps 傳 2 PB 理論上就要約 185 天，遠超過 45 天。
>
> **B ✓** 以 7 Gbps 計算，2 PB 約需 26–27 天，落在 45 天內。DataSync 專為大量資料遷移設計：多執行緒平行傳輸、內建完整性驗證、只傳差異的增量 task、頻寬限制與排程；透過 VPC endpoint 與 Direct Connect，資料完全不經過 Internet。
>
> **C ✗** File Gateway 是為「持續以檔案介面存取 S3」設計的混合儲存，大量搬遷時本機快取會成為瓶頸，也沒有 DataSync 的驗證與增量機制。
>
> **D ✗** Transfer Family 是給外部夥伴的檔案交換服務，手動以 SFTP 上傳 2 PB 既慢又難以追蹤與驗證。
>
> **考點**：SAP-4.2｜大量資料遷移：頻寬計算與 DataSync｜延伸閱讀：第 25、45 章

### 第 31 題｜SAP｜單選｜D2 多帳號多 Region 的 baseline 部署

一家出版與影音集團要把一套安全 baseline（AWS Config rule、跨帳號稽核用的 IAM role、CloudWatch alarm）部署到 `Workloads` OU 下的 60 個帳號、每個帳號 4 個 Region。新帳號加入 OU 時要自動部署；baseline 每次更新都要漸進推出，先只套用到少量帳號，失敗數超過門檻就停止；平台團隊不想登入 management account 操作，也不想維護自訂部署程式。

哪個方案最合適？

- A. 建立一條 CodePipeline，為每個帳號建立一個 stage，在 stage 中 assume 目標帳號的 role 執行 CloudFormation deploy，新帳號加入時再手動新增 stage
- B. 撰寫一個 CDK app，以迴圈列出 OU 下的所有帳號與 Region，由平台工程師在本機執行 `cdk deploy` 部署到每個環境
- C. 使用 self-managed permissions 的 CloudFormation StackSets，在每個目標帳號建立 `AWSCloudFormationStackSetExecutionRole`，並以帳號 ID 清單指定部署目標
- D. 把平台帳號註冊為 StackSets 的 delegated administrator，建立 service-managed permissions 的 StackSet 並以 `Workloads` OU 為目標、啟用 automatic deployment；以 maximum concurrent accounts 與 failure tolerance 控制漸進推出，Region 依序部署

> [!answer]- 答案：D
> **A ✗** 每個帳號一個 stage 的 pipeline 難以維護，新帳號要手動加入，正是要避免的自訂部署邏輯。
>
> **B ✗** 從工程師本機執行沒有稽核與一致性，也無法在新帳號加入時自動部署。
>
> **C ✗** Self-managed permissions 需要自己在每個帳號預先建立 role，且只能以帳號清單為目標，不支援 OU 的 automatic deployment。它適合不在 Organization 內的帳號。
>
> **D ✓** Service-managed StackSets 與 Organizations 整合：以 OU 為目標，新帳號加入時自動部署，離開時可自動移除。Maximum concurrent accounts（數量或百分比）與 failure tolerance 控制每批推出的範圍與失敗門檻；delegated administrator 讓平台帳號不必進入 management account。
>
> **考點**：SAP-2.1｜Service-managed StackSets、automatic deployment 與漸進推出｜延伸閱讀：第 37、40 章

### 第 32 題｜SAP｜單選｜D3 Lambda 環境變數中的明文密碼

一家保險經紀公司有 120 個 Lambda function，資料庫密碼與合作夥伴 API key 以明文放在環境變數中，部分程式碼庫還有 `.env` 檔。資安要求：秘密集中管理並定期自動輪替；每個 function 只能讀到自己需要的秘密；擁有 Lambda 唯讀權限的人不能在 console 看到秘密內容。開發團隊擔心每次 invocation 都呼叫 API 取秘密會增加延遲與費用，部分 function 每秒呼叫上千次。

哪個方案最合適？

- A. 以客戶管理的 KMS key 加密 Lambda 環境變數，並在程式中以 KMS Decrypt 解密，只有 function 的 execution role 能使用這把 key
- B. 把秘密改存到 Parameter Store 的 String parameter，function 每次 invocation 都以 `GetParameter` 讀取，確保拿到最新值
- C. 把秘密存到 Secrets Manager 並設定自動輪替；以 IAM policy 限制每個 function 的 execution role 只能讀取自己的 secret；在 function 加入 AWS Parameters and Secrets Lambda Extension，以本地快取與 TTL 減少 API 呼叫
- D. 把秘密存成加密的 JSON 檔放在 S3，function 在 init 階段下載並解密，之後整個執行環境的生命週期都重複使用

> [!answer]- 答案：C
> **A ✗** KMS 加密環境變數能防止部分人看到明文，但秘密仍綁在 function 設定中，沒有集中管理也沒有自動輪替；每次輪替都要重新部署 120 個 function。
>
> **B ✗** String parameter 是明文；每次 invocation 都呼叫 API，在每秒上千次的流量下會增加延遲並可能遇到 API throttling。
>
> **C ✓** Secrets Manager 提供集中保存、自動輪替與精細的 IAM 授權；Lambda extension 在執行環境中快取 secret，TTL 內的讀取不需要呼叫 Secrets Manager API，兼顧延遲與費用。輪替後快取在 TTL 到期時自動更新。
>
> **D ✗** 自建 S3 方案沒有輪替機制；執行環境可能存活數小時，輪替後也不會取得新值。
>
> **考點**：SAP-3.2｜Secrets Manager 輪替與 Lambda extension 快取｜延伸閱讀：第 15、19 章

### 第 33 題｜SAP｜單選｜D1 不進 management account 也能管理 SCP

一家銀行的 management account 只允許 3 位雲端治理主管登入。資安工程團隊在 Security 帳號工作，每天都需要建立、更新 SCP 與 tag policy，並把它們掛到不同 OU。稽核要求：資安工程團隊在 management account 中不能有任何 IAM 身份或可 assume 的 role，所有政策變更都要留下 CloudTrail 紀錄。

哪個做法最合適？

- A. 在 management account 的 Organizations 設定 resource-based delegation policy，允許 Security 帳號的特定 role 執行 SCP 與 tag policy 的建立、更新、掛載與查詢等動作
- B. 在 management account 建立一個附加 `AWSOrganizationsFullAccess` 的 IAM role，信任 Security 帳號，讓資安工程團隊 assume 後管理政策
- C. 把 Security 帳號註冊為 AWS Config 的 delegated administrator，再以 organization conformance pack 部署並維護 SCP
- D. 在 IAM Identity Center 為資安工程團隊建立只允許 `organizations:*Policy*` 動作的 permission set，指派到 management account

> [!answer]- 答案：A
> **A ✓** Organizations 支援以 resource-based delegation policy 把政策管理權限委派給成員帳號，可以限定政策類型（SCP、tag policy 等）與動作。資安工程團隊在自己的帳號操作，management account 中不需要任何身份，所有呼叫都記錄在 CloudTrail。
>
> **B ✗** 這在 management account 建立了可被 assume 的 role，違反稽核要求；FullAccess 也遠超出需要的權限。
>
> **C ✗** Config 的 delegated administrator 管理的是 Config rule 與 conformance pack，不能建立或掛載 SCP。
>
> **D ✗** 權限雖然收斂了，但仍是在 management account 中的身份，同樣違反要求。若沒有「不得在 management account 有身份」的限制，D 也是可接受的最小權限做法。
>
> **考點**：SAP-1.4｜Organizations 政策管理的 delegation policy｜延伸閱讀：第 14 章

### 第 34 題｜SAP｜單選｜D2 全球記者上傳大型影片

一家國際新聞社的駐外記者遍布亞洲、非洲與南美，每天以公司開發的桌面程式（使用 AWS SDK）把 5–50 GB 的原始影片上傳到 us-east-1 的 S3 bucket。遠距離地區的上傳速度很慢，而且經常中途失敗必須重傳。公司希望提升上傳速度與成功率，不想新增需要維運的基礎設施，也不想讓程式依地區選擇不同的目的地。

哪個做法最合適？

- A. 在亞洲、非洲與南美的 Region 各部署一組 EC2 上傳代理伺服器並掛載 EFS，由代理伺服器收檔後再轉傳到 us-east-1
- B. 在每個大洲附近的 Region 各建立一個 bucket 並設定 cross-Region replication 到 us-east-1，桌面程式依記者所在位置選擇最近的 bucket
- C. 在 bucket 中把物件分散到更多 prefix，提高 S3 的每秒請求上限，並調高 SDK 的重試次數
- D. 在 bucket 啟用 S3 Transfer Acceleration，桌面程式改用 accelerate endpoint，並以 multipart upload 平行上傳各個 part，失敗時只重傳失敗的 part

> [!answer]- 答案：D
> **A ✗** 自建代理伺服器需要維運多個 Region 的 EC2 與 EFS，違反不新增基礎設施的需求。
>
> **B ✗** 多 bucket 加 CRR 可行，但要維護多個 bucket 與複寫規則，程式也要依地區選擇目的地，正好違反限制；複寫延遲還讓總部無法立即取得素材。
>
> **C ✗** 瓶頸在長距離網路與單一連線的傳輸，不是 S3 的請求速率；多重試只會讓失敗的大檔反覆重傳。
>
> **D ✓** Transfer Acceleration 讓上傳先進入最近的 CloudFront edge location，再經 AWS 骨幹網路送到 bucket，改善長距離傳輸；只要在 SDK 設定使用 accelerate endpoint。Multipart upload 平行傳輸各 part，失敗時只重傳單一 part，解決中途失敗必須整檔重傳的問題。
>
> **考點**：SAP-2.5｜S3 Transfer Acceleration 與 multipart upload｜延伸閱讀：第 22、23 章

### 第 35 題｜SAP｜單選｜D3 FIFO queue 被壞訊息卡住

一家網路銀行以 SQS FIFO queue 傳送帳務分錄，`MessageGroupId` 設為帳戶 ID，由 Lambda 消費並寫入核心帳務系統。偶爾會有格式錯誤的訊息讓消費端一再失敗，導致該帳戶後續所有分錄都卡住好幾天，直到維運人員手動刪除。要求：維持每個帳戶內的處理順序；壞訊息要被隔離保留以供調查；其他訊息自動繼續處理，不需要人工介入。

哪個做法最合適？

- A. 把 queue 改為 standard queue 並設定 dead-letter queue，讓失敗訊息移出後其他訊息繼續處理
- B. 為 FIFO queue 設定 redrive policy，指向另一個 FIFO dead-letter queue，`maxReceiveCount` 設為 5；在 dead-letter queue 的訊息數量上建立 CloudWatch alarm 通知調查，修正後再以 redrive 把訊息送回來源 queue
- C. 把 visibility timeout 調高到 12 小時，讓失敗訊息有更多時間被處理
- D. 把 message retention period 縮短為 1 分鐘，讓處理失敗的訊息很快過期

> [!answer]- 答案：B
> **A ✗** Standard queue 不保證順序，違反帳戶內必須依序處理的需求。
>
> **B ✓** FIFO queue 的 dead-letter queue 也必須是 FIFO。訊息被接收超過 `maxReceiveCount` 次仍失敗就移到 DLQ，同一個 message group 的後續訊息就能繼續處理；壞訊息保留在 DLQ 供調查，修正後可以 redrive 回來源 queue。
>
> **C ✗** 拉長 visibility timeout 只會讓壞訊息卡住整個 message group 更久。
>
> **D ✗** 縮短 retention 會讓正常但暫時積壓的訊息也直接遺失，對帳務資料不可接受。
>
> **考點**：SAP-3.4｜FIFO queue 的 DLQ 隔離毒訊息｜延伸閱讀：第 32 章

### 第 36 題｜SAP｜選兩項｜D1 經 Direct Connect 私有存取 S3

一家銀行的地端系統每天要經由既有的 Direct Connect 上傳約 5 TB 資料到 us-east-1 的 S3。目前的連線是 transit VIF → Direct Connect gateway → Transit Gateway → shared-services VPC。資安政策禁止建立 public VIF，也禁止任何資料經過 Internet；S3 bucket 只能接受來自銀行網路、經過指定 VPC endpoint 的存取。

哪兩個步驟組合起來能滿足需求？

- A. 在 shared-services VPC 建立 S3 gateway endpoint，並把 S3 的 prefix list 透過 BGP 宣告給地端路由器
- B. 在 shared-services VPC 建立 S3 interface endpoint，地端系統使用 endpoint 專屬的 DNS 名稱（或由 Route 53 Resolver inbound endpoint 解析），流量經 Transit Gateway 與 Direct Connect 進入 endpoint
- C. 建立 public VIF，並以 BGP community 限制只接收 us-east-1 的 S3 路由
- D. 在 bucket policy 中以 `aws:SourceIp` 限制只允許銀行地端的公有 IP 範圍存取
- E. 在 bucket policy 中加入 Deny 陳述，除非請求的 `aws:SourceVpce` 等於該 interface endpoint 的 ID（並為必要的管理 role 保留例外）

> [!answer]- 答案：B、E
> **A ✗** Gateway endpoint 只對 VPC 內的資源有效，透過 route table 生效，地端經 Direct Connect 或 VPN 進來的流量無法使用；它也沒有可以宣告給地端的 IP 位址。
>
> **B ✓** S3 interface endpoint 在 subnet 中有私有 IP 的 ENI，地端可以經由 Direct Connect 與 Transit Gateway 路由到這些 IP，資料全程走私有網路。地端必須使用 endpoint 專屬 DNS 名稱，或透過 Resolver inbound endpoint 解析到私有 IP。
>
> **C ✗** 直接違反禁止 public VIF 的政策。
>
> **D ✗** 經過 VPC endpoint 的請求，S3 看到的來源是私有 IP，`aws:SourceIp` 條件不會匹配銀行的公有 IP，這條規則會失效。
>
> **E ✓** `aws:SourceVpce` 條件確保 bucket 只接受經由指定 endpoint 的請求，即使有人拿到憑證也無法從 Internet 存取。
>
> **考點**：SAP-1.1｜地端經 DX 使用 S3 interface endpoint 與 aws:SourceVpce｜延伸閱讀：第 6、8 章

### 第 37 題｜SAP｜單選｜D4 每月 600 萬份保單對帳單

一家壽險公司每月要產生約 600 萬份保單對帳單 PDF。現在是在兩台地端大型伺服器上跑的 Java 批次程式，整批需要約 70 小時，中途失敗時只能從頭重跑。每月的輸入是一份放在 S3 的 CSV 清單，每份對帳單的產生時間為 2–8 秒，彼此獨立。新的要求是：6 小時內完成整批、只重試失敗的項目、能即時看到處理進度、不需要管理伺服器。

哪個架構最合適？

- A. 把批次程式原封不動搬到一台記憶體與 CPU 最大的 EC2 instance 上執行，並以 EBS snapshot 保存中間結果
- B. 以自訂程式讀取 CSV，把每筆資料送進 SQS 由 Lambda 處理，並自建 DynamoDB table 記錄每筆的處理狀態、進度與失敗清單
- C. 以 Step Functions Distributed Map 讀取 S3 上的 CSV 清單，用 item batching 把多筆合成一批交給 Lambda 產生 PDF，設定 maximum concurrency 與 tolerated failure 門檻，以 ResultWriter 把結果與失敗項目寫到 S3，必要時對失敗項目 redrive
- D. 建立一個 AWS Glue Python shell job，在 job 中以迴圈依序產生所有 PDF 並寫到 S3

> [!answer]- 答案：C
> **A ✗** 單機垂直擴展無法把 70 小時壓到 6 小時，失敗時仍要大段重跑，也仍要管理伺服器。
>
> **B ✗** 技術上可行，但進度追蹤、失敗統計與重試都要自己寫，營運與開發負擔明顯較高。若處理邏輯需要更複雜的佇列語意，這條路才值得。
>
> **C ✓** Distributed Map 原生支援以 S3 上的 CSV 為輸入，可平行執行大量 child workflow，內建批次、併發控制、失敗容忍門檻與結果輸出；console 能即時看到進度，失敗項目可 redrive 而不必重跑整批。完全 serverless。
>
> **D ✗** Python shell job 是單一節點的小型工作，依序處理 600 萬份 PDF 遠遠來不及。
>
> **考點**：SAP-4.3｜Step Functions Distributed Map 改造大型批次｜延伸閱讀：第 33 章

### 第 38 題｜SAP｜選兩項｜D2 防勒索的不可變備份

一家區域銀行在一次同業勒索軟體事件後，收到主管機關的新要求：40 個帳號中核心系統的 EC2、EBS、Aurora 與 DynamoDB（已啟用 AWS Backup 進階功能）備份必須不可變，即使來源帳號的 root user 或遭入侵的管理員也無法刪除；發生事件時要能在一個與正式環境隔離的乾淨帳號中還原。銀行希望以最少的自訂程式與管理工作達成。

哪兩個步驟組合起來最能滿足需求？

- A. 從 AWS Backup 的 delegated administrator 帳號以 Organizations backup policy 在各帳號建立備份計畫，並設定 copy action 把復原點複製到集中管理帳號中的 logically air-gapped vault
- B. 為所有存放備份的 S3 bucket 啟用 versioning 與 MFA Delete，防止備份被刪除
- C. 在各帳號的 backup vault 啟用 governance mode 的 Vault Lock，讓備份在保留期內無法被一般使用者刪除
- D. 以 AWS RAM 把 logically air-gapped vault 分享給獨立的復原帳號，在事件發生時直接從該帳號還原，並定期執行還原測試
- E. 以排程 Lambda 每天把各帳號的 snapshot 複製到另一個 Region，並以 tag 標記為不可刪除

> [!answer]- 答案：A、D
> **A ✓** Backup policy 讓備份計畫由組織集中下發，各帳號不必自行設定；logically air-gapped vault 一律以 compliance mode 鎖定，保留期內任何人（包含 root）都無法刪除復原點，正好滿足不可變需求。注意它支援的資源類型比一般 vault 少：本題的 EC2、EBS、Aurora 與啟用進階功能的 DynamoDB 都支援，但 RDS DB instance（非 Aurora）目前不在清單內；EC2、EBS 這類非 AWS Backup 完整管理的資源，來源還必須以客戶管理的 KMS key 加密才能複製進去。設計前要先查 AWS Backup 的功能支援表。
>
> **B ✗** AWS Backup 的復原點存放在 backup vault 中，不是你可以設定 versioning 的 S3 bucket，這個選項與機制不符。
>
> **C ✗** Governance mode 可以被擁有特定權限的使用者移除，遭入侵的高權限管理員仍能刪除備份；不可變需求必須使用 compliance mode。
>
> **D ✓** Logically air-gapped vault 可以透過 RAM 分享給另一個帳號，該帳號可直接從分享的 vault 還原，不必先複製。復原帳號與正式環境隔離，即使正式帳號被入侵也能在乾淨環境中恢復；定期測試確保還原流程可用。
>
> **E ✗** 自寫 Lambda 增加維護負擔，tag 也無法防止有權限的人刪除 snapshot。
>
> **考點**：SAP-2.2｜Logically air-gapped vault 與跨帳號還原｜延伸閱讀：第 34、43 章

### 第 39 題｜SAP｜選兩項｜D1 成本中心 tag 的治理

一家工具機製造商在 AWS Organizations 中有 90 個帳號。財務需要在 Cost Explorer 依 `CostCenter` 檢視成本，但現況混亂：key 有 `costcenter`、`Cost-Center` 等寫法，value 也有 `Plant 1`、`P01` 等不同格式。新要求：EC2 instance、EBS volume 與 RDS DB instance 若建立時沒有 `CostCenter` tag 就要被拒絕；tag value 只能是核准清單中的值；財務能在帳單工具中依 tag 分組。

哪兩個步驟組合起來能滿足需求？

- A. 在 management account 啟用 AWS-generated cost allocation tag，讓 AWS 自動為資源加上成本中心資訊
- B. 在組織 root 掛 tag policy，定義 `CostCenter` 的大小寫與允許的 value，並對 EC2 instance、EBS volume 與 RDS DB instance 的資源類型啟用 enforcement；另外掛一個 SCP，以 `aws:RequestTag/CostCenter` 的 `Null` 條件拒絕未帶此 tag 的建立請求
- C. 在 management account 把 `CostCenter` 啟用為 user-defined cost allocation tag
- D. 部署 `required-tags` Config rule，並設定自動修正刪除沒有 `CostCenter` tag 的資源
- E. 建立 cost categories，把各種拼法的 tag value 對應到正確的成本中心，不需要修改現有 tag

> [!answer]- 答案：B、C
> **A ✗** AWS-generated tag（例如 `aws:createdBy`）由 AWS 產生，內容是建立者等資訊，不會產生公司定義的成本中心。
>
> **B ✓** Tag policy 標準化 key 的大小寫與允許的 value，對啟用 enforcement 的資源類型，不合規的 tag 操作會被拒絕；但 tag policy 不會強制「一定要有」tag，所以要搭配 SCP，用 `aws:RequestTag` 條件拒絕沒帶 tag 的建立請求。兩者一起才完整。
>
> **C ✓** User-defined tag 必須在 management（payer）account 啟用為 cost allocation tag，才會出現在 Cost Explorer 與 CUR 中作為分組維度。
>
> **D ✗** 自動刪除資源具破壞性，可能刪掉正式環境的資源；而且是事後處理，不是建立時拒絕。
>
> **E ✗** Cost categories 可以整理歷史資料，但不會阻止新資源繼續帶錯誤或缺少的 tag。它適合當過渡期的補救手段。
>
> **考點**：SAP-1.5｜Tag policy + SCP 強制標記，並啟用 cost allocation tag｜延伸閱讀：第 39、43 章

### 第 40 題｜SAP｜單選｜D3 Java Lambda 的冷啟動

一家數位銀行的餘額查詢 API 由 API Gateway 與 Java 17 Spring Boot 的 Lambda function 組成，function 以 version 與 alias 部署。早上尖峰與每次部署後，冷啟動時間高達 6–8 秒，p99 延遲目標為 1 秒。流量尖峰無法預測，財務不希望為閒置容量付費，團隊也不打算更換程式語言。

哪個做法最合適？

- A. 對 function 的 published version 啟用 Lambda SnapStart，並使用 runtime hook 在還原後重新建立需要唯一性的狀態（例如亂數種子與網路連線）
- B. 為 alias 設定 500 的 provisioned concurrency 並全天維持，確保所有請求都由已初始化的執行環境處理
- C. 把 function 記憶體調到 10,240 MB，以取得最多 CPU 資源加速 Spring 初始化
- D. 以 Python 改寫 function，因為直譯式語言的冷啟動比 Java 短

> [!answer]- 答案：A
> **A ✓** SnapStart 在發布 version 時先完成初始化並保存執行環境的快照，冷啟動改為從快照還原，Java 的初始化時間可大幅縮短，且不需要為閒置容量付費。要注意快照中的狀態會被多個執行環境共用，因此唯一性的資料要在還原後重建。
>
> **B ✗** Provisioned concurrency 能消除冷啟動，但要為預留的容量持續付費，違反財務要求；尖峰無法預測也難以決定數量。若流量可預測或延遲要求極嚴，它才是更好的選擇。
>
> **C ✗** 提高記憶體會分到更多 CPU，能縮短一些初始化時間，但很難把 6–8 秒壓到 1 秒，且每次執行費用都變高。
>
> **D ✗** 違反「不更換程式語言」，改寫成本也很高。
>
> **考點**：SAP-3.3｜Lambda SnapStart 與 provisioned concurrency 的取捨｜延伸閱讀：第 19 章

### 第 41 題｜SAP｜單選｜D2 理賠 App 直接上傳到 S3

一家產險公司的行動 App 讓保戶上傳理賠照片與影片，單檔最大 2 GB。目前檔案先經過 API 伺服器再轉存到 S3，尖峰時 API 伺服器的負載很高。保戶以 Amazon Cognito user pool 登入。新要求：檔案直接從 App 上傳到 S3；每位保戶只能讀寫自己的資料夾；App 中不能有長期憑證；後端程式盡量少。

哪個方案最合適？

- A. 建立一個 IAM user，把 access key 內嵌在 App 中，並以 IAM policy 限制只能寫入理賠 bucket 的特定 prefix
- B. 建立 Cognito identity pool，以 user pool 的 token 換取 authenticated role 的臨時憑證；IAM policy 只允許對 `arn:aws:s3:::claims-bucket/${cognito-identity.amazonaws.com:sub}/*` 執行 `s3:PutObject` 與 `s3:GetObject`；App 以 SDK 的 multipart upload 上傳
- C. 把 bucket 設為允許匿名寫入，App 為每位保戶產生隨機的長字串 prefix，讓他人無法猜到路徑
- D. 建立 API Gateway 的 S3 proxy integration，App 把檔案以 PUT 傳給 API Gateway，由 API Gateway 寫入 S3

> [!answer]- 答案：B
> **A ✗** 內嵌在 App 的 access key 是長期憑證，很容易被反編譯取出，而且所有保戶共用同一組權限，無法隔離。
>
> **B ✓** Identity pool 把已登入的使用者對應到 IAM role 並發放臨時憑證；policy variable `${cognito-identity.amazonaws.com:sub}` 會代入每位使用者的 identity ID，讓同一份 policy 自動限制每人只能存取自己的 prefix。App 直接以 multipart upload 上傳大檔，後端不需轉送。
>
> **C ✗** 匿名寫入的 bucket 會被濫用，隨機 prefix 不是存取控制，也違反新 bucket 預設的 Block Public Access 原則。
>
> **D ✗** API Gateway 的 payload 上限為 10 MB，2 GB 的影片無法通過。若要由後端控制，常見做法是由 API 發 presigned URL，讓 App 直接上傳 S3。
>
> **考點**：SAP-2.3｜Cognito identity pool 與 policy variable 做使用者層級隔離｜延伸閱讀：第 13、22 章

### 第 42 題｜SAP｜單選｜D1 私有 API 的 DNS failover

一家連鎖超市的門市系統透過 private hosted zone 中的 `inventory.internal.example` 呼叫庫存 API。這個 API 部署在 us-east-1 與 us-west-2 各一個 internal ALB 後面，門市經 Direct Connect 可以連到兩個 Region。團隊希望 us-east-1 不健康時，DNS 自動把門市導向 us-west-2。工程師為 internal ALB 的私有 IP 建立了 Route 53 health check，但 health check 一直顯示不健康。

哪個做法能正確實現自動 failover？

- A. 在 internal ALB 的 security group 加入 Route 53 health checker 的 IP 範圍，允許它們連到 ALB 的私有 IP
- B. 把兩個 Region 的 ALB 改成 internet-facing，讓 Route 53 health checker 可以直接檢查
- C. 改用 latency routing，讓門市自動連到延遲較低的 Region，不再需要 health check
- D. 在 us-east-1 以 ALB 的指標（例如 `HealthyHostCount` 或 5xx 比例）或 CloudWatch Synthetics canary 的結果建立 CloudWatch alarm，再建立以該 alarm 狀態為判斷依據的 Route 53 health check，並在 private hosted zone 設定 failover routing 的 primary 與 secondary 記錄

> [!answer]- 答案：D
> **A ✗** Route 53 health checker 位於 Internet 上，根本無法路由到 VPC 內的私有 IP，開放 security group 也沒有用。
>
> **B ✗** 為了 health check 把內部 API 暴露到 Internet，大幅擴大攻擊面，違反內部服務的設計原則。
>
> **C ✗** Latency routing 在沒有 health check 的情況下不會避開故障的 Region，門市仍可能被導到 us-east-1。
>
> **D ✓** 對私有資源，標準做法是以 CloudWatch alarm 為基礎的 health check：alarm 在 VPC 內評估實際指標，Route 53 依 alarm 狀態判斷健康與否。Private hosted zone 支援 failover routing，搭配這類 health check 就能自動切換。
>
> **考點**：SAP-1.3｜私有端點的 health check 以 CloudWatch alarm 為依據｜延伸閱讀：第 9 章

### 第 43 題｜SAP｜單選｜D4 漸進式拆分 monolith

一家服飾電商的 15 年 Java monolith 已 rehost 到 EC2，放在 ALB 後面，涵蓋商品目錄、購物車、結帳與促銷功能。團隊要逐步改成在 ECS on Fargate 上執行的微服務。要求：不能 big-bang 切換；要能依功能逐一導流到新服務，出問題時能快速切回 monolith；共用資料庫要逐步拆分，每個新服務最終擁有自己的資料。

哪個做法最合適？

- A. 凍結 monolith 的新功能開發，用 18 個月重寫全部微服務，完成後在一個週末切換所有流量
- B. 把整個 monolith 包成一個大型 container 部署到 Fargate，完成後即視為微服務化
- C. 以 ALB 作為 façade 採 strangler fig 模式：先把促銷功能做成 Fargate 上的新服務，以 listener rule 把 `/api/promotions/*` 導到新服務的 target group，並以 weighted target group 漸進移轉與回切；新服務擁有自己的資料庫，以事件或 CDC 與 monolith 的資料同步；之後逐一處理其他領域
- D. 在前面放 API Gateway，一次把所有功能改寫為 Lambda function，舊 monolith 保留做為緊急備援

> [!answer]- 答案：C
> **A ✗** 長期重寫再一次切換是 big-bang，風險最高，18 個月內需求還會持續改變。
>
> **B ✗** 這是 replatform，可以作為過渡步驟，但沒有拆分領域，也沒有資料所有權的改變，不算達成目標。
>
> **C ✓** Strangler fig 以 façade 攔截流量，逐一把功能導到新服務：ALB 的 path-based rule 決定哪些請求去新服務，weighted target group 讓你可以先導一小部分流量並隨時切回。從邊界清楚、耦合低的促銷功能開始，資料以事件或 CDC 同步，逐步讓新服務擁有自己的資料。
>
> **D ✗** 一次把所有功能改寫成 Lambda 同樣是 big-bang，只是換了運算平台。
>
> **考點**：SAP-4.4｜Strangler fig 以 ALB 規則與 weighted target group 漸進拆分｜延伸閱讀：第 10、46 章

### 第 44 題｜SAP｜單選｜D2 感測器資料的低成本保存與查詢

一家半導體設備製造商的 12 座工廠每天經 Kinesis Data Streams 送出約 2 TB 的 JSON 感測器資料，目前全部寫入一個 RDS for PostgreSQL（r6g.8xlarge、40 TB gp3）。工程師每週只會做幾次臨時查詢，且多半只查某座工廠、某個感測器最近 30 天的資料。資料要保存 7 年。財務要求以最低成本提供 SQL 查詢能力，且不需要管理伺服器。

哪個架構最合適？

- A. 以 Amazon Data Firehose 消費 Kinesis stream，啟用 record format conversion 把 JSON 轉成 Parquet，並以 dynamic partitioning 依工廠與日期分區寫入 S3；以 Athena 搭配 partition projection 查詢，並以 lifecycle 把舊資料轉到 S3 Standard-IA
- B. 建立 24 小時運作的 Amazon Redshift provisioned cluster（RA3 節點），以 streaming ingestion 從 Kinesis 載入所有資料
- C. 把資料寫入 on-demand 模式的 DynamoDB table，以工廠與感測器為 partition key、時間為 sort key，工程師以 PartiQL 查詢
- D. 保留 RDS for PostgreSQL，購買 3 年期 Reserved Instance，並把 gp3 改為 gp2 以降低儲存費用

> [!answer]- 答案：A
> **A ✓** S3 是最便宜的長期儲存；Parquet 是欄式格式，查詢只讀需要的欄位，搭配工廠與日期分區，Athena 依掃描量計費的成本會大幅下降。Partition projection 免去維護大量分區的 metadata。查詢少、全部 serverless，成本與營運負擔都最低。
>
> **B ✗** Redshift 適合頻繁的複雜分析；每週幾次查詢卻 24 小時運作 provisioned cluster，成本遠高於需求。
>
> **C ✗** DynamoDB 儲存 7 年、每天 2 TB 的資料成本很高，且不適合臨時的 ad hoc 分析查詢。
>
> **D ✗** RI 只降低 compute 費用，40 TB 且持續成長的資料庫儲存仍然昂貴；gp2 也不比 gp3 便宜。
>
> **考點**：SAP-2.6｜時間序列資料改存 S3 Parquet + Athena｜延伸閱讀：第 30、31 章

### 第 45 題｜SAP｜單選｜D3 結帳流程的主動偵測

一家線上家具商兩次都是從社群網路上得知結帳流程壞了：一次是 CDN 設定變更讓第三方付款 iframe 無法載入，另一次是登入頁的 JavaScript 錯誤。兩次事件中後端的 ALB 5xx、延遲與資料庫指標都正常。團隊希望在客戶發現之前就主動偵測到端到端使用者流程的問題，每 5 分鐘從多個 Region 執行一次並保存截圖，失敗時通知值班人員，且不想自建監控伺服器。

哪個做法最合適？

- A. 增加更多 CloudWatch alarm，涵蓋 ALB 的 4xx、5xx、target response time 與資料庫連線數，並縮短評估週期
- B. 建立 CloudWatch Synthetics 的 browser canary，以腳本模擬登入、加入購物車與以付款測試模式結帳的完整流程，在多個 Region 每 5 分鐘執行並保存截圖，失敗時以 CloudWatch alarm 通知值班人員
- C. 在網站加入 CloudWatch RUM，收集真實使用者的頁面錯誤與載入時間，錯誤率上升時發出 alarm
- D. 在後端服務啟用 AWS X-Ray tracing，分析每個請求經過的服務與延遲

> [!answer]- 答案：B
> **A ✗** 兩次事件的後端指標都正常，問題在瀏覽器端與第三方資源，再多的後端 alarm 也看不到。
>
> **B ✓** Synthetics canary 以真實瀏覽器執行腳本，主動從多個地點模擬使用者流程，能抓到前端錯誤、第三方資源載入失敗等後端看不到的問題，並保存截圖與 HAR 協助除錯。即使沒有真實使用者流量也會持續檢查。
>
> **C ✗** RUM 能看到真實使用者遇到的錯誤，是很好的補充，但必須有使用者先遇到問題才會有資料，不符合「在客戶發現之前」的要求。
>
> **D ✗** X-Ray 追蹤後端請求，看不到瀏覽器端的 iframe 或 JavaScript 錯誤。
>
> **考點**：SAP-3.1｜CloudWatch Synthetics 主動監控使用者流程｜延伸閱讀：第 36 章

### 第 46 題｜SAP｜單選｜D1 找出個資存放在哪些 bucket

一家壽險公司在 2 個 Region 共有 75 個帳號、約 4,000 個 S3 bucket。主管機關要求公司能持續掌握保戶個資（身分證字號、銀行帳號）存放在哪些 bucket 中，並在新的個資出現時發出通知。資安團隊在 Security Tooling 帳號工作，希望以受管服務達成；考量成本，不希望每次都完整掃描所有物件。

哪個方案最合適？

- A. 在每個帳號部署 AWS Glue crawler 與自訂的 Lambda function，以正規表示式掃描所有物件內容，結果寫入集中的 DynamoDB table
- B. 在所有帳號啟用 Amazon GuardDuty 的 S3 Protection，偵測含有個資的 bucket 並產生 finding
- C. 在兩個 Region 把 Security Tooling 帳號指定為 Amazon Macie 的 delegated administrator，自動為所有成員帳號啟用 Macie，開啟 automated sensitive data discovery，並建立符合身分證字號格式的 custom data identifier；finding 送到 Security Hub 與 EventBridge 通知
- D. 在所有帳號啟用 Amazon Inspector，掃描 S3 bucket 中的敏感資料並彙整到 delegated administrator 帳號

> [!answer]- 答案：C
> **A ✗** 自建掃描要維護大量程式與基礎設施，完整掃描 4,000 個 bucket 的成本與時間也很高。
>
> **B ✗** GuardDuty S3 Protection 分析 S3 的資料事件，偵測可疑存取行為（例如異常的大量下載），不會檢查物件內容是否含個資。
>
> **C ✓** Macie 是 S3 敏感資料探索服務，以 delegated administrator 集中管理整個組織（每個 Region 各自設定）。Automated sensitive data discovery 以抽樣方式持續評估 bucket，成本遠低於全量掃描；custom data identifier 可以補足當地身分證字號等格式。
>
> **D ✗** Inspector 掃描的是 EC2、container image 與 Lambda 的軟體弱點，不掃描 S3 物件內容。
>
> **考點**：SAP-1.2｜Macie 組織層級的敏感資料探索｜延伸閱讀：第 16 章

### 第 47 題｜SAP｜單選｜D2 新推薦演算法的漸進開放

一家量販店的結帳微服務部署在 ECS 上，每週發布一次程式碼。業務想上線一個新的推薦演算法：先只對某一國家 5% 的使用者開放，兩天內逐步提高比例；若轉換率下降或錯誤率升高要能立即關閉。業務也要求功能開放的節奏不能和程式碼部署綁在一起。

哪個做法最合適？

- A. 以 CodeDeploy 對 ECS service 做 blue/green 部署，先把 5% 流量導到包含新演算法的 task set，觀察兩天後再全量
- B. 把功能開關放在 task definition 的環境變數，每次調整比例時更新 task definition 並重新部署 service
- C. 為新舊兩個版本的 service 各建立一個 DNS 名稱，以 Route 53 weighted record 先導 5% 流量到新版本
- D. 以 AWS AppConfig 建立 multi-variant feature flag，variant 規則同時比對國家並以 `split` 依使用者 ID 取 5%；兩天內分次調高百分比，每次以 deployment strategy 推出新版設定並綁定 CloudWatch alarm 自動回滾；應用程式透過 AppConfig Agent 帶入使用者情境（context）取得並快取 flag

> [!answer]- 答案：D
> **A ✗** Blue/green 是依請求分流，無法鎖定「某國家 5% 的使用者」，而且把功能開放與程式碼部署綁在一起。
>
> **B ✗** 每次調整都要重新部署，速度慢，也無法「立即關閉」；同樣與部署綁定。
>
> **C ✗** DNS 權重依 resolver 分流，不能針對使用者或國家，而且受快取影響，關閉也不即時。
>
> **D ✓** Feature flag 把「功能是否開放」從部署中抽離：程式碼可以早就部署好，由設定決定對誰開放。Multi-variant flag 依應用程式送來的 context（國家、使用者 ID）評估規則，`split` 以使用者 ID 的一致性雜湊選出固定的 5% 使用者，同一位使用者每次都看到同一個版本；調高比例只是更新 flag。要分清楚兩種「百分比」：`split` 控制的是哪些使用者看到新功能，deployment strategy 控制的是新版設定多快推送到各個應用程式執行個體，並在 alarm 觸發時自動回滾到上一版設定；要立即關閉，就把 flag 改為停用並以一次全部推出（AllAtOnce）的 strategy 部署。Agent 在本地快取並評估 flag，不會每次請求都呼叫 API。
>
> **考點**：SAP-2.1｜AppConfig feature flag 分離功能開放與部署｜延伸閱讀：第 37 章

### 第 48 題｜SAP｜選兩項｜D3 EKS 服務的 AZ 與維護韌性

一家美妝電商在 Amazon EKS 上執行購物車服務，共 6 個 replica，節點群組跨 3 個 AZ。一次 AZ 異常時發現 6 個 pod 全部排在同一個 AZ 的節點上，服務整個中斷；另一次節點升級時，drain 動作一次把所有 replica 都驅逐，也造成短暫中斷。團隊要防止這兩類問題再次發生。

哪兩個變更最合適？

- A. 把 replica 數量增加到 20 個，讓 pod 數量多到不可能全部落在同一個 AZ
- B. 把節點改為單一 AZ 的大型 managed node group，減少跨 AZ 的網路延遲
- C. 在 deployment 中加入以 `topology.kubernetes.io/zone` 為 topology key 的 `topologySpreadConstraints`（`maxSkew: 1`），讓 pod 平均分散到各 AZ
- D. 加入以 `kubernetes.io/hostname` 為 topology key 的 required pod anti-affinity，讓每個 pod 落在不同節點上
- E. 為購物車服務建立 PodDisruptionBudget（例如 `minAvailable: 4`），限制 drain 等自願性中斷一次能驅逐的 pod 數量

> [!answer]- 答案：C、E
> **A ✗** 增加 replica 數量不保證分散，scheduler 仍可能把大部分 pod 放在資源較多的 AZ，也會增加成本。
>
> **B ✗** 單一 AZ 讓整個服務暴露在 AZ 故障的風險中，與目標相反。
>
> **C ✓** Topology spread constraint 以 zone 為維度限制各 AZ 之間的 pod 數量差異，6 個 pod 會平均分到 3 個 AZ，任何一個 AZ 故障仍有三分之二的容量。
>
> **D ✗** Hostname anti-affinity 只保證分散到不同節點，這些節點仍可能都在同一個 AZ。若要防的是單一節點故障，它才足夠。
>
> **E ✓** PodDisruptionBudget 讓 drain、節點升級等自願性中斷必須維持最少可用 pod 數，Kubernetes 會分批驅逐，不會一次清空所有 replica。
>
> **考點**：SAP-3.4｜EKS topology spread constraint 與 PodDisruptionBudget｜延伸閱讀：第 21 章

### 第 49 題｜SAP｜單選｜D1 在建立前就擋下不合規資源

一家零售商以 AWS Control Tower 管理 50 個帳號，各應用團隊透過 pipeline 以 CloudFormation 部署資源。資安要求 DynamoDB table 必須啟用 point-in-time recovery、S3 bucket 必須啟用 versioning。目前用 Config rule 偵測，但不合規資源常常存在好幾天才被修正。資安希望這類資源在 CloudFormation 部署時就被拒絕，而不是建立後才偵測；這些設定是在資源建立後透過其他 API 設定的，SCP 難以直接檢查。

哪個做法最合適？

- A. 在相關 OU 啟用 Control Tower 的 proactive controls，以 CloudFormation Hooks 在資源佈建前檢查 DynamoDB PITR 與 S3 versioning，不合規的 stack 操作會失敗
- B. 在相關 OU 啟用 Control Tower 的 detective controls，以 Config rule 每小時評估一次並寄送通知給團隊
- C. 撰寫 SCP，拒絕所有未帶有 PITR 與 versioning 設定的 `dynamodb:CreateTable` 與 `s3:CreateBucket` 呼叫
- D. 移除所有團隊的 CloudFormation 權限，改為只能透過 Service Catalog 申請由平台團隊審核的產品

> [!answer]- 答案：A
> **A ✓** Proactive controls 透過 CloudFormation Hooks 在資源被建立或更新之前檢查屬性，不合規就讓操作失敗，正好是「部署時拒絕」。它只對經由 CloudFormation 佈建的資源有效，這裡團隊都用 CloudFormation，因此適用；可再保留 detective controls 作為補強。
>
> **B ✗** Detective controls 是建立之後才偵測，正是目前的問題。
>
> **C ✗** PITR 與 versioning 是建立 table／bucket 之後才以另外的 API 設定的，建立請求中沒有可以檢查的 condition key，SCP 無法以這種方式強制。
>
> **D ✗** 全部改走 Service Catalog 並人工審核會大幅拖慢交付，限制過度。
>
> **考點**：SAP-1.4｜Control Tower 的 preventive、detective 與 proactive controls｜延伸閱讀：第 14、40 章

### 第 50 題｜SAP｜單選｜D4 600 台 VMware VM 的大規模 rehost

一家工業設備製造商的總部資料中心有 600 台 VMware VM（Windows 與 Linux，版本各異），vSphere 授權 8 個月後到期，不打算續約。應用團隊要求盡量不改程式；每個 wave 的切換窗口只有 4 小時；切換前要先在 AWS 測試啟動；啟動後要自動安裝 CloudWatch agent 與設定 Systems Manager，並依實際用量選擇 instance 大小。

哪個方案最合適？

- A. 以 VM Import/Export 逐台匯出 VMDK 上傳到 S3 再匯入成 AMI，切換時停機重新匯出最新的磁碟
- B. 以 AWS DMS 把每台 VM 的資料複寫到 EC2，再在 EC2 上重新安裝應用程式
- C. 以 AWS Application Migration Service 在來源伺服器安裝 replication agent，持續做區塊層級複寫到 staging area；以 launch template 設定合適的 instance type，先啟動 test instance 驗證，並以 post-launch actions 安裝 agent；每個 wave 在最後同步後 cutover 並 finalize
- D. 以 CloudFormation 在 AWS 重建所有伺服器，由各應用團隊重新安裝與設定應用程式後再搬移資料

> [!answer]- 答案：C
> **A ✗** VM Import 沒有持續複寫，切換時要重新匯出整顆磁碟，600 台在 4 小時窗口內不可行。
>
> **B ✗** DMS 是資料庫遷移服務，不能複寫整台伺服器。
>
> **C ✓** MGN 是大規模 rehost 的標準工具：持續的區塊層複寫讓 cutover 只需等最後一點差異同步；可以在不影響來源的情況下啟動 test instance；launch template 控制 rightsizing；post-launch actions 自動執行 SSM 文件安裝 agent 等設定。
>
> **D ✗** 重建等於 rebuild，600 台在 8 個月內完成不切實際，也違反盡量不改程式的要求。
>
> **考點**：SAP-4.2｜MGN 的持續複寫、測試啟動與 post-launch actions｜延伸閱讀：第 45 章

### 第 51 題｜SAP｜單選｜D2 Spot 轉檔工作被中斷

一家影音平台的轉檔工作每個需要 20–90 分鐘，由 Auto Scaling group 中的 EC2 Spot instance 從 SQS 取得工作執行。Spot 中斷時工作會從頭重來；有時處理時間超過 visibility timeout，同一個工作被另一台 worker 重複處理。結果是許多節目無法在上架期限前完成。公司要繼續使用 Spot 以控制成本，同時滿足期限。

哪個做法最合適？

- A. 全部改用 On-Demand instance，避免 Spot 中斷造成的重做
- B. 使用 price-capacity-optimized 配置策略並分散到多種 instance type 與多個 AZ；worker 收到兩分鐘的中斷通知時把已完成的片段 checkpoint 到 S3，並把訊息的 visibility timeout 設為 0 讓其他 worker 接手續做；處理期間定期延長 visibility timeout，輸出以工作 ID 命名確保重複處理也不會產生錯誤結果
- C. 把 visibility timeout 設為 12 小時，並使用 lowest-price 配置策略以取得最便宜的 Spot instance
- D. 把轉檔改由 Lambda 執行，每個工作一個 invocation，以避免管理 Spot instance

> [!answer]- 答案：B
> **A ✗** 能消除中斷，但放棄了 Spot 的成本優勢，違反要求。
>
> **B ✓** 依容量與價格挑選並分散多種 instance type，可以降低被中斷的機率；兩分鐘通知加上 checkpoint 讓工作不必從頭來；visibility heartbeat 避免長工作被重複領取，idempotent 的輸出命名則讓偶發的重複處理無害。這是 Spot 上執行長工作的標準組合。
>
> **C ✗** Lowest-price 策略集中在最便宜的 pool，被中斷的機率反而較高；12 小時的 visibility timeout 讓中斷後的工作要等很久才會被重試。
>
> **D ✗** Lambda 單次執行最長 15 分鐘，無法處理 20–90 分鐘的轉檔工作。
>
> **考點**：SAP-2.4｜Spot 中斷處理：分散配置、checkpoint 與 visibility heartbeat｜延伸閱讀：第 17、32 章

### 第 52 題｜SAP｜單選｜D3 EKS pod 共用節點 role

一家數位媒體公司在多個 EKS cluster 上執行 40 個微服務，所有 pod 都直接使用節點的 instance role，而這個 role 有 S3、DynamoDB 與 SQS 的廣泛權限。滲透測試證明，入侵任一個 pod 就能讀取所有 S3 bucket。資安要求每個服務只拿到自己需要的權限，CloudTrail 要能區分是哪個服務的呼叫。平台團隊管理很多 cluster，覺得為每個 cluster 維護 OIDC provider 與 trust policy 很麻煩。

哪個方案最合適？

- A. 為每個服務建立 IAM user，把 access key 存成 Kubernetes secret 掛載給 pod 使用
- B. 在每個 cluster 部署 kube2iam 等開源元件，攔截 pod 對 IMDS 的請求並依 annotation 回傳不同 role 的憑證
- C. 為每個服務建立獨立的 node group，各自使用只含該服務權限的 instance role，並以 node selector 把服務固定在自己的 node group
- D. 安裝 EKS Pod Identity Agent add-on，為每個服務的 Kubernetes service account 建立 pod identity association，對應到只含必要權限的 IAM role；把節點 role 縮減到節點本身需要的權限，並把 IMDS 的 hop limit 設為 1，阻止 pod 取得節點憑證

> [!answer]- 答案：D
> **A ✗** Kubernetes secret 中的 access key 是長期憑證，外洩風險高，也沒有自動輪替。
>
> **B ✗** 能達到效果，但要自行維運第三方元件與其高可用，攔截 IMDS 的方式也較脆弱；AWS 已有原生方案。
>
> **C ✗** 每個服務一個 node group 會大幅增加成本與運算資源浪費，也難以管理。
>
> **D ✓** EKS Pod Identity 讓每個 service account 對應到一個 IAM role，pod 取得的是該 role 的臨時憑證，且不需要為每個 cluster 設定 OIDC provider，role 的 trust policy 也可以跨 cluster 重用。限制 IMDS hop limit 能防止 pod 繼續拿到節點 role 的憑證。CloudTrail 中可以看到對應的 role session 與 cluster、namespace 等資訊。
>
> **考點**：SAP-3.2｜EKS Pod Identity 實現 pod 層級最小權限｜延伸閱讀：第 21 章

### 第 53 題｜SAP｜單選｜D1 重疊 CIDR 下的跨帳號服務呼叫

一家零售集團在 25 個帳號中有大量以 ECS、EKS 與 Lambda 執行的微服務，分布在許多 VPC，其中幾個由併購而來的 VPC 都使用 `10.0.0.0/16`。現在服務之間要以 HTTP 與 gRPC 互相呼叫，每個服務都要能以 IAM 決定哪些呼叫端可以存取；網路團隊不想重新編址，也不想維護跨 VPC 的路由。

哪個方案最合適？

- A. 建立 Amazon VPC Lattice service network 並以 AWS RAM 分享給各帳號；各團隊把服務（以 ECS、EKS 或 Lambda 為 target group）註冊為 Lattice service，並把自己的 VPC 關聯到 service network；以 auth policy 搭配 IAM SigV4 驗證控制呼叫權限
- B. 建立 Transit Gateway 並 attach 所有 VPC，以 Transit Gateway route table 控制哪些 VPC 能互通，服務以 security group 限制呼叫端
- C. 為需要互通的 VPC 建立 VPC peering，並在各 VPC 的 route table 加入對方的 CIDR
- D. 為每個服務建立 NLB 與 PrivateLink endpoint service，在每個呼叫端 VPC 建立對應的 interface endpoint

> [!answer]- 答案：A
> **A ✓** VPC Lattice 在應用層連接服務，不依賴 VPC 之間的 IP 路由，因此重疊的 CIDR 不是問題；它原生支援 ECS、EKS、Lambda 等 target，auth policy 可以依 IAM principal 控制每個服務的呼叫權限。以 RAM 分享 service network 後，跨帳號也不必維護路由。
>
> **B ✗** Transit Gateway 依 IP 路由，重疊的 CIDR 無法正確路由；security group 也無法表達 IAM 層級的授權。
>
> **C ✗** VPC peering 不允許 CIDR 重疊，而且數量多時路由維護困難。
>
> **D ✗** PrivateLink 能處理 CIDR 重疊，但每個服務都要建 NLB、每個呼叫端 VPC 都要建 endpoint，數量多時成本與管理負擔很高，也沒有以 IAM 驗證每個請求的原生機制。如果只有少數服務、或需要非 HTTP 的 TCP 服務，PrivateLink 會是合適的選擇。
>
> **考點**：SAP-1.1｜VPC Lattice 處理重疊 CIDR 與 IAM 授權的服務互連｜延伸閱讀：第 7 章

### 第 54 題｜SAP｜單選｜D2 CAD 檔案伺服器的低成本 DR

一家機械設計公司把 20 TB 的 CAD 檔案放在 eu-west-1 的 FSx for Windows File Server（Multi-AZ）。新的 DR 要求是在 eu-central-1 能於 Region 故障時恢復檔案服務，RPO 24 小時、RTO 24 小時，成本要最低。工程師可以接受災難時花一段時間等待還原。

哪個方案最合適？

- A. 在 eu-central-1 建立第二個 Multi-AZ 的 FSx for Windows File Server，以 AWS DataSync 每小時同步一次
- B. 把檔案系統遷移到 FSx for NetApp ONTAP，並以 SnapMirror 複寫到 eu-central-1 的另一個 ONTAP 檔案系統
- C. 以 AWS Backup 建立每日備份計畫，並設定 copy rule 把備份複製到 eu-central-1 的 backup vault；災難時從複本還原成新的 FSx 檔案系統，並更新 DFS namespace 或 DNS 指向
- D. 為 FSx 的底層儲存啟用 S3 cross-Region replication，複寫到 eu-central-1 的 bucket

> [!answer]- 答案：C
> **A ✗** 能滿足需求，但第二個檔案系統全年運作，成本遠高於 RPO 24 小時所需；每小時同步也超出需求。
>
> **B ✗** SnapMirror 適合需要較低 RPO 的情境，但這裡要先遷移整個檔案系統，還要持續運作 DR 端的 ONTAP，成本與工作量都較高。
>
> **C ✓** 每日備份滿足 RPO 24 小時；跨 Region 的備份複本只付儲存費用；災難時從複本還原成新的檔案系統。還原時間隨資料量而定，應以定期演練實測確認能落在 24 小時 RTO 內。平時不需要運作第二個檔案系統，這是最便宜的做法。
>
> **D ✗** FSx for Windows File Server 的資料不是放在你可以設定複寫的 S3 bucket，這個選項在機制上不存在。
>
> **考點**：SAP-2.2｜依 RPO／RTO 選擇最低成本的 FSx DR｜延伸閱讀：第 24、34 章

### 第 55 題｜SAP｜單選｜D3 依資料進行 rightsizing

一家汽車零件製造商在 30 個帳號中有約 400 台 EC2 instance，多數在遷移時依地端規格選型，明顯過大；另有大量 gp2 EBS volume。財務希望以資料為依據，在整個組織進行 rightsizing，建議要考慮記憶體使用率，也要涵蓋 EBS，並盡量減少人工分析。

哪個做法最合適？

- A. 每月檢視 Trusted Advisor 的 Low Utilization Amazon EC2 Instances 檢查結果，依 CPU 使用率手動縮小 instance
- B. 在組織層級啟用 AWS Compute Optimizer（由 management account 或 delegated administrator），在 instance 上安裝 CloudWatch agent 回報記憶體指標，啟用 enhanced infrastructure metrics 延長回溯期間；依 EC2、Auto Scaling group 與 EBS（包含 gp2 改 gp3）的建議，透過變更流程實施
- C. 只使用 Cost Explorer 的 rightsizing recommendations，依建議逐台調整 instance
- D. 先購買 3 年期 Compute Savings Plans 涵蓋現有用量，以折扣抵銷 instance 過大的浪費

> [!answer]- 答案：B
> **A ✗** 只看 CPU 會忽略記憶體瓶頸，可能把需要大量記憶體的 instance 縮得太小；也不涵蓋 EBS。
>
> **B ✓** Compute Optimizer 以機器學習分析使用率，涵蓋 EC2、Auto Scaling group、EBS、Lambda 等；有了 CloudWatch agent 的記憶體指標，建議會考慮記憶體；enhanced infrastructure metrics 把回溯期延長到 3 個月，能看到月底等週期性尖峰。組織層級啟用後可以集中檢視。
>
> **C ✗** Cost Explorer 的 rightsizing 建議只涵蓋 EC2 instance，不包含 EBS volume，無法滿足需求。
>
> **D ✗** 在 rightsizing 之前先承諾用量，等於把過大的規格鎖定 3 年。正確順序是先 rightsizing，再依新的基準購買 Savings Plans。
>
> **考點**：SAP-3.5｜Compute Optimizer 組織層級 rightsizing 與先後順序｜延伸閱讀：第 39 章

### 第 56 題｜SAP｜單選｜D1 工廠斷線時的資料緩衝

一家紡織機械製造商在 300 座客戶工廠部署了閘道器，以 MQTT 收集機台資料後送到 AWS 的 Kinesis Data Streams。偏遠工廠的對外網路有時會中斷長達 6 小時，中斷期間的資料目前全部遺失。新的要求是：斷線期間資料要先保存在本地，恢復連線後自動上傳；靠近機台的異常偵測模型在斷線時也要能繼續運作；300 台閘道器上的軟體要能集中部署與更新。

哪個方案最合適？

- A. 把 Kinesis Data Streams 的 retention 延長到 7 天，確保資料有足夠時間被消費
- B. 讓 PLC 直接以 SDK 呼叫 Kinesis 的 `PutRecords`，失敗時把資料暫存在記憶體並重試
- C. 為每座工廠加裝 4G 備援線路，以 Site-to-Site VPN 在主線路中斷時自動切換
- D. 在閘道器上執行 AWS IoT Greengrass V2：以 stream manager component 把資料持久化到本地磁碟並在恢復連線後匯出到 Kinesis Data Streams；以 ML inference component 在本地執行異常偵測；以 thing group 為目標集中部署元件

> [!answer]- 答案：D
> **A ✗** Retention 控制的是資料進入 stream 之後保留多久，斷線期間資料根本進不了 stream，延長 retention 沒有幫助。
>
> **B ✗** 記憶體容量有限，6 小時的資料量可能超出，閘道器重啟時也會遺失；而且沒有處理本地推論與集中部署。
>
> **C ✗** 備援線路能降低斷線機率，但增加每座工廠的成本，仍不保證不斷線，也沒有解決本地推論與軟體部署的需求。
>
> **D ✓** Greengrass 是邊緣運行環境：stream manager 在本地緩衝資料並在連線恢復時自動上傳到 Kinesis 等目的地；ML 推論在本地執行，不依賴雲端；元件可以透過 deployment 集中推送到 thing group 中的所有裝置。
>
> **考點**：SAP-1.3｜邊緣斷線韌性：Greengrass stream manager 與本地推論｜延伸閱讀：第 31 章

### 第 57 題｜SAP｜選兩項｜D4 遷移評估的資料收集

一家保險集團在兩個資料中心有約 1,200 台伺服器，CMDB 資料已多年未更新。集團在 2025 年上半年曾以 Migration Hub 與 Application Discovery Service 對少量伺服器做過試點，因此是這兩項服務的既有客戶，帳號仍可繼續使用。CIO 需要在 6 週內向董事會提出遷移的 business case，內容必須包含依實際用量 rightsizing 後的 AWS 成本與授權最佳化；之後的 wave 規劃則需要了解伺服器之間的相依關係，以便把互相呼叫的伺服器排在同一個 wave。

哪兩個做法最合適？

- A. 寄送試算表給各應用負責人，請他們填寫伺服器規格、使用率與相依的系統
- B. 在地端伺服器啟用 AWS Config，記錄設定與資源關聯，作為相依分析的依據
- C. 在資料中心的核心交換器啟用 VPC Flow Logs，分析伺服器之間的連線
- D. 部署 Migration Evaluator 的 agentless collector 收集一段期間的伺服器使用率，產出包含 rightsizing 與授權最佳化的 TCO 評估報告
- E. 在伺服器上安裝 AWS Application Discovery Service 的 discovery agent，收集程序與網路連線資料，用來繪製伺服器相依關係並分組成應用程式

> [!answer]- 答案：D、E
> **A ✗** 人工填寫既慢又不準確，CMDB 已經過時正是因為依賴人工維護；6 週內很難收齊 1,200 台的資料。
>
> **B ✗** AWS Config 記錄的是 AWS 資源的設定，不能用來盤點地端伺服器。
>
> **C ✗** VPC Flow Logs 只適用於 VPC 內的網路介面，地端交換器無法啟用。
>
> **D ✓** Migration Evaluator 以實際使用率資料估算 rightsizing 後的 AWS 成本，並分析授權（例如 Windows、SQL Server）的最佳化選項，產出的報告就是 business case 的核心材料。
>
> **E ✓** Agent 型的探索能收集伺服器上執行的程序與實際網路連線，這是推導伺服器相依關係的關鍵資料；只收集 VM 規格與使用率的 agentless 方式看不到這些。注意服務現況：Migration Hub 與 ADS 自 2025-11-07 起不再對新客戶開放，本題集團因為先前用過而屬於既有客戶，才能選 E；若是從未使用過的組織，要改用 AWS Transform 提供的探索收集器與 dependency mapping（或合作夥伴工具），Migration Evaluator 則仍持續提供。
>
> **考點**：SAP-4.1｜Business case 與相依探索的資料來源｜延伸閱讀：第 44 章

### 第 58 題｜SAP｜選兩項｜D2 取代跳板機的安全存取

一家電子製造商的 EC2 instance 位於沒有 NAT Gateway 也沒有 Internet Gateway 的 private subnet（與工廠 OT 網路相鄰）。維運人員目前透過一台 bastion host 以共用的 SSH 金鑰登入。新的資安要求：移除所有 inbound port 與 bastion；登入要透過既有的 IAM Identity Center 並強制 MFA；完整記錄每個 session 的指令並以加密方式保存到 S3 供稽核；不能新增任何 Internet 出口。

哪兩個步驟組合起來能滿足需求？

- A. 為 instance 附加含 `AmazonSSMManagedInstanceCore` 的 instance profile（或啟用 Default Host Management Configuration），確認已安裝 SSM Agent，並在 Session Manager 偏好設定中啟用 session log，以 KMS 加密寫入 S3 與 CloudWatch Logs
- B. 建立 EC2 Instance Connect Endpoint，讓維運人員不經過 bastion 以 SSH 連到 private instance，並移除 bastion
- C. 為 VPC 建立 `ssm`、`ssmmessages` 的 interface endpoint（較舊的 agent 版本另需 `ec2messages`），並建立 S3 gateway endpoint 與 CloudWatch Logs interface endpoint 讓 session log 能從 VPC 內送出
- D. 把 bastion host 移到 public subnet，並在 bastion 上設定以 Identity Center 為來源的 PAM 模組強制 MFA
- E. 改用 Systems Manager Run Command 執行維運指令，並關閉所有互動式登入

> [!answer]- 答案：A、C
> **A ✓** Session Manager 透過 SSM Agent 主動向外建立連線，不需要任何 inbound port；使用者以 Identity Center 登入 AWS 後開啟 session，MFA 由 Identity Center 強制。Session log 會記錄完整的指令與輸出，並可用 KMS 加密送到 S3 與 CloudWatch Logs。
>
> **B ✗** EC2 Instance Connect Endpoint 不需要 bastion，但本質仍是 SSH：instance 的 security group 要允許來自 endpoint 的 22 port，也不提供 session 指令的完整記錄。若只是要移除 bastion 與 public IP，它是可行的選擇。
>
> **C ✓** 沒有 Internet 出口的 subnet 中，SSM Agent 必須透過 interface endpoint 連到 Systems Manager；session log 送到 S3 與 CloudWatch Logs 也需要對應的 endpoint，否則記錄會失敗。
>
> **D ✗** Bastion 仍然存在，也仍有 inbound SSH，違反移除 bastion 與 inbound port 的要求。
>
> **E ✗** Run Command 不提供互動式 session，維運人員無法除錯；需求是取代登入方式，不是取消登入。
>
> **考點**：SAP-2.3｜Session Manager 在無 Internet subnet 的必要設定｜延伸閱讀：第 38 章

### 第 59 題｜SAP｜單選｜D1 研發帳號的超支自動煞車

一家影音串流公司的 `R&D` OU 下有 25 個實驗帳號，每個帳號每月預算 5,000 美元。過去常有工程師忘記關閉 GPU instance，月底帳單暴增。財務要求：某帳號的實際支出達到預算 100% 時，自動阻止該帳號再建立新的 EC2 與 SageMaker 資源，但保留既有資料；要解除限制必須經財務核准；平台團隊不想維護自訂程式。

哪個做法最合適？

- A. 在 management account 為每個實驗帳號建立 AWS Budgets 預算，設定 budget action：實際支出達 100% 時對該帳號套用一個拒絕 `ec2:RunInstances` 與 SageMaker 建立類動作的 SCP；解除時由財務核准後移除 SCP
- B. 為 R&D OU 啟用 AWS Cost Anomaly Detection，偵測到異常支出時寄送通知給帳號負責人
- C. 在每個帳號建立 CloudWatch billing alarm，達到 5,000 美元時發 SNS 通知給平台團隊手動處理
- D. 撰寫每天執行的 Lambda function，以 Cost Explorer API 查詢每個帳號的支出，超過預算時直接終止該帳號所有 EC2 instance

> [!answer]- 答案：A
> **A ✓** Budget action 可以在預算門檻觸發時自動套用 IAM policy 或 SCP，或停止特定的 EC2／RDS instance；套用 SCP 的 action 要從 management account 設定。SCP 只阻止新建，既有資料不受影響；解除限制是可控的人工步驟，符合財務核准的要求。
>
> **B ✗** Anomaly Detection 只會通知，不會阻止支出，而且它偵測的是「異常」，穩定地花到預算上限不一定會被判為異常。
>
> **C ✗** Billing alarm 只會發出通知，處理仍靠平台團隊手動介入，無法自動阻止新資源，也沒有財務核准的解除流程。
>
> **D ✗** 需要自訂程式，終止所有 instance 還可能刪除未保存的資料（instance store、刪除時一起刪除的 EBS），違反保留資料的要求。
>
> **考點**：SAP-1.5｜AWS Budgets action 自動套用 SCP｜延伸閱讀：第 39 章

### 第 60 題｜SAP｜單選｜D3 月底報表時段的 Redshift 排隊

一家壽險公司的精算部門使用 4 個節點的 Amazon Redshift provisioned cluster（RA3）。每月月底 3 天，約 200 位分析師同時查詢儀表板與報表，查詢排隊超過 20 分鐘；其餘時間 cluster 的使用率只有約 30%。團隊希望月底尖峰時查詢效能穩定，但不想為了尖峰全年支付更大規模的 cluster。

哪個做法最合適？

- A. 把 cluster 永久擴充到 12 個節點，確保月底尖峰有足夠容量
- B. 每月月底前以 classic resize 把 cluster 擴充到 12 個節點，月底後再縮回 4 個節點
- C. 為 BI 查詢所在的 WLM queue 啟用 concurrency scaling，並設定 usage limit 控制額外費用；搭配 automatic WLM 與 query priority，讓重要查詢優先執行
- D. 把精算資料遷移到 Aurora PostgreSQL，以多個 Aurora Replica 分擔分析查詢

> [!answer]- 答案：C
> **A ✗** 全年支付 3 倍節點費用，但只有每月 3 天需要，違反成本要求。
>
> **B ✗** Classic resize 耗時較長，期間 cluster 為唯讀，每月執行兩次的營運負擔與影響都不小。
>
> **C ✓** Concurrency scaling 在查詢排隊時自動加入暫時的運算容量處理讀取查詢，尖峰過後自動釋放，只為實際使用的時間付費（並有每日累積的免費額度）；usage limit 可以設定上限避免費用失控。正好對應「短時間的高並發」。
>
> **D ✗** Aurora 是 OLTP 資料庫，不適合大規模分析查詢；遷移本身也是大型專案。
>
> **考點**：SAP-3.3｜Redshift concurrency scaling 應對週期性高並發｜延伸閱讀：第 30 章

### 第 61 題｜SAP｜單選｜D4 地端 AD 斷線時的身份認證

一家重型機械製造商要把 Windows 應用程式與檔案伺服器遷移到 AWS（EC2 與 FSx for Windows File Server）。地端 Active Directory 樹系有 8,000 位使用者，仍是唯一的身份來源，公司不希望使用者有第二個網域帳號。要求：總部與 AWS 之間的 Direct Connect 中斷時，AWS 上的應用程式仍要能驗證使用者，FSx 也要能繼續提供服務；Kerberos 認證的延遲要低。

哪個方案最合適？

- A. 在 AWS 部署 AD Connector，把 EC2 與 FSx 加入地端網域，認證請求由 AD Connector 轉送到地端 domain controller
- B. 部署 AWS Managed Microsoft AD，與地端樹系建立單向信任，把 EC2 與 FSx 加入 Managed AD 網域，地端使用者透過信任存取
- C. 部署 Simple AD，以排程腳本從地端 AD 同步使用者帳號與密碼到 Simple AD
- D. 在兩個 AZ 的 EC2 上部署地端網域的額外 domain controller，在 AD Sites and Services 為 AWS 建立新的 site 與 subnet，經 Direct Connect 複寫；EC2 與 FSx 加入同一個網域，VPC 的 DNS 指向這些 domain controller

> [!answer]- 答案：D
> **A ✗** AD Connector 只是代理，不保存任何目錄資料，所有認證都要到地端 domain controller，Direct Connect 中斷時就無法認證。
>
> **B ✗** 使用者帳號仍在地端樹系，透過信任認證時仍要聯絡地端 domain controller；連線中斷時地端使用者一樣無法認證。若使用者可以放在 Managed AD 網域、地端只是資源端，B 才會成立。
>
> **C ✗** Simple AD 不支援信任關係，以腳本同步密碼既不安全也不可靠，而且讓使用者有第二套帳號。
>
> **D ✓** 把地端網域延伸到 AWS：AWS 中的 domain controller 持有完整的目錄複本，斷線時仍能在本地完成認證；以 AD site 設定讓 AWS 的用戶端優先找同一個 site 的 domain controller，Kerberos 延遲最低。FSx for Windows 支援加入自行管理的 AD。
>
> **考點**：SAP-4.3｜混合 AD 架構：AD Connector、Managed AD 信任與延伸 domain controller｜延伸閱讀：第 13、24 章

### 第 62 題｜SAP｜單選｜D2 商品頁的微秒級讀取

一家 3C 電商的商品詳情服務直接讀取 DynamoDB 中的商品資料（屬性與價格），大型促銷時每秒約 80 萬次讀取，p99 延遲 8 毫秒，新目標是 1 毫秒以下。商品資料每小時只更新幾次，幾秒內的最終一致性可以接受。服務以 DynamoDB SDK 撰寫，團隊不想大幅修改資料存取程式。

哪個方案最合適？

- A. 在 DynamoDB 前加入 ElastiCache（Valkey 或 Redis OSS），以 cache-aside 模式在應用程式中讀取快取，資料更新時由程式主動清除快取
- B. 建立 DynamoDB Accelerator（DAX）cluster，節點分布在多個 AZ；應用程式把 DynamoDB client 換成 API 相容的 DAX client，eventually consistent 讀取由 DAX 的 item cache 回應，並設定合適的 TTL
- C. 把所有讀取改為 strongly consistent read，避免讀到舊資料造成快取不一致
- D. 把 table 轉為 global table 並在多個 Region 建立 replica，讓每個 Region 的服務讀取本地 replica

> [!answer]- 答案：B
> **A ✗** ElastiCache 也能做到次毫秒延遲，但需要在程式中實作快取讀取與失效邏輯，修改幅度比換成 DAX client 大得多。如果快取的是跨多個 table 的組合結果，ElastiCache 會更有彈性。
>
> **B ✓** DAX 是 DynamoDB 專用、API 相容的記憶體內快取，讀取命中時延遲為微秒等級；只要替換 client，查詢程式不必重寫。DAX 只快取 eventually consistent 讀取，正好符合可接受最終一致性的條件。
>
> **C ✗** Strongly consistent read 不會被 DAX 快取，延遲與成本都比 eventually consistent read 高，與目標相反。
>
> **D ✗** Global table 改善的是跨 Region 使用者的延遲，同一 Region 內的讀取仍是毫秒等級，達不到 1 毫秒以下。
>
> **考點**：SAP-2.5｜DAX 與 ElastiCache 的選擇｜延伸閱讀：第 27、28 章

### 第 63 題｜SAP｜單選｜D1 只能連到核准網域的集中 egress

一家工業自動化公司在 15 個帳號中有 40 個 VPC，每個 VPC 都有自己的 NAT Gateway，security group 允許所有對外 443 流量。資安新規定：所有工作負載只能以 HTTPS 連到核准的外部網域（例如原廠更新伺服器與 `*.partner.example`），其他目的地一律阻擋；所有對外連線要集中記錄；方案要能自動擴展，不想自己維運防火牆主機。

哪個方案最合適？

- A. 建立集中的 egress VPC 並以 Transit Gateway 連接所有 VPC；在 egress VPC 部署 AWS Network Firewall，使用 stateful domain list rule group 以 TLS SNI 與 HTTP Host 允許核准網域、預設拒絕其他流量，之後才經過 NAT Gateway 出去；Transit Gateway 的 VPC attachment 啟用 appliance mode；移除各 VPC 自己的 NAT Gateway，並把 firewall log 送到 S3
- B. 在每個 VPC 的 security group 以網域名稱設定 outbound rule，只允許連到核准的網域
- C. 在每個 VPC 的 NACL 設定只允許核准廠商的 IP 範圍、拒絕其他所有對外流量
- D. 在每個 VPC 啟用 Route 53 Resolver DNS Firewall，只允許解析核准的網域，其餘 DNS 查詢回傳 NXDOMAIN

> [!answer]- 答案：A
> **A ✓** Network Firewall 是受管、自動擴展的防火牆，domain list rule group 可以依 TLS SNI 與 HTTP Host 過濾網域。集中 egress 架構讓 40 個 VPC 共用一組檢查點與記錄；appliance mode 確保同一條連線的往返流量走同一個 AZ 的防火牆端點，避免非對稱路由。
>
> **B ✗** Security group 只能以 IP、CIDR、prefix list 或其他 security group 作為規則來源與目的，不支援網域名稱。
>
> **C ✗** 廠商的 IP 經常變動，靜態 IP 清單難以維護；NACL 是 stateless，要額外處理回程的 ephemeral port，且要在 40 個 VPC 各自維護。
>
> **D ✗** DNS Firewall 只控制名稱解析，工作負載若直接以 IP 連線就能繞過；它是很好的補充層，但單獨使用無法保證「其他目的地一律阻擋」，也不記錄實際連線。
>
> **考點**：SAP-1.2｜集中 egress 以 Network Firewall 做網域過濾｜延伸閱讀：第 16、41 章

### 第 64 題｜SAP｜單選｜D3 告警風暴與部署期間的雜訊

一家產險公司的保單管理系統有約 300 個 CloudWatch alarm。一次資料庫異常時，值班人員在 10 分鐘內收到 80 通呼叫，全都是同一個根因；每週部署窗口期間也會有大量 alarm 短暫觸發，造成雜訊。團隊希望只在多個訊號共同顯示客戶受影響時才呼叫值班人員，部署期間自動抑制通知，同時保留個別 alarm 作為診斷資訊。

哪個做法最合適？

- A. 把所有 alarm 的評估週期延長到 30 分鐘，降低短暫波動造成的觸發
- B. 每次部署前由值班人員手動停用所有 alarm 的 action，部署完成後再啟用
- C. 建立 composite alarm，以規則運算式組合訊號，例如 `ALARM(api-5xx) AND (ALARM(api-latency) OR ALARM(db-cpu))`，只在 composite alarm 上設定呼叫；個別 alarm 移除通知 action 但保留狀態；並以代表「部署進行中」的 alarm 作為 composite alarm 的 actions suppressor
- D. 把所有 alarm 改為 anomaly detection 門檻，讓 CloudWatch 自動學習每個指標的正常範圍

> [!answer]- 答案：C
> **A ✗** 延長評估週期會讓真正的事件晚 30 分鐘才被發現，代價太高；同一根因仍會觸發大量 alarm。
>
> **B ✗** 手動操作容易忘記重新啟用，部署期間發生的真實事件也會被漏掉。
>
> **C ✓** Composite alarm 把多個 alarm 的狀態以 AND／OR／NOT 組合，只在組合條件成立時通知，一個根因只會產生一次呼叫；個別 alarm 仍保留狀態供診斷。Actions suppressor 讓指定的 alarm 處於 ALARM 時暫停 composite alarm 的 action，可用來在部署期間自動抑制通知。
>
> **D ✗** Anomaly detection 改善的是門檻設定，但每個 alarm 仍各自通知，告警風暴與部署雜訊都還在。
>
> **考點**：SAP-3.1｜Composite alarm 與 actions suppressor 降低告警雜訊｜延伸閱讀：第 36 章

### 第 65 題｜SAP｜選兩項｜D2 防止 stack 更新誤刪有狀態資源

一家證券公司的核心帳務 stack 以 CloudFormation 管理，包含一個 RDS DB instance 與一個 DynamoDB table。一位工程師修改 template 時更改了 DB instance identifier，觸發資源 replacement，舊資料庫被刪除，最後從備份還原，停機 3 小時。團隊要建立護欄：stack 更新時不能意外替換或刪除這些有狀態資源；即使 stack 被刪除，資料也要保留；pipeline 仍要能正常更新其他資源。

哪兩個措施組合起來最能滿足需求？

- A. 為 stack 啟用 termination protection，防止 stack 被刪除
- B. 為 stack 設定 stack policy，對 RDS 與 DynamoDB 的 logical ID 拒絕 `Update:Replace` 與 `Update:Delete`；pipeline 先建立 change set，若這些資源的 change 顯示需要 replacement 就讓 pipeline 失敗並要求人工審查
- C. 每天執行 drift detection，發現 RDS 或 DynamoDB 的設定與 template 不同時發出通知
- D. 在 template 中為 RDS 設定 `DeletionPolicy: Snapshot` 與 `UpdateReplacePolicy: Snapshot`，為 DynamoDB table 設定 `DeletionPolicy: Retain` 與 `UpdateReplacePolicy: Retain`，並啟用 RDS 的 deletion protection
- E. 把 RDS 與 DynamoDB 從 template 中移除，改由 DBA 手動管理，避免 IaC 變更影響資料庫

> [!answer]- 答案：B、D
> **A ✗** Termination protection 只防止整個 stack 被刪除，不會阻止 stack 更新時替換或刪除個別資源，這次事故就是更新造成的。
>
> **B ✓** Stack policy 讓更新時對指定資源的替換或刪除直接失敗，其他資源照常更新；change set 讓 pipeline 在執行前就看到哪些資源會被替換，可以提早攔截。
>
> **C ✗** Drift detection 比較的是實際設定與 template 是否一致，無法阻止由 template 本身引起的替換。
>
> **D ✓** `DeletionPolicy` 決定資源從 stack 移除或 stack 被刪除時的處理，`UpdateReplacePolicy` 決定被替換時舊資源的處理；設為 Snapshot 或 Retain 後，即使發生替換或刪除，資料也會留下。RDS deletion protection 再多一層保護。
>
> **E ✗** 把資料庫移出 IaC 會失去版本控制與審查，回到手動管理的風險。
>
> **考點**：SAP-2.1｜Stack policy、change set 與 DeletionPolicy／UpdateReplacePolicy｜延伸閱讀：第 37 章

### 第 66 題｜SAP｜單選｜D1 工廠團隊自助申請標準環境

一家食品機械製造商有 35 個工廠 IT 團隊，每個團隊有自己的 AWS 帳號，都在 `Plants` OU 下。團隊需要自行啟動經核准的環境（使用強化過的 AMI、指定的 VPC subnet、強制 tag 的 EC2 與相關資源），但資安不允許他們擁有建立 IAM role 或任意建立 EC2 的廣泛權限。雲端平台團隊希望只在一個地方維護產品與版本。

哪個做法最合適？

- A. 給各團隊 `PowerUserAccess`，並以 SCP 限制只能在核准的 Region 操作
- B. 在平台帳號建立 Service Catalog portfolio，放入以 CloudFormation 定義的產品，透過 Organizations 把 portfolio 分享給 `Plants` OU 並啟用 principal 名稱分享；為產品設定 launch constraint，指定一個具備佈建權限的 IAM role；團隊使用者只需要 Service Catalog end user 權限；新版本在平台帳號集中更新
- C. 以 AWS RAM 把強化過的 AMI 與 subnet 分享給各帳號，讓團隊依文件自行建立環境
- D. 以 CloudFormation StackSets 把標準環境預先部署到所有工廠帳號，由平台團隊依工單調整數量

> [!answer]- 答案：B
> **A ✗** PowerUserAccess 允許建立幾乎所有資源（除了 IAM 管理），遠超出需要，也無法確保團隊使用強化 AMI 與指定 subnet。
>
> **B ✓** Service Catalog 讓使用者只能從核准的產品中選擇並填入允許的參數；launch constraint 讓實際佈建由指定 role 執行，使用者本身不需要 EC2 或 IAM 的權限。跨帳號分享時，launch constraint 通常以 role 名稱（local role name）指定，並事先把同名 role 部署到各工廠帳號（例如用 StackSets）。Portfolio 透過 Organizations 分享給 OU，新帳號自動取得，產品版本只在平台帳號維護一次。
>
> **C ✗** 分享 AMI 與 subnet 只提供材料，團隊仍需要廣泛權限自行建立資源，也無法保證遵循標準。
>
> **D ✗** 預先部署無法讓團隊依需求自助申請，平台團隊會變成瓶頸。
>
> **考點**：SAP-1.4｜Service Catalog 跨帳號分享與 launch constraint｜延伸閱讀：第 40 章

### 第 67 題｜SAP｜單選｜D4 大型 MySQL 的最小停機遷移

一家連鎖書店要把地端 MySQL 8.0 資料庫（4 TB，尖峰每秒約 5,000 筆交易，大量使用 trigger 與 stored procedure）遷移到 Aurora MySQL，切換時的停機不得超過 15 分鐘。地端與 AWS 之間有 5 Gbps 的 Direct Connect。先前以 AWS DMS 測試時，full load 需要 4 天以上，含 LOB 欄位的 table 特別慢，團隊希望找到更快的初始載入方式。

哪個方案最合適？

- A. 以 `mysqldump` 匯出整個資料庫，經 Direct Connect 傳到 EC2 後再匯入 Aurora MySQL，在週末停機期間完成
- B. 以 AWS DMS 只做 full load，安排在週末兩天停機期間執行，完成後直接切換
- C. 以 AWS Application Migration Service 把 MySQL 伺服器複寫到 EC2，切換後再把 EC2 上的 MySQL 升級為 Aurora
- D. 以 Percona XtraBackup 建立實體備份並上傳到 S3，從 S3 還原成 Aurora MySQL cluster，並另外匯出使用者帳號、stored procedure 與 function 的定義在 Aurora 上重建；之後設定從地端來源到 Aurora 的 binlog replication，待複寫延遲歸零後停寫切換

> [!answer]- 答案：D
> **A ✗** 4 TB 的邏輯匯出匯入需要很長時間，期間必須停機，遠超過 15 分鐘。
>
> **B ✗** 4 天的 full load 無法塞進週末，而且沒有 CDC，停機時間更長。
>
> **C ✗** MGN 只會把 MySQL 原樣搬到 EC2，無法「升級」成 Aurora，Aurora 是受管服務，不是安裝在 EC2 上的軟體。
>
> **D ✓** 同質的 MySQL 8.0 到 Aurora MySQL（version 3）遷移，Aurora 可以直接用 Percona XtraBackup 的實體備份檔建立新 cluster，比逐筆的邏輯載入快得多（未壓縮備份上限 64 TiB，4 TB 沒有問題）。要注意這種還原不會帶入使用者帳號、function、stored procedure 與時區資訊，必須事先另外匯出定義（例如 `mysqldump --no-data --routines`）並在 Aurora 上重建，也要先確認來源沒有使用加密等不支援的設定。還原後以 binlog replication 追上備份之後的變更，切換時只需要停寫、等延遲歸零、切換連線，可以在 15 分鐘內完成。
>
> **考點**：SAP-4.2｜同質 MySQL 遷移：實體備份還原 + binlog replication｜延伸閱讀：第 26、45 章

### 第 68 題｜SAP｜單選｜D3 直播期間的 Kinesis 熱分區

一家影音平台以 Kinesis Data Streams（on-demand 模式）收集 2,000 萬台裝置的觀看事件，partition key 是頻道 ID。一場大型直播賽事期間，約 70% 的事件都來自同一個頻道，producer 大量收到 `ProvisionedThroughputExceededException` 並丟棄事件，但整個 stream 的總吞吐量遠低於可用容量。分析端只需要依頻道彙總觀看人數，不要求同一頻道事件之間的嚴格順序。

哪個做法最能解決問題？

- A. 把 partition key 改為高基數的值（例如裝置 ID，或頻道 ID 加隨機後綴），讓寫入分散到多個 shard；由消費端依頻道彙總；producer 以指數退避重試
- B. 把 stream 改為 provisioned 模式，並把 shard 數量增加為目前的兩倍
- C. 把 stream 的 retention 延長到 7 天，讓消費端有更多時間處理事件
- D. 為消費端啟用 enhanced fan-out，提高每個 consumer 的讀取吞吐量

> [!answer]- 答案：A
> **A ✓** 同一個 partition key 一定會進入同一個 shard，而每個 shard 的寫入有上限（每秒 1 MB 或 1,000 筆記錄），on-demand 模式也一樣。改用高基數的 key 讓熱門頻道的事件分散到許多 shard；既然不需要同頻道的嚴格順序，彙總交給消費端即可。
>
> **B ✗** Shard 再多，同一個 key 仍只會寫入其中一個 shard，熱分區問題不變。
>
> **C ✗** Retention 影響的是資料保留多久，與寫入被限流無關。
>
> **D ✗** Enhanced fan-out 提高的是讀取端吞吐量，這次的瓶頸在寫入端。
>
> **考點**：SAP-3.4｜Kinesis 熱 partition key 與 shard 寫入上限｜延伸閱讀：第 31 章

### 第 69 題｜SAP｜單選｜D2 事件匯流排的 Region 備援

一家支付公司的 30 個 producer 服務把付款狀態事件送到 us-east-1 的 EventBridge custom event bus，再由規則分送到 SQS 與 Lambda。新的韌性要求：us-east-1 的 EventBridge 受損時，事件發送要在數分鐘內自動切換到 us-west-2；完成一次性的設定調整後，切換時 producer 不需要任何修改；切換期間的事件也要能在恢復後補送給原本的 Region。

哪個方案最合適？

- A. 修改所有 producer 的程式，讓每個事件同時送到 us-east-1 與 us-west-2 的 event bus，由消費端自行去重
- B. 在 us-east-1 的 event bus 建立規則，把所有事件轉送到 us-west-2 的 event bus，us-east-1 故障時再由維運人員把 producer 設定改指向 us-west-2
- C. 建立 EventBridge global endpoint，以 us-east-1 為 primary、us-west-2 為 secondary（兩邊有同名的 custom event bus 與相同的規則與 target），以基於 CloudWatch alarm 的 Route 53 health check 判斷健康狀態，並啟用 event replication；producer 一次性改為以 endpoint ID 呼叫 `PutEvents`
- D. 把 EventBridge 換成 SNS FIFO topic，訂閱端改為 SQS FIFO queue，以保證事件順序與不重複

> [!answer]- 答案：C
> **A ✗** 每個 producer 都要改程式並重複送出，消費端還要去重，複雜度高。
>
> **B ✗** 主 Region 的 EventBridge 受損時，轉送規則本身也無法運作；手動修改 producer 設定違反自動切換的需求。
>
> **C ✓** Global endpoint 由 EventBridge 依 Route 53 health check 自動把事件導向健康的 Region；event replication 以受管規則把每個自訂事件同時送到兩個 Region 的 event bus；故障期間由 secondary 處理的事件，會在主 Region 恢復後也由主 Region 處理，而且 health check 恢復後事件流量能自動切回（沒有 replication 就要手動重設）。Producer 只要一次性改用 endpoint ID，之後的切換都不需要變動。兩個 Region 的規則與 target 要事先建好。
>
> **D ✗** SNS FIFO 解決的是順序與去重，仍是單一 Region 的服務，沒有處理 Region 故障。
>
> **考點**：SAP-2.4｜EventBridge global endpoint 的跨 Region 自動切換｜延伸閱讀：第 32、42 章

### 第 70 題｜SAP｜單選｜D4 以事件取代資料表輪詢

一家保險公司的保單管理服務把保單存在 DynamoDB。下游 6 個系統（帳務、CRM、資料湖、通知等）每分鐘以 Scan 輪詢整個 table 找出變更，消耗大量讀取容量，且最多延遲 1 分鐘。現代化目標是：變更近即時送達；每個下游只收到與自己相關的事件（例如狀態變為 `ISSUED`）；送達前要補上客戶等級等資訊；盡量少寫串接用的程式。

哪個方案最合適？

- A. 啟用 DynamoDB Streams，為每個下游系統各寫一個 Lambda function 讀取 stream，在程式中過濾並呼叫外部 API 補充資訊後送出
- B. 啟用 DynamoDB Streams，建立以 stream 為來源的 EventBridge Pipe，以 filter pattern 過濾事件、以 Lambda 或 API destination 做 enrichment，目標為 custom event bus；各下游以 EventBridge 規則訂閱自己需要的事件
- C. 每小時把 DynamoDB table 匯出到 S3，下游系統從 S3 讀取最新的匯出檔案並比對變更
- D. 啟用 Kinesis Data Streams for DynamoDB，各下游系統以 KCL 撰寫消費程式，自行過濾與補充資訊

> [!answer]- 答案：B
> **A ✗** 能做到近即時，但 6 個 Lambda 各自重複寫過濾與補充邏輯；而且 DynamoDB Streams 每個 shard 建議的同時讀取者數量有限，6 個獨立消費者會遇到限流。
>
> **B ✓** EventBridge Pipes 把「來源 → 過濾 → 補充 → 目標」做成受管的點對點整合，只寫補充資訊的那段邏輯。事件進入 event bus 後，各下游以規則選擇自己要的事件，新增下游也不必改動來源端。
>
> **C ✗** 每小時匯出無法滿足近即時，下游還要自己比對差異。
>
> **D ✗** Kinesis 可以支援更多消費者，但每個下游都要自行撰寫與維運 KCL 程式，串接程式最多。
>
> **考點**：SAP-4.4｜DynamoDB Streams + EventBridge Pipes 改造輪詢整合｜延伸閱讀：第 32、46 章

### 第 71 題｜SAP｜單選｜D3 內部 TLS 憑證的集中管理

一家銀行的 20 個帳號中有約 200 個內部微服務，在 internal ALB 與 NLB 的 TLS listener 上使用手動安裝的自簽憑證。去年因為憑證過期發生兩次服務中斷。資安要求：建立內部信任的 CA 階層；ALB 與 NLB 上的憑證要自動更新；CA 由資安帳號集中管理並分享給各應用帳號使用；營運負擔要最低。

哪個方案最合適？

- A. 以 ACM 為內部服務名稱申請公開憑證，以 DNS 驗證後部署到各 ALB 與 NLB
- B. 在 EC2 上以 OpenSSL 自建 CA，以 cron 腳本定期簽發新憑證並以 API 更新各 listener
- C. 把現有的自簽憑證匯入 ACM，讓 ACM 集中管理並在到期前發出提醒
- D. 在資安帳號建立 AWS Private CA 的 root 與 subordinate CA，以 AWS RAM 把 subordinate CA 分享給各應用帳號；各團隊透過 ACM 從共享的 CA 申請私有憑證並掛到 ALB 與 NLB，由 ACM 自動更新；把 root CA 憑證發布到各用戶端的信任清單

> [!answer]- 答案：D
> **A ✗** 公開憑證必須通過網域驗證，純內部名稱無法取得；公開憑證也會記錄到公開的 Certificate Transparency log，暴露內部服務名稱。
>
> **B ✗** 自建 CA 要自己保護私鑰、維護高可用與撰寫更新腳本，營運負擔最高。
>
> **C ✗** 匯入 ACM 的憑證不會被自動更新，ACM 只會提醒到期，仍需人工處理。
>
> **D ✓** AWS Private CA 提供受管的私有 CA 階層，可透過 RAM 跨帳號分享；由 ACM 簽發並綁定在 ALB、NLB 等整合服務上的私有憑證會由 ACM 自動更新。用戶端只要信任 root CA 即可。
>
> **考點**：SAP-3.2｜AWS Private CA 跨帳號分享與 ACM 自動更新｜延伸閱讀：第 15 章

### 第 72 題｜SAP｜單選｜D2 轉檔叢集的運算成本

一家影音公司在 ECS on EC2 上執行轉檔與縮圖 worker，目前全部是 x86 On-Demand 的 c5 instance：全年基準約 40 台，每季新節目上架時會衝到 300 台。工作由 SQS 驅動，可以容忍中斷重做；FFmpeg 已有 arm64 版本。公司希望在維持基準容量穩定的前提下，最大幅度降低運算成本。

哪個做法最合適？

- A. 建立 multi-arch container image；設定兩個 ECS capacity provider：一個是 Graviton（例如 c7g）On-Demand 的 Auto Scaling group，以 capacity provider strategy 的 base 承接 40 台基準；另一個是包含多種 Graviton instance type、使用 price-capacity-optimized 配置的 Spot Auto Scaling group，以 weight 承接尖峰；基準用量再以 Compute Savings Plans 承諾
- B. 全部改用 Graviton On-Demand instance，並以 300 台的尖峰用量購買 3 年期 Reserved Instance
- C. 把所有 worker 改為 Fargate On-Demand（x86），由 ECS service auto scaling 依 SQS 佇列長度擴縮
- D. 基準與尖峰全部改用單一 instance type 的 Spot instance，以取得最低單價

> [!answer]- 答案：A
> **A ✓** 三層省錢手段各司其職：Graviton 的性價比通常優於同級 x86；穩定基準用 On-Demand 加 Savings Plans，確保不受中斷影響；可中斷的尖峰用多 instance type 的 Spot，以 capacity provider strategy 的 base 與 weight 分配。Multi-arch image 讓同一個 task definition 能在 arm64 上執行。
>
> **B ✗** 以尖峰 300 台購買 RI，非尖峰期間會浪費大量承諾容量。
>
> **C ✗** Fargate 免去節點管理，但對穩定且大量的運算，單價通常高於 EC2 加 Savings Plans 與 Spot。
>
> **D ✗** 基準容量也放在 Spot 會讓服務隨時可能失去容量；只用單一 instance type 更容易遇到容量不足與集中中斷。
>
> **考點**：SAP-2.6｜Graviton、Spot、capacity provider 與 Savings Plans 的組合｜延伸閱讀：第 21、39 章

### 第 73 題｜SAP｜單選｜D4 雜誌 CMS 的水平擴展

一家雜誌出版社的 PHP CMS 跑在單一 EC2 instance 上，3 TB 的上傳圖片存在本機 EBS，MySQL 也在同一台機器。編輯集中在台北，讀者遍布全球；文章爆紅時流量會在幾分鐘內暴增 20 倍，網站常常因此當機。CMS 已有官方的 S3 儲存外掛。公司希望能水平擴展、改善全球讀者的速度，並盡量少改應用程式。

哪個方案最合適？

- A. 把 instance 升級到最大規格，並把 EBS 改為 io2 以提高磁碟效能
- B. 建立 Auto Scaling group，把上傳圖片搬到 EFS 讓所有 instance 共用，MySQL 保留在其中一台 instance 上
- C. 以 S3 外掛把圖片搬到 S3，透過 CloudFront（以 OAC 存取 S3）提供圖片並快取頁面；MySQL 遷移到 RDS Multi-AZ，session 外部化到 ElastiCache；應用層改為 ALB 後面跨多個 AZ 的 Auto Scaling group
- D. 把整台 instance 複製到 3 個 Region，以 Route 53 latency routing 讓讀者連到最近的 Region

> [!answer]- 答案：C
> **A ✗** 垂直擴展有上限，仍是單點，20 倍的突發流量依然可能壓垮。
>
> **B ✗** EFS 解決了檔案共用，但 MySQL 仍在單一 instance 上，是單點也是瓶頸；沒有 CDN，全球讀者的延遲沒有改善。
>
> **C ✓** 讓應用層變成無狀態：圖片放 S3、資料庫放 RDS、session 放 ElastiCache 後，Auto Scaling 可以隨時增減 instance；CloudFront 吸收大部分讀者流量並改善全球延遲。S3 外掛讓程式改動很小。
>
> **D ✗** 三個 Region 各有一份資料庫與圖片，編輯的變更要自己同步，資料一致性與維運負擔都很大。
>
> **考點**：SAP-4.3｜把有狀態的單機應用改為無狀態、可水平擴展｜延伸閱讀：第 11、46 章

### 第 74 題｜SAP｜單選｜D3 開發測試環境的閒置成本

一家生活用品零售商有 18 個開發測試帳號，共約 250 台 EC2 與 40 個 RDS instance，全部 24 小時運作，但實際上只在平日 08:00–20:00 使用。部分環境在週末發版時需要依申請開機。財務希望降低成本，平台團隊希望以 tag 控制排程與例外，不想寫大量自訂程式。

哪個做法最合適？

- A. 為開發測試環境購買 1 年期 Reserved Instance，以折扣降低 24 小時運作的成本
- B. 部署 Instance Scheduler on AWS（hub 帳號跨帳號管理），以 tag（例如 `Schedule=office-hours`）指定排程，需要例外時由團隊修改 tag；RDS 在停止 7 天後會自動啟動，由排程器在下一個排程時間再次停止
- C. 把所有開發測試 EC2 改為 Spot instance，RDS 改為 Aurora Serverless v2 以自動縮減容量
- D. 每晚以 CloudFormation 刪除所有開發測試環境，每天早上再重新部署，包含資料庫在內

> [!answer]- 答案：B
> **A ✗** 平日 12 小時、週末不用，實際使用時間約為全週的三分之一；排程關機省下的比例遠高於 RI 折扣，而且 RI 是為 24 小時運作付費。
>
> **B ✓** Instance Scheduler 是 AWS 提供的解決方案，依 tag 自動啟停 EC2 與 RDS，支援跨帳號與多 Region；例外只要改 tag，不必寫程式。需注意 RDS 停止最多 7 天就會自動啟動，排程器會在排程時間再次停止它。
>
> **C ✗** Spot 會被中斷，開發人員工作時可能突然失去環境；RDS 沒有 Spot，改成 Aurora 是另一個遷移專案。
>
> **D ✗** 每天重建包含資料庫的環境會遺失測試資料，部署時間與失敗風險也高；這只適合完全無狀態、資料可重建的短期環境。
>
> **考點**：SAP-3.5｜以 tag 驅動的排程啟停降低非正式環境成本｜延伸閱讀：第 38、39 章

### 第 75 題｜SAP｜單選｜D4 自管 Elasticsearch 的現代化

一家信用卡公司在 30 台 EC2 上自管 Elasticsearch 7.10 叢集，用於交易日誌搜尋，總量 150 TB、保存 1 年。最近 14 天的資料查詢量很大；更舊的資料只在調查案件時偶爾查詢，可接受較慢的回應。維運團隊花大量時間在修補、擴展與 snapshot 管理上。公司要改用受管服務、降低舊資料的儲存成本，並保留現有的儀表板與查詢 API。

哪個方案最合適？

- A. 把交易日誌改存到 DynamoDB，以 partition key 與 sort key 設計查詢模式，舊資料以 TTL 刪除
- B. 遷移到 Amazon OpenSearch Service，所有 150 TB 資料都放在 hot 資料節點的 gp3 EBS 上，以確保所有查詢都很快
- C. 把所有日誌匯出到 S3，以 Athena 取代 Elasticsearch 查詢，並以 QuickSight 重建儀表板
- D. 以 snapshot 把資料還原到 Amazon OpenSearch Service domain；最近 14 天的 index 放在 hot 節點，以 Index State Management policy 自動把較舊的 index 移到 UltraWarm，再移到 cold storage；domain 配置 dedicated master node，以 OpenSearch Dashboards 承接現有儀表板

> [!answer]- 答案：D
> **A ✗** DynamoDB 不提供全文搜尋與彈性的聚合查詢，會破壞現有的查詢與儀表板。
>
> **B ✗** 受管化解決了維運問題，但把很少查詢的舊資料都放在 hot 節點上，儲存成本最高。
>
> **C ✗** Athena 的 SQL 與搜尋 API 完全不同，儀表板也要重建，違反保留查詢 API 的要求；互動式全文搜尋的體驗也較差。
>
> **D ✓** OpenSearch Service 相容 Elasticsearch 7.10 的 API，可從 snapshot 還原。UltraWarm 以 S3 為後端儲存唯讀的 index，cold storage 更便宜，適合偶爾查詢的舊資料；ISM policy 依 index 年齡自動移轉，不需人工操作。UltraWarm 要求 domain 配置 dedicated master node。
>
> **考點**：SAP-4.4｜OpenSearch Service 的 hot、UltraWarm 與 cold 分層｜延伸閱讀：第 29 章

## 答案速查與 Domain 分析

| 題號 | 答案 | Domain | Task | 相關章節 |
|---|---|---|---|---|
| 1 | B | D1 | SAP-1.4 | 第 13、40 章 |
| 2 | D | D2 | SAP-2.1 | 第 19、37 章 |
| 3 | C | D4 | SAP-4.1 | 第 44 章 |
| 4 | A、D | D3 | SAP-3.1 | 第 38、40 章 |
| 5 | A | D1 | SAP-1.1 | 第 7、41 章 |
| 6 | C | D2 | SAP-2.2 | 第 26、34 章 |
| 7 | B | D3 | SAP-3.3 | 第 26 章 |
| 8 | A | D2 | SAP-2.3 | 第 15 章 |
| 9 | D | D1 | SAP-1.2 | 第 14、16 章 |
| 10 | B、E | D4 | SAP-4.2 | 第 45 章 |
| 11 | C | D3 | SAP-3.4 | 第 18、26 章 |
| 12 | A、C | D2 | SAP-2.4 | 第 26、32 章 |
| 13 | B、D、F | D1 | SAP-1.3 | 第 31 章 |
| 14 | B | D2 | SAP-2.5 | 第 17、24 章 |
| 15 | A | D3 | SAP-3.2 | 第 13 章 |
| 16 | D | D1 | SAP-1.5 | 第 39、43 章 |
| 17 | B | D4 | SAP-4.3 | 第 25 章 |
| 18 | C | D2 | SAP-2.6 | 第 39 章 |
| 19 | A | D1 | SAP-1.1 | 第 41 章 |
| 20 | A、C、E | D3 | SAP-3.5 | 第 23 章 |
| 21 | D | D2 | SAP-2.2 | 第 26、42 章 |
| 22 | C、D | D1 | SAP-1.4 | 第 14、40 章 |
| 23 | B | D4 | SAP-4.1 | 第 44 章 |
| 24 | C | D3 | SAP-3.3 | 第 11 章 |
| 25 | A | D2 | SAP-2.3 | 第 15 章 |
| 26 | B | D1 | SAP-1.2 | 第 16 章 |
| 27 | D | D2 | SAP-2.4 | 第 26 章 |
| 28 | C | D3 | SAP-3.1 | 第 37 章 |
| 29 | A | D1 | SAP-1.3 | 第 11、34 章 |
| 30 | B | D4 | SAP-4.2 | 第 25、45 章 |
| 31 | D | D2 | SAP-2.1 | 第 37、40 章 |
| 32 | C | D3 | SAP-3.2 | 第 15、19 章 |
| 33 | A | D1 | SAP-1.4 | 第 14 章 |
| 34 | D | D2 | SAP-2.5 | 第 22、23 章 |
| 35 | B | D3 | SAP-3.4 | 第 32 章 |
| 36 | B、E | D1 | SAP-1.1 | 第 6、8 章 |
| 37 | C | D4 | SAP-4.3 | 第 33 章 |
| 38 | A、D | D2 | SAP-2.2 | 第 34、43 章 |
| 39 | B、C | D1 | SAP-1.5 | 第 39、43 章 |
| 40 | A | D3 | SAP-3.3 | 第 19 章 |
| 41 | B | D2 | SAP-2.3 | 第 13、22 章 |
| 42 | D | D1 | SAP-1.3 | 第 9 章 |
| 43 | C | D4 | SAP-4.4 | 第 10、46 章 |
| 44 | A | D2 | SAP-2.6 | 第 30、31 章 |
| 45 | B | D3 | SAP-3.1 | 第 36 章 |
| 46 | C | D1 | SAP-1.2 | 第 16 章 |
| 47 | D | D2 | SAP-2.1 | 第 37 章 |
| 48 | C、E | D3 | SAP-3.4 | 第 21 章 |
| 49 | A | D1 | SAP-1.4 | 第 14、40 章 |
| 50 | C | D4 | SAP-4.2 | 第 45 章 |
| 51 | B | D2 | SAP-2.4 | 第 17、32 章 |
| 52 | D | D3 | SAP-3.2 | 第 21 章 |
| 53 | A | D1 | SAP-1.1 | 第 7 章 |
| 54 | C | D2 | SAP-2.2 | 第 24、34 章 |
| 55 | B | D3 | SAP-3.5 | 第 39 章 |
| 56 | D | D1 | SAP-1.3 | 第 31 章 |
| 57 | D、E | D4 | SAP-4.1 | 第 44 章 |
| 58 | A、C | D2 | SAP-2.3 | 第 38 章 |
| 59 | A | D1 | SAP-1.5 | 第 39 章 |
| 60 | C | D3 | SAP-3.3 | 第 30 章 |
| 61 | D | D4 | SAP-4.3 | 第 13、24 章 |
| 62 | B | D2 | SAP-2.5 | 第 27、28 章 |
| 63 | A | D1 | SAP-1.2 | 第 16、41 章 |
| 64 | C | D3 | SAP-3.1 | 第 36 章 |
| 65 | B、D | D2 | SAP-2.1 | 第 37 章 |
| 66 | B | D1 | SAP-1.4 | 第 40 章 |
| 67 | D | D4 | SAP-4.2 | 第 26、45 章 |
| 68 | A | D3 | SAP-3.4 | 第 31 章 |
| 69 | C | D2 | SAP-2.4 | 第 32、42 章 |
| 70 | B | D4 | SAP-4.4 | 第 32、46 章 |
| 71 | D | D3 | SAP-3.2 | 第 15 章 |
| 72 | A | D2 | SAP-2.6 | 第 21、39 章 |
| 73 | C | D4 | SAP-4.3 | 第 11、46 章 |
| 74 | B | D3 | SAP-3.5 | 第 38、39 章 |
| 75 | D | D4 | SAP-4.4 | 第 29 章 |

### 各 domain 題數與 task 分布

| Domain | 題數 | 涵蓋 task（題數） |
|---|---|---|
| D1 Design Solutions for Organizational Complexity | 20 | 1.1（4）、1.2（4）、1.3（4）、1.4（5）、1.5（3） |
| D2 Design for New Solutions | 22 | 2.1（4）、2.2（4）、2.3（4）、2.4（4）、2.5（3）、2.6（3） |
| D3 Continuous Improvement for Existing Solutions | 19 | 3.1（4）、3.2（4）、3.3（4）、3.4（4）、3.5（3） |
| D4 Accelerate Workload Migration and Modernization | 14 | 4.1（3）、4.2（4）、4.3（4）、4.4（3） |

題型：單選 62 題、選兩項 11 題、選三項 2 題。單選答案分布：A 15、B 16、C 16、D 15。

### 錯題對應複習章節

先計算每個 domain 的答對率，答對率低於 75% 的 domain 優先複習；同一個 task 錯兩題以上，代表觀念有缺口，要回到章節重讀而不是只看解析。

| Domain | 錯題集中時優先複習 | 複習重點 |
|---|---|---|
| D1 | 第 7、8、14、16、40、41 章，其次第 9、31、39、43 章 | 多帳號治理的政策類型（SCP、declarative policy、tag policy、delegation policy、Control Tower 三種 control）、Identity Center 的 identity source 限制、Transit Gateway Connect／Cloud WAN／VPC Lattice 的選型、私有端點的 health check、成本分攤工具的分工 |
| D2 | 第 26、34、37 章，其次第 15、17、32、39 章 | DR 策略與 Aurora Global Database 的 switchover／failover、不可變備份、CodeDeploy／StackSets／AppConfig 的部署語意、KMS 的三種金鑰保存方式、削峰與連線池、Savings Plans 的適用範圍 |
| D3 | 第 21、36、38、39 章，其次第 15、19、26、31 章 | Config 自動修正與 composite alarm、pod 與地端工作負載的臨時憑證、快取鍵與 SnapStart 等效能調校、FIFO DLQ 與 Kinesis 熱分區、rightsizing 與 S3 lifecycle 的順序與組合 |
| D4 | 第 44、45、46 章，其次第 25、33 章 | 7Rs 與第一波的選擇、遷移評估資料來源、DMS 異質遷移與同質實體備份遷移、DataSync 頻寬估算、strangler fig 與事件驅動的現代化 |

> [!tip] 考試提示
> 複習錯題時，把每題的限制條件逐條列出，標記哪個選項違反了哪一條。SAP 的錯誤選項多半「技術上可行」，只是違反了題幹中的某一個限制（不能重建、不能經過 Internet、不能有人工步驟、成本最低）。練習在讀選項前先寫下限制清單，是提高 SAP 答對率最有效的方法。
