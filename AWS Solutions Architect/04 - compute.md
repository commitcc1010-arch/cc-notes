---
title: "Compute 與 Application Architecture"
part: 3
as_of: 2026-10-01
---

# Part 3　Compute 與 Application Architecture

# 第 32 章　EC2 Instance、AMI 與 Placement

EC2選型同時牽涉CPU、memory、network、accelerator、license與failure placement。

## 跟著一份工作走：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：HPC需要低延遲東西向網路，商用軟體依socket授權，web tier可水平擴展。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：EC2選型同時牽涉CPU、memory、network、accelerator、license與failure placement。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Amazon EC2負責主要工作，Amazon Machine Images提醒我們答案不是永遠固定。本章會走向「以profile選instance family，AMI固化可重建映像，placement group依latency或隔離需求使用。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：HPC需要低延遲東西向網路，商用軟體依socket授權，web tier可水平擴展。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[Amazon EC2]
          │ 提供可控制OS、runtime、network與storage的虛擬機compute。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · Amazon Machine Images：保存EC2啟動所需的root-volume template、block-device mapping與l…
  · Placement groups：控制EC2 instances在底層硬體上的相對位置，以交換latency、failure isolati…

失敗時先找：只依vCPU數選型，忽略network/EBS bandwidth、burstable credits與單AZ容量。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問Amazon EC2有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon EC2和Amazon Machine Images並不是兩個任意的產品名稱。前者適合本章，是因為「以profile選instance family，AMI固化可重建映像，placement group依latency或隔離需求使用。」直接回應了眼前的問題；後者描述的「Graviton可降低price/performance但需architecture相容；Dedicated Host適合特定license與隔離。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只依vCPU數選型，忽略network/EBS bandwidth、burstable credits與單AZ容量。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「measure the constrained resource, then choose compute」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon EC2 | 提供可控制OS、runtime、network與storage的虛擬機compute。 | Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 |
| Amazon Machine Images | 保存EC2啟動所需的root-volume template、block-device mapping與launch permissions。 | 啟動instance時由AMI建立root EBS snapshot-backed volume並套用architecture、boot mode與mapping；AMI本身不是正在執行的server。 |
| Placement groups | 控制EC2 instances在底層硬體上的相對位置，以交換latency、failure isolation或分區拓撲。 | Cluster把instances靠近以降低network latency；spread分散少量instances到不同硬體；partition把大型fleet分到可見partition failure domains。 |

## 把全圖套進一個具體案例

**場景：** HPC需要低延遲東西向網路，商用軟體依socket授權，web tier可水平擴展。

1. 故事的起點：HPC需要低延遲東西向網路，商用軟體依socket授權，web tier可水平擴展。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon EC2負責「提供可控制OS、runtime、network與storage的虛擬機compute。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon Machine Images、Placement groups各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只依vCPU數選型，忽略network/EBS bandwidth、burstable credits與單AZ容量。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### ENA、EFA 與 Jumbo Frames：Placement Group 只決定放哪裡，網卡能力決定怎麼傳

Cluster placement group 讓 instances 靠近，卻不會自動把普通網路變成 HPC fabric。ENA 提供 enhanced networking；EFA 在支援的 instance type 上提供適合 HPC/ML 的低延遲、高吞吐 OS-bypass 能力。Jumbo frames 則是 MTU 選擇，只有整條路徑都支援時才能減少封包處理 overhead。

```text
HPC node ─ EFA/ENA ─┐
HPC node ─ EFA/ENA ─┼─ cluster placement group ─ high-bandwidth fabric
HPC node ─ EFA/ENA ─┘
       MTU/path must agree end-to-end; one smaller hop can break jumbo packets
```

#### 排查『頻寬很高但 MPI 很慢』的順序

```Checklist
1. instance type supports EFA / required ENA bandwidth
2. EFA attached and driver/libfabric visible in the guest
3. instances placed in the intended cluster placement group
4. security group allows the required same-group traffic
5. MTU and route path are consistent end-to-end
6. benchmark with the real message-size/concurrency pattern
```

1. Instance advertised bandwidth 是上限，不代表單一 flow 或 application 一定達到。
2. Jumbo MTU 不一致常表現為部分封包可通、較大 payload timeout；需要沿路測試，不是只看 EC2 console。
3. Cluster placement 提升 proximity，但縮小 failure-domain 彈性；容量不足時可能無法一次啟動整個 group。

**選擇邊界：** 一般 web tier 通常不需 EFA；高 packets-per-second 用 ENA 支援的 instance；MPI/ML collective communication 才考慮 EFA＋cluster placement。跨 Internet 路徑不要假設 jumbo MTU。

**考試範圍：** SAA 會測 placement group 與 instance family；EFA、MTU、network-card/flow bandwidth 與 HPC trade-off 通常是 SAP／Advanced Networking 深化。

- [AWS：Enhanced networking on EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/enhanced-networking.html)
- [AWS：Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)

## 需要時再查：四個閱讀支點

### Amazon EC2

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：EC2選型同時牽涉CPU、memory、network、accelerator、license與failure placement。
- **具體例子／邊界：** 在「HPC需要低延遲東西向網路，商用軟體依socket授權，web tier可水平擴展。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon Machine Images

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Graviton可降低price/performance但需architecture相容；Dedicated Host適合特定license與隔離。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只依vCPU數選型，忽略network/EBS bandwidth、burstable credits與單AZ容量。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：measure the constrained resource, then choose compute。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### temporary credentials

具有到期時間的access key、secret與session token，通常由STS簽發，比長期key更易限制與輪替。

### placement group

控制EC2 instances在底層硬體中的相對放置：cluster偏低延遲、spread偏隔離、partition偏大型分區故障邊界。

### failure domain

會因同一事件一起失效的資源集合，例如單一instance、AZ或Region。

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### EC2 instance

AWS虛擬機執行個體，由AMI、instance type、network、storage與IAM instance profile共同定義。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

## 回到 AWS：Components、功用與責任邊界

### Amazon EC2

- **功用：** 提供可控制OS、runtime、network與storage的虛擬機compute。
- **底層機制：** Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。
- **關鍵設定：** instance family/size、AMI、subnet、security group、IAM instance profile、user data、tenancy與purchase option。
- **選擇時機：** 需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。
- **替換時機：** 只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。

### Amazon Machine Images

- **功用：** 保存EC2啟動所需的root-volume template、block-device mapping與launch permissions。
- **底層機制：** 啟動instance時由AMI建立root EBS snapshot-backed volume並套用architecture、boot mode與mapping；AMI本身不是正在執行的server。
- **關鍵設定：** image ID、Region/copy、architecture、root device、block mappings、launch permissions、deprecation與Image Builder pipeline。
- **選擇時機：** 建立immutable server baseline、Auto Scaling launch template或跨帳號核准映像時。
- **替換時機：** 只需部署container application時使用container image；執行中的資料與設定不應只靠AMI保存。

### Placement groups

- **功用：** 控制EC2 instances在底層硬體上的相對位置，以交換latency、failure isolation或分區拓撲。
- **底層機制：** Cluster把instances靠近以降低network latency；spread分散少量instances到不同硬體；partition把大型fleet分到可見partition failure domains。
- **關鍵設定：** strategy、partition count、instance type support、tenancy、AZ與capacity reservation。
- **選擇時機：** HPC低延遲、少量關鍵nodes硬體隔離，或Kafka/HDFS等partition-aware叢集。
- **替換時機：** 一般web fleet先跨AZ使用Auto Scaling；placement group不能提供跨Region或application-level HA。

## 考前與實作時再查：設定操作手冊

### Amazon EC2：逐項設定說明

#### `instance family/size`

- **控制什麼：** `instance family/size`設定Amazon EC2的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `AMI`

- **控制什麼：** `AMI`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EC2鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `subnet`

- **控制什麼：** `subnet`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EC2的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `security group`

- **控制什麼：** `security group`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EC2中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `IAM instance profile`

- **控制什麼：** `IAM instance profile`定義Amazon EC2管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `user data`

- **控制什麼：** `user data`是可版本化的啟動或工作規格，定義Amazon EC2建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `tenancy`

- **控制什麼：** `tenancy`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `purchase option`

- **控制什麼：** `purchase option`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

### Amazon Machine Images：逐項設定說明

#### `image ID`

- **控制什麼：** `image ID`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「建立immutable server baseline、Auto Scaling launch template或跨帳號核准映像時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Machine Images鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `Region/copy`

- **控制什麼：** `Region/copy`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Amazon Machine Images前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `architecture`

- **控制什麼：** 指定AMI可啟動的CPU instruction architecture，例如x86_64或arm64，必須與EC2 instance type及所有native binaries相容。
- **何時需要：** 選擇Graviton或x86 instance family、跨architecture搬移workload，或建立同一應用的多架構golden images時。
- **怎麼設定／驗證：** 在Image Builder／Packer pipeline分別建置並測試每種architecture，標記AMI，讓launch template引用相符的instance family與image ID。
- **常見錯法：** x86 AMI不能直接啟動在arm64 instance；即使應用語言可攜，OS package、agent與native library仍可能不相容。

#### `root device`

- **控制什麼：** 定義EC2開機使用的root volume類型、device mapping、snapshot、容量與DeleteOnTermination等生命週期行為。
- **何時需要：** 需要immutable baseline、調整root磁碟容量／型別，或必須決定instance終止後root資料是否保留時。
- **怎麼設定／驗證：** 檢查AMI的root device與block mappings，在launch template覆寫容量、volume type、encryption及DeleteOnTermination，並實測replace／terminate。
- **常見錯法：** 把root volume設為保留會留下成本與敏感資料；設為刪除又不能把尚未外部化的application state當成可恢復資料。

#### `block mappings`

- **控制什麼：** `block mappings`描述request/resource如何被分類與匹配，命中後才執行相應action。
- **何時需要：** 當需求符合「建立immutable server baseline、Auto Scaling launch template或跨帳號核准映像時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Machine Images以最小、可測的match條件建立規則，明確設定priority/default behavior，先用observe/count模式驗證命中範圍。
- **常見錯法：** 重疊規則、錯誤優先序與缺少default case會讓流量走到意外分支；規則存在也不代表資料或identity已被授權。

#### `launch permissions`

- **控制什麼：** `launch permissions`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「建立immutable server baseline、Auto Scaling launch template或跨帳號核准映像時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Machine Images明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `deprecation`

- **控制什麼：** 為AMI設定棄用時間，使一般DescribeImages結果與新部署不再優先使用它，但不會刪除AMI或停止既有instances。
- **何時需要：** golden image已有安全更新或替代版本，需要阻止新的launch繼續採用舊映像，同時保留受控回滾窗口時。
- **怎麼設定／驗證：** 在新AMI通過測試後更新launch templates，設定舊AMI deprecation time，監控仍引用舊ID的stacks，再依retention政策deregister。
- **常見錯法：** Deprecation不是立即撤銷launch permission，也不會patch已執行instance；太早deregister及刪除snapshots可能讓rollback失去可啟動映像。

#### `Image Builder pipeline`

- **控制什麼：** `Image Builder pipeline`定義Amazon Machine Images要執行的功能、命令或批次單位，是application behavior與release contract。
- **何時需要：** 同一artifact要依環境切換功能、建立可重複run流程或平行處理大量相似jobs時。
- **怎麼設定／驗證：** 版本化command/flag schema，設定validation/default與修改權限；以canary和明確rollback條件推出。
- **常見錯法：** 沒有owner/expiry的feature flag會永久累積；command、preset或array index不驗證會大規模重複失敗。

### Placement groups：逐項設定說明

#### `strategy`

- **控制什麼：** 選擇cluster、spread或partition，決定EC2 instances在底層硬體上的鄰近性、硬體隔離程度與可見failure-domain拓撲。
- **何時需要：** HPC需要低網路延遲、少量關鍵nodes要分散硬體，或Kafka／HDFS fleet需要依partition容忍rack級故障時。
- **怎麼設定／驗證：** 依workload選單一strategy並驗證instance type、AZ、tenancy與capacity限制；partition-aware軟體還要把partition資訊映射到replicas。
- **常見錯法：** Cluster提高效能但集中硬體風險；spread有instance數量限制；placement group本身不提供跨AZ資料複寫或application failover。

#### `partition count`

- **控制什麼：** `partition count`設定Placement groups的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「HPC低延遲、少量關鍵nodes硬體隔離，或Kafka/HDFS等partition-aware叢集。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `instance type support`

- **控制什麼：** `instance type support`選擇Placement groups的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `tenancy`

- **控制什麼：** `tenancy`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `AZ`

- **控制什麼：** `AZ`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Placement groups前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `capacity reservation`

- **控制什麼：** `capacity reservation`設定Placement groups的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「HPC低延遲、少量關鍵nodes硬體隔離，或Kafka/HDFS等partition-aware叢集。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

## 讀到這裡，請用自己的話說一次

1. Amazon EC2的責任：提供可控制OS、runtime、network與storage的虛擬機compute。
2. 底層機制：Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。
3. 第一個要看的設定：instance family/size、AMI、subnet、security group、IAM instance profile、user data、tenancy與purchase option。
4. 選擇邏輯：以profile選instance family，AMI固化可重建映像，placement group依latency或隔離需求使用。
5. 不要混淆：Amazon Machine Images的責任是「保存EC2啟動所需的root-volume template、block-device mapping與launch permissions。」；它不會自動取代Amazon EC2。
6. 替換訊號：只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。
7. 最常見錯法：只依vCPU數選型，忽略network/EBS bandwidth、burstable credits與單AZ容量。
8. 可移植原則：measure the constrained resource, then choose compute。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon EC2 | 提供可控制OS、runtime、network與storage的虛擬機compute。 | Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 | 需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。 | 只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。 |
| Amazon Machine Images | 保存EC2啟動所需的root-volume template、block-device mapping與launch permissions。 | 啟動instance時由AMI建立root EBS snapshot-backed volume並套用architecture、boot mode與mapping；AMI本身不是正在執行的server。 | 建立immutable server baseline、Auto Scaling launch template或跨帳號核准映像時。 | 只需部署container application時使用container image；執行中的資料與設定不應只靠AMI保存。 |
| Placement groups | 控制EC2 instances在底層硬體上的相對位置，以交換latency、failure isolation或分區拓撲。 | Cluster把instances靠近以降低network latency；spread分散少量instances到不同硬體；partition把大型fleet分到可見partition failure domains。 | HPC低延遲、少量關鍵nodes硬體隔離，或Kafka/HDFS等partition-aware叢集。 | 一般web fleet先跨AZ使用Auto Scaling；placement group不能提供跨Region或application-level HA。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Graviton可降低price/performance但需architecture相容；Dedicated Host適合特定license與隔離。 | 只有當題目條件明確改變時才可能合理。 | 只依vCPU數選型，忽略network/EBS bandwidth、burstable credits與單AZ容量。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Graviton可降低price/performance但需architecture相容；Dedicated Host適合特定license與隔離。」之間做選擇。
- 認得常考設定：instance family/size、AMI、subnet、security group、IAM instance profile、user data、tenancy與purchase option。
- 對應官方tasks：SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜依實測瓶頸選擇 EC2 instance family

某即時風險分析服務的 profiling 顯示，每個 worker 只使用 25% CPU，但會反覆掃描 180 GiB 的 in-memory graph；一旦開始 swap，p99 latency 就從 40 ms 升到 2 秒。資料由 S3 載入，單機磁碟容量不是限制。團隊應先採取哪個選型方式？

A. 因資料量很大，直接改用 storage optimized instance，無須 benchmark
B. 選擇目前最大的 general purpose instance，因為最大規格自然最可靠
C. 先比較 memory optimized family，讓 working set 留在記憶體，再以代表性負載 benchmark size
D. 改用 burstable instance，因為目前平均 CPU 低於 baseline

**答案：C**

- **A：** 錯誤。資料量大不代表瓶頸是本機 storage；題目已指出 swap 才是 latency 翻轉點，storage optimized 無法直接補足 RAM。
- **B：** 錯誤。最大規格未必提供最佳 memory-to-cost 比，也沒有以證據確認瓶頸；可靠性仍需靠多 AZ 與可替換架構。
- **C：** 正確。應先按受限資源選 family；memory optimized instance 提供較高 memory/vCPU，之後再用真實 working set 決定 size。
- **D：** 錯誤。Bursty CPU credit 與記憶體容量是不同契約；低 CPU 不能抵銷 working set 超過 RAM 的問題。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EC2 instance types - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html)

### 練習題 2｜SAA｜AMI 與 launch-time 設定的責任邊界

平台團隊建立一個已安裝作業系統與監控 agent 的 golden AMI，並讓不同環境共用。開發人員聲稱：只要指定 AMI，subnet、IAM role 與啟動後環境變數都會自動跟著映像出現。哪一項描述最準確？

A. AMI 會持續同步來源 instance 上所有後續檔案變更到已啟動 instances
B. AMI 提供 root-volume 與 block-device template；instance type、network、instance profile 和 user data 仍由 launch template 或啟動請求設定
C. AMI 會繼承建立映像時 subnet 的 route table，所以不能跨 subnet 啟動
D. AMI 本身會在多個 AZ 維持 standby instance，提供自動 failover

**答案：B**

- **A：** 錯誤。AMI 是建立時的版本化 template，不是與來源 instance 持續雙向同步的檔案系統。
- **B：** 正確。AMI 定義開機映像與 block mappings；運算規格、ENI、IAM credentials 與 bootstrap 行為仍是 launch-time contract。
- **C：** 錯誤。Subnet 與 route table 屬於新 instance 的 networking 設定，不會被封裝進 AMI。
- **D：** 錯誤。AMI 是 artifact，不是高可用 runtime；多 AZ capacity 需由 Auto Scaling 或其他 scheduler 建立。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon Machine Images in Amazon EC2 - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html)

### 練習題 3｜SAP｜辨識 EC2 network 與 EBS bandwidth 上限

一個單執行個體影像處理服務的平均 CPU 只有 35%，但尖峰時 NetworkOut 與 EBS throughput 都貼近該 instance type 的文件上限，queue age 持續增加。下列哪個動作最能直接驗證並處理瓶頸？

A. 把 CPUUtilization target 從 50% 降到 20%，並假設 CPU 是唯一需求訊號
B. 重新製作完全相同內容的 AMI，讓作業系統取得更高 network bandwidth
C. 把 instance 放入 spread placement group，以解除單一 instance 的 I/O 上限
D. 比較 instance-level network/EBS limits 與工作需求，benchmark 較高 bandwidth 的 size，並評估可平行化後 scale out

**答案：D**

- **A：** 錯誤。CPU 並未飽和，降低 CPU target 可能偶然增加容量，卻沒有證明或精準追蹤真正的 I/O demand。
- **B：** 錯誤。AMI 內容不會改變 instance type 的 network 或 EBS performance envelope。
- **C：** 錯誤。Spread placement group 改善硬體隔離，不會提高單一 instance 文件規定的 network/EBS 上限。
- **D：** 正確。先把觀察值對照 instance contract，再決定 scale up 或將工作切分 scale out，才能針對受限資源修正。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon EC2 instance types - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html)

### 練習題 4｜SAA｜Cluster placement group 的 HPC 設定

研究團隊要在同一個 AZ 執行 tightly coupled MPI workload。節點會大量交換小訊息，目標是最低 east-west network latency；團隊可接受單 AZ 風險，且已確認 instance type 支援 enhanced networking。哪個配置最合適？

A. 將相容 instances 一次啟動到同一個 cluster placement group，並在部署前確認該 AZ 容量
B. 使用 spread placement group，因為分散到不同硬體能提供最低節點間 latency
C. 使用 partition placement group，並假設所有 partitions 都位於同一 rack
D. 購買 Dedicated Hosts；host tenancy 會自動建立低延遲 HPC network fabric

**答案：A**

- **A：** 正確。Cluster strategy 將 instances 緊密放置以取得低 latency/high throughput，但會集中在單一 AZ 並面臨容量限制。
- **B：** 錯誤。Spread 的首要目標是把少量 instances 分散到不同硬體，並非讓節點彼此最靠近。
- **C：** 錯誤。Partition 提供可見的 failure partitions；它不保證所有節點同 rack，也不以最低 MPI latency 為主要契約。
- **D：** 錯誤。Dedicated Host 解決 host-level isolation/licensing，不等同 cluster placement 或特定 HPC network topology。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Placement groups for your Amazon EC2 instances - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html)

### 練習題 5｜SAA｜區分 EC2 system 與 instance status check

監控顯示某 EC2 的 system status check 失敗，但 instance status check 在故障前一直正常；同一 AZ 其他 instances 沒有異常。應先如何解讀與處理？

A. 這證明 application thread pool deadlock，應只重新啟動 application process
B. 問題偏向底層 host、power 或 AWS network；若 workload 可中斷，可用 recover 或 stop/start 移到新 host，並保留應用層檢查
C. 這表示 security group 阻擋 ALB health check，修改 inbound rule 即可
D. 這必然是整個 AZ outage，應立刻刪除該 Region 所有 resources

**答案：B**

- **A：** 錯誤。Application deadlock通常不會直接造成 system status check 失敗；仍須另用 application health 判斷。
- **B：** 正確。System check 監控 instance 所在 AWS 基礎設施；recover 或 stop/start 可把 EBS-backed instance 移到可用 host。
- **C：** 錯誤。Security group 可影響 application reachability，卻不是 EC2 system status check 的判定來源。
- **D：** 錯誤。單一 system-check failure 不足以證明整個 AZ 中斷；應依 scope 與其他 telemetry 驗證。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Status checks for Amazon EC2 instances - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html)

### 練習題 6｜SAP｜T family Standard mode CPU credit exhaustion

一個以 Standard mode 執行的 t3.small legacy service，每天有六小時持續使用約 80% CPU。上線數週後，尖峰期間吞吐逐漸下降；磁碟與網路沒有飽和。哪個證據與改善最合理？

A. 切換 Unlimited mode，接受 surplus-credit 費用，並持續觀察 CPUSurplusCreditBalance 與 CPUSurplusCreditsCharged
B. 保留 Standard mode，但把 workload scale out 到更多 T3 instances，讓每台平均 CPU 回到 baseline 以下
C. 檢查 CPUCreditBalance 是否耗盡；若負載本質上長期高於 baseline，benchmark 並改用 M 或 C 等固定性能 family
D. 改成更大的 T3 size；只要初始 credits 較多，就可保證長期 80% CPU 不受 baseline 約束

**答案：C**

- **A：** 錯誤但可能成為替代方案。Unlimited mode 能使用 surplus credits 維持高於 baseline 的 CPU，但題目問的是先解釋 Standard mode 的吞吐下降；切換前還要估算 CPUSurplusCreditsCharged 的長期費用。
- **B：** 錯誤但在可水平分割時可行。Scale out 能降低每台的 CPU 壓力，卻不是題目中單機逐漸降速的直接證據；仍應先確認 CPUCreditBalance 與實際 baseline。
- **C：** 正確。Standard mode 在 CPUCreditBalance 用盡後只能逐步回到 baseline；對每天數小時的持續高 CPU，固定性能 family 通常比反覆依賴 burst 更符合效能契約。
- **D：** 錯誤。較大 T3 的 baseline 與 credit 累積速率可能不同，但仍是 burstable 契約；只增加 size 並不能保證長期 80% CPU 永遠不耗盡 credits。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Standard mode for burstable performance instances - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-standard-mode.html)、[Unlimited mode for burstable performance instances - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-unlimited-mode.html)

### 練習題 7｜SAA｜穩定基線與可中斷尖峰的 purchase mix

一家媒體公司全年至少需要 40 個 stateless workers，另外在發片日會增加 0–200 個可重試 workers。發片時間不固定，Spot interruption 已由 queue retry 處理。哪個 purchase strategy 最符合成本與風險？

A. 所有容量都使用 Dedicated Hosts，因為 host isolation 通常單價最低
B. 所有容量都使用單一 instance type 的 Spot，並假設價格低代表永遠有容量
C. 為可能不會出現的 200 個尖峰 workers 全額購買三年期 commitment
D. 以 Savings Plans/RI 類承諾覆蓋穩定基線，尖峰使用 diversified Spot，短期不可預測缺口保留 On-Demand

**答案：D**

- **A：** 錯誤。Dedicated Hosts 通常因 license/compliance/host visibility 使用，不是一般 stateless fleet 的最低成本預設。
- **B：** 錯誤。單一 Spot pool 會放大 capacity shortage 與 interruption 風險；穩定基線也不宜完全依賴可回收容量。
- **C：** 錯誤。Commitment 應覆蓋可預測利用率；把偶發上限全部承諾會造成低 utilization。
- **D：** 正確。穩定需求取得 commitment discount，可容錯 burst 用多樣化 Spot，On-Demand 補不可預測與容量不足。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EC2 billing and purchasing options - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html)、[Auto Scaling groups with multiple instance types and purchase options - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-mixed-instances-groups.html)

### 練習題 8｜SAA｜Cluster、partition 與 spread placement semantics

架構師需要把三種 workload 對應到 placement strategy：低延遲 MPI；能感知 rack-like failure boundary 的大型 Kafka fleet；四台彼此獨立的關鍵 license servers。哪個對應正確？

A. MPI 用 cluster、Kafka 用 partition、license servers 用 spread
B. MPI 用 spread、Kafka 用 cluster、license servers 用 partition
C. 三者都使用 cluster，因 cluster 同時提供跨 Region fault tolerance
D. 三者都使用 spread，因 spread 沒有 instance 數量與拓撲限制

**答案：A**

- **A：** 正確。Cluster 偏向低 latency，partition 暴露大型 fleet 的 failure partitions，spread 隔離少量關鍵 instances。
- **B：** 錯誤。這把三種 strategy 的主要契約對調；spread 不是 MPI latency 優化，cluster 也不提供 Kafka 的 partition-aware 隔離。
- **C：** 錯誤。Placement group 是 AZ 內的相對放置控制，不能提供跨 Region 容錯。
- **D：** 錯誤。Spread 適合少量 instances且存在限制，也不提供大型 distributed system 所需的 partition visibility。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Placement groups for your Amazon EC2 instances - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html)

### 練習題 9｜SAP｜BYOL Dedicated Host visibility 與 host capacity planning

公司要在指定 AZ cutover 一套依實體 socket 計價的 BYOL 軟體。License auditor 必須能追蹤 host socket/core，且 cutover 當天要在 host tenancy 上啟動 20 台指定 instance type。選擇兩項。

A. 使用 Dedicated Instances，因它提供與 Dedicated Host 相同的 host ID 與 socket placement 控制
B. 使用 Dedicated Hosts，讓公司取得 host identity、socket/core visibility 與明確的 instance placement
C. 購買 Compute Savings Plans，因 commitment 會在指定 AZ 保留實體容量
D. 在 cutover 前於目標 AZ 配置足夠且相容的 Dedicated Hosts，按每台 host 可容納的 instance 數計算 20 台容量，做 canary launch 並保留 host replacement headroom
E. 建立 On-Demand Capacity Reservation 來供 host tenancy 使用，因 default、dedicated 與 host tenancy 可共用同一份 reservation

**答案：B、D**

- **A：** 錯誤。Dedicated Instances 提供硬體隔離，但不提供 Dedicated Host 的 host identity、socket/core visibility 與 placement 控制。
- **B：** 正確。Dedicated Hosts 暴露 host identity、socket/core 與 placement 資訊，適合授權條款綁定實體伺服器的 BYOL；Dedicated Instances 不提供相同的 host 控制。
- **C：** 錯誤。Savings Plans 是費用承諾折扣，不是特定 AZ 的 capacity reservation。
- **D：** 正確。此 workload 的容量單位是已配置的 Dedicated Host；必須依 host 支援的 instance family、每 host slot 數與 AZ 可用 host 數量做容量驗證，而不是另套一般 instance reservation。
- **E：** 錯誤。On-Demand Capacity Reservation 支援 default 或 dedicated tenancy，不能當成 host tenancy 的 Dedicated Host 容量；需要 host 可見性時應直接配置並管理足夠 hosts。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon EC2 Dedicated Hosts - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/dedicated-hosts-overview.html)、[Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-reservations-considerations.html)

### 練習題 10｜SAP｜Immutable、跨 AZ 且可回滾的 EC2 rollout

全球電商要更新跨三個 AZ 的 EC2 web fleet。要求不得 SSH 修改 production、壞映像最多只能影響一個 deployment wave，且 alarm 觸發後要能回到前一版本。選擇兩項。

A. 建立 versioned AMI 與 launch template version，使用 instance refresh 或新 ASG 分批替換，不修改既有 instances
B. 讓 user data 每次從未版本化的 latest URL 下載程式，使所有重啟都自動取得最新版本
C. 部署開始時先終止全部舊 instances，確保不會混用版本
D. 覆寫同一 AMI identity 並假設已執行與新啟動 instances 內容會同步
E. 跨 AZ 保留足夠 healthy capacity，為每 wave 設 health/business alarms、checkpoint 與 rollback 到前一 launch template version

**答案：A、E**

- **A：** 正確。Versioned artifacts 與逐批 replacement 讓每台機器可重建，並把壞版本 blast radius 限制在 wave。
- **B：** 錯誤。Mutable latest 使相同 template 在不同時間產生不同 runtime，破壞可重現與可靠 rollback。
- **C：** 錯誤。一次終止全部舊容量會造成中斷，也沒有先驗證新 AMI 的 production health。
- **D：** 錯誤。AMI 不會被原地覆寫並同步到 running instances；依賴可變 identity 也無法證明版本。
- **E：** 正確。跨 AZ headroom、健康門檻與可觀測 rollback 才能同時保護 availability 與 release safety。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon Machine Images in Amazon EC2 - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html)、[Use an instance refresh to update instances in an Auto Scaling group - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-instance-refresh.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「以profile選instance family，AMI固化可重建映像，placement group依l…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「EC2選型同時牽涉CPU、memory、network、accelerator、license與failure placement。」，所以「以profile選instance family，AMI固化可重建映像，placement group依latency或隔離需求使用。」能直接滿足它；若constraint改成「Graviton可降低price/performance但需architecture相容；Dedicated Host適合特定license與隔離。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「以profile選instance family，AMI固化可重建映像，placement group依latency或隔離需求使用。」。替代方案「Graviton可降低price/performance但需architecture相容；Dedicated Host適合特定license與隔離。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只依vCPU數選型，忽略network/EBS bandwidth、burstable credits與單AZ容量。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「EC2選型同時牽涉CPU、memory、network、accelerator、license與failure placement。」，排除會導致「只依vCPU數選型，忽略network/EBS bandwidth、burstable credits與單AZ容量。」的選項，再選「以profile選instance family，AMI固化可重建映像，placement group依latency或隔離需求使用。」。本章對應的代表task包括：SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「以profile選instance family，AMI固化可重建映像，placement group依latency或隔離需求使用。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「measure the constrained resource, then choose compute」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 33 章　EBS、Instance Store 與 EC2 Lifecycle

運算節點需要在持久性、IOPS、throughput、成本與ephemeral特性間選磁碟。

## 跟著一份工作走：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：資料庫log需穩定低延遲，transcoding scratch可在失敗後重建。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：運算節點需要在持久性、IOPS、throughput、成本與ephemeral特性間選磁碟。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是Amazon EBS，對照角色是EC2 instance store。我們選擇「需持久block用EBS；可重建scratch/cache用instance store；snapshot提供增量備份。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：資料庫log需穩定低延遲，transcoding scratch可在失敗後重建。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[Amazon EBS]
          │ 為EC2提供單AZ持久block volumes。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · EC2 instance store：提供可控制OS、runtime、network與storage的虛擬機compute。
  · EBS snapshots：建立EBS volume的增量、point-in-time block backup，供restore、c…

失敗時先找：把唯一資料放instance store，或誤以為stop/start後所有本機資料必然保留。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問Amazon EBS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon EBS和EC2 instance store並不是兩個任意的產品名稱。前者適合本章，是因為「需持久block用EBS；可重建scratch/cache用instance store；snapshot提供增量備份。」直接回應了眼前的問題；後者描述的「gp3可獨立配置IOPS/throughput；io2適合高耐久低延遲關鍵I/O。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：把唯一資料放instance store，或誤以為stop/start後所有本機資料必然保留。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「ephemeral compute requires external durable state」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon EBS | 為EC2提供單AZ持久block volumes。 | Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 |
| EC2 instance store | 提供可控制OS、runtime、network與storage的虛擬機compute。 | Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 |
| EBS snapshots | 建立EBS volume的增量、point-in-time block backup，供restore、copy與AMI使用。 | 首份snapshot保存已寫入blocks，後續只保存變更；刪除中間snapshot不會破壞仍被後續snapshot需要的blocks。 |

## 把全圖套進一個具體案例

**場景：** 資料庫log需穩定低延遲，transcoding scratch可在失敗後重建。

1. 故事的起點：資料庫log需穩定低延遲，transcoding scratch可在失敗後重建。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon EBS負責「為EC2提供單AZ持久block volumes。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：EC2 instance store、EBS snapshots各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「把唯一資料放instance store，或誤以為stop/start後所有本機資料必然保留。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon EBS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：運算節點需要在持久性、IOPS、throughput、成本與ephemeral特性間選磁碟。
- **具體例子／邊界：** 在「資料庫log需穩定低延遲，transcoding scratch可在失敗後重建。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### EC2 instance store

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：gp3可獨立配置IOPS/throughput；io2適合高耐久低延遲關鍵I/O。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：把唯一資料放instance store，或誤以為stop/start後所有本機資料必然保留。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：ephemeral compute requires external durable state。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### temporary credentials

具有到期時間的access key、secret與session token，通常由STS簽發，比長期key更易限制與輪替。

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### EC2 instance

AWS虛擬機執行個體，由AMI、instance type、network、storage與IAM instance profile共同定義。

### throughput

每秒能傳輸的資料量，偏向大型sequential I/O或network流量。

### data lake

以低成本object storage保存raw/curated資料，schema與多種compute/query engines可在之上演進。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### KMS key

KMS管理的高階key，用於Encrypt/Decrypt或GenerateDataKey並以key policy/grants控制使用者。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### IOPS

每秒可完成的I/O operations數，偏向小型random reads/writes能力。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### RPO

Recovery Point Objective，災難後可接受資料最多落後或遺失多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon EBS

- **功用：** 為EC2提供單AZ持久block volumes。
- **底層機制：** Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。
- **關鍵設定：** gp3/io2/st1/sc1 type、size、IOPS、throughput、AZ、encryption、delete-on-termination與Multi-Attach。
- **選擇時機：** boot disk、database、低延遲random I/O與需要in-place update的單instance state。
- **替換時機：** 多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。

### EC2 instance store

- **功用：** 提供可控制OS、runtime、network與storage的虛擬機compute。
- **底層機制：** Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。
- **關鍵設定：** instance family/size、AMI、subnet、security group、IAM instance profile、user data、tenancy與purchase option。
- **選擇時機：** 需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。
- **替換時機：** 只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。

### EBS snapshots

- **功用：** 建立EBS volume的增量、point-in-time block backup，供restore、copy與AMI使用。
- **底層機制：** 首份snapshot保存已寫入blocks，後續只保存變更；刪除中間snapshot不會破壞仍被後續snapshot需要的blocks。
- **關鍵設定：** snapshot schedule、retention、KMS key、cross-account/Region copy、archive tier、Fast Snapshot Restore與Recycle Bin。
- **選擇時機：** volume backup、跨Region DR copy、golden AMI與誤刪恢復。
- **替換時機：** 需要持續低RPO複寫與快速server recovery時搭配Elastic Disaster Recovery；snapshot不等於Multi-AZ volume。

## 考前與實作時再查：設定操作手冊

### Amazon EBS：逐項設定說明

#### `gp3/io2/st1/sc1 type`

- **控制什麼：** `gp3/io2/st1/sc1 type`選擇Amazon EBS的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `size`

- **控制什麼：** `size`設定Amazon EBS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「boot disk、database、低延遲random I/O與需要in-place update的單instance state。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `IOPS`

- **控制什麼：** `IOPS`設定Amazon EBS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「boot disk、database、低延遲random I/O與需要in-place update的單instance state。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `throughput`

- **控制什麼：** `throughput`設定Amazon EBS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「boot disk、database、低延遲random I/O與需要in-place update的單instance state。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `AZ`

- **控制什麼：** `AZ`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Amazon EBS前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「boot disk、database、低延遲random I/O與需要in-place update的單instance state。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EBS指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `delete-on-termination`

- **控制什麼：** `delete-on-termination`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「boot disk、database、低延遲random I/O與需要in-place update的單instance state。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EBS設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `Multi-Attach`

- **控制什麼：** `Multi-Attach`選擇Amazon EBS的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

### EC2 instance store：逐項設定說明

#### `instance family/size`

- **控制什麼：** `instance family/size`設定EC2 instance store的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `AMI`

- **控制什麼：** `AMI`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在EC2 instance store鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `subnet`

- **控制什麼：** `subnet`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在EC2 instance store的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `security group`

- **控制什麼：** `security group`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在EC2 instance store中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `IAM instance profile`

- **控制什麼：** `IAM instance profile`定義EC2 instance store管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `user data`

- **控制什麼：** `user data`是可版本化的啟動或工作規格，定義EC2 instance store建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `tenancy`

- **控制什麼：** `tenancy`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `purchase option`

- **控制什麼：** `purchase option`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

### EBS snapshots：逐項設定說明

#### `snapshot schedule`

- **控制什麼：** `snapshot schedule`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「volume backup、跨Region DR copy、golden AMI與誤刪恢復。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定EBS snapshots的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「volume backup、跨Region DR copy、golden AMI與誤刪恢復。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定EBS snapshots的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `KMS key`

- **控制什麼：** `KMS key`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「volume backup、跨Region DR copy、golden AMI與誤刪恢復。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在EBS snapshots指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `cross-account/Region copy`

- **控制什麼：** `cross-account/Region copy`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署EBS snapshots前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `archive tier`

- **控制什麼：** `archive tier`選擇EBS snapshots的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `Fast Snapshot Restore`

- **控制什麼：** `Fast Snapshot Restore`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「volume backup、跨Region DR copy、golden AMI與誤刪恢復。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在EBS snapshots設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

#### `Recycle Bin`

- **控制什麼：** 以retention rule暫存被刪除的EBS snapshots或AMIs，讓誤刪資源在保留期間內可以還原，而不是立即永久消失。
- **何時需要：** 管理員或automation可能誤刪snapshot／AMI，且合規要求提供一段可復原窗口時。
- **怎麼設定／驗證：** 依resource type、tag與Region建立最小必要retention rule，測試刪除與restore權限，並把Recycle Bin事件接到稽核與告警流程。
- **常見錯法：** Recycle Bin不是backup排程，也不會自動跨帳號隔離；retention太短來不及發現事故，太長則增加成本與敏感資料保留時間。

## 讀到這裡，請用自己的話說一次

1. Amazon EBS的責任：為EC2提供單AZ持久block volumes。
2. 底層機制：Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。
3. 第一個要看的設定：gp3/io2/st1/sc1 type、size、IOPS、throughput、AZ、encryption、delete-on-termination與Multi-Attach。
4. 選擇邏輯：需持久block用EBS；可重建scratch/cache用instance store；snapshot提供增量備份。
5. 不要混淆：EC2 instance store的責任是「提供可控制OS、runtime、network與storage的虛擬機compute。」；它不會自動取代Amazon EBS。
6. 替換訊號：多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。
7. 最常見錯法：把唯一資料放instance store，或誤以為stop/start後所有本機資料必然保留。
8. 可移植原則：ephemeral compute requires external durable state。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon EBS | 為EC2提供單AZ持久block volumes。 | Volume經network附加為block device，可format成filesystem；snapshot增量保存在regional service。 | boot disk、database、低延遲random I/O與需要in-place update的單instance state。 | 多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。 |
| EC2 instance store | 提供可控制OS、runtime、network與storage的虛擬機compute。 | Nitro hypervisor隔離instance；AMI建立root volume，ENI連VPC，instance profile提供temporary credentials。 | 需要OS存取、legacy agent、特定driver、長時間process或自訂network/storage時。 | 只需執行container選ECS/EKS/Fargate；短事件工作選Lambda以降低主機營運。 |
| EBS snapshots | 建立EBS volume的增量、point-in-time block backup，供restore、copy與AMI使用。 | 首份snapshot保存已寫入blocks，後續只保存變更；刪除中間snapshot不會破壞仍被後續snapshot需要的blocks。 | volume backup、跨Region DR copy、golden AMI與誤刪恢復。 | 需要持續低RPO複寫與快速server recovery時搭配Elastic Disaster Recovery；snapshot不等於Multi-AZ volume。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | gp3可獨立配置IOPS/throughput；io2適合高耐久低延遲關鍵I/O。 | 只有當題目條件明確改變時才可能合理。 | 把唯一資料放instance store，或誤以為stop/start後所有本機資料必然保留。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「gp3可獨立配置IOPS/throughput；io2適合高耐久低延遲關鍵I/O。」之間做選擇。
- 認得常考設定：gp3/io2/st1/sc1 type、size、IOPS、throughput、AZ、encryption、delete-on-termination與Multi-Attach。
- 對應官方tasks：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：多AZ共享file用EFS/FSx；object/data lake用S3；temporary最高local I/O可用instance store。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜Durable block storage 與 ephemeral scratch

一個 EC2 轉碼節點同時保存尚未寫入資料庫的工作 journal，以及可由 S3 原檔重新產生的 600 GiB shuffle files。節點會被 Auto Scaling 終止。哪個 storage layout 最合理？

A. Journal 與 shuffle 都只放 instance store，因 reboot 後通常仍存在
B. Journal 放 EBS；shuffle 可放 instance store，並讓工作在節點遺失時可從 S3 重建
C. 把 EBS snapshot 當成可直接 mount 且持續寫入的資料磁碟
D. 全部改放 S3 並假設資料庫需要的 in-place block writes 與 POSIX semantics 完全相同

**答案：B**

- **A：** 錯誤。Instance store 與 host/instance lifecycle 綁定，Auto Scaling replacement 會讓唯一 journal 遺失。
- **B：** 正確。需跨 stop/replacement 保留的 block state 用 EBS；可重建的高 I/O scratch 才適合 instance store。
- **C：** 錯誤。Snapshot 是 point-in-time backup，用來建立 volume，不是 running instance 可直接寫入的 block device。
- **D：** 錯誤。S3 是 object API；題目中的 journal 需要 block update semantics，不能只因 durability 高就直接替換。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)、[Instance store temporary block storage for EC2 instances - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/InstanceStorage.html)

### 練習題 2｜SAA｜EBS volume 與 snapshot 的 scope

團隊要把 us-east-1a 的 EBS data volume 恢復到 us-east-1c，之後再準備 us-west-2 DR。哪個流程符合 EBS scope？

A. 同一個 EBS volume 可直接同時 attach 到任意 Region 的 instances
B. Detach 後 volume 會自動成為可跨 Region mount 的 S3 object
C. 建立 regional snapshot，在 us-east-1c 由 snapshot 建新 volume；若要 us-west-2，先 copy snapshot 到目標 Region
D. 將 volume 加到 placement group，AWS 就會同步複寫到所有 AZ

**答案：C**

- **A：** 錯誤。EBS volume 是 AZ-scoped，不能直接 attach 到其他 AZ，更不能跨 Region attach。
- **B：** 錯誤。Detach 不改變 EBS volume 的類型或 scope；snapshot 也不是直接 mount 的 shared filesystem。
- **C：** 正確。Snapshot 是 Region 內可用的 backup，可在該 Region 任一 AZ 建 volume；跨 Region 需先 copy。
- **D：** 錯誤。Placement group 只控制 EC2 相對放置，不會複寫 EBS volume。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)、[Amazon EBS snapshots - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)

### 練習題 3｜SAP｜同時檢查 volume 與 instance EBS performance limits

資料庫的 WriteLatency 與 VolumeQueueLength 同時升高。io2 volume 尚未達 provisioned IOPS，但 EC2 的 EBS bandwidth 已接近該 instance type 上限。哪個行動最有可能直接改善？

A. 只再提高 volume IOPS，因 instance bandwidth 不會限制 EBS
B. 增加 snapshot frequency，讓 live writes 被 snapshots 分流
C. 關閉 EBS encryption，因 encryption 是 queue length 的唯一來源
D. 先換到有足夠 EBS bandwidth 的 instance size，並重新量測 IOPS、throughput 與 latency 是否仍需調整

**答案：D**

- **A：** 錯誤。有效效能同時受 volume 與 attached instance 的 EBS limits 約束；只調 IOPS 可能完全沒有作用。
- **B：** 錯誤。Snapshot 是 backup，不會替 running volume 分擔 write path。
- **C：** 錯誤。AWS-managed EBS encryption 並非題目證據指向的上限；任意關閉也會降低安全性。
- **D：** 正確。觀察值已指向 instance-side bandwidth ceiling；先解除該 ceiling，再判斷 volume provisioning。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon EBS volume performance - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-performance.html)、[Amazon EC2 instance types - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html)

### 練習題 4｜SAA｜gp3、io2、st1 與 sc1 選型

公司有兩個 volume：A 是一般 web app boot/data volume，需要可獨立調整 IOPS 與 throughput；B 是關鍵 OLTP，要求持續高 IOPS、低 latency 與較高 durability。哪個初始選擇最合理？

A. A 用 gp3，B 評估 io2，並以 workload benchmark 決定實際 IOPS/throughput
B. A 與 B 都用 st1，因 throughput optimized HDD 最適合 random OLTP
C. A 用 sc1 作 boot volume，B 用 gp2 且不量測效能
D. 兩者都用 instance store，因 EBS 不支援持久 block storage

**答案：A**

- **A：** 正確。gp3 適合一般用途並可獨立配置效能；io2 面向要求更高 durability 與 sustained IOPS 的關鍵工作。
- **B：** 錯誤。st1 適合大型 sequential throughput workload，不適合 latency-sensitive random OLTP 或 boot volume。
- **C：** 錯誤。sc1 是低頻存取 cold HDD，不能作 boot volume；gp2 也不是 B 的最佳起點。
- **D：** 錯誤。EBS 正是持久 network block storage；instance store 不適合唯一 OLTP state。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EBS volume types - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)

### 練習題 5｜SAA｜Application-consistent multi-volume snapshots

一個資料庫把 data 與 transaction log 放在兩個 EBS volumes。稽核要求 backup 必須能還原到一致交易點，但允許短暫 freeze writes。哪個做法最可靠？

A. 同時點兩次 CreateSnapshot 即可保證 application transaction consistency
B. 強制 detach 兩個 mounted volumes，不做 filesystem flush
C. 先用 database-native checkpoint/quiesce 或 freeze I/O，協調建立 multi-volume snapshots，之後定期 restore 驗證
D. 只確認 snapshot 狀態 completed，便可推論整個應用 RTO 已符合

**答案：C**

- **A：** 錯誤。Crash-consistent block snapshots 不等於 application transaction-consistent；應用可能仍有 buffered writes。
- **B：** 錯誤。未 flush 就強制 detach 可能造成 filesystem 或 database inconsistency。
- **C：** 正確。先協調應用寫入再擷取同一時間點，並以 restore test 證明資料與程序都可用。
- **D：** 錯誤。Snapshot 完成只證明 backup artifact 建立，不包含 restore、boot、replay 與 validation 時間。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EBS snapshots - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)

### 練習題 6｜SAA｜Instance store lifecycle 與資料遺失診斷

一台有 NVMe instance store 的 EC2 reboot 後 scratch data 仍在，但一次 stop/start 後資料消失，EBS root volume 則正常保留。哪個解釋正確？

A. Security group 在 stop/start 後封鎖了本機 NVMe device
B. EBS DeleteOnTermination 刪除了 instance store，但沒有刪 root volume
C. Snapshot lifecycle policy 清除了仍在執行中的 local disk
D. Instance store 只在該 instance/host lifecycle 內提供暫存；stop/start 或 host loss 不應被當成持久保證

**答案：D**

- **A：** 錯誤。Security group 控制 ENI network traffic，不控制本機 block device 是否存在。
- **B：** 錯誤。DeleteOnTermination 是 EBS block-device mapping 屬性，不管理 instance-store media。
- **C：** 錯誤。EBS snapshot policy 不會刪除 EC2 host 上的 instance store。
- **D：** 正確。Reboot 通常保留 instance store，但 stop、hibernate、terminate 或 host replacement 會失去其中資料。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Instance store temporary block storage for EC2 instances - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/InstanceStorage.html)

### 練習題 7｜SAP｜EBS 與 snapshot 成本最佳化

FinOps 發現數百個低利用率 io2 volumes、已停止 instances 留下的 unattached volumes，以及六年都未 restore 的標準 snapshots。RPO 30 分鐘、法規保存七年不變。哪個改善最完整？

A. 刪除所有 snapshots，只保留同 AZ EBS replication
B. 將所有 volumes 無測試改為 sc1，因 HDD 單價最低
C. Rightsize volume type/IOPS、清理確認無主的 volumes，以 lifecycle 將長期 snapshots 移入 archive，並持續執行 restore tests
D. 停止 EC2，因停止後 attached EBS 與 snapshots 都不再計費

**答案：C**

- **A：** 錯誤。同 AZ volume durability 不能取代可回到歷史時間點、可跨 AZ 建 volume 的 backup。
- **B：** 錯誤。sc1 不適合 latency-sensitive/random I/O；未測試的批次轉換可能破壞 SLO。
- **C：** 正確。按量測 rightsizing、清理 orphan 與 archive 長期備份，同時保留 restore 證據，兼顧成本與 RPO/retention。
- **D：** 錯誤。EC2 停止後，EBS provisioned storage 與 snapshots 仍持續計費。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon EBS volume types - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)、[Archive Amazon EBS snapshots - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/snapshot-archive.html)

### 練習題 8｜SAA｜DeleteOnTermination 的 per-volume 行為

ASG 以 launch template 啟動 instances；終止時 root volume 應自動刪除，但額外的 forensic EBS data volume 必須保留供事件調查。應如何設定？

A. 在 launch template 的 block device mappings 中，root 設 DeleteOnTermination=true，forensic volume 設 false
B. 只在啟動 API request 覆寫 forensic volume，但不更新 launch template；之後 ASG replacements 會自動沿用這次覆寫
C. 只建立 snapshot lifecycle policy，不設定 block-device mapping；snapshot policy 會自動把所有 data volumes 改成保留
D. 用 termination lifecycle hook 複製資料，但仍把 forensic volume 設 DeleteOnTermination=true，並假設 hook 永遠成功

**答案：A**

- **A：** 正確。DeleteOnTermination 是每個 EBS mapping 的 lifecycle 設定，可讓 root 與 data volume 採不同保留策略。
- **B：** 錯誤。一次性的 RunInstances override 不會回寫 launch template；下一次 ASG replacement 仍依 template 的 block-device mapping 建立與刪除 volumes。
- **C：** 錯誤。Snapshot lifecycle policy 可以排程備份，但不會改寫既有 launch template 的 DeleteOnTermination；保留原 volume 與保留 snapshot 是不同契約。
- **D：** 錯誤。Lifecycle hook 可提供額外處理時間，但有 timeout 與失敗路徑；若 volume 仍設定刪除，就不能把唯一 forensic evidence 依賴在 hook 一定完成。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EBS volumes - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)

### 練習題 9｜SAP｜Encrypted EBS 的跨 Region DR 與 restore latency

一個 EBS-based application 要在另一 Region 於 45 分鐘內恢復。所有 snapshots 以 customer managed KMS key 加密；測試發現大量新 volumes 的 first-read 初始化讓應用超時。選擇兩項。

A. 把來源 AZ 的 EBS volumes 直接 attach 到目標 Region
B. 將 snapshots copy 到目標 Region，使用目標端可授權的 KMS key，並預先建立 IAM/key policy 與 restore runbook
C. 啟用 EBS Multi-Attach，讓同一 volume 同時跨 Region 寫入
D. 對關鍵 snapshots/AZ 評估 Fast Snapshot Restore，或在演練中預初始化 volumes 並量測完整 RTO
E. 只 copy AMI；running instance 的 ENI、security groups 與 application state 會自動搬移

**答案：B、D**

- **A：** 錯誤。EBS volume 是 AZ-scoped，不能跨 Region attach。
- **B：** 正確。跨 Region DR 需要目標 Region 的 snapshot artifact、可用加密金鑰與完整授權。
- **C：** 錯誤。Multi-Attach 限於相容 volume/instances 且同一 AZ，不是跨 Region replication。
- **D：** 正確。FSR 或預初始化可降低由 snapshot 新建 volume 的首次讀取延遲，但必須用實測證明 RTO。
- **E：** 錯誤。AMI copy 不會搬移 VPC identity、security configuration 或持續變動的 application state。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Copy an Amazon EBS snapshot - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copy-snapshot.html)、[Amazon EBS fast snapshot restore - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-fast-snapshot-restore.html)

### 練習題 10｜SAP｜可驗證的 EBS database recovery

單 AZ EC2 database 使用加密 EBS。董事會要求降低 operator deletion 與 volume failure 的資料損失風險，並提供『真的能在四小時內恢復』的證據。選擇兩項。

A. 依 RPO 建立 application-consistent snapshots/backups，保護 KMS key 與刪除權限，並視需要跨帳號或跨 Region 保存
B. 只監控 EC2 StatusCheckFailed；metric 正常即可視為 backup 成功
C. 將同一 EBS volume Multi-Attach 到另一 AZ 的 EC2
D. 只提高 provisioned IOPS，因較高 IOPS 會防止誤刪
E. 定期在隔離環境 restore，啟動 application、驗證資料並量測從宣告事故到可服務的完整 RTO

**答案：A、E**

- **A：** 正確。符合 RPO 的一致備份與獨立權限邊界可處理故障、誤刪與部分帳號風險。
- **B：** 錯誤。Instance health 不證明存在歷史 recovery point，也不測資料可還原性。
- **C：** 錯誤。EBS Multi-Attach 不跨 AZ，且共享 block device 不是防止 logical corruption 或 deletion 的 backup。
- **D：** 錯誤。IOPS 是效能設定，不提供 point-in-time recovery。
- **E：** 正確。只有實際 restore、資料驗證與計時才能證明四小時 RTO，而非只看 backup job completed。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon EBS snapshots - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)、[Restore testing - AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「需持久block用EBS；可重建scratch/cache用instance store；snapshot…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「運算節點需要在持久性、IOPS、throughput、成本與ephemeral特性間選磁碟。」，所以「需持久block用EBS；可重建scratch/cache用instance store；snapshot提供增量備份。」能直接滿足它；若constraint改成「gp3可獨立配置IOPS/throughput；io2適合高耐久低延遲關鍵I/O。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「需持久block用EBS；可重建scratch/cache用instance store；snapshot提供增量備份。」。替代方案「gp3可獨立配置IOPS/throughput；io2適合高耐久低延遲關鍵I/O。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「把唯一資料放instance store，或誤以為stop/start後所有本機資料必然保留。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「運算節點需要在持久性、IOPS、throughput、成本與ephemeral特性間選磁碟。」，排除會導致「把唯一資料放instance store，或誤以為stop/start後所有本機資料必然保留。」的選項，再選「需持久block用EBS；可重建scratch/cache用instance store；snapshot提供增量備份。」。本章對應的代表task包括：SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.1 Determine high-performing and/or scalable storage solutions；SAA-4.1 Design cost-optimized storage solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「需持久block用EBS；可重建scratch/cache用instance store；snapshot提供增量備份。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「ephemeral compute requires external durable state」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 34 章　Auto Scaling 與 Scaling Metrics

容量必須跟需求調整，但錯誤metric會讓系統在過載後才反應。

## 跟著一份工作走：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：Worker從SQS取工作，尖峰時queue age升高但CPU只有30%。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：容量必須跟需求調整，但錯誤metric會讓系統在過載後才反應。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看Amazon EC2 Auto Scaling如何接手工作，再看AWS Auto Scaling何時更合適，最後用設定與考題驗證「Target tracking用與負載近似成比例的metric，scheduled/predictive處理已知週期，保留warmup。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：Worker從SQS取工作，尖峰時queue age升高但CPU只有30%。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[Amazon EC2 Auto Scaling]
          │ 依健康狀態與需求訊號維持、替換並調整EC2 fleet。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · AWS Auto Scaling：以scaling plans跨多種scalable resources協調容量預測與target trac…
  · Amazon CloudWatch：收集metrics、logs、events與synthetic/real-user signals以監控A…

失敗時先找：以平均CPU掩蓋hot partition，scale-in過快移除仍處理工作的instance。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問Amazon EC2 Auto Scaling有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon EC2 Auto Scaling和AWS Auto Scaling並不是兩個任意的產品名稱。前者適合本章，是因為「Target tracking用與負載近似成比例的metric，scheduled/predictive處理已知週期，保留warmup。」直接回應了眼前的問題；後者描述的「CPU不適合所有workload；queue depth per worker或requests per target可能更直接。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：以平均CPU掩蓋hot partition，scale-in過快移除仍處理工作的instance。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「scale on demand signals, protect work during transitions」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon EC2 Auto Scaling | 依健康狀態與需求訊號維持、替換並調整EC2 fleet。 | Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 |
| AWS Auto Scaling | 以scaling plans跨多種scalable resources協調容量預測與target tracking。 | 服務從CloudWatch demand history建立forecast並調整支援資源；實際可伸縮邊界仍由各服務的min/max與scalable target決定。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 |

## 把全圖套進一個具體案例

**場景：** Worker從SQS取工作，尖峰時queue age升高但CPU只有30%。

1. 故事的起點：Worker從SQS取工作，尖峰時queue age升高但CPU只有30%。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon EC2 Auto Scaling負責「依健康狀態與需求訊號維持、替換並調整EC2 fleet。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS Auto Scaling、Amazon CloudWatch各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「以平均CPU掩蓋hot partition，scale-in過快移除仍處理工作的instance。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon EC2 Auto Scaling

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：容量必須跟需求調整，但錯誤metric會讓系統在過載後才反應。
- **具體例子／邊界：** 在「Worker從SQS取工作，尖峰時queue age升高但CPU只有30%。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS Auto Scaling

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：CPU不適合所有workload；queue depth per worker或requests per target可能更直接。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：以平均CPU掩蓋hot partition，scale-in過快移除仍處理工作的instance。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：scale on demand signals, protect work during transitions。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### metric

可聚合的時間序列數值，例如latency、error rate或queue age。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### alarm

metric符合threshold/evaluation條件時改變狀態並通知或觸發action。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### trace

把同一request跨服務的spans串起來，顯示每段時間、錯誤與dependency。

### Spot

使用AWS剩餘EC2容量的折扣模式，可能收到短通知後被中斷，適合可重試、可分散或checkpoint workloads。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### Amazon EC2 Auto Scaling

- **功用：** 依健康狀態與需求訊號維持、替換並調整EC2 fleet。
- **底層機制：** Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。
- **關鍵設定：** min/max/desired、launch template、subnets、health check grace、instance warmup、target tracking、mixed instances與lifecycle hooks。
- **選擇時機：** stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。
- **替換時機：** 它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。

### AWS Auto Scaling

- **功用：** 以scaling plans跨多種scalable resources協調容量預測與target tracking。
- **底層機制：** 服務從CloudWatch demand history建立forecast並調整支援資源；實際可伸縮邊界仍由各服務的min/max與scalable target決定。
- **關鍵設定：** scaling plan、resource selection、forecast、target utilization、min/max capacity與dynamic/predictive scaling。
- **選擇時機：** 舊式需要跨多資源統一scaling plan的情境，或比較predictive與dynamic scaling概念時。
- **替換時機：** 新工作負載通常直接使用各服務的Application Auto Scaling或EC2 Auto Scaling政策，取得更完整功能。

### Amazon CloudWatch

- **功用：** 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。
- **底層機制：** AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。
- **關鍵設定：** namespace/dimensions、metric resolution、statistics/percentiles、alarm periods、dashboards與retention。
- **選擇時機：** resource與application監控、告警、autoscaling signal與operations dashboard。
- **替換時機：** API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。

## 考前與實作時再查：設定操作手冊

### Amazon EC2 Auto Scaling：逐項設定說明

#### `min/max/desired`

- **控制什麼：** `min/max/desired`設定Amazon EC2 Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `launch template`

- **控制什麼：** `launch template`是可版本化的啟動或工作規格，定義Amazon EC2 Auto Scaling建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `subnets`

- **控制什麼：** `subnets`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EC2 Auto Scaling的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `health check grace`

- **控制什麼：** `health check grace`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon EC2 Auto Scaling的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `instance warmup`

- **控制什麼：** `instance warmup`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon EC2 Auto Scaling的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `target tracking`

- **控制什麼：** `target tracking`指定Amazon EC2 Auto Scaling讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `mixed instances`

- **控制什麼：** `mixed instances`設定Amazon EC2 Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `lifecycle hooks`

- **控制什麼：** `lifecycle hooks`把Amazon EC2 Auto Scaling與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### AWS Auto Scaling：逐項設定說明

#### `scaling plan`

- **控制什麼：** `scaling plan`設定AWS Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「舊式需要跨多資源統一scaling plan的情境，或比較predictive與dynamic scaling概念時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `resource selection`

- **控制什麼：** `resource selection`指定AWS Auto Scaling讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `forecast`

- **控制什麼：** `forecast`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「舊式需要跨多資源統一scaling plan的情境，或比較predictive與dynamic scaling概念時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Auto Scaling設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

#### `target utilization`

- **控制什麼：** `target utilization`指定AWS Auto Scaling讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `min/max capacity`

- **控制什麼：** `min/max capacity`設定AWS Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「舊式需要跨多資源統一scaling plan的情境，或比較predictive與dynamic scaling概念時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `dynamic/predictive scaling`

- **控制什麼：** `dynamic/predictive scaling`設定AWS Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「舊式需要跨多資源統一scaling plan的情境，或比較predictive與dynamic scaling概念時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

### Amazon CloudWatch：逐項設定說明

#### `namespace/dimensions`

- **控制什麼：** `namespace/dimensions`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「resource與application監控、告警、autoscaling signal與operations dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出Amazon CloudWatch的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `metric resolution`

- **控制什麼：** `metric resolution`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「resource與application監控、告警、autoscaling signal與operations dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon CloudWatch選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `statistics/percentiles`

- **控制什麼：** `statistics/percentiles`控制metric如何聚合、與門檻比較、需要幾個datapoints，以及缺資料與alarm action如何處理。
- **何時需要：** 需要可靠告警而不能被單點雜訊、短暫missing data或平均值掩蓋tail latency時。
- **怎麼設定／驗證：** 選擇正確namespace/dimensions/statistic，設定period、evaluation periods、DatapointsToAlarm、comparison與missing-data策略，再演練alarm。
- **常見錯法：** 平均值會隱藏p99；missing data設錯可能把停止上報當健康或故障，alarm action也需要自己的IAM與rollback保護。

#### `alarm periods`

- **控制什麼：** `alarm periods`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「resource與application監控、告警、autoscaling signal與operations dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon CloudWatch的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `dashboards`

- **控制什麼：** `dashboards`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「resource與application監控、告警、autoscaling signal與operations dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon CloudWatch選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

#### `retention`

- **控制什麼：** `retention`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「resource與application監控、告警、autoscaling signal與operations dashboard。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon CloudWatch的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

## 讀到這裡，請用自己的話說一次

1. Amazon EC2 Auto Scaling的責任：依健康狀態與需求訊號維持、替換並調整EC2 fleet。
2. 底層機制：Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。
3. 第一個要看的設定：min/max/desired、launch template、subnets、health check grace、instance warmup、target tracking、mixed instances與lifecycle hooks。
4. 選擇邏輯：Target tracking用與負載近似成比例的metric，scheduled/predictive處理已知週期，保留warmup。
5. 不要混淆：AWS Auto Scaling的責任是「以scaling plans跨多種scalable resources協調容量預測與target tracking。」；它不會自動取代Amazon EC2 Auto Scaling。
6. 替換訊號：它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。
7. 最常見錯法：以平均CPU掩蓋hot partition，scale-in過快移除仍處理工作的instance。
8. 可移植原則：scale on demand signals, protect work during transitions。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon EC2 Auto Scaling | 依健康狀態與需求訊號維持、替換並調整EC2 fleet。 | Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 | stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。 | 它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。 |
| AWS Auto Scaling | 以scaling plans跨多種scalable resources協調容量預測與target tracking。 | 服務從CloudWatch demand history建立forecast並調整支援資源；實際可伸縮邊界仍由各服務的min/max與scalable target決定。 | 舊式需要跨多資源統一scaling plan的情境，或比較predictive與dynamic scaling概念時。 | 新工作負載通常直接使用各服務的Application Auto Scaling或EC2 Auto Scaling政策，取得更完整功能。 |
| Amazon CloudWatch | 收集metrics、logs、events與synthetic/real-user signals以監控AWS workload。 | AWS services送metrics；agents/apps送custom telemetry；alarms依時間窗口與statistics轉狀態。 | resource與application監控、告警、autoscaling signal與operations dashboard。 | API audit用CloudTrail；configuration history/compliance用Config；distributed trace用X-Ray/OTel。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | CPU不適合所有workload；queue depth per worker或requests per target可能更直接。 | 只有當題目條件明確改變時才可能合理。 | 以平均CPU掩蓋hot partition，scale-in過快移除仍處理工作的instance。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「CPU不適合所有workload；queue depth per worker或requests per target可能更直接。」之間做選擇。
- 認得常考設定：min/max/desired、launch template、subnets、health check grace、instance warmup、target tracking、mixed instances與lifecycle hooks。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA｜Target tracking、scheduled 與 predictive scaling

票務網站有三種需求：每天 08:00 可預知的開賣、每週模式穩定且已有數月歷史、以及偶發新聞造成的未知流量。若每次只能選最貼合的 policy，哪個對應正確？

A. 三者都只用 step scaling，因其他 policy 不能增加 desired capacity
B. 每天開賣用 scheduled；週期流量可評估 predictive；未知且可量測 demand 用 target tracking
C. 只提高 max size，不需要任何 scaling policy
D. 三者都依每台 instance 的 root disk 使用率擴縮

**答案：B**

- **A：** 錯誤。Step scaling 可用，但沒有利用已知時間或穩定週期，也不是未知需求最簡單的 target-maintenance 方案。
- **B：** 正確。Scheduled 回應已知時間，predictive 利用歷史 forecast，target tracking 對即時可比例化需求調整容量。
- **C：** 錯誤。Max 只是上限，不會自行改變 desired capacity。
- **D：** 錯誤。Root disk 使用率通常不隨 fleet capacity 呈可用的需求比例，容易造成錯誤 scaling。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-scaling-policies.html)

### 練習題 2｜SAA｜ASG desired-capacity reconciliation

CloudWatch target tracking policy 將 ASG desired capacity 從 6 改為 10。接下來由哪個元件依哪些資料建立新容量？

A. CloudWatch alarm 直接複製 running instances，ASG 不參與
B. Launch template 會原地把六台 instance 的 vCPU 調大
C. ASG 依 launch template、允許的 subnets/AZ 與目前健康容量啟動 instances，直到實際狀態接近 desired
D. 用 EC2 Fleet 直接啟動四台 instances，但不更新 ASG desired capacity 或把 instances 納入 ASG 管理

**答案：C**

- **A：** 錯誤。Alarm/policy 提供 scaling 決策，真正的 fleet reconciliation 由 ASG 執行。
- **B：** 錯誤。Launch template 定義新 launches，不會原地 resize 已執行 instances。
- **C：** 正確。ASG 是 capacity controller，依 template 與 placement constraints 維持 desired healthy fleet。
- **D：** 錯誤。EC2 Fleet 能建立容量，但這四台不會自動成為該 ASG 的受管成員；ASG 仍會依 desired capacity 繼續調和，造成重複或未受控容量。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/how-asg-works.html)

### 練習題 3｜SAP｜SQS backlog-per-instance scaling metric

SQS worker 平均每 30 秒完成一個 job，SLO 要求 oldest message 不超過 5 分鐘。CPU 長期只有 25%，尖峰時 backlog 由 1,000 增到 20,000。哪個 metric 最適合 target tracking？

A. Queue 中總訊息數，不除以目前可工作的 instance 數
B. ALB HealthyHostCount，雖然 workers 不接收 HTTP
C. ASG desired capacity 本身，target 設為固定 10
D. Backlog per active worker，target 由可接受等待時間與每 worker 處理率推導，並以 ApproximateAgeOfOldestMessage 驗證

**答案：D**

- **A：** 錯誤。總 backlog 不隨加入 workers 自然正規化，同一數值在不同 fleet size 代表不同壓力。
- **B：** 錯誤。Healthy host 是 capacity/health 指標，不是 queue demand，且此 workload 沒有 ALB。
- **C：** 錯誤。Desired capacity 是控制結果，不是外部需求訊號。
- **D：** 正確。每 worker backlog 會在 capacity 增加時下降，且能以處理率與等待 SLO 推導合理 target。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[Configure scaling based on Amazon SQS - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/scale-sqs-queue-cli.html)

### 練習題 4｜SAA｜Launch template 與 instance warmup

新的 web instance 需要 8 分鐘下載模型並 warm cache，前 5 分鐘 CPU 會達 95%。目前 target tracking 反覆過度 scale-out。哪個設定組合最合理？

A. 使用 versioned launch template，設定接近實際初始化時間的 default instance warmup 與 health grace，再以 readiness 決定接流量
B. 把所有 cooldown 設為 0，讓 policy 更快重複擴容
C. 只把 ALB idle timeout 增加到 8 分鐘
D. 將 min、desired、max 全設為同一值，仍宣稱由需求自動擴縮

**答案：A**

- **A：** 正確。Warmup 避免尚未穩定的新 instance 過早影響 aggregate metric，health grace/readiness 則保護啟動期。
- **B：** 錯誤。零 cooldown/warmup 會把初始化 CPU 誤認為持續需求，進一步放大 over-scaling。
- **C：** 錯誤。ALB idle timeout 管理 client connection，不解決 ASG metric 對初始化容量的判讀。
- **D：** 錯誤。固定三個值會關閉 elasticity，只是 overprovisioning。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Set the default instance warmup for an Auto Scaling group - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-default-instance-warmup.html)、[Health checks for instances in an Auto Scaling group - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-health-checks.html)

### 練習題 5｜SAA｜Lifecycle hook 與 safe scale-in

ASG workers 執行最長 12 分鐘、不能安全重頭做的 simulation。Scale-in 時必須停止接新 job、保存 checkpoint，再終止 instance。哪個機制最適合？

A. 延長 CloudWatch metric period，讓 instance 自動完成工作
B. 建立 termination lifecycle hook，worker 停止取件並 checkpoint，完成後送 CompleteLifecycleAction；同時設定 timeout/default result
C. 使用 health check grace period 作永久 draining timer
D. 關閉 ASG 與 ELB health checks，避免 instance 被替換

**答案：B**

- **A：** 錯誤。Metric period 只改變觀察窗，不會攔截 termination 或通知 application。
- **B：** 正確。Lifecycle hook 將 instance 暫停於 terminating wait，讓 application 執行 bounded drain/checkpoint 後明確完成。
- **C：** 錯誤。Health grace 用於新 instance 啟動，不是 scale-in draining protocol。
- **D：** 錯誤。關閉 health replacement 會保留失效容量，也無法安全協調正常 scale-in。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon EC2 Auto Scaling lifecycle hooks - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html)

### 練習題 6｜SAP｜ASG launch failure 診斷

Target tracking 已把 desired capacity 提高，但新 instances 長時間 Pending，Activity history 顯示部分 InsufficientInstanceCapacity、部分 subnet has insufficient free addresses。第一個完整診斷方向是什麼？

A. 重建 ALB certificate，因 TLS 失敗會阻止 EC2 launch
B. 增加 deregistration delay，讓 subnet 產生更多 IP
C. 依 scaling activity reason 檢查 instance-type/AZ capacity、subnet IP、quota、AMI 與 launch-template permissions，並用多 AZ/type 降低容量集中
D. 降低 desired capacity，讓錯誤消失即視為根因修復

**答案：C**

- **A：** 錯誤。ACM/ALB TLS 與 EC2 placement、subnet address allocation 是不同路徑。
- **B：** 錯誤。Deregistration delay 控制 target draining，不會增加 subnet 可用位址。
- **C：** 正確。Activity reason 已提供兩個具體 constraint；應逐一修正並增加 capacity pool 多樣性。
- **D：** 錯誤。降低需求只隱藏無法 launch 的問題，未恢復目標 capacity。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Troubleshoot Amazon EC2 Auto Scaling: EC2 instance launch failures - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ts-as-instancelaunchfailure.html)、[Auto Scaling groups with multiple instance types and purchase options - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-mixed-instances-groups.html)

### 練習題 7｜SAA｜Mixed instances 的 baseline 與 burst

Stateless API 的最低穩定容量為 20 units，促銷時最多需要 100 units；應用能容忍部分 instance interruption。哪個 ASG 策略最能兼顧可靠與成本？

A. 單一 AZ、單一最便宜 Spot type，因價格最低就代表 capacity 最多
B. 全部使用 Dedicated Hosts，避免 Spot interruption
C. 只購買 Savings Plans，不設定 ASG 或 capacity providers
D. Mixed instances policy：On-Demand baseline，加上多 instance types/AZ 的 capacity-optimized Spot burst，並啟用健康替換/再平衡

**答案：D**

- **A：** 錯誤。集中在單一 Spot pool 與 AZ 會同時放大 shortage、interruption 與 AZ risk。
- **B：** 錯誤。Dedicated Hosts 不符合一般 stateless burst 的成本目標。
- **C：** 錯誤。Savings Plans 是 billing discount，不會排程、擴縮或替換 capacity。
- **D：** 正確。穩定 capacity 用 On-Demand 保底，可中斷 burst 分散多個 Spot pools，兼顧 availability 與 cost。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Auto Scaling groups with multiple instance types and purchase options - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-mixed-instances-groups.html)、[Use allocation strategies to determine how EC2 Fleet or Spot Fleet fulfills Spot and On-Demand capacity - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-fleet-allocation-strategy.html)

### 練習題 8｜SAA｜Target tracking metric proportionality

Web fleet 每台 instance 的 request capacity 大致相同。下列哪個 metric 最符合 target tracking『加入 capacity 後 metric 應向 target 回落』的特性？

A. ALBRequestCountPerTarget，並以 latency/error 確認 target 值
B. 應用自上線以來累積的 lifetime request count
C. 目前 deployment version number
D. HealthyHostCount 作唯一 demand 指標

**答案：A**

- **A：** 正確。每 target request 數會隨健康容量增加而下降，能近似表示 demand/capacity 比。
- **B：** 錯誤。累積 counter 只增不減，不會因 scale-out 回落。
- **C：** 錯誤。Deployment version number 是離散的 release metadata；增加 instances 不會讓它朝某個 demand target 回落，因此不符合 target tracking 的比例性要求。
- **D：** 錯誤。HealthyHostCount 描述可用容量，不表示目前每台承受的請求壓力。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)

### 練習題 9｜SAP｜跨帳號 instance refresh 與 rollback

平台要在 80 個帳號更新數百個 ASGs 的 AMI。要求每批至少保留 90% healthy capacity，錯誤率超標即停止，並能回到前版。選擇兩項。

A. 讓各 ASG 永遠引用 $Latest，部署中再反覆修改同一 launch template version
B. 發布可分享的 versioned AMI 與固定 launch template version，分 wave 執行 instance refresh
C. 以 minimum healthy percentage、checkpoints 與 CloudWatch alarms 控制每 wave，保留前版 template 作 rollback
D. SSH 進 running instances 原地 patch，因這樣不需要替換
E. 一次 terminate 全部舊 instances，讓 ASG 同時重建

**答案：B、C**

- **A：** 錯誤。Mutable $Latest 讓部署輸入不穩定，也難以精確回到已知版本。
- **B：** 正確。Immutable AMI/template version 讓每批 artifact 可追蹤且可重現。
- **C：** 正確。Healthy threshold、checkpoint 與 alarm 共同限制 blast radius，前版則提供可執行 rollback。
- **D：** 錯誤。In-place patch 造成 snowflake drift，無法證明新 launches 與舊 instances 一致。
- **E：** 錯誤。全量替換違反 90% healthy capacity，且先失去可立即回復的舊 fleet。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Use an instance refresh to update instances in an Auto Scaling group - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-instance-refresh.html)、[Amazon Machine Images in Amazon EC2 - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html)

### 練習題 10｜SAP｜Queue worker scaling 與工作完整性

SQS workers 必須在尖峰後 5 分鐘內把等待時間降回 SLO；單一 job 可能跑 4 分鐘，至少一次投遞不可造成重複扣款。選擇兩項。

A. 以 backlog per active worker 與 oldest-message age 建立 scaling signal，target 納入已知 service time
B. 只用平均 CPU，因所有 queue workload 都與 CPU 成比例
C. Scale-in 前停止取新訊息，使用足夠 visibility timeout、idempotency key 與 lifecycle draining/checkpoint
D. 把 message retention 降到 5 分鐘，讓 backlog 自動消失
E. 每次 scale-in 前 purge queue，避免其他 worker 取得舊 job

**答案：A、C**

- **A：** 正確。這把 demand、現有 capacity 與處理時間連成可計算的等待目標。
- **B：** 錯誤。題目沒有證明 CPU 是瓶頸；I/O-bound workers 可能在 queue 堆積時仍維持低 CPU。
- **C：** 正確。Scaling 只處理容量，visibility/idempotency/draining 才保護至少一次投遞與 termination transition。
- **D：** 錯誤。縮短 retention 會丟棄尚未處理的有效工作，並非降低真實 demand。
- **E：** 錯誤。Purge 會刪除整個 backlog，直接破壞資料完整性。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Configure scaling based on Amazon SQS - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/scale-sqs-queue-cli.html)、[Amazon EC2 Auto Scaling lifecycle hooks - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Target tracking用與負載近似成比例的metric，scheduled/predictive處…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「容量必須跟需求調整，但錯誤metric會讓系統在過載後才反應。」，所以「Target tracking用與負載近似成比例的metric，scheduled/predictive處理已知週期，保留warmup。」能直接滿足它；若constraint改成「CPU不適合所有workload；queue depth per worker或requests per target可能更直接。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Target tracking用與負載近似成比例的metric，scheduled/predictive處理已知週期，保留warmup。」。替代方案「CPU不適合所有workload；queue depth per worker或requests per target可能更直接。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「以平均CPU掩蓋hot partition，scale-in過快移除仍處理工作的instance。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「容量必須跟需求調整，但錯誤metric會讓系統在過載後才反應。」，排除會導致「以平均CPU掩蓋hot partition，scale-in過快移除仍處理工作的instance。」的選項，再選「Target tracking用與負載近似成比例的metric，scheduled/predictive處理已知週期，保留warmup。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Target tracking用與負載近似成比例的metric，scheduled/predictive處理已知週期，保留warmup。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「scale on demand signals, protect work during transitions」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 35 章　ALB＋ASG 高可用 Web Tier

Stateless web tier需要跨AZ分流、健康檢查、自動替換與安全deployment。

## 跟著一份工作走：先從故事開始

把鏡頭拉到一個真實的production現場：網站instance仍可ping但thread pool卡死，部署時不可讓使用者掉session。 監控畫面只會告訴你某些數字變紅，卻不會自動解釋因果。我們要先還原一條完整故事：請求如何進來、在哪裡做決定、資料何時改變，以及錯誤如何被使用者看見。

要讓故事繼續，我們必須先解開核心矛盾：Stateless web tier需要跨AZ分流、健康檢查、自動替換與安全deployment。 這個問題會幫我們排除那些技術上做得到、卻沒有滿足真正需求的方案。 這條問題線會一路貫穿正常流程、故障處理與最後的考題。

如果你需要一個暫時的比喻，可以記成：Load balancer像接待櫃檯：ALB會讀懂HTTP內容再分流，NLB主要依連線資訊轉送，GWLB則把流量帶去接受安全檢查。 接待櫃檯不能修復後端保存錯誤狀態，也不能取代application authorization。 後面的設定與failure mode會逐步指出這個比喻哪裡成立、哪裡不能再往下套。

有了問題和畫面，AWS名稱才不會只是縮寫。Application Load Balancer是這一章的入口，Amazon EC2 Auto Scaling用來畫出邊界；主要方向「ALB跨至少兩AZ，ASG維持desired capacity，application health決定target是否接流量。」會在後面的正常流程與故障流程中被逐步證明。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：網站instance仍可ping但thread pool卡死，部署時不可讓使用者掉session。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[Application Load Balancer]
          │ 提供HTTP/HTTPS Layer 7 routing與web workload入口。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · Amazon EC2 Auto Scaling：依健康狀態與需求訊號維持、替換並調整EC2 fleet。
  · Amazon ElastiCache：提供managed Valkey/Redis OSS/Memcached記憶體data store。

失敗時先找：只用EC2 status check而忽略應用deadlock，或把session放local disk阻止替換。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問Application Load Balancer有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Application Load Balancer和Amazon EC2 Auto Scaling並不是兩個任意的產品名稱。前者適合本章，是因為「ALB跨至少兩AZ，ASG維持desired capacity，application health決定target是否接流量。」直接回應了眼前的問題；後者描述的「Sticky sessions可暫時支援legacy session，但更好的長期方案是外部session store。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只用EC2 status check而忽略應用deadlock，或把session放local disk阻止替換。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「make instances disposable and health application-aware」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Application Load Balancer | 提供HTTP/HTTPS Layer 7 routing與web workload入口。 | 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。 |
| Amazon EC2 Auto Scaling | 依健康狀態與需求訊號維持、替換並調整EC2 fleet。 | Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 |

## 把全圖套進一個具體案例

**場景：** 網站instance仍可ping但thread pool卡死，部署時不可讓使用者掉session。

1. 故事的起點：網站instance仍可ping但thread pool卡死，部署時不可讓使用者掉session。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Application Load Balancer負責「提供HTTP/HTTPS Layer 7 routing與web workload入口。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EC2 Auto Scaling、Amazon ElastiCache各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只用EC2 status check而忽略應用deadlock，或把session放local disk阻止替換。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「極低延遲TCP/UDP、static IP或保留source IP需求用NLB。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Application Load Balancer

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Stateless web tier需要跨AZ分流、健康檢查、自動替換與安全deployment。
- **具體例子／邊界：** 在「網站instance仍可ping但thread pool卡死，部署時不可讓使用者掉session。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EC2 Auto Scaling

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Sticky sessions可暫時支援legacy session，但更好的長期方案是外部session store。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只用EC2 status check而忽略應用deadlock，或把session放local disk阻止替換。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：make instances disposable and health application-aware。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### durability

已接受資料在故障後仍存在的程度；高durability不代表服務當下可讀。

### stickiness

以cookie讓同一client暫時持續導向同一target；它是相容legacy state的折衷，不是高可用session store。

### listener

在load balancer指定protocol/port等待client connection的入口。

### Multi-AZ

把服務副本或compute分散在同一Region的多個AZ，以承受單一AZ故障；不等於跨Region DR。

### template

宣告Parameters、Resources、Conditions、Outputs等desired infrastructure的版本化YAML/JSON文件。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### Layer 7

理解HTTP等application protocol，可依host/path/header做routing；ALB與CloudFront屬於此類。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### Spot

使用AWS剩餘EC2容量的折扣模式，可能收到短通知後被中斷，適合可重試、可分散或checkpoint workloads。

### AMI

Amazon Machine Image，建立EC2 root volume與啟動環境的版本化image reference。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

### UDP

不先建立可靠connection的datagram協定，延遲低但application需自行處理遺失與順序。

## 回到 AWS：Components、功用與責任邊界

### Application Load Balancer

- **功用：** 提供HTTP/HTTPS Layer 7 routing與web workload入口。
- **底層機制：** 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。
- **關鍵設定：** listeners/certificates、rules priority、target type、health path、stickiness、idle timeout與access logs。
- **選擇時機：** 網站、microservices、ECS dynamic ports、gRPC或需要content-based routing。
- **替換時機：** 極低延遲TCP/UDP、static IP或保留source IP需求用NLB。

### Amazon EC2 Auto Scaling

- **功用：** 依健康狀態與需求訊號維持、替換並調整EC2 fleet。
- **底層機制：** Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。
- **關鍵設定：** min/max/desired、launch template、subnets、health check grace、instance warmup、target tracking、mixed instances與lifecycle hooks。
- **選擇時機：** stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。
- **替換時機：** 它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。

### Amazon ElastiCache

- **功用：** 提供managed Valkey/Redis OSS/Memcached記憶體data store。
- **底層機制：** Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。
- **關鍵設定：** engine、node/serverless、cluster mode、replicas/Multi-AZ、TTL、eviction、subnets/SG與encryption。
- **選擇時機：** session、hot reads、leaderboard、rate limiting與降低database load。
- **替換時機：** 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。

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

### Amazon EC2 Auto Scaling：逐項設定說明

#### `min/max/desired`

- **控制什麼：** `min/max/desired`設定Amazon EC2 Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `launch template`

- **控制什麼：** `launch template`是可版本化的啟動或工作規格，定義Amazon EC2 Auto Scaling建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `subnets`

- **控制什麼：** `subnets`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EC2 Auto Scaling的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `health check grace`

- **控制什麼：** `health check grace`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon EC2 Auto Scaling的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `instance warmup`

- **控制什麼：** `instance warmup`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon EC2 Auto Scaling的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `target tracking`

- **控制什麼：** `target tracking`指定Amazon EC2 Auto Scaling讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `mixed instances`

- **控制什麼：** `mixed instances`設定Amazon EC2 Auto Scaling的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `lifecycle hooks`

- **控制什麼：** `lifecycle hooks`把Amazon EC2 Auto Scaling與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### Amazon ElastiCache：逐項設定說明

#### `engine`

- **控制什麼：** `engine`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「session、hot reads、leaderboard、rate limiting與降低database load。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ElastiCache鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `node/serverless`

- **控制什麼：** `node/serverless`設定Amazon ElastiCache的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「session、hot reads、leaderboard、rate limiting與降低database load。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `cluster mode`

- **控制什麼：** `cluster mode`選擇資料/目錄service的availability、分片、節點休眠或managed integration模式。
- **何時需要：** 需要在成本與AZ/Region容錯、scale、Windows domain整合或閒置資源間做取捨時。
- **怎麼設定／驗證：** 明確選擇deployment/cluster/AD mode與AZs，設定failover/replica或auto-pause條件；以dependency failure與喚醒延遲測試。
- **常見錯法：** One Zone不適合不能接受AZ資料損失的state；auto-pause會增加首次連線延遲，目錄分享也仍需DNS/trust/network。

#### `replicas/Multi-AZ`

- **控制什麼：** `replicas/Multi-AZ`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Amazon ElastiCache前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

#### `TTL`

- **控制什麼：** `TTL`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「session、hot reads、leaderboard、rate limiting與降低database load。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon ElastiCache的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `eviction`

- **控制什麼：** `eviction`改變Amazon ElastiCache的performance/cost策略，例如並行度、I/O計價、query scheduling或memory回收。
- **何時需要：** 已有代表性load與瓶頸證據，能說明是latency、throughput、concurrency、I/O cost或memory pressure問題時。
- **怎麼設定／驗證：** 用benchmark比較候選mode，設定queue/class/eviction policy，觀察p95/p99、queue time、hit ratio及unit cost。
- **常見錯法：** 未先找瓶頸便切換模式可能只增加費用；問題也可能來自data model或workload isolation。

#### `subnets/SG`

- **控制什麼：** `subnets/SG`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「session、hot reads、leaderboard、rate limiting與降低database load。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ElastiCache的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `encryption`

- **控制什麼：** `encryption`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「session、hot reads、leaderboard、rate limiting與降低database load。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ElastiCache指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

## 讀到這裡，請用自己的話說一次

1. Application Load Balancer的責任：提供HTTP/HTTPS Layer 7 routing與web workload入口。
2. 底層機制：終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。
3. 第一個要看的設定：listeners/certificates、rules priority、target type、health path、stickiness、idle timeout與access logs。
4. 選擇邏輯：ALB跨至少兩AZ，ASG維持desired capacity，application health決定target是否接流量。
5. 不要混淆：Amazon EC2 Auto Scaling的責任是「依健康狀態與需求訊號維持、替換並調整EC2 fleet。」；它不會自動取代Application Load Balancer。
6. 替換訊號：極低延遲TCP/UDP、static IP或保留source IP需求用NLB。
7. 最常見錯法：只用EC2 status check而忽略應用deadlock，或把session放local disk阻止替換。
8. 可移植原則：make instances disposable and health application-aware。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Application Load Balancer | 提供HTTP/HTTPS Layer 7 routing與web workload入口。 | 終止HTTP/TLS，依host/path/header/method/query routing到target groups，支援WAF與OIDC。 | 網站、microservices、ECS dynamic ports、gRPC或需要content-based routing。 | 極低延遲TCP/UDP、static IP或保留source IP需求用NLB。 |
| Amazon EC2 Auto Scaling | 依健康狀態與需求訊號維持、替換並調整EC2 fleet。 | Launch template定義instance；Auto Scaling group跨subnets放置，policy改變desired capacity並執行health replacement。 | stateless EC2水平擴展、Multi-AZ replacement、Spot/On-Demand混合容量。 | 它不分配client traffic，通常搭配ELB；container service使用ECS/EKS service autoscaling。 |
| Amazon ElastiCache | 提供managed Valkey/Redis OSS/Memcached記憶體data store。 | Application顯式實作cache-aside/write-through；cluster以shards/replicas擴展並依TTL/eviction清理。 | session、hot reads、leaderboard、rate limiting與降低database load。 | 需要authoritative durability不能只放cache；DynamoDB專用API cache可用DAX。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Sticky sessions可暫時支援legacy session，但更好的長期方案是外部session store。 | 只有當題目條件明確改變時才可能合理。 | 只用EC2 status check而忽略應用deadlock，或把session放local disk阻止替換。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Sticky sessions可暫時支援legacy session，但更好的長期方案是外部session store。」之間做選擇。
- 認得常考設定：listeners/certificates、rules priority、target type、health path、stickiness、idle timeout與access logs。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：極低延遲TCP/UDP、static IP或保留source IP需求用NLB。
- 對應官方tasks：SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-3.4 Determine a strategy to improve reliability。

## 本章 10 題考題

### 練習題 1｜SAA｜ALB 與 ASG 的責任分工

一個 HTTP 應用需要依 host/path routing，部署在三個 AZ，instance 故障後要自動補回容量。哪個設計正確分配責任？

A. 只用 Route 53，讓 DNS 對每個 HTTP path 選 instance
B. ALB 依 listener rules 導向 healthy target groups；ASG 跨 AZ 維持與替換 EC2 capacity
C. 只用 ASG，因 ASG 能終止 TLS 並解析 URL path
D. 只用 ALB，因 ALB 會依 desired capacity 建立 EC2

**答案：B**

- **A：** 錯誤。Route 53 回答 DNS，不檢視每個 HTTP request 的 host/path，也不維護 EC2 fleet。
- **B：** 正確。ALB 是 L7 traffic plane，ASG 是 capacity controller，兩者以 target group/health integration 連接。
- **C：** 錯誤。ASG 不接受 client requests，也不提供 TLS listener 或 path routing。
- **D：** 錯誤。ALB 註冊並路由 targets，但不建立或替換 EC2 capacity。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Listeners for your Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-listeners.html)、[Health checks for instances in an Auto Scaling group - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-health-checks.html)

### 練習題 2｜SAA｜HTTPS listener 到 target 的資料路徑

Client 呼叫 https://api.example.com/orders。ALB 上有 ACM certificate、443 listener 與 host rule，target group 使用 port 8080。哪個流程描述正確？

A. Target group 先解析 public DNS，再要求 ASG 決定 URL rule
B. ACM certificate 必須安裝在每台 EC2，否則 ALB 無法終止 TLS
C. ALB listener 終止 TLS、依優先序規則選 target group，再連到 healthy target:8080；SG 必須允許這條路徑
D. Launch template 解析 Host header，並把 request 交給 ALB

**答案：C**

- **A：** 錯誤。Listener rules 在 ALB 評估，target group 不執行 DNS-based path routing。
- **B：** 錯誤。若 TLS 在 ALB 終止，certificate 綁在 listener；backend 是否再加密是另一個選擇。
- **C：** 正確。Listener、rule、target group 與 target port 形成 request path，network policy 仍須允許 ALB 到 target。
- **D：** 錯誤。Launch template 只定義 EC2 launches，不處理 production HTTP requests。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Listeners for your Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-listeners.html)、[Target groups for your Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html)

### 練習題 3｜SAA｜RequestCountPerTarget scaling

每台 web instance 經 load test 可在 p95 低於 200 ms 時處理約 500 requests/minute。Background jobs 讓 CPU 與 web demand 關聯很弱。應使用哪個 ASG scaling signal？

A. ALB RequestCountPerTarget target tracking，target 低於測得安全吞吐，並監控 latency/error
B. ALB 自建立以來累積的 RequestCount
C. Route 53 DNSQueries
D. ASG DesiredCapacity 本身

**答案：A**

- **A：** 正確。每 target request rate 直接近似 web demand/capacity，安全 target 可由 load test 推導。
- **B：** 錯誤。累積 counter 不會因增加 targets 回落，不能穩定追蹤 target。
- **C：** 錯誤。DNS queries 不等於經 ALB 的 request 數，且受 resolver caching 影響。
- **D：** 錯誤。DesiredCapacity 是 policy 輸出，不是 demand。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Target tracking scaling policies for Amazon EC2 Auto Scaling - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)、[CloudWatch metrics for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html)

### 練習題 4｜SAA｜Public ALB 與 private targets

Internet 使用者必須透過 HTTPS 存取服務，但 EC2 app instances 不得有 public IP 或接受 Internet 直接連線。哪個配置符合？

A. Internet-facing ALB 跨至少兩個 public subnets；targets 在 private subnets；app SG 只允許 ALB SG 到 app port
B. 每台 EC2 配 public IP，app port 對 0.0.0.0/0 開放，再把 ALB 放 private subnet
C. ALB 只放單一 subnet，因 DNS 會自動提供 Multi-AZ
D. Database SG 直接允許 ALB SG，讓 ALB 跳過 application authorization

**答案：A**

- **A：** 正確。Public entry 與 private targets 分離，SG reference 把 app exposure 限制為 ALB。
- **B：** 錯誤。這讓 app 可被繞過 ALB 直接攻擊，也無法建立正確 internet-facing ALB topology。
- **C：** 錯誤。ALB 高可用需要啟用多個 AZ/subnets，DNS 名稱不會補上不存在的 zonal nodes。
- **D：** 錯誤。ALB 應把 request 交給 app；直接暴露 DB 會破壞 tier boundary。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html#subnets-load-balancer)、[Security groups for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-update-security-groups.html)

### 練習題 5｜SAA｜Target deregistration 與 connection draining

Web app 最長 request 為 90 秒。Rolling deployment 時，舊 target 一收到 termination 就中斷 request。哪個改善最直接？

A. 把 health check interval 調成 90 秒，等同完成 draining
B. 啟用 stickiness，因 sticky cookie 保證 instance 不會被終止
C. 先 deregister target，將 deregistration delay 設為足以完成正常 request，並讓 lifecycle/deployment 等待 app graceful shutdown
D. 立即 terminate，再假設所有 client operation 都可安全重試

**答案：C**

- **A：** 錯誤。Health-check interval 是探測頻率，不會停止新流量並等待 existing connections。
- **B：** 錯誤。Stickiness 影響 routing affinity，不控制 ASG termination 或 in-flight completion。
- **C：** 正確。Deregistration 先停止配置新 request，delay 與 application shutdown 共同保護進行中的工作。
- **D：** 錯誤。非冪等 request 可能重複，而且立即終止直接違反 zero-drop 需求。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Edit target group attributes for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#deregistration-delay)、[Amazon EC2 Auto Scaling lifecycle hooks - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html)

### 練習題 6｜SAP｜ALB 502、503、504 與 fail-open 診斷

事故期間有四種現象：target group 沒有 registered targets；另一個 target group 的 registered targets 全部 unhealthy；一組 backend 超過 idle timeout 未回應；少數 targets reset connection 或送出 malformed headers。哪個描述最準確？

A. 三者都只會產生 429，應增加 API quota
B. 沒有 registered targets 可導致 503；全部 registered targets unhealthy 時 ALB 會 fail open 並仍嘗試路由；backend timeout 常見 504；reset 或 malformed response 常見 502
C. 504 必然是 Route 53 DNS failure，502 必然是 ACM 到期
D. 所有 5xx 都表示 ASG max size 太小

**答案：B**

- **A：** 錯誤。429 是 throttling 類語意，並非這些 ALB backend failure 的一般映射。
- **B：** 正確。ALB 的 target health 與 client HTTP status 不是一對一：沒有可用註冊 target 可回 503，但所有 targets 僅是 unhealthy 時會 fail open；timeout 與不合法 backend response 則分別常見 504、502。
- **C：** 錯誤。DNS/TLS 可失敗，但題目已提供更直接的 backend evidence，不能硬套單一根因。
- **D：** 錯誤。增加 capacity 可能處理 overload，卻不會修 malformed response 或錯誤 backend protocol。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Troubleshoot your Application Load Balancers - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html)、[Health checks for Application Load Balancer target groups - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)

### 練習題 7｜SAP｜ALB LCU 成本主導維度

ALB 費用本月倍增，但 target 數量幾乎不變。LCU usage 顯示 processed bytes 主導，access logs 顯示大量可快取 8 MiB 回應。哪個成本改善最合理？

A. 把 ALB 改成 single AZ
B. 關閉 health checks，因 probes 是所有 LCU 的主要來源
C. 購買 EC2 Savings Plans，讓 ALB LCU 同步折價
D. 先以 CloudFront/cache policy 降低回源 bytes，並檢查 payload/compression；持續以 LCU 各維度驗證

**答案：D**

- **A：** 錯誤。降低 AZ 數會傷害 availability，也不直接消除 processed bytes。
- **B：** 錯誤。Health probes 不等於題目觀察到的大型 response bytes，且關閉健康檢查會降低可靠性。
- **C：** 錯誤。Compute Savings Plans 不折抵 ALB LCU。
- **D：** 正確。應針對主導 billing dimension；edge caching、payload 與 compression 可直接降低 ALB processed bytes。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Elastic Load Balancing pricing](https://aws.amazon.com/elasticloadbalancing/pricing/)、[Manage how long content stays in the cache (expiration) - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html)

### 練習題 8｜SAA｜Session state externalization

ASG 替換 unhealthy instance 後，登入該 instance 的使用者全部被登出。團隊目前把 session 存在 local memory，並使用 ALB stickiness。最佳長期修正是什麼？

A. 把 session 放 instance store，並把 sticky cookie duration 設為一年
B. 禁止 ASG health replacement，避免 session host 被終止
C. 外部化 session 到共享 store，或使用可驗證 signed token；stickiness 只作短期相容而非 durability 保證
D. 只增加 ALB idle timeout

**答案：C**

- **A：** 錯誤。Instance store 仍隨 instance 遺失，長 stickiness 不能把流量送到已終止 host。
- **B：** 錯誤。保留 unhealthy instance 會把 session 問題轉成 availability 與安全風險。
- **C：** 正確。可替換 instance 不應擁有唯一 session state；共享/自包含 state 才能跨 replacement 存活。
- **D：** 錯誤。Idle timeout 控制 connection idle 時間，不保存 application session。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Edit target group attributes for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#sticky-sessions)、[Health checks for instances in an Auto Scaling group - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-health-checks.html)

### 練習題 9｜SAP｜ALB blue/green rollout

公司要把 production 從 blue ASG 漸進移到 green ASG；新版本錯誤率超過 1% 時必須自動回切，database change 已設計成 backward compatible。選擇兩項。

A. 建立獨立 versioned green ASG/target group，先完成 health 與 smoke tests，再用 weighted forwarding 或 deployment service 漸進切流
B. 在 blue instances 上原地覆寫 binary，且不保留前一 artifact
C. 以 error、latency 與 business success alarms 作 promotion gate，超標時把 traffic weight 回到 blue
D. 只看 CloudFormation CREATE_COMPLETE，立即刪除 blue
E. 先部署 incompatible destructive schema，再把 100% traffic 一次切到 green

**答案：A、C**

- **A：** 正確。獨立 target group 與漸進 traffic shift 限制 blast radius，versioned fleet 可快速識別與回復。
- **B：** 錯誤。In-place mutation 無法建立清楚的 blue/green 邊界或可靠 rollback。
- **C：** 正確。Runtime/business evidence 而非 control-plane success 才能判斷新版本是否可擴大。
- **D：** 錯誤。Stack 建立成功不證明應用正確；太早刪 blue 會失去快速 rollback。
- **E：** 錯誤。Incompatible schema 會使新舊版本不能共存，破壞漸進 rollout。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Action types for listener rules - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/rule-action-types.html#forward-actions)、[Use an instance refresh to update instances in an Auto Scaling group - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-instance-refresh.html)

### 練習題 10｜SAP｜跨 AZ 與 application-aware health

Web tier 必須在單一 AZ 失效時維持服務，也要能偵測『EC2 可 ping，但 application thread pool deadlock』。選擇兩項。

A. ALB 與 ASG 啟用至少兩個 AZ，並預留失去一個 AZ 後仍足夠的 healthy capacity
B. Health endpoint 永遠回 200，避免部署被中止
C. 只使用 EC2 system status check 判斷 application deadlock
D. 把所有 session 保存在單一 instance local disk
E. 建立會檢查關鍵 application path/readiness 的 health endpoint，讓 ALB 停止送流量並由 ASG 依 ELB health 替換

**答案：A、E**

- **A：** 正確。跨 AZ distribution 加上 N+1 capacity 才能在 zonal loss 後維持需求。
- **B：** 錯誤。永遠成功的 probe 無法偵測 deadlock，會持續把流量送到壞 target。
- **C：** 錯誤。System status 監測底層 infrastructure，不理解 application thread pool。
- **D：** 錯誤。Local-only session 讓 replacement/AZ failure 造成使用者 state 遺失。
- **E：** 正確。Application-aware health 將真實可服務性連到 traffic removal 與 capacity replacement。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Health checks for Application Load Balancer target groups - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)、[Health checks for instances in an Auto Scaling group - Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-health-checks.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「ALB跨至少兩AZ，ASG維持desired capacity，application health決定t…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Stateless web tier需要跨AZ分流、健康檢查、自動替換與安全deployment。」，所以「ALB跨至少兩AZ，ASG維持desired capacity，application health決定target是否接流量。」能直接滿足它；若constraint改成「Sticky sessions可暫時支援legacy session，但更好的長期方案是外部session store。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「ALB跨至少兩AZ，ASG維持desired capacity，application health決定target是否接流量。」。替代方案「Sticky sessions可暫時支援legacy session，但更好的長期方案是外部session store。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只用EC2 status check而忽略應用deadlock，或把session放local disk阻止替換。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Stateless web tier需要跨AZ分流、健康檢查、自動替換與安全deployment。」，排除會導致「只用EC2 status check而忽略應用deadlock，或把session放local disk阻止替換。」的選項，再選「ALB跨至少兩AZ，ASG維持desired capacity，application health決定target是否接流量。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAP-2.4 Design a strategy to meet reliability requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「ALB跨至少兩AZ，ASG維持desired capacity，application health決定target是否接流量。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「make instances disposable and health application-aware」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 36 章　Lambda Execution、Concurrency 與 Cold Start

事件驅動函式需要理解執行環境重用、並行上限、重試與下游保護。

## 跟著一份工作走：先從故事開始

如果今天由你值班，收到的需求可能是這樣：API流量突增一百倍，下游RDS最多接受兩百條connection。 值班時沒有時間翻產品型錄。最有用的第一步，是先畫出正常流程和故障流程，確認哪一站真的需要AWS幫忙，哪一站仍然是application或團隊自己的責任。

先別急著開console。請先回答：事件驅動函式需要理解執行環境重用、並行上限、重試與下游保護。 當這句話可以用白話說清楚，後面的route、policy、capacity與service choice才有依據。 接下來所有名詞都必須能回答這個問題，否則它就只是多餘的記憶負擔。

把抽象概念放回生活裡：把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。 這只是起點，因為類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。 我們會用真正的資料流與錯誤訊號，把這張粗略草圖補成可操作的架構。

於是我們得到一條可以繼續追查的路：由AWS Lambda承接主要責任，以Lambda concurrency檢查替代條件，並用「函式保持stateless/idempotent，以reserved concurrency隔離，必要時provisioned concurrency降低啟動延遲。」作為暫時結論。後面每個設定都必須能回頭解釋這個結論。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：API流量突增一百倍，下游RDS最多接受兩百條connection。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[AWS Lambda]
          │ 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · Lambda concurrency：控制Lambda同時執行的數量，連結輸入速率、下游容量、throttling與啟動延遲。
  · Amazon RDS Proxy：池化與重用database connections，保護RDS/Aurora免受短暫connection …

失敗時先找：無限制擴展把RDS connection打爆，或依賴global memory一定存在。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問AWS Lambda有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Lambda和Lambda concurrency並不是兩個任意的產品名稱。前者適合本章，是因為「函式保持stateless/idempotent，以reserved concurrency隔離，必要時provisioned concurrency降低啟動延遲。」直接回應了眼前的問題；後者描述的「Lambda適合短任務與變動流量；長時間穩定高利用率服務可能由containers/EC2更經濟。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：無限制擴展把RDS connection打爆，或依賴global memory一定存在。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「serverless removes server management, not capacity contracts」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |
| Lambda concurrency | 控制Lambda同時執行的數量，連結輸入速率、下游容量、throttling與啟動延遲。 | 每個並行request需要execution environment；reserved concurrency同時保留並限制函式額度，provisioned concurrency預先初始化環境。 |
| Amazon RDS Proxy | 池化與重用database connections，保護RDS/Aurora免受短暫connection storm。 | Proxy在client與DB間multiplex connections，使用Secrets Manager/IAM auth並感知failover。 |

## 把全圖套進一個具體案例

**場景：** API流量突增一百倍，下游RDS最多接受兩百條connection。

1. 故事的起點：API流量突增一百倍，下游RDS最多接受兩百條connection。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Lambda負責「按事件執行短生命函式，自動管理capacity與runtime基礎設施。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Lambda concurrency、Amazon RDS Proxy各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「無限制擴展把RDS connection打爆，或依賴global memory一定存在。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 跨來源稽核後補上的進階缺口

社群資料只用來發現漏項；下列技術行為以 AWS 官方文件校正。

### SnapStart 與 Response Streaming：一個縮短開始前等待，一個讓結果不必全部算完才送

Cold start 包含 runtime、依賴與初始化。SnapStart 在發佈版本時先初始化並保存 execution environment snapshot，之後從 snapshot 恢復；response streaming 則讓 function 邊產生資料邊回給 client。兩者優化不同時間：time-to-first-instruction 與 time-to-first-byte。

```text
publish version ─ initialize ─ snapshot
invoke ─ restore snapshot ─ handler ─ write chunk 1 ─ chunk 2 ─ end
          ▲ startup latency             ▲ first-byte latency
```

#### SnapStart 最容易被忽略的 correctness 問題

```Pseudo configuration
function_version:
  snap_start: PublishedVersions
handler_rules:
  - generate unique IDs after restore
  - refresh temporary credentials and timestamps
  - validate/reconnect network connections
response_stream:
  - apply backpressure
  - always end the stream
```

1. Snapshot 會被多個 environments 重用；初始化時產生的 UUID、entropy 或 temporary state 不能假設仍唯一／新鮮。
2. Provisioned Concurrency 維持預先初始化容量，適合更嚴格且可預測的 latency；不是 SnapStart 的同義詞。
3. Streaming 降低 first-byte latency，卻沒有降低全部工作量；client disconnect、backpressure 與 partial response 都要處理。

**選擇邊界：** 初始化很重、可發佈 version 且 runtime/feature 相容時評估 SnapStart；嚴格穩定低延遲評估 Provisioned Concurrency；大型或逐步生成回應才需要 streaming。

**考試範圍：** 這些是 Lambda performance 深化。考題若只說『cold start』，先辨識是初始化、容量未預熱，還是 application 下游慢，不要看到新功能就直接選。

- [AWS：Lambda SnapStart](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html)
- [AWS：Lambda response streaming](https://docs.aws.amazon.com/lambda/latest/dg/config-rs-write-functions.html)

## 需要時再查：四個閱讀支點

### AWS Lambda

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：事件驅動函式需要理解執行環境重用、並行上限、重試與下游保護。
- **具體例子／邊界：** 在「API流量突增一百倍，下游RDS最多接受兩百條connection。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Lambda concurrency

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Lambda適合短任務與變動流量；長時間穩定高利用率服務可能由containers/EC2更經濟。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：無限制擴展把RDS connection打爆，或依賴global memory一定存在。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：serverless removes server management, not capacity contracts。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### idle timeout

Connection沒有資料傳輸多久後被關閉；必須與client、proxy與application timeout形成合理層次。

### target group

一組接收load balancer流量的instances、IPs或Lambda，以及共同health check與routing attributes。

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### cold start

Serverless/container在沒有可重用execution environment時建立runtime的額外延遲。

### throttling

服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### cache

可丟棄、可能過期的資料副本，用較少後端工作換取低延遲；不能當唯一正確性來源。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### AWS Lambda

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

### Lambda concurrency

- **功用：** 控制Lambda同時執行的數量，連結輸入速率、下游容量、throttling與啟動延遲。
- **底層機制：** 每個並行request需要execution environment；reserved concurrency同時保留並限制函式額度，provisioned concurrency預先初始化環境。
- **關鍵設定：** account quota、reserved concurrency、provisioned concurrency、event-source maximum concurrency、batch size與throttles。
- **選擇時機：** 保護database連線、隔離關鍵函式容量、降低可預測流量的cold-start latency。
- **替換時機：** 持續高利用率或超長工作改用container/EC2；提高concurrency不能修復下游容量不足。

### Amazon RDS Proxy

- **功用：** 池化與重用database connections，保護RDS/Aurora免受短暫connection storm。
- **底層機制：** Proxy在client與DB間multiplex connections，使用Secrets Manager/IAM auth並感知failover。
- **關鍵設定：** target group、Secrets Manager auth、IAM auth、max connections、idle timeout、subnets與SG。
- **選擇時機：** Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。
- **替換時機：** 它不cache query也不增加DB compute；讀壓力需replica/cache或schema/index改善。

## 考前與實作時再查：設定操作手冊

### AWS Lambda：逐項設定說明

#### `memory/CPU`

- **控制什麼：** `memory/CPU`設定AWS Lambda的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `timeout`

- **控制什麼：** `timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Lambda的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `reserved/provisioned concurrency`

- **控制什麼：** `reserved/provisioned concurrency`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `event source mapping`

- **控制什麼：** `event source mapping`指定AWS Lambda讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `DLQ/destination`

- **控制什麼：** `DLQ/destination`指定AWS Lambda讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `VPC`

- **控制什麼：** `VPC`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lambda的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `ephemeral storage`

- **控制什麼：** `ephemeral storage`選擇AWS Lambda的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

### Lambda concurrency：逐項設定說明

#### `account quota`

- **控制什麼：** `account quota`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「保護database連線、隔離關鍵函式容量、降低可預測流量的cold-start latency。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Lambda concurrency建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `reserved concurrency`

- **控制什麼：** `reserved concurrency`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `provisioned concurrency`

- **控制什麼：** `provisioned concurrency`設定Lambda concurrency的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「保護database連線、隔離關鍵函式容量、降低可預測流量的cold-start latency。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `event-source maximum concurrency`

- **控制什麼：** `event-source maximum concurrency`指定Lambda concurrency讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `batch size`

- **控制什麼：** `batch size`設定Lambda concurrency的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「保護database連線、隔離關鍵函式容量、降低可預測流量的cold-start latency。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `throttles`

- **控制什麼：** `throttles`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「保護database連線、隔離關鍵函式容量、降低可預測流量的cold-start latency。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Lambda concurrency的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

### Amazon RDS Proxy：逐項設定說明

#### `target group`

- **控制什麼：** `target group`指定Amazon RDS Proxy讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `Secrets Manager auth`

- **控制什麼：** `Secrets Manager auth`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon RDS Proxy指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `IAM auth`

- **控制什麼：** `IAM auth`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon RDS Proxy明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `max connections`

- **控制什麼：** `max connections`指定Amazon RDS Proxy讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `idle timeout`

- **控制什麼：** `idle timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon RDS Proxy的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `subnets`

- **控制什麼：** `subnets`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon RDS Proxy的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `SG`

- **控制什麼：** `SG`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon RDS Proxy中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

## 讀到這裡，請用自己的話說一次

1. AWS Lambda的責任：按事件執行短生命函式，自動管理capacity與runtime基礎設施。
2. 底層機制：事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
3. 第一個要看的設定：memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
4. 選擇邏輯：函式保持stateless/idempotent，以reserved concurrency隔離，必要時provisioned concurrency降低啟動延遲。
5. 不要混淆：Lambda concurrency的責任是「控制Lambda同時執行的數量，連結輸入速率、下游容量、throttling與啟動延遲。」；它不會自動取代AWS Lambda。
6. 替換訊號：長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。
7. 最常見錯法：無限制擴展把RDS connection打爆，或依賴global memory一定存在。
8. 可移植原則：serverless removes server management, not capacity contracts。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| Lambda concurrency | 控制Lambda同時執行的數量，連結輸入速率、下游容量、throttling與啟動延遲。 | 每個並行request需要execution environment；reserved concurrency同時保留並限制函式額度，provisioned concurrency預先初始化環境。 | 保護database連線、隔離關鍵函式容量、降低可預測流量的cold-start latency。 | 持續高利用率或超長工作改用container/EC2；提高concurrency不能修復下游容量不足。 |
| Amazon RDS Proxy | 池化與重用database connections，保護RDS/Aurora免受短暫connection storm。 | Proxy在client與DB間multiplex connections，使用Secrets Manager/IAM auth並感知failover。 | Lambda/serverless高concurrency、頻繁開關connection與需要更快failover reconnect。 | 它不cache query也不增加DB compute；讀壓力需replica/cache或schema/index改善。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Lambda適合短任務與變動流量；長時間穩定高利用率服務可能由containers/EC2更經濟。 | 只有當題目條件明確改變時才可能合理。 | 無限制擴展把RDS connection打爆，或依賴global memory一定存在。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Lambda適合短任務與變動流量；長時間穩定高利用率服務可能由containers/EC2更經濟。」之間做選擇。
- 認得常考設定：memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Lambda 與 container execution model

團隊有兩個新 workload：A 每次由 S3 event 觸發，通常 4 秒完成且流量極不規則；B 是需要 sidecar、持久 WebSocket 與數小時執行的 service。哪個選擇最合理？

A. A 與 B 都用 Lambda，provisioned concurrency 可移除所有 duration/runtime 限制
B. A 用 Lambda；B 用 ECS/Fargate 或 EC2-backed container，依 host 控制與利用率選擇
C. A 用 EKS，因低流量一定需要 Kubernetes；B 用 Lambda
D. 只要程式是 Python，兩者都應使用 Lambda

**答案：B**

- **A：** 錯誤。Provisioned concurrency 降低 cold start，不改變 Lambda 的執行時間與 host/sidecar 契約。
- **B：** 正確。短、事件驅動、bursty 工作符合 Lambda；長連線與 sidecar 更符合持續 container runtime。
- **C：** 錯誤。EKS 不是低流量的必要條件，Lambda 也不適合題述的長時間 persistent service。
- **D：** 錯誤。語言不是主要決策；execution duration、state、network connection 與控制需求才是限制。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Understanding the Lambda execution environment lifecycle - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)、[Choosing an AWS compute service - AWS Decision Guides](https://docs.aws.amazon.com/decision-guides/latest/compute-on-aws-how-to-choose/compute-on-aws-how-to-choose.html)

### 練習題 2｜SAA｜Lambda execution environment reuse

開發者把 SDK client 與模型載入放在 handler 外，並把最近結果 cache 在 /tmp。哪個假設是安全的？

A. 同一 function 永遠只有一個 execution environment，因此 global variable 可作全域 counter
B. 每次 invocation 必定使用全新 environment，所以初始化移出 handler 沒有效果
C. Warm environment 可能重用 global resources 與 /tmp 以改善效能，但 environment 可隨時被替換，durable state 必須外部化
D. 設定 provisioned concurrency 後，/tmp 會成為跨 Region durable database

**答案：C**

- **A：** 錯誤。Lambda 可同時建立多個 environments，也不保證特定 environment 永久存在。
- **B：** 錯誤。Environment reuse 是常見最佳化機會，但不能當 correctness 保證。
- **C：** 正確。重用適合 cache/client initialization；真正 state 必須存到持久服務並處理 cache miss。
- **D：** 錯誤。Provisioned concurrency 只預先初始化 environments，不提供 durable/shared storage。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Understanding the Lambda execution environment lifecycle - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)

### 練習題 3｜SAP｜Concurrency、throttle 與 event lag

SQS-triggered Lambda 的 ApproximateAgeOfOldestMessage 快速升高，ConcurrentExecutions 到達 200，Throttles 同時出現；RDS connections 也逼近上限。下一步應如何判斷？

A. 只看 invocation 總數，因它能指出所有容量限制
B. 延長 function timeout，讓更多 invocations 同時占用 connections
C. 把 DLQ message count 當成可用 concurrency
D. 用 message age 判斷落後、用 concurrency/throttles 找 function/account cap，並把 RDS session budget 納入 maximum concurrency

**答案：D**

- **A：** 錯誤。Invocation count 不顯示 lag、並行上限或 downstream saturation。
- **B：** 錯誤。更長 timeout 可能讓受阻 connections 保留更久，惡化 RDS exhaustion。
- **C：** 錯誤。DLQ 保存超過重試條件的失敗訊息，反映的是失敗隔離與 redrive 結果；它既不是 Lambda 可用 concurrency，也不能解釋目前 queue lag。
- **D：** 正確。三組 evidence 分別描述 backlog、Lambda capacity 與 downstream budget，必須一起設計。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Configuring reserved concurrency for a function - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)、[Configuring scaling behavior for SQS event source mappings - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-scaling.html)

### 練習題 4｜SAA｜Reserved 與 provisioned concurrency

Checkout API 需要穩定低 cold-start latency；同帳號的 image batch function 不得搶光 concurrency。哪個配置正確？

A. 對 checkout published version/alias 配 provisioned concurrency；對 batch 設 reserved concurrency 以保留並限制其最大並行
B. 只對 checkout 設 reserved concurrency，即保證永遠無 cold start
C. 只對 batch 設 provisioned concurrency，因它是 account-wide throttle
D. 把 Lambda memory 設為 200，代表最多 200 concurrent executions

**答案：A**

- **A：** 正確。Provisioned concurrency 準備 warm environments；reserved concurrency 同時保留配額並形成 function-level cap。
- **B：** 錯誤。Reserved concurrency 管理 capacity allocation/cap，不保證 environments 已初始化。
- **C：** 錯誤。Provisioned concurrency 是預初始化容量，不是 account-wide 上限。
- **D：** 錯誤。Memory 是每 invocation 的資源配置，與並行數不是同一欄位。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Configuring reserved concurrency for a function - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)

### 練習題 5｜SAA｜SQS partial batch response

Lambda 一次收到 10 個 SQS messages，其中第 7 筆因資料格式錯誤失敗，其他 9 筆已成功寫入。如何避免 9 筆反覆重做，同時保留失敗項重試？

A. 捕捉所有 exceptions 並永遠回成功
B. 讓 handler idempotent，啟用 partial batch response 回報失敗 item，並設定合適 visibility timeout、retry 與 DLQ
C. 每次失敗就 purge 整個 queue
D. 把 batch size 調到最大，因大 batch 不會重複

**答案：B**

- **A：** 錯誤。若 handler 吞掉例外並回報整批成功，Lambda 會把失敗 message 視為已處理；第 7 筆不再重現，形成無法由 DLQ 挽回的資料遺失。
- **B：** 正確。Partial response 讓成功項完成、失敗項重現；idempotency 仍保護至少一次投遞。
- **C：** 錯誤。PurgeQueue 會移除 queue 中其他仍有效、尚未處理的 messages；它不是隔離單一 poison message 的機制，也破壞至少一次處理流程。
- **D：** 錯誤。Batch size 不改變 failure semantics，反而可能擴大整批重試成本。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Handling errors for an SQS event source in Lambda - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)

### 練習題 6｜SAP｜Lambda throttle 與 RDS connection exhaustion

API 突增時 Lambda 同時報 TooManyRequests，RDS 報 too many connections。Function 沒有 reserved concurrency，每個 invocation 都新建兩條連線。哪個修正最完整？

A. 增加 provisioned concurrency 且不設定任何 cap
B. 延長 timeout，使每條連線存在更久
C. 把 function 移出 VPC，RDS connection limit 就會上升
D. 檢查 account/function limits，設定符合 DB budget 的 reserved concurrency，使用安全 connection reuse/RDS Proxy 並對入口 backpressure

**答案：D**

- **A：** 錯誤。更多 warm capacity 可讓 invocations 更快壓垮 RDS，沒有保護 downstream。
- **B：** 錯誤。延長 timeout 增加 concurrent connection 占用時間。
- **C：** 錯誤。移出 VPC 可能讓 private RDS 不可達，也不改變 database session 上限。
- **D：** 正確。先建立最大並行 budget，再減少 connection churn 並讓 upstream 在超載時退避。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Configuring reserved concurrency for a function - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)、[Using AWS Lambda with Amazon RDS - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-rds.html)

### 練習題 7｜SAP｜Lambda memory、duration 與 provisioned capacity 成本

CPU-bound Lambda 從 512 MB 提高到 1,536 MB 後，平均 duration 由 9 秒降到 2 秒；另有全天 100 units provisioned concurrency 但夜間利用率為 2%。最佳成本行動是什麼？

A. 永遠選最低 memory，因 GB-second 不受 duration 影響
B. 以 cost-per-success benchmark 各 memory size；只在有 latency SLO 的 alias/時段保留必要 provisioned concurrency
C. Provisioned concurrency 只在收到 request 時收費，因此不需調整
D. 把 timeout 加倍，billed duration 會自動減半

**答案：B**

- **A：** 錯誤。較高 memory 同時增加 CPU，可能因 duration 大幅縮短而降低單次總成本。
- **B：** 正確。用完整 price-duration 結果選 memory，並依實際 latency window rightsizing 預備容量。
- **C：** 錯誤。Provisioned concurrency 包含配置期間的容量費，低利用率時需評估時段化。
- **D：** 錯誤。Timeout 是上限，不會降低實際 billed duration。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Configure Lambda function memory - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html)、[AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)

### 練習題 8｜SAA｜同步、非同步與 poll-based invocation

架構師比較三條路徑：API Gateway 直接呼叫 Lambda、EventBridge 送 event、SQS event source mapping。哪個 retry 責任描述正確？

A. 同步 API 的 caller 取得回應並決定重試；非同步由 Lambda event queue/retry；SQS 由 visibility timeout、redrive 與 poller 控制訊息生命週期
B. 三種模式都固定只重試一次，無法設定 DLQ
C. API Gateway 回 202 就證明所有 background work 已完成
D. Lambda DLQ 會攔截所有同步 4xx response

**答案：A**

- **A：** 正確。三種 invocation model 的 ownership 不同，必須分別設計 idempotency、retry 與 failure destination。
- **B：** 錯誤。各 event source 有不同 retry 與 redrive contract。
- **C：** 錯誤。接受 request 只代表入口成功，不代表非同步工作完成。
- **D：** 錯誤。同步 errors 直接回 caller，非同步 DLQ/destination 不會接管所有同步 4xx。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/invocation-models.html)、[Configuring scaling behavior for SQS event source mappings - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-scaling.html)

### 練習題 9｜SAP｜Lambda version、alias canary 與 rollback

多帳號 checkout Lambda 要以 10% canary 發布；若 payment success rate 或 p99 latency 退化，要自動回到舊版。選擇兩項。

A. 發布 immutable function version，以 alias 作 stable endpoint，透過 CodeDeploy/weighted alias 漸進切流
B. 讓 clients 直接呼叫 $LATEST，部署時覆寫同一 package
C. 只看 CloudFormation UPDATE_COMPLETE 後立刻切 100%
D. 把 alarms 綁定 errors、latency 與 payment success，失敗時將 alias rollback 到前一 version
E. 刪除舊 function version 後才開始 canary

**答案：A、D**

- **A：** 正確。Version 提供不可變 artifact，alias 提供可移動入口與細粒度 traffic shift。
- **B：** 錯誤。$LATEST 是 mutable，無法建立清楚 canary population 或可靠 rollback。
- **C：** 錯誤。Control-plane success 不證明 runtime/business behavior 正確。
- **D：** 正確。技術與業務 alarms 是 promotion evidence，alias 能快速回到已知版本。
- **E：** 錯誤。Weighted alias 必須同時指向可用的新舊 published versions；先刪舊版會移除已知良好 rollback target，使 alarm 觸發後無法立即回切。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Create an alias for a Lambda function - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-aliases.html)、[Create an alias for a Lambda function - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/lambda-traffic-shifting-using-aliases.html)

### 練習題 10｜SAP｜保護 RDS-backed Lambda API

Lambda API 流量可瞬間增加 100 倍，但 Aurora 只容許 300 application sessions，且 p95 cold start 有明確 SLO。選擇兩項。

A. 取消所有 concurrency limits，讓 Lambda 先吸收流量
B. 以 reserved concurrency 將最大並行限制在 DB budget，入口在超載時 throttling/queueing/backoff
C. 每個 invocation 建立多條新 DB connections 且不回收
D. 只增加 function timeout
E. 使用 RDS Proxy 或安全 connection reuse 減少 churn；若 SLO 仍需要，對 published alias 配適量 provisioned concurrency

**答案：B、E**

- **A：** 錯誤。取消 concurrency boundary 會讓瞬間 fan-out 超過 Aurora 的 300-session budget；Lambda 自身仍可擴張，但 downstream 會先出現連線拒絕、timeout 與重試風暴。
- **B：** 正確。Concurrency cap 把 Lambda elasticity 約束在 downstream 可承受的 session budget。
- **C：** 錯誤。這會讓每個 concurrent invocation 消耗更多有限 sessions。
- **D：** 錯誤。Timeout 不減少 connection churn，也不降低並行壓力。
- **E：** 正確。Proxy/reuse 保護 connection plane；provisioned concurrency 則獨立處理初始化 latency。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Configuring reserved concurrency for a function - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)、[Using AWS Lambda with Amazon RDS - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-rds.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「函式保持stateless/idempotent，以reserved concurrency隔離，必要時p…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「事件驅動函式需要理解執行環境重用、並行上限、重試與下游保護。」，所以「函式保持stateless/idempotent，以reserved concurrency隔離，必要時provisioned concurrency降低啟動延遲。」能直接滿足它；若constraint改成「Lambda適合短任務與變動流量；長時間穩定高利用率服務可能由containers/EC2更經濟。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「函式保持stateless/idempotent，以reserved concurrency隔離，必要時provisioned concurrency降低啟動延遲。」。替代方案「Lambda適合短任務與變動流量；長時間穩定高利用率服務可能由containers/EC2更經濟。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「無限制擴展把RDS connection打爆，或依賴global memory一定存在。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「事件驅動函式需要理解執行環境重用、並行上限、重試與下游保護。」，排除會導致「無限制擴展把RDS connection打爆，或依賴global memory一定存在。」的選項，再選「函式保持stateless/idempotent，以reserved concurrency隔離，必要時provisioned concurrency降低啟動延遲。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「函式保持stateless/idempotent，以reserved concurrency隔離，必要時provisioned concurrency降低啟動延遲。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「serverless removes server management, not capacity contracts」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 37 章　API Gateway 與 Serverless API

Public API需要authentication、throttling、routing、transformation與版本管理。

## 跟著一份工作走：先從故事開始

故事從一個看似簡單的需求開始：行動app API需JWT、每客戶quota、request validation與canary stage。 這句話裡已經藏著使用者、資料、故障與成本，只是它們還沒有被翻成架構圖。我們先不急著替它貼產品標籤，而是看看事情實際會怎麼發生。

這時最容易做的事，是立刻在服務清單裡找熟悉的名字；但真正要先回答的是：Public API需要authentication、throttling、routing、transformation與版本管理。 我們不是在選功能最多的產品，而是在找能把這個問題切乾淨的做法。 它也會成為後面判斷設定是否正確的驗收標準。

把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。 接下來每個技術名詞都會放回這個畫面裡，讓你知道它出現在流程的哪一站，而不是孤零零地背一個定義。

帶著這張圖再看AWS，Amazon API Gateway會是本章的主要角色，Amazon Cognito則幫我們看清邊界。方向是「API Gateway作managed入口，整合Lambda或HTTP backend，使用authorizer/Cognito與usage controls。」；接下來先沿著一次真實流程看它為什麼成立，再談設定、例外與考題。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：行動app API需JWT、每客戶quota、request validation與canary stage。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[Amazon API Gateway]
          │ 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · Amazon Cognito：為consumer/mobile/web applications提供user sign-up/sign-…
  · AWS Lambda：按事件執行短生命函式，自動管理capacity與runtime基礎設施。

失敗時先找：只依API key做身份驗證，或timeout/retry設定使client與Lambda重複寫入。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問Amazon API Gateway有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon API Gateway和Amazon Cognito並不是兩個任意的產品名稱。前者適合本章，是因為「API Gateway作managed入口，整合Lambda或HTTP backend，使用authorizer/Cognito與usage controls。」直接回應了眼前的問題；後者描述的「ALB也能直接整合Lambda或containers，適合較簡單、已有VPC routing的HTTP服務。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：只依API key做身份驗證，或timeout/retry設定使client與Lambda重複寫入。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「put protocol policy at a managed edge」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon API Gateway | 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。 | Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 |
| Amazon Cognito | 為consumer/mobile/web applications提供user sign-up/sign-in與AWS credential federation。 | User Pool發OIDC tokens；Identity Pool把已驗證身份交換成temporary IAM credentials。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 |

## 把全圖套進一個具體案例

**場景：** 行動app API需JWT、每客戶quota、request validation與canary stage。

1. 故事的起點：行動app API需JWT、每客戶quota、request validation與canary stage。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon API Gateway負責「提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon Cognito、AWS Lambda各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「只依API key做身份驗證，或timeout/retry設定使client與Lambda重複寫入。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon API Gateway

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Public API需要authentication、throttling、routing、transformation與版本管理。
- **具體例子／邊界：** 在「行動app API需JWT、每客戶quota、request validation與canary stage。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon Cognito

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：ALB也能直接整合Lambda或containers，適合較簡單、已有VPC routing的HTTP服務。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：只依API key做身份驗證，或timeout/retry設定使client與Lambda重複寫入。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：put protocol policy at a managed edge。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### concurrency

同一時間正在執行的工作數；提高它會增加throughput，也可能耗盡database connections等下游資源。

### federation

讓外部IdP驗證使用者或workload，再交換AWS temporary role session，而不為每人建立獨立長期AWS密碼。

### throttling

服務因速率或容量限制拒絕／延後request；client應使用bounded retry、backoff、jitter與admission control。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### canary

先把小比例流量或少數targets導向新版本，觀察technical與business指標後再擴大，以限制錯誤版本的blast radius。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### quota

AWS對account/Region/resource的服務上限；架構即使正確，撞到quota仍會被throttle或無法建立資源。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### route

描述「去某個destination應交給哪個next hop」；封包通常需要去程與回程都存在。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### DLQ

Dead-letter queue，保存多次處理失敗的messages，讓主queue繼續前進並支援調查與redrive。

### NAT

Network Address Translation，改寫封包地址；NAT Gateway常讓private IPv4 workload主動出Internet。

### TCP

需要建立connection、可靠且有順序的傳輸協定；HTTP/TLS通常建立在TCP上。

### TTL

Time to live，資料或cache answer在重新驗證、過期或清理前可使用多久。

## 回到 AWS：Components、功用與責任邊界

### Amazon API Gateway

- **功用：** 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。
- **底層機制：** Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。
- **關鍵設定：** REST/HTTP/WebSocket API、routes/resources、stages、authorizers、usage plans、throttling、CORS與integration timeout。
- **選擇時機：** serverless API、公開/私有API、consumer治理與request transformation。
- **替換時機：** 一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。

### Amazon Cognito

- **功用：** 為consumer/mobile/web applications提供user sign-up/sign-in與AWS credential federation。
- **底層機制：** User Pool發OIDC tokens；Identity Pool把已驗證身份交換成temporary IAM credentials。
- **關鍵設定：** user pool、app client、hosted UI、MFA、federation、groups、identity pool roles與token lifetime。
- **選擇時機：** 數十萬外部customers的authentication與social/enterprise federation。
- **替換時機：** 員工多帳號AWS console access用IAM Identity Center；service workload用IAM role。

### AWS Lambda

- **功用：** 按事件執行短生命函式，自動管理capacity與runtime基礎設施。
- **底層機制：** 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。
- **關鍵設定：** memory/CPU、timeout、reserved/provisioned concurrency、event source mapping、DLQ/destination、VPC與ephemeral storage。
- **選擇時機：** 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。
- **替換時機：** 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。

## 考前與實作時再查：設定操作手冊

### Amazon API Gateway：逐項設定說明

#### `REST/HTTP/WebSocket API`

- **控制什麼：** `REST/HTTP/WebSocket API`選擇Amazon API Gateway的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

#### `routes/resources`

- **控制什麼：** `routes/resources`指定Amazon API Gateway讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `stages`

- **控制什麼：** `stages`定義治理scope、ownership、分類或跨帳號分享，影響policy套用、成本歸屬與blast radius。
- **何時需要：** 當需求符合「serverless API、公開/私有API、consumer治理與request transformation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon API Gateway建立穩定taxonomy與owner，將policy附到明確account/OU/resource scope；以automation檢查missing/invalid values。
- **常見錯法：** Tag本身不是不可繞過安全邊界；名稱與owner不穩定會讓ABAC、backup、cost allocation與automation同時失效。

#### `authorizers`

- **控制什麼：** `authorizers`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「serverless API、公開/私有API、consumer治理與request transformation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon API Gateway明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `usage plans`

- **控制什麼：** `usage plans`控制model選擇/grounding、knowledge-base同步、event payload轉換或API consumer的quota/rate plan。
- **何時需要：** AI、event-driven或public API需要可版本化quality、資料新鮮度、payload contract或tenant限額時。
- **怎麼設定／驗證：** 鎖定model/version與eval，設定grounding threshold或sync schedule；event/API則定義transform schema、API key plan、quota與throttle。
- **常見錯法：** Model或sync成功不代表回答正確；input transform漏欄位會破壞consumer，usage plan也不能取代authentication/authorization。

#### `throttling`

- **控制什麼：** `throttling`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「serverless API、公開/私有API、consumer治理與request transformation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定Amazon API Gateway的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `CORS`

- **控制什麼：** CORS決定browser中的某個origin能否以指定methods/headers呼叫另一個origin；它是browser enforcement，不是API authentication。
- **何時需要：** Web frontend與Amazon API Gateway API使用不同scheme、host或port，而且browser需要送出credential或non-simple request時。
- **怎麼設定／驗證：** 設定AllowOrigins、AllowMethods、AllowHeaders、ExposeHeaders與MaxAge；使用credentials時不可用*允許所有origins，並測試preflight OPTIONS。
- **常見錯法：** curl成功不代表browser會放行；CORS header也不能阻止非browser client，真正授權仍需JWT、IAM或OAuth authorizer。

#### `integration timeout`

- **控制什麼：** `integration timeout`把Amazon API Gateway與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### Amazon Cognito：逐項設定說明

#### `user pool`

- **控制什麼：** `user pool`定義application users、OAuth client、登入UI或外部IdP federation，以及token如何交給app/AWS credentials。
- **何時需要：** Consumer/web/mobile application使用Amazon Cognito做註冊登入、social/enterprise federation或API token時。
- **怎麼設定／驗證：** 設定callback/logout URLs、OAuth flows/scopes、client secret策略、token lifetime與MFA；驗證issuer、audience、expiry及group claims。
- **常見錯法：** User pool authentication與identity-pool AWS authorization不是同一件事；把client secret放browser或未驗audience會形成漏洞。

#### `app client`

- **控制什麼：** `app client`定義application users、OAuth client、登入UI或外部IdP federation，以及token如何交給app/AWS credentials。
- **何時需要：** Consumer/web/mobile application使用Amazon Cognito做註冊登入、social/enterprise federation或API token時。
- **怎麼設定／驗證：** 設定callback/logout URLs、OAuth flows/scopes、client secret策略、token lifetime與MFA；驗證issuer、audience、expiry及group claims。
- **常見錯法：** User pool authentication與identity-pool AWS authorization不是同一件事；把client secret放browser或未驗audience會形成漏洞。

#### `hosted UI`

- **控制什麼：** `hosted UI`定義application users、OAuth client、登入UI或外部IdP federation，以及token如何交給app/AWS credentials。
- **何時需要：** Consumer/web/mobile application使用Amazon Cognito做註冊登入、social/enterprise federation或API token時。
- **怎麼設定／驗證：** 設定callback/logout URLs、OAuth flows/scopes、client secret策略、token lifetime與MFA；驗證issuer、audience、expiry及group claims。
- **常見錯法：** User pool authentication與identity-pool AWS authorization不是同一件事；把client secret放browser或未驗audience會形成漏洞。

#### `MFA`

- **控制什麼：** `MFA`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「數十萬外部customers的authentication與social/enterprise federation。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Cognito明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `federation`

- **控制什麼：** `federation`定義application users、OAuth client、登入UI或外部IdP federation，以及token如何交給app/AWS credentials。
- **何時需要：** Consumer/web/mobile application使用Amazon Cognito做註冊登入、social/enterprise federation或API token時。
- **怎麼設定／驗證：** 設定callback/logout URLs、OAuth flows/scopes、client secret策略、token lifetime與MFA；驗證issuer、audience、expiry及group claims。
- **常見錯法：** User pool authentication與identity-pool AWS authorization不是同一件事；把client secret放browser或未驗audience會形成漏洞。

#### `groups`

- **控制什麼：** Cognito groups把user pools中的users分類，group可進token claims並設定role precedence，方便application做粗粒度authorization。
- **何時需要：** 多種使用者角色需要不同UI/API權限，但不想為每位user單獨管理相同claims時。
- **怎麼設定／驗證：** 建立group、加入users並檢查ID/access token中的cognito:groups；API仍需驗證token與將group映射到具體permissions。
- **常見錯法：** Group claim不是萬用admin開關，也不適合取代細粒度resource authorization；user加入多groups時要處理precedence。

#### `identity pool roles`

- **控制什麼：** `identity pool roles`定義application users、OAuth client、登入UI或外部IdP federation，以及token如何交給app/AWS credentials。
- **何時需要：** Consumer/web/mobile application使用Amazon Cognito做註冊登入、social/enterprise federation或API token時。
- **怎麼設定／驗證：** 設定callback/logout URLs、OAuth flows/scopes、client secret策略、token lifetime與MFA；驗證issuer、audience、expiry及group claims。
- **常見錯法：** User pool authentication與identity-pool AWS authorization不是同一件事；把client secret放browser或未驗audience會形成漏洞。

#### `token lifetime`

- **控制什麼：** `token lifetime`附加到temporary identity/session，協助限制delegation、保留caller context或決定credential有效時間。
- **何時需要：** Cross-account、第三方SaaS、federation或agent代表使用者呼叫tool時。
- **怎麼設定／驗證：** 在AssumeRole/OAuth request與trust conditions中設定，讓audit保留source/session context；duration只給完成任務所需時間。
- **常見錯法：** ExternalId不是密碼；session name也不是authentication。Session過長會擴大credential洩漏窗口。

### AWS Lambda：逐項設定說明

#### `memory/CPU`

- **控制什麼：** `memory/CPU`設定AWS Lambda的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `timeout`

- **控制什麼：** `timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Lambda的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `reserved/provisioned concurrency`

- **控制什麼：** `reserved/provisioned concurrency`選擇compute隔離與計價方式，改變承諾、capacity/interruption風險與成本。
- **何時需要：** 已有使用量基線、interruptibility與compliance需求，可分辨baseline與burst capacity時。
- **怎麼設定／驗證：** 穩定部分評估commitment，fault-tolerant部分用Spot diversification；持續看coverage、utilization與interruption。
- **常見錯法：** 先買折扣再rightsizing會鎖定浪費；Dedicated tenancy也不是所有合規要求的唯一答案。

#### `event source mapping`

- **控制什麼：** `event source mapping`指定AWS Lambda讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `DLQ/destination`

- **控制什麼：** `DLQ/destination`指定AWS Lambda讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `VPC`

- **控制什麼：** `VPC`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Lambda的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `ephemeral storage`

- **控制什麼：** `ephemeral storage`選擇AWS Lambda的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

## 讀到這裡，請用自己的話說一次

1. Amazon API Gateway的責任：提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。
2. 底層機制：Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。
3. 第一個要看的設定：REST/HTTP/WebSocket API、routes/resources、stages、authorizers、usage plans、throttling、CORS與integration timeout。
4. 選擇邏輯：API Gateway作managed入口，整合Lambda或HTTP backend，使用authorizer/Cognito與usage controls。
5. 不要混淆：Amazon Cognito的責任是「為consumer/mobile/web applications提供user sign-up/sign-in與AWS credential federation。」；它不會自動取代Amazon API Gateway。
6. 替換訊號：一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。
7. 最常見錯法：只依API key做身份驗證，或timeout/retry設定使client與Lambda重複寫入。
8. 可移植原則：put protocol policy at a managed edge。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon API Gateway | 提供managed REST/HTTP/WebSocket API入口、授權、throttling與整合。 | Gateway驗證request、執行authorizer/mapping，再代理Lambda、HTTP或AWS service integration。 | serverless API、公開/私有API、consumer治理與request transformation。 | 一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。 |
| Amazon Cognito | 為consumer/mobile/web applications提供user sign-up/sign-in與AWS credential federation。 | User Pool發OIDC tokens；Identity Pool把已驗證身份交換成temporary IAM credentials。 | 數十萬外部customers的authentication與social/enterprise federation。 | 員工多帳號AWS console access用IAM Identity Center；service workload用IAM role。 |
| AWS Lambda | 按事件執行短生命函式，自動管理capacity與runtime基礎設施。 | 事件觸發execution environment；concurrency是同時執行數，環境可能重用但不可當durable state。 | 事件驅動、不可預測流量、短工作、API或資料轉換，且希望最少主機營運時。 | 長時間process、持久connection、特殊OS/driver或穩定高利用率時選container/EC2。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | ALB也能直接整合Lambda或containers，適合較簡單、已有VPC routing的HTTP服務。 | 只有當題目條件明確改變時才可能合理。 | 只依API key做身份驗證，或timeout/retry設定使client與Lambda重複寫入。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「ALB也能直接整合Lambda或containers，適合較簡單、已有VPC routing的HTTP服務。」之間做選擇。
- 認得常考設定：REST/HTTP/WebSocket API、routes/resources、stages、authorizers、usage plans、throttling、CORS與integration timeout。
- 對應官方tasks：SAA-1.2 Design secure workloads and applications；SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：一般web load balancing用ALB；長時間或非常高吞吐TCP用NLB。
- 對應官方tasks：SAP-2.3 Determine security controls based on requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals。

## 本章 10 題考題

### 練習題 1｜SAA｜REST API、HTTP API 與 ALB 選型

新 API 只需 OIDC JWT、Lambda proxy 與低 request cost，不需 API keys、usage plans、request validation 或 API cache。哪個入口最貼合？

A. REST API，因名稱含 REST 就永遠優於其他入口
B. HTTP API，因它支援所需 JWT/proxy 且較精簡；若未來需要 REST-only features 再重評估
C. ALB，因 listener rule 原生提供 per-customer usage plans
D. WebSocket API，因可完全取代同步 HTTP

**答案：B**

- **A：** 錯誤。應按 feature contract 選型，REST API 的額外功能在本題不是需求。
- **B：** 正確。HTTP API 符合 JWT 與 proxy 需求且營運/費用較精簡。
- **C：** 錯誤。ALB 可作 L7 routing，但不原生提供 API Gateway usage plans/API keys。
- **D：** 錯誤。WebSocket 解決持久雙向連線，並非一般 HTTP request-response 的自動替代。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Choose between REST APIs and HTTP APIs - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html)

### 練習題 2｜SAA｜API request authorization path

Mobile client 透過 custom domain 呼叫 /orders。哪個順序最合理？

A. API key 先證明 end-user identity，再由 DNS 執行 Lambda
B. Gateway 匹配 API/stage/route，執行 JWT/IAM/Lambda authorizer 與 request processing，再呼叫 integration；backend 仍檢查訂單 ownership
C. Cognito user pool 直接修改 database，無需 integration
D. Stage deployment 自動更新 backend schema

**答案：B**

- **A：** 錯誤。API key 用於識別 client/計量，不是使用者 authentication。
- **B：** 正確。入口驗證 caller，backend 仍擁有 resource-level business authorization。
- **C：** 錯誤。User pool 提供身份，不執行應用 integration。
- **D：** 錯誤。API deployment 與 database schema lifecycle 是不同責任。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Control and manage access to REST APIs in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-control-access-to-api.html)、[Create a deployment for a REST API in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-deployments.html)

### 練習題 3｜SAP｜Latency 與 IntegrationLatency 診斷

API Gateway Latency p95 為 4.2 秒，IntegrationLatency 為 4.0 秒，4XX 很低且 backend CPU 飽和。應先用哪個觀察結果定位並處理主要瓶頸？

A. Latency 與 IntegrationLatency 差值約 0.2 秒，表示先調整 Gateway mapping template 與 authorizer cache，而不檢查 backend
B. AuthorizerLatency 很低但 IntegrationLatency 很高，表示先增加 API key 數量來縮短 backend execution
C. Backend integration 的 capacity/code path，因大部分時間發生在 integration
D. 把 integration timeout 調到更高，因 timeout 增加會直接降低已觀察到的 backend CPU 與執行時間

**答案：C**

- **A：** 錯誤。0.2 秒確實近似 Gateway 自身開銷，但 4.0 秒都發生在 integration；沒有證據顯示 mapping 或 authorizer 才是主要瓶頸。
- **B：** 錯誤。API key 是 consumer identification 與 usage-plan 關聯資料，不會增加 backend CPU capacity，也不會縮短 Lambda 或 HTTP integration 的處理時間。
- **C：** 正確。IntegrationLatency 幾乎占完整 Latency，且 backend CPU 已飽和；應先 profile code、擴充 integration capacity 或降低 downstream contention，再重新量測 Gateway overhead。
- **D：** 錯誤。提高 timeout 只延長 Gateway 等待時間，可能讓更多慢請求占住 backend 資源；它不會修正 CPU saturation 或降低實際 execution duration。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Amazon API Gateway dimensions and metrics - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)

### 練習題 4｜SAA｜JWT、tenant authorization 與硬性 entitlement

SaaS API 要驗證 OIDC user、防止 tenant A 讀 tenant B 訂單，並執行不可超過的每日付費 entitlement；超額 request 不得只靠近似流量整形。哪個設計正確？

A. 只要求 x-api-key，並把 key 當作 user login
B. 只設定 CORS，因瀏覽器會阻止所有未授權 callers
C. JWT authorizer 驗證身份，backend 依 claims 檢查 tenant ownership，並以 durable、具原子更新的 entitlement counter 強制硬額度；REST API usage plan 只作 best-effort throttling/計量
D. Resource policy Principal:* 自動識別 tenant

**答案：C**

- **A：** 錯誤。API key 可分享且不代表 end-user identity。
- **B：** 錯誤。非瀏覽器 clients 不受 CORS 保護，CORS 也不做資料授權。
- **C：** 正確。JWT 解決 caller identity，backend 解決 tenant resource authorization；API Gateway usage-plan throttling 與 quota 是 best effort，付費 entitlement 必須由持久且可一致更新的計數器強制執行。
- **D：** 錯誤。無條件 wildcard 不包含 tenant identity boundary。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Control and manage access to REST APIs in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-control-access-to-api.html)、[Usage plans and API keys for REST APIs in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)

### 練習題 5｜SAP｜Backward-compatible API rollout

舊 mobile clients 可能半年不更新，新版要改 response schema。如何安全發布？

A. 直接改原 route 並刪除舊欄位
B. 提高 integration timeout
C. 刪除舊 stage 迫使 clients 升級
D. 維持 backward compatibility 或新 versioned route，採 expand/contract backend change，小流量 canary 後依 error/business metrics 推進

**答案：D**

- **A：** 錯誤。直接移除舊欄位會破壞既有 response contract；無法同步更新的 mobile clients 可能在解析時失敗，且沒有可獨立回滾的版本邊界。
- **B：** 錯誤。Integration timeout 只控制 Gateway 等待 backend 的時間，不會讓舊 client 理解新的 JSON schema，也不提供 expand/contract migration。
- **C：** 錯誤。刪除舊 stage 會讓半年內無法受控升級的 clients 直接失去 endpoint；這是強迫中斷，不是 backward-compatible rollout。
- **D：** 正確。雙版本相容與 canary 將 client lifecycle 和 server rollout 解耦。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Set up an API Gateway canary release deployment - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/canary-release.html)

### 練習題 6｜SAP｜API Gateway 429、502、504

三個 request 分別遇到 usage-plan throttle、Lambda proxy 回傳非預期格式、backend 超過 integration timeout。最可能的 status 對應為何？

A. 429、502、504
B. 401、429、301
C. 502、403、429
D. 504、502、200

**答案：A**

- **A：** 正確。429 指 throttling，502 常見於 proxy response/integration error，504 表示 integration 未及時回應。
- **B：** 錯誤。401 通常表示身份驗證未成立，301 是重新導向；它們都無法描述 usage-plan throttle、Lambda proxy response 格式錯誤與 integration timeout。
- **C：** 錯誤。Throttle 由 API Gateway 回應 429，不是 502；Lambda proxy 回傳格式不符合契約時常見 502，也不是 resource-policy 造成的 403。
- **D：** 錯誤。Throttle 不會一般映射為 504；backend 超過 integration timeout 時 Gateway 不能假裝成功回 200，應以 execution/access logs 確認 504 根因。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Handle Lambda errors in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/handle-errors-in-lambda-integration.html)、[Gateway response types for API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/supported-gateway-response-types.html)

### 練習題 7｜SAA｜HTTP API 與 caching 成本

每月十億次 simple JWT proxy requests，不用 REST-only features；其中產品 GET 可安全快取 60 秒。哪個方向最合理？

A. 移除 authentication 以省費用
B. 全部改 WebSocket
C. 改用 HTTP API；對可快取 GET 評估 CloudFront 或必要時 REST cache，並正確設計 cache key/invalidation
D. 把 throttling 設無限即可降低 request 單價

**答案：C**

- **A：** 錯誤。移除 authentication 雖可能省下一部分 authorizer 工作，但直接違反 OIDC 身份需求；成本最佳化不能以取消必要安全控制為代價。
- **B：** 錯誤。WebSocket 適合長連線與雙向訊息，不會自動降低一般 request-response 的請求量；還會引入 connection lifecycle 與 state 管理責任。
- **C：** 正確。先選較精簡 API 類型，再用語意正確的 cache 降低 backend demand。
- **D：** 錯誤。Throttle 上限不改變 API request 定價，且可能壓垮 backend。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Choose between REST APIs and HTTP APIs - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html)、[Manage how long content stays in the cache (expiration) - Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html)

### 練習題 8｜SAA｜Private REST API

REST API 只能由兩個 VPC 的 workloads 呼叫，不得經 public Internet。哪個配置符合？

A. Edge-optimized public API 配難猜 URL
B. Private REST API 搭 execute-api interface endpoints、private DNS/SG，resource policy 限制 VPC endpoint/principal
C. 只加 API key
D. 讓 private instances 經 NAT 呼叫 public API，API 就成為 private

**答案：B**

- **A：** 錯誤。Edge-optimized endpoint 仍可從 public Internet 到達；URL 難猜只屬於 obscurity，不能替代 interface endpoint、resource policy 與來源限制。
- **B：** 正確。Private API 與 interface endpoint 建立私有 data path，resource policy 再限制可用來源。
- **C：** 錯誤。API key 可識別 usage-plan consumer，但不會關閉 public execute-api endpoint，也不會建立兩個 VPC 到 API Gateway 的私有 network path。
- **D：** 錯誤。NAT 是 outbound path，目的 API 仍是 public endpoint。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Private REST APIs in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-private-apis.html)

### 練習題 9｜SAP｜Multi-Region regional API failover

同一 custom domain 要在兩個 Region 提供 API，Region failure RTO 需數分鐘，order writes 必須避免重複。選擇兩項。

A. 每 Region 部署獨立 Regional API/backend/certificate 與健康入口，以 Route 53 等機制導流
B. 單一 edge-optimized API 會自動複寫所有 backend state
C. 只降低 TTL 即保證既有 connections 零中斷
D. 只複製 Lambda zip 即完成 DR
E. 設計 state replication、idempotency key、目標 Region IAM/KMS/quota，並定期演練 failover

**答案：A、E**

- **A：** 正確。每個 Region 必須有完整可服務 stack 與可觀測 endpoint。
- **B：** 錯誤。Edge endpoint 不會替 customer 複寫 database/application state。
- **C：** 錯誤。Resolver cache、existing connections 與 backend recovery 仍影響 RTO。
- **D：** 錯誤。Lambda package 只是 compute artifact；database state、custom domain/certificate、IAM/KMS、quota、event sources 與依賴服務若未在目標 Region 就緒，仍無法接管。
- **E：** 正確。DR 的可用性由資料複寫、runtime identity、目標容量與 idempotency 共同決定；演練還要量測 DNS cache、既有連線及 application recovery 對 RTO 的影響。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[API endpoint types for REST APIs in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-endpoint-types.html)、[Failover routing - Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)

### 練習題 10｜SAP｜Public API 身份與濫用保護

一個 Regional REST API 必須識別使用者、限制 abusive clients，且 Lambda backend 與下游資料庫不得被突發流量壓垮。選擇兩項。

A. 只用 API key 作 authentication
B. 使用 JWT/IAM/Lambda authorizer，並由 backend 執行 resource-level authorization
C. CORS 可阻止所有非瀏覽器攻擊
D. 取消 Lambda reserved concurrency 以避免 429
E. 在 REST API stage 關聯 AWS WAF rate-based rules，配置 stage/account throttling；usage-plan quota 只作 best-effort shaping，另以 Lambda reserved concurrency/backpressure 保護 downstream

**答案：B、E**

- **A：** 錯誤。API key 用於識別 REST API usage-plan consumer，可能被分享或外洩；它不是 end-user authentication，也不能單獨證明 caller 可讀某筆資源。
- **B：** 正確。Authorizer 在入口驗證 caller，backend 再根據 claims 與 resource ownership 做授權；兩層分工可避免已登入使用者跨 tenant 讀取資料。
- **C：** 錯誤。CORS 是瀏覽器是否允許前端程式讀取跨來源 response 的政策；非瀏覽器攻擊者不受它約束，因此不是通用濫用防護。
- **D：** 錯誤。移除 reserved concurrency 讓 Lambda 更容易擴張到超過資料庫連線與吞吐預算；429 可能減少，但只會把失敗往 downstream 轉移。
- **E：** 正確。Regional REST API stage 可直接關聯 AWS WAF；WAF、Gateway throttle 與 usage plan 先整形流量，但硬性保護仍需 reserved concurrency、queue/backoff 或 backend admission control。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Control and manage access to REST APIs in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-control-access-to-api.html)、[Throttle requests to your REST APIs for better throughput in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)、[Using rate-based rule statements in AWS WAF - AWS WAF, AWS Firewall Manager, AWS Shield Advanced, and AWS Shield network security director](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based.html)、[Usage plans and API keys for REST APIs in API Gateway - Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)、[AWS WAF - AWS WAF, AWS Firewall Manager, AWS Shield Advanced, and AWS Shield network security director](https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html)、[Configuring reserved concurrency for a function - AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「API Gateway作managed入口，整合Lambda或HTTP backend，使用authori…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Public API需要authentication、throttling、routing、transformation與版本管理。」，所以「API Gateway作managed入口，整合Lambda或HTTP backend，使用authorizer/Cognito與usage controls。」能直接滿足它；若constraint改成「ALB也能直接整合Lambda或containers，適合較簡單、已有VPC routing的HTTP服務。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「API Gateway作managed入口，整合Lambda或HTTP backend，使用authorizer/Cognito與usage controls。」。替代方案「ALB也能直接整合Lambda或containers，適合較簡單、已有VPC routing的HTTP服務。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「只依API key做身份驗證，或timeout/retry設定使client與Lambda重複寫入。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Public API需要authentication、throttling、routing、transformation與版本管理。」，排除會導致「只依API key做身份驗證，或timeout/retry設定使client與Lambda重複寫入。」的選項，再選「API Gateway作managed入口，整合Lambda或HTTP backend，使用authorizer/Cognito與usage controls。」。本章對應的代表task包括：SAA-1.2 Design secure workloads and applications；SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「API Gateway作managed入口，整合Lambda或HTTP backend，使用authorizer/Cognito與usage controls。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「put protocol policy at a managed edge」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 38 章　ECS、EKS、Fargate 與 ECR

Container平台要在Kubernetes生態、控制需求、團隊能力與營運負擔間選擇。

## 跟著一份工作走：先從故事開始

想像你剛接手一個正在上線的系統。團隊告訴你：團隊有十個微服務、無Kubernetes經驗，另有一套必須使用K8s operator的vendor產品。 看起來只是一句需求，但工程師必須把它拆成幾個可以驗證的問題：流量從哪裡來、資料落在哪裡、哪個步驟可能失敗，以及誰負責把服務救回來。

如果只問「該用哪個服務」，討論通常很快失焦。更好的問題是：Container平台要在Kubernetes生態、控制需求、團隊能力與營運負擔間選擇。 這會迫使我們先說清楚限制，再判斷哪些能力是必要、哪些只是看起來方便。 這樣每個服務才有明確工作，而不是一起出現在一張擁擠的圖裡。

先借用一個日常畫面：把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。 類比的用途是讓你找到方向；真正驗證時，我們仍會回到request、state與實際設定。

現在才讓服務名稱進場。Amazon ECS負責主要工作，Amazon EKS提醒我們答案不是永遠固定。本章會走向「偏AWS整合與簡單orchestration用ECS；需要Kubernetes API/ecosystem用EKS；不管節點用Fargate。」，但你會同時看到需求在哪個時刻改變，答案也會跟著翻轉。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：團隊有十個微服務、無Kubernetes經驗，另有一套必須使用K8s operator的vendor產品。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[Amazon ECS]
          │ 以AWS原生control plane排程與維護containers。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · Amazon EKS：提供managed Kubernetes control plane與AWS整合。
  · AWS Fargate：讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。
  · Amazon ECR：保存、掃描與複寫OCI container images/artifacts。

失敗時先找：因履歷或流行選EKS，卻沒有cluster upgrade、network policy與observability能力。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問Amazon ECS有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，Amazon ECS和Amazon EKS並不是兩個任意的產品名稱。前者適合本章，是因為「偏AWS整合與簡單orchestration用ECS；需要Kubernetes API/ecosystem用EKS；不管節點用Fargate。」直接回應了眼前的問題；後者描述的「EC2 launch type提供instance與daemon控制，但需管理capacity與patch。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：因履歷或流行選EKS，卻沒有cluster upgrade、network policy與observability能力。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「platform choice must fit the operating model」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| Amazon ECS | 以AWS原生control plane排程與維護containers。 | Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。 |
| Amazon EKS | 提供managed Kubernetes control plane與AWS整合。 | AWS管理高可用API server/etcd；pods由managed node groups、self-managed nodes或Fargate執行。 |
| AWS Fargate | 讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。 | AWS在隔離的microVM容量上放置工作；使用者仍設定每個task的CPU、memory、network與IAM。 |
| Amazon ECR | 保存、掃描與複寫OCI container images/artifacts。 | Registry以repository/tag/digest管理layers；ECS/EKS execution role拉取image。 |

## 把全圖套進一個具體案例

**場景：** 團隊有十個微服務、無Kubernetes經驗，另有一套必須使用K8s operator的vendor產品。

1. 故事的起點：團隊有十個微服務、無Kubernetes經驗，另有一套必須使用K8s operator的vendor產品。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：Amazon ECS負責「以AWS原生control plane排程與維護containers。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EKS、AWS Fargate、Amazon ECR各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「因履歷或流行選EKS，卻沒有cluster upgrade、network policy與observability能力。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### Amazon ECS

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：Container平台要在Kubernetes生態、控制需求、團隊能力與營運負擔間選擇。
- **具體例子／邊界：** 在「團隊有十個微服務、無Kubernetes經驗，另有一套必須使用K8s operator的vendor產品。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EKS

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：EC2 launch type提供instance與daemon控制，但需管理capacity與patch。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：因履歷或流行選EKS，卻沒有cluster upgrade、network policy與observability能力。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：platform choice must fit the operating model。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### security group

附在ENI的stateful allow-only network firewall；回程流量會自動被視為已允許connection的一部分。

### control plane

建立或修改resource、policy、route、capacity與metadata的管理路徑。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### replica

authoritative資料的副本，可用於讀取、可用性或DR；要理解同步/非同步、lag與promotion語意。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### Region

AWS的地理部署邊界，包含多個AZ；服務、quota與資料多半以Region為scope，不會自動跨Region複製。

### subnet

VPC中位於單一AZ的IP與route-table邊界；public/private由route與public address決定，不是名稱決定。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### ENI

Elastic Network Interface，VPC中的虛擬網卡，持有private IP、security groups與流量。

## 回到 AWS：Components、功用與責任邊界

### Amazon ECS

- **功用：** 以AWS原生control plane排程與維護containers。
- **底層機制：** Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。
- **關鍵設定：** task definition、taskRoleArn、executionRoleArn、networkMode、capacity provider、service deployment與health check。
- **選擇時機：** 團隊要container但不需要Kubernetes API與生態相容性時。
- **替換時機：** 既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。

### Amazon EKS

- **功用：** 提供managed Kubernetes control plane與AWS整合。
- **底層機制：** AWS管理高可用API server/etcd；pods由managed node groups、self-managed nodes或Fargate執行。
- **關鍵設定：** cluster endpoint access、node groups、IRSA/Pod Identity、CNI、add-ons、taints與pod disruption budget。
- **選擇時機：** 需要Kubernetes API、生態、portable manifests、operators或既有平台技能時。
- **替換時機：** 不需要Kubernetes複雜度時以ECS降低營運；單一事件handler可用Lambda。

### AWS Fargate

- **功用：** 讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。
- **底層機制：** AWS在隔離的microVM容量上放置工作；使用者仍設定每個task的CPU、memory、network與IAM。
- **關鍵設定：** task CPU/memory組合、awsvpc、subnets/security groups、ephemeral storage與platform version。
- **選擇時機：** bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。
- **替換時機：** 穩定高利用率或需GPU、特殊daemon/host access時改用EC2-backed ECS/EKS。

### Amazon ECR

- **功用：** 保存、掃描與複寫OCI container images/artifacts。
- **底層機制：** Registry以repository/tag/digest管理layers；ECS/EKS execution role拉取image。
- **關鍵設定：** repository policy、lifecycle policy、immutability、scan on push、KMS與cross-Region/account replication。
- **選擇時機：** ECS/EKS/Fargate的private image supply chain。
- **替換時機：** 它不執行containers；執行由ECS/EKS/App Runner等負責。

## 考前與實作時再查：設定操作手冊

### Amazon ECS：逐項設定說明

#### `task definition`

- **控制什麼：** `task definition`是可版本化的啟動或工作規格，定義Amazon ECS建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `taskRoleArn`

- **控制什麼：** `taskRoleArn`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「團隊要container但不需要Kubernetes API與生態相容性時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ECS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `executionRoleArn`

- **控制什麼：** `executionRoleArn`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「團隊要container但不需要Kubernetes API與生態相容性時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ECS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `networkMode`

- **控制什麼：** `networkMode`決定workload如何取得network identity或接入load-balancing/service path。
- **何時需要：** Container、endpoint或application需要穩定入口、獨立ENI/IP或跨network consumer時。
- **怎麼設定／驗證：** 明確選擇network mode、target type、subnets與SG，建立health check及DNS；從client到target逐跳驗證。
- **常見錯法：** 有load balancer不代表target健康；network mode與target type不相容會無法註冊或無法回程。

#### `capacity provider`

- **控制什麼：** `capacity provider`設定Amazon ECS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「團隊要container但不需要Kubernetes API與生態相容性時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `service deployment`

- **控制什麼：** `service deployment`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「團隊要container但不需要Kubernetes API與生態相容性時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ECS設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

#### `health check`

- **控制什麼：** `health check`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「團隊要container但不需要Kubernetes API與生態相容性時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ECS設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

### Amazon EKS：逐項設定說明

#### `cluster endpoint access`

- **控制什麼：** `cluster endpoint access`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「需要Kubernetes API、生態、portable manifests、operators或既有平台技能時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EKS的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `node groups`

- **控制什麼：** `node groups`設定Amazon EKS的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「需要Kubernetes API、生態、portable manifests、operators或既有平台技能時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `IRSA/Pod Identity`

- **控制什麼：** `IRSA/Pod Identity`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「需要Kubernetes API、生態、portable manifests、operators或既有平台技能時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EKS明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `CNI`

- **控制什麼：** `CNI`決定workload如何取得network identity或接入load-balancing/service path。
- **何時需要：** Container、endpoint或application需要穩定入口、獨立ENI/IP或跨network consumer時。
- **怎麼設定／驗證：** 明確選擇network mode、target type、subnets與SG，建立health check及DNS；從client到target逐跳驗證。
- **常見錯法：** 有load balancer不代表target健康；network mode與target type不相容會無法註冊或無法回程。

#### `add-ons`

- **控制什麼：** `add-ons`指定Amazon EKS依賴的runtime integration、scheduler限制、proxy相容性或要連接的AWS endpoint。
- **何時需要：** Managed control plane仍需要local agent、cluster extension、placement constraint或具名service integration時。
- **怎麼設定／驗證：** 鎖定版本與service identifier，配置network/IAM，先在非production驗證compatibility；taint同時配置對應toleration。
- **常見錯法：** Agent/add-on版本落後會造成同步或network問題；只設taint沒有toleration會讓pods無法排程，service name選錯Region也無法連線。

#### `taints`

- **控制什麼：** `taints`指定Amazon EKS依賴的runtime integration、scheduler限制、proxy相容性或要連接的AWS endpoint。
- **何時需要：** Managed control plane仍需要local agent、cluster extension、placement constraint或具名service integration時。
- **怎麼設定／驗證：** 鎖定版本與service identifier，配置network/IAM，先在非production驗證compatibility；taint同時配置對應toleration。
- **常見錯法：** Agent/add-on版本落後會造成同步或network問題；只設taint沒有toleration會讓pods無法排程，service name選錯Region也無法連線。

#### `pod disruption budget`

- **控制什麼：** `pod disruption budget`決定成本如何計量、承諾、分攤或告警，應對應到business unit economics。
- **何時需要：** 當需求符合「需要Kubernetes API、生態、portable manifests、operators或既有平台技能時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EKS設定account/tag/service filters、time granularity、threshold與owner；比較actual、forecast、coverage、utilization及每成功交易成本。
- **常見錯法：** 只看總帳單或購買承諾折扣，可能掩蓋閒置、跨AZ/NAT流量與錯誤架構；forecast alarm也不等於自動阻止花費。

### AWS Fargate：逐項設定說明

#### `task CPU/memory組合`

- **控制什麼：** `task CPU/memory組合`設定AWS Fargate的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `awsvpc`

- **控制什麼：** `awsvpc`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Fargate的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `subnets/security groups`

- **控制什麼：** `subnets/security groups`決定network scope或下一跳，影響封包是否可達、是否留在private path及故障範圍。
- **何時需要：** 當需求符合「bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Fargate的network/API/IaC設定具體IDs、CIDRs與方向；逐跳畫出client→entry→target及return path，再以Flow Logs或連通測試驗證。
- **常見錯法：** 只建立資源卻漏掉雙向route、DNS或security規則，會得到timeout；CIDR重疊與非對稱routing也不是增加allow rule能修好。

#### `ephemeral storage`

- **控制什麼：** `ephemeral storage`選擇AWS Fargate的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

#### `platform version`

- **控制什麼：** `platform version`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Fargate鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

### Amazon ECR：逐項設定說明

#### `repository policy`

- **控制什麼：** `repository policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「ECS/EKS/Fargate的private image supply chain。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ECR明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `lifecycle policy`

- **控制什麼：** `lifecycle policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「ECS/EKS/Fargate的private image supply chain。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ECR明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `immutability`

- **控制什麼：** `immutability`控制artifact不可覆寫、client驗證，或capacity/discount方案如何選擇與面對中斷。
- **何時需要：** Image supply chain、managed broker access，或Spot/Reserved capacity需要可預測風險與成本時。
- **怎麼設定／驗證：** 開啟immutable tags與scan；authentication選IAM/SASL/TLS並測試；Spot使用capacity-optimized與instance diversification，建立checkpoint/termination handling。
- **常見錯法：** 只設max price不能保證Spot capacity；mutable image tag會讓同一版本指向不同內容，authentication也不取代topic/network authorization。

#### `scan on push`

- **控制什麼：** `scan on push`定義Amazon ECR用什麼規則檢查結果、產生finding/evidence，或判斷migration/deployment是否可接受。
- **何時需要：** 需要在production前發現資料錯誤、漏洞、相容性或control gap，並留下可稽核證據時。
- **怎麼設定／驗證：** 選擇scope、rules與severity，建立baseline，將結果送到具名owner與修復SLA；對高風險結果做第二種方式驗證。
- **常見錯法：** 工具顯示pass只代表它看得到的scope；false positive、stale inventory與未涵蓋resources仍需交叉檢查。

#### `KMS`

- **控制什麼：** `KMS`控制資料以哪把key保護、誰可解密，以及key/secret的生命週期。
- **何時需要：** 當需求符合「ECS/EKS/Fargate的private image supply chain。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon ECR指定customer/AWS managed key、key/resource policy、rotation與跨帳號條件；分別測試service role及讀取者的decrypt權限。
- **常見錯法：** 資源policy允許讀資料不代表KMS也允許Decrypt；停用、刪除或Region錯誤的key可能讓備份與production資料同時不可讀。

#### `cross-Region/account replication`

- **控制什麼：** `cross-Region/account replication`選擇地理、AZ或service locality，影響latency、法規、failure domain、features與data-transfer成本。
- **何時需要：** 部署Amazon ECR前依使用者位置、data residency、service availability與DR需求決定。
- **怎麼設定／驗證：** 建立Region/AZ matrix並用IaC參數化；驗證dependent services、KMS keys、AMIs、quotas與replication destinations都存在。
- **常見錯法：** 第二Region只有空resource不構成DR；跨AZ/Region還會增加資料同步複雜度與傳輸費。

## 讀到這裡，請用自己的話說一次

1. Amazon ECS的責任：以AWS原生control plane排程與維護containers。
2. 底層機制：Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。
3. 第一個要看的設定：task definition、taskRoleArn、executionRoleArn、networkMode、capacity provider、service deployment與health check。
4. 選擇邏輯：偏AWS整合與簡單orchestration用ECS；需要Kubernetes API/ecosystem用EKS；不管節點用Fargate。
5. 不要混淆：Amazon EKS的責任是「提供managed Kubernetes control plane與AWS整合。」；它不會自動取代Amazon ECS。
6. 替換訊號：既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。
7. 最常見錯法：因履歷或流行選EKS，卻沒有cluster upgrade、network policy與observability能力。
8. 可移植原則：platform choice must fit the operating model。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| Amazon ECS | 以AWS原生control plane排程與維護containers。 | Task definition描述image、CPU/memory、ports與roles；service scheduler維持desired count並整合LB。 | 團隊要container但不需要Kubernetes API與生態相容性時。 | 既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。 |
| Amazon EKS | 提供managed Kubernetes control plane與AWS整合。 | AWS管理高可用API server/etcd；pods由managed node groups、self-managed nodes或Fargate執行。 | 需要Kubernetes API、生態、portable manifests、operators或既有平台技能時。 | 不需要Kubernetes複雜度時以ECS降低營運；單一事件handler可用Lambda。 |
| AWS Fargate | 讓ECS或EKS task/pod在不管理EC2 nodes的情況下執行。 | AWS在隔離的microVM容量上放置工作；使用者仍設定每個task的CPU、memory、network與IAM。 | bursty containers、小平台團隊、每個task需獨立ENI與按使用量付費時。 | 穩定高利用率或需GPU、特殊daemon/host access時改用EC2-backed ECS/EKS。 |
| Amazon ECR | 保存、掃描與複寫OCI container images/artifacts。 | Registry以repository/tag/digest管理layers；ECS/EKS execution role拉取image。 | ECS/EKS/Fargate的private image supply chain。 | 它不執行containers；執行由ECS/EKS/App Runner等負責。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | EC2 launch type提供instance與daemon控制，但需管理capacity與patch。 | 只有當題目條件明確改變時才可能合理。 | 因履歷或流行選EKS，卻沒有cluster upgrade、network policy與observability能力。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「EC2 launch type提供instance與daemon控制，但需管理capacity與patch。」之間做選擇。
- 認得常考設定：task definition、taskRoleArn、executionRoleArn、networkMode、capacity provider、service deployment與health check。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：既有Kubernetes工具鏈選EKS；短事件函式選Lambda；不想管理nodes可搭配Fargate。
- 對應官方tasks：SAP-2.1 Design a deployment strategy to meet business requirements；SAP-2.4 Design a strategy to meet reliability requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.3 Determine a new architecture for existing workloads；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜ECS、EKS、Fargate 與 EC2 nodes

三個 workload 分別是：無 Kubernetes 需求的 AWS-native microservices、必須使用 Kubernetes operator 的 vendor app、需要 privileged daemon 與 GPU host access 的 container。哪個對應最佳？

A. 全部 EKS Fargate
B. Microservices 用 ECS；operator app 用 EKS；privileged/GPU workload 用 EC2-backed ECS/EKS nodes
C. Fargate 是獨立 orchestrator，可取代 ECS/EKS
D. ECR 可直接排程三者

**答案：B**

- **A：** 錯誤。Fargate 有功能限制，且無 K8s 需求不必承擔 EKS 複雜度。
- **B：** 正確。Orchestrator contract 與 host-control requirement 分別決定 ECS/EKS 與 Fargate/EC2。
- **C：** 錯誤。Fargate 是 ECS/EKS 的 compute option，不是 orchestrator。
- **D：** 錯誤。ECR 保存 images，不維持 running tasks/pods。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Choosing an AWS compute service - AWS Decision Guides](https://docs.aws.amazon.com/decision-guides/latest/compute-on-aws-how-to-choose/compute-on-aws-how-to-choose.html)、[Architect for AWS Fargate for Amazon ECS - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)

### 練習題 2｜SAA｜ECS service scheduling path

ECS service desired count 為 6，使用 Fargate capacity provider 與 awsvpc，image 在 ECR。哪個描述正確？

A. ECR repository policy決定 desired count
B. ALB listener 建立 Fargate capacity
C. Task definition 定義 image/resources/roles；service 維持 tasks；awsvpc 給每 task ENI；target group 路由 healthy tasks
D. Task role 專供 agent 拉 image，execution role 專供 app 呼叫 AWS API

**答案：C**

- **A：** 錯誤。Repository policy 控制 image access，不是 scheduler。
- **B：** 錯誤。ALB listener 只依規則把 request 轉送到已註冊且可用的 targets；它不解析 task definition，也不建立 Fargate task capacity。
- **C：** 正確。這是 artifact、runtime specification、scheduler、network 與 traffic 的責任鏈。
- **D：** 錯誤。兩個 role 的用途相反：task role 給 app，execution role 給 agent。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon ECS task definitions - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)、[Amazon ECS services - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html)

### 練習題 3｜SAP｜ECS service 與 cluster capacity 兩層 scaling

ALB requests/target 與 latency 升高，ECS service 已提高 desired count，但新 tasks 在 EC2-backed cluster 停留 Pending 並顯示 insufficient CPU。應如何修正？

A. 增加 ECR repository storage
B. 只繼續提高 service desired count
C. 只增加 EC2 nodes 但固定 task desired count
D. 同時讓 service scaling 增加 tasks，並以 capacity provider/cluster autoscaling 增加可放置 tasks 的 EC2 capacity

**答案：D**

- **A：** 錯誤。Image storage 與 runtime CPU capacity 無關。
- **B：** 錯誤。沒有 cluster headroom，更多 desired tasks 只會繼續 Pending。
- **C：** 錯誤。只有 nodes 不增加 tasks，application capacity 仍不變。
- **D：** 正確。Application task demand 與 underlying cluster capacity 是兩個相連但獨立的 control loops。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Automatically scale your Amazon ECS service - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html)、[Automatically manage Amazon ECS capacity with cluster auto scaling - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-auto-scaling.html)

### 練習題 4｜SAA｜Task role 與 execution role

ECS task 的 application 要 GetItem DynamoDB；ECS/Fargate agent 要從 private ECR pull image、取啟動時 secret 並送 logs。權限應放哪裡？

A. DynamoDB 權限放 task role；image pull/secret/log agent 權限放 execution role，兩者最小權限
B. 把 DynamoDB 與 ECR 權限都只放 execution role，因 application container 會自動繼承 execution role credentials
C. 在 ECS on EC2 時只擴大 container-instance profile，讓所有 tasks 共用 host credentials，不建立 task role
D. 只在 ECR repository policy 允許 task role；repository policy 會同時授權 DynamoDB GetItem 與 CloudWatch Logs

**答案：A**

- **A：** 正確。Task role 是 container application identity，execution role 是 ECS agent 執行啟動工作的 identity。
- **B：** 錯誤。Execution role credentials 供 ECS agent 執行 image pull、log 與啟動時 secret 等工作，不會成為 application container 呼叫 DynamoDB 的一般身分。
- **C：** 錯誤。Container-instance profile 是 ECS agent/host 的身分；讓所有 tasks 共用 host 權限會破壞 task-level least privilege，且 Fargate 沒有客戶管理的 EC2 host role。
- **D：** 錯誤。ECR repository policy 只控制對該 repository 的 actions；它不能跨服務授權 DynamoDB 或 CloudWatch Logs，仍需分別配置 task role 與 execution role。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon ECS task IAM role - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)、[Amazon ECS task execution IAM role - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)

### 練習題 5｜SAP｜ECS rolling deployment health

新 task 需 4 分鐘 warmup，且舊 task 有 60 秒長連線。部署常造成 healthy capacity 低於 SLO。最佳設定方向是什麼？

A. Push image 後立即 stop 全部舊 tasks
B. 只增加 ECR scan frequency
C. 設定 container/target health 與 grace、minimum/maximum healthy percent 或 circuit breaker，搭配 deregistration delay/graceful shutdown
D. Health command 固定 exit 0

**答案：C**

- **A：** 錯誤。先停止全部舊 tasks 會讓 healthy capacity 立即低於 desired count；新 tasks 又需四分鐘 warmup，因此在 readiness 通過前會形成可預期中斷。
- **B：** 錯誤。Image scanning 不控制 runtime rollout transitions。
- **C：** 正確。啟動健康門檻與 termination draining 必須一起覆蓋新舊 task 交接。
- **D：** 錯誤。假健康會把未 ready 或 deadlocked task 留在 rotation。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Deploy Amazon ECS services by replacing tasks - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-ecs.html)、[Edit target group attributes for your Application Load Balancer - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#deregistration-delay)

### 練習題 6｜SAP｜CannotPullContainerError

Private-subnet Fargate tasks 回報 CannotPullContainerError: i/o timeout；另一批則 AccessDenied。哪個檢查順序最完整？

A. 提高 ALB idle timeout
B. 增加 desired count
C. 修改 application task role 的 DynamoDB 權限即可
D. 檢查 execution role ECR 權限、repository policy/image digest，以及 private DNS、SG/routes、NAT 或 ECR/S3 endpoints

**答案：D**

- **A：** 錯誤。Load balancer timeout 不影響 image pull。
- **B：** 錯誤。增加 desired count 只會排程更多具有相同 execution role、route、DNS 或 endpoint 設定的 tasks，放大 image-pull 失敗與 event noise。
- **C：** 錯誤。Image pull 由 execution role/agent path 處理，不是 DynamoDB app permission。
- **D：** 正確。AccessDenied 與 timeout 分別要求驗證 identity/artifact 與 network dependency path。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[CannotPullContainer task errors in Amazon ECS - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_cannot_pull_image.html)、[Amazon ECR interface VPC endpoints (AWS PrivateLink) - Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)

### 練習題 7｜SAP｜Fargate 與 EC2/Spot 成本

50 個小服務流量不規則且團隊不想維護 nodes；另一個 fleet 全天 80% 利用率、可容忍部分 interruption。哪個成本策略合理？

A. 所有情況 Fargate 必然最低成本
B. Bursty 小服務評估 Fargate；高利用率 fleet 比較 EC2 capacity providers/Savings Plans，容錯部分加入 diversified Spot
C. EKS 有 control-plane 費所以 ECS tasks 免費
D. 把 task CPU/memory 設 0 即不收費

**答案：B**

- **A：** 錯誤。Fargate 降低 node operations，但穩定高利用率時 EC2 可能有較佳單位成本。
- **B：** 正確。應同時計入 utilization、discount/interruption 與操作人力。
- **C：** 錯誤。ECS/EKS 與 compute resources 各有其費用，不存在此抵銷。
- **D：** 錯誤。Fargate task definition 必須使用受支援的 CPU/memory 組合；設為零既不能通過註冊/排程，也不是規避 vCPU 與 memory 計費的方法。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Choosing an AWS compute service - AWS Decision Guides](https://docs.aws.amazon.com/decision-guides/latest/compute-on-aws-how-to-choose/compute-on-aws-how-to-choose.html)、[Automatically manage Amazon ECS capacity with cluster auto scaling - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-auto-scaling.html)

### 練習題 8｜SAA｜Fargate awsvpc networking

Fargate web task 要有 private IP，只接受 ALB traffic，並私下存取 ECR/S3。哪個配置正確？

A. awsvpc、private subnets、task SG inbound 只允許 ALB SG；以 ECR/S3 endpoints 或必要 NAT 提供 outbound dependencies
B. Fargate 不在 VPC，所以不能用 SG
C. 每個 task 必須有 public IP 才能 pull ECR
D. Host network mode 是 Fargate 唯一選擇

**答案：A**

- **A：** 正確。每個 Fargate task 取得 ENI，能用 subnet/SG 與 private service paths。
- **B：** 錯誤。Fargate tasks 可配置 VPC networking。
- **C：** 錯誤。Private endpoints 或 NAT 可提供 ECR/S3 path，不必直接 public IP。
- **D：** 錯誤。Fargate 使用 awsvpc networking。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon ECS task networking options for Fargate - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-networking.html)、[Amazon ECR interface VPC endpoints (AWS PrivateLink) - Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)

### 練習題 9｜SAP｜EKS control-plane、node 與 add-on upgrade

多團隊 EKS platform 要跨 minor version 升級，且服務 disruption 必須受控。選擇兩項。

A. 盤點 version skew、deprecated APIs 與 add-on 相容性，在 staging 驗證後依序升 control plane/add-ons/node groups
B. 直接升 production control plane，假設所有 manifests 自動相容
C. 用 PDB、readiness、rolling node-group update 與 spare capacity 控制 eviction/disruption
D. 把所有 pods 永久設不可驅逐
E. PDB 保證 application 永不失敗

**答案：A、C**

- **A：** 正確。EKS upgrade 是相依版本鏈，需先發現 API/add-on incompatibility。
- **B：** 錯誤。Control plane upgrade 不會修復 deprecated API 或 workload compatibility。
- **C：** 正確。PDB/readiness/headroom 可限制 voluntary disruption 並維持服務容量。
- **D：** 錯誤。完全禁止 eviction 會阻塞必要 node maintenance。
- **E：** 錯誤。PDB 只限制部分 voluntary disruptions，不是全面 availability guarantee。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Update existing cluster to new Kubernetes version - Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)、[Running highly-available applications - Amazon EKS](https://docs.aws.amazon.com/eks/latest/best-practices/application.html#pod-disruption-budgets)

### 練習題 10｜SAP｜ECR artifact approval enforcement 與 DR

Production 只能部署已核准且不能被覆寫的 container image；Region failure 時另一 Region 必須能 pull 相同 bytes。選擇兩項。

A. Production 永遠使用 latest tag
B. 以 AWS Signer/ECR managed signing 簽署 image，CI/CD gate 驗證 signature、scan severity 與 digest allowlist；啟用 tag immutability 並只部署核准 digest
C. 只掃描 ALB
D. 將 repository 設 public 以簡化 DR
E. 設定 cross-Region/account replication、repository/KMS policies，並在目標環境測試以 digest pull

**答案：B、E**

- **A：** 錯誤。Mutable latest 無法證明 artifact identity。
- **B：** 正確。Digest 與 tag immutability只解決 artifact identity；signature、掃描結果與 CI/CD admission gate 才能強制「通過核准才可部署」，避免未核准 image 僅因存在 ECR 就進入 production。
- **C：** 錯誤。ALB scanning 不驗證 image vulnerabilities 或 provenance。
- **D：** 錯誤。Public repository 擴大 exposure，且不處理治理/加密。
- **E：** 正確。Replication 與授權確保目標 Region 真正取得同一 artifact。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Preventing image tags from being overwritten in Amazon ECR - Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html)、[Sign images in Amazon ECR - Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-signing.html)、[Scan images for software vulnerabilities in Amazon ECR - Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)、[Private image replication in Amazon ECR - Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「偏AWS整合與簡單orchestration用ECS；需要Kubernetes API/ecosystem…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「Container平台要在Kubernetes生態、控制需求、團隊能力與營運負擔間選擇。」，所以「偏AWS整合與簡單orchestration用ECS；需要Kubernetes API/ecosystem用EKS；不管節點用Fargate。」能直接滿足它；若constraint改成「EC2 launch type提供instance與daemon控制，但需管理capacity與patch。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「偏AWS整合與簡單orchestration用ECS；需要Kubernetes API/ecosystem用EKS；不管節點用Fargate。」。替代方案「EC2 launch type提供instance與daemon控制，但需管理capacity與patch。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「因履歷或流行選EKS，卻沒有cluster upgrade、network policy與observability能力。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「Container平台要在Kubernetes生態、控制需求、團隊能力與營運負擔間選擇。」，排除會導致「因履歷或流行選EKS，卻沒有cluster upgrade、network policy與observability能力。」的選項，再選「偏AWS整合與簡單orchestration用ECS；需要Kubernetes API/ecosystem用EKS；不管節點用Fargate。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-2.2 Design highly available and/or fault-tolerant architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「偏AWS整合與簡單orchestration用ECS；需要Kubernetes API/ecosystem用EKS；不管節點用Fargate。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「platform choice must fit the operating model」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 39 章　Batch、EMR 與大型計算

離線工作需要queue、scheduler、依賴、重試與可中斷容量管理。

## 跟著一份工作走：先從故事開始

星期一早上的架構會議裡，有人把這個問題丟到白板上：每天處理TB級Spark ETL，另有百萬個獨立影片轉檔工作。 白板上很快會冒出好幾個AWS名稱。先把它們擦掉一分鐘，因為現在更重要的是看懂使用者究竟在等什麼，以及哪一個結果絕對不能出錯。

先把爭論收斂成一句可以被驗證的話：離線工作需要queue、scheduler、依賴、重試與可中斷容量管理。 服務選型只是後面的答案；前面的題目其實是在決定責任、狀態與故障邊界。 稍後比較選項時，我們會一直回到這句話，不讓產品功能把問題帶偏。

這裡可以先這樣想：把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。 但請同時記住它的邊界：類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。 好類比不是取代技術細節，而是幫你知道稍後的細節應該放在哪裡。

回到AWS世界，主角是AWS Batch，對照角色是Amazon EMR。我們選擇「一般container batch用AWS Batch；大數據Spark/Hadoop用EMR；平行HPC可搭Spot與placement。」，不是因為考試口訣，而是因為它剛好接住了前面那條故事裡不能妥協的部分。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：每天處理TB級Spark ETL，另有百萬個獨立影片轉檔工作。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[AWS Batch]
          │ 排程大量batch jobs到managed compute environments。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · Amazon EMR：提供managed Spark/Hadoop等big-data frameworks。
  · AWS Step Functions：以可視化state machine編排多步驟、retry、branch、parallel與human wo…
  · EC2 Spot Instances：使用AWS剩餘EC2 capacity取得大幅折扣，但可能被中斷。

失敗時先找：將大量短工作各自啟動完整cluster，或Spot interruption沒有checkpoint。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問AWS Batch有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Batch和Amazon EMR並不是兩個任意的產品名稱。前者適合本章，是因為「一般container batch用AWS Batch；大數據Spark/Hadoop用EMR；平行HPC可搭Spot與placement。」直接回應了眼前的問題；後者描述的「Step Functions可協調多階段工作，但不是高吞吐資料處理引擎。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：將大量短工作各自啟動完整cluster，或Spot interruption沒有checkpoint。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「separate orchestration from execution engines」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Batch | 排程大量batch jobs到managed compute environments。 | Job進queue，由scheduler依priority/dependencies放到EC2/Spot/Fargate capacity。 |
| Amazon EMR | 提供managed Spark/Hadoop等big-data frameworks。 | Cluster或serverless runtime把資料分區到workers平行處理，常以S3為durable storage。 |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 |
| EC2 Spot Instances | 使用AWS剩餘EC2 capacity取得大幅折扣，但可能被中斷。 | Capacity需求變化時AWS發出短通知回收instance；價格不是唯一風險，capacity pool多樣性更重要。 |

## 把全圖套進一個具體案例

**場景：** 每天處理TB級Spark ETL，另有百萬個獨立影片轉檔工作。

1. 故事的起點：每天處理TB級Spark ETL，另有百萬個獨立影片轉檔工作。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Batch負責「排程大量batch jobs到managed compute environments。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Job進queue，由scheduler依priority/dependencies放到EC2/Spot/Fargate capacity。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：Amazon EMR、AWS Step Functions、EC2 Spot Instances各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「將大量短工作各自啟動完整cluster，或Spot interruption沒有checkpoint。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「持續service用ECS/EKS；Spark/Hadoop ecosystem用EMR。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Batch

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：離線工作需要queue、scheduler、依賴、重試與可中斷容量管理。
- **具體例子／邊界：** 在「每天處理TB級Spark ETL，另有百萬個獨立影片轉檔工作。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### Amazon EMR

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Step Functions可協調多階段工作，但不是高吞吐資料處理引擎。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：將大量短工作各自啟動完整cluster，或Spot interruption沒有checkpoint。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：separate orchestration from execution engines。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### callback token

Workflow把唯一task token交給外部worker/approver，之後以SendTaskSuccess/Failure恢復暫停execution。

### workflow

把多個tasks、分支、等待、重試與補償串成可追蹤的state machine，而不是一串不可見的同步函式呼叫。

### catalog

描述datasets、schema、partition與location的metadata索引；它不保存原始資料本身。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### queue

保存待處理messages的buffer，解耦producer與consumer速率；長期超載只會讓backlog持續增加。

### retry

暫時失敗後再次嘗試；只有錯誤可恢復、operation安全且有總時間/次數上限時才合理。

### Spot

使用AWS剩餘EC2容量的折扣模式，可能收到短通知後被中斷，適合可重試、可分散或checkpoint workloads。

### ETL

Extract、Transform、Load，把來源資料抽取、清理/轉換後載入目標；ELT則先載入再於目標轉換。

### log

離散事件紀錄，通常包含時間、context與request ID；適合查細節但成本與敏感資料需治理。

## 回到 AWS：Components、功用與責任邊界

### AWS Batch

- **功用：** 排程大量batch jobs到managed compute environments。
- **底層機制：** Job進queue，由scheduler依priority/dependencies放到EC2/Spot/Fargate capacity。
- **關鍵設定：** job definition、queue priority、compute environment、vCPU/memory/GPU、array jobs、retry與timeout。
- **選擇時機：** rendering、scientific、ETL與可排隊的container batch。
- **替換時機：** 持續service用ECS/EKS；Spark/Hadoop ecosystem用EMR。

### Amazon EMR

- **功用：** 提供managed Spark/Hadoop等big-data frameworks。
- **底層機制：** Cluster或serverless runtime把資料分區到workers平行處理，常以S3為durable storage。
- **關鍵設定：** EC2/Serverless/EKS deployment、release label、instance fleets、managed scaling、EMRFS與bootstrap。
- **選擇時機：** 需要Spark、Hive、Presto、HBase等framework與大型ETL/ML。
- **替換時機：** 單純serverless SQL用Athena；managed visual ETL/catalog用Glue。

### AWS Step Functions

- **功用：** 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。
- **底層機制：** Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。
- **關鍵設定：** Standard/Express、Task/Choice/Map/Parallel/Wait、Retry/Catch、timeouts、callback token與logging。
- **選擇時機：** 長流程、補償、人工核准、可稽核orchestration與分散式map。
- **替換時機：** 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。

### EC2 Spot Instances

- **功用：** 使用AWS剩餘EC2 capacity取得大幅折扣，但可能被中斷。
- **底層機制：** Capacity需求變化時AWS發出短通知回收instance；價格不是唯一風險，capacity pool多樣性更重要。
- **關鍵設定：** allocation strategy、instance diversification、capacity-optimized、max price、interruption handling與mixed instances policy。
- **選擇時機：** batch、stateless、queue workers、CI、HPC等可checkpoint/重試工作。
- **替換時機：** 不可中斷single point、stateful primary或無重試設計不能只用Spot。

## 考前與實作時再查：設定操作手冊

### AWS Batch：逐項設定說明

#### `job definition`

- **控制什麼：** `job definition`是可版本化的啟動或工作規格，定義AWS Batch建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `queue priority`

- **控制什麼：** `queue priority`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「rendering、scientific、ETL與可排隊的container batch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Batch依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `compute environment`

- **控制什麼：** `compute environment`定義AWS Batch管理、評估或部署的邏輯scope，讓owner、resources與生命週期不混成全域集合。
- **何時需要：** 多團隊、多環境或migration portfolio需要分批管理、分權與追蹤狀態時。
- **怎麼設定／驗證：** 以business owner與lifecycle建立scope，關聯具體resources/accounts/Regions，版本化metadata並指定完成條件。
- **常見錯法：** 只按server數或resource name分組會拆開強依賴；scope沒有owner與exit criteria時，報表無法推動決策。

#### `vCPU/memory/GPU`

- **控制什麼：** `vCPU/memory/GPU`設定AWS Batch的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「rendering、scientific、ETL與可排隊的container batch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `array jobs`

- **控制什麼：** `array jobs`定義AWS Batch要執行的功能、命令或批次單位，是application behavior與release contract。
- **何時需要：** 同一artifact要依環境切換功能、建立可重複run流程或平行處理大量相似jobs時。
- **怎麼設定／驗證：** 版本化command/flag schema，設定validation/default與修改權限；以canary和明確rollback條件推出。
- **常見錯法：** 沒有owner/expiry的feature flag會永久累積；command、preset或array index不驗證會大規模重複失敗。

#### `retry`

- **控制什麼：** `retry`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「rendering、scientific、ETL與可排隊的container batch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Batch依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `timeout`

- **控制什麼：** `timeout`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「rendering、scientific、ETL與可排隊的container batch。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Batch的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

### Amazon EMR：逐項設定說明

#### `EC2/Serverless/EKS deployment`

- **控制什麼：** `EC2/Serverless/EKS deployment`選擇Amazon EMR的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `release label`

- **控制什麼：** `release label`控制新版本如何建立、分流、驗證與rollback，決定一次變更的blast radius。
- **何時需要：** 當需求符合「需要Spark、Hive、Presto、HBase等framework與大型ETL/ML。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon EMR設定分波比例、health/business alarms、bake time與automatic rollback；先部署到可隔離環境再逐步擴大。
- **常見錯法：** 只監看resource health會漏掉business regression；沒有database/schema backward compatibility時，rollback application也可能無法恢復。

#### `instance fleets`

- **控制什麼：** `instance fleets`設定Amazon EMR的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「需要Spark、Hive、Presto、HBase等framework與大型ETL/ML。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `managed scaling`

- **控制什麼：** `managed scaling`設定Amazon EMR的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「需要Spark、Hive、Presto、HBase等framework與大型ETL/ML。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `EMRFS`

- **控制什麼：** `EMRFS`選擇Amazon EMR的資料介面、持久性與容量，決定block/file/object semantics及replacement後是否保留。
- **何時需要：** Workload需要scratch、共享POSIX file、persistent block volume或object-backed data path時。
- **怎麼設定／驗證：** 先定義access pattern、容量、IOPS/throughput、AZ與backup，再設定volume/filesystem/mount並測試restart/replacement。
- **常見錯法：** Ephemeral storage不能保存唯一state；Multi-Attach也不自動提供cluster filesystem locking。

#### `bootstrap`

- **控制什麼：** `bootstrap`是可版本化的啟動或工作規格，定義Amazon EMR建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

### AWS Step Functions：逐項設定說明

#### `Standard/Express`

- **控制什麼：** `Standard/Express`選擇AWS Step Functions的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `Task/Choice/Map/Parallel/Wait`

- **控制什麼：** `Task/Choice/Map/Parallel/Wait`定義資料如何分區、排序、索引或查詢，是效能與正確性的data-model contract。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先列出AWS Step Functions的read/write access patterns，再選key/index/distribution與projection；用代表性資料量驗證hotspot、scan與query plan。
- **常見錯法：** 先建立table再猜key通常導致scan、hot partition與昂貴backfill；新增index也會增加write/storage成本與一致性考量。

#### `Retry/Catch`

- **控制什麼：** `Retry/Catch`控制message/record的重試、順序、批次與失敗隔離，決定consumer如何面對duplicate與backlog。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Step Functions依最長處理時間設定visibility/timeout與batch，建立DLQ/redrive、idempotency key及queue-age/iterator-age alarms。
- **常見錯法：** Exactly-once通常不是端到端保證；timeout過短會讓同一工作並行重做，retention增加也無法修正長期arrival rate大於service rate。

#### `timeouts`

- **控制什麼：** `timeouts`設定時間邊界，決定資料多久有效、工作多久算失敗、何時執行或多久後清理。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 以business latency、RTO/RPO與上游/downstream timeout chain設定AWS Step Functions的秒數或schedule；用最慢合理案例與故障注入驗證。
- **常見錯法：** 值太短會造成誤判、重試風暴或資料提前刪除；太長會延後failover、佔用capacity並增加過期資料與成本。

#### `callback token`

- **控制什麼：** `callback token`控制workflow如何等待外部結果、辨識execution、避免重複side effect並偵測worker失聯。
- **何時需要：** AWS Step Functions需要長時間等待人工/外部系統，或同一request可能重送而不能重複執行business action時。
- **怎麼設定／驗證：** 保存execution/business idempotency key；callback只接受正確task token，設定heartbeat/timeout並使完成API可安全重試。
- **常見錯法：** 把task token放公開URL、沒有到期/身份驗證，或只靠execution name去重，都可能造成越權核准或重複執行。

#### `logging`

- **控制什麼：** `logging`提供metric、log、trace或audit evidence，讓團隊知道request在哪一層失敗及是否達成business outcome。
- **何時需要：** 當需求符合「長流程、補償、人工核准、可稽核orchestration與分散式map。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Step Functions選擇destination、retention、sampling與敏感資料遮罩；建立可行動alarm並把request/trace ID貫穿上下游。
- **常見錯法：** 開啟logging不等於可觀測；沒有owner、threshold、查詢方式與retention時，只會產生成本卻不能縮短MTTR。

### EC2 Spot Instances：逐項設定說明

#### `allocation strategy`

- **控制什麼：** `allocation strategy`控制artifact不可覆寫、client驗證，或capacity/discount方案如何選擇與面對中斷。
- **何時需要：** Image supply chain、managed broker access，或Spot/Reserved capacity需要可預測風險與成本時。
- **怎麼設定／驗證：** 開啟immutable tags與scan；authentication選IAM/SASL/TLS並測試；Spot使用capacity-optimized與instance diversification，建立checkpoint/termination handling。
- **常見錯法：** 只設max price不能保證Spot capacity；mutable image tag會讓同一版本指向不同內容，authentication也不取代topic/network authorization。

#### `instance diversification`

- **控制什麼：** `instance diversification`設定EC2 Spot Instances的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「batch、stateless、queue workers、CI、HPC等可checkpoint/重試工作。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `capacity-optimized`

- **控制什麼：** `capacity-optimized`設定EC2 Spot Instances的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「batch、stateless、queue workers、CI、HPC等可checkpoint/重試工作。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `max price`

- **控制什麼：** `max price`控制artifact不可覆寫、client驗證，或capacity/discount方案如何選擇與面對中斷。
- **何時需要：** Image supply chain、managed broker access，或Spot/Reserved capacity需要可預測風險與成本時。
- **怎麼設定／驗證：** 開啟immutable tags與scan；authentication選IAM/SASL/TLS並測試；Spot使用capacity-optimized與instance diversification，建立checkpoint/termination handling。
- **常見錯法：** 只設max price不能保證Spot capacity；mutable image tag會讓同一版本指向不同內容，authentication也不取代topic/network authorization。

#### `interruption handling`

- **控制什麼：** `interruption handling`控制artifact不可覆寫、client驗證，或capacity/discount方案如何選擇與面對中斷。
- **何時需要：** Image supply chain、managed broker access，或Spot/Reserved capacity需要可預測風險與成本時。
- **怎麼設定／驗證：** 開啟immutable tags與scan；authentication選IAM/SASL/TLS並測試；Spot使用capacity-optimized與instance diversification，建立checkpoint/termination handling。
- **常見錯法：** 只設max price不能保證Spot capacity；mutable image tag會讓同一版本指向不同內容，authentication也不取代topic/network authorization。

#### `mixed instances policy`

- **控制什麼：** `mixed instances policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「batch、stateless、queue workers、CI、HPC等可checkpoint/重試工作。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在EC2 Spot Instances明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

## 讀到這裡，請用自己的話說一次

1. AWS Batch的責任：排程大量batch jobs到managed compute environments。
2. 底層機制：Job進queue，由scheduler依priority/dependencies放到EC2/Spot/Fargate capacity。
3. 第一個要看的設定：job definition、queue priority、compute environment、vCPU/memory/GPU、array jobs、retry與timeout。
4. 選擇邏輯：一般container batch用AWS Batch；大數據Spark/Hadoop用EMR；平行HPC可搭Spot與placement。
5. 不要混淆：Amazon EMR的責任是「提供managed Spark/Hadoop等big-data frameworks。」；它不會自動取代AWS Batch。
6. 替換訊號：持續service用ECS/EKS；Spark/Hadoop ecosystem用EMR。
7. 最常見錯法：將大量短工作各自啟動完整cluster，或Spot interruption沒有checkpoint。
8. 可移植原則：separate orchestration from execution engines。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Batch | 排程大量batch jobs到managed compute environments。 | Job進queue，由scheduler依priority/dependencies放到EC2/Spot/Fargate capacity。 | rendering、scientific、ETL與可排隊的container batch。 | 持續service用ECS/EKS；Spark/Hadoop ecosystem用EMR。 |
| Amazon EMR | 提供managed Spark/Hadoop等big-data frameworks。 | Cluster或serverless runtime把資料分區到workers平行處理，常以S3為durable storage。 | 需要Spark、Hive、Presto、HBase等framework與大型ETL/ML。 | 單純serverless SQL用Athena；managed visual ETL/catalog用Glue。 |
| AWS Step Functions | 以可視化state machine編排多步驟、retry、branch、parallel與human workflow。 | Amazon States Language保存state transition；service integrations直接呼叫AWS APIs並記錄execution history。 | 長流程、補償、人工核准、可稽核orchestration與分散式map。 | 純event routing用EventBridge；單一背景job buffer用SQS；不要在Lambda內sleep等待。 |
| EC2 Spot Instances | 使用AWS剩餘EC2 capacity取得大幅折扣，但可能被中斷。 | Capacity需求變化時AWS發出短通知回收instance；價格不是唯一風險，capacity pool多樣性更重要。 | batch、stateless、queue workers、CI、HPC等可checkpoint/重試工作。 | 不可中斷single point、stateful primary或無重試設計不能只用Spot。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Step Functions可協調多階段工作，但不是高吞吐資料處理引擎。 | 只有當題目條件明確改變時才可能合理。 | 將大量短工作各自啟動完整cluster，或Spot interruption沒有checkpoint。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Step Functions可協調多階段工作，但不是高吞吐資料處理引擎。」之間做選擇。
- 認得常考設定：job definition、queue priority、compute environment、vCPU/memory/GPU、array jobs、retry與timeout。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：持續service用ECS/EKS；Spark/Hadoop ecosystem用EMR。
- 對應官方tasks：SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-3.3 Determine a strategy to improve performance。

## 本章 10 題考題

### 練習題 1｜SAA｜Batch、EMR 與 Step Functions 邊界

公司有三種需求：十萬個獨立 container jobs、Spark 進行 TB 級 shuffle、以及跨 Lambda/Batch/人工核准的 workflow。哪個對應正確？

A. 全部使用 Step Functions 執行資料運算
B. 獨立 jobs 用 AWS Batch；Spark 用 EMR；跨服務 stateful orchestration 用 Step Functions
C. 每個短 job 建一個 EMR cluster
D. 用 Batch 取代 Spark distributed engine

**答案：B**

- **A：** 錯誤。Step Functions 編排工作，不提供 Spark 或 container compute engine。
- **B：** 正確。三者分別對應 queued compute、distributed data engine 與 workflow state。
- **C：** 錯誤。每個短 job 都建立 EMR cluster 會重複支付 provisioning、bootstrap 與 idle capacity 成本；EMR 適合執行分散式資料引擎，不是每個獨立 container task 的必要 scheduler。
- **D：** 錯誤。Batch 排程 containers，不實作 Spark shuffle/framework semantics。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/how-batch-works.html)、[What is Amazon EMR? - Amazon EMR](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html)、[Integrating services with Step Functions - AWS Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-services.html)

### 練習題 2｜SAA｜Batch submit-to-compute flow

一個影片轉碼 job 被提交到高優先 AWS Batch queue。該 queue 關聯一個 SPOT managed compute environment 與一個獨立 EC2 On-Demand managed compute environment。從提交到執行，哪個描述正確？

A. Queue 保存 input data 並取代 S3
B. 單一 compute environment 可在同一 computeResources.type 同時填 EC2 與 SPOT，scheduler 會在兩種 purchase option 間任意切換
C. Job definition 描述 image、resources、role 與 retry；scheduler 依 queue priority、job dependency、compute-environment order 與相容容量放置 job
D. Batch 必須由 Step Functions 才能排程

**答案：C**

- **A：** 錯誤。Job queue 保存排程狀態與優先順序，不保存影片 bytes；input/output 仍應放在 S3、EFS 或其他適合的 durable data store。
- **B：** 錯誤。Managed compute environment 的 computeResources.type 一次只指定一種資源類型，例如 EC2、SPOT、FARGATE、FARGATE_SPOT 或 ECS_MANAGED_INSTANCES；要組合 Spot 與 On-Demand，必須建立並關聯不同 compute environments。
- **C：** 正確。Job definition 是 runtime contract，queue 管理排序，scheduler 再依 dependency、queue priority、environment order 與 resource shape 尋找可用 capacity。
- **D：** 錯誤。Step Functions 是可選 orchestrator，Batch 可直接 submit。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/how-batch-works.html)、[Job definitions - AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/job_definitions.html)、[Compute environments for AWS Batch - AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/compute_environments.html)、[AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/job_queue_compute_environments.html)

### 練習題 3｜SAP｜RUNNABLE jobs 與 placement constraints

Batch jobs 長時間 RUNNABLE；compute environment 尚未達 max vCPUs，但 jobs 要求 4 GPUs，而允許的 instance types 沒有 GPU。應先做什麼？

A. 增加 S3 bucket 容量
B. 降低 job timeout
C. 增加 Step Functions history quota
D. 檢查 resource shape、instance-type/GPU 相容性、max vCPU、subnet IP 與 Spot/On-Demand capacity，加入可放置的 capacity

**答案：D**

- **A：** 錯誤。Object capacity 不影響 job placement。
- **B：** 錯誤。Job timeout 只限制開始執行後可運行多久；它不會修改 GPU resource requirement，也不會讓不含 GPU 的 instance types 變得可排程。
- **C：** 錯誤。Workflow history 與 Batch placement 無關。
- **D：** 正確。Queue depth 只表示 demand；scheduler 仍需找到符合 resource requirements 的 capacity。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Jobs stuck in a RUNNABLE status - AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/job_stuck_in_runnable.html)

### 練習題 4｜SAA｜Array jobs、retry 與 timeout

十萬個可獨立處理的 image shards，每 shard 最長 30 分鐘；特定 transient exit code 可重試，bad input 不應重試。最佳配置為何？

A. 使用 array jobs/適當分片，job definition 設 resources、30 分鐘 timeout 與依 exit reason 的 retry；輸入輸出外部化
B. 單一巨大 job fork 十萬 processes，無 checkpoint
C. 用 queue retention 取代 job timeout
D. 所有 exit code 無限重試

**答案：A**

- **A：** 正確。分片隔離 failure，timeout 與 evaluateOnExit 可區分 transient/permanent errors。
- **B：** 錯誤。單一 failure domain 放大重算與資源配置問題。
- **C：** 錯誤。Queue/job retention 與執行 timeout 是不同契約。
- **D：** 錯誤。Permanent bad input 會形成無限成本與 queue starvation。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Array jobs - AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/array_jobs.html)、[Job definitions - AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/job_definitions.html)

### 練習題 5｜SAA｜Spot interruption 的 durable recovery

兩小時 Batch simulation 使用 Spot；即使 application 沒有及時收到或處理最後的 interruption signal，也要避免完全重算。哪個設計合理？

A. 忽略通知，Spot 保證跑完
B. 把工作切成可重試的小單位並定期把 checkpoint 寫入 S3/EFS；設定 retry strategy 與 idempotency，若 runtime 另外傳入 interruption event 或 SIGTERM，再把它當 final-checkpoint 機會
C. 把 checkpoint 只寫 instance store
D. retry attempts 設 0

**答案：B**

- **A：** 錯誤。Spot capacity 可因 EC2 需要容量而被中斷，兩分鐘 notice 也不是作業一定完成的保證；沒有 durable progress 時仍可能重做整段計算。
- **B：** 正確。Periodic durable checkpoint 才是主要 recovery mechanism；notice 或 signal 只是額外最佳化，不能取代小工作單位、retry 與 idempotent output。
- **C：** 錯誤。Instance store 會隨被回收 host 遺失。
- **D：** 錯誤。停用 retry 會讓可恢復 interruption 變永久 failure。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Spot Instance interruption notices - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)、[Automated job retries - AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/job_retries.html)、[AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/bestpractice6.html)

### 練習題 6｜SAP｜Spark/EMR 分層診斷

Spark job 某個 stage 少數 tasks 比其他 tasks 慢 20 倍，executor OOM 與 shuffle read 同時偏高。哪個處理順序最好？

A. 直接把 spark.sql.shuffle.partitions 調到極大值，不先確認少數 straggler 是否來自 data skew
B. 只增加 executor heap，忽略 memoryOverhead、spill、GC 與單一 hot key 造成的 skew
C. 把所有 Spot task nodes 改 On-Demand，並假設 executor loss 是 executor OOM 與 shuffle read 偏高的唯一原因
D. 先看 Spark stage/task logs 判斷 data skew、partition size、shuffle spill、GC 與 memory overhead，再查 executor fleet、Spot loss、S3 layout 與 network

**答案：D**

- **A：** 錯誤。增加 partitions 有時能改善平行度，但遇到 hot key/data skew 時仍會留下極大的單一 partition；應先用 stage 與 task 分布確認原因。
- **B：** 錯誤。提高 heap 可能延後 OOM，卻可能加重 GC；若真正限制在 off-heap memoryOverhead、shuffle spill 或 skew，單調 heap 無法形成可靠修正。
- **C：** 錯誤。Spot interruption 會造成 executor loss，但題目同時有 OOM、shuffle read 與少數 stragglers；未看 Spark event logs 就更換 purchase option 會漏掉資料與記憶體根因。
- **D：** 正確。先在 Spark 層比較 task duration、input/shuffle size、spill、GC 與 executor loss，再下鑽 EMR capacity、S3 layout 和 network，才能區分 data skew 與 infrastructure 問題。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Optimize Spark performance - Amazon EMR](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-performance.html)

### 練習題 7｜SAP｜Transient EMR on EC2 與 EMR Serverless 成本邊界

Spark ETL 每晚只跑兩小時，input/output 在 S3；白天沒有互動需求。哪個成本方向最合理？

A. 保留最大 persistent cluster 全天
B. 把唯一資料留在 HDFS，完成後 terminate
C. 資料留 S3；可選 EMR Serverless 依 job 使用 managed capacity，或用 transient EMR on EC2 並只對可重試的 task/core capacity 評估 diversified Spot
D. 所有 nodes 固定最大 On-Demand instance

**答案：C**

- **A：** 錯誤。全天保留最大 cluster 會支付約 22 小時的 idle EC2/EMR capacity；只有需要低啟動延遲或持續互動工作時，persistent capacity 才可能合理。
- **B：** 錯誤。HDFS 隨 transient cluster 終止而消失；唯一 input/output 必須先落到 S3 等 durable storage，否則節省 idle 成本會換成資料遺失。
- **C：** 正確。兩者都能把 compute 生命週期和 S3 data 分離；Spot 只適用於 EMR on EC2 的 instance fleet/group，EMR Serverless 不讓客戶選 Spot purchase option。
- **D：** 錯誤。未依利用率或 interruption tolerance 優化。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[What is Amazon EMR? - Amazon EMR](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html)、[Amazon EMR](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/what-is-emr-serverless.html)、[Configuring Amazon EMR cluster instance types and best practices for Spot instances - Amazon EMR](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-instances-guidelines.html)

### 練習題 8｜SAA｜Orchestration 與 execution

ETL 要先啟動 EMR Spark job，成功後更新 Glue Catalog，失敗通知，並在重跑前等待人工核准。應由哪個服務保存流程狀態？

A. Step Functions 編排 service integrations、branch/retry/callback；Spark 計算仍由 EMR 執行
B. Step Functions 直接取代 Spark executors
C. EventBridge schedule 自動保存所有補償狀態
D. CloudWatch dashboard 執行人工核准

**答案：A**

- **A：** 正確。State machine 負責控制流，EMR 負責資料處理。
- **B：** 錯誤。Step Functions 不執行 TB 級 distributed compute。
- **C：** 錯誤。Schedule 觸發事件，不等於持久 workflow state。
- **D：** 錯誤。Dashboard 顯示 telemetry，不提供 callback orchestration。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Create and manage Amazon EMR clusters with Step Functions - AWS Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/connect-emr.html)

### 練習題 9｜SAP｜Multi-account data processing platform

中央 data account 保存 S3 lake，多個 workload accounts 提交 jobs；需 least privilege、priority isolation、成本歸屬與 recovery。選擇兩項。

A. 所有 teams 共用 administrator job role
B. 分離 data bucket policy/access role、job role 與 compute role，按 account/queue/tag 建立隔離與 cost allocation
C. 中間與結果只放 instance store
D. Output/checkpoint 寫 durable storage，保存 job/audit metadata並測試跨帳號 recovery
E. 所有 jobs 使用單一 queue 且不設 quota/priority

**答案：B、D**

- **A：** 錯誤。共享 admin identity 無法限制資料與追蹤 owner。
- **B：** 正確。Identity 與 queue boundaries 同時控制資料權限、資源競爭與成本。
- **C：** 錯誤。Compute termination 會失去唯一 state。
- **D：** 正確。Durable artifacts 與 audit trail 讓失敗可重跑且責任可追。
- **E：** 錯誤。所有 accounts 共用單一無 quota/priority 的 queue，會讓大量低優先工作占用 capacity，無法提供 workload isolation、關鍵工作優先或清楚的成本歸屬。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Job queues - AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/job_queues.html)、[Example 2: Bucket owner granting cross-account bucket permissions - Amazon Simple Storage Service](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-walkthroughs-managing-access-example2.html)

### 練習題 10｜SAP｜Interruption-tolerant Spot batch fleet

百萬個可重試 jobs 要降低成本，且單一 Spot pool 缺貨時仍要前進。選擇兩項。

A. 固定單一最低價 Spot type/AZ
B. 建立 diversified SPOT compute environment 與獨立 EC2 On-Demand compute environment，兩者關聯到 job queue 並設定 order；同時驗證 quota、priority 與 deadline 所需容量
C. Queue 與結果都放 instance store
D. 關閉 retry
E. Jobs 小批次、idempotent，進度寫 durable checkpoint，使中斷只重做有限工作

**答案：B、E**

- **A：** 錯誤。單一 pool 是 shortage/interruption 單點。
- **B：** 正確。SPOT 與 EC2 是兩個 compute environments，不是同一個 Spot 開關；多樣化 Spot 先降成本，獨立 On-Demand environment 才能在可用容量與排程條件允許時承接 deadline-sensitive jobs。
- **C：** 錯誤。Instance store 與執行節點生命週期綁定；Spot 回收時若 queue metadata、output 或 checkpoint 只在本機，scheduler 即使 retry 也沒有可恢復狀態。
- **D：** 錯誤。Retry strategy 是中斷後重新排程的必要部分；關閉 retry 會把暫時性 Spot loss 直接轉成 FAILED，無法利用其他 pool 或 On-Demand environment。
- **E：** 正確。小批次與 idempotent output 限制每次中斷的重做範圍，durable checkpoint 讓任何新 capacity 都可續跑，而不是依賴被回收節點的最後通知。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Use allocation strategies to determine how EC2 Fleet or Spot Fleet fulfills Spot and On-Demand capacity - Amazon Elastic Compute Cloud](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-fleet-allocation-strategy.html)、[AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/bestpractice.html)、[AWS Batch](https://docs.aws.amazon.com/batch/latest/userguide/job_queue_compute_environments.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「一般container batch用AWS Batch；大數據Spark/Hadoop用EMR；平行HPC…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「離線工作需要queue、scheduler、依賴、重試與可中斷容量管理。」，所以「一般container batch用AWS Batch；大數據Spark/Hadoop用EMR；平行HPC可搭Spot與placement。」能直接滿足它；若constraint改成「Step Functions可協調多階段工作，但不是高吞吐資料處理引擎。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「一般container batch用AWS Batch；大數據Spark/Hadoop用EMR；平行HPC可搭Spot與placement。」。替代方案「Step Functions可協調多階段工作，但不是高吞吐資料處理引擎。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「將大量短工作各自啟動完整cluster，或Spot interruption沒有checkpoint。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「離線工作需要queue、scheduler、依賴、重試與可中斷容量管理。」，排除會導致「將大量短工作各自啟動完整cluster，或Spot interruption沒有checkpoint。」的選項，再選「一般container batch用AWS Batch；大數據Spark/Hadoop用EMR；平行HPC可搭Spot與placement。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions；SAP-2.5 Design a solution to meet performance objectives。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「一般container batch用AWS Batch；大數據Spark/Hadoop用EMR；平行HPC可搭Spot與placement。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「separate orchestration from execution engines」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。

# 第 40 章　Elastic Beanstalk、App Runner 與 Managed Platforms

團隊想快速部署web application，但需要不同程度的VPC、runtime與deployment控制。

## 跟著一份工作走：先從故事開始

先暫時忘掉AWS服務名稱，只看眼前發生的事：小團隊要部署標準Python web app，無意管理cluster，但需autoscaling與TLS。 這種題目難的地方不在縮寫，而在同一句話同時牽動好幾層系統。接下來先跟著事情發生的順序走，等路徑清楚後再把服務名稱放回去。

現在把需求往下挖一層，真正的壓力是：團隊想快速部署web application，但需要不同程度的VPC、runtime與deployment控制。 只要這件事沒有回答，再漂亮的架構圖也只是把不確定性藏在更多方框後面。 先把這個因果關係站穩，後面的技術細節才會彼此連得起來。

為了讓腦中先有畫面，把運算平台想成餐廳廚房：訂單怎麼進來、由誰處理、忙起來如何加人、失敗如何補做。 類比只用來建立第一張心智地圖；真正做決策時仍要回到本章原則：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。 等一下看到AWS名詞時，請把它貼回這個故事，而不是另外開一張互不相干的記憶卡。

接下來的閱讀順序很簡單：先看AWS Elastic Beanstalk如何接手工作，再看AWS App Runner何時更合適，最後用設定與考題驗證「Beanstalk管理常見EC2 stack；App Runner從source/image提供更高抽象的web service。」是否真的能從需求一路推導出來。

## 先看全圖：這件事在系統裡怎麼發生？

```text
場景：小團隊要部署標準Python web app，無意管理cluster，但需autoscaling與TLS。

request／event／batch job抵達
          │ ① admission與工作規格
          ▼
[AWS Elastic Beanstalk]
          │ 從application package建立並管理EC2、ASG、ELB等web環境。
          │ ② scheduler／load balancer選擇runtime並執行
          │ ③ 讀寫外部state；runtime本身應可替換
          ▼
[database／queue／object storage]
容量迴路：demand signal → scale → warm up → health → drain
本章其他角色：
  · AWS App Runner：從source或container image快速提供managed web service。
  · Amazon Lightsail：以固定月費bundle簡化小型VM、database、container與network部署。

失敗時先找：使用高階平台卻需要未暴露的host控制，最後以脆弱hook繞過抽象。
證明完成：使用者結果 + latency/error + audit/log + recovery test
```

## 先懂原理，再把 AWS 名稱放回來

如果只記得一件事，請記得「跟著一份工作走」。先不要急著問AWS Elastic Beanstalk有多少功能，而是沿著故事裡的一次請求、資料變更或故障往前走。每到一站，都問：上一站交給它什麼，它替系統保留了什麼狀態，下一站又依賴它提供什麼。

這樣看就會發現，AWS Elastic Beanstalk和AWS App Runner並不是兩個任意的產品名稱。前者適合本章，是因為「Beanstalk管理常見EC2 stack；App Runner從source/image提供更高抽象的web service。」直接回應了眼前的問題；後者描述的「Lightsail適合簡單小型應用；完整微服務平台則考慮ECS/EKS。」只有在需求改變時才會變成更好的答案。考試喜歡把兩者放在一起，實務上也常因為沒有說清楚需求而選錯。

最後再從失敗方向倒著走一次：使用高階平台卻需要未暴露的host控制，最後以脆弱hook繞過抽象。 如果真的發生，哪個訊號會先變壞，哪一層能隔離影響，又要靠什麼證據確認已恢復？這就是本章的可移植原則——「managed platforms trade control for delivery speed」。更白話地說：先找真正的容量瓶頸與工作生命週期，再選VM、container、function或managed platform。

## 每個 Component 在哪一站接手？

| Component | 負責什麼 | 底層怎麼運作 |
| --- | --- | --- |
| AWS Elastic Beanstalk | 從application package建立並管理EC2、ASG、ELB等web環境。 | Platform version與configuration options產生底層CloudFormation resources並執行deployment policies。 |
| AWS App Runner | 從source或container image快速提供managed web service。 | Service建立build/deploy與autoscaling runtime，透過public endpoint接HTTP requests。 |
| Amazon Lightsail | 以固定月費bundle簡化小型VM、database、container與network部署。 | 把compute、SSD、transfer與簡化控制面包成套餐，降低初學與小workload操作。 |

## 把全圖套進一個具體案例

**場景：** 小團隊要部署標準Python web app，無意管理cluster，但需autoscaling與TLS。

1. 故事的起點：小團隊要部署標準Python web app，無意管理cluster，但需autoscaling與TLS。 先寫下使用者真正等待的結果，不要先寫服務名稱。
2. 第一個交接：AWS Elastic Beanstalk負責「從application package建立並管理EC2、ASG、ELB等web環境。」；確認誰呼叫它、輸入是什麼，以及它是否保存狀態。
3. 系統真正做事時：Platform version與configuration options產生底層CloudFormation resources並執行deployment policies。 沿著這條路徑標出一次request、packet、message或data write。
4. 其他角色接手：AWS App Runner、Amazon Lightsail各自只完成部分責任；把identity、network、data與recovery owner寫在箭頭旁。
5. 故障時倒著追：主動重現「使用高階平台卻需要未暴露的host控制，最後以脆弱hook繞過抽象。」，從使用者症狀一路找到第一個錯誤訊號，而不是看到timeout就盲目重試。
6. 需求改變時重選：一旦出現「container-first可用ECS/App Runner；event-driven短函式用Lambda。」，原方案可能已不合適；這是答案翻轉點，不是設定調得更多就一定能解決。
7. 最後驗收：用成功率、p95/p99、資料正確性、RTO/RPO、audit evidence與單位成本證明故事真的有好結局。

## 需要時再查：四個閱讀支點

### AWS Elastic Beanstalk

- **白話定義：** 本章主要mechanism或服務。它存在是為了解決：團隊想快速部署web application，但需要不同程度的VPC、runtime與deployment控制。
- **具體例子／邊界：** 在「小團隊要部署標準Python web app，無意管理cluster，但需autoscaling與TLS。」中，先確認它是否真的滿足需求，而不是看到名稱便直接選。

### AWS App Runner

- **白話定義：** 用來比較邊界的相鄰選項。它在不同constraint下可能合理：Lightsail適合簡單小型應用；完整微服務平台則考慮ECS/EKS。
- **具體例子／邊界：** 考試常把相鄰服務放在同一題；差異通常藏在protocol、state、failure domain或營運責任。

### Failure boundary

- **白話定義：** 元件失效、過載或設定錯誤時，影響停止在哪裡。本章已知風險是：使用高階平台卻需要未暴露的host控制，最後以脆弱hook繞過抽象。
- **具體例子／邊界：** 看到highly available、fault tolerant或least operational overhead時，要明確指出邊界。

### Portable pattern

- **白話定義：** 不依賴AWS品牌仍成立的原則：managed platforms trade control for delivery speed。
- **具體例子／邊界：** 換成其他雲端或自建系統時，服務名稱會變，但需求、state、flow與trade-off仍存在。

## 本章新名詞字典

### CloudFormation

AWS IaC服務，將template中的Resources與properties轉成stack並管理create/update/delete生命週期。

### health check

系統主動探測target是否能服務；好的check接近使用者成功，但不應過度依賴所有下游。

### workload

共同提供一個business outcome的application、資料、基礎設施、people與operations集合，不等於單一EC2或單一service。

### policy

以statements描述Effect、Action、Resource、Principal與Condition的授權規則。

### event

描述已發生事實的資料；event router依pattern送往targets，但consumer仍需處理duplicate與失敗。

### stack

CloudFormation以一個生命週期單位管理的一組resources；更新與刪除行為受dependencies及policies影響。

### HTTP

Web request/response協定，包含method、path、headers與body；ALB、API Gateway、CloudFront可理解其L7語意。

### role

可被可信principal暫時扮演的AWS identity；trust policy管誰能扮演，permissions管扮演後能做什麼。

### TLS

在transport上提供加密、完整性與server/client身份驗證；certificate把public key綁到domain identity。

## 回到 AWS：Components、功用與責任邊界

### AWS Elastic Beanstalk

- **功用：** 從application package建立並管理EC2、ASG、ELB等web環境。
- **底層機制：** Platform version與configuration options產生底層CloudFormation resources並執行deployment policies。
- **關鍵設定：** platform、environment tier、instance/ASG、LB、deployment policy、.ebextensions與saved configuration。
- **選擇時機：** 開發團隊要快速部署傳統web app，但仍想保留底層resource控制。
- **替換時機：** container-first可用ECS/App Runner；event-driven短函式用Lambda。

### AWS App Runner

- **功用：** 從source或container image快速提供managed web service。
- **底層機制：** Service建立build/deploy與autoscaling runtime，透過public endpoint接HTTP requests。
- **關鍵設定：** source/image、build/start command、CPU/memory、autoscaling、health check、instance role與VPC connector。
- **選擇時機：** 小團隊快速上線stateless web/API且不想管理orchestrator。
- **替換時機：** 複雜network、sidecars、GPU或平台標準化需求選ECS/EKS；應確認新workload的服務可用與產品路線。

### Amazon Lightsail

- **功用：** 以固定月費bundle簡化小型VM、database、container與network部署。
- **底層機制：** 把compute、SSD、transfer與簡化控制面包成套餐，降低初學與小workload操作。
- **關鍵設定：** blueprint/bundle、static IP、firewall、snapshot、load balancer與managed database。
- **選擇時機：** 小網站、prototype與可預測低複雜度workload。
- **替換時機：** 需要完整VPC、enterprise governance、細粒度autoscaling或進階服務整合時改用EC2/ECS等。

## 考前與實作時再查：設定操作手冊

### AWS Elastic Beanstalk：逐項設定說明

#### `platform`

- **控制什麼：** `platform`選擇執行引擎、版本或runtime行為，決定相容性、patch責任與可用功能。
- **何時需要：** 當需求符合「開發團隊要快速部署傳統web app，但仍想保留底層resource控制。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Beanstalk鎖定經測試的版本與parameters，建立upgrade/deprecation inventory，先在staging跑compatibility與rollback測試。
- **常見錯法：** 使用latest而沒有版本策略會產生不可預期升級；長期不升級則累積漏洞、unsupported版本與阻塞migration。

#### `environment tier`

- **控制什麼：** `environment tier`選擇AWS Elastic Beanstalk的運行或管理模式，通常改變capacity、features、latency、pricing與customer responsibility。
- **何時需要：** 先依流量穩定度、相容性、控制需求與營運能力決定模式，再比較價格。
- **怎麼設定／驗證：** 建立decision table列出各mode的hard limits與billing unit，在代表性load下測試；不可原地轉換時規劃parallel migration。
- **常見錯法：** 把serverless當無限capacity、或把managed當零設定，會在quota、cold start與feature gap上失敗。

#### `instance/ASG`

- **控制什麼：** `instance/ASG`設定AWS Elastic Beanstalk的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「開發團隊要快速部署傳統web app，但仍想保留底層resource控制。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `LB`

- **控制什麼：** `LB`決定workload如何取得network identity或接入load-balancing/service path。
- **何時需要：** Container、endpoint或application需要穩定入口、獨立ENI/IP或跨network consumer時。
- **怎麼設定／驗證：** 明確選擇network mode、target type、subnets與SG，建立health check及DNS；從client到target逐跳驗證。
- **常見錯法：** 有load balancer不代表target健康；network mode與target type不相容會無法註冊或無法回程。

#### `deployment policy`

- **控制什麼：** `deployment policy`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「開發團隊要快速部署傳統web app，但仍想保留底層resource控制。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS Elastic Beanstalk明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `.ebextensions`

- **控制什麼：** `.ebextensions`是可版本化的啟動或工作規格，定義AWS Elastic Beanstalk建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `saved configuration`

- **控制什麼：** `saved configuration`是一組可版本化的engine/runtime參數，會改變AWS Elastic Beanstalk的實際process行為。
- **何時需要：** 當需求符合「開發團隊要快速部署傳統web app，但仍想保留底層resource控制。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 複製default group建立custom group，只修改有明確需求的值；確認dynamic或pending-reboot屬性，先在staging量測再綁到resource。
- **常見錯法：** 一次修改大量參數會失去因果關係；需要reboot的值不會立即生效，不同engine/version也可能不支援同名參數。

### AWS App Runner：逐項設定說明

#### `source/image`

- **控制什麼：** `source/image`指定AWS App Runner讀取、處理或寫入的resource boundary，決定data path與所需IAM/network permissions。
- **何時需要：** 服務要跨bucket、database、VPC、account或Region移動或處理資料時。
- **怎麼設定／驗證：** 使用具體ARN/endpoint/location與least-privilege role，分別測試source read、target write、KMS與network path；記錄format/schema。
- **常見錯法：** 只授權service role卻漏掉source/target resource policy或KMS key policy，常表現為AccessDenied或job卡住。

#### `build/start command`

- **控制什麼：** `build/start command`定義AWS App Runner要執行的功能、命令或批次單位，是application behavior與release contract。
- **何時需要：** 同一artifact要依環境切換功能、建立可重複run流程或平行處理大量相似jobs時。
- **怎麼設定／驗證：** 版本化command/flag schema，設定validation/default與修改權限；以canary和明確rollback條件推出。
- **常見錯法：** 沒有owner/expiry的feature flag會永久累積；command、preset或array index不驗證會大規模重複失敗。

#### `CPU/memory`

- **控制什麼：** `CPU/memory`設定AWS App Runner的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「小團隊快速上線stateless web/API且不想管理orchestrator。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `autoscaling`

- **控制什麼：** `autoscaling`設定AWS App Runner的單位容量、平行度或擴縮邊界，直接影響latency、quota與cost。
- **何時需要：** 當需求符合「小團隊快速上線stateless web/API且不想管理orchestrator。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 先用arrival rate、service time、資料量與p95/p99建立基線，再設定min/max、target metric或provisioned capacity；保留quota與warm-up headroom。
- **常見錯法：** 只提高上限不保護downstream會把瓶頸推給database/API；只看平均值會漏掉burst、hot partition與cold-start capacity。

#### `health check`

- **控制什麼：** `health check`定義系統如何判斷可服務、何時隔離故障，以及如何證明恢復路徑有效。
- **何時需要：** 當需求符合「小團隊快速上線stateless web/API且不想管理orchestrator。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS App Runner設定代表使用者成功的probe/alarm、threshold與action；定期執行failure test並記錄偵測、切換及恢復時間。
- **常見錯法：** 只看resource running或CPU正常會產生假健康；health dependency過深也可能讓局部故障把所有targets同時摘除。

#### `instance role`

- **控制什麼：** `instance role`控制誰可以取得身份或對哪些resources執行哪些actions，是authorization boundary的一部分。
- **何時需要：** 當需求符合「小團隊快速上線stateless web/API且不想管理orchestrator。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在AWS App Runner明確寫出principal、Action、Resource與Condition，優先temporary credentials與group/role assignment；以實際caller identity做正反測試。
- **常見錯法：** 使用Administrator或萬用字元能讓測試暫時成功，卻隱藏trust、resource ARN與condition錯誤；explicit Deny仍會覆蓋Allow。

#### `VPC connector`

- **控制什麼：** `VPC connector`把AWS App Runner與外部service或自動化步驟連接，決定event/data/failure如何跨component傳遞。
- **何時需要：** Resource狀態改變後需要觸發轉換、修復、通知、驗證或後續workflow時。
- **怎麼設定／驗證：** 定義input/output schema、execution role、timeout/retry/DLQ與idempotency；以失敗event驗證不會無限retry或重複side effect。
- **常見錯法：** Integration建立成功不代表target有權執行；缺少DLQ、schema version與idempotency會把暫時故障變成資料錯誤。

### Amazon Lightsail：逐項設定說明

#### `blueprint/bundle`

- **控制什麼：** `blueprint/bundle`是可版本化的啟動或工作規格，定義Amazon Lightsail建立runtime時使用的image、commands、roles、capacity與network。
- **何時需要：** 同一workload要可重建、rolling update，或由autoscaling/orchestrator重複啟動時。
- **怎麼設定／驗證：** 把規格放入版本控制，鎖定image/version並分離secret；建立新version後canary/rolling更新，保留可rollback版本。
- **常見錯法：** 直接修改running resource會造成drift；把長期credentials寫入user data、image或job definition也會洩漏。

#### `static IP`

- **控制什麼：** `static IP`決定workload如何取得network identity或接入load-balancing/service path。
- **何時需要：** Container、endpoint或application需要穩定入口、獨立ENI/IP或跨network consumer時。
- **怎麼設定／驗證：** 明確選擇network mode、target type、subnets與SG，建立health check及DNS；從client到target逐跳驗證。
- **常見錯法：** 有load balancer不代表target健康；network mode與target type不相容會無法註冊或無法回程。

#### `firewall`

- **控制什麼：** `firewall`限制network exposure或inspection邊界，回答哪些來源能以哪些protocol/ports到達哪些目標。
- **何時需要：** 當需求符合「小網站、prototype與可預測低複雜度workload。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Lightsail中以最小CIDR、SG reference、rule group或endpoint scope設定；先Count/observe，再逐步enforce並保存logs。
- **常見錯法：** Network allow只證明可達，不代表principal有IAM權限；過寬0.0.0.0/0與錯誤return path會擴大攻擊面或造成timeout。

#### `snapshot`

- **控制什麼：** `snapshot`控制副本、版本、備份或資料生命週期，用來滿足durability、RPO、RTO與retention。
- **何時需要：** 當需求符合「小網站、prototype與可預測低複雜度workload。」時，這個欄位是部署前review的一部分。
- **怎麼設定／驗證：** 在Amazon Lightsail依每一份authoritative state設定copy destination、frequency、retention、encryption與restore owner，並實際演練restore/failover。
- **常見錯法：** 有副本不等於有可恢復備份；錯誤與刪除也可能被複寫。沒有restore test、key與dependency順序就不能宣稱達成RTO/RPO。

#### `load balancer`

- **控制什麼：** `load balancer`決定workload如何取得network identity或接入load-balancing/service path。
- **何時需要：** Container、endpoint或application需要穩定入口、獨立ENI/IP或跨network consumer時。
- **怎麼設定／驗證：** 明確選擇network mode、target type、subnets與SG，建立health check及DNS；從client到target逐跳驗證。
- **常見錯法：** 有load balancer不代表target健康；network mode與target type不相容會無法註冊或無法回程。

#### `managed database`

- **控制什麼：** `managed database`選擇資料/目錄service的availability、分片、節點休眠或managed integration模式。
- **何時需要：** 需要在成本與AZ/Region容錯、scale、Windows domain整合或閒置資源間做取捨時。
- **怎麼設定／驗證：** 明確選擇deployment/cluster/AD mode與AZs，設定failover/replica或auto-pause條件；以dependency failure與喚醒延遲測試。
- **常見錯法：** One Zone不適合不能接受AZ資料損失的state；auto-pause會增加首次連線延遲，目錄分享也仍需DNS/trust/network。

## 讀到這裡，請用自己的話說一次

1. AWS Elastic Beanstalk的責任：從application package建立並管理EC2、ASG、ELB等web環境。
2. 底層機制：Platform version與configuration options產生底層CloudFormation resources並執行deployment policies。
3. 第一個要看的設定：platform、environment tier、instance/ASG、LB、deployment policy、.ebextensions與saved configuration。
4. 選擇邏輯：Beanstalk管理常見EC2 stack；App Runner從source/image提供更高抽象的web service。
5. 不要混淆：AWS App Runner的責任是「從source或container image快速提供managed web service。」；它不會自動取代AWS Elastic Beanstalk。
6. 替換訊號：container-first可用ECS/App Runner；event-driven短函式用Lambda。
7. 最常見錯法：使用高階平台卻需要未暴露的host控制，最後以脆弱hook繞過抽象。
8. 可移植原則：managed platforms trade control for delivery speed。

## Service Decision Matrix

| Component | 負責什麼 | 底層機制 | 選擇時機 | 替換／避免 |
| --- | --- | --- | --- | --- |
| AWS Elastic Beanstalk | 從application package建立並管理EC2、ASG、ELB等web環境。 | Platform version與configuration options產生底層CloudFormation resources並執行deployment policies。 | 開發團隊要快速部署傳統web app，但仍想保留底層resource控制。 | container-first可用ECS/App Runner；event-driven短函式用Lambda。 |
| AWS App Runner | 從source或container image快速提供managed web service。 | Service建立build/deploy與autoscaling runtime，透過public endpoint接HTTP requests。 | 小團隊快速上線stateless web/API且不想管理orchestrator。 | 複雜network、sidecars、GPU或平台標準化需求選ECS/EKS；應確認新workload的服務可用與產品路線。 |
| Amazon Lightsail | 以固定月費bundle簡化小型VM、database、container與network部署。 | 把compute、SSD、transfer與簡化控制面包成套餐，降低初學與小workload操作。 | 小網站、prototype與可預測低複雜度workload。 | 需要完整VPC、enterprise governance、細粒度autoscaling或進階服務整合時改用EC2/ECS等。 |
| 本章反例 | 看似可以工作，但沒有滿足題目真正的hard constraint。 | Lightsail適合簡單小型應用；完整微服務平台則考慮ECS/EKS。 | 只有當題目條件明確改變時才可能合理。 | 使用高階平台卻需要未暴露的host控制，最後以脆弱hook繞過抽象。 |

## SAA 與 SAP 範圍

### SAA 必會

- 能用一句話說出服務功能、scope與managed responsibility。
- 能根據單一workload限制，在主要方案與「Lightsail適合簡單小型應用；完整微服務平台則考慮ECS/EKS。」之間做選擇。
- 認得常考設定：platform、environment tier、instance/ASG、LB、deployment policy、.ebextensions與saved configuration。
- 對應官方tasks：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions。

### SAP 加深

- 把單服務答案擴成跨帳號、跨Region、migration與operating model。
- 明確描述delegated ownership、blast radius、rollout/rollback、evidence與長期成本。
- 知道何時要替換或組合：container-first可用ECS/App Runner；event-driven短函式用Lambda。
- 對應官方tasks：SAP-2.1 Design a deployment strategy to meet business requirements；SAP-2.5 Design a solution to meet performance objectives；SAP-2.6 Determine a cost optimization strategy to meet solution goals；SAP-4.4 Determine opportunities for modernization and enhancements。

## 本章 10 題考題

### 練習題 1｜SAA｜Beanstalk、ECS Express Mode 與 Lightsail 選型

三個新 workload：需控制底層 EC2/ASG/ALB 設定的傳統 Java app；從 ECR 快速上線且希望 AWS 管理 HTTPS、負載平衡與 autoscaling 的 stateless container API；固定預算的單一小網站。哪個對應合理？

A. 全部使用 ECS on EC2，因每種 workload 都必須由團隊管理 hosts
B. Java app 用 Elastic Beanstalk；container API 評估 ECS Express Mode；小型簡化網站可評估 Lightsail
C. 全部 Lightsail
D. Beanstalk 不使用 EC2，不能調 instance

**答案：B**

- **A：** 錯誤。ECS on EC2 可以提供 host control，但會把 cluster capacity、patching 與 placement 責任帶給三個團隊；固定小站與簡單 web container 沒有此必要。
- **B：** 正確。Beanstalk 暴露並管理 EC2/ASG/ELB environment；ECS Express Mode 為新 container web app 建立受管 Fargate、HTTPS、負載平衡與 autoscaling；Lightsail 提供簡化 bundle。
- **C：** 錯誤。Lightsail 適合簡化且邊界明確的 workload，不是需要精細 ASG/ALB 控制或 managed container autoscaling 的共同平台。
- **D：** 錯誤。Elastic Beanstalk 的 load-balanced environment 會建立 EC2、Auto Scaling 與 load balancer；使用者仍可透過 environment options 調整 instance 與部署設定。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Understanding concepts in Elastic Beanstalk - AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts.html)、[Amazon ECS Express Mode - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html)、[What is Amazon Lightsail? - Amazon Lightsail](https://docs.aws.amazon.com/lightsail/latest/userguide/what-is-amazon-lightsail.html)

### 練習題 2｜SAA｜[延伸：既有客戶] App Runner control plane 與 request path

此題只適用於 2026-04-30 前已成為 App Runner 客戶的既有帳號；App Runner 已不接受新客戶。新進工程師把 Elastic Beanstalk 說成逐 request 執行程式的 runtime，也把 App Runner VPC connector 說成 public ingress。哪個敘述正確？

A. Beanstalk 自己逐 request 執行 Python handler
B. Beanstalk environment config 建立/更新 EC2、ASG、LB，request 仍經 LB 到 instances；App Runner 提供 managed endpoint/runtime
C. App Runner VPC connector 是 public inbound load balancer
D. Lightsail blueprint 每 request 重新編譯 app

**答案：B**

- **A：** 錯誤。Beanstalk 是 application deployment 與 environment control plane；實際 request 由 environment 中的 proxy/load balancer 與 EC2 application processes 處理，不是逐次啟動 handler。
- **B：** 正確。Beanstalk 管理可見的 EC2/ASG/LB environment；既有 App Runner service 則暴露 managed endpoint/runtime。兩者的 control plane 都不等同 application data path。
- **C：** 錯誤。App Runner VPC connector 把既有 service 的 outgoing traffic 送入指定 VPC subnets；它不是 public ingress load balancer，也不會把 service endpoint 變成私有入口。
- **D：** 錯誤。Lightsail blueprint 是建立 instance/application stack 的範本；request 到達後由已執行的 web server 處理，不會為每個 request 重新編譯程式。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Understanding concepts in Elastic Beanstalk - AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts.html)、[App Runner architecture and concepts - AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/architecture.html)、[What is AWS App Runner? - AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html)

### 練習題 3｜SAA｜[延伸：既有客戶] App Runner concurrency scaling

此題只適用於 2026-04-30 前已成為 App Runner 客戶的既有帳號。既有 service 在每個 instance 同時處理超過 60 requests 後 p95 急劇惡化。應如何設定 autoscaling？

A. 把 MaxConcurrency 提高到 200，讓每個 instance 盡量吃滿；不改 MinSize/MaxSize，也不重測 latency
B. 把 MinSize 設為尖峰所需容量，但 MaxConcurrency 與 MaxSize 保持預設，因預熱容量會自動修正所有 contention
C. 把 MaxConcurrency 設在實測安全值附近，依 steady/peak demand 設 MinSize 與 MaxSize，並以 p95、active instances 與 throttling 重測 headroom
D. 只降低 MaxSize 來限制費用，並維持 MaxConcurrency 高於已知 latency 崩壞點

**答案：C**

- **A：** 錯誤。MaxConcurrency 是觸發擴張前單一 instance 可承接的同時請求數；設在已知崩壞點之上會讓 latency 先惡化才 scale out。
- **B：** 錯誤。MinSize 可保留 provisioned instances 並降低啟動等待，但若 MaxConcurrency/MaxSize 與 workload 不合，尖峰仍會在單機 contention 或容量上限失敗。
- **C：** 正確。三個參數分別控制 scale-out threshold、最低預留容量與最大 fleet；安全值應來自 load test 與 SLO，而不是只追求單機利用率。
- **D：** 錯誤。降低 MaxSize 會收緊總容量；若 MaxConcurrency 又高於安全值，service 既延遲惡化又更早碰到 fleet ceiling，不能形成可靠成本控制。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Managing App Runner automatic scaling - AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/manage-autoscaling.html)、[What is AWS App Runner? - AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html)

### 練習題 4｜SAP｜Beanstalk deployment policy

Production 更新時必須維持完整 capacity，並在新版本 health 異常時快速 rollback。哪個策略最貼合？

A. 使用 immutable 或 traffic-splitting deployment 建新 capacity 驗證後替換；保留前版
B. All at once 永遠最適合 zero downtime
C. .ebextensions 可取代版本與 rollback
D. Single-instance environment 等同 Multi-AZ HA

**答案：A**

- **A：** 正確。新 capacity/漸進 traffic 限制 rollout impact，舊版本可供回復。
- **B：** 錯誤。All at once 會讓整個 environment 同時更新。
- **C：** 錯誤。Configuration hooks 不提供完整 release isolation。
- **D：** 錯誤。單 instance 無法抵抗 instance/AZ loss。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Deployment policies and settings - AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.rolling-version-deploy.html)

### 練習題 5｜SAP｜Elastic Beanstalk application-aware health

Elastic Beanstalk 新版本 process 已啟動，但 /orders 連 database 失敗；environment 只依基礎 process/port 狀態判斷，因此仍切入流量。應如何改善？

A. Health endpoint 固定回 200
B. 只看 build success
C. 立即刪舊 environment 再測
D. 配置反映關鍵 dependency/readiness 的 health path、startup grace 與 deployment threshold，舊 instances 終止前 graceful drain

**答案：D**

- **A：** 錯誤。固定回 200 的 endpoint 只證明 process 能回應，會隱藏 database、queue 或必要 downstream 已失效，讓 load balancer 繼續導入必然失敗的 requests。
- **B：** 錯誤。Artifact build success 是 control-plane evidence；它沒有穿過 load balancer、application route、network、credentials 與 database，因此不能代表 production readiness。
- **C：** 錯誤。先刪舊 environment 會移除 healthy capacity 與 rollback target；應先讓新版本通過實際 health threshold，再依 deployment policy 漸進替換。
- **D：** 正確。將 health URL 指向能反映必要依賴的 readiness path，配合 deployment threshold、grace 與 connection draining，才能控制新舊 instances 的流量交接。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Enhanced health reporting and monitoring in Elastic Beanstalk - AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/health-enhanced.html)、[Health checks for Application Load Balancer target groups - Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)

### 練習題 6｜SAP｜[延伸：既有客戶] App Runner VPC connector outbound

此題只適用於 2026-04-30 前已成為 App Runner 客戶的既有帳號。既有 service 加 VPC connector 後可連 private RDS，但呼叫 public package/API endpoint 開始 timeout。最可能缺少什麼？

A. 更低 public DNS TTL
B. 更高 App Runner max instances
C. Custom domain certificate
D. 所選 private subnets 的 NAT，或對依賴服務配置 VPC endpoints/routes/SG；connector 不是 inbound private endpoint

**答案：D**

- **A：** 錯誤。Name resolution 不是題目所示的主要 egress path 缺口。
- **B：** 錯誤。增加 instances 會複製相同 network failure。
- **C：** 錯誤。Custom domain 管理 inbound HTTPS 名稱。
- **D：** 正確。Connector 將 outbound 送入 VPC，後續仍需有效 egress 或 private service path。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Enabling VPC access for outgoing traffic - AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html)、[What is AWS App Runner? - AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html)

### 練習題 7｜SAP｜Managed container abstraction 的總成本

某 container service 全天高利用率且需要 sidecars、精細 rollout 與穩定的 baseline capacity；目前的高階 web abstraction 需要多個 workaround，單位成本與營運風險都高於預期。該如何評估？

A. Managed 程度越高 compute 必然越便宜
B. Lightsail bundle 可無限擴展且不增費
C. 比較 active/provisioned compute、利用率、功能落差與營運人力；若持續超出簡化 web-service abstraction，評估 ECS on Fargate 或 ECS on EC2
D. Beanstalk 不收服務費，所以底層 EC2/ALB 也免費

**答案：C**

- **A：** 錯誤。高階 abstraction 可減少 cluster 與 load balancer 操作，但不保證 compute 單價最低；持續高利用率與 feature workaround 可能讓平台 premium 超過人力節省。
- **B：** 錯誤。Lightsail bundle 有固定的 CPU、memory、transfer 與擴展邊界；它適合簡化 workload，不能假設 sidecars、複雜 rollout 與流量成長都不增加費用。
- **C：** 正確。TCO 要同時計算 steady-state utilization、discount、platform labor、feature fit 與 failure recovery；ECS Fargate 和 EC2 capacity providers 提供不同的操作/成本邊界。
- **D：** 錯誤。Elastic Beanstalk 本身不另收服務費，不代表 environment 建立的 EC2、load balancer、database、data transfer 與 monitoring resources 免費。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Automatically manage Amazon ECS capacity with cluster auto scaling - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-auto-scaling.html)、[Understanding concepts in Elastic Beanstalk - AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts.html)

### 練習題 8｜SAA｜新客戶的 smallest sufficient managed container platform

新 AWS 客戶要從 ECR 部署單一 stateless container API，需要 AWS 管理 HTTPS、負載平衡、Fargate capacity 與 autoscaling，沒有 Kubernetes、sidecar 或 host requirement。哪個選項最直接符合？

A. Amazon ECS Express Mode
B. 標準 ECS service on Fargate，手動設計 ALB、listener、target group、autoscaling 與 deployment circuit breaker
C. Elastic Beanstalk Docker platform，並接受其 environment 與 deployment model
D. Amazon EKS Auto Mode，因未來可能需要 Kubernetes

**答案：A**

- **A：** 正確。ECS Express Mode 是目前可供新客戶使用的 web-oriented ECS 路徑，會建立 Fargate service、HTTPS endpoint、load balancing 與 autoscaling，符合題目的最少平台管理限制。
- **B：** 錯誤但在需要精細網路、listener rules、capacity provider 或 deployment control 時會成為合理選擇；本題明確要求最少設定，因此 Express Mode 更貼合。
- **C：** 錯誤但傳統 application platform 或需要 Beanstalk deployment policies 時可用；本題是單一 ECR container API，ECS Express Mode 的 managed container contract 更直接。
- **D：** 錯誤。EKS Auto Mode 仍引入 Kubernetes API、workload manifests 與 cluster governance；只有確定需要 Kubernetes ecosystem 時，這些額外責任才有回報。

**事實查證：** [AWS Certified Solutions Architect - Associate (SAA-C03) - AWS Certified Solutions Architect - Associate](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)、[Amazon ECS Express Mode - Amazon Elastic Container Service](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html)

### 練習題 9｜SAP｜Beanstalk escape hatch 與 modernization

Beanstalk monolith 已拆成多個需獨立 scaling 的 services，還需要 service discovery、sidecars 與複雜 rollout。選擇兩項。

A. 無限增加 .ebextensions shell hooks
B. 先外部化 state、盤點依賴與 SLO，使用 strangler/waves 將適合部分遷到 ECS/EKS
C. 把所有 services 重新塞入單一 process
D. 保留可回切的 Beanstalk route/artifact，逐服務驗證 traffic、data compatibility 與 rollback
E. 直接全部改 Lambda，不評估 timeout/state

**答案：B、D**

- **A：** 錯誤。大量 escape hooks 表示 abstraction mismatch，並增加不可測 drift。
- **B：** 正確。逐步遷移保留業務連續性，orchestrator 承接新需求。
- **C：** 錯誤。這會重新建立 coupling 與共同 scaling boundary。
- **D：** 正確。Parallel path 與相容 data contract 限制 migration blast radius。
- **E：** 錯誤。Lambda 有 execution duration、event model、state 與 concurrency 邊界；未先分析 service 的連線、sidecar、協定與資料一致性，就不能把所有長駐服務直接改成 functions。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Understanding concepts in Elastic Beanstalk - AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts.html)、[Decomposing monoliths into microservices - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/introduction.html)

### 練習題 10｜SAP｜[延伸：既有客戶] App Runner/Beanstalk release 與 private dependency

此題的 App Runner 部分只適用於 2026-04-30 前已成為該服務客戶的既有帳號。小團隊以既有 App Runner service 或 Elastic Beanstalk 上 production；版本必須可回滾，且只能以 least privilege 存取 private database。選擇兩項。

A. 永遠部署 mutable latest
B. 使用 versioned artifact/image、真實 application health 與 staged/immutable rollout，保留 rollback target
C. 把 database 放 public subnet
D. 把 build success 視為 production health
E. 分開建立 network 與 runtime identity：App Runner 用 VPC connector、instance role及必要的 ECR access role；Beanstalk 用 VPC/SG 與 EC2 instance profile；兩者再以 Secrets Manager/KMS 權限取得 database credentials

**答案：B、E**

- **A：** 錯誤。Mutable artifact 無法精確識別或回復版本。
- **B：** 正確。Versioned artifact 建立可識別 rollback target，application-aware health 提供 runtime evidence；Beanstalk 可用 immutable/traffic splitting，既有 App Runner service 也應保留可重部署的 image digest。
- **C：** 錯誤。Public database 擴大攻擊面，並非必要 network 解法。
- **D：** 錯誤。Build 不測資料庫、network 或真實 request path。
- **E：** 正確。Network reachability、database authentication 與 AWS API authorization 是三個獨立條件；App Runner instance role、ECR access role 與 Beanstalk EC2 instance profile 不能籠統稱為同一個 service role。

**事實查證：** [AWS Certified Solutions Architect - Professional (SAP-C02) - AWS Certified Solutions Architect - Professional](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)、[Deployment policies and settings - AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.rolling-version-deploy.html)、[Enabling VPC access for outgoing traffic - AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html)、[AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/manage-access.html)、[What is AWS App Runner? - AWS App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html)

## Follow-up Questions

### Q1. 為什麼本章不能只背「Beanstalk管理常見EC2 stack；App Runner從source/image提供更高抽象的…」？

因為方案成立依賴目前的requirement與failure model。題目給的核心壓力是「團隊想快速部署web application，但需要不同程度的VPC、runtime與deployment控制。」，所以「Beanstalk管理常見EC2 stack；App Runner從source/image提供更高抽象的web service。」能直接滿足它；若constraint改成「Lightsail適合簡單小型應用；完整微服務平台則考慮ECS/EKS。」，答案可能翻轉。專業判斷必須能說出state owner、flow與證據，而不是只記服務配對。

### Q2. 主要方案與相鄰替代方案的真正分界是什麼？

主要方案是「Beanstalk管理常見EC2 stack；App Runner從source/image提供更高抽象的web service。」。替代方案「Lightsail適合簡單小型應用；完整微服務平台則考慮ECS/EKS。」並非錯誤，而是優化不同目標。比較時至少逐項檢查protocol/語意、可用failure domain、資料一致性、營運責任、成本模型與變更風險；只比較feature名稱通常會選錯。

### Q3. 如果系統已經部署，最先應監控或驗證哪個 failure mode？

先針對「使用高階平台卻需要未暴露的host控制，最後以脆弱hook繞過抽象。」建立可重現測試。觀察business success、latency/error、queue或replica lag、CloudWatch資源訊號與CloudTrail/Config設定證據，找出最後正常與第一個錯誤state。只有看到部署成功或單一CPU metric，不能證明架構滿足需求。

### Q4. SAA 題目通常如何考這個主題？

SAA會給單一workload與明確限制，要求選最安全、高可用、高效能或成本最佳方案。先圈出「團隊想快速部署web application，但需要不同程度的VPC、runtime與deployment控制。」，排除會導致「使用高階平台卻需要未暴露的host控制，最後以脆弱hook繞過抽象。」的選項，再選「Beanstalk管理常見EC2 stack；App Runner從source/image提供更高抽象的web service。」。本章對應的代表task包括：SAA-2.1 Design scalable and loosely coupled architectures；SAA-3.2 Design high-performing and elastic compute solutions；SAA-4.2 Design cost-optimized compute solutions；SAP-2.1 Design a deployment strategy to meet business requirements。

### Q5. SAP 會如何把同一題加深？

SAP會加入跨帳號、跨Region、既有系統、組織治理、migration window、合規、成本可見性與最少變更等互相拉扯的限制。答案除了「Beanstalk管理常見EC2 stack；App Runner從source/image提供更高抽象的web service。」，還要描述delegation、blast radius、rollout、rollback、evidence與長期operating model；只選一項服務通常不夠。

### Q6. 把 AWS 服務名稱拿掉後，還剩下什麼可重用知識？

留下的是「managed platforms trade control for delivery speed」。它要求先定義需求與state，再選mechanism；在其他cloud、Kubernetes、自建datacenter或一般software architecture裡同樣成立。AWS服務只是這個pattern的一組managed實作，不是pattern本身。
