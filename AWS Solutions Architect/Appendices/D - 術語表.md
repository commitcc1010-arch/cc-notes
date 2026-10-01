---
title: 術語表
---

# 附錄 D　術語表

本附錄收錄全書正文中定義過的重要術語，共 731 條，依英文字母 A–Z 排列；以數字開頭的放在最前面，沒有固定英文名稱的解題概念放在最後一節「中文術語」。每一條包含四欄：

- **英文術語**：AWS 服務名稱省略 Amazon／AWS 前綴排序（例如 Amazon S3 放在 S、AWS Lambda 放在 L），括號內是完整名稱或縮寫。
- **中文**：常見的中文譯名或白話說明。服務名稱在考試與官方文件中都使用英文，中文只是幫助理解，不必背。
- **一句話定義**：與正文的定義一致；需要比較或細節時，回到首次說明的章節。
- **首次說明**：這個術語第一次以粗體定義的章。若該章只是先簡短介紹、完整說明在後面的章，會寫成「第 2 章（詳見第 17 章）」。

使用方式：讀到後面章節時忘記某個名詞，先查這裡的一句話定義；若定義看不懂，代表前置章節需要重讀。服務的選型比較請看附錄 A，數字與限制看附錄 B，題目關鍵字看附錄 C。

> [!warning] 服務現況
> 部分服務已停止、進入維護模式或不再開放新客戶（例如 QLDB、App Runner、S3 Select、Snowball Edge、Migration Hub 與 Application Discovery Service、Audit Manager 的新帳號設定、Timestream for LiveAnalytics）。本表在定義中註明現況；考題仍可能出現這些名稱，但新設計不應把它們當成推薦方案。

**索引**：0–9｜A｜B｜C｜D｜E｜F｜G｜H｜I｜J｜K｜L｜M｜N｜O｜P｜Q｜R｜S｜T｜U｜V｜W｜X｜Z｜中文術語

## 0–9

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| 7Rs | 七種遷移策略 | Retire、Retain、Relocate、Rehost、Replatform、Repurchase、Refactor 七種處理既有應用程式的方式，遷移評估時逐一分類每個 workload。 | 第 44 章 |

## A

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| ABAC（Attribute-Based Access Control） | 以屬性為基礎的存取控制 | 比對 principal 與資源上的 tag 是否相符來授權，新增資源或團隊時不必修改 policy。 | 第 12 章 |
| Access key | 存取金鑰 | IAM user 或 root user 的長期程式化憑證（access key ID 加 secret access key），外洩風險高，應盡量改用 role 的臨時憑證。 | 第 2 章（詳見第 12 章） |
| Access point（S3 Access Point） | 存取點 | 為同一個 bucket 建立多個各有獨立 policy 與網路來源限制的存取入口，簡化大量使用者共用 bucket 的權限管理。 | 第 22 章 |
| Account Factory | 帳號工廠 | Control Tower 以標準範本自動建立、設定並納管新 AWS 帳號的功能。 | 第 14 章 |
| Account Factory for Terraform（AFT） | Terraform 帳號工廠 | 以 Terraform pipeline 透過 Control Tower 申請帳號並套用自訂 baseline 的做法。 | 第 14 章（詳見第 40 章） |
| ACID | 交易四特性 | 關聯式交易的四個保證：原子性（全做或全不做）、一致性、隔離性、持久性。 | 第 4 章 |
| ACM（AWS Certificate Manager） | 憑證管理服務 | 申請、匯入與自動續約 TLS 憑證的服務；給 CloudFront 用的憑證必須在 us-east-1。 | 第 3 章（詳見第 15 章） |
| Active Directory（AD） | 微軟目錄服務 | Microsoft 的企業目錄服務，存放使用者、群組與電腦帳號，常是企業身份的來源。 | 第 13 章 |
| Active-passive | 主備架構 | 平時只有主站點承接流量，主站點故障時才切到備援站點的部署方式。 | 第 9 章（詳見第 34 章） |
| ACU（Aurora Capacity Unit） | Aurora 容量單位 | Aurora Serverless v2 計量容量的單位，每個 ACU 約等於 2 GiB 記憶體與對應的 CPU、網路能力。 | 第 26 章 |
| Adaptive capacity | 自適應容量 | DynamoDB 自動把 table 的容量優先分給較熱的 partition，緩解存取不均造成的 throttling。 | 第 27 章 |
| AD Connector | AD 連接器 | 把 AWS 服務的目錄請求代理轉送到地端 Active Directory 的 proxy，雲端不存放目錄資料。 | 第 13 章 |
| ADOT（AWS Distro for OpenTelemetry） | AWS OpenTelemetry 發行版 | AWS 支援的 OpenTelemetry 發行版，用一套 SDK 與 collector 把 trace、metric 送到 X-Ray、CloudWatch 等後端。 | 第 36 章 |
| Agent（AI agent） | 代理 | 由模型依指示自行規劃步驟、呼叫工具並根據結果決定下一步的應用程式。 | 第 47 章 |
| AgentCore（Amazon Bedrock AgentCore） | AI agent 營運平台 | 部署與營運 AI agent 的受管元件集合，包含 Runtime、Gateway、Identity、Memory、Observability 等。 | 第 47 章 |
| Aggregator（AWS Config aggregator） | 匯總器 | 把多帳號、多 Region 的 AWS Config 設定與合規資料集中到一個帳號檢視。 | 第 16 章 |
| Alarm（CloudWatch alarm） | 告警 | 監看一個 metric 或運算式，狀態在 OK、ALARM、INSUFFICIENT_DATA 之間轉換並觸發動作。 | 第 36 章 |
| ALB（Application Load Balancer） | 應用程式負載平衡器 | L7 load balancer，依 path、host、header 等條件把 HTTP／HTTPS 請求路由到不同 target group。 | 第 5 章（詳見第 10 章） |
| Alias（KMS alias） | 金鑰別名 | 指向 KMS key 的易讀名稱，程式用 alias 呼叫就能在不改程式的情況下換金鑰。 | 第 15 章 |
| Alias（Lambda alias） | Lambda 別名 | 指向特定 Lambda version 的固定名稱，可設定兩個版本的流量權重來做 canary。 | 第 37 章 |
| Alias record | 別名記錄 | Route 53 特有的記錄類型，可直接指向 ELB、CloudFront、S3 等 AWS 資源，且能放在 zone apex。 | 第 3 章（詳見第 9 章） |
| All-at-once deployment | 一次全部部署 | 同時更新所有 instance，速度最快但更新期間服務會中斷、回滾也最慢。 | 第 21 章（詳見第 37 章） |
| Allocation strategy | 配置策略 | EC2 Fleet、Spot Fleet 或 ASG 選擇 Spot capacity pool 的方式，一般建議 price-capacity-optimized。 | 第 17 章 |
| Amazon MQ | 受管訊息代理 | 受管的 ActiveMQ 與 RabbitMQ message broker，適合已使用 JMS、AMQP、MQTT 等標準協定的既有應用程式。 | 第 32 章 |
| AMI（Amazon Machine Image） | 機器映像 | 啟動 EC2 的範本，包含 root volume snapshot、block device mapping 與 launch 權限；AMI 是 Regional 資源。 | 第 2 章（詳見第 17 章） |
| Anomaly detection | 異常偵測 | CloudWatch 依 metric 歷史資料建立預期區間，超出區間就觸發 alarm，適合有週期性的指標。 | 第 36 章 |
| Anti-corruption layer | 防腐層 | 新舊系統之間的轉換層，把舊系統的資料模型翻譯成新服務的模型，避免舊設計滲入新系統。 | 第 46 章 |
| Anycast | 任播 | 同一個 IP 位址在多個地點同時宣告，使用者自動連到網路上最近的節點；Global Accelerator 以此提供固定入口。 | 第 11 章 |
| API Gateway（Amazon API Gateway） | API 閘道 | 受管的 API 前門，提供 REST、HTTP、WebSocket 三種 API，內建驗證、節流、快取與多種後端整合。 | 第 19 章（詳見第 20 章） |
| API key（API Gateway） | API 金鑰 | API Gateway 用來識別呼叫端並套用 usage plan 的字串；它不是授權機制，不能單獨用來保護 API。 | 第 20 章 |
| AppConfig（AWS AppConfig） | 設定與功能旗標服務 | 受管的設定與 feature flag 發佈服務，可分階段推出並在 CloudWatch alarm 觸發時自動回滾。 | 第 35 章（詳見第 37 章） |
| Appliance mode | 設備模式 | Transit Gateway VPC attachment 的設定，讓同一條連線的去回程都走同一個 AZ 的檢查設備，避免 stateful 防火牆斷線。 | 第 7 章 |
| Application Auto Scaling | 應用程式自動擴展 | 替 EC2 以外的資源（ECS service、DynamoDB、Aurora replica、Lambda provisioned concurrency 等）做自動擴展的服務。 | 第 18 章 |
| Application Discovery Service（ADS） | 應用程式探索服務 | 收集地端伺服器規格、效能與網路相依資料以供遷移評估；自 2025-11-07 起不再開放新客戶。 | 第 44 章 |
| Application Migration Service（MGN） | 應用程式遷移服務 | 以區塊層持續複寫把地端或其他雲的伺服器 rehost 到 EC2，支援測試啟動與 cutover。 | 第 25 章（詳見第 45 章） |
| Application Recovery Controller（ARC） | 應用程式復原控制器 | Route 53 的復原控制服務，提供 routing control、readiness check、zonal shift 與 Region switch，讓 failover 不依賴 control plane。 | 第 9 章（詳見第 34 章） |
| App Runner（AWS App Runner） | 受管容器 web 服務 | 從原始碼或 container image 直接部署 web 服務的受管平台；已對新客戶關閉，不應當成新方案。 | 第 21 章 |
| AppSync（AWS AppSync） | 受管 GraphQL 服務 | 受管 GraphQL API 服務，可整合多種資料來源並支援即時 subscription。 | 第 20 章 |
| ARN（Amazon Resource Name） | Amazon 資源名稱 | AWS 資源的唯一識別字串，格式包含 partition、服務、Region、帳號與資源路徑。 | 第 2 章 |
| Artifact（AWS Artifact） | 合規報告入口 | 下載 AWS 自身合規報告（如 SOC、ISO）與簽署合規協議的入口。 | 第 16 章 |
| ASN（Autonomous System Number） | 自治系統編號 | BGP 中識別一個獨立路由網域的編號，VPN 與 DX 兩端各自有 ASN。 | 第 8 章 |
| Athena（Amazon Athena） | 互動式 SQL 查詢服務 | 用標準 SQL 直接查詢 S3 上資料的 serverless 服務，依掃描資料量計費。 | 第 22 章（詳見第 30 章） |
| At-least-once delivery | 至少一次投遞 | 保證訊息一定送達，但可能重複送出，所以 consumer 必須冪等。 | 第 22 章（詳見第 33 章） |
| At-most-once | 最多一次 | 訊息不重送，可能遺失但不會重複的投遞語意。 | 第 33 章 |
| Attachment（Transit Gateway attachment） | 附加連線 | 把 VPC、VPN、Direct Connect gateway 或另一個 TGW 接上 Transit Gateway 的連接點。 | 第 7 章 |
| Audit Manager（AWS Audit Manager） | 稽核證據管理 | 自動蒐集稽核證據並對應到法規框架；已進入維護模式，2026-04-30 起新帳號無法設定。 | 第 16 章 |
| Aurora（Amazon Aurora） | 雲端原生關聯式資料庫 | AWS 自研、相容 MySQL 與 PostgreSQL 的關聯式資料庫，儲存層 6 份副本跨 3 個 AZ。 | 第 4 章（詳見第 26 章） |
| Aurora cloning | Aurora 複製 | 以 copy-on-write 快速建立與來源共用儲存頁的新 cluster，只有被修改的頁才另外占空間。 | 第 26 章 |
| Aurora DSQL | 分散式 SQL 資料庫 | AWS 較新的 serverless 分散式 SQL 服務，multi-Region 叢集的各 Region endpoint 都可讀寫並維持強一致；PostgreSQL 相容程度需逐項驗證。 | 第 26 章（詳見第 42 章） |
| Aurora Global Database | Aurora 全域資料庫 | 以儲存層複寫把 Aurora 複製到其他 Region，RPO 通常為秒級，可做 switchover 或 failover。 | 第 26 章 |
| Aurora I/O-Optimized | Aurora I/O 最佳化 | Aurora 的儲存計價設定：I/O 不另外收費、儲存與運算單價較高，適合 I/O 費用占比高的負載。 | 第 26 章 |
| Aurora Replica | Aurora 唯讀副本 | 共用同一個 cluster volume 的唯讀 instance，最多 15 個，也是 failover 的目標。 | 第 26 章 |
| Aurora Serverless v2 | Aurora 無伺服器第 2 版 | 依負載以 ACU 為單位細粒度自動調整容量的 Aurora instance class。 | 第 26 章 |
| Authentication／Authorization | 驗證／授權 | 驗證確認「你是誰」，授權決定「你可以做什麼」；IAM 兩者都處理。 | 第 12 章 |
| Auto Scaling group（ASG） | 自動擴展群組 | 一組依 min、max、desired 維持數量的 EC2，可跨 AZ 分布、自動替換不健康 instance 並依政策擴縮。 | 第 18 章 |
| Availability | 可用性 | 系統能正常提供服務的時間比例，常以幾個 9 表示。 | 第 4 章 |
| Availability Zone（AZ） | 可用區域 | Region 內一個或多個具備獨立電力、網路與冷卻的資料中心群，AZ 之間以低延遲網路相連。 | 第 2 章 |
| AWS managed key | AWS 代管金鑰 | AWS 服務代你在帳號中建立的 KMS key（如 aws/s3、aws/rds），key policy 不能修改。 | 第 15 章 |
| AWS owned key | AWS 擁有金鑰 | AWS 擁有並跨多個帳號使用的金鑰，你看不到也無法管理，是許多服務的預設加密方式。 | 第 15 章 |
| AZ ID | 可用區域 ID | 跨帳號一致的實體 AZ 識別碼（例如 use1-az1）；不同帳號的同名 AZ 可能對應不同的實體 AZ。 | 第 2 章 |

## B

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Backpressure | 背壓 | 下游處理不及時把壓力回傳給上游，讓上游放慢或排隊，避免整個系統被壓垮。 | 第 19 章 |
| Backtrack | 回溯 | Aurora MySQL 把資料庫原地倒回過去某個時間點的功能，不需要還原成新的 cluster。 | 第 26 章 |
| Backup Audit Manager（AWS Backup Audit Manager） | 備份稽核管理 | 以 framework 與 control 持續檢查資源是否有備份、保存期限與跨 Region copy 是否合規，並產生稽核報告。 | 第 34 章（詳見第 43 章） |
| Backup（AWS Backup） | 集中備份服務 | 集中管理多種服務備份的服務，提供 backup plan、vault、跨 Region 與跨帳號複製及還原測試。 | 第 24 章（詳見第 34 章） |
| Backup plan | 備份計畫 | AWS Backup 中定義備份頻率、保留期限、lifecycle 與複製目的地的規則集合。 | 第 34 章 |
| Backup policy | 備份政策 | 在 Organizations 層級統一下發 AWS Backup plan 到成員帳號的政策類型。 | 第 34 章（詳見第 43 章） |
| Backup vault | 備份保管庫 | AWS Backup 存放 recovery point 的容器，可用 access policy 與 Vault Lock 保護。 | 第 34 章 |
| Backup Vault Lock（AWS Backup Vault Lock） | 備份保管庫鎖定 | 把 backup vault 鎖成 WORM，recovery point 在保留期內不能被刪除或縮短保留，連 root user 也不行（compliance mode）。 | 第 16 章（詳見第 34 章） |
| Bandwidth | 頻寬 | 單位時間內一條連線最多能傳送的資料量，與延遲是兩回事。 | 第 3 章 |
| Bastion host | 跳板機 | 放在 public subnet、供管理者 SSH 進入 private 機器的 instance；可由 Session Manager 取代。 | 第 38 章 |
| Batch（AWS Batch） | 批次運算服務 | 受管的批次運算排程服務，依 job queue 自動配置 compute environment 執行容器化工作。 | 第 21 章 |
| Batch Operations（S3 Batch Operations） | S3 批次作業 | 對數十億個 object 大量執行複製、加標籤、還原、呼叫 Lambda 等操作，並產出完成報告。 | 第 23 章 |
| Batch Replication（S3 Batch Replication） | S3 批次複寫 | 補複寫既有 object 或先前複寫失敗的 object；一般 replication 規則只處理設定後的新寫入。 | 第 23 章 |
| Batch transform | 批次轉換推論 | SageMaker AI 對一整批資料做離線推論，完成後就釋放資源，不需要常駐 endpoint。 | 第 47 章 |
| Bedrock Agents（Amazon Bedrock Agents） | Bedrock 代理 | 讓模型依指示規劃步驟、呼叫 action group 與 knowledge base 完成多步驟任務的功能。 | 第 47 章 |
| Bedrock（Amazon Bedrock） | 生成式 AI 模型服務 | 以 API 使用多家 foundation model 的受管生成式 AI 服務，另提供 knowledge bases、agents、guardrails 等功能。 | 第 47 章 |
| Bedrock Guardrails（Amazon Bedrock Guardrails） | Bedrock 防護機制 | 對模型輸入與輸出套用內容過濾、禁止主題、敏感資訊遮蔽與 contextual grounding 檢查的防護機制。 | 第 47 章 |
| Bedrock Knowledge Bases（Amazon Bedrock Knowledge Bases） | Bedrock 知識庫 | 受管 RAG 功能：把文件切塊、產生 embedding、存入向量資料庫，查詢時檢索相關片段給模型。 | 第 47 章 |
| BFD（Bidirectional Forwarding Detection） | 雙向轉送偵測 | 以極短間隔的心跳偵測鏈路故障，讓 BGP 比預設計時器更快切換路徑。 | 第 8 章 |
| BGP（Border Gateway Protocol） | 邊界閘道協定 | 路由器之間交換路由資訊的協定，Site-to-Site VPN 與 Direct Connect 用它動態學習對方的 prefix。 | 第 8 章 |
| Billing Conductor（AWS Billing Conductor） | 帳單指揮 | 以 billing group、pricing rules 與 custom line items 產生各群組的 pro forma 帳單，用於 showback、chargeback 或轉售。 | 第 39 章 |
| Blast radius | 爆炸半徑 | 一次故障、錯誤設定或資安事件會波及的範圍；多帳號、cell 與分批部署都在縮小它。 | 第 35 章 |
| Block Public Access（S3 Block Public Access） | 封鎖公開存取 | 帳號、bucket 與 access point 層級阻擋公開存取的設定，新建 bucket 預設全部啟用。 | 第 22 章 |
| Block storage | 區塊儲存 | 以固定大小區塊讀寫、像本機硬碟一樣被作業系統格式化使用的儲存，例如 EBS。 | 第 4 章 |
| Blue/green deployment | 藍綠部署 | 先建立完整的新版本環境，驗證後一次把流量切過去，舊環境保留以便快速回切。 | 第 18 章（詳見第 37 章） |
| Blue/Green Deployments（RDS） | RDS 藍綠部署 | RDS 與 Aurora 建立持續同步的 green 環境，升級驗證後切換，green 接手 blue 原本的名稱與 endpoint。 | 第 26 章 |
| Break-glass | 緊急存取 | 預先準備、嚴格監控、只在正常登入方式失效時才使用的緊急高權限存取流程。 | 第 13 章（詳見第 40 章） |
| Bridge model | 橋接模型 | 多租戶 SaaS 中部分層級 silo、部分層級 pool 的混合隔離模型。 | 第 49 章 |
| Bucket | 儲存桶 | S3 存放 object 的容器，名稱在全球唯一，建立在特定 Region。 | 第 2 章（詳見第 22 章） |
| Bucket Key（S3 Bucket Key） | bucket 金鑰 | 以 bucket 層級的中介金鑰產生 data key，大幅減少 SSE-KMS 對 KMS 的請求次數與費用。 | 第 15 章 |
| Bucket owner enforced | 強制 bucket 擁有者 | S3 Object Ownership 設定：停用 ACL，bucket 擁有者自動擁有所有 object；新建 bucket 的預設值。 | 第 22 章 |
| Bucket policy | bucket 政策 | 附加在 S3 bucket 上的 resource-based policy，可授權其他帳號或加上網路、加密等條件。 | 第 12 章（詳見第 22 章） |
| Budget actions | 預算動作 | 預算超過門檻時自動套用 IAM policy、SCP 或停止特定 EC2／RDS instance 的動作。 | 第 39 章 |
| Budgets（AWS Budgets） | 預算 | 設定成本或用量預算並在超過門檻時通知，搭配 budget actions 可自動套用限制。 | 第 2 章（詳見第 39 章） |
| Bulkhead | 隔艙 | 把資源（連線池、執行緒、並行數）分隔給不同功能，一部分耗盡時不會拖垮其他部分。 | 第 33 章 |
| Burstable performance instance | 可爆發效能 instance | T 系列 instance：平時以 baseline 效能運作，累積 CPU credits 供短暫尖峰使用。 | 第 17 章 |
| Burst capacity | 爆發容量 | DynamoDB provisioned 模式保留最多約 5 分鐘未用完的容量，用來吸收短暫尖峰。 | 第 27 章 |
| BYOK（Bring Your Own Key） | 自帶金鑰 | 把自己在 KMS 之外產生的金鑰材料匯入 KMS key，由你負責保存與到期管理。 | 第 15 章 |
| BYOL（Bring Your Own License） | 自帶授權 | 把既有的軟體授權帶到 AWS 使用，常需 Dedicated Hosts 才符合授權條款。 | 第 17 章 |

## C

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Cache-aside（lazy loading） | 旁路快取 | 應用程式先查 cache，miss 時讀資料庫並把結果寫回 cache；只快取真正被讀到的資料。 | 第 28 章 |
| Cache behavior | 快取行為 | CloudFront 依 path pattern 決定請求要送往哪個 origin、用哪些快取與存取設定。 | 第 11 章 |
| Cache hit／Cache miss | 快取命中／未命中 | 請求在快取中找到資料稱為 hit，找不到而必須回源稱為 miss。 | 第 11 章（詳見第 28 章） |
| Cache key | 快取鍵 | 決定兩個請求是否共用同一份快取的元素組合（URL、header、cookie、query string）；放入越多元素命中率越低。 | 第 11 章 |
| Cache policy | 快取政策 | CloudFront 中定義 cache key 內容與 TTL 的設定；要轉給 origin 但不影響快取的值放在 origin request policy。 | 第 11 章 |
| Cache stampede | 快取踩踏 | 熱門 key 過期的瞬間大量請求同時穿透到資料庫，造成後端過載。 | 第 28 章 |
| Calculated health check | 計算型健康檢查 | 由多個子 health check 的結果依門檻組合出整體健康狀態的 Route 53 health check。 | 第 9 章 |
| Canary（CloudWatch Synthetics） | 合成監控腳本 | 依排程模擬使用者操作或呼叫 API 的腳本，在真實使用者受影響前發現問題。 | 第 36 章 |
| Canary deployment | 金絲雀部署 | 先把一小部分流量導到新版本，觀察指標正常後再全量切換。 | 第 21 章（詳見第 37 章） |
| Capacity provider | 容量提供者 | ECS 決定 task 跑在哪種容量（Fargate、Fargate Spot 或 EC2 ASG）並可設定比例的機制。 | 第 21 章 |
| Capacity Rebalancing | 容量再平衡 | ASG 收到 Spot rebalance recommendation 時主動啟動替代 instance，再終止風險較高的 instance。 | 第 18 章 |
| Capacity Reservation（On-Demand Capacity Reservation，ODCR） | 隨需容量保留 | 在特定 AZ 保留指定 instance type 的容量，沒有期限承諾，保留期間依 On-Demand 價格計費。 | 第 17 章 |
| CapEx／OpEx | 資本支出／營運支出 | CapEx 是一次性購買設備的投資，OpEx 是按使用持續支付的費用；雲端把前者轉成後者。 | 第 2 章 |
| CDC（Change Data Capture） | 變更資料擷取 | 持續讀取資料庫交易日誌，把新增、修改、刪除即時同步到其他系統；DMS 用它做最小停機遷移。 | 第 29 章（詳見第 45 章） |
| CDK（AWS Cloud Development Kit） | 雲端開發套件 | 用 TypeScript、Python 等程式語言定義基礎設施，合成為 CloudFormation template 部署。 | 第 37 章 |
| CDN（Content Delivery Network） | 內容傳遞網路 | 把內容快取在靠近使用者的邊緣節點，降低延遲並減輕 origin 負載。 | 第 11 章 |
| Cell-based architecture | 細胞式架構 | 把系統複製成多個彼此獨立的完整 cell，每個 cell 只服務一部分客戶，以限制故障範圍。 | 第 35 章 |
| Change set | 變更集 | CloudFormation 執行更新前的預覽，列出哪些資源會被新增、修改或取代。 | 第 37 章 |
| Chargeback／Showback | 成本計費／成本展示 | Chargeback 把雲端成本實際記到各部門帳上；Showback 只讓各部門看到自己的成本。 | 第 39 章 |
| Choreography | 編舞模式 | 各服務訂閱事件自行反應、沒有中央協調者的分散式流程設計，與 orchestration 相對。 | 第 33 章 |
| CIDR（Classless Inter-Domain Routing） | 無類別域間路由 | 以「位址/前綴長度」表示 IP 範圍的寫法，例如 10.0.0.0/16 包含 65,536 個位址。 | 第 3 章 |
| Circuit breaker | 斷路器 | 下游持續失敗時暫停呼叫並直接回傳 fallback，等一段時間再試探，避免連鎖故障。 | 第 33 章 |
| Claim check pattern | 提單模式 | 把大型 payload 存到 S3，訊息中只傳物件位置，繞過訊息大小上限。 | 第 32 章 |
| Classic Load Balancer（CLB） | 傳統負載平衡器 | 上一代的 Elastic Load Balancer，新架構應改用 ALB 或 NLB。 | 第 10 章 |
| Client VPN（AWS Client VPN） | 用戶端 VPN | 受管的遠端存取 VPN，讓個別使用者從筆電以 OpenVPN 客戶端連進 VPC。 | 第 8 章 |
| CloudFormation（AWS CloudFormation） | 基礎設施範本服務 | AWS 原生的 IaC 服務，依 template 建立、更新、刪除一組稱為 stack 的資源。 | 第 37 章 |
| CloudFront（Amazon CloudFront） | 內容傳遞網路服務 | AWS 的 CDN，透過全球 edge location 快取與加速內容，可搭配 WAF、OAC 與 edge function。 | 第 2 章（詳見第 11 章） |
| CloudFront Functions | CloudFront 邊緣函式 | 在 edge location 執行的輕量 JavaScript，只處理 viewer request／response，適合改寫 header、轉址等簡單邏輯。 | 第 11 章 |
| CloudHSM（AWS CloudHSM） | 雲端硬體安全模組 | 在 VPC 內提供單租戶、由客戶獨占控制金鑰的 HSM cluster。 | 第 15 章 |
| Cloud Map（AWS Cloud Map） | 服務探索 | 服務探索 registry，讓服務以名稱找到其他服務的 IP、port 或 URL。 | 第 21 章 |
| CloudShell（AWS CloudShell） | 瀏覽器命令列 | 在 Console 中開啟、已帶入登入身份的瀏覽器 shell，內建 AWS CLI。 | 第 2 章 |
| CloudTrail（AWS CloudTrail） | API 稽核紀錄 | 記錄 AWS API 呼叫「誰、何時、從哪裡、做了什麼」的稽核服務。 | 第 16 章 |
| Cloud WAN（AWS Cloud WAN） | 雲端廣域網路 | 以一份 core network policy 宣告式建立與管理跨 Region 全球網路的服務。 | 第 7 章（詳見第 41 章） |
| CloudWatch agent | CloudWatch 代理程式 | 安裝在 instance 或地端主機上，收集記憶體、磁碟等 OS 層指標與日誌檔的程式；這些指標預設沒有。 | 第 36 章 |
| CloudWatch（Amazon CloudWatch） | 監控服務 | AWS 的監控服務，提供 metric、log、alarm、dashboard 與多種應用程式監控功能。 | 第 36 章 |
| CloudWatch Logs Insights | 日誌查詢分析 | 對 CloudWatch Logs 執行互動式查詢與彙總的查詢語言與介面。 | 第 36 章 |
| Cluster mode（ElastiCache） | 叢集模式 | Redis OSS／Valkey 把資料分散到多個 shard 的模式，提升寫入與記憶體容量上限，client 必須 cluster-aware。 | 第 28 章 |
| CodeBuild（AWS CodeBuild） | 建置服務 | 受管的建置服務，依 buildspec 編譯、測試並產出 artifact，按建置時間計費。 | 第 37 章 |
| CodeDeploy（AWS CodeDeploy） | 部署服務 | 把新版本部署到 EC2、地端主機、Lambda 或 ECS 的服務，支援 in-place、blue/green、canary、linear。 | 第 37 章 |
| CodePipeline（AWS CodePipeline） | 持續交付管線 | 串接 source、build、test、deploy 各階段的受管 CI/CD pipeline。 | 第 37 章 |
| Cognito identity pool | 身份池 | 把已登入或訪客身份換成 AWS 臨時憑證，讓前端直接呼叫 AWS 服務。 | 第 13 章 |
| Cognito user pool | 使用者池 | 受管的使用者目錄與登入服務，負責註冊、登入、MFA，登入後發出 JWT。 | 第 13 章 |
| Cold start | 冷啟動 | Lambda 需要建立新執行環境並初始化程式時多出的延遲。 | 第 19 章 |
| Columnar storage | 欄式儲存 | 以欄為單位存放資料，分析查詢只讀需要的欄，壓縮率也高；Parquet 與 Redshift 都採用。 | 第 29 章（詳見第 30 章） |
| Compensatory scoring | 補償式計分 | AWS 考試只看總分是否達標，不要求每個 domain 都及格。 | 第 1 章 |
| Composite alarm | 複合告警 | 以 AND、OR、NOT 組合多個 alarm 的狀態，只在真正需要時通知，減少告警疲勞。 | 第 36 章 |
| Compute Optimizer（AWS Compute Optimizer） | 運算最佳化建議 | 依實際使用量分析 EC2、ASG、EBS、Lambda 等資源並提出 rightsizing 建議。 | 第 17 章 |
| Compute Savings Plans | 運算節省方案 | 承諾每小時固定消費金額，自動套用到任何 instance family、Region 的 EC2，以及 Fargate 與 Lambda。 | 第 17 章 |
| Concurrency（Lambda） | 並行數 | 同一時間正在處理請求的 Lambda 執行環境數量，受帳號每個 Region 的配額限制。 | 第 19 章 |
| Condition key | 條件鍵 | policy 的 Condition 區塊中可比對的屬性，例如 aws:SourceIp、aws:PrincipalOrgID、s3:prefix。 | 第 12 章 |
| Config（AWS Config） | 資源設定紀錄與合規 | 持續記錄資源設定變更並以 Config rule 評估是否合規的服務。 | 第 16 章 |
| Config rule | Config 規則 | AWS Config 中評估資源設定是否符合要求的規則，可用 AWS managed rules 或自訂 Lambda。 | 第 16 章 |
| Conformance pack | 合規套件 | 把一組 Config rules 與修正動作打包成一個單位，一次部署到帳號或整個組織。 | 第 16 章 |
| Confused deputy | 混淆代理人 | 權限較高的第三方被他人誘導，用自己的權限替攻擊者存取資源；跨帳號 role 用 external ID 防範。 | 第 13 章 |
| Connection draining（deregistration delay） | 連線排空 | target 從 load balancer 移除前，先停止送新請求並等待進行中的請求完成。 | 第 10 章 |
| Consolidated billing | 合併帳單 | Organizations 把所有成員帳號合併成一張帳單，用量合併計算級距並共享 RI 與 Savings Plans 折扣。 | 第 14 章 |
| Container | 容器 | 把應用程式與相依套件打包成可攜的 image，在同一個作業系統核心上隔離執行。 | 第 4 章（詳見第 21 章） |
| Container Insights | 容器洞察 | CloudWatch 收集 ECS、EKS 叢集與 container 層 metric 與日誌的功能。 | 第 36 章 |
| Continuous compliance | 持續合規 | 每天、每次變更都自動檢查設定是否合規並保留結果，而不是稽核前才檢查一次。 | 第 43 章 |
| Control plane／Data plane | 控制面／資料面 | control plane 負責建立、修改資源的管理 API；data plane 負責實際處理流量與資料，可用性設計通常更高。 | 第 2 章（詳見第 34 章） |
| Controls（Control Tower controls） | 控制項 | Control Tower 的治理規則（舊稱 guardrails），分為 preventive（SCP／RCP）、detective（Config）、proactive（CloudFormation Hooks）。 | 第 14 章 |
| Control Tower（AWS Control Tower） | 多帳號治理服務 | 依最佳實務自動建立 landing zone，提供 Account Factory 與 preventive、detective、proactive 三類 controls。 | 第 14 章（詳見第 40 章） |
| Convertible RI | 可轉換預留 instance | 可以在期間內換成其他 instance family、作業系統或 tenancy 的 Reserved Instance，折扣比 Standard RI 低。 | 第 17 章 |
| Cooldown | 冷卻時間 | simple scaling 每次擴縮後等待的時間，避免在新 instance 生效前重複觸發；預設 300 秒。 | 第 18 章 |
| CORS（Cross-Origin Resource Sharing） | 跨來源資源共用 | 瀏覽器允許網頁向不同 origin 發送請求的機制，伺服器以回應 header 宣告允許哪些來源。 | 第 20 章 |
| Cost allocation tags | 成本分配標籤 | 在 Billing 中啟用後，可依 tag 在 Cost Explorer 與 CUR 中分攤成本的標籤。 | 第 23 章（詳見第 39 章） |
| Cost and Usage Report（CUR） | 成本與用量報告 | 最詳細的帳單明細資料，以檔案輸出到 S3，常搭配 Athena 或 QuickSight 分析；新版透過 Data Exports 建立。 | 第 39 章 |
| Cost Anomaly Detection（AWS Cost Anomaly Detection） | 成本異常偵測 | 以機器學習監測成本異常增加並發送通知。 | 第 39 章 |
| Cost categories | 成本類別 | 用規則把帳號、tag、服務等歸類成自訂的成本群組（例如事業單位）。 | 第 39 章 |
| Cost Explorer（AWS Cost Explorer） | 成本瀏覽器 | 以圖表檢視、篩選與預測成本及用量，並提供 RI 與 Savings Plans 的覆蓋率與建議。 | 第 2 章（詳見第 39 章） |
| Cost Optimization Hub | 成本最佳化中心 | 集中彙整多帳號的成本最佳化建議並估算可節省金額。 | 第 39 章 |
| CQRS（Command Query Responsibility Segregation） | 命令查詢職責分離 | 把寫入模型與讀取模型分開，讀取端可用不同的資料庫與結構最佳化查詢。 | 第 46 章 |
| Crawler（Glue crawler） | 爬蟲 | 掃描 S3 等資料來源，推斷 schema 與分區並寫入 Glue Data Catalog。 | 第 30 章 |
| Credential report | 憑證報告 | 列出帳號中所有 IAM user 的密碼、access key、MFA 狀態與最後使用時間的報告。 | 第 12 章 |
| Cross-account observability | 跨帳號可觀測性 | CloudWatch 讓 monitoring account 直接查詢多個 source account 的 metric、log 與 trace。 | 第 36 章 |
| Cross-Region inference | 跨 Region 推論 | Bedrock 依 inference profile 把請求分散到多個 Region 的模型容量，提高吞吐與可用性。 | 第 47 章 |
| Cross-zone load balancing | 跨區負載平衡 | load balancer 節點把流量平均分給所有 AZ 的 target，而不是只給自己所在 AZ。 | 第 10 章 |
| CRR／SRR（Cross-Region／Same-Region Replication） | 跨 Region／同 Region 複寫 | S3 把新寫入的 object 非同步複寫到另一個 bucket；跨 Region 用於 DR 與就近存取，同 Region 用於帳號隔離或日誌彙整。 | 第 23 章 |
| Customer gateway（CGW） | 客戶閘道 | 在 AWS 中代表地端 VPN 設備的資源，記錄其 public IP 與 ASN。 | 第 8 章 |
| Customer managed key | 客戶管理金鑰 | 你在 KMS 中自行建立與管理的金鑰，可自訂 key policy、輪替、停用與跨帳號授權。 | 第 15 章 |
| Custom resource | 自訂資源 | CloudFormation 呼叫 Lambda 或 SNS 執行自訂邏輯，處理原生資源類型做不到的事。 | 第 37 章 |

## D

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Database Savings Plans | 資料庫節省方案 | 1 年期承諾，對 Aurora、RDS、DynamoDB、ElastiCache 等多種資料庫用量提供折扣，不論引擎、instance family 或 Region 都適用。 | 第 39 章 |
| Data events（CloudTrail） | 資料事件 | CloudTrail 記錄的資源內部操作（如 S3 GetObject、Lambda Invoke），量大且預設不記錄、需另外付費。 | 第 16 章 |
| Data Exports | 資料匯出 | Billing 中建立 CUR 2.0 等成本資料匯出到 S3 的功能。 | 第 39 章 |
| Data Firehose（Amazon Data Firehose） | 串流資料傳送服務 | 受管的近即時資料傳送服務，緩衝、轉換後把串流資料寫入 S3、Redshift、OpenSearch 等目的地。 | 第 6 章（詳見第 31 章） |
| Data key | 資料金鑰 | KMS 產生、實際用來加密資料的對稱金鑰；明文用完即丟，只保存被 KMS key 加密過的版本。 | 第 15 章 |
| Data lake | 資料湖 | 以 S3 為中心集中存放原始與加工後的各種格式資料，讀取時才套用 schema。 | 第 30 章 |
| Data Lifecycle Manager（Amazon Data Lifecycle Manager，DLM） | 資料生命週期管理員 | 依 tag 自動排程建立、保留與刪除 EBS snapshot 和 EBS-backed AMI。 | 第 24 章 |
| Data mesh | 資料網格 | 由各業務領域擁有並發布自己的資料產品，中央只提供治理與共享機制的組織方式。 | 第 30 章 |
| Data perimeter | 資料邊界 | 以 SCP、RCP、endpoint policy 組合確保只有受信任身份、從預期網路存取受信任資源。 | 第 12 章 |
| Data sharing（Redshift） | 資料共享 | Redshift 讓 consumer cluster 或 workgroup 直接查詢 producer 的即時資料，不需複製。 | 第 30 章 |
| Data sovereignty | 資料主權 | 資料必須存放並處理於特定國家或地區的法規要求，通常以 Region 限制 SCP 落實。 | 第 42 章 |
| DataSync（AWS DataSync） | 線上資料搬移服務 | 在地端儲存與 AWS 儲存服務之間，或 AWS 服務彼此之間，以排程、增量、可驗證的方式線上搬移檔案。 | 第 25 章 |
| Data warehouse | 資料倉儲 | 為分析查詢最佳化的資料庫，通常採欄式儲存與大規模平行處理，例如 Redshift。 | 第 4 章（詳見第 30 章） |
| DAX（DynamoDB Accelerator） | DynamoDB 加速器 | DynamoDB 專用、API 相容的 in-memory 快取，把讀取延遲降到微秒級，幾乎不需改程式。 | 第 27 章 |
| Dead-letter queue（DLQ） | 死信佇列 | 存放多次處理失敗之訊息的 queue，避免毒訊息無限重試並保留以便調查與 redrive。 | 第 19 章（詳見第 32 章） |
| Dedicated Host | 專用主機 | 整台實體伺服器專屬於你，可看到 socket 與 core 數，適合依實體核心計價的授權。 | 第 17 章 |
| Dedicated Instance | 專用 instance | 在只屬於你帳號的硬體上執行的 instance，但無法控制或看到實體主機。 | 第 17 章 |
| Defense in depth | 縱深防禦 | 在身份、網路、資料等多個層次各自設置控制，任何一層失守都還有下一層。 | 第 6 章 |
| Delay queue | 延遲佇列 | SQS 設定，新訊息在指定時間（最長 15 分鐘）內對 consumer 不可見。 | 第 32 章 |
| Delegated administrator | 委派管理員 | 讓 management account 以外的成員帳號管理某個服務（如 GuardDuty、Security Hub）的組織層設定。 | 第 13 章（詳見第 14 章） |
| DeletionPolicy | 刪除政策 | CloudFormation 資源屬性，決定 stack 刪除時資源要刪除、保留或先建 snapshot。 | 第 37 章 |
| Deletion protection | 刪除保護 | 開啟後 RDS、Aurora 等資源必須先關閉此設定才能刪除，防止誤刪。 | 第 26 章 |
| Dependency mapping | 相依關係對應 | 找出伺服器與應用程式之間的網路與功能相依，決定哪些系統必須一起遷移。 | 第 44 章 |
| Deployment circuit breaker（ECS） | 部署斷路器 | ECS rolling update 偵測新 task 持續無法變健康時自動停止並回滾到上一個穩定版本。 | 第 21 章 |
| Desired capacity | 期望容量 | ASG 目前要維持的 instance 數量，介於 min 與 max 之間，由 scaling policy 調整。 | 第 18 章 |
| Destinations（Lambda destinations） | 目的地 | 非同步呼叫成功或失敗後，把結果與原始事件送到 SQS、SNS、Lambda 或 EventBridge。 | 第 19 章 |
| Detective（Amazon Detective） | 資安調查服務 | 把 CloudTrail、VPC Flow Logs、GuardDuty finding 等整理成 behavior graph，用於資安事件的調查。 | 第 16 章 |
| DHCP option set | DHCP 選項集 | VPC 層級設定 instance 取得的 DNS server、網域名稱、NTP server 等選項。 | 第 5 章 |
| Dimension | 維度 | CloudWatch metric 的名稱值對（如 InstanceId），namespace、名稱與 dimension 組合才唯一識別一個 metric。 | 第 36 章 |
| Direct Connect（AWS Direct Connect，DX） | 專線連線 | 從地端經專線接到 AWS 的私有網路連線，頻寬穩定、延遲可預期，但預設不加密。 | 第 8 章 |
| Direct Connect gateway（DXGW） | 專線閘道 | 全球資源，讓一條 DX 透過 VIF 連到多個 Region 的 VGW 或 Transit Gateway；不在 VPC 之間轉送流量。 | 第 8 章 |
| Directory bucket | 目錄 bucket | S3 Express One Zone 使用的 bucket 類型，具階層目錄結構與單一 AZ 的極低延遲。 | 第 22 章 |
| Directory Service（AWS Directory Service） | 目錄服務 | 提供 AWS Managed Microsoft AD、AD Connector、Simple AD 三種目錄服務。 | 第 13 章 |
| Distributed Map | 分散式 Map | Step Functions 平行處理大量項目（例如 S3 中數百萬個 object）的 Map 模式，每批以 child workflow 執行。 | 第 33 章 |
| Distribution | 發佈 | CloudFront 的設定單位，包含網域名稱、origin、cache behavior、憑證與安全設定。 | 第 11 章 |
| DMS（AWS Database Migration Service） | 資料庫遷移服務 | 以 full load 加 CDC 在同質或異質資料庫之間搬移資料，遷移期間來源可持續服務。 | 第 25 章（詳見第 45 章） |
| DMS Schema Conversion | DMS 結構轉換 | DMS 內建的受管 schema 轉換功能，把 Oracle、SQL Server 等的 schema 與程式碼轉換到目標引擎。 | 第 45 章 |
| DNS（Domain Name System） | 網域名稱系統 | 把網域名稱解析成 IP 位址的分散式查詢系統。 | 第 3 章 |
| DNS Firewall（Route 53 Resolver DNS Firewall） | DNS 防火牆 | 在 VPC 的 Route 53 Resolver 上依網域清單允許或封鎖 DNS 查詢，阻擋惡意網域與 DNS 外洩。 | 第 9 章 |
| DNSSEC（DNS Security Extensions） | DNS 安全擴充 | 以數位簽章讓 resolver 驗證 DNS 回應未被竄改，防止 cache poisoning。 | 第 9 章 |
| DocumentDB（Amazon DocumentDB） | 文件資料庫 | 相容 MongoDB API 的受管文件資料庫，儲存架構與 Aurora 類似。 | 第 29 章 |
| Drift detection | 偏移偵測 | 比對 CloudFormation stack 的實際資源設定與 template，找出被手動修改的部分。 | 第 37 章 |
| DSSE-KMS | KMS 雙層伺服器端加密 | S3 以 KMS 金鑰做兩層獨立加密的伺服器端加密選項，滿足要求雙層加密的法規。 | 第 15 章 |
| Dual-stack | 雙棧 | 資源同時擁有 IPv4 與 IPv6 位址，可用任一種協定通訊。 | 第 3 章 |
| Dual write problem | 雙寫問題 | 同時寫資料庫和發訊息時，其中一個成功另一個失敗會造成不一致；用 transactional outbox 解決。 | 第 33 章 |
| Durability | 耐久性 | 資料不會遺失的機率；S3 設計為 11 個 9 的耐久性，與可用性是不同概念。 | 第 4 章 |
| Dynamic partitioning（Firehose） | 動態分區 | Firehose 依紀錄內容（例如 tenant 或日期欄位）把資料寫到不同的 S3 prefix。 | 第 31 章 |
| DynamoDB（Amazon DynamoDB） | 無伺服器 NoSQL 資料庫 | serverless 的 key-value 與文件 NoSQL 資料庫，個位數毫秒延遲，容量可隨需或預置。 | 第 2 章（詳見第 27 章） |
| DynamoDB Streams | DynamoDB 變更串流 | 以時間順序記錄 table 中 item 的變更，保留 24 小時，可觸發 Lambda 做事件處理。 | 第 27 章 |

## E

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| EBS（Amazon Elastic Block Store） | 彈性區塊儲存 | 掛在 EC2 上的網路區塊儲存 volume，綁定單一 AZ 並在 AZ 內自動複寫。 | 第 2 章（詳見第 24 章） |
| EBS-optimized | EBS 最佳化 | instance 為 EBS 流量提供專用頻寬，不與一般網路流量競爭；現行多數 instance type 預設啟用。 | 第 24 章 |
| EBS snapshot | EBS 快照 | EBS volume 的時間點增量備份，存放於 Regional 的 S3 中，可跨 Region 複製與分享。 | 第 17 章（詳見第 24 章） |
| EC2（Amazon Elastic Compute Cloud） | 彈性運算雲（虛擬機器） | AWS 的虛擬機器服務，依 instance type 選擇 CPU、記憶體、儲存與網路組合。 | 第 2 章（詳見第 17 章） |
| EC2 Image Builder | 映像建置服務 | 自動建置、測試與發佈 golden AMI 和 container image 的 pipeline 服務。 | 第 17 章 |
| EC2 Instance Connect Endpoint | instance 連線端點 | 讓使用者不需 bastion 與 public IP，就能以 SSH 或 RDP 連到 private subnet 中的 instance。 | 第 38 章 |
| EC2 Instance Savings Plans | EC2 instance 節省方案 | 承諾特定 Region 中特定 instance family 的每小時消費，折扣高於 Compute Savings Plans。 | 第 17 章 |
| ECMP（Equal-Cost Multi-Path） | 等價多路徑 | 把流量分散在多條成本相同的路徑上，Transit Gateway 用它合併多條 VPN tunnel 的頻寬。 | 第 7 章 |
| ECR（Amazon Elastic Container Registry） | 容器映像庫 | 受管的私有 container image registry，支援弱點掃描、lifecycle policy 與跨 Region 複寫。 | 第 19 章（詳見第 21 章） |
| ECS（Amazon Elastic Container Service） | 彈性容器服務 | AWS 自有的容器編排服務，以 task definition 與 service 管理 container，可跑在 EC2 或 Fargate。 | 第 21 章 |
| ECS Anywhere | ECS 任意環境 | 讓 ECS 管理地端或其他環境中的 external instance，control plane 仍在 AWS。 | 第 21 章 |
| Edge location | 邊緣節點 | CloudFront、Route 53 等全球服務的服務據點，數量遠多於 Region，靠近使用者。 | 第 2 章 |
| EFA（Elastic Fabric Adapter） | 彈性結構介面卡 | 支援 OS-bypass 的網路介面，提供 HPC 與 MPI 應用所需的低延遲節點間通訊。 | 第 17 章 |
| Effective policy | 有效政策 | 帳號從 root、OU 層層繼承後實際生效的管理政策內容（例如 tag policy、backup policy），可用 describe-effective-policy 查看。 | 第 43 章 |
| EFS access point | EFS 存取點 | 為應用程式強制指定 POSIX 使用者身份與根目錄的 EFS 進入點。 | 第 24 章 |
| EFS（Amazon Elastic File System） | 彈性檔案系統 | 受管的 NFS 檔案系統，可同時被多個 AZ 的 Linux instance 掛載，容量自動伸縮。 | 第 4 章（詳見第 24 章） |
| Egress-only Internet Gateway（EIGW） | 僅出站網際網路閘道 | 讓 IPv6 資源可以主動連出 Internet、但 Internet 無法主動連入的閘道。 | 第 3 章（詳見第 5 章） |
| EKS（Amazon Elastic Kubernetes Service） | 受管 Kubernetes 服務 | 受管的 Kubernetes control plane，worker 可用 managed node groups、Fargate 或 Auto Mode。 | 第 21 章 |
| EKS Pod Identity | Pod 身份 | 讓 EKS 中的 Pod 透過 agent 取得對應 IAM role 的臨時憑證，設定比 IRSA 更簡單。 | 第 21 章 |
| ElastiCache（Amazon ElastiCache） | 受管快取服務 | 受管的 Valkey、Redis OSS 與 Memcached in-memory 快取服務。 | 第 4 章（詳見第 28 章） |
| ElastiCache Serverless | 無伺服器快取 | 不需規劃節點的 ElastiCache 部署方式，依用量自動擴展並以 ECPU 與儲存量計費。 | 第 28 章 |
| Elastic Beanstalk（AWS Elastic Beanstalk） | 受管應用程式平台 | 上傳程式碼就自動建立 EC2、ASG、ELB 等環境的受管應用程式平台，仍可存取底層資源。 | 第 21 章 |
| Elastic Disaster Recovery（AWS DRS） | 彈性災難復原 | 以區塊層持續複寫伺服器到 AWS 的低成本 staging area，災難時快速啟動 recovery instance。 | 第 24 章（詳見第 34 章） |
| Elastic IP（EIP） | 彈性 IP | 固定的 public IPv4 位址，可在 instance 或 NAT Gateway 間重新指派。 | 第 5 章 |
| Elasticity | 彈性 | 依負載自動增減資源，用多少付多少。 | 第 4 章 |
| Elastic Load Balancing（ELB） | 彈性負載平衡 | AWS 受管 load balancer 服務的總稱，包含 ALB、NLB、GWLB 與舊的 CLB。 | 第 10 章 |
| Elastic Volumes | 彈性磁碟區 | 線上調整 EBS volume 的大小、類型與效能，不需卸載 volume。 | 第 24 章 |
| Embedding | 嵌入向量 | 把文字或圖片轉成代表語意的數值向量，語意相近的內容向量距離也近，是 RAG 檢索的基礎。 | 第 47 章 |
| EMF（Embedded Metric Format） | 嵌入式指標格式 | 在結構化日誌中嵌入 metric 定義，CloudWatch 自動從 log 擷取成 metric，不需呼叫 PutMetricData。 | 第 36 章 |
| EMR（Amazon EMR） | 大數據處理平台 | 受管的 Spark、Hadoop 等大數據框架平台，可跑在 EC2、EKS 或 Serverless。 | 第 30 章 |
| EMR Serverless | 無伺服器 EMR | 不需管理 cluster、依工作用量計費的 EMR 部署方式。 | 第 30 章 |
| ENA（Elastic Network Adapter） | 彈性網路介面卡 | EC2 的 enhanced networking 網路介面，提供高頻寬、高封包率與低延遲。 | 第 17 章 |
| Encryption at rest／in transit | 靜態加密／傳輸加密 | 靜態加密保護存放在磁碟上的資料，傳輸加密（TLS）保護網路傳送中的資料。 | 第 15 章 |
| Encryption context | 加密情境 | 呼叫 KMS 時附帶的非機密鍵值對，解密時必須相同，也可用在 policy 條件與稽核紀錄中。 | 第 15 章 |
| Endpoint policy | 端點政策 | 附加在 VPC endpoint 上的 resource policy，限制經由該 endpoint 可以存取哪些資源與動作。 | 第 6 章 |
| Endpoint service（PrivateLink） | 端點服務 | 服務提供者把 NLB 或 GWLB 背後的服務發布出去，讓 consumer 以 interface endpoint 私有存取。 | 第 7 章 |
| ENI（Elastic Network Interface） | 彈性網路介面 | VPC 中的虛擬網卡，擁有 private IP、security group 與 MAC 位址，可在同 AZ instance 間移動。 | 第 5 章 |
| Envelope encryption | 信封加密 | 用 data key 加密資料，再用 KMS key 加密 data key；大量資料不必送進 KMS。 | 第 15 章 |
| Ephemeral port | 臨時連接埠 | 用戶端連線時作業系統隨機分配的來源 port（常見範圍 1024–65535），NACL 要放行回程流量。 | 第 3 章（詳見第 6 章） |
| Error budget | 錯誤預算 | SLO 允許的失敗額度（例如 99.9% 對應每月約 43 分鐘），用完就暫停高風險變更。 | 第 36 章 |
| Evacuation | 撤離 | 停止把流量送往有問題的 Region，讓其他 Region 接手；之後再決定是否把資料擁有權一併移走。 | 第 42 章 |
| EventBridge（Amazon EventBridge） | 事件匯流排服務 | serverless 事件匯流排，依 event pattern 把 AWS 服務、SaaS 與自訂應用的事件路由到多種 target。 | 第 4 章（詳見第 32 章） |
| EventBridge Pipes | 事件管道 | 把單一來源（SQS、Kinesis、DynamoDB Streams 等）點對點接到 target，中間可過濾、轉換與 enrichment。 | 第 32 章 |
| EventBridge Scheduler | 排程器 | 受管排程服務，以一次性或 cron／rate 表達式在指定時間呼叫 AWS API 或 target。 | 第 19 章（詳見第 32 章） |
| Event bus | 事件匯流排 | EventBridge 接收事件並依 rule 路由到 target 的通道，分為 default、custom 與 partner。 | 第 32 章 |
| Event source mapping（ESM） | 事件來源對應 | 由 Lambda 代為輪詢 SQS、Kinesis、DynamoDB Streams、Kafka 等來源並批次呼叫 function 的機制。 | 第 19 章 |
| Eventual consistency | 最終一致性 | 寫入後短時間內讀取可能拿到舊值，但沒有新寫入時所有副本最終會一致。 | 第 4 章 |
| Exponential backoff | 指數退避 | 每次重試前等待的時間成倍增加，通常再加上隨機 jitter，避免同時重試壓垮服務。 | 第 22 章（詳見第 33 章） |
| Express workflow（Step Functions） | 快速工作流程 | 高吞吐、短時間（最長 5 分鐘）的 Step Functions 類型，不支援 .waitForTaskToken callback，不適合人工審核等長流程。 | 第 33 章 |
| External ID | 外部 ID | 跨帳號 trust policy 的條件值，由第三方為每個客戶產生，防止 confused deputy。 | 第 13 章 |
| External key store（XKS） | 外部金鑰存放區 | KMS key 的金鑰材料存放在 AWS 之外由你管理的金鑰管理器，每次加解密都要呼叫外部系統。 | 第 15 章 |

## F

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Failover | 容錯移轉 | 主要元件故障時自動或手動把服務切換到備援元件。 | 第 4 章 |
| Failover routing | 容錯移轉路由 | Route 53 依 health check 在 primary 健康時回應 primary 記錄、不健康時改回 secondary 記錄。 | 第 9 章 |
| Fan-out | 扇出 | 一則訊息同時送給多個訂閱者各自處理，典型做法是 SNS topic 訂閱多個 SQS queue。 | 第 32 章 |
| Fargate（AWS Fargate） | 無伺服器容器運算 | ECS 與 EKS 的 serverless 容器運算，不需管理 EC2，依 task 的 vCPU 與記憶體按秒計費。 | 第 21 章 |
| Fargate Spot | Fargate 閒置容量 | 以 Spot 容量執行 Fargate task，價格較低但可能在兩分鐘通知後被中斷。 | 第 21 章 |
| Fault domain | 故障域 | 一次故障會同時影響的範圍，例如 instance、AZ、Region；高可用設計要跨越故障域。 | 第 4 章（詳見第 34 章） |
| Fault Injection Service（AWS FIS） | 故障注入服務 | 受管的混沌工程服務，以實驗範本注入故障（停 instance、加延遲、中斷 AZ）並依 stop condition 停止。 | 第 34 章 |
| Feature flag | 功能旗標 | 以設定開關控制功能是否啟用，讓部署與發布分離，出問題時不需重新部署就能關閉。 | 第 35 章（詳見第 37 章） |
| Field-level encryption | 欄位層級加密 | CloudFront 在 edge 用公鑰加密指定的表單欄位，只有持有私鑰的後端元件能解密。 | 第 11 章 |
| FIFO queue（SQS FIFO） | 先進先出佇列 | 在同一個 message group ID 內保證順序並在 5 分鐘去重視窗內去除重複的 SQS queue。 | 第 32 章 |
| File storage | 檔案儲存 | 以目錄與檔案階層組織、多台機器透過 NFS 或 SMB 共享存取的儲存，例如 EFS、FSx。 | 第 4 章 |
| Fine-tuning | 微調 | 以自己的標註資料繼續訓練 foundation model，調整其風格或特定任務表現。 | 第 47 章 |
| Firewall Manager（AWS Firewall Manager） | 防火牆集中管理 | 在 Organizations 中集中定義並自動套用 WAF、Shield Advanced、security group、Network Firewall 等政策。 | 第 6 章（詳見第 16 章） |
| Fleet Manager | 機群管理員 | Systems Manager 中以 Console 集中檢視與操作受管節點（檔案、程序、日誌、遠端桌面）的功能。 | 第 38 章 |
| Flow Logs（VPC Flow Logs） | VPC 流量日誌 | 記錄 ENI、subnet 或 VPC 的 IP 流量中繼資料（來源、目的、port、ACCEPT／REJECT），不含封包內容。 | 第 5 章（詳見第 6 章） |
| Foundation model（FM） | 基礎模型 | 以大量資料預先訓練、可透過 prompt 處理多種任務的大型模型。 | 第 47 章 |
| FSx File Gateway（Amazon FSx File Gateway） | FSx 檔案閘道 | Storage Gateway 的一種，在地端快取 FSx for Windows File Server 的檔案共用。 | 第 25 章 |
| FSx for Lustre（Amazon FSx for Lustre） | 高效能平行檔案系統 | 高效能平行檔案系統，可與 S3 bucket 連結，適合 HPC 與機器學習訓練。 | 第 21 章（詳見第 24 章） |
| FSx for NetApp ONTAP（Amazon FSx for NetApp ONTAP） | 受管 NetApp 檔案系統 | 受管 NetApp ONTAP 檔案系統，同時支援 NFS、SMB、iSCSI，提供 snapshot、SnapMirror 等功能。 | 第 24 章 |
| FSx for OpenZFS（Amazon FSx for OpenZFS） | 受管 OpenZFS 檔案系統 | 受管 OpenZFS 檔案系統，以 NFS 提供低延遲存取與 snapshot、clone 功能。 | 第 24 章 |
| FSx for Windows File Server（Amazon FSx for Windows File Server） | 受管 Windows 檔案伺服器 | 受管的 Windows 檔案伺服器，支援 SMB、NTFS、Active Directory 整合與 Multi-AZ。 | 第 24 章 |
| Full jitter | 完全抖動 | 每次重試等待 0 到退避上限之間的隨機時間，最能打散同時重試的用戶端。 | 第 33 章 |
| Function URL（Lambda function URL） | 函式網址 | 直接給 Lambda function 一個 HTTPS 端點，不需 API Gateway；驗證只能選 IAM 或不驗證。 | 第 19 章 |

## G

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Game day | 演練日 | 在預先規劃的時段模擬真實故障，演練偵測、應變與 failover 流程。 | 第 34 章 |
| Gateway endpoint | 閘道端點 | 透過 route table 中的 prefix list 讓 VPC 私有存取 S3 與 DynamoDB 的 VPC endpoint，不收費。 | 第 6 章 |
| Gateway Load Balancer endpoint（GWLBe） | 閘道負載平衡器端點 | 放在 VPC subnet 中的 endpoint，route table 把流量導到它，再經 PrivateLink 送到 GWLB 背後的設備。 | 第 6 章（詳見第 10 章） |
| Gateway Load Balancer（GWLB） | 閘道負載平衡器 | 以 GENEVE 協定把流量透明地導到一組第三方防火牆或檢查設備並維持流量對稱的 load balancer。 | 第 10 章 |
| Geolocation routing | 地理位置路由 | Route 53 依使用者所在洲、國家或州回應不同記錄，常用於法規或在地化內容。 | 第 9 章 |
| Geoproximity routing | 地理鄰近路由 | Route 53 依使用者與資源的地理距離回應記錄，並可用 bias 擴大或縮小某資源的服務範圍。 | 第 9 章 |
| Geo restriction | 地理限制 | CloudFront 依使用者所在國家允許或拒絕存取內容。 | 第 11 章 |
| Global Accelerator（AWS Global Accelerator） | 全球加速器 | 提供兩個 anycast 固定 IP，讓 TCP／UDP 流量從最近的 edge 進入 AWS 骨幹並快速 failover 到健康 endpoint。 | 第 2 章（詳見第 11 章） |
| Global Datastore（ElastiCache） | 全域資料存放區 | ElastiCache for Redis OSS／Valkey 的跨 Region 複寫，一個 primary Region 可讀寫，其他 Region 唯讀。 | 第 28 章（詳見第 42 章） |
| Global tables（DynamoDB global tables） | 全域資料表 | 把 DynamoDB table 複寫到多個 Region、每個 Region 都可讀寫的 multi-active 架構，預設以 last writer wins 解決衝突。 | 第 27 章 |
| Glue（AWS Glue） | 資料整合服務 | serverless 的資料整合服務，提供 Data Catalog、crawler 與 Spark ETL job。 | 第 30 章 |
| Glue DataBrew（AWS Glue DataBrew） | 視覺化資料清理 | 以視覺化介面、免寫程式清理與正規化資料的工具。 | 第 30 章 |
| Glue Data Catalog | 資料目錄 | Athena、Redshift Spectrum、EMR 共用的中央 metadata 目錄，記錄 table 的 schema、格式與位置。 | 第 30 章 |
| Golden AMI | 黃金映像 | 預先安裝並強化好作業系統、代理程式與設定的標準 AMI，供全公司啟動 instance 使用。 | 第 17 章 |
| Governance mode／Compliance mode | 治理模式／合規模式 | S3 Object Lock 的兩種模式：governance 允許有特殊權限者解除，compliance 在保留期內任何人（含 root）都不能刪除或縮短。 | 第 16 章（詳見第 23 章） |
| Graceful degradation | 優雅降級 | 部分元件故障或過載時關閉非核心功能或回傳簡化結果，讓核心功能繼續服務。 | 第 35 章 |
| Grant（KMS grant） | 授權 | 以程式動態、暫時地授予某個 principal 使用 KMS key 的權限，常被 AWS 服務使用。 | 第 15 章 |
| Graph database | 圖形資料庫 | 以節點與邊儲存關係，擅長多層關係查詢，例如社群網路、詐欺偵測；AWS 的服務是 Neptune。 | 第 29 章 |
| GraphQL | 圖形查詢語言 | 讓 client 以一個查詢精確指定需要的欄位、一次取得多種資料的 API 查詢語言。 | 第 20 章 |
| Graviton（AWS Graviton） | AWS 自研 Arm 處理器 | AWS 自行設計的 arm64 處理器，通常提供比同級 x86 更好的價格效能比。 | 第 17 章 |
| GSI（Global Secondary Index） | 全域次要索引 | partition key 與 sort key 都可與 base table 不同、有獨立容量、只支援最終一致讀取的 DynamoDB 索引。 | 第 27 章 |
| GuardDuty（Amazon GuardDuty） | 威脅偵測服務 | 分析 CloudTrail、VPC Flow Logs、DNS 日誌等資料偵測威脅的受管服務，只偵測不阻擋。 | 第 16 章 |

## H

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Hallucination | 幻覺 | 模型產生看似合理但與事實不符的內容；RAG 與 grounding 檢查用來降低它。 | 第 47 章 |
| Health check（ELB） | 健康檢查 | load balancer 定期探測 target，只把流量送給健康的 target。 | 第 10 章 |
| Health check grace period | 健康檢查寬限期 | 新 instance 啟動後的一段時間內，ASG 不依 health check 結果把它判為不健康。 | 第 18 章 |
| Health Dashboard（AWS Health Dashboard） | 健康狀態儀表板 | 顯示 AWS 服務整體狀態以及影響你帳號資源之事件與排程維護的入口。 | 第 36 章 |
| Hibernation | 休眠 | 停止 instance 時把記憶體內容存到加密的 EBS root volume，啟動時恢復，縮短應用程式暖機時間。 | 第 17 章 |
| High-resolution metric | 高解析度指標 | 以 1 秒為粒度的 custom metric，搭配 10 秒或 30 秒的 alarm 評估週期。 | 第 36 章 |
| Hosted zone | 託管區域 | Route 53 中存放一個網域所有 DNS 記錄的容器，分為 public 與 private。 | 第 3 章（詳見第 9 章） |
| Hot partition | 熱分割 | 大量請求集中在少數 partition key，使單一 partition 超過吞吐上限而被 throttle。 | 第 27 章 |
| HPA（Horizontal Pod Autoscaler） | Pod 水平自動擴展 | Kubernetes 依 CPU 或自訂指標自動調整 Pod 數量的元件。 | 第 21 章 |
| HSM（Hardware Security Module） | 硬體安全模組 | 專門產生、保存金鑰並執行加解密的防竄改硬體。 | 第 15 章 |
| HTTP API（API Gateway HTTP API） | HTTP API | 功能較精簡、延遲與價格較低的 API Gateway 類型，原生支援 JWT authorizer。 | 第 20 章 |
| Hub-and-spoke | 中心輻射 | 以中央 hub（例如 Transit Gateway）連接所有 spoke VPC 與地端的網路拓撲。 | 第 41 章 |
| Hyperplane ENI | Hyperplane 網路介面 | Lambda 連接 VPC 時在 subnet 中建立、由多個執行環境共用的網路介面；它不會取得 public IP。 | 第 19 章 |

## I

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| IaaS／PaaS／SaaS | 基礎設施／平台／軟體即服務 | 基礎設施即服務、平台即服務、軟體即服務；由左到右，雲端業者代管的層次越多。 | 第 2 章 |
| IaC（Infrastructure as Code） | 基礎設施即程式碼 | 以版本控制的程式碼或範本定義基礎設施，讓建立過程可重複、可審查、可自動化。 | 第 2 章（詳見第 37 章） |
| IAM Access Analyzer | IAM 存取分析器 | 找出被外部存取的資源、未使用的權限，並驗證與依 CloudTrail 產生最小權限 policy。 | 第 12 章 |
| IAM（AWS Identity and Access Management） | 身份與存取管理 | 管理誰（principal）可以對哪些 AWS 資源做哪些動作的全域服務。 | 第 2 章（詳見第 12 章） |
| IAM database authentication | IAM 資料庫驗證 | 以 IAM 產生的短效 authentication token 登入 RDS／Aurora，不需在程式中保存資料庫密碼。 | 第 26 章 |
| IAM group | IAM 群組 | IAM user 的集合，用來一次附加 policy；group 不能巢狀，也不能被當成 principal。 | 第 12 章 |
| IAM Identity Center（AWS IAM Identity Center） | IAM 身份中心 | 集中管理員工登入多個 AWS 帳號與應用程式的服務，以 permission set 指派權限並可連接外部 IdP。 | 第 13 章 |
| IAM role | IAM 角色 | 沒有長期憑證、由受信任的 principal 透過 STS assume 後取得臨時憑證的身份。 | 第 12 章 |
| IAM Roles Anywhere | IAM 任意環境角色 | 讓 AWS 外部的工作負載以 X.509 憑證換取 IAM role 的臨時憑證，取代長期 access key。 | 第 13 章 |
| IAM user | IAM 使用者 | 帳號內具有長期憑證（密碼或 access key）的身份；員工登入建議改用 Identity Center。 | 第 12 章 |
| Idempotency key | 冪等鍵 | 用戶端為每個業務操作產生的唯一 ID，伺服器據此辨識重複請求並回傳第一次的結果。 | 第 20 章（詳見第 33 章） |
| Idempotent | 冪等 | 同一個操作執行一次和執行多次的結果相同；at-least-once 系統的必要條件。 | 第 4 章（詳見第 33 章） |
| Identity-based policy | 身份型政策 | 附加在 user、group 或 role 上，描述該身份可以做什麼的 policy。 | 第 12 章 |
| IdP（Identity Provider） | 身份提供者 | 負責驗證使用者並發出 SAML assertion 或 OIDC token 的系統，例如 Okta、Microsoft Entra ID。 | 第 13 章 |
| IMDSv2 | Instance Metadata Service 第 2 版 | 必須先以 PUT 取得 session token 才能讀取 instance metadata，可防範 SSRF 竊取憑證。 | 第 17 章 |
| Immutable deployment | 不可變部署 | 在新的一組 instance 上部署新版本，驗證健康後才替換舊 instance，失敗時直接丟棄新 instance。 | 第 21 章（詳見第 37 章） |
| Implicit deny | 隱含拒絕 | 沒有任何 policy 明確允許時，請求預設被拒絕。 | 第 12 章 |
| Inbound／Outbound endpoint（Route 53 Resolver） | 入站／出站端點 | inbound 讓地端 DNS 查詢 VPC 內的名稱，outbound 搭配 forwarding rule 讓 VPC 把特定網域轉給地端 DNS。 | 第 8 章 |
| Inference | 推論 | 用訓練好的模型對新輸入產生預測或輸出的過程。 | 第 47 章 |
| Inference profile | 推論設定檔 | Bedrock 中定義模型與可路由 Region 的資源，用於跨 Region 推論與成本歸屬。 | 第 47 章 |
| Inline policy | 內嵌政策 | 直接嵌在單一 user、group 或 role 中、與該身份同生命週期的 policy。 | 第 12 章 |
| Inspection VPC | 檢查 VPC | 集中部署防火牆或 Network Firewall 的 VPC，所有跨 VPC 或出入 Internet 的流量都被導經這裡。 | 第 7 章（詳見第 41 章） |
| Inspector（Amazon Inspector） | 弱點掃描服務 | 自動掃描 EC2、ECR image 與 Lambda 的軟體弱點（CVE）與網路暴露風險。 | 第 16 章 |
| Instance profile | instance 設定檔 | 把 IAM role 交給 EC2 的容器，instance 上的程式從 metadata 取得該 role 的臨時憑證。 | 第 12 章 |
| Instance refresh | instance 汰換 | ASG 依 minimum healthy percentage 分批以新 launch template 替換既有 instance。 | 第 18 章 |
| Instance store | 執行個體儲存 | instance 所在實體主機上的本機磁碟，速度快但 stop、terminate 或硬體故障時資料會消失。 | 第 4 章（詳見第 24 章） |
| Intelligent-Tiering（S3 Intelligent-Tiering） | 智慧分層 | 依每個 object 的存取模式自動在不同存取層之間移動、沒有取回費的儲存類別，適合存取模式未知的資料。 | 第 23 章 |
| Interface endpoint | 介面端點 | 以 PrivateLink 在 subnet 中建立 ENI、讓 VPC 私有存取 AWS 服務或其他服務的 VPC endpoint，依小時與流量收費。 | 第 6 章 |
| Internet Gateway（IGW） | 網際網路閘道 | 附加在 VPC 上、讓有 public IP 的資源與 Internet 雙向通訊的閘道，水平擴展且高可用。 | 第 5 章 |
| Invalidation | 失效 | 在 TTL 到期前強制 CloudFront 從 edge 移除指定路徑的快取。 | 第 11 章 |
| io2 Block Express | io2 區塊高速磁碟區 | 最高效能的 EBS SSD volume 類型，提供高 IOPS、低延遲與較高耐久性，支援 Multi-Attach。 | 第 24 章 |
| IOPS（Input/Output Operations Per Second） | 每秒 I/O 次數 | 儲存裝置每秒能處理的讀寫次數，小檔隨機存取的主要效能指標。 | 第 4 章（詳見第 24 章） |
| IPAM（Amazon VPC IP Address Manager） | IP 位址管理 | 以 pool 階層規劃、配發並稽核整個組織的 IP 位址，避免 CIDR 重疊。 | 第 5 章 |
| IP-based routing | IP 型路由 | Route 53 依查詢來源 IP 所屬的 CIDR collection 回應記錄。 | 第 9 章 |
| IPsec | IP 安全協定 | 在 IP 層加密與驗證封包的協定組，Site-to-Site VPN 用它建立加密 tunnel。 | 第 8 章 |
| IPv6 | 第 6 版網際網路協定 | 128 位元的 IP 位址，位址充足，AWS 上的 IPv6 位址是全球唯一、可路由的。 | 第 3 章 |
| IRSA（IAM Roles for Service Accounts） | 服務帳號 IAM 角色 | 讓 EKS Pod 透過 OIDC 把 Kubernetes service account 對應到 IAM role 取得臨時憑證。 | 第 21 章 |

## J

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Jitter | 抖動 | 在重試等待或 TTL 中加入隨機時間，避免大量用戶端同時動作。 | 第 33 章 |
| JMS（Java Message Service） | Java 訊息服務 | Java 的標準訊息 API；既有應用依賴 JMS 時，遷移目標通常是 Amazon MQ。 | 第 32 章 |
| Job bookmark（Glue） | 作業書籤 | Glue ETL job 記住上次處理到的位置，下次只處理新資料。 | 第 30 章 |
| JWT（JSON Web Token） | JSON 網頁權杖 | 經簽章的 JSON 權杖，記錄使用者身份與聲明；Cognito 與 OIDC 以它傳遞登入結果。 | 第 13 章 |

## K

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Karpenter | Kubernetes 節點自動配置器 | 開源的 Kubernetes 節點自動配置工具，依待排程 Pod 的需求直接啟動合適的 EC2 並自動整併節點。 | 第 21 章 |
| KCL（Kinesis Client Library） | Kinesis 用戶端函式庫 | 協調多個 consumer 分工讀取 Kinesis shard、以 DynamoDB 記錄 lease 與 checkpoint 的函式庫。 | 第 31 章 |
| Kendra（Amazon Kendra） | 企業智慧搜尋 | 受管的企業智慧搜尋服務，可連接多種文件來源並以自然語言搜尋。 | 第 47 章 |
| Key policy | 金鑰政策 | 附加在 KMS key 上的 resource policy；任何人要使用 KMS key，都必須先由 key policy 允許（直接或委派給 IAM）。 | 第 15 章 |
| Key rotation | 金鑰輪替 | KMS 定期產生新的金鑰材料，key ID 與 ARN 不變，舊材料保留以解密舊資料。 | 第 15 章 |
| Keyspaces（Amazon Keyspaces） | 受管 Cassandra 資料庫 | serverless、相容 Apache Cassandra CQL 的 wide-column 資料庫服務。 | 第 29 章 |
| Kinesis Data Streams（Amazon Kinesis Data Streams，KDS） | Kinesis 資料串流 | 以 shard 為單位、可多 consumer 重播的即時資料串流，同一 partition key 內保持順序，預設保留 24 小時、最長 365 天。 | 第 31 章 |
| Kinesis Video Streams | Kinesis 影像串流 | 擷取、儲存與處理攝影機等裝置影像串流的服務。 | 第 31 章 |
| KMS（AWS Key Management Service） | 金鑰管理服務 | 受管的加密金鑰服務，金鑰材料不離開 HSM，與大多數 AWS 服務整合並由 CloudTrail 記錄每次使用。 | 第 15 章 |
| KPL（Kinesis Producer Library） | Kinesis 生產者函式庫 | 把多筆紀錄聚合、批次並重試寫入 Kinesis 的 producer 函式庫。 | 第 31 章 |
| Kubernetes | 容器編排平台 | 開源的容器編排平台，以 Pod、Deployment、Service 等宣告式物件管理 container。 | 第 21 章 |

## L

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| L4／L7 | 第 4 層／第 7 層 | L4 只看 IP 與 port（TCP／UDP），L7 能讀懂 HTTP 的 path、header、cookie；NLB 是 L4、ALB 是 L7。 | 第 3 章（詳見第 10 章） |
| Lake Formation（AWS Lake Formation） | 資料湖權限治理 | 在 Glue Data Catalog 之上集中管理資料湖的資料庫、表、欄、列層級權限與跨帳號共享。 | 第 30 章 |
| Lambda authorizer | Lambda 授權器 | API Gateway 呼叫你的 Lambda 驗證 token 或請求參數，回傳 IAM policy 決定是否放行。 | 第 20 章 |
| Lambda（AWS Lambda） | 無伺服器函式運算 | serverless 函式運算，事件觸發才執行，依請求數與 GB-秒計費，單次最長 15 分鐘。 | 第 2 章（詳見第 19 章） |
| Lambda@Edge | 邊緣 Lambda | 在 CloudFront Regional edge cache 執行的 Lambda，可處理四種觸發點、呼叫外部服務與讀取 body。 | 第 11 章 |
| Lambda layer | Lambda 層 | 把共用函式庫或相依套件打包，供多個 function 共用的封存檔。 | 第 19 章 |
| Landing zone | 著陸區 | 依最佳實務預先建好的多帳號環境，包含帳號結構、身份、日誌、安全與網路基準。 | 第 14 章（詳見第 40 章） |
| Last writer wins | 最後寫入者勝 | 多 Region 同時寫入同一筆資料時，以時間最晚的寫入為準、較早的寫入被覆蓋的衝突處理方式。 | 第 27 章（詳見第 42 章） |
| Latency | 延遲 | 一個請求從送出到收到回應所需的時間，主要受距離與處理時間影響。 | 第 3 章 |
| Latency-based routing | 延遲路由 | Route 53 回應對使用者網路延遲最低之 Region 的記錄。 | 第 9 章 |
| Launch template | 啟動範本 | 定義 AMI、instance type、security group、user data 等啟動參數的版本化範本，取代舊的 launch configuration。 | 第 18 章 |
| Least privilege | 最小權限 | 只授予完成工作所需的最少權限，並隨使用情況持續收斂。 | 第 12 章 |
| Legal hold | 法律保全 | S3 Object Lock 中沒有到期日的保留標記，在移除前 object 版本都不能被刪除。 | 第 16 章（詳見第 23 章） |
| LF-Tags（Lake Formation tag-based access control） | Lake Formation 標籤 | 以 tag 對資料湖的資料庫、表、欄授權，資源增加時不需逐一設定權限。 | 第 30 章 |
| License Manager（AWS License Manager） | 授權管理員 | 追蹤與管理軟體授權使用量並強制授權規則，常與 Dedicated Hosts 搭配。 | 第 17 章 |
| Lifecycle hook | 生命週期掛鉤 | ASG 在 instance 啟動或終止的過程中暫停，讓你執行初始化或收尾工作後再繼續。 | 第 18 章 |
| Lifecycle rule（S3 Lifecycle） | 生命週期規則 | 依 object 年齡自動轉換儲存類別或刪除 object、舊版本與未完成的 multipart upload。 | 第 23 章 |
| Listener | 監聽器 | load balancer 上依 protocol 與 port 接收連線、再依規則轉給 target group 的設定。 | 第 7 章（詳見第 10 章） |
| Little's Law | 利特爾法則 | 系統中平均同時處理的請求數等於到達率乘以平均處理時間，可用來估算所需並行數。 | 第 35 章 |
| LLM（Large Language Model） | 大型語言模型 | 以大量文字訓練、能理解與生成自然語言的 foundation model。 | 第 47 章 |
| Load shedding | 負載卸除 | 過載時主動拒絕部分請求，保住其餘請求的成功率與延遲。 | 第 35 章 |
| Local Zones（AWS Local Zones） | 本地區域 | 把部分 AWS 運算與儲存服務延伸到大都會區、提供個位數毫秒延遲的據點。 | 第 2 章 |
| Log Archive account | 日誌封存帳號 | landing zone 中集中存放 CloudTrail、Config 等日誌、權限嚴格限制的專用帳號。 | 第 14 章（詳見第 40 章） |
| Log group | 日誌群組 | CloudWatch Logs 中共享 retention、權限與加密設定的一組 log stream。 | 第 36 章 |
| Logically air-gapped vault | 邏輯隔離保管庫 | AWS Backup 的特殊 vault，一律以 compliance mode 鎖定，並可透過 AWS RAM 共享給獨立的復原帳號，在主帳號被攻陷時仍能還原。 | 第 34 章 |
| Longest prefix match | 最長前綴匹配 | 路由表有多條符合的路由時，選前綴最長（範圍最小、最精確）的那一條。 | 第 3 章 |
| Long polling | 長輪詢 | SQS ReceiveMessage 最多等待 20 秒直到有訊息，減少空回應與請求費用。 | 第 32 章 |
| Loose coupling | 鬆散耦合 | 元件之間透過 queue、事件或穩定介面溝通，一方故障或擴展不直接影響另一方。 | 第 4 章 |
| LSI（Local Secondary Index） | 本地次要索引 | 與 base table 共用 partition key、使用不同 sort key 的 DynamoDB 索引，只能在建立 table 時定義。 | 第 27 章 |

## M

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Macie（Amazon Macie） | 敏感資料探索 | 以機器學習與規則找出 S3 中的敏感資料（例如 PII）並評估 bucket 安全狀態。 | 第 16 章 |
| MACsec | MAC 安全加密 | IEEE 802.1AE 第二層加密，可在支援的 Direct Connect dedicated connection 上加密線路流量。 | 第 8 章 |
| Mainframe Modernization（AWS Mainframe Modernization） | 大型主機現代化 | 協助把大型主機應用 replatform 或自動重構到 AWS 的服務。 | 第 45 章 |
| Maintenance Window（Systems Manager） | 維護時段 | 定義在什麼時段、對哪些節點執行哪些任務（例如修補）的排程。 | 第 38 章 |
| Managed node group | 受管節點群組 | EKS 代為建立與管理 worker node 的 ASG，支援自動更新與排空。 | 第 21 章 |
| Managed prefix list | 受管前綴清單 | 一組 CIDR 的具名集合，可在 security group 與 route table 中引用；AWS 也提供服務的 prefix list。 | 第 6 章 |
| Managed Service for Apache Flink（Amazon Managed Service for Apache Flink） | 受管 Flink 串流處理 | 受管的 Apache Flink，執行有狀態的即時串流處理（視窗彙總、join），以 KPU 計費。 | 第 31 章 |
| Management account | 管理帳號 | 建立 Organization 的帳號，負責帳單與組織管理；SCP 不會限制它。 | 第 14 章 |
| Map state | Map 狀態 | Step Functions 對陣列中每個項目平行執行相同步驟的 state，分為 inline 與 distributed 兩種模式。 | 第 33 章 |
| Materialized view | 具體化檢視 | 預先計算並儲存查詢結果的 view，Redshift 可自動或手動重新整理。 | 第 30 章 |
| Memcached | Memcached 快取引擎 | 簡單、多執行緒的 in-memory 快取引擎，不支援持久化、複寫與進階資料結構。 | 第 28 章 |
| MemoryDB（Amazon MemoryDB） | 持久化記憶體資料庫 | 相容 Redis OSS／Valkey、以 Multi-AZ 交易日誌提供持久性的 in-memory 主要資料庫。 | 第 28 章 |
| Message group ID | 訊息群組 ID | SQS FIFO 中決定順序範圍的欄位，同一群組內嚴格依序，不同群組可平行處理。 | 第 32 章 |
| Metric filter | 指標篩選器 | 從 CloudWatch Logs 的日誌中比對樣式並轉成 metric，以便設定 alarm。 | 第 36 章 |
| MFA Delete | MFA 刪除保護 | S3 versioning 的額外保護，永久刪除版本或變更 versioning 狀態時必須提供 root user 的 MFA。 | 第 22 章 |
| MFA（Multi-Factor Authentication） | 多因素驗證 | 登入時除了密碼還需第二種因素（例如裝置上的動態碼或安全金鑰）。 | 第 12 章 |
| Migration Evaluator | 遷移成本評估 | 分析地端資源使用量並估算遷移到 AWS 後成本的評估服務。 | 第 44 章 |
| Migration factory | 遷移工廠 | 以標準化流程、工具與團隊分工，大量且可重複地執行遷移 wave 的作業模式。 | 第 44 章 |
| Migration Hub（AWS Migration Hub） | 遷移中心 | 集中追蹤遷移進度的服務；自 2025-11-07 起不再開放新客戶，新專案改用 AWS Transform。 | 第 44 章 |
| Mixed instances policy | 混合 instance 政策 | ASG 同時使用多種 instance type 並混合 On-Demand 與 Spot 的設定。 | 第 17 章（詳見第 18 章） |
| Model invocation logging | 模型呼叫日誌 | Bedrock 把每次模型呼叫的請求與回應記錄到 CloudWatch Logs 或 S3，供稽核與除錯。 | 第 47 章 |
| MPA／MRA | 遷移組合評估／遷移準備度評估 | MRA 評估組織在人員、流程與技術上是否準備好遷移；MPA 分析應用程式組合並估算成本與遷移策略。 | 第 44 章 |
| MQTT | 物聯網訊息協定 | 輕量的 publish/subscribe 訊息協定，常用於 IoT 裝置與 AWS IoT Core 通訊。 | 第 31 章 |
| MREC／MRSC | 多 Region 最終一致／強一致 | DynamoDB global tables 的兩種一致性模式：MREC 非同步複寫、以 last writer wins 解決衝突；MRSC 寫入同步確認到其他 Region，RPO 為零。 | 第 27 章（詳見第 42 章） |
| MSK（Amazon Managed Streaming for Apache Kafka） | 受管 Kafka | 受管的 Apache Kafka 叢集，相容既有 Kafka 用戶端與工具。 | 第 31 章 |
| MSK Serverless | 無伺服器 Kafka | 不需規劃 broker 與儲存容量、依用量計費的 MSK 部署方式。 | 第 31 章 |
| mTLS（mutual TLS） | 雙向 TLS | 用戶端與伺服器互相出示並驗證憑證，常用於 B2B 或裝置驗證。 | 第 3 章 |
| MTTD／MTTR | 平均偵測時間／平均復原時間 | 從故障發生到被發現、以及到恢復服務所需的平均時間，是可觀測性與營運的成效指標。 | 第 36 章 |
| Multi-Attach | 多重掛載 | 讓同一個 io1／io2 volume 同時掛到同一 AZ 內的多台 Nitro instance，應用程式必須自行處理寫入一致性。 | 第 24 章 |
| Multi-AZ DB cluster | 多可用區 DB 叢集 | RDS 的一種部署：一個 writer 與兩個可讀的 reader 分布在三個 AZ，failover 更快。 | 第 4 章（詳見第 26 章） |
| Multi-AZ（RDS Multi-AZ） | 多可用區部署 | 在另一個 AZ 維護同步複寫的 standby，主 instance 故障時自動 failover；standby 不提供讀取。 | 第 4 章（詳見第 26 章） |
| Multipart upload | 分段上傳 | 把大檔案切成多段平行上傳再合併；超過 5 GB 的 object 必須使用，最大 object 為 5 TB。 | 第 22 章 |
| Multi-Region Access Points（S3） | 多 Region 存取點 | 提供單一全球端點，把 S3 請求路由到延遲最低的 Region bucket，並可搭配複寫做 failover。 | 第 22 章（詳見第 42 章） |
| Multi-Region key（KMS） | 多 Region 金鑰 | 在多個 Region 擁有相同 key ID 與金鑰材料的 KMS key，資料可在一個 Region 加密、另一個 Region 解密。 | 第 15 章 |
| Multi-site active-active | 多站點雙活 | 兩個以上 Region 同時承接正式流量的 DR 策略，RTO 與 RPO 最小、成本與複雜度最高。 | 第 34 章 |
| Multivalue answer routing | 多值回應路由 | Route 53 一次回應最多 8 筆健康的記錄，讓用戶端自行挑選，提供簡易的 DNS 層負載分散。 | 第 9 章 |

## N

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| NACL（Network ACL） | 網路存取控制清單 | 套用在 subnet 邊界、stateless、有 allow 與 deny 並依規則編號由小到大評估的防火牆。 | 第 6 章 |
| NAT Gateway | NAT 閘道 | 受管的 NAT 服務，讓 private subnet 主動連出 Internet；它是 zonal 資源，高可用要每個 AZ 各一台。 | 第 3 章（詳見第 5 章） |
| NAT instance | NAT 執行個體 | 自己在 EC2 上執行 NAT 的舊做法，需自行處理高可用、擴展與修補，並關閉 source/destination check。 | 第 5 章 |
| NAT（Network Address Translation） | 網路位址轉換 | 改寫封包的來源或目的位址，讓多台使用 private IP 的機器共用 public IP 連外。 | 第 3 章 |
| Neptune（Amazon Neptune） | 圖形資料庫服務 | 受管的圖形資料庫，支援 Gremlin、openCypher 與 SPARQL 查詢。 | 第 29 章 |
| Network Access Analyzer | 網路存取分析器 | 依你定義的 Network Access Scope 找出 VPC 中不符合預期的網路存取路徑。 | 第 6 章 |
| Network Firewall（AWS Network Firewall） | 網路防火牆 | 部署在 VPC 中的受管 stateful／stateless 防火牆與 IPS，支援網域過濾與 Suricata 規則。 | 第 10 章（詳見第 16 章） |
| Nitro System（AWS Nitro System） | Nitro 系統 | AWS 以專用硬體卸載虛擬化、網路與儲存功能的 EC2 底層平台。 | 第 17 章 |
| NLB（Network Load Balancer） | 網路負載平衡器 | L4 load balancer，處理 TCP／UDP／TLS，延遲極低，每個 AZ 可有固定 IP 並能保留 client IP。 | 第 3 章（詳見第 10 章） |
| Noisy neighbor | 吵鬧的鄰居 | 多租戶系統中某個租戶占用過多共享資源，拖慢其他租戶。 | 第 49 章 |
| NoSQL | 非關聯式資料庫 | 不使用關聯式表格模型的資料庫統稱，包括 key-value、文件、wide-column、圖形等類型。 | 第 4 章 |

## O

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| OAC（Origin Access Control） | 來源存取控制 | CloudFront 以 SigV4 簽署請求存取 S3 等 origin，讓 bucket 只接受特定 distribution；取代舊的 OAI。 | 第 11 章 |
| OAI（Origin Access Identity） | 來源存取身份 | CloudFront 存取私有 S3 的舊做法，不支援 SSE-KMS 等功能，新設計改用 OAC。 | 第 11 章 |
| Object | 物件 | S3 中儲存的單位，由 key、資料本身與 metadata 組成，整份讀寫而非部分修改。 | 第 4 章（詳見第 22 章） |
| Object Lock（S3 Object Lock） | 物件鎖定 | 以 WORM 方式在保留期內禁止刪除或覆寫 object 版本，分為 governance 與 compliance 模式。 | 第 16 章（詳見第 23 章） |
| Object Ownership（S3 Object Ownership） | 物件擁有權 | 控制 bucket 中 object 的擁有者與 ACL 是否生效的設定。 | 第 22 章 |
| Object storage | 物件儲存 | 以 key 存取整個物件、扁平命名空間、可無限擴展的儲存，例如 S3。 | 第 4 章 |
| Observability | 可觀測性 | 透過 metric、log、trace 從外部推斷系統內部狀態，回答「為什麼」而不只是「是否故障」。 | 第 36 章 |
| OIDC（OpenID Connect） | OpenID 連線協定 | 建立在 OAuth 2.0 上的身份協定，以 JWT 格式的 ID token 傳遞使用者身份。 | 第 13 章 |
| OLTP／OLAP | 線上交易處理／線上分析處理 | OLTP 處理大量小筆、即時的讀寫交易；OLAP 處理少量但掃描大量資料的分析查詢。 | 第 4 章 |
| On-demand capacity mode（DynamoDB） | 隨需容量模式 | 依實際讀寫請求數計費、自動因應流量的 DynamoDB 容量模式，適合流量不可預測的 table。 | 第 27 章 |
| On-Demand Instances | 隨需 instance | 不需承諾、依秒或小時計費的 EC2 購買方式，最有彈性但單價最高。 | 第 17 章 |
| One Zone-IA（S3 One Zone-IA） | 單一區域不常存取 | 資料只存在單一 AZ、價格低於 Standard-IA 的不常存取儲存類別，適合可重建的資料。 | 第 4 章（詳見第 23 章） |
| OpenSearch Service（Amazon OpenSearch Service） | 搜尋與分析服務 | 受管的 OpenSearch 叢集，用於全文搜尋、日誌分析與向量搜尋。 | 第 29 章 |
| Open table format | 開放表格式 | 在 S3 檔案之上提供交易、schema 演進與 time travel 的表格式，例如 Apache Iceberg。 | 第 30 章 |
| OpenTelemetry（OTel） | 開放遙測標準 | 開源、與廠商無關的可觀測性標準與 SDK，用來產生與傳送 trace、metric、log。 | 第 36 章 |
| OpsCenter | 營運中心 | Systems Manager 中集中檢視、調查與處理營運問題（OpsItem）的功能。 | 第 38 章 |
| Optimistic locking | 樂觀鎖 | 寫入時以 condition expression 檢查版本號是否未變，避免覆蓋他人的更新。 | 第 27 章 |
| Organization conformance pack | 組織合規套件 | 由 management account 或委派管理員把 conformance pack 一次部署到組織內所有帳號，成員帳號無法修改或刪除。 | 第 43 章 |
| Organizations（AWS Organizations） | 組織服務 | 把多個 AWS 帳號納入同一個組織，以 OU 分層並套用 SCP 等政策與合併帳單。 | 第 5 章（詳見第 14 章） |
| Organization trail | 組織 trail | 由 management account 或委派管理員建立、自動記錄組織內所有帳號 API 活動的 CloudTrail trail。 | 第 16 章 |
| Origin | 源站 | CloudFront 取得原始內容的位置，例如 S3 bucket、ALB 或任何 HTTP 伺服器。 | 第 11 章 |
| Origin failover（origin group） | 源站容錯移轉 | CloudFront 在 primary origin 回應特定錯誤時改向 secondary origin 取資料，只適用於 GET、HEAD、OPTIONS。 | 第 11 章 |
| Origin Shield | 源站防護層 | CloudFront 在 origin 前多加一層集中快取，提高命中率並減少回源請求。 | 第 11 章 |
| OU（Organizational Unit） | 組織單位 | Organizations 中把帳號分組的容器，政策附加在 OU 上會向下繼承。 | 第 14 章 |
| Outposts（AWS Outposts） | 地端 AWS 機櫃 | 把 AWS 硬體與服務安裝在你的資料中心，以同一套 API 管理，適合低延遲或資料必須留在本地的需求。 | 第 2 章 |

## P

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Parameter group | 參數群組 | RDS 與 Aurora 的資料庫引擎參數設定集合，靜態參數修改後需 reboot 才生效。 | 第 26 章 |
| Parameter Store（AWS Systems Manager Parameter Store） | 參數存放區 | 存放設定值與機密（SecureString 以 KMS 加密）的階層式參數服務，標準層免費但沒有內建自動輪替。 | 第 15 章 |
| Parquet（Apache Parquet） | 欄式檔案格式 | 開放的欄式檔案格式，壓縮率高且支援只讀需要的欄，能大幅減少 Athena 的掃描量。 | 第 30 章 |
| Partial batch response | 部分批次回應 | Lambda 處理 SQS 或 stream 批次時只回報失敗的項目，成功的項目不必重新處理。 | 第 19 章 |
| Partition（data lake） | 分區 | 依日期等欄位把資料放在不同 S3 prefix，查詢時只讀符合條件的分區（partition pruning）。 | 第 30 章 |
| Partition key | 分割鍵 | DynamoDB 用來雜湊決定 item 存放在哪個 partition 的屬性；值越分散，吞吐越平均。 | 第 27 章 |
| Patch Manager／Patch baseline | 修補管理／修補基準 | Systems Manager 依 patch baseline 的核准規則自動掃描與安裝作業系統修補。 | 第 38 章 |
| PCI DSS | 支付卡產業資料安全標準 | 處理信用卡資料的組織必須遵守的安全標準，稽核範圍以持卡人資料環境（CDE）為界。 | 第 40 章（詳見第 50 章） |
| Permissions boundary | 權限邊界 | 附加在 user 或 role 上、設定其權限上限的 managed policy；本身不授權，常用來安全地讓開發者自建 role。 | 第 12 章 |
| Permission set | 權限集 | IAM Identity Center 中定義的一組權限，指派到帳號後會自動建立對應的 IAM role。 | 第 13 章 |
| Personalize（Amazon Personalize） | 個人化推薦 | 以你的使用者互動資料訓練推薦模型的受管個人化推薦服務。 | 第 47 章 |
| PII（Personally Identifiable Information） | 個人可識別資訊 | 能直接或間接識別特定個人的資料，例如姓名、身分證號、電話。 | 第 16 章 |
| Pilot light | 指示燈 | DR 策略之一：備援 Region 持續複寫資料、只保留最小核心，災難時才啟動並擴展運算，RTO 約數十分鐘。 | 第 34 章 |
| PITR（Point-in-Time Recovery） | 時間點還原 | 利用自動備份與交易日誌把資料庫還原到保留期內任一秒，RDS 還原時一定會建立新的 instance。 | 第 4 章（詳見第 26 章） |
| Placement group | 置放群組 | 控制 instance 實體分布的設定：cluster（同機架低延遲）、spread（分散到不同硬體）、partition（分組隔離）。 | 第 17 章 |
| Polly（Amazon Polly） | 文字轉語音 | 把文字轉成自然語音的服務。 | 第 47 章 |
| Pool／Silo model | 共用模型／獨立模型 | 多租戶中 pool 讓所有租戶共用同一套資源，silo 為每個租戶提供獨立資源；silo 隔離較強、成本較高。 | 第 49 章 |
| Predictive scaling | 預測擴展 | 依歷史負載的週期性預測未來需求，提前擴充 ASG 容量。 | 第 18 章 |
| Presigned URL | 預先簽章網址 | 以簽署者的權限產生、限時有效的 S3 存取網址，讓沒有 AWS 憑證的人上傳或下載特定 object。 | 第 22 章 |
| Principal | 主體 | 發出 AWS 請求的身份，例如 IAM user、role、AWS 服務或聯合身份。 | 第 12 章 |
| Private CA（AWS Private CA） | 私有憑證機構 | 建立與管理私有憑證機構，發出組織內部使用的私有 TLS 憑證。 | 第 15 章 |
| Private hosted zone | 私有託管區域 | 只有關聯的 VPC 能解析的 Route 53 hosted zone，可關聯其他帳號的 VPC。 | 第 9 章 |
| PrivateLink（AWS PrivateLink） | 私有連結 | 以 interface endpoint 在 VPC 間私有存取服務的技術，流量不經 Internet，可解決 CIDR 重疊。 | 第 5 章（詳見第 7 章） |
| Private subnet／Public subnet | 私有子網路／公有子網路 | route table 有指向 Internet Gateway 之預設路由的是 public subnet，沒有的是 private subnet；AWS 沒有「public」開關。 | 第 5 章 |
| Prompt injection | 提示注入 | 攻擊者在輸入或外部文件中夾帶指令，誘使模型忽略原本指示或濫用工具權限。 | 第 47 章 |
| Provisioned concurrency | 預置並行數 | 預先初始化指定數量的 Lambda 執行環境，消除 cold start，需額外付費。 | 第 19 章 |
| Provisioned Throughput（Bedrock） | 預置吞吐量 | 為 Bedrock 模型購買固定的處理容量，適合穩定的大量推論或使用客製化模型。 | 第 47 章 |
| Proxy Protocol v2 | 代理協定第 2 版 | 在 TCP 連線前加入原始 client IP 等資訊的標頭，讓 NLB 或 PrivateLink 背後的服務得知真正來源。 | 第 7 章 |
| Publish/subscribe（pub/sub） | 發布訂閱 | 發布者把訊息送到 topic，所有訂閱者各自收到一份，發布者不需知道有哪些訂閱者。 | 第 32 章 |

## Q

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| QLDB（Amazon Quantum Ledger Database） | 帳本資料庫 | AWS 的帳本資料庫，已於 2025-07-31 停止支援，新設計改用 Aurora PostgreSQL 等方案。 | 第 29 章 |
| Queue | 佇列 | 生產者放入、消費者取出的訊息緩衝區，讓雙方以不同速度獨立運作並吸收尖峰。 | 第 4 章（詳見第 32 章） |
| Queue-based load leveling | 以佇列平準負載 | 用 queue 吸收突發流量，讓後端以穩定速度處理，保護無法快速擴展的下游。 | 第 32 章 |
| QuickSight（Amazon QuickSight） | 商業智慧儀表板 | 受管的商業智慧與儀表板服務，以 SPICE in-memory 引擎加速查詢；BI 功能現已併入 Amazon Quick，稱為 Amazon Quick Sight。 | 第 30 章 |

## R

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| RA3 | RA3 節點 | Redshift 的節點類型，運算與 Redshift Managed Storage 分離，可各自擴展。 | 第 30 章 |
| RAG（Retrieval-Augmented Generation） | 檢索增強生成 | 先從知識庫檢索相關文件片段放進 prompt，再讓模型依據這些內容回答，降低幻覺並引用最新資料。 | 第 47 章 |
| RAM（AWS Resource Access Manager） | 資源存取管理員 | 把 subnet、Transit Gateway、Resolver rule、IPAM pool 等資源共享給其他帳號或整個組織的服務。 | 第 5 章（詳見第 7 章） |
| Rate-based rule | 速率型規則 | WAF 依 IP 或其他 aggregation key 計算請求速率，超過門檻就封鎖或挑戰。 | 第 16 章 |
| RBAC（Role-Based Access Control） | 以角色為基礎的存取控制 | 依職務角色指派固定權限的模型，角色或資源增加時 policy 也要跟著增加。 | 第 12 章 |
| RCP（Resource Control Policy） | 資源控制政策 | Organizations 的政策類型，限制組織內資源最多可以被誰存取；與 SCP 一樣只限制、不授權。 | 第 12 章（詳見第 14 章） |
| RDS（Amazon Relational Database Service） | 受管關聯式資料庫 | 受管的 MySQL、PostgreSQL、MariaDB、Oracle、SQL Server 等資料庫，代管備份、修補與 Multi-AZ。 | 第 2 章（詳見第 26 章） |
| RDS Custom | 可客製 RDS | 允許存取底層作業系統與資料庫設定的 RDS 變體，適合需要特殊客製化的 Oracle 與 SQL Server。 | 第 26 章 |
| RDS Proxy | RDS 連線代理 | 受管的資料庫連線池，集中並重用連線，讓大量 Lambda 不會耗盡資料庫連線並加快 failover。 | 第 19 章（詳見第 26 章） |
| Read-local／write-global | 就近讀取、集中寫入 | 所有 Region 都服務讀取，寫入集中送到一個 primary Region 的多 Region 資料模式。 | 第 42 章 |
| Read replica | 唯讀副本 | 以非同步複寫建立的唯讀資料庫副本，用於分散讀取，可跨 Region 並 promote 成獨立資料庫。 | 第 26 章 |
| Recycle Bin | 資源回收筒 | 依保留規則暫存被刪除的 EBS snapshot 與 AMI，在期限內可復原誤刪的資源。 | 第 24 章 |
| Redis OSS／Valkey | Redis 開源版／Valkey | 支援複寫、持久化、多種資料結構的 in-memory 引擎；Valkey 是 Redis 的開源分支，ElastiCache 兩者都支援。 | 第 28 章 |
| Redrive | 重新驅動 | 把 DLQ 中的訊息送回來源 queue 重新處理，或從失敗步驟重新執行 Step Functions。 | 第 32 章 |
| Redshift（Amazon Redshift） | 資料倉儲服務 | 受管的 MPP 欄式資料倉儲，提供 provisioned 與 Serverless 兩種部署。 | 第 4 章（詳見第 30 章） |
| Redshift Serverless（Amazon Redshift Serverless） | 無伺服器資料倉儲 | 不需管理節點、依 RPU 用量計費的 Redshift 部署方式。 | 第 30 章 |
| Redshift Spectrum | Redshift 外部查詢 | 讓 Redshift 直接以 external table 查詢 S3 上的資料，不需先載入。 | 第 30 章 |
| Refactor | 重構 | 7Rs 之一：重新設計應用程式以採用雲端原生架構（例如 serverless、微服務），效益最大、工作量也最大。 | 第 21 章（詳見第 44 章） |
| Region | 區域 | AWS 在某個地理區域的一組 AZ，彼此獨立，選擇時要考慮合規、延遲、服務可用性與價格。 | 第 2 章 |
| Regional edge cache | 區域邊緣快取 | 位於 edge location 與 origin 之間、容量較大的 CloudFront 中間快取層。 | 第 2 章 |
| Rehost | 重新託管 | 7Rs 之一：不修改作業系統與應用程式，把伺服器原封不動搬到 EC2（lift and shift），主要工具是 MGN。 | 第 44 章 |
| Rekognition（Amazon Rekognition） | 影像辨識 | 分析圖片與影片中物件、人臉、文字與不當內容的電腦視覺服務。 | 第 47 章 |
| Relocate | 重新安置 | 7Rs 之一：把整個虛擬化平台（例如 VMware）上的 VM 搬到雲端的同類平台，不需轉換 VM。 | 第 44 章 |
| Replatform | 換平台 | 7Rs 之一：小幅修改以使用受管服務（例如自管 MySQL 改成 RDS），不改動核心架構。 | 第 21 章（詳見第 44 章） |
| Replication | 複寫 | 把資料持續複製到其他節點或位置；同步複寫不遺失已確認的寫入，非同步複寫延遲較低但可能遺失最後的變更。 | 第 4 章 |
| Replication lag | 複寫延遲 | 非同步複寫中副本落後主資料庫的時間，讀取副本可能拿到舊資料。 | 第 4 章 |
| Replication Time Control（S3 RTC） | 複寫時間控制 | 為 S3 Replication 提供 99.99% 的 object 在 15 分鐘內複寫完成的 SLA 與監控指標。 | 第 23 章 |
| Repurchase | 重新購買 | 7Rs 之一：放棄現有軟體，改用 SaaS 或另一套商業產品（drop and shop）。 | 第 44 章 |
| Requester Pays | 請求者付費 | S3 bucket 設定，讓下載資料的請求者而非 bucket 擁有者支付請求與傳輸費用。 | 第 22 章 |
| Reserved concurrency | 保留並行數 | 為某個 Lambda function 保留且同時限制的最大並行數，也可用來保護下游或暫停 function。 | 第 19 章 |
| Reserved Instances（RI） | 預留 instance | 承諾 1 年或 3 年使用特定 instance 屬性以換取折扣的購買方式，分 Standard 與 Convertible。 | 第 17 章（詳見第 39 章） |
| Resilience Hub（AWS Resilience Hub） | 韌性評估中心 | 依你設定的 RTO／RPO 目標評估應用程式架構的韌性並提出改善建議。 | 第 34 章 |
| Resolver endpoint（Route 53 Resolver endpoint） | 解析器端點 | 在 VPC 中建立的 ENI，用於地端與 VPC 之間互相轉送 DNS 查詢的 hybrid DNS 元件。 | 第 8 章 |
| Resource-based policy | 資源型政策 | 附加在資源上（例如 bucket、queue、KMS key）、必須寫 Principal 的 policy，可直接授權其他帳號。 | 第 12 章 |
| REST API（API Gateway REST API） | REST API | 功能最完整的 API Gateway 類型，支援 API key、usage plan、快取、request validation、WAF 與 private endpoint。 | 第 20 章 |
| Retain | 保留 | 7Rs 之一：暫時把系統留在原地，並設定重新檢視的時間點。 | 第 44 章 |
| Retire | 退役 | 7Rs 之一：直接關閉沒有人使用或功能重複的系統，是投報率最高的一項。 | 第 44 章 |
| Retry storm | 重試風暴 | 大量用戶端在故障時同時重試，讓原本快恢復的服務再次被壓垮。 | 第 33 章 |
| RI and Savings Plans discount sharing | 折扣共享 | Organizations 中讓 RI 與 Savings Plans 折扣跨帳號套用的偏好設定，可對指定帳號關閉共享。 | 第 43 章 |
| Rightsizing | 調整到合適規格 | 依實際用量把資源換成更小或更合適的規格，是最直接的成本最佳化手段。 | 第 39 章 |
| Role chaining | 角色串接 | 用一個 role 的臨時憑證再 assume 另一個 role；串接後的 session 最長 1 小時。 | 第 13 章 |
| Rolling deployment | 滾動部署 | 分批更新 instance，部署期間容量會暫時減少；rolling with additional batch 先加開一批維持容量。 | 第 18 章（詳見第 37 章） |
| Root user | 根使用者 | 建立 AWS 帳號時使用的 email 身份，擁有完整權限；應啟用 MFA、不建立 access key、日常不使用。 | 第 2 章（詳見第 12 章） |
| Route 53（Amazon Route 53） | DNS 服務 | AWS 的 DNS 服務，提供網域註冊、public／private hosted zone、多種 routing policy 與 health check。 | 第 2 章（詳見第 9 章） |
| Route 53 Profiles | Route 53 設定檔 | 把 private hosted zone、Resolver rule、DNS Firewall 等 DNS 設定打包，一次套用到多個 VPC 與帳號。 | 第 8 章 |
| Route 53 Resolver | VPC DNS 解析器 | 每個 VPC 內建的 DNS resolver（VPC CIDR 起始位址 + 2），負責解析 private hosted zone 與 Internet 名稱。 | 第 3 章（詳見第 8 章） |
| Route table | 路由表 | 決定 subnet 內流量往哪裡送的規則集合，每個 subnet 只能關聯一張。 | 第 3 章（詳見第 5 章） |
| RPO（Recovery Point Objective） | 復原點目標 | 最多能接受遺失多久的資料，決定備份與複寫的頻率。 | 第 4 章（詳見第 34 章） |
| RTO（Recovery Time Objective） | 復原時間目標 | 故障後最多能接受多久恢復服務，決定 DR 策略要預先準備多少資源。 | 第 4 章（詳見第 34 章） |
| RUM（CloudWatch RUM） | 真實使用者監控 | 從使用者瀏覽器收集頁面載入時間、JavaScript 錯誤等真實使用體驗資料。 | 第 36 章 |
| Run Command | 遠端執行命令 | Systems Manager 對大量受管節點遠端執行指令或 SSM document，不需 SSH，並可控制速率。 | 第 38 章 |

## S

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| S3（Amazon Simple Storage Service） | 簡單儲存服務（物件儲存） | AWS 的物件儲存服務，耐久性設計為 11 個 9，自 2020-12 起提供 strong read-after-write consistency。 | 第 2 章（詳見第 22 章） |
| S3 Express One Zone | S3 單區高速儲存 | 單一 AZ、使用 directory bucket 的高效能儲存類別，提供個位數毫秒延遲。 | 第 23 章 |
| S3 File Gateway | S3 檔案閘道 | Storage Gateway 的一種，以 NFS／SMB 讓地端存取 S3，每個檔案對應一個 object，本地保留快取。 | 第 25 章 |
| S3 Glacier Deep Archive | S3 Glacier 深度封存 | 成本最低的 S3 儲存類別，取回時間以小時計（標準 12 小時內），最短存放 180 天。 | 第 23 章 |
| S3 Glacier Flexible Retrieval | S3 Glacier 彈性取回 | 封存用儲存類別，取回需數分鐘到數小時，最短存放 90 天。 | 第 23 章 |
| S3 Glacier Instant Retrieval | S3 Glacier 即時取回 | 毫秒級取回的封存類別，適合每季存取一次左右的資料，最短存放 90 天。 | 第 23 章 |
| S3 Inventory | S3 清單報告 | 定期輸出 bucket 中 object 及其中繼資料（儲存類別、加密、複寫狀態）的清單檔。 | 第 23 章 |
| S3 Select | S3 選取查詢 | 以 SQL 只取回 object 中部分資料的功能；自 2024 年 7 月起不再對新客戶開放，改用 Athena 等替代方案。 | 第 22 章 |
| S3 Standard | S3 標準 | 預設的 S3 儲存類別，跨至少 3 個 AZ、毫秒存取、沒有取回費與最短存放期限。 | 第 23 章 |
| S3 Standard-IA | S3 標準不常存取 | 不常存取但需要毫秒取回的儲存類別，儲存較便宜但有取回費、最短 30 天與最小計費 128 KB。 | 第 23 章 |
| S3 Storage Lens | S3 儲存透鏡 | 提供組織層級 S3 用量與活動指標及最佳化建議的分析儀表板。 | 第 23 章 |
| S3 Tables | S3 表格 | 內建 Apache Iceberg 支援、自動維護的 table bucket 儲存類型，專為表格資料分析設計。 | 第 30 章 |
| S3 Transfer Acceleration | S3 傳輸加速 | 透過 CloudFront edge location 與 AWS 骨幹加速遠距離上傳到 S3。 | 第 11 章 |
| Saga | 長交易補償模式 | 把跨服務的長流程拆成多個本地交易，任一步失敗時依序執行補償交易恢復一致性。 | 第 33 章 |
| SageMaker AI（Amazon SageMaker AI） | 機器學習平台 | 建置、訓練與部署機器學習模型的平台，提供 real-time、serverless、async 與 batch transform 推論。 | 第 47 章 |
| SAM（AWS Serverless Application Model） | 無伺服器應用模型 | CloudFormation 的擴充語法與 CLI，用精簡寫法定義 Lambda、API Gateway 等 serverless 資源。 | 第 20 章（詳見第 37 章） |
| SAML 2.0 | 安全斷言標記語言 | 以 XML assertion 在 IdP 與服務提供者之間傳遞驗證結果的企業單一登入標準。 | 第 13 章 |
| Savings Plans | 節省方案 | 承諾 1 年或 3 年每小時固定消費金額以換取折扣的彈性購買方式，分 Compute、EC2 Instance、SageMaker 等類型。 | 第 17 章（詳見第 39 章） |
| Scaled score | 量尺分數 | AWS 考試把原始成績依題目難度換算成 100–1000 分，720 或 750 分及格不等於答對 72% 或 75%。 | 第 1 章 |
| Scale up／Scale out | 垂直擴展／水平擴展 | scale up 換更大的機器；scale out 增加機器數量，需要應用程式是 stateless。 | 第 4 章 |
| Scheduled action | 排程動作 | 在指定時間調整 ASG 的 min、max、desired，適合可預知的負載變化。 | 第 18 章 |
| SCIM（System for Cross-domain Identity Management） | 跨網域身份佈建協定 | 自動在 IdP 與 IAM Identity Center 之間同步使用者與群組的佈建協定。 | 第 13 章 |
| SCP（Service Control Policy） | 服務控制政策 | Organizations 中限制成員帳號（含 root user）最大權限的政策；不授權、不影響 management account 與 service-linked role。 | 第 12 章（詳見第 14 章） |
| SCT（AWS Schema Conversion Tool） | schema 轉換工具 | 把來源資料庫的 schema 與程式碼轉成目標引擎格式並產出評估報告的桌面工具。 | 第 45 章 |
| Secondary CIDR | 次要 CIDR | VPC 位址不夠時額外加入的 CIDR block。 | 第 5 章 |
| Secrets Manager（AWS Secrets Manager） | 機密管理員 | 存放資料庫密碼、API key 等機密，支援自動 rotation、跨 Region 複寫與 resource policy。 | 第 15 章 |
| Security group | 安全群組 | 套用在 ENI 上的 stateful 虛擬防火牆，只有 allow 規則，可引用其他 security group 作為來源。 | 第 2 章（詳見第 6 章） |
| Security Hub（AWS Security Hub） | 安全中心 | 彙整 GuardDuty、Inspector、Macie 等服務的 finding，並依安全標準檢查設定（CSPM）。 | 第 16 章 |
| Security Lake（Amazon Security Lake） | 安全資料湖 | 把 AWS 與第三方安全日誌以 OCSF 格式集中到你帳號中的 S3 資料湖。 | 第 16 章 |
| Service Catalog（AWS Service Catalog） | 服務目錄 | 讓管理者發布經核准的 CloudFormation 產品組合，使用者自助部署而不需底層權限。 | 第 37 章 |
| Service-linked role | 服務連結角色 | 由 AWS 服務建立與管理、權限預先定義的 role；不受 SCP 影響。 | 第 12 章 |
| Service quota | 服務配額 | 每個帳號每個 Region 對資源數量或 API 速率的上限，多數為預設值、可申請提高。 | 第 17 章（詳見第 35 章） |
| Session Manager | 工作階段管理員 | Systems Manager 透過 SSM Agent 建立的瀏覽器或 CLI shell，不需開 inbound port、bastion 或 SSH key，並可記錄 session。 | 第 38 章 |
| Session policy | 工作階段政策 | assume role 或聯合登入時傳入、進一步限縮該 session 權限的 policy。 | 第 12 章 |
| Session tag | 工作階段標籤 | assume role 時傳入的 tag，可在 policy 中做 ABAC 判斷。 | 第 12 章 |
| Sharding | 分片 | 依 key 把資料水平切分到多個資料庫或節點，突破單一節點的寫入上限。 | 第 4 章（詳見第 35 章） |
| Shard（Kinesis） | 分片 | Kinesis Data Streams 的容量單位，每個 shard 有固定的寫入與讀取吞吐上限。 | 第 31 章 |
| Shared Responsibility Model | 責任分擔模型 | AWS 負責雲端本身的安全，客戶負責在雲端中放的資料、身份、設定與應用程式安全。 | 第 2 章 |
| Shield（AWS Shield Standard／Advanced） | DDoS 防護 | Standard 自動免費防護常見 L3／L4 DDoS；Advanced 付費提供進階防護、SRT 支援與 DDoS 成本保護。 | 第 16 章 |
| Shuffle sharding | 洗牌分片 | 為每個客戶隨機分配一小組資源組合，讓任兩個客戶完全重疊的機率極低，限制單一客戶造成的影響。 | 第 35 章 |
| Signed URL／Signed cookie | 簽章網址／簽章 cookie | CloudFront 限制私有內容存取的方式；signed URL 適合單一檔案，signed cookie 適合多個檔案。 | 第 11 章 |
| SigV4A | 多 Region 簽章第 4 版 | 支援多 Region 的 AWS 請求簽章演算法，呼叫 S3 Multi-Region Access Points 時使用。 | 第 42 章 |
| Simple AD | 簡易目錄 | 相容部分 Active Directory 功能的低成本目錄服務，不支援 trust 等進階功能。 | 第 13 章 |
| Single-table design | 單表設計 | 把多種實體放在同一個 DynamoDB table，以 key 設計滿足所有存取模式。 | 第 27 章 |
| SiteLink | 站點互連 | 讓連到同一個 Direct Connect gateway 的不同 DX location 之間經 AWS 骨幹直接互通的功能。 | 第 8 章 |
| Site-to-Site VPN（AWS Site-to-Site VPN） | 站對站 VPN | 以兩條 IPsec tunnel 經 Internet 連接地端與 VGW 或 Transit Gateway 的受管 VPN。 | 第 8 章 |
| SLA／SLO／SLI | 服務水準協議／目標／指標 | SLI 是量測值（如成功率），SLO 是內部目標，SLA 是對客戶的合約承諾與賠償條件。 | 第 4 章 |
| SnapStart（Lambda SnapStart） | 快照啟動 | 在發布版本時預先初始化並快照執行環境，大幅縮短 cold start。 | 第 19 章 |
| SNI（Server Name Indication） | 伺服器名稱指示 | TLS 握手時用戶端告知目標主機名稱，讓同一個 IP 可以出示不同網域的憑證。 | 第 3 章 |
| Snow Family（AWS Snow Family） | 實體資料搬移裝置 | 以實體裝置離線搬移大量資料；Snowball Edge 已不再提供給新客戶、Snowcone 停產、Snowmobile 退役。 | 第 25 章 |
| SNS（Amazon Simple Notification Service） | 簡單通知服務 | 受管的 pub/sub 服務，把訊息推送給 SQS、Lambda、HTTP、email、SMS 等多個訂閱者。 | 第 4 章（詳見第 32 章） |
| Split brain | 腦裂 | 故障或網路分割時，兩個 Region 都認為自己是 primary 而同時接受寫入，造成資料分歧。 | 第 42 章 |
| Split charges | 分攤費用 | Cost categories 中把共用成本（例如共用網路或支援費）依比例或固定金額分攤到其他類別。 | 第 39 章（詳見第 43 章） |
| SPOF（Single Point of Failure） | 單點故障 | 一旦故障就會讓整個系統停擺的元件。 | 第 4 章 |
| Spot Fleet | Spot 機群 | 依目標容量與配置策略，從多個 Spot capacity pool 啟動並維持一組 instance。 | 第 17 章 |
| Spot Instances | Spot instance | 以大幅折扣使用 EC2 的閒置容量，AWS 需要回收時會提前兩分鐘通知中斷。 | 第 17 章 |
| SQS（Amazon Simple Queue Service） | 簡單佇列服務 | 受管的訊息佇列，以 visibility timeout 確保訊息被處理，保留 1 分鐘到 14 天（預設 4 天）。 | 第 4 章（詳見第 32 章） |
| SSE-C | 客戶提供金鑰的伺服器端加密 | S3 伺服器端加密的一種，由客戶在每次請求提供金鑰，AWS 不保存金鑰。 | 第 15 章 |
| SSE-KMS | KMS 金鑰伺服器端加密 | S3 以 KMS key 做伺服器端加密，可用 key policy 控制存取並由 CloudTrail 稽核金鑰使用。 | 第 11 章（詳見第 15 章） |
| SSE-S3 | S3 受管金鑰伺服器端加密 | S3 以自己管理的金鑰做伺服器端加密，新 object 預設套用、不另收費。 | 第 15 章 |
| SSM Agent | SSM 代理程式 | 安裝在 instance 或地端主機上，讓 Systems Manager 管理該節點的代理程式。 | 第 38 章 |
| SSRF（Server-Side Request Forgery） | 伺服器端請求偽造 | 攻擊者讓伺服器替它對內部位址發出請求，例如竊取 instance metadata 中的憑證；IMDSv2 可緩解。 | 第 17 章 |
| Stack | 堆疊 | CloudFormation 依一份 template 建立、作為一個單位管理的一組資源。 | 第 37 章 |
| StackSets（CloudFormation StackSets） | 堆疊集 | 把同一份 template 部署到多個帳號與 Region，可搭配 Organizations 自動部署到新帳號。 | 第 14 章（詳見第 37 章） |
| Stage（API Gateway） | 階段 | API 的一個已部署快照（例如 dev、prod），各自有設定、節流與 stage variables。 | 第 20 章 |
| Standard queue（SQS） | 標準佇列 | 幾乎無限吞吐、at-least-once 投遞、盡力排序的 SQS queue 類型。 | 第 32 章 |
| Stateful／Stateless firewall | 有狀態／無狀態防火牆 | stateful 會記住連線並自動放行回應流量（security group）；stateless 每個封包獨立判斷，回程要另開規則（NACL）。 | 第 3 章（詳見第 6 章） |
| Stateless application | 無狀態應用 | 伺服器不保存使用者 session 等狀態，任何一台都能處理任何請求，才能自由水平擴展。 | 第 4 章 |
| State Manager | 狀態管理員 | Systems Manager 持續讓節點維持指定狀態（例如安裝代理程式、設定），偏離時重新套用。 | 第 38 章 |
| Static stability | 靜態穩定 | 故障發生時不需要建立新資源或呼叫 control plane，就能靠已部署的容量繼續運作。 | 第 2 章（詳見第 34 章） |
| Step Functions（AWS Step Functions） | 工作流程編排服務 | 以 state machine 編排多個服務的 serverless workflow，內建 retry、catch、平行與等待。 | 第 4 章（詳見第 33 章） |
| Step scaling／Simple scaling | 分段擴展／簡單擴展 | 依 alarm 超出門檻的幅度分段調整容量；simple scaling 每次只做一個動作並等待 cooldown。 | 第 18 章 |
| Sticky session | 黏著連線 | load balancer 把同一個用戶端的請求持續送到同一個 target，會造成負載不均並妨礙擴縮。 | 第 10 章 |
| Storage Gateway（AWS Storage Gateway） | 儲存閘道 | 在地端部署的混合儲存閘道，以檔案、volume 或磁帶介面讓地端應用使用 AWS 儲存。 | 第 25 章 |
| Strangler fig | 絞殺榕模式 | 在舊系統前加一層路由，逐步把功能改由新服務處理，直到舊系統可以退役。 | 第 46 章 |
| Strong consistency | 強一致性 | 寫入完成後任何讀取都一定讀到最新值。 | 第 4 章 |
| Strongly consistent read | 強一致讀取 | DynamoDB 回傳所有先前成功寫入結果的讀取方式，耗用兩倍 RCU，GSI 不支援。 | 第 27 章 |
| STS（AWS Security Token Service） | 安全權杖服務 | 發出 role、聯合身份等臨時憑證（access key、secret、session token）的服務。 | 第 12 章（詳見第 13 章） |
| Subnet | 子網路 | VPC 中屬於單一 AZ 的一段 IP 範圍；AWS 每個 subnet 保留 5 個位址。 | 第 2 章（詳見第 5 章） |
| Subscription filter | 訂閱篩選器 | 把 CloudWatch Logs 即時串流到 Lambda、Kinesis Data Streams 或 Firehose 的設定。 | 第 36 章 |
| Subscription filter policy（SNS） | 訂閱過濾政策 | 讓 SNS 訂閱者只收到 message attribute 或內容符合條件的訊息。 | 第 32 章 |
| Systems Manager（AWS Systems Manager，SSM） | 系統管理員 | 管理 EC2 與地端節點的服務集合，包含 Session Manager、Run Command、Patch Manager、Automation、Parameter Store 等。 | 第 38 章 |

## T

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Tag policies | 標籤政策 | Organizations 的政策類型，規範 tag key 的大小寫與允許值，協助維持成本分攤與治理所需的標籤一致。 | 第 39 章（詳見第 43 章） |
| Target group | 目標群組 | load balancer 把流量送往的一組 target（instance、IP、Lambda 或 ALB），各自設定 health check。 | 第 7 章（詳見第 10 章） |
| Target tracking scaling | 目標追蹤擴展 | 設定一個 metric 目標值（例如 CPU 50%），ASG 自動增減容量讓指標維持在目標附近。 | 第 18 章 |
| Task definition | task 定義 | ECS 中描述 container image、CPU、記憶體、port、環境變數與 IAM role 的範本。 | 第 21 章 |
| Task role／Task execution role | task 角色／task 執行角色 | ECS 的 task role 給 container 內應用程式呼叫 AWS；task execution role 給 ECS agent 拉 image、寫日誌、讀 secrets。 | 第 12 章（詳見第 21 章） |
| Task token | 任務權杖 | Step Functions callback 模式中交給外部系統的權杖，外部完成後以它回報結果，讓流程繼續。 | 第 33 章 |
| TCO（Total Cost of Ownership） | 總持有成本 | 比較地端與雲端時，把硬體、機房、電力、授權、人力等直接與間接成本全部納入計算。 | 第 44 章 |
| TCP／UDP | 傳輸控制協定／使用者資料包協定 | TCP 建立連線並保證可靠、有序傳送；UDP 無連線、不保證送達但延遲低。 | 第 3 章 |
| Termination protection | 終止保護 | 防止 CloudFormation stack 或 EC2 instance 被誤刪的設定。 | 第 37 章 |
| Textract（Amazon Textract） | 文件擷取 | 從掃描文件中擷取文字、表格與表單欄位的服務。 | 第 47 章 |
| Three-way handshake | 三次握手 | TCP 建立連線的 SYN、SYN-ACK、ACK 三個步驟，每次新連線都多花一個 RTT。 | 第 3 章 |
| Throttling | 節流 | 服務在請求超過速率上限時拒絕部分請求（例如 HTTP 429、ThrottlingException），用戶端應以退避重試。 | 第 19 章（詳見第 35 章） |
| Throughput | 吞吐量 | 單位時間實際完成的資料量或請求數。 | 第 3 章 |
| Timestream（Amazon Timestream） | 時間序列資料庫 | 受管時間序列資料庫；Timestream for LiveAnalytics 自 2025-06-20 起不再開放新客戶，新工作負載可用 Timestream for InfluxDB。 | 第 29 章 |
| TLS termination | TLS 終止 | 在 load balancer 或 CloudFront 解開 TLS，後端可用 HTTP 或重新加密。 | 第 3 章 |
| TLS（Transport Layer Security） | 傳輸層安全 | 以憑證驗證伺服器並加密傳輸內容的協定，HTTPS 就是 HTTP over TLS。 | 第 3 章 |
| Token bucket | 權杖桶 | 以固定速率補充 token、允許累積到 burst 上限的限流演算法，API Gateway 用它做 throttling。 | 第 35 章 |
| Tokenization | 代碼化 | 把信用卡號等敏感資料換成無意義的代碼，原始資料只存在受嚴格保護的系統中，以縮小合規範圍。 | 第 50 章 |
| Token（LLM） | 詞元 | 模型處理文字的基本單位，約為一個字詞片段；LLM 的計費、配額與 context window 都以 token 計算。 | 第 47 章 |
| Traffic Mirroring（VPC Traffic Mirroring） | 流量鏡像 | 把 ENI 的完整封包複製一份送到分析設備，用於深度檢查與鑑識。 | 第 6 章 |
| Transactional outbox | 交易式寄件匣 | 把業務資料與待發事件寫在同一個資料庫交易中，再由 relay 讀出發布，解決雙寫問題。 | 第 29 章（詳見第 33 章） |
| Transcribe／Translate（Amazon Transcribe、Amazon Translate） | 語音轉文字／機器翻譯 | Transcribe 把語音轉成文字；Translate 做機器翻譯。 | 第 47 章 |
| Transfer Family（AWS Transfer Family） | 受管檔案傳輸 | 受管的 SFTP、FTPS、FTP 與 AS2 伺服器，檔案直接存入 S3 或 EFS。 | 第 25 章 |
| Transform（AWS Transform） | AI 遷移與現代化服務 | 提供探索收集、VMware 環境分析、dependency mapping 與 wave 規劃等遷移與現代化功能，承接 Migration Hub 停止開放新客戶後的需求；功能範圍仍在快速變動。 | 第 44 章 |
| Transit Gateway（AWS Transit Gateway，TGW） | 轉送閘道 | Regional 的雲端路由器，以 hub-and-spoke 連接大量 VPC、VPN 與 DX，用多張 route table 做分段。 | 第 7 章 |
| Transit VIF | 轉送虛擬介面 | Direct Connect 經 DX gateway 連到 Transit Gateway 的虛擬介面。 | 第 8 章 |
| Trusted Advisor（AWS Trusted Advisor） | 受信任顧問 | 依成本、效能、安全、容錯、服務配額與營運卓越檢查帳號並提出建議；完整檢查需 Business 以上支援方案。 | 第 36 章（詳見第 38 章） |
| Trust policy | 信任政策 | 附加在 role 上、定義誰可以 assume 這個 role 的 resource-based policy。 | 第 12 章（詳見第 13 章） |
| TTL（Time To Live） | 存活時間 | 快取或 DNS 記錄可被保留的秒數，到期後必須重新查詢；也指 DynamoDB 自動刪除過期 item 的功能。 | 第 3 章 |

## U

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Unscored questions | 不計分題 | AWS 用來試驗新題目、混在正式題目中無法分辨的題目；SAA 有 15 題、SAP-C02 有 10 題。 | 第 1 章 |
| UpdateReplacePolicy | 更新取代政策 | CloudFormation 屬性，決定資源因更新而被取代時舊資源要刪除、保留或建 snapshot。 | 第 37 章 |
| Usage plan | 使用量方案 | API Gateway 依 API key 為每個用戶端設定 throttling 速率與每日／每月配額。 | 第 20 章 |
| User data | 使用者資料 | instance 第一次開機時執行的腳本或 cloud-init 設定，用來安裝與設定軟體。 | 第 17 章 |

## V

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Valkey | Valkey 快取引擎 | Redis 的開源分支，相容 Redis OSS 協定；ElastiCache 與 MemoryDB 都支援。 | 第 28 章 |
| Versioning（S3 Versioning） | 版本控制 | 保留 object 的每一個版本，刪除只加上 delete marker，可復原誤刪或覆寫。 | 第 22 章 |
| VIF（Virtual Interface） | 虛擬介面 | Direct Connect 連線上的邏輯介面，分為 private、public 與 transit 三種。 | 第 8 章 |
| Virtual private gateway（VGW） | 虛擬私有閘道 | 附加在單一 VPC 上、作為 Site-to-Site VPN 或 Direct Connect 在 AWS 端終點的閘道。 | 第 8 章 |
| Visibility timeout | 可見性逾時 | SQS 訊息被取走後對其他 consumer 隱藏的時間，預設 30 秒、最長 12 小時，應大於處理時間。 | 第 19 章（詳見第 32 章） |
| VMware Cloud on AWS／Amazon EVS | AWS 上的 VMware | 在 AWS 上執行 VMware 環境的方案，供 relocate 使用；VMware Cloud on AWS 現由 Broadcom 銷售，Amazon EVS 則在你自己的 VPC 以 EC2 裸機執行 VMware Cloud Foundation。 | 第 44 章 |
| Volume Gateway／Tape Gateway | 磁碟區閘道／磁帶閘道 | Volume Gateway 以 iSCSI 提供 cached 或 stored volume；Tape Gateway 以 VTL 取代實體磁帶備份。 | 第 25 章 |
| VPC（Amazon Virtual Private Cloud） | 虛擬私有雲 | 你在某個 Region 中邏輯隔離的私有網路，自訂 CIDR、subnet、路由與閘道。 | 第 2 章（詳見第 5 章） |
| VPC endpoint | VPC 端點 | 讓 VPC 不經 Internet 私有存取 AWS 服務或 PrivateLink 服務的連接點，分為 gateway 與 interface 等類型。 | 第 6 章 |
| VPC Lattice（Amazon VPC Lattice） | 應用層服務網路 | 跨 VPC 與帳號的應用層服務網路，處理服務探索、L7 路由與以 IAM 為基礎的 auth policy。 | 第 7 章 |
| VPC peering | VPC 對等連線 | 兩個 VPC 之間的一對一私有連線，可跨帳號與 Region，不支援遞移路由且 CIDR 不能重疊。 | 第 6 章（詳見第 7 章） |
| VPC sharing | VPC 共享 | 擁有者帳號以 AWS RAM 把 subnet 共享給同組織的參與者帳號，各自在共享 subnet 中建立資源。 | 第 5 章（詳見第 41 章） |
| VPN CloudHub（AWS VPN CloudHub） | VPN 中樞 | 多個地端站點透過同一個 VGW 的 VPN 連線彼此互通的 hub-and-spoke 架構。 | 第 8 章 |

## W

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| WAF（AWS WAF） | 網頁應用程式防火牆 | 依規則檢查 HTTP 請求並允許、封鎖、計數或挑戰，可掛在 CloudFront、ALB、API Gateway、AppSync、Cognito。 | 第 2 章（詳見第 16 章） |
| Warm pool | 暖機池 | ASG 預先準備好已初始化、處於 stopped、hibernated 或 running 狀態的 instance，擴展時更快上線。 | 第 18 章 |
| Warm standby | 暖備援 | DR 策略之一：備援 Region 持續執行縮小規模的完整環境，災難時擴展即可接手，RTO 為分鐘級。 | 第 34 章 |
| Wavelength（AWS Wavelength） | 5G 邊緣運算 | 把 AWS 運算部署在電信業者 5G 網路內，提供行動裝置極低延遲。 | 第 2 章 |
| Wave planning | 波次規劃 | 依相依關係、風險與業務時程把遷移分成多個 wave，先易後難、Wave 0 先建基礎設施。 | 第 44 章 |
| Web ACL | Web 存取控制清單 | WAF 中依 priority 依序評估 rule 並套用到受保護資源的規則集合。 | 第 16 章 |
| WebSocket API | WebSocket API | API Gateway 維持與用戶端長連線、可由伺服器主動推送訊息的 API 類型。 | 第 20 章 |
| Weighted routing | 加權路由 | Route 53 依設定的權重比例回應多筆記錄，常用於 canary 與藍綠切換。 | 第 9 章 |
| Well-Architected Framework（AWS Well-Architected Framework） | 架構完善框架 | AWS 的架構最佳實務框架，包含營運卓越、安全、可靠性、效能效率、成本最佳化、永續六大支柱。 | 第 2 章 |
| Well-Architected Tool（AWS Well-Architected Tool） | 架構完善審查工具 | 依 Well-Architected 問題逐項審查 workload、記錄高與中風險項目並追蹤改善計畫的工具。 | 第 2 章（詳見第 38 章） |
| WLM（Workload Management） | 工作負載管理 | Redshift 依佇列與優先順序分配查詢資源的機制。 | 第 30 章 |
| WORM（Write Once Read Many） | 一次寫入、多次讀取 | 資料寫入後在保留期內不能修改或刪除的保存方式，常為法規要求。 | 第 16 章 |
| Write forwarding | 寫入轉送 | Aurora Global Database 的 secondary Region 收到寫入時代為轉送到 primary Region 執行。 | 第 26 章 |
| Write-local | 就近寫入 | 每個 Region 都能寫入任何資料、彼此非同步複寫的多 Region 模式，必須處理寫入衝突。 | 第 42 章 |
| Write sharding | 寫入分片 | 在 partition key 後加上隨機或計算出的後綴，把熱門 key 的寫入分散到多個 partition。 | 第 27 章 |
| Write-through／Write-behind | 直寫／延後寫入 | write-through 寫資料庫時同步更新 cache；write-behind 先寫 cache 再非同步寫資料庫，可能遺失資料。 | 第 27 章（詳見第 28 章） |

## X

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| X-Forwarded-For | 轉送來源標頭 | ALB 加在請求中的 HTTP header，記錄原始 client IP，後端要讀它才知道使用者位址。 | 第 10 章 |
| X-Ray（AWS X-Ray） | 分散式追蹤服務 | 分散式追蹤服務，記錄請求經過各服務的 segment 與延遲，產生 service map。 | 第 36 章 |

## Z

| 英文術語 | 中文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| Zero-ETL integration | 零 ETL 整合 | 把 Aurora、RDS、DynamoDB 等的資料自動近即時複寫到 Redshift 等分析服務，不需自建 ETL pipeline。 | 第 26 章 |
| Zonal shift | 區域轉移 | 透過 ARC 暫時把流量從某個有問題的 AZ 移開；zonal autoshift 讓 AWS 偵測到 AZ 問題時自動執行。 | 第 9 章（詳見第 34 章） |
| Zone apex | 區域頂點 | 網域本身（例如 example.com，不含子網域）；這裡不能放 CNAME，要用 alias record。 | 第 9 章 |
| Zone of trust | 信任範圍 | IAM Access Analyzer 判斷「外部」的邊界，可設為帳號或整個組織。 | 第 12 章 |

## 中文術語

以下是書中以中文為主、沒有固定英文服務名稱的解題與設計概念。

| 中文術語 | 英文 | 一句話定義 | 首次說明 |
|---|---|---|---|
| 刪去法 | Elimination | 依序刪去違反明確限制、營運負擔較高的選項，再用最佳化目標比較剩下的選項。 | 第 1 章 |
| 最佳化目標 | Optimization goal | 題目中決定答案的關鍵字，例如 MOST cost-effective、LEAST operational overhead、highly available。 | 第 1 章 |
| 兩輪作答 | Two-pass strategy | 第一輪每題都作答並標記沒把握的題目，第二輪只回頭檢查標記題的考場時間策略。 | 第 1 章 |
| 過度設計 | Over-engineering | 選項功能正確但超出需求、成本或營運負擔更高，是常見的錯誤選項類型。 | 第 1 章 |
| 削峰 | Peak shaving | 用 queue 等緩衝吸收短時間的流量尖峰，讓後端以穩定速度處理。 | 第 4 章 |
