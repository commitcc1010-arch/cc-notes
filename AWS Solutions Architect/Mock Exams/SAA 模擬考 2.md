---
title: SAA 模擬考 2
exam: SAA-C03
---

# SAA 模擬考 2

> [!abstract] 作答說明
> **題數**：65 題（單選 54 題、選兩項 11 題），涵蓋 SAA-C03 四個 domain 的全部 14 個 task。題目依 domain 混合排列，和真實考試一樣。
> **建議時間**：130 分鐘。請一次坐完、全程計時，練習真實考試的專注力與時間分配；平均每題 2 分鐘，遇到卡住的題目先標記、跳過，最後再回來。
> **及格參考**：真實考試以 100–1000 分計分、720 分及格，且含未計分題。本回模擬考可用「答對 47 題（約 72%）」作為及格參考線，答對 52 題以上代表準備相當穩定。
> **作答方式**：先在紙上或筆記中寫下每題的答案，**全部作答完畢後**再逐題展開「答案」區塊核對；選兩項的題目必須兩個都選對才算得分。
> **情境產業**：本回以金融科技、線上遊戲、教育與新創 SaaS 為主，題目中的公司都是虛構的。
> **錯題記錄**：每答錯一題，記下題號、選錯的選項、以及「我當時以為的理由」。考點行的 task ID 與延伸閱讀章節告訴你該回去複習哪裡；文末的 domain 分析表可以幫你找出最弱的領域。

## 題目

### 第 1 題｜SAA｜單選｜D1 多帳號員工單一登入

新創 SaaS 公司「表單雲」在 AWS Organizations 底下有 12 個 AWS 帳號，員工身份統一放在 Okta。目前每個帳號都為工程師建立了 IAM user 與 access key，離職時常常漏掉某些帳號沒有撤銷。資安主管要求：員工用公司帳號單一登入所有 AWS 帳號、只使用臨時憑證、權限由中央統一指派，而且營運負擔要最小。

哪個方案最符合需求？

- A. 在 12 個帳號各自建立 SAML identity provider 與對應的 IAM role，讓 Okta 直接 federate 到每個帳號的 role
- B. 在 management account 啟用 IAM Identity Center，以 Okta 作為外部 IdP 並用 SCIM 自動同步使用者與群組，透過 permission set 指派各帳號權限
- C. 只在 management account 保留 IAM user 並強制 MFA，員工登入後再 assume role 到各成員帳號
- D. 部署 AWS Managed Microsoft AD 並與 Okta 建立 forest trust，再把 AD 群組對應到各帳號的 IAM role

> [!answer]- 答案：B
> **A ✗** 每個帳號各自設定 SAML federation 技術上可行，也是臨時憑證，但 12 個帳號要分別維護 IdP metadata、role 與信任關係，新增帳號或調整權限都要逐一修改，不符合「中央統一、營運負擔最小」。帳號只有一兩個、又沒有 Organizations 時，這種做法才比較合理。
>
> **B ✓** IAM Identity Center 是多帳號員工登入的標準做法：Okta 作為外部 IdP 負責驗證，SCIM 自動同步使用者與群組，離職者在 Okta 停用後就無法再登入任何帳號。Permission set 在中央定義一次，Identity Center 會在各帳號自動建立對應的 role，員工拿到的都是臨時憑證。
>
> **C ✗** 仍然保留了 IAM user（長期密碼，若再發 access key 就是長期金鑰），離職撤權仍要另外處理，也沒有和 Okta 整合，違反「使用公司帳號單一登入」。
>
> **D ✗** Okta 不是 Active Directory forest，無法與 Managed Microsoft AD 建立 forest trust；就算改用其他同步方式，也多了一整套目錄服務要維運。公司身份來源本身就是地端 AD 時，才會考慮 AD Connector 或 Managed AD。
>
> **考點**：SAA-1.1｜多帳號員工存取用 IAM Identity Center + 外部 IdP + permission set｜延伸閱讀：第 13 章

### 第 2 題｜SAA｜單選｜D3 固定 IP 的全球 API 入口

跨境支付公司「沛金支付」的支付 API 部署在 ap-northeast-1 與 eu-west-1，兩個 Region 各有一組 Application Load Balancer。許多企業客戶的防火牆只允許連到事先登記的固定 IP，客戶分布在全球各地，抱怨 TCP 與 TLS 握手延遲偏高。公司要求客戶永遠連到同一組固定 IP、改善跨洲延遲，並在某個 Region 故障時自動導向另一個 Region，客戶不需要改任何防火牆設定。

哪個方案最符合需求？

- A. 使用 Route 53 latency-based routing 指向兩個 ALB，並把兩個 ALB 目前解析出的 IP 位址提供給客戶登記
- B. 把兩個 Region 的 ALB 換成 NLB 並各自綁定 Elastic IP，請客戶登記這些 EIP，再用 Route 53 failover routing 切換
- C. 建立 AWS Global Accelerator，以兩個 Region 的 ALB 作為 endpoint group，請客戶登記 accelerator 提供的兩個固定 anycast IP
- D. 建立 CloudFront distribution，以兩個 ALB 組成 origin group 做 origin failover，並請客戶登記 CloudFront 的 IP 範圍

> [!answer]- 答案：C
> **A ✗** ALB 的 IP 位址會隨擴展與維護而改變，AWS 不保證固定，把當下解析到的 IP 給客戶登記，之後一定會斷線。Latency routing 本身也不能縮短 TCP 握手的路徑。
>
> **B ✗** NLB 的 EIP 確實固定，但客戶要登記多個 IP，切換依賴 DNS，會受客戶端 DNS 快取影響；流量也仍然走公用 Internet 到 Region，沒有改善跨洲握手延遲。只需要「單一 Region 固定 IP」時，NLB + EIP 才是合理選擇。
>
> **C ✓** Global Accelerator 提供兩個固定的 anycast IP，客戶從最近的 AWS edge location 進入 AWS 骨幹網路，TCP 連線在邊緣終止，改善跨洲延遲。Endpoint group 會做健康檢查，某個 Region 不健康時，流量在同一組 IP 下自動導到另一個 Region，不依賴 DNS 快取。
>
> **D ✗** CloudFront 預設使用的 IP 範圍很大且會變動，不適合讓客戶寫進防火牆的允許清單（另行申請的 Anycast static IP 是特殊用途的進階功能，也不是這題的重點）。關鍵在於 origin failover 只對 GET、HEAD、OPTIONS 請求生效，支付 API 的 POST 請求不會自動切換到另一個 Region；CloudFront 也是為 HTTP 內容快取設計，對每筆都不同的 API 交易沒有快取效益。
>
> **考點**：SAA-3.4｜固定 IP + 非 HTTP 快取需求 + 多 Region 容錯 → Global Accelerator｜延伸閱讀：第 11 章

### 第 3 題｜SAA｜單選｜D2 每個帳戶依序處理交易

數位錢包「速匯」把每筆入帳與扣款事件送進 SQS standard queue，由 Lambda 處理並更新帳戶餘額。最近發現同一個帳戶的事件偶爾會亂序或重複處理，導致餘額計算錯誤。業務要求：同一個帳戶的事件必須嚴格依序且不重複處理，不同帳戶之間可以平行處理；尖峰約每秒 800 筆事件。

哪個設計最合適？

- A. 改用 SQS FIFO queue，以帳戶 ID 作為 MessageGroupId 並提供 deduplication ID，必要時啟用 high throughput 模式，由 Lambda 消費
- B. 改用 SQS FIFO queue，所有訊息使用同一個 MessageGroupId，確保全域依序處理，由 Lambda 消費
- C. 保留 SQS standard queue，把 Lambda 的 reserved concurrency 設為 1，讓事件一次只處理一筆
- D. 改用 SNS standard topic，依帳戶 ID 把事件 fan-out 到不同的 SQS standard queue 各自處理

> [!answer]- 答案：A
> **A ✓** FIFO queue 保證「同一個 message group 內」依序交付，並在 5 分鐘的去重區間內排除重複訊息。以帳戶 ID 當 MessageGroupId，同一帳戶依序處理、不同帳戶可由多個 Lambda 執行環境平行處理，正好符合需求；每秒 800 筆可以用批次或 high throughput 模式承接。
>
> **B ✗** 所有訊息同一個 group 時，整個 queue 只能一筆接一筆處理，完全失去平行度，也會成為吞吐量瓶頸。只有「全系統必須單一順序」時才會這樣設計。
>
> **C ✗** Standard queue 本身不保證順序，且是 at-least-once 交付，即使只有一個消費者，仍可能收到亂序或重複訊息；同時吞吐量會被壓到極低。
>
> **D ✗** SNS standard topic 不保證順序，也無法動態依帳戶建立無數個 queue；這個設計既複雜又沒有解決順序與重複問題。
>
> **考點**：SAA-2.1｜FIFO queue 的順序單位是 message group｜延伸閱讀：第 32 章

### 第 4 題｜SAA｜單選｜D1 找出散落各處的學生個資

線上教育平台「學海」多年來把學生作業、成績單與報名表匯出檔放在 40 多個 S3 bucket，格式有 CSV、JSON 與 PDF。新的個資法規要求公司找出哪些 bucket 含有身分證字號、生日、電話等個人資料，並持續監控之後新上傳的檔案，發現時通知資安團隊。公司希望盡量不自行開發掃描程式。

哪個方案最符合需求？

- A. 用 AWS Glue crawler 為所有 bucket 建立 table，再以 Amazon Athena 執行含正規表示式的 SQL 定期掃描個資欄位
- B. 啟用 Amazon GuardDuty 的 S3 Protection，由它分析 bucket 內容並對含個資的物件產生 finding
- C. 啟用 S3 Storage Lens 進階指標，依各 bucket 的物件類型與存取活動找出可能含個資的 bucket
- D. 啟用 Amazon Macie 的 automated sensitive data discovery，加入身分證字號格式的 custom data identifier，並把 finding 送到 EventBridge 通知資安團隊

> [!answer]- 答案：D
> **D ✓** Macie 是專門用來在 S3 中探索與分類敏感資料的受管服務，內建大量 managed data identifier，也能用正規表示式定義 custom data identifier（例如台灣身分證字號格式）。Automated discovery 會持續抽樣評估 bucket，finding 可送到 EventBridge 或 Security Hub 觸發通知，幾乎不用寫程式。
>
> **A ✗** Athena 只能查詢有 schema 的結構化或半結構化資料，PDF 無法直接查；每種格式都要自行寫 regex 與排程，等於自己開發掃描系統。若只是分析一個已知格式的資料集，Athena 才合適。
>
> **B ✗** GuardDuty S3 Protection 分析的是 CloudTrail 的 S3 data events，偵測可疑的存取行為（例如異常地點大量下載），並不檢查物件內容是否含個資。
>
> **C ✗** Storage Lens 提供容量、請求數、成本最佳化等用量指標，不讀取物件內容，無法判斷檔案裡有沒有個資。
>
> **考點**：SAA-1.3｜S3 敏感資料探索與分類用 Macie｜延伸閱讀：第 16 章

### 第 5 題｜SAA｜單選｜D3 CPU 密集的 Lambda 太慢

人資 SaaS「人資通」用 Lambda 為每位員工產生薪資單 PDF，函式設定 512 MB 記憶體。CloudWatch 顯示每次執行最多只用到 180 MB 記憶體，但執行時間長達 9 秒，程式大部分時間花在壓縮與字型渲染這類 CPU 密集運算。團隊希望縮短執行時間，且不改變程式架構。

最有效的做法是什麼？

- A. 把記憶體降到 256 MB 以節省成本，並為函式設定 provisioned concurrency
- B. 把函式的記憶體設定提高到 2,048 MB 以上，讓 Lambda 分配到更多 CPU
- C. 為函式設定 provisioned concurrency，讓執行環境事先初始化完成
- D. 把函式的 ephemeral storage（/tmp）從 512 MB 提高到 10,240 MB

> [!answer]- 答案：B
> **A ✗** 降低記憶體會同時減少分配到的 CPU，執行只會更慢；provisioned concurrency 只消除冷啟動，對 9 秒的運算時間沒有幫助。
>
> **B ✓** Lambda 不能單獨設定 CPU，CPU 與網路能力依記憶體設定按比例分配（約 1,769 MB 時相當於一個完整 vCPU，最高 10,240 MB 可到 6 vCPU）。CPU 密集的函式提高記憶體後執行時間會明顯縮短，由於計費是「記憶體 × 時間」，總費用常常持平甚至下降。可用 Lambda Power Tuning 找出最划算的設定。
>
> **C ✗** Provisioned concurrency 解決的是冷啟動的初始化延遲，每次呼叫的 9 秒主要花在運算本身，預熱環境並不會讓 CPU 變快。
>
> **D ✗** /tmp 容量只影響可暫存的檔案大小，與 CPU 無關；這個函式的瓶頸不在磁碟空間。
>
> **考點**：SAA-3.2｜Lambda 的 CPU 依記憶體比例分配｜延伸閱讀：第 19 章

### 第 6 題｜SAA｜單選｜D4 大量 S3 流量經過 NAT Gateway

遊戲公司「星砂互動」的日誌分析 EC2 機群位於 private subnet，資安政策規定這些 instance 不得擁有 public IP。機群每月從同一個 Region 的 S3 讀取約 400 TB 遊戲日誌，目前流量全部經過 NAT Gateway，帳單中的 NAT Gateway 資料處理費用非常高。

哪個做法能最有效地降低成本？

- A. 建立 S3 gateway VPC endpoint，並把它加到 private subnet 的 route table
- B. 建立 S3 interface VPC endpoint，並讓應用程式改用 endpoint 專屬的 DNS 名稱
- C. 為每台 instance 配置 Elastic IP 並放到 public subnet，直接透過 Internet Gateway 存取 S3
- D. 在 bucket 上啟用 S3 Transfer Acceleration，縮短每次讀取的時間

> [!answer]- 答案：A
> **A ✓** S3 gateway endpoint 透過 route table 中的 prefix list 路由，讓流量直接在 AWS 網路內到達 S3，不經過 NAT Gateway；gateway endpoint 本身沒有小時費也沒有資料處理費。400 TB 的 NAT 處理費可以幾乎全部省下來。
>
> **B ✗** Interface endpoint 也能讓流量不經 NAT，但它按 endpoint 每小時與每 GB 處理量計費，大量流量時比免費的 gateway endpoint 貴。需要從地端（經 VPN／Direct Connect）或其他 Region 私有存取 S3 時，interface endpoint 才是正確答案。
>
> **C ✗** 給 instance public IP 違反資安政策，也增加攻擊面。
>
> **D ✗** Transfer Acceleration 是為了長距離上傳／下載經由 edge location 加速，會額外收費，對同 Region 的 EC2 讀取沒有好處，也不會讓流量避開 NAT。
>
> **考點**：SAA-4.4｜同 Region 大量 S3 流量用免費的 gateway endpoint 取代 NAT｜延伸閱讀：第 6 章

### 第 7 題｜SAA｜選兩項｜D1 三層式架構的最小網路權限

「青松大學」的學習管理系統採三層式架構：ALB 在 public subnet，應用程式 EC2 由 Auto Scaling group 管理並位於 private subnet，RDS for MySQL 在另一組 private DB subnet。稽核要求：資料庫只接受應用程式層的連線，應用程式層只接受來自 ALB 的流量；應用程式 instance 會隨擴展不斷更換 IP。

哪兩項設定能以最低營運負擔達成需求？

- A. 在應用程式層 security group 允許來自 0.0.0.0/0 的 HTTP，因為只有 ALB 能把流量送進 private subnet
- B. 在應用程式層 security group 加入 inbound rule，來源設為 ALB 的 security group ID，port 為應用程式 port
- C. 在資料庫 security group 列出每台應用程式 instance 的私有 IP，並用 Lambda 在擴展事件時自動更新規則
- D. 在資料庫 security group 加入 inbound rule，來源設為應用程式層的 security group ID，port 為 3306
- E. 在 DB subnet 的 network ACL 只允許 3306 入站，並拒絕所有其他入站與出站流量

> [!answer]- 答案：B、D
> **A ✗** 雖然 private subnet 沒有 IGW 路由，但規則允許 0.0.0.0/0 代表 VPC 內任何資源（或經 peering、VPN 連進來的流量）都能連到應用程式，不符合「只接受 ALB」的最小權限要求。
>
> **B ✓** Security group 可以引用另一個 security group 作為來源，意思是「掛著 ALB security group 的網卡」才能連入，不管 ALB 節點的 IP 怎麼變都不必改規則。
>
> **C ✗** 技術上做得到，但需要自己維護 Lambda 與事件處理，還可能碰到 security group 規則數上限；引用 security group 就能自動涵蓋新 instance，這是不必要的營運負擔。
>
> **D ✓** 同樣以應用程式層的 security group 作為來源，新啟動的 instance 只要掛上該 security group 就能連資料庫，其他資源一律被拒絕。
>
> **E ✗** NACL 是 stateless，必須另外允許資料庫回應給應用程式的 ephemeral port 出站流量；「拒絕所有出站」會讓連線完全建立不起來。
>
> **考點**：SAA-1.2｜Security group 引用 security group 實現分層最小權限｜延伸閱讀：第 6 章

### 第 8 題｜SAA｜單選｜D2 跨 Region 秒級 RPO 的交易資料庫

證券商「穩利證券」的下單與查詢系統使用 Aurora MySQL，部署在 ap-northeast-1。主管機關要求：發生 Region 層級災難時，必須在 ap-southeast-1 於數分鐘內恢復寫入，資料遺失不超過數秒。平時 ap-southeast-1 也要提供東南亞客戶低延遲的唯讀查詢。

哪個方案最符合需求？

- A. 在 ap-southeast-1 建立以 binlog 複寫的 Aurora cross-Region read replica，災難時手動 promote
- B. 每小時建立 Aurora cluster snapshot 並自動複製到 ap-southeast-1，災難時從最新 snapshot 還原
- C. 建立 Aurora Global Database，在 ap-southeast-1 加入 secondary cluster，災難時執行 failover 讓它成為新的 primary
- D. 在 ap-northeast-1 把 Aurora Replicas 分散到三個 AZ，並啟用 cluster 的自動 failover

> [!answer]- 答案：C
> **A ✗** Binlog 型的跨 Region replica 確實存在，但複寫延遲受 binlog 處理影響、可能達數秒以上，promote 也需要較長時間，難以穩定達到秒級 RPO 與分鐘級 RTO。Aurora Global Database 才是這類需求的設計目標。
>
> **B ✗** 每小時 snapshot 代表最多遺失一小時資料，從 snapshot 還原大型資料庫也要很久，RPO 與 RTO 都不符合。
>
> **C ✓** Aurora Global Database 在儲存層做跨 Region 複寫，典型延遲小於 1 秒，secondary cluster 可提供低延遲唯讀查詢；災難時可以把 secondary promote 為 primary，通常在數分鐘內恢復寫入。
>
> **D ✗** 多 AZ 的 Aurora Replicas 只保護 AZ 故障，整個 ap-northeast-1 失效時仍然無法服務，也無法提供東南亞的低延遲讀取。
>
> **考點**：SAA-2.2｜跨 Region 秒級 RPO、分鐘級 RTO → Aurora Global Database｜延伸閱讀：第 26 章

### 第 9 題｜SAA｜單選｜D3 多個團隊消費同一份遊戲事件

手機遊戲「鯨魚工作室」的客戶端每秒送出約 50,000 筆戰鬥事件，每筆約 1 KB。反作弊、即時排行榜與 data lake 三個團隊要各自獨立讀取同一份資料，反作弊與排行榜要求秒級延遲。反作弊團隊更新模型後，需要重新處理過去 3 天的事件。

哪個方案最合適？

- A. 把事件送進一個 SQS standard queue，三個團隊的程式各自從同一個 queue 輪詢讀取
- B. 把事件發布到 SNS topic，fan-out 到三個 SQS queue，每個團隊各自消費一個 queue
- C. 把事件送進 Amazon Data Firehose 寫入 S3，三個團隊都從 S3 讀取新檔案進行處理
- D. 把事件送進 Kinesis Data Streams，把 retention 延長到 7 天，各團隊以 enhanced fan-out 各自讀取

> [!answer]- 答案：D
> **D ✓** Kinesis Data Streams 讓多個 consumer 各自維護讀取位置、獨立消費同一份資料；enhanced fan-out 讓每個 consumer 各有專屬的讀取吞吐量。Retention 預設 24 小時、最長可延長到 365 天，延長到 7 天後就能從 3 天前的位置重播。
>
> **A ✗** SQS 的訊息被一個 consumer 處理並刪除後就消失，三個團隊會「搶」同一批訊息，而不是各自拿到完整資料，也無法重播。
>
> **B ✗** SNS + SQS fan-out 能讓三個團隊各拿一份，但訊息處理後即刪除，無法重新處理 3 天前的事件。不需要重播、只要可靠分發時，這是好設計。
>
> **C ✗** Firehose 會先緩衝再批次寫入 S3（緩衝時間以秒到分鐘計），達不到反作弊的秒級即時需求；它適合「近即時」寫入 data lake。
>
> **考點**：SAA-3.5｜多 consumer、可重播的串流 → Kinesis Data Streams｜延伸閱讀：第 31 章

### 第 10 題｜SAA｜單選｜D1 地端伺服器不放長期金鑰

金融科技新創在地端機房執行 Jenkins build server，需要把建置產物上傳到 S3，並從 Amazon ECR 拉取映像檔。資安政策禁止在任何伺服器上存放長期 access key。公司已經有內部 PKI，CA 會為每台伺服器簽發 X.509 憑證。團隊希望以最少的營運負擔解決。

哪個方案最符合需求？

- A. 使用 IAM Roles Anywhere，以公司 CA 建立 trust anchor 並設定 profile 與 IAM role，伺服器用自己的憑證換取臨時憑證
- B. 為每台伺服器建立 IAM user，把 access key 存在 Secrets Manager 並每 30 天自動輪替
- C. 建立 Cognito identity pool 並允許 unauthenticated identities，讓 Jenkins 以匿名身份取得臨時憑證
- D. 在 IAM Identity Center 為 Jenkins 建立專用使用者，讓 build server 以 `aws sso login` 取得臨時憑證

> [!answer]- 答案：A
> **A ✓** IAM Roles Anywhere 讓 AWS 以外的工作負載用 X.509 憑證證明身份：trust anchor 指向公司 CA，伺服器透過 credential helper 用憑證簽章換取 IAM role 的臨時憑證，伺服器上不會有長期 access key，而且可以沿用既有 PKI。
>
> **B ✗** 即使會輪替，IAM user 的 access key 仍然是長期憑證，而且還要處理伺服器如何安全取得 Secrets Manager 中的金鑰，違反政策。
>
> **C ✗** Unauthenticated identity 代表任何人都能取得這個 role 的權限，是嚴重的安全漏洞；identity pool 是給終端使用者 App 用的，不是伺服器身份。
>
> **D ✗** `aws sso login` 需要人在瀏覽器完成互動式登入，session 到期後要重新登入，適合人類使用者，不適合無人值守的 build server。
>
> **考點**：SAA-1.1｜AWS 外部工作負載以 X.509 憑證取得臨時憑證 → IAM Roles Anywhere｜延伸閱讀：第 13 章

### 第 11 題｜SAA｜單選｜D4 可中斷的夜間算圖工作

遊戲美術團隊每晚要 render 數千張場景畫面，每張畫面彼此獨立，中斷後可以重新計算，只要在隔天早上 8 點前全部完成即可。目前使用 On-Demand 的運算最佳化 instance，每晚約執行 8 小時，白天完全不用。團隊希望把運算成本降到最低。

哪個方案最符合需求？

- A. 購買 3 年期 Standard Reserved Instances，數量等於夜間尖峰所需的 instance 數
- B. 用 AWS Batch 搭配 Spot 的 compute environment，允許多種 instance type 與多個 AZ，並使用 capacity-optimized 配置策略
- C. 改用 Dedicated Hosts，以取得固定的硬體容量確保早上前完成
- D. 購買 Compute Savings Plans，承諾金額等於夜間尖峰每小時的 On-Demand 花費

> [!answer]- 答案：B
> **B ✓** 工作可中斷、可重算、有寬鬆期限，是 Spot 的典型使用情境，相較 On-Demand 最高可省約 90%。允許多種 instance type 與多個 AZ 能擴大可用的 Spot 容量池，capacity-optimized 策略會挑選中斷機率較低的池；AWS Batch 會自動排程並重試被中斷的工作。
>
> **A ✗** Reserved Instances 按小時全天計費，每天只用 8 小時等於浪費三分之二，總成本不一定比 On-Demand 低，更遠高於 Spot。
>
> **C ✗** Dedicated Hosts 用於授權綁定實體核心或合規需求，價格比 On-Demand 更高。
>
> **D ✗** Savings Plans 的承諾是「每小時」，白天沒用的時段仍要付承諾金額；它適合 24 小時穩定的基礎負載，不適合每天只跑 8 小時的批次工作。
>
> **考點**：SAA-4.2｜可中斷、有彈性期限的批次工作用 Spot｜延伸閱讀：第 39 章

### 第 12 題｜SAA｜單選｜D2 含人工審核的開戶流程

數位銀行的線上開戶流程包含：上傳證件、自動 OCR 與資料比對、若比對信心分數偏低則轉人工審核（最長可能需要 2 天）、建立帳戶、寄送通知。產品團隊要求能清楚看到每一筆申請目前在哪個步驟、失敗步驟可以自動重試，並且盡量少寫協調流程的程式。

哪個方案最符合需求？

- A. 每個步驟寫成一個 Lambda，前一個 Lambda 以同步方式呼叫下一個，人工審核時由 Lambda 每分鐘輪詢資料庫的審核狀態
- B. 每個步驟之間放一個 SQS queue，由排程的 Lambda 定期檢查資料庫，判斷人工審核是否完成再送到下一個 queue
- C. 使用 Step Functions Express Workflow 串接各步驟，人工審核時以 Wait state 等待審核結果寫回
- D. 使用 Step Functions Standard Workflow 串接各步驟，人工審核步驟使用 `.waitForTaskToken` callback 模式，並為各步驟設定 Retry

> [!answer]- 答案：D
> **D ✓** Standard Workflow 單次執行最長可達 1 年，console 可以看到每一筆執行目前所在的步驟與歷史。`.waitForTaskToken` 讓流程暫停，直到審核系統用 task token 呼叫 SendTaskSuccess／SendTaskFailure 才繼續，等待期間不消耗運算；每個 Task 可以宣告式設定 Retry 與 Catch。
>
> **A ✗** Lambda 最長只能執行 15 分鐘，無法同步等待 2 天的人工審核；串接呼叫也讓錯誤處理與狀態追蹤全都要自己寫。
>
> **B ✗** 可以運作，但流程狀態散落在資料庫與多個 queue，需要自己寫協調、重試與狀態查詢邏輯，違反「少寫協調程式」。
>
> **C ✗** Express Workflow 單次執行最長 5 分鐘，適合高頻、短時間的流程，無法等待 2 天。
>
> **考點**：SAA-2.1｜長時間、含人工步驟的流程用 Step Functions Standard 與 callback｜延伸閱讀：第 33 章

### 第 13 題｜SAA｜單選｜D1 持續的軟體漏洞掃描

支付處理新創正準備 PCI DSS 稽核，需要持續找出 EC2 instance、Amazon ECR 中的 container image 與 Lambda 函式所使用套件的已知軟體漏洞（CVE），新的 CVE 公布時要自動重新評估受影響的資源，結果要能集中檢視。團隊希望使用受管服務。

哪個方案最符合需求？

- A. 啟用 Amazon GuardDuty 的 Runtime Monitoring，偵測 EC2 與 container 上的漏洞並產生 finding
- B. 部署 AWS Config managed rules，評估 EC2、ECR 與 Lambda 的設定是否存在已知 CVE
- C. 啟用 Amazon Inspector 的 EC2、ECR 與 Lambda 掃描，並把 finding 彙整到 AWS Security Hub
- D. 定期執行 AWS Trusted Advisor 的安全性檢查，並把結果匯出成報表給稽核人員

> [!answer]- 答案：C
> **C ✓** Amazon Inspector 專門做軟體漏洞與非預期網路暴露的評估，支援 EC2、ECR container image 與 Lambda。它是持續掃描的：新 CVE 加入資料庫或資源變更時會自動重新評估，finding 可以集中到 Security Hub。
>
> **A ✗** GuardDuty Runtime Monitoring 偵測的是執行期間的威脅行為（例如可疑程序、連到惡意網域），不是盤點套件中的 CVE。
>
> **B ✗** AWS Config 評估資源「設定」是否合規（例如是否加密、是否公開），不分析作業系統或套件的漏洞。
>
> **D ✗** Trusted Advisor 檢查的是帳號層級的最佳實務（例如 root MFA、公開的 security group），不會掃描 CVE。
>
> **考點**：SAA-1.2｜EC2／ECR／Lambda 的漏洞掃描用 Amazon Inspector｜延伸閱讀：第 16 章

### 第 14 題｜SAA｜單選｜D3 考試季的讀取尖峰

線上測驗平台在期中考季時流量暴增，其中約 90% 是讀取（載入題目、查詢成績），資料庫是 Aurora MySQL，只有一個 writer instance，尖峰時 CPU 使用率超過 90%。團隊希望提升讀取效能、能隨考試季自動調整，並盡量少改應用程式。

哪個方案最合適？

- A. 新增 Aurora Replicas 並設定 Aurora Auto Scaling，讓應用程式的唯讀查詢改連 cluster 的 reader endpoint
- B. 把 writer instance 升級到最大的 instance class，所有讀寫查詢仍連 cluster endpoint
- C. 把資料庫改成 RDS for MySQL 的 Multi-AZ DB instance 部署，讓唯讀查詢改連 standby instance
- D. 把題目與成績資料遷移到 DynamoDB，並以 on-demand 模式應付考試季的尖峰

> [!answer]- 答案：A
> **A ✓** Aurora Replicas 共用同一個儲存層，最多 15 個，複寫延遲通常在毫秒等級。Reader endpoint 會在所有 replica 之間分配連線，應用程式只要把唯讀查詢的連線字串改成 reader endpoint；Aurora Auto Scaling 可以依 CPU 或連線數自動增減 replica，考試季後自動縮回。
>
> **B ✗** 垂直擴展有上限，而且平時也要付最大規格的費用，無法隨季節彈性調整；讀取占 90% 的工作負載用水平擴展的 replica 更有效率。
>
> **C ✗** RDS Multi-AZ DB instance 部署的 standby 只用來 failover，不能處理讀取流量。若改用 Multi-AZ DB cluster，雖有兩個可讀 standby，但仍是更換引擎與架構，不如直接加 Aurora Replicas。
>
> **D ✗** 從關聯式資料庫遷移到 DynamoDB 需要重新設計資料模型與改寫查詢，違反「少改應用程式」。
>
> **考點**：SAA-3.3｜讀取密集 → Aurora Replicas + reader endpoint + Auto Scaling｜延伸閱讀：第 26 章

### 第 15 題｜SAA｜選兩項｜D2 AZ 故障時不必等待擴展

線上遊戲的大廳 API 目前跑在單一 AZ 的 6 台 EC2 上，由 Auto Scaling group 管理，前面有 ALB。尖峰時至少需要 6 台 instance 才能維持正常延遲。營運團隊要求：任何一個 AZ 故障時，服務不能中斷，而且不能依賴故障發生後才啟動新 instance。

哪兩項措施能滿足需求？

- A. 讓 Auto Scaling group 跨三個 AZ，desired capacity 設為 9（每個 AZ 3 台），使任一 AZ 故障後仍保有 6 台
- B. 維持在單一 AZ，但改用規格加倍的 instance，讓 6 台中有部分故障時仍有足夠容量
- C. 把 instance 放進跨 AZ 的 cluster placement group，讓故障時 instance 能自動移到其他 AZ
- D. 維持 6 台 instance 分散在兩個 AZ，並設定 target tracking policy 在 AZ 故障後自動補足容量
- E. ALB 啟用所有 AZ 的 subnet，Auto Scaling group 使用 ELB health check，讓流量只送往健康的 target

> [!answer]- 答案：A、E
> **A ✓** 這就是 static stability：事先在每個 AZ 預留足夠容量，任何一個 AZ 失效時，剩下兩個 AZ 的 6 台正好滿足尖峰需求，不需要等待新 instance 啟動與暖機。
>
> **B ✗** 不論規格多大，單一 AZ 都是單點故障，整個 AZ 失效時所有 instance 一起消失。
>
> **C ✗** Cluster placement group 只能位於單一 AZ，用途是降低 instance 之間的網路延遲，與跨 AZ 容錯相反。
>
> **D ✗** 6 台分散兩個 AZ，失去一個 AZ 只剩 3 台；擴展政策要等指標觸發、instance 啟動與暖機，故障期間會有一段容量不足，違反「不能依賴故障後才啟動新 instance」。
>
> **E ✓** ALB 要在每個 AZ 都有節點與 target，並搭配 ELB health check，AZ 故障或 instance 不健康時，流量才會自動只送往健康的 target，Auto Scaling 也會替換不健康的 instance。
>
> **考點**：SAA-2.2｜跨 AZ 預先配置容量（static stability）與 ELB health check｜延伸閱讀：第 18 章

### 第 16 題｜SAA｜單選｜D4 比賽 replay 檔的儲存成本

電競平台把每場比賽的 replay 檔（平均 200 MB）存在 S3 Standard。Replay 上傳後 7 天內很熱門，30 天後每個檔案平均每月被觀看不到一次，但只要有人點擊就必須立即開始播放。replay 是唯一副本，不能遺失；依公司政策，上傳滿一年後刪除。

哪個方案最具成本效益？

- A. 設定 lifecycle rule，30 天後轉到 S3 Glacier Deep Archive，365 天後刪除
- B. 設定 lifecycle rule，30 天後轉到 S3 One Zone-IA，365 天後刪除
- C. 設定 lifecycle rule，30 天後轉到 S3 Glacier Instant Retrieval，365 天後刪除
- D. 維持 S3 Standard，只設定 365 天後刪除的 lifecycle rule

> [!answer]- 答案：C
> **A ✗** Deep Archive 最便宜，但取回需要數小時（標準 12 小時內），無法「點擊後立即播放」。
>
> **B ✗** One Zone-IA 只存在單一 AZ，該 AZ 毀損時資料會遺失；replay 是唯一副本，不適合。若資料可以重新產生，One Zone-IA 才是合理選擇。
>
> **C ✓** Glacier Instant Retrieval 適合「很少存取、但存取時要毫秒取得」的資料，儲存費比 Standard-IA 更低，取回時收取較高的 retrieval 費用；每月不到一次的存取量下總成本最低。最低儲存期間 90 天，物件在 30 天轉入、365 天刪除，不會產生提前刪除費。
>
> **D ✗** 30 天後幾乎不被存取的資料仍以 Standard 計價，浪費儲存成本。
>
> **考點**：SAA-4.1｜很少存取但需毫秒取回 → Glacier Instant Retrieval｜延伸閱讀：第 23 章

### 第 17 題｜SAA｜單選｜D1 可控管與稽核的加密金鑰

保險科技公司把理賠文件存在 S3。合規團隊要求：公司能自己管理金鑰的存取政策並啟用自動輪替、每一次解密都在 CloudTrail 留下紀錄、負責管理金鑰的人員不能解密資料，必要時能立即停用金鑰讓所有文件無法讀取。

哪個方案最符合需求？

- A. 使用 SSE-S3 預設加密，並以 bucket policy 限制只有理賠應用程式的 role 能讀取物件
- B. 使用 SSE-KMS 搭配 customer managed key，key policy 讓管理員只有金鑰管理權限、只有應用程式 role 有加解密權限，並啟用自動輪替
- C. 使用 SSE-KMS 搭配 AWS managed key（aws/s3），並在 IAM policy 中拒絕金鑰管理員執行 `kms:Decrypt`
- D. 使用 SSE-C，由應用程式在每次請求時提供公司自行保管的金鑰

> [!answer]- 答案：B
> **A ✗** SSE-S3 的金鑰完全由 S3 管理，公司無法設定金鑰政策、無法停用金鑰，也不會在 CloudTrail 留下每次解密的 KMS 紀錄。
>
> **B ✓** Customer managed key 的 key policy 由公司自己撰寫，可以把「管理金鑰」（例如 kms:EnableKeyRotation、kms:DisableKey）與「使用金鑰」（kms:Decrypt、kms:GenerateDataKey）分給不同角色，達成職責分離。每次加解密都會記錄在 CloudTrail，必要時停用金鑰，所有以它加密的物件都無法讀取。
>
> **C ✗** AWS managed key 的 key policy 由 AWS 管理、無法修改，也不能停用或自行設定輪替週期，不符合「自己管理存取政策」與「立即停用」。
>
> **D ✗** SSE-C 的金鑰由公司自己保管與傳送，AWS 不儲存金鑰，也就沒有 KMS 的解密稽核紀錄；應用程式還要自行處理金鑰的保管與輪替，營運負擔大。
>
> **考點**：SAA-1.3｜Customer managed key 的 key policy、職責分離與稽核｜延伸閱讀：第 15 章

### 第 18 題｜SAA｜單選｜D3 量化交易的高效能暫存檔案系統

量化交易公司每晚在 200 台 EC2 上執行風險模擬，需要讀取存放在 S3 的 50 TB 歷史行情資料，模擬程式要求 POSIX 檔案系統介面、數百 GB/s 的總吞吐量與次毫秒級延遲。模擬結果要寫回 S3 供隔天分析，檔案系統本身只在運算期間需要存在。

哪個方案最合適？

- A. 建立 Amazon EFS（Max I/O 效能模式），每晚先把 S3 資料複製進 EFS，再讓 200 台 EC2 掛載
- B. 在每台 EC2 上使用 Mountpoint for Amazon S3 直接掛載 bucket，讓模擬程式讀寫 bucket 中的檔案
- C. 建立一個 io2 EBS volume 並啟用 Multi-Attach，同時掛載到 200 台 EC2
- D. 建立與 S3 bucket 連結的 Amazon FSx for Lustre 檔案系統，運算完成後把結果匯出回 S3

> [!answer]- 答案：D
> **D ✓** FSx for Lustre 是為 HPC 設計的平行檔案系統，提供數百 GB/s 吞吐量與次毫秒延遲、完整 POSIX 介面。它可以與 S3 bucket 建立 data repository association，第一次存取時從 S3 延遲載入資料，結果再匯出回 S3；只在運算期間需要時可以用 scratch 類型降低成本。
>
> **A ✗** EFS 適合一般共享檔案，延遲與吞吐量無法達到 HPC 平行檔案系統的等級，每晚複製 50 TB 也耗時又增加費用。
>
> **B ✗** Mountpoint for Amazon S3 的讀取吞吐量很高，但它不是完整的 POSIX 檔案系統（例如不支援修改既有檔案與部分目錄操作），延遲也達不到次毫秒。若程式只需要大量循序讀取 S3 物件，它反而是最簡單的選擇。
>
> **C ✗** EBS Multi-Attach 僅限 io1／io2、同一個 AZ，最多 16 台 instance，而且需要叢集檔案系統協調寫入，無法掛到 200 台。
>
> **考點**：SAA-3.1｜HPC 高吞吐 POSIX + S3 整合 → FSx for Lustre｜延伸閱讀：第 24 章

### 第 19 題｜SAA｜單選｜D2 依內容路由的 SaaS 事件

CRM SaaS 公司的核心服務會產生 `customer.created`、`deal.won` 等事件。多個內部服務各自需要不同的事件，例如帳務服務只要金額大於 10,000 的 `deal.won`；新的消費者經常加入，但不希望修改事件產生者的程式。公司也要接收合作夥伴 Zendesk 送來的客服工單事件，並以同樣方式路由。

哪個方案以最少營運負擔滿足需求？

- A. 使用 Amazon EventBridge：核心服務發布事件到 custom event bus，以內容篩選的 rule 路由給各消費者，並透過 partner event source 接收 Zendesk 事件
- B. 使用 SNS topic 搭配各訂閱者的 filter policy，並在 EC2 上撰寫程式定期呼叫 Zendesk API 再把工單事件發布到 topic
- C. 把所有事件寫入 Kinesis Data Streams，每個消費者讀取全部事件後在程式內自行過濾需要的類型與金額
- D. 為每個消費者建立一個 SQS queue，由事件產生者依事件類型與金額判斷要寫入哪些 queue

> [!answer]- 答案：A
> **A ✓** EventBridge rule 可以依事件內容（包含數值比較）篩選，新增消費者只要加 rule，不用改產生者。EventBridge 原生支援 SaaS partner event source，Zendesk 等合作夥伴可以直接把事件送進你的 event bus，不必自己輪詢。
>
> **B ✗** SNS filter policy 也能做內容與數值篩選，事件內部路由的部分可行；但 SNS 沒有 SaaS 合作夥伴整合，必須自己寫並維運輪詢 Zendesk 的程式。若沒有 SaaS 事件來源、且需要極高吞吐的 fan-out，SNS 是好選擇。
>
> **C ✗** 每個消費者都要讀取全部事件再自行過濾，浪費讀取容量，且仍需另外處理 Zendesk 事件的接收。
>
> **D ✗** 產生者必須知道所有消費者與其篩選條件，每加一個消費者都要改產生者，是緊耦合設計。
>
> **考點**：SAA-2.1｜內容路由與 SaaS 整合 → EventBridge｜延伸閱讀：第 32 章

### 第 20 題｜SAA｜單選｜D1 學生從 App 直接上傳作業

K-12 教育 App 讓學生以 Google 帳號登入，並從手機直接把作業照片與影片上傳到 S3。每位學生只能讀寫自己的資料夾，App 中不能內嵌任何長期憑證。開發團隊只有兩人，希望盡量少寫與維運後端程式。

哪個方案最符合需求？

- A. 在 App 中內嵌一組 IAM user 的 access key，其 policy 只允許存取作業 bucket
- B. 建立 API Gateway 與 Lambda 作為上傳代理，App 把檔案送到 API，由 Lambda 驗證學生身份後寫入 S3
- C. 使用 Cognito user pool 與 Google 聯合登入，再用 Cognito identity pool 換取臨時 AWS 憑證，IAM role policy 以 `${cognito-identity.amazonaws.com:sub}` 限制每位學生的 prefix
- D. 把 bucket 設定為允許公開寫入，App 以隨機產生的物件名稱上傳，降低被猜到路徑的機率

> [!answer]- 答案：C
> **A ✗** 內嵌的 access key 很容易被反編譯取出，任何人都能用它存取所有學生的作業，且無法區分每位學生的權限。
>
> **B ✗** 能做到身份驗證，但所有檔案都要經過 API Gateway 與 Lambda，受限於 API Gateway 約 10 MB 的 payload 上限，影片無法直接上傳，還要自己維護代理程式。若必須在寫入前做內容檢查，代理或 presigned URL 方案才值得考慮。
>
> **C ✓** User pool 負責驗證（含 Google 聯合登入），identity pool 把登入後的身份換成 IAM role 的臨時憑證。IAM policy 中的 policy variable `${cognito-identity.amazonaws.com:sub}` 會代入每位使用者的 identity ID，讓同一個 role 自動限制「只能存取自己的 prefix」，App 直接上傳 S3，不需要後端代理。
>
> **D ✗** 公開寫入代表任何人都能上傳或覆寫物件，違反存取控制；隨機名稱不是安全機制。
>
> **考點**：SAA-1.1｜Cognito identity pool 臨時憑證與 policy variable｜延伸閱讀：第 13 章

### 第 21 題｜SAA｜單選｜D4 只在上班時間使用的測試資料庫

新創 SaaS 公司為每個開發分支提供一個 Aurora MySQL 測試資料庫，共 30 個，每個都是 24 小時運行的 provisioned db.r6g.large。這些資料庫主要在平日上班時間使用，夜間與週末幾乎沒有流量，但跑整合測試時負載會短暫衝高。團隊希望大幅降低成本，同時不增加維運工作。

哪個方案最符合需求？

- A. 為 30 個測試資料庫購買 1 年期 Reserved Instances
- B. 改成 RDS for MySQL 的 db.t4g.medium 並啟用 Multi-AZ，以較小的 instance 降低費用
- C. 寫一個排程 Lambda，在每天下班時停止所有 Aurora cluster、上班前再啟動
- D. 改用 Aurora Serverless v2，把最小容量設定得很低（支援的版本可設為 0 ACU 自動暫停），讓容量依負載自動伸縮

> [!answer]- 答案：D
> **D ✓** Aurora Serverless v2 以 ACU 為單位、依實際負載秒級伸縮並按用量計費：閒置時降到最小容量，跑整合測試時自動擴大。新版本支援把最小容量設為 0 ACU，閒置一段時間後自動暫停，幾乎不產生運算費用，也不需要任何排程程式。
>
> **A ✗** Reserved Instances 降低的是每小時單價，但資料庫仍然 24 小時計費，夜間與週末的閒置成本並未消失。
>
> **B ✗** 較小的 instance 仍然 24 小時運行，測試尖峰時容量可能不足；測試環境啟用 Multi-AZ 反而讓費用加倍。
>
> **C ✗** 停止 cluster 可以省錢，但 Aurora cluster 停止最多 7 天後會自動啟動，需要自己維護排程與例外處理；上班時間的負載變化也沒有解決。
>
> **考點**：SAA-4.3｜間歇、不可預測負載的資料庫用 Aurora Serverless v2｜延伸閱讀：第 26 章

### 第 22 題｜SAA｜單選｜D3 改版日的全球 patch 下載

遊戲公司把每次改版的 3 GB patch 檔存在 us-west-2 的 S3 bucket，檔名包含版本號、上傳後不會再修改。改版當天全球數百萬玩家同時下載，亞洲與歐洲玩家反映下載很慢，S3 的資料傳出費用也很高。公司希望改善全球下載速度並降低 origin 負載。

哪個方案最合適？

- A. 用 S3 Cross-Region Replication 把 patch 複寫到五個 Region，並用 Route 53 latency-based routing 導到最近的 bucket
- B. 建立 CloudFront distribution，以 Origin Access Control 存取 S3 bucket，並為 patch 檔設定較長的 TTL
- C. 建立 AWS Global Accelerator，把 S3 bucket 設為 endpoint，讓玩家經 AWS 骨幹網路下載
- D. 在 bucket 上啟用 S3 Transfer Acceleration，讓玩家改用 accelerate endpoint 下載

> [!answer]- 答案：B
> **B ✓** CloudFront 會在全球 edge location 快取 patch 檔，同一個檔案只需從 origin 取一次，之後由邊緣直接提供，速度快且 origin 負載低。檔名含版本號、內容不變，可以放心設定長 TTL；OAC 讓 bucket 保持私有。S3 傳到 CloudFront 的流量不收資料傳出費。
>
> **A ✗** 多 Region 複寫能拉近距離，但要付多份儲存與複寫費用，玩家仍直接從 bucket 下載、沒有邊緣快取，管理也比較複雜。
>
> **C ✗** Global Accelerator 的 endpoint 只能是 ALB、NLB、EC2 instance 或 Elastic IP，不能直接指向 S3；它也不做內容快取。
>
> **D ✗** Transfer Acceleration 透過 edge location 加速傳輸，但不快取內容，每次下載都會回到 bucket，還要額外付加速費用，適合「從遠方上傳大檔」。
>
> **考點**：SAA-3.4｜大量重複下載的靜態內容用 CloudFront 快取｜延伸閱讀：第 11 章

### 第 23 題｜SAA｜單選｜D1 輪替 IP 的機器人攻擊

遊戲點數商城架在 CloudFront 與 ALB 之後。最近有大量機器人從不斷輪替的住宅 IP 爬取商品價格，並暴力嘗試兌換序號，以 IP 為單位的 rate limit 幾乎無效。公司希望用受管規則快速防護兌換頁面，維運負擔越低越好。

哪個方案最合適？

- A. 在 CloudFront 上掛 AWS WAF web ACL，啟用 Bot Control managed rule group，並對兌換 API 套用 CAPTCHA 或 Challenge 動作
- B. 訂閱 AWS Shield Advanced 並保護 CloudFront distribution，由 Shield 自動阻擋爬蟲與暴力嘗試
- C. 寫一個 Lambda 分析 ALB access log，把可疑 IP 自動加入 ALB 所在 subnet 的 network ACL deny 規則
- D. 在 ALB 的 security group 只允許來自主要市場國家的 IP 範圍，阻擋其他國家的機器人

> [!answer]- 答案：A
> **A ✓** WAF Bot Control 會依請求特徵、瀏覽器指紋與行為辨識自動化流量（targeted 等級還能偵測較進階的機器人），不只看 IP；對敏感的兌換 API 套用 CAPTCHA 或 Challenge，可以讓真人通過、讓腳本失敗。全部是受管規則，掛在 CloudFront 上能在邊緣就攔截。
>
> **B ✗** Shield Advanced 主要防護 DDoS，雖然包含 WAF 使用權與應變團隊支援，但它本身不是爬蟲或撞庫偵測的機制，仍需要搭配 WAF 規則。
>
> **C ✗** 住宅 IP 不斷輪替，事後封鎖追不上；NACL 每個方向的規則數有限（預設 20 條），而且流量經過 CloudFront 後，ALB 看到的來源是 CloudFront 的位址，封鎖會誤傷正常使用者。
>
> **D ✗** Security group 只有 allow 規則；在 CloudFront 之後，ALB 收到的連線來源是 CloudFront 而非玩家，依國家 IP 過濾根本無法生效。依國家限制應使用 CloudFront geo restriction 或 WAF geo match。
>
> **考點**：SAA-1.2｜機器人與撞庫防護用 WAF Bot Control 與 CAPTCHA｜延伸閱讀：第 16 章

### 第 24 題｜SAA｜單選｜D2 RTO 2 小時的低成本 DR

會計 SaaS 公司的應用程式由 Auto Scaling group 管理的 EC2 與 RDS for PostgreSQL 組成，所有基礎架構都以 CloudFormation 定義。公司要在另一個 Region 建立 DR，要求 RTO 2 小時、RPO 15 分鐘，並在符合目標的前提下讓平時成本最低。

哪個 DR 策略最合適？

- A. Backup and restore：用 AWS Backup 每天備份 EC2 與 RDS 並複製到 DR Region，災難時用 CloudFormation 重建
- B. Pilot light：在 DR Region 建立 RDS cross-Region read replica 並持續複製 AMI，應用程式層以 CloudFormation 預先定義、平時不運行，災難時 promote replica 並啟動應用程式
- C. Warm standby：在 DR Region 以縮小規模持續運行完整的應用程式與資料庫 replica，災難時擴大規模並切換 DNS
- D. Multi-site active-active：兩個 Region 都以完整容量運行並同時接收流量，資料庫改用雙向複寫

> [!answer]- 答案：B
> **A ✗** 每天備份代表 RPO 最長 24 小時，遠超過 15 分鐘的要求；從備份還原資料庫也可能超過 2 小時。
>
> **B ✓** Pilot light 只讓「核心資料」持續運行：cross-Region read replica 以非同步方式持續複寫，RPO 通常為秒到分鐘級；應用程式層只保留 AMI 與 CloudFormation 定義，平時幾乎不花錢。災難時 promote replica、部署並擴展應用程式、切換 DNS，可在 2 小時內完成。
>
> **C ✗** Warm standby 可以達成目標，RTO 也更短，但平時要持續付應用程式層的運行費用，成本高於 pilot light。RTO 只有數分鐘時才需要它。
>
> **D ✗** Active-active 提供近乎零的 RTO，但成本最高，PostgreSQL 雙向複寫也很複雜；對 2 小時的 RTO 而言是過度設計。
>
> **考點**：SAA-2.2｜依 RTO／RPO 與成本選擇 DR 策略：pilot light｜延伸閱讀：第 34 章

### 第 25 題｜SAA｜單選｜D3 合作銀行的 SFTP 檔案交換

支付公司每天從 30 家合作銀行接收清算檔案，目前使用一台自行管理的 SFTP 伺服器（EC2），是單點故障，修補也很麻煩。合作銀行無法更改既有的 SFTP 用戶端與 SSH 金鑰登入方式。公司希望改用受管服務，檔案直接存入 S3，抵達後自動觸發後續處理。

哪個方案最合適？

- A. 請各銀行在自己的機房安裝 AWS DataSync agent，定期把清算檔案同步到 S3 bucket
- B. 建立 API Gateway 端點產生 S3 presigned URL，請各銀行改用 HTTPS 上傳檔案
- C. 建立 AWS Transfer Family 的 SFTP server，以 S3 為儲存後端並為各銀行設定 SSH 公鑰，檔案抵達時以 S3 事件或 managed workflow 觸發處理
- D. 部署 AWS Storage Gateway 的 S3 File Gateway，讓各銀行以 NFS 或 SMB 掛載後寫入檔案

> [!answer]- 答案：C
> **C ✓** Transfer Family 提供受管、高可用的 SFTP 端點，後端直接存入 S3，可以為每家銀行設定 service-managed user 與 SSH 公鑰，銀行端完全不用改用戶端。檔案寫入 S3 後可以用 S3 event notification、EventBridge 或 Transfer Family managed workflow 觸發處理。
>
> **A ✗** DataSync agent 要安裝在資料來源端，合作銀行不會為此在自家機房部署 AWS 元件，而且也改變了雙方約定的 SFTP 協定。
>
> **B ✗** Presigned URL 能安全上傳，但銀行必須改用 HTTPS 用戶端，違反「無法更改 SFTP 用戶端」的限制。
>
> **D ✗** File Gateway 提供的是 NFS／SMB 協定，而且是部署在公司自己的環境，給內部伺服器使用，不是給外部合作夥伴的 SFTP 端點。
>
> **考點**：SAA-3.5｜外部夥伴的 SFTP 檔案交換用 Transfer Family｜延伸閱讀：第 25 章

### 第 26 題｜SAA｜選兩項｜D1 交易確認書的不可竄改保存

線上券商必須把每筆交易確認書保存 7 年，期間任何人（包含 root user）都不能刪除或覆寫。確認書在產生 90 天後幾乎不會被讀取，稽核調閱時 48 小時內取得即可。公司希望在符合法規的前提下讓儲存成本最低。

哪兩項措施能滿足需求？

- A. 建立啟用 S3 Object Lock 的 bucket，設定 compliance mode、預設保留期間 7 年
- B. 建立啟用 S3 Object Lock 的 bucket，設定 governance mode、預設保留期間 7 年
- C. 在 bucket policy 中對所有 principal 拒絕 `s3:DeleteObject` 與 `s3:PutObject` 覆寫操作
- D. 設定 lifecycle rule，在物件建立 90 天後轉到 S3 Glacier Deep Archive
- E. 設定 lifecycle rule，在物件建立 90 天後轉到 S3 Standard-IA

> [!answer]- 答案：A、D
> **A ✓** Compliance mode 的保留期間內，任何使用者（包含 root user）都不能刪除受保護的版本，也不能縮短保留期間，符合 WORM（write once, read many）法規要求。Object Lock 會自動啟用 versioning，覆寫只會產生新版本，原版本仍受保護。
>
> **B ✗** Governance mode 允許擁有 `s3:BypassGovernanceRetention` 權限的使用者刪除物件或移除保留，root user 也可以，不符合「任何人都不能刪除」。它適合內部防誤刪、但需要保留管理彈性的情境。
>
> **C ✗** Bucket policy 可以被有權限的管理員或 root user 修改後再刪除，無法提供法規等級的不可竄改保證。
>
> **D ✓** Deep Archive 是 S3 最便宜的儲存類別，取回時間在 48 小時內（標準取回 12 小時內、bulk 48 小時內），符合調閱需求。Object Lock 的保留設定在 lifecycle 轉換後仍然有效。
>
> **E ✗** Standard-IA 可以立即讀取，但價格遠高於 Deep Archive；48 小時取回可以接受時，沒有必要付這個價格。
>
> **考點**：SAA-1.3、SAA-4.1｜Object Lock compliance mode 與封存儲存類別｜延伸閱讀：第 23 章

### 第 27 題｜SAA｜單選｜D2 講師影片的非同步轉檔

線上課程平台讓講師上傳教學影片，每支影片轉檔需要 5 到 40 分鐘。目前 web server 在收到上傳後同步轉檔，經常造成上傳逾時；上傳量在學期初暴增，平時很少。公司希望把上傳與轉檔解耦，讓轉檔機群依待處理工作量自動伸縮，且工作不能遺失。

哪個設計最合適？

- A. 影片上傳到 S3 後觸發 Lambda，由 Lambda 直接執行轉檔並把結果寫回 S3
- B. 影片上傳到 S3 後發布 SNS 通知，以 HTTP 訂閱直接推送給轉檔 EC2 機群處理
- C. 影片上傳到 S3 後把事件送進 SQS queue，由 Auto Scaling group 的 EC2 worker 輪詢處理，依「每台 instance 待處理訊息數」擴展，並把 visibility timeout 設得比最長轉檔時間更長
- D. 影片上傳到 S3 後把事件寫入 Kinesis Data Streams，每個 shard 對應一台轉檔 EC2，依 shard 數量調整機群大小

> [!answer]- 答案：C
> **C ✓** SQS 把工作暫存在 queue 中，worker 忙不過來時工作不會遺失。以 ApproximateNumberOfMessagesVisible 除以 instance 數作為 target tracking 指標，學期初 backlog 增加時自動擴展、平時縮小。Visibility timeout 大於最長轉檔時間，避免轉檔還沒做完訊息就被另一台 worker 重複取走。
>
> **A ✗** Lambda 最長執行 15 分鐘，40 分鐘的轉檔會被中斷。若轉檔都在 15 分鐘內，或改用 AWS Elemental MediaConvert 這類受管轉檔服務，事件驅動方案才可行。
>
> **B ✗** SNS 是推送模型，沒有讓 worker 依自己的處理速度拉取工作的緩衝；推送失敗的重試次數有限，也沒有可用來擴展的 backlog 指標。
>
> **D ✗** Kinesis 是有序的串流，適合多個 consumer 重複讀取同一份資料；用它分派獨立的長時間工作，平行度受 shard 數限制，單一慢工作還會卡住整個 shard。
>
> **考點**：SAA-2.1｜SQS 解耦長時間工作並依 backlog per instance 擴展｜延伸閱讀：第 32 章

### 第 28 題｜SAA｜單選｜D3 直播投票的熱分割

線上遊戲在年度直播活動中開放觀眾為 5 位選手投票，票數存在 DynamoDB on-demand table，partition key 是 `candidate_id`，每一票對該選手的計數項目做原子遞增。活動期間每秒約 30,000 次寫入，且大多集中在兩位熱門選手，table 出現大量 throttling。團隊需要持續承受寫入尖峰，並能在幾秒內顯示各選手的總票數。

哪個方案最合適？

- A. 把 table 改為 provisioned 模式，並把 write capacity 設為 40,000 WCU
- B. 為 table 建立以 `candidate_id` 為 partition key 的 GSI，把寫入分散到 base table 與 GSI
- C. 在 table 前面加上 DynamoDB Accelerator（DAX），讓寫入先進入 DAX 快取再寫回 table
- D. 使用 write sharding：寫入時把 key 改成 `candidate_id#隨機數（例如 0–49）`，讀取時查詢該選手所有分片後加總

> [!answer]- 答案：D
> **D ✓** DynamoDB 單一 partition 的寫入上限約為每秒 1,000 WCU，同一個 partition key 的所有寫入都落在同一個 partition，無論 table 總容量多大都會 throttle。加上隨機後綴把一位選手的票數分散到 50 個 key，寫入就能分散到多個 partition；讀取時對 50 個分片加總（或由排程程式定期彙總到另一個項目），幾秒內即可顯示總數。
>
> **A ✗** Table 層級的容量再大，也無法突破單一 partition key 的寫入上限，熱 key 仍然會被 throttle。
>
> **B ✗** GSI 以同樣的 `candidate_id` 為 key，熱點只是複製到 GSI；GSI 被 throttle 時還會反壓 base table 的寫入。GSI 不能用來分散寫入。
>
> **C ✗** DAX 是 write-through 快取，每次寫入仍要寫到 DynamoDB，不會增加寫入容量；它加速的是讀取。
>
> **考點**：SAA-3.3｜熱 partition key 用 write sharding 分散寫入｜延伸閱讀：第 27 章

### 第 29 題｜SAA｜單選｜D4 會改變運算平台的穩定基礎負載

一家 SaaS 公司過去一年在 EC2（m5 系列）上的用量非常穩定，24 小時都維持約每小時 40 美元的 On-Demand 花費。工程團隊計畫明年把部分服務遷到 Fargate、部分改用 Graviton instance，並新增一些 Lambda 函式。財務希望取得長期折扣，但不希望被特定 instance 家族或運算服務綁住。

哪個購買方式最合適？

- A. 購買 1 年期 Compute Savings Plans，承諾金額接近目前穩定基礎負載的每小時花費
- B. 購買 1 年期 EC2 Instance Savings Plans，涵蓋目前 Region 的 m5 instance 家族
- C. 購買 3 年期 Standard Reserved Instances，數量等於目前使用的 m5 instance 數
- D. 把所有服務改用 Spot Instances，並設定 Auto Scaling 在中斷時自動補上

> [!answer]- 答案：A
> **A ✓** Compute Savings Plans 以「每小時承諾金額」換取折扣，自動套用到任何 Region、instance 家族、作業系統的 EC2，以及 Fargate 與 Lambda。從 m5 換到 Graviton、從 EC2 遷到 Fargate，折扣都會跟著走，符合「不被綁住」的需求。
>
> **B ✗** EC2 Instance Savings Plans 折扣比較高，但綁定特定 Region 的 instance 家族；改用 Graviton（例如 m7g）就不在涵蓋範圍，Fargate 與 Lambda 也不適用。確定長期使用同一家族時才選它。
>
> **C ✗** Standard RI 綁定 instance 屬性且不能換家族，3 年期限與明年的平台改變衝突。
>
> **D ✗** Spot 可能隨時被中斷，不適合 24 小時穩定運行的正式服務基礎負載。
>
> **考點**：SAA-4.2｜跨 EC2／Fargate／Lambda 的彈性折扣用 Compute Savings Plans｜延伸閱讀：第 39 章

### 第 30 題｜SAA｜單選｜D1 跨帳號送訊息到 SQS

支付平台的帳號 A 有一個 Lambda 函式，需要把交易事件送到帳號 B 的風控 SQS queue（使用 SSE-SQS 加密）。帳號 A 中 Lambda 執行 role 的 identity policy 已允許對該 queue ARN 執行 `sqs:SendMessage`，但呼叫時仍然收到 AccessDenied。兩個帳號屬於同一個 AWS Organization，SCP 沒有限制 SQS。

最合適的修正方式是什麼？

- A. 在 Lambda 執行 role 的 identity policy 改成允許 `sqs:*`，並把 Resource 設為 `*`
- B. 在帳號 B 的 queue 上設定 queue policy，允許帳號 A 的 Lambda 執行 role ARN 執行 `sqs:SendMessage`
- C. 在帳號 B 建立 IAM user 並產生 access key，把金鑰存放在帳號 A 的 Secrets Manager 供 Lambda 使用
- D. 把兩個帳號移到同一個 OU，讓 Organizations 自動允許同 OU 帳號之間存取資源

> [!answer]- 答案：B
> **A ✗** 跨帳號存取需要雙方都允許：呼叫端的 identity policy 已經允許，缺的是資源擁有者（帳號 B）的授權。把權限放大到 `sqs:*` 與 `*` 不會解決問題，還違反最小權限。
>
> **B ✓** SQS 支援 resource-based policy。帳號 B 在 queue policy 中把帳號 A 的 role ARN 列為 principal、允許 `sqs:SendMessage`，加上帳號 A 原本的 identity policy，跨帳號呼叫就會成功。（如果 queue 改用 SSE-KMS 加密，還必須在 KMS key policy 中授權該 role 使用金鑰，且不能用無法修改 key policy 的 AWS managed key。）
>
> **C ✗** 使用長期 access key 違反最佳實務，也增加金鑰外洩與輪替的負擔；resource policy 或跨帳號 role 都能用臨時憑證完成。
>
> **D ✗** Organizations 與 OU 不會自動授予任何資源存取權；SCP 也只會限制、不會授權。
>
> **考點**：SAA-1.1｜跨帳號存取需要 identity policy 與 resource policy 雙方允許｜延伸閱讀：第 13 章

### 第 31 題｜SAA｜單選｜D3 支付 API 的冷啟動延遲

行動支付 App 的 API 由 API Gateway 與以 Java 撰寫的 Lambda 組成。每天早上 7 點到 9 點流量快速攀升，期間 p99 延遲偶爾高達 4 秒，分析後確認是大量新執行環境的冷啟動造成。產品要求這段時間的 p99 延遲低於 300 毫秒，流量模式每天都很一致。

哪個方案最合適？

- A. 為函式設定 provisioned concurrency，並以 Application Auto Scaling 的排程在每天早上尖峰前提高、尖峰後降低
- B. 為函式設定較高的 reserved concurrency，確保尖峰時有足夠的並行數
- C. 把函式記憶體提高到 10,240 MB，讓初始化階段有更多 CPU 可以使用
- D. 在 API Gateway stage 啟用快取，讓重複的支付請求直接由快取回應

> [!answer]- 答案：A
> **A ✓** Provisioned concurrency 會預先初始化指定數量的執行環境，請求到來時直接使用，沒有冷啟動。流量模式固定，就用排程在尖峰前提高、尖峰後降低，只為需要的時段付費。（Java 函式也可以評估 Lambda SnapStart 來縮短初始化時間。）
>
> **B ✗** Reserved concurrency 是「保留並限制」函式的最大並行數，不會預先初始化執行環境，冷啟動仍然存在。
>
> **C ✗** 更多記憶體與 CPU 能縮短初始化時間，但每個新環境仍要經歷冷啟動，Java 的 JVM 啟動與類別載入很難壓到 300 毫秒以下，成本也大幅增加。
>
> **D ✗** 支付請求多為 POST 且每筆內容不同，不能也不應被快取，否則可能回傳錯誤的交易結果。
>
> **考點**：SAA-3.2｜可預測尖峰的冷啟動用排程的 provisioned concurrency｜延伸閱讀：第 19 章

### 第 32 題｜SAA｜單選｜D2 主備 Region 的 DNS 自動切換

專案管理 SaaS 的 API 主要在 us-east-1 運行，us-west-2 有一套以縮小規模持續運行的備援環境，兩邊各有一個 ALB。公司希望 us-east-1 的應用程式不健康時，使用者的 DNS 查詢自動改為回應 us-west-2；us-east-1 恢復後自動切回。平時所有流量都必須只進 us-east-1。

哪個 Route 53 設定最合適？

- A. 建立兩筆 weighted 記錄，us-east-1 權重 100、us-west-2 權重 0，不設定 health check
- B. 建立兩筆 latency-based 記錄分別指向兩個 ALB，並為兩筆記錄都設定 health check
- C. 建立一筆 simple 記錄，值同時包含兩個 ALB 的位址，由用戶端自行挑選可連線的位址
- D. 建立 failover 記錄：primary 指向 us-east-1 的 ALB 並關聯檢查 `/health` 的 health check，secondary 指向 us-west-2 的 ALB

> [!answer]- 答案：D
> **D ✓** Failover routing 正是 active-passive 的設計：primary 健康時只回應 primary，health check 判定失敗後改回應 secondary，primary 恢復健康後自動切回。檢查應用程式的 `/health` 路徑，比只檢查 ALB 是否存活更能反映真實狀態（alias 記錄也可以搭配 Evaluate Target Health）。
>
> **A ✗** 沒有 health check 時 Route 53 不知道 us-east-1 故障，權重 100／0 的設定永遠只回應 us-east-1，不會切換。
>
> **B ✗** Latency-based routing 會把使用者導到延遲最低的 Region，西岸使用者平時就會進 us-west-2，違反「平時只進 us-east-1」。它適合 active-active。
>
> **C ✗** Simple routing 不支援 health check，也無法指定主備順序；而且指向 ALB 要用 alias 記錄（或子網域的 CNAME），兩者都只能有一個目標，不能把兩個 ALB 寫在同一筆記錄中。就算能寫，用戶端也會隨機連到兩個 Region，違反「平時只進 us-east-1」。
>
> **考點**：SAA-2.2｜Active-passive 跨 Region 切換用 Route 53 failover routing + health check｜延伸閱讀：第 9 章

### 第 33 題｜SAA｜單選｜D1 沒有 Internet 出口的 Lambda 讀取機密

金融科技公司的 Lambda 函式部署在 VPC 的 isolated subnet（沒有 NAT Gateway 也沒有 Internet Gateway 路由），以便連線同一個 VPC 中的 RDS。函式啟動時需要從 Secrets Manager 讀取資料庫憑證，但目前呼叫一律 timeout。資安政策禁止這些 subnet 有任何 Internet 出口。

哪個方案最合適？

- A. 在 public subnet 建立 NAT Gateway，並把 isolated subnet 的預設路由指向它
- B. 建立 Secrets Manager 的 gateway VPC endpoint，並把它加到 isolated subnet 的 route table
- C. 把 Lambda 移出 VPC，讓它可以直接透過 AWS 公用端點存取 Secrets Manager
- D. 建立 Secrets Manager 的 interface VPC endpoint 並啟用 private DNS，endpoint 的 security group 允許來自 Lambda security group 的 443 連線

> [!answer]- 答案：D
> **D ✓** Interface endpoint（AWS PrivateLink）在 subnet 中建立私有 IP 的網卡，啟用 private DNS 後，SDK 呼叫的預設 Secrets Manager 網域會解析到這些私有 IP，不必改程式，流量也不離開 AWS 網路。Endpoint 的 security group 要允許 Lambda 的 HTTPS 連線。
>
> **A ✗** NAT Gateway 就是 Internet 出口，直接違反資安政策。
>
> **B ✗** Gateway endpoint 只支援 S3 與 DynamoDB，Secrets Manager 只能用 interface endpoint。
>
> **C ✗** 移出 VPC 後 Lambda 就無法連到 VPC 內的私有 RDS，解決一個問題又製造另一個。
>
> **考點**：SAA-1.2｜無 Internet 出口的 subnet 以 interface endpoint 私有存取 AWS 服務｜延伸閱讀：第 6 章

### 第 34 題｜SAA｜單選｜D3 十八個 VPC 與地端的集中互連

教育集團在同一個 Region 的 3 個帳號中共有 18 個 VPC，另外還要透過 Site-to-Site VPN 連到總部機房。目前以 VPC peering 兩兩連接，路由表越來越難管理，地端也無法透過 peering 連到所有 VPC。集團希望集中管理、容易擴充，並讓開發與正式環境的 VPC 彼此不能互通。

哪個方案最合適？

- A. 把所有 VPC 改成 full mesh 的 VPC peering，並在每個 VPC 各自建立一條到總部的 VPN
- B. 建立一個 transit VPC，在其中部署第三方路由器 EC2 作為 hub，所有 VPC 與總部 VPN 都連到這些路由器
- C. 建立 Transit Gateway 並用 AWS RAM 分享給其他帳號，把 18 個 VPC 與 VPN 接上，並以不同的 Transit Gateway route table 隔離開發與正式環境
- D. 在每個 VPC 中為其他 VPC 建立 interface VPC endpoint，透過 AWS PrivateLink 互相存取

> [!answer]- 答案：C
> **C ✓** Transit Gateway 是 hub-and-spoke 的區域路由器，VPC 與 VPN 都只要接一次；AWS RAM 讓同組織的其他帳號附加自己的 VPC。透過多張 TGW route table 的 association 與 propagation 設計，可以讓開發與正式 VPC 各自只能看到允許的目的地，地端仍可連到兩者。
>
> **A ✗** 18 個 VPC 的 full mesh 需要 153 條 peering，路由表難以維護；peering 不具遞移性，每個 VPC 各拉一條 VPN 也增加大量管理工作。
>
> **B ✗** Transit VPC 是 Transit Gateway 出現前的舊做法，需要自己維運路由器 instance 的高可用、修補與授權，營運負擔高。
>
> **D ✗** PrivateLink 是把「特定服務」單向暴露給其他 VPC，不提供一般的雙向網路路由，也無法讓地端透過 VPN 存取所有 VPC。
>
> **考點**：SAA-3.4｜多 VPC 與 hybrid 集中互連與路由隔離用 Transit Gateway｜延伸閱讀：第 7 章

### 第 35 題｜SAA｜選兩項｜D4 Versioning bucket 的儲存費失控

SaaS 公司把客戶資料的每日備份上傳到一個啟用 versioning 的 S3 bucket，大型檔案以 multipart upload 上傳。實際有效的資料量一年來幾乎沒變，但儲存費用每月持續上升。S3 Storage Lens 顯示有大量 noncurrent version 與未完成的 multipart upload。公司要求誤刪或覆寫後 30 天內仍可以復原。

哪兩項措施能在符合需求的前提下降低成本？

- A. 停用 bucket 的 versioning，避免之後再產生 noncurrent version
- B. 設定 lifecycle rule，讓 noncurrent version 在變成 noncurrent 30 天後過期刪除
- C. 設定 lifecycle rule，自動中止開始超過 7 天仍未完成的 multipart upload
- D. 把整個 bucket 的物件改成 S3 Intelligent-Tiering，讓不常用的版本自動降到低價層
- E. 在 bucket 啟用 S3 Object Lock，防止新的版本不斷產生

> [!answer]- 答案：B、C
> **A ✗** Versioning 啟用後只能「暫停」而不能完全關閉；暫停後也無法再保留被覆寫或刪除的舊版本，違反 30 天內可復原的需求，既有的 noncurrent version 也不會消失。
>
> **B ✓** NoncurrentVersionExpiration 在版本變成 noncurrent 滿 30 天後自動刪除，正好保留 30 天的復原窗口，同時清掉更舊的版本。
>
> **C ✓** 未完成的 multipart upload 已上傳的 part 會持續計費，但在 console 中看不到成為物件；AbortIncompleteMultipartUpload 規則會自動清除它們。
>
> **D ✗** Intelligent-Tiering 只能降低單價，舊版本與未完成的 part 仍然一直累積；而且未完成的 multipart upload 不是物件，不會被轉換。
>
> **E ✗** Object Lock 是防止刪除，只會讓舊版本更不能被清除，成本更高；也無法阻止新版本產生。
>
> **考點**：SAA-4.1｜Noncurrent version 過期與中止未完成的 multipart upload｜延伸閱讀：第 23 章

### 第 36 題｜SAA｜單選｜D2 小團隊的容器化微服務

一家 3 人的新創 SaaS 團隊有 8 個容器化微服務，目前全部以 docker compose 跑在一台 EC2 上，其中有幾個是持續運行、需要維持長連線的背景 worker。團隊希望各服務能獨立擴展、透過 ALB 依路徑路由到不同服務，且不想再修補或管理任何伺服器。

哪個方案最合適？

- A. 建立 Amazon EKS cluster 搭配自行管理的 EC2 node group，把 8 個服務部署成 Kubernetes Deployment
- B. 使用 Amazon ECS 搭配 AWS Fargate，把每個微服務建成獨立的 ECS service，前端用 ALB 的 path-based routing，並設定 service auto scaling
- C. 為每個微服務建立一個 Elastic Beanstalk 的單一容器環境，各自以 EC2 執行並啟用受管平台更新
- D. 把 8 個服務全部改寫成以 container image 部署的 Lambda 函式，前面用 API Gateway 依路徑路由

> [!answer]- 答案：B
> **B ✓** Fargate 是 serverless 的容器運算引擎，不用管理或修補 EC2；每個微服務是一個 ECS service，可以各自設定 task 數與 auto scaling，ALB 的 path-based rule 把請求導到對應的 target group。持續運行的背景 worker 也能以 service 的形式長時間運行。
>
> **A ✗** 自行管理的 node group 需要負責 EC2 的修補與擴展，EKS 本身也有較高的學習與維運成本；對 3 人團隊不是最低負擔。若團隊已有 Kubernetes 經驗，EKS on Fargate 才值得考慮。
>
> **C ✗** Beanstalk 雖然簡化部署，但底下仍是要付費與管理的 EC2；8 個獨立環境的維運也比在同一個 ECS cluster 中管理更繁瑣。
>
> **D ✗** Lambda 單次最長執行 15 分鐘，無法承載需要持續運行與長連線的背景 worker，而且要大幅改寫程式。
>
> **考點**：SAA-2.1｜不管理伺服器的容器微服務用 ECS on Fargate｜延伸閱讀：第 21 章

### 第 37 題｜SAA｜單選｜D1 強制資料庫連線加密

信用評分公司使用 RDS for PostgreSQL。稽核發現部分舊的內部用戶端以未加密的方式連線資料庫，要求所有連到資料庫的連線都必須使用 TLS，並且要在資料庫端強制執行，而不是依賴各用戶端自律。

哪個做法最合適？

- A. 在 DB instance 關聯的自訂 DB parameter group 中把 `rds.force_ssl` 設為 1，並讓用戶端使用 RDS 提供的 CA 憑證驗證伺服器
- B. 為 DB instance 啟用以 KMS customer managed key 進行的儲存加密
- C. 修改資料庫的 security group，只允許來自應用程式 security group 的 5432 連線
- D. 在資料庫前面建立一個 TLS listener 的 NLB，要求所有用戶端改連 NLB

> [!answer]- 答案：A
> **A ✓** RDS for PostgreSQL 的 `rds.force_ssl` 參數設為 1 後，資料庫會拒絕所有非 TLS 的連線，從伺服器端強制執行傳輸加密。用戶端搭配 RDS 的 CA bundle，還能驗證連到的是真正的資料庫，防止中間人攻擊。
>
> **B ✗** 儲存加密保護的是靜態資料（at rest），對網路傳輸中的資料沒有作用。
>
> **C ✗** Security group 控制「誰可以連」，不會檢查連線是否使用 TLS。
>
> **D ✗** 用戶端仍然可以繞過 NLB 直接連到資料庫端點，無法「在資料庫端強制」；還多了一層要維運的元件。
>
> **考點**：SAA-1.3｜RDS 傳輸加密在伺服器端強制（rds.force_ssl）｜延伸閱讀：第 26 章

### 第 38 題｜SAA｜選兩項｜D3 學習事件轉成可查詢的 Parquet

線上學習平台的前端每秒送出數千筆 JSON 格式的學習行為事件（觀看影片、作答、暫停）。資料分析師希望 5 分鐘內就能用 SQL 查到新事件，資料要以 Parquet 格式、依日期分區存放在 S3，以降低查詢成本。團隊希望營運負擔最小。

哪兩項組合能滿足需求？

- A. 由 EC2 上的 cron 程式每小時把 JSON 檔案轉成 Parquet，再上傳到 S3 的日期資料夾
- B. 把事件送進 Kinesis Data Streams，在 EC2 上用 KCL 撰寫 consumer 把資料轉成 Parquet 寫入 S3
- C. 把事件送進 Amazon Data Firehose，啟用 record format conversion（以 AWS Glue Data Catalog 的 schema 轉成 Parquet），並以日期作為 S3 prefix 分區
- D. 把事件寫入 RDS for PostgreSQL，讓分析師直接在資料庫中查詢
- E. 在 AWS Glue Data Catalog 中為 S3 資料建立 table（可使用 partition projection），讓分析師以 Amazon Athena 查詢

> [!answer]- 答案：C、E
> **A ✗** 每小時批次轉換無法滿足 5 分鐘內可查詢，還要自己維運 EC2 與排程程式。
>
> **B ✗** 技術上可行，但要自己撰寫、部署、擴展 KCL consumer，營運負擔遠大於 Firehose 的內建轉換。
>
> **C ✓** Firehose 是全受管的傳遞服務，可以依 Glue table 的 schema 把 JSON 轉成 Parquet，並以時間或動態分區設定 S3 prefix；緩衝時間可以設在數十秒到數分鐘，符合 5 分鐘內可查詢。
>
> **D ✗** 每秒數千筆的事件長期累積，用關聯式資料庫做分析查詢既昂貴又難擴展，也不符合「存放在 S3」的需求。
>
> **E ✓** Athena 是 serverless 的 SQL 查詢服務，直接查詢 S3 上的 Parquet 資料，只按掃描量計費；partition projection 讓新的日期分區不需要另外執行 crawler 或 MSCK REPAIR 就能被查詢。
>
> **考點**：SAA-3.5｜Firehose 格式轉換 + Athena 查詢 S3 data lake｜延伸閱讀：第 31 章

### 第 39 題｜SAA｜選兩項｜D1 委派建立 role 但防止提權

遊戲公司希望讓各遊戲團隊的開發者自行建立 Lambda 執行 role，以加快開發速度。平台團隊要求：開發者建立的 role 權限絕對不能超過平台團隊定義的範圍，開發者也不能移除或修改這個限制，以免透過新 role 提升自己的權限。

哪兩項措施能達成需求？

- A. 建立一個 customer managed policy 作為 permissions boundary，定義遊戲團隊 role 可以擁有的最大權限
- B. 給開發者 `iam:*` 權限，並以 CloudTrail 與 EventBridge 偵測建立高權限 role 的事件後通知平台團隊
- C. 以 SCP 拒絕遊戲團隊帳號中所有的 `iam:CreateRole` 呼叫，改由平台團隊集中建立 role
- D. 開發者的 policy 只在 `iam:PermissionsBoundary` 條件等於該 boundary ARN 時允許 `iam:CreateRole` 與附加 policy，並明確拒絕刪除 boundary 與修改 boundary policy
- E. 用 IAM Access Analyzer 依 CloudTrail 紀錄為每個新 role 產生最小權限 policy

> [!answer]- 答案：A、D
> **A ✓** Permissions boundary 設定的是 role 的「權限上限」：有效權限是 identity policy 與 boundary 的交集，就算 role 被附加 AdministratorAccess，也不會超出 boundary。
>
> **B ✗** 這是偵測性控制，事件發生後才通知，提權在通知前就可能已被利用，不符合「絕對不能超過」。
>
> **C ✗** 完全禁止建立 role 可以防止提權，但違反「讓開發者自行建立」的目標，又回到集中處理的瓶頸。
>
> **D ✓** 只靠 boundary 還不夠，必須確保開發者「一定要」掛上 boundary 才能建立 role，並且不能移除或改寫它。以 `iam:PermissionsBoundary` 條件限制 CreateRole，再拒絕 `iam:DeleteRolePermissionsBoundary` 與對 boundary policy 的 `iam:CreatePolicyVersion` 等操作，才構成完整的防護。
>
> **E ✗** Access Analyzer 的 policy generation 能協助產生最小權限 policy，但它只是建議，無法阻止開發者建立權限過大的 role。
>
> **考點**：SAA-1.1｜Permissions boundary 與條件式委派防止權限提升｜延伸閱讀：第 12 章

### 第 40 題｜SAA｜單選｜D4 流量已穩定的 DynamoDB table

電子錢包 App 的交易紀錄 table 上線初期使用 DynamoDB on-demand 模式。一年後流量已經非常穩定：每天有固定的日夜週期，尖峰約為基礎量的兩倍，從未出現突發暴增。帳單顯示讀寫請求費用占 table 成本的絕大部分，儲存費用很少。財務希望降低成本。

哪個做法最合適？

- A. 維持 on-demand 模式，並在 table 前加上 DAX 叢集吸收讀取請求
- B. 把交易紀錄遷移到 Aurora PostgreSQL，以 Reserved Instances 取得折扣
- C. 改為 provisioned capacity 並設定 auto scaling 追蹤日夜週期，再為穩定的基礎容量購買 reserved capacity
- D. 把 table class 改為 DynamoDB Standard-Infrequent Access，以降低整體費用

> [!answer]- 答案：C
> **C ✓** 流量可預測時，provisioned capacity 的單位成本明顯低於 on-demand；auto scaling 依目標使用率追蹤日夜變化，reserved capacity 再為長期穩定的基礎容量提供額外折扣。
>
> **A ✗** DAX 只能減少讀取，寫入仍以 on-demand 價格計費，還多了 DAX 叢集的費用；交易紀錄類工作負載不一定有高重複讀取。
>
> **B ✗** 更換資料庫需要大量改寫與遷移，風險與成本都高，而且 DynamoDB 只要換容量模式就能省下大部分費用。
>
> **D ✗** Standard-IA table class 降低儲存單價、但提高讀寫單價，適合「儲存費占大宗」的 table；這個 table 的成本主要是讀寫，改用 Standard-IA 反而更貴。
>
> **考點**：SAA-4.3｜穩定可預測的 DynamoDB 流量改用 provisioned + auto scaling + reserved capacity｜延伸閱讀：第 27 章

### 第 41 題｜SAA｜單選｜D2 多 Region 的玩家資料

線上角色扮演遊戲把玩家資料（遊戲幣、背包、等級）存放在 us-east-1 的 DynamoDB table。遊戲即將在歐洲與亞洲上線，玩家會連到最近的 Region 遊玩，所有 Region 都要能讀寫玩家資料。某個 Region 故障時，玩家必須能立即改連其他 Region 繼續遊戲；同一筆資料在不同 Region 同時更新時，以最後寫入者為準即可接受。

哪個方案以最低營運負擔滿足需求？

- A. 把 table 轉成 DynamoDB global tables，在 eu-west-1 與 ap-northeast-1 新增 replica
- B. 在其他 Region 建立相同結構的 table，以 DynamoDB Streams 觸發 Lambda 把變更複製到其他 Region
- C. 每小時建立 DynamoDB 備份並複製到其他 Region，故障時在當地 Region 從備份還原 table
- D. 在歐洲與亞洲 Region 各建立 DAX 叢集，讓當地玩家透過 DAX 讀寫 us-east-1 的 table

> [!answer]- 答案：A
> **A ✓** Global tables 提供受管的多 Region、多主（multi-active）複寫，每個 replica 都能讀寫，變更通常在一秒內同步到其他 Region，衝突時採 last writer wins。某個 Region 故障時，應用程式改連其他 Region 的 replica 即可。
>
> **B ✗** 自己寫跨 Region 複寫要處理重試、順序、衝突與複寫迴圈，等於重新實作 global tables，營運負擔高。
>
> **C ✗** 備份還原需要時間、而且會遺失最多一小時的資料，無法「立即」切換，平時其他 Region 也不能讀寫。
>
> **D ✗** DAX 是部署在 VPC 中的區域性快取，只能加速同 Region table 的讀取；寫入仍要跨洋回到 us-east-1，us-east-1 故障時整個遊戲都無法寫入。
>
> **考點**：SAA-2.2｜多 Region 讀寫與 Region 容錯用 DynamoDB global tables｜延伸閱讀：第 27 章

### 第 42 題｜SAA｜單選｜D1 自動隔離被入侵的遊戲伺服器

遊戲公司在數百台 EC2 上執行遊戲伺服器，擔心 instance 被入侵後被拿去挖礦或連線到惡意控制伺服器。資安團隊希望在數分鐘內偵測並自動隔離可疑的 instance，同時保留磁碟證據供鑑識，並且盡量不自行撰寫偵測規則。

哪個方案最合適？

- A. 為每台 instance 設定 CloudWatch alarm，CPU 使用率持續超過 90% 時自動終止 instance
- B. 啟用 Amazon GuardDuty，以 EventBridge rule 比對加密貨幣挖礦等 finding 類型，觸發自動化程序把 instance 換成隔離用 security group 並建立 EBS snapshot
- C. 啟用 VPC Flow Logs 寫入 S3，每天用 Athena 查詢連往可疑 IP 的流量並人工處理
- D. 啟用 Amazon Macie，偵測 instance 上的惡意程式並自動停止受影響的 instance

> [!answer]- 答案：B
> **B ✓** GuardDuty 以機器學習與威脅情資分析 VPC Flow Logs、DNS 查詢與 CloudTrail，內建 CryptoCurrency、與已知 C&C 伺服器通訊等 finding 類型，不必自己寫規則。Finding 送到 EventBridge 後，可以觸發 Lambda 或 Systems Manager Automation，把 instance 的 security group 換成不允許任何連線的隔離 security group，並建立 EBS snapshot 保存證據。
>
> **A ✗** 遊戲伺服器本來就可能 CPU 很高，誤判率高；直接終止 instance 還會讓磁碟與記憶體中的鑑識證據消失。
>
> **C ✗** 每天查詢一次加人工處理，無法在數分鐘內反應，也要自己維護查詢邏輯與可疑 IP 清單。
>
> **D ✗** Macie 是分析 S3 中的敏感資料，不會偵測 EC2 上的惡意程式或可疑網路行為。
>
> **考點**：SAA-1.2｜GuardDuty finding + EventBridge 自動化事件回應｜延伸閱讀：第 16 章

### 第 43 題｜SAA｜單選｜D3 關鍵資料庫的 block storage

遊戲公司有一套無法遷移到受管服務的舊版資料庫，自行安裝在 EC2 上。它要求單一 volume 能持續提供 60,000 IOPS 與穩定的次毫秒延遲；由於存放玩家交易資料，團隊希望 volume 本身擁有 EBS 中最高的耐久性等級。

哪個 volume 類型最合適？

- A. gp3，並把佈建的 IOPS 與 throughput 調到需要的數值
- B. st1，以大容量 HDD 提供穩定的循序讀寫效能
- C. io2 Block Express，佈建 60,000 IOPS
- D. Instance store 的 NVMe SSD，以最低延遲提供高 IOPS

> [!answer]- 答案：C
> **C ✓** io2 Block Express 是為關鍵、I/O 密集資料庫設計的 Provisioned IOPS SSD，可以佈建遠高於 60,000 的 IOPS（最高 256,000），平均延遲在次毫秒等級，耐久性為 99.999%，是 EBS 中最高的一級。
>
> **A ✗** gp3 是通用型 SSD，現在單一 volume 最高可佈建 80,000 IOPS，IOPS 數字本身做得到；但它的延遲是「個位數毫秒」等級，不是次毫秒，耐久性也只有 99.8%–99.9%，低於 io2 的 99.999%。題目同時要求次毫秒延遲與最高耐久性，所以選 io2。一般工作負載則應優先選 gp3 以節省成本。
>
> **B ✗** st1 是 throughput 最佳化的 HDD，適合大型循序讀寫（例如日誌、資料倉儲），隨機 IOPS 很低，不適合資料庫。
>
> **D ✗** Instance store 延遲最低，但 instance 停止、終止或底層硬體故障時資料就會消失，不能存放唯一一份的交易資料。
>
> **考點**：SAA-3.1｜關鍵高 IOPS 資料庫選 io2 Block Express｜延伸閱讀：第 24 章

### 第 44 題｜SAA｜單選｜D2 數萬租戶各自的排程報表

行銷 SaaS 讓每個租戶設定自己的每週報表寄送時間，時間依各租戶所在時區而定，目前有約 2 萬個租戶，數量還會持續增減。現行做法是在一台 EC2 上維護 crontab，這台機器一旦故障所有報表都不會寄出。公司希望改用受管、可擴展的排程方式，並且失敗時能自動重試。

哪個方案最合適？

- A. 為每個租戶建立一條 EventBridge 排程 rule，觸發 Lambda 產生報表
- B. 在 ECS 上執行一個常駐的排程 container，從資料庫讀取所有租戶的寄送時間並在時間到時觸發報表
- C. 使用 EventBridge Scheduler 為每個租戶建立一個帶時區設定的排程，目標為 SQS 或 Lambda，並設定重試政策與 dead-letter queue
- D. 為每個租戶啟動一個 Step Functions Standard Workflow，以 Wait state 迴圈等待每週的寄送時間

> [!answer]- 答案：C
> **C ✓** EventBridge Scheduler 專門處理大量的個別排程：每個排程可以設定 cron 運算式與時區（自動處理夏令時間），預設 quota 可支援大量排程，內建重試政策與 dead-letter queue，完全不用管理伺服器，新增或刪除租戶時只要建立或刪除對應的排程。
>
> **A ✗** EventBridge 的排程 rule 有每個 event bus 的 rule 數量上限（預設 300，可申請提高），排程運算式以 UTC 計算、不支援時區，2 萬個租戶難以管理。
>
> **B ✗** 常駐的排程程式仍是自己要維護的單點，要處理高可用、時區與重試邏輯。
>
> **D ✗** Standard Workflow 單次執行最長 1 年，每週迴圈的狀態轉換會持續累積費用，2 萬個長期執行的 workflow 既昂貴又難以管理。
>
> **考點**：SAA-2.1｜大量個別排程用 EventBridge Scheduler｜延伸閱讀：第 32 章

### 第 45 題｜SAA｜單選｜D1 確保新的 EBS volume 一律加密

稽核發現一家 SaaS 公司的帳號中，有部分由不同團隊建立的 EBS volume 沒有加密。公司要求：從現在起，這個帳號在使用中的每個 Region 建立的所有新 EBS volume 都自動以公司的 customer managed key 加密，而且不需要各團隊修改既有的 CloudFormation 範本或 launch template。

哪個做法最合適？

- A. 部署 AWS Config managed rule `encrypted-volumes`，並在發現未加密 volume 時通知建立者
- B. 以 SCP 拒絕 `Encrypted` 條件為 false 的 `ec2:CreateVolume` 與 `ec2:RunInstances` 呼叫
- C. 以 EventBridge 偵測 CreateVolume 事件，觸發 Lambda 直接對新建立的 volume 啟用加密
- D. 在每個使用中的 Region 啟用 EBS encryption by default，並把預設 KMS key 設為公司的 customer managed key

> [!answer]- 答案：D
> **D ✓** EBS encryption by default 是帳號、Region 層級的設定，啟用後該 Region 新建立的 volume 與由 snapshot 建立的 volume 都會自動加密，並使用指定的預設 KMS key，各團隊的範本不需要任何修改。既有的未加密 volume 不受影響，需另外以加密的 snapshot copy 重建。
>
> **A ✗** Config rule 只能在事後偵測與通知，未加密的 volume 仍然會被建立。
>
> **B ✗** SCP 能阻止建立未加密 volume，但沒有指定加密的既有範本會直接部署失敗，等於強迫各團隊修改範本，違反需求。
>
> **C ✗** EBS volume 無法在建立後「原地」啟用加密，只能透過 snapshot 複製時加密再重建，Lambda 無法直接做到。
>
> **考點**：SAA-1.3｜EBS encryption by default 是 Region 層級的帳號設定｜延伸閱讀：第 24 章

### 第 46 題｜SAA｜單選｜D3 緊密耦合的模擬運算

遊戲引擎團隊在 16 台 EC2 上執行緊密耦合的物理模擬，各節點之間以 MPI 頻繁交換小訊息，效能主要取決於節點之間的網路延遲與每秒封包數。這是可以重新執行的批次工作，不需要高可用。

哪個部署方式能提供最佳效能？

- A. 把 16 台 instance 放進 spread placement group，確保每台位於不同的硬體機架
- B. 把 16 台 instance 放進單一 AZ 的 cluster placement group，並使用支援 ENA 或 EFA 的 instance type
- C. 把 16 台 instance 放進 partition placement group，每個 partition 放 4 台
- D. 把 16 台 instance 平均分散到三個 AZ，以避免單一 AZ 的容量不足

> [!answer]- 答案：B
> **B ✓** Cluster placement group 會把 instance 放在同一個 AZ 中網路距離很近的硬體上，提供最低延遲與最高的每秒封包數；搭配 enhanced networking（ENA）或 Elastic Fabric Adapter（EFA，專為 MPI 等 HPC 通訊設計）效果最好。工作不需要高可用，集中在一起的風險可以接受。
>
> **A ✗** Spread placement group 刻意把 instance 分散到不同機架以降低同時故障的機率，每個 AZ 最多 7 台，網路距離反而變遠。
>
> **C ✗** Partition placement group 用於 HDFS、Cassandra 這類需要「故障範圍隔離」的大型分散式系統，不是為最低延遲設計的。
>
> **D ✗** 跨 AZ 部署會增加節點間的網路延遲，也會產生跨 AZ 資料傳輸費，與緊密耦合工作的需求相反。
>
> **考點**：SAA-3.2｜緊密耦合 HPC 用 cluster placement group + ENA／EFA｜延伸閱讀：第 17 章

### 第 47 題｜SAA｜單選｜D4 課程影片的資料傳出費用

線上課程平台的 MP4 教學影片存放在 S3，學生分布在台灣、日本與美國，直接透過 S3 URL 觀看，每月 S3 資料傳出量約 300 TB，而且同一批熱門影片被大量重複觀看。財務希望降低資料傳輸成本，同時改善播放體驗。

哪個方案最合適？

- A. 在 bucket 上啟用 Requester Pays，讓觀看影片的一方負擔資料傳輸費用
- B. 把影片搬到 EC2 上的 EBS volume，由 web server 直接提供下載
- C. 在 bucket 上啟用 S3 Transfer Acceleration，讓學生經由最近的 edge location 下載影片
- D. 建立 CloudFront distribution 以 Origin Access Control 存取 bucket，讓學生透過 CloudFront 觀看影片

> [!answer]- 答案：D
> **D ✓** 從 S3 傳到 CloudFront 的流量不收費，CloudFront 再從 edge 把影片傳給學生；熱門影片被快取後，大部分請求不需要回到 S3。CloudFront 的資料傳出單價一般也低於 S3 直接傳出、且有用量分級折扣，同時改善延遲與播放體驗。
>
> **A ✗** Requester Pays 要求請求者是已驗證的 AWS 帳號並由其付費，匿名的學生無法使用，課程平台也不可能要求學生付 AWS 費用。
>
> **B ✗** EC2 傳出到 Internet 的費用與 S3 相當，還要多付 EC2 與 EBS 的費用並自己處理擴展。
>
> **C ✗** Transfer Acceleration 在原本的傳出費之外另收加速費用，而且不快取內容，成本只會更高。
>
> **考點**：SAA-4.4｜以 CloudFront 降低重複內容的資料傳出成本｜延伸閱讀：第 11 章

### 第 48 題｜SAA｜選兩項｜D2 課程影片 bucket 的跨 Region 備援

教育平台的課程影片存放在 ap-northeast-1 的 S3 bucket，其中已有數百萬個既有物件。DR 計畫要求：另一個 Region 必須有完整副本，新上傳的物件 99.99% 要在 15 分鐘內複製完成並能監控複寫狀況，既有物件也必須複製過去。

哪兩項措施能滿足需求？

- A. 設定 S3 Same-Region Replication，把物件複製到同 Region 的另一個 bucket
- B. 在來源與目的 bucket 都啟用 versioning，設定 Cross-Region Replication 並啟用 S3 Replication Time Control（RTC）
- C. 設定 lifecycle rule，在物件建立 1 天後自動複製到另一個 Region 的 bucket
- D. 建立每天執行一次的 AWS DataSync task，把來源 bucket 同步到另一個 Region
- E. 使用 S3 Batch Replication 複製設定複寫規則之前就已存在的物件

> [!answer]- 答案：B、E
> **A ✗** Same-Region Replication 的副本仍在同一個 Region，Region 層級災難時一起受影響，不符合 DR 需求。
>
> **B ✓** CRR 要求來源與目的 bucket 都啟用 versioning。RTC 提供 SLA：99.99% 的新物件在 15 分鐘內完成複寫，並提供複寫延遲、待複寫量等指標與事件通知，可用於監控。
>
> **C ✗** Lifecycle rule 只能轉換儲存類別或刪除物件，不能把物件複製到其他 bucket。
>
> **D ✗** 每天一次的同步無法達到 15 分鐘的複寫目標。DataSync 適合一次性的大量搬遷或排程同步。
>
> **E ✓** 複寫規則只會處理設定之後新寫入的物件；既有物件要用 S3 Batch Replication 補複寫（也可以重試先前複寫失敗的物件）。
>
> **考點**：SAA-2.2｜CRR + RTC 達成有時間保證的跨 Region 副本，既有物件用 Batch Replication｜延伸閱讀：第 23 章

### 第 49 題｜SAA｜單選｜D1 學生沙盒帳號的護欄

大學的 AI 課程為每位學生建立一個獨立的 AWS 帳號，全部放在 Organizations 的 `Students` OU，學生在自己的帳號中擁有 AdministratorAccess。學校要求：學生不能啟動任何 GPU instance（p 與 g 系列），也不能在 ap-northeast-1 以外的 Region 建立資源；學生不能自行移除這些限制，而且管理負擔要最小。

哪個方案最合適？

- A. 在每個學生帳號的 IAM role 上附加一個 policy，拒絕 GPU instance type 與其他 Region 的操作
- B. 為每個學生帳號設定 AWS Budgets，花費超過門檻時寄信通知學生與助教
- C. 在 `Students` OU 附加 SCP：以 `ec2:InstanceType` 條件拒絕 p 與 g 系列的 `ec2:RunInstances`，並以 `aws:RequestedRegion` 拒絕 ap-northeast-1 以外的操作（排除全域服務）
- D. 在每個學生帳號中透過 Service Quotas 把 GPU instance 的 vCPU quota 設為最低，並請學生不要使用其他 Region

> [!answer]- 答案：C
> **C ✓** SCP 設定的是成員帳號中所有 principal（包含 root user）能使用的最大權限，學生即使是 Administrator 也無法修改附加在 OU 上的 SCP。附加在 OU 上，新加入的學生帳號自動繼承。Region 限制要排除 IAM、Organizations 等全域服務，避免誤擋。
>
> **A ✗** 學生擁有 AdministratorAccess，可以直接移除或修改自己帳號中的 IAM policy，限制形同虛設；逐帳號設定也增加管理負擔。
>
> **B ✗** Budgets 是事後通知，無法阻止學生啟動 GPU instance 或在其他 Region 建立資源。
>
> **D ✗** 學生有管理權限，可以自行申請提高 quota；而且 quota 是分 Region 的，「請學生不要使用」不是技術性控制。
>
> **考點**：SAA-1.1｜以 SCP 限制 instance type 與 Region 作為不可繞過的護欄｜延伸閱讀：第 14 章

### 第 50 題｜SAA｜單選｜D3 Lambda 尖峰時資料庫連線耗盡

新創 SaaS 的 API 由 Lambda 實作，尖峰時並行數會在幾秒內衝到 2,000，每個執行環境都會建立自己的 RDS for MySQL 連線。尖峰期間資料庫頻繁回應 too many connections 錯誤，CPU 與記憶體也因大量建立連線而升高。團隊希望以最少的程式修改解決。

哪個方案最合適？

- A. 在 Lambda 與資料庫之間建立 RDS Proxy，讓函式改連 proxy endpoint，由 proxy 管理連線池
- B. 把 DB instance 升級到更大的規格，並調高 `max_connections` 參數
- C. 建立兩個 read replica，並讓一半的 Lambda 函式改連 read replica
- D. 為函式設定 2,000 的 reserved concurrency，確保尖峰時連線數不會超過這個值

> [!answer]- 答案：A
> **A ✓** RDS Proxy 維護一組到資料庫的長期連線池，數千個 Lambda 執行環境的連線會被多工到少量的資料庫連線上，避免連線數暴增；它也能讓 failover 更快並支援 IAM 驗證。應用程式只要把連線端點換成 proxy endpoint。
>
> **B ✗** 每條連線都會占用資料庫記憶體，單純調高上限只會把問題推到更大的規格，成本上升且仍有上限。
>
> **C ✗** Read replica 只能分擔讀取，寫入仍要連 primary；每個執行環境依然各自建立連線，問題沒有解決。
>
> **D ✗** 2,000 的 reserved concurrency 仍允許 2,000 條連線，只是把現況固定下來。若把並行數壓得更低，又會造成 API throttling。
>
> **考點**：SAA-3.3｜Serverless 大量連線用 RDS Proxy 連線池｜延伸閱讀：第 26 章

### 第 51 題｜SAA｜單選｜D4 可重試的 CI 測試工作

開發者工具 SaaS 以 Amazon ECS on Fargate 執行客戶的 CI 測試工作，每個 task 執行 5 到 15 分鐘，失敗時平台會自動重新排程。工作量集中在平日白天，每天有數千個 task，夜間與週末很少。公司希望降低運算成本，但不想開始管理 EC2 instance。

哪個方案最合適？

- A. 改用 ECS 的 EC2 launch type，並為尖峰所需的 instance 購買 Reserved Instances
- B. 在 ECS cluster 使用 Fargate Spot capacity provider 執行測試 task，並以少量 Fargate 作為 base 容量
- C. 購買 3 年期、全額預付的 Compute Savings Plans，承諾金額等於白天尖峰的每小時 Fargate 花費
- D. 把測試工作改寫成 Lambda 函式，以每次呼叫計費取代 Fargate

> [!answer]- 答案：B
> **B ✓** Fargate Spot 使用 AWS 的閒置容量，價格比 Fargate 低許多，中斷前會有 2 分鐘的 SIGTERM 通知。CI 測試工作短、可重試，正適合 Spot；capacity provider strategy 可以設定少量一般 Fargate 作為 base，確保 Spot 容量不足時仍有基本處理能力。仍然不需要管理任何 EC2。
>
> **A ✗** EC2 launch type 需要管理 instance、修補與 cluster 容量，違反需求；以尖峰數量購買 RI，夜間與週末會大量閒置。
>
> **C ✗** Savings Plans 承諾的是每小時花費，以白天尖峰為準購買，夜間與週末的承諾金額都會浪費；它適合穩定的基礎負載。
>
> **D ✗** 15 分鐘的工作剛好碰到 Lambda 的最長執行時間上限，CI 環境（大量相依套件、Docker 建置）也不適合 Lambda，改寫成本高。
>
> **考點**：SAA-4.2｜可中斷的容器工作用 Fargate Spot｜延伸閱讀：第 21 章

### 第 52 題｜SAA｜選兩項｜D2 批次中的壞訊息拖垮推播

推播通知服務以 Lambda 消費 SQS standard queue，batch size 為 10。只要一批中有一則訊息處理失敗，整批訊息都會重新回到 queue，已經成功發送的通知又被重送一次。另外有少數格式錯誤的訊息永遠無法處理成功，不斷重試並占用處理能力。

哪兩項設定能解決這些問題？

- A. 在 event source mapping 啟用 `ReportBatchItemFailures`，讓函式只回報處理失敗的訊息 ID
- B. 把 batch size 改為 1，並把函式的 reserved concurrency 設為 1
- C. 為來源 queue 設定 redrive policy，指定 dead-letter queue 與適當的 maxReceiveCount
- D. 把 queue 的 visibility timeout 提高到最大值 12 小時
- E. 把 SQS queue 換成 SNS topic，讓 Lambda 直接訂閱並接收通知

> [!answer]- 答案：A、C
> **A ✓** 啟用 partial batch response 後，函式回傳失敗訊息的 ID，Lambda 只會讓這些訊息重新變為可見，成功處理的訊息會從 queue 刪除，不會再重送。
>
> **B ✗** 每次只處理一則、且只有一個並行，確實不會整批重試，但吞吐量會大幅下降，也沒有解決壞訊息不斷重試的問題。
>
> **C ✓** 訊息被接收超過 maxReceiveCount 次仍未成功時，SQS 會把它移到 dead-letter queue，壞訊息不再占用處理能力，之後可以分析或修正後重新導回（redrive）。
>
> **D ✗** 拉長 visibility timeout 只會讓失敗訊息更晚被重試，壞訊息仍然會無限重試，延遲還更嚴重。
>
> **E ✗** SNS 推送給 Lambda 是非同步呼叫，失去 queue 的緩衝與可控的重試機制，沒有解決問題。
>
> **考點**：SAA-2.1｜SQS + Lambda 的 partial batch response 與 DLQ｜延伸閱讀：第 32 章

### 第 53 題｜SAA｜單選｜D1 大型 DDoS 與專家支援

線上券商的交易網站架設在 CloudFront 與 ALB 之後，DNS 使用 Route 53，近半年多次遭到大規模 DDoS 攻擊。公司要求：攻擊期間能 24 小時聯繫 AWS 的 DDoS 應變專家協助、因攻擊造成的擴展費用能獲得補償，並取得進階的攻擊偵測與可視化指標。

哪個方案最符合需求？

- A. 訂閱 AWS Shield Advanced，保護 CloudFront distribution、Route 53 hosted zone 與 ALB，並設定 Shield Response Team 的存取權限
- B. 依賴預設啟用的 AWS Shield Standard，並在 CloudWatch 設定流量異常的 alarm
- C. 在 CloudFront 上掛 AWS WAF，設定 rate-based rule 限制每個 IP 的請求數
- D. 啟用 Amazon GuardDuty，偵測 DDoS 攻擊並自動通知 AWS Support 介入處理

> [!answer]- 答案：A
> **A ✓** Shield Advanced 提供 24 小時的 Shield Response Team（SRT）支援、DDoS 成本保護（攻擊造成的受保護資源擴展費用可申請抵免）、進階偵測與攻擊可視化，並包含受保護資源上 WAF 的使用權。保護範圍可以涵蓋 CloudFront、Route 53、ALB、Global Accelerator 與 Elastic IP。
>
> **B ✗** Shield Standard 自動防護常見的 L3／L4 攻擊且免費，但不提供 SRT、成本保護與進階指標。
>
> **C ✗** WAF rate-based rule 能處理部分 L7 攻擊，但沒有專家支援與成本保護，也不處理網路層攻擊。
>
> **D ✗** GuardDuty 是威脅偵測服務，不提供 DDoS 防護或應變支援。
>
> **考點**：SAA-1.2｜DDoS 專家支援與成本保護 → Shield Advanced｜延伸閱讀：第 16 章

### 第 54 題｜SAA｜單選｜D3 跨洲上傳大型考試錄影

線上認證考試平台要求考生在考試結束後上傳 1–2 GB 的監考錄影檔，檔案存到 us-east-1 的 S3 bucket。東南亞與南美的考生反映上傳速度很慢，網路不穩時整個檔案上傳失敗就要從頭開始。平台希望以最少的架構變更改善上傳速度與可靠性。

哪個方案最合適？

- A. 在東南亞與南美 Region 各建立一個 bucket，再以 Cross-Region Replication 把檔案複製回 us-east-1
- B. 在 bucket 上啟用 S3 Transfer Acceleration，並讓用戶端以 multipart upload 平行上傳多個 part
- C. 把 bucket 的預設儲存類別改成 S3 One Zone-IA，以縮短寫入確認時間
- D. 為主要考區建立 AWS Direct Connect 連線，讓考生經由專線上傳

> [!answer]- 答案：B
> **B ✓** Transfer Acceleration 讓考生先把資料送到最近的 CloudFront edge location，再經 AWS 骨幹網路傳到 bucket，大幅改善長距離上傳速度。Multipart upload 把大檔切成多個 part 平行上傳，某個 part 失敗只要重傳該 part，不必從頭開始。只需改用 accelerate endpoint，架構變更最少。
>
> **A ✗** 多 Region bucket 能拉近上傳距離，但要建立、管理多個 bucket 與複寫規則，應用程式還要依考生位置選 bucket，變更較大；也沒有解決失敗重傳的問題。
>
> **C ✗** 儲存類別不影響上傳的網路速度，One Zone-IA 還降低了資料韌性。
>
> **D ✗** Direct Connect 是企業機房與 AWS 之間的專線，考生分散在各地的家中，不可能使用。
>
> **考點**：SAA-3.1｜長距離大檔上傳用 Transfer Acceleration + multipart upload｜延伸閱讀：第 22 章

### 第 55 題｜SAA｜單選｜D4 大量冷檔案的共享檔案系統

文件管理 SaaS 把客戶附件存放在 20 TB 的 Amazon EFS 上，由多台 EC2 共同掛載。分析顯示約 80% 的檔案在建立 30 天後就很少被讀取，但偶爾仍會被開啟，而且應用程式要求檔案路徑不能改變、讀取時不需要任何額外步驟。公司希望降低儲存成本。

哪個方案最合適？

- A. 為檔案系統設定 EFS lifecycle management，把 30 天未存取的檔案移到 Infrequent Access 儲存類別，並設定在再次存取時移回 Standard
- B. 寫一個排程程式把 30 天未存取的檔案搬到 S3 Glacier Flexible Retrieval，並在 EFS 上留下指向 S3 的捷徑檔案
- C. 建立新的 EFS One Zone 檔案系統並把所有檔案搬過去，以較低的單價儲存
- D. 把檔案搬到 st1 EBS volume，再由其中一台 EC2 以 NFS 分享給其他 instance

> [!answer]- 答案：A
> **A ✓** EFS lifecycle management 依「多久沒有存取」自動把檔案移到 Infrequent Access（還可以再移到 Archive），檔案仍然在原本的路徑、對應用程式完全透明；可以設定第一次存取時移回 Standard。IA 的儲存單價遠低於 Standard，只在讀取時收取少量存取費，非常適合這種存取模式。
>
> **B ✗** 檔案路徑與讀取方式都改變了，Glacier Flexible Retrieval 的取回還需要數分鐘到數小時，不符合「讀取不需額外步驟」。
>
> **C ✗** One Zone 降低了單價，但資料只存在單一 AZ，韌性下降，而且冷熱資料仍以同一價格計費，節省幅度不如 lifecycle management。
>
> **D ✗** EBS volume 綁定單一 AZ，自己用 EC2 架 NFS 會形成單點故障並增加維運負擔。
>
> **考點**：SAA-4.1｜EFS lifecycle management 透明地降低冷檔案成本｜延伸閱讀：第 24 章

### 第 56 題｜SAA｜單選｜D2 線上考試資料庫的 AZ 容錯

線上考試系統使用單一 AZ 的 RDS for MySQL。上個月該 AZ 發生故障，正在進行的考試中斷了一個多小時。學校要求：AZ 故障時資料庫能在一到兩分鐘內自動恢復服務、不能遺失任何已確認的作答資料，且應用程式不需要修改連線設定。

哪個方案最合適？

- A. 在另一個 AZ 建立 read replica，AZ 故障時由維運人員手動 promote 並修改應用程式的連線字串
- B. 開啟 automated backups，AZ 故障時以 point-in-time restore 在另一個 AZ 建立新的 DB instance
- C. 把 DB instance 改為 Multi-AZ 部署，由 RDS 在另一個 AZ 維護同步複寫的 standby 並自動 failover
- D. 建立 Aurora Global Database，在另一個 Region 保留 secondary cluster 以應對故障

> [!answer]- 答案：C
> **C ✓** RDS Multi-AZ 以同步複寫把資料寫到另一個 AZ 的 standby，已確認的交易不會遺失。Primary 故障時 RDS 自動 failover，DNS endpoint 不變、指向新的 primary，通常在一到兩分鐘內完成，應用程式只需重新連線。（Multi-AZ DB cluster 的 failover 通常更快。）
>
> **A ✗** Read replica 是非同步複寫，可能遺失最後一批資料；手動 promote 與修改連線字串既慢又違反「不需要修改連線設定」。
>
> **B ✗** Point-in-time restore 要建立新的 instance，可能需要數十分鐘以上，且最近幾分鐘的交易可能遺失。
>
> **D ✗** Global Database 是跨 Region DR 方案，需要先遷移到 Aurora，對 AZ 層級的需求是過度設計；跨 Region 複寫是非同步的，也無法保證不遺失資料。
>
> **考點**：SAA-2.2｜AZ 容錯、零資料遺失用 RDS Multi-AZ｜延伸閱讀：第 26 章

### 第 57 題｜SAA｜單選｜D1 發卡機構的專屬硬體金鑰保管

發卡機構要在 AWS 上執行卡片資料的加解密與簽章，法規與內部政策要求：金鑰必須存放在單一租戶（single-tenant）、通過 FIPS 140 Level 3 驗證的 HSM 中，只有公司能控制金鑰，AWS 人員無法存取。既有的支付應用程式使用 PKCS#11 介面呼叫 HSM。

哪個方案最合適？

- A. 建立 AWS KMS customer managed key，並在 key policy 中只允許公司的 IAM role 使用
- B. 建立 AWS KMS customer managed key 並匯入公司自行產生的金鑰材料（BYOK）
- C. 把金鑰以 SecureString 形式存放在 AWS Secrets Manager，由應用程式取出後在記憶體中加解密
- D. 建立跨兩個 AZ 的 AWS CloudHSM cluster，由公司管理 HSM 使用者，應用程式透過 CloudHSM 的 PKCS#11 程式庫呼叫

> [!answer]- 答案：D
> **D ✓** CloudHSM 提供客戶專屬、單一租戶的 HSM（FIPS 140 Level 3 驗證：hsm1.medium 為 140-2、新一代 hsm2m.medium 為 140-3），HSM 使用者與金鑰完全由客戶管理，AWS 無法存取金鑰。它支援 PKCS#11、JCE、OpenSSL 等標準介面，既有應用程式可以沿用；cluster 跨 AZ 部署提供高可用。若同時想讓 S3 等服務以 KMS 方式使用這些金鑰，可以再設定 KMS custom key store。
>
> **A ✗** KMS 的 HSM 雖然也通過 FIPS 140-3 Level 3 驗證，但它是由 AWS 營運的多租戶服務，不符合「單一租戶」要求；KMS 也是以自己的 API 存取，不提供 PKCS#11 介面。
>
> **B ✗** BYOK 讓公司控制金鑰材料的來源，但金鑰仍存放在多租戶的 KMS 中，也仍然不支援 PKCS#11。
>
> **C ✗** Secrets Manager 是機密儲存服務而非 HSM，金鑰被取出到應用程式記憶體中使用，不符合「金鑰存放在 HSM 中」的要求。
>
> **考點**：SAA-1.3｜單一租戶 HSM 與標準密碼介面 → CloudHSM｜延伸閱讀：第 15 章

### 第 58 題｜SAA｜單選｜D2 遊戲大廳的 session 狀態

遊戲大廳的 web tier 由 Auto Scaling group 管理的 EC2 組成，玩家的登入 session 存在各台 instance 的記憶體中，並依賴 ALB 的 sticky session。每次 scale-in 或 instance 故障，部分玩家就會被登出，而且 sticky session 也讓各 instance 的負載不平均。團隊希望 web tier 變成 stateless，並讓 session 讀取維持次毫秒延遲。

哪個方案最合適？

- A. 把 ALB 的 sticky session 持續時間延長到 7 天，減少玩家被重新分配到其他 instance 的機會
- B. 把 session 寫入一個 EBS volume，並讓所有 web instance 共同掛載這個 volume
- C. 把 session 存放到 RDS for MySQL 的 session table，每次請求時讀取
- D. 把 session 存放到 Multi-AZ 的 Amazon ElastiCache（Redis OSS 或 Valkey）叢集並設定 TTL，然後關閉 ALB 的 sticky session

> [!answer]- 答案：D
> **D ✓** 把 session 移到外部的記憶體內資料庫後，任何一台 instance 都能處理任何玩家的請求，scale-in 或故障不再造成登出，ALB 也能平均分配負載。ElastiCache 提供次毫秒延遲，TTL 讓過期 session 自動清除，Multi-AZ 搭配自動 failover 避免快取節點成為單點。
>
> **A ✗** Session 仍然存在單台 instance 的記憶體，那台 instance 被終止時一樣會遺失，負載不均的問題反而更嚴重。
>
> **B ✗** 一般的 EBS volume 一次只能掛載在一台 instance 上（Multi-Attach 僅限 io1／io2、同一 AZ，且需要叢集檔案系統），不能當作共享的 session 儲存。
>
> **C ✗** 可以讓 web tier 變成 stateless，但每個請求都查詢關聯式資料庫，延遲以毫秒計且增加資料庫負載，達不到次毫秒的要求。流量不大、已有資料庫時，這是可接受的折衷。
>
> **考點**：SAA-2.1｜把 session 外部化到 ElastiCache 讓 web tier stateless｜延伸閱讀：第 28 章

### 第 59 題｜SAA｜單選｜D4 I/O 費用過高的 Aurora cluster

手機遊戲的 Aurora PostgreSQL cluster 承受大量寫入與隨機讀取，工作負載穩定。Cost Explorer 顯示這個 cluster 的費用中，I/O 請求費用約占 60%，instance 與儲存費用合計只占 40%。公司希望在不修改應用程式的情況下降低成本。

哪個做法最合適？

- A. 為 cluster 中的 instance 購買 Reserved Instances
- B. 新增兩個 Aurora Replicas，把讀取分散出去以降低每個 instance 的 I/O
- C. 把 cluster 中的 instance 改成 Aurora Serverless v2，依負載自動調整容量
- D. 把 cluster 的儲存設定從 Aurora Standard 改為 Aurora I/O-Optimized

> [!answer]- 答案：D
> **D ✓** Aurora I/O-Optimized 不再收取讀寫 I/O 費用，代價是 instance 與儲存的單價較高。AWS 的建議是：I/O 費用超過 Aurora 總費用約 25% 時，改用 I/O-Optimized 通常更省；這個 cluster 的 I/O 占 60%，節省會非常明顯，而且只是 cluster 層級的設定變更，不需要修改應用程式。
>
> **A ✗** Reserved Instances 只降低 instance 費用，占 60% 的 I/O 費用完全不受影響。
>
> **B ✗** Aurora 的 I/O 是以儲存層的請求計費，新增 replica 不會減少總 I/O 請求數，反而多付 instance 費用。
>
> **C ✗** Serverless v2 改變的是運算容量的計費方式；在 Aurora Standard 儲存設定下，I/O 仍然另外計費，問題沒有解決。
>
> **考點**：SAA-4.3｜I/O 密集的 Aurora 改用 I/O-Optimized｜延伸閱讀：第 26 章

### 第 60 題｜SAA｜選兩項｜D1 不使用資料庫密碼的連線方式

金融科技公司在 ECS on Fargate 上執行的服務，目前以環境變數中的密碼連線 RDS for MySQL。資安團隊要求完全不要使用資料庫密碼，改以 task 的 IAM role 驗證，並使用短效的驗證憑證連線。

哪兩項措施能達成需求？

- A. 把資料庫密碼移到 AWS Secrets Manager 並啟用自動輪替，由 task 啟動時讀取
- B. 在 DB instance 啟用 IAM database authentication，並建立以 `AWSAuthenticationPlugin` 驗證的資料庫使用者
- C. 建立 AWS Managed Microsoft AD，讓 RDS 加入網域並以 Kerberos 驗證 container
- D. 把 RDS 放到 public subnet，並以 security group 只允許 Fargate task 的 IP 連線
- E. 在 task role 的 policy 中授予該資料庫使用者的 `rds-db:connect` 權限，應用程式以 SDK 產生驗證 token 並以 TLS 連線

> [!answer]- 答案：B、E
> **A ✗** Secrets Manager 加自動輪替是很好的做法，但仍然是使用密碼，不符合「完全不要使用資料庫密碼」。沒有這個限制時，它往往是最通用的答案。
>
> **B ✓** IAM database authentication 要在 DB instance 上啟用，並在資料庫中建立以 `AWSAuthenticationPlugin` 驗證的使用者，資料庫才會接受 IAM 產生的 token。
>
> **C ✗** RDS for MySQL 確實支援搭配 AWS Managed Microsoft AD 的 Kerberos 驗證，但那是以 Active Directory 帳號驗證，不是題目要求的「以 task 的 IAM role 驗證」；Fargate task 也不會加入 AD 網域，要額外處理 keytab 或 AD 帳號密碼，等於又把長期憑證帶回來，複雜度也遠高於 IAM 驗證。公司已經以 AD 集中管理資料庫使用者、需要單一登入時，Kerberos 才是合適選擇。
>
> **D ✗** 把資料庫放到 public subnet 增加暴露面，而且和驗證方式無關，仍然需要密碼。
>
> **E ✓** Task role 需要 `rds-db:connect` 權限（Resource 為 `arn:aws:rds-db:<region>:<account>:dbuser:<DbiResourceId>/<db_user>`）。應用程式用 SDK 以 task role 的臨時憑證產生 token（有效期 15 分鐘），連線時以 token 取代密碼，且必須使用 TLS。
>
> **考點**：SAA-1.1、SAA-1.3｜RDS IAM database authentication 以 IAM role 取代密碼｜延伸閱讀：第 26 章

### 第 61 題｜SAA｜單選｜D2 RPO 24 小時的最低成本備援

補習班的線上學習系統由 EC2、Amazon EFS 與 RDS for MySQL 組成。DR 需求是：RTO 24 小時、RPO 24 小時，備份必須存放在另一個 Region，並且能集中設定與檢視所有資源的備份狀態。補習班希望成本越低越好。

哪個方案最合適？

- A. 在 DR Region 建立 RDS cross-Region read replica 與 EFS replication，應用程式層以 CloudFormation 預先定義、平時不運行
- B. 建立 AWS Backup backup plan，每天備份 EC2、EFS 與 RDS，並設定 copy rule 把 recovery point 複製到 DR Region 的 backup vault
- C. 為每個服務各寫一支排程 Lambda，分別建立 EBS snapshot、RDS snapshot 與 EFS 檔案複本，再各自複製到 DR Region
- D. 為所有資料啟用 S3 Cross-Region Replication，讓 EC2、EFS 與 RDS 的資料自動複寫到 DR Region

> [!answer]- 答案：B
> **B ✓** RPO／RTO 24 小時屬於 backup and restore 等級，是成本最低的 DR 策略。AWS Backup 以一個 backup plan 集中管理多種資源的排程、保留期間與跨 Region 複製，並提供統一的備份狀態檢視；災難時在 DR Region 從 recovery point 還原。
>
> **A ✗** Pilot light 的持續複寫能達到更短的 RPO，但要持續支付 replica 與複寫費用，對 24 小時的目標是多花錢。
>
> **C ✗** 自己寫多支 Lambda 也能做到，但沒有集中管理與狀態檢視，維護、錯誤處理與保留期間管理都要自己來。
>
> **D ✗** S3 CRR 只能複寫 S3 物件，EC2 的 EBS、EFS 與 RDS 的資料不在 S3 bucket 中，無法以 CRR 複寫。
>
> **考點**：SAA-2.2｜寬鬆 RPO／RTO 用 AWS Backup 跨 Region 複製（backup and restore）｜延伸閱讀：第 34 章

### 第 62 題｜SAA｜選兩項｜D4 NAT 與跨 AZ 傳輸費用

一家 SaaS 公司的 VPC 跨三個 AZ，private subnet 中的 EC2 平均分布在三個 AZ，所有 private subnet 共用一張 route table，預設路由指向位於 AZ-a 的唯一一台 NAT Gateway。這些 instance 大量讀寫 DynamoDB，也會呼叫外部的 SaaS API。帳單顯示 NAT Gateway 資料處理費與跨 AZ 資料傳輸費都很高。公司要在保留外部 API 連線的前提下降低成本。

哪兩項措施最合適？

- A. 把 private subnet 的預設路由改成指向 Internet Gateway，並為 instance 配置 public IP
- B. 為 DynamoDB 建立 interface VPC endpoint，讓 instance 透過 endpoint 的私有 IP 存取 DynamoDB
- C. 為 DynamoDB 建立 gateway VPC endpoint，並把它加到 private subnet 的 route table
- D. 在每個 AZ 的 public subnet 各建立一台 NAT Gateway，並讓每個 AZ 的 private subnet 使用各自的 route table 指向同 AZ 的 NAT Gateway
- E. 建立 Transit Gateway 與集中 egress VPC，讓所有對外流量經由 Transit Gateway 送往共用的 NAT Gateway

> [!answer]- 答案：C、D
> **A ✗** 讓 private instance 擁有 public IP 並直接面對 Internet，等於把它們變成 public subnet 中的機器，增加攻擊面，違反分層設計。
>
> **B ✗** DynamoDB 也支援 interface endpoint，但它按小時與處理量收費；只是要讓 VPC 內的 instance 存取 DynamoDB 時，免費的 gateway endpoint 更划算。需要從地端或其他 VPC 經私有 IP 存取 DynamoDB 時才用 interface endpoint。
>
> **C ✓** Gateway endpoint 讓 DynamoDB 流量不再經過 NAT Gateway，也不收 endpoint 費用，大量的 DynamoDB 讀寫就不再產生 NAT 處理費與跨 AZ 傳輸費。
>
> **D ✓** AZ-b 與 AZ-c 的流量原本要先跨 AZ 到 AZ-a 的 NAT Gateway，產生跨 AZ 傳輸費。每個 AZ 一台 NAT Gateway、各自路由後，流量留在同一個 AZ，同時消除單一 AZ 的故障點；多出的 NAT 小時費通常遠低於省下的跨 AZ 費用。
>
> **E ✗** 集中 egress 適合有許多 VPC 時統一管理出口，但會額外產生 Transit Gateway 的 attachment 與資料處理費；只有一個 VPC 時只會更貴。
>
> **考點**：SAA-4.4｜Gateway endpoint 與每 AZ 一台 NAT Gateway 降低網路費用｜延伸閱讀：第 5 章

### 第 63 題｜SAA｜選兩項｜D1 SSRF 竊取 instance 憑證的風險

金融科技公司的 web 應用程式跑在 EC2 上，最近收到弱點通報：應用程式有 server-side request forgery（SSRF）漏洞，攻擊者可以讓伺服器對 `169.254.169.254` 發出請求，取得 instance role 的臨時憑證。在程式修補完成之前，公司希望先從平台層降低風險與影響範圍。

哪兩項措施最合適？

- A. 移除 instance profile，改把一組 IAM user 的 access key 放在應用程式的環境變數中
- B. 把 instance 的 metadata 選項設為要求 IMDSv2（`HttpTokens=required`），並在 launch template 中套用相同設定
- C. 檢視 instance role 的權限，只保留應用程式實際需要的動作與資源
- D. 在 subnet 的 network ACL 加入拒絕連往 `169.254.169.254` 的出站規則
- E. 啟用 Amazon GuardDuty，由它自動阻擋對 instance metadata 的異常請求

> [!answer]- 答案：B、C
> **A ✗** 長期 access key 一旦外洩就持續有效，而且 SSRF 或其他漏洞也可能讀到環境變數，風險比臨時憑證更高。
>
> **B ✓** IMDSv2 要求先以 PUT 請求取得 session token，之後的 metadata 請求必須帶著 token；典型的 SSRF 只能讓伺服器發出單純的 GET 請求，無法完成這個流程，因此能大幅降低憑證被竊的風險。
>
> **C ✓** 即使憑證被竊，最小權限的 role 也能限制攻擊者能做的事，縮小影響範圍。
>
> **D ✗** Instance metadata 的流量不會經過 subnet 的 network ACL 或 security group 過濾，這條規則沒有作用。
>
> **E ✗** GuardDuty 能偵測憑證在 AWS 外部被使用等異常（例如 InstanceCredentialExfiltration finding），但它是偵測服務，不會阻擋對 metadata 的請求。
>
> **考點**：SAA-1.2｜IMDSv2 與最小權限 role 降低 SSRF 風險｜延伸閱讀：第 17 章

### 第 64 題｜SAA｜單選｜D2 流量無法預測的新創 API

兩名工程師組成的新創團隊要推出線上預約 SaaS，後端是簡單的 REST CRUD API，資料以預約 ID 為鍵、結構固定。上線後流量完全無法預測：夜間可能幾乎為零，被網紅介紹時可能瞬間暴增上千倍。團隊希望不用管理伺服器、能自動擴展，並且只為實際用量付費。

哪個架構最合適？

- A. ALB 搭配 Auto Scaling group 的 EC2，資料庫使用 RDS for MySQL Multi-AZ
- B. API Gateway HTTP API 搭配 Lambda，資料存放在 on-demand 模式的 DynamoDB table
- C. ALB 搭配 ECS on Fargate 的 service，資料庫使用 provisioned 的 Aurora MySQL
- D. 一台 Amazon Lightsail instance 執行 API 與資料庫，流量增加時再升級方案

> [!answer]- 答案：B
> **B ✓** API Gateway、Lambda 與 DynamoDB on-demand 全部是 serverless：不用管理伺服器，能在數秒內隨請求擴展，沒有流量時幾乎不產生運算費用，完全按請求數計費。以 ID 為鍵的固定結構資料很適合 DynamoDB。
>
> **A ✗** 需要管理 EC2 與 Auto Scaling 設定，擴展需要數分鐘，無法應付瞬間暴增；RDS 與最小數量的 instance 在零流量時也持續計費。
>
> **C ✗** Fargate 不用管理伺服器，但 task 與 provisioned Aurora 在沒有流量時仍持續計費，擴展速度也比 Lambda 慢。
>
> **D ✗** 單一 instance 是單點故障，無法自動擴展，升級方案需要人工操作且有停機時間。
>
> **考點**：SAA-2.1｜不可預測流量、按用量付費 → API Gateway + Lambda + DynamoDB on-demand｜延伸閱讀：第 20 章

### 第 65 題｜SAA｜單選｜D4 存取模式無法預測的租戶檔案

文件協作 SaaS 讓客戶上傳合約、設計稿等檔案到 S3，大部分物件大於 128 KB。各租戶的存取行為差異極大：有些檔案上傳後幾個月都沒人開啟，之後又突然被頻繁存取；團隊無法預測哪些檔案會變冷或變熱。公司希望降低儲存成本，不能因為存取冷檔案而產生取回費用或延遲，並且不想自行分析存取模式。

哪個方案最合適？

- A. 把物件的儲存類別設為 S3 Intelligent-Tiering，由 S3 依每個物件的存取情況自動在存取層之間移動
- B. 設定 lifecycle rule，在物件建立 30 天後轉到 S3 Standard-IA
- C. 設定 lifecycle rule，在物件建立 30 天後轉到 S3 One Zone-IA
- D. 設定 lifecycle rule，在物件建立 90 天後轉到 S3 Glacier Flexible Retrieval

> [!answer]- 答案：A
> **A ✓** Intelligent-Tiering 會監控每個物件的存取情況，30 天未存取就移到 Infrequent Access 層、90 天未存取移到 Archive Instant Access 層，一旦被存取就自動移回 Frequent Access 層。沒有取回費用，存取任何層級都是毫秒延遲，只收取少量的每物件監控費；大於 128 KB 的物件才會被自動分層，正適合這個情境。
>
> **B ✗** Standard-IA 每次讀取都收取取回費用；檔案重新變熱時仍停留在 IA，頻繁存取的取回費可能超過省下的儲存費。存取模式可預測、確定會長期變冷時才適合。
>
> **C ✗** 除了與 Standard-IA 相同的取回費問題，One Zone-IA 只存放在單一 AZ，不適合客戶上傳的唯一副本。
>
> **D ✗** Glacier Flexible Retrieval 取回需要數分鐘到數小時，還有取回費用，違反「不能產生延遲」。
>
> **考點**：SAA-4.1｜存取模式無法預測 → S3 Intelligent-Tiering｜延伸閱讀：第 23 章

## 答案速查與 Domain 分析

| 題號 | 答案 | Domain | Task | 相關章節 |
|---|---|---|---|---|
| 1 | B | D1 | SAA-1.1 | 第 13 章 |
| 2 | C | D3 | SAA-3.4 | 第 11 章 |
| 3 | A | D2 | SAA-2.1 | 第 32 章 |
| 4 | D | D1 | SAA-1.3 | 第 16 章 |
| 5 | B | D3 | SAA-3.2 | 第 19 章 |
| 6 | A | D4 | SAA-4.4 | 第 6 章 |
| 7 | B、D | D1 | SAA-1.2 | 第 6 章 |
| 8 | C | D2 | SAA-2.2 | 第 26 章 |
| 9 | D | D3 | SAA-3.5 | 第 31 章 |
| 10 | A | D1 | SAA-1.1 | 第 13 章 |
| 11 | B | D4 | SAA-4.2 | 第 39 章 |
| 12 | D | D2 | SAA-2.1 | 第 33 章 |
| 13 | C | D1 | SAA-1.2 | 第 16 章 |
| 14 | A | D3 | SAA-3.3 | 第 26 章 |
| 15 | A、E | D2 | SAA-2.2 | 第 18 章 |
| 16 | C | D4 | SAA-4.1 | 第 23 章 |
| 17 | B | D1 | SAA-1.3 | 第 15 章 |
| 18 | D | D3 | SAA-3.1 | 第 24 章 |
| 19 | A | D2 | SAA-2.1 | 第 32 章 |
| 20 | C | D1 | SAA-1.1 | 第 13 章 |
| 21 | D | D4 | SAA-4.3 | 第 26 章 |
| 22 | B | D3 | SAA-3.4 | 第 11 章 |
| 23 | A | D1 | SAA-1.2 | 第 16 章 |
| 24 | B | D2 | SAA-2.2 | 第 34 章 |
| 25 | C | D3 | SAA-3.5 | 第 25 章 |
| 26 | A、D | D1 | SAA-1.3、SAA-4.1 | 第 23 章 |
| 27 | C | D2 | SAA-2.1 | 第 32 章 |
| 28 | D | D3 | SAA-3.3 | 第 27 章 |
| 29 | A | D4 | SAA-4.2 | 第 39 章 |
| 30 | B | D1 | SAA-1.1 | 第 13 章 |
| 31 | A | D3 | SAA-3.2 | 第 19 章 |
| 32 | D | D2 | SAA-2.2 | 第 9 章 |
| 33 | D | D1 | SAA-1.2 | 第 6 章 |
| 34 | C | D3 | SAA-3.4 | 第 7 章 |
| 35 | B、C | D4 | SAA-4.1 | 第 23 章 |
| 36 | B | D2 | SAA-2.1 | 第 21 章 |
| 37 | A | D1 | SAA-1.3 | 第 26 章 |
| 38 | C、E | D3 | SAA-3.5 | 第 31 章 |
| 39 | A、D | D1 | SAA-1.1 | 第 12 章 |
| 40 | C | D4 | SAA-4.3 | 第 27 章 |
| 41 | A | D2 | SAA-2.2 | 第 27 章 |
| 42 | B | D1 | SAA-1.2 | 第 16 章 |
| 43 | C | D3 | SAA-3.1 | 第 24 章 |
| 44 | C | D2 | SAA-2.1 | 第 32 章 |
| 45 | D | D1 | SAA-1.3 | 第 24 章 |
| 46 | B | D3 | SAA-3.2 | 第 17 章 |
| 47 | D | D4 | SAA-4.4 | 第 11 章 |
| 48 | B、E | D2 | SAA-2.2 | 第 23 章 |
| 49 | C | D1 | SAA-1.1 | 第 14 章 |
| 50 | A | D3 | SAA-3.3 | 第 26 章 |
| 51 | B | D4 | SAA-4.2 | 第 21 章 |
| 52 | A、C | D2 | SAA-2.1 | 第 32 章 |
| 53 | A | D1 | SAA-1.2 | 第 16 章 |
| 54 | B | D3 | SAA-3.1 | 第 22 章 |
| 55 | A | D4 | SAA-4.1 | 第 24 章 |
| 56 | C | D2 | SAA-2.2 | 第 26 章 |
| 57 | D | D1 | SAA-1.3 | 第 15 章 |
| 58 | D | D2 | SAA-2.1 | 第 28 章 |
| 59 | D | D4 | SAA-4.3 | 第 26 章 |
| 60 | B、E | D1 | SAA-1.1、SAA-1.3 | 第 26 章 |
| 61 | B | D2 | SAA-2.2 | 第 34 章 |
| 62 | C、D | D4 | SAA-4.4 | 第 5 章 |
| 63 | B、C | D1 | SAA-1.2 | 第 17 章 |
| 64 | B | D2 | SAA-2.1 | 第 20 章 |
| 65 | A | D4 | SAA-4.1 | 第 23 章 |

### 各 domain 題數

| Domain | 名稱 | 題數 | 官方比重 | Task 分布 |
|---|---|---|---|---|
| D1 | Design Secure Architectures | 20 | 30% | SAA-1.1×7、SAA-1.2×7、SAA-1.3×7、SAA-4.1×1 |
| D2 | Design Resilient Architectures | 17 | 26% | SAA-2.1×9、SAA-2.2×8 |
| D3 | Design High-Performing Architectures | 15 | 24% | SAA-3.1×3、SAA-3.2×3、SAA-3.3×3、SAA-3.4×3、SAA-3.5×3 |
| D4 | Design Cost-Optimized Architectures | 13 | 20% | SAA-4.1×4、SAA-4.2×3、SAA-4.3×3、SAA-4.4×3 |

（第 26、60 題同時標了兩個 task，所以 task 次數加總略多於題數。）

### 錯題對應複習章節

先算出每個 domain 的答對率。低於 70% 的 domain，依下表回到對應章節，重讀「考試這樣考」與「本章重點整理」，再重做該章練習題。

| Domain | 答錯時優先複習 |
|---|---|
| D1 | IAM 與 policy 評估、permissions boundary 看第 12 章；跨帳號、Identity Center、Cognito、Roles Anywhere 看第 13 章；SCP 看第 14 章；KMS、CloudHSM 看第 15 章；WAF、Shield、GuardDuty、Inspector、Macie 看第 16 章；security group 與 VPC endpoint 看第 6 章。 |
| D2 | SQS、SNS、EventBridge 看第 32 章；Step Functions 看第 33 章；Multi-AZ、DR 策略與 AWS Backup 看第 34 章；Aurora 與 RDS 高可用看第 26 章；DynamoDB global tables 看第 27 章；Auto Scaling 與 static stability 看第 18 章；Route 53 failover 看第 9 章。 |
| D3 | Lambda 效能看第 19 章；placement group 看第 17 章；EBS、FSx 看第 24 章；DynamoDB 分割與 RDS Proxy 看第 27、26 章；CloudFront、Global Accelerator 看第 11 章；Transit Gateway 看第 7 章；Kinesis、Firehose 看第 31 章；Transfer Family 看第 25 章。 |
| D4 | S3 儲存類別與 lifecycle 看第 23 章；EFS 成本看第 24 章；Spot、Savings Plans 看第 39 章；Fargate Spot 看第 21 章；Aurora 與 DynamoDB 計價看第 26、27 章；NAT、endpoint 與 CloudFront 的網路費用看第 5、6、11 章。 |

> [!tip] 考試提示
> 答錯的題目不要只看正確答案。回頭重讀你選的那個錯誤選項的解析，找出它「錯在哪一個關鍵點」，並寫下「題目若改成什麼條件，這個選項就會變成正確答案」。這是提升實戰答對率最有效的方法。
