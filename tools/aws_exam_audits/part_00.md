# P00 Audit：第 1–10 章考點與題目藍圖

## 稽核範圍與判準

- 稽核來源：`aws_architect_topics_01.py`、`aws_architect_profiles.py`、`aws_architect_setting_guides.py`、`aws_architect_deep_content.py` 的題目產生器，以及生成後 HTML 的第 1–10 章。
- 本文件只提出原創題目意圖，不使用、改寫或暗示任何真實考題／exam dump。
- 每章恰好十個題目意圖，依序覆蓋：purpose、mechanism、concrete setting、data/request flow、failure diagnosis、comparison、cost/operations、SAA scenario、SAP expansion、multi-response。
- `task` 使用本專案 `aws_architect_model.py` 中的官方考試 task key；`source` 使用同檔案 `SOURCES` 的官方來源 key。

## 跨章共同缺陷

1. 目前每章只有五題，且除少數 special cases 外，全由同一組 selection/config/mechanism/SAA/SAP 模板產生；題目數量、技能面與情境變化都不足。
2. 產生器固定把 `components(topic)[0]` 當 primary component。概念章因此被迫選一個 AWS 服務當正解，造成「章旨」與「產品選型」錯位。
3. 「哪一段描述 primary component 在 request/data path 的底層機制」不適用於 Certification、Well-Architected Tool、Well-Architected Framework、Shared Responsibility Model 等 control／governance 概念。
4. 多個單選題同時放入兩個正確原則，再以「比較直接」為理由只標一個答案；題幹沒有足夠 constraint 排除另一個答案，屬實質歧義。
5. 干擾項大量使用「自動理解所有 business requirements」「把所有服務都部署」「先給 organization-wide AdministratorAccess」等顯然錯誤句。這類選項不 plausible，不能訓練真實的服務邊界判斷。
6. 第五題在所有章節重複 multi-account、canary、rollback、AdministratorAccess、空 standby 等固定文字；它沒有測到各章專屬的 SAP 深度。
7. `_calibrate_questions()` 以長篇固定 boilerplate 補足解析字數，增加重複資訊，卻沒有補上具體設定、資料流、限制數值或失效診斷。
8. Setting guide 的 generic classifier 會誤分類詞彙。例如第 10 章 `high-risk issues` 被解釋成 data-model key/index 問題；第 1 章 Well-Architected Tool 的 `Regions` 被寫成部署服務與 KMS/AMI 的 Region 設定，而不是 workload metadata。
9. 生成後 HTML 的第 1–10 章都只有五個 `.chapter-exam-question`。沒有題型層級的唯一性檢查，也沒有防止語意重複或多個正解的 validation。
10. 第 1–10 章的 source mapping 幾乎只用 exam guide、Well-Architected 與 community index；compute、network、storage、database、Route 53 等產品題缺少對應產品官方 source key，難以做逐項 factual audit。

---

## 第 1 章：如何使用本書與雙證地圖

### 目前缺陷

- 把 AWS Certification 與 AWS Well-Architected Tool 當成互斥的架構服務，但前者是能力驗證藍圖，後者是 workload review 工具，沒有合理的「選 A 不選 B」產品競爭關係。
- 第 3 題宣稱 Well-Architected Tool 位於 request/data path，分類錯誤；它是 review/control-plane workflow，不處理應用請求。
- 第 4 題以「最少營運負擔」為題，卻直接選 Well-Architected Tool，沒有說明需求是 architecture review、風險追蹤或 workload improvement。
- `Regions` setting guide 把 Tool 內的 workload Region metadata 誤寫成實際部署 Region、KMS keys、AMI 與 replication destination 設定。
- 五題中四題仍在反覆測「requirements first」，沒有真正測 exam guide、domain、task、題幹限制詞、複選規則、錯題分類與 review milestone。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 給一題同時提到最低成本、低延遲與資料駐留的情境，問考生第一步應做什麼。 | 先把 hard constraints、優化目標與「MOST／LEAST」限制詞分開，再比較方案。 | 先列所有可能服務；先選最熟悉服務；先按單一 pillar 最佳化。 | `SAA-2.1` / `saa-guide` |
| 2 | Mechanism | 問 exam domain、task statement 與產品文件各自負責什麼。 | Domain/task 定義被測能力與範圍；產品行為與限制仍以產品官方文件為準。 | Task 是固定題庫；in-scope list 是完整產品規格；community notes 可取代官方文件。 | `SAP-2.4` / `sap-guide` |
| 3 | Concrete setting | 給一份兩週讀書計畫，問 coverage matrix 至少要記錄哪些欄位。 | 記錄 exam code/version、task、錯題率、hard constraint、正解機制、翻轉條件與官方來源。 | 只記服務名稱；只按章節頁數；只記模考總分。 | `SAA-2.1` / `saa-guide` |
| 4 | Data/request flow | 給一個 Well-Architected review 流程，問正確順序。 | 定義 workload/owner → 選 lenses/回答 questions → 辨識 risks → 指派 improvements → 建 milestone 驗證進展。 | Tool 自動掃描後直接修復；先建 milestone 再定義 workload；review 結果可直接證明 data plane 正常。 | `SAP-2.4` / `well-architected` |
| 5 | Failure diagnosis | 學員服務題答對率高但 scenario 題持續失分，問最可能的診斷與修正。 | 錯因應按 task 與 constraint 分類，補「為何不選 B/C/D」及答案翻轉條件。 | 再背更多服務縮寫；只重做同一批題；只提高答題速度。 | `SAA-2.2` / `saa-guide` |
| 6 | Comparison | 比較官方 sample questions、原創 mock、產品文件與 exam dump 的用途。 | Sample 校準題型，mock 驗證遷移能力，產品文件查事實；exam dump 不應使用。 | Sample 可預測正式題分布；mock 可取代產品文件；dump 是最高品質學習素材。 | `SAA-2.1` / `saa-guide` |
| 7 | Cost/operations | 時間只剩十天，問如何分配複習成本。 | 以「官方權重 × 個人錯題率 × 先備依賴」排序，保留跨 domain 模考與回讀時間。 | 平均分配每章；只讀最高權重 domain；只做題不回讀。 | `SAA-2.1` / `saa-guide` |
| 8 | SAA scenario | 題幹要求「MOST cost-effective 且 least operational overhead」，兩個方案皆可用，問如何選。 | 先排除未滿足硬條件者，再比較 recurring cost、管理責任與 failure mode，而非功能數量。 | 永遠選 serverless；永遠選 managed service；永遠選月費最低者。 | `SAA-2.1` / `saa-guide` |
| 9 | SAP expansion | 多帳號 migration 題加入 audit、rollback、owner 與 blast radius，問答案需要增加哪些面向。 | 除技術服務外，納入 delegated ownership、guardrails、分波 rollout、rollback evidence 與 operating model。 | 只增加第二 Region；只升級 enterprise support；只把所有權集中到 management account。 | `SAP-2.4` / `sap-guide` |
| 10 | Multi-response | 選兩項：哪些做法能證明讀者不是背答案，而是真的理解 architecture trade-off。 | 正解應為「逐項解釋 distractor 的缺口」與「指出 constraint 改變時答案如何翻轉」。 | 背正確選項字首；記住服務出現頻率；以價格高低猜答案。 | `SAA-2.2` / `saa-guide` |

---

## 第 2 章：Cloud、Region、AZ 與 Edge

### 目前缺陷

- 章節同時涵蓋 Region、AZ、CloudFront 與 Global Accelerator，但現有五題幾乎只測 Region，edge 服務選型沒有被實質覆蓋。
- 第 1 題的需求包含台灣使用者低延遲與資料留在指定 Region，答案只說 Region/AZ/edge 的定義，沒有提出可執行架構。
- 第 4 題問「最少營運負擔」，正解卻是「選 AWS Regions 並設定 Region 選擇」，不是完整方案。
- `subnet AZ`、`Multi-AZ`、`cross-AZ cost` 等 setting guides 被 generic rule 寫成同一段 Region/AZ matrix 文字，沒有解釋具體行為。
- 未測 CloudFront cache/proxy 與 Global Accelerator anycast/TCP/UDP 的差異，也未測資料不會因使用 edge 自動離開 origin Region 的邊界。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 問 Region、AZ、edge location 各解決哪一層問題。 | Region 是地理/服務邊界，AZ 是 Region 內故障域，edge 是靠近使用者的入口或快取點。 | AZ 是跨國地理邊界；edge 是資料庫 primary；Region 內所有服務自動跨 AZ。 | `SAA-3.4` / `well-architected` |
| 2 | Mechanism | 全球使用者讀取靜態物件，問 CloudFront 正常 cache hit/miss 如何運作。 | DNS 導向 edge；hit 直接回應，miss 依 behavior/policy 回 origin，物件依 TTL/cache key 重用。 | 每次都回 origin；edge 把 origin database 複寫成多主；Global Accelerator cache HTTP objects。 | `SAA-3.4` / `cloudfront` |
| 3 | Concrete setting | 問哪些 CloudFront 設定決定相同 URL 是否共用 cache object。 | Cache policy 中的 headers/cookies/query strings 與 TTL 決定 cache key 和新鮮度。 | Origin request policy 單獨決定 cache key；security group；Route 53 health-check interval。 | `SAA-3.4` / `cloudfront` |
| 4 | Data/request flow | 低延遲但資料不得離開指定 Region，問 viewer、edge、origin 與資料位置關係。 | Edge 可代理/快取允許的回應；authoritative data 與 origin 仍留指定 Region，需按資料分類控制可快取內容。 | 使用 edge 必然把 database 移出 Region；Multi-AZ 等於全球 edge；低 TTL 會把內容快取到 edge。 | `SAA-1.3` / `cloudfront` |
| 5 | Failure diagnosis | 同 Region 三台 EC2 都在一個 AZ，AZ 事故全掛，問根因。 | Instance 數量不是 failure-domain 數量；應跨至少兩個 AZ 放置並確保 state/dependencies 也跨 AZ。 | 增加同 AZ instance size；降低 DNS TTL；改用單一更大 subnet。 | `SAA-2.2` / `well-architected` |
| 6 | Comparison | 全球遊戲 UDP 要固定 IP；網站靜態內容要 cache/WAF，問各選什麼。 | UDP/static anycast IP 用 Global Accelerator；HTTP cache與 edge security 用 CloudFront。 | 兩者都只做 DNS；CloudFront 加速任意 UDP；Global Accelerator 提供 object cache。 | `SAA-3.4` / `cloudfront` |
| 7 | Cost/operations | 問何時 Multi-Region 不應取代 Multi-AZ。 | 只需抵抗 AZ 故障時先用 Multi-AZ；Multi-Region 增加資料複寫、治理、測試及傳輸成本。 | Multi-AZ 可抵抗任何 Region outage；單 AZ 加 backup 等於 HA；跨 Region 沒有資料傳輸成本。 | `SAA-2.2` / `well-architected` |
| 8 | SAA scenario | 區域性電商要求 AZ 故障不中斷、低管理負擔、資料不跨 Region。 | 在單一合規 Region 採 Multi-AZ compute/load balancing 與相符的 Multi-AZ data tier。 | 單 AZ ASG；兩個 Region 各一台但無資料同步；只加 CloudFront。 | `SAA-2.2` / `well-architected` |
| 9 | SAP expansion | 跨 Region active/passive 設計問切換前必須驗證什麼。 | 驗證資料 lag、KMS/identity、quota、依賴、DNS/entry point、capacity、runbook、failover/failback game day。 | 只驗證第二 Region 有空資源；只降低 TTL；只複製 AMI。 | `SAP-1.3` / `sap-d1` |
| 10 | Multi-response | 選兩項：資料駐留且全球低延遲網站的正確控制。 | 正解為「origin/authoritative data 留核准 Region並分類可快取內容」及「以 CloudFront edge 快取非敏感靜態內容」。 | 將所有敏感 response 設長 TTL；以 GA 取代 database replication；假設 edge 不受資料分類政策影響。 | `SAP-1.1` / `cloudfront` |

---

## 第 3 章：Server、VM、Container 與 Serverless

### 目前缺陷

- 第 1 題同時有「依控制需求選抽象層」與「EC2/container/serverless 各自適用情境」兩個合理答案，單選不成立。
- 因 Amazon EC2 排第一，設定題、機制題與 SAA 題都偏向 EC2，ECS、EKS、Fargate、Lambda 的核心邊界未覆蓋。
- 第 4 題明示「最少營運負擔」卻選 EC2，和 EC2 需要管理 guest OS/patching/capacity 的事實衝突。
- 未測 ECS task role 與 execution role、EKS control plane 與 worker responsibility、Fargate 與 scheduler 的關係。
- 未測 Lambda timeout、concurrency、cold start、event source、idempotency 與長時間工作限制；成本題也沒有 steady/bursty utilization 比較。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 問選 compute abstraction 的第一組決策條件。 | 以 OS/driver 控制、封裝需求、執行時間、事件模型、可攜性與營運能力選擇。 | 只按語言；只按資料量；永遠選抽象最高者。 | `SAA-3.2` / `compute` |
| 2 | Mechanism | 問 ECS service、task definition 與 Fargate 分別做什麼。 | ECS 是 scheduler/control plane；task definition 描述 workload；Fargate 提供不需管理 nodes 的執行容量。 | Fargate 取代 container image；ECS 是 VM hypervisor；task definition 自動建立 application data store。 | `SAA-3.2` / `containers` |
| 3 | Concrete setting | 問 ECS `taskRoleArn` 與 `executionRoleArn` 的正確分工。 | Task role 給應用程式呼叫 AWS API；execution role 給 ECS agent 拉 image、寫 logs 等平台動作。 | 兩者完全相同；execution role 給終端使用者；task role 只控制 security group。 | `SAA-1.1` / `containers` |
| 4 | Data/request flow | API Gateway 觸發 Lambda 寫 DynamoDB，問 request 與 credentials 流程。 | Event 進 execution environment；函式以 execution role 的 temporary credentials 呼叫 DynamoDB；回應經 API 層返回。 | Lambda 使用部署者 access key；execution environment 是 durable queue；把函式放 VPC 才能呼叫任何 AWS API。 | `SAA-3.2` / `lambda` |
| 5 | Failure diagnosis | Lambda 高峰出現 throttling、下游 DB 飽和，問如何診斷。 | 檢查 concurrency、reserved concurrency、duration、arrival rate 與下游 capacity；限制/緩衝流量而非只提高上限。 | 只增加 memory；取消所有 concurrency 限制；改成同數量 EC2 即自然解決。 | `SAA-3.2` / `lambda` |
| 6 | Comparison | 已有 Kubernetes operators 與 portable manifests，和只需簡單 container scheduler 的兩個團隊如何選。 | 需要 Kubernetes API/ecosystem 選 EKS；不需要其複雜度時 ECS 較低營運負擔。 | EKS 永遠較便宜；ECS 可直接執行 Kubernetes CRD；Fargate 本身是另一個 orchestrator。 | `SAA-3.2` / `containers` |
| 7 | Cost/operations | 比較穩定 24×7 高利用 container 與偶發短任務的執行成本。 | 穩定高利用可評估 EC2-backed fleet/commitment；bursty、低 duty cycle 可用 Fargate/Lambda 降低 idle 與 node operations。 | Serverless 永遠最低價；EC2 永遠最低價；只比較每 vCPU 單價不計 idle/ops。 | `SAA-4.2` / `compute` |
| 8 | SAA scenario | 長時間 Java daemon 需 OS agent；圖片上傳後做 20 秒縮圖，問組合。 | Daemon 用 EC2 或 container on suitable capacity；縮圖用 event-driven Lambda，分別滿足控制與 burst。 | 兩者全用 Lambda；兩者全用 dedicated hosts；圖片縮圖用 EKS 只因可攜。 | `SAA-3.2` / `lambda` |
| 9 | SAP expansion | 大型 container 平台跨帳號，問 operating model。 | 分離平台與應用 ownership，標準化 image supply chain、identity、network policy、capacity、upgrade waves、quota與 rollback。 | 所有 cluster 共用 admin role；每隊任意建立 control plane；只用第二 Region 當治理方案。 | `SAP-4.4` / `containers` |
| 10 | Multi-response | 選兩項：Fargate workload 仍由 customer 負責的事項。 | 正解為「設定 task CPU/memory/network/IAM」與「維護 application/container image 與資料安全」。 | Patch underlying host；配置 hypervisor；管理 Fargate capacity server fleet。 | `SAP-2.5` / `containers` |

---

## 第 4 章：IP、CIDR、Subnet 與 Route 基礎

### 目前缺陷

- 第 3 題的 Amazon VPC 整體流程與 route-table longest-prefix 描述都正確，卻只標其中一個答案。
- 題目沒有出現任何具體 CIDR 計算、route table rows、destination/target 或 longest-prefix 例子，初學者無法把抽象描述映射到實務。
- 重疊 CIDR 情境只回答「應規劃不重疊」，沒有處理既成重疊環境的 renumber、PrivateLink、proxy/NAT workaround 邊界。
- 未測 subnet 是單 AZ、route-table association、local route、去回程、stateful device 對稱路徑與 blackhole。
- 第 4 題以「最少營運負擔」選整個 Amazon VPC，沒有可比較的網路方案，也沒有滿足題幹的具體 route。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 問 VPC、subnet、route table 的責任邊界。 | VPC 定義 regional address/routing domain；subnet 是單 AZ 位址與 association 邊界；route table 選 next hop。 | Subnet 跨所有 AZ；route table 是 firewall；VPC CIDR 自動全球唯一。 | `SAA-3.4` / `network` |
| 2 | Mechanism | 給 `10.0.0.0/16`，問切成 `/20` 的子網數與每個範圍大小的概念。 | Prefix 多 4 bits 可切 16 個 `/20`；每個 `/20` 共 4096 addresses，另須考慮 AWS 保留地址。 | `/20` 比 `/16` 大；可切 4 個；所有 4096 都可配置給 ENI。 | `SAA-3.4` / `network` |
| 3 | Concrete setting | 給 route table：`10.0.0.0/16 local`、`10.20.0.0/16 tgw`、`0.0.0.0/0 nat`，問到 `10.20.3.4` 的 next hop。 | Longest-prefix match 選 `10.20.0.0/16 → tgw`，不是 default route。 | 一律選最先建立；一律選 local；NAT 優先於較精確 route。 | `SAA-3.4` / `vpc-route-tables` |
| 4 | Data/request flow | App subnet 呼叫 on-prem DB，要求畫出 forward 與 return route。 | App route 指向 TGW/VPN/DX；on-prem 必須有回到 VPC CIDR 的 route，途中 policy/stateful devices 都需允許。 | 只需 AWS 去程；DNS 成功即代表路由完成；SG 可替代缺少的 return route。 | `SAP-1.1` / `network` |
| 5 | Failure diagnosis | 新增更精確 route 後流量進 blackhole，問根因與檢查順序。 | 檢查 effective route、target/attachment 狀態、association、propagation 與 return path；更精確 blackhole 會勝過 default。 | 只重啟 EC2；提高 NACL rule number；降低 DNS TTL。 | `SAA-3.4` / `vpc-route-tables` |
| 6 | Comparison | 比較 route table、security group 與 NACL。 | Route 決定去哪裡；SG 是 ENI 級 stateful allow；NACL 是 subnet 級 stateless ordered allow/deny。 | SG 選 next hop；route table 驗證 IAM；NACL 自動允許回程。 | `SAA-1.2` / `network` |
| 7 | Cost/operations | 多帳號地址規劃問為何預留與集中 IPAM 比事後重編址便宜。 | 不重疊、分層可聚合的 CIDR 降低 peering/TGW/hybrid 路由與 migration 重編址成本。 | 每個 VPC 都用同一 `/16` 最簡單；CIDR 越大永遠越好；NAT 可無成本解決所有 overlap。 | `SAA-4.4` / `network` |
| 8 | SAA scenario | 兩個新 VPC 未來要互連，問 CIDR 與 subnet 規劃。 | 選不重疊 CIDR，依 AZ 切 subnet，預留成長並明確關聯 route table。 | 先重疊再用 SG 分流；一個 subnet 跨三 AZ；只靠名稱 public/private。 | `SAA-3.4` / `network` |
| 9 | SAP expansion | 併購後大量重疊 CIDR，且只需存取中央 API，問可行遷移策略。 | 不建立全網互通；以 PrivateLink/application proxy 暴露特定服務，並制定分階段 renumber 計畫。 | 強行 TGW propagate 全部 routes；假設 longest-prefix 能辨識相同 CIDR；建立更多 peering。 | `SAP-1.1` / `network` |
| 10 | Multi-response | 選兩項：private subnet instance 對外 timeout 時最先驗證的網路事實。 | 正解為「subnet route 的 next hop/target 狀態」與「回程及 SG/NACL/stateful path」。 | IAM user 密碼；S3 object versioning；EC2 purchase option。 | `SAP-2.5` / `vpc-route-tables` |

---

## 第 5 章：DNS、TCP、TLS 與 HTTP

### 目前缺陷

- 第 1 題的分層診斷方向合理，但沒有具體工具輸出、錯誤碼或層級證據，無法訓練判讀。
- 第 4 題問如何以最少營運負擔處理分層問題，卻只選 Route 53 設定；DNS 無法單獨解決 TCP、TLS 或 HTTP 故障。
- 未測 Route 53 Alias/CNAME/TTL、public/private hosted zone、ACM certificate Region/validation，以及 ELB listener/target group/health check。
- 未區分 DNS answer、TCP three-way handshake、TLS hostname/certificate validation、HTTP status 與 ALB 502/504 的責任。
- 現有題目只有服務敘述，沒有可操作的 `dig`、連線、certificate、listener、health path 或 log 診斷情境。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 問 DNS、TCP、TLS、HTTP 各解決什麼。 | DNS 找位址，TCP 建可靠連線，TLS 提供加密/身份，HTTP 表達應用 request/response。 | DNS 授權 AWS API；TLS 選 route；HTTP 保證封包可靠送達。 | `SAA-3.4` / `route53` |
| 2 | Mechanism | 問 Route 53 hosted zone、resolver 與 routing policy 的互動。 | Hosted zone 保存權威 records；resolver 查詢/cache；policy 在 DNS 回答階段選 record，不代理後續流量。 | Route 53 逐 HTTP request proxy；TTL 是 health-check interval；resolver 保存 application session。 | `SAA-3.4` / `route53` |
| 3 | Concrete setting | Zone apex `example.com` 要指向 ALB，問 record 設定。 | 使用 Route 53 A/AAAA Alias 指向 ALB；不手抄動態 IP，也不在 apex 使用一般 CNAME。 | Apex CNAME；固定 A record 指向某台 target IP；MX record 指向 ALB。 | `SAA-3.4` / `route53` |
| 4 | Data/request flow | 要求排列 browser 到 ALB app 的完整路徑。 | DNS resolution → TCP connection → TLS handshake/certificate validation → HTTP request → listener rule → target health/response。 | TLS 在 DNS 前；ALB health check 由 browser 執行；Route 53 傳送 HTTP body。 | `SAP-1.1` / `network` |
| 5 | Failure diagnosis | dig 查詢正常、TCP 443 可達，但 browser 報 certificate name mismatch，問故障層與修正。 | TLS identity 層；certificate SAN 必須涵蓋 hostname，並在正確 endpoint/Region 關聯。 | DNS TTL；target-group health path；NACL ephemeral port 一定是唯一原因。 | `SAA-1.2` / `route53` |
| 6 | Comparison | 比較 TCP health check 與 HTTP health check。 | TCP 只證明 port 接受連線；HTTP 可驗證 path/status，更接近應用可服務性但依賴更深。 | TCP 可驗證回應內容；HTTP 不需成功 TCP/TLS；兩者都能證明 database transaction 成功。 | `SAA-2.2` / `network` |
| 7 | Cost/operations | 問低 TTL 的取捨。 | 低 TTL 可縮短部分 resolver cache，但增加查詢量且不終止既有 connections；切換前應提前降低。 | TTL=0 保證瞬時 failover；TTL 越低 application latency 必然越低；Alias 可自訂任意 TTL。 | `SAA-4.4` / `route53` |
| 8 | SAA scenario | Public HTTPS app 用 ALB，要求自動 certificate renewal 與健康 target 分流。 | ACM certificate 關聯 HTTPS listener，listener/rules 導向有適當 HTTP health check 的 target group。 | Route 53 record 直接保存 private key；只做 TCP health check 即證明完整業務；certificate 裝在每個 client。 | `SAA-1.2` / `network` |
| 9 | SAP expansion | 多 Region API 切換後部分使用者仍到舊站，問完整原因與設計。 | 考慮 resolver/client cache、舊 TTL、既有 connections、health signal、session/data state，並做分階段 cutover/rollback。 | 只把 TTL 改成 1 秒；只增加 ALB targets；把 DNS 當精準 request-level traffic splitter。 | `SAP-2.5` / `route53` |
| 10 | Multi-response | 選兩項：ALB 回 502 時最有價值的證據。 | 正解為「ALB access log/target error」與「target port/protocol/application response 是否符合 listener/health 設定」。 | Route 53 domain registration expiration一定是原因；增加 TTL；更換 client DNS resolver 即可。 | `SAP-2.3` / `network` |

---

## 第 6 章：Block、File 與 Object Storage

### 目前缺陷

- 第 1 題的「Block/file/object 定義」與「database/file/static content 的具體映射」皆正確，只標前者，單選歧義明顯。
- 第 4 題在一個同時需要三種 storage semantics 的情境中只選 EBS，無法滿足共享檔案與十年 object archive。
- 題庫因 primary component 偏向 EBS，未測 EFS mount target/access point/throughput、FSx engine/protocol、S3 key/object/versioning/lifecycle。
- EBS 描述容易讓初學者誤解為永遠只能單機；需說明典型用途、AZ attachment，以及 Multi-Attach 仍要求支援的 volume/instance/cluster-aware filesystem。
- 未測 EBS snapshot、EFS One Zone/Regional、S3 storage class/retrieval、資料遷移與每 GB/IOPS/throughput/request 成本模型。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 問 block、file、object 的 interface/semantics 差異。 | Block 提供 sectors/device；file 提供共享目錄/POSIX或SMB語意；object 以 key/API 讀寫完整物件。 | 三者只差容量；S3 是一般 POSIX disk；EBS 自帶跨主機共享目錄。 | `SAA-3.1` / `storage` |
| 2 | Mechanism | 問 EBS volume 與 snapshot 的位置及關係。 | Volume 位於單一 AZ並網路附加；snapshot 是增量 recovery point，儲存在 regional managed infrastructure，可用來在 AZ 建新 volume。 | Snapshot 是可直接 mount 的共享 filesystem；volume 自動跨 Region；snapshot 只保存 filesystem metadata。 | `SAA-3.1` / `storage` |
| 3 | Concrete setting | Database 需要 12k IOPS、500 MiB/s，問 gp3 設定思路。 | Volume size、IOPS、throughput 是分開的 workload requirements，需確認 volume/type 與 instance throughput limits。 | 只增加容量必然得到任意 IOPS；st1 適合低延遲 random OLTP；EFS throughput mode 控制 EBS。 | `SAA-3.1` / `storage` |
| 4 | Data/request flow | 多 AZ Linux app 讀寫 EFS，問 client 到 storage 的路徑。 | Client 經該 AZ mount target 使用 NFSv4.1；SG、DNS/mount target、access point/POSIX identity 共同影響存取。 | EFS 經 S3 REST API；所有 client 共用 EBS attachment；mount target 是 backup copy。 | `SAA-3.1` / `storage` |
| 5 | Failure diagnosis | EC2 moved 到另一 AZ 後原 EBS 無法直接 attach，問原因與恢復。 | EBS volume 有 AZ affinity；從 snapshot 在目標 AZ 建 volume，或重新設計資料層，不是只改 route。 | Security group 是唯一原因；降低 DNS TTL；把 volume ARN 改成新 AZ。 | `SAA-2.2` / `storage` |
| 6 | Comparison | Windows SMB/AD、Linux NFS、HPC Lustre 與 object archive 分別如何選。 | FSx Windows、EFS、FSx Lustre、S3/Glacier 依 protocol 與 access semantics 選擇。 | 全部用 EBS；全部用 S3 mount；只按容量選最便宜服務。 | `SAA-3.1` / `storage` |
| 7 | Cost/operations | 問十年保存、每年讀一次的大量 objects 應考慮什麼。 | S3 lifecycle 到合適 archive class，納入 minimum duration、retrieval latency/fees、request 與 restore workflow。 | 只比較每 GB 月租；EBS sc1 永遠最便宜；把所有資料直接刪除後依 replication 恢復。 | `SAA-4.1` / `s3` |
| 8 | SAA scenario | 一題同時有 OLTP disk、共享模型檔、影像 archive，問三項映射。 | OLTP 用合適 EBS；共享 Linux files 用 EFS/適合 FSx；影像 object/archive 用 S3 lifecycle。 | 單一 S3 bucket 模擬全部 POSIX；單一 EBS 跨 AZ 給所有 servers；EFS 作冷 archive。 | `SAA-3.1` / `storage` |
| 9 | SAP expansion | Petabyte NAS 遷移到 AWS，應用暫不能改 protocol，問階段策略。 | 先依 SMB/NFS/ONTAP/Lustre 語意選 EFS/FSx 與 DataSync 等遷移路徑，再逐步把適合內容轉 object；驗證 ACL、cutover、rollback。 | 直接改成 S3 而不測語意；用 snapshots 搬 on-prem NAS；只估算容量不看 metadata/throughput。 | `SAP-2.5` / `storage` |
| 10 | Multi-response | 選兩項：S3 不應被當成一般 POSIX filesystem 的原因。 | 正解為「object key/API、PUT 取代完整 object」與「沒有一般 filesystem 的 in-place append/rename/locking contract」。 | S3 不耐久；S3 只能單 AZ；S3 不支援任何 encryption。 | `SAP-2.6` / `s3` |

---

## 第 7 章：Relational、NoSQL、Cache 與 Warehouse

### 目前缺陷

- 第 1 題的「先列 access patterns」與「polyglot persistence」都可合理回答混合工作負載，只標前者，constraint 不足。
- 第 4 題要求最少營運負擔，卻固定選 RDS；原 scenario 明確包含 transaction、session cache 與多年 analytics，單一 RDS 不是完整答案。
- 五題主要測 RDS 設定/機制，Aurora、DynamoDB、ElastiCache、Redshift 幾乎只是干擾項。
- 未測 RDS Multi-AZ vs read replica、Aurora endpoints/shared storage、DynamoDB partition key/GSI/consistency、cache invalidation、Redshift MPP/columnar。
- 沒有資料流、hot partition、replica lag、cache stampede、OLTP/OLAP 隔離或 cost model 題。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 問資料服務選型前最重要的輸入。 | 先列 read/write access patterns、transaction/consistency、latency、scale、retention 與 query shape。 | 只看資料總量；只看團隊熟悉語言；只選功能最多 database。 | `SAA-3.3` / `database` |
| 2 | Mechanism | 問 RDS Multi-AZ 與 read replica 的底層目的差異。 | Multi-AZ 主要提供同步/受管 failover HA；read replica 主要用非同步 replication 擴讀並有 lag。 | Multi-AZ 自動分攤所有 reads；read replica 保證零 RPO；兩者都只是 backup。 | `SAA-2.2` / `database` |
| 3 | Concrete setting | DynamoDB 訂單查詢需要依 customer 列出時間範圍，問 key design。 | 以 customer/tenant 作高基數 partition key，時間/訂單作 sort key；額外 access pattern 才設計 GSI。 | 單一常數 partition key；以 Scan 配 FilterExpression 取代 key；每個 query 都新建 table。 | `SAA-3.3` / `dynamodb` |
| 4 | Data/request flow | 問 cache-aside read miss 的流程。 | App 先查 cache；miss 查 authoritative DB，再以 TTL 寫 cache；更新需定義 invalidation/consistency。 | Cache 自動攔截所有 DB request；cache 是唯一 durable truth；TTL 等於 database transaction timeout。 | `SAA-3.3` / `database` |
| 5 | Failure diagnosis | DynamoDB 整體容量充足但單一 tenant throttled，問根因。 | Hot partition/key distribution；需重設 key/sharding、隔離 noisy tenant 或調整 access pattern，而非只看 table aggregate。 | RDS failover；DNS propagation；Redshift sort key。 | `SAA-3.3` / `dynamodb` |
| 6 | Comparison | 比較 Aurora/RDS、DynamoDB、ElastiCache、Redshift 的 authoritative role。 | Transactional relational、key-based operational store、non-authoritative in-memory acceleration、columnar analytics 各有不同責任。 | ElastiCache 取代所有 backups；Redshift 作低延遲 OLTP；DynamoDB 擅長任意 ad hoc joins。 | `SAA-3.3` / `database` |
| 7 | Cost/operations | 偶發每月一次查 S3 歷史資料與每日高併發 BI dashboard，問成本取捨。 | 偶發 serverless query 可評估 Athena；固定複雜 warehouse/dashboard 可用 Redshift並優化資料布局/容量。 | 一律 provision 最大 Redshift；一律把分析放 primary RDS；只看 storage 單價。 | `SAA-4.3` / `database` |
| 8 | SAA scenario | 訂單需 ACID、session 低延遲、分析掃多年事件，問組合。 | RDS/Aurora 作訂單 truth，ElastiCache 作 session/cache，Redshift/Athena 作分析；同步管線需明確。 | 全部塞 Redis；全部用 primary RDS；只用 DynamoDB Scan 做 warehouse。 | `SAA-3.3` / `database` |
| 9 | SAP expansion | 單體 database 拆成 polyglot stores，問 migration controls。 | 先定 authoritative owner、dual-write/CDC、schema/version、reconciliation、cutover/rollback 與 data quality evidence。 | 永久無監控 dual-write；一次 big-bang 切換；各 store 任意互相寫。 | `SAP-4.3` / `database` |
| 10 | Multi-response | 選兩項：cache stampede 的有效緩解。 | 正解為「TTL jitter/request coalescing或single flight」與「保護 DB 的 rate limit/backpressure並監控 hit ratio/evictions」。 | 所有 key 同秒過期；取消 TTL；把 cache 當唯一資料來源。 | `SAP-2.5` / `database` |

---

## 第 8 章：Availability、Durability、Scalability 與 Elasticity

### 目前缺陷

- 第 1 題的定義選項與「副本仍不能取代 backup/隔離」都正確，但題幹未要求只選定義，存在多解。
- 因 Amazon S3 排第一，設定與機制題轉而測 bucket config/object mechanism，偏離本章四個非功能屬性的核心。
- 第 4 題選 Amazon S3 無法解決 service availability、compute scalability 或五分鐘內十倍流量。
- 未要求讀者以 SLI/SLO、durability loss probability、tested capacity、scale-out time 等可測量方式區分四個名詞。
- 未測 ASG 與 ELB 分工、target tracking/warmup、state bottleneck、backup/replication/HA 的差異，以及「可擴展但不具彈性」情境。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 以四個具體 business statements 辨識 availability、durability、scalability、elasticity。 | 可服務比例、資料不遺失、可承受上限、容量調整速度是四個不同屬性。 | 四者皆等於 high availability；durability 是低 latency；elasticity 是固定最大容量。 | `SAA-2.2` / `reliability` |
| 2 | Mechanism | 問 ASG 與 ELB 如何共同提升 availability/elasticity。 | ASG 維持/調整 healthy instances；ELB 將流量送到 healthy targets，兩者責任互補。 | ELB 建立 EC2 capacity；ASG 代理每個 HTTP request；任一服務單獨保證 data durability。 | `SAA-2.2` / `compute` |
| 3 | Concrete setting | 問 target tracking policy 的 metric、target、min/max、warmup 如何影響 scale。 | 選能代表需求的 metric，設定可達 target 與 headroom，正確 warmup 防止過度擴縮，min/max 限制邊界。 | 只設 max 即自動最佳化；用總 requests 而不正規化 capacity；warmup 越短永遠越好。 | `SAA-3.2` / `compute` |
| 4 | Data/request flow | 促銷 request 進 ALB、ASG、stateless app、database，問哪裡可能阻止水平擴展。 | Frontend 可 scale-out，但 session/local disk、DB connections/hot keys 與同步 downstream 仍可能是 state bottleneck。 | ALB 會自動 scale database schema；增加 app instances 必然線性增加 throughput；S3 versioning 解決 DB connection limit。 | `SAA-2.1` / `reliability` |
| 5 | Failure diagnosis | ASG 已擴到 max 但 p99/5xx 仍升高，問診斷順序。 | 檢查 scaling signal、instance warmup/health、downstream saturation、quota與 load-test ceiling，不盲目再加 capacity。 | 把 S3 durability 提高；降低 DNS TTL；只重啟一台 instance。 | `SAP-3.4` / `reliability` |
| 6 | Comparison | 比較 replication、backup、Multi-AZ 與 Auto Scaling。 | Replication/HA改善持續服務，backup處理時間點恢復，ASG處理 compute capacity/replacement；不可互相取代。 | Replica 天然防錯刪；backup 自動接管流量；ASG 保證 RPO=0。 | `SAA-2.2` / `reliability` |
| 7 | Cost/operations | 問預先佈署峰值容量與自動擴縮的取捨。 | 依 warm-up、峰值可預測性、SLO 與下游限制決定 baseline+elastic headroom；避免全時峰值 idle，也不犧牲啟動速度。 | 所有 workload scale-to-zero；永遠保留峰值容量；只看平均 CPU。 | `SAP-2.4` / `reliability` |
| 8 | SAA scenario | 付款資料不可遺失、服務可短暫停、流量五分鐘增十倍，問方案面向。 | Durable transactional storage/backup與 tested restore 保資料；stateless multi-AZ compute、ELB、預熱/elastic capacity處理流量。 | 只用 S3；只用 ASG；只建立 read replica。 | `SAA-2.2` / `reliability` |
| 9 | SAP expansion | 問如何證明整體系統達成 availability，而不是只引用某服務 SLA。 | 建立 end-to-end SLI/SLO、dependency/error budget、failure injection、capacity test與 recovery evidence。 | 相乘/相加 SLA 後不測；只看 resource running；只依單一服務 durability 數字。 | `SAP-3.4` / `reliability` |
| 10 | Multi-response | 選兩項：可擴展但不夠彈性的例子。 | 正解為「可加 nodes 但需數小時人工操作」與「架構支援大量 nodes，但 quota/max capacity 阻止快速增加」。 | Auto Scaling 五分鐘內按 metric 增加；serverless 隨 request 自動增加 concurrency且下游可承受；預熱完成的 fleet。 | `SAP-1.3` / `reliability` |

---

## 第 9 章：SLA、SLO、RTO、RPO 與 Business Requirement

### 目前缺陷

- 第 1 題的「量化並映射 HA/DR」與「更低 RTO/RPO 需要更多容量/自動化/複寫/演練」均正確，單選條件不足。
- 第 4 題把抽象 business requirement 直接映射為 AWS Backup；backup policy 本身不能保證 application RTO、近零 RPO 或可用性。
- 題庫未區分 SLA（契約承諾）與 SLO（內部目標），也沒有 SLI/error budget。
- 未測 RTO 從事故起算、RPO 代表可接受資料回退點，以及 backup frequency、replication lag、restore time、DNS/capacity 對目標的影響。
- DRS、AWS Backup、Route 53 被列為 services，卻沒有比較 block replication、recovery points、traffic steering 與 application consistency。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 問 SLA、SLI、SLO、RTO、RPO 各自扮演什麼角色。 | SLA 是外部承諾；SLI 是量測；SLO 是內部目標；RTO/RPO 約束事故恢復時間與資料回退。 | SLA 是監控 metric；RPO 是修復所需時間；RTO 是可遺失資料量。 | `SAA-2.2` / `reliability` |
| 2 | Mechanism | 每 15 分鐘 backup、restore 需 2 小時，問它能支持的目標與限制。 | Backup interval 影響理論 RPO，restore/dependency/cutover 影響 RTO；兩者都必須實測且考慮 application consistency。 | 15 分鐘同時保證 RTO/RPO；backup job success 等於 restore success；TTL 決定 RPO。 | `SAP-2.2` / `dr` |
| 3 | Concrete setting | 問 AWS Backup plan 哪些設定會改變 retention、隔離與可恢復性。 | Schedule、lifecycle、vault/KMS、resource assignment、cross-account/Region copy 與 restore testing 必須符合資料分類。 | 只設定 tag 名稱；只增加 EC2 size；Route 53 record type。 | `SAA-2.2` / `dr` |
| 4 | Data/request flow | 問 primary Region 故障到使用者恢復的完整 DR 流程。 | Detect/fence → 確認 recovery point/replication → 恢復資料與 dependencies → 啟動 capacity → 切 DNS/entry → 驗證 business transactions。 | 只改 DNS；只有 data copy 就完成；先讓兩邊同時寫但無 conflict control。 | `SAP-2.2` / `dr` |
| 5 | Failure diagnosis | Backup 全綠但演練超過 RTO，問常見原因。 | Restore throughput、KMS/IAM、quota、dependency order、DNS、capacity與 runbook automation 都可能主導 RTO。 | Backup retention 太長必然是原因；S3 durability 不足；只需提高 health-check frequency。 | `SAP-2.4` / `dr` |
| 6 | Comparison | 比較 AWS Backup、Elastic Disaster Recovery、service-native replication、Route 53。 | Backup 管 recovery points；DRS 做 server block replication/launch；native replication 管特定資料服務；Route 53 只做 DNS steering。 | Route 53 複寫資料；AWS Backup 自動 active-active；DRS 是 application-level transaction replication。 | `SAP-2.2` / `dr` |
| 7 | Cost/operations | 問 backup/restore、pilot light、warm standby、active-active 的成本曲線。 | 越低 RTO/RPO 通常需要越多常駐 capacity、複寫、automation、治理與演練；按 business impact 選擇。 | Active-active 永遠成本最低；backup-only 可保證秒級 RTO；多 Region 空 VPC 即 warm standby。 | `SAP-2.4` / `dr` |
| 8 | SAA scenario | 內部報表可停四小時、可丟一天資料，問 cost-effective DR。 | 使用符合一天 RPO 的排程備份、可在四小時內實測恢復的 runbook/capacity，避免不必要 active-active。 | 跨 Region active-active；同步雙寫；只建立 Route 53 failover record。 | `SAA-2.2` / `dr` |
| 9 | SAP expansion | 財務交易要求近零資料損失、15 分鐘恢復，問設計責任。 | 選可滿足一致性/replication 的 data architecture，加 fencing、跨 Region capacity、automated orchestration、依賴順序與定期 game day；不能只宣稱 RPO=0。 | 每 15 分鐘 snapshot；只把 DNS TTL 設 30 秒；沒有 conflict control 的雙主。 | `SAP-2.2` / `dr` |
| 10 | Multi-response | 選兩項：可證明 DR 目標達成的 evidence。 | 正解為「定期 restore/failover 記錄實際 RTO/RPO」與「以 business transaction 驗證資料完整性及服務可用」。 | Backup console 顯示 completed；standby resources 存在；架構圖標示 Multi-Region。 | `SAP-2.4` / `dr` |

---

## 第 10 章：Shared Responsibility 與六大 Pillars

### 目前缺陷

- 第 1 題的整體責任/pillar 方法與「managed service 不替客戶決定資料/IAM/application correctness」都是正確答案，只標前者。
- Well-Architected Framework 與 Shared Responsibility Model 都不是 request/data-path component；現有機制題使用錯誤問題模型。
- `high-risk issues` setting guide 被 generic classifier 誤寫成 partition key、index、scan 與 hot partition，屬明確 factual/content defect。
- 第 2 題把 framework review 欄位與 responsibility checklist 當成互斥 config；實際上兩者可共同需要，題幹沒有排除條件。
- 未測 EC2、RDS、Lambda/container 的責任如何移動，也未完整驗證六 pillars、pillar trade-offs、RACI、風險 owner 與 improvement prioritization。

### 十個原創題目意圖

| # | 能力面 | 題目意圖 | 正確原則 | 三個 plausible distractor concepts | 官方 task / source key |
|---|---|---|---|---|---|
| 1 | Purpose | 問 Shared Responsibility Model 真正要回答的問題。 | 針對每項服務/層次判斷 AWS 與 customer 各自預防、設定、監控與修復什麼；managed 只移動責任。 | AWS 負責所有 security；customer 必須維護 AWS data center；使用 managed service 即無需資料治理。 | `SAA-1.2` / `security` |
| 2 | Mechanism | 問 EC2、RDS、Lambda 抽象提高時 patching 責任如何移動。 | AWS 一直管理底層設施；customer 在 EC2 管 guest OS，在 RDS/Lambda 減少 OS/runtime platform 工作，但仍管 code、data、IAM、config。 | Lambda code 漏洞由 AWS 修；RDS schema/帳號權限由 AWS 決定；EC2 hypervisor 由 customer patch。 | `SAA-1.2` / `security` |
| 3 | Concrete setting | 問 Well-Architected review 的可稽核紀錄應包含什麼。 | 定義 workload/owner、回答 pillar questions、記錄 HRI/MRI、priority、owner、due date、milestone 與驗證 evidence。 | `high-risk issues` 是 database index 設定；milestone 自動修復資源；只記服務清單。 | `SAP-3.1` / `well-architected` |
| 4 | Data/request flow | 敏感資料經 API、Lambda、KMS、database，問責任如何沿路標註。 | AWS 維護服務基礎設施；customer 決定 identity、network exposure、key policy、data classification、code validation、logging與 retention。 | 使用 KMS 後 AWS 決定誰可解密；private subnet 代表資料已授權；CloudTrail 取代 application authorization。 | `SAA-1.3` / `security` |
| 5 | Failure diagnosis | Public bucket 事故後團隊說「S3 是 managed service」，問真正缺陷。 | Customer 仍負責 bucket policy/BPA、資料分類、IAM、encryption choices、logging與 review；需修 control 和 ownership。 | AWS 應退款但不需改設定；只提高 S3 durability；只改 Region。 | `SAP-3.2` / `security` |
| 6 | Comparison | 問六 pillars 各自主要關注與 trade-off。 | Operational excellence、security、reliability、performance efficiency、cost optimization、sustainability 必須依 business context 平衡。 | 六 pillars 是六個 AWS 服務；只需選 security；cost optimization 等於最低帳單。 | `SAP-2.3` / `well-architected` |
| 7 | Cost/operations | 問 managed service 的總成本評估。 | 比較服務費、idle/capacity、patch/on-call、failure risk、migration與 skill cost，而非只看 unit price。 | Managed 永遠較便宜；self-managed 永遠較便宜；人力與風險不屬架構成本。 | `SAA-2.1` / `well-architected` |
| 8 | SAA scenario | EC2 web app 與 Lambda function 都處理 PII，問 customer 各負責什麼。 | EC2 customer 多負責 guest OS；兩者都仍負責 application code、IAM、data protection、network/config與 logging。 | Lambda 免除所有 customer security；AWS patch EC2 application；資料 owner 由服務自動指定。 | `SAA-1.2` / `security` |
| 9 | SAP expansion | 多帳號 organization 要把 review finding 轉成可治理 improvement program。 | 建 central standards/guardrails與 delegated owners，依 risk/business impact 排程，版本化 rollout，收集 evidence並以 milestones 重審。 | 全部交 management account admin 手動修；只匯出 PDF；所有風險同優先級一次 big-bang。 | `SAP-2.3` / `well-architected` |
| 10 | Multi-response | 選兩項：使用 RDS 後仍由 customer 負責的工作。 | 正解為「database users/schema/query/application correctness」與「network/IAM/encryption/backup retention等可配置 controls及其驗證」。 | Patch RDS host OS；更換 AWS data-center disks；維護 hypervisor。 | `SAA-1.3` / `security` |

---

SUPERSET_WORKER_DONE
status: done
files:
  - tools/aws_exam_audits/part_00.md
checks:
  - audited_chapters: 1-10
  - current_generator_and_generated_html_reviewed: true
  - exactly_10_intents_per_chapter: true
  - required_10_capability_facets_per_chapter: true
  - correct_principle_and_3_distractors_per_intent: true
  - official_task_and_source_key_per_intent: true
  - exam_dumps_used: false
  - other_files_modified: false
END_SUPERSET_WORKER_DONE
