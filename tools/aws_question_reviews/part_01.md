# R01 獨立實質審查：part_01（第 11–20 章）

審查日期：2026-10-01
Reviewer：R01（非本題庫作者）
範圍：`tools/aws_question_banks/part_01.json` 全部 100 題

## 結論摘要

- 題數與 intent：10 章 × 每章 10 題；每章 intent 1–10 各一次，結構完整。
- 題型：80 題單選、20 題複選；答案位置分布符合每章同一位置不超過 4 次的要求。
- 實質判定：77 題可保留，23 題必須修訂。
- 來源：共 99 個 official sources、8 個 community sources。所有題目都有 official source，但 4 個 official source URL 已退化成文件首頁或 retired whitepaper 目錄，無法充分支持引用它們的題目。
- 題目來源安全性：未發現 ExamTopics、braindump、回憶真題或宣稱 actual exam questions 的來源。8 個 community sources 都是 Jayendra Patil 的公開教學文章；逐題比對沒有發現連續 10 個以上實質 token 的照抄。
- 舊題重疊：`ch017-q01` 的正解措辭與 `aws_architect_deep_content.py` 中既有 S3/OAC fallback 題高度近似，需重寫；其餘題目沒有發現明顯沿用舊五題模板。
- Exam scope：Regional NAT Gateway 與 Route 53 Profiles 都是 current-service material。Regional NAT 題已有 enrichment 標記；Route 53 Profiles 題仍需把 SAP-C02 baseline 與 current enrichment 分開。

整體判定為 **REVISE**。題庫骨架與大多數題目的推理方向良好，但以下問題會造成錯誤學習、非唯一答案、scope 混淆或來源不可追溯，不能直接發布。

## 100 題逐題覆核矩陣

| 章 | 可保留 | 必須修訂 |
|---|---|---|
| 11 | `ch011-q02`, `ch011-q06`, `ch011-q07`, `ch011-q08`, `ch011-q09` | `ch011-q01`, `ch011-q03`, `ch011-q04`, `ch011-q05`, `ch011-q10` |
| 12 | `ch012-q01`–`ch012-q09` | `ch012-q10` |
| 13 | `ch013-q01`–`ch013-q03`, `ch013-q05`–`ch013-q10` | `ch013-q04` |
| 14 | `ch014-q02`–`ch014-q09` | `ch014-q01`, `ch014-q10` |
| 15 | `ch015-q01`–`ch015-q10` | 無 |
| 16 | `ch016-q02`, `ch016-q06`–`ch016-q10` | `ch016-q01`, `ch016-q03`, `ch016-q04`, `ch016-q05` |
| 17 | `ch017-q02`–`ch017-q04`, `ch017-q06`–`ch017-q08`, `ch017-q10` | `ch017-q01`, `ch017-q05`, `ch017-q09` |
| 18 | `ch018-q01`–`ch018-q10` | 無 |
| 19 | `ch019-q01`–`ch019-q05`, `ch019-q09`, `ch019-q10` | `ch019-q06`, `ch019-q07`, `ch019-q08` |
| 20 | `ch020-q01`, `ch020-q02`, `ch020-q06`–`ch020-q09` | `ch020-q03`, `ch020-q04`, `ch020-q05`, `ch020-q10` |

「可保留」表示答案集合唯一、核心事實正確、intent 有實際被測到，且干擾項能由題目限制排除；不代表文字永遠不能再潤飾。

## 必須修訂的題目與精確動作

### 第 11 章

#### `ch011-q01` — 沒有真的測到 CIDR 容量計算

題目給出每 AZ 2,000 個 app ENI 與 50% 成長，但正解只說「依需求決定 prefix」，沒有讓考生算出或辨識 prefix。這仍是方向題，不是 audit 11.1 要求的容量題。

修訂動作：

1. 將四個選項都改成具體 subnet plan。
2. App tier 每 AZ 至少要容納約 3,000 個 ENI；應讓正解明確使用 `/20`（4,096 個位址，扣除 AWS 保留位址後仍足夠），並為三個 AZ 配置不重疊範圍。
3. 解析要明算 `/21` 為何不足、AWS 每個 subnet 保留位址如何影響可用量，以及為何既有 subnet 不能原地放大。

#### `ch011-q03` — IPAM pool 來源不可直接驗證

題目方向與答案集合正確，但 `aws-ipam-pools` 目前從 `create-ipam-pool.html` 被導向 IPAM 文件首頁，沒有直接支持 locale、pool hierarchy 與分享行為。

修訂動作：

1. 保留題目內容。
2. 將 `aws-ipam-pools` 換成現行 IPAM pool hierarchy、locale、AWS Organizations delegated administrator、AWS RAM pool sharing 的精確官方頁面；不要引用產品首頁。
3. 解析補充：IPAM 的 home Region、pool locale、delegated administrator 與 consumer account 是四個不同概念。

#### `ch011-q04` — Locale 事實正確，但來源已退化

正解 `ap-southeast-1` 正確；問題同樣是 `aws-ipam-pools` 只導向文件首頁。

修訂動作：

1. 換成明確定義 pool locale 的官方頁面。
2. 解析補上 locale 代表「可從該 pool 配置資源的 Region」，不是 IPAM home Region、管理者所在地或複寫 Region。
3. 若官方現行限制仍如此，補充 locale 建立後不可任意更換，避免讀者誤以為它只是標籤。

#### `ch011-q05` — 把 unmanaged 與 noncompliant 混在一起

題幹說團隊「手動建立」未從核准 pool 配置的 `/18` VPC。這類資源通常首先是 **unmanaged**；若從具有 netmask allocation rules 的 pool申請不合規 prefix，配置應被阻止。現有正解直接說監控 managed/noncompliant resources，沒有把兩種狀態分開，會教錯 IPAM compliance 模型。

修訂動作：

1. 二選一重寫：
   - 若要考 preventive control：改問「從 pool 申請 `/18`」並把正解寫成 allocation rules 會拒絕不符合 `/24`–`/20` 的配置。
   - 若要考 discovery/governance：保留手動建立情境，但正解必須先辨識它是 unmanaged，再說明如何納管與檢查 overlap/compliance。
2. 不得宣稱 IPAM 或 SCP 會替現有 VPC 自動重新編址。
3. 換掉退化的 `aws-ipam-pools` URL，加入直接說明 resource status/compliance 的官方來源。

#### `ch011-q10` — Pool utilization 與 subnet IP utilization 混淆

題目明確說的是 production **IPAM pool** utilization。刪除 idle ENI 只會釋放 subnet 內位址，通常不會把已配置給 VPC 的 CIDR allocation 歸還 IPAM pool；「過度配置 subnet」也不能直接縮小後回收。正解 B 把不同層級的 utilization 混成一件事。

修訂動作：

1. 明確選定 metric：
   - 若考 IPAM pool free space，正解應是回收未使用的 VPC CIDR allocations、釋放可刪除的 VPC/CIDR、擴充上層 pool或規劃新的 non-overlapping pool。
   - 若考 subnet address utilization，才可討論 idle ENI、load balancer node、VPC endpoint ENI 與新 subnet。
2. 不要把刪除 ENI 寫成會釋放 IPAM pool prefix。
3. 解析要區分 pool allocation、VPC CIDR、subnet CIDR、ENI address 四層 ownership。

### 第 12 章

#### `ch012-q10` — 「舊 Peering」不必然導致失敗

只要舊 Peering 仍有效且能到達 App CIDR，去程走 TGW、回程走 Peering 不必然 timeout；只有路徑已失效，或中間有必須看見雙向 flow 的 stateful appliance/NAT，非對稱才成為明確根因。現題沒有給足條件，因此 B 並非唯一可證明的修正。

修訂動作：

1. 明確說明舊 Peering 已刪除／route 為 blackhole，或去程經 stateful firewall而回程繞過它。
2. 如果只考 reachability，將正解聚焦在「修復不存在的 return path」；如果考 symmetry，題幹必須明示 stateful inspection。
3. 題目提到 Reachability Analyzer，但 source 只有 route tables 與 Flow Logs；加入 Reachability Analyzer 的直接官方來源。

### 第 13 章

#### `ch013-q04` — Regional NAT 題目可保留，來源 URL 不可保留

Regional NAT Gateway 是有效的 current-service enrichment，且題目已使用 `ENRICHMENT-CURRENT`，scope 處理正確。但 `aws-nat-regional` 的 `regional-nat-gateway.html` 目前被導向 VPC User Guide 首頁，無法作為可稽核來源。

修訂動作：

1. 將來源改成現行 NAT gateways 文件中的 Regional NAT Gateway 章節，例如 `nat-gateways.html#regional-nat-gateway`，並加入官方發布公告。
2. 解析明列：Regional 與 zonal NAT 的 failure domain、route target、位址/EIP、quota、Region availability 與計費差異。
3. 保留「不是自動納入舊考綱」的說明，不能把 2025 年後服務行為冒充 SAP-C02 原始藍圖必考點。

### 第 14 章

#### `ch014-q01` — 沒有完整覆蓋 audit 14.1 的三層 SG chain

Audit 要求驗證 ALB、App、DB 三個 ingress source；現題只選 App SG 與 DB SG，沒有測到 ALB SG 的 client ingress。

修訂動作：

1. 改成單選，讓每個選項都是完整三條規則組合；正解必須包含：
   - ALB SG：client CIDR → TCP 443。
   - App SG：ALB SG → TCP 8080。
   - DB SG：App SG → TCP 5432。
2. 或保留複選但明確說「只選 App 與 DB 兩層」；此方案仍不足以完成 audit 14.1，較不建議。
3. 解析補充 SG reference 不會建立 route，也不代表所有 ports。

#### `ch014-q10` — Troubleshooting source 已退化成文件首頁

答案集合合理，但 `aws-vpc-troubleshooting` 的 URL 目前被導向 VPC User Guide 首頁，不能直接支持 troubleshooting flow。

修訂動作：

1. 換成現行 VPC network troubleshooting、Reachability Analyzer、Flow Logs、ELB target health 的精確官方頁面。
2. 解析按順序區分 DNS、route、SG/NACL、listener、process/target health；避免只列工具名稱。

### 第 16 章

#### `ch016-q01` — AAAA 需要 dual-stack 前提

「Alias A/AAAA 指向 ALB」容易被讀成無條件同時建立兩種 record。AAAA 只有在 ALB/整條路徑支援 IPv6 dual-stack 時才合理。

修訂動作：

1. 正解改成「Alias A；若 ALB 為 dual-stack且需要 IPv6，再建立 Alias AAAA」。
2. 題幹若要同時測 A/AAAA，必須明示 dual-stack requirement。

#### `ch016-q03` — 遺漏 Route 53 全部不健康時的 fail-open

正解 C 說健康評估可避免回答 unhealthy endpoint，沒有說當所有候選 records 都 unhealthy 時，Route 53 仍可能視它們為健康並返回，以避免 DNS 完全無答案。現有絕對語氣不準確。

修訂動作：

1. 將 C 改成「只要同一 routing set 中仍有健康候選，就排除 unhealthy record」。
2. 解析明確說明 all-unhealthy fail-open 行為，以及 health check 不會中斷既有 connections。

#### `ch016-q04` — Failover policy 同樣缺少雙方都 unhealthy 的行為

Primary unhealthy、secondary healthy 時答案 C 正確；但解析應說明 primary 與 secondary 都 unhealthy 時 Route 53 的 fallback 行為，否則讀者會誤以為一定不回答 primary。

修訂動作：

1. 保留答案 C。
2. 解析補上 both-unhealthy edge case、TTL/cache 與既有 connection 的限制。
3. 不得把 DNS failover描述成資料庫 writer fencing或資料複寫機制。

#### `ch016-q05` — 把 DNS query location 寫成終端使用者法規保證

Route 53 geolocation 通常依 DNS resolver 的來源位置，並可使用 EDNS0 client-subnet資訊；它不等於可靠驗證終端使用者所在地。題幹以「法規要求德國 users」表述，容易把 DNS steering 誤教成合規地理圍欄。

修訂動作：

1. 若只考 routing policy，改成「依 DNS query來源位置做內容在地化」。
2. 若保留法規情境，解析必須說 geolocation routing 不是使用者身分或資料駐留的唯一 enforcement，仍需 application/account/data controls。
3. 說明 default record 的用途與 resolver/EDNS client subnet 判定限制。

### 第 17 章

#### `ch017-q01` — 與舊 fallback 題措辭高度近似

正解「保持 Block Public Access、使用 S3 REST origin 與 OAC、bucket policy只允許指定 distribution」與 `aws_architect_deep_content.py` 既有 S3/OAC 題的正解幾乎是同一句話。概念可以相同，但本題庫契約要求不要沿用舊題措辭。

修訂動作：

1. 重寫 scenario、所有 choices 與 explanations，不只替換幾個同義詞。
2. 可改成要求辨識 bucket policy 中的 CloudFront service principal、distribution `SourceArn`、REST endpoint 與 website endpoint差異。
3. 保留 OAC 核心事實，但產生新的推理形狀。

#### `ch017-q05` — 2026 年已有更強的 VPC origin 選項

如果題目真的問「最佳 defense in depth」，把 ALB 改成 internal並使用 CloudFront VPC origin，通常比繼續公開 ALB、依賴 prefix list與 secret header更強。現題沒有說 ALB 必須維持 internet-facing，因此 A 不是全域唯一最佳答案。

修訂動作：

1. 二選一：
   - 明示 ALB 因相容性限制必須保持 internet-facing，此時 A 是正解。
   - 加入「internal ALB + CloudFront VPC origin」並依需求把它設成正解。
2. 若保留 public ALB方案，解析要說 managed prefix list只限制來源網段，secret header仍需保密與輪替；兩者是 defense in depth，不是不可偽造的 identity。
3. 加入 CloudFront VPC origins 的現行官方來源。

#### `ch017-q09` — 「較重邏輯」不足以唯一選 Lambda@Edge

CloudFront Functions能力持續演進；只說「較完整 runtime與較重邏輯」沒有可判定門檻，也沒有重現 audit 所要求的 network call、event/body或執行限制。

修訂動作：

1. 給需求 B 一個 CloudFront Functions 明確不支援的條件，例如 outbound network call、request body access、origin-facing event或超出其執行限制。
2. 解析以 runtime、event位置、network/body access、timeout、部署 Region/version與 logs逐項比較，不要只寫「比較重」。

### 第 19 章

#### `ch019-q06` — Maximum resiliency 被寫成可能只有兩條 connections

AWS Direct Connect Resiliency Toolkit 的 maximum resiliency model 要求 separate connections終止於 separate devices，並跨多個 locations；標準圖形是每個 location兩條、共四條 connections。現有 B「在兩個 locations建立 connections」可能只表示每處一條，這比較接近 high resiliency，不能精確回答題幹中的 maximum resilience。

修訂動作：

1. 正解明寫「兩個 locations，每個 location兩條終止於不同 AWS devices 的 connections」，並包含 customer/provider path diversity。
2. 說明 high resiliency 與 maximum resiliency 的差別。
3. VPN backup可作額外保護，但不能把一組 VPN tunnels算成兩個 DX location。

#### `ch019-q07` — VPN over DX 來源已退化

題目核心判斷正確，但 `aws-vpn-over-dx` 已從原 whitepaper章節導到 retired/上層目錄，無法直接支持現行實作。

修訂動作：

1. 改用現行 Direct Connect encryption、MACsec、Site-to-Site VPN over Direct Connect 的精確官方文件。
2. 解析清楚區分：
   - MACsec：Layer 2 link encryption，受 port/location/device支援限制。
   - IPsec VPN over DX：Layer 3 overlay，有 tunnel/throughput/route設計。
3. 不得讓讀者誤以為 private VIF或 BGP authentication會自動加密 application payload。

#### `ch019-q08` — Route preference 過度抽象，拓撲不同會有不同規則

「依 AWS route preference與 BGP attributes」方向正確但不可執行。VGW、TGW、VPC route table各有自己的 precedence；未指定 gateway與 prefix長度，就不能唯一說明 DX如何成為 primary。

修訂動作：

1. 明示拓撲，例如 private VIF與 Site-to-Site VPN都終止於同一 VGW，且廣告相同 prefix。
2. 給出相同或不同 prefix長度、static/propagated來源與 BGP attributes，要求判斷實際優先順序。
3. 解析依序說明 longest-prefix match、static/propagated或服務特定 route priority、BGP attributes與 failover測試；加入精確 route-priority官方來源。

### 第 20 章

#### `ch020-q03` — 第二個正解只是模糊建議，不是可驗證的 Resolver precedence

A 正確測到 most-specific rule；C 只說「應檢查」多種行為，沒有說出 Route 53 Resolver 真正的 precedence，因此不像可判真假的答案。

修訂動作：

1. 將 C 改成精確事實：同時存在 matching forwarding rule與同名 private hosted zone時，Resolver rule的優先行為；如需例外，使用 SYSTEM rule。
2. 解析列出 `dev.example.com`、`example.com`、`.` 的匹配順序，並說明 packet route只決定能否到 DNS target，不決定使用哪條 Resolver rule。

#### `ch020-q04` — RAM 與 Route 53 Profiles 不是含糊的二選一

Route 53 Profiles可以聚合 Resolver rules等 DNS設定，跨帳號分享 Profile本身仍使用 AWS RAM。現有正解寫成「RAM或Profiles等支援方式」，沒有形成可部署方案；Profiles也是 SAP-C02之後出現的 current-service material，卻未標 enrichment。

修訂動作：

1. 以 SAP-C02 baseline為主：中央 account建立 outbound rule，透過 AWS RAM分享，consumer VPC完成 association。
2. 另列 current enrichment：把 rules加入 Route 53 Profile，透過 RAM分享 Profile並關聯多個 VPC。
3. 加 `ENRICHMENT-CURRENT` 或在 `tested`/解析明示新功能 scope。
4. 解析保留 endpoint ENI、SG、TGW/VPN/DX route與 on-prem DNS conditional forward不會被分享動作自動建立。

#### `ch020-q05` — Task mapping不符合 SAP-C02藍圖

DNS forwarding loop首先是 network connectivity strategy問題，現標 `SAP-3.2` 是「improve security」；題幹沒有安全控制、事件或漏洞修復條件，mapping不成立。

修訂動作：

1. 改映射到 `SAP-1.1`；若題目重寫成 operating procedure、monitoring與持續改善，也可另評估 `SAP-3.1`。
2. 加入 Route 53 Resolver 官方 best-practices／loop prevention 的直接來源，而不只引用一般 rule與query logging頁。
3. 解析展示一個具體 query loop：AWS outbound endpoint → on-prem resolver → AWS inbound endpoint → 重複，並說明應由哪一側成為 authoritative owner。

#### `ch020-q10` — 混淆 inbound與outbound TLS inspection憑證模型

Network Firewall TLS inspection支援 inbound與outbound，但兩者憑證要求不同。Outbound forward proxy通常需要 CA certificate/private key並讓 clients信任該 CA；inbound inspection使用server certificate/private key。題幹只說「內部 TLS API」，現正解 B卻把 CA與client trust寫成通用必要條件，因此不唯一。

修訂動作：

1. 明示流量方向：
   - 若考 outbound forward proxy，題幹寫成內部 clients連外部 TLS服務，正解要求 CA與client trust distribution。
   - 若考 inbound inspection，題幹寫成 clients連公司持有網域的內部 API，正解要求對應 server certificate/private key。
2. 解析分開說明 inbound/outbound certificate requirements、ACM匯入、re-encryption、rotation、certificate pinning與不解密例外。
3. 保留「TLS inspection不取代 IAM/application authentication」。

## Source provenance 修正清單

下列 source ID 回傳 HTTP 200，但實際被導到過大的首頁或 retired目錄，不能視為有效的精確證據：

| Source ID | 影響題目 | 必要動作 |
|---|---|---|
| `aws-ipam-pools` | `ch011-q03`, `ch011-q04`, `ch011-q05` | 換成 pool hierarchy、locale、allocation rules、resource compliance與RAM sharing的現行精確頁面。 |
| `aws-nat-regional` | `ch013-q04` | 換成 `nat-gateways.html#regional-nat-gateway` 與官方發布公告。 |
| `aws-vpc-troubleshooting` | `ch014-q10` | 換成現行 VPC network troubleshooting、Reachability Analyzer與ELB target-health頁面。 |
| `aws-vpn-over-dx` | `ch019-q07` | 換成現行 Direct Connect encryption／VPN overlay文件，不引用 retired whitepaper目錄。 |

`aws-peering-limits` 雖有 redirect，但會落到明確的 VPC peering limitations anchor，可接受。

## Scope 與覆蓋評估

- SAA-C03：VPC、route tables、NAT、endpoints、SG/NACL、Route 53、CloudFront、ELB、VPN/DX等核心範圍覆蓋良好。
- SAP-C02：多帳號網路、TGW route domains、hybrid DNS、centralized inspection、DX resiliency與operating trade-offs有實際情境，不只是服務名稱辨識。
- Current enrichment：
  - `ch013-q04` Regional NAT Gateway：標記正確，修正來源後可保留。
  - `ch020-q04` Route 53 Profiles：必須補 enrichment標記，並把 SAP-C02 baseline的RAM rule sharing與Profiles流程分開。
- Audit intent：除 `ch011-q01`、`ch014-q01`、`ch017-q09`沒有完整落實原 intent外，其餘 intent都有對應題目；部分題目仍因上述事實或defensibility問題需修正。

## Revision gate

修訂代理必須處理以下 23 個 ID，且 reviewer重新核可前不可把 part_01標為 PASS：

`ch011-q01`, `ch011-q03`, `ch011-q04`, `ch011-q05`, `ch011-q10`,
`ch012-q10`,
`ch013-q04`,
`ch014-q01`, `ch014-q10`,
`ch016-q01`, `ch016-q03`, `ch016-q04`, `ch016-q05`,
`ch017-q01`, `ch017-q05`, `ch017-q09`,
`ch019-q06`, `ch019-q07`, `ch019-q08`,
`ch020-q03`, `ch020-q04`, `ch020-q05`, `ch020-q10`.

REVISE

## Verification

再審日期：2026-10-01
再審範圍：修訂後 `tools/aws_question_banks/part_01.json` 全部 100 題，並逐項回查原 review 所列 23 個 revision IDs。

### 結論

原 review 的 23 個修訂要求均已實質處理，沒有只改 schema、答案位置或表面措辭。重新檢查後，每題仍有唯一可辯護答案集合，且未發現修訂引入新的 part_01 blocker。

### 原問題逐項驗證

- **IPAM**
  - `ch011-q01` 已改成具體 `/20` 與 `/21` 容量計算，正確納入每個 subnet保留5個IPv4位址及約3,000個ENI的成長需求。
  - `ch011-q03`、`ch011-q04` 已分開說明 home Region、pool locale、delegated administrator、consumer account與RAM sharing，並改用可直接到達的官方細分頁面。
  - `ch011-q05` 已正確區分 unmanaged resource與managed allocation的compliance狀態，不再宣稱手動建立的VPC直接是noncompliant或會被自動重新編址。
  - `ch011-q10` 已區分IPAM pool allocation、VPC CIDR、subnet CIDR與ENI address；刪除ENI不再被描述成會歸還上層pool prefix。

- **Return path與asymmetric path**
  - `ch012-q10` 已明示舊Peering遭刪除且route為blackhole，因此回程確實不存在，不再把所有非對稱路由一概判定為失敗。
  - 正解同時要求修復DB subnet與TGW route tables，並加入Reachability Analyzer直接官方來源。

- **Regional NAT Gateway**
  - `ch013-q04` 已改用Regional NAT Gateway現行文件、2025-11-18官方發布公告與pricing來源。
  - 題目正確描述regional route target、跨AZ擴展、manual/automatic IP allocation、無須部署於public subnet，以及不接受unsolicited inbound flow。
  - `tested`與解析已明示它是current-service enrichment，不把它冒充SAP-C02原始藍圖的固定答案。

- **Security Group chain**
  - `ch014-q01` 的兩個正解合併後完整形成三層chain：client CIDR→ALB:443、ALB SG→App:8080、App SG→DB:5432。
  - 解析也明確指出SG reference不建立route、NACL不能引用SG ID。
  - `ch014-q10` 已換成Reachability Analyzer、Flow Logs與ALB target health的精確來源。

- **Route 53 fail-open與geolocation**
  - `ch016-q01` 已將Alias A與dual-stack後才需要的Alias AAAA分開。
  - `ch016-q03` 已補上同一routing set全部不健康時Route 53仍可能回傳record的fail-open行為。
  - `ch016-q04` 已補上primary與secondary都不健康時的fallback，並持續區分DNS回答、既有connection與writer fencing。
  - `ch016-q05` 已改為內容在地化情境，說明resolver來源、EDNS0 client subnet、default record，以及geolocation不能單獨充當身分或資料駐留合規控制。

- **CloudFront VPC origins與Functions/Lambda@Edge**
  - `ch017-q05` 已在沒有保留public ALB需求的前提下，選擇internal ALB與CloudFront VPC origin，答案唯一且符合現行origin-isolation能力。
  - `ch017-q09` 已用request body、origin-request event與external HTTP call建立明確邊界；CloudFront Functions與Lambda@Edge不再只用「較輕／較重」區分。
  - Lambda@Edge的body、network、timeout、`us-east-1`與published-version限制已有直接來源與解析。

- **Direct Connect**
  - `ch019-q06` 已把Maximum Resiliency寫成兩個locations、每處兩條connections且終止於不同AWS devices，並和High Resiliency區分。
  - `ch019-q07` 已換成現行MACsec、Direct Connect encryption與private-IP VPN over DX文件，清楚區分Layer 2與Layer 3 encryption。
  - `ch019-q08` 已限定同一VGW、相同prefix、private VIF與dynamic VPN的拓撲，並依longest-prefix、VGW route priority、BGP return-path policy及撤回測試作答。

- **Route 53 Profiles**
  - `ch020-q04` 已把SAP-C02 baseline寫成「RAM分享Resolver rules並由consumer VPC association」。
  - Profiles被清楚標為current enrichment；題目也正確說明Profile透過RAM分享，且不會自動建立outbound endpoint、SG、TGW/DX/VPN route或on-prem conditional forwarding。

- **Network Firewall TLS inspection**
  - `ch020-q10` 已限定為outbound forward-proxy inspection，因此CA certificate/private key、client trust store與rotation要求具有唯一且正確的語意。
  - Certificate pinning、敏感資料與不相容流量的例外，以及TLS inspection不取代IAM/application authorization，也都有明確解析。

- **Resolver precedence與loop**
  - `ch020-q03` 已明確說明最具體suffix、forwarding rule優先於同名private hosted zone，以及SYSTEM rule例外。
  - `ch020-q05` 已呈現具體AWS outbound→on-prem→AWS inbound循環，task mapping改為`SAP-1.1`，並加入Resolver best-practices來源。

- **舊題重疊**
  - `ch017-q01` 已改成distribution ID、CloudFront service principal、`AWS:SourceArn`、REST endpoint與website endpoint的policy判斷題。
  - 再次比對 `aws_architect_deep_content.py` 後，part_01沒有達到原先近似門檻的prompt或choice，也未發現舊五題模板的stock distractors。

### 回歸與來源檢查

- 100題、10章、每章10題、intent 1–10各一次。
- 80題單選、20題複選；choice數量、answer index、逐選項解析與答案位置分布均符合契約。
- 120個official sources與8個community sources均可解析；本次修訂新增的關鍵官方URL均直接回傳有效頁面。
- 未發現同題重複choice、跨題重複prompt、缺少official source或dump-like來源。
- 全書audit validator通過。全書question-bank validator目前仍回報其他parts的問題，但沒有任何訊息指向`part_01.json`，不影響本次part_01驗證結論。

VERIFIED
