# P01 Audit：第 11–20 章 Networking 題庫與考點覆蓋

稽核日期：2026-10-01

範圍：`aws_architect_topics_01.py`、`aws_architect_profiles.py`、`aws_architect_setting_guides.py`、`aws_architect_deep_content.py`、`aws_architect_topic_factory.py`、`aws_architect_model.py` 與目前產生的 `aws-solutions-architect-saa-sap.html`。
限制：只設計原創情境與題目意圖，不使用或改寫 exam dumps。

## 總結判定

目前第 11–20 章每章只有 5 題，而且全數由同一組「選型／設定清單／機制辨識／最少營運負擔／企業治理」模板產生。題數雖然是 50 題，實際上可區分的推理形狀遠少於 50；Q2 與 Q4 經常只是同一份 `profile.config` 換句話說，Q1 與 Q5 也常直接重複 `topic.decision`。模板還固定插入「managed service 自動理解需求」「建立成功即保證 data plane」「全部部署」「給 AdministratorAccess」等顯然錯誤選項，無法模擬正式考試中彼此都技術可行、只因限制條件不同而分出優劣的干擾項。

更嚴重的是，題目常先提出跨多個元件的綜合需求，後面卻硬把 `components(topic)[0]` 當唯一主角，因此產生章內矛盾。例如第 15 章情境應用 PrivateLink，第 4 題卻選 Peering；第 17 章情境同時需要 CloudFront 與 Global Accelerator，第 4 題只選 CloudFront；第 20 章情境同時需要 Resolver、TGW 與 inspection，第 4 題只選 Resolver。這些題目不能只增加數量，必須改為「一題只驗證一個主要決策」，並以具體 packet/query path、設定值與故障症狀作答。

## Source-key 修正需求

現有章節大多只掛上廣泛的 `network`，不足以審核細節。下列既有 key 可直接使用：

- `saa-d2`、`saa-d3`、`saa-d4`：SAA-C03 官方 domain。
- `sap-d1`、`sap-d2`：SAP-C02 官方 domain。
- `network`：Amazon VPC User Guide。
- `vpc-route-tables`、`vpc-public-private-example`、`vpc-cli-example`：第 12 章既有官方細分來源。
- `route53`：Amazon Route 53 Developer Guide；目前第 16 章尚未掛入。
- `cloudfront`：Amazon CloudFront Developer Guide；目前第 17 章尚未掛入。

實作題庫前應在 `SOURCES` 新增下列官方產品文件 key，否則「有來源 key」仍只是指向過大的 VPC 首頁：

- `vpc-ipam`：VPC IP Address Manager。
- `vpc-nat-zonal`、`vpc-nat-regional`：Zonal NAT Gateway 與 Regional NAT Gateway。
- `vpc-endpoints`、`privatelink`：Gateway/interface endpoints 與 endpoint services。
- `vpc-security`：Security groups、network ACLs 與 ephemeral ports。
- `vpc-peering`、`transit-gateway`：Peering 與 TGW routing。
- `global-accelerator`：AWS Global Accelerator。
- `elb-alb`、`elb-nlb`、`elb-gwlb`：三種 load balancer。
- `site-to-site-vpn`、`direct-connect`、`direct-connect-resiliency`：Hybrid connectivity 與 resiliency models。
- `route53-resolver`：Inbound/outbound endpoints、rules 與 hybrid DNS。
- `network-firewall`、`tgw-centralized-inspection`：Network Firewall 與對稱 inspection path。

以下每個 intent 的「來源」欄使用上述既有或待新增的官方 key；不得以 community key 作為正確性唯一依據。

---

## 第 11 章：VPC 與 CIDR 規劃

### 現有題目問題

- Q1 正解是「用 IPAM 集中追蹤」，但 Q4 又把「選 Amazon VPC 並設定一般 VPC 欄位」當正解；兩題對同一組織級問題給出不同主角。
- Q2 只是比較兩份設定名詞清單，沒有提供 account、Region、pool、locale、可用位址或成長限制，無法驗證讀者真的會規劃地址。
- Q3 問 CIDR/IPAM 章的底層機制，正解卻是一般 VPC packet path；沒有考 prefix arithmetic、overlap 或 allocation。
- Q5 的 canary、rollback 與 business metric 是通用 deployment 模板，和 CIDR 委派、allocation compliance、併購重疊處理關聯很弱。
- 現有題庫完全沒有要求讀者由實際 CIDR 算 subnet、判斷 overlap、預留成長、讀 IPAM pool hierarchy 或處理已重疊網路。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 11.1 | 給定 `10.20.0.0/16`、每 AZ 三個 tier、每 tier 預估 2,000 個 ENI，選擇可容納成長且不互相重疊的 subnet plan。 | 先以所需位址數與成長係數決定 prefix，再跨 AZ 配置不重疊 subnet；不能只依名稱或目前 instance 數量切割。 | 所有 tier 共用一個 `/16`；每個 tier 一律 `/28`；以 SG 數量決定 CIDR。 | SAA | `SAA-3.4 · network` |
| 11.2 | 比較 `10.0.0.0/16`、`10.0.128.0/17`、`10.1.0.0/16`，判斷哪些 ranges overlap，哪些可直接經 Peering/TGW 路由。 | Routing 需要目的 prefix 唯一；子集合 CIDR 仍屬重疊，不能因 prefix 長度不同就視為獨立。 | NAT Gateway 自動解決任意重疊；SG 可消除 route ambiguity；只要帳號不同就可重疊互連。 | SAA | `SAA-3.4 · network` |
| 11.3 | 五十個 accounts、三個 Regions、on-prem 已使用部分 RFC1918 空間，設計 IPAM top-level/child pools 與 delegated allocation。 | 以 organization/Region/environment 建階層 pool，在配置前排除 on-prem ranges，讓 account vending 從核准 pool 自動取得 CIDR。 | 每個帳號自行選 `10.0.0.0/16`；只用 resource tags 發現衝突；先建立 VPC 再人工登記。 | SAP | `SAP-1.1 · vpc-ipam` |
| 11.4 | 新 workload 需要在單一 Region 配置 CIDR；判斷 IPAM pool 的 locale 應如何設定。 | Regional VPC resource allocation 必須由 locale 與目標 Region 相符的 pool 提供；locale 不是資料複寫或使用者所在地。 | locale 設成公司總部；所有 child pools 任意跨 Region 配置；用 Route 53 latency policy取代 locale。 | SAP | `SAP-1.1 · vpc-ipam` |
| 11.5 | 要求 development VPC 只能取得 `/24` 到 `/20`，且不得使用未核准範圍；選擇 IPAM allocation rules/compliance 設計。 | 用 pool allocation rules約束 netmask與資源配置，並監控 compliant/noncompliant allocations；IPAM 不會替代 VPC route。 | 用 NACL 限制 prefix 長度；用 SCP 直接計算可用 IP；只靠 Name tag。 | SAP | `SAP-1.1 · vpc-ipam` |
| 11.6 | VPC 已接近地址耗盡，需增加 app subnets，但未來仍要連接資料中心；比較 secondary CIDR、重建 VPC 與擴大既有 subnet。 | 先確認新 CIDR 與所有已連網範圍不重疊，再關聯 secondary CIDR並建立新 subnets；既有 subnet 不能任意改大。 | 直接修改既有 subnet CIDR；新增相同 CIDR 的 secondary block；以 NAT 增加 private IP 容量。 | SAA | `SAA-3.4 · network` |
| 11.7 | 雙棧 workload 要規劃 IPv4/IPv6；判斷 IPv6 prefix 與 subnet 分配不能沿用哪些 IPv4 假設。 | IPv6 使用可路由位址與不同 egress 模型；仍須規劃 subnet prefix、route 與 SG/NACL，不能假設 NAT Gateway 是必要隱私邊界。 | IPv6 一定經 IPv4 NAT Gateway；IPv6 不需 route table；IPv6 自動繞過 SG。 | SAA | `SAA-3.4 · network` |
| 11.8 | 併購後兩個大型網路 CIDR 重疊，短期只需讓 consumer 呼叫一個 API。 | 無法立即 renumber 時，以 PrivateLink/application proxy 暴露最小服務面；不要建立完整雙向 routed network。 | 直接建立 VPC Peering；在 TGW 同時發布兩個相同 prefix；只調高 route priority。 | SAP | `SAP-1.1 · privatelink` |
| 11.9 | 比較「很大的 VPC CIDR」與「多個可治理的環境 pool」在成本與未來連線上的取捨。 | 地址空間是有限架構資源；依成長、隔離、併購與 hybrid 預留，避免過度配置造成後續可路由空間不足。 | VPC CIDR 大小直接產生固定月費；最大的 CIDR 永遠最佳；以更多 route tables 回收浪費地址。 | SAA | `SAA-4.4 · network` |
| 11.10 | IPAM 顯示 utilization 接近門檻，要求提出不破壞現有連線的改善順序。 | 先找 abandoned allocations/ENI 與不合理 subnet sizing，再規劃 secondary CIDR或新 VPC migration；用監控提早處理而非耗盡後重編址。 | 刪除 local route；縮小運行中的 subnet；讓多個 subnet 共用同一 CIDR。 | SAP | `SAP-1.1 · vpc-ipam` |

---

## 第 12 章：Subnet、Route Table 與 Internet Gateway

### 現有題目問題

- Q1 的 A 與 B 都是正確敘述；題幹沒說 private app 是否需要 Internet egress，因此無法判斷是否需要 NAT。
- Q2 問「最直接決定本章流量」卻把完整 VPC 設定清單判為正解、把 IGW/route/public IP 清單判錯，和題名及情境不一致。
- Q3 的 VPC path 與 IGW 一對一 IPv4 NAT 都是事實，只因題目預先指定 Amazon VPC 才勉強單選；並未測一個實際 packet。
- Q4 重複 Q2，仍沒有 route table rows、association、longest-prefix match、public IPv4 或 return path。
- Q5 的跨帳號 canary/rollback 不像 subnet/route 題；應改測 centralized network ownership、route change blast radius與 Reachability Analyzer/Flow Logs。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 12.1 | 給定 public route table：`10.20.0.0/16→local`、`0.0.0.0/0→igw`，EC2 有 public IPv4、SG 開 443；追蹤 Internet client 到 EC2 的完整 path。 | Public IPv4、subnet 到 IGW 的 route、IGW attachment、SG/NACL 去回程都要成立；「subnet 名稱」不參與判斷。 | 只有 public IPv4 即可；只有 IGW attachment 即可；NAT Gateway 接收入站。 | SAA | `SAA-3.4 · vpc-route-tables` |
| 12.2 | 同一 public subnet 中 EC2 沒有 public IPv4，問它能否直接經 IGW 上網。 | IPv4 經 IGW 通訊時 instance/ENI 仍需 public IPv4/EIP；route 到 IGW 本身不會替 instance 配地址。 | IGW 自動 SNAT 所有 private IP；public subnet 名稱會分配地址；SG outbound allow 會建立 public address。 | SAA | `SAA-3.4 · vpc-public-private-example` |
| 12.3 | Private app route table 的 default 指向 NAT，DB route table只有 local；判斷 app update、Internet 入站與 app→DB 三條路徑。 | App 可主動經 NAT 出站；Internet 不能藉 NAT主動進入；app→DB 使用更精確的 VPC local route，不經 NAT。 | 所有流量因 default route 都經 NAT；DB 無 default route所以 app 也無法連；NAT 可替代 ALB 入站。 | SAA | `SAA-2.2 · vpc-public-private-example` |
| 12.4 | Route table 同時有 `0.0.0.0/0→NAT`、`10.40.0.0/16→TGW`、`10.40.8.0/24→Peering`；目的 `10.40.8.25` 選哪一跳。 | 採 longest-prefix match，`/24` 優先於 `/16` 與 default；route 順序不是依建立時間。 | default route 永遠先；static route 永遠勝 propagated route不看 prefix；最早建立的 route 優先。 | SAA | `SAA-3.4 · vpc-route-tables` |
| 12.5 | 新 route table 建立後未明確 association，實例使用哪張表。 | 每個 subnet 必須關聯一張 route table；未明確關聯時使用 VPC main route table，因此 main table 變更可能有廣泛 blast radius。 | 自動使用名稱相近的 table；同時合併所有 tables；沒有 association 就完全沒有 local route。 | SAA | `SAA-2.2 · vpc-route-tables` |
| 12.6 | Public ALB 跨兩個 AZ，只有 AZ A public subnet route 到 IGW；問可用性與修正。 | Internet-facing ALB 使用的每個 subnet/AZ 都要有正確 public path；為每個 AZ 建立/關聯正確 public route table。 | ALB 自動修正 subnet route；只需 ALB SG；讓 AZ B 經 AZ A NAT。 | SAA | `SAA-2.2 · vpc-public-private-example` |
| 12.7 | IPv6 private workload 只允許主動出站，不接受 Internet 主動入站，選擇 route target。 | 使用 egress-only Internet Gateway 與 `::/0` route；它和 IPv4 NAT Gateway、一般 IGW 的語意不同。 | IPv6 經 NAT Gateway；一般 IGW 加 public IPv6 仍自動阻止入站；刪除 SG outbound。 | SAA | `SAA-1.2 · network` |
| 12.8 | Route 顯示 `blackhole`，Flow Logs無回應；判斷最可能原因。 | Target resource/attachment 已刪除或不可用時 route 可成為 blackhole；修復 next hop 而不是只改 SG。 | DNS TTL 太高；ALB stickiness；IAM explicit deny。 | SAA | `SAA-2.2 · vpc-route-tables` |
| 12.9 | 中央網路帳號要變更數百個 spoke 的 default route，要求降低 production blast radius。 | 版本化 IaC、先在 canary subnet/VPC 驗證雙向 path，再分波變更；監控 Flow Logs/Reachability Analyzer並保留 rollback route。 | 一次改 main route table；先關閉全部 NACL；只看 CloudFormation CREATE_COMPLETE。 | SAP | `SAP-1.1 · vpc-route-tables` |
| 12.10 | App 連 DB timeout，DNS已解析、SG也允許；去程 route經 TGW，回程仍指向舊 Peering。 | Stateful connection仍需要網路設備可見的對稱/有效 return path；逐 hop檢查目的 prefix與回程，而非只看 ingress SG。 | 增加 DNS TTL；配置 public IP；調高 ALB idle timeout。 | SAP | `SAP-1.3 · network` |

---

## 第 13 章：NAT Gateway、Egress 與 VPC Endpoints

### 現有題目問題

- Q1 正確要求 S3 優先走 endpoint、一般 Internet 才走 NAT；Q4 卻直接選 NAT Gateway，章內答案互相矛盾。
- Q2 只列設定名詞，沒有問 public/private NAT、zonal/regional、route target、endpoint DNS、endpoint policy 或 cost path。
- Q3 只測一句 SNAT 定義，沒有檢查 NAT 必須搭配正確 upstream route、return connection state與 port exhaustion。
- 「一般 IPv4 internet egress再使用每 AZ NAT」目前不能再寫成無條件真理。現行產品已有 Regional NAT Gateway；教材須依 exam version 明確區分 zonal public/private NAT Gateway 與 Regional NAT Gateway，不可把過往最佳實務硬編成服務限制。
- 本章沒有任何 deployable config，卻是最需要 route table、gateway endpoint policy、interface endpoint SG/private DNS 與成本比較的章節之一。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 13.1 | Private EC2 大量讀同 Region S3、偶爾下載外部套件；選兩條 route。 | S3 用 gateway endpoint並以 prefix-list route/endpoint policy控管；外部 IPv4 才走 NAT，避免 S3 bytes 經 NAT。 | 所有流量走 NAT；S3 用 Peering；把 EC2 配 public IP。 | SAA | `SAA-4.4 · vpc-endpoints` |
| 13.2 | 追蹤 private EC2 `10.0.1.10` 經 zonal public NAT/EIP 到套件網站的去回程。 | Private route 指 NAT；NAT 所在 public subnet route指 IGW；NAT保存 translation state，Internet不能主動建立到 EC2 的 flow。 | NAT 放 private subnet即可；private route直接指 IGW；網站回覆直接送 private IP。 | SAA | `SAA-3.4 · vpc-nat-zonal` |
| 13.3 | 兩個 AZ 共用 AZ A 的 zonal NAT，AZ A 故障後 AZ B 也失去 egress；選擇改善。 | 若使用 zonal NAT，為每 AZ 建 NAT並讓 private subnet走同 AZ NAT，以隔離 AZ failure與避免不必要 cross-AZ path。 | 只增加一個 EIP；開啟 cross-zone；讓 route 指 ALB。 | SAA | `SAA-2.2 · vpc-nat-zonal` |
| 13.4 | 現行架構評估 Regional NAT Gateway；判斷何時可用它簡化跨 AZ resiliency，並要求標記 exam-version。 | Regional NAT 是不同型別與設計選項；依最新官方文件、Region可用性、路由與費用驗證，不應把 zonal NAT 規則直接套用。 | Regional NAT等同多個 EIP 的別名；任何舊考綱都必然測它；它可接 Internet unsolicited inbound。 | SAP／current-service extension | `SAP-1.1 · vpc-nat-regional` |
| 13.5 | EC2 要私下呼叫 SSM/Secrets Manager，問 interface endpoint 的 subnet、SG 與 private DNS。 | Interface endpoint在所選 subnets建立 ENI；endpoint SG允許 client進入服務 port；private DNS讓標準服務 hostname解析到 private IP。 | Gateway endpoint支援所有 AWS服務；endpoint不需要 SG；private DNS會建立 IAM permission。 | SAA | `SAA-1.2 · vpc-endpoints` |
| 13.6 | 比較 S3 gateway endpoint與 S3 interface endpoint 的用途及 cost/route模型。 | Gateway endpoint以 route table/prefix list運作且服務範圍有限；interface endpoint以 PrivateLink ENI/DNS運作，適用不同 hybrid/拓撲需求。 | 兩者都是 NAT；gateway endpoint需要 ENI SG；interface endpoint自動公開整個 VPC。 | SAP | `SAP-1.1 · vpc-endpoints` |
| 13.7 | Endpoint policy只允許 approved bucket，但 EC2 role沒有 `s3:GetObject`；判斷結果。 | Endpoint policy是額外邊界，不會授權；IAM/resource policy仍須 Allow，任何 applicable Deny仍生效。 | Endpoint policy取代 IAM；route存在即授權；bucket public-read是唯一修正。 | SAA | `SAA-1.2 · vpc-endpoints` |
| 13.8 | Interface endpoint DNS正常解析但 TCP timeout，要求依序排查。 | 查 client route/local reachability、endpoint ENI SG ingress、client SG outbound、NACL與 endpoint AZ；DNS成功只證明名稱到位址。 | 修改 IAM role先修 TCP；提高 DNS TTL；新增 IGW。 | SAA | `SAA-3.4 · vpc-endpoints` |
| 13.9 | NAT `ErrorPortAllocation`/connection capacity 指標上升，許多 hosts連同一 destination；選擇改善。 | 先確認 port/connection exhaustion，再分散來源 NAT IP/路徑或改用 private endpoint；不能只增加 instance CPU。 | 調大 S3 object size；增加 route table數量；降低 SG rule數量。 | SAP | `SAP-2.5 · vpc-nat-zonal` |
| 13.10 | 多帳號集中 egress 與每 VPC NAT做成本/故障面比較。 | 以每 GB NAT/TGW/cross-AZ path、inspection需求與故障隔離計算；集中化降低 gateway數量但增加共享依賴和 route治理。 | NAT數量越少必然最便宜；所有 AWS API 都應走 Internet；集中 egress不需 return-route設計。 | SAP | `SAP-2.6 · vpc-nat-zonal/transit-gateway` |

---

## 第 14 章：Security Group 與 Network ACL

### 現有題目問題

- Q1 的 C 是架構方案，D 是同一方案的機制說明，兩者都正確但型態不同；這是「找最像答案」而非推理。
- Q2/Q4 重複設定清單；沒有一題給實際 source、destination、port、rule number與 ephemeral range。
- Q3 只是背 stateful/stateless 定義，沒有測 established return traffic、NACL first match、default NACL/custom NACL差異或 SG reference。
- Q5 的 canary/rollback模板沒有測 organization-wide SG/NACL治理、Firewall Manager/Config或 change blast radius。
- 現有 config只有 SG chaining，沒有與 NACL 同時作用時的 packet path，讀者仍可能誤以為任一層 Allow 就足夠。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 14.1 | Internet→ALB:443→App:8080→DB:5432，選三個 SG ingress sources。 | ALB允許 client CIDR/443；App以 ALB SG為 source/8080；DB以 App SG為 source/5432，表達 workload identity。 | App開 `0.0.0.0/0:8080`；DB信任 public subnet CIDR；以 NACL名稱引用 SG。 | SAA | `SAA-1.2 · vpc-security` |
| 14.2 | App 主動連 DB，DB回程是否要在 App SG另開 ephemeral inbound。 | SG是 stateful；被允許 connection 的 return traffic自動放行，不需對稱新增 ephemeral inbound rule。 | SG stateless需雙向；只需 NACL inbound；ALB stickiness處理回程。 | SAA | `SAA-1.2 · vpc-security` |
| 14.3 | Custom NACL允許 inbound 443但 outbound只允許443，Internet client timeout。 | NACL stateless，server回 client通常需允許 outbound ephemeral destination ports；兩方向各自依規則評估。 | SG stateful會覆蓋 NACL deny；只加 inbound 80；加 NAT Gateway。 | SAA | `SAA-1.2 · vpc-security` |
| 14.4 | NACL規則 100 allow一個大 CIDR、110 deny其中惡意 `/32`，問結果。 | NACL由最低 rule number開始 first match；較後面的 deny不會覆蓋先匹配 allow，應把精確 deny放更低號碼。 | explicit deny永遠勝出不看順序；longest-prefix match；最後建立規則優先。 | SAA | `SAA-1.2 · vpc-security` |
| 14.5 | 比較 default NACL與新建 custom NACL套到 subnet後的初始行為。 | 必須知道 custom NACL未加入允許規則前會拒絕流量；變更 association會立即影響整個 subnet。 | Custom NACL預設全允許；自動複製 SG；只影響新 ENI。 | SAA | `SAA-1.2 · vpc-security` |
| 14.6 | 要封鎖已知惡意 `/24`，但多個應用 SG已經允許較大 corporate CIDR。 | SG沒有 deny；可在 NACL/Network Firewall等合適邊界明確 deny，同時評估整個 subnet影響與 rule order。 | 在 SG新增 deny；刪除 local route；用 IAM condition封鎖 TCP。 | SAA | `SAA-1.2 · vpc-security` |
| 14.7 | App instances替換後 IP改變，DB規則如何避免維護 CIDR。 | 同一 VPC或支援的連線情境以 App SG reference作 source；SG reference不會建立 route，也不代表所有 ports。 | 引用 ASG名稱；使用 public IP allowlist；把 DB設 public。 | SAA | `SAA-1.2 · vpc-security` |
| 14.8 | Flow Logs顯示 REJECT，判斷 SG與NACL除錯限制。 | Flow Logs可協助定位 ENI flow接受/拒絕，但不是 packet capture；仍須對照 SG、NACL方向/rule與 route。 | Flow Logs會指出確切 SG rule ID與 payload；CloudTrail記每個 packet；Route 53 health check能辨識 NACL rule。 | SAP | `SAP-3.2 · vpc-security` |
| 14.9 | 大量 accounts要禁止 SSH/RDP對全世界，同時保留應用團隊自主管理 SG。 | 以 organization-level preventive/detective controls管理暴露規則，讓 workload SG維持最小權限；不要靠人工季度檢查。 | Root帳號共用 SG；用單一 NACL取代所有 SG；關閉 Flow Logs。 | SAP | `SAP-1.2 · vpc-security` |
| 14.10 | SG允許、NACL也允許，但 connection仍 timeout；選下一個最合理檢查。 | Network policy只是完整 path一部分；接著查 DNS、forward/return route、listener與 target health，不能推論 application必然可用。 | 再加相同 SG rule；改 IAM user；提高 EBS IOPS。 | SAP | `SAP-2.3 · network` |

---

## 第 15 章：VPC Peering、PrivateLink 與 Transit Gateway

### 現有題目問題

- Q1 情境是「30個 consumers只需中央付款 API且彼此不可路由」，真正選擇應是 PrivateLink；正解卻是一整份 Peering/PrivateLink/TGW 菜單。
- Q2/Q3/Q4突然把 Peering當主角；Q4甚至明確把 Peering設為正解，與 Q1 情境及 least-connectivity 原則衝突。
- Q1 的 D「只部署 PrivateLink，但不建立 Peering contract」在此情境其實不需要 Peering contract，因此選項語意不成立。
- 題庫沒有考 Peering雙向 route、DNS option；PrivateLink provider NLB/acceptance/private DNS；TGW association與propagation差異。
- 現有 config偏 Peering，沒有 PrivateLink與 TGW設定，和章節標題的三方比較失衡。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 15.1 | 兩個不重疊 VPC需要任意 private-IP雙向互通且沒有中央轉送需求。 | 少量一對一全網路互通可用 Peering；雙方相關 subnet route、SG與 DNS需求仍分別設定。 | PrivateLink發布整個 CIDR；TGW是唯一可 transitive的方法所以兩 VPC也必選；只有 acceptance即可通。 | SAA | `SAA-3.4 · vpc-peering` |
| 15.2 | A↔B、A↔C均有 Peering，B想經 A連 C。 | Peering不 transitive；需 B↔C直接 peering或改用 TGW等 hub routing。 | 在 A加 default route即可轉送；開 DNS resolution即可 transitive；引用 C的 SG即可。 | SAA | `SAA-3.4 · vpc-peering` |
| 15.3 | Peering active且 DNS可解析，TCP仍 timeout；給出 A/B route tables要求找缺口。 | Peering需要去程與回程各自指向 `pcx-*`，再查 SG/NACL；control-plane active不代表 data path完成。 | 只需 requester route；加 IGW；延長 DNS TTL。 | SAA | `SAA-3.4 · vpc-peering` |
| 15.4 | 跨 Peering使用 EC2 public hostname，希望解析成 peer private IPv4。 | 兩邊 VPC DNS attributes與 requester/accepter DNS-resolution options要正確；這不會建立 route或 private hosted zone association。 | 開啟一側即可保證雙向；建立 NAT；將 hostname寫進 SG。 | SAP | `SAP-1.1 · vpc-peering` |
| 15.5 | 30個重疊 CIDR consumer VPC只需 provider付款 API，不准彼此互通。 | 使用 PrivateLink：provider internal NLB/endpoint service，consumer interface endpoint；暴露單一服務而非 route domain。 | Full-mesh Peering；單張 TGW全互通 route table；Internet-facing ALB與 public allowlist。 | SAA | `SAA-2.1 · privatelink` |
| 15.6 | PrivateLink endpoint request已 accepted，但 client解析到 public endpoint或連線 timeout。 | 分別驗證 provider private-DNS ownership、consumer private DNS/VPC DNS、endpoint ENI SG、listener/target health；acceptance只核准連線。 | Acceptance自動建立 IAM auth；加 Peering route；把 provider VPC CIDR加到 consumer default route。 | SAP | `SAP-2.5 · privatelink` |
| 15.7 | 數百 VPC、VPN、DX需要 transitive hub且 prod/dev隔離。 | 用 TGW attachments與多張 TGW route tables；association決定 ingress lookup table，propagation決定哪些 prefixes被該表學到。 | 單張全互通 table；full-mesh Peering；PrivateLink當任意雙向網路。 | SAP | `SAP-1.1 · transit-gateway` |
| 15.8 | Prod attachment關聯 prod table，但其 prefix錯誤 propagate到 dev table，問造成什麼及如何修正。 | Association與propagation是不同動作；只向應知道該 prefix的 tables propagate，必要時用 static/blackhole route維持隔離。 | Association自動限制所有 propagation；SG可阻止 route泄漏所以不用修；改 DNS即可。 | SAP | `SAP-1.1 · transit-gateway` |
| 15.9 | 需要所有 spokes經 inspection VPC，再回目的 VPC；規劃 TGW route與 appliance mode。 | Forward/return都必須經 stateful appliance；在 appliance VPC attachment正確使用 appliance mode並逐 AZ設計路徑。 | 在每個 spoke隨意開 appliance mode；只改去程；NAT Gateway保證對稱。 | SAP | `SAP-1.1 · tgw-centralized-inspection` |
| 15.10 | 比較三個方案的 unit cost與 blast radius：3個 VPC全互通、100個 VPC hub、100 consumers單一 API。 | 依 connectivity contract選：少量全網路 Peering、多網路 TGW、單服務 PrivateLink；再計算 attachment/hour與 data processing等路徑費。 | 功能最多的 TGW永遠正確；Peering永遠最便宜不看 mesh成長；PrivateLink可取代所有 east-west routing。 | SAP | `SAP-2.6 · vpc-peering/privatelink/transit-gateway` |

---

## 第 16 章：Route 53 Routing Policies

### 現有題目問題

- Q1 同時要求 low latency、disaster failover與 10% rollout，卻把所有 routing policies列成一個答案；沒有說明需要分層 records、不同 names或 deployment router，單題意圖不單一。
- 使用者截圖中的 C/D曾完全重複；目前 source中的 D已變成 health-check mechanism，但生成器仍會在 primary/peer profile相同時產生重複選項，應增加 choice uniqueness檢查。
- Q2/Q4仍是設定清單重複，沒有 records、SetIdentifier、Weight、Region、Failover、TTL或 EvaluateTargetHealth 的具體值。
- Q5 的通用 rollout治理沒有考 DNS cache、health check visibility、private endpoint或 failback/fencing。
- 第 16 章 sources目前沒有掛既有官方 `route53` key，卻掛了廣泛的 `network`。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 16.1 | 單一 endpoint、沒有特殊 steering需求，選 simple policy與 record型別。 | Simple回答單一/一組 records，不提供 weighted/latency語意；AWS target無固定 IP時可用 Alias而非硬編 IP。 | Weighted 100/0；NLB Proxy Protocol；Resolver outbound rule。 | SAA | `SAA-3.4 · route53` |
| 16.2 | 將新 ALB逐步接收約 10% DNS answers，設計 weighted records。 | 同名同型別 records使用 SetIdentifier與相對 Weight；分配作用於 DNS answers，受 resolver cache影響，不是每 100 requests精確 10次。 | Latency policy保證10%；TTL=0保證逐 request；ALB stickiness決定 DNS權重。 | SAA | `SAA-3.4 · route53` |
| 16.3 | 全球 users要導向 AWS量測延遲較低的 Region。 | 使用 latency-based routing並為各 Region建立 records；它依 AWS latency資料選擇，不等於地理距離或即時逐 request探測。 | Geolocation一定最低延遲；weighted 50/50；CloudFront geo restriction。 | SAA | `SAA-3.4 · route53` |
| 16.4 | Primary Region故障時才回答 secondary endpoint，恢復後按規則回切。 | 使用 failover primary/secondary records與 health evaluation；DNS只影響新解析，既有 connections與資料 writer fencing另行處理。 | Simple records自動 failover；只降低 TTL；Multi-value等同 active/passive DR。 | SAA | `SAA-2.2 · route53` |
| 16.5 | 法規要求德國 users到 EU endpoint、其他位置有 default。 | Geolocation依 DNS query來源位置分類，並配置 default record避免未知位置無答案；不是效能選擇。 | Latency policy保證法規；Geo restriction回傳最近 Region；只用 country-specific records不需 default。 | SAA | `SAA-3.4 · route53` |
| 16.6 | 要回傳多個健康 web server IP做 client-side分散，但不是完整 load balancer。 | Multi-value answer可搭 health checks回多個健康 records，但不取代 ALB的 connection/request代理、draining與 L7 routing。 | Simple必做 health-based剔除；weighted等同 target health；NACL可提供 DNS load balancing。 | SAA | `SAA-2.2 · route53` |
| 16.7 | Zone apex `example.com`要指 ALB，不能用一般 CNAME。 | 使用 Route 53 Alias A/AAAA指向支援的 AWS target；Alias與 routing policy是兩個獨立維度。 | 在 apex建立 CNAME；抄 ALB目前 IP；用 Resolver rule。 | SAA | `SAA-3.4 · route53` |
| 16.8 | 計畫 cutover，當天才把 TTL從 3600改 60，問舊 resolver何時可能更新。 | 必須在至少一個舊 TTL之前降低；已快取的舊 answer仍可保留到原 TTL到期，既有 connection更不會被 DNS變更切斷。 | 新 TTL立即覆寫所有 cache；health check清除 client cache；Alias永遠無 cache。 | SAA | `SAA-2.2 · route53` |
| 16.9 | Private endpoint不能被 public Route 53 health checkers直接探測，仍需 DNS failover。 | 用 CloudWatch alarm health check或由可觀測的應用訊號間接表示健康；不要把 private IP直接當 Internet health-check target。 | 建 IGW暴露 health port；用 NACL回報健康；private hosted zone自帶 failover監控。 | SAP | `SAP-1.3 · route53` |
| 16.10 | 同時需要 Region latency steering與每 Region內 blue/green rollout，設計可解釋的 record tree或分離 names。 | 每層只承擔一個 steering signal，避免把 latency、weight、failover混成一句；用具體 records、health與 rollback metric驗證 DNS結果。 | 一筆 record同時套三個 policies；只用低 TTL；Global Accelerator traffic dial可直接修改 Route 53 weights。 | SAP | `SAP-1.1 · route53` |

---

## 第 17 章：CloudFront、Global Accelerator 與 Edge

### 現有題目問題

- Q1同時描述 UDP game與 HTTP website，答案需要兩個服務；Q4卻只選 CloudFront，因此漏掉同一核心需求的一半。
- Q2/Q3/Q4有三題只圍繞 CloudFront，Global Accelerator與 Lambda@Edge幾乎只作名詞干擾。
- 現有題目未測 cache key與 origin request policy的差異，這是最容易造成低 hit ratio或跨使用者內容洩漏的核心設定。
- 沒有測 OAC僅適用 S3 REST origin、origin bypass、GA static anycast IP、traffic dial/endpoint weight或 client affinity。
- 第 17 章 sources沒有掛既有官方 `cloudfront`，也缺 `global-accelerator`。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 17.1 | 全球靜態網站由 private S3提供，要求 cache、WAF且禁止直接 S3 URL。 | CloudFront + S3 REST origin + OAC；bucket policy只允許指定 distribution，保持 Block Public Access。 | S3 website endpoint + OAC；public bucket；Global Accelerator直接 cache S3。 | SAA | `SAA-1.2 · cloudfront` |
| 17.2 | `/assets/*`可 cache一天，`/api/*`不可 cache且轉到 ALB；設計 behaviors與 precedence。 | 用不同 cache behaviors、origins與 policies；更具體 path要正確匹配，API不得沿用 static cache policy。 | 只改 default TTL；用 Route 53 path routing；以 NLB listener rule看 URL。 | SAA | `SAA-3.4 · cloudfront` |
| 17.3 | Response依 `Accept-Language`與 `version` query改變，Authorization只需回源；設計 cache/origin request policies。 | 真正改變 response的欄位進 cache key；只供 origin使用且不改變 cached representation的欄位才只轉送，避免洩漏與 fragmentation。 | 所有 headers/cookies都進 key；Authorization不進 key但 cache user-specific response；完全不轉送 query。 | SAP | `SAP-2.5 · cloudfront` |
| 17.4 | Origin回 `Cache-Control: no-store`，但 cache policy MinimumTTL大於0。 | MinimumTTL可強制至少 cache該時間；敏感 response應使用適當 policy/零 caching，不能只相信 origin directive。 | no-store永遠覆蓋 CloudFront；WAF自動禁止 cache；OAC決定 TTL。 | SAP | `SAP-2.3 · cloudfront` |
| 17.5 | 攻擊者可直接打 public ALB繞過 CloudFront/WAF，選擇 origin protection。 | 限制 origin只接受 CloudFront可驗證的路徑/secret header或 AWS支援的 origin control，並搭配 WAF與 TLS；edge protection不自動私有化 origin。 | 只降低 TTL；只開 geo restriction；使用 public DNS難猜名稱。 | SAP | `SAP-2.3 · cloudfront` |
| 17.6 | 全球 UDP遊戲需要兩個固定 IP與快速 regional endpoint切換。 | Global Accelerator提供 static anycast IP、TCP/UDP listeners與 health-based endpoint routing；CloudFront是 HTTP proxy/cache。 | CloudFront distribution；Route 53加 EIP就成 anycast；ALB UDP listener。 | SAA | `SAA-3.4 · global-accelerator` |
| 17.7 | 新 Region先承接少量 GA traffic，區分 traffic dial與 endpoint weight。 | Traffic dial調整 Region endpoint group整體份額；endpoint weight調整同一 group內 endpoints；兩者都影響新 flows而非搬移既有 connection state。 | Route 53 TTL控制 GA dial；client affinity等同 weight；CloudFront behavior priority。 | SAP | `SAP-1.1 · global-accelerator` |
| 17.8 | Stateful clients需要盡量回同一 GA endpoint，但 endpoint故障仍要切換。 | 依需求使用 client affinity並理解它不是 durable session store；健康與 failover仍優先，應用 state需外部化或可恢復。 | Affinity保證永不切換；ALB cookie可控制 UDP；提高 DNS TTL。 | SAP | `SAP-1.3 · global-accelerator` |
| 17.9 | 只需極低延遲 header rewrite，與需要 network call/JWT library的 edge邏輯比較。 | 簡單 viewer logic優先 CloudFront Functions；較完整 runtime/event能力才用 Lambda@Edge，並納入 Region/version/log/timeout限制。 | 所有 business logic都放 viewer request；用 GA listener修改 HTTP header；Lambda@Edge可任意 VPC access。 | SAA | `SAA-4.4 · cloudfront` |
| 17.10 | 同一產品同時有可 cache HTTP下載與不可 cache TCP protocol。 | 將兩條入口分開：CloudFront負責 HTTP cache/security，GA負責 TCP/UDP global network path；不能用「edge服務」一詞抹平 protocol contract。 | 所有流量依序 GA→CloudFront；CloudFront支援任意 UDP；GA提供 HTTP cache key。 | SAP | `SAP-2.5 · cloudfront/global-accelerator` |

---

## 第 18 章：ALB、NLB 與 Gateway Load Balancer

### 現有題目問題

- Q1同時要求 host routing、TLS passthrough與 firewall insertion，正確答案只是三服務用途清單；不是可部署的 architecture。
- Q4把 ALB單獨判為正解，卻無法滿足題幹中的 TLS passthrough與透明防火牆，與 Q1矛盾。
- Q2/Q3只深入 ALB；NLB的 listener/target/source IP語意與 GWLB的 GENEVE/GWLBe/對稱 route未被測試。
- 題目沒有區分 NLB `TCP` listener的 TLS passthrough與 `TLS` listener的 TLS termination，容易教出錯誤。
- 現有 config只有 ALB，三種 load balancer覆蓋不平衡。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 18.1 | `api.example.com/orders/*`與 `/images/*`送不同 target groups，並在 443終止 TLS。 | ALB理解 HTTP host/path並可使用 ACM certificate、ordered listener rules與 target groups。 | NLB依 path分流；GWLB終止 HTTPS；Route table依 URL選 next hop。 | SAA | `SAA-3.4 · elb-alb` |
| 18.2 | ALB rules中 priority 10為 `/*`、20為 `/admin/*`，問 `/admin/x`走哪裡及修正。 | ALB第一個匹配的較低 priority數字規則生效；應避免寬規則先吞掉具體路徑，default最後。 | Longest path pattern自動勝出；最後建立規則優先；target group weight決定 rule priority。 | SAA | `SAA-3.4 · elb-alb` |
| 18.3 | Fargate tasks使用 `awsvpc`，選 ALB target type與 health path。 | 通常註冊 task ENI IP，選 `ip` target；health endpoint要快速且能代表 readiness，不應只檢查 process存在。 | 使用宿主 EC2 `instance` target；Lambda target；以 SG ID作 target。 | SAA | `SAA-2.2 · elb-alb` |
| 18.4 | Legacy app把 session放單機記憶體，問 stickiness能做什麼、不能做什麼。 | Stickiness可暫時提高同 client回同 target機率，但造成 skew且 target replacement仍丟 session；長期應外部化 session。 | Stickiness複寫 session；可抵抗 target故障；等同 source-IP firewall。 | SAA | `SAA-2.2 · elb-alb` |
| 18.5 | 長輪詢每 90秒才有資料，ALB idle timeout為60秒，client收到斷線。 | 協調 ALB、application與 client timeout，或發送 keepalive/改協定；單純重試可能放大負載。 | 調 health-check interval；提高 DNS TTL；開 cross-zone。 | SAA | `SAA-3.4 · elb-alb` |
| 18.6 | 非 HTTP payment protocol要求 backend自己終止 TLS、入口有 static IP。 | NLB使用 TCP listener做 TLS passthrough並把 bytes送 backend；若選 TLS listener則是在 NLB終止 TLS。 | ALB TCP listener；NLB TLS listener仍是 passthrough；GWLB certificate termination。 | SAA | `SAA-3.4 · elb-nlb` |
| 18.7 | Backend需原始 client IP，問 preserve client IP與 Proxy Protocol v2的選擇及風險。 | 依 target/protocol支援情況保留來源 IP或啟用 PPv2；backend必須解析 PPv2，來源 IP也不能當唯一 identity。 | `X-Forwarded-For`適用所有 TCP；PPv2可隨意開不改 backend；client IP永遠由 NLB保留。 | SAP | `SAP-2.5 · elb-nlb` |
| 18.8 | NLB每 AZ targets數量不均，判斷 cross-zone trade-off。 | Cross-zone可讓 node使用其他 AZ healthy targets，但可能改變 cross-AZ path/cost；它不增加總 capacity。 | Cross-zone建立新 targets；只適用 ALB rules；可修復 unhealthy application。 | SAP | `SAP-2.4 · elb-nlb` |
| 18.9 | 多個 spoke VPC流量要透明送第三方 firewall fleet，不改應用 endpoint。 | 使用 GWLB/GWLBe；routes把 flow導入 endpoint，GWLB以 GENEVE送 appliance，forward/return需對稱。 | ALB WAF取代 L3 inspection；NLB listener rule插入 appliance；只建立 GWLB不改 routes。 | SAP | `SAP-1.1 · elb-gwlb` |
| 18.10 | 需要 static IP入口加 L7 host/path routing，且接受額外元件。 | 可使用 NLB以 ALB作 target，讓 NLB承擔 L4/static入口、ALB承擔 L7；須逐層設 listener、health、SG與診斷。 | ALB直接配置 EIP；GWLB提供 host routing；Route 53 Alias固定 ALB底層 IP。 | SAP | `SAP-2.5 · elb-nlb/elb-alb` |

---

## 第 19 章：VPN、Direct Connect 與 Hybrid Connectivity

### 現有題目問題

- Q1需求是大量穩定流量、加密、兩個 locations容錯，正解只說「關鍵系統建立多路徑」，沒有可驗證的 DX/VPN/BGP設計。
- Q2/Q3/Q4突然把 Site-to-Site VPN當主角；Q4選 VPN單獨解決數 TB穩定延遲需求，與 Q1衝突。
- `Direct Connect Gateway`目前沒有自己的 profile，因 fallback而複製了 `AWS Direct Connect`的 purpose/mechanism/config；這是內容資料的事實性缺口。
- 「每個 VPN connection有兩條 tunnels」沒有延伸測試：兩 tunnels不是兩個 customer locations，也不保證 customer router/provider故障隔離。
- 沒有測 VIF類型、BGP route preference、DX不預設加密、VPN over DX/MACsec、resiliency model或 failover演練。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 19.1 | 新專案兩天內要建立 encrypted hybrid path，流量中等且可接受 Internet變動。 | Site-to-Site VPN能快速建立 IPsec連線；每 connection有兩 tunnels，應同時配置/監控而非只用一條。 | 等待 dedicated DX才可加密；VPC Peering到 on-prem；Public VIF提供 IPsec。 | SAA | `SAA-3.4 · site-to-site-vpn` |
| 19.2 | VPN使用 BGP，一條 tunnel down後要自動改走另一條。 | Customer gateway與 VGW/TGW雙方建立正確 BGP sessions/advertisements；route selection與 tunnel health共同決定 failover。 | DNS failover切 VPN tunnel；SG rule發布 BGP；static route會自動提供 ECMP。 | SAP | `SAP-1.1 · site-to-site-vpn` |
| 19.3 | 每天數 TB、要求較可預測 throughput/latency與 private path。 | Direct Connect適合持續高流量與穩定路徑，但 provision較慢且仍須設計 HA、routing與 encryption。 | 單條 VPN永遠同等穩定；DX自動跨兩 locations；DX等同端到端加密。 | SAA | `SAA-3.4 · direct-connect` |
| 19.4 | 選 private/public/transit VIF：一個 VPC、AWS public services、以及 TGW多 VPC。 | Private VIF連 private VPC資源路徑，public VIF存取 AWS public prefixes，transit VIF經 DXGW連 TGW；依目的 contract選。 | Public VIF讓 EC2自動 public；private VIF直接連任意 TGW；三者可在 route table任意互換。 | SAP | `SAP-1.1 · direct-connect` |
| 19.5 | 定義 Direct Connect Gateway真正角色，修正現有重複 profile。 | DXGW是連接 VIF與 VGW/TGW等資源的全球性 routing construct，不是實體 circuit、VLAN或 customer router本身。 | DXGW提供 physical port；DXGW自動加密；DXGW取代 TGW route table。 | SAP | `SAP-1.1 · direct-connect` |
| 19.6 | 金融 workload要求兩個 location故障隔離，設計 DX resiliency。 | 依 criticality採多 DX connections跨不同 locations/devices，並保留 VPN等備援；用 Resiliency Toolkit/故障演練驗證。 | 同 location兩 VIF等於 location redundancy；VPN的一對 tunnels等於兩 DX sites；LAG跨 location。 | SAP | `SAP-2.2 · direct-connect-resiliency` |
| 19.7 | DX必須加密，選擇 MACsec與 VPN over DX的思考條件。 | DX本身不是預設端到端加密；依 port/location支援與威脅模型選 MACsec或在 DX上建立 IPsec VPN，並管理 keys/tunnels。 | Private VIF自動 TLS；BGP MD5加密所有 payload；只用 SG即可加密線路。 | SAP | `SAP-2.3 · direct-connect` |
| 19.8 | DX與 VPN同時廣告同一 prefix，要求平時走 DX、故障走 VPN。 | 以 BGP attributes與 AWS route preference設計 primary/backup，並實際撤回 route/斷線測試；不能只因兩條線存在就宣稱 failover。 | Route 53選 hybrid path；較高頻寬線路自動優先；SG rule number決定 BGP。 | SAP | `SAP-1.1 · direct-connect/site-to-site-vpn` |
| 19.9 | 比較 centralized TGW/DXGW與每 VPC獨立 VGW/VPN在多帳號環境的治理。 | 大量 networks以 TGW/transit VIF集中 route domains與 attachment治理；小型獨立環境可用較簡單連線，需權衡 blast radius與費用。 | 所有 VPC建立 full-mesh VPN；DXGW自帶 segmentation；Organizations自動傳遞 routes。 | SAP | `SAP-1.1 · transit-gateway/direct-connect` |
| 19.10 | Hybrid path可 ping但大型傳輸失敗或效能差，要求從 MTU/BGP/兩向 path/metrics除錯。 | 逐層驗證 DNS、route advertisement、return path、MTU與 tunnel/circuit metrics；「connection available」不代表 application throughput達標。 | 增加 DNS records；把 NACL全開即保證吞吐；提高 EBS volume解決所有 network loss。 | SAP | `SAP-2.5 · direct-connect` |

---

## 第 20 章：Multi-VPC、Hybrid DNS 與 Network Inspection

### 現有題目問題

- Q1是 Resolver + TGW + inspection的三題合一，正解也是三元件菜單；Q4卻只選 Resolver，無法完成 segmentation與 inspection。
- Q2/Q3只深入 Resolver；TGW association/propagation與 Network Firewall policy/routes幾乎沒有被題目驗證。
- 沒有實際 DNS query path，因此讀者很容易反轉 inbound/outbound endpoint：inbound是 on-prem→VPC resolver，outbound是 VPC→on-prem DNS。
- 沒有考 rule matching、RAM sharing、private hosted zone、DNS loop、query logging或 endpoint SG的 UDP/TCP 53。
- Inspection只用「對稱路由」一句帶過，沒有 ingress/egress/east-west route tables、每 AZ firewall endpoint、HOME_NET或 TLS inspection限制。

### exactly 10 個原創題目意圖

| # | 原創題目意圖 | 正確原則 | 三個可信干擾概念 | Level | 官方 task／source key |
|---|---|---|---|---|---|
| 20.1 | On-prem client查詢 AWS private hosted zone `aws.corp`，畫 query path。 | On-prem DNS把該 domain轉送到 VPC中的 Resolver inbound endpoint IP；inbound endpoint再使用 VPC Resolver/associated private zone回答。 | 使用 outbound endpoint；建立 public hosted zone；讓 on-prem直接查 VPC `+2` resolver address。 | SAP | `SAP-1.1 · route53-resolver` |
| 20.2 | VPC workload查詢 on-prem `corp.local`，畫 query path與 rule。 | Outbound endpoint搭 conditional forward rule把指定 suffix送到 on-prem DNS target IP；需要 network return path與 SG允許 DNS。 | Inbound endpoint主動送 query；Route 53 latency policy；VPC Peering DNS option自動轉送任意 domain。 | SAA | `SAA-3.4 · route53-resolver` |
| 20.3 | 同時存在 `example.com`與更精確 `dev.example.com` Resolver rules，問 query如何選擇。 | 依最具體 matching domain/rule處理；要明確設計 forwarding/system behavior，避免過寬規則遮蔽 private/public DNS意圖。 | 依 rule建立時間；隨機輪替；TGW route priority決定 DNS rule。 | SAP | `SAP-1.1 · route53-resolver` |
| 20.4 | 中央 DNS account把 outbound rule共享給數百 VPC。 | 透過 RAM/Profiles等受支援方式共享 rules並關聯 consumer VPC；共享不會自動建立 TGW route、SG或 on-prem DNS conditional forward。 | 複製 private hosted zone到每 account；用 Organizations自動建立 DNS path；只共享 endpoint ENI。 | SAP | `SAP-1.4 · route53-resolver` |
| 20.5 | AWS與 on-prem雙方都把同一 suffix轉送給對方，造成 SERVFAIL/timeout。 | 建立清楚 authoritative owner與單向 conditional forwarding，保留必要 system rule，避免 forwarding loop；用 query logs與 `dig` trace驗證。 | 降低 TTL修 loop；增加更多 outbound endpoints；改用 weighted records。 | SAP | `SAP-3.2 · route53-resolver` |
| 20.6 | Prod/dev attachments都連 TGW，但不得互通，只能各自到 shared DNS。 | 使用不同 TGW route tables/route domains；association決定來源 lookup，選擇性 propagation/static routes只發布 shared services prefixes。 | 單張全互通 table再靠名稱隔離；只用 SG跨所有 networks；PrivateLink發布完整 DNS server網段。 | SAP | `SAP-1.1 · transit-gateway` |
| 20.7 | Spoke A→Spoke B去程經 inspection VPC，回程由 TGW直接回 A，stateful firewall丟包。 | 修改 TGW/VPC routes讓雙向都經相同 inspection service，按架構正確使用 appliance mode/每 AZ endpoint，驗證 route symmetry。 | 只在 firewall SG開 ephemeral ports；提高 DNS TTL；啟用 ALB stickiness。 | SAP | `SAP-1.1 · tgw-centralized-inspection` |
| 20.8 | 集中 Internet egress使用 AWS Network Firewall，要求畫每 AZ path。 | Spoke→TGW→inspection VPC firewall endpoint→NAT/IGW，回程反向；每 AZ route tables與 endpoint capacity/failure需明確，不能只有一個邏輯方塊。 | Firewall endpoint取代 NAT；只建立 policy不改 route；所有 AZ流量固定繞單一 AZ最可靠。 | SAP | `SAP-1.2 · network-firewall` |
| 20.9 | Network Firewall stateless與 stateful rules、default actions、`HOME_NET`如何影響 east-west檢查。 | Stateless先分類/轉交，stateful依 connection與 rule group檢查；`HOME_NET`等變數要涵蓋實際 internal CIDRs，並開啟 alert/flow logs驗證。 | SG rules自動匯入 firewall；HOME_NET是 Route 53 zone；stateful rules不需要對稱 path。 | SAP | `SAP-2.3 · network-firewall` |
| 20.10 | TLS inspection需求包含內部敏感 API，問憑證信任、解密範圍與例外。 | TLS inspection需要可管理的 CA/certificate與 client trust，依資料分類限定解密範圍並處理不相容/隱私例外；它不取代 application auth。 | 開啟 TLS inspection不需 client trust；用 WAF檢查所有任意 TCP TLS；解密後 IAM自動允許。 | SAP | `SAP-1.2 · network-firewall` |

---

## 實作時的題庫品質門檻

1. 每章必須恰好 10 題，且上述 10 個 intent各出一題；不可用換服務名稱的模板補數量。
2. 每題只設一個主要判斷；需要多元件時，題幹必須明確要求「選兩項」或要求完整 packet/query path。
3. 每個錯誤選項都必須在某個相鄰情境下合理，禁止再使用「服務自動理解所有 business requirements」「全部部署」「給 AdministratorAccess」這類免費送分句。
4. 建立全書 choice uniqueness檢查：同題 normalized choice不得重複；正解與干擾項不得只是同一敘述的摘要/展開。
5. 建立 contradiction檢查：同章共用 scenario時，後題不可把前題明確排除的方案改成正解，除非題幹清楚改變 constraint。
6. 每題解析至少包含：packet/query從哪裡出發、依哪些設定選 next hop/answer/target、回程或 cache/state如何作用、錯誤選項在哪個條件下才會變正解。
7. Config題必須展示真實 record/route/rule/listener/attachment欄位或 CLI/IaC片段，不得只叫讀者從一串名詞中選另一串名詞。
8. Current-service新增功能（例如 Regional NAT Gateway）必須標記文件日期、Region availability與 exam-version；產品事實與該考試版本的必考範圍要分開寫。
9. 正確性來源優先使用官方產品文件與官方 exam guide；community筆記只能協助發現常見混淆，不可決定答案。
10. 生成 HTML 後重新抽取第 11–20 章全部 100 題，檢查題數、答案 index、選項唯一性、source key存在、task mapping有效，以及每個 intent只出現一次。

SUPERSET_WORKER_DONE
status: complete
task: P01-audit
artifact: tools/aws_exam_audits/part_01.md
chapters: 11-20
question_intents: 100
other_files_modified: false
