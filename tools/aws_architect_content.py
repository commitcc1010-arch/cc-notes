"""Generated teaching layers shared by the AWS book builder and checker."""
from __future__ import annotations

import re

from aws_architect_model import PARTS, TASKS, Topic
from aws_architect_profiles import component_profile
from aws_architect_topics_01 import TOPICS as PART01
from aws_architect_topics_02 import TOPICS as PART02
from aws_architect_topics_03 import TOPICS as PART03


TOPICS: list[Topic] = PART01 + PART02 + PART03
TOPIC_BY_NUMBER = {topic.number: topic for topic in TOPICS}


def part_for(number: int) -> dict:
    return next(part for part in PARTS if part["range"][0] <= number <= part["range"][1])


def short(value: str, limit: int = 72) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 1] + "…"


PART_LENSES = {
    0: (
        "先建立共同語言",
        "像第一次看城市地圖：先分清道路、地址、建築與規則，再談哪個地標最好。",
        "先問這個名詞描述的是位置、資料、運算、可靠性，還是人的責任。",
    ),
    1: (
        "跟著一個封包走",
        "把網路想成城市交通：DNS找地址，route選道路，security rules決定哪扇門能進。",
        "永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。",
    ),
    2: (
        "跟著一次授權決定走",
        "把身份系統想成辦公大樓：登入證明你是誰，門禁規則才決定你能進哪一間房。",
        "分清身份、權限、加密金鑰、網路邊界與稽核證據，不能用其中一層代替其他層。",
    ),
    3: (
        "跟著一份工作走",
        "把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。",
        "先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。",
    ),
    4: (
        "跟著一筆資料走",
        "把資料服務想成圖書館與倉庫：有些資料要隨機翻頁，有些要共享編輯，有些只需按編號整件取回。",
        "先決定資料的讀寫語意、誰是唯一真相、如何複製與恢復，再比較容量和單價。",
    ),
    5: (
        "跟著一件工作在服務間流動",
        "把分散式整合想成餐廳出單：收銀台不必站著等每個廚房完成，但每張單都要能追蹤、重做與防重複。",
        "先分清queue、事件通知、stream與workflow，再設計timeout、重試、順序與冪等。",
    ),
    6: (
        "從故障發生的那一刻倒推",
        "把可靠性設計想成消防演練：備用出口畫在圖上不算完成，必須真的走過一次並量出需要多久。",
        "用使用者結果、RTO/RPO、容量與成本衡量，而不是看到資源顯示綠色就宣告成功。",
    ),
    7: (
        "跟著一次變更走到production",
        "把部署想成劇場換景：新布景要先在小舞台試演，觀眾反應不對時還能迅速換回舊版本。",
        "每次變更都要有預覽、有限曝光、驗收訊號、停止條件與rollback。",
    ),
    8: (
        "把鏡頭從單一服務拉到整家公司",
        "把企業雲端想成城市規劃：道路、分區、警消與帳務需要共同規則，但每個社區仍要能獨立生活。",
        "除了技術方案，也要交代owner、委派、跨帳號邊界、推出節奏與長期營運方式。",
    ),
    9: (
        "把AI當成會犯錯但能使用工具的新同事",
        "模型像一位讀過很多資料的助理：它可以提出好建議，卻不能因此自動取得刪除資料或退款的權限。",
        "把生成品質、資料邊界、工具授權、人工核准與稽核分成不同防線。",
    ),
    10: (
        "走進一次完整架構會議",
        "案例章像拼一張地圖：前面學過的道路、門禁、倉庫與應變流程，現在必須共同服務同一個商業目標。",
        "先找最硬的限制與唯一真相，再逐層補上入口、資料、故障、營運與成本。",
    ),
    11: (
        "拿掉AWS名稱，看看設計是否仍然成立",
        "這些pattern像物理定律：換一間cloud或改用自建系統，排隊、故障、權限與資料一致性仍然存在。",
        "用需求、狀態與失敗模式解釋設計；如果只能說出產品名稱，就還沒有真正理解。",
    ),
}


SPECIAL_BLUEPRINT_BODIES = {
    3: """工作抵達
  ├─ 需要完整OS／driver／長時間process ──> VM / EC2
  ├─ 需要封裝與可攜、仍是長時間服務 ────> Container / ECS / EKS
  └─ 短時間、事件驅動、流量高度變動 ────> Serverless / Lambda

共同問題：image從哪來？state放哪裡？如何scale？失敗後誰重啟？
選擇越高階的抽象，主機管理越少；但可控制的OS與runtime細節也越少。""",
    5: """使用者輸入 api.example.com
          │
          ▼
DNS：把名稱查成位址
          │
          ▼
TCP：和該位址的port建立連線
          │
          ▼
TLS：加密並驗證對方certificate
          │
          ▼
HTTP：送出method、path、headers與body
          │
          ▼
Application / ALB回應；502、timeout與certificate error分屬不同層""",
    6: """資料要怎麼被使用？
  ├─ 像本機磁碟、低延遲隨機I/O ───────> Block / EBS
  ├─ 多台機器共享目錄、需要file semantics ─> File / EFS / FSx
  └─ 以key整個PUT/GET、海量耐久保存 ─────> Object / S3

先選access semantics，再比較容量、throughput、availability與價格。
Backup回答「壞掉後如何找回」；它不是第四種日常存取介面。""",
    7: """先列出資料access patterns
  ├─ transaction、join、關聯完整性 ─────> RDS / Aurora
  ├─ 已知key、極大scale、低延遲 ────────> DynamoDB
  ├─ 可重建的熱門讀取結果 ─────────────> ElastiCache
  └─ 掃描多年資料做聚合分析 ───────────> Redshift / Athena

同一系統可以同時使用多種store，但每份資料只能有清楚的authoritative owner。""",
    12: """Internet
   │ inbound HTTPS                         ▲ app主動下載更新的回程
   ▼                                       │
Internet Gateway（附掛在VPC邊界；不是放在兩個subnet中間）
   │                                       │
   ▼                                       │
┌──────────────────── VPC 10.20.0.0/16 ────────────────────┐
│ Public subnet A 10.20.0.0/24                              │
│   internet-facing ALB        NAT Gateway A                │
│   public-rt: 0.0.0.0/0 → IGW                              │
│          │ HTTPS 443                 ▲                    │
│          ▼                           │ private-rt default  │
│ Private app subnet A 10.20.10.0/24   │ 0.0.0.0/0 → NAT A  │
│   EC2 app 10.20.10.25 ───────────────┘                    │
│          │ PostgreSQL 5432                                 │
│          ▼                                                 │
│ Isolated DB subnet A 10.20.20.0/24                         │
│   RDS private address                                      │
│   db-rt: 只有10.20.0.0/16 → local，沒有Internet default    │
│                                                            │
│ AZ B放同樣三層與NAT B，避免AZ A成為共同故障點。             │
└────────────────────────────────────────────────────────────┘

入站：Internet → IGW → ALB → app → database。
App出站：app → private route table → 同AZ NAT → public route table → IGW。
IGW不會讓所有VPC資源自動公開；仍需public route、public address與允許規則同時成立。""",
    15: """需求先分三種，不能只問「VPC怎麼連」

1. 少量VPC需要任意private-IP雙向互通
   VPC A <──────── VPC Peering ────────> VPC B

2. Consumer只該呼叫Provider的一個服務
   Consumer ENI ── PrivateLink ──> Provider NLB / service

3. 大量VPC、VPN、DX需要transitive hub與分段route domains
   Spokes ── attachments ──> Transit Gateway ──> shared services / inspection

三條路都仍需檢查DNS、去回程、security policy與CIDR重疊。""",
    17: """全球使用者
  ├─ HTTP內容可cache、要WAF與保護origin
  │      └─> CloudFront edge ── hit直接回覆 / miss回origin
  │                    └─ Lambda@Edge只在選定event階段修改request/response
  │
  └─ TCP/UDP、不可cache、需要兩個static anycast IP
         └─> Global Accelerator edge ── AWS backbone ──> healthy regional endpoint

CloudFront與Global Accelerator是兩條不同入口路徑，不會依序串在一起。""",
    18: """先看application需要理解到哪一層

HTTP / HTTPS request
  └─ host、path、header routing ──> ALB ──> application targets

TCP / UDP / TLS flow
  └─ static IP、高連線吞吐 ──────> NLB ──> network targets

需要透明檢查的IP flow
  └─ GENEVE封裝 ─────────────────> GWLB ──> firewall / IDS appliances

三者都是load balancing家族，但處理的protocol語意與target完全不同。""",
    21: """人員登入
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

CloudTrail保存最後真正使用哪個identity做了什麼。""",
    41: """Application以bucket + key操作object
      │
      ├─ PUT完整object ──> S3持久保存與versioning
      ├─ GET完整object ──> IAM / bucket policy先授權
      └─ LIST prefix ────> bucket-level permission

S3沒有一般POSIX檔案系統的append、directory rename或file locking。

公開下載通常走：
Viewer ── CloudFront / presigned URL ──> private S3 object
而不是直接把整個bucket設為public。""",
    45: """Application write
      └─ RDS writer ── synchronous standby in another AZ
                         └─ 故障時自動failover；不拿來分擔一般讀取

Reporting reads
      └─ Read replica（可能有replication lag）

大量短生命Lambda connections
      └─ RDS Proxy ── connection pool ──> writer / database

Multi-AZ、read replica與proxy分別解決可用性、讀取擴展與連線管理。""",
    47: """先從每次request知道的key開始
      │
      ▼
Partition key決定資料如何分散
      │
      ├─ 同一key流量過熱 ──> hot partition / throttling
      └─ 分布均勻 ────────> 水平擴展

Sort key讓同一partition內做range/query。
GSI建立另一種查詢入口，但會增加write與storage成本。
DAX/cache只加速可接受cached semantics的讀取，不修正錯誤data model。""",
    52: """Producer很快地送入工作
      │
      ▼
SQS queue保存message並吸收短期burst
      │ ReceiveMessage
      ▼
Consumer開始處理 ── visibility timeout期間暫時隱藏
      │
      ├─ 成功：DeleteMessage
      └─ 失敗／timeout：message再次可見
                     └─ 超過maxReceiveCount ──> DLQ

Queue讓時間解耦，不會讓consumer憑空多出處理能力；duplicate仍需idempotency。""",
    55: """Start workflow
  ├─ 並行查核 A ─┐
  ├─ 並行查核 B ─┼─> Choice：是否進人工核准？
  └─ 並行查核 C ─┘
                         │ task token / callback
                         ▼
                  等待數小時或數天
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
          核准繼續                 拒絕／逾時
             │                       │
             └──── success      compensate / close

State machine保存流程進度；每個business action本身仍要可安全重試。""",
    62: """Business先給RTO / RPO，才選DR成本

Backup & Restore ── 幾乎不常駐 ── 恢復最慢、成本最低
Pilot Light      ── 核心資料常駐 ── 需要啟動其餘服務
Warm Standby     ── 縮小版全系統 ── 可快速擴容接手
Active-Active    ── 多地同時服務 ── 最快但資料與營運最複雜

每一級都必須搬動identity、network、data、dependencies與DNS，並以game day計時。""",
    72: """Git中的Infrastructure as Code
      │ review / test
      ▼
Template + parameters
      │ create Change Set
      ▼
預覽：新增、修改、replacement、delete
      │ approval
      ▼
CloudFormation依dependency順序建立resources
      │
      ├─ 成功：保存stack state與outputs
      └─ 失敗：rollback；資料型resource另需retention保護

同一份設計以不同parameters部署dev、prod與DR，而不是手動重做。""",
    74: """舊版本仍服務100%流量
      │
      ├─ 部署新版本到隔離環境
      ├─ 執行health與business checks
      └─ 逐步切 1% → 5% → 25% → 100%
                         │
            metric超標？ ├─ yes ──> 立即rollback
                         └─ no  ──> 繼續bake

Blue/Green換整套環境；Canary逐步放量；Rolling逐批替換instance。
Database schema必須同時相容新舊application，否則程式rollback也救不回來。""",
    79: """Management account / Organization
      │
      ├─ Security OU：log archive、security tooling
      ├─ Infrastructure OU：network、shared services
      ├─ Workloads OU：prod accounts / non-prod accounts
      └─ Sandbox OU：較小blast radius的實驗

Control Tower / Account Factory提供一致account baseline與guardrails。
中央團隊管理共同道路與安全底線；workload團隊在帳號邊界內獨立交付。
OU是policy繼承樹，不是封包流動的network boundary。""",
    86: """兩千台server inventory
      │
      ├─ 依business application重新分組
      ├─ 發現database、file、identity與network dependencies
      └─ 評估7R與business value
                 │
                 ▼
Wave 0：landing zone / network / identity
Wave 1：低風險且依賴少的applications
Wave 2：共享資料與中度相依applications
Wave N：核心、mainframe或需refactor的系統

每一wave都有owner、cutover、validation、rollback與退出機房條件。""",
    91: """使用者問題
      │ identity / tenant boundary
      ▼
Retrieve：從核准資料找相關片段
      │ grounding context
      ▼
Foundation Model產生候選回答
      │
      ├─ Guardrails檢查內容與敏感資訊
      ├─ Agent tool call另經deterministic authorization
      └─ 高風險動作送human approval
      ▼
回答 + citations + trace / token cost / evaluation result

模型品質與工具權限是兩條不同防線，不能互相取代。""",
    97: """全球使用者
      │
CloudFront / WAF / regional entry
      │
      ├─ Catalog / recommendation：可cache、可降級
      ├─ Cart / order：需要durable state
      └─ Payment：idempotency + authoritative transaction
                         │
                         ▼
                Event / Queue fan-out
                 ├─ inventory
                 ├─ notification
                 └─ analytics

促銷burst先由edge、autoscaling與queue吸收；付款正確性不能為吞吐讓步。""",
    111: """較慢、需要嚴格驗證的Control Plane
管理者 ──> 建立新設定 ──> validate ──> canary rollout ──> published version
                                                        │
                                                        ▼
較快、每次request都依賴的Data Plane
使用者 ──> application ──> 讀本地cache / last-known-good設定 ──> 回應

Control plane短暫故障時，既有data plane仍以最後已知安全版本服務。
錯誤新設定則靠驗證、分波與rollback阻止擴大。""",
}


def analogy_for(topic: Topic) -> tuple[str, str]:
    """Return a concrete analogy and the point where that analogy stops."""

    title = topic.title.lower()
    cases = (
        (
            ("dns", "tcp", "tls", "http"),
            "可以把一次網路請求想成打電話：DNS查號碼，TCP接通線路，TLS核對對方身份，HTTP才是接通後真正說的話。",
            "電話類比無法表達cache、重試與多條網路路徑，所以除錯時仍要逐層看實際metric與log。",
        ),
        (
            ("subnet", "route table", "internet gateway"),
            "VPC像一座園區，subnet是不同街區，route table是每個路口的指示牌，Internet Gateway則是通往公共道路的出口。",
            "街區叫private不會產生魔法；是否能上網仍由有效route、public address與安全規則共同決定。",
        ),
        (
            ("peering", "privatelink", "transit gateway"),
            "Peering像兩個園區直接修一條路，Transit Gateway像中央轉運站，PrivateLink則像只開一個服務窗口而不讓訪客逛完整座園區。",
            "真實網路還有CIDR、DNS、回程與費用；不能只靠類比判斷可達性。",
        ),
        (
            ("cloudfront", "global accelerator", "edge"),
            "CloudFront像把常用商品先放到各地分店，Global Accelerator則像把客戶快速帶上AWS的高速公路，再送往健康的區域入口。",
            "前者理解HTTP與cache，後者主要處理network flow；兩者不是單純的快與更快。",
        ),
        (
            ("alb", "nlb", "load balancer"),
            "Load balancer像接待櫃檯：ALB會讀懂HTTP內容再分流，NLB主要依連線資訊轉送，GWLB則把流量帶去接受安全檢查。",
            "接待櫃檯不能修復後端保存錯誤狀態，也不能取代application authorization。",
        ),
        (
            ("iam", "identity", "policy"),
            "登入像出示員工證，policy像每扇門旁的門禁規則；有證件不代表所有房間都能進。",
            "AWS授權由多層policy共同決定，還要考慮explicit Deny、resource policy與organization guardrail。",
        ),
        (
            ("kms", "envelope encryption", "key policy"),
            "Envelope encryption像用小鑰匙鎖每個箱子，再用受嚴格管理的大鑰匙保護這些小鑰匙。",
            "加密不等於授權；能讀到ciphertext的人仍可能被KMS拒絕解密，反之亦然。",
        ),
        (
            ("s3", "object"),
            "S3比較像大型包裹倉庫：每件物品用完整key存取，而不是在遠端磁碟上任意改其中幾個bytes。",
            "倉庫類比不能取代一致性、multipart upload、versioning與policy細節；它只用來先分清object和file。",
        ),
        (
            ("rds", "aurora", "relational"),
            "關聯式資料庫像一本正式帳簿：交易要讓多個欄位一起成立，讀副本則像提供影本給查詢者使用。",
            "副本可能有延遲，failover也涉及client重新連線；不能把影本當成永遠同步的主帳簿。",
        ),
        (
            ("dynamodb", "partition", "gsi"),
            "DynamoDB像把大量卡片依partition key分到不同抽屜；key選得好就能直接找到，選得差就會讓所有人擠在同一個抽屜。",
            "實際partition由服務管理，類比不代表能手動指定實體節點；仍要用access pattern與capacity metric驗證。",
        ),
        (
            ("sqs", "queue"),
            "Queue像餐廳的出單夾：前台可以先收下工作，廚房按能力處理，失敗的單則移到另一個夾子調查。",
            "出單夾不會創造處理能力，也不保證每張單只被拿一次，所以consumer仍需冪等與backpressure。",
        ),
        (
            ("sns", "eventbridge", "publish-subscribe"),
            "Publish-subscribe像廣播：producer只宣布發生了什麼，各個listener自行決定是否以及如何反應。",
            "廣播不等於持久workflow；delivery、順序、重試與schema仍要依服務分別設計。",
        ),
        (
            ("step functions", "workflow", "human approval"),
            "Workflow像一張可追蹤的辦事流程表：哪些步驟平行、哪裡等待簽核、失敗後要補償，都明白寫在狀態上。",
            "流程引擎只能協調，不能自動讓每個business action具備transaction或冪等性。",
        ),
        (
            ("retry", "idempotency", "exactly-once"),
            "重試像沒聽見店員回覆時再次下單；如果店家沒有訂單編號，就可能真的做出兩份餐點。",
            "Idempotency key只是建立辨識基礎，還需要持久記錄、atomic update與合理的有效期限。",
        ),
        (
            ("rto", "rpo", "disaster", "backup"),
            "RTO像停電後多久必須重新開店，RPO則像最多能接受遺失幾分鐘尚未入帳的交易。",
            "恢復時間與資料落後是兩個不同目標；有備份也不代表能在要求時間內恢復完整服務。",
        ),
        (
            ("cloudformation", "infrastructure as code"),
            "IaC像建築藍圖：它讓每次施工有一致依據，也能在動工前看出哪些牆會被拆掉重建。",
            "藍圖不會自動保護資料；replacement、secret、drift與部署順序仍需明確設計。",
        ),
        (
            ("landing zone", "multi-account"),
            "Landing zone像新城市開發前先鋪好道路、門牌、警報與管理規則，之後每個團隊才能安全地蓋自己的房子。",
            "中央治理不能變成所有變更都排隊等同一個團隊；良好設計同時保留guardrail與delegation。",
        ),
        (
            ("bedrock", "agent", "generative ai"),
            "AI agent像能查資料並操作工具的助理：回答是否合理與它是否被允許執行動作，是兩個完全不同的問題。",
            "類比不能淡化模型的不確定性；production仍要使用評估、policy、approval與完整audit trail。",
        ),
    )
    for keywords, analogy, boundary in cases:
        if any(keyword in title for keyword in keywords):
            return analogy, boundary
    part = part_for(topic.number)["part"]
    _, analogy, principle = PART_LENSES[part]
    return analogy, f"類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：{principle}"


def chapter_story(topic: Topic) -> tuple[str, tuple[str, ...]]:
    """A varied, plain-language chapter opening that starts from a real scene."""

    primary = topic.services[0] if topic.services else topic.title
    peer = topic.services[1] if len(topic.services) > 1 else "相鄰方案"
    lens, _, principle = PART_LENSES[part_for(topic.number)["part"]]
    analogy, boundary = analogy_for(topic)
    openings = (
        f"故事從一個看似簡單的需求開始：{topic.scenario}",
        f"想像你剛接手一個正在上線的系統。團隊告訴你：{topic.scenario}",
        f"星期一早上的架構會議裡，有人把這個問題丟到白板上：{topic.scenario}",
        f"先暫時忘掉AWS服務名稱，只看眼前發生的事：{topic.scenario}",
        f"把鏡頭拉到一個真實的production現場：{topic.scenario}",
        f"如果今天由你值班，收到的需求可能是這樣：{topic.scenario}",
    )
    style = (topic.number - 1) % len(openings)
    opening_tails = (
        "這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。"
        "我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。",
        "看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、"
        "資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。",
        "白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂"
        "使用者究竟在等什麼，以及哪一個結果絕對不能出錯。",
        "這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情"
        "發生的順序走，等路徑清楚後再把服務名稱放回去。",
        "監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事："
        "請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。",
        "值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，"
        "確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。",
    )
    problem_frames = (
        f"這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：{topic.problem} "
        "我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。",
        f"如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：{topic.problem} "
        "這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。",
        f"先把爭論收斂成一句可以被驗證的話：{topic.problem} "
        "服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。",
        f"現在把需求往下挖一層，真正的壓力是：{topic.problem} "
        "只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。",
        f"要讓故事繼續，我們必須先解開核心矛盾：{topic.problem} "
        "這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。",
        f"先別急著開console。請先回答：{topic.problem} "
        "當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。",
    )
    problem_tails = (
        "它也會成為後面判斷設定是否正確的驗收標準。",
        "這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。",
        "稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。",
        "先把這個因果關係站穩，後面的技術細節才會彼此連得起來。",
        "這條問題線會一路貫穿正常流程、故障處理與最後的考題。",
        "接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。",
    )
    problem_frames = tuple(
        frame + " " + tail for frame, tail in zip(problem_frames, problem_tails)
    )
    analogy_frames = (
        f"{analogy} {boundary} 接下來每個技術名詞都會放回這個畫面裡，"
        "讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。",
        f"先借用一個日常畫面：{analogy} {boundary} "
        "類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。",
        f"這裡可以先這樣想：{analogy} 但請同時記住它的邊界：{boundary} "
        "好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。",
        f"為了讓腦中先有畫面，{analogy} {boundary} "
        "等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。",
        f"如果你需要一個暫時的比喻，可以記成：{analogy} {boundary} "
        "後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。",
        f"把抽象概念放回生活裡：{analogy} 這只是起點，因為{boundary} "
        "我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。",
    )
    closing_frames = (
        f"帶著這張圖再看AWS，{primary}會是本章的主要角色，{peer}則幫我們看清邊界。"
        f"方向是「{topic.decision}」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。",
        f"現在才讓服務名稱進場。{primary}負責主要工作，{peer}提醒我們答案不是永遠固定。"
        f"本章會走向「{topic.decision}」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。",
        f"回到AWS世界，主角是{primary}，對照角色是{peer}。我們選擇「{topic.decision}」，"
        "不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。",
        f"接下來的閱讀順序很簡單：先看{primary}如何接手工作，再看{peer}何時更合適，"
        f"最後用設定與考題驗證「{topic.decision}」是否真的能從需求一路推導出來。",
        f"有了問題和畫面，AWS名稱才不會只是縮寫。{primary}是這一章的入口，{peer}用來畫出邊界；"
        f"主要方向「{topic.decision}」會在後面的正常流程與故障流程中被逐步證明。",
        f"於是我們得到一條可以繼續追查的路：由{primary}承接主要責任，以{peer}檢查替代條件，"
        f"並用「{topic.decision}」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。",
    )
    return (
        f"{lens}：先從故事開始",
        (
            openings[style] + " " + opening_tails[style],
            problem_frames[style],
            analogy_frames[style],
            closing_frames[style],
        ),
    )


def term_cards(topic: Topic) -> tuple[tuple[str, str, str], ...]:
    service = topic.services[0] if topic.services else topic.title
    second = topic.services[1] if len(topic.services) > 1 else "Alternative"
    return (
        (
            service,
            f"本章主要mechanism或服務。它存在是為了解決：{topic.problem}",
            f"在「{topic.scenario}」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。",
        ),
        (
            second,
            f"用來比較邊界的相鄰選項。它在不同constraint下可能合理：{topic.alternative}",
            "考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。",
        ),
        (
            "Failure boundary",
            f"元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：{topic.failure}",
            "看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。",
        ),
        (
            "Portable pattern",
            f"不依賴AWS品牌仍成立的原則：{topic.pattern}。",
            "換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。",
        ),
    )


def blueprint(topic: Topic) -> str:
    profile_rows = [
        (name, component_profile(name, topic))
        for name in (topic.services or (topic.title,))
    ]
    primary_name, primary = profile_rows[0]
    supporting = "\n".join(
        f"  · {name}：{short(profile.purpose, 54)}"
        for name, profile in profile_rows[1:]
    ) or "  · 沒有額外服務；重點是把主要責任與application邊界說清楚"
    part = part_for(topic.number)["part"]
    header = f"場景：{short(topic.scenario, 72)}"
    footer = (
        f"失敗時先找：{short(topic.failure, 70)}\n"
        "證明完成：使用者結果 + latency/error + audit/log + recovery test"
    )
    if topic.number in SPECIAL_BLUEPRINT_BODIES:
        return f"{header}\n\n{SPECIAL_BLUEPRINT_BODIES[topic.number]}\n\n{footer}"
    if part == 1:
        body = (
            "來源（使用者／VPC／on-premises）\n"
            "          │ ① 名稱解析：要連到哪個位址？\n"
            "          │ ② 去程 route + network policy\n"
            f"          ▼\n[{primary_name}]\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          ▼\n[target／application state]\n"
            "          │ ③ response沿有效回程返回\n"
            "控制面：建立DNS、route、listener、policy與health設定\n"
            "資料面：每個packet／connection／request實際沿路通過\n"
            f"本章其他角色：\n{supporting}"
        )
    elif part == 2:
        body = (
            "人或workload提出request\n"
            "          │ ① 取得短期身份／credential\n"
            "          │ ② 合併identity、resource與organization規則\n"
            f"          ▼\n[{primary_name}] ── Allow / Deny ──> protected resource\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          │ ③ 需要時再通過network與KMS邊界\n"
            "          ▼\n[protected data／operation]\n"
            "證據面：CloudTrail／finding／Config記錄誰在何時做了什麼\n"
            f"本章其他角色：\n{supporting}"
        )
    elif part == 3:
        body = (
            "request／event／batch job抵達\n"
            "          │ ① admission與工作規格\n"
            f"          ▼\n[{primary_name}]\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          │ ② scheduler／load balancer選擇runtime並執行\n"
            "          │ ③ 讀寫外部state；runtime本身應可替換\n"
            "          ▼\n[database／queue／object storage]\n"
            "容量迴路：demand signal → scale → warm up → health → drain\n"
            f"本章其他角色：\n{supporting}"
        )
    elif part == 4:
        body = (
            "application先提出一個具體access pattern\n"
            "          │ ① key／query／file／object語意\n"
            f"          ▼\n[{primary_name}：authoritative或主要資料路徑]\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          │ ② replica／cache／index服務不同讀取需求\n"
            "          │ ③ backup／archive保護另一種失敗\n"
            "          ▼\n[recovery copy]\n"
            "唯一真相、複寫、一致性與restore必須分開說明\n"
            f"本章其他角色：\n{supporting}"
        )
    elif part == 5:
        body = (
            "producer完成自己的business action\n"
            "          │ ① 發出message／event／record\n"
            f"          ▼\n[{primary_name}]\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          │ ② 保存、路由、排序或協調後交給consumer\n"
            "          │ ③ 成功checkpoint；失敗retry／DLQ／compensate\n"
            "          ▼\n[business state]\n"
            "交付可能重複，因此side effect必須可安全重做\n"
            f"本章其他角色：\n{supporting}"
        )
    elif part in (6, 7):
        body = (
            "正常production路徑\n"
            f"          ▼\n[{primary_name}] → 使用者可觀察的結果\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          │\n"
            "          ├─ telemetry偵測使用者影響\n"
            "          ├─ health／alarm決定隔離或停止推出\n"
            "          └─ recovery path執行replace／failover／rollback\n"
            "演練：注入故障 → 計時偵測 → 恢復資料與服務 → 驗證\n"
            "成本：常駐容量、資料複製與營運工作都要被計入\n"
            f"本章其他角色：\n{supporting}"
        )
    elif part == 8:
        body = (
            "Organization／business portfolio\n"
            "          │ ① identity、policy與account vending\n"
            f"          ▼\n[{primary_name}]\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          │ ② shared network／security／logging平台\n"
            "          │ ③ workload teams在guardrail內獨立交付\n"
            "          ▼\n[member accounts／workloads]\n"
            "Operating model：owner + delegation + evidence + rollout/rollback\n"
            f"本章其他角色：\n{supporting}"
        )
    elif part == 9:
        body = (
            "使用者問題／agent任務\n"
            "          │ ① identity、tenant與內容檢查\n"
            f"          ▼\n[{primary_name}]\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          │ ② retrieval／model產生不確定的建議\n"
            "          │ ③ deterministic policy限制tool與高風險action\n"
            "          ▼\n[human approval／authorized action]\n"
            "Eval與audit同時檢查quality、security、latency與token cost\n"
            f"本章其他角色：\n{supporting}"
        )
    else:
        body = (
            "商業需求與不能妥協的限制\n"
            f"          ▼\n[{primary_name}：主要責任]\n"
            f"          │ {short(primary.purpose, 58)}\n"
            "          ├─ 正常路徑：輸入 → 決策 → 資料變更 → 使用者結果\n"
            "          └─ 故障路徑：偵測 → 隔離 → retry／rollback／restore\n"
            f"本章其他角色：\n{supporting}\n"
            f"可移植原則：{topic.pattern}"
        )
    return f"{header}\n\n{body}\n\n{footer}"


def mental_model(topic: Topic) -> str:
    primary = topic.services[0] if topic.services else topic.title
    peer = topic.services[1] if len(topic.services) > 1 else "相鄰方案"
    lens, _, principle = PART_LENSES[part_for(topic.number)["part"]]
    return (
        f"如果只記得一件事，請記得「{lens}」。先不要急著問{primary}有多少功能，"
        f"而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，"
        "它替系統保留了什麼狀態，下一站又依賴它提供什麼。\n\n"
        f"這樣看就會發現，{primary}和{peer}並不是兩個任意的產品名稱。前者適合本章，是因為"
        f"「{topic.decision}」直接回應了眼前的問題；後者描述的「{topic.alternative}」只有在需求改變時"
        "才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。\n\n"
        f"最後再從失敗方向倒著走一次：{topic.failure} 如果真的發生，哪個訊號會先變壞，"
        "哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——"
        f"「{topic.pattern}」。更白話地說：{principle}"
    )


def mechanics(topic: Topic) -> tuple[str, ...]:
    services = list(topic.services) or [topic.title]
    return (
        f"Requirement gate：將場景拆成安全、可靠、效能、成本與營運限制；本章核心限制是「{topic.problem}」。",
        f"Entry/control：由{services[0]}或對應control plane接收設定與流量，先完成identity、route或admission判斷。",
        f"State/data：追蹤state owner、replica、queue、key或connection；不能把managed service誤當沒有state。",
        f"Decision：套用「{topic.decision}」，並寫下為何「{topic.alternative}」在本題不是最佳選項。",
        f"Failure path：主動注入timeout、quota、AZ、permission或dependency failure，觀察是否出現「{topic.failure}」。",
        f"Evidence loop：用business metric、CloudWatch、CloudTrail、Config、trace或cost data確認結果，而非只看部署成功。",
    )


def tradeoffs(topic: Topic) -> tuple[str, ...]:
    return (
        f"主要方案：{topic.decision}",
        f"答案翻轉條件：{topic.alternative}",
        f"最大failure mode：{topic.failure}",
        f"跨雲保留的原則：{topic.pattern}",
    )


def code_example(topic: Topic) -> tuple[str, tuple[str, ...]]:
    n = topic.number
    title = repr(topic.title)
    decision = repr(short(topic.decision, 96))
    alternative = repr(short(topic.alternative, 96))
    failure = repr(short(topic.failure, 96))
    pattern = repr(topic.pattern)
    if 11 <= n <= 20:
        code = f'''from ipaddress import ip_network, ip_address

routes = [
    (ip_network("10.0.0.0/8"), "private-or-hybrid-path"),
    (ip_network("10.20.0.0/16"), "more-specific-workload-path"),
    (ip_network("0.0.0.0/0"), "default-egress"),
]
destination = ip_address("10.20.7.9")
matches = [(net.prefixlen, target) for net, target in routes if destination in net]
selected = max(matches)
print({title})
print("longest-prefix route:", selected[1])
print("decision:", {decision})
print("failure to test:", {failure})
'''
        steps = (
            "Route lookup不是從上到下選第一條，而是選prefix最長的matching route。",
            "將destination改成其他CIDR，觀察private path、workload path與default egress如何切換。",
            f"把route結果接回本章決策：{topic.decision}",
            f"再補上return route與policy測試，否則仍可能發生：{topic.failure}",
        )
    elif 21 <= n <= 31:
        code = f'''requests = [
    {{"principal": "workload-role", "allowed": True, "explicit_deny": False}},
    {{"principal": "temporary-admin", "allowed": True, "explicit_deny": True}},
    {{"principal": "unknown", "allowed": False, "explicit_deny": False}},
]

def authorize(item):
    if item["explicit_deny"]:
        return "DENY"
    return "ALLOW" if item["allowed"] else "DENY"

print({title})
for request in requests:
    print(request["principal"], authorize(request))
print("boundary:", {pattern})
'''
        steps = (
            "模型先處理explicit deny，再判斷是否存在applicable allow；這是政策交集的核心。",
            "將SCP、boundary與resource policy想成更多獨立條件，而不是互相覆蓋的設定。",
            f"本章的建議是：{topic.decision}",
            f"如果只看單一allow，可能漏掉：{topic.failure}",
        )
    elif 32 <= n <= 40:
        code = f'''from math import ceil

incoming_per_second = 2400
safe_capacity_per_worker = 180
headroom = 1.25
workers = ceil(incoming_per_second * headroom / safe_capacity_per_worker)
print({title})
print("required workers:", workers)
print("scale on demand signal, not a familiar metric")
print("decision:", {decision})
'''
        steps = (
            "先把arrival rate、單worker安全capacity與headroom分開，避免直接猜instance數。",
            "將capacity改小可模擬cold start、connection或CPU以外的瓶頸。",
            f"數字模型只是證據；真正服務選擇仍由本章規則決定：{topic.decision}",
            f"若metric與瓶頸無關，會出現：{topic.failure}",
        )
    elif 41 <= n <= 51:
        code = f'''candidates = {{
    "primary": {{"latency": 5, "durability": 5, "cost": 3, "semantic_fit": 5}},
    "alternative": {{"latency": 3, "durability": 4, "cost": 4, "semantic_fit": 2}},
}}
weights = {{"latency": 3, "durability": 3, "cost": 2, "semantic_fit": 5}}

def score(values):
    return sum(values[key] * weights[key] for key in weights)

print({title})
for name, values in candidates.items():
    print(name, score(values))
print("primary rule:", {decision})
print("alternative boundary:", {alternative})
'''
        steps = (
            "Semantic fit權重最高，表示先選access semantics，再比較容量與單價。",
            "調整weights可模擬低成本、低延遲或合規優先，答案也可能翻轉。",
            f"Primary代表：{topic.decision}",
            f"Alternative只在不同constraint下合理：{topic.alternative}",
        )
    elif 52 <= n <= 60:
        code = f'''from collections import deque

queue = deque(range(12))
processed = []
capacity_per_tick = 4
for tick in range(3):
    batch = [queue.popleft() for _ in range(min(capacity_per_tick, len(queue)))]
    processed.extend(batch)
    print("tick", tick, "processed", batch, "backlog", len(queue))

print({title})
print("at-least-once consumers must be idempotent")
print("failure boundary:", {failure})
'''
        steps = (
            "Queue將producer時間與consumer時間解耦，但capacity不變時backlog仍會累積。",
            "把capacity調成小於arrival rate，觀察queue depth與age為何持續增加。",
            f"本章主要mechanism是：{topic.decision}",
            f"Consumer、retry與deadline設計不完整時會造成：{topic.failure}",
        )
    elif 61 <= n <= 71:
        code = f'''components = [
    ("entry", 0.9999),
    ("application", 0.999),
    ("state", 0.9995),
]
end_to_end = 1.0
for name, availability in components:
    end_to_end *= availability
print({title})
print("series availability:", round(end_to_end, 6))
print("monthly unavailable minutes:", round((1 - end_to_end) * 30 * 24 * 60, 2))
print("rule:", {pattern})
'''
        steps = (
            "同步critical path的availability近似相乘，新增required dependency可能降低整體可用性。",
            "這是簡化模型；共同故障與correlated failure會讓實際結果更差。",
            f"本章的架構動作是：{topic.decision}",
            f"模型必須以game day與真實metric校準，特別防止：{topic.failure}",
        )
    elif 72 <= n <= 78:
        code = f'''population = 1000
stages = [0.01, 0.05, 0.25, 1.0]
error_rate = 0.004
threshold = 0.01
print({title})
for fraction in stages:
    exposed = int(population * fraction)
    observed_errors = exposed * error_rate
    print(f"exposure={{fraction:.0%}} users={{exposed}} errors≈{{observed_errors:.1f}}")
    if error_rate > threshold:
        print("ROLL BACK")
        break
print("deployment rule:", {decision})
'''
        steps = (
            "逐階段增加exposure，讓未知bug先影響較小blast radius。",
            "真正gate應使用business與technical metrics，不只deployment process狀態。",
            f"本章的reversible action是：{topic.decision}",
            f"缺少preview、rollback或owner可能導致：{topic.failure}",
        )
    elif 79 <= n <= 90:
        code = f'''dependencies = {{
    "identity": set(),
    "network": {{"identity"}},
    "shared-data": {{"network"}},
    "application": {{"identity", "network", "shared-data"}},
}}
done = set()
waves = []
while len(done) < len(dependencies):
    ready = sorted(name for name, deps in dependencies.items() if name not in done and deps <= done)
    waves.append(ready)
    done.update(ready)
print({title})
print("dependency-aware waves:", waves)
print("enterprise rule:", {pattern})
'''
        steps = (
            "Dependency graph先安排identity/network/shared data，再安排依賴它們的workload。",
            "真實portfolio還要加入business calendar、owner、data gravity與rollback。",
            f"企業級決策是：{topic.decision}",
            f"若只依server清單排序，容易發生：{topic.failure}",
        )
    elif 91 <= n <= 96:
        code = f'''requests = [
    {{"action": "read-document", "risk": 1}},
    {{"action": "restart-test-service", "risk": 3}},
    {{"action": "delete-production-data", "risk": 10}},
]
approval_threshold = 5
print({title})
for request in requests:
    route = "HUMAN_APPROVAL" if request["risk"] >= approval_threshold else "POLICY_CHECK"
    print(request["action"], "->", route)
print("AI boundary:", {pattern})
'''
        steps = (
            "模型把probabilistic建議與deterministic authorization分開。",
            "Risk分數只是示意；production需由action、resource、requester與reversibility共同決定。",
            f"本章建議的控制是：{topic.decision}",
            f"若agent擁有共享高權限credential，可能造成：{topic.failure}",
        )
    else:
        code = f'''requirements = {{"security": 5, "reliability": 5, "performance": 3, "cost": 2, "operations": 4}}
candidates = {{
    "recommended": {{"security": 5, "reliability": 5, "performance": 4, "cost": 3, "operations": 5}},
    "alternative": {{"security": 3, "reliability": 3, "performance": 4, "cost": 5, "operations": 2}},
}}

def weighted_score(candidate):
    return sum(requirements[key] * candidate[key] for key in requirements)

print({title})
for name, candidate in candidates.items():
    print(name, weighted_score(candidate))
print("decision:", {decision})
print("portable pattern:", {pattern})
'''
        steps = (
            "把需求顯式化後，服務比較才不是憑熟悉度或品牌。",
            "分數只是討論工具；hard constraint不應被其他高分抵消。",
            f"Recommended對應：{topic.decision}",
            f"Alternative與failure邊界是：{topic.alternative}／{topic.failure}",
        )
    return code, steps


def community_insight(topic: Topic) -> str:
    return (
        f"社群筆記常把本章濃縮為「{short(topic.decision, 84)}」。這種口訣適合最後複習，"
        f"卻不能取代mechanism。最常見的誤用，是忽略「{short(topic.alternative, 72)}」其實"
        "可能在另一組constraint下正確。本文因此保留比較表、failure path與反例；技術事實"
        "仍以官方文件校準，社群來源只用來發現高頻卡點、易混淆服務與讀題策略。"
    )


def labs(topic: Topic) -> tuple[str, ...]:
    return (
        f"用自己的話重寫場景與hard constraints：{topic.scenario}",
        f"畫出正常data path，標記每個state owner與同步dependency；至少包含{', '.join(topic.services[:3]) or topic.title}。",
        f"修改一個真實設定或場景constraint，重新畫data path，觀察答案為何會轉向「{topic.alternative}」。",
        f"設計一個最小failure injection來重現「{topic.failure}」，並列出metric/log/audit evidence。",
        f"拿掉所有AWS名稱，只用「{topic.pattern}」向同學解釋同一設計。",
    )


def qas(topic: Topic) -> tuple[tuple[str, str], ...]:
    task_names = "；".join(f"{task} {TASKS[task]}" for task in topic.tasks[:4])
    return (
        (
            f"為什麼本章不能只背「{short(topic.decision, 54)}」？",
            f"因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「{topic.problem}」，"
            f"所以「{topic.decision}」能直接滿足它；若constraint改成「{topic.alternative}」，答案可能翻轉。"
            f"專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。",
        ),
        (
            "主要方案與相鄰替代方案的真正分界是什麼？",
            f"主要方案是「{topic.decision}」。替代方案「{topic.alternative}」並非錯誤，而是優化不同目標。"
            "比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；"
            "只比較feature名稱通常會選錯。",
        ),
        (
            "如果系統已經部署，最先應監控或驗證哪個 failure mode？",
            f"先針對「{topic.failure}」建立可重現測試。觀察business success、latency/error、queue或replica lag、"
            "CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。"
            "只有看到部署成功或單一CPU metric，不能證明架構滿足需求。",
        ),
        (
            "SAA 題目通常如何考這個主題？",
            f"SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出"
            f"「{topic.problem}」，排除會導致「{topic.failure}」的選項，再選「{topic.decision}」。"
            f"本章對應的代表task包括：{task_names}。",
        ),
        (
            "SAP 會如何把同一題加深？",
            f"SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等"
            f"互相拉扯的限制。答案除了「{topic.decision}」，還要描述delegation、blast radius、rollout、"
            "rollback、evidence與長期operating model；只選一項服務通常不夠。",
        ),
        (
            "把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？",
            f"留下的是「{topic.pattern}」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、"
            "自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，"
            "不是pattern本身。",
        ),
    )
