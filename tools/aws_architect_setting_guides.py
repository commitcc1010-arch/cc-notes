"""Self-contained explanations for AWS settings and recurring architecture terms."""
from __future__ import annotations

from dataclasses import dataclass
import re

from aws_architect_model import Topic
from aws_architect_profiles import ComponentProfile


@dataclass(frozen=True)
class SettingGuide:
    name: str
    controls: str
    when: str
    configure: str
    pitfall: str


def S(
    name: str,
    controls: str,
    when: str,
    configure: str,
    pitfall: str,
    expanded_pitfall: str | None = None,
) -> SettingGuide:
    if expanded_pitfall is not None:
        # Some generated-category rules pass a generic applicability sentence
        # before their more precise use case. Keep the precise four teaching
        # fields and discard that generic sentence.
        return SettingGuide(name, controls, configure, pitfall, expanded_pitfall)
    return SettingGuide(name, controls, when, configure, pitfall)


EXPLICIT_GUIDES: dict[str, tuple[SettingGuide, ...]] = {
    "AWS Certification": (
        S(
            "exam version",
            "指定你準備的是哪一份公開考試藍圖，例如SAA-C03或SAP-C02。不同版本可能調整domain、task、服務範圍與題目深度。",
            "開始讀書、考試改版，或使用任何筆記與題庫以前，都要先確認版本與有效日期。",
            "從AWS Certification官方exam guide記錄exam code、發布／更新日期、domains與附錄；把本書章節及mock題映射到同一版本。",
            "只寫「SAA」或「SAP」而不記exam code，容易把舊版權重、已改名服務或非本版本考點混入讀書計畫。",
        ),
        S(
            "domain weights",
            "Domain是考試藍圖中的能力領域；weight是該領域約占計分內容的比例，用來分配複習時間，不是DNS網域或每次考試固定題數。",
            "需要排兩到三週讀書計畫，或模擬考顯示多個能力領域同時薄弱、必須決定補強順序時。",
            "把官方domain名稱與百分比抄入coverage matrix，再以「權重 × 自己的錯題率」排優先序；每週重新計算而不是平均分配時間。",
            "高權重不代表只讀服務名稱；低權重也不能完全跳過。實際scenario常同時跨安全、可靠、效能與成本領域。",
        ),
        S(
            "task statements",
            "Task statement把domain拆成可被情境題驗證的工作能力，例如設計安全存取、選擇migration策略或改善可靠性。",
            "要判斷某章或某道題到底在訓練哪種架構決策，而不是只記住答案中的服務名稱時。",
            "為每道錯題標記一個主要task與一個次要task，寫下hard constraint、正解機制與答案翻轉條件；以task覆蓋率找盲區。",
            "把task statement當成固定題庫會過度擬合；同一task可由完全不同服務與產業情境出題。",
        ),
        S(
            "in-scope services",
            "表示考試可能用來描述架構情境的AWS服務集合；in scope不代表每項同深度，也不表示附錄外服務絕不出現在干擾選項。",
            "建立服務學習清單，決定哪些要會選型、哪些要認得整合關係與主要設定時。",
            "依官方附錄把服務映射到identity、network、compute、data、integration與operations；每項至少寫purpose、mechanism、choose、replace與一個常考設定。",
            "逐項背產品型錄效率很低；服務的實際限制與設定仍應回到產品文件，不能把exam guide當完整產品規格。",
        ),
        S(
            "官方sample questions",
            "官方sample questions展示題幹長度、限制詞、複選格式與逐選項推理深度，用來校準讀題方式，不是完整題庫。",
            "開始準備、考試版本更新，或想檢查自己是在背答案還是真的能從constraint推出方案時。",
            "先限時作答，再為每個選項寫「滿足了什麼、漏了什麼、何時會變正解」；將錯因回填到domain/task coverage matrix。",
            "只背少量sample答案會嚴重過度擬合，也不能由sample出現次數推論正式考試的服務分布。",
        ),
    ),
    "AWS Regions": (
        S(
            "Region選擇",
            "決定workload部署在哪個地理AWS區域；它同時影響使用者延遲、data residency、服務可用性、價格與故障隔離。",
            "建立任何production workload、跨Region DR，或法規指定資料必須位於特定國家／區域時。",
            "建立候選Region矩陣，逐項驗證使用者latency、法規、所需服務／instance types、quota、價格與DR配對，再把Region做成IaC參數。",
            "只選離使用者最近的Region可能違反資料位置或缺少必要服務；只選最便宜Region也可能增加延遲與跨Region傳輸費。",
        ),
        S(
            "service availability",
            "表示某項AWS服務、功能、instance family或managed integration是否已在目標Region提供；不同Region不保證功能完全相同。",
            "架構使用較新服務、特定accelerator、Local Zone、Global Database或跨服務整合時，必須在設計階段確認。",
            "逐一檢查官方Regional Services清單與產品文件，並在目標account/Region呼叫Describe/List API或以小型IaC stack驗證；同時確認quota。",
            "Console中看得到服務名稱不代表所需feature、engine version或capacity可用；DR Region也不能假設和primary完全對稱。",
        ),
        S(
            "data residency",
            "描述資料必須儲存、處理或備份在哪些地理邊界，以及哪些metadata、logs、keys或support流程也受限制。",
            "受法規、客戶合約、資料主權、安全分類或跨境傳輸規則約束，且必須留下可稽核部署證據時。",
            "先分類data types與允許位置，再檢查每個service的storage、backup、replication、logging與KMS Region；用SCP／Config與IaC guardrails限制部署位置。",
            "只把主database放在指定Region不夠；backup、log、snapshot copy、analytics export與support evidence也可能把資料帶到其他Region。",
        ),
        S(
            "cross-Region replication",
            "把資料或artifact非同步／同步複製到另一Region，以支援讀取延遲、災難復原或資料分發；不同服務的一致性與failover語意不同。",
            "整個Region中斷仍需達到指定RPO/RTO，或全球讀取需要在地副本時。",
            "選擇authoritative writer、replication destination、KMS keys、網路與conflict規則；持續監控lag，並演練promotion、DNS切換與failback。",
            "有副本不代表可立即接手，也不等於backup；錯誤刪除可能同步複製，client與dependencies也可能仍指向舊Region。",
        ),
        S(
            "transfer cost",
            "計算資料跨AZ、跨Region、經NAT／Transit Gateway／Internet或回源時的流量費；方向與路徑會影響計價。",
            "高流量架構、集中式inspection、跨Region資料庫、data lake或CDN origin設計時。",
            "畫出每GB的實際data path與方向，使用Pricing Calculator及Cost and Usage Report驗證；監控NAT、cross-AZ與inter-Region bytes並計算每筆交易成本。",
            "只比較compute單價會漏掉巨額網路費；為了省錢把所有元件塞同一AZ，又可能破壞availability要求。",
        ),
    ),
    "Amazon VPC": (
        S(
            "IPv4／IPv6 CIDR",
            "定義VPC可分配的IP位址範圍；subnet必須從這個範圍切割。CIDR重疊會讓peering、TGW與hybrid routing難以判斷封包目的地。",
            "建立新環境、預留成長空間，或未來要連接其他VPC與on-premises時先決定。",
            "建立VPC時設定CidrBlock；要擴充可加入secondary CIDR。先以IPAM或地址表檢查所有既有network，避免只看目前一個帳號。",
            "把每個VPC都設成10.0.0.0/16很快會重疊；CIDR很大也不代表subnet、route與安全邊界設計良好。",
        ),
        S(
            "subnets",
            "把VPC位址切成單一AZ內的部署與route-table邊界。Subnet本身不叫public或private，真正差異是route與resource是否有public IP。",
            "需要跨AZ高可用、分隔web/app/data tiers，或建立inspection、egress與endpoint subnets時。",
            "為每個AZ建立獨立subnet並關聯明確route table；private subnet不要自動分配public IP，並預留足夠可用地址給ENI與擴展。",
            "只建立兩個名稱叫public/private的subnet卻共用錯誤route table，會讓資料庫意外取得internet path或讓app無法出站。",
        ),
        S(
            "route tables",
            "依目的CIDR做longest-prefix match並選擇下一跳，例如local、IGW、NAT、TGW、peering connection或VPC endpoint。",
            "任何跨subnet、Internet、AWS service、VPC或on-premises的封包都要先證明去程與回程route成立。",
            "把route table明確關聯到subnet；新增destination與target後，再到另一側建立return route。使用Flow Logs與reachability analysis驗證實際路徑。",
            "只有去程route沒有回程route、把private subnet的0.0.0.0/0指到IGW，或忘記更精確route會優先匹配，都是常見故障。",
        ),
        S(
            "DNS support／DNS hostnames",
            "EnableDnsSupport控制VPC能否使用Amazon-provided DNS resolver；EnableDnsHostnames控制具有public IPv4的instance是否取得對應DNS hostname。",
            "workload用hostname存取AWS service、private hosted zone、service discovery，或要啟用peering DNS resolution時。",
            "在VPC attributes開啟DNS resolution與DNS hostnames，IaC分別使用EnableDnsSupport與EnableDnsHostnames；再設定private hosted zone或Resolver rules。",
            "DNS能把名稱翻成IP，但不會建立route、security group或IAM permission；名稱解析成功仍可能完全連不到目標。",
        ),
        S(
            "Flow Logs",
            "記錄ENI、subnet或VPC層的accepted/rejected flow metadata，用來判斷封包是否到達、被拒絕及走哪個介面。",
            "除錯timeout、驗證segmentation、建立network forensic evidence或流量基線時。",
            "選擇traffic type、aggregation interval、欄位格式與CloudWatch Logs/S3/Firehose destination；先確認service role與retention。",
            "Flow Logs不是packet capture，不會保存payload，也看不到application-level HTTP錯誤；只靠它無法證明IAM或應用程式成功。",
        ),
    ),
    "VPC Peering": (
        S(
            "acceptance",
            "Peering先由requester提出，再由accepter同意；只有狀態成為active後才可承載route與修改DNS選項。",
            "兩個VPC需要直接private-IP連線，且CIDR不重疊、不需要transitive routing時。",
            "建立AWS::EC2::VPCPeeringConnection或create-vpc-peering-connection，讓另一側accept；跨帳號要先確認account/VPC ID與owner。",
            "接受連線不會自動建立route、DNS或security rules；把active誤認成application已可通是最常見錯法。",
        ),
        S(
            "routes",
            "告訴每個subnet：目的地是peer CIDR時，把封包送到pcx-* peering connection。去程與回程都必須各自存在。",
            "Peering active後，應用需要由一側subnet存取另一側private IP時。",
            "在VPC A相關route table加入「VPC B CIDR → pcx-id」，並在VPC B加入相反route；只開放真正需要互通的subnets。",
            "VPC A連B、A連C不代表B可經A到C；VPC peering不提供transitive routing，route也不能修正重疊CIDR。",
        ),
        S(
            "DNS resolution",
            "DNS resolution是把hostname翻成IP。啟用peering DNS選項後，跨peering查詢EC2 public DNS hostname時可得到peer的private IPv4，讓封包留在私網路徑。",
            "程式以DNS hostname而不是固定private IP連接peer EC2，且希望解析結果走private address時。",
            "先讓兩個VPC啟用DNS support/hostnames並使peering為active；再由requester與accepter owner各自開啟AllowDnsResolutionFromRemoteVpc。CLI使用modify-vpc-peering-connection-options。",
            "這個選項不會讓你直接查詢peer VPC的Amazon DNS server，也不會建立route、SG規則或任意private hosted zone關聯。",
        ),
        S(
            "security-group references",
            "允許SG規則用peer VPC的security group作為source/destination，以workload身份取代容易變動的IP清單。",
            "同Region peering中，app instances經常更換IP，但服務角色與SG邊界穩定時。",
            "在支援的peering情境使用peer account/SG作規則來源，並同時檢查target port與雙方outbound；不支援時退回CIDR或prefix管理。",
            "SG reference不會建立route，也不能跨任意transitive network；刪除peer或SG後要清理stale references。",
        ),
        S(
            "non-overlapping CIDRs",
            "每個VPC必須能以唯一目的prefix被routing；若地址重疊，同一IP可能同時代表local與peer資源。",
            "建立peering之前，以及併購、hybrid network或多帳號環境規劃階段。",
            "比較VPC所有primary/secondary CIDRs與on-premises ranges；大型環境以VPC IPAM分配，已重疊時考慮renumber、PrivateLink或application proxy。",
            "NAT不能普遍消除所有重疊routing語意；硬把重疊網路peer起來通常在建立連線或路由時就被阻止。",
        ),
    ),
    "AWS PrivateLink": (
        S(
            "endpoint service acceptance",
            "控制provider是否必須逐一接受consumer建立的interface endpoint connection request；它是連線核准，不是封包路由設定。",
            "Provider只信任特定consumer、需要人工／自動審批，或allowed principals範圍較廣但仍要二次確認時。",
            "建立endpoint service時設定AcceptanceRequired；收到request後由provider accept/reject。若關閉，任何已被allowed principals授權的request會自動接通。",
            "AcceptanceRequired=false不代表公開給所有人；consumer仍須先符合allowed principals。已接受也不會自動放行NLB target、SG或private DNS。",
        ),
        S(
            "allowed principals",
            "指定哪些AWS accounts、roles、users或organization principals有資格建立連到endpoint service的interface endpoint。",
            "跨帳號SaaS、中央平台服務或只允許organization內特定consumer使用時。",
            "在endpoint service permissions加入具體principal ARN；搭配acceptance policy決定自動或人工核准，並以未授權account做反向測試。",
            "授權整個organization再關閉acceptance會擴大consumer範圍；這也只授權建立連線，不等於後端application已完成身份驗證。",
        ),
        S(
            "provider NLB",
            "Network Load Balancer是endpoint service的provider入口，把PrivateLink連線導向實際service targets，同時隱藏provider VPC的完整route domain。",
            "要發布TCP/TLS服務、支援大量連線，或consumer與provider CIDR重疊而不能建立一般routing時。",
            "建立internal NLB與healthy target groups，再用它建立endpoint service；逐AZ開啟服務並驗證target health、listener port及capacity。",
            "NLB target不健康時endpoint仍可能建立成功但request失敗；PrivateLink也不是任意VPC-to-VPC雙向連線。",
        ),
        S(
            "interface endpoint subnets／SG",
            "Consumer在每個選定AZ建立endpoint ENI與private IP；security group控制clients可連入該ENI的protocol與port。",
            "Consumer要由多個AZ私下存取service，並將入口限制在特定application security groups時。",
            "選擇每個需要的AZ/subnet並附least-privilege SG；client DNS解析後應得到endpoint ENI地址，再逐AZ測試route、SG與回應。",
            "只在單一AZ建立endpoint會形成可用性與跨AZ成本問題；SG附錯方向或port時，DNS正常但TCP仍會timeout。",
        ),
        S(
            "private DNS",
            "讓consumer使用provider驗證過的自訂service hostname時，VPC resolver把該名稱解析成interface endpoint private IP，而非public endpoint。",
            "希望application沿用穩定名稱，不暴露vpce-* DNS名稱，或同一SDK hostname在VPC內自動走PrivateLink時。",
            "Provider設定並驗證private DNS name的domain ownership；consumer endpoint啟用private DNS，且VPC開啟DNS support/hostnames，再用dig驗證。",
            "Private DNS只改名稱答案，不會建立SG、後端authorization或跨VPC route；同名private hosted zone也可能遮蔽預期答案。",
        ),
    ),
    "AWS Transit Gateway": (
        S(
            "attachments",
            "Attachment把VPC、VPN、Direct Connect gateway、peering或Connect連到一個regional Transit Gateway，形成可被TGW routing管理的入口。",
            "需要hub-and-spoke、transitive routing、集中egress／inspection或大量network互連時。",
            "建立attachment並選擇正確subnets/AZ；VPC route table仍要把remote CIDRs指向TGW，另一側也要有return path。",
            "Attachment available只代表control plane完成；沒有VPC routes、TGW routes、DNS與security policy時，application仍完全不通。",
        ),
        S(
            "association",
            "每個attachment一次只能關聯一張TGW route table；該表決定從此attachment進入的封包要依哪組routes轉送。",
            "要把production、shared services、inspection與isolated networks分成不同route domains時。",
            "停用不適合的default association，為每個attachment指定入口route table；以來源attachment逐一驗證可見目的地。",
            "Association不是把attachment的CIDR發布給別人；把它和propagation混淆會造成黑洞或意外互通。",
        ),
        S(
            "propagation",
            "把attachment可到達的prefix動態加入指定TGW route table，讓使用該表的其他來源知道如何前往該attachment。",
            "VPC/VPN/DX routes很多或會變動，不想逐條維護static routes時。",
            "只對應該學到該prefix的route tables啟用propagation；配合static blackhole/inspection routes與route export持續驗證。",
            "Propagation到某張表不會改變attachment自己的association；過度propagate會破壞segmentation並擴大blast radius。",
        ),
        S(
            "TGW route tables",
            "保存destination prefix到attachment的next hop；可用多張表建立transitive hub中的segmentation與service chaining。",
            "VPC數量增加、不同環境需要不同可達性，或所有跨網流量必須先經inspection VPC時。",
            "為route domain建立獨立表，設association、propagation、static及blackhole routes；逐來源畫出forward/return path並檢查longest prefix。",
            "單張全互通表最簡單但blast radius最大；錯誤default route或非對稱return path可能繞過stateful firewall。",
        ),
        S(
            "appliance mode",
            "在inspection VPC attachment上維持同一flow的AZ親和與對稱路徑，使stateful virtual appliance能看到往返封包。",
            "透過TGW把東西向或南北向流量送進跨AZ firewall/IDS appliance fleet時。",
            "只在appliance VPC attachment啟用appliance mode，配合各AZ endpoint/subnet與TGW routes；用雙向flow及故障切換驗證對稱性。",
            "在spoke隨意啟用不能修正錯誤route；缺少對稱路徑時stateful appliance會把回程當成未知connection丟棄。",
        ),
        S(
            "ECMP",
            "Equal-Cost Multi-Path讓TGW在多條等成本VPN/Connect路徑間以flow hash分散流量，提高aggregate throughput與冗餘。",
            "單一VPN tunnel吞吐不足，且on-prem routers能以BGP廣告相同prefix與相同路徑成本時。",
            "在TGW開啟VPN ECMP，建立多條動態路由連線並廣告相同prefix；監控每條tunnel、BGP與aggregate throughput。",
            "ECMP是per-flow而非把單一flow切開；static VPN或不相等BGP path通常無法得到預期分流。",
        ),
        S(
            "multicast",
            "讓一個source把封包送到multicast group，由TGW複製給已註冊receivers，支援少數需要一對多IP傳送的workload。",
            "市場資料、媒體或legacy discovery確實依賴multicast，且unicast fan-out成本／相容性不合適時。",
            "建立multicast domain、關聯subnets並註冊sources/members；確認instance、OS與security rules支援，再量測receiver loss。",
            "Multicast不會自動跨所有attachments或Internet；大多數cloud application用SNS/Kinesis等application-level fan-out更容易治理。",
        ),
    ),
    "Amazon CloudFront": (
        S(
            "origins",
            "Origin是cache miss時CloudFront真正取資料的後端，例如S3 REST endpoint、ALB、API Gateway或自訂HTTP server。",
            "要把全球edge delivery與實際儲存／應用後端分離時。",
            "設定DomainName、OriginPath、origin protocol與custom headers；S3 private origin搭配OAC，自訂origin要限制只接受CloudFront流量。",
            "把S3 website endpoint當成可用OAC的S3 REST origin，或讓origin仍公開可繞過WAF/cache，會破壞安全邊界。",
        ),
        S(
            "cache policy",
            "決定哪些headers、cookies、query strings進入cache key，以及minimum/default/maximum TTL。Cache key不同就會形成不同cache object。",
            "同一路徑會因語言、裝置、授權狀態或query參數產生不同內容時。",
            "優先選AWS managed policy；自訂時只把真正改變response的值放入cache key，並設定TTL與Gzip/Brotli。將policy附到cache behavior。",
            "把所有headers/cookies/query strings都放進cache key會造成大量碎片與低hit ratio；漏掉會改變response的值則可能回錯內容。",
        ),
        S(
            "origin request policy",
            "決定額外轉送哪些headers、cookies與query strings到origin，但不把它們加入cache key。",
            "Origin需要request context做logging、authorization或business logic，但該值不應切碎cache時。",
            "將origin需要、但不改變可快取response的欄位列入allow list；它必須與cache policy一起附到同一cache behavior。",
            "以origin request policy轉送會改變response的欄位、卻不加入cache key，可能讓不同使用者共用錯誤cached response。",
        ),
        S(
            "cache behaviors",
            "依path pattern選擇origin、allowed methods、viewer protocol、cache policy、origin request policy與edge function。",
            "同一distribution同時服務static assets、dynamic API與下載路徑，且各自需要不同cache/security設定時。",
            "建立default behavior，再以更具體path patterns建立額外behaviors；檢查pattern precedence與每條路徑的methods、policies及origin。",
            "只修改default behavior卻忘記更具體pattern會先匹配，可能讓API被意外cache或讓敏感路徑繞過預期policy。",
        ),
        S(
            "OAC",
            "Origin Access Control讓CloudFront以SigV4代表distribution向private S3 REST origin送出已簽章request。",
            "S3 objects要公開給網站使用者，但禁止使用者直接以S3 URL讀取時。",
            "建立AWS::CloudFront::OriginAccessControl並設SigningBehavior=always、SigningProtocol=sigv4；distribution origin引用它，bucket policy只允許cloudfront.amazonaws.com且限制SourceArn。",
            "OAC不支援S3 website endpoint；只建立OAC卻沒有更新bucket policy，CloudFront會得到403。",
        ),
        S(
            "TTL",
            "Time to live決定edge中的object多久視為fresh。到期後CloudFront才回origin重新驗證或取得內容。",
            "在內容新鮮度、origin負載、延遲與cache hit ratio之間做取捨時。",
            "以cache policy設定MinimumTTL、DefaultTTL、MaximumTTL，並理解origin的Cache-Control/Expires如何參與。三者皆為0會停用cache。",
            "Minimum TTL大於0時，即使origin回no-cache/no-store/private，CloudFront仍至少cache該時間；敏感dynamic response不可盲目套高TTL。",
        ),
        S(
            "WAF",
            "Web ACL在edge檢查HTTP request，可依IP、URI、header、body、rate與managed signatures做allow/block/count。",
            "要在流量回到origin前阻擋bot、SQL injection、XSS、惡意IP或HTTP flood時。",
            "建立global-scope Web ACL、先以Count觀察managed rules，再關聯distribution並開啟logging與rate-based rules。",
            "WAF不是IAM，也不保證origin私有；沒有OAC/origin restriction時，攻擊者仍可能直接打後端繞過WAF。",
        ),
        S(
            "geo restriction",
            "依viewer國家位置allow或deny整個distribution內容，是粗粒度的地理存取控制。",
            "授權、法規或商業合約要求阻擋少數國家，且不需依path/user做複雜判斷時。",
            "在distribution設定whitelist或blacklist country codes；需要更細規則、例外或logging時改用WAF geo match。",
            "Geo restriction不是強身份驗證，VPN/proxy可能改變來源位置；敏感資料仍需application authorization與signed URL/cookie。",
        ),
    ),
    "AWS Global Accelerator": (
        S(
            "listeners",
            "Listener定義Global Accelerator接受的TCP或UDP port ranges；client連到兩個static anycast IP後，流量才依此入口進入accelerator。",
            "需要固定全球IP、非HTTP protocol，或不可快取的TCP/UDP application經AWS全球骨幹加速時。",
            "建立TCP/UDP listener與最小port ranges，設定client affinity需求；確認regional endpoints及security rules接受相同目的ports。",
            "Listener不是TLS certificate終止點；若後端要TLS，通常仍由NLB/ALB/application處理。Port設太寬也會擴大暴露面。",
        ),
        S(
            "endpoint groups",
            "每個endpoint group對應一個AWS Region，保存該Region的endpoints、health port/protocol與整體traffic dial。",
            "同一accelerator要在多Region間依健康與比例分配流量，或執行regional evacuation時。",
            "為每個Region建立group，加入ALB、NLB、EC2或EIP endpoints，設定health check與traffic dial；從多地client驗證實際Region。",
            "建立第二group不等於application已多Region就緒；資料、identity、quota與failover dependencies仍要同步設計。",
        ),
        S(
            "traffic dial",
            "以0–100百分比調整某個endpoint group可接收的整體流量比例，常用於Region排空、canary或逐步恢復。",
            "跨Regionmigration、事件期間降低特定Region流量，或先用少量production traffic驗證新Region時。",
            "先確認另一Region有足夠capacity與資料，再逐步調整dial並監控business SLO；預先定義回調與rollback門檻。",
            "Traffic dial不是精準逐request比例，也不修正stateful session與資料一致性；瞬間設為0仍需考慮既有connections。",
        ),
        S(
            "endpoint weight",
            "在同一regional endpoint group內設定各endpoint的相對權重，控制新flows如何分配到多個ALB、NLB、EC2或EIP。",
            "同Region內做blue/green、capacity比例分配，或逐步引入新endpoint時。",
            "為healthy endpoints設定0–255相對weight，以小比例開始並觀察error、latency與capacity；確認health check能正確摘除故障端點。",
            "Weight不是保證百分比，少量flows會有偏差；把不健康endpoint權重設高也不會讓它恢復。",
        ),
        S(
            "health checks",
            "Global Accelerator檢查regional endpoints能否服務，並把新flows導向健康端點；對ALB/NLB可沿用其健康狀態。",
            "要求endpoint或整個Region故障時自動停止接收新連線時。",
            "設定代表真實服務的protocol、port、path、interval與threshold，並以故障注入量測偵測及重新導流時間。",
            "只檢查TCP port可能產生假健康；切走新flows也不會自動終止或遷移已建立的長連線。",
        ),
        S(
            "client affinity",
            "選擇NONE或SOURCE_IP，決定同一來源IP建立的新connections是否傾向被導到同一endpoint。",
            "Application仍依賴endpoint-local session，且來源IP能合理代表client時，才作為相容性措施。",
            "在listener設定ClientAffinity；用多client/NAT情境驗證分布，並讓session逐步外部化到shared store。",
            "大量使用者經同一NAT會被誤認為單一client並造成熱點；affinity也不能在endpoint故障時保存local session。",
        ),
    ),
    "Lambda@Edge": (
        S(
            "event trigger",
            "決定函式在viewer request、origin request、origin response或viewer response哪個CloudFront階段執行；不同階段的cache關係、可見欄位與限制不同。",
            "需要在進cache前改URI／認證、只在回源時選origin，或在response送給viewer前補header時。",
            "先畫出viewer→cache→origin flow，再把function association綁到正確cache behavior與event type；分別測cache hit與miss。",
            "綁錯階段可能讓函式每次request都執行、破壞cache key，或以為能修改該階段不可變更的header/status。",
        ),
        S(
            "us-east-1 function version",
            "Lambda@Edge函式必須建立在us-east-1並使用已發布的numbered version；CloudFront把該immutable版本複寫到edge locations。",
            "任何Lambda@Edge deployment、更新或rollback都需要明確版本，而不能直接關聯$LATEST或alias。",
            "在us-east-1建立函式、publish version，再把version ARN關聯到distribution behavior；更新時發布新版本並等待distribution部署完成。",
            "修改$LATEST不會改變已部署edge程式；過早刪除仍被複寫使用的version會失敗，更新也不是立即全球生效。",
        ),
        S(
            "IAM execution role",
            "允許Lambda與edgelambda service principals assume role，並授予函式寫logs或呼叫其他AWS APIs所需的最小權限。",
            "函式需要記錄執行結果、讀取外部設定或存取AWS資源，且必須保留可稽核的最小權限邊界時。",
            "Trust policy同時允許lambda.amazonaws.com與edgelambda.amazonaws.com；permissions只加入必要actions/resources，並檢查跨Region資源行為。",
            "只加入一般Lambda trust會讓edge replication/執行失敗；給AdministratorAccess會把全球edge code的blast radius放大。",
        ),
        S(
            "memory／timeout",
            "Memory同時影響可用CPU，timeout限制每次edge事件可執行時間；不同event type可用上限並不相同。",
            "程式包含JWT驗證、rewrite或network call，需要在viewer latency與運算需求間取捨時。",
            "依該event type的官方quota設定最小足夠memory/timeout，用真實payload量測p95/p99，避免在edge做慢或不可預測的遠端依賴。",
            "把timeout調大不會讓viewer願意久等；遠端API、冷啟動與大dependency會直接增加每個request延遲與費用。",
        ),
        S(
            "include body",
            "讓request trigger取得經Base64編碼且受大小限制的request body，以便檢查或修改POST/PUT內容。",
            "只有edge邏輯確實需要讀取小型body，例如特定表單驗證或routing訊號時才開啟。",
            "在function association啟用IncludeBody，處理encoding、truncation與content type，並以接近大小上限的request測試。",
            "Body可能被截斷，敏感內容也可能進入logs；大型upload與完整API validation不適合放在Lambda@Edge。",
        ),
        S(
            "logs",
            "函式在最接近執行edge location的AWS Region寫入CloudWatch Logs，而不是只集中在us-east-1。",
            "需要除錯regional使用者錯誤、追蹤deployment版本或建立edge執行證據時。",
            "在可能執行的Regions建立log查詢／centralization策略，輸出request ID與版本但遮罩token、cookie及PII，設定retention。",
            "只查us-east-1會誤以為沒有執行；把完整headers/body寫log會造成跨Region敏感資料與成本問題。",
        ),
        S(
            "deployment restrictions",
            "描述Lambda@Edge與一般regional Lambda不同的功能邊界，例如版本、Region、runtime、environment、VPC與deployment lifecycle限制。",
            "把既有Lambda搬到edge，或選擇Lambda@Edge、CloudFront Functions與regional service之間的執行位置時。",
            "在設計前核對目前官方限制與quota；將configuration打包進版本或安全外部來源，建立staged distribution與可回復舊版本。",
            "假設一般Lambda所有features都可用會在部署時失敗；edge code也不適合承擔database transaction或長時間business workflow。",
        ),
    ),
    "Application Load Balancer": (
        S(
            "listeners／certificates",
            "Listener在指定port/protocol接收client connection；HTTPS listener使用certificate終止TLS，再把HTTP/HTTPS送往target group。",
            "網站要在443提供TLS、將80 redirect到443，或同一ALB承接不同入口時。",
            "建立listener的Protocol/Port與DefaultActions；HTTPS指定ACM CertificateArn與security policy，可加入多張SNI certificates。",
            "只有ALB listener開443但security group未開，或certificate位於錯誤Region／網域不匹配，client仍無法完成TLS。",
        ),
        S(
            "rules priority",
            "Listener rules依數字由小到大評估conditions；第一個匹配的forward、redirect、fixed-response或authentication action生效，default rule最後執行。",
            "依host、path、header、method、query或source IP把microservices導向不同target groups時。",
            "為每條非default rule指定唯一Priority與Conditions，最具體規則放在適當順序；部署前測試重疊patterns。",
            "較寬的/*規則優先匹配會吃掉後面的/admin/*；priority不是權重，也不代表流量百分比。",
        ),
        S(
            "target type",
            "決定target group註冊的是EC2 instance ID、IP address或Lambda。它影響封包目的、port、VPC限制與container整合。",
            "ECS awsvpc tasks通常用ip；傳統EC2可用instance；ALB直接觸發函式才用lambda。",
            "建立target group時設定TargetType，並註冊相同類型targets；此選擇建立後不能任意改成另一類型，通常需新target group。",
            "Fargate沒有可註冊的host instance port卻選instance target，或跨VPC IP不符合允許範圍，會讓targets無法healthy。",
        ),
        S(
            "health path",
            "ALB週期性呼叫target的health-check path；只有達到healthy threshold的targets才接收正常流量。",
            "應用需要排除未啟動、依賴失敗或正在drain的instances/tasks時。",
            "在target group設定HealthCheckPath、port/protocol、interval、timeout、healthy/unhealthy thresholds與Matcher success codes。",
            "Health path執行昂貴database query會放大故障；只回固定200又可能讓已無法服務的target被判定healthy。",
        ),
        S(
            "stickiness",
            "Stickiness又稱session affinity，透過cookie讓同一client在一段時間內持續被導向同一target，而不是每個request重新分配。",
            "Legacy application把session只放在單台server記憶體，短期無法搬到shared session store時。",
            "在target group開啟stickiness.enabled，選lb_cookie或app_cookie並設定duration/name；CloudFormation使用TargetGroupAttributes。",
            "它會造成負載不均、target replacement時session仍可能遺失，也不能取代共享session store；新系統優先保持stateless。",
        ),
        S(
            "idle timeout",
            "前端或後端connection在沒有傳輸資料多久後由ALB關閉，避免閒置connection永久占用資源。",
            "長輪詢、WebSocket、慢request或upload時間超過預設值，需要與application/client timeout協調時。",
            "在ALB attribute設定idle_timeout.timeout_seconds；讓client/application timeout略有明確層次，並測試中途無資料的connection。",
            "只把值調得很大會保留大量dead connections；ALB timeout短於application工作時間常表現為client端502/504或重試。",
        ),
        S(
            "access logs",
            "記錄每個經ALB處理的request，包括client、target、latency、status、chosen rule與TLS資訊，輸出到S3。",
            "分析5xx、target latency、routing規則、security事件與稽核時。",
            "在load balancer attributes啟用access_logs.s3.enabled，指定bucket與prefix，並設定允許log delivery的bucket policy與retention。",
            "Access logs是延遲交付的request紀錄，不是即時metric；未設定資料保留、查詢partition與敏感欄位治理會造成成本與隱私問題。",
        ),
    ),
    "Amazon OpenSearch Service": (
        S(
            "domain／serverless collection",
            "Domain是provisioned OpenSearch cluster；serverless collection由AWS管理底層capacity，依search、time-series或vector workload提供不同抽象。",
            "需要全文搜尋、log analytics或vector index，並在控制cluster拓樸與降低營運負擔之間選擇時。",
            "先定義資料量、ingestion、query latency與相容plugin需求；provisioned設定engine/nodes/shards，Serverless建立collection、encryption、network與data access policies。",
            "這裡的domain不是DNS名稱。Serverless也不是無上限或零設定；network policy與data access policy缺一仍會拒絕請求。",
        ),
        S(
            "instances／shards／replicas",
            "Instance提供CPU、memory與storage；primary shard切分index資料；replica shard增加read capacity並在節點故障時提供副本。",
            "資料量、ingestion或查詢增加，或production搜尋服務需要跨AZ容錯與可預測恢復時間時。",
            "依單一shard大小、heap、query concurrency與AZ規劃node count、primary shards與replicas；用代表性資料量壓測並監控JVM pressure、CPU、storage與shard skew。",
            "過多小shards浪費heap，過大shard拖慢recovery；replica提高可用性與讀取量，但也增加儲存與寫入成本。",
        ),
        S(
            "EBS",
            "為provisioned data nodes提供持久block storage；volume type、size與IOPS／throughput會限制index與merge效能。",
            "使用provisioned domain且資料量超出instance local storage，或需要可調整的持久容量時。",
            "選擇支援的gp3/io類型與容量，保留watermark headroom；監控FreeStorageSpace、IOPS與throughput，擴容前估算rebalance時間。",
            "磁碟變大不會修正hot shard或JVM瓶頸；等到空間接近零才擴容可能已觸發read-only block。",
        ),
        S(
            "VPC access",
            "把OpenSearch endpoint放入指定VPC subnets並建立ENIs，使data plane只由具備network path的clients存取。",
            "搜尋資料或logs不應暴露於Internet，且clients位於VPC、peered/TGW network或hybrid環境時。",
            "選擇跨AZ subnets與security groups，建立DNS、route與return path；再搭配fine-grained access或IAM簽章驗證application身份。",
            "VPC access只限制網路可達性，不等於application authorization；建立後切換public/VPC access通常需要replacement或遷移規劃。",
        ),
        S(
            "fine-grained access",
            "在cluster內以users、backend roles、index、document與field permissions控制誰能搜尋或修改哪些資料。",
            "多租戶、security analytics或不同團隊共用cluster，但不能互讀index時。",
            "啟用fine-grained access，將IAM role／IdP group映射到最小OpenSearch roles；分別測試cluster、index與Dashboards權限。",
            "只靠domain access policy通常粒度太粗；同時混用IAM、basic auth與role mapping若沒有明確模型，容易出現403或過度授權。",
        ),
        S(
            "snapshots",
            "保存index與cluster metadata的可恢復副本；自動snapshot與手動snapshot有不同保留與repository責任。",
            "誤刪index、資料毀損、重大升級或跨domain migration需要恢復點時。",
            "確認自動snapshot時段與保留；長期／遷移需求建立S3 snapshot repository、IAM role與bucket/KMS policy，並定期演練restore到隔離domain。",
            "Replica不是snapshot；snapshot成功也不代表能在目標版本、Region與KMS權限下恢復。",
        ),
        S(
            "index lifecycle",
            "以hot/warm/cold/delete階段管理index rollover、遷移與刪除，讓資料保留和查詢效能對應成本。",
            "Logs或time-series資料持續成長，但新資料查詢頻繁、舊資料只偶爾查詢且有明確retention時。",
            "依時間／size設定rollover與ISM policy，定義各階段、minimum age、snapshot及delete；以alias寫入並監控policy execution。",
            "直接按日期大量建立極小index會產生shard爆炸；delete policy若無legal retention與snapshot檢查，可能永久刪除稽核資料。",
        ),
    ),
    "Network Load Balancer": (
        S(
            "TCP／UDP／TLS listeners",
            "Listener在指定port接受Layer 4 TCP、UDP、TCP_UDP或TLS connections；TLS listener可在NLB終止TLS後轉送到target group。",
            "需要高吞吐、低延遲、非HTTP protocol、static IP或保留來源IP的regional入口時。",
            "建立protocol/port與default target group；TLS listener附ACM certificate及security policy，並讓target protocol符合end-to-end encryption需求。",
            "NLB不提供ALB的path/host routing與WAF；把TLS終止位置搞錯會造成double TLS、明文hop或certificate不匹配。",
        ),
        S(
            "IP／instance／ALB target",
            "Target type決定NLB把flow送到EC2 instance、具體IP或另一個ALB；它影響port、來源IP、跨VPC與container整合方式。",
            "傳統EC2可選instance，awsvpc/Fargate常選ip；需要NLB static IP加ALB Layer 7能力時可選ALB target。",
            "建立target group時選定TargetType並註冊符合範圍的targets；建立後若要換type，通常建立新target group再切listener。",
            "把Fargate當instance target、註冊不支援的public IP，或忽略ALB target的port/health限制，會讓targets無法接流量。",
        ),
        S(
            "cross-zone",
            "決定每個NLB node只把流量送到同AZ targets，或也跨AZ分配到所有enabled-zone healthy targets。",
            "各AZ target容量不均、流量偏斜，且願意接受可能的跨AZdata processing cost時。",
            "在load balancer attribute設定load_balancing.cross_zone.enabled；比較各AZtarget數、flow分布、latency與cross-AZ bytes。",
            "開啟可改善不均但不會增加總capacity；關閉時若某AZtarget不足，使用者可能在其他AZ仍健康時遇到壓力。",
        ),
        S(
            "Proxy Protocol v2",
            "在backend connection前附加二進位header，傳遞原始source/destination、port及PrivateLink endpoint等connection metadata。",
            "Target無法直接看到原始client IP，或應用／proxy需要額外Layer 4來源資訊時。",
            "在target group開啟proxy_protocol_v2.enabled，並先確認backend server能解析PPv2 header；以packet/backend log驗證。",
            "Backend未支援卻開啟PPv2，會把header當application bytes並直接破壞protocol；HTTP X-Forwarded-For不是同一機制。",
        ),
        S(
            "preserve client IP",
            "控制target看到的是原始client source IP還是load balancer私有位址；可用性依target type與protocol而不同。",
            "Firewall、rate limit、audit或application authorization確實需要真實來源IP時。",
            "依target group類型設定preserve_client_ip.enabled，確認return path、security rules與client IP preservation限制，從backend log驗證。",
            "保留來源IP可能改變routing/hairpin行為；以client IP做唯一身份也會被NAT、proxy或共享出口誤導。",
        ),
        S(
            "health check",
            "NLB主動探測target的TCP、HTTP或HTTPS狀態，只把新flows送到通過threshold的targets。",
            "需要排除process停止、port不通或application endpoint失敗的instances、IPs或ALB targets時。",
            "設定protocol、port、path、success codes、interval與threshold；health endpoint應快速、能代表服務能力且不造成下游放大。",
            "TCP成功只證明port接受連線；health check太深可能因單一dependency故障把所有targets一起摘除。",
        ),
    ),
    "Gateway Load Balancer": (
        S(
            "GENEVE 6081",
            "GWLB以UDP 6081上的GENEVE封裝原始IP flow與metadata，透明送到支援GENEVE的firewall、IDS/IPS或其他virtual appliance。",
            "需要在不改變application endpoint的情況下，水平擴展第三方network appliance並保留雙向flow context時。",
            "Appliance必須在UDP 6081監聽並正確decapsulate/recapsulate；SG/NACL允許health與GENEVE traffic，再用packet capture驗證。",
            "GENEVE不是一般application listener；appliance只接受普通Ethernet/IP或錯誤MTU時，會丟包或產生難查的fragmentation。",
        ),
        S(
            "GWLB endpoints",
            "GWLBe是consumer VPC中的PrivateLink gateway endpoint，route table可把要檢查的流量導入provider端GWLB appliance service。",
            "多個spoke VPC要共用中央inspection fleet，又不想把所有網路完整route到provider VPC時。",
            "每個需要的AZ建立GWLBe並接受service；在ingress、subnet或TGW路徑加入指向vpce-*的routes，逐方向驗證。",
            "單AZ endpoint會形成跨AZ或故障問題；endpoint存在但route未指向它時，流量完全不會經過inspection。",
        ),
        S(
            "route tables",
            "決定哪些來源／目的flows被送到GWLBe，以及appliance處理後如何回到原路徑，是service insertion的核心。",
            "Internet ingress/egress、east-west或TGW centralized inspection需要強制經過appliance時。",
            "分別畫出forward與return route，對public subnet、application subnet、endpoint subnet與TGW tables設定精確next hop並測試對稱性。",
            "只改去程不改回程會繞過stateful appliance或造成timeout；過寬default route也可能把管理流量送進錯誤inspection path。",
        ),
        S(
            "target health",
            "GWLB以health check判斷appliance能否處理flow；不健康target停止接收新flows，healthy fleet共同分擔流量。",
            "Appliance可能process crash、license失效、CPU飽和或無法轉送封包，需要自動隔離時。",
            "設定能代表data-plane readiness的health protocol/port與threshold，搭配ASG capacity及appliance metrics測試replacement。",
            "管理介面回200不代表轉送面正常；health check過於表面會留下black hole，過深則可能同時摘除整個fleet。",
        ),
        S(
            "appliance flow stickiness",
            "以flow的5-tuple或3-tuple維持同一connection方向持續送往同一appliance，讓stateful inspection保留session狀態。",
            "Appliance需要看到完整connection並保存NAT、TLS或firewall session state時。",
            "依traffic特性選擇flow stickiness屬性，確保forward/return path對稱；用長連線、fragment與failover案例驗證。",
            "Stickiness不能在appliance故障時遷移其memory state；不適合的tuple選擇也可能讓大量flows集中到少數targets。",
        ),
        S(
            "cross-zone",
            "決定GWLB node是否可把flow送到其他AZ的healthy appliances，在容量均衡、故障隔離與跨AZ成本之間取捨。",
            "各AZ appliance capacity不均或需要在單AZtarget不足時使用其他AZ容量時。",
            "設定cross-zone attribute，確保所有AZ都有對稱route與足夠MTU；監控每AZflows、appliance utilization及cross-AZ bytes。",
            "開啟不能修正單一appliance bottleneck，且跨AZpath若未對稱會讓stateful inspection失效並增加data transfer費。",
        ),
    ),
    "Amazon Route 53": (
        S(
            "public／private hosted zone",
            "Hosted zone保存某個DNS namespace的records。Public zone由Internet resolver查詢；private zone只對關聯VPC及適當hybrid resolver path可見。",
            "公開網站使用public zone；內部service name、split-horizon DNS或VPC私有服務使用private zone。",
            "建立zone後加入A/AAAA/CNAME/Alias等records；private zone要關聯每個需要解析的VPC，跨帳號需authorization或RAM/Profiles設計。",
            "建立private zone不會自動關聯所有VPC；同名public/private records可能因查詢來源不同得到不同答案。",
        ),
        S(
            "Alias record",
            "Route 53專用record，可把zone apex或一般名稱指向ALB、CloudFront、API Gateway、S3 website等AWS資源，且可評估target health。",
            "不能使用CNAME的root domain，或AWS target沒有固定IP時。",
            "建立A/AAAA Alias並填AliasTarget DNSName/HostedZoneId；不要手抄短暫IP，CloudFormation可引用資源屬性。",
            "Alias不是routing policy；是否weighted/failover/latency仍需另外設定，且不是所有AWS endpoint都支援Alias。",
        ),
        S(
            "TTL",
            "DNS resolver可以快取record answer的秒數。TTL越低，變更較快被看見，但權威DNS查詢量增加；既有connection不會因此被中斷。",
            "計畫切換、failover或頻繁變更endpoint時降低；穩定records可提高。",
            "在普通record設定TTL；Alias到AWS資源的TTL由target行為決定。重大cutover要提前至少一個舊TTL降低，不能切換當下才改。",
            "TTL不是健康檢查週期，也不保證所有client準時丟棄cache；把DNS當request-level load balancer會產生不精確分流。",
        ),
        S(
            "routing policies",
            "決定同名records如何回答：simple、weighted、latency、failover、geolocation、geoproximity或multivalue各自解決不同決策。",
            "需要DNS層canary、主備切換、全球低延遲或地理規則時。",
            "先選policy，再為records設定identifier、weight/region/primary-secondary/geography與health checks；用dig從不同來源驗證。",
            "Weighted不是精準百分比；latency不是距離；geolocation沒有default record可能讓未知位置得到no answer。",
        ),
        S(
            "health checks",
            "由Route 53 health checkers探測public endpoint、監看CloudWatch alarm或計算其他checks，並把不健康record從符合條件的DNS回答中移除。",
            "DNS failover或multivalue只想回傳可服務endpoint時。",
            "設定protocol/port/path、interval、failure threshold與regions，或將Alias的EvaluateTargetHealth指向支援的AWS資源。",
            "Private IP不能直接被Internet health checker探測，且移除DNS answer不會中止已建立connection；仍需應用層重試與fencing。",
        ),
    ),
}


def _split_settings(config: str) -> tuple[str, ...]:
    cleaned = config.strip().rstrip("。")
    rows = [part.strip() for part in re.split(r"[、，,；;]|與", cleaned) if part.strip()]
    return tuple(dict.fromkeys(rows))


COMPONENT_SETTING_OVERRIDES: dict[
    tuple[str, str], tuple[str, str, str, str]
] = {
    ("AWS Elemental MediaConvert", "job/template"): (
        "Job是一次實際轉碼請求；job template則保存可重用的output groups、video/audio處理與編碼設定。輸入、輸出位置等每支影片不同的值仍可在送出job時覆寫。",
        "同一平台反覆產生HLS、DASH或檔案輸出，希望把經測試的轉碼規格版本化，同時讓每支影片指定自己的S3來源與目的地時。",
        "先在隔離queue用代表性素材建立並驗證job settings，再保存具版本名稱的job template；提交job時指定template、input、destination、IAM role與metadata，並以EventBridge追蹤COMPLETE或ERROR。",
        "直接修改共用template可能讓重跑的影片產生不同輸出；template也不會自動提供job idempotency，producer仍須以asset/version保存job ID並避免重複計費。",
    ),
    ("AWS Elemental MediaConvert", "codec"): (
        "Codec決定影像或音訊如何壓縮，例如H.264、H.265/HEVC或AV1；它影響裝置相容性、畫質、位元率、轉碼時間與播放端計算成本。",
        "需要在廣泛裝置相容、較低傳輸成本、較高畫質或特定播放器能力間取捨，並為adaptive-bitrate ladder產生多個renditions時。",
        "先列出目標裝置與container/streaming format支援，再為每個output設定codec、rate-control mode、bitrate/quality、resolution、frame rate與GOP；用真實播放器及VMAF等品質指標驗證。",
        "只追求最高壓縮率可能讓舊裝置無法播放或增加編碼成本；把codec、container與manifest混為一談，也會產生檔案成功但播放器不相容的結果。",
    ),
    ("Health checks", "IP/domain"): (
        "指定Route 53健康檢查實際探測的公開IPv4／IPv6位址或完整網域名稱，決定探測封包最後送到哪個endpoint。",
        "Endpoint可由Internet上的Route 53 health checkers直接到達，且DNS failover必須根據這個endpoint的真實狀態做決策時。",
        "優先使用穩定FQDN並確認解析結果；若填domain，也要設定正確protocol、port與Host header，從多個health-check regions驗證。",
        "把private IP填入Internet health check不會成功；domain解析到多個位址或切換DNS時，也可能讓探測目標與你以為的不同。",
    ),
    ("Health checks", "request path"): (
        "指定HTTP／HTTPS探測會請求的URI，例如`/healthz`，讓健康狀態代表某個明確application capability，而不只是TCP port有開。",
        "DNS切換需要確認web application真的可回應，而單純建立TCP connection不足以代表使用者交易可以成功時。",
        "建立便宜、快速且有明確狀態碼的health endpoint；設定path、Host header與可接受回應，並從外部實際重播同一request。",
        "Health endpoint若同步檢查所有下游，單一非必要dependency就可能觸發全站failover；只回固定200又可能掩蓋真正故障。",
    ),
    ("Health checks", "inverted"): (
        "把子health check或CloudWatch alarm的健康結果反轉，使原本的healthy被視為unhealthy，反之亦然。",
        "監控訊號本身表示失敗條件，例如alarm為OK代表不應供應流量，且無法在來源端改寫訊號語意時才考慮。",
        "先寫出原始訊號與期望DNS行為的truth table，再啟用inverted並故意觸發兩種狀態，確認沒有二次反轉。",
        "Inverted很容易造成雙重否定；若alarm、calculated check與routing policy各自反轉一次，事故時可能保留壞endpoint並移除好endpoint。",
    ),
    ("Health checks", "calculated children"): (
        "以多個child health checks與健康門檻計算一個父狀態，用來表達N-of-M、AND或OR式的組合健康條件。",
        "單一服務的健康需要整合多個獨立訊號，或希望少數探測器異常時不立即觸發DNS failover時。",
        "列出child checks、可接受失敗數與相依性，設定父check門檻後逐一模擬child失敗，驗證每種組合的最終狀態。",
        "多個children若都依賴同一DNS、network path或alarm，就不是獨立證據；複雜組合也可能讓真正故障被門檻掩蓋。",
    ),
    ("Direct Connect Gateway", "allowed prefixes"): (
        "限制Direct Connect gateway association可向Transit Gateway或Virtual Private Gateway宣告及接收的CIDR範圍，形成路由傳播邊界。",
        "一條Direct Connect要服務多個VPC／Region，但on-premises只應看見核准網段，或必須避免過度宣告造成路由外洩時。",
        "先建立不重疊的prefix清單，再在association或proposal設定allowed prefixes；同時核對BGP advertisements與兩側return routes。",
        "Allowed prefixes不是security group或packet firewall；前綴過寬會擴大可達範圍，過窄則會讓BGP session正常但application流量黑洞。",
    ),
    ("Envelope encryption", "ciphertext metadata"): (
        "保存解密所需但不必保密的資訊，包括加密後data key、演算法版本、IV／nonce、authentication tag與必要的encryption-context識別。",
        "應用自行做client-side或field-level envelope encryption，未來需要key rotation、格式升級與跨版本解密時。",
        "定義版本化envelope格式，把encrypted data key與ciphertext一起原子保存；解密時重建完全相同的encryption context並驗證authentication tag。",
        "遺失metadata會讓仍有KMS權限的資料也無法解密；重用nonce、未驗tag或把plaintext data key寫入metadata都會破壞安全性。",
    ),
    ("Amazon Machine Images", "architecture"): (
        "指定AMI可啟動的CPU instruction architecture，例如x86_64或arm64，必須與EC2 instance type及所有native binaries相容。",
        "選擇Graviton或x86 instance family、跨architecture搬移workload，或建立同一應用的多架構golden images時。",
        "在Image Builder／Packer pipeline分別建置並測試每種architecture，標記AMI，讓launch template引用相符的instance family與image ID。",
        "x86 AMI不能直接啟動在arm64 instance；即使應用語言可攜，OS package、agent與native library仍可能不相容。",
    ),
    ("Amazon Machine Images", "root device"): (
        "定義EC2開機使用的root volume類型、device mapping、snapshot、容量與DeleteOnTermination等生命週期行為。",
        "需要immutable baseline、調整root磁碟容量／型別，或必須決定instance終止後root資料是否保留時。",
        "檢查AMI的root device與block mappings，在launch template覆寫容量、volume type、encryption及DeleteOnTermination，並實測replace／terminate。",
        "把root volume設為保留會留下成本與敏感資料；設為刪除又不能把尚未外部化的application state當成可恢復資料。",
    ),
    ("Amazon Machine Images", "deprecation"): (
        "為AMI設定棄用時間，使一般DescribeImages結果與新部署不再優先使用它，但不會刪除AMI或停止既有instances。",
        "golden image已有安全更新或替代版本，需要阻止新的launch繼續採用舊映像，同時保留受控回滾窗口時。",
        "在新AMI通過測試後更新launch templates，設定舊AMI deprecation time，監控仍引用舊ID的stacks，再依retention政策deregister。",
        "Deprecation不是立即撤銷launch permission，也不會patch已執行instance；太早deregister及刪除snapshots可能讓rollback失去可啟動映像。",
    ),
    ("Placement groups", "strategy"): (
        "選擇cluster、spread或partition，決定EC2 instances在底層硬體上的鄰近性、硬體隔離程度與可見failure-domain拓撲。",
        "HPC需要低網路延遲、少量關鍵nodes要分散硬體，或Kafka／HDFS fleet需要依partition容忍rack級故障時。",
        "依workload選單一strategy並驗證instance type、AZ、tenancy與capacity限制；partition-aware軟體還要把partition資訊映射到replicas。",
        "Cluster提高效能但集中硬體風險；spread有instance數量限制；placement group本身不提供跨AZ資料複寫或application failover。",
    ),
    ("EBS snapshots", "Recycle Bin"): (
        "以retention rule暫存被刪除的EBS snapshots或AMIs，讓誤刪資源在保留期間內可以還原，而不是立即永久消失。",
        "管理員或automation可能誤刪snapshot／AMI，且合規要求提供一段可復原窗口時。",
        "依resource type、tag與Region建立最小必要retention rule，測試刪除與restore權限，並把Recycle Bin事件接到稽核與告警流程。",
        "Recycle Bin不是backup排程，也不會自動跨帳號隔離；retention太短來不及發現事故，太長則增加成本與敏感資料保留時間。",
    ),
    ("Enhanced fan-out", "registered consumer"): (
        "在Kinesis Data Streams中建立具名稱與ARN的consumer資源，讓它取得每shard獨立的enhanced fan-out讀取通道。",
        "同一stream有多個低延遲consumer，傳統GetRecords shared throughput造成互相競爭或iterator age上升時。",
        "以RegisterStreamConsumer建立唯一consumer name，等待ACTIVE後讓client使用SubscribeToShard，並監控consumer與shard lag。",
        "註冊consumer不會增加shard寫入容量，也不能修復hot partition key；閒置registered consumers仍應清理並評估費用。",
    ),
    ("Enhanced fan-out", "consumer ARN"): (
        "唯一識別已註冊的enhanced fan-out consumer，SubscribeToShard與IAM resource scope會用它選定讀取身份。",
        "同一stream有多個獨立應用，需要明確授權、觀測並追蹤每個consumer的低延遲訂閱時。",
        "從DescribeStreamConsumer取得ACTIVE consumer ARN，將它交給SubscribeToShard並在IAM中只允許需要的stream與consumer資源。",
        "誤用stream ARN或舊consumer ARN會造成授權／訂閱失敗；重新註冊同名consumer後也不能假設ARN永遠不變。",
    ),
    ("AWS Distro for OpenTelemetry", "SDK auto/manual instrumentation"): (
        "決定由agent自動攔截常見framework與AWS SDK，或由程式碼手動建立span、metric與business attributes來補足語意。",
        "需要快速取得HTTP／database基礎traces，同時又要觀測checkout、tenant或job等框架無法自動理解的business operation時。",
        "先啟用支援的auto instrumentation並驗證context propagation，再只對關鍵business boundaries加入manual spans與低基數attributes。",
        "只靠auto instrumentation通常看不到business outcome；過度manual instrumentation或高基數attributes則會增加成本、噪音與敏感資料風險。",
    ),
    ("AWS CDK", "app/stacks"): (
        "CDK app是construct tree與合成入口；stack是會被合成為一份CloudFormation template並在特定environment部署的邊界。",
        "需要把大型基礎設施依ownership、deployment order、Region／account或blast radius切成可獨立變更單位時。",
        "在App中建立具明確env的Stacks，用cross-stack references或外部contract傳遞必要值，保持每個stack責任與rollback範圍清楚。",
        "把所有資源塞進單一stack會放大更新風險；過度cross-stack reference又會鎖死部署順序並使環境難以獨立演進。",
    ),
    ("AWS CDK", "constructs"): (
        "Construct是封裝一個或多個AWS resources、defaults與guardrails的可重用元件；L1／L2／L3代表不同抽象層級。",
        "多個團隊反覆建立相同network、service或security baseline，希望以程式介面重用並集中修正時。",
        "設計小而有清楚contract的construct props，暴露必要設定與escape hatch，加入synthesis assertions及integration deployment tests。",
        "把所有選項硬編碼成高階construct會限制合法use case；直接暴露每個底層property又失去抽象與安全預設的價值。",
    ),
    ("AWS CDK", "context"): (
        "提供synthesis階段的環境查詢結果或設定值，可能保存在cdk.context.json，影響之後產生的CloudFormation template。",
        "Construct需要查VPC、Availability Zones或其他environment facts，且團隊要讓同一revision能重現相同synth結果時。",
        "把必要context檔納入版本控制，變更前review diff；需要刷新lookup時明確清除指定key並在目標account／Region重新synth。",
        "把secret放入context會洩漏；未鎖定lookup結果可能讓相同程式碼在不同時間產生不同template，造成無預期替換。",
    ),
    ("AWS CDK", "assets"): (
        "表示部署需要的本地程式碼、container image或檔案；CDK會打包、雜湊並透過bootstrap資源上傳後供CloudFormation引用。",
        "Lambda code、ECS image或S3 deployment內容不是既有遠端artifact，需要隨IaC版本一起發佈時。",
        "先bootstrap目標environment，固定build input與exclude規則，讓CI執行asset build／publish並確認deployment role可讀取對應bucket或ECR。",
        "未固定dependency會讓相同source產生不同asset；把敏感檔案包入context或asset，以及跨帳號缺少bootstrap trust都會造成風險。",
    ),
    ("AWS CDK", "synth"): (
        "執行CDK程式並把construct tree轉成CloudFormation templates、asset manifests與metadata，是部署前可審查的輸出。",
        "任何CDK變更要進入CI、security scan、policy check或code review之前，都需要先產生確定的deployment artifact時。",
        "在固定runtime與dependencies下執行cdk synth，保存或檢查輸出，對generated template做lint、policy及snapshot assertions。",
        "Synth成功只代表可產生template，不代表service quota、runtime permissions或data-plane行為正確；context漂移也會改變輸出。",
    ),
    ("AWS CDK", "diff"): (
        "比較目前CDK合成結果與已部署stack，標示新增、修改、刪除與可能造成replacement的CloudFormation變更。",
        "production部署前需要人工或自動review blast radius，尤其涉及database、network、IAM與有狀態resource時。",
        "在與部署相同的context及credentials下執行cdk diff，將security-sensitive與replacement changes設為approval gate，再建立change set驗證。",
        "Diff不是完整runtime驗證，也可能受context或lookup權限影響；只看行數而不理解replacement／deletion語意仍可能造成資料遺失。",
    ),
    ("AWS Lambda aliases", "routing config"): (
        "讓alias把大部分invocations送到primary published version，並以單一additional-version weight進行Lambda層canary或linear切流。",
        "需要在不改invoke ARN的情況下逐步推出新Lambda version，並能依CloudWatch alarm快速回到舊版本時。",
        "發布immutable version，讓alias先指舊版，再設定additional version weight；搭配CodeDeploy deployment config、hooks與alarms逐步調整。",
        "權重是機率分配而非每小批request精準比例；alias切回不會回滾database schema、queue side effects或外部state。",
    ),
}


def _generic_guide(
    component: str, term: str, profile: ComponentProfile
) -> SettingGuide:
    override = COMPONENT_SETTING_OVERRIDES.get((component, term))
    if override is not None:
        return S(term, *override)

    lowered = term.lower()
    when = f"當需求符合「{profile.choose}」時，這個欄位是部署前review的一部分。"

    if re.search(r"parameters|outputs|dependson|capabilities|stack policy|deletionpolicy|updatereplacepolicy", lowered):
        return S(
            term,
            f"`{term}`是IaC template/stack的宣告或安全欄位，控制輸入、輸出、dependency、特殊權限或delete/update行為。",
            when,
            f"在{component} template中明確宣告型別、允許值、resource reference與保留策略；先產生change set並review replacement/delete。",
            "Parameter不是secret vault；Output也可能洩漏敏感值。錯誤DependsOn或DeletionPolicy會讓更新順序及資料保留與預期不同。",
        )
    if re.search(r"cache policy|origin request policy|\boac\b|geo restriction|behaviors", lowered):
        cloudfront = EXPLICIT_GUIDES["Amazon CloudFront"]
        for guide in cloudfront:
            if guide.name.lower() in lowered or lowered in guide.name.lower():
                return SettingGuide(term, guide.controls, guide.when, guide.configure, guide.pitfall)
    if re.search(r"callback token|callback heartbeat|execution name|workflow|idempotency", lowered):
        return S(
            term,
            f"`{term}`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。",
            when,
            f"{component}需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。",
            "保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。",
            "把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。",
        )
    if re.search(r"client affinity|cross-zone|preserve client ip|proxy protocol|geneve", lowered):
        return S(
            term,
            f"`{term}`控制load balancer/accelerator如何選target、跨AZ分流或把原始client/flow資訊傳給後端。",
            when,
            "Backend需要來源IP、session affinity、均衡AZ容量，或virtual appliance需要透明flow metadata時。",
            f"在{component} listener/target-group/load-balancer attributes中設定，並以多AZ clients及backend logs驗證實際source與distribution。",
            "Cross-zone可能增加跨AZ費用；關閉preserve client IP或未解析Proxy Protocol會讓backend看到錯誤來源，GENEVE也不是一般app protocol。",
        )
    if re.search(r"user pool|app client|hosted ui|federation|identity pool", lowered):
        return S(
            term,
            f"`{term}`定義application users、OAuth client、登入UI或外部IdP federation，以及token如何交給app/AWS credentials。",
            when,
            f"Consumer/web/mobile application使用{component}做註冊登入、social/enterprise federation或API token時。",
            "設定callback/logout URLs、OAuth flows/scopes、client secret策略、token lifetime與MFA；驗證issuer、audience、expiry及group claims。",
            "User pool authentication與identity-pool AWS authorization不是同一件事；把client secret放browser或未驗audience會形成漏洞。",
        )
    if re.search(r"stream|enhanced fan-out|iterator age", lowered):
        return S(
            term,
            f"`{term}`控制ordered event log是否啟用、consumer如何讀取，以及每個consumer的throughput/lag。",
            when,
            f"需要從{component}持續讀change/events、保留順序位置或讓多個consumer獨立擴展時。",
            "啟用stream，選view/retention與consumer mode；以partition/shard key維持所需順序，監控iterator age與checkpoint。",
            "Stream不是queue delete語意；consumer不checkpoint或partition skew會重讀/lag，enhanced fan-out也會增加費用。",
        )
    if re.search(r"data collection|agent/agentless|lookback|opt-in|recommendation preference", lowered):
        return S(
            term,
            f"`{term}`決定{component}收集多少歷史資料、涵蓋哪些resources，以及何時有足夠樣本產生assessment/recommendation。",
            when,
            "要用真實utilization、inventory與dependency資料做rightsizing、migration或service選擇，而非憑峰值猜測時。",
            "選擇agent/agentless與scope，涵蓋完整business cycle；確認權限、資料新鮮度與缺口，再設定recommendation preferences。",
            "樣本窗口太短會漏掉月末/季末峰值；opt-in不代表所有accounts/Regions與新resources都已持續收集。",
        )
    if re.search(r"redrive|replay|maxreceivecount", lowered):
        return S(
            term,
            f"`{term}`定義message失敗幾次後移到DLQ，以及修復後如何安全送回source queue或重新處理。",
            when,
            "Consumer可能遇到poison message，但不能讓同一錯誤無限阻塞或消耗主queue capacity時。",
            "設定RedrivePolicy/maxReceiveCount、DLQ retention與alarm；修復根因後以小批次redrive並保持consumer idempotent。",
            "未修根因便整批replay會再次塞滿queue；DLQ retention短於source queue也可能在調查前遺失失敗訊息。",
        )
    if re.search(r"reconnect|lag|test/cutover|promotion", lowered):
        return S(
            term,
            f"`{term}`描述failover/migration時的資料落後、切換步驟或client重新連線行為。",
            when,
            "Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。",
            "監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。",
            "只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。",
        )
    if re.search(r"statement|\\bsid\\b|effect|action/notaction|managed/inline policies|explicit deny|allow-list或deny-list|notaction", lowered):
        return S(
            term,
            f"`{term}`是IAM policy statement的結構或匹配欄位，決定哪些request得到Allow/Deny及規則如何被辨識。",
            when,
            "需要以least privilege描述API authorization，或用SCP/resource policy建立guardrail時。",
            "使用Version/Statement，為每段加入可讀Sid，再設定Effect、Action/NotAction、Resource與Condition；以正反caller/resource測試。",
            "NotAction配Allow/Deny很容易擴大scope；Sid只供閱讀不影響evaluation，任何applicable explicit Deny仍覆蓋Allow。",
        )
    if re.search(r"quota code|applied/default value|automatic management|increase request|cloudwatch usage", lowered):
        return S(
            term,
            f"`{term}`辨識服務上限、目前核准值、實際使用率與是否能自動或人工申請調高。",
            when,
            f"{component} capacity接近account/Region limit，或migration/launch會一次建立大量resources時。",
            "查詢quota code與adjustable屬性，將usage/quota比例送CloudWatch alarm，提前提交increase request並在目標Region驗證。",
            "Default quota不是所有account相同；申請提高也需要時間，且quota變大不會自動讓application或downstream擴展。",
        )
    if re.search(r"threshold|comparison|m/n|treat missing data|statistics/percentiles|\\bactions\\b", lowered):
        return S(
            term,
            f"`{term}`控制metric如何聚合、與門檻比較、需要幾個datapoints，以及缺資料與alarm action如何處理。",
            when,
            "需要可靠告警而不能被單點雜訊、短暫missing data或平均值掩蓋tail latency時。",
            "選擇正確namespace/dimensions/statistic，設定period、evaluation periods、DatapointsToAlarm、comparison與missing-data策略，再演練alarm。",
            "平均值會隱藏p99；missing data設錯可能把停止上報當健康或故障，alarm action也需要自己的IAM與rollback保護。",
        )
    if re.search(r"ipv6|non-overlap|prefix list|\\beip\\b|blackhole|scheme|tunnel option|acceleration", lowered):
        return S(
            term,
            f"`{term}`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。",
            when,
            "VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。",
            "記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。",
            "EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。",
        )
    if re.search(r"milestone|lens|pillar question|improvement|conformance pack|aggregator|recorder|delivery channel", lowered):
        return S(
            term,
            f"`{term}`控制architecture/compliance review的時間點、問題集合、資料收集scope、集中檢視或證據輸出。",
            when,
            "多帳號需要一致review、configuration inventory與可追蹤improvement plan時。",
            "指定owner、accounts/Regions、rules/lens與evidence destination，建立baseline milestone；每個finding都要有priority、期限與驗證方式。",
            "只產生報表不安排owner與remediation不會降低風險；recorder未涵蓋所有resource types/Regions也會形成假合規。",
        )
    if re.search(r"daemon/sdk/adot|annotations/metadata|finding groups|\\bgroups\\b|x-ray|artifacts|script", lowered):
        return S(
            term,
            f"`{term}`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。",
            when,
            "需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。",
            "部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。",
            "只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。",
        )
    if re.search(r"patch baseline|patch groups|scan/install|maintenance$", lowered):
        return S(
            term,
            f"`{term}`定義哪些patch被核准、哪些fleet套用、何時只掃描或實際安裝，以及如何回報compliance。",
            when,
            "EC2/on-prem managed nodes需要可分波、可稽核的OS patch流程時。",
            "建立baseline與approval delay，將instances標記到patch group，透過maintenance window先Scan再小批Install，監控reboot與rollback。",
            "直接全fleet Install可能造成同時reboot；compliant只表示符合baseline，不代表application已通過功能與容量測試。",
        )
    if re.search(r"workgroup|output location|bookmark|lob|extension pack|backfill|rpo monitoring|global database", lowered):
        return S(
            term,
            f"`{term}`控制analytics/database工作隔離、結果位置、增量進度、大型欄位處理、schema輔助或跨Region複寫狀態。",
            when,
            "Query/ETL/migration需要限制成本、可重跑增量工作、處理特殊資料型別或監控replication lag時。",
            "設定具名workgroup/result bucket、bookmark/checkpoint、LOB mode或conversion extension；以資料筆數、checksum、lag與cost驗證。",
            "Result bucket權限/KMS錯誤會讓query失敗；bookmark不是transaction，backfill與LOB truncation也可能造成靜默資料缺漏。",
        )
    if re.search(r"key algorithm|key spec/usage|hsm users|quorum", lowered):
        return S(
            term,
            f"`{term}`決定cryptographic key的演算法/用途，以及HSM中誰能管理或需要多少成員共同完成敏感操作。",
            when,
            "TLS、簽章、加解密或專用HSM有相容性、法規與separation-of-duties要求時。",
            "選擇對應service/client支援的RSA/ECC/symmetric spec與usage，建立最少HSM users及quorum/backup/runbook並測試restore。",
            "錯誤algorithm/usage會無法整合；把所有HSM權限交給單一人或遺失quorum credentials可能讓keys永久不可用。",
        )
    if re.search(r"standard/one zone|cluster mode|auto-pause|mrsc availability|managed database|\\bad\\b|shared directories", lowered):
        return S(
            term,
            f"`{term}`選擇資料/目錄service的availability、分片、節點休眠或managed integration模式。",
            when,
            "需要在成本與AZ/Region容錯、scale、Windows domain整合或閒置資源間做取捨時。",
            "明確選擇deployment/cluster/AD mode與AZs，設定failover/replica或auto-pause條件；以dependency failure與喚醒延遲測試。",
            "One Zone不適合不能接受AZ資料損失的state；auto-pause會增加首次連線延遲，目錄分享也仍需DNS/trust/network。",
        )
    if re.search(r"foundation model|contextual grounding|\bsync\b|input transformer|usage plan", lowered):
        return S(
            term,
            f"`{term}`控制model選擇/grounding、knowledge-base同步、event payload轉換或API consumer的quota/rate plan。",
            when,
            "AI、event-driven或public API需要可版本化quality、資料新鮮度、payload contract或tenant限額時。",
            "鎖定model/version與eval，設定grounding threshold或sync schedule；event/API則定義transform schema、API key plan、quota與throttle。",
            "Model或sync成功不代表回答正確；input transform漏欄位會破壞consumer，usage plan也不能取代authentication/authorization。",
        )
    if re.search(r"aft customization|include nested stacks|replacement|execution$|failure tolerance|session preferences", lowered):
        return S(
            term,
            f"`{term}`控制{component}的客製化、變更執行scope、失敗容忍度或operator session行為。",
            when,
            "平台需要批次部署多帳號/stack、控制失敗停止條件，或為管理session設定安全與logging偏好時。",
            "版本化customization/change set，設定concurrency與failure tolerance；執行前review replacement，session則設定KMS/log destination與IAM conditions。",
            "大量並行加上過高failure tolerance會擴大錯誤；resource replacement可能造成資料或endpoint變更，必須先規劃rollback。",
        )
    if re.search(r"management/data events|cloudtrail lake|^lake$|cloudwatch$|monitoring$", lowered):
        return S(
            term,
            f"`{term}`決定{component}蒐集哪些control/data-plane audit events，以及如何集中查詢或監控。",
            when,
            "需要回答誰在何時修改resource、誰讀寫敏感資料，或集中多帳號事件調查時。",
            "選擇management/data event selectors、accounts/Regions、retention與S3/Lake/CloudWatch destination；用已知API call驗證事件可查。",
            "Data events量大且可能昂貴；只開management events看不到S3 object/Lambda invoke等data-plane行為。",
        )
    if re.search(r"datasync.*agent|^agent$|add-ons|taints|rds proxy相容性|service name", lowered):
        return S(
            term,
            f"`{term}`指定{component}依賴的runtime integration、scheduler限制、proxy相容性或要連接的AWS endpoint。",
            when,
            "Managed control plane仍需要local agent、cluster extension、placement constraint或具名service integration時。",
            "鎖定版本與service identifier，配置network/IAM，先在非production驗證compatibility；taint同時配置對應toleration。",
            "Agent/add-on版本落後會造成同步或network問題；只設taint沒有toleration會讓pods無法排程，service name選錯Region也無法連線。",
        )
    if re.search(r"drt/srt contacts|proactive engagement|chain of custody|cluster/edge compute|shipping", lowered):
        return S(
            term,
            f"`{term}`定義重大DDoS或實體device流程中的聯絡人、主動協作、邊緣執行與保管交接證據。",
            when,
            "Security incident需要AWS支援立即聯絡，或使用Snow device離線搬移敏感資料時。",
            "維護24x7 contacts與runbook，設定engagement前置資料；device每次寄送、接收、unlock、copy與return都保存custody record。",
            "過期contact會錯過事件；實體device沒有custody/erase驗證，或把edge compute當永久資料中心，都會留下風險。",
        )
    if re.search(r"immutability|authentication$|allow/deny|offering class|allocation strategy|interruption handling|max price", lowered):
        return S(
            term,
            f"`{term}`控制artifact不可覆寫、client驗證，或capacity/discount方案如何選擇與面對中斷。",
            when,
            "Image supply chain、managed broker access，或Spot/Reserved capacity需要可預測風險與成本時。",
            "開啟immutable tags與scan；authentication選IAM/SASL/TLS並測試；Spot使用capacity-optimized與instance diversification，建立checkpoint/termination handling。",
            "只設max price不能保證Spot capacity；mutable image tag會讓同一版本指向不同內容，authentication也不取代topic/network authorization。",
        )
    if re.search(r"hierarchy|top-level/child pools|parameter store.*polic|^policies$", lowered):
        return S(
            term,
            f"`{term}`建立父子namespace/pool與生命週期規則，讓{component}可以委派、繼承或依路徑管理資源。",
            when,
            "多團隊需要分層管理parameters或IP ranges，並避免名稱/CIDR碰撞時。",
            "先建立top-level owner與child boundaries，使用穩定path/CIDR allocation rules；對敏感values加IAM/KMS並監控過期/未使用項目。",
            "Hierarchy只是組織方式，不自動授權；child pool過度切割會浪費地址，parameter policy也不是完整secret rotation。",
        )
    if re.search(r"^job$|^status$|^network$|^ad$|license assumptions", lowered):
        return S(
            term,
            f"`{term}`指定{component}的工作生命週期、啟用狀態、network/domain整合或成本模型假設。",
            when,
            "服務需要提交可追蹤job、明確enable/disable，連接VPC/AD，或估算BYOL/license成本時。",
            "記錄input/output與job status，設定subnets/SG/DNS/AD trust；成本評估則驗證license edition、core rules與utilization window。",
            "Job submitted不代表完成；status disabled會讓rule不執行，AD/network錯誤會timeout，錯誤license假設會扭曲business case。",
        )
    if re.search(r"\bsid\b|^action$|防止移除boundary|s3:listbucket|object actions", lowered):
        return S(
            term,
            f"`{term}`是policy statement識別、API action/resource配對，或保護permissions boundary不被委派管理者繞過的設定。",
            when,
            "要寫可review的IAM/S3 least-privilege policy，或允許團隊建role但不能突破平台上限時。",
            "Sid使用可讀名稱；Action配正確resource ARN。ListBucket使用bucket ARN，GetObject使用object ARN；以condition/SCP拒絕移除核准boundary。",
            "Sid不影響授權；bucket/object ARN配反會AccessDenied。只附boundary卻允許建立者移除它，等於沒有安全上限。",
        )
    if re.search(r"data owner|network exposure|patching|service abstraction", lowered):
        return S(
            term,
            f"`{term}`用來判斷shared-responsibility邊界：誰決定資料、入口、OS/runtime更新，以及managed service接手到哪一層。",
            when,
            "比較EC2、container與serverless，或事故後判斷哪個team/vendor應預防、偵測與修復時。",
            "為每層建立RACI：AWS、platform、application、security與data owner；將patch、IAM、encryption、backup與logging責任寫進runbook。",
            "Managed不代表customer免責；AWS patch hypervisor不會替你修application dependency，private subnet也不代表資料已授權。",
        )
    if lowered == "官方sample questions":
        return S(
            term,
            "官方sample questions展示題型、用詞與job-role推理深度，用來校準讀題方式，不是完整題庫或實際考題清單。",
            "開始準備、考試版本更新，或想確認自己是在背產品名稱還是能處理scenario constraints時。",
            "先限時作答，再把每個選項映射到exam task、hard constraint與錯誤假設；只引用官方公開題目並記錄版本日期。",
            "只背sample答案會嚴重過度擬合；少量sample也不能推論某個服務一定出題或完整反映權重。",
        )
    if lowered == "groups":
        if component == "Amazon Cognito":
            return S(
                term,
                "Cognito groups把user pools中的users分類，group可進token claims並設定role precedence，方便application做粗粒度authorization。",
                "多種使用者角色需要不同UI/API權限，但不想為每位user單獨管理相同claims時。",
                "建立group、加入users並檢查ID/access token中的cognito:groups；API仍需驗證token與將group映射到具體permissions。",
                "Group claim不是萬用admin開關，也不適合取代細粒度resource authorization；user加入多groups時要處理precedence。",
            )
        return S(
            term,
            "Trace groups以filter expression建立動態trace集合，方便把特定service、error、latency或annotation的requests分開觀察。",
            "需要針對一類transaction建立service map、metrics與調查入口，而不是掃描所有traces時。",
            "建立group filter並以代表性trace驗證命中；filter使用可索引annotations與service/error屬性，避免敏感或高基數資料。",
            "Group不會增加未被sample的traces；filter過寬會增加查詢成本，過窄則讓事故看似沒有資料。",
        )
    if lowered == "actions":
        if component == "AWS Fault Injection Service":
            return S(
                term,
                "FIS actions是實驗要注入的故障，例如stop instances、增加CPU壓力、network disruption或API throttle。",
                "需要驗證autoscaling、failover、alarm與runbook是否真的能承受特定failure mode時。",
                "選擇具體action ID、targets、parameters與duration，設定stop conditions與最小IAM role，先在小scope執行。",
                "沒有stop condition或tag-scoped targets可能影響production大範圍；故障實驗不能用來首次發現沒有backup。",
            )
        return S(
            term,
            "Alarm actions是在狀態轉為ALARM、OK或INSUFFICIENT_DATA時通知SNS、調整Auto Scaling或執行支援的自動化動作。",
            "告警需要通知owner或觸發安全、可逆且有明確邊界的自動反應時。",
            "為每個state設定action ARN與service role，先用測試metric驗證；高風險remediation加入rate limit、approval與rollback。",
            "Alarm action不是無條件修復；反覆flapping可能重複觸發，錯誤自動化也可能比原故障造成更大blast radius。",
        )
    if lowered == "waf":
        guide = next(g for g in EXPLICIT_GUIDES["Amazon CloudFront"] if g.name == "WAF")
        return SettingGuide(term, guide.controls, guide.when, guide.configure, guide.pitfall)
    if lowered == "eip":
        return S(
            term,
            "Elastic IP是帳號/Region內可重新關聯的static public IPv4；public NAT Gateway使用它作Internet看到的source address。",
            "外部allowlist要求固定egress IPv4，或resource replacement後仍需保留相同public address時。",
            "先allocate EIP，再建立public NAT Gateway於具有IGW route的public subnet並指定AllocationId；每個AZ使用自己的NAT/EIP。",
            "單一EIP/NAT跨AZ共用會形成failure/cost path；EIP稀缺且可能收費，也不提供incoming access到private instances。",
        )
    if re.search(r"parameter group|option group|engine parameter|configuration$", lowered):
        return S(
            term,
            f"`{term}`是一組可版本化的engine/runtime參數，會改變{component}的實際process行為。",
            when,
            f"複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。",
            "一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。",
        )
    if re.search(r"object ownership|bucket type|transition|expiration|noncurrent|abortincomplete|legal hold|retain-until|object lock|governance/compliance", lowered):
        return S(
            term,
            f"`{term}`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。",
            when,
            f"需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。",
            f"在{component}設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。",
            "Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。",
        )
    if re.search(r"oversize handling|managed rule|ip sets|allow lists|threat lists|suppression rule", lowered):
        return S(
            term,
            f"`{term}`控制security rule/detector如何匹配、略過或處理超出可檢查大小的資料。",
            when,
            f"要用{component}阻擋或分類traffic/findings，同時控制false positive與檢查盲點時。",
            "先以Count/monitor觀察命中，設定明確scope與例外到期日；oversize值需選continue、match或no-match並測試大payload。",
            "永久allow/suppress會形成監控盲點；一律阻擋oversize也可能誤傷合法upload，必須配合logging與抽樣驗證。",
        )
    if "cors" in lowered:
        return S(
            term,
            "CORS決定browser中的某個origin能否以指定methods/headers呼叫另一個origin；它是browser enforcement，不是API authentication。",
            f"Web frontend與{component} API使用不同scheme、host或port，而且browser需要送出credential或non-simple request時。",
            "設定AllowOrigins、AllowMethods、AllowHeaders、ExposeHeaders與MaxAge；使用credentials時不可用*允許所有origins，並測試preflight OPTIONS。",
            "curl成功不代表browser會放行；CORS header也不能阻止非browser client，真正授權仍需JWT、IAM或OAuth authorizer。",
        )
    if "long polling" in lowered:
        return S(
            term,
            "Long polling讓ReceiveMessage等待一段時間直到message出現，減少空回應、API calls與consumer成本。",
            f"Consumer持續從{component} queue取工作，而且低流量時大量short polls都拿不到message。",
            "設定ReceiveMessageWaitTimeSeconds或每次WaitTimeSeconds；client HTTP timeout必須大於long-poll時間，並監控空回應與queue age。",
            "Long polling不增加consumer處理capacity，也不修正backlog；client timeout過短會先斷線並造成額外retry。",
        )
    if re.search(r"rcu/wcu|on-demand/provisioned|provisioned/serverless", lowered):
        return S(
            term,
            f"`{term}`決定{component}如何取得read/write、stream或compute capacity：依請求計價，或預先配置並autoscale。",
            when,
            "新或不可預測流量先比較on-demand/serverless；穩定可預測流量再比較provisioned與承諾成本。",
            "設定capacity mode、table/index/shard/node容量與autoscaling min/max；監控Consumed、Throttled、utilization與hot-key分布。",
            "總容量足夠仍可能因hot partition被throttle；切換計價模式也不會修正錯誤partition key或下游瓶頸。",
        )
    if re.search(r"consistency|transactions|global write|write forwarding|promotion tier|headless secondary", lowered):
        return S(
            term,
            f"`{term}`定義read/write一致性、authoritative writer、promotion或跨Region寫入語意。",
            when,
            "Business invariant不能接受舊讀、雙寫衝突或不確定writer時，必須明確選擇並驗證。",
            f"記錄{component}的single/multi-writer、strong/eventual read、conflict rule與promotion order；以partition/failover game day驗證。",
            "把replication誤認成zero-RPO transaction，或failover後兩邊繼續寫入，會造成split brain與難以合併的資料。",
        )
    if re.search(r"launch template|job definition|task definition|documents|blueprint|bundle|appspec|\.ebextensions|user data|bootstrap", lowered):
        return S(
            term,
            f"`{term}`是可版本化的啟動或工作規格，定義{component}建立runtime時使用的image、commands、roles、capacity與network。",
            when,
            "同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。",
            "把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。",
            "直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。",
        )
    if re.search(r"region|\baz\b|data residency|locale", lowered):
        return S(
            term,
            f"`{term}`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。",
            when,
            f"部署{component}前依使用者位置、data residency、service availability與DR需求決定。",
            "建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。",
            "第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。",
        )
    if re.search(r"validation|verification|assessment|scan type|scan on push|compliance|action items|report type|official sample", lowered):
        return S(
            term,
            f"`{term}`定義{component}用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。",
            when,
            "需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。",
            "選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。",
            "工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。",
        )
    if re.search(r"source|target|origin|destination|input/output|connection|data lake locations|s3 bucket", lowered):
        return S(
            term,
            f"`{term}`指定{component}讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。",
            when,
            "服務要跨bucket、database、VPC、account或Region移動或處理資料時。",
            "使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。",
            "只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。",
        )
    if re.search(r"\bmode\b|type|tier|edition|standard/express|hosted/dedicated|ec2/serverless/eks", lowered):
        return S(
            term,
            f"`{term}`選擇{component}的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。",
            when,
            "先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。",
            "建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。",
            "把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。",
        )
    if re.search(r"application|workload|environment|profile|framework|home region|waves|inventory", lowered):
        return S(
            term,
            f"`{term}`定義{component}管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。",
            when,
            "多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。",
            "以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。",
            "只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。",
        )
    if re.search(r"eventbridge|lambda transform|integration|connector|hooks|post-launch|automation|remediation", lowered):
        return S(
            term,
            f"`{term}`把{component}與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。",
            when,
            "Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。",
            "定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。",
            "Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。",
        )
    if re.search(r"subscription|subscribers|notification|targets|raw delivery|event buses", lowered):
        return S(
            term,
            f"`{term}`定義event/notification送到哪些consumers，以及是否套用filter、保留payload或跨帳號分享。",
            when,
            "一個producer需要fan-out到多個consumer、告警對象或workflow入口時。",
            "建立target/subscription與filter，設定resource policy、retry/DLQ和owner；用匹配與不匹配event各測一次。",
            "只建立topic/bus卻沒有可用target不會產生business effect；consumer仍需處理duplicate與schema evolution。",
        )
    if re.search(r"external id|session name|source identity|session tag|credential provider|token lifetime", lowered):
        return S(
            term,
            f"`{term}`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。",
            when,
            "Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。",
            "在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。",
            "ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。",
        )
    if re.search(r"chunking|embedding|reranker|temperature|max tokens|instruction|inference profile|vector store|knowledge base", lowered):
        return S(
            term,
            f"`{term}`控制生成式AI的retrieval、sampling、context或inference routing，直接影響quality、latency與token cost。",
            when,
            f"使用{component}處理RAG、agent或production inference，而不是單次playground實驗時。",
            "用版本化eval dataset比較設定，記錄model/version、chunk size/overlap、top-k、temperature與max tokens。",
            "只看一個demo容易過度擬合；低temperature不保證正確，更多context也可能增加雜訊與成本。",
        )
    if re.search(r"networkmode|cni|network connections|static ip|load balancer|\bnlb\b|\blb\b", lowered):
        return S(
            term,
            f"`{term}`決定workload如何取得network identity或接入load-balancing/service path。",
            when,
            "Container、endpoint或application需要穩定入口、獨立ENI/IP或跨network consumer時。",
            "明確選擇network mode、target type、subnets與SG，建立health check及DNS；從client到target逐跳驗證。",
            "有load balancer不代表target健康；network mode與target type不相容會無法註冊或無法回程。",
        )
    if re.search(r"storage|ephemeral|file-system|smb/nfs/iscsi|emrfs|ebs|multi-attach", lowered):
        return S(
            term,
            f"`{term}`選擇{component}的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。",
            when,
            "Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。",
            "先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。",
            "Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。",
        )
    if re.search(r"performance mode|throughput mode|i/o-optimized|wlm|spectrum|eviction", lowered):
        return S(
            term,
            f"`{term}`改變{component}的performance/cost策略，例如並行度、I/O計價、query scheduling或memory回收。",
            when,
            "已有代表性load與瓶頸證據，能說明是latency、throughput、concurrency、I/O cost或memory pressure問題時。",
            "用benchmark比較候選mode，設定queue/class/eviction policy，觀察p95/p99、queue time、hit ratio及unit cost。",
            "未先找瓶頸便切換模式可能只增加費用；問題也可能來自data model或workload isolation。",
        )
    if re.search(r"purchase option|tenancy|spot|savings|reserved", lowered):
        return S(
            term,
            f"`{term}`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。",
            when,
            "已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。",
            "穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。",
            "先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。",
        )
    if re.search(r"grant|agreement|delegation|sso owner|allowed principal", lowered):
        return S(
            term,
            f"`{term}`指定誰能使用、管理或接受{component}的resource/contract，是delegated ownership與authorization的一部分。",
            when,
            "跨帳號、中央平台、KMS/data-lake分享或第三方存取需要把owner與consumer分開時。",
            "使用具名role/account/organization與最小actions，設定可撤銷grant/assignment，並以audit驗證實際principal。",
            "信任整個account或永久delegation會擴大blast radius；data access也可能仍缺KMS或network permission。",
        )
    if re.search(r"detector|protection plan|automated discovery|classification job|custom data identifier|behavior graph", lowered):
        return S(
            term,
            f"`{term}`選擇{component}分析哪些telemetry/data，以及如何建立finding或敏感資料分類。",
            when,
            "需要持續威脅偵測、資料發現或調查關聯，而不是一次人工檢查時。",
            "啟用正確accounts/Regions/data sources，設定organization admin、sampling與finding destination；用測試訊號驗證。",
            "Detector開啟但data source未涵蓋、sample過少或finding無owner，仍會留下盲點。",
        )
    if re.search(r"feature flag|attribute|build/start command|preset|pipeline|array jobs", lowered):
        return S(
            term,
            f"`{term}`定義{component}要執行的功能、命令或批次單位，是application behavior與release contract。",
            when,
            "同一artifact要依環境切換功能、建立可重複run流程或平行處理大量相似jobs時。",
            "版本化command/flag schema，設定validation/default與修改權限；以canary和明確rollback條件推出。",
            "沒有owner/expiry的feature flag會永久累積；command、preset或array index不驗證會大規模重複失敗。",
        )
    if re.search(r"association|appliance mode|ecmp|multicast", lowered):
        return S(
            term,
            f"`{term}`控制{component}的route-domain membership、對稱inspection或多路徑/群組傳送行為。",
            when,
            "使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。",
            "明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。",
            "Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。",
        )

    if re.search(
        r"dns|hostname|hosted zone|resolver|custom domain|domain name|domain validation|\bsan\b",
        lowered,
    ):
        return S(
            term,
            f"`{term}`控制名稱如何被解析或驗證；DNS只把名稱轉成目標資料，不會替代route、network policy或IAM。",
            when,
            f"在{component}的DNS／domain設定中明確指定zone、name、resolver direction或validation方式，並用dig/nslookup從實際來源網路驗證答案。",
            "只在console看到名稱存在，不代表所有VPC、Region與client都得到同一答案；還要檢查cache TTL、zone association與return path。",
        )
    if re.search(r"listener|certificate|protocol|port|tls|ssl", lowered):
        return S(
            term,
            f"`{term}`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。",
            when,
            f"在{component}的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。",
            "入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。",
        )
    if re.search(r"route|cidr|subnet|vpc|endpoint|gateway|attachment|propagation|vif|vlan|bgp|asn|eni", lowered):
        return S(
            term,
            f"`{term}`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。",
            when,
            f"在{component}的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。",
            "只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。",
        )
    if re.search(r"security group|\bsg\b|nacl|firewall|public|private|ingress|egress|home_net", lowered):
        return S(
            term,
            f"`{term}`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。",
            when,
            f"在{component}中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。",
            "Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。",
        )
    if re.search(r"policy|principal|role|iam|permission|assignment|mfa|access|identity|trust|authoriz|scim", lowered):
        return S(
            term,
            f"`{term}`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。",
            when,
            f"在{component}明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。",
            "使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。",
        )
    if re.search(r"kms|encrypt|securestring|secret|rotation|alias|key policy|customer managed key", lowered):
        return S(
            term,
            f"`{term}`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。",
            when,
            f"在{component}指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。",
            "資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。",
        )
    if re.search(r"timeout|ttl|retention|duration|period|schedule|window|delay|bake|grace|warmup|interval", lowered):
        return S(
            term,
            f"`{term}`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。",
            when,
            f"以business latency、RTO/RPO與上游/downstream timeout chain設定{component}的秒數或schedule；用最慢合理案例與故障注入驗證。",
            "值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。",
        )
    if re.search(r"health|failover|drill|restore|stop condition|safety", lowered):
        return S(
            term,
            f"`{term}`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。",
            when,
            f"在{component}設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。",
            "只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。",
        )
    if re.search(r"memory|cpu|vcpu|gpu|rpu|acu|instance|node|broker|shard|partition|capacity|iops|throughput|bandwidth|size|min/max|desired|concurrency|scal|worker", lowered):
        return S(
            term,
            f"`{term}`設定{component}的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。",
            when,
            f"先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。",
            "只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。",
        )
    if re.search(r"\blog\b|logging|logs|metric|alarm|dashboard|trace|sampling|report|evidence|insight|publishing", lowered):
        return S(
            term,
            f"`{term}`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。",
            when,
            f"在{component}選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。",
            "開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。",
        )
    if re.search(r"backup|snapshot|pitr|replica|replication|multi-az|multi-region|copy|vault|versioning|lifecycle|archive", lowered):
        return S(
            term,
            f"`{term}`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。",
            when,
            f"在{component}依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。",
            "有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。",
        )
    if re.search(r"cache|compression|buffer|format|parquet|orc|materialized|result reuse", lowered):
        return S(
            term,
            f"`{term}`改變資料表示、批次大小或重用方式，以較少origin/compute工作換取新鮮度與複雜度。",
            when,
            f"在{component}依access pattern設定cache key/TTL、buffer size/time或columnar/compression format，並同時量測hit ratio、freshness與unit cost。",
            "Cache不是authoritative state；錯誤key、無界TTL、過小files或過大buffers會造成資料錯誤、延遲與昂貴掃描。",
        )
    if re.search(r"dlq|redrive|retry|batch|visibility|dedup|messagegroup|fifo|ordering|iterator|queue", lowered):
        return S(
            term,
            f"`{term}`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。",
            when,
            f"在{component}依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。",
            "Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。",
        )
    if re.search(r"pk|sk|gsi|lsi|index|sort|distribution|projection|schema|table|query|measure|dimension", lowered):
        return S(
            term,
            f"`{term}`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。",
            when,
            f"先列出{component}的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。",
            "先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。",
        )
    if re.search(r"deploy|blue/green|canary|rolling|traffic|alias|appspec|hook|change set|drift|rollback|release", lowered):
        return S(
            term,
            f"`{term}`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。",
            when,
            f"在{component}設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。",
            "只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。",
        )
    if re.search(r"tag|label|\bou\b|account|organization|admin|scope|delegate|sharing|billing", lowered):
        return S(
            term,
            f"`{term}`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。",
            when,
            f"在{component}建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。",
            "Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。",
        )
    if re.search(r"engine|platform|runtime|image|ami|release|version|parameter group|option group|configuration", lowered):
        return S(
            term,
            f"`{term}`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。",
            when,
            f"在{component}鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。",
            "使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。",
        )
    if re.search(r"budget|cost|forecast|payment|term|commitment|utilization|coverage|granularity", lowered):
        return S(
            term,
            f"`{term}`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。",
            when,
            f"在{component}設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。",
            "只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。",
        )
    if re.search(r"rule|priority|condition|filter|pattern|classifier|mapping|validator|control", lowered):
        return S(
            term,
            f"`{term}`描述request/resource如何被分類與匹配，命中後才執行相應action。",
            when,
            f"在{component}以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。",
            "重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。",
        )

    return S(
        term,
        f"`{term}`是{component}的control-plane設定，會改變「{profile.mechanism}」中的某個runtime contract，而不是裝飾性名稱。",
        when,
        f"在{component}console、Create/Update API或IaC property中明確設定`{term}`；記錄預期值、owner、變更方式與一個可重現的正反測試。",
        f"若不知道這個欄位改變哪個request/state/failure boundary，就不應沿用default。需求轉為「{profile.replace}」時也應重新選型。",
    )


def setting_guides(
    component: str, profile: ComponentProfile
) -> tuple[SettingGuide, ...]:
    explicit = EXPLICIT_GUIDES.get(component)
    if explicit is not None:
        return explicit
    return tuple(
        _generic_guide(component, term, profile)
        for term in _split_settings(profile.config)
    )


CONCEPT_GLOSSARY: dict[str, str] = {
    "AWS account": "AWS中的資源、身份、quota與billing隔離邊界；企業通常用多帳號縮小blast radius，而不是把所有環境塞在同一帳號。",
    "workload": "共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。",
    "Region": "AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。",
    "certification exam": "以公開exam guide中的domains與tasks抽樣評估job-role能力；題目測constraint與trade-off，不代表所有服務同深度出題。",
    "shared responsibility": "AWS負責cloud本身的基礎設施；customer負責cloud內的資料、身份、設定與workload。服務越managed，責任會移動但不會消失。",
    "pillar": "Well-Architected用來檢視架構的一個品質維度：operational excellence、security、reliability、performance efficiency、cost optimization與sustainability。",
    "DNS": "Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。",
    "DNS resolution": "名稱解析過程。得到IP只代表知道目的地，不代表route、firewall、TLS與IAM一定允許連線。",
    "resolver": "代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。",
    "hostname": "可讀的網路名稱，例如api.example.com；程式先經DNS取得address後才建立TCP/UDP連線。",
    "IP address": "網路介面的數字位址。Private IP在私有routing domain內使用；public IP可經Internet routing。",
    "CIDR": "以10.0.0.0/16這類prefix描述一段IP範圍；prefix越大，範圍越小。重疊CIDR會破壞明確routing。",
    "subnet": "VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。",
    "route": "描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。",
    "route table": "保存routes並以longest-prefix match選下一跳的表格。",
    "transitive routing": "A能到B且A能到C時，B是否可經A到C；VPC Peering不提供此能力，TGW可建立受控hub routing。",
    "TCP": "需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。",
    "UDP": "不先建立可靠connection的datagram協定，延遲低但application需自行處理遺失與順序。",
    "TLS": "在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。",
    "HTTP": "Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。",
    "Layer 4": "依IP、port與TCP/UDP flow處理流量，不理解HTTP path/headers；NLB屬於此類。",
    "Layer 7": "理解HTTP等application protocol，可依host/path/header做routing；ALB與CloudFront屬於此類。",
    "listener": "在load balancer指定protocol/port等待client connection的入口。",
    "listener rule": "依priority與conditions匹配request，再forward、redirect、authenticate或回固定response。",
    "target group": "一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。",
    "health check": "系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。",
    "stickiness": "以cookie讓同一client暫時持續導向同一target；它是相容legacy state的折衷，不是高可用session store。",
    "cookie": "Browser隨HTTP request帶回的小段name/value資料；可保存session identifier或load-balancer affinity。",
    "idle timeout": "Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。",
    "origin": "CDN/cache miss時真正取得內容的後端，例如S3、ALB或HTTP server。",
    "edge": "靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。",
    "cache": "可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。",
    "cache key": "決定兩個request能否共用同一cached response的識別值，通常由path與選定headers/cookies/query組成。",
    "TTL": "Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。",
    "OAC": "CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。",
    "SigV4": "AWS Signature Version 4，使用credential、時間與request內容產生簽章，讓服務驗證caller與request完整性。",
    "security group": "附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。",
    "NACL": "Network ACL，subnet邊界的stateless ordered allow/deny rules；去回程與ephemeral ports要分開允許。",
    "ENI": "Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。",
    "NAT": "Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。",
    "VPN": "Virtual Private Network，在既有Internet上建立加密tunnel；AWS Site-to-Site VPN通常提供兩條IPsec tunnels。",
    "Direct Connect": "從客戶或colocation到AWS的專用網路連線；提供較穩定路徑，但本身不等於端到端加密或自動高可用。",
    "hybrid connectivity": "讓on-premises與cloud長期互通的network、DNS、identity與routing設計，不只是建立一條VPN。",
    "BGP": "Border Gateway Protocol，在network peers間交換可達prefix與path資訊；DX/VPN常用它動態學習routes。",
    "VLAN": "Virtual LAN，在共享實體link上以標記隔離Layer-2 traffic；Direct Connect VIF配置會使用VLAN ID。",
    "VPC endpoint": "讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。",
    "principal": "AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。",
    "role": "可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。",
    "policy": "以statements描述Effect、Action、Resource、Principal與Condition的授權規則。",
    "explicit Deny": "明確拒絕request的policy結果；只要任一applicable policy命中Deny，就會覆蓋Allow。",
    "least privilege": "只授予完成目前工作需要的actions、resources、conditions與時間，而非先給admin再期待人工回收。",
    "temporary credentials": "具有到期時間的access key、secret與session token，通常由STS簽發，比長期key更易限制與輪替。",
    "federation": "讓外部IdP驗證使用者或workload，再交換AWS temporary role session，而不為每人建立獨立長期AWS密碼。",
    "IdP": "Identity Provider，保存或驗證使用者身份的系統，例如Entra ID、Okta或企業目錄。",
    "control plane": "建立或修改resource、policy、route、capacity與metadata的管理路徑。",
    "data plane": "實際處理每個packet、request、message、query與資料讀寫的runtime路徑。",
    "managed service": "供應商接手部分基礎設施責任的服務；customer仍負責資料、身份、設定、access pattern與business correctness。",
    "envelope encryption": "先用data key加密大量資料，再用KMS key加密較小的data key；避免每個資料block都直接呼叫KMS。",
    "data key": "實際加密application資料的對稱key；通常只在記憶體中短暫使用，儲存的是被KMS key加密後的副本。",
    "KMS key": "KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。",
    "failure domain": "會因同一事件一起失效的資源集合，例如單一instance、AZ或Region。",
    "blast radius": "一個故障、bug或錯誤變更最多能影響的使用者、租戶、accounts或Regions範圍。",
    "Multi-AZ": "把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。",
    "Multi-Region": "把服務或資料放到多個Regions，能處理Region級故障，但要額外設計replication、write ownership與failover。",
    "RTO": "Recovery Time Objective，災難後business service必須在多久內恢復。",
    "RPO": "Recovery Point Objective，災難後可接受資料最多落後或遺失多久。",
    "availability": "需要服務時成功取得回應的程度；多副本、health routing與減少同步依賴可改善。",
    "durability": "已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。",
    "scalability": "系統增加資源後可處理更多工作且不破壞正確性的能力；仍受partition、shared dependency與quota限制。",
    "elasticity": "容量能依需求自動增減的速度；受metrics、warm-up、quota與downstream capacity限制。",
    "quota": "AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。",
    "throttling": "服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。",
    "queue": "保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。",
    "stream": "有順序位置、可由多consumer重讀的事件紀錄；partition/shard決定ordering與parallelism邊界。",
    "event": "描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。",
    "DLQ": "Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。",
    "visibility timeout": "SQS message被consumer取得後暫時隱藏的時間；處理未完成前到期會讓它再次可見。",
    "idempotency": "同一operation重複執行，business effect仍只發生一次或得到等價結果。",
    "retry": "暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。",
    "backoff": "每次retry前逐步增加等待，避免所有clients持續打滿失敗服務。",
    "jitter": "在retry delay加入隨機性，避免大量clients在同一時刻同步重試。",
    "cold start": "Serverless/container在沒有可重用execution environment時建立runtime的額外延遲。",
    "EC2 instance": "AWS虛擬機執行個體，由AMI、instance type、network、storage與IAM instance profile共同定義。",
    "AMI": "Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。",
    "placement group": "控制EC2 instances在底層硬體中的相對放置：cluster偏低延遲、spread偏隔離、partition偏大型分區故障邊界。",
    "concurrency": "同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。",
    "IOPS": "每秒可完成的I/O operations數，偏向小型random reads/writes能力。",
    "throughput": "每秒能傳輸的資料量，偏向大型sequential I/O或network流量。",
    "replica": "authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。",
    "transaction": "一組資料操作以共同原子性、一致性、隔離與持久性邊界完成；跨服務通常需要saga或補償，而非單一database transaction。",
    "eventual consistency": "更新後不同副本可能暫時看到舊值，但在沒有新更新時最終收斂；application必須容忍stale reads與重複event。",
    "data warehouse": "為重複分析、聚合與joins最佳化的columnar analytical database，不是一般低延遲OLTP transaction store。",
    "data lake": "以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。",
    "catalog": "描述datasets、schema、partition與location的metadata索引；它不保存原始資料本身。",
    "ETL": "Extract、Transform、Load，把來源資料抽取、清理/轉換後載入目標；ELT則先載入再於目標轉換。",
    "workflow": "把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。",
    "human approval": "高風險action執行前由具名人員查看evidence並做有期限、不可重放且可稽核的決策。",
    "callback token": "Workflow把唯一task token交給外部worker/approver，之後以SendTaskSuccess/Failure恢復暫停execution。",
    "metric": "可聚合的時間序列數值，例如latency、error rate或queue age。",
    "log": "離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。",
    "trace": "把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。",
    "alarm": "metric符合threshold/evaluation條件時改變狀態並通知或觸發action。",
    "SLO": "Service Level Objective，團隊希望在時間窗口內達到的可靠性目標。",
    "SLA": "對外合約承諾，通常包含可用性計算、排除條款與未達成時的補償；不等於內部工程SLO或單一AWS服務SLA。",
    "IaC": "Infrastructure as Code，以版本化template/code建立與修改基礎設施，使review、重建與rollback更可重複。",
    "canary": "先把小比例流量或少數targets導向新版本，觀察technical與business指標後再擴大，以限制錯誤版本的blast radius。",
    "rollback": "把變更退回已知可用版本；資料schema與side effects也必須保持可逆或有補償。",
    "drift": "實際resource設定與IaC宣告狀態不同，常由console手動修改或外部automation造成。",
    "CloudFormation": "AWS IaC服務，將template中的Resources與properties轉成stack並管理create/update/delete生命週期。",
    "template": "宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。",
    "stack": "CloudFormation以一個生命週期單位管理的一組resources；更新與刪除行為受dependencies及policies影響。",
    "change set": "CloudFormation在執行前計算預計新增、修改、刪除或替換哪些resources，供review但不保證application side effects。",
    "Reserved Instance": "對特定EC2/RDS等使用條件提供計價折扣或容量選項；它不是新的instance，也不會自動改善架構。",
    "Savings Plan": "以每小時固定用量承諾換取符合範圍compute usage折扣；要追蹤coverage與utilization。",
    "Spot": "使用AWS剩餘EC2容量的折扣模式，可能收到短通知後被中斷，適合可重試、可分散或checkpoint workloads。",
    "tagging": "為resources加上key/value metadata，以支援ownership、cost allocation、automation與ABAC；taxonomy與enforcement比Name tag更重要。",
    "showback": "把共享與直接成本顯示給使用團隊但不實際轉帳，先建立成本可見性與行為回饋。",
    "chargeback": "把資源與共享平台成本實際分攤到business/team budget，需要穩定accounts、tags與allocation rules。",
    "Cost and Usage Report": "AWS提供細粒度billing line items與resource IDs的資料集，可輸出到S3供Athena/BI做自訂分析。",
    "unit economics": "以每成功交易、每tenant、每GB或其他business unit計算成本，比只看單一instance月費更能比較架構。",
    "migration": "把workload從目前環境移到目標環境並完成驗證、cutover、rollback與舊環境退役，不等於server已成功開機。",
    "portfolio": "待評估的一組applications、servers、databases、owners、成本與business criticality，用來做migration/modernization排序。",
    "migration wave": "在共同時間窗內一起assessment、replication、test與cutover的一組workloads；通常依dependency與business calendar分組。",
    "dependency graph": "以nodes/edges表示application、database、network、identity與外部系統的依賴，幫助避免把強耦合元件拆到不同waves。",
    "discovery": "透過agent、hypervisor/CMDB資料與owner訪談蒐集inventory、utilization及network connections；資料需要交叉驗證。",
    "rehost": "盡量不改application，把server搬到cloud IaaS；速度快但保留多數技術債與營運模式。",
    "replatform": "搬移時替換部分platform，例如改用managed database/container，但不重寫主要business architecture。",
    "refactor": "重構application與data boundaries以使用cloud-native架構；潛在收益高，時間、風險與testing需求也最高。",
    "retain": "因法規、dependency、時程或business理由暫時保留原環境，並記錄重新評估日期。",
    "retire": "確認沒有business value或consumer後安全下線workload，通常是最快的成本與風險消除方式。",
    "modernization": "為可維護性、可靠性、交付速度或成本改善application/platform；應由可量測outcome驅動，而非因服務較新。",
    "technical debt": "過去為速度或限制做出的設計選擇，現在增加變更成本、故障風險或認知負擔。",
}


def chapter_glossary(
    topic: Topic, components: tuple[tuple[str, ComponentProfile], ...]
) -> tuple[tuple[str, str], ...]:
    text = " ".join(
        (
            topic.title,
            topic.problem,
            topic.decision,
            topic.alternative,
            topic.failure,
            topic.scenario,
            *(value for pair in components for value in (pair[0], *pair[1].__dict__.values())),
        )
    ).lower()
    matched = [
        (term, definition)
        for term, definition in CONCEPT_GLOSSARY.items()
        if term.lower() in text
    ]
    # Longer phrases first so "DNS resolution" is taught before the shorter "DNS".
    matched.sort(key=lambda item: (-len(item[0]), item[0].lower()))
    return tuple(matched)
