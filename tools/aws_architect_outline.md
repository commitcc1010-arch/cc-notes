# AWS Solutions Architect 雙證全攻略：章節大綱

每一列：章號｜檔案路徑（相對 `AWS Solutions Architect/`）｜標題｜舊版對應章（`/tmp/aws_old/chapters/chNNN.md`）｜題數｜必須涵蓋的重點。
全書以虛構公司 **Wanderly**（線上旅遊訂房平台）作為貫穿案例：從一台 EC2 的新創，成長為多帳號、多 Region、要遷移舊資料中心並導入 AI 助理的企業。

## Part 0　零背景基礎（`Part 0 - 零背景基礎/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 1 | 01 - 怎麼讀這本書與考試地圖.md | 怎麼讀這本書：SAA／SAP 考什麼、怎麼解題 | 1 | 6 | SAA-C03 與 SAP-C02 考試形式（題數、時間、計分 100–1000、及格 720／750、未計分題、單選／多選）、四個 domain 與比重、task 清單、兩者差異（單一 workload vs 組織複雜度）、題目關鍵字（MOST cost-effective、LEAST operational overhead、highly available…）、刪去法與讀題順序、時間管理、Wanderly 案例介紹、全書路線圖與 30 天 SAA／45 天 SAP／12 週零背景讀書計畫。題目為「示範解題」：每題附逐步思考。 |
| 2 | 02 - 雲端與 AWS 全球基礎設施.md | 雲端是什麼：Region、AZ、Edge 與責任分擔 | 2, 10 | 10 | 雲端 vs 自建機房、IaaS/PaaS/SaaS、CapEx/OpEx、Region／AZ／Edge location／Regional edge cache／Local Zones／Wavelength／Outposts、如何選 Region（合規、延遲、服務可用性、價格）、global vs regional vs zonal 服務、control plane vs data plane、Shared Responsibility Model、Well-Architected 六大 pillars、AWS 帳號、root user、計費基本觀念（按用量、data transfer 方向）、AWS Console／CLI／SDK／API。 |
| 3 | 03 - 網路基礎速成.md | 網路基礎速成：IP、CIDR、路由、DNS、TCP 與 HTTP | 4, 5 | 10 | IPv4 位址、private 範圍（RFC1918）、CIDR 計算（/16 /24 /28 有幾個位址）、subnet、routing table 與 longest prefix match、NAT、IPv6 基本、port、TCP vs UDP、three-way handshake、TLS 與憑證、HTTP/HTTPS、L4 vs L7、DNS 解析流程（resolver、authoritative、TTL、A/AAAA/CNAME 記錄）、stateful vs stateless 防火牆、latency vs bandwidth。全部從零講。 |
| 4 | 04 - 儲存資料庫與可靠性基礎.md | 儲存、資料庫與可靠性基礎 | 3, 6, 7, 8, 9 | 10 | VM／container／serverless 差異、block／file／object storage、relational vs NoSQL vs cache vs data warehouse、ACID、strong vs eventual consistency、replication 同步／非同步、availability vs durability（幾個 9 的意義）、scale up vs scale out、elasticity、stateless 設計、SLA／SLO、RTO／RPO、single point of failure、loose coupling、同步 vs 非同步通訊。 |

## Part 1　Networking（`Part 1 - Networking/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 5 | 05 - VPC 從零到可上線.md | VPC 從零到可上線：CIDR、Subnet、Route Table、IGW 與 NAT | 11, 12, 13 | 16 | **（試寫章，作為全書範本）** VPC、CIDR 規劃與 secondary CIDR、AWS 保留 5 個位址、subnet 與 AZ、public／private subnet 的真正定義、route table（main／custom、local route）、Internet Gateway、public IP／Elastic IP、NAT Gateway（zonal、每 AZ 一台、費用）、NAT instance、egress-only IGW、default VPC、IPAM（SAP）、DHCP option set、DNS hostnames／support、三層式架構範例。 |
| 6 | 06 - 流量控制與私有存取.md | 流量控制與私有存取：Security Group、NACL、VPC Endpoint 與 Flow Logs | 13, 14 | 16 | SG（stateful、只有 allow、可參照其他 SG）、NACL（stateless、規則編號、ephemeral ports）、兩者比較與除錯、Gateway endpoint（S3、DynamoDB、免費、route table）、Interface endpoint（PrivateLink、ENI、private DNS、收費）、endpoint policy、`aws:SourceVpce` bucket policy、VPC Flow Logs 欄位與用途、Reachability Analyzer、Network Access Analyzer。 |
| 7 | 07 - 多 VPC 互連.md | 多 VPC 互連：Peering、Transit Gateway、PrivateLink 與 VPC Lattice | 15 | 16 | VPC peering（非遞移、不能重疊、跨帳號跨 Region）、Transit Gateway（attachments、route tables、segmentation、跨 Region peering、appliance mode）、PrivateLink endpoint service（NLB／GWLB 背後、可解決 CIDR 重疊）、VPC Lattice、AWS RAM 共享 subnet、規模比較與成本、選型決策樹。 |
| 8 | 08 - 混合雲連線.md | 混合雲連線：VPN、Direct Connect 與 Hybrid DNS | 19, 20 | 16 | Site-to-Site VPN（VGW vs TGW、兩條 tunnel、BGP、accelerated VPN）、Client VPN、Direct Connect（dedicated vs hosted、private／public／transit VIF、DX Gateway、LAG、MACsec、DX + VPN 備援、resiliency 建議）、Route 53 Resolver inbound／outbound endpoints 與 forwarding rules、跨帳號共享 resolver rules、選型與高可用設計。 |
| 9 | 09 - Route 53 與 DNS 流量管理.md | Route 53：DNS 與流量管理 | 16 | 16 | Hosted zone（public／private）、record types、alias vs CNAME（zone apex）、TTL、routing policies（simple、weighted、latency、failover、geolocation、geoproximity、multivalue、IP-based）、health checks（endpoint、calculated、CloudWatch alarm）、active-active vs active-passive、DNSSEC、domain registration、private hosted zone 關聯跨帳號 VPC。 |
| 10 | 10 - Elastic Load Balancing.md | Elastic Load Balancing：ALB、NLB 與 GWLB | 18 | 16 | 為什麼需要 LB、listener／target group／health check、ALB（L7、path／host routing、redirect、fixed response、authentication、sticky sessions、Lambda target）、NLB（L4、static IP／EIP、極低延遲、保留 client IP、TLS passthrough、PrivateLink）、GWLB（GENEVE、inspection appliances）、cross-zone load balancing、connection draining／deregistration delay、SNI、多憑證、X-Forwarded-For、Proxy protocol、選型表。 |
| 11 | 11 - CloudFront 與 Global Accelerator.md | 邊緣加速：CloudFront 與 Global Accelerator | 17 | 16 | CDN 原理、CloudFront distribution／origin／behavior、cache key 與 cache policy／origin request policy、TTL、invalidation、OAC（取代 OAI）存取 S3、signed URL vs signed cookie、geo restriction、field-level encryption、Lambda@Edge vs CloudFront Functions、origin failover／origin group、HTTPS 與 ACM（us-east-1）、Global Accelerator（anycast static IP、TCP/UDP、endpoint weights、快速 failover）、CloudFront vs GA 比較。 |

## Part 2　Security 與 Identity（`Part 2 - Security/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 12 | 12 - IAM 基礎與 Policy 評估.md | IAM：身份、權限與 Policy 評估邏輯 | 21, 22 | 16 | Root user 保護、IAM user／group／role、MFA、access key 風險、policy JSON 結構（Effect、Action、Resource、Condition、Principal）、identity-based vs resource-based、managed vs inline、評估邏輯（預設 deny、explicit deny 優先、SCP／permission boundary／session policy 交集）、常用 condition keys、instance profile／service role、least privilege、IAM Access Analyzer、credential report、ABAC vs RBAC。 |
| 13 | 13 - 跨帳號存取與身份聯合.md | 跨帳號存取、身份聯合與 Cognito | 23, 24, 82 | 16 | STS AssumeRole、trust policy、external ID 與 confused deputy、跨帳號 S3 存取兩種方式比較、SAML 2.0／OIDC federation、IAM Identity Center（permission sets、外部 IdP、AD Connector）、AWS Directory Service（Managed AD、AD Connector、Simple AD）、Cognito user pools vs identity pools、web identity federation、API／App 登入流程。 |
| 14 | 14 - Organizations 與多帳號治理.md | Organizations、SCP 與 Control Tower | 25, 26 | 16 | 為什麼多帳號、Organizations、OU、management account、SCP（只限制不授權、不影響 management account、deny list vs allow list 策略）、RCP（resource control policies）、tag policies、backup policies、consolidated billing、delegated administrator、Control Tower（landing zone、guardrails／controls：preventive／detective／proactive、Account Factory）、permission boundaries 授權開發者自建 role。 |
| 15 | 15 - 加密金鑰與機密管理.md | 加密與機密：KMS、CloudHSM、Secrets Manager 與 ACM | 27, 28 | 16 | 加密基礎（at rest／in transit、對稱／非對稱）、KMS keys（AWS owned／AWS managed／customer managed）、envelope encryption 與 data key、key policy + grants、跨帳號使用 KMS key、自動輪替、multi-Region keys、imported key material、CloudHSM 使用時機、S3 SSE-S3／SSE-KMS／DSSE-KMS／SSE-C／client-side、S3 Bucket Key、Secrets Manager（自動 rotation、跨 Region replication）vs SSM Parameter Store（SecureString、tiers）、ACM（公開／私有憑證、自動更新、region 限制）。 |
| 16 | 16 - 邊界防護與威脅偵測.md | 邊界防護與威脅偵測：WAF、Shield、GuardDuty 與安全稽核 | 29, 30, 31 | 16 | WAF（web ACL、managed rules、rate-based rules、可掛在 CloudFront／ALB／API GW／AppSync／Cognito）、Shield Standard vs Advanced（DRT、成本保護）、Firewall Manager、Network Firewall（stateful/stateless、domain filtering）、Security Groups 與以上的分層、GuardDuty、Inspector、Macie、Detective、Security Hub、CloudTrail（management／data events、organization trail、log file validation）、AWS Config（rules、conformance packs、remediation）、Audit Manager、Artifact、資料分類與 retention（S3 Object Lock、Glacier Vault Lock）。 |

## Part 3　Compute（`Part 3 - Compute/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 17 | 17 - EC2 深入.md | EC2 深入：Instance、AMI、儲存與購買方式 | 32, 33, 68 | 16 | Instance families 命名規則、Graviton、burstable（T 系列 credits）、AMI（跨 Region copy、共享、golden AMI）、user data 與 instance metadata（IMDSv2）、EBS-backed vs instance store、hibernate、placement groups（cluster／spread／partition）、ENI／ENA／EFA、Elastic IP、On-Demand／Reserved Instances／Savings Plans／Spot（中斷通知、Spot Fleet）／Dedicated Hosts／Dedicated Instances／Capacity Reservations、tenancy 與授權。 |
| 18 | 18 - Auto Scaling 與高可用 Web Tier.md | Auto Scaling 與高可用 Web Tier | 34, 35 | 16 | Launch template、ASG（min／max／desired）、跨多 AZ、health check（EC2 vs ELB）、scaling policies（target tracking、step、simple、scheduled、predictive）、cooldown 與 warm-up、lifecycle hooks、warm pools、instance refresh、termination policy、ALB + ASG 標準架構、session state 外部化、mixed instances policy 與 Spot。 |
| 19 | 19 - Lambda 與 Serverless 運算.md | Lambda：Serverless 運算 | 36 | 16 | 事件驅動模型、invocation types（sync／async／event source mapping）、記憶體與 CPU、15 分鐘上限、/tmp、concurrency（reserved、provisioned、account limit、throttling）、cold start 與 SnapStart、VPC 中的 Lambda（Hyperplane ENI、NAT 需求）、layers、container image、destinations 與 DLQ、Lambda + SQS／Kinesis batch 與 partial failure、function URLs、權限（execution role vs resource policy）、費用模型、何時不適合 Lambda。 |
| 20 | 20 - API Gateway 與 Serverless API.md | API Gateway 與 Serverless API 設計 | 37 | 16 | REST API vs HTTP API vs WebSocket API、endpoint types（edge-optimized、regional、private）、stages、throttling 與 usage plans／API keys、caching、authorizers（IAM、Cognito、Lambda）、integration types（Lambda proxy、HTTP、AWS service）、request validation、CORS、29 秒整合逾時（可調整說明）、mutual TLS、AppSync（GraphQL）簡介、典型 serverless 架構（API GW + Lambda + DynamoDB）。 |
| 21 | 21 - Containers 與 Managed Platforms.md | Containers 與受管平台：ECS、EKS、Fargate、Beanstalk 與 Batch | 38, 39, 40 | 16 | Container 是什麼、ECR、ECS（cluster、task definition、service、task role vs execution role、launch types EC2 vs Fargate、capacity providers、service auto scaling、ALB 整合）、EKS（何時選、node groups、Fargate profiles、Karpenter）、ECS Anywhere／EKS Anywhere、App Runner、Elastic Beanstalk（環境、部署策略）、AWS Batch、HPC（ParallelCluster、EFA）、選型決策表。 |

## Part 4　Storage（`Part 4 - Storage/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 22 | 22 - S3 基礎與安全.md | S3 基礎：Object 模型、一致性與存取控制 | 41 | 16 | Bucket／object／key、strong read-after-write consistency、object 大小上限與 multipart upload、versioning、bucket policy vs IAM policy vs ACL（Object Ownership、ACL disabled）、Block Public Access、presigned URL、encryption 預設、S3 Access Points、static website hosting、CORS、event notifications（SNS／SQS／Lambda／EventBridge）、S3 Transfer Acceleration、byte-range fetch、prefix 效能、S3 Select（已不推薦，說明替代）、Requester Pays、Object Lambda。 |
| 23 | 23 - S3 儲存類別生命週期與複寫.md | S3 儲存類別、生命週期、複寫與資料保護 | 42 | 16 | 各 storage class（Standard、Intelligent-Tiering、Standard-IA、One Zone-IA、Glacier Instant／Flexible／Deep Archive、Express One Zone）比較表（耐久度、可用 AZ、最短存放天數、最小計費大小、取回時間與費用）、lifecycle rules、CRR／SRR 與 RTC、replication 不會複製既有物件（Batch Replication）、Object Lock（governance／compliance、legal hold）、MFA delete、S3 Batch Operations、Storage Lens、S3 inventory。 |
| 24 | 24 - EBS EFS 與 FSx.md | Block 與 File Storage：EBS、EFS 與 FSx | 33, 43 | 16 | EBS volume types（gp3、gp2、io2 Block Express、st1、sc1）與 IOPS／throughput、AZ 綁定、snapshots（增量、跨 Region copy、Fast Snapshot Restore、Recycle Bin、archive tier）、Multi-Attach、EBS encryption、instance store；EFS（NFS、多 AZ、performance／throughput modes、storage classes、lifecycle、access points）；FSx for Windows File Server、Lustre（S3 整合、scratch vs persistent）、NetApp ONTAP、OpenZFS；選型表。 |
| 25 | 25 - 資料移轉與混合儲存.md | 資料移轉與混合儲存：Storage Gateway、DataSync、Transfer Family 與 Snow | 44 | 16 | Storage Gateway（S3 File、FSx File、Volume cached／stored、Tape）、DataSync（agent、排程、驗證、跨 Region／帳號）、Transfer Family（SFTP／FTPS／FTP／AS2）、Snowball Edge 與 Snowcone 現況（注意新客戶可用性變化，寫法要保守）、線上 vs 離線傳輸計算（頻寬×時間）、DX 搭配、S3 Transfer Acceleration、選型決策。 |

## Part 5　Database 與 Analytics（`Part 5 - Database/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 26 | 26 - RDS 與 Aurora.md | RDS 與 Aurora：受管關聯式資料庫 | 45, 46 | 16 | RDS engines、Multi-AZ（instance vs cluster deployment、同步複寫、failover 行為、DNS）、read replicas（非同步、跨 Region、可 promote）、備份（automated、PITR、snapshot、跨 Region）、加密（只能建立時啟用、snapshot 重建）、RDS Proxy、IAM DB auth、parameter groups、Aurora 架構（6 份副本 3 AZ、共享儲存、reader endpoint、custom endpoint、最多 15 replicas）、Aurora Serverless v2、Global Database（RPO 秒級、managed failover）、Backtrack、cloning、Blue/Green deployments、選型。 |
| 27 | 27 - DynamoDB.md | DynamoDB：Serverless NoSQL | 47 | 16 | 資料模型（table、item、partition key、sort key）、存取模式設計、熱分割、capacity modes（on-demand vs provisioned + auto scaling）、RCU／WCU 計算、eventually vs strongly consistent reads、LSI vs GSI、TTL、Streams、global tables、transactions、DAX、PITR 與 on-demand backup、export to S3、fine-grained access control、item 大小 400KB、與 S3 搭配存大物件、single-table design 概念。 |
| 28 | 28 - ElastiCache 與快取策略.md | ElastiCache 與快取策略 | 48 | 16 | 為什麼快取、cache-aside／lazy loading、write-through、TTL、cache stampede 與 thundering herd、eviction、Redis OSS／Valkey vs Memcached 比較、cluster mode、replication 與 Multi-AZ auto failover、persistence、session store、leaderboard、ElastiCache Serverless、MemoryDB（durable）、DAX vs ElastiCache、CloudFront 作為快取層、cache 不是 source of truth。 |
| 29 | 29 - Purpose-built 資料庫.md | Purpose-built 資料庫：選對資料庫 | 51 | 16 | DocumentDB、Neptune、Keyspaces、Timestream、OpenSearch Service、MemoryDB、QLDB 已停止（改用 Aurora PostgreSQL 等，寫法保守）、Redshift 定位、選型決策流程（存取模式→一致性→規模→營運）、從 Oracle／SQL Server 選型、license 考量。 |
| 30 | 30 - 資料湖與分析.md | 資料湖與分析：S3、Glue、Athena、Redshift 與 EMR | 49 | 16 | Data lake vs data warehouse、S3 為基礎的 lake、分區與 columnar 格式（Parquet）、Glue（Data Catalog、crawlers、ETL jobs、DataBrew）、Athena（serverless SQL、按掃描量計費、federated query）、Lake Formation（細粒度權限、跨帳號共享）、Redshift（RA3、Serverless、Spectrum、concurrency scaling、data sharing）、EMR（Spark／Hadoop、EMR Serverless、Spot 用法）、QuickSight、成本最佳化。 |
| 31 | 31 - Streaming 與即時資料管線.md | Streaming 與即時資料管線：Kinesis、MSK 與 Flink | 50, 54 | 16 | Batch vs stream、Kinesis Data Streams（shard、partition key、順序、retention、on-demand vs provisioned、enhanced fan-out、KCL）、Data Firehose（near real-time、buffer、轉換、目的地）、Managed Service for Apache Flink、MSK 與 MSK Serverless、Kinesis vs SQS vs MSK 比較、IoT Core 簡介、典型 clickstream 管線。 |

## Part 6　Integration 與分散式系統（`Part 6 - Integration/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 32 | 32 - SQS SNS 與 EventBridge.md | 非同步解耦：SQS、SNS、EventBridge 與 Amazon MQ | 52, 53 | 16 | 為什麼解耦、SQS standard vs FIFO（message group ID、dedup、吞吐）、visibility timeout、long polling、DLQ 與 redrive、delay queue、message 大小 256KB 與 extended client、以 queue 深度 scale ASG、SNS topics、fan-out（SNS→多個 SQS）、message filtering、SNS FIFO、EventBridge（event bus、rules、schema registry、archive／replay、跨帳號、Pipes、Scheduler）、Amazon MQ（何時選：既有 JMS／AMQP）、選型表。 |
| 33 | 33 - Workflow 與分散式模式.md | Step Functions 與分散式系統模式 | 55–60 | 16 | Step Functions（Standard vs Express、states、retry／catch、wait for callback／task token、human approval、Map 與 Distributed Map、service integrations）、retry 與 exponential backoff + jitter、timeout、idempotency 與 idempotency key、at-least-once 與 exactly-once 的錯覺、saga、transactional outbox、circuit breaker、bulkhead、backpressure、stateless vs stateful、sync vs async。 |

## Part 7　Reliability、Operations 與 Cost（`Part 7 - Reliability Operations Cost/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 34 | 34 - 高可用與災難復原.md | 高可用與災難復原：Multi-AZ、Multi-Region 與 DR 策略 | 61, 62, 63, 77 | 16 | Fault domain（instance、AZ、Region）、Multi-AZ 設計、static stability、四種 DR 策略（backup & restore、pilot light、warm standby、multi-site active-active）與 RTO／RPO／成本比較、AWS Backup（plans、vault、vault lock、跨 Region／跨帳號 copy、restore testing）、Elastic Disaster Recovery、各服務的跨 Region 複寫能力（S3 CRR、Aurora Global、DynamoDB global tables、EBS snapshot copy）、Route 53 ARC、failover 演練與 game day。 |
| 35 | 35 - 效能擴展與優雅降級.md | 效能擴展、配額與優雅降級 | 64, 65 | 16 | 讀寫擴展手段（cache、read replica、sharding、queue 削峰）、水平擴展前提、service quotas 與 Service Quotas 服務、API throttling 與 429／ThrottlingException、retry 與 token bucket、load shedding、graceful degradation、bulkhead、cell-based architecture、shuffle sharding、效能測試與瓶頸分析、Compute Optimizer 簡介。 |
| 36 | 36 - 監控與可觀測性.md | 監控與可觀測性：CloudWatch、X-Ray 與 CloudTrail | 66, 67 | 16 | Metrics（standard vs detailed、custom、high resolution）、CloudWatch agent（memory／disk 需 agent）、alarms（composite、anomaly detection）、Logs（log groups、retention、metric filters、subscription filters、Logs Insights）、dashboards、cross-account observability、X-Ray／ADOT 與 tracing、CloudWatch Synthetics、RUM、Container Insights、EventBridge 搭配、CloudTrail vs CloudWatch vs Config 差異、Health Dashboard、Trusted Advisor。 |
| 37 | 37 - IaC 與部署策略.md | Infrastructure as Code 與部署策略 | 72, 73, 74 | 16 | 為什麼 IaC、CloudFormation（template、stack、parameters、outputs、change sets、drift detection、rollback、DeletionPolicy、StackSets、nested stacks、custom resources）、CDK、SAM、CodePipeline／CodeBuild／CodeDeploy、部署策略（all-at-once、rolling、rolling with batch、immutable、blue/green、canary、linear）、各服務如何做 blue/green（ECS、Lambda alias、Beanstalk、Route 53 weighted）、feature flags（AppConfig）、Service Catalog。 |
| 38 | 38 - 營運自動化與持續改善.md | 營運自動化：Systems Manager、事件驅動修復與持續改善 | 75, 76, 78 | 16 | SSM agent、Session Manager（取代 bastion）、Run Command、Patch Manager、State Manager、Automation runbooks、Parameter Store、Inventory、OpsCenter、Fleet Manager；EventBridge + Lambda／SSM 自動修復、Config remediation；營運卓越：runbook／playbook、事後檢討、Well-Architected Tool、Trusted Advisor、Health 事件自動化。 |
| 39 | 39 - 成本最佳化.md | 成本最佳化：計價模型、購買方式與成本治理 | 68, 69, 70, 71, 85 | 16 | 成本組成（compute、storage、data transfer）、data transfer 規則（進免費、跨 AZ、跨 Region、到 Internet、NAT 處理費、VPC endpoint 省錢）、RI vs Savings Plans（Compute／EC2 Instance／SageMaker）比較、Spot 使用情境、rightsizing、Compute Optimizer、S3 與 EBS 成本（gp2→gp3、snapshot 清理）、資料庫成本（Aurora I/O-Optimized、Serverless）、Cost Explorer、Budgets（actions）、Cost Anomaly Detection、CUR／Data Exports、cost allocation tags、Billing Conductor、chargeback／showback。 |

## Part 8　SAP 企業架構（`Part 8 - Enterprise SAP/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 40 | 40 - Landing Zone 與多帳號架構.md | Landing Zone 與多帳號架構設計 | 79, 81, 82 | 16 | 帳號策略（workload、環境、security／log archive／audit／shared services／network 帳號）、OU 設計、Control Tower 進階（Account Factory for Terraform、customizations）、集中化日誌（organization trail、Config aggregator、S3 log archive、Object Lock）、集中安全（delegated admin for GuardDuty／Security Hub）、跨帳號授權模式、break-glass、tag 治理、新帳號 baseline 自動化。 |
| 41 | 41 - 企業級網路架構.md | 企業級網路架構：集中 egress、inspection 與大規模 hybrid | 20, 80 | 16 | Hub-and-spoke TGW、集中 egress VPC、集中 inspection（Network Firewall／GWLB + appliance mode）、集中 VPC endpoints 與 PHZ 共享、shared VPC（RAM）、Cloud WAN、多 Region TGW peering、DX Gateway + TGW、hybrid DNS 大規模架構、IPAM、segmentation（prod／dev 隔離）、成本與效能取捨。 |
| 42 | 42 - 全球多 Region 架構.md | 全球多 Region 應用與資料架構 | 83 | 16 | 為什麼多 Region（延遲、DR、資料主權）、active-active vs active-passive、資料層選擇（Aurora Global、DynamoDB global tables 衝突處理、S3 CRR／Multi-Region Access Points、ElastiCache Global Datastore）、流量層（Route 53、Global Accelerator、CloudFront）、寫入路由（write-local vs write-global）、一致性取捨、Route 53 ARC、multi-Region KMS keys、Secrets 複寫、部署與設定同步。 |
| 43 | 43 - 企業治理合規與成本可視化.md | 企業治理：合規、備份政策與成本可視化 | 31, 84, 85 | 16 | 組織層 AWS Backup policies、跨帳號 vault、法規保存（Object Lock、Vault Lock）、Config conformance packs 與 aggregator、Audit Manager、Security Hub 標準、資料主權（SCP 限制 Region）、tagging 策略與 tag policies、cost categories、CUR + Athena、Budgets per account、chargeback、Savings Plans 分享、RI 共享與關閉分享。 |
| 44 | 44 - 遷移策略與評估.md | 遷移策略：評估、7Rs 與 Wave Planning | 86, 88 | 16 | 遷移動機、AWS CAF、MRA／MPA、Application Discovery Service（agent vs agentless）、Migration Hub／Migration Evaluator、TCO、7Rs（retire、retain、relocate、rehost、replatform、repurchase、refactor）與判斷方式、dependency mapping、wave planning、landing zone 先行、遷移中的 license（BYOL、Dedicated Hosts）、VMware Cloud on AWS／Elastic VMware Service 現況（保守寫法）。 |
| 45 | 45 - 遷移工具與切換執行.md | 遷移工具與切換執行：MGN、DMS、SCT 與資料搬遷 | 87 | 16 | AWS Application Migration Service（replication agent、測試／cutover、post-launch actions）、DMS（full load、CDC、replication instance／Serverless、validation、homogeneous vs heterogeneous）、SCT 與 DMS Schema Conversion、DataSync／Snow／DX 搬資料、資料庫切換步驟、cutover 與 rollback 計畫、最小停機、mainframe（AWS Mainframe Modernization 簡述）。 |
| 46 | 46 - 現代化與持續改善.md | 現代化與持續改善既有系統 | 89, 90 | 16 | Strangler fig、monolith 拆分順序、到 containers 或 serverless、資料庫拆分、從 EC2 自管到 managed service 的效益、SAP Domain 3 題型（改善 security／reliability／performance／cost／operational excellence）、如何找改善點（Trusted Advisor、Compute Optimizer、Well-Architected review）、常見改善模式表。 |

## Part 9　AI 與新興架構（`Part 9 - AI/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 47 | 47 - 生成式 AI 與 ML 架構.md | 生成式 AI 與 ML 架構：Bedrock、SageMaker 與 AI 服務 | 91–96, 104 | 16 | AI 服務地圖（Rekognition、Textract、Comprehend、Transcribe、Polly、Translate、Lex、Kendra、Personalize、Forecast 現況保守寫）、SageMaker AI 定位（training、endpoints：real-time／serverless／async／batch transform）、Bedrock（foundation models、knowledge bases RAG、agents、guardrails、model invocation logging）、資料安全（VPC endpoint、不用於訓練、KMS）、AgentCore 與 agent 身份／工具授權（保守寫）、human-in-the-loop（Step Functions）、成本與觀測、AI 題目在 SAA／SAP 的考法。 |

## Part 10　實戰案例（`Part 10 - Case Studies/`）

每章：需求→SAA 解法→SAP 演進→完整架構圖→設計決策紀錄（為何選 A 不選 B）→failure 演練→成本估算思路→題目。

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 48 | 48 - 案例 全球電商平台.md | 案例：全球電商平台 | 97, 99 | 12 | CloudFront + ALB + ASG/ECS、Aurora、ElastiCache、SQS 訂單處理、促銷尖峰、影音／圖片處理管線、多 Region 演進。 |
| 49 | 49 - 案例 多租戶 Serverless SaaS.md | 案例：多租戶 Serverless SaaS | 98 | 12 | Silo／pool／bridge、tenant isolation（IAM 動態 policy、ABAC）、Cognito、API GW usage plans、DynamoDB 分區、per-tenant 成本、noisy neighbor。 |
| 50 | 50 - 案例 金融業多帳號環境.md | 案例：金融業多帳號與合規環境 | 100 | 12 | Landing zone、集中 inspection、KMS／CloudHSM、日誌不可竄改、資料主權、break-glass、稽核證據。 |
| 51 | 51 - 案例 混合雲企業遷移.md | 案例：企業資料中心遷移 | 101 | 12 | 300 台 VM 的評估、7Rs 分類、DX 建置、MGN + DMS、wave、cutover、遷移後最佳化。 |
| 52 | 52 - 案例 資料湖與即時分析.md | 案例：資料湖與即時分析平台 | 102 | 12 | Kinesis／Firehose、S3 分層、Glue、Lake Formation、Athena／Redshift、QuickSight、成本。 |
| 53 | 53 - 案例 多 Region DR 與 AI 助理.md | 案例：多 Region DR 與 AI 旅遊助理 | 103, 104 | 12 | Wanderly 最終形態：多 Region warm standby、ARC、Bedrock RAG 助理、guardrails、agent tool 授權。 |

## Part 11　總整理（`Part 11 - Final Review/`）

| 章 | 檔名 | 標題 | 舊章 | 題數 | 必須涵蓋 |
|---|---|---|---|---|---|
| 54 | 54 - 架構師思維與考前衝刺.md | 架構師思維：12 個通用模式與考前衝刺 | 105–116 | 10 | 12 個跨雲 pattern（每個：問題、原理、AWS 實作、考試訊號）、考前一週清單、考場策略、SAA→SAP 心態轉換。 |

## 附錄（`Appendices/`）

| 檔名 | 內容 |
|---|---|
| A - 易混淆服務對照.md | 40+ 組易混淆服務對照（SG vs NACL、Gateway vs Interface endpoint、ALB vs NLB vs GWLB、CloudFront vs GA、SQS vs SNS vs EventBridge vs Kinesis、EBS vs EFS vs FSx、RDS vs Aurora vs DynamoDB、Secrets Manager vs Parameter Store、KMS vs CloudHSM、CloudTrail vs Config vs CloudWatch、GuardDuty vs Inspector vs Macie…）。 |
| B - 關鍵數字與限制.md | 考試常見數字（Lambda 15 分鐘／10GB memory、SQS 256KB／14 天、DynamoDB 400KB、S3 5TB／5GB PUT、API GW 29 秒、Kinesis retention、EBS 上限、RDS replicas 數、Aurora 15 replicas…），並註明預設 quota 是否可調整。 |
| C - 題目關鍵字速查.md | 「題目出現 X → 優先考慮 Y」對照表（200 條左右，依 domain 分類）。 |
| D - 術語表.md | 全書術語 A–Z（英文、中文、一句話定義、首次出現章）。 |
| E - 讀書計畫與錯題本.md | 30 天 SAA、45 天 SAP、12 週零背景計畫，每天讀哪章、做哪些題；錯題本模板。 |

## 模擬考（`Mock Exams/`）

| 檔名 | 題數 | 分配 |
|---|---|---|
| SAA 模擬考 1.md | 65 | D1 30%（20 題）、D2 26%（17）、D3 24%（15）、D4 20%（13） |
| SAA 模擬考 2.md | 65 | 同上 |
| SAA 模擬考 3.md | 65 | 同上 |
| SAP 模擬考 1.md | 75 | D1 26%（20）、D2 29%（22）、D3 25%（19）、D4 20%（14） |
| SAP 模擬考 2.md | 75 | 同上 |
