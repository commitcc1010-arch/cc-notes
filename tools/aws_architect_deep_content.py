"""Substantive teaching layers for the AWS Solutions Architect handbook."""
from __future__ import annotations

from dataclasses import dataclass

from aws_architect_model import TASKS, Topic
from aws_architect_profiles import ComponentProfile, component_profile
from aws_architect_question_bank import questions_for_chapter


@dataclass(frozen=True)
class ConfigExample:
    title: str
    language: str
    code: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class PracticeQuestion:
    level: str
    tested: str
    prompt: str
    choices: tuple[str, ...]
    answers: tuple[int, ...]
    explanations: tuple[str, ...]
    question_id: str = ""
    kind: str = "single"
    intent: int = 0
    task_keys: tuple[str, ...] = ()
    sources: tuple[tuple[str, str, str], ...] = ()
    inspirations: tuple[tuple[str, str, str], ...] = ()
    author_agent: str = ""


def components(topic: Topic) -> tuple[tuple[str, ComponentProfile], ...]:
    return tuple((name, component_profile(name, topic)) for name in topic.services)


def key_takeaways(topic: Topic) -> tuple[str, ...]:
    rows = components(topic)
    primary_name, primary = rows[0]
    peer_name, peer = rows[1] if len(rows) > 1 else ("相鄰方案", primary)
    return (
        f"{primary_name}的責任：{primary.purpose}",
        f"底層機制：{primary.mechanism}",
        f"第一個要看的設定：{primary.config}",
        f"選擇邏輯：{topic.decision}",
        f"不要混淆：{peer_name}的責任是「{peer.purpose}」；它不會自動取代{primary_name}。",
        f"替換訊號：{primary.replace}",
        f"最常見錯法：{topic.failure}",
        f"可移植原則：{topic.pattern}。",
    )


def component_narrative(topic: Topic) -> tuple[tuple[str, str], ...]:
    """Explain chapter components as actors in one system rather than cards."""

    rows = components(topic)
    primary_name, primary = rows[0]
    style = (topic.number - 1) % 4
    primary_intros = (
        f"回到剛才的故事，團隊需要有人負責「{primary.purpose}」這件事。"
        f"{primary_name}之所以出現在圖上，不是為了增加一個方框，而是把這段容易重複實作的責任集中起來。",
        f"先問一個很實際的問題：如果不用{primary_name}，誰來完成「{primary.purpose}」？"
        "答案可能是每個application各寫一套，或由平台團隊自己維護同樣的基礎能力；這正是它要接手的麻煩。",
        f"把{primary_name}看成故事中的一個角色，而不是考試單字。它的工作是：{primary.purpose} "
        "只要這份工作確實存在，服務才有被選進來的理由；否則再多features也只是噪音。",
        f"現在把鏡頭停在{primary_name}。前一站交給它一份請求、資料或設定，而它承諾完成「{primary.purpose}」。"
        "這個承諾就是本章選型時真正要比較的責任邊界。",
    )
    mechanism_bridges = (
        f"實際收到工作後，{primary.mechanism} 可以把這句話拆成三步：誰把輸入交進來、"
        "服務根據什麼資料做決定、最後把結果或狀態交給誰。",
        f"再往裡面看一層：{primary.mechanism} 閱讀這段時先不要背名詞，試著畫出輸入、"
        "服務內部的關鍵判斷，以及外部真正能觀察到的結果。",
        f"它不是黑盒子。{primary.mechanism} 這段運作方式告訴我們，control setting最後會如何"
        "改變真正的request或data path，也說明為什麼資源建立成功仍可能無法服務。",
        f"沿著一次正常流程走，{primary.mechanism} 如果能用自己的話重述這條路徑，"
        "你就已掌握核心；設定名稱只是把同一理解映射到AWS console或IaC。",
    )
    sections = [
        (
            f"先認識主角：{primary_name}替系統接下哪件麻煩事？",
            primary_intros[style] + "\n\n" + mechanism_bridges[style],
        )
    ]
    for index, (name, profile) in enumerate(rows[1:], 1):
        connector = (
            ("接著輪到", "下一個出場的是", "故事走到這裡，還需要", "另一個常被放在旁邊比較的角色是")
            [(topic.number + index) % 4]
        )
        relationship = (
            f"它並不是{primary_name}的升級版，而是接手另一段工作。",
            f"把它和{primary_name}放在一起，是為了補足或替換不同責任，不是比較誰的功能比較多。",
            f"兩個服務可能一起出現在架構裡，也可能互為選項；關鍵仍是目前缺的是哪一段能力。",
            f"請把兩者畫成有清楚箭頭的角色：{primary_name}完成自己的承諾，{name}只處理它明確擁有的部分。",
        )[(topic.number + index) % 4]
        sections.append(
            (
                f"{name}何時進場？",
                f"{connector}{name}。它負責的是：{profile.purpose} "
                f"真正有流量或資料通過時，{profile.mechanism}\n\n"
                f"{relationship} 當題目或production出現「{profile.choose}」時，它才有明確理由進場；"
                f"若需求變成「{profile.replace}」，就應該停下來重新分工，而不是繼續堆參數。",
            )
        )
    endings = (
        (
            "把選擇反過來問，理解才算完整",
            f"本章的相鄰方案是「{topic.alternative}」。它不是故意設計的錯答案，而是在另一組需求下"
            f"可能更好的做法。真正的分界，是主要方案能否直接處理「{topic.problem}」。\n\n"
            f"最後用失敗來驗證理解：{topic.failure} 如果你無法指出它會在哪一層發生、會看到什麼症狀，"
            "以及哪個元件負責恢復，就表示目前只記住了名稱，還沒有理解架構。",
        ),
        (
            "現在故意替另一個答案辯護",
            f"試著說服自己採用「{topic.alternative}」。你會發現它並非完全不可行，只是優化了另一組條件。"
            f"回到目前場景，「{topic.problem}」才是不能被犧牲的部分。\n\n"
            f"再用反例檢查：{topic.failure} 能解釋這個錯誤為何發生、如何被看見及怎麼恢復，"
            "才代表你真的懂得兩個方案的邊界。",
        ),
        (
            "服務名稱拿掉後，答案還站得住嗎？",
            f"把所有AWS名稱遮住，只留下「{topic.problem}」與「{topic.alternative}」。"
            "你仍應能從資料語意、失敗邊界與營運責任判斷哪個方向合適，而不是靠品牌猜答案。\n\n"
            f"最好的驗收題是：{topic.failure} 請指出第一個壞掉的狀態、使用者症狀與恢復owner。",
        ),
        (
            "最後看一次答案翻轉點",
            f"目前我們選擇主要方案，是因為它直接回應「{topic.problem}」。"
            f"一旦場景改成「{topic.alternative}」，角色與資料流就可能重排，答案也應該跟著改。\n\n"
            f"如果仍拿不準，就從「{topic.failure}」倒著追：哪個設計最能避免或限制這個結果，"
            "通常就是更符合本題的選擇。",
        ),
    )
    sections.append(endings[style])
    return tuple(sections)


def mechanism_walkthrough(topic: Topic) -> tuple[str, ...]:
    rows = components(topic)
    primary_name, primary = rows[0]
    supporting = "、".join(name for name, _ in rows[1:]) or "後續元件"
    return (
        f"故事的起點：{topic.scenario} 先寫下使用者真正等待的結果，不要先寫服務名稱。",
        f"第一個交接：{primary_name}負責「{primary.purpose}」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。",
        f"系統真正做事時：{primary.mechanism} 沿著這條路徑標出一次request、packet、message或data write。",
        f"其他角色接手：{supporting}各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。",
        f"故障時倒著追：主動重現「{topic.failure}」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。",
        f"需求改變時重選：一旦出現「{primary.replace}」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。",
        "最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。",
    )


def comparison_rows(topic: Topic) -> tuple[tuple[str, str, str, str, str], ...]:
    rows = []
    for name, profile in components(topic):
        rows.append((name, profile.purpose, profile.mechanism, profile.choose, profile.replace))
    rows.append(
        (
            "本章反例",
            "看似可以工作，但沒有滿足題目真正的hard constraint。",
            topic.alternative,
            "只有當題目條件明確改變時才可能合理。",
            topic.failure,
        )
    )
    return tuple(rows)


def scope_guide(topic: Topic) -> tuple[tuple[str, tuple[str, ...]], ...]:
    saa = tuple(task for task in topic.tasks if task.startswith("SAA"))
    sap = tuple(task for task in topic.tasks if task.startswith("SAP"))
    primary = component_profile(topic.services[0], topic)
    saa_rows = (
        "能用一句話說出服務功能、scope與managed responsibility。",
        f"能根據單一workload限制，在主要方案與「{topic.alternative}」之間做選擇。",
        f"認得常考設定：{primary.config}",
        f"對應官方tasks：{'；'.join(f'{task} {TASKS[task]}' for task in saa) if saa else '此章主要是SAP延伸背景'}。",
    )
    sap_rows = (
        "把單服務答案擴成跨帳號、跨Region、migration與operating model。",
        "明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。",
        f"知道何時要替換或組合：{primary.replace}",
        f"對應官方tasks：{'；'.join(f'{task} {TASKS[task]}' for task in sap) if sap else '此章以SAA核心能力為主'}。",
    )
    return (("SAA 必會", saa_rows), ("SAP 加深", sap_rows))


def special_explanation(topic: Topic) -> tuple[tuple[str, str], ...]:
    if topic.number == 15:
        return (
            (
                "先把 routing 與 DNS 拆成兩條獨立路徑",
                "Routing回答「已知目的IP後，封包下一跳去哪裡」；DNS resolution回答「hostname要翻成哪個IP」。"
                "VPC Peering變成active只建立一條可被route table引用的連線，仍要在雙方subnets加入peer CIDR routes，"
                "再設定security groups。若application用hostname，才另外考慮peering DNS resolution。"
                "因此DNS查得到但route不通會timeout；route通但DNS未設定則可能解析到public IP或根本找不到名稱。",
            ),
            (
                "Peering DNS resolution 到底改了什麼",
                "EC2 instance可能有public DNS hostname。預設從peer VPC查詢時，不一定得到可走peering的private address；"
                "在active peering上為requester與accepter各自啟用AllowDnsResolutionFromRemoteVpc後，"
                "跨peering查詢這類hostname可解析成peer private IPv4。兩個VPC仍需啟用DNS support/hostnames，"
                "而private hosted zone還有自己的VPC association或Resolver設計，不能把所有DNS問題都歸給這個開關。",
            ),
            (
                "何時從 Peering 換成 TGW 或 PrivateLink",
                "少量VPC、需要任意private-IP雙向互通且CIDR不重疊時，Peering最直接；但每對VPC都要連線與route，"
                "而且不transitive。VPC數量增加、需要hub routing、分段route domains或集中inspection時，Transit Gateway"
                "更容易治理。若consumer只該使用provider的一個service，尤其有CIDR重疊或SaaS cross-account需求，"
                "PrivateLink暴露endpoint service會比打通整個VPC更小權限。",
            ),
        )
    if topic.number == 17:
        return (
            (
                "CloudFront 的三段 request flow",
                "Viewer先以DNS到最近edge。Edge依cache behavior選origin與policies，再用cache key找副本；hit直接回應，"
                "miss才向origin request。這三段的policy不同：viewer protocol決定client如何進edge，cache policy決定哪些值"
                "切分cache objects，origin request policy決定哪些額外值只轉給origin。若把三者混在一起，最常出現"
                "cache hit ratio極低、不同使用者共用錯誤response，或origin收不到必要context。",
            ),
            (
                "Cache policy 與 origin request policy 為何不能互換",
                "會改變response內容的header/cookie/query必須進cache key，否則不同request可能拿到同一cached response；"
                "origin只需要拿來logging或authorization、但不應產生另一份cache object的值，可只放origin request policy。"
                "最安全的起點不是forward all，而是從AWS managed policies開始，再用實際response variance逐項加入。",
            ),
            (
                "Private S3 origin 與 OAC",
                "使用者只應讀CloudFront URL時，S3保持Block Public Access與Bucket owner enforced。OAC讓CloudFront service"
                "以SigV4簽署到S3 REST endpoint的request；bucket policy再以distribution SourceArn限制。"
                "OAC不是把bucket變public，也不適用S3 website endpoint。若origin仍可被直接打到，WAF、cache與signed URL"
                "等edge controls都可能被繞過。",
            ),
        )
    if topic.number == 18:
        return (
            (
                "ALB 的四層物件不要混在一起",
                "Load balancer是入口資源；listener綁定port/protocol；listener rules依priority與conditions選action；"
                "target group保存targets、health check與routing attributes。看到HTTPS 443、path routing、target health、"
                "stickiness時，要先判斷它分別屬於listener、rule還是target group，否則即使服務選對也會把參數設在錯的地方。",
            ),
            (
                "Stickiness 解決的是相容性，不是根治 state",
                "正常情況ALB可把每個request送到不同healthy target。若legacy app把session存在單機memory，stickiness用"
                "load-balancer或application cookie讓client暫時黏到同一target。但target仍可能失效或scale in，負載也可能不均。"
                "長期設計應把session放到ElastiCache、DynamoDB或其他shared state，讓web tier保持stateless。",
            ),
            (
                "ALB、NLB、GWLB 的答案翻轉點",
                "需要HTTP host/path/header routing、WAF或OIDC時選ALB；需要TCP/UDP/TLS、static IP、極高連線吞吐或"
                "PrivateLink provider時選NLB；要透明插入firewall/IDS appliance並以GENEVE保留flow資訊時選GWLB。"
                "『效能更快』不是單獨理由，真正差異是protocol semantics、target type與security/data-path責任。",
            ),
        )
    if topic.number == 21:
        return (
            (
                "先分清 authentication 與 authorization",
                "Authentication回答「你是誰」：例如員工透過Identity Center登入、EC2透過instance "
                "profile取得role credentials。Authorization回答「這個已驗證principal現在能做什麼」："
                "IAM會把action、resource、request context拿去比對所有applicable policies。只建立user或"
                "role不會自動有權限；只寫policy也必須附到正確identity或resource。",
            ),
            (
                "Role其實有兩道門",
                "Trust policy是第一道門，決定誰能呼叫sts:AssumeRole；permissions policy是第二道門，"
                "決定成功扮演後能呼叫哪些API。面試或考試看到cross-account時，必須同時檢查source principal"
                "是否可AssumeRole、target role是否信任它，以及session最後是否受SCP、boundary或session policy限制。",
            ),
            (
                "人與workload不要共用credential模型",
                "Workforce使用Identity Center/federation，取得短期role session；EC2、Lambda、ECS task使用"
                "service-integrated role；on-premises workload可用OIDC federation或IAM Roles Anywhere。"
                "長期access key只應是不得已的legacy例外，且必須有owner、rotation、monitoring與淘汰日期。",
            ),
        )
    if topic.number == 22:
        return (
            (
                "Policy不是由上到下執行的程式",
                "AWS會找出所有與request相關的statements。沒有Allow是implicit deny；只要任何一份applicable "
                "policy出現explicit Deny，結果立刻是Deny。Identity policy與同帳號resource policy常形成"
                "permission union，但boundary、session policy、SCP與RCP通常是限制上限，不能拿來授權。",
            ),
            (
                "Cross-account為何常需要兩邊都設定",
                "來源帳號要允許principal發出action，目標資源或role trust也要接受這個外部principal。"
                "例如Account A role讀Account B S3 bucket：A端identity policy允許s3:GetObject，B端bucket policy"
                "允許該role principal；任一側缺少或被explicit Deny覆蓋都會失敗。",
            ),
            (
                "除錯順序",
                "先確認caller identity與resource ARN，再查CloudTrail error context；接著依序檢查identity policy、"
                "resource policy、permissions boundary、session policy、SCP/RCP、VPC endpoint policy及"
                "service-specific policy（如KMS key policy）。Policy Simulator有幫助，但不能完全取代真實request。",
            ),
        )
    if topic.number == 41:
        return (
            (
                "S3不是網路磁碟",
                "S3以bucket + key識別object，透過HTTP API整個PUT/GET；prefix只是key字串的共同前綴。"
                "它沒有一般POSIX filesystem的append、rename directory與跨object transaction。若應用依賴"
                "file locking、in-place update或共享mount，應比較EFS、FSx或EBS，而不是勉強把S3當磁碟。",
            ),
            (
                "IAM policy與bucket policy何時選誰",
                "IAM identity policy附在user/group/role，適合描述「這個role可操作哪些AWS資源」，可跨多個服務"
                "集中管理。Bucket policy附在bucket，適合描述「誰可以碰這個bucket」、cross-account、CloudFront/"
                "AWS service delivery，以及用explicit Deny強制TLS、organization、VPC endpoint或encryption。"
                "同帳號簡單存取可能只需其中一個Allow；cross-account通常來源identity與目標resource兩側都要允許。",
            ),
            (
                "ARN最常寫錯的地方",
                "Bucket-level action如s3:ListBucket使用arn:aws:s3:::my-bucket；object-level action如"
                "s3:GetObject使用arn:aws:s3:::my-bucket/prefix/*。把ListBucket綁到/*，或GetObject只綁bucket ARN，"
                "都不會match。Condition的s3:prefix限制LIST看到的key範圍，不能取代object ARN的實際讀取限制。",
            ),
            (
                "四層public防線",
                "Modern S3先保持Object Ownership為Bucket owner enforced以停用ACL，再在account與bucket開啟"
                "四個Block Public Access flags，bucket policy只允許具名principal，最後用IAM Access Analyzer/"
                "Config持續找外部或public access。公開靜態網站通常用private bucket + CloudFront OAC，而非讓bucket public。",
            ),
        )
    # Generic prose here used to repeat the story, component profile and
    # decision table with different headings. Keep this layer only for chapters
    # that have a genuinely chapter-specific mechanism worth unpacking.
    return ()


SPECIAL_CONFIGS: dict[int, tuple[ConfigExample, ...]] = {
    11: (
        ConfigExample(
            "VPC 與跨 AZ private subnets（CloudFormation）",
            "yaml",
            """Resources:
  Vpc:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.20.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags: [{Key: Name, Value: prod}]
  AppSubnetA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.20.16.0/20
      MapPublicIpOnLaunch: false
  AppSubnetB:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      AvailabilityZone: !Select [1, !GetAZs ""]
      CidrBlock: 10.20.32.0/20
      MapPublicIpOnLaunch: false
""",
            (
                "/16是VPC總位址池；每個/20 subnet位於不同AZ，預留未來tiers與成長空間。",
                "MapPublicIpOnLaunch=false只避免自動public IPv4；private/public仍由route table是否指向IGW決定。",
                "Production還需route tables、egress、VPC endpoints、flow logs與non-overlap hybrid planning。",
            ),
        ),
    ),
    12: (
        ConfigExample(
            "Public、private app 與 isolated database 的 routes（CloudFormation 節錄）",
            "yaml",
            """Resources:
  InternetGateway:
    Type: AWS::EC2::InternetGateway

  AttachInternetGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref Vpc
      InternetGatewayId: !Ref InternetGateway

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc

  PublicDefaultRoute:
    Type: AWS::EC2::Route
    DependsOn: AttachInternetGateway
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnetA
      RouteTableId: !Ref PublicRouteTable

  NatEip:
    Type: AWS::EC2::EIP
    DependsOn: AttachInternetGateway
    Properties:
      Domain: vpc

  NatGatewayA:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatEip.AllocationId
      SubnetId: !Ref PublicSubnetA

  PrivateAppRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc

  PrivateAppDefaultRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateAppRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGatewayA

  AppSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref AppSubnetA
      RouteTableId: !Ref PrivateAppRouteTable

  DatabaseRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc

  DatabaseSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref DatabaseSubnetA
      RouteTableId: !Ref DatabaseRouteTable
""",
            (
                "每張route table建立時都會有VPC CIDR → local route；CloudFormation不需再宣告。Public table另外把0.0.0.0/0送到IGW，因此關聯它的subnet具備Internet路徑。",
                "NAT Gateway必須位於具有IGW default route的public subnet。Private app table把0.0.0.0/0送到NAT，讓只有private address的instance可以主動出站，但不接受Internet主動建立連線。",
                "Database table刻意沒有0.0.0.0/0。資料庫仍可和VPC內app通訊，因為local route存在；若同一isolated tier中的自管maintenance host需要存取AWS API，應明確加入VPC endpoint或受控出口，而不是把整層直接公開。",
                "Production應在每個AZ建立NAT與對應private route，避免跨AZ流量費與單一NAT/AZ故障。ALB是否公開還取決於internet-facing scheme、public subnet與security group，不是只有route table。",
            ),
        ),
    ),
    14: (
        ConfigExample(
            "ALB → App → Database 的 Security Group chaining",
            "yaml",
            """Resources:
  AlbSg:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Internet to ALB only
      VpcId: !Ref Vpc
      SecurityGroupIngress:
        - {IpProtocol: tcp, FromPort: 443, ToPort: 443, CidrIp: 0.0.0.0/0}
  AppSg:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: ALB to app only
      VpcId: !Ref Vpc
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8080
          ToPort: 8080
          SourceSecurityGroupId: !Ref AlbSg
  DbSg:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: App to PostgreSQL only
      VpcId: !Ref Vpc
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref AppSg
""",
            (
                "SG reference表達workload identity；app instance換IP時不必更新CIDR。",
                "SG是stateful：已允許connection的回程不需另開ephemeral port。",
                "Database不能以0.0.0.0/0開5432；若題目要求explicit deny或subnet boundary才比較NACL。",
            ),
        ),
    ),
    15: (
        ConfigExample(
            "VPC Peering：雙向 routes 與跨 peer Security Group",
            "yaml",
            """Resources:
  AppToDataPeering:
    Type: AWS::EC2::VPCPeeringConnection
    Properties:
      VpcId: !Ref AppVpc
      PeerVpcId: !Ref DataVpc
      PeerOwnerId: "444455556666"
  AppToDataRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref AppPrivateRouteTable
      DestinationCidrBlock: 10.40.0.0/16
      VpcPeeringConnectionId: !Ref AppToDataPeering
  DataToAppRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref DataPrivateRouteTable
      DestinationCidrBlock: 10.20.0.0/16
      VpcPeeringConnectionId: !Ref AppToDataPeering
  DatabaseIngress:
    Type: AWS::EC2::SecurityGroupIngress
    Properties:
      GroupId: !Ref DatabaseSecurityGroup
      IpProtocol: tcp
      FromPort: 5432
      ToPort: 5432
      SourceSecurityGroupId: sg-0123456789abcdef0
      SourceSecurityGroupOwnerId: "111122223333"
""",
            (
                "Peering resource只是連線；兩側route tables都要加入對方CIDR與pcx target，否則只會單向可達或完全timeout。",
                "同Region且支援的peering情境可用peer security group作source；它比固定instance IP更能表達workload identity。",
                "10.20.0.0/16與10.40.0.0/16必須不重疊。Peering不transitive，DataVpc不能因AppVpc另有連線便經它到第三個VPC。",
            ),
        ),
        ConfigExample(
            "VPC Peering DNS resolution：requester 與 accepter 各自啟用",
            "bash",
            """# Peering 必須已是 active。Requester owner 執行：
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id pcx-0123456789abcdef0 \
  --requester-peering-connection-options \
  AllowDnsResolutionFromRemoteVpc=true

# Accepter owner 在自己的 account/role context 執行：
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id pcx-0123456789abcdef0 \
  --accepter-peering-connection-options \
  AllowDnsResolutionFromRemoteVpc=true

# 從兩側 instance 驗證「名稱 → private IP」，再驗證 TCP path：
dig +short ec2-10-40-8-25.compute-1.amazonaws.com
nc -vz 10.40.8.25 5432
""",
            (
                "DNS resolution把hostname翻成private IPv4；它不會替你建立route、security group或database authorization。",
                "Requester與accepter options分開保存，跨帳號時由各owner使用自己的credentials設定。任一側未開，雙向名稱解析假設就可能不成立。",
                "先用dig驗證answer，再用nc/curl驗證transport。若dig成功而nc timeout，下一步查route table、SG/NACL與return path，而不是繼續改DNS。",
            ),
        ),
    ),
    16: (
        ConfigExample(
            "Route 53 weighted rollout records",
            "yaml",
            """Resources:
  StableRecord:
    Type: AWS::Route53::RecordSet
    Properties:
      HostedZoneId: !Ref HostedZone
      Name: api.example.com
      Type: A
      SetIdentifier: stable
      Weight: 95
      AliasTarget:
        DNSName: !GetAtt StableAlb.DNSName
        HostedZoneId: !GetAtt StableAlb.CanonicalHostedZoneID
  CanaryRecord:
    Type: AWS::Route53::RecordSet
    Properties:
      HostedZoneId: !Ref HostedZone
      Name: api.example.com
      Type: A
      SetIdentifier: canary
      Weight: 5
      AliasTarget:
        DNSName: !GetAtt CanaryAlb.DNSName
        HostedZoneId: !GetAtt CanaryAlb.CanonicalHostedZoneID
""",
            (
                "Weight是相對值，不保證每100個request精確95/5，因DNS resolver會cache。",
                "Alias可指向ALB且不需固定IP；真正failover還要health evaluation與rollback signal。",
                "需要request-level精確canary時用ALB/CodeDeploy/application routing，而非只靠DNS。",
            ),
        ),
    ),
    17: (
        ConfigExample(
            "CloudFront：Cache Policy、OAC 與 private S3 origin",
            "yaml",
            """Resources:
  StaticCachePolicy:
    Type: AWS::CloudFront::CachePolicy
    Properties:
      CachePolicyConfig:
        Name: static-by-language-and-version
        DefaultTTL: 3600
        MinTTL: 0
        MaxTTL: 86400
        ParametersInCacheKeyAndForwardedToOrigin:
          EnableAcceptEncodingBrotli: true
          EnableAcceptEncodingGzip: true
          CookiesConfig: {CookieBehavior: none}
          HeadersConfig:
            HeaderBehavior: whitelist
            Headers: [Accept-Language]
          QueryStringsConfig:
            QueryStringBehavior: whitelist
            QueryStrings: [version]
  S3OriginAccessControl:
    Type: AWS::CloudFront::OriginAccessControl
    Properties:
      OriginAccessControlConfig:
        Name: private-assets-oac
        OriginAccessControlOriginType: s3
        SigningBehavior: always
        SigningProtocol: sigv4
  Distribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        Origins:
          - Id: private-s3
            DomainName: !GetAtt AssetsBucket.RegionalDomainName
            OriginAccessControlId: !Ref S3OriginAccessControl
            S3OriginConfig: {}
        DefaultCacheBehavior:
          TargetOriginId: private-s3
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: !Ref StaticCachePolicy
""",
            (
                "Accept-Language與version會改變cache key；只有真的改變response的值才應加入，否則每種組合都建立新cache object。",
                "OAC以SigV4簽到S3 REST origin。Bucket仍需policy允許cloudfront.amazonaws.com並以distribution SourceArn限制。",
                "DefaultTTL是一小時，但origin Cache-Control與Min/MaxTTL仍會共同決定freshness；敏感dynamic response不應套用此static policy。",
            ),
        ),
        ConfigExample(
            "S3 bucket policy：只允許指定 CloudFront distribution",
            "json",
            """{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontOACReadOnly",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::acme-private-assets/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/E123ABC456"
      }
    }
  }]
}""",
            (
                "Principal是CloudFront service，不是anonymous *；SourceArn把權限縮到單一distribution。",
                "Resource使用object ARN的/*，因GetObject是object-level action。Bucket保持四個Block Public Access flags開啟。",
                "如果改用S3 website endpoint，OAC不適用；website endpoint屬custom origin且通常需要公開讀取，安全模型不同。",
            ),
        ),
    ),
    18: (
        ConfigExample(
            "ALB：listener、health check、stickiness、idle timeout 與 access logs",
            "yaml",
            """Resources:
  WebTargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      VpcId: !Ref Vpc
      Protocol: HTTP
      Port: 8080
      TargetType: ip
      HealthCheckPath: /ready
      HealthCheckIntervalSeconds: 15
      HealthCheckTimeoutSeconds: 5
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3
      Matcher: {HttpCode: "200-299"}
      TargetGroupAttributes:
        - {Key: stickiness.enabled, Value: "true"}
        - {Key: stickiness.type, Value: lb_cookie}
        - {Key: stickiness.lb_cookie.duration_seconds, Value: "300"}
        - {Key: deregistration_delay.timeout_seconds, Value: "30"}
  PublicAlb:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Scheme: internet-facing
      Subnets: [!Ref PublicSubnetA, !Ref PublicSubnetB]
      SecurityGroups: [!Ref AlbSecurityGroup]
      LoadBalancerAttributes:
        - {Key: idle_timeout.timeout_seconds, Value: "90"}
        - {Key: access_logs.s3.enabled, Value: "true"}
        - {Key: access_logs.s3.bucket, Value: !Ref AccessLogBucket}
  HttpsListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref PublicAlb
      Port: 443
      Protocol: HTTPS
      Certificates: [{CertificateArn: !Ref CertificateArn}]
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref WebTargetGroup
""",
            (
                "TargetType=ip適合ECS awsvpc/Fargate tasks；傳統EC2也可依需求選instance。建立後要換target type通常需新target group。",
                "stickiness以ALB cookie維持五分鐘affinity，只是legacy session過渡方案；target失效時仍會換target，長期應外移session state。",
                "/ready應快速反映能否接流量；idle timeout要與client/application timeout協調。Access logs另需S3 delivery policy與retention。",
            ),
        ),
        ConfigExample(
            "ALB listener rule：host/path routing 與 priority",
            "yaml",
            """Resources:
  ApiRule:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      ListenerArn: !Ref HttpsListener
      Priority: 10
      Conditions:
        - Field: host-header
          HostHeaderConfig: {Values: [api.example.com]}
        - Field: path-pattern
          PathPatternConfig: {Values: [/v1/*]}
      Actions:
        - Type: forward
          TargetGroupArn: !Ref ApiTargetGroup
""",
            (
                "Priority數字越小越早評估，第一個matching rule生效；它不是流量權重。",
                "Host與path conditions在同一rule中共同成立才match；未命中則繼續其他rules，最後走listener default action。",
                "若要weighted canary，可在同一forward action中配置多個target groups與weights，並以alarm/rollback控制，而不是改rule priority。",
            ),
        ),
    ),
    21: (
        ConfigExample(
            "EC2 workload role：誰可以 AssumeRole（trust policy）",
            "json",
            """{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}""",
            (
                "Principal是EC2 service，表示只有EC2 service principal可取得這個role session。",
                "Trust policy不包含s3:GetObject；它只控制誰能扮演role。",
                "EC2還需instance profile把role掛到instance，application再從metadata endpoint取得temporary credentials。",
            ),
        ),
        ConfigExample(
            "扮演後可以做什麼（permissions policy）",
            "json",
            """{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadOnlyApplicationPrefix",
    "Effect": "Allow",
    "Action": ["s3:GetObject"],
    "Resource": "arn:aws:s3:::acme-prod-artifacts/app/*"
  }]
}""",
            (
                "Identity policy省略Principal，因為principal就是附加此policy的role。",
                "GetObject是object-level action，所以Resource必須包含/app/*，不能只寫bucket ARN。",
                "沒有ListBucket仍可讀已知object key；若app需要列舉，再另加bucket ARN與s3:prefix condition。",
            ),
        ),
    ),
    22: (
        ConfigExample(
            "Permissions boundary：允許開發role，但禁止IAM與Organizations",
            "json",
            """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "NotAction": ["iam:*", "organizations:*", "account:*"],
      "Resource": "*"
    }
  ]
}""",
            (
                "Boundary本身不授權；role仍需要identity policy Allow。",
                "若identity policy給AdministratorAccess，effective permissions仍只能落在boundary Allow範圍。",
                "Production還要防止建立者移除/替換boundary，通常用iam:PermissionsBoundary condition與SCP。",
            ),
        ),
        ConfigExample(
            "把 boundary 實際附到 delegated role（CloudFormation）",
            "yaml",
            """Resources:
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
""",
            (
                "PermissionsBoundary欄位把managed policy ARN附到role；它限制之後附加的identity policies可以產生的最大權限。",
                "Trust policy只允許PlatformPipeline取得session，並沒有授予部署actions；role仍需另外附上精確permissions policy。",
                "委派建立role時還要以iam:PermissionsBoundary condition強制使用核准boundary，並拒絕未授權的移除或替換。",
            ),
        ),
    ),
    23: (
        ConfigExample(
            "Third-party cross-account role trust policy",
            "json",
            """{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::444455556666:role/VendorWorker"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"sts:ExternalId": "customer-8f3a91"}
    }
  }]
}""",
            (
                "Principal限制到vendor具名role，不要直接信任整個外部account root後再期待對方自律。",
                "ExternalId由服務供應商提供給每個customer，降低confused-deputy風險；它不是密碼。",
                "permissions policy仍需限制vendor session實際可讀的resource與actions。",
            ),
        ),
    ),
    25: (
        ConfigExample(
            "SCP：禁止關閉組織 audit trail",
            "json",
            """{
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
}""",
            (
                "SCP只設最大權限；即使沒有這份Deny，也不會自動授權任何人操作CloudTrail。",
                "先在sandbox OU驗證，再漸進套用；直接掛organization root可能阻斷break-glass與automation。",
                "SCP不影響management account，因此management account不應承載一般workload。",
            ),
        ),
    ),
    27: (
        ConfigExample(
            "KMS key policy：允許application role使用key",
            "json",
            """{
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
}""",
            (
                "KMS key policy是key的resource policy；IAM Allow不一定足夠，key policy也必須建立授權路徑。",
                "kms:ViaService把key usage限制在透過指定Region S3，減少role直接任意Decrypt。",
                "Resource在KMS key policy通常是*，代表這一把key；不要誤解為帳號所有keys。",
            ),
        ),
    ),
    28: (
        ConfigExample(
            "Secrets Manager secret 與 rotation（CloudFormation）",
            "yaml",
            """Resources:
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
""",
            (
                "Secret使用KMS加密並跨Region replica；讀取role仍需secretsmanager:GetSecretValue與kms:Decrypt。",
                "Rotation Lambda必須能network連到database，並完成create/test/finish等rotation steps。",
                "Application要cache secret且在auth failure後重新讀取，避免每request讀取與rotation後長期用舊connection。",
            ),
        ),
    ),
    41: (
        ConfigExample(
            "Bucket policy：TLS、prefix 與 cross-account role",
            "json",
            """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::acme-data",
        "arn:aws:s3:::acme-data/*"
      ],
      "Condition": {"Bool": {"aws:SecureTransport": "false"}}
    },
    {
      "Sid": "AllowAnalyticsRoleToListRawPrefix",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::444455556666:role/AnalyticsReader"
      },
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::acme-data",
      "Condition": {"StringLike": {"s3:prefix": ["raw/*"]}}
    },
    {
      "Sid": "AllowAnalyticsRoleToReadRawObjects",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::444455556666:role/AnalyticsReader"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::acme-data/raw/*"
    }
  ]
}""",
            (
                "第一段是explicit Deny，因此即使其他identity policy允許，也不能用HTTP明文存取。",
                "ListBucket操作bucket本身，Resource沒有/*；s3:prefix只限制LIST結果。",
                "GetObject操作objects，Resource必須是raw/*；cross-account role在來源帳號通常也要有identity Allow。",
                "Principal只出現在resource policy；若這段改成附在AnalyticsReader的IAM policy，就移除Principal。",
            ),
        ),
        ConfigExample(
            "Bucket安全基線：停用ACL、封鎖public、SSE-KMS",
            "yaml",
            """Resources:
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: acme-data
      OwnershipControls:
        Rules:
          - ObjectOwnership: BucketOwnerEnforced
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        IgnorePublicAcls: true
        BlockPublicPolicy: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - BucketKeyEnabled: true
            ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyID: !GetAtt DataKey.Arn
      VersioningConfiguration:
        Status: Enabled
""",
            (
                "BucketOwnerEnforced停用ACL並讓bucket owner擁有所有objects，是modern default。",
                "四個public access flags處理的風險不同，考試常用「Block all public access」概括。",
                "BucketKeyEnabled可減少SSE-KMS對KMS requests與成本；KMS key policy仍要允許S3與讀寫roles。",
                "Versioning保留舊version但不是完整backup；刪除、replication與retention仍需額外設計。",
            ),
        ),
        ConfigExample(
            "同一需求若改用 IAM identity policy",
            "json",
            """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::acme-data",
      "Condition": {"StringLike": {"s3:prefix": ["raw/*"]}}
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::acme-data/raw/*"
    }
  ]
}""",
            (
                "這份policy附到role，因此沒有Principal欄位。",
                "若role與bucket同帳號且bucket沒有explicit Deny，這個identity Allow通常可完成授權。",
                "若bucket在另一帳號，target bucket policy仍需允許該role；這就是cross-account兩側授權。",
            ),
        ),
    ),
    42: (
        ConfigExample(
            "S3 Lifecycle：30天轉IA、180天轉Deep Archive、清理舊version",
            "json",
            """{
  "Rules": [{
    "ID": "archive-audit-logs",
    "Status": "Enabled",
    "Filter": {"Prefix": "audit/"},
    "Transitions": [
      {"Days": 30, "StorageClass": "STANDARD_IA"},
      {"Days": 180, "StorageClass": "DEEP_ARCHIVE"}
    ],
    "NoncurrentVersionTransitions": [
      {"NoncurrentDays": 30, "StorageClass": "GLACIER_IR"}
    ],
    "NoncurrentVersionExpiration": {"NoncurrentDays": 2555},
    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
  }]
}""",
            (
                "Transitions只應在存取頻率與取回時間符合時使用；還要計入minimum duration與retrieval費。",
                "Noncurrent rules與current object rules不同，versioning bucket若不清理會持續累積成本。",
                "AbortIncompleteMultipartUpload避免失敗parts永久計費。",
            ),
        ),
    ),
    45: (
        ConfigExample(
            "RDS PostgreSQL：Multi-AZ、backup 與保護刪除",
            "yaml",
            """Resources:
  OrdersDb:
    Type: AWS::RDS::DBInstance
    DeletionPolicy: Snapshot
    UpdateReplacePolicy: Snapshot
    Properties:
      Engine: postgres
      DBInstanceClass: db.r7g.large
      AllocatedStorage: 100
      StorageType: gp3
      MultiAZ: true
      BackupRetentionPeriod: 14
      StorageEncrypted: true
      KmsKeyId: !Ref DatabaseKey
      DeletionProtection: true
      PubliclyAccessible: false
      DBSubnetGroupName: !Ref DbSubnetGroup
      VPCSecurityGroups: [!Ref DbSecurityGroup]
""",
            (
                "MultiAZ解決availability，不提供application read scaling。",
                "DeletionPolicy與UpdateReplacePolicy保護IaC刪除/替換；DeletionProtection防API誤刪。",
                "Backup retention支援point-in-time recovery，但仍須實際restore並量測RTO。",
            ),
        ),
    ),
    47: (
        ConfigExample(
            "DynamoDB table：均勻partition key、GSI、PITR與TTL",
            "yaml",
            """Resources:
  EventsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - {AttributeName: tenant_id, AttributeType: S}
        - {AttributeName: event_time, AttributeType: S}
        - {AttributeName: status, AttributeType: S}
      KeySchema:
        - {AttributeName: tenant_id, KeyType: HASH}
        - {AttributeName: event_time, KeyType: RANGE}
      GlobalSecondaryIndexes:
        - IndexName: by_status
          KeySchema:
            - {AttributeName: status, KeyType: HASH}
            - {AttributeName: event_time, KeyType: RANGE}
          Projection: {ProjectionType: ALL}
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true
      TimeToLiveSpecification:
        AttributeName: expires_at
        Enabled: true
""",
            (
                "tenant_id若有單一超大型tenant仍可能hot；partition key設計要看實際traffic distribution。",
                "GSI是非同步維護的另一個access path；不要假設可做strongly consistent read。",
                "TTL刪除是非同步且不消耗table write capacity，不應用於精準到秒的排程。",
            ),
        ),
    ),
    52: (
        ConfigExample(
            "SQS queue、DLQ 與 redrive policy",
            "yaml",
            """Resources:
  WorkerDlq:
    Type: AWS::SQS::Queue
    Properties:
      MessageRetentionPeriod: 1209600
      KmsMasterKeyId: alias/aws/sqs
  WorkerQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 360
      ReceiveMessageWaitTimeSeconds: 20
      MessageRetentionPeriod: 345600
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt WorkerDlq.Arn
        maxReceiveCount: 5
      KmsMasterKeyId: alias/aws/sqs
""",
            (
                "VisibilityTimeout應大於一般處理時間並可heartbeat延長；太短會造成同一工作並行重複。",
                "Long polling 20秒降低empty receives與成本。",
                "DLQ retention通常要比source queue長，且必須有ApproximateNumberOfMessagesVisible alarm與redrive runbook。",
            ),
        ),
    ),
    53: (
        ConfigExample(
            "EventBridge rule：只路由已付款訂單",
            "json",
            """{
  "Source": ["com.acme.orders"],
  "DetailType": ["OrderStatusChanged"],
  "Detail": {
    "status": ["PAID"],
    "total": [{"numeric": [">", 0]}]
  }
}""",
            (
                "Event pattern是content-based filter；producer只發布fact，不需知道所有consumers。",
                "Target若需要buffer與retry isolation，通常把rule送到每個consumer自己的SQS queue。",
                "不要把EventBridge當長期high-throughput ordered log；需要replay/partition ordering時比較Kinesis/MSK。",
            ),
        ),
    ),
    55: (
        ConfigExample(
            "Step Functions：重試、Catch 與人工 callback",
            "json",
            """{
  "StartAt": "ChargePayment",
  "States": {
    "ChargePayment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "TimeoutSeconds": 20,
      "Retry": [{
        "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
        "IntervalSeconds": 2,
        "BackoffRate": 2,
        "MaxAttempts": 4
      }],
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "CancelOrder"
      }],
      "Next": "WaitForApproval"
    },
    "WaitForApproval": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke.waitForTaskToken",
      "HeartbeatSeconds": 3600,
      "Next": "CompleteOrder"
    },
    "CancelOrder": {"Type": "Task", "Resource": "COMPENSATION_TASK", "End": true},
    "CompleteOrder": {"Type": "Succeed"}
  }
}""",
            (
                "只重試可恢復的service/throttle errors；payment Lambda本身仍需idempotency key。",
                "Catch把技術錯誤轉入business compensation，不等於rollback分散式transaction。",
                "waitForTaskToken可等待外部/人工callback，不需Lambda持續執行或sleep。",
            ),
        ),
    ),
    66: (
        ConfigExample(
            "CloudWatch p99 latency alarm",
            "yaml",
            """Resources:
  ApiLatencyAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      Namespace: AWS/ApplicationELB
      MetricName: TargetResponseTime
      ExtendedStatistic: p99
      Dimensions:
        - Name: LoadBalancer
          Value: !GetAtt ApiAlb.LoadBalancerFullName
      Period: 60
      EvaluationPeriods: 5
      DatapointsToAlarm: 3
      Threshold: 0.8
      ComparisonOperator: GreaterThanThreshold
      TreatMissingData: notBreaching
      AlarmActions: [!Ref OnCallTopic]
""",
            (
                "3-of-5避免單點noise，仍能在持續p99惡化時告警。",
                "TreatMissingData必須依metric語意設定；沒有request時notBreaching合理，但heartbeat metric可能應breaching。",
                "Resource latency alarm要與business success/error-rate alarm並列，否則快速失敗可能看似低延遲。",
            ),
        ),
    ),
    72: (
        ConfigExample(
            "CloudFormation安全更新：保留database並輸出endpoint",
            "yaml",
            """Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, stage, prod]
Resources:
  Database:
    Type: AWS::RDS::DBCluster
    DeletionPolicy: Snapshot
    UpdateReplacePolicy: Snapshot
    Properties:
      Engine: aurora-postgresql
      StorageEncrypted: true
      DeletionProtection: !Equals [!Ref Environment, prod]
Outputs:
  WriterEndpoint:
    Value: !GetAtt Database.Endpoint.Address
    Export:
      Name: !Sub "${Environment}-orders-db-writer"
""",
            (
                "Parameters與AllowedValues建立有限輸入，不要讓production template接受任意字串。",
                "DeletionPolicy/UpdateReplacePolicy處理刪除與replacement；仍需backup/restore test。",
                "部署前建立change set，特別檢查Replacement=True與IAM capability。",
            ),
        ),
    ),
    79: (
        ConfigExample(
            "Landing zone account manifest",
            "yaml",
            """account:
  name: payments-prod
  email: aws+payments-prod@example.com
  ou: /Workloads/Prod
  owners:
    business: payments
    technical: payments-platform
  baseline:
    identity: IAMIdentityCenter
    organization_trail: required
    config_recorder: required
    guardduty: delegated-admin
    backup_vault_account: security-backup
  network:
    segment: prod
    egress: centralized
  tags:
    cost-center: CC-1042
    data-classification: restricted
""",
            (
                "Account是security、quota、billing與blast-radius boundary，不只是資料夾。",
                "OU決定繼承的SCP/controls；不要按公司org chart盲目設計，而要按policy與lifecycle相似度。",
                "Owner、cost center、data classification與network segment必須在供應時建立，不能事後靠人工補。",
            ),
        ),
    ),
    91: (
        ConfigExample(
            "Bedrock inference role：只允許指定model與Region",
            "json",
            """{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel"],
    "Resource": [
      "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0"
    ],
    "Condition": {
      "StringEquals": {"aws:RequestedRegion": "us-east-1"}
    }
  }]
}""",
            (
                "不要給bedrock:*與Resource *作為永久production policy；model與Region也是cost/data boundary。",
                "應用仍需輸入/輸出logging、guardrail、token limits、timeouts與fallback。",
                "若使用cross-Region inference profile，Resource與Region policy要依官方ARN模型重新設計。",
            ),
        ),
    ),
    93: (
        ConfigExample(
            "Guardrail policy worksheet",
            "yaml",
            """guardrail:
  version: 1
  denied_topics:
    - "提供個人醫療診斷"
  content_filters:
    hate: HIGH
    violence: MEDIUM
    sexual: HIGH
  sensitive_information:
    pii:
      - EMAIL
      - PHONE
      - US_SOCIAL_SECURITY_NUMBER
    action: ANONYMIZE
  contextual_grounding:
    grounding_threshold: 0.75
    relevance_threshold: 0.65
  response_on_block: "此請求無法依目前政策處理。"
""",
            (
                "Threshold要由代表性eval dataset校準，不能直接把HIGH當成零風險。",
                "Guardrail處理內容政策；IAM、VPC、KMS、data retention與tool authorization仍需分開控制。",
                "版本化guardrail並做canary，因為過嚴會降低helpfulness，過鬆會增加安全風險。",
            ),
        ),
    ),
}


def config_examples(topic: Topic) -> tuple[ConfigExample, ...]:
    """Return only real service configuration examples.

    A conceptual chapter does not become more practical by displaying a generic
    author checklist as YAML. Chapters without a useful deployable artifact rely
    on their worked scenario, setting manual and lab instead.
    """

    return SPECIAL_CONFIGS.get(topic.number, ())


def _rotate_questions(
    questions: tuple[PracticeQuestion, ...], seed: int
) -> tuple[PracticeQuestion, ...]:
    rotated: list[PracticeQuestion] = []
    for index, question in enumerate(questions):
        size = len(question.choices)
        amount = seed % size if index == 4 else (seed % 4 + index) % size
        order = list(range(amount, size)) + list(range(amount))
        inverse = {old: new for new, old in enumerate(order)}
        rotated.append(
            PracticeQuestion(
                question.level,
                question.tested,
                question.prompt,
                tuple(question.choices[item] for item in order),
                tuple(sorted(inverse[item] for item in question.answers)),
                tuple(question.explanations[item] for item in order),
            )
        )
    return tuple(rotated)


def _calibrate_questions(
    topic: Topic, questions: tuple[PracticeQuestion, ...]
) -> tuple[PracticeQuestion, ...]:
    """Add unique chapter context and keep every option analysis substantive."""

    calibrated: list[PracticeQuestion] = []
    decision = topic.decision.rstrip("。；;")
    failure = topic.failure.rstrip("。；;")
    for index, question in enumerate(questions, 1):
        explanations = []
        for explanation in question.explanations:
            if len(explanation) < 90:
                explanation += (
                    f" 判斷時要回到第{topic.number}章的責任邊界：{decision}；"
                    f"若忽略它，最可能留下的失效模式是「{failure}」。"
                )
            explanations.append(explanation)
        calibrated.append(
            PracticeQuestion(
                question.level,
                question.tested,
                f"第 {topic.number} 章〈{topic.title}〉第 {index} 題：{question.prompt}",
                question.choices,
                question.answers,
                tuple(explanations),
            )
        )
    return tuple(calibrated)


def _special_practice_questions(topic: Topic) -> tuple[PracticeQuestion, ...] | None:
    if topic.number == 21:
        questions = (
            PracticeQuestion(
                "SAA",
                "Workforce identity",
                "一家公司有800名員工，需要用既有Entra ID群組登入40個AWS帳號，且不得建立長期access keys。最佳方案是什麼？",
                (
                    "使用IAM Identity Center連接既有IdP，以permission sets將短期role sessions指派到各帳號。",
                    "在每個AWS帳號為每名員工建立IAM user並每90天輪替access key。",
                    "所有員工共用一個Administrator IAM user，再用CloudTrail區分操作者。",
                    "只在VPC security group允許公司IP，因此不需要AWS identity。",
                ),
                (0,),
                (
                    "正確。Identity Center集中workforce lifecycle與群組assignment，permission set在member accounts形成roles，"
                    "登入後取得短期credentials；停用IdP使用者即可撤銷未來session，符合多帳號與無長期key要求。",
                    "不選。每帳號建立local users會造成數萬個identity/credential生命週期，離職與權限變更容易遺漏；"
                    "access key rotation也沒有解決workforce federation與集中MFA。",
                    "不選。共享user破壞個人歸屬、least privilege與可稽核性；CloudTrail只能看到同一principal，"
                    "不能可靠證明哪位員工實際執行操作。",
                    "不選。Security group只控制network reachability，不會替AWS API request建立principal或authorization；"
                    "從公司IP進入的未驗證request仍應被IAM拒絕。",
                ),
            ),
            PracticeQuestion(
                "SAA",
                "Workload credentials",
                "EC2上的程式需要讀取特定S3 prefix。哪個方案最符合least privilege並避免長期credentials？",
                (
                    "建立EC2 service trust的IAM role，只允許該prefix的s3:GetObject，透過instance profile掛到instance。",
                    "把管理員access key寫入user data，開機後輸出到環境變數。",
                    "建立bucket public-read，讓EC2不需要任何AWS credentials。",
                    "只建立IAM permissions policy，但不附到role/user，也不建立instance profile。",
                ),
                (0,),
                (
                    "正確。Instance profile讓EC2 workload從metadata取得會自動輪替的temporary role credentials；"
                    "permissions policy可把Action與object ARN限制到所需prefix。",
                    "不選。User data、environment、AMI與log都可能洩漏長期key；AdministratorAccess還會讓單一EC2 compromise"
                    "擴散到整個帳號。",
                    "不選。Public bucket把authentication與authorization全部繞過，且Block Public Access通常會阻止此設定；"
                    "公開資料也應透過CloudFront/OAC等受控入口。",
                    "不選。Policy document本身不會被評估，必須附到identity或resource；EC2還需要instance profile把role"
                    "呈現給instance。",
                ),
            ),
            PracticeQuestion(
                "SAA",
                "Trust policy vs permissions policy",
                "一個role的trust policy允許Lambda service principal AssumeRole，但permissions policy沒有任何Allow。Lambda取得session後能做什麼？",
                (
                    "可以扮演role，但對一般AWS API仍是implicit deny，除非其他applicable policy建立Allow。",
                    "可以執行所有Lambda與CloudWatch actions，因為service principal已被信任。",
                    "完全不能AssumeRole，因為trust policy必須包含每個data-plane action。",
                    "自動繼承建立這個role之IAM user的permissions。",
                ),
                (0,),
                (
                    "正確。Trust policy只回答誰能取得role session；permissions policy回答session能做什麼。沒有Allow時，"
                    "authorization從implicit deny開始，因此例如logs:PutLogEvents也會被拒絕。",
                    "不選。被信任不等於被授權；AWS service integration通常還需要execution role中的具名actions/resources。",
                    "不選。sts:AssumeRole放在trust policy；S3、DynamoDB、Logs等data-plane actions放在permissions policy，"
                    "兩者是不同門。",
                    "不選。Role session不會繼承role建立者的權限；effective permissions來自role、session、boundary、SCP等"
                    "applicable policies。",
                ),
            ),
            PracticeQuestion(
                "SAP",
                "Third-party delegation",
                "SaaS供應商需要進入每個客戶帳號讀取一個inventory bucket。哪個設計最能降低confused deputy與credential風險？",
                (
                    "每個客戶建立具名cross-account role，trust vendor role並要求每客戶唯一ExternalId；permissions只讀指定bucket。",
                    "每個客戶建立IAM user，把access key寄給供應商並永久保存。",
                    "Trust整個vendor account root且不加Condition，permissions設為ReadOnlyAccess。",
                    "把inventory bucket設成public，但用不易猜的bucket name。",
                ),
                (0,),
                (
                    "正確。具名Principal縮小可Assume範圍，ExternalId讓vendor不能把另一客戶的role ARN混用；temporary STS"
                    "credentials與bucket-scoped permissions再限制session impact。",
                    "不選。長期keys難輪替、難追蹤每次customer session，供應商洩漏後也沒有自然失效時間。",
                    "不選。信任整個account且沒有ExternalId會擴大供應商內部principal範圍並留下confused-deputy風險；"
                    "AWS managed ReadOnlyAccess也遠超單一bucket需求。",
                    "不選。Security through obscurity不是authorization；S3名稱可被洩漏，public data也會被Access Analyzer與"
                    "Block Public Access視為風險。",
                ),
            ),
            PracticeQuestion(
                "SAP",
                "Delegated IAM administration（選兩項）",
                "平台團隊允許產品團隊自行建立deployment roles，但新role永遠不得操作Organizations、IAM administration或security log buckets。應採取哪兩項？",
                (
                    "要求所有新role附上由平台管理的permissions boundary，將最大權限限制在核准services/resources。",
                    "用SCP或不可繞過的IAM conditions，拒絕未附指定boundary的CreateRole及移除/替換boundary。",
                    "只在文件中要求產品團隊不要附AdministratorAccess。",
                    "讓產品團隊建立role後，由每季人工稽核找出超權限。",
                    "把所有產品團隊都加入management account的Administrator群組。",
                ),
                (0, 1),
                (
                    "正確。Boundary與role identity policies形成交集，即使產品團隊附較大的Allow，effective permissions仍不能超過平台上限。",
                    "正確。只有boundary而允許建立者移除它仍可繞過；creation condition與organization guardrail要保護boundary生命週期。",
                    "不選。文件是detective/social control，不是authorization enforcement，無法阻止錯誤或惡意設定立即生效。",
                    "不選。季度稽核發現得太晚，且在暴露窗口內已有高權限；它可補充但不能取代preventive boundary。",
                    "不選。Management account與organization admin權限是最大blast radius，不應作為日常delegation機制。",
                ),
            ),
        )
        return _rotate_questions(questions, topic.number)
    if topic.number == 22:
        questions = (
            PracticeQuestion(
                "SAA",
                "Explicit deny",
                "一個role的identity policy允許s3:GetObject，但bucket policy在aws:SecureTransport=false時明確Deny s3:*。使用HTTP請求會怎樣？",
                (
                    "拒絕。任何applicable explicit Deny都會覆蓋identity policy的Allow。",
                    "允許。Identity policy比bucket policy優先。",
                    "隨機允許或拒絕，取決於哪份policy先建立。",
                    "只有跨帳號才拒絕，同帳號會忽略bucket policy。",
                ),
                (0,),
                (
                    "正確。Policy不是用建立時間或固定順序覆寫；request同時匹配Allow與explicit Deny時，Deny勝出。"
                    "改用HTTPS使Condition不匹配後，identity Allow才可能生效。",
                    "不選。Identity與resource policy沒有這種絕對優先順序；explicit Deny是跨applicable policy types的共同上限。",
                    "不選。IAM evaluation是deterministic，與建立時間或讀取順序無關。",
                    "不選。Bucket policy也會限制同帳號requests，尤其explicit Deny常用來強制TLS、VPC endpoint或organization boundary。",
                ),
            ),
            PracticeQuestion(
                "SAA",
                "Same-account union",
                "同帳號IAM role沒有s3:GetObject identity Allow，但bucket policy直接Allow該role ARN讀取objects，且沒有boundary/SCP/Deny。結果為何？",
                (
                    "通常允許；同帳號resource-based Allow可直接授權具名principal，但仍要留意role ARN與role session principal差異。",
                    "一定拒絕，因為identity policy與bucket policy永遠都必須同時Allow。",
                    "一定允許，即使permissions boundary有explicit Deny。",
                    "只有object ACL可以授權，bucket policy無法授權object actions。",
                ),
                (0,),
                (
                    "正確。對同帳號具名principal，identity/resource permissions常形成union；但principal寫法、session、boundary與"
                    "其他Deny仍會改變結果，所以實務需以官方evaluation rules與真實request驗證。",
                    "不選。兩側都Allow是cross-account常見要求，不是所有same-account資源policy的固定規則。",
                    "不選。Explicit Deny仍勝出；某些resource-principal與boundary細節不能簡化成『resource policy永遠繞過boundary』。",
                    "不選。S3 bucket policy可使用object ARN授權s3:GetObject；modern S3通常停用ACL。",
                ),
            ),
            PracticeQuestion(
                "SAA",
                "Cross-account intersection",
                "Account A role要讀Account B bucket。A端identity policy允許GetObject，但B端bucket policy沒有授權A。結果為何？",
                (
                    "拒絕；cross-account存取需要來源identity具備permission，目標resource/trust也接受外部principal。",
                    "允許，因為來源帳號已經授權自己的role。",
                    "允許，只要兩個accounts都在同一Organizations。",
                    "由S3 Block Public Access設定決定，與bucket policy無關。",
                ),
                (0,),
                (
                    "正確。Account A無權單方面授權自己存取Account B資源；B必須用bucket policy、access point policy或role trust建立授權路徑。",
                    "不選。Identity policy只能代表A允許role發出request，不能代表B同意共享資源。",
                    "不選。同一organization本身不自動分享resources；可用aws:PrincipalOrgID簡化condition，但仍需要Allow。",
                    "不選。Block Public Access主要阻止public policies/ACLs；具名cross-account access仍由IAM與resource policy決定。",
                ),
            ),
            PracticeQuestion(
                "SAP",
                "Guardrail intersections",
                "Role policy、bucket policy都Allow，但request仍AccessDenied。最有效的除錯順序是什麼？",
                (
                    "確認caller/ARN與CloudTrail，再查explicit Deny、SCP/RCP、boundary、session policy、endpoint policy及KMS key policy。",
                    "直接加AdministratorAccess，若成功就永久保留。",
                    "只重試直到IAM eventual consistency自然解決。",
                    "關閉Block Public Access與所有organization policies。",
                ),
                (0,),
                (
                    "正確。先確定實際principal與resource，再逐層找限制上限和service-specific authorization；KMS、VPC endpoint與"
                    "session policy是常被漏看的獨立邊界。",
                    "不選。Admin會遮蔽根因、擴大blast radius，而且可能仍被SCP/key policy explicit Deny阻止。",
                    "不選。Eventual consistency可能影響剛修改的policy，但持續重試不能解釋穩定Deny，也可能觸發throttling。",
                    "不選。一次移除所有controls會造成不可接受暴露，且失去定位是哪一層Deny的證據。",
                ),
            ),
            PracticeQuestion(
                "SAP",
                "SCP與permissions boundary（選兩項）",
                "關於SCP與permissions boundary，哪兩項正確？",
                (
                    "兩者通常都不授權；它們限制identity policies可產生的最大effective permissions。",
                    "SCP適合organization/OU/account guardrail，permissions boundary適合限制單一user/role的delegated maximum。",
                    "只要SCP Allow某action，member account role即使沒有identity policy也能執行。",
                    "Permissions boundary可直接附到IAM group並自動限制所有members。",
                    "SCP會限制management account root，因此可把所有organization administration都放在management account日常使用。",
                ),
                (0, 1),
                (
                    "正確。它們是permission ceilings；仍需要identity/resource policy建立Allow，且explicit Deny可進一步阻止。",
                    "正確。SCP控制組織層principal上限，boundary控制具名IAM entity，兩者scope與delegation use case不同。",
                    "不選。SCP Allow不會創造permission；member role仍需IAM/resource Allow。",
                    "不選。Permissions boundary支援IAM users與roles，不直接附到group。",
                    "不選。SCP不適用management account；因此management account必須最小化日常操作而非依賴SCP保護。",
                ),
            ),
        )
        return _rotate_questions(questions, topic.number)
    if topic.number == 41:
        questions = (
            PracticeQuestion(
                "SAA",
                "IAM policy vs bucket policy",
                "Account A的AnalyticsReader role需要讀Account B bucket的raw/ prefix。哪個設定完整且符合least privilege？",
                (
                    "A端role identity policy允許ListBucket/GetObject；B端bucket policy以該role為Principal並限制bucket ARN與raw/* object ARN。",
                    "只在A端加AdministratorAccess，B端不需設定。",
                    "只在B端security group允許A的CIDR。",
                    "關閉B bucket的Block Public Access並加入public-read ACL。",
                ),
                (0,),
                (
                    "正確。Cross-account需要來源principal被允許發出actions，也需要目標bucket owner接受該principal。"
                    "ListBucket使用bucket ARN與s3:prefix，GetObject使用raw/* object ARN。",
                    "不選。A帳號無權透過自己的identity policy單方面授權讀B資源；AdministratorAccess也嚴重超權限。",
                    "不選。S3 bucket不是放在可套security group的VPC ENI上；network reachability也不等於IAM authorization。",
                    "不選。具名cross-account access不需要public bucket。Public ACL擴大到匿名世界，且modern default會由BPA/Ownership阻止。",
                ),
            ),
            PracticeQuestion(
                "SAA",
                "Bucket ARN vs object ARN",
                "哪一組Action與Resource配對正確？",
                (
                    "s3:ListBucket → arn:aws:s3:::acme-data；s3:GetObject → arn:aws:s3:::acme-data/raw/*。",
                    "s3:ListBucket → arn:aws:s3:::acme-data/*；s3:GetObject → arn:aws:s3:::acme-data。",
                    "兩個action都只能使用arn:aws:s3:::acme-data。",
                    "S3 policy不使用ARN，只能使用bucket DNS name。",
                ),
                (0,),
                (
                    "正確。ListBucket是bucket-level operation；GetObject作用在每個object。s3:prefix condition限制LIST結果，"
                    "object ARN則限制真正可讀的keys。",
                    "不選。這是最常見的反向配對錯誤，statements不會match預期resource。",
                    "不選。只給bucket ARN無法匹配GetObject；只給object ARN也無法匹配ListBucket。",
                    "不選。IAM policy使用S3 ARNs描述resources，endpoint URL不是Resource欄位。",
                ),
            ),
            PracticeQuestion(
                "SAA",
                "Private static website",
                "公司要以CloudFront提供公開靜態網站，但S3 objects不得被使用者直接存取。最佳方案是什麼？",
                (
                    "保持bucket private與Block Public Access，使用CloudFront Origin Access Control，bucket policy只允許該distribution讀取。",
                    "關閉Block Public Access，把bucket policy Principal設為*。",
                    "使用S3 static website endpoint並只靠難猜URL保護origin。",
                    "把CloudFront security group加到S3 bucket。",
                ),
                (0,),
                (
                    "正確。使用者只到CloudFront；OAC以service principal簽署到S3的requests，bucket policy可用distribution SourceArn限制。",
                    "不選。Public bucket允許繞過CloudFront cache、WAF與TLS/control策略，且擴大資料暴露。",
                    "不選。S3 website endpoint需要公開讀取且不是OAC的REST origin模式；難猜URL不是authorization。",
                    "不選。S3不附security group；access由IAM/bucket policy、BPA、endpoint與network origin conditions控制。",
                ),
            ),
            PracticeQuestion(
                "SAA",
                "S3 vs EFS",
                "應用需要多台Linux servers同時append檔案、取得POSIX locks並rename directories。應選哪個儲存？",
                (
                    "Amazon EFS，因為它提供共享NFS/POSIX file semantics。",
                    "Amazon S3，因為object數量近乎無限。",
                    "每台server各自使用instance store並每日同步。",
                    "只使用S3 Glacier Deep Archive。",
                ),
                (0,),
                (
                    "正確。題目核心是shared filesystem semantics，不是容量。EFS支援多clients、directories、in-place file operations與locks。",
                    "不選。S3是object API，PUT通常取代整個object，沒有一般共享filesystem的append/rename/locking contract。",
                    "不選。各自local state會產生衝突、遺失與複雜同步；instance stop/terminate也可能失去資料。",
                    "不選。Deep Archive是長期archive，取回需等待，完全不支援interactive POSIX writes。",
                ),
            ),
            PracticeQuestion(
                "SAP",
                "Large-scale data lake access（選兩項）",
                "數百個teams跨帳號存取同一S3 data lake，bucket policy接近大小上限，且每個team只能走自己的VPC。哪兩個動作最合適？",
                (
                    "為不同teams建立VPC-only S3 Access Points，將各自policy與network origin分離。",
                    "保留bucket-level guardrail，限制只能透過核准access points/organization principals存取。",
                    "把所有team principals繼續塞入單一bucket policy直到部署失敗。",
                    "重新啟用object ACL，讓每個developer自行管理權限。",
                    "建立一台NAT instance並用source IP判斷每個team身份。",
                ),
                (0, 1),
                (
                    "正確。Access Point為每個consumer建立具名endpoint、獨立policy與VPC network origin，降低單一bucket policy複雜度。",
                    "正確。Access point policy與bucket policy共同作用；bucket仍應保留organization、TLS與核准access-point等中央data perimeter。",
                    "不選。Policy size與review blast radius已是明確替換訊號，繼續集中會阻礙變更並增加誤授權風險。",
                    "不選。Modern S3應保持Bucket owner enforced並停用ACL；分散ACL讓ownership與audit更難。",
                    "不選。NAT IP不是可靠principal identity，也不處理S3 authorization；還會增加單點、port與cost問題。",
                ),
            ),
        )
        return _rotate_questions(questions, topic.number)
    return None


def practice_questions(topic: Topic) -> tuple[PracticeQuestion, ...]:
    authored = questions_for_chapter(topic.number)
    if authored is not None:
        return tuple(
            PracticeQuestion(
                level=row["level"],
                tested=row["tested"],
                prompt=row["prompt"],
                choices=tuple(row["choices"]),
                answers=tuple(row["answers"]),
                explanations=tuple(row["explanations"]),
                question_id=row["id"],
                kind=row["kind"],
                intent=row["intent"],
                task_keys=tuple(row["task_keys"]),
                sources=tuple(
                    (
                        source["title"],
                        source["url"],
                        source.get("kind", "official"),
                    )
                    for source in row["resolved_sources"]
                ),
                inspirations=tuple(
                    (
                        source["title"],
                        source["url"],
                        source.get("kind", "community"),
                    )
                    for source in row["resolved_inspirations"]
                ),
                author_agent=row["author_agent"],
            )
            for row in authored
        )
    special = _special_practice_questions(topic)
    if special is not None:
        return _calibrate_questions(topic, special)
    rows = components(topic)
    primary_name, primary = rows[0]
    peer_name, peer = rows[1] if len(rows) > 1 else ("相鄰服務", primary)
    third_name, third = rows[2] if len(rows) > 2 else ("手動維運方案", peer)
    tasks_saa = ", ".join(task for task in topic.tasks if task.startswith("SAA")) or "SAA基礎"
    tasks_sap = ", ".join(task for task in topic.tasks if task.startswith("SAP")) or "SAP延伸"

    selection_choices = (
        topic.decision,
        topic.alternative,
        f"只部署{peer_name}，但不建立{primary_name}所負責的contract。",
        f"維持現況並在發生「{topic.failure}」後由人工處理。",
    )
    selection_explanations = (
        f"正確。題目的hard constraint是「{topic.problem}」。這個方案直接使用{primary_name}的能力："
        f"{primary.purpose} 底層成立原因是：{primary.mechanism}",
        f"不選。這是合理的相鄰方案，但它優化的是另一組條件：{topic.alternative}。"
        f"只有出現替換訊號「{primary.replace}」時，才應優先於目前答案。",
        f"不選。{peer_name}的真正責任是：{peer.purpose}。單獨使用它沒有完成{primary_name}的責任，"
        "因此架構圖看似多一個服務，hard constraint仍然沒有被滿足。",
        f"不選。人工處理沒有可預期RTO、scale或audit evidence，並保留已知failure mode：{topic.failure}",
    )

    config_choices = (
        primary.config,
        peer.config,
        f"把{primary_name}設成預設值，不記錄identity、scope、quota或failure test。",
        "只提高容量與預算，不修改任何authorization、data semantics或recovery設定。",
    )
    config_explanations = (
        f"正確。這些是{primary_name}真正控制行為的設定面：{primary.config}。考試不一定要求背CLI，"
        "但會用文字描述其中一個欄位，測你是否知道它改變哪個contract。",
        f"不選。這些設定屬於{peer_name}：{peer.config}。它們可能需要一起設定，但不能取代"
        f"{primary_name}目前負責的機制。",
        "不選。AWS managed不代表不需配置。Default可能不符合cross-account、encryption、latency、"
        "retention或RTO；沒有scope與evidence也無法通過架構審查。",
        "不選。容量只能解決容量瓶頸；它無法修正錯誤的policy、protocol、state owner或failure domain，"
        "且通常會增加成本。",
    )

    mechanism_choices = (
        primary.mechanism,
        peer.mechanism,
        f"{primary_name}會自動理解所有business requirements，因此不需application或operations配合。",
        f"只要resource建立成功，就可保證不會發生「{topic.failure}」。",
    )
    mechanism_explanations = (
        f"正確。{primary_name}的實際流程是：{primary.mechanism} 這把control-plane設定與data-plane結果"
        "連起來，也說明為何只建立resource但沒有正確參數時，production行為仍可能完全不同。",
        f"不選。這段描述的是{peer_name}的機制。若題目需求真的轉成「{peer.choose}」，答案才可能改選它。",
        "不選。Managed service只接手明確責任；資料模型、權限、retry、RTO/RPO與business invariants"
        "仍由架構與application共同負責。",
        f"不選。Create/Deploy成功只證明control plane接受設定，未驗證data plane、quota、依賴與"
        f"故障路徑。此章明確要求測試：{topic.failure}",
    )

    saa_choices = (
        f"選{primary_name}並設定：{primary.config}",
        f"選{peer_name}，因為它功能看起來較多，不再檢查protocol或state。",
        f"選{third_name}，並假設所有managed service都自動跨AZ/Region與自動加密。",
        "把所有選項都部署，避免做取捨。",
    )
    saa_explanations = (
        f"正確。SAA通常要求在單一workload中辨識最直接、managed且符合限制的方案。"
        f"{primary_name}的適用時機是：{primary.choose}。本題對應{tasks_saa}。",
        f"不選。功能數量不是評分準則；{peer_name}的選擇條件是「{peer.choose}」，"
        "必須與題目constraint吻合。",
        f"不選。{third_name}的機制是「{third.mechanism}」，不能推論所有availability、encryption"
        "或replication都已開啟；題目會用這種假設當distractor。",
        "不選。同時部署所有服務會增加cost、failure dependencies與operations，違反題目常見的"
        "least operational overhead或most cost-effective條件。",
    )

    sap_choices = (
        topic.decision,
        "建立跨帳號owner與guardrail，版本化設定，使用canary/分波推出，並以business metric與audit evidence控制rollback。",
        topic.alternative,
        f"先給organization-wide AdministratorAccess以加速migration，完成後再人工回收。",
        "只建立第二Region或第二account，但不搬資料、不演練failover，也不指定on-call owner。",
    )
    sap_explanations = (
        f"正確。這是workload層的核心mechanism：{topic.decision}",
        f"正確。SAP不只問服務；還要求operating model。這個動作補上delegation、blast radius、"
        f"rollout、rollback與evidence，對應{tasks_sap}。",
        f"不選。它只在條件改為「{topic.alternative}」時合理；目前會犧牲題目的核心constraint。",
        "不選。暫時admin常變成永久權限，也破壞least privilege、audit與blast-radius isolation。"
        "Migration速度不能靠移除所有guardrails換取。",
        "不選。空的standby architecture只是成本；沒有data、identity、DNS、dependency order與game day，"
        "無法宣稱達成RTO/RPO。",
    )

    questions = (
        PracticeQuestion(
            "SAA",
            "服務選型與答案翻轉條件",
            f"{topic.scenario} 核心限制是：{topic.problem}。哪一個方案最符合需求？",
            selection_choices,
            (0,),
            selection_explanations,
        ),
        PracticeQuestion(
            "SAA",
            "關鍵設定與參數",
            f"團隊已選擇{primary_name}。下一步哪一組設定最直接決定本章的安全、流量、容量或資料行為？",
            config_choices,
            (0,),
            config_explanations,
        ),
        PracticeQuestion(
            "SAA → SAP",
            "底層機制",
            f"哪一段最準確描述{primary_name}在request/data path中的底層機制？",
            mechanism_choices,
            (0,),
            mechanism_explanations,
        ),
        PracticeQuestion(
            "SAA",
            "高頻干擾選項",
            f"考題要求以最少營運負擔處理「{topic.problem}」。應採取哪個動作？",
            saa_choices,
            (0,),
            saa_explanations,
        ),
        PracticeQuestion(
            "SAP",
            "企業治理與operating model（選兩項）",
            f"同一設計擴大到多帳號與production migration，並要求可稽核rollback。哪兩個動作應一起採用？",
            sap_choices,
            (0, 1),
            sap_explanations,
        ),
    )
    return _calibrate_questions(topic, _rotate_questions(questions, topic.number))
