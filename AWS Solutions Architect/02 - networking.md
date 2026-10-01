---
title: "Networking 與流量入口"
part: 1
as_of: 2026-10-01
---

# Part 1　Networking 與流量入口

# 第 11 章　VPC 與 CIDR 規劃

地址規劃會限制未來VPC互連、hybrid連線、擴展與組織合併。

## 跟著一個封包走：先從故事開始

把鏡頭拉到一個真實的production現場：企業預計建立五十個帳號、三個Region並連回兩個資料中心。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：地址規劃會限制未來VPC互連、hybrid連線、擴展與組織合併。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：把網路想成城市交通：DNS找地址，route選道路，security rules決定哪扇門能進。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon VPC是這一章的入口，AWS VPC IP Address Manager用來畫出邊界；主要方向「預留不可重疊CIDR、依環境與區域分配範圍，並用IPAM集中追蹤。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：企業預計建立五十個帳號、三個Region並連回兩個資料中心。

來源（使用者／VPC／on-premises）
          │ ① 名稱解析：要連到哪個位址？
          │ ② 去程 route + network policy
          ▼
[Amazon VPC]
          │ 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
          ▼
[target／application state]
          │ ③ response沿有效回程返回
控制面：建立DNS、route、listener、policy與health設定
資料面：每個packet／connection／request實際沿路通過
本章其他角色：
  · AWS VPC IP Address Manager：跨accounts與Regions規劃、分配、監控IP address space。

失敗時先找：每個團隊自行使用10.0.0.0/16，之後Transit Gateway與Direct Connect無法直接路由。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問Amazon VPC有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon VPC和AWS VPC IP Address Manager並不是兩個任意的產品名稱。前者適合本章，是因為「預留不可重疊CIDR、依環境與區域分配範圍，並用IPAM集中追蹤。」直接回應了眼前的問題；後者描述的「小CIDR節省地址但增加後續擴張與重編址風險；大CIDR則可能浪費企業地址空間。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：每個團隊自行使用10.0.0.0/16，之後Transit Gateway與Direct Connect無法直接路由。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「address space is an architectural resource」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 |
| AWS VPC IP Address Manager | 跨accounts與Regions規劃、分配、監控IP address space。 | 以IPAM pools階層委派CIDR，追蹤utilization、overlap與compliance。 |

## 把全圖套進一個具體案例

**場景：** 企業預計建立五十個帳號、三個Region並連回兩個資料中心。

1. 故事的起點：企業預計建立五十個帳號、三個Region並連回兩個資料中心。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon VPC負責「建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS VPC IP Address Manager各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「每個團隊自行使用10.0.0.0/16，之後Transit Gateway與Direct Connect無法直接路由。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon VPC

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：地址規劃會限制未來VPC互連、hybrid連線、擴展與組織合併。
- **具體例子／邊界：** 在「企業預計建立五十個帳號、三個Region並連回兩個資料中心。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS VPC IP Address Manager

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：小CIDR節省地址但增加後續擴張與重編址風險；大CIDR則可能浪費企業地址空間。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：每個團隊自行使用10.0.0.0/16，之後Transit Gateway與Direct Connect無法直接路由。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：address space is an architectural resource。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### hybrid connectivity

讓on-premises與cloud長期互通的network、DNS、identity與routing設計，不只是建立一條VPN。

### Direct Connect

從客戶或colocation到AWS的專用網路連線；提供較穩定路徑，但本身不等於端到端加密或自動高可用。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### IP address

網路介面的數字位址。Private IP在私有routing domain內使用；public IP可經Internet routing。

### hostname

可讀的網路名稱，例如api.example.com；程式先經DNS取得address後才建立TCP/UDP連線。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### CIDR

以10.0.0.0/16這類prefix描述一段IP範圍；prefix越大，範圍越小。重疊CIDR會破壞明確routing。

### NACL

Network ACL，subnet邊界的stateless ordered allow/deny rules；去回程與ephemeral ports要分開允許。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### Amazon VPC

- **功用：** 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
- **底層機制：** ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。
- **關鍵設定：** IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
- **選擇時機：** 任何需要私有位址、network segmentation或hybrid connectivity的workload。
- **替換時機：** 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。

### AWS VPC IP Address Manager

- **功用：** 跨accounts與Regions規劃、分配、監控IP address space。
- **底層機制：** 以IPAM pools階層委派CIDR，追蹤utilization、overlap與compliance。
- **關鍵設定：** operating Regions、scope、top-level/child pools、allocation rules、locale、sharing與monitoring。
- **選擇時機：** 大型organization、自動account vending與hybrid CIDR避免重疊。
- **替換時機：** 少量單一VPC可人工規劃；IPAM不取代route tables或DNS。

## 考前與實作時再查：設定操作手冊

### Amazon VPC：逐項設定說明

#### `IPv4／IPv6 CIDR`

- **控制什麼：** 定義VPC可分配的IP位址範圍；subnet必須從這個範圍切割。CIDR重疊會讓peering、TGW與hybrid routing難以判斷封包目的地。
- **何時需要：** 建立新環境、預留成長空間，或未來要連接其他VPC與on-premises時先決定。
- **怎麼設定／驗證：** 建立VPC時設定CidrBlock；要擴充可加入secondary CIDR。先以IPAM或地址表檢查所有既有network，避免只看目前一個帳號。
- **常見錯法：** 把每個VPC都設成10.0.0.0/16很快會重疊；CIDR很大也不代表subnet、route與安全邊界設計良好。

#### `subnets`

- **控制什麼：** 把VPC位址切成單一AZ內的部署與route-table邊界。Subnet本身不叫public或private，真正差異是route與resource是否有public IP。
- **何時需要：** 需要跨AZ高可用、分隔web/app/data tiers，或建立inspection、egress與endpoint subnets時。
- **怎麼設定／驗證：** 為每個AZ建立獨立subnet並關聯明確route table；private subnet不要自動分配public IP，並預留足夠可用地址給ENI與擴展。
- **常見錯法：** 只建立兩個名稱叫public/private的subnet卻共用錯誤route table，會讓資料庫意外取得internet path或讓app無法出站。

#### `route tables`

- **控制什麼：** 依目的CIDR做longest-prefix match並選擇下一跳，例如local、IGW、NAT、TGW、peering connection或VPC endpoint。
- **何時需要：** 任何跨subnet、Internet、AWS service、VPC或on-premises的封包都要先證明去程與回程route成立。
- **怎麼設定／驗證：** 把route table明確關聯到subnet；新增destination與target後，再到另一側建立return route。使用Flow Logs與reachability analysis驗證實際路徑。
- **常見錯法：** 只有去程route沒有回程route、把private subnet的0.0.0.0/0指到IGW，或忘記更精確route會優先匹配，都是常見故障。

#### `DNS support／DNS hostnames`

- **控制什麼：** EnableDnsSupport控制VPC能否使用Amazon-provided DNS resolver；EnableDnsHostnames控制具有public IPv4的instance是否取得對應DNS hostname。
- **何時需要：** workload用hostname存取AWS service、private hosted zone、service discovery，或要啟用peering DNS resolution時。
- **怎麼設定／驗證：** 在VPC attributes開啟DNS resolution與DNS hostnames，IaC分別使用EnableDnsSupport與EnableDnsHostnames；再設定private hosted zone或Resolver rules。
- **常見錯法：** DNS能把名稱翻成IP，但不會建立route、security group或IAM permission；名稱解析成功仍可能完全連不到目標。

#### `Flow Logs`

- **控制什麼：** 記錄ENI、subnet或VPC層的accepted/rejected flow metadata，用來判斷封包是否到達、被拒絕及走哪個介面。
- **何時需要：** 除錯timeout、驗證segmentation、建立network forensic evidence或流量基線時。
- **怎麼設定／驗證：** 選擇traffic type、aggregation interval、欄位格式與CloudWatch Logs/S3/Firehose destination；先確認service role與retention。
- **常見錯法：** Flow Logs不是packet capture，不會保存payload，也看不到application-level HTTP錯誤；只靠它無法證明IAM或應用程式成功。

### AWS VPC IP Address Manager：逐項設定說明

#### `operating Regions`

- **控制什麼：** `operating Regions`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS VPC IP Address Manager前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `scope`

- **控制什麼：** `scope`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「大型organization、自動account vending與hybrid CIDR避免重疊。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS VPC IP Address Manager建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `top-level/child pools`

- **控制什麼：** `top-level/child pools`建立父子namespace/pool與生命週期規則，讓AWS VPC IP Address Manager可以委派、繼承或依路徑管理資源。
- **何時需要：** 多團隊需要分層管理parameters或IP ranges，並避免名稱/CIDR碰撞時。
- **怎麼設定／驗證：** 先建立top-level owner與child boundaries，使用穩定path/CIDR allocation rules；對敏感values加IAM/KMS並監控過期/未使用項目。
- **常見錯法：** Hierarchy只是組織方式，不自動授權；child pool過度切割會浪費地址，parameter policy也不是完整secret rotation。

#### `allocation rules`

- **控制什麼：** `allocation rules`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「大型organization、自動account vending與hybrid CIDR避免重疊。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS VPC IP Address Manager以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `locale`

- **控制什麼：** `locale`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署AWS VPC IP Address Manager前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `sharing`

- **控制什麼：** `sharing`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「大型organization、自動account vending與hybrid CIDR避免重疊。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS VPC IP Address Manager建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `monitoring`

- **控制什麼：** `monitoring`決定AWS VPC IP Address Manager蒐集哪些control/data-plane audit events，以及如何集中查詢或監控。
- **何時需要：** 需要回答誰在何時修改resource、誰讀寫敏感資料，或集中多帳號事件調查時。
- **怎麼設定／驗證：** 選擇management/data event selectors、accounts/Regions、retention與S3/Lake/CloudWatch destination；用已知API call驗證事件可查。
- **常見錯法：** Data events量大且可能昂貴；只開management events看不到S3 object/Lambda invoke等data-plane行為。

## 可以直接對照 AWS 的設定範例

### VPC 與跨 AZ private subnets（CloudFormation）

```yaml
Resources:
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

```

1. /16是VPC總位址池；每個/20 subnet位於不同AZ，預留未來tiers與成長空間。
2. MapPublicIpOnLaunch=false只避免自動public IPv4；private/public仍由route table是否指向IGW決定。
3. Production還需route tables、egress、VPC endpoints、flow logs與non-overlap hybrid planning。

## 讀到這裡，請用自己的話說一次

1. Amazon VPC的責任：建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
2. 底層機制：ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。
3. 第一個要看的設定：IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
4. 選擇邏輯：預留不可重疊CIDR、依環境與區域分配範圍，並用IPAM集中追蹤。
5. 不要混淆：AWS VPC IP Address Manager的責任是「跨accounts與Regions規劃、分配、監控IP address space。」；它不會自動取代Amazon VPC。
6. 替換訊號：跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。
7. 最常見錯法：每個團隊自行使用10.0.0.0/16，之後Transit Gateway與Direct Connect無法直接路由。
8. 可移植原則：address space is an architectural resource。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 | 任何需要私有位址、network segmentation或hybrid connectivity的workload。 | 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。 |
| AWS VPC IP Address Manager | 跨accounts與Regions規劃、分配、監控IP address space。 | 以IPAM pools階層委派CIDR，追蹤utilization、overlap與compliance。 | 大型organization、自動account vending與hybrid CIDR避免重疊。 | 少量單一VPC可人工規劃；IPAM不取代route tables或DNS。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 小CIDR節省地址但增加後續擴張與重編址風險；大CIDR則可能浪費企業地址空間。 | 只有當題目條件明確改變時才可能合理。 | 每個團隊自行使用10.0.0.0/16，之後Transit Gateway與Direct Connect無法直接路由。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「小CIDR節省地址但增加後續擴張與重編址風險；大CIDR則可能浪費企業地址空間。」之間做選擇。
- 認得常考設定：IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
- 對應官方tasks：SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies。

## 本章 10 題考題

### 練習題 1｜SAA｜11.1 CIDR 與 subnet 容量規劃

一個新 VPC 使用 10.20.0.0/16，會部署在 3 個 AZ。每個 AZ 都需要 web、app、data 三個 subnet；其中 app tier 預估需要 2,000 個 ENI，並要求預留約 50% 成長空間。哪一種規劃最合理？

A. 為三個 AZ 的 app tier 分別配置互不重疊的 10.20.0.0/20、10.20.16.0/20、10.20.32.0/20，web、data 使用其他不重疊範圍，並保留剩餘 /16 空間
B. 為三個 AZ 的 app tier 分別配置 /21；每個 /21 有 2,048 個位址，剛好比目前 2,000 個 ENI 多
C. 為整個 app tier 建立一個 10.20.0.0/18 subnet，再讓三個 AZ 的 instances 共用它
D. 在三個 AZ 都建立 10.20.0.0/20 app subnet；相同 CIDR 可讓跨 AZ failover 不必改路由

**答案：A**

- **A：** 正確。每個 AZ 需要約 2,000×1.5=3,000 個 app ENI；/20 共有 4,096 個 IPv4 位址，扣除 AWS 保留的前四個與最後一個後仍有 4,091 個可用位址，且三段彼此不重疊。
- **B：** 不正確。/21 共有 2,048 個位址，扣除 AWS 保留的五個後僅 2,043 個可用位址，只能接近目前需求，無法容納約 3,000 個 ENI 的成長目標。
- **C：** 不正確。Subnet 只能位於一個 Availability Zone；即使 /18 容量足夠，也不能由三個 AZ 共用，因此無法形成題目要求的多 AZ app tier。
- **D：** 不正確。同一 VPC 內的 subnet CIDR 不能重疊；此外既有 subnet 的 CIDR block 不能原地放大，日後擴充必須建立新 subnet 並遷移 workload。

**事實查證：** [VPC CIDR blocks - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html)、[Subnet CIDR blocks - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)

### 練習題 2｜SAA｜11.2 重疊 CIDR 判斷

網路團隊準備互連三個環境：A 為 10.0.0.0/16，B 為 10.0.128.0/17，C 為 10.1.0.0/16。若必須使用一般 routed connectivity，哪個判斷正確？

A. A、B、C 都不重疊，因為 prefix 長度不同
B. B 完全位於 A 之內，因此 A 與 B 重疊；C 與兩者不重疊
C. 只要把 A 與 B 放在不同 AWS 帳號，就能直接消除路由歧義
D. 在 A 與 B 之間加入 NAT Gateway，就會自動轉換所有雙向流量並解決重疊

**答案：B**

- **A：** 不正確。Prefix 長度不同不代表範圍獨立；10.0.128.0/17 是 10.0.0.0/16 的子集合。
- **B：** 正確。Routed network 需要目的 prefix 可唯一判斷；A 與 B 重疊，而 10.1.0.0/16 位於另一段空間。
- **C：** 不正確。帳號是治理邊界，不會改變封包中的 IP；重疊 CIDR 在跨帳號時仍然重疊。
- **D：** 不正確。NAT Gateway 是特定方向與協定的位址轉換服務，不會自動建立任意 VPC 間的雙向重疊網路。

**事實查證：** [VPC CIDR blocks - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html)、[How VPC peering connections work - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html#vpc-peering-limitations)

### 練習題 3｜SAP｜11.3 多帳號 IPAM pool 階層（選兩項）

一家公司有 50 個 AWS 帳號、3 個 Region，且兩個資料中心已使用部分 RFC1918 位址。平台團隊要讓新帳號自動取得不重疊 CIDR。哪兩個動作最適合？

A. 建立 organization 層級 IPAM，先從可用總範圍排除 on-premises 已使用的 CIDR，再依 Region 與環境建立 child pools
B. 讓每個帳號先建立 10.0.0.0/16 VPC，再由中央試算表登記衝突
C. 將 child pools 分享給核准的帳號或 OU，讓自動化從相符 locale 的 pool 配置 VPC CIDR
D. 只用 Name tag 標示 prod/dev；IPAM 會根據名稱自動重新編址既有 VPC
E. 使用 security group 阻止重疊網路互通，因而不必管理地址空間

**答案：A、C**

- **A：** 正確。IPAM 的 home Region 是建立與管理 IPAM 的控制位置；平台團隊可由根地址建立 top-level pool，再按 Region、環境或業務建立 child pools，避免先配置後才發現重疊。
- **B：** 不正確。先建立再登記會把衝突留到連線階段才發現，且 10.0.0.0/16 重複使用正是中央 IPAM 要避免的問題。
- **C：** 正確。Organizations 的 delegated administrator 管理 IPAM；AWS RAM 將 pool 分享給 consumer account或 OU，而 VPC 必須從 locale 與其 Region 相符的 pool 取得 CIDR。這四個概念不能混為一談。
- **D：** 不正確。Tag 可協助分類或 compliance，但 IPAM 不會因名稱而替運作中的 VPC 自動重新編址。
- **E：** 不正確。Security group 控制 ENI 上允許的流量，無法改變 CIDR 所代表的目的範圍，也不能讓路由器辨識兩個相同目的 prefix。

**事實查證：** [What is IPAM? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/what-it-is-ipam.html)、[Create IPv4 pools - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/intro-create-ipv4-pools.html)、[Integrate IPAM with accounts in an AWS Organization - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/enable-integ-ipam.html)、[Share an IPAM pool using AWS RAM - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/share-pool-ipam.html)、[Create a Regional IPv4 pool - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/create-reg-ipam.html)

### 練習題 4｜SAP｜11.4 IPAM pool locale

中央 IPAM 在 us-east-1 管理全球地址空間。團隊要從 IPAM pool 為 ap-southeast-1 的新 VPC 配置 CIDR。該 pool 的 locale 應如何設定？

A. 設成公司總部所在 Region，因為 locale 代表管理者所在地
B. 留空即可從該 pool 配置到任何 Region 的 VPC
C. 設成 ap-southeast-1，因為 pool 必須具有與 regional resource 相符的 locale
D. 設成 us-east-1，因為 IPAM 的 home Region 會覆寫所有 child pool locale

**答案：C**

- **A：** 不正確。Locale 描述 pool 可配置 regional resources 的 AWS Region，不是 IPAM 管理者、delegated administrator 或公司總部所在地。
- **B：** 不正確。Top-level pool 可以使用 None，但要配置 ap-southeast-1 的 VPC，regional child pool 必須具有 ap-southeast-1 locale，不能由無 locale 的根 pool任意跨 Region 配置。
- **C：** 正確。IPAM 可在 us-east-1 home Region 集中管理，但配置 VPC 的 pool locale 必須是 ap-southeast-1；locale 選定後不可修改，並不是可隨時更換的分類標籤。
- **D：** 不正確。Home Region 是建立與管理 IPAM、檢視 operation metrics 的控制位置；它不會覆寫 child pool locale，也不要求所有受管 VPC 都位於 us-east-1。

**事實查證：** [Create a Regional IPv4 pool - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/create-reg-ipam.html)

### 練習題 5｜SAP｜11.5 IPAM unmanaged resource 與 compliance 狀態

公司規定 development VPC 必須由 IPAM pool 取得 /24 到 /20 的 CIDR。某團隊繞過 pool，直接以 EC2 API 建立了一個 /18 VPC。平台團隊在 IPAM 中首先應如何判讀與治理這個資源？

A. 把它視為 compliant，因為只有從 pool 配置的資源才需要遵守 netmask rule
B. 使用 SCP 自動把現有 /18 重新編址為 /20，並保留所有 ENI 位址
C. 先在 IPAM Resources 中辨識它是未由 pool 配置的 unmanaged resource；檢查重疊與歸屬後，再決定匯入或遷移，納管後才依 allocation rules判斷 compliance
D. 在 NACL 拒絕 /18 封包；封包被拒絕後 IPAM 會自動把 VPC 標記為 managed

**答案：C**

- **A：** 不正確。繞過 pool 建立的資源首先是 unmanaged，而不是因為沒有套用 allocation rule 就自動成為 compliant；兩個狀態描述的是不同治理層級。
- **B：** 不正確。SCP 能限制未來 API 行為，但不會替既有 VPC 自動縮小或重新編址；改 CIDR 仍需要明確的遷移與相依資源調整。
- **C：** 正確。IPAM 先區分資源是否由 pool 管理；只有納入可管理的 allocation 後，才可依最小／最大 netmask、locale與 tag rules呈現 compliant或noncompliant。IPAM不會自動重新編址。
- **D：** 不正確。NACL 是 stateless packet filter，不負責地址 inventory、pool ownership 或 compliance，也不會因拒絕封包而改變 IPAM resource status。

**事實查證：** [Monitor CIDR usage by resource - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/monitor-cidr-compliance-ipam.html)、[Create a top-level IPv4 pool - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/create-top-ipam.html)

### 練習題 6｜SAA｜11.6 以 secondary CIDR 擴充 VPC

一個 VPC 的 app subnets 即將用完位址。現有 subnet 不能停機，且 VPC 日後會經 Transit Gateway 連資料中心。哪個改善方式風險最低？

A. 直接把運作中的 /24 subnet 改成 /20
B. 確認新範圍不與 VPC、TGW 或 on-premises 路由重疊後，關聯 secondary CIDR 並從中建立新 subnets
C. 關聯與現有 primary CIDR 相同的 secondary CIDR，再建立同名 subnet
D. 增加 NAT Gateway，讓多個 ENI 共用同一個 private IP

**答案：B**

- **A：** 不正確。既有 subnet 的 CIDR block 不能原地放大；需要建立新 subnet 並遷移或擴展 workload。
- **B：** 正確。VPC 可關聯額外 IPv4 CIDR，但必須先檢查所有互連範圍與 route，之後才能從新範圍切 subnet。
- **C：** 不正確。VPC 內的 CIDR blocks 不能彼此重疊；相同範圍也無法提供新位址。
- **D：** 不正確。NAT 轉換 egress 流量，不會增加 subnet 可分配給 ENI 的 private addresses。

**事實查證：** [VPC CIDR blocks - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html)、[Subnet CIDR blocks - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)

### 練習題 7｜SAA｜11.7 雙棧 IPv6 規劃

團隊把一個 IPv4-only VPC 改為雙棧，認為 IPv6 位址可全球路由，所以不再需要 subnet route 或 security rules。哪個說法正確？

A. IPv6 流量一定先經 IPv4 NAT Gateway，因此既有 IPv4 egress 設計完全不用改
B. AWS 會替所有 IPv6 ENI 自動建立 public DNS 與 unrestricted inbound rule
C. 仍須為 IPv6 規劃 subnet prefix、::/0 的適當 next hop，以及 SG/NACL；若只允許主動出站可使用 egress-only Internet Gateway
D. IPv6 不使用 route table，因此只能在同一 subnet 內通訊

**答案：C**

- **A：** 不正確。一般原生 IPv6 Internet 路徑不依賴 IPv4 NAT；NAT Gateway 的 NAT64 是 IPv6 client 存取 IPv4 destination 的另一種情境。
- **B：** 不正確。可路由位址不等於自動授權；SG、NACL、DNS 與 route 仍需明確設定。
- **C：** 正確。雙棧增加的是另一套路由與政策面；egress-only Internet Gateway 可允許 IPv6 主動出站並阻止 Internet 主動建立連線。
- **D：** 不正確。IPv6 一樣使用 VPC route table；local 與其他 IPv6 routes 決定 next hop。

**事實查證：** [IPv6 support for your VPC - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-migrate-ipv6.html)、[Enable outbound IPv6 traffic using an egress-only internet gateway - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html)

### 練習題 8｜SAP｜11.8 重疊網路的最小服務暴露

併購後，兩個 VPC 都使用 10.30.0.0/16，短期無法重新編址。Consumer 只需要呼叫 provider VPC 中的一個 TCP API，且不需要任意雙向網路。應採用哪個方案？

A. 直接建立 VPC Peering，讓 longest-prefix match 自動選正確的 10.30.0.0/16
B. 把兩個 VPC 同時連到 TGW，並向同一張 route table propagate 相同 prefix
C. 在兩側新增相同優先序的 default route，讓封包隨機選路
D. 由 provider 透過 PrivateLink endpoint service 發布 API，consumer 建立 interface endpoint

**答案：D**

- **A：** 不正確。Peering 要求可路由的非重疊 CIDR；相同目的 prefix 無法表達正確 peer。
- **B：** 不正確。TGW 也不能靠同一 route domain 分辨相同目的 prefix；propagation 反而會造成衝突或不可達。
- **C：** 不正確。Default route 無法消除 local 及重疊 prefix 的歧義，也不能提供可靠服務邊界。
- **D：** 正確。PrivateLink 在 consumer VPC 建立 endpoint ENI，只暴露特定服務，不要求兩個 VPC 的完整 CIDR 互相路由。

**事實查證：** [What is AWS PrivateLink? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)、[How VPC peering connections work - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html#vpc-peering-limitations)

### 練習題 9｜SAA｜11.9 地址空間的成本與成長取捨

架構師正在比較「每個小型 workload 都配置 /16」與「依預估成長從治理過的 pool 配置較小範圍」。哪個觀點最合理？

A. 依 workload 成長、隔離、hybrid 與併購需求配置，避免過度保留耗盡企業可路由空間，也避免小到必須很快重編址
B. VPC CIDR 越大，AWS 每月固定費用一定越高，所以永遠選 /28
C. 最大的 CIDR 永遠最佳，因為 RFC1918 位址在企業中不可能耗盡
D. 浪費的 CIDR 可透過增加 route tables 回收給其他已互連 VPC

**答案：A**

- **A：** 正確。CIDR 本身不是按大小收費的容量，但它是有限的可路由設計資源；配置需同時考慮成長與全域唯一性。
- **B：** 不正確。VPC 不會因 /16 比 /28 大就收固定 CIDR 月費；而 /28 常無法容納實際 ENI。
- **C：** 不正確。大型企業、混合網路與併購很容易耗盡可互連的非重疊私有空間，過大的早期配置也會壓縮後續VPC與資料中心的地址選擇。
- **D：** 不正確。Route table 不會把已配置給某 VPC 的地址所有權釋放給其他 VPC。

**事實查證：** [VPC CIDR blocks - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html)、[What is IPAM? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/what-it-is-ipam.html)

### 練習題 10｜SAP｜11.10 IPAM utilization 改善順序（選兩項）

IPAM 顯示 production pool 可供 VPC 配置的 CIDR 空間即將達到告警門檻，但各 subnet 仍有少量 ENI 位址。團隊希望降低未來配置失敗風險。哪兩個動作應優先執行？

A. 立刻縮小所有運作中 subnet 的 CIDR，讓空出的位址自動回到 pool
B. 盤點 IPAM pool allocations，釋放已不使用的 VPC CIDR allocation，或刪除確認可移除的 VPC並將其 CIDR歸還 pool
C. 刪除 VPC local route，讓同一 IP 可以配置給多個 subnet
D. 刪除閒置 ENI；只要 subnet 多出 private IP，IPAM pool 就會自動收回該 subnet 與 VPC 的 prefix
E. 根據成長預測為上層或 production pool provision額外且不重疊的 CIDR；若無連續空間則規劃新 pool／新 VPC遷移並驗證互連

**答案：B、E**

- **A：** 不正確。既有 subnet CIDR 不能原地縮小；即使重建較小 subnet，釋放的是 VPC CIDR 內部空間，並不必然把 VPC allocation歸還 IPAM pool。
- **B：** 正確。Pool utilization計算的是從 pool 配出的 CIDR allocation；回收不再需要的 VPC或其 pool allocation，才會直接增加該 pool可再次配置的空間。
- **C：** 不正確。Local route 是 VPC 內部連線的基礎，刪除它不會改變 CIDR ownership，也不會讓重疊 allocation 成為可合法重用的地址。
- **D：** 不正確。ENI address屬於 subnet CIDR，subnet屬於 VPC CIDR，而 VPC CIDR才是 IPAM pool allocation；刪除 ENI只改善 subnet位址使用率，不會釋放上層 prefix。
- **E：** 正確。若可回收 allocation不足，應在耗盡前擴充 parent/child pool或建立新的 non-overlapping pool，並把 route、DNS、security與遷移風險納入容量計畫。

**事實查證：** [Monitor CIDR usage with the IPAM dashboard - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/monitor-cidr-usage-ipam.html)、[Create IPv4 pools - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/ipam/intro-create-ipv4-pools.html)、[VPC CIDR blocks - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「預留不可重疊CIDR、依環境與區域分配範圍，並用IPAM集中追蹤。」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「地址規劃會限制未來VPC互連、hybrid連線、擴展與組織合併。」，所以「預留不可重疊CIDR、依環境與區域分配範圍，並用IPAM集中追蹤。」能直接滿足它；若constraint改成「小CIDR節省地址但增加後續擴張與重編址風險；大CIDR則可能浪費企業地址空間。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「預留不可重疊CIDR、依環境與區域分配範圍，並用IPAM集中追蹤。」。替代方案「小CIDR節省地址但增加後續擴張與重編址風險；大CIDR則可能浪費企業地址空間。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「每個團隊自行使用10.0.0.0/16，之後Transit Gateway與Direct Connect無法直接路由。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「地址規劃會限制未來VPC互連、hybrid連線、擴展與組織合併。」，排除會導致「每個團隊自行使用10.0.0.0/16，之後Transit Gateway與Direct Connect無法直接路由。」的選項，再選「預留不可重疊CIDR、依環境與區域分配範圍，並用IPAM集中追蹤。」。本章對應的代表task包括：SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures；SAP-1.1 Architect network connectivity strategies。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「預留不可重疊CIDR、依環境與區域分配範圍，並用IPAM集中追蹤。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「address space is an architectural resource」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 12 章　Subnet、Route Table 與 Internet Gateway

Public/private不是subnet名稱，而是路由與資源public address共同形成的可達性。

## 跟著一個封包走：先從故事開始

如果今天由你值班，收到的需求可能是這樣：ALB必須公開，但應用與資料庫不得接受internet直接連線。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：Public/private不是subnet名稱，而是路由與資源public address共同形成的可達性。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：VPC像一座園區，subnet是不同街區，route table是每個路口的指示牌，Internet Gateway則是通往公共道路的出口。 這只是起點，因為街區叫private不會產生魔法；是否能上網仍由有效route、public address與安全規則共同決定。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Amazon VPC承接主要責任，以Internet Gateway檢查替代條件，並用「Internet-facing資源放可達IGW的subnet；private workload只保留必要出口與內部路由。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：ALB必須公開，但應用與資料庫不得接受internet直接連線。

Internet
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
IGW不會讓所有VPC資源自動公開；仍需public route、public address與允許規則同時成立。

失敗時先找：只把subnet命名private卻保留0.0.0.0/0到IGW與public IP。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問Amazon VPC有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon VPC和Internet Gateway並不是兩個任意的產品名稱。前者適合本章，是因為「Internet-facing資源放可達IGW的subnet；private workload只保留必要出口與內部路由。」直接回應了眼前的問題；後者描述的「Private subnet可經NAT對外發起連線，但internet不能藉此主動建立到instance的連線。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只把subnet命名private卻保留0.0.0.0/0到IGW與public IP。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「derive exposure from effective routes and addresses」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 |
| Internet Gateway | 讓具有public IP的VPC資源與Internet雙向通訊。 | IGW是水平擴展的VPC gateway，對instance public IPv4做一對一NAT並依route傳遞。 |
| Route tables | 決定subnet或gateway流量的下一跳。 | 先匹配目的CIDR，再選最長prefix；local route允許VPC內互通，其他target可為IGW/NAT/TGW/endpoint。 |

## 把全圖套進一個具體案例

**場景：** ALB必須公開，但應用與資料庫不得接受internet直接連線。

1. 故事的起點：ALB必須公開，但應用與資料庫不得接受internet直接連線。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon VPC負責「建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Internet Gateway、Route tables各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只把subnet命名private卻保留0.0.0.0/0到IGW與public IP。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

### 三張 Route Table

| Route table | 關聯 subnet | Destination | Target | 效果 |
| --- | --- | --- | --- | --- |
| public-rt | Public A/B | `10.20.0.0/16` | `local` | VPC 內部互通 |
| public-rt | Public A/B | `0.0.0.0/0` | `igw-0123` | 具備 Internet 路徑；資源仍需 public address |
| app-rt-a | Private app A | `10.20.0.0/16` | `local` | ALB、app、DB 走 private IP |
| app-rt-a | Private app A | `0.0.0.0/0` | `nat-0abc` | App 可主動出站，Internet 不能主動連入 |
| db-rt | Isolated DB A/B | `10.20.0.0/16` | `local` | DB 沒有 Internet default route |

IGW 附掛在 VPC 邊界，不是 public 與 private subnet 中間的路由器。兩者差異來自 route table、resource public address 與 security policy。

## 需要時再查：四個閱讀支點

### Amazon VPC

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Public/private不是subnet名稱，而是路由與資源public address共同形成的可達性。
- **具體例子／邊界：** 在「ALB必須公開，但應用與資料庫不得接受internet直接連線。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Internet Gateway

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Private subnet可經NAT對外發起連線，但internet不能藉此主動建立到instance的連線。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只把subnet命名private卻保留0.0.0.0/0到IGW與public IP。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：derive exposure from effective routes and addresses。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### hybrid connectivity

讓on-premises與cloud長期互通的network、DNS、identity與routing設計，不只是建立一條VPN。

### VPC endpoint

讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### hostname

可讀的網路名稱，例如api.example.com；程式先經DNS取得address後才建立TCP/UDP連線。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### CIDR

以10.0.0.0/16這類prefix描述一段IP範圍；prefix越大，範圍越小。重疊CIDR會破壞明確routing。

### NACL

Network ACL，subnet邊界的stateless ordered allow/deny rules；去回程與ephemeral ports要分開允許。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Amazon VPC

- **功用：** 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
- **底層機制：** ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。
- **關鍵設定：** IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
- **選擇時機：** 任何需要私有位址、network segmentation或hybrid connectivity的workload。
- **替換時機：** 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。

### Internet Gateway

- **功用：** 讓具有public IP的VPC資源與Internet雙向通訊。
- **底層機制：** IGW是水平擴展的VPC gateway，對instance public IPv4做一對一NAT並依route傳遞。
- **關鍵設定：** VPC attachment、0.0.0.0/0或::/0 route、public IP/EIP、SG與NACL return path。
- **選擇時機：** public load balancer、bastion或真正需要直接Internet入口的資源。
- **替換時機：** private instances只需outbound IPv4時使用NAT Gateway；AWS service存取優先用VPC endpoint。

### Route tables

- **功用：** 決定subnet或gateway流量的下一跳。
- **底層機制：** 先匹配目的CIDR，再選最長prefix；local route允許VPC內互通，其他target可為IGW/NAT/TGW/endpoint。
- **關鍵設定：** destination CIDR/prefix list、target、association、propagation、blackhole與return route。
- **選擇時機：** 建立public/private/inspection/hybrid data path與故障隔離時。
- **替換時機：** 需要application-aware routing時使用ALB、API Gateway或service mesh，而不是L3 route。

## 考前與實作時再查：設定操作手冊

### Amazon VPC：逐項設定說明

#### `IPv4／IPv6 CIDR`

- **控制什麼：** 定義VPC可分配的IP位址範圍；subnet必須從這個範圍切割。CIDR重疊會讓peering、TGW與hybrid routing難以判斷封包目的地。
- **何時需要：** 建立新環境、預留成長空間，或未來要連接其他VPC與on-premises時先決定。
- **怎麼設定／驗證：** 建立VPC時設定CidrBlock；要擴充可加入secondary CIDR。先以IPAM或地址表檢查所有既有network，避免只看目前一個帳號。
- **常見錯法：** 把每個VPC都設成10.0.0.0/16很快會重疊；CIDR很大也不代表subnet、route與安全邊界設計良好。

#### `subnets`

- **控制什麼：** 把VPC位址切成單一AZ內的部署與route-table邊界。Subnet本身不叫public或private，真正差異是route與resource是否有public IP。
- **何時需要：** 需要跨AZ高可用、分隔web/app/data tiers，或建立inspection、egress與endpoint subnets時。
- **怎麼設定／驗證：** 為每個AZ建立獨立subnet並關聯明確route table；private subnet不要自動分配public IP，並預留足夠可用地址給ENI與擴展。
- **常見錯法：** 只建立兩個名稱叫public/private的subnet卻共用錯誤route table，會讓資料庫意外取得internet path或讓app無法出站。

#### `route tables`

- **控制什麼：** 依目的CIDR做longest-prefix match並選擇下一跳，例如local、IGW、NAT、TGW、peering connection或VPC endpoint。
- **何時需要：** 任何跨subnet、Internet、AWS service、VPC或on-premises的封包都要先證明去程與回程route成立。
- **怎麼設定／驗證：** 把route table明確關聯到subnet；新增destination與target後，再到另一側建立return route。使用Flow Logs與reachability analysis驗證實際路徑。
- **常見錯法：** 只有去程route沒有回程route、把private subnet的0.0.0.0/0指到IGW，或忘記更精確route會優先匹配，都是常見故障。

#### `DNS support／DNS hostnames`

- **控制什麼：** EnableDnsSupport控制VPC能否使用Amazon-provided DNS resolver；EnableDnsHostnames控制具有public IPv4的instance是否取得對應DNS hostname。
- **何時需要：** workload用hostname存取AWS service、private hosted zone、service discovery，或要啟用peering DNS resolution時。
- **怎麼設定／驗證：** 在VPC attributes開啟DNS resolution與DNS hostnames，IaC分別使用EnableDnsSupport與EnableDnsHostnames；再設定private hosted zone或Resolver rules。
- **常見錯法：** DNS能把名稱翻成IP，但不會建立route、security group或IAM permission；名稱解析成功仍可能完全連不到目標。

#### `Flow Logs`

- **控制什麼：** 記錄ENI、subnet或VPC層的accepted/rejected flow metadata，用來判斷封包是否到達、被拒絕及走哪個介面。
- **何時需要：** 除錯timeout、驗證segmentation、建立network forensic evidence或流量基線時。
- **怎麼設定／驗證：** 選擇traffic type、aggregation interval、欄位格式與CloudWatch Logs/S3/Firehose destination；先確認service role與retention。
- **常見錯法：** Flow Logs不是packet capture，不會保存payload，也看不到application-level HTTP錯誤；只靠它無法證明IAM或應用程式成功。

### Internet Gateway：逐項設定說明

#### `VPC attachment`

- **控制什麼：** `VPC attachment`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「public load balancer、bastion或真正需要直接Internet入口的資源。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Internet Gateway的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `0.0.0.0/0或::/0 route`

- **控制什麼：** `0.0.0.0/0或::/0 route`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「public load balancer、bastion或真正需要直接Internet入口的資源。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Internet Gateway的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `public IP/EIP`

- **控制什麼：** `public IP/EIP`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「public load balancer、bastion或真正需要直接Internet入口的資源。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Internet Gateway中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `SG`

- **控制什麼：** `SG`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「public load balancer、bastion或真正需要直接Internet入口的資源。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Internet Gateway中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `NACL return path`

- **控制什麼：** `NACL return path`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「public load balancer、bastion或真正需要直接Internet入口的資源。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Internet Gateway中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

### Route tables：逐項設定說明

#### `destination CIDR/prefix list`

- **控制什麼：** `destination CIDR/prefix list`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `target`

- **控制什麼：** `target`指定Route tables讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `association`

- **控制什麼：** `association`控制Route tables的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

#### `propagation`

- **控制什麼：** `propagation`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「建立public/private/inspection/hybrid data path與故障隔離時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route tables的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `blackhole`

- **控制什麼：** `blackhole`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `return route`

- **控制什麼：** `return route`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「建立public/private/inspection/hybrid data path與故障隔離時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route tables的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

## 可以直接對照 AWS 的設定範例

### Public、private app 與 isolated database 的 routes（CloudFormation 節錄）

```yaml
Resources:
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

```

1. 每張route table建立時都會有VPC CIDR → local route；CloudFormation不需再宣告。Public table另外把0.0.0.0/0送到IGW，因此關聯它的subnet具備Internet路徑。
2. NAT Gateway必須位於具有IGW default route的public subnet。Private app table把0.0.0.0/0送到NAT，讓只有private address的instance可以主動出站，但不接受Internet主動建立連線。
3. Database table刻意沒有0.0.0.0/0。資料庫仍可和VPC內app通訊，因為local route存在；若同一isolated tier中的自管maintenance host需要存取AWS API，應明確加入VPC endpoint或受控出口，而不是把整層直接公開。
4. Production應在每個AZ建立NAT與對應private route，避免跨AZ流量費與單一NAT/AZ故障。ALB是否公開還取決於internet-facing scheme、public subnet與security group，不是只有route table。

## 讀到這裡，請用自己的話說一次

1. Amazon VPC的責任：建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
2. 底層機制：ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。
3. 第一個要看的設定：IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
4. 選擇邏輯：Internet-facing資源放可達IGW的subnet；private workload只保留必要出口與內部路由。
5. 不要混淆：Internet Gateway的責任是「讓具有public IP的VPC資源與Internet雙向通訊。」；它不會自動取代Amazon VPC。
6. 替換訊號：跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。
7. 最常見錯法：只把subnet命名private卻保留0.0.0.0/0到IGW與public IP。
8. 可移植原則：derive exposure from effective routes and addresses。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 | 任何需要私有位址、network segmentation或hybrid connectivity的workload。 | 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。 |
| Internet Gateway | 讓具有public IP的VPC資源與Internet雙向通訊。 | IGW是水平擴展的VPC gateway，對instance public IPv4做一對一NAT並依route傳遞。 | public load balancer、bastion或真正需要直接Internet入口的資源。 | private instances只需outbound IPv4時使用NAT Gateway；AWS service存取優先用VPC endpoint。 |
| Route tables | 決定subnet或gateway流量的下一跳。 | 先匹配目的CIDR，再選最長prefix；local route允許VPC內互通，其他target可為IGW/NAT/TGW/endpoint。 | 建立public/private/inspection/hybrid data path與故障隔離時。 | 需要application-aware routing時使用ALB、API Gateway或service mesh，而不是L3 route。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Private subnet可經NAT對外發起連線，但internet不能藉此主動建立到instance的連線。 | 只有當題目條件明確改變時才可能合理。 | 只把subnet命名private卻保留0.0.0.0/0到IGW與public IP。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Private subnet可經NAT對外發起連線，但internet不能藉此主動建立到instance的連線。」之間做選擇。
- 認得常考設定：IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.4 Determine high-performing and/or scalable network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures。

## 本章 10 題考題

### 練習題 1｜SAA｜12.1 Internet 到 EC2 的完整 IPv4 path

EC2 位於一個 subnet，其 route table 有 10.20.0.0/16→local 與 0.0.0.0/0→igw。Instance 有 public IPv4，SG 允許來源 203.0.113.0/24 的 TCP 443。還必須滿足哪個條件，該來源才能成功建立 HTTPS 連線？

A. Internet Gateway 已附加到 VPC，且 subnet NACL 的入站與回程規則允許該 flow
B. 只要 subnet 名稱包含 public，AWS 就會忽略 IGW attachment 與 NACL
C. 在 private subnet 建立 NAT Gateway，讓它接受 Internet 主動入站
D. 替 instance role 增加 ec2:AcceptInternetTraffic

**答案：A**

- **A：** 正確。Public IPv4、到 IGW 的 route、IGW attachment、SG 與 stateless NACL 的雙向規則共同形成可達性。
- **B：** 不正確。Public/private 是有效 route 與地址的結果，不由 Name tag 或 subnet 名稱決定。
- **C：** 不正確。NAT Gateway 支援 private workload 主動出站，不是 Internet-facing server 的入站入口。
- **D：** 不正確。IAM 控制 AWS API，不控制遠端 client 到 ENI 的資料封包。

**事實查證：** [Enable internet access for a VPC using an internet gateway - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)、[Example: VPC with servers in private subnets and NAT - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-example-private-subnets-nat.html)

### 練習題 2｜SAA｜12.2 Public subnet 但無 public IPv4

一台 EC2 位於 route table 含 0.0.0.0/0→igw 的 subnet，但 ENI 只有 10.20.1.25，沒有 public IPv4 或 Elastic IP。它能否直接經 IGW 存取 IPv4 Internet？

A. 可以，IGW 會替所有 private IPv4 自動選一個共享 public address
B. 不可以；對 IPv4 而言還需要 ENI/instance 對應的 public IPv4 或 Elastic IP
C. 可以，只要 SG outbound 允許 443，SG 就會配置 public address
D. 不可以，因為任何含 IGW route 的 subnet 都只允許入站、禁止出站

**答案：B**

- **A：** 不正確。IGW 不會把任意 private-only instance 當成共享 NAT clients。
- **B：** 正確。IGW route 只是 next hop；IPv4 Internet 通訊還需要 public IPv4/EIP 與允許規則。
- **C：** 不正確。SG 是封包政策，不負責地址配置或一對一 public/private IPv4 mapping。
- **D：** 不正確。Public subnet 可雙向通訊；失敗原因是此 instance 缺少 public address，不是 IGW route 禁止出站。

**事實查證：** [Enable internet access for a VPC using an internet gateway - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)

### 練習題 3｜SAA｜12.3 Private app、NAT 與 local route（選兩項）

App subnet 的 route table 有 10.20.0.0/16→local、0.0.0.0/0→NAT；DB subnet 只有 10.20.0.0/16→local。App 需下載更新並連 DB。哪兩個敘述正確？

A. App 對 IPv4 Internet 發起的連線會匹配 default route 並送往 NAT
B. Internet client 可使用 NAT 的 public IP 主動連到任意 app instance
C. App 到同 VPC DB 的流量匹配較具體的 local route，不會繞 NAT
D. DB 沒有 default route，因此 App 也不能連到 DB
E. 所有 App→DB response 都必須由 IGW 回傳

**答案：A、C**

- **A：** 正確。目的地不在 VPC local CIDR 時會匹配 0.0.0.0/0，NAT 處理主動 egress flow。
- **B：** 不正確。NAT 不接受 Internet 未經請求的入站連線；它只回傳已建立 translation state 的 response。
- **C：** 正確。Longest-prefix match 使 10.20.0.0/16 比 default route 更優先，VPC 內流量走 local。
- **D：** 不正確。DB 與 App 同在 VPC CIDR；DB 的 local route 足以形成回程，不需要 Internet default。
- **E：** 不正確。VPC 內 private traffic 經 local route，不應送到 IGW。

**事實查證：** [How route priority works - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)、[Example: VPC with servers in private subnets and NAT - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-example-private-subnets-nat.html)

### 練習題 4｜SAA｜12.4 Longest-prefix match

某 subnet route table 同時有 0.0.0.0/0→nat-1、10.40.0.0/16→tgw-1、10.40.8.0/24→pcx-1。目的位址為 10.40.8.25 時會選哪個 next hop？

A. nat-1，因為 default route 是所有路由的第一順位
B. tgw-1，因為 Transit Gateway 功能比 Peering 多
C. pcx-1，因為 /24 是三條 matching routes 中最具體的 prefix
D. 建立時間最早的 route，因為 VPC route table 依插入順序

**答案：C**

- **A：** 不正確。Default route只在沒有更具體prefix時使用；只要目的位址符合/16或/24，路由器就不會選0.0.0.0/0。
- **B：** 不正確。服務型別不會勝過更具體 prefix；route selection 先做 longest-prefix match。
- **C：** 正確。10.40.8.25同時符合三條route，而/24涵蓋的目的範圍最小，比/16與/0更具體，因此依longest-prefix match被選中。
- **D：** 不正確。VPC route table 不以建立時間或畫面順序決定一般 route 優先權。

**事實查證：** [How route priority works - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)

### 練習題 5｜SAA｜12.5 Main route table association

工程師建立了一張新的 route table，但沒有把 application subnet 明確關聯到它。該 subnet 實際會使用哪張 route table？

A. 名稱與 subnet 最相近的 route table
B. VPC 內所有 route tables 的聯集
C. 沒有 route table，因此連 local route 也不存在
D. VPC 的 main route table，直到建立 explicit association

**答案：D**

- **A：** 不正確。Name tag 不參與 route-table association。
- **B：** 不正確。每個 subnet 同一時間只使用一張 associated route table，不會合併多張表。
- **C：** 不正確。未明確關聯的 subnet 會隱式使用 main route table。
- **D：** 正確。這也表示修改 main route table 可能同時影響所有仍採 implicit association 的 subnets。

**事實查證：** [Configure route tables - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)

### 練習題 6｜SAA｜12.6 Internet-facing ALB 的 subnet path

一個 Internet-facing ALB 選了 AZ-a 與 AZ-b 的兩個 subnets。AZ-a 的 route table 有 0.0.0.0/0→IGW，AZ-b 的 route table 只有 local route。如何修正架構？

A. 只需把 ALB security group 再加入一條 0.0.0.0/0，route table 不影響 ALB
B. 讓 AZ-b 的 default route 指向 AZ-a 的 NAT Gateway
C. 為 AZ-b 的 ALB subnet 關聯具有 0.0.0.0/0→IGW 的 public route table，並確認 NACL/SG 回程
D. 把 AZ-b subnet 名稱改成 public-b，AWS 會自動加入 route

**答案：C**

- **A：** 不正確。SG 只決定允許的 flow，不能替缺少 IGW next hop 的 subnet 建立 Internet path。
- **B：** 不正確。NAT Gateway 是 private egress，不能成為 Internet-facing ALB node 的公開入站路徑。
- **C：** 正確。Internet-facing ALB 使用的每個 AZ/subnet 都需要有效 public routing 與網路政策。
- **D：** 不正確。Subnet 名稱不會改變 route-table association 或建立 IGW route。

**事實查證：** [Enable internet access for a VPC using an internet gateway - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)、[Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html#subnets-load-balancer)

### 練習題 7｜SAA｜12.7 IPv6 outbound-only Internet

雙棧 private workload 需要直接使用 IPv6 對 Internet 發起連線，但不能接受 Internet 主動建立的 IPv6 connection。應在 subnet route table 配置什麼？

A. ::/0→IPv4 NAT Gateway
B. ::/0→一般 IGW，因為 IGW 會自動拒絕所有 IPv6 入站
C. ::/0→egress-only Internet Gateway，並保留適當 SG/NACL rules
D. 刪除所有 IPv6 routes，因為沒有 route 仍能主動出站

**答案：C**

- **A：** 不正確。原生 IPv6 outbound-only 模型使用 egress-only Internet Gateway；IPv4 NAT 的一般路由不是此用途。
- **B：** 不正確。一般 IGW 提供可路由的雙向路徑，是否允許入站還取決於 policies，並非 outbound-only 元件。
- **C：** 正確。Egress-only IGW 允許 VPC 端主動建立 IPv6 connection，並阻止 Internet 端主動開始連線。
- **D：** 不正確。沒有可匹配的 IPv6 route，封包就沒有 Internet next hop。

**事實查證：** [Enable outbound IPv6 traffic using an egress-only internet gateway - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html)

### 練習題 8｜SAA｜12.8 Blackhole route

部署後某 route 顯示 blackhole，目的網段所有連線都 timeout。哪個原因最符合這個狀態？

A. DNS TTL 過高，所以 route table 無法載入
B. ALB stickiness 把 client 固定到 unhealthy target
C. IAM role 缺少 ec2:UseRoute 權限
D. 該 route 指向的 peering connection、NAT 或其他 target 已刪除或不可用

**答案：D**

- **A：** 不正確。DNS cache 可能導向舊 IP，但不會把 VPC route 的狀態標成 blackhole。
- **B：** 不正確。Stickiness 影響 ALB target selection，不會改變 L3 route 狀態。
- **C：** 不正確。資料封包不逐次呼叫 IAM API，也沒有 ec2:UseRoute 這種資料面授權。
- **D：** 正確。Blackhole 表示 route 的 target 不再有效；應先修復或替換 next hop，再檢查 return path。

**事實查證：** [Configure route tables - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)

### 練習題 9｜SAP｜12.9 Route change 的 blast radius

中央網路帳號要把數百個 spoke subnets 的 default route 從舊 inspection path 切到新 path。哪種 rollout 最能降低 production blast radius？

A. 將 route 變更版本化，先在 canary VPC/subnet 驗證 forward/return path與 Flow Logs，再分批推出並保留可回復的舊 route
B. 一次修改所有 main route tables，只檢查 CloudFormation 顯示 UPDATE_COMPLETE
C. 先把所有 NACL 改成 allow all，避免 route 變更失敗
D. 只降低 Route 53 TTL，因為 DNS 會替 subnet 選擇 next hop

**答案：A**

- **A：** 正確。Route 是共享資料面控制；canary、雙向驗證、分波與 rollback 能限制錯誤 next hop 的影響範圍。
- **B：** 不正確。Control-plane 成功不證明 packet path、stateful inspection 或 return route 正確。
- **C：** 不正確。移除NACL安全邊界不能修復錯誤routing或next hop，反而會在切換期間擴大所有spoke subnet的暴露面。
- **D：** 不正確。DNS 選 IP，subnet route table 才依目的 prefix 選 next hop。

**事實查證：** [Configure route tables - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)、[Logging IP traffic using VPC Flow Logs - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)

### 練習題 10｜SAP｜12.10 失效回程路由除錯（選兩項）

App 連 DB 持續 timeout。DNS 已解析，SG/NACL 也允許。去程 10.50.0.0/16 經 TGW；舊 VPC Peering 已刪除，但 DB subnet 回到 App CIDR 的 route 仍指向該 peering並顯示 blackhole。哪兩個動作最合適？

A. 增加 DNS TTL，讓 client 更久使用目前 DB IP
B. 把 DB 端回到 App CIDR 的 route 改為可達 App 的 TGW attachment，並確認 TGW雙向 route tables都含正確 prefix
C. 替 DB 加 public IPv4，讓 response 改走 IGW
D. 使用 Flow Logs、Reachability Analyzer 或逐 hop route 檢查確認去回程實際選擇
E. 提高 ALB idle timeout，即使此連線不經 ALB

**答案：B、D**

- **A：** 不正確。名稱已正確解析，增加 DNS TTL 只延長 resolver cache，無法把指向已刪除 peering 的 blackhole route變成有效 next hop。
- **B：** 正確。雙向 TCP 通信需要有效回程；DB subnet route與相關 TGW route table都必須把 App CIDR導向實際存在的 attachment，不能留下已刪除 peering target。
- **C：** 不正確。替 DB 加 public IPv4沒有修正 private return path，且會擴大資料庫暴露面；題目要求應在既有私有連線拓撲內修復。
- **D：** 正確。Flow Logs可顯示 accept/reject與介面流量，Reachability Analyzer可依配置模型指出阻斷元件；逐 hop檢查則能確認 blackhole route正是失敗點。
- **E：** 不正確。這條 App-to-DB TCP path不經 ALB，因此 ALB idle timeout不參與連線；即使提高數值也無法修復不存在的回程路由。

**事實查證：** [Configure route tables - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)、[Logging IP traffic using VPC Flow Logs - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)、[What is Reachability Analyzer? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Internet-facing資源放可達IGW的subnet；private workload只保留必要出…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Public/private不是subnet名稱，而是路由與資源public address共同形成的可達性。」，所以「Internet-facing資源放可達IGW的subnet；private workload只保留必要出口與內部路由。」能直接滿足它；若constraint改成「Private subnet可經NAT對外發起連線，但internet不能藉此主動建立到instance的連線。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Internet-facing資源放可達IGW的subnet；private workload只保留必要出口與內部路由。」。替代方案「Private subnet可經NAT對外發起連線，但internet不能藉此主動建立到instance的連線。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只把subnet命名private卻保留0.0.0.0/0到IGW與public IP。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Public/private不是subnet名稱，而是路由與資源public address共同形成的可達性。」，排除會導致「只把subnet命名private卻保留0.0.0.0/0到IGW與public IP。」的選項，再選「Internet-facing資源放可達IGW的subnet；private workload只保留必要出口與內部路由。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.4 Determine high-performing and/or scalable network architectures；SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Internet-facing資源放可達IGW的subnet；private workload只保留必要出口與內部路由。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「derive exposure from effective routes and addresses」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 13 章　NAT Gateway、Egress 與 VPC Endpoints

Private workload仍需更新套件、呼叫AWS API或外部服務，出口路徑影響安全與成本。

## 跟著一個封包走：先從故事開始

故事從一個看似簡單的需求開始：數百台private EC2大量讀S3，偶爾需下載internet套件。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：Private workload仍需更新套件、呼叫AWS API或外部服務，出口路徑影響安全與成本。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把網路想成城市交通：DNS找地址，route選道路，security rules決定哪扇門能進。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，NAT Gateway會是本章的主要角色，AWS PrivateLink則幫我們看清邊界。方向是「AWS服務優先用gateway/interface endpoint；一般IPv4 internet egress再使用每AZ NAT。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：數百台private EC2大量讀S3，偶爾需下載internet套件。

來源（使用者／VPC／on-premises）
          │ ① 名稱解析：要連到哪個位址？
          │ ② 去程 route + network policy
          ▼
[NAT Gateway]
          │ 讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。
          ▼
[target／application state]
          │ ③ response沿有效回程返回
控制面：建立DNS、route、listener、policy與health設定
資料面：每個packet／connection／request實際沿路通過
本章其他角色：
  · AWS PrivateLink：以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。
  · VPC endpoints：讓VPC私下存取AWS服務，不經IGW或NAT。
  · Amazon S3：以HTTP API保存object，提供高durability、彈性namespace與多種storage…

失敗時先找：所有S3流量繞NAT，造成不必要處理費與單一AZ依賴。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問NAT Gateway有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，NAT Gateway和AWS PrivateLink並不是兩個任意的產品名稱。前者適合本章，是因為「AWS服務優先用gateway/interface endpoint；一般IPv4 internet egress再使用每AZ NAT。」直接回應了眼前的問題；後者描述的「集中NAT可減少gateway數量，但增加跨AZ/Transit成本、路由複雜度與共同故障面。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：所有S3流量繞NAT，造成不必要處理費與單一AZ依賴。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「keep private traffic private and local when practical」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| NAT Gateway | 讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。 | 在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。 |
| AWS PrivateLink | 以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。 | Provider以NLB和endpoint service發布；consumer在自己的subnet取得endpoint ENI。 |
| VPC endpoints | 讓VPC私下存取AWS服務，不經IGW或NAT。 | Gateway endpoint把S3/DynamoDB prefix route加入route table；interface endpoint以PrivateLink ENI與private DNS接服務。 |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 |

## 把全圖套進一個具體案例

**場景：** 數百台private EC2大量讀S3，偶爾需下載internet套件。

1. 故事的起點：數百台private EC2大量讀S3，偶爾需下載internet套件。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：NAT Gateway負責「讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS PrivateLink、VPC endpoints、Amazon S3各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「所有S3流量繞NAT，造成不必要處理費與單一AZ依賴。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### NAT Gateway

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Private workload仍需更新套件、呼叫AWS API或外部服務，出口路徑影響安全與成本。
- **具體例子／邊界：** 在「數百台private EC2大量讀S3，偶爾需下載internet套件。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS PrivateLink

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：集中NAT可減少gateway數量，但增加跨AZ/Transit成本、路由複雜度與共同故障面。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：所有S3流量繞NAT，造成不必要處理費與單一AZ依賴。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：keep private traffic private and local when practical。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### VPC endpoint

讓VPC私下存取AWS service的入口；gateway與interface endpoint的route、DNS與policy機制不同。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### CIDR

以10.0.0.0/16這類prefix描述一段IP範圍；prefix越大，範圍越小。重疊CIDR會破壞明確routing。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### NAT Gateway

- **功用：** 讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。
- **底層機制：** 在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。
- **關鍵設定：** public/private NAT type、subnet、EIP、per-AZ route、connection/port capacity與CloudWatch metrics。
- **選擇時機：** private workload必須下載更新或呼叫無private endpoint的public API時。
- **替換時機：** S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。

### AWS PrivateLink

- **功用：** 以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。
- **底層機制：** Provider以NLB和endpoint service發布；consumer在自己的subnet取得endpoint ENI。
- **關鍵設定：** endpoint service acceptance、allowed principals、NLB、interface endpoint subnets/SG、private DNS。
- **選擇時機：** SaaS、跨帳號服務、CIDR重疊或只需單向client-to-service連線時。
- **替換時機：** 需要VPC任意IP雙向互通用Peering/TGW；需要L7服務網路可評估VPC Lattice。

### VPC endpoints

- **功用：** 讓VPC私下存取AWS服務，不經IGW或NAT。
- **底層機制：** Gateway endpoint把S3/DynamoDB prefix route加入route table；interface endpoint以PrivateLink ENI與private DNS接服務。
- **關鍵設定：** service name、endpoint type、subnets、security groups、private DNS、route tables與endpoint policy。
- **選擇時機：** 要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。
- **替換時機：** VPC間完整雙向routing選Peering/TGW；只發布特定服務選PrivateLink。

### Amazon S3

- **功用：** 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。
- **底層機制：** Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。
- **關鍵設定：** bucket type、Object Ownership、Block Public Access、bucket policy、default encryption、versioning、lifecycle與replication。
- **選擇時機：** static assets、backup、logs、data lake、media與write-once/read-many資料。
- **替換時機：** 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。

## 考前與實作時再查：設定操作手冊

### NAT Gateway：逐項設定說明

#### `public/private NAT type`

- **控制什麼：** `public/private NAT type`選擇NAT Gateway的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `subnet`

- **控制什麼：** `subnet`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「private workload必須下載更新或呼叫無private endpoint的public API時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在NAT Gateway的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `EIP`

- **控制什麼：** Elastic IP是帳號/Region內可重新關聯的static public IPv4；public NAT Gateway使用它作Internet看到的source address。
- **何時需要：** 外部allowlist要求固定egress IPv4，或resource replacement後仍需保留相同public address時。
- **怎麼設定／驗證：** 先allocate EIP，再建立public NAT Gateway於具有IGW route的public subnet並指定AllocationId；每個AZ使用自己的NAT/EIP。
- **常見錯法：** 單一EIP/NAT跨AZ共用會形成failure/cost path；EIP稀缺且可能收費，也不提供incoming access到private instances。

#### `per-AZ route`

- **控制什麼：** `per-AZ route`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署NAT Gateway前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `connection/port capacity`

- **控制什麼：** `connection/port capacity`指定NAT Gateway讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `CloudWatch metrics`

- **控制什麼：** `CloudWatch metrics`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「private workload必須下載更新或呼叫無private endpoint的public API時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在NAT Gateway選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

### AWS PrivateLink：逐項設定說明

#### `endpoint service acceptance`

- **控制什麼：** 控制provider是否必須逐一接受consumer建立的interface endpoint connection request；它是連線核准，不是封包路由設定。
- **何時需要：** Provider只信任特定consumer、需要人工／自動審批，或allowed principals範圍較廣但仍要二次確認時。
- **怎麼設定／驗證：** 建立endpoint service時設定AcceptanceRequired；收到request後由provider accept/reject。若關閉，任何已被allowed principals授權的request會自動接通。
- **常見錯法：** AcceptanceRequired=false不代表公開給所有人；consumer仍須先符合allowed principals。已接受也不會自動放行NLB target、SG或private DNS。

#### `allowed principals`

- **控制什麼：** 指定哪些AWS accounts、roles、users或organization principals有資格建立連到endpoint service的interface endpoint。
- **何時需要：** 跨帳號SaaS、中央平台服務或只允許organization內特定consumer使用時。
- **怎麼設定／驗證：** 在endpoint service permissions加入具體principal ARN；搭配acceptance policy決定自動或人工核准，並以未授權account做反向測試。
- **常見錯法：** 授權整個organization再關閉acceptance會擴大consumer範圍；這也只授權建立連線，不等於後端application已完成身份驗證。

#### `provider NLB`

- **控制什麼：** Network Load Balancer是endpoint service的provider入口，把PrivateLink連線導向實際service targets，同時隱藏provider VPC的完整route domain。
- **何時需要：** 要發布TCP/TLS服務、支援大量連線，或consumer與provider CIDR重疊而不能建立一般routing時。
- **怎麼設定／驗證：** 建立internal NLB與healthy target groups，再用它建立endpoint service；逐AZ開啟服務並驗證target health、listener port及capacity。
- **常見錯法：** NLB target不健康時endpoint仍可能建立成功但request失敗；PrivateLink也不是任意VPC-to-VPC雙向連線。

#### `interface endpoint subnets／SG`

- **控制什麼：** Consumer在每個選定AZ建立endpoint ENI與private IP；security group控制clients可連入該ENI的protocol與port。
- **何時需要：** Consumer要由多個AZ私下存取service，並將入口限制在特定application security groups時。
- **怎麼設定／驗證：** 選擇每個需要的AZ/subnet並附least-privilege SG；client DNS解析後應得到endpoint ENI地址，再逐AZ測試route、SG與回應。
- **常見錯法：** 只在單一AZ建立endpoint會形成可用性與跨AZ成本問題；SG附錯方向或port時，DNS正常但TCP仍會timeout。

#### `private DNS`

- **控制什麼：** 讓consumer使用provider驗證過的自訂service hostname時，VPC resolver把該名稱解析成interface endpoint private IP，而非public endpoint。
- **何時需要：** 希望application沿用穩定名稱，不暴露vpce-* DNS名稱，或同一SDK hostname在VPC內自動走PrivateLink時。
- **怎麼設定／驗證：** Provider設定並驗證private DNS name的domain ownership；consumer endpoint啟用private DNS，且VPC開啟DNS support/hostnames，再用dig驗證。
- **常見錯法：** Private DNS只改名稱答案，不會建立SG、後端authorization或跨VPC route；同名private hosted zone也可能遮蔽預期答案。

### VPC endpoints：逐項設定說明

#### `service name`

- **控制什麼：** `service name`指定VPC endpoints依賴的runtime integration、scheduler限制、proxy相容性或要連接的AWS endpoint。
- **何時需要：** Managed control plane仍需要local agent、cluster extension、placement constraint或具名service integration時。
- **怎麼設定／驗證：** 鎖定版本與service identifier，配置network/IAM，先在非production驗證compatibility；taint同時配置對應toleration。
- **常見錯法：** Agent/add-on版本落後會造成同步或network問題；只設taint沒有toleration會讓pods無法排程，service name選錯Region也無法連線。

#### `endpoint type`

- **控制什麼：** `endpoint type`選擇VPC endpoints的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `subnets`

- **控制什麼：** `subnets`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在VPC endpoints的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `security groups`

- **控制什麼：** `security groups`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在VPC endpoints中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `private DNS`

- **控制什麼：** `private DNS`控制名稱如何被解析或驗證；DNS只把名稱轉成目標資料，不會替代route、network policy或IAM。
- **何時需要：** 當需求符合「要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在VPC endpoints的DNS／domain設定中明確指定zone、name、resolver direction或validation方式，並用dig/nslookup從實際來源網路驗證答案。
- **常見錯法：** 只在console看到名稱存在，不代表所有VPC、Region與client都得到同一答案；還要檢查cache TTL、zone association與return path。

#### `route tables`

- **控制什麼：** `route tables`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在VPC endpoints的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `endpoint policy`

- **控制什麼：** `endpoint policy`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在VPC endpoints的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

### Amazon S3：逐項設定說明

#### `bucket type`

- **控制什麼：** `bucket type`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `Object Ownership`

- **控制什麼：** `Object Ownership`控制S3 object ownership、版本轉層/刪除或WORM retention，是資料安全與生命週期contract。
- **何時需要：** 需要停用legacy ACL、降低長期儲存成本、清理未完成upload，或法規要求保留不可刪資料時。
- **怎麼設定／驗證：** 在Amazon S3設定BucketOwnerEnforced、Lifecycle Filter/Transitions/Expiration，或Object Lock mode與retain-until；先用inventory估算影響。
- **常見錯法：** Lifecycle是非同步且可能有最低儲存期費用；Compliance retention到期前通常不能縮短，和普通backup retention不同。

#### `Block Public Access`

- **控制什麼：** `Block Public Access`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「static assets、backup、logs、data lake、media與write-once/read-many資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `bucket policy`

- **控制什麼：** `bucket policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「static assets、backup、logs、data lake、media與write-once/read-many資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `default encryption`

- **控制什麼：** `default encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「static assets、backup、logs、data lake、media與write-once/read-many資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `versioning`

- **控制什麼：** `versioning`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「static assets、backup、logs、data lake、media與write-once/read-many資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `lifecycle`

- **控制什麼：** `lifecycle`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「static assets、backup、logs、data lake、media與write-once/read-many資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `replication`

- **控制什麼：** `replication`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「static assets、backup、logs、data lake、media與write-once/read-many資料。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon S3依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

## 讀到這裡，請用自己的話說一次

1. NAT Gateway的責任：讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。
2. 底層機制：在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。
3. 第一個要看的設定：public/private NAT type、subnet、EIP、per-AZ route、connection/port capacity與CloudWatch metrics。
4. 選擇邏輯：AWS服務優先用gateway/interface endpoint；一般IPv4 internet egress再使用每AZ NAT。
5. 不要混淆：AWS PrivateLink的責任是「以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。」；它不會自動取代NAT Gateway。
6. 替換訊號：S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。
7. 最常見錯法：所有S3流量繞NAT，造成不必要處理費與單一AZ依賴。
8. 可移植原則：keep private traffic private and local when practical。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| NAT Gateway | 讓private subnet的IPv4資源主動對外，拒絕Internet主動建立的入站連線。 | 在特定AZ配置NAT並以source NAT轉換connection；private route把default route指向NAT。 | private workload必須下載更新或呼叫無private endpoint的public API時。 | S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。 |
| AWS PrivateLink | 以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。 | Provider以NLB和endpoint service發布；consumer在自己的subnet取得endpoint ENI。 | SaaS、跨帳號服務、CIDR重疊或只需單向client-to-service連線時。 | 需要VPC任意IP雙向互通用Peering/TGW；需要L7服務網路可評估VPC Lattice。 |
| VPC endpoints | 讓VPC私下存取AWS服務，不經IGW或NAT。 | Gateway endpoint把S3/DynamoDB prefix route加入route table；interface endpoint以PrivateLink ENI與private DNS接服務。 | 要求private connectivity、降低NAT成本或用endpoint policy建立額外data perimeter時。 | VPC間完整雙向routing選Peering/TGW；只發布特定服務選PrivateLink。 |
| Amazon S3 | 以HTTP API保存object，提供高durability、彈性namespace與多種storage classes。 | Bucket位於Region；key定位object，prefix是名稱慣例而非真正directory；PUT取代整個object。 | static assets、backup、logs、data lake、media與write-once/read-many資料。 | 需要block device/in-place writes選EBS；共享POSIX/NFS語意選EFS/FSx。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 集中NAT可減少gateway數量，但增加跨AZ/Transit成本、路由複雜度與共同故障面。 | 只有當題目條件明確改變時才可能合理。 | 所有S3流量繞NAT，造成不必要處理費與單一AZ依賴。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「集中NAT可減少gateway數量，但增加跨AZ/Transit成本、路由複雜度與共同故障面。」之間做選擇。
- 認得常考設定：public/private NAT type、subnet、EIP、per-AZ route、connection/port capacity與CloudWatch metrics。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：S3/DynamoDB使用gateway endpoint、其他AWS服務使用interface endpoint，可減少NAT cost與failure dependency。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-2.3 Determine security controls based on requirements；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜13.1 S3 gateway endpoint 與 Internet egress（選兩項）

Private EC2 每天從同 Region S3 讀取數 TB 資料，偶爾也要從公共套件網站下載更新。公司希望減少 NAT data processing cost，且 EC2 不得有 public IP。哪兩項設定最合適？

A. 建立 S3 gateway endpoint，將 private subnet route tables 關聯到 endpoint，並用 endpoint/bucket policy限制核准 bucket
B. 讓所有 S3 與 Internet 流量都走單一 NAT Gateway，因為 endpoint 不能降低傳輸費
C. 保留 0.0.0.0/0 到可用 NAT 的路徑，供沒有 private endpoint 的公共網站使用
D. 建立 VPC Peering 到 S3 service VPC
E. 為每台 EC2 配 Elastic IP，讓 S3 response 直接回 instance

**答案：A、C**

- **A：** 正確。Gateway endpoint 會以 AWS managed prefix list route 將 S3 流量留在 AWS 網路，且可疊加 endpoint policy。
- **B：** 不正確。S3 是 gateway endpoint 支援服務；大量 S3 bytes 繞 NAT 會產生不必要的 NAT 依賴與處理費。
- **C：** 正確。一般 public IPv4 destination 仍需要 NAT 或其他 egress path；更具體的 S3 prefix-list route會優先。
- **D：** 不正確。Amazon S3不透過客戶自行建立的VPC Peering提供服務入口；同Region私有存取應使用gateway endpoint等受支援的endpoint類型。
- **E：** 不正確。Public IP 會破壞 private-instance 要求，也不是降低大量 S3 egress 成本的方案。

**事實查證：** [Gateway endpoints - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html)、[NAT gateway basics - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html)

### 練習題 2｜SAA｜13.2 Zonal public NAT 的去回程

EC2 10.0.1.10 位於 private subnet，default route 指向 public NAT Gateway。若要成功連到 Internet 套件站，NAT 所在 subnet 還需要什麼？

A. 只需要 local route；NAT 會繞過 VPC route table
B. 到 IGW 的 default route，且 public NAT 具有 Elastic IP；IGW 也必須附加到 VPC
C. 到 EC2 private IP 的 inbound Internet route
D. 一個 interface endpoint，因為 NAT 只能存取 AWS APIs

**答案：B**

- **A：** 不正確。NAT Gateway 的 upstream packet 仍依所在 subnet route table 選 next hop。
- **B：** 正確。Private subnet 將 flow 送 NAT，public NAT 以 EIP 轉換後再經 public subnet 的 IGW route 出站。
- **C：** 不正確。Internet response 回到 NAT 的 EIP，再由既有 translation state 回到 EC2；不建立 unsolicited inbound route。
- **D：** 不正確。NAT 可連一般 IPv4 Internet；interface endpoint只適用支援 PrivateLink 的服務。

**事實查證：** [NAT gateway basics - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html)、[Example: VPC with servers in private subnets and NAT - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-example-private-subnets-nat.html)

### 練習題 3｜SAA｜13.3 Zonal NAT 的 AZ 隔離

AZ-a 與 AZ-b 的 private subnets 都把 default route 指向 AZ-a 的 zonal NAT Gateway。AZ-a 中斷後，AZ-b 的 instances 也失去 Internet egress。若繼續使用 zonal NAT，應如何改善？

A. 只替原 NAT 多綁一個 EIP，EIP 會把 NAT 移到另一 AZ
B. 開啟 ALB cross-zone load balancing
C. 每個 AZ 建立 NAT Gateway，讓各 private subnet 優先走同 AZ NAT
D. 把 AZ-b default route 指向 IGW，即使 instances 沒有 public IP

**答案：C**

- **A：** 不正確。增加 EIP 可擴展部分 connection capacity，但不改變 zonal failure domain。
- **B：** 不正確。ALB cross-zone 只影響 load balancer target distribution，不會修 NAT egress。
- **C：** 正確。Zonal NAT 的 per-AZ 配置可避免一個 AZ 故障拖累其他 AZ，並減少不必要的 cross-AZ path。
- **D：** 不正確。Private-only IPv4 instance 不能只靠 IGW route 直接上網。

**事實查證：** [NAT gateway basics - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html)

### 練習題 4｜SAP｜13.4 Regional NAT Gateway 現行服務延伸

團隊在支援的 Region 評估新架構，希望由 AWS 管理跨 AZ 的 NAT 可用性，減少每 AZ NAT 與 route 維護。哪個敘述最準確？

A. Regional NAT Gateway 可作為 regional egress 選項；仍要驗證支援 Region、route、EIP/位址需求、quota與費用，不能直接套用 zonal NAT 假設
B. Regional NAT 只是多個 EIP 的別名，沒有獨立 routing 或 HA 行為
C. Regional NAT 接受 Internet 主動建立到 private instance 的連線
D. Regional NAT 已自動納入所有舊版考綱，因此任何 NAT 題都必須選它

**答案：A**

- **A：** 正確。Regional NAT Gateway以單一 regional route target跨 AZ擴展，能配置多個 Elastic IP且不要求放在 public subnet；仍須確認 Region availability、quota、擴展時間與按小時計費方式。
- **B：** 不正確。它具有獨立的 regional NAT gateway ID與route target，會依流量跨 AZ擴展；這些 failure-domain與routing行為不同於只替既有 zonal gateway新增 EIP。
- **C：** 不正確。Regional NAT仍不允許 Internet主動建立到 private workload的連線；它處理由內部發起 flow的位址轉換與回應流量，不是 public ingress gateway。
- **D：** 不正確。Regional NAT於 2025年11月發布，而 SAP-C02較早公布；本題只作 ENRICHMENT-CURRENT，不能把現行服務選項倒推成舊考綱每道 NAT題的唯一答案。

**事實查證：** [Regional NAT gateways - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)、[Introducing Amazon VPC Regional NAT Gateway - AWS Networking & Content Delivery Blog](https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-amazon-vpc-regional-nat-gateway/)、[Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/)

### 練習題 5｜SAA｜13.5 Interface endpoint 的 ENI、SG 與 private DNS

Private EC2 要呼叫同 Region Secrets Manager。團隊建立 interface endpoint 並啟用 private DNS，但連線 timeout。哪個設定最直接控制 client 能否連到 endpoint 的 HTTPS port？

A. Gateway endpoint route table association
B. Endpoint policy中的 IAM Principal，因為它在 TCP handshake 前執行
C. Endpoint ENI 所附 security group 的 inbound TCP 443 規則
D. Internet Gateway 的 0.0.0.0/0 route

**答案：C**

- **A：** 不正確。Gateway endpoint route association 適用 S3/DynamoDB 類型，不是 Secrets Manager interface endpoint。
- **B：** 不正確。Endpoint policy 影響服務 API authorization，不會替被 SG 阻擋的 TCP 建立連線。
- **C：** 正確。Interface endpoint 在所選 subnet 建立 ENI；其 SG 必須允許 client 來源連入服務 port。
- **D：** 不正確。Interface endpoint 走 private IP，不需要 IGW 才能由 VPC client 存取。

**事實查證：** [Access an AWS service using an interface VPC endpoint - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html)

### 練習題 6｜SAP｜13.6 S3 gateway 與 interface endpoint 比較

公司要讓 VPC workloads 及經 Direct Connect 進入 VPC 的 on-premises clients 私下存取 S3。哪個比較正確？

A. Gateway endpoint 與 interface endpoint 都建立 ENI，成本與 DNS 模型完全相同
B. Gateway endpoint 使用 route table/prefix list，主要供該 VPC；interface endpoint 使用 PrivateLink ENI/DNS，可支援需要從 on-premises 經 VPC 私下到達的設計
C. Gateway endpoint 必須附 security group；interface endpoint不能附 SG
D. 兩者都會自動授權所有 S3 buckets

**答案：B**

- **A：** 不正確。Gateway endpoint 是 route target，不建立客戶 subnet ENI；interface endpoint 則建立 ENI並按 endpoint 模型計費。
- **B：** 正確。兩種 endpoint 的 data path 與適用拓撲不同；hybrid DNS與路由需求常使 interface endpoint成為 on-premises 存取選項。
- **C：** 不正確。情況相反：interface endpoint ENI 使用 SG，gateway endpoint以 route table與policy為主。
- **D：** 不正確。Network path 不等於 S3 authorization；IAM、bucket/access-point policy 與 endpoint policy仍共同作用。

**事實查證：** [AWS PrivateLink for Amazon S3 - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)、[Access an AWS service using an interface VPC endpoint - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html)

### 練習題 7｜SAA｜13.7 Endpoint policy 不是授權來源

S3 gateway endpoint policy 允許存取 approved-bucket，但 EC2 role 沒有 s3:GetObject Allow。Bucket policy也沒有額外授權。GetObject 結果為何？

A. 成功，因為 endpoint policy 的 Allow 會授予 role 缺少的 IAM permission
B. 成功，只要 route table有 S3 prefix-list route
C. 失敗；endpoint policy 是額外控制邊界，仍需要 identity或resource policy形成有效 Allow
D. 失敗，但唯一修正是把 bucket 設成 public-read

**答案：C**

- **A：** 不正確。Endpoint policy 不會把未授予的 IAM action直接賦予 principal。
- **B：** 不正確。Route 只建立 reachability，不判斷 role 是否能執行 GetObject。
- **C：** 正確。請求仍受 IAM、resource policy、SCP 等授權評估；任何適用 Deny 也會勝出。
- **D：** 不正確。應給 workload 最小權限並保留 private bucket，無需公開資料。

**事實查證：** [Control access to VPC endpoints using endpoint policies - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html)、[Policies and permissions in Amazon S3 - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-policy-language-overview.html)

### 練習題 8｜SAA｜13.8 Interface endpoint timeout 除錯

EC2 解析標準服務 hostname 時已得到 interface endpoint 的 private IP，但 TCP 443 timeout。下一步最合理的是什麼？

A. 先增加 IAM role permissions，因為 DNS成功後 IAM 會控制 TCP SYN
B. 提高 private hosted zone TTL
C. 新增 IGW，讓 private IP 經 Internet 回傳
D. 檢查 endpoint ENI SG ingress、client SG outbound、NACL、endpoint AZ/subnet與實際 private route

**答案：D**

- **A：** 不正確。IAM 可能在 API 層造成 AccessDenied，但不會讓 TCP handshake 靜默 timeout。
- **B：** 不正確。DNS 已返回預期 private IP，延長 cache 不會建立網路可達性。
- **C：** 不正確。Interface endpoint private IP不應依賴 IGW。
- **D：** 正確。DNS成功只證明名稱解析；TCP timeout 應沿 endpoint ENI 的網路與政策逐層檢查。

**事實查證：** [Access an AWS service using an interface VPC endpoint - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html)、[Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)

### 練習題 9｜SAP｜13.9 NAT port/connection exhaustion

數千台 instances 經同一 zonal NAT 連到同一外部 IP:443，CloudWatch 的 ErrorPortAllocation 上升。應先採取哪個方向？

A. 確認是否為每個 destination 的 concurrent connection/port 壓力，增加 NAT 可用來源位址或分散路徑，能改 private endpoint則避免 NAT
B. 提高 instances 的 CPU，因為 NAT port由 client CPU產生
C. 增加 route table數量，route table會提供新的 source ports
D. 降低 security-group rule數量，SG規則會占用 NAT ports

**答案：A**

- **A：** 正確。ErrorPortAllocation 是 NAT 無法配置新 source port的重要訊號；應處理來源 IP/連線分布或移除可避免的 NAT flow。
- **B：** 不正確。Client CPU可能影響應用，但不會直接增加 NAT Gateway 的 translation port資源。
- **C：** 不正確。Route table只選 next hop，不建立額外 NAT source addresses。
- **D：** 不正確。SG rules不消耗 NAT translation ports。

**事實查證：** [Monitor NAT gateways with Amazon CloudWatch - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway-cloudwatch.html)

### 練習題 10｜SAP｜13.10 集中與分散 egress 取捨（選兩項）

公司比較「每個 VPC 自有 NAT」與「透過 TGW 送到集中 egress/inspection VPC」。哪兩項是必須納入的真實取捨？

A. 集中化一定最便宜，因為 NAT 數量是唯一費用來源
B. 集中方案需計算 TGW processing、cross-AZ 與 NAT per-GB path，並設計所有 return routes
C. 每 VPC NAT 完全沒有營運成本，所以不必用 IaC
D. 集中方案可統一 inspection與 allowlist，但也擴大共享 route或 egress故障的 blast radius
E. 所有 AWS API都必須走 public Internet，因此 VPC endpoints不影響比較

**答案：B、D**

- **A：** 不正確。總成本取決於 gateway-hour、每 GB、TGW與跨 AZ實際路徑，不能只數 NAT數量。
- **B：** 正確。集中 egress多了 transit與可能 cross-AZ hops；去回程、stateful inspection與每 GB計價都要畫出。
- **C：** 不正確。分散方案仍有 route、HA、monitoring與政策一致性的維運責任。
- **D：** 正確。中央控制較一致，但單一錯誤 route、capacity或 inspection policy可同時影響更多 VPC。
- **E：** 不正確。S3/DynamoDB gateway endpoint與其他 interface endpoints常可減少 NAT流量與暴露。

**事實查證：** [Using the NAT gateway with AWS Network Firewall for centralized IPv4 egress - Building a Scalable and Secure Multi-VPC AWS Network Infrastructure](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/using-nat-gateway-with-firewall.html)、[What is AWS Transit Gateway for Amazon VPC? - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)、[AWS PrivateLink concepts - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「AWS服務優先用gateway/interface endpoint；一般IPv4 internet eg…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Private workload仍需更新套件、呼叫AWS API或外部服務，出口路徑影響安全與成本。」，所以「AWS服務優先用gateway/interface endpoint；一般IPv4 internet egress再使用每AZ NAT。」能直接滿足它；若constraint改成「集中NAT可減少gateway數量，但增加跨AZ/Transit成本、路由複雜度與共同故障面。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「AWS服務優先用gateway/interface endpoint；一般IPv4 internet egress再使用每AZ NAT。」。替代方案「集中NAT可減少gateway數量，但增加跨AZ/Transit成本、路由複雜度與共同故障面。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「所有S3流量繞NAT，造成不必要處理費與單一AZ依賴。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Private workload仍需更新套件、呼叫AWS API或外部服務，出口路徑影響安全與成本。」，排除會導致「所有S3流量繞NAT，造成不必要處理費與單一AZ依賴。」的選項，再選「AWS服務優先用gateway/interface endpoint；一般IPv4 internet egress再使用每AZ NAT。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures；SAP-1.1 Architect network connectivity strategies。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「AWS服務優先用gateway/interface endpoint；一般IPv4 internet egress再使用每AZ NAT。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「keep private traffic private and local when practical」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 14 章　Security Group 與 Network ACL

網路控制需要區分資源級stateful規則與subnet級stateless邊界。

## 跟著一個封包走：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：Web tier只接受ALB流量，資料庫只接受app SG，另需封鎖一段惡意CIDR。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：網路控制需要區分資源級stateful規則與subnet級stateless邊界。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把網路想成城市交通：DNS找地址，route選道路，security rules決定哪扇門能進。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Security groups負責主要工作，Network ACLs提醒我們答案不是永遠固定。本章會走向「Security Group作主要allow-list；NACL用於粗粒度subnet防護或明確deny需求。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Web tier只接受ALB流量，資料庫只接受app SG，另需封鎖一段惡意CIDR。

來源（使用者／VPC／on-premises）
          │ ① 名稱解析：要連到哪個位址？
          │ ② 去程 route + network policy
          ▼
[Security groups]
          │ 在ENI層提供stateful allow-only虛擬防火牆。
          ▼
[target／application state]
          │ ③ response沿有效回程返回
控制面：建立DNS、route、listener、policy與health設定
資料面：每個packet／connection／request實際沿路通過
本章其他角色：
  · Network ACLs：在subnet邊界提供stateless、ordered allow/deny規則。
  · Amazon VPC：建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。

失敗時先找：只開啟應用port卻在NACL阻擋回程ephemeral port，造成間歇timeout。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問Security groups有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Security groups和Network ACLs並不是兩個任意的產品名稱。前者適合本章，是因為「Security Group作主要allow-list；NACL用於粗粒度subnet防護或明確deny需求。」直接回應了眼前的問題；後者描述的「SG自動允許已建立連線回程；NACL必須同時允許雙向與ephemeral ports。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只開啟應用port卻在NACL阻擋回程ephemeral port，造成間歇timeout。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「place policy at the narrowest stable boundary」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Security groups | 在ENI層提供stateful allow-only虛擬防火牆。 | 允許的connection回程自動放行；規則可引用CIDR、prefix list或另一SG。 |
| Network ACLs | 在subnet邊界提供stateless、ordered allow/deny規則。 | 入站與出站分開評估，依rule number由小到大首個匹配生效；回程ephemeral ports需明確允許。 |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 |

## 把全圖套進一個具體案例

**場景：** Web tier只接受ALB流量，資料庫只接受app SG，另需封鎖一段惡意CIDR。

1. 故事的起點：Web tier只接受ALB流量，資料庫只接受app SG，另需封鎖一段惡意CIDR。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Security groups負責「在ENI層提供stateful allow-only虛擬防火牆。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：允許的connection回程自動放行；規則可引用CIDR、prefix list或另一SG。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Network ACLs、Amazon VPC各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只開啟應用port卻在NACL阻擋回程ephemeral port，造成間歇timeout。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要explicit deny、subnet邊界或無狀態規則時使用NACL；深度封包檢查用Network Firewall。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Security groups

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：網路控制需要區分資源級stateful規則與subnet級stateless邊界。
- **具體例子／邊界：** 在「Web tier只接受ALB流量，資料庫只接受app SG，另需封鎖一段惡意CIDR。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Network ACLs

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：SG自動允許已建立連線回程；NACL必須同時允許雙向與ephemeral ports。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只開啟應用port卻在NACL阻擋回程ephemeral port，造成間歇timeout。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：place policy at the narrowest stable boundary。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### hybrid connectivity

讓on-premises與cloud長期互通的network、DNS、identity與routing設計，不只是建立一條VPN。

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### explicit Deny

明確拒絕request的policy結果；只要任一applicable policy命中Deny，就會覆蓋Allow。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### hostname

可讀的網路名稱，例如api.example.com；程式先經DNS取得address後才建立TCP/UDP連線。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### CIDR

以10.0.0.0/16這類prefix描述一段IP範圍；prefix越大，範圍越小。重疊CIDR會破壞明確routing。

### NACL

Network ACL，subnet邊界的stateless ordered allow/deny rules；去回程與ephemeral ports要分開允許。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

## 回到 AWS：Components、功用與責任邊界

### Security groups

- **功用：** 在ENI層提供stateful allow-only虛擬防火牆。
- **底層機制：** 允許的connection回程自動放行；規則可引用CIDR、prefix list或另一SG。
- **關鍵設定：** inbound/outbound protocol、port、source/destination、SG referencing與rule descriptions。
- **選擇時機：** 以workload身份控制ALB→app→DB的least-privilege路徑。
- **替換時機：** 需要explicit deny、subnet邊界或無狀態規則時使用NACL；深度封包檢查用Network Firewall。

### Network ACLs

- **功用：** 在subnet邊界提供stateless、ordered allow/deny規則。
- **底層機制：** 入站與出站分開評估，依rule number由小到大首個匹配生效；回程ephemeral ports需明確允許。
- **關鍵設定：** rule number、protocol、port range、CIDR、ALLOW/DENY與ephemeral return ranges。
- **選擇時機：** 需要粗粒度subnet guardrail、封鎖特定CIDR或補充SG時。
- **替換時機：** workload-to-workload身份規則優先SG；L7威脅或stateful inspection使用WAF/Network Firewall。

### Amazon VPC

- **功用：** 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。
- **底層機制：** ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。
- **關鍵設定：** IPv4/IPv6 CIDR、subnets、route tables、DHCP options、DNS support/hostnames、flow logs與tenancy。
- **選擇時機：** 任何需要私有位址、network segmentation或hybrid connectivity的workload。
- **替換時機：** 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。

## 考前與實作時再查：設定操作手冊

### Security groups：逐項設定說明

#### `inbound/outbound protocol`

- **控制什麼：** `inbound/outbound protocol`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「以workload身份控制ALB→app→DB的least-privilege路徑。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Security groups的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `port`

- **控制什麼：** `port`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「以workload身份控制ALB→app→DB的least-privilege路徑。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Security groups的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `source/destination`

- **控制什麼：** `source/destination`指定Security groups讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `SG referencing`

- **控制什麼：** `SG referencing`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「以workload身份控制ALB→app→DB的least-privilege路徑。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Security groups中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `rule descriptions`

- **控制什麼：** `rule descriptions`控制telemetry如何被instrument、標記、分組、保存或由synthetic script產生。
- **何時需要：** 需要把跨服務request、security findings或外部canary結果連成可查詢evidence時。
- **怎麼設定／驗證：** 部署SDK/collector或canary runtime，設定sampling、annotations與artifact destination；避免把高基數或敏感值放入可索引欄位。
- **常見錯法：** 只有daemon沒有application instrumentation不會產生完整trace；過度sampling與高基數metadata會增加成本並拖慢查詢。

### Network ACLs：逐項設定說明

#### `rule number`

- **控制什麼：** `rule number`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「需要粗粒度subnet guardrail、封鎖特定CIDR或補充SG時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Network ACLs以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `protocol`

- **控制什麼：** `protocol`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「需要粗粒度subnet guardrail、封鎖特定CIDR或補充SG時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Network ACLs的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `port range`

- **控制什麼：** `port range`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「需要粗粒度subnet guardrail、封鎖特定CIDR或補充SG時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Network ACLs的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `CIDR`

- **控制什麼：** `CIDR`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「需要粗粒度subnet guardrail、封鎖特定CIDR或補充SG時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Network ACLs的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `ALLOW/DENY`

- **控制什麼：** `ALLOW/DENY`控制artifact不可覆寫、client驗證，或capacity/discount方案如何選擇與面對中斷。
- **何時需要：** Image supply chain、managed broker access，或Spot/Reserved capacity需要可預測風險與成本時。
- **怎麼設定／驗證：** 開啟immutable tags與scan；authentication選IAM/SASL/TLS並測試；Spot使用capacity-optimized與instance diversification，建立checkpoint/termination handling。
- **常見錯法：** 只設max price不能保證Spot capacity；mutable image tag會讓同一版本指向不同內容，authentication也不取代topic/network authorization。

#### `ephemeral return ranges`

- **控制什麼：** `ephemeral return ranges`選擇Network ACLs的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

### Amazon VPC：逐項設定說明

#### `IPv4／IPv6 CIDR`

- **控制什麼：** 定義VPC可分配的IP位址範圍；subnet必須從這個範圍切割。CIDR重疊會讓peering、TGW與hybrid routing難以判斷封包目的地。
- **何時需要：** 建立新環境、預留成長空間，或未來要連接其他VPC與on-premises時先決定。
- **怎麼設定／驗證：** 建立VPC時設定CidrBlock；要擴充可加入secondary CIDR。先以IPAM或地址表檢查所有既有network，避免只看目前一個帳號。
- **常見錯法：** 把每個VPC都設成10.0.0.0/16很快會重疊；CIDR很大也不代表subnet、route與安全邊界設計良好。

#### `subnets`

- **控制什麼：** 把VPC位址切成單一AZ內的部署與route-table邊界。Subnet本身不叫public或private，真正差異是route與resource是否有public IP。
- **何時需要：** 需要跨AZ高可用、分隔web/app/data tiers，或建立inspection、egress與endpoint subnets時。
- **怎麼設定／驗證：** 為每個AZ建立獨立subnet並關聯明確route table；private subnet不要自動分配public IP，並預留足夠可用地址給ENI與擴展。
- **常見錯法：** 只建立兩個名稱叫public/private的subnet卻共用錯誤route table，會讓資料庫意外取得internet path或讓app無法出站。

#### `route tables`

- **控制什麼：** 依目的CIDR做longest-prefix match並選擇下一跳，例如local、IGW、NAT、TGW、peering connection或VPC endpoint。
- **何時需要：** 任何跨subnet、Internet、AWS service、VPC或on-premises的封包都要先證明去程與回程route成立。
- **怎麼設定／驗證：** 把route table明確關聯到subnet；新增destination與target後，再到另一側建立return route。使用Flow Logs與reachability analysis驗證實際路徑。
- **常見錯法：** 只有去程route沒有回程route、把private subnet的0.0.0.0/0指到IGW，或忘記更精確route會優先匹配，都是常見故障。

#### `DNS support／DNS hostnames`

- **控制什麼：** EnableDnsSupport控制VPC能否使用Amazon-provided DNS resolver；EnableDnsHostnames控制具有public IPv4的instance是否取得對應DNS hostname。
- **何時需要：** workload用hostname存取AWS service、private hosted zone、service discovery，或要啟用peering DNS resolution時。
- **怎麼設定／驗證：** 在VPC attributes開啟DNS resolution與DNS hostnames，IaC分別使用EnableDnsSupport與EnableDnsHostnames；再設定private hosted zone或Resolver rules。
- **常見錯法：** DNS能把名稱翻成IP，但不會建立route、security group或IAM permission；名稱解析成功仍可能完全連不到目標。

#### `Flow Logs`

- **控制什麼：** 記錄ENI、subnet或VPC層的accepted/rejected flow metadata，用來判斷封包是否到達、被拒絕及走哪個介面。
- **何時需要：** 除錯timeout、驗證segmentation、建立network forensic evidence或流量基線時。
- **怎麼設定／驗證：** 選擇traffic type、aggregation interval、欄位格式與CloudWatch Logs/S3/Firehose destination；先確認service role與retention。
- **常見錯法：** Flow Logs不是packet capture，不會保存payload，也看不到application-level HTTP錯誤；只靠它無法證明IAM或應用程式成功。

## 可以直接對照 AWS 的設定範例

### ALB → App → Database 的 Security Group chaining

```yaml
Resources:
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

```

1. SG reference表達workload identity；app instance換IP時不必更新CIDR。
2. SG是stateful：已允許connection的回程不需另開ephemeral port。
3. Database不能以0.0.0.0/0開5432；若題目要求explicit deny或subnet boundary才比較NACL。

## 讀到這裡，請用自己的話說一次

1. Security groups的責任：在ENI層提供stateful allow-only虛擬防火牆。
2. 底層機制：允許的connection回程自動放行；規則可引用CIDR、prefix list或另一SG。
3. 第一個要看的設定：inbound/outbound protocol、port、source/destination、SG referencing與rule descriptions。
4. 選擇邏輯：Security Group作主要allow-list；NACL用於粗粒度subnet防護或明確deny需求。
5. 不要混淆：Network ACLs的責任是「在subnet邊界提供stateless、ordered allow/deny規則。」；它不會自動取代Security groups。
6. 替換訊號：需要explicit deny、subnet邊界或無狀態規則時使用NACL；深度封包檢查用Network Firewall。
7. 最常見錯法：只開啟應用port卻在NACL阻擋回程ephemeral port，造成間歇timeout。
8. 可移植原則：place policy at the narrowest stable boundary。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Security groups | 在ENI層提供stateful allow-only虛擬防火牆。 | 允許的connection回程自動放行；規則可引用CIDR、prefix list或另一SG。 | 以workload身份控制ALB→app→DB的least-privilege路徑。 | 需要explicit deny、subnet邊界或無狀態規則時使用NACL；深度封包檢查用Network Firewall。 |
| Network ACLs | 在subnet邊界提供stateless、ordered allow/deny規則。 | 入站與出站分開評估，依rule number由小到大首個匹配生效；回程ephemeral ports需明確允許。 | 需要粗粒度subnet guardrail、封鎖特定CIDR或補充SG時。 | workload-to-workload身份規則優先SG；L7威脅或stateful inspection使用WAF/Network Firewall。 |
| Amazon VPC | 建立Region內可控制CIDR、subnet、route與network policy的邏輯網路。 | ENI取得subnet IP；route table選下一跳；SG/NACL分別在ENI與subnet邊界過濾。 | 任何需要私有位址、network segmentation或hybrid connectivity的workload。 | 跨大量VPC的服務到服務連線可用PrivateLink/VPC Lattice，避免建立完全互通網路。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | SG自動允許已建立連線回程；NACL必須同時允許雙向與ephemeral ports。 | 只有當題目條件明確改變時才可能合理。 | 只開啟應用port卻在NACL阻擋回程ephemeral port，造成間歇timeout。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「SG自動允許已建立連線回程；NACL必須同時允許雙向與ephemeral ports。」之間做選擇。
- 認得常考設定：inbound/outbound protocol、port、source/destination、SG referencing與rule descriptions。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要explicit deny、subnet邊界或無狀態規則時使用NACL；深度封包檢查用Network Firewall。
- 對應官方tasks：SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

## 本章 10 題考題

### 練習題 1｜SAA｜14.1 ALB-App-DB 三層 security-group chain（選兩項）

Internet clients來自 203.0.113.0/24並連 ALB:443；ALB連 App:8080；App連 DB:5432。公司希望 App與DB不依賴容易變動的 instance IP。哪兩組規則合在一起形成完整最小權限 ingress chain？

A. ALB SG inbound TCP 443的source設為203.0.113.0/24；App SG inbound TCP 8080的source設為ALB SG
B. App SG inbound TCP 8080 對 0.0.0.0/0 開放，因為 ALB會先過濾
C. DB SG inbound TCP 5432 的 source設為 App SG
D. DB SG信任整個 public subnet CIDR，讓任何 public resource可連
E. 在 NACL rule中把 ALB SG ID當 source CIDR

**答案：A、C**

- **A：** 正確。第一條限制可接觸 public ALB的client網段，第二條以ALB SG作source，只允許附有該SG的load balancer節點對App:8080建立流量。
- **B：** 不正確。對0.0.0.0/0開放App:8080會讓任何具有route的來源繞過ALB直接嘗試連線，破壞題目要求的ALB-only入口邊界。
- **C：** 正確。DB SG以App SG作source，可讓instance或ENI替換而不必追蹤私有IP；與選項A合併後，三層入口依序為client CIDR、ALB SG、App SG。
- **D：** 不正確。整個public subnet CIDR包含不屬於App角色的資源，授權範圍過寬；subnet的public/private稱呼也不是可驗證的workload identity。
- **E：** 不正確。Network ACL規則只能使用CIDR、protocol與port，不能引用security group ID；而且SG reference只授權流量，不會自行建立任何route。

**事實查證：** [Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)、[Security groups for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-update-security-groups.html)

### 練習題 2｜SAA｜14.2 Security group stateful 回程

App SG outbound允許到 DB:5432，DB SG inbound允許 App SG。DB response回到 App時，是否要在 App SG另加 ephemeral-port inbound rule？

A. 需要，因為所有 VPC firewalls都是 stateless
B. 不需要；SG會自動允許已獲准 connection的 return traffic
C. 需要，但只要把 NACL移除即可由 SG自動產生規則
D. 不需要，因為 ALB stickiness會轉送 DB response

**答案：B**

- **A：** 不正確。Security group是 stateful；NACL才是 stateless、雙向各自評估。
- **B：** 正確。已允許的 outbound connection，其 response可通過 SG connection tracking。
- **C：** 不正確。NACL仍可能阻擋回程；SG也不會修改或產生 NACL rules。
- **D：** 不正確。App到DB的連線不經ALB target group，ALB stickiness只影響client被送往哪個App target，不能授權或修復App-to-DB流量。

**事實查證：** [Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)

### 練習題 3｜SAA｜14.3 NACL ephemeral return ports

Web subnet custom NACL inbound允許 Internet→TCP 443，但 outbound只允許 destination TCP 443。Clients能送 SYN，卻收不到 HTTPS response。最可能缺少什麼？

A. Outbound允許到 client ephemeral destination ports的規則
B. Inbound允許 SSH 22
C. NAT Gateway，因為 public web server response一定要經 NAT
D. IAM permission讓 NACL建立 connection state

**答案：A**

- **A：** 正確。NACL stateless；server response目的通常是 client選用的 ephemeral port，必須在 outbound方向另行允許。
- **B：** 不正確。SSH使用TCP 22，與HTTPS response所需的client ephemeral destination ports無關；增加SSH規則不會讓既有443連線收到回應。
- **C：** 不正確。具有 public IP與 IGW route的 public server不需 NAT回覆 client。
- **D：** 不正確。NACL本身不保存 connection state，也不透過 IAM逐包授權。

**事實查證：** [Control subnet traffic with network access control lists - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)

### 練習題 4｜SAA｜14.4 NACL first-match rule ordering

NACL inbound rule 100允許 203.0.113.0/24 的 TCP 443，rule 110拒絕惡意來源 203.0.113.77/32 的所有流量。該來源連 443會發生什麼？

A. 被拒絕，因為 explicit deny永遠勝過 allow
B. 由 longest-prefix match選 /32 deny
C. 被允許，因為較低 rule number的 100先匹配；應把精確 deny放到更低號碼
D. 由最後建立的 rule決定

**答案：C**

- **A：** 不正確。NACL不是 IAM policy；它以 rule number順序 first match，而非 deny全域優先。
- **B：** 不正確。Longest-prefix match是 route selection概念，不是 NACL規則算法。
- **C：** 正確。Rule 100先匹配 /24後就停止評估，因此 rule 110無法覆寫它。
- **D：** 不正確。Network ACL依rule number由小到大評估並在第一個match停止，規則建立時間不會覆寫數值priority或較早的allow結果。

**事實查證：** [Control subnet traffic with network access control lists - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)

### 練習題 5｜SAA｜14.5 Default 與 custom NACL

工程師把一個正常 subnet從 default NACL改關聯到剛建立、尚未新增規則的 custom NACL。預期結果是什麼？

A. Custom NACL會複製 default NACL並繼續允許全部流量
B. 只影響新建 ENI，既有 connections永遠不受影響
C. Custom NACL會自動匯入該 subnet內所有 SG rules
D. 除非加入允許規則，custom NACL的預設星號規則會拒絕流量

**答案：D**

- **A：** 不正確。新 custom NACL不會複製 default NACL的 allow規則。
- **B：** 不正確。Association改變的是整個 subnet邊界，既有流量也可能受到無狀態規則影響。
- **C：** 不正確。Security group與Network ACL是獨立政策層，custom NACL不會讀取或匯入ENI上的SG規則；剛建立時預設拒絕所有流量。
- **D：** 正確。Custom NACL初始只有不可修改的最後 deny規則；需明確加入 inbound/outbound allows。

**事實查證：** [Control subnet traffic with network access control lists - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)

### 練習題 6｜SAA｜14.6 明確拒絕惡意 CIDR

多個 application SG已允許 corporate 203.0.113.0/24，但其中 203.0.113.77 被確認為惡意來源。需要立即在 subnet邊界封鎖它。應採取什麼？

A. 在每個 SG新增 DENY 203.0.113.77/32
B. 刪除 VPC local route
C. 在合適 NACL用低於 broad allow的 rule number加入 /32 DENY，並評估該 subnet所有 workloads的影響
D. 在 IAM policy加入 aws:SourceIp Deny，所有 TCP SYN都會先由 IAM評估

**答案：C**

- **A：** 不正確。Security group只有 allow rules，不能加入顯式 deny。
- **B：** 不正確。刪除或破壞 local routing會影響大量合法 VPC內流量，且不是來源封鎖機制。
- **C：** 正確。NACL可明確 deny CIDR，但必須正確排序且理解它套用到整個 associated subnet。
- **D：** 不正確。IAM條件可限制支援該條件的 AWS API，不是通用 VPC packet firewall。

**事實查證：** [Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)、[Control subnet traffic with network access control lists - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)

### 練習題 7｜SAA｜14.7 SG reference 與動態 instances

Auto Scaling會頻繁替換 App instances，DB只應接受 App workload。哪個 DB SG source最容易維護？

A. App Auto Scaling group名稱
B. 目前所有 App public IP的手動清單
C. 所有 private RFC1918 ranges
D. App instances所附的 security group

**答案：D**

- **A：** 不正確。SG rule不能直接以 Auto Scaling group名稱作網路來源。
- **B：** 不正確。Instances替換會使 IP清單失效，也不應讓 private DB依賴 public IP。
- **C：** 不正確。這遠大於實際 workload邊界，可能允許不相關 networks。
- **D：** 正確。SG reference跟隨 ENI所附角色，不需隨 instance IP變動而更新；但仍要有 route與正確 port。

**事實查證：** [Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)

### 練習題 8｜SAP｜14.8 Flow Logs 的證據邊界

Flow Logs顯示某 ENI流量為 REJECT。哪個除錯結論最準確？

A. Flow Logs一定會列出造成拒絕的確切 SG/NACL rule ID與封包 payload
B. CloudTrail會提供每個被拒絕 packet的完整內容
C. 應把 flow的五元組、方向與 ENI對照 SG/NACL及 route；Flow Logs是 metadata，不是完整 packet capture
D. REJECT代表 IAM explicit deny，因此只需修改 role

**答案：C**

- **A：** 不正確。Flow Logs提供流量 metadata與 action等欄位，但不是完整 payload或普遍的精確 rule trace。
- **B：** 不正確。CloudTrail記錄 AWS API活動，不記錄每個資料封包。
- **C：** 正確。Flow Logs可縮小網路政策問題範圍，仍需回到實際 SG、NACL方向與路由逐項比對。
- **D：** 不正確。VPC packet REJECT通常是網路控制結果，不代表 IAM API授權。

**事實查證：** [Logging IP traffic using VPC Flow Logs - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)、[Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)、[Control subnet traffic with network access control lists - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)

### 練習題 9｜SAP｜14.9 多帳號 exposure guardrail

數百個帳號都能自行管理 application SG，但安全團隊必須防止 SSH/RDP對 0.0.0.0/0 暴露。哪個治理方式最合理？

A. 使用 Firewall Manager、Config或組織自動化持續偵測/修復高風險 SG，同時讓團隊保留 workload最小權限規則
B. 讓所有帳號共用 root credentials管理同一個 SG
C. 用一張 NACL取代 organization內所有 SG
D. 關閉 Flow Logs，避免產生太多違規證據

**答案：A**

- **A：** 正確。中央 guardrail應可持續評估並有明確 exception流程，而不是要求人工逐帳號巡檢。
- **B：** 不正確。共享 root破壞可追溯性與最小權限，且 SG不能跨任意 VPC作單一全域物件。
- **C：** 不正確。NACL是 subnet粗粒度邊界，不能表達所有 workload-to-workload identity。
- **D：** 不正確。關閉Flow Logs等evidence不會降低公開SSH/RDP的風險，只會讓中央團隊更難偵測違規、確認來源與進行事件調查。

**事實查證：** [Using security group policies in Firewall Manager to manage Amazon VPC security groups - AWS WAF, AWS Firewall Manager, AWS Shield Advanced, and AWS Shield network security director](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies.html)、[vpc-sg-open-only-to-authorized-ports - AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/vpc-sg-open-only-to-authorized-ports.html)

### 練習題 10｜SAP｜14.10 SG/NACL 都允許後的除錯（選兩項）

Client到 service持續 timeout；雙方 SG與沿途 NACL已確認允許。哪兩項是合理的下一步？

A. 再新增一條完全相同的 SG rule
B. 驗證 DNS是否解析到預期 IP，以及 forward/return route是否經正確 next hops
C. 修改 instance profile 的 AWS API permissions，假設它會控制資料面的 TCP handshake
D. 檢查 listener、service process與 target health，確認封包到達後有人接受連線
E. 提高 EBS IOPS，因為所有 network timeout都由 storage造成

**答案：B、D**

- **A：** 不正確。重複新增相同allow rule不會改變SG的集合式policy結果，也不會修復DNS、route、listener或application process等其他path層。
- **B：** 正確。先確認DNS把client帶到預期IP，再逐段檢查forward與return route；Reachability Analyzer可用目前配置模型指出缺少或阻斷的網路元件。
- **C：** 不正確。Instance profile管理workload呼叫AWS API的權限，不參與遠端client與service listener之間的資料面TCP三向交握。
- **D：** 正確。路由與network policy通過後，下一層是load balancer listener、target registration與health check，再確認instance上的process確實在預期port接受連線。
- **E：** 不正確。Storage bottleneck可能提高應用回應時間，但沒有metric或trace證據時不能把所有TCP timeout歸因EBS，更不能跳過listener與target health檢查。

**事實查證：** [What is Reachability Analyzer? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html)、[Logging IP traffic using VPC Flow Logs - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)、[Check the health of your Application Load Balancer targets - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/check-target-health.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Security Group作主要allow-list；NACL用於粗粒度subnet防護或明確deny需…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「網路控制需要區分資源級stateful規則與subnet級stateless邊界。」，所以「Security Group作主要allow-list；NACL用於粗粒度subnet防護或明確deny需求。」能直接滿足它；若constraint改成「SG自動允許已建立連線回程；NACL必須同時允許雙向與ephemeral ports。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Security Group作主要allow-list；NACL用於粗粒度subnet防護或明確deny需求。」。替代方案「SG自動允許已建立連線回程；NACL必須同時允許雙向與ephemeral ports。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只開啟應用port卻在NACL阻擋回程ephemeral port，造成間歇timeout。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「網路控制需要區分資源級stateful規則與subnet級stateless邊界。」，排除會導致「只開啟應用port卻在NACL阻擋回程ephemeral port，造成間歇timeout。」的選項，再選「Security Group作主要allow-list；NACL用於粗粒度subnet防護或明確deny需求。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAP-1.2 Prescribe security controls；SAP-2.3 Determine security controls based on requirements；SAP-3.2 Determine a strategy to improve security。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Security Group作主要allow-list；NACL用於粗粒度subnet防護或明確deny需求。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「place policy at the narrowest stable boundary」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 15 章　VPC Peering、PrivateLink 與 Transit Gateway

VPC之間可共享整個網路、特定服務或經中央路由，但三種需求不同。

## 跟著一個封包走：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：三十個consumer VPC只需呼叫中央付款API，不應彼此路由。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：VPC之間可共享整個網路、特定服務或經中央路由，但三種需求不同。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：Peering像兩個園區直接修一條路，Transit Gateway像中央轉運站，PrivateLink則像只開一個服務窗口而不讓訪客逛完整座園區。 但請同時記住它的邊界：真實網路還有CIDR、DNS、回程與費用；不能只靠類比判斷可達性。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是VPC Peering，對照角色是AWS PrivateLink。我們選擇「少量一對一網路用peering；只發布服務用PrivateLink；多VPC hub-and-spoke用TGW。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：三十個consumer VPC只需呼叫中央付款API，不應彼此路由。

需求先分三種，不能只問「VPC怎麼連」

1. 少量VPC需要任意private-IP雙向互通
   VPC A <──────── VPC Peering ────────> VPC B

2. Consumer只該呼叫Provider的一個服務
   Consumer ENI ── PrivateLink ──> Provider NLB / service

3. 大量VPC、VPN、DX需要transitive hub與分段route domains
   Spokes ── attachments ──> Transit Gateway ──> shared services / inspection

三條路都仍需檢查DNS、去回程、security policy與CIDR重疊。

失敗時先找：為了讓一個API可用而互連整個CIDR，擴大blast radius並遇到重疊地址。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問VPC Peering有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，VPC Peering和AWS PrivateLink並不是兩個任意的產品名稱。前者適合本章，是因為「少量一對一網路用peering；只發布服務用PrivateLink；多VPC hub-and-spoke用TGW。」直接回應了眼前的問題；後者描述的「Peering簡單但不transitive；TGW擴展好但需治理route domains；PrivateLink只暴露endpoint service。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：為了讓一個API可用而互連整個CIDR，擴大blast radius並遇到重疊地址。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「share the minimum required connectivity」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| VPC Peering | 讓兩個VPC透過私有IP直接routing。 | 建立一對一non-transitive連線，雙方route table與SG/DNS需分別設定。 |
| AWS PrivateLink | 以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。 | Provider以NLB和endpoint service發布；consumer在自己的subnet取得endpoint ENI。 |
| AWS Transit Gateway | 以regional hub連接大量VPC、VPN與Direct Connect。 | Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 |

## 把全圖套進一個具體案例

**場景：** 三十個consumer VPC只需呼叫中央付款API，不應彼此路由。

1. 故事的起點：三十個consumer VPC只需呼叫中央付款API，不應彼此路由。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：VPC Peering負責「讓兩個VPC透過私有IP直接routing。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：建立一對一non-transitive連線，雙方route table與SG/DNS需分別設定。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS PrivateLink、AWS Transit Gateway各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「為了讓一個API可用而互連整個CIDR，擴大blast radius並遇到重疊地址。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「VPC數量多或需transitive hub/inspection時使用Transit Gateway；只暴露服務用PrivateLink。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 再往底層走：這一章真正容易混淆的地方

### 先把 routing 與 DNS 拆成兩條獨立路徑

Routing回答「已知目的IP後，封包下一跳去哪裡」；DNS resolution回答「hostname要翻成哪個IP」。VPC Peering變成active只建立一條可被route table引用的連線，仍要在雙方subnets加入peer CIDR routes，再設定security groups。若application用hostname，才另外考慮peering DNS resolution。因此DNS查得到但route不通會timeout；route通但DNS未設定則可能解析到public IP或根本找不到名稱。

### Peering DNS resolution 到底改了什麼

EC2 instance可能有public DNS hostname。預設從peer VPC查詢時，不一定得到可走peering的private address；在active peering上為requester與accepter各自啟用AllowDnsResolutionFromRemoteVpc後，跨peering查詢這類hostname可解析成peer private IPv4。兩個VPC仍需啟用DNS support/hostnames，而private hosted zone還有自己的VPC association或Resolver設計，不能把所有DNS問題都歸給這個開關。

### 何時從 Peering 換成 TGW 或 PrivateLink

少量VPC、需要任意private-IP雙向互通且CIDR不重疊時，Peering最直接；但每對VPC都要連線與route，而且不transitive。VPC數量增加、需要hub routing、分段route domains或集中inspection時，Transit Gateway更容易治理。若consumer只該使用provider的一個service，尤其有CIDR重疊或SaaS cross-account需求，PrivateLink暴露endpoint service會比打通整個VPC更小權限。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### VPC Lattice：當你只想連「服務」，而不是打通整個網路

想像付款 API 在 A 帳號，訂單服務在 B 帳號，而且兩邊 VPC 的 CIDR 還重疊。Peering／Transit Gateway 的核心抽象是 IP 路由；PrivateLink 的核心抽象是一個由 provider 暴露的 endpoint service。VPC Lattice 再往上提一層：平台先建立 service network，服務擁有者把 HTTP／HTTPS 等服務掛進去，consumer VPC 只有在建立 association 且通過 auth policy 時才可呼叫。

```text
consumer workload
  │ service DNS name
  ▼
associated VPC ── security group ──> VPC Lattice service network
                                      │ auth policy
                         ┌────────────┴────────────┐
                         ▼                         ▼
                    payment service          catalog resource
                    listener/rules           resource config
                    targets                  resource gateway
```

#### 一個最小 auth policy 長什麼樣子

```JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::111122223333:role/OrderServiceRole"},
    "Action": "vpc-lattice-svcs:Invoke",
    "Resource": "arn:aws:vpc-lattice:ap-northeast-1:444455556666:service/svc-123/*"
  }]
}
```

1. Principal 是真正可以呼叫服務的 workload role；VPC association 只提供網路入口，不等於授權。
2. Resource 指向 Lattice service，而不是對方整個 VPC。這就是它能縮小 blast radius 的原因。
3. 服務仍需 listener、rules、target group 與健康 targets；Lattice 不會替 application 修好 retry、身份資料或交易一致性。

**選擇邊界：** 需要任意 private-IP 雙向連線時仍比較 Peering/TGW；只暴露單一 TCP 服務可比較 PrivateLink；跨 VPC／帳號的 application networking、L7 routing 與 IAM auth 才是 Lattice 的強項。

**考試範圍：** SAA 先掌握它與 Peering／TGW／PrivateLink 的責任邊界；多帳號 service network、RAM 分享、delegated ownership 與 policy rollout 屬 SAP／進階實務。

- [AWS：What is Amazon VPC Lattice?](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [AWS：VPC Lattice auth policies](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)

## 需要時再查：四個閱讀支點

### VPC Peering

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：VPC之間可共享整個網路、特定服務或經中央路由，但三種需求不同。
- **具體例子／邊界：** 在「三十個consumer VPC只需呼叫中央付款API，不應彼此路由。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS PrivateLink

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Peering簡單但不transitive；TGW擴展好但需治理route domains；PrivateLink只暴露endpoint service。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：為了讓一個API可用而互連整個CIDR，擴大blast radius並遇到重疊地址。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：share the minimum required connectivity。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### transitive routing

A能到B且A能到C時，B是否可經A到C；VPC Peering不提供此能力，TGW可建立受控hub routing。

### Direct Connect

從客戶或colocation到AWS的專用網路連線；提供較穩定路徑，但本身不等於端到端加密或自動高可用。

### DNS resolution

名稱解析過程。得到IP只代表知道目的地，不代表route、firewall、TLS與IAM一定允許連線。

### blast radius

一個故障、bug或錯誤變更最多能影響的使用者、租戶、accounts或Regions範圍。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### principal

AWS authorization中的caller identity，例如user、role session、AWS service或federated identity。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### CIDR

以10.0.0.0/16這類prefix描述一段IP範圍；prefix越大，範圍越小。重疊CIDR會破壞明確routing。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### VPN

Virtual Private Network，在既有Internet上建立加密tunnel；AWS Site-to-Site VPN通常提供兩條IPsec tunnels。

## 回到 AWS：Components、功用與責任邊界

### VPC Peering

- **功用：** 讓兩個VPC透過私有IP直接routing。
- **底層機制：** 建立一對一non-transitive連線，雙方route table與SG/DNS需分別設定。
- **關鍵設定：** acceptance、routes、DNS resolution、SG references與non-overlapping CIDRs。
- **選擇時機：** 少量VPC、簡單全網路互通且不需要中央轉送時。
- **替換時機：** VPC數量多或需transitive hub/inspection時使用Transit Gateway；只暴露服務用PrivateLink。

### AWS PrivateLink

- **功用：** 以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。
- **底層機制：** Provider以NLB和endpoint service發布；consumer在自己的subnet取得endpoint ENI。
- **關鍵設定：** endpoint service acceptance、allowed principals、NLB、interface endpoint subnets/SG、private DNS。
- **選擇時機：** SaaS、跨帳號服務、CIDR重疊或只需單向client-to-service連線時。
- **替換時機：** 需要VPC任意IP雙向互通用Peering/TGW；需要L7服務網路可評估VPC Lattice。

### AWS Transit Gateway

- **功用：** 以regional hub連接大量VPC、VPN與Direct Connect。
- **底層機制：** Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。
- **關鍵設定：** attachments、association、propagation、TGW route tables、appliance mode、ECMP與multicast。
- **選擇時機：** 數十到數千網路、hub-and-spoke、集中egress/inspection或hybrid routing。
- **替換時機：** 只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。

## 考前與實作時再查：設定操作手冊

### VPC Peering：逐項設定說明

#### `acceptance`

- **控制什麼：** Peering先由requester提出，再由accepter同意；只有狀態成為active後才可承載route與修改DNS選項。
- **何時需要：** 兩個VPC需要直接private-IP連線，且CIDR不重疊、不需要transitive routing時。
- **怎麼設定／驗證：** 建立AWS::EC2::VPCPeeringConnection或create-vpc-peering-connection，讓另一側accept；跨帳號要先確認account/VPC ID與owner。
- **常見錯法：** 接受連線不會自動建立route、DNS或security rules；把active誤認成application已可通是最常見錯法。

#### `routes`

- **控制什麼：** 告訴每個subnet：目的地是peer CIDR時，把封包送到pcx-* peering connection。去程與回程都必須各自存在。
- **何時需要：** Peering active後，應用需要由一側subnet存取另一側private IP時。
- **怎麼設定／驗證：** 在VPC A相關route table加入「VPC B CIDR → pcx-id」，並在VPC B加入相反route；只開放真正需要互通的subnets。
- **常見錯法：** VPC A連B、A連C不代表B可經A到C；VPC peering不提供transitive routing，route也不能修正重疊CIDR。

#### `DNS resolution`

- **控制什麼：** DNS resolution是把hostname翻成IP。啟用peering DNS選項後，跨peering查詢EC2 public DNS hostname時可得到peer的private IPv4，讓封包留在私網路徑。
- **何時需要：** 程式以DNS hostname而不是固定private IP連接peer EC2，且希望解析結果走private address時。
- **怎麼設定／驗證：** 先讓兩個VPC啟用DNS support/hostnames並使peering為active；再由requester與accepter owner各自開啟AllowDnsResolutionFromRemoteVpc。CLI使用modify-vpc-peering-connection-options。
- **常見錯法：** 這個選項不會讓你直接查詢peer VPC的Amazon DNS server，也不會建立route、SG規則或任意private hosted zone關聯。

#### `security-group references`

- **控制什麼：** 允許SG規則用peer VPC的security group作為source/destination，以workload身份取代容易變動的IP清單。
- **何時需要：** 同Region peering中，app instances經常更換IP，但服務角色與SG邊界穩定時。
- **怎麼設定／驗證：** 在支援的peering情境使用peer account/SG作規則來源，並同時檢查target port與雙方outbound；不支援時退回CIDR或prefix管理。
- **常見錯法：** SG reference不會建立route，也不能跨任意transitive network；刪除peer或SG後要清理stale references。

#### `non-overlapping CIDRs`

- **控制什麼：** 每個VPC必須能以唯一目的prefix被routing；若地址重疊，同一IP可能同時代表local與peer資源。
- **何時需要：** 建立peering之前，以及併購、hybrid network或多帳號環境規劃階段。
- **怎麼設定／驗證：** 比較VPC所有primary/secondary CIDRs與on-premises ranges；大型環境以VPC IPAM分配，已重疊時考慮renumber、PrivateLink或application proxy。
- **常見錯法：** NAT不能普遍消除所有重疊routing語意；硬把重疊網路peer起來通常在建立連線或路由時就被阻止。

### AWS PrivateLink：逐項設定說明

#### `endpoint service acceptance`

- **控制什麼：** 控制provider是否必須逐一接受consumer建立的interface endpoint connection request；它是連線核准，不是封包路由設定。
- **何時需要：** Provider只信任特定consumer、需要人工／自動審批，或allowed principals範圍較廣但仍要二次確認時。
- **怎麼設定／驗證：** 建立endpoint service時設定AcceptanceRequired；收到request後由provider accept/reject。若關閉，任何已被allowed principals授權的request會自動接通。
- **常見錯法：** AcceptanceRequired=false不代表公開給所有人；consumer仍須先符合allowed principals。已接受也不會自動放行NLB target、SG或private DNS。

#### `allowed principals`

- **控制什麼：** 指定哪些AWS accounts、roles、users或organization principals有資格建立連到endpoint service的interface endpoint。
- **何時需要：** 跨帳號SaaS、中央平台服務或只允許organization內特定consumer使用時。
- **怎麼設定／驗證：** 在endpoint service permissions加入具體principal ARN；搭配acceptance policy決定自動或人工核准，並以未授權account做反向測試。
- **常見錯法：** 授權整個organization再關閉acceptance會擴大consumer範圍；這也只授權建立連線，不等於後端application已完成身份驗證。

#### `provider NLB`

- **控制什麼：** Network Load Balancer是endpoint service的provider入口，把PrivateLink連線導向實際service targets，同時隱藏provider VPC的完整route domain。
- **何時需要：** 要發布TCP/TLS服務、支援大量連線，或consumer與provider CIDR重疊而不能建立一般routing時。
- **怎麼設定／驗證：** 建立internal NLB與healthy target groups，再用它建立endpoint service；逐AZ開啟服務並驗證target health、listener port及capacity。
- **常見錯法：** NLB target不健康時endpoint仍可能建立成功但request失敗；PrivateLink也不是任意VPC-to-VPC雙向連線。

#### `interface endpoint subnets／SG`

- **控制什麼：** Consumer在每個選定AZ建立endpoint ENI與private IP；security group控制clients可連入該ENI的protocol與port。
- **何時需要：** Consumer要由多個AZ私下存取service，並將入口限制在特定application security groups時。
- **怎麼設定／驗證：** 選擇每個需要的AZ/subnet並附least-privilege SG；client DNS解析後應得到endpoint ENI地址，再逐AZ測試route、SG與回應。
- **常見錯法：** 只在單一AZ建立endpoint會形成可用性與跨AZ成本問題；SG附錯方向或port時，DNS正常但TCP仍會timeout。

#### `private DNS`

- **控制什麼：** 讓consumer使用provider驗證過的自訂service hostname時，VPC resolver把該名稱解析成interface endpoint private IP，而非public endpoint。
- **何時需要：** 希望application沿用穩定名稱，不暴露vpce-* DNS名稱，或同一SDK hostname在VPC內自動走PrivateLink時。
- **怎麼設定／驗證：** Provider設定並驗證private DNS name的domain ownership；consumer endpoint啟用private DNS，且VPC開啟DNS support/hostnames，再用dig驗證。
- **常見錯法：** Private DNS只改名稱答案，不會建立SG、後端authorization或跨VPC route；同名private hosted zone也可能遮蔽預期答案。

### AWS Transit Gateway：逐項設定說明

#### `attachments`

- **控制什麼：** Attachment把VPC、VPN、Direct Connect gateway、peering或Connect連到一個regional Transit Gateway，形成可被TGW routing管理的入口。
- **何時需要：** 需要hub-and-spoke、transitive routing、集中egress／inspection或大量network互連時。
- **怎麼設定／驗證：** 建立attachment並選擇正確subnets/AZ；VPC route table仍要把remote CIDRs指向TGW，另一側也要有return path。
- **常見錯法：** Attachment available只代表control plane完成；沒有VPC routes、TGW routes、DNS與security policy時，application仍完全不通。

#### `association`

- **控制什麼：** 每個attachment一次只能關聯一張TGW route table；該表決定從此attachment進入的封包要依哪組routes轉送。
- **何時需要：** 要把production、shared services、inspection與isolated networks分成不同route domains時。
- **怎麼設定／驗證：** 停用不適合的default association，為每個attachment指定入口route table；以來源attachment逐一驗證可見目的地。
- **常見錯法：** Association不是把attachment的CIDR發布給別人；把它和propagation混淆會造成黑洞或意外互通。

#### `propagation`

- **控制什麼：** 把attachment可到達的prefix動態加入指定TGW route table，讓使用該表的其他來源知道如何前往該attachment。
- **何時需要：** VPC/VPN/DX routes很多或會變動，不想逐條維護static routes時。
- **怎麼設定／驗證：** 只對應該學到該prefix的route tables啟用propagation；配合static blackhole/inspection routes與route export持續驗證。
- **常見錯法：** Propagation到某張表不會改變attachment自己的association；過度propagate會破壞segmentation並擴大blast radius。

#### `TGW route tables`

- **控制什麼：** 保存destination prefix到attachment的next hop；可用多張表建立transitive hub中的segmentation與service chaining。
- **何時需要：** VPC數量增加、不同環境需要不同可達性，或所有跨網流量必須先經inspection VPC時。
- **怎麼設定／驗證：** 為route domain建立獨立表，設association、propagation、static及blackhole routes；逐來源畫出forward/return path並檢查longest prefix。
- **常見錯法：** 單張全互通表最簡單但blast radius最大；錯誤default route或非對稱return path可能繞過stateful firewall。

#### `appliance mode`

- **控制什麼：** 在inspection VPC attachment上維持同一flow的AZ親和與對稱路徑，使stateful virtual appliance能看到往返封包。
- **何時需要：** 透過TGW把東西向或南北向流量送進跨AZ firewall/IDS appliance fleet時。
- **怎麼設定／驗證：** 只在appliance VPC attachment啟用appliance mode，配合各AZ endpoint/subnet與TGW routes；用雙向flow及故障切換驗證對稱性。
- **常見錯法：** 在spoke隨意啟用不能修正錯誤route；缺少對稱路徑時stateful appliance會把回程當成未知connection丟棄。

#### `ECMP`

- **控制什麼：** Equal-Cost Multi-Path讓TGW在多條等成本VPN/Connect路徑間以flow hash分散流量，提高aggregate throughput與冗餘。
- **何時需要：** 單一VPN tunnel吞吐不足，且on-prem routers能以BGP廣告相同prefix與相同路徑成本時。
- **怎麼設定／驗證：** 在TGW開啟VPN ECMP，建立多條動態路由連線並廣告相同prefix；監控每條tunnel、BGP與aggregate throughput。
- **常見錯法：** ECMP是per-flow而非把單一flow切開；static VPN或不相等BGP path通常無法得到預期分流。

#### `multicast`

- **控制什麼：** 讓一個source把封包送到multicast group，由TGW複製給已註冊receivers，支援少數需要一對多IP傳送的workload。
- **何時需要：** 市場資料、媒體或legacy discovery確實依賴multicast，且unicast fan-out成本／相容性不合適時。
- **怎麼設定／驗證：** 建立multicast domain、關聯subnets並註冊sources/members；確認instance、OS與security rules支援，再量測receiver loss。
- **常見錯法：** Multicast不會自動跨所有attachments或Internet；大多數cloud application用SNS/Kinesis等application-level fan-out更容易治理。

## 可以直接對照 AWS 的設定範例

### VPC Peering：雙向 routes 與跨 peer Security Group

```yaml
Resources:
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

```

1. Peering resource只是連線；兩側route tables都要加入對方CIDR與pcx target，否則只會單向可達或完全timeout。
2. 同Region且支援的peering情境可用peer security group作source；它比固定instance IP更能表達workload identity。
3. 10.20.0.0/16與10.40.0.0/16必須不重疊。Peering不transitive，DataVpc不能因AppVpc另有連線便經它到第三個VPC。

### VPC Peering DNS resolution：requester 與 accepter 各自啟用

```bash
# Peering 必須已是 active。Requester owner 執行：
aws ec2 modify-vpc-peering-connection-options   --vpc-peering-connection-id pcx-0123456789abcdef0   --requester-peering-connection-options   AllowDnsResolutionFromRemoteVpc=true

# Accepter owner 在自己的 account/role context 執行：
aws ec2 modify-vpc-peering-connection-options   --vpc-peering-connection-id pcx-0123456789abcdef0   --accepter-peering-connection-options   AllowDnsResolutionFromRemoteVpc=true

# 從兩側 instance 驗證「名稱 → private IP」，再驗證 TCP path：
dig +short ec2-10-40-8-25.compute-1.amazonaws.com
nc -vz 10.40.8.25 5432

```

1. DNS resolution把hostname翻成private IPv4；它不會替你建立route、security group或database authorization。
2. Requester與accepter options分開保存，跨帳號時由各owner使用自己的credentials設定。任一側未開，雙向名稱解析假設就可能不成立。
3. 先用dig驗證answer，再用nc/curl驗證transport。若dig成功而nc timeout，下一步查route table、SG/NACL與return path，而不是繼續改DNS。

## 讀到這裡，請用自己的話說一次

1. VPC Peering的責任：讓兩個VPC透過私有IP直接routing。
2. 底層機制：建立一對一non-transitive連線，雙方route table與SG/DNS需分別設定。
3. 第一個要看的設定：acceptance、routes、DNS resolution、SG references與non-overlapping CIDRs。
4. 選擇邏輯：少量一對一網路用peering；只發布服務用PrivateLink；多VPC hub-and-spoke用TGW。
5. 不要混淆：AWS PrivateLink的責任是「以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。」；它不會自動取代VPC Peering。
6. 替換訊號：VPC數量多或需transitive hub/inspection時使用Transit Gateway；只暴露服務用PrivateLink。
7. 最常見錯法：為了讓一個API可用而互連整個CIDR，擴大blast radius並遇到重疊地址。
8. 可移植原則：share the minimum required connectivity。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| VPC Peering | 讓兩個VPC透過私有IP直接routing。 | 建立一對一non-transitive連線，雙方route table與SG/DNS需分別設定。 | 少量VPC、簡單全網路互通且不需要中央轉送時。 | VPC數量多或需transitive hub/inspection時使用Transit Gateway；只暴露服務用PrivateLink。 |
| AWS PrivateLink | 以interface endpoint私下發布或消費特定服務，而不暴露整個VPC route domain。 | Provider以NLB和endpoint service發布；consumer在自己的subnet取得endpoint ENI。 | SaaS、跨帳號服務、CIDR重疊或只需單向client-to-service連線時。 | 需要VPC任意IP雙向互通用Peering/TGW；需要L7服務網路可評估VPC Lattice。 |
| AWS Transit Gateway | 以regional hub連接大量VPC、VPN與Direct Connect。 | Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 | 數十到數千網路、hub-and-spoke、集中egress/inspection或hybrid routing。 | 只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Peering簡單但不transitive；TGW擴展好但需治理route domains；PrivateLink只暴露endpoint service。 | 只有當題目條件明確改變時才可能合理。 | 為了讓一個API可用而互連整個CIDR，擴大blast radius並遇到重疊地址。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Peering簡單但不transitive；TGW擴展好但需治理route domains；PrivateLink只暴露endpoint service。」之間做選擇。
- 認得常考設定：acceptance、routes、DNS resolution、SG references與non-overlapping CIDRs。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：VPC數量多或需transitive hub/inspection時使用Transit Gateway；只暴露服務用PrivateLink。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜15.1 少量 VPC 的完整私網互通

兩個 CIDR 不重疊的 VPC 需要以 private IP 任意雙向連線，沒有中央路由或第三個 VPC。哪個方案最直接？

A. 建立 VPC Peering，並在雙方相關 route tables加入對方 CIDR routes及所需 SG rules
B. 以 PrivateLink發布兩個 VPC的完整 CIDR
C. 建立 TGW是唯一可行方式
D. 只接受 peering request，不需任何 route

**答案：A**

- **A：** 正確。少量 point-to-point full-network connectivity適合 Peering，但 acceptance、雙向 routes與 policies都要完成。
- **B：** 不正確。PrivateLink發布特定服務，不提供任意雙向 CIDR routing。
- **C：** 不正確。TGW也可達成，但此簡單兩 VPC情境沒有 transitive/hub需求，會增加元件與費用。
- **D：** 不正確。Active只表示 control plane建立；沒有 routes仍無 data path。

**事實查證：** [What is VPC peering? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html)、[Update your route tables for a VPC peering connection - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-routing.html)

### 練習題 2｜SAA｜15.2 Peering 不具 transitive routing

VPC-A已 peered到 B，B已 peered到 C。A需要連 C，但不希望新增 hub。應如何處理？

A. 在 A加入到 C的 route並指向 A-B peering，B會自動轉送
B. 建立 A-C直接 Peering並配置雙向 routes；Peering不提供 A→B→C transitive routing
C. 開啟 B的 DNS resolution即可轉送
D. 在 A的 SG引用 C SG即可建立路由

**答案：B**

- **A：** 不正確。Peering connection不能作為另一條 peering的 transit next hop。
- **B：** 正確。每對需要完整網路互通的 VPC都要直接連線；規模變大時才考慮 TGW。
- **C：** 不正確。DNS只改變名稱解析的IP答案，不會賦予VPC B轉送A到C封包的能力；VPC Peering本身也不支援transitive routing。
- **D：** 不正確。Security group reference只在既有可達路徑上表達允許的來源身分，不會建立A到C的route或把B變成transit network。

**事實查證：** [How VPC peering connections work - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html#vpc-peering-limitations)

### 練習題 3｜SAA｜15.3 Peering active但 TCP timeout（選兩項）

A-B Peering狀態為 active，DNS也解析到 B private IP，但 A→B TCP timeout。哪兩項最應先驗證？

A. A相關 subnet route有 B CIDR→pcx，B有 A CIDR→同一 pcx的回程 route
B. 只需 requester A的 route，response會自動學習
C. B的 SG/NACL允許實際來源、port與 stateless回程
D. 新增 IGW讓 peering traffic繞 Internet
E. 延長 DNS TTL

**答案：A、C**

- **A：** 正確。Peering不自動修改 route tables；雙向都要有可匹配 route。
- **B：** 不正確。VPC Peering不會自動propagate route；requester與accepter兩側的相關subnet route tables都必須明確加入對端CIDR與peering target。
- **C：** 正確。Route完成後仍需兩側 network policies允許 flow。
- **D：** 不正確。Private VPC Peering流量直接經AWS網路到peering connection，不依賴Internet Gateway；新增IGW也不能修復缺少的peer route或SG規則。
- **E：** 不正確。題目已確認名稱解析到正確private IP，延長TTL只延長該答案的cache，不會新增雙向route、SG ingress或NACL return rule。

**事實查證：** [Update your route tables for a VPC peering connection - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-routing.html)、[Control traffic to your AWS resources using security groups - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)

### 練習題 4｜SAP｜15.4 Peering DNS resolution options

跨 Peering使用 EC2 public DNS hostname時，公司希望它在 peer端解析為 private IPv4。要做什麼？

A. 只在 requester開 EnableDnsSupport即可
B. 建立 NAT Gateway覆寫 DNS answer
C. 確保兩 VPC DNS attributes與 Peering兩側 DNS-resolution options正確；此設定不會建立 route
D. 將 hostname寫成 SG source

**答案：C**

- **A：** 不正確。兩側 VPC與 requester/accepter peering options都可能需要設定。
- **B：** 不正確。NAT Gateway只處理資料封包的位址轉換，不控制Route 53 VPC Resolver如何回答EC2 public hostname，也不會啟用peering DNS resolution。
- **C：** 正確。DNS option可讓 EC2 public hostname跨 peer解析到 private IP，但 routing/security仍獨立。
- **D：** 不正確。SG source接受 CIDR、prefix list或 SG等，不接受 hostname。

**事實查證：** [Enable DNS resolution for a VPC peering connection - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-dns.html)

### 練習題 5｜SAA｜15.5 重疊 CIDR 的單一 API

30個 consumer VPC CIDR彼此重疊，只需呼叫 provider付款 API，且 consumers不得看見 provider其他資源。最佳方案？

A. Full-mesh Peering
B. 單張 TGW全互通 route table
C. Provider以 internal NLB建立 PrivateLink endpoint service，consumers建立 interface endpoints
D. Public ALB並開放所有 consumer NAT IP

**答案：C**

- **A：** 不正確。Peering不支援重疊 CIDR，且暴露整個 route domain。
- **B：** 不正確。TGW不能在同一 route domain解決相同 prefixes，也比單一服務需求更寬。
- **C：** 正確。Consumer endpoint取得自身 VPC IP，只暴露 provider服務，符合 overlap與 least connectivity。
- **D：** 不正確。可行但經 Internet且維護 NAT allowlist，不符合 private最小暴露。

**事實查證：** [What is AWS PrivateLink? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)、[Create a service powered by AWS PrivateLink - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html)

### 練習題 6｜SAP｜15.6 PrivateLink acceptance 後仍失敗

PrivateLink endpoint request已 accepted，但 client解析到 public endpoint或連線 timeout。最完整的排查順序是？

A. Acceptance成功等於 application已授權，重試即可
B. 建立 consumer到 provider整段 CIDR的 peering route
C. 把 provider bucket設 public
D. 檢查 provider private-DNS驗證、consumer private DNS/VPC DNS、endpoint ENI SG、NLB listener與 target health

**答案：D**

- **A：** 不正確。Acceptance只核准 endpoint connection，不證明 DNS、SG或 backend健康。
- **B：** 不正確。PrivateLink不需要 provider CIDR routing，重疊情境更不能用 Peering。
- **C：** 不正確。題目是透過PrivateLink存取的TCP服務，把無關bucket設public不會修正private DNS、endpoint ENI security group或provider target health。
- **D：** 正確。這些分別涵蓋名稱、consumer入口與 provider data path。

**事實查證：** [Create a service powered by AWS PrivateLink - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html)、[Manage DNS names for VPC endpoint services - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/manage-dns-names.html)

### 練習題 7｜SAP｜15.7 TGW association 與 propagation

數百 VPC與 VPN需要 transitive hub，prod/dev互相隔離但都能到 shared services。應如何設計 TGW？

A. 所有 attachments關聯單張全互通 route table
B. 為 route domains建立不同 TGW route tables；association決定 ingress查哪張表，propagation決定哪些 prefixes進入各表
C. 用 full-mesh Peering並由 B轉送 A到 C
D. 用 PrivateLink發布每個 VPC完整網路

**答案：B**

- **A：** 不正確。所有attachments共用單張全互通TGW route table，會讓prod與dev彼此學到prefix，使隔離難以表達並擴大route leak的blast radius。
- **B：** 正確。分離 association與 propagation可讓 prod/dev都學 shared prefix卻不互相學習。
- **C：** 不正確。VPC Peering不支援transitive routing；要讓數百VPC彼此互連會形成大量pairwise connections與route updates，維運規模近似mesh成長。
- **D：** 不正確。PrivateLink是 service-level connectivity，不是任意多網路 hub。

**事實查證：** [What is AWS Transit Gateway for Amazon VPC? - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)、[Transit gateway route tables in AWS Transit Gateway - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)

### 練習題 8｜SAP｜15.8 TGW route leak

Prod attachment關聯 prod table，但它的 prefix也被 propagate到 dev table，造成 dev可路由到 prod。哪個修正正確？

A. 改變 prod association就會自動刪除所有其他 tables的 propagation
B. 只靠 prod SG，route leak不需要治理
C. 修改 DNS名稱
D. 停用不需要的 dev-table propagation，並以明確 static/blackhole routes與測試維持 route-domain邊界

**答案：D**

- **A：** 不正確。TGW route table association決定attachment送出的流量查哪張表，propagation決定其prefix發布到哪些表；改前者不會自動清除後者。
- **B：** 不正確。SG可再限制 flow，但不應保留違反 segmentation的 route knowledge。
- **C：** 不正確。DNS只把名稱轉成IP address，不控制attachment prefix是否propagate到TGW route table；必須停用錯誤propagation或移除route。
- **D：** 正確。只讓每張表學習必要 prefixes，並用證據驗證來源 attachment的可達範圍。

**事實查證：** [Transit gateway route tables in AWS Transit Gateway - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)

### 練習題 9｜SAP｜15.9 TGW stateful inspection symmetry

Spoke A到 B的去程經 inspection VPC，回程卻由 TGW直接回 A，firewall丟棄 response。應優先修正什麼？

A. 設計雙向 routes都經 inspection attachment，並在該 appliance VPC attachment正確使用 appliance mode與各 AZ路徑
B. 只在 spoke A啟用 appliance mode
C. 增加 NAT Gateway即可保證所有 stateful symmetry
D. 提高 Route 53 TTL

**答案：A**

- **A：** 正確。Stateful appliance必須看見同一 flow兩方向；appliance mode協助維持 AZ affinity，但不能取代 routes。
- **B：** 不正確。Appliance mode應用在 appliance VPC attachment，不是任意 spoke。
- **C：** 不正確。NAT不是自動修正 TGW service chaining的工具。
- **D：** 不正確。Route 53 TTL只影響名稱cache，回程封包的TGW next hop由VPC與transit gateway route tables決定，不能用DNS修復對稱性。

**事實查證：** [Amazon VPC attachments in AWS Transit Gateway - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html#appliance-mode)

### 練習題 10｜SAP｜15.10 Connectivity contract 與成本（選兩項）

公司同時有三個需求：3個 VPC全互通、100個 VPC與 on-prem形成 hub、100個 consumers只存取一個 API。哪兩個判斷正確？

A. 所有需求統一用 TGW一定最便宜
B. 少量全網路可用 Peering；大量 transitive networks用 TGW
C. Peering可讓100個 consumers只看單一 API而完全不暴露其他 IP
D. 單一服務且可能 CIDR overlap時用 PrivateLink，並分別計算 endpoint/NLB費用
E. PrivateLink可取代 on-prem與100 VPC的任意雙向路由

**答案：B、D**

- **A：** 不正確。TGW有 attachment與 data processing成本，且 service-only需求過寬。
- **B：** 正確。兩者分別符合 point-to-point與 hub/transitive contract。
- **C：** 不正確。Peering建立整個 CIDR path，仍需大量 routes與 policy。
- **D：** 正確。PrivateLink最小化服務暴露並支援重疊 CIDR，但仍有 endpoint與 data費用。
- **E：** 不正確。PrivateLink只把指定endpoint service暴露給consumer，不提供VPC與on-prem之間任意prefix的雙向route-domain互連或transitive routing。

**事實查證：** [What is VPC peering? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html)、[What is AWS Transit Gateway for Amazon VPC? - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)、[What is AWS PrivateLink? - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「少量一對一網路用peering；只發布服務用PrivateLink；多VPC hub-and-spoke用…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「VPC之間可共享整個網路、特定服務或經中央路由，但三種需求不同。」，所以「少量一對一網路用peering；只發布服務用PrivateLink；多VPC hub-and-spoke用TGW。」能直接滿足它；若constraint改成「Peering簡單但不transitive；TGW擴展好但需治理route domains；PrivateLink只暴露endpoint service。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「少量一對一網路用peering；只發布服務用PrivateLink；多VPC hub-and-spoke用TGW。」。替代方案「Peering簡單但不transitive；TGW擴展好但需治理route domains；PrivateLink只暴露endpoint service。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「為了讓一個API可用而互連整個CIDR，擴大blast radius並遇到重疊地址。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「VPC之間可共享整個網路、特定服務或經中央路由，但三種需求不同。」，排除會導致「為了讓一個API可用而互連整個CIDR，擴大blast radius並遇到重疊地址。」的選項，再選「少量一對一網路用peering；只發布服務用PrivateLink；多VPC hub-and-spoke用TGW。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures；SAP-1.1 Architect network connectivity strategies。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「少量一對一網路用peering；只發布服務用PrivateLink；多VPC hub-and-spoke用TGW。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「share the minimum required connectivity」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 16 章　Route 53 Routing Policies

DNS可以依健康、位置、權重與延遲選endpoint，但不代理每個request。

## 跟著一個封包走：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：全球API要導向低延遲Region，災難時切換，並逐步將10%流量送新版本。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：DNS可以依健康、位置、權重與延遲選endpoint，但不代理每個request。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，把網路想成城市交通：DNS找地址，route選道路，security rules決定哪扇門能進。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看Amazon Route 53如何接手工作，再看Health checks何時更合適，最後用設定與考題驗證「Simple、weighted、latency、failover、geolocation與multi-value依需求選用並設定health checks。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：全球API要導向低延遲Region，災難時切換，並逐步將10%流量送新版本。

來源（使用者／VPC／on-premises）
          │ ① 名稱解析：要連到哪個位址？
          │ ② 去程 route + network policy
          ▼
[Amazon Route 53]
          │ 提供authoritative DNS、health check與多種流量政策。
          ▼
[target／application state]
          │ ③ response沿有效回程返回
控制面：建立DNS、route、listener、policy與health設定
資料面：每個packet／connection／request實際沿路通過
本章其他角色：
  · Health checks：從AWS外部或CloudWatch alarm判斷endpoint是否健康，供Route 53 routi…

失敗時先找：將低TTL視為零切換時間，忽略resolver/client cache與既有connection。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問Amazon Route 53有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon Route 53和Health checks並不是兩個任意的產品名稱。前者適合本章，是因為「Simple、weighted、latency、failover、geolocation與multi-value依需求選用並設定health checks。」直接回應了眼前的問題；後者描述的「Global Accelerator提供anycast與快速網路層failover；CloudFront適合cache與HTTP edge。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將低TTL視為零切換時間，忽略resolver/client cache與既有connection。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「routing policy must match the failure and steering signal」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 |
| Health checks | 從AWS外部或CloudWatch alarm判斷endpoint是否健康，供Route 53 routing policy決定是否回傳該record。 | Route 53 health checker定期探測指定IP/domain、port與path；calculated check可組合多個checks，private endpoint通常以CloudWatch alarm間接表示健康。 |

## 把全圖套進一個具體案例

**場景：** 全球API要導向低延遲Region，災難時切換，並逐步將10%流量送新版本。

1. 故事的起點：全球API要導向低延遲Region，災難時切換，並逐步將10%流量送新版本。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon Route 53負責「提供authoritative DNS、health check與多種流量政策。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Health checks各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將低TTL視為零切換時間，忽略resolver/client cache與既有connection。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon Route 53

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：DNS可以依健康、位置、權重與延遲選endpoint，但不代理每個request。
- **具體例子／邊界：** 在「全球API要導向低延遲Region，災難時切換，並逐步將10%流量送新版本。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Health checks

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Global Accelerator提供anycast與快速網路層failover；CloudFront適合cache與HTTP edge。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將低TTL視為零切換時間，忽略resolver/client cache與既有connection。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：routing policy must match the failure and steering signal。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### resolver

代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon Route 53

- **功用：** 提供authoritative DNS、health check與多種流量政策。
- **底層機制：** Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
- **關鍵設定：** public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- **選擇時機：** 名稱解析、regional failover、逐步流量切換與全球endpoint selection。
- **替換時機：** 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。

### Health checks

- **功用：** 從AWS外部或CloudWatch alarm判斷endpoint是否健康，供Route 53 routing policy決定是否回傳該record。
- **底層機制：** Route 53 health checker定期探測指定IP/domain、port與path；calculated check可組合多個checks，private endpoint通常以CloudWatch alarm間接表示健康。
- **關鍵設定：** protocol、IP/domain、port、request path、failure threshold、measure latency、inverted、calculated children與alarm association。
- **選擇時機：** DNS failover、multi-value answers或需要把不健康endpoint移出DNS回答時。
- **替換時機：** 需要逐request代理、connection draining或target-level routing時使用load balancer health checks；DNS check不會終止既有connection。

## 考前與實作時再查：設定操作手冊

### Amazon Route 53：逐項設定說明

#### `public／private hosted zone`

- **控制什麼：** Hosted zone保存某個DNS namespace的records。Public zone由Internet resolver查詢；private zone只對關聯VPC及適當hybrid resolver path可見。
- **何時需要：** 公開網站使用public zone；內部service name、split-horizon DNS或VPC私有服務使用private zone。
- **怎麼設定／驗證：** 建立zone後加入A/AAAA/CNAME/Alias等records；private zone要關聯每個需要解析的VPC，跨帳號需authorization或RAM/Profiles設計。
- **常見錯法：** 建立private zone不會自動關聯所有VPC；同名public/private records可能因查詢來源不同得到不同答案。

#### `Alias record`

- **控制什麼：** Route 53專用record，可把zone apex或一般名稱指向ALB、CloudFront、API Gateway、S3 website等AWS資源，且可評估target health。
- **何時需要：** 不能使用CNAME的root domain，或AWS target沒有固定IP時。
- **怎麼設定／驗證：** 建立A/AAAA Alias並填AliasTarget DNSName/HostedZoneId；不要手抄短暫IP，CloudFormation可引用資源屬性。
- **常見錯法：** Alias不是routing policy；是否weighted/failover/latency仍需另外設定，且不是所有AWS endpoint都支援Alias。

#### `TTL`

- **控制什麼：** DNS resolver可以快取record answer的秒數。TTL越低，變更較快被看見，但權威DNS查詢量增加；既有connection不會因此被中斷。
- **何時需要：** 計畫切換、failover或頻繁變更endpoint時降低；穩定records可提高。
- **怎麼設定／驗證：** 在普通record設定TTL；Alias到AWS資源的TTL由target行為決定。重大cutover要提前至少一個舊TTL降低，不能切換當下才改。
- **常見錯法：** TTL不是健康檢查週期，也不保證所有client準時丟棄cache；把DNS當request-level load balancer會產生不精確分流。

#### `routing policies`

- **控制什麼：** 決定同名records如何回答：simple、weighted、latency、failover、geolocation、geoproximity或multivalue各自解決不同決策。
- **何時需要：** 需要DNS層canary、主備切換、全球低延遲或地理規則時。
- **怎麼設定／驗證：** 先選policy，再為records設定identifier、weight/region/primary-secondary/geography與health checks；用dig從不同來源驗證。
- **常見錯法：** Weighted不是精準百分比；latency不是距離；geolocation沒有default record可能讓未知位置得到no answer。

#### `health checks`

- **控制什麼：** 由Route 53 health checkers探測public endpoint、監看CloudWatch alarm或計算其他checks，並把不健康record從符合條件的DNS回答中移除。
- **何時需要：** DNS failover或multivalue只想回傳可服務endpoint時。
- **怎麼設定／驗證：** 設定protocol/port/path、interval、failure threshold與regions，或將Alias的EvaluateTargetHealth指向支援的AWS資源。
- **常見錯法：** Private IP不能直接被Internet health checker探測，且移除DNS answer不會中止已建立connection；仍需應用層重試與fencing。

### Health checks：逐項設定說明

#### `protocol`

- **控制什麼：** `protocol`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「DNS failover、multi-value answers或需要把不健康endpoint移出DNS回答時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Health checks的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `IP/domain`

- **控制什麼：** 指定Route 53健康檢查實際探測的公開IPv4／IPv6位址或完整網域名稱，決定探測封包最後送到哪個endpoint。
- **何時需要：** Endpoint可由Internet上的Route 53 health checkers直接到達，且DNS failover必須根據這個endpoint的真實狀態做決策時。
- **怎麼設定／驗證：** 優先使用穩定FQDN並確認解析結果；若填domain，也要設定正確protocol、port與Host header，從多個health-check regions驗證。
- **常見錯法：** 把private IP填入Internet health check不會成功；domain解析到多個位址或切換DNS時，也可能讓探測目標與你以為的不同。

#### `port`

- **控制什麼：** `port`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「DNS failover、multi-value answers或需要把不健康endpoint移出DNS回答時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Health checks的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `request path`

- **控制什麼：** 指定HTTP／HTTPS探測會請求的URI，例如`/healthz`，讓健康狀態代表某個明確application capability，而不只是TCP port有開。
- **何時需要：** DNS切換需要確認web application真的可回應，而單純建立TCP connection不足以代表使用者交易可以成功時。
- **怎麼設定／驗證：** 建立便宜、快速且有明確狀態碼的health endpoint；設定path、Host header與可接受回應，並從外部實際重播同一request。
- **常見錯法：** Health endpoint若同步檢查所有下游，單一非必要dependency就可能觸發全站failover；只回固定200又可能掩蓋真正故障。

#### `failure threshold`

- **控制什麼：** `failure threshold`控制metric如何聚合、與門檻比較、需要幾個datapoints，以及缺資料與alarm action如何處理。
- **何時需要：** 需要可靠告警而不能被單點雜訊、短暫missing data或平均值掩蓋tail latency時。
- **怎麼設定／驗證：** 選擇正確namespace/dimensions/statistic，設定period、evaluation periods、DatapointsToAlarm、comparison與missing-data策略，再演練alarm。
- **常見錯法：** 平均值會隱藏p99；missing data設錯可能把停止上報當健康或故障，alarm action也需要自己的IAM與rollback保護。

#### `measure latency`

- **控制什麼：** `measure latency`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「DNS failover、multi-value answers或需要把不健康endpoint移出DNS回答時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Health checks的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `inverted`

- **控制什麼：** 把子health check或CloudWatch alarm的健康結果反轉，使原本的healthy被視為unhealthy，反之亦然。
- **何時需要：** 監控訊號本身表示失敗條件，例如alarm為OK代表不應供應流量，且無法在來源端改寫訊號語意時才考慮。
- **怎麼設定／驗證：** 先寫出原始訊號與期望DNS行為的truth table，再啟用inverted並故意觸發兩種狀態，確認沒有二次反轉。
- **常見錯法：** Inverted很容易造成雙重否定；若alarm、calculated check與routing policy各自反轉一次，事故時可能保留壞endpoint並移除好endpoint。

#### `calculated children`

- **控制什麼：** 以多個child health checks與健康門檻計算一個父狀態，用來表達N-of-M、AND或OR式的組合健康條件。
- **何時需要：** 單一服務的健康需要整合多個獨立訊號，或希望少數探測器異常時不立即觸發DNS failover時。
- **怎麼設定／驗證：** 列出child checks、可接受失敗數與相依性，設定父check門檻後逐一模擬child失敗，驗證每種組合的最終狀態。
- **常見錯法：** 多個children若都依賴同一DNS、network path或alarm，就不是獨立證據；複雜組合也可能讓真正故障被門檻掩蓋。

#### `alarm association`

- **控制什麼：** `alarm association`控制Health checks的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

## 可以直接對照 AWS 的設定範例

### Route 53 weighted rollout records

```yaml
Resources:
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

```

1. Weight是相對值，不保證每100個request精確95/5，因DNS resolver會cache。
2. Alias可指向ALB且不需固定IP；真正failover還要health evaluation與rollback signal。
3. 需要request-level精確canary時用ALB/CodeDeploy/application routing，而非只靠DNS。

## 讀到這裡，請用自己的話說一次

1. Amazon Route 53的責任：提供authoritative DNS、health check與多種流量政策。
2. 底層機制：Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。
3. 第一個要看的設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
4. 選擇邏輯：Simple、weighted、latency、failover、geolocation與multi-value依需求選用並設定health checks。
5. 不要混淆：Health checks的責任是「從AWS外部或CloudWatch alarm判斷endpoint是否健康，供Route 53 routing policy決定是否回傳該record。」；它不會自動取代Amazon Route 53。
6. 替換訊號：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
7. 最常見錯法：將低TTL視為零切換時間，忽略resolver/client cache與既有connection。
8. 可移植原則：routing policy must match the failure and steering signal。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon Route 53 | 提供authoritative DNS、health check與多種流量政策。 | Hosted zone保存records；resolver遞迴解析；routing policy在DNS回答階段選record，不代理application traffic。 | 名稱解析、regional failover、逐步流量切換與全球endpoint selection。 | 需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。 |
| Health checks | 從AWS外部或CloudWatch alarm判斷endpoint是否健康，供Route 53 routing policy決定是否回傳該record。 | Route 53 health checker定期探測指定IP/domain、port與path；calculated check可組合多個checks，private endpoint通常以CloudWatch alarm間接表示健康。 | DNS failover、multi-value answers或需要把不健康endpoint移出DNS回答時。 | 需要逐request代理、connection draining或target-level routing時使用load balancer health checks；DNS check不會終止既有connection。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Global Accelerator提供anycast與快速網路層failover；CloudFront適合cache與HTTP edge。 | 只有當題目條件明確改變時才可能合理。 | 將低TTL視為零切換時間，忽略resolver/client cache與既有connection。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Global Accelerator提供anycast與快速網路層failover；CloudFront適合cache與HTTP edge。」之間做選擇。
- 認得常考設定：public/private hosted zone、alias、TTL、weighted/latency/failover/geolocation/multivalue與health checks。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.4 Determine high-performing and/or scalable network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要packet-level static IP加速用Global Accelerator；需要HTTP cache/proxy用CloudFront。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures；SAP-2.4 Design a strategy to meet reliability requirements。

## 本章 10 題考題

### 練習題 1｜SAA｜16.1 Simple routing 與 Alias

Zone apex example.com只有一個目前採IPv4的ALB，沒有權重、地域或健康分流需求。應建立哪種record，未來啟用ALB dual-stack後又應如何支援IPv6 clients？

A. 目前以Simple routing建立Alias A指向ALB；只有在ALB與後續路徑為dual-stack且要服務IPv6時，再建立Alias AAAA
B. Weighted 100/0 CNAME放在 zone apex
C. Resolver outbound rule指向 ALB
D. NLB Proxy Protocol record

**答案：A**

- **A：** 正確。Alias record可在zone apex指向支援的AWS target；IPv4 ALB使用Alias A。Alias AAAA只有在load balancer已啟用dual-stack並需要回覆IPv6位址時才有意義。
- **B：** 不正確。Zone apex不能使用一般CNAME，且單一endpoint沒有流量比例需求；100/0 weighted也增加無用的routing-policy複雜度。
- **C：** 不正確。Resolver outbound rule是把特定DNS suffix的query轉送到另一台DNS server，不是把public application name映射到ALB endpoint。
- **D：** 不正確。Proxy Protocol是load balancer傳送來源連線metadata的L4機制，不是Route 53支援的DNS record type，也不能提供IPv4/IPv6解析。

**事實查證：** [Simple routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-simple.html)、[Choosing between alias and non-alias records - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-choosing-alias-non-alias.html)

### 練習題 2｜SAA｜16.2 Weighted DNS rollout

同名兩個 ALB版本要讓新版本約取得10%的 DNS answers。哪個設定正確？

A. Latency records並把新 ALB TTL設10
B. 建立同名同型別 weighted records、不同 SetIdentifier，權重90與10；理解 resolver cache使它不是逐 request精確比例
C. 把 ALB stickiness設10%
D. TTL設0即可保證每100個 requests恰有10個到新版本

**答案：B**

- **A：** 不正確。Latency routing依AWS量測的預期延遲選endpoint，不提供10%這種指定流量比例；藍綠比例應使用weighted records。
- **B：** 正確。Weighted policy按相對權重選 DNS answer，實際 requests還受 cache與 connection重用影響。
- **C：** 不正確。ALB stickiness在 DNS解析之後影響 target，不選 regional ALB。
- **D：** 不正確。TTL不代表每個 request重新查 DNS，且 resolver可能有自身行為。

**事實查證：** [Weighted routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html)

### 練習題 3｜SAA｜16.3 Latency routing（選兩項）

公司在 us-east-1與 eu-west-1各有 API，希望 users通常解析到 AWS量測延遲較低的 Region。哪兩項正確？

A. 為各 endpoint建立 latency records並指定對應 Region
B. Latency policy保證選地理距離最近的資料中心
C. 搭配健康評估可避免回答已判定不健康的 regional endpoint
D. 將兩 records都設相同 SetIdentifier
E. 使用 geolocation才能量測即時 TCP latency

**答案：A、C**

- **A：** 正確。每個latency record代表一個Region與endpoint，Route 53依其收集的Region間延遲資料，為DNS query選擇預期延遲較低的record。
- **B：** 不正確。Latency routing依AWS的latency measurements選擇，不保證地理距離最近，也不是對每個application request即時執行TCP探測。
- **C：** 正確。只要同一routing set中仍有健康候選，health evaluation會排除已判定不健康的regional endpoint；若全部候選都不健康，Route 53會fail-open並仍返回record。
- **D：** 不正確。同名routing-policy records需要唯一SetIdentifier才能區分各個Region與endpoint；使用相同identifier無法正確建立這組records。
- **E：** 不正確。Geolocation依DNS query來源位置分類，可能參考resolver或EDNS0 client subnet；它不量測即時TCP latency，也不是latency policy的替代品。

**事實查證：** [Latency-based routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-latency.html)、[How Amazon Route 53 chooses records when health checking is configured - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-how-route-53-chooses-records.html)

### 練習題 4｜SAA｜16.4 Active-passive failover

Primary Region不健康時才回答 secondary endpoint；恢復後允許回切。哪種 Route 53 policy最符合？

A. Simple records會自動判斷 primary
B. 只降低 TTL
C. Failover primary/secondary records並配置 health evaluation；另行處理既有 connections與資料 writer fencing
D. Multi-value必然等同 active-passive DR

**答案：C**

- **A：** 不正確。Simple routing沒有primary與secondary角色，也不會依health check狀態把新DNS回答切到指定備援endpoint。
- **B：** 不正確。較低TTL只能縮短部分resolver cache時間，不會建立health decision或primary/secondary關係，既有cache也不會被立即清除。
- **C：** 正確。Primary不健康而secondary健康時，Failover policy回覆secondary；若兩者都不健康，Route 53可能仍回覆primary。DNS只影響新解析，既有connections、資料複寫與writer fencing需另行處理。
- **D：** 不正確。Multivalue answer可在一個回答中返回多個健康records，並不表達嚴格的active-passive primary/secondary切換語意。

**事實查證：** [Failover routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)

### 練習題 5｜SAA｜16.5 Geolocation、resolver位置與default record

媒體網站希望依DNS query的來源位置做內容在地化：判定來自Germany的query回覆EU endpoint，其他或無法判定的位置回覆global endpoint。應如何設計？

A. Latency routing即可保證所有Germany終端使用者都被辨識並留在EU
B. 只建立 Germany record，未知位置會自動使用它
C. Weighted 100% EU並由 client自行判斷國家
D. Geolocation Germany record加一筆 default record，避免未匹配位置無答案

**答案：D**

- **A：** 不正確。Latency routing最佳化預期網路延遲，不依國家分類；而DNS通常看到recursive resolver位置，不能保證可靠驗證每位終端使用者所在地。
- **B：** 不正確。若沒有default record，無法對應任何已建立location的query可能得到no answer；Germany record不會自動成為其他位置的fallback。
- **C：** 不正確。Weighted routing按設定權重分配DNS回答，不按query來源國家分類；把判斷交給client也不會形成Route 53的geolocation policy。
- **D：** 正確。Geolocation可依resolver來源，並在可用時利用EDNS0 client-subnet資訊分類；default承接未匹配位置。它適合內容在地化，但不是身分驗證、資料駐留或法規圍欄的唯一控制。

**事實查證：** [Geolocation routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-geo.html)、[How Amazon Route 53 uses EDNS0 to estimate the location of a user - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-edns0.html)

### 練習題 6｜SAA｜16.6 Multi-value answer 邊界

公司要讓 DNS回傳多個健康 web server IP供 client選擇，但不需要 L7 proxy。哪個敘述正確？

A. Multi-value answer可搭 health checks回多個健康 records，但不取代 ALB的 request routing與connection draining
B. Simple routing會自動剔除每個不健康 record
C. Weighted routing會代理每個 HTTP request
D. NACL可提供 DNS health checking

**答案：A**

- **A：** 正確。它提供簡單 DNS-level分散與健康選擇，沒有 load balancer資料面能力。
- **B：** 不正確。Simple不能把多值 record中的單一 value各自配 health check。
- **C：** 不正確。Route 53只在DNS層返回resource records，不會接收或代理後續HTTP request；client會直接連到答案中的web server IP。
- **D：** 不正確。Network ACL只依CIDR、protocol與port允許或拒絕subnet邊界的packets，不會主動探測application health或產生DNS回答。

**事實查證：** [Multivalue answer routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-multivalue.html)

### 練習題 7｜SAA｜16.7 Apex Alias 與 CNAME

example.com zone apex要指向 CloudFront。哪個選擇正確？

A. 建立 apex CNAME到 distribution hostname
B. 複製目前 CloudFront edge IP成 A records
C. 建立 Alias A/AAAA到 CloudFront；Alias target與 routing policy是不同設定維度
D. 建立 Resolver inbound endpoint

**答案：C**

- **A：** 不正確。DNS apex不能使用一般 CNAME與同 zone必要 records共存。
- **B：** 不正確。CloudFront edge IP由AWS管理且可能變動，手動複製成A records會失去服務整合與自動更新；zone apex應使用Alias。
- **C：** 正確。Route 53 Alias支援 apex與 AWS targets，仍可另選合適 routing policy。
- **D：** 不正確。Inbound endpoint處理 hybrid private DNS queries。

**事實查證：** [Choosing between alias and non-alias records - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-choosing-alias-non-alias.html)

### 練習題 8｜SAA｜16.8 TTL cutover

原 record TTL為3600秒；切換當下才改成60秒並換 endpoint。舊 resolver何時可能更新？

A. 所有 cache立即套用60秒
B. Health check會主動清除所有 client cache
C. Alias record完全不會被 cache
D. 已取得舊答案的 resolver可保留到原3600秒到期；應至少提前一個舊 TTL降低

**答案：D**

- **A：** 不正確。新的60秒TTL只會出現在變更後取得的DNS回答中，無法追溯縮短resolver已按舊3600秒TTL保存的cache。
- **B：** 不正確。Authoritative DNS不能普遍推送清除外部 resolver/client cache。
- **C：** 不正確。Alias record雖不由使用者設定一般TTL，仍會產生可被recursive resolver與client cache的DNS回答，不是即時control-plane切換。
- **D：** 正確。Cutover計畫要考慮舊 TTL與既有 connections。

**事實查證：** [Values specific for simple records - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-values-basic.html#rrsets-values-basic-ttl)

### 練習題 9｜SAP｜16.9 Private endpoint health signal

Private hosted zone的 endpoint沒有 public IP，Internet上的 Route 53 health checker無法直接連入，但仍需 DNS failover。最佳做法？

A. 由內部監控產生 CloudWatch alarm，讓 Route 53 health check以該 alarm作健康訊號
B. 暫時建立 IGW並公開健康 port
C. 用 NACL rule number表示健康
D. Private hosted zone會自動探測所有 records

**答案：A**

- **A：** 正確。CloudWatch alarm health check可間接代表不可由 public checker直接探測的 private application。
- **B：** 不正確。為了Internet health checker而替private service建立IGW與公開health port，會新增不必要的入站路徑與攻擊面，違反原本私有邊界。
- **C：** 不正確。NACL rule number只決定stateless packet-filter評估順序，沒有application health、dependency readiness或Route 53 failover狀態語意。
- **D：** 不正確。Private hosted zone不會自動建立每個 record的 health checks。

**事實查證：** [Types of Amazon Route 53 health checks - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-types.html#health-checks-types-cloudwatch)

### 練習題 10｜SAP｜16.10 多層 DNS steering（選兩項）

公司既要跨 Region latency steering，又要在每個 Region內做 blue/green 90/10 rollout。哪兩項設計原則正確？

A. 在同一 record同時啟用 latency、weighted與 failover三個 policy flags
B. 用可解釋的 record tree或不同 names，讓一層選 Region、下一層在 Region內分版本
C. 只把 TTL設1秒即可同時達成比例與延遲
D. 為每層配置合適 health與 rollback metrics，並測試 resolver cache後的結果
E. 用 Global Accelerator traffic dial直接修改 Route 53 record weights

**答案：B、D**

- **A：** 不正確。單一 record set只有一種 routing-policy語意；複雜需求需分層。
- **B：** 正確。讓外層只選Region、內層只分配blue/green權重，可分別測試latency與rollout結果；每層只承擔一個steering signal較容易驗證與回復。
- **C：** 不正確。TTL只控制resolver可以cache答案多久，不會建立latency-based的Region選擇或weighted的90/10版本分配決策。
- **D：** 正確。每一層都需要health check、cache觀察與business metric，才能證明新DNS回答與真實流量符合預期，並在錯誤時安全rollback。
- **E：** 不正確。GA traffic dial是 GA endpoint-group設定，不會改 Route 53 weights。

**事實查證：** [Choosing a routing policy - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html)、[Weighted routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html)、[Latency-based routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-latency.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Simple、weighted、latency、failover、geolocation與multi-va…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「DNS可以依健康、位置、權重與延遲選endpoint，但不代理每個request。」，所以「Simple、weighted、latency、failover、geolocation與multi-value依需求選用並設定health checks。」能直接滿足它；若constraint改成「Global Accelerator提供anycast與快速網路層failover；CloudFront適合cache與HTTP edge。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Simple、weighted、latency、failover、geolocation與multi-value依需求選用並設定health checks。」。替代方案「Global Accelerator提供anycast與快速網路層failover；CloudFront適合cache與HTTP edge。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將低TTL視為零切換時間，忽略resolver/client cache與既有connection。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「DNS可以依健康、位置、權重與延遲選endpoint，但不代理每個request。」，排除會導致「將低TTL視為零切換時間，忽略resolver/client cache與既有connection。」的選項，再選「Simple、weighted、latency、failover、geolocation與multi-value依需求選用並設定health checks。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.4 Determine high-performing and/or scalable network architectures；SAP-1.1 Architect network connectivity strategies；SAP-1.3 Design reliable and resilient architectures。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Simple、weighted、latency、failover、geolocation與multi-value依需求選用並設定health checks。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「routing policy must match the failure and steering signal」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 17 章　CloudFront、Global Accelerator 與 Edge

全球使用者需要降低延遲、保護origin或改善非HTTP連線路徑。

## 跟著一個封包走：先從故事開始

把鏡頭拉到一個真實的production現場：遊戲使用UDP且需固定入口；網站靜態內容與API則需WAF及origin protection。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：全球使用者需要降低延遲、保護origin或改善非HTTP連線路徑。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：CloudFront像把常用商品先放到各地分店，Global Accelerator則像把客戶快速帶上AWS的高速公路，再送往健康的區域入口。 前者理解HTTP與cache，後者主要處理network flow；兩者不是單純的快與更快。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Amazon CloudFront是這一章的入口，AWS Global Accelerator用來畫出邊界；主要方向「可cache HTTP內容用CloudFront；需要static anycast IP或TCP/UDP加速用Global Accelerator。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：遊戲使用UDP且需固定入口；網站靜態內容與API則需WAF及origin protection。

全球使用者
  ├─ HTTP內容可cache、要WAF與保護origin
  │      └─> CloudFront edge ── hit直接回覆 / miss回origin
  │                    └─ Lambda@Edge只在選定event階段修改request/response
  │
  └─ TCP/UDP、不可cache、需要兩個static anycast IP
         └─> Global Accelerator edge ── AWS backbone ──> healthy regional endpoint

CloudFront與Global Accelerator是兩條不同入口路徑，不會依序串在一起。

失敗時先找：將動態、不可cache且需固定IP的工作硬套CloudFront，或忽略cache key造成資料洩漏。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問Amazon CloudFront有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon CloudFront和AWS Global Accelerator並不是兩個任意的產品名稱。前者適合本章，是因為「可cache HTTP內容用CloudFront；需要static anycast IP或TCP/UDP加速用Global Accelerator。」直接回應了眼前的問題；後者描述的「CloudFront Functions/Lambda@Edge可在edge改寫請求，但會增加部署與除錯面。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將動態、不可cache且需固定IP的工作硬套CloudFront，或忽略cache key造成資料洩漏。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「move computation and copies toward users only when semantics permit」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 |
| AWS Global Accelerator | 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。 | Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。 |
| Lambda@Edge | 在CloudFront edge事件上執行Lambda程式，依request/response修改header、URI、認證或origin選擇。 | CloudFront在viewer request、origin request、origin response或viewer response階段呼叫已複寫到edge的函式版本。 |

## 把全圖套進一個具體案例

**場景：** 遊戲使用UDP且需固定入口；網站靜態內容與API則需WAF及origin protection。

1. 故事的起點：遊戲使用UDP且需固定入口；網站靜態內容與API則需WAF及origin protection。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon CloudFront負責「在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Global Accelerator、Lambda@Edge各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將動態、不可cache且需固定IP的工作硬套CloudFront，或忽略cache key造成資料洩漏。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 再往底層走：這一章真正容易混淆的地方

### CloudFront 的三段 request flow

Viewer先以DNS到最近edge。Edge依cache behavior選origin與policies，再用cache key找副本；hit直接回應，miss才向origin request。這三段的policy不同：viewer protocol決定client如何進edge，cache policy決定哪些值切分cache objects，origin request policy決定哪些額外值只轉給origin。若把三者混在一起，最常出現cache hit ratio極低、不同使用者共用錯誤response，或origin收不到必要context。

### Cache policy 與 origin request policy 為何不能互換

會改變response內容的header/cookie/query必須進cache key，否則不同request可能拿到同一cached response；origin只需要拿來logging或authorization、但不應產生另一份cache object的值，可只放origin request policy。最安全的起點不是forward all，而是從AWS managed policies開始，再用實際response variance逐項加入。

### Private S3 origin 與 OAC

使用者只應讀CloudFront URL時，S3保持Block Public Access與Bucket owner enforced。OAC讓CloudFront service以SigV4簽署到S3 REST endpoint的request；bucket policy再以distribution SourceArn限制。OAC不是把bucket變public，也不適用S3 website endpoint。若origin仍可被直接打到，WAF、cache與signed URL等edge controls都可能被繞過。

## 需要時再查：四個閱讀支點

### Amazon CloudFront

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：全球使用者需要降低延遲、保護origin或改善非HTTP連線路徑。
- **具體例子／邊界：** 在「遊戲使用UDP且需固定入口；網站靜態內容與API則需WAF及origin protection。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Global Accelerator

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：CloudFront Functions/Lambda@Edge可在edge改寫請求，但會增加部署與除錯面。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將動態、不可cache且需固定IP的工作硬套CloudFront，或忽略cache key造成資料洩漏。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：move computation and copies toward users only when semantics permit。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### cache key

決定兩個request能否共用同一cached response的識別值，通常由path與選定headers/cookies/query組成。

### listener

在load balancer指定protocol/port等待client connection的入口。

### origin

CDN/cache miss時真正取得內容的後端，例如S3、ALB或HTTP server。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### edge

靠近使用者的全球節點，用來終止連線、cache、過濾或加速，而不是authoritative application state。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### OAC

CloudFront Origin Access Control，以SigV4簽署到private origin的request，常用來讓S3只接受指定distribution。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

### UDP

不先建立可靠connection的datagram協定，延遲低但application需自行處理遺失與順序。

## 回到 AWS：Components、功用與責任邊界

### Amazon CloudFront

- **功用：** 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
- **底層機制：** DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。
- **關鍵設定：** origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
- **選擇時機：** 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。
- **替換時機：** 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。

### AWS Global Accelerator

- **功用：** 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。
- **底層機制：** Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。
- **關鍵設定：** listeners、endpoint groups、traffic dial、endpoint weight、health checks與client affinity。
- **選擇時機：** 遊戲、VoIP、IoT、固定IP allowlist或不可快取的全球TCP/UDP應用。
- **替換時機：** HTTP內容需要cache、header/path routing或edge function時選CloudFront。

### Lambda@Edge

- **功用：** 在CloudFront edge事件上執行Lambda程式，依request/response修改header、URI、認證或origin選擇。
- **底層機制：** CloudFront在viewer request、origin request、origin response或viewer response階段呼叫已複寫到edge的函式版本。
- **關鍵設定：** event trigger、us-east-1 function version、IAM execution role、memory/timeout、include body、logs與deployment restrictions。
- **選擇時機：** 需要依viewer request做輕量認證、URL rewrite、header處理或動態origin selection時。
- **替換時機：** 只需簡單低延遲JavaScript處理可比較CloudFront Functions；完整API/business logic應放regional service。

## 考前與實作時再查：設定操作手冊

### Amazon CloudFront：逐項設定說明

#### `origins`

- **控制什麼：** Origin是cache miss時CloudFront真正取資料的後端，例如S3 REST endpoint、ALB、API Gateway或自訂HTTP server。
- **何時需要：** 要把全球edge delivery與實際儲存／應用後端分離時。
- **怎麼設定／驗證：** 設定DomainName、OriginPath、origin protocol與custom headers；S3 private origin搭配OAC，自訂origin要限制只接受CloudFront流量。
- **常見錯法：** 把S3 website endpoint當成可用OAC的S3 REST origin，或讓origin仍公開可繞過WAF/cache，會破壞安全邊界。

#### `cache policy`

- **控制什麼：** 決定哪些headers、cookies、query strings進入cache key，以及minimum/default/maximum TTL。Cache key不同就會形成不同cache object。
- **何時需要：** 同一路徑會因語言、裝置、授權狀態或query參數產生不同內容時。
- **怎麼設定／驗證：** 優先選AWS managed policy；自訂時只把真正改變response的值放入cache key，並設定TTL與Gzip/Brotli。將policy附到cache behavior。
- **常見錯法：** 把所有headers/cookies/query strings都放進cache key會造成大量碎片與低hit ratio；漏掉會改變response的值則可能回錯內容。

#### `origin request policy`

- **控制什麼：** 決定額外轉送哪些headers、cookies與query strings到origin，但不把它們加入cache key。
- **何時需要：** Origin需要request context做logging、authorization或business logic，但該值不應切碎cache時。
- **怎麼設定／驗證：** 將origin需要、但不改變可快取response的欄位列入allow list；它必須與cache policy一起附到同一cache behavior。
- **常見錯法：** 以origin request policy轉送會改變response的欄位、卻不加入cache key，可能讓不同使用者共用錯誤cached response。

#### `cache behaviors`

- **控制什麼：** 依path pattern選擇origin、allowed methods、viewer protocol、cache policy、origin request policy與edge function。
- **何時需要：** 同一distribution同時服務static assets、dynamic API與下載路徑，且各自需要不同cache/security設定時。
- **怎麼設定／驗證：** 建立default behavior，再以更具體path patterns建立額外behaviors；檢查pattern precedence與每條路徑的methods、policies及origin。
- **常見錯法：** 只修改default behavior卻忘記更具體pattern會先匹配，可能讓API被意外cache或讓敏感路徑繞過預期policy。

#### `OAC`

- **控制什麼：** Origin Access Control讓CloudFront以SigV4代表distribution向private S3 REST origin送出已簽章request。
- **何時需要：** S3 objects要公開給網站使用者，但禁止使用者直接以S3 URL讀取時。
- **怎麼設定／驗證：** 建立AWS::CloudFront::OriginAccessControl並設SigningBehavior=always、SigningProtocol=sigv4；distribution origin引用它，bucket policy只允許cloudfront.amazonaws.com且限制SourceArn。
- **常見錯法：** OAC不支援S3 website endpoint；只建立OAC卻沒有更新bucket policy，CloudFront會得到403。

#### `TTL`

- **控制什麼：** Time to live決定edge中的object多久視為fresh。到期後CloudFront才回origin重新驗證或取得內容。
- **何時需要：** 在內容新鮮度、origin負載、延遲與cache hit ratio之間做取捨時。
- **怎麼設定／驗證：** 以cache policy設定MinimumTTL、DefaultTTL、MaximumTTL，並理解origin的Cache-Control/Expires如何參與。三者皆為0會停用cache。
- **常見錯法：** Minimum TTL大於0時，即使origin回no-cache/no-store/private，CloudFront仍至少cache該時間；敏感dynamic response不可盲目套高TTL。

#### `WAF`

- **控制什麼：** Web ACL在edge檢查HTTP request，可依IP、URI、header、body、rate與managed signatures做allow/block/count。
- **何時需要：** 要在流量回到origin前阻擋bot、SQL injection、XSS、惡意IP或HTTP flood時。
- **怎麼設定／驗證：** 建立global-scope Web ACL、先以Count觀察managed rules，再關聯distribution並開啟logging與rate-based rules。
- **常見錯法：** WAF不是IAM，也不保證origin私有；沒有OAC/origin restriction時，攻擊者仍可能直接打後端繞過WAF。

#### `geo restriction`

- **控制什麼：** 依viewer國家位置allow或deny整個distribution內容，是粗粒度的地理存取控制。
- **何時需要：** 授權、法規或商業合約要求阻擋少數國家，且不需依path/user做複雜判斷時。
- **怎麼設定／驗證：** 在distribution設定whitelist或blacklist country codes；需要更細規則、例外或logging時改用WAF geo match。
- **常見錯法：** Geo restriction不是強身份驗證，VPN/proxy可能改變來源位置；敏感資料仍需application authorization與signed URL/cookie。

### AWS Global Accelerator：逐項設定說明

#### `listeners`

- **控制什麼：** Listener定義Global Accelerator接受的TCP或UDP port ranges；client連到兩個static anycast IP後，流量才依此入口進入accelerator。
- **何時需要：** 需要固定全球IP、非HTTP protocol，或不可快取的TCP/UDP application經AWS全球骨幹加速時。
- **怎麼設定／驗證：** 建立TCP/UDP listener與最小port ranges，設定client affinity需求；確認regional endpoints及security rules接受相同目的ports。
- **常見錯法：** Listener不是TLS certificate終止點；若後端要TLS，通常仍由NLB/ALB/application處理。Port設太寬也會擴大暴露面。

#### `endpoint groups`

- **控制什麼：** 每個endpoint group對應一個AWS Region，保存該Region的endpoints、health port/protocol與整體traffic dial。
- **何時需要：** 同一accelerator要在多Region間依健康與比例分配流量，或執行regional evacuation時。
- **怎麼設定／驗證：** 為每個Region建立group，加入ALB、NLB、EC2或EIP endpoints，設定health check與traffic dial；從多地client驗證實際Region。
- **常見錯法：** 建立第二group不等於application已多Region就緒；資料、identity、quota與failover dependencies仍要同步設計。

#### `traffic dial`

- **控制什麼：** 以0–100百分比調整某個endpoint group可接收的整體流量比例，常用於Region排空、canary或逐步恢復。
- **何時需要：** 跨Regionmigration、事件期間降低特定Region流量，或先用少量production traffic驗證新Region時。
- **怎麼設定／驗證：** 先確認另一Region有足夠capacity與資料，再逐步調整dial並監控business SLO；預先定義回調與rollback門檻。
- **常見錯法：** Traffic dial不是精準逐request比例，也不修正stateful session與資料一致性；瞬間設為0仍需考慮既有connections。

#### `endpoint weight`

- **控制什麼：** 在同一regional endpoint group內設定各endpoint的相對權重，控制新flows如何分配到多個ALB、NLB、EC2或EIP。
- **何時需要：** 同Region內做blue/green、capacity比例分配，或逐步引入新endpoint時。
- **怎麼設定／驗證：** 為healthy endpoints設定0–255相對weight，以小比例開始並觀察error、latency與capacity；確認health check能正確摘除故障端點。
- **常見錯法：** Weight不是保證百分比，少量flows會有偏差；把不健康endpoint權重設高也不會讓它恢復。

#### `health checks`

- **控制什麼：** Global Accelerator檢查regional endpoints能否服務，並把新flows導向健康端點；對ALB/NLB可沿用其健康狀態。
- **何時需要：** 要求endpoint或整個Region故障時自動停止接收新連線時。
- **怎麼設定／驗證：** 設定代表真實服務的protocol、port、path、interval與threshold，並以故障注入量測偵測及重新導流時間。
- **常見錯法：** 只檢查TCP port可能產生假健康；切走新flows也不會自動終止或遷移已建立的長連線。

#### `client affinity`

- **控制什麼：** 選擇NONE或SOURCE_IP，決定同一來源IP建立的新connections是否傾向被導到同一endpoint。
- **何時需要：** Application仍依賴endpoint-local session，且來源IP能合理代表client時，才作為相容性措施。
- **怎麼設定／驗證：** 在listener設定ClientAffinity；用多client/NAT情境驗證分布，並讓session逐步外部化到shared store。
- **常見錯法：** 大量使用者經同一NAT會被誤認為單一client並造成熱點；affinity也不能在endpoint故障時保存local session。

### Lambda@Edge：逐項設定說明

#### `event trigger`

- **控制什麼：** 決定函式在viewer request、origin request、origin response或viewer response哪個CloudFront階段執行；不同階段的cache關係、可見欄位與限制不同。
- **何時需要：** 需要在進cache前改URI／認證、只在回源時選origin，或在response送給viewer前補header時。
- **怎麼設定／驗證：** 先畫出viewer→cache→origin flow，再把function association綁到正確cache behavior與event type；分別測cache hit與miss。
- **常見錯法：** 綁錯階段可能讓函式每次request都執行、破壞cache key，或以為能修改該階段不可變更的header/status。

#### `us-east-1 function version`

- **控制什麼：** Lambda@Edge函式必須建立在us-east-1並使用已發布的numbered version；CloudFront把該immutable版本複寫到edge locations。
- **何時需要：** 任何Lambda@Edge deployment、更新或rollback都需要明確版本，而不能直接關聯$LATEST或alias。
- **怎麼設定／驗證：** 在us-east-1建立函式、publish version，再把version ARN關聯到distribution behavior；更新時發布新版本並等待distribution部署完成。
- **常見錯法：** 修改$LATEST不會改變已部署edge程式；過早刪除仍被複寫使用的version會失敗，更新也不是立即全球生效。

#### `IAM execution role`

- **控制什麼：** 允許Lambda與edgelambda service principals assume role，並授予函式寫logs或呼叫其他AWS APIs所需的最小權限。
- **何時需要：** 函式需要記錄執行結果、讀取外部設定或存取AWS資源，且必須保留可稽核的最小權限邊界時。
- **怎麼設定／驗證：** Trust policy同時允許lambda.amazonaws.com與edgelambda.amazonaws.com；permissions只加入必要actions/resources，並檢查跨Region資源行為。
- **常見錯法：** 只加入一般Lambda trust會讓edge replication/執行失敗；給AdministratorAccess會把全球edge code的blast radius放大。

#### `memory／timeout`

- **控制什麼：** Memory同時影響可用CPU，timeout限制每次edge事件可執行時間；不同event type可用上限並不相同。
- **何時需要：** 程式包含JWT驗證、rewrite或network call，需要在viewer latency與運算需求間取捨時。
- **怎麼設定／驗證：** 依該event type的官方quota設定最小足夠memory/timeout，用真實payload量測p95/p99，避免在edge做慢或不可預測的遠端依賴。
- **常見錯法：** 把timeout調大不會讓viewer願意久等；遠端API、冷啟動與大dependency會直接增加每個request延遲與費用。

#### `include body`

- **控制什麼：** 讓request trigger取得經Base64編碼且受大小限制的request body，以便檢查或修改POST/PUT內容。
- **何時需要：** 只有edge邏輯確實需要讀取小型body，例如特定表單驗證或routing訊號時才開啟。
- **怎麼設定／驗證：** 在function association啟用IncludeBody，處理encoding、truncation與content type，並以接近大小上限的request測試。
- **常見錯法：** Body可能被截斷，敏感內容也可能進入logs；大型upload與完整API validation不適合放在Lambda@Edge。

#### `logs`

- **控制什麼：** 函式在最接近執行edge location的AWS Region寫入CloudWatch Logs，而不是只集中在us-east-1。
- **何時需要：** 需要除錯regional使用者錯誤、追蹤deployment版本或建立edge執行證據時。
- **怎麼設定／驗證：** 在可能執行的Regions建立log查詢／centralization策略，輸出request ID與版本但遮罩token、cookie及PII，設定retention。
- **常見錯法：** 只查us-east-1會誤以為沒有執行；把完整headers/body寫log會造成跨Region敏感資料與成本問題。

#### `deployment restrictions`

- **控制什麼：** 描述Lambda@Edge與一般regional Lambda不同的功能邊界，例如版本、Region、runtime、environment、VPC與deployment lifecycle限制。
- **何時需要：** 把既有Lambda搬到edge，或選擇Lambda@Edge、CloudFront Functions與regional service之間的執行位置時。
- **怎麼設定／驗證：** 在設計前核對目前官方限制與quota；將configuration打包進版本或安全外部來源，建立staged distribution與可回復舊版本。
- **常見錯法：** 假設一般Lambda所有features都可用會在部署時失敗；edge code也不適合承擔database transaction或長時間business workflow。

## 可以直接對照 AWS 的設定範例

### CloudFront：Cache Policy、OAC 與 private S3 origin

```yaml
Resources:
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

```

1. Accept-Language與version會改變cache key；只有真的改變response的值才應加入，否則每種組合都建立新cache object。
2. OAC以SigV4簽到S3 REST origin。Bucket仍需policy允許cloudfront.amazonaws.com並以distribution SourceArn限制。
3. DefaultTTL是一小時，但origin Cache-Control與Min/MaxTTL仍會共同決定freshness；敏感dynamic response不應套用此static policy。

### S3 bucket policy：只允許指定 CloudFront distribution

```json
{
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
}
```

1. Principal是CloudFront service，不是anonymous *；SourceArn把權限縮到單一distribution。
2. Resource使用object ARN的/*，因GetObject是object-level action。Bucket保持四個Block Public Access flags開啟。
3. 如果改用S3 website endpoint，OAC不適用；website endpoint屬custom origin且通常需要公開讀取，安全模型不同。

## 讀到這裡，請用自己的話說一次

1. Amazon CloudFront的責任：在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。
2. 底層機制：DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。
3. 第一個要看的設定：origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
4. 選擇邏輯：可cache HTTP內容用CloudFront；需要static anycast IP或TCP/UDP加速用Global Accelerator。
5. 不要混淆：AWS Global Accelerator的責任是「以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。」；它不會自動取代Amazon CloudFront。
6. 替換訊號：需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。
7. 最常見錯法：將動態、不可cache且需固定IP的工作硬套CloudFront，或忽略cache key造成資料洩漏。
8. 可移植原則：move computation and copies toward users only when semantics permit。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon CloudFront | 在edge快取與代理HTTP內容，降低全球使用者延遲並保護origin。 | DNS把使用者導向edge POP；cache key、TTL與origin policy決定何時命中或回源。 | 可快取的HTTP內容、S3私有origin、全球網站、API加速與edge security。 | 需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。 |
| AWS Global Accelerator | 以兩個static anycast IP把TCP/UDP流量導入AWS全球骨幹並做健康端點切換。 | Anycast將client送到最近edge，再依endpoint group、weight與health導向regional endpoint。 | 遊戲、VoIP、IoT、固定IP allowlist或不可快取的全球TCP/UDP應用。 | HTTP內容需要cache、header/path routing或edge function時選CloudFront。 |
| Lambda@Edge | 在CloudFront edge事件上執行Lambda程式，依request/response修改header、URI、認證或origin選擇。 | CloudFront在viewer request、origin request、origin response或viewer response階段呼叫已複寫到edge的函式版本。 | 需要依viewer request做輕量認證、URL rewrite、header處理或動態origin selection時。 | 只需簡單低延遲JavaScript處理可比較CloudFront Functions；完整API/business logic應放regional service。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | CloudFront Functions/Lambda@Edge可在edge改寫請求，但會增加部署與除錯面。 | 只有當題目條件明確改變時才可能合理。 | 將動態、不可cache且需固定IP的工作硬套CloudFront，或忽略cache key造成資料洩漏。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「CloudFront Functions/Lambda@Edge可在edge改寫請求，但會增加部署與除錯面。」之間做選擇。
- 認得常考設定：origins、cache policy、origin request policy、behaviors、OAC、TTL、WAF與geo restriction。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要非HTTP的TCP/UDP加速或固定anycast IP時選Global Accelerator。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜17.1 OAC的S3 origin與bucket policy邊界

團隊建立CloudFront distribution E123EXAMPLE，S3 bucket必須維持私有，且只有這個distribution能執行s3:GetObject。下列哪個origin與bucket-policy設計符合要求？

A. 把S3 website endpoint設為custom origin；policy允許Principal為cloudfront.amazonaws.com且不限制distribution
B. 使用S3 REST endpoint與OAC；bucket policy允許CloudFront service principal執行GetObject，並以AWS:SourceArn限制為E123EXAMPLE
C. 保留S3 REST endpoint，但把bucket設public-read，僅靠CloudFront URL不公開來避免繞過
D. 使用Global Accelerator指向bucket regional endpoint，讓固定anycast IP代替bucket authorization

**答案：B**

- **A：** 不正確。S3 website endpoint在CloudFront中屬於custom origin，不支援OAC；而缺少distribution SourceArn條件也會讓授權範圍大於題目指定的單一distribution。
- **B：** 正確。OAC讓CloudFront簽署送往private S3 REST origin的request；bucket policy以cloudfront.amazonaws.com為Principal，並用AWS:SourceArn綁定指定distribution。
- **C：** 不正確。Public-read會允許client直接呼叫S3 URL，繞過CloudFront cache與edge controls；隱藏URL不是authorization，也不符合bucket必須私有的條件。
- **D：** 不正確。Global Accelerator提供L4 anycast入口與endpoint routing，不會替S3提供object cache、SigV4 origin access或bucket policy的service-principal授權。

**事實查證：** [Restrict access to an Amazon S3 origin - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)

### 練習題 2｜SAA｜17.2 CloudFront behavior precedence

同一 distribution的 /assets/*要快取一天並到 S3，/api/*不可快取且到 ALB。應如何設定？

A. 只提高 default TTL
B. 建立不同 origins與 ordered cache behaviors，讓 path pattern映射到各自 cache/origin policies
C. 用 Route 53依 URL path選 endpoint
D. 用 NLB listener rule解析 path

**答案：B**

- **A：** 不正確。單一 default TTL不能同時表達 static與 API語意。
- **B：** 正確。CloudFront依第一個 matching behavior套用 origin與 policies；API需 disabled/適當 cache policy。
- **C：** 不正確。DNS query只包含hostname與record type，看不到後續HTTP request的URL path，因此Route 53無法把/assets與/api送往不同origins。
- **D：** 不正確。Network Load Balancer在L4依IP、port與protocol轉送connection，不解析HTTP URL path；這種分流應由CloudFront cache behaviors或ALB完成。

**事實查證：** [Cache behavior settings - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesCacheBehavior.html)

### 練習題 3｜SAP｜17.3 Cache key 與 origin request policy（選兩項）

Origin response會因 Accept-Language與 version query不同；X-Trace-Id只供 origin logging且不改內容。哪兩項設定正確？

A. 把 Accept-Language與 version納入 cache key
B. 把所有 headers/cookies/query都納入 cache key
C. 用 origin request policy轉送 X-Trace-Id，但不把它納入 cache key
D. 不把 user-specific Authorization納入 key卻快取私人 response
E. 完全不轉送 version query

**答案：A、C**

- **A：** 正確。會改變 representation的欄位必須區分 cached objects。
- **B：** 不正確。無差別加入會造成 cache fragmentation與低 hit ratio。
- **C：** 正確。只供 origin使用的欄位可轉送但不建立更多 cache variants。
- **D：** 不正確。若Authorization會改變private response卻未納入cache isolation，同一cache object可能被回給另一位使用者；應停用快取或以安全方式隔離。
- **E：** 不正確。Origin需要version query才能產生正確內容；完全不轉送會讓origin收到不同語意的request，即使cache key包含version也無法修復。

**事實查證：** [Understand the cache key - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[Control origin requests with a policy - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html)

### 練習題 4｜SAP｜17.4 Minimum TTL 與 no-store

Origin回 Cache-Control: no-store，但 CloudFront cache policy的 Minimum TTL為60秒。實際風險是什麼？

A. no-store永遠覆寫所有 CloudFront policy
B. WAF會自動把 TTL歸零
C. CloudFront仍可能至少快取60秒；敏感內容應使用 Minimum TTL=0或 caching disabled的政策
D. OAC會決定 cache duration

**答案：C**

- **A：** 不正確。若 Minimum TTL大於0，CloudFront可忽略 origin的 no-cache/no-store/private指示到該最小值。
- **B：** 不正確。AWS WAF評估符合scope的web requests與rules，不管理CloudFront cache TTL；即使封鎖惡意request，也不會改變既有object freshness。
- **C：** 正確。Cache policy的 minimum是強制下限，敏感 response不能只依賴 origin header。
- **D：** 不正確。OAC控制 origin authentication，不控制 TTL。

**事實查證：** [Cache behavior settings - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesCacheBehavior.html#DownloadDistValuesMinTTL)

### 練習題 5｜SAP｜17.5 CloudFront VPC origin隔離ALB

CloudFront前有WAF，但攻擊者可直接呼叫internet-facing ALB DNS繞過edge controls。應用相容於CloudFront VPC origins，且沒有保留public ALB的需求。哪個改善提供最強的origin isolation？

A. 保留public ALB，只把DNS名稱改成隨機字串，讓攻擊者較難猜到origin
B. 只在CloudFront啟用geo restriction，不修改ALB的public reachability
C. 把ALB改為internal並建立CloudFront VPC origin；以security group限制origin流量，移除Internet直接到ALB的路徑
D. 保留public ALB並只降低Route 53 TTL，讓direct request較快失效

**答案：C**

- **A：** 不正確。隨機或較長的DNS名稱只增加猜測成本，並沒有移除Internet到origin的route或建立可驗證授權，因此不構成可靠的origin isolation。
- **B：** 不正確。Geo restriction只套用經CloudFront的viewer request；攻擊者若直接連internet-facing ALB，仍可完全繞過該edge policy。
- **C：** 正確。CloudFront VPC origin可連到private subnet中的internal ALB，使origin不再具有Internet主動入口；再以security group限制來源，能把edge path變成可驗證的唯一入口。
- **D：** 不正確。DNS TTL控制名稱回答的cache時間，不限制client直接連到public ALB，也不會讓已知origin DNS名稱失效或建立authorization。

**事實查證：** [Restrict access with VPC origins - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)、[Restrict access with VPC origins: security groups - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html#vpc-origins-security-groups)

### 練習題 6｜SAA｜17.6 UDP、固定 anycast IP 與快速切換

全球遊戲使用 UDP，需要兩個可供企業 firewall allowlist的固定入口 IP，且 regional endpoint不健康時快速切換。應選什麼？

A. CloudFront distribution
B. Route 53加兩個會變動的 ALB IP
C. ALB UDP listener
D. Global Accelerator standard accelerator，配置 UDP listener與 regional endpoint groups

**答案：D**

- **A：** 不正確。CloudFront是HTTP(S) CDN，依cache behavior處理web requests，不提供任意UDP protocol的listener或固定anycast入口。
- **B：** 不正確。Application Load Balancer不提供可供企業firewall長期allowlist的固定regional IP，也不支援遊戲所需的UDP listener。
- **C：** 不正確。Application Load Balancer只支援HTTP、HTTPS與gRPC等L7協定，沒有UDP listener；此需求應評估Global Accelerator或NLB。
- **D：** 正確。GA提供 static anycast IP、TCP/UDP與 health-based endpoint routing。

**事實查證：** [What is AWS Global Accelerator? - AWS Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)

### 練習題 7｜SAP｜17.7 GA traffic dial 與 endpoint weight

Global Accelerator要先把少量新 flows送到新 Region，且該 Region內兩個 endpoints要按不同比例分配。哪個設定組合正確？

A. Route 53 TTL控制 Region比例；ALB cookie控制 endpoint比例
B. Client affinity同時控制兩種比例
C. Traffic dial控制 endpoint group/Region整體份額；endpoint weight控制該 group內 endpoints相對份額
D. CloudFront behavior priority控制 GA

**答案：C**

- **A：** 不正確。Global Accelerator使用固定anycast入口，traffic dial在service data plane調整送往endpoint group的新flow比例，不靠DNS TTL生效。
- **B：** 不正確。Affinity維持 client到 endpoint的傾向，不是 rollout比例控制。
- **C：** 正確。Traffic dial控制送往整個Region endpoint group的份額，endpoint weight再控制group內target相對份額；兩層分別管理新連線分配。
- **D：** 不正確。CloudFront與Global Accelerator是獨立data planes，CloudFront cache behavior priority不會改變GA endpoint group或endpoint weight。

**事實查證：** [Use traffic dials to adjust traffic flow to Regions - AWS Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups-traffic-dial.html)、[How endpoint weights work to manage traffic volume - AWS Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoints-endpoint-weights.html)

### 練習題 8｜SAP｜17.8 GA client affinity 邊界

Stateful client希望盡量回同一 GA endpoint，但 endpoint故障時仍需切換。哪個敘述正確？

A. Affinity保證 client永遠不切換，所以可把 session只存單機
B. ALB cookie可控制所有 UDP GA flows
C. 提高 DNS TTL即可固定 GA endpoint
D. 可使用 client affinity，但它不是 durable session store；健康切換優先，應用 state仍需外部化或恢復

**答案：D**

- **A：** 不正確。Endpoint失效或 routing改變時 affinity不能提供永久保證。
- **B：** 不正確。UDP沒有 HTTP cookie語意，GA affinity設定也不同。
- **C：** 不正確。Client連的是 GA static IP，DNS TTL不固定後端。
- **D：** 正確。Affinity改善連續性，但 resilience必須由應用 state設計承擔。

**事實查證：** [How client affinity works in Global Accelerator - AWS Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-listeners-client-affinity.html)

### 練習題 9｜SAA｜17.9 CloudFront Functions與Lambda@Edge能力邊界

需求A只在viewer request改寫一個header；需求B必須在origin request讀取request body，呼叫外部HTTP服務後再決定送往哪個origin。最佳選擇？

A. A用CloudFront Functions；B用Lambda@Edge的origin-request event，並遵守body、network、timeout、us-east-1與已發布版本等限制
B. 兩者全部放 viewer function且任意呼叫 VPC
C. 用 GA listener修改 HTTP headers
D. 兩者都必須用 regional EC2

**答案：A**

- **A：** 正確。CloudFront Functions適合極短的viewer事件轉換且不提供network access；Lambda@Edge可在origin-facing event包含body並呼叫網路，但函式必須在us-east-1使用已發布版本，且受事件、body與timeout限制。
- **B：** 不正確。CloudFront Functions沒有network access，也不能處理origin-request event或request body；Lambda@Edge同樣不能被假設具有任意VPC連線能力。
- **C：** 不正確。Global Accelerator是L4全球入口，依IP、port與endpoint health轉送TCP/UDP flow，不解析HTTP header、request body或CloudFront origin event。
- **D：** 不正確。需求A可在edge以CloudFront Functions低延遲完成；需求B雖需Lambda@Edge，但不代表兩者都必須回到自管regional EC2執行。

**事實查證：** [Differences between CloudFront Functions and Lambda@Edge - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/edge-functions-choosing.html)、[Restrictions on Lambda@Edge - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-edge-function-restrictions.html)

### 練習題 10｜SAP｜17.10 同產品分離 HTTP 與 TCP 路徑（選兩項）

產品同時提供可快取的 HTTP下載與不可快取的 proprietary TCP realtime feed。哪兩項架構合理？

A. 所有流量依序 GA→CloudFront
B. HTTP下載使用 CloudFront負責 cache、TLS與 edge security
C. CloudFront直接代理 proprietary TCP
D. Realtime TCP使用 Global Accelerator導向 regional NLB/EC2 endpoints
E. GA提供 CloudFront cache key

**答案：B、D**

- **A：** 不正確。CloudFront只處理HTTP(S)，Global Accelerator則處理TCP/UDP flow；兩者不是所有protocol都必須依序經過的固定串鏈。
- **B：** 正確。CloudFront理解 HTTP與 cache semantics。
- **C：** 不正確。CloudFront只支援其定義的HTTP(S) viewer與origin流程，不代理任意proprietary TCP protocol；realtime feed應使用L4入口。
- **D：** 正確。GA支援 TCP/UDP與 static anycast入口，不提供內容快取。
- **E：** 不正確。Cache key是CloudFront決定object cache identity的概念；Global Accelerator不快取content，也不會替CloudFront建立cache key。

**事實查證：** [What is Amazon CloudFront? - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)、[What is AWS Global Accelerator? - AWS Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「可cache HTTP內容用CloudFront；需要static anycast IP或TCP/UDP加…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「全球使用者需要降低延遲、保護origin或改善非HTTP連線路徑。」，所以「可cache HTTP內容用CloudFront；需要static anycast IP或TCP/UDP加速用Global Accelerator。」能直接滿足它；若constraint改成「CloudFront Functions/Lambda@Edge可在edge改寫請求，但會增加部署與除錯面。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「可cache HTTP內容用CloudFront；需要static anycast IP或TCP/UDP加速用Global Accelerator。」。替代方案「CloudFront Functions/Lambda@Edge可在edge改寫請求，但會增加部署與除錯面。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將動態、不可cache且需固定IP的工作硬套CloudFront，或忽略cache key造成資料洩漏。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「全球使用者需要降低延遲、保護origin或改善非HTTP連線路徑。」，排除會導致「將動態、不可cache且需固定IP的工作硬套CloudFront，或忽略cache key造成資料洩漏。」的選項，再選「可cache HTTP內容用CloudFront；需要static anycast IP或TCP/UDP加速用Global Accelerator。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures；SAP-1.1 Architect network connectivity strategies。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「可cache HTTP內容用CloudFront；需要static anycast IP或TCP/UDP加速用Global Accelerator。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「move computation and copies toward users only when semantics permit」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 18 章　ALB、NLB 與 Gateway Load Balancer

負載平衡器在不同層理解不同資訊，影響routing、來源IP、TLS與throughput。

## 跟著一個封包走：先從故事開始

如果今天由你值班，收到的需求可能是這樣：多租戶API依host routing，支付協定走TLS passthrough，所有流量需經防火牆。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：負載平衡器在不同層理解不同資訊，影響routing、來源IP、TLS與throughput。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：Load balancer像接待櫃檯：ALB會讀懂HTTP內容再分流，NLB主要依連線資訊轉送，GWLB則把流量帶去接受安全檢查。 這只是起點，因為接待櫃檯不能修復後端保存錯誤狀態，也不能取代application authorization。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由Application Load Balancer承接主要責任，以Network Load Balancer檢查替代條件，並用「HTTP path/host routing用ALB；高效TCP/UDP與static IP用NLB；虛擬安全設備鏈用GWLB。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：多租戶API依host routing，支付協定走TLS passthrough，所有流量需經防火牆。

先看application需要理解到哪一層

HTTP / HTTPS request
  └─ host、path、header routing ──> ALB ──> application targets

TCP / UDP / TLS flow
  └─ static IP、高連線吞吐 ──────> NLB ──> network targets

需要透明檢查的IP flow
  └─ GENEVE封裝 ─────────────────> GWLB ──> firewall / IDS appliances

三者都是load balancing家族，但處理的protocol語意與target完全不同。

失敗時先找：因NLB較快就用它處理需要path routing的API，結果把邏輯推回應用程式。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問Application Load Balancer有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Application Load Balancer和Network Load Balancer並不是兩個任意的產品名稱。前者適合本章，是因為「HTTP path/host routing用ALB；高效TCP/UDP與static IP用NLB；虛擬安全設備鏈用GWLB。」直接回應了眼前的問題；後者描述的「NLB可把流量送ALB組合L4入口與L7routing，但增加元件與診斷層。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：因NLB較快就用它處理需要path routing的API，結果把邏輯推回應用程式。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「choose the lowest network layer that understands the required decision」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Application Load Balancer | 提供HTTP/HTTPS Layer 7 routing與web workload入口。 | 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。 |
| Network Load Balancer | 提供高吞吐、低延遲Layer 4 TCP/UDP/TLS load balancing與static IP。 | 以flow hash選target，通常保留client source IP；可在listener做TLS termination。 |
| Gateway Load Balancer | 透明插入並擴展第三方firewall、IDS/IPS等virtual appliances。 | GENEVE封裝流量送到appliance fleet，endpoint與route確保雙向對稱路徑。 |

## 把全圖套進一個具體案例

**場景：** 多租戶API依host routing，支付協定走TLS passthrough，所有流量需經防火牆。

1. 故事的起點：多租戶API依host routing，支付協定走TLS passthrough，所有流量需經防火牆。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Application Load Balancer負責「提供HTTP/HTTPS Layer 7 routing與web workload入口。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Network Load Balancer、Gateway Load Balancer各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「因NLB較快就用它處理需要path routing的API，結果把邏輯推回應用程式。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「極低延遲TCP/UDP、static IP或保留source IP需求用NLB。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 再往底層走：這一章真正容易混淆的地方

### ALB 的四層物件不要混在一起

Load balancer是入口資源；listener綁定port/protocol；listener rules依priority與conditions選action；target group保存targets、health check與routing attributes。看到HTTPS 443、path routing、target health、stickiness時，要先判斷它分別屬於listener、rule還是target group，否則即使服務選對也會把參數設在錯的地方。

### Stickiness 解決的是相容性，不是根治 state

正常情況ALB可把每個request送到不同healthy target。若legacy app把session存在單機memory，stickiness用load-balancer或application cookie讓client暫時黏到同一target。但target仍可能失效或scale in，負載也可能不均。長期設計應把session放到ElastiCache、DynamoDB或其他shared state，讓web tier保持stateless。

### ALB、NLB、GWLB 的答案翻轉點

需要HTTP host/path/header routing、WAF或OIDC時選ALB；需要TCP/UDP/TLS、static IP、極高連線吞吐或PrivateLink provider時選NLB；要透明插入firewall/IDS appliance並以GENEVE保留flow資訊時選GWLB。『效能更快』不是單獨理由，真正差異是protocol semantics、target type與security/data-path責任。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### ALB Mutual TLS：HTTPS 不只讓 client 驗證 server，也能反過來驗證 client

一般 TLS 只要求 server 出示 certificate；mTLS 在 handshake 時也要求 client certificate。這適合 B2B API、受管設備或服務間連線，但 client certificate 只建立『這張憑證受信任』，application 仍要把 certificate subject／serial 映射到 tenant、role 或 device authorization。

```text
client cert + TLS ClientHello
          │
          ▼
ALB HTTPS listener ─ trust store / CRL ─ verify
          │ X-Amzn-Mtls-* headers
          ▼
application ─ tenant/device authorization ─ business action
```

#### Listener 上真正需要決定的設定

```YAML
https_listener:
  port: 443
  certificate: server-certificate-arn
  mutual_authentication:
    mode: verify
    trust_store: trusted-client-ca-bundle
    ignore_client_certificate_expiry: false
```

1. verify mode 由 ALB 驗證 X.509 client chain；passthrough 則把 chain 交給 target 驗證。
2. Trust store 決定哪些 CA 被信任；CRL 可用於撤銷檢查。這不是一般 security group 能表達的身份條件。
3. Backend 必須只信任由 ALB 產生／覆寫的 mTLS headers，並避免可繞過 ALB 的直接入口。

**選擇邊界：** 一般 public website 常用 OIDC/Cognito/session；設備或 B2B machine identity 才常用 mTLS。若需要應用內細粒度權限，仍需 JWT／policy engine／database authorization。

**考試範圍：** SAA 需分清 TLS termination、listener certificate、target protocol 與 health check；mTLS trust store、revocation、passthrough/verify 與 backend authorization 是 SAP／進階安全邊界。

- [AWS：Mutual authentication with TLS in ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/mutual-authentication.html)

## 需要時再查：四個閱讀支點

### Application Load Balancer

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：負載平衡器在不同層理解不同資訊，影響routing、來源IP、TLS與throughput。
- **具體例子／邊界：** 在「多租戶API依host routing，支付協定走TLS passthrough，所有流量需經防火牆。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Network Load Balancer

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：NLB可把流量送ALB組合L4入口與L7routing，但增加元件與診斷層。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：因NLB較快就用它處理需要path routing的API，結果把邏輯推回應用程式。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：choose the lowest network layer that understands the required decision。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### stickiness

以cookie讓同一client暫時持續導向同一target；它是相容legacy state的折衷，不是高可用session store。

### throughput

每秒能傳輸的資料量，偏向大型sequential I/O或network流量。

### listener

在load balancer指定protocol/port等待client connection的入口。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### Layer 4

依IP、port與TCP/UDP flow處理流量，不理解HTTP path/headers；NLB屬於此類。

### Layer 7

理解HTTP等application protocol，可依host/path/header做routing；ALB與CloudFront屬於此類。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

### UDP

不先建立可靠connection的datagram協定，延遲低但application需自行處理遺失與順序。

## 回到 AWS：Components、功用與責任邊界

### Application Load Balancer

- **功用：** 提供HTTP/HTTPS Layer 7 routing與web workload入口。
- **底層機制：** 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。
- **關鍵設定：** listeners/certificates、rules priority、target type、health path、stickiness、idle timeout與access logs。
- **選擇時機：** 網站、microservices、ECS dynamic ports、gRPC或需要content-based routing。
- **替換時機：** 極低延遲TCP/UDP、static IP或保留source IP需求用NLB。

### Network Load Balancer

- **功用：** 提供高吞吐、低延遲Layer 4 TCP/UDP/TLS load balancing與static IP。
- **底層機制：** 以flow hash選target，通常保留client source IP；可在listener做TLS termination。
- **關鍵設定：** TCP/UDP/TLS listeners、IP/instance/ALB target、cross-zone、proxy protocol、preserve client IP與health check。
- **選擇時機：** 非HTTP protocol、突然高連線量、static EIP或PrivateLink provider。
- **替換時機：** 需要path/host routing、WAF或HTTP redirect時選ALB；virtual appliances用GWLB。

### Gateway Load Balancer

- **功用：** 透明插入並擴展第三方firewall、IDS/IPS等virtual appliances。
- **底層機制：** GENEVE封裝流量送到appliance fleet，endpoint與route確保雙向對稱路徑。
- **關鍵設定：** GENEVE 6081、GWLB endpoints、route tables、target health、appliance mode與cross-zone。
- **選擇時機：** 集中deep packet inspection且需水平擴展appliances。
- **替換時機：** AWS-native stateful rules可直接用Network Firewall；一般app traffic用ALB/NLB。

## 考前與實作時再查：設定操作手冊

### Application Load Balancer：逐項設定說明

#### `listeners／certificates`

- **控制什麼：** Listener在指定port/protocol接收client connection；HTTPS listener使用certificate終止TLS，再把HTTP/HTTPS送往target group。
- **何時需要：** 網站要在443提供TLS、將80 redirect到443，或同一ALB承接不同入口時。
- **怎麼設定／驗證：** 建立listener的Protocol/Port與DefaultActions；HTTPS指定ACM CertificateArn與security policy，可加入多張SNI certificates。
- **常見錯法：** 只有ALB listener開443但security group未開，或certificate位於錯誤Region／網域不匹配，client仍無法完成TLS。

#### `rules priority`

- **控制什麼：** Listener rules依數字由小到大評估conditions；第一個匹配的forward、redirect、fixed-response或authentication action生效，default rule最後執行。
- **何時需要：** 依host、path、header、method、query或source IP把microservices導向不同target groups時。
- **怎麼設定／驗證：** 為每條非default rule指定唯一Priority與Conditions，最具體規則放在適當順序；部署前測試重疊patterns。
- **常見錯法：** 較寬的/*規則優先匹配會吃掉後面的/admin/*；priority不是權重，也不代表流量百分比。

#### `target type`

- **控制什麼：** 決定target group註冊的是EC2 instance ID、IP address或Lambda。它影響封包目的、port、VPC限制與container整合。
- **何時需要：** ECS awsvpc tasks通常用ip；傳統EC2可用instance；ALB直接觸發函式才用lambda。
- **怎麼設定／驗證：** 建立target group時設定TargetType，並註冊相同類型targets；此選擇建立後不能任意改成另一類型，通常需新target group。
- **常見錯法：** Fargate沒有可註冊的host instance port卻選instance target，或跨VPC IP不符合允許範圍，會讓targets無法healthy。

#### `health path`

- **控制什麼：** ALB週期性呼叫target的health-check path；只有達到healthy threshold的targets才接收正常流量。
- **何時需要：** 應用需要排除未啟動、依賴失敗或正在drain的instances/tasks時。
- **怎麼設定／驗證：** 在target group設定HealthCheckPath、port/protocol、interval、timeout、healthy/unhealthy thresholds與Matcher success codes。
- **常見錯法：** Health path執行昂貴database query會放大故障；只回固定200又可能讓已無法服務的target被判定healthy。

#### `stickiness`

- **控制什麼：** Stickiness又稱session affinity，透過cookie讓同一client在一段時間內持續被導向同一target，而不是每個request重新分配。
- **何時需要：** Legacy application把session只放在單台server記憶體，短期無法搬到shared session store時。
- **怎麼設定／驗證：** 在target group開啟stickiness.enabled，選lb_cookie或app_cookie並設定duration/name；CloudFormation使用TargetGroupAttributes。
- **常見錯法：** 它會造成負載不均、target replacement時session仍可能遺失，也不能取代共享session store；新系統優先保持stateless。

#### `idle timeout`

- **控制什麼：** 前端或後端connection在沒有傳輸資料多久後由ALB關閉，避免閒置connection永久占用資源。
- **何時需要：** 長輪詢、WebSocket、慢request或upload時間超過預設值，需要與application/client timeout協調時。
- **怎麼設定／驗證：** 在ALB attribute設定idle_timeout.timeout_seconds；讓client/application timeout略有明確層次，並測試中途無資料的connection。
- **常見錯法：** 只把值調得很大會保留大量dead connections；ALB timeout短於application工作時間常表現為client端502/504或重試。

#### `access logs`

- **控制什麼：** 記錄每個經ALB處理的request，包括client、target、latency、status、chosen rule與TLS資訊，輸出到S3。
- **何時需要：** 分析5xx、target latency、routing規則、security事件與稽核時。
- **怎麼設定／驗證：** 在load balancer attributes啟用access_logs.s3.enabled，指定bucket與prefix，並設定允許log delivery的bucket policy與retention。
- **常見錯法：** Access logs是延遲交付的request紀錄，不是即時metric；未設定資料保留、查詢partition與敏感欄位治理會造成成本與隱私問題。

### Network Load Balancer：逐項設定說明

#### `TCP／UDP／TLS listeners`

- **控制什麼：** Listener在指定port接受Layer 4 TCP、UDP、TCP_UDP或TLS connections；TLS listener可在NLB終止TLS後轉送到target group。
- **何時需要：** 需要高吞吐、低延遲、非HTTP protocol、static IP或保留來源IP的regional入口時。
- **怎麼設定／驗證：** 建立protocol/port與default target group；TLS listener附ACM certificate及security policy，並讓target protocol符合end-to-end encryption需求。
- **常見錯法：** NLB不提供ALB的path/host routing與WAF；把TLS終止位置搞錯會造成double TLS、明文hop或certificate不匹配。

#### `IP／instance／ALB target`

- **控制什麼：** Target type決定NLB把flow送到EC2 instance、具體IP或另一個ALB；它影響port、來源IP、跨VPC與container整合方式。
- **何時需要：** 傳統EC2可選instance，awsvpc/Fargate常選ip；需要NLB static IP加ALB Layer 7能力時可選ALB target。
- **怎麼設定／驗證：** 建立target group時選定TargetType並註冊符合範圍的targets；建立後若要換type，通常建立新target group再切listener。
- **常見錯法：** 把Fargate當instance target、註冊不支援的public IP，或忽略ALB target的port/health限制，會讓targets無法接流量。

#### `cross-zone`

- **控制什麼：** 決定每個NLB node只把流量送到同AZ targets，或也跨AZ分配到所有enabled-zone healthy targets。
- **何時需要：** 各AZ target容量不均、流量偏斜，且願意接受可能的跨AZdata processing cost時。
- **怎麼設定／驗證：** 在load balancer attribute設定load_balancing.cross_zone.enabled；比較各AZtarget數、flow分布、latency與cross-AZ bytes。
- **常見錯法：** 開啟可改善不均但不會增加總capacity；關閉時若某AZtarget不足，使用者可能在其他AZ仍健康時遇到壓力。

#### `Proxy Protocol v2`

- **控制什麼：** 在backend connection前附加二進位header，傳遞原始source/destination、port及PrivateLink endpoint等connection metadata。
- **何時需要：** Target無法直接看到原始client IP，或應用／proxy需要額外Layer 4來源資訊時。
- **怎麼設定／驗證：** 在target group開啟proxy_protocol_v2.enabled，並先確認backend server能解析PPv2 header；以packet/backend log驗證。
- **常見錯法：** Backend未支援卻開啟PPv2，會把header當application bytes並直接破壞protocol；HTTP X-Forwarded-For不是同一機制。

#### `preserve client IP`

- **控制什麼：** 控制target看到的是原始client source IP還是load balancer私有位址；可用性依target type與protocol而不同。
- **何時需要：** Firewall、rate limit、audit或application authorization確實需要真實來源IP時。
- **怎麼設定／驗證：** 依target group類型設定preserve_client_ip.enabled，確認return path、security rules與client IP preservation限制，從backend log驗證。
- **常見錯法：** 保留來源IP可能改變routing/hairpin行為；以client IP做唯一身份也會被NAT、proxy或共享出口誤導。

#### `health check`

- **控制什麼：** NLB主動探測target的TCP、HTTP或HTTPS狀態，只把新flows送到通過threshold的targets。
- **何時需要：** 需要排除process停止、port不通或application endpoint失敗的instances、IPs或ALB targets時。
- **怎麼設定／驗證：** 設定protocol、port、path、success codes、interval與threshold；health endpoint應快速、能代表服務能力且不造成下游放大。
- **常見錯法：** TCP成功只證明port接受連線；health check太深可能因單一dependency故障把所有targets一起摘除。

### Gateway Load Balancer：逐項設定說明

#### `GENEVE 6081`

- **控制什麼：** GWLB以UDP 6081上的GENEVE封裝原始IP flow與metadata，透明送到支援GENEVE的firewall、IDS/IPS或其他virtual appliance。
- **何時需要：** 需要在不改變application endpoint的情況下，水平擴展第三方network appliance並保留雙向flow context時。
- **怎麼設定／驗證：** Appliance必須在UDP 6081監聽並正確decapsulate/recapsulate；SG/NACL允許health與GENEVE traffic，再用packet capture驗證。
- **常見錯法：** GENEVE不是一般application listener；appliance只接受普通Ethernet/IP或錯誤MTU時，會丟包或產生難查的fragmentation。

#### `GWLB endpoints`

- **控制什麼：** GWLBe是consumer VPC中的PrivateLink gateway endpoint，route table可把要檢查的流量導入provider端GWLB appliance service。
- **何時需要：** 多個spoke VPC要共用中央inspection fleet，又不想把所有網路完整route到provider VPC時。
- **怎麼設定／驗證：** 每個需要的AZ建立GWLBe並接受service；在ingress、subnet或TGW路徑加入指向vpce-*的routes，逐方向驗證。
- **常見錯法：** 單AZ endpoint會形成跨AZ或故障問題；endpoint存在但route未指向它時，流量完全不會經過inspection。

#### `route tables`

- **控制什麼：** 決定哪些來源／目的flows被送到GWLBe，以及appliance處理後如何回到原路徑，是service insertion的核心。
- **何時需要：** Internet ingress/egress、east-west或TGW centralized inspection需要強制經過appliance時。
- **怎麼設定／驗證：** 分別畫出forward與return route，對public subnet、application subnet、endpoint subnet與TGW tables設定精確next hop並測試對稱性。
- **常見錯法：** 只改去程不改回程會繞過stateful appliance或造成timeout；過寬default route也可能把管理流量送進錯誤inspection path。

#### `target health`

- **控制什麼：** GWLB以health check判斷appliance能否處理flow；不健康target停止接收新flows，healthy fleet共同分擔流量。
- **何時需要：** Appliance可能process crash、license失效、CPU飽和或無法轉送封包，需要自動隔離時。
- **怎麼設定／驗證：** 設定能代表data-plane readiness的health protocol/port與threshold，搭配ASG capacity及appliance metrics測試replacement。
- **常見錯法：** 管理介面回200不代表轉送面正常；health check過於表面會留下black hole，過深則可能同時摘除整個fleet。

#### `appliance flow stickiness`

- **控制什麼：** 以flow的5-tuple或3-tuple維持同一connection方向持續送往同一appliance，讓stateful inspection保留session狀態。
- **何時需要：** Appliance需要看到完整connection並保存NAT、TLS或firewall session state時。
- **怎麼設定／驗證：** 依traffic特性選擇flow stickiness屬性，確保forward/return path對稱；用長連線、fragment與failover案例驗證。
- **常見錯法：** Stickiness不能在appliance故障時遷移其memory state；不適合的tuple選擇也可能讓大量flows集中到少數targets。

#### `cross-zone`

- **控制什麼：** 決定GWLB node是否可把flow送到其他AZ的healthy appliances，在容量均衡、故障隔離與跨AZ成本之間取捨。
- **何時需要：** 各AZ appliance capacity不均或需要在單AZtarget不足時使用其他AZ容量時。
- **怎麼設定／驗證：** 設定cross-zone attribute，確保所有AZ都有對稱route與足夠MTU；監控每AZflows、appliance utilization及cross-AZ bytes。
- **常見錯法：** 開啟不能修正單一appliance bottleneck，且跨AZpath若未對稱會讓stateful inspection失效並增加data transfer費。

## 可以直接對照 AWS 的設定範例

### ALB：listener、health check、stickiness、idle timeout 與 access logs

```yaml
Resources:
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

```

1. TargetType=ip適合ECS awsvpc/Fargate tasks；傳統EC2也可依需求選instance。建立後要換target type通常需新target group。
2. stickiness以ALB cookie維持五分鐘affinity，只是legacy session過渡方案；target失效時仍會換target，長期應外移session state。
3. /ready應快速反映能否接流量；idle timeout要與client/application timeout協調。Access logs另需S3 delivery policy與retention。

### ALB listener rule：host/path routing 與 priority

```yaml
Resources:
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

```

1. Priority數字越小越早評估，第一個matching rule生效；它不是流量權重。
2. Host與path conditions在同一rule中共同成立才match；未命中則繼續其他rules，最後走listener default action。
3. 若要weighted canary，可在同一forward action中配置多個target groups與weights，並以alarm/rollback控制，而不是改rule priority。

## 讀到這裡，請用自己的話說一次

1. Application Load Balancer的責任：提供HTTP/HTTPS Layer 7 routing與web workload入口。
2. 底層機制：終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。
3. 第一個要看的設定：listeners/certificates、rules priority、target type、health path、stickiness、idle timeout與access logs。
4. 選擇邏輯：HTTP path/host routing用ALB；高效TCP/UDP與static IP用NLB；虛擬安全設備鏈用GWLB。
5. 不要混淆：Network Load Balancer的責任是「提供高吞吐、低延遲Layer 4 TCP/UDP/TLS load balancing與static IP。」；它不會自動取代Application Load Balancer。
6. 替換訊號：極低延遲TCP/UDP、static IP或保留source IP需求用NLB。
7. 最常見錯法：因NLB較快就用它處理需要path routing的API，結果把邏輯推回應用程式。
8. 可移植原則：choose the lowest network layer that understands the required decision。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Application Load Balancer | 提供HTTP/HTTPS Layer 7 routing與web workload入口。 | 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。 | 網站、microservices、ECS dynamic ports、gRPC或需要content-based routing。 | 極低延遲TCP/UDP、static IP或保留source IP需求用NLB。 |
| Network Load Balancer | 提供高吞吐、低延遲Layer 4 TCP/UDP/TLS load balancing與static IP。 | 以flow hash選target，通常保留client source IP；可在listener做TLS termination。 | 非HTTP protocol、突然高連線量、static EIP或PrivateLink provider。 | 需要path/host routing、WAF或HTTP redirect時選ALB；virtual appliances用GWLB。 |
| Gateway Load Balancer | 透明插入並擴展第三方firewall、IDS/IPS等virtual appliances。 | GENEVE封裝流量送到appliance fleet，endpoint與route確保雙向對稱路徑。 | 集中deep packet inspection且需水平擴展appliances。 | AWS-native stateful rules可直接用Network Firewall；一般app traffic用ALB/NLB。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | NLB可把流量送ALB組合L4入口與L7routing，但增加元件與診斷層。 | 只有當題目條件明確改變時才可能合理。 | 因NLB較快就用它處理需要path routing的API，結果把邏輯推回應用程式。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「NLB可把流量送ALB組合L4入口與L7routing，但增加元件與診斷層。」之間做選擇。
- 認得常考設定：listeners/certificates、rules priority、target type、health path、stickiness、idle timeout與access logs。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.4 Determine high-performing and/or scalable network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：極低延遲TCP/UDP、static IP或保留source IP需求用NLB。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives。

## 本章 10 題考題

### 練習題 1｜SAA｜18.1 ALB host/path routing 與 TLS

HTTPS api.example.com/orders/*與 /images/*要送不同 target groups，憑證由 AWS管理。應選什麼？

A. ALB HTTPS listener搭 ACM certificate與 ordered host/path rules
B. NLB依 URL path分流
C. GWLB終止 HTTPS並選 HTTP target
D. VPC route table依 path選 next hop

**答案：A**

- **A：** 正確。ALB在 L7終止 TLS並依 HTTP內容選 target group。
- **B：** 不正確。Network Load Balancer一般在L4依IP與port轉送connection，不解析HTTPS解密後的URL path，因此無法分流/orders與/images。
- **C：** 不正確。GWLB服務透明 network appliances，不是 web reverse proxy。
- **D：** 不正確。VPC L3 route table只比對destination IP或prefix並選next hop，看不到HTTP URL path，也不負責TLS certificate管理。

**事實查證：** [Listeners for your Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-listeners.html)、[Listener rules for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-rules.html)

### 練習題 2｜SAA｜18.2 ALB rule priority

ALB rule priority 10匹配 /*並送 general，priority 20匹配 /admin/*並送 admin。/admin/x會去哪裡？

A. admin，因為 ALB自動用 longest path
B. general；ALB按 priority由小到大取第一個 match，應讓具體 /admin/*規則先評估
C. 兩個 target groups各50%
D. 最後建立的 rule

**答案：B**

- **A：** 不正確。ALB listener rules依明確priority由小到大評估，不使用IP routing的longest-prefix規則；較具體path不會自動優先。
- **B：** 正確。Priority 10的/*先匹配/admin/x後就停止評估，因此送往general；應把/admin/*設為更小priority，避免寬廣rule遮蔽。
- **C：** 不正確。沒有同一 forward action的 weighted target groups設定。
- **D：** 不正確。Listener rule的建立時間不會取代設定的數值priority；ALB始終先評估較小priority，再使用default rule作最後fallback。

**事實查證：** [Listener rules for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-rules.html)

### 練習題 3｜SAA｜18.3 Fargate target type 與 readiness（選兩項）

ECS Fargate tasks使用 awsvpc networking並由 ALB分流。哪兩項設定正確？

A. Target group使用 ip target type註冊 task ENI地址
B. 使用 instance target type註冊不存在的宿主 EC2
C. Health path應快速且能代表 task已 ready接受真實流量
D. 用 security group ID當 target ID
E. 健康檢查只確認 process PID存在即可代表所有依賴正常

**答案：A、C**

- **A：** 正確。Awsvpc task具有自己的 ENI，Fargate target以 IP註冊。
- **B：** 不正確。Fargate不暴露可供 instance target註冊的客戶宿主。
- **C：** 正確。Health path應在task真正可處理request且必要依賴ready後才成功，避免process剛啟動便過早接收production流量。
- **D：** 不正確。Security group ID代表network policy attachment，不是ALB可註冊的target ID；awsvpc Fargate通常使用IP target type。
- **E：** 不正確。Process PID存在只能證明程序尚未退出，無法證明port已listen、dependency可用或request能成功，因此不足以作readiness check。

**事實查證：** [Target groups for your Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-type)、[Use an Application Load Balancer for Amazon ECS - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/alb.html)

### 練習題 4｜SAA｜18.4 Stickiness 的限制

Legacy app把 session存在單台 target記憶體。ALB stickiness能提供什麼？

A. 自動複寫 session到所有 targets
B. Target故障時保證 session不遺失
C. 在 cookie有效且 target健康時提高同 client回同 target的機率；長期仍應外部化 session
D. 把 client IP當 IAM identity

**答案：C**

- **A：** 不正確。Stickiness只影響 routing，不複製 application state。
- **B：** 不正確。ALB stickiness只盡量把後續request送回同一target；target失效或被替換時，存在該單機記憶體的session仍會遺失。
- **C：** 正確。它是相容性手段，但可能造成負載偏斜並不能取代 durable shared state。
- **D：** 不正確。Client IP或其他來源網路資訊不是IAM principal，ALB stickiness cookie也不會把network identity轉換成AWS authorization身分。

**事實查證：** [Edit target group attributes for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#sticky-sessions)

### 練習題 5｜SAA｜18.5 ALB idle timeout

長輪詢 request每90秒才有資料，但 ALB idle timeout為60秒，clients固定在約60秒斷線。應怎麼做？

A. 調整 ALB、application與 client timeout，或定期傳資料/改用合適協定；避免無上限重試
B. 縮短 health-check interval
C. 提高 DNS TTL
D. 啟用 cross-zone即可延長 connection

**答案：A**

- **A：** 正確。Idle timeout衡量 connection無資料時間；各層 timeout需一致並評估 retry load。
- **B：** 不正確。Target health interval不改既有 client connection idle timer。
- **C：** 不正確。DNS TTL只影響建立connection前的名稱解析與cache；client已連到ALB後，90秒long polling是否中斷由idle timeout控制。
- **D：** 不正確。Cross-zone影響 target位置，不改 idle timeout。

**事實查證：** [Edit attributes for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-load-balancer-attributes.html)

### 練習題 6｜SAA｜18.6 NLB TCP passthrough 與 TLS listener

非 HTTP支付協定要求 backend自行終止 TLS，入口需 static IP。應如何配置？

A. ALB TCP listener
B. NLB TCP listener轉送 encrypted bytes到 backend；若改用 TLS listener則由 NLB終止 TLS
C. NLB TLS listener仍保證完全 passthrough
D. GWLB安裝 ACM certificate

**答案：B**

- **A：** 不正確。Application Load Balancer沒有一般TCP pass-through listener，會在L7處理HTTP(S)；需要backend自行終止非HTTP TLS時應使用NLB。
- **B：** 正確。TCP listener可保留端到端 TLS至 backend；TLS listener則使用 certificate在 NLB解密。
- **C：** 不正確。TLS listener的核心功能就是 TLS termination。
- **D：** 不正確。Gateway Load Balancer用GENEVE透明承載virtual appliances，不作application TLS endpoint，也不滿足static client-facing listener需求。

**事實查證：** [Listeners for your Network Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

### 練習題 7｜SAP｜18.7 Client IP 與 Proxy Protocol v2

NLB backend需取得原始 client network資訊。哪個設計判斷正確？

A. 所有 TCP targets都能讀 X-Forwarded-For
B. 開啟 Proxy Protocol v2後 backend不需任何變更
C. 依 target/protocol支援選 preserve client IP或 PPv2；使用 PPv2時 backend必須解析其 header
D. NLB永遠保留來源 IP，無任何例外

**答案：C**

- **A：** 不正確。X-Forwarded-For是 HTTP proxy header，不適用任意 TCP。
- **B：** 不正確。未支援 PPv2的 backend會把 binary header誤當應用資料。
- **C：** 正確。實際行為取決於 target type、protocol與屬性；來源 IP也不應作唯一身份。
- **D：** 不正確。NLB是否保留client source IP取決於target type、protocol與target-group attribute；不同targets與設定具有不同source-IP語意。

**事實查證：** [Edit target group attributes for your Network Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html#client-ip-preservation)、[Edit target group attributes for your Network Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html#proxy-protocol)

### 練習題 8｜SAP｜18.8 NLB cross-zone trade-off

NLB各 AZ的 healthy targets數量不均，團隊考慮 cross-zone。哪個敘述正確？

A. Cross-zone會自動建立更多 targets
B. 只適用 ALB path rules
C. 能修復 target application bug
D. Cross-zone允許 load balancer node送到其他 AZ targets，但可能增加 cross-AZ path/cost，且不增加總容量

**答案：D**

- **A：** 不正確。Cross-zone load balancing只擴大每個load balancer node可選擇的healthy targets範圍，不會建立新targets或增加application實體容量。
- **B：** 不正確。Network Load Balancer本身也支援cross-zone load balancing設定；它不是ALB path-based listener rule的專屬功能。
- **C：** 不正確。Cross-zone只能把flow分散到其他AZ的healthy target，不能修復application bug；不健康target仍應由health check移除並由團隊修復。
- **D：** 正確。啟用後每個NLB node可送到其他AZ targets，能緩和AZ內target不均；但不增加總容量，且必須評估cross-AZ資料路徑與費用。

**事實查證：** [Network Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/network-load-balancers.html#cross-zone-load-balancing)

### 練習題 9｜SAP｜18.9 GWLB transparent inspection

多個 spoke VPC流量要透明送第三方 firewall fleet，不改 application endpoint。最佳方案？

A. 使用 GWLB與 GWLBe，routes導入 endpoint，GWLB以 GENEVE送 appliances，並維持雙向 flow
B. 用 ALB WAF檢查所有 L3/L4流量
C. 用 NLB URL rule插入 firewall
D. 只建立 GWLB而不修改任何 route

**答案：A**

- **A：** 正確。GWLB提供透明 bump-in-the-wire service insertion；routing與對稱回程是成立條件。
- **B：** 不正確。AWS WAF只檢查支援的HTTP(S) web request，不能透明攔截所有spoke的L3/L4流量或把它們導向第三方virtual appliance fleet。
- **C：** 不正確。NLB不依 URL建立 appliance service chain。
- **D：** 不正確。Gateway Load Balancer與GWLBe建立後仍需在相關subnet route tables明確導流；沒有routes時packets不會自動插入inspection path。

**事實查證：** [What is a Gateway Load Balancer? - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/introduction.html)

### 練習題 10｜SAP｜18.10 NLB 前置 ALB（選兩項）

入口需要 static IP，同時 backend需 host/path routing。公司接受多一層 load balancer。哪兩項正確？

A. 直接替 ALB綁 Elastic IP
B. 使用 NLB作 L4/static入口，將 ALB作 target承擔 L7 routing
C. 用 GWLB作 host routing
D. 分別設定兩層 listener、health checks、security與診斷，不能只確認 NLB healthy
E. Route 53 Alias會把 ALB動態 IP變成固定客戶 allowlist IP

**答案：B、D**

- **A：** 不正確。Application Load Balancer不允許直接綁定客戶Elastic IP；其node IP由AWS管理，不能作為固定allowlist入口。
- **B：** 正確。AWS支援以ALB作NLB target，讓NLB提供L4與static IP入口，再由ALB承擔HTTP host/path routing；兩層各自保留責任。
- **C：** 不正確。Gateway Load Balancer為virtual appliance提供透明GENEVE資料面，不解析HTTP host或URL path，因此不能取代ALB的L7 routing。
- **D：** 正確。新增NLB前置層後，listener、target registration、health check、security與metrics都多一組failure boundary，除錯時不能只確認NLB healthy。
- **E：** 不正確。Route 53 Alias提供對AWS target的DNS整合，仍會回覆服務管理的位址；它不把ALB動態node IP轉成客戶可長期allowlist的固定IP。

**事實查證：** [Use an Application Load Balancer as a target of a Network Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/application-load-balancer-target.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「HTTP path/host routing用ALB；高效TCP/UDP與static IP用NLB；虛擬…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「負載平衡器在不同層理解不同資訊，影響routing、來源IP、TLS與throughput。」，所以「HTTP path/host routing用ALB；高效TCP/UDP與static IP用NLB；虛擬安全設備鏈用GWLB。」能直接滿足它；若constraint改成「NLB可把流量送ALB組合L4入口與L7routing，但增加元件與診斷層。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「HTTP path/host routing用ALB；高效TCP/UDP與static IP用NLB；虛擬安全設備鏈用GWLB。」。替代方案「NLB可把流量送ALB組合L4入口與L7routing，但增加元件與診斷層。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「因NLB較快就用它處理需要path routing的API，結果把邏輯推回應用程式。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「負載平衡器在不同層理解不同資訊，影響routing、來源IP、TLS與throughput。」，排除會導致「因NLB較快就用它處理需要path routing的API，結果把邏輯推回應用程式。」的選項，再選「HTTP path/host routing用ALB；高效TCP/UDP與static IP用NLB；虛擬安全設備鏈用GWLB。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.4 Determine high-performing and/or scalable network architectures；SAP-1.1 Architect network connectivity strategies。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「HTTP path/host routing用ALB；高效TCP/UDP與static IP用NLB；虛擬安全設備鏈用GWLB。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「choose the lowest network layer that understands the required decision」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 19 章　VPN、Direct Connect 與 Hybrid Connectivity

企業需要在上雲速度、頻寬穩定、加密、成本與備援之間取捨。

## 跟著一個封包走：先從故事開始

故事從一個看似簡單的需求開始：金融系統每天傳數TB資料，要求穩定延遲、加密與兩個location容錯。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：企業需要在上雲速度、頻寬穩定、加密、成本與備援之間取捨。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把網路想成城市交通：DNS找地址，route選道路，security rules決定哪扇門能進。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，AWS Site-to-Site VPN會是本章的主要角色，AWS Direct Connect則幫我們看清邊界。方向是「快速建立或backup用VPN；穩定private circuit用Direct Connect；關鍵系統建立多路徑。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：金融系統每天傳數TB資料，要求穩定延遲、加密與兩個location容錯。

來源（使用者／VPC／on-premises）
          │ ① 名稱解析：要連到哪個位址？
          │ ② 去程 route + network policy
          ▼
[AWS Site-to-Site VPN]
          │ 透過Internet建立加密IPsec隧道連接VPC/TGW與on-premises。
          ▼
[target／application state]
          │ ③ response沿有效回程返回
控制面：建立DNS、route、listener、policy與health設定
資料面：每個packet／connection／request實際沿路通過
本章其他角色：
  · AWS Direct Connect：提供從客戶網路到AWS的專用網路connection。
  · Direct Connect Gateway：把private/transit virtual interfaces連到跨Region的VGW或Tran…

失敗時先找：只有單一DX connection且沒有異地或VPN備援，把電信商故障變成單點。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問AWS Site-to-Site VPN有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Site-to-Site VPN和AWS Direct Connect並不是兩個任意的產品名稱。前者適合本章，是因為「快速建立或backup用VPN；穩定private circuit用Direct Connect；關鍵系統建立多路徑。」直接回應了眼前的問題；後者描述的「Direct Connect不是預設端到端加密，仍可能搭配MACsec或VPN。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只有單一DX connection且沒有異地或VPN備援，把電信商故障變成單點。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「hybrid connectivity requires path diversity and routing policy」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Site-to-Site VPN | 透過Internet建立加密IPsec隧道連接VPC/TGW與on-premises。 | 每個VPN connection有兩條隧道；BGP或static routes決定path，Internet品質影響latency。 |
| AWS Direct Connect | 提供從客戶網路到AWS的專用網路connection。 | 實體port經virtual interfaces連到VPC、public services或TGW；BGP交換routes。 |
| Direct Connect Gateway | 把private/transit virtual interfaces連到跨Region的VGW或Transit Gateway associations。 | DX gateway位於連線與VPC/TGW gateway之間，透過BGP allowed prefixes交換可達網段，但不提供VPC間任意transitive routing。 |

## 把全圖套進一個具體案例

**場景：** 金融系統每天傳數TB資料，要求穩定延遲、加密與兩個location容錯。

1. 故事的起點：金融系統每天傳數TB資料，要求穩定延遲、加密與兩個location容錯。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Site-to-Site VPN負責「透過Internet建立加密IPsec隧道連接VPC/TGW與on-premises。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：每個VPN connection有兩條隧道；BGP或static routes決定path，Internet品質影響latency。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Direct Connect、Direct Connect Gateway各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只有單一DX connection且沒有異地或VPN備援，把電信商故障變成單點。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「需要穩定大頻寬與可預測路徑時用Direct Connect，並常保留VPN備援。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### Cloud WAN：當 TGW 已經從區域網路長成全球企業骨幹

一兩個 Region 時，Transit Gateway 配合 peering 很直覺；但當企業有數十個 Region、分公司與資料中心，困難不再只是『能不能連』，而是每個 Region 是否都套用相同分段、route sharing、inspection 與變更版本。Cloud WAN 用 core network policy 描述意圖，再在各 Region 建立 core network edge 並維持 segments。

```text
branch / DC ─ VPN / Connect ┐
VPC A ─ attachment ─────────┼─> Cloud WAN core network
VPC B ─ attachment ─────────┘      ├─ segment: prod
                                   ├─ segment: nonprod
                                   └─ shared-services / inspection
                         policy version → review → execute / rollback
```

#### Core network policy 的關鍵不是 JSON 語法，而是 segment 意圖

```JSON
{
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
}
```

1. Edge locations 決定哪些 Regions 有 managed core edge；它不是 CloudFront edge location。
2. Segment 是隔離的 routing domain。附件不會因為同屬一個 global network 就自動互通。
3. 政策要先產生 change set、檢查 route/segment 影響再 execute；企業網路也需要版本、審核與回復路徑。

**選擇邊界：** 單 Region hub-and-spoke 優先 TGW；需要全球一致 policy、segments、branch/DC/VPC 統一治理時才評估 Cloud WAN。PrivateLink/Lattice 仍適合只暴露服務，不應為了一個 API 建全球 routed network。

**考試範圍：** Cloud WAN 通常是 SAP 的 organizational complexity／network strategy 延伸；SAA 只需理解它不取代Direct Connect、VPN 或 application-level service exposure，而是治理它們形成的 WAN。

- [AWS：What is AWS Cloud WAN?](https://docs.aws.amazon.com/network-manager/latest/cloudwan/what-is-cloudwan.html)
- [AWS：Core network policies](https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-policy-create.html)

## 需要時再查：四個閱讀支點

### AWS Site-to-Site VPN

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：企業需要在上雲速度、頻寬穩定、加密、成本與備援之間取捨。
- **具體例子／邊界：** 在「金融系統每天傳數TB資料，要求穩定延遲、加密與兩個location容錯。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Direct Connect

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Direct Connect不是預設端到端加密，仍可能搭配MACsec或VPN。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只有單一DX connection且沒有異地或VPN備援，把電信商故障變成單點。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：hybrid connectivity requires path diversity and routing policy。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### hybrid connectivity

讓on-premises與cloud長期互通的network、DNS、identity與routing設計，不只是建立一條VPN。

### transitive routing

A能到B且A能到C時，B是否可經A到C；VPC Peering不提供此能力，TGW可建立受控hub routing。

### Direct Connect

從客戶或colocation到AWS的專用網路連線；提供較穩定路徑，但本身不等於端到端加密或自動高可用。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### VLAN

Virtual LAN，在共享實體link上以標記隔離Layer-2 traffic；Direct Connect VIF配置會使用VLAN ID。

### BGP

Border Gateway Protocol，在network peers間交換可達prefix與path資訊；DX/VPN常用它動態學習routes。

### VPN

Virtual Private Network，在既有Internet上建立加密tunnel；AWS Site-to-Site VPN通常提供兩條IPsec tunnels。

## 回到 AWS：Components、功用與責任邊界

### AWS Site-to-Site VPN

- **功用：** 透過Internet建立加密IPsec隧道連接VPC/TGW與on-premises。
- **底層機制：** 每個VPN connection有兩條隧道；BGP或static routes決定path，Internet品質影響latency。
- **關鍵設定：** customer gateway、virtual private gateway/TGW、BGP ASN、tunnel options、routes與acceleration。
- **選擇時機：** 快速建立hybrid連線、低至中流量、DX備援或必須原生加密。
- **替換時機：** 需要穩定大頻寬與可預測路徑時用Direct Connect，並常保留VPN備援。

### AWS Direct Connect

- **功用：** 提供從客戶網路到AWS的專用網路connection。
- **底層機制：** 實體port經virtual interfaces連到VPC、public services或TGW；BGP交換routes。
- **關鍵設定：** connection/location、hosted/dedicated、VLAN、BGP ASN、private/public/transit VIF、DX Gateway與LAG。
- **選擇時機：** 持續大量資料、穩定latency、private path與混合企業網路。
- **替換時機：** 部署需數週且本身不等於加密；快速或低成本情境先用VPN，關鍵服務採雙location。

### Direct Connect Gateway

- **功用：** 把private/transit virtual interfaces連到跨Region的VGW或Transit Gateway associations。
- **底層機制：** DX gateway位於連線與VPC/TGW gateway之間，透過BGP allowed prefixes交換可達網段，但不提供VPC間任意transitive routing。
- **關鍵設定：** gateway associations、allowed prefixes、private/transit VIF、BGP ASN、route advertisements與association proposals。
- **選擇時機：** 同一DX連線需要觸及多個Region的VPC或TGW，並集中管理on-premises prefix交換時。
- **替換時機：** 單一Region單一VPC可直接使用private VIF到VGW；需要VPC間hub routing由Transit Gateway負責。

## 考前與實作時再查：設定操作手冊

### AWS Site-to-Site VPN：逐項設定說明

#### `customer gateway`

- **控制什麼：** `customer gateway`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「快速建立hybrid連線、低至中流量、DX備援或必須原生加密。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Site-to-Site VPN的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `virtual private gateway/TGW`

- **控制什麼：** `virtual private gateway/TGW`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「快速建立hybrid連線、低至中流量、DX備援或必須原生加密。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Site-to-Site VPN的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `BGP ASN`

- **控制什麼：** `BGP ASN`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「快速建立hybrid連線、低至中流量、DX備援或必須原生加密。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Site-to-Site VPN的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `tunnel options`

- **控制什麼：** `tunnel options`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

#### `routes`

- **控制什麼：** `routes`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「快速建立hybrid連線、低至中流量、DX備援或必須原生加密。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Site-to-Site VPN的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `acceleration`

- **控制什麼：** `acceleration`控制address family、可重用CIDR集合、public/static入口或route/tunnel狀態，是network path的一部分。
- **何時需要：** VPC/hybrid入口需要明確addressing、可達範圍、固定IP、加速或故障辨識時。
- **怎麼設定／驗證：** 記錄CIDR/prefix-list與owner，設定public/internal scheme、EIP或tunnel參數；以route table、Flow Logs和雙向測試驗證。
- **常見錯法：** EIP不等於高可用；blackhole route與CIDR重疊會直接中斷流量，IPv6也不能沿用IPv4 NAT與security假設。

### AWS Direct Connect：逐項設定說明

#### `connection/location`

- **控制什麼：** `connection/location`指定AWS Direct Connect讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `hosted/dedicated`

- **控制什麼：** `hosted/dedicated`選擇AWS Direct Connect的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `VLAN`

- **控制什麼：** `VLAN`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「持續大量資料、穩定latency、private path與混合企業網路。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Direct Connect的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `BGP ASN`

- **控制什麼：** `BGP ASN`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「持續大量資料、穩定latency、private path與混合企業網路。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Direct Connect的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `private/public/transit VIF`

- **控制什麼：** `private/public/transit VIF`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「持續大量資料、穩定latency、private path與混合企業網路。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Direct Connect的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `DX Gateway`

- **控制什麼：** `DX Gateway`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「持續大量資料、穩定latency、private path與混合企業網路。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Direct Connect的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `LAG`

- **控制什麼：** `LAG`描述failover/migration時的資料落後、切換步驟或client重新連線行為。
- **何時需要：** Database、replica或migrated server需要在可接受RPO/RTO內切換到新writer/target時。
- **怎麼設定／驗證：** 監控lag並定義freeze、final sync、DNS/endpoint switch、connection retry與rollback gates；以game day量測實際時間。
- **常見錯法：** 只看resource healthy不代表lag歸零；client cache/DNS/connection pool不重連會讓failover後仍打舊endpoint。

### Direct Connect Gateway：逐項設定說明

#### `gateway associations`

- **控制什麼：** `gateway associations`控制Direct Connect Gateway的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

#### `allowed prefixes`

- **控制什麼：** 限制Direct Connect gateway association可向Transit Gateway或Virtual Private Gateway宣告及接收的CIDR範圍，形成路由傳播邊界。
- **何時需要：** 一條Direct Connect要服務多個VPC／Region，但on-premises只應看見核准網段，或必須避免過度宣告造成路由外洩時。
- **怎麼設定／驗證：** 先建立不重疊的prefix清單，再在association或proposal設定allowed prefixes；同時核對BGP advertisements與兩側return routes。
- **常見錯法：** Allowed prefixes不是security group或packet firewall；前綴過寬會擴大可達範圍，過窄則會讓BGP session正常但application流量黑洞。

#### `private/transit VIF`

- **控制什麼：** `private/transit VIF`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「同一DX連線需要觸及多個Region的VPC或TGW，並集中管理on-premises prefix交換時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Direct Connect Gateway的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `BGP ASN`

- **控制什麼：** `BGP ASN`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「同一DX連線需要觸及多個Region的VPC或TGW，並集中管理on-premises prefix交換時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Direct Connect Gateway的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `route advertisements`

- **控制什麼：** `route advertisements`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「同一DX連線需要觸及多個Region的VPC或TGW，並集中管理on-premises prefix交換時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Direct Connect Gateway的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `association proposals`

- **控制什麼：** `association proposals`控制Direct Connect Gateway的route-domain membership、對稱inspection或多路徑/群組傳送行為。
- **何時需要：** 使用TGW建立segmentation、inspection VPC、多VPN吞吐或特殊multicast workload時。
- **怎麼設定／驗證：** 明確關聯attachment與route table，設定propagation/appliance mode，並從雙向flow驗證對稱路徑與期望routes。
- **常見錯法：** Association與propagation不是同一件事；錯誤table或非對稱路徑會繞過firewall或讓stateful appliance丟棄回程。

## 讀到這裡，請用自己的話說一次

1. AWS Site-to-Site VPN的責任：透過Internet建立加密IPsec隧道連接VPC/TGW與on-premises。
2. 底層機制：每個VPN connection有兩條隧道；BGP或static routes決定path，Internet品質影響latency。
3. 第一個要看的設定：customer gateway、virtual private gateway/TGW、BGP ASN、tunnel options、routes與acceleration。
4. 選擇邏輯：快速建立或backup用VPN；穩定private circuit用Direct Connect；關鍵系統建立多路徑。
5. 不要混淆：AWS Direct Connect的責任是「提供從客戶網路到AWS的專用網路connection。」；它不會自動取代AWS Site-to-Site VPN。
6. 替換訊號：需要穩定大頻寬與可預測路徑時用Direct Connect，並常保留VPN備援。
7. 最常見錯法：只有單一DX connection且沒有異地或VPN備援，把電信商故障變成單點。
8. 可移植原則：hybrid connectivity requires path diversity and routing policy。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Site-to-Site VPN | 透過Internet建立加密IPsec隧道連接VPC/TGW與on-premises。 | 每個VPN connection有兩條隧道；BGP或static routes決定path，Internet品質影響latency。 | 快速建立hybrid連線、低至中流量、DX備援或必須原生加密。 | 需要穩定大頻寬與可預測路徑時用Direct Connect，並常保留VPN備援。 |
| AWS Direct Connect | 提供從客戶網路到AWS的專用網路connection。 | 實體port經virtual interfaces連到VPC、public services或TGW；BGP交換routes。 | 持續大量資料、穩定latency、private path與混合企業網路。 | 部署需數週且本身不等於加密；快速或低成本情境先用VPN，關鍵服務採雙location。 |
| Direct Connect Gateway | 把private/transit virtual interfaces連到跨Region的VGW或Transit Gateway associations。 | DX gateway位於連線與VPC/TGW gateway之間，透過BGP allowed prefixes交換可達網段，但不提供VPC間任意transitive routing。 | 同一DX連線需要觸及多個Region的VPC或TGW，並集中管理on-premises prefix交換時。 | 單一Region單一VPC可直接使用private VIF到VGW；需要VPC間hub routing由Transit Gateway負責。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Direct Connect不是預設端到端加密，仍可能搭配MACsec或VPN。 | 只有當題目條件明確改變時才可能合理。 | 只有單一DX connection且沒有異地或VPN備援，把電信商故障變成單點。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Direct Connect不是預設端到端加密，仍可能搭配MACsec或VPN。」之間做選擇。
- 認得常考設定：customer gateway、virtual private gateway/TGW、BGP ASN、tunnel options、routes與acceleration。
- 對應官方tasks：SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：需要穩定大頻寬與可預測路徑時用Direct Connect，並常保留VPN備援。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-2.2 Design a solution to ensure business continuity；SAP-2.5 Design a solution to meet performance objectives。

## 本章 10 題考題

### 練習題 1｜SAA｜19.1 快速建立 encrypted hybrid path

新專案兩天內要讓 on-premises與 VPC私下互通，流量中等、可接受 Internet latency變動，但所有傳輸必須加密。最佳起始方案？

A. 建立 Site-to-Site VPN，配置並監控該 connection的兩條 IPsec tunnels
B. 等待 dedicated Direct Connect完成，因為 VPN不加密
C. 建立 VPC Peering到 on-premises router
D. 使用 Direct Connect public VIF直接提供 IPsec

**答案：A**

- **A：** 正確。Site-to-Site VPN能快速透過 Internet建立 IPsec path；兩 tunnels都應配置以支援設備維護與故障。
- **B：** 不正確。Dedicated Direct Connect通常無法在兩天內完成，且private connection預設不等於payload已加密；Site-to-Site VPN本身使用IPsec。
- **C：** 不正確。VPC Peering只建立兩個VPC間的non-transitive private routing，不提供實體資料中心router到VPC的hybrid network連線。
- **D：** 不正確。Public VIF提供 AWS public prefixes，不會自動建立 customer VPN。

**事實查證：** [What is AWS Site-to-Site VPN? - AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPC_VPN.html)、[Tunnel options for your AWS Site-to-Site VPN connection - AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html)

### 練習題 2｜SAP｜19.2 VPN BGP tunnel failover

Site-to-Site VPN使用 dynamic routing。公司希望一條 tunnel失效時自動改走另一條。必要條件是什麼？

A. Route 53 failover record選 tunnel
B. Customer gateway與 VGW/TGW在兩 tunnels建立正確 BGP sessions與 route advertisements，並監控 tunnel狀態
C. 在 SG發布 BGP routes
D. 只配置 static route即可自動 ECMP

**答案：B**

- **A：** 不正確。Route 53 failover只決定DNS回答中的application endpoint，不控制Site-to-Site VPN兩條IPsec tunnels的BGP route或資料面選路。
- **B：** 正確。Dynamic routing需雙方 BGP與可用 tunnels；failover依 route與 tunnel健康。
- **C：** 不正確。Security group只在ENI層允許符合條件的packets，不會建立BGP session、向VGW/TGW發布prefix或觸發tunnel failover。
- **D：** 不正確。Static routes不自動提供 BGP convergence或必然 ECMP。

**事實查證：** [AWS Site-to-Site VPN routing options - AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html)、[Tunnel options for your AWS Site-to-Site VPN connection - AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html)

### 練習題 3｜SAA｜19.3 大量穩定傳輸的 Direct Connect（選兩項）

公司每天傳輸數 TB，要求比 Internet VPN更可預測的 throughput與 latency。哪兩項判斷正確？

A. Direct Connect提供專用 private connectivity，適合持續高流量與較一致路徑
B. 一條 DX connection會自動跨兩個 physical locations
C. 仍需另外設計冗餘、routing與 encryption；DX本身不等於完整 HA或端到端加密
D. 單一 VPN tunnel永遠提供同等穩定性
E. DX建立後所有 VPC自動可達，不需 VIF或 gateway

**答案：A、C**

- **A：** 正確。DX避免一般 Internet data path，可提供較一致的 network experience。
- **B：** 不正確。Physical diversity要明確建立不同 devices/locations的 connections。
- **C：** 正確。Circuit只完成一部分 contract；VIF、BGP、HA與加密仍是客戶設計。
- **D：** 不正確。VPN受 Internet path與 tunnel capacity影響。
- **E：** 不正確。Direct Connect physical connection建立後仍須建立適當VIF，並配置VGW、DXGW或TGW association及routes，VPC才會取得hybrid reachability。

**事實查證：** [What is Direct Connect? - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html)、[AWS Direct Connect Resiliency Toolkit - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/resiliency_toolkit.html)

### 練習題 4｜SAP｜19.4 Direct Connect VIF 類型

公司有三個需求：連單一 VPC private IP、存取 AWS public services、透過 TGW連多 VPC。正確 VIF對應為何？

A. Public、private、public
B. Transit、public、private
C. Private VIF→VGW/DXGW；Public VIF→AWS public prefixes；Transit VIF→DXGW與 TGW
D. 三者可任意互換，只看 VLAN ID

**答案：C**

- **A：** 不正確。Public VIF不是單一 VPC private-IP path。
- **B：** 不正確。Transit VIF的用途正是透過Direct Connect Gateway連接Transit Gateway；把它分配給單一VPC private IP會顛倒VIF產品語意。
- **C：** 正確。VIF類型由要到達的 routing domain與 gateway contract決定。
- **D：** 不正確。VLAN與BGP是建立每種VIF都需要的連線設定，但不能把public VIF、private VIF與transit VIF的resource scope任意互換。

**事實查證：** [Direct Connect virtual interfaces and hosted virtual interfaces - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/WorkingWithVirtualInterfaces.html)

### 練習題 5｜SAP｜19.5 Direct Connect Gateway 的角色

哪個敘述最準確描述 Direct Connect Gateway（DXGW）？

A. 它是 colocation中的實體 fiber port
B. 它會自動加密所有 DX payload
C. 它取代 TGW route tables做 segmentation
D. 它是將 private/transit VIF與 VGW或 TGW關聯的全球性 routing construct，不是 physical circuit

**答案：D**

- **A：** 不正確。Physical connection是DX location中的實體或託管port；Direct Connect Gateway則是關聯VIF與VGW/TGW的全球routing resource，兩者責任不同。
- **B：** 不正確。Direct Connect Gateway提供跨Region gateway association與routing能力，不會自動加密application payload；加密需另用MACsec、IPsec或application TLS。
- **C：** 不正確。TGW segmentation仍由 attachments與 route tables控制。
- **D：** 正確。DXGW讓一組 DX connectivity關聯到支援的 gateways與 Regions。

**事實查證：** [Direct Connect gateways - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways-intro.html)

### 練習題 6｜SAP｜19.6 DX location failure resilience

金融 workload必須在完整 DX location故障後仍保有 DX級連線能力。哪個設計最符合 maximum resilience？

A. 只在同一 connection建立兩個 VIF
B. 在兩個獨立DX locations各建立兩條connections，每條終止於不同AWS device，並讓customer/provider circuit與設備路徑具diversity；另可保留VPN備援
C. 同一 location建立 LAG就能抵抗 location outage
D. 一個 VPN connection的兩 tunnels等於兩個 DX locations

**答案：B**

- **A：** 不正確。兩個VIF若共用同一physical connection、AWS device與DX location，仍共享底層failure domain，不能承受整個location失效。
- **B：** 正確。Maximum Resiliency模型是兩個locations、每處兩條終止於不同AWS devices的connections；還要確認customer/provider path diversity，並用Resiliency Toolkit與failover testing驗證。
- **C：** 不正確。LAG members位於同一DX location，能增加port capacity或connection redundancy，卻無法在整個site outage時保留另一個location的DX路徑。
- **D：** 不正確。Site-to-Site VPN的兩個tunnels提供IPsec tunnel redundancy，但不等於兩個獨立DX physical locations，也不能取代Maximum Resiliency拓撲。

**事實查證：** [AWS Direct Connect Resiliency Toolkit - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/resiliency_toolkit.html)

### 練習題 7｜SAP｜19.7 DX encryption choices

支援的dedicated DX connection需要link-level encryption並維持高吞吐；另一環境則可接受IPsec tunnel overhead。哪個判斷正確？

A. Private VIF自動端到端 TLS
B. BGP authentication會加密 application payload
C. 支援的dedicated connection可使用MACsec保護Layer 2 hop；若需要Layer 3 overlay，可設計Site-to-Site VPN over DX，但其VIF、route、tunnel與throughput條件不同
D. Security group可在 fiber上執行加密

**答案：C**

- **A：** 不正確。Private VIF提供到private resources的路由與BGP session，不會自動替application payload建立TLS或其他端到端加密。
- **B：** 不正確。BGP authentication保護routing peers交換路由的session，不會加密經該路由承載的業務封包內容。
- **C：** 正確。MACsec在支援的DX port與device上提供Layer 2加密；IPsec VPN over DX是Layer 3 overlay，需要另行設計VIF可達性、tunnels、routes與throughput。
- **D：** 不正確。Security group是ENI層的stateful allow policy，不是cryptographic protocol，無法在physical fiber或BGP path上加密資料。

**事實查證：** [MAC Security in Direct Connect - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/MACsec.html)、[Encryption in AWS Direct Connect - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/encryption-in-transit.html)、[Private IP AWS Site-to-Site VPN with Direct Connect - AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/private-ip-dx.html)

### 練習題 8｜SAP｜19.8 DX primary、VPN backup routing

同一VPC的private VIF與dynamic Site-to-Site VPN都終止於同一VGW，並向VPC廣告相同10.60.0.0/16 on-premises prefix。要求AWS到on-prem平時走DX、DX路由撤回後走VPN。哪個方案正確？

A. 先以longest-prefix match判斷；相同prefix時驗證VGW的route priority會偏好Direct Connect BGP route，再用BGP attributes設計on-prem回程偏好，並實際撤回DX route測試VPN收斂
B. Route 53 latency policy選 circuit
C. 頻寬較大的線路必然自動優先
D. SG rule number決定 BGP path

**答案：A**

- **A：** 正確。Route selection先比較最長prefix；在題目指定的同一VGW與相同prefix條件下，AWS route priority偏好Direct Connect BGP route。On-prem方向仍須由customer router的local preference、AS path等策略控制，並以撤回路由驗證failover。
- **B：** 不正確。Route 53 latency policy只決定DNS回答中的application endpoint，不會選擇VGW內的DX或VPN network path，也不參與BGP收斂。
- **C：** 不正確。線路標稱頻寬不是VPC或VGW的route-priority欄位；若prefix或route source不同，實際選路可能與頻寬大小完全無關。
- **D：** 不正確。Security group rule沒有排序式priority，也不參與BGP best-path；它只在路由選定後決定ENI是否允許相符的資料面流量。

**事實查證：** [Direct Connect routing policies and BGP communities - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html)、[AWS Site-to-Site VPN routing options - AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html)、[How route priority works - Amazon Virtual Private Cloud](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)

### 練習題 9｜SAP｜19.9 多帳號 hybrid connectivity 治理

60個 VPC要共享 on-premises DX，同時 prod/dev route domains隔離。最佳拓撲？

A. 每個 VPC建立 full-mesh VPN
B. DXGW自動提供 segmentation，不需 TGW tables
C. Organizations會自動傳播所有 on-prem routes
D. Transit VIF→DXGW→TGW，使用多張 TGW route tables控制 attachments的 association與 propagation

**答案：D**

- **A：** 不正確。為60個VPC各建獨立VPN會產生大量tunnels、BGP sessions與route policies，增加維運複雜度，也難以一致表達prod/dev route-domain隔離。
- **B：** 不正確。DXGW不是 segmentation policy engine。
- **C：** 不正確。Organizations治理帳號，不建立資料面 routes。
- **D：** 正確。此組合集中 physical connectivity，同時保留 TGW route-domain治理。

**事實查證：** [Direct Connect gateways and Transit Gateway associations - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-transit-gateways.html)、[Transit gateway route tables in AWS Transit Gateway - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)

### 練習題 10｜SAP｜19.10 Hybrid throughput troubleshooting（選兩項）

Hybrid path可以 ping，但大型 TCP傳輸失敗或吞吐異常。哪兩項除錯最有價值？

A. 增加 DNS records
B. 驗證 BGP advertised/received routes與 forward/return path是否一致
C. 把所有 NACL改成 allow all即可證明 throughput達標
D. 檢查 MTU/fragmentation、VPN/DX metrics、packet loss與實際 application flow
E. 提高 EBS IOPS並停止 network investigation

**答案：B、D**

- **A：** 不正確。新增DNS records只改變名稱解析；既然小型ping已通，大型TCP失敗更應檢查MTU、fragmentation、MSS、return route與packet loss。
- **B：** 正確。小型 ICMP成功可能掩蓋不同 prefix或非對稱 data path。
- **C：** 不正確。暫時移除security boundary會擴大攻擊面，且無法直接區分DX/VPN circuit、MTU、fragmentation或asymmetric return path等根因。
- **D：** 正確。Path MTU、loss與 tunnel/circuit counters能解釋大流量與小 ping差異。
- **E：** 不正確。EBS IOPS可能影響application processing，但沒有host metric或trace證據時不能把大型packet與TCP throughput症狀歸因storage並停止network investigation。

**事實查證：** [Troubleshoot Direct Connect - AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/Troubleshooting.html)、[Troubleshoot AWS Site-to-Site VPN connectivity when using Border Gateway Protocol - AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/Generic_Troubleshooting.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「快速建立或backup用VPN；穩定private circuit用Direct Connect；關鍵系統…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「企業需要在上雲速度、頻寬穩定、加密、成本與備援之間取捨。」，所以「快速建立或backup用VPN；穩定private circuit用Direct Connect；關鍵系統建立多路徑。」能直接滿足它；若constraint改成「Direct Connect不是預設端到端加密，仍可能搭配MACsec或VPN。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「快速建立或backup用VPN；穩定private circuit用Direct Connect；關鍵系統建立多路徑。」。替代方案「Direct Connect不是預設端到端加密，仍可能搭配MACsec或VPN。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只有單一DX connection且沒有異地或VPN備援，把電信商故障變成單點。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「企業需要在上雲速度、頻寬穩定、加密、成本與備援之間取捨。」，排除會導致「只有單一DX connection且沒有異地或VPN備援，把電信商故障變成單點。」的選項，再選「快速建立或backup用VPN；穩定private circuit用Direct Connect；關鍵系統建立多路徑。」。本章對應的代表task包括：SAA-3.4 Determine high-performing and/or scalable network architectures；SAA-4.4 Design cost-optimized network architectures；SAP-1.1 Architect network connectivity strategies；SAP-2.2 Design a solution to ensure business continuity。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「快速建立或backup用VPN；穩定private circuit用Direct Connect；關鍵系統建立多路徑。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「hybrid connectivity requires path diversity and routing policy」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 20 章　Multi-VPC、Hybrid DNS 與 Network Inspection

大型組織需要統一解析private names、分離route domains並檢查流量。

## 跟著一個封包走：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：數百VPC需解析on-premises domain，prod/dev隔離且internet egress集中稽核。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：大型組織需要統一解析private names、分離route domains並檢查流量。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：可以把一次網路請求想成打電話：DNS查號碼，TCP接通線路，TLS核對對方身份，HTTP才是接通後真正說的話。 電話類比無法表達cache、重試與多條網路路徑，所以除錯時仍要逐層看實際metric與log。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Route 53 Resolver負責主要工作，AWS Transit Gateway提醒我們答案不是永遠固定。本章會走向「用Route 53 Resolver endpoints/rules共享DNS，TGW route tables隔離環境，inspection VPC集中安全設備。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：數百VPC需解析on-premises domain，prod/dev隔離且internet egress集中稽核。

來源（使用者／VPC／on-premises）
          │ ① 名稱解析：要連到哪個位址？
          │ ② 去程 route + network policy
          ▼
[Route 53 Resolver]
          │ 在VPC DNS與on-premises DNS之間轉送查詢。
          ▼
[target／application state]
          │ ③ response沿有效回程返回
控制面：建立DNS、route、listener、policy與health設定
資料面：每個packet／connection／request實際沿路通過
本章其他角色：
  · AWS Transit Gateway：以regional hub連接大量VPC、VPN與Direct Connect。
  · AWS Network Firewall：在VPC中提供managed stateful/stateless L3–L7 network inspe…

失敗時先找：轉送DNS形成loop，或forward path經firewall而return path繞過，造成stateful檢查失敗。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一個封包走」。先不要急著問Route 53 Resolver有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Route 53 Resolver和AWS Transit Gateway並不是兩個任意的產品名稱。前者適合本章，是因為「用Route 53 Resolver endpoints/rules共享DNS，TGW route tables隔離環境，inspection VPC集中安全設備。」直接回應了眼前的問題；後者描述的「中央inspection便於治理，但對稱路由、appliance mode、跨AZ成本與容量都需設計。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：轉送DNS形成loop，或forward path經firewall而return path繞過，造成stateful檢查失敗。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「centralize policy without centralizing every failure」。更白話地說：永遠分開檢查名稱、去程、回程與允許規則；任何一層缺少都可能只剩timeout。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Route 53 Resolver | 在VPC DNS與on-premises DNS之間轉送查詢。 | Inbound endpoint讓外部查VPC names；outbound endpoint依resolver rules把指定domain送到外部DNS。 |
| AWS Transit Gateway | 以regional hub連接大量VPC、VPN與Direct Connect。 | Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 |
| AWS Network Firewall | 在VPC中提供managed stateful/stateless L3–L7 network inspection。 | Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。 |

## 把全圖套進一個具體案例

**場景：** 數百VPC需解析on-premises domain，prod/dev隔離且internet egress集中稽核。

1. 故事的起點：數百VPC需解析on-premises domain，prod/dev隔離且internet egress集中稽核。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Route 53 Resolver負責「在VPC DNS與on-premises DNS之間轉送查詢。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Inbound endpoint讓外部查VPC names；outbound endpoint依resolver rules把指定domain送到外部DNS。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Transit Gateway、AWS Network Firewall各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「轉送DNS形成loop，或forward path經firewall而return path繞過，造成stateful檢查失敗。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「Internet public DNS delegation使用hosted zones/NS records，不需Resolver endpoints。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### Hybrid DNS 與 DNSSEC：一個管『去哪裡問』，一個管『答案有沒有被竄改』

Hybrid DNS 的問題通常是查詢方向：AWS workload 要問 on-prem zone，或 on-prem client 要問 Route 53 private hosted zone。Resolver outbound endpoint 搭 rule 處理前者；inbound endpoint 處理後者。DNSSEC 解決的是另一件事：resolver 可驗證 public DNS 回答的簽章鏈，降低 cache poisoning／answer tampering。

```text
AWS workload ─> Route 53 Resolver
                   ├─ private hosted zone → private answer
                   ├─ rule: corp.example → outbound endpoint → on-prem DNS
                   └─ public zone → DNSSEC validation chain

on-prem client ─ conditional forwarder → inbound endpoint → private hosted zone
```

#### 真正可維運的 Resolver rule 至少要說清楚三件事

```YAML
resolver_rule:
  domain: corp.example
  direction: FORWARD
  outbound_endpoint_subnets:
    - subnet-a
    - subnet-b
  target_dns_ips:
    - 10.40.0.10
    - 10.40.1.10
  associated_vpcs:
    - app-prod-vpc
```

1. Domain 採 suffix match；過於寬鬆的規則可能把原本應由 public DNS 回答的名稱送到內部。
2. Endpoint 跨至少兩個 AZ，target DNS 也應有可用性設計；否則 DNS 會成為所有 application 的共同單點。
3. 用 dig/nslookup 分別從 AWS 與 on-prem 測試，並記錄實際回答、resolver query logs 與失敗方向。

**選擇邊界：** Split-horizon 是同一名稱依查詢來源得到不同答案；Resolver endpoint/rule 是轉送路徑；DNSSEC 是完整性驗證。三者不能互相替代，路由、安全群組與 UDP/TCP 53 回程也仍要成立。

**考試範圍：** Resolver inbound/outbound 與 conditional forwarding 是 SAP hybrid DNS 高頻邊界；SAA 先會辨識 public/private hosted zone、TTL、Alias 與 DNS 不代理 application traffic。

- [AWS：Route 53 Resolver](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [AWS：Configuring DNSSEC signing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-configuring-dnssec.html)

## 需要時再查：四個閱讀支點

### Route 53 Resolver

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：大型組織需要統一解析private names、分離route domains並檢查流量。
- **具體例子／邊界：** 在「數百VPC需解析on-premises domain，prod/dev隔離且internet egress集中稽核。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Transit Gateway

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：中央inspection便於治理，但對稱路由、appliance mode、跨AZ成本與容量都需設計。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：轉送DNS形成loop，或forward path經firewall而return path繞過，造成stateful檢查失敗。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：centralize policy without centralizing every failure。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### transitive routing

A能到B且A能到C時，B是否可經A到C；VPC Peering不提供此能力，TGW可建立受控hub routing。

### Direct Connect

從客戶或colocation到AWS的專用網路連線；提供較穩定路徑，但本身不等於端到端加密或自動高可用。

### route table

保存routes並以longest-prefix match選下一跳的表格。

### resolver

代替application查DNS並cache答案的服務；VPC可用Amazon-provided resolver，hybrid環境可用Route 53 Resolver endpoints轉送。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### DNS

Domain Name System，把hostname查成IP或其他records的分散式命名系統；resolver提出查詢，hosted zone保存權威答案。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

### VPN

Virtual Private Network，在既有Internet上建立加密tunnel；AWS Site-to-Site VPN通常提供兩條IPsec tunnels。

## 回到 AWS：Components、功用與責任邊界

### Route 53 Resolver

- **功用：** 在VPC DNS與on-premises DNS之間轉送查詢。
- **底層機制：** Inbound endpoint讓外部查VPC names；outbound endpoint依resolver rules把指定domain送到外部DNS。
- **關鍵設定：** inbound/outbound endpoints、target IPs、forward/system rules、RAM sharing、query logging與SG。
- **選擇時機：** hybrid DNS、split-horizon與多帳號central DNS。
- **替換時機：** Internet public DNS delegation使用hosted zones/NS records，不需Resolver endpoints。

### AWS Transit Gateway

- **功用：** 以regional hub連接大量VPC、VPN與Direct Connect。
- **底層機制：** Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。
- **關鍵設定：** attachments、association、propagation、TGW route tables、appliance mode、ECMP與multicast。
- **選擇時機：** 數十到數千網路、hub-and-spoke、集中egress/inspection或hybrid routing。
- **替換時機：** 只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。

### AWS Network Firewall

- **功用：** 在VPC中提供managed stateful/stateless L3–L7 network inspection。
- **底層機制：** Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。
- **關鍵設定：** firewall policy、stateless/stateful rule groups、HOME_NET、TLS inspection、logging與route symmetry。
- **選擇時機：** 集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。
- **替換時機：** 只需ENI allow-list用SG；HTTP application attacks用WAF；第三方appliance用GWLB。

## 考前與實作時再查：設定操作手冊

### Route 53 Resolver：逐項設定說明

#### `inbound/outbound endpoints`

- **控制什麼：** `inbound/outbound endpoints`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「hybrid DNS、split-horizon與多帳號central DNS。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route 53 Resolver的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `target IPs`

- **控制什麼：** `target IPs`指定Route 53 Resolver讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `forward/system rules`

- **控制什麼：** `forward/system rules`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「hybrid DNS、split-horizon與多帳號central DNS。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route 53 Resolver以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `RAM sharing`

- **控制什麼：** `RAM sharing`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「hybrid DNS、split-horizon與多帳號central DNS。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route 53 Resolver建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `query logging`

- **控制什麼：** `query logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「hybrid DNS、split-horizon與多帳號central DNS。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route 53 Resolver選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `SG`

- **控制什麼：** `SG`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「hybrid DNS、split-horizon與多帳號central DNS。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Route 53 Resolver中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

### AWS Transit Gateway：逐項設定說明

#### `attachments`

- **控制什麼：** Attachment把VPC、VPN、Direct Connect gateway、peering或Connect連到一個regional Transit Gateway，形成可被TGW routing管理的入口。
- **何時需要：** 需要hub-and-spoke、transitive routing、集中egress／inspection或大量network互連時。
- **怎麼設定／驗證：** 建立attachment並選擇正確subnets/AZ；VPC route table仍要把remote CIDRs指向TGW，另一側也要有return path。
- **常見錯法：** Attachment available只代表control plane完成；沒有VPC routes、TGW routes、DNS與security policy時，application仍完全不通。

#### `association`

- **控制什麼：** 每個attachment一次只能關聯一張TGW route table；該表決定從此attachment進入的封包要依哪組routes轉送。
- **何時需要：** 要把production、shared services、inspection與isolated networks分成不同route domains時。
- **怎麼設定／驗證：** 停用不適合的default association，為每個attachment指定入口route table；以來源attachment逐一驗證可見目的地。
- **常見錯法：** Association不是把attachment的CIDR發布給別人；把它和propagation混淆會造成黑洞或意外互通。

#### `propagation`

- **控制什麼：** 把attachment可到達的prefix動態加入指定TGW route table，讓使用該表的其他來源知道如何前往該attachment。
- **何時需要：** VPC/VPN/DX routes很多或會變動，不想逐條維護static routes時。
- **怎麼設定／驗證：** 只對應該學到該prefix的route tables啟用propagation；配合static blackhole/inspection routes與route export持續驗證。
- **常見錯法：** Propagation到某張表不會改變attachment自己的association；過度propagate會破壞segmentation並擴大blast radius。

#### `TGW route tables`

- **控制什麼：** 保存destination prefix到attachment的next hop；可用多張表建立transitive hub中的segmentation與service chaining。
- **何時需要：** VPC數量增加、不同環境需要不同可達性，或所有跨網流量必須先經inspection VPC時。
- **怎麼設定／驗證：** 為route domain建立獨立表，設association、propagation、static及blackhole routes；逐來源畫出forward/return path並檢查longest prefix。
- **常見錯法：** 單張全互通表最簡單但blast radius最大；錯誤default route或非對稱return path可能繞過stateful firewall。

#### `appliance mode`

- **控制什麼：** 在inspection VPC attachment上維持同一flow的AZ親和與對稱路徑，使stateful virtual appliance能看到往返封包。
- **何時需要：** 透過TGW把東西向或南北向流量送進跨AZ firewall/IDS appliance fleet時。
- **怎麼設定／驗證：** 只在appliance VPC attachment啟用appliance mode，配合各AZ endpoint/subnet與TGW routes；用雙向flow及故障切換驗證對稱性。
- **常見錯法：** 在spoke隨意啟用不能修正錯誤route；缺少對稱路徑時stateful appliance會把回程當成未知connection丟棄。

#### `ECMP`

- **控制什麼：** Equal-Cost Multi-Path讓TGW在多條等成本VPN/Connect路徑間以flow hash分散流量，提高aggregate throughput與冗餘。
- **何時需要：** 單一VPN tunnel吞吐不足，且on-prem routers能以BGP廣告相同prefix與相同路徑成本時。
- **怎麼設定／驗證：** 在TGW開啟VPN ECMP，建立多條動態路由連線並廣告相同prefix；監控每條tunnel、BGP與aggregate throughput。
- **常見錯法：** ECMP是per-flow而非把單一flow切開；static VPN或不相等BGP path通常無法得到預期分流。

#### `multicast`

- **控制什麼：** 讓一個source把封包送到multicast group，由TGW複製給已註冊receivers，支援少數需要一對多IP傳送的workload。
- **何時需要：** 市場資料、媒體或legacy discovery確實依賴multicast，且unicast fan-out成本／相容性不合適時。
- **怎麼設定／驗證：** 建立multicast domain、關聯subnets並註冊sources/members；確認instance、OS與security rules支援，再量測receiver loss。
- **常見錯法：** Multicast不會自動跨所有attachments或Internet；大多數cloud application用SNS/Kinesis等application-level fan-out更容易治理。

### AWS Network Firewall：逐項設定說明

#### `firewall policy`

- **控制什麼：** `firewall policy`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `stateless/stateful rule groups`

- **控制什麼：** `stateless/stateful rule groups`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `HOME_NET`

- **控制什麼：** `HOME_NET`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `TLS inspection`

- **控制什麼：** `TLS inspection`定義connection入口、協定、port或TLS身份，決定client能否建立第一段連線。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall的listener/endpoint建立明確protocol與port；TLS同時選certificate、security policy及renewal owner，並以真實client握手測試。
- **常見錯法：** 入口設定正確仍可能被SG/NACL/route阻擋；certificate過期、網域不符或前後端protocol混淆也會造成失敗。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `route symmetry`

- **控制什麼：** `route symmetry`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Network Firewall的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

## 讀到這裡，請用自己的話說一次

1. Route 53 Resolver的責任：在VPC DNS與on-premises DNS之間轉送查詢。
2. 底層機制：Inbound endpoint讓外部查VPC names；outbound endpoint依resolver rules把指定domain送到外部DNS。
3. 第一個要看的設定：inbound/outbound endpoints、target IPs、forward/system rules、RAM sharing、query logging與SG。
4. 選擇邏輯：用Route 53 Resolver endpoints/rules共享DNS，TGW route tables隔離環境，inspection VPC集中安全設備。
5. 不要混淆：AWS Transit Gateway的責任是「以regional hub連接大量VPC、VPN與Direct Connect。」；它不會自動取代Route 53 Resolver。
6. 替換訊號：Internet public DNS delegation使用hosted zones/NS records，不需Resolver endpoints。
7. 最常見錯法：轉送DNS形成loop，或forward path經firewall而return path繞過，造成stateful檢查失敗。
8. 可移植原則：centralize policy without centralizing every failure。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Route 53 Resolver | 在VPC DNS與on-premises DNS之間轉送查詢。 | Inbound endpoint讓外部查VPC names；outbound endpoint依resolver rules把指定domain送到外部DNS。 | hybrid DNS、split-horizon與多帳號central DNS。 | Internet public DNS delegation使用hosted zones/NS records，不需Resolver endpoints。 |
| AWS Transit Gateway | 以regional hub連接大量VPC、VPN與Direct Connect。 | Attachments關聯一張TGW route table並可向其他表propagate，藉此建立segmentation與transitive routing。 | 數十到數千網路、hub-and-spoke、集中egress/inspection或hybrid routing。 | 只有少數VPC可用Peering省每GB處理費；單一服務發佈用PrivateLink。 |
| AWS Network Firewall | 在VPC中提供managed stateful/stateless L3–L7 network inspection。 | Firewall endpoints部署到inspection subnets，route強制流量對稱經過；stateful rules可用Suricata語法。 | 集中egress/ingress inspection、domain/IP filtering、IDS/IPS與合規。 | 只需ENI allow-list用SG；HTTP application attacks用WAF；第三方appliance用GWLB。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | 中央inspection便於治理，但對稱路由、appliance mode、跨AZ成本與容量都需設計。 | 只有當題目條件明確改變時才可能合理。 | 轉送DNS形成loop，或forward path經firewall而return path繞過，造成stateful檢查失敗。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「中央inspection便於治理，但對稱路由、appliance mode、跨AZ成本與容量都需設計。」之間做選擇。
- 認得常考設定：inbound/outbound endpoints、target IPs、forward/system rules、RAM sharing、query logging與SG。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-3.4 Determine high-performing and/or scalable network architectures。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：Internet public DNS delegation使用hosted zones/NS records，不需Resolver endpoints。
- 對應官方tasks：SAP-1.1 Architect network connectivity strategies；SAP-1.2 Prescribe security controls；SAP-1.4 Design a multi-account AWS environment；SAP-2.3 Determine security controls based on requirements。

## 本章 10 題考題

### 練習題 1｜SAP｜20.1 On-premises 查 AWS private DNS

On-premises client要解析 Route 53 private hosted zone aws.corp。正確 query path是什麼？

A. On-prem DNS對 aws.corp設 conditional forward到 VPC Resolver inbound endpoint IP，再由 Resolver查 associated private zone
B. 使用 outbound endpoint讓 on-prem query進 VPC
C. 把 private zone改 public
D. 讓 on-prem直接查每個 VPC保留的 +2 resolver IP

**答案：A**

- **A：** 正確。Inbound表示 queries從網路外部進入 VPC Resolver；需要 hybrid route與 UDP/TCP 53政策。
- **B：** 不正確。Outbound endpoint處理從VPC Resolver送往外部DNS的queries；on-prem client要進入VPC解析private hosted zone，應把query送到inbound endpoint。
- **C：** 不正確。公開 zone會暴露 private naming且不解決 split-horizon需求。
- **D：** 不正確。Amazon-provided resolver位址不應直接由 on-prem網路查詢。

**事實查證：** [What is Route 53 VPC Resolver? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)

### 練習題 2｜SAA｜20.2 VPC 查 on-premises DNS

VPC workload要解析 corp.local，而 authoritative DNS位於資料中心。應配置什麼？

A. Inbound endpoint主動查資料中心
B. Resolver outbound endpoint加 corp.local forwarding rule與 on-prem target IP，並確保 route/SG允許 DNS
C. Route 53 latency record
D. 只啟用 Peering DNS option

**答案：B**

- **A：** 不正確。Inbound接收外部送入的 query，不負責 VPC向外轉送。
- **B：** 正確。Outbound endpoint依 matching rule將 query送到外部 DNS；網路回程與 TCP/UDP 53仍要成立。
- **C：** 不正確。Latency policy選 application records，不轉送 private namespace。
- **D：** 不正確。Peering DNS option不等同任意 on-prem conditional forwarding。

**事實查證：** [What is Route 53 VPC Resolver? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)、[Forwarding outbound DNS queries to your network - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-outbound-queries.html)

### 練習題 3｜SAP｜20.3 Resolver rule matching（選兩項）

同一VPC關聯了example.com與dev.example.com兩條forwarding rules，並另有同名dev.example.com private hosted zone。Query為api.dev.example.com。哪兩項正確？

A. 較具體的 dev.example.com rule優先匹配
B. 依 rule建立時間選擇
C. dev.example.com forwarding rule會先於同名private hosted zone；若要讓該suffix改由VPC Resolver本地解析，可建立更具體或同名的SYSTEM rule
D. TGW route priority直接決定 DNS rule
E. 兩條 rules隨機輪替

**答案：A、C**

- **A：** 正確。Resolver依最具體suffix比對，因此api.dev.example.com先匹配dev.example.com，而不是較寬的example.com或預設dot rule。
- **B：** 不正確。Forwarding rule的建立時間不參與domain matching；即使example.com較早建立，仍由較長且更具體的dev.example.com suffix優先。
- **C：** 正確。當forwarding rule與private hosted zone同名時，forwarding rule優先；SYSTEM rule可為特定suffix建立例外，讓VPC Resolver使用本地或private-zone解析。
- **D：** 不正確。TGW route只決定packet能否到達outbound endpoint後方的DNS target，不會決定query套用example.com或dev.example.com哪一條Resolver rule。
- **E：** 不正確。Resolver rules依domain specificity與rule type選擇，不像weighted authoritative records隨權重分配回答，也不會在兩條matching rules間隨機輪替。

**事實查證：** [Forwarding outbound DNS queries to your network - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-outbound-queries.html)、[Values that you specify when you create or edit rules - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-outbound-queries-rule-values.html)

### 練習題 4｜SAP｜20.4 Resolver rule sharing（SAP-C02 baseline；Profiles為current enrichment）

依SAP-C02 baseline，中央DNS account要讓數百個consumer VPC使用同一組outbound forwarding rules；團隊也想了解較新的Route 53 Profiles能增加什麼。最佳做法？

A. 只建立Route 53 Profile即可；Profile會自動產生outbound endpoint ENI、TGW/DX/VPN route與on-prem conditional forwarder
B. Organizations會自動建立 DNS endpoints與 routes
C. 中央建立outbound endpoint與rules，透過AWS RAM分享rules並由consumer VPC完成association；另行建立SG與到DNS targets的route。Current enrichment可把rules加入Profile，再透過RAM分享Profile
D. 只分享 endpoint ENI IP就會自動套用 suffix rules

**答案：C**

- **A：** 不正確。Profile能聚合與關聯Resolver rules等DNS設定，卻不會自動產生outbound endpoint、network route或on-prem DNS設定；把它當成完整data path會造成timeout。
- **B：** 不正確。AWS Organizations可提供帳號與delegated-administration治理，但不會自動建立DNS endpoint ENI、security group、hybrid route或VPC association。
- **C：** 正確。SAP-C02 baseline是以RAM分享Resolver rule並由consumer VPC關聯；endpoint ENI、SG、TGW/VPN/DX route與on-prem conditional forwarding仍需另建。Route 53 Profiles是較新的ENRICHMENT-CURRENT，Profile本身也透過RAM分享。
- **D：** 不正確。Endpoint ENI IP只是DNS query的network target；domain suffix matching、rule target IP與VPC association是分開的控制面設定，分享IP不會套用rules。

**事實查證：** [Managing forwarding rules - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-rules-managing.html#resolver-rules-managing-sharing)、[What are Amazon Route 53 Profiles? - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles.html)

### 練習題 5｜SAP｜20.5 DNS forwarding loop

AWS outbound endpoint把corp.local轉送到on-prem resolver；該resolver又以conditional forward把corp.local送回AWS inbound endpoint，形成AWS outbound→on-prem→AWS inbound→outbound的循環。Clients看到SERVFAIL/timeout。應如何修正？

A. 建立明確 authoritative owner與單向 conditional forwarding，移除循環規則並用 Resolver query logs/dig驗證
B. 降低 TTL即可打破 loop
C. 增加更多 outbound endpoints
D. 改成 weighted records

**答案：A**

- **A：** 正確。應先指定corp.local的authoritative owner；若on-prem權威，AWS只單向forward到on-prem且on-prem不得把同suffix送回AWS。再以query logs與dig追蹤每一跳，確認循環已消失。
- **B：** 不正確。TTL只控制authoritative answer可被cache多久，不會改變recursive resolver的forward destination，因此無法切斷AWS與on-prem之間的query loop。
- **C：** 不正確。增加outbound endpoints只增加可送出循環query的ENI與容量，不會修正namespace ownership或conditional-forward方向，反而可能放大負載。
- **D：** 不正確。Weighted routing policy是在authoritative hosted zone中選擇records；題目故障發生於recursive forwarding graph，必須修規則方向而非改answer權重。

**事實查證：** [Forwarding outbound DNS queries to your network - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-outbound-queries.html)、[Resolver query logging - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-query-logs.html)、[Best practices for VPC Resolver - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/best-practices-resolver.html)

### 練習題 6｜SAP｜20.6 TGW route-domain segmentation

Prod與 dev attachments都需到 shared DNS VPC，但不得彼此互通。應如何配置？

A. 單張全互通 TGW table並以名稱區分
B. 只靠每台 instance SG，TGW route leak無妨
C. 用 PrivateLink發布整個 DNS subnet
D. Prod/dev關聯不同 TGW tables，只向各表 propagate shared-services prefix而不互相發布 prod/dev prefixes

**答案：D**

- **A：** 不正確。Attachment或subnet名稱只是metadata，不會改變TGW route table association、propagation或data-plane reachability，因此無法提供prod/dev隔離。
- **B：** 不正確。SG可補充保護，但 route-domain應先符合隔離 contract。
- **C：** 不正確。DNS server network通常需要明確 hybrid routing；PrivateLink不是任意 subnet發布。
- **D：** 正確。Association決定來源查表，選擇性 propagation建立 least-connectivity。

**事實查證：** [Transit gateway route tables in AWS Transit Gateway - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)

### 練習題 7｜SAP｜20.7 Stateful inspection 對稱路徑

Spoke A→B去程經 inspection VPC，回程由 TGW直接回 A，stateful firewall丟包。最佳修正？

A. 修改 TGW/VPC routes讓雙向都經相同 inspection service，並在 appliance attachment正確使用 appliance mode
B. 只開 firewall SG ephemeral ports
C. 提高 DNS TTL
D. 啟用 ALB stickiness

**答案：A**

- **A：** 正確。Stateful engine需要同一 flow雙向可見；route symmetry與 AZ affinity都要驗證。
- **B：** 不正確。SG allow不能補回繞過 firewall的 return path。
- **C：** 不正確。DNS只負責把名稱解析成位址，不會控制 TGW資料面的回程 next hop。
- **D：** 不正確。這是TGW與stateful firewall的雙向routing問題，流量不經ALB target selection；啟用stickiness無法修正asymmetric return path。

**事實查證：** [Amazon VPC attachments in AWS Transit Gateway - Amazon VPC](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html#appliance-mode)、[Centralized network security for VPC-to-VPC and on-premises to VPC traffic - Building a Scalable and Secure Multi-VPC AWS Network Infrastructure](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/centralized-network-security-for-vpc-to-vpc-and-on-premises-to-vpc-traffic.html)

### 練習題 8｜SAP｜20.8 Network Firewall 集中 egress path

Spokes透過 TGW與 inspection VPC集中上網。哪條 IPv4 path最合理？

A. Spoke→IGW→firewall，回程由 NAT直達 spoke
B. Spoke→TGW→該 AZ Network Firewall endpoint→NAT Gateway→IGW，回程反向並依各 hop route
C. 建立 firewall policy後 packets會自動經過，無需 routes
D. 所有 AZ固定繞單一 AZ endpoint最可靠

**答案：B**

- **A：** 不正確。Private spokes不直接經 IGW，且回程必須維持 stateful path。
- **B：** 正確。Firewall負責 inspection、NAT負責 IPv4 translation、IGW負責 Internet path；各 AZ routes不可省略。
- **C：** 不正確。Network Firewall policy只定義封包到達endpoint後如何檢查，不會自動修改VPC或TGW routes把spoke流量插入inspection data path。
- **D：** 不正確。只部署單AZ firewall endpoint會讓其他AZ流量產生cross-AZ依賴，並在該AZ或endpoint失效時擴大故障範圍與潛在資料處理成本。

**事實查證：** [AWS Network Firewall example architectures with routing - AWS Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)、[Using the NAT gateway with AWS Network Firewall for centralized IPv4 egress - Building a Scalable and Secure Multi-VPC AWS Network Infrastructure](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/using-nat-gateway-with-firewall.html)

### 練習題 9｜SAP｜20.9 Stateless/stateful rules 與 HOME_NET

Network Firewall要檢查多個 spoke CIDR的 east-west traffic。哪個設定觀念正確？

A. SG rules會自動匯入 Network Firewall
B. HOME_NET是 Route 53 hosted zone名稱
C. Stateless rules先分類/轉交，stateful engine依 flow與 rule group檢查；HOME_NET等變數要涵蓋實際 internal CIDRs
D. Stateful rules不需要雙向 flow經相同 firewall

**答案：C**

- **A：** 不正確。Security group與Network Firewall rule groups是獨立policy systems，SG規則不會自動匯入Suricata或stateless firewall policy。
- **B：** 不正確。HOME_NET是 stateful rule variable中的網路範圍概念。
- **C：** 正確。錯誤 HOME_NET可能讓預期 Suricata/stateful rules不匹配，應搭配 alert/flow logs驗證。
- **D：** 不正確。Stateful inspection需要同一flow的雙向封包經相容的firewall endpoint；非對稱路徑會使connection state不完整並造成合法response被丟棄。

**事實查證：** [Network Firewall stateless and stateful rules engines - AWS Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/firewall-rules-engines.html)、[Examples of stateful rules for Network Firewall - AWS Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/suricata-examples.html#suricata-example-rule-with-domain-name-variable)

### 練習題 10｜SAP｜20.10 TLS inspection 的信任與邊界（選兩項）

公司要讓內部clients經Network Firewall連外部public TLS APIs，採outbound forward-proxy inspection；部分clients使用certificate pinning，且流量可能含敏感資料。哪兩項設計正確？

A. 啟用 TLS inspection後 clients不需信任任何 CA
B. 在ACM匯入具私鑰的CA certificate供outbound inspection使用，將該CA加入受管clients的trust store，並規劃私鑰保護與rotation
C. WAF可取代任意 TCP TLS解密
D. 依資料分類限定解密 scope並為 certificate pinning、隱私或不相容 traffic設例外
E. 解密成功後 IAM與 application authentication可移除

**答案：B、D**

- **A：** 不正確。Outbound forward-proxy inspection會動態簽發client看到的server certificate；client若不信任inspection CA，TLS驗證便會失敗。
- **B：** 正確。AWS Network Firewall要求outbound inspection使用ACM中的CA certificate與private key；受管clients也必須信任該CA，並需要安全的certificate lifecycle與rotation。
- **C：** 不正確。AWS WAF只處理支援的HTTP(S) web application流量，不能替任意TCP/TLS flow執行Network Firewall的decrypt、inspect與re-encrypt資料路徑。
- **D：** 正確。Certificate pinning的client可能拒絕代理憑證，解密也會擴大敏感資料暴露；因此應以scope configuration排除不相容或不應解密的destinations與流量。
- **E：** 不正確。TLS inspection只提供network content visibility與policy enforcement，不驗證業務使用者權限；IAM、mTLS、token與application authorization仍須保留。

**事實查證：** [Inspecting SSL/TLS traffic with TLS inspection configurations in AWS Network Firewall - AWS Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tls-inspection-configurations.html)、[Using SSL/TLS certificates with TLS inspection configurations in AWS Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tls-inspection-certificate-requirements.html)、[Considerations when working with TLS inspection configurations in AWS Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tls-inspection-considerations.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「用Route 53 Resolver endpoints/rules共享DNS，TGW route tab…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「大型組織需要統一解析private names、分離route domains並檢查流量。」，所以「用Route 53 Resolver endpoints/rules共享DNS，TGW route tables隔離環境，inspection VPC集中安全設備。」能直接滿足它；若constraint改成「中央inspection便於治理，但對稱路由、appliance mode、跨AZ成本與容量都需設計。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「用Route 53 Resolver endpoints/rules共享DNS，TGW route tables隔離環境，inspection VPC集中安全設備。」。替代方案「中央inspection便於治理，但對稱路由、appliance mode、跨AZ成本與容量都需設計。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「轉送DNS形成loop，或forward path經firewall而return path繞過，造成stateful檢查失敗。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「大型組織需要統一解析private names、分離route domains並檢查流量。」，排除會導致「轉送DNS形成loop，或forward path經firewall而return path繞過，造成stateful檢查失敗。」的選項，再選「用Route 53 Resolver endpoints/rules共享DNS，TGW route tables隔離環境，inspection VPC集中安全設備。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-3.4 Determine high-performing and/or scalable network architectures；SAP-1.1 Architect network connectivity strategies；SAP-1.2 Prescribe security controls。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「用Route 53 Resolver endpoints/rules共享DNS，TGW route tables隔離環境，inspection VPC集中安全設備。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「centralize policy without centralizing every failure」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
