---
chapter: 7
title: 多 VPC 互連
part: 1
---

# 第 7 章　多 VPC 互連：Peering、Transit Gateway、PrivateLink 與 VPC Lattice

> [!abstract] 本章地圖
> **你會學到**：
> - 分辨「打通網路」「發布一個服務」「連接應用程式」三種互連抽象，並對應到 VPC peering、Transit Gateway、PrivateLink、VPC Lattice
> - 設定 VPC peering 的雙向路由、SG 參照與 DNS，並說清楚它不能做的事（非遞移、不能重疊、不能借用對方的閘道）
> - 用 Transit Gateway 的 association 與 propagation 設計 prod／dev／shared 隔離，並知道 appliance mode 何時必要
> - 用 PrivateLink endpoint service 把一個服務安全地提供給其他帳號，即使雙方 CIDR 重疊
> - 依 VPC 數量、方向、CIDR 重疊、協定層級與成本，選出合適的互連方式
>
> **前置知識**：第 5 章（route table、longest prefix match、CIDR 規劃）、第 6 章（security group、interface endpoint）
> **考試比重**：SAA ★★☆（Domain 1 安全、Domain 3 網路效能）｜SAP ★★★（Domain 1 網路連線策略、多帳號環境）

## 7.1 故事：一個 VPC 裝不下整家公司

Wanderly 成立第二年，工程團隊從 8 個人長到 60 個人。平台團隊決定採用多帳號架構（第 14 章）：production、staging、development 各自一個帳號，另外有一個 shared services 帳號放 CI/CD runner、監控與內部套件庫，還有一個 data 帳號給分析團隊跑資料管線。每個帳號都有自己的 VPC，CIDR 依照第 5 章的規劃互不重疊。

帳號分開之後，問題馬上浮現。Production 的應用程式需要把日誌送到 shared services 的收集器；CI/CD runner 需要部署到 production 與 staging；分析團隊要從 production 的 read replica 抽資料。網路工程師小林一開始用 VPC peering 一條一條接，三個月後已經有 10 條 peering，每次新增一個 VPC，都要修改好幾張 route table，而且沒人說得清楚「development 到底能不能連到 production」。

同時，業務部門帶來另一個需求：一家合作的連鎖飯店要即時查詢 Wanderly 的房價 API，希望走私有網路，不經過 Internet。對方的 VPC 也用了 `10.20.0.0/16`，和 Wanderly production 撞在一起。

這一章要回答的就是：多個 VPC 之間，**該打通到什麼程度、用什麼工具打通、打通後怎麼控制範圍**。我們會從最簡單的 peering 開始，看它在什麼規模下失效，再一步步引入 Transit Gateway、PrivateLink 與 VPC Lattice。

## 7.2 三種互連抽象：網路、服務、應用程式

在挑工具之前，先問一個問題：「連過去之後，對方要能碰到什麼？」答案決定了互連的抽象層級。

| 抽象 | 意思 | 對方能碰到 | AWS 工具 |
|---|---|---|---|
| 網路層互連 | 讓兩個網路的 IP 互相可路由 | 對方整段 CIDR（再由 SG／NACL 限制） | VPC peering、Transit Gateway |
| 服務層互連 | 只把某一個服務的入口放進對方網路 | 只有那個服務 | PrivateLink（endpoint service） |
| 應用層互連 | 以服務名稱與身份連接，網路細節交給平台 | 被授權的服務與路徑 | VPC Lattice |

另外還有一種「不連接，而是合併」的思路：**VPC sharing**，讓多個帳號直接共用同一個 VPC（7.8 節）。

這張表最重要的意義是：**網路層互連的預設範圍最大**。兩個 VPC 用 peering 接起來後，路由上整段 CIDR 都可達，安全性完全依賴雙方的 SG 與 NACL 寫得夠緊。如果需求只是「呼叫一個 API」，給整段網路是給太多了。考試裡「最小暴露」「只需要存取一個服務」「CIDR 重疊」這類關鍵字，通常就在暗示服務層或應用層的方案。

## 7.3 VPC peering：兩個 VPC 之間的私有直連

### 它是什麼、怎麼建立

**VPC peering（VPC 對等連線）** 是兩個 VPC 之間的一條私有網路連線，讓雙方可以用 private IP 互相通訊，就像在同一個網路裡一樣。它不是一台設備，沒有頻寬瓶頸，也沒有單點故障；流量走 AWS 的內部網路，不經過 Internet。

建立流程有三步：

1. **Requester（請求方）** 發出 peering 請求，指定對方的 VPC ID（跨帳號時還要指定帳號 ID，跨 Region 時指定 Region）。
2. **Accepter（接受方）** 接受請求。未接受的請求在一段時間後（7 天）會過期。
3. **雙方各自更新 route table**：在需要互通的 subnet 的 route table 加入「對方 CIDR → `pcx-xxxx`」。

第三步是最常被忘記的。Peering 狀態變成 `active` 只代表連線存在，**AWS 不會自動修改任何 route table**。只加了一邊的 route，封包能過去但回不來，結果仍是 timeout。

```yaml
Resources:
  ProdToSharedPeering:
    Type: AWS::EC2::VPCPeeringConnection
    Properties:
      VpcId: !Ref ProdVpc            # 10.20.0.0/16
      PeerVpcId: vpc-0shared12345    # 10.16.0.0/16，另一個帳號
      PeerOwnerId: "444455556666"
      PeerRoleArn: arn:aws:iam::444455556666:role/PeeringAccepterRole
  ProdAppToShared:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref ProdAppRouteTable
      DestinationCidrBlock: 10.16.0.0/16
      VpcPeeringConnectionId: !Ref ProdToSharedPeering
```

跨帳號時，`PeerRoleArn` 是對方帳號裡一個允許接受 peering 的 IAM role，CloudFormation 用它自動完成接受步驟。對方 VPC 的 route table（`10.20.0.0/16 → pcx-xxxx`）則要在對方帳號的 template 裡建立。

### Peering 上的 SG 與 DNS

同一個 Region 的 peering，SG 規則可以直接參照對端 VPC 的 SG（第 6 章），例如 shared services 的日誌收集器 SG 允許「production 帳號的 SG-app」連入 TCP 4317。跨 Region 的 peering 不能參照 SG，只能寫 CIDR。

DNS 方面有一個常見陷阱：EC2 的 public DNS 名稱（例如 `ec2-54-1-2-3.ap-northeast-1.compute.amazonaws.com`）從對端 VPC 查詢時，預設會解析成 public IP，流量就不會走 peering。要讓它解析成 private IP，要在 peering 選項中啟用 **DNS resolution from remote VPC**，而且兩個 VPC 都要開啟 `enableDnsSupport` 與 `enableDnsHostnames`。這個選項分成 requester 與 accepter 兩側：某一側啟用後，**對端 VPC 查詢「我這一側」的 public DNS 名稱時**會得到 private IP。要雙向都生效，就兩側都啟用；跨帳號時，每一側由擁有該 VPC 的帳號自己啟用。

```bash
# requester 帳號執行
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id pcx-0prodshared \
  --requester-peering-connection-options AllowDnsResolutionFromRemoteVpc=true

# accepter 帳號用自己的憑證執行
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id pcx-0prodshared \
  --accepter-peering-connection-options AllowDnsResolutionFromRemoteVpc=true
```

這個選項只處理「名稱解析成哪個 IP」，不建立 route，也不修改 SG。如果應用程式使用 private hosted zone 的名稱，則要把 hosted zone 關聯到對端 VPC（第 9 章），與這個選項無關。

### Peering 的限制：考試最愛的四件事

**1. 不能遞移（non-transitive）。** 如果 A 和 B peering、B 和 C peering，A **不能**經過 B 連到 C。Peering 連線只負責「兩端之間」的流量，不會把收到的封包轉送到第三方。A 要連 C，必須另建 A–C peering。

**2. CIDR 不能重疊。** 兩個 VPC 的任何一段 CIDR（含 secondary CIDR）重疊或相同，就無法建立 peering。這正是第 5 章強調 CIDR 規劃的原因之一。

**3. 不能借用對方的閘道（no edge-to-edge routing）。** A 不能透過 peering 使用 B 的 Internet Gateway、NAT Gateway、VPN 連線、Direct Connect 連線，或 B 的 gateway endpoint（第 6 章）。即使你在 A 的 route table 寫 `0.0.0.0/0 → pcx`，B 也不會替 A 轉送往 Internet 的流量。

**4. 兩個 VPC 之間只能有一條 peering。** 不能為了「備援」建第二條；peering 本身就不是單點。

```text
         ┌────────┐   pcx-1   ┌────────┐   pcx-2   ┌────────┐
         │ VPC A  │◄─────────►│ VPC B  │◄─────────►│ VPC C  │
         │10.1/16 │           │10.2/16 │           │10.3/16 │
         └────────┘           └───┬────┘           └────────┘
                                  │
             ① A → C：✗ 不能經 B 轉送          [NAT GW]──[IGW]
             ② A → B 的 NAT/IGW 上網：✗ 不支援 edge-to-edge
             ③ A ↔ B、B ↔ C：✓ 各自直連可通
```

① A 要到 C，封包到了 B 就停止，因為 pcx-1 只承載 A 與 B 之間的流量。② A 不能把 B 當作出口，B 的 NAT Gateway 與 IGW 只服務 B 自己的流量。③ 直接相連的兩端可以通訊，前提是雙方 route table 與 SG 都設好。

### Peering 的規模與費用

- 每個 VPC 的 active peering 數量有 quota：預設 50，可申請提高，上限 125。
- **全互連（full mesh）** 需要 n × (n − 1) ÷ 2 條 peering：5 個 VPC 是 10 條，20 個 VPC 是 190 條，每條還要在兩端的多張 route table 加 route。
- Peering **沒有每小時費用，也沒有資料處理費**，只有資料傳輸費：同一個 AZ 內經 peering 的流量免費，跨 AZ 按一般跨 AZ 費率，跨 Region 按跨 Region 費率。這讓 peering 成為「兩個 VPC 之間大量流量」最便宜的方式，7.10 節的成本比較會再用到。
- Peering 可以跨帳號、跨 Region；跨 Region 的流量由 AWS 加密。

> [!tip] 考試提示
> 「兩、三個 VPC 互通，CIDR 不重疊，要最簡單、最便宜」→ VPC peering。「A 已和 B peering、B 和 C peering，A 要連 C」→ 建 A–C peering，或改用 Transit Gateway；選項說「在 B 開啟轉送」「在 A 加指向 B 的 route」都是錯的。

## 7.4 Transit Gateway：Region 裡的中央路由器

### 為什麼需要

回到小林的困境：10 條 peering、每加一個 VPC 就要改好幾張 route table、沒人看得懂整體連通關係。根本原因是 peering 是點對點的，**連線數隨 VPC 數量平方成長，而且沒有地方集中表達「誰可以連誰」**。

**AWS Transit Gateway（TGW）** 是一個 Region 範圍、由 AWS 管理的**中央路由器（hub）**。每個 VPC、VPN 或 Direct Connect 只要接到 TGW 一次，就能依 TGW 上的路由表連到其他網路。連線數從 n²／2 變成 n，而且**它是遞移的**：A 接 TGW、C 接 TGW，A 就能經 TGW 到 C，只要 TGW 路由表允許。

### Attachment：誰接到 TGW 上

每一個接上 TGW 的網路稱為一個 **attachment（附加連線）**，主要類型有：

| Attachment 類型 | 連接什麼 | 本書章節 |
|---|---|---|
| VPC | 同 Region 的 VPC（可以是其他帳號的 VPC） | 本章 |
| VPN | Site-to-Site VPN，連到地端 | 第 8 章 |
| Direct Connect gateway | 經 transit VIF 連到地端 | 第 8 章 |
| Peering | 另一個 TGW（同 Region 或跨 Region） | 本章 |
| Connect | 以 GRE 與 BGP 連接 SD-WAN 設備 | 第 41 章 |

建立 **VPC attachment** 時，要在 VPC 的每個 AZ 各選一個 subnet。TGW 會在這些 subnet 中放置網卡，作為流量進出 TGW 的入口。**只有選了 subnet 的 AZ，裡面的資源才能使用 TGW**，所以每個有 workload 的 AZ 都要選。AWS 建議為 TGW attachment 建立專用的小 subnet（例如 /28），不放其他資源，讓它們的 route table 與 NACL 可以獨立管理。

TGW 可以透過 **AWS RAM（Resource Access Manager，跨帳號資源共享服務）** 共享給其他帳號，讓各帳號把自己的 VPC 接上同一個 TGW。Wanderly 的做法是由 network 帳號擁有 TGW，再共享給整個 Organization。

### TGW route table：association 與 propagation

TGW 的核心是它自己的 **TGW route table**（和 VPC 的 route table 是不同的東西）。理解 TGW，就是理解兩個動作：

- **Association（關聯）**：每個 attachment **只能關聯一張** TGW route table。它決定「**從這個 attachment 進入 TGW 的流量，要查哪一張表**」。
- **Propagation（傳播）**：一個 attachment 可以把自己的路由（例如 VPC 的 CIDR，或 VPN 透過 BGP 學到的地端網段）**傳播到一張或多張** TGW route table。它決定「**哪些表知道怎麼到我**」。

除了傳播來的動態路由，也可以手動加 **static route**，或加 **blackhole route**（符合的流量直接丟棄，用來明確封鎖某段網路）。

一句話記憶：**association 管「我出去時看哪張地圖」，propagation 管「我出現在哪些地圖上」**。兩者分開，才做得到「A 能到 B，但 B 不能到 A 的其他鄰居」這類隔離。

### 用路由表做隔離：Wanderly 的 segmentation

Wanderly 的需求是：production 與 development 不能互通；兩者都要能到 shared services；地端辦公室（經 VPN）可以到所有環境。

```text
                        ┌──────────── Transit Gateway ─────────────┐
 [Prod VPC 10.20/16] ───┤ assoc → RT-prod   prop → RT-shared,RT-vpn │
 [Dev  VPC 10.25/16] ───┤ assoc → RT-dev    prop → RT-shared,RT-vpn │
 [Shared VPC 10.16/16] ─┤ assoc → RT-shared prop → RT-prod,RT-dev,  │
                        │                         RT-vpn            │
 [VPN 辦公室 10.0/16] ──┤ assoc → RT-vpn    prop → RT-prod,RT-dev,  │
                        │                         RT-shared         │
                        └──────────────────────────────────────────┘

 RT-prod  ：10.16/16 → Shared、10.0/16 → VPN            （沒有 10.25）
 RT-dev   ：10.16/16 → Shared、10.0/16 → VPN            （沒有 10.20）
 RT-shared：10.20/16 → Prod、10.25/16 → Dev、10.0/16 → VPN
 RT-vpn   ：10.20/16 → Prod、10.25/16 → Dev、10.16/16 → Shared
```

逐步看：

1. Prod 的流量進入 TGW 後查 **RT-prod**（association）。RT-prod 裡只有 shared 與辦公室的路由，因為只有這兩者把路由 propagate 到 RT-prod。Prod 送往 `10.25.x.x`（dev）的封包在 RT-prod 查不到路由，被丟棄。
2. Dev 同理，RT-dev 裡沒有 prod 的路由。
3. Shared 查 RT-shared，那裡有 prod、dev、辦公室三者的路由，所以 shared 能回應任何一方。
4. 辦公室查 RT-vpn，能到所有環境。

隔離是**雙向**成立的：prod 不在 RT-dev 中，dev 也不在 RT-prod 中。如果有人誤把 prod attachment propagate 到 RT-dev，dev 就能路由到 prod，這叫 **route leak（路由外洩）**；修正方式是停用那個 propagation，必要時在 RT-dev 加一條 prod CIDR 的 blackhole route 作為保險。

> [!warning] 常見誤解
> 「VPC 接上 TGW 後，VPC 的 route table 會自動更新。」不會。Propagation 只發生在 **TGW route table**。VPC 這一側的 route table 仍要手動加 route，例如 `10.0.0.0/8 → tgw-xxxx`。很多「TGW 都設好了還是不通」的問題，就是 VPC route table 沒指向 TGW。Customer-managed prefix list（第 6 章）可以讓這些 route 更容易維護。

### 跨 Region：TGW peering

TGW 是 Regional 資源，東京的 TGW 只能接東京的 VPC。要連到新加坡的網路，就在兩個 Region 各建一個 TGW，再建立 **TGW peering attachment**。

- 可以跨帳號、跨 Region，流量走 AWS 骨幹並加密。
- **TGW peering 上只能用 static route**：對端 Region 的 CIDR 必須手動加到本地 TGW route table，並指向 peering attachment；peering 不會自動 propagate 路由。
- 兩個 Region 的 CIDR 同樣不能重疊，這是第 5 章為每個 Region 預留不同位址區塊的原因。

如果需要跨很多 Region 的動態路由與集中政策，AWS 另有 **AWS Cloud WAN**（7.12 節、第 41 章）。

### Appliance mode：讓 stateful 防火牆看到完整連線

SAP 常考的情境：所有 VPC 之間的流量都要先經過一個 **inspection VPC** 中的防火牆設備（例如 AWS Network Firewall 或第三方 appliance）。防火牆是 stateful 的，**必須看到同一條連線的去程與回程**，否則會把它不認得的回程封包丟掉。

問題在於 TGW 預設會讓流量盡量留在來源的 AZ。若 VPC A 的來源在 AZ-a、VPC B 的目的地在 AZ-c，去程可能進入 inspection VPC 的 AZ-a 防火牆，回程卻進入 AZ-c 的防火牆。AZ-c 的防火牆沒看過這條連線的開頭，就會丟棄回應，造成「偶爾不通、看起來很隨機」的故障。

**Appliance mode** 是 VPC attachment 的一個選項，要在 **inspection VPC 的 attachment** 上啟用。啟用後，TGW 會依連線的資訊（來源與目的位址、port 等）選定一個 AZ，讓同一條連線的雙向流量都送到同一個 AZ 的防火牆，直到連線結束。

> [!tip] 考試提示
> 「集中 inspection VPC + TGW，跨 AZ 流量出現不對稱路由、防火牆丟包」→ 在 inspection VPC 的 TGW attachment 啟用 appliance mode。不是在每個 spoke VPC 啟用，也不是加 NAT。

### 頻寬與費用

- TGW 是受管服務，自動擴展。VPC attachment 的頻寬是每個 AZ 每個方向最高約 100 Gbps（這不是能在 Service Quotas 自助申請提高的 quota；需求更高時要聯絡 AWS 的 Solutions Architect 或 TAM 評估，設計上通常把流量分散到多個 AZ）；**VPN attachment 的標準 tunnel 每條最高 1.25 Gbps**（考試最常用的數字；AWS 另有每條最高 5 Gbps 的 large bandwidth tunnel 選項，見第 8 章）。需要更多 VPN 頻寬時，可以建立多條 VPN（必須使用 BGP 動態路由）並啟用 **ECMP（Equal-Cost Multi-Path，等價多路徑）**，把流量分散到多條 tunnel。
- 費用有兩部分：**每個 attachment 每小時**的費用，以及**每 GB 的資料處理費**（流量送進 TGW 時計算）。和 peering 相比，TGW 在大流量時明顯較貴；和數百條 peering 的管理成本相比，TGW 在規模大時明顯較省事。
- TGW 也支援 **Flow Logs**，可以記錄經過 TGW 的流量，用法類似第 6 章的 VPC Flow Logs。
- TGW 也支援 **SG referencing**：接在同一個 TGW 上的 VPC，可以在 SG 的 **inbound** 規則參照另一個 VPC 的 SG。限制是：必須在 TGW 與各 VPC attachment 兩邊都啟用；outbound 規則不能參照；跨 TGW peering，或流量經過 inspection VPC 的 Gateway Load Balancer／Network Firewall 時都不適用，這些情況仍要用 CIDR。

## 7.5 PrivateLink endpoint service：只發布一個服務

### 為什麼網路層互連不適合那家飯店

回到 7.1 節的連鎖飯店。他們只需要呼叫 Wanderly 的房價 API，用 peering 或 TGW 有三個問題：雙方 CIDR 都是 `10.20.0.0/16`，根本無法建立；就算不重疊，打通網路後飯店理論上能碰到 Wanderly 整個 VPC；而且雙方要協調路由、DNS、SG，等於把兩家公司的網路綁在一起。

第 6 章用 interface endpoint 私下存取 AWS 服務。**PrivateLink 讓你自己也能成為「服務提供者」**：把自己的服務包裝成 **endpoint service（端點服務）**，其他帳號在他們的 VPC 建立 interface endpoint，就能私下呼叫你的服務，就像他們呼叫 Secrets Manager 一樣。

```text
  Consumer：飯店的 VPC 10.20.0.0/16           Provider：Wanderly 的 VPC 10.20.0.0/16
  ┌─────────────────────────────┐            ┌──────────────────────────────────┐
  │ [飯店 App]                   │            │                                  │
  │    │ ① rates.wanderly.example│            │   [NLB（internal）] ── ④ ──► [房價 │
  │    ▼   → 10.20.5.77          │            │        ▲                   API]  │
  │ [Interface endpoint ENI      │ ② PrivateLink       │                          │
  │  10.20.5.77  SG: 443 from App]────────────────────►│ ③ endpoint service       │
  └─────────────────────────────┘            │   （acceptance、allowed principals）│
                                             └──────────────────────────────────┘
```

① 飯店的應用程式把服務名稱解析到自己 VPC 中 endpoint ENI 的 IP（`10.20.5.77` 是**飯店自己**的位址）。② 流量經 PrivateLink 由 AWS 轉送，不經過任何 route table 的跨 VPC 路由。③ Wanderly 的 endpoint service 先檢查這個 endpoint 是否被允許、是否已被接受。④ 流量抵達 Wanderly 的 Network Load Balancer，再轉到後端的 API。

兩邊都是 `10.20.0.0/16` 完全不是問題，因為**雙方的 IP 從來沒有互相路由過**：飯店只看到自己 VPC 裡的一個 ENI，Wanderly 只看到來自 NLB 的流量。

### Provider 端的設定

1. **在服務前面放一個 Network Load Balancer（NLB）**。Endpoint service 必須以 NLB 為前端（另一種是以 Gateway Load Balancer 為前端，用於流量檢查設備）。如果服務原本在 ALB 後面，可以讓 NLB 以 ALB 作為 target。
2. **建立 endpoint service**，關聯這個 NLB。
3. **Allowed principals**：設定哪些 AWS 帳號、IAM role 或 user 可以對這個服務建立 endpoint。不在清單上的帳號無法建立 endpoint 連到這個服務。
4. **Acceptance required**：開啟後，每個 endpoint 連線請求都要 provider 手動（或自動化）接受，適合需要審核客戶的場景。
5. **Private DNS name**（選用）：讓 consumer 用 `rates.wanderly.example` 這樣的名稱呼叫服務。Provider 必須在自己的 DNS 中加入一筆 TXT 記錄，**證明擁有這個網域**，AWS 驗證通過後才會生效。

### 你必須知道的特性

- **單向**：只有 consumer 能主動連到 provider，provider **不能**透過這條路徑主動連到 consumer 的任何資源。這對雙方都是安全保證。
- **AZ 要對得上**：Consumer 的 endpoint 只能建在 provider 的 NLB 有啟用的 AZ。要注意，不同帳號的 AZ 名稱（例如 `ap-northeast-1a`）可能對應到不同的實體 AZ；跨帳號規劃時要用 **AZ ID**（例如 `apne1-az1`）溝通。Provider 最好讓 NLB 涵蓋 Region 中所有 AZ。
- **Provider 看不到 consumer 的真實 IP**：流量到達 NLB 後，後端看到的來源 IP 是 NLB 的位址，不是 consumer 的 IP。若後端需要知道「是哪個客戶、哪個 endpoint」，要在 NLB 的 target group 啟用 **Proxy Protocol v2**，它會在連線開頭附上原始來源資訊與 VPC endpoint ID。
- **費用**：Consumer 付 interface endpoint 的每 AZ 小時費與每 GB 費用；provider 付 NLB 的費用。
- **規模**：一個 endpoint service 可以服務成千上萬個 consumer，這正是很多 SaaS 廠商（監控、資料庫、支付服務）提供「PrivateLink 連線選項」的方式。
- **Region**：傳統上 consumer 與 endpoint service 必須在同一個 Region。現在 provider 可以為 endpoint service 加入「支援的 Region」，consumer 建立 endpoint 時選擇服務所在的 Region，就能跨 Region 使用（需要明確的 IAM 權限）。AWS 建議能同 Region 就同 Region，因為延遲與成本較低；考試情境仍多以同 Region 為前提。

> [!note] PrivateLink vs interface endpoint，是同一件事嗎？
> PrivateLink 是底層技術；**interface endpoint** 是 consumer 端看到的資源；**endpoint service** 是 provider 端發布的資源。第 6 章連 Secrets Manager 時，AWS 就是 provider。本節只是把 provider 換成 Wanderly 自己。

## 7.6 VPC Lattice：用服務名稱與身份連接應用程式

### PrivateLink 在微服務規模下的不便

Wanderly 拆成微服務後，有 30 個服務分布在 6 個帳號，服務之間的呼叫關係錯綜複雜。如果每個服務都用 PrivateLink 發布，每個 provider 都要維護一個 NLB，每個 consumer VPC 都要為每個依賴建一個 interface endpoint，數量很快爆炸；而且 PrivateLink 是 L4（TCP／UDP）的，無法依 HTTP 路徑路由，也不知道「呼叫者是哪個 IAM role」。

**Amazon VPC Lattice** 是一個應用層的服務網路（service network）服務，目標是讓服務之間「用名稱連接、用身份授權」，而不用管底下的 VPC、CIDR、peering 或 TGW。

### 核心元件

```text
  [Booking 服務]（帳號 A，VPC 10.20/16）
      │ ① https://pricing.svc.wanderly.example/quote
      ▼
  VPC association（VPC 加入 service network，可附 SG）
      ▼
  ┌───────────── Service network「wanderly-prod」─────────────┐
  │  ② auth policy（service network 層級）：只允許本 Org 的身份 │
  │                                                           │
  │  Service：pricing                                          │
  │   ├ ③ auth policy（service 層級）：只允許 BookingRole        │
  │   ├ listener HTTPS:443                                     │
  │   │   ├ rule：/quote*  → target group A（ECS tasks）        │
  │   │   └ rule：/admin*  → fixed 403                          │
  │   └ ④ target group A（帳號 B，VPC 10.20/16，CIDR 重疊也可）  │
  └───────────────────────────────────────────────────────────┘
```

- **Service network（服務網路）**：一個邏輯上的邊界，把一群服務與一群 VPC 綁在一起。VPC 透過 **association** 加入 service network 後，VPC 內的用戶端就能呼叫網路中的服務。
- **Service（服務）**：一個可被呼叫的應用程式，有自己的 DNS 名稱、**listener**（監聽的協定與 port）與 **rules**（依路徑、header、method 等轉送）。Listener 協定有三種：HTTP、HTTPS（支援 HTTP/2，因此可承載 gRPC），以及 TLS。TLS listener 是 **TLS passthrough**：Lattice 不解密，由後端自己終止 TLS，因此也就無法依路徑或 header 路由。
- **Target group**：實際處理請求的目標，可以是 EC2 instance、IP、Lambda function、ALB，或 ECS／EKS 上的 container。
- **Auth policy**：IAM 格式的政策，可以設在 service network 與 service 兩個層級。啟用 IAM 驗證後，用戶端要用 SigV4 簽署請求，Lattice 會依呼叫者的 IAM 身份做授權。

①Booking 用服務名稱發出 HTTPS 請求，DNS 由 Lattice 管理。② 請求先經過 service network 層級的 auth policy，通常寫粗粒度的規則（例如「只允許本 Organization 的身份」）。③ 再經過 service 層級的 auth policy，寫細粒度規則。④ Rules 把請求轉到另一個帳號的 target group；兩個 VPC 的 CIDR 重疊也沒關係，因為 Lattice 在中間代理了連線。

一個 service 層級的 auth policy 例子：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::111122223333:role/BookingServiceRole" },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "arn:aws:vpc-lattice:ap-northeast-1:444455556666:service/svc-0pricing123/*",
      "Condition": { "StringEquals": { "vpc-lattice-svcs:RequestMethod": "GET" } }
    }
  ]
}
```

這條政策的意思是：只有 Booking 服務的 role 能呼叫 pricing 服務，而且只能用 GET。這是網路層工具做不到的事：peering 與 TGW 只認 IP，PrivateLink 只認「哪個 endpoint」，Lattice 認得「哪個 IAM 身份、哪個 HTTP method、哪個路徑」。

### 其他特性

- Service 與 service network 可以透過 **AWS RAM** 跨帳號共享，服務擁有者與網路管理者可以是不同團隊。
- 不需要 peering 或 TGW 就能跨 VPC、跨帳號；CIDR 重疊也沒問題。範圍是單一 Region。
- Lattice 從一段 link-local 位址範圍把流量送到 target，target 的 SG 要允許 Lattice 的 managed prefix list。
- 費用依服務的小時數、處理的資料量與請求數計算。
- Lattice 也能分享 TCP 資源：在資源所在的 VPC 建立 **resource gateway**，再用 **resource configuration** 描述資源（例如一個 RDS 資料庫的 DNS 名稱或 IP 與 port），其他 VPC 就能經 service network 存取它。這延伸到非 HTTP 的情境；考試仍以 HTTP／HTTPS 服務對服務的情境為主。

> [!warning] 常見誤解
> 「VPC 加入 service network 就代表可以呼叫所有服務。」VPC association 只提供網路入口。啟用 IAM 驗證時，每個請求還要通過 service network 與 service 兩層 auth policy；就像 security group 允許了 443，並不代表應用程式會讓你登入。

## 7.7 互連後的 DNS：名稱與路由是兩條獨立的路

到這裡可以整理一個在所有互連方式中都會遇到的原則：**DNS 回答「名稱是哪個 IP」，路由回答「這個 IP 怎麼到」，兩者必須各自正確。**

| 互連方式 | 路由由誰負責 | DNS 怎麼做 |
|---|---|---|
| VPC peering | 雙方 VPC route table | Peering DNS resolution 選項；private hosted zone 關聯對端 VPC |
| Transit Gateway | VPC route table + TGW route table | Private hosted zone 跨帳號關聯，或 Route 53 Resolver 規則（第 8 章） |
| PrivateLink | 不需要跨 VPC 路由 | Endpoint 的 private DNS，或 provider 的 private DNS name |
| VPC Lattice | 不需要跨 VPC 路由 | Lattice 管理服務名稱；可設定自訂網域 |

除錯時先分清楚是哪一條壞了：`dig` 回答的 IP 不對（例如解析成 public IP），是 DNS 問題；IP 對但 timeout，是路由、SG 或 NACL 問題。改 DNS 修不好路由，加 route 也修不好 DNS。

## 7.8 VPC sharing：不連接，而是共用

前面所有方式都是「多個 VPC 之間連起來」。另一個思路是：**一開始就不要有那麼多 VPC**。

**VPC sharing（VPC 共享）** 透過 AWS RAM，讓 VPC 的擁有者把 **subnet** 共享給同一個 Organization 中的其他帳號：

- **Owner（擁有者）帳號**：通常是 network 帳號，建立並管理 VPC、subnet、route table、NACL、IGW、NAT Gateway、TGW attachment 等網路資源。
- **Participant（參與者）帳號**：應用團隊的帳號，可以在共享的 subnet 中建立自己的 EC2、RDS、Lambda、ALB 等資源，並管理自己建立的 SG。Participant **不能**修改 owner 的 subnet、route table、NACL，也看不到或修改其他 participant 的資源。

效果是：網路由中央團隊統一管理，應用團隊仍保有帳號層級的權限隔離與帳單歸屬。計費的分法是：participant 支付自己建立的資源（EC2、RDS、Lambda 等），以及這些資源產生的跨 AZ、經 peering、經 IGW、經 Direct Connect gateway 的資料傳輸費；owner 支付 NAT Gateway、VGW、TGW、PrivateLink 與 VPC endpoint 的小時費與資料處理費，以及 shared VPC 中使用的 public IPv4 位址費用。同一個 AZ（以 AZ ID 認定）內的傳輸不論資源屬於哪個帳號都免費。同一個 VPC 內的流量走 local route，不需要 peering 或 TGW，也就沒有 TGW 的每 GB 處理費；IP 位址的使用效率也比「每個團隊一個 VPC」高。

取捨是：所有 participant 共享同一個網路邊界與 VPC 層級的 quota，隔離要靠 SG 與 subnet 設計；不同環境（prod 與 dev）通常仍會用不同的 shared VPC。共享 subnet 時也要注意 7.5 節提過的 AZ ID 問題：owner 與 participant 看到的 AZ 名稱可能不同。

## 7.9 組起來：Wanderly 的多 VPC 網路

把本章的工具放到同一張圖上：

```text
                       ┌──────────── TGW（network 帳號，RAM 共享）────────────┐
                       │   RT-prod      RT-dev       RT-shared      RT-vpn    │
                       └──┬──────────────┬─────────────┬──────────────┬──────┘
                    ①     │              │             │              │ ②
  ┌───────────────────────┴──┐  ┌────────┴──────┐  ┌───┴──────────┐  [VPN → 台北辦公室]
  │ Prod shared VPC 10.20/16 │  │ Dev VPC       │  │ Shared svcs  │
  │（owner: network 帳號）     │  │ 10.25/16      │  │ VPC 10.16/16 │
  │  booking 帳號的資源         │  └───────────────┘  │ CI/CD、監控   │
  │  payment 帳號的資源 ③       │                     └──────────────┘
  │         │                │
  │         │ ④ peering（大量資料，免處理費）
  │         ▼                │        ┌─────────────────────────┐
  └─────────┼────────────────┘        │ Data VPC 10.21/16        │
            └────────────────────────►│ 分析管線                  │
                                      └─────────────────────────┘
  ⑤ Endpoint service（NLB）── PrivateLink ──► 連鎖飯店 VPC（10.20/16，重疊無妨）
  ⑥ VPC Lattice service network：booking ⇄ pricing ⇄ inventory（跨帳號 IAM 授權）
```

① 所有 VPC 經 TGW 互連，四張 TGW route table 讓 prod 與 dev 互相隔離、都能到 shared services。② 台北辦公室經 VPN attachment 接到 TGW（第 8 章）。③ Production 用 VPC sharing，booking 與 payment 兩個帳號的資源共用同一個 VPC，網路由 network 帳號管理。④ Production 與 data VPC 之間每天搬移大量資料，除了 TGW 之外再加一條 peering；在 prod 的 route table 中，`10.21.0.0/16 → pcx` 比 `10.0.0.0/8 → tgw` 更精確，依 longest prefix match 會優先走 peering，省下 TGW 的處理費。⑤ 連鎖飯店經 PrivateLink 呼叫房價 API，CIDR 重疊不影響。⑥ 微服務之間的呼叫走 VPC Lattice，以 IAM 身份與 HTTP 規則授權。

這張圖展示了一個重要觀念：**這些工具不是互斥的**。一家公司通常同時使用好幾種，各自負責最適合的那一段。

## 7.10 比較與選型

### 規模、能力與成本比較

| 比較 | VPC peering | Transit Gateway | PrivateLink | VPC Lattice | VPC sharing |
|---|---|---|---|---|---|
| 抽象層級 | 網路（L3） | 網路（L3） | 服務（L4） | 應用（L7 為主） | 共用同一網路 |
| 遞移性 | 無 | 有（依路由表） | 不適用 | 不適用 | 不適用 |
| CIDR 重疊 | 不允許 | 同一路由域內不行 | 可以 | 可以 | 不適用 |
| 方向 | 雙向 | 雙向 | 單向（consumer → provider） | 用戶端 → 服務 | 同 VPC 內 |
| 典型規模 | 少量 VPC | 數十到數千個 attachment | 一個服務對大量 consumer | 大量微服務 | 多帳號共用少數 VPC |
| 連到地端 | 不行（無 edge-to-edge） | 可以（VPN、DX） | 地端可經路由使用 endpoint | 以 VPC 內用戶端為主 | 經 owner 的 TGW／VGW |
| 授權粒度 | IP／SG | IP／SG + 路由表隔離 | Endpoint 與 allowed principals | IAM 身份、HTTP 屬性 | SG 與帳號 |
| 主要費用 | 只有跨 AZ／跨 Region 傳輸 | 每 attachment 小時 + 每 GB 處理 | Endpoint 每 AZ 小時 + 每 GB；NLB | 每服務小時 + 每 GB + 每請求 | 無額外連線費 |
| 跨 Region | 可以 | TGW peering（static route） | 預設同 Region；provider 可開啟跨 Region 存取 | 單一 Region | 單一 Region |

### 選型決策流程

```text
需求是什麼？
├─ 只需要讓對方呼叫「一個或少數服務」
│   ├─ HTTP/HTTPS/gRPC 微服務、要 IAM 身份授權、路徑路由 → VPC Lattice
│   └─ 任意 TCP／UDP 服務、對外提供給客戶或 SaaS、CIDR 可能重疊 → PrivateLink
└─ 需要網路層的任意雙向互通
    ├─ CIDR 重疊？→ 先重新編址，或改用服務層方案（PrivateLink／Lattice），
    │               或用 private NAT Gateway 轉換位址（第 5 章）
    ├─ 只有 2～3 個 VPC、不需要連地端、要最便宜 → VPC peering
    ├─ 很多 VPC、要連地端、要集中隔離或 inspection → Transit Gateway
    │   └─ 其中兩個 VPC 之間流量特別大 → 額外加一條 peering 省處理費
    └─ 各帳號其實可以共用網路、由中央團隊管理 → VPC sharing（可與 TGW 並用）
```

## 7.11 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 兩個 VPC 私有互通、CIDR 不重疊、最便宜 | VPC peering + 雙向 route |
| A–B、B–C 已 peering，A 要連 C | 建 A–C peering 或改用 TGW；peering 不遞移 |
| 透過 peering 使用對方的 NAT Gateway／IGW／VPN | 不支援（no edge-to-edge routing） |
| 數十到數百個 VPC 加地端，簡化管理 | Transit Gateway |
| prod 與 dev 隔離，但都要到 shared services | TGW 多張 route table，以 association／propagation 控制 |
| 集中防火牆、跨 AZ 不對稱路由丟包 | Inspection VPC attachment 啟用 appliance mode |
| 跨 Region 連接兩個 TGW | TGW peering，使用 static route |
| 把服務提供給其他帳號／客戶，不暴露整個 VPC | PrivateLink endpoint service（NLB 前端） |
| Consumer 與 provider CIDR 重疊 | PrivateLink 或 VPC Lattice |
| 跨帳號微服務、以 IAM 身份授權、HTTP 路徑路由 | VPC Lattice + auth policy |
| 中央團隊管網路，應用團隊在共享 subnet 部署 | VPC sharing（AWS RAM） |
| 跨帳號共享 TGW | AWS RAM |
| TGW 上兩個 VPC 間流量很大、處理費高 | 加一條 VPC peering（同 AZ 免傳輸費、無處理費） |
| 跨 peering 的 EC2 public DNS 名稱要解析成 private IP | 雙方啟用 peering DNS resolution |

**常見陷阱**：

1. 「建兩條 peering 做備援」：兩個 VPC 間只能有一條，peering 本身沒有單點。
2. 「VPC 接上 TGW 後，VPC route table 會自動加 route」：不會，只有 TGW route table 有 propagation。
3. 「PrivateLink 讓 provider 也能主動連到 consumer」：PrivateLink 是單向的。
4. 「TGW peering 會自動交換兩邊的路由」：跨 TGW peering 要手動加 static route。
5. 「在每個 spoke VPC 啟用 appliance mode」：應該在 inspection（appliance）VPC 的 attachment 上啟用。
6. 「VPC peering 可以跨重疊的 CIDR，只要 route 寫得更精確」：只要 CIDR 重疊就無法建立 peering。

## 7.12 SAP 加深：大規模互連的設計取捨

### 從 mesh 遷移到 hub-and-spoke

很多公司像 Wanderly 一樣，從 peering 起步，在 VPC 數量增加後遷移到 TGW。遷移可以不停機進行：先把所有 VPC 接上 TGW 並設好 TGW route table，再在 VPC route table 中加入指向 TGW 的**較寬** route（例如 `10.0.0.0/8 → tgw`）；此時原本較精確的 peering route（例如 `10.16.0.0/16 → pcx`）依 longest prefix match 仍然優先。逐一驗證後刪除 peering route，流量就自然轉到 TGW，最後再刪除 peering。反過來，對大流量的 VPC 對保留 peering，就是 7.9 節的成本最佳化。

### 成本模型怎麼算

SAP 題目常要求「MOST cost-effective」的互連設計，要能粗略估算：

- **Peering**：只有資料傳輸費；同 AZ 免費。兩個 VPC 間每月數十 TB 的流量，用 peering 可省下全部 TGW 處理費。
- **TGW**：attachment 數 × 小時費，加上所有經過的流量 × 每 GB 處理費。集中 egress 或集中 inspection 架構中，同一份流量可能經過 TGW 兩次（spoke → inspection → 目的地），處理費也要算兩次。
- **PrivateLink**：每個 consumer endpoint × AZ 數 × 小時費，加每 GB 費用；provider 端還有 NLB。Consumer 數量大時，endpoint 小時費由 consumer 各自負擔。
- **VPC sharing**：同 VPC 內通訊沒有額外連線費，是減少 TGW attachment 與處理費的有效方式。

### 跨 Region 與全球網路

多 Region 架構（第 42 章）中，常見做法是每個 Region 一個 TGW，Region 之間用 TGW peering，並以 static route 指向對端 Region 的位址區塊（第 5 章 IPAM 為每個 Region 預留連續區塊，正好讓這些 static route 可以彙總成少數幾條）。當 Region 數量多、需要動態路由與集中政策時，**AWS Cloud WAN** 提供一個以 JSON **core network policy** 定義的全球網路：把網路分成多個 **segment**（例如 prod、dev），附加的 VPC 依 tag 自動加入對應 segment，路由在 Region 之間動態傳播。第 41 章會比較 TGW peering 與 Cloud WAN 的選擇。

### 多帳號治理

- TGW 由 network 帳號擁有並經 RAM 共享；可以設定 attachment 需要 owner 接受，避免任何帳號自行接上 TGW。
- TGW route table 的變更（association、propagation、static route）是 route leak 的主要來源，應該以 IaC 管理（第 37 章），並用 Network Access Analyzer（第 6 章）定期驗證「dev 無法到 prod」。
- **AWS Network Manager** 提供 TGW 與 Cloud WAN 的全球網路拓撲視圖與事件監控。
- Lattice 的 service 與 service network 以 RAM 跨帳號共享；PrivateLink 則以 endpoint service 的 allowed principals 控制誰能連。SCP 可以限制哪些帳號能建立 peering 或 TGW attachment（例如 deny `ec2:CreateVpcPeeringConnection`，強制所有互連走 TGW），讓網路拓撲維持在中央團隊的掌握之中。

### 跨帳號的 AZ ID

只要涉及「另一個帳號的 AZ」，就要用 AZ ID：PrivateLink 的 consumer endpoint 必須落在 provider NLB 有啟用的實體 AZ；VPC sharing 的 participant 看到的 AZ 名稱可能和 owner 不同；集中 inspection 架構中，要確保每個 spoke 使用的實體 AZ 都有防火牆。SAP 題目若出現「另一個帳號在 `us-east-1a` 建立 endpoint 失敗」，答案通常與 AZ ID 對應有關。

## 本章重點整理

- 互連先問「對方要碰到什麼」：整段網路用 peering／TGW，單一服務用 PrivateLink，應用層服務對服務與身份授權用 VPC Lattice，共用網路用 VPC sharing。
- VPC peering 是兩個 VPC 間的私有直連，可跨帳號、跨 Region；建立後雙方都要手動加 route，AWS 不會自動更新 route table。
- Peering 不遞移、CIDR 不能重疊、不能借用對方的 IGW／NAT／VPN／DX／gateway endpoint，兩個 VPC 間只能有一條。
- Peering 沒有小時費與處理費，同 AZ 流量免費，是兩個 VPC 間大量流量最便宜的連線方式。
- 同 Region peering 可參照對端 SG；跨 Region 只能用 CIDR；要讓 EC2 public DNS 名稱跨 peering 解析成 private IP，雙方都要啟用 DNS resolution 選項。
- Transit Gateway 是 Region 範圍的中央路由器，具遞移性，可連接 VPC、VPN、Direct Connect gateway 與其他 TGW，並可經 RAM 跨帳號共享。
- 每個 TGW attachment 只關聯一張 TGW route table（決定查哪張表），但可 propagate 到多張（決定出現在哪些表）；以此做 prod／dev／shared 的隔離。
- VPC 接上 TGW 後，VPC route table 仍要手動加指向 TGW 的 route；VPC attachment 要在每個有 workload 的 AZ 選 subnet。
- TGW peering 可跨 Region，只支援 static route；集中 inspection 架構要在 appliance VPC 的 attachment 啟用 appliance mode 以維持對稱路由。
- TGW 按 attachment 小時與每 GB 處理費計費；VPN attachment 的標準 tunnel 每條最高 1.25 Gbps，可用 BGP + ECMP 聚合多條 tunnel。
- PrivateLink endpoint service 以 NLB 為前端，透過 allowed principals 與 acceptance 控制誰能連；單向、可解決 CIDR 重疊；provider 要取得原始來源資訊需 Proxy Protocol v2。
- VPC Lattice 以 service network、service、listener／rules、target group 與兩層 auth policy 組成，可跨帳號、跨重疊 CIDR，並以 IAM 身份授權每個請求。
- VPC sharing 讓 owner 管理網路、participant 在共享 subnet 部署資源，減少 VPC 數量與互連成本。
- 跨帳號規劃 PrivateLink、VPC sharing 與 inspection 時，用 AZ ID 而不是 AZ 名稱溝通。

## 本章練習題

### 練習 7-1｜SAA｜單選｜Peering 建立後的路由

Wanderly 在同一個帳號中有 production VPC（`10.20.0.0/16`）與 shared services VPC（`10.16.0.0/16`）。工程師建立了 VPC peering 並已接受，狀態為 `active`，也在 production app subnet 的 route table 加入了 `10.16.0.0/16 → pcx-0abc`。Shared services 的 SG 允許來自 `10.20.0.0/16` 的 TCP 4317。但 production 的應用程式連日誌收集器時一律 timeout。

最可能缺少的設定是什麼？

- A. 第二條 peering 連線，用於回程流量
- B. Shared services 收集器所在 subnet 的 route table 中，`10.20.0.0/16 → pcx-0abc` 的 route
- C. 兩個 VPC 都要附加 Internet Gateway，peering 流量才能傳送
- D. 在 peering 連線上啟用 DNS resolution 選項

> [!answer]- 答案：B
> **A ✗** 兩個 VPC 之間只能有一條 peering，它本身就承載雙向流量，不需要另一條處理回程。
>
> **B ✓** Peering 不會自動修改任何 route table。去程有 route，但 shared services 那一側沒有回到 `10.20.0.0/16` 的 route，回應封包送不回來，結果就是 timeout。兩側都要加 route。
>
> **C ✗** Peering 流量走 AWS 內部網路，不需要 IGW。
>
> **D ✗** DNS resolution 選項只影響 EC2 public DNS 名稱解析成哪個 IP；題目是 IP 層的連線 timeout，與名稱解析無關。
>
> **考點**：SAA-3.4｜peering 雙向路由

### 練習 7-2｜SAA｜單選｜Peering 不遞移

Wanderly 的 VPC A（`10.1.0.0/16`）與 VPC B（`10.2.0.0/16`）之間有 peering，VPC B 與 VPC C（`10.3.0.0/16`）之間也有 peering。現在 VPC A 的一個批次工作需要存取 VPC C 中的資料庫。公司目前只有這三個 VPC，短期內沒有擴充計畫，希望用最低成本完成。

最合適的做法是什麼？

- A. 在 VPC A 的 route table 加入 `10.3.0.0/16 → A–B 的 peering`，並在 VPC B 開啟轉送功能
- B. 在 VPC B 部署一台 EC2 作為路由器，關閉 source/destination check 後轉送 A 與 C 之間的流量
- C. 建立 Transit Gateway，把三個 VPC 都接上並設定路由
- D. 建立 VPC A 與 VPC C 之間的 peering，並在兩側 route table 加入對方 CIDR 的 route

> [!answer]- 答案：D
> **A ✗** Peering 不具遞移性，VPC B 沒有「轉送功能」可以開啟；送到 B 的封包不會被轉往 C。
>
> **B ✗** 用自建 EC2 當路由器技術上可行，但它是單點故障、需要自己維運、頻寬受 instance 限制，維運成本高，也不是最佳實務。
>
> **C ✗** TGW 可以解決，但三個 VPC 的規模下，TGW 的 attachment 小時費與每 GB 處理費比 peering 貴，不是最低成本。
>
> **D ✓** Peering 只連接直接相連的兩端，A 要連 C 就需要 A–C peering。Peering 沒有小時費與處理費，在少量 VPC 時最便宜。
>
> **考點**：SAA-3.4、SAA-4.4｜peering 非遞移

### 練習 7-3｜SAA｜選兩項｜Peering active 但仍 timeout

兩個帳號的 VPC 之間已建立 active 的 peering。Consumer 端的應用程式用 private IP 連線對端的 PostgreSQL（TCP 5432），DNS 不是問題，但連線 timeout。兩側都使用 custom NACL。

最應該先檢查哪兩項？（選兩項）

- A. 兩側相關 subnet 的 route table 是否都有指向同一條 peering 的對方 CIDR route
- B. 是否在兩個 VPC 都附加了 Internet Gateway
- C. 資料庫 SG 是否允許實際來源（對端 CIDR，或同 Region 時對端的 SG），以及兩側 NACL 是否允許 5432 與 ephemeral ports 回程
- D. Peering 連線的頻寬上限是否已達到，需要升級 peering 規格
- E. 是否需要再建第二條 peering 分擔流量

> [!answer]- 答案：A、C
> **A ✓** Peering 不會自動加 route；任何一側缺少 route，去程或回程就會失敗。
>
> **B ✗** Peering 不經過 IGW，附加 IGW 與這條私有連線無關。
>
> **C ✓** 路由正確後，下一層是 SG 與 NACL。資料庫的 SG 要允許來源；兩側都是 custom NACL，stateless 的特性要求去程與 ephemeral ports 回程都要放行。
>
> **D ✗** Peering 不是設備，沒有可升級的規格或單一頻寬瓶頸。
>
> **E ✗** 兩個 VPC 之間只能有一條 peering。
>
> **考點**：SAA-3.4、SAA-1.2｜peering 除錯

### 練習 7-4｜SAA｜單選｜CIDR 重疊與 peering

Wanderly 的分析團隊在新帳號中建立了一個 VPC，CIDR 選了 `10.20.0.0/16`，和 production VPC 相同。他們需要從 production 的 read replica 定期抽取大量資料，嘗試建立 peering 時失敗。Production VPC 不能變更。分析 VPC 目前只有幾台測試機。

最合適的做法是什麼？

- A. 建立 peering 時，只選擇 production VPC 的部分 subnet 來避開衝突
- B. 在分析 VPC 中加入 secondary CIDR，再重新嘗試建立 peering
- C. 依公司 CIDR 規劃，以不重疊的 CIDR 重建分析 VPC 並遷移測試機，再建立 peering
- D. 把兩個 VPC 接到同一個 Transit Gateway，TGW 會自動處理重疊的位址

> [!answer]- 答案：C
> **A ✗** Peering 是 VPC 與 VPC 之間的連線，無法只選部分 subnet；只要 CIDR 重疊就無法建立。
>
> **B ✗** 加入 secondary CIDR 不會移除原本重疊的主要 CIDR，peering 仍然無法建立。
>
> **C ✓** 分析 VPC 才剛建立、資源很少，重新以不重疊的 CIDR 建立的代價最低，而且之後能用 peering 這種最便宜的方式搬移大量資料。這也是第 5 章強調先規劃 CIDR 的原因。
>
> **D ✗** TGW 無法在同一個路由域中正確路由兩個相同的 prefix，不會「自動處理」重疊。
>
> **考點**：SAA-3.4｜peering 不允許 CIDR 重疊

### 練習 7-5｜SAA｜單選｜不能借用對方的 NAT

為了節省成本，一位工程師打算讓 development VPC 的 private subnet 不建 NAT Gateway，而是經過已存在的 peering，使用 shared services VPC 裡的 NAT Gateway 存取 Internet。他在 development 的 route table 加入了 `0.0.0.0/0 → pcx-0devshared`，但 development 的 instance 仍然無法上網。

應如何解決？

- A. 在 shared services VPC 的 NAT Gateway 上加入 development VPC 的 CIDR 允許清單
- B. 在 shared services VPC 的 public subnet route table 加入 `10.25.0.0/16 → pcx-0devshared`
- C. 為 peering 啟用 DNS resolution，讓 NAT Gateway 能識別 development 的流量
- D. VPC peering 不支援經由對端的 NAT Gateway 或 IGW 上網；改為在 development VPC 自建 NAT Gateway，或以 Transit Gateway 搭配集中 egress VPC 設計

> [!answer]- 答案：D
> **A ✗** NAT Gateway 沒有來源允許清單的設定，問題也不在 NAT 本身，而在於 peering 不承載這類流量。
>
> **B ✗** 補回程 route 無法改變 peering 不支援 edge-to-edge routing 的限制。
>
> **C ✗** DNS resolution 只影響名稱解析，和是否能經對端 NAT 上網無關。
>
> **D ✓** Peering 不支援 edge-to-edge routing：不能經由對端 VPC 的 IGW、NAT Gateway、VPN 或 Direct Connect。要共用出口，標準做法是 TGW 搭配集中 egress VPC（第 41 章）；否則就在 development VPC 自己建 NAT Gateway。
>
> **考點**：SAA-3.4｜peering 不支援 edge-to-edge routing

### 練習 7-6｜SAA｜單選｜多 VPC 與地端的集中互連

Wanderly 預計一年內會有 25 個 VPC（分布在多個帳號，同一個 Region），全部都需要和台北辦公室（經 Site-to-Site VPN）互通，部分 VPC 之間也要互通。目前用 peering 管理已經很困難，團隊希望減少連線數量與路由維護工作。

最合適的做法是什麼？

- A. 建立 Transit Gateway，經 AWS RAM 共享給各帳號，把所有 VPC 與 VPN 接為 attachment，以 TGW route table 控制互通
- B. 繼續用 VPC peering 做全互連，並讓所有 VPC 經過其中一個 VPC 的 VPN 連到辦公室
- C. 在每個 VPC 各自建立一條到辦公室的 VPN，VPC 之間改用 PrivateLink
- D. 把 25 個 VPC 合併成一個 VPC

> [!answer]- 答案：A
> **A ✓** TGW 是具遞移性的中央路由器，每個網路只需要接一次；VPN 也可以直接接到 TGW，讓所有 VPC 共用。RAM 共享讓其他帳號能把自己的 VPC 接上，TGW route table 集中表達誰能連誰。
>
> **B ✗** 25 個 VPC 全互連需要 300 條 peering；而且 peering 不支援經由對端 VPC 的 VPN 連到地端（edge-to-edge）。
>
> **C ✗** 每個 VPC 各自建 VPN 會讓辦公室端要維護 25 組連線；PrivateLink 是服務層的單向連線，無法提供 VPC 間的任意互通。
>
> **D ✗** 合併 VPC 會失去帳號與環境之間的網路隔離，遷移成本也極高，不符合多帳號架構的目的。
>
> **考點**：SAA-3.4、SAA-2.1｜Transit Gateway hub-and-spoke

### 練習 7-7｜SAA｜單選｜把 API 提供給合作夥伴

一家連鎖飯店要從他們自己的 AWS 帳號私下呼叫 Wanderly 的房價 API（HTTPS），不能經過 Internet。雙方的 VPC 都使用 `10.20.0.0/16`。Wanderly 的安全團隊要求飯店只能碰到這個 API，不能存取 Wanderly VPC 中的其他資源，也不希望飯店能主動影響 Wanderly 的路由設定。

最合適的做法是什麼？

- A. 建立 VPC peering，在 Wanderly 的 SG 中只允許飯店的 CIDR 存取 API
- B. 把雙方 VPC 都接到 Wanderly 的 Transit Gateway，並在 TGW route table 只放 API 所在 subnet 的路由
- C. 在 Wanderly 端以 Network Load Balancer 為前端建立 endpoint service，把飯店帳號加入 allowed principals，由飯店在自己的 VPC 建立 interface endpoint
- D. 把 API 放到 public ALB 後面，只允許飯店 NAT Gateway 的 EIP 存取

> [!answer]- 答案：C
> **A ✗** CIDR 重疊時無法建立 peering；即使不重疊，peering 也會打通整段網路，安全性完全依賴 SG。
>
> **B ✗** 相同的 `10.20.0.0/16` 無法在 TGW 中正確路由，而且這等於把兩家公司的網路接在一起，超出需求。
>
> **C ✓** PrivateLink 只把一個服務的入口（endpoint ENI，使用飯店自己的 IP）放進飯店的 VPC，雙方 IP 從不互相路由，CIDR 重疊沒有影響；它是單向的，飯店只能呼叫這個服務。Allowed principals 控制誰能建立 endpoint。
>
> **D ✗** 走 public ALB 代表流量經過 Internet，違反需求；維護對方 EIP 允許清單也較脆弱。
>
> **考點**：SAA-1.2、SAA-3.4｜PrivateLink endpoint service

### 練習 7-8｜SAA｜單選｜跨帳號微服務與 IAM 授權

Wanderly 有 30 個以 HTTPS 溝通的微服務，分布在 6 個帳號的多個 VPC 中，部分 VPC 的 CIDR 互相重疊。平台團隊希望：服務之間以服務名稱呼叫；依 HTTP 路徑把請求轉到不同後端；並以呼叫者的 IAM role 決定能否呼叫某個服務。團隊不想為每組服務維護 NLB 與 interface endpoint。

最合適的服務是什麼？

- A. Transit Gateway，搭配每個服務的 SG 規則
- B. Amazon VPC Lattice，建立 service network 並把 VPC 關聯進來，以 listener rules 做路徑路由，並以 auth policy 依 IAM 身份授權
- C. 每個服務都建立 PrivateLink endpoint service，consumer 為每個依賴建立 interface endpoint
- D. 全部 VPC 之間建立 peering，並在每個服務前面放一個 ALB

> [!answer]- 答案：B
> **A ✗** TGW 是網路層互連，無法處理重疊 CIDR，也無法依 HTTP 路徑或 IAM 身份授權。
>
> **B ✓** VPC Lattice 以服務名稱連接、支援 HTTP 路徑等 rules 路由、以 auth policy 依 IAM 身份授權每個請求，而且可跨帳號、跨重疊 CIDR，不需要 peering、TGW 或每服務一個 NLB。
>
> **C ✗** PrivateLink 可解決重疊，但每個服務一個 NLB、每個 consumer 每個依賴一個 endpoint，數量龐大；它是 L4，無法依路徑路由或依 IAM 身份授權。
>
> **D ✗** Peering 無法連接重疊的 CIDR，全互連的數量也難以管理；ALB 本身不提供跨帳號的 IAM 身份授權。
>
> **考點**：SAA-2.1、SAA-1.2｜VPC Lattice 服務網路

### 練習 7-9｜SAP｜單選｜TGW 環境隔離

Wanderly 用一個 Transit Gateway 連接 40 個 production VPC、30 個 development VPC、一個 shared services VPC，以及一條到資料中心的 VPN。需求是：production 與 development 之間不能互通；兩者都要能到 shared services 與資料中心；新的 VPC 加入時要容易套用。

最合適的 TGW 路由設計是什麼？

- A. 所有 attachment 關聯同一張 TGW route table 並全部 propagate，再用每個 VPC 的 SG 擋住 prod 與 dev 之間的流量
- B. 建立 prod、dev、shared、VPN 四張 TGW route table；prod attachment 關聯 RT-prod，並把路由 propagate 到 RT-shared 與 RT-VPN；dev 同理；shared 與 VPN 的路由 propagate 到 RT-prod、RT-dev 與彼此的表
- C. 建立兩個 Transit Gateway，一個給 prod、一個給 dev，再用 VPC peering 把 shared services 接到兩邊
- D. 所有 attachment 關聯同一張 TGW route table 並全部 propagate；在每個 development VPC 的 route table 只加入 shared services 與資料中心 CIDR 指向 TGW 的 route，不加入 production 的 CIDR

> [!answer]- 答案：B
> **A ✗** 單一全互通路由表會讓 prod 與 dev 互相學到路由，隔離完全依賴數十個帳號的 SG 都寫對，風險高且難以稽核。
>
> **B ✓** Association 決定 attachment 的流量查哪張表，propagation 決定誰的路由出現在哪張表。RT-prod 裡沒有 dev 的路由、RT-dev 裡沒有 prod 的路由，隔離在路由層成立；shared 與 VPN 出現在兩邊的表中，所以兩邊都能到達。新 VPC 只要依環境關聯與 propagate 即可。
>
> **C ✗** 兩個 TGW 增加成本與管理負擔，而且資料中心的 VPN 也要接兩次；用 peering 接 shared services 不具遞移性，難以擴展。
>
> **D ✗** 隔離只靠 30 個 dev VPC 的 route table「不要寫錯」：TGW route table 中 prod 與 dev 的路由仍然互相存在，只要任何一個 VPC 加了一條較寬的 route（例如 `10.0.0.0/8 → tgw`），或 prod VPC 本身用了寬 route，就能互通，難以稽核，新 VPC 加入時也容易出錯。正確做法是在 TGW route table 層級控制。
>
> **考點**：SAP-1.1、SAP-1.4｜TGW association／propagation segmentation

### 練習 7-10｜SAP｜單選｜集中 inspection 的不對稱路由

Wanderly 讓所有 VPC 之間的流量都經 TGW 送到 inspection VPC 中的 stateful 防火牆設備，防火牆分布在三個 AZ。上線後發現：同 AZ 內的 VPC 互連正常，但來源與目的在不同 AZ 時，部分連線會隨機失敗，防火牆日誌顯示丟棄了「沒有對應連線狀態」的回程封包。

應如何修正？

- A. 在 inspection VPC 的 TGW attachment 啟用 appliance mode
- B. 在每個 spoke VPC 的 TGW attachment 啟用 appliance mode
- C. 把防火牆改成只部署在一個 AZ，所有流量都送到那個 AZ
- D. 在 inspection VPC 中加入 NAT Gateway，讓回程流量經過 NAT 轉換

> [!answer]- 答案：A
> **A ✓** TGW 預設讓流量留在來源 AZ，跨 AZ 的去程與回程可能進入不同 AZ 的防火牆。在 appliance VPC 的 attachment 啟用 appliance mode 後，TGW 會為同一條連線選定一個 AZ，雙向流量都送到同一台防火牆，stateful 檢查才能運作。
>
> **B ✗** Appliance mode 要在連接防火牆的 inspection VPC attachment 上啟用；在 spoke 上啟用無法讓進入 inspection VPC 的雙向流量維持在同一個 AZ。
>
> **C ✗** 只用一個 AZ 可以「消除」不對稱，但防火牆變成單一 AZ 的故障點，違反高可用設計，也增加跨 AZ 流量費。
>
> **D ✗** NAT 會改變位址，但不能保證 TGW 把回程送到同一個 AZ 的防火牆，也會讓目的端看不到原始來源。
>
> **考點**：SAP-1.1、SAP-1.3｜TGW appliance mode

### 練習 7-11｜SAP｜單選｜TGW 大流量的成本最佳化

Wanderly 有 60 個 VPC 透過 Transit Gateway 互連。成本分析顯示，TGW 的資料處理費大部分來自 production VPC 與 data VPC 之間每月數百 TB 的資料搬移；兩個 VPC 位於同一個 Region、CIDR 不重疊、資源分布在相同的 AZ。其他 VPC 之間流量很小。公司希望在不影響其他 VPC 互連的前提下大幅降低成本。

最合適的做法是什麼？

- A. 把所有 VPC 從 TGW 改回全互連的 VPC peering
- B. 在 production 與 data VPC 之間建立 PrivateLink endpoint service，讓 data VPC 經 interface endpoint 讀取資料
- C. 把 data VPC 移到另一個 Region，改用 TGW peering 降低費用
- D. 保留 TGW，另外在 production 與 data VPC 之間建立 VPC peering，並在兩側 route table 加入對方 CIDR 指向 peering 的 route

> [!answer]- 答案：D
> **A ✗** 60 個 VPC 全互連需要 1,770 條 peering，每個 VPC 要 59 條，已超過預設 quota（50），管理負擔極大；其他 VPC 流量很小，沒有必要全部改。
>
> **B ✗** PrivateLink 有 endpoint 小時費與每 GB 費用，而且是單向的服務層連線，不適合兩個 VPC 間任意方向的大量資料搬移。
>
> **C ✗** 跨 Region 流量會產生跨 Region 傳輸費，也增加延遲，只會更貴。
>
> **D ✓** Peering 沒有資料處理費，同 AZ 內流量免傳輸費。VPC route table 中對方 VPC 的 /16 route 比指向 TGW 的寬 route（例如 /8）更精確，依 longest prefix match 會優先走 peering，其他 VPC 仍經 TGW。
>
> **考點**：SAP-1.5、SAP-3.5｜TGW 與 peering 並用的成本最佳化

### 練習 7-12｜SAP｜單選｜PrivateLink 與 AZ ID

Wanderly 透過 PrivateLink 提供一個 endpoint service，背後的 NLB 只啟用了 `ap-northeast-1a` 與 `ap-northeast-1c`（Wanderly 帳號中的 AZ 名稱）。一個客戶嘗試在他們帳號的 `ap-northeast-1a` 與 `ap-northeast-1c` 建立 interface endpoint，但系統提示其中一個 AZ 不受此服務支援。

最可能的原因與最佳修正是什麼？

- A. 客戶帳號尚未被加入 allowed principals，加入後即可在任何 AZ 建立
- B. AZ 名稱在不同帳號中可能對應到不同的實體 AZ；provider 應以 AZ ID 確認對應，並讓 NLB 啟用該 Region 的所有 AZ
- C. Interface endpoint 只能建在一個 AZ，客戶應刪除其中一個 subnet
- D. Endpoint service 需要開啟 acceptance required，才能支援多個 AZ

> [!answer]- 答案：B
> **A ✗** 若不在 allowed principals 中，客戶根本無法對這個服務建立 endpoint，而不是只有某個 AZ 不支援。
>
> **B ✓** AWS 會在不同帳號間把 AZ 名稱對應到不同的實體 AZ。Consumer endpoint 只能建在 provider NLB 有啟用的實體 AZ。用 AZ ID（例如 `apne1-az1`）溝通才能確認對應；讓 NLB 涵蓋所有 AZ 是 provider 最穩健的做法。
>
> **C ✗** Interface endpoint 可以（也應該）在多個 AZ 建立 ENI 以達到高可用。
>
> **D ✗** Acceptance required 控制連線請求是否需要人工接受，與 AZ 支援範圍無關。
>
> **考點**：SAP-1.1、SAP-1.3｜PrivateLink AZ ID 對應

### 練習 7-13｜SAP｜單選｜PrivateLink provider 識別客戶

Wanderly 以 PrivateLink 提供 API 給 200 個企業客戶，每個客戶從自己的 VPC 經 interface endpoint 連線。後端服務需要依「是哪個客戶的 endpoint 發出的請求」做計費與速率限制，但目前應用程式看到的來源 IP 都是 NLB 的 private IP，而且不同客戶的 VPC 位址可能相同。

最合適的做法是什麼？

- A. 要求每個客戶使用不重疊的 CIDR，後端依來源 IP 判斷客戶
- B. 改用 VPC peering 連接每個客戶，後端直接看到客戶的真實 IP
- C. 在 NLB 的 target group 啟用 Proxy Protocol v2，讓後端從連線標頭讀取原始來源資訊與 VPC endpoint ID，依 endpoint ID 對應客戶
- D. 為每個客戶建立一個獨立的 endpoint service 與 NLB，後端依 NLB 判斷客戶

> [!answer]- 答案：C
> **A ✗** 經 PrivateLink 時後端看到的是 NLB 的位址，客戶 CIDR 是否重疊都看不到；要求 200 個客戶改 CIDR 也不切實際。
>
> **B ✗** 200 條 peering 管理困難，客戶 CIDR 可能重疊而無法建立，也會把網路完全打通，違背使用 PrivateLink 的初衷。
>
> **C ✓** Proxy Protocol v2 會在每條 TCP 連線開頭附上原始來源位址，以及 PrivateLink 的 VPC endpoint ID。Endpoint ID 對每個客戶唯一，即使客戶 IP 重疊也能準確識別。後端應用程式（或 proxy）需支援解析 Proxy Protocol。
>
> **D ✗** 可行但每個客戶一套 NLB 與 endpoint service，成本與營運負擔隨客戶數線性增加，不是最佳做法。
>
> **考點**：SAP-2.5、SAP-1.1｜PrivateLink Proxy Protocol v2

### 練習 7-14｜SAA｜單選｜跨 Region peering 的 SG 規則

Wanderly 在東京與新加坡各有一個 VPC，以跨 Region VPC peering 相連，路由已設好。新加坡的資料庫 SG 想用「來源為東京 VPC 中的 SG-app」的規則授權，但設定時無法選取該 SG。團隊希望只允許東京的應用程式 tier 連線。

最合適的做法是什麼？

- A. 跨 Region peering 不支援參照對端 SG；改用東京應用程式 subnet 的 CIDR 作為來源，並讓這些 subnet 只放應用程式 tier
- B. 在 peering 選項中啟用 DNS resolution，就能參照對端 SG
- C. 把東京的 SG-app 複製到新加坡 VPC，再在資料庫 SG 中參照副本
- D. 改用 NACL 並在規則中填入東京 SG-app 的 ID

> [!answer]- 答案：A
> **A ✓** SG 參照對端 SG 只支援同 Region 的 peering。跨 Region 時只能用 CIDR，所以要讓應用程式 tier 位於專用 subnet，以 subnet CIDR 表達「只有應用程式 tier」。
>
> **B ✗** DNS resolution 選項只影響名稱解析，與 SG 參照能力無關。
>
> **C ✗** SG 是 VPC 範圍的資源，複製出的新 SG 是新加坡 VPC 中的另一個 SG，東京的 instance 並沒有掛它，參照副本沒有意義。
>
> **D ✗** NACL 規則只能使用 CIDR，不能引用任何 SG。
>
> **考點**：SAA-1.2、SAA-3.4｜跨 Region peering 的 SG 限制

### 練習 7-15｜SAP｜選兩項｜跨 Region TGW 互連

Wanderly 在東京（`10.16.0.0/12`）與新加坡（`10.32.0.0/12`）各有一個 Transit Gateway，各自連接數十個 VPC。現在兩個 Region 的部分 VPC 需要互相存取，並要求流量走 AWS 骨幹、不經 Internet，維運盡量簡單。

哪兩個步驟是正確的？（選兩項）

- A. 在兩個 TGW 之間建立 TGW peering attachment，並由對方接受
- B. 在兩個 Region 的每對 VPC 之間建立跨 Region VPC peering
- C. 在東京相關的 TGW route table 加入 `10.32.0.0/12 → peering attachment` 的 static route，新加坡端加入 `10.16.0.0/12` 的 static route
- D. 在 TGW peering attachment 上啟用 propagation，讓兩邊自動交換路由
- E. 在兩個 Region 之間建立 Site-to-Site VPN，接到兩個 TGW

> [!answer]- 答案：A、C
> **A ✓** TGW peering attachment 可以連接不同 Region（也可跨帳號）的兩個 TGW，流量走 AWS 骨幹並加密。
>
> **B ✗** 每對 VPC 都建 peering 數量龐大，而且失去 TGW 集中路由的好處，維運不簡單。
>
> **C ✓** TGW peering 只支援 static route，兩邊都要手動把對方 Region 的位址區塊指向 peering attachment。每個 Region 使用連續且不重疊的位址區塊（如第 5 章的 IPAM 規劃），讓這些 static route 可以彙總成一條。
>
> **D ✗** TGW peering attachment 不支援動態 propagation；需要跨 Region 動態路由時，應考慮 AWS Cloud WAN。
>
> **E ✗** Site-to-Site VPN 的另一端必須是客戶自己的 customer gateway 設備，兩個 TGW 之間不能直接互建 VPN；即使在中間自建 VPN 設備，流量也會走 public IP、受 tunnel 頻寬限制，還要自己維運設備，不符合「走 AWS 骨幹、維運簡單」。
>
> **考點**：SAP-1.1｜TGW 跨 Region peering 與 static route

### 練習 7-16｜SAP｜選兩項｜集中管理網路的多帳號設計

Wanderly 有 15 個應用團隊帳號。網路團隊希望：(1) 集中管理 production 網路的 subnet、route table、NAT 與 TGW 連線，應用團隊不能修改；(2) 應用團隊可以在 production 網路中部署並管理自己的 EC2、RDS 與 SG；(3) 所有網路互連都必須經過中央 TGW，應用團隊不能自行建立 VPC peering。

哪兩個做法最能滿足需求？（選兩項）

- A. 由 network 帳號建立 production VPC，透過 AWS RAM 把 subnet 共享給各應用帳號（VPC sharing）
- B. 每個應用帳號各自建立 VPC，再由網路團隊用 VPC peering 把它們全互連
- C. 把所有應用團隊的 IAM user 建立在 network 帳號中，讓他們直接在 network 帳號部署資源
- D. 以 SCP 拒絕應用帳號呼叫 `ec2:CreateVpcPeeringConnection` 等互連相關 API
- E. 在每個應用帳號的 VPC 中，用 NACL 拒絕所有非 TGW 的流量

> [!answer]- 答案：A、D
> **A ✓** VPC sharing 讓 owner（network 帳號）管理 subnet、route table、NAT 與 TGW attachment，participant 只能在共享 subnet 中建立與管理自己的資源（含 SG），正好滿足 (1) 與 (2)。
>
> **B ✗** 每個帳號自建 VPC 會讓網路分散管理，不符合 (1)；全互連 peering 也違反 (3)。
>
> **C ✗** 把所有團隊放進同一個帳號，失去帳號層級的權限、帳單與故障隔離，也讓應用團隊能接觸網路設定。
>
> **D ✓** SCP 可以在組織層級拒絕建立 peering 等 API，強制所有互連走中央 TGW，滿足 (3)。SCP 不授予權限，只設定上限，不影響應用團隊的其他操作。
>
> **E ✗** NACL 是依 IP 過濾的網路控制，無法阻止建立 peering 這類 API 操作；而且在 VPC sharing 下，NACL 屬於 owner 管理的資源。
>
> **考點**：SAP-1.4、SAP-1.2｜VPC sharing 與 SCP 治理
