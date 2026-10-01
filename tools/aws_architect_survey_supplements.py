"""Focused supplements discovered by the Jayendra/AWS cross-source audit.

These sections close SAA/SAP-relevant gaps without turning the book into a
catalog for every AWS specialty certification.  Facts are sourced from current
AWS documentation; community material only helped identify omissions.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SurveySupplement:
    title: str
    context: str
    diagram: str
    example_title: str
    example_language: str
    example: str
    explanation: tuple[str, ...]
    decision: str
    exam_scope: str
    sources: tuple[tuple[str, str], ...]


SUPPLEMENTS: dict[int, tuple[SurveySupplement, ...]] = {
    15: (
        SurveySupplement(
            "VPC Lattice：當你只想連「服務」，而不是打通整個網路",
            "想像付款 API 在 A 帳號，訂單服務在 B 帳號，而且兩邊 VPC 的 CIDR 還重疊。"
            "Peering／Transit Gateway 的核心抽象是 IP 路由；PrivateLink 的核心抽象是一個由 provider "
            "暴露的 endpoint service。VPC Lattice 再往上提一層：平台先建立 service network，服務擁有者"
            "把 HTTP／HTTPS 等服務掛進去，consumer VPC 只有在建立 association 且通過 auth policy 時才可呼叫。",
            """consumer workload
  │ service DNS name
  ▼
associated VPC ── security group ──> VPC Lattice service network
                                      │ auth policy
                         ┌────────────┴────────────┐
                         ▼                         ▼
                    payment service          catalog resource
                    listener/rules           resource config
                    targets                  resource gateway""",
            "一個最小 auth policy 長什麼樣子",
            "JSON",
            """{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::111122223333:role/OrderServiceRole"},
    "Action": "vpc-lattice-svcs:Invoke",
    "Resource": "arn:aws:vpc-lattice:ap-northeast-1:444455556666:service/svc-123/*"
  }]
}""",
            (
                "Principal 是真正可以呼叫服務的 workload role；VPC association 只提供網路入口，不等於授權。",
                "Resource 指向 Lattice service，而不是對方整個 VPC。這就是它能縮小 blast radius 的原因。",
                "服務仍需 listener、rules、target group 與健康 targets；Lattice 不會替 application 修好 retry、身份資料或交易一致性。",
            ),
            "需要任意 private-IP 雙向連線時仍比較 Peering/TGW；只暴露單一 TCP 服務可比較 PrivateLink；"
            "跨 VPC／帳號的 application networking、L7 routing 與 IAM auth 才是 Lattice 的強項。",
            "SAA 先掌握它與 Peering／TGW／PrivateLink 的責任邊界；多帳號 service network、RAM 分享、"
            "delegated ownership 與 policy rollout 屬 SAP／進階實務。",
            (
                ("AWS：What is Amazon VPC Lattice?", "https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html"),
                ("AWS：VPC Lattice auth policies", "https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html"),
            ),
        ),
    ),
    19: (
        SurveySupplement(
            "Cloud WAN：當 TGW 已經從區域網路長成全球企業骨幹",
            "一兩個 Region 時，Transit Gateway 配合 peering 很直覺；但當企業有數十個 Region、分公司與資料中心，"
            "困難不再只是『能不能連』，而是每個 Region 是否都套用相同分段、route sharing、inspection 與變更版本。"
            "Cloud WAN 用 core network policy 描述意圖，再在各 Region 建立 core network edge 並維持 segments。",
            """branch / DC ─ VPN / Connect ┐
VPC A ─ attachment ─────────┼─> Cloud WAN core network
VPC B ─ attachment ─────────┘      ├─ segment: prod
                                   ├─ segment: nonprod
                                   └─ shared-services / inspection
                         policy version → review → execute / rollback""",
            "Core network policy 的關鍵不是 JSON 語法，而是 segment 意圖",
            "JSON",
            """{
  "version": "2021.12",
  "core-network-configuration": {
    "asn-ranges": ["64520-64529"],
    "edge-locations": [
      {"location": "ap-northeast-1"},
      {"location": "us-east-1"}
    ]
  },
  "segments": [
    {"name": "prod", "require-attachment-acceptance": true},
    {"name": "shared-services"}
  ]
}""",
            (
                "Edge locations 決定哪些 Regions 有 managed core edge；它不是 CloudFront edge location。",
                "Segment 是隔離的 routing domain。附件不會因為同屬一個 global network 就自動互通。",
                "政策要先產生 change set、檢查 route/segment 影響再 execute；企業網路也需要版本、審核與回復路徑。",
            ),
            "單 Region hub-and-spoke 優先 TGW；需要全球一致 policy、segments、branch/DC/VPC 統一治理時才評估 Cloud WAN。"
            "PrivateLink/Lattice 仍適合只暴露服務，不應為了一個 API 建全球 routed network。",
            "Cloud WAN 通常是 SAP 的 organizational complexity／network strategy 延伸；SAA 只需理解它不取代"
            "Direct Connect、VPN 或 application-level service exposure，而是治理它們形成的 WAN。",
            (
                ("AWS：What is AWS Cloud WAN?", "https://docs.aws.amazon.com/network-manager/latest/cloudwan/what-is-cloudwan.html"),
                ("AWS：Core network policies", "https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-policy-create.html"),
            ),
        ),
    ),
    20: (
        SurveySupplement(
            "Hybrid DNS 與 DNSSEC：一個管『去哪裡問』，一個管『答案有沒有被竄改』",
            "Hybrid DNS 的問題通常是查詢方向：AWS workload 要問 on-prem zone，或 on-prem client 要問 Route 53 "
            "private hosted zone。Resolver outbound endpoint 搭 rule 處理前者；inbound endpoint 處理後者。"
            "DNSSEC 解決的是另一件事：resolver 可驗證 public DNS 回答的簽章鏈，降低 cache poisoning／answer tampering。",
            """AWS workload ─> Route 53 Resolver
                   ├─ private hosted zone → private answer
                   ├─ rule: corp.example → outbound endpoint → on-prem DNS
                   └─ public zone → DNSSEC validation chain

on-prem client ─ conditional forwarder → inbound endpoint → private hosted zone""",
            "真正可維運的 Resolver rule 至少要說清楚三件事",
            "YAML",
            """resolver_rule:
  domain: corp.example
  direction: FORWARD
  outbound_endpoint_subnets:
    - subnet-a
    - subnet-b
  target_dns_ips:
    - 10.40.0.10
    - 10.40.1.10
  associated_vpcs:
    - app-prod-vpc""",
            (
                "Domain 採 suffix match；過於寬鬆的規則可能把原本應由 public DNS 回答的名稱送到內部。",
                "Endpoint 跨至少兩個 AZ，target DNS 也應有可用性設計；否則 DNS 會成為所有 application 的共同單點。",
                "用 dig/nslookup 分別從 AWS 與 on-prem 測試，並記錄實際回答、resolver query logs 與失敗方向。",
            ),
            "Split-horizon 是同一名稱依查詢來源得到不同答案；Resolver endpoint/rule 是轉送路徑；DNSSEC 是完整性驗證。"
            "三者不能互相替代，路由、安全群組與 UDP/TCP 53 回程也仍要成立。",
            "Resolver inbound/outbound 與 conditional forwarding 是 SAP hybrid DNS 高頻邊界；SAA 先會辨識 public/private "
            "hosted zone、TTL、Alias 與 DNS 不代理 application traffic。",
            (
                ("AWS：Route 53 Resolver", "https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html"),
                ("AWS：Configuring DNSSEC signing", "https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-configuring-dnssec.html"),
            ),
        ),
    ),
    18: (
        SurveySupplement(
            "ALB Mutual TLS：HTTPS 不只讓 client 驗證 server，也能反過來驗證 client",
            "一般 TLS 只要求 server 出示 certificate；mTLS 在 handshake 時也要求 client certificate。"
            "這適合 B2B API、受管設備或服務間連線，但 client certificate 只建立『這張憑證受信任』，"
            "application 仍要把 certificate subject／serial 映射到 tenant、role 或 device authorization。",
            """client cert + TLS ClientHello
          │
          ▼
ALB HTTPS listener ─ trust store / CRL ─ verify
          │ X-Amzn-Mtls-* headers
          ▼
application ─ tenant/device authorization ─ business action""",
            "Listener 上真正需要決定的設定",
            "YAML",
            """https_listener:
  port: 443
  certificate: server-certificate-arn
  mutual_authentication:
    mode: verify
    trust_store: trusted-client-ca-bundle
    ignore_client_certificate_expiry: false""",
            (
                "verify mode 由 ALB 驗證 X.509 client chain；passthrough 則把 chain 交給 target 驗證。",
                "Trust store 決定哪些 CA 被信任；CRL 可用於撤銷檢查。這不是一般 security group 能表達的身份條件。",
                "Backend 必須只信任由 ALB 產生／覆寫的 mTLS headers，並避免可繞過 ALB 的直接入口。",
            ),
            "一般 public website 常用 OIDC/Cognito/session；設備或 B2B machine identity 才常用 mTLS。"
            "若需要應用內細粒度權限，仍需 JWT／policy engine／database authorization。",
            "SAA 需分清 TLS termination、listener certificate、target protocol 與 health check；mTLS trust store、"
            "revocation、passthrough/verify 與 backend authorization 是 SAP／進階安全邊界。",
            (
                ("AWS：Mutual authentication with TLS in ALB", "https://docs.aws.amazon.com/elasticloadbalancing/latest/application/mutual-authentication.html"),
            ),
        ),
    ),
    24: (
        SurveySupplement(
            "Verified Access：不用先進 VPN，也不代表不用驗證",
            "傳統 VPN 常在使用者連上後給一段網路可達性；Verified Access 改成每次進入 application 都重新評估"
            "使用者與裝置訊號。它保護的是 application access，不是讓 client 任意掃描 private subnet。",
            """user + managed device
        │ identity/device trust
        ▼
Verified Access endpoint ─ policy evaluation ─> private web application
        │ allow/deny log
        └──────────────────────────────> audit / incident response""",
            "Policy 應描述可驗證的身份與裝置條件",
            "CEDAR-like policy sketch",
            """permit(principal, action, resource)
when {
  principal.groups.contains("finance") &&
  context.device.trust_level == "high"
};""",
            (
                "Identity provider 說明人是誰，device trust provider 說明裝置狀態；兩者是不同訊號。",
                "Endpoint 把 policy 套到一個 application 入口；它不是 TGW、VPN 或任意 L3 connectivity 的替代品。",
                "Allow/deny logs 應進入集中稽核，否則『每次驗證』仍無法支持 incident investigation。",
            ),
            "員工存取少數 private web apps、需要 identity/device-aware zero trust 時評估 Verified Access；"
            "任意協定、整段網路管理或 site-to-site connectivity 仍比較 Client VPN、VPN、DX、SSM。",
            "此服務是進階／新式 zero-trust 補充。考試先測 responsibility boundary：identity-aware application access "
            "不等於建立 private routed network。",
            (
                ("AWS：What is AWS Verified Access?", "https://docs.aws.amazon.com/verified-access/latest/ug/what-is-verified-access.html"),
            ),
        ),
    ),
    26: (
        SurveySupplement(
            "Verified Permissions：IAM 管 AWS API；應用程式自己的權限要有另一個 policy decision point",
            "IAM 回答的是 principal 能否呼叫 AWS action；你的 SaaS 還會有『Alice 能不能編輯 tenant B 的 invoice』。"
            "把後者硬寫在每個 controller 容易產生不一致。Verified Permissions 用 Cedar policy store 集中"
            "application authorization，application 每次帶 principal、action、resource 與 context 問 Allow/Deny。",
            """authenticated user
      │ token/claims
      ▼
application ─ IsAuthorized(principal, action, resource, context)
      │                              │
      │                              ▼
      └──────────────────── policy store (Cedar)
                        allow / deny + decision log""",
            "一條 policy 應表達 business resource，而不是 AWS ARN 清單",
            "Cedar",
            """permit (
  principal in Group::"support",
  action == Action::"ReadTicket",
  resource
)
when { resource.tenant == principal.tenant };""",
            (
                "principal/action/resource 是應用 domain；不要把它和 IAM Action/Resource 混為同一份 policy。",
                "Token 證明登入資訊，但 policy engine 才結合 resource ownership、tenant 與 context 做授權。",
                "Policy update 是 control plane；每次 IsAuthorized 是 data path。需要 latency、cache、deny default 與失效策略。",
            ),
            "AWS 資源權限用 IAM/resource policy/SCP/boundary；application fine-grained authorization 才評估"
            "Verified Permissions。兩者常一起出現，但責任完全不同。",
            "SAA 先掌握 authentication/authorization 與 IAM evaluation；Verified Permissions、Cedar schema、"
            "policy store rollout 是現代應用安全延伸；在SAP-C03完整考綱發布前，不把它標成正式計分task。",
            (
                ("AWS：What is Amazon Verified Permissions?", "https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/what-is-avp.html"),
            ),
        ),
    ),
    32: (
        SurveySupplement(
            "ENA、EFA 與 Jumbo Frames：Placement Group 只決定放哪裡，網卡能力決定怎麼傳",
            "Cluster placement group 讓 instances 靠近，卻不會自動把普通網路變成 HPC fabric。ENA 提供 enhanced networking；"
            "EFA 在支援的 instance type 上提供適合 HPC/ML 的低延遲、高吞吐 OS-bypass 能力。Jumbo frames 則是 MTU 選擇，"
            "只有整條路徑都支援時才能減少封包處理 overhead。",
            """HPC node ─ EFA/ENA ─┐
HPC node ─ EFA/ENA ─┼─ cluster placement group ─ high-bandwidth fabric
HPC node ─ EFA/ENA ─┘
       MTU/path must agree end-to-end; one smaller hop can break jumbo packets""",
            "排查『頻寬很高但 MPI 很慢』的順序",
            "Checklist",
            """1. instance type supports EFA / required ENA bandwidth
2. EFA attached and driver/libfabric visible in the guest
3. instances placed in the intended cluster placement group
4. security group allows the required same-group traffic
5. MTU and route path are consistent end-to-end
6. benchmark with the real message-size/concurrency pattern""",
            (
                "Instance advertised bandwidth 是上限，不代表單一 flow 或 application 一定達到。",
                "Jumbo MTU 不一致常表現為部分封包可通、較大 payload timeout；需要沿路測試，不是只看 EC2 console。",
                "Cluster placement 提升 proximity，但縮小 failure-domain 彈性；容量不足時可能無法一次啟動整個 group。",
            ),
            "一般 web tier 通常不需 EFA；高 packets-per-second 用 ENA 支援的 instance；MPI/ML collective "
            "communication 才考慮 EFA＋cluster placement。跨 Internet 路徑不要假設 jumbo MTU。",
            "SAA 會測 placement group 與 instance family；EFA、MTU、network-card/flow bandwidth 與 HPC trade-off "
            "通常是 SAP／Advanced Networking 深化。",
            (
                ("AWS：Enhanced networking on EC2", "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/enhanced-networking.html"),
                ("AWS：Elastic Fabric Adapter", "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html"),
            ),
        ),
    ),
    36: (
        SurveySupplement(
            "SnapStart 與 Response Streaming：一個縮短開始前等待，一個讓結果不必全部算完才送",
            "Cold start 包含 runtime、依賴與初始化。SnapStart 在發佈版本時先初始化並保存 execution environment snapshot，"
            "之後從 snapshot 恢復；response streaming 則讓 function 邊產生資料邊回給 client。兩者優化不同時間："
            "time-to-first-instruction 與 time-to-first-byte。",
            """publish version ─ initialize ─ snapshot
invoke ─ restore snapshot ─ handler ─ write chunk 1 ─ chunk 2 ─ end
          ▲ startup latency             ▲ first-byte latency""",
            "SnapStart 最容易被忽略的 correctness 問題",
            "Pseudo configuration",
            """function_version:
  snap_start: PublishedVersions
handler_rules:
  - generate unique IDs after restore
  - refresh temporary credentials and timestamps
  - validate/reconnect network connections
response_stream:
  - apply backpressure
  - always end the stream""",
            (
                "Snapshot 會被多個 environments 重用；初始化時產生的 UUID、entropy 或 temporary state 不能假設仍唯一／新鮮。",
                "Provisioned Concurrency 維持預先初始化容量，適合更嚴格且可預測的 latency；不是 SnapStart 的同義詞。",
                "Streaming 降低 first-byte latency，卻沒有降低全部工作量；client disconnect、backpressure 與 partial response 都要處理。",
            ),
            "初始化很重、可發佈 version 且 runtime/feature 相容時評估 SnapStart；嚴格穩定低延遲評估 Provisioned Concurrency；"
            "大型或逐步生成回應才需要 streaming。",
            "這些是 Lambda performance 深化。考題若只說『cold start』，先辨識是初始化、容量未預熱，還是 application 下游慢，"
            "不要看到新功能就直接選。",
            (
                ("AWS：Lambda SnapStart", "https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html"),
                ("AWS：Lambda response streaming", "https://docs.aws.amazon.com/lambda/latest/dg/config-rs-write-functions.html"),
            ),
        ),
    ),
    42: (
        SurveySupplement(
            "S3 Express One Zone：它仍是 object storage，但把 latency 與 failure domain 換到同一個 AZ",
            "S3 Standard 的一般用途 bucket 跨多個 AZ 保存資料；S3 Express One Zone 使用 directory bucket，"
            "讓 application 可把 compute 與 object storage 放在同一 AZ，換取一致的 single-digit millisecond access。"
            "它不是 EBS，也不會突然具備 POSIX rename/locking。",
            """compute in AZ-a ─ zonal endpoint ─ directory bucket (AZ-a)
        │                     ├─ S3 Express One Zone only
        │                     ├─ session-based object access
        │                     └─ single-AZ failure boundary
        └─ durable source / replica may still live in general-purpose S3""",
            "選它之前要寫下的資料生命週期",
            "YAML",
            """dataset:
  authoritative_copy: s3-standard://durable-source
  hot_working_set: s3express://directory-bucket--azid--x-s3
  compute_az: apne1-az4
  rebuild_strategy: repopulate-from-authoritative-copy
  encryption: SSE-KMS
  access: CreateSession through supported SDK""",
            (
                "Directory bucket 的 object operations 走 zonal endpoint；client/SDK 會使用 CreateSession 的短期 session credentials。",
                "單 AZ 是刻意的性能取捨。若資料不可重建，還要另外設計 durable copy／replication，而不是只看服務名稱有 S3。",
                "Directory bucket 的 feature/authorization 與 general-purpose bucket 不完全相同；部署前要逐項驗證所需 API。",
            ),
            "低延遲、高 request rate、可與 compute co-locate 且可接受／補足單 AZ 風險時使用；一般 data lake、網站物件、"
            "跨 AZ durability 或完整 S3 feature set 仍以 general-purpose bucket 為主。",
            "SAA 主要仍考 storage class 與 durability/cost；S3 Express 是進階／新服務邊界，重點是不要把高性能誤解成共享磁碟。",
            (
                ("AWS：Directory buckets and S3 Express One Zone", "https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-one-zone.html"),
            ),
        ),
    ),
    46: (
        SurveySupplement(
            "Aurora DSQL：不要因為名字有 Aurora，就把它當成 Aurora Global Database 的新 instance class",
            "Aurora Global Database 以單一 primary Region 寫入、secondary Regions 讀取與災難復原；Aurora DSQL 是另一個"
            "serverless distributed relational service，多 Region peered cluster 的兩個 Regional endpoints 可同時讀寫並提供強一致性。"
            "這會改變 application write path、latency、SQL compatibility 與 migration 假設。",
            """Aurora Global Database:
writer Region ─ async storage replication ─> secondary read Region

Aurora DSQL multi-Region:
app Region A ─ write/read endpoint A ─┐
                                     ├─ one logical strongly consistent DB
app Region B ─ write/read endpoint B ─┘""",
            "服務選型前先問的四個問題",
            "Decision record",
            """data_model: relational + ACID
write_topology: single-writer-region | multi-region-active-active
consistency: local/replica-lag-aware | cross-region-strong
compatibility:
  required_postgresql_features: [...]
  migration_tooling_and_driver_tests: [...]
latency_budget:
  local_read_ms: ...
  cross-region_commit_ms: ...""",
            (
                "PostgreSQL-compatible 不等於支援所有 PostgreSQL extensions/features；必須以實際 schema、query 與 driver 做 compatibility test。",
                "強一致 multi-Region 仍受物理距離影響；架構師要測 transaction latency，而不是把 active-active 當成零代價。",
                "Aurora DSQL 自動管理 infrastructure，卻不會替你決定 shard-independent transaction、hot key、schema 或 business invariant。",
            ),
            "既有 Aurora／RDS workload、完整 engine feature 與單 writer 模型仍有成熟優勢；需要 serverless distributed SQL、"
            "多 Region active-active writes 與強一致性時才評估 DSQL，並先確認 Region set 與 feature compatibility。",
            "Aurora/RDS/DynamoDB 是 SAA/SAP-C02 核心；Aurora DSQL 應清楚標成已公告轉版期間的現代架構補充，"
            "不可拿新服務知識覆蓋目前官方 exam guide。",
            (
                ("AWS：What is Amazon Aurora DSQL?", "https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html"),
            ),
        ),
    ),
    72: (
        SurveySupplement(
            "CloudFormation Guard 與 Custom Resource：一個在部署前說不，一個把 CloudFormation 做不到的事接進生命週期",
            "Guard 是 policy-as-code evaluator：拿 YAML/JSON 與規則比對，適合 shift-left；CloudFormation Hooks 才能在"
            "server side 阻擋 create/update/delete。Custom Resource 則讓 CloudFormation 把 Create/Update/Delete request "
            "送給 Lambda/SNS provider，等待它回 SUCCESS/FAILED。",
            """template ─ cfn-lint ─ Guard rules ─ change set ─ CloudFormation
                                                   │
                                      built-in resource or Custom::Thing
                                                   │ request + ResponseURL
                                                   ▼
                                              Lambda provider
                                                   │ SUCCESS/FAILED
                                                   └──────────────> stack continues/rolls back""",
            "Guard rule與Custom Resource各自最小的樣子",
            "Guard + YAML",
            """# Guard: policy check, not template syntax validation
rule encrypted_buckets {
  AWS::S3::Bucket Properties.BucketEncryption exists
}

# CloudFormation: lifecycle extension
MyExternalObject:
  Type: Custom::ExternalObject
  Properties:
    ServiceToken: !GetAtt ProviderFunction.Arn
    Name: invoice-schema""",
            (
                "cfn-lint 檢查 template structure；Guard 檢查你定義的政策；Hook 才是 CloudFormation control-plane enforcement。",
                "Custom Resource provider 必須對 Create/Update/Delete 冪等，並一定回覆 pre-signed ResponseURL；漏回覆會讓 stack 等到 timeout。",
                "PhysicalResourceId 若不穩定，update 可能被視為 replacement；delete path 也必須能清理外部資源。",
            ),
            "只需標準資源時不要用 Custom Resource；能用 Registry extension 時可得到較完整 CRUDL/drift model。"
            "Guard 適合 CI policy test，組織級不可繞過控制再加 Hooks、SCP、Config 等。",
            "SAA 會辨識 IaC、change set、rollback；custom resource lifecycle、Guard/Hook enforcement、跨帳號 pipeline "
            "與 policy rollout 是 SAP 深度。",
            (
                ("AWS：CloudFormation custom resources", "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html"),
                ("AWS：What is CloudFormation Guard?", "https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html"),
            ),
        ),
    ),
    74: (
        SurveySupplement(
            "CI/CD 的全圖：Source、Build、Artifact、Deploy 是四個責任，不是一個『Pipeline 服務』",
            "最容易背錯的地方，是把 CodePipeline 當成會編譯、測試或部署所有東西。它主要負責 orchestrate stages；"
            "CodeBuild 執行 build/test，artifact 放 S3/ECR，CodeDeploy／CloudFormation／ECS deployment controller "
            "負責實際 rollout。每一段都要有自己的 role、evidence 與 rollback contract。",
            """source commit
   ▼
pipeline orchestration
   ├─ build/test role ─ CodeBuild ─ artifact digest/SBOM
   ├─ approval / policy checks
   └─ deploy role ─ CodeDeploy/CloudFormation/ECS
                         ├─ canary/blue-green
                         └─ alarms → rollback""",
            "一個 production gate 要檢查的是結果，不只是 stage 顯示綠色",
            "YAML",
            """deployment_gate:
  immutable_artifact: sha256:...
  pre_deploy:
    - unit_and_integration_tests
    - cfn_guard_security_rules
  rollout:
    strategy: canary
    first_exposure: 10_percent
  rollback_on:
    - alarm: checkout_error_rate
    - alarm: checkout_p99_latency
  evidence:
    - deployment_id
    - artifact_digest
    - approver
    - alarm_history""",
            (
                "同一 immutable artifact 應依序 promoted，不要每個 environment 重新 build 出不同內容。",
                "Pipeline service role、build role、deploy role 分開，讓 compromise 與錯誤只影響必要範圍。",
                "Rollback 要有 application/data compatibility；把舊 binary 部署回去不一定能回復已做的 schema migration。",
            ),
            "簡單 serverless/CloudFormation deployment 可用原生整合；複雜 application rollout 才加入 CodeDeploy；"
            "第三方 CI 也可行，判斷重點是 identity federation、artifact integrity、gates、blast radius 與 evidence。",
            "SAA 掌握 deployment strategy；SAP 要能設計跨帳號 roles、artifact promotion、manual approval 邊界、"
            "multi-Region waves、rollback 與 audit trail。",
            (
                ("AWS：CodePipeline concepts", "https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html"),
                ("AWS：CodeDeploy deployment configurations", "https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html"),
            ),
        ),
    ),
    81: (
        SurveySupplement(
            "Security Lake 與 Incident Response：先保存可關聯的證據，再談自動修復",
            "CloudTrail、VPC Flow Logs、Route 53 query logs、WAF logs 與 findings 各自描述不同事件。"
            "Security Lake 將多帳號、多 Region 的 security data 集中到你帳號內的 S3，轉成 OCSF 與 Parquet，"
            "讓 SIEM／Athena／其他 subscriber 以一致 schema 分析。它不是 GuardDuty 的替代品：前者是資料層，後者是偵測服務。",
            """accounts/Regions
  ├─ CloudTrail / VPC Flow / DNS / WAF
  ├─ Security Hub findings
  └─ custom sources
          ▼ normalize OCSF + Parquet
     Security Lake (S3 owned by customer)
          ├─ query subscriber
          ├─ data-access subscriber / SIEM
          └─ incident evidence retention
                    ▼
detect → triage → contain → preserve → eradicate → recover → learn""",
            "一個事件不能只留下『已關閉 instance』",
            "Incident record",
            """incident:
  finding_id: gd-...
  affected_resource: i-...
  timeline_sources:
    - cloudtrail
    - vpc_flow_logs
    - dns_query_logs
  containment:
    action: isolate-with-quarantine-sg
    approved_by: security-oncall
  evidence:
    snapshot_ids: [...]
    log_retention_lock: enabled
  recovery:
    rebuild_from_known_good_image: true
  lessons:
    preventive_control_owner: platform-security""",
            (
                "Containment 要限制 attacker movement，同時避免先銷毀 memory/disk/log evidence；動作順序由 incident severity 與 runbook 決定。",
                "Security Lake subscriber 只能取得被授權 sources/Regions；集中不代表所有分析工具自動擁有全資料。",
                "Rollup Region、retention、KMS、Lake Formation 與跨帳號 delegated admin 都是 data residency 與 blast-radius 決策。",
            ),
            "只要查單一服務近期 log，CloudWatch Logs/S3/Athena 可能足夠；需要組織級 normalization、長期 security analytics "
            "與多個 subscribers 才評估 Security Lake。偵測、調查、儲存、回應仍是不同責任。",
            "集中 logging、delegated admin、retention 與 incident runbook 是 SAP 高頻；SAA 先分清 CloudTrail、Config、"
            "CloudWatch、GuardDuty、Security Hub 與原始 logs。",
            (
                ("AWS：What is Amazon Security Lake?", "https://docs.aws.amazon.com/security-lake/latest/userguide/what-is-security-lake.html"),
                ("AWS：Security incident response guide", "https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/aws-security-incident-response-guide.html"),
            ),
        ),
    ),
}


def survey_supplements(chapter: int) -> tuple[SurveySupplement, ...]:
    return SUPPLEMENTS.get(chapter, ())
